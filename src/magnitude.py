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

STEP 1 ANCHOR. Fix the integer band from the SCALE OF THIS THING'S PRESENCE -- how much of
reality it occupies, pervades, or registers within. Not how dangerous it is.

  M0 a village   M1 a city or nation   M2 a continent   M3 a planet
  M4 a stellar system   M5 star clusters   M6 a galaxy   M7 a universe
  M8 multiverses   M9 metaverses and xenoverses   M10 everything

Presence, not threat. Yggdrasil menaces nobody and its presence runs through the nine worlds --
it anchors by what it spans. A treasure, an institution, an event and a law of nature all have a
scale of presence; most of them have no threat at all, and the ladder's own names are scale
names: Worldshaker, Stellar, Galactic, Universal, Multiversal.

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


def assay_entity(c, entity, host, attestation="Transcribed", epoch=None, ceiling=None):
    ev = F.evidence_for(host, entity)
    cand = candidates(ev)
    if not sum(len(v) for v in cand.values()) and not ev["quantities"]:
        return {"entity": entity, "result": None,
                "reason": "no axis cleared its gate on this entity's own source pages"}

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
        head += "\nEPOCH (score THIS state and no other): " + epoch
    prompt = (head + "\n\nCANDIDATE EVIDENCE, GROUPED BY THE AXIS IT BEARS ON:\n"
              + "\n".join(blocks)
              + "\n\nCite only from an axis's own list. An axis with no list takes a status.")

    got = P.ask(c, SYSTEM, prompt, SCHEMA, timeout=420)
    if not got:
        return {"entity": entity, "result": None, "reason": "ollama failure"}

    anchor = got.get("anchor") if got.get("anchor") in A.LADDER else "M0"
    if ceiling and A.LADDER.index(anchor) > A.LADDER.index(ceiling[1]):
        anchor = ceiling[1]                 # a fiction cannot be out-scaled by its own inhabitant
    ev_v = dict(ev)
    ev_v["feats"] = [flat[k][1] for k in sorted(flat)]
    scores, sheet, rejects = verify(entity, got, ev_v)

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
                  epoch=epoch or got.get("epoch") or "unstamped", worksheet=sheet)
    return {"entity": entity, "host": host, "anchor": anchor,
            "presence": got.get("presence_evidence",
                                got.get("hegemonic_feat", "")), "result": res,
            "worksheet": sheet, "rejections": rejects,
            "candidates": {k: len(v) for k, v in cand.items() if v},
            "quantities_seen": len(ev["quantities"]),
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
    c = config()
    print(f"model: {c['model']}\n")
    print(f"{'entity':<20}{'charter':>10}{'assayed':>12}{'band':>7}{'axes':>6}"
          f"{'rej':>5}  worksheet")
    print("-" * 96)
    band_hits = 0
    for name, host, band, val, ci, epoch in BENCHMARKS:
        t = time.time()
        sc = SCOPE.scope_for(host) if host else None
        cl = (sc["scope"], sc["ceiling"]) if sc else None
        r = assay_entity(c, name, host, epoch=epoch, ceiling=cl)
        res = r.get("result")
        if not res or res.get("decimal") is None:
            print(f"{name:<20}{band + '.' + str(int(val % 1 * 100)):>10}{'--':>12}{'--':>7}"
                  f"{'--':>6}{len(r.get('rejections', [])):>5}  {r.get('reason', 'band only')[:40]}")
            continue
        got_band = res["magnitude"]
        band_hits += (got_band == band)
        mark = "OK" if got_band == band else "MISS"
        print(f"{name:<20}{band}.{int(val % 1 * 100):02d}{'':>4}"
              f"{res['moth_number'][2:14]:>12}{mark:>7}"
              f"{len(res['axes_scored']):>6}{len(r.get('rejections', [])):>5}  "
              f"{time.time() - t:.0f}s")
    print("-" * 96)
    print(f"anchor band reproduced on {band_hits}/{len(BENCHMARKS)} published assays")
    return band_hits


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--calibrate", action="store_true",
                    help="run the charter's six published assays")
    ap.add_argument("--one", nargs=2, metavar=("HOST", "ENTITY"))
    a = ap.parse_args()

    if a.calibrate:
        return 0 if calibrate() else 1
    if a.one:
        r = assay_entity(config(), a.one[1], a.one[0])
        print(json.dumps(r, indent=1, ensure_ascii=False)[:4000])
        return 0
    ap.print_help()
    return 0


if __name__ == "__main__":
    sys.exit(main())
