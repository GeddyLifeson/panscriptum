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
import contextlib
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
import assay as ASSAY          # noqa: E402
import escalation as ESC       # noqa: E402
import prose_gate as PG        # noqa: E402

RESULTS = []

# The ratchet for `liveness.py`. LOWER this when code is cleaned up. Raising it to make the
# drill go green is the move this whole layer exists to prevent -- if a new finding appears, the
# finding is the problem, not the number. There is exactly one lawful reason to raise it: the
# DETECTOR got sharper, not the code worse. Both raises on record are that, and each is written
# out below, because a lawful raise and a rubber stamp are the same edit and only the reasoning
# tells them apart.
#
# WHAT IT COUNTS: the SUM of every list `liveness.scan()` returns -- dead module-level functions
# and methods, dead classes, dead MODULES, syntactic tautologies, phantom guards, unparsed files.
# It has never been a count of dead functions alone, and the comment this replaces still said "38
# dead module-level functions" three limbs after that stopped being true.
#
# THE MEASUREMENT IS NOT RESTATED HERE ANY MORE, and that is the point of this paragraph rather
# than an omission from it (orders b99192e41488 and f5549e17b43a, both filed against the number
# that used to sit on this line). It said "Total 46" and was 47 by the time the first order was
# written, 48 by the time either was worked -- three wrong values inside four days, in the file
# whose own `drill_inspector` lists "a comment asserting a measurement that was backwards" among
# the four failures it was built for. A number that moves twice in an afternoon cannot be
# maintained in prose, and a prose copy of a measurement is exactly the thing this layer exists
# to distrust. `python src/liveness.py` prints the live figure, and the drill's own verdict file
# carries `liveness` and `ceiling` side by side on every run, with a time on it. Read either.
# Observed band while these paragraphs were written: 46 to 48, no dead code added or removed.
#
# RAISE 1, 38 -> 41 on 2026-08-26. `liveness`'s `used` set was a single flat, scope-blind,
# module-blind bag of every identifier in `src/`, so a LOCAL LOOP VARIABLE named `_p` in
# cleanup.py and tells.py marked every module-level `_p()` in the project as called -- and
# `coverage._p()`, which has zero callers and is named at liveness.py:12 as the founding example
# of why that module exists, was missing from its own report. The detector could not see its own
# worked example. Usage now resolves the way Python resolves it: a bare name only reaches
# functions in its OWN module, and a cross-module call must arrive as `mod.name`, `from mod
# import name`, or a string handed to getattr. Three functions that were always dead became
# visible; 38 was a floor being ratcheted as though it were a total.
#
# RAISE 2, 41 -> 52 on 2026-08-29 (order 209391b4f990). `scan()` gained a MODULE limb, and it is
# the one finding the per-symbol passes cannot ever produce: a function is credited as used by a
# bare-name Load anywhere in its OWN module, so every function in a module nothing imports is
# kept alive by its siblings, and that module reports ZERO findings -- byte-for-byte what a
# clean, live module reports. Ten modules in `src/` are imported and named by nothing else in
# the tree (chord_field, descending_ladder, halo, handbuilt, module_index, pantheon, render,
# scale_theories, wh40k, zfighters); two of them were already filed by hand as individual
# findings (render 707fefc17465, scale_theories SWEEP34_FINDING) precisely because no instrument
# could see them. Not one line of dead code was added to reach 48.
#
# THE HEADROOM IS CHOSEN, not left over: the ceiling sits a handful above whatever the current
# measurement is, and the width of that handful is the thing argued for below, not its endpoints.
#   * Not zero. Order 6c479972e838 filed the previous state -- the ceiling standing exactly at
#     the measurement -- as a fault in its own right, and it is: the count MOVES during ordinary
#     work. It was watched go 34 -> 35 -> 37 across this single shift, none of it from new dead
#     code, all of it pre-existing symbols becoming visible as other agents' edits changed who
#     references what. A ratchet that breaches on the next honest addition gets raised in a
#     hurry by whoever is unblocking themselves, which is the rubber stamp arriving by the back
#     door -- and here it does not merely annoy somebody, it HALTS THE LIBRARY, because a
#     breached drill net escalates to OWNER.
#   * Not large. The gap must stay deliberately far under the TEN a single orphaned module
#     contributes, so a whole unreachable file can never hide inside the slack -- which is the
#     specific regression the module limb was added to catch, and it is the property that
#     actually has to hold. Anything from four to nine satisfies it, and the gap has been
#     everywhere in that band since 52 was set, purely because the measurement wanders.
#
# WHY THE GAP IS WHATEVER IT IS ON A GIVEN DAY, AND WHY THAT IS NOT A DRIFT UPWARD (order
# 859a95edf44f, ruled 2026-08-29). The ceiling has not moved. The MEASUREMENT has: 48 when the
# paragraphs above were written, 47 when that order was filed a few hours later, 46 when it was
# ruled on, 47 by the next sweep and 48 again four days later -- none of it from anybody adding
# or deleting dead code on purpose. That is now five independent observations of the same
# phenomenon and it is the whole case for the headroom existing. The order asked for the ceiling
# to be lowered to "the measured value", which was 47 when it was written and was already wrong
# by one before it was read; a ceiling set to a number that moves twice in an afternoon is a
# halt waiting for the next honest edit.
#
# The order is also right that headroom is slack, and the answer to that is the ten-module
# floor, not zero: what the slack must never be able to hide is a whole unreachable FILE, and
# six cannot. Six unfailable checks appearing one at a time is what `liveness.py`'s own report
# is for; nobody reads the ceiling to find those, they read the rows.
#
# The lawful lowering is to measured + about four, and the time for it is AFTER a shift closes,
# not during one -- which is what order 859a95edf44f's own remedy note says. Taken now, while
# sixteen agents are still editing and a mutation run is live, it would pin the ratchet to a
# number measured in the middle of the churn it exists to tolerate.
# EXCEEDING IT MEANS: something in `src/` acquired more unreachable code than a shift's ordinary
# churn accounts for. Read `python src/liveness.py`, find the new rows, and fix or delete them.
# It does NOT mean "raise the number" -- unless you can write a paragraph like the two above,
# naming what the instrument can now see that it could not before.
LIVENESS_CEILING = 52

# WHERE THE CASCADE'S CONFIG LIVES, for the one net that reads outside this repository.
# `paid_access_stays_switched_off` checks a ruling recorded in ANOTHER project's config (the
# owner holds `allow_paid`), and it used to carry that project's absolute path as a literal --
# one machine's directory layout, written into the safety layer, with doubled backslashes that
# made it read as an escaped path when it was not one (order eed51b638439). Taken from the
# environment now, so a different machine says where its own config is instead of making the net
# wrong; the fallback is where it sits on this one. Absent is a legitimate answer and the net
# treats it as "not this machine" rather than as a pass.
CASCADE_CONFIG = os.environ.get(
    "PANSCRIPTUM_CASCADE_CONFIG",
    os.path.join(os.path.expanduser("~"), "cascade", "config.json"))

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


@contextlib.contextmanager
def _ledger_redirected(root):
    """Point EVERY path `ledger_guard` writes at `root`, together, and put them all back.

    WRITTEN AFTER THIS HELPER'S ABSENCE CORRUPTED THE REAL LEDGER STATE (2026-09-01). Two nets
    were added the same day to prove the append-only gate works. Each repointed the module
    globals it happened to think about: the first set `HERE` and `SNAPSHOT_DIR`, the second set
    `HERE` and `CHAIN`. `ledger_guard.seal()` writes BOTH -- a sealed copy of every append-only
    ledger into `SNAPSHOT_DIR`, and a hash-chain link into `CHAIN`. So each net redirected half
    of what it drove and sent the other half into the live tree: the first appended fixture
    links to the real `state/ledger_chain.jsonl`, the second overwrote the real sealed snapshots
    of `HANDOFF.md` and `handoff/HANDOFF.md` with two hundred lines reading `line 0`, `line 1`.

    No LEDGER CONTENT was lost -- the live files were never touched, and were still 589,120 and
    58,748 bytes afterwards -- but the sealed copies they are compared against were, and the
    chain now carries links describing a fixture. It is the exact shape this project files as a
    fault: a probe that reaches live state, in the module whose subject is not losing history.

    THE FIX IS THE SHAPE, NOT THE TWO CALL SITES. Fixing only those two nets leaves the next one
    to remember three globals correctly. Redirection is now ONE operation over a named list, so a
    net cannot redirect a subset by accident, and a path added to `ledger_guard` later is a path
    this helper must be taught about -- which the assertion below makes loud rather than silent:
    every redirected value must end up under `root`, checked before the body runs.
    """
    import ledger_guard as _LG
    # EVERY path the module writes or reads as state. `ACKNOWLEDGED` joined this list the same
    # day it was added to ledger_guard (2026-09-02): a probe that seals fixtures and then writes
    # an acknowledgement for them would otherwise land that acknowledgement in the LIVE registry
    # -- and an acknowledgement is a waiver, so that is the worst file in the module to litter.
    names = ("HERE", "SNAPSHOT_DIR", "CHAIN", "ACKNOWLEDGED")
    keep = {n: getattr(_LG, n) for n in names}
    try:
        _LG.HERE = root
        _LG.SNAPSHOT_DIR = os.path.join(root, "state", "ledger_snapshot")
        _LG.CHAIN = os.path.join(root, "state", "ledger_chain.jsonl")
        _LG.ACKNOWLEDGED = os.path.join(root, "state", "ledger_chain_acknowledged.json")
        real = os.path.abspath(keep["HERE"])
        for n in names:
            got = os.path.abspath(getattr(_LG, n))
            if not got.startswith(os.path.abspath(root)) or got.startswith(real + os.sep):
                raise AssertionError("ledger_guard.%s still points into the live tree (%s) -- "
                                     "refusing to run a probe that would write there" % (n, got))
        yield
    finally:
        for n in names:
            setattr(_LG, n, keep[n])
        shutil.rmtree(root, ignore_errors=True)


def _quietly(fn):
    """Run a probe whose guard is SUPPOSED to shout on stderr, without the shout. -> fn's answer.

    The sibling of `_deliberately_failing`, for the other channel. Two paths in escalation.py --
    `_raise_halt` exhausting its attempts and `_land_halt` catching a throwing write -- are
    deliberately loud on stderr as well as in the ledger, because a halt that cannot be written
    is the worst case this project has. The nets that prove those paths refuse correctly have to
    trigger them, and a drill run that prints CANNOT WRITE HALT FILE twice while every net holds
    is a run whose own output argues against its verdict.

    Scoped to the single call under test, exactly as `_deliberately_failing` is, and asserting
    the RETURN VALUE rather than the absence of the message -- nothing under test is suppressed,
    only its echo in this process's terminal.
    """
    import contextlib
    import io as _io
    with contextlib.redirect_stderr(_io.StringIO()):
        return fn()


def _deliberately_failing(fn):
    """Run a probe whose WHOLE POINT is to make a guard record a failure -- without that record
    landing in the library's own failure ledger. -> fn's answer.

    THE LITTER THIS STOPS, measured on 2026-08-31. `state/failures.json` is the operational
    ledger: `standards` grades from it, `foreman.triage_swallowed()` names its classes and then
    archives and clears it, and a person reads those names to decide what is wrong with the
    library. Two nets in this file deliberately corrupt a blob and deliberately stage a stale
    write, both guards call `silence.note`, and `silence.note` calls `health.record` -- so EVERY
    DRILL RUN added one `silent:compress_store.py:address-mismatch` and one
    `silent:silence.py:cas-target-changed` to that ledger.

    The counts were 6 and 13 when this was found, and the first of them reads as CORPUS
    CORRUPTION: `compress_store.load()` refusing a blob whose content hash does not match the
    address it is filed under. Order 842025c83c3c cited exactly that class as its flagship
    example of a real fault being archived unspoken. It was this net's own probe. Confirmed by
    running `drill_recorders_and_lane` and watching both counters rise by exactly one, and by
    scanning every stored blob under output/ and data/ and finding no genuine mismatch at all.
    A drill of the whole tree currently contributes both entries per run.

    That is worse than noise. It is a probe manufacturing the exact signal it exists to prove
    the library can raise, in the file a person consults to find out whether the library has
    raised it -- so a REAL misaddressed blob would arrive indistinguishable from six copies of
    this rehearsal, in a ledger that gets cleared. It is the same discipline `_sweep_probe_litter`
    and `a_probe_leaves_no_order_behind` already enforce for the WORK ORDER queue, applied to
    the other ledger a probe can write to.

    SCOPED AS TIGHTLY AS POSSIBLE, on purpose: only the call that is SUPPOSED to fail is wrapped,
    so an unrelated fault raised during the same net is still recorded. The nets assert the
    RAISE, never the ledger entry, so nothing under test is being suppressed.
    """
    import health as _H
    real = _H.record
    _H.record = lambda *a, **k: None
    try:
        return fn()
    finally:
        _H.record = real


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


def _rows_in(path, token=None):
    """How many lines an append-only ledger holds right now. -> int (0 if it is not there yet).

    A probe that leaves the OPEN queue clean and quietly grows the PAPER TRAIL on every run is
    still littering; see `a_probe_leaves_no_order_behind`. Counting lines rather than parsing
    them is deliberate -- the question is only "did this file grow", and a row this probe cannot
    parse must not be able to answer it either way.

    `token` narrows the count to the rows that NAME something -- and it is what makes the
    question answerable on a live library at all (order 00f8ca4ab967). The whole-file count is
    a count of what EVERY detector in the kit wrote, so "did this file grow" is answered "yes"
    by any neighbour closing any order in the window, and a breached drill net escalates to
    OWNER. Asked with the probe's own reserved subsystem name, the count moves only when a row
    belonging to this probe appears, which is the thing the caller actually wants to know.
    Substring, not a parse: the caller's token is a reserved `__drill...__` marker that no
    ordinary row can contain, and a row too damaged to parse must still be able to say that it
    mentions one.
    """
    try:
        with open(path, encoding="utf-8") as fh:
            return sum(1 for line in fh if token is None or token in line)
    except OSError:
        return 0


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


# WHY THE NETS BELOW ASK THE PARSE TREE ANYTHING AT ALL. Three of them asked whether a WORD
# appeared in a source file and called that "the guard is wired". A word is not a call. The run
# #34 sweep defeated two on the spot: `"snapshot" in withdraw_chapters.py` is satisfied by the
# COMMENT sitting directly above the snapshot block, so the block could be deleted whole and the
# net would stay green on its own explanation; and `guards_are_wired_where_claimed` was
# satisfied by a `coverage.py` docstring, a `pipeline.py` comment and a `feats.py` comment block
# -- three of its six files could lose the import and every use while the net named "every guard
# is present in the file that claims it" went on holding. A literal cannot tell code from prose
# about code, and prose about a guard OUTLIVES the guard by design, because the person who
# deletes the call rarely deletes the paragraph explaining why it was there.
#
# `_called_names(path)` was the first answer to that and it lived here. It has gone the same way
# as `_calls` below and for the same reason (order 78f04bec15ad): file-wide is the wrong scope,
# and a convenience answering a weaker question than anybody wants is how the weaker question
# gets asked again. `_ast_of` + `_call_spellings` is the one line it was, and every caller now
# says which scope and which reachability it means.


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


def _src_py_files(src):
    """Every `.py` file under `src/`, subdirectories included. -> [(label, full path)].

    TWO NETS SAID "NO MODULE IN src/" AND MEANT "no module in the top level of src/" (order
    cf9ee9000be8, run #37). Both took `sorted(os.listdir(src))` and kept what ended in `.py`,
    and `src/deprecated/` exists and holds `catalogue_local.py`. The sweep proved the hole on
    `_no_programmatic_clear`: a scratch tree with a clean top level and a real, reachable
    `escalation.clear("<a ruling long enough to pass>")` in `src/deprecated/lifter.py` returned
    True -- "no module in src/ calls the halt's release", while a module in src/ called it.
    Latent rather than live (the real `catalogue_local.py` was read and calls nothing of the
    kind), but a deprecated directory is exactly where a lift would be least looked at.

    `__pycache__` is skipped because it holds no source. The label carries the relative path so
    a finding names the file a person has to open.
    """
    out = []
    for root, dirs, files in os.walk(src):
        dirs[:] = [d for d in dirs if d != "__pycache__"]
        for f in sorted(files):
            if f.endswith(".py"):
                full = os.path.join(root, f)
                out.append((os.path.relpath(full, src).replace(os.sep, "/"), full))
    return sorted(out)


def _defn(tree, name):
    """The `def` or `class` named `name`, at any nesting depth. None if there is not one."""
    import ast
    for n in ast.walk(tree):
        if (isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef))
                and n.name == name):
            return n
    return None


def _import_maps(tree):
    """(alias, from) for one module. `import x as y` -> alias[y]=x; `from m import f` -> frm[f]=m.f."""
    import ast
    alias, frm = {}, {}
    for n in ast.walk(tree):
        if isinstance(n, ast.Import):
            for al in n.names:
                alias[al.asname or al.name.split(".")[0]] = al.name
        elif isinstance(n, ast.ImportFrom) and n.module:
            for al in n.names:
                frm[al.asname or al.name] = "%s.%s" % (n.module, al.name)
    return alias, frm


def _spellings_of_call(tree, call, maps=None):
    """The spellings of the CALLABLE in one call node -- not of the calls nested in its args.

    `_call_spellings` answers "does this subtree call X anywhere in it", which is the wrong
    question when the claim is "THIS assignment carries the result of X": `x = f(g())` calls
    both and binds only one. Every dataflow check below needs the narrow answer.
    """
    import ast
    alias, frm = maps if maps is not None else _import_maps(tree)
    out, fn = set(), call.func
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


def _name_spellings(tree, node, maps=None):
    """The spellings of one NAME or ATTRIBUTE expression, resolved through this file's imports.

    The value-side counterpart of `_spellings_of_call`, and it exists for the same reason order
    7cc460706efe filed against two nets pinned to an import ALIAS: `_ESC.SAFETY`, `ESC.SAFETY`
    and a bare `SAFETY` from `from escalation import SAFETY` are one constant under three
    spellings, and a net that recognises one of them refuses correct code that uses another --
    which, in this file, HALTS THE LIBRARY. Asking for `escalation.SAFETY` gets all three.
    """
    import ast
    alias, frm = maps if maps is not None else _import_maps(tree)
    out = set()
    if isinstance(node, ast.Name):
        out.add(node.id)
        if node.id in frm:
            out.add(frm[node.id])
    elif isinstance(node, ast.Attribute):
        out.add(node.attr)
        if isinstance(node.value, ast.Name):
            out.add("%s.%s" % (node.value.id, node.attr))
            if node.value.id in alias:
                out.add("%s.%s" % (alias[node.value.id], node.attr))
    return out


def _static_truth(test):
    """True/False for a test the parser can already decide; None for a real condition.

    `and False` / `or True` are handled as well as a bare constant, because "wrap the live
    branch in something that reads as a condition" is the first thing anybody tries when a net
    starts refusing `if False:`. `not <constant>` likewise.
    """
    import ast
    if isinstance(test, ast.Constant):
        return bool(test.value)
    if isinstance(test, ast.UnaryOp) and isinstance(test.op, ast.Not):
        inner = _static_truth(test.operand)
        return None if inner is None else (not inner)
    if isinstance(test, ast.BoolOp):
        kinds = [_static_truth(v) for v in test.values]
        if isinstance(test.op, ast.And) and False in kinds:
            return False
        if isinstance(test.op, ast.Or) and True in kinds:
            return True
    return None


def _breaks_out_of(loop):
    """Can this loop's OWN body reach a `break` that leaves it? -> bool.

    Asked only of a loop whose test the parser has already decided is True, where the answer
    settles whether the statements after the loop are reachable at all. Two exclusions carry the
    whole meaning of "its own":

      * a `break` inside a NESTED `for`/`while` leaves THAT loop and comes straight back to this
        one -- the same distinction `_arm_leaves` was corrected for at order 515eb8cae3c2, where
        four guard nets accepted an inner loop's `continue` as the outer arm leaving;
      * a `break` inside a nested `def`, `lambda` or `class` is not this loop's at all, and is a
        `SyntaxError` in real code besides.

    Every statement list is filtered through `_live_stmts` on the way down, so a `break` parked
    after a `return` or inside an `if False:` does not count as a way out -- a loop that can only
    be left by dead code is a loop nobody leaves.
    """
    import ast
    stack = list(_live_stmts(loop.body))
    while stack:
        n = stack.pop()
        if isinstance(n, ast.Break):
            return True
        if isinstance(n, (ast.For, ast.AsyncFor, ast.While, ast.FunctionDef,
                          ast.AsyncFunctionDef, ast.ClassDef, ast.Lambda)):
            continue
        for field, value in ast.iter_fields(n):
            if isinstance(value, list):
                items = value
                if (field in ("body", "orelse", "finalbody") and value
                        and all(isinstance(x, ast.stmt) for x in value)):
                    items = _live_stmts(value)
                stack.extend(x for x in items if isinstance(x, ast.AST))
            elif isinstance(value, ast.AST):
                stack.append(value)
    return False


def _live_stmts(body):
    """The statements of ONE block that execution can actually reach. -> list.

    WHY THIS EXISTS, and it is the run #36 sweep's sharpest finding. Every parse-tree net in
    this file walked whole `If` nodes with `ast.walk`, which visits the taken arm, the untaken
    arm and **unreachable code** without distinguishing any of them. The sweep beat
    `_halt_is_not_breakage` with a fixture whose real behaviour always declared the library
    broken and never checked the halt at all, carrying the tokens the net wanted in a dead
    `if False:` block placed AFTER a `break`. The net reported HELD. Dead code is prose that
    happens to parse: it makes exactly the same claim a comment does and it is exactly as
    binding on the running program, which is not at all.

    So: statements after an unconditional `return`/`raise`/`break`/`continue` are dropped, an
    `if False:` contributes only its `else`, and an `if True:` contributes only its body.

    AND A `while` CARRIES AN `else` TOO, WHICH THIS GOT BACKWARDS IN BOTH DIRECTIONS
    (sweep43-batch01). Python runs a loop's `else` when the loop ends WITHOUT a `break`:

      * `while False:` never enters the body and therefore terminates without breaking, so its
        `else` RUNS IMMEDIATELY. This dropped the whole statement -- `inner = []` -- and read
        that live code as dead. A net asking "is the call made" would answer no about a call
        that is made, i.e. a false BREACH.
      * `while True:` can only leave through `break`, `return` or `raise`, and all three SKIP
        the `else`. That arm fell through to `inner = None`, the node was appended whole, and
        `_live_walk` then descended into the `orelse` like any other block -- reading provably
        dead code as reachable. That is the direction this whole function exists to prevent,
        and it is the one that makes a net report HELD on a fixture that never runs the code.

    The `while True:` ELSE is fixed in `_live_walk`, not here, because the loop body still has
    to be walked normally and only the `else` is unreachable. Verified 2026-09-03 that no
    `while ... else:` exists anywhere in `src/`, so no net was giving a wrong verdict on today's
    tree -- this is a latent defect in shared infrastructure, repaired before it is depended on.

    AND THE SAME LOOP HAS A FALL-THROUGH AS WELL AS AN ELSE, WHICH THAT REPAIR LEFT BEHIND
    (order 7baa1527f69c). A `while True:` whose body cannot reach a `break` never terminates, so
    every statement AFTER it in the same block is as dead as an `if False:` arm -- and those were
    still being appended and fed to every net built on `_live_walk`. Measured on the order's own
    fixture: for `def f(): while True: the_real_behaviour()` followed by
    `the_guard_that_can_never_run()`, `_live_walk` returned BOTH names, so a fixture whose real
    behaviour loops forever and whose guard is parked underneath it read as a fixture that calls
    the guard. That is the direction this whole function exists to prevent, arriving through the
    loop's fall-through instead of its else, and it is the direction that makes a net report HELD
    on code that never runs.

    A `return` or a `raise` inside the loop does NOT reopen the block below it -- both leave the
    function entirely -- so `break` is the only way past, which is why `_breaks_out_of` asks about
    exactly that and about nothing else. Verified 2026-09-07 that `src/` holds nine such loops and
    NOT ONE of them is followed by a statement, so no net changed its verdict on today's tree:
    latent, and repaired before it is depended on, exactly as the `else` half was.
    """
    import ast
    out = []
    for s in body:
        inner = None
        if isinstance(s, (ast.If, ast.While)):
            k = _static_truth(s.test)
            if k is False:
                # Both spellings run the `else` and neither runs the body.
                inner = _live_stmts(s.orelse)
            elif k is True and isinstance(s, ast.If):
                inner = _live_stmts(s.body)
        if inner is None:
            out.append(s)
            if isinstance(s, (ast.Return, ast.Raise, ast.Break, ast.Continue)):
                break
            # A LOOP NOBODY CAN LEAVE ENDS THE BLOCK, like a `return` does. The node is still
            # appended -- the body is real code and every net has to see it -- but nothing after
            # it is reachable.
            if (isinstance(s, ast.While) and _static_truth(s.test) is True
                    and not _breaks_out_of(s)):
                break
        else:
            out.extend(inner)
            if any(isinstance(x, (ast.Return, ast.Raise, ast.Break, ast.Continue))
                   for x in inner):
                break
    return out


def _live_walk(node):
    """`ast.walk` restricted to code that can actually be REACHED from `node`. -> list.

    The reachable counterpart of `ast.walk`, and the instrument every net below that says "the
    call is made" rather than "the name appears" is built on. Every statement list is filtered
    through `_live_stmts` on the way down, so a dead branch never contributes a Call node, a
    Continue node or a string literal to any answer.
    """
    import ast
    out, stack = [], [node]
    while stack:
        n = stack.pop()
        out.append(n)
        for field, value in ast.iter_fields(n):
            if isinstance(value, list):
                items = value
                if (field in ("body", "orelse", "finalbody") and value
                        and all(isinstance(x, ast.stmt) for x in value)):
                    # THE `else` OF A `while True:` IS UNREACHABLE, and it is the one block
                    # `_live_stmts` cannot drop on its own -- the loop body still has to be
                    # walked, so the node is appended whole and its fields are descended here.
                    # A loop's `else` runs only when the loop ends WITHOUT a break, and a
                    # `while True:` can end only by `break`, `return` or `raise`, every one of
                    # which skips it. Left alone, this fed dead code to every net built on
                    # `_live_walk` -- the exact fault the `if False:` handling exists to stop,
                    # arriving through the loop spelling. (sweep43-batch01)
                    if (field == "orelse" and isinstance(n, ast.While)
                            and _static_truth(n.test) is True):
                        continue
                    items = _live_stmts(value)
                for x in items:
                    if isinstance(x, ast.AST):
                        stack.append(x)
            elif isinstance(value, ast.AST):
                stack.append(value)
    return out


def _live_stmt_walk(stmts):
    """`_live_walk` over a list of statements. -> list of nodes."""
    return [x for s in stmts for x in _live_walk(s)]


def _arm_leaves(body, exits):
    """Does this branch's OWN body leave by one of `exits`? -> bool.

    THE QUESTION EVERY GUARD NET IS ACTUALLY ASKING, and four of them were asking a looser one
    (order 515eb8cae3c2). They walked the whole arm with `_live_stmt_walk` and accepted any
    `Continue` node anywhere inside it -- so a `continue` belonging to a NESTED loop counted as
    the arm leaving. Proved with a fixture whose only `continue` sits in an inner `for` and
    which spawns unconditionally afterwards: the inner loop swallows the `continue`, the arm
    falls through, and the launch the guard was supposed to skip happens anyway. The net said
    the guard was wired.

    So an exit is credited only to the block that OWNS it:

      * `Continue`/`Break` belong to the innermost enclosing loop, so one inside a `for`/`while`
        nested in the arm does not leave the arm;
      * `Return` belongs to the innermost enclosing function, and a nested `def` is not executed
        where it is written, so nothing inside one counts at all;
      * `Raise` propagates out of every loop, so it leaves from wherever it stands.

    Reachability is handled here rather than by the caller: every statement list on the way down
    goes through `_live_stmts`, so a `continue` parked after a `return` is not an exit either.
    """
    import ast

    def scan(stmts, in_loop):
        for s in _live_stmts(stmts):
            if isinstance(s, exits) and not (isinstance(s, (ast.Continue, ast.Break))
                                             and in_loop):
                return True
            if isinstance(s, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                continue                       # a definition does not run where it is written
            loop = isinstance(s, (ast.For, ast.AsyncFor, ast.While))
            for field in ("body", "orelse", "finalbody"):
                block = getattr(s, field, None)
                # A loop's `else` is outside the loop for `continue`/`break` purposes: an exit
                # there binds to whatever loop encloses the whole statement, not to this one.
                if block and scan(block, in_loop or (loop and field == "body")):
                    return True
            for h in getattr(s, "handlers", ()) or ():
                if scan(h.body, in_loop):
                    return True
        return False

    return scan(body, False)


def _call_spellings(tree, node=None, reachable=False):
    """Every call spelling inside `node` (default: the whole module), resolved through the
    module's imports.

    Split out of `_called_names` (HISTORY -- that helper was deleted by order 78f04bec15ad and
    nothing here is offering it) so a net can ask the question of ONE FUNCTION rather than of a
    whole file: "the escalation happens in the failure branch" and "the file mentions escalate
    somewhere" are different claims, and the nets that used a text window around an anchor
    string were reaching for the first while only ever testing the second.

    `reachable=True` narrows it one step further, to calls the running program can actually
    make: see `_live_stmts` for the dead-code fixture that made that distinction necessary.
    """
    import ast
    maps = _import_maps(tree)
    root = node if node is not None else tree
    nodes = _live_walk(root) if reachable else ast.walk(root)
    out = set()
    for n in nodes:
        if isinstance(n, ast.Call):
            out |= _spellings_of_call(tree, n, maps)
    return out


# `_calls(path, want)` USED TO LIVE HERE, and every net in this file that says "the guard is
# wired" was built on it. It answered "the name appears at a call site somewhere in this file",
# which walks dead code, untaken branches and functions nothing calls -- and the run #37 sweep
# defeated FOUR nets on that in one pass (order 78f04bec15ad): each fixture did the forbidden
# thing on the live path and parked the required call after a `return` or inside an `if False:`,
# and all four reported HELD. Relocating a guard into a branch nothing enters deletes it as
# thoroughly as removing it and leaves a better-looking diff.
#
# All four now ask `_reaches_call` instead, so there is no caller left and the helper is gone
# rather than kept "in case": a convenience that answers a weaker question than the one anybody
# wants is how the weaker question gets asked again next quarter.
#
# SO THE THREE DEGREES AVAILABLE TODAY, NAMED, because this paragraph is where a reader lands
# when they want to know which one to reach for. Weakest to strongest:
#   * `_call_spellings(tree, node)` -- the name is called somewhere in this subtree, dead code
#     included. Almost never the question anybody means.
#   * `_call_spellings(tree, node, reachable=True)` (and `_calls_within(..., reachable=True)`,
#     its boolean form) -- the honest MIDDLE form: the call is on a path execution can enter.
#     An uncalled helper still satisfies it, which is why it is the middle and not the top.
#   * `_reaches_call(tree, want, entries)` -- the strict one: the running program can get there
#     from a named entry point. This is what every "the guard is wired" net now asks.
# `_spelled` is unchanged.
#
# THIS BLOCK USED TO OFFER `_called_names(path, reachable=True)` HERE as the middle form, in the
# present tense, two lines under the paragraph explaining that `_called_names` had been deleted
# (order e75b265c1d3c). There is no such helper and there has not been one for a shift; a reader
# taking the offer would have had to re-invent it, and the shape they would most likely have
# reached for is the file-wide one this very paragraph says was removed for being too weak. The
# two remaining mentions of the old names -- at `_call_spellings` ("Split out of `_called_names`")
# and at `_calls_within` ("the scoped form of `_calls`") -- are HISTORY and are marked as such
# where they sit; this one made a present-tense claim, which is the difference that mattered.


def _entry_nodes(tree, names):
    """The places the running program STARTS: module top level, plus the named defs. -> list.

    The module entry deliberately excludes the `def`/`class` bodies at top level, because those
    are what `names` is for; a bare `_live_walk(tree)` would walk into every function in the
    file whether or not anything calls it, which is the hole `_reaches_call` exists to close.
    """
    import ast
    top = [s for s in _live_stmts(tree.body)
           if not isinstance(s, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef))]
    out = [ast.Module(body=top, type_ignores=[])]
    for n in names:
        d = _defn(tree, n)
        if d is not None:
            out.append(d)
    return out


def _live_calls_from(tree, entries=("main",)):
    """Every call spelling the running program can REACH from `entries`. -> set.

    THE THIRD DEGREE OF "IS THIS GUARD WIRED", and the one order 78f04bec15ad asked for.
    `_calls` answers "the name appears at a call site somewhere in the file", which dead code
    satisfies. `_calls(..., reachable=True)` answers "on a path that can be entered", which an
    UNCALLED HELPER still satisfies -- `_live_walk` descends into every `def` in the file, so
    parking the required call in a function nothing calls reads exactly like wiring it. This
    follows the call graph instead: start at the module's top level and its named entry points,
    take the reachable calls of each, and descend into any of them that names a function defined
    in this same module. A helper nothing calls is never entered and so never answers.

    Deliberately intraprocedural-only and deliberately name-based: it proves REACHED, and a
    negative means "not reached from here", which is why every net using it names an entry point
    the module genuinely has rather than guessing one.
    """
    import ast
    defs = {n.name: n for n in ast.walk(tree)
            if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))}
    out, todo, done = set(), list(_entry_nodes(tree, entries)), set()
    while todo:
        node = todo.pop()
        if id(node) in done:
            continue
        done.add(id(node))
        spellings = _call_spellings(tree, node, reachable=True)
        out |= spellings
        for s in spellings:
            d = defs.get(s)
            if d is not None and id(d) not in done:
                todo.append(d)
    return out


def _reaches_call(tree, want, entries=("main",)):
    """Can the running program reach a call to `want` from `entries`? -> bool."""
    return _spelled(_live_calls_from(tree, entries), want)


def _spelled(got, want):
    """Is `want` among these call spellings? A trailing dot asks for any call on that module."""
    if want.endswith("."):
        return any(c.startswith(want) for c in got)
    return want in got


def _calls_within(tree, node, want, reachable=False):
    """Does the subtree `node` CALL `want`? The scoped form of `_calls` (HISTORY -- `_calls`
    itself was deleted by order 78f04bec15ad; see the block above `_entry_nodes`).

    `reachable=True` asks the stricter question -- can the running program make that call --
    which is the difference between a wired guard and one sitting in a dead branch.
    """
    return _spelled(_call_spellings(tree, node, reachable=reachable), want)


def _bound_from_call(tree, node, want, reachable=True):
    """Every name inside `node` that CARRIES THE RESULT of a call to `want`. -> set.

    `_busy, _rec = _MUT.active()` -> `{"_busy", "_rec"}`, and `h = _ESC.status()[0]` -> `{"h"}`.

    WHY A NET NEEDS THIS. `publish_asks_before_pushing` proved that "the module is imported"
    and "the refusal string is present" can both be true of a `push()` with no interlock at
    all -- the sweep passed a fixture carrying zero interlock logic. What makes an interlock an
    interlock is that the ANSWER reaches the branch: the value the guard computed has to be the
    value the refusal is conditioned on. Names are how that link is visible in a parse tree.
    """
    import ast
    maps = _import_maps(tree)
    out = set()
    for n in (_live_walk(node) if reachable else ast.walk(node)):
        if not isinstance(n, (ast.Assign, ast.AnnAssign)):
            continue
        v = n.value
        while isinstance(v, (ast.Subscript, ast.Attribute)):   # f()[0], f().x
            v = v.value
        if not (isinstance(v, ast.Call) and _spelled(_spellings_of_call(tree, v, maps), want)):
            continue
        targets = n.targets if isinstance(n, ast.Assign) else [n.target]
        for t in targets:
            for e in ast.walk(t):
                if isinstance(e, ast.Name):
                    out.add(e.id)
    return out


def _carries_result_of(tree, node, want, reachable=True):
    """Every name in `node` carrying a call to `want`'s result, DIRECTLY OR THROUGH A CONTAINER.

    -> set. A superset of `_bound_from_call`, and the reason it had to exist is that
    `_bound_from_call` only sees `x = want()`. A guard is free to hold its readings in a list,
    a tuple or a dict and unpack them in a loop, which is what `publish.push` does now that it
    takes TWO readings of `mutate.active()` (order d56228616f9c): `readings = [("at push time",
    _MUT.active())]` then `for _when, (_busy, _rec) in readings:`. Not one name there is bound
    directly to the call, so `_bound_from_call` returned an empty set and the net that asks
    "does the ANSWER reach the branch" reported BREACHED against a stronger interlock than the
    one it was written for. A net that goes red when a guard is improved teaches people to
    stop improving guards.

    IT IS STILL A DATA-DEPENDENCE TEST, not a widening into "any name in the function". A name
    enters the set only by being bound from an expression that either CALLS `want` or mentions a
    name already in the set, so a body with no call to `want` in it yields nothing at all and a
    fixture carrying no interlock logic still cannot satisfy a net built on this.
    """
    import ast
    maps = _import_maps(tree)
    nodes = _live_walk(node) if reachable else list(ast.walk(node))

    def _calls_want(sub):
        return any(isinstance(x, ast.Call) and _spelled(_spellings_of_call(tree, x, maps), want)
                   for x in ast.walk(sub))

    out = set()
    for _ in range(8):        # a fixpoint; real chains here are one or two links long
        grew = False
        for n in nodes:
            if isinstance(n, (ast.Assign, ast.AnnAssign)):
                src = n.value
                targets = n.targets if isinstance(n, ast.Assign) else [n.target]
            elif isinstance(n, (ast.For, ast.AsyncFor)):
                src, targets = n.iter, [n.target]
            elif isinstance(n, ast.withitem):
                src = n.context_expr
                targets = [n.optional_vars] if n.optional_vars else []
            else:
                continue
            if src is None or not targets:
                continue
            if not (_calls_want(src)
                    or any(isinstance(x, ast.Name) and x.id in out for x in ast.walk(src))):
                continue
            for t in targets:
                for e in ast.walk(t):
                    if isinstance(e, ast.Name) and e.id not in out:
                        out.add(e.id)
                        grew = True
        if not grew:
            break
    return out


def _guarded_by(tree, if_node, names, want=None):
    """Is this `if` conditioned on one of `names` (or on a direct call to `want`)? -> bool."""
    import ast
    t = if_node.test
    if any(isinstance(x, ast.Name) and x.id in names for x in ast.walk(t)):
        return True
    if want is None:
        return False
    maps = _import_maps(tree)
    return any(isinstance(x, ast.Call) and _spelled(_spellings_of_call(tree, x, maps), want)
               for x in ast.walk(t))


def _gate_precedes_spawn(tree, fn, gate, spawn, exits):
    """Does `fn` ask `gate`, BIND the answer, and skip `spawn` on it? -> bool.

    The three-part claim `the_keeper_asks_before_restarting` makes about `_keep`, lifted out so
    the other launchers can be asked the same question in the same words (order e0948238ef36).
    A guard is an interlock only when all three hold at once, and each of the three is a
    separate way the same net has already been beaten:

      * the answer is BOUND -- `_manager_stopped(name, args)` called and thrown away reads
        identically to a consultation and stops nothing;
      * a REACHABLE `if` conditioned on that bound answer leaves by one of `exits` without
        reaching a spawn -- a guard that does not skip the launch is not a guard, and order
        07c7379597ba beat the line-number form with a consultation in an unrelated arm;
      * every reachable spawn sits OUTSIDE that arm and after it -- a launch the guard cannot
        precede is not gated by it.

    `exits` is a tuple of node types because the two shapes leave differently and both are
    correct: the keeper `continue`s to the next standing job, `start`/`run` `return` a
    did-not-start value to their caller.
    """
    import ast
    if fn is None:
        return False
    answered = _bound_from_call(tree, fn, gate)
    if not answered:
        return False                            # not asked, or asked and the answer discarded
    maps = _import_maps(tree)
    spawns = [n for n in _live_walk(fn)
              if isinstance(n, ast.Call) and _spelled(_spellings_of_call(tree, n, maps), spawn)]
    if not spawns:
        return False                            # a launcher that launches nothing proves nothing
    for g in _live_walk(fn):
        if not isinstance(g, ast.If) or not _guarded_by(tree, g, answered):
            continue
        arm = _live_stmt_walk(_live_stmts(g.body))
        if not _arm_leaves(g.body, exits):
            continue                            # the stopped arm must LEAVE, not fall through
        if any(x is s for x in arm for s in spawns):
            continue                            # ... and must not launch what it just refused
        inside = {id(x) for x in _live_walk(g)}
        if all(id(s) not in inside and s.lineno > g.lineno for s in spawns):
            return True
    return False


def _code_strings(node, reachable=False):
    """Every string literal in `node` that is CODE, not PROSE ABOUT CODE.

    Docstrings and floating string blocks are dropped; comments are not in a parse tree at all,
    which is the entire reason these checks moved off the file text. A marker a module raises,
    prints or stores is a fact about what it does. The same words in the paragraph above it are
    a fact about what somebody meant, and prose about a guard reliably OUTLIVES the guard --
    whoever deletes the call rarely deletes the explanation. The two must stop counting as the
    same evidence.
    """
    import ast
    nodes = _live_walk(node) if reachable else list(ast.walk(node))
    prose = set()
    for n in nodes:
        if (isinstance(n, ast.Expr) and isinstance(n.value, ast.Constant)
                and isinstance(n.value.value, str)):
            prose.add(id(n.value))
    return {n.value for n in nodes
            if isinstance(n, ast.Constant) and isinstance(n.value, str) and id(n) not in prose}


def _says(node, fragment, reachable=False):
    """Does any CODE string in `node` contain `fragment`? Docstrings and comments do not count.

    `reachable=True` also refuses a string sitting in a branch nothing can enter -- dead code
    that carries the right words is the same evidence a comment is, which is none.
    """
    return any(fragment in s for s in _code_strings(node, reachable=reachable))


def _subscript_assigns(node, obj, key, reachable=False):
    """Every `ast.Assign` in `node` of the shape `obj[key] = ...`. -> list of Assign nodes.

    `reachable=True` drops the ones the running program cannot execute. Order c54a22a4e6fc beat
    `_run_marks_a_landless_run_failed` with a `run()` that returns `{"ok": True, "patches": []}`
    and carries `out["ok"] = False` on the line AFTER that return -- an assignment that exists
    exactly as much as a comment does.
    """
    import ast
    out = []
    for n in (_live_walk(node) if reachable else ast.walk(node)):
        if not isinstance(n, ast.Assign):
            continue
        for t in n.targets:
            if (isinstance(t, ast.Subscript) and isinstance(t.value, ast.Name)
                    and t.value.id == obj and isinstance(t.slice, ast.Constant)
                    and t.slice.value == key):
                out.append(n)
    return out


# Free functions whose PATH is the argument at the mapped index.
_WRITE_CALLS = {"_write": 0, "os.remove": 0,
                "os.unlink": 0, "shutil.rmtree": 0, "shutil.copy": 1, "shutil.copy2": 1,
                "shutil.copyfile": 1, "shutil.move": 1, "os.replace": 1, "os.rename": 1}

# pathlib METHODS, whose path is the RECEIVER and is not an argument at all. They sat in the
# table above at index 0, beside the free functions, which is how they came to be filed there --
# but in `p.write_text(body)` argument 0 is the BODY, so `_write_targets` handed back the
# CONTENT expression as though it were the path, and `mutation_never_touches_the_live_tree`
# would have been reasoning about the wrong node. The error runs toward a FALSE owner halt, not
# a missed one, and it is latent: `mutate.py` writes through its own `_write(path, data)`, where
# index 0 really is the path, so nothing was wrong on today's tree. It was wrong for the day
# somebody reached for pathlib. (order d1b2247ff350)
_WRITE_METHODS = ("write_bytes", "write_text")


def _write_targets(tree, node):
    """Every REACHABLE call in `node` that opens or replaces a file. -> [(call, path expr)].

    `open(p, "w")` and friends, plus the small set of module helpers and shutil/os spellings
    this project actually writes through. A mode with no `w`/`a`/`x`/`+` in it is a read and is
    not collected -- `_read`'s `open(path, "rb")` must not count as touching anything.

    Two tables, because two shapes: `_WRITE_CALLS` holds free functions whose path is an
    ARGUMENT, `_WRITE_METHODS` the pathlib methods whose path is the RECEIVER. See the note
    above `_WRITE_METHODS` for what filing the second kind in the first table did.
    """
    import ast
    maps = _import_maps(tree)
    out = []
    for n in _live_walk(node):
        if not isinstance(n, ast.Call):
            continue
        if isinstance(n.func, ast.Attribute) and n.func.attr in _WRITE_METHODS:
            out.append((n, n.func.value))      # `p.write_text(body)` -- the path is `p`
            continue
        if not n.args:
            continue
        spellings = _spellings_of_call(tree, n, maps)
        for want, idx in _WRITE_CALLS.items():
            if _spelled(spellings, want) and len(n.args) > idx:
                out.append((n, n.args[idx]))
                break
        else:
            if "open" in spellings:
                mode = n.args[1] if len(n.args) > 1 else None
                for kw in n.keywords:
                    if kw.arg == "mode":
                        mode = kw.value
                m = mode.value if isinstance(mode, ast.Constant) else ""
                if isinstance(m, str) and any(c in m for c in "wax+"):
                    out.append((n, n.args[0]))
    return out


def _filtered_names(node, seed):
    """Names in REACHABLE code under `node` carrying a value derived from one of `seed`. -> set.

    The general form of `_rooted_names` below, which tracks a filesystem path from one call;
    this tracks a WORK LIST through the ordinary shapes a work list travels in -- an assignment
    mentioning it, a comprehension over it, a `for` target, and `x.append(<derived>)`, which is
    how a list gets built one row at a time and which no assignment-only walk sees.

    WHY A NET NEEDS IT. `generator_actually_skips_an_excluded_source` had to answer "did the
    thing that queues jobs get the FILTERED list, or a copy taken before the filter", and the
    list is five derivations away from the comprehension that filters it -- roll -> populated ->
    assigned/unassigned -> build_pool -> the loop variable. Asking only whether SOME
    comprehension somewhere reads the exclusions is answered by a filter whose result is never
    used, which is the five-day fault that net is named after, wearing one more layer.

    Deliberately generous: anything MENTIONING a derived name is derived. A generous
    over-approximation makes this net miss a contrived case; a tight one makes it BREACH over a
    refactor, and a breach here halts the library.
    """
    import ast
    clean, nodes, grew = set(seed), _live_walk(node), True

    def _mentions(e):
        return any(isinstance(x, ast.Name) and x.id in clean for x in ast.walk(e))

    while grew:
        grew = False
        for n in nodes:
            targets = ()
            if isinstance(n, (ast.Assign, ast.AugAssign)) and _mentions(n.value):
                targets = n.targets if isinstance(n, ast.Assign) else [n.target]
            elif isinstance(n, (ast.For, ast.AsyncFor)) and _mentions(n.iter):
                targets = [n.target]
            elif isinstance(n, ast.comprehension) and _mentions(n.iter):
                targets = [n.target]
            elif (isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute)
                  and n.func.attr in ("append", "extend", "add", "update")
                  and any(_mentions(a) for a in n.args)):
                targets = [n.func.value]
            for t in targets:
                for e in ast.walk(t):
                    if isinstance(e, ast.Name) and e.id not in clean:
                        clean.add(e.id)
                        grew = True
    return clean


def _rooted_names(tree, node, seed):
    """Names in `node` holding a path built from a call to `seed`. -> set.

    `root = root or sandbox()` then `path = os.path.join(root, "src", target)` gives
    `{"root", "path"}`. Propagation is deliberately narrow -- a bare alias, a `join`, or a
    `or`/conditional around the seed call -- so that reading a FILE through a rooted path does
    not make the file's CONTENTS count as rooted too.
    """
    import ast
    maps = _import_maps(tree)
    derived, changed = set(), True
    while changed:
        changed = False
        for n in _live_walk(node):
            if not isinstance(n, ast.Assign):
                continue
            names = {e.id for t in n.targets for e in ast.walk(t) if isinstance(e, ast.Name)}
            if not names or names <= derived:
                continue
            v = n.value
            hit = False
            if isinstance(v, (ast.BoolOp, ast.IfExp)) or (
                    isinstance(v, ast.Call)
                    and _spelled(_spellings_of_call(tree, v, maps), seed)):
                hit = any(isinstance(c, ast.Call)
                          and _spelled(_spellings_of_call(tree, c, maps), seed)
                          for c in ast.walk(v))
            if not hit and _is_rooted(tree, v, derived, maps):
                hit = True
            if hit:
                derived |= names
                changed = True
    return derived


def _is_rooted(tree, expr, derived, maps=None):
    """Is this expression a path anchored at one of `derived`? -> bool.

    A bare `path`, any `join(...)` carrying one -- `os.path.join(root, ...)` is the spelling
    this project writes -- or either wrapped in `or`/a conditional. A literal, an unrelated
    name, or a join off some other root is NOT rooted, which is the whole question a net asks
    when it wants to know whether a write landed in the sandbox.

    THERE USED TO BE AN `os.path.join` BRANCH ABOVE THE `join` ONE AND IT COULD NEVER FIRE
    (order 3c4b04b4b463). `_spellings_of_call` builds a dotted spelling only when the callee's
    receiver is a bare `Name`, and in `os.path.join(...)` the receiver is `os.path`, an
    `Attribute` -- so the only spelling that call ever produced was the bare `join`, and the
    branch below it was doing all the work for both. Dead code that reads as a check is the
    shape this whole file exists against, so the dead branch is gone and the live one says what
    it accepts.

    WHAT IT NO LONGER ACCEPTS. A bare `join` matched `",".join(root)` as readily as a path
    build, so a SENTENCE assembled out of a rooted name read as a place inside the sandbox. A
    string literal in the receiver position is the SEPARATOR; when it holds no path separator
    the answer is text, not a location. `os.sep.join`, `"/".join` and any join this module
    cannot resolve are all still read as path builds, which keeps the accepting direction the
    two branches had between them -- the narrowing is exactly the case that was never a path.
    """
    import ast
    maps = maps if maps is not None else _import_maps(tree)
    if isinstance(expr, ast.Name):
        return expr.id in derived
    if isinstance(expr, (ast.BoolOp, ast.IfExp)):
        kids = expr.values if isinstance(expr, ast.BoolOp) else [expr.body, expr.orelse]
        return any(_is_rooted(tree, k, derived, maps) for k in kids)
    if isinstance(expr, ast.Call) and _spelled(_spellings_of_call(tree, expr, maps), "join"):
        recv = expr.func.value if isinstance(expr.func, ast.Attribute) else None
        if (isinstance(recv, ast.Constant) and isinstance(recv.value, str)
                and not any(c in recv.value for c in "/\\")):
            return False                       # `",".join(...)` is text, not a place
        return any(_is_rooted(tree, a, derived, maps) for a in expr.args)
    return False


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
    net(a, "the answer is about the source that was ASKED for",
        _coverage_answers_about_the_source_it_was_asked,
        "order b27b9c2e5935, and this exact corruption reached a public repo once already: "
        "with `and` flipped to `or` the row test matches the FIRST dict in COVERAGE.json "
        "whatever source it describes, so an unread source inherits a read one's citations")


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


def _coverage_answers_about_the_source_it_was_asked():
    """`cited_fraction` must report on the source NAMED, not on whichever row came first.

    THIS EXACT CORRUPTION HAS SHIPPED. On 2026-08-25 a `publish.py --loop` daemon pushed a
    mutated `prose_gate.py` to a public repo in which `cited_fraction()` matched every source
    EXCEPT the one it was asked about; the same one-token change survived the whole battery
    again in batch C01 (order b27b9c2e5935, `isinstance(r, dict) and r.get("source") == source`
    -> `or`). Nothing above could see it: every net in this area either asks about a source that
    is the ONLY row, or asks against an EMPTY rows list -- and with an empty list the loop body
    never runs at all, so `and` and `or` are indistinguishable there by construction.

    The attack that separates them is the one the incident was: an unmeasured source asked
    against a NON-empty COVERAGE.json. Both halves are asserted, because a lookup that always
    returns the first row would satisfy the second half alone.
    """
    rows = [{"source": "READ", "entries": 10, "cited": 10},
            {"source": "UNREAD", "entries": 10, "cited": 2}]
    if PG.cited_fraction("UNREAD", rows) != 0.2:
        return False                       # answered about a different row than the one asked
    if PG.cited_fraction("__never catalogued__", rows) is not None:
        return False                       # a source nobody has measured came back measured
    return not PG.evidence_ok("__never catalogued__", 0.35, rows)[0]


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
    # THE STEP 4 GATE — RATIFIED AND OPEN SINCE 2026-08-31, by a recorded owner ruling.
    # This row asserted the gate was CLOSED, which was correct for as long as the plan was
    # unratified and is why it breached the moment the owner opened it. That breach was
    # the system working: the flag is the second most consequential value in the
    # repository and nothing may move it without a net going red.
    #
    # It is REPOINTED, not removed and not relaxed -- the gate is still pinned to an exact
    # state, so a silent CLOSE is now caught exactly as loudly as a silent open was. The
    # three sibling rows below (stringy flag, missing plan, assert_step4_open) are
    # untouched: they test HOW the gate decides, which the ruling does not change.
    #
    # SCOPE: STEP4_PLAN.md §7E authorises Phase 4.0 and 4.1 ONLY. `prose_enabled` is a
    # separate flag, is untouched, and the row four lines above still pins it CLOSED.
    net(a, "the Step 4 gate stands where the owner ruled it -- OPEN since 2026-08-31",
        lambda: PG.step4_gate_open()[0],
        "the owner ruled the plan ratified after Phase 4.0 measured closed; if this goes "
        "red, find the ruling that closed the gate, and if there is none then something "
        "that is not a person moved it")
    net(a, "the Step 4 gate refuses a stringy flag too",
        lambda: not PG.step4_gate_open({"step4_enabled": "true"})[0],
        "same strict identity as the prose gate; a typo is not a ratification")
    net(a, "the Step 4 gate refuses if the PLAN ITSELF is missing", _step4_needs_its_plan,
        "a ratification that refers to no document has ratified nothing")
    net(a, "assert_step4_open RAISES when closed",
        lambda: _refuses(lambda: PG.assert_step4_open({}), PG.ProseRefused),
        "the assert form must stop the caller, not hand back a False for it to ignore")
    # THE DISK-READ PATH, which until batch C01 no net in this area had ever entered. See the
    # block above `_ask_both_gates` for what survived here and why an in-memory cfg cannot see it.
    net(a, "an unreadable config.yaml closes both gates", _an_unreadable_config_closes_both_gates,
        "orders 2e63fd03ae72 / 3b5377c4eda9: `return False` on the unreadable branch became "
        "`return True` in both gates and nothing went red -- a config nobody can read OPENED "
        "the gate, which is FAIL OPEN in the one module built to fail closed")
    net(a, "the gates read what is actually in config.yaml", _the_gates_read_what_is_actually_in_config,
        "orders 9cd7b0d0754f / 32a02c7ab338: `safe_load(f) or {}` became `and {}`, which "
        "discards the file and leaves both gates judging an empty mapping for ever -- a gate "
        "wired to nothing looks exactly like a gate that is closed")


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
        "the sibling of the Threads net above: an entry with no Shelfmark cannot be cited "
        "back to anything, and it was filed as complete just as often")
    net(a, "entries that never appeared at all are caught",
        lambda: any("no ◈ block" in m for m in PG.section_shortfall(good, 4)[2]),
        "three missing entries must not read as 100% of the one that arrived")
    net(a, "an empty block raises rather than shelving",
        lambda: _refuses(lambda: PG.assert_block_complete("", 3, "drill"), PG.ProseRefused),
        "nothing at all is the easiest shortfall to produce and the easiest to shelve as "
        "'three entries, all complete'")
    net(a, "a half block raises rather than shelving",
        lambda: _refuses(lambda: PG.assert_block_complete(
            "◈ **A**\nShelfmark: 1\n", 1, "drill"), PG.ProseRefused),
        "a block that started and stopped is the shape 71% of the withdrawn batch had; it must "
        "raise rather than shelve, exactly as an empty one does")
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
    # THE BEHAVIOUR, NOT THE MESSAGE (order 212e3096edfc). The net directly above asserts that
    # the sentence appears in `section_shortfall`'s third return value, and verify_math section
    # 20x asserts the same thing -- and for as long as the defect stood, BOTH were satisfied by
    # a gate that let the block straight through. Each invented entry brought its own 5 to
    # `present` AND its own 5 to `required`, `frac` stayed exactly 1.0, and the sentence was only
    # ever rendered inside a `ProseRefused` that was never constructed. A message is not a price,
    # and a net that tests the message rather than the refusal is a decoy: it is green whether
    # the gate works or not. The ghost direction has had a RAISES net all along ("a half block
    # raises rather than shelving"); this is its missing twin, and this is layer 4 of the gate
    # that stands between the catalogue and 145 unauthorised chapters.
    net(a, "a block with entries nobody asked for RAISES, not merely complains",
        lambda: _refuses(lambda: PG.assert_block_complete(good * 3, 1, "drill"), PG.ProseRefused),
        "an invented entry is a fabricated record -- Hard Rule 1 -- and pricing it into the "
        "denominator is the only thing that can make assert_block_complete refuse it")
    net(a, "and a block of exactly the entries asked for still passes",
        lambda: PG.assert_block_complete(good * 3, 3, "drill") == 1.0,
        "an over-refusing gate is removed by whoever it blocks; the price must fall only on "
        "the entries nobody asked for")
    net(a, "prose that merely MENTIONS Threads does not count as the section",
        lambda: any("Threads" in m for m in PG.section_shortfall(
            "◈ **A**\nShelfmark: 1\nClass: Person\nMagnitude: M2\n"
            "He cut the threads of fate.\n", 1)[2]),
        "the check must want the SECTION, not the word")
    net(a, "a refusal names the block it is about", _a_refusal_names_the_block_it_refused,
        "orders d65d43a823c4 / 22612f09489a / 9730552e6315: every net above reads the FACT of "
        "the raise and none of them reads the message, so both `label or \"block\"` sites and "
        "the `if not required:` guard could be corrupted with the battery still green")
    net(a, "the shortfall says how many, and means it",
        lambda: _the_shortfall_counts_agree_with_their_nouns(good),
        "orders c78d23849343 / 73c814ee9295: these two lines are the only place the shortfall "
        "report states a QUANTITY, and an operator deciding whether to withdraw a batch reads "
        "that quantity -- every net above matches only the stem of the sentence")


def _a_refusal_names_the_block_it_refused(label="II.A.3/Persons#1-30"):
    """Every `ProseRefused` from `assert_block_complete` must name the block it refused.

    Batch C01 mutated `label or "block"` to `label and "block"` at BOTH sites (orders
    d65d43a823c4 and 22612f09489a) and nothing went red, because no net had ever read the
    message -- only the fact of the raise. `ProseRefused`'s own docstring is "carries the reason
    a person needs, never a bare False", and a refusal that cannot say WHICH of several hundred
    chapter jobs it is about is a refusal nobody can act on. `label and "block"` renders every
    one of them as the word "block".

    The empty-manifest case is also the only attacker the `if not required:` guard has ever had
    (order 9730552e6315). With the negation dropped, a block with nothing to check skips the
    refusal and falls through to `present / required` -- ZeroDivisionError, which is not a
    refusal at all, and `_refuses(..., ProseRefused)` two nets above would not catch it either.
    """
    try:
        PG.assert_block_complete("", 0, label)
        return False                    # nothing asked for, nothing delivered, and it passed
    except PG.ProseRefused as e:
        if label not in str(e) or "no entries" not in str(e):
            return False
    except Exception:
        return False                    # a crash is not the refusal this gate promises anyone
    try:
        PG.assert_block_complete("◈ **A**\nShelfmark: 1\n", 1, label)
        return False
    except PG.ProseRefused as e:
        return label in str(e)
    except Exception:
        return False


def _the_shortfall_counts_agree_with_their_nouns(good):
    """The ghost and extra sentences must agree in number with the count they carry.

    Orders c78d23849343 and 73c814ee9295 flipped `"y" if ghosts == 1 else "ies"` to `!=` at both
    sites and survived: every net in this area matches on the STEM of the sentence ("no ◈
    block", "never asked for") and none of them reads the number in front of it. Smallest net in
    the file, and it is not really about grammar -- these two lines are the only place the
    shortfall report states a QUANTITY, and the quantity is what an operator reads when deciding
    whether a batch comes back. "1 entries" and "3 entry" are what a report nobody proofread
    looks like, in the one message that exists to be believed.
    """
    want = ((good, 2, "1 entry produced no"),
            (good, 4, "3 entries produced no"),
            (good * 2, 1, "1 entry the manifest never asked for"),
            (good * 3, 1, "2 entries the manifest never asked for"))
    for text, expected, sentence in want:
        if not any(sentence in m for m in PG.section_shortfall(text, expected)[2]):
            return False
    return True


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
        lambda: PG.unearned_instrument("◈ A\n**Strength**: 30\n", set()) != [],
        "the other half of AUDIT DEFEAT 4: bold around the LABEL hides an axis score just as "
        "well as bold around the whole line, and the model emits both")
    # THIS NET WAS SATISFIED BY THE CONDITION ITS OWN EXPECTATION NAMES AS THE DEFEAT (order
    # 29fceddad360). It asserted `cited_names_for(...) is not None and isinstance(..., set)` --
    # and AUDIT DEFEAT 5 is an ALWAYS-EMPTY set, which is a `set`, and passes both clauses. It
    # also called the function twice with identical arguments and tested `is not None` beside an
    # `isinstance` that already implies it.
    #
    # AND IT IS THE LIVE-CORPUS HALF, WHICH IS NOT WHAT `_cited_names_for_can_credit_a_name`
    # BELOW COVERS. That one is deliberately hermetic -- scratch host map, stood-in
    # `cachekey.load` -- so it proves the FUNCTION credits a name given evidence on disk. Defeat
    # 5 was not a function fault: it was that no entry in any of the 216 record files carried a
    # feats/cited key at all, so the set was empty for a corpus reason and the hermetic net
    # would have reported HELD throughout. This asks the corpus. Both directions, because a
    # `cited_names_for` that echoed back everything handed to it would pass a membership check
    # on its own. Measured live: the real name comes back credited, the invented one comes back
    # empty, and a list holding both returns only the real one.
    net(a, "the cited set is looked up, not read off a key that does not exist",
        lambda: (PG.cited_names_for("Marvel", ["Bruce Banner (Earth-616)"])
                 == {"Bruce Banner (Earth-616)"}
                 and PG.cited_names_for("Marvel", ["A Name No Record Anywhere Carries"])
                 == set()),
        "AUDIT DEFEAT 5: no entry in any of the 216 record files carried a feats/cited key, so "
        "the old set was ALWAYS empty and this guard could not tell earned from invented -- and "
        "the net watching it accepted an empty set, because an empty set is a set")
    net(a, "a floor of zero is treated as misconfigured, not as permission",
        lambda: not PG.evidence_ok("S", 0.0, [{"source": "S", "entries": 5000, "cited": 0}])[0],
        "AUDIT DEFEAT 6: frac < 0 is never true, so floor=0 deleted this layer silently")
    net(a, "a floor above 1 is refused too",
        lambda: not PG.evidence_ok("S", 2.0, [{"source": "S", "entries": 10, "cited": 10}])[0],
        "the mirror of the zero floor: a fraction can never reach 2.0, so a floor above 1 "
        "refuses everything for ever, which is misconfiguration and not a standard")
    net(a, "a floor that is not a number refuses everything",
        lambda: not PG.evidence_ok("S", "as high as it needs to be",
                                   [{"source": "S", "entries": 10, "cited": 10}])[0]
        and not PG.evidence_ok("S", None, [{"source": "S", "entries": 10, "cited": 10}])[0],
        "order 610839223d60: `return False` on the unparseable-floor branch became `return "
        "True` and the battery stayed green -- the two nets above only ever hand it NUMBERS, so "
        "a floor nobody can evaluate admitted everything, which is what a floor exists to stop")
    net(a, "the cited set can actually credit a name", _cited_names_for_can_credit_a_name,
        "orders c19186633734 / 38c4af8d5c02 / 953e03976d62 / 66353129da6a / 298b2269423f: five "
        "one-token changes in cited_names_for, all with the same effect -- it returns the empty "
        "set for everything -- and the only net watching asserted the answer is a `set`")
    net(a, "the supervisor gate agrees with the real gate on a stringy 'false'", _gates_agree,
        "AUDIT DEFEAT 7: overnight used bool(), so prose_enabled: \"false\" read as TRUE")
    net(a, "and proving that never writes the owner's gate", _drill_never_writes_the_gate,
        "run #31: the net above wrote prose_enabled: true into the LIVE config.yaml five "
        "times a cycle and restored it in a finally -- which a kill does not run")


def _cited_names_for_can_credit_a_name():
    """`cited_names_for` must return the names that DO carry evidence, not merely a set.

    FIVE SURVIVORS, ONE HOLE (orders c19186633734, 38c4af8d5c02, 953e03976d62, 66353129da6a,
    298b2269423f). Each is a one-token change on a different line of this one function --
    `(json.load(f) or {})` -> `and {}`, `if not host:` -> `if host:`, `names or ()` -> `and ()`,
    `if not n:` -> `if n:`, `(doc.get("feats") or [])` -> `and []` -- and every one of them has
    the same effect: the function returns the EMPTY SET, for everything, always. The one net
    watching it asserted that the answer is a `set`. It still is.

    AN ALWAYS-EMPTY CITED SET IS NOT A HARMLESS OVER-REFUSAL. It is AUDIT DEFEAT 5 restored
    verbatim -- the defeat this function was written to end, where the cited set was
    unconditionally empty and `unearned_instrument` "was really just asking 'does this line
    match a regex'". Every axis score in every chapter becomes unearned, the refusal stops being
    able to tell an earned number from an invented one, and a guard that refuses everything is a
    guard whoever it blocks eventually deletes. That is how the original prose gate was lost.

    HERMETIC, so the verdict does not depend on which entities happen to be in the live feats
    cache tonight: the host map is a scratch file under a redirected `PG.HERE`, and `cachekey.
    load` is stood in the way `_unreadable_coverage_is_a_refusal` stands in `_coverage_rows`.
    BOTH DIRECTIONS, because a function that simply echoed back every name it was given would
    pass a membership check on its own.
    """
    cited, uncited = "Athuri of the Ninth Shelf", "A Name With Nothing Under It"
    root = tempfile.mkdtemp(prefix="drill_cited_names_")
    saved_here, saved_load = PG.HERE, CK.load

    def stand_in(base, host, name):
        # The host must be the one the map named. `cited_names_for` swallows exceptions from
        # `cachekey.load` into "not cited", so raising here cannot pass by accident -- it can
        # only produce an empty set, which breaches.
        if host != "drill.invalid":
            raise AssertionError("the host map was not consulted")
        if name == cited:
            return {"feats": [{"claim": "shelved the ninth shelf", "cite": "Vol. IX p. 2"}]}, None
        return None, None

    try:
        os.makedirs(os.path.join(root, "data"), exist_ok=True)
        with open(os.path.join(root, "data", "WIKI_HOSTS.json"), "w", encoding="utf-8") as f:
            json.dump({"__drill__": "drill.invalid"}, f)
        PG.HERE = root
        CK.load = stand_in
        if PG.cited_names_for("__drill__", [cited, uncited, "", None]) != {cited}:
            return False
        # AND IT STILL FAILS CLOSED where it is supposed to: a source with no host in the map
        # credits nothing, so every axis score in it stays unearned. That is the safe direction
        # and the net must not buy the direction above by giving this one away.
        return PG.cited_names_for("__not in the host map__", [cited]) == set()
    finally:
        PG.HERE = saved_here
        CK.load = saved_load
        shutil.rmtree(root, ignore_errors=True)


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
    # A UNIQUE ROOT, BECAUSE A FIXED ONE IS SHARED WITH EVERY OTHER DRILL ON THIS MACHINE. This
    # was `gettempdir()/drill_step4_root`, a hard-coded path, opened with `rmtree` and closed
    # with `rmtree`. Two drills running at once -- which is exactly what a mutation harness with
    # parallel sandboxes does, and what two maintenance agents do without noticing -- take turns
    # deleting each other's stand-in plan, and this net then BREACHES on a plan that was removed
    # by a neighbour rather than by the attack it is making. Measured on 2026-08-30 while
    # reproducing the batch C01 survivors: a false breach here is worse than a missing net,
    # because a net that is red for an unrelated reason is DISABLED AS A DETECTOR -- a mutant is
    # judged by difference from the baseline, so anything already red kills nothing.
    root = tempfile.mkdtemp(prefix="drill_step4_root_")
    plan = os.path.join(root, "STEP4_PLAN.md")
    saved = PG.HERE
    try:
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


# ------------------------------------------------- the gates' own DISK-READ path (batch C01)
#
# WHY THIS BLOCK EXISTS. Every net above hands `gate_open` and `step4_gate_open` a cfg mapping
# in memory. That is the right way to attack the DECISION, and it leaves the whole first half of
# both functions -- open config.yaml, parse it, decide what an unreadable or unparseable one
# means -- with no attacker at all. A mutation run measured the consequence: `return False,
# "config.yaml unreadable ..."` was flipped to `return True` in BOTH gates (orders 2e63fd03ae72
# and 3b5377c4eda9) and the entire battery stayed green. An unreadable config.yaml OPENED the
# prose gate. That is the precise inverse of the FAIL CLOSED property prose_gate's own docstring
# claims for this path, and the failure being guarded is 145 chapters nobody asked for.
#
# THE PERMISSION IS NEVER TOUCHED, and that is a constraint on the nets, not an accident of
# them. Nothing here writes `prose_enabled` or `step4_enabled` in any form, on disk or in
# memory. The three scratch configs below are an ABSENT file, a YAML LIST and an EMPTY file, and
# every one of them is a refusal under correct code -- what is attacked is the ENTRY the gate
# judges, never the owner's ruling about it. `PG.HERE` is redirected exactly as
# `_step4_needs_its_plan` redirects it: the predicate is `os.path.join(HERE, "config.yaml")`, so
# a scratch root puts the same question to the same code about a directory this drill owns, and
# the owner's config.yaml is never opened at all. Run #31 established that as the only
# acceptable way for this file to ask that file anything.


def _ask_both_gates(write):
    """Put a scratch config.yaml in front of BOTH gates' disk-read path. -> [(name, ok, why)].

    `write` is handed a scratch root and leaves whatever config.yaml the attack wants there, or
    nothing at all. A stand-in STEP4_PLAN.md is always present, because the Step 4 gate checks
    its plan BEFORE its flag and every answer would otherwise be "the plan is missing" -- the
    wrong refusal, and a net satisfied by the wrong refusal is green on a neighbour's guard.
    """
    root = tempfile.mkdtemp(prefix="drill_gate_root_")
    saved = PG.HERE
    try:
        with open(os.path.join(root, "STEP4_PLAN.md"), "w", encoding="utf-8") as f:
            f.write("a stand-in for the ratified plan\n")
        write(root)
        PG.HERE = root
        return [("gate_open",) + tuple(PG.gate_open()),
                ("step4_gate_open",) + tuple(PG.step4_gate_open())]
    finally:
        PG.HERE = saved
        shutil.rmtree(root, ignore_errors=True)


def _an_unreadable_config_closes_both_gates():
    """A config.yaml that cannot be read must close both gates, and must say that is why.

    `ok is not False` rather than `if ok`: a gate answering None, "" or 0 has not refused, it
    has failed to answer, and this layer's whole rule is that unknown means stop. The reason is
    read as well as the verdict, so a redirect that silently missed -- which would put the
    question to the LIVE config.yaml, readable, and get a refusal for a different reason --
    breaches rather than passing on the real gate's real answer.
    """
    for _name, ok, why in _ask_both_gates(lambda root: None):
        if ok is not False or "unreadable" not in why:
            return False
    return True


def _the_gates_read_what_is_actually_in_config():
    """The gates must READ config.yaml, not merely survive opening it.

    Orders 9cd7b0d0754f and 32a02c7ab338 flipped `yaml.safe_load(f) or {}` to `and {}` in the
    two gates, and both survived. It reads like a harmless idiom swap and it is not: anything
    truthy `and {}` IS `{}`, so the file's contents are DISCARDED and both gates evaluate an
    empty mapping for ever after. That is a gate wired to nothing -- this project's own
    recurring shape -- and no net asking "is the gate closed?" can ever see it, because a gate
    wired to nothing is closed. It is only visible by asking WHY it is closed.

    Two documents, because they separate the two halves of the idiom. A LIST must reach the
    isinstance check and be refused as not-a-mapping (orders bcc439b4d4a2 and 72f2cc2bc4e1 live
    on that line and that return). An EMPTY file must be NORMALISED to an empty mapping and
    refused for the FLAG instead -- `yaml.safe_load` answers None for an empty document, and the
    `or {}` is the only thing that turns that into the mapping the rest of the function is
    written against.
    """
    def _a_list(root):
        with open(os.path.join(root, "config.yaml"), "w", encoding="utf-8") as f:
            f.write("- a list is not a mapping\n- and a list is not a ruling\n")

    for _name, ok, why in _ask_both_gates(_a_list):
        if ok is not False or "did not parse to a mapping" not in why:
            return False

    def _empty(root):
        with open(os.path.join(root, "config.yaml"), "w", encoding="utf-8") as f:
            f.write("")

    for _name, ok, why in _ask_both_gates(_empty):
        if ok is not False or "did not parse to a mapping" in why or "is not true" not in why:
            return False
    return True


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

    def a_short_featless_source_is_not_dropped_either():
        """The feat-LESS arm again, at a size under one block. Named for what it drives.

        THIS NET WAS CALLED `feat_bearing_path_unchanged` AND PRINTED "the feat-bearing path is
        untouched by the fix", AND IT NEVER TOUCHED THAT PATH (order a5de2dcb9447). Its fixture
        is `{"source": "T", ...}`; `pipeline._mined_feats` looks "T" up in data/WIKI_HOSTS.json,
        finds no host, and returns `{}` -- verified, "T" is not in the map -- so `with_feats` is
        empty, `blocks = ([with_feats chunks] or [rest chunks])` takes the `or` arm, and this was
        `nomination_drops_nothing` again with 30 entries instead of 97 and a `sum(len(b))`
        instead of a name comparison. A net's printed NAME is what people trust, and it may not
        promise more than the code delivers -- which is the exact fault
        `coverage_totals_never_exceed_their_entry_count` was renamed for.

        Kept rather than deleted, because a size under the 14-entry block width is a real second
        case for the `or` arm and the sibling above only covers 97. Renamed to say so, and the
        feat-bearing path is now driven for real by the net below.
        """
        rec = {"source": "T", "entries": [{"name": "f%02d" % i, "description": "d"}
                                          for i in range(30)]}
        blocks, _ = PL.synthesis_blocks(rec)
        return sum(len(b) for b in blocks) == 30
    net(a, "a short feat-less source is not dropped either",
        a_short_featless_source_is_not_dropped_either,
        "30 entries is two blocks and a bit; the fallback must chunk it, not sample it")

    def the_feat_bearing_path_really_is_untouched():
        """AND NOW ACTUALLY THE FEAT-BEARING PATH -- with feats standing in, not hoped for.

        `_mined_feats` is the seam, exactly as `PL.records` is the seam for the stranded-
        synthesis net and `CK.load` is for `_cited_names_for_can_credit_a_name`: it is the one
        call that decides which arm `synthesis_blocks` takes, and standing in for it is the only
        way to reach the other arm without a live host map and a populated feats cache. Nothing
        real is touched and the original is restored in a `finally`.

        Every entry carries a feat here, so `with_feats` is the whole source and the `or` never
        comes into it. The property is the same one Hard Rule 0 puts on the fallback: 30 in, 30
        out, chunked and not sampled. The RANKING is asserted too -- feats descending -- because
        the feat arm sorts by feat count and a sort silently reversed or dropped would still
        deliver all 30.

        WHAT THIS DELIBERATELY DOES NOT ASSERT, and it is an OWNER QUESTION rather than a
        finding. `blocks = ([with_feats chunks] or [rest chunks])` SHORT-CIRCUITS, so the moment
        ONE entry in a source has mined feats, every feat-less entry is dropped from nomination
        entirely. No net in this area states that rule, tests it, or distinguishes it from the
        ranked truncation this area exists to forbid. It may well be the intended selection rule
        -- the owner's 2026-08-25 ruling was about the feat-LESS fallback specifically and says
        nothing about the mixed case -- and it is not a drill's place to decide it. Order
        a5de2dcb9447 stays open for that ruling; when it comes, the mixed fixture belongs here.
        """
        rec = {"source": "T", "entries": [{"name": "f%02d" % i, "description": "d"}
                                          for i in range(30)]}
        keep = PL._mined_feats
        try:
            PL._mined_feats = lambda r: {e["name"]: [{"claim": "c"}] * (1 + i % 3)
                                         for i, e in enumerate(r["entries"])}
            blocks, feats_for = PL.synthesis_blocks(rec)
        finally:
            PL._mined_feats = keep
        got = [e["name"] for b in blocks for e in b]
        counts = [len(feats_for[n]) for n in got]
        return (sorted(got) == sorted(e["name"] for e in rec["entries"])
                and len(got) == 30 and counts == sorted(counts, reverse=True))
    net(a, "the feat-bearing path is untouched by the fix",
        the_feat_bearing_path_really_is_untouched,
        "a fix that quietly changes the healthy path too is a second bug -- and for a shift the "
        "net named for this path drove the other one, so nothing was watching it at all")


# ============================================================== THE RIDE RECORD (M23)

def drill_cache():
    a = "THE RIDE RECORD — can one entity be handed another's evidence?"
    net(a, "a foreign document is rejected",
        lambda: not CK.owns({"entity": "Magic 8-Ball"}, "Magic 8 Ball"),
        "the live collision this fix exists for")
    net(a, "its own document is accepted",
        lambda: CK.owns({"entity": "Magic 8 Ball"}, "Magic 8 Ball"),
        "an ownership check that rejects the entity's own document rejects the whole corpus, "
        "and passes every refusal test ever written while doing it")
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
        lambda: not CK.owns({"entity": None}, "Magic 8 Ball"),
        "the sibling of the missing-field net above: a null entity is a field that is present "
        "and says nothing, which a `.get('entity')` truth test reads the same as a match")
    net(a, "the writer does not overwrite a neighbour",
        lambda: CK.disambiguated_path("b", "h", "Magic 8 Ball")
        != CK.natural_path("b", "h", "Magic 8 Ball"),
        "the disambiguated form has to land somewhere ELSE; if the two paths coincide the "
        "collision this whole area exists for is resolved by silently clobbering one of them")

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
                         A.AssayIntegrityError),
        "the other end of the scale from the net above -- a bound checked on one side only is "
        "half a bound, and the arithmetic absorbs a negative as readily as a 99")
    net(a, "a non-numeric score is refused",
        lambda: _refuses(lambda: A.assay("M3", dict(A.CHARTER_KENSHIRO, ruin="lots"),
                                         attestation="Witnessed", worksheet="w"),
                         A.AssayIntegrityError),
        "a range check only ever sees NUMBERS; a score nobody can evaluate must be refused "
        "before it reaches the arithmetic rather than coerced on the way in")
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
        lambda: A.SIGMA_UNKNOWN >= max(A.SIGMA_BY_ATTESTATION.values()),
        "the table's own shape, checked as a constant rather than through a reading: if "
        "SIGMA_UNKNOWN ever slips below the worst attested sigma, knowing NOTHING about an axis "
        "buys a tighter bar than reading it badly")
    net(a, "marking axes INAPPLICABLE cannot buy a tighter bar", _inapplicable_not_gameable,
        "measured clean: n/a renormalises the remaining weights, so the bar WIDENS")
    net(a, "a broken sigma table refuses to load", _broken_table_refuses,
        "the instrument checks itself at import, like the eaten-escape guard")

    # THE OTHER TABLE ON THE PUBLISHING PATH (orders 00a85c511b53 / d27e95a57233, landed
    # 2026-09-06 from handoff/nets_20260906/custodes_policy.py). `custodes.table_faults()`
    # has detected this since order 39f19f7e646c and `custodes.main()` exits non-zero on it,
    # but nothing in the battery or the drill consulted either -- so a new zero-tilt entry
    # would still have surfaced only by audit, three sweeps later, exactly as Threnody's did.
    # This net and the verify_math row added beside it are that missing consultation.
    def custodes_table_faults_is_empty():
        """No CUSTODES entry may carry tilt == 0.0 together with a non-zero evidence_sensitivity.

        Reads the LIVE table via custodes.table_faults() rather than duplicating its arithmetic, so
        this net tracks the real function and cannot drift from it. HELD means the table declares
        nothing it does not enforce; a BREACH names the entry and the exact reason via `raise
        AssertionError`, which `net()` records in `error` and `main()` prints under the breach --
        the same house pattern `no_open_order_sits_on_a_legacy_cap_boundary` uses, so a person
        reading a breach here sees which Custos is at fault rather than a bare False (order
        93e73e0c59a6: this docstring used to describe that work as a future possibility rather
        than doing it).
        """
        import custodes as CU
        faults = CU.table_faults()
        if faults:
            raise AssertionError("%d CUSTODES table fault(s): %s"
                                 % (len(faults), "; ".join(faults)))
        return True


    net(a, "no CUSTODES entry declares a sensitivity its own tilt makes inert",
        custodes_table_faults_is_empty,
        "orders 00a85c511b53 / d27e95a57233 -- tilt=0.0 makes evidence_sensitivity inert by "
        "construction (evidential_part = tilt * evidence_sensitivity * (1 - q)); Threnody sat "
        "exactly there once, found by audit rather than by the battery")


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
        lambda: _refuses(lambda: ESC.clear("ok"), ValueError),
        "the empty-string net above is defeated by two characters; a halt exists to buy a "
        "DECISION, and 'ok' is a keystroke pretending to be one")
    net(a, "the halt refuses a programmatic lift AT RUN TIME, in every spelling",
        _no_runtime_clear,
        "the rule was enforced only by a substring scan for two spellings, which an import "
        "alias, a from-import and a getattr each walk straight past")
    net(a, "no module in src/ clears the halt programmatically", _no_programmatic_clear,
        "an agent may RAISE a halt; only a person may lift one")
    # THE TWELVE MUTATIONS OF 2026-08-31 (mutate.py --target escalation). Six were real holes and
    # six were equivalent; these six nets are the half that was real, plus the constant the other
    # half's equivalence silently rests on.
    net(a, "escalation's per-source log name is really sanitised",
        _the_log_name_actually_sanitises,
        "one character turns the keep-set inside out and a source name walks into a file path")
    net(a, "a halt is raised on the FILE's word, never the writer's",
        _a_halt_is_not_raised_on_the_writer_s_word,
        "`and` -> `or` deletes the read-back and both racing writers report a halt the file "
        "holds once")
    net(a, "an unreadable halt file confirms no record",
        _an_unreadable_halt_file_confirms_nothing,
        "'I cannot read it' must never come back as 'yes, it is in there'")
    net(a, "escalation.main() under a BORROWED argv is not a person at the CLI",
        _a_borrowed_main_is_not_a_person,
        "every existing net called clear() from a frame the second guard refuses, so the first "
        "guard could be inverted and nothing anywhere noticed")
    net(a, "a caller the halt gate cannot SEE is not a person either",
        _an_unfetchable_frame_is_not_a_person,
        "'I could not establish who is calling' must not come back as 'a person is calling'")
    net(a, "a landing that was refused says it was refused",
        _a_refused_landing_reports_that_it_was_refused,
        "the read-back caught both inversions end to end, which is defence in depth working -- "
        "and no measurement at all of the layer underneath it")
    net(a, "the compare-and-swap loop runs at least once",
        _the_retry_loop_runs_at_least_once,
        "four 'not attempted' initialisers are equivalent only while the loop that overwrites "
        "them executes; at 0 attempts all four become the answer")
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

    AND THAT REWRITE WAS DEFEATED THE SAME WAY THE TEXT WINDOW WAS (order adc3dc9c3fc6, run
    #37). `_calls_within`, `_says` and the Continue search all ran over the WHOLE `If` node --
    taken arm, untaken arm and **unreachable code** alike -- so the three findings never had to
    be on the same path, or on any path at all. The sweep built a supervisor whose real
    behaviour ALWAYS declares the library broken and never consults the halt, and parked the
    call, the `continue` and the string in a dead `if False:` block after the `break`. The net
    reported HELD. Dead code makes exactly the claim a comment makes, and binds the running
    program exactly as much.

    So the three findings are now tied together and to the reachable path:

      * `escalation.status` must be called on a path the loop can reach, and its ANSWER must be
        bound to a name -- calling it and discarding the result is not consulting it;
      * the `continue` must be in the REACHABLE arm of an `if` conditioned on that name;
      * "it is a broken one" must be reachable and must be OUTSIDE that arm, because the whole
        finding is that a halted library must not reach the give-up.

    That last clause is the one this net exists for. `_ESC.status` resolves through the alias,
    the from-import and the plain spelling, so renaming the import does not blind it.

    AND IT EXAMINED ONLY THE FIRST SUCH BRANCH (order e2f44baedfdc, run #37). The loop `return`ed
    unconditionally after the first `if idle >= IDLE_LIMIT` it met, so a SECOND one was never
    looked at. The sweep built an `overnight.py` with a correct first branch followed by a
    second, wholly unguarded give-up that prints "it is a broken one" and exits, and this net --
    whose subject is this project's longest outage, a halted library read as a broken one --
    reported HELD. It was one added branch away from missing the same incident twice, which is
    the one thing a net written from an incident must not be.

    The property is stated for EVERY matching branch now, and the absence of any is a failure
    rather than a pass: a supervisor with no idle give-up at all is not evidence that its idle
    give-up consults the halt.
    """
    import ast

    def _consults_the_halt(n):
        if not _calls_within(tree, n, "escalation.status", reachable=True):
            return False
        asked = _bound_from_call(tree, n, "escalation.status")
        if not asked:
            return False                       # status() called and the answer thrown away
        if not _says(n, "it is a broken one", reachable=True):
            return False                       # the give-up must still be reachable at all
        for g in _live_walk(n):
            if not isinstance(g, ast.If) or not _guarded_by(tree, g, asked):
                continue
            arm = _live_stmts(g.body)
            if not _arm_leaves(g.body, ast.Continue):
                continue
            if any(_says(s, "it is a broken one", reachable=True) for s in arm):
                continue                       # the halted arm IS the give-up. Not a guard.
            return True
        return False

    tree = _ast_of(os.path.join(_srcdir(src), "overnight.py"))
    branches = []
    for n in _live_walk(tree):
        if not isinstance(n, ast.If):
            continue
        t = n.test
        if (isinstance(t, ast.Compare) and isinstance(t.left, ast.Name)
                and t.left.id == "idle" and len(t.comparators) == 1
                and isinstance(t.comparators[0], ast.Name)
                and t.comparators[0].id == "IDLE_LIMIT"):
            branches.append(n)
    return bool(branches) and all(_consults_the_halt(n) for n in branches)


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


# ---- THE MUTATION SURVIVORS OF 2026-08-31 -------------------------------------------------
#
# `mutate.py` broke escalation.py on purpose in twelve places and the WHOLE battery -- 1064
# checks and 364 nets -- noticed none of them. Six of those twelve were genuinely equivalent
# under the code as it stands and are recorded as such below; the other six were real holes,
# and each one has its attack here. The rule this file is built on is that a safety nobody has
# seen refuse is not evidence of anything, and a safety a deliberate corruption walks past is
# the same statement with the proof attached.

def _the_log_name_actually_sanitises():
    """`escalation._safe_name` must return a FILENAME, not the string it was handed.

    THE MUTATION THIS REFUSES (order deae02ab8c7e). One character of `_safe_name` --
    `c if (c.isalnum() or c in "-_")` -> `... or c not in "-_"` -- inverts the keep-set from
    "alphanumerics, dash and underscore" to "everything except dash and underscore". The
    function still runs, still returns a string, still passes every existing check, and now
    passes `/`, `\\`, `:` and `..` straight through into `state/escalations/<name>.log`. That is
    a path built out of an unsanitised source name, which is the one thing this function exists
    to make impossible, and the entire battery said nothing.

    Asked as a POSITIVE property of the output rather than by reading the line: the answer may
    hold only the characters the docstring promises. A future rewrite that keeps the promise
    passes; one that quietly stops sanitising cannot.
    """
    hostile = 'Kobold Press: ../../etc/passwd\\x00 & "quoted" (Midgard)'
    out = ESC._safe_name(hostile)
    # ONE ALPHABET CLAUSE, NOT FIVE (order 16b4f9dbecb6). Four clauses used to follow this one
    # -- `"/" not in out`, `"\\" not in out`, `":" not in out`, `".." not in out` -- and not one
    # of them could ever be the reason this net refused. Every character they name is non-alnum
    # and is neither `-` nor `_`, so the alphabet clause had already failed on it. A check that
    # cannot fail reads exactly like a check that passed, which is the shape `liveness.py`
    # exists to find and the standing lesson CLAUDE.md names -- and it was sitting in the drill,
    # which is what Hard Rule -1 rests on. The alphabet is the clause that actually carries all
    # four of those promises, so it is stated once, over the whole answer, where loosening it
    # loses the promises visibly instead of leaving four true-by-construction clauses standing
    # in for a guarantee that has quietly gone.
    return (out and all(c.isalnum() or c in "-_" for c in out)
            # and it still separates two different sources, which is the other half of the
            # contract `_safe_name` was rewritten for (order e8cd908ce5e4).
            and ESC._safe_name("a" * 80 + "one") != ESC._safe_name("a" * 80 + "two"))


def _a_halt_is_not_raised_on_the_writer_s_word():
    """`_raise_halt` must verify the record LANDED; a write that merely claims to is not one.

    THE MUTATION THIS REFUSES (order 74094dcc8063). `if landed and _halt_file_records(rec):`
    -> `if landed or _halt_file_records(rec):`. The `and` is the read-back that escalation.py's
    own comment calls "the original defect wearing the fix's clothes" when it is missing: two
    writers released together both reported `halt_landed: True` while the file held one of
    them. With `or`, the verdict comes from the WRITER'S OWN claim and the file is never
    consulted -- and no check in the battery was reading the file either.

    The attack is a `_land_halt` that lies: it reports (True, "landed") and writes nothing. The
    net holds when `_raise_halt` still answers False, because the fault is not in the file.

    THROUGH `_deliberately_failing`, AND ITS STDERR IS SWALLOWED TOO. `_raise_halt`'s exhausted
    path is one of the few things in this project allowed to be loud on both channels: it calls
    `silence.note("escalation.py:halt-write-denied")` and writes CANNOT WRITE HALT FILE to
    stderr. Both are correct, and both are exactly what this probe is manufacturing -- so
    letting them through would put a rehearsal of the worst fault the library can have into the
    ledger a person reads to find out whether it has happened, once per drill run.
    """
    real_file, real_land = ESC.HALT_FILE, ESC._land_halt
    d = tempfile.mkdtemp(prefix="drill_halt_readback_")
    scratch = os.path.join(d, "HALT.json")
    rec = {"code": "DRILL_READBACK", "what": "a fault whose write is going to lie about landing",
           "at": 1.0, "who": "drill.py"}
    try:
        ESC.HALT_FILE = scratch
        ESC._land_halt = lambda _rec, _expected: (True, "landed")
        raised = _deliberately_failing(lambda: _quietly(lambda: ESC._raise_halt(rec)))
        # Nothing was ever written, so the halt was NOT raised -- and that is what it must say.
        return raised is False and not os.path.exists(scratch)
    finally:
        ESC.HALT_FILE, ESC._land_halt = real_file, real_land
        shutil.rmtree(d, ignore_errors=True)


def _an_unreadable_halt_file_confirms_nothing():
    """`_halt_file_records` must answer False when it cannot read the file at all.

    THE MUTATION THIS REFUSES (order 3d984bc25048). The guard is
    `cur = _read_halt_raw(); if not isinstance(cur, dict): return False`, and `False -> True`
    turns "I could not read the halt file" into "yes, your fault is recorded in it". That is the
    exact inversion `_unreadable_halt` exists to prevent one function away -- a record we cannot
    read is not a record that says what we hoped -- and it is the answer `_raise_halt` gates its
    whole retry loop on, so a corrupt file would end the loop reporting the halt raised.

    Both unreadable shapes are attacked: a file that is not JSON, and a file that parses to
    something that is not a record.
    """
    real = ESC.HALT_FILE
    d = tempfile.mkdtemp(prefix="drill_halt_records_")
    rec = {"code": "DRILL_RECORDS", "what": "not in any file", "at": 2.0}
    try:
        answers = []
        for body in ("{ this is not json", '["a list is not a record"]', ""):
            p = os.path.join(d, "HALT.json")
            with open(p, "w", encoding="utf-8") as f:
                f.write(body)
            ESC.HALT_FILE = p
            answers.append(ESC._halt_file_records(rec))
        # And the absent file, which is the first-halt case.
        ESC.HALT_FILE = os.path.join(d, "nothing-here.json")
        answers.append(ESC._halt_file_records(rec))
        return all(x is False for x in answers)
    finally:
        ESC.HALT_FILE = real
        shutil.rmtree(d, ignore_errors=True)


def _a_borrowed_main_is_not_a_person():
    """`escalation.main()` called from ANOTHER program may not lift the halt.

    THE MUTATION THIS REFUSES (order 8b3929252ee5), and it is the most serious of the twelve.
    `_by_a_person_at_the_cli` has two guards: `__main__` must BE escalation.py, and the caller
    two frames up must be escalation's own `main`. Flipping the first one's `return False` to
    `return True` leaves the second standing, which is why every existing net still passed --
    they all call `clear` from drill.py, whose frame is not named `main`, so the second guard
    refuses them and the hole never shows.

    The case it opens is the one `_by_a_person_at_the_cli`'s own docstring names and no net was
    asking about: `escalation.main()` under a BORROWED argv. Import escalation from any script,
    call its `main`, and frame 2 is a function named `main` whose file IS escalation.py -- so
    with the mutation both guards pass and an autonomous run lifts the halt. That is precisely
    the incident the whole escalation chain was built after.

    The attack synthesises exactly that frame: a function named `main`, compiled under
    escalation.py's own filename, calling `clear()` with a ruling long enough to clear the
    written-ruling check, while `__main__` is whatever is running drill. It runs against a
    SCRATCH halt file -- as `_no_runtime_clear` does -- so a breach cannot lift the real one.
    """
    real = ESC.HALT_FILE
    d = tempfile.mkdtemp(prefix="drill_borrowed_main_")
    scratch = os.path.join(d, "HALT.json")
    standing = json.dumps({"raised_at": 0.0, "code": "DRILL_SYNTHETIC_HALT",
                           "what": "a synthetic standing halt for the borrowed-main probe",
                           "evidence": None, "source": None, "by": "drill.py",
                           "cleared": False, "ruling": None, "also": []},
                          indent=1, ensure_ascii=False)
    src = "def main():\n    return _ESC.clear(_RULING)\n"
    glb = {"_ESC": ESC, "_RULING": "a ruling long enough to pass the written-ruling check"}
    exec(compile(src, ESC.__file__, "exec"), glb)          # noqa: S102 -- the frame IS the probe
    try:
        with open(scratch, "w", encoding="utf-8") as fh:
            fh.write(standing)
        ESC.HALT_FILE = scratch
        refused = _refuses(glb["main"], PermissionError)
        with open(scratch, encoding="utf-8") as fh:
            untouched = fh.read() == standing
        return refused and untouched
    finally:
        ESC.HALT_FILE = real
        shutil.rmtree(d, ignore_errors=True)


def _an_unfetchable_frame_is_not_a_person():
    """When `_by_a_person_at_the_cli` cannot SEE the caller, the answer is no.

    THE MUTATION THIS REFUSES (order 8b3929252ee5, and it is a different line from the one
    `_a_borrowed_main_is_not_a_person` covers). `f = sys._getframe(2)` is wrapped in
    `except ValueError: return False` -- the arm that runs when the stack is shallower than the
    three frames the check counts on. Flipping it to `return True` turns "I could not establish
    who is calling" into "a person is calling", in the one gate that decides whether the halt
    may be lifted. That is the fail-OPEN direction, in the place this project least tolerates it.

    Reachability is honestly the reason nothing caught it: `clear()` must be called by
    something, so frame 2 almost always exists, and no ordinary run reaches this arm. The net
    is here anyway, because a default nobody can trigger today is still the answer the code
    gives tomorrow -- and `_unreadable_halt` one screen away is the same decision made the
    right way, for the same reason. An unreadable answer is more alarming than a bad one, never
    less.

    The stack cannot be made shallow from inside a test, so the CONDITION is injected instead:
    `sys._getframe` is made to raise exactly the ValueError the arm names, for exactly one call.
    The first guard has to be satisfied too, or the check returns at `__main__` and never
    reaches the `try` -- so `__main__.__file__` is pointed at escalation.py for the same one
    call, which is also the harder case: everything else about this caller looks legitimate.
    """
    real_main = sys.modules.get("__main__")
    had_file = hasattr(real_main, "__file__")
    real_file = getattr(real_main, "__file__", None)
    real_getframe = sys._getframe

    def _no_such_frame(_depth):
        raise ValueError("call stack is not deep enough")

    try:
        if real_main is None:
            return False                      # no __main__ at all: cannot pose the question
        real_main.__file__ = ESC.__file__
        sys._getframe = _no_such_frame
        answered = ESC._by_a_person_at_the_cli()
    finally:
        sys._getframe = real_getframe
        if had_file:
            real_main.__file__ = real_file
        else:
            try:
                del real_main.__file__
            except AttributeError:
                pass
    return answered is False


def _a_refused_landing_reports_that_it_was_refused():
    """`_land_halt` must return landed=False on BOTH of its failure paths.

    THE MUTATIONS THIS REFUSES (orders 05daf8a1d2e1 and 0c792a51a1f4): `return False, why` ->
    `return True, why` in the compare-and-swap's refusal arm, and `return False, "raised"` ->
    `return True, "raised"` in the `except`. Both survived the whole battery, and the reason
    they survived is worth keeping: `_raise_halt`'s read-back CATCHES them end to end, so the
    library's observable behaviour is unchanged and the loop still terminates correctly. That is
    defence in depth working exactly as designed.

    It is still a hole. Nothing measured `_land_halt`'s own contract, so the read-back was
    load-bearing without anybody knowing it was -- and the moment it is relaxed for any reason,
    two inverted returns become a halt that reports itself raised and is not. A layer that is
    silently the only thing holding is the shape this project files as a fault. So the inner
    contract is now measured directly, one net per arm.
    """
    real = ESC.HALT_FILE
    d = tempfile.mkdtemp(prefix="drill_land_halt_")
    scratch = os.path.join(d, "HALT.json")
    rec = {"code": "DRILL_LAND", "what": "a fault for the refused-landing probe", "at": 3.0}
    try:
        # ARM 1 -- the compare-and-swap refuses, because the digest we hand it is not the
        # file's. `_land_halt` must say it did not land.
        with open(scratch, "w", encoding="utf-8") as fh:
            fh.write(json.dumps({"raised_at": 0.0, "code": "STANDING", "what": "x",
                                 "cleared": False, "also": []}))
        before = open(scratch, encoding="utf-8").read()
        ESC.HALT_FILE = scratch
        # The last of the ten probe-litter sites (2026-09-06). ARM 1 hands `_land_halt` a digest
        # that is deliberately not the file's, so the compare-and-swap refuses and
        # `replace_if_unchanged` files `note("silence.py:cas-target-changed")` -> `health.record`.
        # Found by instrumenting `health.record` with a stack-capturing spy and running the whole
        # drill: the ledger diff said the key still grew by one, and reading code had already
        # sent me to the wrong function twice. Two of these ten were located by measurement after
        # inspection failed, which is the argument order 895a99602bf0 makes for a standing check.
        stale, why_stale = _deliberately_failing(
            lambda: ESC._land_halt(rec, "not-the-digest-on-disk"))
        after = open(scratch, encoding="utf-8").read()
        arm1 = (stale is False and after == before and bool(str(why_stale).strip()))

        # ARM 2 -- the write itself throws, because the halt file's PARENT is a regular file.
        # `makedirs` raises, the `except` arm runs, and it must report a refusal too.
        blocker = os.path.join(d, "a-file-not-a-directory")
        with open(blocker, "w", encoding="utf-8") as fh:
            fh.write("x")
        ESC.HALT_FILE = os.path.join(blocker, "HALT.json")
        # Loud on both channels by design, and this is the rehearsal -- see `_quietly`.
        threw, why_threw = _deliberately_failing(
            lambda: _quietly(lambda: ESC._land_halt(rec, None)))
        arm2 = (threw is False and why_threw == "raised")
        return arm1 and arm2
    finally:
        ESC.HALT_FILE = real
        shutil.rmtree(d, ignore_errors=True)


def _the_retry_loop_runs_at_least_once():
    """`STOP_CAS_ATTEMPTS` must be >= 1, because four other mutations depend on it silently.

    WHAT THIS IS ACTUALLY PINNING (orders 939dd7430619, a380a696d364, b20396a54027,
    081a64e8e120). Four `landed, ... = False, "not attempted"` initialisers were mutated to
    `True` and every one survived. Read carefully, all four ARE equivalent: each sits directly
    above `for _ in range(STOP_CAS_ATTEMPTS):`, every path out of those loops reassigns
    `landed`, so the initial value is never the one returned. They are recorded here as
    equivalent rather than filed as defects.

    They are equivalent for exactly one reason, though, and it is a reason nothing was checking:
    the loop must RUN. Set `STOP_CAS_ATTEMPTS = 0` -- a plausible edit, and the kind a person
    makes while disabling a retry they think is causing trouble -- and all four initialisers
    become the returned value at once. Three of them would then report a halt raised, a
    subsystem stopped and a subsystem resumed, none of which was ever attempted. So the constant
    that makes the equivalence true is now held by a net instead of by luck.
    """
    return isinstance(ESC.STOP_CAS_ATTEMPTS, int) and ESC.STOP_CAS_ATTEMPTS >= 1


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

    TWO FURTHER DEFECTS, BOTH OF THEM THE KIND THAT HALTS THE LIBRARY OVER NOTHING.

    IT WAS PINNED TO AN IMPORT ALIAS (order 7cc460706efe, run #37). It asked for the literal
    spelling `_ESC.escalate`, so a CORRECT `local_agent.py` -- a real, reachable
    `ESC.escalate(ESC.SAFETY, ...)` in the ALARM branch, differing only in writing
    `import escalation as ESC` -- returned False. A net that returns False is a BREACH, and a
    breach raises an OWNER halt: renaming an import would have stopped the library until a
    person ruled on it. `_spellings_of_call` has resolved aliases all along, so the question is
    now `escalation.escalate`, which `_ESC.`, `ESC.`, a bare `escalate` from a from-import and
    the plain module spelling all answer. The RUNG is asked the same way through
    `_name_spellings`, which also stops an unrelated object's `.SAFETY` attribute answering for
    escalation's. Same class as order 8ee268ce32cc, where a net pinned to `_land` blocked a
    compare-and-swap fix.

    AND IT ACCEPTED AN ESCALATION THE PROGRAM CANNOT REACH (order c54a22a4e6fc, run #37).
    Neither the branch search nor the rung search was reachability-scoped, so a `run()` whose
    ALARM branch does nothing, carrying `_ESC.escalate(_ESC.SAFETY, ...)` inside an `if False:`,
    returned True -- a half-written module on disk with the battery reporting success, which is
    verbatim the outcome this net's expectation names. Branch, call and rung are now all taken
    from the reachable tree.
    """
    import ast
    tree = _ast_of(os.path.join(_srcdir(src), "local_agent.py"))
    maps = _import_maps(tree)
    # SCOPED TO `run`, NOT TO THE MODULE (order 616e761094a5, run #40). This walked
    # `_live_walk(tree)`, and `_live_walk` descends into every `def` in the file whether or not
    # anything calls it -- this file says so itself where the THREE DEGREES of reachability are
    # named, in the paragraph under `_call_spellings`: `_call_spellings(..., reachable=True)` is
    # the middle form, it answers "the call is on a path execution can enter", and "an uncalled
    # helper still satisfies it, which is why it is the middle and not the top". (Cited by symbol
    # rather than by line per order 0c7592915a48: this read `:506-513`, which had drifted onto
    # `_static_truth`'s docstring. Order 5c5dd914bf82.) So the
    # ALARM branch, the `escalation.escalate` call and the `escalation.SAFETY` rung could all
    # live in a function nothing invokes, and the net would still report HELD.
    #
    # PROVED, not reasoned: a `local_agent.py` whose real `run()` sets `out["ALARM"]`, prints it,
    # escalates nothing and returns -- with the SAFETY escalation parked in
    # `_a_helper_nothing_ever_calls` -- returned True. That is verbatim the outcome this net's
    # own expectation names: "a half-written module on disk while the run reports success is the
    # worst outcome this lane has."
    #
    # Its two siblings in this area were the model and were correctly scoped all along:
    # `_write_lane_checks_the_halt` and `_run_marks_a_landless_run_failed` both take
    # `_defn(tree, "run")` first and refuse if it is absent.
    run = _defn(tree, "run")
    if run is None:
        return False
    # THE SCOPE IS `run` AND WHAT `run` HANDS WORK TO -- not the module, and not `run` alone.
    #
    # Module-wide was the defect. `run` alone is too tight and would have breached against
    # CORRECT code, which in this file means an OWNER halt over a working library: the real
    # ALARM lives in `t_propose_patch`'s revert-failure branch (it sets `out["ALARM"]` and
    # escalates at SAFETY there -- cited by symbol, not by line, per order 0c7592915a48: a line
    # number drifts the first time something is edited above it, a symbol does not), because
    # `run` COLLECTS the alarms its tools raise rather than raising them itself.
    #
    # `t_propose_patch` reaches the loop through the `impl` DISPATCH TABLE, so it is a bare
    # NAME reference inside `run` and never a syntactic call there. `_call_spellings` -- what
    # `mutation_never_touches_the_live_tree` uses to build its `bodies` list -- would not see it.
    # (The line span that used to sit here had drifted onto `the_keeper_asks_before_restarting`;
    # the symbol was already in the sentence. Orders 0c7592915a48 and 5c5dd914bf82.) Name references are therefore what is followed, which is the same
    # relation one step looser and is exactly the relation a dispatch table creates: a function
    # `run` names is a function `run` can invoke. A function nothing in `run` mentions -- the
    # uncalled helper this order is about -- is still out.
    bodies = [run]
    for name in sorted({n.id for n in ast.walk(run) if isinstance(n, ast.Name)}):
        d = _defn(tree, name)
        if d is not None and d is not run and d not in bodies:
            bodies.append(d)
    for n in [x for b in bodies for x in _live_walk(b)]:
        if not isinstance(n, ast.If):
            continue
        if not _subscript_assigns(n, "out", "ALARM", reachable=True):
            continue
        if not _calls_within(tree, n, "escalation.escalate", reachable=True):
            continue
        # The RUNG matters as much as the call: escalating this at a lower one would leave a
        # half-written module on disk while the battery went on reporting success.
        for c in _live_walk(n):
            if not (isinstance(c, ast.Call)
                    and _spelled(_spellings_of_call(tree, c, maps), "escalation.escalate")):
                continue
            for arg in c.args:
                if _spelled(_name_spellings(tree, arg, maps), "escalation.SAFETY"):
                    return True
    return False


def _run_marks_a_landless_run_failed(src=None):
    """`local_agent.run()` contains a real `out["ok"] = False`. -> bool.

    The half of `_landing_nothing_is_not_success` that has to be read off another module rather
    than driven: `_achievement` can compute the right verdict all day and it changes nothing
    unless `run()` acts on it. Scoped to `run` and asked as an assignment, so neither a comment
    nor a docstring nor the same words in a different function can answer for it.

    AND AN ASSIGNMENT AFTER THE RETURN IS A COMMENT (order c54a22a4e6fc, run #37). The walk was
    `ast.walk(run)`, so a `run()` that returns `{"ok": True, "patches": []}` -- a landless run
    reported as success, the fault itself -- with `out["ok"] = False` on the following line
    satisfied it. The assignment must now be on a path the program can reach.
    """
    import ast
    tree = _ast_of(os.path.join(_srcdir(src), "local_agent.py"))
    run = _defn(tree, "run")
    if run is None:
        return False
    return any(isinstance(n.value, ast.Constant) and n.value.value is False
               for n in _subscript_assigns(run, "out", "ok", reachable=True))


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
    answered = LA._achievement([], True, answer="here is what I found")
    # AND THE FOURTH SHAPE: NEITHER WORK NOR AN ANSWER. Measured 2026-08-30 on a real work
    # order -- the model read one file, said nothing, and the run returned
    # {"ok": true, "answer": "", "patches": []} under the achievement line "answer-only
    # run". The existing blank-answer guard covered only turn 0 ("not tool-trained"), so a
    # model that stopped talking on any later turn came back clean. This is the
    # all-refused case one step over: a caller closing an order on `ok` gets nothing.
    produced_nothing = LA._achievement([], True, answer="   ")
    return (all_refused["landed"] == 0 and all_refused["attempted"] == 2
            and landed["landed"] == 1 and answered["attempted"] == 0
            and answered["produced_nothing"] is False
            and produced_nothing["produced_nothing"] is True
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

    def the_gate_and_the_public_door_are_denied():
        """The local model may not write the prose gate, nor the module that pushes to the public.

        NOT A STRING BYPASS -- the first six attacks in this area were all "a name the filesystem
        resolves differently". This one is the list simply not naming two files it says it names.
        `local_agent.DENYLIST`'s own stated rule is that each entry "is either the thing that
        would have to be working to detect a bad patch, or the thing doing the patching", and
        until 2026-09-04 it omitted both of these while `src/` sat on `WRITABLE_PREFIXES`.
        Measured before the fix: `_denied_target` answered False for both.

          * `prose_gate.py` is THE gate -- the one an autonomous run deleted for looking like an
            instruction to a human, with 145 unauthorised chapters after it. The prefix denylist's
            comment says "config.yaml holds the prose gate", which is true of the FLAG and not of
            the ENFORCEMENT, so the switch was protected and the wiring was writable. Nothing had
            to touch the flag: `overnight.py` has already demonstrated, in this repository, that
            reimplementing this check with `bool()` makes `prose_enabled: "false"` OPEN it, and
            every gate below stays green because they ask whether a patch parses, lints, imports
            and leaves verify_math passing -- not whether it left a decision intact.
          * `publish.py` is the only module the local model could reach that takes an
            IRREVERSIBLE, OUTWARD action, and it carries `scan_for_secrets` in front of that push.
            It is both halves of the rule at once, and it is the module that pushed
            deliberately-corrupted source to the public repo twice on 2026-08-25.

        The net asks the LIVE gate, not the constant, because `_denied_target` is what
        `t_propose_patch` actually consults and a module denylist that the resolver never reaches
        would pass a source-shaped check while refusing nothing. The control arm matters as much
        as the attack: an ordinary repair target must still be writable, or the honest way to make
        this net green is to deny everything.
        """
        denied = all(LA._denied_target(p) for p in ("src/prose_gate.py", "src/publish.py"))
        # CONTROL -- the LOCAL rung still has a job. If these came back denied too, the net above
        # would be measuring a gate that refuses its own purpose.
        still_open = not any(LA._denied_target(p) for p in
                             ("src/rosetta.py", "src/hostcheck.py", "src/magnitude.py"))
        return denied and still_open
    net(a, "the local model may not write the prose gate or the module that pushes to the public",
        the_gate_and_the_public_door_are_denied,
        "the gate whose deletion cost this project 145 unauthorised chapters was writable by "
        "the autonomous local model, and so was the module that pushes to a public repo behind "
        "the secret scanner -- protecting config.yaml protects the switch, not the wiring")

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

        IT SAID "SKIPS" AND IT HALTED THE LIBRARY (order ef0b67732a3b). The docstring promised a
        skip when the junction could not be staged; the code returned False, `net()` records
        False as held=False, and `main()` escalates a breached net to OWNER -- a full stop, not a
        skip. Off Windows it was worse: `subprocess.run(["cmd", ...])` raises FileNotFoundError,
        and `net()` records a raised attack as a breach too, so the entire battery halted the
        library on any machine without `cmd`. Two nets in this one file were answering the same
        question in opposite directions, because `datasette_config_is_generated_not_copied` had
        already ruled the other way, and ruled correctly: "A path that could not be written is a
        measurement that did not happen, and a measurement that did not happen must not be graded
        either way." So this follows that ruling now -- an unstageable junction is NOTED and
        returns True, which is a measurement declining to be taken rather than an alarm about the
        writable-surface gate. The alarm it used to sound was about the probe, and it was aimed at
        the owner.

        THAT IS NOT "ABSENCE READ AS CLEAN", and the difference is worth being exact about,
        because this file is built against that shape. The gate under test is exercised by five
        other nets in this same area against string-level bypasses; this one adds the
        directory-level case, and on a machine that cannot make a junction there is no
        directory-level case to have. What is refused is grading an attack that was never
        delivered. The note is the record that it was not.
        """
        import subprocess as _sp
        import silence as _si
        import local_agent as LA
        link = os.path.join(LA.HERE, "src", "__drill_junction_probe__")

        def unstage():
            """Remove the probe whether or not it ever became usable. -> None.

            A DANGLING JUNCTION IS STILL A JUNCTION, and this is the litter the old shape left.
            `mklink /J` SUCCEEDS against a target that does not exist -- it makes a junction
            pointing at nothing -- and `os.path.isdir` on one of those is False. The staging
            check therefore read "could not stage" and returned without removing anything, so on
            any tree with no `state/` directory yet (a fresh clone, a mutation sandbox, a scratch
            copy) every run left `src/__drill_junction_probe__` behind. `src` is in
            `publish.COPY_DIRS`. Reproduced in a scratch tree while this net was being worked.
            """
            for remove in (os.rmdir, os.unlink):
                try:
                    remove(link)
                    return
                except FileNotFoundError:
                    return
                except OSError:
                    continue
            if os.path.lexists(link):
                _si.note("drill.py:junction-probe-cleanup")

        try:
            _sp.run(["cmd", "/c", "mklink", "/J", link, os.path.join(LA.HERE, "state")],
                    capture_output=True, text=True,
                    creationflags=getattr(_sp, "CREATE_NO_WINDOW", 0))
        except OSError:
            # No `cmd` at all -- not Windows. FileNotFoundError is an OSError.
            unstage()
            _si.note("drill.py:junction-probe-unstageable")
            return True
        if not os.path.isdir(link):
            unstage()
            _si.note("drill.py:junction-probe-unstageable")
            return True                       # could not stage the attack; not evidence either way
        try:
            through_link = LA._safe("src/__drill_junction_probe__/failures.json")
            ordinary = LA._safe("src/lognames.py")
        finally:
            unstage()
        # Refused through the link, and the ordinary path still permitted -- a gate that refuses
        # everything passes every refusal test ever written.
        #
        # AND THE CLEANUP IS NOT PART OF THE VERDICT (order f5f01fe5f8ef). This used to end
        # `and not os.path.exists(link)`, which graded the net's OWN litter: a denied `os.rmdir`
        # -- an antivirus scanner holding the directory for a moment is enough on this machine
        # -- turned a held net into a breached one, and `main()` escalates a breached net to
        # OWNER. A full stop caused by a probe that could not tidy up is precisely the failure
        # order ef0b67732a3b already records this net causing once, and it contradicts the
        # ruling written above: a probe that could not be staged, or unstaged, is NOTED, not
        # graded. `unstage()` files that note. The sibling net at
        # `_junction_to_an_unlisted_but_undenied_place` has always left the term out.
        return through_link is None and bool(ordinary)
    net(a, "a JUNCTION out of the writable surface is refused",
        _junction_out_of_the_writable_surface,
        "the gate compared a string while the filesystem resolved a different one -- the same "
        "shape as the five bypasses before it, and mutate.py junctions three directories as a "
        "matter of course, so this is a technique the project already uses on itself")

    def _junction_to_an_unlisted_but_undenied_place():
        """BYPASS CLASS SEVEN, and the one the net above does not cover (2026-09-02).

        The junction net above points at `state/`, which is on `DENYLIST_PREFIXES` — so it
        proves the DENYLIST is asked of the resolved path, which `_safe` does. It says nothing
        about the ALLOWLIST, and the two lists are not complements. `t_propose_patch` tested
        `WRITABLE_PREFIXES` against the path AS WRITTEN, so a junction pointing anywhere merely
        UNLISTED — `data/`, whose only denied child is `data/records/` — satisfied every gate:
        allowlist passes on `src/...`, denylist passes on `data/...`, and the write lands off
        the writable surface entirely.

        ATTACKED THROUGH `t_propose_patch`, not `_safe`, because that is where the allowlist
        lives and a net that asks the wrong function proves nothing about the right one. The
        target is a probe file this net creates and removes, so the breaching case damages only
        its own scratch file — a net whose failure mode is corrupting real state is not a net
        anyone will keep enabled.
        """
        import subprocess as _sp
        import silence as _si
        import local_agent as LA
        link = os.path.join(LA.HERE, "src", "__drill_surface_probe__")
        probe = os.path.join(LA.HERE, "data", "__drill_surface_probe__.txt")

        def unstage():
            for remove in (os.rmdir, os.unlink):
                try:
                    remove(link)
                    break
                except FileNotFoundError:
                    break
                except OSError:
                    continue
            if os.path.lexists(link):
                _si.note("drill.py:surface-probe-cleanup")
            try:
                os.unlink(probe)
            except FileNotFoundError:
                pass
            except OSError:
                _si.note("drill.py:surface-probe-cleanup")

        try:
            os.makedirs(os.path.dirname(probe), exist_ok=True)
            with open(probe, "w", encoding="utf-8") as fh:
                fh.write("CANARY\n")
        except OSError:
            unstage()
            _si.note("drill.py:surface-probe-unstageable")
            return True
        try:
            _sp.run(["cmd", "/c", "mklink", "/J", link, os.path.join(LA.HERE, "data")],
                    capture_output=True, text=True,
                    creationflags=getattr(_sp, "CREATE_NO_WINDOW", 0))
        except OSError:
            unstage()
            _si.note("drill.py:surface-probe-unstageable")
            return True
        if not os.path.isdir(link):
            unstage()
            _si.note("drill.py:surface-probe-unstageable")
            return True               # could not stage the attack; not evidence either way
        try:
            got = LA.t_propose_patch("src/__drill_surface_probe__/__drill_surface_probe__.txt",
                                     "CANARY", "BREACHED", why="drill: bypass class seven")
            after = ""
            try:
                with open(probe, encoding="utf-8") as fh:
                    after = fh.read()
            except OSError:
                _si.note("drill.py:surface-probe-readback")
            # An ordinary in-surface path must still be reachable: a gate that refuses
            # everything passes every refusal test ever written.
            ordinary = LA._safe("src/lognames.py")
        finally:
            unstage()
        # IT MUST BE REFUSED BEFORE THE GATES RUN, NOT MERELY UNDONE AFTERWARDS.
        #
        # TWO WRONG ASSERTIONS WERE WRITTEN HERE BEFORE THIS ONE, and both are worth recording
        # because they fail in opposite directions.
        #
        # The first asserted `not applied` and an unchanged file. It went GREEN against the
        # unfixed code -- which is how the assertion was found to be wrong rather than the bug
        # absent. The patch had been APPLIED and then rolled back by the downstream
        # `verify_math`/lint/import gate, so a working allowlist and a defeated one had
        # identical end states. That backstop is real defence in depth but it is
        # CONTENT-SENSITIVE: it re-runs the battery, so a write to a non-Python file -- a JSON
        # record, a YAML config, anything under `data/` -- regresses nothing and would have been
        # KEPT. Asserting on the aftermath tested the backstop, not the gate.
        #
        # The second over-corrected and demanded the refusal message contain "writable surface".
        # That passed on the live tree and BREACHED inside `mutate.py`'s sandbox, where `data/`
        # is itself a junction to the real repository (see `mutate.sandbox`): the probe then
        # resolves OUTSIDE the sandbox root, `_safe()` refuses it first for that reason, and the
        # wording is different. The refusal was correct and the net called it a breach -- and
        # because `mutate` grades every mutant by DIFFERENCE from a baseline, a net that is red
        # in the baseline is disabled as a detector for that entire run. A net that misfires in
        # the sandbox does not merely cry wolf; it quietly switches off the mutation pass.
        #
        # So the assertion is the narrowest property that actually separates the two worlds, and
        # it is indifferent to WHICH gate refused: the write was refused, and it was refused
        # before execution ever reached the gate stage. `gate` present is precisely the
        # applied-then-reverted signature the vulnerable build produced.
        return (not got.get("applied")
                and "gate" not in got
                and bool(got.get("error"))
                and "BREACHED" not in after and bool(ordinary))
    net(a, "a junction to a merely UNLISTED place is refused, not just a denied one",
        _junction_to_an_unlisted_but_undenied_place,
        "the allowlist is the gate that fails closed, and it was asking about a string the "
        "filesystem had already disagreed with -- a denylist that misses is one hole, an "
        "allowlist that misses is every file nobody thought to list")

    def _write_lane_checks_the_halt(src=None):
        """`local_agent.run` must CALL assert_clear, not merely mention it.

        Written first as a substring scan over the function source, and it passed against a
        regressed build in which the call had been replaced by `pass` -- because the paragraph
        explaining WHY the call is there still contained the word. A literal cannot tell code
        from prose about code, which is the defect the run #35 sweep filed against nine other
        nets in this file. Asked of the parse tree instead: an actual Call node, by either
        spelling, anywhere in the function.

        AND "ANYWHERE IN THE FUNCTION" ACCEPTED TWO THINGS IT SHOULD NOT (order c54a22a4e6fc,
        run #37). The walk was `ast.walk`, so a call parked after the `return` answered for one
        on the live path; and the test was `fn.attr == "assert_clear"`, so
        `logging.getLogger("x").assert_clear()` -- any attribute of that name, on any object --
        answered too, which is the same "a word is not a call" defect one level in. The call
        must now be REACHABLE inside `run` and must RESOLVE to `escalation.assert_clear`.

        READ OFF THE FILE, NOT `inspect.getsource` (run #37). A function's own source carries no
        import statements, so nothing could be resolved through the module's aliases at all --
        which is why the check had been reduced to matching a bare attribute name in the first
        place. Parsing `local_agent.py` whole makes `_ESC.assert_clear`, `ESC.assert_clear` and
        a bare `assert_clear` from a from-import one question, and takes an unrelated object's
        method of the same name out of the answer.
        """
        tree = _ast_of(os.path.join(_srcdir(src), "local_agent.py"))
        run = _defn(tree, "run")
        if run is None:
            return False
        return _calls_within(tree, run, "escalation.assert_clear", reachable=True)
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

        `no such file` WAS THE SAME CONFLATION WITH A DIFFERENT MESSAGE, and it made the one net
        here that matters empty (order 5a24b2956be8). `local_agent.t_propose_patch` answers
        `no such file` BEFORE the module denylist, before the WRITABLE_PREFIXES/WRITABLE_FILES
        allowlist and before DENYLIST_PREFIXES -- so for any path that does not exist on disk
        this returned True whatever the gates said. Reproduced 2026-08-30 with every one of
        those five lists emptied, i.e. an agent with no writable-surface gate at all:
        `denied('something_nobody_listed.txt')` was still True, still
        `err='no such file: ...'`, and the net still read HELD. The control in the same run --
        `denied('data/COVERAGE.json')`, whose file exists -- correctly flipped to False, so the
        neighbouring allowlist nets do have teeth and only the invented-name one was empty.
        Every remaining `denied(...)` target in this area exists on disk and comes back with
        `denylist`, `protected region` or `writable surface`.
        """
        r = LA.t_propose_patch(path, "x", "y", why="drill", apply=False)
        if not isinstance(r, dict) or r.get("applied"):
            return False
        err = str(r.get("error") or "")
        if "denylist" in err or "protected region" in err or "writable surface" in err:
            return True
        # AND THE OTHER HALF OF `no such file`, WHICH IS A GATE AFTER ALL. Measured 2026-08-30
        # while making the line above stop accepting that message: `t_propose_patch` prints it
        # for TWO different events -- the file is genuinely absent, which is not a refusal, and
        # `_safe()` RETURNED None, which is the containment gate refusing. `_safe` is the gate
        # that stops an alternate data stream, a trailing dot or space, a path outside the
        # project root, anything under `.git`, and -- bypass class six -- a name inside the
        # project that RESOLVES outside it through a junction. The two are told apart by asking
        # `_safe` itself rather than by reading the message.
        #
        # This is not theoretical and it is not only about hostile paths. `mutate.py` junctions
        # `data/`, `prompts/`, `reference/` and `output/index` into every sandbox, so inside a
        # mutation sandbox EVERY path under those four trees resolves out of the sandbox and
        # `_safe` refuses it. Six nets here point at exactly those trees -- the records, the
        # charter, the catalog, COVERAGE.json, WIKI_HOSTS.json -- and until the line above
        # stopped taking `no such file` on faith, all six were passing in the sandbox for the
        # wrong reason, in the run whose entire purpose is measuring which nets cannot see.
        #
        # `local_agent.py` is NOT changed to suit this net, per order 5a24b2956be8: no path's
        # verdict moves, and a genuinely missing ordinary file still passes `_safe` (it is inside
        # the project) and fails only `os.path.isfile`, so the invented-name net below still
        # requires a real file on disk to mean anything.
        return "no such file" in err and LA._safe(path) is None

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
    net(a, "it cannot edit the catalog", lambda: denied("output/index/catalog.json"),
        "output/ is what the library has produced; a night-shift model that can rewrite the "
        "catalog can rewrite the record of its own work")
    def cannot_edit_shared_run_state():
        """A SCRATCH FILE IN `state/`, because the halt file is not always there to point at.

        This net used to probe `state/HALT.json`, and its verdict turned on whether that file
        happened to exist. In the live tree it always does. In a MUTATION SANDBOX it never does
        -- `mutate.sandbox()` removes it deliberately, since a copied halt would make every gate
        refuse on purpose -- so once `denied()` stopped accepting `no such file` on faith
        (order 5a24b2956be8) this net was the last of six here reporting a refusal it had not
        actually obtained. Worse, it was UNSTABLE: a sandbox drill run that breaches RAISES a
        halt, which writes `state/HALT.json` inside that sandbox, so a second run in the same
        directory saw a different answer than the first.

        `state/` is refused as a whole -- the allowlist admits `src/`, `prompts/`, `handoff/` and
        four root documents and nothing else -- so a scratch name inside it tests exactly the
        property, in both trees, without depending on any particular file being present. The
        halt file is still the thing this net is about; it is simply no longer the thing it needs
        to find on disk.
        """
        probe = os.path.join(HERE, "state", "__drill_state_probe__.json")
        try:
            os.makedirs(os.path.dirname(probe), exist_ok=True)
            with open(probe, "w", encoding="utf-8") as fh:
                fh.write('{"drill": "state-surface probe, created and deleted by drill.py"}\n')
            return denied("state/__drill_state_probe__.json")
        finally:
            # A FAILED CLEANUP IS NOT NOTHING, and this one litters the LIVE shared run-state
            # directory -- the place every job looks to find out what is going on. Was
            # `except OSError: pass`; a denied `os.remove` on Windows needs nothing exotic (a
            # reader holding the file, or this machine's documented Norton interference) and the
            # reason it failed was thrown away at the moment it was known. Same discipline as
            # the junction-probe and blast-cap cleanups. Not a reason to FAIL the net: failing
            # to tidy up is not a fault, and killing the battery over a permissions error would
            # lose every other verdict with it.
            try:
                os.remove(probe)
            except OSError:
                import silence as _si
                _si.note("drill.py:state-probe-cleanup")
    net(a, "it cannot edit shared run state", cannot_edit_shared_run_state,
        "least of all the halt file")
    net(a, "it CAN still be given ordinary work", lambda: not denied("src/scope.py"),
        "a writer that can write nothing is not a writer")

    def blast_cap_bites():
        """The bound that does not depend on knowing which gate was bypassed.

        THIS PROBE STOPPED EXERCISING THE CAP, AND HALTED THE LIBRARY SAYING SO (2026-08-28,
        DRILL_BREACH at 22:44). It hammered `t_propose_patch` with `apply=False` and a find
        string occurring ZERO times, and read a refusal out of the far end. Order 528e5b07fded
        then moved `_blast_ok`'s charge to AFTER the uniqueness check and after the `--no-apply`
        early return -- correct, and what the comment beside it had claimed all along: a refused
        path costs no budget, and neither an ambiguous find string nor a dry run is an edit. So
        the probe's calls stopped charging anything, the cap could never bite, and the net
        breached against a library that was working.

        The net was right to be unhappy and the local_agent change is right to stand. What was
        wrong was the PROBE: it demonstrated the cap through a path that no longer reaches it,
        which is the same defect as a check that cannot fail wearing the other sign. It now
        drives the path the cap actually guards -- a REAL find string, `apply=True`, a patch
        that would otherwise land -- and the bound is lowered to make it bite, exactly as the
        orphan reaper's age gate is lowered next door to make reaping observable.

        THE TARGET IS A SCRATCH FILE THIS PROBE CREATES AND DELETES, inside the writable surface
        but under `handoff/` rather than `src/`: `codewatch` fingerprints `src/`, and a battery
        that adds and removes a module there would bounce every standing daemon onto rc=17 every
        cycle. Nothing tracked is written on either arm -- the staged arm does not write by
        definition, and the capped arm is refused BEFORE the write, which is the property.
        """
        keep_caps = (LA.MAX_PATCHES_PER_RUN, LA.MAX_FILES_PER_RUN)
        probe = os.path.join(HERE, "handoff", "__drill_blast_probe__.md")
        body = "drill blast-radius probe -- created and deleted by drill.py\nMARKER-ONCE\n"
        LA.blast_reset()
        try:
            os.makedirs(os.path.dirname(probe), exist_ok=True)
            with open(probe, "w", encoding="utf-8") as fh:
                fh.write(body)
            rel = "handoff/__drill_blast_probe__.md"

            # 1 -- THE PROBE REALLY WOULD HAVE PATCHED. Writable surface, off every denylist,
            #      find string occurring exactly once. Without this arm a cap-shaped refusal
            #      could be any of the four earlier gates wearing the wrong message, and a
            #      probe that never gets as far as the charge is what caused this halt.
            staged = LA.t_propose_patch(rel, "MARKER-ONCE", "MARKER-TWICE",
                                        why="drill", apply=False)
            if not (isinstance(staged, dict) and staged.get("staged") is True
                    and staged.get("applied") is False):
                return False
            if LA._BLAST["patches"] != 0:
                return False                  # a staged dry run must still cost no budget

            # 2 -- AND THE CAP REFUSES IT ANYWAY once the budget is gone. Both bounds are
            #      taken to zero, so the very first charge is over budget and the refusal
            #      arrives before anything is written -- which is what "the cap bites" means.
            LA.MAX_PATCHES_PER_RUN = LA.MAX_FILES_PER_RUN = 0
            # ORDER 247b173c78ee's CLASS, the eighth and last of them (2026-09-06). The cleanup
            # below already retires the WORK ORDER this refusal files -- but the refusal also
            # goes through `escalation.escalate` at MANAGER, and escalate calls `health.record`,
            # so an `escalation:MANAGER:LOCAL_AGENT_BLAST_CAP:...` row landed in the LIVE
            # state/failures.json on every drill run and nothing retired THAT. It stood at 39,
            # the drill-run count, exactly like the seven `silent:` rows. Two ledgers, one probe;
            # the order queue had the discipline and the failure ledger did not. The net still
            # asserts the refusal, the charge, and the untouched file, so nothing is suppressed.
            r = _deliberately_failing(
                lambda: LA.t_propose_patch(rel, "MARKER-ONCE", "MARKER-TWICE",
                                           why="drill", apply=True))
            if "blast-radius cap" not in str((r or {}).get("error", "")):
                return False
            if (r or {}).get("applied") is not False or LA._BLAST["patches"] != 1:
                return False                  # refused, and the charge was actually made
            with open(probe, encoding="utf-8") as fh:
                return fh.read() == body      # ... and the file it was refused on is untouched
        finally:
            LA.MAX_PATCHES_PER_RUN, LA.MAX_FILES_PER_RUN = keep_caps
            LA.blast_reset()
            # AND THIS ONE LEAKS INTO THE PUBLIC EXPORT. The probe lives under `handoff/`, which
            # is in `publish.COPY_DIRS`, so a removal that quietly failed would PUBLISH
            # `handoff/__drill_blast_probe__.md` to the public repo on the next cycle with
            # nothing anywhere recording why. It was `except OSError: pass` while the work-order
            # cleanup twenty lines below -- with a weaker consequence -- already noted its own
            # failure under a paragraph making exactly this argument. (Order 5442da43c9f8.)
            try:
                os.remove(probe)
            except OSError:
                import silence as _si
                _si.note("drill.py:blast-probe-cleanup")
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
                # `synthetic=True` -- the ORDER is real (the cap is a real safety that
                # fires on real runs, so it carries no reserved subject) and only THIS
                # closure is a rehearsal. The closer is the only actor that knows, so
                # the closer says so, and the row goes to the self-test log instead of
                # the paper trail. 314 rows of this one id were 10.6% of the trail.
                # Order c24fcbb8a291.
                WO.resolve_code("LOCAL_AGENT_BLAST_CAP", "drill self-test; not a real runaway",
                                by="drill.py", synthetic=True)
            except Exception:
                import silence
                silence.note("drill.py:blast-cap-cleanup")
    net(a, "a runaway is stopped by the blast-radius cap", blast_cap_bites,
        "five gate bypasses were found after the fact; this bounds the sixth without "
        "needing to know what it is")
    def the_cap_resets_per_run():
        """`blast_reset()` clears the WHOLE budget, both halves of it.

        IT ONLY EVER CHECKED ONE COUNTER, AND ONLY AFTER SOMETHING ELSE HAD ALREADY RESET IT
        (order 9ada7602a356, run #37). The net was `(LA.blast_reset() or True) and
        LA._BLAST["patches"] == 0`. `_BLAST` is `{"files": set(), "patches": 0}` and
        `blast_reset` clears both (module-level `_BLAST` and the `blast_reset` function itself in
        local_agent.py -- cited by symbol per order 0c7592915a48, not by line), but `files` was never looked at: the
        sweep charged the budget to `{"files": {"a.py", "b.py"}, "patches": 5}`, replaced
        `blast_reset` with one that clears `patches` and forgets `files`, and this net returned
        True -- leaving two of MAX_FILES_PER_RUN=8 permanently spent at the start of every
        subsequent run, which is verbatim the outage its own expectation names.

        And it was comparing 0 to 0 in any case: `blast_cap_bites` runs first and resets in its
        `finally`, so at the moment this net ran the counter it inspected was already clear
        whatever `blast_reset` did. A check whose subject is "the budget goes back to zero" must
        SPEND the budget first, or it is asking a question with only one possible answer.

        Charged directly rather than through `t_propose_patch`, deliberately: the charging path
        is `blast_cap_bites`' subject next door, and this net's is the release. It restores
        whatever it found, so a charge left over from anything else is not disturbed.
        """
        keep = (set(LA._BLAST["files"]), LA._BLAST["patches"])
        try:
            LA._BLAST["files"] = {"a.py", "b.py"}
            LA._BLAST["patches"] = 5
            LA.blast_reset()
            return LA._BLAST["patches"] == 0 and not LA._BLAST["files"]
        finally:
            LA._BLAST["files"], LA._BLAST["patches"] = keep
    net(a, "the cap resets per run, not per process", the_cap_resets_per_run,
        "a cap that never resets turns into an outage on a long-lived process")
    # The ALLOWLIST — the half that fails CLOSED. These paths are on no denylist at all; they are
    # refused because they are outside the agent's working surface, which is the property M24
    # showed a denylist cannot provide.
    net(a, "a path on NO denylist is still refused if it is outside the surface",
        lambda: denied("data/COVERAGE.json"),
        "a denylist fails open on anything nobody thought of; this is the closed half")
    net(a, "it cannot write into data/ at all", lambda: denied("data/WIKI_HOSTS.json"),
        "data/ is the corpus and its bindings; WIKI_HOSTS.json in particular decides which wiki "
        "every source is read from, so a write here redirects the whole library quietly")
    def cannot_write_an_unlisted_top_level_file():
        """A REAL FILE AT A NAME NOBODY LISTED, so the ALLOWLIST is what refuses it.

        This net used to point at `something_nobody_listed.txt`, which does not exist -- and
        `denied()` counted `no such file` as a refusal, so it reported HELD over an agent whose
        every gate had been deleted (order 5a24b2956be8, reproduced). It is the only net in this
        area that exercises the allowlist's fail-closed half against a name invented AFTER the
        lists were written, which is precisely the property a denylist cannot provide, so it is
        also the one that could least afford to be empty.

        The probe is created and deleted here, with the same discipline `blast_cap_bites` uses
        for `handoff/__drill_blast_probe__.md`: the repo ROOT is outside `codewatch`'s `src/`
        fingerprint, so no standing daemon bounces onto rc=17 for it, and it is outside
        `publish.COPY_FILES`, which is an explicit list of names, so it reaches no export. The
        marker occurs exactly once, so nothing but the writable-surface gate can be what
        refuses: with the allowlist in place the answer is `writable surface`, and with it
        removed the patch would be perfectly ordinary work.
        """
        probe = os.path.join(HERE, "__drill_unlisted_probe__.txt")
        try:
            with open(probe, "w", encoding="utf-8") as fh:
                fh.write("drill unlisted-name probe -- created and deleted by drill.py\n"
                         "MARKER-ONCE\n")
            return denied("__drill_unlisted_probe__.txt")
        finally:
            # Recorded, not swallowed, for the third time in this area: a failed removal leaves
            # `__drill_unlisted_probe__.txt` at the repository ROOT, which is the one place a
            # stray file is most likely to be read as somebody's work in progress.
            try:
                os.remove(probe)
            except OSError:
                import silence as _si
                _si.note("drill.py:unlisted-probe-cleanup")
    net(a, "it cannot write a brand-new top-level file",
        cannot_write_an_unlisted_top_level_file,
        "the test that matters: a path invented AFTER the lists were written")

    # THE SEVENTH FAMILY, and it is not a path at all (order f29382aa7911, landed
    # 2026-09-06 from handoff/nets_20260906/safety.py).
    def an_empty_find_is_not_a_location():
        """`str.count("")` returns len(s) + 1, which is 1 for the empty string alone -- so on a
        ZERO-BYTE target the uniqueness test passed, and `"".replace("", replace, 1)` is just
        `replace`. The model writes arbitrary content into a file without having read a byte of
        it.

        NOT A GATE BYPASS, and the net says so: the target still has to pass every allow/deny
        gate and must already exist, so no protected file is reachable and no new file is
        created. What is lost is the CONTRACT the tool's own description and the SYSTEM prompt
        both state -- an exact unique find string copied verbatim from the file -- which is the
        thing that makes a patch evidence that the model read its target.

        `apply=False` throughout: the staged/refused verdict is the whole assertion, and a net
        about a write gate must not be the thing that writes. The probe file is created and
        removed inside the drill's own handoff scratch, which is on the writable surface, so the
        gates under test are the real ones."""
        import local_agent as LA
        rel = "handoff/__drill_empty_find__.txt"
        full = os.path.join(HERE, rel.replace("/", os.sep))
        try:
            open(full, "w", encoding="utf-8").close()          # genuinely zero bytes
            r = LA.t_propose_patch(rel, "", "content never read", apply=False)
            if r.get("applied") is not False or "not a location" not in (r.get("error") or ""):
                return False
            if r.get("staged") or os.path.getsize(full) != 0:
                return False
            # ... and no honest patch is affected.
            with open(full, "w", encoding="utf-8") as f:
                f.write("alpha beta gamma\n")
            if LA.t_propose_patch(rel, "beta", "delta", apply=False).get("staged") is not True:
                return False
            miss = LA.t_propose_patch(rel, "zzz-not-present", "x", apply=False)
            return "occurs 0 times" in (miss.get("error") or "")
        finally:
            # THIS ONE LEAKS INTO THE PUBLIC EXPORT TOO (order 749597eb95d4). The probe lives
            # under `handoff/`, which is in `publish.COPY_DIRS`, and `_is_agent_scratch` refuses
            # only `.py`/`.pyw`/`.pyi` -- a `.txt` is copied. `blast_cap_bites` twenty lines up
            # makes exactly this argument about its own probe and records a failed removal
            # rather than swallowing it; this one still did. Same note, same discipline.
            try:
                os.remove(full)
            except OSError:
                import silence as _si
                _si.note("drill.py:empty-find-probe-cleanup")
    net(a, "an empty find string is refused, with its own reason",
        an_empty_find_is_not_a_location,
        "find_symbol, read_file and the uniqueness test are the three things standing between "
        "this lane and a model editing what it has not looked at, and one of them had a hole "
        "exactly one byte wide")


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

    IT NO LONGER ATTACKS THE OWNER'S HALT (order 9495caa65d06). This called the REAL `clear()`
    four times against the LIVE `state/HALT.json`, and the only thing between it and lifting a
    standing halt was the very guard it exists to test. `clear()` validates the ruling, then
    `_by_a_person_at_the_cli()`, then `status()`, then writes `cleared: true`. The ruling here
    is a real 47-character sentence ON PURPOSE, so the first check is passed deliberately --
    which left the caller-identity check as the sole run-time barrier, and that check is
    precisely the thing that has failed if this net is ever going to refuse. A regression in it,
    or a reordering that put the caller check after the status read, turned this net into the
    thing it forbids: four lifts of the owner's halt, followed by a breach that raised a fresh
    halt over the one it had just cleared.

    The old answer to that was a line of prose -- "CHECKED AGAINST THE SOURCE BEFORE IT WAS RUN"
    -- an assurance taken once, at authoring time, against a function whose own docstring says
    "Order of refusals is part of what is tested here". An assurance about code that is expected
    to be edited is a comment, not a safety.

    So the probes now run against a SCRATCH halt file, exactly as `_halt_fails_closed` does, and
    drill.py has removed this same shape from itself twice before with the reasoning written out
    at length: `_gates_agree` (run #31) wrote the live config.yaml, and `_step4_needs_its_plan`
    renamed the owner's STEP4_PLAN.md. Even a completely broken caller check now cannot reach
    the owner's halt.

    AND THE NET GOT THE PROPERTY IT WAS MISSING. A synthetic STANDING halt is written into the
    scratch file first, and after the four probes the file is asserted BYTE-IDENTICAL to what
    was written. An exception coming back proves only that something refused; comparing the
    bytes proves the refusal happened BEFORE any write, which is the actual guarantee -- a
    `clear()` that wrote the file and then raised would have satisfied the old net completely.

    The two `ValueError` nets above stay exactly where they are: they pin the ORDER of the
    refusals, which `clear()` deliberately preserves and documents.

    `drill.py` calls the real `clear()` deliberately, in several places, precisely to prove each
    spelling of a programmatic lift is refused -- which is why `verify_math`'s AST check exempts
    this file by name rather than by counting call sites. (Order 036d9ca295ad: this sentence
    used to claim ONE call site, a count that was true when written and had drifted to fifteen
    live sites plus three exec-compiled ones by the time it was checked. A count in prose is a
    number that moves; what stays true is the reason for the exemption.)
    """
    import escalation as _alias
    from escalation import clear as _fromimport
    r = "a ruling long enough to pass the written-ruling check"
    real = ESC.HALT_FILE
    d = tempfile.mkdtemp(prefix="drill_runtime_clear_")
    scratch = os.path.join(d, "HALT.json")
    standing = json.dumps({"raised_at": 0.0, "code": "DRILL_SYNTHETIC_HALT",
                           "what": "a synthetic standing halt, so the four probes below have "
                                   "something to fail to lift",
                           "evidence": None, "source": None, "by": "drill.py",
                           "cleared": False, "ruling": None, "also": []},
                          indent=1, ensure_ascii=False)
    try:
        with open(scratch, "w", encoding="utf-8") as fh:
            fh.write(standing)
        ESC.HALT_FILE = scratch
        refused = all(_refuses(c, PermissionError) for c in (
            lambda: ESC.clear(r), lambda: _alias.clear(r),
            lambda: getattr(ESC, "clear")(r), lambda: _fromimport(r)))
        with open(scratch, encoding="utf-8") as fh:
            untouched = fh.read() == standing
        return refused and untouched
    finally:
        ESC.HALT_FILE = real
        shutil.rmtree(d, ignore_errors=True)


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

    AND THE FIFTH SPELLING IS A LOCAL VARIABLE (order f016ae5433b1, run #37). `f =
    escalation.clear` followed by `f(ruling)` walked past all four checks, confirmed by test:
    every one of them looks at the CALL, and in that shape the call names nothing this scan
    recognises. Binding the function to a name is now tracked to a fixpoint, so a chain
    (`f = escalation.clear; g = f; g(...)`) is caught too, along with a bound
    `getattr(escalation, "clear")`.

    FILED MINOR AND FIXED ANYWAY. The real guarantee is `clear()`'s own caller-identity check
    at run time, which no alias defeats and which `_no_runtime_clear` attacks directly; this
    scan is defence in depth, meant to catch the attempt while a person reads the diff. But a
    defence-in-depth layer everybody knows is porous is a layer nobody consults, and then it is
    not there for the case it was written for.

    AND IT ONLY EVER READ THE TOP LEVEL OF src/ (order cf9ee9000be8, run #37). `os.listdir` is
    not a walk, and `src/deprecated/` holds a module; a real programmatic lift placed there was
    invisible to a net whose name is "no module in src/ calls the halt's release". Now
    `_src_py_files` walks, so the sanctioned exemptions have to be matched on the FILE rather
    than on a bare name -- a `deprecated/escalation.py` must not exempt itself by basename.
    """
    import ast
    src = src or os.path.dirname(os.path.abspath(__file__))
    for f, full in _src_py_files(src):
        if f in ("escalation.py", "drill.py"):
            continue
        try:
            with open(full, encoding="utf-8") as fh:
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

        def _is_the_release(v, direct=direct, mods=mods):
            """Is this expression the `clear` FUNCTION ITSELF, handed around as a value?"""
            if isinstance(v, ast.Attribute) and v.attr == "clear":
                return isinstance(v.value, ast.Name) and v.value.id in mods
            if isinstance(v, ast.Name):
                return v.id in direct
            if (isinstance(v, ast.Call) and isinstance(v.func, ast.Name)
                    and v.func.id == "getattr" and len(v.args) >= 2
                    and isinstance(v.args[0], ast.Name) and v.args[0].id in mods
                    and isinstance(v.args[1], ast.Constant) and v.args[1].value == "clear"):
                return True
            return False

        # A NAME BOUND TO THE FUNCTION IS THE FUNCTION. To a fixpoint, so an alias of an alias
        # is caught as well; `direct` is what every call check below already consults.
        grew = True
        while grew:
            grew = False
            for n in ast.walk(tree):
                if not isinstance(n, ast.Assign) or not _is_the_release(n.value):
                    continue
                for t in n.targets:
                    # PLAIN NAMES ONLY. `obj.clear = x` binds an attribute, not a local, and
                    # walking into it would mark `obj` itself as the release function.
                    if isinstance(t, ast.Name) and t.id not in direct:
                        direct.add(t.id)
                        grew = True

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
        lambda: not redacted("password = correct horse battery"),
        "the entropy arm above has to be able to say NO: a scrubber that redacts every line "
        "with the word password in it redacts this project's own documentation, and a gate "
        "that cries wolf on every run is one somebody switches off")
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
    net(a, "a live maintenance shift stops the cycle", _a_live_maintenance_shift_stops_publishing,
        "at 22:16:29 five source files belonging to three agents two minutes into their work "
        "went to a PUBLIC repo, and forty-one more at 22:26:58")
    net(a, "an absent, broken or dead maintenance guard still PUBLISHES",
        _a_broken_maintenance_guard_fails_open,
        "failing closed here lets one malformed JSON file wedge the publisher silently and for "
        "ever, which is worse than one cycle of half-finished source the next cycle overwrites")
    net(a, "the publish loop re-asks the HALT every cycle and stops when it stands",
        _the_loop_reasks_the_halt,
        "main() asserted it once at startup, so an OWNER halt raised while the daemon was up "
        "never reached it and it kept pushing to the PUBLIC repo on its timer; codewatch does "
        "not cover this, because a halt is stale STATE and not stale CODE")
    net(a, "the publish loop actually ASKS the maintenance gate", _the_loop_asks_the_gate,
        "a predicate nothing calls is a comment; the guard has to be upstream of sync_tree, "
        "which is where the bytes are taken")


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

    THE SEAM ARM USED TO GUESS WHERE THE SEAM WAS (orders 73264e58fdeb and a51a546185ec, filed
    separately against the same line). It read `seam = P._SCAN_BLOCK and 2_000_000  # the default
    line cap`, and every clause of that was wrong about something. `_SCAN_BLOCK` is 262,144 and
    is the READ-BLOCK size, not the line cap; the conjunct never changes the result, so the
    expression is the literal `2_000_000` for any truthy `_SCAN_BLOCK`; and that literal is a
    hand-copy of `scan_for_secrets`'s `max_bytes` default living in a different module. Two ways
    to fail, in opposite directions. If `_SCAN_BLOCK` were renamed or made falsy, `seam` becomes
    0 or None, the slice raises, and `net()` records a raised attack as a BREACH -- an OWNER halt
    over a constant rename somewhere else. And if the default simply MOVED, the credential at
    1,999,990 would land in the middle of a segment, the arm would silently stop being a seam
    test, and the net would report HELD over a scanner that could no longer see a secret across a
    boundary. Measured before the change: with the segment at 300,000 and `_SCAN_OVERLAP` cut to
    8 -- the overlap repair effectively deleted -- the old fixture still returned True.

    So the cap is CHOSEN AND PASSED IN. `only()` hands `max_bytes` to the scanner and the
    fixture is built from that same local, which makes the straddle true by construction and
    makes this arm cheap (600 KB rather than three megabytes) into the bargain. The oversized
    arms keep the real default, since their claim is about files nobody sized for the scanner.
    (`_SCAN_OVERLAP = 0` is NOT the regression to test against: `seg[-0:]` is the whole segment,
    so a zero overlap carries everything forward rather than nothing. A short non-zero overlap is
    the honest deletion, and 8 is what this was watched go red against.)
    """
    import shutil
    import publish as P
    d = tempfile.mkdtemp(prefix="scanbig_")
    filler = "the custodian recorded the specimen in the usual manner. "
    try:
        def only(name, body, cap=None):
            for f in os.listdir(d):
                os.remove(os.path.join(d, f))
            with open(os.path.join(d, name), "w", encoding="utf-8") as fh:
                fh.write(body)
            return (P.scan_for_secrets(d, max_bytes=cap) if cap is not None
                    else P.scan_for_secrets(d))

        long_line = filler * 55_000                     # ~3.1 MB, no newline anywhere
        # AND THE "MULTI-LINE" ARM HAD NO LINE BREAKS IN IT (order 010eedfe1c47). `filler`
        # contains no newline, so `filler * 40_000 + _AWS_EXAMPLE + "\n"` was ONE ~2.36 MB
        # logical line with the only newline at the very end -- structurally identical to
        # `long_line` below, which the comment beside it calls "no newline anywhere". Both
        # therefore took `_scan_units`'s overlapping-SEGMENT branch, since that branch is
        # entered by a logical line longer than `line_cap` and not by a large file. So this
        # arm tested the same code shape as the next one, and the genuinely different case --
        # the ordinary file of many short lines that only crosses `max_bytes` in AGGREGATE,
        # which is the likely shape of the incident's own examples (a 2.97 MB citations file, a
        # 2.68 MB terminal page) -- drove nothing here. `_scan_units`'s per-line yield and its
        # `for mid in parts[1:-1]` had no regression cover in this file at all. Real breaks now.
        multi_line = "\n".join([filler] * 40_000)       # ~2.3 MB, 40,000 ordinary short lines
        # The two oversized arms take the REAL default, because "size is not a reason to skip"
        # is a claim about what the scanner does to files nobody sized for it.
        if not only("big.md", multi_line + _AWS_EXAMPLE + "\n"):
            return False
        if not only("register.json", _AWS_EXAMPLE + long_line):
            return False
        # THE SEAM ARM CHOOSES ITS SEGMENT SIZE instead of guessing it, so the credential
        # straddles by construction whatever the module default happens to be.
        seam = 300_000
        straddling = (long_line[:seam - 10] + _AWS_EXAMPLE
                      + long_line[:seam])              # material on the far side of the cut
        if not only("minified.js", straddling, cap=seam):
            return False
        return not only("clean.md", multi_line)
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
    """No handler around publish.py's safety imports may FALL THROUGH. All three wrapped a SAFETY.

    `ledger_guard`, `escalation` and the `mutate` interlock were each imported under a bare
    `except ImportError: pass`, so deleting, renaming or breaking any one of those modules
    silently switched its guard off in the job that pushes to a PUBLIC repo -- and the mutation
    interlock exists precisely because a push once shipped a deliberately corrupted
    `prose_gate.py` to GitHub. The swallow made the interlock's own absence the condition under
    which it stops working, which is the one condition it has to survive.

    Asked of the AST because that is the lesson of the same morning: `_no_programmatic_clear`
    breached today on a COMMENT quoting the strings it grepped for, and a `grep -c` here would
    fail the same way the first time somebody writes the phrase in a docstring explaining why it
    is banned. A handler passes only if it ENDS THE FLOW.

    AND IT USED TO ENUMERATE ONE EXCEPTION NAME, WHICH IS THE WHOLE HOLE BACK (order
    46aa5a5eac38). Handlers were selected by looking for the literal Name `ImportError` in
    `handler.type` and `continue`ing past every handler where it was absent -- so `except
    ModuleNotFoundError`, which is the exception Python ACTUALLY raises for a missing module and
    is an ImportError subclass, was never examined at all, and neither was a bare `except:`,
    whose `handler.type` is None. MEASURED, not argued: a copy of this file's `publish.py` with
    all four handlers respelled `except ModuleNotFoundError as ...` returned True, and the same
    copy with the raise in the MUTATION-INTERLOCK arm neutralised ALSO returned True -- a handler
    swallowing the interlock's own absence, on the path that pushes to a PUBLIC repo, reported
    HELD.

    THE REMEDY IS THE HOUSE ONE, TAKEN FROM `_meta_ban_has_no_fall_through`, which states its
    invariant as "no handler falls through" precisely because "`except ModuleNotFoundError`,
    `except (ImportError, AttributeError)`, or a bare `except:` added later would each pass it
    while reopening exactly this hole". So the handlers are selected by SHAPE, never by the name
    of an exception class: the try blocks that matter are the ones whose OWN BODY imports
    `ledger_guard`, `mutate` or `escalation`, and the requirement is on the handler's last
    REACHABLE statement.

    DIRECTLY IMPORTS, and `directly` is load-bearing. `main()`'s whole cycle loop CONTAINS the
    re-import of `escalation` several levels down, and its `except PushHeld` / `except Exception`
    arms end in an assignment deliberately -- that is the loop's rc bookkeeping, not a swallowed
    safety -- so selecting on an `ast.walk` of the try body rather than on its own statements
    would report BREACHED against correct code, which this file's own rule calls worse than no
    net at all.

    AND THE LAST STATEMENT MUST BE A `raise`, NOT MERELY AN EXIT (order 1c1e61dbfea4, kept).
    `_meta_ban_has_no_fall_through` accepts `continue`/`return`/`raise` because it guards a loop
    that must go round again; here the handlers guard a PUSH TO A PUBLIC REPO, and every one of
    them is documented in `publish.py` as failing closed with a raise. Accepting a `return` would
    have re-admitted the exact fixture order 1c1e61dbfea4 was filed for -- `except ImportError:
    print(...); return None` with a dead `raise` beneath it -- which was measured GREEN against
    the looser form while this repair was being written. A `return` also stops the push, but it
    hands `main()` the same falsy answer as "nothing had changed", which is `PushHeld`'s own
    recorded defect: a run that reports rc=0 and no change while the ledger guard is off.

    SCOPED TO `push` AND `main`, and the scope is not a second list to maintain: it is read off
    the SAME tuple the `_reaches_call` floors below are built from, so the two halves of this net
    name the same entry points by construction. That scope is also what leaves
    `_mutation_observation` alone -- its handler ends `return None` on purpose, and its docstring
    records why that is not a swallow (`push()` refuses outright on an unimportable `mutate`, so
    a reading that could not be taken meets the same refusal one step later). A net that reached
    into it would be red against code the file argues for at length.

    THE RAISE MUST BE REACHABLE, NOT MERELY PRESENT (order 1c1e61dbfea4). This walked each
    handler with a plain `ast.walk`, which accepts a `raise` parked after a `return` or inside an
    `if False:` -- so `except ImportError: print(...); return None` with a dead `raise` beneath it
    read exactly like a handler that fails closed. That is the same defeat orders c54a22a4e6fc
    and 78f04bec15ad removed from four other nets in this file, and the instrument for it
    (`_live_stmts`) was already sitting upstairs unused by this one. The no-fall-through rewrite
    above keeps that property and needs only the last live statement, so the walk over the whole
    handler body is gone with the enumeration it served.

    AND THE CENSUS WENT, BECAUSE IT BREACHED ON AN IMPROVEMENT. The last line was
    `return arms >= 3`, a floor on HANDLERS PRESENT. Making any one of `ledger_guard`,
    `escalation` or `mutate` an unconditional top-level import -- strictly stronger, since there
    is then no handler left to swallow anything -- drops the count and returns False, and a False
    here is a breach, and a breach raises an OWNER halt. The library would stop because somebody
    made a guard harder to switch off. This file names that hazard in its own words a few hundred
    lines up ("a net that goes red when a guard is improved teaches people to stop improving
    guards") and order 8ee268ce32cc exists for it.

    The docstring's worry was real, though: a for-all over handlers is satisfied vacuously by a
    file with no handlers. The answer is to assert what must still BE THERE rather than to count
    the handlers. So the floor is now on GUARDS PRESENT -- the three interlocks must be REACHABLY
    CALLED from the entry point each one actually guards -- which is the guarantee anybody
    actually wants and which no amount of import-hardening can take away.
    """
    import ast
    src = path or os.path.join(os.path.dirname(os.path.abspath(__file__)), "publish.py")
    with open(src, encoding="utf-8") as f:
        tree = ast.parse(f.read(), filename="publish.py")
    # THE THREE INTERLOCKS, EACH WITH THE DOOR IT STANDS BEHIND. Both halves below read this one
    # tuple: the handler check scopes itself to these entry points, and the floor asserts these
    # calls are reachable from them, so the two cannot come to mean different things.
    SAFETIES = (("ledger_guard.assert_intact", ("push",)),
                ("mutate.active", ("push",)),
                ("escalation.assert_clear", ("main",)))
    modules = {want.split(".")[0] for want, _ in SAFETIES}
    doors = {e for _, entries in SAFETIES for e in entries}
    for fn in ast.walk(tree):
        if not isinstance(fn, (ast.FunctionDef, ast.AsyncFunctionDef)) or fn.name not in doors:
            continue
        for n in _live_walk(fn):
            if not isinstance(n, ast.Try):
                continue
            # ITS OWN STATEMENTS, not everything underneath it -- see `DIRECTLY IMPORTS` above.
            imported = set()
            for s in _live_stmts(n.body):
                if isinstance(s, ast.Import):
                    imported |= {al.name.split(".")[0] for al in s.names}
                elif isinstance(s, ast.ImportFrom) and s.module:
                    imported.add(s.module.split(".")[0])
            if not imported.intersection(modules):
                continue
            for h in n.handlers:
                # THE LAST REACHABLE STATEMENT, which is what makes the raise REACHABLE rather
                # than merely present (order 1c1e61dbfea4). `_live_stmts` drops whatever sits
                # after a `return`, so a dead `raise` beneath one cannot answer for the handler,
                # and an `if cond: raise` that falls through when `cond` is false does not answer
                # either -- which the old any()-over-the-walk accepted.
                live = _live_stmts(h.body)
                if not live or not isinstance(live[-1], ast.Raise):
                    return False
    # AND THE GUARDS THEMSELVES ARE STILL WIRED, each from the door it actually stands behind:
    # the ledger check and the mutation interlock inside `push()`, the plant-wide halt at the top
    # of `main()`. Removing a handler by hardening its import cannot fail this; deleting the
    # guard, or moving it into a branch nothing enters, does.
    return all(_reaches_call(tree, want, entries) for want, entries in SAFETIES)


def _maintenance_guard_fixture(d, name, body):
    """Write one guard-file fixture in a scratch dir and return its path.

    NEVER the live `state/MAINTENANCE_RUN.json`. A maintenance shift is holding that file right
    now; writing it -- even restoring it a millisecond later -- is a chance for the running
    publisher to read a heartbeat this drill invented and conclude the shift had crashed. The
    predicate takes `path` and `now` precisely so it can be asked about a fixture and a pinned
    clock instead, which also makes the 14m59s / 15m01s pair testable at all.
    """
    p = os.path.join(d, name)
    with open(p, "w", encoding="utf-8") as f:
        f.write(body)
    return p


def _a_live_maintenance_shift_stops_publishing():
    """THE FOURTH INTERLOCK. Nothing asked whether somebody was in the middle of EDITING src/.

    Measured on 2026-08-29 from the export repo's own commit log, while it was happening. The
    four cycles before the maintenance shift began moved no source at all -- 21:35, 21:45, 21:55
    and 22:06 are each "N data/site file(s)". Sixteen agents started editing disjoint modules at
    22:14. At 22:16:29, two minutes in, commit 5f0d5e1 pushed five source files -- compress_store,
    coverage, escalation, retry_synthesis, tuning -- to a PUBLIC repository; they belonged to
    three different agents and not one had finished, verified or self-checked. At 22:26:58,
    forty-one more. Twice in eleven minutes a public repo received an arbitrary instant of a
    sixteen-way concurrent edit.

    `push()` was already well defended and every one of those locks answers a DIFFERENT
    question: the scanner asks "is a secret staged", `mutate.active()` asks "is source being
    corrupted on purpose", `claim_singleton` asks "is there a second publisher", `assert_clear`
    asks "is the library halted" -- and that last is read once at startup, so a loop up for
    hours has stopped asking it.

    The REFUSAL half, on a fixture with `done:false` and a heartbeat one second old. Both live
    shapes are asked: a guard with an agent name on it and a bare minimal one, because the
    refusal must not depend on optional decoration.
    """
    import publish as P
    d = tempfile.mkdtemp(prefix="drill_maint_")
    try:
        now = 1_700_000_000.0
        named = _maintenance_guard_fixture(
            d, "named.json",
            json.dumps({"agent": "maintenance-shift", "done": False, "heartbeat": now - 1}))
        bare = _maintenance_guard_fixture(
            d, "bare.json", json.dumps({"done": False, "heartbeat": now - 60}))
        for p in (named, bare):
            busy, why = P.maintenance_shift_live(path=p, now=now)
            if busy is not True or not why:
                return False
        # ... and one second inside the limit is still live. The boundary is where a guard that
        # merely LOOKS at the heartbeat and a guard that compares it correctly come apart.
        edge = _maintenance_guard_fixture(
            d, "edge.json",
            json.dumps({"done": False, "heartbeat": now - (P.MAINTENANCE_HEARTBEAT_SECONDS - 1)}))
        return P.maintenance_shift_live(path=edge, now=now)[0] is True
    finally:
        shutil.rmtree(d, ignore_errors=True)


def _a_broken_maintenance_guard_fails_open():
    """FAILS OPEN, and this half is the one that is easy to forget.

    The opposite rule from `subsystem_stopped`, deliberately, and the asymmetry is the argument:
    a stop ledger's whole content is what must not run, so being unable to read it cannot be
    permission to run things. A maintenance guard's content is what somebody is BUSY WITH, and
    being unable to read it must not become a reason to stop publishing for ever. Failing closed
    here would let one malformed JSON file wedge the publisher silently and indefinitely, which
    is a worse outcome than one cycle of half-finished source that the next cycle overwrites.

    A net that only checked the refusal would let exactly that regression in unnoticed -- the
    wedge is silent, so nothing else in the tree would report it either.

    Eight ways of not being a live shift, every one of which must answer PUBLISH: the file is
    absent, it is not JSON at all, it parses to something that is not an object, it parses to a
    JSON STRING rather than an object, it says the run finished, it carries no heartbeat at all,
    its heartbeat is not a number, and its heartbeat is one second past the limit so the run is
    treated as crashed rather than live.

    THE COUNT IS STATED BECAUSE IT IS CHECKABLE, and it was wrong: this paragraph said "Six" and
    listed six while `cases` below held eight (order b99192e41488). The two it omitted -- the
    JSON string and the non-numeric heartbeat -- are separate labelled cases with their own
    fixtures, so the prose was understating the net it describes rather than overstating it, but
    a reader counting the list against the sentence would have concluded one of them was stale
    and had no way to tell which.
    """
    import publish as P
    d = tempfile.mkdtemp(prefix="drill_maintopen_")
    try:
        now = 1_700_000_000.0
        limit = P.MAINTENANCE_HEARTBEAT_SECONDS
        cases = [
            ("absent", os.path.join(d, "there-is-no-such-file.json")),
            ("not json", _maintenance_guard_fixture(d, "bad.json", "{ not json at all")),
            ("not an object", _maintenance_guard_fixture(d, "list.json", "[1, 2, 3]")),
            ("a string", _maintenance_guard_fixture(d, "str.json", '"done"')),
            ("finished", _maintenance_guard_fixture(
                d, "done.json", json.dumps({"done": True, "heartbeat": now - 1}))),
            ("no heartbeat", _maintenance_guard_fixture(
                d, "nobeat.json", json.dumps({"done": False}))),
            ("heartbeat is not a number", _maintenance_guard_fixture(
                d, "strbeat.json", json.dumps({"done": False, "heartbeat": "just now"}))),
            ("crashed", _maintenance_guard_fixture(
                d, "old.json", json.dumps({"agent": "a shift that died",
                                           "done": False, "heartbeat": now - (limit + 1)}))),
        ]
        for _label, p in cases:
            # ORDER b53dd5b3f76f: one of these eight fixtures ("not json") is the only one that
            # reaches `maintenance_shift_live`'s except-Exception arm, which calls
            # `note("publish.py:maintenance-guard")` -> `health.record` and wrote a
            # `silent:publish.py:maintenance-guard:JSONDecodeError` row into the LIVE
            # state/failures.json on every drill run. Measured 2026-09-06 at 39, the drill-run
            # count. Wrapping the whole loop rather than only that fixture keeps the probe honest
            # if another case later grows an unreadable shape -- the net still asserts the
            # VERDICT (`busy is False` with a reason), so nothing under test is suppressed.
            busy, why = _deliberately_failing(
                lambda p=p: P.maintenance_shift_live(path=p, now=now))
            if busy is not False or not why:
                return False
        return True
    finally:
        shutil.rmtree(d, ignore_errors=True)


def _the_loop_asks_the_gate(src=None):
    """A PREDICATE NOTHING CALLS IS A COMMENT. The gate has to be upstream of the copy.

    The two nets above prove `maintenance_shift_live` answers correctly. Neither of them would
    notice if `main()` stopped asking it -- which is the whole distance between "the guard
    exists" and "the guard is in effect", and the reason the manager-stop gate in `overnight.py`
    needed a second net of its own this same shift.

    ASKED OF THE PARSE TREE, in the same three parts as the launcher nets and through the same
    helper: the answer is BOUND, a reachable `if` conditioned on it leaves the lap by `continue`
    without copying anything, and every reachable `sync_tree()` sits outside that arm and after
    it. `sync_tree` is the right thing to be upstream of because the fault is the COPY -- the
    bytes are taken there and `push()` only ships what the copy already holds, so a gate read at
    push time is a gate read after the half-finished tree has already been captured.
    """
    import ast
    tree = _ast_of(os.path.join(_srcdir(src), "publish.py"))
    return _gate_precedes_spawn(tree, _defn(tree, "main"), "maintenance_shift_live",
                                "sync_tree", (ast.Continue,))


def _the_loop_reasks_the_halt(src=None):
    """The publish loop must re-ask the HALT every cycle, and STOP when it is standing.

    `main()` asserts the halt once at startup and that is where it stayed, so an OWNER halt
    raised by any other job while the daemon was up did not reach it: it went on committing and
    pushing the whole tree to the PUBLIC repo on its timer until somebody killed the process by
    hand (order 5905045ff433). `codewatch.exit_if_stale` does not cover this -- it fingerprints
    `src/` and a halt is data in a state file, so this is Hard Rule -1's "IN EFFECT" property in
    the dimension the codewatch fix did not close: the daemon has stale STATE rather than stale
    code, and no amount of src/ never changing will fix it.

    ASKED OF THE PARSE TREE, and in TWO parts, because either half alone is satisfiable by code
    that does not stop:

      1. a reachable call to `escalation.assert_clear` INSIDE the `while` body -- not merely
         somewhere in `main()`, which the startup assert already satisfies and which is exactly
         the state this net exists to refuse;
      2. a `break` reachable from a handler for `SystemHalted` inside that same loop. Catching
         the halt and continuing is worse than not catching it: a halted library must stop the
         publisher, not make it knock every ten minutes for ever.

    `assert_clear` is spelled through a loop-local alias on purpose (a deleted escalation.py
    must be a SystemExit there, not something the generic `except Exception` swallows), so the
    call is resolved through `_import_maps` rather than matched as text.
    """
    import ast
    tree = _ast_of(os.path.join(_srcdir(src), "publish.py"))
    main = _defn(tree, "main")
    if main is None:
        return False
    # `_live_walk`, NOT `ast.walk` -- the net was written with the latter on 2026-08-30
    # and sweep39-batch02 defeated it the same day with the fixture this file already
    # knows by heart: a publish.py whose live `while True:` never asks the halt and
    # pushes for ever, with the `assert_clear` and its `except SystemHalted: break`
    # parked in a trailing `while False:`. The net said HELD; its neighbour
    # `_the_loop_asks_the_gate`, which goes through `_gate_precedes_spawn`, correctly
    # said False on the same file. DEAD CODE IS PROSE -- `_live_stmts` exists in this
    # module for exactly this and every sibling net uses it. Both walks are filtered:
    # the loop must be reachable, and so must the handler that breaks out of it.
    for loop in _live_walk(main):
        if not isinstance(loop, ast.While):
            continue
        if not _calls_within(tree, loop, "escalation.assert_clear", reachable=True):
            continue
        for handler in _live_walk(loop):
            if not isinstance(handler, ast.ExceptHandler) or handler.type is None:
                continue
            named = {n.attr for n in ast.walk(handler.type) if isinstance(n, ast.Attribute)}
            named |= {n.id for n in ast.walk(handler.type) if isinstance(n, ast.Name)}
            if "SystemHalted" not in named:
                continue
            if any(isinstance(x, ast.Break) for x in _live_stmt_walk(_live_stmts(handler.body))):
                return True
    return False


def _suppressed_still_visible():
    """A waived finding must appear in the scan output, tagged -- never silently vanish."""
    import publish as P
    # Scanned from the REPO ROOT, not from src/: `scan_for_secrets` reports paths relative to
    # the root it was given, and suppressions are written repo-relative (`src/drill.py`). Passing
    # src/ produced `drill.py`, which matched no suppression -- a probe that measured the wrong
    # thing and reported the guard broken.
    #
    # AND SCOPED TO WHAT ACTUALLY REACHES THE EXPORT (order 01a479a891a5, measured this shift).
    # The root has to stay HERE for the reason above, but the WALK does not: this net was
    # reading all 277,221 files under a 4.3 GB tree -- the mined corpus, the state logs, the
    # generated output, none of which is ever published -- and did not finish in four minutes.
    # One net dominating the runtime of the whole battery is a safety cost, not a performance
    # one: a battery that is expensive to run is a battery that gets run less often. `only=`
    # narrows the walk to publish's own COPY_DIRS/COPY_FILES, 552 files, which is the set the
    # push path stages and the set the suppression table is written against -- `src/drill.py`
    # and `handoff/*/AUDIT_*.md` both live inside it.
    hits = P.scan_for_secrets(HERE, only=P.COPY_DIRS + P.COPY_FILES)
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
        lambda: not LG.check_append_only("HANDOFF.md", "")[0],
        "the degenerate truncation, and the one a crashed writer produces by accident: an "
        "empty proposal contains nothing of what came before, so containment must refuse it")
    net(a, "a bug in BOTH Open and Resolved is caught",
        lambda: not LG.check_structure(
            "BUGS.md",
            "## Open\n### Major\n- **[m99] x**\n## Watching\n## Resolved (paper trail)\n"
            "- **[m99] x**\n" + "y" * 9000)[0],
        "run in this project by HAND at the end of every session; now it is a check")
    net(a, "a ledger that lost its sections is caught",
        lambda: not LG.check_structure("BUGS.md", "nothing here" * 900)[0],
        "the length check above would wave 10 KB of filler straight through; a BUGS.md with no "
        "Open, Watching or Resolved heading is a ledger nobody can read a bug out of")

    def ledger_loss_counts_duplicate_lines():
        """DELETING THE SECOND OF TWO IDENTICAL LINES IS DELETING A LINE.

        `_lost_fraction` compared `{set} - {set}`, so a removed line counted as lost only if its
        exact text appeared NOWHERE else in the file. In a markdown ledger that is a large
        exemption, not a corner: repeated headings, bare dates, `**Why:**`, the same one-line
        verdict under twenty entries. Measured on the real `handoff/HANDOFF.md` on 2026-09-03,
        733 substantive lines and 700 distinct -- 33 lines, 4.50% of the file, deletable for a
        measured loss of EXACTLY ZERO, against `MAX_LOST_FRACTION` of 0.05. This is the only
        gate `assert_intact()` puts in front of `publish.push()`.

        Attacked on a FIXTURE rather than on the live ledger, so the net measures the function
        and not today's contents of a file that changes every shift. Both halves are asserted,
        because a multiset that reports loss on a REORDER would be a new false alarm on a gate
        that must not cry wolf: eight lines, four of them the same line repeated, minus two of
        those repeats must read as 2/8; the same eight shuffled must read as 0.
        """
        import ledger_guard as LG
        old = "\n".join(["alpha", "**Why:**", "beta", "**Why:**",
                         "gamma", "**Why:**", "delta", "**Why:**"])
        # Two of the four duplicate lines removed; every distinct line still present.
        fewer = "\n".join(["alpha", "**Why:**", "beta", "**Why:**", "gamma", "delta"])
        shuffled = "\n".join(["delta", "**Why:**", "gamma", "**Why:**",
                              "beta", "**Why:**", "alpha", "**Why:**"])
        return (abs(LG._lost_fraction(old, fewer) - 0.25) < 1e-9
                and LG._lost_fraction(old, shuffled) == 0.0
                and LG._lost_fraction(old, old) == 0.0)
    net(a, "losing a DUPLICATED line still counts as loss", ledger_loss_counts_duplicate_lines,
        "a set diff let 33 lines of the real HANDOFF.md be deleted for a measured loss of zero, "
        "half a percentage point under the threshold that gates the public push")

    def the_writer_and_the_reader_of_a_snapshot_agree():
        """Every APPEND_ONLY name `seal()` writes must be a name `_read_snapshot()` can find.

        THE GATE THAT WAS DARK FOR A DAY AND SAID `ok` THE WHOLE TIME (order fc7f5b371e6e,
        found 2026-09-01). `seal()` FLATTENS a nested ledger name -- `handoff/HANDOFF.md` is
        written to `state/ledger_snapshot/handoff__HANDOFF.md`, deliberately, because the
        separator would otherwise send it into a subdirectory nothing creates.
        `_read_snapshot()` did not flatten. It opened `state/ledger_snapshot/handoff/HANDOFF.md`,
        got `FileNotFoundError`, and returned None -- which `check_since_snapshot` reads as
        "nothing has been sealed yet" and answers True to. The snapshot was on disk the entire
        time and correctly written; the reader was looking where the writer never writes.

        So append-only enforcement on `handoff/HANDOFF.md` was INERT from the moment that file
        joined `APPEND_ONLY` on 2026-08-31, and printed `SINCE LAST SEAL : ok` on every run in
        between. That is this project's oldest lesson wearing its most convincing disguise: a
        check that cannot fail looks exactly like a check that passed -- on the ledger whose own
        commentary records it having already lost 629 lines, and which `assert_intact()` gates
        `publish.push()` on.

        THE NET IS THE SHAPE, NOT THE ONE FILENAME. Asking "does `handoff/HANDOFF.md` work now"
        would pass forever and catch nothing the next time a name is added. What must hold is
        that the two functions agree for EVERY name in `APPEND_ONLY`, whatever those names
        become -- so a future nested entry cannot go dark the way this one did.
        """
        d = tempfile.mkdtemp(prefix="drill_snapshot_names_")
        with _ledger_redirected(d):
            for name in LG.APPEND_ONLY:
                p = os.path.join(d, name)
                os.makedirs(os.path.dirname(p) or d, exist_ok=True)
                with open(p, "w", encoding="utf-8") as fh:
                    fh.write("".join("line %d\n" % i for i in range(200)))
            LG.seal()
            for name in LG.APPEND_ONLY:
                if LG._read_snapshot(name) is None:
                    return False              # sealed, and the reader cannot find it
                ok, _ = LG.check_since_snapshot(name)
                if not ok:
                    return False              # a freshly sealed ledger must read as preserved
                # AND IT MUST STILL BE ABLE TO REFUSE. A reader that finds the snapshot but
                # compares nothing would pass the two checks above and be just as dark.
                with open(os.path.join(d, name), "w", encoding="utf-8") as fh:
                    fh.write("line 0\n")
                if LG.check_since_snapshot(name)[0]:
                    return False
            return True
    net(a, "the writer and the reader of a sealed snapshot agree, for EVERY append-only name",
        the_writer_and_the_reader_of_a_snapshot_agree,
        "seal() flattened a nested name and _read_snapshot() did not, so a missing file read as "
        "'nothing sealed yet' and the gate printed ok on every run for a day")

    def an_unparseable_chain_line_fails_the_chain():
        """A hash-chain line that will not parse must FAIL the chain, not be skipped past.

        `read_chain` used to `continue` past any line it could not parse -- inside the function
        whose entire job is detecting tampering. A dropped line is indistinguishable from a line
        that was never there, which is exactly what both an attacker and a torn write produce,
        and the chain then verified as a shorter chain that hangs together perfectly.

        Not hypothetical on this machine: `silence.append_line` was found the same day losing
        704 of 3,200 rows and tearing 3 more under concurrency, because `O_APPEND` is atomic on
        POSIX and a seek-then-write on Windows. Torn lines in an append-only ledger are a
        measured local phenomenon.

        THE FINAL LINE IS TESTED SEPARATELY, on purpose: it is both the likeliest to be torn (it
        is the one being written when a process dies) and the easiest for a loop to treat as an
        ordinary end-of-file.
        """
        d = tempfile.mkdtemp(prefix="drill_chain_torn_")
        with _ledger_redirected(d):
            os.makedirs(os.path.dirname(LG.CHAIN), exist_ok=True)
            for name in LG.APPEND_ONLY:
                p = os.path.join(d, name)
                os.makedirs(os.path.dirname(p) or d, exist_ok=True)
                with open(p, "w", encoding="utf-8") as fh:
                    fh.write("".join("line %d\n" % i for i in range(200)))
            LG.seal()
            LG.seal()
            with open(LG.CHAIN, encoding="utf-8") as fh:
                good = [ln for ln in fh.read().split("\n") if ln.strip()]
            if len(good) < 2 or not LG.verify_chain()[0]:
                return False                  # the honest chain must verify first
            for where in ("middle", "final"):
                torn = list(good)
                idx = 0 if where == "middle" else len(torn) - 1
                torn[idx] = torn[idx][: max(4, len(torn[idx]) // 2)]
                with open(LG.CHAIN, "w", encoding="utf-8") as fh:
                    fh.write("\n".join(torn) + "\n")
                if _deliberately_failing(lambda: LG.verify_chain()[0]):
                    return False              # a torn link read as an intact chain
            return True
    net(a, "a chain line that will not parse FAILS the chain, final line included",
        an_unparseable_chain_line_fails_the_chain,
        "read_chain skipped past unparseable lines inside the function whose job is detecting "
        "tampering, so a torn write verified as a shorter chain that hangs together perfectly")

    def an_acknowledged_shrink_is_carried_and_nothing_else_is():
        """The owner's ruling (a) on order be33a61be79f, attacked from every side it has.

        An acknowledgement must (1) stop the NAMED shrink failing the chain, (2) still REPORT it,
        (3) cover nothing outside its link range, (4) cover nothing for a ledger it does not
        name, and (5) be refused when malformed. A waiver that fails any of the last three is a
        blanket, and the ruling was explicit that this is not one. Driven in a redirected tree,
        never against the live chain (see `_ledger_redirected`, and why it exists).
        """
        d = tempfile.mkdtemp(prefix="drill_chain_ack_")
        with _ledger_redirected(d):
            def write_ledgers(n):
                for name in LG.APPEND_ONLY:
                    p = os.path.join(d, name)
                    os.makedirs(os.path.dirname(p) or d, exist_ok=True)
                    with open(p, "w", encoding="utf-8") as fh:
                        fh.write("".join("line %d\n" % i for i in range(n)))

            def ack(links, ledgers, reason="a written reason long enough to pass the floor set for one"):
                os.makedirs(os.path.dirname(LG.ACKNOWLEDGED), exist_ok=True)
                with open(LG.ACKNOWLEDGED, "w", encoding="utf-8") as fh:
                    json.dump([{"links": links, "ledgers": list(ledgers), "reason": reason,
                                "order": "drill", "by": "drill.py"}], fh)

            # ORDER 76e870e21631: THE ASSERTED COUNTS ARE DERIVED FROM APPEND_ONLY, NOT TYPED.
            # This used to hard-code 2 / 2 / 2 / 2 / 4 / 4 -- the counts that happen to fall out
            # of a two-entry APPEND_ONLY -- so a third append-only ledger joining the tuple
            # (exactly what "handoff/HANDOFF.md" itself did on 2026-08-31, per the sibling net
            # above) would make every one of those literals wrong and BREACH this net against a
            # correct change. `n` is the number of ledgers under test; the shrink at link 2
            # produces one problem per ledger (`n`), and the malformed-waiver case at (5)
            # produces one problem per ledger per shrinking link seen so far (`2 * n`, links 2
            # and 3). The five properties this net polices are unchanged by the substitution.
            n = len(LG.APPEND_ONLY)
            if n < 2:
                return False                                  # the net needs a shrink AND a range
            write_ledgers(200); LG.seal()                     # link 0
            write_ledgers(200); LG.seal()                     # link 1
            write_ledgers(100); LG.seal()                     # link 2: SHRANK (1 -> 2), all n
            ok, probs = LG.verify_chain()
            if ok or len(probs) != n:
                return False                                  # the shrink must fail unacknowledged
            ack([1, 2], LG.APPEND_ONLY)
            ok, probs, carried = LG.verify_chain(with_acknowledged=True)
            if not ok or probs or len(carried) != n:
                return False                                  # (1) stops failing, (2) still reported
            write_ledgers(50); LG.seal()                      # link 3: a NEW shrink (2 -> 3)
            ok, probs, carried = LG.verify_chain(with_acknowledged=True)
            if ok or len(probs) != n or len(carried) != n:
                return False                                  # (3) range covers nothing outside it
            ack([1, 3], [LG.APPEND_ONLY[0]])                  # widen the range, drop a ledger
            ok, probs, carried = LG.verify_chain(with_acknowledged=True)
            if ok or len(probs) != n or len(carried) != n:
                return False                                  # (4) the unnamed ledger still fails
            ack([1, 3], LG.APPEND_ONLY, reason="too short")
            # ORDER 630fe4529c51's CLASS, found 2026-09-06 but named by no order: case (5) writes
            # a DELIBERATELY malformed waiver, and `_load_acknowledgements` answers that with
            # `note("ledger_guard.py:acknowledgement-refused")` -> `health.record`, writing that
            # row into the LIVE state/failures.json on every drill run. It stood at 39, the
            # drill-run count. A refused waiver on the tamper-evident ledger chain is close to
            # the most alarming row this ledger can carry, and every one of them was this
            # rehearsal. The net still asserts the refusal, so nothing under test is suppressed.
            ok, probs = _deliberately_failing(LG.verify_chain)
            if ok or len(probs) != 2 * n:
                return False                                  # (5) malformed = refused = all fail
            ack([1, 3], LG.APPEND_ONLY)
            ok, probs, carried = LG.verify_chain(with_acknowledged=True)
            return ok and not probs and len(carried) == 2 * n  # and a proper one carries all
    net(a, "an acknowledged shrink is carried, still reported, and covers nothing beyond its name",
        an_acknowledged_shrink_is_carried_and_nothing_else_is,
        "ruling (a) on be33a61be79f: a fault a person has ruled on stops the presses no longer, "
        "is printed on every run and every push, and a waiver with no range, no ledger, no "
        "reason or no author acknowledges nothing")


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
        lambda: PL.verify_record_provenance(rec)[0] == "OK",
        "a provenance check that never returns OK reports the whole corpus as suspect, which "
        "is the same as reporting nothing")

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
        # THROUGH `_deliberately_failing`, AND IT IS THE ONLY PIPELINE-DRIVING NET HERE THAT WAS
        # NOT (sweep41-batch01, order 5fa88a896c3f). This probe's whole subject is a write that
        # did NOT land, so `gate_done`'s refusal branch runs for real: it writes a line to
        # `state/pipeline.log` and a `silent:pipeline.py:phase-not-marked-done` row into
        # `state/failures.json`, once per drill run, for ever -- `foreman.triage_swallowed`
        # deliberately never clears that ledger (order 842025c83c3c), so the litter is permanent.
        # Its two sibling nets below drive the SUCCESS path and leave no trace, which is exactly
        # why the omission was invisible: the net that manufactures the alarm is the one that
        # looks the same as the ones that do not.
        st = {"done": {}}
        _deliberately_failing(lambda: _quietly(
            lambda: PL.gate_done(st, "cosmology", [True, True, False, True])))
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

    def the_deprecated_cataloguer_still_refuses(src=None):
        """THE THIRD WRITER IS QUARANTINED, and nothing was watching the quarantine.

        `src/deprecated/catalogue_local.py` is a live entry point that writes
        `data/records/<slug>.json` with a bare `open(path, "w")` -- a third writer against the
        two-writer contract every other net in this area defends -- and rewrites the whole of
        `data/SWEEP_ROLL.json` non-atomically inside its per-source loop, so a Ctrl-C lands a
        truncated roll. What stopped it was a README until order 2bf50e1ae6ce put a refusal at
        the top of the file itself, above every path, so importing it stops as hard as running
        it. That order's own last line asked for this net (order ee3d4404718a).

        THE ATTACK THIS EXISTS AGAINST is somebody deleting the refusal because six lines at the
        top of a deprecated file nobody reads look exactly like dead code -- which is the shape
        of the 2026-08-25 incident, an autonomous run removing a safety it judged unnecessary.
        `_drill_never_writes_the_gate` is the precedent: a net whose whole job is to notice the
        reintroduction of a removed fault.

        BOTH HALVES, because each protects the other. Every argv, and none at all, must exit
        NON-ZERO and name `deprecated/README.md` ON STDERR. And `--help` must still exit ZERO:
        `allsweep.check_import` asks every module under `src/` for `--help` and grades a
        non-zero rc as a BROKEN IMPORT, and `sweep_plan._src_py_files` made this directory
        visible to that tier, so a bare refusal here files a MAJOR order against a module
        behaving exactly as designed -- order 2d6c9343cd32's mistake, which `cascade_bridge` was
        given an argv guard to escape. A net that only checked the refusal would push whoever
        fixed the resulting false order straight into removing the exemption.

        WHICH STREAM IT ARRIVES ON IS THE WHOLE DIFFERENCE, and the first version of this net
        did not ask. "Non-zero, and the words appear somewhere" is satisfied by
        `print(_REFUSAL)` over a `main()` left fully live -- the module says the right thing,
        runs anyway, and exits non-zero later for some unrelated reason of its own. Watched: the
        loose form reported HELD against exactly that mutant. `raise SystemExit(msg)` writes
        `msg` to STDERR; `print(msg)` writes it to STDOUT. So a refusal is a refusal only on
        stderr, and `--help`'s notice -- which is a message, not a refusal -- only on stdout.
        That is the line between stopping and merely mentioning, and it is the line this net is
        about.

        Run as a SUBPROCESS, not imported: the refusal is a module-level `SystemExit`, so
        importing it here would end the drill, and `sys.modules` would make a second ask
        meaningless anyway. Nothing is written by any of these five runs -- that is the claim.
        """
        import subprocess
        mod = os.path.join(_srcdir(src), "deprecated", "catalogue_local.py")
        if not os.path.isfile(mod):
            return False              # the quarantined module gone is not evidence of a refusal

        def ask(argv):
            r = subprocess.run([sys.executable, mod] + list(argv), capture_output=True,
                               text=True, errors="replace", cwd=HERE, timeout=300,
                               creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
            return r.returncode, (r.stdout or ""), (r.stderr or "")

        named = "deprecated/README.md"
        for argv in ([], ["--dry-run"], ["--limit", "3"], ["--only", "Bleach"]):
            rc, out, err = ask(argv)
            if rc == 0 or named not in err:
                return False
        rc, out, err = ask(["--help"])
        return rc == 0 and named in out
    net(a, "the deprecated cataloguer still refuses to run, and still answers --help",
        the_deprecated_cataloguer_still_refuses,
        "a README said 'do not run' for months while every entry point stayed fully live; the "
        "refusal that replaced it is six lines in a file nobody opens")


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


def _the_catalogue_merge_does_not_key_entries_on_name_alone():
    """`name` is not a per-entry identity, and a merge keyed on one loses two ways.

    ORDER b418b8b3be54. `write_record_catalogue` built its merge map as
    `{e.get("name"): e for e in rec["entries"]}` -- the exact expression order b67dc1990af6 had
    already removed from the twin, `write_record`, and left standing in the writer EVERY
    cataloguer goes through. Both losses were silent and both still returned True:

      (1) A REVERTED JUDGMENT. A duplicated name collapsed to whichever fresh entry the
          comprehension saw LAST, so every disk row of that name folded onto that one survivor
          and the others emerged with no judgment at all. Measured against the pre-fix code:
          the surviving row came out carrying BOTH rows' marks (`excluded` AND `catalogued`)
          while its twin came out `{}`.
      (2) A SHRUNK CAST. A disk row whose name was in the map was folded and never appended, so
          three identical-named disk rows merged to one -- against a docstring that promises in
          as many words that "a merge never shrinks a cast".

    MEASURED over data/records/*.json: 282,822 entries, 1,840 in duplicated-name groups, 935
    rows a name-keyed dict collapses, 65 of 216 records affected.

    THIS NET ATTACKS ALL THREE PROPERTIES OF THE FIX, because pinning only the easy one would
    let the other two rot:
      * judgments follow the RIGHT row when the fresh cast arrives REORDERED (the case ordinal
        pairing gets wrong, and the reason the twin's remedy does not transfer here);
      * the cast does not shrink when the triple genuinely cannot separate the rows;
      * the merge is IDEMPOTENT, so a re-catalogue cannot grow a record without bound -- the
        failure a naive "append everything unpaired" fix would introduce.

    A throwaway record in a temp directory. Nothing in `data/records/` is opened.
    """
    import shutil
    import silence as _S
    import pipeline as PL
    d = tempfile.mkdtemp(prefix="drilldup_")
    keep = (PL.log, PL.silence)
    try:
        PL.log = lambda *a, **k: None
        PL.silence = _quiet(_S)
        # (1) two rows share a name and are separated only by the rest of the triple; the fresh
        #     cast arrives in the OPPOSITE order to the disk copy.
        path = os.path.join(d, "dup.json")
        with open(path, "w", encoding="utf-8") as f:
            json.dump({"source": "drill", "entries": [
                {"name": "The Guitar", "type": "Thing", "description": "the red one",
                 "category": "M3", "excluded": True},
                {"name": "The Guitar", "type": "Thing", "description": "the blue one",
                 "category": "M7", "catalogued": True}]}, f)
        rec = {"source": "drill", "entries": [
            {"name": "The Guitar", "type": "Thing", "description": "the blue one"},
            {"name": "The Guitar", "type": "Thing", "description": "the red one"}]}
        if PL.write_record_catalogue(path, rec) is not True:
            return False
        with open(path, encoding="utf-8") as f:
            out = json.load(f)
        rows = {(e.get("name"), e.get("description")): e for e in out.get("entries") or []}
        if len(out.get("entries") or []) != 2:
            return False
        red = rows.get(("The Guitar", "the red one")) or {}
        blue = rows.get(("The Guitar", "the blue one")) or {}
        if red.get("category") != "M3" or not red.get("excluded") or red.get("catalogued"):
            return False
        if blue.get("category") != "M7" or not blue.get("catalogued") or blue.get("excluded"):
            return False
        # (2) rows the triple CANNOT separate: the cast must not shrink, and (3) re-merging the
        #     result against the same fresh cast must not grow it.
        p2 = os.path.join(d, "identical.json")
        same = [{"name": "Dup", "type": "T", "description": "same", "category": m}
                for m in ("M1", "M2", "M3")]
        with open(p2, "w", encoding="utf-8") as f:
            json.dump({"source": "drill", "entries": same}, f)
        rec2 = {"source": "drill",
                "entries": [{"name": "Dup", "type": "T", "description": "same"}]}
        if PL.write_record_catalogue(p2, rec2) is not True:
            return False
        with open(p2, encoding="utf-8") as f:
            first = len(json.load(f).get("entries") or [])
        if first < 3:
            return False
        rec3 = {"source": "drill",
                "entries": [{"name": "Dup", "type": "T", "description": "same"}]}
        if PL.write_record_catalogue(p2, rec3) is not True:
            return False
        with open(p2, encoding="utf-8") as f:
            second = len(json.load(f).get("entries") or [])
        if second != first:
            return False
        # (4) AN UNHASHABLE FIELD MUST NOT TURN A MERGE INTO THE FALL-THROUGH. The pairing key is
        # a dict key, and the fresh cast is not a trusted shape -- it comes from a wiki re-fetch
        # or a doc ingest. A list or dict in name/type/description would raise TypeError, and the
        # raise would land in this writer's `except Exception` arm, so the merge would silently
        # become whatever that handler does. Keying on three fields instead of one widened that
        # exposure, so the key coerces; this is the attack on that coercion.
        p3 = os.path.join(d, "unhashable.json")
        with open(p3, "w", encoding="utf-8") as f:
            json.dump({"source": "drill", "entries": [
                {"name": "X", "type": "T", "description": ["a", "list"], "category": "M1"},
                {"name": "X", "type": "T", "description": {"a": 1}, "category": "M2"}]}, f)
        rec4 = {"source": "drill", "entries": [
            {"name": "X", "type": "T", "description": ["a", "list"]},
            {"name": "X", "type": "T", "description": {"a": 1}}]}
        if PL.write_record_catalogue(p3, rec4) is not True:
            return False
        with open(p3, encoding="utf-8") as f:
            got = json.load(f).get("entries") or []
        if len(got) != 2:
            return False
        # and the judgments still landed on the RIGHT rows, not merely without raising
        return [e.get("category") for e in got] == ["M1", "M2"]
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
    net(a, "the catalogue merge does not key entries on name alone",
        _the_catalogue_merge_does_not_key_entries_on_name_alone,
        "the fold order b67dc1990af6 removed from write_record stood on in its twin: 935 rows a "
        "name-keyed dict collapses across 65 records, judgments stamped onto the wrong entity "
        "and a cast that shrank, against a docstring promising it never does")


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

    def the_validator_is_what_refuses_it():
        """THE TWO NETS ABOVE CANNOT TELL A REFUSAL FROM A CRASH, and for four days that was
        the whole of the fault (orders ed46a60bc2dc, 559b09f35e5c, 6f1652a21efb -- three
        separate filings against one line).

        `decode`'s pattern spelled its address and feature groups `[0-9a-z]`, the full
        36-character range, while `B32` is the 32-symbol Crockford set with i, l, o and u
        removed. So those four letters passed `re.fullmatch` cleanly, the
        `raise ValueError(f"not a world profile: {profile!r}")` written for exactly that case
        never fired, and execution carried on into `_unb32`, where `B32.index(ch)` raised a bare
        `ValueError: substring not found` from inside a private helper -- naming neither the
        profile nor the offending character.

        AND `_refuses(..., ValueError)` ACCEPTS BOTH, which is why two nets sat directly above
        this one asserting the right property and reporting HELD across every one of those four
        days. The string was refused either way and nothing decoded wrongly; what was wrong is
        WHICH LAYER refused it and with what. A net that asks only for the exception TYPE cannot
        see that difference, and the difference is the entire remedy.

        So this asks for the message. All four excluded letters, in both fields, and the
        refusal must be the validator's own -- it must name the profile it rejected, which
        `B32.index`'s cannot do because it never saw one.
        """
        import profile as _PR
        for bad in ("PS-i23-myc-0000-u0", "PS-1l3-myc-0000-u0", "PS-1o3-myc-0000-u0",
                    "PS-1u3-myc-0000-u0", "PS-123-myc-000i-u0", "PS-123-myc-l000-u0",
                    "PS-123-myc-00o0-u0", "PS-123-myc-000u-u0"):
            try:
                _PR.decode(bad)
                return False                   # accepted a character the encoder cannot write
            except ValueError as e:
                if "not a world profile" not in str(e) or repr(bad) not in str(e):
                    return False               # refused, but by `B32.index`, not the validator
        return True
    net(a, "a profile outside the alphabet is refused BY THE VALIDATOR, naming the string",
        the_validator_is_what_refuses_it,
        "the guard written for this case never fired; the string died four frames later inside "
        "a private helper, as 'substring not found', naming neither the profile nor the char")


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
    word appears at `withdraw_chapters.py:216-219` inside the paragraph that sits directly above the
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

    AND `_calls` READ THE WHOLE FILE, DEAD CODE INCLUDED (order 78f04bec15ad, run #37). The
    sweep handed this a `withdraw_chapters.py` that `shutil.move`s the chapters with no snapshot
    at all and carries `SNAP.before(...)` / `SNAP.verify(...)` after the `return`, and the net
    reported HELD -- the same defeat as the comment, one layer down: unreachable code makes
    exactly the claim a paragraph makes. Both calls must now be REACHED from `main`, the entry
    this script has, so neither dead code nor a helper nothing calls can answer for them. And
    the moves have to be reached from there too: a script that no longer moves anything is not
    evidence that a script which does takes a copy first.
    """
    p = path or os.path.join(os.path.dirname(os.path.abspath(__file__)),
                             "withdraw_chapters.py")
    tree = _ast_of(p)
    return (_reaches_call(tree, "shutil.move")
            and _reaches_call(tree, "snapshot.before")
            and _reaches_call(tree, "snapshot.verify"))


def _a_waived_partial_snapshot_still_records_what_it_missed():
    """`allow_missing=True` suppresses the refusal and NOTHING ELSE. -> bool.

    The waiver is the half that makes the partial-capture refusal survivable, and a waiver that
    also erased the record would be worse than no refusal at all: the caller would get an id, no
    exception, and a manifest that cannot say which of its paths were never taken. `requested`
    and `skipped` go in either way. Cleaned up by name, like the empty-snapshot litter above.
    """
    import shutil as _sh
    import snapshot as SNAP
    sid = None
    try:
        sid = SNAP.before("drill-partial", ["config.yaml", "no/such/path"], allow_missing=True)
        m = SNAP.manifest(sid)
        return (m.get("skipped") == ["no/such/path"]
                and "config.yaml" in (m.get("requested") or [])
                and bool(m.get("took")))
    finally:
        if sid:
            _sh.rmtree(os.path.join(SNAP.ROOT, sid), ignore_errors=True)


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
    # `snapshot.py`, which this file does not own.
    #
    # BY NAME AS WELL AS BY DIFFERENCE (order 64c8827cc72b, run #37). The cleanup was the set
    # difference of two `os.listdir`s across the window in which the net below runs, and it
    # rmtree'd EVERYTHING that appeared in it -- on the theory that a directory found by
    # difference is one this drill just made. It is not: `snapshot.before()` is a shared entry
    # point, and `withdraw_chapters.py` -- the caller this entire area exists for -- calls it.
    # A withdrawal that took its backup one second into that window had it deleted by the
    # drill. The comment three paragraphs down says the 151 pre-existing snapshots are left
    # alone because "deleting a backup somebody may be keeping is the owner's call"; the
    # difference-based sweep could do exactly that to a backup one second old.
    #
    # The refusal being tested uses a KNOWN LABEL, and `snapshot.before` builds its id as
    # "<label>-<epoch>", so the litter this makes is identifiable by name. Both guards are kept:
    # new in the window AND carrying the prefix. And the cleanup cannot take the run down --
    # failing to tidy up is not a fault, and killing the battery over it would lose 251 verdicts
    # to a permissions error on a scratch directory.
    _EMPTY = "drill-empty"
    _empty_before = set(os.listdir(SNAP.ROOT)) if os.path.isdir(SNAP.ROOT) else set()
    net(a, "an EMPTY snapshot raises rather than passing",
        lambda: _refuses(lambda: SNAP.before(_EMPTY, ["no/such/path"]),
                         SNAP.SnapshotFailed),
        "a snapshot that captured nothing is a missing one wearing the same name")
    # THE SIBLING OF THE NET ABOVE, and the case that actually happens (order f4193095edff).
    # All-or-nothing refusal fired only when NOTHING was captured, which is the one shape nobody
    # hits: ask for four paths where one is a typo, a renamed directory or a file not created
    # yet, and `before()` returned an id, `verify()` returned True, and the caller went ahead
    # with an irreversible step holding PART of what it asked for. A check that fires only in
    # the case nobody reaches is furniture. Three assertions, because the refusal is not the
    # whole fix: the manifest must record what was REQUESTED and what was SKIPPED either way --
    # that is what a restore six weeks from now has to read -- and `allow_missing=True` must
    # still be a way through for the caller who genuinely means "whichever of these exist",
    # since a guard that blocks correct work is a guard somebody deletes.
    net(a, "a PARTIAL snapshot raises too, not just an empty one",
        lambda: _refuses(lambda: SNAP.before(_EMPTY, ["config.yaml", "no/such/path"]),
                         SNAP.SnapshotFailed),
        "an irreversible step must not proceed on part of the copy it asked for, with nothing "
        "anywhere naming the part it did not get")
    net(a, "and allow_missing is still a way through, with the absences on the record",
        _a_waived_partial_snapshot_still_records_what_it_missed,
        "a guard that blocks the caller who genuinely means 'whichever of these exist' is a "
        "guard that gets an allow_missing=True typed in front of every call site")
    try:
        import shutil as _sh0
        for _new in (set(os.listdir(SNAP.ROOT)) - _empty_before
                     if os.path.isdir(SNAP.ROOT) else ()):
            if _new.startswith(_EMPTY + "-"):
                _sh0.rmtree(os.path.join(SNAP.ROOT, _new), ignore_errors=True)
    except OSError:
        import silence as _si0
        _si0.note("drill.py:empty-snapshot-cleanup")
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
            # Found 2026-09-06 by diffing state/failures.json across a full drill run, NOT by
            # reading code: `silent:silence.py:cas-target-changed` rose by 2 per run while the
            # eight known probe rows held flat. This is one of the two. The refusal under test
            # reaches `note("silence.py:cas-target-changed")` -> `health.record`, so the probe was
            # manufacturing the exact stale-write signal it exists to prove the library can raise.
            # `_deliberately_failing`'s docstring already names a `silence.py:cas-target-changed`
            # row it covers -- a DIFFERENT key from a different branch of the same module, which
            # is how this one stayed hidden behind an entry that looked like it.
            ok, _why = _deliberately_failing(
                lambda: S.replace_if_unchanged(tmp, dst, seen))
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

            THE SEAM MOVED, AND THIS NET WENT RED ON CORRECT CODE (2026-08-30). It used to take
            the denial from a stand-in for `S.replace_retry`, because `replace_if_unchanged`
            handed the rename to it. Order fede605db64f then moved the retry loop INTO
            `replace_if_unchanged` -- rightly: the compare and the swap have to be adjacent, and
            the sleeping helper between them was losing writes -- and `replace_retry` stopped
            being called from this path at all. The stand-in intercepted nothing, no denial
            could occur, `ok` came back True, and this net BREACHED against a fix. A net whose
            seam has moved measures nothing, and it is worse than an absent one because it
            halts the library while doing it.

            SO THE DENIAL IS NOW REAL, which the paragraph this replaces said no test could
            schedule. On Windows `os.replace` onto a file somebody holds open raises
            PermissionError -- CPython's `open` does not grant FILE_SHARE_DELETE -- so holding a
            read handle on the target drives the genuine `except PermissionError` branch rather
            than a mock of it, and there is no seam left to move. `attempts=1` so the real
            backoff (0.3 + 0.6 + 0.9 + 1.2 s) is not paid on every battery run. Off Windows,
            where an open handle does not deny a rename, `os.replace` is stood in for instead.

            The file must also be untouched afterwards: a reason is not evidence if the write
            happened anyway.
            """
            t3 = dst + ".tmp3"
            with open(t3, "w", encoding="utf-8") as f:
                f.write('{"v":"DENIED"}')
            before = open(dst, encoding="utf-8").read()
            expected = S.digest_of(dst)
            holder = saved = None
            if os.name == "nt":
                holder = open(dst, encoding="utf-8")
            else:
                saved = os.replace

                def _denied(_tmp, _dst):
                    raise PermissionError("stand-in: only Windows denies this for real")
                os.replace = _denied
            try:
                # ORDER 630fe4529c51: the denial this probe manufactures reaches
                # `note("replace-denied:" + basename(dst))` -> `health.record`, which wrote a
                # `silent:replace-denied:shared.json` row into the LIVE state/failures.json on
                # every drill run. Its sibling `the_loser_of_a_race_is_refused_mid_backoff`
                # right below drives the same function's refusal path and has always wrapped
                # the call; this one never did. Measured 2026-09-06: that key stood at 39, the
                # exact drill-run count, alongside seven others of the same shape.
                ok, why = _deliberately_failing(
                    lambda: S.replace_if_unchanged(t3, dst, expected, attempts=1))
            finally:
                if holder is not None:
                    holder.close()
                if saved is not None:
                    os.replace = saved
            return (ok is False and why != "landed" and "could not be renamed" in why
                    and open(dst, encoding="utf-8").read() == before)
        net(a, "a DENIED rename gives back the reason it was denied, not 'landed'",
            reason_matches_verdict,
            "runguard.claim() printed 'landed' for a write that did not land, because the "
            "reason string was returned unconditionally beside a False verdict")

        def the_loser_of_a_race_is_refused_mid_backoff():
            """THE COMPARE AND THE SWAP HAVE TO BE ADJACENT -- driven, not asserted.

            THE FAULT THIS REPRODUCES (order fede605db64f, repaired 2026-08-29).
            `replace_if_unchanged` digested the target ONCE and then handed the rename to
            `replace_retry`, whose backoff sleeps 0.3 + 0.6 + 0.9 + 1.2 seconds between
            attempts. A writer denied on its first try therefore compared the file at T and
            landed its bytes at T+3s, and ANY writer that got in during those three seconds was
            silently overwritten -- both of them told `(True, "landed")`. It cost this project
            two work-order closures on the shift that found it, each of which had already
            written a paper-trail entry, and they were watched reappear in the OPEN queue
            minutes later. That is this window running backwards.

            AND THE REPAIR HAD NO ADVERSARY. It was measured once -- three processes, forty rows
            each, 120 of 120 surviving where the old helper kept 55 to 86 -- and a measurement
            taken once is not a standing guard. `a stale write is REFUSED` above covers the
            plain race, where the change lands before the swap is ever attempted; nothing
            covered the one that actually bit, where the change lands DURING THE BACKOFF, after
            the digest the writer is holding was taken and before its rename succeeds. A compare
            that cannot fail is indistinguishable from a compare that passed, which is standing
            lesson 9 and the reason this file exists.

            SO THE SEQUENCE IS DRIVEN END TO END, in the order it happened: the loser reads its
            digest, its first `os.replace` is DENIED, the other writer lands its bytes while the
            loser is in the backoff, and nothing stands between the loser and a successful
            rename on its next attempt EXCEPT the re-digest. Four assertions, and the last two
            are what make it evidence rather than a story: the retrying writer is REFUSED, the
            reason says the file changed under it rather than that anything landed, the winner's
            bytes are still on disk afterwards, and `os.replace` was reached exactly ONCE -- the
            second rename was never attempted, because the compare ran before it. A reason is
            not a refusal if the write happened anyway.

            THE DENIAL IS STOOD IN FOR, AND ONLY THE DENIAL. `reason_matches_verdict` above
            already drives a genuine Windows PermissionError through this function, so the
            handler is proved real next door; what this net needs is a denial it can schedule an
            event INSIDE, which no held handle can give it. Everything the net actually asserts
            -- that the loop re-digests before its second rename, and refuses -- runs for real,
            and the stand-in is released before anything is read back. It is also the same seam
            the sibling uses off Windows, so there is no new one.

            WATCHED GO RED against the pre-fix shape (digest once, then hand the rename to
            `replace_retry`): the loser is told `(True, "landed")` and the winner's bytes are
            gone.

            The three callers whose correctness rests on this: `workorders._mutate` (the work
            order queue itself), `endpoint.register`, and `runguard.claim`.
            """
            race = os.path.join(d, "raced.json")
            with open(race, "w", encoding="utf-8") as f:
                f.write('{"v":"original"}')
            held = S.digest_of(race)             # what the losing writer read, before the race
            loser = race + ".loser"
            with open(loser, "w", encoding="utf-8") as f:
                f.write('{"v":"STALE LOSER"}')

            saved, attempts_seen = os.replace, []

            def denied_once_then_allowed(tmp, dst):
                attempts_seen.append(1)
                if len(attempts_seen) == 1:
                    # The other writer lands its work in the window the backoff opens. This is
                    # the whole fault: on the old shape the digest was already taken and would
                    # not be taken again, so these bytes were about to be overwritten silently.
                    with open(race, "w", encoding="utf-8") as fh:
                        fh.write('{"v":"WINNER"}')
                    raise PermissionError(13, "a reader is holding the target open")
                return saved(tmp, dst)

            os.replace = denied_once_then_allowed
            try:
                # Wrapped because the REFUSAL calls `silence.note`, which would put
                # `silent:silence.py:cas-target-changed` into the library's operational ledger
                # once per drill run -- in the file a person reads to find out what is actually
                # going wrong. Same reason as the two probes in `drill_recorders_and_lane`; see
                # `_deliberately_failing`. The raise is what is asserted, never the ledger row.
                ok, why = _deliberately_failing(
                    lambda: S.replace_if_unchanged(loser, race, held, attempts=3))
            finally:
                os.replace = saved

            with open(race, encoding="utf-8") as fh:
                on_disk = fh.read()
            # EXACTLY ONE RENAME WAS ATTEMPTED, and that is the sharp end of it: the second
            # attempt never reached `os.replace` at all, because the re-digest at the top of the
            # loop stopped it. On the old shape the digest was taken once, outside the loop, and
            # this second rename went through.
            return (len(attempts_seen) == 1 and ok is False
                    and "changed under this writer" in (why or "")
                    and on_disk == '{"v":"WINNER"}')
        net(a, "a writer whose target changed DURING ITS BACKOFF is still refused",
            the_loser_of_a_race_is_refused_mid_backoff,
            "the compare and the swap were three seconds of sleep apart, so both writers were "
            "told they landed and one of them had not -- two work-order closures with paper "
            "trail entries were lost to exactly this and watched reappear in the open queue")
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


def _a_boolean_is_not_a_score():
    """`True` must not be accepted as an axis score of 1.0. -> bool.

    Every numeric-score gate in `magnitude.py` was `isinstance(x, (int, float))`, and `bool` is
    a subclass of `int` -- so a model answering the `score` field with JSON `true` had it taken
    as the number 1.0 and carried onto the worksheet and into a published +/- interval, by the
    one input shape that should have routed to `_status_score` or been refused as UNESTIMABLE
    (sweep 44, batch 8). Six sites, one rule, now `_is_score`.

    The zero case is the half that matters as much: this project's other recurring slip is the
    FALSY-ZERO one, and the obvious "fix" -- testing truthiness instead of type -- would refuse a
    legitimate score of 0. So the net pins both directions, and pins `float` and `int` alike.
    """
    import magnitude as MG
    rejects = all(MG._is_score(v) is False for v in (True, False, "n/a", None, "", [], {}))
    accepts = all(MG._is_score(v) is True for v in (0, 0.0, 1, 1.5, -3, 10.0))
    return rejects and accepts


def _a_scope_refusal_is_never_cached_as_no_ceiling():
    """A host whose scope could not be READ must not become a host with NO CEILING. -> bool.

    ORDER 3eeedaafce1e (sweep46-batch08). `scope.scope_for` was repaired on 2026-09-06 to stop
    caching an API failure as an honest empty verdict -- it raises `ProbeUnread` instead (order
    6e2dab4c3981). `magnitude.host_ceiling` then caught that refusal in a bare `except Exception`
    and returned `cl = None`, which every caller reads as "this host has no ceiling", so the
    fabrication was recreated one layer above the fix.

    AND IT WAS CACHED, which is what made it permanent: the None went into `_SCOPE_CACHE`, so
    every later entity from that host in the same process skipped the clamp as well, with no
    second attempt and nothing recorded. A throttled host mid-batch is ordinary, and this clamp
    is the only outside check on the model's anchoring -- `host_ceiling`'s own docstring records
    what its absence produced: Jace Beleren at M10.77 against a published M2.88, Silver Surfer at
    M10.93.

    THREE ARMS, because fixing only the first would leave the expensive half in place:
      1. the refusal REACHES the caller instead of turning into None;
      2. it is NOT cached, so the next call tries again rather than inheriting a verdict that was
         never reached;
      3. a GENUINE empty verdict -- scope read successfully, no ceiling recorded -- still returns
         None and is still cached, so the fix cannot be "refuse everything", which would pass arm
         1 and quietly disable the on-disk fast path for all 155 hosts already measured.
    """
    import magnitude as MG
    import scope as _SC
    real_scope_for, real_cache = MG.SCOPE.scope_for, dict(MG._SCOPE_CACHE)
    host = "__drill_scope_probe__.invalid"
    calls = {"n": 0}
    try:
        def refusing(_h):
            calls["n"] += 1
            raise _SC.ProbeUnread("drill: the scope probe could not be read")
        MG.SCOPE.scope_for = refusing
        MG._SCOPE_CACHE.clear()
        # WRAPPED, BECAUSE THIS NET WAS ITSELF THE TWELFTH PROBE-LITTER SITE. The refusal path it
        # drives calls `note("magnitude.py:host_ceiling-unread")` -> `health.record`, and a
        # before/after diff of state/failures.json across a full drill run caught it growing 6 -> 8
        # -- two per run, one per arm -- within minutes of the net being written, on the same day
        # eleven older sites of this exact shape were retired. Recorded rather than quietly fixed:
        # the discipline is easy to state and easy to forget while writing the net that needs it,
        # which is the argument order 895a99602bf0 makes for a standing ledger check instead of
        # per-site care. The assertions are untouched.
        for _ in range(2):
            try:
                _deliberately_failing(lambda: MG.host_ceiling(host))
                return False                      # arm 1: swallowed the refusal
            except _SC.ProbeUnread:
                pass
        if host in MG._SCOPE_CACHE:
            return False                          # arm 2: cached a verdict never reached
        if calls["n"] != 2:
            return False                          # arm 2: did not retry
        MG.SCOPE.scope_for = lambda _h: {}
        MG._SCOPE_CACHE.clear()
        return MG.host_ceiling(host) is None and host in MG._SCOPE_CACHE   # arm 3
    finally:
        MG.SCOPE.scope_for = real_scope_for
        MG._SCOPE_CACHE.clear()
        MG._SCOPE_CACHE.update(real_cache)


def _status_reports_i_do_not_know_as_itself():
    """`autostart --status` must not print an unreadable process table as "not running". -> bool.

    `overnight.running()` is TRI-STATE and its own docstring says so: None means the probe could
    not see, and callers "test `is None` explicitly rather than leaning on truthiness". The
    per-job loop in `autostart.main()` leaned on truthiness, so "I could not tell" was rendered
    as "not running" -- the one answer an operator acts on, produced by the one condition in
    which nobody knows anything. It sat ten lines below the SAME file's correct handling of the
    same tri-state for the supervisor, which is how a reader learns the wrong one is deliberate.

    Driven, not read: `running` is stubbed to return None and the real `--status` is run with
    its output captured, so the net measures what an operator would actually see.
    """
    import contextlib
    import io as _io
    import autostart as AU
    import overnight as ON
    real_running, real_argv = ON.running, sys.argv
    buf = _io.StringIO()
    try:
        ON.running = lambda *_a, **_k: None          # the probe could not read the table
        sys.argv = ["autostart.py", "--status"]
        with contextlib.redirect_stdout(buf):
            AU.main()
    except SystemExit:
        pass
    finally:
        ON.running, sys.argv = real_running, real_argv
    out = buf.getvalue()
    # Every roster job must be reported as UNKNOWN, and none of them as a confident negative.
    jobs = [j for j in ON.ALL_JOBS if j not in ("autostart.py", "overnight.py")]
    if not jobs:
        return False                                  # an empty roster proves nothing
    lines = [ln for ln in out.splitlines()
             if any(ln.strip().startswith(j) for j in jobs)]
    return bool(lines) and all("UNKNOWN" in ln for ln in lines)


def _meta_ban_has_no_fall_through(src=None):
    """No handler around the P8 meta-language ban may let the chapter be WRITTEN. -> bool.

    `generate.py` is the only thing that turns a manifest into prose, and the last statement
    before it writes is `pipeline.assert_in_universe`, the Charter P8 meta-language gate. Its
    `except Exception` arm refuses the chapter and files it, and states the rule in its own
    words: "a gate that cannot run has not passed."

    Directly above it sat `except ImportError: silence.note(...)` -- and Python takes the FIRST
    matching clause, so an unimportable `pipeline` was caught THERE, noted, and fell through to
    the write. The gate was off and the chapter was published, for every chapter of the run,
    while the run reported success. `pipeline.py` is large and frequently edited in this same
    tree; one syntax error inside it is all that condition needs. Found by sweep 44, batch 7.

    THE INVARIANT IS "NO HANDLER FALLS THROUGH", not "there is no ImportError arm". Naming the
    one exception type would be a net that a differently-spelled fall-through walks past --
    `except ModuleNotFoundError`, `except (ImportError, AttributeError)`, or a bare `except:`
    added later would each pass it while reopening exactly this hole. So every handler on that
    `try` is required to END the iteration: the last statement of each must be `continue`,
    `raise` or `return`. That is the property the write depends on, and it is checkable without
    naming a single exception class.

    Source-shaped, and it has to be: the behaviour lives inside a multi-hour generation loop
    that needs a config, a manifest and a live model to reach. What is asserted is a structural
    fact about the code that runs, not a comment about it.
    """
    import ast
    tree = _ast_of(os.path.join(_srcdir(src), "generate.py"))
    guarded = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Try):
            continue
        calls = [n for n in ast.walk(ast.Module(body=node.body, type_ignores=[]))
                 if isinstance(n, ast.Call)
                 and getattr(n.func, "attr", None) == "assert_in_universe"]
        if calls:
            guarded.append(node)
    # THE GATE MUST STILL BE THERE. An empty list is the "absence read as clean" shape: delete
    # the call and every handler check below is vacuously true.
    #
    # `!= 1` USED TO REFUSE A SECOND GATE, NOT JUST AN ABSENT ONE (order 5156478c4583). The
    # comment above argues only for a floor -- "the gate must still be there" -- and the code
    # enforced an exact ceiling too, so a strictly STRONGER change (a second guarded call to
    # `assert_in_universe` somewhere else in `generate.py`) would breach a net whose whole
    # invariant, "no handler falls through", is a for-all over handlers and holds fine across
    # several `try` blocks. `not guarded` keeps the floor; every guarded node is now checked,
    # not just the first.
    if not guarded:
        return False
    for node in guarded:
        if not node.handlers:
            return False
        for h in node.handlers:
            if not h.body or not isinstance(h.body[-1], (ast.Continue, ast.Raise, ast.Return)):
                return False
        # AND NOTHING MAY RUN AFTER THE HANDLERS. An `else`/`finally` that wrote the chapter
        # would satisfy every check above and reopen the hole one line lower.
        if node.orelse or node.finalbody:
            return False
    return True


def _binding_health_filters(tmp=None):
    """`--limit 0` must select NOTHING, and a filter that matched nothing must not re-stamp.

    Two faults that had to be fixed together, which is why they are measured together (orders
    cd7492eec3bc and f1901d2178ba). `if limit:` read the integer 0 -- `--limit` defaults to
    `None`, so 0 is a value the operator gave -- as "no limit given", and answered a request for
    nothing by canarying the whole ~200-host estate. Fixing that alone ARMS the second: an empty
    host list is precisely the input the whole-estate-empty guard mishandled, because it was
    written `not (only or limit) and not out` and a filtered pass skipped it, fell through to the
    whole-file merge path, and landed a report with `at` bumped to now having verified nothing.
    Every downstream reader -- `workorders.sweep`'s binding detector, allsweep's reconcile --
    takes that stamp as the estate's current state.

    Driven against the real `run()` with the network stubbed, counting CANARIES rather than
    reading source: the first limb is about how many hosts get probed, and a source-shaped net
    would pass against a fix that says the right thing and probes the estate anyway.
    """
    import binding_health as BH
    tmpdir = tmp or tempfile.mkdtemp(prefix="drill_binding_filters_")
    out_path = os.path.join(tmpdir, "BINDING_HEALTH.json")
    seeded = {"at": 0, "checked": 2, "failed": 0,
              "hosts": [{"host": "a.example.invalid", "healthy": True},
                        {"host": "b.example.invalid", "healthy": True}]}
    saved_out, saved_canary, saved_titles, saved_load, saved_note = (
        BH.OUT, BH.canary, BH.known_present_titles, BH._load, BH._report_not_written)
    probed, refused = [], []
    try:
        with open(out_path, "w", encoding="utf-8") as f:
            json.dump(seeded, f)
        BH.OUT = out_path
        BH.known_present_titles = lambda h, m=None, **kw: "Any Title"
        BH.canary = lambda h, t, sources=None: (probed.append(h),
                                                {"host": h, "healthy": True,
                                                 "reason": "stubbed"})[1]
        BH._load = lambda path, default: ({"A": "a.example.invalid", "B": "b.example.invalid",
                                           "C": "c.example.invalid"}
                                          if path.endswith("WIKI_HOSTS.json")
                                          else saved_load(path, default))
        # Recorded rather than escalated: the refusal is the net's evidence, and a drill run
        # should not leave JANITOR rows in the live ledger for faults it staged itself.
        BH._report_not_written = lambda code, what: refused.append(code)

        # LIMB 1 -- `--limit 0` asks for no hosts. Nothing may be canaried.
        BH.run(limit=0)
        limb1 = not probed and refused == ["BINDING_FILTER_MATCHED_NOTHING"]

        # LIMB 2 -- and the report it did not probe must be untouched, `at` included.
        with open(out_path, encoding="utf-8") as f:
            after_zero = json.load(f)
        limb2 = after_zero == seeded

        # LIMB 3 -- a `--host` filter matching no bound host is the same refusal by the other
        # road, and this is the one that fell through to the merge before.
        probed.clear(), refused.clear()
        BH.run(only=["no-such-host.example.invalid"])
        with open(out_path, encoding="utf-8") as f:
            after_miss = json.load(f)
        limb3 = (not probed and refused == ["BINDING_FILTER_MATCHED_NOTHING"]
                 and after_miss == seeded)

        # LIMB 4 -- and none of this may have broken the ordinary filtered pass, which must
        # still probe its host and merge it into the standing report.
        probed.clear(), refused.clear()
        BH.run(only=["a.example.invalid"])
        with open(out_path, encoding="utf-8") as f:
            after_real = json.load(f)
        limb4 = (probed == ["a.example.invalid"] and not refused
                 and {h.get("host") for h in after_real.get("hosts") or []}
                 == {"a.example.invalid", "b.example.invalid"}
                 and after_real.get("at") != 0)
    finally:
        (BH.OUT, BH.canary, BH.known_present_titles, BH._load,
         BH._report_not_written) = (saved_out, saved_canary, saved_titles, saved_load, saved_note)
        shutil.rmtree(tmpdir, ignore_errors=True)
    return limb1 and limb2 and limb3 and limb4


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

    AND SCOPED TO THE ARM THE CONDITION ACTUALLY GUARDS (order 07c7379597ba, run #37). The
    search still ran over the whole `If` node, so a `_probe_identity` call in the `else` -- the
    UNGATED path, which is the fault itself -- or in a branch nothing can enter would have
    answered for one inside the gate. It was unexploitable only because `binding_health.py`
    happens to contain exactly one call site today, which is a fact about this morning's source
    and not about this net. The gated arm is now the only place the call counts.

    AND "THERE EXISTS A GATED SITE" IS THE WRONG QUANTIFIER (order 5ed81099fc49, run #37). Even
    scoped to the arm, the net asked only whether ONE correctly-gated call could be found -- so
    adding an UNGATED `_probe_identity(h)` beside it restored the whole fault with the net
    green. The sweep proved it: a `sweep()` that probes every host unconditionally AND keeps the
    gated call returns True, which is a network round trip per host per sweep, exactly the cost
    this net exists to prevent. The property was never "a gate exists somewhere"; it is "no
    probe happens outside the gate", and those differ by one added line.

    Stated now the way `resync_cannot_revert_an_exclusion` (below) states its own: collect the
    reachable gated arms, collect EVERY reachable call to `_probe_identity`, and require that
    there is at least one and that all of them are inside a gate. One escaping call is one
    sweep away from the round trips.
    """
    import ast
    tree = _ast_of(os.path.join(_srcdir(src), "binding_health.py"))
    gates = []
    for n in _live_walk(tree):
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
        if gated and sourced:
            gates.append(n)
    protected = {id(x) for g in gates for x in _live_stmt_walk(_live_stmts(g.body))}
    probes = [x for x in _live_walk(tree) if isinstance(x, ast.Call)
              and _spelled(_spellings_of_call(tree, x), "_probe_identity")]
    return bool(probes) and all(id(x) in protected for x in probes)


def _supersession_is_called(src=None):
    """`workorders` CALLS `_supersede_binding_suspect`, rather than merely containing the name.

    ASKED OF THE PARSE TREE (run #36). The old form searched the file text, and the file text
    carries the name in a comment (`-- see _supersede_binding_suspect`) and in the `def` line
    itself. So every call site could be deleted -- leaving the settled host's vague order open
    beside its precise replacement for ever, the exact fault this net was written for -- and the
    net would have gone on holding on the definition of the function nobody calls.

    AND A CALL IN DEAD CODE IS A DEFINITION NOBODY CALLS (order 78f04bec15ad, run #37). `_calls`
    read the whole file, so the sweep's `workorders.py` -- which supersedes nothing, and carries
    the call after a `return` -- left this net green. The call must now be REACHED, from the
    sweep that files these orders or from the CLI: `_supersede_binding_suspect` is only worth
    anything on the path that just filed the order it supersedes.
    """
    return _reaches_call(_ast_of(os.path.join(_srcdir(src), "workorders.py")),
                         "_supersede_binding_suspect", ("main", "sweep_detectors"))


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
    net(a, "a boolean is not an axis score, and zero still is",
        _a_boolean_is_not_a_score,
        "`bool` subclasses `int`, so `isinstance(x, (int, float))` took JSON `true` as the "
        "number 1.0 and published it inside an assay interval -- while the obvious truthiness "
        "'fix' would refuse a legitimate score of 0")
    net(a, "a scope that could not be READ is never cached as a host with NO CEILING",
        _a_scope_refusal_is_never_cached_as_no_ceiling,
        "scope.py was fixed to raise rather than cache an API failure as an empty verdict, and "
        "host_ceiling's bare `except Exception` turned the refusal straight back into None -- "
        "then cached it, so every later entity from that host skipped the clamp too")
    net(a, "`--status` reports an unreadable process table as UNKNOWN, not as 'not running'",
        _status_reports_i_do_not_know_as_itself,
        "`running()` is tri-state and None means nobody knows; rendering that as the confident "
        "negative an operator acts on is the fail-closed property inverted")
    net(a, "the P8 meta-language ban has no handler that falls through to the write",
        _meta_ban_has_no_fall_through,
        "`except ImportError: note()` above the fail-closed arm caught an unimportable "
        "`pipeline` FIRST and fell through, so the gate was off and the chapter was published "
        "-- for every chapter of the run, while the run reported success")
    net(a, "an EMPTY filter canaries nothing and re-stamps nothing",
        _binding_health_filters,
        "`--limit 0` read as 'no limit' answers a request for nothing by canarying the whole "
        "estate, and a filter matching no host lands a report with `at` bumped to now having "
        "verified nothing -- which is the one field every downstream reader trusts")
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
    # THE FIXTURE MOVED OFF `absent`, run #36. This net drove `op: "absent"`, and `absent`
    # became the one exempt operator this run (policy.py, order 9ef866225683): asserting a field
    # is MISSING has `found=False` as its only truthful passing case, so flagging it would report
    # every correct pass of that operator as a non-result. The exemption is right and the net's
    # SUBJECT is unchanged -- a pass over a field that does not exist is not evidence of anything
    # -- so the net now drives `not_matches`, whose `v is None` clause passes on an absent field
    # as a SIDE EFFECT rather than as its subject, which policy.py names in those words as the
    # case that must stay reported. The exemption gets its own net below rather than being
    # smuggled in as the absence of this one.
    net(a, "a pass over a MISSING field is flagged vacuous",
        lambda: len(POL.evaluate({}, [{"id": "t", "path": "nope", "op": "not_matches",
                                       "arg": "zzz"}])["vacuous"]) == 1,
        "the standards HIGH guard read a key nothing set and was ABSENT for its whole life")
    net(a, "the `absent` operator's own correct pass is NOT called vacuous",
        lambda: POL.evaluate({}, [{"id": "t", "path": "nope", "op": "absent"}])["vacuous"] == []
        and POL.evaluate({}, [{"id": "t", "path": "nope", "op": "absent"}])["failed"] == [],
        "a signal that fires on every correct use of an operator is furniture, and the "
        "exemption that stops it must be netted or the next edit will widen it to everything")
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

    AND THE RECORDING HALF WAS A WHOLE-FILE WALK WITH NO BRANCH SCOPING (order 18958aba2143,
    run #37). It was satisfied by ANY assignment, in ANY function, whose target was a subscript
    of a name `unreal` -- under any key at all. The sweep built a `feats.py` whose refusal
    branch is `pass`, so the refusal is DROPPED ON THE FLOOR, which IS the fault; it carried
    `unreal['unrelated'] = ...` elsewhere in the file and went on returning
    `{'pages_refused': unreal}`, and this net returned True. Neither half tested the
    distinction the net exists for -- "this entity has no evidence" against "we were served a
    block page" -- and that distinction is the whole subject.

    So the recording is asked where it has to happen: inside `evidence_for`, in the REACHABLE
    branch guarded by the answer `page_looks_real` gave, and KEYED BY THE PAGE -- the subscript
    has to be a loop variable of that function, not a literal. An empty refusal branch stops
    answering, and so does a recording made anywhere else. The carrying half is unchanged; it
    was never the defective one.
    """
    import ast
    tree = _ast_of(os.path.join(_srcdir(src), "feats.py"))
    ev = _defn(tree, "evidence_for")
    records = False
    if ev is not None:
        asked = _bound_from_call(tree, ev, "page_looks_real")
        loopvars = {e.id for n in _live_walk(ev)
                    if isinstance(n, (ast.For, ast.AsyncFor))
                    for e in ast.walk(n.target) if isinstance(e, ast.Name)}
        for g in _live_walk(ev):
            if not (asked and isinstance(g, ast.If) and _guarded_by(tree, g, asked)):
                continue
            for st in _live_stmt_walk(_live_stmts(g.body)):
                if not isinstance(st, ast.Assign):
                    continue
                for t in st.targets:
                    if (isinstance(t, ast.Subscript) and isinstance(t.value, ast.Name)
                            and t.value.id == "unreal" and isinstance(t.slice, ast.Name)
                            and t.slice.id in loopvars):
                        records = True
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
    `cand.bucket.startswith(LOCAL_PREFIX)`, and `_ask_call`'s own comment naming `LOCAL_PREFIX`
    while explaining the branch (cited by symbol, not by line, per order 0c7592915a48 -- a line
    drifts the first time something is edited above it) -- so the guard could be deleted and the
    explanation would keep answering for it, while the router handed out ollama buckets and
    flooded a 10 GB card with its own queue again. The test is now a real `.startswith` call
    against the real constant, guarding a real branch.

    AND THAT REWRITE WAS VACUOUS THREE WAYS (order 8f4bb64503c2, run #37). It asked only that
    SOME `if` anywhere in the file mention `<x>.bucket.startswith(LOCAL_PREFIX)` in its test. It
    never asked what the branch DID, whether anything could enter it, or whether it was the
    router's branch at all, and the sweep beat it on each count in turn:

      * a guard whose body is `pass`, with an ollama bucket served straight past it -> HELD;
      * the same guard parked in dead code after a `return` -> HELD;
      * and the finding that matters -- the REAL `cascade_bridge.py` with the router's actual
        skip inside `_ask_call` DELETED -> still HELD, answered instead by the catalogue
        de-duplication `if` inside `cloud_buckets`, which has
        nothing to do with handing a worker a bucket to call.

    A net satisfied by an unrelated line elsewhere in the file is not measuring the guard; it is
    measuring whether anybody has ever written that expression. So the question is now stated
    the way the property is, and modelled on `resync_cannot_revert_an_exclusion` below:

      * SCOPED to a function that reachably CLAIMS a candidate -- the only path on which a local
        bucket can be handed out, which is what makes `cloud_buckets`' de-duplication stop
        answering for the router;
      * REACHABLE, so a guard nothing can enter counts as the deletion it is;
      * and the guarded arm must actually SKIP the candidate. `continue`, `break`, `return` or
        `raise`: the arm has to end this candidate's turn. A `pass` that falls through to the
        code serving the bucket is the fault wearing the guard's shape.

    `claim` is asked for by method name rather than through `_ROUTER`, deliberately: pinning a
    net to one spelling of the object it goes through is what order 7cc460706efe filed against
    two nets in this file, and a net that breaches over a rename halts the library.

    AND "THERE EXISTS A GATED SITE" WAS STILL THE WRONG QUANTIFIER (order 8ab131910911, run
    #40). Every correction above sharpened WHERE the net looked and left it a `return True` on
    the first qualifying `if` -- so it asked whether ONE correctly-gated claim loop could be
    found, when the property is that NO local bucket is handed out. Adding a second, UNGATED
    candidate loop beside the correct one restored the whole fault with the net reporting HELD.
    PROVED with a fixture driven through the real function.

    This is verbatim order 5ed81099fc49, which this same file records against
    `_identity_probe_is_gated` twenty lines up: "adding an UNGATED `_probe_identity(h)` beside
    it restored the whole fault with the net green ... The property was never 'a gate exists
    somewhere'; it is 'no probe happens outside the gate', and those differ by one added line."
    That net was rewritten to the universal form; this one's own docstring said it was modelled
    on `resync_cannot_revert_an_exclusion`, which IS universal, and it was not.

    STATED UNIVERSALLY NOW, and anchored on the CLAIM rather than on the guard. Every reachable
    `claim` call is found; each is attributed to its INNERMOST enclosing loop -- the candidate
    loop that hands that bucket out; and EVERY such loop must carry a reachable
    `<x>.bucket.startswith(LOCAL_PREFIX)` guard whose arm ends the candidate's turn. Anchoring
    on the claim rather than on the guard is what makes an added loop count: a new way to hand
    out a bucket brings its own claim with it and must bring its own skip, while a net that
    starts from the guards can only ever count the guards that are there. `bool(loops)` keeps
    the net from passing vacuously on a file that claims nothing at all.
    """
    import ast
    tree = _ast_of(os.path.join(_srcdir(src), "cascade_bridge.py"))

    def ends_the_turn(loop):
        """Does this loop skip a local bucket, on a path the program can reach?"""
        for n in _live_walk(loop):
            if not isinstance(n, ast.If):
                continue
            guards = False
            for c in ast.walk(n.test):
                if not (isinstance(c, ast.Call) and isinstance(c.func, ast.Attribute)
                        and c.func.attr == "startswith"):
                    continue
                if not (isinstance(c.func.value, ast.Attribute)
                        and c.func.value.attr == "bucket"):
                    continue
                if any(isinstance(x, ast.Name) and x.id == "LOCAL_PREFIX" for x in c.args):
                    guards = True
            if not guards:
                continue
            if _arm_leaves(n.body, (ast.Continue, ast.Break, ast.Return, ast.Raise)):
                return True
        return False

    loops = []
    for fn in ast.walk(tree):
        if not isinstance(fn, (ast.FunctionDef, ast.AsyncFunctionDef)):
            continue
        if not _calls_within(tree, fn, "claim", reachable=True):
            continue                     # not a path that hands a worker a bucket
        # The innermost loop around each reachable claim: that is the candidate loop, and a
        # skip in an OUTER loop does not protect an inner one that serves buckets of its own.
        for n in _live_walk(fn):
            if not isinstance(n, (ast.For, ast.AsyncFor)):
                continue
            if not _calls_within(tree, n, "claim", reachable=True):
                continue
            if any(isinstance(inner, (ast.For, ast.AsyncFor)) and inner is not n
                   and _calls_within(tree, inner, "claim", reachable=True)
                   for inner in _live_walk(n)):
                continue                 # an enclosing loop; the inner one is the candidate loop
            loops.append(n)
    return bool(loops) and all(ends_the_turn(n) for n in loops)


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
    would look identical from the passing half alone. `QUARANTINE` points at a temp path, and the
    escalation chain is a stand-in, because the real one files a work order and the drill is not
    allowed to leave one in the queue for a host that does not exist.

    AND THE FAILURE IS NOW REAL, NOT STUBBED (order 8ee268ce32cc, run #37). This used to replace
    `BH._land` with `lambda path, obj: False`, which made the net an assertion about ONE named
    helper rather than about the property. That pinned `quarantine()` to a blind overwrite:
    order 8ee268ce32cc asks for the same compare-and-swap `release()` now uses -- two writers of
    `HOST_QUARANTINE.json` is the normal situation here -- and the moment the write went through
    `_land_cas` instead, the stub stopped being consulted, the real write landed, and every
    expectation here inverted. A net that has to be edited before a correctness fix can be
    applied is a net standing in the way of the thing it was written to protect.

    So nothing about the write path is stubbed. THE TARGET IS A DIRECTORY, so the rename cannot
    succeed however it is attempted -- `_land`'s `replace_retry` reports a denied rename, and a
    compare-and-swap cannot even digest it -- and neither raises, which is the contract both
    sides of `silence` already promise. The passing half writes for real and the file is then
    READ BACK and required to name the host, which is a stronger claim than the old arm's "the
    stub wrote nothing": the record and the disk have to agree in both directions.

    `silence.note` is silenced for the duration. A genuinely denied rename records
    `replace-denied:` in the health ledger, and a battery that files a synthetic fault every
    cycle is the litter discipline the rung-4 probes next door already keep.
    """
    import json as _json
    import shutil
    import types
    import binding_health as BH
    import silence as _S
    d = tempfile.mkdtemp(prefix="drillquar_")
    raised = []
    stub = types.ModuleType("escalation")
    stub.SUPERVISOR = ESC.SUPERVISOR
    stub.escalate = lambda level, code, what, **k: raised.append(code)
    had, prev = "escalation" in sys.modules, sys.modules.get("escalation")
    keep, keep_note = BH.QUARANTINE, _S.note
    try:
        sys.modules["escalation"] = stub
        _S.note = lambda *a, **k: None

        # 1 -- A WRITE THAT CANNOT LAND. The target is a directory, so no write path lands on
        #      it and none of them raises. The host is NOT quarantined, and the record and the
        #      escalation both have to say so.
        BH.QUARANTINE = os.path.join(d, "unwritable", "HOST_QUARANTINE.json")
        os.makedirs(BH.QUARANTINE, exist_ok=True)
        rec = BH.quarantine("__drill__.invalid", "drill self-test; no such host")
        if rec.get("landed") is not False or raised != ["HOST_QUARANTINE_NOT_RECORDED"]:
            return False
        if BH.is_quarantined("__drill__.invalid"):
            return False                      # it reported not-landed and quarantined it anyway

        # 2 -- AND A WRITE THAT DOES LAND, read back off the disk it claims to have reached.
        del raised[:]
        BH.QUARANTINE = os.path.join(d, "HOST_QUARANTINE.json")
        rec = BH.quarantine("__drill__.invalid", "drill self-test; no such host")
        if not (rec.get("landed") is True and raised == ["HOST_QUARANTINED"]):
            return False
        with open(BH.QUARANTINE, encoding="utf-8") as fh:
            on_disk = _json.load(fh)
        return "__drill__.invalid" in on_disk and BH.is_quarantined("__drill__.invalid")
    finally:
        BH.QUARANTINE, _S.note = keep, keep_note
        if had:
            sys.modules["escalation"] = prev
        else:
            sys.modules.pop("escalation", None)
        shutil.rmtree(d, ignore_errors=True)


def _backoff_stops_at_its_ceiling():
    """Throttle a host until the multiplier saturates, and require it to STOP at the clamp.

    THE OLD NET WAS `1.0 < F.BACKOFF_MAX <= 128.0`. That is an assertion about a number nobody
    was going to change, and it never drove a call: the clamp it is named after is
    `feats.py:159`, `min(BACKOFF_MAX, _BACKOFF.get(host, 1.0) * BACKOFF_GROWTH)`, and deleting
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

    # A TRANSPORT FAILURE READ AS AN EMPTY ANSWER, in three more places (orders
    # de0681cb9edc and 6e2dab4c3981, landed 2026-09-06 from
    # handoff/nets_20260906/read_catalogue.py and longtail.py). Same subject as this
    # area's founding nets one layer up: a roster or a scope that was never read must not
    # come back looking like a roster or a scope that was read and was empty. All three
    # stub the transport; none makes a request.
    # Both attack wiki_source's listing walks with a MOCKED transport -- no network call is made, and
    # neither writes to the corpus, the roll, or any file. `wiki_source._api` is monkeypatched to
    # succeed once (one page, with a pagination continuation token) and then raise on every call after
    # that -- exactly the shape of a real mid-walk API hiccup -- and each net checks that the walk
    # propagates the failure instead of silently returning the alphabetical prefix it had already
    # collected as if it were the whole roster.
    #
    # PROVEN RED AGAINST THE PRE-FIX wiki_source.py (this sweep, before the order de0681cb9edc edit
    # landed):
    #
    #     category_members: NO EXCEPTION -- returned ['Alpha', 'Beta'] -- BREACH (pre-fix expected)
    #     all_categories:   NO EXCEPTION -- returned [(500, 'Characters')] -- BREACH (pre-fix expected)
    #
    # AND GREEN AFTER IT (this sweep, against the fixed wiki_source.py in this same tree):
    #
    #     category_members: RAISED TimeoutError -- HELD
    #     all_categories:   RAISED TimeoutError -- HELD
    #
    # Order: de0681cb9edc (priority order, sweep45-batch09, verified against source by run #45).

    def wiki_source_partial_roster_never_lands_as_complete():
        """category_members must raise on a transport failure mid-pagination, not return the
        alphabetical prefix it had already collected as if that were the whole category.

        Pre-fix, `category_members` caught the transport exception, logged it via `silence.note`,
        and `break`-ed out with whatever had been paginated so far -- and because MediaWiki returns
        category members ALPHABETICALLY, that partial list is an A-through-something PREFIX of the
        real roster, handed back with no marker distinguishing it from a genuinely short category.
        `catalogue()`'s single-wiki path (catalogue_web.py) wraps nothing around this call, on the
        documented premise that a transport failure here fails the whole attempt honestly and keeps
        the source retryable (`entry_count` stays 0) -- a premise that was false as written before
        this fix, because the exception this premise depends on never actually reached the caller.
        """
        import wiki_source as WS

        calls = {"n": 0}

        def _fake_api(subdomain, params, timeout=25):
            calls["n"] += 1
            if calls["n"] == 1:
                return {"query": {"categorymembers": [{"title": "Alpha"}, {"title": "Beta"}]},
                        "continue": {"cmcontinue": "next-page"}}
            raise TimeoutError("simulated transport failure mid-pagination")

        _orig_api = WS._api
        WS._api = _fake_api
        try:
            try:
                # The propagating failure notes itself on the way out, so the call that is
                # SUPPOSED to raise is wrapped -- see `_deliberately_failing`. The RAISE is
                # what is asserted; nothing under test is suppressed.
                _deliberately_failing(
                    lambda: WS.category_members("faketest-net-de0681cb9edc", "Characters",
                                                limit=None))
                return False   # no exception -- the partial roster was returned silently: BREACH
            except Exception:
                return True    # the failure propagated -- HELD
        finally:
            WS._api = _orig_api


    def wiki_source_all_categories_partial_walk_never_cached_as_complete():
        """all_categories must raise on a transport failure mid-pagination -- and, because a failed
        walk that raises can never reach the memoisation line below it, a failed walk can no longer
        be cached as the wiki's whole category set for the rest of the process either.

        Pre-fix, this caught the transport exception, set `complete = False`, `break`-ed out with the
        partial list, and returned it (uncached only because of the `complete` guard -- the partial
        list itself was still handed to the caller as the answer). Every one of the seven canonical
        classes that calls `find_categories` -> `discover_categories` -> `all_categories` for the
        same wiki would then have silently read that same truncated category list.
        """
        import wiki_source as WS

        calls = {"n": 0}
        key = ("faketest-net-de0681cb9edc-allcats", 40, None)

        def _fake_api(subdomain, params, timeout=25):
            calls["n"] += 1
            if calls["n"] == 1:
                return {"query": {"allcategories": [{"*": "Characters", "pages": 500}]},
                        "continue": {"accontinue": "next-page"}}
            raise TimeoutError("simulated transport failure mid-pagination")

        _orig_api = WS._api
        with WS._ALLCATS_LOCK:
            WS._ALLCATS.pop(key, None)   # leave no state behind from a previous run of this net
        WS._api = _fake_api
        try:
            try:
                _deliberately_failing(
                    lambda: WS.all_categories("faketest-net-de0681cb9edc-allcats",
                                              min_pages=40))
                return False   # no exception -- the partial category list was returned: BREACH
            except Exception:
                return True    # the failure propagated -- HELD
        finally:
            WS._api = _orig_api
            with WS._ALLCATS_LOCK:
                WS._ALLCATS.pop(key, None)


    net(a, "a category roster cut off mid-walk is not handed back as the whole roster",
        wiki_source_partial_roster_never_lands_as_complete,
        "category_members raises on a transport failure mid-pagination instead of silently "
        "returning the alphabetical prefix already collected (order de0681cb9edc)")

    net(a, "a category WALK cut off mid-pagination is not handed back as the wiki's whole set",
        wiki_source_all_categories_partial_walk_never_cached_as_complete,
        "all_categories raises on a transport failure mid-pagination instead of returning (and, "
        "unbounded, memoising) a partial category list (order de0681cb9edc)")

    def drill_scope_refuses_an_unread_host():
        import scope as SC, feats as F
        real = F.api, F.fetch
        def _fail(host, params, retries=2, outcome=None):
            if outcome is not None:
                outcome.clear(); outcome["ok"], outcome["why"] = False, "throttled"
            return None
        def _ok_empty(host, params, retries=2, outcome=None):
            if outcome is not None:
                outcome.clear(); outcome["ok"], outcome["why"] = True, "ok"
            return {"query": {"search": []}}
        try:
            F.api = _fail
            try:
                SC.scope_for("fixture.invalid")
                return False              # a swallowed failure came back as a verdict
            except SC.ProbeUnread:
                pass
            F.api = _ok_empty
            if SC.scope_for("fixture.invalid") is not None:
                return False              # the genuine empty answer must still be the empty answer
            return True
        finally:
            F.api, F.fetch = real


    net(a, "a host that could not be read is not stamped as having no scope",
        drill_scope_refuses_an_unread_host,
        "scope_for raises ProbeUnread when feats.api swallowed a failure, and still returns "
        "None for a host that genuinely answered with nothing")


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
    def burial_is_permanent_codes_only():
        """DRIVEN, not read (order 64dfe6bec15c, run #37). These were the last two raw
        substring-over-file-text nets in the module, and they were both defeated by a COMMENT.

        This one was `all(c in src for c in ("401","402","404","410")) and "429" in src` --
        satisfied by any file that happens to contain those five numbers anywhere, in any
        order, for any reason. The sweep passed it a `cascade_bridge.py` whose entire content
        was a two-line comment naming the codes plus a `permanent_refusal()` returning True for
        EVERY error string, so a 429 was buried permanently: precisely what this net's own
        expectation forbids, held green on the strength of the sentence describing the rule.

        So the classifier is now put to real inputs, on both sides of the line and in both
        places the line is drawn. `dead_forever` is fed a synthetic proof file -- IN A SCRATCH
        DIRECTORY, never `data/POOL_PROOF.json` -- and must bury exactly the four codes a human
        has to fix and nothing else; `permanent_refusal` must bench a 401 and a 402 and must not
        bench a 429. A timeout row is in there too: burying that is the mistake the module's own
        docstring records making once, when eleven buckets were written off for being busy.
        """
        import cascade_bridge as CB
        codes = ("401", "402", "404", "410")
        d = tempfile.mkdtemp(prefix="drill_pool_")
        keep_proof = CB.PROOF
        try:
            rows = [{"bucket": "b%s:free" % c, "verdict": "no answer",
                     "reason": "provider said HTTP %s" % c} for c in codes + ("429",)]
            rows.append({"bucket": "btimeout:free", "verdict": "no answer",
                         "reason": "read timed out after 45s"})
            p = os.path.join(d, "POOL_PROOF.json")
            with open(p, "w", encoding="utf-8") as fh:
                json.dump(rows, fh)
            CB.PROOF, CB._PROVEN[0] = p, None
            buried = CB.dead_forever()
        finally:
            # The memo is dropped rather than restored: it is keyed on the proof file's mtime,
            # and leaving this probe's answer in it would hand the next caller a verdict about
            # a scratch file. Dropping it costs one stat.
            CB.PROOF, CB._PROVEN[0] = keep_proof, None
            shutil.rmtree(d, ignore_errors=True)
        return (buried == {"b%s:free" % c for c in codes}
                and CB.permanent_refusal("HTTP 401 invalid api key")
                and CB.permanent_refusal("HTTP 402 payment required")
                and not CB.permanent_refusal("HTTP 429 rate limit reached"))
    net(a, "burial buries the permanent codes and ONLY those", burial_is_permanent_codes_only,
        "a rate limit must never be written down as a permanent property")

    def there_is_no_paid_lane():
        """ASKED OF THE PARSE TREE (order 64dfe6bec15c, run #37). This was
        `"THERE IS NO PAID LANE" in src` -- a check that a COMMENT exists. The sweep passed it a
        `cascade_bridge.py` carrying that phrase in a two-line comment beside a live
        `PAID = {"enabled": True, "cap": 500}`, and the net held. A net whose whole subject is
        that a lane which merely LOOKS closed is not closed had been reduced to reading the sign
        on the door.

        The file states the property itself, and it is structural: "NOTHING IN THIS FILE KNOWS
        WHAT A PAID BUCKET IS. There is no prefix constant to match, no cap to enforce, no
        counter to maintain, and no branch that could reach one." A lane needs a NAME -- a
        constant, an attribute, an argument, or a dict key -- so the parse tree is asked for one,
        and comments and docstrings, which is where every legitimate mention of the retired lane
        lives, are not in a parse tree at all.

        STRING LITERALS ARE EXEMPT UNLESS THEY ARE KEYS, deliberately: `_PERMANENT_WORDS` holds
        "purchase pre-paid", which is the classifier that AXES a provider asking for money --
        the opposite of a paid lane, and flagging it would make this net breach against the code
        it is protecting. A key is different: `cfg["paid"]["cap"]` is machinery.

        The documentation half is KEPT rather than replaced. It was never wrong, only
        insufficient, and the ruling it records is worth having in the file.
        """
        import ast
        path = os.path.join(_srcdir(), "cascade_bridge.py")
        with open(path, encoding="utf-8") as fh:
            text = fh.read()
        tree = _ast_of(path)
        named = []
        for n in ast.walk(tree):
            for f in ("id", "attr", "name", "arg", "asname"):
                v = getattr(n, f, None)
                if isinstance(v, str) and "paid" in v.lower():
                    named.append(v)
            if isinstance(n, (ast.Import, ast.ImportFrom)):
                named += [al.name for al in n.names if "paid" in (al.name or "").lower()]
            keys = []
            if isinstance(n, ast.Dict):
                keys = [k for k in n.keys if k is not None]
            elif isinstance(n, ast.Subscript):
                keys = [n.slice]
            named += [k.value for k in keys
                      if isinstance(k, ast.Constant) and isinstance(k.value, str)
                      and "paid" in k.value.lower()]
        return not named and "THERE IS NO PAID LANE" in text
    net(a, "there is no paid lane to spend", there_is_no_paid_lane,
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
        reaching the `permanent_refusal` branch inside `_ask_call` (cited by symbol, not by
        line, per order 0c7592915a48) that BENCHES a bucket for four hours on evidence that was
        never about that bucket — with both halves of this net still true. Found by the run #34
        sweep; third time this shape has been cut out of this file.

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

    def sweep_fire_polarity():
        """THE ARMS OF `_fire` MUST NOT BE THE OTHER WAY ROUND.

        Every net above this one proves `battery_faults` COMPUTES the right faults. Not one of
        them followed the answer one layer further, to the helper that decides whether a
        computed fault gets FILED or CLOSED -- and on 2026-09-03 that helper was inverted. All
        eleven call sites in `sweep_detectors` pass a predicate that is TRUE when the thing is
        HEALTHY (`not bad`, `chain_ok`, `not hits`, `n <= CEILING`, `f is None`, `not stranded`,
        `not scratch`, `not _ghosts`), and `_fire` filed on the true arm. So a clean tree filed
        the order and a REAL fault closed it, writing "detector stopped firing" into the paper
        trail as the resolution.

        It stood in the queue as three BLOCKING orders each reporting ZERO problems, two battery
        orders whose `what` was the empty string, and LIVENESS_RATCHET calling 46-against-52 a
        breach. The severity was the part that rotted first: three permanently-red BLOCKING
        orders are an alarm that always sounds, which Hard Rule -1 calls furniture. The arm that
        mattered was the quiet one -- a real credential staged for the PUBLIC repo would have
        RESOLVED its own BLOCKING order and said nothing.

        Asserted on the SOURCE, not by running the sweep, because running it writes the live
        queue and a net may not do that. `ok` is the healthy predicate: the true arm must reach
        `resolve_code` and only `resolve_code`, and the false arm must reach `file_order` and
        only `file_order`. Pinned this way so that swapping the two bodies, negating the test,
        or renaming the parameter all read as BREACHED rather than as a passing rewrite.
        """
        import ast
        tree = _ast_of(os.path.join(_srcdir(), "workorders.py"))
        fire = None
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef) and node.name == "sweep_detectors":
                for inner in node.body:
                    if isinstance(inner, ast.FunctionDef) and inner.name == "_fire":
                        fire = inner
        if fire is None:
            return False
        # The parameter it branches on must still be the FIRST one, and still be the healthy
        # predicate by name -- a rename here is a contract change, not a refactor.
        if not fire.args.args or fire.args.args[0].arg != "ok":
            return False
        branch = next((s for s in fire.body if isinstance(s, ast.If)), None)
        if branch is None:
            return False
        # A bare `if ok:` -- not `if not ok:`, and not a compare that happens to read the same.
        if not (isinstance(branch.test, ast.Name) and branch.test.id == "ok"):
            return False

        def calls(stmts):
            got = set()
            for s in stmts:
                for n in ast.walk(s):
                    if isinstance(n, ast.Call) and isinstance(n.func, ast.Name):
                        got.add(n.func.id)
            return got
        healthy, faulty = calls(branch.body), calls(branch.orelse)
        return ("resolve_code" in healthy and "file_order" not in healthy
                and "file_order" in faulty and "resolve_code" not in faulty)
    net(a, "the sweep files on the FAULT and closes on the HEALTH, not the reverse",
        sweep_fire_polarity,
        "inverted for an unknown span to 2026-09-03: a clean tree filed three BLOCKING orders "
        "and a real staged credential would have closed its own")

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

    def stranded_synthesis_selects_on_the_condition():
        """A record with entries and no synthesis must be reported, whatever LOST the synthesis.

        THE DETECTOR EXISTS AND HAS NEVER BEEN WATCHED FIRE (order 1f39177464cf). It was added to
        `sweep_detectors` because thirty-one records sat with a null synthesis until a person
        noticed on 2026-08-28 -- 191,029 entries, Marvel and DC among them -- and the pipeline's
        own failed set held exactly TWO of them. The other twenty-nine never failed anything:
        their blocks were written correctly and then CLOBBERED by the catalogue-side writer.
        `phase_synthesis` skips any source already in its done-keys, so nothing would ever have
        revisited them.

        SO THE PROPERTY UNDER TEST IS SELECTION ON THE CONDITION, NOT ON THE CAUSE, and it is the
        whole reason the detector is worth having: a rescue tool keyed to the failed set misses
        every casualty whose cause it did not anticipate. `stranded` here is in no failed set and
        must still be returned; `whole` has a synthesis and must not be; `empty` has nothing to
        synthesise FROM and is not stranded, it is empty, and a detector that fires on it would
        file a hundred orders nobody can act on and be switched off within the day.

        Driven against a fixture record set, never the live one -- `records()` is the seam,
        exactly as `drill_two_writer` uses it.
        """
        import pipeline as PL
        import retry_synthesis as RS
        keep = PL.records
        rows = [("stranded.json", {"source": "Stranded", "entries": [{"name": "a"}],
                                   "synthesis": None}),
                ("whole.json", {"source": "Whole", "entries": [{"name": "b"}],
                                "synthesis": {"band": "M4"}}),
                ("empty.json", {"source": "Empty", "entries": [], "synthesis": None})]
        try:
            PL.records = lambda: list(rows)
            return RS.stranded_sources() == ["Stranded"]
        finally:
            PL.records = keep
    net(a, "a record with entries and no synthesis is reported STRANDED",
        stranded_synthesis_selects_on_the_condition,
        "the pipeline's failed set held 2 of the 31 clobbered records, so a detector keyed to "
        "the CAUSE would have found two and reported the job done")

    def stranded_detector_fires_on_what_it_computes():
        """...and the sweep must actually FILE on that list, in a reachable branch.

        The half a behavioural net cannot answer. `stranded_sources()` could be perfect and the
        detector still inert: this project's signature failure is a value computed, printed and
        dropped, and `sweep_detectors` is exactly where that would be invisible -- a `_fire`
        whose condition was hard-wired, or a stranded list bound and never passed, reports the
        same "nothing outstanding" line as a clean library.

        So: the call is REACHABLE inside `sweep_detectors`, the name it binds is what the
        `_fire` guarding STRANDED_SYNTHESIS is conditioned on, and the code string is there to
        be filed under.
        """
        import ast
        tree = _ast_of(os.path.join(_srcdir(), "workorders.py"))
        sweep = _defn(tree, "sweep_detectors")
        if sweep is None or not _says(tree, "STRANDED_SYNTHESIS"):
            return False
        bound = _bound_from_call(tree, sweep, "retry_synthesis.stranded_sources")
        if not bound:
            return False
        for call in _live_walk(sweep):
            if not (isinstance(call, ast.Call) and isinstance(call.func, ast.Name)
                    and call.func.id == "_fire" and len(call.args) >= 2):
                continue
            code = call.args[1]
            if not (isinstance(code, ast.Constant) and code.value == "STRANDED_SYNTHESIS"):
                continue
            # The verdict argument must READ the computed list. `not stranded` is a UnaryOp over
            # the bound name; anything that does not mention it is a hard-wired verdict.
            return any(isinstance(n, ast.Name) and n.id in bound
                       for n in ast.walk(call.args[0]))
        return False
    net(a, "the stranded detector files on the list it computed, not on a constant",
        stranded_detector_fires_on_what_it_computes,
        "a value computed, printed and dropped is this project's signature failure, and a queue "
        "that is blind reports the same sentence as a queue that is clear")

    def no_open_order_sits_on_a_legacy_cap_boundary():
        """HARD RULE 0, ASKED OF THE QUEUE ITSELF -- from outside the module that keeps it.

        FOUR SHIFTS OF CAP DAMAGE SURVIVED THE CAPS (orders 8dc37c208839, 3025ac8aa20f). Work
        orders were once stored truncated -- `what` at 600 characters, `where` at 200, `found_by`
        at 80, a closed row's `resolution` at 400 -- and when those caps were removed from the
        writers, nothing anywhere noticed that the ROWS ALREADY ON DISK were still cut. A stored
        field sitting exactly on one of those four numbers is the fingerprint, and for four
        shifts no instrument in this project looked for it. That order named three empty places:
        no entry in `workorders.sweep_detectors`, no check in `verify_math`, and no net here.
        The detector exists now and self-closes when the open queue is clean; this is the layer
        that does not share its failure modes.

        WHY THAT IS NOT A DUPLICATE, and it is the CLAUDE.md INDEPENDENT property spelled out. A
        detector living inside `workorders.py` cannot report `workorders.py` failing to import,
        its sweep never being run, or `_load` raising QueueUnreadable -- and from the outside
        every one of those reads byte-for-byte like a clean queue. This net calls the same
        function rather than re-deriving the measurement, because two hand-kept copies of one
        number is precisely how they come to disagree; what it adds is a SECOND CALLER, on a
        different schedule, whose failure to get an answer at all is itself a breach.

        A RATCHET, AND ONLY OVER THE OPEN QUEUE. Measured zero on the day it was written and
        zero again today, so any future non-zero is a regression and the ids are named so a
        person can look at each row rather than at a count. The CLOSED log is deliberately NOT
        graded: it is append-only history, it cannot be repaired, and a battery that fails on it
        nightly is an alarm nobody can ever silence -- which is how alarms get switched off. The
        honest figure, for the record, since this file has no channel for a measurement that is
        not a verdict: of 3,171 closed rows, 221 carry a `what` at exactly 600 and 532 a
        `resolution` at exactly 400, and 548 rows are cut in some field. Roughly a sixth of this
        project's record of its own closed work is truncated, and the 532 resolutions have no
        second copy anywhere. That is permanent. `python src/workorders.py --sweep` prints it
        fresh every sweep.
        """
        hits = W.cap_boundary_scan()["open_hits"]
        if hits:
            # THE IDS, NOT THE COUNT, and delivered through the one channel `net()` prints
            # verbatim. A person has to open each of these and decide whether the text was
            # truncated or merely happens to end there; a number tells them neither which rows
            # nor where to start. Raising is how a net says something a bare False cannot --
            # `net()` records the message in `error` and `main()` prints it under the breach --
            # and it is the same rule `_a_refusal_names_the_block_it_refused` puts on the
            # library. Not truncated on the way out, for reasons that should not need saying in
            # the net named after cap damage.
            raise AssertionError(
                "%d open work order field(s) sit exactly on a legacy cap boundary: %s"
                % (len(hits), "; ".join(sorted(str(h) for h in hits))))
        return True
    net(a, "no OPEN work order sits on a legacy cap boundary",
        no_open_order_sits_on_a_legacy_cap_boundary,
        "a stored field ending exactly on 600 / 200 / 80 / 400 is cap damage that outlived the "
        "cap, and it went unseen for four shifts because the only thing that could have looked "
        "lived inside the module keeping the queue")


def _guards_are_wired_where_claimed(src=None):
    """Each interlock must be CALLED in the file that claims it — asked of the AST.

    SATISFIED BY PROSE IN HALF ITS FILES, until run #34. It was `token in <file text>`, and
    for three of the six the token occurs only in explanation: `coverage.py:53` names
    cachekey in a docstring ("verifies via `cachekey.owns()` before believing a file"),
    `pipeline._mined_feats`'s comment above its own `cachekey.load` call, `feats.py`'s comment
    block naming cachekey near its statblock gates (cited by symbol, not by line, per order
    0c7592915a48 -- a line drifts the first time something is edited above it). Those three files
    could lose the import and every call and this net — named "every guard is present in the
    file that claims it", expectation "the last incident was a guard DELETED, not a guard
    that failed" — would have kept holding on the paragraphs describing the deleted guard.
    A guard's explanation is the part MOST likely to survive its removal.

    Call spellings resolve through each file's own imports, so `import cachekey as CK; CK.load()`
    counts and a same-named local method does not. The FIVE cache files are asked for a call
    on the MODULE, which is the honest form of "cachekey is wired in here"; the two gate
    files are asked for the specific function, because there the identity of the call is the
    whole claim.

    AND `_calls` WALKED DEAD CODE (order 78f04bec15ad, run #37). The sweep built all six
    modules UNGATED, each carrying its required call inside an `if False:`, and this net --
    the one whose expectation is "the last incident was a guard DELETED" -- reported HELD.
    Relocating a guard into a branch nothing enters deletes it just as thoroughly as removing
    it, and leaves a better-looking diff. So the question is now `_reaches_call`: starting from
    the entry point each module actually has, can the running program get to that call. That
    also closes the uncalled-helper form of the same trick, which plain `reachable=True` does
    not -- `_live_walk` descends into every `def` in a file whether or not anything calls it.

    THE ENTRY POINTS ARE NAMED PER FILE, and they are a claim in their own right. All but one
    are reached from `main`; `pipeline.py`'s cache check lives under `synthesis_blocks`, which
    is the door other modules come in through rather than its CLI. Naming the wrong door would
    make this net breach against correct code, so each was measured against the live tree before
    it was written down.

    THE COVERAGE LIST IS ITSELF A CLAIM, AND IT OMITTED THE BIGGEST SITE (order 87615a030864).
    `read.py` was not in this dict, and it is the largest cachekey call site in the tree -- the
    helper at `cache_path`, `cachekey.load`, `cachekey.write_path` -- and until the shift that
    filed this it ALSO built the per-entity evidence path by hand inside `queue()`, which is
    precisely the defect this net exists to catch. The net reported HELD across the whole time
    that fifth spelling was live, because the file containing it was not in the set. That is
    this net's own named failure shape wearing a different hat: a guard's coverage list is a
    claim, and a claim that omits the site where the guard was actually missing is a green light
    of unknown provenance. `read.py` reaches `cachekey.` from `main` by two routes (main -> run
    -> queue -> _queue_row, and main -> run -> read_entity), both measured against the live tree
    before the entry was written down.

    MODULE LEVEL, LIKE THE OTHER SOURCE-SHAPE NETS, and for the reason `_srcdir` gives: it was a
    closure carrying an unusable `src=` parameter, so the one way to prove it still refuses --
    point it at a tree with the guards moved into dead code and watch it go red -- could not be
    performed on the net itself, only on a copy of its body. A net nobody can drive against the
    defeat it exists to catch is a green light of unknown provenance.
    """
    src = src or os.path.dirname(os.path.abspath(__file__))
    want = {"generate.py": ("prose_gate.assert_gate_open", ("main",)),
            "overnight.py": ("_prose_enabled", ("main",)),
            "coverage.py": ("cachekey.", ("main",)),
            "feats.py": ("cachekey.", ("main",)),
            "pipeline.py": ("cachekey.", ("main", "synthesis_blocks")),
            "hostcheck.py": ("cachekey.", ("main",)),
            "read.py": ("cachekey.", ("main",))}
    return all(_reaches_call(_ast_of(os.path.join(src, f)), token, entries)
               for f, (token, entries) in want.items())


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

        AND IT SUMMED FOUR OF THE FIVE COLUMNS IT NAMES (order 63b8b84d7504). The paragraph above
        lists `cited`, `read`, `no_page`, `no_host` and `not_attempted`; the code left
        `not_attempted` out. Because those five sum to `entries` exactly -- re-verified today
        against the live data/COVERAGE.json: 210 rows, `not_attempted` present in every one, 0
        over and 0 under -- the four-column sum is identically `entries - not_attempted`, so it
        could only ever exceed `entries` if `not_attempted` went NEGATIVE. An entry
        double-counted into `not_attempted`, which is the M23 shape in one of the five buckets
        and the exact thing this net is named for, could not move the check at all. That is a
        docstring naming a fifth column the code did not read, in the net whose own history is a
        docstring outrunning its code, which is why the correction is written down rather than
        quietly applied.

        The equality claim stays OUT. Overflow is the direction worth grading; it simply has to
        cover every column it names.

        A NOTE ON THE ABSENT-FILE PASS below: no COVERAGE.json returns True, consistent with the
        other inspector nets, and it is the one soft edge here -- if that file is ever expected
        to exist, this is where the expectation would have to be stated.
        """
        p = path or os.path.join(HERE, "data", "COVERAGE.json")
        if not os.path.exists(p):
            return True
        rows = json.load(open(p, encoding="utf-8"))
        for r in rows:
            if not isinstance(r, dict):
                continue
            parts = sum(r.get(k, 0) for k in
                        ("cited", "read", "no_page", "no_host", "not_attempted"))
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

    net(a, "every guard is CALLED in the file that claims it", _guards_are_wired_where_claimed,
        "the last incident was a guard DELETED, not a guard that failed -- and the comment "
        "explaining it stayed behind")

    def the_meta_language_ban_is_actually_enforced():
        """A BAN NOTHING CHECKS IS A STYLE NOTE. `pipeline.assert_in_universe` rejects prose that
        breaks the in-fiction frame, and a comment near it once claimed the ban "is enforced in
        code like scale_note and the Marginalia cap before it" (that comment's line has since
        moved and is not re-cited here by number, per order 0c7592915a48). It was not: the function had ZERO
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
        #
        # AND THE CALL HAD ONLY TO EXIST SOMEWHERE IN THE FILE (order 78f04bec15ad, run #37).
        # The sweep's `generate.py` never checked a line of prose and parked the call after the
        # return; this net held. It must now be REACHED from `main`, which is the function that
        # turns a manifest into prose -- dead code and an uncalled helper both stop answering.
        return _reaches_call(_ast_of(os.path.join(_srcdir(), "generate.py")),
                             "assert_in_universe", ("main",))
    net(a, "meta-language is refused by the writer, not just noticed by an audit",
        the_meta_language_ban_is_actually_enforced,
        "one 'as a DM you might' in a finished volume breaks the frame for every entry near it")

    def liveness_sees_its_own_founding_example():
        """THE DETECTOR MUST CATCH THE CASE IT WAS WRITTEN FOR. `liveness.py:12` names
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
        """A RATCHET, not a floor. The findings counted here predate this work and deleting them
        is a separate, reviewable act. What must not happen is the number GROWING -- a new check
        that never runs is exactly how "a check that cannot fail" gets into the tree, and it is
        invisible to every other instrument because nothing red ever appears.

        The number is the SUM over every list `scan()` returns, so a limb added to the detector
        counts the moment it lands: see `LIVENESS_CEILING` for what it stands at, what the two
        lawful raises were, and how much headroom is deliberate.
        """
        import liveness
        r = liveness.scan()
        n = sum(len(v) for v in r.values())
        return n <= LIVENESS_CEILING
    net(a, "no NEW dead code or unfailable check has appeared", liveness_does_not_worsen,
        "the ceiling is a ratchet: lower it when you clean up, never raise it to go green")

    def the_reachability_primitive_understands_loop_else():
        """`_live_walk` IS THE INSTRUMENT, so a blind spot in it is a blind spot in ~two dozen
        nets at once -- every net that says "the call is made" rather than "the name appears".

        It knew that `if False:` runs its `else` and `if True:` does not, and it had BOTH loop
        cases backwards (sweep43-batch01). A loop's `else` runs when the loop ends without a
        `break`, so `while False:` runs its `else` immediately -- that was being discarded as
        dead, which turns into a false BREACH -- and `while True:` can leave only by `break`,
        `return` or `raise`, every one of which skips the `else`, so that block is provably dead
        and was being walked as live. The second is the direction that matters: it is exactly
        the "dead code read as reachable" fault the run #36 sweep used to beat
        `_halt_is_not_breakage` with an `if False:` block after a `break`, arriving through the
        loop spelling instead.

        AND THE THIRD FIXTURE IS THE SAME LOOP'S FALL-THROUGH (order 7baa1527f69c). The `else`
        repair left the OTHER unreachable block behind it: a `while True:` whose body cannot
        reach a `break` never terminates, so the statements AFTER it are dead too, and they were
        still being walked. The order measured it on this exact fixture and got both names back.
        Both halves of the same loop are asserted here, and the fourth fixture is the control --
        a `while True:` that CAN break must keep everything after it, or the repair would have
        become a false BREACH on every retry loop in the tree.

        Asserted on the two properties rather than on node counts, so a later rewrite of the
        walker is judged on what it can SEE, not on how it is built.
        """
        import ast
        live = ast.parse(
            "def f():\n"
            "    while False:\n"
            "        only_in_dead_loop_body()\n"
            "    else:\n"
            "        reached_because_loop_never_ran()\n")
        dead = ast.parse(
            "def g():\n"
            "    while True:\n"
            "        breaks_out()\n"
            "        break\n"
            "    else:\n"
            "        can_never_run()\n")
        fell_through = ast.parse(
            "def h():\n"
            "    while True:\n"
            "        the_real_behaviour()\n"
            "    the_guard_that_can_never_run()\n")
        left_by_break = ast.parse(
            "def i():\n"
            "    while True:\n"
            "        if done():\n"
            "            break\n"
            "    the_guard_that_runs_after_the_loop()\n")

        def names(tree):
            return {n.func.id for n in _live_walk(tree)
                    if isinstance(n, ast.Call) and isinstance(n.func, ast.Name)}
        seen_live, seen_dead = names(live), names(dead)
        seen_fell, seen_left = names(fell_through), names(left_by_break)
        return ("reached_because_loop_never_ran" in seen_live
                and "only_in_dead_loop_body" not in seen_live
                and "breaks_out" in seen_dead
                and "can_never_run" not in seen_dead
                and "the_real_behaviour" in seen_fell
                and "the_guard_that_can_never_run" not in seen_fell
                and "the_guard_that_runs_after_the_loop" in seen_left)
    net(a, "the reachability walker knows a loop has an else, and when it runs",
        the_reachability_primitive_understands_loop_else,
        "both loop cases were inverted: a `while True:` else was walked as live code, which is "
        "the fault that let a dead fixture make a net report HELD")


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

    def an_unparseable_reply_names_itself(src=None):
        """THE ONE FAILURE THAT WAS THE MODEL'S OWN FAULT, AND THE ONLY ONE THAT HAD NO NAME.

        `_ask_call` sets `served["outcome"] = "answered"` the moment the stream closes -- true of
        the transport, not of the call. If the provider answered with prose, an apology or a
        truncated fence, `_extract_json` returns None and the function returned None too, leaving
        the caller's `served` dict still reading "answered", with no error text and the reply
        itself discarded. Measured 2026-09-02: `--selftest` printed a bare `live call -> FAILED`
        against buckets that were answering, and nothing in `served` or in the metrics row could
        separate an unparseable answer from a dead account.

        ASKED OF THE PARSE TREE, not of the text, so a comment mentioning the fix cannot satisfy
        it -- this file's own recurring lesson (run #36, the `cascade_bridge` router net above).
        The assertion is narrow and behavioural: inside `_ask_call`, the `if` guarding the
        `_extract_json` result must not be a bare `return None`; it must write `served`. That is
        the property, and it is the property a future tidy-up would delete.
        """
        import ast
        tree = _ast_of(os.path.join(_srcdir(src), "cascade_bridge.py"))
        fn = next((n for n in ast.walk(tree)
                   if isinstance(n, ast.FunctionDef) and n.name == "_ask_call"), None)
        if fn is None:
            return False
        # The call that parses the reply, and the `if <name> is None:` that follows it.
        parsed_into = None
        for node in ast.walk(fn):
            if (isinstance(node, ast.Assign) and isinstance(node.value, ast.Call)
                    and isinstance(node.value.func, ast.Name)
                    and node.value.func.id == "_extract_json"
                    and node.targets and isinstance(node.targets[0], ast.Name)):
                parsed_into = node.targets[0].id
        if parsed_into is None:
            return False
        for node in ast.walk(fn):
            if not isinstance(node, ast.If):
                continue
            t = node.test
            if not (isinstance(t, ast.Compare) and isinstance(t.left, ast.Name)
                    and t.left.id == parsed_into
                    and any(isinstance(o, ast.Is) for o in t.ops)):
                continue
            # It must SAY something before it gives up: a subscript store into `served`.
            for sub in ast.walk(node):
                if (isinstance(sub, ast.Assign) and sub.targets
                        and isinstance(sub.targets[0], ast.Subscript)
                        and isinstance(sub.targets[0].value, ast.Name)
                        and sub.targets[0].value.id == "served"):
                    return True
            return False
        return False
    net(a, "a reply that will not parse is recorded as such, not as 'answered'",
        an_unparseable_reply_names_itself,
        "the transport succeeding is not the call succeeding, and served must not say it was")

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
        """`allow_paid` is owner-held. Nothing automatic may switch it on.

        FOUR FAULTS IN EIGHT LINES, all of them found at once (order eed51b638439).

        1. THE PATH WAS A LITERAL, AND A MALFORMED ONE. It was an r-string with DOUBLED
           backslashes, so the parsed constant carried eight of them; Windows collapses repeated
           separators and the file opened anyway, which made it latent rather than live -- an
           escaped path that is not one, inside a safety battery. It also hard-coded one
           machine's directory layout, and it reached OUT of the repository by absolute path from
           a file whose own header says every attack is built in memory or in a scratch
           directory. `CASCADE_CONFIG` above takes it from the environment instead, with this
           machine's location as the fallback, so another machine says where its config is rather
           than making this net wrong.

        2. `except Exception: return True` CONFLATED FOUR CONDITIONS -- "not this machine"
           (intended), corrupt JSON, a denied read, and a changed schema. Every one of them made
           the net unfailable, silently, which is the absence-read-as-clean shape this whole file
           exists against. They are separated now: FileNotFoundError is the honest "not this
           machine"; anything else is a measurement that did not happen and follows the ruling at
           `datasette_config_is_generated_not_copied` -- noted, not graded -- under its own name
           in the ledger, so the two are distinguishable afterwards.

        3. AND THE OTHER DIRECTION HALTED THE LIBRARY. `cfg.get("allow_paid") is False` returns
           False when the key is merely ABSENT, because None is not False. A missing key in an
           unrelated project's config file would breach this net, and a breached net escalates to
           OWNER. Absent is not switched on; the ruling is satisfied by absence and by an explicit
           False, and by nothing else -- a stringy "false" is still a breach, because that is a
           value somebody wrote, and this project has already been bitten by `bool("false")`.
        """
        import json as _j
        import silence as _si
        try:
            with open(CASCADE_CONFIG, encoding="utf-8") as fh:
                cfg = _j.load(fh)
        except FileNotFoundError:
            _si.note("drill.py:paid-lane-config-absent")
            return True          # not this machine; the ruling is still recorded in the config
        except Exception:
            _si.note("drill.py:paid-lane-config-unreadable")
            return True          # unreadable or corrupt: a measurement that did not happen
        if not isinstance(cfg, dict):
            _si.note("drill.py:paid-lane-config-unreadable")
            return True
        val = cfg.get("allow_paid")
        return val is False or val is None
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

        Asserted by DOING IT: a fresh synthetic subsystem is stopped and resumed here, and no
        order carrying THIS PROBE'S name may be open afterwards that was not open before.
        Counting is not enough -- an unrelated detector filing one order while this probe leaks
        one would net to zero -- so the identities are compared.

        SCOPED TO THIS PROBE'S OWN ROWS, WHICH IS THE OTHER HALF OF THAT SAME SENTENCE (order
        00f8ca4ab967). It compared the WHOLE open set and the WHOLE closed-log length, on two
        files every detector in the kit writes, so a different detector filing one ordinary order
        in this net's window made the sets differ -- and a breached drill net escalates to OWNER.
        The masking direction stays closed and the false-alarm direction closes with it, because
        `where` carries the synthetic subsystem name verbatim (`escalate` passes `source` through
        as `file_order`'s `where`) and no bystander can produce that string: `__drill_litter_probe__`
        is reserved, matched by `health.is_selftest`, and belongs to nothing that has ever existed.
        Same ruling as `twin_detection_does_not_match_bystanders` -- a net whose answer depends on
        what happens to be running when it looks is not testing the code.

        AND IT NOW WATCHES THE CLOSED LOG TOO, which is the half it was pointed away from
        (order c24fcbb8a291). The probe passed -- it leaves nothing OPEN -- and then littered the
        PAPER TRAIL instead, once per battery run, for ever. Measured 2026-08-29: eight such ids
        were 49.0% of the trail. Measured again one day later: 62.6%. The net checked the half of
        the queue it was pointed at, and the honest fraction of this project's record of its own
        closed work fell every day it passed. Rehearsals now go to `workorders_selftest.jsonl`,
        and this asserts the paper trail did not move -- so if a future probe stops being marked
        as one, THIS goes red rather than the trail quietly filling up again.
        """
        import escalation as E
        import workorders as WO
        name = "__drill_litter_probe__"

        def mine():
            return {i for i, o in WO._load().items()
                    if isinstance(o, dict) and o.get("where") == name}

        before = mine()
        trail_before = _rows_in(WO.CLOSED_LOG, name)
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
        return mine() == before and _rows_in(WO.CLOSED_LOG, name) == trail_before
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

        AND "BEFORE" WAS A LINE NUMBER, WHICH IS NOT A PATH (order 07c7379597ba, run #37).
        `min(asked) < min(started)` is satisfied by a consultation sitting in dead code above
        the restart, or in an unrelated arm, or with its answer thrown away -- none of which
        stops the keeper restarting a subsystem a person stopped, which is the whole incident.
        It survived only because `_keep` contains exactly one of each call today.

        The claim is now the real one, in three parts: the answer is BOUND, a reachable `if`
        conditioned on that answer `continue`s without starting anything, and every reachable
        `start` is outside that arm and after it. A guard that does not skip the restart is not
        a guard, and a restart the guard cannot precede is not gated by it.
        """
        import ast
        tree = _ast_of(os.path.join(_srcdir(), "overnight.py"))
        keep = _defn(tree, "_keep")
        if keep is None:
            return False
        answered = _bound_from_call(tree, keep, "_manager_stopped")
        if not answered:
            return False                       # asked and the answer discarded, or not asked
        started = [n for n in _live_walk(keep)
                   if isinstance(n, ast.Call) and isinstance(n.func, ast.Name)
                   and n.func.id == "start"]
        if not started:
            return False                       # a keeper that restarts nothing proves nothing
        for g in _live_walk(keep):
            if not isinstance(g, ast.If) or not _guarded_by(tree, g, answered):
                continue
            arm = _live_stmt_walk(_live_stmts(g.body))
            if not _arm_leaves(g.body, ast.Continue):
                continue                       # the stopped arm must SKIP, not fall through
            if any(x is s for x in arm for s in started):
                continue                       # ... and must not start the job it just skipped
            inside = {id(x) for x in _live_walk(g)}
            if all(id(s) not in inside and s.lineno > g.lineno for s in started):
                return True
        return False
    net(a, "the keeper checks for a MANAGER stop before re-asserting a job",
        the_keeper_asks_before_restarting,
        "the ledger existed for 25 minutes and the one process that needed it never opened it")

    def both_launchers_ask_before_spawning():
        """THE OTHER NINE LAUNCH SITES. The keeper was one of ten, and it was the only one gated.

        Order 4c1eaa9df7fa moved `_manager_stopped` out of `main()` -- where it was a closure
        with the keeper thread as its single caller -- to module level, and put the gate inside
        `overnight.start()` and `overnight.run()` themselves. Everything this file launches goes
        through one of those two: the standing set at the top of every cycle, prose, the roll,
        read, the serial pipeline and the foreman's four repairs. Before that change the keeper
        would decline to restart a subsystem a person had closed at rung 4 and the supervisor's
        own next lap would start it anyway, so the 22:5x `catalogue_web` incident was fixed for
        the one caller that had been caught doing it and for none of the others.

        The net above proved the keeper arm and its own docstring calls that "the half that
        matters"; order e0948238ef36 filed the arithmetic, which is that it was one of ten sites
        and is now one of three. So the enforcement was real and two thirds of it unwatched --
        the exact distance between "the guard exists" and "the guard is in effect" that this
        file is about.

        ASKED OF THE PARSE TREE, in the same three parts and through the same helper the keeper
        arm uses (`_gate_precedes_spawn`): the answer is bound, a reachable `if` on it returns
        without reaching the spawn, and every reachable `_guarded_popen` is outside that arm and
        after it. `_guarded_popen` rather than `subprocess.Popen` because it is the one place in
        the module where a process is actually born -- both launchers reach it and nothing else
        does -- so a gate that precedes it precedes every launch these two functions perform.

        BOTH FUNCTIONS IN ONE NET, deliberately: the claim order 4c1eaa9df7fa closed is that
        neither launcher can spawn past a rung-4 stop, and half of that is the state this net
        was written to end.
        """
        import ast
        tree = _ast_of(os.path.join(_srcdir(), "overnight.py"))
        return all(_gate_precedes_spawn(tree, _defn(tree, fname), "_manager_stopped",
                                        "_guarded_popen", (ast.Return,))
                   for fname in ("start", "run"))
    net(a, "overnight.start() and overnight.run() ask before they spawn",
        both_launchers_ask_before_spawning,
        "the gate lived beside ONE of this module's ten launch sites, so the supervisor's own "
        "next lap restarted whatever the keeper had just refused to restart")

    def an_unreadable_stop_ledger_stops_everything():
        """FAIL CLOSED. The file's only content is what must not run, so failing to read it
        cannot be permission to run things."""
        import escalation as E
        saved = E.STOPPED
        d = tempfile.mkdtemp(prefix="drill_stopped_bad_")
        E.STOPPED = os.path.join(d, "STOPPED.json")
        try:
            with open(E.STOPPED, "w", encoding="utf-8") as fh:
                fh.write("{ not json at all")
            held, why = E.subsystem_stopped("anything at all")
            return held is True
        finally:
            E.STOPPED = saved
            shutil.rmtree(d, ignore_errors=True)
    net(a, "an unreadable stop ledger reports everything stopped",
        an_unreadable_stop_ledger_stops_everything,
        "'I cannot tell whether a person closed this' is not permission to re-open it")


def _esc_sandbox():
    """A temp directory the escalation chain can be driven inside, with its side effects off.

    RETURNS a (dir, filed, restore) triple. `filed` is the list `workorders.file_order` calls
    land in while stubbed -- load-bearing, not incidental: `an_escalation_reaches_the_queue_
    addressed_and_graded` asserts against it. `restore()` puts every redirected module constant
    back and removes the directory. Written as a tuple rather than a context manager because
    `net()` takes a zero-argument callable and every probe below wants the same four
    redirections plus the recorder; a helper that both callers and `finally` blocks can name is
    easier to keep honest than four copies of the same try/finally.

    WHAT IS REDIRECTED, AND WHY EACH ONE HAS TO BE. `escalation.py` resolves its paths once, at
    import, from `HERE` -- so a probe that calls `escalate(OWNER, ...)` for real writes the
    LIVE `state/HALT.json` and halts the library, which is a battery that stops the plant every
    time it runs. HALT_FILE, LOG, SRC_LOGS and STOPPED are therefore all pointed at scratch.

    AND THE TWO SIDE EFFECTS ARE STOPPED AS WELL, which the path redirection alone does not
    reach. `escalate()` calls `health.record` and `workorders.file_order` through a late
    `import`, so both resolve out of `sys.modules` at call time and both write real files: a
    probe that raises forty synthetic escalations would file forty real work orders and forty
    real failure rows. That is the litter `drill_rung_four`'s own `_sweep_probe_litter` exists
    to clean up after two calls; at this area's volume, cleaning up afterwards is the wrong
    shape and not filing them at all is the right one. The calls still HAPPEN -- the probe below
    that asserts an escalation reaches the queue reads the recorder to prove it -- they simply
    land in a list instead of in the library's ledgers.
    """
    d = tempfile.mkdtemp(prefix="drill_escbehav_")
    saved = {k: getattr(ESC, k) for k in ("HALT_FILE", "LOG", "SRC_LOGS", "STOPPED")}
    ESC.HALT_FILE = os.path.join(d, "HALT.json")
    ESC.LOG = os.path.join(d, "escalation.log")
    ESC.SRC_LOGS = os.path.join(d, "escalations")
    ESC.STOPPED = os.path.join(d, "STOPPED.json")

    filed, recorded = [], []
    import workorders as _WO
    import health as _H
    real_file_order, real_record = _WO.file_order, _H.record
    _WO.file_order = lambda *args, **kw: filed.append((args, kw))
    _H.record = lambda *args, **kw: recorded.append((args, kw))

    def restore():
        _WO.file_order, _H.record = real_file_order, real_record
        for k, v in saved.items():
            setattr(ESC, k, v)
        shutil.rmtree(d, ignore_errors=True)

    return d, filed, restore


def _esc_probe(fn):
    """Run one behavioural probe inside a fresh sandbox. -> whatever `fn(d, filed)` returns.

    The sandbox is torn down even when the probe raises, and the raise travels: `net()` grades
    an exception during an attack as a BREACH, which is the correct reading here -- these
    probes assert on real return values, and a probe that dies has not shown the net holding.
    """
    d, filed, restore = _esc_sandbox()
    try:
        return fn(d, filed)
    finally:
        restore()


def drill_escalation_behaviour():
    """The chain of command, DRIVEN rather than read. Orders MUTANT_SURVIVED_ESCALATION_*.

    WHY THIS AREA EXISTS. `mutate.py` corrupts one token of `escalation.py` at a time and asks
    whether the whole battery notices. On the run before this was written it reported **68
    survivors in this one file** -- 68 places where `escalation.py` could be silently wrong and
    every check in the library still passed. That is not 68 defects; it is one, and it is
    structural: every net that touches this module reads its SOURCE. `_no_programmatic_clear`
    parses the tree, `_failed_revert_is_escalated` walks branches, `_halt_fails_closed` is the
    lone exception and covers a single arm of a single function. Source-shaped nets prove the
    code SAYS the right thing. None of them proves it DOES it, so `return True` became
    `return False`, `if not landed` lost its `not`, `False, "not attempted"` became
    `True, "not attempted"` -- and the battery was green for all of it.

    The distinction matters most exactly here. This module's promise is that a halt cannot be
    lifted by a program, that an unreadable ledger fails closed, and that a write which did not
    land is reported as not having landed. Every one of those is a RUNTIME property. A file
    that describes them and a file that has them are indistinguishable to a parser and are not
    remotely the same file to the library.

    So: real calls, real return values, scratch state. The nets are grouped by the function
    they drive, and each names the specific corruption it refuses -- because a net whose
    expectation is 'it works' is the kind that survives the mutation that breaks it.
    """
    a = "THE CHAIN, DRIVEN — escalation.py's runtime promises, not its source"

    # ------------------------------------------------------------------ _safe_name
    #
    # The per-source log filename. Its whole job is INJECTIVITY: "every source is its own area
    # of the park", and two sources sharing one log file is a park map with fewer areas on it
    # than the park has. Order e8cd908ce5e4 fixed the truncation; nothing ever checked the fix.

    net(a, "a source name survives sanitisation intact",
        lambda: ESC._safe_name("Kobold_Press") == "Kobold_Press",
        "with `or` flipped to `and` in the character test every alphanumeric becomes '_' and "
        "every source's log collapses into one file named for none of them")
    net(a, "an empty source name gets the documented stand-in",
        lambda: ESC._safe_name("") == "unscoped",
        "`return out or 'unscoped'` flipped to `and` returns 'unscoped' for EVERY source, "
        "which is the same collapse arriving from the other side")
    net(a, "a short name is not given a digest it does not need",
        lambda: "-" not in ESC._safe_name("Marvel"),
        "`len(out) > _NAME_MAX` flipped to `<=` suffixes every short name and truncates no "
        "long one -- it renames every existing log on disk and stops disambiguating the "
        "names that actually collide")

    def two_long_names_sharing_a_prefix_get_two_files():
        """The exact fault order e8cd908ce5e4 was filed for, asserted rather than described."""
        stem = "Kobold_Press__Midgard_Heroes_Handbook__Midgard_Worldbook"
        one, two = ESC._safe_name(stem + "__volume_one"), ESC._safe_name(stem + "__volume_two")
        return one != two and len(one) > ESC._NAME_MAX
    net(a, "two long source names sharing a 60-character prefix do NOT share a log",
        two_long_names_sharing_a_prefix_get_two_files,
        "a truncating name silently merges two areas of the park, and a person reading one "
        "source's escalations is reading another's without being told")

    # ------------------------------------------------------------------ brief()
    #
    # The whitelist that decides what each rung is told. A blacklist leaks; this is the net
    # that proves the whitelist is still a whitelist and still admits what it promises.

    def brief_keeps_what_the_rung_needs_and_drops_the_rest():
        rec = {"at": 1.0, "level_name": "SAFETY", "code": "C", "what": "W", "source": "S",
               "who": "me", "evidence": {"k": 1}, "level": 3, "secret": "must not travel"}
        out = ESC.brief(rec, ESC.SUPERVISOR)
        return ("secret" not in out and "who" not in out
                and out.get("code") == "C" and out.get("source") == "S")
    net(a, "a rung is told what it must act on and nothing else",
        brief_keeps_what_the_rung_needs_and_drops_the_rest,
        "a field added later must be admitted on purpose rather than leaking upward")

    def brief_drops_none_but_keeps_falsey():
        """`rec[k] is not None` flipped to `is None` empties every brief. A record whose
        fields are all present must come back with them; a field that is None must not."""
        rec = {"at": 0.0, "code": "", "what": "W", "source": None, "level_name": "SAFETY"}
        out = ESC.brief(rec, ESC.SAFETY)
        return out.get("what") == "W" and "source" not in out and "at" in out and "code" in out
    net(a, "brief keeps present fields and drops only the absent ones",
        brief_drops_none_but_keeps_falsey,
        "`is not None` flipped to `is None` hands every rung an empty record -- the alarm "
        "sounds and says nothing")

    # ------------------------------------------------------------------ escalate(), the rungs
    #
    # Level coercion is on the error path by construction: every call site that gets it wrong
    # is itself handling a fault. That is precisely why it was untested -- and why a mutation
    # run found a real problem, tried to report it, and watched the alarm crash instead.

    net(a, "a rung named as a string resolves to that rung",
        lambda: _esc_probe(lambda d, f: ESC.escalate("SAFETY", "C", "W")["level"] == ESC.SAFETY),
        "`escalate('OWNER', ...)` used to raise ValueError from inside an error handler; "
        "`if _named is None` flipped to `is not None` sends every correctly-named rung to "
        "MANAGER instead")
    net(a, "a rung named as a number resolves to that rung",
        lambda: _esc_probe(lambda d, f: ESC.escalate(ESC.SUPERVISOR, "C", "W")["level"]
                           == ESC.SUPERVISOR),
        "the bounds test `JANITOR <= level <= OWNER` flipped to `>` rejects every VALID rung "
        "and accepts every invalid one")

    def an_unknown_rung_lands_at_manager_with_the_bad_value_kept():
        def probe(d, filed):
            rec = ESC.escalate("MANGER", "C", "W", evidence={"keep": "me"})
            ev = rec.get("evidence") or {}
            return (rec["level"] == ESC.MANAGER
                    and ev.get("unrecognised_level") == "MANGER"
                    and ev.get("keep") == "me")
        return _esc_probe(probe)
    net(a, "a misspelled rung stops the SUBSYSTEM, never the library, and keeps the evidence",
        an_unknown_rung_lands_at_manager_with_the_bad_value_kept,
        "resolving a typo to OWNER makes `escalate('Owner ', ...)` a denial of service "
        "anyone can trigger by accident; `dict(evidence or {})` flipped to `and` throws the "
        "caller's evidence away and leaves the typo unfixable")

    net(a, "an out-of-range rung number also lands at MANAGER",
        lambda: _esc_probe(lambda d, f: ESC.escalate(99, "C", "W")["level"] == ESC.MANAGER),
        "unknown must stop something real without handing a slip of the keyboard the park")

    net(a, "the caller's name is recorded, not the process's",
        lambda: _esc_probe(lambda d, f: ESC.escalate(ESC.SAFETY, "C", "W",
                                                     who="drill-probe")["who"] == "drill-probe"),
        "`who or basename(argv[0])` flipped to `and` records the SCRIPT for every escalation, "
        "so every alarm in the log claims to come from whatever ran it")

    def evidence_travels_as_given_and_a_non_mapping_is_stringified():
        def probe(d, filed):
            keeps = ESC.escalate(ESC.SAFETY, "C", "W", evidence={"a": 1})["evidence"] == {"a": 1}
            lists = ESC.escalate(ESC.SAFETY, "C", "W", evidence=[1, 2])["evidence"] == [1, 2]
            other = ESC.escalate(ESC.SAFETY, "C", "W", evidence=7)["evidence"] == "7"
            return keeps and lists and other
        return _esc_probe(probe)
    net(a, "evidence survives as a mapping or a list, and anything else becomes text",
        evidence_travels_as_given_and_a_non_mapping_is_stringified,
        "`evidence is None or isinstance(...)` flipped to `is not None` stringifies every "
        "real evidence mapping into `\"{'a': 1}\"`, which no reader can index")

    # ------------------------------------------------------------------ escalate() -> the queue
    #
    # Severity and addressee are deliberately different axes. The map that joins them is the
    # thing a queue full of MAJORs comes from when it drifts.

    def an_escalation_reaches_the_queue_addressed_and_graded():
        def probe(d, filed):
            ESC.escalate(ESC.SAFETY, "PROBE_CODE", "probe what", source="probe-source",
                         who="drill-probe")
            if not filed:
                return False
            args, kw = filed[-1]
            return (args[0] == "PROBE_CODE" and args[2] == "RUN" and args[3] == "MAJOR"
                    and kw.get("where") == "probe-source"
                    and kw.get("found_by") == "drill-probe")
        return _esc_probe(probe)
    net(a, "every escalation becomes a work order, addressed and graded",
        an_escalation_reaches_the_queue_addressed_and_graded,
        "owner ruling 2026-08-25; `rec.get('source') or ''` flipped to `and` files every "
        "order with an EMPTY subject, so the queue can no longer say what an alarm is about")

    # ------------------------------------------------------------------ the halt, raised
    #
    # The rung that actually stops the plant. Every one of these ran against the live
    # state/HALT.json before this area existed, which is why none of them ran at all.

    def only_the_owner_rung_writes_a_halt():
        def probe(d, filed):
            ESC.escalate(ESC.MANAGER, "C", "not the top rung")
            if os.path.exists(ESC.HALT_FILE):
                return False
            ESC.escalate(ESC.OWNER, "C", "the top rung")
            return os.path.exists(ESC.HALT_FILE)
        return _esc_probe(probe)
    net(a, "a halt file appears at OWNER and at no rung below it",
        only_the_owner_rung_writes_a_halt,
        "`if level >= OWNER` flipped to `<` halts the library on every JANITOR note and "
        "lets a real OWNER fault pass without stopping anything")

    def a_raised_halt_reads_back_as_halted():
        def probe(d, filed):
            ESC.escalate(ESC.OWNER, "PROBE_HALT", "probe what")
            halted, rec = ESC.status()
            return halted is True and rec.get("code") == "PROBE_HALT" and rec.get("ruling") is None
        return _esc_probe(probe)
    net(a, "a halt that was raised reads back as standing",
        a_raised_halt_reads_back_as_halted,
        "`'cleared': False` flipped to True in the payload means every halt is born already "
        "lifted -- the alarm is written down and nothing obeys it")

    def the_verdict_travels_on_the_record():
        def probe(d, filed):
            return ESC.escalate(ESC.OWNER, "C", "W").get("halt_landed") is True
        return _esc_probe(probe)
    net(a, "the record says whether the halt actually landed",
        the_verdict_travels_on_the_record,
        "run #34: `landed = False` left unchanged reports every successful halt as not "
        "raised, and `landed = True` reports every FAILED one as raised -- which is the "
        "failure the whole verdict was added to expose")

    # THE SAME QUESTION ONE RUNG DOWN, and the one the ledger routes on. Landed 2026-09-06
    # from handoff/nets_20260906/safety.py (orders cd76813c39bc, 5bbbb65e7787).
    def a_lost_escalation_says_so_on_the_record():
        """THE JANITOR'S RUNG REPORTS WHETHER IT ACTUALLY TOOK THE ALARM DOWN.

        `escalate()` used to call `_append_log(rec)` bare -- no assignment, no branch, nothing
        placed on the record -- and `_append_log` itself answered for `state/escalation.log`
        alone, dropping the per-source append's verdict on the floor one line later. So the
        record handed back to whoever raised the alarm was byte-identical whether the alarm was
        written down or lost. At rungs 1-4 the log IS the whole enforcement: OPERATOR,
        SUPERVISOR and SAFETY neither raise a halt nor write a state file, so a lost append
        leaves no trace a person can find.

        BOTH APPENDS, SEPARATELY, because the per-source half is the one that was invisible and
        a net that only refuses the both-denied case would pass over it. And the landed case
        too: a `recorded` that is always False is the same defect facing the other way.
        """
        def probe(d, filed):
            import silence as SI
            real = SI.append_line
            try:
                if ESC.escalate(ESC.SUPERVISOR, "C", "W", source="S").get("recorded") is not True:
                    return False                      # a landed escalation must say so

                SI.append_line = lambda *a, **kw: False
                if ESC.escalate(ESC.SUPERVISOR, "C", "W", source="S").get("recorded") is not False:
                    return False                      # every append refused

                def only_the_area_log_fails(path, line):
                    if os.path.basename(os.path.dirname(path)) == "escalations":
                        return False
                    return real(path, line)

                SI.append_line = only_the_area_log_fails
                # THE HALF THAT USED TO BE LOST: state/escalation.log lands, the source's own
                # log does not, and the verdict must still be False.
                return ESC.escalate(ESC.SUPERVISOR, "C", "W",
                                    source="S").get("recorded") is False
            finally:
                SI.append_line = real
        return _esc_probe(probe)
    net(a, "an escalation that could not be written down says so on its own record",
        a_lost_escalation_says_so_on_the_record,
        "at rungs 1-4 the log is the whole enforcement, and the record used to read as filed "
        "whether it was filed or lost -- the defect already repaired one rung up (halt_landed) "
        "and one rung down (stop_recorded)")


    def the_escalations_source_travels_to_the_failure_ledger():
        """`health.is_selftest` matches `__drill[A-Za-z0-9_]*__` against the composed key AND
        against `subject`, and only the key used to be offered. Six of the seven live drill rows
        embed the marker somewhere inside the key; the seventh --
        `escalation:SUPERVISOR:DRILL_AREA:drill: one area closing`, whose marker is in `source`
        and nowhere in the key -- cannot be caught by ANY reading of the key. The caller has to
        say, and `escalate()` is the caller that knows."""
        def probe(d, filed):
            import health as _H
            seen = []
            real = _H.record
            _H.record = lambda *args, **kw: seen.append(kw.get("subject"))
            try:
                ESC.escalate(ESC.SUPERVISOR, "DRILL_AREA", "drill: one area closing",
                             source="__drill__")
            finally:
                _H.record = real
            return seen == ["__drill__"]
        return _esc_probe(probe)
    net(a, "an escalation hands the failure ledger its SOURCE, not only its key",
        the_escalations_source_travels_to_the_failure_ledger,
        "state/failures.json is the ledger a person reads to find real faults, and one of "
        "drill.py's own rehearsals could not be told from a real SUPERVISOR-rung area closure "
        "by any reading of the composed key")

    def a_second_fault_corroborates_and_does_not_bury_the_first():
        def probe(d, filed):
            ESC.escalate(ESC.OWNER, "FIRST", "the first thing that went wrong")
            ESC.escalate(ESC.OWNER, "SECOND", "a louder later symptom")
            halted, rec = ESC.status()
            also = rec.get("also") or []
            return (halted and rec.get("code") == "FIRST" and len(also) == 1
                    and also[0].get("code") == "SECOND")
        return _esc_probe(probe)
    net(a, "a second fault while halted is appended, never written over the first",
        a_second_fault_corroborates_and_does_not_bury_the_first,
        "the FIRST thing that went wrong is the one a person needs; "
        "`not cur.get('cleared', False)` flipped to True replaces it with the symptom")

    def a_halt_that_loses_the_race_is_kept_as_corroboration():
        """The compare-and-swap's conflict path, driven deterministically.

        BUGS.md M38's remaining limb: `_raise_halt` did an unlocked read-modify-write, so two
        processes raising a FIRST halt at once each read "no halt" and whichever renamed second
        REPLACED the other's -- one OWNER fault lost, silently, on a successful write.

        WHY THIS IS NOT A THREADED RACE TEST, AND THE MEASUREMENT THAT DECIDED IT. A threaded
        version of this net was written first and MEASURED: 25 trials of two concurrent first
        halts lost a fault in 1 of them, and at four writers in 7 of 25. The compare-and-swap
        plus read-back is a large improvement -- the same harness against the ORIGINAL code lost
        a fault in 25 of 25 trials at both widths, 75 faults in total at four writers -- but it
        does NOT close the race, because `replace_if_unchanged` re-reads its digest immediately
        before `os.replace` and that pair is not atomic. A net that fails 1 run in 25 would raise
        a spurious OWNER halt roughly every twenty-fifth battery, and a flaky safety is worse
        than an absent one: it teaches people that a red drill means nothing. The residual is
        recorded as an order instead, with the numbers, and M38 stays open on that limb.

        What IS deterministic, and is what the new machinery has to get right, is the CONFLICT
        PATH: when the file moves under us, our fault must end up in the winner's `also` rather
        than being dropped or overwriting them. A competitor is landed exactly once, between our
        digest and our rename, by making the first `replace_if_unchanged` refuse the way a real
        collision refuses.
        """
        d, filed, restore = _esc_sandbox()
        real = ESC.silence.replace_if_unchanged
        state = {"first": True}

        def collides_once(tmp, dst, expected, attempts=5):
            if state["first"]:
                state["first"] = False
                ESC.silence.write_json(dst, {
                    "raised_at": 0.0, "code": "COMPETITOR", "what": "this one landed first",
                    "evidence": None, "source": None, "by": "probe",
                    "cleared": False, "ruling": None, "also": []}, indent=1)
                ESC._unlink(tmp)
                return False, "%s changed under this writer" % os.path.basename(dst)
            return real(tmp, dst, expected, attempts)
        try:
            ESC.silence.replace_if_unchanged = collides_once
            rec = ESC.escalate(ESC.OWNER, "OURS", "the fault that lost the race")
            ESC.silence.replace_if_unchanged = real
            halted, cur = ESC.status()
            also = [x.get("code") for x in (cur.get("also") or [])]
            return (halted is True
                    and cur.get("code") == "COMPETITOR"      # the winner keeps the top slot
                    and "OURS" in also                       # and ours is NOT lost
                    and rec.get("halt_landed") is True)      # and we are told it landed
        finally:
            ESC.silence.replace_if_unchanged = real
            restore()
    net(a, "a halt that loses the write race is kept as corroboration, not dropped",
        a_halt_that_loses_the_race_is_kept_as_corroboration,
        "BUGS.md M38: an unlocked read-modify-write on the one ledger that must never lose a "
        "fault -- the loser's OWNER escalation used to disappear on a SUCCESSFUL write, and "
        "`halt_landed: True` said it had not")

    def a_cleared_halt_is_replaced_not_appended_to():
        def probe(d, filed):
            ESC.escalate(ESC.OWNER, "OLD", "an old fault, since ruled on")
            rec = ESC._read_halt_raw()
            rec["cleared"] = True
            ESC.silence.write_json(ESC.HALT_FILE, rec, indent=1)
            ESC.escalate(ESC.OWNER, "NEW", "a new fault after the lift")
            cur = ESC._read_halt_raw()
            return cur.get("code") == "NEW" and not cur.get("also") and cur.get("cleared") is False
        return _esc_probe(probe)
    net(a, "a NEW fault after a lift starts a new halt rather than joining the old one",
        a_cleared_halt_is_replaced_not_appended_to,
        "appending to a cleared halt leaves `cleared: true` standing, so the new fault is "
        "recorded inside a halt that nothing obeys")

    # ------------------------------------------------------------------ the halt, read
    #
    # FAIL CLOSED is this module's second declared property. It had exactly one net.

    net(a, "no halt file at all is the only thing that means clear",
        lambda: _esc_probe(lambda d, f: ESC.status() == (False, None)),
        "`return False, None` flipped to `True, None` halts a library with no halt in it, "
        "and every job refuses forever with nothing to read")

    def a_cleared_halt_is_not_a_halt():
        def probe(d, filed):
            ESC.silence.write_json(ESC.HALT_FILE, {"cleared": True, "code": "OLD", "ruling": "ruled"})
            halted, rec = ESC.status()
            return halted is False and rec is not None
        return _esc_probe(probe)
    net(a, "a halt a person has ruled on is not standing",
        a_cleared_halt_is_not_a_halt,
        "`(not rec.get('cleared', False))` flipped to a bare True never lets the library "
        "start again -- the lift becomes unreachable and only a file deletion helps")

    def every_wrong_shape_reads_as_halted():
        """Valid JSON of the WRONG SHAPE is the shape a half-written file most easily takes."""
        def probe(d, filed):
            for blob in ("null", "[]", '"halted"', "3"):
                with open(ESC.HALT_FILE, "w", encoding="utf-8") as f:
                    f.write(blob)
                halted, rec = ESC.status()
                if not (halted and (rec or {}).get("code") == "HALT_FILE_UNREADABLE"
                        and rec.get("unreadable") is True):
                    return False
            return True
        return _esc_probe(probe)
    net(a, "a halt file of the wrong SHAPE reads as halted, not as absent",
        every_wrong_shape_reads_as_halted,
        "`if rec is None` flipped to `is not None`, or `not isinstance(rec, dict)` losing its "
        "`not`, hands a list or a bare string straight back and every caller gets "
        "AttributeError where the fail-closed promise says SystemHalted")

    def assert_clear_is_the_interlock():
        def probe(d, filed):
            if ESC.assert_clear("probe") is not True:
                return False
            ESC.escalate(ESC.OWNER, "PROBE_HALT", "probe what")
            try:
                ESC.assert_clear("probe")
                return False
            except ESC.SystemHalted as e:
                return ESC.HALT_REFUSAL in str(e) and "PROBE_HALT" in str(e)
        return _esc_probe(probe)
    net(a, "assert_clear passes a running library and refuses a halted one, by name",
        assert_clear_is_the_interlock,
        "this is the rung that makes the chain real; without it a halt is a note in a file "
        "that the running jobs never read")

    def the_destructive_tool_asks_before_it_moves_anything():
        """The interlock is only real where it is WIRED, and this was the gap (bd107a18b13e).

        `withdraw_chapters.py` `shutil.move`s every catalogued chapter out of the library, moves
        every unclaimed stray in `output/raw`, and rewrites `output/index/catalog.json` -- the
        file `generate.py` and `publish.py` both read. It MOVES rather than copies, so the
        archive is the only copy afterwards. It was the one tool in its batch with an
        irreversible action and the one not calling `assert_clear`.

        DRIVEN, NOT READ. `verify_math`'s `_INTERLOCKED` roster now covers the two SOURCE
        properties (no fail-open `except ImportError: pass`, and a "REFUSING TO" sentence). This
        asks the behavioural question those cannot: with a halt actually standing, does `main()`
        raise before it touches anything? Run with `--go` -- the destructive form -- on purpose:
        a net that only proves the dry run refuses proves nothing about the run that moves files.
        """
        import withdraw_chapters as WC
        d, filed, restore = _esc_sandbox()
        argv = sys.argv
        try:
            ESC.silence.write_json(ESC.HALT_FILE, {
                "raised_at": 0.0, "code": "DRILL_SYNTHETIC_HALT",
                "what": "a synthetic standing halt for the interlock probe",
                "by": "drill.py", "source": None, "cleared": False, "ruling": None, "also": []})
            sys.argv = ["withdraw_chapters.py", "--go"]
            return _refuses(WC.main, ESC.SystemHalted)
        finally:
            sys.argv = argv
            restore()
    net(a, "the tool that MOVES chapters out of the library asks about the halt first",
        the_destructive_tool_asks_before_it_moves_anything,
        "a halt is raised when a library-wide invariant has been violated, and moving the "
        "chapters out and rewriting the index of them is the last thing that should proceed "
        "on uncertain ground -- the move is one-way, so the archive is the only copy")

    # THE SECOND TOOL IN THAT CLASS, found by the same reasoning (order 77950336e3aa,
    # landed 2026-09-06 from handoff/nets_20260906/safety.py). Same shape as the net
    # directly above, including the `--go` on purpose.
    def the_tool_that_deletes_mined_evidence_asks_about_the_halt():
        """`hostcheck --purge --go` empties `entries` in every matching data/records/*.json and
        then os.remove()s every cached page under data/feats/<host>/ and data/readfeats/<host>/
        -- the only supporting evidence for the entries being removed, deleted one way.
        `--repair` and `--adopt --go` rewrite WIKI_HOSTS.json, which hostcheck.py itself calls
        one of the two files not reconstructible from anything else on disk. None of the three
        asked about the plant-wide halt.

        THE DRY RUNS AND THE READ-ONLY SWEEP ARE ASSERTED UNGATED, and that half is not padding:
        a measurement that cannot be retaken is abandoned rather than deferred
        (completeness.host_reachable), and a gate that swallowed the shortlist a person reads
        before deciding what to purge would be over-eager safety of the shape this project keeps
        having to walk back."""
        import hostcheck as HC
        import weave_index as WI
        d = tempfile.mkdtemp(prefix="drill_hostcheck_halt_")
        saved_halt = ESC.HALT_FILE
        saved = {k: getattr(HC, k) for k in ("ROSTERS", "entities_by_source",
                                             "_land_hosts", "_land")}
        real_records = WI.load_records
        try:
            ESC.HALT_FILE = os.path.join(d, "HALT.json")
            with open(ESC.HALT_FILE, "w", encoding="utf-8") as f:
                json.dump({"code": "DRILL", "what": "a synthetic halt", "by": "drill",
                           "cleared": False}, f)
            if not ESC.status()[0]:
                return False              # the synthetic halt must actually stand
            # Second line of defence: with the gate removed, none of these can move anything.
            HC.ROSTERS = os.path.join(d, "no-such-roster-audit.json")
            HC.entities_by_source = lambda: {}
            HC._land_hosts = lambda *a, **kw: (False, "drill: writing is stubbed out")
            HC._land = lambda *a, **kw: False
            WI.load_records = lambda *a, **kw: []

            def refuses(fn):
                try:
                    fn()
                except ESC.SystemHalted:
                    return True
                return False

            if not refuses(lambda: HC.purge(dry=False, only=["__drill_source__"])):
                return False
            if not refuses(lambda: HC.adopt(dry=False, workers=1)):
                return False
            if not refuses(lambda: HC.sweep(repair=True, workers=1)):
                return False
            if refuses(lambda: HC.purge(dry=True, only=["__drill_source__"])):
                return False              # a shortlist is a measurement
            if refuses(lambda: HC.sweep(repair=False, workers=1)):
                return False              # so is a read-only sweep
            os.remove(ESC.HALT_FILE)
            return not refuses(lambda: HC.sweep(repair=True, workers=1))
        finally:
            ESC.HALT_FILE = saved_halt
            WI.load_records = real_records
            for k, v in saved.items():
                setattr(HC, k, v)
            shutil.rmtree(d, ignore_errors=True)
    net(a, "the tool that DELETES mined evidence asks about the halt first",
        the_tool_that_deletes_mined_evidence_asks_about_the_halt,
        "purge --go deletes the only copy of the evidence for the entries it removes, and every "
        "decision it makes is made from the state a halt says is untrustworthy")

    # ------------------------------------------------------------------ clear(), the asymmetry
    #
    # An autonomous run may RAISE a halt; only a person may lift one. `_no_programmatic_clear`
    # proves no CALLER exists in src/. These prove the CAPABILITY refuses.

    net(a, "a halt cannot be lifted by a program, whatever it calls itself",
        lambda: _esc_probe(lambda d, f: _refuses(
            lambda: ESC.clear("a ruling long enough to pass the words test"), PermissionError)),
        "the incident this chain exists for was an automated agent removing a safety it had "
        "concluded was unnecessary; the three identity tests in `_by_a_person_at_the_cli` are "
        "one flipped `==` away from admitting every caller")

    net(a, "a lift with no ruling is refused, and refused FIRST",
        lambda: _esc_probe(lambda d, f: _refuses(lambda: ESC.clear(""), ValueError)
                           and _refuses(lambda: ESC.clear("ok"), ValueError)),
        "order of refusals is part of the contract: a caller check running ahead of the "
        "ruling check answers these probes with the wrong refusal and leaves the ruling "
        "rule untested")

    # ------------------------------------------------------------------ rung four, read back
    #
    # `drill_rung_four` proves a stop is recorded and that resuming demands a ruling. These are
    # the arms it does not reach: the fail-closed read, and the refusals that return False.

    def an_unreadable_stop_ledger_stops_everything():
        def probe(d, filed):
            with open(ESC.STOPPED, "w", encoding="utf-8") as f:
                f.write("[]")
            held, why = ESC.subsystem_stopped("anything-at-all")
            return held is True and "not an object" in why
        return _esc_probe(probe)
    net(a, "a stop ledger of the wrong shape reports EVERY subsystem stopped",
        an_unreadable_stop_ledger_stops_everything,
        "the file only exists to say what must not run, so failing to read it cannot be "
        "permission to run things; this arm failed OPEN until run #36 found it")

    def a_stop_reads_back_with_its_reason_and_its_author():
        def probe(d, filed):
            ESC.stop_subsystem("probe-sub", "a probe reason", who="drill-probe")
            held, why = ESC.subsystem_stopped("probe-sub")
            clear_, _ = ESC.subsystem_stopped("some-other-sub")
            return held is True and "a probe reason" in why and "drill-probe" in why and not clear_
        return _esc_probe(probe)
    net(a, "a stopped subsystem reads back stopped, and its neighbours do not",
        a_stop_reads_back_with_its_reason_and_its_author,
        "a fault in one source must never close the park; `return True, ...` flipped in the "
        "hit arm reports every subsystem running while the ledger says otherwise")

    def the_stop_verdict_travels_on_the_record():
        def probe(d, filed):
            return ESC.stop_subsystem("probe-sub", "r", who="p").get("stop_recorded") is True
        return _esc_probe(probe)
    net(a, "the record says whether the stop was actually written down",
        the_stop_verdict_travels_on_the_record,
        "`landed, detail = False, 'not attempted'` flipped to True reports a stop that was "
        "never recorded as recorded -- the twenty-five-minute failure, restored")

    def resuming_something_that_is_not_stopped_is_refused():
        def probe(d, filed):
            return ESC.resume_subsystem("never-stopped", "a ruling long enough to pass") is False
        return _esc_probe(probe)
    net(a, "resuming a subsystem that was never stopped returns False",
        resuming_something_that_is_not_stopped_is_refused,
        "`if str(name) not in doc` flipped to `in` refuses every REAL resume and accepts "
        "every meaningless one, so a genuinely stopped subsystem can never be re-opened")

    def a_resume_lifts_the_stop_and_leaves_the_others_standing():
        def probe(d, filed):
            ESC.stop_subsystem("sub-a", "reason a", who="p")
            ESC.stop_subsystem("sub-b", "reason b", who="p")
            ok = ESC.resume_subsystem("sub-a", "a ruling long enough to pass the words test")
            a_held, _ = ESC.subsystem_stopped("sub-a")
            b_held, _ = ESC.subsystem_stopped("sub-b")
            return ok is True and a_held is False and b_held is True
        return _esc_probe(probe)
    net(a, "a resume lifts exactly its own stop",
        a_resume_lifts_the_stop_and_leaves_the_others_standing,
        "the compare-and-swap exists because two concurrent stops each read the map and the "
        "second writer lands a snapshot taken before the first's stop existed")

    def a_resume_over_an_unreadable_ledger_writes_nothing():
        def probe(d, filed):
            with open(ESC.STOPPED, "w", encoding="utf-8") as f:
                f.write("[]")
            ok = ESC.resume_subsystem("anything", "a ruling long enough to pass the words test")
            with open(ESC.STOPPED, encoding="utf-8") as f:
                return ok is False and f.read().strip() == "[]"
        return _esc_probe(probe)
    net(a, "a resume never writes over a stop ledger nobody could read",
        a_resume_over_an_unreadable_ledger_writes_nothing,
        "the fault `binding_health.quarantine` was repaired for: writing through the "
        "unreadable case lands the marker itself and destroys every standing stop")

    # ------------------------------------------------------------------ _append, the janitor
    #
    # The lowest rung, on duty at all hours. Its return value is the only thing that says
    # whether the record that outlives the process actually got written.

    def the_janitor_writes_and_says_so():
        def probe(d, filed):
            path = os.path.join(d, "deep", "deeper", "j.log")
            first = ESC._append(path, {"a": 1})
            second = ESC._append(path, {"a": 2})
            with open(path, encoding="utf-8") as f:
                rows = [json.loads(line) for line in f if line.strip()]
            return first is True and second is True and len(rows) == 2
        return _esc_probe(probe)
    net(a, "the janitor's log is created, appended to, and reports that it landed",
        the_janitor_writes_and_says_so,
        "`exist_ok=True` flipped to False makes the SECOND record of any run fail; "
        "`return True` flipped to False says every successful write failed")

    def the_janitor_reports_a_write_it_could_not_make():
        def probe(d, filed):
            blocker = os.path.join(d, "blocker")
            with open(blocker, "w", encoding="utf-8") as f:
                f.write("a file where a directory would have to be")
            return ESC._append(os.path.join(blocker, "sub", "j.log"), {"a": 1}) is False
        return _esc_probe(probe)
    net(a, "a janitor write that could not happen is reported as not having happened",
        the_janitor_reports_a_write_it_could_not_make,
        "`return False` flipped to True in the handler reports every lost record as kept, "
        "which is the one thing the bottom rung must never do")

    def the_record_keeps_the_characters_it_was_given():
        def probe(d, filed):
            path = os.path.join(d, "j.log")
            ESC._append(path, {"what": "Skånska — a source with a name"})
            with open(path, encoding="utf-8") as f:
                raw = f.read()
            return "Skånska" in raw and "\\u" not in raw
        return _esc_probe(probe)
    net(a, "a record is written in the characters it was given, not in escapes",
        the_record_keeps_the_characters_it_was_given,
        "`ensure_ascii=False` flipped to True turns every non-ASCII source name in the "
        "ledgers into `\\uXXXX`, and the person reading the log at the worst moment is the "
        "one who has to decode it")

    net(a, "an escalation with no named author records the program that raised it",
        lambda: _esc_probe(lambda d, f: ESC.escalate(ESC.SAFETY, "C", "W")["who"]
                           not in (None, "", "?")),
        "`sys.argv[0] or '?'` flipped to `and` records a bare '?' for every escalation that "
        "does not name itself, so the log cannot say which job raised the alarm")

    # ------------------------------------------------------------------ the write that did NOT land
    #
    # Run #34's finding, and the reason `halt_landed` exists at all: on Windows the rename is
    # DENIED while any reader holds the target, and this file HAS readers on their own clocks.
    # A halt that did not land is a halt every other process's assert_clear() will not find.
    # Nothing exercised these arms, because nothing could make the write fail on purpose.

    def _with_refused_writes(d, fn, raising=False):
        """Run `fn` with EVERY landing mechanism refused (or raising). -> fn's answer.

        BOTH SPELLINGS, AND THAT IS THE POINT. This stubbed `silence.write_json` alone, and when
        `_raise_halt` was compare-and-swapped it moved to `silence.replace_if_unchanged` -- so
        four nets in this area went red against CORRECT code, because the helper was pinned to
        one spelling of "land a file" rather than to the property. That is the same defect
        `_failed_revert_is_escalated` was filed for one directory over: a net that names an
        implementation instead of a behaviour breaks when the implementation improves, and in
        this file a breach is an OWNER halt of a working library.

        The two have different contracts and the stub honours both: `write_json` answers a bool,
        `replace_if_unchanged` answers `(landed, why)`. `why` is "raised" rather than "changed"
        deliberately -- "changed" means a competing writer got there first, which `_raise_halt`
        RETRIES, and a probe that returned it would spin instead of testing the refusal path.
        """
        real_json = ESC.silence.write_json
        real_cas = ESC.silence.replace_if_unchanged

        def refuse_json(*args, **kw):
            if raising:
                raise OSError("refused on purpose")
            return False

        def refuse_cas(*args, **kw):
            if raising:
                raise OSError("refused on purpose")
            return False, "raised"
        ESC.silence.write_json = refuse_json
        ESC.silence.replace_if_unchanged = refuse_cas
        try:
            return fn()
        finally:
            ESC.silence.write_json = real_json
            ESC.silence.replace_if_unchanged = real_cas

    def a_refused_halt_write_is_reported_as_not_raised():
        def probe(d, filed):
            rec = _with_refused_writes(d, lambda: ESC.escalate(ESC.OWNER, "PROBE", "probe what"))
            if rec.get("halt_landed") is not False:
                return False
            with open(ESC.LOG, encoding="utf-8") as f:
                rows = [json.loads(line) for line in f if line.strip()]
            second = [r for r in rows if r.get("code") == "HALT_NOT_RAISED"]
            return (len(second) == 1
                    and second[0].get("evidence", {}).get("halt_landed") is False
                    and second[0].get("evidence", {}).get("of_code") == "PROBE"
                    and second[0].get("halt_landed") is False)
        return _esc_probe(probe)
    net(a, "a halt whose write was refused is recorded as NOT having been raised",
        a_refused_halt_write_is_reported_as_not_raised,
        "run #34: the verdict used to stop one frame short, so the actor that escalated to "
        "OWNER could not tell a halt that took from one that never appeared -- and when it "
        "never appears every other process carries straight on")

    def a_halt_write_that_throws_is_also_reported():
        def probe(d, filed):
            rec = _with_refused_writes(
                d, lambda: ESC.escalate(ESC.OWNER, "PROBE", "probe what"), raising=True)
            return rec.get("halt_landed") is False
        return _esc_probe(probe)
    net(a, "a halt write that raises is reported as not raised, not as raised",
        a_halt_write_that_throws_is_also_reported,
        "`return False` flipped to True in the one handler that is allowed to be loud on "
        "stderr reports the worst case in the module as a success")

    def a_halt_keeps_the_characters_of_the_fault_it_records():
        def probe(d, filed):
            ESC.escalate(ESC.OWNER, "PROBE", "the source Skånska broke an invariant")
            with open(ESC.HALT_FILE, encoding="utf-8") as f:
                raw = f.read()
            return "Skånska" in raw and "\\u" not in raw
        return _esc_probe(probe)
    net(a, "the halt file is written in the characters of the fault it records",
        a_halt_keeps_the_characters_of_the_fault_it_records,
        "the halt file is what a person opens at the worst moment; escaping the one field "
        "that names what broke is a cost paid exactly then")

    # ------------------------------------------------------------------ fail closed on a MISSING key
    #
    # A half-written or hand-edited halt record is the realistic corruption, and `cleared` is
    # the field the whole interlock turns on. Its ABSENCE must read as standing, not as lifted.

    def a_halt_record_with_no_cleared_key_is_standing():
        def probe(d, filed):
            ESC.silence.write_json(ESC.HALT_FILE, {"code": "OLD", "what": "a fault"}, indent=1)
            halted, rec = ESC.status()
            return halted is True and rec.get("code") == "OLD"
        return _esc_probe(probe)
    net(a, "a halt record that has lost its `cleared` field is treated as STANDING",
        a_halt_record_with_no_cleared_key_is_standing,
        "`rec.get('cleared', False)` with its default flipped to True lifts every halt whose "
        "record was truncated mid-write -- a halt that a corrupted file can lift is not a halt")

    def a_second_fault_corroborates_a_halt_that_lost_its_cleared_key():
        def probe(d, filed):
            ESC.silence.write_json(ESC.HALT_FILE, {"code": "OLD", "what": "a fault"}, indent=1)
            ESC.escalate(ESC.OWNER, "NEW", "a second fault")
            cur = ESC._read_halt_raw()
            also = cur.get("also") or []
            return cur.get("code") == "OLD" and len(also) == 1 and also[0].get("code") == "NEW"
        return _esc_probe(probe)
    net(a, "a new fault does not overwrite a halt whose `cleared` field is missing",
        a_second_fault_corroborates_a_halt_that_lost_its_cleared_key,
        "the same default, one function along: with it flipped the standing halt is replaced "
        "and the FIRST thing that went wrong -- the one a person needs -- is gone")

    # ------------------------------------------------------------------ rung four, the failures
    #
    # `stop_subsystem`'s whole point is that the stop OUTLIVES the process that set it. Every
    # arm that reports it did not is below, because each one flipped to True reports the
    # twenty-five-minute failure as a stop that was written down.

    def _stop_reports_failure(d, break_it):
        real_read, real_write = ESC._read_stopped, ESC._write_stopped
        break_it()
        try:
            return ESC.stop_subsystem("probe-sub", "a reason", who="p").get("stop_recorded")
        finally:
            ESC._read_stopped, ESC._write_stopped = real_read, real_write

    def a_stop_that_could_not_be_read_is_not_recorded():
        def probe(d, filed):
            def boom():
                def raise_it():
                    raise OSError("unreadable on purpose")
                ESC._read_stopped = raise_it
            return _stop_reports_failure(d, boom) is False
        return _esc_probe(probe)
    net(a, "a stop over a ledger that could not be read at all is reported as not recorded",
        a_stop_that_could_not_be_read_is_not_recorded,
        "`landed, detail = False, ...` flipped to True in the read handler tells the caller "
        "the subsystem is closed while nothing on disk says so")

    def a_stop_over_an_unreadable_ledger_is_not_recorded():
        def probe(d, filed):
            with open(ESC.STOPPED, "w", encoding="utf-8") as f:
                f.write("[]")
            rec = ESC.stop_subsystem("probe-sub", "a reason", who="p")
            with open(ESC.STOPPED, encoding="utf-8") as f:
                untouched = f.read().strip() == "[]"
            return rec.get("stop_recorded") is False and untouched
        return _esc_probe(probe)
    net(a, "a stop never writes over a ledger nobody could read, and says it did not land",
        a_stop_over_an_unreadable_ledger_is_not_recorded,
        "writing through the unreadable case lands the marker itself and destroys every "
        "standing stop -- the fault `binding_health.quarantine` was repaired for")

    def a_stop_whose_temp_copy_failed_is_not_recorded():
        def probe(d, filed):
            def boom():
                def raise_it(*args, **kw):
                    raise OSError("temp copy refused on purpose")
                ESC._write_stopped = raise_it
            return _stop_reports_failure(d, boom) is False
        return _esc_probe(probe)
    net(a, "a stop whose temp copy could not be written is reported as not recorded",
        a_stop_whose_temp_copy_failed_is_not_recorded,
        "a stop is already an emergency; it must not also become a traceback at its caller, "
        "and it must never be reported as taken when it was not")

    def a_resume_whose_write_failed_leaves_the_subsystem_stopped():
        def probe(d, filed):
            ESC.stop_subsystem("probe-sub", "a reason", who="p")
            real = ESC._write_stopped

            def raise_it(*args, **kw):
                raise OSError("temp copy refused on purpose")
            ESC._write_stopped = raise_it
            try:
                ok = ESC.resume_subsystem("probe-sub",
                                          "a ruling long enough to pass the words test")
            finally:
                ESC._write_stopped = real
            held, _ = ESC.subsystem_stopped("probe-sub")
            return ok is False and held is True
        return _esc_probe(probe)
    net(a, "a resume that could not be written leaves the stop standing and says so",
        a_resume_whose_write_failed_leaves_the_subsystem_stopped,
        "order 4f290dae34ef: the operator got a traceback while the subsystem was still "
        "stopped on disk; reporting it as resumed instead is the same fault told as good news")

    def a_stop_that_was_never_recorded_closes_only_a_FALSE_order():
        """THE RECHECK AFTER AN UNRECORDABLE STOP -- three worlds, and only one closes an order.

        `stop_subsystem` escalates to MANAGER before it touches any disk, and `escalate` turns
        every escalation into a work order -- so a MAJOR order keyed (SUBSYSTEM_STOPPED, name)
        exists saying the subsystem is stopped. If the write to `state/STOPPED.json` then never
        lands, that order is FALSE and order b1ffe2a0e293 closes it. But `landed` False does not
        by itself prove the subsystem is running: the name may have been stopped by an earlier
        call that DID land, in which case the order is true and closing it erases a live alarm.
        So the ledger is re-read, and the order is closed only where it positively shows the
        name absent.

        TWO MUTANTS, BOTH IN THIS BLOCK AND BOTH FAIL-OPEN (orders 3d88887246d3 and
        8c02de6742ee, both in `stop_subsystem`'s post-write recheck -- cited by symbol, not by
        line, per order 0c7592915a48). `_still_stopped = True` on an unreadable
        ledger -> False closes a SUBSYSTEM_STOPPED order that is still true; `if not
        _still_stopped:` losing its `not` closes the order exactly when the subsystem IS
        stopped. Both survived because nothing in the battery arranges a stop whose write
        fails -- the branch was unreachable, so every line in it was free.

        THREE WORLDS, because each mutant is invisible in the other two:

          * the write is denied and the ledger does NOT hold the name -- the order is false and
            must be CLOSED. This is the only world in which anything is closed at all, and
            without it the `not` could be dropped for nothing;
          * the write is denied and the ledger DOES hold the name, from an earlier stop that
            landed -- the order is TRUE and nothing may be closed. This kills the dropped `not`;
          * the ledger cannot be asked at all -- `subsystem_stopped` raises -- and the order
            STANDS, because an answer nobody could get is not evidence that a subsystem is
            running. This kills the fail-open `_still_stopped = False`.

        `workorders.resolve_code` is stood in for and its calls collected. It is not one of the
        two side effects `_esc_sandbox` already stops (`file_order` and `health.record`), so
        without the stand-in this probe would reach the real queue -- and reaching the real
        queue to close orders is the one thing a net about closing orders wrongly must not do.
        """
        def probe(d, filed):
            import workorders as WO
            real_resolve, real_stopped = WO.resolve_code, ESC.subsystem_stopped
            closed = []
            WO.resolve_code = lambda *args, **kw: closed.append((args, kw))
            try:
                def denied_stop(name):
                    del closed[:]
                    _with_refused_writes(
                        d, lambda: ESC.stop_subsystem(name, "a reason", who="drill-probe"))

                # 1 -- nothing in the ledger: the order the escalation filed is false.
                denied_stop("sub-never-landed")
                if len(closed) != 1:
                    return False
                args, kw = closed[0]
                if args[0] != "SUBSYSTEM_STOPPED" or kw.get("where") != "sub-never-landed":
                    return False

                # 2 -- already stopped by a call that DID land: the order is true, leave it.
                with open(ESC.STOPPED, "w", encoding="utf-8") as f:
                    json.dump({"sub-already-stopped": {"at": time.time(),
                                                       "reason": "an earlier stop that landed",
                                                       "by": "someone"}}, f)
                denied_stop("sub-already-stopped")
                if closed:
                    return False

                # 3 -- the ledger cannot be asked: leave the order standing.
                def unaskable(_name):
                    raise OSError("the stop ledger cannot be read at all")
                ESC.subsystem_stopped = unaskable
                denied_stop("sub-unknowable")
                return not closed
            finally:
                WO.resolve_code, ESC.subsystem_stopped = real_resolve, real_stopped
        return _esc_probe(probe)
    net(a, "an unrecordable stop closes its work order only when the ledger says NOT stopped",
        a_stop_that_was_never_recorded_closes_only_a_FALSE_order,
        "this rung's whole worth is that a real stop can be FOUND in the queue, and it cannot "
        "be found among false copies of itself -- nor if a true one is quietly closed")

    def a_refused_write_leaves_no_litter_beside_the_ledger():
        def probe(d, filed):
            ESC.stop_subsystem("probe-sub", "a reason", who="p")
            # A digest taken from a state the file is no longer in: the compare-and-swap must
            # refuse, and refuse without leaving its temp copy behind.
            ok, why = ESC._write_stopped({"x": {}}, "a digest this file never had")
            litter = [n for n in os.listdir(d) if n.endswith(".tmp")]
            return ok is False and not litter
        return _esc_probe(probe)
    net(a, "a compare-and-swap that refuses leaves no temp file beside the ledger",
        a_refused_write_leaves_no_litter_beside_the_ledger,
        "`if not ok` losing its `not` unlinks on SUCCESS and litters on refusal, so the "
        "state directory fills with half-written maps of what must not run")

    def the_stop_ledger_keeps_the_characters_it_was_given():
        def probe(d, filed):
            ESC.stop_subsystem("Skånska-jobb", "stängd", who="p")
            with open(ESC.STOPPED, encoding="utf-8") as f:
                raw = f.read()
            held, _ = ESC.subsystem_stopped("Skånska-jobb")
            return held is True and "Skånska-jobb" in raw and "\\u" not in raw
        return _esc_probe(probe)
    net(a, "a subsystem with a non-ASCII name is stopped under the name it was given",
        the_stop_ledger_keeps_the_characters_it_was_given,
        "`_read_stopped` opens this file as utf-8, so the two ends agree by construction -- "
        "flipping `ensure_ascii` breaks the agreement the comment claims is structural")

    # ------------------------------------------------------------------ who may lift a halt
    #
    # `_by_a_person_at_the_cli` asks three questions, and a single flipped comparison in any of
    # them admits every caller. The first net proves the guard refuses; these prove each of the
    # three questions is load-bearing on its own -- a guard whose parts are individually inert
    # is a guard that passes review and stops nothing.

    def _call_clear_from(filename, funcname):
        """Call `ESC.clear` from a function whose code object claims that file and name.

        The frame `_by_a_person_at_the_cli` inspects is its caller's caller, so forging the
        frame is the only honest way to ask whether each identity test carries weight. The
        `__main__` module is pointed at escalation.py for the duration so the FIRST test passes
        and the other two are the ones actually being asked.
        """
        ns = {"ESC": ESC}
        src = "def %s():\n    return ESC.clear('a ruling long enough to pass')\n" % funcname
        exec(compile(src, filename, "exec"), ns)
        main_mod = sys.modules.get("__main__")
        had = hasattr(main_mod, "__file__")
        was = getattr(main_mod, "__file__", None)
        main_mod.__file__ = ESC.__file__
        try:
            return _refuses(ns[funcname], PermissionError)
        finally:
            if had:
                main_mod.__file__ = was
            else:
                del main_mod.__file__

    net(a, "a caller inside escalation.py that is not main() may still not lift a halt",
        lambda: _esc_probe(lambda d, f: _call_clear_from(ESC.__file__, "not_main")),
        "the caller-NAME test is one flipped `==` from admitting any function in this file, "
        "so a helper added later would inherit the owner's authority without anyone deciding "
        "that it should")
    net(a, "a caller named main() in another file may not lift a halt either",
        lambda: _esc_probe(lambda d, f: _call_clear_from(
            os.path.join(os.path.dirname(ESC.__file__), "not_escalation.py"), "main")),
        "the caller-FILE test is the other half: a module that reaches in and calls a "
        "borrowed `main()` must not be able to lift the library's halt")

    # ------------------------------------------------------------------ the lift itself
    #
    # Everything past the person check was unreachable from any test, which is why every line
    # of it survived mutation. The authorisation is asserted above and stubbed here, on
    # purpose: whether a program may lift a halt and whether a lift does the right thing are
    # two questions, and testing the second must not require answering the first wrongly.

    def _as_a_person(fn):
        real = ESC._by_a_person_at_the_cli
        ESC._by_a_person_at_the_cli = lambda: True
        try:
            return fn()
        finally:
            ESC._by_a_person_at_the_cli = real

    def lifting_an_unhalted_library_changes_nothing():
        def probe(d, filed):
            return _as_a_person(lambda: ESC.clear("a ruling long enough to pass")) is False
        return _esc_probe(probe)
    net(a, "lifting a halt that is not standing reports that nothing was lifted",
        lifting_an_unhalted_library_changes_nothing,
        "`if not halted` losing its `not` refuses every REAL lift and accepts every empty "
        "one, so the halt becomes permanent and the CLI says it cleared")

    def a_lift_records_the_ruling_beside_the_original_fault():
        def probe(d, filed):
            ESC.escalate(ESC.OWNER, "ORIGINAL", "the fault that stopped the library",
                         source="a-source")
            ruling = "read the evidence and decided it was a false alarm"
            did = _as_a_person(lambda: ESC.clear(ruling, by="drill-probe"))
            halted, rec = ESC.status()
            return (did is True and halted is False
                    and rec.get("cleared") is True
                    and rec.get("ruling") == ruling
                    and rec.get("cleared_by") == "drill-probe"
                    and rec.get("code") == "ORIGINAL"
                    and rec.get("source") == "a-source")
        return _esc_probe(probe)
    net(a, "a lift keeps the ruling WITH the fault it was given for",
        a_lift_records_the_ruling_beside_the_original_fault,
        "the halt exists to buy a decision; `dict(rec or {})` flipped to `and` throws the "
        "original fault away and leaves a ruling about nothing, and `'cleared': True` "
        "flipped to False leaves the library halted while reporting that it is not")

    def a_fault_landing_mid_lift_is_not_swallowed_by_the_lift():
        """The attack order 0f815b38363f describes, driven end to end.

        `clear()` was an unlocked read-modify-write on the one file that must never lose a
        fault: read the record, merge the ruling, write the whole thing back. A fault escalating
        to OWNER in that gap is appended to `also` by `_land_halt` and then OVERWRITTEN by the
        lift's payload, which was built from the record as it stood before the append. The write
        succeeds, so nothing ever reported it -- and unlike the raise-side race this one takes
        the halt DOWN as it goes, resuming the library on a ruling written about facts that are
        no longer what the file says.

        The attack injects exactly that: a competing OWNER fault arrives between the person's
        read and their write. The net holds when the lift is REFUSED, the halt still stands, and
        the fault that arrived is still in the record. It is deliberately not "retry until it
        lands" -- a lift is a person's ruling about specific facts, and re-merging it onto a
        record that has grown a fault they never read would sign their name to a decision they
        did not make.
        """
        def probe(d, filed):
            ESC.escalate(ESC.OWNER, "ORIGINAL", "the fault that stopped the library")
            real_status, seen = ESC.status, {"n": 0}

            def racing_status():
                out = real_status()
                seen["n"] += 1
                if seen["n"] == 1:          # the gap between the person's read and their write
                    ESC.escalate(ESC.OWNER, "ARRIVED_MID_LIFT",
                                 "a fault nobody has ruled on yet")
                return out

            ESC.status = racing_status
            try:
                did = _quietly(
                    lambda: _as_a_person(lambda: ESC.clear("a ruling long enough to pass")))
            finally:
                ESC.status = real_status
            halted, rec = ESC.status()
            kept = [x.get("code") for x in (rec.get("also") or []) if isinstance(x, dict)]
            with open(ESC.LOG, encoding="utf-8") as f:
                rows = [json.loads(line) for line in f if line.strip()]
            return (did is False and halted is True
                    and rec.get("cleared") is False
                    and "ARRIVED_MID_LIFT" in kept
                    and not [r for r in rows if r.get("code") == "HALT_CLEARED"])
        return _esc_probe(probe)
    net(a, "a fault that lands mid-lift refuses the lift instead of being overwritten by it",
        a_fault_landing_mid_lift_is_not_swallowed_by_the_lift,
        "an unlocked read-modify-write on state/HALT.json drops a concurrent OWNER fault with "
        "a SUCCESSFUL write and lifts the halt anyway, so the library resumes on a ruling "
        "about facts the person never saw")

    def a_lift_whose_write_was_refused_is_reported_as_not_lifted():
        def probe(d, filed):
            ESC.escalate(ESC.OWNER, "ORIGINAL", "the fault that stopped the library")
            did = _with_refused_writes(
                d, lambda: _as_a_person(lambda: ESC.clear("a ruling long enough to pass")))
            halted, _ = ESC.status()
            return did is False and halted is True
        return _esc_probe(probe)
    net(a, "a lift whose write was refused is reported as not lifted, and the halt stands",
        a_lift_whose_write_was_refused_is_reported_as_not_lifted,
        "the mirror of `_raise_halt`'s discarded verdict: a person walks away believing the "
        "library is running while every job goes on refusing")

    def a_lift_that_did_not_land_writes_no_ledger_entry():
        def probe(d, filed):
            ESC.escalate(ESC.OWNER, "ORIGINAL", "the fault that stopped the library")
            _with_refused_writes(
                d, lambda: _as_a_person(lambda: ESC.clear("a ruling long enough to pass")))
            with open(ESC.LOG, encoding="utf-8") as f:
                rows = [json.loads(line) for line in f if line.strip()]
            return not [r for r in rows if r.get("code") == "HALT_CLEARED"]
        return _esc_probe(probe)
    net(a, "no HALT_CLEARED line is written for a lift that did not happen",
        a_lift_that_did_not_land_writes_no_ledger_entry,
        "a ledger entry for a lift that did not happen is worse than no entry, because it "
        "is what the next reader trusts when the file and the log disagree")

    def the_readback_asks_what_the_file_says_not_what_shape_it_is():
        """`_halt_file_cleared` is the readback that makes a lift's verdict EVIDENCE.

        THE MUTATION THIS REFUSES (order be7eed229509, inside `_halt_file_cleared` -- cited by
        symbol, not by line, per order 0c7592915a48). `isinstance(cur,
        dict) and bool(cur.get("cleared", False))` -> `or`. The file exists and parses -- it
        always does, that is what a standing halt looks like -- so the first operand is True and
        the mutant answers True without ever reading the field. A STANDING HALT REPORTS AS
        LIFTED. `clear()` then writes its HALT_CLEARED ledger line and tells the person the
        library is running while every job goes on refusing, which is the precise disagreement
        between file and log that the net above exists to keep out of the ledger.

        It survived because the only caller is inside `clear()`, and `clear()` refuses a
        programmatic caller by design -- correctly, and that refusal is not weakened here. The
        helper is called DIRECTLY instead, which lifts nothing and asks nobody's permission.

        BOTH ANSWERS, since a readback that always says False refuses every real lift and would
        pass a one-directional test -- that is the same shape as `lifting_an_unhalted_library`'s
        lost `not`, arriving one function down.
        """
        def probe(d, filed):
            def on_disk(cleared):
                with open(ESC.HALT_FILE, "w", encoding="utf-8") as f:
                    json.dump({"code": "TEST", "cleared": cleared}, f)
            on_disk(False)
            if ESC._halt_file_cleared() is not False:
                return False               # a standing halt read as lifted
            on_disk(True)
            return ESC._halt_file_cleared() is True
        return _esc_probe(probe)
    net(a, "the halt readback answers the CLEARED FIELD, not the file's existence",
        the_readback_asks_what_the_file_says_not_what_shape_it_is,
        "the one check standing between a refused lift and a HALT_CLEARED line in the ledger")

    def a_refused_lift_leaves_no_temp_file_behind():
        """A compare-and-swap that REFUSED must take its scratch copy with it.

        THE MUTATION THIS REFUSES (order 5be3e1774747, inside `_land_clear`'s own refusal branch
        -- cited by symbol, not by line, per order 0c7592915a48). `_land_clear` writes
        the lifted record to a temp file and hands it to `replace_if_unchanged`; on a refusal --
        which is the ordinary outcome when a fault landed under the writer, and the reason the
        compare-and-swap is there at all -- `if not landed: _unlink(tmp)` removes it. Drop the
        `not` and every refused attempt leaks a `HALT.json.<pid>.<tid>.clear.tmp` beside the
        real halt file, and `clear()` makes STOP_CAS_ATTEMPTS of them per lift. That is litter
        in `state/`, which is on `local_agent.DENYLIST_PREFIXES` and is the directory a person
        reads when they are deciding whether the library is halted -- and each leaked file is a
        complete halt record saying `cleared: true`.

        Forced by handing an `expected` digest that cannot match what is on disk, so
        `replace_if_unchanged` must refuse the rename. The whole sandbox directory is listed
        before and after: the assertion is that NOTHING appeared, which does not depend on the
        temp file's name and so cannot be defeated by renaming it.
        """
        def probe(d, filed):
            with open(ESC.HALT_FILE, "w", encoding="utf-8") as f:
                json.dump({"code": "TEST", "cleared": False}, f)
            before = sorted(os.listdir(d))
            landed, why = ESC._land_clear({"code": "TEST", "cleared": True},
                                          "not-the-digest-on-disk")
            return (landed is False and "refusing to land a stale copy" in (why or "")
                    and sorted(os.listdir(d)) == before)
        return _esc_probe(probe)
    net(a, "a refused lift removes its own scratch copy", a_refused_lift_leaves_no_temp_file_behind,
        "each leak is a complete halt record reading cleared:true, in the directory a person "
        "reads to find out whether the library is halted")

    def a_writer_who_says_it_landed_is_not_taken_at_its_word():
        """AND THE READBACK IS ASKED, not merely available (order 5b051a906ecf, `clear`'s own
        landing check -- cited by symbol, not by line, per order 0c7592915a48).

        `if landed and _halt_file_cleared():` -> `or`. The net two above proves the readback
        answers the file correctly; this proves `clear()` still CONSULTS it. They are different
        claims and each survives the other's mutation: a perfect readback nothing asks is a
        perfect readback nothing asks.

        The gap the `and` covers is stated in `clear()`'s own comment: `replace_if_unchanged`
        re-reads the digest immediately before its rename, so a competing writer can still land
        in the gap between that read and the rename, and `landed` is then the WRITER'S OWN claim
        about a file it no longer owns. That is the same discarded-verdict shape `_raise_halt`
        was repaired for. With `or`, the writer's word is enough: HALT_CLEARED goes into the
        ledger and `clear()` returns True over a `state/HALT.json` that still says `cleared:
        false`, so the person walks away and every job goes on refusing.

        DRIVEN BY A LANDING THAT DID NOT LAND. `_land_clear` is stood in for -- it reports
        `(True, "")` and writes nothing -- which is exactly the world the readback exists to
        catch and is not otherwise reachable, since a real `replace_if_unchanged` that returns
        True has by then genuinely written the file. The halt is real, the person check is
        stubbed the way the rest of this section stubs it, and the assertion is on both the
        verdict and the ledger: `clear()` must report False and no HALT_CLEARED line may exist.
        """
        def probe(d, filed):
            ESC.escalate(ESC.OWNER, "ORIGINAL", "the fault that stopped the library")
            real_land = ESC._land_clear
            ESC._land_clear = lambda rec, expected: (True, "")   # claims to have landed
            try:
                did = _as_a_person(lambda: ESC.clear("a ruling long enough to pass"))
            finally:
                ESC._land_clear = real_land
            halted, rec = ESC.status()
            with open(ESC.LOG, encoding="utf-8") as f:
                rows = [json.loads(line) for line in f if line.strip()]
            return (did is False and halted is True and rec.get("cleared") is not True
                    and not [r for r in rows if r.get("code") == "HALT_CLEARED"])
        return _esc_probe(probe)
    net(a, "a lift is not believed on the writer's word; the file is read back",
        a_writer_who_says_it_landed_is_not_taken_at_its_word,
        "`replace_if_unchanged` re-reads the digest before its own rename, so a competing "
        "writer still fits in the gap and `landed` is a claim about a file this writer lost")

    # ------------------------------------------------------------------ the CLI
    #
    # What a person actually reads, and the return codes a script actually branches on. The
    # `--status` display could not be exercised at all without a standing halt, so none of it
    # was: every line of the HALTED report survived mutation.

    def _cli(argv):
        """Run `escalation.main()` under a forged argv. -> (rc, stdout)."""
        import contextlib as _c
        import io as _io
        buf = _io.StringIO()
        was = sys.argv
        sys.argv = ["escalation.py"] + list(argv)
        try:
            with _c.redirect_stdout(buf):
                rc = ESC.main()
        finally:
            sys.argv = was
        return rc, buf.getvalue()

    def the_status_report_names_the_fault():
        def probe(d, filed):
            ESC.escalate(ESC.OWNER, "PROBE_CODE", "the invariant that broke",
                         source="a-source", who="drill-probe")
            rc, out = _cli(["--status"])
            return (rc == 1 and "HALTED" in out and "PROBE_CODE" in out
                    and "the invariant that broke" in out and "a-source" in out
                    and "drill-probe" in out)
        return _esc_probe(probe)
    net(a, "the status report names the code, the fault, the source and who raised it",
        the_status_report_names_the_fault,
        "`(rec or {}).get(k)` flipped to `and` prints None for every field, so the one "
        "screen a person reads while the library is stopped says nothing at all")

    def the_status_report_counts_the_corroborating_faults():
        def probe(d, filed):
            ESC.escalate(ESC.OWNER, "FIRST", "the first fault")
            ESC.escalate(ESC.OWNER, "SECOND", "a later symptom")
            rc, out = _cli(["--status"])
            return "+1 further fault" in out
        return _esc_probe(probe)
    net(a, "the status report says how many further faults arrived while halted",
        the_status_report_counts_the_corroborating_faults,
        "`(rec or {}).get('also')` flipped to `and` always reads an empty mapping, so a "
        "halt with a dozen corroborating faults reports none of them")

    def a_clear_library_reports_itself_running():
        def probe(d, filed):
            rc, out = _cli(["--status"])
            return rc == 0 and "clear" in out
        return _esc_probe(probe)
    net(a, "a library with no halt reports itself running, with a zero return code",
        a_clear_library_reports_itself_running,
        "every job in this project branches on this rc; `if not halted` losing its `not` "
        "inverts the answer for all of them")

    def raising_a_halt_by_hand_reports_the_landing():
        def probe(d, filed):
            rc, out = _cli(["--raise-halt", "BY_HAND:a person stopped the library"])
            halted, rec = ESC.status()
            return (rc == 0 and "halted." in out and halted is True
                    and rec.get("code") == "BY_HAND"
                    and rec.get("what") == "a person stopped the library")
        return _esc_probe(probe)
    net(a, "a halt raised by hand carries the code and the words it was given",
        raising_a_halt_by_hand_reports_the_landing,
        "`what or 'raised by hand'` flipped to `and` discards what the person typed and "
        "records the placeholder for every deliberate halt")

    def a_hand_raised_halt_that_did_not_land_returns_nonzero():
        def probe(d, filed):
            rc, out = _cli([])          # warm the parser path with no halt standing
            rc, out = _with_refused_writes(
                d, lambda: _cli(["--raise-halt", "BY_HAND:stopping the library"]))
            return rc == 1 and "NOT RAISED" in out
        return _esc_probe(probe)
    net(a, "a hand-raised halt that never landed says so, with a non-zero return code",
        a_hand_raised_halt_that_did_not_land_returns_nonzero,
        "order a1addbdff907: a person who deliberately halted the library was told on stdout "
        "that they had, with a success rc for any script watching, whether or not the file "
        "ever appeared")

    def the_cli_identity_admits_the_one_caller_it_is_supposed_to():
        """The guard's POSITIVE direction, which no other net here asks for.

        Every check above proves `_by_a_person_at_the_cli` REFUSES. A guard that refuses
        everything passes all of them and breaks the only way a halt can ever be lifted --
        which is not a safe failure, it is a library that can be stopped and never started.
        `python src/escalation.py --clear` is the sanctioned path and it has to keep working.
        """
        def probe(d, filed):
            ns = {"ESC": ESC}
            src = "def main():\n    return ESC.clear('a ruling long enough to pass')\n"
            exec(compile(src, ESC.__file__, "exec"), ns)
            main_mod = sys.modules.get("__main__")
            had = hasattr(main_mod, "__file__")
            was = getattr(main_mod, "__file__", None)
            main_mod.__file__ = ESC.__file__
            try:
                return ns["main"]() is False      # admitted, and nothing was standing to lift
            except PermissionError:
                return False                      # the sanctioned path was refused. Breach.
            finally:
                if had:
                    main_mod.__file__ = was
                else:
                    del main_mod.__file__
        return _esc_probe(probe)
    net(a, "the sanctioned CLI lift is ADMITTED, so the halt is not one-way",
        the_cli_identity_admits_the_one_caller_it_is_supposed_to,
        "the program-identity test is one flipped operator from refusing its own CLI, and a "
        "halt nobody can lift stops the library permanently over a fault that was ruled on")

    def a_refused_halt_write_is_loud_on_stderr():
        """The one failure in this module allowed to be loud, and the only reader some jobs have.

        Everything here runs under CREATE_NO_WINDOW, so stderr is frequently the only channel a
        person sees at the moment the halt does not land. The `silence.note` counter and the
        janitor line are both asserted elsewhere; this asserts the sentence, and asserts it is
        NOT printed when the write did land -- a warning that fires on the good path is a
        warning people learn to scroll past.
        """
        def probe(d, filed):
            import contextlib as _c
            import io as _io
            noisy, quiet = _io.StringIO(), _io.StringIO()
            with _c.redirect_stderr(noisy):
                _with_refused_writes(d, lambda: ESC.escalate(ESC.OWNER, "PROBE", "probe what"))
            with _c.redirect_stderr(quiet):
                ESC.escalate(ESC.OWNER, "PROBE2", "probe what")
            return ("CANNOT WRITE HALT FILE" in noisy.getvalue()
                    and "CANNOT WRITE HALT FILE" not in quiet.getvalue())
        return _esc_probe(probe)
    net(a, "a halt whose rename was refused says so on stderr, and only then",
        a_refused_halt_write_is_loud_on_stderr,
        "`if not landed` losing its `not` prints the alarm on every SUCCESSFUL halt and stays "
        "silent on the one that did not land, which is the failure inverted rather than caught")

    def a_lift_keeps_the_characters_of_the_ruling():
        def probe(d, filed):
            ESC.escalate(ESC.OWNER, "ORIGINAL", "the fault that stopped the library")
            ruling = "läste bevisen och beslutade att det var falsklarm"
            _as_a_person(lambda: ESC.clear(ruling, by="drill-probe"))
            with open(ESC.HALT_FILE, encoding="utf-8") as f:
                raw = f.read()
            _halted, rec = ESC.status()
            return ruling in raw and "\\u" not in raw and rec.get("ruling") == ruling
        return _esc_probe(probe)
    net(a, "the ruling is kept in the characters it was written in",
        a_lift_keeps_the_characters_of_the_ruling,
        "the ruling is the whole reason the halt was worth having; storing it as `\\uXXXX` "
        "makes the record of the decision less readable than the fault it settled")


def drill_assay_behaviour():
    """The scoring engine, DRIVEN at the arms the battery could not see. Orders MUTANT_SURVIVED_ASSAY_*.

    The mutation pass reported ELEVEN survivors in `assay.py` -- eleven single-token corruptions
    that `verify_math.py` and every existing drill area passed straight over. They cluster, and
    the cluster is legible: `verify_math` checks the ARITHMETIC (does the composite come out
    where the charter says), and `drill_assay`/`drill_assay_engine` check the HAPPY PATH and the
    published invariants. What neither reaches is the REFUSALS and the SENTINEL bookkeeping --
    the Layer-1 weight validation, the nil/unscored partition, the floor half of the ladder
    clamp, and the reason a faculty prints no value. Those are the arms that only run when a
    caller gets something wrong, which is exactly when they have to be right.

    Every net below drives the real public function and asserts on the real returned dict.
    """
    a = "THE ASSAY, DRIVEN — the refusals and the sentinels, not the arithmetic"

    # ------------------------------------------------------------------ Layer 1: the weight table
    #
    # `weights=` is a PUBLIC per-call override. custodes.py builds one per Custos. Everything
    # downstream -- the composite, the denominator, the error bar -- trusts that this checked it.

    net(a, "an empty weight table is refused, not read as 'use the defaults'",
        lambda: _refuses(lambda: ASSAY._check_weights({}), ASSAY.AssayIntegrityError),
        "`not isinstance(weights, dict) or not weights` flipped to `and` admits `{}`, and an "
        "empty override is not the defaults -- it is a universe with no Measures in it")
    net(a, "a weight table that is not a table is refused as a weight table",
        lambda: _refuses(lambda: ASSAY._check_weights([1, 2]), ASSAY.AssayIntegrityError),
        "with the same flip a truthy non-dict walks past the guard and dies on `.items()` "
        "one frame later, so the caller gets AttributeError where the contract promises "
        "AssayIntegrityError")
    net(a, "a boolean is not a weight",
        lambda: _refuses(lambda: ASSAY._check_weights({"ruin": True}),
                         ASSAY.AssayIntegrityError),
        "`isinstance(v, bool) or not isinstance(v, (int, float))` flipped to `and` admits "
        "True/False -- which ARE ints in Python, so they would score silently as 1 and 0 "
        "rather than being named as the mistake they are")
    net(a, "a negative weight is still refused, and a zero weight is still allowed",
        lambda: (_refuses(lambda: ASSAY._check_weights({"ruin": -1.0}),
                          ASSAY.AssayIntegrityError)
                 and ASSAY._check_weights({"ruin": 0.0, "celerity": 1.0}) is None),
        "a negative weight asserts that scoring well LOWERS a being's standing, which is a "
        "different method; 'this axis does not count for this reading' is a coherent thing "
        "for a caller to say and must survive the guard that stops the other one")

    # ------------------------------------------------------------------ the nil / unscored partition
    #
    # Three states an axis can be in and they carry three different dispersions. Swapping any
    # two changes every published error bar in the library and changes no arithmetic anywhere
    # that `verify_math` looks.

    def a_nil_axis_is_narrower_than_an_unscored_one():
        """NIL is knowledge; UNSCORED is ignorance. The bars must say so.

        ASSERTED PER AXIS, not on the published total, and the difference matters. Comparing
        one assay's interval against another's caught the partition mutation and NOT the
        dispersion mutation: swapping which branch gets the nil factor
        moves BOTH assays in the same direction, so the `<` between them still held while
        every nil axis in the library was silently carrying the dispersion of ignorance and
        every ignorant one the nil factor. `reach` and `volition` are given identical weights
        by WEIGHTS, so their variance terms in ONE assay are directly comparable and the
        comparison is about the dispersion alone.

        THE TWO MUTANTS USED TO BE CITED AS `assay.py` line 947 and line 802 (order
        5c5dd914bf82). Both had drifted -- 947 now lands on `_interval`'s loop head and 802 on
        the tail of the correlated-measures warning string -- and neither could be re-pointed at
        a symbol with any confidence, because the numbers describe a tree several edits ago. They
        are gone rather than guessed at: order 0c7592915a48's rule is to cite by symbol, and a
        line number nobody can resolve is worse than no citation, since it reads as evidence.
        """
        scored = {"ruin": 7.0, "celerity": 6.0}
        plain = ASSAY.assay("M3", dict(scored), worksheet="w")
        with_nil = ASSAY.assay("M3", dict(scored, reach=ASSAY.NONE), worksheet="w")
        var = with_nil["variance_by_axis"]
        return (with_nil["interval"] < plain["interval"]
                and with_nil["axes_nil"] == ["reach"]
                and "reach" not in with_nil["axes_unscored"]
                and "volition" in with_nil["axes_unscored"]
                and ASSAY.WEIGHTS["reach"] == ASSAY.WEIGHTS["volition"]
                and var["reach"] < var["volition"])
    net(a, "an axis known to be nil tightens the bar; an unscored one does not",
        a_nil_axis_is_narrower_than_an_unscored_one,
        "`elif k in nil` flipped to `not in` gives every nil axis the dispersion of ignorance "
        "and every ignorant axis the nil factor -- every error bar in the library moves and "
        "no arithmetic check notices")

    def the_unscored_list_is_the_axes_with_no_score():
        r = ASSAY.assay("M3", {"ruin": 7.0, "celerity": 6.0}, worksheet="w")
        unscored, scored = set(r["axes_unscored"]), set(r["scores"])
        return (unscored == set(ASSAY.WEIGHTS) - scored and not (unscored & scored)
                and "ruin" not in unscored and "reach" in unscored)
    net(a, "the unscored axes are the ones that were not scored",
        the_unscored_list_is_the_axes_with_no_score,
        "`k not in used` flipped to `in` publishes the SCORED axes as the unscored ones, so "
        "the coverage figure and the ignorance term both invert while the composite stays put")

    def an_inapplicable_axis_is_not_charged_as_ignorance():
        """INAPPLICABLE leaves the denominator; UNESTIMABLE stays in it. That is the whole
        distinction, and it is the one a reader of a published bar is trusting."""
        base = {"ruin": 7.0, "celerity": 6.0}
        na = ASSAY.assay("M3", dict(base, suasion=ASSAY.INAPPLICABLE), worksheet="w")
        un = ASSAY.assay("M3", dict(base, suasion=ASSAY.UNESTIMABLE), worksheet="w")
        return (na["axes_unestimable"] == [] and un["axes_unestimable"] == ["suasion"]
                and "suasion" not in na["axes_unscored"]
                and "suasion" not in un["axes_unscored"]
                and "suasion" not in na["variance_by_axis"]
                and "suasion" in un["variance_by_axis"])
    net(a, "an inapplicable axis leaves the denominator and an unestimable one does not",
        an_inapplicable_axis_is_not_charged_as_ignorance,
        "charging ignorance for an axis that cannot apply punishes an assessor for knowing "
        "that a landslide has no Suasion")

    # ------------------------------------------------------------------ the ladder clamp, both ends
    #
    # A clamp on one end of a scale is not a clamp, it is a half-checked instrument -- the
    # file's own words. The ceiling end is exercised; the FLOOR end never was, and all three of
    # its lines survived mutation.

    def the_floor_end_of_the_ladder_says_which_case_it_is():
        """The floor arm is DEFENCE IN DEPTH, and reaching it means going round Layer 1.

        `_check_weights` now refuses the negative weight that produced the original
        `MOTH M3.-90`, so with the public API intact the composite cannot go below zero and
        this arm is unreachable -- which is exactly why all three of its lines survived
        mutation. The file's own comment says the arm is written anyway, because the guarantee
        worth having is about the NOTATION and not about any one route into it. That is a
        testable claim, so it is tested: Layer 1 is stood down for the length of the call and
        the historical route (order 8b74d2b4f569, quoted verbatim in `assay()`) is driven
        through the arm it was filed for. Layer 1 is restored in `finally`, and the net above
        proves it still refuses.
        """
        real = ASSAY._check_weights
        ASSAY._check_weights = lambda w: None
        try:
            bad = {"ruin": 1.0, "celerity": -0.5}
            below_band = ASSAY.assay("M3", {"ruin": 0.0, "celerity": 9.0},
                                     worksheet="w", weights=bad)
            at_floor = ASSAY.assay("M0", {"ruin": 0.0, "celerity": 9.0},
                                   worksheet="w", weights=bad)
        finally:
            ASSAY._check_weights = real
        return (at_floor["decimal"] == 0.0
                and at_floor["at_ladder_floor"] is True
                and at_floor["demotion_due"] is False
                and below_band["decimal"] == 0.0
                and below_band["at_ladder_floor"] is False
                and below_band["demotion_due"] is True
                and "-" not in below_band["moth_number"].split("±")[0])
    net(a, "the floor end names which case it is: saturation at M0, demotion above it",
        the_floor_end_of_the_ladder_says_which_case_it_is,
        "`anchor == LADDER[0]` flipped to `!=` swaps the two answers, so a being pinned at "
        "the bottom of the scale is reported as needing demotion below it and a genuinely "
        "over-anchored one is reported as saturated -- and both flags exist precisely so a "
        "reviewer can tell those apart")

    def the_ceiling_end_still_says_which_case_it_is():
        """The mirror, kept beside it: a net that only checks the newly-broken end is how the
        other end becomes the next survivor."""
        top = {k: 10.0 for k in ASSAY.WEIGHTS}
        at_ceiling = ASSAY.assay("M10", top, worksheet="w")
        above_band = ASSAY.assay("M5", top, worksheet="w")
        return (at_ceiling["at_ladder_ceiling"] is True and at_ceiling["promotion_due"] is False
                and above_band["at_ladder_ceiling"] is False and above_band["promotion_due"] is True
                and at_ceiling["decimal"] == 0.99)
    net(a, "the ceiling end names which case it is too",
        the_ceiling_end_still_says_which_case_it_is,
        "the printed decimal is inside [0, 1) or the dict says which end it hit and why")

    # ------------------------------------------------------------------ the instrument's silences
    #
    # "Transcendence is not evidence" (Definition 5). A faculty with nothing behind it prints no
    # value AND no Grade -- and it has to print WHY, or the silence is indistinguishable from a
    # bug in the caller.

    def a_half_read_constitution_says_which_half_was_missing():
        """Constitution is the mean of two axes, so it has a failure mode the others do not:
        either half can be the sentinel, and the reason must survive whichever it is."""
        first = ASSAY.instrument("M6", {"continuity": ASSAY.NONE, "sustain": 5.0},
                                 worksheet="w")
        second = ASSAY.instrument("M6", {"continuity": 5.0, "sustain": ASSAY.UNESTIMABLE},
                                  worksheet="w")
        both = ASSAY.instrument("M6", {"continuity": 5.0, "sustain": 5.0}, worksheet="w")
        return (first["faculties"]["Constitution"] is None
                and first["faculty_status"]["Constitution"] == ASSAY.NONE
                and second["faculties"]["Constitution"] is None
                and second["faculty_status"]["Constitution"] == ASSAY.UNESTIMABLE
                and both["faculties"]["Constitution"] is not None)
    net(a, "a faculty that prints no value says which of its readings was missing",
        a_half_read_constitution_says_which_half_was_missing,
        "`(why_a or why_b)` flipped to `and` returns None whenever the FIRST half is the "
        "sentinel, so the commonest case prints a blank Grade with no reason beside it and "
        "reads as a defect in the instrument rather than as an unattested axis")

    # ------------------------------------------------------------------ the attestation floor
    #
    # Order 13a678071cbf: an unrecognised grade is NAMED, not absorbed. Two layers have to
    # speak, because two layers absorbing the same bad input the same way is one layer and a decoy.

    def a_recognised_grade_uses_its_own_floor_and_an_unknown_one_is_named():
        readings = {"AVAR": 3.0, "QUILL": 3.2, "MOTH": 3.1}
        tight = ASSAY.interval_from_hands(readings, "Instrumented")
        loose = ASSAY.interval_from_hands(readings, "Disputed")
        typo = ASSAY.interval_from_hands(readings, "witnessed")
        proper = ASSAY.interval_from_hands(readings, "Witnessed")
        return (tight["interval"] < loose["interval"]
                and tight["attestation_recognised"] is True
                and tight["attestation_floor"] == ASSAY.ATTESTATION_FLOOR["Instrumented"]
                and typo["attestation_recognised"] is False
                and typo["attestation_floor"] == ASSAY.ATTESTATION_FLOOR_UNRECOGNISED
                and "UNRECOGNISED" in typo["attestation_source"]
                and typo["interval"] != proper["interval"])
    net(a, "a recognised attestation uses its own floor; an unrecognised one is not absorbed",
        a_recognised_grade_uses_its_own_floor_and_an_unknown_one_is_named,
        "`attestation in ATTESTATION_FLOOR` flipped to `not in` gives every RECOGNISED grade "
        "the unrecognised floor and raises KeyError on every typo -- so the five grades the "
        "charter defines stop meaning anything and the bad input crashes instead of speaking")

    # ------------------------------------------------------------------ the calibration report
    #
    # The single worked example the charter fixes by hand. `holds` is the one field anything
    # reads, and it is an AND of two independent agreements.

    def calibration_holds_only_when_BOTH_halves_agree():
        real_i, real_d = ASSAY.CHARTER_KENSHIRO_INTERVAL, ASSAY.CHARTER_KENSHIRO_DECIMAL
        try:
            if not ASSAY.calibration_report()["holds"]:
                return False                      # the real table must agree with itself
            ASSAY.CHARTER_KENSHIRO_DECIMAL = real_d + 0.5
            half = ASSAY.calibration_report()
            return half["holds"] is False and half["interval"] == half["want_interval"]
        finally:
            ASSAY.CHARTER_KENSHIRO_INTERVAL = real_i
            ASSAY.CHARTER_KENSHIRO_DECIMAL = real_d
    net(a, "the calibration holds only when the interval AND the decimal both agree",
        calibration_holds_only_when_BOTH_halves_agree,
        "`and` flipped to `or` reports the charter's worked example as holding when only one "
        "of its two published figures still matches, which is the check certifying itself")


    # ============================== THE TABLES IT LOADS, AND THE FIELDS THE REPORT CARRIES
    #
    # Landed 2026-09-06 from handoff/nets_20260906/assay.py. Nine of the ten attack guards added
    # to `assay.py` the same day -- five import-time ratchets over constant tables that had no
    # net anywhere in the tree, and four additive report fields that make a silently-absorbed bad
    # input speak. The tenth is COVERAGE rather than proof and says so in its own comment:
    # `axis_score`'s `hi <= lo` limb is old code nothing had ever watched refuse, because
    # BAND_EDGES happens to be well-ordered, which is precisely the condition the limb defends
    # against a future edit breaking.

    # -------------------------------------------------------------- the second attestation table
    #
    # Orders 6d132aa1e8aa and 95404f8825f2, filed independently, same finding: `SIGMA_BY_ATTESTATION`
    # is checked at import and `ATTESTATION_FLOOR` -- the quadrature floor `interval_from_hands` adds,
    # and the table `custodes.py` reads as `A.ATTESTATION_FLOOR` for all ten Custodes' evidential
    # parts -- was checked nowhere in the tree.

    def the_attestation_floors_cannot_be_rearranged_mid_table():
        """A floor swap that leaves both endpoints alone must still refuse at import.

        Instrumented and Disputed are untouched here on purpose: that is precisely the edit the two
        existing endpoint probes cannot see, and it publishes a NARROWER bar for the worse-attested
        of the two grades it moves -- the "less knowledge, narrower bar" defect assay.py's own header
        names as the worst direction this library can be wrong in.
        """
        saved = dict(ASSAY.ATTESTATION_FLOOR)
        try:
            ASSAY.ATTESTATION_FLOOR.update({"Transcribed": 0.40, "Reconstructed": 0.20})
            refused = _refuses(ASSAY._check_constants, ASSAY.AssayIntegrityError)
        finally:
            ASSAY.ATTESTATION_FLOOR.clear()
            ASSAY.ATTESTATION_FLOOR.update(saved)
        # And the live table is exactly as it was, so a red net cannot leave a redder library.
        return refused and ASSAY.ATTESTATION_FLOOR == saved

    net(a, "an attestation FLOOR table that is not strictly increasing refuses to load",
        the_attestation_floors_cannot_be_rearranged_mid_table,
        "ATTESTATION_FLOOR had no ordering check anywhere in src/. Swap Transcribed 0.20 and "
        "Reconstructed 0.40 and leave the endpoints alone: import succeeds, drill's two-point probe "
        "still passes, and interval_from_hands plus custodes.ATTESTATION_QUALITY publish a TIGHTER "
        "bar for the worse-attested grade -- less knowledge, narrower bar, on the table with no net")

    def a_renamed_attestation_grade_refuses_rather_than_substituting():
        """The five grades are the charter's, and a table that lost one must not load.

        `interval_from_hands` SUBSTITUTES ATTESTATION_FLOOR_UNRECOGNISED for a grade it cannot find,
        so a renamed grade does not raise anywhere downstream -- it quietly publishes every reading
        of that grade against a floor the charter never assigned it, and says "UNRECOGNISED" about a
        grade the charter does define.
        """
        saved = dict(ASSAY.ATTESTATION_FLOOR)
        try:
            ASSAY.ATTESTATION_FLOOR.pop("Witnessed")
            ASSAY.ATTESTATION_FLOOR["Seen"] = 0.10
            refused = _refuses(ASSAY._check_constants, ASSAY.AssayIntegrityError)
        finally:
            ASSAY.ATTESTATION_FLOOR.clear()
            ASSAY.ATTESTATION_FLOOR.update(saved)
        return refused and ASSAY.ATTESTATION_FLOOR == saved

    net(a, "an ATTESTATION_FLOOR that lost or renamed a charter grade refuses to load",
        a_renamed_attestation_grade_refuses_rather_than_substituting,
        "the substitution path is silent by design, so a dropped grade is not a KeyError -- it is "
        "every reading of that grade published against ATTESTATION_FLOOR_UNRECOGNISED with a "
        "sentence saying the charter does not define a grade the charter does define")

    def the_substituted_floor_is_never_a_reward():
        """A grade nobody recognised must not buy a bar as tight as an instrument reading.

        This is the SIGMA_UNKNOWN check's own shape, asserted on the floor table: the substituted
        value is what an unread grade GETS, and it is not allowed to be better than the best evidence
        on file.
        """
        saved = ASSAY.ATTESTATION_FLOOR_UNRECOGNISED
        try:
            ASSAY.ATTESTATION_FLOOR_UNRECOGNISED = 0.05
            refused = _refuses(ASSAY._check_constants, ASSAY.AssayIntegrityError)
        finally:
            ASSAY.ATTESTATION_FLOOR_UNRECOGNISED = saved
        return refused and ASSAY.ATTESTATION_FLOOR_UNRECOGNISED == saved

    net(a, "a substituted floor tighter than the best recognised grade refuses to load",
        the_substituted_floor_is_never_a_reward,
        "ATTESTATION_FLOOR_UNRECOGNISED at 0.05 makes an INVENTED grade the most confident reading "
        "in the library -- the fastest way to a tight bar becomes typing a grade nobody has heard of")

    # ------------------------------------------------------------- the Instrument's own constants
    #
    # Order 422ccc9f6eb4. Two tables sitting beside BAND_EDGES, both read on the publishing path,
    # neither checked when the BAND_EDGES ratchet was written.

    def a_ladder_rung_with_no_instrument_window_refuses_to_load():
        """`instrument()` refuses such a rung with a message that NAMES it as acceptable.

        Worse, anchors.py:427 indexes INSTRUMENT_WINDOWS[b] for every b in LADDER with no guard, so
        the same divergence arrives as a KeyError raised from inside production code. Both directions
        are attacked, because a table can disagree with the Ladder by having too little or too much.
        """
        saved = dict(ASSAY.INSTRUMENT_WINDOWS)
        try:
            ASSAY.INSTRUMENT_WINDOWS.pop("M7")
            missing_refused = _refuses(ASSAY._check_constants, ASSAY.AssayIntegrityError)
            ASSAY.INSTRUMENT_WINDOWS.clear()
            ASSAY.INSTRUMENT_WINDOWS.update(saved)
            ASSAY.INSTRUMENT_WINDOWS["M11"] = (30, 30)
            stray_refused = _refuses(ASSAY._check_constants, ASSAY.AssayIntegrityError)
        finally:
            ASSAY.INSTRUMENT_WINDOWS.clear()
            ASSAY.INSTRUMENT_WINDOWS.update(saved)
        return missing_refused and stray_refused and ASSAY.INSTRUMENT_WINDOWS == saved

    net(a, "INSTRUMENT_WINDOWS and the Ladder must name the same rungs, both directions",
        a_ladder_rung_with_no_instrument_window_refuses_to_load,
        "a rung on the Ladder with no window is refused by `anchor must be one of {LADDER}` -- a "
        "sentence that names that rung as acceptable -- and is an unguarded KeyError out of "
        "anchors.py:427; a window row off the Ladder is numbers nothing can ever score against")

    def a_faculty_that_reads_a_measure_nobody_defines_refuses_to_load():
        """A misspelt axis in FACULTY_READS is not a refusal downstream, it is a SILENT DROP.

        `instrument()` does `axis_scores.get(axis)`, so an unknown name returns None, the faculty
        prints None, and `faculty_status` records "unattested" -- which ASSERTS the subject was never
        observed exercising that faculty. `_check_scores` cannot see it: it validates the CALLER's
        keys and this is the table's own values. The second attack is the same fault reached from the
        WEIGHTS side, and it covers Constitution, whose two halves are read by name in code rather
        than through FACULTY_READS at all.
        """
        saved_reads = dict(ASSAY.FACULTY_READS)
        saved_w = dict(ASSAY.WEIGHTS)
        try:
            ASSAY.FACULTY_READS["Wisdom"] = "discernement"
            misspelt_refused = _refuses(ASSAY._check_constants, ASSAY.AssayIntegrityError)
            ASSAY.FACULTY_READS.clear()
            ASSAY.FACULTY_READS.update(saved_reads)
            ASSAY.WEIGHTS.pop("sustain")
            constitution_refused = _refuses(ASSAY._check_constants, ASSAY.AssayIntegrityError)
        finally:
            ASSAY.FACULTY_READS.clear()
            ASSAY.FACULTY_READS.update(saved_reads)
            ASSAY.WEIGHTS.clear()
            ASSAY.WEIGHTS.update(saved_w)
        return (misspelt_refused and constitution_refused
                and ASSAY.FACULTY_READS == saved_reads and ASSAY.WEIGHTS == saved_w)

    net(a, "a faculty pointed at a Measure that does not exist refuses to load",
        a_faculty_that_reads_a_measure_nobody_defines_refuses_to_load,
        "one letter in FACULTY_READS prints a published faculty as unattested, which asserts the "
        "subject was never observed exercising it -- a finding manufactured out of a typo, and "
        "invisible to `_check_scores`, which judges the caller's keys and not the table's values")

    # ----------------------------------------------------------- the grade speaks at BOTH layers
    #
    # Order 9a0588111549. `interval_from_hands` names an unrecognised grade; `assay()` -- the layer
    # that produces every printed Magnitude in the library -- absorbed it, doubled the bar, and
    # returned a dict whose `attestation` field said "witnessed" while its interval said Disputed.

    def assay_names_an_attestation_grade_it_could_not_read():
        """A lowercase spelling and an invented grade must both be flagged, not just widened.

        Widening is the safe direction and that is not why the silence was acceptable: the interval
        IS the published claim about how much the library does not know, and a bar that doubled
        because somebody typed a lowercase w is not a statement about evidence. Measured on the
        charter's own worksheet: 'Witnessed' 0.12, 'witnessed' 0.25, 'Excellent' 0.25.
        """
        proper = ASSAY.assay("M3", dict(ASSAY.CHARTER_KENSHIRO), attestation="Witnessed",
                             worksheet="w")
        typo = ASSAY.assay("M3", dict(ASSAY.CHARTER_KENSHIRO), attestation="witnessed",
                           worksheet="w")
        invented = ASSAY.assay("M3", dict(ASSAY.CHARTER_KENSHIRO), attestation="Excellent",
                               worksheet="w")
        return (proper["attestation_recognised"] is True
                and proper["attestation_sigma"] == ASSAY.SIGMA_BY_ATTESTATION["Witnessed"]
                and "UNRECOGNISED" not in proper["attestation_source"]
                and typo["attestation_recognised"] is False
                and invented["attestation_recognised"] is False
                and typo["attestation_sigma"] == ASSAY.SIGMA_MAX
                and "UNRECOGNISED" in typo["attestation_source"]
                and "UNRECOGNISED" in invented["attestation_source"]
                # the grade is still carried verbatim: the flag is ADDITIVE, never a rewrite
                and typo["attestation"] == "witnessed"
                and typo["interval"] > proper["interval"])

    net(a, "assay() says when it could not read the attestation grade it was handed",
        assay_names_an_attestation_grade_it_could_not_read,
        "`SIGMA_BY_ATTESTATION.get(attestation, SIGMA_MAX)` absorbs a lowercase 'witnessed' onto the "
        "Disputed sigma and doubles the published bar, while the stored entry says 'witnessed' -- "
        "the entry and its interval then disagree about the evidence and nothing reconciles them. "
        "`attestation_recognised` flipped to `not in` reverses it: every real grade is flagged unread")

    def the_reported_sigma_is_the_sigma_the_arithmetic_used():
        """One lookup, not two. A reported number that can drift from the computed one is worse
        than no report, because a reader stops checking.

        The `sigma=` override is the case that separates them: `calibration_report` sweeps ~650 of
        them, and a call that overrides the dispersion has NOT thereby validated its grade, so the
        recognition flag must still describe the GRADE while the reported sigma describes the CALL.
        """
        swept = ASSAY.assay("M3", dict(ASSAY.CHARTER_KENSHIRO), attestation="Witnessed",
                            worksheet="w", sigma=2.0)
        clamped = ASSAY.assay("M3", dict(ASSAY.CHARTER_KENSHIRO), attestation="Witnessed",
                              worksheet="w", sigma=99.0)
        return (swept["attestation_sigma"] == 2.0
                and swept["attestation_recognised"] is True
                and "sigma= override" in swept["attestation_source"]
                # the ceiling binds an override exactly as it binds the table
                and clamped["attestation_sigma"] == round(ASSAY.SIGMA_MAX, 4))

    net(a, "the sigma an assay reports is the sigma it computed with, override and ceiling included",
        the_reported_sigma_is_the_sigma_the_arithmetic_used,
        "the lookup was hoisted so the dict reports the same value `_interval` used; a second copy "
        "of it would report the table's sigma while the bar was computed from a swept one, and a "
        "`min(SIGMA_MAX, ...)` dropped from either copy lets a caller buy certainty the table cannot")

    # ----------------------------------------------------------- the Hands are read, not assumed
    #
    # Order 91a30aa88893. `HANDS` had no reader anywhere in src/ while `interval_from_hands`'
    # `readings` argument is keyed by exactly those four names and validated none of them.

    def a_signature_that_is_not_one_of_the_hands_is_named():
        """{"AVARR": 7.41} used to yield a perfectly ordinary interval with nothing saying so.

        This matters more than a typo usually would: per Vol. 0.5 §2 this interval is the divergence
        between the ORDER'S CANONICAL PRIORS, and HANDS is the list of those priors. A signature from
        outside them is a reading whose prior is not on file, so the quantity the field publishes is
        not the quantity it claims. Every KEY is judged, including one whose value is None -- a
        misspelt Hand that filed nothing is still a caller who does not know the Hands' names.
        """
        good = ASSAY.interval_from_hands({"AVAR": 7.41, "QUILL": 7.90})
        typo = ASSAY.interval_from_hands({"AVARR": 7.41, "QUILL": 7.90})
        silent = ASSAY.interval_from_hands({"AVAR": 7.41, "QILL": None})
        return (good["hands_recognised"] is True
                and good["unrecognised_hands"] == []
                and "UNRECOGNISED" not in good["hands_source"]
                and typo["hands_recognised"] is False
                and typo["unrecognised_hands"] == ["AVARR"]
                and "UNRECOGNISED" in typo["hands_source"]
                and silent["unrecognised_hands"] == ["QILL"]
                # ADDITIVE: the interval itself is unchanged by the flag
                and typo["interval"] == good["interval"])

    net(a, "a reading signed by something that is not one of the four Hands is named",
        a_signature_that_is_not_one_of_the_hands_is_named,
        "HANDS was prose that happens to be a dict -- no reader anywhere in src/ -- beside the one "
        "function keyed by its names. `h not in HANDS` flipped to `in` flags all four canonical "
        "Hands and passes every typo, which is the fault inverted rather than removed")

    # ---------------------------------------------------- the guarantee, and the datum beside it
    #
    # Orders e4c8355cc7a0 and 623ac39b4d61, which are one finding. `covers_all_signatures` is True
    # for every possible input because the widening loop terminates exactly when its expression does
    #  so nothing read it, and the mutation that inverts it survived a full battery.

    def the_covering_guarantee_holds_and_says_what_bought_it():
        """Three things at once, because they are one claim about one published number.

        (1) The guarantee itself: whatever the readings, the interval covers every signature. This is
        what the `covers_all_signatures` mutant (`<=` flipped to `>` in the comprehension that
        computes it) breaks -- and that mutant is NOT equivalent, it
        returns False for EVERY non-empty `readings`, so a single assertion kills it.
        (2) The datum: whether the EVIDENCE covered them, or the covering rule bought the coverage.
        (3) That the datum is not a second tautology -- a skewed set really does fail the quadrature
        interval, because `centre` is the mean while the spread is measured from the extremes.
        """
        plain = ASSAY.interval_from_hands({"AVAR": 7.41, "QUILL": 7.90})
        skewed = ASSAY.interval_from_hands({"AVAR": 0.0, "QUILL": 0.0, "MOTH": 30.0})
        return (plain["covers_all_signatures"] is True
                and skewed["covers_all_signatures"] is True
                and plain["covered_before_widening"] is True
                and plain["widening_added"] == 0.0
                and plain["interval"] == plain["quadrature_interval"]
                and skewed["covered_before_widening"] is False
                and skewed["widening_added"] > 0.0
                and skewed["interval"] > skewed["quadrature_interval"]
                # and the widened interval really does cover the outlier the quadrature one missed
                and abs(30.0 - 10.0) <= skewed["interval"])

    net(a, "the interval covers every signature, and says whether the evidence or the rule did it",
        the_covering_guarantee_holds_and_says_what_bought_it,
        "assay.py's interval_from_hands, 'covers_all_signatures' key (cited by symbol per order "
        "0c7592915a48, not by line) -- `<=` flipped to `>` survived a whole mutation pass because NOTHING read this "
        "field; it is not equivalent, it publishes False for every reading on file. And a guarantee "
        "published as if it were a check is the shape CLAUDE.md names -- a check that cannot fail "
        "looks exactly like a check that passed -- so `covered_before_widening` is asserted beside "
        "it, in both directions, or the pair reads as two rubber stamps instead of one and a datum")

    # ---------------------------------------------------------- the limb of a guard nobody drives
    #
    # Order d9c8aab72a2c, remedy (2). NOT a net for a guard added this shift: `axis_score`'s
    # `hi <= lo` refusal has been there all along and is unchanged. It has simply never been WATCHED
    # refuse, because BAND_EDGES happens to be well-ordered, so the mutant that deleted it outright
    # changed nothing anybody looked at. This net drives it directly instead of through the table.
    # It therefore HOLDS against the pre-fix module too, and is staged as coverage, not as proof.

    def axis_score_refuses_a_band_whose_ceiling_is_not_above_its_floor():
        """An inverted or degenerate band pair must return None, not a number.

        Without the refusal, `(log(x) - log(lo)) / (log(hi) - log(lo))` is a ZeroDivisionError when
        hi == lo and a NEGATIVE denominator when hi < lo -- a scoring function that returns a
        confident wrong number rather than declining. Driven by synthesising the edges rather than by
        corrupting BAND_EDGES, because the property under test is what the FUNCTION does with a bad
        pair; `_check_constants` separately ratchets the table so a bad pair cannot arise from it.
        """
        saved = {b: dict(ASSAY.BAND_EDGES[b]) for b in ("M3", "M4")}
        try:
            ASSAY.BAND_EDGES["M4"]["ruin"] = ASSAY.BAND_EDGES["M3"]["ruin"]      # hi == lo
            degenerate = ASSAY.axis_score(1e28, "M3", "ruin")
            ASSAY.BAND_EDGES["M4"]["ruin"] = ASSAY.BAND_EDGES["M3"]["ruin"] / 10.0   # hi < lo
            inverted = ASSAY.axis_score(1e28, "M3", "ruin")
        finally:
            for b, row in saved.items():
                ASSAY.BAND_EDGES[b].clear()
                ASSAY.BAND_EDGES[b].update(row)
        return (degenerate is None and inverted is None
                # half-defined edges refuse too, and the live table is back as it was
                and ASSAY.axis_score(1e28, "M3", "acumen") is None
                and ASSAY.BAND_EDGES["M4"]["ruin"] == saved["M4"]["ruin"])

    net(a, "axis_score refuses a band whose ceiling is not above its floor",
        axis_score_refuses_a_band_whose_ceiling_is_not_above_its_floor,
        "`if not lo or not hi or hi <= lo` with the last limb dropped -- which is exactly what the "
        "surviving mutant `not lo or not hi and hi <= lo` does, since `and` binds tighter -- is a "
        "ZeroDivisionError at hi == lo and a silently INVERTED score at hi < lo. The limb has never "
        "been watched refuse because BAND_EDGES happens to be well-ordered, which is the condition "
        "the guard exists to defend against a future edit breaking")


def drill_threads():
    """The entanglement pass — the one place a citation can be invented.

    STEP4_PLAN.md §8 requires every Step 4 phase to add its own attack before it ships, and names
    the one that matters most: *can a thread be emitted that points at nothing?* A thread that
    resolves to nothing is not a weak thread, it is a broken one (§1), and the whole design rests
    on the claim that dangling is prevented BY CONSTRUCTION rather than caught afterwards.

    The second attack is the §7B ruling, which is a rule about AUTHORSHIP rather than about code:
    the Great Identifications are "where the walls come down entirely" and a claim of that weight
    must have a person's name on it. `threads.py` must be unable to machine-derive one.
    """
    a = "THE ENTANGLEMENT PASS — can a citation be invented?"
    import threads as TH

    KNOWN = {"II.A.3", "II.A.5"}

    def refused(**kw):
        """Did `edge()` refuse, as opposed to failing for some unrelated reason?"""
        try:
            TH.edge(**kw)
            return False
        except TH.ThreadRefused:
            return True
        except Exception:
            return False        # a TypeError is not a refusal; it is a broken probe

    net(a, "a thread cannot be emitted that points at nothing",
        lambda: refused(to="II.Z.99", cls="T1", why="x", frm="II.A.3", known_codes=KNOWN),
        "the plan names this the attack that matters most: dangling is supposed to be "
        "impossible by construction, not caught afterwards by the verifier")
    net(a, "nor at an UNASSIGNED source, which is not an address",
        lambda: refused(to="UNASSIGNED", cls="T1", why="x", frm="II.A.3", known_codes=KNOWN),
        "an unaddressed source has nothing to thread to; emitting one would be a dangling "
        "thread wearing a placeholder's name")
    net(a, "nor at nothing at all",
        lambda: refused(to="", cls="T2", why="x", frm="II.A.3", known_codes=KNOWN),
        "an empty target is the one a truthiness check catches by accident and a membership "
        "check misses; it is still a thread pointing at no address")
    net(a, "and an address that DOES resolve is still admitted",
        lambda: TH.edge(to="II.A.5", cls="T2", why="x", frm="II.A.3",
                        known_codes=KNOWN)["to"] == "II.A.5",
        "a gate that refuses everything is also broken")

    # THE AUTHORSHIP RULING, WHICH NO AMOUNT OF CORRECT CODE CAN SUBSTITUTE FOR.
    net(a, "the Great Identifications cannot be machine-derived",
        lambda: refused(to="II.A.5", cls="T5", why="x", frm="II.A.3", known_codes=KNOWN),
        "STEP4_PLAN.md §7B: T5 is owner-authored ONLY -- never derived, never inferred, never "
        "emitted by threads.py, because it is the strongest cross-verse claim the charter makes")
    net(a, "nor may an unauthorised later phase be reached by a new path",
        lambda: (refused(to="II.A.5", cls="T3", why="x", frm="II.A.3", known_codes=KNOWN)
                 and refused(to="II.A.5", cls="T4", why="x", frm="II.A.3", known_codes=KNOWN)),
        "T3 (the Chronicle join) and T4 (Law citations) are unauthorised by the §7E ruling; "
        "the refusal lives in edge() so a future caller cannot route around it")

    def every_addressed_entry_gets_a_home():
        """§6's "quiet one": a Threads section present but EMPTY.

        Indistinguishable from "pending" to a reader and from "done" to a checker. An entry with
        zero threads after T1 is impossible by construction -- T1 is its own home volume -- so
        zero means the pass did not run for that entry. Driven against a fixture rather than the
        live corpus, so the net answers the same on a fresh clone.
        """
        recs = [{"source": "Alpha", "entries": [{"topic": "Persons"}, {"topic": "Places"}]},
                {"source": "Beta", "entries": [{"topic": "Persons"}]}]
        keep = TH.ADDR.spine_code_for
        try:
            TH.ADDR.spine_code_for = lambda n: {"Alpha": "II.A.1", "Beta": "II.A.2"}.get(n, "UNASSIGNED")
            g = TH.build(recs)
            for src, rec in g["sources"].items():
                for cat in rec["by_category"]:
                    if not TH.threads_for(g, src, {"topic": cat}):
                        return False
            # and the home thread really is the source's own volume, not a neighbour's
            return (g["sources"]["Alpha"]["T1"]["to"] == "II.A.1"
                    and g["sources"]["Beta"]["T1"]["to"] == "II.A.2"
                    and TH.verify(g) == [])
        finally:
            TH.ADDR.spine_code_for = keep
    net(a, "every addressed entry carries at least its home volume",
        every_addressed_entry_gets_a_home,
        "a Threads section that is present but empty reads as pending to a person and as done "
        "to a checker, which is the worst of both")

    def an_unaddressed_source_is_recorded_and_refused():
        """THE BRANCH WITH NO TRAFFIC (order bee8fcbd12ab).

        `build()`'s `unaddressed` arm has never run: every one of the 210 catalogued sources
        resolves through `spine_code_for` today, so the code was correct only as far as reading
        could tell. It goes live the first time a source is added to the roll ahead of the
        Acquisitions Index -- which CLAUDE.md Hard Rule 2 calls the ORDINARY case, not an
        exotic one.

        Two properties, and the second is the one that matters. An unaddressed source must be
        RECORDED in the artifact rather than silently dropped, because it is a curatorial gap a
        person has to see; and asking it for a Threads section must REFUSE rather than hand back
        a blank, which is STEP4_PLAN.md §6's "quiet one" (order 98f37cc90ddf).
        """
        import threads as TH
        recs = [{"source": "Addressed", "entries": [{"category": "Persons (x)"}]},
                {"source": "Homeless", "entries": [{"category": "Persons (x)"}]}]
        keep = TH.ADDR.spine_code_for
        try:
            TH.ADDR.spine_code_for = lambda n: ("II.A.1" if n == "Addressed"
                                                else TH.UNADDRESSED)
            g = TH.build(recs)
            if [u["source"] for u in g["unaddressed"]] != ["Homeless"]:
                return False                      # dropped instead of recorded
            if "Homeless" in g["sources"]:
                return False                      # threaded anyway
            try:
                TH.threads_for(g, "Homeless", {"category": "Persons (x)"})
                return False                      # handed back a blank
            except TH.ThreadRefused:
                pass
            return bool(TH.threads_for(g, "Addressed", {"category": "Persons (x)"}))
        finally:
            TH.ADDR.spine_code_for = keep
    net(a, "a source with no address is recorded, and asking it for threads REFUSES",
        an_unaddressed_source_is_recorded_and_refused,
        "the branch had never executed -- all 210 sources resolve today -- and it goes live the "
        "first time a source reaches the roll before the Acquisitions Index, which Hard Rule 2 "
        "calls the ordinary case")

    def the_write_needs_the_owners_ratification(src=None):
        """`main()` must consult `prose_gate.step4_gate_open` before it writes.

        ASKED OF THE PARSE TREE, like the other gate nets in this file: the call has to be a
        call, inside `main`, and reachable. The plan makes the ratification the first gate of the
        whole pass and says nothing in the automation may flip it -- so a pass that derived its
        graph and landed it without asking would have skipped the only step the owner holds.
        """
        tree = _ast_of(os.path.join(_srcdir(src), "threads.py"))
        main = _defn(tree, "main")
        return bool(main) and _calls_within(tree, main, "prose_gate.step4_gate_open",
                                            reachable=True)
    net(a, "the pass asks the owner's ratification before it writes",
        the_write_needs_the_owners_ratification,
        "step4_enabled is owner-held and asserts three things at once: the plan has been read, "
        "its rulings are answered, and Phase 4.0 is done")

    # THIS NET ASSERTED THE GATE WAS SHUT AND IS NOW ASSERTED THE OTHER WAY, on the same
    # terms it was written under: "if this ever goes red without the owner having ruled,
    # the gate has been opened by something that is not a person". The owner ruled on
    # 2026-08-31 and the pass has run. The net still pins the gate to an exact state, so
    # a silent CLOSE is caught as loudly as a silent open was.
    net(a, "the gate stands where the owner ruled it -- OPEN since 2026-08-31",
        lambda: __import__("prose_gate").step4_gate_open()[0],
        "the flag is owner-held in BOTH directions; if this goes red, find the ruling "
        "that closed it, and if there is none then something that is not a person moved "
        "the most consequential flag in the repository after prose_enabled")

    def the_cli_can_actually_finish():
        """RUN IT. Every other net in this area reads the source or asks the gate.

        That is how a green area coexisted with a CLI that could not complete a single
        invocation on this machine: `threads.py` printed one U+2192, `sys.stdout.encoding` is
        cp1252 here, and the crash sat BEFORE the ratification gate -- so on the day
        `step4_enabled` was set the pass would have derived the whole graph, died on a print and
        written nothing. Eight parse-tree and gate nets were green throughout, because none of
        them ran the program.

        `PYTHONIOENCODING` IS DELIBERATELY REMOVED FROM THE CHILD'S ENVIRONMENT. Every harness in
        this project -- allsweep, foreman, overwatch, overnight, autostart, local_agent -- sets
        it for its children, and nothing launches this module, so inheriting it here would
        reproduce the exact blind spot: the bug is invisible to anyone who tests through a
        harness and immediate to the owner at a prompt.

        `--dry-run` writes nothing and does not need the ratification, so this is safe to run on
        a live library every cycle.
        """
        import subprocess
        env = dict(os.environ)
        env.pop("PYTHONIOENCODING", None)
        env["PYTHONUTF8"] = "0"          # and do not let the interpreter opt itself back in
        # CREATE_NO_WINDOW, like every other spawn in this file. Missing it is a black
        # console flashing on the owner's desktop once per battery run, and verify_math
        # catches the omission by name -- which is how this one was found, one run after
        # it was written.
        r = subprocess.run([sys.executable, os.path.join(_srcdir(), "threads.py"), "--dry-run"],
                           capture_output=True, text=True, errors="replace", env=env,
                           cwd=HERE, timeout=600,
                           creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
        # A SAFETY THAT STOPS WORK IS NOT A FAULT THAT STOPS WORK, and this net breached
        # on exactly that confusion the first time a halt stood. `main()` asserts the
        # plant-wide halt before anything else, so under a halt the CLI REFUSES -- which
        # is the correct behaviour, and the first version of this net read it as "the CLI
        # cannot finish". That made the net unable to pass while any halt was up,
        # which means it added a second breach to every halt and helped keep it alive.
        # It is the conflation this project refuses everywhere else, committed inside the
        # battery.
        #
        # So the expected answer depends on the state of the halt, and both answers are
        # "the program ran to completion and said something coherent" -- which is the
        # only thing this net was ever about.
        out = (r.stdout or "") + (r.stderr or "")
        try:
            import escalation as _E
            halted = _E.status()[0]
            refusal = _E.HALT_REFUSAL
        except Exception:
            halted, refusal = False, "THE LIBRARY IS HALTED"
        if halted:
            return refusal in out
        return r.returncode == 0 and "DRY RUN" in (r.stdout or "")
    net(a, "the pass's own CLI runs to completion on this machine's console",
        the_cli_can_actually_finish,
        "eight nets read its source and were green while one arrow character made every "
        "invocation die, before the gate, with the whole graph already derived")

    # ------------------------------------------------- PHASE 4.2 (STEP4_PLAN.md §7F, 2026-09-02)
    # The verifier can finally see the graph. These attack the reading, not the writing: every
    # one drives `thread_integrity`'s pure functions against fixtures or the live artifact and
    # none of them reaches `main()`, which escalates for real.
    import thread_integrity as TI

    def _graph(d, rows):
        p = os.path.join(d, "THREADS.json")
        with open(p, "w", encoding="utf-8") as fh:
            json.dump({"sources": rows, "counts": {}}, fh)
        return p

    def a_thread_to_no_address_is_caught_after_the_fact():
        """§8: 'thread_integrity re-checks afterwards, and DANGLING = 0 is a release gate'."""
        d = tempfile.mkdtemp(prefix="drill_graph_")
        try:
            rows = {"A": {"code": "II.A.3", "T1": {"to": "II.A.3"},
                          "T2": {"Persons": [{"to": "II.ZZ.999"}]}},
                    "B": {"code": "II.A.5", "T1": {"to": "II.A.5"}, "T2": {}}}
            rec, unres, meta = TI.load_thread_graph(_graph(d, rows))
            return unres == [("A", "T2", "II.ZZ.999")] and ("A", "B") not in rec
        finally:
            shutil.rmtree(d, ignore_errors=True)

    def siblings_are_recorded_both_ways_and_never_to_self():
        """The code->sources fold: a Set's members thread to each other, nobody threads to
        itself, and a T2 edge to a sibling code reaches every source filed under it."""
        d = tempfile.mkdtemp(prefix="drill_graph_")
        try:
            rows = {"A": {"code": "II.C.2", "T1": {"to": "II.C.2"},
                          "T2": {"Events": [{"to": "II.C.1"}]}},
                    "B": {"code": "II.C.2", "T1": {"to": "II.C.2"}, "T2": {}},
                    "C": {"code": "II.C.1", "T1": {"to": "II.C.1"},
                          "T2": {"Events": [{"to": "II.C.2"}]}}}
            rec, unres, _ = TI.load_thread_graph(_graph(d, rows))
            return (not unres
                    and {("A", "B"), ("B", "A"), ("A", "C"), ("C", "A"), ("C", "B")} <= rec
                    and ("B", "C") not in rec
                    and all(x != y for x, y in rec))
        finally:
            shutil.rmtree(d, ignore_errors=True)

    def a_corrupt_graph_is_refused_not_read_as_empty():
        """An unreadable graph must never come back as an empty one: an empty graph verifies
        perfectly. §8 makes a corrupt THREADS.json OWNER-level for exactly that reason."""
        d = tempfile.mkdtemp(prefix="drill_graph_")
        try:
            p = os.path.join(d, "THREADS.json")
            for body in ("{ not json", '{"sources": [1, 2]}', '{"sources": {"A": {"T1": {}}}}',
                         '["a list"]'):
                with open(p, "w", encoding="utf-8") as fh:
                    fh.write(body)
                try:
                    TI.load_thread_graph(p)
                    return False                              # read a corrupt file as a graph
                except TI.ThreadGraphUnreadable:
                    pass
            return TI.load_thread_graph(os.path.join(d, "absent.json")) is None
        finally:
            shutil.rmtree(d, ignore_errors=True)

    def the_live_graph_has_no_thread_to_nowhere():
        """THE RELEASE GATE, against the real artifact. A breach here halts the library, which
        is what §8 asks for when 'thread_integrity becomes a drill net'."""
        g = TI.load_thread_graph()
        return g is not None and g[1] == [] and g[2]["recorded_directions"] > 0

    def the_floor_never_rises_to_go_green():
        """§8's ratchet, read in the direction this floor points: a baseline is recorded once,
        lowered when the count drops, and NEVER raised by anything in the automation."""
        d = tempfile.mkdtemp(prefix="drill_floor_")
        try:
            p = os.path.join(d, "floor.json")
            s = [TI._floor_verdict(5, path=p)[0], TI._floor_verdict(7, path=p)[0],
                 TI._floor_verdict(3, path=p)[0], TI._floor_verdict(4, path=p)[0]]
            with open(p, "w", encoding="utf-8") as fh:
                fh.write("{ broken")
            # ORDER 630fe4529c51's CLASS, found 2026-09-06 but named by no order: this last case
            # writes a deliberately unparseable floor file, and `_floor_verdict`'s except arm
            # calls `note("thread_integrity.py:floor-unreadable")` -> `health.record`, writing
            # that row into the LIVE state/failures.json on every drill run. It stood at 39, the
            # drill-run count. The net still asserts the UNREADABLE verdict itself -- which is
            # the property under test -- so nothing is suppressed.
            s.append(_deliberately_failing(lambda: TI._floor_verdict(0, path=p))[0])
            return s == ["baseline", "REGRESSED", "ratcheted", "REGRESSED", "UNREADABLE"]
        finally:
            shutil.rmtree(d, ignore_errors=True)

    net(a, "a thread that resolves to no address is caught after the fact, by the verifier",
        a_thread_to_no_address_is_caught_after_the_fact,
        "edge() prevents it by construction; the verifier is the second, independent layer, and "
        "a second layer that shares the first's failure mode is one layer and a decoy")
    net(a, "a Set's members thread to each other, both ways, and never to themselves",
        siblings_are_recorded_both_ways_and_never_to_self,
        "the graph is keyed source->code and classify() wants source->source; a wrong fold here "
        "would report reciprocity that does not exist or asymmetry that does")
    net(a, "a corrupt graph is REFUSED, never read as an empty one",
        a_corrupt_graph_is_refused_not_read_as_empty,
        "an empty graph verifies perfectly, which is why an unreadable one must fail closed "
        "(OWNER-level, §8)")
    net(a, "no thread on record resolves to no address -- the Phase 4.2 release gate",
        the_live_graph_has_no_thread_to_nowhere,
        "DANGLING = 0 is a release gate, not a metric (§8); measured 0 over 1,508,653 threads "
        "on the day 4.2 was authorised")
    net(a, "the ASYMMETRIC-SUSPECT floor only ever ratchets down",
        the_floor_never_rises_to_go_green,
        "no phase may lower a floor to go green (§8); ruling C keeps existing asymmetry lawful, "
        "so the gate fails only on growth")


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

    def daemons_actually_check_their_own_source(src=None):
        """Every daemon the keeper restarts must call it. Checked by reading them, because a
        daemon that merely COULD check is a daemon that does not.

        THE ROSTER IS DERIVED, NOT TYPED (order 1f172f5acc6f, run #37). This looped over the
        literal `("publish.py", "foreman.py", "overwatch.py")` while its own title promised
        "every standing daemon" -- so a daemon added to the keeper tomorrow was never noticed,
        and on the night this was filed SIX long-lived jobs were up with no codewatch call at
        all, four of them for more than three hours. That is the MEASURED-NOT-MAINTAINED shape
        `derivation.SCAN_MODULES` was corrected for in run #35: a hand-typed list standing in
        for the real population, right and then quietly wrong.

        The real population is `overnight.STANDING`, read out of `overnight.py`'s parse tree so
        that this net has no import side effect and cannot be answered by a module-level
        variable somebody set. STANDING is the correct population and not merely a convenient
        one: `exit_if_stale` EXITS THE PROCESS with rc=17, and the contract that makes that safe
        is the keeper restarting the job within five minutes on the current code (CLAUDE.md,
        Hard Rule -1). A job outside STANDING calling it would simply die. `read.py --run`,
        `feats.py --roll`, `autostart.py --watch` and `overnight.py` itself are long-lived and
        are NOT restarted by the keeper -- they are uncovered, they are known to be uncovered,
        and whether a mid-crawl rc=17 is an acceptable price is an operations ruling rather than
        something this net may decide by going red. Order 2cb8756deb0a carries that half.

        A roster that reads as empty, or shorter than the keeper's own list, FAILS: this net's
        job is to be unsatisfiable by an absence, and "I could not find the daemons" is not
        "every daemon checks".

        AND READ AS A PARSE TREE, NOT AS TEXT (run #36). Both names were substring-searched over
        the whole file, and all three daemons carry long comments about staleness that name
        `codewatch.exit_if_stale` -- `publish.py`'s runs to eight lines and quotes it. A daemon
        that merely MENTIONS the check is exactly the daemon this net exists to catch, and until
        now it could not tell that daemon from one that runs it.

        AND A CALL IS NOT A CALL ON THE PATH THAT MATTERS (order 07c7379597ba, run #37). Both
        spellings were asked of the WHOLE FILE, so a call in a helper nothing invokes, in a
        dead branch, or in a `--once` path the daemon never takes would have answered for the
        loop. The incident this exists for is specifically a LONG-RUNNING loop that never
        re-read its own source: a staleness check that runs once at startup and never again is
        the same daemon with an extra line in it. So `stamp` must be reachable in `main`, and
        `exit_if_stale` must be reachable INSIDE A LOOP in `main`. Three files, and each has
        exactly one call site today -- which is why this could not be exploited and not why it
        was safe.
        """
        import ast
        here = _srcdir(src)
        # THE KEEPER'S OWN LIST, read as data. Every `.py` string constant inside the STANDING
        # assignment is a job the keeper re-asserts; the entries are
        # (name, [path, *args], logfile) so the module name is the only `.py` in each one.
        on_tree = _ast_of(os.path.join(here, "overnight.py"))
        standing = None
        for n in ast.walk(on_tree):
            if isinstance(n, ast.Assign) and any(
                    isinstance(t, ast.Name) and t.id == "STANDING" for t in n.targets):
                standing = n.value
                break
        if standing is None:
            return False                       # no roster read is not "the roster is satisfied"
        names = sorted({os.path.basename(k.value) for k in ast.walk(standing)
                        if isinstance(k, ast.Constant) and isinstance(k.value, str)
                        and k.value.endswith(".py")})
        if len(names) < 3:
            return False                       # a roster that shrank proves nothing
        for f in names:
            tree = _ast_of(os.path.join(here, f))
            main_fn = _defn(tree, "main")
            if main_fn is None:
                return False
            if not _calls_within(tree, main_fn, "codewatch.stamp", reachable=True):
                return False
            if not any(_calls_within(tree, loop, "codewatch.exit_if_stale", reachable=True)
                       for loop in _live_walk(main_fn)
                       if isinstance(loop, (ast.While, ast.For))):
                return False
        return True
    net(a, "every daemon the keeper restarts checks whether its own source has changed",
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
        empty = tempfile.mkdtemp(prefix="drill_codewatch_none_")
        try:
            fp = CW.fingerprint(empty)
            # An empty directory legitimately fingerprints; the None path is the unreadable one.
            return (fp is not None
                    and CW.fingerprint(os.path.join(empty, "does_not_exist")) is None)
        finally:
            shutil.rmtree(empty, ignore_errors=True)
    net(a, "an unreadable source tree is not mistaken for an unchanged one",
        unreadable_source_is_not_reported_as_unchanged,
        "None must never compare equal to a digest")

    def restarts_are_budgeted():
        """Spend the budget against a scratch ledger and require it to RUN OUT, then refill.

        THE OLD NET WAS `isinstance(CW.BUDGET_PER_HOUR, int) and 0 < ... <= 12`. A constant, and
        one nobody was going to set to zero. The enforcement is `_budget_left`, whose rolling
        hour is the whole mechanism: drop the `t > cutoff` filter and a job that restarted four
        times last week can never restart again; drop the subtraction and a daemon bounces for
        ever. Past the budget the job keeps running STALE on purpose — lag beats thrash, and
        this project has already paid for one respawn loop (`autostart._twin_watchdog`). None of
        that was observed by an `isinstance`.

        CORRECTED 2026-09-06 (order 06b7f22484df, remedy (c)). This paragraph used to say
        "`exit_if_stale` reads `left <= 0` and keeps running STALE on purpose past it". That
        stopped being true when the check and the spend were fused: `exit_if_stale` now reads
        `granted, used = _claim_restart_slot(who)` and never inspects a `left` at all — the
        rolling-hour arithmetic moved inside the claim so two twins could not both walk through
        the gap between reading the budget and taking from it. The sentence also predates the
        SECOND refusal reason: a claim is now refused either because the hour's budget is spent
        (`used >= BUDGET_PER_HOUR`) or because the ledger write was DENIED and the spend could
        not be recorded at all (order f06ba4c82363), and codewatch reports those separately
        because they send a person looking for different things. Left as a correction rather
        than a silent edit: this docstring is what a reader consults to decide which branch is
        safe to drive, and a stale explanation of a safety is its own small hazard.

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
        real = CW.LEDGER
        d = tempfile.mkdtemp(prefix="drill_codewatch_budget_")
        who = "__drill__"
        try:
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

    def the_live_claim_path_runs_out_and_refills():
        """THE SAME BUDGET, THROUGH THE FUNCTION THAT ACTUALLY SPENDS IT (order 06b7f22484df).

        The net above drives `_budget_left`, and `codewatch.py`'s own docstring on that function
        says in capitals that it has NO PRODUCTION CALLER: since the run #36 fix `exit_if_stale`
        claims through `_claim_restart_slot` -> `_take_locked(enforce=True)`. `_budget_left`
        delegates to the same two helpers, so the arithmetic it measures is the real one -- but
        the ENFORCEMENT is not arithmetic. It is `if enforce and len(recent) >=
        BUDGET_PER_HOUR: return False`, one branch in a different function, and nothing drove
        it. A budget that is only ever read is not a budget anyone has watched refuse.

        So this spends real slots through the real claim, requires the fifth to be REFUSED, then
        ages the ledger past the rolling hour and requires the budget to come back. Both
        directions, because a claim that always refuses caps a daemon at zero restarts for ever
        and would pass a one-directional test.

        `_claim_restart_slot` and NOT `exit_if_stale`, for the reason the net above states: the
        far end of that function escalates and then exits the process, so a net that reached it
        would raise on a live library or kill the drill. `_claim_restart_slot` takes the ledger
        lock, reads, appends and writes -- it escalates nothing and exits nothing. Confirmed
        against the source this shift.

        BOTH `LEDGER` AND `LEDGER_LOCK` ARE REDIRECTED, and the second one matters here in a way
        it does not above. `LEDGER_LOCK = LEDGER + ".lock"` is computed once at import, so
        repointing `LEDGER` alone leaves the lock file pointing into the real `state/`
        directory -- and unlike `_budget_left`, which never locks, this path creates and removes
        that file on every claim. A probe that litters the live state directory is the shape
        `_ledger_redirected` was written for one module over.
        """
        import codewatch as CW
        real, real_lock = CW.LEDGER, CW.LEDGER_LOCK
        d = tempfile.mkdtemp(prefix="drill_codewatch_claim_")
        who = "__drill__"
        try:
            CW.LEDGER = os.path.join(d, "CODEWATCH.json")
            CW.LEDGER_LOCK = CW.LEDGER + ".lock"
            for i in range(CW.BUDGET_PER_HOUR):
                granted, used = CW._claim_restart_slot(who)
                if not granted or used != i:
                    return False               # a slot inside the budget must be GRANTED
            if CW._claim_restart_slot(who) != (False, CW.BUDGET_PER_HOUR):
                return False                   # ... and the one past it must be REFUSED
            with open(CW.LEDGER, encoding="utf-8") as f:
                doc = json.load(f)
            doc[who] = [t - 3601 for t in doc[who]]     # an hour and a second on
            with open(CW.LEDGER, "w", encoding="utf-8") as f:
                json.dump(doc, f)
            return CW._claim_restart_slot(who) == (True, 0)
        finally:
            CW.LEDGER, CW.LEDGER_LOCK = real, real_lock
            shutil.rmtree(d, ignore_errors=True)
    net(a, "the restart claim itself runs out at the budget, and refills after the hour",
        the_live_claim_path_runs_out_and_refills,
        "the tested arithmetic and the spent arithmetic were two different functions, and only "
        "one of them could refuse anything")

    def a_denied_ledger_write_refuses_the_restart():
        """FAIL CLOSED ON A DENIED WRITE -- the fix of order f06ba4c82363, never watched.

        `_take_locked` used to call `silence.write_json` for its side effect and grant the slot
        regardless. That function returns False rather than raising when the atomic replace is
        denied, and on Windows a denied replace is the ORDINARY case for this file: the
        dashboard reads `CODEWATCH.json` and a reader holding it open is enough. So a
        persistently denied write granted every claim while recording none -- `recent` never
        grew, `BUDGET_PER_HOUR` could never be reached, and the only cap between a daemon that
        keeps exiting and a restart storm was silently absent. Not a smaller budget: no budget,
        with the arithmetic still reporting one.

        The repair is one line -- if the spend cannot be recorded it is not authorised -- and
        nothing anywhere asked whether it was still there. Driven by refusing the write the way
        Windows refuses it, with a bool and not an exception, because an exception is the case
        the surrounding `try` already handled and the bool is the case it did not.
        """
        import codewatch as CW
        import silence as SI
        real, real_lock, real_write = CW.LEDGER, CW.LEDGER_LOCK, SI.write_json
        d = tempfile.mkdtemp(prefix="drill_codewatch_denied_")
        try:
            CW.LEDGER = os.path.join(d, "CODEWATCH.json")
            CW.LEDGER_LOCK = CW.LEDGER + ".lock"
            SI.write_json = lambda *args, **kw: False      # denied, not raised
            # ORDER 247b173c78ee's CLASS, found 2026-09-06 but named by no order: the denial this
            # probe manufactures reaches `note("codewatch.py:record-denied")` -> `health.record`,
            # writing a `silent:codewatch.py:record-denied` row into the LIVE state/failures.json
            # on every drill run. It stood at 39 -- the drill-run count -- beside seven others of
            # the same shape, and "a restart could not be recorded" is exactly the class a person
            # reading that ledger would go looking for a cause of. The net still asserts the
            # refusal itself, so nothing under test is suppressed.
            granted, used = _deliberately_failing(
                lambda: CW._claim_restart_slot("__drill_denied__"))
            return granted is False and used == 0
        finally:
            CW.LEDGER, CW.LEDGER_LOCK, SI.write_json = real, real_lock, real_write
            shutil.rmtree(d, ignore_errors=True)
    net(a, "a restart whose ledger write was DENIED is refused, not granted unrecorded",
        a_denied_ledger_write_refuses_the_restart,
        "a budget whose accounting can fail unnoticed is not a budget; the cap was absent "
        "exactly when the file was busy, which is exactly when daemons are restarting")

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

    def publish_foreman_and_overwatch_refuse_to_run_beside_a_twin():
        """ASKED OF THE PARSE TREE (run #36). `"claim_singleton" not in fh.read()` was satisfied
        by any mention at all, and `publish.py`'s own comment above the call explains at length
        why the guard is there and only fires in loop mode -- so the call could go and the
        explanation would answer for it, which is how two publishers end up in one export repo.

        AND ASKED OF THE PATH, NOT OF THE FILE (order 07c7379597ba, run #37). `_calls` reads
        the whole module, so the claim was answered by a call anywhere in it: in a helper with
        no caller, in a dead branch, in a subcommand the daemon never reaches. That is the same
        distance between "the guard exists" and "the guard is in effect" that this whole area
        is about. It has to be reachable in `main`, which is the process the twin fights with.

        RENAMED, NOT DERIVED (order fe3dc98ca42e). This net was called
        `singleton_guard_is_wired_into_the_daemons` and printed "every standing daemon refuses
        to run beside a twin" while checking a hand-typed three -- the exact defect its neighbour
        `daemons_actually_check_their_own_source` was corrected for at order 1f172f5acc6f, one
        net higher. Deriving the roster from `overnight.STANDING` the same way would take this
        net red the moment it ran, because `dashboard.py` and `pipeline.py` are STANDING and
        neither calls `claim_singleton` -- and whether either one SHOULD is a real question this
        net may not decide by going red. `autostart.watch()` records a deliberate ruling -- cited
        by symbol, not by line, per order 0c7592915a48; the `autostart.py:395` this used to name
        had drifted off it -- that `claim_singleton` is the wrong instrument for a job that has a
        legitimate concurrent `--status` caller, `_twin_watchdog` being the stricter version of
        the same idea; whether the same reasoning covers dashboard and pipeline is not
        recorded anywhere. So: the name now says exactly what the check does -- publish, foreman
        and overwatch, and no promise about "every standing daemon" -- until that ruling lands.
        """
        for f in ("publish.py", "foreman.py", "overwatch.py"):
            tree = _ast_of(os.path.join(_srcdir(), f))
            main_fn = _defn(tree, "main")
            if main_fn is None:
                return False
            if not _calls_within(tree, main_fn, "codewatch.claim_singleton", reachable=True):
                return False
        return True
    net(a, "publish, foreman and overwatch refuse to run beside a twin",
        publish_foreman_and_overwatch_refuse_to_run_beside_a_twin,
        "two publishers into one export repo is the two-writer fault push() documents; whether "
        "dashboard and pipeline need the same guard is order fe3dc98ca42e's open half")

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

    ASKED OF ALL OF src/, NOT ITS TOP LEVEL (order cf9ee9000be8, run #37). This claimed "NO gate
    anywhere in src/" while reading `os.listdir`, which does not descend, and `src/deprecated/`
    holds a module. Same one-line hole as `_no_programmatic_clear`, filed and fixed together.
    """
    import ast
    src = src or os.path.dirname(os.path.abspath(__file__))
    found = []
    for f, full in _src_py_files(src):
        try:
            with open(full, encoding="utf-8") as fh:
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
        # THE FIFTH SPELLING IS DRIVEN TOO (sweep42-batch01). `_no_programmatic_clear` grew
        # detection for the BOUND-NAME ALIAS class -- `f = escalation.clear` and then `f(...)`,
        # order f016ae5433b1 -- and this fixture list was never extended to exercise it, so four
        # of the five documented bypass classes were proven and the fifth was asserted. On the
        # guard that stands over the one function able to lift a halt, "we added a check for it"
        # and "the check works" are not the same claim, and only the second one is evidence.
        #
        # Probed before adding: all three alias spellings below are ALREADY caught by the
        # current scan, so this is a coverage gap being closed rather than a hole being found.
        # It is worth having precisely because a future simplification of that scan would now
        # take this net red instead of passing quietly.
        for i, body in enumerate((
                "import escalation\nescalation.clear('x')\n",
                "import escalation as X\nX.clear('x')\n",
                "from escalation import clear\nclear('x')\n",
                "import escalation as e\ngetattr(e, 'clear')('x')\n",
                "import escalation\nf = escalation.clear\nf('x')\n",
                "import escalation as E\ng = E.clear\ng('x')\n",
                "from escalation import clear as c\nc('x')\n")):
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


def _the_log_roll_off_archives_before_it_trims():
    """No scouting cycle is ever DELETED — and a failed archive costs a duplicate, not a loss.

    THE BRANCH THE BATTERY DID NOT EXECUTE (order 207dd7c41347). Order e8cd908ce5e4 turned
    `scout.sweep`'s roll-off from `_land(LOG, prev[-40:])` -- a silent delete of the oldest
    cycle, every cycle past the fortieth -- into an ARCHIVE-THEN-TRIM move: the overflow is
    appended to `_archive_for(LOG)` first, and the window is trimmed only if every append
    landed. That ordering IS the guarantee, and an ordering is exactly what a later edit
    reverses without noticing. The two existing scout nets run four-cycle fixtures against
    `LOG_CYCLES = 40`, so neither has ever entered this branch: the one piece of scout that
    carries a "nothing is ever lost" promise was the one piece nothing attacked.

    FOUR ASSERTIONS, and the fourth is the one worth the net:
      1. after a sweep, `LOG` holds exactly `LOG_CYCLES` entries;
      2. the archive holds exactly the overflow, in order, one JSON object per line;
      3. their union is the original list -- nothing missing, nothing duplicated;
      4. with `silence.append_line` forced to fail, `LOG` still holds EVERYTHING. A failed
         archive must cost a duplicated cycle, never a deleted one.

    And a fifth, small: `_archive_for(SC.LOG)` must land inside the redirected directory. The
    archive path is derived from `LOG` rather than declared as its own constant precisely so
    that redirecting one redirects the other; nothing proved that it did, and a net that wrote
    into the live `data/` while proving a fixture is how this net's own subject got filed.
    """
    import contextlib
    import io
    import json as _json
    import shutil
    import scout as SC
    import silence as _S
    d = tempfile.mkdtemp(prefix="drillscout3_")
    keep = (SC.hostless, SC.ATTEMPTS, SC.LOG, SC.scout, _S.append_line)
    try:
        table = _synthetic_hostless()
        SC.hostless = lambda: dict(table)
        SC.ATTEMPTS = os.path.join(d, "SCOUT_ATTEMPTS.json")
        SC.LOG = os.path.join(d, "SCOUT.json")
        SC.scout = lambda source, names, register=True: {
            "source": source, "proposed": 0, "kept": [], "checked": [], "note": "drill stub"}
        arch = SC._archive_for(SC.LOG)
        if os.path.dirname(os.path.abspath(arch)) != os.path.abspath(d):
            return False              # the overflow would have gone to the LIVE archive

        # OVERFULL BY THREE. `sweep` appends one cycle of its own, so seeding LOG_CYCLES + 2
        # leaves exactly three to roll off.
        seed = [{"at": "seed-%03d" % i, "results": []} for i in range(SC.LOG_CYCLES + 2)]
        with open(SC.LOG, "w", encoding="utf-8") as fh:
            _json.dump(seed, fh)
        with contextlib.redirect_stdout(io.StringIO()):
            # ORDER 31a946e96c69: this fourth case forces `_S.append_line` to fail on purpose, and
            # scout.sweep's roll-off arm answers that with `note("scout.py:archive-unwritable")`
            # -> `health.record`, writing a `silent:scout.py:archive-unwritable` row into the LIVE
            # state/failures.json on every drill run (measured 2026-09-06 at 39, the drill-run
            # count). The redirect above only silences the PRINTED warning; it never touched the
            # ledger. The net still asserts the real property -- the log keeps every cycle when
            # the archive write fails -- so nothing under test is suppressed.
            _deliberately_failing(lambda: SC.sweep(limit=1, register=False))
        kept = _json.load(open(SC.LOG, encoding="utf-8"))
        rolled = [_json.loads(ln) for ln in open(arch, encoding="utf-8").read().splitlines() if ln]
        if len(kept) != SC.LOG_CYCLES or [c["at"] for c in rolled] != [c["at"] for c in seed[:3]]:
            return False
        # NOTHING MISSING AND NOTHING DUPLICATED across the two files, checked as a sequence
        # rather than as a set so a re-ordering counts as a loss too.
        whole = [c["at"] for c in rolled] + [c["at"] for c in kept]
        if whole != [c["at"] for c in seed] + [kept[-1]["at"]]:
            return False

        # 4 -- THE ORDERING PROPERTY. Archive refused; the log must keep everything.
        with open(SC.LOG, "w", encoding="utf-8") as fh:
            _json.dump(seed, fh)
        _S.append_line = lambda *a_, **k_: False
        with contextlib.redirect_stdout(io.StringIO()), \
                contextlib.redirect_stderr(io.StringIO()):
            # ORDER 31a946e96c69, AND THIS IS THE CALL THAT ACTUALLY LEAKS -- the one directly
            # under the `append_line` stub. My first pass at this order wrapped the case-3 sweep
            # above instead, and a before/after diff of state/failures.json across a full drill
            # run showed `silent:scout.py:archive-unwritable` still climbing (41 -> 42) while the
            # other seven held flat. That measurement is the only reason the mistake was caught:
            # the wrapper looked right and the order was closeable on inspection. The redirects
            # on this line silence the printed warning only; they never touched the ledger.
            _deliberately_failing(lambda: SC.sweep(limit=1, register=False))
        after = _json.load(open(SC.LOG, encoding="utf-8"))
        return len(after) == len(seed) + 1
    finally:
        SC.hostless, SC.ATTEMPTS, SC.LOG, SC.scout, _S.append_line = keep
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
    net(a, "a cycle rolling out of the log is ARCHIVED before the log is trimmed",
        _the_log_roll_off_archives_before_it_trims,
        "the ordering is the whole guarantee, and both existing scout nets run four-cycle "
        "fixtures against LOG_CYCLES=40 -- so this branch had never once been executed")


def drill_recorders_and_lane():
    """Four fixes that landed this shift and had never been watched refuse.

    Each of these is a real repair with a real incident behind it, and each arrived with no net
    -- which by this project's own standing rule means it is not yet evidence of anything. "A
    guard nobody has watched refuse is a guard nobody has evidence about", and a fix in that
    state is indistinguishable, from outside, from a fix that does not work. They are gathered
    in one area rather than scattered because none of the four subsystems had a drill area of
    its own, and inventing four one-net areas would bury them.
    """
    a = "RECENT REPAIRS — a fix nobody has watched refuse is not yet evidence"

    def a_lost_release_reaches_an_escalation():
        """`release()` saying NOT RELEASED must be REPORTED, not returned into a bare statement.

        `binding_health.release()` was rewritten so a lost compare-and-swap returns a string
        beginning "NOT RELEASED" rather than the reason-for-release it could not honour -- and
        both of `run()`'s call sites were bare statements, so the one thing that rewrite
        produced went into the bin. A release that loses five CAS rounds was completely
        invisible: `main()` printed `ok` for the host, the sweep reported it recovered, and the
        host stayed closed off with its coverage switched off (order a29c38c9eff3).

        BOTH DIRECTIONS AND THE RUNG. A refusal must escalate at SUPERVISOR -- a release that
        did not land is an ACTION REPORTED THAT DID NOT HAPPEN, which closes one area of the
        park, not a JANITOR-level observation going stale -- and an ordinary successful release
        must escalate NOTHING, because an alarm that also sounds on the healthy case is
        furniture within a week.
        """
        import contextlib
        import io
        import binding_health as BH
        import escalation as ESC
        seen = []
        real = ESC.escalate
        try:
            ESC.escalate = lambda level, code, what, **k: seen.append((level, code))
            with contextlib.redirect_stderr(io.StringIO()):
                refused = BH._report_not_released(
                    "drill.invalid", "NOT RELEASED: HOST_QUARANTINE.json could not be written")
                quiet = BH._report_not_released("drill.invalid", "canary passed")
        finally:
            ESC.escalate = real
        return (refused is True and quiet is False
                and seen == [(ESC.SUPERVISOR, "HOST_RELEASE_NOT_RECORDED")])
    net(a, "a release that did not land reaches an escalation, not a bare statement",
        a_lost_release_reaches_an_escalation,
        "the host stays quarantined with its coverage off while main() prints ok for it")

    def the_release_verdict_is_actually_passed_to_the_reporter(src=None):
        """...and `run()` must hand it the verdict, in a reachable branch.

        The behavioural net above proves the reporter works. It cannot prove anything reaches
        it, and "the value was computed and dropped" is the exact defect that was filed: a
        `_report_not_released` sitting in the file with `release(h)` still called as a bare
        statement beside it would satisfy every behavioural check ever written.
        """
        import ast
        tree = _ast_of(os.path.join(_srcdir(src), "binding_health.py"))
        run = _defn(tree, "run")
        if run is None or _defn(tree, "_report_not_released") is None:
            return False
        for call in _live_walk(run):
            if not (isinstance(call, ast.Call) and isinstance(call.func, ast.Name)
                    and call.func.id == "_report_not_released"):
                continue
            if any(isinstance(n, ast.Call) and isinstance(n.func, ast.Name)
                   and n.func.id == "release" for arg in call.args for n in ast.walk(arg)):
                return True
        return False
    net(a, "and run() passes release()'s verdict into it rather than discarding it",
        the_release_verdict_is_actually_passed_to_the_reporter,
        "a discarded write verdict in the function whose whole rewrite was about not "
        "discarding it")

    def an_unarbitrable_lane_proceeds_immediately():
        """None from `_take_slot` means GO NOW; False means wait. -> bool.

        `_take_slot` returned one sentinel for two situations needing opposite responses --
        "every slot is live", where waiting is right, and "os.open raised, I cannot arbitrate at
        all", whose own comment promised the caller "proceeds unmetered". It did not proceed:
        `lane()`'s queue loop polled until `deadline = now + SLOT_LEASE_SECONDS`, 900 seconds,
        and then went ahead anyway. `lane()` fronts EVERY model call this library makes, so one
        persistent `os.open` failure on `state/gpu_lane` -- a permissions change, or Norton,
        which already blocks DuckDB and Python TLS on this machine -- turned every model call in
        nine standing jobs into a fifteen-minute stall (order d316c46b67bd).

        DRIVEN WITH THE LEASE SHORTENED, which is the only way to tell the fix from the fault
        inside a battery: at the real 900 seconds the two answers look identical for the first
        fifteen minutes. With the ceiling at two seconds the unarbitrable call must return in
        well under it, and -- the control that makes the first half mean anything -- a BUSY lane
        must still pay the full wait. A net that only proved "None is fast" would also pass
        against a `lane()` that never waited for anything.

        Pointed at a temp `LANE` directory so no real slot is taken or released.
        """
        import shutil
        import gpu_lane as GL
        d = tempfile.mkdtemp(prefix="drill_lane_")
        keep = (GL.LANE, GL.SLOT_LEASE_SECONDS, GL._take_slot, GL.foreground_active)
        try:
            GL.LANE = os.path.join(d, "gpu_lane")
            GL.SLOT_LEASE_SECONDS = 2.0
            GL.foreground_active = lambda ignore_pid=None: False
            GL._take_slot = lambda label: None            # cannot arbitrate
            t0 = time.time()
            with GL.lane("drill"):
                pass
            unarbitrable = time.time() - t0
            GL._take_slot = lambda label: False           # genuinely busy
            t0 = time.time()
            with GL.lane("drill"):
                pass
            busy = time.time() - t0
            return unarbitrable < 0.5 <= busy
        finally:
            (GL.LANE, GL.SLOT_LEASE_SECONDS, GL._take_slot,
             GL.foreground_active) = keep
            shutil.rmtree(d, ignore_errors=True)
    net(a, "a lane that cannot be arbitrated proceeds AT ONCE, and a busy one still waits",
        an_unarbitrable_lane_proceeds_immediately,
        "one os.open failure on state/gpu_lane put a 15-minute stall in front of every model "
        "call in nine standing jobs, and the module header mandates the opposite")

    def a_corrupt_slot_refills_and_a_fresh_one_is_never_stolen():
        """A stranded slot file must return to the pool -- and a slot mid-claim must not.

        THE STRAND (order 763b56061157). `_read()` answers None to two different questions:
        "there is no such file" and "the file is there and will not parse". The reclaim guard
        was `if rec is not None and _expired(rec, ...)`, which filters the second out before
        asking -- so `_expired`'s own first line, `if not isinstance(rec, dict): return True  #
        unreadable/corrupt: reclaim rather than strand`, was UNREACHABLE from the one call site
        written for it. A corrupt or zero-byte slot then fell through to `os.open(O_EXCL)`,
        which raised `FileExistsError` because the file does exist, and `continue` skipped it.
        Forever. `MAX_SLOTS` such files put every model call in every standing job behind a pool
        that can never refill.

        AND THE HALF THAT MAKES THIS NET WORTH MORE THAN THE FIX. The obvious remedy -- reclaim
        whatever will not parse -- is WRONG, and worse than the strand. A zero-byte slot file is
        exactly what a slot looks like in the window between `os.open(O_CREAT|O_EXCL)` creating
        it and the `json.dump` that follows, so "unreadable, therefore reclaim" deletes a slot
        another process claimed microseconds ago and hands one slot to two callers. That fails
        SILENTLY -- the card is oversubscribed and nothing says so -- where the strand at least
        announces itself as a stall. So both directions are attacked here, and a future
        simplification that keeps only the first will go red on the second.

        The reclaim bar is mtime, the only clock an unreadable file has, judged against the same
        lease every readable holder is judged by: a slot mid-creation is milliseconds old, a
        stranded one is older than the lease.

        Pointed at a temp `LANE` so the live lane -- which is arbitrating real model calls -- is
        never touched.
        """
        import gpu_lane as GL
        d = tempfile.mkdtemp(prefix="drill_lane_strand_")
        keep = GL.LANE
        try:
            GL.LANE = d
            # (1) EVERY slot a stranded zero-byte file, aged past the lease. The pool must refill.
            for i in range(GL.MAX_SLOTS):
                p = os.path.join(d, "slot.%d.json" % i)
                open(p, "w").close()
                old = time.time() - (GL.SLOT_LEASE_SECONDS + 60)
                os.utime(p, (old, old))
            got = GL._take_slot("drill-strand")
            if not got:
                return False                  # the pool stayed stranded
            for f in os.listdir(d):
                os.remove(os.path.join(d, f))
            # (2) ONE FRESH zero-byte slot: another process between O_EXCL and its json.dump.
            #     A competitor must leave it alone and report BUSY, not take it.
            fresh = os.path.join(d, "slot.0.json")
            open(fresh, "w").close()
            before = os.path.getmtime(fresh)
            taken = GL._take_slot("drill-thief")
            if GL.MAX_SLOTS == 1 and taken:
                return False                  # it stole a slot that was being claimed
            if not os.path.exists(fresh) or os.path.getmtime(fresh) != before:
                return False                  # it deleted or rewrote somebody's live claim
            return True
        finally:
            GL.LANE = keep
            shutil.rmtree(d, ignore_errors=True)
    net(a, "a lane of corrupt slot files refills, and a slot mid-claim is never stolen",
        a_corrupt_slot_refills_and_a_fresh_one_is_never_stolen,
        "_read() collapses 'absent' and 'unreadable' into one None, so the reclaim branch could "
        "never fire and MAX_SLOTS corrupt files stranded every model call in the library -- "
        "while the obvious fix hands one slot to two callers, silently")

    def a_misaddressed_blob_is_refused():
        """The filename IS a checksum, and `load()` must read it. -> bool.

        `store()` names every blob by `content_hash(text)` and `load()` returned the
        decompressed bytes without ever hashing them back -- declining the one property
        content-addressing gives away for free. It matters concretely: the temp-then-replace
        repair in `store()` stops NEW torn blobs and can do nothing about one already on disk,
        because `store()` never revisits a path that exists. A verifying `load()` is the only
        thing that will ever find one, and it finds it when the damage matters -- as the chapter
        is served to a reader.

        THREE CASES, because a checker that refuses everything is as useless as one that refuses
        nothing: the honest blob must come back, the substituted one must RAISE, and a file
        whose name is not a content address at all must not have a failure invented for it.
        """
        import shutil
        import compress_store as CS
        d = tempfile.mkdtemp(prefix="drill_store_")
        try:
            good = CS.store("the custodian records the specimen" * 20, d)
            if CS.load(good["path"], good["codec"]) != "the custodian records the specimen" * 20:
                return False
            # SUBSTITUTED UNDER ITS OWN NAME: what a torn write or a replaced file looks like.
            other = CS.store("something else entirely" * 20, d)
            shutil.copyfile(other["path"], good["path"])
            if not _deliberately_failing(
                    lambda: _refuses(lambda: CS.load(good["path"], good["codec"]),
                                     RuntimeError)):
                return False
            # NOT CONTENT-ADDRESSED: no address to check, so no failure to invent.
            plain = os.path.join(d, "hand-copied" + os.path.splitext(good["path"])[1])
            shutil.copyfile(other["path"], plain)
            return CS.load(plain, other["codec"]) == "something else entirely" * 20
        finally:
            shutil.rmtree(d, ignore_errors=True)
    net(a, "a blob that is not what its own filename claims is REFUSED, not served",
        a_misaddressed_blob_is_refused,
        "returning text that is not what was stored is the quietest corpus corruption "
        "available to this project")

    def a_competing_flush_cannot_clobber_the_recorder():
        """`health._cas_land` must refuse a write staged against a copy that has moved on.

        THE LOST UPDATE WAS IN THE RECORDER (order d770b1896635) -- the one component whose
        silent failure hides every other component's failure. Two concurrent flushes each read
        the ledger, each merged their own samples, and whichever renamed second landed a
        snapshot taken before the other's edit existed. The write SUCCEEDS, which is why nothing
        ever reported it, and the lost samples look exactly like samples that were never taken.

        Both directions: the stale digest must be refused, and the current one must still land,
        or the recorder has simply been broken into never writing.
        """
        import shutil
        import health as H
        import silence as S
        d = tempfile.mkdtemp(prefix="drill_health_")
        try:
            p = os.path.join(d, "SAMPLES.json")
            with open(p, "w", encoding="utf-8") as fh:
                json.dump({"a": [1]}, fh)
            stale = S.digest_of(p)
            # ...a competitor lands between our read and our write.
            with open(p, "w", encoding="utf-8") as fh:
                json.dump({"a": [1], "b": [2]}, fh)
            # Wrapped for the same reason the blob probe above is: the REFUSAL calls
            # `silence.note`, which writes `silent:silence.py:cas-target-changed` into the
            # library's operational ledger -- one per drill run, in the file whose whole job is
            # to say what is genuinely going wrong. See `_deliberately_failing`.
            landed, _why = _deliberately_failing(
                lambda: H._cas_land(p, {"a": [1, 99]}, stale))
            if landed:
                return False
            with open(p, encoding="utf-8") as fh:
                if json.load(fh) != {"a": [1], "b": [2]}:   # the competitor's write survives
                    return False
            fresh = S.digest_of(p)
            landed2, _why2 = H._cas_land(p, {"a": [1], "b": [2], "c": [3]}, fresh)
            with open(p, encoding="utf-8") as fh:
                return landed2 and json.load(fh) == {"a": [1], "b": [2], "c": [3]}
        finally:
            shutil.rmtree(d, ignore_errors=True)
    net(a, "a flush staged against a stale copy is refused, and a current one still lands",
        a_competing_flush_cannot_clobber_the_recorder,
        "a lost update in the evidence bag looks exactly like evidence that was never "
        "collected, and it is the recorder that hides every other component's failure")

    def a_probe_leaves_the_failure_LEDGER_alone():
        """The other ledger a probe can write to, and nothing was watching it.

        `a_probe_leaves_no_order_behind` enforces exactly this discipline for the WORK ORDER
        queue, and was written because rung-4 probes were decorating it once per battery run.
        The identical thing was happening to `state/failures.json` and nobody had pointed a net
        at it: the two deliberately-failing probes in this area make real guards call
        `silence.note`, which calls `health.record`, so every drill run added one
        `silent:compress_store.py:address-mismatch` and one
        `silent:silence.py:cas-target-changed` to the operational ledger.

        WHY THAT MATTERS MORE THAN THE COUNT. `standards` grades from that file, and
        `foreman.triage_swallowed()` names its classes and then archives and CLEARS it. The
        first of those two classes is `compress_store.load()` refusing a blob whose content hash
        does not match the address it is filed under -- corpus corruption, the quietest kind
        this project has. Order 842025c83c3c cited that very class, at x10, as its flagship
        example of a real fault being erased unspoken. It was this file's own rehearsal. A
        genuine misaddressed blob would have arrived indistinguishable from it.

        ASSERTED BY DOING IT, not by reading the source: the two deliberate failures are
        performed exactly as the probes above perform them, and NOTHING may reach `health.record`
        while they run. Unwrapping either probe turns this red.

        AND IT USED TO COMPARE THE LIVE FILE, BYTE FOR BYTE, WHICH IS A HALT WAITING FOR A
        NEIGHBOUR (order 00f8ca4ab967). `state/failures.json` is, in `health.py`'s own words, the
        highest-traffic shared file in the project: every process in the kit flushes into it under
        compare-and-swap, and any standing job calling `silence.note` inside this net's window
        moved it. A breached drill net escalates to OWNER, so an ordinary daemon doing its
        ordinary job could HALT THE LIBRARY through this net -- which is verbatim the shape
        `twin_detection_does_not_match_bystanders` was rewritten to remove after it caused a false
        halt twice, and that net's ruling is the file's: "a net whose answer depends on what
        happens to be running when it looks is not testing the code".

        THE MASKING DIRECTION THE BYTE COMPARE CLOSED IS NOT REOPENED -- it is closed harder. The
        old worry was that counting entries lets an unrelated recorder's row cancel out a leaked
        one; the answer here is to stop reading the shared file at all and watch THIS PROCESS's
        own `health.record` instead. A stand-in is installed for the duration of the two probes
        and must be called ZERO times. That cannot be cancelled out by anyone, it cannot be
        satisfied by a flush that happened to land between two reads, and it catches a leak whose
        class happens to collide with a bystander's -- all three of which the byte compare could
        not do. It is also the technique `_deliberately_failing` right above already uses, and it
        nests correctly with it: that helper saves whatever `health.record` currently is, puts its
        own no-op in for the wrapped call, and puts this stand-in back afterwards. So a leak is
        exactly a call this stand-in sees, which is exactly a call made OUTSIDE the wrapper --
        i.e. a probe somebody unwrapped.

        THE TWO CLASSES, RE-MEASURED 2026-09-07 by unwrapping both probes and reading what the
        stand-in caught: `silent:compress_store.py:address-mismatch` and
        `silent:silence.py:cas-target-changed`. Five comments in this file -- this one included --
        named the second one `silence.py:stale-write-refused`, which `silence.py` has not emitted
        under that name since the site was renamed, so a person grepping the ledger for the class
        this net protects would have found nothing at all. Corrected in all five.
        """
        import shutil
        import compress_store as CS
        import health as H
        import silence as S

        leaked = []
        real_record = H.record
        H.record = lambda *ar, **kw: leaked.append((ar, kw))
        d = tempfile.mkdtemp(prefix="drill_ledger_probe_")
        try:
            # 1 -- a blob substituted under its own name: `load()` must refuse, quietly.
            good = CS.store("the custodian records the specimen" * 20, d)
            other = CS.store("something else entirely" * 20, d)
            shutil.copyfile(other["path"], good["path"])
            refused_blob = _deliberately_failing(
                lambda: _refuses(lambda: CS.load(good["path"], good["codec"]), RuntimeError))
            # 2 -- a flush staged against a copy that has moved on: `_cas_land` must refuse.
            p = os.path.join(d, "SAMPLES.json")
            with open(p, "w", encoding="utf-8") as fh:
                json.dump({"a": [1]}, fh)
            stale = S.digest_of(p)
            with open(p, "w", encoding="utf-8") as fh:
                json.dump({"a": [1], "b": [2]}, fh)
            landed, _why = _deliberately_failing(
                lambda: H._cas_land(p, {"a": [1, 99]}, stale))
        finally:
            H.record = real_record
            shutil.rmtree(d, ignore_errors=True)
        return refused_blob and not landed and not leaked
    net(a, "a probe's DELIBERATE failures stay out of the library's failure ledger",
        a_probe_leaves_the_failure_LEDGER_alone,
        "a rehearsal recorded in the ledger a person reads to find real faults is worse than "
        "noise: it manufactures the exact signal it exists to prove the library can raise, so "
        "a genuine misaddressed blob arrives indistinguishable from six copies of the drill")

    def a_shared_ledger_keeps_every_row_under_concurrency():
        """`silence.append_line` must not lose or tear rows when processes collide.

        WHY THIS NET EXISTS AND THE ONE ABOVE IT DID NOT CATCH ANYTHING (2026-09-01).
        `verify_math` section 19ag already checks `append_line`: it writes 50 rows and requires
        50 whole rows back. It passes, it has always passed, and it cannot fail -- it writes
        them from ONE process, and tearing is by definition what happens when there are two.
        The hazard the function was WRITTEN for was the one thing its check did not create, so
        m62 read as proven for eight days while the live ledger was still losing rows.

        WHAT WAS ACTUALLY HAPPENING. `O_APPEND` makes the seek-to-end and the write one
        operation on POSIX. On Windows the CRT implements it as a seek FOLLOWED BY a write, so
        two processes seek to the same offset and the second lands ON the first rather than
        after it. Measured with eight processes and 400 rows each: 3,200 expected, 2,496
        arrived, **704 destroyed outright** and 3 torn -- in the ledger
        `standards.ollama_token_flow` grades from. Fixed by taking an OS-level lock for the
        write, and by asking for `O_BINARY` so the CRT stops rewriting every `\\n` into `\\r\\n`
        behind the comment that says it writes exactly the bytes it was handed.

        SIX PROCESSES, EIGHTY ROWS, sized by measurement rather than by feel: against the
        unfixed function that configuration lost 84 of 480 rows in 1.2 seconds, and four
        processes at sixty rows still lost 30. The net therefore goes red on the real defect
        comfortably inside a second, which is what lets it live in the standing battery.

        The assertion is EVERY row, by identity, not a count -- a count can be satisfied by the
        right number of wrong rows.
        """
        import subprocess
        d = tempfile.mkdtemp(prefix="drill_append_race_")
        led = os.path.join(d, "ledger.jsonl")
        child = os.path.join(d, "appender.py")
        procs, rows = 6, 80
        try:
            with open(child, "w", encoding="utf-8") as fh:
                fh.write("import json, sys\n"
                         "sys.path.insert(0, %r)\n" % _srcdir() +
                         "import silence\n"
                         "led, who, n = sys.argv[1], sys.argv[2], int(sys.argv[3])\n"
                         "for i in range(n):\n"
                         "    silence.append_line(led, json.dumps("
                         "{'who': who, 'i': i, 'pad': who * 300}))\n")
            # CREATE_NO_WINDOW: nothing this project starts may pop a console window.
            kids = [subprocess.Popen([sys.executable, child, led, chr(65 + k), str(rows)],
                                     stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                                     creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
                    for k in range(procs)]
            for k in kids:
                k.wait()
            with open(led, "rb") as fh:
                raw = fh.read()
            seen = set()
            for line in raw.split(b"\n"):
                if not line.strip():
                    continue
                try:
                    row = json.loads(line)
                except Exception:
                    return False                      # a torn row is a breach on its own
                seen.add((row.get("who"), row.get("i")))
            want = {(chr(65 + k), i) for k in range(procs) for i in range(rows)}
            return seen == want
        finally:
            shutil.rmtree(d, ignore_errors=True)
    net(a, "a shared ledger keeps EVERY row when six processes append at once",
        a_shared_ledger_keeps_every_row_under_concurrency,
        "O_APPEND is atomic on POSIX and is a seek-then-write on Windows; the existing check "
        "wrote its 50 rows from one process, so the one hazard the function exists for was the "
        "one thing it could not produce -- 704 of 3,200 rows were being destroyed silently")

    def a_coverage_name_that_is_no_module_is_refused():
        """`sweep_plan.record()` USED TO ACCEPT ANY STRING as a coverage claim (order
        f307490add1e), so `missing() == 0` was not evidence that a sweep had read anything: a
        batch that read nothing and recorded four plausible module names was indistinguishable
        from one that read every line of them. The completeness proof the whole sweep rests on
        could not tell a claim from a reading, which is a check that cannot fail.

        BOTH DIRECTIONS, and they are separate faults with separate costs.

        Accepting the spellings that ARE real. On run41 fifteen batches all genuinely read their
        modules and sent three different spellings from three callers -- the label `batches()`
        emits, a `src/`-prefixed path, and a bare name with the extension stripped. `missing()`
        matched only the first, named 26 of 116 modules as never read, and cost a re-audit of
        every one of them. So `src/publish.py` and `foreman` have to resolve.

        Refusing the ones that are NOT. Shard run41.7 recorded `catalogue_local.py`, which this
        module spells `deprecated/catalogue_local.py` -- a name matching nothing, sitting in the
        coverage record, noticed by nothing. That is the direction that matters, because a name
        that resolves to no module is a void claim wearing the shape of proof.

        The basename clause leans on `deprecated/catalogue_local.py` being the only module with
        that basename, which is what makes the resolution exact rather than a guess -- checked
        against the tree this shift: no basename under `src/` is duplicated. If two ever share
        one, `normalise_module` refuses the bare form by design and this clause is the thing
        that will say so.

        PURE. It asks the vocabulary and the resolver and writes no shard, so running it every
        cycle records nothing and disturbs no coverage record.
        """
        import sweep_plan as SP
        known = SP.known_modules()
        return (SP.normalise_module("src/publish.py", known) == "publish.py"
                and SP.normalise_module("foreman", known) == "foreman.py"
                and SP.normalise_module("catalogue_local.py", known)
                == "deprecated/catalogue_local.py"
                and SP.normalise_module("totally_made_up.py", known) is None)
    net(a, "a coverage name that is not a module is refused, and run41's three spellings resolve",
        a_coverage_name_that_is_no_module_is_refused,
        "record() accepted any string, so missing()==0 was not evidence of coverage: a batch "
        "that read nothing and recorded a plausible name looked identical to one that read "
        "every line (order f307490add1e)")

    # THE LEDGER ROUTES ON THE SUBJECT THE ESCALATION HANDS IT (order 5bbbb65e7787, landed
    # 2026-09-06 from handoff/nets_20260906/safety.py). Its sibling in
    # `drill_escalation_behaviour` proves the SUBJECT travels; this proves the ledger routes
    # on it. Either alone passes while the other's half is broken, which is why they are two.
    def a_rehearsal_is_not_filed_as_a_fault():
        """AND THE LEDGER ROUTES ON IT. Both directions: a synthetic subject goes to the
        self-test ledger, a real one stays in the operational ledger. A router that sends
        everything to the self-test ledger empties the ledger a person reads, which is the same
        defect facing the other way."""
        import health as _H
        key = "escalation:SUPERVISOR:DRILL_AREA:drill: one area closing"
        saved_l, saved_s = dict(_H.LEDGER), dict(_H._SELFTEST)
        try:
            _H.LEDGER.clear()
            _H._SELFTEST.clear()
            _H.record(key, "", subject="__drill__")
            if _H._SELFTEST.get(key) != 1 or key in _H.LEDGER:
                return False
            _H.LEDGER.clear()
            _H._SELFTEST.clear()
            _H.record("escalation:SUPERVISOR:AREA_CLOSED", "", subject="Song of Syx")
            return bool(_H.LEDGER) and not _H._SELFTEST
        finally:
            _H.LEDGER.clear()
            _H.LEDGER.update(saved_l)
            _H._SELFTEST.clear()
            _H._SELFTEST.update(saved_s)
    net(a, "a rehearsal lands in the self-test ledger and a fault lands in the real one",
        a_rehearsal_is_not_filed_as_a_fault,
        "7 of 67 keys and 42 of 4,054 counted events in state/failures.json were the battery "
        "rehearsing itself, incrementing once per run with no ceiling")

    # THE PREFLIGHT'S OWN LIVENESS PROBE (order f366f81f6ddc, landed 2026-09-06 from
    # handoff/nets_20260906/safety.py).
    def the_liveness_probe_retries_and_names_what_it_found():
        """This is the preflight's liveness probe. It made ONE attempt per host family
        (`retries=0` against feats.api's default of 2), so a single DNS hiccup or TLS handshake
        failure -- documented, live faults on this machine -- became a preflight problem, a
        stamped row in state/preflight_last.json, a filed MAJOR order and an rc=1 cycle, for a
        condition that had already cleared. `check_caches` in the same file states the doctrine:
        "A permanent red is not extra safety; it is how a preflight stops being read."

        And it did not pass api()'s `outcome` dict, so "fandom API unreachable" was emitted
        identically for the wrong API path -- the 404 that cost 5,590 entries and is this
        check's whole stated purpose -- and for a transient network fault. Two faults with
        opposite remedies, one sentence. api() separates them and its own docstring says that
        channel exists because collapsing them "is NOT tolerable for a liveness probe".

        THREE WORLDS, since a probe that reports every fault as `network` is as useless as one
        that reports every fault as `unreachable`."""
        import feats as F
        import health as _H
        calls = []
        real = F.api

        def stub(why, ok, ret):
            def api(host, params, retries=2, outcome=None):
                calls.append((retries, outcome is not None))
                if outcome is not None:
                    outcome.clear()
                    outcome["ok"], outcome["why"] = ok, why
                return ret
            return api
        try:
            F.api = stub("http-404", False, None)
            rows = _H.check_api_paths()
            if not rows or not all("http-404" in r[1] for r in rows):
                return False
            if not calls or any(r == 0 for r, _ in calls) or not all(o for _, o in calls):
                return False              # retries=0 forced, or the channel not passed
            F.api = stub("network", False, None)
            if not all("network" in r[1] for r in _H.check_api_paths()):
                return False
            F.api = stub("ok", True, {"batchcomplete": True})
            return all("without a `query` block" in r[1] for r in _H.check_api_paths())
        finally:
            F.api = real
    net(a, "the API liveness probe retries, and its report names which fault it found",
        the_liveness_probe_retries_and_names_what_it_found,
        "a spurious red was one packet away and became a filed order; and 'unreachable' is not "
        "actionable while 'http-404 on /api.php' is")

    # TWO OVERNIGHT REPAIRS (orders df385729e15f and 6c3a42f8dbdd, landed 2026-09-06 from
    # handoff/nets_20260906/foreman_overnight.py). Both are the same class as this area's
    # founding four: a caller could not tell a denial from a success.
    def an_owner_queue_denial_is_reported_as_a_denial():
        """A denied FOR_OWNER.md replace must not print as a successful landing.

        `foreman.owner_queue()` staged the markdown to a pid/thread-qualified scratch name and
        landed it with `silence.replace_retry(_tmp, FOR_OWNER)` -- but on refusal it fell straight
        through to `return FOR_OWNER`, the SAME value returned on success. `round_once()` then
        printed "N for the owner -> <path>" over a file that still held the previous round's queue,
        while `publish.py` copies FOR_OWNER.md into the export tree on its own 10-minute loop --
        so a denied replace, the ORDINARY outcome on Windows when any reader holds the target open,
        published a stale decision document under a caption claiming it was fresh (order
        df385729e15f, MAJOR).

        Driven with `silence.replace_retry` monkeypatched to always refuse and `FM.FOR_OWNER`
        redirected to a throwaway temp file, so no real state is touched and no real reader can be
        holding the target open to begin with -- the refusal is forced, not awaited.
        """
        import tempfile
        import shutil
        import foreman as FM
        import silence as SI
        tmpdir = tempfile.mkdtemp(prefix="drill_owner_queue_")
        orig_replace_retry = SI.replace_retry
        orig_for_owner = FM.FOR_OWNER
        try:
            FM.FOR_OWNER = os.path.join(tmpdir, "FOR_OWNER.md")
            with open(FM.FOR_OWNER, "w", encoding="utf-8") as f:
                f.write("previous round\n")
            SI.replace_retry = lambda *a, **k: False       # force the Windows-refuses-the-rename case
            # The denial under test calls `silence.note`, so the call that is SUPPOSED to be
            # refused is wrapped -- see `_deliberately_failing`. The returned SHAPE is still
            # what is asserted, so nothing under test is suppressed.
            result = _deliberately_failing(lambda: FM.owner_queue([]))
            # HELD only if the caller can actually tell the denial happened -- a bare path string
            # (the pre-fix return) is indistinguishable from success at the call site.
            return isinstance(result, tuple) and len(result) == 2 and result[1] is False
        finally:
            SI.replace_retry = orig_replace_retry
            FM.FOR_OWNER = orig_for_owner
            shutil.rmtree(tmpdir, ignore_errors=True)


    net(a, "a denied FOR_OWNER.md replace is reported as denied, not printed as landed",
        an_owner_queue_denial_is_reported_as_a_denial,
        "round_once prints 'N for the owner -> <path>' over a file that still holds the previous "
        "round's queue, exactly when publish.py's next 10-minute loop exports it")


    def scout_hostless_does_not_count_an_unregistered_page_as_found():
        """A source whose URL verified but whose REGISTRATION failed must not read as solved.

        `foreman.scout_hostless()` counted `r.get("kept")` truthy as found, which is true for the
        UNSAVED case `scout.sweep()` deliberately excludes from its own `found` (inside `sweep`
        itself, cited by symbol per order 0c7592915a48 -- not by line: `r["kept"] and
        r.get("registered") is True`) -- so a persistently unwritable
        SOURCE_PAGES.json could print scout's honest '0 of N sources now have somewhere to read
        from' immediately followed by foreman's '4 of 4 sources given somewhere to read from', with
        foreman's line the one that reaches the supervisor's report and the dashboard (order
        6c3a42f8dbdd).

        Driven with `sys.modules["scout"]` stubbed to a fake module returning one result whose
        page verified (`kept`) but whose registration explicitly failed (`registered: False`), so
        no network call happens and no real scout state is touched.
        """
        import sys
        import types
        import foreman as FM
        fake = types.ModuleType("scout")

        def sweep(limit=None):
            return [{"kept": ["http://example.invalid/a"], "registered": False}]
        fake.sweep = sweep
        real = sys.modules.get("scout")
        sys.modules["scout"] = fake
        try:
            ok, why = FM.scout_hostless()
            return ok is False and why.startswith("0 of 1")
        finally:
            if real is not None:
                sys.modules["scout"] = real
            else:
                del sys.modules["scout"]


    net(a, "a verified-but-unregistered source is not counted as given somewhere to read from",
        scout_hostless_does_not_count_an_unregistered_page_as_found,
        "a persistently unwritable registry reads as a scout that is working perfectly, on the "
        "line that reaches the supervisor's report and the dashboard")

    # AND TWO FROM THE 44-ORDER LONG TAIL (orders 91cbbd5e4d24 and f4f3c1d15915, landed
    # 2026-09-06 from handoff/nets_20260906/longtail.py). The first is the whole-corpus
    # idempotency assertion remedy (c) asks for by name, and it is a whole-corpus read rather
    # than a sample on purpose: this class cannot be seen from a single pass, and a SAMPLED
    # idempotency check is exactly the shape this project refuses. It costs about thirty-five
    # seconds of the battery and writes nothing.
    def drill_clean_description_is_idempotent():
        import json as _json, os as _os, cleanup as _C
        recs = _os.path.join(HERE, "data", "records")
        for fn in sorted(f for f in _os.listdir(recs) if f.endswith(".json")):
            try:
                d = _json.load(open(_os.path.join(recs, fn), encoding="utf-8"))
            except Exception:
                continue          # an unreadable record is estate.py's finding, not this net's
            ents = d.get("entries") or []
            if isinstance(ents, dict):
                ents = list(ents.values())
            for e in ents:
                if not isinstance(e, dict):
                    continue
                desc = e.get("description")
                if not desc:
                    continue
                once = _C.clean_description(desc)
                if _C.clean_description(once) != once:
                    return False
        return True

    net(a, "clean_description reaches a fixed point on every catalogued description",
        drill_clean_description_is_idempotent,
        "a second `cleanup.py --apply` must not change what the first one wrote -- "
        "pipeline._is_cleaned_twin is built on that identity")

    # ------------------------------------------------------------------------------------------
    def drill_codex_dedupe_is_typed():
        import catalogue_codex as _CC
        contents = [("Race", "Troglodyte"), ("Language", "Troglodyte"),
                    ("Companion", "Mastiff"), ("Item", "Mastiff")]
        seen = set()
        for et, nm in contents:
            seen.add((_CC.norm(et), _CC.norm(nm)))
        return len(seen) == 4

    net(a, "two element types sharing a name are two elements",
        drill_codex_dedupe_is_typed,
        "a Dragonmark and a Race Variant of the same name must not collapse to one "
        "catalogue entry")


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
        d = tempfile.mkdtemp(prefix="drill_mut_excl_")
        M.LOCK = os.path.join(d, "LOCK.json")
        try:
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
            shutil.rmtree(d, ignore_errors=True)
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
        d = tempfile.mkdtemp(prefix="drill_mut_held_")
        M.LOCK = os.path.join(d, "LOCK.json")
        seen = []
        try:
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
        d = tempfile.mkdtemp(prefix="drill_mut_bad_")
        M.LOCK = os.path.join(d, "LOCK.json")
        try:
            with open(M.LOCK, "w", encoding="utf-8") as fh:
                fh.write("{ this is not json")
            return M.active()[0] is True
        finally:
            M.LOCK = saved
            shutil.rmtree(d, ignore_errors=True)
    net(a, "an unreadable lock is treated as HELD, not as absent", unreadable_lock_counts_as_HELD,
        "an unparseable claim is still a claim")

    def dead_holder_does_not_block_forever():
        """The other half. A lock outliving its process would block every future push, which is
        an outage wearing a safety's clothes."""
        import mutate as M
        saved = M.LOCK
        d = tempfile.mkdtemp(prefix="drill_mut_stale_")
        M.LOCK = os.path.join(d, "LOCK.json")
        try:
            with open(M.LOCK, "w", encoding="utf-8") as fh:
                json.dump({"pid": 999999999, "started": 0, "targets": ["x.py"]}, fh)
            held, rec = M.active()
            return held is False and bool(rec and rec.get("stale"))
        finally:
            M.LOCK = saved
            shutil.rmtree(d, ignore_errors=True)
    net(a, "a lock whose process died is reported stale, not held forever",
        dead_holder_does_not_block_forever,
        "a safety that cannot be released is an outage, and it reports as protection")

    def mutation_never_touches_the_live_tree(src=None):
        """The architectural fix, asserted rather than assumed. `run()` must open the SANDBOX
        path for writing and must verify the live file is byte-identical afterwards.

        ASKED OF THE PARSE TREE (run #36). Three substrings over the whole file, and `mutate.py`
        names `live_file_untouched` in its module docstring before it ever computes it -- so
        two of the three could be satisfied by prose alone. `sandbox` had to be a DEF, the
        untouched verdict had to be RECORDED as a dict entry, and the OWNER-level code had to
        be a code string rather than a word in a paragraph.

        AND ALL THREE WERE STILL SATISFIED BY A `run()` THAT WROTE TO THE LIVE TREE (order
        18612d60c3f2, run #37). Not one of them was scoped to `run`, and not one asked whether
        anything was REACHED: a `sandbox` def nobody calls, a dict key in a return value nobody
        computes, and a marker string anywhere in the module together said nothing whatsoever
        about where the mutants get written. The sweep confirmed it with a crafted `run()`
        writing straight into `src/` unsandboxed. This net is the one that is supposed to
        guarantee mutation testing cannot corrupt the real source -- which it did, twice, on
        2026-08-25, and the second time the corruption reached a public repo.

        SO THE QUESTION IS NOW THE ONE THAT MATTERS: WHAT DOES THE MUTATION BODY WRITE THROUGH?

          1. the write sites are FOUND, in `run` and in whatever `run` delegates to, and there
             has to BE at least one -- a body that writes nothing is not a mutation engine;
          2. EVERY one of them has to be anchored at a path built from a `sandbox()` call. The
             live path in that same function (`os.path.join(SRC, target)`) is not, so a single
             `_write(live, ...)` fails this outright;
          3. the untouched verdict has to be COMPUTED -- a real comparison, not a constant --
             and recorded under its key in what the body returns;
          4. the OWNER escalation has to sit in a REACHABLE branch conditioned on that key.

        `_rooted_names` deliberately does not propagate through file CONTENTS, so reading the
        sandbox file does not make the bytes read out of it count as sandboxed.
        """
        import ast
        tree = _ast_of(os.path.join(_srcdir(src), "mutate.py"))
        recorded = any(isinstance(k, ast.Constant) and k.value == "live_file_untouched"
                       for n in ast.walk(tree) if isinstance(n, ast.Dict) for k in n.keys)
        if not (recorded and _defn(tree, "sandbox") is not None
                and _says(tree, "MUTATE_TOUCHED_LIVE_TREE")):
            return False

        run = _defn(tree, "run")
        if run is None:
            return False
        bodies = [run]
        for name in _call_spellings(tree, run, reachable=True):
            d = _defn(tree, name)
            if d is not None and d is not run and d not in bodies:
                bodies.append(d)

        # 1 + 2 -- the mutants are written, and every write is rooted at the sandbox.
        wrote = False
        for b in bodies:
            targets = _write_targets(tree, b)
            if not targets:
                continue
            rooted = _rooted_names(tree, b, "sandbox")
            if not rooted:
                return False
            for _call, path in targets:
                if not _is_rooted(tree, path, rooted):
                    return False               # a write that does not go through the sandbox
            wrote = True
        if not wrote:
            return False

        # 3 -- the verdict is COMPUTED, not asserted. `"live_file_untouched": True` is a claim.
        computed = False
        for b in bodies:
            for n in _live_walk(b):
                if not isinstance(n, ast.Dict):
                    continue
                for k, v in zip(n.keys, n.values):
                    if (isinstance(k, ast.Constant) and k.value == "live_file_untouched"
                            and isinstance(v, ast.Compare)):
                        computed = True
        if not computed:
            return False

        # 4 -- and the alarm is reachable, in a branch that reads that verdict back.
        for n in _live_walk(tree):
            if not isinstance(n, ast.If):
                continue
            if not any(isinstance(s, ast.Subscript) and isinstance(s.slice, ast.Constant)
                       and s.slice.value == "live_file_untouched"
                       for s in ast.walk(n.test)):
                continue
            arm = _live_stmt_walk(_live_stmts(n.body))
            if (any(x for x in arm if isinstance(x, ast.Call)
                    and _spelled(_spellings_of_call(tree, x), "escalate"))
                    and any(_says(s, "MUTATE_TOUCHED_LIVE_TREE", reachable=True)
                            for s in _live_stmts(n.body))):
                return True
        return False
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

        AND BOTH PROBES NOW CARRY AN OWNER CLAIM (order 22e114422cba, run #37). Neither wrote
        an `_owner.json`, so after the M46 rewrite this net exercised the age gate against two
        directories the reaper considered UNOWNED -- the one case where ownership never gets
        consulted at all. The staged note that came with the M46 fix said this in as many
        words: "reaping a directory to demonstrate the net now requires that directory to have
        a dead or absent owner", and a net whose probes are all absent-owner cannot see the
        difference the fix made. The aged one is claimed by a pid that is definitely gone (so
        it must still reap, by age, on a dead claim) and the fresh one by THIS process (so its
        survival is the ownership rule and the age rule agreeing, not the age rule alone).
        """
        import mutate as M
        if not hasattr(M, "reap_orphans") or M.ORPHAN_AGE_SECONDS < 3600:
            return False
        # CONTAINED 2026-09-06, and this is the net the M46 docstring below points at when it says
        # "the net directly above this one ... destroyed every concurrent sandbox on the machine".
        # It calls the REAL `reap_orphans()` against the REAL temp root. At the default age that
        # looked safe, and it is not, for a reason the age gate cannot see:
        #
        #   A LIVE MUTATION SANDBOX GOES STALE WHILE IT IS BEING USED. `reap_orphans` ages on
        #   `os.path.getmtime(p)` -- the sandbox ROOT -- but a running pass writes into
        #   `p/src/*.py`, which updates `p/src`'s mtime and NOT `p`'s. So after ORPHAN_AGE_SECONDS
        #   a pass that is actively running looks exactly like an abandoned one, and the ownership
        #   check is the only thing left. That check FAILS SAFE TO REAPING by design: an
        #   unreadable, malformed or absent owner file drops back to age-only.
        #
        # PROVED, not argued: a decoy sandbox planted in the real temp root with an unreadable
        # owner claim and a 10-hour age was DELETED by a full drill run on 2026-09-06 -- after the
        # sibling M46 net had already been contained, which is how this second call site was
        # found. The same run's mutation pass had died at 23:20:47 with FileNotFoundError on its
        # own sandbox, 60 seconds after a drill run.
        #
        # Redirecting `tempfile.tempdir` sends both this probe's fixtures and the
        # `tempfile.gettempdir()` inside `reap_orphans` to a throwaway root. The age logic is
        # still proved exactly as before -- one aged fixture reaped, one fresh fixture spared --
        # against the real function. It simply cannot reach anyone else's sandbox to do it.
        _tmp_root = tempfile.mkdtemp(prefix="drill_orphan_root_")
        _saved_tempdir = tempfile.tempdir
        tempfile.tempdir = _tmp_root
        root = tempfile.gettempdir()
        aged = os.path.join(root, M.SANDBOX_PREFIX + "drillprobe_aged_%d" % os.getpid())
        fresh = os.path.join(root, M.SANDBOX_PREFIX + "drillprobe_fresh_%d" % os.getpid())
        try:
            for p, pid in ((aged, 999999999), (fresh, os.getpid())):
                os.makedirs(p, exist_ok=True)
                with open(os.path.join(p, "marker.txt"), "w", encoding="utf-8") as fh:
                    fh.write("drill orphan probe -- safe to delete")
                with open(os.path.join(p, M.OWNER_FILE), "w", encoding="utf-8") as fh:
                    json.dump({"pid": pid, "started": time.time()}, fh)
            # AFTER the owner file is written: creating an entry in a directory updates that
            # directory's mtime, so ageing first and claiming second ages nothing.
            back = time.time() - (M.ORPHAN_AGE_SECONDS + 3600)
            os.utime(aged, (back, back))
            removed = M.reap_orphans()
            return (aged in removed and not os.path.isdir(aged)
                    and fresh not in removed and os.path.isdir(fresh))
        finally:
            # The probe cleans up after itself whichever way the answer came out; a net that
            # leaves litter in TEMP is a net that reproduces the fault it is testing for.
            # The tempdir is restored FIRST and unconditionally, before anything else in this
            # process allocates another temp path.
            tempfile.tempdir = _saved_tempdir
            shutil.rmtree(aged, ignore_errors=True)
            shutil.rmtree(fresh, ignore_errors=True)
            shutil.rmtree(_tmp_root, ignore_errors=True)
    net(a, "abandoned sandboxes are reaped, but only once they are old",
        abandoned_sandboxes_are_reaped,
        "a leak of 50 MB per interrupted run fills a disk without ever reporting anything")

    def _a_reap_never_takes_a_live_runs_sandbox():
        """M46, and the net the age-gate one above could never have been.

        Reaping matched a PREFIX AND AN AGE and nothing else, so it deleted sandboxes belonging
        to other LIVE processes. The age gate was the only thing between a reap and somebody
        else's in-flight run -- and an age gate is exactly what a caller lowers when it wants to
        watch reaping actually happen, so the net directly above this one, IN THE ACT OF BEING
        MADE ABLE TO GO RED, destroyed every concurrent sandbox on the machine. That is what
        killed `mutate.py --target all` about four minutes in, after its own baseline gates had
        passed, for three consecutive runs, while three different diagnoses blamed concurrent
        edits, the drill gate, and drill.py generally.

        Attacked from the direction that actually happened -- a sandbox owned by a DIFFERENT
        live process, against the most aggressive reap there is. All four arms are pinned,
        because a guard that simply stopped deleting anything would pass the first arm and
        quietly restore the 154 MB leak the reaper exists for, and because an ownership claim
        that never expired would do the same thing more slowly: pids are recycled, so a dead
        run's number handed to some unrelated long-lived process would protect its sandbox for
        ever. A fix whose failure mode is the bug it replaced is not a fix.
        """
        import json as _json
        import subprocess as _sp
        import mutate as M

        def _mk(tag, pid, age=0.0, started=None):
            d = tempfile.mkdtemp(prefix=M.SANDBOX_PREFIX + tag + "_")
            os.makedirs(os.path.join(d, "src"), exist_ok=True)
            if pid is not None:
                rec = {"pid": pid}
                if started is not None:
                    rec["started"] = started
                with open(os.path.join(d, M.OWNER_FILE), "w", encoding="utf-8") as fh:
                    _json.dump(rec, fh)
            if age:
                # AFTER the owner file is written: creating an entry in a directory updates that
                # directory's mtime, so ageing first and claiming second ages nothing.
                os.utime(d, (time.time() - age, time.time() - age))
            return d

        made = []
        child = _sp.Popen([sys.executable, "-c", "import time; time.sleep(90)"],
                          creationflags=getattr(_sp, "CREATE_NO_WINDOW", 0))
        # THE BLAST RADIUS IS NOW CONTAINED, 2026-09-06. `reap_orphans` scans
        # `tempfile.gettempdir()`, and this net calls it at `older_than=0` -- the most aggressive
        # reap there is -- in the REAL temp directory, where real mutation sandboxes live. The
        # ownership check this net exists to prove was the ONLY thing standing between that call
        # and somebody's in-flight run, and by its own design it FAILS SAFE TO REAPING: an
        # unreadable, malformed or absent owner file drops back to age-only, which `older_than=0`
        # satisfies for everything. One unlucky read of an owner file and M46 happens again.
        #
        # It may already have. `state/mutate_20260905b.log` died at 23:20:47 with
        # FileNotFoundError on its OWN sandbox's escalation.py, 60 seconds after a drill run
        # finished at 23:19:47, having completed assay.py and prose_gate.py over ~12 hours.
        # Causation is NOT proven and is recorded as unproven in order f0a7... (see the handoff):
        # the one signal that would settle it, `mutate.py:reap-skipped-live-owner`, is suppressed
        # during this call by the `_deliberately_failing` wrapper added the same day.
        #
        # So the root is redirected for the duration. `tempfile.mkdtemp` inside `_mk` and the
        # `tempfile.gettempdir()` inside `reap_orphans` then both resolve to a throwaway
        # directory, and the reap physically cannot see a real sandbox. NOTHING UNDER TEST IS
        # WEAKENED: all four arms still run against a genuinely live pid, a genuinely expired
        # claim, a dead pid and an unowned directory, so the ownership logic is proved exactly as
        # before -- it simply can no longer take a live run with it if it is wrong.
        _tmp_root = tempfile.mkdtemp(prefix="drill_reap_root_")
        _saved_tempdir = tempfile.tempdir
        tempfile.tempdir = _tmp_root
        try:
            live = _mk("netlive", child.pid, started=time.time())
            expired = _mk("netexpired", child.pid, age=10 * 3600,
                          started=time.time() - (M.OWNERSHIP_CEILING_SECONDS + 3600))
            dead = _mk("netdead", 999999999, age=10 * 3600, started=time.time())
            unowned = _mk("netnone", None, age=10 * 3600)
            made = [live, expired, dead, unowned]
            # ORDER 247b173c78ee: the `expired` fixture exists precisely to drive mutate.py's
            # ownership-expiry branch, and that branch calls
            # `note("mutate.py:owner-claim-expired")` -> `health.record`, writing a
            # `silent:mutate.py:owner-claim-expired` row into the LIVE state/failures.json on
            # every drill run -- a manufactured entry indistinguishable from a genuinely expired
            # orphaned sandbox, in the ledger a person reads to find out whether that happened.
            # Measured 2026-09-06 at 39, the drill-run count. The net still asserts every reap
            # verdict below, so nothing under test is suppressed.
            _deliberately_failing(lambda: M.reap_orphans(older_than=0))
            return (os.path.isdir(live)              # the M46 failure itself
                    and not os.path.isdir(expired)   # a recycled pid cannot protect for ever
                    and not os.path.isdir(dead)      # no new disk leak
                    and not os.path.isdir(unowned))  # unclaimed still reaps by age
        finally:
            # Restored FIRST and unconditionally: every later net, and anything this process does
            # afterwards, would otherwise keep writing temp files into a directory this block is
            # about to delete.
            tempfile.tempdir = _saved_tempdir
            child.kill()
            child.wait(timeout=10)
            for d in made:
                shutil.rmtree(d, ignore_errors=True)
            shutil.rmtree(_tmp_root, ignore_errors=True)

    net(a, "a reap never deletes a sandbox whose owner is still running",
        _a_reap_never_takes_a_live_runs_sandbox,
        "M46: reaping matched only a prefix and an age, so the net above -- lowering the age to "
        "prove reaping works -- deleted a live mutation run's sandbox and blocked the whole "
        "mutation mandate for three runs")

    def _a_canonical_snapshot_refuses_when_it_cannot_verify_itself():
        """The backup of the only copy of a 217-source corpus must be able to say no.

        `data/` is gitignored and `git ls-files data/` returns zero, so until 2026-08-27 the 219
        canonical files were in exactly one place on one disk. `canon_backup.snapshot()` reopens
        the archive it wrote and re-hashes every member before recording success -- and that
        read-back is the only thing separating a backup from an assertion that a backup
        happened, so it is what this attacks.

        THREE REFUSALS, and the middle one is the reason this net was rewritten hours after it
        was first staged. An EMPTY canonical set verifies trivially; a PARTIAL one verifies
        PERFECTLY -- every digest of the three files it did collect matches -- and the original
        code guarded only the empty case, so a missing `data/records/` would have produced a
        "verified" snapshot of three small side files. Verification compares what was collected
        against where it came from; it never asks whether the collection was complete.
        """
        import json as _json
        import zipfile as _zip
        import canon_backup as CB
        saved = (CB.ROOT, CB.CANON_FILES, CB.CANON_DIRS, CB.HERE)
        d = tempfile.mkdtemp(prefix="drill_canon_")
        try:
            CB.ROOT, CB.HERE = os.path.join(d, "snaps"), d

            # 1 -- an EMPTY canonical set must refuse, and must write nothing.
            CB.CANON_FILES, CB.CANON_DIRS = (), ()
            try:
                CB.snapshot()
                empty_refused = False
            except RuntimeError:
                empty_refused = True
            if not empty_refused or (os.path.isdir(CB.ROOT) and any(
                    f.startswith("canon-") for f in os.listdir(CB.ROOT))):
                return False

            # 2 -- a PARTIAL set must refuse and must NAME what is missing.
            os.makedirs(os.path.join(d, "data"), exist_ok=True)
            with open(os.path.join(d, "data", "SIDE.json"), "w", encoding="utf-8") as fh:
                fh.write("{}")
            CB.CANON_FILES, CB.CANON_DIRS = ("data/SIDE.json",), ("data/records",)
            try:
                CB.snapshot()
                partial_refused = False
            except RuntimeError as e:
                partial_refused = "records" in str(e)
            if not partial_refused:
                return False

            # 3 -- an archive whose bytes do not match its source must refuse AND self-delete.
            os.makedirs(os.path.join(d, "data", "records"), exist_ok=True)
            with open(os.path.join(d, "data", "records", "a.json"), "w", encoding="utf-8") as fh:
                _json.dump({"real": 1}, fh)
            real_zip = _zip.ZipFile

            class _LyingZip(_zip.ZipFile):
                def write(self, filename, arcname=None, *a_, **k_):
                    return self.writestr(arcname or filename, "{}")

            try:
                _zip.ZipFile = _LyingZip
                try:
                    CB.snapshot()
                    corrupt_refused = False
                except RuntimeError as e:
                    corrupt_refused = "verification" in str(e)
            finally:
                _zip.ZipFile = real_zip
            left = ([f for f in os.listdir(CB.ROOT) if f.startswith("canon-")]
                    if os.path.isdir(CB.ROOT) else [])
            return corrupt_refused and not left
        finally:
            CB.ROOT, CB.CANON_FILES, CB.CANON_DIRS, CB.HERE = saved
            shutil.rmtree(d, ignore_errors=True)

    net(a, "a canonical-corpus snapshot refuses when it cannot verify itself",
        _a_canonical_snapshot_refuses_when_it_cannot_verify_itself,
        "an unverified backup of the only copy of a 217-source corpus is a belief, and both the "
        "empty and the partial case verify perfectly while restoring almost nothing")

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

    def publish_asks_before_pushing(src=None):
        """The step whose failure is IRREVERSIBLE and OUTWARD-FACING. Verified by reading the
        push path, the same way `guards_are_wired_where_claimed` checks the other interlocks --
        a net that actually pushed to prove a refusal would be worse than the bug.

        ASKED OF THE PARSE TREE (run #36). The old form sliced the file text at "def push(" and
        looked for "import mutate" and "REFUSING TO PUSH" in the remainder -- both of which the
        long comment inside `push()` about the two-writer fault could carry on its own.

        AND THAT REWRITE WAS STILL VACUOUS, WHICH IS THE POINT (order 5737db3ce725, run #37).
        Moving the two checks onto the parse tree made them harder to satisfy by accident and
        left them checking the same two facts: that `mutate` is imported, and that the words
        "REFUSING TO PUSH" occur somewhere in `push()`. Neither is the interlock. **Nothing
        asked whether `active()` was ever CALLED**, so a fixture carrying zero interlock logic
        passed -- and worse, measured on the live file: `push()` already raises "REFUSING TO
        PUSH" three separate times for three unrelated reasons, so deleting the genuine
        mutation interlock today would have left this net green on the ledger guard's refusal
        string. This is the guard between a mutation run and a push of deliberately corrupted
        source to a PUBLIC repo, which is not a hypothetical: it happened on 2026-08-25.

        THE INTERLOCK IS NOW REQUIRED AS AN INTERLOCK, in the four parts that make it one, and
        each part is a thing the 2026-08-25 failure actually needed:

          1. `mutate` is imported inside `push` -- REACHABLY, not in a dead branch;
          2. `mutate.active` is CALLED, through any alias spelling, on a reachable path;
          3. the ANSWER IS BOUND to a name, and a reachable `if` is conditioned on that name --
             this is the link nothing checked, and the one a fixture with no logic cannot fake;
          4. the refusal RAISED in that branch's reachable arm says both "REFUSING TO PUSH" and
             "mutation", so the other two refusal strings in this function cannot answer for it.

        A comment produces no Call node, no Name binding and no Raise; dead code produces none
        of them that `_live_walk` will look at.
        """
        import ast
        tree = _ast_of(os.path.join(_srcdir(src), "publish.py"))
        push = _defn(tree, "push")
        if push is None:
            return False
        live = _live_walk(push)
        imports_mutate = any(al.name == "mutate"
                             for n in live if isinstance(n, ast.Import)
                             for al in n.names)
        if not imports_mutate:
            return False
        if not _calls_within(tree, push, "mutate.active", reachable=True):
            return False
        # THROUGH A CONTAINER TOO (2026-08-29). `_bound_from_call` alone sees only
        # `x = mutate.active()`, and `push()` now takes TWO readings and unpacks them out of a
        # list in a `for` (order d56228616f9c) -- a STRONGER interlock, which this net reported
        # as BREACHED for want of a direct assignment. `_carries_result_of` follows the value
        # through the container; it is still a data-dependence test, so an interlock-free
        # fixture still yields nothing and still fails at the next line.
        answered = (_bound_from_call(tree, push, "mutate.active")
                    | _carries_result_of(tree, push, "mutate.active"))
        if not answered:
            return False                      # active() called and its answer thrown away
        for n in live:
            if not isinstance(n, ast.If) or not _guarded_by(tree, n, answered, "mutate.active"):
                continue
            for r in _live_stmt_walk(_live_stmts(n.body)):
                if (isinstance(r, ast.Raise) and _says(r, "REFUSING TO PUSH")
                        and _says(r, "mutation")):
                    return True
        return False
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
        #
        # AND IT ASKED FOR THE ALIAS, NOT THE MODULE (order 7cc460706efe, run #37). The spelling
        # it wanted was the literal `_MUT.active`, so a CORRECT drill.py that happened to write
        # `import mutate as MUT` returned False -- and this net returning False is a breach,
        # which raises an OWNER halt. Renaming a local import would have stopped the library:
        # the identical defect order 8ee268ce32cc filed when a net pinned to `_land` blocked a
        # compare-and-swap fix, and the reason `_spellings_of_call` resolves aliases at all. The
        # question is `mutate.active`, which every spelling of the import answers.
        #
        # Reachability-scoped with it, for the reason every other parse-tree net here now is: a
        # dead `if breached:` carrying the interlock, parked after the live one, would otherwise
        # have answered for a `main()` that halts the library through a mutation run regardless.
        import ast
        tree = _ast_of(os.path.join(_srcdir(), "drill.py"))
        main_fn = _defn(tree, "main")
        if main_fn is None:
            return False
        for n in _live_walk(main_fn):
            if not (isinstance(n, ast.If) and isinstance(n.test, ast.Name)
                    and n.test.id == "breached"):
                continue
            if (_calls_within(tree, n, "mutate.active", reachable=True)
                    and _says(n, "MUTATION RUN IS ACTIVE", reachable=True)
                    and _says(n, "DRILL_BREACH", reachable=True)):
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

        AND CALLING IT IS NOT CONSULTING IT (order 07c7379597ba, run #37). `_calls` reads the
        whole file, so the exclusion list could be fetched and dropped on the floor, or fetched
        in a branch nothing enters, and this net would hold over a builder that queued every
        excluded source exactly as before -- which is, precisely and literally, the five-day
        fault it was written for: a value produced where nobody acts on it. The ANSWER now has
        to be bound to a name and that name has to FILTER something: a comprehension whose
        condition reads it, which is how a work list actually loses a row.

        AND "SOMETHING IS FILTERED SOMEWHERE" IS STILL THE WRONG QUANTIFIER (order 5ed81099fc49,
        run #37). Both halves ran over the whole file, so the filter could live in a HELPER
        NOTHING CALLS while `build_jobs_for_source` queued every source unconditionally, and
        this net held -- which is, again literally, the five-day fault: a value produced where
        nobody acts on it. The sweep built exactly that and it returned True.

        Three things are asked now, and the third is the one that was missing:

          * the exclusions are fetched on the path the program actually runs -- inside `main`,
            reachably, not in a function nothing enters;
          * they still have to FILTER: a comprehension whose condition reads them;
          * and EVERY reachable call that builds jobs for a source has to be handed a value
            DERIVED from that filtered list. `_filtered_names` follows the derivation through
            the assignments, comprehensions, `for` targets and `append`s the list travels
            through, so a copy of the roll taken BEFORE the filter -- the one shape that puts an
            excluded source back in the manifest -- can no longer reach the builder unnoticed.
        """
        import ast
        tree = _ast_of(os.path.join(_srcdir(), "manifest_builder.py"))
        main_fn = _defn(tree, "main")
        if main_fn is None:
            return False
        excluded = _bound_from_call(tree, main_fn, "roll.out_of_scope", reachable=True)
        if not excluded:
            return False
        filters = False
        for n in _live_walk(main_fn):
            if not isinstance(n, (ast.ListComp, ast.SetComp, ast.GeneratorExp, ast.DictComp)):
                continue
            for gen in n.generators:
                for cond in gen.ifs:
                    if any(isinstance(x, ast.Name) and x.id in excluded
                           for x in ast.walk(cond)):
                        filters = True
        if not filters:
            return False
        clean = _filtered_names(main_fn, excluded)
        built = [c for c in _live_walk(main_fn) if isinstance(c, ast.Call)
                 and _spelled(_spellings_of_call(tree, c), "build_jobs_for_source")]
        return bool(built) and all(
            any(isinstance(x, ast.Name) and x.id in clean for a in c.args for x in ast.walk(a))
            for c in built)
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

        AND THE FIRST MATCH ANYWHERE WAS ACCEPTED (order 07c7379597ba, run #37). The walk
        covered the whole tree including code nothing can reach, and it returned True on the
        first qualifying `if` it happened to meet -- so a dead `if r["status"] == OUT_OF_SCOPE:
        pass` parked after a `return` satisfied it while the live promotion carried straight
        on underneath. The guard was one occurrence away from meaning nothing.

        The property is now stated the way an exclusion actually has to hold: every REACHABLE
        write to a record's status is inside the `else` of an out-of-scope guard. One escaping
        write is one routine resync away from promoting an excluded source back, which is the
        trap this net is named after.
        """
        import ast
        tree = _ast_of(os.path.join(_srcdir(), "resync_roll.py"))
        guards = []
        for n in _live_walk(tree):
            if not (isinstance(n, ast.If) and isinstance(n.test, ast.Compare)):
                continue
            if not any(isinstance(c, ast.Attribute) and c.attr == "OUT_OF_SCOPE"
                       for c in n.test.comparators):
                continue
            # WHICH ARM IS THE EXCLUDED ONE DEPENDS ON THE OPERATOR, and reading only one of
            # them is what made this net breach against correct code (2026-08-29). It assumed
            # `if status == OUT_OF_SCOPE: ... else: <relabel>` and required every write to sit
            # in the `else`. The module now spells the identical rule the other way round --
            # `if r.get("status") != _roll.OUT_OF_SCOPE:` with the relabel in the BODY -- which
            # is the same guarantee and arguably the clearer form, and the net called it an
            # exclusion a maintenance script could undo. A guard is not two shapes; it is one
            # property, and the property is that the write is unreachable when the source is
            # out of scope. Both spellings are now read, and a `Compare` that is neither `==`
            # nor `!=` is declined rather than guessed at.
            if len(n.test.ops) != 1 or not isinstance(n.test.ops[0], (ast.Eq, ast.NotEq)):
                continue
            is_eq = isinstance(n.test.ops[0], ast.Eq)
            excluded_arm = n.body if is_eq else n.orelse
            protected_arm = n.orelse if is_eq else n.body
            # The EXCLUDED arm must leave the status alone; a guard that then rewrites it in
            # the very branch it was protecting is not a guard.
            if _subscript_assigns(ast.Module(body=_live_stmts(excluded_arm), type_ignores=[]),
                                  "r", "status"):
                continue
            guards.append(protected_arm)
        if not guards:
            return False
        protected = set()
        for arm in guards:
            for w in _live_stmt_walk(_live_stmts(arm)):
                protected.add(id(w))
        writes = [w for w in _live_walk(tree) if isinstance(w, ast.Assign)
                  and _subscript_assigns(ast.Module(body=[w], type_ignores=[]), "r", "status")]
        return bool(writes) and all(id(w) in protected for w in writes)
    net(a, "a routine resync cannot silently un-exclude a source",
        resync_cannot_revert_an_exclusion,
        "an exclusion a maintenance script can undo unnoticed is not an exclusion")

    def excluded_sources_keep_their_records():
        """Removed from work, NOT from disk. Reversing the ruling must cost one field.

        THE SWALLOWED READ (order a531ac23d07c). This carried a bare `except Exception:
        continue` around the record read -- verbatim the swallow `_policy_corpus_clean`'s own
        docstring records REMOVING from itself, for the stated reason that a swallowed read
        makes a breach here name the wrong fault. A record this net could not open contributed
        no source name, so an unreadable corpus arrived as an EMPTY one, and `not names` reads
        an empty corpus as "nothing was deleted". That is absence read as clean, in the net
        whose whole subject is records that must still be on disk. Counted and failed now, and
        it is the only thing that can fail this net which is not a missing record, so the two
        cannot be confused by whoever reads the breach.
        """
        import roll
        import glob as _g
        ex = roll.out_of_scope()
        if not ex:
            return True
        names, unreadable = set(), 0
        for p in _g.glob(os.path.join(HERE, "data", "records", "*.json")):
            try:
                with open(p, encoding="utf-8") as fh:
                    names.add(json.load(fh).get("source"))
            except Exception:
                unreadable += 1
        # At least one excluded source that HAD records must still have them. If every excluded
        # source lost its records, "exclusion" has quietly become deletion.
        had = [n for n in ex if n in names]
        return unreadable == 0 and (bool(had) or not names)
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
        #
        # AND THAT IS THE WHOLE ASSERTION. A second line used to follow --
        # `return f["stale"] == (newer > 0) or newer == 0` -- which reads as a check and cannot
        # evaluate to False in any of the four states: with `newer > 0` and stale, True == True;
        # with `newer > 0` and not stale, the guard above has already returned; with `newer == 0`
        # the `or` rescues both remaining cases whatever `stale` says. It was a second assertion
        # that never assessed anything, two lines from the only line doing work, in the file whose
        # entire purpose is removing checks that cannot fail (order 9e2fe6e222d9). Deleted rather
        # than tightened, because the overstating direction is deliberately not graded and the
        # comment above already says why.
        return not (newer > 0 and not f["stale"])
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
        """Two lists of canned queries drift. There must only ever be one.

        AGAINST A SCRATCH PATH, NEVER `state/datasette.json` (order 5eea5c20db8a, run #37) --
        the same correction order 38ce9cb3b499 made to `index_query_cannot_write` two nets
        above, for the same reason. This called `datasette_metadata()` with no argument, so
        every drill run REWROTE the live config, inside a module whose header says every attack
        is built in memory or in a scratch directory. The function has taken a path all along.

        AND AN ENVIRONMENTAL WRITE FAILURE IS NOT A BREACH. Since the run #36 fix,
        `datasette_metadata` returns None when the atomic replace is denied -- which its own
        docstring names as the EXPECTED case (cited by symbol, not by line, per order
        0c7592915a48), because a running `datasette` holding
        the file open is enough to cause it on Windows. This net then did `open(None)`, which
        `net()` records as a breach and `main()` escalates to OWNER: an ordinary file lock would
        have halted the library, and the sweep reproduced it end to end. A path that could not
        be written is a measurement that did not happen, and a measurement that did not happen
        must not be graded either way. Scoped to a scratch directory this cannot fail for the
        live-file reason at all; if it fails anyway, that is the machine, not a drift between
        the two lists, and it is recorded where a person will find it rather than sounded as an
        alarm about something else.

        The check itself is unchanged and one degree stricter than it was: the file this reads
        is one this net just generated, so a stale config can no longer be graded as a pass.
        """
        import corpus_db
        d = tempfile.mkdtemp(prefix="drill_datasette_")
        try:
            p = corpus_db.datasette_metadata(os.path.join(d, "datasette.json"))
            if p is None:
                import silence
                silence.note("drill.py:datasette-config-unwritable")
                return True                  # could not measure; not a drift, and not a breach
            with open(p, encoding="utf-8") as fh:
                doc = json.load(fh)
            served = set((doc.get("databases", {}).get("corpus", {}).get("queries") or {}))
            return served == set(corpus_db.CANNED)
        finally:
            shutil.rmtree(d, ignore_errors=True)
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


def drill_resonance():
    """The curl measurement, which was confidently wrong on the commonest contest shape there is.

    `resonance.hodge_decompose` splits a pairwise flow into the best-fitting ladder plus what no
    ladder can explain, and `eta` is the ladder's share. `custodes.convene()`'s Threnody
    curl-veto reads it, so a wrong eta is a veto that fires or abstains on arithmetic nobody
    checked.

    IT WAS PLAIN JACOBI UNDER A FIXED BUDGET (order 6e1c72cddfeb, closed 2026-08-29). Jacobi on
    a graph Laplacian has iteration matrix D^-1 A, whose eigenvalue is -1 on any BIPARTITE
    component: theta oscillates with period two for ever, the gauge-fix subtracts the constant
    mode and not the alternating one, and the budget then sampled whichever phase parity it
    landed on -- 599 sweeps gave eta 0.8, 600 gave 0.0, 601 gave 0.8. A STAR, one entity beating
    three others, measured eta 0.0: "100% irreducibly chord", with `no_evidence` False, so it
    was shaped exactly like a confident measurement and read like one.

    NOTHING PROVED THE REPAIR. Order 3f1dd963252d filed the gap: no net here and no check in
    `verify_math.py` touched this function at all -- its only resonance checks are on
    `incomparability_rate` -- so the fix was a claim. These are the order's own three cases plus
    the bipartite one it names as the case that would have caught the original defect, and every
    one of them is arithmetic on a handful of edges: no corpus, no model, no disk.
    """
    a = "THE CURL — a decomposition that never settled, reported as a measurement"
    import resonance as R

    STAR = {("a", "b"): 1.0, ("a", "c"): 1.0, ("a", "d"): 1.0}
    CYCLE3 = {("a", "b"): 1.0, ("b", "c"): 1.0, ("c", "a"): 1.0}
    PATH4 = {("a", "b"): 1.0, ("b", "c"): 1.0, ("c", "d"): 1.0}
    BIPARTITE = {(h, v): 1.0 for h in ("h1", "h2", "h3", "h4")
                 for v in ("v1", "v2", "v3", "v4")}

    def a_pure_ladder_is_all_ladder():
        """A STAR is EXACTLY representable: theta_a = 0.75, the three losers -0.25 each,
        reproducing every edge. eta must be 1.0 and the curl fraction 0.0. Under Jacobi this
        was 0.0 -- the answer for a shape with NO ladder in it at all, returned for a shape that
        is nothing but ladder."""
        r = R.hodge_decompose(STAR)
        return (r["converged"] is True and r["no_evidence"] is False and r["eta"] == 1.0
                and r["curl_fraction"] == 0.0 and r["irreducibly_chord"] == 0.0)
    net(a, "a pure ladder measures as 100% ladder", a_pure_ladder_is_all_ladder,
        "the STAR -- one entity beating three others -- read eta 0.0 with no_evidence False, "
        "which is a confident measurement of the opposite of the truth")

    def a_bipartite_ladder_is_all_ladder():
        """THE CASE THAT NAMES THE DEFECT. Four heroes each beating four villains by 1.0 is a
        complete bipartite graph, exactly reproduced by theta_h = +0.5 / theta_v = -0.5 -- and
        bipartite is precisely where Jacobi's iteration matrix has eigenvalue -1, so theta[h1]
        went 1, 0, 1, 0, 1, 0, 1, 0 over the first eight sweeps and never approached anything.
        Measured eta 0.0 before the fix, 1.0 after, in two sweeps."""
        r = R.hodge_decompose(BIPARTITE)
        return (r["converged"] is True and r["no_evidence"] is False and r["eta"] == 1.0
                and r["curl_fraction"] == 0.0)
    net(a, "a bipartite ladder measures as 100% ladder", a_bipartite_ladder_is_all_ladder,
        "an oscillation of period two on a bipartite component is the exact fault, and this is "
        "the shape that carries it")

    def a_pure_cycle_is_all_curl():
        """BOTH DIRECTIONS. A method that answered 1.0 to everything would sail past the two
        nets above while measuring nothing. a>b>c>a by 1.0 each is pure curl -- no ladder
        explains any of it -- so eta must be 0.0 and `irreducibly_chord` 100.0. This is the one
        answer the broken version also got right, which is why it cannot be the whole net."""
        r = R.hodge_decompose(CYCLE3)
        return (r["converged"] is True and r["no_evidence"] is False and r["eta"] == 0.0
                and r["curl_fraction"] == 1.0 and r["irreducibly_chord"] == 100.0)
    net(a, "a pure cycle measures as 100% curl", a_pure_cycle_is_all_curl,
        "a decomposition that says 'all ladder' to every input measures nothing; the odd cycle "
        "is what stops the two nets above being satisfied by a constant")

    def an_unfinished_iteration_reports_no_eta():
        """THE FAIL-CLOSED HALF, and the reason the budget is no longer trusted in silence. The
        4-node path needs 18 sweeps to settle; asked for 1, the function must say so -- eta and
        everything derived from it None, `converged` False, `no_evidence` False, because there
        IS evidence here and no measurement of it. An eta read off an unconverged iteration is
        this module's signature failure applied to itself, and it erred toward "maximally
        non-transitive" while `no_evidence` came back False."""
        r = R.hodge_decompose(PATH4, sweeps=1)
        if not (r["converged"] is False and r["sweeps"] == 1 and r["no_evidence"] is False):
            return False
        if any(r[k] is not None for k in ("eta", "curl_fraction", "ladder_representable",
                                          "irreducibly_chord", "theorem_2_error_floor")):
            return False
        # ... and the SAME graph with the budget it needs must produce the number, or this net
        # is satisfied by a function that has simply stopped answering.
        full = R.hodge_decompose(PATH4)
        return full["converged"] is True and full["eta"] == 1.0
    net(a, "an iteration that did not settle returns NO eta at all",
        an_unfinished_iteration_reports_no_eta,
        "at 599 sweeps eta was 0.8, at 600 it was 0.0 and at 601 it was 0.8 again -- no budget "
        "reaches the right answer when the sequence does not converge, and the caller was "
        "handed the number anyway")


# ============================================================== report

# ================================================== THIS SHIFT'S identity.py / dashboard.py
# Landed 2026-09-06 from handoff/nets_20260906/identity_dashboard.py. Every attack below was
# run once against the OLD logic, reconstructed inline (there is no VCS in this checkout to
# revert against), and once against the real post-fix modules: all five RED then GREEN. The
# transcript of that proof run is kept verbatim at the foot of this area, because a net's claim
# to have been watched refuse is the only thing separating it from a green light of unknown
# provenance, and that claim is worth no more than the evidence filed with it.
#
# Each attack is self-contained: it imports the real module under test, patches ONLY a
# module-level path constant (or, for identity.MIN_BEARERS, a module-level tuning constant) to
# point at a scratch file or directory, and restores it in a `finally`. Nothing here touches
# live state/ or data/ files, and the three that drive a repair path wrap the call that is
# SUPPOSED to trip it in `_deliberately_failing`, so the rehearsal stays out of the operational
# failure ledger.
#
# Covers:
#   order d4e2df7d7d6a  identity._is_continuity's majority rule (src/identity.py)
#   order c003673cff01  dashboard.movement()'s corrupt-history repair, Cases A and B
#   order e7ea68901bfe  dashboard.safety()'s drill/escalation UNREADABLE-vs-ABSENT distinction

def drill_identity_dashboard():
    """Attacks against this shift's identity.py / dashboard.py fixes (2026-09-06)."""
    a = "IDENTITY/DASHBOARD — this shift's fixes, attacked (2026-09-06)"
    import tempfile
    import json
    import time as _time

    # ---- order d4e2df7d7d6a --------------------------------------------------------------
    # identity._is_continuity's "BRANCHING" majority test collapsed to the constant
    # `max(2, 0.5*n)`, which is only a real majority at n == 2 (the only value MIN_BEARERS = 3
    # ever lets reach it). Raise MIN_BEARERS and the constant stops tracking a majority without
    # anything else changing. The fix (`shared >= (n // 2) + 1`) is a majority at every n.
    def continuity_majority_scales():
        import identity as ID
        orig = ID.MIN_BEARERS
        try:
            ID.MIN_BEARERS = 5   # lets n == 4 reach the final branch instead of being caught
                                  # by the n >= MIN_BEARERS shortcut above it
            # 2 of 4 bearers shared is NOT a majority (a majority of 4 needs > 2, i.e. >= 3).
            return ID._is_continuity("Foo", {"bearers": 4, "shared": 2}) is False
        finally:
            ID.MIN_BEARERS = orig
    net(a, "a 2-of-4 shared count is refused as a continuity (not a majority)",
        continuity_majority_scales,
        "order d4e2df7d7d6a: max(2, 0.5*n) stopped being a majority rule for any n > 2 and "
        "would silently admit a minority-shared designator the day MIN_BEARERS moved past 3")

    # ---- order c003673cff01, Case A --------------------------------------------------------
    # A history row whose 'at' is a string passed the old `isinstance(h, dict)`-only guard,
    # then raised TypeError (str > float) INSIDE the try -- upstream of the write that would
    # have replaced the bad file -- so the file could never heal itself and every later poll
    # re-threw on the same bytes forever.
    def history_heals_nonnumeric_at():
        import dashboard as DB
        tmp = tempfile.mktemp(suffix=".json")
        orig_history = DB.HISTORY
        try:
            DB.HISTORY = tmp
            corrupt = [{"at": "2026-09-05", "cited": 1}]
            with open(tmp, "w", encoding="utf-8") as f:
                json.dump(corrupt, f)
            before = open(tmp, encoding="utf-8").read()
            # The repair under test calls `silence.note`; only the call that is SUPPOSED
            # to trip it is wrapped (see `_deliberately_failing`), and the healed FILE is
            # still what is asserted.
            _deliberately_failing(lambda: DB.movement({}))
            after = open(tmp, encoding="utf-8").read()
            return after != before and json.loads(after) != corrupt
        finally:
            DB.HISTORY = orig_history
            try:
                os.remove(tmp)
            except OSError:
                pass
    net(a, "a history row with a non-numeric 'at' heals the file rather than wedging it",
        history_heals_nonnumeric_at,
        "order c003673cff01 Case A: the write that would have healed HISTORY was never "
        "reached, so the one function that can replace the file could not -- worse than the "
        "list-of-non-dicts shape order 62286a6c018a fixed, which at least reset and healed")

    # ---- order c003673cff01, Case B --------------------------------------------------------
    # The delta loop (`delta = v - was`) sat OUTSIDE movement()'s try/except. A history row
    # whose metric value is a string cleared the cutoff filter and reached the subtraction
    # unguarded, raising TypeError straight out of movement() -- and state() calls movement()
    # unguarded as its last act, so do_GET's /api/state handler answered an error for the WHOLE
    # page over one bad field in one sample.
    def movement_survives_nonnumeric_metric():
        import dashboard as DB
        tmp = tempfile.mktemp(suffix=".json")
        orig_history = DB.HISTORY
        try:
            DB.HISTORY = tmp
            with open(tmp, "w", encoding="utf-8") as f:
                json.dump([{"at": _time.time() - 3600, "cited": "n/a"}], f)
            try:
                out = DB.movement({"library": {"coverage": {"cited": 5}}})
                return isinstance(out, list)
            except TypeError:
                return False
        finally:
            DB.HISTORY = orig_history
            try:
                os.remove(tmp)
            except OSError:
                pass
    net(a, "a non-numeric stored metric does not raise out of movement()",
        movement_survives_nonnumeric_metric,
        "order c003673cff01 Case B: one string in one history sample used to black out every "
        "panel on the page, including the halt headline panelSafety renders first and loud")

    # ---- order e7ea68901bfe, drill -----------------------------------------------------------
    # safety()'s drill-record except-block's own exemption text covers ONLY "no drill has run
    # yet" (FileNotFoundError). The old bare `except Exception` also swallowed a torn/unreadable
    # file the same way, so the panel that answers "did the nets hold" could not tell "never
    # asked" from "could not read the answer".
    def safety_distinguishes_unreadable_drill():
        import dashboard as DB
        d = tempfile.mkdtemp()
        os.makedirs(os.path.join(d, "state"), exist_ok=True)
        with open(os.path.join(d, "state", "drill_last.json"), "w", encoding="utf-8") as f:
            f.write("{not valid json")
        orig_here = DB.HERE
        try:
            DB.HERE = d
            # `safety()` NOTES the unreadable record it is reporting on, which is correct
            # behaviour and would otherwise file one row per drill run; see
            # `_deliberately_failing`. The reported verdict is still what is asserted.
            out = _deliberately_failing(DB.safety)
            return out.get("drill") == {"unreadable": True}
        finally:
            DB.HERE = orig_here
            # ORDER d015e0a139a8: this `mkdtemp()` carries no `mutate.SANDBOX_PREFIX`, so
            # `reap_orphans` will never take it -- without this line every drill run left one
            # more directory in TEMP forever, which `abandoned_sandboxes_are_reaped` states in
            # as many words is the fault this file exists to catch, not commit.
            shutil.rmtree(d, ignore_errors=True)
    net(a, "an unparseable drill_last.json reports 'unreadable', not 'no drill has run yet'",
        safety_distinguishes_unreadable_drill,
        "order e7ea68901bfe: a JSONDecodeError on a torn drill_last.json, a denial, a lock, an "
        "OSError on getmtime all rendered identically to a drill that has never run")

    # ---- order e7ea68901bfe, escalation -------------------------------------------------------
    # The escalation-ledger except-block's own comment ASSERTS THE VERDICT for every exception
    # ("an empty escalation log is the good state"), not only for the FileNotFoundError it is
    # actually true of. An UNREADABLE escalation log is not the good state and is not an empty
    # one -- it is the ledger of everything the library has escalated in the last 24 hours.
    def safety_distinguishes_unreadable_escalation():
        import dashboard as DB
        d = tempfile.mkdtemp()
        os.makedirs(os.path.join(d, "state"), exist_ok=True)
        # A directory where the log is expected forces a real read failure (IsADirectoryError)
        # rather than the per-line json.loads swallow escalation.log's own parser already does
        # on purpose for one torn LINE (that swallow is correct and is not what this attacks).
        os.makedirs(os.path.join(d, "state", "escalation.log"))
        orig_here = DB.HERE
        try:
            DB.HERE = d
            out = _deliberately_failing(DB.safety)
            return out.get("escalation_unreadable") is True
        finally:
            DB.HERE = orig_here
            # ORDER d015e0a139a8: same leak as this net's sibling above -- no SANDBOX_PREFIX,
            # no reap, one more orphaned directory in TEMP per drill run without this line.
            shutil.rmtree(d, ignore_errors=True)
    net(a, "an unreadable escalation.log reports 'unreadable', not a clean empty 24h",
        safety_distinguishes_unreadable_escalation,
        "order e7ea68901bfe: a read failure on the escalation ledger used to be presented as a "
        "clean 24 hours, the exact 'silence reads as a pass' shape this whole layer exists "
        "against")


# ============================================================================================
# TRANSCRIPT of the RED (pre-fix) -> GREEN (post-fix) proof run, 2026-09-06, produced by a
# throwaway script (not part of this file, not part of the tree) that:
#   (a) re-runs each OLD formula/guard/except-block inline against the same fixture, showing it
#       either returns the wrong answer or raises where the new code does not, and
#   (b) imports the REAL, current identity.py / dashboard.py and runs the attacks above against
#       them, showing each one now HOLDS.
#
# === NET 1: identity._is_continuity majority scaling (order d4e2df7d7d6a) ===
# OLD formula, n=4 shared=2 MIN_BEARERS=5 -> True (expected True = BUG: 2-of-4 admitted as majority)
# NEW code,  n=4 shared=2 MIN_BEARERS=5 -> False (expected False = FIXED)
# NET 1: proven RED (old=True) -> GREEN (new=False)
#
# === NET 2/3: dashboard.movement() (order c003673cff01) ===
# Case A: movement({}) returned [] ; file changed: True
# NET 2 (Case A): file healed instead of wedging -- GREEN
# OLD guard on the case-A corrupt row -> True (True = guard PASSES, so the TypeError below is
#   reached and the write never lands)
# OLD comparison raises: '>' not supported between instances of 'str' and 'float' -- confirms
#   pre-fix WEDGE
# Case B: movement(now_state) returned
#   [{'metric': 'cited', 'now': 5, 'delta': None, 'minutes': 60, 'reset': False, 'stalled': False}]
#   without raising
# NET 3 (Case B): no crash out of movement() -- GREEN
# OLD subtraction raises: unsupported operand type(s) for -: 'int' and 'str' -- confirms
#   pre-fix Case B crash
#
# === NET 4/5: dashboard.safety() drill/escalation UNREADABLE vs ABSENT (order e7ea68901bfe) ===
# drill -> {'unreadable': True}
# escalation_recent -> None  escalation_unreadable -> True
# NET 4/5: UNREADABLE distinguished from ABSENT -- GREEN
# OLD behaviour (reconstructed): both bare `except Exception` blocks would have left drill=None
#   (indistinguishable from 'never run') and escalation_recent=None with no
#   escalation_unreadable flag at all (indistinguishable from 'empty log') -- confirms pre-fix
#   collapse of UNREADABLE into the clean/absent state.
#
# ALL NETS: RED (pre-fix) -> GREEN (post-fix) PROVEN
# ============================================================================================


def drill_hostcheck():
    """The host verdict, and the baseline every lift in the module is computed against.

    Landed 2026-09-06 from handoff/nets_20260906/safety.py; orders d66e629ae3ca and a5fd110e3910.
    Neither of these had ANY drill area to belong to -- `hostcheck.py` scores which wikis the
    library is allowed to mine and nothing in the battery had ever driven `score()` or
    `null_rate()` -- so they get one rather than being filed beside a neighbour that does not
    share their subject.

    Both are the same defect facing opposite directions: strictly LESS evidence buying strictly
    MORE permission. Zero readable article bodies skipped both aboutness veto branches (each
    guarded on `about is not None`) and fell through to lift alone, so a host nothing could be
    read from scored `holds` while a host with two readable bodies scored UNREACHABLE. And
    MIN_PROBE -- whose own comment says "under five names, a hit rate is noise -- 1/2 reads as
    50% and means nothing" -- was enforced twice on the subject side and nowhere on the control,
    while `foreign` is built from at most three names per source.
    """
    a = "THE HOST SCORE — can less evidence buy more permission?"

    def zero_readable_bodies_is_the_thinnest_evidence_and_buys_the_least():
        """`relevance()` answers (None, 0) when no article body could be read at all -- a
        throttle, a 403, a network fault swallowed by its own silence.note, or a wiki serving no
        revisions. Both aboutness veto branches are guarded on `about is not None`, so at n=0
        NEITHER fired and the verdict fell through to lift alone: `holds`, or `partial`, which
        is inside JUDGED. Two bodies read -> UNREACHABLE, host untouched. ZERO bodies read ->
        judged and promoted. Strictly less evidence bought strictly more permission, at the
        bottom end of the very floor ABOUT_MIN was added to hold.

        FOUR ROWS, because three of them are what stops this being a one-directional change:
        the n=1..2 UNREACHABLE must be unchanged, a measured about host must still judge, a
        measured NOT-about host must still be vetoed, and a host already rejected by LIFT must
        STAY rejected -- aboutness is a veto and only ever downgrades."""
        import hostcheck as HC
        saved = {k: getattr(HC, k) for k in ("probe", "null_rate", "relevance")}
        try:
            def row(about, about_n, rate=0.60, base=0.30):
                HC.probe = lambda host, names: {"host": host, "probed": 20, "hits": 12,
                                                "rate": rate,
                                                "titles": ["T%d" % i for i in range(12)]}
                HC.null_rate = lambda host, by=None, exclude=None, sample=40: base
                HC.relevance = lambda host, titles, source, sample=12: (about, about_n)
                return HC.score("en.wikipedia.org", ["a", "b", "c"], "S",
                                by={"S": []})["verdict"]

            return (row(None, 0).startswith("UNREACHABLE")
                    and row(0.0, 2).startswith("UNREACHABLE")
                    and row(0.9, 12) in ("holds", "partial")
                    and row(0.1, 12) == "NAMES ONLY"
                    and row(None, 0, rate=0.31, base=0.30) in ("WRONG FICTION", "NAMES ONLY")
                    and row(1.0, None) in ("holds", "partial"))
        finally:
            for k, v in saved.items():
                setattr(HC, k, v)
    net(a, "a host on which NO article body could be read is unmeasured, not `holds`",
        zero_readable_bodies_is_the_thinnest_evidence_and_buys_the_least,
        "the branch is reached only on the generous hosts the veto exists for -- the "
        "en.wikipedia.org class score() records Rocket League as nearly being adopted onto")


    def a_control_too_thin_to_be_one_is_not_a_baseline():
        """MIN_PROBE exists with the comment "under five names, a hit rate is noise -- 1/2 reads
        as 50% and means nothing", and it was enforced twice on the SUBJECT side and nowhere on
        the CONTROL. `foreign` is built from at most three names per source, so a caller with
        few sources, or one whose rosters overlap heavily, got a control four names wide -- or
        two, or one -- and every lift in the module is computed against it.

        BOTH DIRECTIONS AND THE NETWORK TOO: below the floor the answer must be None AND the
        probe must never have been made (an unmeasurable control is not worth a request), and at
        or above it the control must still measure over the whole sample."""
        import hostcheck as HC
        asked = []
        real = HC.probe
        try:
            HC.probe = lambda host, names: asked.append(list(names)) or {
                "host": host, "probed": len(names), "hits": 1, "rate": 0.5, "titles": []}
            HC._NULL_CACHE.clear()
            # WRAPPED FOR THE LEDGER, NOT FOR THE ASSERTION (see `_deliberately_failing`). The
            # refusal under test IS a `silence.note`, so an unwrapped probe filed one
            # `silent:hostcheck.py:null_rate-control-too-thin` row in `state/failures.json` on every
            # drill run -- a rehearsal arriving in the ledger a person reads to find real faults.
            # Only the call that is SUPPOSED to refuse is wrapped; the return value is still what is
            # asserted, so nothing under test is suppressed.
            if _deliberately_failing(
                    lambda: HC.null_rate("h", by={"A": ["a1", "a2"], "S": ["x"]},
                                         exclude="S")) is not None:
                return False
            if asked:
                return False
            HC._NULL_CACHE.clear()
            wide = {"S%d" % i: ["n%d_%d" % (i, j) for j in range(3)] for i in range(4)}
            if HC.null_rate("h", by=wide) != 0.5:
                return False
            return bool(asked) and len(asked[-1]) >= HC.MIN_PROBE
        finally:
            HC.probe = real
            HC._NULL_CACHE.clear()
    net(a, "a foreign control below MIN_PROBE is unmeasured, not a number",
        a_control_too_thin_to_be_one_is_not_a_baseline,
        "this function's own comment: a baseline measured against the wrong foreign set is "
        "worse than no baseline, because it still looks like one")


def drill_weave_plan():
    """Two thresholds that could be spent without ever having been measured.

    Landed 2026-09-06 from handoff/nets_20260906/weave_rigor.py; orders 12aca83cab86 (weave.py)
    and 9508f9322b4c (sweep_plan.py). They are one area because they are one shape, and it is
    this project's oldest: an UNMEASURED answer spelled as a perfectly ordinary measured one.
    `null_threshold_surprisal` returned 0.0 -- a real, spendable threshold -- whenever no
    permutation trial produced a single pair weight, and `components()` then merged every pair
    that cleared it, which at 0.0 is every pair in the corpus INCLUDING pairs sharing no entity
    at all; complete-linkage agglomeration ran until every source sat in one continuity, with no
    evidence anywhere under it. `frozen_plan` collapsed absent, unreadable and
    parsed-but-not-a-dict into one bare None, so `freeze_plan` recomputed against the live tree
    and landed a NEW plan over the existing file -- destroying it -- while `main()` printed that
    the run's plan "is FROZEN". The list shape it destroys is one this module's own CLI writes.
    """
    a = "THE WEAVE AND THE PLAN — an unmeasured threshold is not a permissive one"

    def weave_components_refuses_nonpositive_threshold():
        """components() must refuse threshold <= 0 rather than merge every source into one cluster.

        Builds a fixture with sources that share NO entity at all (`w={}`, so every pair falls to
        the lookup's absent-pair default of 0.0) and asserts that a threshold of exactly 0.0 is
        REFUSED, not agglomerated into a single continuity the way the pre-fix code did.
        """
        import weave as W
        sources = ["adventure_time", "alien", "warhammer", "one_piece"]
        try:
            W.components(sources, {}, 0.0)
            return False                      # did not raise -- BREACHED
        except ValueError:
            return True                       # HELD


    def weave_null_threshold_surprisal_refuses_unmeasured():
        """null_threshold_surprisal() must raise, not return 0.0, when no trial produced a weight.

        Two distinct unmeasurable inputs: an empty corpus (no entity in the 2..60-source band) and
        a non-positive `--trials`. Both used to return a spendable 0.0; both must now raise
        `weave.NullThresholdUnmeasured`.
        """
        import weave as W
        ok = True
        try:
            W.null_threshold_surprisal({}, {}, [], trials=20)
            ok = False
        except W.NullThresholdUnmeasured:
            pass
        try:
            W.null_threshold_surprisal({"k": ["a", "b"]}, {"k": 1.0}, ["a", "b"], trials=0)
        except W.NullThresholdUnmeasured:
            pass
        else:
            ok = False
        return ok


    def sweep_plan_freeze_plan_refuses_a_broken_existing_file():
        """freeze_plan() must refuse -- not recompute and overwrite -- a plan file that exists but
        is not a usable frozen-plan record.

        Reproduces case (c) from the order: a bare JSON list at plan_path(run), the shape this
        module's own `--batches N --out PATH` writes. Asserts the file is left byte-for-byte
        unchanged and the return carries `frozen: False, reason: "not_a_dict"`.
        """
        import json
        import shutil
        import tempfile
        import sweep_plan as SP

        tmp = tempfile.mkdtemp(prefix="drill_sweepplan_freeze_")
        real_plans = SP.PLANS
        try:
            SP.PLANS = tmp
            run = "__drill_freeze_plan_case_c__"
            path = SP.plan_path(run)
            with open(path, "w", encoding="utf-8") as f:
                json.dump([{"batch": 1, "lines": 10, "modules": ["a.py"]}], f)
            before = open(path, encoding="utf-8").read()

            # The refusal under test calls `silence.note`, so the call that is SUPPOSED to
            # refuse is wrapped -- see `_deliberately_failing`. The verdict is still asserted.
            rec = _deliberately_failing(lambda: SP.freeze_plan(run, 4))

            after = open(path, encoding="utf-8").read()
            return (before == after and rec.get("frozen") is False
                    and rec.get("reason") == "not_a_dict")
        finally:
            SP.PLANS = real_plans
            shutil.rmtree(tmp, ignore_errors=True)

    net(a, "components() refuses a non-positive threshold instead of merging every source",
        weave_components_refuses_nonpositive_threshold,
        "order 12aca83cab86 -- threshold<=0 makes every absent-pair default (0.0) clear the bar, "
        "degenerating complete linkage to one continuity containing everything")

    net(a, "null_threshold_surprisal refuses an unmeasured null instead of returning 0.0",
        weave_null_threshold_surprisal_refuses_unmeasured,
        "order 12aca83cab86 -- an empty corpus or trials<=0 used to hand back 0.0, spent by "
        "components() as the most permissive threshold there is")

    net(a, "freeze_plan refuses to recompute over an existing non-dict plan file",
        sweep_plan_freeze_plan_refuses_a_broken_existing_file,
        "order 9508f9322b4c -- case (c): `--batches N --out PATH` writes a bare JSON list at the "
        "plan path, and freeze_plan used to silently recompute and overwrite it")


# ==================================================== THE ONE GUARD BETWEEN A SCRATCH
#                                                      SCRIPT AND THE PUBLIC REPO
# Landed 2026-09-06 from handoff/nets_20260906/unlocated.py.
#
# WHY THIS NET EXISTS.
#
# `publish._is_agent_scratch` (a function in src/publish.py -- cited by symbol, not by line, per
# order 0c7592915a48: this citation had already drifted from :205-214 to the real :209-215
# before drifting further still) is the only thing between an agent's
# throwaway `.py` script and the PUBLIC repo. It is the repair for the class behind the
# 2026-08-28 SECRET_IN_EXPORT halt: a sweep agent asked to demonstrate that the secret scanner
# catches credentials wrote the fixtures into a script under `handoff/`, which is a
# `publish.COPY_DIRS` root, so the file was staged for publication. Nothing leaked -- the secret
# gate refused the push -- but the fault was the PATH, and this is the guard that now closes it.
#
# NOTHING IN THE BATTERY WATCHED IT REFUSE until this area landed. Measured 2026-09-06: `_is_agent_scratch` and
# `CODE_FREE_DIRS` appear NOWHERE in src/drill.py and NOWHERE in src/verify_math.py. By Hard
# Rule -1's third property that makes it an unproven safety -- "a guard nobody has watched
# REFUSE is a guard nobody has evidence about" -- and it is the exact shape the same rule warns
# about, because the guard is silent when it works: a file that is quietly not copied looks
# identical to a file that was never there.
#
# It is live and it is firing. `state/failures.json` carries
# `silent:publish.py:agent-scratch-refused` at 33, `publish.gitignore_lines()` emits
# `handoff/**/*.py`, `handoff/*.py` and the .pyw/.pyi variants, and the export copy at
# C:\Users\imarl\panscriptum-export holds ZERO .py files under `handoff/` against 20 in the live
# tree. So the guard works today and nothing would notice if it stopped.
#
# THIS ALSO CORRECTS AN OPEN ORDER. `a66423722e45` (AGENT_SCRATCH_IN_PUBLISHED_TREE, MINOR, RUN)
# says of those files "so every one of them is copied to the PUBLIC repo on the next push".
# THAT IS NO LONGER TRUE, and the sentence is generated by the detector in
# `workorders.sweep` (src/workorders.py, the `handoff-scratch` block), so it will be regenerated
# verbatim on every sweep until someone who owns that file rewrites it. The detector's LIST is
# still correct and still worth having; only its stated consequence is stale. Left as an open
# order rather than closed, because the files really are still there and where they should live
# is a curatorial call, but the urgency it claims is not real.
#
# ============================================================================================
# THE ATTACK THAT WOULD DEFEAT WHAT EXISTS TODAY
# ============================================================================================
#
# Somebody removes `CODE_FREE_DIRS`, empties it, drops `.py` from `_CODE_EXT`, or -- the one
# that leaves every existing artefact looking right -- deletes the four lines in `sync_tree`
# that ASK the predicate, leaving `_is_agent_scratch` defined, documented, unit-testable and
# never called. `gitignore_lines()` would still name the pattern, the docstrings would still
# describe the guard, and the next `--push` would publish the scripts. That is the FOURTH
# PROPERTY, IN EFFECT, and it is why the third net below asks the parse tree rather than the
# predicate.
#
# ============================================================================================
# PROVEN RED BEFORE LANDING (2026-09-06) -- each net run against a deliberately broken fixture
# ============================================================================================
#
#   net 1  `CODE_FREE_DIRS = ()`                      -> the_scratch_gate_refuses_code_under_handoff  False
#   net 1  `_CODE_EXT = (".pyw", ".pyi")`             -> the_scratch_gate_refuses_code_under_handoff  False
#   net 2  gitignore_lines() with the handoff rules removed -> the_ignore_file_names_the_same_class  False
#   net 3  a `sync_tree` fixture with the four-line   -> the_copy_loop_actually_asks_the_gate         False
#          `if _is_agent_scratch(rel): ... continue`
#          block deleted, everything else identical
#
# and GREEN against the live module and the live `src/publish.py` as they stand today. The
# fixtures and the runner are in the session scratchpad, not in this repo -- which is the
# practice order `a66423722e45` is actually asking for.
#
# NOT USING `_gate_precedes_spawn`, DELIBERATELY, AND THAT IS WHY NET 3 LOOKS UNLIKE ITS
# SIBLINGS.
# The obvious move is to reuse the house helper the way `_the_loop_asks_the_gate` does for
# `maintenance_shift_live`. It would report BREACHED against correct code. `_gate_precedes_spawn`
# requires the guard's answer to be BOUND to a name (`_bound_from_call` only matches
# `ast.Assign` / `ast.AnnAssign`), and `sync_tree` tests the predicate inline --
# `if _is_agent_scratch(rel):` -- so the bound-name set comes back empty and the helper returns
# False. A net that goes red on a correct guard is worse than no net, so net 3 below asks the
# same three-part question directly against this shape: the `if` TESTS the predicate, the arm
# LEAVES by `continue`, the arm COPIES NOTHING, and every `shutil.copy2` in the function sits
# outside that arm.
#

def drill_agent_scratch_gate():
    """The one guard between an agent's throwaway script and the public repo.

    THE FAULT IT REPAIRS is a PATH, not a string. `handoff/` is a `publish.COPY_DIRS` root and
    is the directory every sweep brief points agents at, correctly, for their `.md` audits and
    `.json` queue state. A `.py` file there is by construction something somebody ran once, and
    on 2026-08-28 one of them carried credential-shaped fixtures into the publish staging area.

    ATTACKED FROM BOTH SIDES, because a guard that refuses everything is a wall and would take
    `handoff/`'s audits and queue state out of the published record along with the scripts --
    which is the whole reason `handoff/` is in `COPY_DIRS` in the first place.

    AND FROM THE THIRD SIDE, which is the one the other two cannot see: whether `sync_tree`
    still ASKS. The predicate is pure and will keep answering correctly long after the call
    site is gone, and a guard nothing calls is a comment.
    """
    a = "THE PUBLISHED TREE — can an agent's working script still reach the public repo?"

    def the_scratch_gate_refuses_code_under_handoff():
        import publish as P
        return (P._is_agent_scratch("handoff/run35/checks_F1.py")
                and P._is_agent_scratch("handoff/nets_20260906/unlocated.py")
                and P._is_agent_scratch("handoff/x.pyw")
                and P._is_agent_scratch("handoff/x.pyi")
                and P._is_agent_scratch("handoff/deep/deeper/still.PY")   # case, and depth
                # EVERY EXECUTABLE SHAPE, NOT JUST PYTHON'S (orders e7e00ffde6c5, 749597eb95d4).
                # `_CODE_EXT` enumerated one language's suffixes while `_is_agent_scratch` exists
                # to refuse scratch CODE by WHERE it sits, so a `.sh`/`.ps1`/`.bat` an agent left
                # under handoff/ synced to the export tree and was pushed to the PUBLIC repo. The
                # net asserted only the `.py` family, so it would have stayed green through the
                # whole hole -- and would stay green again if the tuple were narrowed back.
                and P._is_agent_scratch("handoff/x.sh")
                and P._is_agent_scratch("handoff/x.ps1")
                and P._is_agent_scratch("handoff/x.bat")
                and P._is_agent_scratch("handoff/run35/helper.js")
                # ... and refuses NOTHING else: the record itself must still publish.
                and not P._is_agent_scratch("handoff/AUDIT_batch11.md")
                and not P._is_agent_scratch("handoff/queue/state.json")
                and not P._is_agent_scratch("handoff")          # the root is never a file
                and not P._is_agent_scratch("src/publish.py")   # src/ IS the published code
                and not P._is_agent_scratch("reference/x.py"))
    net(a, "a .py under handoff/ is refused, and nothing else is",
        the_scratch_gate_refuses_code_under_handoff,
        "the 2026-08-28 SECRET_IN_EXPORT halt was a working script written into a COPY_DIRS "
        "root; a gate that also refused the .md audits would take the record out of the "
        "published tree, which is what handoff/ is in COPY_DIRS to carry")

    def the_ignore_file_names_the_same_class():
        """THE SAME CLASS MEANS THE WHOLE CLASS, NOT THE .py FAMILY (order fcee2bec657c).

        This asserted six hand-typed patterns -- `.py`/`.pyw`/`.pyi` in both the root and the
        `**` forms -- while `publish._CODE_EXT` holds seventeen suffixes and `gitignore_lines()`
        derives its patterns from `CODE_FREE_DIRS` x `_CODE_EXT`. So the net checked roughly a
        third of what the function it grades actually emits, and the two layers could cease to
        agree for any suffix outside that family without anything going red. Its own printed
        expectation is that "two layers enforcing DIFFERENT rules is one layer and a decoy", and
        the sibling directly above it already asserts `.sh`, `.ps1`, `.bat` and `.js` on the
        COPY-GATE side -- so the decoy was on this side of the pair.

        ASKED OF THE GATE, NOT OF THE TUPLE, which is what keeps it from being a tautology.
        `gitignore_lines()` and `_is_agent_scratch` both read the same two constants today; the
        question is whether they still describe the same class TOMORROW, so the expectation is
        built from what the copy gate actually REFUSES -- one probe path per root per suffix --
        and every refusal must have both ignore forms behind it. A hand-typed `.gitignore`, or a
        derivation that quietly narrows to one language, is then exactly what goes red.

        THE SIX LITERALS STAY AS A FLOOR. A for-all over `_CODE_EXT` is satisfied vacuously by an
        EMPTY `_CODE_EXT` -- which is the fault the sibling net has a fixture for -- so the .py
        family is still named outright and the derived half is added on top of it, never instead.
        """
        import publish as P
        lines = set(P.gitignore_lines())
        # BOTH FORMS. `handoff/*.py` alone misses every subdirectory, which is where all 20 of
        # the live scratch scripts actually are; `handoff/**/*.py` alone misses the root.
        if not all(p in lines for p in ("handoff/**/*.py", "handoff/*.py",
                                        "handoff/**/*.pyw", "handoff/*.pyw",
                                        "handoff/**/*.pyi", "handoff/*.pyi")):
            return False
        refused = 0
        for d in P.CODE_FREE_DIRS:
            for e in P._CODE_EXT:
                if not P._is_agent_scratch("%s/__drill_ignore_probe__%s" % (d, e)):
                    continue     # the copier does not refuse it, so the ignore file need not
                refused += 1
                if not all(p in lines for p in ("%s/**/*%s" % (d, e), "%s/*%s" % (d, e))):
                    return False
        # ... and the derived half must have had something to say. A `CODE_FREE_DIRS` or a
        # `_CODE_EXT` emptied out leaves the copy gate refusing nothing, which is a hole in the
        # OTHER layer -- the sibling net's job -- but it must not be able to make this one pass
        # by having examined nothing at all.
        return refused > 0
    net(a, "the export .gitignore names the same class the copy gate refuses",
        the_ignore_file_names_the_same_class,
        "the copy gate and the ignore file are two independent layers over one rule, and two "
        "layers enforcing DIFFERENT rules is one layer and a decoy")

    def the_copy_loop_actually_asks_the_gate(src=None):
        """IN EFFECT, asked of the parse tree in the same three parts as the launcher nets.

        Not through `_gate_precedes_spawn`: that helper requires the answer to be BOUND to a
        name and `sync_tree` tests the call inline, so it would report BREACHED against correct
        code. The three parts are unchanged -- the predicate is ASKED in the test of a reachable
        `if`, that arm LEAVES without copying, and every reachable copy sits outside it.
        """
        import ast
        tree = _ast_of(os.path.join(_srcdir(src), "publish.py"))
        fn = _defn(tree, "sync_tree")
        if fn is None:
            return False
        maps = _import_maps(tree)
        copies = [n for n in _live_walk(fn)
                  if isinstance(n, ast.Call) and _spelled(_spellings_of_call(tree, n, maps),
                                                          "copy2")]
        if not copies:
            return False          # a sync that copies nothing proves nothing about a copy gate
        for g in _live_walk(fn):
            if not isinstance(g, ast.If):
                continue
            asked = [c for c in ast.walk(g.test)
                     if isinstance(c, ast.Call)
                     and _spelled(_spellings_of_call(tree, c, maps), "_is_agent_scratch")]
            if not asked:
                continue
            if not _arm_leaves(g.body, (ast.Continue,)):
                continue          # a guard that falls through is not a guard
            inside = {id(x) for x in _live_walk(g)}
            if all(id(c) not in inside and c.lineno > g.lineno for c in copies):
                return True
        return False
    net(a, "sync_tree's copy loop still ASKS the scratch gate before copying",
        the_copy_loop_actually_asks_the_gate,
        "the predicate is pure and will keep answering correctly for ever after the call site "
        "is deleted -- and the failure is silent, because a file quietly not copied looks "
        "exactly like a file that was never copied")


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
               drill_defect_classes, drill_recorders_and_lane, drill_mutation,
               drill_scope, drill_correlation, drill_resonance, drill_threads,
               drill_escalation_behaviour,
               drill_assay_behaviour,
               # LANDED 2026-09-06. Four areas whose subjects had no home in the list above:
               # identity/dashboard's repairs from this shift, `hostcheck.score` and
               # `null_rate` (which nothing in the battery had ever driven), weave's and
               # sweep_plan's unmeasured thresholds, and the one guard between an agent's
               # throwaway script and the public repo. An area added here and nowhere else
               # is an area whose nets never run, which is the quietest way to lose a net.
               drill_identity_dashboard, drill_hostcheck, drill_weave_plan,
               drill_agent_scratch_gate,
               drill_outside):
        # AN AREA THAT DIES IS A BREACH OF THAT AREA, NOT THE END OF THE RUN (order
        # 5c87268a388c, run #37).
        #
        # Several area functions execute statements at call time, OUTSIDE any `net()` wrapper --
        # `SNAP.before('drill', ['config.yaml'])` takes a REAL snapshot and raises SnapshotFailed
        # if `config.yaml` is locked or `state/snapshots` is unwritable; `PL.stamp_record(...)`,
        # a `tempfile.mkdtemp`, an `os.listdir` and, until today, an `open().read()` of another
        # module all sit there too. `net()` catches what happens INSIDE an attack and records it;
        # nothing caught what happened between them. So a locked file anywhere in that set threw
        # an uncaught traceback out of this loop, all 251 verdicts went unreported,
        # `state/drill_last.json` was never written, and `workorders.py` then graded the PREVIOUS
        # run's verdict as current -- which is exactly the failure the "this run's verdict did
        # NOT land" paragraph below was written against, reached by a route that never gets as
        # far as printing it.
        #
        # Recorded rather than swallowed: an area that could not run is an area whose nets
        # nobody has watched, and "absence read as clean" is the shape this whole file exists
        # against. It costs one row, the verdict still lands, and the other thirty areas still
        # report.
        try:
            fn()
        except Exception as e:
            RESULTS.append({"area": "AREA DID NOT RUN — %s" % fn.__name__,
                            "net": "%s completed" % fn.__name__, "held": False,
                            "expected": "an area that cannot run has proved nothing, and its "
                                        "nets must not be counted as held",
                            "error": "%s: %s" % (type(e).__name__, e)})

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
        # A BREACH ALWAYS SAYS SOMETHING ABOUT WHAT WAS EXPECTED, even when nobody wrote one
        # down. This read `if not r["held"] and r["expected"]:`, so a net whose expectation was
        # the empty string printed its name and nothing else -- twenty of them, and an operator
        # reading a 3am breach on "a low-entropy passphrase is not mistaken for a key" got no
        # statement of what should have happened. The omission was invisible at RUNTIME, which is
        # the wrong place for it to be invisible; it is now visible in the output, where a
        # reviewer will fix it. This is the same rule `_a_refusal_names_the_block_it_refused`
        # enforces on the library: a refusal carries the reason a person needs, never a bare
        # False. (Order 6e7ecf6b9fbd.)
        if not r["held"]:
            print("            expected: %s"
                  % (r["expected"] or "(no expectation was recorded for this net)"))

    held = sum(1 for r in RESULTS if r["held"])
    breached = [r for r in RESULTS if not r["held"]]

    # THE SUMMARY LINE IS PRINTED BELOW THIS BLOCK, NOT ABOVE IT, AND THAT ORDER IS THE POINT
    # (order 75c4171c2e93, the VISIBILITY half). The "verdict did not land" warning has always
    # been printed -- and it has always reached nobody. `overnight.safety_drill()` captures this
    # stdout and logs `[x for x in stdout if x.startswith("DRILL:")][-1]`, so the ONLY line of
    # this whole run that a supervisor ever writes down is the summary; a plain `WARNING:` line
    # under it is discarded, and the cycle is logged as a normal inspection while the dashboard
    # and `workorders --sweep` go on grading the PREVIOUS run's `drill_last.json` as current.
    # This file's own words for that are "the green check that never ran, with a longer fuse".
    #
    # So the fact is folded INTO the summary line rather than added as a second one. A second
    # `DRILL:` line would become `line[-1]` and cost the log the counts; it would also add a
    # second mark to the gate signature `mutate.baseline()` builds from these lines, and mutate
    # grades by DIFFERENCE from a baseline. One line, both facts, no new mark, no new exit code.
    #
    # THE EXIT CODE IS STILL 0 IN THIS CASE, AND THAT HALF IS NOT FIXED HERE. `overnight`,
    # `foreman` and `mutate`'s `drill` gate all branch on this rc, `overnight.name_rc` has to
    # name any new one, and mutate's gate has to be checked against it before it is introduced --
    # which is why the order is addressed to RUN and why this shift landed only the half that
    # cannot break a caller.
    #
    # THE VERDICT, ON DISK, WITH A TIME ON IT AND THE CODE IT WAS ABOUT.
    #
    # Two separate faults lived in the four lines this replaces, both filed by the run #34
    # sweep, and both are about a result being believed longer than it is true for.
    #
    # `open(out, "w")` is a TRUNCATE-THEN-FILL, not a write. This file has two live readers --
    # `dashboard.safety()`, which puts it on the page, and `workorders.sweep_detectors()`, which
    # GRADES THE BATTERY from it and closes a DRILL_BREACH order on the strength of it (cited by
    # symbol, not by line, per order 0c7592915a48) -- so a reader
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
    print("\n" + "=" * 96)
    print("DRILL: %d nets attacked, %d held, %d BREACHED%s"
          % (len(RESULTS), held, len(breached),
             "" if landed else " -- AND THIS VERDICT DID NOT LAND in state/drill_last.json"))
    print("=" * 96)

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
            # EVERY ONE OF THEM, NOT FIVE (order 2f679246a6e4). `mutate` reads this
            # stdout to decide whether a mutant was killed, and this is the file that
            # enforces Hard Rule 0 on everybody else.
            print("  " + "; ".join(r["net"] for r in breached))
            return 1
        # A BREACHED NET IS ITSELF AN OWNER-LEVEL EVENT. A safety that does not refuse is worse
        # than an absent one, because the whole system is built assuming it refuses.
        # THE HALT SENTENCE NAMES EVERY BREACHED NET (order 2f679246a6e4). This `what` is
        # what a person reads in HALT.json to rule on whether the library may start again,
        # and it used to name five however many were down -- in the file whose own
        # `drill_no_caps` net enforces Hard Rule 0 on the rest of the library, and whose
        # `_policy_corpus_clean` docstring calls a slice inside a safety net "worse than
        # one in a report". `len(breached)` was in the sentence and `evidence` was already
        # uncapped, so the count was never wrong -- what a reader could not recover from
        # the halt sentence alone was WHICH nets. An escalation `what` is not size
        # constrained, so the slice simply goes.
        ESC.escalate(ESC.OWNER, "DRILL_BREACH",
                     "%d safety net(s) did not hold: %s"
                     % (len(breached), "; ".join(r["net"] for r in breached)),
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
