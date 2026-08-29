#!/usr/bin/env python3
"""
CLEANUP — the presentation defects the backscan turned up.

These were filed as "cosmetic", which was the wrong word for them. Every one of these ends up in
generated prose or on a shelf label, so they are hand design rather than noise:

  1. WIKI NAVIGATION captured as entities. "Season 1: Tyranny of Dragons" is a publication
     schedule; it is not a thing inside any fiction. Shelving it under Places or Events puts the
     scaffolding of the website into the encyclopedia.

  2. CEILING ENTITIES that are prose rather than names. Phase 1 was asked for the entity at a
     source's power ceiling and sometimes answered with a paragraph -- "Admiral Chang Wei's coup /
     near-WWIII escalation (Battlefield 4 ...), with the Battlefield 3 Paris nuclear detonation as
     the franchise's single most destructive on-screen object". A ceiling is a NAME; the argument
     for it belongs in the evidence field, which exists for exactly that.

  3. WIKI MARKUP inside descriptions. "France WP (フランス, Furansu ? )" carries a link marker and a
     broken ruby annotation. The description is the evidence every later volume quotes from, so
     markup here is markup in the finished book.

  4. DESCRIPTIONS too thin to be evidence -- "duplicate", "Dory's father." These are not wrong,
     they are simply not enough to write from, and they should be marked rather than silently
     carried as though they were.

Run with --apply to write. Without it, reports only.
"""
import argparse
import os
import re
import sys

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import pipeline as PL          # noqa: E402
import silence                 # noqa: E402

# Publication scaffolding and site furniture. Note "Season N" is included but a fiction's own
# in-universe seasons are not: the pattern requires the publication sense (a numbered season with
# a product subtitle, or a bare navigation word).
_NAV = re.compile(
    r"^(?:season\s+\d+\b|category:|list of |index of |gallery$|navigation$|main page$|"
    r"contents?$|glossary$|episodes?$|seasons?$|appearances?$|references?$|trivia$|"
    r"see also$|external links$|sitemap$|all pages$|recent changes$"
    # 'Character' matched and 'Character condition' did not, because the anchor demanded the word
    # end the name. Site furniture takes qualifiers like anything else does.
    #
    # READ THAT SENTENCE AS PAST TENSE -- it describes the state BEFORE this half of the
    # alternation was switched from `$` to `\b`, and the `\b` is the fix, not the fault. Sweep 33
    # read it as a claim about current behaviour, concluded the pattern was over-broad, and filed
    # it as a MAJOR. Measured against the live corpus at the time: of 69,652 catalogued entries,
    # this half matches 16, ten of them the bare word and six of them qualified --
    # 'Character condition', 'Character Profiles', 'Character guide', and three
    # 'Characters/Mass Effect ...' index pages. Every one is the wiki furniture the `\b` was added
    # to reach; not one is an entity of any fiction. The first half of the alternation keeps `$`
    # on purpose, because 'Gallery', 'Trivia' and 'Contents' are common enough words that a
    # qualified form is more likely a real name than a nav page. The two halves differ because the
    # words differ.
    r"|characters?\b|gameplay\b|mechanics\b|controls\b|achievements?\b|trophies\b"
    r"|downloadable content\b|patch notes?\b|version history\b|soundtrack\b)", re.I)

# Wikipedia link markers, broken ruby annotations, citation stubs.
_MARKUP = [
    (re.compile(r"\s*\bWP\b(?=\s*[\(,]|\s*$)"), ""),          # "France WP (..." link marker
    (re.compile(r"\s*\(\s*[^()]*?,\s*[A-Za-z]+\s*\?\s*\)"), ""),   # "(フランス, Furansu ? )"
    (re.compile(r"\s*\[\s*\d+\s*\]"), ""),                    # [1] citation stubs
    (re.compile(r"\s*\[(?:citation needed|edit|sic)\]", re.I), ""),
    (re.compile(r"\s*\?\s*(?=\))"), ""),                      # stray ? before a close paren
    (re.compile(r"\s+([,.;:!?])"), r"\1"),        # "on Luna , and" -- wiki spacing
    (re.compile(r"\(\s+"), "("),
    (re.compile(r"\s+\)"), ")"),
    (re.compile(r"\s{2,}"), " "),
]

_THIN = 15

# An entry with NO description that names a proficiency, variant or slot is a rules construct that
# reached the catalogue through a gap. Real things with thin descriptions -- a Wooden Stake, a
# Newspaper -- are kept and marked; these are struck, because they were never entities.
_EMPTY_MECHANIC = re.compile(
    r"(proficienc|variant$|feature$|trait$|slot$|score improvement|ability score|"
    r"saving throw|hit dice|starting equipment|multiclass|subclass$|archetype$)", re.I)


# GUARD. Three regexes in this project have been silently broken by an escape being eaten in
# transit -- a word boundary arriving as a literal backspace (0x08), which matches nothing and
# fails silently. A pattern that cannot match is worse than a wrong pattern: it reports zero
# violations and looks like success. This refuses to load rather than pass quietly.
#
# THE ROSTER USED TO CARRY `("_SETTING_META", None)`, which `_p is not None` always skipped --
# `_SETTING_META` is not a name in this file at all, it lives at `pipeline.py:1204` (imported
# above as `PL`) and is exactly the `\b`-fenced shape this guard exists to catch. And `_MARKUP`
# (above) was not on the roster at all, though its own first pattern opens with the identical
# `\bWP\b` escape -- if either arrived mangled, `clean_description` would silently strip nothing.
for _n, _p in (("_NAV", _NAV), ("_EMPTY_MECHANIC", _EMPTY_MECHANIC),
               ("_SETTING_META", PL._SETTING_META),
               *[(f"_MARKUP[{_i}]", _pat) for _i, (_pat, _rep) in enumerate(_MARKUP)]):
    if any(ord(c) < 32 for c in _p.pattern):
        raise SystemExit(f"{_n} contains a control character; the escape was mangled in transit")


def clean_description(d):
    out = d or ""
    for pat, rep in _MARKUP:
        out = pat.sub(rep, out)
    return out.strip()


def clean_ceiling(ce, entry_names):
    """Reduce a prose ceiling to the name it is about.

    Strategy, in order: exact match; the text before the first delimiter; the longest catalogued
    entry name that appears inside the prose. If none of those land, the ceiling is left ALONE and
    reported -- guessing a name would be worse than admitting phase 1 answered the wrong question.
    """
    ce = (ce or "").strip()
    if not ce:
        return ce, "empty"
    low = {n.lower(): n for n in entry_names}
    if ce.lower() in low:
        return low[ce.lower()], "exact"

    head = re.split(r"\s*[/(,;:]|\s+--\s+|\s+—\s+", ce)[0].strip()
    if head and head.lower() in low:
        return low[head.lower()], "head"

    # A SUBSTRING strategy was tried and removed: on "The Apothicons (with their corrupted
    # emissary, the Shadow Man / Doctor Monty)" it returned Doctor Monty -- a different entity,
    # pulled out of a parenthetical.
    #
    # A PREFIX match is a different proposition and is safe. "Skarsgard Abraxis" is the opening of
    # the entry 'Skarsgard Abraxis ("Skars"; also Admiral/Commander Abraxis...)' -- the same being,
    # written at greater length. A name cannot prefix an unrelated entry by accident the way it can
    # appear inside one.
    low_pref = [n for n in entry_names
                if n.lower().startswith(ce.lower()) and len(ce) >= 6]
    if len(low_pref) >= 1:
        return min(low_pref, key=len), "prefix"
    return ce, "unresolved"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--apply", action="store_true")
    args = ap.parse_args()

    nav, ceil_fixed, ceil_unres, desc_fixed, thin = [], [], [], [], []
    unwritten = []

    for path, rec in PL.records():
        changed = False
        src = rec["source"]
        names = [(e.get("name") or "").strip() for e in rec["entries"] if e.get("name")]

        syn = rec.get("synthesis") or {}
        ce = (syn.get("ceiling_entity") or "").strip()
        if ce:
            fixed, how = clean_ceiling(ce, names)
            if how == "unresolved":
                ceil_unres.append((src, ce[:70]))
            elif fixed != ce:
                ceil_fixed.append((src, ce[:52], fixed, how))
                if args.apply:
                    syn["ceiling_entity"] = fixed
                    syn.setdefault("ceiling_prose", ce)   # the argument is kept, not discarded
                    changed = True

        for e in rec["entries"]:
            if not e.get("catalogued"):
                continue
            nm = (e.get("name") or "").strip()
            if nm and _NAV.match(nm):
                nav.append((src, nm))
                if args.apply:
                    e["catalogued"] = False
                    e["excluded"] = "wiki navigation, not an entity of any fiction"
                    changed = True
                continue

            d = e.get("description") or ""
            if not d.strip() and _EMPTY_MECHANIC.search(nm):
                nav.append((src, nm + "  [empty mechanic]"))
                if args.apply:
                    e["catalogued"] = False
                    e["excluded"] = "rules construct with no description; not an entity"
                    changed = True
                continue
            cd = clean_description(d)
            if cd != d:
                desc_fixed.append((src, nm, d[:46], cd[:46]))
                if args.apply:
                    e["description"] = cd
                    changed = True
            if len(cd) < _THIN:
                thin.append((src, nm, cd))
                if args.apply:
                    e["thin_description"] = True
                    # `changed` was never set on this branch, so a record whose ONLY edit was
                    # a thin-description mark was never handed to write_record -- the flag was
                    # set on an in-memory dict and dropped when the loop moved on. The module's
                    # docstring says thin entries are "marked, not deleted"; for every entry
                    # that had no other defect, they were neither. Its two sibling branches
                    # both set it; this one was simply missed. (run #29, batch 05, reproduced.)
                    changed = True

        if changed:
            # GATED, like every other caller of the two-writer contract (`catalogue_web.py:498`
            # gates `write_record_catalogue` the same way). `write_record` answers False for two
            # separate refusals -- a denied atomic replace, and its own deliberate "could not
            # read this record to merge, REFUSING to write the in-memory copy over it" -- and
            # this discarded both. Every correction below is reported from the in-memory lists,
            # which are appended to BEFORE the write, so a record that refused printed exactly
            # like a record that was cleaned and the run still ended on "APPLIED." Re-running
            # recovers the edit; a run that says it applied edits it did not is what stops
            # anyone from re-running. (run #37 sweep.)
            if not PL.write_record(path, rec):
                silence.note("cleanup.py:record-write-refused")
                unwritten.append(src)

    print("=" * 96)
    print("CLEANUP — presentation defects from the backscan")
    print("=" * 96)
    print(f"\n1. wiki navigation removed from the catalogue : {len(nav):,}")
    for s, n in nav[:5]:
        print(f"     {s[:26]:<28}{n}")
    print(f"\n2. ceiling entities reduced to a name        : {len(ceil_fixed):,}")
    for s, before, after, how in ceil_fixed[:6]:
        print(f"     {s[:22]:<24}{how:<10}{before!r}")
        print(f"     {'':<24}{'-> ':<10}{after!r}")
    print(f"   still unresolved (left alone, not guessed) : {len(ceil_unres):,}")
    for s, ce in ceil_unres[:4]:
        print(f"     {s[:26]:<28}{ce}")
    print(f"\n3. descriptions with markup stripped         : {len(desc_fixed):,}")
    for s, n, b, a in desc_fixed[:5]:
        print(f"     {str(n)[:22]:<24}{b!r}")
        print(f"     {'':<24}-> {a!r}")
    print(f"\n4. descriptions too thin to write from       : {len(thin):,}  (marked, not deleted)")
    for s, n, d in thin[:5]:
        print(f"     {str(n)[:26]:<28}{d!r}")

    if unwritten:
        # The counts above are what this pass FOUND. These are the records it could not land,
        # and they are listed by name rather than summarised: "APPLIED." over a refused write is
        # the exact reading that stops the re-run which would have fixed it.
        print(f"\nNOT WRITTEN — {len(unwritten):,} record(s) refused the write (a denied "
              f"atomic replace, or write_record declining to overwrite a record it could not "
              f"read to merge). Their corrections above are NOT on disk; re-run to retry.")
        for s in unwritten[:12]:
            print(f"     {s}")
        if len(unwritten) > 12:
            print(f"     ... and {len(unwritten) - 12:,} more")

    if not args.apply:
        print("\nDRY RUN. Re-run with --apply to write.")
    elif unwritten:
        print(f"\nPARTIALLY APPLIED — {len(unwritten):,} record(s) above did not land.")
    else:
        print("\nAPPLIED.")
    return 1 if unwritten else 0


if __name__ == "__main__":
    sys.exit(main())
