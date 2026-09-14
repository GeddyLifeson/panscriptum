# Sweep 58 — Batch 10 audit

Modules read in full (top to bottom, offset-paged where needed):

| module | lines |
|---|---|
| src/publish.py | 2107 |
| src/rigor.py | 1132 |
| src/derivation.py | 811 |
| src/secondopinion.py | 704 |
| src/address.py | 539 |
| src/cleanup.py | 448 |
| src/descending_ladder.py | 357 |
| src/cosmology_graph.py | 260 |
| src/whoruns.py | 159 |

Open queue checked first via `workorders.open_orders()` (scratch script under
`scratchpad/sweep58/check_orders.py`) before any finding was written up.

---

## src/publish.py (2107 lines)

This shift's three stated changes were verified against source, line by line, not assumed from
the brief:

1. **`main()` checks `maintenance_shift_live()` on any `--push`, not only `--loop`.** Confirmed at
   `main()`'s cycle body: `if a.loop or a.push: _busy, _why = maintenance_shift_live(); ...`. The
   one-shot arm (`if _busy and not a.loop:`) reads the guard via `runguard.read(MAINTENANCE_GUARD)`
   and calls `_one_shot_push_verdict(_rec, a.i_hold_the_guard)`, refusing (`return 1`) unless the
   verdict allows. Traced all three cases of `_one_shot_push_verdict` (digest match / legacy
   `--i-hold-the-guard` assertion / refusal) against `runguard.TOKEN_DIGEST_KEY` and
   `runguard.token_matches`, both of which exist and match the expected shape. No defect found;
   this correctly implements order `12d4e1b00c2f`.

2. **`main()` returns `rc` after the loop.** Confirmed at the final `return rc` (line 2102), reached
   only via the halt-arm's `break` (which sets `rc = 1` first). Before this fix a halted daemon fell
   off the end of `main()`, returned `None`, and `sys.exit(None)` exits 0 — a halted publisher
   reporting success to its supervisor. Now correctly exits 1. No defect found.

3. **`_scrub` recurses into tuples and sets.** Confirmed at lines 383–386:
   ```python
   if isinstance(obj, tuple):
       return tuple(_scrub(v) for v in obj)
   if isinstance(obj, set):
       return {_scrub(v) for v in obj}
   ```

   **DEFECT MINOR** — the new set-handling silently drops collisions. `_scrub`'s own dict-key
   branch, four lines above this new code, explicitly guards against two keys redacting to the
   same string (`if sk in out: sk = "%s#%d" % (sk, len(out))`) precisely because collapsing two
   distinct entries into one is a silent loss. The new `{_scrub(v) for v in obj}` for sets applies
   no such guard: if a snapshot ever carries a `set` of, say, two different long API-key-shaped
   strings, `_scrub_line`'s `_vendor` substitution replaces *both* with the literal string
   `"[redacted]"`, and building a Python `set` from `{"[redacted]", "[redacted]"}` silently
   collapses two elements into one — the count of distinct secrets present is lost with no marker,
   the same failure shape the adjacent dict-key fix (order b1147f53971e) was written to prevent, one
   paragraph earlier in the same function. Concrete scenario: `_scrub({"tok1sk-aaaaaaaaaaaaaaaaaaaa",
   "tok2sk-bbbbbbbbbbbbbbbbbbbb"})` (a hypothetical set-valued snapshot field holding two distinct
   secrets) returns a set of length 1. Not live today — the module's own comment says "no live field
   exercises this today" for tuple/set generally — so this is filed MINOR rather than MAJOR, but it
   is a real, demonstrable gap in code newly written this shift, immediately beside the fix for the
   identical problem in the sibling (dict) branch. Remedy: convert to a list (or apply the same
   `#%d` collision suffix used for dict keys, converting the container to a list of possibly-suffixed
   strings) rather than a Python `set`, or note the ordinal so a `json.dumps` of the eventual field
   does not also choke on a raw Python `set` (JSON has no native set type either).

4. **KNOWN `12d4e1b00c2f`** (`PUBLISH_ONE_SHOT_PUSH_SKIPS_THE_MAINTENANCE_GUARD`) — FIXED. See
   change 1 above; the order's own remedy description is now implemented verbatim in code and
   docstrings that cite the order number.

5. **KNOWN `a66423722e45`** (`AGENT_SCRATCH_IN_PUBLISHED_TREE`) — appears FIXED, but was still open
   in the queue at read time. `CODE_FREE_DIRS = ("handoff",)`, `_CODE_EXT` (the full executable-shape
   family), `_is_agent_scratch()`, the `refused` list in `sync_tree()` (printed in full, Hard Rule 0
   compliant), and the matching `.gitignore` entries in `gitignore_lines()` are all present and wired
   exactly as the order's remedy describes. This looks like exactly the situation order
   `e114b2d0fe48` (`FIXED_ORDERS_LEFT_OPEN_AT_SHIFT_END`) warns about — landed code, order not yet
   resolved in `state/workorders.json`. Flagged for the resolve step rather than re-filed.

No other defects found in publish.py. Checked in particular: the credential regexes (`_SECRET`,
`_SECRET_ASSIGN`, `_AMBIGUOUS`, `_PLACEHOLDER_CREDS`) for eaten escapes (none — the module's own
`_BAD_CHARS` self-check guards this at import time and passed), every `git()` failure path for
whole-vs-clipped diagnostics (all whole, as documented), `prune_export`/`sync_tree`'s
held-vs-gone-vs-live tri-state classification for both `COPY_DIRS` roots and `COPY_FILES` names, and
`push()`'s three-outcome contract (`True`/`False`/`PushHeld`). No console-window risk (`_NO_WIN`
passed on every subprocess spawn).

---

## src/rigor.py (1132 lines)

Nothing found. Checked the commensuration math (`measure_bit_value`, `faculty_parity_weights`)
against the live `assay.FACULTY_WEIGHTS`/`assay.CHARTER_PHYSICAL_WEIGHTS`/`assay.WEIGHTS` tables
(all exist and hold the values the docstrings describe — `assay.WEIGHTS` is in fact 11 entries,
physical scaled by `_PHYS_SCALE` then updated with the three faculties at `_FACULTY_W`, matching
`rigor.main()`'s comment that it "had grown to 11"). Checked `_validate_reciprocal_matrix`,
`perron_weights`, `logrank_weights`, `theorem_1_check` for the two-sided CR/curl fix described in
their own comments (order `dc501e776a2b`) — correctly two-sided (`abs(cr) < 0.10`, `abs(cf) < 1e-9`
etc.). Checked `bradley_terry`'s Ford's-condition refusal logic (independent `if`/`if` rather than
`if`/`elif`, per order `0fa1ad406c7e`) and the `observed` vs `W` (post-prior) distinction for the
undefeated/winless report — correct. Checked `mathematical_resonance()`'s load-bearing display cut
in `main()` (lines ~1105–1125): correctly extends the head through every tie at the cut boundary
and marks the remainder, per its own documented order `52c99c58c50d`. Confirmed `assay.py`,
`chord_field.py`, `cosmography.py`, `derivation.py`, `tempus.py` all exist and are importable
targets as the module expects.

---

## src/derivation.py (811 lines)

**DEFECT MINOR** — stale/self-contradicting docstring in `scan_constants_with_reason()` (around
lines 628–632):

```
The mislabel was total rather than occasional: `SCAN_MODULES` is built from `os.listdir(HERE)`
over the same directory this function then reads (order ca1ed2be8c51 notes this listing is
still flat and misses `src/deprecated/`, left open this shift -- see the comment above
`SCAN_MODULES`), ...
```

This is false against the code as it stands. `SCAN_MODULES = _scan_modules()`, and `_scan_modules()`
(lines 584–593) uses `os.walk(HERE)` — recursive, not `os.listdir` — pruning only `__pycache__`,
returning relative paths with forward slashes. The comment block immediately above `_scan_modules()`
(lines 555–570) itself states this exact defect was **closed 2026-09-06** ("NO LONGER FLAT (order
`ca1ed2be8c51`, closed 2026-09-06)"), and that `src/deprecated/catalogue_local.py` (confirmed present
on disk) is now reachable by the walk. So one comment in this file correctly records the fix as
closed, and a second comment 60-odd lines later, in a different function, still asserts the bug is
"left open this shift" and that the scan is built from `os.listdir`. This is exactly the "one fact,
two copies, one of them fixed" pattern this project's own docstrings warn about elsewhere (verbatim
in `rigor.py`'s module docstring, and in `secondopinion.py`'s `vulture` entry). Not a runtime defect
— `SCAN_MODULES` is genuinely recursive today — but it actively misleads a future reader (or auditor)
into believing `src/deprecated/` is still unscanned and re-filing a closed order. Remedy: delete or
rewrite the `os.listdir(HERE)` sentence in `scan_constants_with_reason`'s docstring to match the
current (fixed) implementation.

No other defects found. `check_graph()`'s taxonomy-outside-KINDS check, dangling/rootless/unsigned
checks, and the cycle detector (`visit()`) were checked against the docstring's stated fix (order
`72bc85d74ccf`) — correct. `main()`'s early-return-on-cycle fix (order `90516d53d696`) is present and
correctly prevents the non-terminating deepest-chain walk from ever being reached over a cyclic
ledger. The deepest-chain panel (order `7ef394911fb3`/`81410993cb8d`) is genuinely uncapped and
deterministically ordered. `_target_names` correctly unwraps `ast.Tuple`/`ast.List`/`ast.Starred`
targets (order `72bc85d74ccf`).

---

## src/secondopinion.py (704 lines)

Nothing found. The brief's pointer ("`secondopinion._exe` reports 'exited N'") corresponds to
`_exe()`'s `reason = ("found on disk but exited %d on --version%s" ...)` (line ~156) — this is
already the fixed, correct state (order `3fc19ad4d1c6`), not a live defect. Traced the loop over the
three candidate paths (`.exe` in the interpreter's Scripts dir, bare name in Scripts dir, bare name
on PATH): a `FileNotFoundError` on a later candidate never clobbers a more informative `reason` set
by an earlier one, so the final answer correctly reflects the most specific outcome across all three
probes. Checked the returncode-contract fixes for `_ruff`/`_vulture`/`_detect_secrets` (order
`12694407d245`) and vulture's drive-letter-safe regex parse (sweep43-batch05) — all match their
documented behaviour. Checked `report()`'s tree-fingerprint torn-read guard and the three-way
secrets AGREEMENT/DISAGREEMENT/UNMEASURED branching (order `cee96f28fea4`) — logically exhaustive and
correctly distinguishes "house scanner errored" from "house scanner found N" from "found the same
N". `main()`'s `--file-orders` refusal on a torn read (order `dd673cc2f348`) is wired.

---

## src/address.py (539 lines)

Nothing found beyond what the file already documents as an unsettled design question in its own
comments (the `_FILLER` set at lines 40–56, self-flagged "left for a ruling", not a new finding).
Traced `_index_name_is_placed_like_a_title()`'s opens/closes remainder logic (the padding-length
arithmetic between `_worded()`'s leading/trailing single space and the `rstrip()`/`lstrip()` slice
offsets) by hand against several worked examples ("Alien Predator Doom Crossover", exact-name
equality, a single-token target) — consistent and correct. `spine_code_for`'s four-stage fallback
(exact code / normalized-letter equality / most-specific-wins containment with the
opens-or-closes-as-title exception / token-overlap with the equal-token-set exception) was checked
against its own documented false-positive history (DC Comics swallowing a D&D sourcebook, Halo
swallowing an unrelated documentary) and each guard is present and ordered correctly. `promote()`'s
demotion-refusal and unrankable-tier repair (order `2c8e55f8f3f7`) are correct. `slugify()`'s cap
removal (order `5d317e3e47f0`) is confirmed absent from the function.

---

## src/cleanup.py (448 lines)

**KNOWN `fe99e57e1993`** (`UNMARKED_NAME_CUTS_SWEEP44`, cleanup.py portion: old lines 231, 233,
261) — FIXED and confirmed. Grepped the current file for any remaining `[:N]` truncation on a live
code path: none found (`cleanup.py:431` is a comment describing the historical bug, not live code).
`desc_fixed`, `ceil_fixed`, `ceil_unres`, `ceil_ambig` (with every candidate name), `nav`, `mech`
are all printed whole with no caps.

**KNOWN `174c7948f15f`** (`UNMARKED_DISPLAY_CUTS_SWEEP57`, cleanup.py portion: old lines 333,
409–412) — FIXED and confirmed. The `desc_fixed` roster (line ~336) now appends the full `(src, nm,
d, cd)` tuple with no character cut, and the `ceil_ambig` candidate loop (lines ~405–411) prints
every candidate name uncapped, exactly as the surrounding comments describe. (The `whoruns.py` and
`events.py` portions of this same order are addressed separately below / out of batch scope —
`events.py` is not in this batch.)

No other defects found. The eaten-escape guard (lines 187–202) correctly covers `_NAV`,
`_EMPTY_MECHANIC`, `PL._SETTING_META`, and every `_MARKUP` pattern by iterating the roster rather
than a hand-typed list (this itself closes the gap a prior sweep found, where `_MARKUP` was absent
from the guard's roster). `clean_ceiling`'s exact/head/single-prefix-match/ambiguous-prefix
resolution order is correct and refuses to guess on multiple prefix matches (order `ed6e66c0c12d`).
The `changed`-gating fix for thin-description marking (order `2b83e058be3f`, run #29 batch 05) is
present and correct.

---

## src/descending_ladder.py (357 lines)

Nothing found. This module is explicitly held/unwired (order `66f96febdb3a`, not in the open
queue — presumably already resolved as a held/marked ruling) and is not imported anywhere in
`src/`, so there is no live caller to audit for a wiring defect. Verified `rung_for_length()`'s
domain guards at both ends (refuses `metres <= 0` and `metres > DESCENDING[0][3]` with `(None,
None)`, per its own documented fix for the "falls off the top of the table and is silently
labelled Continental" bug) and hand-traced the rung-selection loop against a boundary value
(1e-9 m, exactly the Molecular rung's edge) to confirm it resolves to the correct (finest-scale)
rung rather than an adjacent one. `shrink_report()` and `transgression_bits()`'s non-positive-input
refusals (`to_m <= 0 or mass_kg <= 0`) are consistent with each other and with their sibling
functions' (`compton_confinement_energy`, `density_at_scale`) `None`-on-invalid-domain convention.
`PLANCK_ENERGY` is genuinely derived (`PLANCK_MASS * C_LIGHT ** 2`), not a restated literal, per the
module's own order `8dae7cda3e2e`/`57acf43b339a` claims.

---

## src/cosmology_graph.py (260 lines)

Nothing found. `build_graph()`'s inverse-frequency weight formula (`1/log(n+1.5)`, ×0.15 past
`UBIQUITOUS_CUTOFF`) matches the module docstring exactly. `components()` is a standard iterative
connected-components walk with no unbounded recursion. The `--write` path is fully gated on
`silence.write_json`'s return value (`landed`), never claims a write happened when the atomic
replace was denied, and every list written to `data/SHARED_STAGE_GRAPH.json` (`pairs`, `clusters`,
`source_entities`) is uncapped; the only truncations are in the console report (`main()`'s
`names[:4]`/`c[:6]`), and both carry an explicit "(+N more)" marker per Hard Rule 0. `_cut()`
matches the same convention `_marked` (publish.py) and `_message` (secondopinion.py) use.

---

## src/whoruns.py (159 lines)

**KNOWN `174c7948f15f`** (`UNMARKED_DISPLAY_CUTS_SWEEP57`, whoruns.py portion: old line 154) —
FIXED and confirmed. Line 154 now reads:
```python
print("   %-7d %s" % (pid, cmd if len(cmd) <= 150 else cmd[:149] + chr(8230)))
```
The cut is now marked with an ellipsis (`chr(8230)`), matching this project's house convention
for a reversible display cut (`_marked`/`_cut`/`_message`).

No other defects found. `script_of()`'s interpreter-flag handling (`-m`/`-c` short-circuit,
`_FLAGS_WITH_A_VALUE` two-token skip, bare-flag one-token skip) was traced against the three
documented false-positive/false-negative histories in the module docstring and each is correctly
handled. `running()`'s tri-state contract (`None` for an unreadable process table, distinct from an
empty list) is preserved through to `main()`, which prints `UNKNOWN` (exit 2) rather than treating
an unmeasured process table as "none running" (exit 1).

---

## Summary counts

- DEFECT: 2 (both MINOR — publish.py `_scrub` set-collision loss; derivation.py stale/contradicting
  docstring)
- QUESTION: 0 filed (one self-documented, already-flagged design question noted in address.py, not
  newly raised)
- KNOWN: 5 references across 3 orders (`12d4e1b00c2f` fixed; `a66423722e45` appears fixed but still
  open in the queue; `fe99e57e1993` cleanup.py portion fixed; `174c7948f15f` cleanup.py and
  whoruns.py portions fixed)

publish.py was audited hard per the brief's instruction (public-repo pusher) and was never run,
imported for execution, or invoked with `--push`/`--loop`/`--apply`/`--write`/`--go`. All reading
was static (Read tool) plus read-only `grep`/`wc -l` over the source tree; the only script executed
was the open-queue check (`workorders.open_orders()`), which performs no writes.
