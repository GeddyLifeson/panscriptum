#!/usr/bin/env python3
"""
Builds the generation job queue (manifest) from data/SWEEP_ROLL.json + data/records/*.json,
addressed against the REAL spine codes in the charter's Acquisitions Index
(data/CHARTER_SPINE_CODES.json -- see src/address.py's module docstring for why this matters).

IMPORTANT: about half the current roll (~110 of 215 sources) has no spine code yet. This is
real and expected, not a bug: the charter's Acquisitions Index appendix was written before the
owner's later additions to the Acquisitions Roll (League of Legends, the Nintendo/anime batch,
Battlestar Galactica/WoW/StarCraft, and the entire D&D "Folder" of official books and
third-party creators, which the appendix only covers as aggregate lines, not per-book).

By default this script only builds jobs for sources WITH a real spine code, and writes a
report of everything else to output/index/unassigned_sources.md. Extending the Acquisitions
Index for those ~110 sources is real curatorial work (which Collection/Set a thing belongs
next to is a judgment call, same as the rest of the appendix) -- do it deliberately, ideally
with the owner's sign-off, rather than having this script silently invent placement. Pass
--include-unassigned if you want provisional codes anyway (clearly marked as such in the
address) so you can pilot the prose pipeline on them before their real shelving is decided.

Usage:
    python3 src/manifest_builder.py                       # full manifest, assigned sources only
    python3 src/manifest_builder.py --pilot 3              # small manifest, 3 cheapest sources
    python3 src/manifest_builder.py --only "One Piece,Marvel"
    python3 src/manifest_builder.py --include-unassigned   # also generate provisional-code books
"""
import argparse
import hashlib
import json
import os
import sys

sys.path.insert(0, os.path.dirname(__file__))
from address import (spine_code_for, slugify, chapter_slug,  # noqa: E402
                     placeholder_shelfmark, chapter_label_for, FEATS_LABEL)
import feats_index  # noqa: E402
import silence  # noqa: E402

import yaml  # noqa: E402


def content_hash(obj) -> str:
    """
    Hash of a job's actual source-data content. This is what makes the resumable cache in
    generate.py safe to use across refreshed data/ snapshots -- see address.recipe_hash's
    docstring for why the address alone isn't enough. Recompute this every time you rebuild
    the manifest; it changes automatically whenever the underlying entries/facts change, even
    if the address (spine code + chapter) stays the same.
    """
    blob = json.dumps(obj, sort_keys=True, default=str).encode("utf-8")
    return hashlib.sha256(blob).hexdigest()[:16]

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def load_config():
    with open(os.path.join(HERE, "config.yaml"), encoding="utf-8") as f:
        return yaml.safe_load(f)


def load_roll(cfg):
    with open(os.path.join(HERE, cfg["paths"]["data_roll"]), encoding="utf-8") as f:
        return json.load(f)


def load_record(cfg, source_name):
    records_dir = os.path.join(HERE, cfg["paths"]["data_records"])
    norm_target = "".join(ch for ch in source_name.lower() if ch.isalnum())
    if not norm_target:
        return None

    # THE SLUG IS A TRUNCATION OF THE NAME, so the containment runs both ways. This tested only
    # `target in filename`, and record slugs are cut to a fixed length -- "Who Framed Roger
    # Rabbit (incl. all content from its associated crossover-toon IPs)" is stored as
    # who-framed-roger-rabbit-incl-all-content-from-its-associated.json, which the full name is
    # NOT a substring of. The result: a source with 304 catalogued entries reported as having
    # no record file at all, and the operator told the wrong reason. (`ingest_doc.record_path`
    # already tests both directions and finds this same file correctly.)
    #
    # The reverse arm is PREFIX-anchored, not free containment: slugs are cut from the front, so
    # a genuine truncation is always a prefix, while free containment would let a short slug
    # match anywhere inside an unrelated long name -- the same accident that had "DC" swallowing
    # "Sword Coast Adventurer's Guide" over in address.py.
    #
    # Candidates are ranked by CLOSENESS, not by file order and not by raw length: an exact
    # match always wins, otherwise the smallest length difference does. Ranking by longest
    # instead sent source "DC" to sword-coast-adventurer-s-guide.json, because that filename
    # also contains the letters "dc" (swor-d-c-oast) and is far longer than dc.json. First-match
    # ordering had been hiding that by luck of `listdir`.
    best_name, best_score = None, None
    for fname in os.listdir(records_dir):
        if not fname.endswith(".json"):
            continue
        norm_fname = "".join(ch for ch in fname[:-5].lower() if ch.isalnum())
        if not norm_fname:
            continue
        if norm_target in norm_fname or norm_target.startswith(norm_fname):
            score = abs(len(norm_fname) - len(norm_target))
            if best_score is None or score < best_score:
                best_name, best_score = fname, score
    if best_name:
        with open(os.path.join(records_dir, best_name), encoding="utf-8") as f:
            return json.load(f)
    return None


def chunk(lst, size):
    for i in range(0, len(lst), size):
        yield lst[i:i + size], i + 1, min(i + size, len(lst))


# Characters of feat JSON one generation call may carry. The measured lesson is `read.py`'s,
# not `generate.py`'s (generate.py cites it for OUTPUT attention; the input measurement is at
# read.py:80 -- 10,000 chars/5 chunks found 41 feats where 36,000 chars/2 chunks found 19).
# Input attention thins past ~30,000 characters and material starts going missing.
#
# The weight is per ENTITY, which is the unit blocking would otherwise have used: a feat is
# 207 characters (measured 2026-08-24 over all 39,862 on disk) and an entity carries a mean of
# 34 of them, so ~7,079 characters of feats per entity against 683 for its catalogue entry --
# 10.4x, the order of magnitude this comment's last sentence turns on. One entity ("List of
# techniques used by Goku") carries 569 deeds for 121,299 characters alone, and 39 entities
# exceed 30,000. Blocking by ENTITY COUNT would therefore have produced single calls an order
# of magnitude past the point where the model silently drops material.
#
# Corrected in maintenance run #10: this comment claimed "137 characters each" and called
# feats "far denser than catalogue entries". Both were wrong -- 207, and a feat is 0.30x a
# catalogue ENTRY, denser only per entity. The comment's own worked example already refuted
# the figure (121,299 / 569 = 213). The conclusion it supports was right the whole time.
#
# The budget is a floor on emitted size, not a ceiling: `cost()` weighs only each entity's
# `feats` list, while the block also carries entity/shelfmark/magnitude/topic/pages/axis_counts
# per entity. Measured on Warhammer 40,000 (the richest source, 91 rows, 7,354 deeds): 106
# blocks, median 20,464 chars, max 21,993 -- 58 blocks over the nominal 20,000, none within
# 8,000 of the 30,000 line. The margin is real but ~10% narrower than the number suggests.
# RETAINED AS THE MEASUREMENT OF RECORD, NOT AS A DEFAULT (2026-08-24). This was `pack_feats`'s
# default third argument, and a default is exactly how a caller forgets that the budget is
# supposed to be DERIVED from the live context window -- both an audit subagent and run #12
# called `pack_feats` without a budget and silently got this 20,000 instead of the manifest
# path's computed one. `budget` is now required, so that mistake is a TypeError at the call
# site rather than a quietly wrong block size. The number itself stays because the paragraph
# above it is a real measurement worth keeping; whether the constant should now be deleted
# outright is a question for NEXT_STEPS, not a silent removal here.
FEATS_BLOCK_CHARS = 20000


def pack_feats(rows, source_name, budget):
    """Pack ranked feat rows into blocks under a character budget.

    Two rules, and the second is the one that matters:

      * Entities are packed together while they fit, so a source of many small casts does not
        pay one call per entity.
      * AN ENTITY LARGER THAN THE BUDGET IS SPLIT ACROSS BLOCKS BY ITS OWN FEATS, and every
        slice is emitted. This is PAGINATION, not truncation -- Hard Rule 0. Each slice says
        which span of that entity's deeds it holds, so the prose can name the span and a reader
        can tell a partial block from a complete one. Dropping the overflow would have been the
        cap this project exists to refuse: 569 attested deeds silently becoming the first 90.
    """
    def cost(feats):
        return len(json.dumps(feats, ensure_ascii=False))

    def shell(r, feats, span=None):
        out = {
            "entity": r["entity"],
            "shelfmark": placeholder_shelfmark(source_name),
            "magnitude": (r["entry"] or {}).get("magnitude", "unassayed"),
            "topic": (r["entry"] or {}).get("topic"),
            "pages": r["pages"],
            "feat_count": r["feat_count"],
            "axis_counts": r["axis_counts"],
            "feats": feats,
        }
        if span:
            out["feat_span"] = span
        return out

    blocks, cur, cur_cost = [], [], 0
    for r in rows:
        feats = r["feats"]
        c = cost(feats)
        if c <= budget:
            if cur and cur_cost + c > budget:
                blocks.append(cur)
                cur, cur_cost = [], 0
            cur.append(shell(r, feats))
            cur_cost += c
            continue
        # Oversized: flush what is open, then slice this entity alone across whole blocks.
        if cur:
            blocks.append(cur)
            cur, cur_cost = [], 0
        # FLUSH BEFORE EXCEEDING, not after. The first version appended a deed and then asked
        # whether the slice had reached the budget, so a slice always overshot by its last
        # deed -- and deeds are not uniform. Measured on Warhammer 40,000: a Black Templars
        # slice reached 5,414 characters against a 2,987 budget because one long deed landed on
        # an almost-full slice. That was harmless while the budget was decorative; now that the
        # budget is derived from `num_ctx` it is the difference between a block that fits and a
        # ContextOverflow. Checking before appending keeps every slice inside the budget except
        # the one case that cannot be helped, below.
        slice_, start = [], 0
        for f in feats:
            if slice_ and cost([*slice_, f]) > budget:
                span = f"{start + 1}-{start + len(slice_)} of {len(feats)}"
                blocks.append([shell(r, list(slice_), span)])
                start += len(slice_)
                slice_ = []
            # A SINGLE deed larger than the whole budget still gets its own block and is NOT
            # dropped or clipped -- Hard Rule 0. It will fail `assert_fits` loudly at generation
            # time, which is the correct outcome: one un-writable deed is a reported problem,
            # and silently discarding it is the thing this project exists to refuse.
            slice_.append(f)
        if slice_:
            span = f"{start + 1}-{start + len(slice_)} of {len(feats)}"
            blocks.append([shell(r, list(slice_), span)])
    if cur:
        blocks.append(cur)
    return blocks


def provisional_spine(roll_entry):
    """Only used with --include-unassigned. Clearly marked PROVISIONAL, never silently real."""
    cat = slugify(roll_entry.get("category", "Uncategorized"))
    return f"UNSORTED.{cat}.PROVISIONAL"


def build_jobs_for_source(cfg, roll_entry, record, spine):
    jobs = []
    source_name = roll_entry["name"]
    entries = record.get("entries", [])
    if not entries:
        return jobs

    # ROUTE BY THE SOURCE'S MODE, not by the entry's category alone. The classifier has one
    # bucket for every ability, so a homebrew spell and a narrative power arrive identically
    # labelled; the source's `mode` is what distinguishes a rulebook from a wiki. See
    # address.chapter_label_for -- 65.9% of all Powers entries are mechanical.
    mode = record.get("mode")
    by_chapter = {}
    for e in entries:
        chap = chapter_label_for(e.get("category", "Uncategorized"), mode)
        by_chapter.setdefault(chap, []).append(e)

    max_per_call = cfg.get("max_entries_per_call", 30)
    synth = record.get("synthesis") or {}

    front_addr = f"{spine}/Frontmatter"
    volume_facts = {
        "source": source_name,
        "spine_code": spine,
        "mode": record.get("mode"),
        "total_entries": len(entries),
        "ceiling_entity": synth.get("ceiling_entity"),
        "provisional_magnitude": synth.get("provisional_magnitude"),
        "canon_branches": synth.get("canon_branches", []),
        "chapters": sorted(by_chapter.keys()),
    }
    jobs.append({
        "job_id": front_addr,
        "type": "frontmatter",
        "source_name": source_name,
        "spine_code": spine,
        "chapter_label": "Frontmatter",
        "address": front_addr,
        "page_range": None,
        "volume_facts": volume_facts,
        "content_hash": content_hash(volume_facts),
    })

    for chap_label, chap_entries in by_chapter.items():
        chunks = list(chunk(chap_entries, max_per_call))
        multi = len(chunks) > 1
        for part, start, end in chunks:
            page_range = f"{start}-{end}" if multi else None
            addr = f"{spine}/{chapter_slug(chap_label)}"
            if page_range:
                addr += f"#{page_range}"
            source_context = {
                "mode": record.get("mode"),
                "ceiling_entity": synth.get("ceiling_entity"),
                "provisional_magnitude": synth.get("provisional_magnitude"),
                "total_entries_in_source": len(entries),
            }
            # prompts/system_style.txt tells the model: "Shelfmark: [use exactly what is
            # supplied in the entry data's shelfmark field ... do not invent rungs]". Nothing
            # was ever putting that field there -- address.placeholder_shelfmark() existed but
            # had no callers, so every entry reached the model without a shelfmark and the
            # model filled the gap itself. Observed in a real pilot run: gemma3:12b invented a
            # numbering scheme (II.C.2/Factions/01, /02, /03) and qwen2.5:14b echoed the
            # chapter address, both violating Hard Rule 4. Supplying the honest UNCHARTED
            # placeholder gives the model something correct to copy.
            part = [dict(e, shelfmark=placeholder_shelfmark(source_name)) for e in part]
            jobs.append({
                "job_id": addr,
                "type": "chapter",
                "source_name": source_name,
                "spine_code": spine,
                "chapter_label": chap_label,
                "address": addr,
                "page_range": page_range,
                "entries": part,
                "source_context": source_context,
                "content_hash": content_hash({"entries": part, "context": source_context}),
            })

    # ---------------------------------------------------------------- the Feats chapter
    #
    # 39,862 mined feats existed before this and no volume could print one. They are not
    # catalogue entries, so the category grouping above cannot see them; `feats_index` joins
    # them to this source's cast by name (98.6% of the store). Each feat is a QUOTED sentence
    # carrying its own page and one of the eleven Assay axes -- Charter Part Three's worksheet
    # material, which is exactly why this chapter must never be asked to rank or score: the
    # prose reports what was attested and nothing else. See prompts/feats_prompt.txt.
    #
    # Ranked richest-first by feat count, and PAGINATED, never truncated: every entity with
    # feats gets a block, and a large cast simply produces more blocks.
    #
    # AND A FAILED LOOKUP SAYS SO, OUT LOUD. `except Exception: silence.note(...)` alone made a
    # BUG in `feats_index` -- a KeyError on a malformed record, an AttributeError, anything --
    # produce the identical observable result to "this source genuinely has no attested feats":
    # `feat_rows = []`, no Feats chapter emitted, and a build report (the prints in `main()`)
    # that reads exactly the same as a clean run. That is Hard Rule 0's central failure, a
    # smaller-than-real output that nothing distinguishes from a legitimately small one, sitting
    # directly under the comment explaining that 39,862 mined feats once existed with no volume
    # able to print one. The note is kept for the ledger; the print is what reaches the operator
    # watching the build. Found by the run #33 sweep (batch 15).
    try:
        feat_rows = feats_index.feats_for_source(source_name, record)
    except Exception as e:
        silence.note("manifest_builder.py:feats")
        print("WARNING: feats lookup FAILED for %s (%s: %s) -- this volume will carry no Feats "
              "chapter, which is NOT the same finding as a source with no attested feats"
              % (source_name, type(e).__name__, str(e)[:110]))
        feat_rows = []
    if feat_rows:
        # DERIVED, NOT DECLARED (m46). `FEATS_BLOCK_CHARS` had no arithmetic relationship to
        # `num_ctx`: at the configured window the packed block plus its scaffolding came to
        # ~1.9x the context, and Ollama truncates an over-long prompt rather than refusing it.
        # `context_budget` computes what actually fits from the window, the measured prompt
        # scaffolding, and an output reserve -- so raising num_ctx widens the blocks by itself
        # and lowering it narrows them. An explicit `feats_block_chars` in config still wins,
        # for an owner who wants to override the arithmetic deliberately.
        import context_budget as _CBUD
        budget = cfg.get("feats_block_chars")
        budget = int(budget) if budget else _CBUD.feats_block_budget(cfg)
        if budget <= 0:
            # Not clamped to something small and carried on: a window this narrow cannot carry
            # a feats block at all, and pretending otherwise is how the cap comes back.
            raise _CBUD.ContextOverflow(
                f"{source_name}: num_ctx={_CBUD.window(cfg)} leaves no room for feats content "
                f"after the prompt scaffolding. Raise num_ctx or trim the prompts.")
        blocks = pack_feats(feat_rows, source_name, budget)
        multi = len(blocks) > 1
        ctx = {
            "mode": record.get("mode"),
            "ceiling_entity": synth.get("ceiling_entity"),
            "provisional_magnitude": synth.get("provisional_magnitude"),
            "entities_with_feats": len(feat_rows),
            "feats_in_source": sum(r["feat_count"] for r in feat_rows),
        }
        for bi, slim in enumerate(blocks, 1):
            addr = f"{spine}/{chapter_slug(FEATS_LABEL)}"
            if multi:
                addr += f"#b{bi}"
            jobs.append({
                "job_id": addr,
                "type": "feats",
                "source_name": source_name,
                "spine_code": spine,
                "chapter_label": "Feats & Attested Deeds",
                "address": addr,
                "page_range": f"block {bi} of {len(blocks)}" if multi else None,
                "entities": slim,
                "source_context": ctx,
                "content_hash": content_hash({"entities": slim, "context": ctx}),
            })
    return jobs


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--pilot", type=int, default=0)
    ap.add_argument("--only", type=str, default=None)
    ap.add_argument("--include-unassigned", action="store_true")
    args = ap.parse_args()

    cfg = load_config()
    roll = load_roll(cfg)

    # OWNER EXCLUSIONS ARE HONOURED HERE, which until 2026-08-25 they were not: the roll had
    # carried `status: "out-of-scope"` since 2026-08-20 and not one module in `src/` read it, so
    # an excluded source was still queued for generation exactly like any other. Reported by
    # name rather than silently filtered -- a source vanishing from the manifest with no line
    # explaining it is indistinguishable from a source the builder lost.
    import roll as _roll
    _excluded = _roll.out_of_scope(roll)
    if _excluded:
        print("excluded by owner ruling (records kept, work stopped):")
        for _n, _why in sorted(_excluded.items()):
            print("   %-44s %s" % ((_n or "?")[:43], _why[:90]))
    roll = [r for r in roll if r.get("name") not in _excluded]

    populated = [r for r in roll if r.get("entry_count", 0) > 0]
    skipped_empty = [r["name"] for r in roll if r.get("entry_count", 0) == 0]

    assigned, unassigned = [], []
    for r in populated:
        code = spine_code_for(r["name"])
        (assigned if code != "UNASSIGNED" else unassigned).append(r)

    build_pool = assigned + (unassigned if args.include_unassigned else [])

    if args.only:
        wanted = set(n.strip() for n in args.only.split(","))
        build_pool = [r for r in build_pool if r["name"] in wanted]
    elif args.pilot:
        build_pool = sorted(build_pool, key=lambda r: r.get("entry_count", 0))[:args.pilot]

    # Resolve each source to its Series code first, THEN hand out Volume numbers where a
    # Series holds more than one source.
    #
    # Why this exists: the charter's spine format is Collection.Set.Series[.Volume], and a
    # Series legitimately holds several related worlds -- II.A.7 is Soul Calibur AND Street
    # Fighter AND Tekken; II.F.7 is Cosmoteer, Risk of Rain, Star Realms and Stellaris. The
    # Series code is correct for all of them; what was missing was the Volume level. Without
    # it, every one of those sources produced the SAME job address, and generate.py keys both
    # its catalog and its output filenames on that address -- so the sources silently
    # overwrote each other, and resume never converged (two jobs sharing an address with
    # different content_hashes each mark the other stale, forever). Measured before this fix:
    # 303 duplicate addresses across 916 of 3,502 jobs.
    #
    # Volume numbers are assigned deterministically by sorted source name so the address of a
    # given book is stable across rebuilds. Ordering within a Series is otherwise arbitrary
    # and is NOT a curatorial claim -- if the owner wants a deliberate volume order, set it in
    # the charter's Acquisitions Index and this will follow it.
    series_members = {}
    for r in build_pool:
        code = spine_code_for(r["name"])
        if code == "UNASSIGNED":
            code = provisional_spine(r)
        series_members.setdefault(code, []).append(r["name"])

    volume_code = {}
    for code, names in series_members.items():
        if len(names) == 1:
            volume_code[names[0]] = code
        else:
            for i, name in enumerate(sorted(names), start=1):
                volume_code[name] = f"{code}.{i}"

    all_jobs = []
    missing_records = []
    for r in build_pool:
        record = load_record(cfg, r["name"])
        if record is None:
            missing_records.append(r["name"])
            continue
        all_jobs.extend(build_jobs_for_source(cfg, r, record, volume_code[r["name"]]))

    out_key = "pilot_manifest" if args.pilot else "manifest"
    out_path = os.path.join(HERE, cfg["paths"][out_key])
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    # GATED: `write_json` returns whether the rename LANDED, and this discarded the verdict and
    # printed "Wrote N jobs" regardless. THIS FILE IS generate.py's ENTIRE RUN. A denied replace
    # -- routine on Windows while any reader holds the target open, and `generate.py` is exactly
    # such a reader -- left the PREVIOUS manifest on disk while the build reported success, so
    # the next generation pass would run the old job list against the new records and every
    # freshly-catalogued source would silently not be written. Run #36 discarded-verdict sweep.
    manifest_landed = silence.write_json(out_path, {"jobs": all_jobs}, indent=2)

    if manifest_landed:
        print(f"Wrote {len(all_jobs)} jobs from {len(build_pool)} sources -> {out_path}")
    else:
        silence.note("manifest_builder.py:main-manifest-write-denied")
        print(f"MANIFEST WRITE DENIED -> {out_path}: replace refused, so the {len(all_jobs)} "
              f"jobs built from {len(build_pool)} sources did NOT land. The file on disk is the "
              f"PREVIOUS manifest -- do not run generate.py against it expecting this build. "
              f"Rerun to retry.")
    if missing_records:
        print(f"WARNING: {len(missing_records)} sources had no matching record file: "
              f"{missing_records}")
    print(f"Skipped {len(skipped_empty)} sources with entry_count == 0 "
          f"(re-sweep pending on the cloud side).")

    # A REPORT MUST BE CLEARED WHEN ITS FINDING IS. This block only ran when `unassigned` was
    # non-empty, so the day the last source got a spine code the file simply stopped being
    # rewritten -- and went on asserting "47 populated sources aren't in the appendix" for as
    # long as anyone cared to read it. Caught 2026-08-24, 4.6 days stale, the same hour the
    # count actually reached zero. A stale report is worse than no report: it is a confident
    # answer to a question nobody re-asked.
    report_path = os.path.join(HERE, "output/index/unassigned_sources.md")
    os.makedirs(os.path.dirname(report_path), exist_ok=True)
    if not unassigned or args.include_unassigned:
        with open(report_path, "w", encoding="utf-8") as f:
            f.write("# Sources with no spine code yet\n\n")
            f.write("**None.** Every populated source on the Acquisitions Roll resolves to a "
                    "real spine code as of this manifest build.\n"
                    if not unassigned else
                    "Generated with `--include-unassigned`: provisional codes were used, so "
                    "nothing was skipped. These still need real assignments.\n")
    if unassigned and not args.include_unassigned:
        with open(report_path, "w", encoding="utf-8") as f:
            f.write("# Sources with no spine code yet\n\n")
            f.write(f"{len(unassigned)} populated sources aren't in the charter's Acquisitions "
                    f"Index appendix yet (00_MASTER_CHARTER.md), so they were skipped from this "
                    f"manifest. Assign real spine codes for these (extending the appendix, "
                    f"following its existing Collection/Set groupings) before generating their "
                    f"books, or re-run with --include-unassigned to generate them now under "
                    f"clearly-marked provisional codes.\n\n")
            for r in sorted(unassigned, key=lambda r: r["category"]):
                f.write(f"- **{r['name']}** ({r['category']}, {r.get('entry_count', 0)} entries)\n")
        print(f"\n{len(unassigned)} populated sources have NO spine code in the charter yet -- "
              f"skipped. See {report_path}")

    # The unassigned-sources report above is refreshed either way -- it describes the ROLL, not
    # the manifest, and letting a denied manifest write leave it stale would be the same defect
    # this block's own comment was written about. The exit status carries the manifest verdict.
    return 0 if manifest_landed else 1


if __name__ == "__main__":
    sys.exit(main())
