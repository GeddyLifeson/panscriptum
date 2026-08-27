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
        rate = len(v) / max(1, stats["entries_catalogued"])
        print(f"\n  {k}")
        print(f"     {len(v):,} occurrences ({rate:.2%} of catalogued entries)")
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
        d = re.sub(r"\s+", " ", (e.get("description") or ""))[:150]
        print(f"\n  [{e.get('magnitude')!s:<9}] {(e.get('name') or '?')[:44]:<46}{src[:26]}")
        print(f"     topic={e.get('topic')}  category={(e.get('category') or '?')[:34]}")
        if e.get("scale_note"):
            print(f"     FEAT: {e['scale_note'][:110]}")
        print(f"     desc: {d}")

    # banded entries deserve their own look: those are the ones carrying a number
    banded = [(s, e) for s, e in pool if e.get("magnitude") not in (None, "unassayed")]
    print("\n" + "=" * 96)
    print(f"BANDED SAMPLE ({min(10,len(banded))} of {len(banded):,} — every one of these makes a claim)")
    print("=" * 96)
    for src, e in rng.sample(banded, min(10, len(banded))):
        print(f"\n  [{e['magnitude']}] {(e.get('name') or '?')[:44]:<46}{src[:26]}")
        print(f"     FEAT: {(e.get('scale_note') or '(none)')[:120]}")
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())
