"""
Proposed checks for run35 batch 4 (agent working publish.py / ledger_guard.py / ledger.py /
mutate.py / overwatch.py / secondopinion.py / axis_correlation.py).

These are NOT run standalone against verify_math.py or drill.py -- this run's rule is that
neither is safe to run concurrently with the mutate run already in flight (order c349a51ee2c5),
and the coordinator runs the battery centrally. Every check below WAS smoke-tested standalone,
directly against the real, already-fixed modules in this checkout, with a minimal local `check`/
`net` stub matching verify_math.py's/drill.py's own signatures -- not against synthetic snippets,
except where noted. All passed (HELD / PASS) at the time this file was written.

Local names are suffixed `_b4` to avoid colliding with verify_math.py's own `_NN<letters>` locals
when this is spliced in.
"""

import os as _os_b4
import re as _re_b4
import inspect as _insp_b4
import tempfile as _tmp_b4


# ==================================================================================================
# order a01ab2cf736e -- belongs in verify_math.py, target src/ledger_guard.py.
#
# THE MOST IMPORTANT CHECK IN THIS BATCH. Pins the actual fix: read_chain() must still treat
# FileNotFoundError as "no chain yet" (-> []), and must now RAISE on every other exception
# instead of collapsing it into the same empty list -- the exact confusion that let an
# unreadable ledger chain report "verified". A directory created where the chain file should be
# stands in for permission-denied / held-open / encoding-broken, all of which raise something
# other than FileNotFoundError on `open()`.
# ==================================================================================================
print()
print("[batch4] order a01ab2cf736e -- read_chain() tells 'no chain yet' from 'could not be read'")

def _b4_read_chain_checks():
    import ledger_guard as LG
    orig_chain = LG.CHAIN
    try:
        missing = _os_b4.path.join(_tmp_b4.mkdtemp(), "nope.jsonl")
        LG.CHAIN = missing
        check("read_chain() on a genuinely missing file returns [] (FileNotFoundError stays quiet)",
              LG.read_chain(), [])

        broken_dir = _tmp_b4.mkdtemp()
        broken = _os_b4.path.join(broken_dir, "ledger_chain.jsonl")
        _os_b4.makedirs(broken)   # a directory where the chain file should be
        LG.CHAIN = broken
        raised = False
        try:
            LG.read_chain()
        except FileNotFoundError:
            pass
        except Exception:
            raised = True
        check("read_chain() on an unreadable (non-missing) chain RAISES rather than returning []",
              raised, True,
              note="a directory standing in for permission-denied / held-open / encoding-broken; "
                   "all of them must fail closed, and assert_intact()/verify_chain() make no "
                   "attempt to catch this, so it propagates all the way to publish.push()")
    finally:
        LG.CHAIN = orig_chain

_b4_read_chain_checks()


# ==================================================================================================
# order dec2e6bf4b37 -- belongs in verify_math.py, target src/publish.py.
#
# SKIP_SUFFIX's `.pre*` family is now matched by shape (`_is_skipped`), not by an enumerated
# tuple of names discovered one incident at a time. Proves a suffix nobody has ever written
# still gets skipped, and that an ordinary file is not caught by accident.
# ==================================================================================================
print("[batch4] order dec2e6bf4b37 -- .pre* backups are skipped by SHAPE, not by name")

def _b4_skip_suffix_checks():
    import publish as PUB
    check("publish._is_skipped catches a .pre* suffix not in any historical enumeration",
          PUB._is_skipped("some_module.py.prezzzznotarealone"), True,
          note="the old SKIP_SUFFIX tuple would have missed this -- it only ever grew a new "
               "entry after a suffix had already reached the public repo once")
    check("publish._is_skipped leaves an ordinary source file alone",
          PUB._is_skipped("some_module.py"), False)
    check("publish._is_skipped still catches the non-family suffixes (.bak/.tmp/.orig/.pyc)",
          all(PUB._is_skipped("x" + s) for s in (".bak", ".tmp", ".orig", ".pyc")), True)

_b4_skip_suffix_checks()


# ==================================================================================================
# order 6d7f88ffb76e -- belongs in drill.py, target src/mutate.py.
#
# The corrected sandbox() docstring now names FOUR specific subtrees as live-tree JUNCTIONS
# (portals, not walls): data/, prompts/, reference/, output/index. That is a structural safety
# property, not prose -- a future edit that junctions a FIFTH subtree without re-auditing
# whether any gate command writes there would reopen the exact live-tree-corruption risk this
# order analysed. This net pins the CURRENT junction set so that edit is caught here.
# ==================================================================================================
print("[batch4] order 6d7f88ffb76e -- sandbox() junctions exactly the four known live portals")

def _b4_junction_targets():
    import mutate as AM
    src_txt = _insp_b4.getsource(AM.sandbox)
    names = set()
    m = _re_b4.search(r'for shared in \(([^)]+)\):', src_txt)
    if m:
        names |= {s.strip().strip('"\'') for s in m.group(1).split(",") if s.strip()}
    for m2 in _re_b4.finditer(r'_junction\(os\.path\.join\(root,((?:\s*,?\s*"[^"]+")+)\)', src_txt):
        parts = _re_b4.findall(r'"([^"]+)"', m2.group(1))
        names.add("/".join(parts))
    return names

net("MUTATE SANDBOX", "sandbox() junctions exactly the four known live-tree portals",
    lambda: _b4_junction_targets() == {"data", "prompts", "reference", "output/index"},
    "a fifth or sixth junction was added without re-checking whether GATES/FAST_GATES write "
    "there -- re-read order 6d7f88ffb76e's analysis before trusting the sandbox again")


# ==================================================================================================
# order adba96551729 -- belongs in verify_math.py, target src/mutate.py.
#
# Regression pin for the corrected verify_restore() docstring: its one call site must remain the
# THROWAWAY sandbox copy (`os.path.join(root, "src", target)`), never SRC/the live file. If a
# future edit adds a second caller against a live path, the corrected claim (this function
# protects a sandbox copy, not the three ledgers) becomes false again exactly as it was found.
# ==================================================================================================
print("[batch4] order adba96551729 -- verify_restore()'s only caller is still the sandbox copy")

def _b4_verify_restore_checks():
    import mutate as AM
    lines = _insp_b4.getsource(AM).splitlines()
    call_idxs = [i for i, l in enumerate(lines)
                 if "verify_restore(path)" in l and not l.strip().startswith("def ")]
    check("mutate.verify_restore has exactly one CALL site", len(call_idxs), 1)
    if call_idxs:
        i = call_idxs[0]
        assign = next((l for l in reversed(lines[:i]) if l.strip().startswith("path = ")), "")
        check("that call site's `path` is built from the sandbox root, not SRC",
              'os.path.join(root, "src", target)' in assign, True)

_b4_verify_restore_checks()


# ==================================================================================================
# order a3ee0d1d2d4c -- belongs in verify_math.py, target src/overwatch.py.
#
# review() now returns (findings, complete); round_once only stamps led["seen"][module] when
# complete is True. Proves both halves directly: force every _ask call to return None (the
# GPU-busy / cloud-budget-spent case) and confirm review() reports complete=False rather than
# looking identical to a module that was read and found clean.
# ==================================================================================================
print("[batch4] order a3ee0d1d2d4c -- a skipped review no longer looks like a clean one")

def _b4_overwatch_checks():
    import overwatch as OW
    orig_ask, orig_slices = OW._ask, OW._slices
    try:
        OW._ask = lambda *a, **k: None
        OW._slices = lambda path: [(1, 1, "x = 1\n")]
        found, complete = OW.review("overwatch", local=True)
        check("overwatch.review() reports complete=False when every _ask call is skipped",
              complete, False)
        check("overwatch.review() still returns [] findings on a fully-skipped module",
              found, [])
    finally:
        OW._ask, OW._slices = orig_ask, orig_slices

_b4_overwatch_checks()


# ==================================================================================================
# order 12694407d245 -- belongs in verify_math.py, target src/secondopinion.py.
#
# _ruff/_vulture/_detect_secrets now read r.returncode and report a distinct "TOOL ERROR" status
# instead of "RAN" when the tool never actually answered. Forces ruff into its documented
# CLI-misuse exit code (rc=2, bad --select, empty stdout) and vulture into its "path not found"
# case (rc=1, output that fails to parse as any real finding) and confirms neither reports RAN.
#
# ENVIRONMENT-DEPENDENT: skips (rather than failing) if ruff/vulture are not installed in the
# interpreter's Scripts directory on the machine running this -- matches this module's own
# "NOT INSTALLED is not a failure" doctrine. Confirmed RAN against the real installed tools in
# this checkout on 2026-08-27.
# ==================================================================================================
print("[batch4] order 12694407d245 -- an installed-but-failing tool no longer reports RAN")

def _b4_secondopinion_checks():
    import secondopinion as SO
    scripts = _os_b4.path.join(_os_b4.path.dirname(SO.sys.executable), "Scripts")
    ruff_exe = _os_b4.path.join(scripts, "ruff.exe")
    vulture_exe = _os_b4.path.join(scripts, "vulture.exe")
    if not (_os_b4.path.exists(ruff_exe) and _os_b4.path.exists(vulture_exe)):
        print("   (skipped -- ruff/vulture not found at %s)" % scripts)
        return
    orig_exe, orig_rules = SO._exe, SO.RUFF_RULES
    try:
        SO._exe = lambda name: _os_b4.path.join(scripts, name + ".exe")
        SO.RUFF_RULES = "ZZZ999"    # a selector ruff refuses -> documented rc=2, empty stdout
        status, _ = SO._ruff([_os_b4.path.join(SO.SRC, "ledger_guard.py")])
        check("ruff runner reports a tool error (not RAN) on a bad --select",
              status.startswith("RAN"), False)

        status2, _ = SO._vulture([_os_b4.path.join(SO.SRC, "definitely_missing_module_xyz.py")])
        check("vulture runner reports a tool error (not RAN) on an unreadable path",
              status2.startswith("RAN"), False)
    finally:
        SO._exe, SO.RUFF_RULES = orig_exe, orig_rules

_b4_secondopinion_checks()


# ==================================================================================================
# order 1b29e38dbb17 -- belongs in verify_math.py, target src/axis_correlation.py + src/assay.py.
#
# LEFT FOR OWNER (see AUDIT_batch4.md) -- the fallback VALUE (0.0 on a missing/unreadable matrix)
# is an already-ruled owner decision (order c00cab9d0412), not this order's bug. What this order
# actually found is that axis_correlation.rho()'s bare fallback and assay._rho_doc's wrapped one
# are now two INDEPENDENT implementations of that one ruling. Nothing pinned that they agree;
# this does, so a future edit to one without the other is caught here instead of surfacing as two
# published numbers disagreeing about the identical situation.
# ==================================================================================================
print("[batch4] order 1b29e38dbb17 -- the two independent missing-matrix fallbacks still agree")

def _b4_axis_correlation_checks():
    import axis_correlation as AC
    import assay as A
    orig_load = AC.load
    orig_cache = A._RHO_CACHE[0]
    orig_reason = A.RHO_FALLBACK_REASON
    try:
        AC.load = lambda: None      # simulate "matrix missing, unreadable, or carrying no pairs"
        A._RHO_CACHE[0] = None
        check("axis_correlation.rho() and assay._rho() agree on the missing-matrix fallback",
              AC.rho("reach", "ruin"), A._rho("reach", "ruin"),
              note="both must currently read 0.0 -- a mismatch means one side's fallback moved "
                   "without the other's, re-opening order c00cab9d0412 by accident")
    finally:
        AC.load = orig_load
        A._RHO_CACHE[0] = orig_cache
        A.RHO_FALLBACK_REASON = orig_reason

_b4_axis_correlation_checks()
