#!/usr/bin/env python3
"""
Autonomous pipeline runner for the Panscriptum.

Runs the project's phases in order, unattended and resumably, driving the local Ollama model
for every step that needs judgment or composition. Designed to survive being left overnight:
each unit of work is checkpointed the moment it completes, so a crash, a reboot, or a Ctrl-C
costs at most one unit.

PHASES
  1  synthesis   per-source: nominate the power ceiling entity and a band-only magnitude,
                 grounded in quoted evidence from the source's own entry text
  2  entrypass   per-entry: correct the category, assign a Magnitude band, assign the
                 encyclopedia topic, and extract scale_note ONLY where the text states a
                 demonstrated feat
  3  weave       cross-source ENTITY RESOLUTION -- "Zeus" becomes one canonical entity with
                 four attestations, not four entries (the charter's Step 4 entanglement)
  4  chain       THE CHAIN OF DEFEATS (Charter S129, X.2 S5) -- extract attested contests,
                 fit Bradley-Terry per connected component, and derive a band for entities
                 that have no feat of their own but are placed by comparison
  5  cosmology   derive universe -> multiverse -> metaverse -> xenoverse -> hyperverse from
                 the resolved entities, bottom-up from evidence
  6  history     write THE HISTORY OF THE OMNIVERSE from the weave + cosmology
  7  shelve      assemble THE ENCYCLOPEDIA OF THE OMNIVERSE: topical A-Z volumes, with
                 Persons of Importance shelved by Magnitude band then A-Z
  8  write       volume prose

Phases 4-8 are declared here but not yet implemented; the orchestrator stops cleanly at the
first unimplemented phase rather than pretending to run it. They are built one per custodian
check-in, tested, while earlier phases are still grinding -- see handoff/AUTONOMOUS_PLAN.md.

STATE
  state/PIPELINE_STATE.json   phase progress + per-unit completion, the resume point
  state/pipeline.log          append-only run log
  handoff/RUN_STATUS.md       machine-written run status, rewritten after every unit
  handoff/HANDOFF.md          hand-written; the defects and the reasoning. NEVER written here.

Usage:
    python3 src/pipeline.py --status
    python3 src/pipeline.py --phase 1
    python3 src/pipeline.py            # run all implemented phases in order, forever
"""
import argparse
import datetime
import glob
import collections
import json
import os
import re
import sys
import time
import traceback
import urllib.request

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RECORDS = os.path.join(HERE, "data/records")
STATE_DIR = os.path.join(HERE, "state")
STATE = os.path.join(STATE_DIR, "PIPELINE_STATE.json")
LOG = os.path.join(STATE_DIR, "pipeline.log")
# THE RUNNER GETS ITS OWN FILE.
#
# This pointed at handoff/HANDOFF.md, which is also the hand-written document that carries every
# defect this project has found and the reasoning that keeps each one from recurring. The runner
# rewrote it after every completed unit, so running the phases destroyed 629 lines of it and
# replaced them with a status table. Nothing failed, nothing warned, and the loss was only
# visible because a later edit could not find its own anchor.
#
# Two authors writing one file, one of them silently clobbering the other, is this project's
# defect in its most literal form. The status is machine-written and belongs in a machine-written
# file; the handoff is written by whoever last understood something and belongs in theirs.
HANDOFF = os.path.join(HERE, "handoff/RUN_STATUS.md")

sys.path.insert(0, os.path.dirname(__file__))
import yaml  # noqa: E402
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


# Phase ladder, revised 2026-08-20 on the owner's architectural correction.
#
# Volumes are organised BY TOPIC ACROSS THE WHOLE OMNIVERSE, never by source IP. "Zeus" is one
# entry in Persons A-Z carrying four attestations (Marvel, God of War, Riordan, Smite), not
# four separate entries in four franchise volumes. Two collections, in dependency order:
#
#   The History of the Omniverse  -- narrative volumes built FROM the weave, whose job is to
#                                    construct the hyper/xeno/meta/multiverse structure by
#                                    connecting the sources to each other
#   The Encyclopedia of the Omniverse -- topical A-Z series drawing on that history:
#                                    Wars A-Z, Persons of Importance A-Z, Relics A-Z,
#                                    Powers A-Z, Weapons A-Z, Media A-Z, Events A-Z
#
# This makes `weave` load-bearing for everything downstream: without cross-source entity
# resolution, a topical volume is just a concatenation of per-IP lists with duplicate subjects.
PHASES = ["synthesis", "entrypass", "weave", "chain", "cosmology", "history", "shelve", "write"]

# Encyclopedia series. Volumes are built from these, across the whole omniverse -- never per
# source IP. Order matters only for reporting.
#
# Weapons vs Relics (owner ruling, 2026-08-20): a relic weapon is still a WEAPON. If its
# attested use is combat it files under Weapons regardless of how sacred or historically
# significant it is, so that a holy sword sits beside ordinary blades rather than being
# separated from them. Relics is therefore the NON-weapon significant-object series.
TOPICS = ["Persons", "Places", "Factions", "Weapons", "Relics",
          "Powers", "Events", "Wars", "Media"]

# Magnitude bands, strongest first. Persons of Importance is shelved BY BAND THEN A-Z
# (owner ruling, 2026-08-20): "Persons of Importance: M7 A-Z", "... M6 A-Z", and so on, with
# unassayed entities in their own trailing series. This is why phase 2 assigns a band to every
# entry and not just to each source's ceiling.
BANDS = ["M10", "M9", "M8", "M7", "M6", "M5", "M4", "M3", "M2", "M1", "M0", "unassayed"]

CATEGORIES = [
    "Persons (named individual characters, real or fictional)",
    "Places & Locations (worlds, regions, cities, planes, ships-as-places)",
    "Vessels & Things (items, vehicles, weapons, artifacts, notable objects)",
    "Factions & Organizations (groups, nations, guilds, companies, orders)",
    "Powers, Abilities & Systems (magic systems, power systems, tech systems, disciplines)",
    "Events (major storyline events, wars, historical turning points within the fiction)",
    "Media (in-fiction media: books, songs, broadcasts, works that exist within the story itself)",
]


# --------------------------------------------------------------------------- infrastructure

def log(msg):
    os.makedirs(STATE_DIR, exist_ok=True)
    stamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    line = f"[{stamp}] {msg}"
    print(line, flush=True)
    with open(LOG, "a", encoding="utf-8") as f:
        f.write(line + "\n")


def load_state():
    if os.path.exists(STATE):
        with open(STATE, encoding="utf-8") as f:
            return json.load(f)
    return {"phase": 1, "done": {}, "failed": {}, "started": None, "units_done": 0}


def save_state(st):
    os.makedirs(STATE_DIR, exist_ok=True)
    tmp = STATE + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(st, f, indent=2, ensure_ascii=False)
    os.replace(tmp, STATE)  # atomic: a crash mid-write must not corrupt the resume point


def cfg():
    with open(os.path.join(HERE, "config.yaml"), encoding="utf-8") as f:
        return yaml.safe_load(f)


def ask(c, system, prompt, schema, retries=2, timeout=None):
    """One structured Ollama call. Returns parsed dict, or None on repeated failure.

    `timeout` deliberately does NOT default to config's request_timeout (1800s). That value is
    sized for volume prose, where a single chapter legitimately runs several minutes. The
    judgment calls here emit a few hundred tokens and should never take minutes -- so a call
    that does is hung, and waiting half an hour to find out would burn a whole unattended
    night on one stuck request. Fail fast, log it, move to the next unit.
    """
    body = json.dumps({
        "model": c["model"], "system": system, "prompt": prompt, "stream": False,
        "format": schema,
        # keep_alive is sent explicitly on EVERY request rather than relying on
        # OLLAMA_KEEP_ALIVE being inherited by whichever process happened to start the
        # server. Getting this wrong is expensive out of all proportion: an unloaded MoE
        # costs ~170s to bring back (measured), against ~12s for the call itself. Belt and
        # braces is correct here.
        "keep_alive": -1,
        "options": {"seed": c.get("seed", 47), "temperature": 0.1,
                    "num_ctx": c.get("num_ctx", 6144)},
    }).encode()
    for attempt in range(retries + 1):
        try:
            req = urllib.request.Request(c["ollama_host"].rstrip("/") + "/api/generate",
                                         data=body,
                                         headers={"Content-Type": "application/json"})
            with urllib.request.urlopen(req, timeout=timeout or 420) as r:
                return json.loads(json.loads(r.read().decode()).get("response", "{}"))
        except Exception as e:
            if attempt == retries:
                log(f"    ollama failed after {retries + 1} tries: {type(e).__name__} {str(e)[:80]}")
                return None
            time.sleep(5 + attempt * 10)


def records():
    out = []
    for p in sorted(glob.glob(os.path.join(RECORDS, "*.json"))):
        try:
            with open(p, encoding="utf-8") as f:
                r = json.load(f)
        except Exception:
            silence.note("pipeline.py:191")
            continue
        if r.get("entries"):
            out.append((p, r))
    return out


def write_record(path, rec):
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(rec, f, indent=2, ensure_ascii=False)
    os.replace(tmp, path)


# ------------------------------------------------------------------------------- phase 1

SYNTH_SYSTEM = """You assess fictional sources for an encyclopedia's power-scale index.

You are given a sample of catalogued entries from ONE source. Identify which entity is the
source's power ceiling -- the single most powerful being or force present -- and assign a
MAGNITUDE BAND.

HARD RULES:
1. Ground every claim in the supplied text. Quote the phrase that justifies your choice in
   `evidence` -- at most 20 words, the quoted fragment only. If the text does not demonstrate
   power, say so and use "unassayed".
0. BE TERSE. `rationale` is ONE short sentence, never a paragraph. Long rationales cost
   generation time and add nothing a reader of `evidence` does not already have.
2. BAND ONLY. Output M0-M10, never a decimal. Decimal Assay scores require a nine-measure
   worksheet against cited feats and are a separate process. Emitting "M4.31" is a fabrication.
3. If no entry shows a demonstrated feat, set ceiling_entity to "" and magnitude "unassayed".
   That is a correct, expected answer for many sources.

MAGNITUDE BANDS:
  M0 Mundane - ordinary human capability
  M1 Heroic - peak human, small-scale combat
  M2 Paragon - superhuman, city-block effects
  M3 Worldshaker - city to continent scale
  M4 Planetary Sovereign - planet-scale power
  M5 Stellar - star or solar-system scale
  M6 Galactic
  M7 Universal
  M8 Multiversal
  M9 Metaversal
  M10 Omniversal / ground-of-being
"""

SYNTH_SCHEMA = {
    "type": "object",
    "properties": {
        "ceiling_entity": {"type": "string"},
        "magnitude": {"type": "string"},
        "evidence": {"type": "string"},
        "rationale": {"type": "string"},
    },
    "required": ["ceiling_entity", "magnitude", "evidence", "rationale"],
}



def _mined_feats(rec):
    """{entity name: [feat sentences]} from whatever the miners have collected for this source.

    Reads the model-read cache first and falls back to the regex-mined one, so this improves on
    its own as `read.py` works through the roll.
    """
    import feats as _F
    out = {}
    try:
        hosts = json.load(open(_F.HOSTS, encoding="utf-8"))
    except Exception:
        silence.note("pipeline.py:261")
        return out
    host = hosts.get(rec["source"])
    if not host:
        return out
    hd = re.sub(r"[^A-Za-z0-9]+", "_", host)[:40]
    for e in rec["entries"]:
        nd = re.sub(r"[^A-Za-z0-9]+", "_", e["name"])[:80] + ".json"
        for base in (os.path.join(HERE, "data", "readfeats"),
                     os.path.join(HERE, "data", "feats")):
            fp = os.path.join(base, hd, nd)
            if not os.path.exists(fp):
                continue
            try:
                with open(fp, encoding="utf-8") as fh:
                    d = json.load(fh)
            except Exception:
                silence.note("pipeline.py:277")
                continue
            fl = [x.get("feat") for x in (d.get("feats") or []) if x.get("feat")]
            if fl:
                out[e["name"]] = fl
                break
    return out


def phase_synthesis(c, st):
    """Per-source ceiling + band. ~186 units, roughly 45s each."""
    # A source that FAILED still had a synthesis block written, with empty fields. Filtering on
    # the block's mere presence therefore made failure permanent: the source could never appear
    # in `todo` again, no matter how many times phase 1 was re-run. Sixty-nine sources sat with
    # `ceiling_entity: ""` and no way back.
    #
    # It also mattered more than a retry usually does. Those sixty-nine include SpongeBob, Mario,
    # Overwatch, Yakuza, Fire Emblem and Gundam -- sources whose ceilings came back empty because
    # phase 1 examined them BEFORE their casts existed, and honestly found no entity to nominate
    # among places and items. They have casts now, so the nomination is worth making again.
    todo = [(p, r) for p, r in records()
            if not (r.get("synthesis") or {}).get("ceiling_entity")]
    log(f"phase 1 synthesis: {len(todo)} sources need a ceiling")
    done_keys = st["done"].setdefault("synthesis", [])

    for path, rec in todo:
        src = rec["source"]
        if src in done_keys:
            continue
        # Feed the entries most likely to carry a feat: longest descriptions first.
        #
        # Sized deliberately. Was 22 entries x 420 chars = ~2,300 input tokens; the ceiling
        # entity is essentially always in the top handful of longest descriptions, so the tail
        # was paying prompt-eval cost for nothing. 14 x 300 is ~1,100 tokens -- less than half
        # -- with no observed change in which entity gets nominated.
        # FEATS FIRST, descriptions only as a fallback.
        #
        # This sampled the longest DESCRIPTIONS, and a description is a wiki lead paragraph --
        # biography, not a deed. It is the identical failure that made entrypass return 99.6%
        # `unassayed`: the evidence gate is looking for an act upon an object and a lead
        # paragraph does not contain one. Overwatch was sampled with twelve of its fourteen
        # slots filled by real characters (Reaper, Soldier: 76, Junker Queen) and still nominated
        # nobody, because what it was shown about them was where they were born.
        #
        # The library now holds mined feats for these same entities. An entity with a feat on
        # record is exactly what a ceiling nomination wants to see, so those go first and carry
        # their feat text with them.
        feats_for = _mined_feats(rec)
        with_feats = [e for e in rec["entries"] if feats_for.get(e["name"])]
        with_feats.sort(key=lambda e: -len(feats_for[e["name"]]))
        rest = sorted((e for e in rec["entries"] if not feats_for.get(e["name"])),
                      key=lambda e: -len(e.get("description", "")))
        sample = (with_feats[:14] or [])[:14]
        if len(sample) < 14:
            sample += rest[:14 - len(sample)]
        lines = []
        for e in sample:
            fl = feats_for.get(e["name"]) or []
            if fl:
                d = " | ".join(re.sub(r"\s+", " ", x)[:150] for x in fl[:3])[:420]
            else:
                d = re.sub(r"\s+", " ", e.get("description", ""))[:300]
            lines.append(f"- {e['name']} [{e.get('type','')}]: {d}")
        prompt = (f"SOURCE: {src}\n\nCATALOGUED ENTRIES (sample of "
                  f"{len(sample)} from {len(rec['entries'])}):\n" + "\n".join(lines) +
                  "\n\nIdentify the power ceiling and magnitude band for this source.")

        got = ask(c, SYNTH_SYSTEM, prompt, SYNTH_SCHEMA, timeout=420)
        if got is None:
            st["failed"].setdefault("synthesis", {})[src] = "ollama failure"
            save_state(st)
            continue

        band = (got.get("magnitude") or "").strip()
        m = re.match(r"^(M(?:10|[0-9]))\b", band)
        if not m and band.lower() not in ("unassayed", ""):
            band = "unassayed"  # reject anything that is not a clean band
        elif m:
            band = m.group(1)
        else:
            band = "unassayed"

        # NO FEAT, NO BAND -- at phase 1 as well as phase 2.
        #
        # This was enforced only in entrypass, and the backscan found the consequence: 70 of 211
        # sources carried a synthesis band whose evidence field was the EMPTY STRING. A source-level
        # ceiling is the anchor every entry in that source is later read against, so an unevidenced
        # one is the most expensive kind of unearned number in the library -- it does not misplace
        # one entity, it tilts a whole shelf.
        _ev = (got.get("evidence") or "").strip()
        if band != "unassayed" and not valid_scale_note(_ev):
            band = "unassayed"

        rec["synthesis"] = {
            "ceiling_entity": (got.get("ceiling_entity") or "").strip(),
            "provisional_magnitude": band,
            "evidence": (got.get("evidence") or "").strip()[:600],
            "rationale": (got.get("rationale") or "").strip()[:900],
            "method": ("Band-only nomination by local model over the source's own catalogued "
                       "text. NOT a Custodial Assay: no nine-measure worksheet, no decimal, "
                       "no confidence interval. Treat as a provisional shelving hint that a "
                       "real Assay pass must confirm."),
            "assessed_at": datetime.datetime.now().isoformat(timespec="seconds"),
        }
        write_record(path, rec)
        done_keys.append(src)
        # A later attempt succeeded, so the earlier failure is no longer true. Without this the
        # failed-set becomes a permanent record of every transient ollama hiccup, and a run that
        # fully recovered still reports twelve casualties -- which is how a healthy pipeline gets
        # mistaken for a damaged one.
        st.get("failed", {}).get("synthesis", {}).pop(src, None)
        st["units_done"] += 1
        save_state(st)
        log(f"  {src[:44]:46s} {band:10s} {rec['synthesis']['ceiling_entity'][:34]}")
        update_handoff(st)

    return True


# ------------------------------------------------------------------------------- phase 2

ENTRY_SYSTEM = """You are correcting catalogue metadata for an encyclopedia. You are given
entries with a name, a type, and a description transcribed from a reference source.

For each entry return:
  * `category` - the correct bucket, as a NUMBER 1-7:
      1 Persons  2 Places  3 Vessels & Things  4 Factions  5 Powers  6 Events  7 Media The commonest
    error to fix is an ability filed as an object: a named technique, transformation, release
    state or process is a POWER, never a Vessel. Vessels & Things means physical objects.
  * `scale_note` - a demonstrated feat of power or scale, ONLY if the supplied description
    actually states one (destruction caused, distance crossed, beings overcome). Quote or
    closely paraphrase the description. If the description shows no feat, return "".
    Do NOT estimate, infer, or import knowledge you have about this entity from elsewhere.
  * `magnitude` - the power band THIS entity's own supplied text demonstrates. Band only.
    Return "unassayed" unless the description states an actual feat. This is the single
    easiest field to get wrong: a description that calls someone "a powerful warrior" or "a
    legendary king" demonstrates NOTHING and is "unassayed". A description that says they
    destroyed a city is M3. Rank the feat, never the reputation.

      M0 ordinary human    M1 peak human      M2 superhuman, city-block
      M3 city to continent M4 planet-scale    M5 star / solar system
      M6 galactic          M7 universal       M8 multiversal
      M9 metaversal        M10 omniversal / ground-of-being

    Most entries are "unassayed" and that is the correct, expected answer. Do not reach for a
    band to avoid saying so -- these bands order the entire encyclopedia, and an inflated one
    files an ordinary soldier next to a god.

  * `topic` - which encyclopedia series this entity belongs to. The volumes are organised by
    TOPIC ACROSS THE WHOLE OMNIVERSE, not by which work it came from.

      Persons  a named individual
      Places   a world, region, city, plane, realm
      Factions a group, nation, order, organisation, or a people/race
      Weapons  an object whose attested use is combat -- INCLUDING relic and sacred weapons.
               A holy sword is a Weapon, not a Relic. If it is wielded to fight, it is here.
      Relics   a NON-weapon object of historical, sacred or reality-affecting significance
      Powers   a magic/tech system, technique, discipline or ability
      Events   a discrete happening within the fiction
      Wars     a sustained armed conflict specifically (a subset of Events, filed separately)
      Media    a work existing INSIDE the fiction (in-universe book, song, broadcast)

BE TERSE. `scale_note` is at most 15 words when present, and "" otherwise -- and "" is the
right answer for most entries. Output length is the dominant cost of this pass: every wasted
word is multiplied by 52,000 entries.

Return one object per input entry, in the same order, keyed by the entry's index.
"""

ENTRY_SCHEMA = {
    "type": "object",
    "properties": {
        "results": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "index": {"type": "integer"},
                    "category": {"type": "integer"},
                    "scale_note": {"type": "string"},
                    "magnitude": {"type": "string"},
                    "topic": {"type": "string", "enum": [
                        "Persons", "Places", "Factions", "Weapons", "Relics",
                        "Powers", "Events", "Wars", "Media"]},
                },
                "required": ["index", "category", "scale_note", "magnitude", "topic"],
            },
        }
    },
    "required": ["results"],
}

ENTRY_BATCH = 20

# A scale_note must record a DEMONSTRATED feat, not a vivid sentence. The model reliably
# ignores this instruction and echoes a fragment of the description instead -- observed:
# "witnesses a past age of flourishing creativity" (a vision, no feat) and "You manifest a
# circular amphitheater with a 50 foot radius" (a utility spell). So the instruction is
# backed by a deterministic filter: a feat names a quantity, a scale, or an act of
# destruction/creation at scale. Anything else is discarded.
# CORRECTED 2026-08-20 after a backscan of 10,574 catalogued entries found that ~90% of assigned
# bands rested on no evidence at all.
#
# The three patterns below were previously OR-ed together, so ANY ONE of them satisfied "no feat,
# no band". The middle one is a list of bare scale nouns, which meant that the phrase
# "resource-rich jungle planet" -- a description of a setting, containing no act by anybody --
# licensed a Magnitude. Measured on the corpus:
#
#     225 banded entries
#       7.1%  carried a number with a unit (and most of those were DATES)
#      38.2%  named a destructive act but no object or quantity
#      54.2%  contained neither an act nor a quantity of any kind
#
# Entries carrying a band on that basis included "one of the cities dedicated to the preservation
# of humanity" at M2, and "primordial cosmic being once called the 'Breaker of Worlds'" at M5 --
# a TITLE, at a band that means the gravitational binding energy of a star.
#
# The gate was testing for scale VOCABULARY. A feat is an ACT UPON AN OBJECT, or a measured
# quantity, and nothing else qualifies. Hence conjunction rather than disjunction.
#
# Real physical units only. "years" is deliberately absent: a date is not a magnitude, and it was
# letting "colonized in 2186" read as quantified evidence. Durations belong to Sustain and are
# scored there from their own worksheet.
_MAGNITUDE = re.compile(
    r"\d[\d,.]*\s*(?:km|kilometers?|kilometres?|miles?|meters?|metres?|light[- ]?years?|"
    r"astronomical units?|au|parsecs?|tons?|tonnes?|kilotons?|megatons?|gigatons?|"
    r"joules?|watts?|newtons?|kelvin|solar masses?|earth masses?|g(?:'s)? of (?:force|accel)"
    r")\b", re.I)

# An act, and a thing of consequence for it to be performed upon.
_ACT = re.compile(
    r"\b(?:destroy|annihilat|obliterat|shatter|erase|unmake|unmade|raze|razed|level(?:l?ed|s)?|"
    r"vapori[sz]|incinerat|disintegrat|sunder|split|cleave|collapse|wipe[ds]? out|"
    r"blow[ns]? (?:up|apart)|conquer|subjugat|reshap|rewr(?:ote|ite|iting)|"
    r"drain|consum|devour)\w*", re.I)
_OBJECT = re.compile(
    r"\b(?:planets?|worlds?|continents?|galax(?:y|ies)|universes?|multiverses?|"
    r"dimensions?|realit(?:y|ies)|stars?|suns?|moons?|solar systems?|timelines?|"
    r"civili[sz]ations?|cities|city|nations?|countries|country|fleets?|armies|army|"
    r"islands?|mountains?|oceans?|realms?|kingdoms?|empires?)\b", re.I)

# The entity must be the AGENT. "must be located, activated, and destroyed to save a planet"
# describes something done TO the subject and was licensing an M3.
_PAST_ACT = (r"destroyed|razed|shattered|obliterated|erased|vapori[sz]ed|annihilated|"
             r"levelled|leveled|consumed|devoured|drained|split|sundered|conquered")
_PATIENT = re.compile(
    # "must be located, activated, and destroyed" -- the intervening words carry commas, which an
    # earlier \w+ run could not cross, so this leaked an M3 for a thing that gets destroyed.
    r"\b(?:must be|to be|can be|was|were|is|are|been|being)\s+(?:[\w,]+\s+){0,5}"
    r"(?:" + _PAST_ACT + r")\b"
    # "stars consumed by Sanguilius" -- a past participle followed by an agent. The subject is
    # what was acted upon; the feat belongs to whoever is named after "by".
    r"|\b(?:" + _PAST_ACT + r")\s+by\b", re.I)

# A reputation is not a deed. "once called the Breaker of Worlds" reports what people say.
_REPUTATION = re.compile(
    r"\b(?:known as|called|titled|named|nicknamed|referred to as|epithet|moniker|"
    r"reputed|rumou?red|said to be|believed to|considered|regarded as|legend(?:s|ary)?"
    r"|myth(?:s|ical)?|prophec"
    # ADDED after the re-pass: the surviving SOURCE ceilings were almost all of the form
    # "GOLB is described as a dimension-spanning entity". A description of a description is not a
    # deed, and these are the most expensive bands in the library -- a source ceiling anchors every
    # entry beneath it, so an unearned one tilts a whole shelf rather than one entry.
    r"|described as|depicted as|portrayed as|presented as|characteri[sz]ed as"
    r"|stated to be|claimed to|purported|allegedly|apparently|seemingly"
    r")\w*", re.I)

_SCALE_PATTERNS = [_MAGNITUDE.pattern, _ACT.pattern, _OBJECT.pattern]   # kept for reference
_SCALE_EVIDENCE = re.compile("|".join(_SCALE_PATTERNS), re.I)

# How close an act must sit to its object to count as acting upon it.
_PROXIMITY = 70


def _act_upon_object(text):
    """An act performed on something of consequence, close enough together to be one claim."""
    for m in _ACT.finditer(text):
        lo = max(0, m.start() - _PROXIMITY)
        window = text[lo:m.end() + _PROXIMITY]
        if _OBJECT.search(window):
            return True
    return False


# Stat-block mechanics. These are RESOLUTION PROCEDURE, not demonstrated acts, and the difference
# is the whole point of the invariant: "each creature within 5 feet must succeed on a Dexterity
# saving throw" describes how an outcome would be adjudicated at a table, and contains no evidence
# whatsoever about what the entity did to a world. A distance in feet inside such a clause is a
# rules radius, not a reach.
#
# Found by audit: 112 scale_notes (2.6%) carried meta-language, and the stat-block ones were
# supplying "scale" made entirely of saving throws and hit points.
_STATBLOCK = re.compile(
    r"\b(saving throws?|hit points?|temporary hit points?|armou?r class|challenge rating|CR \d+"
    r"|proficiency bonus|initiative|stat block|d20|advantage on the roll|spell slots?"
    r"|damage dice|\d+d\d+)\b", re.I)

# Setting words. These contaminate the PHRASING of an otherwise real feat -- "overthrew the Titans
# roughly 500 years before the campaign's start" is a genuine deed wearing one wrong word. The feat
# survives; the wording is flagged so the write phase rephrases rather than the evidence being
# thrown away.
_SETTING_META = re.compile(r"\b(campaign|adventure path|session|the table|module|sourcebook"
                           r"|players?|DMs?|game master)\b", re.I)


def valid_scale_note(text):
    """Keep a scale_note only if it actually evidences scale. Returns '' otherwise.

    Three gates, in order of severity:
      1. too short to say anything
      2. STAT-BLOCK mechanics -- rejected outright; a saving throw is not a feat
      3. no scale evidence at all
    """
    t = (text or "").strip()
    if len(t) < 8:
        return ""
    if _STATBLOCK.search(t):
        return ""

    # A measured quantity stands on its own -- that is what measurement means.
    if _MAGNITUDE.search(t):
        return t

    # Otherwise: an act, upon an object, performed BY the subject, and reported as done rather
    # than as said. All four conditions, because dropping any one of them is what produced a
    # library in which a city's dedication to preserving humanity was worth an M2.
    if not _act_upon_object(t):
        return ""
    if _PATIENT.search(t):
        # The subject is the target, not the doer. An earlier version allowed an escape hatch for
        # notes that ALSO contained an active verb, and it promptly matched "destroyed to save a
        # planet" and let the M3 through. The asymmetry decides it: a false negative costs an
        # honest `unassayed`, a false positive mints a Magnitude nobody earned. Refuse.
        return ""
    if _REPUTATION.search(t) and not _MAGNITUDE.search(t):
        return ""                       # a title or a rumour, not a deed
    return t


def scale_note_needs_rephrase(text):
    """True when a VALID feat is described in contaminated words. Not a rejection -- a flag."""
    return bool(text) and bool(_SETTING_META.search(text))


def phase_entrypass(c, st):
    """Per-entry category correction + grounded scale_note. Multi-day; fully resumable."""
    done_keys = st["done"].setdefault("entrypass", [])
    allrecs = records()
    log(f"phase 2 entrypass: {len(allrecs)} records, {sum(len(r['entries']) for _, r in allrecs):,} entries")


    for path, rec in allrecs:
        src = rec["source"]
        entries = rec["entries"]
        for start in range(0, len(entries), ENTRY_BATCH):
            key = f"{src}#{start}"
            if key in done_keys:
                continue
            batch = entries[start:start + ENTRY_BATCH]
            lines = []
            for i, e in enumerate(batch):
                # 380 -> 240 chars. Classification needs the opening clause ("X is a city in
                # ...", "a technique used by ..."), not the whole lead paragraph. Feats, when
                # present, are almost always stated early too.
                d = re.sub(r"\s+", " ", e.get("description", ""))[:240]
                lines.append(f"[{i}] {e['name']} (type: {e.get('type','')}): {d}")
            # The category list lives in the system prompt only. It used to be repeated here
            # as well, paying ~200 input tokens per call across ~2,600 calls for a list the
            # model already had.
            prompt = (f"SOURCE: {src}\n\nENTRIES:\n" + "\n".join(lines) +
                      f"\n\nReturn results for all {len(batch)} entries.")

            got = ask(c, ENTRY_SYSTEM, prompt, ENTRY_SCHEMA, timeout=600)
            if got is None:
                st["failed"].setdefault("entrypass", {})[key] = "ollama failure"
                save_state(st)
                continue

            for res in got.get("results", []):
                i = res.get("index")
                if not isinstance(i, int) or not (0 <= i < len(batch)):
                    continue
                ci = res.get("category")
                if isinstance(ci, int) and 1 <= ci <= len(CATEGORIES):
                    batch[i]["category"] = CATEGORIES[ci - 1]
                # NEVER DISCARD WHAT THE GATE REJECTED. The first version assigned the gated
                # result straight over the field, so a rejected note left no trace: 51,611
                # entries ended up holding an empty string and ~46,000 candidate feats were
                # destroyed. The cost is not only the feats. It is that the rejection rate
                # became unauditable -- with the raw text gone there is no way to tell a gate
                # that is correctly refusing biography from one that is too tight, which is
                # exactly the question that matters before a Magnitude pass.
                raw = (res.get("scale_note") or "").strip()
                sn = valid_scale_note(raw)
                batch[i]["scale_note"] = sn[:500]
                if raw and not sn:
                    batch[i]["scale_note_rejected"] = raw[:500]
                else:
                    batch[i].pop("scale_note_rejected", None)

                # Band-clamp exactly as phase 1 does: accept only a clean M0-M10, and treat
                # anything else -- prose, a decimal, an empty string -- as unassayed. These
                # bands order the whole Persons series (Mx A-Z), so a malformed value would
                # silently misfile an entity rather than fail loudly.
                mb = (res.get("magnitude") or "").strip()
                m = re.match(r"^(M(?:10|[0-9]))\b", mb)
                band = m.group(1) if m else "unassayed"

                # NO FEAT, NO BAND. A Magnitude with no surviving scale_note behind it is a
                # number with no evidence -- exactly what Charter Part Three's "no worksheet,
                # no number" rule (theorem H5, Vol. X.6) forbids. This caught a utility spell
                # that creates a wooden amphitheater being filed at M2 because the model
                # ranked the building's 50-foot radius as a power feat.
                #
                # These bands shelve the entire Persons series (Mx A-Z), so an unevidenced
                # band does real damage: it files an ordinary character beside a god.
                if not sn:
                    band = "unassayed"
                batch[i]["magnitude"] = band

                topic = (res.get("topic") or "").strip()
                if topic in TOPICS:
                    batch[i]["topic"] = topic
                batch[i]["catalogued"] = True

            write_record(path, rec)
            # A batch is done only when every entry in it carries a result. The model is asked
            # for N and sometimes returns fewer, or returns an out-of-range index that the loop
            # above discards -- and marking the batch done on the WRITE rather than on the
            # RESULT stranded those entries permanently. 95 batches were sitting complete with
            # 378 entries inside them that had never been judged and never would be.
            #
            # An unfinished batch is simply not recorded, so the next run picks it up again. The
            # cost of re-doing a mostly-complete batch is one call; the cost of the old behaviour
            # was silent, permanent data loss.
            if all(e.get("catalogued") for e in batch):
                done_keys.append(key)
            else:
                log(f"    batch {key} returned {sum(1 for e in batch if e.get('catalogued'))}"
                    f"/{len(batch)} - left open for retry")
            st.get("failed", {}).get("entrypass", {}).pop(key, None)   # see phase 1: a later
            # success retires the earlier failure, so the failed-set stays a list of things
            # actually still broken rather than a scar log.
            st["units_done"] += 1
            save_state(st)
        log(f"  {src[:50]:52s} done")
        update_handoff(st)

    return True


# ------------------------------------------------------------------------------- handoff

def update_handoff(st):
    try:
        recs = records()
        total = sum(len(r["entries"]) for _, r in recs)
        with_syn = sum(1 for _, r in recs if r.get("synthesis"))
        catted = sum(1 for _, r in recs for e in r["entries"] if e.get("catalogued"))
        with open(os.path.join(HERE, "data/SWEEP_ROLL.json"), encoding="utf-8") as f:
            roll = json.load(f)
        have = sum(1 for r in roll if r.get("entry_count", 0) > 0)

        phase = st.get("phase", 1)
        name = PHASES[phase - 1] if 1 <= phase <= len(PHASES) else "?"
        fails = sum(len(v) for v in st.get("failed", {}).values())

        md = f"""# PANSCRIPTUM — AUTONOMOUS RUN STATUS

*Rewritten automatically by `src/pipeline.py` after every completed unit.*
*Last update: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}*

## Where the run is

| | |
|---|---|
| Current phase | **{phase} — {name}** |
| Units completed this run | {st.get('units_done', 0):,} |
| Failures logged | {fails} |

## Corpus

| | |
|---|---|
| Sources catalogued | **{have}/215** |
| Records with entries | {len(recs)} |
| Total entries | **{total:,}** |
| Sources with a ceiling nominated (phase 1) | {with_syn}/{len(recs)} |
| Entries through the judgment pass (phase 2) | {catted:,}/{total:,} |

## Phase ladder

| # | phase | state | what it does |
|---|---|---|---|
| 1 | `synthesis` | **built** | per-source power ceiling + magnitude band |
| 2 | `entrypass` | **built** | per-entry category, band, topic, grounded scale_note |
| 3 | `weave` | **built** | cross-source entity resolution + the onomasticon |
| 4 | `chain` | to build | the Chain of Defeats; Bradley-Terry theta per component |
| 5 | `cosmology` | to build | universe → multiverse → metaverse → xenoverse → hyperverse |
| 6 | `history` | to build | *The History of the Omniverse* |
| 7 | `shelve` | to build | the topical A–Z encyclopedia volumes |
| 8 | `write` | to build | volume prose |

Volumes are organised by **topic across the omniverse**, never by source IP.

The runner stops cleanly at the first unimplemented phase rather than faking it.

## Built alongside the pipeline

These run standalone and do not block the sweep.

| module | what it is |
|---|---|
| `verify_math.py` | 237 independent checks across 17 sections; recomputes, never re-calls |
| `derivation.py` | the ledger: every quantity names its parents, or the graph fails |
| `assay.py` `rigor.py` `custodes.py` | the Assay, commensuration, and the ten-Custos college |
| `tiers.py` `sevenfold.py` `grounding.py` | the cosmological tiers and the declared 1–7 shelving |
| `address_space.py` `profile.py` | the shelfmark, and the whole world in one 30-char string |
| `worldseed.py` `burgs.py` | map parameters and settlements by the rank-size rule |
| `navtree.py` `build_terminal.py` | the Registry Terminal (`output/registry_terminal.html`) |
| `audit.py` `cleanup.py` | the backscan and its repairs |
| `tells.py` `style_audit.py` | 138 machine-writing tells; Rule 7 is generated from the list |

## Files

- `state/PIPELINE_STATE.json` — resume point (atomic writes; safe to kill the process)
- `state/pipeline.log` — append-only run log
- `handoff/AUTONOMOUS_PLAN.md` — the full plan for every phase

## Restarting

```
python3 src/pipeline.py            # resumes exactly where it stopped
python3 src/pipeline.py --status   # no work, just report
```

**Run one instance only.** Two concurrent runners both write `PIPELINE_STATE.json` and the same
record files; that happened on 2026-08-21 and the records survived by luck. Check before starting:

```
powershell -Command "Get-CimInstance Win32_Process -Filter \"Name='python.exe'\" | Select CommandLine"
```
"""
        os.makedirs(os.path.dirname(HANDOFF), exist_ok=True)
        tmp = HANDOFF + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            f.write(md)
        os.replace(tmp, HANDOFF)
    except Exception:
        log("  (handoff update failed: " + traceback.format_exc(limit=1).strip() + ")")


def phase_chain(c, st):
    """Phase 4 -- the Chain of Defeats. See chain.py for the reasoning.

    This existed as a standalone module and NOT as a phase, so the runner reached phase 4, found
    no `phase_chain`, and stopped cleanly every single time -- reporting "not implemented yet"
    about a module that was finished and working. Phase 4 only ever ran when somebody invoked it
    by hand, and phases 5 through 8 were never even attempted, because the runner never got past
    the gap. A finished stage that nothing dispatches to is indistinguishable from a stage that
    was never written, which is this project's defect wearing yet another hat.

    Charter Part Three names three kinds of evidence: a witnessed feat, an instrument reading,
    and a suffered defeat. The first two are what phases 1-2 collect. This is the third, and it
    is the only one that CHECKS the others -- if the Assay puts A above B while the source
    records B beating A, that is a defect visible without anyone's opinion.
    """
    import chain as CH
    rows = CH.harvest()
    log(f"phase 4 chain: {len(rows):,} sentences read like a contest outcome")
    if len(rows) < 10:
        log("  too few contests on record to fit anything; leaving the graph empty")
        st["done"].setdefault("chain", []).append("all")
        st["units_done"] += 1
        save_state(st)
        return

    edges, unmatched, prov = CH.extract(rows, workers=c.get("workers", 8))
    edges = CH.adjudicate_mutuals(edges, prov)
    log(f"  {len(edges):,} distinct edges, {sum(edges.values()):,} recorded wins")

    res = CH.fit(edges, prior=0.5)
    if res.get("error"):
        # Ford (1957): the Bradley-Terry MLE exists and is unique only on a strongly connected
        # graph. Refusing is the correct answer, and it is a RESULT -- the edges are kept and the
        # graph is the finding.
        log(f"  no fit: {res['error']} -- the edges stand as the result")
    else:
        log(f"  identified: {res.get('identified')}  components: {len(res.get('components', []))}"
            f"  deviance/df: {res.get('deviance_per_df')}")

    json.dump({"edges": [[a, b, n] for (a, b), n in edges.items()],
               "unmatched": unmatched.most_common(40), "fit": res},
              open(os.path.join(HERE, "data/CHAIN.json"), "w", encoding="utf-8"),
              indent=1, ensure_ascii=False)
    st["done"].setdefault("chain", []).append("all")
    st["units_done"] += 1
    save_state(st)


def phase_cosmology(c, st):
    """Phase 5 -- chart the tiers, and answer the First Argument per cosmos.

    Every piece of this existed and nothing dispatched to it. `tiers.chart` places each source in
    a multiverse, metaverse, xenoverse and hyperverse from the resonance graph phase 3 built;
    `grounding` answers what each cosmos says about its own origin; `cosmography.census` gives the
    population arithmetic; `address_space` turns a tier stack into a real 89-bit address. Four
    finished modules and no phase, so none of it ever ran inside the pipeline.

    What comes out is the shelving skeleton: which universe a thing is in, as a number the Ladder
    can read, instead of the charter's honest-but-empty `omega > ? > ?` placeholder.
    """
    import tiers as T
    import grounding as G
    import cosmography as CG
    import address_space as AS

    # chart() returns a tuple; the first element is the per-source tier stack. Unpacking by
    # position rather than assuming a dict, because assuming cost a TypeError on the first run.
    charted = T.chart()
    if isinstance(charted, tuple):
        charted = charted[0]
    log("phase 5 cosmology: %d sources charted across the tiers" % len(charted))
    json.dump(charted, open(os.path.join(HERE, "data/TIERS.json"), "w", encoding="utf-8"),
              indent=1, ensure_ascii=False)

    grounds = {}
    for src in charted:
        try:
            grounds[src] = G.classify_source(src)
        except Exception:
            silence.note("pipeline.py:phase_cosmology-ground")
            grounds[src] = {"type": G.UNGROUNDED}
    def _kind(v):
        if isinstance(v, dict):
            return v.get("type") or v.get("grounding") or "ungrounded"
        return str(v)
    kinds = collections.Counter(_kind(v) for v in grounds.values())
    log("  grounding: " + ", ".join("%s %d" % (k, n) for k, n in kinds.most_common(6)))
    json.dump(grounds, open(os.path.join(HERE, "data/GROUNDINGS.json"), "w", encoding="utf-8"),
              indent=1, ensure_ascii=False)

    cen = CG.census("STANDARD")
    log("  census: %.3g worlds, %.3g in a habitable zone, %.3g civilisations extant"
        % (cen["exoplanets"], cen["habitable_zone_rocky"], cen["civilizations_extant"]))
    json.dump(cen, open(os.path.join(HERE, "data/CENSUS.json"), "w", encoding="utf-8"),
              indent=1, ensure_ascii=False)

    try:
        seeds = json.load(open(os.path.join(HERE, "data/WORLDSEEDS.json"), encoding="utf-8"))
    except Exception:
        silence.note("pipeline.py:phase_cosmology-seeds")
        seeds = {}
    marks = {}
    for desig in seeds:
        src = desig.split("::")[0]
        addr = AS.assign(desig, charted.get(src) or {})
        marks[desig] = {"address": addr, "shelfmark": AS.shelfmark(addr),
                        "map_seed": AS.map_seed(addr)}
    dupes = len(marks) - len({v["address"] for v in marks.values()})
    log("  addressed %d worlds, %d collision(s)" % (len(marks), dupes))
    json.dump(marks, open(os.path.join(HERE, "data/SHELFMARKS.json"), "w", encoding="utf-8"),
              indent=1, ensure_ascii=False)

    st["done"].setdefault("cosmology", []).append("all")
    st["units_done"] += 1
    save_state(st)


def phase_history(c, st):
    """Phase 6 -- the Chain of Record: how far each shelf lags the registry, and what is
    therefore contemporary with what.

    `tempus` settles a question the Chronicle had been quietly assuming an answer to.
    Simultaneity between universes has no physical referent -- there is no shared frame, so "at
    the same time" means nothing between them. The library's `now` is INSTITUTIONAL: two events
    are contemporary iff they were accessioned together.

    So this computes the accessioning, not a date. Each source's apparent lag from the registry
    comes from X.7's propagation metric over its charted tier stack -- a shelf nested deeper is
    further from the Communion and its news arrives later. Shelves whose lag agrees to within the
    tolerance are contemporary, and that grouping is the only claim about omniversal time the
    charter can actually support.

    Written against tempus's REAL surface. A first draft called `TP.mark()`, which does not
    exist, and reported "0 shelves given an ascension mark" -- a phase that ran, returned an
    empty result, and looked like a finding rather than a wrong call. That is this project's
    signature defect, committed inside a phase written to close it, which is worth leaving in the
    record.
    """
    import tempus as TP
    try:
        tiersd = json.load(open(os.path.join(HERE, "data/TIERS.json"), encoding="utf-8"))
    except Exception:
        silence.note("pipeline.py:phase_history-tiers")
        log("phase 6 history: no charted tiers on disk -- phase 5 has not run")
        tiersd = {}
    if not tiersd:
        st["done"].setdefault("history", []).append("all")
        st["units_done"] += 1
        save_state(st)
        return

    # The registry sits at the apex. A shelf's distance from it is how deep its tier stack goes
    # before a tier is unknown -- an unnested shelf is close to the Communion, a shelf inside a
    # xenoverse inside a hyperverse is far.
    TIER_ORDER = ("hyperverse", "xenoverse", "metaverse", "multiverse")
    # The shelf everything is measured from. The Concordance is a lightcone with an origin, and
    # this is it: the shelf the Communion keeps its register on.
    REGISTRY_SHELF = sorted(tiersd)[0]

    def depth(stack):
        d = 0
        for t in TIER_ORDER:
            if (stack or {}).get(t) is not None:
                d += 1
        return d

    lags, marks = {}, {}
    for src, stack in sorted(tiersd.items()):
        d = depth(stack)
        # apparent_lag_years takes two SHELVES and walks X.7's propagation graph between them --
        # it is not a function of depth. The registry is the reference shelf, so every source is
        # measured against it, and a source with no shared furniture returns a null lag, which is
        # a real answer meaning "the relation is mediated or absent".
        try:
            got = TP.apparent_lag_years(REGISTRY_SHELF, src)
            lag = (got or {}).get("lag_years") if isinstance(got, dict) else got
        except Exception:
            silence.note("pipeline.py:phase_history-lag")
            lag = None
        lags[src] = lag
        marks[src] = {"tier_depth": d, "apparent_lag_years": lag,
                      "grounding": (stack or {}).get("own_grounding")}
    log("phase 6 history: %d shelves placed against the Chain of Record" % len(marks))

    groups = collections.defaultdict(list)
    for src, m in marks.items():
        groups[m["tier_depth"]].append(src)
    biggest = max((len(v) for v in groups.values()), default=0)
    log("  %d contemporaneity classes by ratification depth, largest holds %d shelves"
        % (len(groups), biggest))
    for d in sorted(groups):
        known = [lags[x] for x in groups[d] if isinstance(lags.get(x), (int, float))]
        log("    depth %d: %4d shelves, %d with a measurable lag%s"
            % (d, len(groups[d]), len(known),
               (", median %.0f yr" % sorted(known)[len(known) // 2]) if known else ""))

    # A closed timelike shelf spends no reference time and can therefore never accession. That is
    # a real category in the charter, not an error, and it belongs in the record.
    try:
        loops = TP.loop_report(1000)
    except Exception:
        silence.note("pipeline.py:phase_history-loops")
        loops = None

    json.dump({"marks": marks, "loops": loops,
               "contemporary": {str(k): v for k, v in sorted(groups.items())}},
              open(os.path.join(HERE, "data/CHRONICLE.json"), "w", encoding="utf-8"),
              indent=1, ensure_ascii=False, default=str)
    st["done"].setdefault("history", []).append("all")
    st["units_done"] += 1
    save_state(st)


def phase_shelve(c, st):
    """Phase 7 -- put every entry on a shelf, with a real address and a real spine code.

    This is where the library stops being a database. Each entry takes the charter's
    Collection/Set/Series/Volume spine code and a Ladder-of-Being shelfmark from the address
    space. Everything it needs was built in phases 3 to 6; nothing until now put them together.

    Hard Rule 2 is enforced rather than worked around: about half the roll is not in the charter's
    Acquisitions Index, and inventing a spine code for those is exactly what that rule forbids.
    They are RECORDED as unspined, which is a finding the owner can act on, not a gap.
    """
    import address as AD
    import weave_index as WI

    try:
        marks = json.load(open(os.path.join(HERE, "data/SHELFMARKS.json"), encoding="utf-8"))
    except Exception:
        silence.note("pipeline.py:phase_shelve-marks")
        marks = {}
    try:
        tiersd = json.load(open(os.path.join(HERE, "data/TIERS.json"), encoding="utf-8"))
    except Exception:
        silence.note("pipeline.py:phase_shelve-tiers")
        tiersd = {}

    def spine_of(src):
        try:
            return AD.spine_code_for(src)
        except Exception:
            silence.note("pipeline.py:phase_shelve-spine")
            return None

    shelved, unspined = {}, set()
    for r in WI.load_records():
        src = r["source"]
        spine = spine_of(src)
        if not spine:
            unspined.add(src)
        for e in r.get("entries", []):
            key = "%s::%s" % (src, e.get("name"))
            shelved[key] = {"source": src, "name": e.get("name"),
                            "category": e.get("category"), "spine": spine,
                            "tier": tiersd.get(src),
                            "shelfmark": (marks.get(key) or {}).get("shelfmark")}
    log("phase 7 shelve: %d entries placed, %d source(s) with no charter spine code"
        % (len(shelved), len(unspined)))
    json.dump({"entries": shelved, "unspined": sorted(unspined)},
              open(os.path.join(HERE, "data/SHELVES.json"), "w", encoding="utf-8"),
              indent=1, ensure_ascii=False)
    st["done"].setdefault("shelve", []).append("all")
    st["units_done"] += 1
    save_state(st)


# A source is written when this fraction of its entries is SETTLED -- cited, or read with nothing
# found, which is a real finding rather than a gap. Below it the volume would be mostly silence
# wearing the shape of scholarship.
WRITE_SETTLED_MIN = 0.60


def phase_write(c, st):
    """Phase 8 -- the volumes themselves, and the one thing this library must never do.

    Delegates to `manifest_builder`, which knows which jobs exist, and `generate.py`, which knows
    how to turn a manifest into prose against the house style. This phase's own job is the guard
    rail: it REFUSES to write about a source whose entries have not been read.

    Prose about an entity with no evidence is the single output that would undo everything above
    it. It would be indistinguishable from the cited kind -- same voice, same shelfmark, same
    confident interval -- and the entire apparatus of verbatim checks, host fitness tests and
    honest absences exists to keep that distinction real. A library that writes about what it has
    not read is just a generator with a card catalogue.
    """
    import manifest_builder as MB

    try:
        rows = json.load(open(os.path.join(HERE, "data/COVERAGE.json"), encoding="utf-8"))
    except Exception:
        silence.note("pipeline.py:phase_write-coverage")
        rows = []
    ready, thin = [], []
    for r in rows:
        n = max(r.get("entries", 0), 1)
        settled = (r.get("cited", 0) + r.get("read", 0)) / n
        (ready if settled >= WRITE_SETTLED_MIN else thin).append((settled, r.get("source")))
    log("phase 8 write: %d of %d sources are settled enough to write (>= %d%% read or cited)"
        % (len(ready), len(rows), int(WRITE_SETTLED_MIN * 100)))
    if not ready:
        log("  nothing is ready, and that is a correct outcome rather than a failure:")
        log("  the library does not write about entities nobody has read.")
        st["done"].setdefault("write", []).append("all")
        st["units_done"] += 1
        save_state(st)
        return

    names = sorted({s for _, s in ready if s})
    # The real signature is build_jobs_for_source(cfg, roll_entry, record, spine) -- four
    # arguments, in that order. Calling it with two produced "117 sources would not build",
    # which reads as a property of the sources and was a property of the call.
    cfg = MB.load_config()
    roll = {r.get("source") or r.get("name"): r for r in (MB.load_roll(cfg) or [])}
    jobs, refused = [], []
    for src in names:
        try:
            rec = MB.load_record(cfg, src)
            spine = MB.spine_code_for(src) or MB.provisional_spine(src)
            jobs += MB.build_jobs_for_source(cfg, roll.get(src) or {"source": src},
                                             rec, spine) or []
        except Exception as e:
            silence.note("pipeline.py:phase_write-jobs")
            refused.append("%s (%s)" % (src, type(e).__name__))
    log("  manifest: %d job(s) across %d source(s), %d source(s) would not build"
        % (len(jobs), len(names), len(refused)))
    for r in refused[:5]:
        log("    refused: %s" % r)
    if jobs:
        out = os.path.join(HERE, "output", "index", "manifest.json")
        os.makedirs(os.path.dirname(out), exist_ok=True)
        json.dump(jobs, open(out, "w", encoding="utf-8"), indent=1, ensure_ascii=False)
        log("  -> output/index/manifest.json   (run generate.py against it)")
    st["done"].setdefault("write", []).append("all")
    st["units_done"] += 1
    save_state(st)


def phase_weave(c, st):
    """Phase 3 -- cross-source entity resolution. See weave.py for the reasoning.

    Runs whole-corpus rather than per-source, because identity is a property of the WHOLE
    catalogue: whether Alien's Ripley and Predator's Ripley are one person cannot be decided by
    looking at either shelf alone. It is therefore safe to run before phase 2 finishes -- it reads
    entity NAMES, which entrypass never changes (it only adds bands and topics).

    Two graphs come out, and conflating them was the first draft's error:
      IDENTITY   strict complete-linkage continuities. Mostly singletons: each universe keeps its
                 own Earth, and Earth resolves to ~30 distinct entities rather than one.
      RESONANCE  permissive. Drives X.7 propagation. Diameter 5, mean path 2.04 hops.
    """
    import weave as W
    raw = W.load_index()
    index, dropped = W.filtered_index(raw)
    log(f"phase 3 weave: {len(raw):,} keys, {dropped:,} mechanics dropped")

    occ, idf, sources, N = W.idf_table(index)
    sur, names = W.name_surprisal(index)
    w, shared = W.surprisal_pair_weights(occ, sur)
    thr = W.null_threshold_surprisal(occ, sur, sources, trials=12)
    log(f"  permutation threshold {thr:.1f} over {len(w):,} shelf-pairs")

    groups = W.components(sources, w, thr)
    resolved, homonyms = W.resolve(index, groups)
    res = W.resonance_graph(w, sources)
    log(f"  {len(groups)} continuities | {homonyms:,} homonyms kept apart | "
        f"{sum(1 for v in resolved.values() if v['n_attestations'] > 1):,} fused")
    log(f"  resonance diameter {res['diameter']} hops, six degrees: {res['six_degrees_holds']}")

    json.dump({"threshold": thr, "groups": groups},
              open(os.path.join(HERE, "data/CONTINUITY_GROUPS.json"), "w", encoding="utf-8"),
              indent=2, ensure_ascii=False)
    json.dump(resolved,
              open(os.path.join(HERE, "data/RESOLVED_ENTITIES.json"), "w", encoding="utf-8"),
              indent=2, ensure_ascii=False)
    json.dump({"threshold": thr, "metric": "name-surprisal (bits)", "topology": res,
               "pairs": [{"a": a, "b": b, "weight": round(v, 2),
                          "shared_sample": shared[(a, b)][:6]}
                         for (a, b), v in sorted(w.items(), key=lambda kv: -kv[1])
                         if v >= thr]},
              open(os.path.join(HERE, "data/RESONANCE_GRAPH.json"), "w", encoding="utf-8"),
              indent=2, ensure_ascii=False)

    # The onomasticon belongs to this phase, not a later one: resolution is what reveals that
    # thirty distinct worlds are all called Earth, and a catalogue that knows this and still files
    # them under one name is worse off than before resolution ran.
    import onomast as O
    named = O.name_worlds(resolved)
    json.dump(named, open(os.path.join(HERE, "data/ONOMASTICON.json"), "w", encoding="utf-8"),
              indent=2, ensure_ascii=False)
    endos = len({v["endonym"] for v in named.values()})
    log(f"  onomasticon: {len(named):,} worlds given designations across {endos} carried names")

    st["done"].setdefault("weave", []).append("all")
    st["units_done"] += 1
    save_state(st)
    update_handoff(st)
    return True


# BUILT FROM PHASES, NOT HAND-MAINTAINED.
#
# This was a literal dict of three entries, and it went stale the moment a phase was written
# without somebody remembering to add it here. `chain` was finished, working, and reported by the
# runner as "not implemented yet" for exactly that reason -- so phase 4 only ever ran by hand and
# phases 5 through 8 were never attempted, because the runner stopped at the gap.
#
# Deriving it from PHASES means writing `phase_<name>` IS registering it, and the two can never
# disagree again.
IMPLEMENTED = {i: globals()["phase_" + name]
               for i, name in enumerate(PHASES, 1)
               if "phase_" + name in globals()}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--phase", type=int, default=None)
    ap.add_argument("--status", action="store_true")
    args = ap.parse_args()

    st = load_state()
    if args.status:
        update_handoff(st)
        print(open(HANDOFF, encoding="utf-8").read())
        return

    if st.get("started") is None:
        st["started"] = datetime.datetime.now().isoformat(timespec="seconds")
    c = cfg()
    log(f"pipeline start | model={c['model']} | phase={args.phase or st['phase']}")

    phases = [args.phase] if args.phase else list(range(st.get("phase", 1), len(PHASES) + 1))
    for ph in phases:
        fn = IMPLEMENTED.get(ph)
        if fn is None:
            log(f"phase {ph} ({PHASES[ph-1]}) is not implemented yet -- stopping cleanly.")
            log("Build it, then re-run; state is preserved.")
            break
        st["phase"] = ph
        save_state(st)
        log(f"=== PHASE {ph}: {PHASES[ph-1]} ===")
        try:
            fn(c, st)
        except KeyboardInterrupt:
            log("interrupted -- state saved, safe to resume")
            save_state(st)
            return
        except Exception:
            log("PHASE CRASHED:\n" + traceback.format_exc())
            save_state(st)
            return
        log(f"=== PHASE {ph} COMPLETE ===")
        st["phase"] = ph + 1
        save_state(st)
        update_handoff(st)

    log("runner exiting")


if __name__ == "__main__":
    main()


# ------------------------------------------------------------------ P8: the meta-language ban
#
# "these books should read like in-universe books only, nothing meta about the game they are
# designed for" -- owner, on file. Ground Rule 4 says it, the model ignores it, so it is
# enforced in code like scale_note and the Marginalia cap before it.
#
# This scans GENERATED PROSE ONLY. It must never be run against entries[].description, which is
# transcribed evidence: 7.4% of that text (3,870 entries, concentrated in the D&D homebrew)
# legitimately contains "saving throw" and "hit points" because that is what the source says.
# Evidence is allowed to be meta. The library's own voice is not.
_META_TERMS = re.compile(
    r"\b(?:DMs?|dungeon master|game master|GMs?|player characters?|players?|PCs?|NPCs?"
    r"|tier of play|at your table|the table|adventuring party|session|campaign"
    r"|d20|saving throws?|hit points?|armou?r class|proficiency bonus|initiative"
    r"|challenge rating|CR \d+|stat block|5e|fifth edition|homebrew|sourcebook"
    r"|roll(?:s|ed)? (?:a )?d\d+|advantage on the roll)\b", re.I)


def meta_violations(prose):
    """Return the distinct meta terms found in generated prose. Empty list = clean."""
    return sorted({m.group(0).lower() for m in _META_TERMS.finditer(prose or "")})


def assert_in_universe(prose, where=""):
    """Raise on meta leakage. Callers in the write phase should reject and regenerate rather
    than publish -- a single 'as a DM you might' in a finished volume breaks the frame for
    every entry around it."""
    bad = meta_violations(prose)
    if bad:
        raise ValueError(f"meta-language in generated prose{' at ' + where if where else ''}: "
                         f"{bad}")
    return True
