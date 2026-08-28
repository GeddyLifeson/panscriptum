"""Second tranche of run #36 sweep findings (batches 08 and onward), filed as work orders."""
import os
import sys

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(HERE, "src"))
import workorders  # noqa: E402

F = []


def add(code, where, what, severity="MINOR", handler="RUN", batch="", evidence=None):
    F.append(dict(code=code, where=where, what=what, severity=severity, handler=handler,
                  evidence=evidence or {}, found_by="sweep36-%s" % batch))


add("MAGNITUDE_DOER_GUARD_NOT_ON_THE_DEFAULT_PATH", "src/magnitude.py _split_gate()",
    "GUARD 3 -- 'the entity must be the DOER' -- IS A SAFETY IN A FILE AND NOT A SAFETY IN "
    "EFFECT, and this is a sharper statement of open order e9ff72c7eb48 rather than a repeat of "
    "it. The guard genuinely CAN refuse: the sweep drove all four documented shapes against "
    "subject_refusal() live and each was rejected. But it is only reached from the one-shot "
    "verify() path. _split_gate(), which is the DEFAULT grading path and therefore the one that "
    "handles the heaviest and best-documented entities, never calls subject_refusal at all. "
    "Demonstrated: a real bystander sentence -- 'Beerus erased the universe...' -- mines cleanly "
    "into GOKU's own candidate list through feats.by_axis, with nothing to say the entity being "
    "scored is not the one doing the thing. That is an attribution error feeding a published "
    "Magnitude, which is the single most expensive class of wrong answer this library can "
    "produce. The fix is wiring, not logic: the guard already works.",
    "MAJOR", batch="batch08",
    evidence={"anchor": "def _split_gate(got, cand):  -- no subject_refusal call anywhere in it",
              "guard_verified_working": "all 4 documented shapes refused when driven directly",
              "demonstration": "'Beerus erased the universe...' enters Goku's candidate list",
              "sharpens": "e9ff72c7eb48"})

add("SECONDOPINION_WAIVER_COMMENT_ARITHMETIC_WRONG", "src/secondopinion.py NOT_FILED comment",
    "The comment justifying the NOT_FILED waivers states its own arithmetic wrongly: it claims "
    "'531 BLE001 + 63 S110/S112 sites out of 1,002 live findings ... 96%', but 594/1002 is about "
    "59 per cent, not 96. Measured live this shift: 401 of 1,014 findings are waived (39.5%), "
    "and BLE001/S110/S112 are NOT among them -- they remain filed, as intended. So the waiver "
    "policy is behaving correctly and the sentence defending it is wrong, which matters because "
    "this is the module that exists to be the library's one INDEPENDENT opinion: a reader "
    "checking whether the outside tools are being muffled is reading a number that does not "
    "support the conclusion drawn from it.",
    "MINOR", batch="batch08",
    evidence={"claimed": "96%", "actual": "594/1002 = 59%",
              "measured_waived": "401 of 1014 (39.5%)",
              "BLE001_S110_S112": "filed, not waived"})

add("SECONDOPINION_SIM115_WAIVER_REASON_DOES_NOT_MATCH_ITS_SITES",
    "src/secondopinion.py NOT_FILED['SIM115']",
    "The SIM115 waiver's written reason is 'a handle outlives one block', but the sampled sites "
    "are mostly single-expression open(...).read() idioms, where the handle does not outlive "
    "anything. A waiver with a reason that does not describe what it waives is a waiver nobody "
    "can review -- and every NOT_FILED entry in this module is required to carry a written "
    "reason precisely so that it CAN be reviewed. 183 findings sit behind this one sentence.",
    "MINOR", batch="batch08",
    evidence={"stated_reason": "a handle outlives one block",
              "sampled_sites": "single-expression open(...).read()",
              "count_behind_the_waiver": 183})

add("PICK_MODEL_RESIDENT_AND_FIT_NOTE_USE_DIFFERENT_VRAM_BUDGETS",
    "src/pick_model.py resident() vs fit_note()",
    "resident()'s REFUSED gate measures against TOTAL VRAM budget while fit_note() measures "
    "against FREE VRAM, so a model resident() calls usable can still have fit_note() print "
    "'WILL OFFLOAD'. Reported as a QUESTION rather than a defect: on a shared GPU the two "
    "questions ('does this fit the card' and 'does this fit right now') are genuinely different "
    "and a caller may want both. What is not defensible is that neither function says which one "
    "it is answering. An owner ruling, or one sentence in each docstring, closes it.",
    "MINOR", "OWNER", batch="batch08",
    evidence={"resident": "total VRAM budget", "fit_note": "free VRAM",
              "consequence": "'usable' and 'WILL OFFLOAD' can both be true at once"})

# ---------------------------------------------------------------- batch 16
add("PUBLISH_WRITE_FIXED_TMP_NAME", "src/publish.py write()",
    "write()'s temp file has a FIXED, non-unique name (STATE_JSON + '.tmp') shared by two "
    "processes this module itself permits to run at once -- the --push --loop daemon and a "
    "manual one-shot. Two writers collide on the scratch file, the second truncates the first, "
    "and whichever renames second can land a partial file. This is the same collision that "
    "runguard._land, binding_health._land, suppressions._land and health.py were all repaired "
    "for during this shift, remaining in the module that publishes to a PUBLIC repo.",
    "MAJOR", batch="batch16",
    evidence={"anchor": "tmp = STATE_JSON + '.tmp'",
              "concurrent_writers_permitted_by_this_module": ["--push --loop daemon",
                                                              "manual one-shot"]})

add("PRUNE_EXPORT_SITE_GUARD_USES_UNRESOLVED_PATHS",
    "src/publish.py prune_export SITE == HERE guard",
    "The guard that stops the new delete path running against the live tree compares "
    "os.path.abspath(SITE) with os.path.abspath(HERE), which does NOT resolve symlinks, "
    "junctions or case variants. On this machine junctions are used deliberately (mutate.py "
    "junctions four directories into its sandbox), so a junctioned or case-variant SITE would "
    "read as a different directory and let the prune proceed against the live project. No live "
    "trigger found -- latent. os.path.realpath with a casefold comparison closes it.",
    "MINOR", batch="batch16",
    evidence={"anchor": "if os.path.abspath(SITE) == os.path.abspath(HERE): return 0",
              "not_resolved": ["symlinks", "directory junctions", "case variants"],
              "live_trigger": "none found"})

add("AXIS_CORRELATION_WRITE_DISCARDS_ITS_VERDICT", "src/axis_correlation.py write()",
    "write() discards silence.write_json's return value and then prints 'wrote ...', so a "
    "denied rename to AXIS_CORRELATION.json is reported as a success. That file holds the "
    "covariance matrix that sits inside every published +/- in the library, so a silently "
    "stale one means every error bar afterwards is computed from a matrix nobody knows did not "
    "update. Sibling module zfighters.py was fixed for this exact helper in the same batch.",
    "MAJOR", batch="batch16",
    evidence={"anchor": "silence.write_json(OUT, doc, indent=2, sort_keys=True)  -- unchecked",
              "consequence": "every published error bar rests on this file"})

add("WITHDRAW_CHAPTERS_SECOND_DISCARDED_VERDICT",
    "src/withdraw_chapters.py catalog.withdrawn.json",
    "A second discarded write_json verdict, on the supplementary catalog.withdrawn.json archive "
    "record. The operational CATALOG write beside it IS correctly checked, which is what makes "
    "this worth filing: the two sit together and only one was repaired, so the next reader will "
    "reasonably assume both were.",
    batch="batch16",
    evidence={"checked_sibling": "the operational CATALOG write", "unchecked": "catalog.withdrawn.json"})

add("ESTATE_CHARTER_EXAMPLE_LIST_CAPPED", "src/estate.py charter()",
    "charter()'s 'no charter spine code' finding caps its illustrative example list at four "
    "names (un[:4]) while the reported COUNT stays full. Filed because it is literally the [:N] "
    "shape Hard Rule 0 names, and because the same question -- does the rule reach announced "
    "console illustration, or only pipeline-consumed rosters -- arose independently in five "
    "batches this sweep. One owner ruling settles all of them.",
    "MINOR", "OWNER", batch="batch16",
    evidence={"anchor": "un[:4]", "count_reported_in_full": True,
              "same_question_raised_by_batches": ["07", "08", "10", "15", "16"]})

# ---------------------------------------------------------------- batch 04
add("SCOPE_STALE_INVENTED_CEILINGS_CANNOT_BE_REPROBED", "data/SCOPE.json + src/scope.py build()",
    "THE CODE WAS FIXED TODAY AND THE BAD DATA IT PRODUCED IS UNREACHABLE BY THE FIX. scope_for "
    "now returns None below the evidence floor instead of inventing a ceiling (order "
    "09d47bc950d9, closed this shift). But 28 of 155 hosts in data/SCOPE.json still hold "
    "ceilings invented BEFORE that fix -- confirmed live on disk, including M7 on TWO mentions "
    "against MIN_MENTIONS=10 (root.fandom.com, rosariovampire.fandom.com among them) -- and "
    "build()'s 'h not in out' skip means those rows can NEVER be re-probed. magnitude."
    "host_ceiling() reads them straight off disk as authoritative CLAMPS, so they are actively "
    "constraining published Magnitudes right now. This is the same shape as the "
    "catalogue_aurora records: a repaired parser beside unrepaired output. Re-deriving 28 "
    "ceilings is mechanical once someone decides it is wanted, but purging rows from SCOPE.json "
    "changes published numbers, so the decision is filed rather than taken.",
    "MAJOR", "OWNER", batch="batch04",
    evidence={"stale_rows": "28 of 155", "floor": "MIN_MENTIONS=10",
              "worst_seen": "M7 on 2 mentions",
              "named": ["root.fandom.com", "rosariovampire.fandom.com"],
              "why_unreachable": "build()'s `h not in out` skip never revisits an existing row",
              "consumer": "magnitude.host_ceiling() clamps published Magnitudes with them",
              "code_fix_closed_this_shift": "09d47bc950d9"})

add("STANDARDS_JOB_PROGRESS_FIXED_TMP_NAME", "src/standards.py job_progress.json write",
    "state/job_progress.json is written through a fixed path + '.tmp' name from two independent "
    "long-lived processes -- dashboard.py polling and publish.py --loop -- rather than through "
    "silence.write_json's pid-qualified pattern. Same two-writers-one-scratch-file collision "
    "repaired in four other modules during this shift.",
    "MAJOR", batch="batch04",
    evidence={"anchor": "tmp = JOB_WATCH + '.tmp'  then  silence.replace_retry(tmp, JOB_WATCH)",
              "concurrent_readers_writers": ["dashboard.py", "publish.py --loop"]})

add("STANDARDS_STALE_NOTE_TAGS", "src/standards.py silence.note tags",
    "Two silence.note line tags no longer point at their own lines: 'standards.py:370' is on "
    "line 991 and 'standards.py:449' is on 1073 -- drifted by six hundred lines, so tracing a "
    "swallowed failure by either tag lands nowhere near it.",
    batch="batch04",
    evidence={"tags": {"standards.py:370": 991, "standards.py:449": 1073}})

add("CATALOGUE_WEB_SAVE_ROLL_DISCARDS_AND_HIDES_ITS_VERDICT", "src/catalogue_web.py save_roll()",
    "save_roll() discards its write verdict AND does not return it, so no caller can check "
    "either -- while the write_record_catalogue call three lines above it IS checked. The two "
    "sit together, which makes the unchecked one read as deliberate.",
    batch="batch04",
    evidence={"anchor": "_sil.replace_retry(tmp, ROLL)  -- result neither tested nor returned",
              "checked_neighbour": "write_record_catalogue, three lines above"})

add("TIERS_AND_PANTHEON_DISCARD_WRITE_VERDICTS", "src/tiers.py main() / src/pantheon.py",
    "Both discard silence.write_json's return and print an unconditional success line. Same "
    "family as the ten modules repaired this shift; these two were outside that agent's "
    "ownership. scope.py in the same batch is the positive example to copy.",
    batch="batch04",
    evidence={"tiers": "silence.write_json(out, charted, ...) then unconditional 'wrote {out}'",
              "pantheon": "silence.write_json(OUT, out, indent=1, ensure_ascii=False)",
              "good_example": "scope.py build()/main()"})

add("PANTHEON_BAND_LABELS_MISSING_THREE_MAGNITUDES", "src/pantheon.py label table",
    "The magnitude-band label table omits M1, M5 and M6. Dormant today because Z_FIGHTERS.json "
    "only holds M2-M4 and M7, which is exactly why it will surface as a silent blank the first "
    "time an entity lands in one of the three missing bands.",
    batch="batch04",
    evidence={"missing": ["M1", "M5", "M6"], "present": ["M2", "M3", "M4", "M7", "M8"],
              "why_dormant": "Z_FIGHTERS.json currently uses none of the missing bands"})

for f in F:
    o = workorders.file_order(**f)
    print("%-12s %-8s %s" % (o["id"], o["severity"], o["code"]))
print("\nfiled %d" % len(F))
