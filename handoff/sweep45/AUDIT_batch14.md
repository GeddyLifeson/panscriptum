# sweep45 — batch 14

**Read-and-report only. No source file was edited.** The DRILL_BREACH halt was left standing;
no battery tool (`drill.py`, `verify_math.py`, `allsweep.py`, `publish.py`, `mutate.py`) was run.

## Coverage

Every line of all eight modules was read. No sampling (Hard Rule 0).

| module | lines | read |
|---|---:|---|
| `src/hostcheck.py` | 1458 | all |
| `src/escalation.py` | 1112 | all |
| `src/completeness.py` | 795 | all |
| `src/thread_integrity.py` | 627 | all |
| `src/address.py` | 477 | all |
| `src/hosts.py` | 393 | all |
| `src/recover_folder_records.py` | 286 | all |
| `src/profile.py` | 264 | all |
| **total** | **5412** | |

Recorded via `sweep_plan.record('sweep45', [...], batch=14)`.

Every grep hit reported below was opened and confirmed to sit on a **code** line, not on a
comment documenting a repair. Two of this batch's files (`address.py`, `profile.py`) carry long
comment blocks quoting the exact defective code they replaced, which is the trap the coordinator
warned about; it is also what let seven stale orders be identified (§4).

## 1. Filed, worst first

### cd76813c39bc — MAJOR / RUN — a failure to RECORD an escalation is not itself reported
`src/escalation.py:184-199` (`_append_log`), `:254` (`escalate`)

`_append_log` writes the janitor's rung in two places and returns one verdict: `ok = _append(LOG,
...)` at `:194`, then the per-source append at `:196-198` whose bool is **dropped entirely**, then
`return ok`. `escalate()` discards even that — `:254` is a bare `_append_log(rec)`.

This is the exact defect already repaired at the rung above and the rung below. OWNER carries
`halt_landed` on the record (`:306-307`) because "the verdict used to stop one frame short of
here"; MANAGER carries `stop_recorded` (`:620`) "exactly as `halt_landed` does one rung up".
JANITOR / OPERATOR / SUPERVISOR / SAFETY carry nothing — and those are the four rungs where the
log *is* the whole enforcement, because they neither raise nor write a state file. `_append`'s
own docstring insists its bool is truthful and `drill.py:8067-8090` has two nets proving it. That
truthful answer travels one frame and stops.

`health.record` and `WO.file_order` are two further landings, but both sit under
`except Exception: silence.note(...)`, so a locked `state/` directory loses the escalation at
every landing and still hands back a record that reads as filed.

Remedy is purely additive and modelled on its two siblings: return both verdicts, set
`rec["recorded"]`, and — mirroring the `HALT_NOT_RAISED` corroboration at `:309-318` — say so on
stderr when it is False, since by construction it cannot be said in the log.

### d66e629ae3ca — MAJOR / RUN — the aboutness veto fails open at zero article bodies
`src/hostcheck.py:375-376`, `:716-718`, `:736-737`, `:754`, `:756-759`

`relevance()` returns `(None, 0)` when no article body could be read (`if not bodies: return
None, 0`). `_bodies()` returns `[]` both when the wiki served no revisions and when the request
**raised** (its own `except Exception: silence.note("relevance-wikitext")`), so a throttle or a
403 lands here. `score()` then guards *both* veto branches on `r["about"] is not None`, so with
`about=None` neither fires and the verdict falls to lift alone — `holds` or `partial`, both inside
`JUDGED`, so `sweep(--repair)` and `adopt()` will keep or promote the host.

The ordering is inverted against the file's own ruling. `ABOUT_MIN` was added by order
44ae72489678 for n=1 and n=2, and the comment at `:738-753` says verbatim: *"Letting the veto
simply not fire hands the verdict to lift alone, which lands on `holds` or on `partial` … an
unmeasured host would still have gone to the repair pass."* Two bodies read → UNREACHABLE, host
left alone. **Zero** bodies read → veto skipped, host judged `holds`. Strictly less evidence buys
strictly more permission.

It only fires where the veto is *due* — `:716-718` calls `relevance()` only when
`base >= ABOUT_VETO_ABOVE` — i.e. on the generous, encyclopedia-class hosts the veto exists for.
The distinguishing value is already on the row (`about_n == 0` for "asked and got nothing" vs
`None` for "not asked") and the verdict never reads it.

### 8dfba71f73c3 — MAJOR / RUN — the ASYMMETRIC-SUSPECT floor is announced without checking it landed
`src/thread_integrity.py:187-191`, `:198-203`; reported at `:599-614`

`_floor_verdict` writes `state/THREAD_INTEGRITY_FLOOR.json` twice and gates on neither.
`silence.write_json` returns False and never raises on a denied replace — the ordinary case here,
and the reason run #37's discarded-verdict pass gated six other modules.

The baseline arm is the fail-open one, **and it is a release gate**. If the baseline write never
lands, the file stays absent, every later run re-enters the `FileNotFoundError` arm, re-baselines
to whatever it measured that day, and returns `"baseline"` — so `REGRESSED` (`:609-614`), the only
outcome this function exists to produce and the only one that reddens the exit code for
`allsweep`, can never fire however far the count grows. Meanwhile stdout prints
*"recorded as the Phase 4.2 baseline"*.

Live, not latent: `data/THREADS.json` exists (1,130,546 bytes, 2026-09-01 11:34) so
`recorded is not None` on every run. `state/THREAD_INTEGRITY_FLOOR.json` exists today, so the
current exposure is the ratchet arm's false *"ratcheted down"*; the baseline arm goes live the
moment that file is lost or cleared — exactly when the gate matters. The same function already
has the fail-closed precedent one branch up (`:192-194`, "the regression gate cannot be judged.
Fail closed.").

### 77950336e3aa — MAJOR / RUN — the tool that irreversibly deletes mined evidence never asks about the halt
`src/hostcheck.py` main() and every writing path

`grep -c escalation src/hostcheck.py` is **0**. No entry point calls `assert_clear`, and
`hostcheck.py` is absent from `verify_math._INTERLOCKED` (`src/verify_math.py:6022-6023`).

`--purge --source NAME --go` empties `entries` in matching `data/records/*.json` and then
`os.remove()`s every cached page under `data/feats/<host>/` and `data/readfeats/<host>/` — the
only supporting evidence for the entries being removed, one-way. `--repair` and `--adopt` rewrite
`WIKI_HOSTS.json`, which this module itself calls one of the two files "confirmed not
reconstructible from anything else on disk" (`:96-98`).

The precedent is exact and already ruled on: order bd107a18b13e filed `withdraw_chapters.py` as
*"the one tool in its batch with an irreversible action and the one not calling `assert_clear`"*,
after which it was wired, added to `_INTERLOCKED`, and given a behavioural net
(`drill.py:7935-7969`) that runs `--go` on purpose.

**Half of this is a question.** A read-only `hostcheck` sweep or `--rosters` audit is a
measurement, and this project has ruled that a measurement which cannot be retaken is abandoned
rather than deferred (`completeness.host_reachable`). So the filed proposal is narrow: gate
`--purge --go`, `--repair` and `--adopt --go`; leave the dry runs and the read-only sweep ungated.
Gating the whole `main()` instead is one line and the owner's call.

### 6c3092103415 — MINOR / LOCAL — `--only` announces a file it deliberately did not write
`src/completeness.py:718-720`, `:787`

`land()` was given a third outcome, `SKIPPED_ONLY` (`:660`), whose docstring says a caller that
needs to tell "wrote" from "declined on purpose" can check `is True` / `is SKIPPED_ONLY`.
`main()` is that caller and checks only `if not land(...)`. `SKIPPED_ONLY` is truthy, so the run
continues to `:787`'s unconditional `print("-> " + OUT)`. On a `--only` run stdout ends naming the
whole-corpus file as this pass's output while stderr said one screen earlier that it was not
written. Two streams disagreeing on one console is the specific failure `escalation.main()`'s
`--clear` arm carries its repair note for. Nothing is lost — the rows on disk are the correct
whole-corpus ones — but a distinguishing value that was built, documented at length, and then not
consulted by its only caller is one the next reader deletes as unused.

### ea31ea2ba72b — MINOR / LOCAL — Hard Rule 0: `profile.py:220` cuts the designation
`print(f"\n  {r['designation'][:56]}")` in `main()`'s SAMPLE block. A **code** line, verified —
not one of this file's comments about a removed cap. The designation is the world's identity
(`build_all` keys genre and tier off `designation.split("::")[0]`), and the `::<continuity>`
suffix that distinguishes two worlds of one source sits at the *end*. Three other files in this
same batch already carry the fix and quote it — `recover_folder_records.py:256`, `hosts.py:370`,
`hostcheck.roster_audit` — and `completeness.main()` sizes its column from the data instead. Eight
rows are printed; there is no width cost worth the identity.

### c70cd8bb9f7f — INFO / LOCAL — seven open orders already repaired in code
See §4. Filed for verification-and-closure only; nothing in `src/` is to change for it, and this
audit did not close them, because closing an order is a judgement and this was a read-only sweep.

## 2. Corroborated, already open — not refiled

- **4b69c225dbb6** `hosts.py:102` — `hosts_for`'s primary filter excludes only the `pages:`
  sentinel, not `doc:`. Confirmed on the code line; `completeness.SENTINELS` next door is the
  two-element form and `health.py`/`binding_health.py` both use the pair.
- **2c8e55f8f3f7** `address.py:390-393` — `tier_rank` returns 0 for an unknown tier, the same rank
  as `volume`, so `promote()` cannot tell a corrupt tier from the lowest real one. Confirmed.
- **946153deafe9** `completeness.py:122-129` — `category_size` has no caller. Confirmed: only its
  own `def` and two docstring mentions.
- **3fb312a72435** — `hosts.py` has no caller anywhere in the pipeline. Confirmed by reading; the
  module is finished, self-consistent and unreferenced.
- **d2da5914da94** `completeness.py:533-534` — `work()`'s `if not sizes and failed == 0: return
  None`. Still the open question; both readings stand.
- **729c26e0e63c** `recover_folder_records.py:140` — `_declared_count` unpacked and never read.
- **9954fb56d0e3** `recover_folder_records.py:226-227` — in-memory mutation of the snapshot row.
- **07258ace3a09** `address.py:151-169` — the opens/closes-the-title exception. Confirmed live.
- **a67d4b81f963** — the halt-lift path is unreachable from every automated gate. Not refiled.
  I looked specifically for *another* path in `escalation.py` that no gate can reach and did not
  find one: `_safe_name`, `_halt_file_records`, `_unreadable_halt`, `_read_halt_raw`,
  `halt_landed`, `HALT_NOT_RAISED`, `_write_stopped`'s CAS refusal and the stop-unlanded recheck
  are all netted in `drill.py` (`:2302-2400`, `:7626-7660`, `:7787-7880`, `:8007-8110`,
  `:8155-8180`, `:8229-8390`). The one hole left is cd76813c39bc above, which is not an unreached
  path but an unread verdict.
- **ddb5eadd8934** — the 20-vs-12 character ruling-length discrepancy. **Deliberately left open
  for the owner; not refiled and not touched.**

## 3. Deliberate design, examined and not filed

- **`escalation.clear()`'s refusal of programmatic callers.** Read closely and left entirely
  alone. `_by_a_person_at_the_cli`'s two conditions are correct and the ordering of refusals
  (ruling first, caller second) is load-bearing for two drill probes, as its own docstring says.
  Nothing here should be relaxed, and no finding in this report proposes weakening it.
- **`escalate()` resolving an unrecognisable rung to MANAGER rather than OWNER** — order
  762256b4b844 covers the reasoning; the argument in the comment is sound (a misspelling must not
  be a denial of service).
- **`hostcheck.sweep(--repair)`'s `best[0] > LIFT_MIN`**, which the comment itself admits nothing
  passing `ok` can fail. Kept on purpose — "the gate should state the bar even when the bar is
  already met" — and it is a floor, not a check that pretends to measure something.
- **`hosts.discover`'s `if not res:` at `:278`**, self-declared unreachable and kept loud with a
  `silence.note`. Correct: it is a canary, not a dead guard.
- **`hostcheck._PROSE_ONLY_GOOD_RATE`** — dead, renamed rather than deleted, and the name now says
  it. No action.
- **`_read_stopped` / `_read_halt_raw` fail-closed arms** — checked for a fail-open edge; both
  answer wrong-shape JSON the same way they answer unparseable JSON, which is right.
- **`completeness._cs_put`'s ungated write** — the comment explains why the verdict is genuinely
  ignorable (12h scratch cache, nothing else reads it, retry pressure would land on a domain that
  has IP-banned this machine). Agreed; deliberately distinguished from 8dfba71f73c3, where the
  ignored verdict belongs to a release gate.
- **`hostcheck.purge`'s `landed` gate on cache deletion** — correct as written: a denied record
  write leaves the cache files in place rather than deleting evidence out from under entries that
  stayed.

## 4. Stale queue: seven open orders whose code no longer exists

Each verified against the current source. Filed as c70cd8bb9f7f for someone to confirm and close.

| order | claims | current code |
|---|---|---|
| 7b9d3605a8a4 | `address.py:39` `_FILLER` has six untestable entries | `:55` is the six reachable entries only |
| c6ca8a8f8e55 | `hosts.py` `--discover` prints `str(src)[:39]` | `:370` `print("  %-40s + %s" % (str(src), ...))` |
| b1612dc92424 | `recover_folder_records.py:253` `{name[:48]:50s}` | `:256` `{name:50s}` |
| ed46a60bc2dc | `profile.py:109` regex admits `i l o u` | `:90-92` class built from `B32` |
| 559b09f35e5c | same line, same defect | same fix |
| 6f1652a21efb | same line, same defect | same fix |
| b9ff8dbf2c77 | `profile.py` round trip returns 0 regardless | `:256-260` returns 1 on any failure |

The three `profile.py:109` filings — the queue's largest twin cluster — are one line and one edit.
Reproduced independently: with `B32 = "0123456789abcdefghjkmnpqrstvwxyz"` (32 symbols, no
`i`/`l`/`o`/`u`), the current pattern rejects `PS-i23-myc-0000-u0`, `PS-l23-…`, `PS-o23-…` and
`PS-u23-…` and accepts `PS-123-myc-0000-u0`. The comment block at `:72-89` names all three orders
as the reason for the fix.
