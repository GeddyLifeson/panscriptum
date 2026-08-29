#!/usr/bin/env python3
"""
MAGNITUDE — Charter Part Three's Custodial Assay, run against mined source text.

Phase 2 tried to band 52,343 entities from their catalogue descriptions and returned 99.6%
`unassayed`. That was the evidence gate behaving correctly on 170-character biographies. This
pass gives the same gate something to work with: `feats.py` mines the entity's own source wiki,
and the model scores the axes from those feats alone.

WHY THIS FILE IS MOSTLY GUARDS
------------------------------
The first unguarded run of this worksheet is the reason for everything below. Given thirteen
mined feats and eleven axes, the model returned:

    all eleven axes scored 9.9
    Celerity justified by "causes worldwide earthquakes"          (that is Ruin)
    Reach justified by "3,000 kili - power to destroy planets"    (that is Ruin)
    Continuity justified by "Goku summoned Zeno, who erased the rogue Kai"

That last line is not Goku's feat. It is Zeno's, and the sheet filed it under Goku. `assay.py`
then did its job perfectly and computed 'A M4.99 +/- 0.20' at coverage 1.0 -- a maximally
confident reading of a fabricated sheet. The arithmetic is not what failed; nothing downstream
of a bad worksheet can detect a bad worksheet.

So the model is treated as a proposer and never as an authority. Five checks stand between it
and `assay()`, and an axis that fails any of them does not get a number:

  1. VERBATIM      the cited feat must appear in the mined list. Invented citations are the
                   easiest failure to catch and the most damaging to miss.
  2. RELEVANCE     the feat must bear on the axis it was filed under. An earthquake sentence
                   cited for Celerity fails, and Celerity drops to `unestimable`.
  3. SUBJECT       the entity must be the DOER, and the check is made AGAINST THE ENTITY'S
                   NAME. Where the sentence names an agent -- after "by", after a handoff verb,
                   or leading the clause the axis evidence sits in -- that agent is compared to
                   the entity and the score stands or falls on the answer. Where the sentence
                   names no agent at all ("He destroyed the moon"), the guard cannot decide and
                   says so; those pass on provenance alone. Until 2026-08-26 this guard read
                   only the SENTENCE and never the entity, so it could not tell a doer from a
                   bystander in either direction -- see the note above `subject_refusal`.
  4. SATURATION    a sheet whose scored axes all sit at the top is a sheet from a model that
                   would not refuse. It is rejected whole, not averaged down.
  5. QUANTITY      "40 tons", "3,000 kili" never reach the model's judgement at all. A measured
                   quantity is converted and scored arithmetically by assay.axis_score against
                   BAND_EDGES, which is the highest-grade evidence the library can hold.

An axis that survives all five carries a number. Everything else carries a status, and the
interval widens accordingly. That is the intended outcome, not a shortfall: Part Three refines
the band "where evidence permits" and prints the band alone where it does not.
"""
import argparse
import json
import os
import re
import sys
import time

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import pipeline as P                                                    # noqa: E402
import feats as F                                                       # noqa: E402
import assay as A                                                       # noqa: E402
import scope as SCOPE                                                   # noqa: E402
import identity as ID                                                   # noqa: E402
import silence

# A regex escape arriving as a literal control character matches nothing and fails SILENTLY.
# A word-boundary escape written through a shell heredoc has arrived here as a 0x08 backspace
# five separate times in this project. Each time it read as a tuning problem -- a gate that
# passed nothing, a parser that found zero rows -- rather than as corruption, which is what
# makes it expensive. The check is built from chr() codes because the first version was
# written with escapes and they were eaten too, so it flagged its own source and refused.
_BAD_CHARS = (chr(8), chr(11), chr(12), chr(7))
if any(c in open(os.path.abspath(__file__), encoding='utf-8').read() for c in _BAD_CHARS):
    raise SystemExit(__file__ + ': a regex escape was eaten in transit - a literal control '
                     'character is present in the source. Repair before running.')


OUT = os.path.join(HERE, "data", "ASSAYS.json")
AXES = list(A.WEIGHTS)                       # 11: eight physical, three faculty

# ------------------------------------------------------------------------------- transport
#
# THE ASSAY HAD NO POOL, AND THAT IS WHY THE LIBRARY HAS 49 ASSAYS OUT OF 21,663 ENTITIES.
#
# Every other reading stage here -- read.py, chain.py -- tries `cascade_bridge` first and falls
# back to the local model. This module called `P.ask(config(), ...)`, which is local Ollama and
# nothing else: one 6,144-token context, one 420-second timeout, one entity at a time.
#
# The second half of the defect is worse than the slowness. An entity's prompt is built from
# EVERY candidate sentence its pages yielded -- deliberately uncapped, because "capping at six
# decided that an entity with forty pieces of Ruin evidence had six". So prompt size scales with
# how well-documented an entity is, and measured against the local window:
#
#     Goten     4,825 chars   0.2x   fits          -> assayable
#     Krillin  13,453 chars   0.5x   fits          -> assayable
#     Gohan    28,242 chars   1.1x   over          -> "unassayed"
#     Frieza   46,382 chars   1.9x   over
#     Vegeta   49,761 chars   2.0x   over          -> "unassayed"
#     Goku     58,099 chars   2.4x   over          -> "unassayed"
#
# The instrument could only measure entities it barely knew, and it reported everything else as
# "unassayed" -- the identical word it uses for entities nobody has looked at yet. A failure that
# is indistinguishable from a queue.
#
# Cloud buckets carry 128k-token contexts, so the full prompt fits there with room to spare and
# the whole record is read. When the pool declines a call, an entity whose evidence exceeds the
# local window is DEFERRED rather than trimmed to fit -- see the Hard Rule 0 note in
# assay_entity(). Nothing here ever assays a partial record and calls it a Magnitude.

# The largest prompt the local model can actually read, in characters. NOT a budget to trim
# evidence down to -- Hard Rule 0 forbids that -- but a threshold for deciding whether the local
# model can take this entity AT ALL. Over it, the entity waits for the pool.
LOCAL_FITS = 20000

# Index pages that the character sweep catalogued as though they were people. Only 43 of 14,927,
# but they are the LONGEST pages on their wikis, and the queue runs richest-evidence-first -- so
# unfiltered they are the first dozen things the instrument would ever assay, and it would
# publish a Magnitude for "List of tertiary characters".
NOT_AN_ENTITY = re.compile(
    r"^(list of|category:|template:|index of|timeline of|glossary|gallery\b)|"
    r"\(disambiguation\)$", re.I)
_POOL = [None]                # resolved once, before any worker starts


def pool_ready():
    """Is the cloud pool reachable? Resolved ONCE and cached.

    read.py learned this the expensive way: ten workers racing the same probe drove the answer
    to False permanently, and every transport fix afterwards landed on a flag that was already
    wrong. Resolve before the pool starts, then never again.
    """
    if _POOL[0] is None:
        try:
            import cascade_bridge as CB
            _POOL[0] = bool(CB.engine())
        except Exception:
            silence.note("magnitude.py:pool_ready")
            _POOL[0] = False
    return _POOL[0]


def _ask(c, system, prompt, schema, timeout=420):
    """Cascade first, local second -- the same order read.py and chain.py already use."""
    if pool_ready():
        try:
            import cascade_bridge as CB
            got = CB.ask(system, prompt, schema)
            if got is not None:
                return got
        except Exception:
            silence.note("magnitude.py:_ask-cascade")
    try:
        # Sized, not defaulted: a split slice is ~8k chars and fits 4096 tokens with room; the
        # config default of 6144 was both too big for slices (wasted KV on a shared card) and
        # too small for anything larger (Ollama truncates the tail silently, no error).
        nc = 4096 if len(prompt) + len(system) < 11000 else 8192
        return P.ask(c, system, prompt, schema, timeout=timeout, num_ctx=nc, tag="assay-split")
    except Exception:
        silence.note("magnitude.py:_ask-local")
        return None

# --------------------------------------------------------------------------- guard 2: relevance
#
# What a feat has to be ABOUT to license a score on each axis. These are deliberately narrow.
# A feat that could be read onto any axis is evidence for none of them, and the cost asymmetry
# is the same one that governs the scale-note gate: a false negative prints an honest
# `unestimable`, a false positive mints a decimal nobody earned.
AXIS_LEXICON = {
    "ruin": r"destroy|destruct|obliterat|shatter|vaporiz|level(?:ed|s|led)?\b|raze|"
            r"blow (?:up|apart)|annihilat|explos|damage|wreck|demolish|kill|slew|slay|"
            r"tons?|megatons?|kilotons?|joules?|yield",
    "continuity": r"surviv|withstood|withstand|regenerat|heal|endur|resurrect|revive|"
                  r"unkillable|immortal|tank(?:ed)?|shrug|unharmed|no[- ]sell|durab",
    "celerity": r"speed|fast|swift|blitz|react|reflex|instant|light[- ]speed|mach|"
                r"faster than|dodge|evad|tempo|quick",
    "reach": r"range|reach|distance|kilomet|light[- ]year|across the|from orbit|"
             r"planet[- ]wide|galaxy[- ]wide|met(?:er|re)s? away|miles? away|spann",
    "transgression": r"time|erase|rewrite|reality|concept|soul|fate|law of|causal|acausal|"
                     r"dimension|negat|bypass|ignore|immun|nullif|probability|existence|"
                     r"resurrect|curse|seal",
    "sustain": r"indefinit|sustain|prolonged|for (?:hours|days|years)|stamina|"
               r"without tiring|endless|unlimited energy|maintain",
    "vector": r"teleport|travel|fly|flight|traverse|cross(?:ed|es)? (?:the|space)|"
              r"dimension(?:al)? travel|warp|portal|instant transmission|mobility",
    "volition": r"master|skill|technique|tactic|strateg|outwit|trained|discipline|"
                r"combat experience|prodigy|genius fighter|adapt",
    "acumen": r"predict|calculat|deduc|plan|analyz|analys|strateg|intellect|genius|"
              r"solved|invented|engineer|forese",
    "discernment": r"perceiv|sense|detect|insight|see through|aware|observ|read (?:the|his|her)|"
                   r"identif|recogniz",
    "suasion": r"persuad|convinc|inspir|rally|command|lead|negotiat|diplomat|"
               r"reputation|swayed|follower|charisma",
}
AXIS_RE = {k: re.compile(v, re.I) for k, v in AXIS_LEXICON.items()}

# --------------------------------------------------------------------------- guard 3: subject
#
# "Goku used the button to summon Future Zeno, who immediately proceeded to erase the rogue Kai."
# The entity appears in the sentence, and the sentence describes an erasure, and the erasure is
# not the entity's. A relative clause after another proper noun is where the deed changes hands.
_HANDOFF = re.compile(
    r"\b(?:summon(?:ed|s)?|call(?:ed|s)? (?:in|upon|forth)|order(?:ed|s)?|"
    r"command(?:ed|s)?|had|let|allow(?:ed|s)?|ask(?:ed|s)?)\b.{0,60}?"
    r"\b[A-Z][a-z]+\b.{0,20}?\b(?:who|which|then)\b", re.S)

# THE GUARD USED TO BE THE TWO PATTERNS ABOVE AND NOTHING ELSE, AND THAT IS THE WHOLE DEFECT
# (order 1dbec361641b). `verify(entity, got, ev)` never read `entity` -- AST-verified, zero
# occurrences in the body -- so a check whose stated claim is "the entity must be the DOER"
# was deciding on the SENTENCE alone. Both operands are entity-agnostic: `pipeline._PATIENT`
# is a generic passive-voice pattern and `_HANDOFF` needs only *some* capitalised word before
# a relative clause. The consequences run in both directions and neither is small:
#
#   MISSED  "Beerus erased the universe with a flick" is a clean pass for a sheet filed under
#           GOKU. No passive, no handoff -- a bystander's deed, credited, which is the exact
#           failure the module docstring opens with.
#   FALSE   "the planets destroyed by Goku" is refused ON GOKU'S OWN SHEET, because
#           `<past act> by <agent>` matches `_PATIENT` no matter who the agent is. The doer
#           named in the sentence was thrown away for being named.
#
# What follows tests the claim the guard makes, using the two things the function is actually
# handed: the entity's name and the sentence. It resolves the cases where the sentence NAMES
# an agent, and it says so when it cannot resolve one.
#
# WHAT IT STILL CANNOT DECIDE, stated here rather than papered over: a sentence whose subject
# is a bare pronoun ("He destroyed the moon") or elided entirely ("Destroyed a planet in one
# blow") carries no agent to test. Pronoun resolution needs the paragraph, and `verify` is
# given one sentence. Those pass this guard on the strength of provenance alone -- the feat was
# mined from the entity's own page -- and that is a weaker warrant than the docstring's wording
# suggests. It is left OPEN and named rather than closed with a test that would only look like
# one. Guards 1 and 2 still apply to them.

# Capitalised words that are not somebody's name. A sentence's first word is capitalised for
# grammar, and the mined corpus is full of "The", "During", "After" -- treating those as rival
# actors would refuse honest evidence wholesale.
_NAME_STOP = {
    "the", "a", "an", "this", "that", "these", "those", "his", "her", "its", "their", "our",
    "and", "but", "for", "nor", "yet", "so", "as", "at", "by", "in", "on", "of", "to", "from",
    "with", "without", "into", "onto", "upon", "over", "under", "after", "before", "during",
    "while", "when", "where", "which", "who", "whom", "whose", "what", "why", "how", "if",
    "he", "she", "it", "they", "him", "them", "one", "two", "three", "both", "all", "each",
    "every", "any", "some", "no", "not", "however", "although", "though", "because", "since",
    "unlike", "like", "despite", "due", "later", "then", "once", "twice", "afterwards",
    "eventually", "finally", "originally", "initially", "meanwhile", "instead", "thus",
    "therefore", "moreover", "furthermore", "additionally", "unfortunately", "fortunately",
    "according", "following", "prior", "shortly", "soon", "even", "only", "just", "also",
    "despite", "throughout", "within", "against", "among", "between", "beyond", "behind",
    "hers", "theirs", "himself", "herself", "itself", "themselves",
    # Modals and bare auxiliaries open a great many mined lines ("Can identify, engage, and
    # neutralise enemies") and are not anybody's name.
    "can", "could", "will", "would", "may", "might", "must", "shall", "should", "cannot",
    "sometime", "sometimes", "eventually", "presumably", "such", "subsequently",
    "similarly", "consequently", "nevertheless", "nonetheless", "regardless", "notably",
    "afterward", "formerly", "previously", "currently", "occasionally", "generally",
    # Chapter/section furniture and units that capitalise mid-sentence in wiki prose.
    "chapter", "episode", "volume", "arc", "season", "part", "book", "issue", "act",
    "file", "image", "gallery", "main", "see", "note", "list", "category", "template",
    "north", "south", "east", "west",
}
# Words that can follow a name without making it the actor: a preposition, a conjunction, a
# determiner or a relative. "News of the ... spread" and "Street Fighter: Resurrection" are
# not somebody doing something; "The Time Breakers empower ..." is.
_NOT_A_VERB = {
    "of", "the", "a", "an", "and", "or", "but", "nor", "in", "on", "at", "to", "for", "with",
    "from", "by", "as", "into", "onto", "upon", "over", "under", "near", "about", "per",
    "via", "than", "then", "also", "not", "only", "just", "however", "though", "although",
    "because", "since", "while", "during", "after", "before", "until", "against", "between",
    "among", "beyond", "behind", "within", "without", "throughout", "despite", "toward",
    "towards", "who", "whom", "whose", "which", "that", "when", "where", "why", "how",
    "his", "her", "its", "their", "our", "your", "my", "this", "these", "those", "there",
    "here", "such", "both", "each", "every", "all", "any", "some", "no", "more", "most",
    "less", "least", "very", "much", "many", "again", "still", "even", "so", "too",
}
_PAREN_TAIL = re.compile(r"\s*\([^()]*\)\s*$")
_PROPER = re.compile(r"\b[A-Z][a-z]{2,}(?:[ -][A-Z][a-z]{2,})*\b")
_PRONOUN = re.compile(r"\b(?:he|she|it|they|him|her|his|hers|its|their|them|himself|herself|"
                      r"itself|themselves|who|which|that)\b", re.I)
_BY_AGENT = re.compile(r"\bby\s+(?:the\s+|a\s+|an\s+)?((?:[A-Z][a-z]{2,})(?:[ -][A-Z][a-z]{2,})*)")


def entity_forms(entity):
    """Surface forms a mined sentence could use for this entity.

    The catalogue title carries a disambiguating parenthetical the prose never does -- pages
    say "the Future Warrior", never "Future Warrior (Xenoverse 2)" -- so the tail comes off,
    and every substantial word of what remains stands on its own because wikis shorten to a
    surname or a given name after first mention.
    """
    whole = (entity or "").strip()
    base = _PAREN_TAIL.sub("", whole)
    forms = set()
    if base:
        forms.add(base.lower())
    # THE PARENTHETICAL IS OFTEN WHERE THE REAL NAME IS. "Iron Man (Tony Stark)" is called Tony
    # on nine pages in ten, and dropping the bracket entirely made every one of those sentences
    # read as somebody else's deed. Both halves count as this entity.
    for tok in re.findall(r"[A-Za-z][A-Za-z'\-]{2,}", whole):
        if tok.lower() not in _NAME_STOP:
            forms.add(tok.lower())
    return forms


def _leads_a_verb(text, end):
    """True when the word right after a name is the name DOING something.

    Not a parser -- a filter against the commonest false actor in mined wiki prose. "Super Ki
    Explosion - A more powerful version", "News of the survival", "Street Fighter: Resurrection"
    all put a capitalised span in front of the evidence without anybody acting; a name followed
    by an ordinary lowercase word that is not a preposition, determiner or relative is the shape
    that does.
    """
    rest = text[end:]
    rest = re.sub(r"^['’]s\b", "", rest)
    m = re.match(r"[\s,]*([a-z][a-z'\-]+)\b", rest)
    return bool(m) and m.group(1) not in _NOT_A_VERB


def _is_entity(name, forms):
    """True when this capitalised span names the entity rather than somebody else."""
    n = (name or "").strip().lower()
    if not n:
        return False
    if n in forms:
        return True
    return any(t in forms for t in re.findall(r"[a-z][a-z'\-]{2,}", n))


def _proper_spans(text, forms):
    """(mine, others) -- capitalised spans that name the entity, and those that name a rival."""
    mine, others = [], []
    for m in _PROPER.finditer(text):
        span = m.group(0)
        if all(w.lower() in _NAME_STOP for w in re.findall(r"[A-Za-z'\-]+", span)):
            continue
        (mine if _is_entity(span, forms) else others).append(m)
    return mine, others


def subject_refusal(entity, text, ax=None):
    """Guard 3. Why this sentence cannot be credited to `entity`, or None if it can.

    Four questions, each one asked of the entity by name:

      a. `<act> by <agent>` -- a passive that NAMES its doer. The deed belongs to whoever is
         after "by", and the only question worth asking is whether that is the entity.
      b. a passive with no agent named -- the sentence's subject is what was acted upon, and
         nobody in the sentence is offered as the doer. Refused, as before.
      c. a handoff ("summoned X, who erased ...") -- the deed lands on the actor the relative
         clause attaches to. Refused unless that actor IS the entity, which is the Zeno case
         read from the other side: on ZENO's sheet that erasure is his own.
      d. a rival agent leading the act -- another name stands before the axis evidence and the
         entity is nowhere ahead of it, by name or pronoun. This is the bystander credit the
         guard exists to stop and the one it could never see.
    """
    text = text or ""
    forms = entity_forms(entity)
    if not forms:
        return None                      # nothing to test the sentence against
    mine, others = _proper_spans(text, forms)

    passive = P._PATIENT.search(text)
    if passive:
        # a. the passive names its agent
        agent = _BY_AGENT.search(text, passive.start())
        if agent:
            if _is_entity(agent.group(1), forms):
                return None              # "planets destroyed by Goku", on Goku's own sheet
            return "the deed is credited to " + agent.group(1)
        # b. no agent offered
        return "the sentence puts its subject on the receiving end of the act"

    # c. the deed changes hands mid-sentence
    hand = _HANDOFF.search(text)
    if hand:
        recip = _PROPER.findall(hand.group(0))
        recip = [r for r in recip if not all(w.lower() in _NAME_STOP
                                             for w in re.findall(r"[A-Za-z'\-]+", r))]
        if recip and _is_entity(recip[-1], forms):
            return None                  # the entity is who the deed was handed TO
        return "the deed passes to " + (recip[-1] if recip else "another actor")

    # d. somebody else is standing in front of the verb.
    #
    # Three conditions together, because any one alone over-refuses on real wiki prose: the
    # rival must END before the axis evidence begins (otherwise the "name" contains it -- "Odd
    # Speed Wave" IS the celerity match), it must lead a verb rather than sit in a heading or a
    # possessive, and the entity must be absent from the whole run-up, by name AND by pronoun.
    m_ax = AXIS_RE[ax].search(text) if ax in AXIS_RE else None
    if m_ax:
        cut = m_ax.start()
        head = text[:cut]
        if not any(m.start() < cut for m in mine) and not _PRONOUN.search(head):
            lead = next((m for m in others
                         if m.end() <= cut and _leads_a_verb(text, m.end())), None)
            if lead is not None:
                return lead.group(0) + " leads the act and " + str(entity) + " is not named"
    return None

# --------------------------------------------------------------------------- guard 5: quantities
#
# Conversions to the SI quantity each BAND_EDGES axis is expressed in. Only units with an
# unambiguous physical meaning appear here; "power level" and "kili" are franchise-internal
# scales with no conversion and are deliberately absent -- they belong in the Rosetta Tables
# (Vol. X.4), not in a joules column.
_TO_JOULES = {
    "ton": 4.184e9, "tons": 4.184e9, "tonne": 4.184e9, "tonnes": 4.184e9,
    "kiloton": 4.184e12, "kilotons": 4.184e12,
    "megaton": 4.184e15, "megatons": 4.184e15,
    "gigaton": 4.184e18, "gigatons": 4.184e18,
    "joule": 1.0, "joules": 1.0,
}
_TO_METRES = {
    "meter": 1.0, "meters": 1.0, "metre": 1.0, "metres": 1.0,
    "kilometer": 1e3, "kilometers": 1e3, "kilometre": 1e3, "kilometres": 1e3,
    "mile": 1609.34, "miles": 1609.34,
    "light-year": 9.461e15, "lightyear": 9.461e15, "light year": 9.461e15,
    "light-years": 9.461e15, "lightyears": 9.461e15, "light years": 9.461e15,
    "parsec": 3.086e16, "parsecs": 3.086e16,
}


def quantity_scores(ev, anchor):
    """Axis scores computed arithmetically from measured quantities. No model opinion involved.

    A tonne of TNT is a tonne of TNT in every fiction, which is the whole reason Part Three
    grounds the ladder in joules and metres rather than adjectives.
    """
    out = {}
    for q in ev.get("quantities", []):
        try:
            val = float(str(q["value"]).replace(",", ""))
        except (ValueError, KeyError):
            silence.note("magnitude.py:quantity-value")
            continue
        unit = (q.get("unit") or "").lower().rstrip(".")
        if unit in _TO_JOULES:
            axis, x = "ruin", val * _TO_JOULES[unit]
        elif unit in _TO_METRES:
            axis, x = "reach", val * _TO_METRES[unit]
        else:
            continue                      # franchise-internal scale: not convertible, not used
        s = A.axis_score(x, anchor, axis)
        if s is None:
            continue
        # Keep the strongest measured reading per axis; a lesser feat does not unmake a greater.
        if axis not in out or s > out[axis]["score"]:
            out[axis] = {"score": s, "feat": q["sentence"], "page": q.get("page", ""),
                         "measured": f"{val:g} {unit}", "si": x, "by": "instrument"}
    return out


# --------------------------------------------------------------------------- the call

SYSTEM = f"""You are Custos-Prime of the Panscriptum, running Charter Part Three's Custodial Assay.

You are given FEATS mined verbatim from an entity's own source wiki. Score the entity from those
feats and from nothing else. Knowledge you have that is not in the list may not be used.

STEP 1 ANCHOR. Fix the integer band by CAPACITY TO DECIDE OUTCOMES AT SCALE (owner ruling,
2026-08-23; Charter Part Three's own "what scale of conflict it can DECIDE, not merely what it
can break", generalised to every kind of entry). One question, three projections:

  a PERSON        who would they beat -- the scale of conflict their attested feats decide
  an EQUIPABLE    how much stronger does it make its possessor -- the DELTA it grants, ranked
                  exactly as a person's own power would be
  anything else   how much effect does it have WITHIN THE SCOPE OF WHAT IT CAN INTERACT WITH
                  -- an institution, a world-tree, a law of nature all decide outcomes without
                  ever fighting

These are one quantity manifesting differently, which is why unlike things stay comparable:
Yggdrasil SUSTAINS at everything-scale, Dr. Manhattan ACTS at it, the completed Infinity
Gauntlet GRANTS it -- three manifestations, one Magnitude ceiling.

  M0 a village   M1 a city or nation   M2 a continent   M3 a planet
  M4 a stellar system   M5 star clusters   M6 a galaxy   M7 a universe
  M8 multiverses   M9 metaverses and xenoverses   M10 everything

Effect, not menace. Yggdrasil menaces nobody and SUSTAINS nine worlds -- deciding, every
moment, that they continue -- so it anchors at what its effect holds up. A treasure, an
institution, an event and a law of nature all decide outcomes within what they can interact
with; most of them have no threat at all, and the ladder's own names are scale names:
Worldshaker, Stellar, Galactic, Universal, Multiversal.

TRAVEL DECIDES NOTHING BY ITSELF. Crossing universes, walking between planes, or riding a
time machine is VECTOR -- one axis, scored later -- and never the anchor. The anchor asks what
scale of outcome the entity can DECIDE, and arriving somewhere is not deciding anything there.
Goku anchors M7 because a tournament deciding twelve universes' survival turned on his fights;
a planeswalker who crosses the multiverse but whose victories are duels and mind-edits decides
outcomes at the scale of a person or a city, and anchors there. The charter's own published
Jace Beleren is 𝔄 M2.88 for exactly this reason, with his Spark filed under Vector.

Presence is also ABSOLUTE, never relative to an opponent. Goku is no threat to Brahman and
Brahman is no threat to Goku, and neither fact touches either anchor: one is present at the
scale of a universe, the other throughout existence, and both would be so with the other absent.
Ask "how far does this thing extend, and through what", never "who would win".

STEP 2 SCORE these axes 0.0-9.9 WITHIN that band: {', '.join(AXES)}.
Cite, for each axis, the exact feat number that justifies it. The feat must be ABOUT that axis:
a feat about destruction supports Ruin, not Celerity. The entity must be the one who ACTED.

If no feat in the list bears on an axis, do not score it. Return instead:
  "none"        the axis applies and the quantity is genuinely absent
  "unestimable" the axis applies but was never observed being exercised
  "n/a"         the axis does not apply to this kind of thing

Most entities have evidence for two or three axes. Returning nine statuses and two scores is a
correct answer. Scoring every axis is almost always wrong, and a sheet with every axis near the
top is rejected outright."""

SCHEMA = {
    "type": "object",
    "properties": {
        "anchor": {"type": "string", "enum": A.LADDER},
        "presence_evidence": {"type": "string"},
        "epoch": {"type": "string"},
        "axes": {
            "type": "object",
            "properties": {ax: {
                "type": "object",
                "properties": {"score": {"type": ["number", "string"]},
                               "feat": {"type": "string"}},
                "required": ["score", "feat"]} for ax in AXES},
            "required": AXES},
    },
    "required": ["anchor", "presence_evidence", "epoch", "axes"],
}


def _norm(t):
    return re.sub(r"[^a-z0-9 ]", " ", (t or "").lower())


def verify(entity, got, ev):
    """Apply guards 1-3. Returns (scores, worksheet, rejections).

    Guard 4 (saturation) judges the finished sheet and guard 5 (quantity) overwrites axes from
    instruments; both run in `assay_entity`, after this.
    """
    mined = {i: f["feat"] for i, f in enumerate(ev["feats"], 1)}
    mined_norm = {i: _norm(t) for i, t in mined.items()}
    scores, sheet, rejects = {}, {}, []

    for ax in AXES:
        got_ax = (got.get("axes") or {}).get(ax) or {}
        raw = got_ax.get("score")
        cited = (got_ax.get("feat") or "").strip()

        if isinstance(raw, str):
            st = raw.strip().lower()
            scores[ax] = {"none": A.NONE, "unestimable": A.UNESTIMABLE,
                          "n/a": A.INAPPLICABLE, "na": A.INAPPLICABLE}.get(st, A.UNESTIMABLE)
            sheet[ax] = cited or st
            continue
        if not isinstance(raw, (int, float)):
            scores[ax] = A.UNESTIMABLE
            continue

        # 1 VERBATIM -- the citation has to be one of the sentences we handed over.
        #
        # AN EMPTY CITATION USED TO PASS THIS GUARD, ALWAYS, AND TAKE THE FIRST MINED FEAT WITH
        # IT. `_norm("")` is `""` and `"" in t` is True for every non-empty `t`, so the
        # generator below matched on its FIRST iteration: a model that returned a number with no
        # citation at all -- the exact thing this guard exists to refuse -- got `hit` = whichever
        # feat happened to be first in `mined_norm`, and `text` on the next line became that
        # unrelated sentence. Guards 2 and 3 then judged the wrong evidence, and if that
        # arbitrary feat happened to mention the axis and name the subject, an uncited score was
        # written into the library wearing a citation the model never made.
        #
        # This is the "a check that cannot fail looks exactly like a check that passed" shape,
        # in the one place where passing means fabricated provenance. The emptiness test has to
        # come FIRST and be its own rejection, not a special case folded into the match: a blank
        # citation is not a citation that failed to match, it is the absence of the evidence the
        # whole assay is built on, and it deserves to say so in `rejects`. (run #27)
        cn = _norm(cited)
        if not cn:
            rejects.append((ax, "no citation given"))
            scores[ax] = A.UNESTIMABLE
            continue
        hit = next((i for i, t in mined_norm.items()
                    if t and (t in cn or cn in t or _overlap(t, cn) > 0.6)), None)
        if hit is None:
            rejects.append((ax, "citation not in the mined feats"))
            scores[ax] = A.UNESTIMABLE
            continue
        text = mined[hit]

        # 2 RELEVANCE -- the feat has to be about this axis.
        if not AXIS_RE[ax].search(text):
            rejects.append((ax, f"feat does not bear on {ax}: {text[:60]}"))
            scores[ax] = A.UNESTIMABLE
            continue

        # 3 SUBJECT -- the entity has to be the doer, and the check now reads the entity.
        why = subject_refusal(entity, text, ax)
        if why:
            rejects.append((ax, f"entity is not the actor ({why}): {text[:60]}"))
            scores[ax] = A.UNESTIMABLE
            continue

        scores[ax] = round(min(9.9, max(0.0, float(raw))), 2)
        sheet[ax] = f"[{hit}] {text}  ({ev['feats'][hit - 1]['page']})"

    return scores, sheet, rejects


def _overlap(a, b):
    """Token overlap, so a citation trimmed at the ends still matches its source sentence."""
    A_, B_ = set(a.split()), set(b.split())
    return len(A_ & B_) / max(1, min(len(A_), len(B_)))


def saturated(scores):
    """Guard 4. Every scored axis at the top means the model did not refuse anywhere."""
    nums = [v for v in scores.values() if isinstance(v, (int, float))]
    return len(nums) >= 6 and min(nums) >= 9.0


def candidates(ev, cap=None):
    """{axis: [sentences]} drawn from the entity's own cached pages.

    The model used to receive one flat pile of feats and had to allocate it across eleven axes,
    which is how an earthquake ended up cited for Celerity. It now sees only the candidates for
    the axis it is scoring, so citing across axes stops being an error it can make.
    """
    out = {ax: [] for ax in AXES}
    for page, clean in (ev.get("text") or {}).items():
        for ax, rows in F.by_axis(clean, page).items():
            out[ax].extend(rows)
    # Longest first: a sentence carrying more of its own context makes the better worksheet line.
    # Ranked longest-first so the richest line leads, but never truncated: capping at six
    # decided that an entity with forty pieces of Ruin evidence had six.
    return {ax: sorted(v, key=lambda r: -len(r["feat"]))[:cap] if cap
            else sorted(v, key=lambda r: -len(r["feat"])) for ax, v in out.items()}


AXIS_SCHEMA = {
    "type": "object",
    "properties": {"score": {"type": ["number", "string"]}, "feat": {"type": "string"}},
    "required": ["score", "feat"],
}
ANCHOR_SCHEMA = {
    "type": "object",
    "properties": {"anchor": {"type": "string", "enum": A.LADDER},
                   "presence_evidence": {"type": "string"}, "epoch": {"type": "string"}},
    "required": ["anchor", "presence_evidence", "epoch"],
}
# Per-slice ceiling for split calls, in characters of evidence. Small enough for every live
# bucket's per-minute token caps AND the local window.
SPLIT_SLICE = 8000
# Above this, a single call's recall is measurably unreliable and the split path is DEFAULT.
ONE_SHOT_MAX = 30000


def _split_assay(c, entity, cand, epoch, head_note=None):
    """Assay an entity whose evidence no single call can carry: eleven axis calls plus one
    anchor call, merged into the same sheet shape the one-shot path produces.

    THIS IS A SPLIT, NEVER A TRUNCATION. Jace Beleren's evidence is ~140,000 characters; the
    pool's fastest buckets cap tokens per minute well below that, the local window is 24k, and
    the old behaviour was to DEFER him forever -- so the heaviest, best-documented entities in
    the library were exactly the ones the automation could not assay, and a person did them by
    hand. The owner's brief is that the person is not the instrument. Every candidate sentence
    is still read: each axis's list is sent in SPLIT_SLICE-sized slices, an axis's score is the
    best-evidenced slice's answer, and the anchor is then asked over the eleven winning
    citations -- the same digest a hand worksheet ends up staring at.
    """
    # AXES IN PARALLEL. Eleven independent questions were being asked one after another, so a
    # heavyweight's split assay took eleven round-trips end to end while fifteen pool lanes sat
    # idle. The axes share nothing; six at a time cuts the wall clock without adding a single
    # extra call.
    from concurrent.futures import ThreadPoolExecutor as _TPE

    def _one_axis(ax):
        rows = cand.get(ax) or []
        if not rows:
            return ax, {"score": A.UNESTIMABLE, "feat": "",
                        "slices": {"attempted": 0, "answered": 0, "refused": 0,
                                   "sentences": 0, "sentences_unread": 0, "chars_unread": 0}}
        best = None
        i = 0
        # A SLICE THAT NOBODY ANSWERED USED TO LEAVE NO TRACE (order cb9c6ca51d90).
        #
        # The line below this loop was `if not got: continue`, and that `continue` was the whole
        # defect: the slice's sentences had already been consumed by `i`, the transport had said
        # nothing, and the axis went on to score from whatever else came back. An axis answered
        # on one slice of ten and an axis answered on ten of ten produced the SAME shape --
        # a score, a citation, no remainder -- while the docstring three lines up promises
        # "Every candidate sentence is still read". On a rate-limited pool that gap is not rare;
        # it is the common case, and it is invisible precisely when it is worst.
        #
        # So the loop counts. Nothing about how the score is CHOSEN changes -- still the best
        # answered slice, same number for the same answers -- but the axis now carries how much
        # of its own evidence was actually read, and `_split_assay` totals it onto the sheet.
        att = ans = 0
        unread_rows = unread_chars = 0
        while i < len(rows):
            block, size = [], 0
            while i < len(rows) and (size == 0 or size + len(rows[i]["feat"]) < SPLIT_SLICE):
                block.append(rows[i]["feat"])
                size += len(rows[i]["feat"]) + 4
                i += 1
            prompt = ("ENTITY: " + entity
                      + ((chr(10) + "EPOCH (score THIS state and no other): " + epoch)
                         if epoch else "")
                      + chr(10) + chr(10) + "AXIS UNDER ASSAY: " + ax.upper()
                      + chr(10) + "Score 0-9.9 from these candidate sentences ONLY, citing the"
                      + " single strongest VERBATIM as `feat`. If none genuinely bears on this"
                      + " axis, return score \"unestimable\" and an empty feat."
                      + chr(10) + chr(10)
                      + chr(10).join("- " + b for b in block))
            att += 1
            got = _ask(c, SYSTEM, prompt, AXIS_SCHEMA)
            if not got:
                unread_rows += len(block)
                unread_chars += size
                continue
            ans += 1
            sc = got.get("score")
            if isinstance(sc, (int, float)):
                if best is None or not isinstance(best[0], (int, float)) or sc > best[0]:
                    best = (sc, (got.get("feat") or "").strip())
            elif best is None:
                best = (A.UNESTIMABLE, "")
        census = {"attempted": att, "answered": ans, "refused": att - ans,
                  "sentences": len(rows), "sentences_unread": unread_rows,
                  "chars_unread": unread_chars}
        out = ({"score": best[0], "feat": best[1]} if best
               else {"score": A.UNESTIMABLE, "feat": ""})
        out["slices"] = census
        return ax, out

    with _TPE(max_workers=6) as _ex:
        axes_out = dict(_ex.map(_one_axis, AXES))

    cites = [v["feat"] for v in axes_out.values() if v.get("feat")]
    if not cites:
        return None
    ap = ("ENTITY: " + entity
          + ((chr(10) + "EPOCH: " + epoch) if epoch else "")
          + ((chr(10) + head_note) if head_note else "")
          + chr(10) + chr(10) + "THE STRONGEST CITED FEAT PER AXIS:" + chr(10)
          + chr(10).join("- " + f for f in cites)
          + chr(10) + chr(10) + "Fix the ANCHOR band per STEP 1 of your instructions.")
    got = _ask(c, SYSTEM, ap, ANCHOR_SCHEMA)
    if not got or got.get("anchor") not in A.LADDER:
        return None
    return {"anchor": got["anchor"],
            "presence_evidence": (got.get("presence_evidence") or "").strip(),
            "epoch": got.get("epoch") or epoch or "unstamped",
            "axes": axes_out,
            "slice_census": slice_census(axes_out)}


def slice_census(axes_out):
    """How much of the evidence a split sheet was actually read from.

    `evidence_dropped_to_fit` already exists on the record for the budgeted case, on the
    argument that "a sheet scored on a trimmed body of evidence must say so". A slice the
    transport never answered trims the same body just as effectively, and this is the same
    declaration for that case: totals, plus the per-axis rows so a reader can see WHICH axis
    is thin rather than only that something was.
    """
    per, att = {}, 0
    ans = unread = chars = 0
    for ax, v in (axes_out or {}).items():
        s = (v or {}).get("slices") or {}
        if not s.get("attempted"):
            continue
        per[ax] = {"answered": s.get("answered", 0), "attempted": s.get("attempted", 0),
                   "sentences_unread": s.get("sentences_unread", 0)}
        att += s.get("attempted", 0)
        ans += s.get("answered", 0)
        unread += s.get("sentences_unread", 0)
        chars += s.get("chars_unread", 0)
    thin = sorted(a for a, r in per.items() if r["answered"] < r["attempted"])
    return {"slices_attempted": att, "slices_answered": ans, "slices_refused": att - ans,
            "sentences_unread": unread, "chars_unread": chars,
            "complete": att > 0 and ans == att, "axes_thinned": thin, "by_axis": per}


def compose(entity, cand, epoch, budget, head_note=None):
    """Build the prompt at a given evidence budget. Returns (prompt, flat, dropped).

    Round-robin across axes rather than filling axis by axis: a budget spent in declaration
    order hands the whole allowance to Ruin and leaves Suasion with nothing, which silently
    converts "not measured" into "no evidence". Those are different findings, and one of them
    is a lie.
    """
    dropped = 0
    if budget:
        keep, spent, depth = {ax: [] for ax in AXES}, 0, 0
        while True:
            progressed = False
            for ax in AXES:
                if depth < len(cand[ax]):
                    r = cand[ax][depth]
                    cost = len(r["feat"]) + 8
                    if spent + cost <= budget:
                        keep[ax].append(r)
                        spent += cost
                        progressed = True
            if not progressed:
                break
            depth += 1
        dropped = sum(len(cand[ax]) for ax in AXES) - sum(len(keep[ax]) for ax in AXES)
        cand = keep

    blocks, flat, i = [], {}, 0
    for ax in AXES:
        if not cand[ax]:
            continue
        blocks.append(ax.upper() + ":")
        for r in cand[ax]:
            i += 1
            flat[i] = (ax, r)
            blocks.append("  [" + str(i) + "] " + r["feat"])
    head = "ENTITY: " + entity
    if epoch:
        head += chr(10) + "EPOCH (score THIS state and no other): " + epoch
    if head_note:
        head += chr(10) + head_note
    nl = chr(10)
    prompt = (head + nl + nl + "CANDIDATE EVIDENCE, GROUPED BY THE AXIS IT BEARS ON:" + nl
              + nl.join(blocks) + nl + nl
              + "Cite only from an axis's own list. An axis with no list takes a status.")
    return prompt, flat, dropped


def _split_gate(got, cand, entity=None):
    """Verbatim + relevance + SUBJECT gate for split-path sheets. Axis-relevance is by
    construction (each axis was scored only from its own candidate list); verbatim is checked
    against that same list; guard 3 is applied here for the same reason `verify` applies it.

    GUARD 3 USED TO STOP AT THE ONE-SHOT DOOR (order e22f29b8e4df). `verify()` called
    `subject_refusal`; this function did not call it at all, and this is the DEFAULT path --
    anything over ONE_SHOT_MAX comes here, which is precisely the heaviest and best-documented
    entities in the library, the ones a bystander's deed is most likely to be sitting next to.
    "Beerus erased the universe with a flick" scored 9.0 for Transgression on a sheet filed
    under GOKU and the rejection list came back empty: the guard existed, could refuse, and was
    never asked. A safety in a file is not a safety in effect.

    The guard is run against the FULL CANDIDATE SENTENCE rather than the model's citation. The
    citation may be a trim of it, and a trim is exactly what removes the agent -- "erased the
    universe with a flick" carries no Beerus to refuse. `verify` reads `mined[hit]` for the same
    reason; reading less would over-refuse honest evidence and under-refuse the bystander.

    `entity` defaults to None so a caller with nothing to test against is unchanged rather than
    silently refused: `subject_refusal` returns None on an empty name, which is the same "cannot
    decide" it already returns for a bare pronoun.
    """
    scores, sheet, rejects = {}, {}, []
    for ax, v in (got.get("axes") or {}).items():
        sc, ft = v.get("score"), (v.get("feat") or "").strip()
        # containment one way ONLY: a trimmed copy of a real candidate passes; a fabricated
        # wrapper AROUND a real candidate (o in ft) is the fabrication direction and fails
        source = next((r["feat"] for r in (cand.get(ax) or [])
                       if ft and ft in r["feat"]), None) if ft else None
        if isinstance(sc, (int, float)) and source is not None:
            # 3 SUBJECT -- the entity has to be the doer, on this path too.
            why = subject_refusal(entity, source, ax)
            if why:
                rejects.append((ax, f"entity is not the actor ({why}): {source[:60]}"))
                scores[ax] = A.UNESTIMABLE
                continue
            scores[ax] = max(0.0, min(9.9, float(sc)))
            sheet[ax] = ft
        elif isinstance(sc, (int, float)):
            rejects.append((ax, "split citation not verbatim in this axis's candidates"))
            scores[ax] = A.UNESTIMABLE
        else:
            scores[ax] = A.UNESTIMABLE
    return scores, sheet, rejects


def assay_entity(c, entity, host, attestation="Transcribed", epoch=None, ceiling=None):
    ev = F.evidence_for(host, entity)
    cand = candidates(ev)
    if not sum(len(v) for v in cand.values()) and not ev["quantities"]:
        return {"entity": entity, "result": None,
                "reason": "no axis cleared its gate on this entity's own source pages"}

    # TRY THE POOL WITH EVERYTHING, THEN THE LOCAL MODEL WITH WHAT FITS IN IT.
    #
    # The first version of this decided the budget once, from pool_ready(), and built a single
    # prompt. That is wrong in the exact case that matters: the pool is REACHABLE but declines
    # this particular call -- every bucket rate-limited, or four of them shed to HTTP 402 mid-run
    # -- and the un-budgeted 58,000-character prompt then falls back onto a 24,576-character
    # local window and times out. Eight of the first twelve batch entities died precisely there,
    # and the reason string said "no answer from the pool or the local model", which is true and
    # useless. So the prompt is composed twice, at two sizes, for two different transports.
    epoch_note = None if epoch else ID.epoch_directive(host)
    prompt, flat, dropped = compose(entity, cand, epoch, None, head_note=epoch_note)
    got = None
    used = "pool"
    # SPLIT-FIRST above the recall cliff. read.py measured it directly: the same page at
    # 36,000 characters yielded 19 feats against 41 at 10,000 -- attention over a long prompt
    # thins, and a citation the model half-remembers fails the verbatim gate. Jace's 140k
    # one-shot came back with EVERY axis rejected: the pool accepted the prompt and the answer
    # was worthless. Big evidence goes through the per-axis split by default; one-shot is for
    # prompts a model can actually hold in mind.
    if len(prompt) > ONE_SHOT_MAX:
        used = "split"
        got = _split_assay(c, entity, cand, epoch, head_note=epoch_note)
    elif pool_ready():
        try:
            import cascade_bridge as CB
            got = CB.ask(SYSTEM, prompt, SCHEMA)
        except Exception:
            silence.note("magnitude.py:pool-call")
            got = None

    if got is None and used != "split":
        # HARD RULE 0. The local window is 6,144 tokens and Goku's evidence is 58,099
        # characters, so the obvious fallback is to trim the evidence until it fits. That is
        # forbidden, and rightly: "a cap on an ordered listing is not a sample, it is a
        # TRUNCATION, and it silently decides that everything past the cutoff does not exist."
        # An entity assayed on the two-fifths of its own record that happened to fit would
        # carry a Magnitude indistinguishable from one assayed on all of it.
        #
        # So an entity too large for the local model is DEFERRED, not shrunk. `settled()` treats
        # a deferral as unfinished business and the next run picks it up, which is the rule's
        # own prescription: more providers, or more time, never a smaller universe.
        if len(prompt) <= LOCAL_FITS:
            used = "local"
            try:
                # LOCAL_FITS is 20,000 chars ~ 5,400 tokens of prompt: over the config default
                # of 6,144 once the system prompt and reply are counted, and Ollama truncates
                # the overflow without a word. 8,192 holds the whole one-shot.
                # ONE RUNNER, ONE CONTEXT. This asked for 8,192 to hold a ~5,400-token one-shot
                # that would overflow the OLD 6,144 default -- sound reasoning against a default
                # that no longer applies: config now declares 12,288, which holds the same
                # one-shot with room to spare. Asking for 8,192 anyway bought a runner REBUILD,
                # not a bigger window, because Ollama holds a model at one size. Order
                # 706215aabc5f.
                got = P.ask(c, SYSTEM, prompt, SCHEMA, timeout=420, tag="assay-local")
            except Exception:
                silence.note("magnitude.py:local-call")
                got = None
        else:
            # TOO BIG FOR ANY SINGLE CALL -> SPLIT, never defer-first. The five heaviest
            # entities in the library sat permanently deferred here while a person assayed
            # them by hand, which inverts the whole point of the automation.
            used = "split"
            got = _split_assay(c, entity, cand, epoch, head_note=epoch_note)
            if got is None:
                return {"entity": entity, "host": host, "result": None, "status": "DEFERRED",
                        "reason": ("no transport carried even the split calls; retried on the "
                                   "next run"),
                        "prompt_chars": len(prompt), "transport_tried": "pool+split"}

    if not got:
        return {"entity": entity, "host": host, "result": None, "status": "DEFERRED",
                "reason": "no transport answered (one-shot, split, or local); retried next run",
                "prompt_chars": len(prompt), "transport_tried": used}

    final_epoch = epoch or (got.get("epoch") or "").strip()
    if not ID.epoch_acceptable(host, final_epoch):
        # OWNER RULING 2026-08-23: for epoch-mandatory sources an unstamped sheet is refused,
        # not published. An oldwalker and a neowalker are different power classes; a sheet
        # that does not say which it measured is a measurement of an unspecified subject.
        return {"entity": entity, "host": host, "result": None, "status": "DEFERRED",
                "reason": ("epoch required for this source and the model returned "
                           + repr(final_epoch or "nothing") + "; retried next run"),
                "prompt_chars": len(prompt), "transport_tried": used}

    anchor = got.get("anchor") if got.get("anchor") in A.LADDER else "M0"
    if ceiling and A.LADDER.index(anchor) > A.LADDER.index(ceiling[1]):
        anchor = ceiling[1]                 # a fiction cannot be out-scaled by its own inhabitant
    ev_v = dict(ev)
    ev_v["feats"] = [flat[k][1] for k in sorted(flat)]
    if used.startswith("split"):
        scores, sheet, rejects = _split_gate(got, cand, entity)
    else:
        scores, sheet, rejects = verify(entity, got, ev_v)
        if not sheet and any(cand.values()):
            # A ONE-SHOT WHOSE EVERY CITATION FAILED VERBATIM IS A QUALITY FAILURE, NOT A
            # FINDING. Jace one-shot three times: two M2 anchors and an M0, every axis
            # rejected each time -- whichever bucket took the call paraphrased its citations
            # and the gate (correctly) threw them all away. Filing that as band-only would
            # record the transport's bad day as the entity's evidence ceiling. The split re-asks
            # axis by axis in slices a model can actually hold, which is where citation
            # fidelity comes back.
            retry = _split_assay(c, entity, cand, epoch, head_note=epoch_note)
            if retry is not None:
                got, used = retry, "split-retry"
                # THE RETRY IS A NEW ANSWER AND IS HELD TO EVERY GATE THE FIRST ONE WAS.
                # The first draft validated the epoch on the ORIGINAL got and then let the
                # retry replace it -- so a junk one-shot with a plausible epoch could pass the
                # mandate, and the published accession would carry the junk answer's epoch on
                # the retry's sheet. Re-derive, re-validate, re-clamp.
                final_epoch = epoch or (got.get("epoch") or "").strip()
                if not ID.epoch_acceptable(host, final_epoch):
                    return {"entity": entity, "host": host, "result": None,
                            "status": "DEFERRED",
                            "reason": ("epoch required; the split retry returned "
                                       + repr(final_epoch or "nothing") + "; retried next run"),
                            "prompt_chars": len(prompt), "transport_tried": used}
                anchor = got.get("anchor") if got.get("anchor") in A.LADDER else anchor
                if ceiling and A.LADDER.index(anchor) > A.LADDER.index(ceiling[1]):
                    anchor = ceiling[1]
                scores, sheet, rejects = _split_gate(got, cand, entity)

    # Cross-axis citation is now checkable by INDEX rather than by lexicon: every candidate knows
    # which axis it was offered under, so a line filed elsewhere is caught exactly.
    for ax in AXES:
        cited = ((got.get("axes") or {}).get(ax) or {}).get("feat", "")
        m = re.match(r"\s*\[(\d+)\]", cited)
        if m and int(m.group(1)) in flat and flat[int(m.group(1))][0] != ax:
            rejects.append((ax, "cited evidence offered under " + flat[int(m.group(1))][0]))
            scores[ax] = A.UNESTIMABLE

    # 5 QUANTITY -- measured readings overwrite the model's judgement on their axis. An
    # instrument outranks an opinion, which is the ordering the Attestation ladder already
    # states (Instrumented above Transcribed).
    for ax, q in quantity_scores(ev, anchor).items():
        scores[ax] = q["score"]
        sheet[ax] = f"INSTRUMENT {q['measured']} = {q['si']:.3g} SI  <- {q['feat'][:120]}"

    if saturated(scores):
        return {"entity": entity, "result": None, "anchor": anchor,
                "reason": "sheet saturated: every scored axis at the ceiling, model did not refuse",
                "rejections": rejects}

    res = A.assay(anchor, scores, attestation=attestation,
                  epoch=final_epoch or "unstamped", worksheet=sheet)
    return {"entity": entity, "host": host, "anchor": anchor,
            "presence": got.get("presence_evidence",
                                got.get("hegemonic_feat", "")), "result": res,
            "worksheet": sheet, "rejections": rejects,
            "candidates": {k: len(v) for k, v in cand.items() if v},
            "quantities_seen": len(ev["quantities"]),
            "prompt_chars": len(prompt),
            # A sheet scored on a trimmed body of evidence must say so. Left off, a budgeted
            # assay is indistinguishable from a complete one, and the number carries a
            # confidence it has not earned.
            "evidence_dropped_to_fit": dropped,   # always 0 now; kept so a future budget cannot be silent
            # The split path's equivalent of the line above: how many evidence slices were put
            # to a transport and how many came back. None on the one-shot and local paths,
            # which read their whole prompt in one call or not at all.
            "evidence_slices": (got.get("slice_census") if isinstance(got, dict) else None),
            "transport": used,
            "pages": ev["pages_read"]}


# --------------------------------------------------------------------------- calibration

# Charter Part Three prints these with worksheets. They are the only assays in the library whose
# answers are already known, which makes them the only honest test of the instrument. The model
# is never shown the target.
BENCHMARKS = [
    # Epoch is an INPUT. The first run anchored Goku at M3 against a published M7.62 purely
    # because the miner surfaced Super Saiyan 3 feats and scored them faithfully, which is a
    # correct reading of a different subject.
    ("Jotaro Kujo",     "jojo.fandom.com",       "M2", 2.14, 0.18, "Stardust Crusade"),
    ("Kenshiro",        "hokuto.fandom.com",     "M3", 3.52, 0.12, "post-Raoh"),
    ("Monkey D. Luffy", "onepiece.fandom.com",   "M4", 4.08, 0.55, "Gear Five / Awakened Nika"),
    ("Naruto Uzumaki",  "naruto.fandom.com",     "M4", 4.31, 0.30,
     "Fourth Shinobi World War, Six Paths"),
    ("Goku",            "dragonball.fandom.com", "M7", 7.62, 0.41,
     "Mastered Ultra Instinct, Tournament of Power"),
    ("Jace Beleren",    "mtg.fandom.com",        "M2", 2.88, 0.25, "post-Mending"),
]


def config():
    import yaml
    cfg = yaml.safe_load(open(os.path.join(HERE, "config.yaml"), encoding="utf-8"))
    return {"model": cfg.get("model"),
            "ollama_host": cfg.get("ollama_host", "http://localhost:11434"),
            "seed": 47, "num_ctx": cfg.get("num_ctx", 6144)}


def calibrate():
    """Run the charter's published assays through the WHOLE automation and persist the verdict.

    This is the instrument's regression test: the model is never shown the target, the run
    goes through every gate a stranger's entity would (evidence mine, split, epoch mandate,
    ceiling clamp), and the result lands in data/CHARTER_REGRESSION.json where a standard
    reads it. Consistency is interval OVERLAP -- two measurements with error bars agree when
    |got - published| <= ci_published + ci_got -- because the automation's honest coverage
    (it scores only the axes whose feats survive the verbatim gate) legitimately differs from
    a hand worksheet's, and demanding the point value land inside the charter's own interval
    would fail runs the instrument actually got right.

    WRITTEN TO BE KILLED, like its sibling `run_batch()`. The foreman dispatches this roughly
    hourly and kills it on the next lap (M15), and six charter benchmarks against a rate-limited
    pool do not reliably finish inside one lap. The original wrote CHARTER_REGRESSION.json ONCE,
    after the whole loop -- so every killed attempt threw away every benchmark it had completed,
    and the file sat 35 hours stale while the job ran constantly. That is why the standard
    `the automation reproduces the charter` was red: not because the instrument had drifted, but
    because nothing it produced was ever persisted.

    So the file is now the IN-PROGRESS pass, checkpointed after every benchmark, and the next
    invocation RESUMES it instead of restarting. Two honesty properties matter more than the
    speed-up:

    * `at` is stamped ONLY when every benchmark has a row. A half-finished pass has not
      reproduced the charter, and must not read as though it had -- one consistent row written
      early would otherwise turn the standard green with five references unrun, which is the
      project's "green by absence" failure mode exactly. `complete` and `pending` say so out
      loud, and `standards.py` reports the partial pass as in-progress rather than as an age.
    * A pass whose `started` is older than the standard's own 26h freshness floor is ABANDONED
      and begun again. Rows carry their own `at`, so a pass spanning hours is visible as one;
      a "daily" regression stitched from three days of fragments would not be one.
    """
    c = config()
    _cr = os.path.join(HERE, "data", "CHARTER_REGRESSION.json")
    now = time.time()
    prior, started = {}, now
    try:
        with open(_cr, encoding="utf-8") as f:
            old = json.load(f)
        # Resume only a pass that is genuinely unfinished, recent, and from THIS model. A
        # completed pass is what we are here to replace; a stale or foreign-model one would
        # blend measurements the standard reads as a single verdict.
        if (isinstance(old, dict) and not old.get("complete")
                and old.get("model") == c["model"]
                and (now - float(old.get("started") or 0)) < 26 * 3600):
            started = float(old.get("started") or now)
            for r in (old.get("results") or []):
                if isinstance(r, dict) and r.get("entity"):
                    prior[r["entity"]] = r
    except FileNotFoundError:
        pass
    except Exception:
        silence.note("magnitude.py:calibrate-resume")

    def _land(rows, complete):
        """Checkpoint. `at` appears only on a complete pass -- see the docstring."""
        done = {r.get("entity") for r in rows}
        out = {"started": started, "model": c["model"], "results": rows,
               "complete": bool(complete),
               "pending": [b[0] for b in BENCHMARKS if b[0] not in done]}
        if complete:
            out["at"] = time.time()
        # A standard reads this file (`standards.py`, `automation reproduces the charter`), so a
        # truncating write can leave that check reading an unparseable artifact -- which it would
        # report as a failure to reproduce the charter rather than as a failure to write a file.
        #
        # THROUGH `write_json`, AND THE VERDICT IS READ (order 2a2ca57b2d56). The hand-rolled
        # version here used a PID-less `_cr + ".tmp"`, which two concurrent calibrations collide
        # on directly, and it threw away `replace_retry`'s return -- so a checkpoint that never
        # landed printed exactly like one that did, on a file whose whole job is surviving the
        # foreman's next kill.
        if not silence.write_json(_cr, out, ensure_ascii=False):
            print("   checkpoint did NOT land on " + os.path.basename(_cr)
                  + " (target held open); this pass's progress is not on disk yet")

    print(f"model: {c['model']}\n")
    if prior:
        print(f"resuming pass started {(now - started) / 3600:.1f}h ago: "
              f"{len(prior)} of {len(BENCHMARKS)} benchmarks already done\n")
    def _published(band, val):
        """The charter's own decimal, printed as it was written (order 392372951714).

        This column was `int(val % 1 * 100)`, which floors the binary remainder: Naruto's
        published 4.31 printed as .30 and Jace's 2.88 as .87. Display only -- `row['published']`
        always carried the true value -- but this is the exact column a person reads beside the
        assayed figure to decide whether the instrument reproduced the charter, so a digit lost
        here manufactures a disagreement that the data does not contain.
        """
        return band + ("%.2f" % val)[-3:]

    print(f"{'entity':<20}{'charter':>10}{'assayed':>12}{'band':>7}{'axes':>6}"
          f"{'rej':>5}  worksheet")
    print("-" * 96)
    band_hits, rows = 0, []
    for name, host, band, val, ci, epoch in BENCHMARKS:
        t = time.time()
        if name in prior:
            row = prior[name]
            rows.append(row)
            band_hits += bool(row.get("band_match"))
            print(f"{name:<20}{_published(band, val):>10}"
                  f"{'(resumed)':>12}{'--':>7}{'--':>6}{'--':>5}  "
                  f"kept from this pass")
            continue
        sc = SCOPE.scope_for(host) if host else None
        cl = (sc["scope"], sc["ceiling"]) if sc else None
        r = assay_entity(c, name, host, epoch=epoch, ceiling=cl)
        res = r.get("result")
        row = {"entity": name, "host": host, "published": val, "ci": ci, "band": band}
        row["at"] = time.time()
        if not res or res.get("decimal") is None:
            row.update({"status": r.get("status") or "NO_SCORE",
                        "reason": (r.get("reason") or "band only")[:120], "consistent": None})
            rows.append(row)
            _land(rows, False)
            print(f"{name:<20}{_published(band, val):>10}{'--':>12}{'--':>7}"
                  f"{'--':>6}{len(r.get('rejections', [])):>5}  {r.get('reason', 'band only')[:40]}")
            continue
        got_band = res["magnitude"]
        band_hits += (got_band == band)
        got_val = float(str(got_band)[1:]) + float(res.get("decimal") or 0)
        got_ci = float(res.get("interval") or 0)
        row.update({"status": "SCORED", "got_band": got_band, "got": round(got_val, 2),
                    "got_ci": got_ci, "band_match": got_band == band,
                    "consistent": got_band == band and abs(got_val - val) <= ci + got_ci})
        rows.append(row)
        _land(rows, False)
        mark = "OK" if got_band == band else "MISS"
        print(f"{name:<20}{_published(band, val):>10}"
              f"{res['moth_number'][2:14]:>12}{mark:>7}"
              f"{len(res['axes_scored']):>6}{len(r.get('rejections', [])):>5}  "
              f"{time.time() - t:.0f}s")
    print("-" * 96)
    print(f"anchor band reproduced on {band_hits}/{len(BENCHMARKS)} published assays")
    _land(rows, len(rows) == len(BENCHMARKS))
    return band_hits


def queue(host=None, limit=None):
    """Every catalogued entity with mined evidence, least-assayed first.

    Reads the same character sweep the dashboard reads, so "how many are left" means the same
    number in both places.
    """
    path = os.path.join(HERE, "data", "CHARACTER_SWEEP.json")
    with open(path, encoding="utf-8") as f:
        rows = json.load(f)
    out, seen = [], set()
    for r in rows:
        if not isinstance(r, dict) or not r.get("host") or not r.get("name"):
            continue
        if host and r["host"] != host:
            continue
        if not (r.get("chars") or 0):
            continue                       # nothing mined; the assay would have nothing to read
        # SEARCH, NOT MATCH. The pattern has two arms and each carries its own anchor: the
        # index-page arm is `^`-anchored, the disambiguation arm is `$`-anchored. `match()`
        # pins the whole pattern to position 0, so the second arm could only ever fire on a
        # title that was LITERALLY "(disambiguation)" -- "Kirby (disambiguation)" sailed
        # through. `search()` lets each arm mean what it says; the `^` arm is unaffected.
        if NOT_AN_ENTITY.search(r["name"]):
            continue
        k = r["host"] + "|" + r["name"]
        if k in seen:                      # the sweep carries duplicate rows for shared pages
            continue
        seen.add(k)
        out.append((r["host"], r["name"], r.get("chars") or 0))
    # Richest evidence first. These are the entities the old single-call path could never do,
    # and they are also the ones anybody actually looks up.
    out.sort(key=lambda t: -t[2])
    return out[:limit] if limit else out


_SCOPE_CACHE = {}


def host_ceiling(host):
    """This fiction's own ceiling band, cached per host. The clamp's input.

    `SCOPE.scope_for` does live wiki calls, which is why the batch never passed a ceiling and
    the clamp in assay_entity sat unused: Jace Beleren came back at M10.77 against the
    charter's published 𝔄 M2.88, and Silver Surfer at M10.93 -- a band the charter reserves
    for exactly one class of entry. The model, shown only feats, anchors on the grandest
    sentence it sees; the SOURCE's own measured scope is the outside check, and it was
    already on disk for 155 hosts.
    """
    if host in _SCOPE_CACHE:
        return _SCOPE_CACHE[host]
    cl = None
    try:
        with open(os.path.join(HERE, "data", "SCOPE.json"), encoding="utf-8") as f:
            row = json.load(f).get(host)
        if row and row.get("ceiling"):
            cl = (row.get("scope"), row["ceiling"])
    except Exception:
        silence.note("magnitude.py:host_ceiling-disk")
    if cl is None:
        try:
            row = SCOPE.scope_for(host)
            if row and row.get("ceiling"):
                cl = (row.get("scope"), row["ceiling"])
        except Exception:
            silence.note("magnitude.py:host_ceiling-live")
    _SCOPE_CACHE[host] = cl
    return cl


def settled(rec):
    """Is this record a FINDING, or just the last thing that happened to it?

    The distinction the whole project turns on. Three of these are real results and must never
    be recomputed:

        a scored assay                      -- the entity has a Magnitude
        "no axis cleared its gate"          -- the evidence genuinely does not support one
        a saturation refusal                -- the sheet was rejected whole, on purpose

    Everything else is a transport failure wearing a result's clothes. The first version of
    run_batch() skipped any entity already present in ASSAYS.json, which meant eight entities
    that timed out against a rate-limited pool were recorded as done and would never have been
    attempted again -- the same defect as the poisoned read-cache, rebuilt from scratch in a
    function written to avoid it.
    """
    if not isinstance(rec, dict):
        return False
    if (rec.get("result") or {}).get("decimal") is not None:
        return True
    if rec.get("status") == "DEFERRED":
        return False
    reason = rec.get("reason") or ""
    return ("no axis cleared its gate" in reason) or ("sheet saturated" in reason)


def run_batch(host=None, limit=None, workers=8, resume=True):
    """Assay the queue in parallel, writing after every result.

    Written to be killed. The roll runs for hours against a rate-limited pool, and a crash at
    hour three must not cost hours one and two -- so ASSAYS.json is rewritten on each completion
    and `--resume` skips anything already in it.
    """
    import threading
    from concurrent.futures import ThreadPoolExecutor

    c = config()
    # The requested worker count is a CEILING, never a floor. On local hardware twelve workers
    # do not run twelve assays: they queue behind one model on one card and time each other out.
    # That is how a 393-entity batch scored ZERO tonight while the same code, with the pool up,
    # had scored seven.
    try:
        import tuning as T
        prof = T.profile(force=True)
        workers = T.workers(workers)
        print("regime: %s (%s) -> %d worker(s)" % (prof["regime"], prof["why"], workers))
    except Exception:
        silence.note("magnitude.py:tuning")
    print("transport: " + ("cloud pool (cascade)" if pool_ready()
                           else "LOCAL ONLY -- oversized entities are DEFERRED, never truncated"))
    done = {}
    if resume and os.path.exists(OUT):
        try:
            with open(OUT, encoding="utf-8") as f:
                done = json.load(f)
        except Exception:
            silence.note("magnitude.py:resume")
            done = {}

    all_q = queue(host, limit)                 # 13MB sweep parsed ONCE, not twice
    todo = [(h, n, ch) for h, n, ch in all_q
            if not settled(done.get(h + "|" + n))]
    print("queue: %d entities, %d already assayed, %d to do"
          % (len(all_q), len(done), len(todo)))
    lock = threading.Lock()
    tally = {"n": 0, "scored": 0, "band_only": 0, "unlanded": 0}

    def work(item):
        h, n, _ch = item
        try:
            r = assay_entity(c, n, h, ceiling=host_ceiling(h))
        except Exception as e:
            silence.note("magnitude.py:run_batch")
            r = {"entity": n, "host": h, "result": None,
                 "reason": type(e).__name__ + ": " + str(e)[:160]}
        with lock:
            done[h + "|" + n] = r
            tally["n"] += 1
            if (r.get("result") or {}).get("decimal") is not None:
                tally["scored"] += 1
            else:
                tally["band_only"] += 1
            # On Windows os.replace is DENIED while any reader holds the target open --
            # the dashboard and settled() both read ASSAYS.json on their own clocks, and
            # one collision took a worker down mid-batch (2026-08-23, WinError 5). A short
            # retry outwaits any honest reader; a result that still cannot land is requeued
            # by settled() next run rather than lost.
            #
            # That retry loop used to be spelled out here, over a PID-less `OUT + ".tmp"`, and
            # eight batch workers plus a second `--batch` process all wrote that one temp name
            # (order 2a2ca57b2d56). `silence.write_json` is the same backoff with a tmp name
            # carrying pid and thread, so two writers can no longer land on each other's file.
            # `indent=None` keeps ASSAYS.json in the compact shape it already has on disk.
            # `replace_retry` already records a persistent denial in the failure ledger; the
            # tally counts it too so the batch's own last line cannot claim a clean pass over
            # results that never reached disk.
            if not silence.write_json(OUT, done, ensure_ascii=False, indent=None):
                tally["unlanded"] += 1
            if tally["n"] % 10 == 0 or tally["n"] == len(todo):
                print("   %5d/%d   scored %d   no-number %d"
                      % (tally["n"], len(todo), tally["scored"], tally["band_only"]),
                      flush=True)

    with ThreadPoolExecutor(max_workers=workers) as ex:
        list(ex.map(work, todo))

    print("")
    print("assayed with a decimal: %d" % tally["scored"])
    print("band-only or refused  : %d" % tally["band_only"])
    if tally["unlanded"]:
        print("checkpoints that did NOT land: %d  (a reader held %s open; those results are "
              "requeued by settled() next run)" % (tally["unlanded"], os.path.basename(OUT)))
    print("-> " + OUT)
    return tally["scored"]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--calibrate", action="store_true",
                    help="run the charter's six published assays")
    ap.add_argument("--one", nargs=2, metavar=("HOST", "ENTITY"))
    ap.add_argument("--batch", action="store_true",
                    help="assay the whole queue, richest evidence first")
    ap.add_argument("--host", help="restrict --batch to one wiki")
    ap.add_argument("--limit", type=int)
    ap.add_argument("--workers", type=int, default=8)
    ap.add_argument("--fresh", action="store_true", help="ignore existing ASSAYS.json")
    a = ap.parse_args()

    if a.calibrate:
        # `calibrate()` returns band_hits, 0-len(BENCHMARKS), not a pass/fail flag -- `if
        # calibrate()` was truthy on ANY nonzero count, so one benchmark out of six reproducing
        # its band exited 0. `standards.py`'s own `charter_regression_verdict` (the check behind
        # "the automation reproduces the charter") requires EVERY scored row consistent, zero
        # `bad`; the exit code here must mean the same thing the standard it feeds does.
        return 0 if calibrate() == len(BENCHMARKS) else 1
    if a.one:
        r = assay_entity(config(), a.one[1], a.one[0])
        print(json.dumps(r, indent=1, ensure_ascii=False)[:4000])
        return 0
    if a.batch:
        run_batch(host=a.host, limit=a.limit, workers=a.workers, resume=not a.fresh)
        return 0
    ap.print_help()
    return 0


if __name__ == "__main__":
    sys.exit(main())
