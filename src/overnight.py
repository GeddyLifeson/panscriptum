#!/usr/bin/env python3
"""
OVERNIGHT — an unattended supervisor that runs the library's stages in the right order.

Written because running these by hand went wrong in exactly the ways an unattended run cannot
afford. At one point three jobs were live at once: a stale roll from four hours earlier, a fresh
roll, a pipeline, and a reader. They competed for the same GPU and the same wiki hosts, the
reader managed two entities in twelve minutes, and Wikipedia returned HTTP 429 across the board.
Nothing had gone wrong in any single program.

So the rules here are about ORDER and EXCLUSION, not about doing anything new:

  ONE OF EACH. A lock file per stage. A stage already running is never started again -- the
  single most expensive mistake available overnight, because duplicates do not fail, they
  degrade everything quietly and look like slowness.

  GPU IS SERIAL. `read.py` and `pipeline.py` both drive Ollama, and Ollama on this machine runs
  a 19GB model at a 56/44 CPU/GPU split. Two clients do not go twice as fast, they thrash. Only
  one GPU stage runs at a time. The roll is network-bound and may overlap with either.

  PREFLIGHT BEFORE COMMITTING HOURS. `health.py` checks the failure classes already seen -- a
  chunk that overflows the context, an API path that 404s, a control character where an escape
  should be, a cache empty in a way that means broken. Problems are logged and the run
  continues, except for control characters, which stop it: a corrupted regex silently matches
  nothing and would waste the whole night producing confident emptiness.

  MEASURE EVERY CYCLE. Coverage is snapshotted each pass and written to STATUS.md, so the
  morning question is answered by a file rather than by an archaeology session over four logs.
"""
import argparse
import datetime
import json
import os
import subprocess
_NO_WIN = getattr(subprocess, "CREATE_NO_WINDOW", 0)

import sys
import time
import silence
import lognames as LN

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(HERE, "src")
STATE = os.path.join(HERE, "state")
PY = sys.executable

_BAD_CHARS = (chr(8), chr(11), chr(12), chr(7))
if any(c in open(os.path.abspath(__file__), encoding="utf-8").read() for c in _BAD_CHARS):
    raise SystemExit(__file__ + ": a regex escape was eaten in transit.")


def log(msg):
    line = f"[{datetime.datetime.now():%Y-%m-%d %H:%M:%S}] {msg}"
    print(line, flush=True)
    os.makedirs(STATE, exist_ok=True)
    with open(os.path.join(STATE, "overnight.log"), "a", encoding="utf-8") as f:
        f.write(line + "\n")


def running(fragment):
    """Is a python process already running this script?

    Checked by live command line rather than by a lock file: a lock file survives a kill and
    would block its stage for the rest of the night.

    Self-exclusion is by PROCESS ID, compared as a field. A first version looked for its own pid
    as a substring of the command line, where it never appears -- so the supervisor matched
    itself, and any command that merely MENTIONED a stage's filename counted as that stage
    running. It would have skipped every stage it was built to run.
    """
    try:
        out = subprocess.run(
            ["powershell", "-NoProfile", "-Command",
             "Get-CimInstance Win32_Process -Filter \"Name='python.exe' or Name='pythonw.exe'\" | "
             "ForEach-Object { $_.ProcessId.ToString() + '|' + $_.CommandLine }"],
            capture_output=True, text=True, timeout=60, creationflags=_NO_WIN).stdout
    except Exception:
        silence.note("overnight.py:73")
        return False
    mine = os.getpid()
    for ln in out.splitlines():
        pid, _, cmd = ln.partition("|")
        try:
            if int(pid.strip()) == mine:
                continue
        except ValueError:
            silence.note("overnight.py:81")
            continue
        # Normalise separators so a relative and an absolute invocation compare equal.
        if fragment in cmd.replace("\\", "/").split("/")[-1] or fragment in cmd:
            return True
    return False


# Windows opens a console for every child process unless told not to. `autostart.py` already
# passes CREATE_NO_WINDOW for the supervisor itself -- but the supervisor then spawns eight jobs
# of its own without it, so the watchdog starts silently and then eight empty black windows
# appear on the owner's desktop. Every one of them shows nothing, because stdout is redirected
# into state/*.log by the lines just below.
#
# DETACHED_PROCESS is deliberately NOT set here, unlike in autostart: these children are joined
# and their return codes are read, and a detached child cannot be waited on.
NO_WINDOW = getattr(subprocess, "CREATE_NO_WINDOW", 0)


def run(name, args, logfile, timeout_h=6):
    """Run one stage to completion, refusing to start a duplicate."""
    # Matched on BASENAME. The stage is invoked with an absolute path while an already-running
    # copy may have been started with a relative one, so a substring test on the full path never
    # matches and the guard passes when it should not. That is how a second roll got launched
    # against a live one, which is precisely the failure this supervisor exists to prevent.
    if running(os.path.basename(args[0])):
        log(f"  {name}: already running, left alone")
        return "already-running"
    lf = os.path.join(STATE, logfile)
    log(f"  {name}: starting")
    t0 = time.time()
    try:
        with open(lf, "w", encoding="utf-8") as fh:
            env = dict(os.environ, PYTHONIOENCODING="utf-8")
            p = subprocess.Popen([PY, "-u"] + args, cwd=HERE, stdout=fh,
                                 stderr=subprocess.STDOUT, env=env,
                                 creationflags=NO_WINDOW)
            p.wait(timeout=timeout_h * 3600)
        el = time.time() - t0
        log(f"  {name}: finished rc={p.returncode} in {el/60:.0f}m")
        if p.returncode != 0:
            tail(lf, name)
        return "ok" if p.returncode == 0 else f"rc={p.returncode}"
    except subprocess.TimeoutExpired:
        p.kill()
        log(f"  {name}: hit the {timeout_h}h cap and was stopped (work is cached, it resumes)")
        return "timeout"
    except Exception as e:
        log(f"  {name}: {type(e).__name__} {str(e)[:80]}")
        return "error"


def start(name, args, logfile):
    """Launch a job without waiting for it.

    The roll is network-bound and the reader is GPU/Cascade-bound: they contend for nothing.
    Running them in sequence left one resource idle for the whole of the other's turn, which on
    a 6.8h roll meant the model did no reading at all that cycle. Returns None if the job was
    already running -- the same basename guard as run(), which exists because a second roll was
    once launched against a live one.
    """
    if running(os.path.basename(args[0])):
        log(f"  {name}: already running, left alone")
        return None
    lf = os.path.join(STATE, logfile)
    log(f"  {name}: starting (background)")
    fh = open(lf, "w", encoding="utf-8")
    env = dict(os.environ, PYTHONIOENCODING="utf-8")
    p = subprocess.Popen([PY, "-u"] + args, cwd=HERE, stdout=fh,
                         stderr=subprocess.STDOUT, env=env,
                         creationflags=NO_WINDOW)
    return {"name": name, "proc": p, "fh": fh, "t0": time.time()}


def join(job, timeout_h):
    """Wait out a backgrounded job, with the same wall-clock ceiling run() applies.

    The ceiling is on TIME, not on content -- every job here is resumable from cache, so a
    stopped job continues next cycle from where it stopped. Nothing is dropped.
    """
    if not job:
        return "already-running"
    try:
        job["proc"].wait(timeout=timeout_h * 3600)
        rc = job["proc"].returncode
        log(f"  {job['name']}: finished rc={rc} in {(time.time()-job['t0'])/60:.0f}m")
        if rc != 0:
            tail(os.path.join(STATE, os.path.basename(job["fh"].name)), job["name"])
        return "ok" if rc == 0 else f"rc={rc}"
    except subprocess.TimeoutExpired:
        job["proc"].kill()
        log(f"  {job['name']}: hit the {timeout_h}h cap and was stopped (cached, it resumes)")
        return "timeout"
    except Exception as e:
        log(f"  {job['name']}: {type(e).__name__} {str(e)[:80]}")
        return "error"
    finally:
        try:
            job["fh"].close()
        except Exception as e:
            log(f"  {job['name']}: log handle {type(e).__name__}")


def foreman_report():
    """What the foreman fixed this cycle, and what it could not.

    The supervisor log is where somebody looks in the morning, so the repair record belongs
    beside the coverage numbers rather than in a file of its own that nobody opens.
    """
    path = os.path.join(HERE, "data", "FOREMAN.json")
    try:
        with open(path, encoding="utf-8") as f:
            rounds = json.load(f)
    except Exception:
        return
    if not rounds:
        return
    last = rounds[-1]
    did = [a for a in (last.get("auto") or []) if a.get("did")]
    if did:
        log(f"  foreman: {len(did)} remedy(ies) applied at {last.get('at', '?')}")
        for a in did[:5]:
            log(f"    {a['standard']} -> {a['remedy']}: {a.get('result', '')[:70]}")
    owner = last.get("owner") or []
    if owner:
        log(f"  foreman: {len(owner)} order(s) need the owner -- see FOR_OWNER.md")


def watch_report(top=6):
    """What the standing debug sweep has open, surfaced where the night's log will show it.

    `overwatch` writes WATCH.md for a person to read. This puts the headline in the supervisor
    log too, because a report nobody opens is the same as a report nobody wrote -- which is the
    failure mode every watcher in this project has had at least once.
    """
    path = os.path.join(HERE, "data", "OVERWATCH.json")
    try:
        with open(path, encoding="utf-8") as f:
            d = json.load(f)
    except Exception:
        return
    open_f = [v for v in (d.get("findings") or {}).values() if v.get("state") == "open"]
    if not open_f:
        log(f"  overwatch: round {d.get('rounds', 0)}, nothing open")
        return
    hi = [f for f in open_f if (f.get("severity") or "").lower() == "high"]
    log(f"  overwatch: {len(open_f)} finding(s) open ({len(hi)} high) after "
        f"{d.get('rounds', 0)} round(s):")
    for f in sorted(open_f, key=lambda x: -(x.get("severity") == "high"))[:top]:
        log(f"    {f.get('module','?')}.py {f.get('symbol','')}: {f.get('actual','')[:96]}")


def ledger_report(top=8):
    """What the swallowed failures were this cycle.

    Every `except` in src/ now records its class before continuing (see silence.py). This is
    where that pays: 5,590 identical HTTPErrors show up as one loud line instead of as 5,590
    entities that look like they honestly have no page.
    """
    path = os.path.join(HERE, "state", "failures.json")
    try:
        with open(path, encoding="utf-8") as f:
            d = json.load(f)
    except Exception:
        return
    if not d:
        return
    rows = sorted(d.items(), key=lambda kv: -kv[1])[:top]
    log(f"  swallowed failures: {sum(d.values()):,} recorded, top {len(rows)}:")
    for k, v in rows:
        log(f"    {v:>8,}  {k}")


# A cycle shorter than this did no real work: the roll alone takes hours and the reader takes
# hours more. Anything faster means the jobs are failing on startup.
MIN_CYCLE_SECONDS = 300
IDLE_LIMIT = 3
WAIT_SECONDS = 600


def tail(path, name, n=12):
    """Put a failed job's last words in the supervisor log.

    Without this a job that dies on line one records `finished rc=1 in 0m` and the cycle turns
    again -- which is what happened for ten cycles while the reader was crashing on its own
    banner. The supervisor is supposed to be the thing that CANNOT be fooled by a plausible
    negative result; a bare exit code is exactly that.
    """
    try:
        with open(path, encoding="utf-8", errors="replace") as f:
            lines = [ln.rstrip() for ln in f if ln.strip()]
    except Exception as e:
        log(f"    {name}: log unreadable ({type(e).__name__})")
        return
    if not lines:
        log(f"    {name}: exited nonzero and wrote NOTHING -- it died before its first output")
        return
    log(f"    {name}: last {min(n, len(lines))} lines --")
    for ln in lines[-n:]:
        log(f"      {ln[:160]}")


def coverage_snapshot():
    try:
        subprocess.run([PY, os.path.join(SRC, "coverage.py")], cwd=HERE,
                       capture_output=True, text=True, timeout=1800,
                       env=dict(os.environ, PYTHONIOENCODING="utf-8"), creationflags=_NO_WIN)
        rows = json.load(open(os.path.join(HERE, "data", "COVERAGE.json"), encoding="utf-8"))
    except Exception as e:
        silence.note("overnight.py:124")
        return {"error": f"{type(e).__name__} {str(e)[:60]}"}
    n = sum(r["entries"] for r in rows)
    cited = sum(r["cited"] for r in rows)
    read = sum(r["read"] for r in rows)
    return {"entries": n, "cited": cited, "read": read, "feats": sum(r["feats"] for r in rows),
            "cited_pct": round(100 * cited / max(n, 1), 2),
            "settled_pct": round(100 * (cited + read) / max(n, 1), 2)}


def preflight():
    """Returns (n_problems, blocking). Only corrupted source blocks."""
    try:
        r = subprocess.run([PY, os.path.join(SRC, "health.py"), "--preflight"], cwd=HERE,
                           capture_output=True, text=True, timeout=1800,
                           env=dict(os.environ, PYTHONIOENCODING="utf-8"), creationflags=_NO_WIN)
        out = r.stdout
    except Exception:
        silence.note("overnight.py:141")
        return 0, False
    for ln in out.splitlines():
        if ln.strip().startswith("FAIL"):
            log(f"    preflight {ln.strip()}")
    blocking = "control characters in source" in out and "FAIL  control" in out
    n = out.count("FAIL")
    return n, blocking


def write_status(cycle, history):
    p = os.path.join(HERE, "STATUS.md")
    cur = history[-1] if history else {}
    first = history[0] if history else {}
    with open(p, "w", encoding="utf-8") as f:
        f.write("# Overnight run\n\n")
        f.write(f"Last update: {datetime.datetime.now():%Y-%m-%d %H:%M:%S}  ")
        f.write(f"(cycle {cycle})\n\n")
        f.write("## Citation coverage\n\n")
        f.write("| | now | at start | change |\n|---|---:|---:|---:|\n")
        for k, label in (("cited", "entries cited"), ("read", "read, no feat"),
                         ("feats", "feats on record"),
                         ("cited_pct", "cited %"), ("settled_pct", "settled %")):
            a, b = cur.get(k, 0), first.get(k, 0)
            f.write(f"| {label} | {a:,} | {b:,} | {a - b:+,} |\n")
        f.write("\n## Cycles\n\n| cycle | time | cited | settled % | feats |\n")
        f.write("|---|---|---:|---:|---:|\n")
        for h in history[-12:]:
            f.write(f"| {h.get('cycle','')} | {h.get('at','')} | {h.get('cited',0):,} | "
                    f"{h.get('settled_pct',0)} | {h.get('feats',0):,} |\n")
        f.write("\n## Logs\n\n`state/overnight.log` is the supervisor. Per-stage logs are\n")
        f.write("`state/roll_auto.log`, `state/read_auto.log`, `state/pipeline_auto.log`.\n")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--cycles", type=int, default=99)
    ap.add_argument("--read-hours", type=float, default=3.0)
    ap.add_argument("--read-workers", default="auto",
                    help="number, or 'auto' to match the pool's usable buckets")
    a = ap.parse_args()

    # ONE SUPERVISOR. Two watchdogs once launched two of these twenty seconds apart; both ran
    # full cycles, their foremen shot each other's children, and the pair respawned every three
    # minutes. running() excludes this process's own pid, so a survivor here means a TWIN.
    if running("overnight.py"):
        log("another supervisor is already running -- exiting rather than duelling it")
        return 0

    log("=" * 70)
    log("overnight supervisor starting")
    history = []
    idle = 0
    for cycle in range(1, a.cycles + 1):
        log(f"--- cycle {cycle} ---")
        cycle_t0 = time.time()
        n, blocking = preflight()
        if blocking:
            log("  HALT: a source file carries a control character where an escape should be.")
            log("  A corrupted regex matches nothing silently; continuing would spend the night")
            log("  producing confident emptiness. Repair and restart.")
            break
        if n:
            log(f"  preflight: {n} problem(s) noted, continuing")

        # 1. Network: gather source pages. Cheap, resumable, safe to repeat. Backgrounded --
        #    it contends with the reader for nothing, and blocking on it wasted the GPU.
        statuses = []
        # 0a. THE INSTRUMENTS. Always up, so the owner never has to ask anybody where things
        #     stand. It is a read-only HTTP server on localhost and costs nothing to leave
        #     running; the alternative is a dashboard that exists but is not on.
        start("dashboard", [os.path.join(SRC, "dashboard.py"), "--port", "8777"],
              "dashboard.log")
        # 0a2. THE PUBLISHER. Syncs the code and a scrubbed snapshot to the public repo every
        #      ten minutes, so the panel is readable from a phone. It copies a NAMED SUBSET into
        #      a clean tree rather than ignoring things out of this one -- the mined corpus is
        #      489MB of third-party wiki text and must never travel by accident.
        start("publish", [os.path.join(SRC, "publish.py"), "--push", "--loop", "10"],
              "publish.log")
        # 0a3. THE FOREMAN. Reads the work orders `standards` produces and acts on the ones
        #      with a scripted remedy -- clearing mis-learned rate caps, re-proving which
        #      buckets answer, re-running host adoption. Everything mechanical I did by hand
        #      today, on a loop. What it cannot fix goes to FOR_OWNER.md, and code defects go to
        #      the model lane. A list nobody acts on is a tidier version of the problem.
        # --patch ON. The model lane repairs code defects unattended, behind six gates: one
        # file, never one on the denylist, it parses, under 40 lines changed, the module still
        # imports, verify_math still reports 0 FAILED, and allsweep finds no new broken module.
        # A backup is written before the patch and restored on ANY failure including an
        # exception inside the checking. It also yields the pool when the corpus read is
        # starving, because reading the library is the work and repairing the code protects it.
        start("foreman", [os.path.join(SRC, "foreman.py"), "--go", "--patch", "--loop", "30"],
              "foreman.log")
        # 0b. THE WATCHER. Its own long-lived process, started once and left alone -- it outlives
        #    a cycle deliberately, because the whole point is that something is looking BETWEEN
        #    the moments anybody looks. `start()` returns None if it is already running, which
        #    is the normal case after the first cycle.
        start("overwatch", [os.path.join(SRC, "overwatch.py"), "--loop", "20", "--modules", "4"],
              "overwatch.log")
        roll = start("roll", [os.path.join(SRC, "feats.py"), "--roll", "--workers", "6"],
                     LN.ROLL)

        # 2. GPU: the model reads pages and extracts cited feats. The long pole; capped so the
        #    cycle keeps turning and coverage keeps being measured.
        # Workers raised from 2 because the transport changed underneath this. Two was right
        # for local Ollama, where a single 19GB MoE at a 56/44 CPU/GPU split gets slower, not
        # faster, with a second client. Through Cascade the calls land on separately-metered
        # buckets and genuinely run in parallel -- measured at 1,837 calls/hour against roughly
        # 440 locally. Cascade keeps local Ollama in the pool as an unlimited bucket, so if every
        # cloud meter runs dry the work falls back to the GPU instead of stopping.
        statuses.append(run("read", [os.path.join(SRC, "read.py"), "--run",
                                     "--workers", str(a.read_workers)],
                            LN.READ, timeout_h=a.read_hours))
        statuses.append(join(roll, timeout_h=4))

        # 3. GPU: absorb the new feats into ceilings and per-entry judgements. Runs after the
        #    reader so it sees the evidence the reader just produced.
        statuses.append(run("pipeline", [os.path.join(SRC, "pipeline.py")],
                            "pipeline_auto.log", timeout_h=2))

        foreman_report()
        watch_report()
        ledger_report()
        snap = coverage_snapshot()
        snap["cycle_seconds"] = round(time.time() - cycle_t0)
        snap.update({"cycle": cycle, "at": f"{datetime.datetime.now():%H:%M}"})
        history.append(snap)
        log(f"  coverage: {snap.get('cited',0):,} cited ({snap.get('cited_pct')}%), "
            f"{snap.get('settled_pct')}% settled, {snap.get('feats',0):,} feats")
        write_status(cycle, history)

        # A cycle that does no work must not immediately begin another. Ten cycles once turned
        # in five minutes because every job was dying on startup, and the log recorded ten
        # tidy "finished" lines. Fast cycles are now counted, and a run of them halts the
        # supervisor loudly rather than burning the night on nothing.
        # "already-running" is not idleness. A job this supervisor did not start but which is
        # alive and working is the healthiest state there is, and counting it as a dead cycle
        # would halt the run precisely when everything was going well. The cycle just needs to
        # wait rather than spin.
        busy = [x for x in statuses if x == "already-running"]
        if busy and snap["cycle_seconds"] < MIN_CYCLE_SECONDS:
            log(f"  {len(busy)} job(s) already running and working; waiting "
                f"{WAIT_SECONDS // 60}m before looking again")
            idle = 0
            time.sleep(WAIT_SECONDS)
        elif snap["cycle_seconds"] < MIN_CYCLE_SECONDS:
            idle += 1
            log(f"  cycle took {snap['cycle_seconds']}s -- nothing worked "
                f"({idle}/{IDLE_LIMIT} in a row)")
            if idle >= IDLE_LIMIT:
                log("  HALT: every job has returned instantly for "
                    f"{IDLE_LIMIT} cycles. That is not an idle library, it is a broken one.")
                log("  Read the job logs named above; the failure is in the first lines of one.")
                break
            time.sleep(min(60 * idle, 600))
        else:
            idle = 0
    log("supervisor finished")
    return 0


if __name__ == "__main__":
    sys.exit(main())
