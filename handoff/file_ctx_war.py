"""File the real cause of the dead local rung, which is OURS, and correct two recorded findings.

THE STORY THIS CORRECTS. The local rung has been unusable for 31 hours and it has now been
misdiagnosed three times, each time with confidence and evidence:

  run #35  blamed a foreign process -- pythonw "semsearch.cli watch" holding 9,599 connections.
  run #36  blamed the runner's infinite keep_alive and the num_ctx MISMATCH, and specifically
           refuted the reload theory on the grounds that the resident context never changed
           across a probe at four different num_ctx values.
  2026-08-28 (this session) established the mechanism by intervention rather than observation.

WHAT WAS ACTUALLY MEASURED TONIGHT, in order:

  1. The owner reported Ollama restarted. It was not: llama-server pid 29452 was the SAME
     process, up since 2026-08-26 17:28, by then at 95,241 seconds of CPU -- 26 hours of compute
     -- and still answering nothing.
  2. `ollama stop qwen3:8b` moved expires_at from 2318-12-07 to now. The runner ignored it and
     kept burning CPU: a wedged runner cannot process its own unload.
  3. Killing pid 29452 worked. A FRESH runner loaded within seconds -- and was immediately
     re-pinned at context_length 4096 with expires_at back to 2318.
  4. That re-pin is OURS. `grep keep_alive src/*.py`: `pipeline.ask` sends `keep_alive: -1` on
     every request, and so does `standards.py`'s health probe. Meanwhile FOUR call sites ask for
     a context that is not config's 12288:

         overwatch.py   nc = 4096 if len(prompt)+len(system) < 11000 else 8192   [FIXED tonight]
         pipeline.py    num_ctx=4096   (phase_synthesis)
         pipeline.py    num_ctx=4096   (phase_entrypass)
         magnitude.py   num_ctx=8192

  5. `overwatch.py` is a LOOPING DAEMON. Every cycle it dragged the resident model back to 4096
     while other callers asked for 12288, and both ends pin with keep_alive: -1.

WHY THE run #36 REFUTATION LOOKED RIGHT AND WAS INCOMPLETE. That probe watched the resident
context stay at 4096 across requests at None/4096/12288/4096 and concluded Ollama was not
reloading. It was not reloading FOR THAT PROBE -- because the queue was already saturated and the
12288 request was rejected outright ("maximum pending requests exceeded") before any reload could
begin. The refutation measured a symptom of the jam and read it as evidence against the cause of
the jam. The correct conclusion was narrower than the one drawn: matching num_ctx would not have
fixed anything WHILE THE RUNNER WAS ALREADY WEDGED, which is true and is not the same as the
mismatch being harmless.

THE DOCTRINE CONFLICT, which is the real decision and is the owner's. Two rules live in this
codebase and they contradict:

  * "num_ctx SIZED TO THE CALL, not a generous default" -- pipeline.ask's own comment, argued on
    VRAM: a 2,400-token batch in a 6,144 window pays 2.5x the VRAM it needs on a 10 GB card.
  * "one runner, one context" -- enforced by gpu_lane.py, local_agent.py and verify_math S19ab.

On this hardware the second wins and the first is a false economy, because Ollama holds a model
at ONE context: a differently-sized request does not get a cheaper window, it gets a REBUILD. The
VRAM saved is worth nothing if the model spends its life being rebuilt instead of serving. But
changing three more call sites is a real design change with real VRAM consequences on a 10 GB
card, so it is filed rather than taken.

Only the looping daemon was fixed tonight, because a loop is what turns a mismatch into a war.
"""
import os
import sys

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(HERE, "src"))
import workorders  # noqa: E402


def main():
    a = workorders.file_order(
        code="FOUR_CALL_SITES_FIGHT_OVER_THE_RUNNER_CONTEXT",
        what=(
            "THE LOCAL RUNG'S DEATH IS OURS, AND THIS IS THE THIRD DIAGNOSIS -- the first two "
            "are recorded as fact and are wrong. Ollama holds a model at ONE context size, so a "
            "request naming a different num_ctx forces the runner to be REBUILT, not given a "
            "cheaper window. Four call sites ask for something other than config's 12288: "
            "overwatch.py (4096/8192, FIXED tonight), pipeline.py phase_synthesis (4096), "
            "pipeline.py phase_entrypass (4096), magnitude.py (8192). Meanwhile pipeline.ask and "
            "standards.py both send keep_alive: -1, so whichever context wins is pinned "
            "indefinitely. overwatch.py is a LOOPING daemon, which is what turned a mismatch "
            "into a continuous rebuild war: a 6 GB model being rebuilt on a loop cannot also "
            "serve, and the queue saturates. MEASURED TONIGHT BY INTERVENTION: llama-server pid "
            "29452 had been resident 31 hours and burned 95,241s of CPU answering nothing; "
            "'ollama stop' moved expires_at from 2318 to now and the wedged runner ignored it; "
            "killing it produced a FRESH runner that was re-pinned at 4096 with expires_at 2318 "
            "within seconds, by our own code. CORRECTS run #35 (blamed a foreign semsearch "
            "client, which had already exited while the stall continued) and run #36 (blamed the "
            "keep_alive alone and explicitly REFUTED the reload theory, on a probe that watched "
            "the resident context hold still -- it held still because the 12288 request was "
            "rejected from a full queue before any reload could start, so the probe measured a "
            "symptom of the jam and read it as evidence against its cause). THE DECISION IS THE "
            "OWNER'S because two doctrines in this codebase contradict: pipeline.ask's comment "
            "argues num_ctx should be SIZED TO THE CALL to save VRAM on a 10GB card, while "
            "gpu_lane, local_agent and verify_math S19ab enforce ONE RUNNER, ONE CONTEXT. On "
            "this hardware the second wins -- VRAM saved is worthless if the model is always "
            "being rebuilt -- but changing three more call sites has real VRAM consequences and "
            "is not a maintenance run's call to make."),
        handler="OWNER", severity="MAJOR",
        where="src/pipeline.py (synthesis, entrypass), src/magnitude.py, src/overwatch.py [fixed]",
        evidence={
            "sites_not_using_config_num_ctx": {
                "overwatch.py": "4096 / 8192 (FIXED 2026-08-28 -- the looping daemon)",
                "pipeline.py phase_synthesis": 4096,
                "pipeline.py phase_entrypass": 4096,
                "magnitude.py": 8192,
                "config.yaml": 12288},
            "keep_alive_minus_1_sent_by": ["pipeline.ask (every request)", "standards.py probe"],
            "runner_before_kill": {"pid": 29452, "up_since": "2026-08-26 17:28",
                                   "cpu_seconds": 95241, "context": 4096,
                                   "expires_at": "2318-12-07"},
            "ollama_stop": "moved expires_at to now; the wedged runner ignored it",
            "after_kill": "a fresh runner was re-pinned at 4096 / expires 2318 within seconds",
            "corrects": ["run #35: foreign semsearch client (had already exited)",
                         "run #36: keep_alive alone; its refutation of the reload theory "
                         "measured a saturated queue rejecting the request, not an absent reload"],
            "doctrine_conflict": ["pipeline.ask: num_ctx sized to the call, for VRAM",
                                  "gpu_lane / local_agent / verify_math S19ab: one runner, "
                                  "one context"]},
        found_by="maintenance-2026-08-28 owner-directed follow-up, by intervention")
    print("filed:", a["id"], a["code"])

    workorders.resolve(
        "cf54b3ed349d",
        how=("Fixed, and it turned out to be the load-bearing one of the four. overwatch._ask "
             "computed nc = 4096 if len(prompt)+len(system) < 11000 else 8192 and passed it to "
             "pipeline.ask; it now passes no num_ctx at all, so it takes config's value like "
             "every other caller. This mattered more than the other three sites because "
             "overwatch is a LOOPING DAEMON: a one-off mismatch costs one rebuild, a looping one "
             "rebuilds the model forever. Measured tonight: killing the 31-hour-old wedged "
             "runner produced a fresh one that was re-pinned at 4096 within seconds. The "
             "remaining three sites (pipeline synthesis, pipeline entrypass, magnitude) and the "
             "underlying doctrine conflict are filed at OWNER as "
             "FOUR_CALL_SITES_FIGHT_OVER_THE_RUNNER_CONTEXT -- they are one-shot rather than "
             "looping, and changing them has real VRAM consequences on a 10GB card. NOTE: "
             "overwatch.py is running as a live daemon and holds the OLD code until it "
             "restarts; the fix is not in effect until then."))
    print("closed cf54b3ed349d")
    return 0


if __name__ == "__main__":
    sys.exit(main())
