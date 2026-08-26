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
    # PROVENANCE (the in-toto materials idea, stdlib-sized). Three outcomes, and the third is
    # the one that matters: nothing recorded must read as UNVERIFIABLE, never as verified.
    net(a, "unchanged source text verifies as PROVEN",
        lambda: CK.provenance_ok(CK.text_digest({"P": "the hero lifted it"}),
                                 {"P": "the hero lifted it"})[0] is True,
        "evidence mined from text that has not moved is still proven")
    net(a, "changed source text is NOT proven",
        lambda: CK.provenance_ok(CK.text_digest({"P": "the hero lifted it"}),
                                 {"P": "the hero did something else"})[0] is False,
        "a citation is not wrong when its page is edited -- it is no longer PROVEN, which is a "
        "different state and must not share a cell with proven")
    net(a, "no recorded provenance is UNVERIFIABLE, not verified",
        lambda: CK.provenance_ok({}, {"P": "anything"})[0] is None,
        "the coverage no_page lesson: 'nobody recorded it' and 'it checked out' differ")
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

def _failed_revert_is_escalated():
    """A revert that FAILS must reach something outliving the process.

    The ALARM existed; nothing carried it. `run()` prints `json.dumps(res)[:110]`, and the keys
    ahead of `ALARM` -- `applied`, `reverted`, and 120 characters of `error` -- push it past the
    cut every time, while the `patches` trail records only patch intent. So the one lane that
    lets a model write to `src/` could leave a half-written module on disk and report success.
    Asserted over the source between the ALARM assignment and the branch's `return`, so moving
    the escalation out of that branch is what breaks this net. (run #33)
    """
    src = open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "local_agent.py"),
               encoding="utf-8").read()
    i = src.find('out["ALARM"]')
    if i == -1:
        return False
    j = src.find("return out", i)
    if j == -1:
        return False
    branch = src[i:j]
    return "_ESC.escalate(" in branch and "_ESC.SAFETY" in branch


def drill_local_agent():
    """The autonomous local writer is staff too, and staff get supervised.

    `local_agent.py` lets the free local model read and PATCH the repo, which is the cheapest
    labour available and also the only actor here that can change the building while nobody is
    watching. Its gate has already been defeated four separate ways (case, name prefix, an NTFS
    alternate data stream, a case-sensitive extension test). These attacks are the fifth family.
    """
    a = "THE NIGHT STAFF — can the local model edit what it must not?"
    import local_agent as LA

    net(a, "a FAILED auto-revert fails the battery instead of printing into the void",
        _failed_revert_is_escalated,
        "a half-written module on disk while the run reports success is the worst outcome this "
        "lane has, and the ALARM was being truncated out of the only place it was sent")

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

def _snapshot_proves_a_directory():
    """A snapshotted DIRECTORY must be proved file by file, not by the folder still existing.

    THE GAP THIS COVERS, found by the run #33 sweep. Every net in `drill_snapshot` exercised a
    single FILE -- `config.yaml` -- and `snapshot.verify()` only ran its byte comparison under
    `os.path.isfile(a)`. So for a directory, the sole surviving check was `os.path.exists(b)`,
    which is true of a folder whatever is or is not inside it, and a restore that dropped or
    truncated every file beneath it still reported "N path(s) restored and byte-identical".
    The battery had no way to notice, because the battery never snapshotted a directory. A
    directory is not the exotic case here: it is what `before()` takes through `shutil.copytree`
    and what a caller about to withdraw a folder of chapters actually hands it.

    THE END-TO-END HALF CANNOT FAIL BY ITSELF and is not asked to. Taking a snapshot of a real
    directory and verifying it proves that the directory path is walked at all, but it would
    keep passing if the byte comparison were deleted again -- that is the whole shape of the
    original defect. The teeth are the two REFUSALS below, put directly to the comparator:
    a file missing on the restored side, and a file present with different bytes AT THE SAME
    LENGTH, which is the answer a stat-only or shallow compare would wave through. Remove the
    comparator and this net raises rather than passes.

    In `state/` rather than the system temp dir because `snapshot._rel` takes paths relative to
    the repo root, and an absolute path from outside it produces a `../..` relative path that
    would escape the snapshot directory. Both the scratch tree and the snapshot it produces are
    removed in the `finally`; the drill leaves nothing behind.
    """
    import shutil
    import tempfile
    import snapshot as SNAP
    d = tempfile.mkdtemp(prefix="drilldir_", dir=os.path.join(HERE, "state"))
    sid = None
    try:
        os.makedirs(os.path.join(d, "nested"))
        for name, body in (("top.txt", "the bytes that must come back\n"),
                           (os.path.join("nested", "chapter.txt"), "a chapter, nested\n")):
            with open(os.path.join(d, name), "w", encoding="utf-8") as f:
                f.write(body)
        sid = SNAP.before("drill-dir", [d], note="drill self-test (directory)")
        if not SNAP.verify(sid)[0]:
            return False

        # ... and the comparator must be able to say no, in both shapes.
        other = tempfile.mkdtemp(prefix="drilldir2_", dir=os.path.join(HERE, "state"))
        try:
            shutil.copytree(d, other, dirs_exist_ok=True)
            os.remove(os.path.join(other, "nested", "chapter.txt"))
            if SNAP._dir_matches(d, other)[0]:
                return False                      # a dropped file read as byte-identical
            with open(os.path.join(other, "nested", "chapter.txt"), "w",
                      encoding="utf-8") as f:
                f.write("a chapter, mangled\n")   # same length, different bytes
            if SNAP._dir_matches(d, other)[0]:
                return False
            return True
        finally:
            shutil.rmtree(other, ignore_errors=True)
    finally:
        shutil.rmtree(d, ignore_errors=True)
        if sid:
            shutil.rmtree(os.path.join(SNAP.ROOT, sid), ignore_errors=True)


def drill_snapshot():
    a = "THE UNDO — is there a copy behind an irreversible step, and does it restore?"
    import snapshot as SNAP
    sid = SNAP.before("drill", ["config.yaml"], note="drill self-test")
    net(a, "a snapshot restores byte-identically", lambda: SNAP.verify(sid)[0],
        "an untested backup is a belief, not a backup")
    net(a, "a snapshotted DIRECTORY is proved file by file, not by its own existence",
        _snapshot_proves_a_directory,
        "every net here exercised one file, and a folder of chapters is what really gets "
        "snapshotted")
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
        _policy_corpus_clean,      # the function, not a lambda wrapping it: every other net in
        # this battery passes the callable itself, and the wrapper is a layer that can only
        # ever forward. `secondopinion` flagged it (PLW0108) and it is the right call. (run #33)
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

def _refusal_is_recorded():
    """A page that was REFUSED must reach the cached record as a refusal, not as an absence.

    THIS NET COULD NOT FAIL UNTIL RUN #33. It read:

        lambda: "pages_refused" in F.evidence_for.__doc__ or True

    -- and `or True` made the whole expression unconditionally true. Worse, the masked half was
    testing the wrong thing anyway: it asked whether a DOCSTRING mentioned the key, and that
    docstring does not mention it, so the net would have failed had anyone ever removed the
    `or True`. A net asserting a fact about prose, then defanged so the wrong assertion could
    not embarrass anyone, is the exact shape this project calls a check that cannot fail. Found
    by the run #33 sweep.

    What actually carries the guarantee is `feats.evidence_for`: the refusal branch records the
    reason under the title, and the written record carries that map. Both halves are asserted,
    because either one alone can be removed without the other looking wrong.
    """
    src = open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "feats.py"),
               encoding="utf-8").read()
    return '"pages_refused": unreal' in src and "unreal[t] = why" in src


def _throttle_hands_off():
    """A host throttled to the strike limit must be HANDED to binding_health, not hit again.

    THE OLD NET ASSERTED A CONSTANT AND A NAME:

        lambda: F.THROTTLE_STRIKES >= 1 and hasattr(F, "note_throttled")

    Neither half ever drives a call. `THROTTLE_STRIKES` is a module constant nobody was going
    to set to zero, `hasattr` asks whether a name exists, and the entire hand-off -- the
    `if strikes >= THROTTLE_STRIKES` test and the `BH.quarantine(...)` inside it -- could be
    deleted outright with both halves still true. Its sibling two lines up, `_backoff_adapts`,
    already showed the right shape: call the real function against a throwaway host and read
    the real state back. Found by the run #33 sweep, alongside the `or True` in
    `_refusal_is_recorded` immediately above it.

    THE HAND-OFF IS TAKEN BY A STAND-IN, swapped into `sys.modules` and restored in a
    `finally`. `note_throttled` does its `import binding_health as BH` inside its own body, so
    the stand-in is what it reaches -- and it must be, because the real `quarantine()` writes
    to `data/HOST_QUARANTINE.json` and the drill is not allowed to leave a quarantine behind
    for a host that does not exist. A battery with side effects is a battery nobody dares run
    on a live library, which is the one place it is worth running.

    BOTH DIRECTIONS ARE ASSERTED. Handing off too early is its own defect -- three strikes is
    the point at which "busy right now" stops being the likelier reading than "we are being
    blocked", and a hand-off on the first 429 would quarantine every healthy host under load.
    So the net requires silence below the threshold and exactly one hand-off at it.
    """
    import types
    import feats as F
    h = "__drill_quarantine__.invalid"
    handed = []
    stub = types.ModuleType("binding_health")
    stub.is_quarantined = lambda host: False
    stub.quarantine = lambda host, why: handed.append((host, why))
    had = "binding_health" in sys.modules
    prev = sys.modules.get("binding_health")
    F._BACKOFF.pop(h, None)
    F._STRIKE.pop(h, None)
    try:
        sys.modules["binding_health"] = stub
        for _ in range(F.THROTTLE_STRIKES - 1):
            F.note_throttled(h)
        early = list(handed)
        F.note_throttled(h)
    finally:
        if had:
            sys.modules["binding_health"] = prev
        else:
            sys.modules.pop("binding_health", None)
        F._BACKOFF.pop(h, None)
        F._STRIKE.pop(h, None)
    return early == [] and len(handed) == 1 and handed[0][0] == h


def drill_fetch():
    """Between the wiki and the model: the two ways a network failure becomes a false absence."""
    a = "THE FETCH — can a blocked or throttled page read as an empty subject?"
    net(a, "a block page is refused before the model ever sees it", _page_is_real_gate,
        "verbatim provenance against a Cloudflare interstitial is still verbatim, and still wrong")
    net(a, "throttling widens the pace, and a clean response earns it back", _backoff_adapts,
        "1,364 throttled fetches were once filed as honest absences across every pantheon")

    import feats as F
    net(a, "a refused page is RECORDED, not dropped",
        _refusal_is_recorded,
        "the distinction between 'no evidence' and 'we were blocked' must survive to the cache")
    net(a, "persistent throttling hands off to quarantine rather than hammering",
        _throttle_hands_off,
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

def drill_workorders():
    """THE QUEUE — does a RED battery actually reach the work order file?

    Added run #33, for a fault the queue could not see. `drill.py` escalated; `verify_math`,
    `health`, `allsweep` and `liveness` did not, and none of them were in `sweep_detectors`. So
    on 2026-08-25 `workorders --sweep` printed "no open work orders -- the nets found nothing
    outstanding" while verify_math was FAILING and the preflight was FAILING. The queue was not
    wrong about its own contents; it was blind, and a blind queue reports the same sentence as a
    clear one. These nets attack that blindness directly: each one hands `battery_faults` a
    battery in a known state and demands the verdict.
    """
    a = "THE QUEUE — does a red battery reach the work order file?"
    import workorders as W
    NOW = 1000000.0
    fresh = {"at": NOW - 60}
    green_sweep = {"at": NOW - 60, "imports": [{"module": "m", "ok": True}],
                   "verifiers": [{"check": "v", "crashed": False, "timeout": False}],
                   "lint": [], "estate": {"artifacts": {"bad": []}}}

    def fired(preflight, allsweep):
        return {k for k, v in W.battery_faults(preflight=preflight, allsweep=allsweep,
                                               now=NOW).items() if v}

    net(a, "a GREEN battery files nothing (no alarm that always sounds)",
        lambda: fired(dict(fresh, problems=0, rows=[]), green_sweep) == set(),
        "an alarm that sounds on a healthy library is furniture within a week")
    net(a, "a preflight WITH problems files an order",
        lambda: "PREFLIGHT_PROBLEM" in fired(
            dict(fresh, rows=[{"check": "caches", "what": "feats/x", "detail": "all empty"}]),
            green_sweep),
        "805 empty dandwiki entries sat unreported for four runs because the only thing that "
        "knew was a console")
    net(a, "a FAILED import in allsweep files an order",
        lambda: "BATTERY_GRADED" in fired(
            dict(fresh, rows=[]),
            {"at": NOW - 60, "imports": [{"module": "verify_math", "ok": False,
                                          "detail": "FAILED"}]}),
        "verify_math failing its own completeness proof must not be a terminal-only event")
    net(a, "a dirty LINT tier files an order",
        lambda: "BATTERY_GRADED" in fired(dict(fresh, rows=[]),
                                          {"at": NOW - 60, "lint": ["src/x.py:1 undefined"]}),
        "run #26: the lint tier was computed, printed, and dropped")
    net(a, "a CRASHED verifier files an order",
        lambda: "BATTERY_GRADED" in fired(
            dict(fresh, rows=[]),
            {"at": NOW - 60, "verifiers": [{"check": "drill", "crashed": True}]}),
        "a verifier that died is not a verifier that passed")
    net(a, "a MISSING battery artifact does not read as green",
        lambda: fired(None, None) == {"PREFLIGHT_STALE", "BATTERY_STALE"},
        "absence of evidence read as evidence of health is how this library goes quiet")
    net(a, "a STALE battery artifact does not read as green",
        lambda: fired({"at": NOW - 99 * 3600, "rows": []},
                      {"at": NOW - 99 * 3600}) == {"PREFLIGHT_STALE", "BATTERY_STALE"},
        "'nobody has run the battery since Tuesday' and 'the battery is green' are different "
        "sentences")
    net(a, "every code this tier files can also be CLOSED",
        lambda: set(W.BATTERY_WHERE) == set(W.BATTERY_CODES) and all(
            W.BATTERY_WHERE.get(c) for c in W.BATTERY_CODES),
        "resolve_code closes order_id(code, where) -- a detector filing under one `where` and "
        "clearing under another files orders nobody can ever close")
    import binding_health as _BH33
    net(a, "a host that is UP but resolves no title is NOT quarantined",
        lambda: _BH33.verdict(False, True, True)[0] is None,
        "a quarantine stops mining, and mining a live wiki is still correct when it was only "
        "the probe titles that were wrong -- 5 live wikis were quarantined this way in run #33")
    net(a, "an UNREACHABLE host is still called dead",
        lambda: _BH33.verdict(False, True, False)[0] is False,
        "if unreachable stopped being a host fault, dandwiki's 403 would read as healthy")
    net(a, "a host that answers yes to EVERYTHING is dead however reachable it is",
        lambda: _BH33.verdict(True, False, True)[0] is False
        and _BH33.verdict(False, False, True)[0] is False,
        "a soft-404 or a login wall dressed as an article makes every hit worthless")
    net(a, "a host that serves what we know it holds is healthy",
        lambda: _BH33.verdict(True, True, True)[0] is True,
        "a canary that can never say yes quarantines the whole library eventually")
    net(a, "every unhealthy verdict carries a REASON",
        lambda: all(_BH33.verdict(p, a2, r)[1] for p in (True, False) for a2 in (True, False)
                    for r in (True, False) if _BH33.verdict(p, a2, r)[0] is not True),
        "a quarantine with no reason is one nobody can ever judge or lift")
    net(a, "no code in this tier is UNREACHABLE",
        lambda: set(W.BATTERY_CODES) <= (
            fired(None, None)
            | fired(dict(fresh, rows=[{"check": "c", "what": "w", "detail": "d"}]),
                    {"at": NOW - 60, "lint": ["x"]})),
        "a code nothing can ever raise is a check that cannot fail, wearing a name")


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


def drill_codewatch():
    """Stale daemons — the failure that made every other safety here conditional.

    On 2026-08-25 a guard was added to `publish.py` to stop it pushing during a mutation run.
    It was correct, it was tested by hand, and a mutated file went to a public GitHub repo
    anyway — because `publish.py --push --loop 1` had been running since 14:28 with the
    pre-guard code in memory. A Python process does not re-read its own source.

    That is not a fact about publishing. It is a fact about **every safety in this project**:
    each one is inert in every job already running until that job restarts. Fifteen were.
    """
    a = "CODEWATCH — a running job is a photograph of the code it started with"

    def daemons_actually_check_their_own_source():
        """The three standing loops must call it. Checked by reading them, because a daemon
        that merely COULD check is a daemon that does not."""
        src = os.path.dirname(os.path.abspath(__file__))
        for f in ("publish.py", "foreman.py", "overwatch.py"):
            with open(os.path.join(src, f), encoding="utf-8") as fh:
                text = fh.read()
            if "codewatch.exit_if_stale" not in text or "codewatch.stamp" not in text:
                return False
        return True
    net(a, "every standing daemon checks whether its own source has changed",
        daemons_actually_check_their_own_source,
        "a guard added at 19:00 is not in effect at 03:00 unless the job restarted")

    def a_change_must_settle_before_it_restarts_anything():
        """A digest taken mid-write is a digest of garbage. `local_agent --patch` writes several
        files over several seconds, and a naive watcher would bounce every daemon per file."""
        import codewatch as CW
        CW.stamp("__drill__")
        saved = CW._START["digest"]
        try:
            CW._START["digest"] = "0000000000000000"      # pretend the source moved
            first = CW.stale("__drill__")
            second = CW.stale("__drill__")
            return first[0] is False and second[0] is False and "settling" in second[1]
        finally:
            CW._START["digest"] = saved
            CW._PENDING["digest"] = None
            CW._PENDING["first_seen"] = None
    net(a, "a source change must hold still before it triggers a restart",
        a_change_must_settle_before_it_restarts_anything,
        "restarting into a half-written file is worse than running the old one")

    def unreadable_source_is_not_reported_as_unchanged():
        """FAIL LOUD, NOT QUIET. If the tree cannot be read, `fingerprint` returns None, and
        None must never be compared equal to a stored digest -- that would silently stop the
        watching without stopping the reporting."""
        import codewatch as CW
        empty = os.path.join(tempfile.gettempdir(), "drill_codewatch_none")
        os.makedirs(empty, exist_ok=True)
        fp = CW.fingerprint(empty)
        # An empty directory legitimately fingerprints; the None path is the unreadable one.
        return fp is not None and CW.fingerprint(os.path.join(empty, "does_not_exist")) is None
    net(a, "an unreadable source tree is not mistaken for an unchanged one",
        unreadable_source_is_not_reported_as_unchanged,
        "None must never compare equal to a digest")

    def restarts_are_budgeted():
        """A daemon that bounces every cycle does no work while looking busy. Past the budget
        it must keep running stale and ESCALATE instead -- lag beats thrash, and this project
        has already paid for one respawn loop."""
        import codewatch as CW
        return isinstance(CW.BUDGET_PER_HOUR, int) and 0 < CW.BUDGET_PER_HOUR <= 12
    net(a, "source-change restarts are budgeted per job per hour", restarts_are_budgeted,
        "an unbudgeted restarter is a respawn loop waiting for an edit storm")

    def twin_detection_does_not_match_bystanders():
        """THE ONE THAT WOULD HAVE CAUSED THE OUTAGE IT PREVENTS. The first version asked
        whether the module name appeared ANYWHERE in a command line, and immediately matched a
        `pyflakes src/codewatch.py src/publish.py src/foreman.py src/overwatch.py` invocation --
        one linter reported as a twin of three daemons at once. Every one of them would then
        have refused to start because somebody was linting it."""
        import codewatch as CW
        # A module no daemon runs must have no twins even while this very drill's command line
        # is full of module names.
        return CW.twins("anchors") == [] and CW.twins("verify_math") == []
    net(a, "twin detection matches the script being RUN, not any mention of it",
        twin_detection_does_not_match_bystanders,
        "a linter is not a daemon; refusing to start because someone read the file is an outage")

    def singleton_guard_is_wired_into_the_daemons():
        src = os.path.dirname(os.path.abspath(__file__))
        for f in ("publish.py", "foreman.py", "overwatch.py"):
            with open(os.path.join(src, f), encoding="utf-8") as fh:
                if "claim_singleton" not in fh.read():
                    return False
        return True
    net(a, "every standing daemon refuses to run beside a twin",
        singleton_guard_is_wired_into_the_daemons,
        "two publishers into one export repo is the two-writer fault push() documents")

    def the_supervisor_can_name_the_deliberate_exit():
        """rc=17 must read as intent, never as breakage. The confusion between the two caused
        this project's longest outage."""
        import overnight as ON
        return "PURPOSE" in ON.name_rc(17).upper()
    net(a, "the supervisor reads rc=17 as deliberate, not as a crash",
        the_supervisor_can_name_the_deliberate_exit,
        "a safety that stops work must be distinguishable from a fault that stops work")


def drill_mutation():
    """The mutation lock — because breaking code on purpose is only safe if everyone knows.

    THE INCIDENT, 2026-08-25, an hour after `mutate.py` was written. A mutation run had
    `prose_gate.py` deliberately corrupted on disk. Two other things read it in that window: a
    concurrent `drill.py` saw two nets fail and **halted the entire library**, and
    `publish.py --push` **shipped the corrupted gate to GitHub**, where `cited_fraction()`
    matched every source except the one it was asked about.

    Nothing was positioned to catch it. The secret scanner does not read logic, `ledger_guard`
    watches the ledgers, and the drill was confused by the same corruption it should have
    reported. The only process that can know the tree is deliberately broken is the one breaking
    it, so it now says so, and these nets attack every way that announcement could fail.
    """
    a = "MUTATION — deliberate corruption must be distinguishable from a real fault"

    def lock_is_exclusive():
        """Two mutation runs at once means two mutants on disk and no way to attribute either."""
        import mutate as M
        saved = M.LOCK
        M.LOCK = os.path.join(tempfile.gettempdir(), "drill_mut_excl.json")
        try:
            if os.path.exists(M.LOCK):
                os.remove(M.LOCK)
            M._lock_acquire(["a.py"], "t1")
            try:
                M._lock_acquire(["b.py"], "t2")
                return False                      # a second holder was allowed. Breach.
            except RuntimeError:
                return True
            finally:
                M._lock_release()
        finally:
            M.LOCK = saved
    net(a, "a second mutation run cannot start while one is active", lock_is_exclusive,
        "two mutants on disk at once is a corruption nobody can attribute")

    def unreadable_lock_counts_as_HELD():
        """FAIL CLOSED. If the file exists, something claimed the right to corrupt the tree;
        'I could not read the claim' is not permission to publish over it."""
        import mutate as M
        saved = M.LOCK
        M.LOCK = os.path.join(tempfile.gettempdir(), "drill_mut_bad.json")
        try:
            with open(M.LOCK, "w", encoding="utf-8") as fh:
                fh.write("{ this is not json")
            return M.active()[0] is True
        finally:
            try:
                os.remove(M.LOCK)
            except OSError:
                pass
            M.LOCK = saved
    net(a, "an unreadable lock is treated as HELD, not as absent", unreadable_lock_counts_as_HELD,
        "an unparseable claim is still a claim")

    def dead_holder_does_not_block_forever():
        """The other half. A lock outliving its process would block every future push, which is
        an outage wearing a safety's clothes."""
        import mutate as M
        saved = M.LOCK
        M.LOCK = os.path.join(tempfile.gettempdir(), "drill_mut_stale.json")
        try:
            with open(M.LOCK, "w", encoding="utf-8") as fh:
                json.dump({"pid": 999999999, "started": 0, "targets": ["x.py"]}, fh)
            held, rec = M.active()
            return held is False and bool(rec and rec.get("stale"))
        finally:
            try:
                os.remove(M.LOCK)
            except OSError:
                pass
            M.LOCK = saved
    net(a, "a lock whose process died is reported stale, not held forever",
        dead_holder_does_not_block_forever,
        "a safety that cannot be released is an outage, and it reports as protection")

    def mutation_never_touches_the_live_tree():
        """The architectural fix, asserted rather than assumed. `run()` must open the SANDBOX
        path for writing and must verify the live file is byte-identical afterwards."""
        src = os.path.dirname(os.path.abspath(__file__))
        with open(os.path.join(src, "mutate.py"), encoding="utf-8") as fh:
            text = fh.read()
        return ("live_file_untouched" in text and "def sandbox(" in text
                and "MUTATE_TOUCHED_LIVE_TREE" in text)
    net(a, "mutation writes into a sandbox and proves the live file is untouched",
        mutation_never_touches_the_live_tree,
        "fifteen processes read the live tree; corrupting it is not something a lock can fix")

    def abandoned_sandboxes_are_reaped():
        """A killed run cannot clean up after itself -- `finally` does not run on a kill -- and
        two kills leaked 154 MB in two hours. A nightly job that leaks 50 MB per interruption
        fills a disk quietly, and a full disk takes down the crawl, the model and the publisher
        at once for a reason nobody would look for."""
        import mutate as M
        if not hasattr(M, "reap_orphans"):
            return False
        # Must be age-gated: reaping indiscriminately would delete the sandbox of the run doing
        # the reaping.
        return M.ORPHAN_AGE_SECONDS >= 3600 and M.reap_orphans(older_than=10 ** 9) == []
    net(a, "abandoned sandboxes are reaped, but only once they are old",
        abandoned_sandboxes_are_reaped,
        "a leak of 50 MB per interrupted run fills a disk without ever reporting anything")

    def publish_asks_before_pushing():
        """The step whose failure is IRREVERSIBLE and OUTWARD-FACING. Verified by reading the
        push path, the same way `guards_are_wired_where_claimed` checks the other interlocks --
        a net that actually pushed to prove a refusal would be worse than the bug."""
        src = os.path.dirname(os.path.abspath(__file__))
        with open(os.path.join(src, "publish.py"), encoding="utf-8") as fh:
            text = fh.read()
        head = text[:text.index("def push(")] if "def push(" in text else ""
        body = text[len(head):]
        return "import mutate" in body and "REFUSING TO PUSH" in body
    net(a, "publish refuses to push while a mutation run is active", publish_asks_before_pushing,
        "a mutated file pushed to a public repo is public even after the next commit")

    def drill_does_not_halt_during_a_mutation_run():
        """This file must PRINT a breach during a mutation run and must not HALT over it --
        mutate reads the breach from stdout, which is how a mutant gets killed."""
        src = os.path.dirname(os.path.abspath(__file__))
        with open(os.path.join(src, "drill.py"), encoding="utf-8") as fh:
            text = fh.read()
        # Search for the escalation FROM the branch, not from the top of the file: the string
        # "DRILL_BREACH" also appears in this module's own prose long before the code that
        # raises it, so a bare `find` compared two unrelated offsets and this net breached
        # against correct code. A net that fails for its own reasons teaches people to ignore it.
        # `rfind`, and the reason is worth the line: this net reads the file it LIVES IN, so a
        # forward `find` for "if breached:" matched the string literal inside this very
        # function -- 78,000 characters before the branch it meant to inspect -- and the net
        # breached against perfectly correct code, twice. A detector that searches its own
        # source has to reckon with finding itself. The real branch is in `main()`, last.
        i = text.rfind("    if breached:")
        j = text.rfind('"DRILL_BREACH"')
        return -1 < i < j and "MUTATION RUN IS ACTIVE" in text[i:j]
    net(a, "a breach during a mutation run is reported but does not halt the library",
        drill_does_not_halt_during_a_mutation_run,
        "a safety that stops work must be distinguishable from a fault that stops work")


def drill_scope():
    """An owner exclusion must actually exclude — the status that did nothing for five days.

    `SWEEP_ROLL.json` carried `status: "out-of-scope"` on four sources from 2026-08-20, and not
    one module in `src/` read it. The generator queued them, the cataloguer crawled them, the
    coverage meter counted them against the library. A decision recorded where nobody reads it
    is worse than one never taken, because the record stops anyone asking again.
    """
    a = "SCOPE — an owner exclusion must remove a source from WORK, not just from a list"

    def exclusion_is_readable_and_reasoned():
        """Every excluded source names why, and `roll.py` is the one place that answers."""
        import roll
        ex = roll.out_of_scope()
        if not ex:
            return True                       # nothing excluded is a lawful state
        return all(w and "no reason recorded" not in w for w in ex.values())
    net(a, "every excluded source carries a written reason", exclusion_is_readable_and_reasoned,
        "an exclusion nobody can explain is a source quietly dropped")

    def generator_actually_skips_an_excluded_source():
        """The manifest builder must consult `roll`, not just read the file."""
        src = os.path.join(os.path.dirname(os.path.abspath(__file__)), "manifest_builder.py")
        with open(src, encoding="utf-8") as fh:
            text = fh.read()
        return "out_of_scope" in text and "import roll" in text
    net(a, "the generator consults the exclusion list before building jobs",
        generator_actually_skips_an_excluded_source,
        "a status string no consumer reads is a decision that did not happen")

    def resync_cannot_revert_an_exclusion():
        """THE TRAP THIS ALMOST FELL INTO. `resync_roll` rebuilds status from records on disk
        with the rule `catalogued if n else keep` -- so an excluded source that still HAS records
        would be silently promoted back. All four of the 2026-08-25 exclusions have records."""
        src = os.path.join(os.path.dirname(os.path.abspath(__file__)), "resync_roll.py")
        with open(src, encoding="utf-8") as fh:
            text = fh.read()
        return "OUT_OF_SCOPE" in text
    net(a, "a routine resync cannot silently un-exclude a source",
        resync_cannot_revert_an_exclusion,
        "an exclusion a maintenance script can undo unnoticed is not an exclusion")

    def excluded_sources_keep_their_records():
        """Removed from work, NOT from disk. Reversing the ruling must cost one field."""
        import roll
        import glob as _g
        ex = roll.out_of_scope()
        if not ex:
            return True
        names = set()
        for p in _g.glob(os.path.join(HERE, "data", "records", "*.json")):
            try:
                with open(p, encoding="utf-8") as fh:
                    names.add(json.load(fh).get("source"))
            except Exception:
                continue
        # At least one excluded source that HAD records must still have them. If every excluded
        # source lost its records, "exclusion" has quietly become deletion.
        had = [n for n in ex if n in names]
        return bool(had) or not names
    net(a, "an excluded source keeps its records on disk", excluded_sources_keep_their_records,
        "withdraw MOVES, it does not unlink -- reversing a ruling must not need a re-crawl")

    def unreadable_roll_does_not_exclude_the_library():
        """`in_scope` fails OPEN, against house habit, and the reason is stated in roll.py: an
        unreadable roll silently excluding all 215 sources would be a fault that looks exactly
        like a completed run."""
        import roll
        return roll.in_scope("a source that is not in any roll", rows=[])
    net(a, "an unreadable roll does not silently exclude everything",
        unreadable_roll_does_not_exclude_the_library,
        "fail-closed here would turn one bad file into a mass deletion that reports success")


def drill_correlation():
    """The covariance term — a correction that could silently become a decoration.

    Adding `rho` to `_interval` made every published bar wider, which is the honest direction.
    But a correlation term has three ways to stop working and none of them are loud: the matrix
    file goes missing and the formula degrades to independence; a future edit writes rho = 0,
    which is the one value the data rules out; or the term is present but so small it changes
    nothing. All three leave an instrument that reports exactly as it did when it was working.
    """
    a = "CORRELATION — the covariance term, and the ways it could quietly stop mattering"

    def measures_are_not_independent():
        """The matrix must be present AND must say what the measurement said."""
        import axis_correlation as AC
        doc = AC.load()
        if not doc:
            return False                       # a missing matrix silently restores rho = 0
        mean = doc.get("mean_r")
        return isinstance(mean, (int, float)) and mean > 0.1 and doc.get("n_entities", 0) >= 20
    net(a, "the measured correlation matrix exists and rules out independence",
        measures_are_not_independent,
        "rho = 0 is the single value 45 entities and 55 pairs have excluded")

    def correlation_actually_widens_the_bar():
        """Positive rho must produce a WIDER interval than independence. Prove it arithmetically
        rather than trusting that a term which is present is a term which is doing work."""
        import assay as A
        import axis_correlation as AC
        phys = list(A.CHARTER_PHYSICAL_WEIGHTS)
        sigma = A.SIGMA_BY_ATTESTATION["Witnessed"]
        factor, indep, cov = AC.widening(A.WEIGHTS, sigma, phys)
        return cov > 0 and factor > 1.2 and indep > 0
    net(a, "the covariance term measurably widens the interval", correlation_actually_widens_the_bar,
        "a correction that changes nothing is a comment, not a correction")

    def more_ignorance_never_narrows():
        """THE ONE THAT ALREADY CAUGHT A BUG. Marking axes UNESTIMABLE must cost more than
        marking them INAPPLICABLE. The first covariance implementation applied rho only among
        SCORED axes, which diluted their weights without replacing their cross terms, and made
        declaring three faculties unknown produce a NARROWER bar. The battery caught it; this
        net is here so the drill catches it next time too."""
        import assay as A
        base = {"ruin": 2.1, "continuity": 4.8, "celerity": 6.5, "reach": 1.2,
                "transgression": 8.7, "sustain": 7.4, "vector": 0.8, "volition": 9.6}
        na = dict(base, acumen=A.INAPPLICABLE, discernment=A.INAPPLICABLE,
                  suasion=A.INAPPLICABLE)
        unk = dict(base, acumen=A.UNESTIMABLE, discernment=A.UNESTIMABLE,
                   suasion=A.UNESTIMABLE)
        i_na = A.assay("M3", na, attestation="Witnessed", worksheet="drill")["interval"]
        i_unk = A.assay("M3", unk, attestation="Witnessed", worksheet="drill")["interval"]
        return i_unk >= i_na
    net(a, "three UNESTIMABLE axes never cost less than three INAPPLICABLE ones",
        more_ignorance_never_narrows,
        "less knowledge must never buy a narrower bar -- this project's oldest arithmetic bug")

    def charter_bar_still_reproduced():
        """The correction moved the intermediate constant. It must NOT have moved the charter's
        published number, which is the only external authority the instrument answers to."""
        import assay as A
        r = A.calibration_report()
        return bool(r.get("holds")) and r["interval"] == A.CHARTER_KENSHIRO_INTERVAL
    net(a, "the charter's published Kenshiro bar survived the recalibration",
        charter_bar_still_reproduced,
        "the constant moves, the charter does not")

    def anchor_sigma_is_physically_coherent():
        """Witnessed must sit BELOW the maximum-entropy dispersion of the scale. Under the old
        independent formula the raw fit was 4.08 against a uniform-prior sd of 2.86 -- the
        charter's best testimony coming out more uncertain than knowing nothing, which was the
        missing covariance being absorbed into the per-axis sigma."""
        import assay as A
        return A._ANCHOR_SIGMA < A.SIGMA_UNIFORM_PRIOR
    net(a, "the Witnessed sigma sits inside the maximum-entropy bound",
        anchor_sigma_is_physically_coherent,
        "a grade of testimony more uncertain than total ignorance is a formula, not a fact")


def drill_outside():
    """The derived index and the outside opinion — two new ways to be confidently wrong.

    Both of the things adopted on 2026-08-25 carry the same hazard in different clothes. A SQL
    index of the corpus answers instantly and will keep answering instantly after it has drifted
    from the records it was built from; a linter that is not installed produces no findings and
    no findings reads as a clean bill of health. Neither failure announces itself, and both
    produce output that looks exactly like the healthy case -- which is the shape this project
    has paid for more times than any other.
    """
    a = "OUTSIDE — the derived index and the second opinion"

    def index_admits_when_it_is_behind():
        """NOT "is the index fresh" -- it cannot be. "Does it KNOW it isn't."

        The first version of this net demanded agreement within 2% and breached immediately,
        and the breach taught the right lesson rather than the one it was looking for: 8,613
        entries were catalogued in the twenty-seven minutes after a rebuild, so this index is
        stale within about seven minutes and no tolerance band survives contact with the crawl.
        A net that goes red for a condition nobody can fix is furniture, and worse, it trains
        people to read BREACHED as normal.

        The property that IS enforceable, and is the one that matters, is honesty: when a record
        has been written since the build, `freshness()` must say so. An index that reports itself
        current while sitting on a five-figure gap is the failure; an index that says "I am forty
        minutes behind" is doing its job.
        """
        import corpus_db
        import glob as _g
        if not os.path.exists(corpus_db.DB):
            return corpus_db.freshness()["stale"] is True    # no index is maximally stale
        f = corpus_db.freshness()
        if f["built_at"] is None:
            return f["stale"] is True
        # Independently recompute the thing it claims, from mtimes it did not hand us.
        newer = 0
        for p in _g.glob(os.path.join(HERE, "data", "records", "*.json")):
            try:
                if os.path.getmtime(p) > f["built_at"]:
                    newer += 1
            except OSError:
                newer += 1
        # It may not UNDERSTATE. Claiming fresh while records have moved is the breach; a small
        # overstatement from a file written between the two passes is not.
        if newer > 0 and not f["stale"]:
            return False
        return f["stale"] == (newer > 0) or newer == 0
    net(a, "the SQL index admits when it is behind the records",
        index_admits_when_it_is_behind,
        "it cannot be fresh; it can be honest, and a silent stale index is the real fault")

    def stale_index_says_so_where_the_numbers_are():
        """The warning must ride WITH the results, not live in a separate command."""
        import corpus_db
        line = corpus_db._freshness_banner()
        f = corpus_db.freshness()
        if f["age_seconds"] is None:
            return "NO INDEX" in line
        return ("STALE" in line) == bool(f["stale"])
    net(a, "the staleness warning is printed above the results themselves",
        stale_index_says_so_where_the_numbers_are,
        "a caveat somewhere else is a caveat nobody reads next to the number it qualifies")

    def index_spine_agrees_with_the_resolver():
        """THE ONE THAT ALREADY COST A FALSE ALARM. The index's `spine` column must come from
        `address.spine_code_for()`, not from a simpler reimplementation of it.

        It did not, at first: `corpus_db` read the Acquisitions Index into a dict and did a
        direct `get`, and reported 36 sources with no spine code covering 13,417 entries. The
        real resolver does letter-level equality, whole-word containment and order-independent
        token matching, and resolves 35 of those 36. The true count is ONE. A derived view that
        reimplements a rule more simply than the rule is a second answer to the same question,
        and this one was alarming enough to nearly be acted on as a curatorial backlog.
        """
        import corpus_db
        import address
        if not os.path.exists(corpus_db.DB):
            return True
        cols, rows = corpus_db.query("SELECT name, spine FROM source")
        for name, stored in rows:
            if not name:
                continue
            real = address.spine_code_for(name)
            real = None if real == "UNASSIGNED" else real
            if stored != real:
                return False
        return True
    net(a, "the index's spine column agrees with address.spine_code_for()",
        index_spine_agrees_with_the_resolver,
        "a derived view must derive through the same code, never a simpler copy of it")

    def index_query_cannot_write():
        """`query()` is read-only BY CONTRACT. Prove the contract is enforced, not documented."""
        import corpus_db
        if not os.path.exists(corpus_db.DB):
            return True
        try:
            corpus_db.query("CREATE TABLE _drill_should_not_exist (x INTEGER)")
        except Exception:
            return True                      # refused, which is the whole point
        # It succeeded. Undo the damage before reporting the breach, so the drill does not
        # leave the thing it was testing in a worse state than it found it.
        try:
            con = corpus_db.connect()
            con.execute("DROP TABLE IF EXISTS _drill_should_not_exist")
            con.commit()
            con.close()
        except Exception:
            import silence
            silence.note("drill.py:index-write-undo")
        return False
    net(a, "a read-only query really cannot write", index_query_cannot_write,
        "read-only by convention is read-only until somebody is in a hurry")

    def datasette_config_is_generated_not_copied():
        """Two lists of canned queries drift. There must only ever be one."""
        import corpus_db
        p = corpus_db.datasette_metadata()
        with open(p, encoding="utf-8") as fh:
            doc = json.load(fh)
        served = set((doc.get("databases", {}).get("corpus", {}).get("queries") or {}))
        return served == set(corpus_db.CANNED)
    net(a, "the web UI's queries come from CANNED, not a second copy",
        datasette_config_is_generated_not_copied,
        "the CLI and the browser must not answer the same question differently")

    def absent_tool_is_not_reported_as_clean():
        """THE ONE THAT MATTERS. A linter that did not run must never look like a linter that
        ran and found nothing. Simulated by handing `ran_clean`/`missing` the exact shape
        `run()` produces for a tool that is not installed."""
        import secondopinion as SO
        absent = {"ruff": {"status": "NOT INSTALLED", "findings": []},
                  "vulture": {"status": "RAN", "findings": []},
                  "detect-secrets": {"status": "RAN", "findings": []}}
        return (not SO.ran_clean(absent)) and SO.missing(absent) == ["ruff"]
    net(a, "an uninstalled checker is not counted as an all-clear",
        absent_tool_is_not_reported_as_clean,
        "no findings and no checker look identical unless the code refuses to conflate them")

    def outside_opinion_survives_a_broken_tool():
        """A second opinion is optional. It must degrade, not take the library down with it."""
        import secondopinion as SO
        got = SO.run([os.path.join(HERE, "src", "silence.py")])
        return isinstance(got, dict) and set(got) == {"ruff", "vulture", "detect-secrets"} \
            and all("status" in v for v in got.values())
    net(a, "the outside opinion always returns a status for every tool",
        outside_opinion_survives_a_broken_tool,
        "fail-open here, and say so -- an optional check must not be able to halt the park")


# ============================================================== report

def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--to-halt", action="store_true",
                    help="finish by raising a REAL halt so the top rung is observed firing")
    a = ap.parse_args()

    for fn in (drill_queue, drill_dispatch, drill_train, drill_assay, drill_assay_engine,
               drill_no_caps, drill_cache, drill_local_agent, drill_publish, drill_ledgers, drill_two_writer,
               drill_snapshot, drill_stale_writer, drill_policy, drill_fetch, drill_cascade, drill_park,
               drill_workorders, drill_inspector, drill_codewatch, drill_mutation,
               drill_scope, drill_correlation,
               drill_outside):
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
        # A DELIBERATE CORRUPTION IS NOT A FAULT. `mutate.py` breaks source files on purpose and
        # runs THIS as one of its gates, so a breach during a mutation run is the expected
        # answer, not an incident. On 2026-08-25 a drill run that happened to overlap one read a
        # mutated `prose_gate.py`, saw two nets fail, and halted the entire library over code
        # that was about to be restored seconds later.
        #
        # This is CLAUDE.md's own standing lesson pointed at a new target: "a safety that stops
        # work must be distinguishable from a fault that stops work." Here the pair is a safety
        # that refuses because the code is genuinely wrong, and one that refuses because someone
        # made it wrong on purpose to see whether it would. The breach is still PRINTED and still
        # returned -- mutate reads it from stdout, which is how a mutant gets killed. Only the
        # halt is withheld.
        try:
            import mutate as _MUT
            _busy, _ = _MUT.active()
        except Exception:
            _busy = False
        if _busy:
            print("\n%d net(s) did not hold — but a MUTATION RUN IS ACTIVE, so this is the"
                  " expected answer to code that was broken on purpose. NOT halting." % len(breached))
            print("  " + "; ".join(r["net"] for r in breached[:5]))
            return 1
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
