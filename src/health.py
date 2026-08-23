#!/usr/bin/env python3
"""
HEALTH — make failures loud, because every bug in this project has been a quiet one.

THE PATTERN
-----------
Eleven separate defects were found in one day. Listed as a list they look like bad luck. Lined
up by SHAPE they are one defect:

    Wikipedia served 404              ->  looked like "these entities have no page"
    chunks overflowed num_ctx         ->  looked like "the model fabricates 51% of the time"
    a word-boundary escape became 0x08 ->  looked like "the gate is too strict"
    a batch closed on write not result ->  looked like "judged"
    failed synthesis wrote an empty block -> looked like "no ceiling exists here"
    the gate could only see Ruin       ->  looked like "no evidence on ten axes"

Every layer converts a failure into a plausible NEGATIVE RESULT. Nothing raises, nothing counts,
and so every one of them costs a full investigation to tell "broken" apart from "genuinely
empty". There are 45 bare `except Exception` handlers in this tree, and that number is the real
bug; the eleven were its output.

WHAT THIS DOES
--------------
Two things, neither of which requires rewriting those 45 handlers:

  A LEDGER. The transport layer records why a call failed instead of only that it did. A run
  that 404s 5,590 times now says so at the end rather than reporting 5,590 honest absences.

  A PREFLIGHT. Cheap assertions, run BEFORE a job commits hours, aimed at the exact classes of
  fault already seen: does the context arithmetic hold, does each host family answer on the API
  path we use for it, is any module carrying a control character where an escape should be, is
  a cache systematically empty in a way that means broken rather than absent.

The preflight would have caught the Wikipedia path, the chunk overflow and every escape
corruption before they cost a day each.
"""
import argparse
import collections
import glob
import json
import os
import sys
import threading

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

_BAD_CHARS = (chr(8), chr(11), chr(12), chr(7))
if any(c in open(os.path.abspath(__file__), encoding="utf-8").read() for c in _BAD_CHARS):
    raise SystemExit(__file__ + ": a regex escape was eaten in transit.")

# A feats record with no pages serialises to roughly 200 bytes; one with a single
# page runs to kilobytes. Anything under this threshold held nothing.
EMPTY_BYTES = 400

LEDGER = collections.Counter()
_LOCK = threading.Lock()
LEDGER_PATH = os.path.join(HERE, "state", "failures.json")


def record(kind, detail=""):
    """Note a failure by CLASS. The class is what makes a pattern visible; the instance does not."""
    with _LOCK:
        LEDGER[f"{kind}:{detail}" if detail else kind] += 1


def flush():
    if not LEDGER:
        return
    os.makedirs(os.path.dirname(LEDGER_PATH), exist_ok=True)
    prev = {}
    if os.path.exists(LEDGER_PATH):
        try:
            with open(LEDGER_PATH, encoding="utf-8") as f:
                prev = json.load(f)
        except Exception as e:
            # An unreadable ledger must not be quietly replaced by an empty one -- that would
            # make the failure-recorder itself the sixteenth instance of the defect it exists
            # to expose. Keep the corrupt file and say so.
            os.replace(LEDGER_PATH, LEDGER_PATH + ".corrupt")
            prev = {"ledger:unreadable": 1}
            print(f"health: ledger unreadable ({type(e).__name__}); "
                  f"kept as failures.json.corrupt", file=sys.stderr)
    for k, v in LEDGER.items():
        prev[k] = prev.get(k, 0) + v
    with open(LEDGER_PATH, "w", encoding="utf-8") as f:
        json.dump(prev, f, indent=1, sort_keys=True)
    LEDGER.clear()


def summary():
    if os.path.exists(LEDGER_PATH):
        with open(LEDGER_PATH, encoding="utf-8") as f:
            return json.load(f)
    return {}


# --------------------------------------------------------------------------- preflight

def check_control_chars():
    """A regex escape eaten in transit. Six occurrences so far, every one silent."""
    bad = []
    for p in sorted(glob.glob(os.path.join(HERE, "src", "*.py"))):
        with open(p, encoding="utf-8") as f:
            src = f.read()
        hits = sum(src.count(c) for c in _BAD_CHARS)
        if hits:
            bad.append((os.path.basename(p), hits))
    return bad


def check_context_budget():
    """Does the chunk actually fit the window it is sent to?

    Ollama does not refuse an overlong prompt, it truncates silently -- so this is arithmetic
    nobody is told they got wrong. English wiki prose runs ~3.7 characters per token.
    """
    try:
        import read as R
        cfg = R.config()
    except Exception as e:
        return [("read.py config unreadable", str(e)[:60])]
    ctx = cfg.get("num_ctx", 6144)
    sys_toks = len(R.SYSTEM) / 4
    body_toks = R.CHUNK / 3.7
    reply = 700
    total = sys_toks + body_toks + reply
    if total > ctx:
        return [("chunk overflows context",
                 f"{int(total)} tokens needed vs num_ctx {ctx} "
                 f"(CHUNK={R.CHUNK} chars) - the tail is silently truncated")]
    return []


def check_api_paths():
    """One live call per host FAMILY, on the path that family is actually served from.

    Fandom answers at /api.php and Wikipedia at /w/api.php. Using one for the other returns 404,
    which the transport swallows into None, which reads as 'no page'. That cost 5,590 entries
    across nineteen sources and looked exactly like an honest absence.
    """
    out = []
    try:
        import feats as F
        hosts = json.load(open(F.HOSTS, encoding="utf-8"))
    except Exception as e:
        return [("host map unreadable", str(e)[:60])]
    fams = {}
    for h in hosts.values():
        if not h:
            continue
        fams.setdefault("wikipedia" if "wikipedia" in h else "fandom", h)
    for fam, host in fams.items():
        d = F.api(host, {"action": "query", "meta": "siteinfo"}, retries=0)
        if not d or "query" not in d:
            out.append((f"{fam} API unreachable", host))
    return out


def check_caches():
    """A cache that is systematically empty means broken, not absent.

    An empty entry is normal. An entire host directory of empty entries is the 404 signature.
    """
    out = []
    for base in ("feats", "readfeats"):
        root = os.path.join(HERE, "data", base)
        if not os.path.isdir(root):
            continue
        for host in sorted(os.listdir(root)):
            files = glob.glob(os.path.join(root, host, "*.json"))
            if len(files) < 25:
                continue
            # SIZE, NOT PARSE. Preflight runs at the head of every supervisor cycle, and
            # parsing 200 records for each of 147 hosts meant reading gigabytes of page text to
            # answer a question about emptiness. It pushed a cycle past five minutes before any
            # work began. An entry with no pages is a few hundred bytes; one with pages is
            # kilobytes at least. The file size answers this exactly, and instantly.
            empty = 0
            unreadable = 0
            for fp in files[:200]:
                try:
                    if os.path.getsize(fp) < EMPTY_BYTES:
                        empty += 1
                except OSError:
                    unreadable += 1
            if unreadable:
                out.append((f"{base}/{host} cache unreadable",
                            f"{unreadable} files cannot be stat'd"))
            n = min(len(files), 200)
            if empty == n:
                out.append((f"{base}/{host}", f"all {n} sampled entries empty"))
    return out


def check_state():
    """Batches recorded complete that are not, and failures recorded that are not."""
    out = []
    try:
        import pipeline as P
        st = json.load(open(os.path.join(HERE, "state", "PIPELINE_STATE.json"),
                            encoding="utf-8"))
    except Exception as e:
        return [("state unreadable", str(e)[:60])]
    done = set(st.get("done", {}).get("entrypass", []))
    B = P.ENTRY_BATCH
    orphan = 0
    for _, r in P.records():
        E = r["entries"]
        for start in range(0, len(E), B):
            if f"{r['source']}#{start}" in done:
                orphan += sum(1 for e in E[start:start + B] if not e.get("catalogued"))
    if orphan:
        out.append(("entries stranded in closed batches", str(orphan)))
    stale = 0
    for src in st.get("failed", {}).get("synthesis", {}):
        rec = next((r for _, r in P.records() if r["source"] == src), None)
        if rec and (rec.get("synthesis") or {}).get("ceiling_entity"):
            stale += 1
    if stale:
        out.append(("failures recorded that already succeeded", str(stale)))
    return out


def reopen_stranded(dry=True):
    """Re-open entry batches marked done that still contain uncatalogued entries.

    A batch once closed on WRITE rather than on RESULT, which stranded 378 entries permanently:
    the key said done, the entries said uncatalogued, and nothing in the pipeline ever looked at
    both. The write bug is fixed; this clears what it left behind, and stays because the same
    shape can recur any time a stage is interrupted between its work and its bookkeeping.

    Removing a key only causes rework. Nothing is deleted and nothing is fabricated -- the batch
    simply becomes eligible again.
    """
    import pipeline as P
    path = os.path.join(HERE, "state", "PIPELINE_STATE.json")
    with open(path, encoding="utf-8") as f:
        st = json.load(f)
    done = st.get("done", {}).get("entrypass", [])
    doneset = set(done)
    B = P.ENTRY_BATCH
    reopen, entries = [], 0
    for _, r in P.records():
        E = r["entries"]
        for start in range(0, len(E), B):
            key = f"{r['source']}#{start}"
            if key not in doneset:
                continue
            missing = sum(1 for e in E[start:start + B] if not e.get("catalogued"))
            if missing:
                reopen.append(key)
                entries += missing
    if not reopen:
        print("no stranded batches")
        return []
    verb = "would re-open" if dry else "re-opened"
    print(f"{verb} {len(reopen)} batch(es) holding {entries} uncatalogued entries")
    for k in reopen[:20]:
        print("   " + k)
    if not dry:
        st["done"]["entrypass"] = [k for k in done if k not in set(reopen)]
        with open(path, "w", encoding="utf-8") as f:
            json.dump(st, f, indent=1)
        print("-> PIPELINE_STATE.json")
    return reopen


CHECKS = [
    ("control characters in source", check_control_chars),
    ("context budget", check_context_budget),
    ("API paths per host family", check_api_paths),
    ("caches empty in a way that means broken", check_caches),
    ("state consistency", check_state),
]


def preflight(verbose=True):
    problems = 0
    for label, fn in CHECKS:
        try:
            found = fn()
        except Exception as e:
            found = [("check itself failed", f"{type(e).__name__} {str(e)[:60]}")]
        if found:
            problems += len(found)
            if verbose:
                print(f"  FAIL  {label}")
                for a, b in found:
                    print(f"          {a}: {b}")
        elif verbose:
            print(f"  ok    {label}")
    return problems


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--reopen", action="store_true",
                    help="re-open entry batches marked done that hold uncatalogued entries")
    ap.add_argument("--go", action="store_true", help="with --reopen, actually write")
    ap.add_argument("--preflight", action="store_true")
    ap.add_argument("--failures", action="store_true")
    a = ap.parse_args()
    if a.reopen:
        reopen_stranded(dry=not a.go)
        return 0
    if a.failures:
        s = summary()
        if not s:
            print("no failures recorded")
            return 0
        print(f"{'count':>8}  class")
        for k, v in sorted(s.items(), key=lambda kv: -kv[1]):
            print(f"{v:>8}  {k}")
        return 0
    print("PREFLIGHT")
    n = preflight()
    print(f"\n{n} problem(s)" if n else "\nall checks pass")
    return 1 if n else 0


if __name__ == "__main__":
    sys.exit(main())
