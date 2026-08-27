#!/usr/bin/env python3
"""
THE WORLD PROFILE — one string that says everything, and from which everything regenerates.

THE POINT
---------
A world currently needs five files to describe it: an address, a genre, a feature vector, a band,
and an attestation status. Handing someone a world means handing them a paragraph.

The precedent for fixing that is fifty years old. Traveller's Universal World Profile compresses a
whole planet into nine characters -- starport, size, atmosphere, hydrographics, population,
government, law, tech -- and two referees who have never met can exchange one and mean the same
world. The idea is not compression for its own sake. It is that a NAME WITH STRUCTURE is a thing
you can hand over, sort, index, and check, and a paragraph is not.

THE PANSCRIPTUM PROFILE

    PS-<address>-<gr><rg>-<lcce>-<band><att>

    address   the 89-bit shelfmark in base32: where the world IS
    gr rg     genre and naming register: what KIND of story it belongs to
    lcce      landform, climate, condition, era: what the world IS LIKE
    band      Magnitude, 0-A, or 'u' for unassayed
    att       how many of the four world axes the sources actually attested, 0-4

Everything downstream derives from it and nothing else has to be stored:

    the surface map      Azgaar FMG, seeded from the address
    the star system      a hierarchical galaxy API, whose galaxy/neighbourhood/star seeds nest
                         the same way this address does
    the naming           the register, which the genre fixes
    the shelf            the band

WHAT THE PROFILE DELIBERATELY CARRIES
-------------------------------------
The attestation digit is not decoration and it is the field a compression scheme would drop first.
Only 29.9% of world axes come from a source; the rest are seeded. A profile that did not say so
would present a coin-flip and a citation in identical type, which is the single thing this library
is built not to do.
"""
import re
import sys
import os

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import address_space as AS      # noqa: E402
import worldseed as WS          # noqa: E402
import silence

# Crockford Base32: no i, l, o, u. THIRTY-TWO SYMBOLS, and the count is the whole point.
# This string carried THIRTY-THREE until run #33 -- `u` was still in it, at index 27, while the
# comment beside it claimed `u` was excluded. Two things went wrong at once. `_b32` masks with
# `n & 31`, so it can only ever emit indices 0-31 and the 33rd symbol `z` was unreachable from
# the encoder; `_unb32`, which has no such mask, would happily accept a `z` and return 32 for
# it, so a profile string that picked up a stray character decoded to a SILENTLY WRONG address
# rather than refusing -- an alphabet that can read what it cannot write is a decoder that
# cannot say "this is not one of mine". And `u` sitting in the address alphabet collided in
# spirit with `encode`'s use of `u` as the band's "unassayed" sentinel: the one character the
# format reserves to mean "no band was ever assayed" was also a legal address digit. Removing
# it makes `u` unambiguous across the whole profile and brings the alphabet to the 32 symbols
# the mask and the comment both already assumed. No profile string is persisted anywhere (the
# set is rebuilt from `worldseed` + `address_space` on every call to `build_all`), so this
# re-lettering of digits 27-31 rewrites nothing on disk. Found by the run #33 sweep.
B32 = "0123456789abcdefghjkmnpqrstvwxyz"

GENRE_CODE = {
    "mythology": "my", "high_fantasy": "hf", "grimdark": "gd", "cosmic_horror": "ch",
    "space_opera": "so", "cyberpunk": "cp", "post_apocalyptic": "pa", "military_modern": "mm",
    "superhero": "sh", "eastern": "ea", "whimsy": "wh", "unclassified": "un",
}
GENRE_FROM = {v: k for k, v in GENRE_CODE.items()}
REG_CODE = {"classical": "c", "guttural": "g", "liquid": "l",
            "sibilant": "s", "compact": "k", "long": "n"}
REG_FROM = {v: k for k, v in REG_CODE.items()}

AXES = [("landform", WS.LANDFORM), ("climate", WS.CLIMATE),
        ("condition", WS.CONDITION), ("tech", WS.TECH)]
BANDS = ["M0", "M1", "M2", "M3", "M4", "M5", "M6", "M7", "M8", "M9", "M10"]


def _b32(n):
    if n == 0:
        return "0"
    out = []
    while n:
        out.append(B32[n & 31])
        n >>= 5
    return "".join(reversed(out))


def _unb32(s):
    n = 0
    for ch in s:
        n = (n << 5) | B32.index(ch)
    return n


def encode(address, genre, register, features, band="unassayed", attested=0):
    a = _b32(address)
    g = GENRE_CODE.get(genre, "un") + REG_CODE.get(register, "c")
    f = "".join(B32[[n for n, _ in tbl].index(features[axis])] for axis, tbl in AXES)
    b = "u" if band in (None, "unassayed") else B32[BANDS.index(band)]
    return f"PS-{a}-{g}-{f}-{b}{attested}"


def decode(profile):
    m = re.fullmatch(r"PS-([0-9a-z]+)-([a-z]{2})([a-z])-([0-9a-z]{4})-([0-9au])([0-4])", profile)
    if not m:
        raise ValueError(f"not a world profile: {profile!r}")
    addr, gr, rg, feats, band, att = m.groups()
    address = _unb32(addr)
    features = {axis: tbl[B32.index(ch)][0] for (axis, tbl), ch in zip(AXES, feats)}
    return {
        "address": address,
        "shelfmark": AS.shelfmark(address),
        "fields": AS.unpack(address),
        "map_seed": AS.map_seed(address),
        "genre": GENRE_FROM.get(gr, "unclassified"),
        "register": REG_FROM.get(rg, "classical"),
        "features": features,
        "band": "unassayed" if band == "u" else BANDS[B32.index(band)],
        "attested_axes": int(att),
        "profile": profile,
    }


def galaxy_api(address, base="https://galaxy-generator.oogabooga.dev/api/galaxy"):
    """The star system, from a hierarchical galaxy service.

    That service nests its seeds exactly as this address does -- a neighbourhood seed is derived
    from its galaxy's -- so the address's own galaxy field IS the galaxy seed and no translation
    layer is needed. The endpoint shape is that project's business and should be checked against
    the version in use; the nesting is the part that matters and it matches.
    """
    f = AS.unpack(address)
    return f"{base}?seed={f['galaxy']}", f"{base}/{f['galaxy']}/neighbourhood?seed={f['star']}"


def build_all(limit=None):
    import json
    try:
        genres = json.load(open(os.path.join(HERE, "data", "GENRES.json"), encoding="utf-8"))
    except Exception:
        silence.note("profile.py:131")
        genres = {}
    try:
        tiers = json.load(open(os.path.join(HERE, "data", "TIERS.json"), encoding="utf-8"))
    except Exception:
        silence.note("profile.py:135")
        tiers = {}

    out = []
    for w in WS.build_all(limit):
        src = w["designation"].split("::")[0]
        gspec = genres.get(src, {})
        genre = gspec.get("genre", "unclassified")
        register = gspec.get("register", "classical")
        addr = AS.assign(w["designation"], tiers.get(src, {}))
        out.append({
            "designation": w["designation"],
            "profile": encode(addr, genre, register, w["features"],
                              w.get("band", "unassayed"), w.get("attested_axes", 0)),
            "address": addr,
        })
    return out


def main():
    rows = build_all()
    print("=" * 100)
    print("THE WORLD PROFILE — a whole world in one string")
    print("=" * 100)
    lens = [len(r["profile"]) for r in rows]
    print(f"\nworlds profiled : {len(rows):,}")
    print(f"profile length  : {min(lens)}-{max(lens)} chars "
          f"(mean {sum(lens)/len(lens):.1f})")
    print(f"whole library   : {sum(lens)/1024:.1f} KB for every world it has ever named")
    print(f"unique profiles : {len({r['profile'] for r in rows}):,}")

    print("\n" + "-" * 100)
    print("SAMPLE")
    print("-" * 100)
    for r in rows[:8]:
        d = decode(r["profile"])
        print(f"\n  {r['designation'][:56]}")
        print(f"     {r['profile']}")
        print(f"     {d['shelfmark']}")
        print(f"     {d['genre']}/{d['register']}  {d['features']}  "
              f"band={d['band']}  attested {d['attested_axes']}/4")

    print("\n" + "-" * 100)
    print("ROUND TRIP — the string must reconstruct the world exactly")
    print("-" * 100)
    bad = 0
    for r in rows:
        d = decode(r["profile"])
        # `d["profile"]` is decode()'s own argument echoed back (line 125 above) -- comparing it
        # to `r["profile"]` compares that string with itself and can never fail. The real
        # round trip is to RE-ENCODE what decode() extracted and check it reproduces the exact
        # string, which is the only way genre, register, features, band and attested_axes -- the
        # five fields decode() touches that nothing was ever checking -- get exercised at all.
        re_encoded = encode(d["address"], d["genre"], d["register"], d["features"],
                             d["band"], d["attested_axes"])
        if d["address"] != r["address"] or re_encoded != r["profile"]:
            bad += 1
    print(f"   {len(rows)-bad:,} of {len(rows):,} round-trip exactly   failures: {bad}")

    print("\n" + "-" * 100)
    print("WHAT REGENERATES FROM IT, WITH NOTHING ELSE STORED")
    print("-" * 100)
    d = decode(rows[0]["profile"])
    g, n = galaxy_api(d["address"])
    print(f"   surface map  https://azgaar.github.io/Fantasy-Map-Generator/?seed={d['map_seed']}&...")
    print(f"   galaxy       {g}")
    print(f"   neighbourhood{n}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
