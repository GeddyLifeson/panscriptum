#!/usr/bin/env python3
"""
BACKSCAN — an audit of everything catalogued so far.

Two passes, because they answer different questions:

  INVARIANTS  run over EVERY entry. These are the rules the pipeline claims to enforce, checked
              from outside rather than trusting the code that enforces them. Cheap, exhaustive,
              and the only way to catch a rule that quietly stopped applying.

  SAMPLE      a seeded random draw, printed in full so a person can read actual rows. Invariants
              catch violations of rules we thought to write; reading catches the rest.

The seed is fixed so the same sample can be re-read after a fix.
"""
import argparse
import collections
import os
import random
import re
import sys
import textwrap

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import pipeline as PL          # noqa: E402

# Wiki navigation artefacts. These are not entities in any fiction; they are the scaffolding of
# the site the catalogue was drawn from, and they should never have been captured.
#
# The anchors are per-alternative and deliberately uneven, and carry the shape cleanup.py's `_NAV`
# was already corrected to. One trailing `\b` shared by the whole group silently made this a
# PREFIX test rather than a name test: 'Timeline of the Fallen Empire', 'Seasons of War',
# 'Gallery of Rogues', 'References Codex' and 'Navigation Beacon' all matched, because each merely
# OPENS with a furniture word. BACKSCAN is trusted precisely because it checks from outside, so a
# bucket that over-fires on real entities is worse than one that misses -- it buries the genuine
# scaffolding hits it exists to surface, under a flood of unrelated entities. So the words that
# are furniture only when they ARE the whole name end at `$`, while the ones that are furniture
# as an opening -- 'Category:', 'List of ...', 'Index of ...', and 'Characters', which takes
# qualifiers the way any other piece of site furniture does -- keep the `\b` and stay prefixes.
_JUNK = re.compile(r"^(?:characters?\b|category:|list of |index of |gallery$|navigation$|"
                   r"main page$|contents?$|glossary$|timeline$|episodes?$|seasons?$|"
                   r"appearances?$|references?$|trivia$|see also$|external links$)", re.I)

VALID_BANDS = set(PL.BANDS)


def _field(label, text, indent="     ", width=96):
    """Print one long sample field WRAPPED, never sliced (order 01eff1b24759).

    The SAMPLE pass is documented at the top of this file as "printed in full so a person can
    read actual rows", and it was not: description came out at `[:150]` and the feat at `[:110]`
    / `[:120]`, with no marker of any kind. The feat slice was the one that cost something --
    the BANDED SAMPLE is introduced as "every one of these makes a claim" and prints exactly one
    line of evidence per row, so a measurement sitting past character 120 was cut mid-sentence
    and the reader was shown LESS than `valid_scale_note` and `meta_violations` saw. That is the
    wrong way round for a pass whose whole job is to catch what the invariants did not think to
    ask. These blocks are 10 and 14 rows, not a corpus dump, so the fix is to wrap rather than
    to slice-with-a-marker.
    """
    body = str(text) if str(text).strip() else "(none)"
    print(textwrap.fill(body, width=width,
                        initial_indent=indent + label,
                        subsequent_indent=indent + " " * len(label)))


def audit_invariants(recs):
    fails = collections.defaultdict(list)
    stats = collections.Counter()

    for path, rec in recs:
        src = rec["source"]
        syn = rec.get("synthesis") or {}

        # -- synthesis-level -------------------------------------------------------------
        if syn:
            stats["sources_with_synthesis"] += 1
            ce = (syn.get("ceiling_entity") or "").strip()
            band = syn.get("provisional_magnitude")
            if band not in VALID_BANDS:
                fails["synthesis: band not on the ladder"].append(f"{src}: {band!r}")
            if band != "unassayed" and not ce:
                fails["synthesis: band claimed with no ceiling entity"].append(src)
            if ce:
                names = {(e.get("name") or "").strip().lower() for e in rec["entries"]}
                if ce.lower() not in names:
                    fails["synthesis: ceiling entity not among the source's own entries"].append(
                        f"{src}: {ce!r}")
            ev = syn.get("evidence") or ""
            if band != "unassayed" and not PL.valid_scale_note(ev):
                fails["synthesis: band rests on evidence that is not a scale feat"].append(
                    f"{src}: {ev[:60]!r}")

        # -- entry-level -----------------------------------------------------------------
        for e in rec["entries"]:
            if not e.get("catalogued"):
                continue
            stats["entries_catalogued"] += 1
            nm = (e.get("name") or "").strip()
            band = e.get("magnitude")
            sn = e.get("scale_note") or ""
            topic = e.get("topic")
            cat = e.get("category")

            if not nm:
                fails["entry: no name"].append(src)
            elif _JUNK.match(nm):
                fails["entry: wiki navigation artefact, not an entity"].append(f"{src}: {nm!r}")

            if band is not None and band not in VALID_BANDS:
                fails["entry: band not on the ladder"].append(f"{src}/{nm}: {band!r}")

            # THE core invariant: no feat, no band.
            if band and band != "unassayed":
                stats["entries_banded"] += 1
                if not sn:
                    fails["entry: BAND WITH NO SCALE NOTE (core invariant)"].append(f"{src}/{nm}")
                elif not PL.valid_scale_note(sn):
                    fails["entry: band rests on a note that no longer passes the gate"].append(
                        f"{src}/{nm}: {sn[:60]!r}")

            if sn:
                stats["entries_with_scale_note"] += 1
                meta = PL.meta_violations(sn)
                if meta:
                    fails["entry: meta-language in scale note"].append(f"{src}/{nm}: {meta}")
                if PL.scale_note_needs_rephrase(sn):
                    stats["scale_notes_flagged_for_rephrase"] += 1

            if topic and topic not in PL.TOPICS:
                fails["entry: topic not in the encyclopedia series"].append(f"{src}/{nm}: {topic!r}")
            if cat and cat not in PL.CATEGORIES:
                fails["entry: category not on the list"].append(f"{src}/{nm}: {cat!r}")

            d = e.get("description") or ""
            if not d.strip():
                fails["entry: empty description"].append(f"{src}/{nm}")
            elif len(d.strip()) < 15:
                fails["entry: description too short to be evidence"].append(
                    f"{src}/{nm}: {d[:40]!r}")

    return fails, stats


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--sample", type=int, default=14)
    ap.add_argument("--seed", type=int, default=20260820)
    args = ap.parse_args()

    recs = PL.records()
    print("=" * 96)
    print("BACKSCAN — everything catalogued so far")
    print("=" * 96)

    fails, stats = audit_invariants(recs)
    print(f"\nsources {len(recs)} | with synthesis {stats['sources_with_synthesis']} | "
          f"entries catalogued {stats['entries_catalogued']:,}")
    print(f"entries banded {stats['entries_banded']:,} | "
          f"with a scale note {stats['entries_with_scale_note']:,} | "
          f"flagged for rephrase {stats['scale_notes_flagged_for_rephrase']:,}")

    print("\n" + "-" * 96)
    print("INVARIANTS (checked on every entry, from outside the code that enforces them)")
    print("-" * 96)
    if not fails:
        print("  all clean")
    total_f = 0
    for k in sorted(fails, key=lambda x: -len(fails[x])):
        v = fails[k]
        total_f += len(v)
        # THE DENOMINATOR COMES FROM THE CLASS, NOT FROM ONE COUNTER (order 220a0e95b471).
        # Every rate here used to be divided by `entries_catalogued`, including the four
        # synthesis-level classes above, which append once per SOURCE. Measured: a synthesis
        # fault touching 20 of 215 sources -- 9.30% of them -- printed as "0.01% of catalogued
        # entries". Three orders of magnitude, in the reassuring direction, on the one report
        # whose premise is checking the pipeline's claims from outside. A source-level fault
        # could never look like more than a rounding error, which is how a systematic synthesis
        # defect gets read as noise. The keys already carry their own class as a prefix, so the
        # population is read off the key, and the UNIT is printed so the reader can see which
        # population the percentage is against.
        if k.startswith("synthesis:"):
            denom, unit = stats["sources_with_synthesis"], "of sources with synthesis"
        else:
            denom, unit = stats["entries_catalogued"], "of catalogued entries"
        rate = len(v) / max(1, denom)
        print(f"\n  {k}")
        print(f"     {len(v):,} occurrences ({rate:.2%} {unit}; {denom:,} in that population)")
        for x in v[:4]:
            print(f"       - {x}")
        if len(v) > 4:
            print(f"       ... and {len(v)-4:,} more")
    print(f"\n  TOTAL violations: {total_f:,}")

    # ---------------------------------------------------------------- readable sample
    rng = random.Random(args.seed)
    pool = [(rec["source"], e) for _, rec in recs for e in rec["entries"] if e.get("catalogued")]
    print("\n" + "=" * 96)
    print(f"RANDOM SAMPLE ({args.sample} of {len(pool):,} catalogued entries, seed {args.seed})")
    print("=" * 96)
    for src, e in rng.sample(pool, min(args.sample, len(pool))):
        # NOTHING IN THIS BLOCK IS SLICED ANY MORE (order 01eff1b24759). The name, source and
        # category cuts were cosmetic column alignment, but a cut with no marker is a cut a
        # reader cannot see; `{:<46}` pads a short name and leaves a long one whole, which is
        # the alignment those slices were reaching for without the truncation.
        d = re.sub(r"\s+", " ", (e.get("description") or ""))
        print(f"\n  [{e.get('magnitude')!s:<9}] {(e.get('name') or '?'):<46}{src}")
        print(f"     topic={e.get('topic')}  category={e.get('category') or '?'}")
        if e.get("scale_note"):
            _field("FEAT: ", e["scale_note"])
        _field("desc: ", d)

    # banded entries deserve their own look: those are the ones carrying a number
    banded = [(s, e) for s, e in pool if e.get("magnitude") not in (None, "unassayed")]
    print("\n" + "=" * 96)
    print(f"BANDED SAMPLE ({min(10,len(banded))} of {len(banded):,} — every one of these makes a claim)")
    print("=" * 96)
    for src, e in rng.sample(banded, min(10, len(banded))):
        print(f"\n  [{e['magnitude']}] {(e.get('name') or '?'):<46}{src}")
        _field("FEAT: ", e.get("scale_note") or "")
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())
