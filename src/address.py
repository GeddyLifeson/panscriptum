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

    # MOST SPECIFIC WINS, NOT FIRST-IN-FILE. This loop used to `return code` on the first index
    # entry whose worded form contained the target or was contained by it, so the winner was
    # decided by the order the Acquisitions Index happens to be written in rather than by the
    # weight of the evidence. The word-boundary fix above stopped "dc" matching inside
    # "swor-d-c-oast", but it did not stop the two-letter index entry "DC" (-> II.D.2) from
    # matching a genuine standalone word "DC" anywhere in a much longer title and returning
    # before the loop ever reached the correct, more specific entry sitting later in the same
    # dict:
    #     Sword Coast Adventurer's Guide DC Edition Reprint -> II.D.2   (DC Comics)
    # while "Sword Coast Adventurer's Guide" is itself an index entry mapped to II.L.7. A D&D
    # sourcebook shelved inside DC Comics' spine is the invented address Hard Rule 2 forbids,
    # and it does the same second harm the note above describes: a source that matches WRONG
    # never reaches `unassigned_sources.md`, so the owner sign-off that would have caught it is
    # never asked for.
    #
    # Since one side of a containment match IS the other's substring, the shorter of the two
    # worded strings is exactly the matched text, and its length is exactly how much evidence
    # the match rests on. Scoring every candidate by that and keeping the largest picks the
    # most specific entry; `>` rather than `>=` leaves ties resolving in index order, so a tie
    # behaves as it always did. (Verified against all 215 roll entries and all 220 index names
    # before and after: no assignment changed.)
    # AND A ONE-WORD MATCH IS NOT EVIDENCE HERE EITHER (order 3b030216a138). Order 7f9a58566f91
    # fixed exactly this hazard in the token-overlap FALLBACK below, and this branch runs FIRST
    # and had the same weakness: a single-token index entry matches as a whole word anywhere
    # inside an unrelated long title, and the fallback's guard is never reached. Demonstrated
    # live against the real index, both of them wrong:
    #
    #     'A Halo Around The Moon Documentary'            -> II.F.4   (Halo)
    #     'Some Unrelated Game About Doom Marines On Mars' -> II.N.2   (Doom)
    #
    # 51 of the 220 index entries are a single token -- 'Alien', 'Doom', 'Dune', 'Halo',
    # 'Diablo', 'DC' among them -- so this is a broad surface, and it does the same second harm
    # the notes above describe: a source that matches WRONG never reaches
    # `unassigned_sources.md`, so the owner sign-off that would have caught it is never asked
    # for. Hard Rule 2 says never invent an address; this was a path that did.
    #
    # THE RULE HAS TWO PARTS, AND THE DIRECTION OF THE CONTAINMENT IS THE FIRST OF THEM.
    #
    # When the TARGET sits inside the INDEX NAME, the index is naming it on purpose: the
    # appendix writes out its contents, e.g. 'Tom Clancy (all: Splinter Cell, Rainbow Six, Ghost
    # Recon, The Division, HAWX, EndWar)', and the roll entries 'HAWX' and 'EndWar' are real
    # single-token matches inside it. That direction is authoritative and is left untouched.
    #
    # When the INDEX NAME sits inside the TARGET, the index is not asserting anything about the
    # longer title -- the word simply occurs in it. So a single-token index entry counts only if
    # its token OPENS or CLOSES the title, which is where a work's name sits: 'Norse' closing
    # 'Pantheon: Norse' and 'Halo' opening 'Halo (all games)' are the roll and the index writing
    # the same work with a qualifier attached; 'Halo' in the middle of a sentence-shaped title is
    # a coincidence of vocabulary. Two-or-more-token containment is unchanged -- 'One Piece' in
    # 'One Piece (all arcs)' is real evidence, and the most-specific-wins scoring below already
    # sorts out competing entries.
    #
    # Nothing legitimate is lost by the rejection either: 'all Doom' against index 'Doom' fails
    # here (the word neither opens nor closes it, 'all' does) and is then matched by the token
    # fallback, whose equal-token-set arm exists for exactly that shape. Verified against all 215
    # roll entries and all 220 index names: no assignment changed, and the two titles above now
    # return UNASSIGNED, which is the safe answer this fallback exists to give.
    # PRECOMPUTED ONCE, for the opens/closes exception below to check the REST of the title
    # against, not just the matched token. (order 07258ace3a09)
    _worded_index = [(nm, _worded(nm)) for nm in codes]

    def _index_name_is_placed_like_a_title(w_name, w_target):
        """The index entry sits inside the target: is it there as the title, or as vocabulary?

        Opening or closing the title is only good evidence when nothing else CATALOGUED
        survives on that side of the match. `_index_name_is_placed_like_a_title` only ever
        checked the matched token's position, never what the rest of the title said -- so an
        invented crossover/anthology title that happens to open or close with one catalogued
        single-token name (e.g. "Alien Predator Doom Crossover", which opens with "Alien" and
        also contains "Doom") was shelved under that franchise at full confidence, instead of
        falling through to UNASSIGNED as a title naming more than one catalogued work should.
        Once the matched name is stripped off the matched end, if what remains still names
        ANOTHER catalogued work as a whole word, this is vocabulary for a crossover/anthology
        title, not evidence that the title belongs to the work that happened to sit first or
        last -- so the match is refused here and the caller falls through (to UNASSIGNED, or to
        the token-overlap fallback's stricter equal-token-set test).
        """
        if len(w_name.split()) > 1:
            return True
        if w_target.startswith(w_name.rstrip() + " "):
            remainder = " " + w_target[len(w_name):].strip() + " "
        elif w_target.endswith(" " + w_name.lstrip()):
            remainder = " " + w_target[:len(w_target) - len(w_name)].strip() + " "
        else:
            return False
        remainder_tokens = remainder.split()
        for other_name, w_other in _worded_index:
            if w_other == w_name or not w_other.strip():
                continue
            if w_other in remainder:
                return False
            # PLURAL-INSENSITIVE for a single-token other name. "Doom Marines vs Aliens
            # Anthology" opens with "Doom" and its remainder says "aliens", not "alien" -- the
            # exact-substring check above misses it on spelling alone, and a crossover title is
            # at least as likely to pluralise the other franchise's name as not. A trailing-`s`
            # strip on both sides catches that without touching anything shorter than four
            # letters, where stripping one letter off the end risks colliding with an unrelated
            # word (e.g. an index entry that really is "as" or "is").
            other_tokens = w_other.split()
            if len(other_tokens) == 1 and len(other_tokens[0]) > 3:
                stem = other_tokens[0].rstrip("s")
                if stem and any(tok.rstrip("s") == stem for tok in remainder_tokens):
                    return False
        return True

    w_target = _worded(source_name)
    if w_target.strip():
        best_code, best_evidence = None, 0
        for name, code in codes.items():
            w_name = _worded(name)
            if w_name in w_target and not _index_name_is_placed_like_a_title(w_name, w_target):
                continue
            if w_target in w_name or w_name in w_target:
                evidence = min(len(w_target), len(w_name))
                if evidence > best_evidence:
                    best_code, best_evidence = code, evidence
        if best_code is not None:
            return best_code

    # word-order-independent fallback (handles "all Black Ops" vs "Black Ops (all)")
    #
    # NORMALISING BY min() MAKES A ONE-WORD INDEX ENTRY MATCH ANYTHING THAT SAYS THAT WORD. The
    # denominator is the SHORTER side, so an index name of a single token needs exactly one shared
    # token to score coverage 1.0 -- and 125 of the 220 Acquisitions-Index entries are two tokens
    # or fewer, among them 'Alien', 'Doom', 'Dune', 'Halo', 'Diablo' and 'DC'. Any future source
    # whose title happens to contain one of those words as a standalone word would be shelved
    # inside it, at full confidence, without ever reaching UNASSIGNED:
    #
    #     'Sword Coast Adventurer's Guide DC Edition' vs 'DC'
    #       overlap 1, min(5, 1) = 1, coverage 1.0  ->  II.D.2, DC Comics
    #
    # That is the invented address Hard Rule 2 forbids, arriving by the same route the two fixes
    # above closed (raw-letter containment, then first-in-file order) and surviving both of them,
    # because this branch never asks how much of the LONGER name agreed. It does the second harm
    # too: a source that matches wrongly never reaches unassigned_sources.md, so the owner
    # sign-off that would have caught it is never asked for. Latent, not live -- all 16 sources on
    # today's roll that reach this branch were verified genuine before and after. (Order
    # 7f9a58566f91.)
    #
    # THE FIX IS ON THE EVIDENCE, NOT THE THRESHOLD. One shared word is not evidence of identity;
    # it is evidence of one shared word. So a single overlapping token only counts when the two
    # token sets are the SAME set -- which is the one case where nothing was left over on either
    # side to disagree about ('all Battlefield' vs 'Battlefield (all)', both {battlefield}, three
    # of today's sixteen). Anything else needs at least two words in common before its coverage is
    # worth reading. Raising the 0.8 threshold instead would not have helped: coverage was already
    # 1.0, the maximum, on exactly the matches that are wrong.
    #
    # Rejected: normalising by max() instead. It breaks two genuine matches on today's roll --
    # 'the Skate games' (2 of 6 tokens) and 'Western astrology' (2 of 7) -- because an index entry
    # that spells out its contents in parentheses is legitimately much longer than the roll's name
    # for the same thing. Verified against all 215 roll entries: no assignment changed.
    target_tokens = _token_set(source_name)
    if target_tokens:
        best, best_overlap = None, 0
        for name, code in codes.items():
            name_tokens = _token_set(name)
            if not name_tokens:
                continue
            overlap = len(target_tokens & name_tokens)
            if overlap < 2 and target_tokens != name_tokens:
                continue
            coverage = overlap / min(len(target_tokens), len(name_tokens))
            if coverage >= 0.8 and overlap > best_overlap:
                best, best_overlap = code, overlap
        if best:
            return best

    return "UNASSIGNED"


def slugify(name: str) -> str:
    """Mint a slug from a label. NOT TRUNCATED -- see below.

    THE [:60] IS GONE (order 5d317e3e47f0). This function used to end `[:60]`, the same cap on
    the same kind of value that `catalogue_web.py:68-95` spends thirty lines documenting: its
    own slug function's trailing [:60] wrote a record under a 79-character slug's first sixty
    characters and produced "a roll row that is not missing, a record that is not orphaned, and
    no path between them". This is the ADDRESSING module and slugify's output is used as a
    path/label component, so it is the last place a silent truncation belongs -- a cap here does
    not fail, it mints a DIFFERENT identity that looks like the right one.

    LATENT WHEN REMOVED, and verified so rather than assumed: slugify has exactly two call sites
    -- `chapter_slug()`'s fallback for a label not in CHAPTER_SLUGS, and manifest_builder.py:247
    on `roll_entry['category']` -- and all 17 distinct category values on the live roll slugify
    to between 5 and 29 characters, while every CHAPTER_SLUGS key is mapped explicitly so the
    fallback never sees the long chapter labels. Removing the cap changed no current output.

    If a bound is ever genuinely wanted for a filesystem it belongs at the point a PATH is
    built, with the full value kept in the data -- not inside the function that mints the
    identity.
    """
    cleaned = re.sub(r"[^\w\s-]", "", name)
    parts = re.split(r"[\s_-]+", cleaned.strip())
    parts = [p for p in parts if p]
    while parts and parts[0].lower() in ("all", "the", "a"):
        parts = parts[1:]
    if not parts:
        parts = ["Untitled"]
    return "".join(p[:1].upper() + p[1:] for p in parts)


CHAPTER_SLUGS = {
    "Persons (named individual characters, real or fictional)": "Persons",
    "Factions & Organizations (groups, nations, guilds, companies, orders)": "Factions",
    "Places & Locations (worlds, regions, cities, planes, ships-as-places)": "Places",
    "Vessels & Things (items, vehicles, weapons, artifacts, notable objects)": "VesselsAndThings",
    "Events (major storyline events, wars, historical turning points within the fiction)": "Events",
    "Media (in-fiction media: books, songs, broadcasts, works that exist within the story itself)": "Media",
    "Powers, Abilities & Systems (magic systems, power systems, tech systems, disciplines)": "Powers",
    "Mechanical/Named Content": "MechanicalContent",
    "Feats & Attested Deeds (quoted feats mined from the source's own pages)": "Feats",
}

POWERS_LABEL = ("Powers, Abilities & Systems "
                "(magic systems, power systems, tech systems, disciplines)")
MECHANICAL_LABEL = "Mechanical/Named Content"
FEATS_LABEL = "Feats & Attested Deeds (quoted feats mined from the source's own pages)"

# A source whose MODE is this writes game mechanics, not cosmology. `mode` is already recorded
# per source on the roll and per record in the corpus, so this is a reading of existing data
# rather than a new classification.
MECHANICAL_MODES = {"folder-mechanical"}


def chapter_label_for(category_label: str, mode: str | None = None) -> str:
    """Which chapter an entry's category belongs to, given the SOURCE it came from.

    THE PROBLEM THIS SOLVES. The entrypass classifier can emit seven categories, and
    `Powers, Abilities & Systems` is the only bucket offered for an ability. So a 3rd-level
    evocation from a homebrew PDF and Ichigo's Bankai land in the same chapter. Measured on the
    corpus: **65.9% of all `Powers` entries come from `folder-mechanical` sources** -- spells and
    subclass features -- against 32.8% narrative. An encyclopedia of powers built on the raw
    category would be two-thirds D&D spell lists wearing the same cover as Haki.

    `CHAPTER_SLUGS` has carried a `Mechanical/Named Content` slug since the charter, with NO
    producer: nothing has ever assigned that label, because it is not one of the seven the
    classifier can emit. This is its producer, and it needs no per-entry reclassification --
    the source's own `mode` already says which kind of book it is. Measured: 98.7% of Powers
    entries route cleanly, `folder-mechanical` one way and `web` the other.

    The remaining 1.2% are `hybrid` sources (87 entries, 6 sources), which genuinely mix the two
    and cannot be routed wholesale. They stay under `Powers` and are flagged as an owner
    question rather than guessed at -- see NEXT_STEPS.
    """
    if category_label == POWERS_LABEL and mode in MECHANICAL_MODES:
        return MECHANICAL_LABEL
    return category_label


def chapter_slug(category_label: str) -> str:
    return CHAPTER_SLUGS.get(category_label, slugify(category_label))


def build_address(source_name: str, chapter_label: str, page_range: str | None = None) -> str:
    """
    The address used for generated chapter files: <SpineCode>/<Chapter>[#PageRange]
    e.g. II.A.3/Persons#1-30  (One Piece, Persons chapter, entries 1-30)

    `page_range` and `chapter_label_for`'s `mode` are spelled `str | None` rather than the bare
    `str` they carried before: both default to None and both are called with None in the tree, so
    the bare annotation stated a contract the callers do not keep. PEP 484 removed the implicit
    Optional, and an annotation that lies is worse than none at all. Defaults and behaviour are
    untouched -- this is the type talking, not the code.
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


# ---------------------------------------------------------------- the promotion ladder
#
# OWNER AMENDMENT, 2026-08-24: "each classification should have a standard that over x entries
# it increases in overall classification hierarchy." A source's shelf rank is a function of how
# much of it there actually is, rather than a judgement made once when it joined the roll and
# never revisited.
#
# The thresholds were chosen against the real corpus, not invented: 209 sources carry entries,
# median 194, mean 410, max 30,207 (Marvel). This ladder yields 163 Volumes, 37 Series, 8 Grand
# Series/Wings and 1 Set -- and that one Set is Marvel, which the charter had already promoted
# to a Set with two Wings by hand. A rule whose only automatic Set is the one a human already
# made is a rule that agrees with the librarian.
#
# Deliberately conservative. Lowering Set to 1,000 would mint six Sets at a stroke (Black Ops,
# KibblesTasty, Unearthed Arcana, Battlefield, Gears of War alongside Marvel), which is a
# structural change to Collection II rather than a shelving correction.
TIER_FLOORS = (("volume", 0), ("series", 400), ("grand", 900), ("set", 3000))


def tier_for(entry_count):
    """Which rung a cast of this size earns. Pure function of the count."""
    rank = "volume"
    for name, floor in TIER_FLOORS:
        if (entry_count or 0) >= floor:
            rank = name
    return rank


def tier_rank(tier):
    """Ordinal position of a tier, so two tiers can be compared."""
    order = [n for n, _ in TIER_FLOORS]
    return order.index(tier) if tier in order else 0


def promote(current, entry_count):
    """The tier a source should now hold, given what it holds today.

    PROMOTION ONLY, NEVER DEMOTION -- and that asymmetry is the whole safety of running this
    automatically. A cast count is a measurement, and this project's measurements have gone
    briefly to zero more than once (COMPLETENESS.json emptied itself twice; a fandom block makes
    every roster look small for an afternoon). Demoting on a dip would rewrite a source's address
    downward on bad data, and every cross-reference already pointing at the old code would break
    for a reason nobody could see. Growing is real; shrinking is usually a broken read.

    Returns the tier to use. `current` may be None for a source not yet ranked."""
    earned = tier_for(entry_count)
    if not current:
        return earned
    return earned if tier_rank(earned) > tier_rank(current) else current


if __name__ == "__main__":
    for n in (0, 194, 399, 400, 899, 900, 2999, 3000, 30207):
        print("%6d entries -> %s" % (n, tier_for(n)))
    print("demotion refused:", promote("set", 12))
    for name in ["One Piece", "Marvel", "DC", "all Black Ops", "Some Brand New Unlisted Thing"]:
        print(f"{name!r:45s} -> {spine_code_for(name)}")
    print(build_address("One Piece", "Persons (named individual characters, real or fictional)"))
