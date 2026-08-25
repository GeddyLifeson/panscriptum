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
            if sec in b:
                present += 1
            else:
                missing.append("entry %d: %s" % (i + 1, sec.rstrip(":")))
    # An entry that never produced a block at all is the worst case and must not read as 100%.
    ghosts = max(0, expected_entries - len(blocks))
    required += ghosts * len(REQUIRED_PER_ENTRY)
    if ghosts:
        missing.append("%d entr%s produced no ◈ block at all"
                       % (ghosts, "y" if ghosts == 1 else "ies"))
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

_AXIS_RE = re.compile(
    r"(?im)^\s*(Strength|Dexterity|Constitution|Intelligence|Wisdom|Charisma)\s*:\s*(\d+)")


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
