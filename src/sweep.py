#!/usr/bin/env python3
"""
SWEEP — every character in the library, measured against every system built for them.

The corpus holds 17,444 entries classed Persons. Each one is supposed to end up carrying an
address, a Magnitude band, a worksheet of cited feats, and a place in its own fiction's native
scale. Four separate machines produce those, they were built at different times, and nothing has
ever joined them and asked what fraction of characters actually clears each stage.

This does that join and prints what each machine has reached:

    catalogued   the entry exists and phase 2 judged it
    addressed    its source is shelved, so a Shelfmark can be issued
    reachable    its source resolves to a wiki host
    read         pages were fetched and cached for it
    evidenced    at least one of the eleven axis gates found something
    assayable    enough axes to produce a decimal rather than a band alone
    ranked       its own fiction publishes a scale position for it (Rosetta)

NOT ALL OF THOSE ARE FUNNEL STAGES, AND THE FILE USED TO SAY THEY WERE (order 2420550a2b8e).
The claim here was "each stage is a strictly smaller set than the one above". Against the live
sweep it is false and not by a rounding: catalogued = 44,185 while addressed = 144,452 and
reachable = 144,488. Those are not nested; `catalogued` is phase 2's judgement, a property of
the ENTRY, while `addressed` and `reachable` are properties of the entry's SOURCE, and 100,343
entries sit in the second and not the first. The drawing did not merely round the picture off:
the drop line computed `prev - count` and printed `-{drop:,}`, so a negative drop rendered as
the garbled `--100,267`, and the bar for `addressed` -- 99.9% of the corpus -- was drawn
immediately below a 30% bar as though nothing had been lost at the widest gate in the report.
The stage that lost the most looked like the stage that lost nothing.

So the report no longer asserts nesting; it TESTS it, in `report()`, against the rows in hand,
and draws a funnel over the longest genuinely nested run of stages it finds. Everything outside
that run is printed as its own population with the crossover counts stated, because two
overlapping populations reported as one chain is not an imprecise picture, it is an inverted
one. Nothing is hidden by this: every count that was printed before is still printed.
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
import cachekey
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
    """The entity's NATURAL cache path. Delegates -- one spelling of this key (M23).

    Callerless since the sweep's own read moved to `cachekey.load`. Kept and delegating rather
    than deleted, so it cannot drift back out of step with the real formula.
    """
    return cachekey.natural_path(F.CACHE, host, name)


def load(path):
    """Read one evidence cache file, or None if there isn't one yet.

    THE ABSENT FILE IS THE NORMAL PATH, NOT A FAILURE. The only call site (`:129`) asks for the
    evidence of every Person-category entry in the library and does no existence check first, so
    every character the reader has not reached yet raises FileNotFoundError here. That is the
    expected majority: ~45,000 entries against ~1,200 readfeats records on 2026-08-25.

    Recording those as swallowed failures made the ledger useless as an alarm. Measured that day:
    18,418 of 21,764 entries in the whole project's swallowed-failure ledger -- 85% -- came from
    this one handler, and the "unexpected swallowed failures" standard sat red at 19,043 against
    a floor of 2,000 purely because of them. A standard that is always red reports nothing.

    Worse than the noise: a CORRUPT cache file (a truncated write, a JSONDecodeError) is a real
    fault and was landing in the same bucket as those 18,418 non-events, where nobody would ever
    pick it out. Splitting the two does not hide a failure -- it is the only way the real one
    becomes visible. The genuine path is still noted, now under a semantic label rather than a
    line number that goes stale the moment anything above it moves. 2026-08-25, run #21.
    """
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        # Expected by construction -- see the docstring. Deliberately unrecorded.
        _ = "silence-exempt: an unbuilt evidence cache is the normal case at this call site"
        return None
    except Exception:
        silence.note("sweep.py:load-unreadable")
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
                # M23: verified read. `cache_path` below still exists for callers that want the
                # natural path, but a SWEEP that credits one entity with a neighbour's pages
                # feeds CHARACTER_SWEEP.json, which magnitude, standards, foreman and hostcheck
                # all read as fact.
                # on_corrupt: an unreadable cache file must not read the same as "nothing was
                # ever mined" (sweep.load's docstring above is the whole argument for this).
                ev, _ = cachekey.load(F.CACHE, host, e["name"],
                                       on_corrupt=lambda fp: silence.note("sweep.py:evidence-unreadable"))
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


# The stages in the order the project runs them. Membership is by MEMBER, not by count, so the
# nesting question can actually be asked instead of guessed at from two totals.
STAGE_TESTS = (
    ("catalogued", lambda r: bool(r["catalogued"]), "phase 2 judged the entry"),
    ("addressed", lambda r: bool(r["shelfmark"]), "its source is shelved, so a Shelfmark can issue"),
    ("reachable", lambda r: bool(r["host"]), "its source resolves to a wiki host"),
    ("read", lambda r: bool(r["pages"]), "pages were fetched and cached for it"),
    ("evidenced", lambda r: bool(r["axes"]), "at least one axis gate found something"),
    ("assayable", lambda r: r["axes"] >= 2, "enough axes for a decimal, not a band alone"),
)


def nested_run(sets, order):
    """The longest run of consecutive stages that really is a chain of subsets.

    Asked of the data every time rather than declared once: a stage's population can change
    meaning under it (a source getting shelved, a host resolving) and a funnel drawn from a
    stale assumption of nesting is the defect this replaced.
    """
    best = (0, 0)
    for i in range(len(order)):
        j = i + 1
        while j < len(order) and sets[order[j]] <= sets[order[j - 1]]:
            j += 1
        if j - i > best[1] - best[0]:
            best = (i, j)
    return list(order[best[0]:best[1]])


def report(rows, top=18):
    n = len(rows)
    sets = {k: {i for i, r in enumerate(rows) if t(r)} for k, t, _ in STAGE_TESTS}
    blurb = {k: b for k, _, b in STAGE_TESTS}
    order = [k for k, _, _ in STAGE_TESTS]
    f = {k: len(v) for k, v in sets.items()}
    f["ranked"] = sum(1 for r in rows if r["native"])
    f["banded"] = sum(1 for r in rows if r["band"] not in ("unassayed", "", None))

    print("=" * 88)
    print(f"CHARACTER SWEEP — {n:,} entries classed Persons across {len({r['source'] for r in rows})} sources")
    print("=" * 88)

    chain = nested_run(sets, order)
    base = chain[0]
    nb = max(len(sets[base]), 1)
    loose = [k for k in order if k not in chain]

    print(f"\nFUNNEL — verified nested: each stage below is a subset of the one above it, "
          f"tested on these {n:,} rows")
    print(f"{'stage':<14}{'count':>9}{'of all':>9}{'of ' + base:>14}  {'':<20}")
    prev = None
    for k in chain:
        bar = "#" * int(34 * len(sets[k]) / nb)
        drop = (prev - f[k]) if prev is not None else 0
        print(f"  {k:<12}{f[k]:>9,}{f[k]/max(n, 1):>8.1%}{f[k]/nb:>13.1%}  {bar}"
              + (f"   -{drop:,}" if drop else ""))
        prev = f[k]

    if loose:
        # NOT DRAWN AS STAGES, AND NOT DROPPED EITHER. These are real measurements of the same
        # corpus that simply do not nest into the chain above; stacking their bars under it is
        # what made a 30% gate and a 99.9% gate read as one descending sequence. Each one is
        # printed against the funnel's base with the crossover in BOTH directions, which is the
        # only honest way to say "overlapping, not nested".
        print("\nSEPARATE POPULATIONS — measured on the same rows, NOT stages of that funnel")
        for k in loose:
            only_k = len(sets[k] - sets[base])
            only_b = len(sets[base] - sets[k])
            print(f"  {k:<12}{f[k]:>9,}{f[k]/max(n, 1):>8.1%}   {blurb[k]}")
            print(f"  {'':<12}{'':>9}{'':>8}   {only_k:,} of these are not {base}; "
                  f"{only_b:,} {base} entries are not {k}")

    print(f"\n  {'ranked':<12}{f['ranked']:>9,}{f['ranked']/max(n, 1):>8.1%}   "
          f"(own fiction publishes a scale position)")
    print(f"  {'banded':<12}{f['banded']:>9,}{f['banded']/max(n, 1):>8.1%}   "
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
    # LANDED, NOT TRUNCATED-THEN-FILLED. CHARACTER_SWEEP.json is read LIVE and unguarded by
    # `hostcheck.py`, `magnitude.py` and `standards.py` while this runs, and a bare truncating
    # open hands all three a half-written file that parses as a shorter cast list rather than
    # failing -- the exact indistinguishable-from-legitimate shape m100 retired across the tree.
    # This site was missed by that sweep. The VERDICT is reported: a denied replace leaves the
    # PREVIOUS sweep on disk, and the standard `the character sweep is newer than the catalogue`
    # is what will notice, but only if nobody claimed success here first.
    if not silence.write_json(OUT, rows, ensure_ascii=False):
        print(f"\nsweep: {os.path.basename(OUT)} could not be replaced; it still holds the "
              f"PREVIOUS sweep. Nothing downstream has this run's cast list.", file=sys.stderr)
        return 1
    print(f"\nfull table -> {OUT}  ({os.path.getsize(OUT)//1024:,} KB)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
