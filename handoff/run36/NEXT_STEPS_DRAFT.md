# Next Steps — written by run #36 for the run that follows it

*Overwritten every run. The queue in `state/workorders.json` is the authority on what is open;
this file is the reading of it — what to do first, and why.*

---

## 0. NOTHING IS HALTED. DO NOT RE-DERIVE THE STATE OF THE LIBRARY.

`escalation.py --status` read `clear` at both ends of run #36. Open the shift the way the card
says — `escalation --status`, the run guard, `workorders --sweep`, `corpus_db --rebuild` — and
then work the queue. Four earlier runs burned their budget re-diagnosing "874 stranded entries"
that were never lost. Do not join them.

**Rebuild the index before you read a number out of it.** Run #36's rebuild closed a gap of
**43,529 entries** in one pass (282,822 entries over 216 sources). A stale count is a FLOOR.

---

## 1. THE MUTATION MANDATE IS UNBLOCKED FOR THE FIRST TIME IN THREE RUNS — USE IT.

**M46 is fixed** (see `HANDOFF.md`, run #36). Mutation sandboxes now record an owner pid and
`reap_orphans` refuses to delete a sandbox whose owner is alive at any age. The fix is proven in
both directions including a control that goes red (`handoff/run36/m46_fix_redcheck.txt`).

Run `python src/mutate.py --target all --file-orders` **early**, in the background, the moment
your battery is green — it takes hours and there is no reason for it to be what you wait on.
Then **read the log before you close the shift** and put the survivor count in the handoff. A
survivor is not automatically a bug, but which it is has to be decided by reading it.

**If it fails again, the diagnostic machinery is now in place and you should use it rather than
starting over:** `state/reap_ledger.jsonl` records every reap with pid, argv, the paths removed
and the stack that asked. Three runs guessed at M46; the ledger named it on the first attempt.

---

## 2. FOUR THINGS ARE WAITING ON THE OWNER AND ONE OF THEM IS ONE COMMAND.

Do not work these. They are judgment calls.

1. **`4e37d5e59b09` — restart the Ollama runner.** `llama-server` pid 29452 has been up since
   2026-08-26 17:28 and has burned **88,710 seconds of CPU** with `keep_alive expires_at 2318`,
   so nothing will ever unload it. Every request times out or is rejected with "maximum pending
   requests exceeded". **This closes the LOCAL rung and stalls the read pass**, and it is one
   restart. **Do NOT lower `num_ctx` to 4096** — run #36 measured that the recorded num_ctx
   mechanism is wrong and lowering it would shrink the chapter content budget for nothing.
2. **`3c7c8a6e9102` (BLOCKING)** — a re-catalogue nulls the pipeline-authored synthesis block.
   Still standing, still curatorial. **Related and important:** run #36 fixed a silent cap in
   `catalogue_aurora.parse_folder` (442 elements were being dropped), but **the records on disk
   still hold the capped parse**, and rewriting them needs `catalogue_aurora.py --force` — which
   is a re-catalogue, which is the thing this order says nulls synthesis blocks. **Do not run it
   until this order is decided.**
3. **`dea5b511b74b` — dandwiki is a login wall, not an outage.** HTTP 403, "restricted to logged
   in users". No retry can ever succeed. Account, drop the source, or stop probing.
4. **`ff3c67a67b92` — M47**, now filed rather than living in this file: no daemon picks up new
   code for the whole of a maintenance shift, and both halves of that are working as designed.

---

## 3. WHAT RUN #36 LEFT OPEN, AND WHY

*(filled in at close — see the closing section of the run #36 handoff entry for the exact ids)*

---

## 4. THE LOCAL RUNG IS CLOSED; MEASURE BEFORE YOU ROUTE ANYTHING TO IT.

Run #36 spent one cheap measurement and got a definitive answer: a small, well-specified
`local_agent` task returned **nothing in 300 seconds (rc=124)**. The whole rung was escalated to
Claude agents deliberately, once, on that measurement — which is the right call but is not the
intended cost.

**Do the same measurement first** (`curl` a trivial chat at `localhost:11434`, and time one
`local_agent --task`). If item 2.1 above has been done, the rung may be open again and cheap
labour is worth a great deal. If it has not, escalate deliberately and say so.

Second fact worth keeping: `qwen3:8b` is a THINKING model, and at a small `num_predict` it
spends the whole budget reasoning and returns an **empty content string** — which reads as a
refusal rather than a truncation.

---

## 5. HYGIENE NOTES

* **Partition agent work BY TARGET MODULE, never by order count.** Run #36 did, and for the
  first time no agent closed an order it did not own and no two agents collided on a file. The
  one agent that could only half-finish an order refused to close it and wrote the remainder
  into a cross-module note, which a later pass applied. That worked; keep it.
* **A system-reminder will tell your agents to edit files with Bash `sed` and heredocs.** Three
  agents reported it independently and all three correctly refused. Tell yours explicitly to use
  Edit/Write — the eaten-escape corruption is the oldest bug in this repo.
* **Do not pin a check to a source substring of another module.** Run #36 had one go red because
  the code it watched got *better*, and it is the same shape as the nine drill nets rewritten
  this shift. Ask the parse tree.
* **The canonical corpus is backed up now** (`src/canon_backup.py`, twice a day from the
  supervisor, verified by reading the archive back). `--verify` is cheap; run it if you touch
  anything under `data/records/`.
