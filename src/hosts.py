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
    """Record an additional host. Never touches WIKI_HOSTS. -> True | False | None.

    THREE STATES, BECAUSE TWO OF THEM MEAN OPPOSITE THINGS (order b840f43d4f8f):

        True   the host is now recorded
        False  there was nothing to record -- no host, the primary, or already present
        None   there WAS something to record and the write was DENIED; the host is LOST

    The comment below already claimed a caller could tell a denied write from a duplicate, and
    it could not: both returned a bare `False`, which is precisely how a lost host comes to look
    like a known one. `False` and `None` are both falsy, so callers counting successes are
    unaffected; a caller that cares which kind of failure it got can now ask.
    """
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
        return None
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
    added, rows, lost = 0, [], []

    def work(source):
        # NO `[:40]`. This roster is the evidence a candidate host is SCORED against, so capping
        # it scored every wiki on the same alphabetical first forty names -- the CLAUDE.md
        # canonical violation, applied to the decision of where a source lives. A host that holds
        # the back half of a cast could not be told from one that holds none of it. (run #26)
        names = list(by.get(source) or [])
        if len(names) < 4:
            # A DISTINGUISHABLE NEGATIVE, NOT A SILENT DROP (order f28f27da7c1f). Three names
            # is too thin a roster to score a host against, and that bound is sound -- but the
            # consumer below used to test `if not res: continue`, which reads a bare `None` the
            # same way whether the source was probed and held nothing or was never probed at
            # all. `discover()`'s own summary already makes this argument for its OTHER bound
            # (the per-source speculation cap, printed a few lines down): "an unstated bound is
            # indistinguishable from no bound at all." Return a sentinel `discover()` can tally
            # and name instead of a bare None.
            return (source, None, 0)
        cur = primary_host(source)
        try:
            grounded, spec = HC.candidates_split(source, cur, by=by, hosts=prim)
        except Exception:
            silence.note("hosts.py:candidates")
            return None
        # THE BOUND IS APPLIED TO THE SPECULATION, AND IT CAN NO LONGER REACH THE EVIDENCE.
        #
        # This read `cands = HC.candidates(...)` followed by `cands[:per_source]`, over a flat
        # concatenation, under a comment asserting that "the bound sits AFTER the evidence,
        # never through it, and what it drops is guesses rather than known hosts". Nothing
        # enforced that. It was true only because the grounded prefix happened to be shorter
        # than 24: measured over the whole live roll on 2026-08-29, 175 sources with a roster,
        # the longest candidate list ran to 75 while the largest grounded prefix was 15, no
        # source exceeded 24 grounded, and no grounded host was actually dropped. Nine hosts of
        # headroom, on a grounded list that is bounded by nothing -- www.dandwiki.com, every
        # pairwise and single-token slug, EVERY NEIGHBOUR HOST whose roster shares max(3, 25%)
        # of this source's names (an unbounded loop over all ~193 sources), every feats._slugs
        # variant, and en.wikipedia.org. The D&D shelf already sits at the top of that table, so
        # a franchise added to the roll with many overlapping rosters pushes the prefix up with
        # no signal at all, and the day it passes 24 the slice starts eating real hosts in
        # silence. hostcheck.py records the last time this exact slice did that: en.wikipedia.org
        # at position nineteen of a list cut at eighteen, so every pantheon and astrology source
        # was reported as having no wiki. (order 0b43bb663c36)
        #
        # `candidates_split` hands back the boundary instead of making the caller guess where it
        # is, so the bound now provably lands on guesses only. Probing an invented subdomain
        # still costs a round trip to learn it does not exist, which is what the bound is for.
        withheld = 0
        if per_source and len(spec) > per_source:
            withheld = len(spec) - per_source
            spec = spec[:per_source]
        cands = grounded + spec
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
        return (source, keep, withheld)

    # 615 speculative probes were withheld across the roll on the day this was measured and
    # nothing anywhere said so. A bound is allowed to exist; a bound nobody can see the size of
    # is how a smaller universe gets mistaken for the whole one, so the total is reported.
    withheld_total = 0
    not_probed = []
    with ThreadPoolExecutor(max_workers=workers) as ex:
        for res in ex.map(work, todo):
            if not res:
                continue
            source, keep, withheld = res
            if keep is None:
                # A THIN ROSTER, NOT A CANDIDATE THAT LOST. Counted and named beside the
                # speculative-guess figure below, so "probed, nothing held" and "never probed"
                # stay two different findings. Uncapped, like the two lists next to it.
                not_probed.append(source)
                continue
            withheld_total += withheld
            for lift, h, verdict, rate in keep:
                landed = add(source, h, evidence=verdict + " lift=" + str(lift), score=rate)
                if landed:
                    added += 1
                elif landed is None:
                    # A HOST THAT WAS FOUND AND THEN LOST TO A DENIED WRITE. This is the only
                    # place that can say so: `add()` knows the write failed but not which host
                    # discovery had just paid to find, and the summary below counts only what
                    # landed -- so without this line a denied write reads as "we looked and
                    # there was nothing there", which is the same shape as a smaller universe.
                    lost.append((source, h))
            if keep:
                rows.append((source, [k[1] for k in keep]))
    if lost:
        # SAID OUT LOUD, ON STDERR, AND ESCALATED -- not returned quietly for a caller to
        # notice. A discovery walk is expensive and its whole product is these hosts; losing one
        # to a denied write and printing only "hosts added: N" is the failure this library calls
        # green-by-absence, since N is smaller and nothing says why.
        sys.stderr.write("hosts: %d DISCOVERED HOST(S) WERE NOT RECORDED -- the write to "
                         "SOURCE_HOSTS was denied and these are lost until the next walk: %s\n"
                         % (len(lost), "; ".join("%s -> %s" % (s, h) for s, h in lost)))
        silence.note("hosts.py:discover-lost")
    if withheld_total:
        # Speculation only -- `candidates_split` guarantees the bound cannot reach a grounded
        # host -- so this is a cost figure, not a loss figure. It is printed because it is the
        # number that says how much guessing the per_source bound is buying back, and because
        # an unstated bound is indistinguishable from no bound at all.
        print("  (%d speculative host guess(es) withheld by per_source=%d; grounded hosts are "
              "never bounded)" % (withheld_total, per_source))
    if not_probed:
        print("  (%d source(s) not probed: fewer than 4 roster names to score a host against: "
              "%s)" % (len(not_probed), ", ".join(not_probed)))
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
            # UNCUT (Hard Rule 0, sweep42-batch05). This file has already treated the identical
            # pattern as a defect once -- see work()'s comment on removing a [:40] roster cap --
            # and the same cut survived here in --discover.
            print("  %-40s + %s" % (str(src), ", ".join(hs)))
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
