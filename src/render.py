#!/usr/bin/env python3
"""
RENDER — one dispatcher, nine tiers, from a burg to a hyperverse.

THE GAP THIS CLOSES
-------------------
Four tiers could be seen and five could not:

    burg           Azgaar's ?burg= parameter, which hands off to Watabou      WIRED
    planet         Azgaar's Fantasy Map Generator, seeded from the card       WIRED
    star system    a hierarchical galaxy service                              WIRED
    galaxy         the same service, one level up                             WIRED
    universe                                                                  nothing
    multiverse                                                                nothing
    metaverse                                                                 nothing
    xenoverse                                                                 nothing
    hyperverse                                                                nothing

The top five had addresses and no way to look at them.

WHY THE FIX IS NOT "FIND A BIGGER MAP GENERATOR"
------------------------------------------------
There isn't one, and there should not be. A map generator draws TERRAIN, and terrain stops at the
planet. A galaxy still has positions, which is why a galaxy service works. Above that there are no
positions at all -- a metaverse is not a place, it is a set of multiverses joined by resonance,
and asking what it looks like from outside is a category error of the same kind as asking where
the Ladder is kept.

What the upper tiers have is STRUCTURE: what contains what, how many, and how strongly joined. So
they are drawn rather than fetched -- a containment diagram, generated here, deterministic from
the same tree the shelfmark comes from. Below the galaxy the library defers to tools built for
terrain; above it, it draws its own.

    tiers 1-4   a URL to an external generator
    tiers 5-9   an SVG, generated from the sevenfold tree

One call, `view()`, takes a coordinate at any tier and returns whichever is right.
"""
import argparse
import hashlib
import html
import json
import math
import os
import sys

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# `sevenfold` is no longer imported here: the only use was `children_of`'s SF.TIERS gate, which
# asserted a schema instead of reading the tree (see the note there). pyflakes is load-bearing in
# this project's LINT tier, so a kept-for-documentation import would fail the sweep.

FMG = "https://azgaar.github.io/Fantasy-Map-Generator/"
GALAXY = "https://galaxy-generator.oogabooga.dev/api/galaxy"

TIER_ORDER = ("hyperverse", "xenoverse", "metaverse", "multiverse", "universe",
              "galaxy", "system", "planet", "burg")
DRAWN = TIER_ORDER[:5]          # no terrain, no positions -- drawn here
FETCHED = TIER_ORDER[5:]        # terrain or positions -- deferred to a generator


# ==================================================================================================
# 1. THE FETCHED TIERS
# ==================================================================================================

def galaxy_view(galaxy_id):
    return f"{GALAXY}?seed={galaxy_id}"


def system_view(galaxy_id, star_id):
    return f"{GALAXY}/{galaxy_id}/neighbourhood?seed={star_id}"


def planet_view(map_seed, scale=1):
    return f"{FMG}?seed={map_seed}&options=default&scale={scale}"


def burg_view(map_seed, rank, scale=8):
    """Through Azgaar, never around it -- its own integration performs the Watabou hand-off."""
    return f"{FMG}?seed={map_seed}&options=default&scale={scale}&burg={rank}"


# ==================================================================================================
# 2. THE DRAWN TIERS
# ==================================================================================================

PALETTE = {
    "hyperverse": ("#1a1033", "#e8d9ff", "#8b6fd4"),
    "xenoverse":  ("#0f1f2e", "#d4ecff", "#4f9fd4"),
    "metaverse":  ("#0e2620", "#d6f5e8", "#4fb391"),
    "multiverse": ("#2b1c0d", "#ffe9cc", "#c98b3f"),
    "universe":   ("#26111a", "#ffd9e6", "#c4557f"),
}


def _hue(seed):
    return int(hashlib.sha256(str(seed).encode()).hexdigest()[:4], 16) % 360


def containment_svg(tier, label, children, width=920, height=520):
    """A containment diagram: this node, and what it holds.

    Radial rather than a tree, because containment at these tiers is not a hierarchy anyone walks
    -- nothing travels from a metaverse to its multiverses. The ring says 'these are the parts of
    this' without implying a route, which a tree would.
    """
    bg, fg, accent = PALETTE.get(tier, ("#111", "#eee", "#888"))
    cx, cy = width / 2, height / 2 + 10
    n = max(1, len(children))
    radius = min(width, height) * 0.31

    out = [f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {width} {height}" '
           f'width="{width}" height="{height}" role="img" '
           f'aria-label="{html.escape(tier)} {html.escape(str(label))}">',
           f'<rect width="{width}" height="{height}" fill="{bg}"/>',
           f'<text x="{width/2}" y="42" fill="{fg}" font-family="Georgia,serif" '
           f'font-size="21" text-anchor="middle" letter-spacing="2">'
           f'{html.escape(tier.upper())} &#183; {html.escape(str(label))}</text>',
           f'<text x="{width/2}" y="66" fill="{accent}" font-family="Georgia,serif" '
           f'font-size="12.5" text-anchor="middle">'
           f'{n} {"child" if n == 1 else "children"} &#183; span 1&#8211;7</text>']

    # the containing node
    out.append(f'<circle cx="{cx}" cy="{cy}" r="{radius*0.30:.1f}" fill="none" '
               f'stroke="{accent}" stroke-width="1.1" stroke-dasharray="3 5" opacity="0.65"/>')

    for i, ch in enumerate(children):
        ang = -math.pi / 2 + (2 * math.pi * i / n)
        x, y = cx + radius * math.cos(ang), cy + radius * math.sin(ang)
        size = ch.get("weight", 1)
        r = 15 + min(26, 5.2 * math.log2(1 + size))
        hue = _hue(f"{tier}:{label}:{i}")
        out.append(f'<line x1="{cx}" y1="{cy}" x2="{x:.1f}" y2="{y:.1f}" '
                   f'stroke="{accent}" stroke-width="0.9" opacity="0.4"/>')
        out.append(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="{r:.1f}" '
                   f'fill="hsl({hue},44%,26%)" stroke="{accent}" stroke-width="1.3"/>')
        out.append(f'<text x="{x:.1f}" y="{y+4:.1f}" fill="{fg}" font-family="Georgia,serif" '
                   f'font-size="13" text-anchor="middle">{html.escape(str(ch["id"]))}</text>')
        nm = str(ch.get("name", ""))[:26]
        if nm:
            dy = r + 15 if math.sin(ang) >= 0 else -(r + 7)
            out.append(f'<text x="{x:.1f}" y="{y+dy:.1f}" fill="{accent}" '
                       f'font-family="Georgia,serif" font-size="10.5" '
                       f'text-anchor="middle">{html.escape(nm)}</text>')

    out.append(f'<text x="{width/2}" y="{height-16}" fill="{accent}" '
               f'font-family="Georgia,serif" font-size="10" text-anchor="middle" opacity="0.75">'
               f'drawn, not fetched &#183; there is no terrain at this tier</text>')
    out.append("</svg>")
    return "\n".join(out)


# ==================================================================================================
# 3. THE DISPATCHER
# ==================================================================================================

def _tree():
    with open(os.path.join(HERE, "data", "SEVENFOLD.json"), encoding="utf-8") as f:
        return json.load(f)


def children_of(tier, coord, tree=None):
    """What a node at this tier contains, read from the sevenfold tree."""
    tree = tree or _tree()
    pools = {**tree.get("sources", {}), **tree.get("worlds", {})}
    idx = TIER_ORDER.index(tier)
    child_tier = TIER_ORDER[idx + 1] if idx + 1 < len(TIER_ORDER) else None
    # Gate on whether the TREE charts the child tier, not on whether the child tier is one of
    # SF.TIERS. The two agree today -- SEVENFOLD.json's deepest coordinate is `universe`, so
    # `universe` has no charted children by either test -- but the SF.TIERS form is an
    # assumption about the schema rather than a reading of it: the moment galaxy coordinates are
    # charted, `children_of("universe", ...)` would keep returning [] and the emptiness would
    # look like data rather than a stale guard. The per-entry `child_tier not in c` check below
    # already does the honest work.
    if child_tier is None:
        return []
    prefix = TIER_ORDER[:idx + 1]
    buckets = {}
    for name, c in pools.items():
        if any(c.get(t) != coord.get(t) for t in prefix if t in coord):
            continue
        if child_tier not in c:
            continue
        buckets.setdefault(c[child_tier], []).append(name)
    return [{"id": k, "weight": len(v), "name": (v[0].split("::")[0][:24] if v else "")}
            for k, v in sorted(buckets.items())]


def view(tier, coord=None, map_seed=None, galaxy=None, star=None, rank=None, tree=None):
    """One call for any tier. Returns {'kind': 'url'|'svg', ...}."""
    if tier == "burg":
        return {"kind": "url", "url": burg_view(map_seed, rank or 1)}
    if tier == "planet":
        return {"kind": "url", "url": planet_view(map_seed)}
    if tier == "system":
        return {"kind": "url", "url": system_view(galaxy, star)}
    if tier == "galaxy":
        return {"kind": "url", "url": galaxy_view(galaxy)}
    if tier in DRAWN:
        kids = children_of(tier, coord or {}, tree)
        label = coord.get(tier, "?") if coord else "?"
        return {"kind": "svg", "tier": tier, "children": len(kids),
                "svg": containment_svg(tier, label, kids)}
    raise ValueError(f"unknown tier {tier!r}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--write", action="store_true")
    args = ap.parse_args()

    tree = _tree()
    print("=" * 92)
    print("RENDER — every tier, from a burg to a hyperverse")
    print("=" * 92)
    print(f"\n{'tier':<14}{'kind':<8}{'how'}")
    print("-" * 92)

    import worldseed as WS
    import address_space as AS
    w = WS.build_all(limit=1)[0]
    seed = AS.map_seed(w["seed"])
    sample = next(iter(tree["worlds"].values()))

    rows = []
    for t in TIER_ORDER:
        if t in FETCHED:
            v = view(t, map_seed=seed, galaxy=54167113046, star=42873198, rank=1)
            rows.append((t, "url", v["url"][:64]))
        else:
            v = view(t, coord=sample, tree=tree)
            rows.append((t, "svg", f"{v['children']} children, {len(v['svg']):,} bytes"))
    for t, k, how in rows:
        print(f"{t:<14}{k:<8}{how}")

    print(f"\nall {len(TIER_ORDER)} tiers viewable")

    if args.write:
        out = os.path.join(HERE, "output", "views")
        os.makedirs(out, exist_ok=True)
        for t in DRAWN:
            v = view(t, coord=sample, tree=tree)
            p = os.path.join(out, f"{t}.svg")
            with open(p, "w", encoding="utf-8") as f:
                f.write(v["svg"])
        print(f"wrote {len(DRAWN)} diagrams to output/views/")
    return 0


if __name__ == "__main__":
    sys.exit(main())
