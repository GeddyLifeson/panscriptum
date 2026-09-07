#!/usr/bin/env python3
"""
Query what's been generated so far.

Usage:
    python3 src/catalog.py stats
    python3 src/catalog.py search "One Piece"
    python3 src/catalog.py address "II.L.6/Persons"
    python3 src/catalog.py read "II.L.6/Factions#11-13"

Addresses are `SpineCode/Chapter[#PageRange]`, exactly as they are keyed in
output/index/catalog.json. An earlier version of this docstring advertised a
`PANSCRIPTUM://Collection/Source/.../Chapter` URI form that appears nowhere else in the
codebase and that nothing has ever produced -- typing it verbatim always answered "No entry
for address", which reads as an empty catalogue rather than as a bad example. (2026-08-24.)
"""
import argparse
import json
import os
import sys

sys.path.insert(0, os.path.dirname(__file__))
import compress_store  # noqa: E402
import yaml  # noqa: E402

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def load_config():
    with open(os.path.join(HERE, "config.yaml"), encoding="utf-8") as f:
        return yaml.safe_load(f)


def load_catalog(cfg):
    """The generated-chapter index, or {} -- and it SAYS which (order 3f4d2d058fdc).

    A MISSING INDEX USED TO READ AS AN EMPTY ONE. This returned {} silently when the configured
    path did not exist, so `cmd_stats` printed "Sources with at least one generated chapter: 0"
    and "Total chapters/frontmatter pages generated: 0" -- byte-identical to a catalogue that
    exists and is genuinely empty. CLAUDE.md's "When you're done with a batch" section tells the
    operator to report current coverage from this command, so the one output a person is told to
    trust could not distinguish "nothing generated yet" from "the catalog file is not where
    config.yaml says it is". That is this project's signature failure shape: a broken read
    wearing the face of an honest negative.

    Still returns {}, so nothing downstream changes; what is added is the sentence saying so.
    """
    path = os.path.join(HERE, cfg["paths"]["catalog"])
    if not os.path.exists(path):
        print("NOTE: no catalog file at %s -- config.yaml's paths.catalog points there and "
              "nothing is on disk. The zero counts below mean 'not found', NOT 'nothing "
              "generated yet'." % path, file=sys.stderr)
        return {}
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def load_roll(cfg):
    with open(os.path.join(HERE, cfg["paths"]["data_roll"]), encoding="utf-8") as f:
        return json.load(f)


def cmd_stats(cfg, catalog):
    roll = load_roll(cfg)
    populated = [r for r in roll if r.get("entry_count", 0) > 0]
    sources_with_books = set(v["source_name"] for v in catalog.values())
    total_raw = sum(v["raw_bytes"] for v in catalog.values())
    total_compressed = sum(v["compressed_bytes"] for v in catalog.values())
    print(f"Sources on roll: {len(roll)}")
    print(f"Sources with entry data (ready for books): {len(populated)}")
    print(f"Sources with at least one generated chapter: {len(sources_with_books)}")
    print(f"Total chapters/frontmatter pages generated: {len(catalog)}")
    if total_raw:
        ratio = total_raw / max(total_compressed, 1)
        print(f"Raw text: {total_raw/1024:.1f} KB -> Compressed: {total_compressed/1024:.1f} KB "
              f"({ratio:.1f}x)")
    missing = [r["name"] for r in populated if r["name"] not in sources_with_books]
    if missing:
        # EVERY MISSING SOURCE, NO SLICE (order 6434c1ba7b20, HARD RULE 0). This was
        # `for n in missing[:30]` followed by an "... and N more" line. Measured live when the
        # order was filed: 209 populated sources had no books, 30 were printed and 179 were
        # hidden, and the 30 shown were the alphabetical head (2112 (Rush) .. Curious DM
        # Investigations) -- the first name past the cutoff was "Curse of Strahd". No flag
        # anywhere in this module printed the rest, so the roster was unreachable rather than
        # merely folded, and this is the exact pathology Hard Rule 0 names by example
        # ("cap=250 took the alphabetical head of every missing-cast repair").
        #
        # It matters more here than in most places: CLAUDE.md's "When you're done with a batch"
        # section tells the operator to report coverage from THIS command, so the truncation was
        # feeding a report that a person acts on. Ranking this roster would still be fine;
        # cutting it is not.
        print(f"\nPopulated sources with NO books yet ({len(missing)}):")
        for n in missing:
            print(f"  - {n}")


def cmd_search(cfg, catalog, query):
    q = query.lower()
    hits = [(addr, v) for addr, v in catalog.items()
            if q in addr.lower() or q in v.get("source_name", "").lower()]
    print(f"{len(hits)} matches for '{query}':")
    for addr, v in hits:
        print(f"  {addr}  ({v['raw_bytes']} bytes, generated {v['generated_at']})")


def cmd_address(cfg, catalog, address):
    """-> rc. A MISS IS rc=1 (order 3f4d2d058fdc). See main()."""
    v = catalog.get(address)
    if not v:
        print(f"No entry for address: {address}")
        return 1
    print(json.dumps(v, indent=2))
    return 0


def cmd_read(cfg, catalog, address):
    """-> rc. A MISS IS rc=1 (order 3f4d2d058fdc). See main()."""
    v = catalog.get(address)
    if not v:
        print(f"No entry for address: {address}")
        return 1
    raw_path = os.path.join(HERE, v["raw_path"])
    if os.path.exists(raw_path):
        with open(raw_path, encoding="utf-8") as f:
            print(f.read())
        return 0
    text = compress_store.load(os.path.join(HERE, v["compressed_path"]), v["codec"])
    print(text)
    return 0


def main():
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("stats")
    p_search = sub.add_parser("search")
    p_search.add_argument("query")
    p_addr = sub.add_parser("address")
    p_addr.add_argument("address")
    p_read = sub.add_parser("read")
    p_read.add_argument("address")
    args = ap.parse_args()

    cfg = load_config()
    catalog = load_catalog(cfg)

    # EVERY PATH USED TO EXIT 0 (order 3f4d2d058fdc). `main()` had no return statement and
    # `__main__` called it without `sys.exit`, so an unknown address ("No entry for address: X")
    # and a missing catalogue both exited 0 -- any script or scheduled step shelling out to
    # `catalog.py read ...` could not tell a hit from a miss. Every other CLI audited alongside
    # it ends `sys.exit(main())` and returns non-zero on a refusal: read.py, health.py,
    # identity.py, ingest_doc.py, sevenfold.py.
    if args.cmd == "stats":
        cmd_stats(cfg, catalog)
        return 0
    if args.cmd == "search":
        cmd_search(cfg, catalog, args.query)
        return 0
    if args.cmd == "address":
        return cmd_address(cfg, catalog, args.address)
    if args.cmd == "read":
        return cmd_read(cfg, catalog, args.address)
    return 2


if __name__ == "__main__":
    sys.exit(main())
