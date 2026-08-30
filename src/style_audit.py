#!/usr/bin/env python3
"""
STYLE AUDIT — catch repetition across chapters, which no single chapter can see.

Ground Rule 6 in the style prompt forbids reusing a construction within a chapter. It cannot
forbid reusing one across chapters, because each chapter is a separate generation call and the
model has no memory of the other two hundred. Left alone, a corpus of 52,000 entries converges on
a handful of sentence shapes and reads like one entry copied out with the nouns changed.

This reads generated output and reports:

    OPENERS       how many Records begin the same way
    CONSTRUCTIONS the banned shapes from Ground Rule 6, counted corpus-wide
    DENSITY       em-dashes per entry, and how many entries end on a turn
    VOCABULARY    words carrying far more weight than their frequency warrants

Run it on the pilot before scaling. Run it again after every few hundred chapters.
"""
import argparse
import collections
import glob
import os
import re
import sys

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# The banned set is IMPORTED, not restated here. Kept in two places these lists drift, and a
# phrase banned in the prompt but missing from the checker goes unnoticed for fifty thousand
# entries. tells.py is the single source; the style prompt's Rule 7 is generated from it too.
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import tells as TELLS          # noqa: E402

_WATCHED = (len(TELLS.ALL_PATTERNS) + len(TELLS.LEXICAL)
            + len(TELLS.LEXICAL_FICTION))

# ENDING ON A TURN means the ENTRY's last sentence swings on a conjunction, and the anchor has
# to be the end of the RECORD, not the end of a line.
#
# This was `...\.\s*$` compiled with `re.M`, and under `re.M` a `$` matches before EVERY newline.
# Records here are multi-paragraph almost without exception (1,270 of 1,278 in the withdrawn
# pilot), so the pattern was really asking "does any PARAGRAPH anywhere in this entry end on a
# turn" -- a far easier question, matched on 55 records where only 3 actually closed that way.
# The measured rate came out 4.3% against a true 0.2%.
#
# An inflated number here is not a harmless overcount. This is the prose-quality gate: a high
# turn rate reads as evidence that the voice is being CONTROLLED and the corpus is converging on
# one shape, so the inflation makes the checker look stricter than it is and would be cited as
# proof of a discipline that was never measured. Under-reporting a tell is a missed defect;
# over-reporting one is a fabricated pass mark.
#
# `\Z` anchors at the end of the string and nowhere else, so `re.M` is neither needed nor wanted
# (nothing else in the pattern is line-oriented). `[^.\n]` keeps the turn clause on one line --
# with `[^.]` the run could swallow paragraph breaks and reach a full stop several paragraphs
# later, which is the same false positive arriving by another door.
TURN_ENDING = re.compile(
    r"(?:\.|\?)\s+(?:And|But|Yet|Still|Which|That)\b[^.\n]{0,80}\.\s*\Z")


def entries(text):
    """Split a generated chapter into its entries."""
    # One codepoint, written once. The class used to read `[◈◈]` -- the SAME U+25C8 listed
    # twice, which a reader reasonably takes for two different entry markers being accepted.
    parts = re.split(r"^◈\s*", text, flags=re.M)
    return [p for p in parts[1:] if p.strip()]


def record_of(entry):
    m = re.search(r"The Record\.?\s*(.+?)(?=\n\s*(?:Contradictions|Marginalia|▣|⌁)|\Z)",
                  entry, re.S)
    return (m.group(1) if m else entry).strip()


def opener(rec, words=4):
    w = re.findall(r"[A-Za-z']+", rec)
    return " ".join(w[:words]).lower()


def opener_shape(rec):
    """The grammatical shape of an opening, so 'Vorgansharax is a' and 'Tiamat is a' collide.

    A first version marked every capitalised word NAME, so an entry opening 'Aminion Athuri, the
    Astarii envoy' came out as 'NAME NAME NAME NAME' and collided with any other multi-word proper
    noun. That reported 27% repetition where there was none. Names are collapsed to a single NAME
    token now, and the shape is read from the FUNCTION words that follow, which is where a
    repeated construction actually lives.
    """
    w = re.findall(r"[A-Za-z']+", rec)[:8]
    if not w:
        return ""
    out, seen_name = [], False
    for x in w:
        low = x.lower()
        if low in FUNCTION:
            out.append(low)
            seen_name = False
        elif x[:1].isupper():
            if not seen_name:
                out.append("NAME")
                seen_name = True
        else:
            out.append(low)
            seen_name = False
        if len(out) >= 4:
            break
    return " ".join(out)


FUNCTION = {"is", "was", "are", "were", "a", "an", "the", "of", "in", "on", "at", "to",
            "and", "but", "had", "has", "have", "its", "his", "her", "their", "it",
            "this", "that", "which", "who", "whose", "for", "from", "by", "with"}

# Template field names and Custodial furniture. These recur because the FORM requires them, not
# because the prose is repetitive, and counting them buries the words that matter.
TEMPLATE_WORDS = {
    "strength", "dexterity", "constitution", "intelligence", "wisdom", "charisma",
    "magnitude", "shelfmark", "attestation", "marginalia", "instrument", "threads",
    "contradictions", "unassayed", "transcribed", "witnessed", "reconstructed",
    "disputed", "pending", "entanglement", "custodial", "custodes", "record",
    "uninstrumented", "applicable", "transcendence",
}


def audit(texts):
    recs, ems, turns = [], 0, 0
    for t in texts:
        for e in entries(t):
            r = record_of(e)
            if not r:
                continue
            recs.append(r)
            ems += r.count("—") + r.count(" -- ")
            if TURN_ENDING.search(r):
                turns += 1

    n = max(1, len(recs))
    rep = collections.Counter()
    for r in recs:
        for name, c in TELLS.scan(r).items():
            rep[name] += c

    return {
        "entries": len(recs),
        "openers": collections.Counter(opener(r) for r in recs),
        "shapes": collections.Counter(opener_shape(r) for r in recs),
        "banned": rep,
        "em_per_entry": ems / n,
        "turn_endings": turns,
        "turn_rate": turns / n,
        "vocab": collections.Counter(
            w.lower() for r in recs for w in re.findall(r"[A-Za-z]{6,}", r)
            if w.lower() not in TEMPLATE_WORDS and not w[:1].isupper()),
    }


def _cut(shown, total, unit):
    """The house line for a ranking that had to be cut, from repass_bands.py:106-113.

    THREE OF THE FOUR RANKINGS IN `report` WERE CUT WITH NO REMAINDER (order 1cb7bd3ad0ce).
    OPENING SHAPES, EXACT OPENERS and VOCABULARY printed a `most_common(...)` window under a
    heading that describes the CORPUS -- "two entries should not start the same way" -- with no
    count of how many shapes or openers there were in total, so a corpus with 400 repeated
    openers and a corpus with 9 printed identically. This is the report a person reads to decide
    whether the voice is converging, i.e. a ranking somebody reads to act on: ranking is fine
    and stays, the REMAINDER has to be visible (Hard Rule 0).
    """
    if shown < total:
        return (f"showing {shown:,} of {total:,} {unit}; "
                f"{total - shown:,} more not shown")
    return f"{total:,} {unit}, all shown"


def report(a, top=8):
    n = a["entries"]
    print("=" * 84)
    print(f"STYLE AUDIT — {n:,} entries")
    print("=" * 84)

    shapes = a["shapes"].most_common(top)
    print(f"\nOPENING SHAPES (two entries should not start the same way) "
          f"— {_cut(len(shapes), len(a['shapes']), 'distinct shapes')}")
    for shape, c in shapes:
        flag = "  OVERUSED" if c / max(1, n) > 0.12 else ""
        print(f"   {c:>5}  {c/max(1,n):>6.1%}  {shape}{flag}")

    # TWO CUTS, NOT ONE: the `most_common(top)` window AND the `c > 1` filter. The population
    # this block is about is the openers that REPEAT, so that is what the remainder counts --
    # saying "8 of 40,000 openers" here would answer a question nobody asked.
    repeated_total = sum(1 for c in a["openers"].values() if c > 1)
    reps = [(o, c) for o, c in a["openers"].most_common(top) if c > 1]
    print(f"\nEXACT OPENERS repeated — {_cut(len(reps), repeated_total, 'repeated openers')}")
    if reps:
        for o, c in reps:
            print(f"   {c:>5}  {o}")
    else:
        print("   none")

    print(f"\nMACHINE TELLS  ({_WATCHED} patterns watched, style prompt Rule 7)")
    if a["banned"]:
        for k, c in sorted(a["banned"].items(), key=lambda kv: -kv[1])[:14]:
            rate = c / max(1, n)
            flag = "  OVERUSED" if rate > 0.05 else ""
            print(f"   {c:>5}  {rate:>6.2%}/entry  {k}{flag}")
        print(f"   ({len(a['banned'])} distinct tells present)")
    else:
        print("   none")

    print("\nDENSITY")
    print(f"   em-dashes per entry   {a['em_per_entry']:.2f}"
          f"{'   OVER (target <= 1)' if a['em_per_entry'] > 1 else ''}")
    print(f"   entries ending on a turn  {a['turn_endings']:,}  ({a['turn_rate']:.1%})"
          f"{'   OVER (target <= 25%)' if a['turn_rate'] > 0.25 else ''}")

    # THE CAP IS GONE HERE RATHER THAN DECLARED (order 1cb7bd3ad0ce). This was
    # `most_common(10)` with the rate test applied INSIDE the loop, which is two separate cuts:
    # a word carrying more than half an occurrence per entry could be ranked eleventh and never
    # print at all, and nothing said so. The rate test is the population -- these are the words
    # actually carrying unusual weight -- so it is applied first and every one of them prints.
    # The filter keeps the list naturally short; a corpus where it does not is a corpus whose
    # whole list a reader needs.
    heavy = [(w, c) for w, c in a["vocab"].most_common() if c / max(1, n) > 0.5]
    print(f"\nVOCABULARY carrying unusual weight "
          f"— {_cut(len(heavy), len(heavy), 'words over 0.50/entry')}")
    for w, c in heavy:
        print(f"   {c:>5}  {c/max(1,n):>5.2f}/entry  {w}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--path", default=os.path.join(HERE, "output", "raw"))
    ap.add_argument("--self-test", action="store_true")
    args = ap.parse_args()

    if args.self_test:
        # THIS SELF-TEST USED TO PASS WITH THE SHAPE DETECTOR COMPLETELY BROKEN (order
        # 2487a74f7027). It asserted `a["banned"] and max(a["shapes"].values()) >= 2`, and
        # `max(...) >= 2` is satisfied by ANY two entries sharing a shape -- including the
        # degenerate case where `opener_shape` returns the SAME value for every entry.
        # Reproduced by monkeypatching it to return "": the shapes became {"": 3} and ok was
        # STILL True, the broken detector reporting MORE apparent repetition (3) than the
        # working one (2). Over-collapsing is precisely the regression `opener_shape`'s own
        # docstring records -- "reported 27% repetition where there was none" -- so the test was
        # blind to the one fault the function has actually had. `a["banned"]` truthiness had the
        # same hole: a `TELLS.scan` degenerated to matching one pattern still satisfies it.
        # And there was no negative control at all, so a detector that flagged EVERYTHING passed
        # too. A check that cannot fail looks exactly like a check that passed, and this one
        # returns an exit code, so it gets read as a verdict.
        #
        # The fixtures are now asserted by NAME and by COUNT, which fails an over-split as
        # loudly as an over-collapse, and a second VARIED fixture is required to come back
        # clean.
        bad = ["◈ ALPHA\nThe Record. Alpha is a city of the northern reach. It endures.\n"
               "◈ BETA\nThe Record. Beta is a city of the southern reach. It endures.\n"
               "◈ GAMMA\nThe Record. Gamma is not merely a fortress; it is a warning — and it "
               "stands as a testament to the age. And so it remains.\n"]
        # THE NEGATIVE CONTROL: three entries that share no construction and trip no tell.
        # Deliberately plain prose -- if this one ever comes back dirty, the finding is in the
        # detector, not in the fixture.
        good = ["◈ DELTA\nThe Record. Delta rose from silt at the mouth of a slow river.\n"
                "◈ EPSILON\nThe Record. Merchants keep three ledgers here, and audit none of "
                "them.\n"
                "◈ ZETA\nThe Record. Nobody agrees where the wall ends.\n"]
        a = audit(bad)
        report(a)
        b = audit(good)

        # The three tells GAMMA is built to trip, asserted as a SUBSET rather than as the exact
        # set on purpose: `tells.py` is the single source for the banned list and it is expected
        # to GROW, so an equality here would be a net that has to be edited before an unrelated
        # addition can land. The over-firing direction is covered from the other side instead --
        # the varied fixture must report NO tell at all.
        want_tells = {"not merely X but Y", "stands as a testament", "word: testament"}
        checks = [
            ("the repetitive fixture splits into its three entries", a["entries"] == 3),
            ("ALPHA and BETA collide on one shape", a["shapes"].get("NAME is a city") == 2),
            ("GAMMA does not join them", a["shapes"].get("NAME is not merely") == 1),
            ("and no shape is invented or collapsed away", len(a["shapes"]) == 2),
            ("GAMMA's tells are found by name: " + ", ".join(sorted(want_tells)),
             want_tells <= set(a["banned"])),
            ("the varied fixture splits into its three entries", b["entries"] == 3),
            ("a varied corpus repeats no shape", max(b["shapes"].values()) == 1),
            ("and trips no banned tell", not b["banned"]),
        ]
        print()
        for label, passed in checks:
            print(f"   {'ok  ' if passed else 'FAIL'}  {label}")
        ok = all(passed for _, passed in checks)
        print(f"\nself-test {'PASSED' if ok else 'FAILED'} — the checker detects repetition, "
              f"and leaves a corpus that has none alone")
        return 0 if ok else 1

    files = sorted(glob.glob(os.path.join(args.path, "**", "*.md"), recursive=True)) + \
        sorted(glob.glob(os.path.join(args.path, "**", "*.txt"), recursive=True))
    if not files:
        print(f"no generated output under {args.path}")
        print("Run this on the pilot before scaling, and again every few hundred chapters.")
        return 0
    texts = []
    for f in files:
        with open(f, encoding="utf-8", errors="replace") as fh:
            texts.append(fh.read())
    print(f"read {len(files)} files")
    report(audit(texts))
    return 0


if __name__ == "__main__":
    sys.exit(main())
