#!/usr/bin/env python3
"""
SWEEP — every character in the library, measured against every system built for them.

The corpus holds 17,444 entries classed Persons. Each one is supposed to end up carrying an
address, a Magnitude band, a worksheet of cited feats, and a place in its own fiction's native
scale. Four separate machines produce those, they were built at different times, and nothing has
ever joined them and asked what fraction of characters actually clears each stage.

This does that join and prints the funnel:

    catalogued   the entry exists and phase 2 judged it
    addressed    its source is shelved, so a Shelfmark can be issued
    reachable    its source resolves to a wiki host
    read         pages were fetched and cached for it
    evidenced    at least one of the eleven axis gates found something
    assayable    enough axes to produce a decimal rather than a band alone
    ranked       its own fiction publishes a scale position for it (Rosetta)

Each stage is a strictly smaller set than the one above, and the size of each drop is the real
statement of where the project stands. A number that only ever gets reported at the top of the
funnel is a number that hides the four stages below it.
"""
import argparse
import collections
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import pipeline as P                                                    # noqa: E402
import feats as F                                                       # noqa: E402
import magnitude as M                                                   # noqa: E402
import silence

# A regex escape arriving as a literal control character matches nothing and fails SILENTLY.
# A word-boundary escape written through a shell heredoc has arrived here as a 0x08 backspace
# five separate times in this project. Each time it read as a tuning problem -- a gate that
# passed nothing, a parser that found zero rows -- rather than as corruption, which is what
# makes it expensive. The check is built from chr() codes because the first version was
# written with escapes and they were eaten too, so it flagged its own source and refused.
_BAD_CHARS = (chr(8), chr(11), chr(12), chr(7))
if any(c in open(os.path.abspath(__file__), encoding='utf-8').read() for c in _BAD_CHARS):
    raise SystemExit(__file__ + ': a regex escape was eaten in transit - a literal control '
                     'character is present in the source. Repair before running.')


OUT = os.path.join(HERE, "data", "CHARACTER_SWEEP.json")
PERSON = re.compile(r"^Persons", re.I)


def _norm(s):
    return re.sub(r"[^a-z0-9]+", " ", (s or "").lower()).strip()


def cache_path(host, name):
    return os.path.join(F.CACHE, re.sub(r"[^A-Za-z0-9]+", "_", host)[:40],
                        re.sub(r"[^A-Za-z0-9]+", "_", name)[:80] + ".json")


def load(path):
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        silence.note("sweep.py:66")
        return None


def rosetta_index():
    """{normalised name: (scale title, value, rank-within-scale)} across every mined scale."""
    p = os.path.join(HERE, "data", "ROSETTA.json")
    if not os.path.exists(p):
        return {}
    idx = {}
    for host, scales in json.load(open(p, encoding="utf-8")).items():
        for title, sc in scales.items():
            ordered = sorted(sc["values"].items(), key=lambda kv: -kv[1])
            for rank, (name, val) in enumerate(ordered, 1):
                k = _norm(name)
                # A character graded on more than one scale keeps the finer-grained one, which is
                # the larger table: a 91-row bounty list places someone better than a 13-row one.
                if k not in idx or sc["n"] > idx[k][3]:
                    idx[k] = (title, val, rank, sc["n"])
    return idx


def navtree_names():
    p = os.path.join(HERE, "data", "NAVTREE.json")
    if not os.path.exists(p):
        return {}, {}
    nav = json.load(open(p, encoding="utf-8"))
    where = {}
    for key, node in nav["nodes"].items():
        for src in (node.get("s") or []):
            where[src] = key
    names = {k: v.get("name", k) for k, v in nav["nodes"].items()}
    return where, names


def sweep():
    recs = P.records()
    hosts = json.load(open(F.HOSTS, encoding="utf-8")) if os.path.exists(F.HOSTS) else {}
    ros = rosetta_index()
    where, names = navtree_names()

    rows = []
    for _, r in recs:
        src = r["source"]
        host = hosts.get(src)
        key = where.get(src)
        shelf = None
        if key:
            parts = key.split(".")
            shelf = " › ".join(names.get(".".join(parts[:i + 1]), "?")
                               for i in range(len(parts)))
        for e in r["entries"]:
            if not PERSON.search(e.get("category") or ""):
                continue
            row = {"name": e["name"], "source": src, "host": host,
                   "shelfmark": shelf,
                   "catalogued": bool(e.get("catalogued")),
                   "band": e.get("magnitude", "unassayed"),
                   "pages": 0, "chars": 0, "axes": 0, "quantities": 0,
                   "axis_list": [], "native": None}
            if host:
                ev = load(cache_path(host, e["name"]))
                if ev:
                    row["pages"] = len(ev.get("pages_read") or [])
                    row["chars"] = ev.get("chars_read", 0)
                    row["quantities"] = len(ev.get("quantities") or [])
                    if ev.get("text"):
                        cand = M.candidates(ev)
                        row["axis_list"] = sorted(a for a, v in cand.items() if v)
                        row["axes"] = len(row["axis_list"])
            hit = ros.get(_norm(e["name"]))
            if hit:
                row["native"] = {"scale": hit[0], "value": hit[1], "rank": hit[2], "of": hit[3]}
            rows.append(row)
    return rows


def report(rows, top=18):
    n = len(rows)
    f = {
        "catalogued": sum(1 for r in rows if r["catalogued"]),
        "addressed": sum(1 for r in rows if r["shelfmark"]),
        "reachable": sum(1 for r in rows if r["host"]),
        "read": sum(1 for r in rows if r["pages"]),
        "evidenced": sum(1 for r in rows if r["axes"]),
        "assayable": sum(1 for r in rows if r["axes"] >= 2),
        "ranked": sum(1 for r in rows if r["native"]),
        "banded": sum(1 for r in rows if r["band"] not in ("unassayed", "", None)),
    }
    print("=" * 88)
    print(f"CHARACTER SWEEP — {n:,} entries classed Persons across {len({r['source'] for r in rows})} sources")
    print("=" * 88)
    print(f"\n{'stage':<14}{'count':>9}{'of all':>9}  {'':<24}")
    prev = n
    for k in ("catalogued", "addressed", "reachable", "read", "evidenced", "assayable"):
        drop = prev - f[k]
        bar = "#" * int(38 * f[k] / max(n, 1))
        print(f"  {k:<12}{f[k]:>9,}{f[k]/n:>8.1%}  {bar}"
              + (f"   -{drop:,}" if drop else ""))
        prev = f[k]
    print(f"\n  {'ranked':<12}{f['ranked']:>9,}{f['ranked']/n:>8.1%}   "
          f"(own fiction publishes a scale position)")
    print(f"  {'banded':<12}{f['banded']:>9,}{f['banded']/n:>8.1%}   "
          f"(carries a Magnitude today)")

    print("\nAXES EVIDENCED PER CHARACTER")
    d = collections.Counter(r["axes"] for r in rows)
    for k in sorted(d):
        print(f"   {k:>2} axes  {d[k]:>7,}  {'#' * int(46 * d[k] / max(n, 1))}")

    print("\nWHICH AXES ARE FINDING EVIDENCE")
    ax = collections.Counter(a for r in rows for a in r["axis_list"])
    for a, c in ax.most_common():
        print(f"   {a:<15}{c:>7,}  {c/max(f['read'],1):>6.1%} of characters read")

    print("\nDEEPEST EVIDENCE — the characters most ready to assay")
    best = sorted(rows, key=lambda r: (-r["axes"], -r["quantities"], -r["chars"]))[:top]
    print(f"   {'axes':>4}{'qty':>5}{'chars':>10}   {'character':<30}{'source':<26}native")
    for r in best:
        nat = f"{r['native']['value']:,.0f} (#{r['native']['rank']})" if r["native"] else ""
        print(f"   {r['axes']:>4}{r['quantities']:>5}{r['chars']:>10,}   "
              f"{r['name'][:29]:<30}{r['source'][:25]:<26}{nat}")

    print("\nBIGGEST GAPS — sources whose characters are unreachable")
    gap = collections.Counter(r["source"] for r in rows if not r["host"])
    for s, c in gap.most_common(10):
        print(f"   {c:>6,}  {s[:60]}")

    print("\nREACHED BUT SILENT — read, yet no axis found anything")
    sil = [r for r in rows if r["pages"] and not r["axes"]]
    bysrc = collections.Counter(r["source"] for r in sil)
    print(f"   {len(sil):,} characters ({len(sil)/max(f['read'],1):.0%} of those read)")
    for s, c in bysrc.most_common(8):
        print(f"   {c:>6,}  {s[:60]}")
    return f


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--top", type=int, default=18)
    a = ap.parse_args()
    rows = sweep()
    report(rows, top=a.top)
    with open(OUT, "w", encoding="utf-8") as f:
        json.dump(rows, f, ensure_ascii=False)
    print(f"\nfull table -> {OUT}  ({os.path.getsize(OUT)//1024:,} KB)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
