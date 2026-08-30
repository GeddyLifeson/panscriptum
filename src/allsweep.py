#!/usr/bin/env python3
"""
ALLSWEEP — run every check this project owns, at once, and reconcile what they say.

WHY THIS EXISTS
---------------
By 2026-08-22 the tree held sixty-eight modules and nine separate verifiers: `health` for
preflight, `silence` for swallowed failures, `coverage` for citation state, `hostcheck` for
whether a wiki holds its fiction, `verify_math` for the numbers, `thread_integrity` for the
cross-links, `anchors` for the instrument, `audit` for the catalogue, `style_audit` for the
prose.

Every one of them worked. Nothing ran them together, so the project was verified the way it was
debugged: whichever symptom happened to surface. Eighteen faults were found that day, and the
common thread was not that they were hard to detect -- most were a single measurement away --
it was that nobody was measuring until something already looked wrong.

A defect nobody looked for is indistinguishable from a defect that is not there. That is the same
sentence as the one at the top of `silence.py`, arriving one level up.

WHAT IT DOES
------------
Five tiers now, not the three this paragraph used to list -- LINT was added in run #26 to catch
the fault class IMPORT cannot (see the tier's own comment below) and this description was never
revisited, so it undersold what `foreman._checks_pass` was already written against. All of it is
fanned across the machine's cores because the tiers share nothing:

  IMPORT     every module in src/ imports cleanly and its CLI parses. Catches the breakage that
             a targeted run never touches -- a module nobody has invoked since it was edited is
             a module nobody knows is broken.

  LINT       every line of every module, statically, via pyflakes. IMPORT proves a module
             LOADS; it does not prove a function inside it RUNS -- an undefined name reachable
             only from a branch nothing here calls passed IMPORT clean and then failed for real
             the day something finally called it. Gates the exit status alongside VERIFY.

  VERIFY     every read-only verifier runs for real and its verdict is captured.

  ESTATE     every file this project owns, opened -- catalogue, charter, terminal, external --
             so a corrupt or unreadable file is a finding rather than a silent skip the next
             time something tries to read it.

  RECONCILE  the answers are cross-checked AGAINST EACH OTHER. This is the part no single
             verifier can do: coverage says an entity is CITED, the feats cache says it has no
             pages, and only a comparison notices. Each subsystem is internally consistent and
             can still disagree with its neighbour, and that disagreement is where the next
             eighteen faults live.

READ-ONLY AGAINST THE LIBRARY, but not writeless: the combined verdict is landed at
`data/ALLSWEEP.json` (via `silence.write_json`) so the dashboard and the next run's ESTATE tier
have something to read without re-running the whole sweep. It changes nothing in `data/records`
or the corpus itself, which is the property "safe to run at any time, including against live
jobs" actually depends on -- and the supervisor calls it every cycle so the answer is never more
than one cycle old.
"""
import argparse
import glob
import json
import os
import subprocess
import silence
# Windows: a child process spawned from a windowless (pythonw) parent ALLOCATES ITS OWN
# CONSOLE unless told not to. Under the old console launcher every subprocess inherited a
# hidden console and nobody noticed; under pythonw each powershell/wmic/python child
# flashed a black window -- dozens per cycle across the stack. Passed on every spawn.
_NO_WIN = getattr(subprocess, "CREATE_NO_WINDOW", 0)

import sys
import time

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(HERE, "src")
sys.path.insert(0, SRC)

_BAD_CHARS = (chr(8), chr(11), chr(12), chr(7))
if any(c in open(os.path.abspath(__file__), encoding="utf-8").read() for c in _BAD_CHARS):
    raise SystemExit(__file__ + ": a regex escape was eaten in transit.")

PY = sys.executable
ENV = dict(os.environ, PYTHONIOENCODING="utf-8")

# The sentence `escalation.assert_clear` raises with when the plant-wide halt is standing. A
# child that prints this REFUSED; it did not break. Taken from the live message rather than
# guessed, and pinned by verify_math so the two cannot drift into disagreement silently.
_HALT_REFUSAL = "THE LIBRARY IS HALTED"
OUT = os.path.join(HERE, "data", "ALLSWEEP.json")

# Modules whose no-argument run does real, expensive or mutating work. They are still IMPORT
# checked; they are simply never invoked -- but the safety here is structural (check_import only
# ever passes `--help`, and run_verifier only ever invokes the explicit VERIFIERS list below), not
# this set. NOTHING READS NEVER_RUN; it is a roster for a human to check against, not a gate.
# Naming them here beats guessing from a flag.
NEVER_RUN = {
    "feats", "read", "pipeline", "overnight", "generate", "backfill", "sweep",
    "catalogue_web", "catalogue_aurora", "catalogue_codex", "repass_bands", "retry_synthesis",
    "recover_folder_records", "resync_roll", "cleanup", "compress_store", "build_terminal",
    "manifest_builder", "weave", "chain", "magnitude", "rosetta", "scope", "allsweep",
    "hostcheck", "silence", "pick_model", "navtree", "genre", "worldseed", "burgs",
}

# WHAT A NONZERO EXIT MEANS, PER ROW. Until run #37 the VERIFY tier read `rc` for the console
# and for the report and then graded on `crashed or timeout` alone, so a verifier's own verdict
# reached neither this sweep's exit code nor the work order queue -- the same "computed, printed
# and dropped" hole this file already documents for LINT and for ESTATE, in the one tier whose
# entire product IS a verdict. Order 14bd09740627.
#
# A blanket `rc != 0` would have been the wrong repair, and that is why the semantics live here
# rather than in the sum: `silence.py` and `audit.py` exit 1 BY CONTRACT when they have findings,
# so a shell can gate on them, and both are rc=1 and healthy on an ordinary day. Grading those as
# broken would make the battery an alarm that always sounds, which this project has already had
# to walk back once. So each row says which kind of tool it is, and the sum reads the row.
RC_BROKEN = "broken"      # a nonzero exit is a FAULT: it fails the sweep and files a work order
RC_FINDINGS = "findings"  # a nonzero exit is this tool's documented "I have findings" signal


class Verifier:
    """One row of the VERIFY tier: what to run, and what a nonzero exit MEANS.

    IT ITERATES AS EXACTLY `(label, argv)`, deliberately, and that is not tidiness. A plain
    three-tuple was the obvious shape, and it would have broken `verify_math.py:6241` --
    `any(argv == ["rosetta.py", "--check"] for _label, argv in allsweep.VERIFIERS)`, a check
    written in run #26 to prove this very row exists. A net that has to be edited before a
    correctness fix can be applied is a net standing in the way of the thing it was written to
    protect (the same lesson order 8ee268ce32cc taught `drill.py:_quarantine_...`). So the
    semantics ride on an ATTRIBUTE, the old two-element unpack still answers, and there is still
    only ONE table -- a parallel `{label: rc_means}` dict would be two hand-kept copies of one
    mapping, which is how they come to disagree.
    """
    __slots__ = ("label", "argv", "rc_means")

    def __init__(self, label, argv, rc_means=RC_BROKEN):
        self.label, self.argv, self.rc_means = label, argv, rc_means

    def __iter__(self):
        return iter((self.label, self.argv))

    def __len__(self):
        return 2

    def __getitem__(self, i):
        return (self.label, self.argv)[i]

    def __repr__(self):
        return "Verifier(%r, %r, %r)" % (self.label, self.argv, self.rc_means)


# The verifiers, with the argv that makes each one report rather than act, and what its rc means.
VERIFIERS = [
    # `health.py --preflight` is `return 1 if n else 0` over the preflight problem count. Graded
    # BROKEN even though `workorders.battery_faults` also raises PREFLIGHT_PROBLEM off
    # state/preflight_last.json: the two can disagree (this runs the checks live, that reads the
    # last artifact and can be stale), and a fault named twice is a cost this project has
    # repeatedly decided it will pay rather than let one go unnamed.
    Verifier("preflight", ["health.py", "--preflight"], RC_BROKEN),
    # rc=1 means "there are swallowed failures to read", which is silence.py's whole product.
    Verifier("swallowed failures", ["silence.py"], RC_FINDINGS),
    # coverage.py returns 1 only when the atomic write of data/COVERAGE.json was DENIED -- not
    # when coverage is low. That is a broken subsystem, not a finding.
    Verifier("citation coverage", ["coverage.py"], RC_BROKEN),
    Verifier("the numbers", ["verify_math.py"], RC_BROKEN),
    # thread_integrity.py's main() returns None and is called bare, so it can only exit nonzero
    # by dying. Declared BROKEN because that is what a nonzero would then mean.
    Verifier("thread integrity", ["thread_integrity.py"], RC_BROKEN),
    # anchors.py: `sys.exit(0 if _ok else 1)` -- 1 is the assay disagreeing with the declared
    # ladder, which is the exact fault the file exists to shout about.
    Verifier("the instrument", ["anchors.py"], RC_BROKEN),
    # audit.py is the other by-contract findings tool: `return 1 if fails else 0`.
    Verifier("catalogue backscan", ["audit.py"], RC_FINDINGS),
    # identity.py returns 0 on every path it can reach.
    Verifier("continuity inventory", ["identity.py"], RC_BROKEN),
    # reference.py: `return 0 if (landed and calibrated) else 1`. This comment used to read
    # "again a denied write, not a finding", and it was an accurate description of a hole --
    # the rc answered only whether REFERENCE_ASSAYS.json got written, so the calibration this
    # row is here to watch could drift by any margin and still exit 0 (order d049dbbfed6e,
    # reproduced at delta 5.44). It now carries the calibration too.
    #
    # STILL ONE ROW, ON PURPOSE. The two faults it can now report -- WRITE DENIED and
    # CALIBRATION OUTSIDE -- are both BROKEN-class: a benchmark that no longer reproduces the
    # charter's published interval is not this tool's documented "I have findings" signal the
    # way silence.py's and audit.py's rc=1 are, it is the ruler being wrong. They are told apart
    # by the printed line, which names which reconstruction drifted and by how much; splitting
    # them into two VERIFIERS entries would run the file twice to learn the same rc.
    Verifier("calibration assays", ["reference.py"], RC_BROKEN),
    # Spearman rank-agreement between each franchise's OWN published scale (bounties, power
    # levels, curse grades...) and our Assay -- the module's stated purpose, and until now it
    # had no automated caller anywhere: only a hand-typed `rosetta.py --check`, which nobody
    # was typing, and `main()` returned 0 whatever the rhos said. `--check` now exits 1 on a
    # real disagreement (rho < 0.3), so this row can actually fail. 2026-08-26, batch 3.
    # AND IT NOW REACHES THE GRADE, which is the other half of that change: rosetta.py:426-436
    # says the exit code "has to carry the verdict ... so nothing that gates on rc (a shell,
    # allsweep's VERIFIERS, a scheduler) could ever learn a franchise's own published ordering
    # disagreed with our Assay" -- and for eleven runs neither consumer read it.
    Verifier("franchise rank agreement", ["rosetta.py", "--check"], RC_BROKEN),
    # MOVED HERE FROM THE IMPORT TIER, where it was never meant to be (order 2d6c9343cd32).
    # cascade_bridge.py had no argparse, so `check_import`'s `--help` fell through to its
    # `selftest()` and made a real model call -- the IMPORT tier, whose question is "does this
    # load", was answering it with the weather at thirty providers, and filed a MAJOR order
    # against a module that imports cleanly. `--help` is now honoured there; the live call keeps
    # running, once per sweep exactly as before, but in the tier that grades verdicts. BROKEN
    # rather than FINDINGS deliberately: it is what it was worth before this move, and quietly
    # softening a check while relocating it is how a safety gets removed by accident.
    Verifier("cascade live call", ["cascade_bridge.py", "--selftest"], RC_BROKEN),
]


# --------------------------------------------------------------------------- tier 1: import

def modules():
    """Every module under src/, SUBDIRECTORIES INCLUDED. -> paths relative to src/, no `.py`.

    `glob(SRC + "/*.py")` does not descend, and `src/deprecated/` holds `catalogue_local.py`, so
    that file was never import-checked and never linted here -- the same non-recursive glob
    `sweep_plan.modules()` had (order f42c55355431). Both consumers below join `SRC` with the
    name plus `.py`, and a relative path with a separator works for that unchanged; for every
    top-level module the name is exactly what it always was.

    `__pycache__` is skipped because it holds no source.
    """
    out = []
    for root, dirs, files in os.walk(SRC):
        dirs[:] = [d for d in dirs if d != "__pycache__"]
        for f in files:
            if f.endswith(".py"):
                rel = os.path.relpath(os.path.join(root, f), SRC).replace(os.sep, "/")
                out.append(rel[:-3])
    return sorted(out)


def check_import(name):
    """Does it import, and does its CLI parse?

    `--help` is the cheapest total exercise of a module: it runs every import, every module-level
    constant, every regex compile, every load-time guard, and then builds the argument parser --
    without doing any work. A module that cannot answer --help cannot be run at all, and until
    something invoked it nobody would know.
    """
    t = time.time()
    r = subprocess.run([PY, os.path.join(SRC, name + ".py"), "--help"],
                       capture_output=True, text=True, timeout=120, env=ENV, cwd=HERE,
                       encoding="utf-8", errors="replace", creationflags=_NO_WIN)
    ok = r.returncode == 0
    err = ""
    if not ok:
        # A module with no argparse exits nonzero on --help, which is not a fault. A module that
        # cannot IMPORT raises, and the traceback is what separates the two.
        blob = (r.stderr or "") + (r.stdout or "")
        tail = (r.stderr or "").strip().splitlines()
        err = tail[-1][:150] if tail else f"rc={r.returncode}"
        # A SAFETY THAT STOPS WORK IS NOT A FAULT THAT STOPS WORK. Owner ruling 2026-08-25,
        # after the halt made every job exit on purpose and the SUPERVISOR read that as every
        # job crashing, declared the library broken and quit. That was fixed in `overnight.py`
        # (M26) and the identical construction here was never visited -- so with a halt standing
        # this tier reported "8 subsystem(s) in a bad state" while those eight subsystems were
        # doing exactly what they are built to do. Found run #31, by running the battery under a
        # live halt. Deliberate refusal is its own verdict, and it is not red.
        if _HALT_REFUSAL in blob:
            ok, err = True, "refused: the library is halted (obeying the interlock)"
        elif "Traceback" not in blob:
            # AND THE SAME TEST IN THE OTHER DIRECTION. Absence of a traceback used to mean
            # "imported cleanly" outright, so anything dying via `raise SystemExit(msg)` --
            # which prints no traceback -- was graded green. That is not hypothetical: every
            # module in this tree carries a `_BAD_CHARS` guard that raises exactly that way when
            # a regex escape is eaten in transit, and run #31's new fail-closed interlocks do
            # too. The IMPORT tier was blind to its own corruption detector. A bare nonzero exit
            # with nothing to say is still "no CLI"; one that PRINTED a refusal is a finding.
            said = blob.strip()
            if said:
                ok, err = False, "exited without a traceback, saying: " + said.splitlines()[-1][:150]
            else:
                ok, err = True, "no CLI (imported cleanly)"
    return {"module": name, "ok": ok, "detail": err, "seconds": round(time.time() - t, 1)}


# --------------------------------------------------------------------------- tier 2: verify

def run_verifier(item):
    """Run one verifier and PUBLISH ITS GRADE, not just its exit code.

    `failed` is the single severity judgement for this row, made here and landed in
    ALLSWEEP.json, so `main()`'s sum and `workorders.battery_faults` both READ it instead of
    each re-deriving which rc counts. That is the same shape `estate_faults` was given in run
    #36 for exactly the same reason: two hand-mirrored grading rules is how the sweep and the
    queue came to disagree about `MASTER CHARTER MISSING`.

    `rc_means` rides along so a person reading the report can see WHY a row was graded the way
    it was without opening this file. A row with no declared semantics is treated as BROKEN --
    fail closed: an ungraded verifier must not be a free pass.
    """
    label, argv = item[0], item[1]
    # `getattr` first so a `Verifier` answers, then the third slot so a bare tuple still can,
    # then RC_BROKEN so an undeclared row fails closed rather than becoming a free pass.
    rc_means = getattr(item, "rc_means", None)
    if rc_means is None:
        rc_means = item[2] if len(item) > 2 else RC_BROKEN
    t = time.time()
    try:
        r = subprocess.run([PY, os.path.join(SRC, argv[0]), *argv[1:]],
                           # utf-8 explicitly: Windows decodes a child's output as cp1252 by
                           # default, and this project's output is full of the charter's own
                           # typography. A verifier whose report contains an em-dash would have
                           # crashed the auditor rather than been read.
                           capture_output=True, text=True, timeout=1800, env=ENV, cwd=HERE,
                           encoding="utf-8", errors="replace", creationflags=_NO_WIN)
        out = (r.stdout or "") + (r.stderr or "")
        crashed = "Traceback" in out
        # A SAFETY THAT STOPS WORK IS NOT A FAULT THAT STOPS WORK, the same ruling the IMPORT
        # tier already honours: with the plant-wide halt standing every verifier refuses and
        # exits nonzero, and grading that as ten broken subsystems is the run-#31 mistake in a
        # new tier. A child that printed the halt refusal obeyed the interlock.
        refused = _HALT_REFUSAL in out
        failed = bool(crashed or (r.returncode != 0 and rc_means == RC_BROKEN and not refused))
        return {"check": label, "rc": r.returncode, "crashed": crashed,
                "rc_means": rc_means, "refused": refused, "failed": failed,
                "seconds": round(time.time() - t, 1),
                "tail": [ln for ln in out.strip().splitlines() if ln.strip()][-14:]}
    except subprocess.TimeoutExpired:
        silence.note("allsweep.py:run_verifier-timeout")
        return {"check": label, "rc": None, "crashed": False, "timeout": True,
                "rc_means": rc_means, "refused": False, "failed": True,
                "seconds": round(time.time() - t, 1), "tail": ["timed out after 30 minutes"]}
    except Exception as e:
        silence.note("allsweep.py:run_verifier")
        return {"check": label, "rc": None, "crashed": True, "seconds": 0,
                "rc_means": rc_means, "refused": False, "failed": True,
                "tail": [f"{type(e).__name__}: {str(e)[:120]}"]}


# --------------------------------------------------------------------------- tier 3: reconcile

def reconcile():
    """Where the subsystems DISAGREE — the only place a single verifier cannot look.

    Each of these compares two independent records of the same fact. A mismatch is not
    necessarily a bug, but it is always a thing nobody has explained, and every fault found so
    far lived in exactly that gap.
    """
    out = []

    def note(kind, detail, n=None, names=None):
        # `names` CARRIES THE FULL SET, `detail` is only a head (order d2c3e5542551).
        # Every list-valued row here used to join `whatever[:6]` into `detail` and store THAT,
        # so unlike every other capped list in this file the full set existed nowhere -- not on
        # the console, not in ALLSWEEP.json. Measured when the order was filed: "catalogued
        # sources with no host" had count=8 and named 7, so one source was named nowhere at all;
        # the band-ceiling row is the one that would really hurt, since a run with 400
        # over-banded entries reported six examples and the other 394 were unrecoverable from
        # the artifact. Compare art['bad'][:25] at the ARTIFACTS tier, which prints "... and N
        # more" AND genuinely keeps the whole list in the JSON -- that is the shape being
        # matched. Rows that have no list (a plain fact, or a caught exception) pass names=None.
        out.append({"finding": kind, "detail": detail, "count": n, "names": names})

    def _head(names, k=6):
        """A console-length head of `names` that says out loud what it is not showing.

        The cap exists so the RECONCILE table stays one line per finding. It is honest about
        itself here, and it is not the record: the caller hands the same list to note(names=...)
        and ALLSWEEP.json keeps every element.
        """
        names = list(names)
        shown = ", ".join(str(x) for x in names[:k])
        return shown if len(names) <= k else "%s, and %s more" % (shown, format(len(names) - k, ","))

    # --- the roll, the records, and the host map should describe the same set of sources ----
    try:
        import feats as F
        import weave_index as WI
        hosts = json.load(open(F.HOSTS, encoding="utf-8"))
        recs = {r["source"]: r for r in WI.load_records()}
        roll = json.load(open(os.path.join(HERE, "data", "SWEEP_ROLL.json"), encoding="utf-8"))
        roll_src = {r.get("source") or r.get("name") for r in
                    (roll if isinstance(roll, list) else roll.get("sources", []))}
        roll_src.discard(None)

        orphan_hosts = sorted(set(hosts) - set(recs))
        if orphan_hosts:
            note("hosts for sources with no catalogue record", _head(orphan_hosts),
                 len(orphan_hosts), names=orphan_hosts)
        no_host = sorted(s for s in recs if not hosts.get(s))
        if no_host:
            note("catalogued sources with no host", _head(no_host), len(no_host), names=no_host)
        if roll_src:
            missing = sorted(roll_src - set(recs))
            if missing:
                note("on the roll but never catalogued", _head(missing), len(missing),
                     names=missing)
    except Exception as e:
        note("source reconciliation failed", f"{type(e).__name__}: {str(e)[:90]}")

    # --- coverage's verdict against what is actually on disk -------------------------------
    try:
        rows = json.load(open(os.path.join(HERE, "data", "COVERAGE.json"), encoding="utf-8"))
        claimed = sum(r["cited"] for r in rows)
        feats_on_disk = 0
        for fp in glob.glob(os.path.join(HERE, "data", "readfeats", "**", "*.json"),
                            recursive=True):
            try:
                if os.path.getsize(fp) > 400:
                    feats_on_disk += 1
            except OSError:
                silence.note("allsweep.py:reconcile-size")
        note("coverage says CITED", f"{claimed:,} entries", claimed)
        note("readfeats records holding text", f"{feats_on_disk:,} files", feats_on_disk)
        stamp = os.path.getmtime(os.path.join(HERE, "data", "COVERAGE.json"))
        age_h = (time.time() - stamp) / 3600
        if age_h > 2:
            note("COVERAGE.json is stale", f"{age_h:.1f} hours old -- its percentages predate "
                 f"whatever has run since")
    except Exception as e:
        note("coverage reconciliation failed", f"{type(e).__name__}: {str(e)[:90]}")

    # --- rejected hosts must not still be mining -------------------------------------------
    try:
        import re as _re
        import feats as F
        hosts = json.load(open(F.HOSTS, encoding="utf-8"))
        live = {_re.sub(r"[^A-Za-z0-9]+", "_", h)[:40] for h in hosts.values() if h}
        stale = []
        for base in ("feats", "readfeats"):
            root = os.path.join(HERE, "data", base)
            for d in (sorted(os.listdir(root)) if os.path.isdir(root) else []):
                if d not in live and glob.glob(os.path.join(root, d, "*.json")):
                    stale.append(f"{base}/{d}")
        if stale:
            note("cache directories no source points to", _head(stale), len(stale), names=stale)
    except Exception as e:
        note("cache reconciliation failed", f"{type(e).__name__}: {str(e)[:90]}")

    # --- purged rosters must be gone from the records, not merely marked -------------------
    try:
        p = os.path.join(HERE, "data", "ROSTER_PURGES.json")
        if os.path.exists(p):
            import weave_index as WI
            purged = json.load(open(p, encoding="utf-8"))
            recs = {r["source"]: r for r in WI.load_records()}
            ghosts = [s for s in purged if recs.get(s, {}).get("entries")]
            if ghosts:
                # Deliberately NOT run through _head: this row was already uncapped and adding
                # a head here would be introducing a cap, not removing one. It gains `names`
                # so consumers get a list rather than having to split the string.
                note("purged sources that still carry entries", ", ".join(ghosts), len(ghosts),
                     names=ghosts)
    except Exception as e:
        note("purge reconciliation failed", f"{type(e).__name__}: {str(e)[:90]}")

    # --- the phases the runner claims against the phases that exist ------------------------
    try:
        import pipeline as P
        phases = [p for p in getattr(P, "PHASES", [])]
        names = [p[0] if isinstance(p, (list, tuple)) else str(p) for p in phases]
        # The runner dispatches to `phase_<name>`, not to `<name>`. Looking for the bare name
        # reported synthesis and entrypass as unimplemented while they were the two phases
        # doing all the work -- a false alarm is as corrosive to an audit as a missed fault,
        # because both teach the reader to stop believing it.
        built = [n for n in names if hasattr(P, "phase_" + n)]
        missing = [n for n in names if n not in built]
        note("phases implemented", ", ".join(built), len(built))
        if missing:
            note("PHASES NAMED BY THE RUNNER WITH NO IMPLEMENTATION",
                 ", ".join(missing), len(missing))
    except Exception as e:
        note("phase reconciliation failed", f"{type(e).__name__}: {str(e)[:90]}")

    # --- no entry may out-band its own source's ceiling -------------------------------------
    #
    # The assay clamps against SCOPE.json, but phase 3's synthesis band and phase 4's entry
    # bands are two separate model passes over the same source, and nothing compared them: an
    # entry banded above the fiction it lives in is the Jace fault (M10.77 in an M2-scale
    # setting) wearing entrypass clothes. Bands are ordinal, so the comparison is one index
    # lookup per entry -- 'unassayed' rows are skipped, they claim nothing yet.
    try:
        import weave_index as WI
        order = ["M" + str(i) for i in range(11)]

        def _band(s):
            s = str(s or "").strip().split(".")[0].split(" ")[0]
            return order.index(s) if s in order else None

        over, examples = 0, []
        for r in WI.load_records():
            ceil = _band((r.get("synthesis") or {}).get("provisional_magnitude"))
            if ceil is None:
                continue
            for e in (r.get("entries") or []):
                b = _band(e.get("magnitude")) if isinstance(e, dict) else None
                if b is not None and b > ceil:
                    over += 1
                    # EVERY over-banded entry is collected, not the first six (order
                    # d2c3e5542551). `if len(examples) < 6` stopped the collection itself, so
                    # the other entries were not merely absent from the console line -- they
                    # never existed in the process, and ALLSWEEP.json got the same six. A run
                    # with 400 of these reported six and the remaining 394 were unrecoverable
                    # from the artifact, which is the worst of the five sites this order names.
                    # The console still shows a head; `names` below is the record.
                    examples.append(f"{r['source']}:{e.get('name')} "
                                    f"{e.get('magnitude')}>{order[ceil]}")
        if over:
            note("ENTRIES BANDED ABOVE THEIR OWN SOURCE'S CEILING",
                 _head(examples), over, names=examples)
    except Exception as e:
        note("band reconciliation failed", f"{type(e).__name__}: {str(e)[:90]}")

    # --- what is actually running right now ------------------------------------------------
    try:
        r = subprocess.run(["powershell", "-NoProfile", "-Command",
                            "Get-CimInstance Win32_Process -Filter \"Name like '%python%'\" | "
                            "ForEach-Object { $_.CommandLine }"],
                           capture_output=True, text=True, timeout=120,
                           encoding="utf-8", errors="replace", creationflags=_NO_WIN)
        live = [ln.strip() for ln in (r.stdout or "").splitlines() if ln.strip()]
        # The roster comes from overnight.ALL_JOBS, not from a copy kept here. The four-job
        # tuple this replaced omitted dashboard, publish, foreman, overwatch and autostart, so
        # the sweep reported "4 running" against a process table holding nine -- for four runs
        # straight. Nothing was down; the roster simply could not see them. A hand-kept subset
        # of a list that lives somewhere else is a false negative with a delay fuse, and this
        # is the reading a later run would trust to decide a job had died.
        import overnight as _ON
        for job in _ON.ALL_JOBS:
            n = sum(1 for ln in live if job in ln)
            if n > 1:
                note("MORE THAN ONE INSTANCE RUNNING", f"{job}: {n} processes", n)
            elif n:
                note("running", job, n)
            else:
                # Reported, not counted as a bad subsystem: on this machine the keeper brings a
                # standing job back within five minutes, and a job between laps is not a fault.
                note("NOT RUNNING", job, 0)
    except Exception as e:
        note("process check failed", f"{type(e).__name__}: {str(e)[:90]}")

    return out


# --------------------------------------------------------------------- grading the ESTATE tier

# The four named ESTATE tiers. `artifacts` is not here because it is graded by its own `bad`
# LIST (a row per unreadable file) and always has been; these four return REPORT ROWS.
ESTATE_TIERS = ("charter", "written", "terminal", "external")


def _row_is_fault(row):
    """Is one ESTATE report row a fault? FAIL-CLOSED on a row that will not say.

    A row that carries no `bad` key is counted as a fault ON PURPOSE. Every row `estate.py`
    produces now sets one explicitly, so a keyless row means somebody added a finding without
    deciding what it means -- and the failure mode this whole file exists against is the
    undecided thing scoring green. Defaulting the other way would restore exactly the hole this
    fixes: a new `note()` call would be born ungradeable and nothing would ever say so.
    """
    return bool(row.get("bad", True)) if isinstance(row, dict) else True


def estate_faults(est):
    """-> the list of graded FAULT rows across CHARTER/WRITTEN/TERMINAL/EXTERNAL.

    WHY THIS EXISTS. Until run #36 these four tiers were printed, written into ALLSWEEP.json,
    and summed by NOTHING: `main()` counted only `estate["artifacts"]["bad"]`, so
    `MASTER CHARTER MISSING`, `CHARTER_SPINE_CODES.json MISSING`,
    `TERMINAL HAS NO HTML ENTRY POINT` and `OLLAMA UNREACHABLE` could all be true at once and
    this sweep still printed "0 subsystem(s) in a bad state" and exited 0. Proven by execution
    before the change: `estate.charter()` driven against an empty tree returned
    `MASTER CHARTER MISSING`, and the old formula graded it 0.

    That is the ESTATE tier of the same defect run #26 fixed in the LINT tier -- a tier that
    was computed, printed, and dropped. A check that cannot fail looks exactly like a check
    that passed, and these four were the ones that could not.

    NOT EVERY ROW IS A FAULT and the severity is set at the `note()` call in `estate.py`, not
    guessed from the text here. An earlier draft of this reached for `finding.isupper()` (the
    heuristic `overwatch.py` uses on reconcile rows) and it is wrong in both directions:
    `config.yaml NAMES A MODEL OLLAMA DOES NOT HAVE` and `conc.js UNREADABLE` are faults that
    are not all-caps, and grading on the shape of a sentence is a check about typography.

    RECONCILE still does not count, and that remains recorded below as a gap rather than a
    decision -- its rows have no severity to read.
    """
    out = []
    for tier in ESTATE_TIERS:
        for row in (est.get(tier) or []):
            if _row_is_fault(row):
                out.append({"tier": tier, "finding": (row.get("finding") if isinstance(row, dict)
                                                      else str(row)),
                            "detail": (row.get("detail") if isinstance(row, dict) else "")})
    return out


# --------------------------------------------------------------------------- the report

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--workers", type=int, default=max(2, (os.cpu_count() or 4) - 2))
    ap.add_argument("--quick", action="store_true", help="imports and reconciliation only")
    a = ap.parse_args()
    from concurrent.futures import ThreadPoolExecutor

    t0 = time.time()
    print("=" * 92)
    print("ALLSWEEP — every check this project owns, at once")
    print("=" * 92)

    mods = [m for m in modules() if not m.startswith("_")]
    print(f"\nIMPORT — {len(mods)} modules, {a.workers} workers")
    with ThreadPoolExecutor(max_workers=a.workers) as ex:
        imports = list(ex.map(check_import, mods))
    broken = [r for r in imports if not r["ok"]]
    print(f"  {len(imports) - len(broken)}/{len(imports)} import and parse their CLI cleanly")
    for r in broken:
        print(f"   BROKEN  {r['module']:<26}{r['detail']}")

    # LINT — every line of every module, for the fault class importing cannot catch.
    #
    # The IMPORT tier above proves a module loads. It does NOT prove the module's functions
    # run: `wiki_source.py` used `os.path` in one function without importing `os`, imported
    # fine, passed this sweep twice, and then failed at the exact moment the re-catalogue asked
    # it to resolve DC -- with the NameError swallowed by an except and filed in silence.
    # An undefined name is detectable STATICALLY, on every line, without executing anything,
    # and pyflakes does precisely that. This tier is the sweep's answer to "examine every line
    # of every module": a machine does it, on every run, rather than a person doing it once.
    lint_bad = []
    try:
        lr = subprocess.run([sys.executable, "-m", "pyflakes"] +
                            [os.path.join(SRC, m + ".py") for m in mods],
                            capture_output=True, text=True, timeout=120,
                            encoding="utf-8", errors="replace", creationflags=_NO_WIN)
        for ln in (lr.stdout or "").splitlines():
            if "undefined name" in ln or ("local variable" in ln and "referenced before" in ln):
                lint_bad.append(ln.strip())
        # AND A PYFLAKES THAT DID NOT RUN IS NOT A CLEAN LINT (order bb03d4d92f4e).
        # `lr.returncode` was never read, so the BLIND line below was appended ONLY from the
        # `except` arm -- which covers a timeout or a failure to launch the interpreter, and
        # NOT the far likelier case of the checker simply being absent from the environment.
        # Measured: `python -m pyflakes_not_installed src/cachekey.py` returns rc=1 with EMPTY
        # stdout and the reason on stderr, raising nothing; both comprehension filters then
        # match nothing, `lint_bad` stays [], the console prints "no undefined names in any
        # module" and the tier contributes 0 to `bad`. A tier that cannot fail is worth less
        # than no tier, and this one gates the sweep's exit code.
        #
        # NOT a blanket `rc != 0`: pyflakes exits 1 as its ordinary "I found something" signal
        # (verified here -- rc=0 on a clean file, rc=1 with the findings on stdout). The
        # predicate is the one overnight.preflight (overnight.py:961) already uses against
        # health.py's identical `return 1 if n else 0` contract: a code outside {0,1}, or rc=1
        # with none of the stdout that contract requires, CONTRADICTS the contract, and that
        # contradiction is the did-not-complete signature. Note this is dormant on this box --
        # miniconda ships pyflakes -- and live the first time the sweep runs anywhere else.
        if lr.returncode not in (0, 1) or (lr.returncode == 1 and not (lr.stdout or "").strip()):
            silence.note("allsweep.py:lint-did-not-complete")
            lint_bad.append("pyflakes DID NOT COMPLETE (rc=%d, %s) -- the lint tier is BLIND "
                            "this sweep, not clean"
                            % (lr.returncode,
                               ((lr.stderr or "").strip().splitlines() or ["no stderr"])[-1][:150]))
    except Exception:
        silence.note("allsweep.py:lint")
        lint_bad.append("pyflakes did not run -- the lint tier is BLIND this sweep, not clean")
    print("\nLINT — every line, statically")
    if lint_bad:
        # UNCAPPED AND UNTRUNCATED, both halves. This printed `lint_bad[:20]` with no "and N
        # more" beside it and clipped each line to 100 characters -- so a 21st undefined name
        # did not exist as far as the console was concerned, and on this machine the absolute
        # path alone eats most of 100, which puts the identifier a person needs past the cut.
        # Hard Rule 0: a cap on a list somebody reads to act is a truncation, not a sample, and
        # the whole point of this tier is that a machine reads every line so a person does not
        # have to. There are normally none of these; when there are, all of them matter.
        for ln in lint_bad:
            print(f"   UNDEFINED  {ln}")
    else:
        print("  no undefined names in any module")

    verifiers = []
    if not a.quick:
        print(f"\nVERIFY — {len(VERIFIERS)} verifiers in parallel")
        with ThreadPoolExecutor(max_workers=a.workers) as ex:
            verifiers = list(ex.map(run_verifier, VERIFIERS))
        for r in sorted(verifiers, key=lambda x: x["check"]):
            # A NONZERO EXIT IS NOT A CRASH HERE. `silence` and `audit` exit 1 when they HAVE
            # findings -- that is their contract, so a shell can gate on them -- and printing
            # them beside genuine crashes made two working tools look broken every run.
            # FAILED is the new word, and it is the row's published grade rather than a second
            # reading of rc: a declared-BROKEN verifier that exited nonzero now says so here,
            # counts below, and reaches the queue.
            mark = ("CRASHED" if r["crashed"] else
                    "TIMEOUT" if r.get("timeout") else
                    "refused" if r.get("refused") else
                    "ok" if r["rc"] == 0 else
                    "FAILED" if r.get("failed") else "findings")
            print(f"   {mark:<9}{r['check']:<26}{r['seconds']:>7.1f}s"
                  f"   rc={r['rc']} ({r.get('rc_means', RC_BROKEN)})")
        for r in verifiers:
            if r.get("failed") or r["crashed"] or r.get("timeout"):
                print(f"\n   --- {r['check']} ---")
                for ln in r["tail"]:
                    print(f"      {ln[:150]}")

    est = {}
    if not a.quick:
        import estate as E
        print("\nESTATE — every file this project owns, opened")
        art = E.artifacts(workers=a.workers)
        est["artifacts"] = art
        print("  {:,} files inspected, {} unreadable or corrupt".format(
            art["total"], len(art["bad"])))
        for d, v in sorted(art["by_dir"].items(), key=lambda kv: -kv[1]["files"]):
            flag = "   <-- {} BAD".format(v["bad"]) if v["bad"] else ""
            print("   {:<20}{:>8,} files  {:>9,.0f} MB{}".format(
                d, v["files"], v["bytes"] / 1e6, flag))
        for r in art["bad"][:25]:
            print("      {:<60}{}".format(r["error"][:58], r["path"][:72]))
        if len(art["bad"]) > 25:
            print("      ... and {:,} more (full list in ALLSWEEP.json)".format(
                len(art["bad"]) - 25))

        for label, fn in (("CHARTER", E.charter), ("WRITTEN", E.written),
                          ("TERMINAL", E.terminal), ("EXTERNAL", E.external)):
            print("\n" + label)
            try:
                rows = fn()
            except Exception as ex:
                print("   check itself failed: {}: {}".format(
                    type(ex).__name__, str(ex)[:90]))
                # `bad: True`, because a tier that CRASHED is the loudest possible finding and
                # it used to be the quietest: this row was written into ALLSWEEP.json with no
                # severity and summed by nothing, so `estate.charter()` raising on every run
                # scored identically to `estate.charter()` returning a clean report.
                rows = [{"finding": "check failed", "detail": type(ex).__name__, "bad": True}]
            est[label.lower()] = rows
            for r in rows:
                mark = "  FAULT" if _row_is_fault(r) else ""
                print("   {:<50}{}{}".format(r["finding"][:50], str(r["detail"])[:58], mark))

    print("\nRECONCILE — where the subsystems disagree")
    findings = reconcile()
    for f in findings:
        n = f"{f['count']:,}" if isinstance(f["count"], int) else ""
        # `detail` is already a self-describing head (reconcile._head appends "and N more"), so
        # a further silent clip to 70 characters was cutting the disclosure off the end of the
        # very line that carried it. Print it whole and let the row be ragged; the table's
        # readability was never worth an undisclosed second truncation of the same string.
        print(f"   {f['finding']:<46}{n:>9}  {f['detail']}")

    # ATOMIC. The audit reads every file in the tree including its own output, so a plain
    # truncate-then-write leaves a zero-byte ALLSWEEP.json on disk for as long as the dump takes
    # -- and the audit duly reported its own report as corrupt. Write beside, then rename.
    # `os.replace` alone raises PermissionError on Windows while any reader holds the target
    # open, which is exactly this file's situation -- the dashboard and the next ESTATE tier
    # read it. `silence.write_json` retries the rename instead of dying. 2026-08-25.
    # STAMPED WITH ITS OWN CLOCK. `workorders.battery_faults` asks how old this result is, and
    # without an `at` inside the file the only answer available is the file's mtime -- which a
    # copy, a restore or a publish step rewrites, so a stale battery could present as fresh.
    # An artifact that cannot say when it was made is one a detector has to guess about. (run #33)
    # `estate_faults` IS LANDED AS ITS OWN TOP-LEVEL KEY, not left for a reader to re-derive.
    # `workorders.battery_faults` reads this file to decide what the battery says, and it reads
    # `estate.artifacts.bad` only -- so the four ESTATE tiers were invisible to the queue as
    # well as to the grade. Publishing the graded list here means the ONE severity judgement
    # (made at the `note()` call in `estate.py`) travels with the report, instead of every
    # consumer inventing its own rule about which findings are red. (run #36, batch 08)
    est_faults = estate_faults(est)
    # GATED, like scope.py's build(). `write_json` returns whether the rename LANDED and this
    # dropped the verdict, which is the quiet half of the atomicity note above: a denied replace
    # (the dashboard and `workorders.battery_faults` both read this file, and either holding it
    # open is enough on Windows) left the whole sweep printing its grade and exiting on a count
    # nobody stored. What is on disk in that case is the PREVIOUS sweep's report, and every
    # consumer treats this file as the battery's answer -- `workorders.py:158` calls a missing or
    # unreadable one "allsweep has left no result", `standards.py:1132` reads it for a standard.
    # So a red sweep whose write was denied leaves yesterday's green report standing, with a
    # fresh-looking console beside it. Counted as a fault rather than raised, because the tiers
    # above it really did run and their findings are still worth printing; the file just cannot
    # be claimed. (run #37 sweep.)
    landed = silence.write_json(OUT, {"at": time.time(),
                                      "imports": imports, "verifiers": verifiers,
                                      "lint": lint_bad,
                                      "reconcile": findings, "estate": est,
                                      "estate_faults": est_faults,
                                      "seconds": round(time.time() - t0, 1)}, indent=1)
    if not landed:
        silence.note("allsweep.py:report-write-denied")
    # THE LINT TIER NOW COUNTS. Run #26: this sweep ran four tiers and graded two. `lint_bad` was
    # computed, printed to the console and dropped, so a real pyflakes undefined-name anywhere in
    # `src/` left this process exiting 0 and left no trace in ALLSWEEP.json, which had no `lint`
    # key at all. Everything that gates on the integrity suite was reading a pass from a tier
    # that was never allowed to fail. That includes the line `lint_bad` appends when pyflakes
    # itself will not run: the tier announces it is BLIND, and being blind scored as clean.
    # That claim was true only of the EXCEPTION path until order bb03d4d92f4e -- an absent
    # pyflakes returns normally, so nothing was appended and blind scored as clean after all.
    # The rc predicate beside the parse loop above closes the other half; both arms now put a
    # BLIND line into `lint_bad`, which is what makes it count here.
    #
    # RECONCILE DELIBERATELY DOES NOT COUNT, and that is a gap rather than a decision. Its rows
    # are not all faults: `note()` carries no severity, and the same undifferentiated list holds
    # `catalogued sources with no host` (a real disagreement) beside `phases implemented 8` and
    # `running 1 dashboard.py` (plain healthy facts). Summing it made a green machine report 16
    # bad subsystems -- tried and reverted here in run #26, deliberately recorded rather than
    # quietly dropped. Giving `note()` a severity so this tier CAN gate is real work and is in
    # NEXT_STEPS; until then the count is printed below and judged by a person, and the tier is
    # honestly ungraded rather than dishonestly summed.
    #
    # AND THE ESTATE TIER'S OWN FINDINGS NOW COUNT TOO (run #36). The paragraph above was
    # written about LINT and the identical hole was sitting one line below it: `est["charter"]`,
    # `est["written"]`, `est["terminal"]` and `est["external"]` were computed, printed, landed
    # in ALLSWEEP.json -- and excluded from this sum, which read only the `artifacts` file list.
    # `MASTER CHARTER MISSING` was therefore a finding that could never fail the battery.
    # Unlike RECONCILE, these rows now carry an explicit severity set at the `note()` call
    # (`estate.py`), so the tier can gate without guessing.
    #
    # AND THE VERIFY TIER'S OWN VERDICTS NOW COUNT (run #37, order 14bd09740627). The term below
    # read `crashed or timeout` and never `rc`, so ten verifiers computed a verdict, printed it,
    # landed it in ALLSWEEP.json -- and none of it could fail this sweep or reach the queue. It
    # is the third spelling of the paragraph above: LINT was computed-printed-dropped until run
    # #26, ESTATE until run #36, VERIFY until now. The concrete case this file argues for itself
    # is `rosetta.py --check`, wired in at run #26 specifically so a franchise's own published
    # ordering disagreeing with our Assay could fail something, and read by nobody since.
    # `failed` is the row's PUBLISHED grade (see `run_verifier`), not a second rule here.
    bad = (len(broken)
           + sum(1 for r in verifiers if r.get("failed"))
           + len(lint_bad)
           + len((est.get("artifacts") or {}).get("bad", []))
           + len(est_faults)
           # A SWEEP THAT COULD NOT FILE ITS REPORT IS ITSELF A BAD SUBSYSTEM. Without this the
           # exit code answered only for the tiers, and the one thing every other consumer of
           # this sweep depends on -- the report reaching disk -- was the single condition that
           # could not fail it.
           + (0 if landed else 1))
    if not landed:
        print("\nREPORT NOT WRITTEN — the atomic replace of {} was denied after five attempts "
              "(most likely a reader holding it open). Everything above is this run's finding; "
              "the file on disk is still the PREVIOUS sweep's, so the dashboard, "
              "workorders.battery_faults and standards.py are all reading that one. Re-run."
              .format(OUT))
    if est_faults:
        print("\nESTATE FAULTS — graded, and each one fails this sweep")
        for f in est_faults:
            print("   {:<10}{:<52}{}".format(
                f["tier"].upper(), str(f["finding"])[:50], str(f["detail"])[:44]))
    print(f"\n{bad} subsystem(s) in a bad state.  {time.time() - t0:.0f}s.  -> {OUT}")
    print(f"   graded:   imports {len(broken)}   verifiers "
          f"{sum(1 for r in verifiers if r.get('failed'))}   "
          f"lint {len(lint_bad)}   "
          f"estate files {len((est.get('artifacts') or {}).get('bad', []))}"
          f"   estate findings {len(est_faults)}")
    print(f"   ungraded: reconcile {len(findings)} row(s) -- read them, they are not all faults")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
