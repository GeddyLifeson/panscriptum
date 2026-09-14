# Next Steps — the priority queue for the next maintenance run

*Overwritten each run. The permanent record is `HANDOFF.md`; the live queue is
`state/workorders.json` via `python src/workorders.py --sweep`.*

Written by run #58 (daily), 2026-09-13/14. **No halt was raised or lifted. The library is running and the battery is green, apart from one external row.**

    drill              590 nets / 590 held / 0 BREACHED   (was 523; +67 nets this shift, each proven HELD and RED)
    verify_math        1307 passed / 0 FAILED            (was 1294)
    allsweep           1 subsystem bad -- preflight (dandwiki no-api, owner order 8b3f2911fa0c); cascade live call OK again
    pyflakes           clean over src/
    secondopinion      all three tools RAN, 0 secrets by two independent scanners
    liveness           47 findings, 0 tautology, 0 phantom
    silence            300 SILENT handlers
    axis_correlation   45 entities -- unchanged, no --write owed
    sweep run58        16 batches, all 119 modules, `missing()` = []
    escalation         clear
    queue at close     54 open -- RUN 11 / OWNER 41 / LOCAL 2 / SESSION 0   (was 95)

---

## READ FIRST: FIVE THINGS TO CHECK BEFORE ANYTHING ELSE

**1. Three daemons were still on start-of-shift code at close:** `overnight`, `pipeline` and `read`. The tree never held still for 180s while agents edited, so none could bounce during the shift. Run #58 stopped `foreman` by hand under the ten-minute rule (the keeper had it back in six seconds). It deliberately did not kill the supervisor, which awaits the feats lap, or pipeline and read, which were mid-work. Run `python src/codewatch.py` and check each has bounced. If one has not, restart it at a safe point and say so.

**2. The mutation pass (pid 39980, `state/mutate_20260913.log`).** At run #58's close it had not finished its first target. Its sandbox predates run #57's AND run #58's edits, so it judges mutants against a drill of 511 nets and a verify_math of 1289 rows. **Re-check every survivor it reports against the CURRENT battery (590 nets) before filing.** When the pass ends, and `state/MUTATION_ACTIVE.json` is gone:
* do `d56cb7f2bed0` (the prose_gate eaten-escape guard)
* do the citation sites inside assay.py, prose_gate.py and escalation.py left open on `89503c58409f`, `1d45a56ae1d8` and `d7efd67caa6f`
* read the result that `58a00e909217` is waiting for

**3. The publish daemon's first push after run #58 released the guard.** Run #57's unexplained `could not read Username` failure has still not reproduced: 0 occurrences during run #58, when the daemon correctly skipped every cycle under the guard. Watch `state/publish.log`.

**4. Claim the guard WITH A TOKEN.** Since order 12d4e1b00c2f, a one-shot `publish.py --push` during a live shift is exempt only for the guard's holder. Run #58's guard predated tokens, so its own push used the legacy override (`PANSCRIPTUM_GUARD_TOKEN=<non-empty>` plus `--i-hold-the-guard`), which is logged as a trusted assertion, not a proof. Instead, claim with `runguard.claim(agent, token_path=<a private scratch file>)`, keep the token, and push with `PANSCRIPTUM_GUARD_TOKEN=<that token>`.

**5. Do not spend a shift re-deriving the owner decisions.** They are routed, each with a written reason: `1e6f99e54b25` + `21c075e5e2d6`, `a5faab7f3ede`, `a724ec57e0d5`, `d1709d8e757d`, `d9328fe1ee38`, `79d51aef8b71`, `30854f11f322`, `a66423722e45`, `0384c99d5454`, `34ec8a90c42f`, `ff77e242b830`, `325ccb493c45`, `a8e02f3bbf76`, plus the external `8b3f2911fa0c` / `32eaec248adf` / `2d6c9343cd32`.

---

## THE RUN WORK LEFT, IN ORDER

**1. `fadd4338a7b0`: the eaten-escape guard on 23 named regex-importing modules.** Do it as ONE batch at the START of the shift, before any other edit, because every save to a daemon's module costs a restart of every standing daemon. Copy the guard exactly from local_agent.py. drill.py and workorders.py are on the local model's write denylist.

**2. Small and well-specified, filed this shift:**
* `9f1cce19c85c`: `drill.py --prove` never prints the child's stderr, so a crash shows no traceback.
* `e3fcbbe262e2`: an absent corpus.db passes the index-spine net, and every prove and mutation tree is in that state.
* `5b00f9d39b94`: `workorders.where_targets` still reduces a backslash path to its basename.
* `ec8b8b35e521`: generate.py's failures.json is load-once-write-whole (latent under the singleton guard).
* `058fa19d4e65`: rebuild `state/chain_harvest_idx.json` so the widened OUTCOME pattern reaches indexed feats; better, add a pattern digest to the index.

**3. Needs a reproduction, not a patch:** `9ea4d3545524`, the mutation sandbox FileNotFoundError. Run a pass with its sandbox root audited, and name the process that deletes it.

**4. Questions only:** `2f314697d52b` (INFO): child spawns without `cwd=` in `_live_audit`, and whether THE LIVE-STATE WITNESS should drive every sandboxed probe.

**5. The partial citation orders** (`89503c58409f` RUN, `1d45a56ae1d8` LOCAL, `d7efd67caa6f` LOCAL). Beyond the mutation-target sites (item 2 of READ FIRST), three kinds of site remain:
* citations inside STRING literals in drill.py and verify_math.py, which a check may match on, so grep before editing
* four historical mutation coordinates in mutate.py (`escalation.py:409` / `assay.py:593`). Run #58 deliberately left these: they are the key format of `mutate.py --rule-equivalent` and of the orders that cite them, and line 1056 is a CLI usage example.
* one intentional fixture string in verify_math.py (`"# see verify_math.py:1457 ..."`). Do not "fix" it.

---

## LESSONS FROM RUN #58 (keep them)

* **Never set a shell variable inside a backgrounded `&&` chain.** `VAR=x && ... & job2 &` hands the assignment to the first background job only. It bit twice.
* **Every stored order field is length-checked against 80/200/400/600.** `file_order` now refuses one, and the drill breaches on an open order that has one.
* **The Write tool saves CRLF on this machine.** A revert JSON whose strings carry CRLF matches nothing, and `--prove` then reports DID NOT RUN, not RED. Normalise before proving.
* **An agent's standalone "RED" is not a landed net.** W2a found three proposals whose reverts could never defeat them.
* **Run the central drill after every landing wave, not only at close.** Both of this shift's breaches were caught that way within minutes.
* **Sweep the code the shift itself wrote.** Sweep 58 found nine defects in this shift's own fixes, every one of which had passed its author's tests.
