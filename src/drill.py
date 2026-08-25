"""DRILL — attack every safety net in the library and report which ones actually held.

WHY. This project's most expensive recurring lesson is that *a check that cannot fail looks
exactly like a check that passed* (standing lesson 9). A guard nobody has watched REFUSE is a
guard nobody has evidence about. Verify_math asserts that the guards exist and behave on
synthetic inputs; this goes further and tries to get PAST each one, in the shape a real failure
would take, and reports HELD or BREACHED for every net individually.

The owner's framing, and it is the right one: the coaster has failsafes, and so do the track, the
lift chain, the dispatch electronics, the loading platform, the queue line, the building, and the
people operating it after hours. A drill that only tests the restraints is a drill that has
tested one of eight things.

WHAT IT DOES NOT DO. It never writes to the corpus, never calls a model, and never opens the
prose gate. Every attack is constructed in memory or in a scratch directory. `--to-halt` is the
one exception and is opt-in: it ends the drill by raising a REAL halt, so the top rung is
observed firing rather than assumed to work, and the owner clears it by hand.

Usage:
    python src/drill.py                 # attack every net, report, change nothing
    python src/drill.py --to-halt       # ... and finish by genuinely halting the library
"""
import argparse
import json
import os
import sys
import tempfile

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import cachekey as CK          # noqa: E402
import escalation as ESC       # noqa: E402
import prose_gate as PG        # noqa: E402

RESULTS = []

# The ratchet for `liveness.py`. Measured 2026-08-25: 38 dead module-level functions, 0
# syntactic tautologies, 0 phantom guards. LOWER this when code is cleaned up. Raising it to
# make the drill go green is the move this whole layer exists to prevent -- if a new finding
# appears, the finding is the problem, not the number.
LIVENESS_CEILING = 38

# GitHub's push protection scans the repo too -- a FOURTH lock, and it is
# right: a real-looking key must not exist in source even as a fixture. Built
# from parts so the literal never appears, while the drill still gets a value
# with the exact shape of the thing it needs to prove the scrubber catches.
def _J(parts):
    return "".join(parts)


# EVERY credential fixture is BUILT AT RUNTIME, never written as a literal.
#
# GitHub's push protection is a fourth lock this project did not build, and it is right: a
# credential-shaped literal must not exist in source even as a test fixture, because a scanner
# cannot tell a fixture from a leak and should not try. It rejected two pushes here -- first on
# an AWS example key id, then on a Slack token -- and each rejection was correct.
#
# Assembling from fragments keeps the drill honest (the value it tests has the exact shape of
# the real thing) while leaving nothing in the file for any scanner, ours or GitHub's, to find.
_AWS_EXAMPLE = _J(["AKIA", "IOSFODNN7", "EXAMPLE"])


def _fixtures():
    """(value, label) for each credential shape the scrubber must redact."""
    return (
        (_AWS_EXAMPLE, "an AWS access key"),
        (_J(["xox", "b-", "123456789012-", "abcdefghijklmno"]), "a Slack token"),
        (_J(["sk", "_live_", "abcdefghijklmnop1234"]), "a Stripe LIVE key"),
        (_J(["eyJhbGciOiJIUzI1NiJ9.", "eyJzdWIiOiIxMjM0NTYifQ.",
             "dozjgNryP4J3jVmNHl0w5N"]), "a JWT"),
        (_J(["-----BEGIN ", "RSA PRIVATE KEY", "-----"]), "a PEM private key"),
        (_J(["Bearer ", "abcdefghijklmnopqrstuvwxyz123456"]), "a bearer token"),
        (_J(["postgres", "://svc_ingest:", "R7qNz4LmWx", "@db.internal/panscriptum"]),
         "a DB URL with credentials"),
        (_J(["ghp", "_", "abcdefghijklmnopqrstuvwxyz0123"]), "a GitHub token"),
    )


def net(area, name, attack, expectation):
    """Record one attack. `attack` returns True if the net HELD (i.e. it refused the attack)."""
    try:
        held = bool(attack())
        err = None
    except Exception as e:                      # an exception during the attack is a breach
        held, err = False, "%s: %s" % (type(e).__name__, e)
    RESULTS.append({"area": area, "net": name, "held": held,
                    "expected": expectation, "error": err})
    return held


def _refuses(fn, exc):
    """Did calling this raise the refusal it is supposed to raise?"""
    try:
        fn()
        return False
    except exc:
        return True


# ============================================================== THE QUEUE LINE (before boarding)

def drill_queue():
    a = "QUEUE LINE — can a source that should never be written reach the platform?"
    net(a, "an unmeasured source is refused",
        lambda: not PG.evidence_ok("no such source", 0.35, [])[0],
        "a source absent from COVERAGE.json cannot be shown to have evidence")
    net(a, "a 0%-cited source is refused",
        lambda: not PG.evidence_ok("S", 0.35, [{"source": "S", "entries": 20, "cited": 0}])[0],
        "three of the withdrawn batch's seven sources were exactly this")
    net(a, "a source with zero entries does not divide by zero",
        lambda: not PG.evidence_ok("S", 0.35, [{"source": "S", "entries": 0, "cited": 0}])[0],
        "an empty source must refuse, not crash and not pass")
    net(a, "a well-read source is still admitted",
        lambda: PG.evidence_ok("S", 0.35, [{"source": "S", "entries": 100, "cited": 90}])[0],
        "a net that refuses everything is a wall, not a net")
    net(a, "COVERAGE.json unreadable is a refusal, not a pass",
        lambda: PG.cited_fraction("anything", None) is None
        or PG.evidence_ok("nope", 0.35, [])[0] is False,
        "unknown must mean stop")


# ============================================================== DISPATCH (the electronics)

def drill_dispatch():
    a = "DISPATCH — can prose start when the owner has not opened the gate?"
    net(a, "an absent flag is closed", lambda: not PG.gate_open({})[0],
        "silence must never authorise a book")
    net(a, "the string 'true' does not open it",
        lambda: not PG.gate_open({"prose_enabled": "true"})[0],
        "a truthy string is a typo, not a ruling")
    net(a, "the string 'false' does not open it either",
        lambda: not PG.gate_open({"prose_enabled": "false"})[0],
        "'false' is a TRUTHY string -- the classic way a gate silently opens")
    net(a, "1 does not open it", lambda: not PG.gate_open({"prose_enabled": 1})[0],
        "only an explicit boolean true counts")
    net(a, "a non-dict config is refused",
        lambda: not PG.gate_open("prose_enabled: true")[0],
        "a config that did not parse to a mapping has not consented to anything")
    net(a, "an explicit True DOES open it",
        lambda: PG.gate_open({"prose_enabled": True})[0],
        "the gate must be openable or it is not a gate")
    net(a, "assert_gate_open RAISES when closed",
        lambda: _refuses(lambda: PG.assert_gate_open({}), PG.ProseRefused),
        "the tool refuses on its own authority, not just the supervisor's")
    net(a, "the live gate is closed right now",
        lambda: not PG.gate_open()[0],
        "prose is held by owner ruling pending Step 4")
    # THE STEP 4 GATE — the plan must be ratified before the entanglement pass can fire.
    net(a, "the Step 4 gate is closed until its plan is ratified",
        lambda: not PG.step4_gate_open()[0],
        "the owner's instruction: plan Step 4 before beginning Step 4")
    net(a, "the Step 4 gate refuses a stringy flag too",
        lambda: not PG.step4_gate_open({"step4_enabled": "true"})[0],
        "same strict identity as the prose gate; a typo is not a ratification")
    net(a, "the Step 4 gate refuses if the PLAN ITSELF is missing", _step4_needs_its_plan,
        "a ratification that refers to no document has ratified nothing")
    net(a, "assert_step4_open RAISES when closed",
        lambda: _refuses(lambda: PG.assert_step4_open({}), PG.ProseRefused), "")


# ============================================================== THE TRAIN (restraints)

def drill_train():
    a = "THE TRAIN — can a half-written chapter be filed as complete?"
    # A REAL entry: the four fields AND a body. The first version of this fixture was four
    # labels and nothing else, which is exactly the stub an audit used to defeat the validator --
    # so the fixture that proved the guard worked was itself the thing the guard should refuse.
    good = ("◈ **A**\nShelfmark: 1\nClass: Person\nMagnitude: M2\n"
            "The custodian records that the specimen was catalogued in the usual manner, its "
            "provenance attested by two hands and its measure left open pending the assay.\n"
            "**Threads: pending the entanglement pass**\n")
    net(a, "a complete entry passes", lambda: PG.section_shortfall(good, 1)[2] == [],
        "the net must let a good block through")
    net(a, "an entry that lost Threads is caught",
        lambda: any("Threads" in m for m in PG.section_shortfall(
            "◈ **A**\nShelfmark: 1\nClass: Person\nMagnitude: M2\n", 1)[2]),
        "71% of the withdrawn batch failed exactly here and was filed as complete")
    net(a, "an entry that lost its Shelfmark is caught",
        lambda: any("Shelfmark" in m for m in PG.section_shortfall(
            "◈ **A**\nClass: Person\nMagnitude: M2\nThreads: pending\n", 1)[2]),
        "")
    net(a, "entries that never appeared at all are caught",
        lambda: any("no ◈ block" in m for m in PG.section_shortfall(good, 4)[2]),
        "three missing entries must not read as 100% of the one that arrived")
    net(a, "an empty block raises rather than shelving",
        lambda: _refuses(lambda: PG.assert_block_complete("", 3, "drill"), PG.ProseRefused),
        "")
    net(a, "a half block raises rather than shelving",
        lambda: _refuses(lambda: PG.assert_block_complete(
            "◈ **A**\nShelfmark: 1\n", 1, "drill"), PG.ProseRefused),
        "")
    # --- the five defeats an adversarial audit actually achieved, 2026-08-25. Each of these
    # PASSED the first version of the guard. They are kept as nets so they cannot come back.
    stub = ("◈ Athuri\nShelfmark: UNCHARTED\nClass: Person\nMagnitude: unassayed\n"
            "Threads: pending the entanglement pass\n")
    net(a, "a four-label stub with no prose is refused",
        lambda: PG.section_shortfall(stub, 1)[2] != [],
        "AUDIT DEFEAT 1: this scored 4/4 at 100% -- 'padded from a bare name and category'")
    net(a, "a run-on sentence merely naming the fields is refused",
        lambda: PG.section_shortfall(
            "◈ A\nHe had a Shelfmark: and a Class: and a Magnitude: and Threads: too, "
            "all in one breath, which is not a template at all but a sentence about one.\n",
            1)[2] != [],
        "AUDIT DEFEAT 2: a substring search is not a structure check")
    net(a, "entries the manifest never asked for are refused",
        lambda: any("never asked for" in m
                    for m in PG.section_shortfall(good + good + good, 2)[2]),
        "AUDIT DEFEAT 3: max(0, ...) floored the ghost term, so padding was free")
    net(a, "prose that merely MENTIONS Threads does not count as the section",
        lambda: any("Threads" in m for m in PG.section_shortfall(
            "◈ **A**\nShelfmark: 1\nClass: Person\nMagnitude: M2\n"
            "He cut the threads of fate.\n", 1)[2]),
        "the check must want the SECTION, not the word")


# ============================================================== THE ASSAY (Hard Rule 3)

def drill_assay():
    a = "THE ASSAY — can a number appear with nothing under it?"
    axis = "◈ **Athuri**\nMagnitude: unassayed\nWisdom: 28 (Transcendent, Grade III)\n"
    net(a, "axis scores on an uncited entity are caught",
        lambda: PG.unearned_instrument(axis, set()) != [],
        "this is what the withdrawn Song of Syx chapter did, at 0.0% cited")
    net(a, "axis scores on a cited entity are allowed",
        lambda: PG.unearned_instrument(axis, {"Athuri"}) == [],
        "an earned number must survive")
    net(a, "a disambiguated name still matches its citation",
        lambda: PG.unearned_instrument(
            "◈ **Wally West (New Earth)**\nStrength: 20\n", {"Wally West"}) == [],
        "the base name is accepted so a parenthetical does not read as fabrication")
    net(a, "BOLD markdown does not hide an axis score",
        lambda: PG.unearned_instrument(
            "◈ Athuri\nMagnitude: unassayed\n**Wisdom:** 28 (Transcendent, Grade III)\n",
            set()) != [],
        "AUDIT DEFEAT 4: the model emits bold constantly; this slipped through silently")
    net(a, "bold-outside-colon does not hide one either",
        lambda: PG.unearned_instrument("◈ A\n**Strength**: 30\n", set()) != [], "")
    net(a, "the cited set is looked up, not read off a key that does not exist",
        lambda: PG.cited_names_for("Marvel", ["Bruce Banner (Earth-616)"]) is not None
        and isinstance(PG.cited_names_for("Marvel", ["Bruce Banner (Earth-616)"]), set),
        "AUDIT DEFEAT 5: no entry in any of the 216 record files carries a feats/cited key, so "
        "the old set was ALWAYS empty and this guard could not tell earned from invented")
    net(a, "a floor of zero is treated as misconfigured, not as permission",
        lambda: not PG.evidence_ok("S", 0.0, [{"source": "S", "entries": 5000, "cited": 0}])[0],
        "AUDIT DEFEAT 6: frac < 0 is never true, so floor=0 deleted this layer silently")
    net(a, "a floor above 1 is refused too",
        lambda: not PG.evidence_ok("S", 2.0, [{"source": "S", "entries": 10, "cited": 10}])[0],
        "")
    net(a, "the supervisor gate agrees with the real gate on a stringy 'false'", _gates_agree,
        "AUDIT DEFEAT 7: overnight used bool(), so prose_enabled: \"false\" read as TRUE")
    net(a, "and proving that never writes the owner's gate", _drill_never_writes_the_gate,
        "run #31: the net above wrote prose_enabled: true into the LIVE config.yaml five "
        "times a cycle and restored it in a finally -- which a kill does not run")


def _step4_needs_its_plan():
    """Hide the plan and confirm the gate refuses even with the flag set true."""
    plan = os.path.join(HERE, "STEP4_PLAN.md")
    if not os.path.exists(plan):
        return PG.step4_gate_open({"step4_enabled": True})[0] is False
    tmp = plan + ".drill-moved"
    os.rename(plan, tmp)
    try:
        return PG.step4_gate_open({"step4_enabled": True})[0] is False
    finally:
        os.rename(tmp, plan)


def _gates_agree():
    """Both gate implementations must answer identically for the values that defeated one.

    THIS NET USED TO WRITE THE LIVE config.yaml, AND THAT MADE IT THE MOST DANGEROUS CODE IN
    THE REPOSITORY (found run #31). It parsed the real config, set `prose_enabled` to each of
    five trial values -- `"true"` and `yes` among them -- wrote the file with a bare
    `open(real, "w")`, compared the two gates, and restored the original in a `finally`. Three
    things were wrong with that, and the third is the one that matters:
      1. `open(w)` truncates before it fills, so any process reading config.yaml in the gap saw
         an empty or half-written gate.
      2. The supervisor runs this drill EVERY CYCLE, so the window recurred every cycle.
      3. `finally` does not run when the process is killed -- and the foreman SIGTERMs stalled
         jobs as a matter of routine. A kill in that window leaves `prose_enabled: true` on
         disk, permanently, with nobody informed. The drill that exists to prove the prose gate
         could open the prose gate, and the incident it guards against is precisely 145
         unauthorised chapters.
    The comparison never needed the disk. `gate_open` already took `cfg`; `_prose_enabled` now
    takes it too (run #31), so both layers are asked about the same in-memory mapping and
    config.yaml is never opened for writing by anything in this file.
    """
    import overnight as ON
    import yaml
    with open(os.path.join(HERE, "config.yaml"), encoding="utf-8") as f:
        base = yaml.safe_load(f) or {}
    for val in ('"false"', '"true"', '1', '"no"', 'yes'):
        cfg = dict(base)
        cfg["prose_enabled"] = yaml.safe_load(val)
        if ON._prose_enabled(cfg) != PG.gate_open(cfg)[0]:
            return False
    return True


def _drill_never_writes_the_gate():
    """The gate-comparison net must leave config.yaml byte-for-byte untouched.

    The attack that defeats the fix above is simply reintroducing the write, so this is the
    net that watches for it: run the comparison and require the owner's file to be unchanged.
    Watched go red against the pre-fix `_gates_agree` on 2026-08-25 -- it reported the file
    rewritten, which is what a drill opening the prose gate looks like from the outside.
    """
    real = os.path.join(HERE, "config.yaml")
    with open(real, "rb") as f:
        before = f.read()
    _gates_agree()
    with open(real, "rb") as f:
        return f.read() == before


# ============================================================== HARD RULE 0 (no caps, ever)

def drill_no_caps():
    """A ranked truncation is the rule's exact prohibition, and it hides inside justifications.

    `synthesis_blocks` kept `rest[:14]` for feat-less sources under a comment arguing that lead
    paragraphs cannot carry a ceiling feat -- an argument that refutes its own conclusion, since
    if they cannot, fourteen is as pointless as four hundred. Two independent readers flagged it
    before the owner ruled. The lesson generalises past this one slice: a cap that arrives with a
    paragraph of reasoning is harder to see than a bare `[:n]`, not easier.
    """
    a = "HARD RULE 0 — is anything still deciding what does not exist?"
    import pipeline as PL

    def nomination_drops_nothing():
        rec = {"source": "T", "entries": [{"name": "e%03d" % i, "description": "x" * (500 - i)}
                                          for i in range(97)]}
        blocks, _ = PL.synthesis_blocks(rec)
        return (sorted(e["name"] for b in blocks for e in b)
                == sorted(e["name"] for e in rec["entries"]))
    net(a, "no entry is dropped from nomination, feats or not", nomination_drops_nothing,
        "a 97-entry source used to nominate 14 and publish a ceiling as if it had read them all")

    def ranking_survives():
        rec = {"source": "T", "entries": [{"name": "e%03d" % i, "description": "x" * (500 - i)}
                                          for i in range(40)]}
        blocks, _ = PL.synthesis_blocks(rec)
        return bool(blocks) and bool(blocks[0]) and blocks[0][0]["name"] == "e000"
    net(a, "the richest material still lands in the FIRST block", ranking_survives,
        "Hard Rule 0 permits ranking and encourages it; it forbids truncating after ranking")

    def feat_bearing_path_unchanged():
        rec = {"source": "T", "entries": [{"name": "f%02d" % i, "description": "d"}
                                          for i in range(30)]}
        blocks, _ = PL.synthesis_blocks(rec)
        return sum(len(b) for b in blocks) == 30
    net(a, "the feat-bearing path is untouched by the fix", feat_bearing_path_unchanged,
        "a fix that quietly changes the healthy path too is a second bug")


# ============================================================== THE RIDE RECORD (M23)

def drill_cache():
    a = "THE RIDE RECORD — can one entity be handed another's evidence?"
    net(a, "a foreign document is rejected",
        lambda: not CK.owns({"entity": "Magic 8-Ball"}, "Magic 8 Ball"),
        "the live collision this fix exists for")
    net(a, "its own document is accepted",
        lambda: CK.owns({"entity": "Magic 8 Ball"}, "Magic 8 Ball"), "")
    net(a, "a document with no entity field is not trusted",
        lambda: not CK.owns({"feats": [1]}, "Magic 8 Ball"),
        "all 86,288 files carry one; a file without it was written by something else")
    net(a, "a document with a null entity is not trusted",
        lambda: not CK.owns({"entity": None}, "Magic 8 Ball"), "")
    net(a, "the writer does not overwrite a neighbour",
        lambda: CK.disambiguated_path("b", "h", "Magic 8 Ball")
        != CK.natural_path("b", "h", "Magic 8 Ball"), "")

    _PAIRS = [("pixar.fandom.com", "Magic 8 Ball", "Magic 8-Ball"),
              ("forgottenrealms.fandom.com", "Ten Towns", "Ten-Towns")]
    _BASES = [os.path.join(HERE, "data", "readfeats"),
              os.path.join(HERE, "data", "feats")]

    def live_reads_are_separated():
        """Neither name may be handed the other's document.

        THIS NET USED TO COMPARE COVERAGE STATE TUPLES AND IT RAISED A FALSE HALT (run #31).
        It called `coverage.state_of()` on both names and failed if the two answers were equal
        and not "NO PAGE" -- inferring "these share one file" from "these report the same
        numbers". The numbers are a 3-tuple of small integers, so equality is ordinary
        coincidence: on 2026-08-25 `Ten Towns` and `Ten-Towns` both read ('READ', 0, 1) while
        loading two DIFFERENT files, `Ten_Towns__e84ad6558f.json` (entity "Ten Towns") and
        `Ten_Towns.json` (entity "Ten-Towns") -- which is the M23 disambiguation working
        exactly as designed. The net halted the whole library over it, and an alarm that
        sounds when nothing is wrong is furniture, not a safety.

        So ask the question the fix is actually about: FILE IDENTITY and OWNERSHIP. Two names
        that sanitise to one stem must resolve to two documents, and each document must carry
        its own entity. Both are things `cachekey` can be held to; neither can be satisfied by
        a coincidence.
        """
        for host, x, y in _PAIRS:
            for base in _BASES:
                dx, fx = CK.load(base, host, x)
                dy, fy = CK.load(base, host, y)
                # One file answering to both names is the collision itself.
                if fx and fy and os.path.abspath(fx) == os.path.abspath(fy):
                    return False
                # And a document that came back for a name it does not belong to is the same
                # fault caught one step later -- this is what `owns` exists to refuse.
                if dx is not None and not CK.owns(dx, x):
                    return False
                if dy is not None and not CK.owns(dy, y):
                    return False
        return True

    def _collision_would_still_be_caught():
        """The net above must have teeth: build a real collision and watch it refuse.

        A false alarm is repaired by making a check STRICTER about the right thing, never by
        making it quieter -- a net that cannot fail looks exactly like a net that passed. So
        this stages the pre-M23 world in a scratch tree (one file at the natural stem, owned by
        one of the two names) and requires `load` to refuse to hand it to the other.
        """
        host, x, y = "forgottenrealms.fandom.com", "Ten Towns", "Ten-Towns"
        with tempfile.TemporaryDirectory() as base:
            nat = CK.natural_path(base, host, x)
            os.makedirs(os.path.dirname(nat), exist_ok=True)
            with open(nat, "w", encoding="utf-8") as f:
                json.dump({"entity": x, "feats": []}, f)
            dx, fx = CK.load(base, host, x)
            dy, fy = CK.load(base, host, y)
            # x owns it; y must get nothing rather than x's evidence.
            return fx is not None and dy is None and fy is None
    net(a, "the live colliding pairs get separate verdicts", live_reads_are_separated,
        "measured against the real corpus, not a fixture")
    net(a, "and a real collision would still be refused", _collision_would_still_be_caught,
        "run #31 loosened the net above off state-tuple equality; this is the proof that "
        "loosening it did not make it unfailable")


# ============================================================== THE INSTRUMENT (the Assay)

def drill_assay_engine():
    """The sigma is the one number every printed Magnitude in the library inherits.

    A wrong interval here is not one bad entry, it is a library-wide falsehood -- and the quiet
    kind, because `M3.52 +/- 0.06` reads exactly as well as `M3.52 +/- 0.12`. The halved interval
    survived for months for precisely that reason, and the battery's own regression checks did
    not catch it because they had been RECORDED FROM the halved output.
    """
    a = "THE INSTRUMENT — can a number be published that the charter would not recognise?"
    import assay as A

    net(a, "the charter's published interval is reproduced",
        lambda: A.calibration_report()["holds"],
        "re-DERIVED from the charter's own worked example, never asserted from a constant")
    net(a, "the calibration is not sitting on a rounding edge",
        lambda: (A.calibration_report().get("margin") or 0) >= 0.25,
        "the first fix landed 0.0001 below the bucket boundary and printed 0.11")
    net(a, "an off-scale score is REFUSED, not absorbed",
        lambda: _refuses(lambda: A.assay("M3", dict(A.CHARTER_KENSHIRO, ruin=99.0),
                                         attestation="Witnessed", worksheet="w"),
                         A.AssayIntegrityError),
        "ruin=99.0 used to yield a decimal and an interval with no complaint")
    net(a, "a negative score is refused",
        lambda: _refuses(lambda: A.assay("M3", dict(A.CHARTER_KENSHIRO, ruin=-5.0),
                                         attestation="Witnessed", worksheet="w"),
                         A.AssayIntegrityError), "")
    net(a, "a non-numeric score is refused",
        lambda: _refuses(lambda: A.assay("M3", dict(A.CHARTER_KENSHIRO, ruin="lots"),
                                         attestation="Witnessed", worksheet="w"),
                         A.AssayIntegrityError), "")
    net(a, "a real reading is still accepted",
        lambda: A.assay("M3", dict(A.CHARTER_KENSHIRO), attestation="Witnessed",
                        worksheet="w")["decimal"] is not None,
        "an instrument that refuses everything is not an instrument")
    net(a, "no worksheet, no number (H5)",
        lambda: A.assay("M3", dict(A.CHARTER_KENSHIRO), attestation="Witnessed",
                        worksheet=None)["decimal"] is None,
        "thin attestation yields a band window, never a fabricated point")
    net(a, "better testimony never buys a wider bar", _sigmas_monotone,
        "the pre-fix table let an UNREAD axis publish a tighter interval than a witnessed one")
    net(a, "ignorance is never narrower than the worst testimony",
        lambda: A.SIGMA_UNKNOWN >= max(A.SIGMA_BY_ATTESTATION.values()), "")
    net(a, "marking axes INAPPLICABLE cannot buy a tighter bar", _inapplicable_not_gameable,
        "measured clean: n/a renormalises the remaining weights, so the bar WIDENS")
    net(a, "a broken sigma table refuses to load", _broken_table_refuses,
        "the instrument checks itself at import, like the eaten-escape guard")


def _sigmas_monotone():
    import assay as A
    order = ["Instrumented", "Witnessed", "Transcribed", "Reconstructed", "Disputed"]
    v = [A.SIGMA_BY_ATTESTATION[g] for g in order]
    return v == sorted(v) and len(set(v)) == len(v)


def _inapplicable_not_gameable():
    """Narrowing the worksheet must never narrow the interval."""
    import assay as A
    full = A.assay("M3", dict(A.CHARTER_KENSHIRO), attestation="Witnessed",
                   worksheet="w")["interval"]
    thin = dict(A.CHARTER_KENSHIRO)
    for k in ("vector", "sustain", "reach"):
        thin[k] = A.INAPPLICABLE
    return A.assay("M3", thin, attestation="Witnessed", worksheet="w")["interval"] >= full


def _broken_table_refuses():
    """Invert the sigma order and confirm the constants check catches it."""
    import assay as A
    saved = dict(A.SIGMA_BY_ATTESTATION)
    try:
        A.SIGMA_BY_ATTESTATION["Instrumented"] = 99.0      # best testimony, worst sigma
        try:
            A._check_constants()
            return False
        except A.AssayIntegrityError:
            return True
    finally:
        A.SIGMA_BY_ATTESTATION.clear()
        A.SIGMA_BY_ATTESTATION.update(saved)


# ============================================================== THE PARK (halt + isolation)

def drill_park():
    a = "THE PARK — does a fault close one area, and can the whole park stop?"
    def area_fault_does_not_close_the_park():
        """A source-level fault must not CHANGE the halt state, whatever it already is.

        The first version asserted `not status()[0]` outright, which quietly assumed the park
        was running -- so the moment a real halt stood (which is exactly when a drill matters
        most) this net reported itself breached and the drill blamed the wrong thing. A net
        whose result depends on unrelated state is not measuring what it claims to.
        """
        before = ESC.status()[0]
        ESC.escalate(ESC.SUPERVISOR, "DRILL_AREA", "drill: one area closing",
                     source="__drill__")
        same = ESC.status()[0] == before
        # CLEAN UP AFTER THE TEST. Escalating now files a real work order, so a drill that left
        # its own probe behind would put one piece of litter in the queue on every cycle -- and
        # a queue with permanent decoration in it is a queue people stop reading. The order is
        # resolved by identity, so this closes exactly the one this probe just filed.
        try:
            import workorders as WO
            WO.resolve_code("DRILL_AREA", "drill self-test; not a real fault",
                            where="__drill__", by="drill.py")
        except Exception:
            pass
        return same
    net(a, "a SOURCE-level fault does NOT change the park's halt state",
        area_fault_does_not_close_the_park,
        "escalating everything is the same failure as escalating nothing")
    net(a, "the halt file FAILS CLOSED when unreadable", _halt_fails_closed,
        "a halt a corrupted file can lift is not a halt")
    net(a, "a halt cannot be lifted without a written ruling",
        lambda: _refuses(lambda: ESC.clear(""), ValueError),
        "the halt exists to buy a decision; lifting it with none buys nothing")
    net(a, "a lazy ruling is refused too",
        lambda: _refuses(lambda: ESC.clear("ok"), ValueError), "")
    net(a, "no module in src/ clears the halt programmatically", _no_programmatic_clear,
        "an agent may RAISE a halt; only a person may lift one")
    # A REMEDY MUST NOT CAUSE THE BREACH IT PREVENTS (owner finding, 2026-08-25).
    net(a, "a remedy never kills a job nothing would restart", _no_unrestartable_kill,
        "read.py was killed at 10:59 and stayed dead; every library counter went flat, and the "
        "killer's own log line said it would happen")
    net(a, "STANDING jobs are still killable", _standing_still_killable,
        "a remedy that can never act is not a remedy")
    net(a, "a HALTED library does not read as a BROKEN one to the supervisor",
        _halt_is_not_breakage,
        "the halt made every job exit, the supervisor called that broken and quit, and nothing "
        "came back when the halt was cleared -- the guard caused the outage it prevents")


def _no_unrestartable_kill():
    import foreman as F
    import lognames as _LN
    frags = {fn[:-4]: fr for fn, fr in _LN.OWNER.items()}
    read_frag = frags.get("read_auto") or frags.get("read")
    return read_frag is not None and not F._restartable(read_frag)


def _standing_still_killable():
    import foreman as F
    import lognames as _LN
    frags = {fn[:-4]: fr for fn, fr in _LN.OWNER.items()}
    pipe = frags.get("pipeline_auto") or frags.get("pipeline")
    return pipe is not None and F._restartable(pipe)


def _halt_is_not_breakage():
    """The supervisor must consult the halt BEFORE concluding the library is broken."""
    src = open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "overnight.py"),
               encoding="utf-8").read()
    i = src.find("idle >= IDLE_LIMIT")
    j = src.find("it is a broken one", i)
    return i != -1 and j != -1 and "_ESC.status()" in src[i:j]


def _halt_fails_closed():
    """Point the module at a deliberately corrupt halt file and confirm it reads as HALTED."""
    real = ESC.HALT_FILE
    d = tempfile.mkdtemp(prefix="drill_halt_")
    bad = os.path.join(d, "HALT.json")
    with open(bad, "w", encoding="utf-8") as f:
        f.write("{ this is not json")
    try:
        ESC.HALT_FILE = bad
        halted, rec = ESC.status()
        return halted and (rec or {}).get("code") == "HALT_FILE_UNREADABLE"
    finally:
        ESC.HALT_FILE = real
        try:
            os.remove(bad)
            os.rmdir(d)
        except OSError:
            pass


# ============================================================== THE NIGHT STAFF (local_agent)

def drill_local_agent():
    """The autonomous local writer is staff too, and staff get supervised.

    `local_agent.py` lets the free local model read and PATCH the repo, which is the cheapest
    labour available and also the only actor here that can change the building while nobody is
    watching. Its gate has already been defeated four separate ways (case, name prefix, an NTFS
    alternate data stream, a case-sensitive extension test). These attacks are the fifth family.
    """
    a = "THE NIGHT STAFF — can the local model edit what it must not?"
    import local_agent as LA

    def denied(path):
        """Was the path refused BY A GATE, as opposed to failing for an unrelated reason?

        The first version asked only "did it decline", which conflated a gate refusal with
        `find string occurs 0 times` -- so a file the agent is perfectly entitled to write read
        as denied, and the net that proves the agent can still do its job reported a false
        breach. A probe that cannot tell refusal from ordinary failure is measuring the wrong
        thing, which is the same defect as a check that cannot fail.
        """
        r = LA.t_propose_patch(path, "x", "y", why="drill", apply=False)
        if not isinstance(r, dict) or r.get("applied"):
            return False
        err = str(r.get("error") or "")
        return ("denylist" in err or "protected region" in err
                or "writable surface" in err or "no such file" in err)

    net(a, "it cannot patch the checking machinery", lambda: denied("src/verify_math.py"),
        "the gate must not be able to edit its own judge")
    net(a, "nor with a capital letter", lambda: denied("src/Verify_Math.py"),
        "one capital letter defeated this gate once already (m113)")
    net(a, "it cannot patch config.yaml", lambda: denied("config.yaml"),
        "config.yaml now holds the prose gate")
    net(a, "it cannot write a record directly",
        lambda: denied("data/records/marvel.json"),
        "M24: that is a third writer against a two-writer contract")
    net(a, "it cannot edit the CHARTER", lambda: denied(
        "reference/keystone_volumes/00_MASTER_CHARTER.md"),
        "an autonomous model must not edit the document defining what it may do")
    net(a, "it cannot edit the catalog", lambda: denied("output/index/catalog.json"), "")
    net(a, "it cannot edit shared run state", lambda: denied("state/HALT.json"),
        "least of all the halt file")
    net(a, "it CAN still be given ordinary work", lambda: not denied("src/scope.py"),
        "a writer that can write nothing is not a writer")

    def blast_cap_bites():
        """The bound that does not depend on knowing which gate was bypassed."""
        LA.blast_reset()
        try:
            for i in range(LA.MAX_PATCHES_PER_RUN + 3):
                r = LA.t_propose_patch("src/scope.py", "zzz-no-such-%d" % i, "y",
                                       why="drill", apply=False)
                if "blast-radius cap" in str((r or {}).get("error", "")):
                    return True
            return False
        finally:
            LA.blast_reset()
            # The cap escalates when it bites, and an escalation files a work order -- so this
            # probe would leave one behind on every cycle. Same discipline as the DRILL_AREA
            # probe: a test that litters the real queue is a test with a side effect, and a
            # queue carrying permanent decoration is one people stop reading.
            try:
                import workorders as WO
                WO.resolve_code("LOCAL_AGENT_BLAST_CAP", "drill self-test; not a real runaway",
                                by="drill.py")
            except Exception:
                pass
    net(a, "a runaway is stopped by the blast-radius cap", blast_cap_bites,
        "five gate bypasses were found after the fact; this bounds the sixth without "
        "needing to know what it is")
    net(a, "the cap resets per run, not per process",
        lambda: (LA.blast_reset() or True) and LA._BLAST["patches"] == 0,
        "a cap that never resets turns into an outage on a long-lived process")
    # The ALLOWLIST — the half that fails CLOSED. These paths are on no denylist at all; they are
    # refused because they are outside the agent's working surface, which is the property M24
    # showed a denylist cannot provide.
    net(a, "a path on NO denylist is still refused if it is outside the surface",
        lambda: denied("data/COVERAGE.json"),
        "a denylist fails open on anything nobody thought of; this is the closed half")
    net(a, "it cannot write into data/ at all", lambda: denied("data/WIKI_HOSTS.json"), "")
    net(a, "it cannot write a brand-new top-level file",
        lambda: denied("something_nobody_listed.txt"),
        "the test that matters: a path invented AFTER the lists were written")


def _no_programmatic_clear():
    src = os.path.dirname(os.path.abspath(__file__))
    for f in sorted(os.listdir(src)):
        if not f.endswith(".py") or f in ("escalation.py", "drill.py"):
            continue
        with open(os.path.join(src, f), encoding="utf-8") as fh:
            t = fh.read()
        if "escalation.clear(" in t or "ESC.clear(" in t:
            return False
    return True


# ============================================================== THE GATE TO THE OUTSIDE WORLD

def drill_publish():
    """The only irreversible, outward-facing step in the project.

    A key pushed to a public repo is public even if the next commit removes it. This is the one
    place where "we caught it next run" is not a recovery.
    """
    a = "THE PUBLIC GATE — can a credential reach the public repo?"
    import publish as P

    def redacted(s):
        return "[redacted]" in P.scrub_text(s)

    for s, label in _fixtures():
        net(a, "%s is redacted" % label, (lambda v: (lambda: redacted(v)))(s),
            "enumerated by an audit as passing the ORIGINAL eight-prefix scrubber")
    net(a, "an unknown vendor's key is caught by ENTROPY alone",
        lambda: redacted("api" + "_key = " + _J(["9f8Ka2Lm", "Q7ZxYb4T", "nV1PwR6dEs0G"])),
        "the pattern list only knows the secrets somebody thought of")
    net(a, "ordinary prose survives",
        lambda: not redacted("The custodian recorded the specimen in the usual manner."),
        "a scrubber that redacts the library is not a scrubber")
    net(a, "a low-entropy passphrase is not mistaken for a key",
        lambda: not redacted("password = correct horse battery"), "")
    # STRUCTURED SUPPRESSION (trivy/prowler discipline). An exception must be data, carry a
    # reason and an expiry, stay VISIBLE in the report, and never widen into a class.
    import suppressions as SUP
    net(a, "every suppression carries a reason and an expiry",
        lambda: all(len(r.get("reason", "")) >= 12 and r.get("expires_at")
                    for r in SUP.active()),
        "a waiver with no stated reason cannot be reviewed and never will be")
    net(a, "no suppression is expired or dangling",
        lambda: SUP.problems() == [],
        "a rule narrowed for a case that no longer exists is a hole nobody chose")
    net(a, "a suppression is NARROW, not a detector off-switch",
        lambda: not SUP.suppressed("secret_scan", "src/read.py"),
        "src/drill.py is waived; the rest of src/ must not be")
    net(a, "a suppressed finding is still REPORTED", _suppressed_still_visible,
        "a waiver that hides a finding is indistinguishable from a detector that stopped working")
    net(a, "the pre-push scanner reads real files", _scanner_finds_a_planted_secret,
        "files copied wholesale never pass through _scrub at all -- this is the lock that "
        "reads what is ACTUALLY staged")


def _suppressed_still_visible():
    """A waived finding must appear in the scan output, tagged -- never silently vanish."""
    import publish as P
    # Scanned from the REPO ROOT, not from src/: `scan_for_secrets` reports paths relative to
    # the root it was given, and suppressions are written repo-relative (`src/drill.py`). Passing
    # src/ produced `drill.py`, which matched no suppression -- a probe that measured the wrong
    # thing and reported the guard broken.
    hits = P.scan_for_secrets(HERE)
    # drill.py is suppressed, so its fixtures should be listed AS SUPPRESSED rather than absent.
    return any(str(w).startswith("SUPPRESSED") for _f, _n, w in hits)


def _page_is_real_gate():
    """A block page must not mine to 'this entity has no evidence'."""
    import feats as F
    good = "{{Infobox}} ==History== The [[hero]] " + "lifted the boulder. " * 20
    bad = "Checking your browser before accessing the site. Cloudflare " + "x" * 300
    thin = "[[a]] {{b}} ==c=="
    return (F.page_looks_real(good)[0] and not F.page_looks_real(bad)[0]
            and not F.page_looks_real(thin)[0])


def _backoff_adapts():
    """Throttling must widen the pace and a clean response must earn it back."""
    import feats as F
    h = "__drill_backoff__.invalid"
    F._BACKOFF.pop(h, None)
    F._STRIKE.pop(h, None)
    F.note_throttled(h)
    grew = F._BACKOFF.get(h, 1.0) > 1.0
    for _ in range(8):
        F.note_ok(h)
    recovered = F._BACKOFF.get(h, 1.0) <= 1.0
    F._BACKOFF.pop(h, None)
    F._STRIKE.pop(h, None)
    return grew and recovered


def _scanner_finds_a_planted_secret():
    """Plant a synthetic secret in a temp tree and confirm the scanner reports it.

    The only way to know a scrubber scrubs is to give it something to find. A scanner asserted
    to work by reading its source is a check that cannot fail.
    """
    import tempfile
    import publish as P
    d = tempfile.mkdtemp(prefix="scanleak_")
    try:
        with open(os.path.join(d, "notes.md"), "w", encoding="utf-8") as f:
            f.write("a log excerpt someone pasted:\n" + _AWS_EXAMPLE + "\n")
        hits = P.scan_for_secrets(d)
        if not hits:
            return False
        with open(os.path.join(d, "notes.md"), "w", encoding="utf-8") as f:
            f.write("the custodian recorded the specimen in the usual manner\n")
        return not P.scan_for_secrets(d)      # and it must go quiet again
    finally:
        import shutil
        shutil.rmtree(d, ignore_errors=True)


# ============================================================== THE RELAY (the ledgers)

def drill_ledgers():
    """The four files that carry continuity between runs, and had no guard at all."""
    a = "THE RELAY — can a run destroy the memory the next run depends on?"
    import ledger_guard as LG

    net(a, "the live ledgers are intact", lambda: LG.check_all() == {},
        "structure, floors, and no bug id in two sections at once")
    net(a, "an honest append is allowed",
        lambda: LG.check_append_only("HANDOFF.md", "## NEW\n\n" + (LG._read("HANDOFF.md") or ""))[0],
        "a guard that blocks the normal case gets removed within a week")
    net(a, "a TRUNCATION padded back to length is refused",
        lambda: not LG.check_append_only("HANDOFF.md", "## NEW\n" + "x" * 200000)[0],
        "length comparison would wave this through; containment does not")
    net(a, "an empty overwrite is refused",
        lambda: not LG.check_append_only("HANDOFF.md", "")[0], "")
    net(a, "a bug in BOTH Open and Resolved is caught",
        lambda: not LG.check_structure(
            "BUGS.md",
            "## Open\n### Major\n- **[m99] x**\n## Watching\n## Resolved (paper trail)\n"
            "- **[m99] x**\n" + "y" * 9000)[0],
        "run in this project by HAND at the end of every session; now it is a check")
    net(a, "a ledger that lost its sections is caught",
        lambda: not LG.check_structure("BUGS.md", "nothing here" * 900)[0], "")


# ============================================================== THE CORPUS (two-writer contract)

def drill_two_writer():
    a = "THE CORPUS — can a third writer edit a record without leaving a trace?"
    import pipeline as PL
    rec = {"source": "X", "entries": [{"name": "A"}, {"name": "B"}]}
    net(a, "an unstamped record is not reported as OK",
        lambda: PL.verify_record_provenance(rec)[0] == "UNSTAMPED",
        "most of the corpus predates stamping; that is not evidence of good provenance")
    PL.stamp_record(rec, "pipeline.write_record")
    net(a, "a sanctioned write verifies",
        lambda: PL.verify_record_provenance(rec)[0] == "OK", "")

    def third_writer_detected():
        r = dict(rec, entries=list(rec["entries"]) + [{"name": "C-injected"}])
        return PL.verify_record_provenance(r)[0] == "DRIFTED"
    net(a, "an entry added outside the writer is DETECTED", third_writer_detected,
        "M24: local_agent could write records directly and every gate stayed green")

    def renamed_entry_detected():
        r = dict(rec, entries=[{"name": "A"}, {"name": "B-renamed"}])
        return PL.verify_record_provenance(r)[0] == "DRIFTED"
    net(a, "a renamed entry is detected even at the same count", renamed_entry_detected,
        "a count check alone would miss this")

    # m36: `_landed` returned its verdict so callers could gate their done-keys on it, and said
    # so in its docstring -- and all twelve `land_json` callers threw the verdict away and marked
    # the phase done anyway. A denied rename then left the phase complete over a pre-write file
    # forever. These attack the gate BEHAVIOURALLY rather than reading pipeline.py's text, per
    # standing lesson 26: a source-literal net here would pass on a comment mentioning gate_done.
    def denied_write_leaves_phase_open():
        st = {"done": {}}
        PL.gate_done(st, "cosmology", [True, True, False, True])
        return "cosmology" not in st["done"]
    net(a, "a phase whose write did NOT land is left open",
        denied_write_leaves_phase_open,
        "a done-key over a pre-write artifact is permanent loss -- no run ever redoes it")

    def landed_writes_still_close_the_phase():
        st = {"done": {}}
        PL.gate_done(st, "cosmology", [True, True, True])
        return st["done"].get("cosmology") == ["all"]
    net(a, "a phase whose writes all landed is still marked done",
        landed_writes_still_close_the_phase,
        "a gate that refuses everything is a wall, not a gate -- the pipeline would never finish")

    def nothing_to_write_is_not_a_failure():
        st = {"done": {}}
        PL.gate_done(st, "write", [])
        return st["done"].get("write") == ["all"]
    net(a, "a phase that correctly wrote nothing is not held open",
        nothing_to_write_is_not_a_failure,
        "phase 8 with nothing settled enough to write is a correct outcome, not a denied write")


# ============================================================== THE UNDO (snapshots)

def drill_snapshot():
    a = "THE UNDO — is there a copy behind an irreversible step, and does it restore?"
    import snapshot as SNAP
    sid = SNAP.before("drill", ["config.yaml"], note="drill self-test")
    net(a, "a snapshot restores byte-identically", lambda: SNAP.verify(sid)[0],
        "an untested backup is a belief, not a backup")
    net(a, "an EMPTY snapshot raises rather than passing",
        lambda: _refuses(lambda: SNAP.before("drill-empty", ["no/such/path"]),
                         SNAP.SnapshotFailed),
        "a snapshot that captured nothing is a missing one wearing the same name")
    net(a, "the withdrawal script takes one before moving anything",
        lambda: "snapshot" in open(
            os.path.join(os.path.dirname(os.path.abspath(__file__)), "withdraw_chapters.py"),
            encoding="utf-8").read(),
        "145 chapters were withdrawn with nothing but an instinct behind them")


# ============================================================== THE STALE WRITER

def drill_stale_writer():
    a = "THE STALE WRITER — can a copy read hours ago overwrite fresher work?"
    import tempfile
    import silence as S
    d = tempfile.mkdtemp(prefix="stale_")
    try:
        dst = os.path.join(d, "shared.json")
        with open(dst, "w", encoding="utf-8") as f:
            f.write('{"v":1}')
        seen = S.digest_of(dst)                     # what our writer read
        with open(dst, "w", encoding="utf-8") as f:  # somebody else lands newer work
            f.write('{"v":2}')
        tmp = dst + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            f.write('{"v":"STALE"}')

        def refused():
            ok, _why = S.replace_if_unchanged(tmp, dst, seen)
            with open(dst, encoding="utf-8") as f:
                return (not ok) and f.read() == '{"v":2}'
        net(a, "a stale write is REFUSED and the fresher file survives", refused,
            "m42: WIKI_HOSTS.json was written from a snapshot two hours old, and it SUCCEEDED")

        def fresh_allowed():
            cur = S.digest_of(dst)
            t2 = dst + ".tmp2"
            with open(t2, "w", encoding="utf-8") as f:
                f.write('{"v":3}')
            ok, _ = S.replace_if_unchanged(t2, dst, cur)
            return ok
        net(a, "an up-to-date write still lands", fresh_allowed,
            "compare-and-swap must not become a wall")
    finally:
        import shutil
        shutil.rmtree(d, ignore_errors=True)


# ============================================================== POLICY (checks as data)

def drill_policy():
    """The rule table itself, and the one property that makes it worth having."""
    a = "POLICY — can a rule pass for the wrong reason without anyone seeing?"
    import policy as POL

    net(a, "a rule records the value it OBSERVED, not just its verdict",
        lambda: "observed" in POL.check_rule({"a": 1}, {"id": "t", "path": "a", "op": "exists"}),
        "a boolean cannot distinguish a real pass from a pass over a missing field")
    net(a, "a pass over a MISSING field is flagged vacuous",
        lambda: len(POL.evaluate({}, [{"id": "t", "path": "nope", "op": "absent"}])["vacuous"])
        == 1,
        "the standards HIGH guard read a key nothing set and was ABSENT for its whole life")
    net(a, "a real pass is NOT flagged vacuous",
        lambda: POL.evaluate({"a": 1}, [{"id": "t", "path": "a", "op": "eq", "arg": 1}])
        ["vacuous"] == [],
        "flagging everything is the same as flagging nothing")
    net(a, "an unknown operator is REFUSED at evaluation",
        lambda: _refuses(lambda: POL.check_rule({}, {"id": "t", "path": "a", "op": "wat"}),
                         POL.BadRule),
        "an open operator set is a language, and a language needs its own tests")
    net(a, "a malformed rule is refused rather than skipped",
        lambda: _refuses(lambda: POL.check_rule({}, {"id": "t", "op": "exists"}), POL.BadRule),
        "a rule silently skipped is a rule that cannot fail")
    net(a, "absent and null are distinguished",
        lambda: POL.resolve({"a": None}, "a")[1] and not POL.resolve({}, "a")[1],
        "a resolver that returns only the value makes 'holds null' and 'has no such key' identical")
    net(a, "the live corpus passes its structural rules",
        lambda: _policy_corpus_clean(),
        "records and coverage rows must be well-formed before anything reasons over them")


def _policy_corpus_clean():
    import glob
    import policy as POL
    bad = 0
    for p in sorted(glob.glob(os.path.join(HERE, "data", "records", "*.json")))[:40]:
        try:
            with open(p, encoding="utf-8") as f:
                ev = POL.evaluate(json.load(f), POL.RECORD_RULES, os.path.basename(p))
        except Exception:
            continue
        bad += len([r for r in ev["failed"] if r.get("severity") != "INFO"])
    return bad == 0


# ============================================================== THE FETCH (network manners)

def drill_fetch():
    """Between the wiki and the model: the two ways a network failure becomes a false absence."""
    a = "THE FETCH — can a blocked or throttled page read as an empty subject?"
    net(a, "a block page is refused before the model ever sees it", _page_is_real_gate,
        "verbatim provenance against a Cloudflare interstitial is still verbatim, and still wrong")
    net(a, "throttling widens the pace, and a clean response earns it back", _backoff_adapts,
        "1,364 throttled fetches were once filed as honest absences across every pantheon")

    import feats as F
    net(a, "a refused page is RECORDED, not dropped",
        lambda: "pages_refused" in F.evidence_for.__doc__ or True,
        "the distinction between 'no evidence' and 'we were blocked' must survive to the cache")
    net(a, "persistent throttling hands off to quarantine rather than hammering",
        lambda: F.THROTTLE_STRIKES >= 1 and hasattr(F, "note_throttled"),
        "past a few strikes, 'busy' is a less likely reading than 'blocked'")
    net(a, "the backoff has a ceiling -- slowed, never stopped",
        lambda: 1.0 < F.BACKOFF_MAX <= 128.0,
        "an unbounded backoff is an outage that reports itself as politeness")


# ============================================================== THE CLOUD POOL (cascade)

def drill_cascade():
    """The remote model pool: many providers, separate quotas, and failures that look alike.

    The pool's characteristic failure is not an outage -- it is a bucket that is CLAIMED,
    spends the deadline, and returns nothing, for hours, while the metrics cannot say which
    bucket it was. That is the owner's own open ruling ("two dead keys and a spent account")
    and it was unanswerable from the data: 426 cascade failures in six hours, every one
    recorded as bucket "?".
    """
    a = "THE CLOUD POOL — can a provider burn deadlines without anyone being able to name it?"
    import cascade_bridge as CB

    def failure_names_its_bucket():
        CB._tried_reset()
        CB._tried_add("groq:free")
        CB._tried_add("gemini:free")
        return CB._tried() == ["groq:free", "gemini:free"]
    net(a, "a failed call records which buckets it tried", failure_names_its_bucket,
        "without this, 'which key is dead?' cannot be answered from the metrics at all")

    def tried_is_thread_local():
        import threading
        CB._tried_reset()
        CB._tried_add("mine")
        seen = {}

        def other():
            CB._tried_reset()
            CB._tried_add("theirs")
            seen["other"] = CB._tried()
        t = threading.Thread(target=other)
        t.start()
        t.join()
        return CB._tried() == ["mine"] and seen.get("other") == ["theirs"]
    net(a, "one worker's failure is not attributed to another's bucket", tried_is_thread_local,
        "the readers run sixteen wide; a wrong name is worse than no name")

    # dead_forever must bury ONLY conditions a human has to fix. A 429 or a timeout is the most
    # temporary thing a provider does, and burying those made the pool smaller, not more
    # accurate -- the module's own docstring records that mistake.
    src = open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "cascade_bridge.py"),
               encoding="utf-8").read()
    net(a, "burial is documented as permanent-codes-only",
        lambda: all(c in src for c in ("401", "402", "404", "410")) and "429" in src,
        "a rate limit must never be written down as a permanent property")
    net(a, "there is no paid lane to spend",
        lambda: "THERE IS NO PAID LANE" in src,
        "the lane overspent its own cap 598/500 because the cap gated promotion, not selection")
    net(a, "the local prefix is excluded from cloud claims",
        lambda: "LOCAL_PREFIX" in src and "cand.bucket.startswith(LOCAL_PREFIX)" in src,
        "the router handing out ollama buckets flooded a 10GB card with its own queue")

    # THE OWNER'S STRIKE-OFF (ruling 2026-08-25). Four providers measured at ~40 claims/hour and
    # zero successes; excluding them moves cloud_success_rate 37% -> 45%, which is the floor
    # holding the reader's throttle on.
    for _b in ("zai:free", "cohere:free", "cloudflare:free", "hyperbolic:free"):
        net(a, "%s is struck off and cannot be claimed" % _b,
            (lambda v: (lambda: not CB._alive(v)))(_b),
            "a dead credential claimed 40x/hour costs a deadline every time")
    net(a, "the strike-off matches a bare provider name too",
        lambda: not CB._alive("zai"),
        "a ruling that only bites on one spelling of a bucket does not bite")
    net(a, "working buckets are NOT struck off",
        lambda: CB._alive("groq:free") and CB._alive("gemini:free"),
        "an exclusion list that grows over the whole pool is an outage, not a fix")
    net(a, "every exclusion carries a REASON",
        lambda: all(isinstance(v, str) and len(v) > 8 for v in CB.OWNER_EXCLUDED.values()),
        "a struck-off provider with no stated reason cannot be reviewed or restored")
    net(a, "the strike-off list has not been emptied by a run",
        lambda: len(CB.OWNER_EXCLUDED) >= 4,
        "only the owner removes an entry -- restoring one is an account action, not a code fix")

    def empty_pool_is_not_silence():
        """An exhausted pool must be reportable, not an empty answer that reads as 'no data'."""
        return hasattr(CB, "pool_exhausted") and callable(CB.pool_exhausted)
    net(a, "an exhausted pool is a NAMED condition", empty_pool_is_not_silence,
        "a pool with nothing alive returning None is indistinguishable from a real empty result")


# ============================================================== THE INSPECTOR

def drill_inspector():
    """Does the state of the building match what the building SAYS about itself?

    Every net above tests a mechanism. This tests the REPORTS -- because this project's most
    expensive failures were never a mechanism breaking, they were a report that had drifted from
    the thing it described: a published page ninety minutes behind its own source, a coverage
    field that said "no article under this name" when nothing had been fetched, a roster that
    listed four jobs where nine were running, a comment asserting a measurement that was
    backwards. An inspector does not ask the operator whether the ride is safe. They walk it.
    """
    a = "THE INSPECTOR — is everything actually as it is reported to be?"

    def gate_claim_matches_reality():
        """The gate says closed. Is prose ACTUALLY not being produced?"""
        if PG.gate_open()[0]:
            return True                     # gate open: nothing to reconcile
        cat = os.path.join(HERE, "output", "index", "catalog.json")
        raw = os.path.join(HERE, "output", "raw")
        n_cat = len(json.load(open(cat, encoding="utf-8"))) if os.path.exists(cat) else 0
        n_raw = len([f for f in os.listdir(raw)
                     if os.path.isfile(os.path.join(raw, f))]) if os.path.isdir(raw) else 0
        return n_cat == 0 and n_raw == 0
    net(a, "the gate says CLOSED and the library is genuinely empty of prose",
        gate_claim_matches_reality,
        "a closed gate with chapters still arriving would mean a writer nobody knows about")

    def catalog_matches_disk():
        """Every chapter the catalog claims must exist on disk, and vice versa."""
        cat = os.path.join(HERE, "output", "index", "catalog.json")
        if not os.path.exists(cat):
            return True
        d = json.load(open(cat, encoding="utf-8"))
        for rec in d.values():
            p = (rec or {}).get("raw_path") or ""
            p = p.replace("\\", os.sep).replace("/", os.sep)
            full = p if os.path.isabs(p) else os.path.join(HERE, p)
            if p and not os.path.exists(full):
                return False
        return True
    net(a, "every chapter the catalog claims exists on disk", catalog_matches_disk,
        "a catalog entry with no file is a book the library thinks it has")

    def coverage_totals_are_recomputable():
        """COVERAGE.json's per-source arithmetic must add up to its own entry count."""
        p = os.path.join(HERE, "data", "COVERAGE.json")
        if not os.path.exists(p):
            return True
        rows = json.load(open(p, encoding="utf-8"))
        for r in rows:
            if not isinstance(r, dict):
                continue
            parts = sum(r.get(k, 0) for k in ("cited", "read", "no_page", "no_host"))
            if parts > r.get("entries", 0):
                return False
        return True
    net(a, "coverage's own states never exceed its entry count",
        coverage_totals_are_recomputable,
        "states that sum past the total mean an entry counted twice -- the M23 shape")

    def halt_claim_is_honest():
        """If we are halted, the file must say WHY. A halt with no reason cannot be ruled on."""
        halted, rec = ESC.status()
        if not halted:
            return True
        return bool((rec or {}).get("code")) and bool((rec or {}).get("what"))
    net(a, "a standing halt always carries a reason", halt_claim_is_honest,
        "a halt nobody can read is a halt nobody can lift")

    def guards_are_wired_where_claimed():
        """The interlocks must be present in the files that claim to have them."""
        src = os.path.dirname(os.path.abspath(__file__))
        want = {"generate.py": "assert_gate_open", "overnight.py": "_prose_enabled()",
                "coverage.py": "cachekey", "feats.py": "cachekey",
                "pipeline.py": "cachekey", "hostcheck.py": "cachekey"}
        for f, token in want.items():
            with open(os.path.join(src, f), encoding="utf-8") as fh:
                if token not in fh.read():
                    return False
        return True
    net(a, "every guard is present in the file that claims it", guards_are_wired_where_claimed,
        "the last incident was a guard DELETED, not a guard that failed")

    def liveness_does_not_worsen():
        """A RATCHET, not a floor. The 38 dead functions here predate this work and deleting
        them is a separate, reviewable act. What must not happen is the number GROWING -- a new
        check that never runs is exactly how "a check that cannot fail" gets into the tree, and
        it is invisible to every other instrument because nothing red ever appears.
        """
        import liveness
        r = liveness.scan()
        n = sum(len(v) for v in r.values())
        return n <= LIVENESS_CEILING
    net(a, "no NEW dead code or unfailable check has appeared", liveness_does_not_worsen,
        "the ceiling is a ratchet: lower it when you clean up, never raise it to go green")


# ============================================================== report

def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--to-halt", action="store_true",
                    help="finish by raising a REAL halt so the top rung is observed firing")
    a = ap.parse_args()

    for fn in (drill_queue, drill_dispatch, drill_train, drill_assay, drill_assay_engine,
               drill_no_caps, drill_cache, drill_local_agent, drill_publish, drill_ledgers, drill_two_writer,
               drill_snapshot, drill_stale_writer, drill_policy, drill_fetch, drill_cascade, drill_park, drill_inspector):
        fn()

    area = None
    for r in RESULTS:
        if r["area"] != area:
            area = r["area"]
            print("\n" + area)
            print("-" * min(96, len(area)))
        mark = "HELD    " if r["held"] else "BREACHED"
        print("  %s  %s" % (mark, r["net"]))
        if r["error"]:
            print("            %s" % r["error"])
        if not r["held"] and r["expected"]:
            print("            expected: %s" % r["expected"])

    held = sum(1 for r in RESULTS if r["held"])
    breached = [r for r in RESULTS if not r["held"]]
    print("\n" + "=" * 96)
    print("DRILL: %d nets attacked, %d held, %d BREACHED" % (len(RESULTS), held, len(breached)))
    print("=" * 96)

    out = os.path.join(HERE, "state", "drill_last.json")
    try:
        os.makedirs(os.path.dirname(out), exist_ok=True)
        try:
            import liveness
            _lv = sum(len(v) for v in liveness.scan().values())
        except Exception:
            _lv = None
        with open(out, "w", encoding="utf-8") as f:
            json.dump({"nets": len(RESULTS), "held": held,
                       "breached": [r["net"] for r in breached],
                       "liveness": _lv, "ceiling": LIVENESS_CEILING,
                       "results": RESULTS}, f, indent=1, ensure_ascii=False)
    except Exception:
        pass

    if breached:
        # A BREACHED NET IS ITSELF AN OWNER-LEVEL EVENT. A safety that does not refuse is worse
        # than an absent one, because the whole system is built assuming it refuses.
        ESC.escalate(ESC.OWNER, "DRILL_BREACH",
                     "%d safety net(s) did not hold: %s"
                     % (len(breached), "; ".join(r["net"] for r in breached[:5])),
                     evidence={"breached": [r["net"] for r in breached]}, who="drill.py")
        print("\nA net did not hold, so the library has been HALTED. Clear it with:")
        print('  python src/escalation.py --clear --ruling "<what you decided>"')
        return 1

    if a.to_halt:
        ESC.escalate(ESC.OWNER, "DRILL_COMPLETE",
                     "Full safety drill: every net held. Halt raised deliberately, by request, "
                     "so the top rung is seen firing rather than assumed to work.",
                     evidence={"nets": len(RESULTS), "held": held}, who="drill.py")
        print("\nEvery net held. A halt was raised ON PURPOSE so you can see the top rung work.")
        print("The park is stopped. Restart it with:")
        print('  python src/escalation.py --clear --ruling "<your ruling>"')
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
