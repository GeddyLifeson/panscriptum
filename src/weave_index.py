#!/usr/bin/env python3
"""
Phase 3, first half — the global entity index and cross-source collision detector.

Pure Python. No model, no GPU, no tokens. This is deliberate: the charter's Identity Rule is a
factual question before it is a judgment one, and the factual half is a string-matching problem.

  "When two sources describe the same thing ... they are the *same thing witnessed twice*, and
   the disagreements go to the Contradictions register as scholarship, not to separate shelves
   as canon. One reality, many witnesses."   -- Charter, Part Four

What this produces is CANDIDATES, not rulings. A shared name is evidence that two entries may be
one entity; it is not proof. Thor in Marvel and Thor in the Norse pantheon are the same Office
seatholder witnessed twice (Great Identification 2); "Ruby" in three unrelated works is three
people. Only the model, reading both descriptions, may adjudicate that -- and only into the
three-way classification of the second half.

Why this matters more than it looks: Collection V.1-V.11 is "the master alphabetical registry"
across all of Collection II. A Persons A-Z volume is impossible without it, because without
resolution the volume is just concatenated per-IP lists with the same subject repeating.

Usage:
    python3 src/weave_index.py                 # report
    python3 src/weave_index.py --write         # also emit data/ENTITY_INDEX.json + candidates
"""
import argparse
import collections
import json
import os
import re
import time
import unicodedata
import silence

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RECORDS = os.path.join(HERE, "data/records")
OUT_INDEX = os.path.join(HERE, "data/ENTITY_INDEX.json")
OUT_CAND = os.path.join(HERE, "data/WEAVE_CANDIDATES.json")

# Titles and honorifics that must not participate in matching -- otherwise every "Captain"
# collides with every other Captain and the candidate list is noise.
_STRIP = re.compile(
    r"^(?:the|a|an|lord|lady|king|queen|prince|princess|sir|dame|saint|st|captain|commander|"
    r"general|admiral|doctor|dr|professor|master|mistress|father|mother|brother|sister|"
    r"emperor|empress|god|goddess|great|grand)\s+", re.I)

# Names too generic to be evidence of anything. A collision on these is meaningless.
_STOPNAMES = {
    "narrator", "protagonist", "player", "hero", "villain", "boss", "enemy", "soldier",
    "guard", "citizen", "merchant", "priest", "knight", "warrior", "mage", "wizard",
    "dragon", "demon", "angel", "ghost", "spirit", "god", "goddess", "king", "queen",
    "father", "mother", "child", "man", "woman", "unknown", "unnamed", "none", "other",
}


# A parenthetical is usually an ALIAS -- "Hulk (Bruce Banner)" is one being under two names, and
# folding it is right. A parenthetical naming a CONTINUITY is the opposite: it is the thing that
# makes two entries different beings.
#
# Marvel and DC are not written as retcons, they are written as timelines. Earth-616's Thor and
# Earth-1610's Thor have separate histories, separate deaths and separate feats. Folding them
# merges two universes' evidence into one worksheet and assays nobody. The charter already has
# the rung for this -- Goku shelves at U-7 -- so a declared continuity belongs in the identity.
# WHICH parentheticals are designations is LEARNED FROM THE CORPUS, not listed by hand.
#
# A hand-list would need Marvel's Earths, DC's Earths, Dragon Ball's Xeno and Future timelines,
# Star Trek's TOS and Kelvin, Transformers' Bayverse and G1, Zelda's three branches, Sonic's four
# publishers -- and then it would need updating forever, every time a source is added. That is
# precisely the brittle-list pattern that produced most of this project's silent failures.
#
# The corpus already knows. A parenthetical that appears on MANY DIFFERENT names is a marker
# applied to a whole population: "(new earth)" on 48 names, "(earth-616)" on 37, "(bayverse)" on
# 23, "(tos)" on 24. A parenthetical appearing on ONE name is that name's own gloss -- "(Bruce
# Banner)" -- and 3,126 of 3,451 parentheticals in this corpus are that kind.
#
# The threshold sits low because the cost is asymmetric. Merging two entities INVENTS a composite
# being that never existed and fuses two universes' evidence into one worksheet. Splitting one
# entity in two only leaves two thinner records, which the weave can relate afterwards. When
# uncertain, split.
DESIGNATION_MIN_NAMES = 3

# A short SEED for designations that are unambiguous but too rare in this corpus to be learned.
# "Xeno" names a Dragon Ball timeline and "Kelvin" a Star Trek one, but each sits on a single
# entry here, so frequency alone reads them as a gloss. The seed exists only for terms that can
# mean nothing else; anything that could plausibly be an alias is left to the corpus to decide.
_SEED = {
    "xeno", "kelvin", "mirror", "g1", "idw", "archie", "satam", "legends", "canon",
    "new 52", "n52", "post-crisis", "pre-crisis", "flashpoint", "rebirth", "dceu", "mcu",
    "ultimate", "noir", "1602", "zombieverse", "mangaverse", "dcau", "arrowverse",
    "future trunks", "gt", "super", "heroes", "downfall", "child timeline", "adult timeline",
}
_EARTH = re.compile(r"^earth[- ]?[\w']+$", re.I)   # every Earth-N in every publisher, at once
_DESIGNATIONS = None


def designations(records=None):
    """The set of parentheticals this corpus uses as designations rather than as aliases.

    Cached against the records directory's own signature, exactly like `load_records()`. The
    first version cached in a bare global with no invalidation at all, so a long-lived process
    (the dashboard, the keeper) that called this once kept answering from a corpus snapshot
    taken at import time -- and this set decides whether "(Earth-616)" is a continuity marker
    or part of a name, so a stale answer misreads every entity ingested since. Same stale-cache
    shape that bit `chain_harvest_idx` and `load_records` before their own fixes. (BUGS m17.)"""
    global _DESIGNATIONS
    # Only the corpus-derived answer is cacheable. A caller-supplied `records` list has no
    # signature to key on, so caching it would let one explicit call's answer be served to the
    # next -- a worse staleness than the one being fixed. Explicit callers always recompute.
    cacheable = records is None
    sig = _records_sig()[1] if cacheable else None
    if cacheable and _DESIGNATIONS is not None and _DESIGNATIONS[0] == sig:
        return _DESIGNATIONS[1]
    seen = {}
    try:
        recs = records if records is not None else load_records()
    except Exception:
        silence.note("weave_index-designations-load")
        if cacheable:
            _DESIGNATIONS = (sig, set())
        return set()
    for r in recs:
        for e in r.get("entries", []):
            base = re.sub(r"\s*\([^)]*\)", "", e.get("name", "")).strip().lower()
            for inner in re.findall(r"\(([^)]*)\)", e.get("name", "")):
                head = inner.split("/")[0].strip().lower()
                if 1 < len(head) < 40:
                    seen.setdefault(head, set()).add(base)
    out = {k for k, v in seen.items() if len(v) >= DESIGNATION_MIN_NAMES}
    out |= _SEED
    out |= {k for k in seen if _EARTH.match(k)}
    if cacheable:
        _DESIGNATIONS = (sig, out)
    return out


def continuity_of(name, known=None):
    """The designation a name declares, or None. Part of identity, never stripped from it.

    `known` is an optional precomputed designation set (i.e. the return of `designations()`).
    A caller folding many names in a row should hoist it out of the loop: the set is one
    corpus-wide answer, so re-asking for it per name buys no freshness a loop could use.
    """
    if known is None:
        known = designations()
    for inner in re.findall(r"\(([^)]*)\)", name or ""):
        head = inner.split("/")[0].strip().lower()
        if head in known:
            return re.sub(r"[^a-z0-9]", "", head)
    return None


def norm(name, known=None):
    """Fold to a comparison key: strip accents, parentheticals, titles, punctuation.

    A declared continuity survives the fold as a suffix, so two Thors stay two Thors.

    `known` is an optional precomputed designation set, passed straight to `continuity_of`.
    Hot loops should hoist it (see `build`); omitting it is unchanged behaviour.
    """
    keep = continuity_of(name, known)
    s = unicodedata.normalize("NFKD", name or "")
    s = "".join(c for c in s if not unicodedata.combining(c))
    s = re.sub(r"\([^)]*\)", " ", s)          # drop parenthetical aliases
    s = re.sub(r"[^\w\s'-]", " ", s)
    s = re.sub(r"\s+", " ", s).strip().lower()
    prev = None
    while prev != s:                           # strip stacked titles: "the great lord X"
        prev = s
        s = _STRIP.sub("", s)
    s = re.sub(r"[^a-z0-9]", "", s)
    return s + "@" + keep if keep else s


_REC_CACHE = {"sig": None, "out": None}

# How long a computed signature may be reused before the directory is re-read. See the note in
# `_records_sig` for why this number is what it is.
SIG_MEMO_SECONDS = 1.0
_SIG_MEMO = {"at": None, "val": None}


def _records_sig(fresh=False):
    """(file count, newest mtime) over the records directory, or None if it cannot be stat'd.

    Shared by both caches below so they invalidate on exactly the same event. Pulled out
    2026-08-23 (BUGS m17) when `designations()` turned out to have no invalidation at all.

    2026-08-26 (BUGS 31715d/98a80b). This ran `glob` + 216 separate `getmtime` calls on EVERY
    call, including the cache-HIT fast path -- so `norm()`, whose only job is a regex fold,
    cost 13.0 ms and a single `build()` over 197,334 entries spent ~43 minutes inside
    `getmtime`. Two things fix it, and they fix different callers:

    1. `os.scandir` instead of `glob` + per-file `getmtime`. On Windows the directory
       enumeration already carries each entry's mtime, so the 216 stat syscalls collapse into
       the one enumeration that was happening anyway. Measured 14.3 ms -> 0.70 ms, and the
       signature is byte-identical -- this half trades away NOTHING.

    2. A short memo, because 0.70 ms x 197,334 is still 2.3 minutes. `fresh=True` bypasses it.

    On the window: it is deliberately shorter than the 2.34 s that `load_records()` needs to
    re-parse the corpus once something DOES change, so the memo can never be the dominant
    term in how fast a change is noticed. It is also, more to the point, shorter than the
    freshness the hot callers ever actually had: `build()` and `chain.entity_index()` re-stat
    the corpus per entry while iterating a record list they captured ONCE at the top, so their
    per-entry freshness was already fictional -- the memo makes an existing snapshot honest
    rather than introducing a new one. Records have exactly one sanctioned writer
    (`pipeline.write_record`), and no stage writes a record and re-reads it inside a second.
    """
    now = time.monotonic()
    if not fresh and _SIG_MEMO["at"] is not None and now - _SIG_MEMO["at"] < SIG_MEMO_SECONDS:
        return _SIG_MEMO["val"]
    files, newest = [], 0
    try:
        with os.scandir(RECORDS) as it:
            for de in it:
                if not de.name.endswith(".json"):
                    continue
                try:
                    if not de.is_file():
                        continue
                    m = de.stat().st_mtime
                except OSError:
                    # A file that vanished mid-enumeration. Same meaning the old getmtime
                    # failure had: refuse to hand out a signature this pass.
                    _ = "silence-exempt: an unstattable dir just skips the cache fast-path"
                    files.sort()
                    val = (files, None)
                    _SIG_MEMO.update({"at": now, "val": val})
                    return val
                files.append(de.path)
                if m > newest:
                    newest = m
    except OSError:
        # A missing or unreadable directory. `glob` returned [] here rather than raising, and
        # the old `max(..., default=0)` then made that a real, cacheable (0, 0) signature.
        # Preserved exactly: callers depend on an empty corpus being a stable answer.
        _ = "silence-exempt: an unreadable records dir reads as an empty corpus, as it always did"
    files.sort()
    val = (files, (len(files), newest))
    _SIG_MEMO.update({"at": now, "val": val})
    return val


def load_records():
    """All records with entries -- cached against the directory's own signature.

    63MB across 216 files (marvel.json alone is 27MB), and this was re-parsed on EVERY
    dashboard poll and three separate times per allsweep run (2026-08-23 optimization sweep).
    The signature is (count, max mtime), so any write anywhere in the directory invalidates.
    Callers get the shared list: read it, never mutate it."""
    files, sig = _records_sig()
    if sig is not None and sig == _REC_CACHE["sig"]:
        return _REC_CACHE["out"]
    out = []
    for p in files:
        try:
            with open(p, encoding="utf-8") as f:
                r = json.load(f)
        except Exception:
            silence.note("weave_index.py:load_records-unreadable")
            continue
        if r.get("entries"):
            out.append(r)
    _REC_CACHE.update({"sig": sig, "out": out})
    return out


def build():
    recs = load_records()
    # Hoisted: one corpus-wide answer for the whole pass, over the same record list this loop
    # already froze on the line above. Asking per entry was 197,334 directory reads for an
    # answer that cannot change while `recs` is held.
    known = designations()
    index = collections.defaultdict(list)     # norm-key -> [attestation dicts]
    total = 0
    for r in recs:
        src = r["source"]
        att = r.get("attestation", "Transcribed")
        for e in r["entries"]:
            total += 1
            key = norm(e.get("name"), known)
            if not key or len(key) < 3 or key in _STOPNAMES:
                continue
            index[key].append({
                "source": src,
                "name": e.get("name"),
                "type": e.get("type", ""),
                "topic": e.get("topic"),
                "magnitude": e.get("magnitude", "unassayed"),
                "attestation": att,
                # UNCAPPED. This was `[:400]`, and it is STORED DATA -- ENTITY_INDEX.json is
                # read by weave, cosmology_graph and thread_integrity, and by whatever reads it
                # next. A console preview may abbreviate; a file on disk that abbreviates is a
                # smaller universe wearing the shape of the real one, which is Hard Rule 0's
                # exact wording. 119,136 of 282,822 descriptions -- 42% -- were over 400
                # characters, and 45.4 million characters were being dropped without a word
                # anywhere in the file saying so. The one traced consumer (weave.py:204) slices
                # to [:400] and [:300] ITSELF for its own matching, so it is unaffected either
                # way; the cap was only ever costing every future reader. Order b974e9ed76de.
                "description": (e.get("description") or ""),
            })
    return recs, index, total


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--write", action="store_true")
    ap.add_argument("--min-sources", type=int, default=2,
                    help="a candidate needs this many DISTINCT sources")
    args = ap.parse_args()

    recs, index, total = build()

    # A collision only counts across DIFFERENT sources. Two entries with the same name inside
    # one source are that source's own duplication problem, not an omniverse identity.
    candidates = {}
    for key, hits in index.items():
        srcs = {h["source"] for h in hits}
        if len(srcs) >= args.min_sources:
            candidates[key] = hits

    print(f"records          : {len(recs)}")
    print(f"entries          : {total:,}")
    print(f"distinct keys    : {len(index):,}")
    print(f"CROSS-SOURCE     : {len(candidates):,} candidate entities "
          f"({sum(len(v) for v in candidates.values()):,} attestations)")
    print()

    spread = collections.Counter(len({h['source'] for h in v}) for v in candidates.values())
    print("attested in N sources:")
    for n in sorted(spread, reverse=True)[:10]:
        print(f"   {n:3d} sources : {spread[n]:5d} entities")
    print()

    top = sorted(candidates.items(), key=lambda kv: -len({h["source"] for h in kv[1]}))[:18]
    print("most cross-attested entities (the weave's backbone):")
    for key, hits in top:
        srcs = sorted({h["source"] for h in hits})
        print(f"   {hits[0]['name'][:26]:28s} {len(srcs):2d} sources: "
              f"{', '.join(s[:16] for s in srcs[:5])}{' …' if len(srcs) > 5 else ''}")

    if args.write:
        # ATOMIC: cosmology_graph, thread_integrity and weave all read these concurrently.
        silence.write_json(OUT_INDEX, {k: v for k, v in index.items()},
                           indent=None, ensure_ascii=False)
        silence.write_json(OUT_CAND, candidates, indent=2, ensure_ascii=False)
        print(f"\nwrote {OUT_INDEX}")
        print(f"wrote {OUT_CAND}  ({len(candidates):,} candidates for adjudication)")


if __name__ == "__main__":
    main()
