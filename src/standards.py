#!/usr/bin/env python3
"""
STANDARDS — what "working" means, in numbers, and a work order when it is not met.

THE OWNER'S BRIEF
-----------------
    "your overwatch should have a 'standards' section where it understands that things should be
     operating at some minimum level and if it isn't it reports that to you or ollama or wherever
     as a work order to get it fixed"
    "they should be as concise and granular as reasonably possible"

Exactly the missing piece. `overwatch` could already tell whether a module imports and whether a
model finds a defect in the source. Neither catches the failure this project actually keeps
having: a system that runs, imports, parses, raises nothing -- and performs at a tenth of what it
should.

Every instance was invisible until somebody happened to look at a number:

    the reader ran on one GPU for a morning        every check passed, throughput 4x low
    5,090 chunks were skipped and filed as read    no exception, progress said 9.8/s
    six buckets pinned at 1 request a minute       "available", pool 10x too small
    the bridge fell back to a local model          38 of 75 "cloud" calls were the GPU

There was no declared expectation, so there was nothing to fall short OF. **A number with no
floor under it cannot be wrong.**

GRANULAR, BECAUSE A COARSE STANDARD CANNOT BE ACTED ON
------------------------------------------------------
"Throughput is low" is a complaint. It does not say whether the pool shrank, the caps were
mis-learned, the GPU is jammed, the workers outnumber the buckets, or the free tiers simply ran
out for the day -- and those have five different remedies. So the standards are split until each
one has exactly one likely cause and one first move.

Each carries a FLOOR and an ORDER. The floors are deliberately generous: a standard that trips on
a normal bad minute trains its reader to ignore it, and this project has burned that lesson twice
already -- on a preflight FAIL everyone learned to scroll past, and an auditor that called an
empty log file corrupt.
"""
import json
import os
import sys
import time

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(HERE, "src")
sys.path.insert(0, SRC)
import silence                                                          # noqa: E402
import tuning                                                           # noqa: E402

_BAD_CHARS = (chr(8), chr(11), chr(12), chr(7))
if any(c in open(os.path.abspath(__file__), encoding="utf-8").read() for c in _BAD_CHARS):
    raise SystemExit(__file__ + ": a regex escape was eaten in transit.")

# ---------------------------------------------------------------------------- the floors
#
# Each is set where a breach means something is genuinely wrong rather than merely unlucky.

MIN_CALLS_PER_HOUR = 900        # measured healthy 3,400/h; a third of that is a real fault
# Below this many calls a success PERCENTAGE is noise, not a measurement. NOT a second literal
# `20` -- that used to be a hand-copied spelling of tuning.MIN_CALLS_TO_JUDGE, and the check
# written to hold the two together (verify_math.py's "the threshold itself is the one tuning.py
# already settled on") compared this constant against the literal 20, not against tuning's
# constant, so raising tuning.MIN_CALLS_TO_JUDGE would have left that check green while the two
# policies silently diverged -- the exact failure the check exists to catch. Deriving the value
# here means there is nothing left to diverge: this name and tuning's are the same number by
# construction, not by two people remembering to update both. See `calls that succeed`.
MIN_CALLS_TO_JUDGE_RATE = tuning.MIN_CALLS_TO_JUDGE
MIN_LIVE_BUCKETS = 6            # below this the pool cannot absorb even modest concurrency
MAX_DRY_FRACTION = 0.60         # more than this exhausted means the day's allowance is spent
MAX_PINNED_AT_ONE = 0           # a bucket reading rpm 0/1 is a mis-learned cap, never a real one
MAX_ETA_HOURS = 24              # the corpus read is meant to be an overnight job
MIN_FEATS_PER_CHUNK = 0.5       # below this the reader is running but extracting nothing
MAX_FABRICATION = 0.45          # verbatim-check rejections; above this the model is guessing
MAX_COVERAGE_AGE_H = 6          # coverage older than this predates whatever has run since
# EVERY source must have somewhere to read from. Not most.
#
# This was 0.80, and 92% passed -- quietly accepting 18 sources and thousands of entries as
# permanently uncitable. A floor that tolerates a gap closes the file on it: nothing retries, the
# scout never fires, and the standard reports green forever. At 1.0 it stays breached until every
# source has a wiki, a raw endpoint or a registered page list, and the foreman keeps scouting.
# Some will never be found. A permanently breached standard whose remedy runs every cycle is a
# system still looking; a satisfied one is a system that stopped.
MIN_HOST_COVERAGE = 1.0
MIN_SETTLED = 0.55              # cited or read; the rest is unexamined
MAX_BROKEN_MODULES = 0
MAX_CORRUPT_FILES = 0
MAX_HIGH_FINDINGS = 0
MAX_PHASES_MISSING = 0          # all eight phases are built; ANY gap is a regression now
MIN_ROLL_PROGRESS = 0.95        # the page roll should be essentially complete
MAX_SWALLOWED_NEW = 2000        # a spike in swallowed failures is a fault somewhere upstream
MAX_UNANSWERED_RECORDS = 0      # a cached record with unread chunks is permanently incomplete
MAX_FOREIGN_ROSTERS = 0         # a roster whose pages never name it came from the wrong wiki
MAX_SHELFMARK_COLLISIONS = 0    # two worlds at one address make every citation ambiguous
MAX_SWEEP_AGE_H = 6             # a stale audit reports on a system that no longer exists
MIN_DISK_GB = 10                # the roll writes hundreds of MB an hour
MAX_PUBLISH_AGE_H = 2           # the public panel is a snapshot; stale, it misleads quietly

# How long a RUNNING job may write nothing before it counts as stalled.
#
# THE GAP THIS CLOSES. Every liveness check in this file asks whether a process exists.
# `overnight.running(job)` returns a boolean and the "every managed job is running" standard is
# satisfied by a process that is alive and doing absolutely nothing -- which is the same
# alive-but-idle confusion the whole project exists to refuse, wearing a supervisor's uniform.
#
# It happened exactly as you would predict. A catalogue run sat on its first source for 28
# minutes and wrote 207 bytes total. The process was up, so the jobs standard passed. The
# dashboard's own `movement()` DOES compute a `stalled` flag -- and nothing here ever read it,
# so the stall was drawn on a panel and never became a work order. A finding nobody is dispatched
# to fix is decoration.
#
# 15 minutes is generous on purpose: the corpus reader can legitimately spend ten minutes on one
# oversized page, and a false stall that halts a healthy job is worse than a slow report.
MAX_JOB_SILENCE_MIN = 15
JOB_WATCH = os.path.join(HERE, "state", "job_progress.json")


_RUNNER = {"at": 0.0, "up": None}


def ollama_runner_up(ttl=120.0):
    """Is a model-runner PROCESS actually alive? Cached, because this costs a process spawn.

    Deliberately separate from "does the daemon answer". On 2026-08-24 the daemon answered
    `/api/tags` with 200 and `/api/ps` named a resident model while NO `llama-server.exe`
    existed at all -- nothing was draining the request queue, so every call returned
    `503 maximum pending requests exceeded`, including each attempt to load a model. The phase
    runner logged 59 unbroken 503s over 31 minutes doing no work, and every liveness check in
    this project reported Ollama healthy throughout, because they all ask `/api/tags`.

    `None` means "could not tell" and is never reported as a fault."""
    now = time.time()
    if now - _RUNNER["at"] < ttl:
        return _RUNNER["up"]
    up = None
    try:
        import subprocess as _sp
        out = _sp.run(
            ["tasklist", "/FI", "IMAGENAME eq llama-server.exe", "/NH"],
            capture_output=True, text=True, timeout=25,
            creationflags=getattr(_sp, "CREATE_NO_WINDOW", 0)).stdout or ""
        up = "llama-server" in out.lower()
    except Exception:
        silence.note("standards.py:ollama-runner")
    _RUNNER.update({"at": now, "up": up})
    return up


_TOKENFLOW = {"at": 0.0, "ok": None, "s": None}


def _flow_failure(exc, secs):
    """-> a short phrase naming what actually stopped the token-flow probe.

    A FAULT IS NOT A DIAGNOSIS. The standard built from this reported "daemon up, generation
    TIMED OUT -- queue is wedged" for every failure the probe could have, so a daemon that was
    not listening at all read as a wedged queue and the remedy on the page ("restart ollama.exe")
    was the wrong one -- the same misdiagnosis-costs-hours lesson this file records for the
    model-calls order text, in a smaller box. Each branch below is a DIFFERENT machine state
    with a different first move: nothing listening (start it), the daemon answering an error
    (read its log), a generation that never returned (the wedge the standard was written for).
    """
    reason = getattr(exc, "reason", None)
    status = getattr(exc, "code", None)
    if isinstance(exc, TimeoutError) or isinstance(reason, TimeoutError):
        return "generation TIMED OUT after %ss -- queue is wedged" % secs
    if isinstance(reason, ConnectionRefusedError):
        return "nothing listening on the ollama port -- the daemon is DOWN, not wedged"
    if status is not None:
        return "the daemon answered HTTP %s -- it is up and refusing, not wedged" % status
    if reason is not None:
        return "the probe never reached the daemon (%s: %s)" % (type(reason).__name__, reason)
    return "the probe failed before any tokens (%s: %s)" % (type(exc).__name__, str(exc)[:80])


def ollama_token_flow(ttl=300.0, timeout=300):
    """Does a generation actually COMPLETE? The third liveness lesson in two days.

    The runner-process check above closed the first wedge (resident model, no runner). On the
    same day the inverse appeared: runner alive, model fully GPU-resident, /api/tags fine --
    and a trivial generate timing out for TWO HOURS while every check here read green. Process
    presence and API reachability are both proxies; the only proof of a model server is a
    completed generation.

    BUSY IS NOT WEDGED. The first draft probed with a 90s timeout and cried wolf the moment a
    healthy queue held a few worker calls -- exactly the false-alarm class this file's own
    docstring warns trains readers to scroll past. So the LEDGER answers first: any local
    call completing in the last 15 minutes (a metrics row with a tps) is proof of flow at
    zero cost. Only a silent ledger earns the live probe, and the probe waits like a worker
    would. `None` = could not tell, never reported as a fault.

    THE PROBE MUST ASK FOR THE WINDOW THE LIBRARY ACTUALLY SERVES. Measured 2026-08-24: this
    probe hardcoded `num_ctx: 512` while every real caller derives the window from
    `config.yaml` (12288). Ollama serves a resident model at ONE context size, so a call
    naming a different window needs the runner torn down and rebuilt -- `gpu_lane.py`'s own
    measured table puts that at "240 s+, never completed" against a queue that never drains.
    The consequence was not slowness, it was a MANUFACTURED FINDING: whenever the ledger was
    silent, this probe asked for a window nobody serves, timed out, and published
    "generation TIMED OUT -- queue is wedged" as a red standard. Reproduced live at 18:22 --
    a `num_predict: 8` "say ok" at 512 failed on a 180s deadline while `ollama ps` showed the
    12288 runner still resident and two other clients being served normally.

    It was also actively harmful, which is the half worth remembering. The probe carries
    `keep_alive: -1`, so a probe that ever WON its rebuild would pin a 512-token runner
    forever, and every real 12288 caller would then have to evict it back -- a diagnostic
    that manufactures the fault it reports, and inflicts it on the jobs it is watching.
    Deriving the window from config makes the probe measure the resident runner, which is
    what a caller experiences. Pinned by verify_math S19ab."""
    now = time.time()
    if now - _TOKENFLOW["at"] < ttl:
        return _TOKENFLOW["ok"], _TOKENFLOW["s"]
    try:
        mp = os.path.join(HERE, "state", "model_metrics.jsonl")
        size = os.path.getsize(mp)
        with open(mp, "rb") as f:
            if size > 120_000:
                f.seek(-120_000, 2)
            tail = f.read().decode("utf-8", "replace").splitlines()
        for ln in reversed(tail):
            try:
                r = json.loads(ln)
            except Exception:
                continue
            if r.get("tps") and now - float(r.get("at", 0)) < 900:
                _TOKENFLOW.update({"at": now, "ok": True, "s": "ledger"})
                return True, "ledger"
    except Exception:
        _ = "silence-exempt: no metrics ledger yet just means the probe decides"
    ok, secs = None, None
    # BUILDING THE PROBE IS NOT PROBING. This stage reads config.yaml and composes the request;
    # every failure in it (a missing or malformed config, a `yaml` that will not import) is a
    # fact about THIS REPO and no fact at all about the daemon. It used to share the handler
    # below, so a config that failed to parse published "daemon up, generation TIMED OUT --
    # queue is wedged" as a HIGH standard and sent the reader to restart ollama.exe for a local
    # parse bug -- this file's own recorded lesson (a misdiagnosis costs more hours than the
    # fault) reappearing one screen below where it is written down. Run33 order 2eaae3c5f50f.
    # `None` is the documented value for "could not tell", and an unsent probe told nothing.
    try:
        import urllib.request as _ur
        import yaml as _yaml
        cfg = _yaml.safe_load(open(os.path.join(HERE, "config.yaml"), encoding="utf-8"))
        # num_ctx FROM CONFIG, never a literal -- see the docstring. A foreign window turns
        # this probe into a runner rebuild, which is the one call shape that cannot finish.
        body = json.dumps({"model": cfg.get("model"), "prompt": "say ok", "stream": False,
                           "keep_alive": -1,
                           "options": {"num_ctx": int(cfg.get("num_ctx", 6144)),
                                       "num_predict": 8}}).encode()
        req = _ur.Request(str(cfg.get("ollama_host", "http://localhost:11434")).rstrip("/")
                          + "/api/generate", data=body,
                          headers={"Content-Type": "application/json"})
    except Exception:
        silence.note("standards.py:token-flow-unsent")
        return None, None
    try:
        t0 = time.time()
        with _ur.urlopen(req, timeout=timeout) as r:
            _raw = json.loads(r.read())
        # PROOF OF FLOW IS TOKENS PRODUCED, NOT PROSE RETURNED. The predicate here was
        # `bool(response.strip())`, which is wrong for the model this library actually runs.
        # qwen3 is a reasoning model: its first tokens land in `thinking`, and `response` stays
        # empty until the reasoning closes. With num_predict 8 the call ends `done_reason:
        # "length"` mid-thought -- a perfectly healthy generation reporting `response: ""`.
        # Measured 2026-08-24: eval_count 8, thinking "Okay, the user just said", response "".
        # The old predicate called that a wedged daemon. `eval_count` is the direct measure of
        # the thing this function exists to prove, so it is what decides.
        ok = bool(_raw.get("eval_count")) or bool(_raw.get("response", "").strip())
        secs = round(time.time() - t0, 1)
    except Exception as e:
        # A timeout or 5xx here IS the finding: the daemon exists and tokens do not flow.
        #
        # WHICH failure it was decides the remedy, so the cause travels with the verdict. The
        # standard that reads this asserted ONE diagnosis -- "daemon up, generation TIMED OUT --
        # queue is wedged" -- for every exception this handler catches, including a refused
        # connection, which says the daemon is not up at all and needs starting rather than
        # restarting. The second slot already carries a string on the ledger path ("ledger"), so
        # naming the cause here costs nothing and the caller prints it verbatim.
        ok, secs = False, _flow_failure(e, round(time.time() - t0, 1))
        silence.note("standards.py:token-flow")
    _TOKENFLOW.update({"at": now, "ok": ok, "s": secs})
    return ok, secs


# A CONTENT wiki, deliberately, and one this corpus actually reads (WIKI_HOSTS binds it to
# "Marvel" and to "major fantasy pantheons"). `community.fandom.com` is the wrong host to ask:
# it is the only fandom host publishing AAAA records, so it answers over IPv6 while every
# content wiki -- all of them A-record-only -- is unreachable. This is not a sample standing in
# for the others: every fandom content host resolves to the SAME two Cloudflare IPv4 addresses,
# so one connect tests the identical socket all 191 bound hosts must open.
FANDOM_PROBE_HOST = "marvel.fandom.com"


def fandom_ipv4_reachable(host=FANDOM_PROBE_HOST, timeout=8, _sk=None):
    """Can this machine open a TCP connection to fandom's edge OVER IPv4? `(ok, detail)`.

    THE FAMILY IS THE WHOLE POINT, and it is why this standard read green through a total
    outage on 2026-08-24. The old probe was `create_connection(("community.fandom.com", 443))`,
    which walks whatever `getaddrinfo` returns and stops at the first success. `community` is
    the one fandom host that publishes AAAA records, so it connected over IPv6 in 0.02s and the
    board said "reachable" while EVERY content wiki -- marvel, forgottenrealms, starwars,
    aneurism, all A-record-only -- timed out at the socket. 164 of 164 rows in
    COMPLETENESS.json carried "no denominator was obtained", preflight said "fandom API
    unreachable", and this standard, whose entire reason for existing is to catch exactly that
    shape, stayed green.

    Measured that day: the content hosts and `community` resolve to the SAME two Cloudflare
    IPv4 addresses (162.159.142.170, 172.66.2.166), and BOTH time out from here while
    Wikipedia, GitHub and 1.1.1.1 over IPv4 answer in under 0.05s. So pinning the family to
    AF_INET is not a sample of one host standing in for the others -- it is the identical
    socket every content wiki has to open, asked once.

    ASKED ONCE PER PROCESS. `check()` calls this on every invocation, and `verify_math` calls
    `check()` about nineteen times in one run -- so the battery was opening nineteen live TLS
    connections to Cloudflare to answer a question whose answer cannot change between them.
    That was not merely waste. `mutate.py` runs the battery in a sandbox as its differential
    gate, and on 2026-08-26 it REFUSED TO RUN AT ALL -- "verify_math TIMEOUT ... a gate that
    cannot finish on unmutated code cannot judge a mutant" -- because those probes stall under
    load while the same battery finishes in 32s on the live tree. `getaddrinfo` in particular
    takes no timeout argument and can hang for as long as the resolver wants, so the `timeout`
    below never bounded the whole call. One answer per process bounds the exposure to a single
    DNS lookup and a single connect, and makes the battery give the same answer to every check
    that asks -- which is what a check comparing two runs needs it to do.

    Deliberately NOT cached across processes: a network fact goes stale in minutes and the
    whole point of this standard is to notice an outage while it is happening.

    `_sk` exists so the regression checks can drive this with a stub instead of the network --
    and a stubbed call bypasses the memo entirely, in both directions, because three checks in
    verify_math §19z drive this with three DIFFERENT synthetic networks and a memo shared with
    them would answer the second and third with the first one's result."""
    if _sk is not None:
        return _fandom_probe(host, timeout, _sk)
    key = (host, timeout)
    if key not in _FANDOM_V4_CACHE:
        import socket as _real_sk
        _FANDOM_V4_CACHE[key] = _fandom_probe(host, timeout, _real_sk)
    return _FANDOM_V4_CACHE[key]


# Keyed by (host, timeout) rather than a bare flag, so a caller asking about a different host or
# with a different patience gets its own answer instead of inheriting one.
_FANDOM_V4_CACHE = {}


def _fandom_probe(host, timeout, _sk):
    """The live probe itself, with no memo in front of it. -> (ok, detail)."""
    try:
        infos = _sk.getaddrinfo(host, 443, _sk.AF_INET, _sk.SOCK_STREAM)
    except OSError:
        silence.note("standards.py:fandom-v4-dns")
        return False, "no A record for " + host
    detail = "no address tried"
    for fam, typ, proto, _canon, sa in infos:
        s = _sk.socket(fam, typ, proto)
        try:
            s.settimeout(timeout)
            s.connect(sa)
            return True, str(sa[0])
        except OSError as e:
            detail = "%s %s" % (sa[0], type(e).__name__)
        finally:
            try:
                s.close()
            except OSError:
                silence.note("standards.py:fandom-v4-close")
    return False, detail


def job_stamp(prev_entry, size, now):
    """`(held, at)` for one watched log: has it held this size, and since when?

    Pulled out so the rule can be tested without processes or files -- see verify_math 19b.
    `at` must survive across checks while the size holds, because the question the stall
    detector asks is "how long has this log been silent", not "how long since I last looked".
    Re-stamping unconditionally made those two the same number, and since the checker runs far
    more often than MAX_JOB_SILENCE_MIN, the threshold became unreachable for every job."""
    held = bool(prev_entry) and prev_entry.get("size") == size
    return held, (prev_entry.get("at", now) if held else now)

# Fraction of each source's own cast the catalogue must hold. DELIBERATELY 1.0 AND DELIBERATELY
# UNSATISFIABLE, like MIN_HOST_COVERAGE: its job is not to be met, it is to keep the catalogue
# pass dispatching itself for as long as anything is missing.
#
# This is the standard the library most needed and did not have. It knew -- in a file, in
# writing -- that it held 4.9% of its sources' characters, with Marvel at 0.4% and DC at 0.5%,
# and that number sat in COMPLETENESS.json waiting for somebody to read it. Nothing was
# dispatched, because no floor said a shortfall was a fault. A cap had removed the characters
# and the absence of a floor kept them removed.
MIN_CATALOGUE_COVERAGE = 1.0
MAX_STALE_MODEL_IDS = 0         # a retired model name makes a live provider read as dead
MAX_PROVIDER_MODELS_AGE_H = 12  # an empty `stale` list from three days ago measured nothing


_UNANS_CACHE = {"at": 0.0, "n": 0}


def context_verdict(served, want):
    """PURE. Does the resident runner serve the context this project asks for? -> (holds, observed).

    Pulled out of `check()` for the same reason `verdict()` and `charter_regression_verdict()`
    are: a decision the drill must be able to attack without a GPU, a daemon or a network. It
    also stops the net from having to scrape numbers back out of the printed sentence, which is
    a check on the formatting rather than on the finding -- the first version of that net went
    red on its own comma.

    `None` on either side means the question could not be put, and is NOT agreement: the caller
    routes that to `_dropped` rather than emitting a row that reads as a pass.
    """
    if served is None or want is None:
        return None, ("resident context %r, configured %r -- one of them could not be read"
                      % (served, want))
    return int(served) == int(want), (
        "runner serves num_ctx=%s, config.yaml asks for %s" % (int(served), int(want)))


def cfg_num_ctx():
    """-> the context window config.yaml asks for, or None if it cannot be read.

    READ, NEVER RESTATED, and never defaulted to a plausible number: a default here would make
    the context standard compare the runner against a literal this file invented, which is the
    one thing it exists to catch. None means "could not tell", and the caller reports that as
    unmeasurable rather than as agreement.
    """
    try:
        import yaml as _y
        with open(os.path.join(HERE, "config.yaml"), encoding="utf-8") as f:
            return int(_y.safe_load(f).get("num_ctx"))
    except Exception:
        silence.note("standards.py:cfg-num-ctx")
        return None


def _s(name, holds, observed, floor, order, severity="medium", group="general"):
    return {"standard": name, "group": group, "holds": bool(holds), "observed": observed,
            "floor": floor, "order": order, "severity": severity}


CHARTER_REGRESSION_MAX_AGE_H = 26


def charter_regression_verdict(reg, now=None):
    """(holds, observed) for `the automation reproduces the charter`, from the parsed file.

    PULLED OUT OF `check()` ON PURPOSE, 2026-08-25. This verdict has three distinguishable
    states -- never run, mid-pass, and complete -- and until now `check()` could only test the
    third by reading the one real file on disk, which is why nobody could ask "what does this
    say about a HALF-FINISHED pass?" without waiting for one to exist. As a pure function of
    the parsed dict it is testable with synthetic inputs, and `verify_math` does exactly that.
    That is the point: a behavioural check beats a source-grep, which cannot tell a live branch
    from a dead one.

    THE INVARIANT IT EXISTS TO DEFEND: a pass in progress NEVER holds. `magnitude.calibrate()`
    now checkpoints after every benchmark so a killed run keeps its work, and it deliberately
    withholds `at` until the pass is complete. Without that, the first consistent row would turn
    this standard green with five charter references still unrun -- the project's green-by-
    absence failure mode, on a HIGH standard guarding the instrument itself.
    """
    now = time.time() if now is None else now
    if not isinstance(reg, dict):
        return False, "never run"
    rows = [r for r in (reg.get("results") or []) if isinstance(r, dict)]
    scored = [r for r in rows if r.get("status") == "SCORED"]
    bad = [r for r in scored if not r.get("consistent")]
    at = reg.get("at")
    if not reg.get("complete") and at is None:
        pend = [p for p in (reg.get("pending") or []) if isinstance(p, str)]
        started_h = (now - float(reg.get("started") or 0)) / 3600
        return False, ("pass IN PROGRESS: %d of %d benchmarks done, started %.1fh ago%s"
                       % (len(rows), len(rows) + len(pend), started_h,
                          (" -- pending: " + ", ".join(pend)) if pend else ""))
    age_h = (now - float(at or 0)) / 3600
    holds = bool(scored) and not bad and age_h <= CHARTER_REGRESSION_MAX_AGE_H
    return holds, ("%d/%d consistent, %d unscored, %.0fh old"
                   % (len(scored) - len(bad), len(scored), len(rows) - len(scored), age_h))


def provider_pool_denominator(pm):
    """How much of the provider pool a `stale` count was actually measured over.

    Returns (n_providers, n_verified, n_unverified, unverified_names, sentence) from a
    `data/PROVIDER_MODELS.json` payload.

    A NUMERATOR WITH NO DENOMINATOR. Found 2026-08-25, the other half of order cd64337d3349.
    `check()` read `pm["stale"]` and nothing else and printed "0 stale in the cloud pool" -- a
    claim about THE POOL. In the 2026-08-25 20:21 snapshot the pool held 26 providers and only
    12 ever produced a model list: 10 had no key configured and 4 failed the request outright
    (402/410/405/401). The other 14 contributed nothing to `stale` and nothing to any count; they
    were not in the arithmetic, and the line reporting the result did not know they existed.
    Zero stale out of twelve verified is a fact. Zero stale out of twenty-six is what the line
    was read as -- a HIGH standard giving an all-clear over half a pool it never asked.

    `catalogue_models.py` now always returns an `outcome` per provider (listed / empty_list /
    unreachable / unconfigured) and ships an `unverified` list plus a `counts` block. `stale`
    deliberately does NOT absorb the unverified ones: a stale row asserts "the config asks for a
    model this provider no longer serves", and for a provider nobody could ask that is UNKNOWN,
    not false. So both numbers travel together here or neither is worth reading.

    NOTHING IS CAPPED -- every unverified provider is named. Pulled out of `check()` on purpose,
    as `charter_regression_verdict` was: the three shapes this must handle (a current snapshot, a
    pre-fix snapshot with no `counts`, and a fresh snapshot where NOTHING verified) cannot all be
    put on disk at once, so as a pure function of the payload they are all testable.
    """
    pm = pm or {}
    counts = pm.get("counts") or {}
    unver = pm.get("unverified") or []
    rows = pm.get("providers") or []
    n_prov = counts.get("providers") or len(rows)
    derived = ""
    if counts:
        n_ver = counts.get("verified", 0)
        n_unver = counts.get("unverified", len(unver))
        unchecked = counts.get("unchecked_ids")
        names = ["%s:%s" % (u.get("outcome") or "?", u.get("provider") or "?")
                 for u in sorted(unver, key=lambda u: (u.get("outcome") or "",
                                                       u.get("provider") or ""))]
    else:
        # A snapshot written before catalogue_models gained `counts` -- the shape this standard
        # used to be handed. Derive what can be derived (a row that produced no model list
        # produced no evidence) and SAY it was derived, because the derived figure cannot tell
        # `no key` from `the provider refused`: only the fixed sweep records that, and recording
        # it is what the fix was for.
        n_ver = len([r for r in rows if r.get("models")])
        n_unver = n_prov - n_ver
        unchecked = None
        names = sorted("%s (%s)" % (r.get("provider") or "?",
                                    str(r.get("error") or "no model list")[:40])
                       for r in rows if not r.get("models"))
        derived = (" [denominator DERIVED from the provider rows: this snapshot predates the "
                   "`counts`/`unverified` block, so the reason each provider went unverified "
                   "survives only as its error string -- re-run `catalogue_models.py` for the "
                   "outcome breakdown]")
    sentence = "over %d VERIFIED provider(s) of %d in the pool" % (n_ver, n_prov)
    if n_unver:
        sentence += ("; %d produced no model list and are UNVERIFIED -- neither fresh nor "
                     "stale, unasked%s -- %s"
                     % (n_unver,
                        ("" if unchecked is None
                         else ", leaving %d configured model id(s) unchecked" % unchecked),
                        ", ".join(names)))
    return n_prov, n_ver, n_unver, names, sentence + derived


def check(state=None):
    """Measure every declared standard against the dashboard's own numbers.

    Reading the same state dict the instrument panel reads is deliberate: a standard that
    computed its own figure could disagree with the panel, and then nobody knows which to
    believe.
    """
    if state is None:
        import dashboard as D
        state = D.state()
    out = []
    # GREEN BY ABSENCE. Roughly eighteen standards below live inside a `try: ... out.append(...)
    # except Exception: silence.note(...)` block where the append is the only thing inside the
    # try -- so a missing or unreadable input file (the exact FAIL-CLOSED case Hard Rule -1
    # exists for) does not fail that standard, it DELETES it. `report()`'s "N/N standards met"
    # line then divides by whatever's left, and a run losing three standards to a missing file
    # reads as MORE consistent, not less. `_dropped` is filled by those same except blocks (see
    # each `silence.note("standards.py:<name>")` call) and turned into one real standard below,
    # so a vanished standard shows up as a miss instead of shrinking the denominator it would
    # have counted against. 2026-08-26, batch 4.
    _dropped = []
    tp = state.get("throughput") or {}
    quotas = state.get("quotas") or []
    jobs = {j["name"]: j for j in (state.get("jobs") or [])}
    lib = state.get("library") or {}
    w = state.get("watch") or {}

    # ------------------------------------------------------------------ the provider pool
    #
    # THE ORDER TEXT BELOW USED TO END "the reader is not asking", FULL STOP. It was wrong, and
    # wrong in the most expensive way an order can be: it named one cause and sounded certain.
    # Run #16 followed it and spent its queue checking the reader's transport, which was fine
    # (Cascade, 8 workers, printed in read_auto.log line 1). Measured in run #18: over three
    # hours the pool took 543 calls and REFUSED 364 of them, and no standard in this tree
    # reported it -- the three sub-standards below read `worst` (quota headroom) and `cap`
    # (shape), so a bucket that 429s every call while holding a full daily allowance reads
    # green in all three. Worse, 38% of those refusals came from four buckets that can never
    # succeed again without the owner: zai and cohere are out of credit (their 429 bodies say
    # so), cloudflare and hyperbolic answer 401. Nothing benches them, because engine.is_dead()
    # fires only on 404/410/402/400/422 -- a dead key and a spent account are not in that set.
    # The floor (900) is deliberately untouched; a floor is an opinion. The GUIDANCE was a
    # factual claim, and a false one. 2026-08-24, run #18.
    per_hour = tp.get("per_hour", 0)
    out.append(_s(
        "model calls per hour", per_hour >= MIN_CALLS_PER_HOUR, per_hour, MIN_CALLS_PER_HOUR,
        "CHECK `the reader's gate is open` FIRST -- it is below these four and it outranks "
        "them. If it is red the reader is throttling itself and the pool is not the cause at "
        "all: the ceiling is floor * GATE_LOCAL_N / GATE_CLOUD_N, which on this machine is "
        "900 * 2/16 = 112 an hour, and every standard below can read green while it binds. "
        "That is exactly what run #27 measured, after runs #16, #18 and #26 each worked this "
        "number from the pool side. Only once the gate is open do the four below apply. "
        "Work the four standards below in order -- they split this one number into its causes. "
        "If all four hold and throughput is still low there are TWO candidates, and the four "
        "standards can only see one of them. Either the reader is not asking (check that "
        "read.py resolved its transport to Cascade and that its worker count matches the "
        "bucket count), OR it is asking and being REFUSED -- which none of the four below "
        "can detect, because they read quota headroom and cap shape, never call disposition. "
        "Measure refusal directly: `select outcome,count(*) from usage where ts>strftime('%s',"
        "'now','-3 hours') group by outcome` in state/cascade_scratch.db, and read "
        "bucket_state.last_error for any bucket that is failing -- a bucket out of credit or "
        "holding a dead key refuses every call forever while still reporting full headroom.",
        "high", "pool"))

    metered = [q for q in quotas if not q.get("unlimited")]
    live = [q for q in quotas if q.get("unlimited") or q.get("worst", 0) > 0.05]
    out.append(_s(
        "buckets with headroom", len(live) >= MIN_LIVE_BUCKETS, len(live), MIN_LIVE_BUCKETS,
        "The pool has collapsed to a handful of providers. Check the quota panel for keys that "
        "started returning 401 or 402, and for providers disabled in Cascade's config.",
        "high", "pool"))

    dry = [q for q in metered if q.get("worst", 1) <= 0.001]
    frac_dry = len(dry) / max(len(metered), 1)
    out.append(_s(
        "buckets not exhausted", frac_dry <= MAX_DRY_FRACTION, f"{frac_dry:.0%} dry",
        f"{MAX_DRY_FRACTION:.0%}",
        "Most of the pool has spent its daily allowance. This is the one breach with no code "
        "remedy: either add providers or wait for the windows to roll. Check WHICH window is "
        "zero -- a spent rpd is a real day's worth of work, a zero rpm is not.",
        "medium", "pool"))

    pinned = [q for q in metered
              if any(win.get("name") == "rpm" and win.get("cap") == 1 for win in q.get("windows", []))]
    out.append(_s(
        "no bucket pinned at rpm 1", len(pinned) <= MAX_PINNED_AT_ONE, len(pinned),
        MAX_PINNED_AT_ONE,
        "A cap of one request per minute is the signature of a 429 arriving after a quiet "
        "minute, not a real limit. Clear `learned` for those buckets in "
        "state/cascade_scratch.db. The router now floors this at 2 and expires it after 6h, so "
        "a fresh occurrence means something is generating 429 storms again -- check worker "
        "count against bucket count.", "high", "pool"))

    # A RATE NEEDS A DENOMINATOR BIG ENOUGH TO CARRY IT. `tot = max(sum(...), 1)` was a
    # div-by-zero guard, and on a window with NO calls at all it made the arithmetic read
    # errs=0 over tot=1 -- a clean "100% ok" that HELD, reported off a pool that had not
    # answered once. That is the fabricated `0.0% (0 of 0)` of 2026-08-24 wearing the other
    # face: the completeness audit invented a red off an empty file, this invented a GREEN.
    # A single failed call was equally loud in the other direction, rendering "0% ok" as
    # though one sample were a rate.
    #
    # The remedy is the one completeness.py already settled on for the same shape -- when the
    # sample cannot support a judgment, say so and decline to render one, rather than
    # computing a percentage nobody should act on. UNMEASURED is reported as a breach (not a
    # quiet hold) for the same reason the `every source is fully catalogued` standard is: a
    # standard that cannot see is not a standard that is satisfied. This costs no alarm
    # accuracy, because a window too thin to judge is a window `model calls per hour` above
    # has ALREADY failed on volume -- the two lines then name one cause together instead of
    # one of them printing reassurance over it.
    calls = sum(b["calls"] for b in tp.get("buckets", []))
    errs = sum(b["calls"] - b["ok"] for b in tp.get("buckets", []))
    if calls < MIN_CALLS_TO_JUDGE_RATE:
        out.append(_s(
            "calls that succeed", False,
            "UNMEASURED -- %d call(s) in the %d-min window, below the %d needed to judge a "
            "rate. This is too thin a sample to measure, NOT a pool measuring healthy."
            % (calls, tp.get("window_min", 15), MIN_CALLS_TO_JUDGE_RATE), "50%",
            "The pool is not being ASKED enough to tell whether it answers. Read `model calls "
            "per hour` above -- it is the same fault seen from the volume side, and it is the "
            "one to work. Do not read this line as a failure rate either way.",
            "medium", "pool"))
    else:
        out.append(_s(
            "calls that succeed", (errs / calls) <= 0.5,
            f"{1 - errs / calls:.0%} ok of {calls}", "50%",
            "Half the calls are failing. Look at which buckets: a 413 means the prompt exceeds "
            "that provider's token cap, a 401 means a dead key, a 429 means real contention.",
            "medium", "pool"))

    # THE THROTTLE THAT DECIDES THROUGHPUT IS NOT ON THIS PAGE, AND IT IS THE ANSWER TODAY.
    #
    # Measured run #27, and it closes the pool question runs #16, #18 and #26 all worked with
    # the wrong instrument. `model calls per hour` read 112 against a floor of 900 while all
    # four sub-standards above read GREEN and 29 buckets held headroom. None of them can see
    # why, because the binding constraint is not in the pool at all -- it is a semaphore in the
    # reader:
    #
    #   tuning.regime()  -> "local"   (cloud success 33.3% over 24 calls, floor 35% -- it lost
    #                                  by 1.7 points)
    #   read._gate()     -> _GATE_LOCAL, which holds GATE_LOCAL_N = 2 permits, not 16
    #   tuning.profile() -> workers 2, not 16
    #
    # and `read._ask` runs the WHOLE transport ladder inside that gate -- including the cloud
    # attempt, which never touches the card the gate exists to protect. Two calls in flight
    # instead of sixteen is 1/8th the rate, and 900/8 = 112.5 against an observed 112.
    #
    # That last arithmetic is why this standard exists rather than a comment. The number was
    # derivable from two other numbers all along and nothing on the page multiplied them, so
    # three runs read four green sub-standards under a red headline and went looking in the
    # pool. THE ORDER TEXT ON `model calls per hour` NAMED TWO CANDIDATE CAUSES AND THIS WAS
    # NEITHER; it has been amended to send the next run here first.
    #
    # IT OSCILLATES, AND THAT IS THE STRONGEST EVIDENCE THERE IS. Twelve minutes after the
    # measurement above, the same three calls read `cloud`, 16 of 16 permits, 53% ok over 70
    # calls -- and `model calls per hour` had gone 112 -> 280 with nothing changed and nothing
    # restarted. The regime had crossed back over a 35% threshold it lost by 1.7 points, and
    # throughput moved with it. So this is not a stuck switch to be flipped once; it is a
    # constraint that binds and releases on its own, which is precisely why a snapshot standard
    # is the right instrument and why reading `model calls per hour` alone can never explain it.
    #
    # DELIBERATELY A REPORT, NOT A REMEDY. Whether a starved machine SHOULD squeeze cloud calls
    # through the card's semaphore is a routing-policy question with real blast radius (it sets
    # concurrency against a shared GPU and a free-tier pool at once), and it is in NEXT_STEPS
    # for the owner. This standard only makes the state legible; it changes no routing. It reads
    # green whenever the gate is wide, so on a healthy cloud regime it costs nothing.
    try:
        import tuning as _T
        import read as _R
        _regime = _T.regime()
        _gate_n = _R.GATE_CLOUD_N if _regime == "cloud" else _R.GATE_LOCAL_N
        out.append(_s(
            "the reader's gate is open", _regime == "cloud",
            "%s, %d of %d permits (%s)" % (_regime, _gate_n, _R.GATE_CLOUD_N, _T.profile()["why"]),
            "cloud regime, full width",
            "THE READER IS THROTTLING ITSELF, AND THIS OUTRANKS EVERY POOL STANDARD ABOVE WHEN "
            "IT IS RED. `read._ask` runs its whole transport ladder -- cloud attempt included -- "
            "inside the gate `tuning.regime()` selects. On 'cloud' that gate is GATE_CLOUD_N "
            "wide and never binds. On 'local' or 'starved' it is GATE_LOCAL_N, which is the "
            "CARD's parallelism (OLLAMA_NUM_PARALLEL, normally 2), so at most two model calls "
            "of ANY kind are in flight -- and `tuning.profile()` drops the worker count to "
            "match. Multiply it out before blaming the pool: ceiling = floor * "
            "GATE_LOCAL_N / GATE_CLOUD_N. The parenthesised text is `regime.why`, which names "
            "the exact measurement that chose the regime -- read it, because the usual cause is "
            "the cloud success rate losing to CLOUD_MIN_SUCCESS by a point or two, and that is "
            "a self-feeding loop: a narrow gate makes few calls, few calls make a small and "
            "noisy sample, and a bad sample keeps the gate narrow.",
            "high", "pool"))
    except Exception:
        silence.note("standards.py:reader-gate")
        _dropped.append("reader-gate")

    # ------------------------------------------------------------------ the corpus read
    read = jobs.get("corpus read")
    if read:
        out.append(_s(
            "chunks nobody answered", not (read.get("warn") or ""), read.get("warn") or "none",
            "none",
            "A passage was sent to every transport and none replied. The entity is NOT cached "
            "when this happens so nothing is lost -- but it means the pool and the GPU declined "
            "together, which is capacity, not reading.", "high", "read"))
        eta = read.get("eta_h", 0)
        out.append(_s(
            "corpus read finishes inside a day", eta <= MAX_ETA_HOURS, f"{eta:.1f}h",
            f"{MAX_ETA_HOURS}h",
            "At this rate the read does not finish overnight. The lever is providers, not code, "
            "once the pool standards above all hold.", "medium", "read"))
        det = read.get("detail") or ""
        feats = 0
        for part in det.split("·"):
            if "feats" in part:
                feats = int("".join(c for c in part if c.isdigit()) or 0)
        per_chunk = feats / max(read.get("done", 1), 1)
        out.append(_s(
            "feats per chunk", per_chunk >= MIN_FEATS_PER_CHUNK, f"{per_chunk:.2f}",
            MIN_FEATS_PER_CHUNK,
            "The reader is running and extracting almost nothing. Either the queue has reached "
            "thin entities -- normal late in a pass -- or the model is returning text that "
            "fails the verbatim check. Compare against the fabrication standard below.",
            "medium", "read"))
        prog = read.get("done", 0) / max(read.get("total", 1), 1)
        out.append(_s(
            "corpus read is progressing", prog > 0, f"{prog:.1%}", "above 0",
            "No chunk has completed. Check that read.py printed its transport banner and that "
            "the queue is not empty.", "high", "read"))

    roll = jobs.get("page roll")
    if roll:
        prog = roll.get("done", 0) / max(roll.get("total", 1), 1)
        out.append(_s(
            "page roll complete", prog >= MIN_ROLL_PROGRESS, f"{prog:.0%}",
            f"{MIN_ROLL_PROGRESS:.0%}",
            "Mining has not finished its pass. It is network-bound and unaffected by model "
            "quota, so a stall here is a host problem: check the failure ledger for a spike of "
            "HTTPError against one host.", "low", "read"))

    # ------------------------------------------------------------------ the library
    cov = lib.get("coverage") or {}
    if cov:
        out.append(_s(
            "coverage figures are current", cov.get("age_h", 99) <= MAX_COVERAGE_AGE_H,
            f"{cov.get('age_h', 0):.1f}h", f"{MAX_COVERAGE_AGE_H}h",
            "The cited/settled percentages predate whatever has run since. coverage.py runs at "
            "the end of each supervisor cycle; if it is stale, cycles are not completing.",
            "low", "library"))
        n = max(cov.get("entries", 1), 1)
        out.append(_s(
            "entries settled", cov.get("settled", 0) / n >= MIN_SETTLED,
            f"{cov.get('settled', 0) / n:.0%}", f"{MIN_SETTLED:.0%}",
            "Settled means cited or read-with-nothing-found. Unsettled entries are ones nobody "
            "has looked at. Raising it is the corpus read's job.", "low", "library"))
    src = lib.get("sources") or {}
    if src.get("total"):
        frac = src.get("with_host", 0) / src["total"]
        out.append(_s(
            "sources with a reachable wiki", frac >= MIN_HOST_COVERAGE, f"{frac:.0%}",
            f"{MIN_HOST_COVERAGE:.0%}",
            "Sources without a host are uncitable by construction. Run "
            "`python src/hostcheck.py --adopt --go`. For homebrew, try D&D Wiki and the "
            "publisher's own site -- homebrew is inconsistent about where it lives.",
            "medium", "library"))

    # ------------------------------------------------------------------ the code
    out.append(_s(
        "every module imports", len(w.get("broken") or []) <= MAX_BROKEN_MODULES,
        len(w.get("broken") or []), MAX_BROKEN_MODULES,
        "A module that will not import is one nobody knows is broken -- verify_math sat dead for "
        "an unknown period and every number it checks was unverified for exactly that long. "
        "Run `python src/allsweep.py` and fix what the IMPORT tier names.", "high", "code"))
    out.append(_s(
        "no high-severity findings open", w.get("high", 0) <= MAX_HIGH_FINDINGS,
        w.get("high", 0), MAX_HIGH_FINDINGS,
        "The standing sweep believes some code does something other than what it says. Read "
        "WATCH.md, confirm or refute each, then fix or retire it.", "medium", "code"))
    ph = lib.get("phases") or []
    missing = [p["name"] for p in ph if not p["built"]]
    out.append(_s(
        "phases implemented", len(missing) <= MAX_PHASES_MISSING,
        f"{len(ph) - len(missing)}/{len(ph)}", f"at least {len(ph) - MAX_PHASES_MISSING}",
        "A phase the runner names but nobody wrote stops the pipeline cleanly at that point and "
        "everything after it never runs. Missing: " + (", ".join(missing) or "none"),
        "low", "code"))
    # PROBING IS NOT FAILING.
    #
    # This counted every swallowed exception and breached at 13,066 -- of which 11,774 were
    # HTTPErrors from `endpoint.detect` and `hostcheck.probe`, where a failed request IS the
    # measurement. Detection tries six paths per host and expects five to fail; the scout tries
    # eight URLs and expects most to 404. Counting those as faults means the standard is
    # permanently red for doing its job, which trains its reader to ignore it -- the exact
    # failure mode every floor here is written to avoid.
    #
    # So the classes whose failures are the method are counted separately and reported, not
    # judged. What is judged is everything else.
    ledger = {}
    try:
        with open(os.path.join(HERE, "state", "failures.json"), encoding="utf-8") as f:
            ledger = json.load(f)
    except Exception:
        silence.note("standards.py:ledger")
    probe = sum(v for k, v in ledger.items()
                if any(t in k for t in ("endpoint.py:detect", "endpoint.py:fetch",
                                        "hostcheck.py:probe", "hostcheck.py:candidates",
                                        "hostcheck.py:relevance", "scout.py:verify")))
    real = sum(ledger.values()) - probe
    out.append(_s(
        "unexpected swallowed failures", real <= MAX_SWALLOWED_NEW, f"{real:,}",
        f"{MAX_SWALLOWED_NEW:,}",
        "Excludes the probe classes, where a failed request is the measurement. What remains is "
        "something upstream failing and being tolerated. The class names the module and the "
        "line; `python src/health.py --failures` lists them. Note the ledger is CUMULATIVE -- "
        "the foreman archives it after triage so a fault that was fixed stops counting.",
        "medium", "code"))
    out.append(_s(
        "probe failures (reported, not judged)", True, f"{probe:,}", "no floor",
        "Requests that failed as part of finding something out: endpoint detection trying six "
        "paths, the scout trying eight URLs. Volume here is work, not damage.",
        "low", "code"))
    # ------------------------------------------------------------------ evidence integrity
    #
    # Everything above measures whether the machinery RUNS. These measure whether what it
    # produced can be believed, which is a different question and the one the library is for.

    # Cached on a 2-minute clock: 531 file-opens per call, on a check the dashboard polls
    # every five seconds, for an answer that only changes when the reader finishes an entity.
    unans_files = 0
    try:
        import glob as _g
        now_m = time.time()
        if now_m - _UNANS_CACHE["at"] < 120:
            unans_files = _UNANS_CACHE["n"]
        else:
            for fp in _g.glob(os.path.join(HERE, "data", "readfeats", "**", "*.json"),
                              recursive=True):
                with open(fp, encoding="utf-8") as f:
                    head = f.read(700)
                if '"chunks_unanswered": 0' not in head and "chunks_unanswered" in head:
                    unans_files += 1
                elif "chunks_unanswered" not in head:
                    unans_files += 1          # written before the guard existed
            _UNANS_CACHE.update({"at": now_m, "n": unans_files})
    except Exception:
        silence.note("standards.py:unanswered-records")
    out.append(_s(
        "cached records that were fully read", unans_files <= MAX_UNANSWERED_RECORDS,
        unans_files, MAX_UNANSWERED_RECORDS,
        "A record written while some of its chunks went unanswered is PERMANENTLY incomplete -- "
        "read_entity returns the cache forever after and queue never revisits it. Delete those "
        "files so the entities are read again; the guard in read.py stops new ones appearing.",
        "high", "evidence"))

    # THIS STANDARD HAD NEVER RUN. NOT ONCE. Repaired run #28.
    #
    # It read `read.get("raw")` -- a job-dict key NOTHING in the tree has ever written. The
    # search was therefore always against `""`, `drop` was always None, `fab` stayed None, and
    # the `if fab is not None` below meant the standard was never even APPENDED. It did not
    # read green; it was ABSENT, which on a page of green is indistinguishable from green.
    # The number it wanted was in the read log all along and `dashboard.RE_READ` had been
    # capturing it as `dropped` the whole time -- `_read_row` parsed it and dropped it on the
    # floor one line later. Both halves are fixed; this reads the job dict's `dropped`.
    #
    # AND THE SELF-CHECK THAT EXISTS TO CATCH EXACTLY THIS DID NOT CATCH IT. `every declared
    # floor is measured` greps `check()`'s source for each floor's NAME, and MAX_FABRICATION
    # *is* named here -- on a line that could never execute. A source-grep cannot tell a used
    # constant from an unreachable one, which is NEXT_STEPS §2's "behavioural checks to replace
    # verify_math's source-greps" arriving in a second file, on the guard against the model
    # inventing evidence. Worth stating plainly: for its entire life this project had no live
    # measurement of its own fabrication rate.
    #
    # IT IS APPENDED UNCONDITIONALLY NOW, INCLUDING WHEN IT CANNOT BE MEASURED. A standard that
    # vanishes on a missing input is green by absence -- the exact defect batch 03 catalogued
    # across the data-file-backed standards in this file, and the one that hid this bug for its
    # whole life. UNMEASURED is a reading; silence is not.
    fab = None
    why = ""
    read = jobs.get("corpus read")
    if not read:
        why = "the reader has logged no progress line yet"
    else:
        det = read.get("detail") or ""
        try:
            import re as _re
            kept = int((_re.search(r"([\d,]+) feats", det).group(1)).replace(",", ""))
            drop = read.get("dropped")
            if drop is None:
                why = "the reader's progress line carried no `dropped` count"
            elif (kept + int(drop)) == 0:
                why = "no sentences have been judged yet (kept + dropped is 0)"
            else:
                fab = int(drop) / (kept + int(drop))
        except Exception:
            silence.note("standards.py:fabrication")
            why = "the reader's progress line did not parse"
    out.append(_s(
        "sentences that survive the verbatim check",
        # UNMEASURED IS NOT GREEN. This read `True if fab is None else ...`, so the one state
        # the order text below calls out by name -- "IF THIS READS UNMEASURED, TREAT THAT AS
        # THE FINDING" -- was the state that satisfied the standard. The row and its own
        # boolean said opposite things, and `work_orders()` reads the boolean, so the finding
        # could never be dispatched. Run #28 fixed the standard's ABSENCE and left its
        # emptiness green, one line under its own comment about green-by-absence; this is the
        # same defect one layer in. A guard that cannot measure has not passed.
        # (run #29, batch 03, reproduced.)
        fab is not None and fab <= MAX_FABRICATION,
        f"{fab:.0%} rejected" if fab is not None else "UNMEASURED -- %s" % why,
        f"{MAX_FABRICATION:.0%}",
        "The model is returning text that is not in the source. A rate this high means the "
        "passage is being truncated before it arrives -- check the chunk size against the "
        "model's context -- or that a weak fallback model is carrying the run. "
        "IF THIS READS UNMEASURED, TREAT THAT AS THE FINDING: this standard silently did not "
        "exist from the day it was written until run #28, because it read a job-dict key that "
        "nothing sets, so an absent reading here is exactly the failure mode that hid it. "
        "The input is `dropped` in `state/read_auto.log`, captured by `dashboard.RE_READ` and "
        "carried into the job dict by `dashboard._read_row`.",
        "high", "evidence"))

    try:
        with open(os.path.join(HERE, "data", "ROSTER_AUDIT.json"), encoding="utf-8") as f:
            ra = json.load(f)
        # Only rows the audit says it CAN judge, and only sources still holding a roster. Four
        # were being reported: two already purged, and two sourcebooks the test cannot speak to.
        # A standard that counts findings nobody can act on is a standard nobody reads.
        try:
            with open(os.path.join(HERE, "data", "ROSTER_PURGES.json"), encoding="utf-8") as f:
                purged = set(json.load(f))
        except Exception:
            silence.note("standards.py:370")
            purged = set()
        foreign = [k for k, v in ra.items()
                   if isinstance(v, dict) and v.get("rate", 1) < 0.10
                   and v.get("judgeable", True) and k not in purged]
        out.append(_s(
            "rosters that name their own fiction", len(foreign) <= MAX_FOREIGN_ROSTERS,
            len(foreign), MAX_FOREIGN_ROSTERS,
            "A source whose mined pages never mention it was catalogued from the wrong wiki. "
            "That proves the HOST was wrong, not necessarily the roster -- read each one before "
            "purging, then `hostcheck.py --purge --go --source NAME`. `Lost Mines of "
            "Phandelver` held the cast of the television series Lost.",
            "medium", "evidence"))
    except Exception:
        silence.note("standards.py:roster-audit")
        _dropped.append("roster-audit")

    try:
        with open(os.path.join(HERE, "data", "SHELFMARKS.json"), encoding="utf-8") as f:
            marks = json.load(f)
        addrs = [v.get("address") for v in marks.values() if isinstance(v, dict)]
        collisions = len(addrs) - len(set(addrs))
        out.append(_s(
            "shelfmarks are unique", collisions <= MAX_SHELFMARK_COLLISIONS, collisions,
            MAX_SHELFMARK_COLLISIONS,
            "Two worlds sharing an address means the Ladder cannot tell them apart, and every "
            "citation to either is ambiguous. The address space has 115,000x headroom, so a "
            "collision is a bug in assignment rather than exhaustion.",
            "high", "evidence"))
    except Exception:
        silence.note("standards.py:shelfmarks")
        _dropped.append("shelfmarks")

    # ------------------------------------------------------------------ the instrument itself
    #
    # The Assay is the library's one original claim. If its arithmetic drifts, everything shelved
    # under it is wrong in a way no amount of correct mining can rescue.

    try:
        with open(os.path.join(HERE, "data", "REFERENCE_ASSAYS.json"), encoding="utf-8") as f:
            refs = json.load(f)
        # COMPUTED against PUBLISHED, not a flag somebody remembered to write. The first draft
        # of this looked for `inside_charter_interval`, a key the file has never had, and
        # reported 0/3 -- an alarm about the instrument being broken, raised by a standard that
        # was itself broken. Recomputing from the two numbers that actually exist means the
        # check cannot drift from what it claims to check.
        inside = 0
        for v in refs.values():
            if not isinstance(v, dict):
                continue
            ch = v.get("charter") or []
            got = (v.get("reference") or {})
            if len(ch) >= 3 and got.get("magnitude"):
                band = str(ch[0])
                published, tol = float(ch[1]), float(ch[2])
                mine = float(str(band)[1:]) + float(got.get("decimal", 0))
                if abs(mine - published) <= tol:
                    inside += 1
        out.append(_s(
            "hand-built assays match the charter", inside >= len(refs) if refs else True,
            f"{inside}/{len(refs)}", "all of them",
            "The three reference assays reconstruct values the charter published. If one falls "
            "outside its interval, the instrument has drifted from the document it implements -- "
            "check assay.SIGMA_BY_ATTESTATION and the axis weights before trusting any new "
            "Magnitude.", "high", "instrument"))
    except Exception:
        silence.note("standards.py:reference-assays")
        _dropped.append("reference-assays")

    # (the charter-regression verdict is `charter_regression_verdict()`, below check())
    # The standard above proves the ARITHMETIC; this one proves the AUTOMATION. calibrate()
    # runs the charter's six published assays through the whole live chain -- evidence mine,
    # split, epoch mandate, ceiling clamp, cascade transport -- and persists the verdict.
    # Consistency is interval overlap (see calibrate's docstring). A file older than 26h means
    # the regression has not run today and the foreman dispatches it; that is the freshness
    # floor, not a fault in the instrument.
    try:
        reg_path = os.path.join(HERE, "data", "CHARTER_REGRESSION.json")
        try:
            with open(reg_path, encoding="utf-8") as f:
                reg = json.load(f)
        except Exception:
            silence.note("standards.py:449")
            reg = None
        holds, obs = charter_regression_verdict(reg)
        out.append(_s(
            "the automation reproduces the charter", holds, obs,
            "every scored reference overlaps its published interval, within 26h",
            "The charter's six published assays re-run end-to-end through the live automation "
            "daily -- the same code path a stranger's entity takes. A reference that stops "
            "overlapping its published interval means something in the chain drifted (prompt, "
            "gate, clamp, transport), and every number published since the drift is suspect.",
            "high", "instrument"))
    except Exception:
        silence.note("standards.py:charter-regression")
        _dropped.append("charter-regression")

    # THE COUNTERS MUST MOVE. The job-advancing standard watches LOG GROWTH, and a job whose
    # every model call fails grows its log beautifully -- 2026-08-23 evening: fourteen
    # processes alive, logs streaming timeout lines, and cited/settled/feats/entities-read
    # flat for 36 minutes. The owner saw it on the movement panel before anything here did.
    # So the panel's own history is the measurement: if every output counter is unchanged
    # across 45 minutes of samples, the system is running and producing nothing, whatever
    # the logs say. The remedy chain (reprove the pool, restart the reader) is safe to fire
    # even when the true cause is an empty evening pool -- it converts a silent stall into a
    # measured one.
    try:
        hist_p = os.path.join(HERE, "state", "dashboard_history.json")
        with open(hist_p, encoding="utf-8") as f:
            hist = [h for h in json.load(f) if isinstance(h, dict)]
        now_t = time.time()
        window = [h for h in hist if now_t - h.get("at", 0) <= 45 * 60]
        span_min = (window[-1]["at"] - window[0]["at"]) / 60 if len(window) >= 2 else 0
        counters = ("cited", "settled", "feats", "entities read")
        # A STANDARD THAT DOES NOT EMIT IS WORSE THAN ONE THAT FAILS: it does not appear on the
        # page at all, so nobody can even see that it went unmeasured. This block used to skip
        # `out.append` entirely when the history was shorter than 40 minutes -- and the history
        # is short after EVERY dashboard restart, which the keeper does routinely. Caught in run
        # #25's closing diagnostic: bouncing the dashboard dropped a HIGH-severity throughput
        # standard clean off the page for 40 minutes, and `every declared floor is measured`
        # went on reporting "all measured" the whole time, because it can only inspect rows that
        # exist. The check that exists to catch an unmeasured floor cannot see an absent one.
        #
        # It now always emits. Short history reports `holds=True` -- deliberately, so no remedy
        # fires on absent evidence, which would be crying wolf -- but SAYS so in `observed`, so
        # the page shows "not enough history yet" rather than showing nothing.
        moved = sum(1 for k in counters
                    if len({h.get(k) for h in window if h.get(k) is not None}) > 1)
        _enough = span_min >= 40
        out.append(_s(
            "the library's counters are moving", (moved > 0) if _enough else True,
            (f"{moved}/{len(counters)} moved in {span_min:.0f}m" if _enough
             else f"not enough history yet ({span_min:.0f}m of 40)"), ">= 1 in 45m",
            "Cited, settled, feats and entities-read are the library's output. All four "
            "flat while jobs run means every model call is failing -- log growth cannot "
            "see that, only the counters can.", "high", "throughput"))
    except Exception:
        silence.note("standards.py:counters-moving")
        _dropped.append("counters-moving")

    try:
        with open(os.path.join(HERE, "data", "ALLSWEEP.json"), encoding="utf-8") as f:
            sweep = json.load(f)
        bad_files = len(((sweep.get("estate") or {}).get("artifacts") or {}).get("bad") or [])
        out.append(_s(
            "files that parse", bad_files <= MAX_CORRUPT_FILES, bad_files, MAX_CORRUPT_FILES,
            "A record that will not load is skipped in silence by every stage that reads it, so "
            "a corrupt cache is indistinguishable from an empty one -- and empty is a legitimate "
            "finding here. `allsweep.py` names the files.", "high", "instrument"))

        crashed = [v for v in (sweep.get("verifiers") or [])
                   if v.get("crashed") or v.get("timeout")]
        out.append(_s(
            "verifiers all run", not crashed, len(crashed), 0,
            "A verifier that crashes stops verifying and says nothing. `verify_math` sat dead "
            "for an unknown period and every number it checks was unverified for exactly that "
            "long.", "high", "instrument"))
        age = (time.time() - os.path.getmtime(
            os.path.join(HERE, "data", "ALLSWEEP.json"))) / 3600
        out.append(_s(
            "the full audit is recent", age <= MAX_SWEEP_AGE_H, f"{age:.1f}h",
            f"{MAX_SWEEP_AGE_H}h",
            "`allsweep` is what notices a module that stopped importing. Stale, it is reporting "
            "the health of a system that no longer exists. overwatch runs it every round.",
            "medium", "instrument"))
    except Exception:
        silence.note("standards.py:allsweep")
        _dropped.append("allsweep")

    # ------------------------------------------------------------------ is the cast all here?
    try:
        with open(os.path.join(HERE, "data", "COMPLETENESS.json"), encoding="utf-8") as f:
            comp = json.load(f)
        good = [c for c in comp if not c.get("unreliable")]
        wiki = sum(c.get("wiki_persons") or 0 for c in good)
        have = sum(c.get("catalogued_persons") or 0 for c in good)
        cov = (have / wiki) if wiki else 0.0
        # ALL OF THEM, WORST FIRST -- not `[:3]`. A cap here is the same shape as the
        # `[:3]`/`[:60]` fix on the unrecognised-pool standard above (see that block's note,
        # "which is lesson 14: fix a shape, then grep the tree for it"): it silently decided
        # which sources "count" as the worst-covered, and every source past the cutoff read
        # as fine on the page that exists to catch exactly this.
        worst = sorted(good, key=lambda c: c.get("coverage", 0))
        detail = "; ".join("%s %.1f%%" % (str(c["source"])[:18], 100 * c.get("coverage", 0))
                           for c in worst)
        # NO DENOMINATOR IS NOT ZERO COVERAGE. With an empty or all-unreliable COMPLETENESS.json
        # the arithmetic above yields a clean-looking `0.0% (0 of 0)`, and this standard is HIGH
        # severity, so a file the audit failed to write outranked every real fault in the queue
        # for two hours on 2026-08-24 while accusing the catalogue of holding nothing. The fault
        # is real either way -- an unmeasured library is not a measured one -- but the operator
        # must be told which of the two it is, because the repairs point in opposite directions:
        # a true 0% wants `catalogue_web --recatalogue`, an unmeasured one wants the transport
        # looked at.
        if not wiki:
            reading = ("UNMEASURED -- %d row(s) in COMPLETENESS.json, %d measurable, no "
                       "denominator obtained. This is the audit failing to measure, NOT the "
                       "catalogue measuring empty." % (len(comp), len(good)))
        else:
            reading = "%.1f%% (%s of %s) -- worst: %s" % (100 * cov, f"{have:,}",
                                                          f"{wiki:,}", detail)
        out.append(_s(
            "every source is fully catalogued", bool(wiki) and cov >= MIN_CATALOGUE_COVERAGE,
            reading,
            "100%",
            "The wikis' own categoryinfo says how many characters each source has; the "
            "catalogue says how many it holds. Every point of shortfall is a character that "
            "reads, from inside the library, as NOT IN THAT FICTION rather than not reached "
            "yet. Molecule Man, Mister Mxyzptlk and the Black Winter were all in that gap. The "
            "remedy starts `catalogue_web --recatalogue --shortfall 100`, largest gap first, "
            "and re-measures afterwards.",
            "high", "library"))
    except Exception:
        silence.note("standards.py:catalogue-coverage")
        _dropped.append("catalogue-coverage")

    # ------------------------------------------------------------------ derived data is FRESH
    #
    # Nothing enforces the dependency order recatalogue -> character sweep -> feats roll ->
    # read -> assay. After the uncapped Marvel pull (1,051 -> 30,207 entries) every downstream
    # stage kept reading the OLD sweep: magnitude.queue, hostcheck.entities_by_source and the
    # chain's index all silently excluded 29,000 new entities while reporting normally. Stale
    # derived data is this project's defect with a lineage: each stage is individually honest
    # about inputs that are collectively out of date.
    try:
        import glob as _g
        sweep_p = os.path.join(HERE, "data", "CHARACTER_SWEEP.json")
        sweep_m = os.path.getmtime(sweep_p)
        newest_rec = max((os.path.getmtime(f) for f in
                          _g.glob(os.path.join(HERE, "data", "records", "*.json"))),
                         default=0.0)
        lag_h = (newest_rec - sweep_m) / 3600.0
        out.append(_s(
            "the character sweep is newer than the catalogue", lag_h <= 1.0,
            ("fresh" if lag_h <= 1.0 else "%.1fh behind the newest record" % lag_h), "fresh",
            "A record was re-catalogued after the sweep last ran, so every consumer of "
            "CHARACTER_SWEEP.json -- the assay queue, the host fitness roster, the chain's "
            "entity index -- is working from a cast list that no longer matches the shelves. "
            "The remedy starts `sweep.py`; the feats roll and the reader then pick the new "
            "entities up on their own next cycle.",
            "high", "library"))
    except Exception:
        silence.note("standards.py:sweep-freshness")
        _dropped.append("sweep-freshness")

    # ------------------------------------------------------------------ jobs that are ADVANCING
    #
    # Not "is it running". Whether it has produced a single byte since the last time anyone
    # looked. A log's size is the cheapest honest proxy for work done: every long-running job
    # here prints progress, so a log that has not grown is a job that has not progressed.
    try:
        import overnight as _ON
        prev = {}
        if os.path.exists(JOB_WATCH):
            with open(JOB_WATCH, encoding="utf-8") as f:
                prev = json.load(f)

        import lognames as LN
        now = time.time()
        stalled, watched, cur = [], 0, {}
        # THE MANAGED JOBS, BY NAME, not every *.log in the directory. Deriving the job from the
        # log filename asked whether `read_auto.py` was running -- no such script exists -- so
        # the three jobs that matter were never watched, while stale legacy logs whose stems
        # collide with a live script name (`read.log` beside a running `read.py`) were. See
        # lognames.OWNER for the full account.
        for fn, owner in sorted(LN.OWNER.items()):
            job = fn[:-4] if fn.endswith(".log") else fn
            path = os.path.join(HERE, "state", fn)
            try:
                size = os.path.getsize(path)
            except Exception:
                silence.note("standards.py:job-size")
                continue

            # WHEN DID IT LAST MOVE, not when did this check last run. `at` was re-stamped to
            # `now` on every pass, so `quiet_min` measured the interval between two consecutive
            # standards runs -- a few minutes, always -- and could not reach the 15-minute floor
            # no matter how long a job had actually been silent. The standard this file's own
            # docstring calls "the failure this whole library is built to refuse" was therefore
            # structurally unable to fire, for any job, and had been reporting "all advancing"
            # by construction. Carrying the stamp forward while the size holds is what makes the
            # number mean silence. (Found 2026-08-23; regression pinned in verify_math.)
            p = prev.get(job)
            held, stamp = job_stamp(p, size, now)
            cur[job] = {"size": size, "at": stamp}

            # Only a job whose process is UP can stall. A finished job's log stops growing
            # because it is finished, and calling that a fault would cry wolf on every
            # completed run -- which is how a standards system gets ignored.
            alive = False
            try:
                alive = bool(_ON.running(owner))
            except Exception:
                silence.note("standards.py:job-alive")
            if not alive:
                continue
            watched += 1
            if not held:
                continue
            quiet_min = (now - cur[job]["at"]) / 60.0
            if quiet_min >= MAX_JOB_SILENCE_MIN:
                stalled.append("%s (%d min, %d bytes)" % (job, round(quiet_min), size))

        tmp = JOB_WATCH + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(cur, f)
        silence.replace_retry(tmp, JOB_WATCH)

        out.append(_s(
            "every running job is advancing", not stalled,
            ", ".join(stalled) or ("%d running, all advancing" % watched),
            "no silent job",
            "A process that is UP and producing nothing is the failure this whole library is "
            "built to refuse, and until now the only check on it asked whether the process "
            "existed. Read the named log's tail: a job repeating one line is looping, a job "
            "silent from its first line is wedged on its first unit of work. `dashboard.py` "
            "already flags this in its movement panel -- if the panel says stalled and this "
            "standard does not, the two are measuring different things and this one is wrong.",
            "high", "machine"))
    except Exception:
        silence.note("standards.py:job-advance")
        _dropped.append("job-advance")

    # A POOL FAILURE NOBODY CAN NAME IS THE ONE TO WORK FIRST.
    #
    # Owner ruling 2026-08-25: "an unrecognised failure should be immediately investigated and
    # resolved upon spotting it." This standard is the spotting. `cascade_bridge` classifies a
    # refusal as permanent (bench 4h) or as a deadline (bench, doubling); anything else used to
    # fall through with its reason discarded, which is how the pool ran at 64 calls/hour against
    # a floor of 900 while all four of its sub-standards read green. Every such failure now
    # lands in `state/POOL_UNRECOGNISED.json` WITH ITS TEXT, and this puts it on the page.
    #
    # The remedy is deliberately a human/maintenance one, not a scripted bench: the point is to
    # NAME the fault and either classify it (add it to the permanent list) or fix it, not to
    # absorb it quietly. Rows age out after 24h, so a resolved fault leaves the page by itself.
    try:
        import cascade_bridge as _CB
        _unrec = _CB.unrecognised_open()
        # EVERY ROW, ITS WHOLE TEXT, AND ITS AGE. This expression used to carry THREE caps at
        # once on the one field the order below tells a person to read: `[:3]` kept only the
        # three highest-count rows, `[:60]` cut each error mid-sentence, and neither said how
        # old the row was. Measured run #27: fourteen rows were open and the page showed three.
        # All fourteen were the SAME shape (`All 1 candidates failed: <label>`) -- one fault
        # wearing fourteen bucket names -- and the cap is why nobody could see that. Run #26
        # read the top row, chased it alone, and recorded the other thirteen as "the third row
        # was genuinely unexplained"; the shape was invisible from three samples. This is m145's
        # sentence exactly (`available_sample: models[:8]`, a cap on the field a person reads to
        # act) in a second file, which is lesson 14: fix a shape, then grep the tree for it.
        #
        # THE AGE IS NOT DECORATION. The order below used to end "anything here is happening
        # NOW", which is false and falsely reassuring in the expensive direction: rows live for
        # 24h, so a fault fixed at 06:40 keeps this HIGH standard red until the next morning and
        # reads exactly like a live fire. All fourteen open rows this run predated the fix that
        # resolved them. Printing the age lets the next run tell a fossil field from a fire
        # without opening the ledger, and costs nothing when the rows really are fresh.
        _now = time.time()
        _rows = sorted(_unrec, key=lambda r: -float(r.get("last_seen", 0)))
        out.append(_s(
            "every pool failure is recognised", not _unrec,
            "; ".join("%s: %s (x%d, %.1fh old)"
                      % (r.get("bucket"), str(r.get("error")),
                         int(r.get("count", 0)),
                         (_now - float(r.get("last_seen", 0))) / 3600.0)
                      for r in _rows) or "none",
            "no unrecognised refusal",
            "Each row is a provider failing for a reason this code cannot name, so it is "
            "neither benched as permanent nor backed off as contention -- it just burns a "
            "claim and a deadline, repeatedly. READ THE ERROR TEXT IN THE ROW. If it is a "
            "permanent refusal (a dead key, a spent account, a retired model), add its wording "
            "to the `permanent` tuple in `cascade_bridge._ask_call` and it will be benched for "
            "four hours from then on. If it is a transport or parse fault, it is a bug and "
            "belongs in BUGS.md. READ THE AGE ON EACH ROW BEFORE BELIEVING IT IS A FIRE: rows "
            "live for 24h, so a fault you fixed an hour ago keeps this red until tomorrow and "
            "looks identical to one happening right now. If every row is hours old and none has "
            "recurred since the last bounce, the fault is already fixed and this is a fossil "
            "field waiting to age out. And READ THE ROWS AS A SET, not one at a time -- fourteen "
            "buckets all reporting `All 1 candidates failed` is ONE unnamed wrapper, not "
            "fourteen provider faults.",
            "high", "pool"))
    except Exception:
        silence.note("standards.py:unrecognised-pool")
        _dropped.append("unrecognised-pool")

    # ------------------------------------------------------------------ the machine
    # ------------------------------------------------------------------ the network
    #
    # On 2026-08-23 every fandom.com host dropped this machine's connections at the socket for
    # hours -- an IP block earned by our own 100-req/s catalogue rate -- and NOTHING on the
    # board said so. The recatalogue skipped DC as "no wiki resolved", the roll's failures piled
    # into the swallowed-ledger, and the diagnosis took a person with curl. A network-shape
    # fault deserves its own light: unreachable-with-DNS-working is a block, not an outage.
    # The probe is PINNED TO IPv4 (see `fandom_ipv4_reachable`). It used to take whatever
    # family resolved first, and on 2026-08-24 that let `community.fandom.com`'s IPv6 record
    # answer for a fleet of A-record-only content wikis that were all dead at the socket.
    try:
        _fandom_ok, _fandom_where = fandom_ipv4_reachable()
        out.append(_s(
            "fandom answers this machine", _fandom_ok,
            ("reachable over IPv4 at " + _fandom_where) if _fandom_ok
            else ("IPv4 connect fails: " + _fandom_where),
            "reachable",
            "DNS resolves but the TCP connect times out on every *.fandom.com host while "
            "Wikipedia answers normally: that is an IP block, usually earned by our own "
            "request rate. Do NOT keep retrying -- stop fandom-facing jobs (feats --roll, "
            "catalogue_web, hostcheck) and let it age out; check wiki_source.MIN_GAP stayed "
            "at its polite value. The catalogue remedy is gated on this same probe. NOTE the "
            "family: content wikis are A-record-only, so IPv4 is the only path they have, and "
            "an IPv6 route that still works does NOT mean fandom answers this machine.",
            "high", "machine"))
    except Exception:
        silence.note("standards.py:fandom-reachable")
        _dropped.append("fandom-reachable")

    try:
        import shutil as _sh
        free = _sh.disk_usage(HERE).free / 1e9
        out.append(_s(
            "disk space", free >= MIN_DISK_GB, f"{free:.0f} GB", f"{MIN_DISK_GB} GB",
            "The roll writes hundreds of megabytes an hour. Out of disk, every stage fails at "
            "once and most of them fail quietly.", "high", "machine"))
    except Exception:
        silence.note("standards.py:disk")
        _dropped.append("disk")

    # ------------------------------------------- promotions whose spine code has not caught up
    #
    # Owner amendment 2026-08-24: a source's rank follows its cast size automatically, but its
    # ADDRESS is curatorial work Hard Rule 2 reserves for the owner. So a promotion does not
    # re-shelve anything -- it raises this. Without a standard the flag would sit in a JSON file
    # nobody opens, which is the exact shape of every silent fault this project has paid for.
    try:
        with open(os.path.join(HERE, "data", "SHELF_RANKS.json"), encoding="utf-8") as f:
            _ranks = json.load(f)
        _pending = sorted(s for s, v in _ranks.items() if v.get("code_amendment_pending"))
        # ALL OF THEM, not `[:120]` characters -- that cut the joined name list mid-name, so
        # whichever source happened to fall across the 120th character read as truncated or
        # missing entirely to whoever read this row. Same shape as the two caps above.
        out.append(_s(
            "promotions have their spine codes amended", not _pending,
            (", ".join(_pending) if _pending else "none outstanding"),
            "no source outgrowing its code",
            "A source whose cast crossed a promotion floor now outranks the spine code it was "
            "given. The code cannot be rewritten automatically -- where a source sits in the "
            "Collection/Set/Series structure is the owner's judgement (Hard Rule 2), and a "
            "silently deepened address would break every cross-reference aimed at the old one. "
            "Amend the charter's Acquisitions Index, then set `rank_at_code` to the new rank in "
            "data/SHELF_RANKS.json to clear this.",
            "medium", "catalogue"))
    except FileNotFoundError:
        _ = "silence-exempt: phase 7 has not run yet, so there is nothing to rank"
    except Exception:
        silence.note("standards.py:shelf-ranks")
        _dropped.append("shelf-ranks")

    # ------------------------------------------------------ the local model is really serving
    try:
        import urllib.request as _ur
        resident, resident_raw = None, []
        try:
            with _ur.urlopen("http://localhost:11434/api/ps", timeout=8) as r:
                resident_raw = json.load(r).get("models") or []
                resident = [m.get("name") for m in resident_raw]
        except Exception:
            resident = None          # a daemon that will not answer at all is another question
        if not resident:
            # A STANDARD THAT COULD NOT BE ASKED MUST NOT SIMPLY VANISH. This used to fall
            # straight through: an 8s timeout against a busy daemon, or no model resident, and
            # the row was never appended -- so `N/N standards met` quietly counted a smaller
            # denominator and the standard read as fine by being absent. Measured on 2026-08-27:
            # the same battery passed with 44 standards declared and 44 emitted, then minutes
            # later emitted 42 while Ollama was saturated by an unrelated process holding ~9,600
            # connections to it, and the only reason anyone noticed was a check comparing
            # declared against emitted. `_dropped` is the mechanism this file already has for
            # exactly this, and the aggregate standard it feeds names what went missing.
            _dropped.append("ollama-runner-standard")
        else:
            runner = ollama_runner_up()
            # The contradiction IS the fault: the daemon cannot have a model resident with no
            # runner process holding it. When that happened the queue filled behind the missing
            # runner and stayed full, so every call 503'd forever and nothing recovered on its
            # own -- it needed `ollama.exe` restarting by hand. `runner is None` means the probe
            # itself failed and is never reported as a fault.
            out.append(_s(
                "the local model has a live runner", runner is not False,
                ("resident %s, NO llama-server process" % resident[0][:28]) if runner is False
                else ("runner up, %d resident" % len(resident)),
                "a runner for every resident model",
                "Ollama reported this model resident with no runner process on 2026-08-24; the "
                "request queue filled behind the gap and every call returned '503 maximum "
                "pending requests exceeded' for 31 minutes while `/api/tags` kept answering "
                "200, so every other liveness check in this project called it healthy. If this "
                "fires, restart ollama.exe -- the tray app respawns it -- then confirm a real "
                "call completes. Nothing drains that queue on its own.",
                "high", "machine"))

            # AND THE CONTEXT THE RUNNER IS ACTUALLY SERVING, WHICH NOTHING CHECKED.
            #
            # Ollama holds a resident model at ONE context size. A request naming a different
            # `num_ctx` needs the runner torn down and rebuilt, which `gpu_lane.py`'s measured
            # table records as "240 s+, never completed" on a card with no headroom. So a
            # `num_ctx` in config.yaml that disagrees with the resident runner does not raise
            # anything -- it makes EVERY call pay a rebuild, and the symptom is not an error but
            # a stall. That is this project's signature failure in its most expensive costume:
            # a fault that presents as slowness, so nobody looks for a fault.
            #
            # Measured 2026-08-27, which is why this exists: `read.py --run` had managed 1,659
            # of 326,617 chunks at 0.01 chunks/s -- an ETA of about 1.7 YEARS -- while the
            # resident runner served ctx=4096 and this project's config asked for 12288. Two
            # identical probe calls timed out at 240s and a third returned in 18.7s. Sixteen
            # modules read `num_ctx`, `verify_math` section 19ab already forbids hardcoding it,
            # and NOTHING compared the number we ask for against the number being served.
            #
            # Reported as a standard rather than raised: the remedy is a person's (re-pin the
            # runner, change the config, or evict whatever else is holding it), and a library
            # that refused to run whenever a context mismatched would stop for a condition it
            # can neither cause nor cure.
            served = next((m.get("context_length") for m in resident_raw
                           if m.get("context_length")), None)
            want_ctx = cfg_num_ctx()
            ctx_holds, ctx_observed = context_verdict(served, want_ctx)
            if ctx_holds is None:
                # NOT a pass. An unmeasurable context is exactly the state this whole block is
                # about, and letting it read as agreement would be the green-by-absence bug one
                # standard to the left.
                _dropped.append("ollama-context-matches-config")
            else:
                out.append(_s(
                    "the resident runner serves the context this project asks for",
                    ctx_holds, ctx_observed,
                    "the served context equals the configured one",
                    "A mismatch does not fail, it STALLS: every request rebuilds the runner, "
                    "which on a full card is minutes per call and can never drain. Either "
                    "re-pin the model at the configured size, or change config.yaml to what is "
                    "actually being served, or find what else pinned it -- on 2026-08-27 an "
                    "unrelated process had pinned qwen3:8b at 4096 with an infinite keep_alive "
                    "while this project asked for 12288, and the read pass was running at an "
                    "ETA of 1.7 years.",
                    "high", "machine"))
    except Exception:
        silence.note("standards.py:ollama-runner-standard")
        _dropped.append("ollama-runner-standard")

    # The runner check's inverse, found the same day it landed: runner ALIVE, model fully
    # GPU-resident, tags answering -- and a trivial generate timed out for two hours while
    # everything above read green. Only a completed generation proves a model server.
    try:
        flow, secs = ollama_token_flow()
        if flow is not None:
            out.append(_s(
                "the local model produces tokens", flow,
                # THE PROBE NAMES ITS OWN FAILURE. This slot used to assert "daemon up,
                # generation TIMED OUT -- queue is wedged" whatever had actually gone wrong,
                # so a refused connection or an HTTP error published a wedge diagnosis and the
                # remedy below sent the reader to restart a daemon that was not running.
                # `_flow_failure` distinguishes them; this prints what it found.
                ("probe completed in %ss" % secs) if flow
                else str(secs or "the generation probe did not complete"),
                "one tiny generation completes",
                "Process presence and API reachability are proxies; on 2026-08-24 both read "
                "healthy through a two-hour wedge in which zero tokens flowed. Read the detail "
                "before acting: a WEDGE is cured by restarting ollama.exe (the tray app "
                "respawns it) and nothing drains that queue on its own, but a daemon that is "
                "DOWN or answering an HTTP error needs starting or reading, not restarting.",
                "high", "machine"))
    except Exception:
        silence.note("standards.py:token-flow-standard")
        _dropped.append("token-flow-standard")

    try:
        import overnight as ON
        # (Removed 2026-08-24 with owner sign-off, BUGS m20: a `for job in (...)` loop whose body
        # was a bare `pass`, building a `dupes` list nothing read. The decision it recorded is
        # kept here because it is still true -- `running()` is a boolean, so COUNTING instances
        # is the reconcile tier's job, not this check's; this one asks only whether the
        # supervisor's own exclusion held. The real duplicate count lives in the
        # "one instance of each job" check below, which has its own `dupes`.)
        # `include_self=True` IS LOAD-BEARING AND MUST NOT BE DROPPED. This check runs inside
        # whichever process is rendering the panel -- `publish.py` for the public page,
        # `dashboard.py` for the local one -- and `running()`'s default excludes the caller's own
        # pid. Without this argument each renderer reported ITSELF down: on 2026-08-25 the public
        # panel read `publish.py,read.py` and the local panel read `dashboard.py,read.py` at the
        # same instant, while `allsweep.py` saw both up. The standard has no remedy, so the false
        # name went to the owner's file every round and hid the one job that was genuinely down.
        alive = {j: ON.running(j, include_self=True)
                 for j in ("dashboard.py", "publish.py", "foreman.py",
                           "overwatch.py", "read.py")}
        down = [j for j, v in alive.items() if not v]
        out.append(_s(
            "every managed job is running", not down, ",".join(down) or "all up", "all up",
            "The supervisor starts these every cycle, so one that is down means it failed on "
            "startup rather than never being launched -- read its log in state/. If the "
            "SUPERVISOR is down, the watchdog in autostart.py restarts it within three minutes.",
            "medium", "machine"))
    except Exception:
        silence.note("standards.py:jobs-alive")
        _dropped.append("jobs-alive")

    # ONE INSTANCE EACH. Three concurrent jobs once put the reader at two entities in twelve
    # minutes with nothing individually broken, which is why `overnight.start` checks by process
    # basename before launching. A second instance is not twice the work -- it is two processes
    # racing on the same caches and dividing the same provider quota.
    try:
        import subprocess as _sp
        # NOT `out` -- that is the results list this whole function is building, and assigning
        # the subprocess output to it silently replaced thirty standards with a string. The
        # traceback said `'str' object has no attribute 'append'` three lines later, which is a
        # long way from the cause.
        procs = _sp.run(["powershell", "-NoProfile", "-Command",
                         "Get-CimInstance Win32_Process -Filter \"Name like '%python%'\" | "
                         "ForEach-Object { $_.CommandLine }"],
                        capture_output=True, text=True, timeout=60,
                        encoding="utf-8", errors="replace",
                        creationflags=getattr(_sp, "CREATE_NO_WINDOW", 0)).stdout or ""
        lines = [x for x in procs.splitlines() if x.strip()]
        dupes = []
        for job in ("read.py --run", "feats.py --roll", "overnight.py", "foreman.py",
                    "overwatch.py", "dashboard.py", "publish.py"):
            n = sum(1 for x in lines if job in x)
            if n > 1:
                dupes.append(f"{job.split()[0]} x{n}")
        _dup = _s("one instance of each job", not dupes,
                  ", ".join(dupes) or "one each", "one each",
                  "Two copies of the same job race on one cache and split one quota. The "
                  "supervisor excludes by process basename before launching, so a duplicate "
                  "means one was started outside it -- find and stop the older.",
                  "high", "machine")
    except Exception:
        silence.note("standards.py:duplicates")
        _dup = None
    if _dup:
        out.append(_dup)

    try:
        pub = os.path.join(HERE, "state", "publish.log")
        age = (time.time() - os.path.getmtime(pub)) / 3600 if os.path.exists(pub) else 99
        out.append(_s(
            "the published panel is fresh", age <= MAX_PUBLISH_AGE_H, f"{age:.1f}h",
            f"{MAX_PUBLISH_AGE_H}h",
            "The public dashboard is a snapshot pushed on a timer. Stale, it shows numbers that "
            "were true once and says so only in a timestamp nobody reads.",
            "low", "machine"))
    except Exception:
        silence.note("standards.py:publish-age")
        _dropped.append("publish-age")

    # ------------------------------------------------------------------ the provider config
    try:
        with open(os.path.join(HERE, "data", "PROVIDER_MODELS.json"), encoding="utf-8") as f:
            pm = json.load(f)
        # A HIGH STANDARD HELD RED BY AN OWNER DECISION IT CANNOT SEE. Split run #28.
        #
        # All 8 rows in `stale` this run were `ollama` -- local models named in Cascade's config
        # that are not pulled on this machine. That is not a provider retiring a model id; it is
        # the owner's GPU-only residency ruling of 2026-08-24, which made `qwen3:8b` the single
        # standing local model. The rows are the ruling working, and this standard was counting
        # them as HIGH-severity faults, so it could never go green while the ruling stands.
        #
        # That is worse than a wrong number. A HIGH standard that is red by construction trains
        # the reader to skip it, and the next genuine stale CLOUD id -- the failure this was
        # written for, where "the KEY works, the string does not, and the whole provider reads
        # as dead" -- arrives on a line everyone has learned to ignore. Batch 10 adds the other
        # half: the standard's only automated remedy, `foreman.recatalogue_models()`, re-probes
        # the same external config forever, so nothing in this repo could ever close it either.
        #
        # NOTHING IS HIDDEN AND NOTHING IS CAPPED. Both lists are reported in full, every name
        # spelled out; only the GATE changes, and the local rows are labelled with the ruling
        # that explains them. If the owner reverses that ruling, this reverts in one line.
        _stale_rows = pm.get("stale") or []
        _local = [r for r in _stale_rows if (r.get("provider") or "") == "ollama"]
        _cloud = [r for r in _stale_rows if (r.get("provider") or "") != "ollama"]
        stale = len(_cloud)
        # The count is meaningless without what it was counted over: see
        # `provider_pool_denominator` for what was wrong and why `stale` must not absorb
        # the providers nobody could ask. Both numbers are reported, nothing is capped.
        _n_prov, _n_ver, _n_unver, _unver_names, _over = provider_pool_denominator(pm)
        _denom = "%d stale, %s" % (stale, _over)
        # AGE THE EVIDENCE BEFORE BELIEVING THE ALL-CLEAR.
        #
        # Found 2026-08-25 (run #23). This standard is HIGH severity and it read GREEN off a
        # snapshot that was FIFTY-EIGHT HOURS OLD -- `data/PROVIDER_MODELS.json` stamped
        # `2026-08-22 17:42`, `stale: []` -- while `state/read_auto.log` showed the live pool
        # removing five model IDs with HTTP 404 (no such model) on EVERY reader start
        # (`local-qwen3-30b`, `local-qwen3-30b-q3`, `local-llama31`, `local-gemma3-12b`,
        # `local-qwen25-14b`) and two providers 402-ing on depleted credit.
        #
        # The project already knows to age `data/COVERAGE.json` before believing a coverage
        # STALL. This is the same lesson from the other side and it is the more dangerous
        # side: a stale file that produces a FALSE ALARM gets investigated and dismissed,
        # while a stale file that produces a FALSE ALL-CLEAR is never looked at again. An
        # empty `stale` list from three days ago is not a measurement of now -- it is the
        # absence of one, and the two were rendering identically on the page.
        #
        # Deliberately NOT re-measuring here: `catalogue_models.py` owns that probe and it
        # costs a request per provider. A standard's job is to say whether the floor holds
        # and, when it cannot tell, to SAY SO rather than pass. `MAX_PROVIDER_MODELS_AGE_H`
        # is generous because a provider's catalogue changes over days, not minutes.
        age_h = (time.time() - os.path.getmtime(
            os.path.join(HERE, "data", "PROVIDER_MODELS.json"))) / 3600.0
        fresh = age_h <= MAX_PROVIDER_MODELS_AGE_H
        out.append(_s(
            "model IDs their providers still serve",
            fresh and _n_ver > 0 and stale <= MAX_STALE_MODEL_IDS,
            ((_denom + "".join(" [%s wants %s]" % (r.get("provider"), r.get("wants"))
                               for r in _cloud))
             + (("; and %d local model(s) named in config but not resident -- %s -- which is "
                 "the owner's GPU-only residency ruling of 2026-08-24 (qwen3:8b is the standing "
                 "local model), NOT a fault, and deliberately does not gate this standard"
                 % (len(_local),
                    ", ".join(str(r.get("wants")) for r in _local))) if _local else "")
             ) if (fresh and _n_ver > 0) else
            ("UNMEASURED -- the provider catalogue is %.0fh old (floor %dh), so this is the "
             "ABSENCE of a measurement, not a clean one. Do not read it as green."
             % (age_h, MAX_PROVIDER_MODELS_AGE_H) if not fresh else
             # Fresh file, empty measurement. `stale: []` over ZERO verified providers is the
             # purest form of the bug this branch exists to name: nothing was asked, so nothing
             # came back stale, and the old line would have called that a clean pool.
             "UNMEASURED -- the snapshot is %.0fh old and fresh, but NONE of its %d provider(s) "
             "produced a model list, so `stale: []` is the absence of a measurement rather than "
             "a clean pool: %s" % (age_h, _n_prov, ", ".join(_unver_names) or "no rows at all")),
            "0 stale, and the verified-provider denominator stated beside it, "
            "catalogue under %dh old" % MAX_PROVIDER_MODELS_AGE_H,
            "The config names a model the provider has retired. The KEY works; the string does "
            "not -- and the whole provider reads as dead. Six stale names once hid five live "
            "providers. `catalogue_models.py` lists what each one actually serves today; run "
            "`python src/catalogue_models.py` to refresh the snapshot this standard reads. "
            "If the snapshot is merely OLD, that is the finding -- refresh it before drawing "
            "any conclusion about the pool, in either direction. "
            "LOCAL (`ollama`) ROWS ARE REPORTED IN FULL BUT DO NOT GATE THIS STANDARD: an "
            "unpulled local model is the owner's residency ruling, not a retired model id, and "
            "counting it here held a HIGH standard red by construction for as long as the "
            "ruling stands -- which teaches the reader to ignore the line where a real stale "
            "cloud id will one day appear. If that ruling is reversed, delete the `_local` "
            "split and this counts them again. "
            "READ THE COUNT WITH ITS DENOMINATOR OR NOT AT ALL: the observed line now states "
            "how many providers were actually verified out of how many exist, and names every "
            "provider that produced no list. An unverified provider is not a clean one -- its "
            "configured model ids are unchecked, and a `no key` or a 402 is a finding of its "
            "own, to be fixed in the Cascade config rather than counted as fresh here.",
            "high", "pool"))
    except Exception:
        silence.note("standards.py:provider-models")
        _dropped.append("provider-models")

    # ------------------------------------------------------------------ the standards themselves
    #
    # A floor that is declared and never measured is worse than no floor: it reads as a promise
    # that something is being watched. Three were found dead in this very file --
    # MAX_CORRUPT_FILES, MAX_FABRICATION and MAX_UNANSWERED were all declared, all authoritative
    # looking, and all measured nothing. This standard is the one that would have said so.
    try:
        import re as _re
        src = open(os.path.abspath(__file__), encoding="utf-8").read()
        # Names that START with MIN_/MAX_ *and* names that carry it after a prefix, like
        # CHARTER_REGRESSION_MAX_AGE_H -- a real floor this same self-check could not see until
        # 2026-08-26 because the old pattern anchored M(IN|AX)_ to the start of the name.
        declared = set(_re.findall(r"^((?:[A-Z][A-Z0-9]*_)*M(?:IN|AX)_[A-Z_]+)\s*=", src, _re.M))
        # Comment-stripped and word-bounded: MAX_UNANSWERED read as "measured" for two
        # independent bad reasons -- it was quoted inside a comment, and it was a prefix of
        # the genuinely-used MAX_UNANSWERED_RECORDS. Found by the 2026-08-23 audit; either
        # alone defeated a plain substring test.
        #
        # Search the WHOLE file, not just from `def check(` onward. That cut assumed every
        # floor's only real use was inside check() itself -- true until CHARTER_REGRESSION_MAX_AGE_H,
        # which is used inside `charter_regression_verdict()`, PULLED OUT ABOVE check() on
        # 2026-08-25 for its own testability; check() calls that function by name and never
        # repeats the constant, so the old `def check(`-anchored body could never find it even
        # once the name above was fixed. A constant is credited as measured only on a SECOND
        # appearance -- the first is always its own declaration line, which every dead constant
        # has too and must not count towards its own defence.
        code_all = chr(10).join(ln.split("#")[0] for ln in src.splitlines())
        wordb = chr(92) + "b"      # regex word boundary built from codes -- the
        # escaped form of this exact line was eaten by a heredoc once already
        dead = sorted(d for d in declared
                      if len(_re.findall(wordb + _re.escape(d) + wordb, code_all)) < 2)
        out.append(_s(
            "every declared floor is measured", not dead, ", ".join(dead) or "all measured",
            "all measured",
            "A floor nothing checks is a promise that something is being watched when nothing "
            "is. Either wire it into check() or delete it -- both are honest; leaving it is not.",
            "high", "standards"))
    except Exception:
        silence.note("standards.py:self-check")
        _dropped.append("self-check")

    # THE STANDARD THAT CATCHES ITS OWN SIBLINGS VANISHING. Every `_dropped.append(...)` above
    # sits beside a `silence.note(...)` in an except block whose try held the ONLY out.append
    # for that standard -- so an exception there (missing file, bad JSON, whatever) used to
    # just delete the standard, and `report()`'s "N/N standards met" divided by the smaller N
    # and read as MORE consistent for having lost evidence. This one holds only when nothing
    # upstream dropped, so a vanished standard now costs a MISS instead of shrinking the
    # denominator it would have counted against.
    out.append(_s(
        "every standard could read its own input", not _dropped,
        (", ".join(sorted(_dropped)) if _dropped else "none"), "none",
        "One or more standards above could not be measured this run (missing, unreadable or "
        "malformed input) and would otherwise have silently vanished from the count instead "
        "of failing. Cross-reference the name(s) in `observed` against this file's own "
        "`silence.note(\"standards.py:<name>\")` calls in check() to find which input broke, "
        "then fix that input or the read.", "high", "instrument"))

    return out


def work_orders(state=None):
    """Only the breaches, worst first — the thing a person or a model is meant to act on."""
    rank = {"high": 0, "medium": 1, "low": 2}
    return sorted((v for v in check(state) if not v["holds"]),
                  key=lambda v: rank.get(v["severity"], 3))


def _wrap(text, width):
    words, line, out = text.split(), "", []
    for w in words:
        if len(line) + len(w) + 1 > width:
            out.append(line)
            line = w
        else:
            line = (line + " " + w).strip()
    if line:
        out.append(line)
    return out


def report(state=None):
    rows = check(state)
    bad = [r for r in rows if not r["holds"]]
    lines = [f"{len(rows) - len(bad)}/{len(rows)} standards met"]
    group = None
    for r in rows:
        if r["group"] != group:
            group = r["group"]
            lines.append("")
            lines.append("  " + group.upper())
        mark = "ok  " if r["holds"] else "MISS"
        lines.append(f"    {mark}  {r['standard']:<36}{str(r['observed']):>14}   "
                     f"floor {r['floor']}")
    # By RANK, not alphabetically. Sorting the severity strings gives high, low, medium -- so
    # the CLI report buried every medium work order below the lows, which is the opposite of
    # worst-first. `work_orders()` in this file already defines this exact rank dict for this
    # exact purpose, and the dashboard's panel already uses it; only this report was out of
    # step. (2026-08-24.)
    _rank = {"high": 0, "medium": 1, "low": 2}
    for r in sorted(bad, key=lambda v: _rank.get(v["severity"], 3)):
        lines.append("")
        lines.append(f"WORK ORDER [{r['severity'].upper()}] — {r['standard']}")
        lines.append(f"  observed {r['observed']}, floor {r['floor']}")
        for chunk in _wrap(r["order"], 92):
            lines.append("  " + chunk)
    return "\n".join(lines)


def main():
    import argparse
    ap = argparse.ArgumentParser(description="what working means, in numbers")
    ap.add_argument("--json", action="store_true", help="emit the verdicts as JSON")
    ap.add_argument("--orders", action="store_true", help="only the breaches")
    a = ap.parse_args()
    if a.json:
        print(json.dumps(check(), indent=1))
        return 0
    if a.orders:
        for r in work_orders():
            print(f"[{r['severity'].upper()}] {r['standard']}: {r['observed']} "
                  f"(floor {r['floor']})")
            for chunk in _wrap(r["order"], 92):
                print("   " + chunk)
        return 0
    print(report())
    return 1 if work_orders() else 0


if __name__ == "__main__":
    sys.exit(main())
