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
Three tiers, all fanned across the machine's cores because they share nothing:

  IMPORT   every module in src/ imports cleanly and its CLI parses. Catches the breakage that a
           targeted run never touches -- a module nobody has invoked since it was edited is a
           module nobody knows is broken.

  VERIFY   every read-only verifier runs for real and its verdict is captured.

  RECONCILE  the answers are cross-checked AGAINST EACH OTHER. This is the part no single
           verifier can do: coverage says an entity is CITED, the feats cache says it has no
           pages, and only a comparison notices. Each subsystem is internally consistent and
           can still disagree with its neighbour, and that disagreement is where the next
           eighteen faults live.

Nothing here writes. It is safe to run at any time, including against live jobs, and the
supervisor calls it so the answer is never more than one cycle old.
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
OUT = os.path.join(HERE, "data", "ALLSWEEP.json")

# Modules whose no-argument run does real, expensive or mutating work. They are still IMPORT
# checked; they are simply never invoked. Naming them here beats guessing from a flag.
NEVER_RUN = {
    "feats", "read", "pipeline", "overnight", "generate", "backfill", "sweep",
    "catalogue_web", "catalogue_aurora", "catalogue_codex", "repass_bands", "retry_synthesis",
    "recover_folder_records", "resync_roll", "cleanup", "compress_store", "build_terminal",
    "manifest_builder", "weave", "chain", "magnitude", "rosetta", "scope", "allsweep",
    "hostcheck", "silence", "pick_model", "navtree", "genre", "worldseed", "burgs",
}

# The verifiers, with the argv that makes each one report rather than act.
VERIFIERS = [
    ("preflight", ["health.py", "--preflight"]),
    ("swallowed failures", ["silence.py"]),
    ("citation coverage", ["coverage.py"]),
    ("the numbers", ["verify_math.py"]),
    ("thread integrity", ["thread_integrity.py"]),
    ("the instrument", ["anchors.py"]),
    ("catalogue backscan", ["audit.py"]),
    ("continuity inventory", ["identity.py"]),
    ("calibration assays", ["reference.py"]),
]


# --------------------------------------------------------------------------- tier 1: import

def modules():
    return sorted(os.path.splitext(os.path.basename(p))[0]
                  for p in glob.glob(os.path.join(SRC, "*.py")))


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
        tail = (r.stderr or "").strip().splitlines()
        err = tail[-1][:150] if tail else f"rc={r.returncode}"
        if "Traceback" not in (r.stderr or ""):
            ok, err = True, "no CLI (imported cleanly)"
    return {"module": name, "ok": ok, "detail": err, "seconds": round(time.time() - t, 1)}


# --------------------------------------------------------------------------- tier 2: verify

def run_verifier(item):
    label, argv = item
    t = time.time()
    try:
        r = subprocess.run([PY] + [os.path.join(SRC, argv[0])] + argv[1:],
                           # utf-8 explicitly: Windows decodes a child's output as cp1252 by
                           # default, and this project's output is full of the charter's own
                           # typography. A verifier whose report contains an em-dash would have
                           # crashed the auditor rather than been read.
                           capture_output=True, text=True, timeout=1800, env=ENV, cwd=HERE,
                           encoding="utf-8", errors="replace", creationflags=_NO_WIN)
        out = (r.stdout or "") + (r.stderr or "")
        crashed = "Traceback" in out
        return {"check": label, "rc": r.returncode, "crashed": crashed,
                "seconds": round(time.time() - t, 1),
                "tail": [ln for ln in out.strip().splitlines() if ln.strip()][-14:]}
    except subprocess.TimeoutExpired:
        silence.note("allsweep.py:140")
        return {"check": label, "rc": None, "crashed": False, "timeout": True,
                "seconds": round(time.time() - t, 1), "tail": ["timed out after 30 minutes"]}
    except Exception as e:
        silence.note("allsweep.py:run_verifier")
        return {"check": label, "rc": None, "crashed": True, "seconds": 0,
                "tail": [f"{type(e).__name__}: {str(e)[:120]}"]}


# --------------------------------------------------------------------------- tier 3: reconcile

def reconcile():
    """Where the subsystems DISAGREE — the only place a single verifier cannot look.

    Each of these compares two independent records of the same fact. A mismatch is not
    necessarily a bug, but it is always a thing nobody has explained, and every fault found so
    far lived in exactly that gap.
    """
    out = []

    def note(kind, detail, n=None):
        out.append({"finding": kind, "detail": detail, "count": n})

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
            note("hosts for sources with no catalogue record", ", ".join(orphan_hosts[:6]),
                 len(orphan_hosts))
        no_host = sorted(s for s in recs if not hosts.get(s))
        if no_host:
            note("catalogued sources with no host", ", ".join(no_host[:6]), len(no_host))
        if roll_src:
            missing = sorted(roll_src - set(recs))
            if missing:
                note("on the roll but never catalogued", ", ".join(missing[:6]), len(missing))
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
            note("cache directories no source points to", ", ".join(stale[:6]), len(stale))
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
                note("purged sources that still carry entries", ", ".join(ghosts), len(ghosts))
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
                    if len(examples) < 6:
                        examples.append(f"{r['source']}:{e.get('name')} "
                                        f"{e.get('magnitude')}>{order[ceil]}")
        if over:
            note("ENTRIES BANDED ABOVE THEIR OWN SOURCE'S CEILING",
                 ", ".join(examples), over)
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
            if "undefined name" in ln or "local variable" in ln and "referenced before" in ln:
                lint_bad.append(ln.strip())
    except Exception:
        silence.note("allsweep.py:lint")
        lint_bad.append("pyflakes did not run -- the lint tier is BLIND this sweep, not clean")
    print("\nLINT — every line, statically")
    if lint_bad:
        for ln in lint_bad[:20]:
            print(f"   UNDEFINED  {ln[:100]}")
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
            mark = ("CRASHED" if r["crashed"] else
                    "TIMEOUT" if r.get("timeout") else
                    "ok" if r["rc"] == 0 else "findings")
            print(f"   {mark:<9}{r['check']:<26}{r['seconds']:>7.1f}s")
        for r in verifiers:
            if r["crashed"] or r.get("timeout"):
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
                rows = [{"finding": "check failed", "detail": type(ex).__name__}]
            est[label.lower()] = rows
            for r in rows:
                print("   {:<50}{}".format(r["finding"][:50], str(r["detail"])[:58]))

    print("\nRECONCILE — where the subsystems disagree")
    findings = reconcile()
    for f in findings:
        n = f"{f['count']:,}" if isinstance(f["count"], int) else ""
        print(f"   {f['finding']:<46}{n:>9}  {f['detail'][:70]}")

    # ATOMIC. The audit reads every file in the tree including its own output, so a plain
    # truncate-then-write leaves a zero-byte ALLSWEEP.json on disk for as long as the dump takes
    # -- and the audit duly reported its own report as corrupt. Write beside, then rename.
    # `os.replace` alone raises PermissionError on Windows while any reader holds the target
    # open, which is exactly this file's situation -- the dashboard and the next ESTATE tier
    # read it. `silence.write_json` retries the rename instead of dying. 2026-08-25.
    silence.write_json(OUT, {"imports": imports, "verifiers": verifiers,
                             "lint": lint_bad,
                             "reconcile": findings, "estate": est,
                             "seconds": round(time.time() - t0, 1)}, indent=1)
    # THE LINT TIER NOW COUNTS. Run #26: this sweep ran four tiers and graded two. `lint_bad` was
    # computed, printed to the console and dropped, so a real pyflakes undefined-name anywhere in
    # `src/` left this process exiting 0 and left no trace in ALLSWEEP.json, which had no `lint`
    # key at all. Everything that gates on the integrity suite was reading a pass from a tier
    # that was never allowed to fail. That includes the line `lint_bad` appends when pyflakes
    # itself will not run: the tier announces it is BLIND, and being blind scored as clean.
    #
    # RECONCILE DELIBERATELY DOES NOT COUNT, and that is a gap rather than a decision. Its rows
    # are not all faults: `note()` carries no severity, and the same undifferentiated list holds
    # `catalogued sources with no host` (a real disagreement) beside `phases implemented 8` and
    # `running 1 dashboard.py` (plain healthy facts). Summing it made a green machine report 16
    # bad subsystems -- tried and reverted here in run #26, deliberately recorded rather than
    # quietly dropped. Giving `note()` a severity so this tier CAN gate is real work and is in
    # NEXT_STEPS; until then the count is printed below and judged by a person, and the tier is
    # honestly ungraded rather than dishonestly summed.
    bad = (len(broken)
           + sum(1 for r in verifiers if r["crashed"] or r.get("timeout"))
           + len(lint_bad)
           + len((est.get("artifacts") or {}).get("bad", [])))
    print(f"\n{bad} subsystem(s) in a bad state.  {time.time() - t0:.0f}s.  -> {OUT}")
    print(f"   graded:   imports {len(broken)}   verifiers "
          f"{sum(1 for r in verifiers if r['crashed'] or r.get('timeout'))}   "
          f"lint {len(lint_bad)}   "
          f"estate {len((est.get('artifacts') or {}).get('bad', []))}")
    print(f"   ungraded: reconcile {len(findings)} row(s) -- read them, they are not all faults")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
