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
  3. SUBJECT       the entity must be the DOER. Reuses the patient-check that pipeline.py
                   already applies to scale notes, plus a check that another named actor is not
                   standing between the entity and the verb.
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
            silence.note("magnitude.py:151")
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
    """Apply guards 1-4. Returns (scores, worksheet, rejections)."""
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
        cn = _norm(cited)
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

        # 3 SUBJECT -- the entity has to be the doer.
        if P._PATIENT.search(text) or _HANDOFF.search(text):
            rejects.append((ax, f"entity is not the actor: {text[:60]}"))
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
            return ax, {"score": A.UNESTIMABLE, "feat": ""}
        best = None
        i = 0
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
            got = _ask(c, SYSTEM, prompt, AXIS_SCHEMA)
            if not got:
                continue
            sc = got.get("score")
            if isinstance(sc, (int, float)):
                if best is None or not isinstance(best[0], (int, float)) or sc > best[0]:
                    best = (sc, (got.get("feat") or "").strip())
            elif best is None:
                best = (A.UNESTIMABLE, "")
        return ax, ({"score": best[0], "feat": best[1]} if best
                    else {"score": A.UNESTIMABLE, "feat": ""})

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
            "axes": axes_out}


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


def _split_gate(got, cand):
    """Verbatim + relevance gate for split-path sheets. Axis-relevance is by construction
    (each axis was scored only from its own candidate list); verbatim is checked against that
    same list."""
    scores, sheet, rejects = {}, {}, []
    for ax, v in (got.get("axes") or {}).items():
        sc, ft = v.get("score"), (v.get("feat") or "").strip()
        own = {r["feat"] for r in (cand.get(ax) or [])}
        if isinstance(sc, (int, float)) and ft and any(ft in o for o in own):
            # containment one way ONLY: a trimmed copy of a real candidate passes; a fabricated
            # wrapper AROUND a real candidate (o in ft) is the fabrication direction and fails
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
                got = P.ask(c, SYSTEM, prompt, SCHEMA, timeout=420, num_ctx=8192,
                            tag="assay-local")
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
        scores, sheet, rejects = _split_gate(got, cand)
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
                scores, sheet, rejects = _split_gate(got, cand)

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
    """
    c = config()
    print(f"model: {c['model']}\n")
    print(f"{'entity':<20}{'charter':>10}{'assayed':>12}{'band':>7}{'axes':>6}"
          f"{'rej':>5}  worksheet")
    print("-" * 96)
    band_hits, rows = 0, []
    for name, host, band, val, ci, epoch in BENCHMARKS:
        t = time.time()
        sc = SCOPE.scope_for(host) if host else None
        cl = (sc["scope"], sc["ceiling"]) if sc else None
        r = assay_entity(c, name, host, epoch=epoch, ceiling=cl)
        res = r.get("result")
        row = {"entity": name, "host": host, "published": val, "ci": ci, "band": band}
        if not res or res.get("decimal") is None:
            row.update({"status": r.get("status") or "NO_SCORE",
                        "reason": (r.get("reason") or "band only")[:120], "consistent": None})
            rows.append(row)
            print(f"{name:<20}{band + '.' + str(int(val % 1 * 100)):>10}{'--':>12}{'--':>7}"
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
        mark = "OK" if got_band == band else "MISS"
        print(f"{name:<20}{band}.{int(val % 1 * 100):02d}{'':>4}"
              f"{res['moth_number'][2:14]:>12}{mark:>7}"
              f"{len(res['axes_scored']):>6}{len(r.get('rejections', [])):>5}  "
              f"{time.time() - t:.0f}s")
    print("-" * 96)
    print(f"anchor band reproduced on {band_hits}/{len(BENCHMARKS)} published assays")
    out = {"at": time.time(), "model": c["model"], "results": rows}
    with open(os.path.join(HERE, "data", "CHARTER_REGRESSION.json"), "w",
              encoding="utf-8") as f:
        json.dump(out, f, indent=1, ensure_ascii=False)
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
        if NOT_AN_ENTITY.match(r["name"]):
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

    todo = [(h, n, ch) for h, n, ch in queue(host, limit)
            if not settled(done.get(h + "|" + n))]
    print("queue: %d entities, %d already assayed, %d to do"
          % (len(queue(host, limit)), len(done), len(todo)))
    lock = threading.Lock()
    tally = {"n": 0, "scored": 0, "band_only": 0}

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
            tmp = OUT + ".tmp"
            with open(tmp, "w", encoding="utf-8") as f:
                json.dump(done, f, ensure_ascii=False)
            os.replace(tmp, OUT)
            if tally["n"] % 10 == 0 or tally["n"] == len(todo):
                print("   %5d/%d   scored %d   no-number %d"
                      % (tally["n"], len(todo), tally["scored"], tally["band_only"]),
                      flush=True)

    with ThreadPoolExecutor(max_workers=workers) as ex:
        list(ex.map(work, todo))

    print("")
    print("assayed with a decimal: %d" % tally["scored"])
    print("band-only or refused  : %d" % tally["band_only"])
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
        return 0 if calibrate() else 1
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
