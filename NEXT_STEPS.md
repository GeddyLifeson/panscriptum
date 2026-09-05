# NEXT STEPS — written by the daily maintenance run of 2026-09-04 (run #44)

## 0. THE MUTATION PASS IS STILL RUNNING. READ ITS LOG BEFORE YOU DO ANYTHING ELSE.

    state/mutate_20260904.log        the run
    sandbox: C:\Users\imarl\AppData\Local\Temp\panscriptum_mutate_axiwiyu8

Launched 2026-09-04 ~23:15 with `--target all --file-orders --rebaseline-every 3600`. It takes
roughly eighteen hours, so **it will not have finished when you open**, and it may still be live.
Check before assuming either way:

```
python src/mutate.py --status 2>/dev/null || python -c "import sys;sys.path.insert(0,'src');import mutate;print(mutate.active())"
```

**Its baseline was fully green, which is the thing that was wrong last time:**
`verify_math rc=0 | 1130 passed, 0 FAILED` and `drill rc=0 | 395 nets, 395 held, 0 BREACHED`. The
2026-09-02 run that filed the eleven `MUTANT_SURVIVED_*` orders took a **red** baseline with
`verify_math` disabled, which is why `assay.py:228` "survived" that day.

**The log carries a warning you should read and then discount:** *"A MAINTENANCE SHIFT IS EDITING
THIS TREE."* That fires because this run still held `state/MAINTENANCE_RUN.json` with a fresh
heartbeat at launch. My `src/` edits were finished before the launch — the relaunch was
deliberately held until they were. The warning is conservative by design; it is not evidence the
source moved under this baseline.

### WHAT IS NEW IN THE INSTRUMENT, AND WHAT TO LOOK FOR IN THE LOG

`mutate.py` now re-photographs the gates on restored code every `--rebaseline-every` seconds. This
is the experiment run #43 asked for, built as a permanent feature rather than a one-off:

- **`baseline re-photographed every 3600s and never disagreed with itself.`** If you see this and
  no drift lines, then over an eighteen-hour run the gate signatures were **stable**, and run #43's
  leading hypothesis — that a moving `data/` junction drifts the baseline — is **not** the
  explanation for the `escalation.py:409` false kill. That would be a real result, and it would
  send the next investigation somewhere else. Say so in the handoff either way.
- **`*** BASELINE DRIFTED on clean code (...) ***`** with a list of `in doubt:` lines. Every kill
  named there was judged against a stale signature and **is not evidence of coverage**. Those
  drift records are also journaled to `state/MUTANTS_SURVIVED.jsonl` under `baseline_event`, so
  they survive a crash.
- **`a mid-run baseline refresh could not complete`** — a refresh whose gates timed out was
  **discarded**, not adopted, and the previous known-good photograph stayed in force. That is
  correct behaviour, not a fault, but it means the window it covers was judged against an older
  baseline than the clock implies.

### AND THE QUESTION THAT IS STILL OPEN

`escalation.py:409` is a **confirmed false kill** (orders `a380a696d364` and `e5954a534604` are
CORRECT and must not be closed). **Check what this run says about it specifically.** If this run
reports it as a SURVIVOR, the periodic re-baseline was the fix and the instrument can be trusted
again. If it reports it KILLED with no drift recorded, then drift is **not** the mechanism and the
cause is still unknown — which is a more important finding than the score.

**Do not close the eleven `MUTANT_SURVIVED_*` orders in bulk on the strength of any run.** Retire
them one at a time by re-attack; the method is in `state/equivalent_mutant_test_20260904.log`.

---

## 1. THE QUEUE GREW, AND THAT IS NOW THE BINDING CONSTRAINT

    open at start:  411      LOCAL 141 · BOTS 23 · RUN 70 · SESSION 57 · OWNER 122
    open at close:  441      LOCAL 150 · BOTS 22 · RUN 86 · SESSION 57 · OWNER 126
    filed 32 · closed 10

Sweep 44 read **116 modules, 92,633 lines, and `sweep_plan.missing('run44')` returns 0** — every
module in `src/` read in full. A sweep of that size files more than one shift can work. The honest
reading is that the detectors are working and the *working* rung is the bottleneck; it is not that
the sweep should be smaller. **Do not sample the queue** — Hard Rule 0 applies to your own shift.

**Where the leverage is, in order:**

1. **`8cdbd0fb6c14` VERIFY_MATH_POOL19AI_NONE_UNGUARDED (RUN/MAJOR).** `_pool19ai` returns `None`
   when its standard vanishes and six sites subscript it unguarded, so verify_math raises at
   **module level** — no `RESULT:` line, `allsweep` grades it BROKEN. This is a **mutation gate**:
   a gate that dies before printing its signature produces exactly the ERROR/TIMEOUT class that
   `unusable_gates` refuses, so this can take the measuring instrument out on clean code. Fix this
   one first.
2. **`0e041fe97852` PIPELINE_CEILING_PROMPT_CAPS_FEATS_AT_THREE (RUN/MAJOR).** `fl[:3]` — an
   unranked, unmarked cut on an ordered evidence list feeding the power-ceiling model call. Both
   readings are in the order; even under the context-budget reading, the *unranked and unmarked*
   part is wrong on this project's own terms.
3. **`af47010df391` CASCADE_SIZE_REFUSAL_READ_AS_THROTTLE (RUN/MAJOR).** A permanent per-request
   size refusal filed as a transient throttle, so the bucket is cooled and the same impossible
   request retried for ever. Note the constraint recorded in the order: **there is no `max_tokens`
   anywhere in `src/`**, so the remedy can only exclude the bucket, not shrink the request.
4. **The six `drill.py` orders** (`16b4f9dbecb6`, `d1b2247ff350`, `3c4b04b4b463`, `515eb8cae3c2`,
   `f5f01fe5f8ef`, `a531ac23d07c`). These are defects in the battery that Hard Rule -1's PROVEN
   property rests on — including four clauses in one net that **cannot fail**, which is the exact
   shape `liveness.py` exists to find. `515eb8cae3c2` has four sites and wants one careful change,
   not four independent ones.

---

## 2. WAITING ON A PERSON — THE NEW ONES FIRST

- **THE POLICY NARROWING I MADE, WHICH YOU MAY WANT TO REVERSE.** I added `prose_gate` and
  `publish` to `local_agent.DENYLIST` (order `0434fc05eb95`, filed and closed with the
  measurement). Before it, `_denied_target` returned `False` for both — the local model could
  write the prose gate itself and the module that pushes to the public repo behind the secret
  scanner. This **narrows the LOCAL rung** and four `publish.py` orders were re-routed LOCAL → RUN.
  I believe it is right; it is still a policy change made by a maintenance run and it wants a
  ruling.
- **`d3acbb793ef2` — `cascade_bridge`'s pin path has no local-bucket exclusion** while the non-pin
  claim loop does, and `try_disabled()` admits *disabled local Ollama models*. Traced against the
  live `cascade/config.json`: six disabled `provider:"ollama"` entries sit in the `coding` pool
  now, and running `try_disabled()` today would dispatch a live call to a local GPU bucket — an
  absolute invariant that file states never to break. Small remedy, most critical subsystem.
- **`5c962f306e58` — the MODEL-patch gate calls `allsweep --quick`, which skips the whole VERIFY
  tier.** A model patch that breaks a verifier's CLI contract is accepted as "verified" by a gate
  that never ran it; `rosetta.py` carried that class of regression for eleven runs. May be a
  deliberate trade against the foreman's 20-minute loop.
- **`6fc71f8ab76e` — feat-less entries are never nominated for the power ceiling** once a source
  has any feat-bearing entry. The two readings differ about what the *absence of a feat means*,
  which is a question about the library, not the code.
- **`2e0ba4b02ec4` — `liveness`'s PHANTOM pass has no per-function scoping.** Changing it moves a
  ratcheted count, so it should have a name attached.

**Still standing from earlier runs:** `c614f7c145fc` (the 2026-08-26 automated halt-lift);
`88982cef258d` (providers rate-limited at once); `171ade4c7d27` (`local_agent` returns `ok:true`
for an answer whose text says it failed — **do not** implement a heuristic predicate for this);
`codewatch`'s deliberate fail-open paths; `runguard`'s fail-open on a corrupt guard;
`assay.ATTESTATION_FLOOR` having no monotonicity or ceiling guard while its sibling is protected.

---

## 3. STANDING, AND UNCHANGED

- **`foreman` and `overwatch` run under `pythonw.exe`, not `python.exe`.** A process search that
  only asks about `python.exe` finds neither and will tell you they are down. I bounced both this
  shift (they were 23 hours stale and predated the denylist fix); the keeper restarted them at
  23:14 on current code. **`state/CODEWATCH.json` records only *keeper* restarts, so a manual
  bounce leaves no trace there** — its timestamps read 46 hours old while the processes were 23
  hours old. Check `CreationDate` on the real processes, not the file.
- **The GitHub push is live and everything you write is public**, including all sixteen
  `handoff/sweep44/AUDIT_batch*.md` files and these three ledgers. Write them as publishable prose.
  The secret gate passed on the way out with two independently-written scanners agreeing on zero.
- **Never open `prose_enabled` or `step4_enabled`.** A gate that looks unnecessary is what a
  working gate looks like.
- **Do not widen `state/ledger_chain_acknowledged.json`.**
- **`publish.py:293`'s `_AMBIGUOUS` case-sensitivity stays as it is** — the change would loosen the
  gate in front of a public push, and it currently fails toward over-blocking.
- **Do not implement `local_agent` "refuse immediately on a saturated queue"** — measured and
  rejected; it turns a slow success into a fast failure.
- `data/records/getter-robo.json.precatfix` is still a non-`.json` leftover in the records
  directory, carried from run #42. **I did not delete it** — it is a backup of canonical record
  data and deleting one is not a night-shift call. It wants an owner's word or a verified
  equivalence check against the live record.

---

## 4. PROCESS LESSONS FROM THIS SHIFT

1. **"Never pass prose through a shell" is not about backticks.** A `bash` heredoc ate the `\n`
   escapes in a batch of order text and produced an unterminated string literal. Same family,
   different mechanism. Write prose with the file tool, run the file, **and read one record back
   off disk afterwards** — that habit is what confirmed the text landed intact.
2. **Write the net against the invariant, not the spelling.** The meta-ban net asserts *no handler
   falls through* rather than *there is no `ImportError` arm*, and it caught three reconstructions
   it was never written against. A net that only catches the exact defect it was written for is
   worth much less than it looks.
3. **When the fix is about a type, pin both directions.** The boolean-score net also refuses the
   *tempting* truthiness fix, because that one would reject a legitimate score of `0`.
4. **A subagent auditing your own hours-old code is worth more than one auditing old code.** Sweep
   44 batch 5 found a MAJOR defect in the re-baseline feature I had written that same shift, and
   it was right. I killed the running mutation pass and relaunched on corrected code rather than
   spend eighteen hours on an instrument I already knew could be poisoned mid-run.
5. **`silence.replace_retry(path, content)` is not a writer.** It is `os.replace` with a backoff.
   `silence.write_json` is the one correct way. The wrong call returns `False` and writes nothing
   rather than raising — so it fails quietly, which is why it is worth knowing before you reach
   for it.
