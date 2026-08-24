#!/usr/bin/env python3
"""
Catalogues the roll's remaining sources from real wiki data.

This supersedes src/catalogue_local.py, which asked the local model to recall each franchise
from memory. That approach produced confidently wrong names -- it catalogued Bleach's Yasutora
Sado as "Chad (Seraura Urahara)" -- and nothing on this machine could detect the error.

Here, names, categories and descriptions all come from the source's own wiki over the
MediaWiki API. No model is involved at any point, so there is nothing to hallucinate. The
records this writes are therefore Attestation **Transcribed** ("the chain delivered it", Vade
Mecum II.4) rather than *Reconstructed* ("guessed").

What is still NOT claimed:
  * `scale_note` is left empty. Power/scale is Assay work, derived from cited feats through
    Part Three's worksheet method; guessing it from a wiki lead paragraph would be exactly the
    fabricated-decimal problem the charter's Hard Rule 3 exists to prevent.
  * `synthesis` (ceiling_entity, provisional_magnitude) is left null for the same reason.

Usage:
    python3 src/catalogue_web.py --dry-run          # resolve wikis only, fetch nothing
    python3 src/catalogue_web.py --limit 2          # catalogue two sources
    python3 src/catalogue_web.py --only "Bleach"
    python3 src/catalogue_web.py                    # everything still uncatalogued
"""
import argparse
import json
import os
import re
import sys
import time

sys.path.insert(0, os.path.dirname(__file__))
import wiki_source as ws  # noqa: E402
import silence

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ROLL = os.path.join(HERE, "data/SWEEP_ROLL.json")
RECORDS = os.path.join(HERE, "data/records")

# HARD RULE 0. There is no per-source ceiling and there must not be one.
#
# This read `MAX_PER_SOURCE = 320`, justified in its own comment as avoiding "ballooning the
# library with every minor page a large wiki happens to hold". That reasoning is the exact thing
# Hard Rule 0 exists to refuse, and the damage is measurable: DC's character category holds
# 33,614 members and `data/records/dc.json` holds 377. Marvel got 1,051 across several
# sub-wikis. Molecule Man, Mister Mxyzptlk and the Black Winter were all outside the window, and
# every one of them reads as "not in that fiction" rather than "past the cutoff".
#
# The trim was proportional across categories, which made it worse rather than better: it looked
# principled, it kept a plausible spread of Persons and Places, and it produced a catalogue with
# the same SHAPE as a complete one. Nothing downstream can tell the difference.
MAX_PER_SOURCE = None
# Hard Rule 0: kept only as a name other code may import. Nothing truncates by it any more.
MAX_PER_CATEGORY = None
# How deep to read a category before ranking. Must be well above MAX_PER_CATEGORY or ranking
# has nothing to choose from and the alphabetical bias returns.
CATEGORY_SCAN_DEPTH = None


def slug(s):
    return re.sub(r"[^a-z0-9]+", "-", s.lower()).strip("-")[:60]


def load_roll():
    with open(ROLL, encoding="utf-8") as f:
        return json.load(f)


def save_roll(roll):
    with open(ROLL, "w", encoding="utf-8") as f:
        json.dump(roll, f, indent=2, ensure_ascii=False)


def catalogue_composite(source_name, verbose=True):
    """Catalogue a cross-media source by merging named categories from several wikis.

    Used for roll entries that are a category of thing rather than a single work -- see
    ws.COMPOSITE_SOURCES. Every entry records which wiki it came from, so a merged source
    stays auditable per-item.
    """
    spec = ws.COMPOSITE_SOURCES[source_name]
    entries, seen = [], set()
    for sub, cats in spec:
        got = 0
        for c in cats:
            try:
                titles = ws.clean_titles(ws.category_members(sub, c, limit=None))
            except Exception:
                silence.note("catalogue_web.py:79")
                continue
            if len(titles) > 40:
                titles = ws.rank_by_size(sub, titles, top=None)   # rank, never truncate
            wanted = []
            for title in titles:
                key = re.sub(r"[^a-z0-9]", "", re.sub(r"\([^)]*\)", "", title.lower()))
                if not key or key in seen:
                    continue
                seen.add(key)
                wanted.append(title)
            texts = ws.page_texts(sub, wanted)
            for title in wanted:
                text = texts.get(title)
                if not text:
                    continue
                entries.append({
                    "name": title,
                    "type": "Deity",
                    "description": text,
                    "scale_note": "",
                    "category": "Persons (named individual characters, real or fictional)",
                    "wiki_page": f"https://{sub}.fandom.com/wiki/" + title.replace(" ", "_"),
                    "origin_work": sub,
                })
                got += 1
        if verbose:
            print(f"      {sub:24s} {got:4d}", flush=True)
    if not entries:
        return None, "composite produced no entries"
    wikis = ", ".join(s for s, _ in spec)
    return {
        "source": source_name,
        "mode": "web",
        "entries": entries,
        "synthesis": None,
        "status": "catalogued",
        "attestation": "Transcribed",
        "provenance": (
            f"Transcribed from the deity/pantheon categories of multiple franchise wikis "
            f"({wikis}) via the MediaWiki API by src/catalogue_web.py. This source is the "
            f"INVENTED pantheons of fiction across anime, film, television and games -- the "
            f"roll's thirteen 'Pantheon: <culture>' sources already cover real-world "
            f"mythology separately. Each entry records its origin_work. No model generated "
            f"any of this content."
        ),
    }, "ok"


def catalogue(source_name, verbose=True):
    """Returns (record dict or None, note)."""
    if source_name in ws.COMPOSITE_SOURCES:
        return catalogue_composite(source_name, verbose=verbose)

    sub, sitename = ws.resolve_wiki(source_name)
    if not sub:
        return None, "no wiki resolved"
    if verbose:
        print(f"      wiki: {sub}.fandom.com ({sitename})")

    # gather candidate titles per canonical category
    planned = []
    for canon in ws.CATEGORY_KEYWORDS:
        cats = ws.find_categories(sub, canon)
        if not cats:
            continue
        # Pull the category WIDE, then rank by article size and keep the top slice. Slicing
        # the raw listing instead would just take the alphabetically-first names -- that is
        # how an earlier run built a Bleach catalogue with no Ichigo Kurosaki in it.
        titles = []
        for c in cats:
            titles += ws.category_members(sub, c, limit=None)
        titles = ws.clean_titles(titles)
        # Was `if len(titles) > MAX_PER_CATEGORY:` -- and MAX_PER_CATEGORY is None, so this
        # line raised TypeError for every category that had any titles at all. It was left
        # behind when the cap was removed: the constant was neutralised, the comparison
        # against it was not. Ranking is unconditional now, which is what it should always
        # have been, because ranking without truncating costs nothing and buys ordering.
        titles = ws.rank_by_size(sub, titles, top=None)       # rank, never truncate
        if titles:
            planned.append((canon, cats, titles))

    if not planned:
        return None, "wiki resolved but no usable categories"

    # No trim. The proportional slice that stood here is gone entirely -- see MAX_PER_SOURCE.
    # The concern it addressed was real (one huge category crowding out the others) and the
    # answer to it is ordering, not truncation: every category is ranked by article size above,
    # so if a run is interrupted the richest material is already in hand and the tail is still
    # queued rather than discarded.
    if MAX_PER_SOURCE is not None:
        raise SystemExit("catalogue_web: MAX_PER_SOURCE was set to " + str(MAX_PER_SOURCE)
                         + ". Hard Rule 0 forbids a per-source ceiling. Refusing to run rather "
                         "than silently publishing a smaller universe.")

    entries, seen = [], set()
    for canon, cats, titles in planned:
        # De-duplicate BEFORE fetching, so the pool never spends a request on a page we would
        # discard anyway.
        wanted = []
        for title in titles:
            key = re.sub(r"[^a-z0-9]", "", re.sub(r"\([^)]*\)", "", title.lower()))
            if not key or key in seen:
                continue
            seen.add(key)
            wanted.append(title)

        texts = ws.page_texts(sub, wanted)
        got = 0
        for title in wanted:
            text = texts.get(title)
            if not text:
                continue
            entries.append({
                "name": title,
                "type": cats[0].rstrip("s") if cats else canon.split(" (")[0].rstrip("s"),
                "description": text,
                "scale_note": "",
                "category": canon,
                "wiki_page": f"https://{sub}.fandom.com/wiki/"
                             + title.replace(" ", "_"),
            })
            got += 1
        if verbose:
            print(f"      {canon.split(' (')[0][:28]:30s} {got:4d}")

    if not entries:
        return None, "categories found but no page text retrievable"

    return {
        "source": source_name,
        "mode": "web",
        "entries": entries,
        "synthesis": None,
        "status": "catalogued",
        "attestation": "Transcribed",
        "provenance": (
            f"Transcribed from {sitename} ({sub}.fandom.com) via the MediaWiki API by "
            f"src/catalogue_web.py. Entity names, categories and descriptions are the wiki's "
            f"own text; no model generated any of this content. scale_note and synthesis are "
            f"deliberately empty -- Assay values require Part Three's worksheet method against "
            f"cited feats and are not inferable from a wiki lead paragraph."
        ),
    }, "ok"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true", help="resolve wikis only")
    ap.add_argument("--limit", type=int, default=None)
    ap.add_argument("--only", type=str, default=None,
                    help="substring match against source names, comma-separated")
    ap.add_argument("--recatalogue", action="store_true",
                    help="include sources that already have entries (use after a cap is lifted)")
    ap.add_argument("--shortfall", type=int, default=0, metavar="N",
                    help="only sources COMPLETENESS.json says are short by N or more, "
                         "largest gap first")
    args = ap.parse_args()

    roll = load_roll()
    if args.recatalogue:
        # Every source, regardless of entry_count. The default selection -- sources with zero
        # entries -- is right for a first pass and exactly wrong after a CAP IS REMOVED, because
        # every source the cap truncated has a non-zero entry_count and therefore looks finished.
        # A truncated catalogue is indistinguishable from a complete one by that test, which is
        # how MAX_PER_SOURCE survived as long as it did.
        todo = list(roll)
    else:
        todo = [r for r in roll if r.get("entry_count", 0) == 0]

    if args.shortfall:
        # Target what the completeness audit says is actually missing, worst first, so an
        # interrupted run has spent its time where the gap was largest.
        try:
            with open(os.path.join(HERE, "data", "COMPLETENESS.json"), encoding="utf-8") as f:
                comp = json.load(f)
        except Exception:
            silence.note("catalogue_web.py:266")
            raise SystemExit("--shortfall needs data/COMPLETENESS.json; run completeness.py")
        gap = {}
        for c in comp:
            if c.get("unreliable"):
                continue
            missing = (c.get("wiki_persons") or 0) - (c.get("catalogued_persons") or 0)
            if missing >= args.shortfall:
                gap[str(c["source"]).lower()] = missing
        todo = [r for r in todo if r["name"].lower() in gap]
        todo.sort(key=lambda r: -gap[r["name"].lower()])
        print("targeting %d sources short by %d or more entries; largest gaps first"
              % (len(todo), args.shortfall))

    if args.only:
        wanted = [n.strip().lower() for n in args.only.split(",")]
        todo = [r for r in todo if any(w in r["name"].lower() for w in wanted)]
    if args.limit:
        todo = todo[: args.limit]

    print(f"{len(todo)} sources to catalogue from wiki sources "
          f"(Attestation: Transcribed)\n")

    if args.dry_run:
        hit = 0
        for r in todo:
            sub, name = ws.resolve_wiki(r["name"])
            if sub:
                hit += 1
            print(f"  {r['name'][:44]:46s} -> {str(sub or 'UNRESOLVED')[:24]:26s} {name or ''}")
        print(f"\n{hit}/{len(todo)} resolved. (dry run -- no pages fetched)")
        return

    roll_by_name = {r["name"]: r for r in roll}
    # SOURCES IN PARALLEL. Each source is a different wiki, and per-host politeness lives in
    # the throttle -- serializing sources added nothing but wall-clock. Three at once puts
    # DC, Gundam and SpongeBob in flight together instead of in a queue. Record and roll
    # writes are serialized under a lock; a source is still written atomically, whole.
    import threading
    from concurrent.futures import ThreadPoolExecutor
    _wlock = threading.Lock()
    tally = {"done": 0, "failed": 0, "i": 0}

    def _one(r):
        name = r["name"]
        with _wlock:
            tally["i"] += 1
            print(f"[{tally['i']}/{len(todo)}] {name}", flush=True)
        t0 = time.time()
        try:
            record, note = catalogue(name)
        except Exception as e:
            record, note = None, f"error: {type(e).__name__} {str(e)[:60]}"
        with _wlock:
            if not record:
                print(f"      -> SKIPPED {name} ({note})", flush=True)
                tally["failed"] += 1
                return
            record["category"] = r.get("category")
            # Atomic + judgment-preserving: the raw truncating write here raced the pipeline
            # phases and a SIGTERM mid-dump left corrupt JSON (2026-08-23 audit, finding 3).
            import pipeline as _P
            _P.write_record_catalogue(os.path.join(RECORDS, slug(name) + ".json"), record)
            roll_by_name[name]["entry_count"] = len(record["entries"])
            roll_by_name[name]["status"] = "catalogued"
            save_roll(roll)
            tally["done"] += 1
            print(f"      -> {name}: {len(record['entries'])} entries in "
                  f"{time.time()-t0:.0f}s", flush=True)

    with ThreadPoolExecutor(max_workers=3) as ex:
        list(ex.map(_one, todo))

    print(f"Catalogued {tally['done']}/{len(todo)} sources ({tally['failed']} skipped).")


if __name__ == "__main__":
    main()
