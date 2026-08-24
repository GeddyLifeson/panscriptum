#!/usr/bin/env python3
"""
FOREMAN — reads the work orders and actually does something about them.

THE OWNER'S BRIEF
-----------------
    "shouldn't there be something developed that reads the work orders and sends them to either
     you or the ollama model for fixing? cause rn it's just giving the list but nothing is being
     done about it"

Correct, and it is the obvious next thing. `standards` measures against declared floors and emits
a work order; `overwatch` reads the source and reports defects of fact. Both produce excellent
lists that sit there. A list nobody acts on is a slightly more organised version of the problem
this project keeps having -- a number nobody was looking at.

THREE LANES, AND THE SORTING IS THE WHOLE DESIGN
------------------------------------------------
Not every breach can be fixed the same way, and pretending otherwise is how an automatic repairer
becomes a hazard.

  AUTO      A remedy that is mechanical, deterministic, and reversible. Clearing a mis-learned
            rate cap, re-proving which buckets answer, re-running host adoption, refreshing a
            stale coverage measurement. Every one of these I have run by hand today, more than
            once, with no judgement involved. They are scripted here exactly as performed.

  MODEL     A defect of fact in the source: the code does something other than what it says.
            This needs reading and reasoning, which is what a model is for -- and it needs
            guarding, which is most of the code below.

  OWNER     Anything requiring a decision that is not mine to make. "The free tiers are spent,
            add providers" is not a bug to be fixed, it is a choice about money and accounts.
            "This roster looks like another fiction" needs somebody to read the roster. These
            queue into a file rather than being acted on.

WHY THE MODEL LANE IS FENCED THIS HARD
--------------------------------------
A model editing a live codebase unsupervised is a bad idea, and the reasons are not hypothetical
in this project: the same defect class that produced eighteen silent faults would produce silent
patches. So a proposed patch must clear every one of these before it is kept:

    one file, and not one on the denylist
    it parses
    it changes fewer than MAX_PATCH_LINES lines
    `python -c "import <module>"` still succeeds
    `verify_math.py` still reports 0 failures
    `allsweep.py --quick` reports no new broken module

Anything that fails, reverts. The backup is written before the patch and restored on any failure,
including an exception in the checking itself. The bar is deliberately higher than a human's,
because a human explains a change and a model does not.
"""
import argparse
import ast
import json
import os
import shutil
import subprocess
# Windows: a child process spawned from a windowless (pythonw) parent ALLOCATES ITS OWN
# CONSOLE unless told not to. Under the old console launcher every subprocess inherited a
# hidden console and nobody noticed; under pythonw each powershell/wmic/python child
# flashed a black window -- dozens per cycle across the stack. Passed on every spawn.
_NO_WIN = getattr(subprocess, "CREATE_NO_WINDOW", 0)

import sqlite3
import sys
import time

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(HERE, "src")
sys.path.insert(0, SRC)
import silence                                                          # noqa: E402

_BAD_CHARS = (chr(8), chr(11), chr(12), chr(7))
if any(c in open(os.path.abspath(__file__), encoding="utf-8").read() for c in _BAD_CHARS):
    raise SystemExit(__file__ + ": a regex escape was eaten in transit.")

PY = sys.executable
ENV = dict(os.environ, PYTHONIOENCODING="utf-8")
LOG = os.path.join(HERE, "data", "FOREMAN.json")
FOR_OWNER = os.path.join(HERE, "FOR_OWNER.md")
BACKUPS = os.path.join(HERE, "state", "foreman_backups")

# Files a model may never edit. Each is either the thing that would have to be working to detect
# a bad patch, or the thing doing the patching.
DENYLIST = {"foreman", "silence", "health", "allsweep", "estate", "standards", "verify_math"}
MAX_PATCH_LINES = 40


# Remedy timeouts are bounded WELL UNDER the loop interval. A remedy allowed 1800
# seconds inside a 20-minute round cannot finish in time by construction: it either
# overruns the schedule or is killed, and either way the round it belongs to is
# already stale when it returns. Long work belongs in a job the supervisor starts,
# not in a repair the foreman waits on.
def _run(args, timeout=900):
    return subprocess.run([PY] + args, capture_output=True, text=True, timeout=timeout,
                          env=ENV, cwd=HERE, encoding="utf-8", errors="replace", creationflags=_NO_WIN)


# =========================================================================== the AUTO lane
#
# Each remedy returns (did_something, what_happened). They are written to be safe to run when
# they are not needed -- an idempotent remedy can be attempted on a hunch, and a destructive one
# cannot.

def clear_learned_caps():
    """Drop per-minute caps of 1, which are never real.

    A 429 arriving after a quiet minute teaches `rpm: 1`, and until the router was fixed nothing
    ever raised a learned cap again. Six buckets sat pinned that way -- both Geminis, Gemini
    Lite, both Groq models and zai -- against documented caps of 10, 10 and 15. The router now
    floors the learned value at 2 and expires it after six hours, so a fresh occurrence means
    something is generating 429 storms; this clears the damage either way.
    """
    n = 0
    for db in (os.path.join(HERE, "state", "cascade_scratch.db"),
               os.path.join(os.path.expanduser("~"), "cascade", "data.db")):
        if not os.path.exists(db):
            continue
        try:
            c = sqlite3.connect(db)
            n += c.execute("update bucket_state set learned=NULL "
                           "where learned like '%\"rpm\": 1%' or learned like '%\"rpm\":1%'"
                           ).rowcount
            c.commit()
        except Exception:
            silence.note("foreman.py:clear_learned_caps")
    return bool(n), f"cleared {n} bucket(s) pinned at one request per minute"


def reprove_pool():
    """Re-measure which buckets actually answer.

    Headroom is not evidence. Twenty-five of thirty-six buckets reported healthy quota while
    answering nothing, and each burned a full deadline every time it was claimed. This is the
    measurement that turns the pool's nominal width into its real one.
    """
    try:
        import cascade_bridge as CB
        rows = CB.prove()
        ok = [r for r in rows if r.get("verdict") == "answers"]
        with open(os.path.join(HERE, "data", "POOL_PROOF.json"), "w", encoding="utf-8") as f:
            json.dump(rows, f, indent=1)
        CB._PROVEN[0] = None                      # force the next _alive() to re-read
        return True, f"{len(ok)} of {len(rows)} buckets answer"
    except Exception as e:
        silence.note("foreman.py:reprove_pool")
        return False, f"{type(e).__name__}: {str(e)[:80]}"


def adopt_hosts():
    """Find a wiki for sources that have none. Entries with no host are uncitable forever."""
    r = _run([os.path.join(SRC, "hostcheck.py"), "--adopt", "--go", "--workers", "3"],
             timeout=600)
    # The summary line always says "N adopted", including N=0 -- and a substring match on
    # "adopted" reported that zero as a successful remedy. Only a non-zero count is an action.
    import re as _re
    m = None
    for ln in (r.stdout or "").splitlines():
        m = _re.match(r"([1-9]\d*) adopted", ln.strip()) or m
    return bool(m), (m.group(0) + " host(s)" if m else "nothing adopted")


def scout_hostless():
    """Ask the model where the sources with no host publish, and verify every answer.

    This was the last step that needed a person: knowing that KibblesTasty's material is at
    kthomebrew.com in the first place. `scout` asks the model and then PROVES each URL by
    fetching it and checking the page contains this source's own catalogued names -- a
    hallucinated URL 404s, a real URL about something else contains none of them. Nothing is
    registered on the model's say-so.
    """
    try:
        import scout as SC
        res = SC.sweep(limit=4)
        found = sum(1 for r in res if r.get("kept"))
        return bool(found), f"{found} of {len(res)} sources given somewhere to read from"
    except Exception as e:
        silence.note("foreman.py:scout_hostless")
        return False, f"{type(e).__name__}: {str(e)[:80]}"


def rerun_roll():
    """The page roll has not finished its pass. It is network-bound, so a stall is a host
    problem rather than a quota one -- and the supervisor restarts it next cycle anyway. This
    reports rather than acts, because two rolls at once is the failure the supervisor exists to
    prevent."""
    try:
        import overnight as ON
        if ON.running("feats.py"):
            return True, "roll is running; it will finish its pass"
    except Exception:
        silence.note("foreman.py:rerun_roll")
    return False, "roll is not running -- the supervisor starts it next cycle"


def triage_swallowed():
    """A spike in swallowed failures means something upstream is failing and being tolerated.

    The remedy is not to clear the ledger -- that would be deleting the evidence. It is to name
    the top classes, because the class names the module and the line, and a class that is 90% of
    the total is a single fault wearing thousands of hats.
    """
    path = os.path.join(HERE, "state", "failures.json")
    try:
        with open(path, encoding="utf-8") as f:
            d = json.load(f)
    except Exception:
        silence.note("foreman.py:triage_swallowed")
        return False, "no ledger"
    if not d:
        return False, "ledger empty"
    top = sorted(d.items(), key=lambda kv: -kv[1])[:3]
    total = sum(d.values())
    detail = "; ".join(f"{k} x{v:,}" for k, v in top)

    # ARCHIVE AFTER READING, because the ledger never forgets.
    #
    # It is cumulative, so a fault that was FIXED goes on counting forever and its standard stays
    # red for good -- 419 `phase_cosmology-ground` errors were still being counted an hour after
    # the call was corrected. A permanently red standard for a solved problem is indistinguishable
    # from one for an unsolved problem, and both get ignored at the same speed.
    #
    # Rolling it into a dated archive keeps every number and makes the live ledger mean "since
    # the last time anybody looked", which is what the standard is actually asking about.
    try:
        arch = os.path.join(HERE, "state", "failures_archive.json")
        prev = {}
        if os.path.exists(arch):
            with open(arch, encoding="utf-8") as f:
                prev = json.load(f)
        prev[time.strftime("%Y-%m-%d %H:%M")] = d
        with open(arch, "w", encoding="utf-8") as f:
            json.dump(prev, f, indent=1)
        with open(path, "w", encoding="utf-8") as f:
            json.dump({}, f)
    except Exception:
        silence.note("foreman.py:triage-archive")
    return True, f"{total:,} swallowed and archived, top: {detail}"


def recatalogue_models():
    """Re-ask every provider what it serves, so stale-ID findings cannot outlive their fix.

    The standard read a file written before the six stale model IDs were corrected, and went on
    reporting six for as long as nobody re-measured. Same shape as the failure ledger that never
    forgot: a measurement taken once becomes a permanent verdict, and the fix looks like it did
    not work.
    """
    r = _run([os.path.join(SRC, "catalogue_models.py")], timeout=900)
    tail = [ln for ln in (r.stdout or "").splitlines() if "stale model reference" in ln]
    return r.returncode == 0, (tail[-1] if tail else "provider lists refreshed")


def refresh_coverage():
    """Re-measure cited/settled. Stale figures understate the library and mislead every other
    standard that reads them."""
    r = _run([os.path.join(SRC, "coverage.py")], timeout=600)
    return r.returncode == 0, "coverage recomputed" if r.returncode == 0 else "coverage failed"


def restart_reader():
    """The reader is not progressing. Restarting is safe: every entity is cached only when it was
    fully read, so nothing is lost and nothing is re-read that was finished.

    This BOUNCES a running reader rather than declining to touch it. The 2026-08-23 idempotency
    review found both branches returned without acting -- a remedy named restart that never
    restarted -- and the counters-flat stall it serves is precisely the case where the reader
    is alive, logging failures, and doing nothing. Down-and-absent still defers to the
    supervisor, which is the only party allowed to start jobs."""
    import re as _re
    import signal
    try:
        out = subprocess.run(
            ["wmic", "process", "where", "name='python.exe' or name='pythonw.exe'",
             "get", "ProcessId,CommandLine", "/format:csv"],
            capture_output=True, text=True, timeout=40, creationflags=_NO_WIN).stdout
    except Exception:
        silence.note("foreman.py:restart_reader-list")
        return False, "could not enumerate processes"
    killed = []
    for line in out.splitlines():
        if "read.py" in line and "--run" in line:
            m = _re.search(r",(\d+)\s*$", line.strip())
            if m and int(m.group(1)) != os.getpid():
                try:
                    os.kill(int(m.group(1)), signal.SIGTERM)
                    killed.append(m.group(1))
                except Exception:
                    silence.note("foreman.py:restart_reader-kill")
    if killed:
        return True, "bounced reader pid " + ", ".join(killed) + "; supervisor restarts next cycle"
    return False, "reader is not running -- the supervisor starts it next cycle"


def kill_stalled_job():
    """A job that is UP and writing nothing is worse than a job that is down.

    Down, the supervisor restarts it next cycle. Up-and-idle, it holds the supervisor's
    single-instance lock forever and nothing ever restarts it -- so a stall is permanent by
    construction, and the liveness standard reports it as healthy the whole time.

    Every job here is resumable by design (the reader caches only fully-read entities, the
    catalogue writes per source, the assay writes per entity and defers rather than truncating),
    so killing a wedged one loses at most the unit it was stuck on. That is the unit it was
    never going to finish.
    """
    import re as _re
    import signal
    try:
        import standards as ST
        import dashboard as D
        rows = ST.check(D.state())
    except Exception:
        silence.note("foreman.py:kill_stalled-read")
        return False, "could not read the standards to learn which job stalled"

    row = next((r for r in rows if r["standard"] == "every running job is advancing"), None)
    if not row or row.get("holds"):
        return True, "no job is stalled now"

    names = _re.findall(r"([A-Za-z0-9_]+) \(\d+ min", str(row.get("observed") or ""))
    if not names:
        return False, "stall reported but no job name parsed: " + str(row.get("observed"))[:80]

    killed = []
    for job in names:
        try:
            out = subprocess.run(
                ["wmic", "process", "where",
                 "name='python.exe' or name='pythonw.exe'", "get", "ProcessId,CommandLine", "/format:csv"],
                capture_output=True, text=True, timeout=40, creationflags=_NO_WIN).stdout
        except Exception:
            silence.note("foreman.py:kill_stalled-list")
            continue
        for line in out.splitlines():
            if job in line and "python" in line:
                m = _re.search(r",(\d+)\s*$", line.strip())
                if not m:
                    continue
                pid = int(m.group(1))
                if pid == os.getpid():
                    continue
                try:
                    os.kill(pid, signal.SIGTERM)
                    killed.append(job + ":" + str(pid))
                except Exception:
                    silence.note("foreman.py:kill_stalled-kill")
    if killed:
        return True, "killed stalled " + ", ".join(killed) + "; supervisor restarts next cycle"
    return False, "stalled jobs found but no process matched: " + ", ".join(names)


def kill_duplicate_jobs():
    """Keep the OLDEST instance of each job and end the rest.

    Oldest rather than newest deliberately: the first instance is the one that acquired whatever
    state exists and has been writing it, and the duplicate is the accident. Killing the elder
    would throw away the work.
    """
    import re as _re
    import signal
    try:
        out = subprocess.run(
            ["wmic", "process", "where", "name='python.exe' or name='pythonw.exe'",
             "get", "ProcessId,CreationDate,CommandLine", "/format:csv"],
            capture_output=True, text=True, timeout=40, creationflags=_NO_WIN).stdout
    except Exception:
        silence.note("foreman.py:dupes-list")
        return False, "could not enumerate processes"

    seen, killed = {}, []
    for line in out.splitlines():
        m = _re.search(r"src[\\/](\w+)\.py", line)
        pid = _re.search(r",(\d+)\s*$", line.strip())
        started = _re.search(r",(\d{14})", line)
        if not (m and pid):
            continue
        job, p = m.group(1), int(pid.group(1))
        # The supervision chain is NEVER a valid duplicate target. Two watchdogs spawned two
        # supervisors spawned two foremen, and each foreman -- keeping "the oldest" of every
        # job -- shot the other stack's members on its first round. The stacks killed each
        # other every three minutes for half an hour; the watchdogs dutifully restarted them;
        # the user watched the corpses flash by as console windows. Duplicate SUPERVISORS are
        # the watchdog's own self-guard's problem; a repair tool that can kill its own
        # dispatcher is a repair tool that can dismantle the system it repairs.
        if job in ("overnight", "autostart"):
            continue
        if p == os.getpid() or job in DENYLIST:
            continue
        stamp = started.group(1) if started else "9" * 14
        seen.setdefault(job, []).append((stamp, p))

    for job, procs in seen.items():
        if len(procs) < 2:
            continue
        procs.sort()                       # oldest first
        for _stamp, p in procs[1:]:
            try:
                os.kill(p, signal.SIGTERM)
                killed.append(job + ":" + str(p))
            except Exception:
                silence.note("foreman.py:dupes-kill")
    if killed:
        return True, "ended duplicate " + ", ".join(killed)
    return True, "no duplicates found now"


def _fandom_reachable(timeout=8):
    """Can this machine currently open a socket to fandom.com at all?

    On 2026-08-23 the whole domain dropped our connections at the socket for a while (an IP
    block earned by a 100-req/s catalogue pull). During such a window every fandom-facing job
    fails on every request while burning its retry budget and PROLONGING the block -- and this
    remedy, left ungated, would have re-dispatched the catalogue into it every round.
    One cheap socket probe answers the only question that matters before starting hours of work.
    """
    import socket
    try:
        socket.create_connection(("community.fandom.com", 443), timeout=timeout).close()
        return True
    except OSError:
        return False


def run_catalogue_gap():
    """Catalogue coverage is short. Start the pass that closes it, now.

    THE POINT OF THIS ONE. Every other remedy here reacts to something broken. This reacts to
    something UNFINISHED, which the standards system previously had no way to express: the
    library knew it held 4.9% of its own sources' characters and that fact sat in a JSON file
    waiting for a person to notice. Work that is known to be outstanding should dispatch itself.
    """
    try:
        import overnight as ON
        if ON.running("catalogue_web.py"):
            return True, "catalogue pass already running"
        if not _fandom_reachable():
            return False, ("fandom.com is dropping connections (IP block or outage); "
                           "catalogue deferred rather than dispatched into it")
        ON.start("catalogue gap", ["src/catalogue_web.py", "--recatalogue", "--shortfall", "100"],
                 "recatalogue.log")
        return True, "started catalogue_web --recatalogue --shortfall 100"
    except Exception as e:
        silence.note("foreman.py:run_catalogue_gap")
        return False, "could not start the catalogue pass: " + str(e)[:90]


def run_character_sweep():
    """Rebuild CHARACTER_SWEEP.json so downstream stages see the re-catalogued cast."""
    try:
        import overnight as ON
        import lognames as LN
        if ON.running("sweep.py"):
            return True, "character sweep already running"
        ON.start("character sweep", ["src/sweep.py"], LN.SWEEP)
        return True, "started sweep.py"
    except Exception as e:
        silence.note("foreman.py:run_character_sweep")
        return False, "could not start the sweep: " + str(e)[:90]


def run_completeness_audit():
    """Re-measure the gap. Cheap (one API call per category) and needs no model at all.

    MARKED `always`: a measurement is not an alternative to a repair. Without the mark this sits
    second in the list behind run_catalogue_gap, which returns True, and never runs -- which is
    how the catalogue standard reported 0.4% coverage for Marvel while marvel.json held 30,207
    entries.
    """
    try:
        import overnight as ON
        if ON.running("completeness.py"):
            return True, "completeness audit already running"
        ON.start("completeness", ["src/completeness.py", "--workers", "6"], "completeness.log")
        return True, "started completeness.py"
    except Exception as e:
        silence.note("foreman.py:run_completeness_audit")
        return False, "could not start the completeness audit: " + str(e)[:90]


def run_charter_regression():
    """The daily instrument check: the charter's six published assays, end-to-end, live chain.

    Gated on the pool the way the catalogue is gated on fandom: dispatching six full assays
    into a starved pool produces six DEFERRED rows and a red standard that reads like drift
    when it is only the meter -- wait for buckets instead.
    """
    try:
        import overnight as ON
        import lognames as LN
        if ON.running("--calibrate"):
            return True, "charter regression already running"
        try:
            with open(os.path.join(HERE, "data", "POOL_PROOF.json"), encoding="utf-8") as f:
                answering = sum(1 for r in json.load(f)
                                if isinstance(r, dict) and r.get("verdict") == "answers")
        except Exception:
            answering = 0
        if answering < 3:
            return False, f"pool too thin for the regression ({answering} answering); waiting"
        ON.start("charter regression", ["src/magnitude.py", "--calibrate"], LN.CALIBRATE)
        return True, "started magnitude.py --calibrate"
    except Exception as e:
        silence.note("foreman.py:run_charter_regression")
        return False, "could not start the regression: " + str(e)[:90]


run_completeness_audit.always = True
refresh_coverage.always = True


# standard name -> remedies to try, in order. A standard with no entry falls to the OWNER lane,
# which is the right default: acting on a breach nobody scripted a remedy for is guessing.
REMEDIES = {
    # A stall is now ACTED ON rather than reported. This is the entry whose absence let a
    # catalogue run sit on its first source for 28 minutes while the jobs standard read green.
    "every running job is advancing": [kill_stalled_job],
    # Two supervisors is the worst duplicate of all: each starts the jobs the other is already
    # running, and the single-instance guards inside those jobs then fight. Keep the oldest,
    # which is the one holding the state, and end the rest.
    "one instance of each job": [lambda: kill_duplicate_jobs()],
    # Unfinished work dispatches itself. Coverage short -> start the pass; and re-measure, so
    # the next round is judged against what is true rather than against a stale audit.
    "every source is fully catalogued": [run_catalogue_gap, run_completeness_audit],
    "the character sweep is newer than the catalogue": [run_character_sweep],
    "the automation reproduces the charter": [run_charter_regression],
    "the library's counters are moving": [reprove_pool, restart_reader],
    "no bucket pinned at rpm 1": [clear_learned_caps],
    "calls that succeed": [clear_learned_caps, reprove_pool],
    "model calls per hour": [clear_learned_caps, reprove_pool],
    "buckets with headroom": [reprove_pool],
    "coverage figures are current": [refresh_coverage],
    "corpus read is progressing": [restart_reader],
    "sources with a reachable wiki": [adopt_hosts, scout_hostless],
    "page roll complete": [rerun_roll],
    "swallowed failures not spiking": [triage_swallowed],
    "unexpected swallowed failures": [triage_swallowed],
    "model IDs their providers still serve": [recatalogue_models],
    # Both of these are the throughput standard wearing a different name: a passage nobody
    # answered and a read that will not finish are what a starved pool looks like from the
    # reader's side. Same diagnosis, same remedies -- and routing them to the owner instead
    # would put a capacity problem in a file meant for decisions about money.
    "chunks nobody answered": [clear_learned_caps, reprove_pool],
    "corpus read finishes inside a day": [clear_learned_caps, reprove_pool],
}


# =========================================================================== the MODEL lane

PATCH_SYSTEM = """You are given one Python function and a specific claim that it does something
other than what it says. Return a corrected version of THAT FUNCTION ONLY.

Rules:
- Return the complete function, from its `def` line to its last line, and nothing else.
- Change as little as possible. If the claim is wrong, return the function UNCHANGED.
- Preserve every comment and docstring unless the claim is about one of them.
- Do not add imports, do not rename anything, do not reformat.
- Indentation must match the original exactly.

Return JSON only:
{"verdict": "fix"|"claim is wrong", "function": "<the complete function source>"}"""

PATCH_SCHEMA = {
    "type": "object",
    "properties": {"verdict": {"type": "string"}, "function": {"type": "string"}},
    "required": ["verdict", "function"],
}


def _function_source(path, symbol):
    """The source of one top-level function or method, with its line span."""
    import ast as _ast
    with open(path, encoding="utf-8") as f:
        src = f.read()
    tree = _ast.parse(src)
    want = symbol.split("(")[0].split(".")[-1].strip()
    for node in _ast.walk(tree):
        if isinstance(node, (_ast.FunctionDef, _ast.AsyncFunctionDef)) and node.name == want:
            lines = src.splitlines(keepends=True)
            start = node.lineno - 1
            end = getattr(node, "end_lineno", node.lineno)
            return "".join(lines[start:end]), start, end
    return None, None, None


def _literals(src):
    """Every string literal in a fragment of code."""
    out = []
    text = src if src.lstrip().startswith(("def ", "async def")) else None
    if text is None:
        pad = chr(10) + " "
        text = "def _wrapped():" + chr(10) + " " + src.replace(chr(10), pad)
    try:
        tree = ast.parse(text)
    except SyntaxError:
        # Only a PARSE failure is tolerable here, and it means the fragment is not valid Python
        # -- which the caller already refuses. Anything else must be seen: this function was
        # raising NameError because `ast` was never imported at module level, the bare `except`
        # swallowed it, and the gate reported "no literals changed" for every patch ever
        # examined. A safety check that fails open is worse than no safety check, and this one
        # failed open silently, inside the file written to stop exactly that.
        return out
    for node in ast.walk(tree):
        if isinstance(node, ast.Constant) and isinstance(node.value, str):
            out.append(node.value)
    return out


# Characters that make a string a PATTERN rather than a word. A changed literal containing any of
# these is a changed regex, whatever the code around it looks like.
_META = set(chr(92) + "^$.|?*+()[]{}")


def regex_touched(before, after):
    """Did this patch alter a pattern?

    THE FIRST PATCH THE MODEL EVER PROPOSED DID EXACTLY THIS. It rewrote

        re.sub(r"[^a-z0-9]+", ...)   ->   re.sub(r"[\\^a-z0-9]+", ...)

    turning "not alphanumeric" into "a caret, or a-z, or 0-9" -- the inverse of the intended
    class. It parses. It imports. `verify_math` does not touch that module, so it passes. Every
    gate built so far would have waved it through, and every name comparison in the library would
    have quietly inverted.

    This project has already lost six separate regexes to a single character, invisibly each
    time. A patch may fix logic; it may not become a different pattern on the way. If any literal
    containing metacharacters changed at all, the patch is refused -- a genuine regex fix is rare
    enough to be worth a human, and a wrong one is undetectable by everything else here.
    """
    b = sorted(x for x in _literals(before) if any(c in _META for c in x))
    a = sorted(x for x in _literals(after) if any(c in _META for c in x))
    return b != a


def _checks_pass(module):
    """Everything that must still be true after a patch.

    Deliberately more than "it parses". A patch that parses and breaks an import is exactly the
    kind of silent damage this project spends its life catching.
    """
    r = _run(["-c", f"import sys; sys.path.insert(0, r'{SRC}'); import {module}"], timeout=300)
    if r.returncode != 0:
        return False, "module no longer imports"
    r = _run([os.path.join(SRC, "verify_math.py")], timeout=1200)
    if "0 FAILED" not in (r.stdout or ""):
        return False, "verify_math no longer passes"
    r = _run([os.path.join(SRC, "allsweep.py"), "--quick"], timeout=900)
    if "BROKEN" in (r.stdout or ""):
        return False, "allsweep reports a broken module"
    return True, "checks pass"


def attempt_patch(finding, dry=True):
    """Have the model repair one finding, then prove the repair or revert it."""
    module = finding.get("module")
    symbol = finding.get("symbol") or ""
    if not module or module in DENYLIST:
        return {"ok": False, "why": f"{module} is on the denylist"}
    path = os.path.join(SRC, module + ".py")
    if not os.path.exists(path):
        return {"ok": False, "why": "no such module"}

    body, start, end = _function_source(path, symbol)
    if not body:
        # NOT EVERY FINDING POINTS AT PYTHON. `build_terminal.place` is JavaScript inside a
        # template string and `assay.SIGMA_MAX` is a module constant -- both are real code and
        # neither is a function this can replace. Retiring rather than refusing forever: an
        # unactionable finding that stays open is a permanent breach of the standard that reads
        # it, which trains everybody to ignore that standard.
        return {"ok": False, "why": f"{symbol} is not a Python function here", "retire": True}
    if len(body.splitlines()) > 400:
        return {"ok": False, "why": "function too large to patch safely"}

    prompt = (f"MODULE: {module}.py\nSYMBOL: {symbol}\n"
              f"CLAIM: the code {finding.get('actual', '')}\n"
              f"IT SAYS: {finding.get('claim', '')}\n\nFUNCTION:\n{body}")
    # LOCAL FIRST, AND THAT IS WHY THIS LANE NEVER RAN.
    #
    # It called `read._ask`, which goes to the cloud pool first -- so every patch attempt
    # competed with the corpus read, and the guard that stops it doing that (`_pool_has_room`)
    # was therefore true almost never. The lane was correct, fenced, and permanently asleep.
    #
    # The GPU is the right resource for this anyway. The reader now uses it only as a fallback,
    # so the card is idle most of the time; a code review is unmetered there, private, and
    # competes with nothing the library actually needs. The cloud is the fallback, not the
    # default -- exactly inverted from the reader, because their scarcities are opposite.
    got = None
    try:
        import read as R
        got = R._local(R.config(), PATCH_SYSTEM, prompt, PATCH_SCHEMA)
    except Exception:
        silence.note("foreman.py:attempt_patch-local")
    if got is None and _pool_has_room():
        try:
            import read as R
            R.ensure_transport(verbose=False)
            got = R._ask(R.config(), PATCH_SYSTEM, prompt, PATCH_SCHEMA)
        except Exception as e:
            silence.note("foreman.py:attempt_patch-ask")
            return {"ok": False, "why": f"model unreachable: {type(e).__name__}"}
    if got is None:
        return {"ok": False, "why": "GPU busy and no spare pool capacity; will retry"}
    if not got:
        return {"ok": False, "why": "no answer from the model"}
    if got.get("verdict") != "fix":
        return {"ok": False, "why": "model says the claim is wrong", "retire": True}

    new = (got.get("function") or "").rstrip() + "\n"
    if not new.lstrip().startswith("def ") and not new.lstrip().startswith("async def"):
        return {"ok": False, "why": "reply is not a function"}
    delta = abs(len(new.splitlines()) - len(body.splitlines()))
    if delta > MAX_PATCH_LINES:
        return {"ok": False, "why": f"patch changes {delta} lines; cap is {MAX_PATCH_LINES}"}
    if new.strip() == body.strip():
        return {"ok": False, "why": "no change proposed", "retire": True}
    if regex_touched(body, new):
        return {"ok": False, "why": "refused: the patch alters a regex literal"}
    if dry:
        return {"ok": True, "why": "would patch", "delta": delta, "preview": new[:400]}

    os.makedirs(BACKUPS, exist_ok=True)
    backup = os.path.join(BACKUPS, f"{module}.{int(time.time())}.py")
    shutil.copy2(path, backup)
    try:
        with open(path, encoding="utf-8") as f:
            lines = f.readlines()
        lines[start:end] = [new]
        with open(path, "w", encoding="utf-8") as f:
            f.writelines(lines)
        good, why = _checks_pass(module)
        if not good:
            shutil.copy2(backup, path)
            return {"ok": False, "why": f"reverted: {why}", "backup": backup}
        return {"ok": True, "why": "patched and verified", "delta": delta, "backup": backup}
    except Exception as e:
        silence.note("foreman.py:attempt_patch-apply")
        try:
            shutil.copy2(backup, path)
        except Exception:
            silence.note("foreman.py:attempt_patch-revert")
        return {"ok": False, "why": f"reverted after {type(e).__name__}"}


# =========================================================================== the round

def _retire(finding):
    """Close a finding the model lane can never act on, so it stops blocking its standard."""
    path = os.path.join(HERE, "data", "OVERWATCH.json")
    try:
        with open(path, encoding="utf-8") as f:
            led = json.load(f)
        for fid, v in (led.get("findings") or {}).items():
            if (v.get("module") == finding.get("module")
                    and v.get("symbol") == finding.get("symbol")
                    and v.get("state") == "open"):
                v["state"] = "retired"
                v["retired_why"] = finding.get("why", "unactionable")
        with open(path, "w", encoding="utf-8") as f:
            json.dump(led, f, indent=1, sort_keys=True)
    except Exception:
        silence.note("foreman.py:_retire")


def _pool_has_room(floor=600):
    """Is there spare provider capacity, or is the corpus read starving?

    Reading the library is the work. Repairing the code is what protects the work, and the
    watcher, the publisher and this all draw on the same few hundred calls an hour the free tiers
    allow. Four of my own processes competing for one thin pool is a self-inflicted outage, and
    the reader is the one that must not lose.

    A patch attempt costs several calls and the finding will still be there in half an hour.
    """
    try:
        import dashboard as D
        return (D.throughput(10) or {}).get("per_hour", 0) >= floor
    except Exception:
        silence.note("foreman.py:pool_has_room")
        return False


def owner_queue(items):
    """Everything nobody but the owner can decide, in one file they can read in ten seconds."""
    lines = ["# FOR THE OWNER", "",
             f"*Written by `src/foreman.py` — {time.strftime('%Y-%m-%d %H:%M')}*", "",
             "These need a decision, not a fix. Everything mechanical has already been done.",
             ""]
    for it in items:
        lines.append(f"### {it['standard']}")
        lines.append("")
        lines.append(f"- observed **{it['observed']}**, floor **{it['floor']}**")
        lines.append(f"- {it['order']}")
        lines.append("")
    # REAL MONEY REPORTS ITSELF. The paid burst lane counts every pin in PAID_BURST.json; the
    # owner turned it on and the owner should never have to open a JSON file to learn what it
    # has cost. The per-call estimate lives in the same file (est_usd_per_call) so correcting
    # it is a one-field edit, not a code change.
    try:
        with open(os.path.join(HERE, "state", "PAID_BURST.json"), encoding="utf-8") as f:
            pb = json.load(f)
        used, cap = pb.get("used", 0), pb.get("cap", 0)
        est = float(pb.get("est_usd_per_call", 0.02))
        lines.append("### The paid burst lane")
        lines.append("")
        lines.append(f"- {'ENABLED' if pb.get('enabled') else 'off'} — {used}/{cap} calls "
                     f"used, estimated **${used * est:.2f}** so far "
                     f"(at ~${est:.02f}/call; edit `est_usd_per_call` in "
                     "`state/PAID_BURST.json` if that rate is wrong)")
        if pb.get("enabled") and used >= cap:
            lines.append("- the cap is REACHED; the lane has closed itself. Raise `cap` or "
                         "set `enabled: false` to retire it.")
        lines.append("")
    except Exception:
        silence.note("foreman.py:paid-burst-report")

    # Material that EXISTS and declines automated readers. This is not a bug and not a gap in
    # the automation -- it is a storefront, and the correct answer to a storefront is a person
    # with an account, not a crawler in a costume. Surfaced with the URL so the decision is one
    # click away.
    try:
        with open(os.path.join(HERE, "data", "SCOUT_BLOCKED.json"), encoding="utf-8") as f:
            blocked = json.load(f)
    except Exception:
        blocked = {}
    if blocked:
        lines.append("### Material that exists but declines automated readers")
        lines.append("")
        lines.append("The scout found these and was refused. Mostly paid products. Nothing here "
                     "can be automated -- the library can only read them if you supply the text.")
        lines.append("")
        for src, urls in sorted(blocked.items()):
            lines.append(f"- **{src}**")
            for u in urls[:3]:
                lines.append(f"  - {u}")
        lines.append("")

    if len(lines) <= 6:
        lines.append("Nothing outstanding.")
    with open(FOR_OWNER, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
    return FOR_OWNER


def round_once(dry=True, patch=False):
    import standards as ST
    log = {"at": time.strftime("%Y-%m-%d %H:%M:%S"), "auto": [], "model": [], "owner": []}

    orders = ST.work_orders()
    print(f"{len(orders)} work order(s) open")

    # A code finding is not the owner's problem; it is the model lane's, by definition. Routing
    # it to the owner queue would put "some function does not do what it says" in a file meant
    # for decisions about money and accounts, and the two need different readers.
    MODEL_LANE = {"no high-severity findings open"}

    for o in orders:
        if o["standard"] in MODEL_LANE:
            log["model_pending"] = log.get("model_pending", []) + [o["standard"]]
            print(f"   MODEL  {o['standard']}: {o['observed']} open "
                  f"-> run with --patch to attempt repairs")
            continue
        remedies = REMEDIES.get(o["standard"])
        if not remedies:
            log["owner"].append(o["standard"])
            print(f"   OWNER  {o['standard']}: {o['observed']} (floor {o['floor']})")
            continue
        for fn in remedies:
            if dry:
                print(f"   AUTO   {o['standard']} -> would run {fn.__name__}")
                log["auto"].append({"standard": o["standard"], "remedy": fn.__name__,
                                    "dry": True})
                continue
            # A REMEDY MAY FAIL. IT MAY NOT TAKE THE FOREMAN WITH IT.
            #
            # `adopt_hosts` shells out to hostcheck with a 1800-second timeout, hit it, and
            # raised TimeoutExpired straight through round_once and out of the `while True` in
            # main(). The autonomous loop -- the thing whose entire purpose is to keep running
            # unattended -- was ended permanently by one slow subprocess, and the log recorded a
            # traceback rather than a work order.
            #
            # Every remedy is a repair attempt on a system already known to be faulty, so a
            # remedy raising is ORDINARY, not exceptional. It is recorded as a failed remedy and
            # the next one in the list is tried, which is exactly what the list is for.
            try:
                did, what = fn()
            except Exception as e:
                did, what = False, ("remedy raised " + type(e).__name__ + ": " + str(e)[:110])
                silence.note("foreman.py:remedy-raised")
            print(f"   AUTO   {o['standard']} -> {fn.__name__}: {what}")
            log["auto"].append({"standard": o["standard"], "remedy": fn.__name__,
                                "did": did, "result": what})
            # A REMEDY LIST IS USUALLY ALTERNATIVES, BUT NOT ALWAYS.
            #
            # `if did: break` treats every list as "try these until one works", which is right
            # for clear_learned_caps/reprove_pool -- two ways to fix one pool -- and WRONG for
            # a repair paired with a re-measurement. `every source is fully catalogued` runs
            # run_catalogue_gap then run_completeness_audit; the first returns True, the break
            # fires, and the audit never runs. So the catalogue pass did its job (Marvel went
            # from 401 entries to 30,207) while COMPLETENESS.json still reported 401, eighteen
            # hours stale, and the standard went on reporting 0.4% coverage forever.
            #
            # The repair worked and the instrument did not notice -- this project's own defect,
            # committed by the thing built to fix it. A remedy marked `always` runs regardless
            # of what came before, because measuring is not an alternative to repairing.
            if did and not getattr(fn, "always", False):
                remaining = [g for g in remedies[remedies.index(fn) + 1:]
                             if getattr(g, "always", False)]
                for g in remaining:
                    try:
                        d2, w2 = g()
                    except Exception as e:
                        d2, w2 = False, ("remedy raised " + type(e).__name__
                                         + ": " + str(e)[:110])
                        silence.note("foreman.py:always-raised")
                    print(f"   AUTO   {o['standard']} -> {g.__name__} (always): {w2}")
                    log["auto"].append({"standard": o["standard"], "remedy": g.__name__,
                                        "did": d2, "result": w2, "always": True})
                break

    if patch:
        try:
            led = json.load(open(os.path.join(HERE, "data", "OVERWATCH.json"), encoding="utf-8"))
            open_f = [f for f in (led.get("findings") or {}).values()
                      if f.get("state") == "open"]
        except Exception:
            silence.note("foreman.py:round-findings")
            open_f = []
        for f in sorted(open_f, key=lambda x: -(x.get("severity") == "high"))[:3]:
            res = attempt_patch(f, dry=dry)
            print(f"   MODEL  {f.get('module')}.{f.get('symbol')}: {res.get('why')}")
            log["model"].append({"module": f.get("module"), "symbol": f.get("symbol"), **res})
            if res.get("retire") and not dry:
                _retire(f)

    owner_items = [o for o in orders if o["standard"] in log["owner"]]
    p = owner_queue(owner_items)
    print(f"\n{len(owner_items)} for the owner -> {p}")

    try:
        prev = json.load(open(LOG, encoding="utf-8")) if os.path.exists(LOG) else []
    except Exception:
        prev = []
    prev.append(log)
    with open(LOG, "w", encoding="utf-8") as f:
        json.dump(prev[-200:], f, indent=1)
    return log


def main():
    ap = argparse.ArgumentParser(description="read the work orders and act on them")
    ap.add_argument("--go", action="store_true", help="actually run the remedies")
    ap.add_argument("--patch", action="store_true",
                    help="also let the model attempt code repairs (guarded, auto-reverting)")
    ap.add_argument("--loop", type=float, default=0, help="keep going, minutes apart")
    a = ap.parse_args()
    while True:
        print("=" * 88)
        print(f"FOREMAN  {time.strftime('%H:%M:%S')}" + ("" if a.go else "   (dry run)"))
        print("=" * 88)
        # The second layer, and it is not redundant with the per-remedy guard above. That one
        # covers remedies; this one covers everything else a round touches -- reading the
        # standards, the dashboard state, the overwatch ledger. A loop that can be ended by any
        # of those is not a loop, it is a single run with optimistic scheduling.
        try:
            round_once(dry=not a.go, patch=a.patch)
        except KeyboardInterrupt:
            raise
        except Exception as e:
            silence.note("foreman.py:round-raised")
            print("   ROUND FAILED: " + type(e).__name__ + ": " + str(e)[:200])
            print("   the loop continues; the next round re-reads the standards from scratch")
        if not a.loop:
            return 0
        time.sleep(a.loop * 60)


if __name__ == "__main__":
    sys.exit(main())
