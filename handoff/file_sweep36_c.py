"""Batch 02's findings: three freshly-converted drill nets that STILL cannot fail.

This is the sharpest result of the run #36 sweep and it deserves its own file.

Earlier the same shift, sixteen drill nets that verified a guard by WHOLE-FILE SUBSTRING SEARCH
were converted to ask the PARSE TREE instead -- a real improvement, and each conversion was
watched refuse a crafted defeat before it was kept. The sweep agent that then audited drill.py
found that three of the converted nets are STILL vacuous, and proved each one by building a
fixture that removes the guard entirely and watching the net report HELD.

The conversion fixed the medium and left the defect: substring-in-file became
node-present-in-tree, and PRESENCE IS NOT REACHABILITY. A name that appears in a dead branch, in
an unrelated sibling function, or in a docstring satisfies "the tree contains this call" exactly
as well as a comment satisfied "the file contains this string".

Two of the three guard things that have already cost this project outages, which is why they are
filed MAJOR rather than as a tidy-up:

  * `publish_asks_before_pushing` is the net standing between a mutation run and a push of
    deliberately-corrupted source to a PUBLIC repo. That push has happened, twice, on
    2026-08-25. The net checks that `import mutate` appears and that "REFUSING TO PUSH" appears
    somewhere inside `push()` -- and `push()` already contains THREE unrelated "REFUSING TO
    PUSH" strings, so deleting the real interlock today would not be caught.
  * `_halt_is_not_breakage` encodes the distinction whose absence caused this project's longest
    outage: a watcher reading jobs-exiting-on-purpose as jobs-crashing. The sweep's fixture
    always declares the library broken and never checks halt status, and the net still reports
    HELD because a dead `if False:` block after a `break` carries the required call, continue
    and string.
"""
import os
import sys

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(HERE, "src"))
import workorders  # noqa: E402

F = []


def add(code, where, what, severity="MAJOR", handler="RUN", evidence=None):
    F.append(dict(code=code, where=where, what=what, severity=severity, handler=handler,
                  evidence=evidence or {}, found_by="sweep36-batch02 (audit of the same "
                                                    "shift's AST conversion)"))


add("NET_MUTATION_NEVER_TOUCHES_LIVE_TREE_CANNOT_FAIL",
    "src/drill.py mutation_never_touches_the_live_tree",
    "PROVEN VACUOUS. The net checks that a `sandbox` def exists, that a 'live_file_untouched' "
    "dict key exists, and that the string 'MUTATE_TOUCHED_LIVE_TREE' appears somewhere in the "
    "module. None of the three is scoped to `run()`, and none is checked for being called or "
    "reachable. The sweep confirmed it by running a crafted `run()` that writes STRAIGHT TO THE "
    "LIVE TREE unsandboxed -- the net still reported HELD. This net is the one that is supposed "
    "to guarantee mutation testing cannot corrupt the real source, which it did, twice, on "
    "2026-08-25. Fix: assert the sandbox path is what `run()` actually mutates through, by "
    "checking reachability from `run()` rather than presence in the file.",
    evidence={"checks": ["a `sandbox` def exists",
                         "a 'live_file_untouched' key exists",
                         "the string MUTATE_TOUCHED_LIVE_TREE appears somewhere"],
              "none_scoped_to": "run()",
              "proof": "a crafted run() writing to the live tree unsandboxed still HELD"})

add("NET_PUBLISH_ASKS_BEFORE_PUSHING_CANNOT_FAIL",
    "src/drill.py publish_asks_before_pushing",
    "PROVEN VACUOUS, AND THIS IS THE ONE THAT MATTERS MOST. The net checks only that `import "
    "mutate` appears and that 'REFUSING TO PUSH' appears somewhere inside `push()`. It never "
    "checks that `_MUT.active()` is CALLED. The sweep confirmed it with a fixture carrying zero "
    "interlock logic, which passed. Worse, and measured: the real `push()` already contains "
    "THREE unrelated 'REFUSING TO PUSH' strings, so deleting the genuine mutation interlock "
    "today would leave this net green. This is the guard between a mutation run and a push of "
    "deliberately-corrupted source to a PUBLIC GitHub repo -- which happened twice on "
    "2026-08-25 and is the incident the whole sandbox rewrite exists because of. Fix: assert a "
    "call to `active()` on the mutate module is reachable from `push()` and that its false "
    "branch raises.",
    evidence={"checks": ["import mutate appears", "'REFUSING TO PUSH' appears inside push()"],
              "never_checks": "_MUT.active() is called",
              "decoys_already_present": "3 unrelated 'REFUSING TO PUSH' strings in push()",
              "proof": "a fixture with zero interlock logic passed",
              "what_it_guards": "a public push of deliberately corrupted source (happened twice)"})

add("NET_HALT_IS_NOT_BREAKAGE_CANNOT_FAIL",
    "src/drill.py _halt_is_not_breakage",
    "PROVEN VACUOUS, and it reproduces the exact outage the net exists to prevent. "
    "`_calls_within` / `_says` / the continue-search all run over the WHOLE `If` node -- body, "
    "orelse and unreachable code alike -- rather than over the reachable halted-arm. The sweep "
    "built a fixture whose real behaviour ALWAYS declares the library 'broken' and never checks "
    "halt status, with a dead `if False:` block after a `break` carrying the required "
    "status-call, continue and string. The net reported HELD. This encodes 'a safety that stops "
    "work is not a fault that stops work', the confusion that caused this project's longest "
    "outage. Fix: walk only the reachable arm, and exclude branches whose test is a constant "
    "false.",
    evidence={"scope_error": "the whole If node including orelse and dead code",
              "should_be": "the reachable halted-arm only",
              "proof": "a fixture that always reports 'broken', with a dead if False: block "
                       "carrying the required tokens, reported HELD",
              "what_it_guards": "the halt-vs-breakage distinction behind the longest outage"})

add("SIXTEEN_AST_NETS_CHECK_PRESENCE_NOT_REACHABILITY",
    "src/drill.py -- all sites tagged 'ASKED OF THE PARSE TREE (run #36)'",
    "THE PATTERN BEHIND THE THREE ORDERS ABOVE, filed separately because the pattern is the "
    "finding. Six further converted nets share the same presence-not-reachability weakness -- "
    "_identity_probe_is_gated, the_keeper_asks_before_restarting, "
    "daemons_actually_check_their_own_source, singleton_guard_is_wired_into_the_daemons, "
    "generator_actually_skips_an_excluded_source, resync_cannot_revert_an_exclusion -- and are "
    "not currently exploitable only because each has exactly ONE real occurrence in the live "
    "tree today. That is a property of today's source, not of the nets, and it expires the "
    "moment somebody writes a second occurrence or a comment. The conversion from substring to "
    "AST was right and is a real improvement; what it did not change is that the question being "
    "asked is 'does this token exist somewhere' rather than 'is this guard reached'. Recommend "
    "a shared helper -- reachable-call-from-function, dead-branch-excluded -- so the sixteen "
    "converted nets ask the second question, and a meta-net asserting no converted net passes "
    "against a fixture with the guard removed.",
    "MAJOR", "RUN",
    evidence={"total_converted_sites": 16,
              "proven_vacuous": 3,
              "same_weakness_not_yet_exploitable": 6,
              "why_not_yet": "each guard has exactly one real occurrence in today's tree"})

add("NO_PROGRAMMATIC_CLEAR_MISSES_A_LOCAL_ALIAS",
    "src/drill.py _no_programmatic_clear",
    "The scan misses a local-variable alias: `f = escalation.clear; f(ruling)` passes it, "
    "confirmed by test. Filed MINOR rather than MAJOR, and deliberately so: the module's own "
    "docstring is explicit that this scan is defence in depth and that the real guarantee is "
    "`escalation.clear()`'s own caller-identity check at run time, which the alias does not "
    "defeat. Worth closing anyway, because a defence-in-depth layer that everyone knows is "
    "porous stops being consulted.",
    "MINOR",
    evidence={"defeat": "f = escalation.clear; f(ruling)",
              "real_guarantee_unaffected": "escalation.clear()'s _by_a_person_at_the_cli check",
              "status": "defence in depth, per the module's own docstring"})

for f in F:
    o = workorders.file_order(**f)
    print("%-12s %-8s %s" % (o["id"], o["severity"], o["code"]))
print("\nfiled %d" % len(F))
