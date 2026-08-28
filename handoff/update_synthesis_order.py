"""Record progress on the standing BLOCKING order without closing it. The blocks are still null.

Order 3c7c8a6e9102 stays OPEN because the thing it is about -- 31 records carrying a null
synthesis, 191,029 entries, Marvel and DC among them -- is unchanged on disk. What changed
tonight is that the rescue path is now capable of doing the work, and the reason it still cannot
is measured rather than assumed.

TWO REAL DEFECTS IN THE RESCUE TOOL, both fixed:

  1. `retry_synthesis` selected on the CAUSE and not the CONDITION. It read the pipeline's
     failed-set, which holds TWO names. Twenty-nine of the thirty-one never failed anything --
     their blocks were written correctly and then clobbered by the catalogue writer. A rescue
     tool whose whole job is "sources the pipeline will never revisit" could see two of the
     thirty-one that qualified. It now also selects `stranded_sources()`: no synthesis block,
     and entries to reason over. 2 failed + 27 stranded = 28.
  2. It called `PL.ask` -- Ollama only -- while `phase_synthesis`, the function it exists to
     stand in for and whose prompt construction it deliberately shares, calls
     `PL.ask_pool_first` (cloud first, local second). The docstring already records being burned
     once by exactly this kind of drift, when the two built different prompts. They were asking
     different MODELS too. Now both go pool-first.

AND THE BLOCKER, WHICH IS NOT IN THIS TOOL. Neither transport is available:

  * CLOUD: `ask_pool_first` is gated on `tuning.CLOUD_MIN_BUCKETS` (3) answering buckets. A
    fresh `cascade_bridge.prove()` tonight returned exactly TWO, both groq. The gate correctly
    refuses. Lowering the threshold to force the work through was considered and rejected: the
    constant carries a written argument for why two is not enough, and weakening a policy to get
    a result is the shape of decision this project exists to catch.
  * LOCAL: the Ollama runner is saturated by a context reload war between four of our own call
    sites -- see order 706215aabc5f. Killing the 31-hour-old wedged runner produced a fresh one
    that was re-pinned at 4096 within seconds by our own code.

So the work is ready and there is no model to do it with. That is a materially different state
from this morning, when the tool could not have done it even with a model.
"""
import os
import sys

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(HERE, "src"))
import workorders  # noqa: E402

NOTE = (
    "STILL OPEN -- the 31 blocks are still null on disk and nothing has been re-derived. What "
    "changed on 2026-08-28: the rescue path is now able to do the job, and the remaining blocker "
    "is measured. Re-measured tonight: 31 records with null synthesis, all mode=web, 191,029 "
    "entries, Marvel (59,170) and DC (55,560) the largest; 27 of them have entries to reason "
    "over, and the pipeline's failed-set holds only TWO names -- confirming the other 29 were "
    "CLOBBERED rather than failed, exactly as this order says. TWO DEFECTS FIXED IN THE RESCUE "
    "TOOL, both of which would have silently limited any attempt: (1) retry_synthesis selected "
    "on the CAUSE (the failed-set) rather than the CONDITION (no synthesis block), so it could "
    "see 2 of the 31 that qualified -- it now also takes stranded_sources(), giving 28; (2) it "
    "called PL.ask (Ollama only) while phase_synthesis, whose prompt construction it "
    "deliberately shares so the two cannot drift, calls PL.ask_pool_first (cloud first) -- they "
    "were asking different models. Added --only and --smallest for piloting. THE BLOCKER IS NOW "
    "TRANSPORT, NOT SELECTION, and neither arm is available: the cloud pool answers with 2 "
    "buckets against tuning.CLOUD_MIN_BUCKETS=3 (fresh prove tonight; lowering the threshold was "
    "rejected -- the constant carries a written argument that two is not enough, and weakening a "
    "policy to obtain a result is precisely what this project exists to catch), and the local "
    "runner is saturated by a context reload war among four of our own call sites (order "
    "706215aabc5f). A pilot on the smallest stranded source (Chowder) ran end to end and failed "
    "at the transport with 'ollama failed after 3 tries: HTTP 503', which is the correct "
    "behaviour and is the evidence. NEXT: this becomes runnable the moment either arm opens -- "
    "one more answering cloud bucket, or the owner's ruling on the three remaining num_ctx call "
    "sites. It can also be forced tonight by quiescing the competing model consumers (read.py, "
    "pipeline.py, magnitude.py --calibrate), which the --merge step requires stopped anyway; "
    "that stops the library's overnight work for hours and was not done unilaterally.")


def main():
    o = workorders.file_order(
        code="RECATALOGUE_NULLS_PIPELINE_SYNTHESIS",
        what=NOTE,
        handler="OWNER", severity="BLOCKING",
        where="data/records/*.json synthesis block (31 null) + src/retry_synthesis.py",
        evidence={
            "null_records": 31, "entries_affected": 191029,
            "largest": {"marvel": 59170, "dc": 55560},
            "failed_set_size": 2,
            "clobbered_not_failed": 29,
            "rescue_selection_before": "pipeline failed-set only (2 of 31)",
            "rescue_selection_after": "failed + stranded (28)",
            "rescue_transport_before": "PL.ask (Ollama only)",
            "rescue_transport_after": "PL.ask_pool_first (cloud first, local second)",
            "cloud_buckets_answering": 2, "cloud_min_buckets": 3,
            "local": "saturated by the num_ctx reload war, order 706215aabc5f",
            "pilot": "Chowder: ran end to end, failed at transport with HTTP 503",
            "unblocks_when": "one more answering cloud bucket, OR the num_ctx ruling, OR "
                             "quiescing read.py / pipeline.py / magnitude.py"},
        found_by="maintenance-2026-08-28 owner-directed follow-up")
    print("refreshed:", o["id"], "seen", o["seen"])
    return 0


if __name__ == "__main__":
    sys.exit(main())
