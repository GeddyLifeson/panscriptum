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
MIN_LIVE_BUCKETS = 6            # below this the pool cannot absorb even modest concurrency
MAX_DRY_FRACTION = 0.60         # more than this exhausted means the day's allowance is spent
MAX_PINNED_AT_ONE = 0           # a bucket reading rpm 0/1 is a mis-learned cap, never a real one
MAX_ETA_HOURS = 24              # the corpus read is meant to be an overnight job
MAX_UNANSWERED = 0              # a passage nobody read must never be counted as read
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
    per_hour = tp.get("per_hour", 0)
    out.append(_s(
        "model calls per hour", per_hour >= MIN_CALLS_PER_HOUR, per_hour, MIN_CALLS_PER_HOUR,
        "Work the four standards below in order -- they split this one number into its causes. "
        "If all four hold and throughput is still low, the reader is not asking: check that "
        "read.py resolved its transport to Cascade and that its worker count matches the "
        "bucket count.", "high", "pool"))

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

    errs = sum(b["calls"] - b["ok"] for b in tp.get("buckets", []))
    tot = max(sum(b["calls"] for b in tp.get("buckets", [])), 1)
    out.append(_s(
        "calls that succeed", (errs / tot) <= 0.5, f"{1 - errs / tot:.0%} ok", "50%",
        "Half the calls are failing. Look at which buckets: a 413 means the prompt exceeds that "
        "provider's token cap, a 401 means a dead key, a 429 means real contention.",
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

    unans_files = 0
    try:
        import glob as _g
        for fp in _g.glob(os.path.join(HERE, "data", "readfeats", "**", "*.json"),
                          recursive=True):
            with open(fp, encoding="utf-8") as f:
                head = f.read(700)
            if '"chunks_unanswered": 0' not in head and "chunks_unanswered" in head:
                unans_files += 1
            elif "chunks_unanswered" not in head:
                unans_files += 1          # written before the guard existed
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
        out.append(_s(
            "every source is fully catalogued", cov >= MIN_CATALOGUE_COVERAGE,
            "%.1f%% (%s of %s) -- worst: %s" % (100 * cov, f"{have:,}", f"{wiki:,}", detail),
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

        now = time.time()
        stalled, watched, cur = [], 0, {}
        for fn in sorted(os.listdir(os.path.join(HERE, "state"))):
            if not fn.endswith(".log"):
                continue
            job = fn[:-4]
            path = os.path.join(HERE, "state", fn)
            try:
                size = os.path.getsize(path)
            except Exception:
                silence.note("standards.py:job-size")
                continue
            cur[job] = {"size": size, "at": now}

            # Only a job whose process is UP can stall. A finished job's log stops growing
            # because it is finished, and calling that a fault would cry wolf on every
            # completed run -- which is how a standards system gets ignored.
            alive = False
            try:
                alive = bool(_ON.running(job + ".py")) or bool(_ON.running(job))
            except Exception:
                silence.note("standards.py:job-alive")
            if not alive:
                continue
            watched += 1
            p = prev.get(job)
            if not p:
                continue
            quiet_min = (now - p.get("at", now)) / 60.0
            if p.get("size") == size and quiet_min >= MAX_JOB_SILENCE_MIN:
                stalled.append("%s (%d min, %d bytes)" % (job, round(quiet_min), size))

        tmp = JOB_WATCH + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(cur, f)
        os.replace(tmp, JOB_WATCH)

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

    # ------------------------------------------------------------------ the machine
    # ------------------------------------------------------------------ the network
    #
    # On 2026-08-23 every fandom.com host dropped this machine's connections at the socket for
    # hours -- an IP block earned by our own 100-req/s catalogue rate -- and NOTHING on the
    # board said so. The recatalogue skipped DC as "no wiki resolved", the roll's failures piled
    # into the swallowed-ledger, and the diagnosis took a person with curl. A network-shape
    # fault deserves its own light: unreachable-with-DNS-working is a block, not an outage.
    try:
        import socket as _sk
        try:
            _sk.create_connection(("community.fandom.com", 443), timeout=8).close()
            _fandom_ok = True
        except OSError:
            _fandom_ok = False
        out.append(_s(
            "fandom answers this machine", _fandom_ok,
            "reachable" if _fandom_ok else "connections dropped at the socket",
            "reachable",
            "DNS resolves but the TCP connect times out on every *.fandom.com host while "
            "Wikipedia answers normally: that is an IP block, usually earned by our own "
            "request rate. Do NOT keep retrying -- stop fandom-facing jobs (feats --roll, "
            "catalogue_web, hostcheck) and let it age out; check wiki_source.MIN_GAP stayed "
            "at its polite value. The catalogue remedy is gated on this same probe.",
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

    try:
        import overnight as ON
        dupes = []
        for job in ("read.py", "feats.py", "pipeline.py", "overnight.py"):
            # running() is a boolean; the reconcile tier counts instances. Here the question is
            # only whether the supervisor's own exclusion held.
            pass
        alive = {j: ON.running(j) for j in ("dashboard.py", "publish.py", "foreman.py",
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
                        encoding="utf-8", errors="replace").stdout or ""
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
        out.append(_s(
            "model IDs their providers still serve", stale <= MAX_STALE_MODEL_IDS, stale,
            MAX_STALE_MODEL_IDS,
            "The config names a model the provider has retired. The KEY works; the string does "
            "not -- and the whole provider reads as dead. Six stale names once hid five live "
            "providers. `catalogue_models.py` lists what each one actually serves today.",
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
        dead = sorted(d for d in declared if d not in body)
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
    for r in sorted(bad, key=lambda v: v["severity"]):
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
