#!/usr/bin/env python3
"""
FEATS_INDEX — the join that makes 39,862 mined feats reachable as a chapter.

WHAT WAS MISSING
----------------
`feats.py` mines attested deeds out of wiki prose and lands them under `data/readfeats/<host>/
<Entity>.json`: each feat a QUOTED sentence, tagged with one of the eleven Assay axes and
carrying the page it came from. That is the Charter's Part Three worksheet material, already
gathered -- 39,862 of them across 1,166 entities, averaging 34 per entity.

And nothing could reach it. `assay.py` and `magnitude.py` consume feats per-entity when scoring,
but the generation path had no idea the store existed: `manifest_builder` groups a source's
CATALOGUE entries by category and emits chapter jobs, and feats are not catalogue entries. So
the best-evidenced material in the library was structurally unable to become prose.

WHY THE OBVIOUS JOIN DOES NOT WORK
----------------------------------
The tempting key is the entry's own `wiki_page` URL: parse out host and title, look up
`readfeats/<host>/<title>.json`. Measured, that reaches **676 of 1,241** records. The reason it
fails is instructive and is the sort of thing this project keeps paying for: **a catalogue entry
does not necessarily have a URL.** All 341 `all Bloons TD` entries carry `wiki_page: None`, so
its feats -- Geraldo, Gravelord Lych, Magus Perfectus, all present in the catalogue BY NAME and
all mined successfully -- could never be matched by a URL join. A key that is absent on a whole
source is not a weak key, it is no key.

THE JOIN THAT WORKS
-------------------
`data/WIKI_HOSTS.json` is the authoritative source -> host binding (202 sources). Invert it,
then match the feats record's `entity` against the source's entry NAMES, normalised. Measured
over the whole store: **1,224 of 1,241 records and 39,400 of 39,862 feats -- 98.6%**.

The seventeen that miss are TWO different problems, and an earlier version of this note called
them all one. Measured 2026-08-24:

  * **14 records / 222 feats** are hosts with no `WIKI_HOSTS` entry at all (the amazing digital
    circus, date a live, sakamoto days, uncle grandpa) -- sources whose host was never recorded.
    A gap in that file rather than in this join, and binding those four hosts fixes them.
  * **3 records / 240 feats -- the MAJORITY of the stranded deeds -- are on hosts that ARE bound**
    (`dc.fandom.com` -> DC, `marvel.fandom.com` -> Marvel): `Wally West (New Earth)`, `Wally West
    (Prime Earth)` and `Brood`. The host is known; the catalogue simply holds no entry under a
    matching name. Binding hosts will never recover these, and neither will loosening `_norm`
    (see its docstring, which measures why). They are catalogue gaps.

The distinction matters because it changes who fixes it, and 52% of the stranded evidence sits on
the side the original note did not describe. `audit()` and `main()` already report a known host
separately from an unrecorded one -- the code was right and only this note was wrong.

They are REPORTED rather than dropped quietly, because an unjoined feats record is a mined deed
that no volume will ever print.

ON SHARED HOSTS, DELIBERATELY
-----------------------------
Some hosts serve several sources: `forgottenrealms.fandom.com` backs thirty D&D books,
`en.wikipedia.org` backs twenty-two, `godofwar.fandom.com` backs both `God of War` and
`major fantasy pantheons`. An entity catalogued in two of them attaches to BOTH, and that is
correct rather than a duplication bug: each volume covers its own cast, and Kratos genuinely
appears in both casts. Measured, this affects 35 records and 531 feats -- small, and the
alternative (picking one source by some tie-break) would silently rob the other volume of
evidence it is entitled to.

NO CAPS. `feats_for_source` returns every feat of every matching entity. Callers that paginate
must page through all of it, exactly as `manifest_builder` already does for large chapters.
"""
import collections
import json
import os
import sys

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import silence  # noqa: E402

_BAD_CHARS = (chr(8), chr(11), chr(12), chr(7))
if any(c in open(os.path.abspath(__file__), encoding="utf-8").read() for c in _BAD_CHARS):
    raise SystemExit(__file__ + ": a regex escape was eaten in transit.")

READFEATS = os.path.join(HERE, "data", "readfeats")
WIKI_HOSTS = os.path.join(HERE, "data", "WIKI_HOSTS.json")

# `WIKI_HOSTS` records owner-supplied books as `pages:<title>` rather than a hostname. Those are
# not wiki hosts and must not be inverted into the host map, or every one of them would collide
# on a single pseudo-host.
_PAGES_SENTINEL = "pages:"

# KEYED BY THE PATH THAT WAS ASKED FOR, not by the function that was called. Both readers below
# take a path override and used to cache under one global slot each, so a second call with a
# different path silently returned the FIRST path's answer -- a join quietly computed against a
# store nobody asked for. No caller passes a non-default argument today; the signature invites
# exactly that, and a cache that ignores its own key is a wrong answer waiting for a caller.
_CACHE = {"hosts": {}, "index": {}}


def _norm(s):
    """Fold a name to its comparable core.

    Case and punctuation differ freely between a wiki page title and the catalogue's entry name,
    and both are written by different passes. Alphanumerics only.

    THIS DOES NOT STRIP A PARENTHETICAL, and an earlier version of this docstring claimed it did
    -- it offered "Zangetsu (Zanpakutou spirit)" vs "Zangetsu" as a case this folds together.
    It does not: alphanumeric-only folding gives `zangetsuzanpakutouspirit` against `zangetsu`.
    Corrected 2026-08-24 after measuring, because a comment that promises a capability the code
    lacks is how the next reader mis-diagnoses a stranded record.

    The STRICT form is nonetheless the right one, and that part of the original claim held up.
    79 of 1,241 feats records carry a parenthetical and 76 of them join anyway, because the
    catalogue overwhelmingly records the SAME disambiguated form. Loosening it would recover
    none of the three that miss (`Wally West (New Earth)` and `Wally West (Prime Earth)` would
    fold onto the catalogue's `Wally West (Earth-16)`, silently merging three DC continuities;
    Marvel has no plain `Brood` entry under any spelling) while risking exactly that class of
    conflation across the whole store. Those three are catalogue gaps, not folding failures --
    see `audit()`, which reports a known host separately from an unrecorded one.
    """
    return "".join(c for c in (s or "").lower() if c.isalnum())


def host_to_sources(path=WIKI_HOSTS):
    """{host: [source, ...]} inverted from WIKI_HOSTS.json, minus the `pages:` sentinels."""
    if path in _CACHE["hosts"]:
        return _CACHE["hosts"][path]
    out = collections.defaultdict(list)
    try:
        with open(path, encoding="utf-8") as f:
            wh = json.load(f)
    except Exception:
        silence.note("feats_index.host_to_sources")
        wh = {}
    for src, host in (wh or {}).items():
        if isinstance(host, str) and host and not host.startswith(_PAGES_SENTINEL):
            out[host.lower()].append(src)
    _CACHE["hosts"][path] = dict(out)
    return _CACHE["hosts"][path]


def load_index(root=READFEATS):
    """Every feats record on disk, as {(host, normalised entity): record}.

    Read once and cached: the store is ~1,240 small files and the manifest builder would
    otherwise re-walk it per source.
    """
    if root in _CACHE["index"]:
        return _CACHE["index"][root]
    idx = {}
    if not os.path.isdir(root):
        _CACHE["index"][root] = idx
        return idx
    for host_dir in sorted(os.listdir(root)):
        p = os.path.join(root, host_dir)
        if not os.path.isdir(p):
            continue
        host = host_dir.replace("_", ".").lower()
        for fn in sorted(os.listdir(p)):
            if not fn.endswith(".json"):
                continue
            try:
                with open(os.path.join(p, fn), encoding="utf-8") as f:
                    rec = json.load(f)
            except Exception:
                silence.note("feats_index.load_index")
                continue
            entity = rec.get("entity") or fn[:-5]
            rec.setdefault("entity", entity)
            rec.setdefault("host", host)
            idx[(host, _norm(entity))] = rec
    _CACHE["index"][root] = idx
    return idx


def feats_for_source(source_name, record):
    """Every mined feat belonging to this source's cast, entity by entity.

    `record` is the source's catalogue record (the thing `pipeline.records()` yields), because
    the match is against its ENTRY NAMES -- that is what makes the join survive a source whose
    entries carry no URL.

    Returns a list of dicts, one per entity that has feats, each carrying the catalogue entry it
    matched so the prose has the entry's own description and magnitude to hand:

        {"entity", "host", "pages", "feats": [{"feat", "axis", "page"}, ...],
         "axis_counts": {axis: n}, "entry": <the catalogue entry>, "feat_count": n}

    Ordered by feat count, richest first, then by name for stability. RANKED, NEVER TRUNCATED --
    if a generation run is interrupted the best-evidenced entities have already been written.
    """
    idx = load_index()
    hosts = [h for h, srcs in host_to_sources().items() if source_name in srcs]
    if not hosts:
        return []
    entries_by_norm = {}
    for e in (record.get("entries") or []):
        entries_by_norm.setdefault(_norm(e.get("name")), e)

    out = []
    for host in hosts:
        for (h, ent_norm), rec in idx.items():
            if h != host or ent_norm not in entries_by_norm:
                continue
            feats = rec.get("feats") or []
            if not feats:
                continue
            axes = collections.Counter(f.get("axis") for f in feats if f.get("axis"))
            out.append({
                "entity": rec.get("entity"),
                "host": host,
                "pages": rec.get("pages") or [],
                "feats": feats,
                "axis_counts": dict(axes),
                "feat_count": len(feats),
                "entry": entries_by_norm[ent_norm],
            })
    out.sort(key=lambda r: (-r["feat_count"], r["entity"]))
    return out


def audit():
    """Which feats records reach a source, and which are stranded.

    A stranded record is a mined deed no volume will ever print, so it is counted and named
    rather than left to be inferred from a smaller total.
    """
    sys.path.insert(0, os.path.join(HERE, "src"))
    import pipeline as PL

    idx = load_index()
    h2s = host_to_sources()
    by_src = {}
    for _, rec in PL.records():
        by_src[rec["source"]] = {_norm(e.get("name")) for e in (rec.get("entries") or [])}

    joined, stranded = [], []
    for (host, ent_norm), rec in idx.items():
        srcs = [s for s in h2s.get(host, []) if ent_norm in by_src.get(s, set())]
        (joined if srcs else stranded).append((host, rec, srcs))
    return {
        "records": len(idx),
        "joined": len(joined),
        "stranded": len(stranded),
        "feats_joined": sum(len(r.get("feats") or []) for _, r, _ in joined),
        "feats_stranded": sum(len(r.get("feats") or []) for _, r, _ in stranded),
        "stranded_hosts": collections.Counter(h for h, _, _ in stranded),
        "shared": sum(1 for _, _, s in joined if len(s) > 1),
    }


def main():
    a = audit()
    print("=" * 96)
    print("FEATS INDEX — can the mined deeds reach a volume?")
    print("=" * 96)
    print(f"\nfeats records on disk : {a['records']:,}")
    print(f"  joined to a source  : {a['joined']:,}  ({a['feats_joined']:,} feats)")
    print(f"  STRANDED            : {a['stranded']:,}  ({a['feats_stranded']:,} feats)")
    rate = 100.0 * a["joined"] / max(1, a["records"])
    print(f"  join rate           : {rate:.1f}% of records")
    print(f"  entities catalogued in more than one source on the same host: {a['shared']:,}")
    if a["stranded_hosts"]:
        print("\nSTRANDED BY HOST — a mined deed no volume will print. Usually a host with no")
        print("WIKI_HOSTS entry, which is a gap in that file rather than in the join:")
        for h, n in a["stranded_hosts"].most_common():
            known = "known host" if h in host_to_sources() else "NOT IN WIKI_HOSTS"
            print(f"   {h:<42}{n:>4} record(s)   {known}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
