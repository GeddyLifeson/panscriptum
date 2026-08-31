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

  GPU-SERIAL IS OBSOLETE, AND THIS PARAGRAPH USED TO SAY THE OPPOSITE. It read "only one GPU
  stage runs at a time" while the body below started `pipeline` backgrounded alongside the
  reader -- true when `read.py` and `pipeline.py` both drove local Ollama at a 19GB model's
  56/44 CPU/GPU split, where two clients thrashed instead of doubling throughput. The reader
  has been cascade-first since 2026-08-25 -- its local-Ollama fallback is rare and benched --
  so the card sitting idle for a whole stage was wasted capacity, not caution. The roll is
  network-bound and has always been free to overlap with either.

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
    """One process enumeration, shared. -> the listing, or None meaning COULD NOT READ IT.

    A PowerShell/WMI spawn costs hundreds of ms, and `standards.check()` was calling running()
    twice per log file -- ~146 spawns per check, on a check the dashboard polls every five
    seconds and the publisher runs every ten minutes (found by the 2026-08-23 optimization
    sweep). Within the TTL every caller reads the same listing; the table cannot meaningfully
    change faster than that.

    THREE ANSWERS, NOT TWO (order 1d556b6ef535). This returned a STRING, so "I could not read
    the process table" arrived at `running()` as `''` and came out the far end as "nothing is
    running" -- a fact, acted on by every spawn site in this file. Two ways in, and neither
    left a mark: the spawn raised and the except only called `silence.note`, leaving
    `_PROCS['out']` at its previous value (`''` on the first call); or the spawn SUCCEEDED with
    empty stdout and a nonzero returncode, which was never read at all because
    `subprocess.run(...).stdout` was taken directly. The supervisor's ONE OF EACH invariant
    rests entirely on this sensor, so a blind reading starts dashboard, publish, foreman,
    overwatch, pipeline, roll, read and prose as DUPLICATES -- verbatim the incident this
    module's docstring opens with -- and the keeper re-asserts the whole standing set every
    300s on the same blind reading. It also defeated the deliberate tri-state given to
    `autostart.supervisor_alive()`, which was `bool()` wrapped around a sensor with no way to
    say "I don't know".

    AN EMPTY LISTING IS ALSO UNKNOWN, not "no python is running". The filter is python.exe /
    pythonw.exe and the CALLER IS ONE OF THOSE, so a probe that worked cannot come back with
    zero rows; empty stdout means the enumeration did not happen. The nonzero-rc case is
    checked for the same reason.

    An unknown is NOT cached: `_PROCS['out']` keeps the last good listing and `_PROCS['at']`
    is left un-stamped, so the very next caller retries the spawn rather than inheriting the
    blindness for a TTL.
    """
    global _PROCS_LOCK
    if _PROCS_LOCK is None:
        import threading
        _PROCS_LOCK = threading.Lock()
    with _PROCS_LOCK:
        now = time.time()
        if now - _PROCS["at"] > ttl:
            try:
                r = subprocess.run(
                    ["powershell", "-NoProfile", "-Command",
                     "Get-CimInstance Win32_Process -Filter \"Name='python.exe' or "
                     "Name='pythonw.exe'\" | "
                     "ForEach-Object { $_.ProcessId.ToString() + '|' + $_.CommandLine }"],
                    capture_output=True, text=True, timeout=60, creationflags=_NO_WIN)
            except Exception:
                silence.note("overnight.py:proc-lines")
                return None
            if r.returncode != 0 or not (r.stdout or "").strip():
                silence.note("overnight.py:proc-lines-blind")
                return None
            _PROCS["out"] = r.stdout
            _PROCS["at"] = now
        return _PROCS["out"]


_BLIND_WINDOW_SECONDS = 3600      # matches autostart.START_WINDOW_SECONDS, same purpose
_BLIND_SAID = {}


def _blind(where, message):
    """Say "the process table could not be read" at most once an hour per site. -> None.

    The keeper asks every 300s and the cycle asks at every stage, so an instrument that is
    broken for an evening would otherwise write the same line into overnight.log a hundred
    times and bury the night. `autostart.watch()` throttles its identical concession the same
    way and for the same reason; the window constant is copied from it rather than invented.
    """
    now = time.time()
    if now - _BLIND_SAID.get(where, 0.0) >= _BLIND_WINDOW_SECONDS:
        _BLIND_SAID[where] = now
        log(message)


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

    RETURNS None WHEN THE PROBE COULD NOT SEE (order 1d556b6ef535). `_proc_lines()` can now say
    "I could not read the process table", and that is not the same claim as "nobody is running
    this". None is falsy, so the read-only callers that only ever ask `if running(x)` (foreman's
    four repair gates, standards' roster) behave exactly as they did -- they were already
    getting False from a blind probe. The SPAWN sites in this file are the ones that must not,
    and each of them tests `is None` explicitly rather than leaning on truthiness.
    """
    out = _proc_lines()
    if out is None:
        return None
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
        if not _cmd_is_running(fragment, cmd):
            continue
        # AND IT MUST BE THIS TREE'S COPY. `mutate.py` runs the whole battery inside a SANDBOX --
        # a throwaway temp copy of `src/` -- so a sandboxed `python src/verify_math.py` has a
        # command line indistinguishable from the live one and differs only in its cwd. Matching
        # on the name alone made the battery's own answer depend on whether a mutation run
        # happened to have a child alive, which is a check whose result is not a fact about the
        # library. `codewatch.twins()` was fixed for exactly this earlier in run #34, after the
        # same confusion HALTED the library; this is the same rule, asked of the same fields.
        if not _in_this_tree(int(pid.strip()), cmd):
            continue
        return True
    return False


def _in_this_tree(pid, cmd):
    """Is the script on this command line THIS checkout's copy? -> bool.

    FAILS OPEN BY SAYING NO, matching `codewatch.twins()`: a process we cannot resolve is not
    counted as running the job. That direction is deliberate and it is the cheaper error here --
    the cost is starting a second copy of something, which the stage guards catch, whereas the
    other direction is a job that refuses to run for ever because of a process in a directory it
    has nothing to do with. That failure has already cost this project one outage.
    """
    toks = cmd.replace("\\", "/").split()
    script = next((t for t in toks if t.endswith(".py")), None)
    if not script:
        return False
    if not os.path.isabs(script):
        try:
            import psutil
            script = os.path.join(psutil.Process(pid).cwd(), script)
        except Exception:
            return False              # cannot tell whose copy it is -- see the docstring
    try:
        return os.path.samefile(script, os.path.join(HERE, "src", os.path.basename(script)))
    except OSError:
        return False                  # vanished mid-walk, or unreadable


def _cmd_is_running(fragment, cmd):
    """PURE. Does this command line show `fragment` BEING RUN, rather than merely mentioned?

    THE SECOND ARM USED TO BE `fragment in cmd`, AND THAT IS A MENTION TEST, NOT A RUN TEST.
    `allsweep` lints the tree with `pyflakes src/codewatch.py src/publish.py src/foreman.py
    src/overwatch.py`, which names four daemons in one command line, so for the ~120 seconds that
    linter runs every one of them reads as UP. `autostart.supervisor_alive()` asks this question,
    so a dead supervisor was reported alive for two minutes out of every sweep -- and the reverse
    error, a job refusing to start because somebody was reading its file, is the same coin.

    This is the identical defect `codewatch.twins()` carried until run #34, where matching on a
    bare basename let a SANDBOXED `verify_math.py` -- a temp copy, run by `mutate.py` exactly as
    designed -- count as a twin of the live one and HALT THE LIBRARY. Fixed there by asking which
    file is being RUN; fixed here the same way, because two spellings of one rule is how those two
    sites drifted apart in the first place.

    A fragment may carry arguments (`feats.py --roll` is a real one, from `lognames.OWNER`), so
    the script half must be the script ARGUMENT and every remaining word must appear among the
    args -- never anywhere in the string.
    """
    parts = fragment.split()
    want, want_args = parts[0], parts[1:]
    toks = cmd.replace("\\", "/").split()
    if not toks:
        return False
    # THE INTERPRETER MUST BE PYTHON, which is what separates running a script from reading one.
    # Without this, `grep -rn read.py src/` matches `read.py` -- a linter, a grep, an editor or a
    # shell that merely NAMES the file would each count as the job running it. `codewatch.twins()`
    # carries the same test for the same reason, and its docstring records finding it within a
    # minute of the first version being written.
    if "python" not in os.path.basename(toks[0]).lower():
        return False
    # `-m` MEANS THE INTERPRETER IS RUNNING A MODULE, AND ANY .py AFTER IT IS THAT
    # MODULE'S ARGUMENT, NOT THE SCRIPT (found 2026-08-30, sweep39-batch11 + this run).
    # The loop below takes the FIRST token ending in ".py" as the script -- so
    # `python -m pyflakes src/codewatch.py src/publish.py src/foreman.py
    # src/overwatch.py` reported codewatch.py as RUNNING. That is this function's own
    # docstring example: it names that exact command as the mention-vs-run defect it was
    # written to end, and it still let the first of the four through. Measured before the
    # fix: mention-test said all four were up, this said one was.
    #
    # A linter, a formatter, a test runner and `pip` are all `python -m <tool> <files>`,
    # so this is the common shape, not an exotic one. Refusing outright is right rather
    # than conservative: `-m` genuinely means no .py on that line is being run as a
    # script, and every caller here -- allsweep's roster, `codewatch.twins`,
    # `autostart.supervisor_alive` -- is asking about scripts.
    script = None
    for i, tok in enumerate(toks[1:], start=1):
        if tok == "-m":
            return False
        if tok.endswith(".py"):
            script = tok
            rest = toks[i + 1:]
            break
    else:
        return False                      # no script argument at all: nothing is being RUN here
    if os.path.basename(script) != os.path.basename(want):
        return False
    # Every argument named in the fragment must be present, so `feats.py --roll` does not match a
    # `feats.py --mine`. Absent from the fragment means "any invocation of this script".
    return all(a in rest for a in want_args)


# Windows opens a console for every child process unless told not to. `autostart.py` already
# passes CREATE_NO_WINDOW for the supervisor itself -- but the supervisor then spawns eight jobs
# of its own without it, so the watchdog starts silently and then eight empty black windows
# appear on the owner's desktop. Every one of them shows nothing, because stdout is redirected
# into state/*.log by the lines just below.
#
# DETACHED_PROCESS is deliberately NOT set here, unlike in autostart: these children are joined
# and their return codes are read, and a detached child cannot be waited on.
NO_WINDOW = getattr(subprocess, "CREATE_NO_WINDOW", 0)

_SPAWN_LOCK = None


def _spawn_lock():
    global _SPAWN_LOCK
    if _SPAWN_LOCK is None:
        import threading
        _SPAWN_LOCK = threading.Lock()
    return _SPAWN_LOCK


def _guarded_popen(name, args, fh, banner=None):
    """Check-then-spawn, SERIALISED against every other thread in this process. -> Popen | None.

    THE SINGLETON GUARD WAS A CHECK AND A SPAWN WITH NOTHING HOLDING THEM TOGETHER, and this
    process runs two threads that both make that pair of calls for the SAME job names: the keeper
    (every 300s) and the cycle's own standing starts at the top of each lap. `_PROCS_LOCK`
    protects the process-table CACHE, not the decision -- so both threads could read
    `running() == False` from the same 3-second-old listing, and both call `Popen`. The keeper's
    own comment says "start() keeps the singleton guard, so the keeper can never double
    anything"; that was true of one thread and this file has had two since the keeper was added.
    ONE OF EACH is the invariant the whole supervisor is built on, and a doubled `pipeline` or
    `publish` is exactly the failure `run()`'s docstring records having already cost this project
    once.

    Double-checked deliberately: `run()` and `start()` still make their own cheap unlocked call
    first, so the ordinary "already running, left alone" log line is unchanged and no caller
    waits on a lock to be told nothing needs doing. This second check is the authoritative one,
    and it is the one that is atomic with the spawn.

    `banner` IS THE JOB LOG'S SESSION SEPARATOR, AND IT IS WRITTEN HERE (order e038910102b4).
    Both callers used to write it before calling this, which meant a caller that lost the race
    above had already stamped "session started" into that job's log for a process it did not
    start. The docstring used to call the stray separator the cheaper half of a trade; it is
    not a trade at all, it is just a shorter function. These logs are the forensic record an
    incident gets reconstructed from, and a start banner with no start behind it is the one
    kind of noise that costs an investigation rather than annoying it -- two banners, one real
    process, and nothing in the file saying which was which. Written under the lock, after the
    authoritative check and before the spawn, so it appears exactly when a spawn happens.
    Suppressed like the writes it replaces: an unwritable log must not stop a job starting.
    """
    with _spawn_lock():
        # FAIL CLOSED ON A BLIND PROBE (order 1d556b6ef535). The lock serialises the DECISION,
        # never the BLINDNESS: two threads reading None would both have been told "not running"
        # and both spawned. `is None` before truthiness, because None is falsy and the old test
        # could not tell the two apart.
        _up = running(os.path.basename(args[0]))
        if _up is None:
            _blind("guarded-popen", f"  {name}: cannot read the process table, so NOT starting "
                                    f"it -- a blind spot is not an absence")
            return None
        if _up:
            log(f"  {name}: already running, left alone (found on the second check)")
            return None
        if banner is not None:
            with contextlib.suppress(Exception):
                banner()
        env = dict(os.environ, PYTHONIOENCODING="utf-8")
        p = subprocess.Popen([PY, "-u", *args], cwd=HERE, stdout=fh,
                             stderr=subprocess.STDOUT, env=env,
                             creationflags=NO_WINDOW)
        _PROCS["at"] = 0.0    # the table just changed; the shared cache must not deny it
        return p


CANON_BACKUP_EVERY_HOURS = 12


def canon_backup_cycle():
    """Take a verified snapshot of the canonical corpus, at most twice a day. Never raises.

    WHY THIS IS IN THE SUPERVISOR AND NOT ONLY IN THE MAINTENANCE RUN. `canon_backup.py` was
    written on 2026-08-27 after order ec67de571754 established that `data/` is gitignored, that
    `git ls-files data/` returns zero, and that 219 canonical files -- 214.7 MB, the 217-source
    corpus every other file in `data/` is derived FROM -- existed in exactly one place on one
    disk. The immediate exposure was closed by taking a snapshot by hand.

    A backup that happens only when somebody remembers to take one is not a backup policy, it is
    a backup anecdote. The incident that prompted the order took two overwrites of a canonical
    file inside a single shift; the gap between two maintenance runs is a day. So the supervisor
    takes it, on the same cycle it does everything else.

    RATE-LIMITED BY THE NEWEST SNAPSHOT'S OWN TIMESTAMP, not by a counter in memory: the
    supervisor restarts (rc=17 on a source change, among others) and a counter would reset with
    it, so a restarting supervisor would snapshot every cycle and churn 50 MB a time.

    NEVER RAISES. A failed backup must not take down the night's work -- it is recorded, loudly,
    and the cycle goes on. The one thing it may not do is fail silently, because a backup nobody
    knows has stopped is worse than no backup at all: it is a backup that will be trusted.
    """
    try:
        import canon_backup as CB
    except ImportError as e:
        log(f"  canon backup: MODULE MISSING ({e}) -- the canonical corpus is unbacked")
        return
    try:
        newest = CB.newest()
        if newest:
            age_h = (time.time() - os.path.getmtime(newest)) / 3600.0
            if age_h < CANON_BACKUP_EVERY_HOURS:
                return
        t0 = time.time()
        path, man = CB.snapshot()
        pruned = CB.prune()
        log(f"  canon backup: {man['files']} files, {man['bytes'] / 1e6:.1f} MB, verified, "
            f"in {time.time() - t0:.0f}s"
            + (f" (pruned {len(pruned)})" if pruned else ""))
    except Exception as e:
        # LOUD. `snapshot()` refuses and deletes its own archive when it cannot verify what it
        # wrote, and that refusal arrives here as an exception -- which is exactly the event
        # that must not be swallowed.
        log(f"  canon backup: FAILED -- {e}")
        silence.note("overnight.py:canon-backup-failed")


def _manager_stopped(job, args=None):
    """Is this subsystem closed at rung 4? -> (bool, why). FAILS CLOSED.

    Asked BEFORE every launch. If escalation cannot answer -- module missing, ledger unreadable
    -- the job does NOT start: "I cannot tell whether a person closed this" has never been
    permission to re-open it, and the failure this guards against was twenty-six records losing
    their synthesis block while a stop went unread.

    MODULE-LEVEL SINCE ORDER 4c1eaa9df7fa, AND ASKED BY `start()`/`run()` THEMSELVES. It used to
    be a closure inside `main()` with exactly ONE caller, the keeper thread -- so the remedy for
    the 22:5x `catalogue_web` incident (order 4e7f1e47d0a0) landed on one of the TEN places this
    file launches jobs. The supervisor's own cycle body re-asserts the whole STANDING set at the
    top of every lap, plus prose, roll, read and the serial pipeline, and none of those consulted
    the ledger: a subsystem a person or a maintenance run closed at rung 4 was restarted within
    one lap by the very code the keeper's gate was written to stop. `escalation.subsystem_stopped`
    has no other callers in the tree, so these two functions are the whole enforcement surface;
    the gate belongs where the spawn is, not beside one caller of it.

    BOTH SPELLINGS OF THE NAME ARE HONOURED. The ledger's keys are free-form strings written by
    whoever stopped the subsystem, and the two natural spellings for the same thing are the
    supervisor's job name ("pipeline", "roll") and the script it runs ("pipeline", "feats").
    A stop is a person saying "not this"; honouring only the spelling they did not use is the
    same as not honouring it.
    """
    names = [str(job)]
    if args:
        stem = os.path.splitext(os.path.basename(str(args[0])))[0]
        if stem and stem not in names:
            names.append(stem)
    try:
        import escalation as _esc
        for n in names:
            held, why = _esc.subsystem_stopped(n)
            if held:
                return True, (why if n == str(job) else "%s (stopped as %r)" % (why, n))
        return False, ""
    except Exception:
        silence.note("overnight.py:manager-stop-unreadable")
        return True, "escalation unreadable; refusing to start on an unknown answer"


def run(name, args, logfile, timeout_h=6):
    """Run one stage to completion, refusing to start a duplicate."""
    # A SUBSYSTEM STOPPED AT THE MANAGER RUNG STAYS STOPPED -- HERE TOO (order 4c1eaa9df7fa).
    # The keeper had this gate and this function did not, so the cycle body simply restarted
    # whatever the keeper had just refused to restart. Asked before the duplicate check because
    # the answer does not depend on it: a closed subsystem must not be launched whether or not
    # a copy happens to be up.
    _held, _why = _manager_stopped(name, args)
    if _held:
        log(f"  {name}: STOPPED at MANAGER rung — not started ({_why})")
        return "manager-stopped"
    # Matched on BASENAME. The stage is invoked with an absolute path while an already-running
    # copy may have been started with a relative one, so a substring test on the full path never
    # matches and the guard passes when it should not. That is how a second roll got launched
    # against a live one, which is precisely the failure this supervisor exists to prevent.
    #
    # AND A BLIND PROBE IS NOT AN ABSENCE (order 1d556b6ef535). `running()` answers None when it
    # could not read the process table; starting on that is how one unreadable table turns the
    # whole standing set into duplicates. Distinct status so the cycle's summary line does not
    # claim the stage was found already up.
    _up = running(os.path.basename(args[0]))
    if _up is None:
        _blind("run:" + name, f"  {name}: cannot read the process table, so NOT starting it")
        return "probe-blind"
    if _up:
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
            # Written by `_guarded_popen` under the spawn lock, not here, for the reason given
            # in start() below (order e038910102b4): a separator written before the
            # authoritative check is a "session started" line for a session that may not start.
            def _banner():
                fh.write(chr(10) + "=" * 28 + " %s session %s " % (
                    name, datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
                    + "=" * 28 + chr(10))
                fh.flush()

            p = _guarded_popen(name, args, fh, banner=_banner)
            if p is None:
                return "already-running"
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

    AND THE SAME MANAGER-RUNG GATE AS run() (order 4c1eaa9df7fa). Every standing start at the top
    of the cycle comes through here, as do prose, the roll and the foreman's four repairs, and
    none of them asked the stop ledger -- so the keeper's refusal to restart a stopped subsystem
    was undone by the next lap of the supervisor that owns the keeper. Returns None when the
    subsystem is closed, which every caller already treats as "did not start".
    """
    held, why = _manager_stopped(name, args)
    if held:
        log(f"  {name}: STOPPED at MANAGER rung — not started ({why})")
        return None
    # A BLIND PROBE IS NOT AN ABSENCE (order 1d556b6ef535). Returns None, which every caller
    # already treats as "did not start" -- the same shape the manager-rung gate above uses.
    _up = running(os.path.basename(args[0]))
    if _up is None:
        _blind("start:" + name, f"  {name}: cannot read the process table, so NOT starting it")
        return None
    if _up:
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
    #
    # AND WRITTEN ONLY IF A SPAWN ACTUALLY HAPPENS (order e038910102b4). The separator used to
    # be written here, before `_guarded_popen`'s locked second check -- so the keeper thread and
    # the cycle's own standing starts, which race for these same job names by design, could both
    # stamp "started" into one job's log for a single real process start. The double spawn was
    # already prevented; only the evidence was wrong, which is the part an incident is
    # reconstructed from later. Handing the write to `_guarded_popen` as a callback puts it
    # inside the same lock as the decision it is claiming to record.
    fh = open(lf, "a", encoding="utf-8")

    def _banner():
        stamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        fh.write(f"\n{'=' * 78}\n=== {name} started {stamp} (pid pending)\n{'=' * 78}\n")
        fh.flush()

    p = _guarded_popen(name, args, fh, banner=_banner)
    if p is None:
        with contextlib.suppress(Exception):
            fh.close()
        return None
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
        # CONTENT LABELS, NOT LINE NUMBERS, here and at the four sites below. These five keys
        # read "overnight.py:203", ":229", ":253", ":124" and ":141" -- line numbers from a
        # version of this file that has not existed for two refactors, pointing at code that
        # has nothing to do with the swallow they name. The label IS the key `state/failures.json`
        # aggregates on and the one `ledger_report()` prints every cycle, so a reader chasing a
        # specific swallowed failure was sent to the wrong lines; the same drift BUGS m5 fixed in
        # wiki_source and m81 in dashboard. Descriptive keys survive the next refactor.
        silence.note("overnight.py:foreman-report-read")
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


def watch_report():
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
        silence.note("overnight.py:watch-report-read")
        return
    open_f = [v for v in (d.get("findings") or {}).values() if v.get("state") == "open"]
    if not open_f:
        log(f"  overwatch: round {d.get('rounds', 0)}, nothing open")
        return
    hi = [f for f in open_f if (f.get("severity") or "").lower() == "high"]
    log(f"  overwatch: {len(open_f)} finding(s) open ({len(hi)} high) after "
        f"{d.get('rounds', 0)} round(s):")
    # ALL of them, high severity first -- the `[:top]` slice this used to end on was the
    # identical defect `did[:5]` was removed for above: the header announces a count and the
    # list then delivers fewer. The sort key here also used to compare severity
    # case-SENSITIVELY three lines under a count that lowers it first, so a finding the model
    # stored as "High" (overwatch.py does not normalise what it writes) was counted into the
    # "(N high)" headline and simultaneously sorted as not-high -- reachable by construction,
    # never triggered yet because every stored severity today happens to already be lowercase.
    # One fix for both: stop capping, and sort on the same lowered value the count uses.
    for f in sorted(open_f, key=lambda x: -((x.get("severity") or "").lower() == "high")):
        log(f"    {f.get('module','?')}.py {f.get('symbol','')}: {f.get('actual','')[:96]}")


def ledger_report():
    """What the swallowed failures were this cycle.

    Every `except` in src/ now records its class before continuing (see silence.py). This is
    where that pays: 5,590 identical HTTPErrors show up as one loud line instead of as 5,590
    entities that look like they honestly have no page.

    ALL OF THE CLASSES, RANKED -- the trailing slice and the `top` parameter that fed it are
    gone (order 16bba34c2e68). This is the THIRD instance of the same cut removed from this one
    file, after the one in foreman_report and the one in watch_report, and it sat in the
    function whose entire product IS the ranked list: 47 distinct classes and 2,197 occurrences
    on the night it was measured, of which 39 classes were named nowhere. Nothing in the old
    header said so, because the two numbers it printed were the OCCURRENCE total and
    `len(rows)` -- neither of them the class count. Both quantities are now named. No caller
    ever passed `top` (main() calls this bare), and the list is bounded by the number of
    distinct `silence.note` tags in src/, on a per-cycle report, so there is no volume argument
    for a cut.
    """
    path = os.path.join(HERE, "state", "failures.json")
    try:
        with open(path, encoding="utf-8") as f:
            d = json.load(f)
    except Exception:
        silence.note("overnight.py:ledger-report-read")
        return
    if not d:
        return
    rows = sorted(d.items(), key=lambda kv: -kv[1])
    log(f"  swallowed failures: {len(rows):,} class(es), "
        f"{sum(d.values()):,} occurrence(s), ranked:")
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
    # `--run` selects the default behaviour and exists to make this command line identifiable:
    # `lognames.OWNER[PIPELINE]` matches the fragment `pipeline.py --run`, so a hand-run
    # `pipeline.py --status` no longer answers for the daemon. See order 08c1fd3932a4.
    ("pipeline", [os.path.join(SRC, "pipeline.py"), "--run"], LN.PIPELINE),
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
    # A DELIBERATE EXIT, AND THE ONE THE SUPERVISOR MOST NEEDS TO READ CORRECTLY. `codewatch`
    # exits a long-lived job when `src/` has changed under it, because a Python process is a
    # photograph of the code it started with and there is no other way to pick up an edit. This
    # project's longest outage came from a watcher reading jobs-exiting-on-purpose as
    # jobs-crashing, so it is named here, next to the codes it must never be confused with.
    if rc == 17:
        return "rc=17 (ON PURPOSE — source changed, restarting to run the current code)"
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
    """This cycle's coverage figures, or `{"error": ...}` if they were not MEASURED this cycle.

    THE RETURN CODE USED TO BE DISCARDED, AND A STALE FILE READ EXACTLY LIKE A FRESH ONE
    (order a37032c3f36a). `subprocess.run(...)` was called for its side effect and the previous
    `data/COVERAGE.json` was then loaded unconditionally -- so a `coverage.py` that crashed, was
    refused its own atomic write (`coverage.main` returns 1 when `replace_retry` denies the
    landing), or died on an internal fault left LAST cycle's numbers on disk, the load succeeded,
    no "error" key was set, and main() logged them as this cycle's measurement, wrote them into
    STATUS.md as a fresh row and appended them to history[] as a datum. Only the timeout and the
    unreadable-file paths ever reached the except.

    Run #19 fixed how a CRASHED snapshot is REPORTED; this is the same species one level up -- a
    snapshot that failed while still looking perfectly measured, in the module whose docstring
    rule 5 is MEASURE EVERY CYCLE. Both halves of the check are needed and they catch different
    faults: a nonzero rc is coverage.py saying so itself, and an unmoved mtime catches the case
    where it exits 0 without landing a new file at all. `t0` is taken BEFORE the spawn so the
    comparison cannot be beaten by the run's own duration.
    """
    t0 = time.time()
    cov = os.path.join(HERE, "data", "COVERAGE.json")
    try:
        r = subprocess.run([PY, os.path.join(SRC, "coverage.py")], cwd=HERE,
                           capture_output=True, text=True, timeout=1800,
                           env=dict(os.environ, PYTHONIOENCODING="utf-8"), creationflags=_NO_WIN)
        if r.returncode != 0:
            silence.note("overnight.py:coverage-snapshot-rc")
            return {"error": "coverage.py %s -- COVERAGE.json on disk is the PREVIOUS run's"
                             % name_rc(r.returncode)}
        # A file older than the run that was supposed to write it was not written by it. One
        # second of slack because filesystem timestamps and time.time() need not agree to the
        # microsecond, and the failure this catches is a whole cycle stale, not a whole second.
        if os.path.getmtime(cov) < t0 - 1:
            silence.note("overnight.py:coverage-snapshot-stale")
            return {"error": "coverage.py exited clean but data/COVERAGE.json was not "
                             "rewritten -- these would be the PREVIOUS run's numbers"}
        rows = json.load(open(cov, encoding="utf-8"))
    except Exception as e:
        silence.note("overnight.py:coverage-snapshot")
        return {"error": f"{type(e).__name__} {str(e)[:60]}"}
    n = sum(r["entries"] for r in rows)
    cited = sum(r["cited"] for r in rows)
    read = sum(r["read"] for r in rows)
    return {"entries": n, "cited": cited, "read": read, "feats": sum(r["feats"] for r in rows),
            "cited_pct": round(100 * cited / max(n, 1), 2),
            "settled_pct": round(100 * (cited + read) / max(n, 1), 2)}


def preflight():
    """Returns (n_failing_checks, blocking). Only corrupted source blocks."""
    try:
        r = subprocess.run([PY, os.path.join(SRC, "health.py"), "--preflight"], cwd=HERE,
                           capture_output=True, text=True, timeout=1800,
                           env=dict(os.environ, PYTHONIOENCODING="utf-8"), creationflags=_NO_WIN)
        out = r.stdout
    except Exception as e:
        silence.note("overnight.py:preflight")
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
    fails = [ln.strip() for ln in out.splitlines() if ln.strip().startswith("FAIL")]
    for ln in fails:
        log(f"    preflight {ln}")
    # THE BLOCKING CONDITION WAS TWO HAND-TYPED SUBSTRINGS OF ANOTHER MODULE'S CONSOLE OUTPUT
    # (order 001c0be3e3ad). It read
    #     blocking = "control characters in source" in out and "FAIL  control" in out
    # -- the label is `health.CHECKS[0][0]` and the two-space "  FAIL  {label}" is health.py's
    # print format (health.py:840), and NOTHING pinned either. Reword the check and `blocking`
    # becomes False for ever, silently, while the supervisor spends the night doing exactly
    # what the branch's own log line says it exists to prevent: "producing confident
    # emptiness". `allsweep.py` carries the structurally identical cross-module string in
    # `_HALT_REFUSAL` and it IS pinned by verify_math, "so the two cannot drift into
    # disagreement silently"; the same discipline was absent here, on the harder-to-notice of
    # the two. Taking the label FROM health deletes the copy rather than pinning it.
    #
    # The first conjunct was also dead weight: health prints the label on the PASS line too
    # ("  ok    control characters in source"), so it was true on every clean preflight and the
    # whole gate rested on the second term. A reader saw a two-condition guard and there was
    # one. There is one now, and it is the real one.
    try:
        import health as _health
        _control_label = _health.CHECKS[0][0]
    except Exception:
        # A health.py that cannot even be imported is a bigger problem than this gate, and the
        # subprocess above would already have failed -- but the gate must not evaporate on the
        # way. Fall back to the literal and record that the pin did not hold.
        silence.note("overnight.py:preflight-label")
        _control_label = "control characters in source"
    blocking = ("FAIL  " + _control_label) in out
    if _control_label not in out:
        # Neither the ok line nor the FAIL line for the one blocking check: health did not get
        # that far, or the label moved under us. Either way `blocking` is not an answer, and
        # saying so out loud is the entire point of pinning it.
        log(f"  preflight: the blocking check '{_control_label}' did not report at all "
            f"-- the halt gate had nothing to read this cycle")
    # `n` COUNTS FAILING CHECKS, NOT THE SUBSTRING (same order). `out.count("FAIL")` counted
    # the word anywhere in stdout, including inside the indented "{what}: {detail}" lines a
    # check emits, so a finding whose own text contained the word inflated the total. It was
    # also a THIRD quantity for the same thing: `health.preflight` counts one per FINDING
    # (problems += len(found)) and returns that, this counts one per failing CHECK. `len(fails)`
    # is the honest name for what is visible from here, and main()'s log line now says which
    # quantity it is printing.
    n = len(fails)
    # AND A PREFLIGHT THAT DIED MID-RUN IS NOT A PREFLIGHT THAT PASSED (order 6761a8e56280).
    # The except arm above -- run #19's "it no longer passes for a pass" -- only covers a
    # health.py that could not be LAUNCHED or that timed out. One that STARTS and then dies
    # returns here normally: nonzero rc, its traceback on the stderr nothing reads, and a
    # PARTIAL stdout. `n` is then 0 and `blocking` is False, so main() takes neither the halt
    # branch nor the "N problem(s) noted" branch and the cycle proceeds indistinguishably from
    # a clean run. health.py's contract is `return 1 if n else 0` (health.py:780), so a
    # nonzero rc is not itself a fault -- but a code outside {0,1}, or rc=1 with NO FAIL line
    # in the stdout it is supposed to have printed, CONTRADICTS that contract, and that
    # contradiction is exactly the crash signature. Reported in the launch-failure path's own
    # words, and deliberately non-blocking for the same reason it gives: a preflight that
    # cannot run must not stop the cycle, it must stop being mistaken for one that ran.
    if r.returncode not in (0, 1) or (r.returncode == 1 and not fails):
        silence.note("overnight.py:preflight-did-not-complete")
        log(f"  preflight: DID NOT COMPLETE ({name_rc(r.returncode)}, {len(fails)} FAIL line(s) "
            f"parsed) -- continuing, but this cycle was NOT checked")
        err = (r.stderr or "").strip().splitlines()
        if err:
            log(f"    preflight last stderr line: {err[-1][:160]}")
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
    # AN EXIT CODE THIS FUNCTION CANNOT NAME IS NOT "NOT BREACHED" (order b66a8b1acf50). The
    # only branch here was `== 1`, so drill.py exiting 2 (argparse refusing its own arguments),
    # or on a Windows NTSTATUS, or on any other nonzero code, logged the summary line -- or
    # "produced no summary line" -- and the cycle went on to start every stage. This is the park
    # inspection that runs before anything else on every cycle, and `name_rc` exists in this very
    # file precisely because an unrecognised exit code is a bug rather than weather. Same
    # wording as the except arm above, because it is the same fact: the nets were not inspected.
    if r.returncode not in (0, 1):
        silence.note("overnight.py:drill-did-not-complete")
        log(f"  safety drill: DID NOT COMPLETE ({name_rc(r.returncode)}) "
            f"-- the nets were NOT inspected this cycle")
        err = (r.stderr or "").strip().splitlines()
        if err:
            log(f"    safety drill last stderr line: {err[-1][:160]}")
    if r.returncode == 1:
        for x in (r.stdout or "").splitlines():
            if x.strip().startswith("BREACHED"):
                log("    " + x.strip())
        log("  A SAFETY NET DID NOT HOLD — the library has halted itself. "
            "Clear it with: python src/escalation.py --clear --ruling \"...\"")
    return r.returncode


STATUS_CYCLES_SHOWN = 12


def write_status(cycle, history):
    """Land STATUS.md. -> True if it landed, False if the replace was denied.

    BUILT WHOLE, THEN LANDED ATOMICALLY (order 3fdf445e7c0d). This was `open(STATUS.md, "w")`
    followed by twenty sequential `f.write()` calls -- the m6 truncate-then-serialise pattern
    this project retired repo-wide -- on a file `publish.py` copies verbatim into the PUBLIC
    repo and `estate.py` hashes. An exception part-way through (an unencodable value in a
    history row, a full disk, a kill) left a half-written STATUS.md on disk and published it,
    and there was no verdict for the caller to gate on in a module that gates every verdict it
    can see. Same temp-name-plus-`replace_retry` idiom as `silence.write_json` and
    `build_terminal.py`, and the denial is REPORTED rather than swallowed: a status page that
    silently stopped updating is a status page that lies by standing still.
    """
    p = os.path.join(HERE, "STATUS.md")
    cur = history[-1] if history else {}
    first = history[0] if history else {}
    out = []
    out.append("# Overnight run\n\n")
    out.append(f"Last update: {datetime.datetime.now():%Y-%m-%d %H:%M:%S}  ")
    out.append(f"(cycle {cycle})\n\n")
    out.append("## Citation coverage\n\n")
    out.append("| | now | at start | change |\n|---|---:|---:|---:|\n")
    for k, label in (("cited", "entries cited"), ("read", "read, no feat"),
                     ("feats", "feats on record"),
                     ("cited_pct", "cited %"), ("settled_pct", "settled %")):
        a, b = cur.get(k, 0), first.get(k, 0)
        out.append(f"| {label} | {a:,} | {b:,} | {a - b:+,} |\n")
    # AND THE WINDOW SAYS IT IS A WINDOW. `history[-12:]` printed the last twelve rows under a
    # heading that read as the whole run, which is Hard Rule 0's shape -- a smaller universe
    # wearing the same shape as the real one. `coverage.report()` is the model: announce the
    # slice and the count it was taken from, so the reader knows what is not on the page.
    shown = history[-STATUS_CYCLES_SHOWN:]
    if len(shown) < len(history):
        out.append(f"\n## Cycles\n\nShowing the last {len(shown)} of {len(history)} cycles this "
                   f"run; the {len(history) - len(shown)} earlier ones are in "
                   f"`state/overnight.log`.\n\n")
    else:
        out.append(f"\n## Cycles\n\nAll {len(history)} cycles this run.\n\n")
    out.append("| cycle | time | cited | settled % | feats |\n")
    out.append("|---|---|---:|---:|---:|\n")
    for h in shown:
        out.append(f"| {h.get('cycle','')} | {h.get('at','')} | {h.get('cited',0):,} | "
                   f"{h.get('settled_pct',0)} | {h.get('feats',0):,} |\n")
    out.append("\n## Logs\n\n`state/overnight.log` is the supervisor. Per-stage logs are\n")
    # NAMED FROM `lognames`, not typed out. This line is the pointer a person follows when
    # they want the evidence, and a renamed log would leave it pointing at nothing while
    # still reading like an instruction (order bc98d8655e26).
    out.append("`state/%s`, `state/%s`, `state/%s`.\n" % (LN.ROLL, LN.READ, LN.PIPELINE))

    import threading as _th
    tmp = "%s.%d.%d.tmp" % (p, os.getpid(), _th.get_ident())
    try:
        with open(tmp, "w", encoding="utf-8") as f:
            f.write("".join(out))
    except Exception as e:
        # The old code would have left the truncated file behind at exactly this point. Now the
        # damage is confined to a scratch file nobody publishes, and the previous good STATUS.md
        # is still the one on disk.
        silence.note("overnight.py:status-serialise")
        with contextlib.suppress(Exception):
            os.remove(tmp)
        log(f"  STATUS.md: NOT WRITTEN ({type(e).__name__}: {str(e)[:120]}) "
            f"-- the page on disk is the previous cycle's")
        return False
    landed = silence.replace_retry(tmp, p)
    if not landed:
        # `replace_retry` has already recorded the denial under its own key; this line is for
        # the person reading the night's log, who would otherwise see a status page frozen at
        # an earlier cycle with nothing anywhere saying why. The temp goes too -- `replace_retry`
        # records a denial and returns False, it does not unlink, and a uniquely-named leftover
        # per denied round accumulates (`silence.write_json` cleans up for the same reason).
        with contextlib.suppress(Exception):
            os.remove(tmp)
        log("  STATUS.md: WRITE DENIED -- the page still shows an earlier cycle; "
            "it lands next cycle")
    return landed


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
            "imported (%s), so the halt cannot be read. Hard Rule -1." % _esc_gone) from _esc_gone
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
    # AND AN UNREADABLE PROCESS TABLE MUST NOT AUTHORISE A SECOND ONE EITHER (order
    # 1d556b6ef535). This guard is the only thing standing between the machine and the twin
    # incident above, and it used to be satisfied by a probe that had merely gone blind. If we
    # cannot see whether a supervisor is up, the safe answer is to not become the second one:
    # the watchdog will try again, and a missing supervisor for one window is recoverable
    # where two duelling ones are not.
    _twin = running("overnight.py")
    if _twin is None:
        log("cannot read the process table, so cannot tell whether a supervisor is already "
            "running -- exiting rather than risking a twin")
        return 0
    if _twin:
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
    # `_manager_stopped` LIVES AT MODULE LEVEL NOW (order 4c1eaa9df7fa). It was defined here, as
    # a closure with this thread as its only caller, which is why the gate covered one of the ten
    # places this file launches jobs. It is asked here AND inside `start()`/`run()`; the keeper
    # keeps its own call so the refusal is logged as the keeper's decision and so the answer is
    # bound before the restart it gates, which is the property `drill.the_keeper_asks_before_
    # restarting` proves.
    import threading as _th

    def _keep():
        while True:
            time.sleep(300)
            for name, args, lf in STANDING:
                try:
                    # Checked silently first: start() logs "left alone" for a healthy job,
                    # and five of those every five minutes is log spam wearing a uniform.
                    #
                    # `is None` FIRST, because None is falsy and `not running(...)` read a
                    # blind probe as "down" (order 1d556b6ef535). This thread re-asserts the
                    # ENTIRE standing set every 300s, so one unreadable process table here
                    # doubles every standing job at once -- the widest blast radius the defect
                    # had. `_blind` throttles the concession to once an hour per job.
                    _up = running(os.path.basename(args[0]))
                    if _up is None:
                        _blind("keeper:" + name,
                               f"  keeper: cannot read the process table, so cannot tell "
                               f"whether {name} is down -- NOT restarting it")
                    elif not _up:
                        # A SUBSYSTEM STOPPED AT THE MANAGER RUNG STAYS STOPPED, and until
                        # 2026-08-26 it did not. At 22:5x a maintenance run stopped
                        # `catalogue_web --recatalogue` because it was NULLING SYNTHESIS BLOCKS
                        # -- 26 sources in 24 hours, including DC at 44,958 entries. At 23:21
                        # this keeper started it again. The stop lasted twenty-five minutes and
                        # no person was ever told.
                        #
                        # The escalation chain records that rung 4 fired. Nothing read it. So
                        # the chain had five rungs of which exactly ONE could actually stop
                        # anything -- the OWNER halt -- and a MANAGER stop was a note in a file
                        # that the supervisor whose whole job is keeping jobs up never opened.
                        # That is the "a decision recorded where nobody reads it" failure the
                        # roll's out-of-scope status had, arriving in the escalation chain
                        # itself.
                        held, why = _manager_stopped(name, args)
                        if held:
                            log(f"  keeper: {name} is STOPPED at MANAGER rung — "
                                f"NOT restarting ({why})")
                            continue
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
                "be imported (%s), so the halt cannot be read. Hard Rule -1." % _esc_gone) from _esc_gone
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
            log(f"  preflight: {n} failing check(s) noted, continuing "
                f"(checks, not findings -- health.py counts one per finding)")

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
        start("pipeline", [os.path.join(SRC, "pipeline.py"), "--run"], LN.PIPELINE)
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

        # 3. GPU: absorb the new feats into ceilings and per-entry judgements.
        #
        # THIS DOES NOT ORDER ANYTHING, AND THE COMMENT HERE USED TO SAY IT DID -- "Runs after
        # the reader so it sees the evidence the reader just produced". It cannot. `pipeline` is
        # a member of STANDING, it is started BACKGROUNDED at the top of this same cycle
        # (0c above), and the keeper re-asserts the whole standing set every 300s from wherever
        # this cycle happens to be blocked. So by the time the reader returns, hours later, a
        # copy has been running since before the reader began, and `run()`'s basename guard
        # returns "already-running" without doing any work. The only window in which this line
        # actually runs the stage is the <=300s gap between a standing copy exiting and the
        # keeper noticing.
        #
        # LEFT IN PLACE PENDING AN OWNER RULING (run #36, order 5d14e90b5043), because deleting
        # it is not neutral: its reliable "already-running" is what puts a job in `busy` below,
        # and `busy` is what stops a fast cycle being counted toward IDLE_LIMIT and halting the
        # supervisor. The choice is between the standing copy and the serial one; taking the
        # serial one out without answering that also re-arms the idle halt.
        statuses.append(run("pipeline", [os.path.join(SRC, "pipeline.py"), "--run"],
                            LN.PIPELINE, timeout_h=2))

        canon_backup_cycle()

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
        # AND NEITHER IS "manager-stopped" (order 4c1eaa9df7fa). A subsystem a person closed at
        # rung 4 returns instantly by DESIGN, and counting that as a dead cycle would let a
        # narrow, deliberate, one-subsystem stop halt the entire supervisor after three laps --
        # the exact "a fault in one area must never close the whole park" property rung 4 exists
        # to provide, defeated by the idle counter. Same reasoning the halt branch below already
        # applies to a halted library: a job exiting on purpose is not a job failing.
        # AND NEITHER IS "probe-blind" (order 1d556b6ef535). A stage that was skipped because
        # the process table could not be read has not failed; the INSTRUMENT has. Counting it
        # as a dead cycle would halt the supervisor after three laps of a transient WMI hiccup,
        # and nothing restarts it -- `autostart.supervisor_alive()` reads the same blind sensor
        # and correctly declines to act on it. Waiting and looking again is the whole remedy.
        busy = [x for x in statuses if x in ("already-running", "manager-stopped",
                                             "probe-blind")]
        if busy and snap["cycle_seconds"] < MIN_CYCLE_SECONDS:
            log(f"  {len(busy)} job(s) already running, stopped at the MANAGER rung, or "
                f"skipped on a blind process probe; "
                f"waiting {WAIT_SECONDS // 60}m before looking again")
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
