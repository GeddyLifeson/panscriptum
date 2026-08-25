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
import contextlib
import datetime
import json
import os
import subprocess
_NO_WIN = getattr(subprocess, "CREATE_NO_WINDOW", 0)

import sys
import time
import silence
import lognames as LN


def _prose_enabled(cfg=None):
    """Is the owner's prose gate open? (M25 / owner ruling 2026-08-25.)

    `cfg` mirrors `prose_gate.gate_open(cfg=None)` exactly: pass a parsed mapping to ask what
    the gate WOULD say about it, leave it None in production to read config.yaml fresh. Added
    run #31 so `drill._gates_agree` can compare the two layers in memory. It previously wrote
    five trial values into the LIVE config.yaml on every supervisor cycle and restored the file
    in a `finally` -- so a kill in that window left `prose_enabled: true` on disk permanently.
    The drill that proves the prose gate could open the prose gate.

    Read fresh from config.yaml on every cycle, deliberately: the owner turning prose on should
    not require restarting the supervisor. FAILS CLOSED -- an unreadable or absent config keeps
    prose off, because the failure this guards is "books written that nobody asked for", and a
    missing flag must not be the thing that authorises them.

    ADVERSARIAL AUDIT, 2026-08-25: this used to reimplement the check as
    `bool(cfg.get("prose_enabled", False))`, which is LOOSER than the real gate. Measured, every
    one of these opened this gate while `prose_gate.gate_open()` correctly refused them:
    `1`, `"1"`, `"true"`, `"no"`, and -- the dangerous one -- **`"false"`**, a completely
    plausible thing to type when DISABLING the flag. A quoted "false" is a truthy string.

    It was backstopped (generate.py re-checks strictly, so no prose was ever written), but two
    layers enforcing DIFFERENT invariants is not defence in depth, it is one layer and a decoy.
    Now delegates. The layers stay independent where independence matters -- a separate process,
    a separate decision point, a separate failure mode -- while agreeing on what "open" means.
    """
    try:
        import prose_gate
        return prose_gate.gate_open(cfg)[0]
    except Exception:
        silence.note("overnight.py:prose-gate")
        return False


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


_PROCS = {"at": 0.0, "out": ""}
_PROCS_LOCK = None


def _proc_lines(ttl=3.0):
    """One process enumeration, shared. A PowerShell/WMI spawn costs hundreds of ms, and
    `standards.check()` was calling running() twice per log file -- ~146 spawns per check, on
    a check the dashboard polls every five seconds and the publisher runs every ten minutes
    (found by the 2026-08-23 optimization sweep). Within the TTL every caller reads the same
    listing; the table cannot meaningfully change faster than that."""
    global _PROCS_LOCK
    if _PROCS_LOCK is None:
        import threading
        _PROCS_LOCK = threading.Lock()
    with _PROCS_LOCK:
        now = time.time()
        if now - _PROCS["at"] > ttl:
            try:
                _PROCS["out"] = subprocess.run(
                    ["powershell", "-NoProfile", "-Command",
                     "Get-CimInstance Win32_Process -Filter \"Name='python.exe' or "
                     "Name='pythonw.exe'\" | "
                     "ForEach-Object { $_.ProcessId.ToString() + '|' + $_.CommandLine }"],
                    capture_output=True, text=True, timeout=60, creationflags=_NO_WIN).stdout
                _PROCS["at"] = now
            except Exception:
                silence.note("overnight.py:proc-lines")
        return _PROCS["out"]


def running(fragment, include_self=False):
    """Is a python process already running this script?

    Checked by live command line rather than by a lock file: a lock file survives a kill and
    would block its stage for the rest of the night.

    Self-exclusion is by PROCESS ID, compared as a field. A first version looked for its own pid
    as a substring of the command line, where it never appears -- so the supervisor matched
    itself, and any command that merely MENTIONED a stage's filename counted as that stage
    running. It would have skipped every stage it was built to run.

    `include_self` EXISTS BECAUSE SELF-EXCLUSION ANSWERS ONLY ONE OF THE TWO QUESTIONS CALLERS
    ASK. The default (False) answers *"is anyone ELSE running this?"*, which is what a job about
    to launch a stage -- or refuse to start a second copy of itself -- needs. But a LIVENESS
    REPORT asks a different question: *"is job X up?"* -- and there the asker's own process is
    a perfectly good answer. Passing False for that question makes any job that reports on the
    roster permanently report ITSELF as down.

    That is not hypothetical; it was live for an unknown length of time and found on 2026-08-25
    (run #21) by reading the same standard off two renderers at one moment. `publish.py` computes
    the published page in its own process (`publish.py:168-172`), so the public panel said
    `publish.py,read.py` were down; `dashboard.py` computes the local page in ITS process, so at
    the same instant the local panel said `dashboard.py,read.py`. `allsweep.py`, a third and
    neutral process, saw both up. Each renderer was deleting itself from its own roster.

    The cost was not cosmetic. "every managed job is running" has NO remedy in `foreman.REMEDIES`,
    so every round routed it to the owner's decision file as an unexplained red -- and the genuine
    casualty (`read.py`, down from an M15 kill) was buried inside a string that ALWAYS contained
    one false name, which is exactly the finding-as-decoration failure `MAX_JOB_SILENCE_MIN`'s
    comment was written to refuse.

    Additive keyword with the old behaviour as the default, so no existing caller changes.
    """
    out = _proc_lines()
    if not out:
        return False
    mine = os.getpid()
    for ln in out.splitlines():
        pid, _, cmd = ln.partition("|")
        try:
            is_mine = int(pid.strip()) == mine
        except ValueError:
            # A non-integer pid field is a FORMATTING ROW of the probe's own output (header,
            # blank, continuation), present on every call by construction. Noting it filed
            # 35,806 ledger entries in two hours and buried every real failure class under a
            # probe artefact -- TWICE, because `silence.py --instrument` re-added the note
            # the evening sweep removed. The string below is a deliberate exemption marker:
            # the audit and the instrumenter both read it as "observed", so this handler
            # stays quiet on purpose and stays exempt.
            _ = "silence-exempt: routine formatting row of the probe's own output"
            continue
        if is_mine and not include_self:
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
        # APPEND, same m23 fix as start() below: run()-managed jobs (read, pipeline) restart
        # every supervisor lap, and "w" erased each lap's evidence just as surely as the
        # keeper's bounces did for standing jobs. Same separator idiom, same single-file
        # contract for the dashboard's _tail_match readers.
        with open(lf, "a", encoding="utf-8") as fh:
            with contextlib.suppress(Exception):
                fh.write(chr(10) + "=" * 28 + " %s session %s " % (
                    name, datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
                    + "=" * 28 + chr(10))
                fh.flush()
            env = dict(os.environ, PYTHONIOENCODING="utf-8")
            p = subprocess.Popen([PY, "-u"] + args, cwd=HERE, stdout=fh,
                                 stderr=subprocess.STDOUT, env=env,
                                 creationflags=NO_WINDOW)
            _PROCS["at"] = 0.0    # the table just changed; the shared cache must not deny it
            p.wait(timeout=timeout_h * 3600)
        el = time.time() - t0
        log(f"  {name}: finished {name_rc(p.returncode)} in {el/60:.0f}m")
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
    # APPEND, NEVER TRUNCATE (m23). This was `open(lf, "w")`, so every keeper-driven restart
    # destroyed that job's entire history -- and the keeper restarts a standing job whenever it
    # finds it down, which is the NORMAL path, not an edge case. It cost two investigations:
    # the 59-503 record that diagnosed the Ollama wedge in run #4 existed only in
    # pipeline_auto.log and was erased minutes after being read, and run #7 hit the same wall.
    # Any problem needing more than one restart to understand could not be investigated at all.
    #
    # Append plus a session separator rather than rotation, deliberately: the dashboard's
    # `_tail_match` readers assume ONE current file per job, and rotating to `<job>.N.log` would
    # silently change what they read. This keeps the file they expect and stops throwing the
    # evidence away. Borrowed from `trading_bot/log.py` and `rent_engine/scripts/weekly.py`,
    # which both open long-lived logs in append mode for exactly this reason.
    fh = open(lf, "a", encoding="utf-8")
    with contextlib.suppress(Exception):
        stamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        fh.write(f"\n{'=' * 78}\n=== {name} started {stamp} (pid pending)\n{'=' * 78}\n")
        fh.flush()
    env = dict(os.environ, PYTHONIOENCODING="utf-8")
    p = subprocess.Popen([PY, "-u"] + args, cwd=HERE, stdout=fh,
                         stderr=subprocess.STDOUT, env=env,
                         creationflags=NO_WINDOW)
    _PROCS["at"] = 0.0    # the table just changed; the shared cache must not deny it
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
        log(f"  {job['name']}: finished {name_rc(rc)} in {(time.time()-job['t0'])/60:.0f}m")
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
        silence.note("overnight.py:203")
        return
    if not rounds:
        return
    last = rounds[-1]
    did = [a for a in (last.get("auto") or []) if a.get("did")]
    if did:
        # STAMP EACH LINE WITH THE FOREMAN'S OWN TIME, AND SHOW ALL OF THEM (run #19).
        #
        # This is a REPLAY of FOREMAN.json's last round, printed when the supervisor's lap comes
        # round -- but `log()` prefixes every line with the SUPERVISOR'S current time. So a kill
        # the foreman performed at 22:00:55 appeared in overnight.log as
        # "[22:39:04]  ... kill_stalled_job: killed stalled read_auto:42972" -- misdated by 38
        # minutes, in the one log used to reconstruct what killed the reader and when. M15's
        # whole evidence base is timestamps out of this file, so a reader who trusts the line
        # prefix will attribute a kill to the wrong lap. The header carried the true time all
        # along; each line now carries it too, because that is the line people quote.
        #
        # `did[:5]` also had to go: the header announces a count and the list then delivered
        # fewer -- "6 remedy(ies) applied" above five lines. Nothing downstream parses this, so
        # the cap bought nothing and cost the sixth remedy its only mention.
        when = last.get("at", "?")
        log(f"  foreman: {len(did)} remedy(ies) applied at {when}")
        for a in did:
            log(f"    [{when}] {a['standard']} -> {a['remedy']}: {a.get('result', '')[:70]}")
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
        silence.note("overnight.py:229")
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
        silence.note("overnight.py:253")
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

# THE STANDING SET — the jobs the keeper re-asserts every five minutes. Module-level, and
# deliberately so: this roster used to live inside main() while THREE other places carried
# their own partial copy of it (allsweep's process check knew four jobs, autostart's status
# display knew six, this knew five). A job missing from a roster does not read as "not
# listed", it reads as NOT RUNNING — which is how allsweep came to report 4 live jobs across
# runs #7-#10 while the process table held nine. One list, imported by its readers.
STANDING = [
    ("dashboard", [os.path.join(SRC, "dashboard.py"), "--port", "8777"], "dashboard.log"),
    ("publish", [os.path.join(SRC, "publish.py"), "--push", "--loop", "10"], "publish.log"),
    ("foreman", [os.path.join(SRC, "foreman.py"), "--go", "--patch", "--loop", "30"],
     "foreman.log"),
    ("overwatch", [os.path.join(SRC, "overwatch.py"), "--loop", "20", "--modules", "4"],
     "overwatch.log"),
    ("pipeline", [os.path.join(SRC, "pipeline.py")], "pipeline_auto.log"),
]

# Every long-lived job the kit runs, as the command-line fragment that identifies it. The
# keeper's STANDING set is the subset it can restart on its own; `read.py` and `feats.py
# --roll` hang off this supervisor's hours-long main lap, and the supervisor and its launcher
# sit above all of it. Anything asking "what should be up right now?" reads THIS, not a
# hand-kept subset of it.
ALL_JOBS = (["autostart.py", "overnight.py"]
            + [os.path.basename(args[0]) for _n, args, _l in STANDING]
            + ["read.py", "feats.py --roll"])


def name_rc(rc):
    """Say what an exit code MEANS, not just what it is. `rc=<number>` is not a diagnosis.

    Run #24. `read.py` exited `rc=4294967295` three times running (02:41, 02:50, 03:47) and the
    supervisor logged the bare number each time. Run #23 read the first two, matched them
    against its own commit times, and filed them as "run #22b's process bounce, not a fault" --
    a reasonable guess that the third occurrence disproves, because nothing was bouncing at
    03:47. The number carried no information either way, so the guess was never testable.

    That is the "unrecognised failure is a bug, not weather" rule reaching the JOB layer. The
    pool side already has `cascade_bridge.record_unrecognised` and a standard that goes red on
    an unnameable refusal; the job side had nothing, so an exit code nobody could name simply
    scrolled past. Naming them is what makes the reader's history readable at a glance -- and
    read back over `state/overnight.log` it immediately separates the eras: every reader exit
    up to 02:17 today was `15`, a foreman remedy (M15); every one after 02:30 is `-1`, which no
    remedy in this repo produces.

    The three that matter here, and they are genuinely different faults:
      15   psutil's kill() on Windows terminates with the signal number -- a foreman remedy.
      1    an ordinary Python error exit, or subprocess.Popen.kill().
      -1   TerminateProcess(handle, -1) by something OUTSIDE this supervisor. Not a remedy and
           not a Python crash, both of which land elsewhere. This is the one to chase.
    """
    try:
        rc = int(rc)
    except Exception:
        return "rc=%r" % (rc,)
    if rc == 0:
        return "rc=0 (clean)"
    signed = rc - (1 << 32) if rc >= (1 << 31) else rc
    known = {
        1: "a python error exit, or subprocess kill()",
        15: "SIGTERM -- a foreman remedy killed it (M15)",
        -1: "TerminateProcess(-1) from OUTSIDE this supervisor -- not a remedy (those are 15) "
            "and not a python crash (those are 1)",
        0xC000013A - (1 << 32): "STATUS_CONTROL_C_EXIT -- the console was closed or Ctrl-C'd",
        0xC0000005 - (1 << 32): "STATUS_ACCESS_VIOLATION -- a native crash",
        0xC0000409 - (1 << 32): "STATUS_STACK_BUFFER_OVERRUN",
        0xC00000FD - (1 << 32): "STATUS_STACK_OVERFLOW",
    }
    if signed in known:
        return "rc=%d (%s)" % (rc, known[signed])
    if rc >= 0xC0000000:
        return "rc=%d (0x%X: an unnamed Windows NTSTATUS crash code -- INVESTIGATE)" % (rc, rc)
    return "rc=%d (UNRECOGNISED exit code -- investigate rather than assume)" % rc


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
    except Exception as e:
        silence.note("overnight.py:141")
        # SAY SO (run #19). The return value below is indistinguishable from a clean preflight --
        # `(0, False)` takes neither of main()'s branches, so a health.py that crashed, timed out
        # after its 30 minutes, or could not be launched at all read exactly like "checked,
        # nothing wrong". The swallow was recorded only as a bare count in state/failures.json,
        # under a stale line-number key, never labelled as the preflight. The behaviour is
        # deliberately unchanged -- a preflight that cannot run must not block the cycle -- but
        # it no longer passes for a pass.
        log(f"  preflight: DID NOT RUN ({type(e).__name__}: {str(e)[:120]}) "
            f"-- continuing, but this cycle was NOT checked")
        return 0, False
    for ln in out.splitlines():
        if ln.strip().startswith("FAIL"):
            log(f"    preflight {ln.strip()}")
    blocking = "control characters in source" in out and "FAIL  control" in out
    n = out.count("FAIL")
    return n, blocking


def safety_drill():
    """Walk every safety net and confirm it still REFUSES. The scheduled park inspection.

    `preflight()` above asks whether the library is healthy. This asks a different and harder
    question: are the things that are supposed to STOP us still capable of stopping us? A guard
    nobody has watched refuse is a guard nobody has evidence about (standing lesson 9), and the
    incident this whole layer exists for was not a guard failing -- it was a guard being deleted,
    which no health check anywhere would have noticed.

    `drill.py` raises an OWNER-level halt by itself if any net is breached, so this does not need
    to decide anything; it runs the inspection and reports what the inspector found. Exit 1 means
    a net did not hold and the library has already stopped itself.
    """
    try:
        r = subprocess.run([PY, os.path.join(SRC, "drill.py")], cwd=HERE,
                           capture_output=True, text=True, timeout=900,
                           env=dict(os.environ, PYTHONIOENCODING="utf-8"), creationflags=_NO_WIN)
    except Exception as e:
        # Same discipline as preflight: a drill that could not run must not pass for a pass.
        silence.note("overnight.py:drill")
        log(f"  safety drill: DID NOT RUN ({type(e).__name__}: {str(e)[:120]}) "
            f"-- the nets were NOT inspected this cycle")
        return None
    line = [x for x in (r.stdout or "").splitlines() if x.startswith("DRILL:")]
    log("  safety drill: " + (line[-1] if line else "produced no summary line"))
    if r.returncode == 1:
        for x in (r.stdout or "").splitlines():
            if x.strip().startswith("BREACHED"):
                log("    " + x.strip())
        log("  A SAFETY NET DID NOT HOLD — the library has halted itself. "
            "Clear it with: python src/escalation.py --clear --ruling \"...\"")
    return r.returncode


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
    # PLANT-WIDE INTERLOCK. The top rung of the escalation chain (escalation.py). If a
    # library-wide invariant has been violated, nothing starts until a person rules on it.
    # Placed first in main() so there is no path into this job that skips it.
    try:
        import escalation as _ESC
    except ImportError as _esc_gone:
        # FAIL CLOSED. This used to be `except ImportError: pass`, which meant a deleted or
        # unparseable `escalation.py` silently switched the plant-wide halt off in every job
        # at once -- nine sites, all of them quiet about it. That is Hard Rule -1's own
        # incident wearing different clothes: the last one began with an autonomous run
        # removing a safety it had concluded was unnecessary, and nothing downstream could
        # tell. A job that cannot ask whether the library is halted has no business
        # starting. Pinned by verify_math so the swallow cannot come back. (run #31)
        raise SystemExit(
            "REFUSING TO START: the escalation chain (src/escalation.py) could not be "
            "imported (%s), so the halt cannot be read. Hard Rule -1." % _esc_gone)
    _ESC.assert_clear(os.path.basename(__file__))
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

    # THE KEEPER. The cycle re-asserts the standing jobs only at its TOP, and then blocks for
    # hours inside run(read) / join(roll) / run(pipeline) -- so a standing job that dies (or
    # is deliberately bounced onto new code) mid-cycle stays down until the next lap. Found
    # live on 2026-08-23: dashboard, publisher, foreman and overwatch were all down for the
    # length of a 4-hour roll join. This thread re-asserts the standing set every five
    # minutes from wherever the cycle happens to be blocked. start() keeps the singleton
    # guard, so the keeper can never double anything.
    import threading as _th

    def _keep():
        while True:
            time.sleep(300)
            for name, args, lf in STANDING:
                try:
                    # Checked silently first: start() logs "left alone" for a healthy job,
                    # and five of those every five minutes is log spam wearing a uniform.
                    if not running(os.path.basename(args[0])):
                        log(f"  keeper: {name} was down mid-cycle")
                        start(name, args, lf)
                except Exception:
                    silence.note("overnight.py:keeper")

    _th.Thread(target=_keep, daemon=True).start()

    def _keep_warm():
        """Hold the model resident AT THE CONFIGURED num_ctx.

        Two separate costs this pays off, both measured 2026-08-24.

        The ordinary one, which `motoko/discord_bot.py:495` records on this same card: Ollama
        evicts an idle model after about five minutes and reloading it costs tens of seconds on
        whatever call happens to be next. Its note -- "most of what 'she's slow' actually was".

        The sharp one, which is ours. Ollama serves a resident model at ONE context size, and a
        call asking for a different `num_ctx` must tear the runner down and rebuild it. Under
        contention that rebuild loses to the queue and simply never completes: measured, a call
        at the resident 4096 answered in 9-38 s while calls at 6144 and 8192 did not return at
        all, so the whole library was pinned to whichever size loaded first. A periodic ping AT
        THE CONFIGURED SIZE keeps the runner the right shape as well as merely warm.

        Skipped whenever the card is busy -- this must never become one more competitor for the
        thing it is protecting.
        """
        import json as _json
        import urllib.request as _ur
        try:
            import gpu_lane as _gl
        except Exception:
            # The one handler in this file that recorded nothing at all (found run #19), in a
            # module whose whole point is that a swallowed failure must leave a mark. It matters
            # more than most: `_gl` is checked once, before the loop, so a failure here is STICKY
            # for the process lifetime, and the busy-check below short-circuits to False forever
            # -- turning keep-warm into exactly the competitor the docstring above forbids. No
            # realistic failure surface on this machine (gpu_lane is stdlib-only and sits in the
            # same directory), which is why it has never fired; that is a reason to record it,
            # not a reason to leave it silent.
            silence.note("overnight.py:keepwarm-no-gpu-lane")
            log("  keep-warm: gpu_lane import FAILED -- busy-check disabled for this process")
            _gl = None
        while True:
            time.sleep(120)
            try:
                if _gl is not None and (_gl.status()["slots"] or _gl.foreground_active()):
                    continue                      # busy; poking it would only add to the queue
                cfg = {}
                with contextlib.suppress(Exception):
                    import yaml
                    with open(os.path.join(HERE, "config.yaml"), encoding="utf-8") as f:
                        cfg = yaml.safe_load(f) or {}
                host = cfg.get("ollama_host", "http://localhost:11434")
                body = _json.dumps({
                    "model": cfg.get("model"), "prompt": "ok", "stream": False,
                    "keep_alive": "10m",
                    "options": {"num_ctx": int(cfg.get("num_ctx", 6144)), "num_predict": 1},
                }).encode()
                req = _ur.Request(host.rstrip("/") + "/api/generate", data=body,
                                  headers={"Content-Type": "application/json"})
                with _ur.urlopen(req, timeout=120):
                    pass
            except Exception:
                silence.note("overnight.py:keep_warm")

    _th.Thread(target=_keep_warm, daemon=True).start()

    history = []
    idle = 0
    for cycle in range(1, a.cycles + 1):
        log(f"--- cycle {cycle} ---")
        cycle_t0 = time.time()

        # THE PLANT-WIDE INTERLOCK, RE-ASKED EVERY CYCLE. A halt raised while the supervisor was
        # mid-cycle must stop the NEXT one; checking only at startup would let a halted library
        # keep running for hours because the process that needed to notice had already started.
        try:
            import escalation as _ESC
        except ImportError as _esc_gone:
            # FAIL CLOSED -- see the note on the startup interlock above. A supervisor that
            # cannot read the halt must stop the cycle loop, not keep dispatching stages.
            raise SystemExit(
                "REFUSING TO CONTINUE: the escalation chain (src/escalation.py) could not "
                "be imported (%s), so the halt cannot be read. Hard Rule -1." % _esc_gone)
        try:
            _ESC.assert_clear("overnight.py cycle %d" % cycle)
        except Exception as e:
            log("  " + str(e).splitlines()[0])
            log("  The library is halted. Nothing further will start until a person rules on it.")
            break

        # THE PARK INSPECTION. Every cycle, before any stage is started: are the things that are
        # supposed to stop us still able to? Cheap (no model calls, no network) and it is the
        # only check that would notice a safety having been REMOVED rather than having failed.
        safety_drill()

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
        # THE GPU-SERIAL RULE IS OBSOLETE, AND KEEPING IT WAS WASTING A WHOLE STAGE. It
        # existed because read.py and pipeline.py both drove local Ollama. The reader has been
        # cascade-first for a day -- its local fallback is rare and benched -- so the card sat
        # idle while 33,000 new Marvel entries waited for entrypass judgment. The phases ARE
        # the GPU's job now. running() guards the singleton as everywhere else.
        start("pipeline", [os.path.join(SRC, "pipeline.py")], "pipeline_auto.log")
        # PROSE RUNS ITSELF. phase_write builds the manifest and used to end with a log line
        # telling a PERSON to run generate.py -- an instruction to a human inside an
        # automation (found by the 2026-08-23 sweep). generate is resumable and exits in
        # seconds when nothing is pending, so starting it every cycle is idle-cheap; when
        # phase 8 has produced work, this is what writes the books.
        # THE GATE IS BACK, AND IT IS THE OWNER'S (ruling 2026-08-25). The comment above is the
        # reasoning that removed it: a log line telling a PERSON to run generate.py did read as
        # an instruction to a human inside an automation. But the remedy deleted the decision
        # rather than relocating it, and the decision was load-bearing -- prose was on hold until
        # the Step 4 entanglement pass, and this wrote 145 chapters straight through that hold.
        # `prose_enabled` in config.yaml is where the decision lives now: still out of the log,
        # still not an instruction to a human, but no longer taken by the automation either.
        manifest = os.path.join(HERE, "output", "index", "manifest.json")
        if os.path.exists(manifest) and _prose_enabled():
            start("prose", [os.path.join(SRC, "generate.py"), "--manifest", manifest],
                  "prose_auto.log")
        roll = start("roll", [os.path.join(SRC, "feats.py"), "--roll", "--workers", "12"],
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
        # A crashed snapshot carries ONLY an "error" key, which nothing read (run #19). The log
        # line below then printed "None% settled" and write_status()'s `.get(k, 0)` defaults
        # rendered the cycle as a clean row of zeroes in STATUS.md -- a measurement failure
        # wearing the shape of a measured zero. Nothing downstream acts on it (verified: no
        # module parses STATUS.md; publish copies it verbatim and estate.py only hashes it), so
        # this is a reporting fix, not a correctness one.
        if snap.get("error"):
            log(f"  coverage: SNAPSHOT FAILED ({snap['error']}) "
                f"-- this cycle's row in STATUS.md is not a measurement")
        else:
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
                # A HALTED LIBRARY IS NOT A BROKEN ONE, AND MUST NOT BE TREATED AS ONE.
                #
                # Found the hard way, 2026-08-25, and it was self-inflicted. The escalation
                # halt makes every job's `main()` exit immediately -- which is exactly what it
                # is for. But from HERE that is indistinguishable from every job crashing on
                # startup, so the supervisor concluded the library was broken, logged
                # "supervisor finished", and EXITED. Nothing then restarted anything, so
                # clearing the halt did not bring the library back: read.py, pipeline.py and
                # feats.py --roll all stayed down, and every library counter went flat.
                #
                # The safety mechanism caused the outage it exists to prevent -- standing
                # lesson 10, committed by the newest guard in the tree. So the halt is checked
                # FIRST, and a halted supervisor WAITS instead of giving up: the whole promise
                # of the halt is that work resumes when a person clears it.
                try:
                    import escalation as _ESC
                    _halted, _rec = _ESC.status()
                except Exception:
                    _halted, _rec = False, None
                if _halted:
                    log("  the library is HALTED (%s) -- every job is exiting on purpose, which "
                        "is not the same as failing. Waiting for a person to clear it."
                        % (_rec or {}).get("code"))
                    idle = 0
                    time.sleep(WAIT_SECONDS)
                    continue
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
