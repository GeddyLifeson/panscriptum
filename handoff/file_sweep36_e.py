"""Batch 06's findings."""
import os
import sys

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(HERE, "src"))
import workorders  # noqa: E402

F = []


def add(code, where, what, severity="MAJOR", handler="RUN", evidence=None):
    F.append(dict(code=code, where=where, what=what, severity=severity, handler=handler,
                  evidence=evidence or {}, found_by="sweep36-batch06"))


add("RESYNC_ROLL_CANNOT_SEE_A_RECORD_WITH_NO_ROLL_ROW",
    "src/resync_roll.py + data/SWEEP_ROLL.json",
    "A record file with NO matching roll row at all is invisible to the resync, so the one "
    "mechanism meant to reconcile the roll against the records cannot report the worst kind of "
    "disagreement -- a source that exists only on one side. Confirmed against live data: "
    "data/records/bone-jeff-smith.json holds 86 CATALOGUED ENTRIES and has no row anywhere in "
    "the 215-row SWEEP_ROLL.json, which very likely makes those 86 entries invisible to "
    "downstream generation gating. The resync compares row-by-row from the roll's side, so "
    "anything absent from the roll is absent from the comparison: a check that cannot see the "
    "case it exists for. NOTE for whoever works this: SWEEP_ROLL.json was destroyed twice on "
    "2026-08-26 and reconstructed, so an absent row may be a casualty of that incident rather "
    "than a source that was never rolled -- establish which before adding anything, and note "
    "the roll is now covered by canon_backup so a future reconstruction has a real reference.",
    evidence={"orphan_record": "data/records/bone-jeff-smith.json",
              "entries_at_risk": 86,
              "roll_rows": 215,
              "direction_of_the_blindness": "the resync iterates the roll, not the records",
              "related_incident": "SWEEP_ROLL.json destroyed twice, 2026-08-26"})

add("CODEWATCH_RESTART_BUDGET_DEFEATED_BY_A_DENIED_WRITE",
    "src/codewatch.py _take_locked",
    "_take_locked discards silence.write_json's return value and returns granted regardless, so "
    "a persistently DENIED ledger write -- the ordinary Windows PermissionError case this "
    "project has hit repeatedly -- silently defeats BUDGET_PER_HOUR. That budget is the "
    "restart-storm safety: it exists so a daemon that keeps exiting cannot be restarted forever. "
    "With the write denied, every claim is granted, nothing is ever recorded as used, and the "
    "budget can never be reached. A safety whose accounting can fail silently is not a budget, "
    "it is a formality -- and the failure mode is a machine-wide restart storm, which is exactly "
    "what it was written to prevent.",
    evidence={"anchor": "silence.write_json(LEDGER, doc, indent=2) then return True, used_before",
              "safety_defeated": "BUDGET_PER_HOUR restart-storm limit",
              "trigger": "a persistently denied atomic rename (routine on Windows here)"})

add("SWEEP_FUNNEL_STAGES_ARE_NOT_MONOTONIC",
    "src/sweep.py funnel report",
    "The funnel's 'each stage is strictly smaller' claim is FALSE against live data: "
    "catalogued=44,185 while addressed=144,452 and reachable=144,487, which prints a garbled "
    "'--100,267' artifact and renders a visually near-100% funnel immediately after a 30% gate. "
    "Confirmed against data/CHARACTER_SWEEP.json. Two different populations are being compared "
    "as if they were nested subsets of one another, so the picture a reader takes away is not "
    "merely imprecise, it is inverted -- the stage that lost the most looks like the stage that "
    "lost nothing.",
    evidence={"catalogued": 44185, "addressed": 144452, "reachable": 144487,
              "artifact": "--100,267", "source": "data/CHARACTER_SWEEP.json"})

add("STYLE_AUDIT_TURN_ENDING_MATCHES_ANY_LINE_BREAK",
    "src/style_audit.py TURN_ENDING",
    "TURN_ENDING combines re.M with '$', so it matches at ANY line break rather than at the end "
    "of an entry, and the reported 'ending on a turn' rate is inflated by every mid-entry "
    "paragraph break. Confirmed by direct test. This is a prose-quality measure, so an inflated "
    "rate makes the style gate look stricter than it is and would be read as evidence the voice "
    "is being controlled. Minor and separate: the character class [<two identical codepoints>] "
    "lists the same codepoint twice, harmless.",
    evidence={"anchor": "TURN_ENDING with re.M and $",
              "effect": "matches at any line break, not entry end",
              "confirmed": "direct test"})

add("FEATS_A_FAILED_FIRST_CONTINUATION_READS_AS_ZERO_RESULTS",
    "src/feats.py _api_list_all",
    "_api_list_all does not count or flag a continuation walk whose VERY FIRST request fails: "
    "rows stay empty and the entity's discovery is then indistinguishable from a genuine zero "
    "result, while the 'discovery lists: complete' banner still prints. This is a new edge in "
    "code that landed today to REMOVE a truncation (551 titles became 1,331), so it is a good "
    "fix with an honest gap rather than a regression -- but a transport failure reading as "
    "'this entity has no pages' is the same smaller-universe shape Hard Rule 0 is about, "
    "arriving through the error path instead of through a cap.",
    evidence={"anchor": "the `if not d:` / `if rows:` guard in _api_list_all",
              "banner_still_printed": "discovery lists: complete",
              "context": "the module gained full continuation-following today"})

add("LIVENESS_DEAD_METHOD_RESOLVES_BY_BARE_NAME",
    "src/liveness.py DEAD detector (methods)",
    "The DEAD-for-methods widening added today resolves by BARE NAME globally rather than per "
    "class, so a dead method sharing a name with any attribute access anywhere in the tree can "
    "never be flagged. Measured: zero collisions among the nine non-dunder methods currently in "
    "scope, so there is no live impact -- which is precisely why it is worth filing now, while "
    "it is cheap. Same batch, same shape: the PHANTOM widening still does not cover match/case "
    "guards or bare `cond and action()` statements (also measured at zero instances today).",
    "MINOR",
    evidence={"resolution": "bare name, global", "should_be": "per class",
              "current_collisions": 0, "non_dunder_methods_in_scope": 9,
              "phantom_gaps": ["match/case guards", "bare `cond and action()` statements"]})

for f in F:
    o = workorders.file_order(**f)
    print("%-12s %-8s %s" % (o["id"], o["severity"], o["code"]))
print("\nfiled %d" % len(F))
