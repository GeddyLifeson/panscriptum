# Sweep 58 — Batch 07 audit

Modules read in full, top to bottom (line count = last line read):

| module | lines |
|---|---|
| src/workorders.py | 2425 |
| src/ledger_guard.py | 1062 |
| src/catalogue_web.py | 799 |
| src/endpoint.py | 611 |
| src/reference.py | 498 |
| src/retry_synthesis.py | 380 |
| src/resync_roll.py | 333 |
| src/halo.py | 220 |
| src/chord_field.py | 211 |

Open queue was checked first via `workorders.open_orders()` (103 open orders as of this read).
Matches against this batch's modules are called out below as `KNOWN <id>`.

---

## src/workorders.py (2425 lines) — audited hard, per the brief

### DEFECT MAJOR — `--check-closed` on an absent/mistyped directory reports a false "all clean"

`resolution_ids_in(dir_path)`'s own docstring promises: *"a missing or unreadable directory is
honestly empty, not an error ... `check_closed` below is the thing that has an opinion about
whether that is suspicious, not this."* Reading `check_closed`:

```python
def check_closed(dir_path, queue_path=None):
    resolved_ids = resolution_ids_in(dir_path)
    open_map = _load(path=queue_path)
    still_open = sorted(oid for oid in resolved_ids if oid in open_map)
    return {"dir": dir_path, "resolved_ids": resolved_ids, "still_open": still_open}
```

`check_closed` never calls `os.path.isdir`, never distinguishes "directory absent" from
"directory holds resolutions, all already closed" — the promised "opinion" does not exist. Both
cases return `resolved_ids=[]`, `still_open=[]`.

Reproduced live (read-only, no writes):

```
$ python src/workorders.py --check-closed handoff/sweep58/DOES_NOT_EXIST_TYPO
check-closed handoff/sweep58/DOES_NOT_EXIST_TYPO: 0 distinct order id(s) named by a resolution file
all resolved orders are closed in the queue.
EXIT=0
```

A shift that mistypes its own resolve directory (or points `--check-closed` at the wrong sweep's
folder) gets told the queue is clean and exits 0 — the exact "check that cannot fail looks
exactly like a check that passed" shape this module's own doctrine names, on the very feature
built to catch orders fixed-but-left-open (`KNOWN e114b2d0fe48`, below). **Remedy:** `check_closed`
should report `os.path.isdir(dir_path)` explicitly (e.g. a `"dir_exists": bool` field) and `main()`
should refuse or flag a `--check-closed` on a non-existent path rather than printing the same
"all resolved orders are closed" sentence a genuine clean run produces.

### DEFECT MAJOR — `file_order`'s cap-boundary refusal on a rerouted order's `found_by` reads a value the caller does not control, and can wedge that order + mask a whole detector section

New this shift, per the brief ("`file_order` / `reroute` refuse cap-boundary lengths"). In
`file_order`'s `_change`:

```python
_rerouted = (bool(prev.get("rerouted")) or " | rerouted " in str(prev.get("found_by") or ""))
...
_found_by = str(prev.get("found_by") or "") if _rerouted else str(found_by or "")
_refuse_cap_hit(oid, "what", _what)
_refuse_cap_hit(oid, "where", _where)
_refuse_cap_hit(oid, "found_by", _found_by)
```

For `what` and `where`, `_refuse_cap_hit` checks text the *calling* detector supplied on *this*
call — the remedy the docstring gives ("Shorten or rephrase the text by hand") is available to
that caller. For a **rerouted** order, `_found_by` is `prev.get("found_by")` — the value already
sitting on disk from a *previous* `reroute()` call, not anything the current `file_order()` caller
wrote. If that stored value ever sits at exactly 80 characters (the legacy `found_by` cap this
same order-class already produced once, per `LEGACY_CAP_BOUNDARY`/`cap_boundary_scan`'s own
history: 43 orders were found sitting at exactly these boundaries on 2026-08-29), then **every**
future `file_order()` refresh of that specific order id raises `BadOrder` inside `_mutate`, which
propagates out uncaught to whichever `sweep_detectors()` section called it. That section's
`try/except Exception` catches it and files `DETECTOR_FAILED` instead — which means the *entire*
detector block for that cycle (e.g. the whole `ledgers` section, LEDGER_STRUCTURE +
LEDGER_CHAIN) never runs its real checks that cycle, and the specific rerouted order can never be
refreshed (`last_seen`/`seen`/`what`/`evidence` all frozen) until someone hand-edits its stored
`found_by`.

`reroute()` itself is self-protecting (it applies the same `_refuse_cap_hit` to the string it is
about to *write*, so a fresh reroute can never land exactly on 80), so the trigger condition is
narrow today — it needs either a pre-existing legacy value at exactly 80, or a write that reaches
`found_by` through some path other than `file_order`/`reroute` (a hand edit, a restore). The live
queue currently has zero `found_by` values at length 80 (`cap_boundary_scan()["open_hits"] == []`,
checked), so this is dormant, not firing. But it is a real asymmetry the docstring does not
disclose: `_refuse_cap_hit` reads as "the caller can always dodge this by rewording", and for one
of its three fields on one code path, the caller cannot. **Remedy:** either don't apply the door
check to a value the current call did not produce (only check `found_by` when `not _rerouted`,
since `reroute()` already guards its own writes), or have `file_order` fall back to storing the
inherited `found_by` with a distinguishing suffix rather than raising when it is inherited and at
the boundary.

### DEFECT MINOR — `--check-citations` always exits 0, even when it finds provably stale citations

Its sibling flag, `--check-closed`, exits 1 when it finds a mismatch (documented: "Exits nonzero
when any are"). `--check-citations`'s handler in `main()` ends with an unconditional `return 0`
regardless of whether `findings` is empty:

```python
if findings:
    print("%d PROVABLY STALE citation(s) ...")
    ...
else:
    print("no provably stale citations found ...")
...
return 0
```

Both flags are new-this-shift additions addressing sibling orders (`dc9ffadae765` for citations,
`e114b2d0fe48` for closed-orders). Nothing calls `--check-citations` from automation today, so the
impact is bounded to a person reading stdout — but if this is ever wired into a gate that reads
the exit code (the way the rest of this project's doctrine treats exit codes as the channel that
actually matters — see `resync_roll.py`'s and `catalogue_web.py`'s own comments on exactly this),
stale citations would pass silently. **Remedy:** `return 1 if findings else 0`, matching
`--check-closed`.

### DEFECT MINOR — basename-only clustering in `twins()`/`where_targets()` can merge two different files that share a name

`where_targets()` normalises every cited path to its basename (`path.rsplit("/", 1)[-1]`),
explicitly to catch `publish.py` vs `src/publish.py` naming the same file. The project's own tree
currently has a genuine basename collision between two *different* files:

```
$ find . -name "*.py" | sed 's/.*\///' | sort | uniq -d
assay.py
$ find . -name assay.py
./handoff/nets_20260906/assay.py
./src/assay.py
```

(`handoff/nets_20260906/assay.py` is itself named as agent scratch under `KNOWN a66423722e45`,
`AGENT_SCRATCH_IN_PUBLISHED_TREE`, and has not been removed.) An order whose `where` cites
`handoff/nets_20260906/assay.py:NN` and one that cites `src/assay.py:NN` would both normalise to
`assay.py` and be reported by `twins()` under `file_clusters`/`file_line_clusters` as candidate
duplicates of the same fault, even though they name two unrelated files. No open order currently
triggers this (only one order cites any `assay.py` path today, verified via `twins()`), so it is
latent. `twins()` is advisory ("CANDIDATES, NOT A VERDICT... verify each against source"), which
limits the damage to wasted operator attention rather than a wrong auto-close, but the docstring's
own justification for basename normalisation doesn't anticipate two genuinely different files
sharing a name. **Remedy:** at minimum, `twins()`'s report should also show the full paths behind
each clustered id when they disagree, so a reader isn't misled into treating a same-basename hit
as automatically the same file.

### KNOWN e114b2d0fe48 (FIXED_ORDERS_LEFT_OPEN_AT_SHIFT_END) — the motivating order for `check_closed`/`--check-closed`

Still accurate as the general problem statement; the new tool is the intended remedy but see the
DEFECT above (absent-directory false-clean) in the remedy's own implementation.

### KNOWN dc9ffadae765 (THE_QUEUE_CITES_LINE_NUMBERS_AND_NOTHING_CHECKS_THEM) — the motivating order for `--check-citations`

Still accurate; the tool now exists and correctly scans `what`/`where`/`evidence` across every
open order via `citecheck`'s own resolver (no second copy of the stale-citation rule). See the
exit-code DEFECT above for a gap in the remedy.

### KNOWN 247586e57b61 (ESC_SANDBOX_DOES_NOT_STOP_RESOLVE_CODE) — `workorders.resolve_code` reached live by drill probes outside the sandbox

Not touched by this shift's changes to workorders.py (the fault is in `drill.py`'s sandbox
coverage, batch 1's area); `resolve_code()` itself is unchanged in any way that would close it.
Still accurate as read.

### KNOWN 54db4a3baec8 (SOURCE_PAGES_UNREADABLE_READ_AS_ABSENT) — appears already fixed on disk

This order is filed against `src/endpoint.py`'s `source_pages`, which agent R may be editing
concurrently this shift. As read just now, the fix is present: `source_pages()` raises
`PagesRegistryUnreadable` on an unreadable/non-dict registry rather than returning `[]`, and the
docstring documents it as the deliberate close of order 54db4a3baec8. Reporting as KNOWN/resolved
rather than DEFECT since the code on disk at read-time already matches the order's own remedy;
noting explicitly per the brief that agent R's concurrent edits mean this snapshot could change.

### KNOWN 1e6f99e54b25 (CORPUS_WRITERS_WITHOUT_A_HALT_INTERLOCK) — confirmed for both `retry_synthesis.py` and `resync_roll.py`

Neither file imports or calls `escalation`/`escalation.assert_clear` anywhere (grepped both full
reads by eye; no `escalation` reference in either module). `retry_synthesis.py --merge` writes
`data/records/*.json` via `PL.write_record` and `resync_roll.py` writes `data/SWEEP_ROLL.json` via
`roll.mutate`, both with no halt check before or during the write loop. Still accurate.

### KNOWN a5faab7f3ede (LEDGER_GUARD_FLOOR_RATCHETS_ON_LINE_COUNT) — confirmed, unrelated to this shift's changes

`seal()`'s floor-advance condition is still `sum(_substantive_lines(text).values()) >=
sum(_substantive_lines(floor_text).values())` — line-count-based, not content-preservation-based,
exactly as the order describes. `_handoff_journal_problems` (this shift's actual change) does not
touch this mechanism. Still accurate.

### KNOWN f27c121c6cb7 (CATALOGUE_WEB_STORED_TYPES_NEED_RECATALOGUE) — orthogonal to this shift's change

About stale `type` values already on disk from before an earlier fix to `catalogue()`'s category
provenance tracking; the code fix it references (order 6eb20e8d3565) is present and correct in the
`catalogue()`/`catalogue_composite()` read this shift (both use `first_cat.setdefault` to record
per-title provenance). The remaining problem is data already on disk, which `--recatalogue` is the
declared repair for — a repair action, not something to verify further here.

Nothing else found in the rest of workorders.py. Checked in particular: `_load`'s new `path=`
parameter (correctly read-only, never threaded into `_mutate`, so no writer can be pointed away
from the live queue); the WHERE_TARGET regex's 3 capture groups and `_span`'s min/max normalisation
(interval overlap test in `twins()` is a standard `s2.start <= s.end and s.start <= s2.end`, correct);
`resolve()`'s "did it land, then did it exist" ordering; `_mutate`'s digest-before-read discipline.

---

## src/ledger_guard.py (1062 lines)

### DEFECT MAJOR — `_handoff_journal_problems` (new this shift) cannot see an undated run-journal entry, which is exactly the historical fault class its own docstring names

The function's docstring cites the incident it closes: *"runs #51/#52/#37/#47/#48/#49 **and two
undated housekeeping notes**, fixed under this order."* But `_HANDOFF_ENTRY_HEADING` requires an
ISO date to match at all:

```python
_HANDOFF_ENTRY_HEADING = re.compile(
    r"^(#{1,2})\s+(?:RUN\s*#?\d+[A-Za-z]*\s*[-‐-―]+\s*)?(\d{4}-\d{2}-\d{2})", re.IGNORECASE)

def _handoff_journal_problems(text):
    ...
    for i, ln in enumerate(...):
        m = _HANDOFF_ENTRY_HEADING.match(ln)
        if not m:
            continue          # <-- an undated heading is skipped BEFORE the level check runs
        level, date_str, heading = len(m.group(1)), m.group(2), ln.strip()
        if level == 1:
            problems.append(...)
```

Reproduced (read-only): a level-1 `#` heading with no date — mirroring the "undated housekeeping
note" the order names — never matches, so `if not m: continue` skips it before the `level == 1`
check ever runs:

```
text = "... ## 2026-09-13 -- RUN #57 ... # Housekeeping: server migration notes ..."
_handoff_journal_problems(text) -> []
_HANDOFF_ENTRY_HEADING.match("# Housekeeping: server migration notes") -> None
```

So a `#`-heading housekeeping note appended at the bottom of `HANDOFF.md` with no date in its
title — the same fault shape three sweeps have now hand-caught (run #43, then this order) — would
sail through this brand-new check silently, because the check's own matcher requires the one thing
the fault-instance in question is missing. This isn't a hypothetical edge case; it's named
verbatim in the function's own commit history as a real instance of the class it exists to
prevent. **Remedy:** the level-1 (`#` instead of `##`) check should not require a date to fire —
it should test any heading that otherwise looks like a run-journal entry (e.g. any level-1 heading
appearing after the title line, dated or not), with the date-ordering check remaining
date-gated since ordering genuinely needs two dates to compare.

Checked and confirmed correct, not a defect: subsections that open with prose rather than a date
(`## CORRECTION TO RUN #48, WRITTEN 2026-09-09`) are correctly excluded from the sequence (the
regex requires the heading to *open* on the date/RUN-prefix, which "CORRECTION TO..." does not);
`_handoff_journal_problems` is wired only for `name == "HANDOFF.md"`, correctly excluding
`handoff/HANDOFF.md` (a doctrine/architecture reference, not a dated run journal — confirmed its
headings are topical, e.g. `# LOOK`, `# ASSAY`, `# CORPUS`, not run entries); the unicode dash
character class `[-‐-―]` correctly spans the common em/en-dash code points used in the live file.

### KNOWN e8675703f045 (HANDOFF_RUN_ENTRIES_APPENDED_AT_THE_BOTTOM_AGAIN) — the motivating order; largely closed, see DEFECT above for the residual gap

The dated/level-1 case this order's primary incident describes (runs #51/#52 at the bottom under
`#`) is correctly caught by the new function. The undated-note sub-case named in the same order's
own text is not — see above.

Nothing else found. `check_structure`, `check_since_snapshot`, `check_since_floor`, `seal`,
`verify_chain`, `read_chain`/`_read_chain_lines`, and the acknowledgement machinery are unchanged
by this shift's diff and were re-read in full without finding a new defect; their extensive
in-file commentary already documents the faults they were built to close.

---

## src/catalogue_web.py (799 lines)

### KNOWN e7143aba1e9a (WIKI_SOURCE_FLOOR_REPORT_HAS_NO_CALLER, finding 1) — FIXED this shift, verified

`main()` now calls `ws.category_floor_report()` after the catalogue pass and prints an uncapped
report (`catalogue_web.py:774-779`). Confirmed the call is signature-compatible:
`wiki_source.category_floor_report()` takes no arguments and returns a list of dicts with exactly
the keys `catalogue_web.py` reads (`subdomain`, `categories_above_floor`, `floor`, `note`), and the
returned list is never sliced (`for (sub, floor), n in sorted(_FLOOR_APPLIED.items())` — no cap).
The order's finding 2 (`rank_by_size` fetch, also in `wiki_source.py`) is out of this batch's scope
and not addressed here.

Nothing else found. `catalogue()`/`catalogue_composite()`'s per-title provenance tracking
(`first_cat`), dedup-with-disambiguator, `save_roll`'s key-wise compare-and-swap via
`roll.update_rows`, and `main()`'s exit-code handling (`return 1 if todo and tally["failed"] else
0`) were all re-read in full; no new defect found beyond the wiring already covered above.

---

## src/endpoint.py (611 lines)

### KNOWN 54db4a3baec8 — see workorders.py section above (cross-listed since this is the file the order names)

`source_pages()` raises `PagesRegistryUnreadable` rather than returning `[]` on an unreadable or
non-dict `SOURCE_PAGES.json`, matching the order's remedy. Agent R may be editing this file
concurrently this shift, so treat this as a snapshot.

Nothing else found. `_save()`'s merge-not-overwrite compare-and-swap (mirroring `register()`'s),
`detect()`'s DEAD_TTL re-probe logic, `fetch_raw`/`fetch_html`'s refusal-vs-absence distinction,
and the eaten-regex-escape self-check at the top of the file were all re-read in full with no new
defect found.

---

## src/reference.py (498 lines)

Nothing found. Hand-built calibration module (Goku/Naruto/Luffy Assay reconstructions against the
charter's published intervals), not named in this shift's change list and not touched by it.
Checked `shelfmark()`'s upper/lower rung clamp against `RUNGS`' length (correct for all three
current entries, 3+4=7=len(RUNGS)); `main()`'s write-verdict handling and the RC that now carries
both "write denied" and "calibration outside" as one `RC_BROKEN`-class exit code (deliberate, per
its own comment); the eaten-regex-escape self-check.

---

## src/retry_synthesis.py (380 lines)

### KNOWN 1e6f99e54b25 — see workorders.py section above

Confirmed no `escalation` import/call anywhere in this file.

Nothing else found. `save_side`'s re-read-then-merge-then-write pattern, `do_merge()`'s per-source
`PL.write_record` gate and uncapped unmerged-source reporting, and `synthesise()`'s use of
`PL`'s own block/prompt/band-acceptance/evidence-cut helpers (rather than restated copies) were
re-read in full with no new defect found. Not named in this shift's change list.

---

## src/resync_roll.py (333 lines)

### KNOWN 1e6f99e54b25 — see workorders.py section above

Confirmed no `escalation` import/call anywhere in this file.

Nothing else found. The exclusion-guard re-check on the fresh row inside `_apply` (not the
snapshot), the `dry`-run argparse fix, and the exit-code plumbing (`sys.exit(main())`) were all
re-read in full with no new defect found. Not named in this shift's change list.

---

## src/halo.py (220 lines)

Nothing found. Hand-authored Assay module for three Halo entities (Precursors, Gravemind,
Ur-Didact); same family and same already-fixed shape as `reference.py`/`zfighters.py`/`wh40k.py`
per its own comments (per-axis provenance tags, wrapped-not-cut `--full` display, gated
`write_json` with an honest non-zero exit on a denied replace). Not named in this shift's change
list and no new defect found.

---

## src/chord_field.py (211 lines)

Nothing found. Pure physics/math module (no I/O, no file writes, no CLI, no concurrency) backing
the setting's "Chord" power-unification doctrine. Checked the four numeric functions for
correctness: `landauer_floor` (bits·k_B·T·ln2, correct Landauer bound), `recoil_momentum` (E/c,
correct for p ≥ E/c), `recoil_velocity` (non-relativistic p=mv, consistent with its own
"if momentum conserves in 3-space alone" framing), and `critical_power_self_focus` (Marburger's
self-focusing formula, 3.77·λ²/(8πn₀n₂), matches the standard constant). Not named in this shift's
change list.

---

## Coverage stamp

Recorded via `sweep_plan.record("run58", [...], batch=7)` for exactly the nine modules listed in
the header table above (all read in full this session).
