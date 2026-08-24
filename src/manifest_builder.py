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
                     placeholder_shelfmark)

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

    by_chapter = {}
    for e in entries:
        chap = e.get("category", "Uncategorized")
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
    return jobs


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--pilot", type=int, default=0)
    ap.add_argument("--only", type=str, default=None)
    ap.add_argument("--include-unassigned", action="store_true")
    args = ap.parse_args()

    cfg = load_config()
    roll = load_roll(cfg)

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
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump({"jobs": all_jobs}, f, indent=2)

    print(f"Wrote {len(all_jobs)} jobs from {len(build_pool)} sources -> {out_path}")
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


if __name__ == "__main__":
    main()
