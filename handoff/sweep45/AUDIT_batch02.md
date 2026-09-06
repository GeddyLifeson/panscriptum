# sweep45 — batch 02 — `src/verify_math.py`

**Scope:** the whole file, and only that file. No source file was edited.

## What was actually read

All **9,885 lines**, in eleven contiguous chunks covering 1–900, 900–1800, 1799–2698,
2698–3597, 3597–4496, 4496–5395, 5395–6294, 6294–7193, 7193–8088, 8088–8987, 8987–9886.
No sampling, no head, no "top N". Every section from the `--help` short-circuit at :16
through `_print_result_vm()` at :9883 was read.

**The file did not change under me.** `md5 e44ed3d1d971c62be36dea30e8883437`, 597,564 bytes,
9,885 lines at the start of the read and identical at the end of it. If another agent is
editing this file tonight, it had not landed an edit during this window.

Verification of claims was done against source, never from memory:

* an AST `Call`-node scan over **all 116 `*.py` under `src/`, including `src/deprecated/`**,
  for production callers of the functions the battery exercises;
* AST scans of `verify_math.py` itself for `check()` rows whose `got` and `want` share a
  source segment, whose `got` is a bare constant, and which sit inside an `if`/`else`;
* direct reads of `src/standards.py`, `src/dashboard.py`, `src/sevenfold.py`,
  `src/mutate.py`, `src/withdraw_chapters.py` and `state/read_auto.log` to confirm or kill
  each candidate.

Nothing on the forbidden list was run: no `drill.py`, no `verify_math.py`, no `allsweep.py`,
no `publish.py`, and no attempt to touch `state/HALT.json`.

---

## Findings filed — worst first

### 1. `74f1bc47da2a` — MAJOR / SESSION — a second set of rows rides a live third party

`src/verify_math.py:5573`, `:7146-7154`, `:7651-7686`

The order the coordinator most wanted: **another row of the section-20z shape**, in a
different section, unwrapped. `verify_math` calls the **live** `standards.check(
dashboard.state())` at five sites. That function opens a TCP connection to
`marvel.fandom.com`, posts a generation to `localhost:11434` with a 300-second timeout, and
shells out to PowerShell — and it carries about **28 `_dropped.append(...)` handlers**, each
of which *deletes* its standard's row when that standard's input read raises, plus one
further gate at `standards.py:1897` (`if flow is not None:`) that drops a standard with no
`_dropped` entry at all.

`verify_math.py:7148` then asserts `declared − emitted − exempt == []` with **exactly one**
name exempted. Any of those ~29 paths firing reddens the row.

It has already happened, and the file records it in its own comment at `:7578-7583`:
*"Measured inside one shift on 2026-08-29/30: 46 declared / 46 emitted, then 46 / 43"* —
caused by an unrelated process exhausting the machine's ephemeral ports. Note the
arithmetic: **46 − 43 is three rows missing, and only two were named and fixed.** The class
was never closed.

The second site (`:7651-7686`) is worse in one specific way: its own note claims set
comparison *"can't be fooled by an unrelated standard flapping between the two check()
calls"*. That is not so — a standard that emits in the clean run and drops in the second run
lands in the set difference and reddens the row. The note vouches for an immunity the check
does not have.

Filed to SESSION rather than RUN because deciding *which* drop paths are facts about this
library and which are facts about the machine is a judgement, not an edit. The machinery to
express it already exists in this file: `_third_party_vm` at `:340-364`.

### 2. `7099a092abd3` — MAJOR / OWNER — the battery is the only caller of thirteen public functions

The prompt's second precedent shape (`codewatch._record_restart`), measured rather than
asserted. AST scan of every `Call` node in all 116 modules including `src/deprecated/`,
counting a caller only outside `verify_math` / `drill` / `liveness` / `mutate` /
`secondopinion`:

| function | call sites | production callers |
|---|---|---|
| `assay.band_for_quantity` | 6 | **0** |
| `assay.null_instrument` | 2 | **0** |
| `assay.interval_from_hands` | 8 | **0** |
| `tempus.retrocausality_beta` | 3 | **0** |
| `tempus.contemporaneous` | 1 | **0** |
| `tempus.is_present_at` | 2 | **0** |
| `tempus.prescience_horizon_bits` | 6 | **0** |
| `ledger.cross_rate` | 2 | **0** |
| `ledger.to_standards` | 2 | **0** |
| `ledger.from_standards` | 1 | **0** |
| `ledger.assay_to_standards` | 4 | **0** |
| `cosmography.kardashev_K` | 2 | **0** |
| `cosmography.kardashev_to_magnitude` | 2 | **0** |

Their near siblings were checked and **do** have production callers, so they are excluded:
`ledger.work_value` (`ledger.py:170`), `tempus.loop_report` (`pipeline.py:2497`),
`tempus.apparent_lag_years` (`pipeline.py:2472`), `tempus.band_resolution` (`rigor.py:150`),
`assay.regress_test` (`grounding.py:237`), `assay.calibration_report` (`dashboard.py:637`),
`assay.axis_score` (17 sites). Roughly thirty battery rows measure the thirteen above.

Two things make it an owner ruling rather than a note:

* **`verify_math` contradicts itself.** Its comment at `:2144-2148` says of the three assay
  functions: *"They survive because they NEVER RUN … Those are left for the owner's ruling on
  deletion rather than propped up with tests."* Section 20r, added later, props all three up
  with about **fifteen** tests (`:6540-6554`, `:6624-6644`, `:6682-6686`).
* **Open order `1a9c237dda4d` stands on the opposite reading and is addressed to the owner.**
  Its `evidence.siblings_all_read` lists eight of these thirteen as *read*, citing
  `verify_math.py` line numbers as the readers, and its method line says so outright:
  *"verified_by: grep -rn over all *.py INCLUDING verify_math.py and drill.py."* Counting the
  battery as a caller is the exact confusion this project has already paid for.

### 3. `2f0a734d8c15` — MAJOR / RUN — a check that cannot fail, testing a parser it built itself

`src/verify_math.py:8729-8736`

```python
import argparse as _ap36, datetime as _dt
_ap_probe = _ap36.ArgumentParser()
_ap_probe.add_argument("--label", default=_dt.date.today().isoformat())
check("withdraw_chapters --label no longer hardcodes 2026-08-25",
      _ap_probe.parse_args([]).label != "2026-08-25", True, ...)
```

`verify_math` **never imports `withdraw_chapters`** — the name appears only in the
section-20p `_INTERLOCKED` tuple at `:6023`, the section banner at `:8713`, and this row's own
label. The parser under test is one this file constructs three lines earlier with a default
it supplies itself, so what is asserted is that **today's date is not the string
`"2026-08-25"`**. That was already true when the row was written, and the one calendar day it
could have failed on is in the past.

`withdraw_chapters.py:176` is currently correct — the property holds. What does not hold is
the claim that the battery keeps it: revert that line to a literal and the row stays green
for ever. Same class as `96c4be60fb92`, `8a6d86040d10` and `ff470a877ac5`, all repaired in
this file already.

### 4. `a93bd62a7c5f` — MAJOR / RUN — three section-20k rows ride the reader's log file

`src/verify_math.py:5573-5588`; `src/dashboard.py:225-250`

`dashboard._read_row` appends the `"corpus read"` job **only** when a tail line of
`state/read_auto.log` matches `RE_READ` (`dashboard.py:61-65` — nine named groups on one
line). There is no `else` branch. `verify_math.py:5584` then asserts that job's `dropped` is
an `int`, and `:5579` that the fabrication standard is measured rather than `UNMEASURED`.

They pass **today** only because the log happens to hold a matching line (checked 2026-09-05).
A fresh checkout, a log rotation, a malformed tail line, or a reader stopped by
`foreman.kill_stalled_job` — which section 20a of this same file documents as routine, at 42
minutes of downtime measured in run #18 — turns three rows red for a reason no source edit
can fix. Not a case for deleting the rows: section 20k exists because that guard was absent
for its whole life. The wrong thing is the tier.

### 5. `b4af486851af` — MINOR / RUN — a conditional row, and an unscoped `path` lookup

`src/verify_math.py:7967-7979`

The only genuine conditional row I found that is **not** already covered. The second check is
guarded by `if call_idxs:`, so if `mutate.py`'s call is ever spelled differently the row that
actually protects the live tree (that the restored path is the sandbox copy, not `SRC`)
**vanishes** rather than reddening — the green-by-absence shape section 20r retired at
`:6771-6779` (order `c8704a41a70f`). Second fault in the same twelve lines: `assign = next((l
for l in reversed(lines[:i]) if l.strip().startswith("path = ")), "")` walks backwards through
the **whole module**, not the enclosing function, so an unrelated `path = ` anywhere above
silently redirects the assertion. That is the scope confusion `_own_nodes20p` (`:6167-6191`)
and order `6a8444cad673` each fixed in this file on the same day; the helper is present and
unused here.

### 6. `58ec389036d7` — MINOR / RUN — "shelving is deterministic" is `f() == f()`

`src/verify_math.py:1489`

Compares `SF.build()` to `SF.build()` inside one process. This file has already ruled that
shape insufficient three times with the reason written beside each — orders `3f86c571da58`
(map_seed), `fbdb7fe3bd4c` (assign), `cc500a6cbf4b` (`_chunk_key`) — and the repair
(`_asfresh`, an independently exec'd second copy of the module, `:1239-1251`) is in the file.
It is not hypothetical: `sevenfold.shelve` uses `set(members)` (`sevenfold.py:86`) and
`sorted(set(cuts))` (`:214`), and section 19n of this same battery records that
`PYTHONHASHSEED`-dependent set ordering really did rename **75 of 734** navtree nodes between
two runs on identical inputs. A within-process comparison is blind to precisely that. Sibling
of the same shape at `:1550` (burg seeds).

### 7. `ddae3747d37d` — MINOR / RUN — two rows skip silently when ruff/vulture are absent

`src/verify_math.py:8024-8046`. `_b4_secondopinion_checks` prints `(skipped …)` and returns,
emitting **no row at all**, so a run in which the two outside-opinion assertions never ran is
indistinguishable from one in which they passed. Green-by-absence, refused twice by name in
this same file (`:5556-5588`, `:6771-6779`). The gate is also narrower than the condition it
stands for — it reads the `Scripts` directory of *the interpreter running the battery*, and
this machine has several.

### 8. `d43a5a050c0f` — MINOR / RUN — the last unmarked swallow in the file

`src/verify_math.py:284-285`. `_ledger_counts_vm` answers `except Exception: return {}` with
no `silence.note` and no `silence-exempt:` declaration — the two forms this file states as
doctrine three times (`:2358-2362`, `:5076-5079`, `:7285-7293`). Order `3fa9f4ac0265`'s
inventory of every `ExceptHandler` here missed it because it is not a cleanup handler.
Consequence: an unreadable `state/failures.json` makes the section-20z growth banner print
nothing, so *"the ledger did not move"* and *"the ledger could not be read"* render
identically. Deliberately **not** to become a failing row — order `c121db910a17` settled that
another program's fault must not redden this battery.

---

## Corroborated, not refiled

| open order | what I saw |
|---|---|
| `23dbbcd656f3` ("conditional fallback checks") | Still standing at `:6698-6704`: `if _stamp.startswith("FALLBACK"): … else: …`. `A._rho_source()` reads `measured:` in normal operation (asserted at `:2159-2161`), so the FALLBACK row never executes in the configuration the library runs in. Its property *is* separately covered unconditionally at `:6832-6843`, so the live risk is low — but it is the shape, and it is the order's. |
| `1e83e387cfc1` (hardcoded anti-vacuity floor `_guarded20e >= 20`) | Eight siblings of the same instrument survive: `_used20q >= 12` (`:6368`), `len(_tags20y) >= 55` (`:9343`), `_toln20z >= 60` (`:9624`), `_seen20zn >= 30` (`:9823`), `len(_all_via) >= 1` (`:4965`), `_fm20a.count("os.kill(") >= 3` (`:4045`), `len(_run35_files) == 6` (`:8841`). This is the instrument the file itself **retired** at `:5534-5545` (order `ba7b55d6465f`) for reporting a count where a name was needed. |
| `5a0c4196142f` (source-substring checks) | Many remain; `_b4_verify_restore_checks` (finding 5) is one of them, as are the `"return rc"` / `"rc = 1"` pair and the `AUTH_BENCH = 4 \* 3600` regex at `:4924`. |
| `7a379f99fe80` (unmarked truncation in diagnostics) | Confirmed live at `:8884` (`str(_label36)[:70]`), `:8872`/`:8885` (`[:200]`), `:8858` (`[:160]`), `:5760` (`[:60]`), plus `(res.get("sample") or [])[:3]` at `:8357`. |
| `06b7f22484df` (`codewatch._record_restart` has no production caller) | Confirmed independently by the same AST scan. The battery keeps the old row at `:7364` **and** added the `_claim_restart_slot` companion at `:7375` — the right resolution, and it is what finding 2 above asks for the other thirteen. |
| `28c1f58f5e8a` (six unspliced `handoff/run35/checks_*.py`) | Confirmed: `checks_F1/M1/M2/M3/M4/SO.py` exist beside the six `checks_L*.py` that section 20u globs at `:8840`. |
| `44539ab9be89` (cross-type module-level rebind at `:8407`) | Confirmed; the `_a`/`_b` rebind in the `itertools.combinations` loop is still there at `:8801`. |

## Judged deliberate design — read, and not filed

* **`_raises`, `_json_try`, `_refuses_cap`, the `§20a` SIGTERM probe and the two cleanup
  handlers** each carry either `silence.note(...)` or an explicit `"silence-exempt: …"`
  string. Every one was checked individually; only `_ledger_counts_vm` (finding 8) lacks both.
* **`check("probe: a non-numeric got against a float want", None, 1.0)` at `:5251`** and the
  two `check(…, False, True)` rows at `:8884`/`:8887` have bare-constant `got` arguments. All
  three are deliberate failure-reporting rows and are scrubbed from the tally at `:5246-5258`.
  Not tautologies.
* **No literal tautology survives.** An AST scan for `check()` rows whose `got` and `want`
  share a source segment returned empty, and the disarm detector at `:5284-5313` covers the
  `or True` family with both controls.
* **`_third_party_vm`, `_no_ledger_vm`, `_spy_record_vm`, `_spy_flush_vm`** and their five
  `[control]` rows at `:9430-9524` are sound, two-sided, and exercise their own wrappers. The
  abstention banner is the right pattern; findings 1 and 4 are asking for it to be pointed at
  two more dependencies.
* **`handoff/run35/checks_L*.py` executed at `:8845-8889`.** Eighteen `.py` files live under
  `handoff/`, which is copied to a public repo. That is a `handoff/`-hygiene question about a
  directory this batch does not own, and section 20u's use of them is deliberate and
  fail-closed at every step. Recorded here rather than filed against `verify_math.py`.
* **`:8123`** carries a comment with a hole in it — *"Spliced into `src/verify_math.py`, so
  IS a file in src/"* — a token appears to have been lost in a merge. Cosmetic; noted, not
  filed.
