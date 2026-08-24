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
import time

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LANE = os.path.join(HERE, "state", "gpu_lane")

# How many model calls may be in flight at once, across every process. One card that serves
# one request at a time does not go faster when nine ask together -- it goes slower, because
# each waits behind the rest AND the daemon cannot rebuild a runner while the queue is full.
# Two rather than one: a single slot would serialise the whole library behind one slow call,
# and the daemon does overlap prompt evaluation with generation to a useful degree.
MAX_SLOTS = int(os.environ.get("PANSCRIPTUM_GPU_SLOTS", "2"))

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
        return False
    try:
        pid = int(pid)
    except Exception:
        return False
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
                with contextlib.suppress(Exception):
                    os.remove(path)
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
    """
    path = _claim_path()
    rec = _read(path) or {}
    depth = int(rec.get("depth") or 0) + 1
    _write_claim(path, depth, label)
    try:
        yield
    finally:
        cur = _read(path) or {}
        d = int(cur.get("depth") or 1) - 1
        if d <= 0:
            with contextlib.suppress(Exception):
                os.remove(path)
        else:
            _write_claim(path, d, label)


def _write_claim(path, depth, label):
    if not _ensure_dir():
        return
    with contextlib.suppress(Exception):
        tmp = path + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump({"pid": os.getpid(), "depth": depth, "label": label,
                       "heartbeat": _now()}, f)
        os.replace(tmp, path)


# --------------------------------------------------------------------------- the slots

def _take_slot(label):
    """Claim one of MAX_SLOTS leases, or return None if they are all live.

    `O_CREAT|O_EXCL` is the whole mutual-exclusion mechanism: on Windows and POSIX alike it
    either creates the file or fails, atomically, with no window between the two.
    """
    for i in range(MAX_SLOTS):
        path = os.path.join(LANE, f"slot.{i}.json")
        rec = _read(path)
        if rec is not None and _expired(rec, SLOT_LEASE_SECONDS):
            with contextlib.suppress(Exception):
                os.remove(path)          # the holder is gone; the lease returns to the pool
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
            with contextlib.suppress(Exception):
                os.remove(path)
            return None
        return path
    return None


def _touch(path):
    """Refresh a lease. A long, healthy call must not look abandoned."""
    if not path:
        return
    with contextlib.suppress(Exception):
        rec = _read(path) or {}
        rec["heartbeat"] = _now()
        tmp = path + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(rec, f)
        os.replace(tmp, path)


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
            time.sleep(_POLL)
        yield
    except Exception:
        raise
    finally:
        if slot:
            with contextlib.suppress(Exception):
                os.remove(slot)
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
