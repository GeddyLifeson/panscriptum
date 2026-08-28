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

TURN_ENDING = re.compile(
    r"(?:\.|\?)\s+(?:And|But|Yet|Still|Which|That)\b[^.]{0,80}\.\s*$", re.M)


def entries(text):
    """Split a generated chapter into its entries."""
    parts = re.split(r"^[◈◈]\s*", text, flags=re.M)
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


def report(a, top=8):
    n = a["entries"]
    print("=" * 84)
    print(f"STYLE AUDIT — {n:,} entries")
    print("=" * 84)

    print("\nOPENING SHAPES (two entries should not start the same way)")
    for shape, c in a["shapes"].most_common(top):
        flag = "  OVERUSED" if c / max(1, n) > 0.12 else ""
        print(f"   {c:>5}  {c/max(1,n):>6.1%}  {shape}{flag}")

    print("\nEXACT OPENERS repeated")
    reps = [(o, c) for o, c in a["openers"].most_common(top) if c > 1]
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

    print("\nVOCABULARY carrying unusual weight")
    for w, c in a["vocab"].most_common(10):
        if c / max(1, n) > 0.5:
            print(f"   {c:>5}  {c/max(1,n):>5.2f}/entry  {w}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--path", default=os.path.join(HERE, "output", "raw"))
    ap.add_argument("--self-test", action="store_true")
    args = ap.parse_args()

    if args.self_test:
        # The checker has to catch a corpus that is obviously repetitive, or it proves nothing.
        bad = ["◈ ALPHA\nThe Record. Alpha is a city of the northern reach. It endures.\n"
               "◈ BETA\nThe Record. Beta is a city of the southern reach. It endures.\n"
               "◈ GAMMA\nThe Record. Gamma is not merely a fortress; it is a warning — and it "
               "stands as a testament to the age. And so it remains.\n"]
        a = audit(bad)
        report(a)
        ok = (a["banned"] and max(a["shapes"].values()) >= 2)
        print(f"\nself-test {'PASSED' if ok else 'FAILED'} — the checker detects repetition")
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
