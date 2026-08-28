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
    # `silence.write_json`, not a fixed temp name plus a bare `os.replace`. SOURCE_HOSTS extras
    # are read live while `discover()` walks, the temp path was shared by every concurrent
    # writer, and an uncaught PermissionError from Norton's object lock took `discover()` down
    # mid-walk instead of reporting a denied write. The retrying, pid-unique writer is what the
    # rest of the tree uses and what `silence.write_json`'s own docstring says replaced this
    # exact pattern. The verdict is returned, so a caller can tell a denied write from a
    # duplicate host -- both used to be `False`, which is how a lost host looks like a known one.
    if not silence.write_json(EXTRA, data, indent=1, ensure_ascii=False):
        silence.note("hosts.py:add-denied")
        return False
    return True


KEEP = ("holds", "partial")

# A SECONDARY HOST IS JUDGED DIFFERENTLY FROM A PRIMARY ONE.
#
# `hostcheck.score` judges by LIFT -- hit rate minus the host's own baseline for names it has no
# reason to hold. That is exactly right when choosing the ONE host a source will be mined from,
# because it finds the specialist and refuses a site that answers everybody.
#
# It is exactly wrong when asking whether a site is worth reading IN ADDITION. Measured on Bleach:
#
#     en.wikipedia.org   probed 40   hits 14   rate 0.35   baseline 0.462   lift -0.112
#                        about 1.00                        verdict "NAMES ONLY"
#
# Every page it matched is a real Bleach article -- Ichigo Kurosaki, Byakuya Kuchiki, Kenpachi
# Zaraki -- and `about` says so at 1.00. The negative lift is not evidence against Wikipedia; it
# is a statement that Wikipedia is an encyclopedia of everything, which was already known. Under
# a lift rule NO general-purpose host can ever be adopted for ANY source, however much genuine
# canon it holds. That is the rule silently deciding the library may only ever read fan wikis.
#
# So a secondary host is kept on ABOUTNESS and substance: the pages it returned must really be
# about this fiction, and there must be enough of them to be worth a request.
MIN_HITS_SECONDARY = 3
MIN_ABOUT_SECONDARY = 0.6


def discover(only=None, workers=6, per_source=24):
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
    wanted = [w.strip().lower() for w in only.split(",")] if only else None
    todo = [s for s in prim
            if (not wanted or any(w in s.lower() for w in wanted)) and by.get(s)]
    added, rows = 0, []

    def work(source):
        # NO `[:40]`. This roster is the evidence a candidate host is SCORED against, so capping
        # it scored every wiki on the same alphabetical first forty names -- the CLAUDE.md
        # canonical violation, applied to the decision of where a source lives. A host that holds
        # the back half of a cast could not be told from one that holds none of it. (run #26)
        names = list(by.get(source) or [])
        if len(names) < 4:
            return None
        cur = primary_host(source)
        try:
            cands = HC.candidates(source, cur, by=by, hosts=prim)
        except Exception:
            silence.note("hosts.py:candidates")
            return None
        # `candidates` returns grounded hosts first and speculation after. Probing every
        # invented subdomain costs a network round trip each to learn it does not exist, so the
        # tail is bounded -- but the bound sits AFTER the evidence, never through it, and what
        # it drops is guesses rather than known hosts.
        if per_source and len(cands) > per_source:
            cands = cands[:per_source]
        keep = []
        for h in cands:
            if h == cur:
                continue
            try:
                r = HC.score(h, names, source, by=by)
            except Exception:
                silence.note("hosts.py:score")
                continue
            about = r.get("about")
            hits = r.get("hits") or 0
            # Either test admits a host: the specialist bar (lift over its own baseline), or the
            # substance bar (it really holds this fiction's material, whatever else it holds).
            specialist = r.get("verdict") in KEEP
            substantial = (hits >= MIN_HITS_SECONDARY
                           and about is not None and about >= MIN_ABOUT_SECONDARY)
            if specialist or substantial:
                why = r.get("verdict") if specialist else "about=" + str(about)
                keep.append((r.get("lift") or 0, h, why, r.get("rate")))
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
