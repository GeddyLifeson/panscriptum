#!/usr/bin/env python3
"""
Catalogues the owner's homebrew sources directly from their Aurora Builder XML.

Supersedes the codex route (src/catalogue_codex.py). Both cover the same sources -- the
homebrew ones that have no wiki because the owner wrote them -- but this reads the primary
files rather than a summary of them, and that matters twice over:

  1. Richer. The codex's "Full Contents" manifest lists element NAMES only; the XML carries a
     full <description> for each. Dr. Firestorm's + The Elements Beyond alone yield 1,159
     elements from the XML against 123 names from the codex.

  2. Clean. THE_PRIME_OMNIVERSE_CODEX.md is a leftover artifact of an earlier, abandoned
     version of this project, and its section blurbs carry that version's setting assumptions
     (placing homebrew tech in "Alphar-un's scrapyards", relics in "Manchuko's Vassal
     States"). Seeding the new omniverse with them would import a cosmology the owner has
     explicitly discarded. The XML has no such framing -- it is just the mechanical content.

Attestation: **Transcribed** -- the owner's own files, read directly. No model involved.
"""
import argparse
import glob
import json
import os
import re
import sys
import xml.etree.ElementTree as ET

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ROLL = os.path.join(HERE, "data/SWEEP_ROLL.json")
RECORDS = os.path.join(HERE, "data/records")
CUSTOM = r"C:\Users\imarl\Documents\5e Character Builder\custom"

sys.path.insert(0, os.path.dirname(__file__))
from catalogue_codex import TYPE_CATEGORY, THINGS  # noqa: E402
import silence

# Folder -> roll source name. Folders not listed here (core, supplements, third-party, user,
# addons, extras) aggregate many published books at once; those are already covered by
# LOCAL_REGISTER.json and its FOLDER_SOURCE_MAP, so they are deliberately not re-derived here.
FOLDER_SOURCE = {
    "drfirestorm": "Dr. Firestorm's Engineering Corps",
    "the-elements-beyond": "The Elements Beyond",
    "JMBrew": "JMBrew",
    "kibblestasty": "KibblesTasty (techno-psionic line)",
    "FFXIV": "the FFXIV / Eorzea conversion",
    "a-plethora-of-paladins": "A Plethora of Paladins",
    "yorviings-arcane-grimoire": "Yorviing's Arcane Grimoire",
    "unearthed-arcana": "Unearthed Arcana (incl. the Planeshift documents)",
    "swecky": "swecky's Nature Traditions",
    "swordmeow-atavist": "swordmeow's Atavist",
}

# 'Source' elements are file metadata (book title, author), not content.
SKIP_TYPES = {"source"}


def slug(s):
    return re.sub(r"[^a-z0-9]+", "-", s.lower()).strip("-")[:60]


def text_of(el):
    d = el.find("description")
    if d is None:
        return ""
    return re.sub(r"\s+", " ", "".join(d.itertext())).strip()


def parse_folder(folder):
    entries, seen = [], set()
    for path in sorted(glob.glob(os.path.join(CUSTOM, folder, "**", "*.xml"),
                                 recursive=True)):
        try:
            root = ET.parse(path).getroot()
        except Exception:
            silence.note("catalogue_aurora.py:74")
            continue  # a malformed homebrew file should not abort the whole source
        for el in root.iter("element"):
            etype = (el.get("type") or "").strip()
            name = (el.get("name") or "").strip()
            if not name or etype.lower() in SKIP_TYPES:
                continue
            key = (etype.lower(), re.sub(r"[^a-z0-9]", "", name.lower()))
            if key in seen:
                continue
            seen.add(key)
            entries.append({
                "name": name,
                "type": etype,
                "description": text_of(el),
                "scale_note": "",
                "category": TYPE_CATEGORY.get(etype.lower(), THINGS),
                "aurora_file": os.path.relpath(path, CUSTOM).replace("\\", "/"),
                "aurora_source": el.get("source") or "",
            })
    return entries


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--force", action="store_true",
                    help="rewrite even if the source already has entries (use to replace "
                         "codex-derived records)")
    args = ap.parse_args()

    with open(ROLL, encoding="utf-8") as f:
        roll = json.load(f)
    by_name = {r["name"]: r for r in roll}

    written = []
    for folder, source_name in FOLDER_SOURCE.items():
        r = by_name.get(source_name)
        if r is None:
            print(f"  ! no roll entry for {source_name!r} (folder {folder})")
            continue
        if r.get("entry_count", 0) > 0 and not args.force:
            continue
        entries = parse_folder(folder)
        if not entries:
            print(f"  ! {folder}: no elements parsed")
            continue
        record = {
            "source": source_name,
            "category": r.get("category"),
            "mode": "folder-mechanical",
            "entries": entries,
            "synthesis": None,
            "status": "catalogued",
            "attestation": "Transcribed",
            "provenance": (
                f"Transcribed directly from the owner's Aurora Builder XML in "
                f"custom/{folder}/. Element names, types and descriptions are the source "
                f"files' own content. No model generated any of this, and nothing here is "
                f"derived from THE_PRIME_OMNIVERSE_CODEX.md, which is a leftover artifact of "
                f"an abandoned earlier version of the project. scale_note and synthesis left "
                f"empty: Assay values require Part Three's worksheet method."
            ),
        }
        written.append((r, record))
        if not args.dry_run:
            import pipeline as _P
            _P.write_record_catalogue(
                os.path.join(RECORDS, slug(source_name) + ".json"), record)
            r["entry_count"] = len(entries)
            r["status"] = "catalogued"

    if not args.dry_run and written:
        # ATOMIC: four scripts write this same roll (see silence.write_json). 2026-08-25.
        silence.write_json(ROLL, roll, indent=2, ensure_ascii=False)

    verb = "Would write" if args.dry_run else "Wrote"
    print(f"{verb} {len(written)} records from Aurora XML:\n")
    for r, rec in sorted(written, key=lambda x: -len(x[1]["entries"])):
        withtext = sum(1 for e in rec["entries"] if e["description"])
        print(f"  {len(rec['entries']):5d} entries ({withtext} with description)  {r['name']}")
    if args.dry_run:
        print("\n(dry run -- nothing written)")


if __name__ == "__main__":
    main()
