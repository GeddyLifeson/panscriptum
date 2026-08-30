"""GPU LANE — one card, nine processes, and an order of precedence.

THE PROBLEM THIS EXISTS FOR, measured 2026-08-24. Nine standing Panscriptum jobs
(read, feats --roll, pipeline, foreman, overwatch, publish, dashboard, overnight, autostart)
all reach the same Ollama daemon on the same RTX 3080. Nothing coordinated them. Measured
consequences, all on the same trivial prompt needing ~50ms of compute:

    caught a free slot                     0.057 s
    queued behind the others              28.4 s, 34.6 s
    asking for a num_ctx not resident    240 s+, never completed

That last row is the expensive one and it is not merely slowness. Ollama serves a resident
model at ONE context size. A call asking for a different `num_ctx` needs the runner torn down
and rebuilt, and a rebuild cannot win against a queue that never drains -- so the whole library
was pinned to whatever context size happened to load first, and every attempt to raise it
timed out. Contention was not costing throughput, it was costing a CAPABILITY.

THE MODEL FOR THIS IS `motoko/discord_bot.py:256-298`, on this same machine and the same card,
which recorded the identical problem in its own words: "Her autonomous activities ran flat out
and saturated the GPU, so a Discord reply had to queue behind them: measured 96-149s with the
life loop running vs ~10s without." Its fix is a lock that serialises every model call plus an
event that background work waits on. That version is `asyncio` inside ONE process. Panscriptum
is nine SEPARATE processes, so the same idea has to land on the filesystem instead.

TWO RULES, and the second is the one that matters:

  * At most MAX_SLOTS model calls run at once, across every process. Everything else waits.
  * A BACKGROUND call yields to any live FOREGROUND claim. Prose generation and an owner's
    interactive run are foreground; the corpus read, the roll, the phases and the model lane
    are background. Background work is never cancelled -- it waits, then proceeds.

FAIL OPEN, ALWAYS. This module sits in front of every model call the library makes. A bug in
it must never be able to stop the library from working, so every failure path here PROCEEDS
rather than blocks: a corrupt claim file, a permissions error, a slot that cannot be created,
a wait that runs past its ceiling -- all of them end in "go ahead anyway". A lane that
deadlocks nine standing jobs would be far worse than no lane at all, and the whole point of
this project's silence discipline is that a quiet refusal is the most expensive kind.

STALENESS IS THE OTHER HALF OF FAIL-OPEN. Every claim and every slot carries a PID and a
heartbeat. A holder whose process is gone, or whose heartbeat has aged past its lease, is
broken by whoever notices. Otherwise one killed job would strand the card forever -- which is
precisely the failure this project has now hit twice with orphaned processes (m40, m42) and
once with a foreign one that pinned the daemon for two days (M5).
"""
import contextlib
import json
import os
import threading
import time

import silence                          # for replace_retry -- see _write_claim and _touch

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LANE = os.path.join(HERE, "state", "gpu_lane")

# How many model calls may be in flight at once, across every process. One card that serves
# one request at a time does not go faster when nine ask together -- it goes slower, because
# each waits behind the rest AND the daemon cannot rebuild a runner while the queue is full.
# Two rather than one: a single slot would serialise the whole library behind one slow call,
# and the daemon does overlap prompt evaluation with generation to a useful degree.
# ONE PHYSICAL FACT, READ RATHER THAN RESTATED: how many requests the card serves at once is
# `OLLAMA_NUM_PARALLEL`, the daemon's own setting. This was a bare "2" default, and `read.py`
# spelled the same number out a third time as GATE_LOCAL_N -- three constants for one fact with
# no link between them, so raising the daemon's parallelism silently left both gates on the old
# number. `PANSCRIPTUM_GPU_SLOTS` still wins when set, for pinning the two together deliberately.
DEFAULT_SLOTS = 2


def _slot_count():
    """MAX_SLOTS, parsed so that a bad environment cannot make this module unimportable.

    THE CRASH. This was one expression -- `max(1, int(PANSCRIPTUM_GPU_SLOTS or
    OLLAMA_NUM_PARALLEL or "2"))` -- with a bare `int()` at module scope, so any non-integer
    value raised at IMPORT:

        OLLAMA_NUM_PARALLEL=auto python -c "import gpu_lane"
            -> ValueError: invalid literal for int() with base 10: 'auto'

    which is the opposite of what the header mandates in capitals four screens up. An
    ImportError is not a failure path that PROCEEDS: it takes down every consumer of `lane()`
    in all nine standing jobs at once, strictly worse than the unarbitrated lane this module
    is already willing to accept when a claim file is corrupt.

    THE QUIETER HALF, and it mattered more because it did not announce itself. `0` is Ollama's
    own "let the server decide" setting, not a request for zero, and `max(1, 0)` read it as ONE
    slot -- silently serialising the whole library behind a single call, the exact outcome the
    comment above says two slots exist to avoid. An auto value is an ABSENT value here, so it
    falls through to the default rather than being clamped up to the minimum, which would
    invert its meaning. An explicit `PANSCRIPTUM_GPU_SLOTS=0` is refused the same way: there is
    no coherent zero-slot lane, and if an operator meant "unlimited" that is not this knob.

    Precedence is unchanged and deliberate: PANSCRIPTUM_GPU_SLOTS wins, for pinning the two
    settings together on purpose. Every rejection is recorded rather than absorbed, so a bad
    value is visible in the health ledger instead of showing up as mysterious throughput.
    (order b54fbcf84962)
    """
    for var in ("PANSCRIPTUM_GPU_SLOTS", "OLLAMA_NUM_PARALLEL"):
        raw = os.environ.get(var)
        if raw is None or str(raw).strip() == "":
            continue
        try:
            n = int(str(raw).strip())
        except (ValueError, TypeError):
            silence.note("gpu_lane.py:bad-slot-env")
            continue
        if n >= 1:
            return n
        # n <= 0: "auto" from the daemon, or nonsense from an operator. Either way this is not
        # a slot count, so the next source gets its turn and the default has the last word.
        silence.note("gpu_lane.py:bad-slot-env")
    return DEFAULT_SLOTS


MAX_SLOTS = _slot_count()

# A slot is a lease, not a lock. If the holder dies mid-call its slot must return to the pool
# without anyone intervening. Generous, because a real prose call legitimately runs for minutes
# -- the lease is a crash backstop, not a timeout, and the holder refreshes it as it works.
SLOT_LEASE_SECONDS = 900

# A foreground claim expires faster: it is held around a call, not for the life of a job, and
# an over-long claim starves exactly the background work the library depends on.
CLAIM_LEASE_SECONDS = 300

# The ceiling on how long a background call yields to foreground work before going anyway.
# Yielding forever is indistinguishable from a deadlock, and this project would rather have a
# slow correct run than a stalled one.
MAX_YIELD_SECONDS = 240

_POLL = 0.4

# Serialises this process's own read-modify-write of its foreground refcount. Cross-PROCESS
# safety comes from the claim file being named for the PID; this is the in-process half that
# was missing. See `foreground()`.
_DEPTH_LOCK = threading.Lock()


def _now():
    return time.time()


def _alive(pid):
    """Is this PID still running? A dead holder's lease is broken immediately.

    THE POSIX IDIOM IS WRONG ON THIS MACHINE and the first version of this module shipped with
    it. `os.kill(pid, 0)` against a nonexistent PID does not raise ESRCH on Windows -- measured
    2026-08-24, it raises `errno 22 (EINVAL), winerror 87`. Checking for ESRCH therefore
    answered "alive" for every dead process, so no lease was ever reclaimed: a ghost holder
    stranded a slot for its full 900-second lease and a ghost foreground claim stalled every
    background call for the whole 240-second yield ceiling. The concurrency tests caught it by
    hanging, which is the only reason it is not in the tree.

    So ask Windows directly. `OpenProcess` distinguishes the two cases the errno cannot:
    ERROR_INVALID_PARAMETER means no such process, ERROR_ACCESS_DENIED means a live process
    that is not ours. A handle that opens still has to be checked for exit status, because a
    terminated process keeps an openable handle until every reference is closed.

    Unknown answers are treated as ALIVE, deliberately. Guessing "dead" would let two callers
    into one slot, which is the stampede this module exists to prevent; guessing "alive" only
    costs a wait that the lease will end anyway.
    """
    if not pid:
        return False                     # no holder recorded at all -- an absence, not an unknown
    try:
        pid = int(pid)
    except Exception:
        # UNKNOWN, so ALIVE -- the policy in the docstring above (fixed run #19; this returned
        # False and so contradicted the paragraph three lines up, the exact comment-versus-code
        # shape behind this project's last four majors). An unparseable pid means a corrupt or
        # partially-written claim record, which is precisely an "unknown answer": guessing dead
        # breaks the lease and lets a second caller into an occupied slot, while guessing alive
        # costs at most one lease's wait, because `_expired` reclaims it on the timeout anyway.
        return True
    if pid == os.getpid():
        return True

    if os.name == "nt":
        try:
            import ctypes
            from ctypes import wintypes
            ERROR_INVALID_PARAMETER = 87
            ERROR_ACCESS_DENIED = 5
            STILL_ACTIVE = 259
            PROCESS_QUERY_LIMITED_INFORMATION = 0x1000
            k32 = ctypes.WinDLL("kernel32", use_last_error=True)
            h = k32.OpenProcess(PROCESS_QUERY_LIMITED_INFORMATION, False, pid)
            if not h:
                err = ctypes.get_last_error()
                if err == ERROR_INVALID_PARAMETER:
                    return False                 # no such process
                if err == ERROR_ACCESS_DENIED:
                    return True                  # exists, simply not ours to inspect
                return True                      # unknown: assume alive, per the rule above
            try:
                code = wintypes.DWORD()
                if k32.GetExitCodeProcess(h, ctypes.byref(code)):
                    return code.value == STILL_ACTIVE
                return True
            finally:
                k32.CloseHandle(h)
        except Exception:
            return True

    try:
        os.kill(pid, 0)
        return True
    except ProcessLookupError:
        return False
    except PermissionError:
        return True
    except Exception:
        return True


def _read(path):
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return None


def _expired(rec, lease):
    """A record nobody is maintaining any more."""
    if not isinstance(rec, dict):
        return True                      # unreadable/corrupt: reclaim rather than strand
    if _now() - float(rec.get("heartbeat") or 0) > lease:
        return True
    return not _alive(rec.get("pid"))


def _ensure_dir():
    try:
        os.makedirs(LANE, exist_ok=True)
        return True
    except Exception:
        return False


# --------------------------------------------------------------------------- foreground claims

def _claim_path(pid=None):
    return os.path.join(LANE, f"fg.{pid or os.getpid()}.json")


def foreground_active(ignore_pid=None):
    """Is any LIVE foreground claim outstanding?

    Sweeps dead claims as it goes -- the check and the cleanup are the same pass on purpose,
    because a separate reaper is one more thing that can be down when it is needed.
    """
    try:
        if not os.path.isdir(LANE):
            return False
        for name in os.listdir(LANE):
            if not name.startswith("fg.") or not name.endswith(".json"):
                continue
            path = os.path.join(LANE, name)
            rec = _read(path)
            if _expired(rec, CLAIM_LEASE_SECONDS):
                _remove_retry(path)      # m55: a release that silently fails strands the claim
                continue
            if ignore_pid is not None and int(rec.get("pid") or 0) == int(ignore_pid):
                continue
            return True
        return False
    except Exception:
        return False                     # fail open: unknown means "do not block anyone"


@contextlib.contextmanager
def foreground(label="foreground"):
    """Mark this process as doing work that background jobs should get out of the way for.

    Re-entrant by refcount, because a foreground call may nest inside another. motoko learned
    this the hard way with a plain boolean: the inner call's exit cleared the outer call's flag
    and the two deadlocked around each other.

    THE REFCOUNT IS READ-MODIFY-WRITTEN UNDER `_DEPTH_LOCK` (run #36, latent when found). The
    claim file is named for this PID, so no other PROCESS can race it -- but the increment and
    the decrement are each a read, an arithmetic step and a write, and two THREADS of this
    process entering `foreground()` together both read depth 0, both write 1, and the first
    exit deletes the claim while the second is still inside it. Every background call in the
    library then proceeds straight through the yield this module exists to enforce. Only
    single-threaded callers reach it today; the lock costs nothing and removes the question.
    It is held across the file write and released before the `yield`, never over it -- holding
    it over the body would serialise exactly the nesting the refcount exists to allow.
    """
    path = _claim_path()
    with _DEPTH_LOCK:
        rec = _read(path) or {}
        depth = int(rec.get("depth") or 0) + 1
        # THE ENTRY CLAIM IS THE ONE THAT MATTERS, so its verdict is checked (order
        # e7b6dcc8d630). If this write did not land there is no claim file, `foreground_active`
        # answers False for this process, and every background caller in the other eight
        # processes proceeds straight through the yield -- the exact pre-m54 state whose cost
        # this module's header measures as "240 s+, never completed". Never raised: `lane()`
        # enters this manager around the caller's model call and the work must happen either
        # way. Recorded, so a round that ran unarbitrated is distinguishable afterwards from a
        # round that was arbitrated and merely slow.
        if not _write_claim(path, depth, label):
            silence.note("gpu_lane.py:claim-write-denied")
    try:
        yield
    finally:
        with _DEPTH_LOCK:
            cur = _read(path) or {}
            d = int(cur.get("depth") or 1) - 1
            if d <= 0:
                _remove_retry(path)      # m55
            else:
                # THE DECREMENT IS THE SAFE DIRECTION and is deliberately not escalated: a
                # depth left too HIGH keeps this process's own claim standing a little longer
                # than the nesting warrants, which errs toward background work yielding to
                # foreground work rather than away from it, and CLAIM_LEASE_SECONDS collects it
                # regardless. The denial itself is already in the ledger from `_write_claim`.
                _write_claim(path, d, label)


def _write_claim(path, depth, label):
    """Land this process's foreground claim. -> True if the claim file now says `depth`.

    THE VERDICT IS RETURNED, not dropped (order e7b6dcc8d630). The paragraph below already
    argued that a dropped first write leaves the claim invisible and lets every background
    call walk through the yield this module exists to enforce -- and then discarded the one
    value that says whether that happened. `contextlib.suppress` covered the same ground for
    the dump, so BOTH halves of the failure were silent: from `foreground()` a claim that
    never appeared was indistinguishable from one held. The arbiter still fails open, which is
    correct -- the caller's work must proceed either way -- but failing open silently is what
    turns a degraded round into a permanently unexplained one.
    """
    if not _ensure_dir():
        return False
    try:
        tmp = path + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump({"pid": os.getpid(), "depth": depth, "label": label,
                       "heartbeat": _now()}, f)
        # replace_retry, not a bare os.replace (run #19). `_remove_retry` below cites the
        # Windows rename-denied race (m55) as its own reason to exist, so this module already
        # knows the hazard -- these two writers just did not use the remedy. This one is the
        # sharper of the two: a NEW foreground claim's first write has no beat margin to absorb
        # a miss, and a dropped first write means the claim never appears, so every background
        # call proceeds straight through the yield this file exists to enforce.
        # `bool(...)` rather than an identity test against False: truthiness is the contract
        # every other caller in this project gates on (`if not silence.write_json(...)`), and
        # it is the one that stays correct if `replace_retry` ever grows a third answer.
        return bool(silence.replace_retry(tmp, path))
    except Exception:
        silence.note("gpu_lane.py:_write_claim")
        return False


# --------------------------------------------------------------------------- the slots

def _take_slot(label):
    """Claim one of MAX_SLOTS leases. -> the slot path, False if BUSY, None if UNARBITRABLE.

    `O_CREAT|O_EXCL` is the whole mutual-exclusion mechanism: on Windows and POSIX alike it
    either creates the file or fails, atomically, with no window between the two.

    THREE ANSWERS, NOT TWO, and the missing distinction cost fifteen minutes a call. This
    returned None for two situations that need OPPOSITE responses -- "every slot is live", where
    waiting is exactly right, and "os.open raised, I cannot arbitrate at all", whose own comment
    below already promised the caller "proceeds unmetered". It did not proceed: `lane()`'s queue
    loop cannot tell the two apart from one sentinel, so it went on calling this every `_POLL`
    until `deadline = now + SLOT_LEASE_SECONDS`, i.e. 900 seconds, and then proceeded anyway.
    Reproduced with LANE pointed at a temp dir, this forced to return None and the ceiling
    shortened to 2s: the call was delayed 2.01s, the full ceiling. (order d316c46b67bd)

    That contradicts this module's header verbatim -- "FAIL OPEN, ALWAYS ... a permissions
    error, A SLOT THAT CANNOT BE CREATED ... all of them end in go ahead anyway" -- and `lane()`
    fronts every model call the library makes, so one persistent `os.open` failure on
    `state/gpu_lane` (a permissions change, or Norton, which already blocks DuckDB and Python
    TLS on this machine) turned every model call in nine standing jobs into a 15-minute stall.
    A lane that deadlocks nine standing jobs is worse than no lane at all, which is the whole
    reason that mandate is written down.

    So the two answers are now spelled differently: False means "busy, ask again", None means
    "this lane cannot be arbitrated, stop asking and go". Both are falsy, so every truth test on
    the return value -- including the `if slot:` guards in `lane()`'s own `finally` -- keeps
    working unchanged; only the code that must distinguish them looks at which one it got.
    """
    for i in range(MAX_SLOTS):
        path = os.path.join(LANE, f"slot.{i}.json")
        rec = _read(path)
        if rec is not None and _expired(rec, SLOT_LEASE_SECONDS):
            # the holder is gone; the lease returns to the pool (m55: retried, because a
            # denial here silently leaves the slot claimed by a process that no longer exists)
            _remove_retry(path)
        try:
            fd = os.open(path, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
        except FileExistsError:
            continue
        except Exception:
            return None                  # cannot arbitrate -- caller proceeds unmetered
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as f:
                json.dump({"pid": os.getpid(), "label": label, "heartbeat": _now()}, f)
        except Exception:
            _remove_retry(path)          # m55: we created it and could not write it
            # ALSO UNARBITRABLE, not busy. The slot file was created here and could not be
            # written, so this lane's own storage is not working; polling it for fifteen
            # minutes would reach the same answer more slowly.
            return None
        return path
    # Every slot exists and is live: BUSY. This is the one answer that deserves the wait.
    return False


def _touch(path):
    """Refresh a lease. A long, healthy call must not look abandoned.

    NEVER RESURRECTS. The first version did `rec = _read(path) or {}` and wrote the result, so
    calling it on a slot that had already been released RE-CREATED the file -- with a fresh
    heartbeat and no live holder, i.e. a slot leased forever to nobody. That is reachable: the
    heartbeat thread below is joined with a timeout, and a thread that wakes after the join
    gave up would otherwise resurrect the slot it was supposed to be keeping alive. So a
    missing record, or one belonging to another PID, is left exactly as found.
    """
    if not path:
        return
    with contextlib.suppress(Exception):
        rec = _read(path)
        if not isinstance(rec, dict) or rec.get("pid") != os.getpid():
            return
        rec["heartbeat"] = _now()
        tmp = path + "." + str(os.getpid()) + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(rec, f)
        # m55, as in _write_claim above. THE VERDICT IS DELIBERATELY NOT ACTED ON HERE, and
        # this is the one writer in this module where that is right (order e7b6dcc8d630).
        # A beat is not a fact anybody reads for an answer -- it is a periodic assertion that
        # the holder is still alive, and `_BEAT_SECONDS` is a THIRD of the shortest lease
        # precisely so that two consecutive beats may be lost without anyone judging the holder
        # gone. The next beat, ~100s away, carries the same information and retries the rename;
        # gating on this one would only skip that. Persistent denial for a whole lease does
        # cost the holder its slot, but `replace_retry` has already written `replace-denied:`
        # to the failure ledger by then -- so the condition is visible without this thread
        # deciding anything about it, and a beat thread that escalated would file one row every
        # 100s for a condition the lease expiry already handles.
        silence.replace_retry(tmp, path)


# How often a held lease is refreshed. A third of the lease means two consecutive missed beats
# before anyone judges the holder gone -- tolerant of a stalled thread, still far short of the
# lease itself.
#
# DERIVED FROM THE SHORTEST LEASE THIS THREAD KEEPS, not from the slot lease alone (2026-08-24).
# It was `SLOT_LEASE_SECONDS / 3` = 300s, which is a third of the slot lease and EXACTLY the
# whole of `CLAIM_LEASE_SECONDS`. The moment the same thread also began keeping the foreground
# claim alive, a 300s beat would have been refreshing a 300s lease at the instant it expired --
# a heartbeat that is always exactly too late. Taking the min means adding any shorter lease
# later tightens the beat automatically instead of silently outrunning it.
_BEAT_SECONDS = max(5.0, min(SLOT_LEASE_SECONDS, CLAIM_LEASE_SECONDS) / 3.0)


def _heartbeat(paths, stop):
    """Keep every lease this call holds fresh until the call finishes.

    THE DEFECT THIS CLOSES (m54, measured 2026-08-24). `_touch` existed and was called from
    NOWHERE IN THE TREE -- verified by grep across `src/`. So a slot's heartbeat was written
    once, at acquisition, and never again. Meanwhile `config.yaml` sets `request_timeout: 1800`
    while `SLOT_LEASE_SECONDS` is 900: every prose call outlives its own lease by a factor of
    two, at which point `_take_slot` reads it as expired, deletes the file, and hands the slot
    to somebody else. The holder is still running. MAX_SLOTS is then violated by exactly the
    calls that take longest, which is to say the card is over-subscribed precisely when it is
    busiest -- the M7 pile-up, arriving through the module built to prevent it.

    THE HALF THE m54 FIX MISSED (found 2026-08-24, the audit after the one that fixed slots).
    m54 gave the SLOT a heartbeat and stopped there, but `lane(priority=True)` also writes a
    FOREGROUND CLAIM, and that claim was written once at entry and never refreshed -- the
    identical defect, in the identical function, one variable over. Its exposure was worse, not
    better: `CLAIM_LEASE_SECONDS` is 300 against the slot's 900, so a foreground claim went
    stale three times sooner. `generate.py` is the only `priority=True` caller in the tree and
    it runs with `request_timeout: 1800`; 14 recorded calls have already exceeded 300s, the
    longest at 917s. Past that point `foreground_active()` judged a live prose call abandoned
    and swept its claim, and rule 2 of this module's header -- background yields to foreground
    -- quietly stopped applying to the one call it exists for.

    Accepts one path or several. Every lease the call holds is refreshed on the same beat, so
    there is one thread per call rather than one per lease.

    Daemon thread, bounded waits, every failure swallowed: this must never be able to stop a
    model call. `stop.wait()` returns True the moment the call ends, so release is immediate
    rather than waiting out a sleep.
    """
    many = paths if isinstance(paths, (list, tuple)) else (paths,)
    while not stop.wait(_BEAT_SECONDS):
        for p in many:
            _touch(p)


def _remove_retry(path, attempts=4):
    """Release a lease, outwaiting a transient Windows denial (m55).

    A plain `os.remove` under `suppress(Exception)` loses the race against any reader holding
    the file open -- `status()` and a competing `_take_slot` both open slot files -- and a
    release that silently does not happen strands the slot for the rest of its lease. Same
    reasoning as `silence.replace_retry`, which wraps `os.replace` rather than `os.remove`.
    Persistent failure is not raised: the lease expiry is the backstop.
    """
    for a in range(attempts):
        try:
            os.remove(path)
            return True
        except FileNotFoundError:
            _ = "silence-exempt: already gone IS released -- the absence is the answer here"
            return True
        except Exception:
            _ = ("silence-exempt: the outcome is carried in this function's RETURN VALUE, "
                 "which is the observation. Raising would break fail-open, and the lease "
                 "expiry is the backstop. (A # comment does not satisfy the silence audit -- "
                 "it reads the AST, where comments do not exist.)")
            if a < attempts - 1:
                time.sleep(0.15 * (a + 1))
    return False


@contextlib.contextmanager
def lane(label="background", priority=False):
    """Wrap ONE model call.

    `priority=True` announces foreground work: it does not yield to anyone, and background
    callers elsewhere will wait for it. Everything else yields first, then queues for a slot.

    Every exit path releases. Every failure path proceeds. The call happens either way -- the
    only thing this decides is WHEN.
    """
    if not _ensure_dir():
        yield                            # no state dir, no arbitration; do the work
        return

    slot = None
    fg = None
    beat = None
    stop = None
    try:
        if priority:
            fg = foreground(label)
            fg.__enter__()
        else:
            # YIELD TO LIVE FOREGROUND WORK, but never indefinitely.
            waited = 0.0
            while foreground_active(ignore_pid=os.getpid()) and waited < MAX_YIELD_SECONDS:
                time.sleep(_POLL)
                waited += _POLL

        # QUEUE FOR A SLOT. The ceiling here is the slot lease rather than the yield ceiling:
        # waiting for a genuinely busy card is the correct behaviour, and a dead holder's slot
        # is reclaimed by _take_slot itself, so this cannot wait on nothing forever.
        deadline = _now() + SLOT_LEASE_SECONDS
        while _now() < deadline:
            slot = _take_slot(label)
            if slot:
                break
            if slot is None:
                # CANNOT ARBITRATE -> GO NOW. `_take_slot` says None only when the lane's own
                # storage refused it (os.open raised, or the slot file could not be written),
                # which no amount of polling fixes -- and polling it cost the full 900-second
                # ceiling on every model call in nine standing jobs. This is the "go ahead
                # anyway" the module header mandates and the comment at the raise already
                # promised. Unmetered by design: an unarbitrable lane must not be a stalled
                # one. (order d316c46b67bd)
                break
            time.sleep(_POLL)
        # HOLD EVERY LEASE FOR AS LONG AS THE CALL ACTUALLY RUNS (m54, completed 2026-08-24).
        # Without this a lease ages out mid-call and a competitor reclaims it while the holder
        # is still working. BOTH leases are kept: the slot, and -- for a foreground call -- the
        # claim that tells background work to stand aside. Keeping only the slot left the
        # foreground claim expiring at 300s inside calls permitted to run for 1800.
        _keep = [p for p in (slot, _claim_path() if fg is not None else None) if p]
        if _keep:
            with contextlib.suppress(Exception):
                stop = threading.Event()
                beat = threading.Thread(target=_heartbeat, args=(_keep, stop),
                                        name="gpu-lane-beat", daemon=True)
                beat.start()
        yield
    except Exception:
        raise
    finally:
        # ORDER MATTERS: stop the heartbeat BEFORE releasing, or a beat landing between the
        # remove and the thread noticing would re-create the file. `_touch` refuses to
        # resurrect a missing record as a second guard, so this is belt and braces.
        if stop is not None:
            with contextlib.suppress(Exception):
                stop.set()
        if beat is not None:
            with contextlib.suppress(Exception):
                beat.join(timeout=2.0)
        if slot:
            _remove_retry(slot)
        if fg is not None:
            with contextlib.suppress(Exception):
                fg.__exit__(None, None, None)


def status():
    """What is holding the card right now -- every holder, never a sample."""
    out = {"slots": [], "foreground": [], "max_slots": MAX_SLOTS}
    try:
        if not os.path.isdir(LANE):
            return out
        for name in sorted(os.listdir(LANE)):
            if name.endswith(".tmp"):
                continue
            rec = _read(os.path.join(LANE, name))
            if not isinstance(rec, dict):
                continue
            age = _now() - float(rec.get("heartbeat") or 0)
            row = {"pid": rec.get("pid"), "label": rec.get("label"),
                   "age_s": round(age, 1), "alive": _alive(rec.get("pid"))}
            if name.startswith("slot."):
                out["slots"].append(row)
            elif name.startswith("fg."):
                out["foreground"].append(row)
    except Exception:
        pass
    return out
