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
    it parses -- but only as a side effect: see _checks_pass and regex_touched. The standalone
        parse gate this line promises does not exist; an unparseable patch is caught by the
        import check below, after being written and then reverted
    it changes at most MAX_PATCH_LINES lines (the test is `> MAX`, so exactly MAX is allowed;
        this line used to say "fewer than", which is one line stricter than the code)
    `python -c "import <module>"` still succeeds
    `verify_math.py` still reports 0 failures
    `allsweep.py --quick` reports no broken module -- NOT "no *new* broken module": no
        pre-patch baseline is taken, so a module already broken for unrelated reasons refuses
        every patch until it is fixed

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
import silence
# Windows: a child process spawned from a windowless (pythonw) parent ALLOCATES ITS OWN
# CONSOLE unless told not to. Under the old console launcher every subprocess inherited a
# hidden console and nobody noticed; under pythonw each powershell/wmic/python child
# flashed a black window -- dozens per cycle across the stack. Passed on every spawn.
_NO_WIN = getattr(subprocess, "CREATE_NO_WINDOW", 0)

import sqlite3
import sys
# For the pid/thread-qualified scratch name in owner_queue(). FOR_OWNER.md is markdown, so it
# cannot go through `silence.write_json`, but it needs the same collision-proof temp name --
# see the comment there. (order 99b1ae2c580c)
import threading
import time

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(HERE, "src")
sys.path.insert(0, SRC)

_BAD_CHARS = (chr(8), chr(11), chr(12), chr(7))
if any(c in open(os.path.abspath(__file__), encoding="utf-8").read() for c in _BAD_CHARS):
    raise SystemExit(__file__ + ": a regex escape was eaten in transit.")

PY = sys.executable
ENV = dict(os.environ, PYTHONIOENCODING="utf-8")
LOG = os.path.join(HERE, "data", "FOREMAN.json")
FOR_OWNER = os.path.join(HERE, "FOR_OWNER.md")
BACKUPS = os.path.join(HERE, "state", "foreman_backups")

# The catalogue dispatch's rotation ledger, and the number that used to be a filter and is now
# only a RATE. See _catalogue_batch().
CATALOGUE_ATTEMPTS = os.path.join(HERE, "state", "CATALOGUE_ATTEMPTS.json")
CATALOGUE_SHORTFALL = 100

# Files a model may never edit. Each is either the thing that would have to be working to detect
# a bad patch, or the thing doing the patching.
#
# THE SECOND ROW WAS MISSING (order 881ff7f49438). The rule in the sentence above is the whole
# membership test, and five modules satisfied it while sitting outside the list: `drill` is the
# net battery Hard Rule -1 names as the PROVEN property ("a BREACHED net halts the library by
# itself"); `escalation` is the plant-wide interlock this file's own main() refuses to start
# without; `codewatch` is the rc=17 stale-code interlock; `liveness` is the check-that-cannot-
# fail detector; `overnight` is the supervisor that starts every job. And `_checks_pass` does
# not cover for the omission: it runs `import`, `verify_math` and `allsweep --quick`, and
# `--quick` skips only the VERIFY and ESTATE tiers (allsweep.py:702, :727) -- IMPORT and LINT
# still run unconditionally. `drill` IS among the modules `allsweep.modules()` walks (it is
# just a file under src/), so the IMPORT tier does smoke-check that drill.py still imports and
# its CLI still parses -- but that is import-level coverage only: it catches a deletion or a
# syntax break, not a weakened comparison inside a working net, which is the shape a model
# patch takes. verify_math's ~30 source-level assertions about drill.py and escalation.py catch
# the same shallow class of fault, for the same reason.
#
# Adding `python src/drill.py` to `_checks_pass` would close the rest of it and is NOT done
# here: verify_math.py:6051 (and again at :6283) records a standing rule that verify_math.py
# and drill.py "are not safe to run" concurrently from an agent context, and drill historically
# wrote trial values of `prose_enabled` into the live config. That is an owner ruling. This half
# needs none -- it only makes the list satisfy the rule it states.
DENYLIST = {"foreman", "silence", "health", "allsweep", "estate", "standards", "verify_math",
            "drill", "escalation", "codewatch", "liveness", "overnight"}
MAX_PATCH_LINES = 40


# Remedy timeouts are bounded WELL UNDER the loop interval. A remedy allowed 1800
# seconds inside a 20-minute round cannot finish in time by construction: it either
# overruns the schedule or is killed, and either way the round it belongs to is
# already stale when it returns. Long work belongs in a job the supervisor starts,
# not in a repair the foreman waits on.
def _run(args, timeout=900):
    return subprocess.run([PY, *args], capture_output=True, text=True, timeout=timeout,
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
    unreadable = []
    for db in (os.path.join(HERE, "state", "cascade_scratch.db"),
               os.path.join(os.path.expanduser("~"), "cascade", "data.db")):
        if not os.path.exists(db):
            continue
        try:
            c = sqlite3.connect(db)
            try:
                n += c.execute("update bucket_state set learned=NULL "
                               "where learned like '%\"rpm\": 1%' or learned like '%\"rpm\":1%'"
                               ).rowcount
                c.commit()
            finally:
                c.close()
        except Exception:
            silence.note("foreman.py:clear_learned_caps")
            unreadable.append(os.path.basename(db))
    if unreadable:
        # NOT the same sentence as the healthy zero. A db that could not even be opened is
        # not evidence there was nothing pinned -- it is evidence nobody looked.
        return False, (f"cleared {n} bucket(s) pinned at one request per minute; "
                        f"{len(unreadable)} database(s) could not be read ({', '.join(unreadable)}) "
                        "-- unknown whether they still hold stale caps")
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
        # Atomic, like _retire() below: cascade_bridge reads this file live inside `ask()` to
        # decide routing, and read.py and tuning.py read it on their own clocks -- a torn read
        # costs one of them a cycle, silently. (BUGS m18, 2026-08-24.)
        _pp = os.path.join(HERE, "data", "POOL_PROOF.json")
        # THROUGH `silence.write_json`, NOT A HAND-ROLLED `path + ".tmp"` (order a3fd659f4ff7).
        # The old scratch name was FIXED, so two foremen -- which this file deliberately allows,
        # the singleton claim being inside `if a.loop:` in main() -- opened the same temp and the
        # loser could land a half file over the target. `write_json`'s temp carries pid and
        # thread (silence.py:511), which is the collision the helper exists to make unavailable.
        # Same repair as the other six sites in this file (order 99b1ae2c580c).
        #
        # A DENIED RENAME HERE IS WORSE THAN A LOST WRITE, because of the line below it.
        # Clearing `_PROVEN[0]` forces the next `_alive()` to re-read POOL_PROOF.json from
        # disk -- so if the rename did not land, we have just thrown away the in-memory proof
        # AND pointed the router at the stale file, then told round_once we handled it (which
        # makes it `break` and skip the remedy for a whole cycle). Report the failure and keep
        # the cached proof rather than invalidating it in favour of something older.
        if not silence.write_json(_pp, rows, indent=1):
            return False, "pool re-proved but POOL_PROOF.json write was DENIED; routing still " \
                          "reads the previous proof"
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
    # EVERY CLASS, NOT THE FIRST THREE (order 842025c83c3c, Hard Rule 0).
    #
    # This named `[:3]` classes and then ARCHIVED AND CLEARED the live ledger in the same
    # breath -- so every class past the third was erased from state/failures.json having never
    # been named in the one log a person reads, and with no "and N more" the line read exactly
    # like a complete list. MEASURED on 2026-08-29: the ledger held 58 distinct classes over
    # 2,827 events, the top three were one URLError class and two HTTPError classes, and 55
    # names went to the archive unspoken. Among them were
    # `silent:compress_store.py:address-mismatch` x10 -- `compress_store.load()` refusing a blob
    # whose content hash does not match the address it is filed under, which is CORPUS
    # CORRUPTION -- and `silent:silence.py:stale-write-refused` x21. Neither would ever have
    # reached the log. The archive's three most recent snapshots hold 21, 24 and 56 classes, so
    # more than three is the normal case and not an outlier.
    #
    # This function's own siblings in this file already refuse the shape for the same reason:
    # `owner_queue()` ("EVERY url, not the first three ... A cap here is Hard Rule 0's exact
    # shape aimed at a human decision") and `_catalogue_batch`, which prints every deferred
    # source by name.
    #
    # Ranking is kept -- worst first is what makes the line readable, and Hard Rule 0 permits
    # ranking. The secondary sort on the class name makes the order a property of the ledger
    # rather than of dict insertion order, so two runs over the same ledger read the same.
    top = sorted(d.items(), key=lambda kv: (-kv[1], kv[0]))
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
        # Both atomic. state/failures.json is the highest-traffic shared file in the project --
        # the dashboard polls it, standards reads it, and EVERY process read-modify-writes it
        # through health.flush(). Truncating it with a bare open() is the one write here that
        # could lose another process's concurrent flush outright, not merely cost it a cycle.
        # (BUGS m18, 2026-08-24.)
        # AND THROUGH `silence.write_json`, whose temp name carries pid and thread. Both of
        # these were hand-rolled `path + ".tmp"` opens, which is a FIXED scratch name on the
        # file this very function calls "the highest-traffic shared file in the project" --
        # health.py:198-210 records the interleaved-writer corruption of `state/failures.json`
        # verbatim and was migrated to the helper for it; this writer of the same file was
        # not. Two foremen are allowed by design (the singleton claim is inside `if a.loop:`),
        # so this is foreman against foreman, not theory. (order 99b1ae2c580c)
        #
        # ARCHIVE FIRST, AND ONLY CLEAR IF THE ARCHIVE LANDED. These two writes are a move,
        # not two independent saves, and the order matters in both directions: clearing a
        # ledger whose archive was denied destroys the counts outright, while archiving without
        # clearing merely re-archives them next round. Neither return value was checked, so
        # both failures reported the same cheerful "swallowed and archived".
        if not silence.write_json(arch, prev, indent=1):
            return False, "failures archive write DENIED; ledger left INTACT rather than " \
                          "cleared into nothing"
        if not silence.write_json(path, {}, indent=1):
            return False, f"{total:,} archived, but clearing state/failures.json was DENIED; " \
                          f"the same batch will archive again next round"
    except Exception as e:
        # THE THIRD FALSE-SUCCESS PATH, missed when the other two were fixed (run #19).
        #
        # The comment above records that neither replace_retry return value was checked and that
        # both failures "reported the same cheerful 'swallowed and archived'". Those two got
        # honest returns; this handler did not, so it still fell through to the same cheerful
        # line for every OTHER failure -- a corrupt failures_archive.json raising JSONDecodeError
        # on the read at the top, a disk error on either open(). The ledger would be untouched
        # and the round would log that it had been archived and cleared. Same defect, same
        # function, one exit lower.
        silence.note("foreman.py:triage-archive")
        return False, (f"{total:,} swallowed, but the archive/clear FAILED "
                       f"({type(e).__name__}: {str(e)[:80]}); ledger left intact")
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
    if r.returncode != 0:
        # SAME SHAPE AS `adopt_hosts`'s "0 adopted" bug above: a nonzero exit is not "provider
        # lists refreshed" just because the stale-reference substring happened not to appear.
        # did=False, and the sentence says the run failed rather than echoing the success text.
        detail = tail[-1] if tail else (r.stderr or r.stdout or "").strip()[:150] or "no output"
        return False, f"catalogue_models.py exited {r.returncode}: {detail}"
    return True, (tail[-1] if tail else "provider lists refreshed")


def refresh_coverage():
    """Re-measure cited/settled. Stale figures understate the library and mislead every other
    standard that reads them."""
    r = _run([os.path.join(SRC, "coverage.py")], timeout=600)
    return r.returncode == 0, "coverage recomputed" if r.returncode == 0 else "coverage failed"


def _standing_cmds():
    """The keeper's STANDING roster as command-line strings, basename-first.

    ONE construction for both `_restartable` and `_restart_horizon`, which is the point: the two
    are called in the same breath by `kill_stalled_job` -- one to decide whether a kill is
    allowed, the other to say what it costs -- and they had built the comparison two different
    ways, one strict and one on loose substrings, so they could disagree about the same job.
    Deriving both from here means a change to the matching is a change to both answers.

    Raises rather than swallowing: the two callers want DIFFERENT failure behaviour (a refused
    kill versus an "UNKNOWN horizon" sentence), and each already has the handler that says so.
    """
    import overnight as _ON
    return [" ".join([os.path.basename(a[0]), *list(a[1:])]) for _n, a, _l in _ON.STANDING]


def _restartable(frag):
    """Will something bring this job back PROMPTLY if it is killed? (owner finding 2026-08-25)

    Derived from the keeper's STANDING set -- the same single roster m49 established as the one
    authority on which jobs are re-asserted, so this cannot drift into a second hand-kept list.
    A job in it returns within 300s. A job outside it waits for the supervisor's main lap, which
    has been measured at 42-44 minutes typically and four hours at worst.

    Used to REFUSE a kill rather than to caption one. `_restart_horizon` below already knew this
    distinction and only ever printed it; knowing a kill will cost four hours and doing it anyway
    is not a remedy, it is the breach of a different standard.
    """
    try:
        # THE SAME STRICT TEST `_restart_horizon` USES, from the same helper (order 9803b72711b3).
        #
        # This was `base in frag or frag in " ".join(args)` -- two loose substrings, in the
        # function that decides whether a job may be KILLED at all. That is the exact class
        # `restart_reader` above documents having fixed for itself ("anything whose command line
        # happened to contain both ... was a valid SIGTERM target"), and here it disagreed with
        # its own sibling: `_restartable` and `_restart_horizon` are called in the same breath by
        # `kill_stalled_job`, so one could authorise a kill while the other printed that nothing
        # restarts it. Measured against the live roster the two agreed on all six managed
        # fragments today -- it goes live the moment a second invocation of a STANDING script
        # enters lognames.OWNER (`pipeline.py --phase 4`), which would then read as restartable
        # and buy a kill costing "42-44 min typically and 4h at worst". Deriving both from
        # `_standing_cmds` is what stops them drifting apart again.
        for c in _standing_cmds():
            if c.startswith(frag):
                return True
    except Exception:
        silence.note("foreman.py:restartable")
        # FAIL CLOSED: if the roster cannot be read we cannot show the job comes back, and the
        # safe answer to "may I kill this?" when the answer is unknown is no.
        return False
    return False


def _restart_horizon(frag):
    """How long "the supervisor restarts it" actually means for THIS job. Say the true number.

    `frag` is the job's `lognames.OWNER` command-line fragment -- the same constant the killer
    already matches processes with -- NOT a log stem and not a display name. Keying off the one
    shared identifier is the point: a second, hand-kept name mapping is how this project got a
    nine-job tree reporting as four.

    Both killing remedies below used to end their note with the words "supervisor restarts next
    cycle". For a job in the keeper's STANDING set that is true and cheap -- the keeper re-asserts
    it every 300 seconds. For `read.py` and `feats.py --roll` it is badly false: they hang off the
    supervisor's hours-long MAIN LAP (`overnight.py`'s STANDING comment says so explicitly), so
    "next cycle" is a lap, not five minutes. Measured downtimes after a kill: 1, 8, 32, 37, 42 and
    44 minutes, and once four hours.

    That single misleading clause is why this cost went unnoticed for so long -- every kill
    reported itself as a five-minute inconvenience, in the one log a human actually reads. This
    changes NO behaviour; it only stops the remedy from understating its own price. Which of the
    three candidate real fixes to apply is the owner's ruling (M15 / NEXT_STEPS §2 B).

    STANDING is imported rather than copied: `overnight.py` keeps that roster module-level for
    exactly this reason, after three separate partial copies of it disagreed and made a nine-job
    tree report as four.
    """
    try:
        cmds = _standing_cmds()
    except Exception:
        silence.note("foreman.py:restart-horizon")
        return f"{frag}: restart horizon UNKNOWN -- could not read overnight.STANDING"
    if any(c.startswith(frag) for c in cmds):
        return f"{frag} is STANDING, so the keeper restarts it within 300s"
    return (f"{frag} is NOT in the keeper's STANDING set -- nothing restarts it until the "
            f"supervisor's next MAIN LAP, measured at 42-44 min typically and 4h at worst")


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
    # ONE CONTIGUOUS FRAGMENT, NOT TWO LOOSE SUBSTRINGS (run #19).
    #
    # This tested `"read.py" in line and "--run" in line` independently, so anything whose
    # command line happened to contain both -- a shell running a grep that mentions read.py, a
    # future `build_read.py --run-tests` -- was a valid SIGTERM target. `kill_stalled_job` below
    # documents having fixed exactly this loose-match class for its own matching and got the
    # remedy: `lognames.OWNER` publishes the one fragment that identifies each managed job,
    # precisely so the killer and the launcher cannot drift apart. This site was left behind.
    # The fragment is "read.py --run", which is how overnight.py:1425 actually launches it.
    import lognames as _LN
    frag = _LN.OWNER[_LN.READ]
    killed = []
    for line in out.splitlines():
        if frag in line:
            m = _re.search(r",(\d+)\s*$", line.strip())
            if m and int(m.group(1)) != os.getpid():
                try:
                    os.kill(int(m.group(1)), signal.SIGTERM)
                    killed.append(m.group(1))
                except Exception:
                    silence.note("foreman.py:restart_reader-kill")
    if killed:
        return True, ("bounced reader pid " + ", ".join(killed) + "; " + _restart_horizon(frag))
    return False, "reader is not running -- " + _restart_horizon(frag)


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
    if row is None:
        return False, ("the 'every running job is advancing' standard was not in the "
                        "report, so whether a job is stalled is UNKNOWN; nothing killed")
    if row.get("holds"):
        return True, "no job is stalled now"

    names = _re.findall(r"([A-Za-z0-9_]+) \(\d+ min", str(row.get("observed") or ""))
    if not names:
        return False, "stall reported but no job name parsed: " + str(row.get("observed"))[:80]

    # Resolve the reported job name to the command line that actually owns it. The stall
    # report names a LOG ("read_auto"), and matching that against a process command line found
    # nothing -- `read_auto` appears in no invocation, so this remedy could never kill anything
    # even once the standard was able to fire. Worse, the bare `job in line` test it used is
    # loose in the other direction too: a stem like "pipeline" matches any command line that
    # merely mentions it. lognames.OWNER carries the specific fragment for each managed job.
    import lognames as _LN
    owners = {fn[:-4]: frag for fn, frag in _LN.OWNER.items()}

    killed = []
    unrestartable = []        # stalled, but nothing would bring it back -- reported, not killed
    hit_frags = []            # the OWNER fragment of each job actually killed, for the horizon
    for job in names:
        frag = owners.get(job)
        if not frag:
            continue          # a job with no declared owner is not one this remedy may kill
        try:
            out = subprocess.run(
                ["wmic", "process", "where",
                 "name='python.exe' or name='pythonw.exe'", "get", "ProcessId,CommandLine", "/format:csv"],
                capture_output=True, text=True, timeout=40, creationflags=_NO_WIN).stdout
        except Exception:
            silence.note("foreman.py:kill_stalled-list")
            continue
        for line in out.splitlines():
            if frag in line and "python" in line:
                m = _re.search(r",(\d+)\s*$", line.strip())
                if not m:
                    continue
                pid = int(m.group(1))
                if pid == os.getpid():
                    continue
                # NEVER KILL WHAT YOU CANNOT RESTART (owner finding, 2026-08-25).
                #
                # This remedy exists to satisfy "every running job is advancing". For a STANDING
                # job that is a clean trade: the keeper has it back in 300s and a wedged unit is
                # lost. For a job OUTSIDE the standing set it is not a trade at all -- nothing
                # restarts it until the supervisor's next main lap, "42-44 min typically and 4h
                # at worst", and this function's own log line SAID SO while killing it anyway.
                #
                # Measured cost the day it was found: `read.py` was killed at 10:59 and stayed
                # dead. Every library counter -- cited, settled, feats, entries read -- was flat
                # for the whole window. So the remedy for one standard directly BREACHED another
                # ("the library's counters are moving"), which is standing lesson 10 exactly: a
                # guard failing by doing the thing it guards against.
                #
                # A stalled job that cannot be restarted is REPORTED, not killed. A stall costs
                # one wedged unit; an unrestartable kill costs hours of throughput, and the
                # second is strictly worse than the thing being remedied.
                if not _restartable(frag):
                    unrestartable.append("%s:%d" % (job, pid))
                    continue
                try:
                    os.kill(pid, signal.SIGTERM)
                    killed.append(job + ":" + str(pid))
                    hit_frags.append(frag)
                except Exception:
                    silence.note("foreman.py:kill_stalled-kill")
    spared = ""
    if unrestartable:
        # A stalled job nothing would restart is escalated, not silently left. SUPERVISOR rung:
        # it is one job's problem, not the library's, and it must not halt the park.
        spared = ("; SPARED (stalled but nothing restarts them, so killing costs more than the "
                  "stall): " + ", ".join(unrestartable))
        try:
            import escalation as _ESC
            _ESC.escalate(_ESC.SUPERVISOR, "STALLED_UNRESTARTABLE",
                          "stalled and deliberately NOT killed, because nothing would bring them "
                          "back promptly: " + ", ".join(unrestartable),
                          evidence={"jobs": unrestartable}, who="foreman.kill_stalled_job")
        except Exception:
            silence.note("foreman.py:kill_stalled-escalate")
    if killed:
        # Name the horizon PER JOB: this remedy can kill a STANDING job (pipeline, back in 300s)
        # and a main-lap job (read, roll) in the same breath, and one blanket clause cannot be
        # true of both. See _restart_horizon.
        horizons = "; ".join(sorted({_restart_horizon(f) for f in hit_frags}))
        return True, "killed stalled " + ", ".join(killed) + "; " + horizons + spared
    if unrestartable:
        return False, "no job killed" + spared
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

    seen, killed, unaged = {}, [], []
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
        # AN UNREADABLE CREATION TIME IS NOT A TIMESTAMP. The old fallback invented "9" * 14,
        # which sorts as the NEWEST possible process -- so an instance whose CreationDate field
        # WMIC garbled or omitted was always placed last and always SIGTERMed, even when it was
        # in fact the oldest and the one this function promises to keep. Guessing a timestamp in
        # order to decide which process to kill is the same species of error as `_checks_pass`
        # accepting "10 FAILED" (run #3): a destructive action taken on a value that was never
        # read. `None` is carried instead and the job is skipped below. 2026-08-24.
        seen.setdefault(job, []).append((started.group(1) if started else None, p))

    for job, procs in seen.items():
        if len(procs) < 2:
            continue
        if any(stamp is None for stamp, _ in procs):
            silence.note("foreman.py:dedup-unstamped")
            unaged.append(job)
            continue
        procs.sort()                       # oldest first
        for _stamp, p in procs[1:]:
            try:
                os.kill(p, signal.SIGTERM)
                killed.append(job + ":" + str(p))
            except Exception:
                silence.note("foreman.py:dupes-kill")
    note = ("; left alone (creation time unreadable, so no victim can be chosen): "
            + ", ".join(unaged)) if unaged else ""
    if killed:
        return True, "ended duplicate " + ", ".join(killed) + note
    if unaged:
        return True, "no duplicate ended" + note
    return True, "no duplicates found now"


def _fandom_reachable(timeout=8, _opener=None):
    """Is fandom.com actually ANSWERING right now?

    On 2026-08-23 the whole domain dropped our connections for a while (an IP block earned by a
    100-req/s catalogue pull). During such a window every fandom-facing job fails on every
    request while burning its retry budget and PROLONGING the block -- and this remedy, left
    ungated, would have re-dispatched the catalogue into it every round.

    A SOCKET IS NOT AN ANSWER. This used to open a TCP connection and call that reachable, and
    on 2026-08-24 -- mid-block -- that handshake succeeded INSTANTLY while a real API request to
    the same domain returned nothing after 21.3 seconds. The edge accepts the connection and
    drops the request. So this gate, written to defer work during exactly that kind of outage,
    was answering "reachable" for the whole of one and deferring nothing. Ask the API instead:
    it is the same one cheap call, and it tests the thing the caller actually depends on.

    AND THEN ASKING THE API INTRODUCED THE OPPOSITE ERROR, which is why the two fixes are
    recorded together. The rewrite above called `urlopen` on a bare URL, so the request went out
    as `Python-urllib/3.13` and MediaWiki answered **403 Forbidden in 0.13 seconds** -- from
    fandom AND from Wikipedia, healthy or not. This gate therefore returned False on every call
    it has ever made, and `run_catalogue_gap` deferred the catalogue every foreman round while
    reporting "fandom.com is dropping connections (IP block or outage)". A gate that always
    says "outage" is not conservative, it is off. Send the project's own polite UA, the one
    `wiki_source` has always sent: with it, the same two URLs return 200.

    THE HOST MATTERS AS MUCH AS THE HEADER. `community.fandom.com` is the only fandom host
    publishing AAAA records, so it answers over IPv6 while every A-record-only CONTENT wiki is
    dead at the socket -- which is exactly the state of this machine on 2026-08-24, and exactly
    what the `fandom answers this machine` standard missed for the same reason. Ask a content
    host (`standards.FANDOM_PROBE_HOST`), which is the path the catalogue actually uses. If that
    one host is individually down the gate defers a round it could have run: that is the safe
    direction, and it is the reason to prefer it over the host that cannot fail correctly.
    """
    try:
        import urllib.request
        import wiki_source as _ws
        import standards as _ST
        url = ("https://%s/api.php?action=query&meta=siteinfo&format=json"
               % _ST.FANDOM_PROBE_HOST)
        req = urllib.request.Request(url, headers=_ws.UA)
        with (_opener or urllib.request.urlopen)(req, timeout=timeout) as r:
            return r.status == 200
    except Exception:
        silence.note("foreman.py:fandom-unreachable")
        return False


def _catalogue_batch():
    """Which short sources this dispatch names, and which are waiting their turn.

    -> (batch, deferred, off_roll, unnameable, universe_size, fragments, measured), where
    `batch` and `deferred` are lists of (source name, gap), `batch` is what goes on the command
    line this round, `fragments` maps a source name to the comma-free `--only` needle for it,
    and `measured` is how many rows the completeness audit actually holds.

    `measured` exists so the caller can tell an EMPTY audit from a COMPLETE library (order
    9803b72711b3). Both produce `universe_size == 0`, and data/COMPLETENESS.json has genuinely
    been `[]` -- the comment in `run_completeness_audit` records the episode -- during which
    "no source is short" was printed off a measurement nobody had taken.

    HARD RULE 0, IN THE SHAPE THAT LOOKED LIKE A RATE. `run_catalogue_gap` dispatched
    `--shortfall 100`, and in `catalogue_web` that argument is a HARD FILTER, not a rate: it
    keeps every source short by 100 or more and DISCARDS the rest outright, with no cap and
    nothing rotating. Measured on the live audit the day this was fixed: 54 sources are
    reliably short and 19 of them clear 100, so **35 sources could never be dispatched at all**
    -- Fortnite short by 94, Tekken by 80, Naruto by 44, and on down. Not deferred, not queued,
    not slow: absent. And absent in the way Hard Rule 0 warns about, because the pass reported
    itself as a completed catalogue run every single time.

    It is the same non-rotating window the owner abolished in `scout.sweep(limit=4)` on
    2026-08-25, and it had the same self-sealing property: a source LEAVES the short list only
    when it is catalogued, so the sources at the head stayed at the head, were re-dispatched
    every round for ever, and nothing below the line ever moved up. The window could not
    rotate, because the only thing that would have moved a source out of it was the very work
    that was not being given to anything else.

    So the treatment is scout's, exactly: the universe is WHOLE (every source the audit says is
    short by one or more), the ordering is LAST-DISPATCHED FIRST with the gap as the tie-break
    among equally stale sources, and what is deferred is PRINTED BY NAME, because a window
    nobody can see the far side of reads exactly like a complete list.

    AND THE VOLUME IS LEFT WHERE IT IS, deliberately. `catalogue_web --recatalogue` is under an
    open BLOCKING order (3c7c8a6e9102) for nulling records' synthesis blocks, and this run is
    not the one to widen its dispatch. `CATALOGUE_SHORTFALL` therefore survives, but it now
    means "as many sources per dispatch as the old filter would have taken" -- a RATE, which is
    a cost decision -- instead of "which sources exist", which was never anybody's to decide.
    The count is derived from the same audit each round, so the rate tracks whatever the old
    behaviour would have done while the MEMBERSHIP rotates underneath it.

    STAMPED BEFORE THE WORK, not after, for scout's reason: a source whose dispatch dies must
    still count as attempted, or it sorts to the front again next round and pins the window the
    way the gap ordering did -- the same bug wearing the fix's clothes.
    """
    with open(os.path.join(HERE, "data", "COMPLETENESS.json"), encoding="utf-8") as f:
        comp = json.load(f)
    gap = {}
    for c in comp:
        if c.get("unreliable"):
            continue
        missing = (c.get("wiki_persons") or 0) - (c.get("catalogued_persons") or 0)
        if missing > 0:
            gap[str(c.get("source"))] = missing

    # A SOURCE THE AUDIT NAMES BUT THE ROLL DOES NOT can never be dispatched by any argument, so
    # it is separated out and reported rather than left to look like a source waiting its turn.
    import catalogue_web as CW
    roll = {str(r.get("name") or "").lower() for r in CW.load_roll()}
    off_roll = sorted(n for n in gap if n.lower() not in roll)
    for n in off_roll:
        gap.pop(n, None)

    # `catalogue_web --only` SPLITS ON COMMAS, so a source whose own name contains one cannot be
    # passed whole -- and two of them do ("Warhammer 40,000", "Gundam (all centuries, incl. G
    # Gundam)"). The longest comma-free prefix is used instead, and only if it identifies this
    # source and no other in the universe; `--only` is a substring match, so a fragment that hits
    # two sources would quietly WIDEN the dispatch, which is the one thing this change must not
    # do. A fragment that cannot be made unambiguous is reported by name every round rather than
    # silently dropped, because a source that can never be named is exactly the thing Hard Rule 0
    # is about.
    frags, unnameable = {}, []
    for n in gap:
        f = n.split(",")[0].strip().lower()
        if not f or sum(1 for m in gap if f in m.lower()) != 1:
            unnameable.append(n)
        else:
            frags[n] = f
    for n in unnameable:
        gap.pop(n, None)

    try:
        with open(CATALOGUE_ATTEMPTS, encoding="utf-8") as f:
            seen = json.load(f)
    except Exception:
        # An unreadable or absent ledger reads as "nothing has ever been attempted", which sends
        # everything to the front of one queue in a defined order. That costs a round of
        # re-ordering; it never costs a source its place.
        silence.note("foreman.py:catalogue-attempts")
        seen = {}
    order = sorted(gap, key=lambda s: (float(seen.get(s) or 0.0), -gap[s]))

    rate = sum(1 for s in gap if gap[s] >= CATALOGUE_SHORTFALL)
    rate = max(1, min(rate, len(order)))          # never zero, or a thin audit stalls for ever
    batch, rest = order[:rate], order[rate:]

    now = time.time()
    for s in batch:
        seen[s] = now
    seen = {k: v for k, v in seen.items() if k in gap}      # forget sources no longer short
    if not silence.write_json(CATALOGUE_ATTEMPTS, seen):
        # A LOST LEDGER IS A LOST ROTATION. Nothing is dispatched twice by it, but the same
        # batch sorts to the front again next round and the window stops turning -- silently,
        # which is the failure mode this whole function exists to end.
        silence.note("foreman.py:catalogue-attempts-denied")

    return ([(s, gap[s]) for s in batch], [(s, gap[s]) for s in rest],
            off_roll, unnameable, len(gap), frags, len(comp))


def run_catalogue_gap():
    """Catalogue coverage is short. Start the pass that closes it, now.

    THE POINT OF THIS ONE. Every other remedy here reacts to something broken. This reacts to
    something UNFINISHED, which the standards system previously had no way to express: the
    library knew it held 4.9% of its own sources' characters and that fact sat in a JSON file
    waiting for a person to notice. Work that is known to be outstanding should dispatch itself.

    WHICH sources it dispatches now rotates. See `_catalogue_batch()` -- the `--shortfall 100`
    this used to pass was a filter that permanently excluded 35 of the 54 short sources, and the
    volume is deliberately unchanged by the repair.
    """
    try:
        import overnight as ON
        import lognames as LN
        if ON.running("catalogue_web.py"):
            return True, "catalogue pass already running"
        if not _fandom_reachable():
            return False, ("fandom.com is dropping connections (IP block or outage); "
                           "catalogue deferred rather than dispatched into it")
        try:
            (batch, deferred, off_roll, unnameable, whole,
             frags, measured) = _catalogue_batch()
        except Exception as e:
            # FAIL CLOSED. Without a batch the only dispatch available is the old whole-universe
            # one, and widening this job's volume on a round where the audit could not be read
            # is precisely the thing the blocking order on `--recatalogue` forbids.
            silence.note("foreman.py:catalogue-batch")
            return False, ("could not choose a catalogue batch (%s: %s); nothing dispatched"
                           % (type(e).__name__, str(e)[:70]))
        if not batch:
            # AN UNMEASURED AUDIT IS NOT A FULL LIBRARY (order 9803b72711b3). This sentence read
            # "the completeness audit says no source is short" in both cases, and the case that
            # actually happened was data/COMPLETENESS.json == [] -- see run_completeness_audit's
            # comment -- where the audit says nothing at all. The remedy still returns False and
            # `run_completeness_audit` is marked `always`, so the re-measurement runs on this
            # same round either way; only the line a person reads was untrue.
            if not measured:
                return False, ("the completeness audit is EMPTY -- nothing has been measured, so "
                               "no source can be shown to be short; the re-measurement runs this "
                               "same round")
            return False, ("the completeness audit says no source is short (%d source(s) "
                           "measured); nothing to dispatch" % measured)

        # PRINTED BY NAME, all of it. These lines go to the foreman's operational log, which is
        # the log a person actually reads, and they are the difference between a rotation and a
        # truncation that happens to move.
        print("   AUTO   catalogue: %d of %d short source(s) this round, longest-waiting first: "
              % (len(batch), whole) + ", ".join("%s (short %d)" % (n, g) for n, g in batch))
        if deferred:
            print("   AUTO   catalogue: %d waiting for a later round, each moving to the front "
                  "by waiting: " % len(deferred)
                  + ", ".join("%s (short %d)" % (n, g) for n, g in deferred))
        if off_roll:
            print("   AUTO   catalogue: named by the audit but ABSENT FROM THE ROLL, so no "
                  "dispatch can reach them: " + ", ".join(off_roll))
        if unnameable:
            print("   AUTO   catalogue: cannot be named unambiguously on the command line, so "
                  "NOT dispatched this round: " + ", ".join(unnameable))

        # `--shortfall 1` keeps the universe whole on catalogue_web's side (every source short by
        # one or more) and leaves its largest-gap-first ranking intact; `--only` is what selects
        # this round's rotated membership. The two together also mean a fragment that somehow
        # matched a source with no gap still cannot be dispatched.
        ON.start("catalogue gap",
                 ["src/catalogue_web.py", "--recatalogue", "--shortfall", "1",
                  "--only", ",".join(frags[n] for n, _g in batch)],
                 LN.RECATALOGUE)
        return True, ("started catalogue_web on %d of %d short source(s); %d deferred to a "
                      "later round (named above)" % (len(batch), whole, len(deferred)))
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
        # NO LONGER GATED ON FANDOM (2026-08-24). The gate was right about the cost -- 8 probes
        # x 164 fandom sources at ~129s per failure is a ~47-minute round of pure failure against
        # a domain that has IP-banned this machine once already -- but wrong about the remedy,
        # and the cure was worse than the disease: COMPLETENESS.json had ALREADY been emptied to
        # `[]`, and gating the only thing that could rewrite it meant the file stayed empty for
        # as long as the block lasted, with a HIGH standard reading UNMEASURED off it the whole
        # time. A measurement that cannot be retaken is abandoned, not deferred.
        # `completeness.host_reachable()` now asks each DOMAIN once and emits an honest
        # `unreliable` row for its sources without probing them, so the expensive failure is
        # gone while the 46 sources on reachable hosts still get measured.
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
            silence.note("foreman.py:run_charter_regression-pool_proof")
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
RESTART_STAMP = os.path.join(HERE, "state", "OLLAMA_RESTARTS.json")


def restart_ollama():
    """Restart the local model service when tokens stop flowing. AUTO by owner ruling
    (2026-08-24, "FIX IT ALL"): the wedge cannot clear itself -- twice in one day the daemon
    answered /api/tags while zero generations completed, once with no runner process and once
    with a runner spinning at 98% completing nothing -- and both times the only cure was a
    restart a person had to perform. The restart is mechanical and reversible (the tray app
    respawns the daemon; the resident model reloads on first call), and it is rate-limited:
    at most one automated restart per 30 minutes, so a deeper fault escalates to the owner
    instead of being restart-looped into invisibility."""
    try:
        # FAIL CLOSED ON AN UNREADABLE STAMP (order f194d8444d12). This was a bare
        # `except Exception: st = {"count": 0, "last": 0}`, and `last=0` makes the 30-minute
        # test below False -- so a TORN or ZERO-BYTE stamp silently licensed another
        # `Stop-Process -Name ollama -Force`. That is precisely the end state the comment at
        # the write half of this function describes ("the guard failing open, silently"),
        # reached one exit up: run #19 hardened the WRITE and left the READ as it was.
        # Verified offline against this guard with nothing killed: a healthy 2-minute-old
        # stamp REFUSED, the same file torn or truncated PROCEEDED.
        #
        # A MISSING file is the one benign case -- genuinely the first restart -- and only it
        # is allowed to proceed. Anything else is unknown, and an unknown guard file answers
        # STOP (Hard Rule -1), because the alternative is restart-looping the daemon on the
        # one signal that would have stopped it. The fallback also reset `count` to 0, so the
        # "(automated restart #N)" figure -- the only thing distinguishing a one-off wedge
        # from a loop -- silently read 1 every time; refusing keeps the real count too.
        try:
            with open(RESTART_STAMP, encoding="utf-8") as f:
                st = json.load(f)
        except FileNotFoundError:
            st = {"count": 0, "last": 0}
        except Exception as _stamp_err:
            silence.note("foreman.py:ollama-stamp-unreadable")
            return False, ("the 30-minute restart stamp (%s) could not be read (%s) -- REFUSING "
                           "to restart ollama, because an unreadable rate limit is not an absent "
                           "one; repair or remove the file and the next round proceeds"
                           % (os.path.basename(RESTART_STAMP), type(_stamp_err).__name__))
        if time.time() - st.get("last", 0) < 1800:
            return False, ("restarted %.0f min ago and tokens still do not flow -- this is "
                           "deeper than a wedge; owner attention needed"
                           % ((time.time() - st.get("last", 0)) / 60))
        subprocess.run(["powershell", "-NoProfile", "-Command",
                        "Stop-Process -Name llama-server -Force -ErrorAction SilentlyContinue; "
                        "Stop-Process -Name ollama -Force -ErrorAction SilentlyContinue"],
                       capture_output=True, text=True, timeout=60, creationflags=_NO_WIN)
        _t0 = time.time()
        time.sleep(12)
        import urllib.request as _ur
        up = False
        for _ in range(6):
            try:
                _ur.urlopen("http://localhost:11434/api/tags", timeout=8)
                up = True
                break
            except Exception:
                time.sleep(5)
        st = {"count": st.get("count", 0) + 1, "last": time.time()}
        # This stamp IS the 30-minute rate limit that keeps this remedy from restarting Ollama
        # in a loop. A denied rename loses the stamp, so the next round reads no recent restart
        # and is free to kill the daemon again -- the guard failing open, silently. Checked and
        # recorded as of run #19; routed through `silence.write_json` (pid/thread-qualified
        # temp) as of order 99b1ae2c580c, since the fixed `.tmp` name was a second way for two
        # foremen to lose the same stamp.
        if not silence.write_json(RESTART_STAMP, st):
            silence.note("foreman.py:ollama-stamp-denied")
        if up:
            return True, ("ollama restarted (automated restart #%d); daemon answering, model "
                          "reloads on first call" % st["count"])
        return False, ("ollama killed but the tray did not respawn it within %.0fs -- owner needed"
                       % (time.time() - _t0))
    except Exception as e:
        silence.note("foreman.py:restart_ollama")
        return False, "restart failed: " + type(e).__name__ + " " + str(e)[:80]


REMEDIES = {
    # A stall is now ACTED ON rather than reported. This is the entry whose absence let a
    # catalogue run sit on its first source for 28 minutes while the jobs standard read green.
    "every running job is advancing": [kill_stalled_job],
    # The wedge remedies. Both liveness standards route to the same cure, because both wedge
    # shapes (no runner; runner spinning, nothing completing) have the same one.
    "the local model produces tokens": [restart_ollama],
    "the local model has a live runner": [restart_ollama],
    # Two supervisors is the worst duplicate of all: each starts the jobs the other is already
    # running, and the single-instance guards inside those jobs then fight. Keep the oldest,
    # which is the one holding the state, and end the rest.
    # Bare function, not a lambda wrapper: every log line in round_once prints `fn.__name__`,
    # and the wrapper made this one remedy report itself as "<lambda>" in the operational log
    # the project reads to find out what the foreman did. (2026-08-24.)
    "one instance of each job": [kill_duplicate_jobs],
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
    dotted = symbol.split("(")[0].strip()
    want = dotted.split(".")[-1]
    # HONOUR THE QUALIFIER WHEN THE FILE ACTUALLY HAS ONE. `symbol` may arrive qualified
    # (`ClassB.__init__`), and the bare `split(".")[-1]` threw the qualifier away, so two
    # same-named methods were indistinguishable and the MODEL lane -- which writes live source
    # unsupervised -- could land ClassB's patch on ClassA's body. `verify_math.py` alone holds
    # five `__init__`s. Resolved against the enclosing scope, so a match is exact; a qualifier
    # that names no scope in this file (`module.func`, the older convention) falls through to
    # the original bare-name search unchanged.
    if "." in dotted:
        qualified = {}

        def _scopes(node, prefix):
            for child in _ast.iter_child_nodes(node):
                if isinstance(child, (_ast.FunctionDef, _ast.AsyncFunctionDef, _ast.ClassDef)):
                    path = [*prefix, child.name]
                    qualified.setdefault(".".join(path), child)
                    _scopes(child, path)
                else:
                    _scopes(child, prefix)

        _scopes(tree, [])
        node = qualified.get(dotted)
        if isinstance(node, (_ast.FunctionDef, _ast.AsyncFunctionDef)):
            lines = src.splitlines(keepends=True)
            start = node.lineno - 1
            end = getattr(node, "end_lineno", node.lineno)
            return "".join(lines[start:end]), start, end
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
        silence.note("foreman.py:_literals")
        return out
    for node in ast.walk(tree):
        if isinstance(node, ast.Constant) and isinstance(node.value, str):
            out.append(node.value)
    return out


# Characters that make a string a PATTERN rather than a word. A changed literal containing any of
# these is a changed regex, whatever the code around it looks like.
_META = set(chr(92) + "^$.|?*+()[]{}")


def lines_changed(body, new):
    """How many lines a rewrite actually touches.

    NOT `abs(len(new) - len(old))`, which is what this gate used to measure while the module
    docstring sold it as bounding how much of a function a model rewrite may change. A rewrite
    that replaced every line of an 80-line function and landed on 82 lines scored 2 and passed
    a cap of 40 -- and the refusal message, when it did fire, reported that net figure as
    "patch changes N lines". Each non-equal opcode costs the LARGER of the two spans it spans:
    30 old lines replaced by 30 new ones is 30 changed, not 0, and 2 replaced by 40 is 40.
    """
    import difflib
    old_l, new_l = body.splitlines(), new.splitlines()
    return sum(max(i2 - i1, j2 - j1) for tag, i1, i2, j1, j2 in
               difflib.SequenceMatcher(None, old_l, new_l).get_opcodes() if tag != "equal")


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
    # READ THE NUMBER, DO NOT SUBSTRING IT. verify_math prints "RESULT: N passed, M FAILED",
    # and `"0 FAILED" in stdout` is satisfied by "10 FAILED", "20 FAILED", "100 FAILED" -- the
    # zero is just the last digit of M. This is the gate that decides whether a model-authored
    # patch to live source is KEPT or REVERTED, so the false positive kept exactly the patches
    # that broke a round number of checks. Same bug class as the `adopt_hosts` "0 adopted"
    # substring already fixed above; this instance had teeth. (Found by the ops audit and
    # reproduced against synthetic result lines, 2026-08-23.)
    import re as _re
    m = _re.search(r"RESULT:\s*\d+\s+passed,\s*(\d+)\s+FAILED", r.stdout or "")
    if not m:
        return False, "verify_math produced no readable result line"
    if m.group(1) != "0":
        return False, "verify_math no longer passes (%s failing)" % m.group(1)
    r = _run([os.path.join(SRC, "allsweep.py"), "--quick"], timeout=900)
    # READ THE EXIT CODE, NOT A TOKEN OUT OF THE CONSOLE.
    #
    # This tested `"BROKEN" in stdout`, and only ONE of allsweep's tiers prints that word. The
    # IMPORT tier prints `BROKEN <module>`; the LINT tier prints `UNDEFINED  <pyflakes line>`
    # and was invisible to this gate entirely. So the exact fault class LINT exists to catch --
    # an undefined name, which `import <module>` cannot see because the module imports fine and
    # only explodes when the function is called -- was ACCEPTED by the last gate standing
    # between a model-authored patch and live source. `wiki_source.py` is the recorded instance
    # of that fault reaching production: it imported clean, swept clean twice, and then failed
    # the moment the re-catalogue asked it to resolve DC.
    #
    # allsweep already publishes the right contract: `main()` returns `1 if bad else 0` where
    # `bad` sums every GRADED tier (imports, crashed/timed-out verifiers, lint, estate), and
    # deliberately leaves the ungraded reconcile rows out of it. Gating on that number is the
    # whole of the fix, and it also fails closed on the case the substring could never see at
    # all -- allsweep itself crashing, which produced no "BROKEN" and therefore read as a pass.
    #
    # Same family as the `local_agent` gate that tested `"0 FAILED" not in stdout` and duly
    # passed `10 FAILED`, and as `adopt_hosts` counting "0 adopted" as an adoption. A substring
    # standing in for a count is not a check; it is a check-shaped thing that cannot fail.
    if r.returncode != 0:
        graded = [ln.strip() for ln in (r.stdout or "").splitlines() if "graded:" in ln]
        # NOTE ON STRICTNESS, unchanged from run #19: no pre-patch baseline is taken, so this
        # is "no bad subsystem at all" rather than "no NEW bad subsystem". One module already
        # broken for unrelated reasons therefore refuses every patch until it is fixed. That is
        # deliberate -- loosening a safety that guards model-authored writes to live source is
        # not a change to make unasked -- but the message must not blame the patch for it.
        return False, ("allsweep --quick exits %s (a graded tier is bad: imports, lint, "
                       "verifiers or estate)%s -- NOTE: no pre-patch baseline is taken, so "
                       "this may pre-date the patch rather than be caused by it"
                       % (r.returncode, (" [" + graded[-1] + "]") if graded else ""))
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
    # LINES CHANGED, not the difference in line COUNT. This gate is the one the module
    # docstring sells as bounding how much of a function a model rewrite may touch, and it was
    # measuring `abs(len(new) - len(old))` -- a net total. A rewrite that replaced every line of
    # an 80-line function and happened to land on 82 lines scored `delta = 2` and passed a gate
    # meant to stop exactly that. The message said "patch changes 2 lines", which was false.
    # difflib is stdlib, so this costs nothing and finally measures the quantity it names.
    changed = lines_changed(body, new)
    if changed > MAX_PATCH_LINES:
        return {"ok": False, "why": f"patch changes {changed} lines; cap is {MAX_PATCH_LINES}"}
    if new.strip() == body.strip():
        return {"ok": False, "why": "no change proposed", "retire": True}
    if regex_touched(body, new):
        return {"ok": False, "why": "refused: the patch alters a regex literal"}
    if dry:
        return {"ok": True, "why": "would patch", "delta": changed, "preview": new[:400]}

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
        return {"ok": True, "why": "patched and verified", "delta": changed, "backup": backup}
    except Exception as e:
        silence.note("foreman.py:attempt_patch-apply")
        # "REVERTED" IS A CLAIM ABOUT THE FILE ON DISK, NOT ABOUT HAVING TRIED.
        #
        # Until run #26 this swallowed a failed restore and returned "reverted after X" anyway.
        # That is the worst place in the tree for an optimistic report: the file it could not
        # restore is LIVE SOURCE CODE with a model's unverified patch still in it, the round
        # prints a line saying the patch was rolled back, and the next thing to import that
        # module gets the patch. A gate that says it undid something it did not undo is worse
        # than no gate, because it stops anyone looking.
        try:
            shutil.copy2(backup, path)
        except Exception:
            silence.note("foreman.py:attempt_patch-revert")
            return {"ok": False, "reverted": False, "backup": backup,
                    "why": f"FAILED AFTER {type(e).__name__} AND THE REVERT ALSO FAILED -- "
                           f"{os.path.basename(path)} still holds the patch; restore it from "
                           f"{backup} by hand"}
        return {"ok": False, "reverted": True, "why": f"reverted after {type(e).__name__}"}


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
        # Atomic, and the read-modify-write held as tight as possible: overwatch owns this
        # file and persists after every module it reviews; a torn or stale write here would
        # silently discard its newest finding (2026-08-23 audit, finding 2).
        # CHECK THE RETURN THIS COMMENT ALREADY WARNS ABOUT (run #19). The paragraph above
        # names the exact hazard -- a torn or stale write here silently discards overwatch's
        # newest finding -- and then discarded the boolean that reports it. A denied rename
        # meant the finding was never actually retired and the standard it blocks stayed red
        # for reasons nobody could see. Same omission as triage_swallowed's, same file.
        # Through `silence.write_json` since order 99b1ae2c580c: the hand-rolled `path + ".tmp"`
        # was a fixed scratch name, and overwatch.py writes this same target with the safe
        # helper -- the collision this closes is foreman against a second foreman.
        if not silence.write_json(path, led, indent=1, sort_keys=True):
            silence.note("foreman.py:_retire-denied")
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
    # THE PAID-LANE SPEND REPORT WAS REMOVED 2026-08-25 with the lane itself (owner ruling:
    # "the paid lane should be erased from the code"). Nothing in this project can spend money
    # any more, so there is no running total to carry and nothing here for the owner to decide.
    # The old counter survives on disk under `state/`, unread, as the only record of what the
    # lane cost; `verify_math` §19h asserts this file cannot name it. See BUGS.md m100.

    # Material that EXISTS and declines automated readers. This is not a bug and not a gap in
    # the automation -- it is a storefront, and the correct answer to a storefront is a person
    # with an account, not a crawler in a costume. Surfaced with the URL so the decision is one
    # click away.
    try:
        with open(os.path.join(HERE, "data", "SCOUT_BLOCKED.json"), encoding="utf-8") as f:
            blocked = json.load(f)
    except Exception:
        silence.note("foreman.py:scout-blocked-read")
        blocked = {}
    if blocked:
        lines.append("### Material that exists but declines automated readers")
        lines.append("")
        lines.append("The scout found these and was refused. Mostly paid products. Nothing here "
                     "can be automated -- the library can only read them if you supply the text.")
        lines.append("")
        for src, urls in sorted(blocked.items()):
            lines.append(f"- **{src}**")
            # EVERY url, not the first three. This is the owner's decision document -- the file
            # whose whole purpose is "everything nobody but the owner can decide, in one place".
            # A cap here is Hard Rule 0's exact shape aimed at a human decision instead of a
            # catalogue: the owner reads three URLs, rules on what those three imply, and never
            # learns the fourth existed. Whether a source is genuinely unreachable or merely
            # blocked on the one mirror the scout happened to list first is precisely the
            # question the missing entries answer.
            for u in urls:
                lines.append(f"  - {u}")
        lines.append("")

    if len(lines) <= 6:
        lines.append("Nothing outstanding.")
    # Atomic, like every other shared write in this file (run #19 -- this was the one that
    # skipped it). FOR_OWNER.md is not private to the foreman: publish.py copies it into the
    # export tree on its own 10-minute loop, so a bare truncating open() can be read mid-write
    # and published as a half file. m18's reasoning, applied to the last writer that lacked it.
    # AND THE SCRATCH NAME CARRIES PID AND THREAD (order 99b1ae2c580c). `silence.write_json`
    # cannot be used here -- this file is MARKDOWN, not JSON -- but the hazard the helper was
    # written for is the temp NAME, not the format: a fixed `FOR_OWNER.md.tmp` is one file two
    # foremen open at once, and two foremen are allowed by design (the singleton claim in main()
    # sits inside `if a.loop:`). The loser's half-written owner queue then lands over the
    # winner's, and publish.py copies it into the export tree on its own clock. Same
    # `"%s.%d.%d.tmp"` shape as silence.py:511, inline rather than a new helper.
    _tmp = "%s.%d.%d.tmp" % (FOR_OWNER, os.getpid(), threading.get_ident())
    with open(_tmp, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
    if not silence.replace_retry(_tmp, FOR_OWNER):
        silence.note("foreman.py:for-owner-write")
        # A denied replace leaves the scratch file on disk, and a pid/thread-qualified name is
        # uniquely named per writer, so it accumulates rather than overwrites -- exactly the
        # litter `silence.write_json` learned to clean up after itself (silence.py:_discard_tmp).
        try:
            if os.path.exists(_tmp):
                os.remove(_tmp)
        except Exception:
            silence.note("foreman.py:for-owner-tmp-not-removed")
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
            log["model_pending"] = [*log.get("model_pending", []), o["standard"]]
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
        # RANKED, NOT TRUNCATED. `[:3]` here meant the fourth-ranked open finding was never
        # attempted -- not this round, not any round, because nothing rotated and the same three
        # stayed at the head while they stayed open. That is Hard Rule 0's shape exactly, and the
        # same shape the owner abolished in the sweep rotation on 2026-08-25: a cap that never
        # fails and always reads like a completed pass. Ranking survives (high severity first, so
        # the worst is attempted first if the round is cut short); the truncation does not.
        # Each attempt prints its own line below, so a long round announces itself rather than
        # going silent and looking wedged to `kill_stalled_job`. (run #26)
        _ranked = sorted(open_f, key=lambda x: -(x.get("severity") == "high"))
        for _i, f in enumerate(_ranked, 1):
            print(f"   MODEL  ({_i}/{len(_ranked)}) {f.get('module')}.{f.get('symbol')}",
                  flush=True)
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
        silence.note("foreman.py:round-log-read")
        prev = []
    prev.append(log)
    # Atomic: overnight.foreman_report() reads this every supervisor cycle, so this is two
    # long-running processes on one file. (BUGS m18, 2026-08-24.)
    # A denied rename here loses this whole round from the operational record, and
    # overnight.foreman_report() would then replay the PREVIOUS round as if it were this one --
    # i.e. report stale repairs as current. Checked and recorded as of run #19; through
    # `silence.write_json` since order 99b1ae2c580c, so the temp name cannot be shared with a
    # second foreman writing the same log.
    if not silence.write_json(LOG, prev[-200:], indent=1):
        silence.note("foreman.py:round-log-denied")
    return log


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
    ap = argparse.ArgumentParser(description="read the work orders and act on them")
    ap.add_argument("--go", action="store_true", help="actually run the remedies")
    ap.add_argument("--patch", action="store_true",
                    help="also let the model attempt code repairs (guarded, auto-reverting)")
    ap.add_argument("--loop", type=float, default=0, help="keep going, minutes apart")
    a = ap.parse_args()
    import codewatch
    # ONE OF ME. Two `publish.py` daemons were observed running seventeen seconds
    # apart on 2026-08-25 after a restart race, and two writers into one export repo
    # is the failure `push()` documents at length. Fails open: if the process table
    # cannot be read this starts anyway, because not being able to look is not a
    # reason to take the job down.
    # ONLY IN LOOP MODE, and this needed correcting within the minute: the guard was
    # unconditional at first and immediately refused a hand-run one-shot `--push`
    # because the standing daemon was up. A one-shot is not a second daemon; it is a
    # person doing one thing deliberately, and a safety that blocks the operator
    # from acting is a safety that will be removed.
    if a.loop:
        codewatch.claim_singleton("foreman")
        codewatch.stamp("foreman")
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
            silence.note("foreman.py:round-interrupted")
            raise
        except Exception as e:
            silence.note("foreman.py:round-raised")
            print("   ROUND FAILED: " + type(e).__name__ + ": " + str(e)[:200])
            print("   the loop continues; the next round re-reads the standards from scratch")
        if not a.loop:
            return 0
        # PICK UP CODE CHANGES. A running process is a photograph of the source as it was
        # when it started, and on 2026-08-25 a `publish.py --loop` daemon from 14:28 pushed
        # deliberately-corrupted files to a public repo because the guard written to stop it
        # at 19:00 was never in its memory. Exits with rc=17 on purpose; the keeper's STANDING
        # set restarts it within five minutes running the current code. Budgeted and settled,
        # so an edit storm cannot turn this into a respawn loop -- see codewatch.py.
        codewatch.exit_if_stale("foreman")
        time.sleep(a.loop * 60)


if __name__ == "__main__":
    sys.exit(main())
