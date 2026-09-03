#!/usr/bin/env python3
"""
CASCADE BRIDGE — route the library's model calls through the owner's quota-aware router.

The reading pass is the long pole of this project and it is bottlenecked on one machine's GPU.
`ollama ps` tells the story: a 19GB MoE on a 10GB card runs at a 56/44 CPU/GPU split, which puts
one entity at roughly ten minutes and the full roll at about a month.

Cascade already solves this. It is the owner's own router over eleven providers with live keys,
metering each separately and failing over on 429, 401, timeout or an empty response. Groq alone
carries about 17,400 requests a day across four separately-metered models, and Gemini, Cerebras,
Mistral, NVIDIA, GitHub, Z.AI, SambaNova, Cloudflare and OpenRouter sit behind it. The work here
is embarrassingly parallel and stateless, which is the shape that suits a pool of small quotas.

TWO THINGS THIS HAS TO GET RIGHT
--------------------------------
STRUCTURED OUTPUT. The local path uses Ollama's `format` parameter, which constrains generation
to a JSON schema. Cloud endpoints do not all offer that, so the schema is carried in the prompt
as a REQUEST, and `_extract_json` PARSES what comes back -- it confirms the reply is JSON, not
that it matches the schema it was asked for. A cloud model can return perfectly well-formed JSON
of entirely the wrong shape and this layer has no way to tell, because it does not know what any
particular caller's schema means: whether a given key is required, what a valid value for it
looks like, or which shapes are unusable are all questions specific to the call, not to the
transport. That judgment is therefore made one level up, per call site, by whoever holds the
schema's actual meaning -- `pipeline._pool_answer_usable` and the `accept` predicate passed to
`ask_pool_first` are where a cloud answer that parsed but does not deserve to be used gets
rejected and the call retried against the local arm. (Fixed run35, batch 6 -- this docstring
used to claim the validating happened here; it does not, and the module stays a generic
multi-provider transport rather than one that would need every caller's schema semantics baked
into it to keep the old claim true.)

PROVENANCE. Every feat is verified verbatim against the page it came from, and that check does
not care which model produced the sentence. So a cloud model cannot introduce a class of error
the local model could not: it can only be wrong in ways already caught. That is what makes
widening the pool safe rather than a loosening of standards.
"""
import json
import os
import random
import re
import sys
import threading
import time
import silence

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CASCADE = os.environ.get("CASCADE_HOME", r"C:\Users\imarl\cascade")

_BAD_CHARS = (chr(8), chr(11), chr(12), chr(7))
if any(c in open(os.path.abspath(__file__), encoding="utf-8").read() for c in _BAD_CHARS):
    raise SystemExit(__file__ + ": a regex escape was eaten in transit.")

_ENGINE = None
_ROUTER = None
_LOCAL = threading.local()
_BUILD_LOCK = threading.Lock()


def available():
    return os.path.isdir(CASCADE) and os.path.exists(os.path.join(CASCADE, "config.json"))


def engine():
    """Build Cascade's Engine once, against its own config and a scratch store.

    A SEPARATE store file, deliberately. Cascade's own data.db holds the owner's conversations,
    and a batch job that writes 34,000 rows into it would bury them. Nothing here needs history.
    """
    global _ENGINE, _ROUTER
    if _ENGINE is not None:
        return _ENGINE
    if not available():
        return None
    # DOUBLE-CHECKED LOCKING, AND THE LOCK WAS ON THE WRONG HALF (order af50bab5a369).
    #
    # `_BUILD_LOCK` guarded only `thread_engine`'s PER-THREAD build, which needs no cross-thread
    # coordination at all, while THIS build -- the one that publishes three module globals --
    # ran unsynchronised. The readers run sixteen workers wide and every one of them reaches
    # here on the same cold start, so both hazards were live:
    #
    #   TWO ROUTERS. Both threads see `_ENGINE is None`, both build, and the second overwrites
    #   `_ROUTER`. Every per-thread Engine already constructed holds the FIRST Router while
    #   `_alive`, the claim loop, `widen_candidates`, `_bucket_of`, `pools`, `cloud_buckets`,
    #   `prove` and `try_disabled` all read the module global, which is now the second. That
    #   breaks the one invariant `thread_engine`'s docstring gives as the reason the Router is
    #   shared -- the in-flight reservations only pace anything if all workers consult the same
    #   counter -- and reservations split across two counters over-admit, which is the
    #   429-then-learned-cap failure the whole reservation design exists to prevent.
    #
    #   KeyError: 'cfg'. `_ENGINE` was published BEFORE `_CFG["cfg"]` was written, so a second
    #   thread returning from `engine()` between those two statements fell straight into
    #   `E.Engine(_CFG["cfg"], ...)` in `thread_engine` and raised. `_ask_call` calls
    #   `thread_engine()` bare, so nothing caught it and the worker lost its call.
    #
    # So: the whole build happens under the lock, `_ENGINE` is published LAST, and a reader that
    # sees a non-None `_ENGINE` is therefore guaranteed to see a complete `_CFG` and `_ROUTER`.
    # A plain `Lock` is still correct and an `RLock` is not needed: `thread_engine` lets this
    # function RETURN before it takes the same lock for its own build, so the two acquisitions
    # are sequential rather than nested.
    with _BUILD_LOCK:
        if _ENGINE is not None:
            return _ENGINE
        sys.path.insert(0, CASCADE)
        from cascade import config as C, store as S, router as R, engine as E
        cfg = C.load()
        st = S.Store(os.path.join(HERE, "state", "cascade_scratch.db"))
        # TOOLS OFF for batch work. Cascade's system prompt advertises a filesystem toolset to
        # its coding assistant, and a routed model inherits it -- extraction calls came back
        # carrying `tool search_text(...)` and `tool read_file(...)` instead of answers. The
        # verbatim check threw all of it away, so nothing was corrupted, but every one of those
        # was a wasted round trip. A feat-extraction call has nothing to read from a filesystem.
        cfg = dict(cfg)
        cfg["system_prompt"] = ""
        router = R.Router(cfg, st)
        eng = E.Engine(cfg, st, router)
        for m in router.models:
            m.supports_tools = False
        # PUBLICATION ORDER IS THE POINT: config, then router, then -- last -- the engine that
        # every other reader gates on. Built into locals first so a half-built router is never
        # visible under the global name even for an instant.
        _CFG["cfg"] = cfg
        _ROUTER = router
        _ENGINE = eng
        return _ENGINE


_CFG = {}


def thread_engine():
    """One Engine per worker thread, sharing the Router.

    Eight concurrent calls through a single shared Engine did not return in two minutes, while
    one call returned in eight seconds. The Engine carries per-conversation state and a store
    handle, and SQLite connections are not shareable across threads at all -- so the shared
    instance was not slow, it was stuck.

    The Router is deliberately still shared, because its whole job is to see all the traffic at
    once: the in-flight reservations that stop eight workers piling onto one meter only work if
    all eight consult the same counter. It guards its own state with a lock. What is NOT shared
    is the per-call machinery, which never needed to be.
    """
    e = getattr(_LOCAL, "engine", None)
    if e is not None:
        return e
    if engine() is None:
        return None
    with _BUILD_LOCK:
        sys.path.insert(0, CASCADE)
        from cascade import store as S, engine as E
        st = S.Store(os.path.join(HERE, "state", "cascade_scratch.db"))
        e = E.Engine(_CFG["cfg"], st, _ROUTER)
    _LOCAL.engine = e
    return e


def pools():
    e = engine()
    if not e:
        return []
    return sorted({p for m in _ROUTER.models for p in m.pools})


_FENCE = re.compile(r"```(?:json)?\s*(.*?)```", re.S)


def _extract_json(text):
    """Parse the first JSON object in a reply.

    Cloud models wrap JSON in prose or a fence far more often than a schema-constrained local
    one, so this looks for a fence first and then falls back to brace matching. A reply that
    yields nothing parseable returns None and is treated as a failed call, never as an empty
    result -- an empty result would silently read as "this page has no feats".
    """
    if not text:
        return None
    m = _FENCE.search(text)
    if m:
        try:
            return json.loads(m.group(1))
        except Exception:
            silence.note("cascade_bridge.py:extract_json-fence")
            pass
    start = text.find("{")
    while start != -1:
        depth, i = 0, start
        while i < len(text):
            if text[i] == "{":
                depth += 1
            elif text[i] == "}":
                depth -= 1
                if depth == 0:
                    try:
                        return json.loads(text[start:i + 1])
                    except Exception:
                        silence.note("cascade_bridge.py:extract_json-brace")
                        break
            i += 1
        start = text.find("{", start + 1)
    return None


_DEAD = {}
_STRIKES = {}
_DEAD_LOCK = threading.Lock()
# GRADED, NOT FLAT.
#
# A flat ten-minute bench treated "this provider is gone" and "this provider is busy right now"
# as the same event, and under sustained load they are not remotely the same. Fifteen minutes
# into a real run it had benched Mistral, Gemini Flash-Lite and Groq simultaneously -- the three
# carrying almost all the traffic -- because each had queued one request past the deadline. The
# estimate went from 9.7 hours to 59.
#
# So the first miss costs a minute, and only a bucket that keeps missing earns a long bench. Any
# success clears the record entirely, because a provider that just answered is not down.
FIRST_BENCH = 60
MAX_BENCH = 900
# A dead key is not a busy provider. Long enough to stop costing claims, short enough that a
# key fixed this afternoon is back in rotation this evening.
AUTH_BENCH = 4 * 3600


LOCAL_PREFIX = "ollama:"

# THERE IS NO PAID LANE. Owner ruling 2026-08-25: "the paid lane should be erased from the code."
#
# This is the end of a three-step retreat, and the history is the reason the code is now empty
# rather than merely switched off. The lane was opened 2026-08-23 with a hard cap of 500 calls
# in a state file, and spent 598 -- because the cap only ever decided whether to PROMOTE the
# paid bucket in the ranking, while the bucket stayed unconditionally selectable. Setting the
# file's `enabled` to false changed nothing about selectability; DELETING the file was worse
# still, because it stopped the counter while the calls continued. On 2026-08-24 the ruling was
# "there shouldn't be a paid lane anywhere" and a retirement flag was added to kill it
# structurally, with the cap machinery kept "readable as evidence". That machinery is now gone
# too: a retired lane whose plumbing is intact is a lane one edit away from being live, and the
# whole lesson of 598/500 is that a gate which merely looks closed is not closed.
#
# NOTHING IN THIS FILE KNOWS WHAT A PAID BUCKET IS. There is no prefix constant to match, no
# cap to enforce, no counter to maintain, and no branch that could reach one. Re-introducing a
# paid lane means writing it from scratch, deliberately, with an owner saying so -- which is
# exactly the cost it should carry.
#
# The old spend counter survives on disk, under `state/`, and is deliberately NOT deleted: it is
# the only record of what the lane cost. It is not named here on purpose -- `verify_math` §19h
# asserts that this file cannot even spell it, because a filename in a comment is the first
# handhold anyone rebuilding the lane would reach for. The ledgers name it; the code does not.
_WIDEN_RR = [0]
_RR_LOCK = threading.Lock()                 # round-robin cursor for the widened fallback

# ---------------------------------------------------------------------- per-bucket pacing
#
# A claim says "this bucket has headroom". It does not say "and it is your turn". Nine workers
# claiming across a dozen buckets still put several requests a second into a provider whose free
# tier allows ten a MINUTE, and the result was 4% of calls succeeding: every one of the other 96%
# a 429, a cooldown, and -- until the router was fixed -- a learned cap that made the pool
# permanently smaller.
#
# This is the same instrument `feats._throttle` uses on wiki hosts, applied to model providers:
# a bucket may be entered once per 60/rpm seconds, and a worker that arrives early waits its
# turn. Waiting two seconds beats a 429 that costs a cooldown, and it beats a retry ladder that
# costs ninety.
_PACE_LOCK = threading.Lock()
_PACE_LAST = {}
_PACE_GATE = {}
# Never pace slower than this even for a bucket claiming a tiny rpm -- a genuinely 1-rpm provider
# is not worth a worker standing still for a minute, and the deadline handles it either way.
MAX_PACE_SECONDS = 8.0


def _interval(bucket):
    """Minimum seconds between entries to this bucket, from its own declared rate."""
    try:
        rpm = (_ROUTER.limits_for(bucket) or {}).get("rpm")
    except Exception:
        silence.note("cascade_bridge.py:interval")
        return 0.0
    if not rpm or rpm <= 0:
        return 0.0
    return min(MAX_PACE_SECONDS, 60.0 / float(rpm))


def _pace(bucket):
    """Block until this bucket's turn. One waiter at a time per bucket, so the queue is orderly.

    The per-bucket gate matters: without it, ten workers all sleep until the same instant and
    then arrive together, which is the burst the pacing exists to prevent.
    """
    gap = _interval(bucket)
    if gap <= 0:
        return
    with _PACE_LOCK:
        gate = _PACE_GATE.setdefault(bucket, threading.Lock())
    with gate:
        last = _PACE_LAST.get(bucket, 0.0)
        wait = gap - (time.time() - last)
        if wait > 0:
            time.sleep(min(wait, MAX_PACE_SECONDS))
        _PACE_LAST[bucket] = time.time()




def cloud_buckets(pool="coding"):
    """Distinct REMOTE buckets in this pool — the real width of the fan-out.

    Five of this pool's sixteen buckets are local Ollama models. They are separate entries in
    the router because they are separate models, but they are one GPU, and a claim that lands on
    one is a cloud call that is quietly the slow path. Counting them as capacity is what made
    sixteen workers slower than eight: half of them queued on a card that serves one request at
    a time while the cloud sat idle.
    """
    try:
        if engine() is None:
            return []
        seen = []
        for m in _ROUTER.candidates(pool):
            if m.bucket.startswith(LOCAL_PREFIX) or m.bucket in seen:
                continue
            seen.append(m.bucket)
        return seen
    except Exception:
        silence.note("cascade_bridge.py:cloud_buckets")
        return []


def _bucket_of(name):
    """The bucket a model id (or label) belongs to. "" when nothing matches.

    The engine's `model` event names the model that ACTUALLY served a call; this is the only
    honest way to turn that into the bucket the meter belongs to. Matching on the id first
    because it is the router's own key -- labels are display strings and two providers may
    reasonably print the same one. Total: a lookup that can raise would take down the call it
    exists to describe.
    """
    if not name:
        return ""
    try:
        for m in (_ROUTER.models if _ROUTER is not None else []):
            if m.id == name:
                return m.bucket
        for m in (_ROUTER.models if _ROUTER is not None else []):
            if getattr(m, "label", None) == name:
                return m.bucket
    except Exception:
        silence.note("cascade_bridge.py:bucket-of")
    return ""


PROOF = os.path.join(HERE, "data", "POOL_PROOF.json")
_PROVEN = [None]


# A proof this old is no longer evidence about now. Free tiers roll their windows constantly,
# and a bucket that was busy an hour ago is not a bucket that is broken.
PROOF_TTL = 3600

# ON WORD BOUNDARIES, for the same reason `_PERMANENT_CODES` is: a bare `"404" in v` also
# matches the 404 inside a request id, a trace hash or a token count, and the penalty for a
# false positive here is not a four-hour bench but PERMANENT exclusion from the pool until the
# next proof. This test was the one place in the file still doing a raw substring check on a
# status code, which is m103's fault surviving in the last room nobody had swept.
_DEAD_CODES = re.compile(r"\b(401|402|404|410)\b")
# The prose half. `no such model`, `needs billing on that provider` and `retired by the
# provider` are the engine's OWN wordings from `is_dead()`, which is where these arrive from;
# they are distinctive enough that an accidental hit is not a realistic failure.
# `model rejected by the provider` WAS MISSING, AND IT IS A REAL ESCAPE (run40 sweep).
#
# `is_dead()` in the engine has FOUR wordings, not three. The 404/410/402 branch yields "no such
# model" / "retired by the provider" / "needs billing on that provider", and a fourth branch --
# HTTP 400 or 422 whose body names the model as not found, unknown, invalid, unsupported or
# decommissioned -- yields "model rejected by the provider" (engine.py:545, read directly).
#
# That fourth reason reaches `POOL_PROOF.json`'s `reason` field verbatim, and NOTHING here
# recognised it: 400 and 422 are not in `_DEAD_CODES` (401|402|404|410) and the phrase was not
# in this tuple. So a bucket the ENGINE has permanently disabled for a genuinely unrecoverable
# reason was never added to the exclusion set, and the widen-fallback path went on re-selecting
# it indefinitely -- the pool-WIDENING error, the mirror of the pool-narrowing one fixed in
# `dead_forever()`'s memo this same shift.
#
# `bad key` IS KEPT, AND THE COMMENT NO LONGER CLAIMS IT IS AN ENGINE WORDING. Verified: the
# only occurrence of that phrase anywhere in the cascade tree is a SOURCE COMMENT at
# engine.py:225 ("401/403 mean a bad key -- a long cooldown stops us hammering it"); the engine
# never returns it, and 401/403 take the ordinary bench path rather than the permanent one. It
# is therefore a marker for text the engine does not emit. It is left in place deliberately:
# removing a marker SHRINKS the exclusion set, which is the pool-widening direction and the more
# expensive error, and a marker that matches nothing costs one substring test.
_DEAD_WORDS = ("no such model", "needs billing", "bad key", "retired by the provider",
               "model rejected by the provider")


def dead_forever():
    """Buckets excluded by proof — and ONLY for reasons that cannot fix themselves.

    The first version of this excluded anything that failed to answer, and it made the pool
    SMALLER rather than more accurate. Eleven buckets were recorded "no answer" at a 45-second
    deadline, and `huggingface`, `zai` and `gemini-3.1-flash-lite` were observed answering
    normally minutes afterwards -- they had been rate-limited at that instant, and a rate limit
    is the most temporary condition a provider has. I wrote a transient failure down as a
    permanent property, which is the precise mistake this project exists to stop making.

    So exclusion now requires a reason that CANNOT resolve on its own:

        401  the key is wrong                  a human must fix it
        402  the account has no balance        a human must fix it
        404  the model does not exist          the config is stale
        410  the model was retired             it is not coming back

    A timeout, a 429, or a silent minute excludes nothing. Those buckets stay in rotation and
    fail over on their own, which is what the router is for -- and if they are genuinely down,
    the deadline costs one call and the next claim goes elsewhere.

    IT READ A FIELD THAT COULD NOT CONTAIN ANY OF THAT (order 2f18e95e4f17). The test ran on
    `verdict` alone, and `prove()` has only ever written a five-word vocabulary into `verdict`:
    `local`, `provider disabled`, `no API key`, `answers`, `no answer`, or an exception's class
    name. Not one of those can hold a status code or a provider's wording, so every branch below
    was structurally unreachable -- measured against the live `data/POOL_PROOF.json`, which held
    three distinct verdict strings across 36 rows and no bucket-specific reason at all. The
    permanent-failure classifier could not see a permanent failure. `prove()` now records the
    provider's own disposition in `reason` (from the engine's `failover` events, which is the
    only place that text ever existed), and this reads BOTH -- `verdict` first so an older proof
    file written before that change still classifies exactly as it did.
    """
    # THE ANSWER IS CACHED AGAINST THE PROOF FILE, NOT FOR THE LIFE OF THE PROCESS.
    #
    # `if _PROVEN[0] is not None: return _PROVEN[0]` memoised the FIRST call and never looked
    # again -- in jobs that run for hours or days. That breaks the function in both directions.
    # A bucket whose key dies at noon is proven dead by the next `prove()` and written into
    # POOL_PROOF.json, but a reader that first asked at 09:00 keeps claiming it, burning a
    # deadline per call until the process restarts; that is the shape of `hyperbolic:free` and
    # `cloudflare:free` sitting at 0 successful calls while still being claimed. And the
    # reverse: a key the owner ROTATES stays excluded until restart, so the fix does not take.
    # PROOF_TTL already says a proof older than an hour is not evidence about now -- the
    # process-lifetime memo quietly overrode it with "forever".
    #
    # Keyed on the file's mtime, so a re-proof invalidates it and an unchanged file costs one
    # stat. (run #29, batch 05, reproduced.)
    try:
        stamp = os.path.getmtime(PROOF)
    except Exception:
        stamp = None
    # AND THE MEMO CARRIES FRESHNESS AS WELL AS IDENTITY (order 90bd64fe676d).
    #
    # Keying on the mtime alone MOVED the override without removing it. `PROOF_TTL` says a proof
    # older than an hour is not evidence about now -- but this line short-circuited BEFORE the
    # freshness test below, so as long as POOL_PROOF.json was not rewritten the mtime never
    # changed, the memo never invalidated, and the stale exclusion set was returned for the life
    # of the process. That is the same "quietly overrode it with forever" the comment above says
    # it fixed, one trigger along: it now takes a stalled `prove()` rather than a stalled
    # `dead_forever()`.
    #
    # REPRODUCED with PROOF_TTL shrunk to 1.0s against a scratch proof file: at t=0 the call
    # returned ['acme:free']; at t=1.6s, the file untouched, the CACHED call still returned
    # ['acme:free'] while the same call with `_PROVEN` cleared returned []. That third value is
    # what a process starting one second later computes from the identical file -- so two of the
    # sixteen workers in one run disagree about which buckets are in the pool, which is the
    # "two views of the same pool disagreeing" defect this module's own widen-path comment
    # names. The error direction is pool-NARROWING, on the resource this file repeatedly calls
    # the binding constraint, and the readers affected are exactly the long-lived worker
    # processes the memo was written for.
    #
    # The entry now records WHEN it was computed as well as which file it was computed from, and
    # is discarded once the proof it rests on has aged past PROOF_TTL. The recompute costs one
    # open of a small JSON file, an hour apart at most.
    if (_PROVEN[0] is not None and _PROVEN[0][0] == stamp
            and (stamp is None or time.time() - stamp <= PROOF_TTL)):
        return _PROVEN[0][1]
    out = set()
    try:
        if stamp is not None and time.time() - stamp <= PROOF_TTL:
            with open(PROOF, encoding="utf-8") as f:
                rows = json.load(f)
            for r in rows:
                if not isinstance(r, dict) or not r.get("bucket"):
                    continue
                # BOTH FIELDS. `verdict` is the coarse token every other reader counts;
                # `reason` is where a status code or a provider's own words can actually be.
                v = (str(r.get("verdict") or "") + " " + str(r.get("reason") or "")).lower()
                # A FAULT ON THIS MACHINE IS NOT EVIDENCE ABOUT A PROVIDER'S ACCOUNT, and now
                # that the provider's raw text reaches this line, it can arrive carrying one.
                # `local_transport` is the same guard `permanent_refusal` opens with, and it
                # matters more here: that one costs a four-hour bench, this one excludes the
                # bucket outright. A WAF turning the client away is evidence about the REQUEST,
                # by the identical argument.
                # `client_rejection`, not the bare regex: a proof row whose reason merely NAMES
                # cloudflare must not be excused from exclusion (order 62f4b7caae73). This is the
                # costlier of the two sites -- `permanent_refusal` spends a four-hour bench, this
                # one excludes the bucket outright until the next proof.
                if local_transport(v) or client_rejection(v):
                    continue
                if _DEAD_CODES.search(v) or any(w in v for w in _DEAD_WORDS):
                    out.add(r["bucket"])
    except Exception:
        silence.note("cascade_bridge.py:dead_forever")
    _PROVEN[0] = (stamp, out)
    return out


UNRECOGNISED = os.path.join(HERE, "state", "POOL_UNRECOGNISED.json")
_UNREC_LOCK = threading.Lock()

# Cascade's own aggregate wrappers. These are what the ENGINE says when a call fails; they name
# the friendly model labels it tried and carry NO disposition -- no status code, no provider
# wording, nothing a classifier can act on.
_WRAPPERS = ("candidates failed", "every model in this pool")
SCRATCH_DB = os.path.join(HERE, "state", "cascade_scratch.db")

# A FAILURE THE CODE CAN NAME IS NOT AN UNRECOGNISED FAILURE.
#
# Found 2026-08-25 (run #23) by reading the ledger the `every pool failure is recognised`
# standard had filled: 44 open rows, 122 occurrences, and exactly ONE of them was a fault
# nobody could name (`groq:groq/compound-mini: empty response`). Everything else was an
# ordinary throttle -- `Rate limit exceeded`, `429`, `tokens per day (tpd): limit 200000`,
# `Every model in this pool is rate limited or unconfigured`. The classifier's vocabulary was
# BINARY: permanent, or unrecognised. It had no word for "busy", which is the single most
# common thing a free-tier pool says, so the standard built to surface the unknown was burying
# it under the known at 122 to 1.
#
# That is worth naming precisely, because it is the same failure shape the project keeps
# meeting from the other side: m108 was a classifier that could never match, and this is a
# classifier that matches everything. Both end with a page that cannot be read.
#
# NOTHING IS HIDDEN BY THIS. A throttle is already counted twice over -- in the throughput
# panel's refusal count, and as `outcome='rate_limited'` in Cascade's own `usage` table, which
# is where `model calls per hour` and its four sub-standards read from. What changes is only
# that a NAMED refusal stops being filed as a NAMELESS one.
#
# `Every model in this pool is rate limited or unconfigured` is on this list deliberately.
# It is an engine wrapper (it is in `_WRAPPERS` too) and it is reached only when the unwrap
# found no fresh provider row -- but unlike `All N candidates failed: <label>`, which carries
# no disposition whatsoever, this one STATES its disposition in its own words. Recognising it
# costs nothing and removes 7 buckets of noise.
#
# Word boundaries on the numeric codes, for m103's reason: a bare `"429" in err` also matches
# the 429 inside a request id, and a classifier that cries wolf on a trace hash is worse than
# one that stays quiet.
# Each entry is a PHRASE, not a lone word. `"connection"` and `"capacity"` were on this list
# for one draft and the sweep agent auditing the same session was right to object: a bare
# `"connection" in err` also matches `invalid connection string`, which is a configuration
# fault someone must fix, and quietly calling it "busy" is how a real unknown stops being
# reported. Every marker here has to be a thing a provider says when it is TEMPORARILY unable,
# and nothing else -- because the cost of over-matching is the ledger going quiet again.
_TRANSIENT_WORDS = (
    "rate limit", "rate-limit", "rate_limit", "ratelimit", "too many requests",
    "quota", "throttl", "overloaded", "over capacity", "at capacity",
    "high demand", "try again", "temporarily", "timed out", "timeout",
    "could not resolve host", "connection reset", "connection refused",
    "could not connect", "failed to connect", "unconfigured",
    "service unavailable", "bad gateway",
)
_TRANSIENT_CODES = re.compile(r"\b(408|409|425|429|500|502|503|504)\b")

# `All 7 candidates failed: <label>, <label>, ...` -- the engine having walked a whole candidate
# list and found none of it available. Measured 2026-08-25: 15 of the 23 aggregate rows in the
# ledger named MORE THAN ONE candidate, and for those the unwrap cannot work by construction --
# `provider_error()` reads the PINNED bucket's row, but a multi-candidate call is not
# necessarily an attempt on the pinned bucket at all. The ledger showed pin
# `groq:openai/gpt-oss-20b` against candidate label `Llama 3.3 70B (Groq)`: different model,
# so `bucket_state` for the pin was never touched by that call and aged past the 180s window.
#
# A multi-candidate aggregate is NOT AN UNNAMEABLE PROVIDER FAULT -- it names no provider and
# affords no per-provider action. It is a statement about POOL CAPACITY in that instant, which
# is precisely what `model calls per hour`, `buckets with headroom` and `buckets not exhausted`
# already measure and act on. Filing it as an unrecognised provider refusal is a category
# error, and 15 of them drowned the one row that was a real unknown.
#
# `All 1 candidates failed: <label>` DELIBERATELY STAYS UNRECOGNISED. There the pin and the
# attempt do agree, so a failed unwrap means something genuinely went unexplained -- and that
# is the exact row shape that exposed m108 (`zai:free` re-claimed forever while its real error
# read "Insufficient balance"). Keeping the single-candidate case loud is what preserves the
# discovery path; recognising the multi-candidate case is what makes it visible again.
_MULTI_CANDIDATE = re.compile(r"\ball (\d+) candidates failed\b")


def pool_exhausted(err):
    """True if `err` is the engine reporting a whole candidate list unavailable at once."""
    m = _MULTI_CANDIDATE.search((err or "").lower())
    return bool(m) and int(m.group(1)) > 1


def named_transient(err):
    """True if `err` names a busy/unreachable condition the router already handles.

    Used only to keep a NAMED refusal out of the unrecognised ledger. It deliberately does not
    bench, cool down, or otherwise change routing -- whether a refusal should cost a bucket
    anything is an open owner question (NEXT_STEPS routing decision B), and answering it
    quietly inside a diagnostic would be exactly the kind of silent policy change this file's
    history argues against. Checked AFTER the permanent classifier, so a billing complaint that
    also says "try again" is still correctly benched.
    """
    e = (err or "").lower()
    if not e:
        return False
    return bool(_TRANSIENT_CODES.search(e)) or any(w in e for w in _TRANSIENT_WORDS)


# The provider answered, with nothing in it. Cascade's engine has two wordings for this one
# condition (`cascade/engine.py:277` and `:343`), and because `record_unrecognised` de-duplicates
# on EXACT text they arrived as two separate permanent rows for the same fault on the same
# bucket -- `groq:groq/compound-mini` held both on 2026-08-25. Neither was a throttle, an
# exhaustion or a dead key, so no existing predicate could name either, and the HIGH-severity
# `every pool failure is recognised` standard sat red on them.
#
# EXACT MATCH ON THE WHOLE STRING, deliberately, not a substring test. A loose `"empty" in err`
# would quietly swallow genuinely unknown failures that merely mention the word, which is the
# one thing this ledger exists to prevent -- naming a fault must never become a way of not
# seeing faults. Adding a wording here is a claim that this exact sentence is understood.
#
# Naming it does NOT bench it, exactly as `named_transient` does not: whether an empty
# completion should cost a bucket a cooldown is the open routing question in NEXT_STEPS, and
# answering it quietly inside a diagnostic is the failure mode this file's history warns about.
# Tracked as a named condition in BUGS.md rather than vanishing off the page. (run #25)
_EMPTY_CONTENT = (
    "no answer text produced",
    "produced no answer text",
    "empty response",
)


def empty_content(err):
    """True if `err` is the engine reporting a successful call that carried no content."""
    return (err or "").strip().lower() in _EMPTY_CONTENT


# A FAULT ON THIS MACHINE IS NOT A REFUSAL BY A PROVIDER, AND MUST NEVER COST A BENCH.
#
# Measured 2026-08-25: `deepinfra`, `huggingface`, `cerebras` and `chutes` all sat on
# `transport: curl: (6) Could not resolve host: <host>` -- one resolver fault, four providers,
# and not one of them had said anything at all. Benching that would convert a local network
# problem into four permanently disabled providers AND hide the cause, because a benched
# bucket stops being asked and therefore stops reporting. Filed separately as a DNS order.
#
# `could not resolve host` is already in `_TRANSIENT_WORDS`, so today these classify correctly
# by luck of ordering: the permanent test runs FIRST, and merely fails to match. That is the
# whole safety margin, and it lasts exactly until someone adds a marker broad enough to catch
# a curl line -- at which point four providers vanish and the ledger goes quiet about why.
# This makes the guarantee structural instead: if the text is one of curl's own transport
# complaints, no permanent marker can reach it, whatever anyone adds below.
#
# AND THE WINDOWS SOCKET FAULTS THIS HOST ACTUALLY PRODUCES (order 119ebee92481). WinError 10055
# -- "an operation on a socket could not be performed because the system lacked sufficient buffer
# space" -- and its neighbour 10048 ("only one usage of each socket address ... is normally
# permitted") were not on this list, so either one reaching a classifier as text was attributable
# to a PROVIDER. That is not hypothetical here: order f6c52ef7657f records a foreign process
# cyclically consuming the entire ephemeral port range on this machine, during which every
# outbound connect() returns 10055 or 10048 and the foreman reported "0 of 36 buckets answer".
# Blaming thirty-six providers for one local socket exhaustion is the exact inversion this list
# exists to prevent.
#
# QUALIFIED, NOT BARE CODES. `"10055" in err` would also match the 10055 inside a request id or
# a token count -- m103's fault, which the code classifiers in this file carry word boundaries
# to avoid. `local_transport` is a plain substring test, so the marker carries the `winerror`
# prefix instead, and the two prose forms are listed beside it because a socket error reaches
# this code as often through its message as through its number.
_LOCAL_TRANSPORT = ("could not resolve host", "failed to connect", "could not connect",
                    "connection reset", "connection timed out", "curl exited",
                    "winerror 10055", "winerror 10048",
                    "lacked sufficient buffer space", "only one usage of each socket address")


def local_transport(err):
    """True if `err` is this machine failing to reach the provider, not the provider refusing."""
    return any(w in (err or "").lower() for w in _LOCAL_TRANSPORT)


# A SPENT ACCOUNT IS PERMANENT AND POLITE; A THROTTLE IS TEMPORARY AND SOUNDS IDENTICAL.
#
# Measured over three hours on 2026-08-25 (m108's descendant, run #27). The two halves cost
# very differently, and only the second half was still costing anything:
#
#   dead keys, already caught here -- `cloudflare:free` HTTP 401 `Authentication error` (24
#   errors/3h), `hyperbolic:free` HTTP 401 `Could not validate credentials` (25/3h);
#   spent accounts -- `zai:free` `Insufficient balance or no resource package. Please
#   recharge.` counted `rate_limited` NINETY times in three hours, and `cohere:free`, a Trial
#   key whose 1000-calls-a-month allowance is gone, counted `rate_limited` sixteen more.
#
# The second shape is the worse one and the reason this list keeps growing. A dead key at
# least reads as an error; a spent account read as CONTENTION backs off politely, waits, and
# returns for ever, holding a claim and a deadline every time round. It never escalates,
# because nothing it does looks like a failure worth escalating.
#
# EVERY MARKER HERE MUST BE A THING A PROVIDER SAYS ONLY WHEN THE ACCOUNT IS FINISHED.
# The penalty for over-matching is four hours of bench on a bucket that was merely busy, which
# is m103's harm and worse than the bug being fixed -- the pool is already the binding
# constraint. Measured this shift, and every one of these was checked against the live text of
# the buckets that MUST KEEP ROTATING:
#
#   `nvidia:free`   118 ok / 5 rate_limited -- `{"status":429,"title":"Too Many Requests"}`
#   `groq:*`        25 ok  -- `Rate limit reached for model ... Please try again in 6m51.264s.
#                              Need more tokens? Upgrade to Dev Tier`
#   `gemini:*`      `You exceeded your current quota, please check your plan and billing
#                    details` -- says BILLING, and resets daily. This is why the marker is
#                    `needs billing` and not `billing`, and why Mistral's is the whole phrase
#                    `check your subscription` and not `subscription`.
#   `openrouter:free` `Rate limit exceeded: free-models-per-day. Add 10 credits to unlock 1000
#                    free model requests per day` -- says CREDITS, and resets at midnight UTC.
#                    This is why HuggingFace's marker is `monthly included credits` entire.
#
# Cohere is the sharpest of these. A Trial key emits the SAME SENTENCE for its per-minute
# throttle and for its monthly cap, differing only in the tail: `limited to 40 API calls /
# minute` versus `limited to 1000 API calls / month`. So the marker is the unit, not the key
# type -- matching `trial key` would bench a live bucket for four hours over a 40-a-minute
# throttle. Both spacings, because providers do not agree about the slash.
#
# `payment_required` is separate from `payment required` for the same reason: the type field
# arrives as `payment_required_error`, which the spaced form cannot see.
#
# `depleted` already catches HuggingFace's `You have depleted your monthly included credits`.
# `monthly included credits` is listed anyway and the redundancy is deliberate: bare `depleted`
# is the loosest marker on this list and a future audit may well narrow it, and when that
# happens HuggingFace should not silently regress to being retried for ever.
_PERMANENT_WORDS = (
    "authentication", "invalid_api_key", "credentials",
    "insufficient balance", "no resource package",
    "payment required", "payment_required", "needs billing", "depleted",
    "check your subscription", "positive balance", "monthly included credits",
    "api calls / month", "api calls/month",
    # ADDED 2026-08-26 after probing every provider for a real completion. Each of these is a
    # verbatim fragment of a refusal this pool actually received, and each slipped through:
    #   chutes  "Quota exceeded and account balance is $0.0, please pay with fiat or send tao"
    #   deepinfra "You need positive balance... Please add balance manually or setup top-up"
    # `quota exceeded` ALONE is deliberately NOT here -- on most providers that is a daily
    # cooldown, which the owner's ruling says to keep. It is the BALANCE half that makes it
    # permanent, so the balance half is what gets matched.
    "account balance is $0", "balance is $0", "add balance", "setup top-up", "set up top-up",
    "subscription has ended", "subscription expired", "billing tab", "purchase pre-paid",
)
# Word boundaries, for m103's reason: a bare `"403" in err` also matches the 403 inside a
# request id like `req_4403abc`, and the penalty for a false positive is four hours of bench.
# 403 IS NOT AN ACCOUNT FAULT BY ITSELF, and treating it as one benched a working provider.
# Measured 2026-08-26: `groq` and `cerebras` both answered `HTTP 403 error code: 1010` to a
# completion request. That is CLOUDFLARE rejecting the CLIENT, not the provider rejecting the
# account -- 1010 is its browser-integrity code. Sending a real User-Agent turned groq's 403
# straight into a 200 and cerebras's into a truthful 402. This project already carries the same
# scar from the other side of the fence: `verify_math` section 19aa records MediaWiki answering
# 403 to `Python-urllib/3.13` and 200 to the project's own UA.
#
# So a BARE 403 is no longer permanent; it needs corroborating words. The thing a 403 most often
# means here is fixable on this side, and benching hides that for four hours.
_PERMANENT_CODES = re.compile(r"\b(401|402)\b")
# A WAF turning the client away. Never an account fault, whatever status code it wears.
#
# `cloudflare` WAS A BARE ALTERNATIVE HERE, AND IT IS ALSO THE NAME OF A CONFIGURED PROVIDER
# (order 62f4b7caae73). Both `permanent_refusal` and `dead_forever` OPEN by returning or skipping
# on a client-rejection hit, so any error text that happened to name its own provider was
# dismissed as a WAF rejection whatever status code it carried. Demonstrated offline before the
# fix: permanent_refusal("HTTP 401 Authentication error") was True while
# permanent_refusal("Cloudflare Workers AI: HTTP 401 Authentication error") was False, and
# dead_forever() over two proof rows carrying the IDENTICAL 401 excluded groq:free and refused
# cloudflare:free. This file WARNED about it at the `box` comment in `_ask_call` -- the fix
# applied there split failovers from reasons but never narrowed the guard, and two paths still
# deliver provider-naming text here (`_why = raw` keeps the engine's "All 1 candidates failed:
# <label>" wrapper when no failover reason exists, and `provider_error()` returns a
# `bucket_state.last_error` a provider may open with its own name). The corroboration is in
# OWNER_EXCLUDED: `cloudflare:free` had to be struck off BY HAND with "HTTP 401 -- credential
# dead, needs rotation", and the comment above that dict says dead_forever() "cannot help
# either". One of the four hand-excluded buckets was the one bucket this classifier was
# structurally blind to. Scanned at filing: of the 26 configured provider names, `cloudflare` is
# the only collision with any classifier vocabulary in this module.
#
# So the challenge markers stand alone and the provider name does not: it is now only evidence
# when it arrives WITH one of the companion words below, which is what a real Cloudflare block
# page says and what a provider naming itself in a 401 does not.
_CLIENT_REJECTION = re.compile(r"error code:\s*10\d\d|browser integrity|just a moment|"
                               r"attention required|checking your browser|"
                               r"enable javascript and cookies")
_WAF_COMPANION_WORDS = ("ray id", "blocked", "captcha", "security service", "challenge",
                        "access denied")


def client_rejection(err):
    """True if `err` is a WAF refusing the CLIENT -- never evidence about the account.

    Two ways to qualify: a challenge marker that only a block page emits (the 1010 family,
    "browser integrity", "just a moment", "attention required"), or the provider name
    `cloudflare` CO-OCCURRING with a companion word from a block page. The bare name is not
    enough, for the reason written above the patterns.
    """
    e = (err or "").lower()
    if not e:
        return False
    if _CLIENT_REJECTION.search(e):
        return True
    return "cloudflare" in e and any(w in e for w in _WAF_COMPANION_WORDS)


def permanent_refusal(err):
    """True if `err` is an account fault a human must fix -- a dead key or a spent balance.

    Checked BEFORE `named_transient`, so a billing complaint that also says "try again" is
    still benched. `local_transport` wins over everything: a curl failure on this machine is
    not evidence about the provider's account, whatever words happen to be in the buffer.

    OWNER RULING 2026-08-26: "if something runs out and is on cooldown, fine; if something runs
    out and requires payment after running out, axe it." That is exactly the line this function
    draws. A 429 is a cooldown and stays in the pool. A 402 -- payment required, insufficient
    balance, depleted credits -- is PERMANENT, because the remedy is money and the answer to
    money is no. Nothing here may treat a 402 as something to retry into.
    """
    e = (err or "").lower()
    if not e or local_transport(e):
        return False
    # A WAF turning us away is evidence about the REQUEST, not the provider -- the same reason
    # `local_transport` wins above. Through `client_rejection`, so the provider name alone
    # cannot excuse a refusal (order 62f4b7caae73).
    if client_rejection(e):
        return False
    return bool(_PERMANENT_CODES.search(e)) or any(w in e for w in _PERMANENT_WORDS)


def provider_error(bucket, max_age_s=180):
    """The PROVIDER's own last error for `bucket`, from Cascade's scratch DB. "" if unknown.

    THE ENGINE HANDS US A WRAPPER, NOT A REASON, AND THIS IS WHY THE BENCH NEVER FIRED.
    Found 2026-08-25 by the standard added the same hour: `zai:free` was being re-claimed
    forever with `box["error"]` reading `All 1 candidates failed: GLM 4.7 Flash (Z.AI)` -- while
    the row in `bucket_state.last_error`, stamped the same minute, read `Insufficient balance or
    no resource package`. The permanent-refusal classifier was correct and simply never saw the
    text it was written to match. Repairing the classifier's WORDING earlier that day was
    necessary and not sufficient; this is the missing half.

    Read-only, single row, and aged: a stale row is not evidence about this call, and claiming
    it would bench a live provider for four hours on a fossil. Total -- a diagnostic lookup that
    can raise would take down the call it is trying to explain.
    """
    try:
        import sqlite3
        con = sqlite3.connect("file:%s?mode=ro" % SCRATCH_DB, uri=True, timeout=1.0)
        try:
            for err, at in con.execute(
                    "select last_error, updated_at from bucket_state where bucket=?", (bucket,)):
                if err and at and (time.time() - float(at)) <= max_age_s:
                    return " ".join(str(err).split())[:300]
        finally:
            con.close()
    except Exception:
        silence.note("cascade_bridge.py:provider-error")
    return ""


def _row_survived(key, count):
    """Is `key` on disk in POOL_UNRECOGNISED.json with at least `count` occurrences?

    The read-back half of `record_unrecognised`'s compare-and-swap, and it is needed because
    the swap is not one instruction: `silence.replace_if_unchanged` digests the target and THEN
    renames over it, so two processes that digest the same value both pass the compare and the
    later rename silently discards the earlier one -- while BOTH are told they landed. Asking
    the file whether the row is actually there turns that undetectable loss into one more
    attempt. `>=` rather than `==` because a concurrent writer bumping the same key further is
    not a loss; a smaller count, or no row at all, is.

    Total, like everything else on this path: a read that fails cannot be evidence the row
    survived, so it answers False and the caller retries.
    """
    try:
        with open(UNRECOGNISED, encoding="utf-8") as f:
            rows = json.load(f)
        r = rows.get(key)
        return isinstance(r, dict) and int(r.get("count", 0)) >= int(count)
    except Exception:
        silence.note("cascade_bridge.py:unrecognised-readback")
        return False


def record_unrecognised(bucket, err):
    """Write down a pool failure that matched no known disposition, so it can be investigated.

    Owner ruling 2026-08-25: "an unrecognised failure should be immediately investigated and
    resolved upon spotting it." Spotting it requires that it exist somewhere a person or a
    maintenance run will look, with ENOUGH TEXT TO CLASSIFY IT. A counter cannot be
    investigated; the error string can. Keyed by bucket + the error's leading text so a
    provider repeating one fault stays one row with a count rather than flooding the file.

    Deliberately NOT a bench. Whether an unrecognised failure should also cost the bucket a
    cooldown is a routing question the owner has not ruled on, and benching quietly is the
    opposite of surfacing. This records; `standards` turns the record red; the run resolves it.

    Total, like `silence.note`: a recorder that can raise would suppress the fault it exists to
    expose, and this sits on the hot path of every failed call.
    """
    try:
        text = " ".join(str(err).split())[:300]
        # THE KEY FOLDS; THE TEXT DOES NOT. Run #26: the ledger held eight buckets carrying
        # `Every model in this pool is rate limited or unconfigured.` and the same sentence
        # lowercased as SEPARATE PERMANENT ROWS, because this key was the raw text and a change
        # upstream started folding it. One fault, two rows, both counted, both red.
        #
        # This is the third time de-duplication-on-exact-text has split one fault (m132 was the
        # second, and named two engine wordings rather than fixing the key). Case is not a
        # different failure and must never again be able to look like one. Folding here cannot
        # hide anything: `text` -- the thing a person reads and classifies -- is stored verbatim,
        # and two genuinely different errors do not become one by differing in case alone.
        key = bucket + "|" + text[:80].lower()
        now = time.time()
        # COMPARE-AND-SWAP, NOT A SNAPSHOT WRITE (order 853aa8990132).
        #
        # `_UNREC_LOCK` is a `threading.Lock`, so it orders writers inside ONE process, and this
        # file is written from every process that imports `cascade_bridge` -- read, pipeline,
        # feats, overwatch. The previous shape loaded the whole dict, edited it, and landed the
        # snapshot: process A loads, process B loads, A writes, B writes, and B's rename
        # replaces the file with a version that never contained A's key. A row -- or an
        # incremented `count` -- was silently gone.
        #
        # The loss is the exact loss this ledger exists to prevent. The owner's ruling of
        # 2026-08-25 is that an unrecognised failure is investigated the moment it is spotted,
        # and a row that was never written is a fault nobody spots; worse, the losses bunch up
        # in a BURST, which is both when several processes fail at once and when the row is
        # likeliest to be the one that matters. A dropped `count` also corrupts the
        # "how long has this been failing" signal the file is kept for.
        #
        # So the read-modify-write retries against a digest taken at read time, which is the
        # shape `workorders._mutate` and `endpoint.register` already use here. The temp still
        # carries pid AND thread (m100's fixed-`.tmp` collision race stays closed) plus the
        # attempt number, and the landing still goes through `silence` -- `replace_if_unchanged`
        # calls `replace_retry`, so the Windows denied-rename backoff is unchanged and the
        # verdict is still READ rather than assumed, which is what makes the note below reachable.
        with _UNREC_LOCK:
            landed = False
            # TWELVE ATTEMPTS AND A JITTERED BACKOFF, not the flat eight `workorders._mutate`
            # uses. Measured while fixing this: three processes recording forty rows each with
            # no think time between them landed 91 of 120 on a flat backoff, because every loser
            # slept the SAME interval and collided again on the next attempt. Jitter breaks the
            # lockstep, and the extra attempts cost nothing on a path that has already spent a
            # provider deadline. The refusal is still reported rather than assumed if all twelve
            # go -- losing a row quietly is the fault this whole change is about.
            for attempt in range(12):
                # The digest is taken BEFORE the read, so anything landing between the two makes
                # the swap fail closed rather than pass on a copy that is already behind.
                digest = silence.digest_of(UNRECOGNISED)
                try:
                    with open(UNRECOGNISED, encoding="utf-8") as f:
                        rows = json.load(f)
                except Exception:
                    rows = {}
                if not isinstance(rows, dict):
                    rows = {}
                # RE-DERIVED FROM THE COPY JUST READ, on every attempt. `count` and `first_seen`
                # must come from the fresh dict, never be captured once from the first read --
                # that is the whole reason this re-applies the change rather than merely
                # retrying the write, so a concurrent record of the same fault is merged in
                # instead of being overwritten.
                r = rows.get(key) or {"bucket": bucket, "error": text,
                                      "first_seen": now, "count": 0}
                r["error"] = text
                r["last_seen"] = now
                r["count"] = int(r.get("count", 0)) + 1
                rows[key] = r
                os.makedirs(os.path.dirname(UNRECOGNISED), exist_ok=True)
                tmp = "%s.%d.%d.%d.tmp" % (UNRECOGNISED, os.getpid(),
                                           threading.get_ident(), attempt)
                with open(tmp, "w", encoding="utf-8") as f:
                    json.dump(rows, f, indent=1, sort_keys=True)
                landed, _why = silence.replace_if_unchanged(tmp, UNRECOGNISED, digest)
                if landed and _row_survived(key, r["count"]):
                    break
                # AND THE COMPARE-AND-SWAP IS READ BACK, because it is not actually atomic.
                # `silence.replace_if_unchanged` digests the target ONCE and then hands the
                # rename to `replace_retry`, whose denied-rename backoff can sleep for seconds
                # before the rename actually happens -- so content can land validated against a
                # digest that is by then long stale, and BOTH writers are told they landed.
                #
                # MEASURED, three processes recording forty rows each at a 50 ms cadence, out of
                # 120 rows: the old snapshot write kept 4-12; this compare-and-swap keeps 55-86;
                # the same test with the helper tightened to re-digest before each rename
                # attempt keeps 117-120. So the read-back below is NOT what makes this whole
                # today -- the remaining loss is the helper's, it is a wider fault than this
                # function (`workorders._mutate` and `endpoint.register` land the work-order
                # queue and the page registry through the same window), and it is filed as its
                # own order. The read-back stays because it turns a loss this function CAN see
                # into one more attempt instead of a silent drop, and because it is the belt to
                # that brace once the helper is repaired.
                if not landed:
                    # Only when the rename was REFUSED is `tmp` still there to remove; after a
                    # landed-but-clobbered write the file has already been renamed away, and
                    # removing it would note a cleanup failure that is not one.
                    try:
                        os.remove(tmp)
                    except OSError:
                        silence.note("cascade_bridge.py:unrecognised-tmp-cleanup")
                landed = False
                time.sleep(0.02 * (attempt + 1) * (1.0 + random.random()))
            if not landed:
                # The verdict is READ, not assumed. A denied replace is a return value here, not
                # an exception, so without this the recorder built to make failures visible was
                # itself the one place whose own failure left no mark (run #26).
                silence.note("cascade_bridge.py:record-unrecognised-denied")
    except Exception:
        # Total, but NOT untraceable. `pass` alone meant the recorder built to make failures
        # visible was the one place in the tree whose own failure left no mark anywhere -- the
        # ledger could quietly stop recording and the page would simply read "none". (run #26)
        silence.note("cascade_bridge.py:record-unrecognised")


def unrecognised_open(max_age_h=24):
    """The unrecognised failures seen recently, newest first. Read by `standards`.

    Aged deliberately: a fault that was investigated and resolved should stop appearing on the
    page on its own, and a fossil from two days ago is not evidence about now -- the same
    lesson the four 36-hour-old `Could not resolve host` rows taught on 2026-08-25.

    RE-TRIAGED ON READ, and this is the half that ageing cannot cover. "Unrecognised" is a
    statement about the CURRENT classifier, not a permanent property of a row. Every time
    `named_transient` or `pool_exhausted` learns a new phrase, every row already on disk that
    the new predicate would have absorbed keeps sitting in the ledger -- still inside the 24h
    window, still red, still unactionable -- because nothing re-asks the question. Found run
    #24: the file held 48 rows of which 36 were ordinary throttles the classifier repaired an
    hour earlier already understood, burying the one genuine unknown (`empty response`) 36 rows
    deep and holding a HIGH standard red on debris.

    Filtering here rather than pruning the file is deliberate. The row is evidence and stays on
    disk; what changes is only whether it is still an open QUESTION. And doing it on the read
    side makes the answer independent of WHICH process wrote the row and which version of the
    classifier that process had imported -- a long-lived job carries its launch-time import, so
    a write-side-only fix leaves a stale worker quietly refilling the ledger for hours.
    """
    try:
        with open(UNRECOGNISED, encoding="utf-8") as f:
            rows = json.load(f)
        cut = time.time() - max_age_h * 3600
        live = []
        for r in rows.values():
            if not isinstance(r, dict):
                continue
            if float(r.get("last_seen", 0)) < cut:
                continue
            err = r.get("error") or ""
            # RE-TRIAGE RE-ASKED THE CLASSIFIER BUT NEVER RE-ASKED THE PROVIDER. Run #28.
            #
            # The paragraph above is right that "unrecognised" is a statement about the current
            # classifier and not a property of the row -- and then re-ran only the PREDICATES
            # over the frozen write-time text. The unwrap (`provider_error`) was write-side
            # only, so a row that lost the unwrap race at the instant it was recorded keeps the
            # engine's `All 1 candidates failed: <label>` for its whole 24h life, even when the
            # provider's actual complaint is sitting in `bucket_state` and has been refreshed
            # every few minutes since. Measured this run: ten rows on the page carried the bare
            # wrapper at 5.6-5.9h old while the SAME buckets held fresh (2-12 minute old) real
            # causes -- Groq tokens-per-day at 199999/200000, SambaNova `rate_limit_exceeded`,
            # Z.AI `Insufficient balance or no resource package`. Every one of those is a phrase
            # the classifier below already understands. The ledger was not holding mysteries; it
            # was holding answered questions it never re-asked.
            #
            # So the unwrap moves to the read side too, for exactly the reason the docstring
            # gives for the predicates: the answer stops depending on which process wrote the
            # row, what it had imported, and whether it happened to lose a 180-second race.
            #
            # READ-ONLY AND WIDE, DELIBERATELY. This reaches no bench, no cooldown and no
            # routing decision -- `_bury` is decided at call time and is not involved here --
            # so the narrow 180s window that protects BENCHING from acting on a fossil is the
            # wrong window for EXPLAINING, which is lesson 15. The worst this can do is attach
            # an older true explanation to a row that would otherwise carry a wrapper that is
            # unactionable by design.
            if any(w in err.lower() for w in _WRAPPERS):
                _deep = provider_error(r.get("bucket"), max_age_s=max_age_h * 3600)
                if _deep and not any(w in _deep.lower() for w in _WRAPPERS):
                    r = dict(r)
                    r["error"] = _deep
                    r["unwrapped_on_read"] = True
                    err = _deep
                else:
                    # THE PIN AND THE ATTEMPT DO NOT ALWAYS AGREE AT n=1, AND THE DOCTRINE SAYS
                    # THEY DO. `_MULTI_CANDIDATE`'s comment exempts multi-candidate aggregates
                    # because "a multi-candidate call is not necessarily an attempt on the
                    # pinned bucket at all", and keeps `All 1 candidates failed` loud on the
                    # stated grounds that "there the pin and the attempt do agree". Measured
                    # against the live ledger this run, that premise is false: `github:free`
                    # was recorded against `Qwen3 Coder 480B (NVIDIA)`, `mistral:free` against
                    # `llama 3.3 70b (groq)`, and `gemini:models/gemini-2.5-flash` twice against
                    # groq llamas -- six of fourteen rows, all n=1.
                    #
                    # Those rows can NEVER be unwrapped, above or here, because the bucket named
                    # in them never made the call and so has no `bucket_state` row to consult.
                    # Worse, the row asserts a falsehood: a maintainer reads "github:free
                    # failed", goes and finds github healthy, and writes down "genuinely
                    # unexplained" -- which is what happened in run #26. Naming the mismatch is
                    # not a routing change; it is the row telling the truth about what it knows.
                    # Note `gemini:models/gemini-2.5-flash` is not in the live model set at all,
                    # which ties this straight to `model IDs their providers still serve`.
                    if not provider_error(r.get("bucket"), max_age_s=7 * 24 * 3600):
                        r = dict(r)
                        r["error"] = (
                            "%s -- NOTE: the pinned bucket `%s` has no provider row at all, so "
                            "the engine did not reach it; the label in this message is the "
                            "candidate that actually failed and it belongs to another bucket. "
                            "This row cannot be unwrapped by bucket, and it does NOT mean `%s` "
                            "is at fault." % (err, r.get("bucket"), r.get("bucket")))
                        r["pin_not_attempted"] = True
            if pool_exhausted(err) or named_transient(err) or empty_content(err):
                continue
            live.append(r)
        return sorted(live, key=lambda r: -float(r.get("last_seen", 0)))
    except Exception:
        silence.note("cascade_bridge.py:unrecognised-read")
        return []


def widen_candidates(models):
    """The candidate buckets for the exhausted-pool fallback, in config order.

    Locals never (one GPU wearing several names -- see `_alive`). Everything else is free, so
    there is nothing else to exclude: the paid-lane filter that used to live here was erased
    2026-08-25 along with the rest of the lane. Kept as a function rather than an inline
    comprehension so a regression check can exercise the real predicate instead of a paraphrase.
    """
    return [m for m in models if not m.bucket.startswith(LOCAL_PREFIX)]


# BUCKETS THE OWNER HAS STRUCK OFF (ruling 2026-08-25: "exnay them from the program").
#
# These four were measured being claimed ~40 times an hour with ZERO successes between them, and
# the cost was not merely wasted calls: `cloud_success_rate` sat at 37% against a 0.35 floor, and
# that floor is what holds the reader's throttle at 1-of-16 permits (M19/M35). Excluding them
# moves the measured rate to 45%.
#
# WHY THIS LIST EXISTS RATHER THAN THE EXISTING BENCH. `_DEAD` is a per-PROCESS dict with a
# 4-hour timeout, so roughly fifteen live processes each re-discover the same dead provider,
# each paying a deadline to learn it, over and over, for ever. And `dead_forever()` cannot help
# either: it keys off a proof file whose codes are provider-reported, and Z.AI answers an empty
# account with **HTTP 429** -- a throttle, by the letter -- so the router files it as busy rather
# than broken and comes straight back. A standing owner ruling is not a measurement and must not
# be re-derived from one; it lives in the source where a run can read it and cannot overturn it.
#
# TO RESTORE ONE: the owner rotates or refills the credential and deletes its line here. Nothing
# in the automation may remove an entry -- verify_math asserts the set is non-empty until then.
OWNER_EXCLUDED = {
    "zai:free":        "account empty; answers HTTP 429 so the router reads it as a throttle",
    "cohere:free":     "trial credits spent",
    "cloudflare:free": "HTTP 401 -- credential dead, needs rotation",
    "hyperbolic:free": "HTTP 401 -- credential dead, needs rotation",
}


def owner_excluded(bucket):
    """Is this bucket struck off by owner ruling? Matches on the bucket's provider prefix too.

    Prefix-tolerant because a bucket may be named `zai:free` in one view and `zai` in another,
    and a ruling that only bites on one spelling is a ruling that does not bite.
    """
    b = str(bucket or "").strip().lower()
    if b in OWNER_EXCLUDED:
        return OWNER_EXCLUDED[b]
    head = b.split(":", 1)[0]
    for k, why in OWNER_EXCLUDED.items():
        if head and head == k.split(":", 1)[0]:
            return why
    return None


def _alive(bucket):
    why = owner_excluded(bucket)
    if why:
        return False
    if bucket in dead_forever():
        return False
    if bucket.startswith(LOCAL_PREFIX):
        # The GPU is read.py's own fallback and reaching it through here would hide that fact
        # behind a "Cascade" label, with a 90-second deadline on a call that legitimately takes
        # minutes. Never claim it.
        return False
    with _DEAD_LOCK:
        until = _DEAD.get(bucket, 0)
        if until and until > time.time():
            return False
        if until:
            _DEAD.pop(bucket, None)
    return True


def _bury(bucket, seconds=None):
    # NO `_DEAD = {}` GUARD HERE. It used to open this function and it made every call throw.
    # `_DEAD` is a module-level dict that is never None, so the guard was dead -- but the mere
    # presence of an ASSIGNMENT to `_DEAD` in this scope made Python treat the name as local
    # throughout, so the `if _DEAD is None` that read it raised UnboundLocalError before
    # anything could be benched. The two call sites sit in a try/finally with no except, so the
    # error escaped the whole call: no provider was ever benched, exhausted and 401-ing
    # providers cycled back into rotation every few minutes taking a claim and a deadline each
    # time, and the deadline path raised instead of returning None for a clean GPU fallback.
    # Mutating a module-level dict needs no `global`; introducing one here would re-arm the trap.
    with _DEAD_LOCK:
        if seconds:
            _DEAD[bucket] = time.time() + seconds
            return
        n = _STRIKES.get(bucket, 0) + 1
        _STRIKES[bucket] = n
        _DEAD[bucket] = time.time() + min(MAX_BENCH, FIRST_BENCH * (2 ** (n - 1)))


def _clear(bucket):
    """A bucket that just answered is not down, whatever it did a minute ago."""
    with _DEAD_LOCK:
        _STRIKES.pop(bucket, None)
        _DEAD.pop(bucket, None)


def dead_buckets():
    """Which providers are currently benched, for a run to report rather than merely suffer."""
    now = time.time()
    with _DEAD_LOCK:
        return {b: round(t - now) for b, t in _DEAD.items() if t > now}


_METRICS = os.path.join(HERE, "state", "model_metrics.jsonl")


import threading as _threading

# Per-thread record of which buckets THIS call claimed, so a failed metric row can name them.
# Thread-local by construction: the readers run sixteen workers wide, and a module-global slot
# would attribute one worker's failure to another's bucket -- a wrong name is worse than none.
_TRIED = _threading.local()


def _tried_reset():
    _TRIED.names = []


def _tried_add(bucket):
    if not hasattr(_TRIED, "names"):
        _TRIED.names = []
    if bucket and bucket not in _TRIED.names:
        _TRIED.names.append(str(bucket))


def _tried():
    return list(getattr(_TRIED, "names", []) or [])


def _metric(row):
    """Same ledger pipeline.ask writes, cloud lane. Ollama reports token counts; a stream
    through Cascade does not, so these rows carry character counts and the aggregator keys on
    which fields exist. Append-only, best-effort -- a metrics failure must never cost a call."""
    # ONE SYSCALL, NOT A BUFFERED WRITE (m62): five processes share this file and a buffered
    # append can be split mid-line, producing rows that parse as neither writer's.
    # BEST-EFFORT, AND SAID SO RATHER THAN ASSUMED. The verdict is deliberately not allowed to
    # affect the call -- the docstring's "a metrics failure must never cost a call" stands, and
    # nothing here raises or returns early. `append_line` already notes its own failure under
    # `silence.py:append_line`, so this is not a silent path today; what that generic tag cannot
    # say is WHICH ledger stopped accepting rows, and there are several appenders. Naming this
    # one costs nothing and is what makes a thin hour distinguishable from an unwritten one when
    # somebody later asks why the pool looked fast.
    if not silence.append_line(_METRICS, json.dumps(row)):
        silence.note("cascade_bridge.py:metric-append-denied")


def ask(system, prompt, schema=None, pool="coding", temperature=0.1, timeout=75, pin=None,
        max_attempts=None, served=None):
    """Instrumented wrapper: wall time, outcome and answering model per call, so 'the pool got
    slow' is a measurement rather than a feeling. The real work is _ask_call.

    `max_attempts` and `served` are pass-throughs for `prove()`, which is asking a DIFFERENT
    question from every other caller here: not "get me an answer from the pool" but "did THIS
    bucket answer". Both default to the behaviour every existing caller already has -- no cap on
    the engine's walk, and nothing recorded about who served. See `_ask_call`."""
    t0 = time.time()
    _tried_reset()
    got = _ask_call(system, prompt, schema=schema, pool=pool, temperature=temperature,
                    timeout=timeout, pin=pin, max_attempts=max_attempts, served=served)
    _metric({"at": round(t0, 1), "tag": "cascade:" + pool, "s": round(time.time() - t0, 2),
             # `.get` ON WHATEVER PARSED, NOT ON WHATEVER IS TRUTHY. `_extract_json` will
             # happily return a list, bool or number from a fenced reply, `_ask_call` only
             # tags `_via` when the payload is a dict, and `(got or {})` then evaluates to the
             # non-dict itself -- so a provider answering ```json\n[1,2]\n``` crashed the
             # metrics line with AttributeError and took the whole call with it.
             "ok": got is not None,
             # A FAILURE MUST NAME THE BUCKET IT BURNED (owner finding, 2026-08-25).
             #
             # `_via` is stamped by the ANSWERING model, so on failure this field was "" and the
             # row was unattributable. Measured when found: **426 cascade calls in six hours,
             # every one a failure, every one recorded as bucket "?"** -- so the question the
             # owner's own ruling queue asks ("which keys are dead and still being claimed?")
             # could not be answered from the metrics at all, only from a provider's error text
             # if somebody happened to be reading a log at the right moment.
             #
             # `_LAST_TRIED` is filled by `_ask_call` with the buckets it actually claimed, so a
             # failed row now says which providers spent the deadline. Thread-local because the
             # readers run sixteen workers wide and a shared slot would attribute one thread's
             # failure to another thread's bucket -- which is worse than no attribution.
             "model": ((got.get("_via") or "") if isinstance(got, dict)
                       else ("tried:" + ",".join(_tried()) if _tried() else "")),
             "tried": _tried(),
             "in_chars": len(system) + len(prompt),
             "out_chars": len(json.dumps(got, default=str)) if got is not None else 0})
    return got


def _ask_call(system, prompt, schema=None, pool="coding", temperature=0.1, timeout=75, pin=None,
              max_attempts=None, served=None):
    """One structured call through Cascade. Returns a parsed dict, or None.

    Mirrors pipeline.ask() so a caller can swap transports without changing anything else.

    The call CLAIMS a bucket before dispatching and releases it after. Without that, concurrent
    workers all read the same stale headroom -- usage is only recorded on completion -- and pile
    onto one meter, which costs a 429 and, worse, teaches the router a lower cap permanently.

    `max_attempts` CAPS THE ENGINE'S WALK, AND A PIN IS NOT A CAP. This is the correction behind
    order c810cf64d278. `Router.candidates(pool, pinned)` returns `[the pinned model] + THE
    REST OF THE POOL` -- its own comment says "a pinned model still gets the rest of the pool as
    backup" -- and `Engine.stream_chat` walks that whole list until something answers, because
    its own default is `max_attempts or config or len(candidates)`. That is exactly right for
    WORK, where any answer will do, and exactly wrong for a MEASUREMENT of one bucket: pin
    `chutes:free`, have it 402, and `mistral:free` serves the call. Passing 1 here makes the
    walk stop at the pinned model. `None` is the engine's own default, so every existing caller
    is byte-for-byte unchanged.

    `served`, when a caller passes a dict, is filled in with WHO ACTUALLY SERVED and WHY IT
    FAILED -- `model_id`, `label`, `bucket`, `outcome`, `error`, `failovers`. The information
    was already flowing through `pump` and was thrown away everywhere except `_via`: the
    `failover` events, which carry the provider's own HTTP status and body, were not even read.
    A measurement that cannot name its own subject is not a measurement.
    """
    if served is not None:
        served.clear()
        served.update({"asked": pin, "outcome": "not started", "model_id": None,
                       "label": None, "bucket": None, "error": "", "failovers": []})
    e = thread_engine()
    if not e:
        if served is not None:
            served["outcome"] = "no engine"
        return None
    # A BUCKET THAT MISSED ITS DEADLINE IS OUT FOR A WHILE.
    #
    # Two providers on this pool answer HTTP 402 -- an account at zero -- and the router drops
    # those the moment they say so. The expensive ones are the buckets that say nothing at all:
    # the claim succeeds, the stream never yields, and the call burns its whole deadline before
    # the caller can try anyone else. Sixteen workers doing that spent five minutes to make
    # eleven calls on a pool that had just served eight in three seconds.
    #
    # So a timeout is remembered. The bucket is skipped for DEAD_FOR seconds and the claim is
    # retried, which costs one extra claim and buys back the whole worker.
    pinned = None
    if pin:
        # A named model, claim or no claim. `prove()` needs to ask ONE bucket whether it works,
        # and the router's job is the opposite -- to pick for you. Without this the prover would
        # test whichever bucket happened to be least busy, twenty-eight times.
        pinned = next((m for m in _ROUTER.models if m.id == pin), None)
        if pinned is None:
            # NAME THE REFUSAL. Every other exit from this function writes `served["outcome"]`,
            # and this one left the placeholder `"not started"` standing -- so a caller pinning
            # a model id that no longer exists in the config (a renamed or retired model, which
            # this pool sees regularly) read back a dict saying the call had never begun, which
            # is indistinguishable from the engine being absent. `prove()` and `try_disabled()`
            # are precisely the callers that pass a pin, and both take their whole verdict from
            # this dict; a retired model id would otherwise be recorded as an untried bucket
            # rather than as a configuration fault. Found by sweep42-batch05.
            if served is not None:
                served["outcome"] = "no such model"
                served["error"] = "pinned model id %r is not in the router's model list" % (pin,)
            return None
        _ROUTER.reserve(pinned)
        # SYMMETRY WITH THE OTHER TWO RESERVE SITES (order d5012fbc73c1). Nothing is lost today
        # -- both pinning callers, `prove()` and `try_disabled()`, take their attribution from
        # the `served` dict -- but a third caller passing `pin=` without `served=` would write
        # the same blank metric row this order was filed about, and the cost of preventing that
        # is one line.
        _tried_add(pinned.bucket)
    for _ in range(4 if pin is None else 0):
        claimed = _ROUTER.claim(pool, 1)
        if not claimed:
            break
        cand = claimed[0]
        # THE ROUTER NEVER HANDS OUT A LOCAL BUCKET. Cascade's pool lists three ollama models,
        # and on a 10GB card a claim on any of them asks the server to load a model it cannot
        # fit beside whatever is resident -- measured this afternoon at 108 calls in fifteen
        # minutes, zero ok, and Ollama answering everyone "maximum pending requests exceeded"
        # once its queue filled. Every caller of this bridge already has its own local
        # fallback (read._local picks the ONE model that fits whole and benches it when it
        # stops answering); the router adding three more local claimants was pure queue flood.
        if cand.bucket.startswith(LOCAL_PREFIX):
            _ROUTER.release(cand)
            continue
        if _alive(cand.bucket):
            pinned = cand
            _tried_add(cand.bucket)
            break
        _ROUTER.release(cand)
    if pinned is None and pin is None:
        # THE POOL IS NARROWER THAN THE ACCOUNT. Widen before giving up.
        #
        # The router only routes models carrying a pool tag, and on this configuration that is
        # ten models out of forty-two. `cloud_buckets("coding")` therefore reports FOUR buckets
        # -- cerebras, chutes, deepinfra, huggingface -- and every one of those four is currently
        # answering HTTP 402. Meanwhile the account holds working credentials for roughly
        # twenty-six more (cohere, mistral, nvidia, zai, github, cloudflare, sambanova, five
        # Geminis, together, hyperbolic, nebius, kluster, bigmodel, moonshot, dashscope, novita,
        # ovh, ai21), and the prover reaches them -- it pins by name and skips the pool entirely,
        # which is exactly why POOL_PROOF.json cheerfully reported "7 answering" while `ask`
        # returned None in 0.0 seconds for hours.
        #
        # Two views of the same pool disagreeing is the defect this project keeps meeting: the
        # measurement was taken down a path the work never travels. So when the tagged pool is
        # exhausted, fall through to ANY alive remote model. Locals stay excluded for the reason
        # below -- they are one GPU wearing several names, and letting a cloud call land there
        # silently is how thirty-eight of seventy-five calls once went to a reloading card.
        # PROOF WINNERS FIRST. The models list is config order, and config order is a
        # graveyard tour: the dashboard measured ~100 calls across gemini/zai/groq/openrouter
        # for ONE success while mistral sat at 86-for-86. Every worker walked the same dead
        # buckets, paid a failure and a 60s bench on each, and only then reached a live one --
        # which is most of the difference between the pool's 952 calls/hour and the read's
        # 0.36 chunks/s. POOL_PROOF.json already knows who actually answers; start there.
        answering = set()
        try:
            with open(PROOF, encoding="utf-8") as _f:
                answering = {r.get("bucket") for r in json.load(_f)
                             if isinstance(r, dict) and r.get("verdict") == "answers"}
        except Exception:
            silence.note("cascade_bridge.py:widen-proof")
        # EVERY CANDIDATE HERE IS FREE. The paid burst lane that used to be read, gated and
        # counted at this point was erased 2026-08-25 (owner ruling); see the note beside
        # LOCAL_PREFIX for why the machinery went rather than just the switch. This branch can
        # no longer spend money, so there is no cap to enforce and no counter to maintain.
        ranked = sorted(widen_candidates(_ROUTER.models),
                        key=lambda m: (m.bucket not in answering))
        # ROTATE. First-alive-wins pinned EVERY call to the same front-ranked bucket, and the
        # whole pool serialised through one provider's per-minute cap -- 20 buckets with quota
        # idle while mistral carried everything at 10 RPM. The dashboard read "significant drop
        # in call rate, still a lot of models available", which is exactly what a fallback with
        # no rotation looks like from outside. The offset spreads consecutive calls across the
        # alive set; the sort still puts proven answerers ahead of unproven ones.
        if ranked:
            # Locked: concurrent workers reading the same cursor both rotated to the same
            # bucket, quietly re-creating the pinning the rotation exists to prevent.
            with _RR_LOCK:
                off = _WIDEN_RR[0] % len(ranked)
                _WIDEN_RR[0] += 1
            ranked = ranked[off:] + ranked[:off]
            ranked.sort(key=lambda m: (m.bucket not in answering))
        for m in ranked:
            if not _alive(m.bucket):
                continue
            try:
                _ROUTER.reserve(m)
            except Exception:
                silence.note("cascade_bridge.py:widen-reserve")
                continue
            # THE WIDEN PATH NAMES ITS BUCKET TOO (order d5012fbc73c1). The tagged-pool claim
            # loop above calls `_tried_add(cand.bucket)`; this branch reserved, pinned and
            # returned without it, so `_tried()` was empty for every widened call and `ask()`'s
            # metric row wrote `"model": ""` and `"tried": []`. That is the exact unattributable
            # row the comment beside `"model"` records as already fixed -- 426 cascade calls in
            # six hours, every one a failure, every one written down as bucket "?" -- surviving
            # on the branch that carries nearly all the traffic, since this file's own comment
            # above explains the tagged pool is four buckets and all four were answering 402.
            _tried_add(m.bucket)
            pinned = m
            break

    if pinned is None:
        # NO CLOUD BUCKET IS FREE, SO SAY SO. Calling stream_chat without a pin lets the engine
        # choose, and the engine happily chooses a LOCAL model -- which meant "Cascade" calls
        # were quietly running on the same GPU the caller keeps as its own fallback, erroring
        # while the card reloaded, and burning a 75-second deadline each time. Thirty-eight of
        # seventy-five calls in one ten-minute window went that way.
        #
        # Returning None hands the decision back to the caller, which knows the GPU is a real
        # resource rather than a hiding place.
        if served is not None:
            served["outcome"] = "no bucket free"
        return None
    # INVARIANT, STATED ONCE (order 8b0338b019ce): `pinned` is a non-None router Model from HERE
    # to the end of this function -- the only way out with `pinned` still None was the `return
    # None` immediately above. Every `if pinned:` / `pinned and ...` guard below this point
    # (there are eight) is therefore belt-and-braces, not a live condition; none of them can be
    # False. That is deliberate, not dead code -- read them as documentation of which branches
    # touch the pinned bucket, not as a reachability check.
    if served is not None:
        served["dispatched_to"] = pinned.id
        served["dispatched_bucket"] = pinned.bucket
    # THE TRY OPENS AT THE RESERVE, NOT AT THE STREAM (order e0b4a02c5133). The reservation is
    # taken well above here -- `_ROUTER.reserve(pinned)` on the pin path and `_ROUTER.reserve(m)`
    # on the widen fallback -- while this `try`'s `finally` used to start only at
    # `done.wait(timeout)`, so everything in between ran with a live reservation and no release.
    # Two faults in that gap are real rather than theoretical: `json.dumps(schema)` raises
    # TypeError on a schema carrying a non-serialisable value, and `Thread.start()` raises
    # RuntimeError when the process cannot make a thread -- and this module runs sixteen workers
    # wide on a host that has already been recorded running out of ephemeral ports. A leaked
    # reservation never heals: it permanently narrows the router's view of that bucket's
    # headroom, shrinking the pool this file repeatedly calls the binding constraint. Opening
    # here makes the release unconditional from the moment the reservation exists. The
    # `if pinned is None: ... return None` exit above stays OUTSIDE, because nothing is reserved
    # on that path.
    try:
        _pace(pinned.bucket)
        sys_msg = system
        if schema:
            sys_msg = (system + "\n\nReply with JSON ONLY, no prose and no code fence, "
                       "matching this schema exactly:\n" + json.dumps(schema))
        messages = [{"role": "system", "content": sys_msg},
                    {"role": "user", "content": prompt}]
        out, answered, done = [], None, threading.Event()
        # `failovers` keeps the model LABEL for the record; `reasons` is the provider's disposition
        # ALONE, and the split is not tidiness. The label is a display string that contains the
        # provider's NAME, and every classifier downstream matches provider names as words --
        # the WAF test used to look for a bare "cloudflare", which appears in the label of every
        # Cloudflare model whatever went wrong. Feeding a labelled string to a classifier makes the
        # label decide the verdict.
        #
        # THE RECEIVING SIDE IS NOW CLOSED TOO (order 62f4b7caae73): `client_rejection` requires the
        # provider name to arrive WITH a challenge word, so the two paths that still deliver
        # provider-naming text to a classifier -- `_why = raw` keeping the engine's
        # "All 1 candidates failed: <label>" wrapper, and `provider_error()` returning a
        # `last_error` a provider may open with its own name -- can no longer excuse a real refusal.
        # This split stays as it is: keeping the reason clean at the source is still the better
        # discipline, and the guard below it is the belt to that pair of braces.
        box = {"answered": None, "answered_id": None, "failed": False,
               "failovers": [], "reasons": []}

        # THE NEW KEYWORD IS ONLY SENT WHEN IT IS ASKED FOR. `Engine.stream_chat` grew
        # `max_attempts` some time ago and every call here goes through one function, so passing it
        # unconditionally would make EVERY call in the library depend on the age of whatever
        # `CASCADE_HOME` points at -- a `TypeError` on an older engine would be a total outage of the
        # cloud lane, bought for a parameter only `prove()` uses. Absent, the engine applies its own
        # default, which is what this call has always got.
        _stream_kw = {"pool": pool, "temperature": temperature,
                      "pinned": pinned.id if pinned else None}
        if max_attempts is not None:
            _stream_kw["max_attempts"] = max_attempts

        def pump():
            try:
                for ev in e.stream_chat(messages, **_stream_kw):
                    t = ev.get("type")
                    if t == "delta":
                        out.append(ev.get("text") or ev.get("delta") or "")
                    elif t == "model":
                        box["answered"] = ev.get("label") or ev.get("model_id")
                        # THE ID AS WELL AS THE LABEL. `_via` wants the friendly label; deciding
                        # WHICH BUCKET served needs the model id, which is the only field that maps
                        # back to `Model.bucket` without guessing at a display string.
                        box["answered_id"] = ev.get("model_id")
                    elif t == "failover":
                        # THE EVENT THIS LOOP USED TO STEP OVER IN SILENCE, and the reason
                        # POOL_PROOF.json has never once held a bucket-specific reason. Each
                        # failover carries the PROVIDER's own disposition -- `HTTP 401 ...`,
                        # `removed from the pool - no such model (HTTP 404)`, `rate limited` --
                        # while the aggregate that arrives at the end says only "All N candidates
                        # failed". The classifier in `dead_forever` was written against words that
                        # only ever existed in these events.
                        _r = str(ev.get("reason") or "")[:200]
                        box["failovers"].append("%s: %s" % (ev.get("from") or "?", _r))
                        if _r:
                            box["reasons"].append(_r)
                    elif t == "error":
                        box["failed"] = True
                        box["error"] = str(ev.get("error") or ev.get("text") or "")[:300]
                        return
            except Exception as exc:
                silence.note("cascade_bridge.py:stream-pump")
                box["failed"] = True
                # THE TEXT IS THE DIAGNOSIS, AND IT USED TO BE THROWN AWAY HERE.
                # A provider whose failure ARRIVES AS AN EXCEPTION rather than as a `type:"error"`
                # event left `box["error"]` unset, so the auth classifier below matched the empty
                # string, never fired, and the bucket took no bench at all. That is why the bench
                # this file's own comment promises -- "benched for hours so the rotation contains
                # only providers that could plausibly answer" -- was not reaching `cloudflare` and
                # `hyperbolic`, which hold hard 401s and were still being re-claimed every few
                # minutes on 2026-08-25. Recording the text is what makes the classifier reachable.
                box["error"] = str(exc)[:300]
            finally:
                done.set()

        # A HARD DEADLINE, because a provider going quiet must not take a worker with it.
        #
        # Seventy-five seconds, against a healthy call that returns a 10,000-character extraction in
        # one to four. The deadline is not a timeout for slow work -- it is the cost of discovering a
        # SILENT bucket, and it has to sit well above the worst honest queueing a free tier does
        # under sustained load, or the run benches its own best providers for being busy.
        #
        # Eight workers went into this call and none came out in two minutes, while the same call
        # alone returned in eight seconds. Whatever a given free tier does when it is unhappy --
        # throttle, hold the socket, never answer -- the run cannot be hostage to it. The stream is
        # pumped on its own thread and abandoned at the deadline; the caller falls back to the GPU,
        # which is slower and always answers.
        #
        # The abandoned thread is a daemon and will finish or die with the process. Letting it leak
        # is the lesser fault: the alternative is a reader that stops without saying so.
        th = threading.Thread(target=pump, daemon=True)
        th.start()
        finished = done.wait(timeout)
        if not finished:
            silence.note("cascade_bridge.py:deadline")
            if pinned:
                _bury(pinned.bucket)
            if served is not None:
                served["outcome"] = "deadline"
                served["error"] = "no reply within %ss" % timeout
                served["failovers"] = list(box["failovers"])
            return None
        if box["failed"]:
            # AN AUTH FAILURE IS NOT A BUSY SIGNAL.
            #
            # A 401 or 402 will still be a 401 or 402 in sixty seconds, and in ten minutes, and
            # tomorrow -- it needs a human with an account page. Treating it like contention
            # meant `cloudflare` and `hyperbolic` cycled back into rotation every few minutes to
            # fail again, taking a claim and a deadline with them each time. Benched for hours
            # so the rotation contains only providers that could plausibly answer.
            # A SPENT ACCOUNT IS AS PERMANENT AS A BAD KEY, AND SAYS SO IN WORDS, NOT CODES.
            # The list below was HTTP-status-shaped, so a provider that returns 200 with a
            # billing complaint in the body slipped through it. `zai:free` answers
            # `{"code":"1113","message":"Insufficient balance or no resource package. Please
            # recharge."}` -- no 401, no 402, no "credentials" -- and was therefore re-claimed
            # forever while reporting full headroom. `403` was missing for the same reason.
            # Matching is case-folded because providers do not agree on capitalisation.
            # THE STATUS CODES ARE MATCHED ON WORD BOUNDARIES, THE WORDS AS SUBSTRINGS.
            # A bare `"403" in err` also matches the 403 inside a request id like
            # `req_4403abc` or a trace hash, and the penalty for a false positive here is
            # FOUR HOURS of bench on a provider that was merely busy -- the opposite of the
            # bug this classifier was added to fix, and worse, because it shrinks a pool that
            # is already the binding constraint. `\b` refuses a match with a digit either
            # side. The prose markers stay plain substrings: they are distinctive enough that
            # an accidental hit is not a realistic failure, and providers word them freely.
            # TWO VARIABLES, DELIBERATELY. `err` is FOLDED FOR CLASSIFICATION; `raw` is the
            # provider's own words, kept intact for the ledger. Run #26 found the ledger holding
            # `Every model in this pool is rate limited or unconfigured.` and
            # `every model in this pool is rate limited or unconfigured.` as TWO permanent rows
            # on eight separate buckets, because this line folded the text and
            # `record_unrecognised` de-duplicates on EXACT text -- so a code change that started
            # folding split every pre-existing row from its own successor.
            #
            # That is m132's lesson recurring one letter over. m132 named the two engine
            # wordings for "answered with nothing" and stopped there; case is simply a THIRD
            # spelling of the same fault, and the de-duplication key was the thing that needed
            # fixing, not the vocabulary. `record_unrecognised` now folds its KEY (see there).
            #
            # Folding the recorded TEXT is separately lossy and worth refusing on its own:
            # `record_unrecognised`'s whole premise is "enough text to classify it", and a
            # provider's complaint carries case-bearing identifiers -- model ids, `request_id`,
            # `org_01KYDH...` -- that a maintenance run may have to quote back to the provider.
            raw = " ".join((box.get("error") or "").split())
            err = raw.lower()
            # UNWRAP FIRST. If the engine handed us one of its aggregate messages, the real
            # reason is not in this string at all -- it is the provider's own last error, which
            # Cascade recorded in its scratch DB at the same moment. Without this the classifier
            # below is judging the words "All 1 candidates failed: GLM 4.7 Flash (Z.AI)", which
            # will never match anything, forever.
            # DECIDE "WAS THE WHOLE POOL DRY" ON THE RAW TEXT, BEFORE THE UNWRAP DESTROYS IT.
            #
            # Caught the same run this branch was written, by the sweep agent auditing it.
            # `All 11 candidates failed: ...` is a fact about the ENGINE'S WALK, and it lives
            # only in the raw message -- once `err` is replaced by the pinned bucket's own last
            # error, that fact is gone and `pool_exhausted(err)` below can never see it.
            #
            # Worse than losing the classification: it could BENCH ON THE WRONG EVIDENCE. A
            # multi-candidate call is not necessarily an attempt on the pinned bucket at all
            # (the ledger showed pin `groq:openai/gpt-oss-20b` against candidate label
            # `Llama 3.3 70B (Groq)`), so unwrapping it could pull up a neighbouring
            # "insufficient balance" and hand this bucket a FOUR HOUR bench for a call that
            # failed because the pool was empty. That is m103's harm exactly -- shrinking the
            # pool that is already the binding constraint -- reached by a new road.
            exhausted = pool_exhausted(err)
            if pinned and not exhausted and any(w in err for w in _WRAPPERS):
                deeper = provider_error(pinned.bucket)
                if deeper:
                    raw, err = deeper, deeper.lower()
            # HOISTED TO `permanent_refusal`, which is the point of the change and not a tidy-up.
            # This test lived as a tuple and a regex inline in a 300-line branch, so the only way
            # to check a wording was to make a live cloud call and lose a claim finding out --
            # which is why the list stayed wrong for a shift while `zai:free` was re-claimed
            # ninety times. `pool_exhausted`, `named_transient` and `empty_content` are all
            # module-level predicates for exactly this reason; this one was the odd one out.
            # Now both directions can be asserted offline against the measured strings.
            if pinned and not exhausted and permanent_refusal(err):
                _bury(pinned.bucket, AUTH_BENCH)
            elif pinned and (exhausted or named_transient(err)):
                # RECOGNISED, AND ALREADY COUNTED ELSEWHERE. A throttle is not a mystery: it is
                # the most ordinary thing a free-tier pool says, it is tallied in the throughput
                # panel and in `usage.outcome='rate_limited'`, and writing it into the
                # unrecognised ledger buried the one genuine unknown under 121 known ones on the
                # day the ledger was created. Named here, deliberately not benched -- see
                # `named_transient`.
                pass
            elif pinned:
                # AN UNRECOGNISED FAILURE IS A THING TO INVESTIGATE, NOT A THING TO ABSORB.
                # Owner ruling 2026-08-25. Until now this branch simply fell through to
                # `return None`: the call failed, the reason was discarded, and the only trace
                # was a tick in the throughput panel's refusal count. That is how a pool sits at
                # 64 calls/hour against a floor of 900 with every sub-standard green -- the
                # failure was never nameless, it was just never written down.
                # `silence.note` cannot serve here: it records the exception currently being
                # handled, and by this point there is no live exception, only a string.
                # `err`, not `box["error"]` -- this records the UNWRAPPED text where one was
                # found, so what lands on the page is the provider's actual complaint rather
                # than the engine's "All 1 candidates failed", which is unactionable by design.
                # ONE WINDOW WAS SERVING TWO QUESTIONS WITH DIFFERENT ANSWERS.
                #
                # `provider_error`'s 180s gate is exactly right for BENCHING: claiming a stale row
                # would bench a live provider for four hours on a fossil, which is m103's harm.
                # It is far too narrow for EXPLAINING. Run #26 measured the biggest open row --
                # `groq:openai/gpt-oss-120b: All 1 candidates failed: GPT-OSS 120B (Groq)`, thirty
                # occurrences holding a HIGH standard red -- and the cause was sitting in
                # `bucket_state` the whole time: a Groq tokens-per-day rate limit. During a burst
                # the aggregate arrives more than 180s after the provider row that explains it, so
                # the unwrap above found nothing and the ledger recorded the engine's wrapper,
                # which is unactionable by design and can never be classified by anyone.
                #
                # So: a SECOND, WIDER lookup, for the recorded text only. It reaches no bench, no
                # cooldown and no routing decision -- `_bury` is above and already decided -- and
                # it is used only when the narrow one found nothing, so it can never override a
                # fresh reason with an older one. The worst it can do is attach an hour-old
                # explanation to a row that would otherwise have had none at all.
                _text = raw or box.get("error") or ""
                if pinned and any(w in _text.lower() for w in _WRAPPERS):
                    _older = provider_error(pinned.bucket, max_age_s=6 * 3600)
                    if _older and not any(w in _older.lower() for w in _WRAPPERS):
                        _text = _older
                record_unrecognised(pinned.bucket, _text)
            if served is not None:
                served["outcome"] = "failed"
                served["failovers"] = list(box["failovers"])
                # THE WRAPPER IS NOT A REASON, so do not report one as though it were. `All 1
                # candidates failed: GPT-OSS 120B (Groq)` names the engine's walk and carries
                # no disposition -- no status code, no provider wording. That aggregate is
                # what has been reaching `POOL_PROOF.json` for its whole life (as the string
                # `no answer`, once `prove` had thrown even this much away), which is why
                # `dead_forever`'s 401/402/404/410 test has never had anything to match. The
                # failover events hold the provider's own status line; prefer them.
                _why = raw
                if (not _why or any(w in _why.lower() for w in _WRAPPERS)) and box["reasons"]:
                    _why = "; ".join(box["reasons"])
                served["error"] = (_why or "")[:300]
            return None
        if pinned:
            _clear(pinned.bucket)
        answered = box["answered"]
        if served is not None:
            served["outcome"] = "answered"
            served["label"] = box["answered"]
            served["model_id"] = box["answered_id"]
            served["bucket"] = _bucket_of(box["answered_id"] or box["answered"])
            served["failovers"] = list(box["failovers"])
    finally:
        if pinned:
            _ROUTER.release(pinned)
    _reply = "".join(out)
    got = _extract_json(_reply)
    if got is None:
        # A REPLY THAT WOULD NOT PARSE IS A FAILURE, AND UNTIL NOW IT WAS AN INVISIBLE ONE.
        #
        # `served["outcome"]` is set to "answered" a dozen lines above, the moment the stream
        # closes -- which is true of the TRANSPORT and false of the CALL. If the provider
        # answered with prose, an apology, a truncated fence or an empty string, `_extract_json`
        # returns None, this function returns None, and the `served` dict the caller reads still
        # says "answered" with no error text and the reply itself discarded. So the one failure
        # mode that is entirely the MODEL's fault -- as opposed to the account's or the
        # network's -- was the only one this module could not name, and a caller measuring
        # provider quality would score it as a success that mysteriously produced nothing.
        #
        # Measured 2026-09-02: `selftest()` reported a bare "live call -> FAILED" against a pool
        # whose buckets were answering fine, and neither the metrics row nor `served` held
        # anything to distinguish an unparseable answer from a dead account.
        #
        # The reply is recorded UNTRUNCATED. It is the evidence, this is the only place it
        # exists, and Hard Rule 0 applies to the diagnostic as much as to the report.
        if served is not None:
            served["outcome"] = "unparseable reply"
            served["error"] = ("model answered but the reply is not JSON matching the schema; "
                               "raw reply follows: " + _reply)
        silence.note("cascade_bridge.py:unparseable-reply")
        return None
    if isinstance(got, dict):
        got["_via"] = answered or "cascade"
    return got


def selftest():
    if not available():
        print(f"cascade not found at {CASCADE}")
        return 1
    engine()
    print(f"engine built. pools: {pools()}")
    ready = [m.label for m in _ROUTER.models if _ROUTER.provider_ready(m)[0]]
    print(f"models configured: {len(_ROUTER.models)}   provider-ready: {len(ready)}")
    # EVERY ONE OF THEM (order c48c3de407d8, Hard Rule 0). This was `ready[:12]` with no "and N
    # more" anywhere, and `selftest` is the command a person runs precisely to find out WHICH
    # providers are live -- roughly forty-two models are configured here with about twenty-six
    # holding working credentials, so the cut fired on every ordinary run and the reader had
    # only the count above to infer from that anything had been dropped. Printing the lot costs
    # a couple of dozen lines at this scale, which is cheaper than a truncated answer to the one
    # question the command exists to answer.
    for lab in ready:
        print(f"   {lab}")
    schema = {"type": "object", "properties": {"feats": {"type": "array", "items": {
        "type": "object", "properties": {"sentence": {"type": "string"},
                                         "axis": {"type": "string"}},
        "required": ["sentence", "axis"]}}}, "required": ["feats"]}
    # ASK FOR THE DIAGNOSIS, NOT JUST THE VERDICT (order filed 2026-09-02, sweep42-batch05).
    #
    # `selftest` is the command a person runs to find out whether the cloud lane works, and for
    # its whole life it could answer only "OK" or "FAILED" -- while `_ask_call` had, sitting
    # right there behind an optional argument this call did not pass, the bucket it dispatched
    # to, the provider's own status line, and every failover on the way. `allsweep` grades this
    # command's exit code as a battery row, so a red row said a subsystem was broken and gave
    # the reader nothing whatsoever to act on. Measured this shift: three consecutive FAILED
    # runs, cause invisible; with `served` passed it took one call to see a Groq tokens-per-day
    # quota at 198,972 of 200,000.
    served = {}
    got = _ask_call("You extract feats. Copy sentences verbatim.",
                    "ENTITY: Test\n\nHe lifted the boulder over his head and hurled it across "
                    "the valley. He liked tea.\n\nReturn feats.", schema, served=served)
    # `if got` is TRUTHINESS, not type. `_extract_json` can return a list, and a non-empty list
    # is truthy -- so this line would raise AttributeError on exactly the reply shape the metrics
    # line above was fixed for. Same bug, same file, one path further down, and the AST check in
    # verify_math counts BOTH reads. Guarded the same way rather than differently.
    _via = (got.get("_via") if isinstance(got, dict) else None)
    print(f"\nlive call -> {'OK via ' + str(_via) if got else 'FAILED'}")
    if got:
        # UNCUT (Hard Rule 0). This was `[:400]`, in the same function whose `ready[:12]` cap the
        # comment above records as removed for exactly this reason. A self-test's whole output is
        # the evidence it exists to produce, and this answer is one small object.
        print(json.dumps({k: v for k, v in got.items() if k != '_via'}, indent=1))
    else:
        # WHY, NOT JUST THAT. Everything below came back in `served` and was previously thrown
        # away -- see the note at the call site.
        print(f"   outcome        : {served.get('outcome')}")
        print(f"   dispatched to  : {served.get('dispatched_to')}"
              f"  (bucket {served.get('dispatched_bucket')})")
        if served.get("error"):
            print(f"   provider said  : {served['error']}")
        for _f in served.get("failovers") or []:
            print(f"   failover       : {_f}")
        if not served.get("error") and not served.get("failovers"):
            print("   (no provider text was recorded — this is itself a fault, "
                  "report it with the outcome above)")
    return 0 if got else 1


# --------------------------------------------------------------------------- proving the pool

def prove(pool="coding", timeout=45):
    """Send one tiny call to EVERY bucket and record which actually answer.

    "27 buckets with headroom" was fiction. Headroom is what a bucket reports about its own
    meters; it says nothing about whether the key works, whether the model still exists, or
    whether the provider will accept a request at all. Two buckets were returning HTTP 401 on
    every attempt while reporting 100% of their daily allowance untouched, and the standards
    floored on the fictional number.

    One three-token call per bucket settles it. The result is fact rather than inference, and a
    bucket that fails here is benched long enough to stop costing every claim that follows.

    THE CALL IS ISOLATED TO THE BUCKET UNDER TEST, WHICH IT WAS NOT (order c810cf64d278).
    Pinning names a FIRST candidate, not an only one. `Router.candidates(pool, pinned)` returns
    `[the pinned model] + the rest of the pool` -- "a pinned model still gets the rest of the
    pool as backup", in its own words -- and `Engine.stream_chat` walks that list to the end
    unless capped. So `prove` asked `chutes:free`, `mistral:free` answered, and the row said
    `chutes:free -> answers`. A health check that any healthy neighbour can pass on your behalf
    is not a health check; it is the "check that cannot fail" this project's whole ledger is
    about, sitting in the module that decides where every call goes.

    Two changes, and they are the same change from both ends: `max_attempts=1` stops the walk at
    the bucket being asked, and the SERVED model is compared against the ASKED one, so if
    anything ever routes past the cap the row says so instead of crediting the wrong bucket.

    AND THE ROW NOW CARRIES A REASON. Every verdict this function has ever written came from a
    four-word vocabulary -- `local`, `no API key` / `provider disabled`, `answers`, `no answer`,
    or an exception's class name -- none of which contains a status code or a provider's
    wording. `dead_forever` reads this file looking for exactly those, so its entire
    permanent-failure test (401/402/404/410, "no such model", "needs billing", "bad key") was
    unreachable by construction: a classifier that cannot see the thing it classifies. The
    provider's own disposition arrives in the engine's `failover` events; `served["error"]`
    carries it here and `reason` puts it in the file. `verdict` keeps its exact old vocabulary,
    because `foreman`, `tuning`, `pipeline` and `read` all count `verdict == "answers"`.
    """
    e = engine()
    if not e:
        return []
    seen, out = {}, []
    for m in _ROUTER.models:
        if pool in (m.pools or []) and m.bucket not in seen:
            seen[m.bucket] = m
    for bucket, m in sorted(seen.items()):
        if bucket.startswith(LOCAL_PREFIX):
            out.append({"bucket": bucket, "model": m.id, "verdict": "local", "seconds": 0})
            continue
        ready, why = _ROUTER.provider_ready(m)
        if not ready:
            out.append({"bucket": bucket, "model": m.id, "verdict": why, "seconds": 0,
                        "reason": why, "served": ""})
            continue
        if not m.enabled:
            # A DISABLED MODEL CANNOT BE THE FIRST CANDIDATE, so asking for it asks for
            # somebody else. `Router.candidates` returns the pinned model only `if ready and
            # model.enabled`, and drops straight through to the rest of the pool otherwise --
            # so before the cap below, a disabled model's row was ALWAYS a report about a
            # neighbour, and `answers` was the likeliest thing it said. Named for what it is;
            # `try_disabled()` is the pass that exists to test these on purpose.
            out.append({"bucket": bucket, "model": m.id, "verdict": "model disabled",
                        "seconds": 0, "reason": "model disabled in config", "served": ""})
            continue
        t = time.time()
        # `who` is bound HERE, not inside the try: the row below reads it on every path, and the
        # exception path never reaches the line that computes it.
        served, reason, who = {}, "", ""
        try:
            got = ask("Reply with JSON only.", 'Return {"ok": true}',
                      {"type": "object", "properties": {"ok": {"type": "boolean"}},
                       "required": ["ok"]}, pool=pool, timeout=timeout, pin=m.id,
                      # ONE CANDIDATE. See the docstring: without this the engine walks the
                      # whole pool behind the pin and the neighbour's success is written down
                      # under this bucket's name.
                      max_attempts=1, served=served)
            verdict = "answers" if got else "no answer"
            reason = str(served.get("error") or "")
            by = str(served.get("bucket") or "")
            # THE SERVING MODEL BY WHATEVER NAME IT CAN BE GIVEN. `by` is `_bucket_of(...)`, and
            # that returns "" for any model id the router does not recognise -- so the raw id and
            # the display label are kept as the fallback for the audit trail below.
            who = by or str(served.get("model_id") or served.get("label") or "")
            if verdict == "answers" and not by:
                # AN UNRESOLVABLE SERVER IS NOT A PASS (order fdebedb8d0ce). The guard used to
                # read `if verdict == "answers" and by and by != bucket`, so when `_bucket_of`
                # answered "" the guard was SKIPPED, the verdict stayed `answers`, and the row's
                # `served` field was written as "" -- the check and the audit trail that would
                # let anyone reconstruct it went blank together, in the same condition. That is
                # the fail-open direction of a check whose stated job is to catch the engine's
                # contract changing underneath this function, which is exactly when `_bucket_of`
                # is most likely to stop resolving. `max_attempts=1` is still the primary guard,
                # so this is small exposure -- and it is closed in the honest direction.
                verdict = "no answer"
                reason = ("the serving model %s could not be mapped to a bucket"
                          % (who or "<the engine named none>"))
            elif verdict == "answers" and by != bucket:
                # BELT AND BRACES, and deliberately not silent. The cap above should make this
                # impossible; if it ever fires, the engine's contract has changed underneath
                # this function and the honest verdict is that THIS bucket did not answer.
                verdict = "no answer"
                reason = "the call was served by %s, not by this bucket" % by
        except Exception as ex:
            silence.note("cascade_bridge.py:prove")
            verdict = type(ex).__name__
            reason = "%s: %s" % (type(ex).__name__, str(ex)[:200])
        out.append({"bucket": bucket, "model": m.id, "verdict": verdict,
                    "seconds": round(time.time() - t, 1),
                    # WHO ACTUALLY SERVED IT, recorded whether or not it matched. A proof that
                    # cannot name its own subject cannot be audited by anyone later -- which is
                    # why this falls back to the raw model id or label when the bucket lookup
                    # comes back empty, rather than writing "" and losing the only clue.
                    "served": who,
                    "reason": reason[:300]})
    return out


def try_disabled(pool="coding", timeout=60):
    """Test models that are switched off in config but DO have a working key.

    Twelve providers are disabled for the only good reason there is -- no key. Seven models are
    disabled while holding one, and that is capacity sitting idle. Some were switched off for
    real causes that have not changed (a retired endpoint, an account needing balance) and some
    for causes that have: GitHub Models refused a 22,000-token request during the oversized-chunk
    experiment and would comfortably take the 2,700-token chunks used now.

    Nothing is enabled on a guess. Each is called directly, once, and the answer decides.

    AND "DIRECTLY" NOW MEANS IT (order 77d59411ca75). This function flipped `m.enabled = True`
    and pinned the model but did not cap the candidate walk, so it carried the identical
    isolation defect `prove()` was repaired for under c810cf64d278: a neighbouring bucket could
    answer and be recorded as ANSWERS for the model under test. `max_attempts=1` and the
    served-bucket cross-check are the same two halves of the same change, and the row now
    records who served it.
    """
    e = engine()
    if not e:
        return []
    out = []
    for m in _ROUTER.models:
        if pool not in (m.pools or []):
            continue
        st = _ROUTER.model_status(m)
        if st.get("available") or st.get("reason") != "model disabled":
            continue
        prov = m.provider or {}
        if not (prov.get("api_key") or prov.get("local")):
            out.append({"model": m.id, "bucket": m.bucket, "verdict": "no key"})
            continue
        was = m.enabled
        t = time.time()
        served, who = {}, ""
        try:
            m.enabled = True
            got = ask("Reply with JSON only.", 'Return {"ok": true}',
                      {"type": "object", "properties": {"ok": {"type": "boolean"}},
                       "required": ["ok"]}, pool=pool, timeout=timeout, pin=m.id,
                      # THE SAME ISOLATION `prove()` WAS GIVEN (order 77d59411ca75). Pinning
                      # names a FIRST candidate, not an only one: `Router.candidates` returns
                      # the pin followed by the rest of the pool, and `Engine.stream_chat` walks
                      # it to the end unless capped -- so a NEIGHBOURING bucket could serve this
                      # call and be written down as ANSWERS for the model under test. That is
                      # worse here than it looks from the call count: this is the tool a person
                      # reaches for precisely when they distrust the pool, and its whole product
                      # is the sentence "this disabled model works, switch it back on".
                      max_attempts=1, served=served)
            verdict = "ANSWERS" if got else "no answer"
            by = str(served.get("bucket") or "")
            who = by or str(served.get("model_id") or served.get("label") or "")
            if verdict == "ANSWERS" and by != m.bucket:
                # Same belt-and-braces as `prove()`, including the blank case: a server that
                # cannot be named is not evidence that THIS model answered.
                verdict = "no answer"
        except Exception as ex:
            silence.note("cascade_bridge.py:try_disabled")
            verdict = type(ex).__name__
        finally:
            m.enabled = was
        out.append({"model": m.id, "bucket": m.bucket, "verdict": verdict,
                    # WHO ACTUALLY SERVED IT, for the same reason `prove()` records it: a row
                    # that cannot name its own subject cannot be audited later.
                    "served": who,
                    "seconds": round(time.time() - t, 1)})
    return out


_USAGE = """cascade_bridge -- the router every cloud model call in this pipeline goes through.

  python src/cascade_bridge.py --selftest   build the engine and make ONE live call
  python src/cascade_bridge.py              the same thing (the historic default)
  python src/cascade_bridge.py --help       this text, and nothing else

Everything else here is used by importing it: feats.py, pipeline.py and the rest call ask().
"""

if __name__ == "__main__":
    # AT THE FOOT OF THE FILE, WHICH IT WAS NOT (order fa3900441022). This block sat at :1564
    # with `prove()` (:1587) and `try_disabled()` (:1701) defined BELOW it, so run as a script
    # the `sys.exit(...)` fired before those two `def` statements ever executed and neither
    # function existed in the `__main__` namespace. Nothing was broken -- `selftest()` uses
    # neither, and every other caller imports the module, where module-level execution completes
    # -- but it was a trap primed for whoever next adds a `--prove` or `--try-disabled` flag here
    # and gets a NameError that reads like a typo. It also left `_USAGE`, which describes the
    # whole CLI, sitting above two thirds of the module's public surface. Pure relocation.
    #
    # `--help` MUST NOT SPEND A LIVE MODEL CALL, and until now it did. This file has no argparse,
    # so every argv fell straight through to `selftest()` -- which builds the router, walks
    # thirty providers and makes a real request. `allsweep.check_import` asks EVERY module
    # `--help` precisely because it is "the cheapest total exercise of a module ... without doing
    # any work", so once a day the IMPORT tier made a network call on this one's behalf, and when
    # the weather was bad `selftest()` returned 1 with no traceback and the tier graded
    # cascade_bridge a BROKEN IMPORT. That is order 2d6c9343cd32: a MAJOR work order filed
    # against a module that imports perfectly, by a tier that cannot tell "this will not load"
    # from "a provider was rate-limited ninety seconds ago".
    #
    # The live check is NOT dropped -- trading one blind spot for another is not a fix. It is now
    # an explicit VERIFY-tier row in `allsweep.VERIFIERS` (`cascade live call`, rc graded
    # BROKEN), which is the tier whose entire product is a verdict, and whose rows now actually
    # reach the sweep's grade and the work order queue (order 14bd09740627, same run).
    if set(sys.argv[1:]) & {"-h", "--help"}:
        print(_USAGE)
        sys.exit(0)
    sys.exit(selftest())
