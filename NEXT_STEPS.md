# Next Steps — the priority queue for the next maintenance run

*Overwritten each run. The permanent record is `HANDOFF.md`; the live queue is
`state/workorders.json` via `python src/workorders.py --sweep`.*

Written by run #46, 2026-09-07. **Queue at close: 293 open** (LOCAL 42 · RUN 47 · OWNER 137 ·
SESSION 63 · BOTS 4), down from 406 at open. **172 closed, 52 filed.** The queue did not empty and
was never going to: the comprehensive sweep read 116 modules and filed what it found, which is the
sweep working. **The workable rung is 94 and every id is listed in §1 below**, so you start from my
position rather than rediscovering it.

---

## 0. READ THE MUTATION LOG FIRST — AND KNOW THAT THE LAST ONE DIED

`state/mutate_20260907.log` is the pass this run launched. **Read it before anything else.**

The run #45 pass (`state/mutate_20260905b.log`) **did not finish**. It completed two targets and
then died on the third:

| target | result |
|---|---|
| `assay.py` | 124 mutants, **122 killed, 2 SURVIVED**, 0 indeterminate (25,503s) |
| `prose_gate.py` | 62 mutants, **62 killed, 0 SURVIVED**, 0 indeterminate (18,632s) |
| `escalation.py` | **NO RESULT — the pass died here** |

It died at 23:20:47 with `FileNotFoundError` on **its own sandbox's** `escalation.py`. A pass killed
partway is not a pass with fewer survivors; a third of the mandate is missing. Full analysis is in
order **`f9643582fd29` (OWNER)**, including the hypothesis I **disproved by experiment** (a
10-hour-old sandbox with a live owner pid SURVIVES a full drill run — ownership beats age, as
designed) and the mechanism that does fit (`sandbox()`'s documented mkdtemp/claim window, order
`404d0ccf9df5`, whose stated mitigation is the 6h age gate that `older_than=0` removes).

Two things about the new pass:

- **The baseline is the cleanest this project has recorded**: `import rc=0`, `verify_math` **1159
  passed, 0 FAILED**, `drill` **443 nets, 443 held, 0 BREACHED**. All three green, and stronger
  than run #45's (405 nets, 1156 checks).
- **`_session`'s KeyError abort is fixed** (order `f4af474dfc49`, M75). It would otherwise very
  likely have taken this pass down too — that is why a maintenance run took a SESSION-rung order.

**Do not run `drill.py` while a mutation pass is live.** Both drill reap nets are now contained
(they redirect `tempfile.tempdir`, so they cannot see a real sandbox), but the window in
`sandbox()` itself is still open and is reachable from any `older_than=0` caller.

## 1. THE WORKABLE QUEUE — 94 ORDERS, EVERY ID

Nothing here is sampled. Work them cheapest-handler-first as always.

**MAJOR (26)** — start here:
```
05294ca33e1f 06b7f22484df 07258ace3a09 08c9ee5fb3bd 0922effae314 12c9a84b3b10 1e45fae97848
23dbbcd656f3 2461a04d8849 2cb8756deb0a 30854f11f322 4e5df284d5fc 58a00e909217 5b79deaaace9
77950336e3aa 85873effe631 8bd76479c64e a67d4b81f963 af47010df391 ca4f97d6b64d ced15f4f9d1f
d1113e987407 d17a7463a5fd dfa24eb10b9f eb4801a30501 fb5ac415e249
```
**MINOR (53)**:
```
036d9ca295ad 0c7592915a48 10dbef1a47d2 1d54acf05414 26b0e8cb30a1 2caa35dc6a30 2f07cbd3241d
3465775cc2ca 3dc2832846bc 475a06c19374 4ed4041c3b78 5156478c4583 5d14e90b5043 5ed00985ce04
690db2bf4f1d 70f5e5150f8b 749597eb95d4 76e870e21631 82adeee9b7ee 929622118156 9586cdf72b82
9b54659bc403 9da4543dc586 a5de2dcb9447 a66423722e45 a693102e217a a724ec57e0d5 ad681057369a
ad80146c36dc aefd1a2c9343 befb174bca20 bfafac3e1c5e c1d6ddfe148b c22c8b1f426c c54bb7d84622
c9146abf92df cdf0d2367cba cf861246e83e d015e0a139a8 d27e95a57233 d5155cb101df d56c041a8f4d
d7404ad383f1 d9fbd60efd0f e049b82ab858 e866d1520c16 ea1a063d75d6 ef26ed6029e7 f19f4a2b00f4
f5ffb9979a07 fe3dc98ca42e fe99e57e1993 ffdaa9aa7288
```
**INFO (15)**:
```
0058f581b42b 00a85c511b53 018727423a09 371140b9fb9d 57ab902a45ae 5c8c8b99e655 6273d7103222
764e283cdf00 83bf7498d135 9038da917a70 91bb70c85e31 93e73e0c59a6 e45618de083f ee382241ff8c
f646c1c5f1d0
```

### The sharpest of them, with why

- **`728d9e99e9ec`** (SESSION) and **`c1d6ddfe148b`**/**`d5155cb101df`** (RUN) — **this is the
  answer to the baseline-drift question that has dogged three mutation passes.** Six unwrapped live
  calls in `verify_math` write into `state/failures.json`, reddening §20z; a red baseline **cancels
  the whole mutation pass**. Worse, `dashboard.state()` calls `standards.check()` internally, so
  `standards.check()` runs **~15× per battery run**, each doing a real DNS+TCP connect, an Ollama
  generate with `timeout=300`, and a PowerShell spawn. That is also the non-determinism: `:4726`
  asserts on a live process-table enumeration that returns `None` on a loaded machine — i.e.
  exactly when a 20-hour pass is running. **Fixing this makes the battery deterministic and the
  next mutation pass trustworthy.** I did not take it because it is substantial surgery on the
  battery itself and the pass was already relaunched.
- **`2eabb417f58f`** (SESSION) — a drill net that **cannot fail**: `drill_codex_dedupe_is_typed`
  rebuilds the dedupe key itself and never enters `catalogue_codex`. Reverting the real fix leaves
  it green. Its sibling `2f07cbd3241d` is the staged withdraw_chapters net held back for the same
  reason. These are the highest-value class in the tree.
- **`dfa24eb10b9f`** (RUN) — `corpus_db.rebuild()` falls back to `{}` on a WIKI_HOSTS/COVERAGE read
  failure, which would make the **entire** catalogue read as hostless/unmeasured. The same function
  already fixed this for its spine resolver and left the two siblings.
- **`d1113e987407`** (RUN) — a source whose cleaned name is ≤2 chars (measured: only "DC") gets
  `known[src]=None` cached with **zero probes ever made**.
- **`5b79deaaace9`** (RUN) — `overwatch`'s filter silently drops all seven *"reconciliation
  failed"* rows from `WATCH.md`, the one file this project calls the only thing a person reads to
  learn what that job found. "A check that crashed is not a check that passed", left unguarded one
  tier down from where the same file already guards it.
- **`85873effe631`** (RUN) — the nine transparency fields added to `assay.py` this shift have
  **zero** coverage in `verify_math`, unlike their sibling `covers_all_signatures`.
- **`0922effae314`** (LOCAL) — `axis_correlation`'s `degraded` flag is **write-only**: a matrix
  built from 1-of-8 source files publishes as "measured" identically to a complete one, inside
  every published ±.

## 2. FOR THE OWNER — 137 OWNER + 63 SESSION, AND SIX ARE NEW

The run #45 digest (`handoff/OWNER_DIGEST_20260905.md`) still stands for the older ones; **I did
not decide any of them.** New this shift, in order of consequence:

1. **`f9643582fd29`** — the dead mutation pass (§0). Includes the mechanical remedy sweep46-batch04
   worked out: build the sandbox under a name that does **not** match `SANDBOX_PREFIX` and rename it
   into place only after the owner file is written, making it invisible to the reaper's prefix
   filter until it is already protected. That changes the reaper's contract, so it is yours.
2. **`895a99602bf0`** — what stops a *thirteenth* probe-litter site. Twelve are fixed; **four were
   found only by measurement**, and one was created by this very run while fixing the others. Three
   options with a recommendation. **Do not let it be closed by someone wrapping a thirteenth site.**
   Note the correction inside it: this order's own first draft recommended a drill-scoped remedy,
   which was wrong, because the ninth site was in `verify_math`.
3. **`58cfc2b6dbc4`** — `hostcheck`'s halt check fires at function entry, but the destructive write
   to the non-reconstructible `WIKI_HOSTS.json` happens only after a rate-limited network probe over
   the whole roll. A halt raised mid-probe is never re-checked before the write lands.
4. **`9fcbe25a473b`** — `pantheon`'s roster-gap marker prints a note but does not fail the run,
   beside a sibling total-failure case that was explicitly fixed to do exactly that. Looks like an
   incomplete repair rather than a decision, but it is a curatorial call.
5. **`5bbd4b3376fe`** — `generate.py`'s coverage checks string-match against the **whole** model
   response, which carries no think-tag stripping. A thinking model narrating its plan can satisfy
   them from reasoning text alone. Harmless only while `prose_enabled` is shut — and the configured
   model **is** a thinking variant (`342ccfafa4a4`, still open, still the sharpest thing on your
   list).
6. **`12c9a84b3b10`** — `local_agent.DENYLIST` does not cover `deprecated/catalogue_local.py`, whose
   entire safety is a textual refusal, so the model it was quarantined against could patch it out
   and pass every gate.

## 3. THINGS THAT ARE TRUE AND WILL WASTE YOUR TIME IF YOU FORGET THEM

- **Do not run a gate against a tree under edit.** It produced **three** false reds this shift
  (`verify_math` 980/1, then 979/2, then a `SCAN_MODULES` mismatch), each costing an investigation;
  tracebacks pointed at comment text because the file changed under the run. Two agents hit it
  independently. This is the mechanism that cost run #45 a halt. Queued as `71ae3fa7e55e` (OWNER);
  the mechanical half is `690db2bf4f1d` (RUN) — `mutate` infers "src/ is being edited" from the
  **maintenance guard's heartbeat**, which is wrong in both directions, while `codewatch` already
  computes the exact signal (a `src/` fingerprint).
- **The shell-injection mechanism bit three more times today.** Two sweep agents had order prose
  mangled by backtick command substitution while filing via `python -c`; both caught it by reading
  the stored record back and refiled from script files. **Then it bit me**, writing resolutions
  through a heredoc. `1c99df1f69c1` is closed and there is nothing left to patch in-repo — the
  remedy is the **wording of the session brief a coordinator writes**, and this run found the gap in
  its own brief: it told agents to use `--how-file` for **resolutions** and said nothing about
  `file_order` **prose**. Whoever writes the next brief should cover both. Use the Write tool and
  `--how-file`; never a heredoc, never argv.
- **An order left open behind a landed fix is re-diagnosed by every later sweep.** `de0681cb9edc`
  survived its own remedy this shift because the agent that fixed it never ran `--resolve`; I caught
  it only by re-checking the MAJOR list against source. If you fix it, close it.
- **`file_order`'s id is `order_id(code, where)`.** Widening `where` on a refile **mints a new
  order** rather than refreshing — it produced a duplicate I had to close by hand. Filed as
  `fb5ac415e249` (RUN, MAJOR): the behaviour is intended but undiscoverable.
- **`dashboard` spent its whole restart budget (4/4)** while twelve agents churned `src/`, so it ran
  stale on purpose for a period. That is the budget working (lag beats thrash), and it does reach a
  person via `escalation`. Expect it during any large fan-out.

## 4. THE SWEEP

**Sweep46 is complete and its coverage is falsifiable: 16 batches, 116 modules, 102,408 lines,
`sweep_plan.missing('run46') == 0`.** The plan was frozen at `state/sweep_plan/run46.json` *before*
dispatch, and each agent recorded its own coverage, because the agent is the only thing that knows
what it actually read. Audits: `handoff/sweep46/AUDIT_batch01.md` … `AUDIT_batch16.md`.

Batches 3, 11 and parts of 5/6/13 came back unusually clean and said so — several modules are now
heavily pre-audited and the honest finding was "already tracked, verified against current source,
not re-filed". That is worth as much as a new order and should not be read as a batch doing less
work.
