# Panscriptum run #48 comprehensive code sweep — batch 04

**Modules read (full, in successive chunks, no sampling):**

| module | lines read | lines in file |
|---|---|---|
| src/mutate.py | 1-3146 (all) | 3146 |
| src/catalogue_web.py | 1-786 (all) | 785 |
| src/build_terminal.py | 1-668 (all) | 667 |
| src/reference.py | 1-498 (all) | 497 |
| src/burgs.py | 1-433 (all) | 432 |
| src/resync_roll.py | 1-333 (all) | 332 |
| src/scale_theories.py | 1-216 (all) | 215 |
| src/chord_field.py | 1-211 (all) | 210 |

No edits made to src/ (read-only, as instructed; a mutation-testing pass was running
concurrently). `mutate.py` itself was read only, never executed.

Every finding below is a **stale citation** (defect class 6). I looked hard for classes 1-5
(unfireable checks, fail-open silence, lost updates on roll writers, unmarked Hard-Rule-0 caps,
and mutate.py sandbox-escape paths) across all eight modules and found nothing I could verify as
a live defect in any of those classes — see the "read and found nothing wrong in" section. The
two roll writers in scope (`catalogue_web.save_roll`, `resync_roll.main`) both go through
`roll.update_rows` / `roll.mutate` (compare-and-swap), matching the standing requirement.

The citation drift below turned up in unusual volume — six confirmed instances across five of
the eight files, several of them inside comments that were *themselves written to complain about
a previous stale citation*. Reporting all of them because the pattern (not just one instance) is
the finding: this codebase's own convention of citing `file.py:NNN` in prose is losing the race
against ordinary editing, including in exactly the comments most concerned with getting it right.

---

## Finding 1 — MINOR — mutate.py:731-732, citations to verify_math.py and drill.py are stale

**What's wrong.** `_row_ids`'s docstring says:

> Both gates already print the row identity on its own line ... verify_math with
> `  FAILED <label>: got ..., want ... <note>` (verify_math.py:7990) and drill with
> `  BREACHED  <net name>` (drill.py:9604).

Neither line number points at the code described.

**How I verified it.**
- `verify_math.py:7990` is inside a `check(...)` call about instrument windows (`_iw_msg_gone`
  assertion), unrelated to printing. The actual `print(f"  FAILED {_lbl_vm}: ...")` statement
  that produces the row format described is at **verify_math.py:142**.
- `drill.py:9604` is inside `a_resume_over_an_unreadable_ledger_writes_nothing`'s `probe()`
  function (writing `ESC.STOPPED` to `"[]"`), unrelated to printing breach rows. The actual
  `mark = "HELD    " if r["held"] else "BREACHED"` / `print("  %s  %s" % (mark, r["net"]))` pair
  that produces the described row format is at **drill.py:15909-15910**.

**Proposed remedy.** Update the two citations to verify_math.py:142 and drill.py:15909 (or
switch to a content-based tag, as `reference.py:246` and `wiki_source.py` already do elsewhere
in this tree for exactly this failure mode, per the comment at reference.py:242-246).

---

## Finding 2 — MINOR — mutate.py:884, 1421, 2216, citation to escalation.py:409 is stale (repeated 3×)

**What's wrong.** Three separate places in mutate.py's docstrings and comments cite
`escalation.py:409` as the site of the mutation `landed, why = False, "not attempted" -> True`,
the confirmed false kill central to the `_refresh_baseline`/re-photograph mechanism's design
rationale (e.g. line 1421: "the one CONFIRMED false kill on record: `escalation.py:409` was
scored KILLED by a 16.3-hour run and SURVIVES cleanly when re-attacked in a fresh sandbox").

**How I verified it.** `escalation.py:409` currently reads:
```
    UNLOCKED, exactly as it did before this function existed, and the failure is noted.
```
— a line inside an unrelated docstring about halt-write locking. A grep for the literal
mutated source text, `landed, why = False, "not attempted"`, finds it at **escalation.py:495,
567, and 1226** (three separate functions carry the identical line, so the citation is now
ambiguous as well as wrong). Functionally harmless — the actual suppression/ruling mechanism
(`_order_identity`, `ruled_equivalent`) keys off the *current* line number reported by a live
mutation run, never off this prose citation — but the citation itself no longer supports the
claim it is used to argue for a reader checking it by hand.

**Proposed remedy.** Either drop the line number and cite by content/order id only (order
`58a00e909217` is already given alongside it and is sufficient to find the incident in the
journal), or update all three occurrences to name which of the three current sites (495/567/1226)
the false kill was actually re-attacked against.

---

## Finding 3 — MINOR — catalogue_web.py:193, citations to catalogue_codex.py:361 and resync_roll.py:211 are stale

**What's wrong.** `save_roll`'s docstring says every roll writer "now lands through
`roll.update_rows` / `roll.mutate` (catalogue_codex.py:361, resync_roll.py:211)".

**How I verified it.**
- `catalogue_codex.py:361` is inside `dupe_elements.setdefault(...)` in the local-register
  dedup logic — nothing to do with the roll. The actual `roll_landed, roll_why =
  _roll.update_rows(roll_changes, path=ROLL)` call is at **catalogue_codex.py:480**.
- `resync_roll.py:211` is a blank comment line between two comment blocks. The actual
  `landed, why = _roll.mutate(_apply, path=ROLL)` call is at **resync_roll.py:248**.

**Proposed remedy.** Update to catalogue_codex.py:480 and resync_roll.py:248.

---

## Finding 4 — MINOR — build_terminal.py:647, citations to catalogue_codex.py:315-331 and generate.py:700-706 are stale

**What's wrong.** The comment justifying `return 1` on a denied terminal write says this is
"exactly what `catalogue_codex.py:315-331` and `generate.py:700-706` already settle the other
way in this same tree, both citing `module_index.py` as the shape."

**How I verified it.**
- `catalogue_codex.py:315-331` is inside the manifest-building duplicate-element loop (the
  `pair in seen` / `unmapped_types` block), not a denied-write handler. The actual
  `write_json`-denial-to-`return 1` handling in that file is at **catalogue_codex.py:496-507**.
- `generate.py:700-706` is inside the per-job evidence-cache loop (`_ev_cache[src] =
  PG.evidence_ok(...)`), not a denied-write handler either. The nearest matching "refuse loudly,
  return 1" sites in that file's `main()` are at generate.py:679 and 693 (evidence-floor
  refusals); the save-path's own denial handling (`silence.note("generate.py:save-denied")`) is
  at generate.py:144-149, and its docstring says the eventual nonzero exit is applied in
  `main()`, not at 700-706.

**Proposed remedy.** Update both citations (catalogue_codex.py:496, generate.py roughly
679/693) or drop the specific line numbers and keep only the module names, since the point being
made ("this shape is settled elsewhere in the tree") doesn't need exact lines to stand.

---

## Finding 5 — INFO — burgs.py:353, self-citation to ":300" is stale

**What's wrong.** The comment explaining why a world's `designation` must not be truncated in
the sample-table header says "not even a unique one, see the collision note at :300".

**How I verified it.** burgs.py:300 is `import address_space as AS`. The actual "collision
note" — the block explaining that 47 of 5,986 worlds share a `designation` with another world
(order 65ae84ee4bd7) — is at **burgs.py:317-326**.

**Proposed remedy.** Update the self-citation to ":317" (or drop the line number and cite the
order id, `65ae84ee4bd7`, which is unambiguous and line-number-proof).

---

## Finding 6 — INFO — scale_theories.py:52-53, citation to descending_ladder.py:49 is stale

**What's wrong.** The docstring explaining why `G_NEWTON`/`C_LIGHT`/etc. stay duplicated rather
than centralised says: "`descending_ladder.py:49` carries a comment cross-referencing
'scale_theories.py names the same value as G_NEWTON'".

**How I verified it.** descending_ladder.py:49 is a blank line inside that module's own
docstring (between "left for the next sweep to re-derive." and "Nothing in `src/` imports it").
The actual cross-referencing comment ("scale_theories.py names the same value as G_NEWTON") is
at **descending_ladder.py:94**, attached to that module's own `G_NEWTON` declaration at line 91.

**Proposed remedy.** Update the citation to descending_ladder.py:94 (or 91, the declaration
line the comment sits beside).

---

## What I read and found nothing wrong in

- **mutate.py** end to end (all 3,146 lines): the lock/staleness machinery (`active`,
  `_lock_acquire`, `_lock_release`, `_hold_lock`, `_pid_alive`/`_pid_alive_windows`), the
  sandbox builder (`sandbox`, `reap_orphans`, `_owner_pid`, `_touch_root`, the `data/`
  hardlink-vs-junction split, the BUILDING_PREFIX rename-in trick), the mutation generator
  (`_mutations`, `_between`, `_token_pos`, `_find_op`, dedup logic), gate running and
  differential judging (`_gate_result`, `could_not_judge`, `hang_confirms_a_kill`,
  `_refresh_baseline`, drift recording), the ruled-equivalent registry
  (`ruled_equivalent`/`rule_equivalent`/`ruling_mismatch`), `file_orders`, and `main`/`_session`'s
  CLI flow. All of the module's own historically-fixed defects (root==HERE refusal, missing
  baseline refusal, TIMEOUT==TIMEOUT false kills, the b248f8f706d3/f9643582fd29/f40f701594a4
  orders, etc.) are in fact fixed as described, verified by reading the current code rather than
  trusting the comment. I did not find any additional unfireable check, fail-open silence, or
  sandbox-escape path beyond what the module's own extensive commentary already documents as
  historical incidents now closed.
- **catalogue_web.py**: `save_roll` correctly routes through `roll.update_rows` (compare-and-
  swap, key-wise merge by `names`), not a whole-document write — matches the requirement.
  `_singular()`, the MAX_PER_SOURCE/MAX_PER_CATEGORY tripwires, the dry-run and `--recatalogue`
  paths, `catalogue()`/`catalogue_composite()`'s provenance and dedup bookkeeping, and `main()`'s
  exit-code handling (order 1e45fae97848 / ea1a063d75d6) all check out. The previously-filed cap
  at `r['name'][:44]` (order fe99e57e1993) is fixed (now printed uncut at line 687); I did not
  find any other unmarked truncation of an operator-facing identity in this file — the `[:16]`/
  `[:28]` truncations on canonical-class labels (`canon.split(" (")[0][:N]`) are over a small,
  fixed, code-defined vocabulary of 7 categories (Persons, Places & Locations, etc.), not a
  dynamic roster, so Hard Rule 0 does not appear to bite there.
- **resync_roll.py**: `main()` correctly routes the actual write through `roll.mutate` (compare-
  and-swap over freshly re-read rows), not the stale in-memory `roll` snapshot. The
  out-of-scope exclusion guard, the unreadable/malformed-record handling, the duplicate-source
  handling, and the exit-code fix (order 8605c2ed6061) all check out.
- **build_terminal.py**: the `<script>`-injection neutralisation (`data.replace("<",
  "\\u003c")`), the `esc()` JS helper and its use across `shelfmark`/`panel`/`selectSource`/
  `selectWorld`, the atomic write with denial handling, and the `--help`-must-not-rebuild fix
  all check out.
- **reference.py**: the Assay reconstruction, `shelfmark()`'s NAVTREE-unreadable-vs-genuinely-
  unknown distinction, `card()`'s inside/outside-interval check, and `main()`'s
  write-denied/calibration-outside exit-code logic (order d049dbbfed6e) all check out.
- **burgs.py**: the rank-size derivation, the `--limit` narrowing-only fix (order 1bc825e806a9),
  the designation-collision handling (order 65ae84ee4bd7), and the parameters-not-rosters
  storage design (order 47e4e1ace8f1) all check out.
- **scale_theories.py** and **chord_field.py**: both are small, deliberately-unwired "held"
  modules (owner ruling 2026-09-08). `surviving_theory()`'s exactly-one-survivor assertion is a
  real, fireable check keyed on the `falsified` boolean field rather than on `falsified_by`
  prose (its own docstring documents the earlier version of this same defect class, already
  fixed). No caps, no roll writes, no silent excepts in either file.
