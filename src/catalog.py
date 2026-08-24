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
    path = os.path.join(HERE, cfg["paths"]["catalog"])
    if not os.path.exists(path):
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
        print(f"\nPopulated sources with NO books yet ({len(missing)}):")
        for n in missing[:30]:
            print(f"  - {n}")
        if len(missing) > 30:
            print(f"  ... and {len(missing) - 30} more")


def cmd_search(cfg, catalog, query):
    q = query.lower()
    hits = [(addr, v) for addr, v in catalog.items()
            if q in addr.lower() or q in v.get("source_name", "").lower()]
    print(f"{len(hits)} matches for '{query}':")
    for addr, v in hits:
        print(f"  {addr}  ({v['raw_bytes']} bytes, generated {v['generated_at']})")


def cmd_address(cfg, catalog, address):
    v = catalog.get(address)
    if not v:
        print(f"No entry for address: {address}")
        return
    print(json.dumps(v, indent=2))


def cmd_read(cfg, catalog, address):
    v = catalog.get(address)
    if not v:
        print(f"No entry for address: {address}")
        return
    raw_path = os.path.join(HERE, v["raw_path"])
    if os.path.exists(raw_path):
        with open(raw_path, encoding="utf-8") as f:
            print(f.read())
        return
    text = compress_store.load(os.path.join(HERE, v["compressed_path"]), v["codec"])
    print(text)


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

    if args.cmd == "stats":
        cmd_stats(cfg, catalog)
    elif args.cmd == "search":
        cmd_search(cfg, catalog, args.query)
    elif args.cmd == "address":
        cmd_address(cfg, catalog, args.address)
    elif args.cmd == "read":
        cmd_read(cfg, catalog, args.address)


if __name__ == "__main__":
    main()
