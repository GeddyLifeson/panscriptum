# AUDIT — sweep47, batch 01

**Module:** `src/drill.py` (13,742 lines) — the only module in this batch.

## Coverage

Read in full, every line, in fourteen contiguous passes:
1–1000, 1000–2000, 2000–3000, 2999–3999, 3999–4999, 4998–5998, 5998–6998, 6997–7997,
7997–8997, 8996–9996, 9996–10996, 10995–11995, 11995–12995, 12994–13743.

**No line range was skipped.** The overlapping offsets are read boundaries, not gaps.

Structural checks run against the file (results below under *Clean*):
all 41 module-level `drill_*` area functions, all 433 `net()` call sites, the
`main()` roster, and every numeric source citation in the file.

---

## Findings filed

### 1. `_publish_never_swallows_a_missing_safety` enumerates one exception NAME — MAJOR
The net's stated invariant is "no missing safety is swallowed on the way to a public push",
and it is the guard over `publish.push()`'s three interlocks (`ledger_guard.assert_intact`,
`mutate.active`, `escalation.assert_clear`). It walks each `ExceptHandler`, collects the
`Name` nodes in `handler.type`, and `continue`s past any handler where the literal string
`"ImportError"` is absent — so `except ModuleNotFoundError`, which is a *subclass of
ImportError* and is the exception Python actually raises for a missing module, is never
examined at all. A bare `except:` (type is `None`) is skipped by the same line.

**Measured, not reasoned.** A copy of the live `src/publish.py` with all four
`except ImportError as …` handlers respelled `except ModuleNotFoundError as …` returned
**True**; the same copy with the `raise` in the `mutate` handler neutralised also returned
**True** — a handler that swallows the mutation interlock's own absence, reported HELD.

This is the "enumeration where a shape is needed" family. The sibling net in this same file,
`_meta_ban_has_no_fall_through`, already argues the correct form in as many words
("`except ModuleNotFoundError`, `except (ImportError, AttributeError)`, or a bare `except:`
would each pass it while reopening exactly this hole") and asks the shape instead — every
handler on the guarded `try` must END the iteration. That form transfers here directly.

### 2. `main()` returns 0 when the run's own verdict did not land — MAJOR
`main()` writes `state/drill_last.json` through `silence.write_json`, checks `landed`, prints
a WARNING when it is False — and then falls through to `return 0`.

The warning goes nowhere the supervisor reads. `overnight.safety_drill()` captures stdout and
logs only lines beginning `DRILL:` (plus `BREACHED` lines when rc==1); it treats
`returncode not in (0, 1)` as "DID NOT COMPLETE — the nets were NOT inspected this cycle", and
rc==0 as a clean inspection. So a cycle in which the verdict never reached disk is logged as a
normal pass while `workorders.sweep_detectors` and `dashboard.safety` go on grading the
PREVIOUS run's `drill_last.json` as current — which `main()`'s own comment calls
"the 'green check that never ran' shape with a longer fuse".

This file enforces exactly the opposite property on another module: the net
`a_hand_raised_halt_that_did_not_land_returns_nonzero` exists because (order a1addbdff907)
"a person who deliberately halted the library was told on stdout that they had, with a success
rc for any script watching, whether or not the file ever appeared."

Not a mechanical change — `overnight`, `foreman` and `mutate` all read this rc, and
`mutate` grades mutants by difference from a baseline — so it needs a run that checks the
callers, not a one-line edit.

### 3. Two nets byte-compare live shared ledgers across a window — MAJOR (false-halt risk)
`a_probe_leaves_the_failure_LEDGER_alone` snapshots `state/failures.json` as **bytes**, runs
two probes, flushes, and requires the file byte-identical. `health.py`'s own commentary calls
that file "the highest-traffic shared file in the project", written under compare-and-swap by
concurrent flushes from many processes; any of the standing jobs calling `silence.note` inside
that window moves it. A breached drill net escalates to OWNER — so an unrelated recorder doing
its job halts the library.

`a_probe_leaves_no_order_behind` has the same shape one ledger over: it compares
`set(workorders._load())` and `_rows_in(CLOSED_LOG)` before and after, so a *different*
detector filing an order in the window breaches it.

Both docstrings reason about the masking direction ("an unrelated detector filing one order
while this probe leaked one would net to zero") and close it by comparing identities/bytes —
which opens the false-alarm direction instead. The file already carries the ruling this
collides with, at `twin_detection_does_not_match_bystanders`: *"A net whose answer depends on
what happens to be running when it looks is not testing the code."* It has cost a false halt
here twice before (run #31, and the mutation-sandbox breach).

### 4. `_live_walk` reads code after a non-breaking `while True:` as reachable — MINOR
`_live_stmts` truncates a statement list after an unconditional `Return`/`Raise`/`Break`/
`Continue`, and handles `if False:` / `if True:` / `while False:`. It does **not** truncate
after a `while True:` that contains no `break`, `return` or `raise` — a loop that cannot
terminate. Everything after it is provably dead and is fed to every net built on `_live_walk`.

**Measured:**
```
def f():
    while True:
        the_real_behaviour()
    the_guard_that_can_never_run()
```
`_live_walk` returns both names. This is the exact class repaired in sweep43-batch01 for the
`while True: … else:` spelling ("dead code read as reachable … the direction that matters"),
arriving through the loop's fall-through instead of its `else`. Latent today — no such shape
exists in `src/` — and it is shared infrastructure under ~two dozen "the call is made" nets.

### 5. Six numeric source citations have drifted — MINOR
The file carries a standing convention (order 0c7592915a48, quoted eight times in it) to cite
by SYMBOL because "a line number drifts the first time something is edited above it". Ten
numeric citations remain; six of them are provably wrong against the tree as it stands:

| citation | where it sits in `drill.py` | what is actually there |
|---|---|---|
| `drill.py :506-513` | `_failed_revert_is_escalated` | `_static_truth`'s docstring — the quoted `_calls(..., reachable=True)` passage is ~:716 |
| `drill.py :7942-7946` | `_failed_revert_is_escalated` | `the_keeper_asks_before_restarting` — the `bodies` list it names is ~:11916 |
| `autostart.py:395` | `publish_foreman_and_overwatch_refuse_to_run_beside_a_twin` | the `claim_singleton` ruling is at `autostart.py:416` |
| `assay.py` "line 947" | `a_nil_axis_is_narrower_than_an_unscored_one` | the missing-covariance comment, not the nil/unscored partition |
| `assay.py` "line 802" | same net | a warning string, not the dispersion branch |
| `assay.py` "L1392" | `the_covering_guarantee_holds_and_says_what_bought_it` | the MOmega docstring, not `covers_all_signatures` |

Verified as still correct and left alone: `coverage.py:53`, `feats.py:159`, `anchors.py:427`,
`withdraw_chapters.py:216-219`, `liveness.py:12`.

### 6. `the_ignore_file_names_the_same_class` asserts a third of the class — INFO
`publish._CODE_EXT` now holds ten-plus suffixes (`.py .pyw .pyi .sh .bash .zsh .ps1 .psm1 …`,
orders e7e00ffde6c5 / 749597eb95d4) and `gitignore_lines()` derives its patterns from that
tuple × `CODE_FREE_DIRS`. The net hard-codes six `.py`-family patterns. Its own expectation
says "two layers enforcing DIFFERENT rules is one layer and a decoy" — the layers agree today,
but the net cannot see them stop agreeing for any suffix outside the `.py` family, and its
sibling net one above it *does* assert `.sh`, `.ps1`, `.bat` and `.js`.

## Questions filed (not defects)

### 7. `drill_clean_description_is_idempotent` swallows an unreadable record
`except Exception: continue`, with the comment "an unreadable record is estate.py's finding,
not this net's". Two nets in this same file were explicitly repaired away from exactly that:
`_policy_corpus_clean` ("a bare `except Exception: continue` scored an unreadable or
unparseable record as clean … it now fails the net") and `excluded_sources_keep_their_records`
(order a531ac23d07c, same swallow, same remedy). Whether the deferral to `estate.py` is a
deliberate divergence from that precedent, or an instance of it that has not been swept yet,
is not recorded anywhere.

### 8. `_twins_ignores_a_foreign_tree` grades a probe it could not stage
It spawns a child and polls `codewatch.twins()` for up to 20 s; if the child never becomes
visible — a loaded machine, an AV scan holding the exe, a `Popen` that failed — `seen` is
False, the net returns False, and `main()` escalates a breached net to OWNER. The file's own
ruling for a probe that could not be staged is NOTE, don't grade
(`_junction_out_of_the_writable_surface`, order ef0b67732a3b; and
`datasette_config_is_generated_not_copied`, order 5eea5c20db8a: "a measurement that did not
happen must not be graded either way"). This is the same shape as
`twin_detection_does_not_match_bystanders`' own subject — a net whose answer depends on the
live process table — surviving in the sibling net beside it.

---

## Clean — checked and found sound

* **Every area runs.** All 41 module-level `drill_*` functions appear in `main()`'s roster;
  nothing is rostered that is not defined; no area was found with a `net()` call sitting in
  unreachable code (checked with the module's own `_live_walk`).
* **No orphan nets.** No inner function defined inside an area is left unreferenced — there is
  no net that was written and never wired.
* **No empty expectations.** All 433 `net()` call sites carry a non-empty expectation string.
  The defect order 6e7ecf6b9fbd was filed for — twenty nets printing a name and nothing else on
  a breach — **is fixed**, both in the printer and in the data.
* **`_no_programmatic_clear`** exempts by relative path, not basename, as its docstring
  promises: `deprecated/escalation.py` would not exempt itself.
* **`_a_scan_can_tell_code_from_prose_about_code`** drives all five documented bypass classes,
  including the bound-name alias chain.
* Probe-litter discipline is thorough: twelve `_deliberately_failing` sites, each with the
  measurement that found it, plus `_quietly`, `_quiet`, `_sweep_probe_litter` and the
  `synthetic=True` closer.
* Redirection discipline (`_ledger_redirected`, `_esc_sandbox`, the `tempfile.tempdir`
  containment on both reaper nets) is complete for the paths those modules write.

## Not re-filed
The sixteen orders already open against `drill.py` were checked against the file; none of them
reads as already fixed, and none is duplicated above. The two closest calls:
order a5de2dcb9447 (`DRILL_NO_CAPS_NETS_DRIVE_THE_WRONG_BRANCH`) is correctly still open — the
mixed feat-bearing/feat-less short-circuit in `synthesis_blocks` is still an unstated selection
rule, and the net's docstring says so; order 864a626a258e (`CLAUDE_MD_DRILL_NET_COUNT_STALE`)
is confirmed real — CLAUDE.md still says "attacks all 57 nets" against 433 call sites.
