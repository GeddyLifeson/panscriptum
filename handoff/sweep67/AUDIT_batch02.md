# sweep67 batch 02 -- AUDIT

## Scope

`src/verify_math.py`, **13,750 lines, all of them**. Read from line 1 to line 13,750 with the Read
tool in consecutive chunks of about 900-1,000 lines. Nothing was sampled. This is the only module
in the batch (batch 2 of run67).

Read-only for the project: nothing under `src/`, `data/`, `state/`, `output/`, `prompts/`,
`reference/` or the repo root was edited, and `verify_math.py`, `drill.py`, `generate.py`,
`publish.py`, `mutate.py` and every pipeline phase were NOT run. No subagents. The only executions
were scratch scripts under `%TEMP%\s67b2\` that `ast.parse` the source and exec only the file's own
pure scan helpers (no `src/` module imported), plus `pyflakes` over `verify_math.py`:

- the battery's own whole-tree scans, re-run standalone against the live tree: num_ctx literals
  (none), unguarded subprocess spawns (none, and no importer the scan cannot see), `escalation.clear()`
  callers (none), `tol=` discards (none, 80 rows scanned), disarmed rows (none), self-line-citations
  (none), the prose-backed scan (exactly the two named exceptions; unresolved and declined lists
  match their pins), section-tag uniqueness (70 tags, no duplicate; 48 banner / 24 print / 4
  dashed), literal-label uniqueness (none), `_INTERLOCKED` roster vs `assert_clear` callers (33 vs
  33, no difference either way), per-module fail-closed guard counts and `REFUSING TO` (all match),
  the six `_RUN35_PINNED36` sha256 pins (all six match the bytes on disk), the run35 proposal
  register (no unaccounted file), and that `state/sweep_plan/run66.json` lists all 119 current
  modules (so the "a sweep is owed" row is not red today);
- `pyflakes src/verify_math.py`: no output; no `assert` statement anywhere; no BEL/VT/FF/BS byte in
  the file (so the line-17 corruption guard does not fire).

## Prior-audit cross-check (handoff/sweep66/AUDIT_batch02.md)

- **D1 (MINOR, the 1018d49b186e positive control tested a re-typed copy): FIXED.** The control at
  the end of the run35-batch2 block now writes a synthetic module into a scratch directory and calls
  the real `_writejson_calls_discarded_b2(path)`; the scratch directory is removed in a `finally`.
  The comment credits sweep66 batch 02.
- **D2 (MINOR, three stale cross-module line citations): FIXED, all three.** The `standards.py`
  cut is now cited by symbol in the `[note]` of "the boundary MOVES WITH THE CONSTANT" row; the
  `silence.py:511, 518` pair in `_for_owner_landing_b19` is gone (the comment says `silence.write_json`);
  the `withdraw_chapters.py:176` sentence now names `main()`'s `--label` default. I grepped every
  remaining `<module>.py:NNN` in the file: the ones that still describe live code are still right
  (`standards.py:67` is `MIN_CALLS_TO_JUDGE_RATE = tuning.MIN_CALLS_TO_JUDGE`, `cascade_bridge.py:18`
  is the STRUCTURED OUTPUT paragraph, `prose_gate.py:34` is the PROVEN paragraph, `assay.py:147-189`
  still brackets the sentinels, INAPPLICABLE at 152 and NONE/UNESTIMABLE at 190-191, one line past the
  range's end and harmless); the rest are quotations of what a past file said.
- **Q1 (unguarded subscripts of the subject's output): PARTLY FIXED, class still open.** The three
  named sites are repaired: `_rows19h[0][...]` and `_RG.read(_gp)["superseded"]["agent"]` now go
  through `_at_vm`, and the foreground-claim read is the non-raising `_claim19ad()` (sweep66 question
  6, order 253d116215ab). The class is not swept: see Q1 below for the sites that still subscript
  directly.
- **Q2 (three deliberate swallows without the marker): RESOLVED.** All three now carry
  `_ = "silence-exempt: ..."` (the `THREAD_INTEGRITY_FLOOR` read, `_follows_continuation`'s
  `SyntaxError` arm, the unreadable-shard `continue` in §20n).
- **Q3 (probe files written into the live `state/`): STANDS, unchanged and known.**
  `state/_VM_UNRECOGNISED_TEST.json` (§19h-bis) and `state/_VM_ATOMIC_PROBE.json` (§20g). Order
  c349a51ee2c5 already rules the battery unsafe to run concurrently.
- **Sweep66 "cleared" list:** re-traced again after the file grew by 334 lines; nothing I read
  contradicts any of it. The growth is the hermetic-transport block near the top (about 200 lines,
  orders 79d51aef8b71 / 36eca6457ed9 / 30122bf3a5a7), the `worst=None` quota row and the §20n split
  rows, the 20 new `_INTERLOCKED` entries, and the last rows before RESULT.

## Findings

No logic defect, no silent-failure path that turns an error into a plausible negative, no cap or
truncation of a ranked listing, and no unsafe write to shared state was found. Three small ones, all
comment accuracy, all verified by grep or count:

### F1 -- INFO -- the temp-directory enumeration in §18c is stale again (7 stated, 9 real)

`verify_math.py` §18c paragraph "WHAT IS ACTUALLY EXEMPT, re-enumerated by reading every temp-making
site" (the block above `_mkdtemp_vm`). It says the sites that do not go through `_mkdtemp_vm` are
"SEVEN": §19ab's token-flow root, §20p's halt-probe root, §19ft's feats-gate root, batch2's
`_codewatch_concurrency_b2` `scratch_dir`, the two `TemporaryDirectory()` blocks, and batch6's
`_tmp_guard`. `grep -n -E "mkdtemp\(|mktemp\(|TemporaryDirectory\("` now finds nine: also
`_lane_root_vm` (hermetic lane, near the top; removed by an atexit `rmtree`) and
`_synthetic_dir_b2` (the sweep66 D1 control; removed in a `finally`). Both clean up, so nothing
leaks; only the count in the paragraph is wrong -- the same class of stale enumeration that
paragraph was corrected for under orders 41e4489aa545 and c8491264e6dc. Suggested fix: say "nine"
and add the two, or replace the count with "every direct `mkdtemp` is removed in a `finally` or an
atexit hook". Severity INFO.

### F2 -- INFO -- the note on the §20ad self-citation control describes nine fixtures; there are sixteen

The note on `check("[control] the self-citation scan flags exactly the citations it should", ...)`
(end of §20ad's control) reads "these nine fixtures are the constructs actually present in this
file, and four of the five zeros are the false positives order 363c79272987 named in advance".
`_FIX20ad` now holds 16 fixtures (nine original plus seven added under orders 3c72359c53aa and
eb496bfb4db3), of which nine expect 0. Counted from the literal. The row itself is correct; only its
note is out of date. Suggested fix: drop the numbers ("every fixture is a construct that really
occurs in this file"). INFO.

### F3 -- INFO -- a word was eaten from a comment in the run35 batch5 header

The comment above `_SRC_b5` reads "Spliced into src/verify_math.py, so  IS a file in src/." (two
spaces where a token was). It is the "regex escape / backtick eaten in transit" shape the file's own
line-17 guard exists for, only for prose. Cosmetic. Suggested fix: restore the missing name
(probably `__file__`). INFO.

## Questions (possibly deliberate; the owner or a maintainer decides)

### Q1 -- the unguarded-subscript class is still open after the three named sites

Orders e0d71f507510 / 8cdbd0fb6c14 give `_at_vm` and `_Absent19ai` for a row that subscripts the
output of code under test. Rows that still subscript a returned dict directly at module level (a
`None` or a missing key from a regressed subject raises out of the flat script, the atexit net then
prints RED not BROKEN, but every later row is lost): the `_iv[...]` block (`covers_all_signatures`,
`signatures`, `hands_recognised`, `covered_before_widening` ...) and the `_wide[...]`, `_skew[...]`,
`_iv_bad[...]`, `_iv_nog[...]` rows in §20r; `_ev19ft["pages_read"]` and its four siblings in §20b;
`_r["covers_every_reading"]` in §9; `_ac_*`/`_ab_*` tuple reads are safe. Does the rule cover every
subscript of a subject's output? If yes this is a class-wide sweep, not a one-line fix. Unchanged
from sweep66 Q1 apart from the three sites already done.

### Q2 -- the spawn scan cannot see `subprocess.getoutput` / `getstatusoutput` or `os.spawn*`/`os.exec*`

`_SPAWNERS20e` is `{run, Popen, call, check_output, check_call}` and the `os` set is
`{system, popen, startfile}`. `subprocess.getoutput()` and `getstatusoutput()` spawn a shell and
accept no `creationflags`, and `os.spawn*` / `os.exec*` are not looked at. Grep of the whole of
`src/` (minus this file and drill.py) finds no use of any of them today, so this is a theoretical
hole in the "no console windows, ever" invariant, not a live one. Add them to the two sets, or is
the omission deliberate?

### Q3 -- can the onomast doctrine-count rows recur into a banned word, and do digits match anywhere?

`_b5_onomast_doctrine_counts` accepts `str(n) in doc or _b5_spelled(n) in doc`. `str(n) in doc` is a
raw substring test with no word boundary, so a small measured count ("1", "4", "10" -- the
docstring carries the digits `10` and `4`) is satisfied by unrelated text. And the last row bans
"thirty", "eighteen" and "sixteen" outright while `_NUM_WORDS_b5` only spells 12, 14, 15 and 26, so
if a measured count ever legitimately becomes 16, 18 or 30 the docstring can only be correct in
digits. Today's docstring uses "fifteen", "fourteen" and "twenty-six" and nothing here is red. Is
that acceptable as a known limit?

### Q4 -- a deliberately red row ("a sweep is owed") beside the mutation baseline

Carried, not new: the §20n split (order de265a105279) keeps `src/ has no module that no finished
sweep has read` red on purpose whenever a module is added, and `mutate.py` refuses to run on a red
baseline. The owner ruled both must fail the battery; recorded only because the interaction is
easy to trip over. It is green today (119 modules, all in run66's roster).

## Cleared (looked at closely and found correct)

- **Hermetic transport** (about lines 244-450, and the two closing rows): the class-level
  `socket.socket.connect` / `connect_ex` patch covers `create_connection`, http.client and SSL
  sockets (they reach `socket.socket.connect`); the port set is `{11434}` plus `config.yaml`'s
  `ollama_host` port with a widening-only exemption; the `/api/tags` and `/api/ps` canned answers
  dial nothing; `_pin_token_flow_vm` uses a far-future `at` so `ttl=0` cannot reach past the pin,
  nests correctly, and is restored in a `finally`; the closing control drives a socket connect and a
  generation, takes its own two entries back out, and asserts the stand-ins are still installed.
- **The crash net and `check()`**: the atexit ordering (registered first, so it runs last, after
  the tmpdir sweep), `_REACHED_THE_END_VM`, and the `bool`-against-float behaviour are as documented.
- **Ledger wrappers** (`_no_ledger_vm`, `_no_ledger_for_vm`, `_third_party_vm`) and their driven
  controls, the grant-vs-real-note-sites ratchets, and the abstention banner.
- **Every module-level override in the file is restored** from a `finally` (completeness, gpu_lane,
  tuning, standards, foreman/publish stubs, `A.BAND_EDGES`, `A.SIGMA_BY_ATTESTATION`,
  `A.INSTRUMENT_WINDOWS`, `A._RHO_CACHE`, `builtins.open` at §b3 and §b5, `sys.argv`); each has a
  restore-verifying row.
- **Whole-tree scans** (§19ab, §20e, §20p, §20t, §20y, §20z): re-run standalone as listed in Scope;
  each has a two-directional control, and each control drives the real function rather than a copy.
- **Owner-held gates**: `prose_enabled: true`, `step4_enabled: true` and
  `prose_min_cited_fraction: 0.35` are pinned as exact values (§20x); working as designed, not to be
  relaxed.
- **§20u exec of `handoff/run35/checks_L*.py`**: name-and-digest gated, one read hashed then
  compiled, unpinned/tampered/gone all refused with a named FAILED row; the six digests match today.
- **Live state files touched by the battery**: only the two known probe files (Q3 of sweep66);
  every other write goes to a scratch directory, and `onomast.main`, `reference.main`,
  `rosetta.main`, `publish.main`, `phase_cosmology`, `phase_write` are all driven against redirected
  or stubbed paths.

## Coverage note

Read in full, and only: `src/verify_math.py`, lines 1-13,750.
