#!/usr/bin/env python3
"""HOSTS — every site a source can be read from, not just the best one.

THE SINGLE-HOST ASSUMPTION
--------------------------
`data/WIKI_HOSTS.json` maps each source to ONE host, as a bare string: 194 sources, 194 strings,
zero lists. Everything downstream inherited that shape, so `hostcheck.adopt()` picks a winner and
the runners-up are discarded -- even when they scored well, and even when they hold material the
winner does not.

That is a cap wearing different clothes. A source is not a website; it is a fiction, and a
fiction is written about in more than one place. The Undertaker is on prowrestling.fandom.com,
on Wikipedia, and in half a dozen wrestling databases, and the three do not agree about the same
things: the fandom wiki has kayfabe and storyline, Wikipedia has dates and provenance, the
databases have match records. Reading one and calling the source covered is the same error as
reading one page of an entity and calling the entity read.

WHAT THIS DOES
--------------
Keeps a SECOND file, `data/SOURCE_HOSTS.json`, holding every additional host a source has been
shown to be readable from, with the evidence that justified it. `hosts_for()` returns the primary
from WIKI_HOSTS followed by the extras, in scored order, so a caller that wants one host still
gets the right one first and a caller that wants everything can have it.

Nothing here overwrites WIKI_HOSTS. The primary stays where every other module expects it.
"""
import argparse
import json
import os
import sys

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import silence                                                          # noqa: E402

_BAD_CHARS = (chr(8), chr(11), chr(12), chr(7))
if any(c in open(os.path.abspath(__file__), encoding="utf-8").read() for c in _BAD_CHARS):
    raise SystemExit(__file__ + ": a regex escape was eaten in transit.")

PRIMARY = os.path.join(HERE, "data", "WIKI_HOSTS.json")
EXTRA = os.path.join(HERE, "data", "SOURCE_HOSTS.json")


def _load(path, default):
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        silence.note("hosts.py:load")
        return default


def primary_host(source):
    h = _load(PRIMARY, {}).get(source)
    if isinstance(h, list):
        return h[0] if h else None
    return h


def hosts_for(source, include_primary=True):
    """Every host this source can be read from, best first.

    The primary leads because it is the one every other module already trusts. Extras follow in
    the order they were adopted, which is scored order.
    """
    out = []
    if include_primary:
        p = primary_host(source)
        if p and not str(p).startswith("pages:"):
            out.append(p)
    for rec in (_load(EXTRA, {}).get(source) or []):
        h = rec.get("host") if isinstance(rec, dict) else rec
        if h and h not in out:
            out.append(h)
    return out


def add(source, host, evidence=None, score=None):
    """Record an additional host. Never touches WIKI_HOSTS."""
    if not host or host == primary_host(source):
        return False
    data = _load(EXTRA, {})
    rows = data.setdefault(source, [])
    if any((r.get("host") if isinstance(r, dict) else r) == host for r in rows):
        return False
    rows.append({"host": host, "evidence": evidence, "score": score})
    tmp = EXTRA + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=1, ensure_ascii=False)
    os.replace(tmp, EXTRA)
    return True


KEEP = ("holds", "partial")


def discover(only=None, workers=6, per_source=8):
    """Find every ADDITIONAL host each source can be read from, and keep all that hold.

    `hostcheck.adopt()` already does the hard part -- propose candidates, probe each against the
    source's own roster, and judge by LIFT over the host's own baseline for foreign names. The
    only thing it does wrong for this purpose is pick a winner. A host scoring `partial` is not
    a loser; it is a second shelf with some of the same books and some different ones, and the
    library wants both.

    Nothing is adopted on a name match. A host is kept only if it answers this source's OWN
    roster measurably better than it answers everybody else's, which is the same bar `sweep`
    uses and the reason 'Lost Mines of Phandelver' stopped resolving to the cast of Lost.
    """
    import hostcheck as HC
    from concurrent.futures import ThreadPoolExecutor

    by = HC.entities_by_source()
    prim = _load(PRIMARY, {})
    todo = [s for s in prim if (not only or only.lower() in s.lower()) and by.get(s)]
    added, rows = 0, []

    def work(source):
        names = list(by.get(source) or [])[:40]
        if len(names) < 4:
            return None
        cur = primary_host(source)
        try:
            cands = HC.candidates(source, cur, by=by)[:per_source]
        except Exception:
            silence.note("hosts.py:candidates")
            return None
        keep = []
        for h in cands:
            if h == cur:
                continue
            try:
                r = HC.score(h, names, source, by=by)
            except Exception:
                silence.note("hosts.py:score")
                continue
            if r.get("verdict") in KEEP:
                keep.append((r.get("lift") or 0, h, r.get("verdict"), r.get("rate")))
        keep.sort(reverse=True)
        return (source, keep)

    with ThreadPoolExecutor(max_workers=workers) as ex:
        for res in ex.map(work, todo):
            if not res:
                continue
            source, keep = res
            for lift, h, verdict, rate in keep:
                if add(source, h, evidence=verdict + " lift=" + str(lift), score=rate):
                    added += 1
            if keep:
                rows.append((source, [k[1] for k in keep]))
    return added, rows


def coverage():
    """How many sources have more than one place to be read from."""
    prim = _load(PRIMARY, {})
    ex = _load(EXTRA, {})
    rows = []
    for src in prim:
        rows.append((src, len(hosts_for(src))))
    multi = sum(1 for _, n in rows if n > 1)
    return {"sources": len(rows), "with_a_host": sum(1 for _, n in rows if n >= 1),
            "with_more_than_one": multi, "extra_hosts_recorded": sum(len(v) for v in ex.values())}


def main():
    ap = argparse.ArgumentParser(description="the multi-host registry")
    ap.add_argument("--show", metavar="SOURCE", help="list every host for one source")
    ap.add_argument("--stats", action="store_true")
    ap.add_argument("--discover", action="store_true",
                    help="probe alternative hosts for every source and keep all that hold")
    ap.add_argument("--only", help="restrict --discover to sources matching this")
    ap.add_argument("--workers", type=int, default=6)
    a = ap.parse_args()

    if a.discover:
        before = coverage()
        added, rows = discover(only=a.only, workers=a.workers)
        after = coverage()
        for src, hs in rows:
            print("  %-40s + %s" % (str(src)[:39], ", ".join(hs)))
        print("")
        print("hosts added: %d" % added)
        print("sources with more than one host: %d -> %d"
              % (before["with_more_than_one"], after["with_more_than_one"]))
        return 0
    if a.show:
        prim = _load(PRIMARY, {})
        match = [s for s in prim if a.show.lower() in s.lower()]
        for s in match:
            print(s)
            for h in hosts_for(s):
                print("   " + h)
            if not hosts_for(s):
                print("   (none)")
        return 0
    c = coverage()
    for k, v in c.items():
        print("%-22s %s" % (k, v))
    return 0


if __name__ == "__main__":
    sys.exit(main())
