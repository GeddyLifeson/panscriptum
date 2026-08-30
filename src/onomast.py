#!/usr/bin/env python3
"""
THE ONOMASTICON — distinct designations for the worlds that all call themselves Earth.

THE PROBLEM, AND WHY IT IS NOT A LABELLING PROBLEM
--------------------------------------------------
Resolution finds twenty-six distinct worlds named Earth, fifteen named Moon, fourteen named Mars.
Keeping them all as "Earth" produces a catalogue in which the commonest entry is a name shared by
twenty-six unrelated planets, and every cross-reference to it is ambiguous.

The tempting fix is a serial number. It is the wrong fix, because it treats the repetition as an
accident of bookkeeping when the repetition is a FACT ABOUT THE OMNIVERSE that wants explaining.

THE DOCTRINE OF CARRIED NAMES
-----------------------------
Twenty-six peoples, with no contact between them, call their world by the same word. That is not
coincidence and it is not identity. It is DESCENT.

Each of these peoples holds a founding tradition that their line began on Earth. Carrying the
tradition, they carried the name, and applied it to the world they actually inhabit -- which is
what every settled people has ever done. New Amsterdam, New England, New Carthage: the name
travels with the people and lands on new ground.

So the reading is:

    THE NAME "EARTH" IS AN ENDONYM OF DESCENT, NOT A DESIGNATION OF IDENTITY.

There is one Earth. There are twenty-six worlds whose peoples remember it, live somewhere else, and
call that somewhere else by the remembered name. The Library therefore assigns each world its own
catalogue designation and RECORDS the endonym, because what a people calls its own world is a
fact about the people and belongs in the record.

This generalises exactly as far as the mechanism does. It covers worlds and the toponyms carried
onto them -- Earth, Moon, Mars, Venus, Sun, and terrestrial place-names reapplied to new ground.
It does NOT cover Cerberus or Leviathan: two distinct beings sharing a name is ordinary homonymy,
not a carried tradition, and inventing a mechanism for it would be the second-mechanism error
X.10 §4 warns against.

THE TWO NAMING LAYERS
---------------------
A world carries two names and they answer different questions, so neither is a compromise for the
other. This began as a technical limitation -- Azgaar's generator will not take a culture set from
a query string, so the names on a map cannot be steered from here -- and the owner's ruling turns
it into the correct structure, which is what it should have been anyway.

    CATALOGUE DESIGNATION   what the Library files the world under: Coriantum, Vilarum, Amastes.
                            Assigned here, from the register its genre and features imply.
                            Stable, unique, and the name every cross-reference uses.

    INTERNAL TOPONYMY       what the world calls itself and its own parts: its endonym, and the
                            names of its states, cities and rivers. Generated with the map, by
                            the world rather than about it.

This is the ordinary practice of every serious catalogue. A national library files a place under
an authorised heading and the people who live there go on calling it what they call it; the
exonym and the endonym are both correct and neither is the real one. The Doctrine of Carried
Names above is the same distinction applied to a single word -- twenty-six peoples call their
world Earth, and the Library files twenty-six designations -- so the layering was already here,
and this only names it.

What the record must never do is present one layer as the other. An entry gives the designation
as its heading and the endonym in its body, because what a people calls its own world is a fact
about that people and belongs in the record beside the shelfmark, not instead of it.

REPRODUCIBILITY
---------------
Designations are generated deterministically from the world's own catalogue position, so a Custos
who reruns this gets the same names. The Moth test applies to naming as much as to arithmetic:
*can a stranger, given the citations, get your number?* -- and a name nobody else can re-derive is
a name the Library cannot stand behind.
"""
import hashlib
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import silence                                                          # noqa: E402

RESOLVED = os.path.join(HERE, "data", "RESOLVED_ENTITIES.json")
OUT = os.path.join(HERE, "data", "ONOMASTICON.json")


# ==================================================================================================
# WHAT THE DOCTRINE COVERS
# ==================================================================================================
#
# Solar-system bodies and terrestrial toponyms: the names a people of Earth-descent would carry
# with them. Matched on the canonical name, case-insensitively, allowing a parenthetical gloss.
CARRIED_NAMES = {
    "earth", "the earth", "terra", "moon", "the moon", "luna", "mars", "venus", "mercury",
    "jupiter", "saturn", "neptune", "uranus", "pluto", "sun", "the sun", "sol",
    "japan", "china", "russia", "france", "england", "germany", "italy", "egypt", "greece",
    "new york city", "new york", "london", "paris", "tokyo", "rome", "berlin", "moscow",
    "chicago", "los angeles", "san francisco", "cairo", "athens", "atlantis",
}


def is_carried(name):
    """Does this name fall under the doctrine? Strips a parenthetical gloss first."""
    base = re.sub(r"\s*\([^)]*\)\s*", "", name or "").strip().lower()
    return base in CARRIED_NAMES


# ==================================================================================================
# THE SYLLABARY
# ==================================================================================================
#
# Six registers, each with its own phonotactics. The register is chosen by CONTINUITY, so worlds
# sharing a continuity sound related to one another and worlds from unrelated universes do not --
# which is the correct acoustic signal, since naming conventions are a property of a culture and
# cultures do not cross shelves.
REGISTERS = {
    "classical": dict(
        onset=["V", "S", "T", "C", "M", "L", "N", "R", "Val", "Ser", "Cor", "Tel", "Am", "Or"],
        mid=["a", "e", "i", "o", "au", "ia", "eo"],
        coda=["r", "n", "l", "s", "nt", "st", "rn", "ll"],
        end=["ia", "us", "um", "or", "es", "anum", "ium"],
    ),
    "guttural": dict(
        onset=["K", "G", "Kr", "Gr", "Dr", "Th", "Vh", "Kh", "Tor", "Kar", "Grim", "Vor"],
        mid=["a", "u", "o", "ai", "ou"],
        coda=["k", "g", "rk", "gg", "th", "kt", "rn", "zh"],
        end=["ar", "un", "oth", "ak", "urn", "grad", "ok"],
    ),
    "liquid": dict(
        onset=["El", "Ly", "Ae", "Mi", "Nu", "Ry", "Sil", "Ala", "Ily", "Ori", "Ven"],
        mid=["a", "e", "i", "ae", "ei", "io", "ua"],
        coda=["l", "n", "r", "m", "ll", "nn", "rl"],
        end=["a", "ae", "eth", "iel", "ora", "wen", "ys"],
    ),
    "sibilant": dict(
        onset=["S", "Sh", "Th", "Ves", "Ash", "Sy", "Zeph", "Xa", "Is", "Os"],
        mid=["e", "i", "a", "ei", "ia", "yu"],
        coda=["s", "sh", "th", "ss", "st", "vs", "z"],
        end=["eth", "is", "ess", "ith", "asha", "yss", "ora"],
    ),
    "compact": dict(
        onset=["Th", "Br", "Cr", "Dr", "Fen", "Hal", "Jor", "Kel", "Mor", "Pel", "Tarn"],
        mid=["a", "e", "o", "u"],
        coda=["n", "r", "d", "rn", "ld", "rd", "st"],
        end=["e", "en", "ar", "on", "ath", "eld", "ock"],
    ),
    "long": dict(
        onset=["Ten", "Osu", "Ana", "Kalu", "Mera", "Sura", "Tira", "Vana", "Ilo", "Uka"],
        mid=["ra", "ka", "na", "va", "sa", "ta", "la", "ma"],
        coda=["n", "l", "r", "m", ""],
        end=["um", "ari", "ala", "eno", "ira", "oma", "uta"],
    ),
}
REGISTER_ORDER = sorted(REGISTERS)


def _stream(seed):
    """A deterministic byte stream from a seed string. No RNG state, so no ordering hazards."""
    buf, i = b"", 0
    while True:
        if not buf:
            buf = hashlib.sha256(f"{seed}:{i}".encode("utf-8")).digest()
            i += 1
        yield buf[0]
        buf = buf[1:]


_VOWELS = set("aeiouy")


def well_formed(name):
    """Is this a name a Custos could say aloud and write down twice the same way?

    The first generator produced Shiashiathasha, Goggoktok and Zgournazhun alongside perfectly
    good names like Amastes and Valeornus. Random morpheme concatenation has no opinion about
    whether a result is pronounceable, so the opinion has to be supplied.

    Four constraints, all mechanical:
      length      4 to 11 characters -- long enough to be distinctive, short enough to shelve
      echo        no trigram appearing twice (kills Shiashiathasha, Shessasha)
      stutter     no immediately doubled syllable (kills Goggoktok, Khakak)
      cluster     no run of three consonants (kills Zgournazhun's opening)
    """
    n = name.lower()
    if not (4 <= len(n) <= 11):
        return False
    for i in range(len(n) - 2):
        if n.count(n[i:i + 3]) > 1:
            return False
    for i in range(len(n) - 3):
        if n[i:i + 2] == n[i + 2:i + 4]:
            return False
    run = 0
    for ch in n:
        run = 0 if ch in _VOWELS else run + 1
        if run >= 3:
            return False
    # Consonant density. Shessasha (s x4) and Goggournok (g x3) pass every repetition test above
    # -- they alternate rather than repeat -- and still read as a stutter. Capping each consonant
    # at two occurrences catches what the sequence tests structurally cannot. Vowels are exempt:
    # Alaualora is fine, and vowel-rich names are the point of the liquid register.
    for ch in set(n):
        if ch not in _VOWELS and n.count(ch) > 2:
            return False
    vrun = 0
    for ch in n:
        vrun = vrun + 1 if ch in _VOWELS else 0
        if vrun >= 3:                      # Aeeinna and friends
            return False
    return sum(1 for ch in n if ch in _VOWELS) >= 2


def coin_name(seed, register):
    """Build one name deterministically from the register's phonotactics."""
    r = REGISTERS[register]
    s = _stream(seed)

    def pick(lst, avoid=None):
        # Never draw the morpheme just used: repetition is what made the ugly names ugly.
        opts = [x for x in lst if x != avoid] or lst
        return opts[next(s) % len(opts)]

    syllables = 2 + (next(s) % 2)
    parts = [pick(r["onset"])]
    last_mid = last_coda = None
    for _ in range(syllables - 1):
        last_mid = pick(r["mid"], last_mid)
        parts.append(last_mid)
        c = pick(r["coda"], last_coda)
        last_coda = c
        if c:
            parts.append(c)
    parts.append(pick(r["end"]))
    name = re.sub(r"(.)\1{2,}", r"\1\1", "".join(parts))
    return name[0].upper() + name[1:].lower()


def coin_well_formed(base, register, taken, max_tries=400):
    """First well-formed, unused name for this seed. Deterministic: same input, same output."""
    for salt in range(max_tries):
        nm = coin_name(f"{base}|{salt}", register)
        if well_formed(nm) and nm.lower() not in taken:
            return nm
    # THE FALLBACK USED TO ABANDON BOTH INVARIANTS AT ONCE. It was a bare
    # `return coin_name(f"{base}|fallback", register)` -- no `well_formed` check and, worse, no
    # `taken` check, so the one path taken when naming is HARDEST returned a name that could be
    # malformed AND could duplicate a name already issued. "Shelfmarks are unique" is one of the
    # 39 standards, and this was the single code path capable of breaking it silently. Filed by
    # the run #5 audit; open until 2026-08-24.
    #
    # Determinism is preserved -- same input, same output -- by continuing the SAME deterministic
    # walk into a wider salt space rather than inventing a different rule. Only the range grows.
    nm = coin_name(f"{base}|fallback", register)
    if well_formed(nm) and nm.lower() not in taken:
        return nm
    for salt in range(max_tries, max_tries * 25):
        nm = coin_name(f"{base}|{salt}", register)
        if well_formed(nm) and nm.lower() not in taken:
            return nm
    # Genuinely exhausted: 10,000 deterministic candidates and every one taken or malformed.
    # That is not a naming problem, it is a register that has run out of namespace, and it must
    # be LOUD rather than a quietly duplicated shelfmark. Recorded, then the caller still gets a
    # designation -- refusing to name anything would be the worse failure.
    silence.note("onomast.py:coin-exhausted")
    return coin_name(f"{base}|fallback", register)


# How a world's OWN character bends the register its source handed it.
#
# Influence runs both ways. A source supplies the register -- mythology sounds classical, grimdark
# sounds guttural -- but a world is not merely an instance of its genre. A frozen world and a
# tropical world in one setting are named by different people living different lives, and if the
# generator cannot tell them apart it is modelling the source and not the world.
#
# So genre sets the base phonology and the world's own features shift it. The shift is a nudge,
# not an override: a grimdark tropical world is still recognisably grimdark, just softer than its
# frozen neighbour. Two worlds of one shelf stay kin, and stop being twins.
FEATURE_SHIFT = {
    ("climate", "frozen"):       "guttural",   # hard consonants; cold-country names run short
    ("climate", "tropical"):     "liquid",     # vowel-rich, flowing
    ("climate", "oceanic"):      "liquid",
    ("climate", "volcanic"):     "guttural",
    ("climate", "arid"):         "sibilant",   # dry, hissing
    ("climate", "temperate"):    None,         # says nothing; casts no vote
    ("landform", "archipelago"): "long",       # scattered peoples, longer compound names
    ("landform", "isles"):       "liquid",
    ("landform", "shattered"):   "sibilant",
    ("landform", "highland"):    "compact",    # terse, defensible, monosyllabic
    ("landform", "pangaea"):     "long",
    ("landform", "continents"):  None,
    ("condition", "ruined"):     "guttural",
    ("condition", "wartorn"):    "compact",
    ("condition", "thriving"):   "classical",
    ("condition", "settled"):    None,
    ("tech", "spacefaring"):     "sibilant",
    ("tech", "primitive"):       "guttural",
    ("tech", "magical"):         "liquid",
    ("tech", "industrial"):      "compact",
    ("tech", "medieval"):        None,
}
# The balance that makes influence genuinely two-way. A first attempt weighted the source at 2 and
# each feature at 1, which meant a single feature could never outvote the genre and two rarely
# could -- every grimdark world came back guttural whatever its geography, so the world had no
# voice at all. At 3 against 2, ONE feature still cannot flip the register (the source is the more
# reliable signal) but TWO AGREEING FEATURES CAN. A tropical archipelago stops sounding like a
# frozen highland even when both are grimdark.
GENRE_WEIGHT = 3
FEATURE_WEIGHT = 2


def register_for(group_id, genre_register=None, features=None):
    """The naming register: what the source gives, bent by what the world is.

    Falls back to a hash of the group id ONLY when neither a genre nor features are known. That
    fallback used to be the whole function, and it produced the register that gave Alien and Doom
    the flowing elvish sound and denied Greek myth the classical one.
    """
    if not genre_register and not features:
        return REGISTER_ORDER[int(hashlib.sha256(str(group_id).encode()).hexdigest(), 16)
                              % len(REGISTER_ORDER)]

    votes = {}
    if genre_register in REGISTERS:
        votes[genre_register] = GENRE_WEIGHT
    for axis, value in (features or {}).items():
        shifted = FEATURE_SHIFT.get((axis, value))
        if shifted in REGISTERS:
            votes[shifted] = votes.get(shifted, 0) + FEATURE_WEIGHT
    if not votes:
        return genre_register if genre_register in REGISTERS else "classical"
    # Ties break toward the source, which is the more reliable signal of the two.
    best = max(votes.values())
    tied = sorted(k for k, v in votes.items() if v == best)
    return genre_register if genre_register in tied else tied[0]


def load_onomasticon():
    """The onomasticon as it currently stands on disk. Best-effort: a missing or unreadable file
    means nothing is standing yet, not that naming should refuse to proceed."""
    try:
        with open(OUT, encoding="utf-8") as f:
            return json.load(f) or {}
    except FileNotFoundError:
        return {}
    except Exception:
        silence.note("onomast.py:name_worlds-onomasticon-unreadable")
        return {}


def is_retired(rec):
    """A designation the Library has issued and withdrawn. It is never issued again."""
    return bool(isinstance(rec, dict) and rec.get("retired"))


def name_worlds(resolved):
    """Assign a distinct designation to every world bearing a carried name.

    A name is only replaced where the SAME name occurs in more than one continuity: a world called
    Earth in a shelf where nothing else is, needs no disambiguation and does not get renamed. The
    doctrine explains repetition; where there is no repetition there is nothing to explain.

    THE RETURN IS THE WHOLE ONOMASTICON, NOT JUST THIS RUN'S NAMINGS -- APPEND-ONLY. The `taken`
    seeding below exists to stop a withdrawn designation being handed to a different world while
    older prose still cites it, and it used to survive exactly ONE cycle, because both writers of
    ONOMASTICON.json (`main()` here and the weave phase in pipeline.py) write this function's
    return value and nothing else. A cid that left `resolved` was therefore dropped from the file,
    the NEXT run could not see it, and the name it was protecting became free again. Reproduced
    with three runs over a two-world shelf: run 1 named a=Torutharkok, b=Torathak; run 2 (world a
    gone) correctly held Torutharkok back; run 3 handed Torutharkok to b and Torathak to c. Every
    designation on the shelf shifted by one, and every citation written against run 1 now pointed
    at a different world. A safety that holds for one cycle and then forgets is worse than none,
    because it reads as protection. (Order 9309a040f208.)

    A carried-forward record is RETIRED only if its cid has left `resolved` entirely. One that is
    still in `resolved` but no longer collides is STANDING: its name is still in use, still
    reserved, and not withdrawn. See the comment on `merged` below (order e5001f0b0153).

    So prior records are carried forward here, flagged `retired` or not, and the memory becomes
    permanent rather than one-cycle. Both writers get it without either having to know, which is
    the point: the fix belongs where the invariant is, not in each caller. Retired records are
    emitted FIRST so that a consumer building a lookup from `.values()` (navtree, worldseed) sees
    the live record last and keeps it, and `is_retired()` is there for consumers that want to
    filter instead.
    """
    import collections
    by_key = collections.defaultdict(list)
    for cid, v in resolved.items():
        if is_carried(v["canonical_name"]):
            by_key[v["key"]].append((cid, v))

    # Which cids this call will actually issue a designation to. Computed BEFORE seeding, because
    # the seeding rule depends on it: a cid that is still in `resolved` but has fallen out of a
    # >=2 group is not renamed this run either, and its standing designation needs the same
    # protection as a cid that vanished entirely. The old rule ("skip cids in `resolved`") left
    # that second case unprotected, so a shelf shrinking from two worlds to one freed a name that
    # published prose was still citing.
    naming = {cid for items in by_key.values() if len(items) >= 2 for cid, _ in items}

    # `taken` must start seeded with designations ALREADY standing in the catalogue namespace,
    # not just the ones this call coins -- otherwise two runs (one now, one after `resolved`
    # has grown or shrunk between pipeline passes) can independently hand the same
    # catalogue_name to two different worlds, and nothing here would notice: this call fully
    # overwrites ONOMASTICON.json with only what it names THIS time, so a world dropped from
    # `resolved` this run keeps its old designation alive in already-published prose while its
    # name silently becomes free for a new, unrelated world to be coined into.
    #
    # ONOMASTICON.json's own top-level keys are cids, exactly like `resolved`'s -- so seeding is
    # restricted to cids this call is NOT about to name. Every cid in `naming` gets its
    # designation freshly recomputed below, so seeding those too would make coin_well_formed see
    # its own prior answer as taken and bump every unchanged world to a different name on every
    # rerun -- breaking the exact reproducibility this module's docstring promises.
    prior = load_onomasticon()
    taken = set()
    for cid, rec in prior.items():
        if cid in naming:
            continue
        nm = (rec or {}).get("catalogue_name") if isinstance(rec, dict) else None
        if nm:
            taken.add(nm.lower())

    out = {}
    for key, items in sorted(by_key.items()):
        if len(items) < 2:
            continue                                   # unique already; leave it alone
        for cid, v in sorted(items, key=lambda t: t[0]):
            reg = register_for(v["continuity_group"])
            nm = coin_well_formed(f"{key}|{v['continuity_group']}", reg, taken)
            taken.add(nm.lower())
            out[cid] = {
                "catalogue_name": nm,
                "endonym": v["canonical_name"],
                "register": reg,
                "continuity_group": v["continuity_group"],
                "attestations": v["attestations"],
                "note": (f"Its people call it {v['canonical_name']}, holding by tradition that "
                         f"their line began there. The Library records the endonym and shelves "
                         f"the world under its own designation, the name being carried rather "
                         f"than shared."),
            }

    # APPEND-ONLY. Carried-forward records first (so a live record wins any lookup a consumer
    # builds by iterating values), then this run's namings, which overwrite their own carried
    # copies if a world has come back -- and come back to the same designation, since the seed is
    # the world's own catalogue position and its cid is excluded from `taken` above.
    #
    # STANDING IS NOT RETIRED, AND THIS USED TO FLAG BOTH THE SAME WAY (order e5001f0b0153).
    # `out` holds only cids in `naming`, and `naming` is restricted to cids sitting in a
    # collision group of size >= 2 -- so a world that is STILL PRESENT in `resolved` but whose
    # shelf has shrunk to one, and therefore correctly needs no disambiguation this run, was
    # stamped `retired: True` beside worlds that have genuinely vanished. Reproduced offline:
    # two worlds both named Earth, then a run with the second removed and the first untouched
    # and still present -> the first came back `retired: True` and `is_retired()` answered True
    # for it. `is_retired`'s own docstring defines the flag as "issued and withdrawn", so any
    # consumer filtering on it dropped the designation of a world that still exists and fell
    # back to the bare endonym -- the exact ambiguity this module removes -- and main()'s
    # "designations retired, never reissued" over-reported withdrawals by every shrunken shelf.
    #
    # The two states are now separated by the only fact that distinguishes them: whether the cid
    # is still in `resolved`. Both are still carried forward and both still seed `taken` above
    # (the seeding rule reads `naming`, not this flag), so the reservation that order 9309a040f208
    # exists for is untouched -- a third run still cannot reissue a standing name to another world.
    merged = {cid: {**rec, "retired": cid not in resolved}
              for cid, rec in prior.items()
              if isinstance(rec, dict) and rec.get("catalogue_name") and cid not in out}
    merged.update(out)
    return merged


def main():
    with open(RESOLVED, encoding="utf-8") as f:
        resolved = json.load(f)
    named = name_worlds(resolved)
    # `named` is the WHOLE onomasticon, retired records included -- that is what makes it
    # append-only. The report counts the live ones, because a count that quietly included
    # withdrawn designations would be the same class of untruth as the one this fixes.
    live = {cid: v for cid, v in named.items() if not is_retired(v)}
    retired = {cid: v for cid, v in named.items() if is_retired(v)}

    import collections
    by_endonym = collections.defaultdict(list)
    for cid, v in live.items():
        by_endonym[v["endonym"]].append(v)

    print("=" * 92)
    print("THE ONOMASTICON — worlds that carry a name rather than share one")
    print("=" * 92)
    # The retired count is now only worlds that have left `resolved` (order e5001f0b0153); a
    # standing designation on a shelf that has shrunk to one world is counted as live, which is
    # what it is. The line used to include those and over-reported withdrawals accordingly.
    print(f"\nworlds holding their own designation: {len(live):,}")
    print(f"carried names resolved              : {len(by_endonym)}")
    print(f"designations retired, never reissued: {len(retired):,}  "
          f"(worlds gone from the resolution; a standing name is not one of these)")

    # SAY WHAT WAS CUT, THE WAY THE INNER LOOP ALREADY DOES (order 89fc2eaf23f1, Hard Rule 0).
    # This was `[:4]` with nothing announcing it, four lines above an inner list that prints its
    # own "... and N more" -- two disciplines in one function, and the silent one on the outer
    # list, which is the one that decides which carried names a reader learns exist at all.
    _endonyms = sorted(by_endonym, key=lambda k: -len(by_endonym[k]))
    for endo in _endonyms[:4]:
        rows = by_endonym[endo]
        print(f"\n  {endo} — {len(rows)} worlds, none of them each other:")
        for v in rows[:9]:
            src = v["attestations"][0]
            print(f"     {v['catalogue_name']:<16}{v['register']:<11}{src[:34]}")
        if len(rows) > 9:
            print(f"     ... and {len(rows)-9} more")
    if len(_endonyms) > 4:
        print(f"\n  ... and {len(_endonyms)-4} more carried name(s) not shown; "
              f"the whole set is in {OUT}")

    # ATOMIC: ONOMASTICON.json is shared. 2026-08-25 whole-tree sweep.
    if silence.write_json(OUT, named, indent=2, ensure_ascii=False):
        print(f"\nwrote {OUT}")
    else:
        print(f"\nWRITE DENIED {OUT} — replace refused; it lands on the next run")
    print("\nEvery designation is reproducible: reseeded from the world's own catalogue")
    print("position, so a Custos who reruns this gets these names and not others.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
