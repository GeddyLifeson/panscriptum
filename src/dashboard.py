#!/usr/bin/env python3
"""
DASHBOARD — what every meter in this project reads, on one page, without asking anybody.

WHY
---
Everything this library does is metered somewhere, and until now every meter was in a different
place and most of them were in my head: the corpus reader's progress line in one log, the page
roll's in another, the free-tier quotas inside Cascade's router, the watcher's findings in a
JSON ledger, coverage in a third file. The owner's only way to see where things stood was to ask
and wait for someone to go and look.

That is a bad arrangement for a project whose entire recurring defect is a number nobody was
looking at. A quota exhausted at two in the afternoon should be visible at two in the afternoon.

WHAT IT SERVES
--------------
    /            the page. Auto-refreshes; no build step, no dependencies, one file.
    /api/state   the same numbers as JSON, for anything else that wants them.

Nothing here computes anything of its own. It reads what the pipeline already writes -- logs,
ledgers, the router's own accounting -- so the dashboard can never disagree with the system it
is reporting on. If a number is wrong here it is wrong there, which is the property you want in
an instrument.

THE QUOTA PANEL IS THE POINT
----------------------------
Free tiers meter four different ways at once -- requests per minute, requests per day, tokens
per minute, tokens per day -- and a bucket is exhausted the moment ANY of the four hits zero.
Today Mistral's daily 2,000 requests were spent by mid-afternoon while its per-minute window sat
wide open, and the corpus read slowed by a factor of ten with nothing in any log to say why. The
panel shows every window for every bucket, and the TIGHTEST one is what actually binds.
"""
import argparse
import glob
import http.server
import json
import os
import re
import socketserver
import sys
import time

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(HERE, "src")
sys.path.insert(0, SRC)
import silence                                                          # noqa: E402

_BAD_CHARS = (chr(8), chr(11), chr(12), chr(7))
if any(c in open(os.path.abspath(__file__), encoding="utf-8").read() for c in _BAD_CHARS):
    raise SystemExit(__file__ + ": a regex escape was eaten in transit.")

STATE = os.path.join(HERE, "state")
DATA = os.path.join(HERE, "data")

# The reader's progress line. Built by hand-transcribing the format string read.py prints, so
# if that line changes this stops matching -- not "safely": `_read_row` then appends nothing,
# and the corpus-read row (and movement()'s chunks metric) vanish from the page, rendered as
# "No job is writing a progress line right now", indistinguishable from the reader being down.
# `_tail_match`'s `hint` argument gives that case its own ledger entry instead.
RE_READ = re.compile(
    r"(?P<done>[\d,]+)/(?P<total>[\d,]+)\s+(?P<rate>[\d.]+)\s+chunks/s\s+"
    r"feats\s+(?P<feats>[\d,]+)\s+dropped\s+(?P<dropped>[\d,]+)\s+"
    r"chunks\s+(?P<chunks>[\d,]+)/(?P<budget>[\d,]+).*?"
    r"(?P<gpu>\d+)\s+to\s+GPU,\s+(?P<unans>\d+)\s+UNANSWERED.*?eta\s+(?P<eta>[\d.]+)h")

RE_ROLL = re.compile(
    r"(?P<done>[\d,]+)/(?P<total>[\d,]+)\s+(?P<rate>[\d.]+)/s\s+"
    r"feats\s+(?P<feats>[\d,]+)\s+quantities\s+(?P<q>[\d,]+)\s+"
    r"pages\s+(?P<pages>[\d,]+)\s+(?P<chars>[\d.]+)M\s+chars\s+eta\s+(?P<eta>[\d.]+)h")


def _num(s):
    try:
        return int(str(s).replace(",", ""))
    except Exception:
        # Descriptive tag, not a line number (order d61b06dbe66d), for the reason this file
        # already gives at the `metrics-badline` handler below: a baked-in line number rots the
        # moment anything above it moves, and this one was already four lines out.
        silence.note("dashboard.py:num-parse")
        return 0


def _tail_match(path, rx, keep=400, hint=None):
    """The most recent line in a log that matches. Reads the tail, not the file.

    These logs reach tens of megabytes over a long run and the dashboard polls every few
    seconds; reading them whole would make the instrument the heaviest thing on the machine.

    `hint`, if given, is a short substring that only appears on a line the progress format was
    MEANT to produce (e.g. "chunks/s" for the reader, "M chars" for the roll). `RE_READ` and
    `RE_ROLL` are both built by hand-transcribing read.py's/feats.py's own format string, and
    neither of those files can see this one -- a field added or reworded there is a silent
    non-match here, and the caller cannot tell that apart from the ordinary case of a job that
    simply has not printed in the last `keep` lines. Both look identical: nothing returned. If
    `hint` is on a recent line but no line the FULL regex matched, that is not idleness, it is
    the format having moved out from under `rx`, and it gets its own ledger entry so it stops
    being indistinguishable from "nothing to report" (the same unreadable-vs-empty rule Hard
    Rule 0 applies to a read failure, applied here to a format failure instead).
    """
    try:
        size = os.path.getsize(path)
        with open(path, "rb") as f:
            f.seek(max(0, size - 60000))
            body = f.read().decode("utf-8", "replace")
    except Exception:
        silence.note("dashboard.py:tail")
        return None
    lines = body.splitlines()[-keep:]
    for line in reversed(lines):
        m = rx.search(line)
        if m:
            return m.groupdict()
    if hint and any(hint in ln for ln in lines):
        silence.note(f"dashboard.py:tail-format-mismatch:{os.path.basename(path)}")
    return None


# --------------------------------------------------------------------------- the panels

def quotas():
    """Every window on every bucket, and which one is actually binding.

    A bucket is exhausted when ANY of its four meters hits zero, so reporting only requests-per-
    day would have shown Mistral as healthy at the exact moment its per-minute window was the
    thing stopping the run -- and reporting only per-minute would have missed the opposite.
    """
    out = []
    try:
        import cascade_bridge as CB
        if not CB.engine():
            return [{"bucket": "cascade unavailable", "windows": [], "worst": 0.0}]
        router = CB._ROUTER
        seen = {}
        for m in router.models:
            if m.bucket in seen:
                continue
            seen[m.bucket] = m
        for bucket, m in sorted(seen.items()):
            try:
                st = router.model_status(m)
            except Exception:
                silence.note("dashboard.py:model_status")
                continue
            if st.get("unlimited"):
                out.append({"bucket": bucket, "model": m.id, "unlimited": True,
                            "windows": [], "worst": 1.0})
                continue
            windows, worst = [], 1.0
            for name, v in (st.get("remaining") or {}).items():
                if not isinstance(v, dict) or not v.get("cap"):
                    continue
                left, cap = max(0, v.get("left", 0)), v["cap"]
                frac = left / cap if cap else 0.0
                worst = min(worst, frac)
                windows.append({"name": name, "left": left, "cap": cap,
                                "frac": round(frac, 4)})
            out.append({"bucket": bucket, "model": m.id, "unlimited": False,
                        "windows": sorted(windows, key=lambda w: w["frac"]),
                        "worst": round(worst, 4)})
    except Exception as e:
        silence.note("dashboard.py:quotas")
        out.append({"bucket": f"quota read failed: {type(e).__name__}", "windows": [],
                    "worst": 0.0})
    return out


def throughput(minutes=15):
    """Calls actually made in the recent past, per bucket. The quota panel says what is LEFT;
    this says what is being SPENT, and the two together are the whole picture."""
    import contextlib
    import sqlite3
    from urllib.request import pathname2url
    path = os.path.join(STATE, "cascade_scratch.db")
    out = {"window_min": minutes, "calls": 0, "per_hour": 0, "buckets": []}
    # ABSENT IS NOT THE SAME AS UNREADABLE (order ef7a5b8b56a5). `sqlite3.connect` CREATES a
    # missing file, so on a machine where Cascade has never run this used to mint a 0-byte
    # database, fail the query with "no such table: usage", and post the same silence tag on
    # every five-second poll -- 720 entries an hour in the ledger for a condition that is not a
    # failure. The existence test comes first and carries its own tag, and the connection is
    # opened read-only via the URI form so a monitor can never author the file it is watching.
    if not os.path.exists(path):
        silence.note("dashboard.py:throughput-no-db")
        return out
    try:
        # contextlib.closing: this ran unclosed on a 5s poll loop, leaking a handle per tick.
        with contextlib.closing(
                sqlite3.connect("file:%s?mode=ro" % pathname2url(path), uri=True)) as c:
            since = time.time() - minutes * 60
            rows = list(c.execute(
                "select bucket, count(*), sum(outcome='ok') from usage where ts > ? "
                "group by bucket order by 2 desc", (since,)))
        total = sum(r[1] for r in rows)
        out["calls"] = total
        out["per_hour"] = int(total * 60 / minutes) if minutes else 0
        out["buckets"] = [{"bucket": b, "calls": n, "ok": int(ok or 0)} for b, n, ok in rows]
    except Exception:
        silence.note("dashboard.py:throughput")
    return out


def jobs():
    """The long-running work, each as a fraction of its own honest denominator.

    FAULT-ISOLATED like every sibling panel (run #19). This was the one builder in the file with
    no handler of its own, and `state()` calls it unguarded -- so a single unexpected value in
    read_auto.log or roll_auto.log would raise all the way out of `state()` and be caught only at
    the HTTP layer, replacing the ENTIRE /api/state response with an error blob. Every other
    panel degrades to an empty result and lets the rest of the page render; the panel that
    reports on the project's bottleneck job should not be the one that can black out the page.
    Note the two logs are isolated separately: a malformed reader line must not cost the roll's
    row as well.
    """
    out = []
    import lognames as LN
    try:
        _read_row(out, LN)
    except Exception:
        silence.note("dashboard.py:jobs-read")
    try:
        _roll_row(out, LN)
    except Exception:
        silence.note("dashboard.py:jobs-roll")
    return out


def _read_row(out, LN):
    r = _tail_match(os.path.join(STATE, LN.READ), RE_READ, hint="chunks/s")
    if r:
        out.append({
            "name": "corpus read", "unit": "chunks",
            "done": _num(r["chunks"]), "total": _num(r["budget"]),
            "detail": (f"{_num(r['done']):,}/{_num(r['total']):,} entities  ·  "
                       f"{_num(r['feats']):,} feats  ·  {r['rate']} chunks/s"),
            "warn": (f"{_num(r['unans'])} unanswered" if _num(r["unans"]) else ""),
            # THE FABRICATION GUARD HAD NO INPUT, SO IT NEVER RAN ONCE. Run #28.
            # `RE_READ` has captured `dropped` -- the count of model sentences the verbatim
            # check REJECTED as not present in the source -- since the regex was written, and
            # this dict threw it away one line after parsing it. `standards.py:663` then read
            # `read.get("raw")`, a key NOTHING in the tree has ever set, so `drop` was always
            # None, `fab` stayed None, and the HIGH standard `sentences that survive the
            # verbatim check` was never even APPENDED to the standards list. It did not read
            # green: it did not exist. A guard against the model inventing text, silently
            # absent for its whole life -- lesson 9's shape ("a check that cannot fail looks
            # exactly like a check that passed") in its most expensive location.
            #
            # Worse, `every declared floor is measured` is supposed to catch precisely this and
            # did not: MAX_FABRICATION *is* named inside `check()`, on a line that can never
            # execute. A source-grep cannot tell a used constant from an unreachable one.
            "dropped": _num(r["dropped"]),
            "eta_h": float(r["eta"])})


def _roll_row(out, LN):
    roll = _tail_match(os.path.join(STATE, LN.ROLL), RE_ROLL, hint="M chars")
    if roll:
        out.append({
            "name": "page roll", "unit": "entities",
            "done": _num(roll["done"]), "total": _num(roll["total"]),
            "detail": (f"{_num(roll['pages']):,} pages  ·  {roll['chars']}M characters  ·  "
                       f"{roll['rate']}/s"),
            "warn": "", "eta_h": float(roll["eta"])})


_TTL_MEMO = {}


def _ttl(key, seconds, fn):
    """A 5-second client poll against sources that change on an hours clock was recomputing
    85,904-entry sums and a recursive glob per tick (round-2 optimization audit, finding 6).
    Same pattern as overnight._proc_lines: within the TTL, everyone reads the same answer."""
    now = time.time()
    hit = _TTL_MEMO.get(key)
    if hit and now - hit[0] < seconds:
        return hit[1]
    val = fn()
    _TTL_MEMO[key] = (now, val)
    return val


def library():
    return _ttl("library", 30, _library)


def _library():
    """What the library actually holds: hosts, coverage, and the phases that exist."""
    out = {}
    try:
        import weave_index as WI
        import feats as F
        hosts = json.load(open(F.HOSTS, encoding="utf-8"))
        recs = {r["source"]: r for r in WI.load_records()}
        with_host = [s for s in recs if hosts.get(s)]
        without = [s for s in recs if not hosts.get(s)]
        out["sources"] = {"total": len(recs), "with_host": len(with_host),
                          "without_host": len(without),
                          "entries_with_host": sum(len(recs[s]["entries"]) for s in with_host),
                          "entries_without_host": sum(len(recs[s]["entries"]) for s in without)}
    except Exception:
        silence.note("dashboard.py:library-hosts")
    try:
        rows = json.load(open(os.path.join(DATA, "COVERAGE.json"), encoding="utf-8"))
        n = sum(r["entries"] for r in rows)
        cited = sum(r["cited"] for r in rows)
        read = sum(r["read"] for r in rows)
        out["coverage"] = {"entries": n, "cited": cited, "read": read,
                           "settled": cited + read, "feats": sum(r["feats"] for r in rows),
                           "age_h": round((time.time() - os.path.getmtime(
                               os.path.join(DATA, "COVERAGE.json"))) / 3600, 1)}
    except Exception:
        silence.note("dashboard.py:library-coverage")
    try:
        import pipeline as P
        out["phases"] = [{"name": n, "built": hasattr(P, "phase_" + n)} for n in P.PHASES]
    except Exception:
        silence.note("dashboard.py:library-phases")
    try:
        readfeats = len(glob.glob(os.path.join(DATA, "readfeats", "**", "*.json"),
                                  recursive=True))
        out["readfeats"] = readfeats
    except Exception:
        silence.note("dashboard.py:library-readfeats")
    return out


def watch():
    return _ttl("watch", 30, _watch)


def _watch():
    """The standing sweep's verdict, so the dashboard says when the code itself is suspect."""
    out = {"open": 0, "high": 0, "rounds": 0, "findings": [], "broken": []}
    try:
        d = json.load(open(os.path.join(DATA, "OVERWATCH.json"), encoding="utf-8"))
        out["rounds"] = d.get("rounds", 0)
        openf = [v for v in (d.get("findings") or {}).values() if v.get("state") == "open"]
        out["open"] = len(openf)
        out["high"] = sum(1 for f in openf if (f.get("severity") or "").lower() == "high")
        out["findings"] = [{"module": f.get("module"), "symbol": f.get("symbol"),
                            # UNCUT (order 50c9f6130b95). This per-row [:160] survived inside the
                            # list the cap three lines below was removed from: the longest
                            # `actual` on disk measured exactly 160, so findings WERE being cut
                            # mid-sentence with no ellipsis and the full text lived nowhere on
                            # the page. The table cell wraps; /api/state has no layout at all.
                            "actual": f.get("actual") or "",
                            "severity": f.get("severity", "medium")}
                           for f in openf]     # ALL open findings -- a monitoring cap ruled a truncation, 2026-08-24
    except Exception:
        silence.note("dashboard.py:watch")
    try:
        f = json.load(open(os.path.join(STATE, "failures.json"), encoding="utf-8"))
        # ALL of them, ranked -- the identical cap on `findings` five lines above this was ruled
        # a truncation on 2026-08-24 and this one was not visited then. `swallowed_total` already
        # published the magnitude, but a tag past rank 6 had no identity on the page at all:
        # `state/failures.json` held 25 distinct tags the day this was found and six were
        # displayable. Ranking (worst first) is still useful and stays; the cutoff does not.
        out["swallowed"] = sorted(f.items(), key=lambda kv: -kv[1])
        out["swallowed_total"] = sum(f.values())
    except Exception:
        silence.note("dashboard.py:failures")
    return out


HISTORY = os.path.join(STATE, "dashboard_history.json")
# How far back "moved" looks. Long enough that slow work still registers, short enough that the
# number answers "is it going right now" rather than "did it ever".
MOVED_WINDOW_MIN = 30


def movement(now_state):
    """What has CHANGED, not what the level is.

    The panel showed bars and the bars did not move, so it read as a system doing nothing --
    which was half right and impossible to tell from the levels alone. A progress bar at 12.8%
    looks identical whether it reached 12.8% a minute ago or three hours
    ago.

    So every reading is appended to a small history and the deltas are computed against the
    oldest sample inside the window. A number that has not moved now SAYS it has not moved,
    which is the difference between an instrument and a decoration.
    """
    keys = {
        "cited": ((now_state.get("library") or {}).get("coverage") or {}).get("cited"),
        "settled": ((now_state.get("library") or {}).get("coverage") or {}).get("settled"),
        "feats": ((now_state.get("library") or {}).get("coverage") or {}).get("feats"),
        "entities read": (now_state.get("library") or {}).get("readfeats"),
        "chunks": next((j.get("done") for j in (now_state.get("jobs") or [])
                        if j.get("name") == "corpus read"), None),
        "standards met": sum(1 for x in (now_state.get("standards") or []) if x.get("holds")),
    }
    row = {"at": time.time(), **{k: v for k, v in keys.items() if v is not None}}
    # A CORRUPT HISTORY FILE MUST HEAL, NOT WEDGE.
    #
    # Run #26 found `silent:dashboard.py:movement:JSONDecodeError` at 82 and climbing. The read
    # and the write shared ONE try/except, so a torn HISTORY file threw on `json.load`, skipped
    # the write that would have replaced it, and returned `[]` -- which the panel renders as the
    # cheerful "No history yet". Every five-second poll then re-threw on the same bytes: the file
    # could never be repaired by the only code that writes it, and the movement panel -- the one
    # instrument that can see "every counter flat while every job is up" -- was dark for as long
    # as the corruption lasted, saying only that it was new.
    #
    # Isolating the load fixes both halves. A decode failure is now a fact about the OLD file,
    # not a reason to abandon the new sample: `hist` starts empty, this poll's row is appended,
    # and the write lands a valid file that every later poll can read. Losing the history is the
    # cost of the corruption, not of the repair; staying blind was the cost of the old shape.
    hist = []
    if os.path.exists(HISTORY):
        try:
            with open(HISTORY, encoding="utf-8") as f:
                hist = json.load(f)
            # AND THE ELEMENTS HAVE TO BE DICTS TOO (order 62286a6c018a). A list of non-dicts --
            # `[1, 2, 3]` -- passed this guard, and `h.get("at", 0)` then raised inside the
            # try below, which returned [] and SKIPPED the write that would have healed the
            # file. Every five-second poll repeated it forever: the one corrupt shape that
            # wedged, in the repair whose own comment is "A CORRUPT HISTORY FILE MUST HEAL,
            # NOT WEDGE". Reproduced on a temp history before and after.
            if not isinstance(hist, list) or not all(isinstance(h, dict) for h in hist):
                raise ValueError("history is not a list of sample dicts")
        except Exception:
            silence.note("dashboard.py:movement-corrupt-reset")
            hist = []
    try:
        hist.append(row)
        cutoff = time.time() - 24 * 3600
        hist = [h for h in hist if h.get("at", 0) > cutoff][-2000:]
        # silence.write_json, not a hand-rolled path + ".tmp": this server is threaded
        # (daemon_threads=True) and every /api/state poll runs this function, so two
        # concurrent pollers on a fixed temp name collide on the temp file itself. The
        # PID+thread-qualified tmp name write_json uses closes that race.
        #
        # THE VERDICT IS DELIBERATELY NOT GATED, and this comment is the repair (run #37's
        # discarded-write-verdict pass, which gated address_space, allsweep, cleanup, corpus_db,
        # feats and generate and stopped here). Three things have to be true for that to be safe
        # and all three are:
        #
        #   1. The answer this function RETURNS does not depend on the write. `hist` already
        #      holds this poll's row in memory and the movement rows below are computed from it,
        #      so a denied replace costs the sample's persistence, never the current reading.
        #   2. The next poll retries. This runs on every /api/state request -- seconds, not
        #      hours -- so a lock that outwaits `replace_retry` is re-attempted immediately with
        #      no operator action, which is exactly the "the caller's write lands next round"
        #      case `write_json` documents.
        #   3. The stall detector does not go blind if it never lands. With the file frozen,
        #      `base` stays the last row that did land and `span` grows, so a genuinely flat
        #      counter still satisfies `delta == 0 and span >= 10` -- the panel keeps reporting
        #      stalled, and once the 24h cutoff empties the frozen rows it reports a zero-length
        #      window rather than a false clean bill.
        #
        # Note the `except` below covers the append/serialise, NOT the replace: write_json
        # answers False for a denied rename instead of raising. A persistent denial is still
        # recorded -- `replace_retry` writes `replace-denied:dashboard_history.json` into the
        # health ledger itself -- so nothing here needs a second channel for it.
        silence.write_json(HISTORY, hist)
    except Exception:
        silence.note("dashboard.py:movement")
        return []

    window = time.time() - MOVED_WINDOW_MIN * 60
    older = [h for h in hist if h.get("at", 0) <= window]
    base = older[-1] if older else (hist[0] if hist else {})
    span = (row["at"] - base.get("at", row["at"])) / 60 if base else 0
    out = []
    for k, v in keys.items():
        if v is None:
            continue
        was = base.get(k)
        delta = None if was is None else v - was
        # A COUNTER THAT FELL IS NOT A COUNTER THAT MOVED.
        #
        # `stalled` tests `delta == 0`, so a NEGATIVE delta was reported as ordinary progress.
        # Run #26 caught the page showing `chunks` at delta -3689 with `stalled: false`, and the
        # cause is benign but the reporting was not: `read.py`'s `done["chunks"]` is an
        # in-process counter reset to zero on every launch and never persisted, so a reader
        # restart between two samples makes the total fall. The panel was comparing across a
        # discontinuity it had no way to see -- and worse, a restart therefore READS AS MOVEMENT,
        # which is precisely the "every counter flat while every job is up" condition the
        # `the library's counters are moving` standard exists to catch. A restart could mask one.
        #
        # Named rather than smoothed: `reset` says what happened, the delta stays honest, and
        # nothing downstream has to guess whether -3689 was progress.
        reset = delta is not None and delta < 0
        if reset:
            delta = None
        out.append({"metric": k, "now": v, "delta": delta,
                    "minutes": round(span),
                    "reset": reset,
                    "stalled": delta == 0 and span >= 10})
    return out


def metrics(tail_bytes=250_000):
    """Per-tag latency and outcome from state/model_metrics.jsonl -- the observability
    baseline. Local rows (pipeline.ask) carry token counts and tps from Ollama's own eval
    fields; cloud rows (cascade_bridge.ask) carry ok/chars, because a stream reports no
    counts. Tail-read only: the ledger is append-forever and the panel wants the recent past,
    not an archaeology dig."""
    p = os.path.join(HERE, "state", "model_metrics.jsonl")
    rows = []
    try:
        size = os.path.getsize(p)
        with open(p, "rb") as f:
            if size > tail_bytes:
                f.seek(-tail_bytes, 2)
            raw = f.read().decode("utf-8", "replace").splitlines()
        for ln in raw[1:] if size > tail_bytes else raw:
            try:
                r = json.loads(ln)
                if isinstance(r, dict) and r.get("tag"):
                    rows.append(r)
            except Exception:
                # Descriptive tag, not a line number (run #19). The old label said
                # "dashboard.py:336" while sitting at 362 -- m81's drift, in a file not
                # previously known to carry it. Line-number labels are baked once by
                # `silence.py --instrument` and never move as the file grows, so every one of
                # them rots; a stable tag cannot.
                silence.note("dashboard.py:metrics-badline")
                pass
    except Exception:
        silence.note("dashboard.py:metrics")
        return []
    by = {}
    for r in rows:
        by.setdefault(r["tag"], []).append(r)

    def pct(v, q):
        v = sorted(v)
        return v[min(len(v) - 1, int(q * len(v)))] if v else None

    out = []
    for tag, rs in sorted(by.items(), key=lambda kv: -len(kv[1])):
        secs = [r["s"] for r in rs if isinstance(r.get("s"), (int, float))]
        oks = [r.get("ok") for r in rs if "ok" in r]
        tps = [r["tps"] for r in rs if isinstance(r.get("tps"), (int, float))]
        out.append({"tag": tag, "n": len(rs),
                    "p50": round(pct(secs, 0.5) or 0, 1), "p95": round(pct(secs, 0.95) or 0, 1),
                    "ok_pct": round(100 * sum(1 for o in oks if o) / len(oks)) if oks else None,
                    "tps": round(sum(tps) / len(tps), 1) if tps else None})
    return out


def safety():
    """The interlocks, as data. The FIRST thing the page shows and the first thing a run reads.

    Every field here is READ from a file, never computed by running the thing it reports on. The
    dashboard polls every five seconds; a panel that ran the drill would be a denial-of-service
    against its own library, and a panel that ran `liveness` would take a minute per poll. So the
    drill writes `state/drill_last.json` when it runs and this reports what it found and HOW OLD
    that is -- an age is not decoration here, it is the difference between "57 nets held" and
    "57 nets held, at some point, possibly before the change you are looking at".
    """
    out = {"halted": None, "prose_gate": None, "drill": None, "escalation_recent": None}
    try:
        import escalation as ESC
        halted, rec = ESC.status()
        rec = rec or {}
        # A CLEARED halt leaves its record on disk, which is the point -- it is the paper trail.
        # But reporting its `code` and `what` alongside `halted: false` reads as a live fault to
        # anyone consuming state.json directly, and this project has lost whole runs to a stale
        # field that looked current. The reason travels ONLY while the halt stands; once lifted
        # it becomes `last_cleared`, which is unambiguous about being history.
        out["halted"] = {"halted": bool(halted)}
        if halted:
            out["halted"].update({"code": rec.get("code"), "what": rec.get("what"),
                                  "by": rec.get("by"), "source": rec.get("source"),
                                  "also": len(rec.get("also") or [])})
        elif rec:
            out["halted"]["last_cleared"] = {
                "code": rec.get("code"), "ruling": rec.get("ruling"),
                "cleared_by": rec.get("cleared_by")}
    except Exception:
        silence.note("dashboard.py:safety-halt")
    try:
        import prose_gate as PG
        ok, why = PG.gate_open()
        out["prose_gate"] = {"open": bool(ok), "why": why}
    except Exception:
        silence.note("dashboard.py:safety-gate")
    try:
        import prose_gate as PG4
        ok4, why4 = PG4.step4_gate_open()
        out["step4_gate"] = {"open": bool(ok4), "why": why4}
    except Exception:
        silence.note("dashboard.py:safety-step4")
    try:
        # The calibration is RE-DERIVED here, not read from a constant -- it is the one number
        # every printed Magnitude in the library inherits, and the halved interval survived for
        # months because the checks that watched it had been recorded from its own bad output.
        import assay as _AS
        out["assay_calibration"] = _AS.calibration_report()
    except Exception:
        silence.note("dashboard.py:safety-assay")
    try:
        # Hosts currently being paced slower than their base rate, and any host quarantined for
        # persistent throttling. A backoff that nothing reports is indistinguishable from a slow
        # network, which is how "we are being blocked" becomes "this source is empty".
        import feats as _F
        import binding_health as _BH
        out["fetch"] = {"backoff": _F.backoff_state(),
                        # reason uncut, same ruling as the finding text above (order
                        # 50c9f6130b95): panelSafety renders `h + ': ' + qn[h]` verbatim, so a
                        # [:120] here stopped a quarantine reason mid-sentence with no marker.
                        "quarantined": {h: r.get("reason", "")
                                        for h, r in _BH.quarantined().items()}}
    except Exception:
        silence.note("dashboard.py:safety-fetch")
    try:
        p = os.path.join(HERE, "state", "drill_last.json")
        with open(p, encoding="utf-8") as f:
            d = json.load(f)
        out["drill"] = {"nets": d.get("nets"), "held": d.get("held"),
                        "breached": d.get("breached") or [],
                        "liveness": d.get("liveness"), "liveness_ceiling": d.get("ceiling"),
                        "age_min": round((time.time() - os.path.getmtime(p)) / 60.0, 1)}
    except Exception:
        _ = "silence-exempt: no drill has run yet is a legitimate first state, and the panel "\
            "says so rather than pretending"
    try:
        p = os.path.join(HERE, "state", "escalation.log")
        cutoff = time.time() - 24 * 3600
        by = {}
        with open(p, encoding="utf-8") as f:
            for ln in f:
                try:
                    r = json.loads(ln)
                except Exception:
                    continue
                if (r.get("at") or 0) >= cutoff:
                    by[r.get("level_name") or "?"] = by.get(r.get("level_name") or "?", 0) + 1
        out["escalation_recent"] = by
    except Exception:
        _ = "silence-exempt: an empty escalation log is the good state"
    return out


def state():
    s = {"at": time.strftime("%Y-%m-%d %H:%M:%S"), "quotas": quotas(),
         "throughput": throughput(), "jobs": jobs(), "library": library(),
         "watch": watch(), "metrics": metrics(), "safety": safety()}
    try:
        import standards as ST
        s["standards"] = ST.check(s)
    except Exception:
        silence.note("dashboard.py:standards")
        s["standards"] = []
    s["movement"] = movement(s)
    return s


# --------------------------------------------------------------------------- the page

PAGE = r"""<!doctype html>
<html lang="en"><head><meta charset="utf-8">
<title>Panscriptum — Instruments</title>
<meta name="viewport" content="width=device-width,initial-scale=1">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Spectral:ital,wght@0,400;0,600;1,400&family=IBM+Plex+Mono:wght@400;500;600&display=swap" rel="stylesheet">
<style>
:root{
  --ink:#e8e3d9; --ink-dim:#9b968c; --ink-faint:#6b675f;
  --ground:#14140f; --panel:#1c1c16; --panel-2:#232219; --rule:#332f26;
  --brass:#c8a44a; --brass-dim:#8a7333;
  --good:#7fa650; --warn:#c8853a; --bad:#b4483c;
  --mono:'IBM Plex Mono',ui-monospace,Menlo,Consolas,monospace;
  --serif:'Spectral',Georgia,'Times New Roman',serif;
}
*{box-sizing:border-box}
body{margin:0;background:var(--ground);color:var(--ink);font-family:var(--serif);
  font-size:15px;line-height:1.5;-webkit-font-smoothing:antialiased}
header{padding:26px 30px 18px;border-bottom:1px solid var(--rule);
  display:flex;align-items:baseline;gap:18px;flex-wrap:wrap}
h1{font-size:19px;font-weight:600;margin:0;letter-spacing:.14em;text-transform:uppercase}
.stamp{font-family:var(--mono);font-size:11px;color:var(--ink-faint);letter-spacing:.1em}
.wrap{display:grid;grid-template-columns:repeat(auto-fit,minmax(370px,1fr));gap:18px;padding:22px 30px 60px}
section{background:var(--panel);border:1px solid var(--rule);border-radius:2px;padding:18px 20px 20px}
section.wide{grid-column:1/-1}
h2{font-family:var(--mono);font-size:10.5px;font-weight:600;letter-spacing:.2em;
  text-transform:uppercase;color:var(--brass);margin:0 0 14px;padding-bottom:9px;
  border-bottom:1px solid var(--rule)}
.row{display:flex;justify-content:space-between;align-items:baseline;gap:12px;margin:11px 0 5px}
.label{font-family:var(--mono);font-size:12px;color:var(--ink)}
.value{font-family:var(--mono);font-size:12px;color:var(--ink-dim);
  font-variant-numeric:tabular-nums;white-space:nowrap}
.bar{height:7px;background:var(--panel-2);border:1px solid var(--rule);overflow:hidden}
.bar>i{display:block;height:100%;background:var(--brass);transition:width .5s ease}
.bar>i.good{background:var(--good)} .bar>i.warn{background:var(--warn)} .bar>i.bad{background:var(--bad)}
.sub{font-family:var(--mono);font-size:11px;color:var(--ink-faint);margin:5px 0 14px;
  font-variant-numeric:tabular-nums}
.note{font-family:var(--mono);font-size:11px;color:var(--warn)}
.bucket{margin:0 0 15px;padding-bottom:13px;border-bottom:1px solid var(--rule)}
.bucket:last-child{border-bottom:none;margin-bottom:0;padding-bottom:0}
.win{display:grid;grid-template-columns:74px 1fr 96px;gap:9px;align-items:center;margin:4px 0}
.win .n{font-family:var(--mono);font-size:10px;color:var(--ink-faint);letter-spacing:.08em;
  text-transform:uppercase}
.win .v{font-family:var(--mono);font-size:10.5px;color:var(--ink-dim);text-align:right;
  font-variant-numeric:tabular-nums}
.pill{display:inline-block;font-family:var(--mono);font-size:9.5px;letter-spacing:.1em;
  padding:2px 7px;border:1px solid var(--rule);color:var(--ink-faint);text-transform:uppercase}
.pill.dry{color:var(--bad);border-color:var(--bad)}
.pill.low{color:var(--warn);border-color:var(--warn)}
.pill.ok{color:var(--good);border-color:var(--good)}
table{width:100%;border-collapse:collapse;font-family:var(--mono);font-size:11.5px}
td{padding:5px 8px 5px 0;border-bottom:1px solid var(--rule);color:var(--ink-dim);
  font-variant-numeric:tabular-nums}
td.k{color:var(--ink)} tr:last-child td{border-bottom:none}
.empty{font-family:var(--mono);font-size:11.5px;color:var(--ink-faint);font-style:normal}
footer{padding:0 30px 40px;font-family:var(--mono);font-size:10.5px;color:var(--ink-faint)}
.sgrid{display:grid;grid-template-columns:repeat(auto-fit,minmax(230px,1fr));gap:16px;margin:14px 0 4px}
.gname{font-family:var(--mono);font-size:9.5px;letter-spacing:.2em;text-transform:uppercase;
  color:var(--brass-dim);margin-bottom:6px}
.srow{display:grid;grid-template-columns:1fr auto;gap:6px;align-items:baseline;
  font-family:var(--mono);font-size:11px;padding:3px 0;border-bottom:1px solid var(--rule)}
.srow:last-child{border-bottom:none}
.sname{color:var(--ink-dim)} .sval{color:var(--good);font-variant-numeric:tabular-nums}
.sfloor{grid-column:1/-1;font-size:9.5px;color:var(--ink-faint)}
.srow.miss .sname{color:var(--ink)} .srow.miss .sval{color:var(--bad);font-weight:600}
.srow.miss{border-left:2px solid var(--bad);padding-left:7px;margin-left:-9px}
.order{margin:10px 0 0;padding:10px 12px;background:var(--panel-2);border-left:2px solid var(--warn)}
.otitle{font-family:var(--mono);font-size:11px;color:var(--warn);margin-bottom:5px}
.obody{font-size:13.5px;color:var(--ink-dim);line-height:1.5}
td.up{color:var(--good)} td.down{color:var(--bad);font-weight:600}
</style></head><body>
<header>
  <h1>Panscriptum · Instruments</h1>
  <span class="stamp" id="stamp">reading…</span>
</header>
<div class="wrap" id="wrap"></div>
<footer>Served by <code>src/dashboard.py</code>. Every number is read from what the pipeline
already writes — logs, ledgers, and Cascade's own accounting — so this page cannot disagree with
the system it reports on. Refreshes every 5 seconds.</footer>
<script>
const el=(t,c,x)=>{const n=document.createElement(t);if(c)n.className=c;
  if(x!==undefined)n.textContent=x;return n};
const cls=f=>f<=0.001?'bad':f<0.15?'bad':f<0.4?'warn':'good';
const pct=f=>(f*100).toFixed(0)+'%';
function bar(frac,kind){const b=el('div','bar');const i=el('i',kind||cls(frac));
  i.style.width=Math.max(0,Math.min(1,frac))*100+'%';b.appendChild(i);return b}

function panelMovement(d){const s=el('section','wide');
  s.appendChild(el('h2',null,'Movement — what has changed, not what the level is'));
  const M=d.movement||[];
  if(!M.length){s.appendChild(el('div','empty','No history yet. Deltas appear after the second reading.'));return s}
  const t=el('table');
  M.forEach(m=>{const tr=el('tr');
    const d1=el('td','k',m.metric);
    const d2=el('td',null,(m.now||0).toLocaleString());
    let txt='—', cls='';
    if(m.delta===null||m.delta===undefined){txt='first reading'}
    else if(m.delta>0){txt='+'+m.delta.toLocaleString()+' in '+m.minutes+' min';cls='up'}
    else if(m.delta<0){txt=m.delta.toLocaleString()+' in '+m.minutes+' min';cls='down'}
    else{txt=m.stalled?('NO CHANGE in '+m.minutes+' min'):'no change yet';cls=m.stalled?'down':''}
    const d3=el('td',cls,txt);
    tr.append(d1,d2,d3);t.appendChild(tr)});
  s.appendChild(t);
  s.appendChild(el('div','sub','A bar that has not moved looks identical to one that just '+
    'moved. This says which.'));
  return s}

function panelStandards(d){const s=el('section','wide');
  const S=d.standards||[];
  const bad=S.filter(x=>!x.holds);
  s.appendChild(el('h2',null,'Standards — where things stand against spec'));
  if(!S.length){s.appendChild(el('div','empty','Standards not readable.'));return s}
  const r=el('div','row');r.appendChild(el('span','label','met'));
  r.appendChild(el('span','value',(S.length-bad.length)+' of '+S.length));
  s.appendChild(r);s.appendChild(bar((S.length-bad.length)/S.length,''));
  const groups={};S.forEach(x=>{(groups[x.group]=groups[x.group]||[]).push(x)});
  const grid=el('div','sgrid');
  Object.keys(groups).forEach(g=>{
    const col=el('div','scol');col.appendChild(el('div','gname',g));
    groups[g].forEach(x=>{
      const row=el('div','srow '+(x.holds?'':'miss'));
      row.appendChild(el('span','sname',x.standard));
      row.appendChild(el('span','sval',String(x.observed)));
      row.appendChild(el('span','sfloor','floor '+x.floor));
      col.appendChild(row)});
    grid.appendChild(col)});
  s.appendChild(grid);
  if(bad.length){
    s.appendChild(el('div','sub','WORK ORDERS'));
    bad.sort((a,b)=>({high:0,medium:1,low:2}[a.severity]||3)-({high:0,medium:1,low:2}[b.severity]||3));
    bad.forEach(x=>{const o=el('div','order');
      o.appendChild(el('div','otitle','['+x.severity.toUpperCase()+'] '+x.standard+
        ' — observed '+x.observed+', floor '+x.floor));
      o.appendChild(el('div','obody',x.order));
      s.appendChild(o)})}
  return s}

function panelJobs(d){const s=el('section','wide');s.appendChild(el('h2',null,'Work in progress'));
  if(!d.jobs.length){s.appendChild(el('div','empty','No job is writing a progress line right now.'));return s}
  d.jobs.forEach(j=>{const f=j.total?j.done/j.total:0;
    const r=el('div','row');r.appendChild(el('span','label',j.name));
    r.appendChild(el('span','value',
      j.done.toLocaleString()+' / '+j.total.toLocaleString()+' '+j.unit+
      '  ·  '+pct(f)+'  ·  eta '+j.eta_h.toFixed(1)+'h'));
    s.appendChild(r);s.appendChild(bar(f,''));
    const sub=el('div','sub',j.detail);s.appendChild(sub);
    if(j.warn){const w=el('div','note',j.warn);s.appendChild(w)}});
  return s}

function panelQuota(d){const s=el('section');
  s.appendChild(el('h2',null,'Provider quota — what is left'));
  if(!d.quotas.length){s.appendChild(el('div','empty','No buckets reporting.'));return s}
  d.quotas.forEach(q=>{const b=el('div','bucket');
    const r=el('div','row');r.appendChild(el('span','label',q.bucket));
    const st=q.unlimited?'ok':(q.worst<=0.001?'dry':q.worst<0.2?'low':'ok');
    const txt=q.unlimited?'unlimited':(q.worst<=0.001?'exhausted':pct(q.worst)+' left');
    const p=el('span','pill '+st,txt);r.appendChild(p);b.appendChild(r);
    q.windows.forEach(w=>{const g=el('div','win');
      g.appendChild(el('div','n',w.name));g.appendChild(bar(w.frac,''));
      g.appendChild(el('div','v',w.left.toLocaleString()+'/'+w.cap.toLocaleString()));
      b.appendChild(g)});
    if(q.unlimited)b.appendChild(el('div','sub','local — no meter'));
    s.appendChild(b)});
  return s}

function panelSpend(d){const s=el('section');
  s.appendChild(el('h2',null,'Provider spend — last '+d.throughput.window_min+' minutes'));
  const r=el('div','row');r.appendChild(el('span','label','calls per hour'));
  r.appendChild(el('span','value',d.throughput.per_hour.toLocaleString()));s.appendChild(r);
  const t=el('table');
  if(!d.throughput.buckets.length){s.appendChild(el('div','empty','Nothing has called out recently.'));return s}
  d.throughput.buckets.forEach(b=>{const tr=el('tr');
    const a=el('td','k',b.bucket);const c=el('td',null,b.calls+' calls');
    const o=el('td',null,b.ok+' ok');tr.append(a,c,o);t.appendChild(tr)});
  s.appendChild(t);return s}

function panelMetrics(d){const s=el('section');
  s.appendChild(el('h2',null,'Call metrics — recent, per lane'));
  if(!d.metrics||!d.metrics.length){s.appendChild(el('div','empty','No instrumented calls yet.'));return s}
  const t=el('table');
  d.metrics.forEach(m=>{const tr=el('tr');
    tr.append(el('td','k',m.tag),el('td',null,m.n+' calls'),
      el('td',null,'p50 '+m.p50+'s / p95 '+m.p95+'s'),
      el('td',null,m.ok_pct==null?(m.tps==null?'':m.tps+' tok/s'):m.ok_pct+'% ok'));
    t.appendChild(tr)});
  s.appendChild(t);return s}

function panelLibrary(d){const s=el('section');s.appendChild(el('h2',null,'The library'));
  const L=d.library;
  if(L.coverage){const c=L.coverage;
    [['cited',c.cited,c.entries],['settled',c.settled,c.entries]].forEach(([k,v,n])=>{
      const r=el('div','row');r.appendChild(el('span','label',k));
      r.appendChild(el('span','value',v.toLocaleString()+' / '+n.toLocaleString()+
        '  ·  '+pct(v/n)));s.appendChild(r);s.appendChild(bar(v/n,''))});
    s.appendChild(el('div','sub',c.feats.toLocaleString()+' feats on record  ·  measured '+
      c.age_h+'h ago'))}
  if(L.sources){const q=L.sources;const t=el('table');
    [['sources with a host',q.with_host+' of '+q.total],
     ['entries reachable',q.entries_with_host.toLocaleString()],
     ['entries with no wiki',q.entries_without_host.toLocaleString()+
       ' in '+q.without_host+' sources'],
     ['entities read by the model',(L.readfeats||0).toLocaleString()]].forEach(([k,v])=>{
      const tr=el('tr');tr.append(el('td','k',k),el('td',null,v));t.appendChild(tr)});
    s.appendChild(t)}
  return s}

function panelSafety(d){const s=el('section','wide');
  const sf=d.safety||{};
  const h=sf.halted||{};
  s.appendChild(el('h2',null,'Safety'));
  // THE HALT IS THE HEADLINE. If the library has stopped itself, nothing else on this page
  // matters until a person rules on it, so it is rendered first, loud, and with the reason --
  // a halt whose cause you have to go and find is a halt that stays up longer than it should.
  if(h.halted){
    const b=el('div','row');
    b.appendChild(el('span','label','THE LIBRARY IS HALTED'));
    b.appendChild(el('span','value bad',(h.code||'?')));
    s.appendChild(b);
    s.appendChild(el('div','empty',(h.what||'no reason recorded — which is itself a fault')));
    const c=el('div','row');c.appendChild(el('span','label','raised by'));
    c.appendChild(el('span','value',(h.by||'?')+(h.source?(' · '+h.source):'')));
    s.appendChild(c);
    if(h.also){s.appendChild(el('div','empty',h.also+' further fault(s) recorded while halted'))}
    s.appendChild(el('div','empty',
      'Only a person may lift it:  python src/escalation.py --clear --ruling "…"'));
  }else{
    const b=el('div','row');b.appendChild(el('span','label','library'));
    b.appendChild(el('span','value ok','running — no halt standing'));s.appendChild(b);
  }
  // The prose gate. Closed is the CORRECT state right now; the page says which and why, so a
  // future reader does not mistake a deliberate hold for a broken pipeline.
  const g=sf.prose_gate||{};
  const gr=el('div','row');gr.appendChild(el('span','label','prose gate'));
  gr.appendChild(el('span','value '+(g.open?'warn':'ok'),
    g.open===undefined?'unknown':(g.open?'OPEN — books may be written':'closed (owner ruling)')));
  s.appendChild(gr);
  if(g.why){s.appendChild(el('div','empty',g.why))}
  const g4=sf.step4_gate||{};
  if(g4.open!==undefined){
    const r4=el('div','row');r4.appendChild(el('span','label','Step 4 gate'));
    r4.appendChild(el('span','value '+(g4.open?'warn':'ok'),
      g4.open?'OPEN — the entanglement pass may run':'closed (plan not ratified)'));
    s.appendChild(r4);
  }
  // The Assay calibration. Re-derived every poll against the charter's published worked example,
  // because this is the number every printed Magnitude inherits.
  const cal=sf.assay_calibration;
  if(cal){
    const cr=el('div','row');cr.appendChild(el('span','label','assay calibration'));
    cr.appendChild(el('span','value '+(cal.holds?'ok':'bad'),
      cal.holds?('charter reproduced — '+cal.decimal+' +/- '+cal.interval)
               :('DRIFTED — got '+cal.decimal+' +/- '+cal.interval
                 +', charter publishes '+cal.want_decimal+' +/- '+cal.want_interval)));
    s.appendChild(cr);
    if(cal.margin!=null){
      const mr=el('div','row');mr.appendChild(el('span','label','calibration margin'));
      mr.appendChild(el('span','value '+(cal.margin<0.25?'warn':''),cal.margin));
      s.appendChild(mr);
    }
  }
  // The drill. A count with no age is a claim about an unknown moment.
  const dr=sf.drill;
  if(!dr){s.appendChild(el('div','empty','no safety drill has run yet'))}
  else{
    const n=dr.nets||0,held=dr.held||0,br=(dr.breached||[]);
    const r=el('div','row');r.appendChild(el('span','label','safety drill'));
    r.appendChild(el('span','value '+(br.length?'bad':'ok'),
      held+' of '+n+' nets held'+(br.length?(' — '+br.length+' BREACHED'):'')));
    s.appendChild(r);
    s.appendChild(bar(n?held/n:0,br.length?'bad':'ok'));
    // EVERY breached net, not the first six. The row above already states the true count, so a
    // cap here made the page contradict itself: "10 BREACHED" over a list of six, with the four
    // that were hidden having no identity anywhere on the page. Same ruling as the open-findings
    // and swallowed-failures lists on 2026-08-24; this sibling was not visited then.
    br.forEach(x=>s.appendChild(el('div','empty','BREACHED: '+x)));
    const a=el('div','row');a.appendChild(el('span','label','last drilled'));
    a.appendChild(el('span','value '+(dr.age_min>90?'warn':''),
      (dr.age_min==null?'?':dr.age_min+' min ago')));
    s.appendChild(a);
    if(dr.liveness!=null){
      const lv=el('div','row');lv.appendChild(el('span','label','checks that cannot fail'));
      lv.appendChild(el('span','value '+((dr.liveness>dr.liveness_ceiling)?'bad':''),
        dr.liveness+' (ceiling '+dr.liveness_ceiling+')'));
      s.appendChild(lv);
    }
  }
  // Fetch manners: who we are slowing down for, and who has stopped answering.
  const ft=sf.fetch||{};
  const bo=ft.backoff||{}, qn=ft.quarantined||{};
  const nbo=Object.keys(bo).length, nqn=Object.keys(qn).length;
  if(nbo||nqn){
    const fr=el('div','row');fr.appendChild(el('span','label','fetch'));
    fr.appendChild(el('span','value '+(nqn?'warn':''),
      nbo+' host(s) backed off'+(nqn?(', '+nqn+' quarantined'):'')));
    s.appendChild(fr);
    // Every quarantined host, for the same reason: the label counts them all, and a host whose
    // name never appears cannot be un-quarantined by anyone reading this page.
    Object.keys(qn).forEach(h=>s.appendChild(el('div','empty',h+': '+qn[h])));
  }
  const esc=sf.escalation_recent||{};
  const keys=Object.keys(esc);
  if(keys.length){
    const t=el('table');
    t.appendChild((()=>{const tr=el('tr');tr.append(el('td','k','escalations, 24h'),
      el('td',null,keys.map(k=>k+' '+esc[k]).join(' · ')));return tr})());
    s.appendChild(t);
  }
  return s}

function panelPhases(d){const s=el('section');s.appendChild(el('h2',null,'Phases'));
  const ph=(d.library.phases)||[];
  if(!ph.length){s.appendChild(el('div','empty','Runner not readable.'));return s}
  const built=ph.filter(p=>p.built).length;
  const r=el('div','row');r.appendChild(el('span','label','implemented'));
  r.appendChild(el('span','value',built+' of '+ph.length));s.appendChild(r);
  s.appendChild(bar(built/ph.length,''));
  const t=el('table');ph.forEach(p=>{const tr=el('tr');
    tr.append(el('td','k',p.name),
      el('td',null,p.built?'built':'not built'));t.appendChild(tr)});
  s.appendChild(t);return s}

function panelWatch(d){const s=el('section','wide');
  s.appendChild(el('h2',null,'Overwatch — the standing sweep'));
  const w=d.watch;
  const r=el('div','row');r.appendChild(el('span','label','open findings'));
  r.appendChild(el('span','value',w.open+' ('+w.high+' high) after '+w.rounds+' round(s)'));
  s.appendChild(r);
  if(w.findings.length){const t=el('table');w.findings.forEach(f=>{const tr=el('tr');
    tr.append(el('td','k',f.module+'.py'),el('td',null,f.symbol||''),
      el('td',null,f.actual));t.appendChild(tr)});s.appendChild(t)}
  else s.appendChild(el('div','empty','Nothing open — every finding was fixed or retired when its file changed.'));
  if(w.swallowed&&w.swallowed.length){
    s.appendChild(el('div','sub','swallowed failures recorded: '+
      (w.swallowed_total||0).toLocaleString()));
    const t2=el('table');w.swallowed.forEach(([k,v])=>{const tr=el('tr');
      tr.append(el('td','k',k),el('td',null,v.toLocaleString()));t2.appendChild(tr)});
    s.appendChild(t2)}
  return s}

async function tick(){
  try{const d=await (await fetch('/api/state',{cache:'no-store'})).json();
    document.getElementById('stamp').textContent=d.at;
    const w=document.getElementById('wrap');w.innerHTML='';
    w.append(panelSafety(d),panelMovement(d),panelStandards(d),panelJobs(d),panelQuota(d),
             panelSpend(d),panelMetrics(d),panelLibrary(d),panelPhases(d),panelWatch(d));
  }catch(e){document.getElementById('stamp').textContent='server unreachable';}
}
tick();setInterval(tick,5000);
</script></body></html>"""


class Handler(http.server.BaseHTTPRequestHandler):
    def _send(self, body, ctype):
        raw = body.encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(raw)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(raw)

    def do_GET(self):
        if self.path.startswith("/api/state"):
            try:
                self._send(json.dumps(state()), "application/json; charset=utf-8")
            except Exception as e:
                silence.note("dashboard.py:state")
                self._send(json.dumps({"error": f"{type(e).__name__}: {str(e)[:120]}"}),
                           "application/json; charset=utf-8")
            return
        self._send(PAGE, "text/html; charset=utf-8")

    def log_message(self, *a):
        # Silent: this polls every five seconds and a request log would bury the console it
        # shares with everything else.
        return


class Server(socketserver.ThreadingTCPServer):
    allow_reuse_address = True
    daemon_threads = True


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
    ap = argparse.ArgumentParser(description="every meter in this project, on one page")
    ap.add_argument("--port", type=int, default=8777)
    ap.add_argument("--once", action="store_true", help="print the state as JSON and exit")
    a = ap.parse_args()
    if a.once:
        print(json.dumps(state(), indent=1))
        return 0
    # THE FINGERPRINT OF src/ AS THIS PROCESS FOUND IT, and it is taken only on the SERVING
    # path -- `--once` prints and exits, and a one-shot has no staleness to have. See the loop
    # below and codewatch.py. (order 1f172f5acc6f: this daemon had no codewatch call site, and
    # it had been up 12.3 hours when that was measured. The page a person reads the library's
    # state from was itself a photograph of the code as it stood when it started.)
    import codewatch
    codewatch.stamp("dashboard")
    with Server(("127.0.0.1", a.port), Handler) as srv:
        print(f"instruments on http://127.0.0.1:{a.port}   (ctrl-c to stop)")
        # `handle_request()` IN A LOOP RATHER THAN `serve_forever()`, so the staleness check has
        # somewhere to live. `serve_forever` never returns and offers no hook a reader of main()
        # can see, and a check hidden in a server callback is the kind nobody can find later.
        # `timeout` bounds the wait for a request, so an idle dashboard still notices a source
        # change within five seconds; `daemon_threads` means each request is already served off
        # this thread, so the loop turns over immediately under load too.
        srv.timeout = 5
        try:
            while True:
                srv.handle_request()
                # Exits rc=17 on purpose when src/ has changed and held still; the keeper's
                # STANDING set restarts this within five minutes on the current code. Budgeted
                # and settled, so an edit storm cannot turn this into a respawn loop.
                codewatch.exit_if_stale("dashboard")
        except KeyboardInterrupt:
            print("\nstopped")
    return 0


if __name__ == "__main__":
    sys.exit(main())
