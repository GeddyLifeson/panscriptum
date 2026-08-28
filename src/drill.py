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
import re
import shutil
import sys
import tempfile
import time

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
# RAISED 38 -> 41 on 2026-08-26, and the direction needs its justification because the rule
# attached to this number is "lower it when you clean up, NEVER raise it to go green".
#
# This is the one lawful reason to raise it: the DETECTOR got sharper, not the code worse. Not
# one line of dead code was added. `liveness`'s `used` set was a single flat, scope-blind,
# module-blind bag of every identifier in `src/`, so a LOCAL LOOP VARIABLE named `_p` in
# cleanup.py and tells.py marked every module-level `_p()` in the project as called -- and
# `coverage._p()`, which has zero callers and is named at liveness.py:10 as the founding example
# of why that module exists, was missing from its own report. The detector could not see its own
# worked example.
#
# Usage now resolves the way Python resolves it: a bare name only reaches functions in its OWN
# module, and a cross-module call must arrive as `mod.name`, `from mod import name`, or a string
# handed to getattr. Three functions that were always dead became visible; 38 was a floor being
# ratcheted as though it were a total.
#
# The rule is unchanged and still binds: raising this to make a red drill go green is forbidden.
# Raising it because the instrument now measures something it previously could not is the
# opposite act, and it must be written down like this or the two become indistinguishable.
LIVENESS_CEILING = 41

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


def _sweep_probe_litter(subsystem, site):
    """Close the work orders a synthetic subsystem probe just filed. -> None.

    `stop_subsystem` and `resume_subsystem` each `escalate()`, and an escalation FILES A REAL
    WORK ORDER. The rung-4 probes released the synthetic subsystem they created but never the
    orders, so every battery run left two more behind: at the time this was written the queue
    held SUBSYSTEM_STOPPED for `__drill_rung4__` and `__drill_rung4b__` at MAJOR, addressed to
    RUN, `seen 15x`, beside their matching SUBSYSTEM_RESUMED pair -- six pieces of permanent
    decoration describing subsystems that have never existed. A queue with permanent decoration
    in it is a queue people stop reading, which is the failure mode this whole ladder exists to
    avoid.

    The DRILL_AREA and blast-cap probes have kept this discipline for some time; the rung-4
    pair simply never had it. Resolved by identity (code + subject), so this closes exactly the
    orders this probe filed and nothing else. A cleanup that fails is RECORDED rather than
    swallowed, for the same reason it is next door: a silently failed cleanup produces exactly
    the litter the cleanup exists to prevent, and leaves nobody a way to find out why.
    """
    try:
        import workorders as WO
        for code in ("SUBSYSTEM_STOPPED", "SUBSYSTEM_RESUMED"):
            WO.resolve_code(code, "drill self-test on a synthetic subsystem; not a real fault",
                            where=subsystem, by="drill.py")
    except Exception:
        import silence as _s
        _s.note("drill.py:%s-order-cleanup" % site)


def _quiet(mod):
    """A stand-in for `silence` whose `note()` goes nowhere, for nets that drive real phases.

    `silence.note` arms an atexit flush into `state/failures.json`, so a net that walks a phase's
    failure branch on purpose would file its own synthetic fault in the health ledger on every
    cycle. That is the same litter discipline the DRILL_AREA and blast-cap probes already keep by
    resolving the work orders they file: a battery with side effects is a battery nobody dares
    run on a live library, which is the one place it is worth running.
    """
    import types
    out = types.SimpleNamespace(**{k: getattr(mod, k) for k in dir(mod)
                                   if not k.startswith("__")})
    out.note = lambda *a, **k: None
    return out


def _called_names(path):
    """Every function a file actually CALLS, as a set of spellings, resolved through its imports.

    WHY THIS EXISTS. Three nets in this file asked whether a WORD appeared in a source file and
    called that "the guard is wired". A word is not a call. The run #34 sweep defeated two of
    them on the spot: `"snapshot" in withdraw_chapters.py` is satisfied by the COMMENT sitting
    directly above the snapshot block, so the block could be deleted whole and the net would
    stay green on its own explanation; and `guards_are_wired_where_claimed` was satisfied by a
    `coverage.py` docstring, a `pipeline.py` comment and a `feats.py` comment block — three of
    its six files could lose the import and every use and the net named "every guard is present
    in the file that claims it" would go on holding. That is the failure `_no_programmatic_clear`
    already had rewritten out of it for the same reason: a literal cannot tell code from prose
    about code, and prose about a guard OUTLIVES the guard by design, because the person who
    deletes the call rarely deletes the paragraph explaining why it was there.

    WHAT COMES BACK. For `f()`, `"f"`. For `x.f()`, both `"f"` and `"x.f"`, plus `"m.f"` when
    `x` is an alias this file bound to module `m`. For a bare `f()` where `f` arrived by
    `from m import f`, also `"m.f"`. So a caller can ask for a fully-resolved
    `"cachekey.load"` and not be answered by an unrelated local method of the same name.

    AN UNPARSEABLE FILE RAISES. A file this cannot read is a file nothing has checked, which is
    the "absence read as clean" shape the whole layer exists against; `net()` records a raised
    attack as a BREACH, which is the correct verdict.
    """
    return _call_spellings(_ast_of(path))


def _ast_of(path):
    """The parse tree of one file. Raises on unreadable or unparseable, deliberately.

    A file this cannot read is a file nothing has checked -- the "absence read as clean" shape
    -- and `net()` records a raised attack as a breach, which is the right verdict.
    """
    import ast
    with open(path, encoding="utf-8") as fh:
        return ast.parse(fh.read(), filename=os.path.basename(path))


_SRC_OVERRIDE = None


def _srcdir(src=None):
    """The `src/` directory the source-shape nets read. Defaults to the real one.

    OVERRIDABLE ONLY SO THOSE NETS CAN BE SHOWN GOING RED. Each of them asserts a fact about
    another module's code, and the one way to prove such a net still works is to build the
    defeat it exists to catch -- a copy of `src/` with the real call deleted and a comment
    reproducing its name -- and watch it refuse. A net nobody has ever seen refuse is not
    evidence of anything; it is a green light of unknown provenance. Every `net()` call site
    passes nothing and `_SRC_OVERRIDE` is None in every real run, so the battery always reads
    the real tree; the module-level form exists because several of these nets are closures
    inside their area and cannot be handed an argument.
    """
    return src or _SRC_OVERRIDE or os.path.dirname(os.path.abspath(__file__))


def _defn(tree, name):
    """The `def` or `class` named `name`, at any nesting depth. None if there is not one."""
    import ast
    for n in ast.walk(tree):
        if (isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef))
                and n.name == name):
            return n
    return None


def _call_spellings(tree, node=None):
    """Every call spelling inside `node` (default: the whole module), resolved through the
    module's imports.

    Split out of `_called_names` so a net can ask the question of ONE FUNCTION rather than of a
    whole file: "the escalation happens in the failure branch" and "the file mentions escalate
    somewhere" are different claims, and the nets that used a text window around an anchor
    string were reaching for the first while only ever testing the second.
    """
    import ast
    alias, frm = {}, {}
    for n in ast.walk(tree):
        if isinstance(n, ast.Import):
            for al in n.names:
                alias[al.asname or al.name.split(".")[0]] = al.name
        elif isinstance(n, ast.ImportFrom) and n.module:
            for al in n.names:
                frm[al.asname or al.name] = "%s.%s" % (n.module, al.name)
    out = set()
    for n in ast.walk(node if node is not None else tree):
        if not isinstance(n, ast.Call):
            continue
        fn = n.func
        if isinstance(fn, ast.Name):
            out.add(fn.id)
            if fn.id in frm:
                out.add(frm[fn.id])
        elif isinstance(fn, ast.Attribute):
            out.add(fn.attr)
            if isinstance(fn.value, ast.Name):
                out.add("%s.%s" % (fn.value.id, fn.attr))
                if fn.value.id in alias:
                    out.add("%s.%s" % (alias[fn.value.id], fn.attr))
    return out


def _calls(path, want):
    """Does `path` CALL `want`? A trailing dot asks for any call on that module.

    `_calls(f, "cachekey.")` is "this file calls something on the cachekey module", which is the
    honest form of the claim "cachekey is wired in here" — the specific function matters less
    than the module being reached at a call site at all.
    """
    return _spelled(_called_names(path), want)


def _spelled(got, want):
    """Is `want` among these call spellings? A trailing dot asks for any call on that module."""
    if want.endswith("."):
        return any(c.startswith(want) for c in got)
    return want in got


def _calls_within(tree, node, want):
    """Does the subtree `node` CALL `want`? The scoped form of `_calls`."""
    return _spelled(_call_spellings(tree, node), want)


def _code_strings(node):
    """Every string literal in `node` that is CODE, not PROSE ABOUT CODE.

    Docstrings and floating string blocks are dropped; comments are not in a parse tree at all,
    which is the entire reason these checks moved off the file text. A marker a module raises,
    prints or stores is a fact about what it does. The same words in the paragraph above it are
    a fact about what somebody meant, and prose about a guard reliably OUTLIVES the guard --
    whoever deletes the call rarely deletes the explanation. The two must stop counting as the
    same evidence.
    """
    import ast
    prose = set()
    for n in ast.walk(node):
        if (isinstance(n, ast.Expr) and isinstance(n.value, ast.Constant)
                and isinstance(n.value.value, str)):
            prose.add(id(n.value))
    return {n.value for n in ast.walk(node)
            if isinstance(n, ast.Constant) and isinstance(n.value, str) and id(n) not in prose}


def _says(node, fragment):
    """Does any CODE string in `node` contain `fragment`? Docstrings and comments do not count."""
    return any(fragment in s for s in _code_strings(node))


def _enclosing(tree, target):
    """The innermost `def` containing node `target`, by line span. None if it is at module level.

    Line numbers off the parse tree are not the file-text search these nets are being moved
    away from: they come from the same structure being asserted, and they are how "this call
    happens inside that function" gets asked without threading parent pointers everywhere.
    """
    import ast
    best = None
    for n in ast.walk(tree):
        if not isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef)):
            continue
        if n.lineno <= target.lineno and target.lineno <= (n.end_lineno or n.lineno):
            if best is None or n.lineno > best.lineno:
                best = n
    return best


def _subscript_assigns(node, obj, key):
    """Every `ast.Assign` in `node` of the shape `obj[key] = ...`. -> list of Assign nodes."""
    import ast
    out = []
    for n in ast.walk(node):
        if not isinstance(n, ast.Assign):
            continue
        for t in n.targets:
            if (isinstance(t, ast.Subscript) and isinstance(t.value, ast.Name)
                    and t.value.id == obj and isinstance(t.slice, ast.Constant)
                    and t.slice.value == key):
                out.append(n)
    return out


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
        _unreadable_coverage_is_a_refusal,
        "unknown must mean stop")


def _unreadable_coverage_is_a_refusal():
    """A COVERAGE.json that cannot be read must come back UNKNOWN, and unknown must stop.

    THIS NET COULD NOT FAIL ON ITS NAMED SUBJECT. It was an `or` whose second arm,
    `PG.evidence_ok("nope", 0.35, [])[0] is False`, is word for word the assertion the FIRST net
    of this area already makes ("an unmeasured source is refused"). So the whole expression held
    whatever `cited_fraction` did with an unreadable file: the first arm could have started
    returning `0.0` — UNKNOWN silently becoming ZERO CITED, which is the precise thing this net
    exists to forbid and the shape of the withdrawn batch's three 0.0%-cited sources — and it
    would have stayed green on its neighbour's work. Found by the run #34 sweep.

    Both properties are now asserted separately, and against a COVERAGE.json that is genuinely
    unreadable rather than merely silent about the source asked for — those are different
    questions and only one of them is this net's. `_coverage_rows` is stood in for, so no file
    is moved or damaged to produce the condition. The readable pass first: a stand-in that never
    reached the code under test would make the refusal arm pass for the wrong reason.
    """
    real = PG._coverage_rows
    rows = [{"source": "__drill__", "entries": 100, "cited": 90}]

    def unreadable():
        raise OSError("COVERAGE.json unreadable")

    try:
        PG._coverage_rows = lambda: rows
        if PG.cited_fraction("__drill__") != 0.9 or not PG.evidence_ok("__drill__", 0.35)[0]:
            return False                     # the stand-in never reached the code under test
        PG._coverage_rows = unreadable
        if PG.cited_fraction("__drill__") is not None:
            return False                     # unknown came back as a number
        ok, why = PG.evidence_ok("__drill__", 0.35)
        return ok is False and "COVERAGE.json" in why
    finally:
        PG._coverage_rows = real


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
    """The gate must refuse when its plan is absent — proved WITHOUT moving the owner's plan.

    THIS NET USED TO RENAME THE LIVE `STEP4_PLAN.md`. It moved the owner's 15 KB document to
    `STEP4_PLAN.md.drill-moved`, asked the gate, and restored it in a `finally` — which is the
    exact hazard `_gates_agree` fifteen lines below documents at length as the reason the
    config.yaml write was removed in run #31, reintroduced one function over. `finally` does not
    run when a process is killed, the foreman SIGTERMs stalled jobs as a matter of routine, and
    the supervisor runs this drill every cycle. A kill inside that window ends with the plan on
    disk under a name nothing looks for, this net BREACHING for ever on a file it can no longer
    restore, and the Step 4 gate refusing everything on the grounds that its plan is missing —
    which it then genuinely would be. The drill that exists to prove the gate cannot be opened
    by accident could delete the document the gate is about.

    THE PREDICATE DOES NOT NEED THE REAL FILE. `step4_gate_open` asks
    `os.path.exists(os.path.join(PG.HERE, "STEP4_PLAN.md"))`, so pointing `PG.HERE` at a scratch
    directory puts the same question to the same code about a directory this drill owns. Nothing
    in the repository is touched, and a kill mid-net leaves only an in-memory global that the
    next process re-imports from source anyway. `cfg` is passed explicitly, so config.yaml is not
    read through the redirected root either.

    BOTH DIRECTIONS, because a redirect that silently missed would make the refusal arm pass for
    the wrong reason — the gate would be answering about the real tree and refusing for the real
    tree's reasons. So: with a plan present under the scratch root the gate OPENS, and only then
    is its absence worth anything. And the live plan is checked to be where it belongs first: if
    it is gone, that is a finding, not a net that has nothing to do.
    """
    import shutil
    if not os.path.exists(os.path.join(HERE, "STEP4_PLAN.md")):
        return False                       # the owner's plan is missing — say so, do not pass
    cfg = {"step4_enabled": True}
    root = os.path.join(tempfile.gettempdir(), "drill_step4_root")
    plan = os.path.join(root, "STEP4_PLAN.md")
    saved = PG.HERE
    try:
        shutil.rmtree(root, ignore_errors=True)
        os.makedirs(root, exist_ok=True)
        with open(plan, "w", encoding="utf-8") as f:
            f.write("a stand-in for the ratified plan\n")
        PG.HERE = root
        if PG.step4_gate_open(cfg)[0] is not True:
            return False                   # the redirect never reached the predicate
        os.remove(plan)
        ok, why = PG.step4_gate_open(cfg)
        return ok is False and "STEP4_PLAN.md" in why
    finally:
        PG.HERE = saved
        shutil.rmtree(root, ignore_errors=True)


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
        # AND IF THE CLEANUP ITSELF FAILS, SAY SO. This was `except Exception: pass`, which
        # discarded the one fact worth having: a failed resolve leaves a DRILL_AREA order in the
        # LIVE queue, one per supervisor cycle, for ever -- the exact outcome the paragraph
        # above says the cleanup exists to prevent, arrived at silently. `silence.note` records
        # the site and the live exception in the health ledger, where a swallowed failure in
        # this project is supposed to go.
        try:
            import workorders as WO
            WO.resolve_code("DRILL_AREA", "drill self-test; not a real fault",
                            where="__drill__", by="drill.py")
        except Exception:
            import silence
            silence.note("drill.py:drill-area-cleanup")
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
    net(a, "the halt refuses a programmatic lift AT RUN TIME, in every spelling",
        _no_runtime_clear,
        "the rule was enforced only by a substring scan for two spellings, which an import "
        "alias, a from-import and a getattr each walk straight past")
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


def _halt_is_not_breakage(src=None):
    """The supervisor must consult the halt BEFORE concluding the library is broken.

    ASKED OF THE PARSE TREE, NOT OF THE FILE TEXT. This used to read `overnight.py` as a string,
    take the offsets of "idle >= IDLE_LIMIT" and "it is a broken one", and ask whether
    "_ESC.status()" appeared between them. All three are phrases a COMMENT can carry, and the
    branch in question is nine lines of prose explaining that the halt is checked first -- so
    deleting the check and leaving its explanation, the ordinary shape of a careless edit, left
    this net green over a supervisor that would again mistake a halted library for a broken one
    and exit. That mistake caused this project's longest outage and the net written for it could
    not have seen it happen twice.

    Now the `if idle >= IDLE_LIMIT` branch is found AS a branch, `_ESC.status` has to be CALLED
    inside it, and the halted arm has to `continue` -- wait for a person -- rather than fall
    through to the give-up. No comment produces a Call node or a Continue node.
    """
    import ast
    tree = _ast_of(os.path.join(_srcdir(src), "overnight.py"))
    for n in ast.walk(tree):
        if not isinstance(n, ast.If):
            continue
        t = n.test
        if not (isinstance(t, ast.Compare) and isinstance(t.left, ast.Name)
                and t.left.id == "idle" and len(t.comparators) == 1
                and isinstance(t.comparators[0], ast.Name)
                and t.comparators[0].id == "IDLE_LIMIT"):
            continue
        return (_calls_within(tree, n, "_ESC.status")
                and any(isinstance(x, ast.Continue) for x in ast.walk(n))
                and _says(n, "it is a broken one"))
    return False


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

def _failed_revert_is_escalated(src=None):
    """A revert that FAILS must reach something outliving the process.

    The ALARM existed; nothing carried it. `run()` prints `json.dumps(res)[:110]`, and the keys
    ahead of `ALARM` -- `applied`, `reverted`, and 120 characters of `error` -- push it past the
    cut every time, while the `patches` trail records only patch intent. So the one lane that
    lets a model write to `src/` could leave a half-written module on disk and report success.
    ASKED OF THE PARSE TREE (run #36). The check was a text window: find `out["ALARM"]`, find
    the next `return out`, and look for `_ESC.escalate(` and `_ESC.SAFETY` between them. The
    thirteen lines between those two anchors are a comment block that NAMES the escalation and
    NAMES the rung -- so the `try: import escalation as _ESC; _ESC.escalate(...)` could be
    deleted whole and the net would have gone on holding on the strength of the paragraph
    explaining why it was there. The branch is now located as a branch and the escalation has to
    be a real call inside it, at the SAFETY rung.
    """
    import ast
    tree = _ast_of(os.path.join(_srcdir(src), "local_agent.py"))
    for n in ast.walk(tree):
        if not isinstance(n, ast.If):
            continue
        if not _subscript_assigns(n, "out", "ALARM"):
            continue
        if not _calls_within(tree, n, "_ESC.escalate"):
            continue
        # The RUNG matters as much as the call: escalating this at a lower one would leave a
        # half-written module on disk while the battery went on reporting success.
        for c in ast.walk(n):
            if not (isinstance(c, ast.Call) and isinstance(c.func, ast.Attribute)
                    and c.func.attr == "escalate"):
                continue
            for arg in c.args:
                if isinstance(arg, ast.Attribute) and arg.attr == "SAFETY":
                    return True
    return False


def _run_marks_a_landless_run_failed(src=None):
    """`local_agent.run()` contains a real `out["ok"] = False`. -> bool.

    The half of `_landing_nothing_is_not_success` that has to be read off another module rather
    than driven: `_achievement` can compute the right verdict all day and it changes nothing
    unless `run()` acts on it. Scoped to `run` and asked as an assignment, so neither a comment
    nor a docstring nor the same words in a different function can answer for it.
    """
    import ast
    tree = _ast_of(os.path.join(_srcdir(src), "local_agent.py"))
    run = _defn(tree, "run")
    if run is None:
        return False
    return any(isinstance(n.value, ast.Constant) and n.value.value is False
               for n in _subscript_assigns(run, "out", "ok"))


def _landing_nothing_is_not_success(src=None):
    """The attack: propose patches, land none, and try to be recorded as work done.

    Measured 2026-08-25 on a real order -- 6 turns, 5 tool calls, every propose_patch refused
    with "find string occurs 0 times", and the run returned {"ok": true, "patches": []}. `ok`
    meant "the model stopped talking without breaking anything", which is the one thing a
    caller never needs to know. A maintenance run bulk-routing the LOCAL rung on that flag
    closes every such order having changed nothing.

    Put to the real `_achievement`, not to a copy of its rules. Three shapes, because the net
    has to hold in both directions: all-refused is a FAILURE, a landed patch is a SUCCESS, and
    an answer-only run (no patch attempted) must stay a success -- failing that one would make
    the flag lie the other way, and every survey task would report as broken.
    """
    import local_agent as LA
    refused = [{"outcome": {"applied": False, "error": "find string occurs 0 times"}},
               {"outcome": {"applied": False, "reverted": True, "gate": "pyflakes"}}]
    all_refused = LA._achievement(refused, True)
    landed = LA._achievement([{"outcome": {"applied": True}}], True)
    answered = LA._achievement([], True)
    return (all_refused["landed"] == 0 and all_refused["attempted"] == 2
            and landed["landed"] == 1 and answered["attempted"] == 0
            # and the verdict has to REACH `run()`'s ok, not merely be computable beside it.
            # ASKED OF THE PARSE TREE (run #36): the arm was a whole-file search for the text
            # `out["ok"] = False`, which the comment sitting directly above that line -- "TRIED
            # AND LANDED NOTHING IS NOT SUCCESS" -- is one edit away from carrying itself, and
            # which any of this module's other prose about the flag could reproduce. An
            # assignment is now required to EXIST as an assignment, inside `run`, of False.
            and _run_marks_a_landless_run_failed(src))


def drill_local_agent():
    """The autonomous local writer is staff too, and staff get supervised.

    `local_agent.py` lets the free local model read and PATCH the repo, which is the cheapest
    labour available and also the only actor here that can change the building while nobody is
    watching. Its gate has already been defeated four separate ways (case, name prefix, an NTFS
    alternate data stream, a case-sensitive extension test). These attacks are the fifth family.
    """
    a = "THE NIGHT STAFF — can the local model edit what it must not?"
    import local_agent as LA

    def _junction_out_of_the_writable_surface():
        """The sixth bypass: a name inside the project that is not a PLACE inside the project.

        Every earlier defeat of this gate was a string the filesystem resolved differently --
        letter case, a name prefix, an NTFS alternate data stream, a case-sensitive extension,
        an unlisted directory. A junction is the same trick at directory level: `_safe` ran on
        `os.path.abspath`, which normalises a string and follows nothing, so a link under `src/`
        pointing at `state/` or `data/records/` satisfied the allowlist, missed every denylist,
        and `open(full, "w")` followed it to the real protected file.

        Attacked with a REAL junction, created and removed here, because the whole point is that
        the filesystem disagrees with the string and only the filesystem can demonstrate that.
        Skips rather than fails if the junction cannot be created (no mklink, a filesystem that
        does not support them) -- and says so through the return value rather than passing
        quietly, since a net that cannot run is not a net that held.
        """
        import subprocess as _sp
        import silence as _si
        import local_agent as LA
        link = os.path.join(LA.HERE, "src", "__drill_junction_probe__")
        _sp.run(["cmd", "/c", "mklink", "/J", link, os.path.join(LA.HERE, "state")],
                capture_output=True, text=True,
                creationflags=getattr(_sp, "CREATE_NO_WINDOW", 0))
        if not os.path.isdir(link):
            return False                      # could not stage the attack; not evidence of safety
        try:
            through_link = LA._safe("src/__drill_junction_probe__/failures.json")
            ordinary = LA._safe("src/lognames.py")
        finally:
            try:
                os.rmdir(link)
            except OSError:
                _si.note("drill.py:junction-probe-cleanup")
        # Refused through the link, and the ordinary path still permitted -- a gate that refuses
        # everything passes every refusal test ever written.
        return through_link is None and bool(ordinary) and not os.path.exists(link)
    net(a, "a JUNCTION out of the writable surface is refused",
        _junction_out_of_the_writable_surface,
        "the gate compared a string while the filesystem resolved a different one -- the same "
        "shape as the five bypasses before it, and mutate.py junctions three directories as a "
        "matter of course, so this is a technique the project already uses on itself")

    def _write_lane_checks_the_halt():
        """`local_agent.run` must CALL assert_clear, not merely mention it.

        Written first as a substring scan over the function source, and it passed against a
        regressed build in which the call had been replaced by `pass` -- because the paragraph
        explaining WHY the call is there still contained the word. A literal cannot tell code
        from prose about code, which is the defect the run #35 sweep filed against nine other
        nets in this file. Asked of the parse tree instead: an actual Call node, by either
        spelling, anywhere in the function.
        """
        import ast as _ast
        import inspect as _insp
        import local_agent as LA
        tree = _ast.parse(_insp.getsource(LA.run))
        for node in _ast.walk(tree):
            if not isinstance(node, _ast.Call):
                continue
            fn = node.func
            if isinstance(fn, _ast.Attribute) and fn.attr == "assert_clear":
                return True
            if isinstance(fn, _ast.Name) and fn.id == "assert_clear":
                return True
        return False
    net(a, "the model's write lane asks whether the library is HALTED",
        _write_lane_checks_the_halt,
        "twelve modules consult the halt before working; the ONE lane on which a model may "
        "write to src/ was not among them, and an OWNER halt means nothing starts until a "
        "person rules on it")

    net(a, "a run that proposed patches and landed NONE cannot report success",
        _landing_nothing_is_not_success,
        "ok meant 'the model stopped talking' -- so a run that was refused five times running "
        "was indistinguishable, to the caller closing the order, from work actually done")

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
            # A FAILED CLEANUP IS NOT NOTHING. Was `except Exception: pass`; a resolve that did
            # not happen leaves a LOCAL_AGENT_BLAST_CAP order standing in the live queue on
            # every cycle, and the reason it did not happen was thrown away at the moment it
            # was known. Recorded now, in the ledger the rest of the project uses for exactly
            # this.
            try:
                import workorders as WO
                WO.resolve_code("LOCAL_AGENT_BLAST_CAP", "drill self-test; not a real runaway",
                                by="drill.py")
            except Exception:
                import silence
                silence.note("drill.py:blast-cap-cleanup")
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


def _no_runtime_clear():
    """The four spellings of a programmatic lift, each put to the real `clear()`.

    THE OTHER HALF, AND THE ONE THAT RUNS. `_no_programmatic_clear` below is a literal substring
    scan of `src/` for `escalation.clear(` and `ESC.clear(`. It is worth keeping -- it catches
    the attempt while a person reads the diff -- but as the ONLY enforcement it made the
    asymmetry the whole chain rests on hold against two spellings rather than against the
    capability. `import escalation as X; X.clear(...)`, `from escalation import clear`, and
    `getattr(escalation, "clear")(...)` contain neither string. Run #33's `_by_a_person_at_the_cli`
    makes the refusal true in the code instead: `clear()` demands that `__main__.__file__` BE
    escalation.py and that its immediate caller be escalation's own `main()`, so every spelling
    below is refused for the same reason, from anywhere that is not a person at that CLI.

    SAFE WITH A HALT STANDING, AND CHECKED AGAINST THE SOURCE BEFORE IT WAS RUN. `clear()`
    validates the ruling, then calls `_by_a_person_at_the_cli()`, and only then consults
    `status()` -- so this drill (whose `__main__` is drill.py) is turned away at the second step,
    before the halt file is read and long before anything is written. The ruling passed in is a
    real sentence on purpose: a short one would be refused by the FIRST check and this net would
    silently be re-testing the two `ValueError` nets above instead of the guard it names. Those
    two stay exactly where they are -- they pin the ORDER of the refusals, which `clear()`
    deliberately preserves and documents.

    This is the one place in drill.py that calls `clear`, which is why `verify_math`'s AST check
    exempts this file by name.
    """
    import escalation as _alias
    from escalation import clear as _fromimport
    r = "a ruling long enough to pass the written-ruling check"
    return all(_refuses(c, PermissionError) for c in (
        lambda: ESC.clear(r), lambda: _alias.clear(r),
        lambda: getattr(ESC, "clear")(r), lambda: _fromimport(r)))


def _no_programmatic_clear(src=None):
    """No module in src/ CALLS the halt's release — asked of the AST, not of the text.

    THIS NET BREACHED AGAINST CORRECT CODE (run #34) and the way it did is its own subject. It
    read every `src/*.py` looking for the literal strings `escalation.clear(` and `ESC.clear(`.
    Today `verify_math.py` gained a paragraph EXPLAINING that those are the two spellings this
    scan looks for -- quoting both, in a comment -- and the scan matched the explanation. A
    literal cannot tell code from prose about code: it fails on an honest description and it
    passes on a comment. `verify_math`'s own `_writes_the_config20p` says that in those words,
    after the identical thing happened to it. A breach here HALTS the library, so a false
    positive in this particular net is not a nuisance, it is the outage.

    WIDENED WHILE IT WAS BEING REWRITTEN, because the two spellings were never the property. The
    module-alias set is resolved per file, so `import escalation as X; X.clear()`,
    `from escalation import clear; clear()` and `getattr(escalation, "clear")()` are all caught
    now -- the three spellings the substring scan walked straight past, and the reason the
    runtime guard that `_no_runtime_clear` attacks had to be built at all.

    AN UNPARSEABLE MODULE IS NOT A PASS. It is a file this net could not read, which is the
    "absence read as clean" shape the whole project is built against. `escalation.py` defines
    `clear` and calls it from its own CLI, which is the one sanctioned caller; `drill.py` calls
    it in four spellings on purpose, to prove each is refused.
    """
    import ast
    src = src or os.path.dirname(os.path.abspath(__file__))
    for f in sorted(os.listdir(src)):
        if not f.endswith(".py") or f in ("escalation.py", "drill.py"):
            continue
        try:
            with open(os.path.join(src, f), encoding="utf-8") as fh:
                tree = ast.parse(fh.read(), filename=f)
        except (OSError, SyntaxError):
            return False
        mods, direct = set(), set()
        for n in ast.walk(tree):
            if isinstance(n, ast.Import):
                for al in n.names:
                    if al.name == "escalation":
                        mods.add(al.asname or "escalation")
            elif isinstance(n, ast.ImportFrom) and n.module == "escalation":
                for al in n.names:
                    if al.name == "clear":
                        direct.add(al.asname or "clear")
        for n in ast.walk(tree):
            if not isinstance(n, ast.Call):
                continue
            fn = n.func
            if (isinstance(fn, ast.Attribute) and fn.attr == "clear"
                    and isinstance(fn.value, ast.Name) and fn.value.id in mods):
                return False                          # X.clear(), for any alias X
            if isinstance(fn, ast.Name) and fn.id in direct:
                return False                          # from escalation import clear
            if (isinstance(fn, ast.Call) and isinstance(fn.func, ast.Name)
                    and fn.func.id == "getattr" and len(fn.args) >= 2
                    and isinstance(fn.args[0], ast.Name) and fn.args[0].id in mods
                    and isinstance(fn.args[1], ast.Constant) and fn.args[1].value == "clear"):
                return False                          # getattr(escalation, "clear")()
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
    net(a, "a file OVER two megabytes is scanned, including across the segment seam",
        _the_scanner_reads_files_over_two_megabytes,
        "11.5 MB across four published files was skipped with a bare `continue` and reported "
        "clean; the net above could not see it because its fixture is two lines long")
    net(a, "a staged file that cannot be READ is a hit, not a silence",
        _an_unreadable_staged_file_is_a_hit,
        "'too big to check' and 'could not read' reported as clean is the failure shape this "
        "project refuses, and this is the one gate where next run is not a recovery")
    net(a, "no missing safety is swallowed on the way to a public push",
        _publish_never_swallows_a_missing_safety,
        "three `except ImportError: pass` arms wrapped the ledger guard, the halt and the "
        "mutation interlock -- deleting a module switched its own guard off, quietly")


def _the_scanner_reads_files_over_two_megabytes():
    """SIZE IS NOT A REASON TO SKIP, and the net that should have caught this could not.

    `scan_for_secrets` passed over any staged file above `max_bytes` with a bare `continue` --
    no count, no note, nothing in the result to distinguish "scanned and clean" from "not
    scanned". Four published files were over it: a 3.36 MB register, a 2.97 MB citations file, a
    2.68 MB terminal page and a 2.47 MB data script. That is 11.5 MB reaching the PUBLIC repo
    examined by nothing, reported as clean. (Hand-scanned afterwards, and clean -- this time.)

    WHY 57 NETS MISSED IT. `_scanner_finds_a_planted_secret` above plants its secret in a
    TWO-LINE temp file, so the branch that skipped big files was never on the path it walked.
    The net was not weak; it was aimed at a file the bug could not affect. So the fixture is the
    fix here: three files that actually cross the threshold, in the three shapes the streaming
    reader has to handle.

      * an ordinary multi-line file over 2 MB, with the secret at the very end;
      * a SINGLE-LINE file over 2 MB -- a 3 MB one-line JSON register IS one line, and the naive
        repair (read line by line) still loads the whole thing;
      * a secret STRADDLING THE SEGMENT SEAM, which is the failure a segmented reader invents
        for itself: split a long line into blocks and the value that spans the cut disappears
        from both halves. `_SCAN_OVERLAP` is what makes it survive, and this is what tests it.

    And a clean file of the same size must still come back quiet, or the net is a wall.
    """
    import shutil
    import publish as P
    d = tempfile.mkdtemp(prefix="scanbig_")
    filler = "the custodian recorded the specimen in the usual manner. "
    try:
        def only(name, body):
            for f in os.listdir(d):
                os.remove(os.path.join(d, f))
            with open(os.path.join(d, name), "w", encoding="utf-8") as fh:
                fh.write(body)
            return P.scan_for_secrets(d)

        long_line = filler * 55_000                     # ~3.1 MB, no newline anywhere
        if not only("big.md", filler * 40_000 + _AWS_EXAMPLE + "\n"):
            return False
        if not only("register.json", _AWS_EXAMPLE + long_line):
            return False
        seam = P._SCAN_BLOCK and 2_000_000              # the default line cap
        if not only("minified.js", long_line[:seam - 10] + _AWS_EXAMPLE + long_line[:400_000]):
            return False
        return not only("clean.md", filler * 40_000)
    finally:
        shutil.rmtree(d, ignore_errors=True)


def _an_unreadable_staged_file_is_a_hit():
    """"Could not read it" must reach the caller as a REFUSAL, never as an empty result.

    The twin of the size skip, in the same function and with the same bare `continue`: a staged
    file that raised on open was passed over silently. This is the one gate where "we caught it
    next run" is not a recovery, because by then the bytes are public -- so an unreadable file is
    reported BY NAME as an `UNSCANNABLE` finding at line 0, which blocks the push and puts it in
    front of a person.

    THE FAILURE IS DELIVERED BY A STAND-IN, and it has to be. `scan_for_secrets` opens with
    `errors="replace"`, so no CONTENT can make it raise; what raises is the filesystem refusing
    the open -- a Windows lock, a permission, a file deleted between the walk and the read --
    and none of those can be scheduled from inside a test (`os.chmod(p, 0)` does not deny reads
    on this filesystem; it was tried). So `_scan_units` refuses this one path and the real
    handler in `scan_for_secrets` is what is under test, exactly as `_throttle_hands_off` puts a
    stand-in where the real `quarantine()` would write to disk.
    """
    import shutil
    import publish as P
    d = tempfile.mkdtemp(prefix="scanlocked_")
    real = P._scan_units
    try:
        for name in ("locked.json", "readable.md"):
            with open(os.path.join(d, name), "w", encoding="utf-8") as f:
                f.write("nothing secret here at all\n")

        def refusing(path, cap):
            if os.path.basename(path) == "locked.json":
                raise PermissionError(13, "the file is held open by another process")
            return real(path, cap)
        P._scan_units = refusing
        hits = P.scan_for_secrets(d)
        return (len(hits) == 1 and hits[0][0].endswith("locked.json") and hits[0][1] == 0
                and "UNSCANNABLE" in hits[0][2])
    finally:
        P._scan_units = real
        shutil.rmtree(d, ignore_errors=True)


def _publish_never_swallows_a_missing_safety(path=None):
    """No `except ImportError` in publish.py may pass. All three arms wrapped a SAFETY.

    `ledger_guard`, `escalation` and the `mutate` interlock were each imported under a bare
    `except ImportError: pass`, so deleting, renaming or breaking any one of those modules
    silently switched its guard off in the job that pushes to a PUBLIC repo -- and the mutation
    interlock exists precisely because a push once shipped a deliberately corrupted
    `prose_gate.py` to GitHub. The swallow made the interlock's own absence the condition under
    which it stops working, which is the one condition it has to survive.

    Asked of the AST because that is the lesson of the same morning: `_no_programmatic_clear`
    breached today on a COMMENT quoting the strings it grepped for, and a `grep -c` here would
    fail the same way the first time somebody writes the phrase in a docstring explaining why it
    is banned. A handler passes only if it raises. The count is asserted too -- three arms must
    still BE there, or a net that requires every handler to raise is satisfied by a file with no
    handlers left at all.
    """
    import ast
    src = path or os.path.join(os.path.dirname(os.path.abspath(__file__)), "publish.py")
    with open(src, encoding="utf-8") as f:
        tree = ast.parse(f.read(), filename="publish.py")
    arms = 0
    for n in ast.walk(tree):
        if not isinstance(n, ast.ExceptHandler):
            continue
        names = [x.id for x in ast.walk(n.type or ast.Pass()) if isinstance(x, ast.Name)]
        if "ImportError" not in names:
            continue
        arms += 1
        if not any(isinstance(b, ast.Raise) for b in ast.walk(n)):
            return False
    return arms >= 3


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


# ============================================================== THE DONE-KEY (permanent loss)

def _chain_done_key_follows_the_disk():
    """Phase 4's done-key must be gated on the artifact, not on the writer's say-so.

    THE THIRTEENTH LANDING, found by the run #33 sweep. `gate_done` closed the twelve `land_json`
    call sites, where the writer returns a landed/not-landed verdict. Phase 4 writes through
    `chain.write_result` instead -- one schema, one writer, which is right -- and that function
    returns the DOCUMENT IT BUILT, unconditionally, whatever the disk said. A denied rename was
    printed to stderr and nowhere else, so the call site appended its done-key regardless. Because
    a done-key is permanent, no later run would ever redo phase 4: `CHAIN.json` would hold the
    PREVIOUS cycle's fit for ever while `PIPELINE_STATE.json` recorded the phase complete. That
    is not one lost cycle -- phase artifacts are read by later phases in the SAME run.

    BOTH HALVES, because either alone can be removed without the other looking wrong: the
    comparator must say no to a document that differs from the file, and the PHASE must then
    leave "chain" out of `st["done"]`. And both directions of each, since a comparator that
    always says no would close the phase for ever in the other direction.

    The phase is driven against a stand-in `chain` module in `sys.modules` -- `phase_chain` does
    its `import chain as CH` inside its own body -- with `log` and `save_state` silenced, so no
    real harvest runs and `state/PIPELINE_STATE.json` is never touched.
    """
    import shutil
    import types
    import silence as _S
    import pipeline as PL
    d = tempfile.mkdtemp(prefix="drillchain_")
    doc = {"schema": 1, "edges": {"a>b": 3}, "fit": {"identified": True}}
    stub = types.ModuleType("chain")
    stub.OUT = os.path.join(d, "CHAIN.json")
    stub.built = doc
    stub.harvest = lambda: [{"row": i} for i in range(20)]
    stub.extract = lambda rows, workers=8: ({("a", "b"): 1}, [], {})
    stub.adjudicate_mutuals = lambda edges, prov: edges
    stub.fit = lambda edges, prior=0.5: {"identified": True, "components": [],
                                         "deviance_per_df": 1.0}
    stub.write_result = lambda edges, res, unmatched: stub.built
    had, prev = "chain" in sys.modules, sys.modules.get("chain")
    keep = (PL.log, PL.save_state, PL.silence)
    try:
        with open(stub.OUT, "w", encoding="utf-8") as f:
            json.dump(doc, f)
        PL.log = lambda *a, **k: None
        PL.save_state = lambda st: None
        PL.silence = _quiet(_S)
        sys.modules["chain"] = stub
        if PL._chain_landed(stub, doc) is not True:
            return False                                  # what IS on disk must read as landed
        if PL._chain_landed(stub, dict(doc, edges={"a>b": 4})) is not False:
            return False                                  # ... and what is not, must not
        stub.built = dict(doc, edges={"a>b": 99})         # the write that did NOT land
        st = {"done": {}, "units_done": 0}
        PL.phase_chain({}, st)
        if "chain" in st["done"]:
            return False
        stub.built = doc                                  # ... and the one that did
        st = {"done": {}, "units_done": 0}
        PL.phase_chain({}, st)
        return st["done"].get("chain") == ["all"]
    finally:
        PL.log, PL.save_state, PL.silence = keep
        if had:
            sys.modules["chain"] = prev
        else:
            sys.modules.pop("chain", None)
        shutil.rmtree(d, ignore_errors=True)


def _write_phase_stays_open_when_everything_refuses():
    """`all([])` is True, and two very different histories arrive at an empty list.

    Phase 8 marks itself done on `all(landed)`, and an empty `landed` is deliberately a pass: a
    phase that correctly wrote nothing must not be held open for ever, and there is a drill net
    on exactly that. But `landed` is ALSO empty when every ready source raised inside
    `build_jobs_for_source` and fell into `refused` instead -- "nothing needed building" and
    "everything refused to build" reaching the same verdict by the same arithmetic. Marked done,
    the second is permanent: no later run redoes phase 8, no manifest exists, and nothing
    anywhere records that a total build failure happened. (run #33)

    Both histories are put to the phase here, since the whole defect was that they were
    indistinguishable. `WRITE_SETTLED_MIN` is dropped to zero so the real `COVERAGE.json` yields
    a non-empty ready set whatever the corpus looks like today -- a net whose result depends on
    how well-read the library happens to be is not measuring what it claims to. Every manifest
    call is a stand-in, so no manifest is built and nothing is written.
    """
    import silence as _S
    import manifest_builder as MB
    import pipeline as PL
    keep_pl = (PL.log, PL.save_state, PL.silence, PL.WRITE_SETTLED_MIN)
    keep_mb = (MB.load_config, MB.load_roll, MB.load_record, MB.spine_code_for,
               MB.build_jobs_for_source)

    def refuses(*a, **k):
        raise RuntimeError("drill: this source will not build")
    try:
        PL.log = lambda *a, **k: None
        PL.save_state = lambda st: None
        PL.silence = _quiet(_S)
        PL.WRITE_SETTLED_MIN = 0.0
        MB.load_config = lambda: {}
        MB.load_roll = lambda cfg: []
        MB.load_record = lambda cfg, source_name: {"source": source_name, "entries": []}
        MB.spine_code_for = lambda source: "XX"
        MB.build_jobs_for_source = refuses
        st = {"done": {}, "units_done": 0}
        PL.phase_write({}, st)
        if "write" in st["done"]:
            return False
        # ... and the vacuous case is still allowed to close, or the phase never finishes.
        MB.build_jobs_for_source = lambda cfg, roll_entry, record, spine: []
        st = {"done": {}, "units_done": 0}
        PL.phase_write({}, st)
        return st["done"].get("write") == ["all"]
    finally:
        PL.log, PL.save_state, PL.silence, PL.WRITE_SETTLED_MIN = keep_pl
        (MB.load_config, MB.load_roll, MB.load_record, MB.spine_code_for,
         MB.build_jobs_for_source) = keep_mb


def _a_denied_batch_write_stays_on_the_failed_list():
    """A success retires an earlier failure. A DENIED WRITE is not a success.

    The pop that clears `st["failed"]["entrypass"][key]` used to sit outside the if/elif/else and
    fired on all three paths -- including "the write was denied" and "judged 6 of 20" -- so any
    non-None answer from the model retired a recorded failure whether or not anything landed. Its
    correctly-gated twin in `phase_synthesis` only reaches its pop after the write succeeds. The
    damage is to the health signal rather than to the corpus, and that is worse than it sounds: a
    batch under sustained write contention could sit at ZERO entries in `st["failed"]`, which is
    the number `update_handoff` publishes to the owner as "Failures logged". This library runs
    unattended for days on that one line, and it went quiet exactly when it should have been
    loudest. (run #33)

    Driven with `records`, `ask_pool_first` and `write_record` all replaced: one synthetic record
    that exists only in memory, a model answer that judges its single entry in full, and a write
    that is denied. No model is called, no record is read, and `save_state` and `update_handoff`
    are silenced so nothing in `state/` or `handoff/` moves.
    """
    import silence as _S
    import pipeline as PL
    key = "__drill__#0"
    rec = {"source": "__drill__", "synthesis": {},
           "entries": [{"name": "Drill Entity", "type": "person",
                        "description": "a synthetic entry that exists only in this test"}]}
    keep = (PL.log, PL.save_state, PL.records, PL.write_record, PL.ask_pool_first,
            PL.update_handoff, PL.silence)
    try:
        PL.log = lambda *a, **k: None
        PL.save_state = lambda st: None
        PL.update_handoff = lambda st: None
        PL.silence = _quiet(_S)
        PL.records = lambda: [(os.path.join(HERE, "data", "records", "__drill__.json"), rec)]
        PL.ask_pool_first = lambda *a, **k: {"results": [
            {"index": 0, "category": 1, "topic": "Persons", "magnitude": "M1",
             "scale_note": "lifted a gate weighing some ten tonnes off its hinges"}]}
        PL.write_record = lambda path, r: False
        st = {"done": {}, "failed": {"entrypass": {key: "ollama failure"}}, "units_done": 0}
        PL.phase_entrypass({}, st)
        return (st["failed"]["entrypass"].get(key) == "write denied"
                and key not in st["done"].get("entrypass", []))
    finally:
        (PL.log, PL.save_state, PL.records, PL.write_record, PL.ask_pool_first,
         PL.update_handoff, PL.silence) = keep


def _run_the_runner(verdicts):
    """Drive `pipeline.main()`'s phase loop over stubbed phases. -> (st, [phases that ran]).

    `verdicts` maps a phase number to what its stand-in returns. Phases past the stubs are
    absent from `IMPLEMENTED`, so the loop hits its "not implemented yet" branch and stops --
    which is the loop's own clean exit, not a special case built for this.

    THE HALT INTERLOCK IS STOOD IN FOR, NOT LIFTED. `main()` calls `escalation.assert_clear`
    first thing, deliberately, so there is no path into the job that skips it -- and the library
    is halted while this is being written. The drill may not clear a halt (that is the point of
    the four nets in THE PARK), so a stand-in `escalation` answers that one question for the
    duration and is restored in the `finally`. Nothing else here reaches the disk either:
    `load_state`, `save_state`, `log` and `update_handoff` are all stand-ins, so the real
    `state/PIPELINE_STATE.json` -- the file that actually carries this bug -- is never read or
    written by the net that tests for it.
    """
    import types
    import silence as _S
    import pipeline as PL
    ran = []
    st = {"phase": 1, "done": {}, "failed": {}, "units_done": 0, "started": "drill"}
    esc = types.ModuleType("escalation")
    esc.assert_clear = lambda who="?": True
    had, prev = "escalation" in sys.modules, sys.modules.get("escalation")
    keep = (PL.log, PL.load_state, PL.save_state, PL.update_handoff, PL.IMPLEMENTED, PL.silence)
    # `main()` parses sys.argv, and the drill's own argv is not the runner's. `drill.py
    # --to-halt` would otherwise reach pipeline's parser as an unrecognised argument and kill
    # this net with a SystemExit -- a net that only holds when the drill is invoked one
    # particular way is a net that holds by luck.
    argv = sys.argv

    def phase(n):
        def fn(c, s):
            ran.append(n)
            return verdicts[n]
        return fn
    try:
        sys.argv = ["pipeline.py"]
        sys.modules["escalation"] = esc
        PL.log = lambda *a, **k: None
        PL.load_state = lambda: st
        PL.save_state = lambda s: None
        PL.update_handoff = lambda s: None
        PL.silence = _quiet(_S)
        PL.IMPLEMENTED = {n: phase(n) for n in verdicts}
        PL.main()
        return st, ran
    finally:
        sys.argv = argv
        (PL.log, PL.load_state, PL.save_state, PL.update_handoff, PL.IMPLEMENTED,
         PL.silence) = keep
        if had:
            sys.modules["escalation"] = prev
        else:
            sys.modules.pop("escalation", None)


def _the_pointer_stops_at_the_open_phase():
    """The resume pointer must not walk past a phase that did not report completion.

    THE RUNNER WAS PERMANENTLY NO-OPPING (m37). `st["phase"] = ph + 1` ran unconditionally at
    the bottom of the loop -- including for the phases that deliberately return early to stay
    open, and for every `gate_done` that refused to mark its phase done. Nothing read
    `st["done"]` for phases 3-8. So the pointer walked to the end over work that had never
    completed, `range(9, 9)` was empty, and `main()` exited **0** for as long as it sat there:
    twice a cycle, cleanly, doing nothing at all. Stopping and finishing produced the same
    signal, which is this project's standing lesson with the runner's name on it. The live state
    shows it happened and was hand-reset five times.

    THREE VERDICTS, because the shape that hid it was the third. `False` is a phase saying it
    stayed open. `None` is a phase saying nothing -- and phases 4 through 8 returned `None` on
    every path, which is exactly why an unconditional advance looked fine for so long. Only an
    explicit `True` may move the pointer; anything else is incomplete, and the stall is RECORDED
    in `st["failed"]["runner"]` rather than merely logged, because a fault whose only trace is a
    line in a log file is not one the handoff can count.

    The later phases still run -- they may make progress from artifacts already on disk -- but
    the resume point stays behind the open work, which is the only thing a pointer is for.
    """
    for verdict in (False, None):
        st, ran = _run_the_runner({1: True, 2: verdict, 3: True})
        if st.get("phase") != 2 or ran != [1, 2, 3]:
            return False
        if "entrypass" not in (st.get("failed", {}).get("runner") or {}):
            return False
        if "weave" in (st.get("failed", {}).get("runner") or {}):
            return False                     # phase 3 reported completion; it is not the stall
    # ... and a run where every phase reports True must still advance, or the pointer never moves.
    st, ran = _run_the_runner({1: True, 2: True, 3: True})
    return st.get("phase") == 4 and ran == [1, 2, 3] and not st.get("failed", {}).get("runner")


def _a_done_marker_cannot_accumulate():
    """"all" twice cannot mean more than "all" once, and the live state says it did.

    Every phase-level marker in `pipeline.py` is the literal string "all" -- "this phase, whole,
    is finished" -- and both `gate_done` and the phases that mark themselves appended it
    unguarded on every run. The state on disk grew `write: ["all"] * 5` and
    `weave: ["all"] * 4`: a count of how many times the phase was re-run, kept in the field that
    answers whether it is done. Nothing reads the length, so nothing objected, and the field that
    should have exposed the runner's no-op was itself unreadable as evidence.

    Both doors, because there are two: the marker itself, and the gate that calls it.
    """
    import silence as _S
    import pipeline as PL
    keep = (PL.log, PL.silence)
    try:
        PL.log = lambda *a, **k: None
        PL.silence = _quiet(_S)
        st = {"done": {}}
        first = PL.mark_done(st, "weave")
        again = [PL.mark_done(st, "weave") for _ in range(4)]
        if st["done"]["weave"] != ["all"] or first is not True or any(again):
            return False
        st = {"done": {}}
        for _ in range(5):
            PL.gate_done(st, "write", [True, True])
        if st["done"]["write"] != ["all"]:
            return False
        # The per-unit lists are genuinely accumulative and must NOT be flattened with them.
        st = {"done": {}}
        PL.mark_done(st, "synthesis", "marvel")
        PL.mark_done(st, "synthesis", "dc")
        PL.mark_done(st, "synthesis", "marvel")
        return st["done"]["synthesis"] == ["marvel", "dc"]
    finally:
        PL.log, PL.silence = keep


def _the_catalogue_cannot_erase_what_it_did_not_author():
    """A key the caller did not write must not overwrite one the disk holds.

    THE DATA LOSS THIS STOPPED, and it was running. `write_record_catalogue` merged only
    `rec["entries"]` and then dumped `rec` WHOLE, so every top-level key the caller had not
    authored was destroyed by the write that followed the merge. `catalogue_web.catalogue()`
    returns `"synthesis": None` -- correctly, because a wiki lead paragraph is not an Assay --
    and that None landed on the pipeline's `ceiling_entity` and `provisional_magnitude` and
    erased them. 31 of 216 records carry a null synthesis, 26 of them nulled in 24 hours, DC
    among them at 44,958 entries. It does not self-heal: `phase_synthesis` skips a source already
    in its done-keys, so the block stays null for ever. Two records lost `purged_roster` to
    simple absence.

    THREE STATES, because the fix rests on telling them apart: `None` and absent both mean "did
    not author this" and preserve the disk value, while an explicit `{}`/`[]`/`""` is a
    deliberate statement and still clears. "Did not compute this field" and "means to clear this
    field" are different acts, and a merge that cannot read minds must take the recoverable side.

    AND THE ENTRY DIRECTION MUST BE UNCHANGED, which is the half a net pinning the new behaviour
    could quietly undo. The catalogue's fresh cast IS the authority here -- that asymmetry is the
    whole reason this writer exists beside `write_record` -- so a larger new cast still wins,
    disk-only entries still survive (a merge never shrinks a cast), and the disk copy's per-entry
    judgments still carry forward onto matching names.

    A throwaway record in a temp directory. Nothing in `data/records/` is opened.
    """
    import shutil
    import silence as _S
    import pipeline as PL
    d = tempfile.mkdtemp(prefix="drillcat_")
    keep = (PL.log, PL.silence)
    try:
        PL.log = lambda *a, **k: None
        PL.silence = _quiet(_S)
        path = os.path.join(d, "drill_source.json")
        with open(path, "w", encoding="utf-8") as f:
            json.dump({"source": "drill", "mode": "web",
                       "synthesis": {"provisional_magnitude": "M4", "ceiling_entity": "someone"},
                       "purged_roster": ["a struck name"],
                       "note_from_disk": "a value the caller means to clear",
                       "entries": [{"name": "A", "magnitude": "M3", "topic": "Persons",
                                    "catalogued": True},
                                   {"name": "OnlyOnDisk", "magnitude": "M2"}]}, f)
        rec = {"source": "drill", "mode": "web",
               "synthesis": None,                    # "I did not author this"
               "note_from_disk": "",                 # ... and this one I DID mean to clear
               "entries": [{"name": "A"}, {"name": "B"}]}   # a fresher, larger cast
        if PL.write_record_catalogue(path, rec) is not True:
            return False
        with open(path, encoding="utf-8") as f:
            out = json.load(f)
        names = {e.get("name") for e in out.get("entries") or []}
        a = next(e for e in out["entries"] if e.get("name") == "A")
        return ((out.get("synthesis") or {}).get("provisional_magnitude") == "M4"
                and out.get("purged_roster") == ["a struck name"]
                and out.get("note_from_disk") == ""
                and names == {"A", "B", "OnlyOnDisk"}
                and a.get("magnitude") == "M3" and a.get("topic") == "Persons")
    finally:
        PL.log, PL.silence = keep
        shutil.rmtree(d, ignore_errors=True)


def drill_done_keys():
    """A done-key is permanent, so writing one over a failed write is permanent loss."""
    a = "THE DONE-KEY — is a phase marked complete over an artifact that never landed?"
    net(a, "phase 4's done-key is gated on what is ON DISK, not on what the writer returned",
        _chain_done_key_follows_the_disk,
        "the thirteenth landing: chain.write_result hands back the document whatever the disk "
        "said, so a denied rename left phase 4 complete over the previous cycle's fit for ever")
    net(a, "phase 8 stays OPEN when every ready source refuses to build",
        _write_phase_stays_open_when_everything_refuses,
        "all([]) is True, and 'nothing needed building' and 'everything refused' arrived at the "
        "same empty list -- one of them permanently")
    net(a, "a denied batch write is RECORDED and does not retire the earlier failure",
        _a_denied_batch_write_stays_on_the_failed_list,
        "the pop fired on all three branches, so a batch under write contention published ZERO "
        "failures to the owner's handoff while failing every round")
    net(a, "the resume pointer stops at the first phase that did not report completion",
        _the_pointer_stops_at_the_open_phase,
        "m37: the pointer advanced unconditionally, walked past eight phases that never "
        "finished, and main() then exited 0 twice a cycle having done nothing at all")
    net(a, "a phase-level done marker cannot accumulate duplicates",
        _a_done_marker_cannot_accumulate,
        "the live state carries write:['all']*5 and weave:['all']*4 -- a re-run counter in the "
        "field that answers whether the phase is finished, which is how the no-op stayed hidden")
    net(a, "the catalogue writer cannot erase a key it did not author",
        _the_catalogue_cannot_erase_what_it_did_not_author,
        "catalogue_web's honest `synthesis: None` was dumped whole over the pipeline's Assay "
        "block: 26 records nulled in 24 hours, DC among them, and it does not self-heal")


# ============================================================== THE HANDLE (the world profile)

def drill_profile():
    """One string that says everything — including, if the alphabet is wrong, something else."""
    a = "THE PROFILE — can a world profile decode to a world that was never encoded?"
    import profile as PR
    net(a, "the address alphabet holds exactly 32 distinct symbols",
        lambda: len(PR.B32) == 32 and len(set(PR.B32)) == 32,
        "it carried 33 until run #33: `_b32` masks with `n & 31` so the 33rd symbol was "
        "unwritable, while `_unb32` had no mask and would happily read it")
    net(a, "a profile carrying a character outside the alphabet REFUSES",
        lambda: _refuses(lambda: PR.decode("PS-1u-hfc-0000-u0"), ValueError),
        "an alphabet that can read what it cannot write is a decoder that cannot say 'this is "
        "not one of mine' -- it returned a silently wrong ADDRESS instead")
    net(a, "and in the feature digits too, not only the address",
        lambda: _refuses(lambda: PR.decode("PS-1a-hfc-000i-u0"), ValueError),
        "the regex admits every letter a-z; only the alphabet knows which are digits")
    net(a, "a well-formed profile still decodes",
        lambda: PR.decode("PS-1a-hfc-0000-u0")["address"] == 42,
        "a decoder that refuses everything is a wall, not a format")


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


def _verify_reads_the_bytes_under_a_restored_directory():
    """`verify()` end to end, against a restore that returns the right SIZE and the wrong bytes.

    The net above puts the two refusals directly to `_dir_matches`, which proves the comparator
    can say no. It cannot prove that `verify()` ASKS it -- `verify` restores a snapshot it just
    took, so the two sides are identical by construction and the directory branch is never given
    anything to reject. That is the same shape as the original defect: a check whose only inputs
    are ones it must accept.

    So `restore` is replaced with one that restores faithfully and then mangles a nested file AT
    THE SAME LENGTH, which is precisely the answer a stat-only or shallow compare would wave
    through, and `verify` must return False with a reason that says the bytes differ. Under
    `state/` because `snapshot._rel` takes paths relative to the repo root; the scratch tree AND
    the snapshot it produces are both removed in the `finally`, so this leaves no `drill-*`
    directory behind.
    """
    import shutil
    import snapshot as SNAP
    d = tempfile.mkdtemp(prefix="drillvfy_", dir=os.path.join(HERE, "state"))
    sid = None
    real_restore = SNAP.restore
    try:
        os.makedirs(os.path.join(d, "nested"))
        with open(os.path.join(d, "nested", "chapter.txt"), "w", encoding="utf-8") as f:
            f.write("a chapter, nested\n")
        sid = SNAP.before("drill-verify", [d], note="drill self-test (verify)")
        if not SNAP.verify(sid)[0]:
            return False
        rel = SNAP._rel(d).replace("/", os.sep)

        def restore_then_mangle(s, into=None):
            n = real_restore(s, into=into)
            with open(os.path.join(into, rel, "nested", "chapter.txt"), "w",
                      encoding="utf-8") as fh:
                fh.write("a chapter, tested\n")     # same length, one byte different
            return n
        SNAP.restore = restore_then_mangle
        ok, why = SNAP.verify(sid)
        return (not ok) and "differ" in why
    finally:
        SNAP.restore = real_restore
        shutil.rmtree(d, ignore_errors=True)
        if sid:
            shutil.rmtree(os.path.join(SNAP.ROOT, sid), ignore_errors=True)


def _withdrawal_takes_a_snapshot(path=None):
    """`withdraw_chapters.py` must CALL for a copy, and must VERIFY it, before it moves a file.

    THIS NET WAS SATISFIED BY A COMMENT. It tested `"snapshot" in <the file's text>`, and the
    word appears at `withdraw_chapters.py:50` inside the paragraph that sits directly above the
    code — "A COPY BEFORE THE IRREVERSIBLE STEP ... the instinct was the ONLY thing standing
    behind 145 chapters". So the import, the `SNAP.before(...)`, the `SNAP.verify(...)` and the
    refusal that raises on a bad copy could all be deleted and this net would go on holding, on
    the strength of the sentence explaining why they used to be there. Found by the run #34
    sweep. The failure is the one `_no_programmatic_clear` was rewritten out of for the same
    reason: prose about a guard outlives the guard.

    So the AST is asked instead, and for both halves. `before()` alone is not the property —
    "an untested backup is a belief, not a backup" is this area's own first line, and the script
    itself raises `SnapshotFailed` when `verify` says no. A withdrawal that takes a copy and
    never opens it has the same evidence behind it as one that took none.
    """
    p = path or os.path.join(os.path.dirname(os.path.abspath(__file__)),
                             "withdraw_chapters.py")
    return _calls(p, "snapshot.before") and _calls(p, "snapshot.verify")


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
    net(a, "verify() itself reads the bytes under a restored DIRECTORY",
        _verify_reads_the_bytes_under_a_restored_directory,
        "the comparator being able to say no proves nothing if verify never hands it anything "
        "to reject; a same-length corruption is what a shallow compare waves through")
    # `before()` makes the destination directory BEFORE it discovers it captured nothing, so the
    # refusal below leaves an empty `drill-empty-*` behind on every run -- the other half of the
    # litter the cleanup at the end of this function closes. Noted rather than fixed in
    # `snapshot.py`, which this file does not own; what is removed here is only what this net
    # just made, found by difference so nothing older is touched.
    _empty_before = set(os.listdir(SNAP.ROOT)) if os.path.isdir(SNAP.ROOT) else set()
    net(a, "an EMPTY snapshot raises rather than passing",
        lambda: _refuses(lambda: SNAP.before("drill-empty", ["no/such/path"]),
                         SNAP.SnapshotFailed),
        "a snapshot that captured nothing is a missing one wearing the same name")
    import shutil as _sh0
    for _new in (set(os.listdir(SNAP.ROOT)) - _empty_before
                 if os.path.isdir(SNAP.ROOT) else ()):
        _sh0.rmtree(os.path.join(SNAP.ROOT, _new), ignore_errors=True)
    net(a, "the withdrawal script takes one before moving anything",
        _withdrawal_takes_a_snapshot,
        "145 chapters were withdrawn with nothing but an instinct behind them")
    # THE DRILL'S OWN LITTER, and it had been accumulating since this area was written: the
    # `before()` above takes a real snapshot on every run and nothing removed it, so
    # `state/snapshots/` held 151 orphaned `drill-*` directories by run #34 -- one per drill,
    # for months. Removed only now that every net that needed it has run. Same discipline as the
    # DRILL_AREA and blast-cap probes resolving the work orders they file, and the same reason:
    # a shared area carrying permanent decoration is one people stop reading. The 151 already
    # there are left alone -- deleting a backup somebody may be keeping is the owner's call, not
    # a side effect of a test tidying up after itself.
    import shutil as _sh
    _sh.rmtree(os.path.join(SNAP.ROOT, sid), ignore_errors=True)


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

        def reason_matches_verdict():
            """A denied rename must not come back describing itself as a landing.

            `replace_if_unchanged` returned `..., "landed"` unconditionally on its last line, so
            a DENIED rename came back as `(False, "landed")` -- and every caller that logs the
            reason, `runguard.claim()` among them since it was routed here, printed "landed" for
            a write that did not land. The two halves of the return disagreed, and the half that
            reaches a human was the wrong one.

            The denial is taken by a stand-in for `replace_retry`, because the real one only
            fails when Windows actually refuses a rename -- a condition no test can schedule, and
            waiting for it is how this went unnoticed. The file must also be untouched afterwards:
            a reason is not evidence if the write happened anyway.
            """
            t3 = dst + ".tmp3"
            with open(t3, "w", encoding="utf-8") as f:
                f.write('{"v":"DENIED"}')
            before = open(dst, encoding="utf-8").read()
            real = S.replace_retry
            try:
                S.replace_retry = lambda tmp_, dst_, attempts=5: False
                ok, why = S.replace_if_unchanged(t3, dst, S.digest_of(dst))
            finally:
                S.replace_retry = real
            return (ok is False and why != "landed" and "could not be renamed" in why
                    and open(dst, encoding="utf-8").read() == before)
        net(a, "a DENIED rename gives back the reason it was denied, not 'landed'",
            reason_matches_verdict,
            "runguard.claim() printed 'landed' for a write that did not land, because the "
            "reason string was returned unconditionally beside a False verdict")
    finally:
        import shutil
        shutil.rmtree(d, ignore_errors=True)


# ============================================================== POLICY (checks as data)

def _partial_canary_merges(tmp=None):
    """A five-host `--host` run must not land a five-host estate over a two-hundred-host one.

    Driven against the REAL `run()` with the network stubbed out, in a temporary OUT, because
    the fault is in what gets WRITTEN and a source scan would pass against a merge that was
    written but wrong. The standing report is seeded with two hosts, one host is re-probed, and
    the file afterwards must still describe both.
    """
    import binding_health as BH
    tmpdir = tmp or tempfile.mkdtemp(prefix="drill_binding_")
    out_path = os.path.join(tmpdir, "BINDING_HEALTH.json")
    saved_out, saved_canary, saved_titles, saved_load = (
        BH.OUT, BH.canary, BH.known_present_titles, BH._load)
    try:
        with open(out_path, "w", encoding="utf-8") as f:
            json.dump({"at": 0, "checked": 2, "failed": 0,
                       "hosts": [{"host": "kept.example.invalid", "healthy": True},
                                 {"host": "probed.example.invalid", "healthy": True}]}, f)
        BH.OUT = out_path
        BH.known_present_titles = lambda h, m=None, **kw: "Any Title"
        BH.canary = lambda h, t, sources=None: {"host": h, "healthy": None,
                                                "reason": "stubbed"}
        BH._load = lambda path, default: ({"A source": "probed.example.invalid",
                                           "Another": "kept.example.invalid"}
                                          if path.endswith("WIKI_HOSTS.json")
                                          else saved_load(path, default))
        BH.run(only=["probed.example.invalid"])
        with open(out_path, encoding="utf-8") as f:
            after = json.load(f)
    finally:
        BH.OUT, BH.canary, BH.known_present_titles, BH._load = (
            saved_out, saved_canary, saved_titles, saved_load)
        shutil.rmtree(tmpdir, ignore_errors=True)
    hosts = {h.get("host") for h in (after.get("hosts") or [])}
    return ("kept.example.invalid" in hosts and "probed.example.invalid" in hosts
            and after.get("checked") == 2)


def _battery_asks_the_network_once():
    """The battery must not open one live socket per check that happens to ask.

    `standards.check()` probes fandom over IPv4, and `verify_math` calls `check()` about
    nineteen times in a run -- so the battery opened nineteen live TLS connections to
    Cloudflare to answer a question that cannot change between them. On 2026-08-26 that stopped
    being waste and became a blocker: `mutate.py` runs the battery in a sandbox as its
    differential gate and REFUSED TO RUN, reporting `verify_math TIMEOUT` on unmutated code,
    because those probes stall under load while the same battery finishes in 32s live. A gate
    that cannot finish on clean code cannot judge a mutant, and the whole mutation mandate sat
    behind it.

    Driven against the real memo with the PROBE counted, not the socket, so the net needs no
    network of its own and cannot pass merely because the machine happens to be offline.
    """
    import standards as ST
    calls = []
    saved_probe, saved_cache = ST._fandom_probe, dict(ST._FANDOM_V4_CACHE)
    try:
        ST._FANDOM_V4_CACHE.clear()
        ST._fandom_probe = lambda host, timeout, sk: (calls.append(host), (True, "1.2.3.4"))[1]
        first = ST.fandom_ipv4_reachable()
        for _ in range(18):                       # the battery's real call count
            ST.fandom_ipv4_reachable()
        memoised = len(calls) == 1 and first == (True, "1.2.3.4")
        # And a STUBBED call must still bypass the memo, or verify_math §19z's three synthetic
        # networks would all get the first one's answer and two of its checks would be vacuous.
        ST._FANDOM_V4_CACHE.clear()
        calls.clear()
        ST.fandom_ipv4_reachable(_sk=object())
        ST.fandom_ipv4_reachable(_sk=object())
        stub_bypasses = len(calls) == 2 and not ST._FANDOM_V4_CACHE
    finally:
        ST._fandom_probe = saved_probe
        ST._FANDOM_V4_CACHE.clear()
        ST._FANDOM_V4_CACHE.update(saved_cache)
    return memoised and stub_bypasses


def _identity_probe_is_gated(src=None):
    """`binding_health` asks a host its name ONLY where the answer changes something. -> bool.

    ASKED OF THE PARSE TREE (run #36). This was `"healthy is None and sources" in <whole file>`,
    and the four-line comment immediately above that branch explains the gate in almost those
    words -- so removing the `if` and probing every host on every sweep, which is precisely the
    round-trip-per-host-per-sweep this net exists to prevent, would have left the net green on
    its own explanation. The gate is now found as a BRANCH and the probe has to be CALLED inside
    it: a condition that no longer guards the call cannot be mistaken for one that does.
    """
    import ast
    tree = _ast_of(os.path.join(_srcdir(src), "binding_health.py"))
    for n in ast.walk(tree):
        if not isinstance(n, ast.If):
            continue
        t = n.test
        if not (isinstance(t, ast.BoolOp) and isinstance(t.op, ast.And)):
            continue
        gated = any(isinstance(v, ast.Compare) and isinstance(v.left, ast.Name)
                    and v.left.id == "healthy" and any(isinstance(o, ast.Is) for o in v.ops)
                    and any(isinstance(c, ast.Constant) and c.value is None
                            for c in v.comparators)
                    for v in t.values)
        sourced = any(isinstance(v, ast.Name) and v.id == "sources" for v in t.values)
        if gated and sourced and _calls_within(tree, n, "_probe_identity"):
            return True
    return False


def _supersession_is_called(src=None):
    """`workorders` CALLS `_supersede_binding_suspect`, rather than merely containing the name.

    ASKED OF THE PARSE TREE (run #36). The old form searched the file text, and the file text
    carries the name in a comment (`-- see _supersede_binding_suspect`) and in the `def` line
    itself. So every call site could be deleted -- leaving the settled host's vague order open
    beside its precise replacement for ever, the exact fault this net was written for -- and the
    net would have gone on holding on the definition of the function nobody calls.
    """
    return _calls(os.path.join(_srcdir(src), "workorders.py"), "_supersede_binding_suspect")


def drill_binding_identity():
    """Can an unfixable fault be filed, for ever, at a handler that cannot fix it?

    Five BINDING_SUSPECT orders stood at the BOTS rung, re-filed every sweep, `seen 14x`. Three
    of them were not repairable by anything: eberron.fandom.com IS the Eberron Wiki, and the
    entries catalogued against its source are rules features (`Alchemical Savant`, `Arcane
    Firearm`) that no wiki has articles for. The order asked a bot to re-probe a binding that
    was already correct. An alarm that can never be cleared is furniture, and this project has
    already learned once that an alarm which always sounds stops being read.

    The discriminator is the wiki's own `sitename`, and it is MEASURED rather than kept in a
    hand-maintained roster of known-fine hosts -- a list like that goes stale the day a source
    is rebound, which is the smaller-universe failure Hard Rule 0 is about.

    Attacked offline against the sitenames measured live on 2026-08-26, so the net proves the
    DECISION rather than today's internet.
    """
    a = "BINDING IDENTITY — is this host the wiki it is bound to?"
    import binding_health as BH

    confirmed = [("Eberron Wiki", ["Eberron: Rising from the Last War"]),
                 ("War Thunder Wiki", ["War Thunder + World of Tanks/Warplanes/Warships "
                                       "(space-refit)"]),
                 ("ANEURISM Wiki", ["ANEURISM IV"])]
    misbound = [("Prime Hydration Wiki", ["Prime World Equipment"]),
                ("The Brain World Wikia", ["Star Realms"])]

    def _rows_kwarg_does_not_write_the_real_roll():
        """The exact call that destroyed the live roll twice on 2026-08-26.

        `roll.exclude(name, note, rows=...)` edited the caller's list and then landed it on the
        module-level ROLL path anyway, so passing test rows IN ORDER TO AVOID touching the real
        file was the way to overwrite it -- 216 sources, no backup anywhere. A parameter whose
        obvious reading is the opposite of its behaviour is a trap, not a sharp edge, and this
        one was baited with the word a careful caller reaches for.

        Attacked against the real function with the real ROLL path pointed at a throwaway file,
        so the net proves the WRITE and cannot itself put the live roll at risk.
        """
        import roll as R
        tmpdir = tempfile.mkdtemp(prefix="drill_roll_")
        saved = R.ROLL
        try:
            R.ROLL = os.path.join(tmpdir, "SWEEP_ROLL.json")
            canon = [{"name": "Real Source", "status": "catalogued", "entry_count": 900}]
            with open(R.ROLL, "w", encoding="utf-8") as f:
                json.dump(canon, f)
            R.exclude("Scratch", "a probe's own rows must never land on the canonical roll",
                      rows=[{"name": "Scratch", "status": "catalogued", "entry_count": 1}])
            with open(R.ROLL, encoding="utf-8") as f:
                after = json.load(f)
            untouched = after == canon
            # And without `rows` it must STILL write, or the fix has simply broken the tool.
            R.exclude("Real Source", "the ordinary path still persists")
            with open(R.ROLL, encoding="utf-8") as f:
                persisted = json.load(f)[0]["status"] == R.OUT_OF_SCOPE
        finally:
            R.ROLL = saved
            shutil.rmtree(tmpdir, ignore_errors=True)
        return untouched and persisted
    def _sandbox_without_its_target_refuses():
        """A sandbox missing the module about to be mutated must say so, not crash later.

        On 2026-08-27 a `--target all` session died four minutes in with a bare
        FileNotFoundError on `<sandbox>/src/assay.py`, AFTER its baseline gates had run and
        passed, because repair agents were rewriting that file while the sandbox was being
        copied. The copy is a listdir followed by per-file copies, so a module renamed in
        between is named and then not copied. The crash was not the fault; the fault was that
        the sandbox read as sound until something opened the file, so the failure surfaced far
        from its cause and looked like a bug in the mutation engine.

        Attacked by making the copy itself lose exactly one target -- the real `sandbox()`, with
        `shutil.copy2` swapped for one that drops `assay.py` -- so the net proves the refusal
        rather than the message.
        """
        import mutate as M
        real_copy, roots = shutil.copy2, []

        def dropping_copy(src_path, dst_path, *a_, **k_):
            if os.path.basename(src_path) == "assay.py":
                return dst_path                      # listed, then quietly not copied
            return real_copy(src_path, dst_path, *a_, **k_)

        real_mkdtemp = tempfile.mkdtemp

        def remember(*a_, **k_):
            r = real_mkdtemp(*a_, **k_)
            roots.append(r)
            return r

        try:
            shutil.copy2, tempfile.mkdtemp = dropping_copy, remember
            try:
                M.sandbox()
                refused = False
            except RuntimeError as e:
                refused = "assay.py" in str(e) and "Nothing was mutated" in str(e)
            except Exception:
                refused = False
        finally:
            shutil.copy2, tempfile.mkdtemp = real_copy, real_mkdtemp
            for r in roots:
                shutil.rmtree(r, ignore_errors=True)
        # And it must not leave the half-built sandbox behind while refusing.
        return refused and not any(os.path.isdir(r) for r in roots)
    net(a, "a sandbox missing its own mutation target REFUSES to be used",
        _sandbox_without_its_target_refuses,
        "the run crashed on a bare FileNotFoundError four minutes after a baseline that had "
        "already passed, which reads as an engine bug rather than as a tree being edited")

    net(a, "a caller's own rows never land on the canonical Acquisitions Roll",
        _rows_kwarg_does_not_write_the_real_roll,
        "this ate the live 216-source roll twice in one afternoon, while someone was being "
        "careful, and no backup of that file existed")

    def _context_mismatch_is_a_finding():
        """A served context that disagrees with the configured one must be a FINDING, not a lag.

        Ollama holds a resident model at ONE context size; a request naming a different
        `num_ctx` rebuilds the runner, which on a full card is "240 s+, never completed". So a
        mismatch does not raise -- it makes every call pay a rebuild, and presents as slowness.
        Measured 2026-08-27: `read.py --run` had done 1,659 of 326,617 chunks at 0.01 chunks/s,
        an ETA of ~1.7 years, while the runner served 4096 and config asked for 12288. Sixteen
        modules read `num_ctx` and nothing compared it to what was being served.

        Driven against the real `standards` verdict logic with the daemon and the config
        stubbed, so the net proves the DECISION and needs neither a GPU nor a network. Both
        directions: a mismatch must not hold, agreement must hold, and an unreadable context
        must be neither -- it goes to `_dropped`, because "I could not tell" read as agreement
        is the green-by-absence bug this standard sits next to.
        """
        import standards as ST
        mismatch, _ = ST.context_verdict(4096, 12288)      # the live 2026-08-27 shape
        agree, _ = ST.context_verdict(12288, 12288)
        same_str, _ = ST.context_verdict("8192", 8192)     # the API returns ints, config may not
        unknown_a, _ = ST.context_verdict(None, 12288)     # daemon would not say
        unknown_b, _ = ST.context_verdict(4096, None)      # config unreadable
        return (mismatch is False and agree is True and same_str is True
                and unknown_a is None and unknown_b is None)
    net(a, "a served context that disagrees with the configured one is a FINDING, not a lag",
        _context_mismatch_is_a_finding,
        "a num_ctx mismatch does not fail, it stalls -- every call rebuilds the runner -- so it "
        "presents as slowness and nobody looks for a fault; measured at an ETA of 1.7 years")

    net(a, "the battery asks the live network ONCE, not once per check",
        _battery_asks_the_network_once,
        "nineteen live TLS connections per run made verify_math time out in mutate's sandbox, "
        "and a gate that cannot finish on clean code cannot judge a mutant -- the whole "
        "mutation mandate sat behind this")

    net(a, "a wiki that names itself after its bound source is CONFIRMED, not suspected",
        lambda: all(BH.binding_verdict(s, n)["verdict"] == "CONFIRMED" for s, n in confirmed),
        "these three re-filed at a bot every sweep for a fault no bot can repair")
    net(a, "a wiki serving something else entirely is MISBOUND",
        lambda: all(BH.binding_verdict(s, n)["verdict"] == "MISBOUND" for s, n in misbound),
        "prime.fandom.com serves the Prime Hydration drink wiki; the two share only the word "
        "'Prime', and a partial-string match would have called that a confirmed binding")
    net(a, "the two verdicts are separated by a real margin, not by a hair",
        lambda: (min(BH.binding_verdict(s, n)["score"] for s, n in confirmed)
                 - max(BH.binding_verdict(s, n)["score"] for s, n in misbound)) >= 20,
        "a threshold that only just separates today's cases is a threshold that will be wrong "
        "about tomorrow's")
    net(a, "a host whose identity cannot be read is UNKNOWN, not guessed either way",
        lambda: (BH.binding_verdict(None, ["Star Realms"])["verdict"] == "UNKNOWN"
                 and BH.binding_verdict("Some Wiki", [])["verdict"] == "UNKNOWN"),
        "guessing is what put an unfixable order in a bot's queue in the first place")
    net(a, "a name too close to call is UNCLASSIFIED rather than forced to a side",
        lambda: BH.BINDING_MISBOUND_BELOW < BH.BINDING_CONFIRMED_AT,
        "collapsing the undecided band into one of the answers would make every borderline "
        "host either an unfixable bot order or an accusation of misbinding")
    net(a, "the identity probe is only spent where it changes something",
        _identity_probe_is_gated,
        "a host whose titles resolve is bound correctly by demonstration; asking its name "
        "anyway costs a network round trip per host per sweep to confirm what was just proved")
    net(a, "a PARTIAL canary run cannot shrink the whole-estate report",
        _partial_canary_merges,
        "probing five hosts by name wrote a report saying the library has five hosts, and the "
        "binding detector reads that file AS the estate -- the same smaller-universe shape as "
        "a cap, arrived at while INVESTIGATING a binding")
    net(a, "settling a host's identity CLOSES the undecided order it replaces",
        _supersession_is_called,
        "splitting one code into two only ever ADDS unless the old order is resolved: the host "
        "is still unhealthy, so the vague order would sit open beside the precise one for ever")


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
        "records and coverage rows must be well-formed before anything reasons over them -- and "
        "this read 40 of 216 records and scored an unparseable one as clean, so the claim was "
        "about a fifth of the corpus and could not fail on the file most likely to be broken")


def _policy_corpus_clean(root=None):
    """Every record in the corpus passes its structural rules — every record, and read.

    TWO DEFECTS, BOTH FOUND BY THE RUN #34 SWEEP, and both in the worst possible place: a net
    whose whole claim is about "the live corpus".

    THE CAP. This carried `[:40]` over a sorted glob, so the net asserted a property of the whole
    corpus while opening its alphabetical first fifth -- 40 of 216 record files. It reported
    green over 80% of a corpus it never looked at, and the claim it printed said nothing about
    the sample. A Hard Rule 0 truncation inside a safety net is worse than one in a report: a
    report that shows five of a hundred rows is merely incomplete, while a NET that reads five of
    a hundred rows is evidence about the wrong thing wearing the name of evidence about the right
    thing. Uncapped; the full pass costs about three seconds.

    THE SWALLOWED RECORD. A bare `except Exception: continue` scored an unreadable or unparseable
    record as clean. A record that cannot be parsed has not passed its structural rules -- it is
    a file this net could not read, which is the "absence read as clean" shape the whole project
    exists against, and it is the shape a corrupted record would arrive in. It now fails the net,
    and it is the ONLY thing that can fail it that is not a rule verdict, so the two cannot be
    confused by whoever reads the breach.

    `root` exists so the drill can watch this net go red against a deliberately malformed record
    in a temp directory, which is the only way to see it refuse without corrupting the corpus.
    """
    import glob
    import policy as POL
    root = root or os.path.join(HERE, "data", "records")
    bad, unreadable = 0, 0
    for p in sorted(glob.glob(os.path.join(root, "*.json"))):
        try:
            with open(p, encoding="utf-8") as f:
                ev = POL.evaluate(json.load(f), POL.RECORD_RULES, os.path.basename(p))
        except Exception:
            unreadable += 1
            continue
        bad += len([r for r in ev["failed"] if r.get("severity") != "INFO"])
    return bad == 0 and unreadable == 0


# ============================================================== THE FETCH (network manners)

def _refusal_is_recorded(src=None):
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

    AND BOTH ARE NOW ASKED OF THE PARSE TREE (run #36). They were two substring searches of the
    whole file, `'"pages_refused": unreal'` and `"unreal[t] = why"`, and `feats.py` mentions
    `pages_refused` in five other places including a comment about cache files written before it
    existed. A net whose subject is "a check defanged so a wrong assertion could not embarrass
    anyone" has no business being satisfiable by a comment. The recording is now an ASSIGNMENT
    into `unreal`, and the carrying is a dict entry keyed `"pages_refused"` whose value is that
    same name -- neither of which prose can produce.
    """
    import ast
    tree = _ast_of(os.path.join(_srcdir(src), "feats.py"))
    records = any(isinstance(t, ast.Subscript) and isinstance(t.value, ast.Name)
                  and t.value.id == "unreal"
                  for n in ast.walk(tree) if isinstance(n, ast.Assign) for t in n.targets)
    carried = False
    for n in ast.walk(tree):
        if not isinstance(n, ast.Dict):
            continue
        for k, v in zip(n.keys, n.values):
            if (isinstance(k, ast.Constant) and k.value == "pages_refused"
                    and isinstance(v, ast.Name) and v.id == "unreal"):
                carried = True
    return records and carried


def _local_buckets_excluded_from_cloud_claims(src=None):
    """A cloud claim must SKIP an `ollama:` bucket, not merely have a constant naming one.

    ASKED OF THE PARSE TREE (run #36). The old form searched `cascade_bridge.py` for the text
    `cand.bucket.startswith(LOCAL_PREFIX)`, and line 1060 of that file is a COMMENT that names
    `LOCAL_PREFIX` while explaining the branch -- so the guard could be deleted and the
    explanation would keep answering for it, while the router handed out ollama buckets and
    flooded a 10 GB card with its own queue again. The test is now a real `.startswith` call
    against the real constant, guarding a real branch.
    """
    import ast
    tree = _ast_of(os.path.join(_srcdir(src), "cascade_bridge.py"))
    for n in ast.walk(tree):
        if not isinstance(n, ast.If):
            continue
        for c in ast.walk(n.test):
            if not (isinstance(c, ast.Call) and isinstance(c.func, ast.Attribute)
                    and c.func.attr == "startswith"):
                continue
            if not (isinstance(c.func.value, ast.Attribute) and c.func.value.attr == "bucket"):
                continue
            if any(isinstance(x, ast.Name) and x.id == "LOCAL_PREFIX" for x in c.args):
                return True
    return False


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


def _quarantine_reports_the_disk_not_the_intention():
    """The escalation must describe what is ON DISK, not what the caller meant to write.

    A refused rename leaves the host UNQUARANTINED -- `quarantined()` re-reads the file on every
    call -- so raising HOST_QUARANTINED for it puts a lie in the escalation ledger and closes a
    case that was never opened. The host keeps being mined while the record says it was stopped,
    which is the same shape as `release()` telling a caller a host is free while it is still
    quarantined. The actionable finding is the failure to WRITE, and the verdict rides out in the
    returned record so a caller cannot mistake an attempted quarantine for a recorded one.

    BOTH VERDICTS, since a `quarantine()` that always reported failure would be just as wrong and
    would look identical from the passing half alone. `QUARANTINE` points at a temp path and
    `_land` is a stand-in, so nothing is written; the escalation chain is a stand-in too, because
    the real one files a work order and the drill is not allowed to leave one in the queue for a
    host that does not exist.
    """
    import shutil
    import types
    import binding_health as BH
    d = tempfile.mkdtemp(prefix="drillquar_")
    raised = []
    stub = types.ModuleType("escalation")
    stub.SUPERVISOR = ESC.SUPERVISOR
    stub.escalate = lambda level, code, what, **k: raised.append(code)
    had, prev = "escalation" in sys.modules, sys.modules.get("escalation")
    keep = (BH.QUARANTINE, BH._land)
    try:
        BH.QUARANTINE = os.path.join(d, "HOST_QUARANTINE.json")
        sys.modules["escalation"] = stub
        BH._land = lambda path, obj: False
        rec = BH.quarantine("__drill__.invalid", "drill self-test; no such host")
        if rec.get("landed") is not False or raised != ["HOST_QUARANTINE_NOT_RECORDED"]:
            return False
        del raised[:]
        BH._land = lambda path, obj: True
        rec = BH.quarantine("__drill__.invalid", "drill self-test; no such host")
        return (rec.get("landed") is True and raised == ["HOST_QUARANTINED"]
                and not os.path.exists(BH.QUARANTINE))
    finally:
        BH.QUARANTINE, BH._land = keep
        if had:
            sys.modules["escalation"] = prev
        else:
            sys.modules.pop("escalation", None)
        shutil.rmtree(d, ignore_errors=True)


def _backoff_stops_at_its_ceiling():
    """Throttle a host until the multiplier saturates, and require it to STOP at the clamp.

    THE OLD NET WAS `1.0 < F.BACKOFF_MAX <= 128.0`. That is an assertion about a number nobody
    was going to change, and it never drove a call: the clamp it is named after is
    `feats.py:148`, `min(BACKOFF_MAX, _BACKOFF.get(host, 1.0) * BACKOFF_GROWTH)`, and deleting
    the `min(...)` leaves the constant exactly as it was. Its sibling `_backoff_adapts` walks
    growth and recovery but never approaches the ceiling, so nothing in this file had ever seen
    the clamp bite. Third time this shape has been removed from this file (run #33 took two).

    THE HAND-OFF IS TAKEN BY A STAND-IN, exactly as `_throttle_hands_off` does and for the same
    reason: past `THROTTLE_STRIKES` consecutive 429s `note_throttled` calls `BH.quarantine`,
    which writes `data/HOST_QUARANTINE.json`, and saturating the backoff needs far more strikes
    than that. The drill must not leave a quarantine on file for a host that does not exist.

    "SLOWED, NEVER STOPPED" IS THE OTHER HALF and it is asserted too, because a clamp that
    saturated at some enormous value would satisfy the first half and still be an outage: the
    pace the saturated multiplier implies is required to stay inside a minute.
    """
    import types
    import feats as F
    h = "__drill_ceiling__.invalid"
    stub = types.ModuleType("binding_health")
    stub.is_quarantined = lambda host: True          # already handed off; do not hand off again
    stub.quarantine = lambda host, why: None
    had = "binding_health" in sys.modules
    prev = sys.modules.get("binding_health")
    F._BACKOFF.pop(h, None)
    F._STRIKE.pop(h, None)
    try:
        sys.modules["binding_health"] = stub
        # Enough strikes that an UNCLAMPED backoff would be astronomical: at the smallest
        # plausible growth factor this is many times past any sane ceiling.
        for _ in range(64):
            F.note_throttled(h)
        saturated = F._BACKOFF.get(h, 1.0)
        F.note_throttled(h)                          # ... and one more must not widen it
        after = F._BACKOFF.get(h, 1.0)
        return (saturated == F.BACKOFF_MAX           # clamped, not merely large
                and after == saturated
                and F._pause_for(h) * saturated < 60.0)   # slowed, never stopped
    finally:
        if had:
            sys.modules["binding_health"] = prev
        else:
            sys.modules.pop("binding_health", None)
        F._BACKOFF.pop(h, None)
        F._STRIKE.pop(h, None)


def drill_fetch():
    """Between the wiki and the model: the two ways a network failure becomes a false absence."""
    a = "THE FETCH — can a blocked or throttled page read as an empty subject?"
    net(a, "a block page is refused before the model ever sees it", _page_is_real_gate,
        "verbatim provenance against a Cloudflare interstitial is still verbatim, and still wrong")
    net(a, "throttling widens the pace, and a clean response earns it back", _backoff_adapts,
        "1,364 throttled fetches were once filed as honest absences across every pantheon")

    net(a, "a refused page is RECORDED, not dropped",
        _refusal_is_recorded,
        "the distinction between 'no evidence' and 'we were blocked' must survive to the cache")
    net(a, "persistent throttling hands off to quarantine rather than hammering",
        _throttle_hands_off,
        "past a few strikes, 'busy' is a less likely reading than 'blocked'")
    net(a, "a quarantine that could not be written says so, instead of claiming the host is out",
        _quarantine_reports_the_disk_not_the_intention,
        "a refused rename leaves the host being mined; HOST_QUARANTINED for it would close a "
        "case in the ledger that was never opened on disk")
    net(a, "the backoff has a ceiling -- slowed, never stopped", _backoff_stops_at_its_ceiling,
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
        _local_buckets_excluded_from_cloud_claims,
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
        """An exhausted pool must be NAMED from the engine's own wording, and only from it.

        THE OLD NET WAS `hasattr(CB, "pool_exhausted") and callable(...)`. That asks whether a
        name exists. `pool_exhausted` could have been rewritten to `return False` — every
        multi-candidate failure then falling through to the unrecognised ledger and, worse,
        reaching the `permanent_refusal` branch at `cascade_bridge.py:1192` that BENCHES a
        bucket for four hours on evidence that was never about that bucket — with both halves
        of this net still true. Found by the run #34 sweep; third time this shape has been cut
        out of this file.

        DRIVEN WITH THE MEASURED STRINGS, in both directions, because the discriminations are
        the behaviour. `All 11 candidates failed` is the engine reporting a whole walk; the
        singular `All 1 candidates failed` is one bucket's own refusal wearing the same wrapper
        and must NOT be read as an empty pool, since that is exactly the confusion that would
        bench a live bucket for a call the pool never made. And an ordinary throttle is not an
        exhausted pool either.
        """
        if not CB.pool_exhausted("All 11 candidates failed: groq, gemini, ..."):
            return False                       # the real condition read as something else
        if not CB.pool_exhausted("ALL 2 CANDIDATES FAILED"):
            return False                       # case is the engine's business, not ours
        for not_it in ("All 1 candidates failed: insufficient balance",
                       "429 rate limited, please try again",
                       "", None):
            if CB.pool_exhausted(not_it):
                return False                   # a single bucket's refusal is not the pool
        return True
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

    def catalog_matches_disk(root=None):
        """Every chapter the catalog claims exists on disk, AND VICE VERSA — both directions.

        The docstring said "and vice versa" and the code walked one way only, catalog -> disk,
        which is the smaller half. A chapter the catalog has LOST is invisible to that walk, and
        an uncatalogued chapter in `output/raw` is the more alarming of the two conditions: the
        prose gate is closed by owner ruling, so a file arriving there is prose from a writer
        nobody knows about — the incident this whole layer was built after, in its early form.
        `gate_claim_matches_reality` two nets up counts the same directory but only demands it
        be EMPTY while the gate is shut; this one holds once the gate is open again, which is
        when it starts to matter. A net's printed name is what people trust; it may not promise
        more than the code does. (Run #34, MINOR.)
        """
        root = root or HERE
        cat = os.path.join(root, "output", "index", "catalog.json")
        if not os.path.exists(cat):
            return True
        d = json.load(open(cat, encoding="utf-8"))
        claimed = set()
        for rec in d.values():
            p = (rec or {}).get("raw_path") or ""
            p = p.replace("\\", os.sep).replace("/", os.sep)
            if not p:
                continue
            full = p if os.path.isabs(p) else os.path.join(root, p)
            if not os.path.exists(full):
                return False                   # a book the library thinks it has
            claimed.add(os.path.normcase(os.path.basename(full)))
        raw = os.path.join(root, "output", "raw")
        if os.path.isdir(raw):
            for f in os.listdir(raw):
                if not os.path.isfile(os.path.join(raw, f)):
                    continue
                if os.path.normcase(f) not in claimed:
                    return False               # a book on the shelf in no catalogue
        return True
    net(a, "the catalog and the shelf agree in BOTH directions", catalog_matches_disk,
        "a catalog entry with no file is a book the library thinks it has; a file in no catalog "
        "entry is prose from a writer nobody knows about")

    def coverage_totals_never_exceed_their_entry_count(path=None):
        """No source's states may sum PAST its own entry count. One direction, and only one.

        THE DOCSTRING USED TO SAY the arithmetic "must add up to its own entry count", which is
        a claim about equality that the code never made. What was wrong HERE was a net whose name
        and docstring promised a completeness check while its code did an overflow check, so a
        reader of the drill's output came away believing the stronger thing. The name now says
        what the code does.

        AND A CORRECTION, KEPT ON PURPOSE BECAUSE IT IS THE SAME MISTAKE THIS NET IS ABOUT.
        The first version of this rewrite justified itself with a measurement -- "16 of 210 rows
        sum BELOW their entry count, DC is 14,376 of 44,958, Diablo 313 of 5,480, so tens of
        thousands of entries sit in no state at all". That is FALSE, and it was arrived at by
        reading `settled` as a count when it is a FRACTION: 0.3198 x 44,958 = 14,376 exactly, and
        0.0571 x 5,480 = 313 exactly. The real state columns are `cited`, `read`, `no_page`,
        `no_host` and `not_attempted`, and re-measured against those on 2026-08-26 they sum to
        the entry count EXACTLY for all 210 rows -- 0 below, 0 past. So a fix written to remove
        prose that outran its code came within one commit of writing new prose that outran its
        data, into a safety file, where the next reader would have believed it. Verified before
        it stood. (Run #34.)

        The overflow direction stays exactly as it was and is worth keeping on its own: states
        summing past the total mean an entry counted twice, which is the M23 shape.
        """
        p = path or os.path.join(HERE, "data", "COVERAGE.json")
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
        coverage_totals_never_exceed_their_entry_count,
        "states that sum past the total mean an entry counted twice -- the M23 shape")

    def halt_claim_is_honest():
        """If we are halted, the file must say WHY. A halt with no reason cannot be ruled on."""
        halted, rec = ESC.status()
        if not halted:
            return True
        return bool((rec or {}).get("code")) and bool((rec or {}).get("what"))
    net(a, "a standing halt always carries a reason", halt_claim_is_honest,
        "a halt nobody can read is a halt nobody can lift")

    def guards_are_wired_where_claimed(src=None):
        """Each interlock must be CALLED in the file that claims it — asked of the AST.

        SATISFIED BY PROSE IN HALF ITS FILES, until run #34. It was `token in <file text>`, and
        for three of the six the token occurs only in explanation: `coverage.py:53` names
        cachekey in a docstring ("verifies via `cachekey.owns()` before believing a file"),
        `pipeline.py:822` in a comment, `feats.py:918-923` in a comment block. Those three files
        could lose the import and every call and this net — named "every guard is present in the
        file that claims it", expectation "the last incident was a guard DELETED, not a guard
        that failed" — would have kept holding on the paragraphs describing the deleted guard.
        A guard's explanation is the part MOST likely to survive its removal.

        `_calls` resolves through each file's own imports, so `import cachekey as CK; CK.load()`
        counts and a same-named local method does not. The four cache files are asked for a call
        on the MODULE, which is the honest form of "cachekey is wired in here"; the two gate
        files are asked for the specific function, because there the identity of the call is the
        whole claim.
        """
        src = src or os.path.dirname(os.path.abspath(__file__))
        want = {"generate.py": "prose_gate.assert_gate_open",
                "overnight.py": "_prose_enabled",
                "coverage.py": "cachekey.", "feats.py": "cachekey.",
                "pipeline.py": "cachekey.", "hostcheck.py": "cachekey."}
        return all(_calls(os.path.join(src, f), token) for f, token in want.items())
    net(a, "every guard is CALLED in the file that claims it", guards_are_wired_where_claimed,
        "the last incident was a guard DELETED, not a guard that failed -- and the comment "
        "explaining it stayed behind")

    def the_meta_language_ban_is_actually_enforced():
        """A BAN NOTHING CHECKS IS A STYLE NOTE. `pipeline.assert_in_universe` rejects prose that
        breaks the in-fiction frame, and `pipeline.py:2122` states the ban "is enforced in code
        like scale_note and the Marginalia cap before it". It was not: the function had ZERO
        callers anywhere in `src/`, and `generate.py` -- the only thing that turns a manifest
        into prose -- did not import `pipeline` at all. The sole reader of `meta_violations` was
        an after-the-fact audit report on text already written.

        Attacked from both ends: the refusal must fire on meta-language and must NOT fire on
        ordinary in-universe prose, and the writer must be the thing that calls it.
        """
        import pipeline as PL
        if not PL.assert_in_universe(
                "The Custodes record that Kenshiro struck the gate at the ninth hour.",
                where="__drill__"):
            return False
        if not _refuses(lambda: PL.assert_in_universe(
                "As a DM you might rule that this sourcebook lets the player reroll.",
                where="__drill__"), ValueError):
            return False
        # ASKED OF THE PARSE TREE (run #36). This was `"assert_in_universe" in generate.py`, and
        # `generate.py` names the check twice in the comment block directly above the call --
        # once as "THE P8 META-LANGUAGE BAN, ENFORCED FOR THE FIRST TIME. `pipeline.
        # assert_in_universe`" -- so deleting the call would have left the net green on the
        # paragraph announcing it. The writer must CALL it; noticing it is what the audit does.
        return _calls(os.path.join(_srcdir(), "generate.py"), "assert_in_universe")
    net(a, "meta-language is refused by the writer, not just noticed by an audit",
        the_meta_language_ban_is_actually_enforced,
        "one 'as a DM you might' in a finished volume breaks the frame for every entry near it")

    def liveness_sees_its_own_founding_example():
        """THE DETECTOR MUST CATCH THE CASE IT WAS WRITTEN FOR. `liveness.py:10` names
        `coverage._p()` -- "a fully documented cache-path helper with no callers" -- as one of
        the instances that motivated the module. For an unknown length of time it was NOT in
        `scan()['dead']`, because the `used` set was scope-blind and a LOCAL LOOP VARIABLE named
        `_p` in cleanup.py and tells.py marked every `_p()` in the project as called.

        A detector blind to its own worked example reports a floor and calls it a total, and
        `LIVENESS_CEILING` was ratcheting that floor as though it were the truth. Pinned by name
        rather than by count so that fixing the count cannot quietly re-lose the case.
        """
        import liveness
        dead = liveness.scan()["dead"]
        return any(d.startswith("coverage.py:") and "_p()" in d for d in dead)
    net(a, "the dead-code detector catches the example in its own docstring",
        liveness_sees_its_own_founding_example,
        "a scope-blind used set hid coverage._p(), the case the module was written for")

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


def _twins_ignores_a_foreign_tree():
    """A namesake in ANOTHER checkout is not a twin of this tree's module.

    THE INCIDENT THIS NET EXISTS FOR, 2026-08-25 22:38, and it is the halt standing over this
    file as it is written. `twins()` compared `os.path.basename(script)` and nothing else, so any
    process running a file merely CALLED `verify_math.py` counted as a twin of this tree's
    `src/verify_math.py`. `mutate.py` runs the whole battery inside a throwaway sandbox -- a temp
    copy of `src/`, precisely so the live tree is never corrupted -- and its sandboxed
    `python src/verify_math.py` was reported as a twin. The control net two above this one
    asserts `twins("verify_math") == []` for exactly that reason (no daemon runs it), so the
    drill BREACHED against correct code and raised a real DRILL_BREACH halt over a process doing
    the job it was designed to do.

    THE FALSE HALT IS THE MILD FORM. `claim_singleton` EXITS a daemon when it finds a twin, so
    the same confusion could have stood a live publisher down for a namesake in the export copy,
    in a second checkout, or in a mutation sandbox -- "an outage that reports itself as caution",
    which is the failure `twins`' own docstring warns about, arriving by a third route after the
    linter-matched-as-a-daemon bug and this one.

    BOTH DIRECTIONS, because a `twins()` that found nothing at all would sail through the first
    half while protecting nobody. ONE live child process is asked about twice: with `SRC` pointing
    at this tree, where it must NOT count, and with `SRC` pointing at the sandbox it really lives
    in, where it MUST. The command line is deliberately the relative `python src/verify_math.py`
    the sandbox actually runs, since resolving a relative script against the CHILD's cwd rather
    than ours is the half that has to be right. The child is killed in the `finally` and nothing
    is written outside the temp directory.
    """
    import shutil
    import subprocess
    import time as _t
    import codewatch as CW
    needle = "verify_math"
    d = tempfile.mkdtemp(prefix="drilltwin_")
    child = None
    real_src = CW.SRC
    try:
        sandbox = os.path.join(d, "src")
        os.makedirs(sandbox)
        with open(os.path.join(sandbox, needle + ".py"), "w", encoding="utf-8") as f:
            f.write("import time\ntime.sleep(45)\n")
        child = subprocess.Popen(
            [sys.executable, os.path.join("src", needle + ".py")], cwd=d,
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
        # Wait for the child to be visible AS A TWIN OF ITS OWN TREE. Polling on the positive
        # case rather than on a fixed sleep means the negative case below cannot pass merely
        # because the process table had not caught up yet -- which would be a net that holds by
        # being early rather than by being right.
        CW.SRC = sandbox
        seen, deadline = False, _t.time() + 20
        while _t.time() < deadline:
            if child.pid in CW.twins(needle):
                seen = True
                break
            _t.sleep(0.2)
        CW.SRC = real_src
        return seen and child.pid not in CW.twins(needle)
    finally:
        CW.SRC = real_src
        if child is not None:
            try:
                child.kill()
                child.wait(timeout=5)
            except Exception:
                pass
        shutil.rmtree(d, ignore_errors=True)


def drill_no_top_ups():
    """OWNER RULING 2026-08-26: cooldown is fine; pay-to-continue is axed.

    "if something runs out and is on cooldown, fine, if something runs out and requires payment
    after running out, axe it." The whole ruling turns on one distinction, so the distinction is
    what gets attacked here rather than the list of providers it happened to produce today.

    Both directions cost something real. Reading a 429 as permanent benches a provider that
    would have come back in an hour; reading a 402 as transient spends the pool's permits
    forever on a door that money is the only key to, and the answer to money is no.
    """
    a = "NO TOP-UPS — a cooldown is not a bill"

    def payment_refusals_are_permanent():
        import cascade_bridge as CB
        for e in ("HTTP 402 payment required",
                  "quota exceeded and account balance is $0.0, please pay with fiat",
                  "you have depleted your monthly included credits. purchase pre-paid credits",
                  "you need positive balance to do inference. please add balance or setup top-up",
                  "payment required to access this resource. visit your billing tab"):
            if not CB.permanent_refusal(e):
                return False
        return True
    net(a, "a provider that wants money is axed, not retried", payment_refusals_are_permanent,
        "the remedy is money and the owner's answer to money is no")

    def cooldowns_stay_in_the_pool():
        import cascade_bridge as CB
        for e in ("HTTP 429 rate limit reached",
                  "429 free-models-per-day rate limit exceeded",
                  "rate limit exceeded, retry after 60s",
                  "quota exceeded, resets at midnight UTC"):
            if CB.permanent_refusal(e):
                return False
        return True
    net(a, "a provider on cooldown is kept, not axed", cooldowns_stay_in_the_pool,
        "benching a 429 throws away a provider that returns within the hour")

    def a_waf_rejection_is_not_an_account_fault():
        """MEASURED, not assumed. groq and cerebras both answered `403 error code: 1010` -- a
        Cloudflare browser-integrity refusal. A real User-Agent turned groq's into a 200. Had
        that been read as permanent, the fastest working provider in the pool would have been
        benched for a fault that was on this side of the wire."""
        import cascade_bridge as CB
        return (not CB.permanent_refusal("HTTP 403 error code: 1010")
                and not CB.permanent_refusal("403 Just a Moment... cloudflare"))
    net(a, "a Cloudflare rejection is read as our problem, not the provider's",
        a_waf_rejection_is_not_an_account_fault,
        "1010 is a client-fingerprint refusal; a real UA fixed it outright")

    def paid_access_stays_switched_off():
        import json as _j
        try:
            with open(r"C:\\Users\\imarl\\cascade\\config.json", encoding="utf-8") as fh:
                cfg = _j.load(fh)
        except Exception:
            return True          # not this machine; the ruling is still recorded in the config
        return cfg.get("allow_paid") is False
    net(a, "the cascade never switches paid access on", paid_access_stays_switched_off,
        "allow_paid is owner-held; anything that flips it is a bug")


def drill_probe_honesty():
    """A probe that could not run must not be counted as a probe that passed.

    `binding_health._probe_absent` is the check that catches a host answering yes to everything
    -- a soft-404, a search page, a login wall wearing an article's clothes. It caught ANY
    exception and returned `True, "no answer, which is the correct answer"`, so a timeout, a
    500, a DNS failure or a bug in `feats.fetch` all certified the host as sound. The one probe
    written to tell "it refused" from "something came back" could not tell either from "I never
    got to look."
    """
    a = "PROBE HONESTY — not asked is not answered"

    def unknown_never_reads_as_healthy():
        import binding_health as B
        for present in (True, False):
            for reach in (True, False):
                ok, _why = B.verdict(present, None, reach, det_p="d", det_a="d", det_r="d")
                if ok is True:
                    return False          # a probe that did not run bought a clean bill
        return True
    net(a, "an unrunnable absent-probe can never produce a healthy verdict",
        unknown_never_reads_as_healthy,
        "the probe returned True on every exception, certifying hosts it never tested")

    def unknown_does_not_quarantine_a_live_host():
        """The other side. Refusing on unknown would stop mining a good wiki on a network blip,
        which is the false-quarantine this module warns about at length."""
        import binding_health as B
        ok, _ = B.verdict(True, None, True, det_a="timeout")
        return ok is None
    net(a, "an unrunnable probe does not quarantine a reachable host on its own",
        unknown_does_not_quarantine_a_live_host,
        "unknown is a third answer, not a vote either way")

    def a_lying_host_is_still_caught():
        """The original purpose must survive the fix."""
        import binding_health as B
        ok, why = B.verdict(True, False, True, det_a="resolved a title that cannot exist")
        return ok is False and "absent probe resolved" in (why or "")
    net(a, "a host that resolves an impossible title is still refused",
        a_lying_host_is_still_caught,
        "the tri-state must not soften the verdict it was built to deliver")


def drill_rung_four():
    """MANAGER stops must actually stop things — for four days they did not.

    On 2026-08-26 the nightly run stopped `catalogue_web --recatalogue` at rung 4 because it was
    NULLING SYNTHESIS BLOCKS: 26 sources in twenty-four hours, DC among them at 44,958 entries.
    Twenty-five minutes later the keeper started it again. Nothing had failed — the chain
    recorded that rung 4 fired, and the supervisor whose entire job is keeping jobs up had never
    been given anything to read.

    So of five rungs, exactly ONE could stop anything: the OWNER halt. Escalating to a rung that
    cannot enforce itself is the same as escalating to nobody, and worse, because it reads as
    action taken and stops anyone looking further.
    """
    a = "RUNG FOUR — a stopped subsystem stays stopped"

    def a_stop_is_written_down_and_readable():
        import escalation as E
        name = "__drill_rung4__"
        try:
            E.stop_subsystem(name, "drill probe: rung 4 must outlive the process that set it",
                             who="drill.py")
            held, why = E.subsystem_stopped(name)
            return held is True and "drill probe" in why
        finally:
            try:
                E.resume_subsystem(name, "drill probe complete; releasing the synthetic stop")
            except Exception:
                import silence as _s
                _s.note("drill.py:rung4-cleanup")
            _sweep_probe_litter(name, "rung4")
    net(a, "a MANAGER stop is recorded where another process can read it",
        a_stop_is_written_down_and_readable,
        "a stop only the stopping process knows about lasted 25 minutes and lost 26 records")

    def resuming_demands_a_written_ruling():
        import escalation as E
        name = "__drill_rung4b__"
        try:
            E.stop_subsystem(name, "drill probe: resuming must not be casual", who="drill.py")
            try:
                E.resume_subsystem(name, "ok")
                return False                      # a shrug re-opened it. Breach.
            except ValueError:
                return True
        finally:
            try:
                E.resume_subsystem(name, "drill probe complete; releasing the synthetic stop")
            except Exception:
                import silence as _s
                _s.note("drill.py:rung4b-cleanup")
            _sweep_probe_litter(name, "rung4b")
    net(a, "re-opening a stopped subsystem demands a written ruling",
        resuming_demands_a_written_ruling,
        "the thing that undid the last stop was an automated actor with a restart timer")

    def a_probe_leaves_no_order_behind():
        """The battery must be able to run on a live library without decorating its queue.

        Every escalation FILES A REAL WORK ORDER, so a probe that stops and resumes a synthetic
        subsystem files two, and the rung-4 pair above did that on every cycle without ever
        clearing them: SUBSYSTEM_STOPPED for `__drill_rung4__` at MAJOR, addressed to RUN, was
        `seen 15x` when this net was written, next to its RESUMED twin and a `probe_job` pair
        left by a scratch test that no longer exists anywhere in `src/`. None of the four
        describe a subsystem that has ever existed.

        Asserted by DOING IT: a fresh synthetic subsystem is stopped and resumed here, and the
        open-order set afterwards must equal the set before. Counting is not enough -- an
        unrelated detector filing one order while this probe leaks one would net to zero -- so
        the identities are compared.
        """
        import escalation as E
        import workorders as WO
        name = "__drill_litter_probe__"
        before = set(WO._load())
        try:
            E.stop_subsystem(name, "drill probe: a probe must not litter the queue",
                             who="drill.py")
        finally:
            try:
                E.resume_subsystem(name, "drill probe complete; releasing the synthetic stop")
            except Exception:
                import silence as _s
                _s.note("drill.py:litter-probe-cleanup")
            _sweep_probe_litter(name, "litter-probe")
        return set(WO._load()) == before
    net(a, "a probe leaves NO work order behind in the live queue",
        a_probe_leaves_no_order_behind,
        "six permanent orders described three subsystems that never existed; a queue with "
        "decoration in it is a queue people stop reading, and that is the failure this whole "
        "ladder exists to prevent")

    def the_keeper_asks_before_restarting():
        """The half that matters. `overnight`'s keeper must CONSULT the ledger, not just have
        one available to consult.

        ASKED OF THE PARSE TREE (run #36). The old form took a 1,200-character text window above
        the log line "was down mid-cycle" and looked for the name `_manager_stopped` in it. That
        window is almost entirely the fourteen-line comment recounting the 22:5x incident, which
        names the manager rung repeatedly -- so the consultation could be deleted, the keeper
        would restart a subsystem a person had stopped, and this net would have gone on holding
        on the story of the last time that happened. Now: the call has to be a call, inside the
        keeper, and it has to come BEFORE the restart it is supposed to gate.
        """
        import ast
        tree = _ast_of(os.path.join(_srcdir(), "overnight.py"))
        keep = _defn(tree, "_keep")
        if keep is None:
            return False
        asked = [n.lineno for n in ast.walk(keep)
                 if isinstance(n, ast.Call) and isinstance(n.func, ast.Name)
                 and n.func.id == "_manager_stopped"]
        started = [n.lineno for n in ast.walk(keep)
                   if isinstance(n, ast.Call) and isinstance(n.func, ast.Name)
                   and n.func.id == "start"]
        return bool(asked) and bool(started) and min(asked) < min(started)
    net(a, "the keeper checks for a MANAGER stop before re-asserting a job",
        the_keeper_asks_before_restarting,
        "the ledger existed for 25 minutes and the one process that needed it never opened it")

    def an_unreadable_stop_ledger_stops_everything():
        """FAIL CLOSED. The file's only content is what must not run, so failing to read it
        cannot be permission to run things."""
        import escalation as E
        saved = E.STOPPED
        E.STOPPED = os.path.join(tempfile.gettempdir(), "drill_stopped_bad.json")
        try:
            with open(E.STOPPED, "w", encoding="utf-8") as fh:
                fh.write("{ not json at all")
            held, why = E.subsystem_stopped("anything at all")
            return held is True
        finally:
            try:
                os.remove(E.STOPPED)
            except OSError:
                pass
            E.STOPPED = saved
    net(a, "an unreadable stop ledger reports everything stopped",
        an_unreadable_stop_ledger_stops_everything,
        "'I cannot tell whether a person closed this' is not permission to re-open it")


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
        that merely COULD check is a daemon that does not.

        AND READ AS A PARSE TREE, NOT AS TEXT (run #36). Both names were substring-searched over
        the whole file, and all three daemons carry long comments about staleness that name
        `codewatch.exit_if_stale` -- `publish.py`'s runs to eight lines and quotes it. A daemon
        that merely MENTIONS the check is exactly the daemon this net exists to catch, and until
        now it could not tell that daemon from one that runs it.
        """
        for f in ("publish.py", "foreman.py", "overwatch.py"):
            p = os.path.join(_srcdir(), f)
            if not (_calls(p, "codewatch.exit_if_stale") and _calls(p, "codewatch.stamp")):
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
        """Spend the budget against a scratch ledger and require it to RUN OUT, then refill.

        THE OLD NET WAS `isinstance(CW.BUDGET_PER_HOUR, int) and 0 < ... <= 12`. A constant, and
        one nobody was going to set to zero. The enforcement is `_budget_left`, whose rolling
        hour is the whole mechanism: drop the `t > cutoff` filter and a job that restarted four
        times last week can never restart again; drop the subtraction and a daemon bounces for
        ever. `exit_if_stale` reads `left <= 0` and keeps running STALE on purpose past it —
        lag beats thrash, and this project has already paid for one respawn loop
        (`autostart._twin_watchdog`). None of that was observed by an `isinstance`.

        `_budget_left` and not `exit_if_stale`, deliberately. The budget-exhausted branch is the
        only safe one to drive: the other end of that function CALLS `escalation.escalate` and
        then exits the process, so a net that reached it would either raise a halt on a live
        library or kill the drill outright — and if the budget arithmetic were the thing that
        was broken, that is precisely the branch it would take.

        The ledger path is swapped to a scratch file for the same litter discipline the rest of
        this file keeps: `state/CODEWATCH.json` is the real restart record and a test must not
        write a job into it.
        """
        import codewatch as CW
        import shutil
        real = CW.LEDGER
        d = os.path.join(tempfile.gettempdir(), "drill_codewatch_budget")
        who = "__drill__"
        try:
            shutil.rmtree(d, ignore_errors=True)
            os.makedirs(d, exist_ok=True)
            CW.LEDGER = os.path.join(d, "CODEWATCH.json")

            def ledger(times):
                with open(CW.LEDGER, "w", encoding="utf-8") as f:
                    json.dump({who: times}, f)

            now = time.time()
            ledger([])                                   # a job that has not restarted
            if CW._budget_left(who) != (CW.BUDGET_PER_HOUR, 0):
                return False
            ledger([now - 60] * (CW.BUDGET_PER_HOUR - 1))   # one short of the budget
            left, used = CW._budget_left(who)
            if left != 1 or used != CW.BUDGET_PER_HOUR - 1:
                return False
            ledger([now - 60] * CW.BUDGET_PER_HOUR)      # ... and now it is spent
            left, used = CW._budget_left(who)
            if left > 0 or used != CW.BUDGET_PER_HOUR:
                return False
            ledger([now - 3601] * CW.BUDGET_PER_HOUR)    # an hour on, it is back
            return CW._budget_left(who) == (CW.BUDGET_PER_HOUR, 0)
        finally:
            CW.LEDGER = real
            shutil.rmtree(d, ignore_errors=True)
    net(a, "source-change restarts are budgeted per job per hour", restarts_are_budgeted,
        "an unbudgeted restarter is a respawn loop waiting for an edit storm")

    def twin_detection_does_not_match_bystanders():
        """THE ONE THAT WOULD HAVE CAUSED THE OUTAGE IT PREVENTS, and that then went on to cause
        two outages of its own before it was written correctly.

        The behaviour under test is real: the first `twins()` asked whether a module name
        appeared ANYWHERE in a command line, and immediately matched a
        `pyflakes src/codewatch.py src/publish.py src/foreman.py src/overwatch.py` invocation --
        one linter reported as a twin of three daemons, every one of which would then have
        refused to start because somebody was reading it.

        THE NET ITSELF WAS WRONG TWICE, both times the same way: it asked the LIVE PROCESS
        TABLE. `twins("verify_math") == []` is true only when no `verify_math.py` happens to be
        running -- and the battery runs it, and `mutate.py` runs it inside a sandbox. It
        breached against perfectly correct code and HALTED THE LIBRARY, once on the sandbox copy
        and once on a plain concurrent battery run. Scoping `twins()` to this tree fixed the
        first and not the second, because a live verify_math in this tree is a real match.

        **A net whose answer depends on what happens to be running when it looks is not testing
        the code.** So this one no longer looks. It puts SYNTHETIC command lines to the same
        predicate `twins()` uses, which is deterministic, needs no processes, and actually
        exercises the distinction that matters.
        """
        import codewatch as CW
        here = os.path.dirname(os.path.abspath(__file__)).replace("\\", "/")
        cases = [
            # (argv, module, should_match, what this argv IS)
            ([r"C:/py/python.exe", here + "/publish.py", "--push"], "publish", True,
             "the daemon itself"),
            ([r"C:/py/python.exe", "-u", here + "/publish.py", "--loop", "10"], "publish", True,
             "the daemon with interpreter flags"),
            ([r"C:/py/python.exe", "-m", "pyflakes", here + "/publish.py"], "publish", False,
             "a LINTER naming the file"),
            ([r"C:/Windows/system32/grep.exe", here + "/publish.py"], "publish", False,
             "grep -- not even python"),
            ([r"C:/py/python.exe", "-c", "import publish"], "publish", False,
             "python -c that merely imports it"),
            ([r"C:/py/python.exe", "/tmp/sandbox/src/publish.py"], "publish", False,
             "ANOTHER TREE's copy of the same file"),
        ]
        for argv, module, want, _what in cases:
            if CW.runs_script(argv, module, root=here) is not want:
                return False
        return True
    net(a, "twin detection matches the script being RUN, not any mention of it",
        twin_detection_does_not_match_bystanders,
        "a linter is not a daemon; refusing to start because someone read the file is an outage")

    net(a, "a namesake in ANOTHER tree is not a twin of this tree's module",
        _twins_ignores_a_foreign_tree,
        "22:38 today: a mutation sandbox's own `python src/verify_math.py` was read as a twin of "
        "this tree's, the control net above breached against correct code and HALTED the "
        "library -- and claim_singleton would have stood a live daemon down for the same reason")

    def singleton_guard_is_wired_into_the_daemons():
        """ASKED OF THE PARSE TREE (run #36). `"claim_singleton" not in fh.read()` was satisfied
        by any mention at all, and `publish.py`'s own comment above the call explains at length
        why the guard is there and only fires in loop mode -- so the call could go and the
        explanation would answer for it, which is how two publishers end up in one export repo.
        """
        for f in ("publish.py", "foreman.py", "overwatch.py"):
            if not _calls(os.path.join(_srcdir(), f), "codewatch.claim_singleton"):
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


# ============================================================== THE CLASS, NOT THE INSTANCE

_BARE_COUNT = re.compile(r"^\d+\s+[A-Za-z]+$")
_VERDICT_WORDS = ("failed", "passed", "errors", "failures")
_OUTPUT_NAMES = {"stdout", "stderr", "out", "output", "completed"}


def _is_process_output(node):
    """Does this expression plausibly hold the text a subprocess printed?"""
    import ast
    if isinstance(node, ast.BoolOp):                      # (r.stdout or "")
        return any(_is_process_output(v) for v in node.values)
    if isinstance(node, ast.Call):                        # r.stdout.lower()
        return _is_process_output(node.func)
    if isinstance(node, ast.Attribute):
        return node.attr in _OUTPUT_NAMES or _is_process_output(node.value)
    if isinstance(node, ast.Name):
        return node.id in _OUTPUT_NAMES
    return False


def _counts_decided_by_substring(src=None):
    """-> [site] where a gate reads a NUMBER out of process output with `in`.

    THREE TIMES IS A CLASS. `adopt_hosts` did it, `foreman._checks_pass` did it (fixed with a
    regex on 2026-08-23), and `local_agent._gates` was still doing it today -- on the LAST gate
    standing between the local model and `src/`. `verify_math` prints
    `RESULT: N passed, M FAILED`, and `"0 FAILED" not in stdout` is FALSE for `10 FAILED`,
    `20 FAILED` and `100 FAILED`, because the zero is just the last digit of M. So the gate
    passed every patch that broke a round number of invariants, which is precisely the patches
    worth reverting.

    Two instances is a coincidence and three is a class, and a class deserves a net rather than
    a third individual fix -- otherwise the fourth one is written next month by somebody who
    read neither of the first three. Asked of the AST: a string literal that is either a bare
    `<count> <word>` or carries a verdict word, tested with `in`/`not in` against something that
    looks like what a subprocess printed. `"Traceback" in stderr` and `"undefined name" in
    r.stdout` are ordinary substring tests about TEXT and are deliberately not flagged; the
    defect is a substring standing in for a COMPARISON.
    """
    import ast
    src = src or os.path.dirname(os.path.abspath(__file__))
    found = []
    for f in sorted(os.listdir(src)):
        if not f.endswith(".py"):
            continue
        try:
            with open(os.path.join(src, f), encoding="utf-8") as fh:
                tree = ast.parse(fh.read(), filename=f)
        except (OSError, SyntaxError) as e:
            found.append("%s: UNPARSEABLE (%s)" % (f, type(e).__name__))
            continue
        for n in ast.walk(tree):
            if not isinstance(n, ast.Compare):
                continue
            left = n.left
            if not (isinstance(left, ast.Constant) and isinstance(left.value, str)):
                continue
            v = left.value.strip()
            if not (_BARE_COUNT.match(v) or any(w in v.lower() for w in _VERDICT_WORDS)):
                continue
            for op, right in zip(n.ops, n.comparators):
                if isinstance(op, (ast.In, ast.NotIn)) and _is_process_output(right):
                    found.append("%s:%d %r against process output" % (f, n.lineno, left.value))
    return found


def _a_scan_can_tell_code_from_prose_about_code():
    """The other half of the same family, and it cost a halt this morning.

    `_no_programmatic_clear` was a literal scan of `src/` for `escalation.clear(` and
    `ESC.clear(`. `verify_math.py` then gained a paragraph EXPLAINING that those are the two
    spellings it looks for, quoting both, and the scan matched the explanation and BREACHED --
    which halts the library. A literal cannot tell code from prose about code: it fails on an
    honest description and it passes on a comment, so it is wrong in both directions at once.

    Put to the rewritten scan directly, over a scratch tree rather than the real one: a file
    that only NAMES the forbidden call in a comment and a string must pass, and each of the four
    real spellings must fail. Nothing is written into `src/`.
    """
    import shutil
    d = tempfile.mkdtemp(prefix="drillprose_")
    try:
        prose = os.path.join(d, "prose")
        os.makedirs(prose)
        with open(os.path.join(prose, "explains.py"), "w", encoding="utf-8") as f:
            f.write("# The rule: nothing may call escalation.clear( or ESC.clear( at all.\n"
                    "WHY = 'escalation.clear( is refused; only a person may lift a halt'\n")
        if not _no_programmatic_clear(src=prose):
            return False                      # a comment about the rule is not a breach of it
        for i, body in enumerate((
                "import escalation\nescalation.clear('x')\n",
                "import escalation as X\nX.clear('x')\n",
                "from escalation import clear\nclear('x')\n",
                "import escalation as e\ngetattr(e, 'clear')('x')\n")):
            sub = os.path.join(d, "call%d" % i)
            os.makedirs(sub)
            with open(os.path.join(sub, "caller.py"), "w", encoding="utf-8") as f:
                f.write(body)
            if _no_programmatic_clear(src=sub):
                return False                  # a real call, in a spelling that walked past
        return True
    finally:
        shutil.rmtree(d, ignore_errors=True)


def drill_defect_classes():
    """Two shapes that have each appeared three times. Netted as classes, not as instances."""
    a = "THE CLASS — a defect seen three times deserves a net, not a third individual fix"
    net(a, "NO gate anywhere in src/ decides a COUNT by substring",
        lambda: _counts_decided_by_substring() == [],
        "'0 FAILED' not in stdout is FALSE for '10 FAILED'; adopt_hosts, foreman._checks_pass "
        "and local_agent._gates each shipped this, the last on the only lane a model may write "
        "into src/ through")
    net(a, "a scan of src/ is not fooled by a COMMENT about the thing it looks for",
        _a_scan_can_tell_code_from_prose_about_code,
        "this exact confusion breached _no_programmatic_clear against correct code this "
        "morning, and a breach there halts the library")


# ============================================================== THE WORK-LIST (Hard Rule 0)

def _synthetic_hostless():
    """Fifteen sources of increasing size — the measured shape of the fault, in miniature."""
    return {"drill-source-%02d" % i: ["name %d-%d" % (i, j) for j in range(i + 1)]
            for i in range(15)}


def _the_work_list_rotates():
    """Every hostless source is reached within a bounded number of cycles.

    THE SHAPE THAT LOOKED LIKE COMPLIANCE, fixed today. `sweep` ranked the hostless sources by
    entry count and then took `order[:limit]`, and `foreman.scout_hostless()` calls it as
    `sweep(limit=4)` on a thirty-second loop. Ranking is allowed; truncating is not, and the
    reason is not theoretical here: a source LEAVES `hostless()` only when a scout SUCCEEDS, so a
    source that keeps failing stays hostless, stays among the four largest, and is re-scouted
    twice a minute for ever -- while everything ranked fifth and below is never attempted once.
    The window could not rotate, because the only thing that could move a source out of it was
    the very success that was not happening. Measured when it was fixed: 15 hostless sources, of
    which 4 could ever be reached. A count that stayed right the whole time is what made it
    comfortable.

    ROTATION IS THE PROPERTY, so rotation is what is asserted -- not the size of the window, and
    not anything about `scout()`. Fifteen synthetic sources, a limit of four, four cycles: the
    windows must differ, each must be full, the deferred remainder must be NAMED on the way past
    (a window nobody can see the far side of reads exactly like a complete list), and the union
    must be the whole universe. Under the old entry-count ordering the same run returns the same
    four sources four times and the union is four of fifteen.
    """
    import contextlib
    import io
    import shutil
    import scout as SC
    d = tempfile.mkdtemp(prefix="drillscout_")
    # NOTHING REAL IS TOUCHED. `ATTEMPTS` is the ledger the rotation runs on, so a drill that
    # stamped it would move every live source's place in the queue as the price of testing that
    # the queue rotates; `LOG` and `scout` are redirected for the same reason -- and `scout()`
    # is a network call, which is not what is under test. The ORDER the work-list is walked in
    # is decided before any source is touched. All four are restored in the `finally`.
    keep = (SC.hostless, SC.ATTEMPTS, SC.LOG, SC.scout)
    try:
        table = _synthetic_hostless()
        SC.hostless = lambda: dict(table)
        SC.ATTEMPTS = os.path.join(d, "SCOUT_ATTEMPTS.json")
        SC.LOG = os.path.join(d, "SCOUT.json")
        SC.scout = lambda source, names, register=True: {
            "source": source, "proposed": 0, "kept": [], "checked": [], "note": "drill stub"}
        windows, said = [], []
        for _ in range(4):
            buf = io.StringIO()
            with contextlib.redirect_stdout(buf):
                windows.append([r["source"] for r in SC.sweep(limit=4, register=False)])
            said.append(buf.getvalue())
        return (all(len(w) == 4 for w in windows)
                and windows[0] != windows[1]
                and all("waiting for a later cycle" in s for s in said)
                and set().union(*windows) == set(table)
                and os.path.exists(SC.ATTEMPTS))
    finally:
        SC.hostless, SC.ATTEMPTS, SC.LOG, SC.scout = keep
        shutil.rmtree(d, ignore_errors=True)


def _a_new_source_does_not_queue_behind_the_old_ones():
    """Absent-means-never-attempted, so a source added today goes to the FRONT.

    The tie-break is entry count, and the newcomer here is deliberately the SMALLEST source in
    the set -- dead last under the ordering that caused the fault, first under the one that
    replaced it. Nothing has to seed the ledger for a new source to be reachable, which is the
    half of the fix that keeps `SCOUT_ATTEMPTS.json` from becoming a registry somebody has to
    maintain.
    """
    import contextlib
    import io
    import shutil
    import scout as SC
    d = tempfile.mkdtemp(prefix="drillscout2_")
    keep = (SC.hostless, SC.ATTEMPTS, SC.LOG, SC.scout)
    try:
        table = _synthetic_hostless()
        SC.hostless = lambda: dict(table)
        SC.ATTEMPTS = os.path.join(d, "SCOUT_ATTEMPTS.json")
        SC.LOG = os.path.join(d, "SCOUT.json")
        SC.scout = lambda source, names, register=True: {
            "source": source, "proposed": 0, "kept": [], "checked": [], "note": "drill stub"}
        with contextlib.redirect_stdout(io.StringIO()):
            for _ in range(4):
                SC.sweep(limit=4, register=False)
            table["drill-newcomer"] = ["its one and only name"]
            window = [r["source"] for r in SC.sweep(limit=4, register=False)]
        return window and window[0] == "drill-newcomer"
    finally:
        SC.hostless, SC.ATTEMPTS, SC.LOG, SC.scout = keep
        shutil.rmtree(d, ignore_errors=True)


def drill_scout():
    """The hostless work-list — a rate is a cost decision; a cap is a smaller universe."""
    a = "THE WORK-LIST — does the scouting window rotate, or is it the universe wearing a limit?"
    net(a, "every hostless source is reached within a bounded number of cycles",
        _the_work_list_rotates,
        "Hard Rule 0: `order[:limit]` over an entry-count ranking pinned the same 4 of 15 "
        "sources for ever, because a source only leaves hostless() when a scout SUCCEEDS")
    net(a, "a source added today is scouted next cycle, not after every older one",
        _a_new_source_does_not_queue_behind_the_old_ones,
        "absent-means-never-attempted is what keeps the attempts ledger from becoming a "
        "registry somebody has to seed by hand")


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

    def run_actually_holds_the_lock():
        """FOUR GREEN NETS EXERCISED THE LOCK; NONE ASKED WHETHER ANYTHING TOOK IT.

        `_lock_acquire` and `_lock_release` had no call site anywhere inside `mutate.py`. The
        lock was correct, exclusive, fail-closed and stale-tolerant, and it was never held --
        so `publish.py`'s "REFUSING TO PUSH while a mutation is active" could not fire, and the
        push that shipped a deliberately corrupted `prose_gate.py` to a public repo would have
        gone through again. The nets around it all pointed at the mechanism and not one of them
        pointed at the wiring, which is the same distance between "the guard exists" and "the
        guard is in effect" that Hard Rule -1's fourth property is about.

        BOTH EXITS, because the failure path is the one that matters: a run that dies
        mid-mutation is exactly when the tree is most likely to be sitting corrupt, and a lock
        left behind blocks every future push until a person deletes a file by hand.

        `LOCK` is redirected and the mutation BODY is replaced, so no source file is corrupted
        and no sandbox is built -- what is under test is whether `run()` wraps the body at all.
        """
        import mutate as M
        saved_lock, saved_body, saved_held = M.LOCK, M._run_mutation, M._HELD
        M.LOCK = os.path.join(tempfile.gettempdir(), "drill_mut_held.json")
        seen = []
        try:
            if os.path.exists(M.LOCK):
                os.remove(M.LOCK)
            M._HELD = None
            M._run_mutation = lambda *a, **k: seen.append(M.active()[0]) or {"ok": True}
            M.run("scope.py")
            if seen != [True] or M.active()[0]:
                return False                      # not held during, or not released after

            def boom(*a, **k):
                seen.append(M.active()[0])
                raise RuntimeError("drill: the mutation body dies mid-run")
            M._run_mutation = boom
            if not _refuses(lambda: M.run("scope.py"), RuntimeError):
                return False
            return seen == [True, True] and not M.active()[0] and not os.path.exists(M.LOCK)
        finally:
            M.LOCK, M._run_mutation, M._HELD = saved_lock, saved_body, saved_held
    net(a, "run() actually HOLDS the lock, on the crash path too", run_actually_holds_the_lock,
        "_lock_acquire had no caller anywhere in mutate.py, so publish's 'refusing to push "
        "during a mutation' could never fire -- and four nets exercised the lock without ever "
        "asking whether anything took it")

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
        path for writing and must verify the live file is byte-identical afterwards.

        ASKED OF THE PARSE TREE (run #36). Three substrings over the whole file, and `mutate.py`
        names `live_file_untouched` in its module docstring before it ever computes it -- so
        two of the three could be satisfied by prose alone. Now: `sandbox` must be a DEF, the
        untouched verdict must be RECORDED as a dict entry, and the OWNER-level code must be a
        code string rather than a word in a paragraph about what would happen if it fired.
        """
        import ast
        tree = _ast_of(os.path.join(_srcdir(), "mutate.py"))
        recorded = any(isinstance(k, ast.Constant) and k.value == "live_file_untouched"
                       for n in ast.walk(tree) if isinstance(n, ast.Dict) for k in n.keys)
        return (recorded and _defn(tree, "sandbox") is not None
                and _says(tree, "MUTATE_TOUCHED_LIVE_TREE"))
    net(a, "mutation writes into a sandbox and proves the live file is untouched",
        mutation_never_touches_the_live_tree,
        "fifteen processes read the live tree; corrupting it is not something a lock can fix")

    def abandoned_sandboxes_are_reaped():
        """A killed run cannot clean up after itself -- `finally` does not run on a kill -- and
        two kills leaked 154 MB in two hours. A nightly job that leaks 50 MB per interruption
        fills a disk quietly, and a full disk takes down the crawl, the model and the publisher
        at once for a reason nobody would look for.

        THIS NET COULD NOT GO RED (found by the run #35 sweep, fixed run #36). It called
        `M.reap_orphans(older_than=10 ** 9)` and asserted the answer was `[]`. Inside,
        `cutoff = time.time() - older_than`, so a threshold of ~31.7 years puts the cutoff
        before the epoch and nothing on any disk can be old enough to reap: the call returns
        `[]` whether reaping works, is broken, or has been replaced by `return []` -- which is
        the exact 154 MB regression the net exists to catch. It asserted the arithmetic of its
        own argument. A net that cannot refuse is not a safety, it is a green light.

        It now builds a REAL orphan -- a directory carrying the real `SANDBOX_PREFIX`,
        back-dated past the real `ORPHAN_AGE_SECONDS` -- and a second one left FRESH, and
        requires the aged one gone and the fresh one standing. Both halves: a reaper that
        deletes indiscriminately would delete the sandbox of the run doing the reaping, and
        that is an outage rather than a leak.

        AT THE MODULE'S OWN DEFAULT AGE, deliberately, so a genuine orphan older than six hours
        is reaped as it passes. That is what the function is for, this battery is the only thing
        that calls it, and reaping is safe by construction -- a live run's sandbox is minutes
        old, not hours.
        """
        import mutate as M
        if not hasattr(M, "reap_orphans") or M.ORPHAN_AGE_SECONDS < 3600:
            return False
        root = tempfile.gettempdir()
        aged = os.path.join(root, M.SANDBOX_PREFIX + "drillprobe_aged_%d" % os.getpid())
        fresh = os.path.join(root, M.SANDBOX_PREFIX + "drillprobe_fresh_%d" % os.getpid())
        try:
            for p in (aged, fresh):
                os.makedirs(p, exist_ok=True)
                with open(os.path.join(p, "marker.txt"), "w", encoding="utf-8") as fh:
                    fh.write("drill orphan probe -- safe to delete")
            back = time.time() - (M.ORPHAN_AGE_SECONDS + 3600)
            os.utime(aged, (back, back))
            removed = M.reap_orphans()
            return (aged in removed and not os.path.isdir(aged)
                    and fresh not in removed and os.path.isdir(fresh))
        finally:
            # The probe cleans up after itself whichever way the answer came out; a net that
            # leaves litter in TEMP is a net that reproduces the fault it is testing for.
            shutil.rmtree(aged, ignore_errors=True)
            shutil.rmtree(fresh, ignore_errors=True)
    net(a, "abandoned sandboxes are reaped, but only once they are old",
        abandoned_sandboxes_are_reaped,
        "a leak of 50 MB per interrupted run fills a disk without ever reporting anything")

    def a_gate_that_cannot_finish_is_refused():
        """BOTH DIRECTIONS OF THE SAME WORTHLESS ANSWER. Before the baseline existed, a
        pre-existing failure killed every mutant and the run reported a perfect score. After it
        existed, a gate that TIMED OUT on clean code made every mutant compare
        `TIMEOUT == TIMEOUT` and the run reported the whole set as surviving. Both look exactly
        like a finished run; only the sign of the lie changes.

        Measured 2026-08-26: `verify_math` finishes in 44s on the live tree and stalled past
        330s in a sandbox, because section 19aa makes a live API call to fandom and Wikipedia.
        """
        import mutate as M
        bad = M.unusable_gates({"ok": "rc=0|RESULT: 10 passed, 0 FAILED",
                                "hung": "TIMEOUT", "broke": "ERROR:OSError"})
        return sorted(n for n, _ in bad) == ["broke", "hung"]
    net(a, "a gate that cannot complete on clean code is refused, not averaged in",
        a_gate_that_cannot_finish_is_refused,
        "TIMEOUT == TIMEOUT reports every mutant as surviving and looks like a finished run")

    def publish_asks_before_pushing():
        """The step whose failure is IRREVERSIBLE and OUTWARD-FACING. Verified by reading the
        push path, the same way `guards_are_wired_where_claimed` checks the other interlocks --
        a net that actually pushed to prove a refusal would be worse than the bug.

        ASKED OF THE PARSE TREE (run #36). The old form sliced the file text at "def push(" and
        looked for "import mutate" and "REFUSING TO PUSH" in the remainder -- both of which the
        long comment inside `push()` about the two-writer fault could carry on its own, and one
        of which (`import mutate`) is a phrase this net's own sibling docstrings use. `push` is
        now located as a DEF, the interlock has to be a real import inside it, and the refusal
        has to be a string the code actually carries rather than a phrase about refusing.
        """
        import ast
        tree = _ast_of(os.path.join(_srcdir(), "publish.py"))
        push = _defn(tree, "push")
        if push is None:
            return False
        imports_mutate = any(al.name == "mutate"
                             for n in ast.walk(push) if isinstance(n, ast.Import)
                             for al in n.names)
        return imports_mutate and _says(push, "REFUSING TO PUSH")
    net(a, "publish refuses to push while a mutation run is active", publish_asks_before_pushing,
        "a mutated file pushed to a public repo is public even after the next commit")

    def drill_does_not_halt_during_a_mutation_run():
        """This file must PRINT a breach during a mutation run and must not HALT over it --
        mutate reads the breach from stdout, which is how a mutant gets killed."""
        # ASKED OF THE PARSE TREE (run #36), which retires the whole `rfind` apparatus below and
        # the two false breaches that produced it. The old form searched this file's own TEXT
        # for "    if breached:" and '"DRILL_BREACH"' and had to use `rfind` for both, because a
        # forward search matched the string literals inside THIS VERY FUNCTION, 78,000
        # characters before the branch it meant to inspect -- it breached against perfectly
        # correct code twice, and a net that fails for its own reasons teaches people to ignore
        # it. Offsets in a file are also the wrong instrument for "the interlock is inside the
        # branch": a comment carrying either phrase moves them. The branch is now found as the
        # `if breached:` inside `main()`, and the mutation interlock has to be a real call to
        # `mutate.active` within it, with the not-halting message a code string of that branch.
        import ast
        tree = _ast_of(os.path.join(_srcdir(), "drill.py"))
        main_fn = _defn(tree, "main")
        if main_fn is None:
            return False
        for n in ast.walk(main_fn):
            if not (isinstance(n, ast.If) and isinstance(n.test, ast.Name)
                    and n.test.id == "breached"):
                continue
            if (_calls_within(tree, n, "_MUT.active")
                    and _says(n, "MUTATION RUN IS ACTIVE")
                    and _says(n, "DRILL_BREACH")):
                return True
        return False
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
        """The manifest builder must consult `roll`, not just read the file.

        ASKED OF THE PARSE TREE (run #36). `"out_of_scope" in text and "import roll" in text`
        is answered by any comment naming either -- and this net's whole subject is a status
        string that sat in a file for five days with no consumer, so "the name appears
        somewhere" is the precise evidence it must not accept. `roll.out_of_scope` now has to
        be CALLED.
        """
        return _calls(os.path.join(_srcdir(), "manifest_builder.py"), "roll.out_of_scope")
    net(a, "the generator consults the exclusion list before building jobs",
        generator_actually_skips_an_excluded_source,
        "a status string no consumer reads is a decision that did not happen")

    def resync_cannot_revert_an_exclusion():
        """THE TRAP THIS ALMOST FELL INTO. `resync_roll` rebuilds status from records on disk
        with the rule `catalogued if n else keep` -- so an excluded source that still HAS records
        would be silently promoted back. All four of the 2026-08-25 exclusions have records.

        ASKED OF THE PARSE TREE (run #36). `"OUT_OF_SCOPE" in text` was the weakest check of the
        nine: the eight-line comment above that branch spells the constant out in full while
        explaining why it is there, so the guard could be deleted, the promotion would resume,
        and the net would have kept holding on the paragraph describing the trap it had fallen
        back into. The status test now has to be a real comparison against `roll.OUT_OF_SCOPE`,
        guarding a branch that does NOT reassign the status.
        """
        import ast
        tree = _ast_of(os.path.join(_srcdir(), "resync_roll.py"))
        for n in ast.walk(tree):
            if not (isinstance(n, ast.If) and isinstance(n.test, ast.Compare)):
                continue
            if not any(isinstance(c, ast.Attribute) and c.attr == "OUT_OF_SCOPE"
                       for c in n.test.comparators):
                continue
            # The branch must LEAVE the status alone; a guard that then rewrites it is not one.
            if not _subscript_assigns(ast.Module(body=n.body, type_ignores=[]), "r", "status"):
                return True
        return False
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
        """`query()` is read-only BY CONTRACT. Prove the contract is enforced, not documented.

        AGAINST A SCRATCH INDEX, NEVER THE LIVE ONE (order 38ce9cb3b499, run #36). This aimed
        `CREATE TABLE _drill_should_not_exist` straight at `corpus_db.DB`. In the single case
        the net exists to catch -- the read-only guard genuinely broken -- that statement LANDS,
        in the live SQL index; the undo was a best-effort DROP whose own failure was recorded
        with `silence.note` and nothing else. So the check's failure mode was "leave a stray
        table in the corpus index and mention it in a ledger", inside a file whose framing is
        that it never writes to the corpus. `connect()` reads `DB` at call time on purpose --
        its docstring says why -- so pointing it at a throwaway database is the whole fix.

        AND THE REFUSAL HAS TO BE SPECIFIC. A `query()` that raised on everything would have
        satisfied the old net for entirely the wrong reason, so a SELECT goes through first:
        this only means something while reads still work.
        """
        import sqlite3
        import corpus_db
        real = corpus_db.DB
        d = tempfile.mkdtemp(prefix="drill_index_")
        corpus_db.DB = os.path.join(d, "corpus.db")
        try:
            con = sqlite3.connect(corpus_db.DB)
            con.execute("CREATE TABLE probe (x INTEGER)")
            con.execute("INSERT INTO probe VALUES (1)")
            con.commit()
            con.close()
            if corpus_db.query("SELECT x FROM probe")[1] != [(1,)]:
                return False                 # a reader that cannot read proves nothing
            try:
                corpus_db.query("CREATE TABLE _drill_should_not_exist (x INTEGER)")
            except Exception:
                return True                  # refused, which is the whole point
            return False
        finally:
            corpus_db.DB = real
            shutil.rmtree(d, ignore_errors=True)
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
               drill_done_keys, drill_profile,
               drill_snapshot, drill_stale_writer, drill_policy, drill_binding_identity,
               drill_fetch, drill_cascade, drill_park,
               drill_workorders, drill_inspector, drill_no_top_ups, drill_probe_honesty, drill_rung_four, drill_codewatch, drill_scout,
               drill_defect_classes, drill_mutation,
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

    # THE VERDICT, ON DISK, WITH A TIME ON IT AND THE CODE IT WAS ABOUT.
    #
    # Two separate faults lived in the four lines this replaces, both filed by the run #34
    # sweep, and both are about a result being believed longer than it is true for.
    #
    # `open(out, "w")` is a TRUNCATE-THEN-FILL, not a write. This file has two live readers --
    # `dashboard.py:529`, which puts it on the page, and `workorders.py:564`, which GRADES THE
    # BATTERY from it and closes a DRILL_BREACH order on the strength of it -- so a reader
    # arriving in the gap sees an empty or half-written verdict about the safety layer. And the
    # `except: pass` around it meant a write that never landed left the PREVIOUS run's result
    # standing as current with nothing anywhere recording the substitution. `silence.write_json`
    # is this project's stated one correct way to land a shared file, and its docstring counts
    # the twelve sites that had to be converted before this one.
    #
    # NO TIME FIELD AT ALL was the worse half. It wrote nets/held/breached/liveness/ceiling and
    # nothing to date them by, so nothing could tell a fresh result from a week-old one -- and a
    # reader falling back to `d.get("at", 0)` gets the epoch, which formats as a perfectly
    # plausible wall-clock time. THIS RUN WAS MISLED BY THAT TWICE, calling a current artifact
    # stale. Its siblings `state/preflight_last.json` and `data/ALLSWEEP.json` both carry `at`,
    # which is exactly why `workorders` can give them PREFLIGHT_STALE and BATTERY_STALE codes;
    # the drill -- the member whose breach HALTS THE LIBRARY -- was the one that could not be
    # aged. `src` is `codewatch`'s fingerprint of the tree, so a result can also be tied to the
    # CODE it tested rather than only to a clock: a green drill and an edited src/ are not the
    # same sentence. (The staleness work order itself belongs in `workorders.py`, which this
    # file does not own.)
    out = os.path.join(HERE, "state", "drill_last.json")
    try:
        import silence
        try:
            import liveness
            _lv = sum(len(v) for v in liveness.scan().values())
        except Exception:
            _lv = None
            silence.note("drill.py:liveness-scan")
        try:
            import codewatch as _CW
            _fp = _CW.fingerprint()
        except Exception:
            _fp = None
            silence.note("drill.py:src-fingerprint")
        landed = silence.write_json(
            out, {"at": time.time(), "src": _fp,
                  "nets": len(RESULTS), "held": held,
                  "breached": [r["net"] for r in breached],
                  "liveness": _lv, "ceiling": LIVENESS_CEILING,
                  "results": RESULTS}, indent=1, ensure_ascii=False)
    except Exception:
        landed = False
        try:
            import silence
            silence.note("drill.py:stamp")
        except Exception:
            pass
    if not landed:
        # HONOUR THE VERDICT. A stamp that did not land means the dashboard and the work-order
        # sweep are both about to read the PREVIOUS run and call it this one, which is the
        # "green check that never ran" shape with a longer fuse. Said out loud, on the same
        # stdout `mutate.py` reads, rather than swallowed.
        print("\nWARNING: this run's verdict did NOT land in state/drill_last.json. The "
              "dashboard and `workorders --sweep` will report the PREVIOUS run's result as "
              "current until a drill writes successfully.")

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
