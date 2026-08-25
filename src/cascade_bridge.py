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
and the reply is parsed and VALIDATED here. A reply that does not validate is a failure, not a
result -- which is the rule this project keeps having to relearn.

PROVENANCE. Every feat is verified verbatim against the page it came from, and that check does
not care which model produced the sentence. So a cloud model cannot introduce a class of error
the local model could not: it can only be wrong in ways already caught. That is what makes
widening the pool safe rather than a loosening of standards.
"""
import json
import os
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
    sys.path.insert(0, CASCADE)
    from cascade import config as C, store as S, router as R, engine as E
    cfg = C.load()
    st = S.Store(os.path.join(HERE, "state", "cascade_scratch.db"))
    # TOOLS OFF for batch work. Cascade's system prompt advertises a filesystem toolset to its
    # coding assistant, and a routed model inherits it -- extraction calls came back carrying
    # `tool search_text(...)` and `tool read_file(...)` instead of answers. The verbatim check
    # threw all of it away, so nothing was corrupted, but every one of those was a wasted round
    # trip. A feat-extraction call has nothing to read from a filesystem.
    cfg = dict(cfg)
    cfg["system_prompt"] = ""
    _ROUTER = R.Router(cfg, st)
    _ENGINE = E.Engine(cfg, st, _ROUTER)
    for m in _ROUTER.models:
        m.supports_tools = False
    _CFG["cfg"] = cfg
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
            silence.note("cascade_bridge.py:100")
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
                        silence.note("cascade_bridge.py:113")
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


PROOF = os.path.join(HERE, "data", "POOL_PROOF.json")
_PROVEN = [None]


# A proof this old is no longer evidence about now. Free tiers roll their windows constantly,
# and a bucket that was busy an hour ago is not a bucket that is broken.
PROOF_TTL = 3600


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
    """
    if _PROVEN[0] is not None:
        return _PROVEN[0]
    out = set()
    try:
        if time.time() - os.path.getmtime(PROOF) <= PROOF_TTL:
            with open(PROOF, encoding="utf-8") as f:
                rows = json.load(f)
            for r in rows:
                v = str(r.get("verdict") or "")
                if any(code in v for code in ("401", "402", "404", "410")):
                    out.add(r["bucket"])
                if "no such model" in v or "needs billing" in v or "bad key" in v:
                    out.add(r["bucket"])
    except Exception:
        silence.note("cascade_bridge.py:dead_forever")
    _PROVEN[0] = out
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
        with _UNREC_LOCK:
            try:
                with open(UNRECOGNISED, encoding="utf-8") as f:
                    rows = json.load(f)
            except Exception:
                rows = {}
            if not isinstance(rows, dict):
                rows = {}
            r = rows.get(key) or {"bucket": bucket, "error": text,
                                  "first_seen": now, "count": 0}
            r["error"] = text
            r["last_seen"] = now
            r["count"] = int(r.get("count", 0)) + 1
            rows[key] = r
            # `silence.write_json`, NOT a hand-rolled `path + ".tmp"`. This function was written
            # in the same session as m100 -- the sweep that found eighteen truncate-then-fill
            # writes and closed the fixed-temp-name collision race behind them -- and then used
            # the exact pattern m100 retired. `_UNREC_LOCK` is a threading lock, so it orders
            # writers inside ONE process; this file is written from every process that imports
            # `cascade_bridge` (read, pipeline, feats, overwatch), and those collide on the temp
            # file itself. The pid+thread-unique name makes that unavailable to get wrong.
            silence.write_json(UNRECOGNISED, rows, indent=1, sort_keys=True)
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


def _alive(bucket):
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


def _metric(row):
    """Same ledger pipeline.ask writes, cloud lane. Ollama reports token counts; a stream
    through Cascade does not, so these rows carry character counts and the aggregator keys on
    which fields exist. Append-only, best-effort -- a metrics failure must never cost a call."""
    # ONE SYSCALL, NOT A BUFFERED WRITE (m62): five processes share this file and a buffered
    # append can be split mid-line, producing rows that parse as neither writer's.
    silence.append_line(_METRICS, json.dumps(row))


def ask(system, prompt, schema=None, pool="coding", temperature=0.1, timeout=75, pin=None):
    """Instrumented wrapper: wall time, outcome and answering model per call, so 'the pool got
    slow' is a measurement rather than a feeling. The real work is _ask_call."""
    t0 = time.time()
    got = _ask_call(system, prompt, schema=schema, pool=pool, temperature=temperature,
                    timeout=timeout, pin=pin)
    _metric({"at": round(t0, 1), "tag": "cascade:" + pool, "s": round(time.time() - t0, 2),
             # `.get` ON WHATEVER PARSED, NOT ON WHATEVER IS TRUTHY. `_extract_json` will
             # happily return a list, bool or number from a fenced reply, `_ask_call` only
             # tags `_via` when the payload is a dict, and `(got or {})` then evaluates to the
             # non-dict itself -- so a provider answering ```json\n[1,2]\n``` crashed the
             # metrics line with AttributeError and took the whole call with it.
             "ok": got is not None,
             "model": (got.get("_via") or "") if isinstance(got, dict) else "",
             "in_chars": len(system) + len(prompt),
             "out_chars": len(json.dumps(got, default=str)) if got is not None else 0})
    return got


def _ask_call(system, prompt, schema=None, pool="coding", temperature=0.1, timeout=75, pin=None):
    """One structured call through Cascade. Returns a parsed dict, or None.

    Mirrors pipeline.ask() so a caller can swap transports without changing anything else.

    The call CLAIMS a bucket before dispatching and releases it after. Without that, concurrent
    workers all read the same stale headroom -- usage is only recorded on completion -- and pile
    onto one meter, which costs a 429 and, worse, teaches the router a lower cap permanently.
    """
    e = thread_engine()
    if not e:
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
            return None
        _ROUTER.reserve(pinned)
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
        return None
    _pace(pinned.bucket)
    sys_msg = system
    if schema:
        sys_msg = (system + "\n\nReply with JSON ONLY, no prose and no code fence, "
                   "matching this schema exactly:\n" + json.dumps(schema))
    messages = [{"role": "system", "content": sys_msg},
                {"role": "user", "content": prompt}]
    out, answered, done = [], None, threading.Event()
    box = {"answered": None, "failed": False}

    def pump():
        try:
            for ev in e.stream_chat(messages, pool=pool, temperature=temperature,
                                    pinned=pinned.id if pinned else None):
                t = ev.get("type")
                if t == "delta":
                    out.append(ev.get("text") or ev.get("delta") or "")
                elif t == "model":
                    box["answered"] = ev.get("label") or ev.get("model_id")
                elif t == "error":
                    box["failed"] = True
                    box["error"] = str(ev.get("error") or ev.get("text") or "")[:300]
                    return
        except Exception as exc:
            silence.note("cascade_bridge.py:151")
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
    try:
        if not finished:
            silence.note("cascade_bridge.py:deadline")
            if pinned:
                _bury(pinned.bucket)
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
            permanent_words = ("authentication", "invalid_api_key", "credentials",
                               "insufficient balance", "no resource package",
                               "payment required", "needs billing", "depleted")
            if pinned and not exhausted and (re.search(r"\b(401|402|403)\b", err)
                                             or any(w in err for w in permanent_words)):
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
            return None
        if pinned:
            _clear(pinned.bucket)
        answered = box["answered"]
    finally:
        if pinned:
            _ROUTER.release(pinned)
    got = _extract_json("".join(out))
    if got is None:
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
    for lab in ready[:12]:
        print(f"   {lab}")
    schema = {"type": "object", "properties": {"feats": {"type": "array", "items": {
        "type": "object", "properties": {"sentence": {"type": "string"},
                                         "axis": {"type": "string"}},
        "required": ["sentence", "axis"]}}}, "required": ["feats"]}
    got = ask("You extract feats. Copy sentences verbatim.",
              "ENTITY: Test\n\nHe lifted the boulder over his head and hurled it across the "
              "valley. He liked tea.\n\nReturn feats.", schema)
    print(f"\nlive call -> {'OK via ' + str(got.get('_via')) if got else 'FAILED'}")
    if got:
        print(json.dumps({k: v for k, v in got.items() if k != '_via'}, indent=1)[:400])
    return 0 if got else 1


if __name__ == "__main__":
    sys.exit(selftest())


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
            out.append({"bucket": bucket, "model": m.id, "verdict": why, "seconds": 0})
            continue
        t = time.time()
        try:
            got = ask("Reply with JSON only.", 'Return {"ok": true}',
                      {"type": "object", "properties": {"ok": {"type": "boolean"}},
                       "required": ["ok"]}, pool=pool, timeout=timeout, pin=m.id)
            verdict = "answers" if got else "no answer"
        except Exception as ex:
            silence.note("cascade_bridge.py:prove")
            verdict = type(ex).__name__
        out.append({"bucket": bucket, "model": m.id, "verdict": verdict,
                    "seconds": round(time.time() - t, 1)})
    return out


def try_disabled(pool="coding", timeout=60):
    """Test models that are switched off in config but DO have a working key.

    Twelve providers are disabled for the only good reason there is -- no key. Seven models are
    disabled while holding one, and that is capacity sitting idle. Some were switched off for
    real causes that have not changed (a retired endpoint, an account needing balance) and some
    for causes that have: GitHub Models refused a 22,000-token request during the oversized-chunk
    experiment and would comfortably take the 2,700-token chunks used now.

    Nothing is enabled on a guess. Each is called directly, once, and the answer decides.
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
        try:
            m.enabled = True
            got = ask("Reply with JSON only.", 'Return {"ok": true}',
                      {"type": "object", "properties": {"ok": {"type": "boolean"}},
                       "required": ["ok"]}, pool=pool, timeout=timeout, pin=m.id)
            verdict = "ANSWERS" if got else "no answer"
        except Exception as ex:
            silence.note("cascade_bridge.py:try_disabled")
            verdict = type(ex).__name__
        finally:
            m.enabled = was
        out.append({"model": m.id, "bucket": m.bucket, "verdict": verdict,
                    "seconds": round(time.time() - t, 1)})
    return out
