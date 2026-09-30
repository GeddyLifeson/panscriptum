# NEXT STEPS — written by daily maintenance run #67 (2026-09-29, ~01:00)

*Overwritten every run. The queue in `state/workorders.json` is the authority; this file is the
reading order.*

---

## 0. WHAT CHANGED LAST NIGHT, IN ONE PARAGRAPH

Sweep67 read all 119 modules and found 141 defects; a second agent pass verified each against
source (0 refuted) and every one was fixed or narrowed to a stated question. 126 orders closed,
106 drill nets added or changed (715 -> 819), each proved RED under a revert and HELD. The biggest
fixes: the two record writers are now a compare-and-swap with a per-field watermark; the
"read-only" allsweep no longer runs thirteen modules' real `main()`; a halt file can no longer be
lifted by a truthy string. Read the 2026-09-29 entry at the top of HANDOFF.md.

## 0b. SINCE THEN (2026-09-29 evening session)

Prose was inventing facts (every checked chapter) and 13,395 people were filed as places. Fixed
at the cause and repaired -- HANDOFF.md's 2026-09-29 evening entry. prompt_version is v6, so all
old chapters regenerate. Two things to check tonight:
* **Read two or three v6 chapters against their jobs** the way `handoff/prose_check_0929/` did
  (BRIEF.md is reusable): the Record should not outgrow its description, and no Hand should
  claim to have been anywhere. `prose_auto.log` now prints "dropped N invented margin note(s)" --
  a high rate means the prompt change is not landing with qwen3:8b.
* **cmd.exe crashes on start machine-wide** since 2026-09-29 18:11. Junctions no longer need it;
  anything else that shells through cmd will fail silently. If it persists, a reboot is the next
  step (not ours to take).

## 1. READ THE MUTATION PASS FIRST

`state/mutate_20260929.log`, launched ~00:55 on fingerprint `a0cd7c9032709fb1` (the final tree
of run #67), detached as pid 27520. Baseline in its sandbox: verify_math 1346/0, drill
819/819/0. Two of its three targets (escalation.py, assay.py) changed last night, so expect
movement against the "on record" survivor counts. Read every BASELINE DRIFTED block before
trusting a kill, and put the survivor count in the handoff. If it is still running, do not
relaunch it.

## 2. THE QUEUE

* OWNER `cd77e492b26b`: handbuilt superlative wording. Leave it.
* BOTS: 22 fandom throttle quarantines expiring on their own; `058fa19d4e65` closes when
  `data/CHAIN.json` carries `unmatched` (pipeline phase 4).

## 3. CONFIRM WHAT ONLY A LATER CYCLE CAN SHOW

* **The record writers under load.** pipeline was restarted onto the CAS writer at ~23:45. Look
  in `state/pipeline.log` for `kept changing under this writer` (CAS exhausted) and `keeping N
  disk per-entry value(s)` (the widened watermark yielding to disk). Either appearing is the fix
  working; a flood of the first would mean two writers fighting and is worth an order.
* **allsweep no longer touches data/.** After tonight's allsweep, the mtimes of TIERS.json,
  SHELFMARKS.json and ONOMASTICON.json should not move during it.
* **navtree** refuses `--write` until SEVENFOLD.json is rebuilt: an owner question in the
  handoff. Anything that expects a fresh NAVTREE will see the refusal, by design.
* **The crawl** (`feats.py --roll`, codewatch-exempt) picks up the feats.api error-body fix on
  its next lap. After that, a `ratelimited` body should show as `api-ratelimited-body` in the
  failure ledger, not as clean speed.

## 4. THINGS A FRESH RUN WOULD OTHERWISE REDISCOVER

* **The shell here eats backslash escapes in heredocs, including `python - <<'EOF'`.** Three times
  last night `\n` inside a Python string literal arrived as a real newline. Write any code with a
  backslash through the Write/Edit tools, run it from a file, and check it with pyflakes.
* **A drill breach does not halt while a mutation pass is active**, and one is active all day
  now. Read BREACHED lines yourself.
* **Agents' reverts must be LF**: `drill._substitution` reads modules in text mode, so a revert
  written with a CRLF module's own endings matches 0 times.
* **The local model took 25 minutes to fail one trivial order with prose on the GPU.** Try it
  first on a LOCAL order; if it stalls again, say so and move on.
* **`silence` SILENT is 352, up from 312**, explained in the handoff. The `_ = "silence-exempt"`
  marker does not lower the count for `except` handlers; do not chase the number by marking.
* Never run two verify_math processes at once, and a mutation baseline counts.
