# sweep45 — batch 11

Read in full, no sampling: `workorders.py` (1,753), `overwatch.py` (991), `identity.py` (711),
`weave.py` (557), `backfill.py` (443), `retry_synthesis.py` (342), `catalogue_aurora.py` (324),
`scale_theories.py` (174), `compress_store.py` (149). 5,444 lines, all of them.

Read-and-report only. No source file was edited. Nothing from the battery was run; the standing
DRILL_BREACH halt was left alone.

---

## 1. The shell-safety code in `workorders.py` — what it does and does not do

Taken first, because it is new, it is a security boundary, and nothing had audited it.

### What holds (verified, so nobody re-checks it)

* **`--how-file` cannot crash and cannot close an order with an empty resolution.** The read at
  `:1574-1583` is inside a `try/except Exception`. A binary file raises `UnicodeDecodeError`
  (confirmed to be an `Exception` subclass by running it); an unreadable path, a directory or a
  permission denial raises `OSError`. Both land on
  `refused: --how-file %s could not be read ... NOTHING WAS CLOSED` and `return 2`. A file that is
  empty or all whitespace is caught one line later by `if not how.strip()` at `:1587`, also `rc 2`.
  A BOM survives into the resolution text but nothing else follows from it.
* **`--how` and `--how-file` together are refused** (`:1569-1572`), so the two channels cannot
  disagree.
* **The warning is reachable and correctly gated.** `via_argv` is `True` only when the text
  actually arrived as an argv string; `--how -` and `--how-file` both clear it. There is no path
  on which argv text escapes the check, and none on which file/stdin text triggers it spuriously.
* **No module in `src/` ever routes order text through a shell.** There is no `shell=True`, no
  `os.system`, no `os.popen` anywhere in the tree (`verify_math.py:4823` asserts this). The two
  `powershell -NoProfile -Command` call sites — `allsweep.py:610`, `foreman.py:1072` — carry fixed
  literal command strings with no interpolation. The remaining exposure is exactly the one
  `1c99df1f69c1` names: an agent typing the CLI into Bash.
* `resolve()` demands a non-empty resolution in the function as well as at the CLI (`:539-543`), so
  a Python caller cannot close an order blank either.

### What does not hold — filed as `ebdd80dc9e68` (LOCAL, MINOR)

`SHELL_ACTIVE` (`:117-124`) lists six tokens and misses the rest. Measured by calling
`workorders.shell_active` directly:

| input | reported |
|---|---|
| ``run `x` `` | 1 construct (correct) |
| `$(x)` | **2** constructs for one construct (`$(` and `$` both match) |
| `'x'` | **[]** |
| `a; b \| c & d\ne` | **[]** |
| `what!!` | **[]** |

The double quote is listed under the rationale *"ends the caller's own quoting and re-opens the
line to the shell"* — which is symmetric between the two quote characters, and single-quoting is
the more common way an agent wraps a remedy field. Command separators and redirections
(`;` `|` `&` `>` `<` newline) are how a broken quote turns one command into several, and history
expansion (`!`) is absent too. `main()` prints the list length as *"contains %d construct(s) a
shell acts on"*, which a reader will take as the whole answer; a resolution containing only
`; rm -rf x` is announced as inert today.

Filed in the same order, because it is the same forty-line block and the same edit session: the
`--how -` stdin read at `:1584-1586` is **bare**, while the identical read through `--how-file -`
at `:1574-1583` is wrapped. A stdin that raises on the first path gives a traceback instead of the
"NOTHING WAS CLOSED" refusal, in the one place a caller most needs that sentence.

---

## 2. Filed this batch, worst first

### `12aca83cab86` — RUN / MAJOR — a zero threshold merges every shelf into one continuity
`src/weave.py:256-273`, `:276-300`, `:319-352`; caller `src/pipeline.py:2783-2786`.

`components()` scores an absent pair `lookup.get((a, b), 0.0)` and merges on `m >= threshold`. At
`threshold == 0.0` every pair clears the bar — **including pairs with no shared entity and no edge
in `w`** — complete linkage degenerates and the agglomeration runs until all sources sit in one
cluster. `null_threshold_surprisal()` ends `return out[len(out) // 2] if out else 0.0`, and `out`
is empty whenever no trial produced a weight: no entity occurring in 2..60 sources (a fresh, small
or filter-emptied corpus), or `trials <= 0` (`weave.main`'s `--trials` has no floor).
`null_threshold()` has the identical tail.

`pipeline.phase_weave` computes that threshold and hands it straight to `components()`, then
`resolve()` fuses every repeated name inside the resulting group and lands `CONTINUITY_GROUPS`,
`RESOLVED_ENTITIES` and `RESONANCE_GRAPH`. That is the outcome this module's own docstring names as
the error it exists to prevent — Adventure Time's Earth and Alien's Earth as one planet — reached
not through chaining but through an unmeasured threshold, and it is silent: the log prints
`permutation threshold 0.0` and `1 continuities`, and nothing fails. `identity.py` states the
asymmetry that makes this the dangerous direction: two records left separate is recoverable, a
wrong merge is not.

`tiers.chart()` is **not** exposed — it passes the fixed `MULTIVERSE_THRESHOLD = 102.3`.

### `14c70c3782fd` — LOCAL / MINOR — battery evidence rows are cut, so no uncut copy exists
`src/workorders.py:255, :287, :289, :305, :307` vs `:310-314`.

`battery_faults()` builds its `bad` rows with `[:160]` (import detail, lint row, bad estate
artifact), `[:120]` (graded estate detail) and `[:160]` (bare estate finding), then files
`BATTERY_GRADED` with `evidence: bad` — the same already-cut list. The comment immediately above
that filing reads *"the count and the three are honest and labelled, the evidence is complete"*.
For `PREFLIGHT_PROBLEM` that is true (`:210` passes the whole `rows`); for `BATTERY_GRADED` the
evidence is complete in **count** and cut in **content**. A cap labelled as compliance is the shape
`weave.py:243-251` records as the worst kind. The field that loses most is the import detail — the
tier this file's docstring calls "the one that caught four dead modules". `cap_boundary_scan`
cannot see it: the cut happens before storage and lands at no 600/200/80/400 boundary. Third
instance in this file of composing a capped `what`/evidence one layer above `file_order`
(cf. `e6385a07a3fd`, `8dc37c208839`).

### `ebdd80dc9e68` — LOCAL / MINOR — `shell_active` reports six constructs and misses the rest
Detailed in §1 above.

### `5067df94c1d5` — LOCAL / MINOR — the rescue path gates on a truncated evidence string
`src/retry_synthesis.py:182-186` vs `src/pipeline.py:1479-1481`.

Retry does `ev = (...).strip()[:600]` and then `PL.valid_scale_note(ev)`. `phase_synthesis` does
`_ev = (...).strip()` — uncut — tests `valid_scale_note(_ev)`, and truncates only when it *stores*
the field. So evidence longer than 600 characters whose scale-evidencing fragment sits past
character 600 is accepted by the main phase and refused here: the source is shelved `unassayed` by
the tool whose job is to rescue it, and whose `method` string written into the record asserts
"same invariants as the main synthesis phase". This is the **fourth** instance of the drift this
function documents three of (prompt construction, transport, and `ceiling_band` vs `clean_band` on
the accepting side — order `46e3b6918dce`), each of the first three closed by taking the code from
`pipeline` rather than restating it. Remedy is one line: validate before truncating.

Deliberately distinct from `1f9a54bede08`, which names the same line but ruled the `[:600]`/`[:900]`
cuts *shape parity* with `pipeline.py` and explicitly **not** a divergence. This is not about the
stored field's length; it is that the two writers feed different strings to the same gate.

---

## 3. Corroborated, already open — not refiled

| order | what it covers | status against source |
|---|---|---|
| `1c99df1f69c1` | order text through a shell is executed | still open; §1 is the audit of the guard filed against it |
| `d4e2df7d7d6a` | `identity._is_continuity` final branch unreachable | confirmed: `MIN_BEARERS = 3` and the `n == 1` arm leave only `n == 2`, so `max(2, 0.5 * n)` is always `2` and the branch is exactly `shared >= 2` |
| `05f36eceaa9f` | `identity` epoch probe unmarked cuts (`[:1200]`, `[:60]`) | confirmed live at `:576` and `:589` |
| `92a9017a5d14` | `overwatch` auto-triage cuts the claim it judges and the reason it records | confirmed live: `[:400]`/`[:400]` at `:618-619`, stored `why[:300]` at `:632` |
| `1f9a54bede08` | `retry_synthesis` evidence/rationale cuts | confirmed live at `:182`, `:200` |
| `9586cdf72b82` | `backfill.lead` mid-word cut with no marker | confirmed live at `:145-152` |
| `fe99e57e1993` | unmarked name cuts incl. `backfill.py:364` | confirmed live (`x['source'][:52]`) |
| `01695fe3ef26` | `scale_theories` has no production caller | confirmed by search over all of `src/` incl. `src/deprecated/`: the only hits are prose mentions in `descending_ladder`, `drill`, `liveness`, `tempus`. `surviving_theory()`, `bulk_export_beta()`, `growth_strike()`, `penetration_pressure()` are called by nothing |
| `905f13a21f0c` + `e637c67ab438` | both describe `weave.null_threshold` dead code (`:275-299` / `:276-300`) | **twins** — one fault, two orders, two rungs (LOCAL/INFO and OWNER/MINOR). Flagged for the coordinator, not closed here |

**Candidate for closure / re-scoping — verify before acting:** `357e24fa2fa1`
(`WEAVE_MAIN_REPORT_CAPS`) names nine sites. Eight are gone from source: `multi[:12]`, `g[:4]`,
`[:8]` on the fusions ranking, `most_common(6)`, `attestations[:3]`, and the `[:26]`/`[:30]`/`[:18]`
name cuts are all now uncapped or are format-widths (`:<32`, `:<28`) that pad rather than
truncate. Only `names[k][:34]` at `weave.py:464` remains. I did not close or edit it.

---

## 4. Judged deliberate, or verified clean — not filed

* **`workorders._mutate`** — correct compare-and-swap through `silence.replace_if_unchanged`, temp
  name carrying pid **and** thread, refusal reason kept, never healing a `QueueUnreadable`. The
  paper-trail append goes through `silence.append_line` and turns a `False` into the exception its
  handler is written for. I found no non-atomic write to shared state in any of the nine modules.
* **`workorders.resolve`** — the deletion-before-append ordering and the land-then-exists test
  order are both right; the failed-append handler prints the id, the code and the full resolution
  to stderr, so the closure is re-enterable by hand.
* `backfill.lead()`'s 420-character window is an excerpt by design (a "lead"), with provenance
  stamped on every entry it writes; the mid-sentence case is already order `9586cdf72b82`.
* `overwatch._fingerprint`'s `actual[:80]` is a dedupe **key**; changing it would re-key the whole
  ledger. The file says so and is right.
* `identity.staleness`'s `_ = "silence-exempt: ..."` is a deliberate marker, not dead code.
* `catalogue_aurora.py` and `compress_store.py`: nothing found. Every write verdict is gated, every
  refusal reaches the exit code, `compress_store.load()` verifies the blob against the content
  address in its own filename and refuses rather than returning wrong text.
* `backfill.roster()` raising `RosterIncomplete` rather than returning a short list, and
  `missing.sort(key=lambda t: (t in sizes, -sizes.get(t, 0)))` ranking unmeasured titles with the
  deepest rather than below them, are both correct as written (I re-derived the ordering).
* No bare `except Exception:` in these nine modules returns without recording. Every one either
  notes and re-raises, notes and files under `DETECTOR_FAILED`, or notes and prints an actionable
  sentence. The nearest thing to an exception is `workorders.py:1012-1013`, whose fallback is a
  `silence.note` alone — but it is the last resort inside `_detector`'s own handler and is
  effectively unreachable, since `file_order` returns `None` rather than raising on a lost write.

*Coverage recorded via `sweep_plan.record('sweep45', [...], batch=11)`.*
