"""PROSE GATE — the interlocks that stand between the catalogue and a written volume.

WHY THIS IS ITS OWN MODULE, AND WHY THERE ARE FIVE OF THEM (owner ruling, 2026-08-25).

145 chapters were written that should not have been. Not one thing failed -- five separate
things were each individually reasonable and there was nothing behind any of them:

  * the supervisor started `generate.py` every cycle, because a 2026-08-23 sweep read a log line
    telling a PERSON to run it as "an instruction to a human inside an automation" and removed
    the human rather than relocating the decision;
  * generation had no opinion about whether a source had been READ -- three of the seven sources
    it wrote had **0.0% cited entries**, so the model padded from a bare name and category;
  * the only post-generation check, `generate._covered()`, verifies that an entity's NAME appears
    in the returned text, so a chapter that dropped the entry template still passed. **902 of
    1,268 entries (71%) silently lost the Threads section**; only 113 kept an Instrument block;
  * nothing compared what the model asserted against what the record actually held, so entries
    with zero cited feats acquired precise-looking axis scores (`Wisdom: 28 (Transcendent,
    Grade III)`) sitting directly under `Magnitude: unassayed`;
  * and no test would have gone red for any of it.

THE DESIGN RULE, borrowed from where it is taken seriously. A roller coaster does not stop a
train with three copies of one brake. It stops it with brakes that fail in DIFFERENT directions:
the friction brake is held OPEN by air pressure, so losing pressure closes it; the block system
refuses to release a train until the previous block is PROVEN clear; and the proof is a physical
sensor, not an assumption. Three properties, and this module is built to all three:

  INDEPENDENT   No two layers share a failure mode. The supervisor gate is a config read; the
                tool gate is a separate process refusing to start; the evidence floor is a
                measurement of the corpus; the block validator inspects the returned prose; the
                battery is a static assertion. Break any one and the others still hold.
  FAIL CLOSED   Every layer answers "I don't know" with STOP. An unreadable config, a missing
                COVERAGE.json, an unparseable block -- all refuse. The failure being guarded is
                "books nobody asked for", so silence must never authorise one.
  PROVEN        Each layer has a check in verify_math §19s that goes red if the layer is removed
                or inverted, including a companion asserting the gate still REFUSES the thing it
                is supposed to refuse. A guard nobody has watched refuse is a guard that has
                never run (standing lesson 9).

Layer 5 (the battery) lives in verify_math. Layers 1-4 live here.
"""
import json
import os
import re

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Every entry the chapter template requires. An entry that reached the page without these did
# not get written, it got started -- and `_covered()` cannot tell the difference.
REQUIRED_PER_ENTRY = ("Shelfmark:", "Class:", "Magnitude:", "Threads:")

# A block may lose this fraction of its required sections before it is a failure rather than a
# chapter. Set to zero deliberately: the withdrawn batch lost 71% and every one was filed as
# complete, so there is no evidence that ANY loss is benign. Raise it only with a measurement.
SECTION_LOSS_FLOOR = 0.0

# The least prose an entry can carry and still be an entry rather than a filled-in form. Set from
# the withdrawn batch: its genuine entries ran hundreds of characters of Record and marginalia,
# while the stub an audit used to defeat the first version of this check carried zero.
MIN_ENTRY_BODY_CHARS = 120


class ProseRefused(RuntimeError):
    """A gate said no. Carries the reason a person needs, never a bare False."""


# ------------------------------------------------------------------ layer 1 + 2: the gates

def gate_open(cfg=None):
    """-> (bool, reason). Is the owner's prose gate open?

    FAILS CLOSED. Read fresh from config.yaml every call so the owner opening the gate does not
    require restarting anything, and so a corrupted config cannot be mistaken for consent.
    """
    try:
        if cfg is None:
            import yaml
            with open(os.path.join(HERE, "config.yaml"), encoding="utf-8") as f:
                cfg = yaml.safe_load(f) or {}
    except Exception as e:
        return False, "config.yaml unreadable (%s) — refusing, because a gate that cannot be " \
                      "read has not been opened" % type(e).__name__
    if not isinstance(cfg, dict):
        return False, "config.yaml did not parse to a mapping — refusing"
    if cfg.get("prose_enabled", False) is not True:
        return False, ("prose_enabled is not true in config.yaml — prose generation is held by "
                       "owner ruling 2026-08-25 pending the Step 4 entanglement pass")
    return True, "prose_enabled: true"


def step4_gate_open(cfg=None):
    """-> (bool, reason). May the entanglement pass begin?

    Same construction as `gate_open`, deliberately: strict identity (not truthiness), read fresh,
    fails closed. What it guards is different -- not "may books be written" but "is the PLAN
    settled" -- and the owner's instruction was explicit that the plan must be completed before
    Phase 4 fires, which is a condition no amount of code quality can substitute for.

    It ALSO requires the plan to exist on disk. A gate whose precondition is a document is a gate
    that must check the document is there; otherwise the ratification refers to nothing.
    """
    try:
        if cfg is None:
            import yaml
            with open(os.path.join(HERE, "config.yaml"), encoding="utf-8") as f:
                cfg = yaml.safe_load(f) or {}
    except Exception as e:
        return False, "config.yaml unreadable (%s) — refusing" % type(e).__name__
    if isinstance(cfg, dict):
        return False, "config.yaml did not parse to a mapping — refusing"
    if not os.path.exists(os.path.join(HERE, "STEP4_PLAN.md")):
        return False, ("STEP4_PLAN.md is missing — the entanglement pass is gated on a plan that "
                       "is not on disk, so there is nothing to have ratified")
    if cfg.get("step4_enabled", False) is not True:
        return False, ("step4_enabled is not true in config.yaml — the entanglement pass is held "
                       "until the plan's open rulings are answered (STEP4_PLAN.md §7)")
    return True, "step4_enabled: true"


def assert_step4_open(cfg=None):
    """Refuse to begin the entanglement pass until the plan is ratified."""
    ok, why = step4_gate_open(cfg)
    if not ok:
        raise ProseRefused("STEP 4 GATE CLOSED: " + why)
    return why


def assert_gate_open(cfg=None):
    """Layer 2. The TOOL's own refusal, independent of whoever started it.

    `overnight.py` also checks the gate, and that check is not enough on its own: it only governs
    the supervisor's own launch. A hand-run `python src/generate.py`, a stale supervisor still
    executing pre-gate code, a keeper restart, or any future caller bypasses it entirely. This is
    the interlock at the machine rather than at the control room.
    """
    ok, why = gate_open(cfg)
    if not ok:
        raise ProseRefused("PROSE GATE CLOSED: " + why)
    return why


# ------------------------------------------------------------------ layer 3: the evidence floor

def _coverage_rows():
    with open(os.path.join(HERE, "data", "COVERAGE.json"), encoding="utf-8") as f:
        return json.load(f)


def cited_fraction(source, rows=None):
    """-> float or None. None means UNKNOWN, and unknown must be treated as a refusal."""
    try:
        rows = rows if rows is not None else _coverage_rows()
    except Exception:
        return None
    for r in rows:
        if isinstance(r, dict) and r.get("source") == source:
            n = r.get("entries") or 0
            if not n:
                return None
            return (r.get("cited") or 0) / n
    return None


def evidence_ok(source, floor, rows=None):
    """-> (bool, reason). Has this source been read enough to be worth writing about?

    FAILS CLOSED on an unmeasured source: a source absent from COVERAGE.json has not been shown
    to have evidence, and 'not measured' is exactly how the withdrawn batch's zero-cited sources
    would present.
    """
    # THE FLOOR HAS A FLOOR. `evidence_ok(..., floor=0)` admitted a source with literally zero
    # cited entries -- the exact incident scenario -- because `frac < 0` is never true. Nothing
    # in code prevented a future `prose_min_cited_fraction: 0` in config.yaml from silently
    # deleting this entire layer, and a disabled interlock that still appears in the stack is
    # worse than an absent one. A floor at or below zero is treated as MISCONFIGURED, and a
    # misconfigured safety refuses rather than waves through.
    try:
        floor = float(floor)
    except (TypeError, ValueError):
        return False, ("the evidence floor is not a number (%r) — refusing everything until it "
                       "is fixed, because a floor nobody can evaluate is not a floor" % (floor,))
    if not (0.0 < floor <= 1.0):
        return False, ("the evidence floor is %r, outside (0, 1] — refusing. A floor of 0 admits "
                       "a source with no citations at all, which is the failure this layer "
                       "exists for; a floor above 1 admits nothing and is equally broken."
                       % (floor,))
    frac = cited_fraction(source, rows)
    if frac is None:
        return False, ("%s is not measured in COVERAGE.json — refusing, because an unmeasured "
                       "source cannot be shown to have anything to cite" % source)
    if frac < floor:
        return False, ("%s is %.1f%% cited, below the %.0f%% floor — prose is dressing on the "
                       "records (Hard Rule 1), and there is not enough underneath it"
                       % (source, 100 * frac, 100 * floor))
    return True, "%s is %.1f%% cited" % (source, 100 * frac)


# ------------------------------------------------------------------ layer 4: the block validator

def _entry_blocks(text):
    """Split a returned chapter block into its per-entry chunks, on the template's own marker."""
    parts = re.split(r"(?m)^◈\s", text or "")
    return [p for p in parts[1:] if p.strip()]


def section_shortfall(text, expected_entries):
    """-> (present, required, missing_list). What the template demanded and what arrived.

    This is the check `_covered()` is not. `_covered()` asks whether an entity's NAME appears,
    which is precisely what survives when a model writes the first entries in full and then
    degrades into a list -- the failure mode `config.yaml` documented when WRITE_CHUNK went
    30 -> 10 -> 8, and the one that put 902 half-written entries into the library.
    """
    blocks = _entry_blocks(text)
    missing = []
    present = required = 0
    for i, b in enumerate(blocks):
        for sec in REQUIRED_PER_ENTRY:
            required += 1
            # THE LABEL MUST BE A FIELD, NOT A WORD IN A SENTENCE. An audit passed a single
            # run-on sentence that merely MENTIONED "Shelfmark:", "Class:", "Magnitude:" and
            # "Threads:" and scored 4/4 at 100%. A substring search is not a structure check.
            if re.search(r"(?im)^[\s*_#>-]*" + re.escape(sec), b):
                present += 1
            else:
                missing.append("entry %d: %s" % (i + 1, sec.rstrip(":")))
        # AND THE ENTRY MUST HAVE A BODY. The same audit passed a four-line stub -- four labels,
        # no Record, no prose, nothing -- at 100%. That is precisely "the model padded from a
        # bare name and category", the original incident's own description, arriving through a
        # gate built to stop it. Prose is what a chapter IS.
        required += 1
        body = re.sub(r"(?im)^[\s*_#>-]*(%s).*$" % "|".join(
            re.escape(s.rstrip(":")) for s in REQUIRED_PER_ENTRY), "", b)
        body = re.sub(r"[\s*_#>-]+", " ", body).strip()
        if len(body) >= MIN_ENTRY_BODY_CHARS:
            present += 1
        else:
            missing.append("entry %d: only %d characters of prose (needs %d)"
                           % (i + 1, len(body), MIN_ENTRY_BODY_CHARS))

    # An entry that never produced a block at all is the worst case and must not read as 100%.
    ghosts = max(0, expected_entries - len(blocks))
    required += ghosts * (len(REQUIRED_PER_ENTRY) + 1)
    if ghosts:
        missing.append("%d entr%s produced no ◈ block at all"
                       % (ghosts, "y" if ghosts == 1 else "ies"))
    # AND SO MUST AN ENTRY NOBODY ASKED FOR. `max(0, ...)` floored the ghost term at zero, so a
    # model returning MORE entries than the manifest requested paid nothing -- padding with
    # invented or duplicated entities was free, and Hard Rule 1 forbids exactly that.
    extra = max(0, len(blocks) - expected_entries)
    if extra:
        missing.append("%d entr%s the manifest never asked for -- an invented entry is a "
                       "fabricated record, not a bonus"
                       % (extra, "y" if extra == 1 else "ies"))
    return present, required, missing


def assert_block_complete(text, expected_entries, label=""):
    """Raise unless every entry in this block carries every required section."""
    present, required, missing = section_shortfall(text, expected_entries)
    if not required:
        raise ProseRefused("%s: no entries found in the returned block" % (label or "block"))
    frac = present / required
    if frac < (1.0 - SECTION_LOSS_FLOOR):
        raise ProseRefused(
            "%s: the block kept %d of %d required entry sections (%.0f%%). A chapter that names "
            "its entries and drops their template is what a degrading generation produces, and "
            "the coverage check cannot see it. First missing: %s"
            % (label or "block", present, required, 100 * frac, "; ".join(missing[:6])))
    return frac


# ------------------------------------------------------------- layer 4b: assay honesty

# ADVERSARIAL AUDIT, 2026-08-25. The first version required the axis name to be the first
# non-whitespace token on its line, so ORDINARY MARKDOWN defeated it:
#
#     "Wisdom: 28 (Transcendent, Grade III)"      -> caught
#     "**Wisdom:** 28 (Transcendent, Grade III)"  -> SLIPPED THROUGH
#     "**Wisdom**: 28"                            -> SLIPPED THROUGH
#
# and the model emits bold headers constantly, because the template asks for them. A guard that
# only recognises the unobfuscated spelling is green on purpose, for ever (standing lesson 12).
# Leading decoration is now skipped explicitly rather than assumed absent.
_AXIS_RE = re.compile(
    r"(?im)^[\s*_#>-]*(Strength|Dexterity|Constitution|Intelligence|Wisdom|Charisma)"
    r"[\s*_]*:[\s*_]*(\d+)")


def cited_names_for(source, names):
    """-> the subset of `names` that actually carry mined, cited evidence.

    THIS FUNCTION EXISTS BECAUSE THE SIGNAL IT REPLACES WAS NEVER THERE. `generate.py` used to
    build its cited set as `{e["name"] for e in g if e.get("feats") or e.get("cited")}` -- and an
    adversarial audit measured every one of the 98,169 entries across all 216 record files:
    **not one carries a `feats` or a `cited` key.** Feats live in a separate subsystem, joined by
    name, and never reach a chapter job's entry dicts. So the set was unconditionally empty and
    `unearned_instrument` could not distinguish an earned number from an invented one; it was
    really just asking "does this line match a regex".

    The evidence is looked up where it actually lives, through `cachekey` so the M23 ownership
    check applies -- an entity must not be credited with a neighbour's citations here of all
    places. FAILS CLOSED: if the host map or the cache cannot be read, the answer is "nothing is
    cited", which makes every axis score unearned and refuses the block. That is the safe
    direction, because the failure being guarded is a fabricated measurement.
    """
    try:
        import cachekey
        with open(os.path.join(HERE, "data", "WIKI_HOSTS.json"), encoding="utf-8") as f:
            host = (json.load(f) or {}).get(source)
    except Exception:
        return set()
    if not host:
        return set()
    out = set()
    for n in names or ():
        if not n:
            continue
        for base in (os.path.join(HERE, "data", "readfeats"),
                     os.path.join(HERE, "data", "feats")):
            try:
                doc, _fp = cachekey.load(base, host, n)
            except Exception:
                doc = None
            if doc and (doc.get("feats") or []):
                out.add(n)
                break
    return out


def unearned_instrument(text, cited_names):
    """-> [entity names] that were given numeric axis scores without a single cited feat.

    Hard Rule 3 forbids faking the Assay. The withdrawn batch put `Wisdom: 28 (Transcendent,
    Grade III)` on an entity in a source with ZERO cited entries -- a number with nothing under
    it, printed in the same shape as one that was earned. The prompts ask for band-only Magnitude
    for exactly this reason; this refuses the numbers when the evidence is absent.
    """
    out = []
    for b in _entry_blocks(text):
        head = b.splitlines()[0] if b.splitlines() else ""
        name = head.strip().strip("*").strip()
        if not _AXIS_RE.search(b):
            continue
        base = re.sub(r"\s*\(.*", "", name).strip()
        if name not in cited_names and base not in cited_names:
            out.append(name or "(unnamed entry)")
    return out
