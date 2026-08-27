#!/usr/bin/env python3
"""
COVERAGE — does every source, and everything inside it, carry a citation?

The goal is one sentence: every entry in the library traces to a sentence in a real source page.
Not a band, not a paraphrase, not the model's recollection -- a quotable line with the page it
came from. This measures how far from that we are, per source, and says what is stopping each
one, because "37% covered" is a number you cannot act on and "this source has no wiki host" is.

Every entry sits in exactly one state:

    CITED        at least one verbatim feat mined from its own source page
    READ         pages were fetched and read, and honestly contained no feat.
                 This is a RESULT, not a gap. A tavern has no feats. A Pixar side character has
                 no feats. The library saying so with the pages read is a finding.
    NO PAGE      the wiki was ASKED and has no article under this name
    NOT ATTEMPTED nothing has ever fetched this entity. NOT a finding about the wiki --
                 a finding about US. Split out 2026-08-25 after 30,102 of Marvel's 30,207
                 entries were reported as "no article" when nothing had ever asked.
    NO HOST      the source has no wiki at all
    UNREACHABLE  a host exists but the fetch failed -- the only state that is purely a defect

The distinction between READ and NO PAGE is the whole point of the file. Collapsing them is what
made every silent failure in this project look like an honest absence.
"""
import argparse
import collections
import json
import os
import sys

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import pipeline as P                                                    # noqa: E402
import feats as F                                                       # noqa: E402
import cachekey
import silence

_BAD_CHARS = (chr(8), chr(11), chr(12), chr(7))
if any(c in open(os.path.abspath(__file__), encoding="utf-8").read() for c in _BAD_CHARS):
    raise SystemExit(__file__ + ": a regex escape was eaten in transit.")

OUT = os.path.join(HERE, "data", "COVERAGE.json")
READ_CACHE = os.path.join(HERE, "data", "readfeats")


def _p(base, host, name):
    """The entity's natural cache path. M23: reads through here MUST verify ownership.

    This function used to be the whole answer, and it is lossy -- `Magic 8 Ball` and
    `Magic 8-Ball` return the same path. `measure()` therefore counted one entity's mined feats
    as evidence for BOTH, inflating CITED on either side of every collision. `state_of()` now
    verifies via `cachekey.owns()` before believing a file.
    """
    return cachekey.natural_path(base, host, name)


# Per-file result cache, mtime-keyed and persisted. state_of() only ever wants two list
# LENGTHS, but the evidence files are 95% page text -- measure() was deserializing on the
# order of the whole 874MB corpus per run, several runs a day (round-2 optimization audit,
# finding 2). A file re-parses only when its mtime moves; everything else is a dict hit.
_SO_CACHE_P = os.path.join(HERE, "state", "coverage_cache.json")
_SO = {"loaded": False, "d": {}, "dirty": 0}


def _so_load():
    if not _SO["loaded"]:
        try:
            with open(_SO_CACHE_P, encoding="utf-8") as f:
                _SO["d"] = json.load(f)
        except Exception:
            _ = "silence-exempt: no cache yet is the normal first state"
        _SO["loaded"] = True
    return _SO["d"]


def _so_save():
    if not _SO["dirty"]:
        return
    try:
        import silence as _sil
        tmp = _SO_CACHE_P + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(_SO["d"], f)
        # ADVANCE ON THE WRITE, NOT ON THE INTENT: replace_retry returns False (never raises) on
        # persistent denial, so `dirty` must only clear when the rename actually landed. Clearing
        # it unconditionally told the process its mtime cache was on disk when it was not, and
        # the next run re-parsed the whole evidence corpus to rebuild what this cache exists to
        # avoid (see the comment above _SO_CACHE_P).
        if _sil.replace_retry(tmp, _SO_CACHE_P):
            _SO["dirty"] = 0
    except Exception:
        silence.note("coverage.py:so-save")


def state_of(host, name):
    """(state, n_feats, n_pages) for one entry."""
    if not host:
        return "NO HOST", 0, 0
    cache = _so_load()
    # NOT_ATTEMPTED IS ITS OWN STATE, and conflating it with NO PAGE was this module's oldest
    # lie. The report prints NO PAGE as "no article under this name" -- a claim about the WIKI --
    # while the code reached it by default, whenever no cache file existed. Measured 2026-08-24:
    # 42,582 entries were reported that way, and **30,102 of them were Marvel**, which had 30,207
    # entries and 3,181 cache files. Those articles all exist; nothing had fetched them. Anyone
    # reading the coverage table would conclude the corpus was near-exhausted when it was ~12%
    # attempted. (Trivy draws the same distinction and for the same reason: "not scanned" and
    # "scanned, clean" are different findings and must never share a cell.)
    best = ("NOT ATTEMPTED", 0, 0)
    for base in (READ_CACHE, F.CACHE):
        for fp in cachekey.candidate_paths(base, host, name):
            st_np = _state_of_file(fp, name, cache)
            if st_np is None:
                continue
            st, nf, np = st_np
            # STRICT PRECEDENCE: CITED > READ > NO PAGE > NOT ATTEMPTED. The first version of
            # this loop only ever promoted to READ, so a cache file with zero pages -- a genuine
            # "we asked and the wiki has nothing" -- fell through and was reported as NOT
            # ATTEMPTED. The whole point of splitting the two states is lost if one of them can
            # never be reached, and `measure()` duly reported **no_page: 0** across the entire
            # corpus while 2,003 cache files sat on disk with empty page lists. A state that
            # cannot occur is a check that cannot fail, arriving inside the fix for a check that
            # could not fail.
            if st == "CITED":
                return "CITED", nf, np
            if st == "READ":
                best = ("READ", 0, np)
            elif st == "NO PAGE" and best[0] == "NOT ATTEMPTED":
                best = ("NO PAGE", 0, 0)
    return best


def _state_of_file(fp, name, cache):
    """-> (state, n_feats, n_pages) for ONE candidate file, or None if it is not usable.

    Split out of `state_of` so the ownership check has exactly one home. M23: a file is only
    this entity's evidence if it says so.
    """
    try:
        mt = os.path.getmtime(fp)
    except OSError:
        return None
    # M23: the memo is keyed by PATH **and NAME**. Keying it by path alone was a second copy of
    # the same bug one layer up -- two entities that share a path would also share the memo, so
    # the ownership check below would be skipped for whichever asked second.
    rel = os.path.relpath(fp, HERE) + "|" + name
    hit = cache.get(rel)
    if hit and hit[0] == mt:
        if hit[1] == "NOT_MINE":
            return None
        return hit[1], hit[2], hit[3]
    try:
        with open(fp, encoding="utf-8") as f:
            d = json.load(f)
    except Exception:
        silence.note("coverage.py:state_of_file-read")
        return None
    if not cachekey.owns(d, name):
        # Someone else's evidence sitting at our path. NOT this entity's citation.
        cache[rel] = [mt, "NOT_MINE", 0, 0]
        _SO["dirty"] += 1
        return None
    pages = d.get("pages_read") or d.get("pages") or []
    feats = d.get("feats") or []
    st = "CITED" if feats else ("READ" if pages else "NO PAGE")
    nf, np = len(feats), len(pages)
    cache[rel] = [mt, st, nf, np]
    _SO["dirty"] += 1
    return st, nf, np


def measure():
    hosts = json.load(open(F.HOSTS, encoding="utf-8"))
    _so_load()
    rows = []
    for _, r in P.records():
        host = hosts.get(r["source"])
        c = collections.Counter()
        feats = 0
        for e in r["entries"]:
            st, nf, _ = state_of(host, e["name"])
            c[st] += 1
            feats += nf
        n = len(r["entries"])
        rows.append({"source": r["source"], "host": host, "entries": n,
                     "cited": c["CITED"], "read": c["READ"],
                     "no_page": c["NO PAGE"], "no_host": c["NO HOST"],
                     "not_attempted": c["NOT ATTEMPTED"],
                     "feats": feats,
                     "coverage": c["CITED"] / max(n, 1),
                     "settled": (c["CITED"] + c["READ"]) / max(n, 1)})
    _so_save()
    return rows


def report(rows, show=None):
    n = sum(r["entries"] for r in rows)
    cited = sum(r["cited"] for r in rows)
    read = sum(r["read"] for r in rows)
    nopage = sum(r["no_page"] for r in rows)
    untried = sum(r.get("not_attempted", 0) for r in rows)
    nohost = sum(r["no_host"] for r in rows)
    feats = sum(r["feats"] for r in rows)
    print("=" * 84)
    print(f"CITATION COVERAGE — {n:,} entries across {len(rows)} sources")
    print("=" * 84)
    print(f"\n  CITED       {cited:>8,}  {cited/n:>6.1%}   carries a verbatim feat")
    print(f"  READ        {read:>8,}  {read/n:>6.1%}   pages read, honestly no feat")
    print(f"  NO PAGE     {nopage:>8,}  {nopage/n:>6.1%}   asked; the wiki has no such article")
    print(f"  NOT TRIED   {untried:>8,}  {untried/n:>6.1%}   nothing has ever fetched this")
    print(f"  NO HOST     {nohost:>8,}  {nohost/n:>6.1%}   source has no wiki")
    print(f"  {'-'*46}")
    print(f"  SETTLED     {cited+read:>8,}  {(cited+read)/n:>6.1%}   "
          f"looked at and answered either way")
    print(f"\n  total feats on record: {feats:,}")

    hostless = sorted((x for x in rows if not x["host"]), key=lambda x: -x["entries"])
    print(f"\nSOURCES WITH NO WIKI HOST — nothing can ever be cited here ({len(hostless)}, all shown)")
    for r in hostless:
        print(f"   {r['entries']:>6,}  {r['source'][:58]}")

    have = [r for r in rows if r["host"] and r["entries"] >= 40]
    worst = sorted(have, key=lambda x: (x["coverage"], -x["entries"]))
    limit = show if show is not None else len(worst)
    if limit < len(worst):
        print(f"\nWORST COVERED WITH A HOST — where the work is "
              f"(showing {limit} of {len(worst)}; {len(worst) - limit} more not shown, --show to raise)")
    else:
        print(f"\nWORST COVERED WITH A HOST — where the work is ({len(worst)}, all shown)")
    for r in worst[:limit]:
        print(f"   {r['coverage']:>6.1%} cited  {r['settled']:>6.1%} settled  "
              f"{r['entries']:>6,} entries   {r['source'][:44]}")

    print("\nBEST COVERED")
    for r in sorted(have, key=lambda x: -x["coverage"])[:10]:
        print(f"   {r['coverage']:>6.1%} cited  {r['feats']:>6,} feats  "
              f"{r['entries']:>6,} entries   {r['source'][:44]}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--show", type=int, default=None,
                     help="cap the WORST COVERED list to N rows (announced, not silent); "
                          "omit to print all of them")
    a = ap.parse_args()
    rows = measure()
    report(rows, show=a.show)
    # ATOMIC: COVERAGE.json holds the library's headline figures and is read by the dashboard,
    # standards, allsweep and the published page. This file's own cache-save two functions
    # above already lands atomically; the headline write did not. 2026-08-25.
    silence.write_json(OUT, rows, indent=1, ensure_ascii=False)
    print(f"\nper-source table -> {OUT}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
