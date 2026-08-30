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
import sys
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
        # THE FAILURE IS NOT CACHED (order 75307186e12a). This stored `(sig, set())` -- an EMPTY
        # designation set under the LIVE corpus signature -- so ONE transient read failure was
        # served to every later call in the process, until some other writer touched a record
        # file and moved the signature. `_SEED` and the `_EARTH` pattern went with it. With no
        # designations "(Earth-616)" reads as a gloss rather than a continuity and Earth-616
        # Thor folds onto Earth-1610 Thor, which the header above prices as the expensive
        # direction: merging INVENTS a composite being and fuses two universes' evidence into
        # one worksheet. `load_records()` below is guarded against exactly this shape -- it only
        # writes `_REC_CACHE` after a successful read -- and this was not.
        #
        # Leaving `_DESIGNATIONS` untouched means the next call retries. The empty set is still
        # returned to THIS caller, which is the fail-closed answer for one call (an unknown
        # designation set splits nothing and merges nothing new); what it must not become is the
        # corpus's standing answer.
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
    unstattable = 0
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
                    # A file that vanished mid-enumeration. Refuse to hand out a signature this
                    # pass -- but FINISH WALKING THE DIRECTORY (order f70e87058f66).
                    #
                    # This used to `return (files, None)` from inside the loop, which dropped
                    # every entry the enumeration had not yet reached. Refusing the signature is
                    # correct and sufficient for the caches -- `load_records` checks
                    # `sig is not None`, so a None sig can never serve or poison one -- but the
                    # FILE LIST is the other half of the return value and it is consumed
                    # unconditionally: `files, sig = _records_sig()` then `for p in files`. A
                    # truncated corpus went back to the caller looking complete, and `build()`
                    # would then land a short ENTITY_INDEX.json / WEAVE_CANDIDATES.json over the
                    # files weave.py, cosmology_graph.py and thread_integrity.py read as the
                    # whole entity population. Skipping the one bad entry and continuing gives
                    # the caller everything that IS readable; the None signature still says the
                    # pass was not clean.
                    #
                    # AND IT IS NOTED. The old marker claimed exemption on the reasoning that
                    # this "just skips the cache fast-path", which was true of the signature and
                    # false of the file list -- an unstattable record is a real event in the one
                    # directory the two-writer contract governs, and nothing else records it.
                    silence.note("weave_index.py:records-entry-unstattable")
                    unstattable += 1
                    continue
                files.append(de.path)
                if m > newest:
                    newest = m
    except OSError:
        # A missing or unreadable directory. `glob` returned [] here rather than raising, and
        # the old `max(..., default=0)` then made that a real, cacheable (0, 0) signature.
        # Preserved exactly: callers depend on an empty corpus being a stable answer.
        _ = "silence-exempt: an unreadable records dir reads as an empty corpus, as it always did"
    files.sort()
    # A pass that could not stat every entry hands back a None signature -- the whole readable
    # file list, and an honest "do not treat this pass as clean".
    val = (files, None if unstattable else (len(files), newest))
    _SIG_MEMO.update({"at": now, "val": val})
    return val


def load_records():
    """All records with entries -- cached against the directory's own signature.

    63MB across 216 files (marvel.json alone is 27MB), and this was re-parsed on EVERY
    dashboard poll and three separate times per allsweep run (2026-08-23 optimization sweep).
    The signature is (count, max mtime), so any write anywhere in the directory invalidates.
    Callers get the shared list: read it, never mutate it.

    A None signature means "this pass could not stat every entry", not "this list is short":
    `_records_sig` finishes the enumeration either way (order f70e87058f66), so `files` is
    every record that could be read and parsing it is sound. The None only suppresses the
    cache, which is what it was always for."""
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


# The shortest normalised key that is evidence of anything in CROSS-SOURCE MATCHING. "X" and
# "Vi" collide with every other two-letter name in the omniverse, so a candidate built on one is
# noise. It is a rule about MATCHING, and it is applied where the matching happens (main()) --
# not in `build`, where it used to strike the entry out of ENTITY_INDEX.json itself. See the
# comment on the candidate loop.
MIN_MATCH_KEY = 3


def build():
    """-> (records, {norm-key: [attestations]}, entries seen, {reason: entries not indexed}).

    The fourth member is new with order e959f566275d and `main()` is its only caller anywhere in
    the tree (grepped): the build now has to be able to SAY what it did not index, because until
    it could, the only two numbers the report printed -- entries and distinct keys -- were both
    consistent with a silent loss.
    """
    recs = load_records()
    # Hoisted: one corpus-wide answer for the whole pass, over the same record list this loop
    # already froze on the line above. Asking per entry was 197,334 directory reads for an
    # answer that cannot change while `recs` is held.
    known = designations()
    index = collections.defaultdict(list)     # norm-key -> [attestation dicts]
    total = 0
    # WHAT DID NOT MAKE IT IN, BY REASON. Nothing counted these before, so `entries` and
    # `distinct keys` were printed beside a loss the report could not mention -- 415 entries on
    # the measurement that filed order e959f566275d, on the one line where a loss would show.
    excluded = collections.Counter()
    for r in recs:
        src = r["source"]
        att = r.get("attestation", "Transcribed")
        for e in r["entries"]:
            total += 1
            key = norm(e.get("name"), known)
            # THE len<3 RULE IS GONE FROM HERE (order e959f566275d). It is a MATCHING rule and it
            # was striking entries out of the STORED index -- the same fault as the [:400]
            # description cap removed from this loop by b974e9ed76de: a rule written for
            # candidate matching applied to data on disk. 257 real named characters ('Ed', 'X',
            # 'Vi', 'JJ', 'Dr. J', 'A.D.A.') did not exist to `weave.load_index`, which reads
            # ENTITY_INDEX.json as the whole entity population. The rule now lives in main()'s
            # candidate loop, where matching actually happens; the index keeps the entry.
            #
            # An entry with NO key at all is still not stored, and that is not a truncation: the
            # index is a mapping FROM the normalised key, so an entry whose name folds to the
            # empty string has no address in it, and filing three unrelated ones under "" would
            # merge them -- the direction this module's own header calls the expensive one.
            # It is counted and printed instead of being dropped silently.
            #
            # _STOPNAMES is UNTOUCHED and deliberately so: that half is order 8f50f37255b5,
            # which sits at OWNER because whether Fullmetal Alchemist's 'Father' is an entity of
            # the library is a curatorial call, not a maintenance one. Its casualties are now
            # counted here so the ruling can be made against a number.
            if not key:
                excluded["name folds to an empty key"] += 1
                continue
            if key in _STOPNAMES:
                excluded["_STOPNAMES (order 8f50f37255b5, at OWNER)"] += 1
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
                # anywhere in the file saying so. Order b974e9ed76de.
                #
                # THE "UNAFFECTED EITHER WAY" CLAUSE THAT USED TO END THIS COMMENT WAS WRONG, and
                # order 543cec75ad02 caught it: it said the one traced consumer sliced to [:400]
                # and [:300] itself for its own matching, so the cap cost only future readers.
                # It cost that consumer too. weave.filtered_index drops mechanics by looking for
                # rules voice in the description, and the window meant rules text starting after
                # character 300 was invisible to it -- 54 entities of 46,103 were kept that the
                # whole-description test drops, 2 of them inside the pair-weighting band. Those
                # windows are gone now; filtered_index searches the whole field.
                "description": (e.get("description") or ""),
            })
    return recs, index, total, excluded


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--write", action="store_true")
    ap.add_argument("--min-sources", type=int, default=2,
                    help="a candidate needs this many DISTINCT sources")
    args = ap.parse_args()

    recs, index, total, excluded = build()

    # A collision only counts across DIFFERENT sources. Two entries with the same name inside
    # one source are that source's own duplication problem, not an omniverse identity.
    candidates = {}
    short_keys = short_hits = 0
    for key, hits in index.items():
        # THE SHORT-KEY RULE, MOVED HERE FROM `build` (order e959f566275d). "X" and "Vi" collide
        # with every other two-letter name in the omniverse, so they are useless as MATCHING
        # evidence -- which is a statement about candidates, not about whether the entity exists.
        # Applied here, the entry keeps its place in ENTITY_INDEX.json (and therefore in
        # `weave.load_index`'s population and idf table) and only stays out of the candidate
        # list. The count is printed below rather than left to be rediscovered by the next audit.
        if len(key) < MIN_MATCH_KEY:
            short_keys += 1
            short_hits += len(hits)
            continue
        srcs = {h["source"] for h in hits}
        if len(srcs) >= args.min_sources:
            candidates[key] = hits

    print(f"records          : {len(recs)}")
    print(f"entries          : {total:,}")
    print(f"distinct keys    : {len(index):,}")
    print(f"CROSS-SOURCE     : {len(candidates):,} candidate entities "
          f"({sum(len(v) for v in candidates.values()):,} attestations)")
    # WHAT DID NOT MAKE IT, PRINTED WHERE THE TOTALS ARE (order e959f566275d). The report used to
    # show `entries` and `distinct keys` and nothing else, so an entry excluded from the stored
    # index left no trace at all in the one output a person reads to decide the build is sound.
    # Two different losses, kept apart because they are not the same act: an entry NOT INDEXED is
    # absent from ENTITY_INDEX.json and therefore from the weave's whole entity population; a
    # short key IS in the index and is only held out of candidate matching.
    n_ex = sum(excluded.values())
    print(f"not indexed      : {n_ex:,} entries ({n_ex / max(1, total):.2%})"
          + ("" if n_ex else "  — none"))
    for reason, n in sorted(excluded.items(), key=lambda kv: -kv[1]):
        print(f"   {n:>6,}  {reason}")
    print(f"indexed, not matched: {short_keys:,} keys / {short_hits:,} attestations with a "
          f"normalised key shorter than {MIN_MATCH_KEY} chars — in ENTITY_INDEX.json, held out "
          f"of candidates only")
    print()

    spread = collections.Counter(len({h['source'] for h in v}) for v in candidates.values())
    # EVERY BUCKET (orders 987bf4088026 / 4cea367c9235). This was `sorted(spread, reverse=True)
    # [:10]`, which sorts the KEYS descending and keeps ten -- so it printed the rarest,
    # widest-attested tail and silently dropped the head of the distribution, including the
    # 2-source bucket that by construction holds the large majority of candidates. The section
    # is headed "attested in N sources" with no "top" in the label, so it reads as the
    # distribution and was not one. The bucket count is bounded by the number of sources and is
    # a couple of dozen lines in practice -- cheaper than the leaderboard printed below it.
    print(f"attested in N sources ({len(spread)} buckets, all shown):")
    for n in sorted(spread, reverse=True):
        print(f"   {n:3d} sources : {spread[n]:5d} entities")
    print()

    ranked = sorted(candidates.items(), key=lambda kv: -len({h["source"] for h in kv[1]}))
    TOP_N = 18
    top = ranked[:TOP_N]
    # A RANKING PLUS A STATED FLOOR AND AN HONEST "AND N MORE" -- the ruling recorded at
    # health.py:576-585, applied here (order 4cea367c9235). Eighteen of 8,000-odd candidates
    # were printed under a heading calling them the weave's backbone with nothing saying so,
    # and this is a list a person reads to decide which entities to adjudicate. The eighteen
    # stay -- ranking is allowed -- but the cut is now named, with the floor it was made at.
    print("most cross-attested entities (the weave's backbone):")
    for key, hits in top:
        srcs = sorted({h["source"] for h in hits})
        print(f"   {hits[0]['name'][:26]:28s} {len(srcs):2d} sources: "
              f"{', '.join(s[:16] for s in srcs[:5])}"
              f"{f' … and {len(srcs) - 5} more sources' if len(srcs) > 5 else ''}")
    if len(ranked) > TOP_N:
        floor = len({h["source"] for h in ranked[TOP_N - 1][1]})
        print(f"   … and {len(ranked) - TOP_N:,} more cross-attested entities, every one "
              f"attested in {floor} sources or fewer — the full set is WEAVE_CANDIDATES.json "
              f"(written with --write)")

    if args.write:
        # ATOMIC: cosmology_graph, thread_integrity and weave all read these concurrently.
        #
        # GATED, BOTH HALVES, AND THE PAIR AS A PAIR. These two files are one join:
        # `candidates` is derived from `index` in this very function, `thread_integrity` matches
        # WEAVE_CANDIDATES.json keys against `weave_index.norm` output, and `weave.py` reads
        # ENTITY_INDEX.json. Discarding the verdicts left three failure modes all wearing the
        # same "wrote ..." line. Either file alone going stale is a stale read as fresh; ONE of
        # them landing is worse than neither, because the survivors then disagree about which
        # entities exist -- a candidate set indexed against attestations that were never
        # written, or an index whose cross-source candidates are a previous corpus's. The
        # concurrent readers named on the line above are exactly what denies these renames on
        # Windows, so this is the ordinary case here.
        ok_index = silence.write_json(OUT_INDEX, {k: v for k, v in index.items()},
                                      indent=None, ensure_ascii=False)
        ok_cand = silence.write_json(OUT_CAND, candidates, indent=2, ensure_ascii=False)
        print()
        print(f"wrote {OUT_INDEX}" if ok_index else
              f"NOT WRITTEN {OUT_INDEX}: replace refused; the file weave.py reads is the "
              f"previous build's")
        print(f"wrote {OUT_CAND}  ({len(candidates):,} candidates for adjudication)"
              if ok_cand else
              f"NOT WRITTEN {OUT_CAND}: replace refused; the file cosmology_graph.py and "
              f"thread_integrity.py read is the previous build's")
        if not (ok_index and ok_cand):
            silence.note("weave_index.py:write-denied")
            if ok_index != ok_cand:
                # The half-landed case gets its own sentence. Two files that are meant to be
                # one snapshot are now from two different builds, and nothing downstream can
                # tell -- neither file carries a build stamp the other could be checked against.
                print("SPLIT: one half of the pair landed and the other did not, so "
                      "ENTITY_INDEX.json and WEAVE_CANDIDATES.json are now from DIFFERENT "
                      "builds. Do not read either until this is rerun.", file=sys.stderr)
            print("Rerun `weave_index.py --write` once whatever is holding these open has "
                  "let go; the build itself is cheap and derived entirely from data/records.",
                  file=sys.stderr)
            return 1
    return 0


if __name__ == "__main__":
    # `main()`'s verdict has to reach the shell. A `--write` whose files did not land must not
    # exit 0 -- anything scripting this build (or a person reading `$?`) would take the refusal
    # for a success, which is the same defect one layer out.
    sys.exit(main())
