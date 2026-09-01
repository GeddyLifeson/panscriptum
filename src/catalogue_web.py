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
# DEAD: the ranking-before-truncating mechanism this described no longer exists -- categories
# are pulled with limit=None (see category_members below) and ranked with top=None, so there is
# no "how deep to scan before ranking" question left to answer. Kept only as a name other code
# may import, like MAX_PER_CATEGORY above; nothing reads it.
CATEGORY_SCAN_DEPTH = None
# How often `catalogue()` may print a progress line. NOT a cap on anything -- it rate-limits
# OUTPUT, never work, and each line still reports a real completed unit. It must stay well
# under `standards.MAX_JOB_SILENCE_MIN` (15 minutes) or a healthy pass on a big wiki reads as
# a stall and the foreman kills it, which is precisely what it did before run #25.
PROGRESS_EVERY_S = 20


# HARD RULE 0 AGAIN, ON THE IDENTITY THIS TIME. `slug` was defined here as
#
#     re.sub(r"[^a-z0-9]+", "-", s.lower()).strip("-")[:60]
#
# and that trailing `[:60]` is the same act as MAX_PER_SOURCE above, one level down: it does not
# fail, it returns a shorter thing wearing the shape of the real one. What it cut was not a list
# of entries but the NAME of the file holding them, and THIS MODULE is the writer that produced
# the live symptom -- `data/records/who-framed-roger-rabbit-incl-all-content-from-its-associated
# .json` carries `mode: "web"` and 304 entries:
#
#     roll row  'Who Framed Roger Rabbit (incl. all content from its associated
#                crossover-toon IPs)'
#     slugs to  who-framed-roger-rabbit-incl-all-content-from-its-associated-crossover-toon-ips
#               (79 characters)
#     on disk   who-framed-roger-rabbit-incl-all-content-from-its-associated.json
#               (60 -- exactly the cap)
#
# A roll row that is not missing, a record that is not orphaned, and no path between them except
# a reader willing to guess the name was cut. It was filed against catalogue_aurora.py (order
# 683c59f43829) and fixed there; the writer that actually did it was this one, and a `--force`
# run would have done it again.
#
# IMPORTED, NOT RE-WRITTEN. Four independent slug functions that must agree is precisely how the
# disagreement arose, so this takes catalogue_aurora's -- one definition, and `record_path` with
# it, which prefers the file that ALREADY EXISTS (exact slug first, then the legacy 60-character
# prefix) so removing the cap cannot strand or duplicate a record written under it. No cycle:
# catalogue_aurora imports catalogue_codex and silence, neither of which imports this module.
from catalogue_aurora import record_path, slug as _slug  # noqa: E402

# Re-bound, not redefined. `catalogue_web.slug` is this module's long-standing public name --
# recover_folder_records.py's own comment cites it as the filename authority these records must
# land beside -- so it stays available under that name, while being the SAME OBJECT as
# catalogue_aurora.slug. Two names, one function; they cannot drift apart again.
slug = _slug


def _singular(s):
    """A Fandom category name as a stored `type`. Singularise only where it is unambiguous.

    THIS REPLACES `s.rstrip("s")` (order 0a5019b2527e), which was not a suffix test at all --
    `str.rstrip(chars)` removes a SET of characters from the end, so it stripped EVERY trailing
    's'. Run against real Fandom category names it produced: Goddesses -> Goddesse,
    Bosses -> Bosse, Classes -> Classe, Princess -> Prince, Colossus -> Colossu. That value is
    WRITTEN INTO THE RECORD, not merely printed, so every entry harvested from such a category
    carried a corrupted type in data/records/.

    Deliberately not an English pluraliser. Three rules, in order, and the middle one is the
    point: where the shape is genuinely ambiguous the category name is LEFT INTACT rather than
    guessed at. A plural type is untidy; a mangled one is wrong, and a downstream reader can
    still singularise a plural it recognises. Every case below is at least as good as the old
    rstrip and never worse.

      -es after a sibilant -> drop 'es'   Goddesses -> Goddess, Bosses -> Boss,
                                          Classes -> Class, Boxes -> Box, Witches -> Witch
      -ss/-us/-is          -> unchanged   Princess, Colossus, Analysis: already singular
      -ies/-oes            -> unchanged   Species, Deities, Movies, Heroes: 'Deities' -> 'Deity'
                                          and 'Movies' -> 'Movie' cannot be told apart without a
                                          dictionary, so neither is attempted
      -s                   -> drop 's'    Characters -> Character, Places -> Place,
                                          Vehicles -> Vehicle, Gods -> God
    """
    if s.endswith(("sses", "xes", "zes", "ches", "shes")):
        return s[:-2]
    if s.endswith(("ss", "us", "is", "ies", "oes")):
        return s
    if s.endswith("s"):
        return s[:-1]
    return s


def load_roll():
    with open(ROLL, encoding="utf-8") as f:
        return json.load(f)


def save_roll(roll, names=None):
    """-> True if the write landed. `names` limits the merge to those sources' rows.

    Atomic for the same reason the record write beside it is: SWEEP_ROLL.json is written from
    three worker threads here and read elsewhere by `load_roll` and `resync_roll.py`, BOTH of
    which do an unguarded `json.load`. A truncating write interrupted mid-dump therefore does
    not degrade anything gracefully -- it kills the next run of either script outright.

    GATE ON THE WRITE, like `write_record_catalogue` three lines above every call site: this
    used to run `replace_retry` and drop the verdict, so a denied replace here was invisible to
    every caller even though the record write right beside it in the same function IS checked.

    AND THROUGH `silence.write_json`, NOT A HAND-ROLLED TMP (order 0924f1b5af2f). This was
    `tmp = ROLL + ".tmp"` + open + json.dump + replace_retry -- a FIXED temp name, shared by
    every process that writes the roll. It was the last of the then-FIVE writers of the file
    (there are SEVEN, counted for order f818a77293fc) of data/SWEEP_ROLL.json
    still on that convention: every roll writer now lands through `roll.update_rows` /
    `roll.mutate` (catalogue_codex.py:361, resync_roll.py:211), which stages its own
    pid+thread+attempt-qualified temp name and lands it through `silence.replace_if_unchanged`
    directly, not through `write_json` -- the same pid/thread discipline, hand-rolled instead.
    Two processes writing the roll opened the SAME temp file; the second truncated the first and
    whichever renamed second landed a partial roll over a finished one -- the identical hazard
    already repaired in runguard._land (where PermissionError fired 99 times in production),
    health._flush_ledger and pipeline.py (order e080a5f83b3c). The `_wlock` this is called under
    serialises the three worker threads inside ONE run; the collision is between PROCESSES,
    which is exactly the case the four siblings were migrated for.

    The irony worth recording, since it is why the migration passed this site by: write_json's
    own docstring names `catalogue_web.save_roll()` as the site that ALREADY had the atomic
    version while its siblings did not. Being the exemplar is what kept it on the one convention
    write_json was written to make unavailable to get wrong.

    write_json returns the same landed/not-landed verdict replace_retry did, so no call site
    changes -- the gate is save_roll's call site in `_one`, still gating on it.

    AND NOW IT IS A COMPARE-AND-SWAP, which is the exposure the paragraph that used to stand
    here described and left open (order f818a77293fc). main() loads the whole roll once and every
    worker wrote the WHOLE object back, so on a large wiki the in-memory snapshot is hours old
    and another writer's change inside that window was overwritten wholesale -- complete,
    consistent, atomic, and one row behind. `roll.update_rows` re-reads the file, merges only the
    rows named in `names`, and re-applies rather than retrying the same bytes if the file moved.

    `names` IS OPTIONAL FOR THE SIGNATURE, NOT FOR CORRECTNESS. Passing it is what makes the
    merge key-wise; omitting it merges every row of the caller's copy, which is the old
    whole-document semantics with the torn-file and staleness hazards closed but the caller's
    stale rows still carried. The one call site in this module names the source it just wrote.
    """
    import roll as _roll
    rows = roll if names is None else [r for r in roll if r.get("name") in set(names)]
    landed, why = _roll.update_rows({r["name"]: {k: v for k, v in r.items() if k != "name"}
                                     for r in rows if r.get("name")}, path=ROLL)
    if why:
        print("      -> ROLL: %s" % why, flush=True)
    return landed


def catalogue_composite(source_name, verbose=True):
    """Catalogue a cross-media source by merging named categories from several wikis.

    Used for roll entries that are a category of thing rather than a single work -- see
    ws.COMPOSITE_SOURCES. Every entry records which wiki it came from, so a merged source
    stays auditable per-item.
    """
    spec = ws.COMPOSITE_SOURCES[source_name]
    entries, seen = [], set()
    failed_cats = []
    # A TITLE THAT CAME BACK WITHOUT TEXT IS NOT AN ENTITY WITH NO EVIDENCE. `page_texts` drops
    # every falsy result, and `page_text` returns the same "" whether all three of its section
    # fetches raised (timeout, 429) or the page genuinely has no prose -- so a dropped title used
    # to leave no trace at all, and a source could report "Transcribed" over a fetch that lost
    # half its pages to the network. Counted here and named in the provenance, the same way
    # `failed_cats` is: this module cannot tell the two apart from the outside, but it can refuse
    # to pretend the drops did not happen.
    no_text = 0
    for sub, cats in spec:
        got = 0
        for c in cats:
            try:
                titles = ws.clean_titles(ws.category_members(sub, c, limit=None))
            except Exception:
                silence.note("catalogue_web.py:composite-category-members")
                failed_cats.append(f"{sub}:{c}")
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
                    no_text += 1
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
    # A FAILED SUB-CATEGORY IS NOT AN ABSENT ONE, and this path used to say nothing about the
    # difference. `catalogue()`'s single-wiki path lets `find_categories`/`category_members`
    # raise, so ANY transport failure fails the whole attempt honestly and the source stays
    # retryable (`entry_count` stays 0). This path instead keeps going after each category, on
    # purpose -- one dead sub-wiki should not cost the others their data -- but that meant a
    # source could come back "catalogued"/"Transcribed"/"ok" while some of its categories were
    # never actually read, indistinguishable from one where they came back genuinely empty. The
    # failures are now named in the provenance and the note, so a reader (and `_one`'s log line)
    # can tell "transcribed in full" from "transcribed except for these".
    bits = []
    if failed_cats:
        bits.append(f"transport failed for {len(failed_cats)} categories")
    if no_text:
        bits.append(f"{no_text} titles returned no text")
    note = "ok" if not bits else "ok (" + "; ".join(bits) + ")"
    provenance = (
        f"Transcribed from the deity/pantheon categories of multiple franchise wikis "
        f"({wikis}) via the MediaWiki API by src/catalogue_web.py. This source is the "
        f"INVENTED pantheons of fiction across anime, film, television and games -- the "
        f"roll's thirteen 'Pantheon: <culture>' sources already cover real-world "
        f"mythology separately. Each entry records its origin_work. No model generated "
        f"any of this content."
    )
    if failed_cats:
        provenance += (
            f" INCOMPLETE: the transport failed for {len(failed_cats)} categor"
            f"{'y' if len(failed_cats) == 1 else 'ies'} that were never read and are not "
            f"reflected in the entries below -- " + ", ".join(failed_cats) + "."
        )
    if no_text:
        provenance += (
            f" {no_text} title{'' if no_text == 1 else 's'} named by these categories are not "
            f"below because no page text came back for them. The API answers the same empty "
            f"string for a failed fetch and for a page with no prose, so this count is the "
            f"UPPER bound on genuine absence and the upper bound on lost fetches alike -- it "
            f"is not a claim that those entities have no evidence."
        )
    return {
        "source": source_name,
        "mode": "web",
        "entries": entries,
        "synthesis": None,
        "status": "catalogued",
        "attestation": "Transcribed",
        "provenance": provenance,
    }, note


def catalogue(source_name, verbose=True):
    """Returns (record dict or None, note)."""
    if source_name in ws.COMPOSITE_SOURCES:
        return catalogue_composite(source_name, verbose=verbose)

    sub, sitename = ws.resolve_wiki(source_name)
    if not sub:
        return None, "no wiki resolved"
    if verbose:
        print(f"      wiki: {sub}.fandom.com ({sitename})", flush=True)

    # A WORKING JOB MUST LOOK LIKE A WORKING JOB, OR THE STALL REMEDY KILLS IT.
    #
    # Everything below this line -- category discovery, member listing, size ranking, page
    # fetching -- used to print NOTHING until a whole canonical class was finished. On a small
    # wiki that is seconds. On DC it is hours: MEASURED run #25, the `Persons` class alone
    # resolves to 360 categories, the first of which lists 33,614 titles (23s) and takes ~3.8
    # minutes just to rank. `standards.MAX_JOB_SILENCE_MIN` is 15, so `foreman.kill_stalled_job`
    # killed the catalogue pass every single time it reached a large source -- and because
    # `catalogue_web.py --recatalogue` is NOT in the keeper's STANDING set, it then stayed down
    # until the supervisor's next main lap. `--shortfall` orders the work LARGEST GAP FIRST and
    # runs three sources at once, so the pass began with the three biggest wikis in the library
    # every time and was killed before finishing any of them. That is why `every source is
    # fully catalogued` sat at 17.2% with its worst offenders being its biggest sources: DC at
    # 0.5% is not a slow source, it is a source that has never once been allowed to finish.
    # Killed 3 times in the visible foreman log alone.
    #
    # The fix is to say what is happening, not to weaken the detector: every line below is
    # emitted on a REAL completed unit of work, merely rate-limited so a huge source does not
    # write a million lines. A wedged fetch completes nothing, so it still goes silent and is
    # still killed -- which is exactly what the stall standard is for.
    _beat_at = [time.time()]

    def _beat(what, done, total):
        if not verbose:
            return
        now = time.time()
        if now - _beat_at[0] < PROGRESS_EVERY_S:
            return
        _beat_at[0] = now
        print(f"      {source_name[:20]:22s} {what:24s} {done}/{total}", flush=True)

    # gather candidate titles per canonical category
    planned = []
    for canon in ws.CATEGORY_KEYWORDS:
        cats = ws.find_categories(sub, canon)
        if not cats:
            continue
        _short = canon.split(" (")[0][:16]
        # Pull the category WIDE, then rank by article size and keep the top slice. Slicing
        # the raw listing instead would just take the alphabetically-first names -- that is
        # how an earlier run built a Bleach catalogue with no Ichigo Kurosaki in it.
        titles = []
        # PROVENANCE IS RECORDED AS THE TITLES ARRIVE (order 6eb20e8d3565). This loop used to
        # flatten every category of the class into one list and keep no title->category map, so
        # the only category still in hand when the entries were built was `cats[0]` -- and every
        # entry in the class was stored with THAT as its `type`. `cats[0]` is not the primary or
        # the largest category either: `ws.find_categories` returns the hardcoded CATEGORY_PROBES
        # guess that answered, followed by discovered ones, so the winner was an artefact of
        # probe order. Measured over the 156 mode='web' records on disk when this was filed:
        # 3,521 Media entries typed 'Ability', 1,696 Vessels & Things typed 'Character', 690
        # Events typed 'Total War: Warhammer' -- a video game's name stored as an entity type.
        # `setdefault` keeps the FIRST category a title was found in, which is the honest answer
        # when a title is a member of several.
        first_cat = {}
        for _ci, c in enumerate(cats, 1):
            got = ws.category_members(sub, c, limit=None)
            for _t in got:
                first_cat.setdefault(_t, c)
            titles += got
            _beat(_short + " cats", _ci, len(cats))
        # Keyed on the RAW title, deliberately: `clean_titles` only filters and de-duplicates and
        # `rank_by_size` only reorders, so every string that survives into `wanted` below is one
        # of these exact strings. Nothing normalises them in between, so nothing can drift.
        titles = ws.clean_titles(titles)
        # Was `if len(titles) > MAX_PER_CATEGORY:` -- and MAX_PER_CATEGORY is None, so this
        # line raised TypeError for every category that had any titles at all. It was left
        # behind when the cap was removed: the constant was neutralised, the comparison
        # against it was not. Ranking is unconditional now, which is what it should always
        # have been, because ranking without truncating costs nothing and buys ordering.
        titles = ws.rank_by_size(
            sub, titles, top=None,       # rank, never truncate
            # Default-arg bind: freezes THIS iteration's `_short` at lambda-creation time, so a
            # future caller that defers the callback cannot see it silently drift to whatever
            # class discovery landed on last (see the rebind note below for the bug this class
            # of mistake already caused once).
            progress=lambda d, t, _short=_short: _beat(_short + " ranking", d, t))
        if titles:
            planned.append((canon, titles, first_cat))

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
    # See `catalogue_composite`: `page_texts` drops falsy results and `page_text` answers ""
    # for a page with no prose and for one whose three section fetches all raised. Dropping
    # those titles is right -- an entry with no description is not evidence -- but dropping
    # them SILENTLY made a partial fetch indistinguishable from a complete one.
    no_text = 0
    for canon, titles, first_cat in planned:
        # Rebind for THIS fetch unit -- the discovery loop above left `_short` on the last
        # canonical class that had categories, and the fetch progress heartbeat closed over
        # that stale value, so every "<class> fetching d/t" line named whatever discovery
        # finished on rather than the class actually in flight.
        _short = canon.split(" (")[0][:16]
        # De-duplicate BEFORE fetching, so the pool never spends a request on a page we would
        # discard anyway.
        wanted = []
        for title in titles:
            key = re.sub(r"[^a-z0-9]", "", re.sub(r"\([^)]*\)", "", title.lower()))
            if not key or key in seen:
                continue
            seen.add(key)
            wanted.append(title)

        texts = ws.page_texts(sub, wanted,
                              # Same default-arg freeze as the ranking callback above.
                              progress=lambda d, t, _short=_short: _beat(_short + " fetching", d, t))
        got = 0
        for title in wanted:
            text = texts.get(title)
            if not text:
                no_text += 1
                continue
            entries.append({
                "name": title,
                # THE CATEGORY THIS TITLE ACTUALLY CAME FROM (order 6eb20e8d3565), not
                # `cats[0]` -- see the discovery loop above for what that cost. The fallback is
                # the CANONICAL CLASS rather than another category: a title with no recorded
                # provenance is one ranking or cleaning dropped and re-found, and "Event" is
                # then the true and least-wrong thing that can be said about it.
                #
                # This is not a cosmetic field. corpus_db.py indexes `type` into the queryable
                # corpus index, and manifest_builder.py puts the entry dict itself into the
                # model prompt while prompts/system_style.txt tells the model to pick the
                # closest fit to the entry's type -- so a wrong type is carried into finished
                # prose.
                #
                # _singular(), never .rstrip("s") -- rstrip takes a character SET, so it ate
                # every trailing 's' and stored Goddesse / Bosse / Classe / Prince / Colossu
                # into the record. (Order 0a5019b2527e.)
                "type": _singular(first_cat.get(title) or canon.split(" (")[0]),
                "description": text,
                "scale_note": "",
                "category": canon,
                "wiki_page": f"https://{sub}.fandom.com/wiki/"
                             + title.replace(" ", "_"),
            })
            got += 1
        if verbose:
            print(f"      {canon.split(' (')[0][:28]:30s} {got:4d}", flush=True)
            _beat_at[0] = time.time()

    if not entries:
        return None, ("categories found but no page text retrievable "
                      f"({no_text} titles asked, none answered)")

    provenance = (
        f"Transcribed from {sitename} ({sub}.fandom.com) via the MediaWiki API by "
        f"src/catalogue_web.py. Entity names, categories and descriptions are the wiki's "
        f"own text; no model generated any of this content. scale_note and synthesis are "
        f"deliberately empty -- Assay values require Part Three's worksheet method against "
        f"cited feats and are not inferable from a wiki lead paragraph."
    )
    if no_text:
        provenance += (
            f" {no_text} title{'' if no_text == 1 else 's'} found in these categories are not "
            f"below because no page text came back for them. The API answers the same empty "
            f"string for a failed fetch and for a page with no prose, so this is not a claim "
            f"that those entities have no evidence -- only that this pass did not obtain any."
        )
    return {
        "source": source_name,
        "mode": "web",
        "entries": entries,
        "synthesis": None,
        "status": "catalogued",
        "attestation": "Transcribed",
        "provenance": provenance,
    }, ("ok" if not no_text else f"ok ({no_text} titles returned no text)")


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
        except Exception as _comp_err:
            silence.note("catalogue_web.py:shortfall-completeness-read")
            raise SystemExit(
                "--shortfall needs data/COMPLETENESS.json; run completeness.py") from _comp_err
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
            # GATE ON THE WRITE, like every other caller. write_record_catalogue returns whether
            # the rename LANDED, and it returns it precisely so a denied write is not recorded as
            # done (`pipeline.write_record_catalogue`, checked by `ingest_doc.mine`, `backfill`,
            # `catalogue_aurora` and `catalogue_codex`).
            # This was the one call site throwing the verdict away and then setting
            # `status = "catalogued"` regardless -- so a persistent PermissionError left a stale
            # record on disk beside a roll claiming N entries. The default work selection is
            # `entry_count == 0`, so that source would never be picked up again and the loss
            # was permanent and silent.
            # `record_path`, not `os.path.join(RECORDS, slug(name) + ".json")`: with the cap gone
            # the raw join would look for the un-truncated name, miss the record this module
            # itself wrote under the cap, and write a SECOND one beside it -- the roll counting
            # one source and the corpus holding two halves of it.
            if not _P.write_record_catalogue(record_path(name, RECORDS), record):
                print(f"      -> WRITE DENIED {name}; roll left untouched", flush=True)
                tally["failed"] += 1
                return
            roll_by_name[name]["entry_count"] = len(record["entries"])
            roll_by_name[name]["status"] = "catalogued"
            # NAMED, so the roll write is a key-wise merge of the row this worker just changed
            # rather than a land of a snapshot taken when the run began (order f818a77293fc).
            if not save_roll(roll, [name]):
                # The record already landed (checked above); only the roll's bookkeeping of it
                # did not. Not a failed catalogue -- entry_count/status just don't reflect it in
                # SWEEP_ROLL.json yet, so a later save_roll() (or a rebuild) is what recovers it.
                print(f"      -> ROLL WRITE DENIED for {name}; record landed, roll unsynced "
                      f"this round", flush=True)
            tally["done"] += 1
            # `note` can say more than "ok" now -- catalogue_composite reports a transport
            # failure on some categories even when it still returns a usable record. Print it
            # here so that case is visible in the run log, not only in the record's own
            # provenance field.
            flag = "" if note == "ok" else f"  [{note}]"
            print(f"      -> {name}: {len(record['entries'])} entries in "
                  f"{time.time()-t0:.0f}s{flag}", flush=True)

    with ThreadPoolExecutor(max_workers=3) as ex:
        list(ex.map(_one, todo))

    print(f"Catalogued {tally['done']}/{len(todo)} sources ({tally['failed']} skipped).")


if __name__ == "__main__":
    main()
