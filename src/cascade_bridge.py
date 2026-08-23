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


def ask(system, prompt, schema=None, pool="coding", temperature=0.1, timeout=75, pin=None):
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
        ranked = sorted((m for m in _ROUTER.models
                         if not m.bucket.startswith(LOCAL_PREFIX)),
                        key=lambda m: (m.bucket not in answering))
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
        except Exception:
            silence.note("cascade_bridge.py:151")
            box["failed"] = True
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
            err = box.get("error") or ""
            if pinned and any(code in err for code in ("401", "402", "Authentication",
                                                       "invalid_api_key", "credentials")):
                _bury(pinned.bucket, AUTH_BENCH)
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
