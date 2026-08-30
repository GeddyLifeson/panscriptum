#!/usr/bin/env python3
"""
THE ADDRESS SPACE — one fixed-width name for every planet in the omniverse.

(The width is DERIVED from the census, not chosen: `TOTAL_BITS` below is the number, and the
title used to state it as a literal for the same reason the table further down did. It was 74,
then 89; it moves whenever TIERS.json is re-charted.)

WHAT THIS IS
------------
The charter's Shelfmark is the Ladder-of-Being address of a thing: which hyperverse, which
universe, which galaxy, which world. `address.py` has been emitting the honest placeholder

    Ω › ? › ? › ...

since the beginning, because the classification research behind those question marks did not
exist. This module is that research, done as arithmetic rather than by hand.

THE SEED IDEA, AIMED AT THE RIGHT LAYER
---------------------------------------
The owner's instinct was to store a seed and learn the language of its bits. Against a PRNG seed
that cannot work -- seeds are constructed to be uninterpretable, and `worldseed.py` says why at
length.

Against an ADDRESS it works perfectly, and for the reason the PRNG case fails: an address is not
an index into chaos, it is a POSITION IN A STRUCTURE. Every field names a real level of the
cosmological hierarchy the library already derived, so the bits do mean things, and neighbouring
addresses ARE neighbours -- two worlds one bit apart in the planet field orbit the same star.

    [ hyperverse | xenoverse | metaverse | multiverse | universe | galaxy | star | planet ]

THE FIELD ORDER IS THE ONLY THING THIS DIAGRAM CLAIMS. It carries no bit counts and no total,
because it cannot compute them: a module docstring is a literal evaluated before `FIELDS` and
`WIDTHS` exist, so any number written here is a hand-copied transcription that goes stale
silently the moment the census moves. `python3 src/address_space.py` prints the live per-field
widths and the total, derived from `WIDTHS`/`TOTAL_BITS`; that is the only place to read them.

THIS TABLE WENT STALE ONCE AND MUST NOT AGAIN. It described the five-field, 74-bit/10-byte
address for three passes after `tiers.py` charted xenoverse, metaverse and multiverse and FIELDS
grew to eight, so the module's own advertised justification named a design the module no longer
had. It then said 89 bits / 12 bytes, correct on the day it was typed and equally unenforced --
and the upper-tier widths are read out of TIERS.json AT IMPORT, so a re-charting moves them
without touching this file. The authority is `FIELDS`/`WIDTHS` below and nothing else, and the
numbers have now been removed from here rather than re-transcribed, which is the only fix that
cannot drift a third time.

THE WIDTHS ARE DERIVED, NOT CHOSEN
----------------------------------
Each field is exactly wide enough for the census the weave and cosmography.py resolved:

    hyperverse  6        highest hyperverse index in TIERS.json, plus one
    xenoverse   6        the cut above the metaverses
    metaverse   8        resonance clusters -- multiverses joined by theme, law or recognition
    multiverse  168      continuity groups the catalogue resolved
    universe    64       continuities per multiverse
    galaxy      2.0e11   Lauer et al. 2021
    star        1.0e8    dwarf-dominated mean per galaxy
    planet      1.6      Cassan et al. 2012

The four upper tiers read their populations out of TIERS.json at import, so a re-charting moves
them; the floor of two in FIELDS keeps every field at least one bit wide. Change the census and
the widths change with it. Nothing here is a round number picked because it looked tidy.

FOR SCALE
---------
No Man's Sky addresses its galaxy with 64 bits: 1.8e19 planets, the great majority lifeless. This
omniverse holds 5.4e21 planets, of which 1.0e20 bear life -- so its LIVING worlds alone outnumber
that entire catalogue five and a half times over, and a 64-bit scheme cannot address it at all. It
falls short by a factor of a thousand.

Of those 1.0e20 living worlds, roughly 5,200 have ever been written down. The rest are addressable
and unvisited, which is the correct relationship between a library and a cosmos.
"""
import hashlib
import json
import math
import os
import sys

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import cosmography as C          # noqa: E402
import silence


def _continuities():
    try:
        with open(os.path.join(HERE, "data", "CONTINUITY_GROUPS.json"), encoding="utf-8") as f:
            return len(json.load(f)["groups"])
    except Exception:
        silence.note("address_space.py:continuity-groups")
        return 168


# CORRECTED against Part Two. The charter's own Shelfmark carries SEVEN tiers below Ω --
#
#     Ω › H? › X? › Mt.ASC › Mv.DRG › U-7 › G.North › P.Earth
#
# and an earlier version of this module had five, silently omitting xenoverse, metaverse and
# multiverse. Worse, it ASSIGNED a hyperverse (continuity_group % 7), which the charter names
# outright as the thing not to do:
#
#     "hyperverse position is uncharted; the Custodes considered guessing a form of lying"
#
# The charter's own worked citation prints H? and X? for exactly that reason. So this module now
# refuses those two tiers rather than filling them.
#
# The tiers that CAN be charted were already computed by the weave, which is the good news:
#
#     MULTIVERSE  "universes joined by a shared origin or connective law"  -> a continuity group
#     METAVERSE   "multiverses joined by RESONANCE -- theme, law, or mutual recognition"
#                                                                         -> a resonance cluster
#
# Those are not analogies. They are the definitions, and the weave's two graphs compute precisely
# those two relations. The 6 clusters the resonance graph yields at its natural threshold are
# metaverses; the 168 continuities are multiverses.
# CHARTED 2026-08-20. Part Two left H and X as '?' because the distinction between the upper
# tiers had been DEFINED but never operationalised -- there was no procedure that could look at two
# universes and say which tier joined them. tiers.py is that procedure: the four definitions name
# four strengths of connective evidence, and the resonance graph measures exactly that, so the
# tiers are four cuts of one dendrogram taken at its plateaus.
#
#     168 multiverses -> 8 metaverses -> 6 xenoverses -> 1 hyperverse
#
# Strictly nested, zero containment violations. The question marks come out.
def _tier_counts():
    try:
        with open(os.path.join(HERE, "data", "TIERS.json"), encoding="utf-8") as f:
            t = json.load(f)
        out = {}
        for k in ("hyperverse", "xenoverse", "metaverse", "multiverse"):
            out[k] = max((v[k] for v in t.values() if v.get(k) is not None), default=0) + 1
        return out
    except Exception:
        silence.note("address_space.py:tier-counts")
        return dict(hyperverse=1, xenoverse=6, metaverse=8, multiverse=168)


_TC = _tier_counts()
UNADDRESSED = None      # a shelf in no hyperverse: it shares no entity with anything


def _bits(n):
    return max(1, math.ceil(math.log2(max(2, n))))


# hyperverse and xenoverse are NOT fields. They are not unknown values awaiting a survey -- they
# are positions the charter declines to state, and reserving bits for them would invite filling
# them in.
FIELDS = [
    ("hyperverse", max(2, _TC["hyperverse"])),
    ("xenoverse",  max(2, _TC["xenoverse"])),
    ("metaverse",  max(2, _TC["metaverse"])),
    ("multiverse", max(2, _TC["multiverse"])),
    ("universe",   1 << 6),
    ("galaxy",     C.GALAXIES_DEFAULT),
    ("star",       C.STARS_PER_GALAXY_MEAN),
    ("planet",     C.PLANETS_PER_STAR),
]
WIDTHS = {name: _bits(n) for name, n in FIELDS}
TOTAL_BITS = sum(WIDTHS.values())
CAPACITY = 1 << TOTAL_BITS


def pack(hyperverse=0, xenoverse=0, metaverse=0, multiverse=0, universe=0,
         galaxy=0, star=0, planet=0):
    """Fields to a single integer address. Raises rather than truncating: a silently wrapped
    address would name a different world, which is the one failure mode worth being loud about."""
    vals = dict(hyperverse=hyperverse, xenoverse=xenoverse, metaverse=metaverse,
                multiverse=multiverse, universe=universe, galaxy=galaxy, star=star,
                planet=planet)
    out = 0
    for name, _ in FIELDS:
        w = WIDTHS[name]
        v = int(vals[name])
        if not (0 <= v < (1 << w)):
            raise ValueError(f"{name}={v} does not fit in {w} bits")
        out = (out << w) | v
    return out


def unpack(addr):
    out = {}
    for name, _ in reversed(FIELDS):
        w = WIDTHS[name]
        out[name] = addr & ((1 << w) - 1)
        addr >>= w
    return {k: out[k] for k, _ in FIELDS}


def shelfmark(addr):
    """The charter's own notation, with H and X printed as the charted integers they now are.

    THIS DOCSTRING SAID THE OPPOSITE FOR THREE SWEEPS. It claimed H and X print as '?' -- true of
    Part Two, and true of this function until tiers.py charted the upper tiers -- while the return
    statement below emitted real integers for both. Anyone who read the docstring and not the
    format string came away believing the module still emits the honest `Ω › ? › ?` placeholder,
    which is precisely the belief Hard Rule 4 exists to protect. The behaviour is deliberate and
    stays; only the description was wrong.

    Part Two is explicit that the Custodes "considered guessing a form of lying", and the charter's
    worked citation for Son Goku prints H? and X? for exactly that reason. Nothing here guesses:
    the two tiers stopped being uncharted when the resonance dendrogram was cut at its plateaus
    (168 multiverses -> 8 metaverses -> 6 xenoverses -> 1 hyperverse, strictly nested), so what
    prints is a measurement, not a filled-in blank. If TIERS.json is ever absent, `assign()` falls
    back to tier zero, and the note in `main()` says so out loud rather than letting a zero read
    as a survey.
    """
    f = unpack(addr)
    # H is the GROUNDING TYPE -- which answer this cosmos gives to the First Argument. It printed
    # '?' through two earlier passes: first because the tier was undefined, then because a
    # pantheon-seeded reading left most fictions homeless. Neither is true any more.
    return (f"Ω › H{f['hyperverse']} › X{f['xenoverse']} › Mt.{f['metaverse']} › "
            f"Mv.{f['multiverse']} › U-{f['universe']} › G.{f['galaxy']:x} › P.{f['planet']}")


def citation_card(name, addr, band="unassayed", decimal=None, interval=None,
                  epoch=None, attestation="Transcribed", worksheet=None, endonym=None,
                  threads=()):
    """The formal citation block of Part Seven, as a dict.

    Split deliberately into two halves, because the seed depends on which is which:

      IDENTITY     name, endonym, shelfmark. WHAT THE THING IS AND WHERE. Stable for the life of
                   the entry -- a world does not stop being that world.
      MEASUREMENT  assay, epoch, attestation, worksheet. WHAT THE LIBRARY CURRENTLY HOLDS about
                   it. Revisable by design; that is the whole point of an honest interval.
    """
    return {
        "identity": {
            "name": name,
            "endonym": endonym,
            "shelfmark": shelfmark(addr),
        },
        "measurement": {
            "assay": ("𝔄: DECLINED" if band == "declined" else
                      f"𝔄 {band}" + (f".{round(decimal*100):02d}" if decimal is not None else "")
                      + (f" ± {interval:.2f}" if interval is not None else "")),
            "epoch": epoch or "unstamped",
            "attestation": attestation,
            "worksheet": worksheet or "none — band-only per H5",
        },
        "threads": list(threads),
    }


def seed_from_card(card):
    """The generator seed, derived from the CITATION CARD -- and only from its identity half.

    This is the right key for two reasons.

    THE MOTH TEST. A reader holding the printed volume has the citation block on the page, so they
    can recompute the map themselves. A seed derived from an internal integer nobody publishes
    fails that test: it would make the terrain unverifiable by anyone outside this repository.

    AND THE MEASUREMENT HALF IS EXCLUDED ON PURPOSE. If the seed keyed on the assay, then
    re-assaying a world would move its mountains -- a revision to the record would rewrite the
    world the record is about, which inverts the entire relationship between a library and its
    subject. Magnitudes are revisable; geography is not downstream of them.
    """
    ident = card["identity"]
    key = "|".join(str(ident.get(k) or "") for k in ("name", "endonym", "shelfmark"))
    return int(hashlib.sha256(key.encode("utf-8")).hexdigest()[:8], 16)


def map_seed(addr):
    """Position-only seed. Retained for worlds with no card yet; prefer seed_from_card()."""
    return int(hashlib.sha256(str(addr).encode()).hexdigest()[:8], 16)


# WHERE THE HASHED FIELDS DRAW THEIR BITS FROM -- DERIVED, NOT TYPED IN.
#
# `assign()` shifted the digest by the literals 8, 48 and 78, which is the one thing this module
# tells you never to do: every width above is computed from the census precisely so that a
# re-charting moves it, and three hand-copied offsets sitting underneath them are the same
# hand-copied transcription the module docstring says went stale twice already. They do not
# overlap TODAY (universe ends at bit 6, galaxy spans 8..45, star 48..74, planet 78), and they
# stop being safe the moment the census grows: one more bit of galaxy than 40 and the galaxy slice
# reaches into the star's, so two fields would be drawn from correlated bits and nothing would
# say so. (Order 528fc483c4f0.)
#
# THE LEGACY OFFSETS ARE KEPT AS A FLOOR, AND THAT IS DELIBERATE. The offsets are what decide
# which bits a world's galaxy, star and planet come from, so changing them RE-ADDRESSES every
# world -- 1,016 of them currently standing in data/SHELFMARKS.json with map seeds derived from
# those addresses. Deriving them from a bare running total would have produced 0/6/44/71 and
# silently moved all 1,016, which is the same act as re-slugging a record: the address is the
# identity. So each offset is the running total of the widths below it, RAISED to the historical
# literal where that is larger. Today that reproduces 8/48/78 exactly and nothing moves; as the
# census grows the running total takes over and the fields still cannot overlap. Dropping the
# floor is a deliberate re-addressing and needs an owner's ruling, not a tidy-up.
_LEGACY_HASH_OFFSETS = {"galaxy": 8, "star": 48, "planet": 78}
_HASHED_FIELDS = ("universe", "galaxy", "star", "planet")


def _hash_offsets():
    """Bit offset into the digest for each hashed field. Derived from WIDTHS."""
    offsets, cursor = {}, 0
    for name in _HASHED_FIELDS:
        cursor = max(cursor, _LEGACY_HASH_OFFSETS.get(name, 0))
        offsets[name] = cursor
        cursor += WIDTHS[name]
    return offsets


HASH_OFFSETS = _hash_offsets()

# How much of the sha256 digest `assign()` has to read to reach the top of the last slice. Was a
# fixed `h[:16]`, which is 128 bits and was chosen when the top slice ended at bit 79. A layout
# that outgrows it would not raise -- the high slices would simply come back zero or clipped, so
# every world in the omniverse would share a planet index and nothing would report it. Derived
# from the offsets, floored at the historical 16 bytes so today's addresses are unchanged.
_HASH_SPAN = max(HASH_OFFSETS[n] + WIDTHS[n] for n in _HASHED_FIELDS)
HASH_BYTES = max(16, -(-_HASH_SPAN // 8))
if HASH_BYTES > 32:
    raise ValueError(
        f"address layout needs {HASH_BYTES} bytes of digest but sha256 gives 32; widen the "
        f"digest in assign() rather than letting the top fields silently read zero")


def assign(designation, tiers):
    """A deterministic address for a catalogued world, using its CHARTED tier stack.

    `tiers` is the source's row from TIERS.json: hyperverse, xenoverse, metaverse, multiverse. All
    four are measured by the weave rather than guessed here, which is what took the question marks
    out of the shelfmark. Galaxy, star and planet remain unknown in the sources and are hashed from
    the designation -- drawn reproducibly rather than differently on each run.
    """
    h = hashlib.sha256(designation.encode("utf-8")).digest()
    n = int.from_bytes(h[:HASH_BYTES], "big")

    def fit(v, field):
        # NO MODULO (order b6474eb0a258). This read `... % (1 << WIDTHS[field])`, and assign()
        # is this module's only real address producer -- the one main() uses for all 1,016
        # catalogued worlds -- so pack()'s promise to raise "rather than truncating: a silently
        # wrapped address would name a different world" was a guard whose sole production caller
        # pre-satisfied it. A check that cannot fail looks exactly like a check that passed.
        # Proved both halves before removing it: pack(multiverse=10**9) raises ValueError, while
        # assign('Demo::World', {'multiverse': 10**9}) returned an address whose unpacked
        # multiverse was 0 -- silently, with no note and no escalation. The value now reaches
        # pack(), which names the field and the width it overflowed.
        #
        # MEASURED AGAINST THE LIVE CENSUS FIRST, so this cannot break a run that works today:
        # TIERS.json holds 209 rows with hyperverse 2..5, xenoverse 0..5, metaverse 0..7 and
        # multiverse 0..167 against field capacities of 8/8/8/256, and all 1,016 designations in
        # WORLDSEEDS.json address with zero out-of-range tiers. The widths are DERIVED from the
        # census maxima, so a tier can only fall outside one if TIERS.json moved after import or
        # carries a negative -- and re-charting the census while a run holds the old widths
        # (order 60dc7c624c06) is precisely the circumstance in which the wrap used to fire.
        #
        # THE `None` -> 0 ARM IS DELIBERATELY UNCHANGED. A tier that is MISSING being addressed
        # at zero unmarked is a different fault and has its own open order (642a95fe9f3c); this
        # is about a tier that is PRESENT and TOO LARGE. The local keeps the name `fit` so that
        # order's citation still resolves.
        return 0 if v is None else int(v)

    def drawn(field):
        return (n >> HASH_OFFSETS[field]) % (1 << WIDTHS[field])

    return pack(fit(tiers.get("hyperverse"), "hyperverse"),
                fit(tiers.get("xenoverse"), "xenoverse"),
                fit(tiers.get("metaverse"), "metaverse"),
                fit(tiers.get("multiverse"), "multiverse"),
                drawn("universe"),
                drawn("galaxy"),
                drawn("star"),
                drawn("planet"))


def main():
    print("=" * 96)
    print(f"THE ADDRESS SPACE — every planet in the omniverse, named in {TOTAL_BITS} bits")
    print("=" * 96)
    print(f"\n{'field':<14}{'population':>14}{'bits':>7}   derived from")
    print("-" * 96)
    # BY FIELD NAME, ALWAYS -- the same lesson as the keyword-only pack() call further down, and
    # learned the same way. This table was a positional `zip(FIELDS, srcs)` over a five-entry
    # `srcs` list left behind by the five-field address. zip stops at the shorter side without
    # complaining, so galaxy, star and planet vanished from the printed report entirely and the
    # four tiers that tiers.py added took the citations written for the fields below them -- the
    # row labelled `xenoverse` printed "168 continuities resolved by the weave", which is the
    # multiverse's provenance, not the xenoverse's. A dict keyed by field name cannot mispair, and
    # the `?` default makes a field added without a citation visible instead of silently absent.
    srcs = {
        "hyperverse": "tiers.py: the dendrogram closes at a single root",
        "xenoverse":  "tiers.py: the plateau above the metaverses",
        "metaverse":  "weave.py: resonance clusters at the natural threshold",
        "multiverse": "168 continuities resolved by the weave",
        "universe":   "continuities per multiverse",
        "galaxy":     "Lauer et al. 2021 (New Horizons LORRI)",
        "star":       "dwarf-dominated mean stars per galaxy",
        "planet":     "Cassan et al. 2012, Nature",
    }
    for name, n in FIELDS:
        print(f"{name:<14}{n:>14.3e}{WIDTHS[name]:>7}   {srcs.get(name, '?')}")
    print(f"{'TOTAL':<14}{'':>14}{TOTAL_BITS:>7}   = {math.ceil(TOTAL_BITS/8)} bytes per world")
    print(f"\naddressable: {CAPACITY:.3e}   census says {C.census('STANDARD')['exoplanets']*_continuities():.3e} exist")
    print(f"headroom   : {CAPACITY/(C.census('STANDARD')['exoplanets']*_continuities()):.1f}x")

    print("\n" + "-" * 96)
    print("ROUND TRIP")
    print("-" * 96)
    # BY KEYWORD, ALWAYS. This demo was written when the address had five fields and was never
    # updated when xenoverse, metaverse and multiverse were added -- so `pack(3, 11, ...)` put
    # a universe index of 11 into a three-bit xenoverse field and the module raised on import.
    # It stayed broken because nothing ran it: `verify_math` exercises pack/unpack directly and
    # passed all twenty of its address-space checks the whole time. A positional call across
    # eight fields is a bug waiting for a ninth.
    fields = dict(hyperverse=3, xenoverse=2, metaverse=5, multiverse=97,
                  universe=11, galaxy=0x2A1F3B, star=0x5C91D2, planet=1)
    a = pack(**fields)
    print(f"   packed    {a}  (0x{a:x})")
    print(f"   unpacked  {unpack(a)}")
    print(f"   shelfmark {shelfmark(a)}")
    print(f"   map seed  {map_seed(a)}")
    assert unpack(a) == fields, f"round trip lost something: {unpack(a)} != {fields}"
    print("   round trip exact across all eight tiers")

    # Real worlds from the catalogue
    try:
        with open(os.path.join(HERE, "data", "WORLDSEEDS.json"), encoding="utf-8") as f:
            ws = json.load(f)
    except Exception:
        silence.note("address_space.py:worldseeds")
        ws = {}
    if ws:
        print("\n" + "-" * 96)
        print("CATALOGUED WORLDS, ADDRESSED")
        print("-" * 96)
        # assign() takes the source's CHARTED TIER STACK, not a continuity-group integer. That
        # second argument changed when the weave started measuring hyperverse/xenoverse/metaverse
        # instead of leaving them as question marks, and this caller was never updated -- it kept
        # handing an int to something that calls .get() on it. Same staleness as the positional
        # pack() above, and it survived for the same reason: nothing ran this file.
        tiers_path = os.path.join(HERE, "data", "TIERS.json")
        try:
            with open(tiers_path, encoding="utf-8") as f:
                tiers = json.load(f)
        except Exception:
            silence.note("address_space.py:tiers")
            tiers = {}
        addrs = {}
        for desig, w in ws.items():
            # A worldseed designation is "Source::World"; the tier stack is charted per SOURCE.
            src = desig.split("::")[0]
            addrs[desig] = assign(desig, tiers.get(src) or {})
        if not tiers:
            print("   (TIERS.json absent -- every world addressed at tier zero, which is a "
                  "placeholder and not a charting)")
        print(f"   worlds addressed : {len(addrs):,}")
        print(f"   collisions       : {len(addrs) - len(set(addrs.values()))}")
        for d, a in list(addrs.items())[:6]:
            print(f"     {d[:44]:<46}{shelfmark(a)}")
        out = os.path.join(HERE, "data", "SHELFMARKS.json")
        # ATOMIC: pipeline.py and standards.py both read SHELFMARKS.json.
        #
        # GATED, like scope.py's build() and zfighters.py's main(). `write_json` returns whether
        # the rename LANDED and this dropped the verdict, so a denied replace -- the ordinary
        # Windows case here, since `pipeline.py:2024` reads this file as a phase input and
        # `standards.py:1009` reads it on its own clock, and either holding it open is enough --
        # still reached the unconditional `wrote {out}` below and exit 0. The addresses printed
        # above would then be the ones this run computed while the file both readers consult
        # held the PREVIOUS run's, which is the shape that makes a re-address look applied when
        # nothing moved. Nothing here can retry the rename, so the honest act is to say so and
        # exit nonzero: the map is regenerable by re-running, but a shelfmark read as fresh
        # while it is stale is not recoverable by anything downstream. (run #37 sweep.)
        if not silence.write_json(out,
                                  {d: {"address": a, "shelfmark": shelfmark(a),
                                       "map_seed": map_seed(a)} for d, a in addrs.items()},
                                  indent=2, ensure_ascii=False):
            # NO `silence.note` HERE, deliberately. `replace_retry` has already recorded
            # `replace-denied:SHELFMARKS.json` in the health ledger by the time it answers
            # False, so a note at this site would file the same denial twice under two names --
            # and this file's note-tag inventory is itself asserted, tag by tag, by
            # `handoff/run35/checks_L4.py`. The visible channel for this module is the console
            # and the exit code, and both are used below.
            print(f"\n   WRITE DENIED -> {out}: the replace was refused (most likely a reader "
                  f"holding it open). The addresses above did NOT land, and pipeline.py and "
                  f"standards.py are still reading the previous map. Re-run to retry.")
            return 1
        print(f"\n   wrote {out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
