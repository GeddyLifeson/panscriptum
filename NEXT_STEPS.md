# NEXT STEPS — written by daily maintenance run #68 (2026-09-30, ~03:30)

*Overwritten every run. The queue in `state/workorders.json` is the authority; this file is the
reading order. The routine gained §0 (spend as few Claude tokens as possible) and "ANSWER THE
QUESTIONS YOURSELF" on 2026-09-30. Read both before you start.*

## 0. WHAT CHANGED LAST NIGHT, IN ONE PARAGRAPH

Sweep68 fixed 132 findings. The same agents then answered 93 of the questions the sweep raised
(61 changed, 32 kept) and reserved 11. Drill went from 829 to 1025 nets, and every new net was
proved RED under its revert. Along the way the run found and fixed three live faults:
* **the 09-29 mutation pass was void:** a mutant's halt persisted inside its sandbox;
* **prose was overwriting itself:** 1,251 duplicate job ids came out of `pipeline.phase_write`;
* **Storage Sense deleted about 12,400 live chunk-cache files:** it followed a sandbox junction that sat in %TEMP%.

The run also RAISED AND LIFTED TWO HALTS OF ITS OWN. Read the top of HANDOFF.md.

## 1. READ THE MUTATION PASS FIRST

`state/mutate_20260930c.log` was launched at about 03:10 as pid 21792 on the final tree. Its baseline
is clean: verify_math 1367/0, drill 1025/1025/0. Sandboxes now live in
`C:\Users\imarl\panscriptum-scratch`, not %TEMP%. All three targets changed last night, so expect
movement against the survivor counts on record. Read every BASELINE DRIFTED block. If the pass is
still running, do not relaunch it. Put the survivor count in the handoff.

## 2. THE QUEUE

* **RUN `8707ebf9ce01` (MAJOR): foreman writes the model's unverified patch into live `src/`.**
  foreman runs `--patch` live. Verify the patch in a sandbox copy (`mutate.sandbox()` or a
  one-module scratch) and write it into live `src/` only once it passes. Add the net.
* **RUN `36c4134de171`: 2,209 Character entries have topic Places.** Repair them through
  `write_record` (CAS). Check each against its description, because at least 207 genuinely are
  places.
* **RUN HOST_QUARANTINED rows:** batch 07 Q1 moved these from BOTS to RUN ("nothing but a run
  releases them"). But the queue sweep closed 14 of them by itself during run #68, and
  binding_health read 133 hosts with 0 failed. Re-check that decision, and move them back to
  BOTS if the sweep does close them.
* **OWNER `e2e5189c8da3`:** the reserved bundle (`handoff/sweep68/RESERVED.md`). Leave it.
* **OWNER `3976a097f975`:** 580 shared addresses. Leave it; generate holds those jobs by name.
* **BOTS `058fa19d4e65`:** unchanged. It closes when `data/CHAIN.json` carries `unmatched`.

## 3. CONFIRM WHAT ONLY A LATER CYCLE CAN SHOW

* **Prose on the corrected manifest.** Near the top of `prose_auto.log` you should see
  "ADDRESS COLLISION -- 580 address(es) ... held". Read two new v6 chapters against their jobs
  with `handoff/prose_check_0929/BRIEF.md`. Last night's check read the wrong canon because of
  the collision, so the invention question for v6 is still OPEN.
* **The chunk cache refills.** Count `data/chunkfeats/*/*.json` (it was 6,198 after the
  incident) and watch cloud-call volume in read.py. The lost entries are re-asked as misses.
* **The Ollama reaper runs.** In foreman's log, look for `housekeeping -> reap_ollama_orphans`
  lines when there was something to reap.
* **batch 15 Q4:** the first `coverage.measure()` discards the live memo once and reparses the
  evidence corpus. It could hit foreman's 600 s timeout one time.

## 4. THINGS A FRESH RUN WOULD OTHERWISE REDISCOVER

* **Run at most 2 `drill.py --prove` at once, and check `df -h /c` first.** 12 at once filled
  C:, which triggered Storage Sense, which deleted live data. `prove_net` now refuses under 20 GB.
* **The splice script** (`state/work_scripts/run68_splice.py`) refreshes nets whose file changed.
  Fix a net in its FILE under `handoff/sweep68/nets/`, never only in drill.py, or the next splice
  reverts it.
* **A net that stubs a function** needs `*a, **k`, or verify_math's stand-in arity checks go red.
  A stdlib stand-in (such as `time.strftime`) is unresolvable, so don't stub stdlib.
* **A net whose subject now calls `silence.note`** must wrap that call in `_deliberately_failing`,
  or the ledger witness halts the library.
* **HALT.json persists after a lift** (`cleared: True`). Agents read it and wrongly report "the
  library is halted". Trust `escalation.py --status`.
* **`_scrub_sandbox_halt` and `scratch_home()` are new in mutate.py.** Don't undo them.
