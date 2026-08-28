"""File run #36's measurement of the local rung, which REFUTES the standing mechanism.

Orders a8464e348c5e and 505177847f43 both name a cause that this run measured and disproved.
That matters more than it sounds: a fix built on the recorded mechanism (lower `num_ctx` in
config.yaml to match the resident 4096) would have cost a real reduction in the chapter content
budget and changed nothing at all about the stall.

WHAT WAS MEASURED, 2026-08-27, directly:

  * `/api/ps` reports qwen3:8b resident at context_length=4096 with expires_at in the year 2318
    -- an effectively infinite keep_alive, so the runner is pinned and never recycles.
  * The SAME trivial 16-token prompt was sent four times with num_ctx of None, 4096, 12288 and
    4096 again. Three timed out at 90s; the 12288 one returned in 0.3s with the server's own
    error, "server busy, please try again. maximum pending requests exceeded". The resident
    context_length stayed 4096 across ALL FOUR, including the 12288 request.
  * That is the refutation. The recorded mechanism is "every request naming a different context
    forces a 6 GB reload". Ollama did not reload for the 12288 request -- it rejected it from a
    full queue while still holding 4096. The mismatch is real and worth tidying, but it is not
    what is stopping the work, and no num_ctx value succeeds.
  * The process previously blamed -- pythonw pid 11468, "semsearch.cli watch", 9,599 established
    connections -- IS GONE. Established connections to 11434 are down to 20, of which 10 belong
    to ollama.exe itself.
  * What is actually holding it: llama-server pid 29452, started 2026-08-26 17:28, which has
    burned 87,270 SECONDS of CPU (24.2 hours) in 29 hours of wall clock and holds 7.2 GB with
    the GPU at 96%. It is saturated with a full pending queue and it is not going to drain,
    because with expires_at 2318 nothing will ever unload it.

WHY THIS IS FILED AND NOT FIXED. Restarting a shared Ollama runner is not a Panscriptum action:
that daemon serves whatever else on this machine uses it, and the previous run's card says in
terms not to kill the owner's processes. The remedy is one line for a person -- restart the
Ollama runner, which releases the pin and drains the queue -- and it stays with the owner.
"""
import os
import sys

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(HERE, "src"))
import workorders  # noqa: E402

WHAT = (
    "THE LOCAL RUNG IS STILL CLOSED, BUT THE RECORDED MECHANISM IS WRONG AND A FIX BUILT ON IT "
    "WOULD HAVE COST QUALITY FOR NOTHING. Orders a8464e348c5e and 505177847f43 both attribute "
    "the stall to a num_ctx mismatch (config asks 12288, resident serves 4096) forcing a 6 GB "
    "reload per request. Measured directly on 2026-08-27: the same trivial prompt at num_ctx "
    "None/4096/12288/4096 gave three 90s timeouts and one instant server-side rejection -- "
    "'maximum pending requests exceeded' -- and the resident context_length stayed 4096 through "
    "ALL FOUR, including the 12288 one. Ollama never reloaded. No num_ctx value works, so "
    "matching them fixes nothing. The process previously blamed (pythonw pid 11468, "
    "semsearch.cli watch, 9,599 connections) HAS EXITED; connections are down to 20, ten of "
    "them ollama.exe's own. The actual holder is llama-server pid 29452, up since 2026-08-26 "
    "17:28, 87,270s of CPU burned in 29h wall clock, 7.2 GB resident, GPU 96%, pinned by "
    "keep_alive expires_at=2318 so nothing will ever unload it. A live local_agent order timed "
    "out at 300s with zero output. REMEDY, and it belongs to a person, not to this run: restart "
    "the Ollama runner to release the pin and drain the queue. Do not lower num_ctx -- that "
    "would shrink the chapter content budget and change nothing."
)

EVIDENCE = {
    "refuted_mechanism": "num_ctx mismatch forcing a per-request model reload",
    "refutation": "resident context_length stayed 4096 across num_ctx None/4096/12288/4096",
    "probe_results": {"none": "90.0s timeout", "4096": "90.1s timeout",
                      "12288": "0.3s ERROR 'server busy ... maximum pending requests exceeded'",
                      "4096 again": "90.0s timeout"},
    "previously_blamed_pid_11468": "GONE; established conns to 11434 now 20 (10 are ollama.exe)",
    "actual_holder": {"process": "llama-server", "pid": 29452,
                      "started": "2026-08-26 17:28", "cpu_seconds": 87270,
                      "working_set_mb": 7190, "gpu": "8200/10240 MiB, 96%"},
    "keep_alive": "expires_at 2318-12-07 -- effectively infinite, runner never recycles",
    "local_agent_probe": "300s timeout, zero output, rc=124",
    "remedy_owner_action": "restart the Ollama runner; do NOT change config.yaml num_ctx",
}


def main():
    o = workorders.file_order(
        code="LOCAL_RUNG_CLOSED_RECORDED_MECHANISM_REFUTED",
        what=WHAT,
        handler="OWNER",
        severity="MAJOR",
        where="localhost:11434 / llama-server pid 29452",
        evidence=EVIDENCE,
        found_by="maintenance-2026-08-27 direct measurement (ctx_probe + local_agent probe)",
    )
    print("filed:", o["id"], o["code"])
    return 0


if __name__ == "__main__":
    sys.exit(main())
