"""Close 3c7c8a6e9102 -- the project's standing BLOCKING bug -- with the restore verified.

It had been open since 2026-08-25. Thirty-one records carried a null synthesis block: 191,029
catalogued entries with no ceiling and no band, Marvel (59,170) and DC (55,560) among them, and
they did not self-heal because `phase_synthesis` skips any source already in its done-keys.
"""
import os
import sys

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(HERE, "src"))
import workorders  # noqa: E402

HOW = (
    "RESTORED AND VERIFIED. 27 synthesis blocks re-derived and merged; records carrying a "
    "synthesis went 185 -> 212. The only four still null hold ZERO entries and are the four "
    "sources the owner excluded on 2026-08-20 as having no verifiable wiki source -- there is "
    "nothing to synthesise from, so null is the correct state for them. "
    "WHAT IT TOOK, in three parts. (1) THE RESCUE TOOL COULD NOT SEE THE CASUALTIES: "
    "retry_synthesis selected on the CAUSE, reading the pipeline's failed-set, which held TWO "
    "names. Twenty-nine of the thirty-one never failed anything -- they were clobbered -- so a "
    "tool whose whole job is 'sources the pipeline will never revisit' could see 2 of the 31 "
    "that qualified. It now also selects on the CONDITION (stranded_sources: no synthesis, and "
    "entries to reason over). (2) IT ASKED THE WRONG MODEL: it called PL.ask (Ollama only) while "
    "phase_synthesis, whose prompt construction it deliberately shares so the two cannot drift, "
    "calls PL.ask_pool_first. Now both go pool-first. (3) THE LOCAL RUNG WAS DEAD FOR A REASON "
    "NOBODY HAD FOUND: OLLAMA_NUM_PARALLEL was set to 3 at user scope, and Ollama divides a "
    "model's context across parallel slots -- 12288/3 = 4096, which is the context_length every "
    "diagnosis had been staring at for three runs and blaming on a client. No client asked for "
    "4096; the server was dividing. Set to 1 and restarted: a request at num_ctx=12288 that had "
    "timed out at 90s for 31 hours returned in 9 SECONDS. Previous value and revert command in "
    "state/run36b_env_before.json. "
    "THE RESTORE ITSELF: 27 of 28 on the first pass (3 lost to WinError 10048/10055 ephemeral "
    "port exhaustion, which this run's own connection rate caused and which cleared on its own "
    "-- 2 of those 3 succeeded on retry); the 28th, Bone (Jeff Smith), needed nothing because "
    "its record already carried a synthesis and its entry in the failed-set is stale. Merged "
    "with the pipeline stopped, as the tool requires. "
    "VERIFIED AGAINST A SNAPSHOT TAKEN IMMEDIATELY BEFORE THE MERGE, because this order is about "
    "a writer clobbering things and 'the merge said it worked' is not evidence: all 216 record "
    "files re-read and compared -- 0 entries lost, 0 top-level keys nulled, 0 files missing. "
    "Marvel still holds 59,170 entries and now names Franklin Richards at M10. "
    "Sample of what was recovered: Marvel M10 Franklin Richards, DC M10 Star Conqueror, Dragon "
    "Ball Z M10 Shabbet, Transformers M10 Elephorca, Digimon M10 Tooru, Mario M10 Megabug, "
    "Naruto M9 Kaguya Otsutsuki, Adventure Time M9 The Glitch, Invincible M9 Stripevincible, "
    "He-Man M9 Nepthu, Rick and Morty M8 Universe Bomb, Gundam M7 ELS, Zelda M7 Triforce, "
    "Soul Calibur M6 KOS-MOS, and four honest 'unassayed' where the source genuinely shows no "
    "quantified feat (Chowder, Ghost Recon, Baki, Terminator) -- the 'no feat, no band' "
    "invariant working rather than failing. "
    "STILL OPEN AND FILED SEPARATELY: the CAUSE of the clobbering is fixed in both writers "
    "(write_record_catalogue on 2026-08-25, write_record on 2026-08-27, both now treating an "
    "absent or None key as unauthored rather than as an instruction to erase), so this should "
    "not recur -- but nothing yet re-derives a synthesis automatically if it ever does, and "
    "phase_synthesis still skips anything in its done-keys."
)


def main():
    workorders.resolve("3c7c8a6e9102", how=HOW)
    print("closed 3c7c8a6e9102 -- the standing BLOCKING order")
    o = workorders.file_order(
        code="NOTHING_AUTOMATICALLY_REDERIVES_A_LOST_SYNTHESIS",
        what=("The clobbering that nulled 31 synthesis blocks is fixed in both writers, and the "
              "31 have now been restored by hand (order 3c7c8a6e9102, closed 2026-08-28). What "
              "does not exist is a detector: `phase_synthesis` still skips any source already in "
              "its done-keys, so if a block is ever lost again -- by a new writer, a bad merge, "
              "or a restore that half-lands -- the pipeline will never revisit it and nothing "
              "reports it. The condition is trivially checkable (a record with entries and no "
              "synthesis) and `retry_synthesis.stranded_sources()` now computes exactly that "
              "list, so the missing piece is only that nobody CALLS it on a schedule. Suggest "
              "either a health.py check or a workorders detector that files an order when a "
              "record with entries carries no synthesis. Cheap, and it converts a four-day "
              "BLOCKING outage into an order that files itself the same hour."),
        handler="RUN", severity="MAJOR",
        where="src/health.py or src/workorders.py -- a detector for stranded synthesis",
        evidence={"restored_by_hand": 27,
                  "records_with_synthesis": "185 -> 212",
                  "still_null": "4, all with zero entries (owner-excluded sources)",
                  "detector_exists_but_uncalled": "retry_synthesis.stranded_sources()",
                  "why_it_persisted": "phase_synthesis skips sources in its done-keys"},
        found_by="maintenance-2026-08-28b")
    print("filed:", o["id"], o["code"])
    return 0


if __name__ == "__main__":
    sys.exit(main())
