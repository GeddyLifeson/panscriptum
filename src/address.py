"""
Addressing for the Panscriptum, aligned to the REAL system defined in
reference/keystone_volumes/00_MASTER_CHARTER.md (Parts One, Two, Six, Seven, and the
Acquisitions Index appendix). Do not reinvent this scheme -- the charter already specifies it
in detail; this module just implements it in code.

Two distinct addresses matter here, and they are NOT the same thing:

1. The SPINE CODE (`Collection.Set.Series[.Volume]`, e.g. `II.A.3`) -- where a source's home
   volume sits on the physical shelf. This comes straight from the charter's own Acquisitions
   Index (data/CHARTER_SPINE_CODES.json, parsed from the appendix table). This is the address
   used for the generated book files and the manifest.

2. The SHELFMARK (`Ω › H? › X? › Mt.ASC › Mv.DRG › U-7 › G.North › P.Earth`, per Part Two's
   17-rung Ladder of Being) -- where an individual ENTITY sits in the omniverse itself. This
   requires classifying each entity's home universe/galaxy/planet against the Ladder, which
   the research pass hasn't done yet (that's a distinct, deeper cataloguing task, not something
   to fake here). We emit an honest placeholder (`Ω › ? › ? › ... › [Source Name]`) using the
   charter's own `?` convention for "uncharted rung" -- never guess a real one.
"""
import hashlib
import json
import os
import re

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_SPINE_CODES = None


def _load_spine_codes():
    global _SPINE_CODES
    if _SPINE_CODES is None:
        path = os.path.join(HERE, "data", "CHARTER_SPINE_CODES.json")
        with open(path, encoding="utf-8") as f:
            _SPINE_CODES = json.load(f)
    return _SPINE_CODES


_FILLER = {"all", "the", "a", "and", "1", "2", "3", "&", "-", "incl", "its", "associated"}


def _normalize(name: str) -> str:
    return re.sub(r"[^a-z0-9]", "", name.lower())


def _token_set(name: str):
    words = re.findall(r"[a-z0-9]+", name.lower())
    return frozenset(w for w in words if w not in _FILLER and len(w) > 1)


def spine_code_for(source_name: str) -> str:
    """
    Look up the source's real home spine code from the charter's Acquisitions Index.
    Falls back to a flagged placeholder (never a guessed real code) if the source isn't in
    the appendix yet -- this happens for sources added to the Acquisitions Roll AFTER the
    charter's appendix was last updated. Surface these to the owner for a real assignment
    rather than silently inventing one; Collection/Set letters are not arbitrary, they're
    thematically grouped (see Part One and Catalog B).
    """
    codes = _load_spine_codes()
    if source_name in codes:
        return codes[source_name]

    # CONTAINMENT ON WHOLE WORDS, NOT ON RAW LETTERS. `_normalize` strips spaces, so the old
    # test asked whether one name's letters appeared anywhere inside the other's -- and the
    # Acquisitions Index contains the two-letter entry "DC" (-> II.D.2). "dc" falls inside
    # "swor-d-c-oast..." and "associate-d-c-rossover...", so BOTH of these came back as DC
    # Comics:
    #     Sword Coast Adventurer's Guide            -> II.D.2
    #     Who Framed Roger Rabbit (...crossover...) -> II.D.2
    # A D&D sourcebook and a Disney film, shelved inside DC Comics' spine. That is the invented
    # address Hard Rule 2 forbids, and it does a second harm on the way: a source that matches
    # WRONG never reaches `unassigned_sources.md`, so the owner sign-off that would have caught
    # it never gets asked for. A miss is cheap here and a false hit is not -- the whole point of
    # the UNASSIGNED fallback is that it is the safe answer.
    #
    # Padding with spaces makes the boundary explicit: "one piece" still matches "one piece all
    # arcs", while "dc" now matches only a genuine "dc" word. (Found by the generation-side
    # audit, 2026-08-23; verified against all 215 roll entries before and after.)
    # Letter-level EQUALITY first, though: the index writes "Soulcalibur" and the roll writes
    # "Soul Calibur", and a spacing variant is the same title by any honest reading. Equality
    # cannot false-match the way containment can, so it is safe to keep at full letter level --
    # dropping it was the one real regression the word-boundary fix introduced, caught by
    # diffing all 215 roll assignments before and after.
    norm_target = _normalize(source_name)
    if norm_target:
        for name, code in codes.items():
            if _normalize(name) == norm_target:
                return code

    def _worded(n):
        return " " + " ".join(re.findall(r"[a-z0-9]+", n.lower())) + " "

    w_target = _worded(source_name)
    if w_target.strip():
        for name, code in codes.items():
            w_name = _worded(name)
            if w_target in w_name or w_name in w_target:
                return code

    # word-order-independent fallback (handles "all Black Ops" vs "Black Ops (all)")
    target_tokens = _token_set(source_name)
    if target_tokens:
        best, best_overlap = None, 0
        for name, code in codes.items():
            name_tokens = _token_set(name)
            if not name_tokens:
                continue
            overlap = len(target_tokens & name_tokens)
            coverage = overlap / min(len(target_tokens), len(name_tokens))
            if coverage >= 0.8 and overlap > best_overlap:
                best, best_overlap = code, overlap
        if best:
            return best

    return "UNASSIGNED"


def slugify(name: str) -> str:
    cleaned = re.sub(r"[^\w\s-]", "", name)
    parts = re.split(r"[\s_-]+", cleaned.strip())
    parts = [p for p in parts if p]
    while parts and parts[0].lower() in ("all", "the", "a"):
        parts = parts[1:]
    if not parts:
        parts = ["Untitled"]
    return "".join(p[:1].upper() + p[1:] for p in parts)[:60]


CHAPTER_SLUGS = {
    "Persons (named individual characters, real or fictional)": "Persons",
    "Factions & Organizations (groups, nations, guilds, companies, orders)": "Factions",
    "Places & Locations (worlds, regions, cities, planes, ships-as-places)": "Places",
    "Vessels & Things (items, vehicles, weapons, artifacts, notable objects)": "VesselsAndThings",
    "Events (major storyline events, wars, historical turning points within the fiction)": "Events",
    "Media (in-fiction media: books, songs, broadcasts, works that exist within the story itself)": "Media",
    "Powers, Abilities & Systems (magic systems, power systems, tech systems, disciplines)": "Powers",
    "Mechanical/Named Content": "MechanicalContent",
}


def chapter_slug(category_label: str) -> str:
    return CHAPTER_SLUGS.get(category_label, slugify(category_label))


def build_address(source_name: str, chapter_label: str, page_range: str = None) -> str:
    """
    The address used for generated chapter files: <SpineCode>/<Chapter>[#PageRange]
    e.g. II.A.3/Persons#1-30  (One Piece, Persons chapter, entries 1-30)
    """
    spine = spine_code_for(source_name)
    volume = chapter_slug(chapter_label)
    addr = f"{spine}/{volume}"
    if page_range:
        addr += f"#{page_range}"
    return addr


def placeholder_shelfmark(source_name: str) -> str:
    """
    Honest 'uncharted' shelfmark per the charter's own notation (Part Two / Part Seven: '?'
    for uncharted rungs, never guessed). Real shelfmarks require Ladder-of-Being research
    per entity -- flag this as future work rather than fabricating one.
    """
    return f"Ω › ? › ? › ? › ? › ? › ? › {source_name} [UNCHARTED -- Ladder-of-Being pass not yet done]"


def babel_coordinate(content_obj) -> str:
    """Cosmetic base36 hash of canonical content -- flavor only, not load-bearing."""
    blob = json.dumps(content_obj, sort_keys=True, default=str).encode("utf-8")
    digest = hashlib.sha256(blob).hexdigest()
    n = int(digest[:20], 16)
    if n == 0:
        return "0"
    digits = "0123456789abcdefghijklmnopqrstuvwxyz"
    out = []
    while n:
        n, r = divmod(n, 36)
        out.append(digits[r])
    return "".join(reversed(out))


def recipe_hash(address: str, model: str, seed, prompt_version: str, content_hash: str = "") -> str:
    """
    The cache key that decides whether generate.py can skip a job as "already done."

    `content_hash` MUST be a hash of the actual source-data content (the entries/facts a job
    was built from), not just the address -- otherwise refreshing data/ with corrected or
    newly-completed research (e.g. a source that went from a partial re-sweep to a full one)
    silently fails to invalidate the cache, and generate.py skips regenerating it, leaving a
    book built on stale facts with no warning. manifest_builder.py computes this per job.
    """
    key = f"{address}|{model}|{seed}|{prompt_version}|{content_hash}"
    return hashlib.sha256(key.encode("utf-8")).hexdigest()[:24]


if __name__ == "__main__":
    for name in ["One Piece", "Marvel", "DC", "all Black Ops", "Some Brand New Unlisted Thing"]:
        print(f"{name!r:45s} -> {spine_code_for(name)}")
    print(build_address("One Piece", "Persons (named individual characters, real or fictional)"))
