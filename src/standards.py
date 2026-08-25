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

_BAD_CHARS = (chr(8), chr(11), chr(12), chr(7))
if any(c in open(os.path.abspath(__file__), encoding="utf-8").read() for c in _BAD_CHARS):
    raise SystemExit(__file__ + ": a regex escape was eaten in transit.")

# ---------------------------------------------------------------------------- the floors
#
# Each is set where a breach means something is genuinely wrong rather than merely unlucky.

MIN_CALLS_PER_HOUR = 900        # measured healthy 3,400/h; a third of that is a real fault
MIN_CALLS_TO_JUDGE_RATE = 20    # below this a success PERCENTAGE is noise, not a measurement.
                                # Mirrors tuning.MIN_CALLS_TO_JUDGE (20), which already answers
                                # this exact question for regime(). See `calls that succeed`.
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
        ok, secs = False, None
        silence.note("standards.py:token-flow")
        _ = e
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

    `_sk` exists so the regression checks can drive this with a stub instead of the network."""
    if _sk is None:
        import socket as _sk
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


def _s(name, holds, observed, floor, order, severity="medium", group="general"):
    return {"standard": name, "group": group, "holds": bool(holds), "observed": observed,
            "floor": floor, "order": order, "severity": severity}


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

    fab = None
    read = jobs.get("corpus read")
    if read:
        det = read.get("detail") or ""
        try:
            import re as _re
            kept = int((_re.search(r"([\d,]+) feats", det).group(1)).replace(",", ""))
            m = _re.search(r"dropped\s+([\d,]+)", read.get("raw") or "")
            drop = int(m.group(1).replace(",", "")) if m else None
            if drop is not None and (kept + drop):
                fab = drop / (kept + drop)
        except Exception:
            silence.note("standards.py:fabrication")
    if fab is not None:
        out.append(_s(
            "sentences that survive the verbatim check", fab <= MAX_FABRICATION,
            f"{fab:.0%} rejected", f"{MAX_FABRICATION:.0%}",
            "The model is returning text that is not in the source. A rate this high means the "
            "passage is being truncated before it arrives -- check the chunk size against the "
            "model's context -- or that a weak fallback model is carrying the run.",
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
            age_h = (time.time() - float(reg.get("at") or 0)) / 3600
            rows = [r for r in (reg.get("results") or []) if isinstance(r, dict)]
        except Exception:
            silence.note("standards.py:449")
            reg, age_h, rows = None, 1e9, []
        scored = [r for r in rows if r.get("status") == "SCORED"]
        bad = [r for r in scored if not r.get("consistent")]
        holds = bool(scored) and not bad and age_h <= 26
        if reg is None:
            obs = "never run"
        else:
            obs = "%d/%d consistent, %d unscored, %.0fh old" % (
                len(scored) - len(bad), len(scored), len(rows) - len(scored), age_h)
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

    # ------------------------------------------------------------------ is the cast all here?
    try:
        with open(os.path.join(HERE, "data", "COMPLETENESS.json"), encoding="utf-8") as f:
            comp = json.load(f)
        good = [c for c in comp if not c.get("unreliable")]
        wiki = sum(c.get("wiki_persons") or 0 for c in good)
        have = sum(c.get("catalogued_persons") or 0 for c in good)
        cov = (have / wiki) if wiki else 0.0
        worst = sorted(good, key=lambda c: c.get("coverage", 0))[:3]
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
        _worst = sorted(_unrec, key=lambda r: -int(r.get("count", 0)))[:3]
        out.append(_s(
            "every pool failure is recognised", not _unrec,
            ", ".join("%s: %s (x%d)" % (r.get("bucket"), str(r.get("error"))[:60],
                                        int(r.get("count", 0))) for r in _worst) or "none",
            "no unrecognised refusal",
            "Each row is a provider failing for a reason this code cannot name, so it is "
            "neither benched as permanent nor backed off as contention -- it just burns a "
            "claim and a deadline, repeatedly. READ THE ERROR TEXT IN THE ROW. If it is a "
            "permanent refusal (a dead key, a spent account, a retired model), add its wording "
            "to the `permanent` tuple in `cascade_bridge._ask_call` and it will be benched for "
            "four hours from then on. If it is a transport or parse fault, it is a bug and "
            "belongs in BUGS.md. Rows older than 24h disappear on their own, so anything here "
            "is happening NOW.",
            "high", "pool"))
    except Exception:
        silence.note("standards.py:unrecognised-pool")

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

    try:
        import shutil as _sh
        free = _sh.disk_usage(HERE).free / 1e9
        out.append(_s(
            "disk space", free >= MIN_DISK_GB, f"{free:.0f} GB", f"{MIN_DISK_GB} GB",
            "The roll writes hundreds of megabytes an hour. Out of disk, every stage fails at "
            "once and most of them fail quietly.", "high", "machine"))
    except Exception:
        silence.note("standards.py:disk")

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
        out.append(_s(
            "promotions have their spine codes amended", not _pending,
            (", ".join(_pending)[:120] if _pending else "none outstanding"),
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

    # ------------------------------------------------------ the local model is really serving
    try:
        import urllib.request as _ur
        resident = None
        try:
            with _ur.urlopen("http://localhost:11434/api/ps", timeout=8) as r:
                resident = [m.get("name") for m in (json.load(r).get("models") or [])]
        except Exception:
            resident = None          # a daemon that will not answer at all is another question
        if resident:
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
    except Exception:
        silence.note("standards.py:ollama-runner-standard")

    # The runner check's inverse, found the same day it landed: runner ALIVE, model fully
    # GPU-resident, tags answering -- and a trivial generate timed out for two hours while
    # everything above read green. Only a completed generation proves a model server.
    try:
        flow, secs = ollama_token_flow()
        if flow is not None:
            out.append(_s(
                "the local model produces tokens", flow,
                ("probe completed in %ss" % secs) if flow
                else "daemon up, generation TIMED OUT -- queue is wedged",
                "one tiny generation completes",
                "Process presence and API reachability are proxies; on 2026-08-24 both read "
                "healthy through a two-hour wedge in which zero tokens flowed. If this fires, "
                "restart ollama.exe (the tray app respawns it) and re-probe. Nothing drains "
                "a wedged queue on its own.",
                "high", "machine"))
    except Exception:
        silence.note("standards.py:token-flow-standard")

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

    # ------------------------------------------------------------------ the provider config
    try:
        with open(os.path.join(HERE, "data", "PROVIDER_MODELS.json"), encoding="utf-8") as f:
            pm = json.load(f)
        stale = len(pm.get("stale") or [])
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
            fresh and stale <= MAX_STALE_MODEL_IDS,
            ("%d stale" % stale) if fresh else
            ("UNMEASURED -- the provider catalogue is %.0fh old (floor %dh), so this is the "
             "ABSENCE of a measurement, not a clean one. Do not read it as green."
             % (age_h, MAX_PROVIDER_MODELS_AGE_H)),
            "0 stale, catalogue under %dh old" % MAX_PROVIDER_MODELS_AGE_H,
            "The config names a model the provider has retired. The KEY works; the string does "
            "not -- and the whole provider reads as dead. Six stale names once hid five live "
            "providers. `catalogue_models.py` lists what each one actually serves today; run "
            "`python src/catalogue_models.py` to refresh the snapshot this standard reads. "
            "If the snapshot is merely OLD, that is the finding -- refresh it before drawing "
            "any conclusion about the pool, in either direction.",
            "high", "pool"))
    except Exception:
        silence.note("standards.py:provider-models")

    # ------------------------------------------------------------------ the standards themselves
    #
    # A floor that is declared and never measured is worse than no floor: it reads as a promise
    # that something is being watched. Three were found dead in this very file --
    # MAX_CORRUPT_FILES, MAX_FABRICATION and MAX_UNANSWERED were all declared, all authoritative
    # looking, and all measured nothing. This standard is the one that would have said so.
    try:
        import re as _re
        src = open(os.path.abspath(__file__), encoding="utf-8").read()
        declared = set(_re.findall(r"^(M(?:IN|AX)_[A-Z_]+)\s*=", src, _re.M))
        body = src[src.index("def check("):]
        # Comment-stripped and word-bounded: MAX_UNANSWERED read as "measured" for two
        # independent bad reasons -- it was quoted inside a comment, and it was a prefix of
        # the genuinely-used MAX_UNANSWERED_RECORDS. Found by the 2026-08-23 audit; either
        # alone defeated a plain substring test.
        body_code = chr(10).join(ln.split("#")[0] for ln in body.splitlines())
        wordb = chr(92) + "b"      # regex word boundary built from codes -- the
        # escaped form of this exact line was eaten by a heredoc once already
        dead = sorted(d for d in declared
                      if not _re.search(wordb + _re.escape(d) + wordb, body_code))
        out.append(_s(
            "every declared floor is measured", not dead, ", ".join(dead) or "all measured",
            "all measured",
            "A floor nothing checks is a promise that something is being watched when nothing "
            "is. Either wire it into check() or delete it -- both are honest; leaving it is not.",
            "high", "standards"))
    except Exception:
        silence.note("standards.py:self-check")

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
