"""Batch 13's findings, plus the 46 discarded-verdict sites left outside the repaired ten."""
import os
import sys

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(HERE, "src"))
import workorders  # noqa: E402

F = []


def add(code, where, what, severity="MAJOR", handler="RUN", found_by="", evidence=None):
    F.append(dict(code=code, where=where, what=what, severity=severity, handler=handler,
                  evidence=evidence or {}, found_by=found_by))


add("ESCALATION_READ_STOPPED_FAILS_OPEN", "src/escalation.py _read_stopped()",
    "A FAIL-OPEN IN THE CHAIN OF COMMAND ITSELF, reproduced live. `_read_stopped()` ends with "
    "`return d if isinstance(d, dict) else {}`, so a state/STOPPED.json that is valid JSON but "
    "not a dict -- a list, a string, a number -- silently becomes an empty mapping instead of "
    "the `__unreadable__` sentinel the rest of the module expects. `subsystem_stopped()` then "
    "reports NOT STOPPED for every subsystem. The file's own docstring promises the opposite in "
    "capitals: 'UNREADABLE MEANS STOPPED, for everything.' This is the module whose three "
    "required properties are INDEPENDENT, FAIL CLOSED and PROVEN, and this path fails open in "
    "the one direction that matters: a MANAGER-level stop silently not being in force.",
    found_by="sweep36-batch13",
    evidence={"anchor": "return d if isinstance(d, dict) else {}",
              "trigger": "valid JSON that is not an object",
              "promise_broken": "UNREADABLE MEANS STOPPED, for everything",
              "reproduced": "live"})

add("ESCALATION_NON_DICT_HALT_CRASHES_INSTEAD_OF_FAILING_CLOSED",
    "src/escalation.py _read_halt_raw() / status()",
    "A valid-but-non-dict state/HALT.json raises AttributeError rather than the documented "
    "fail-closed SystemHalted, because the `except Exception` wraps only the `json.load` and "
    "not the attribute access after it. Reproduced live. No current caller fails OPEN on it -- "
    "they all crash to a stop or catch broadly -- so the effect today is a confusing traceback "
    "rather than an unsafe pass. The exception is verify_math.py's narrow `except SystemHalted:` "
    "probe, which would itself crash uncaught under this input, i.e. the battery check about "
    "the halt would die rather than report.",
    "MINOR", found_by="sweep36-batch13",
    evidence={"raised": "AttributeError", "documented": "SystemHalted",
              "reproduced": "live",
              "affected_check": "verify_math.py narrow `except SystemHalted:` probe"})

add("ONOMAST_RESERVED_NAMES_SURVIVE_ONLY_ONE_CYCLE",
    "src/onomast.py name_worlds() vs main()",
    "The `taken`-seeding protection in `name_worlds()` exists to stop a dropped world's "
    "catalogue_name being reissued to a different world while older prose still cites it -- and "
    "it survives exactly ONE generation cycle. `main()` writes ONOMASTICON.json with only the "
    "current run's `named` dict, so any cid no longer in `resolved` is dropped from the file, "
    "the next run cannot see it, and the name becomes free again. Reproduced end to end with a "
    "three-run simulation. The guard is real and its memory is erased by the writer beneath it: "
    "a safety that holds for one cycle and then forgets is worse than none, because the ledger "
    "still shows it working.",
    found_by="sweep36-batch13",
    evidence={"guard": "name_worlds() seeds `taken` from prior names",
              "eraser": "main() writes only the current run's `named` dict",
              "proof": "3-run simulation reissued a retired name"})

add("BINDING_HEALTH_WRITE_FAILURES_NOT_ESCALATED",
    "src/binding_health.py BINDING_HEALTH.json writes",
    "Failed writes to BINDING_HEALTH.json are not escalated through the chain, while failed "
    "writes to HOST_QUARANTINE.json in the same module ARE. Filed as a QUESTION: the asymmetry "
    "may be deliberate (a quarantine is an action, a health report is an observation), but "
    "nothing in the module says so, and an unexplained asymmetry between two writes in one file "
    "is how the next editor picks the wrong one to copy.",
    "MINOR", "OWNER", found_by="sweep36-batch13",
    evidence={"escalated": "HOST_QUARANTINE.json", "not_escalated": "BINDING_HEALTH.json"})

add("FORTY_SIX_MORE_DISCARDED_WRITE_VERDICTS",
    "src/ -- 46 sites across 30 files (table in handoff/nets/run36_discarded_verdicts.md)",
    "The systemic discarded-write-verdict pass repaired 13 sites across the ten modules it "
    "owned; a full AST walk found 46 MORE across 30 files that were outside that ownership. "
    "Named as notable by the agent: weave_index.py:335/337 reads the very artifacts weave.py "
    "writes, so BOTH halves of that join were discarding verdicts; overwatch.py:168 is a "
    "LEDGER -> LEDGER.corrupt quarantine move that health.py gates correctly in its own copy of "
    "the same code; pipeline.py:212 writes STATE under a comment reading 'readers poll this "
    "file'; plus generate.py:58, standards.py:1305, health.py:680. THE SHAPE IS STILL BEING "
    "INTRODUCED, not merely left over: hostcheck.py went from 1 site to 5 DURING this shift "
    "when another agent refactored its writes behind a local _land() helper, and all five "
    "discard the verdict. A staged drill net that finds the shape generally (AST, wrapper-aware, "
    "allowlist keyed by file+callee+first-arg rather than line number) is in "
    "handoff/nets/run36_discarded_verdicts.md. IT STARTS RED AT 46, deliberately, and the "
    "document lays out three merge options with the count-ratchet's weakness named. Re-measure "
    "before merging: the count moved five times during this run (57 -> 44 -> 43 -> 47 -> 46) "
    "purely from concurrent edits.",
    found_by="run36 systemic discarded-verdict pass",
    evidence={"repaired": "13 sites / 10 modules",
              "remaining": "46 sites / 30 files",
              "still_being_introduced": "hostcheck.py went 1 -> 5 sites mid-shift",
              "net_status_on_merge": "RED at 46",
              "count_volatility": [57, 44, 43, 47, 46],
              "net_doc": "handoff/nets/run36_discarded_verdicts.md"})

for f in F:
    o = workorders.file_order(**f)
    print("%-12s %-8s %s" % (o["id"], o["severity"], o["code"]))
print("\nfiled %d" % len(F))
