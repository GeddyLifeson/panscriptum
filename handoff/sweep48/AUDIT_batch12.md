# AUDIT — sweep48, batch 12

Batch: 12
Modules and lines read (full, in successive chunks, no sampling):
  - src/overnight.py        1,950 / 1,950 lines
  - src/rigor.py             1,132 / 1,132 lines
  - src/scout.py               826 / 826 lines
  - src/address_space.py       673 / 673 lines
  - src/address.py             538 / 538 lines
  - src/retry_synthesis.py     379 / 379 lines
  - src/style_audit.py         338 / 338 lines
  - src/profile.py             295 / 295 lines

All eight files read start-to-finish. Cross-file citations were verified by grepping the cited
file for the cited symbol/line and comparing.

---

## FINDING 1 — MAJOR — src/overnight.py:395-410 (`_cmd_is_running`)

**What is wrong.** `_cmd_is_running` special-cases the `-m` interpreter flag (`if tok == "-m":
return False`) but not `-c`. A `-c` invocation's remaining tokens are `sys.argv` for the inline
code, not a script — but the loop does not know that, so it keeps scanning and will accept ANY
later token ending in `.py` as "the script being run." This is the same defect class as the
`-m` bug the file's own docstring says was found and fixed in sweep39-batch11 ("mention vs run"),
just for a different interpreter flag that was not covered by that fix.

**How I verified it.**

1. Direct execution test (miniconda python, `overnight._cmd_tokens`/`_cmd_is_running` called
   directly):
   ```
   _cmd_is_running("roll.py", 'python.exe -c pass roll.py')  ->  True   (false positive)
   ```
   `running()`'s real call sites in this file (`_guarded_popen` line 485, `run()` line 688,
   `start()` line 759, the twin-check line 1478, the keeper line 1518) all pass a BARE basename
   with no arguments as the fragment, so `want_args` is always `[]` and the `all(a in rest ...)`
   guard is vacuously true — meaning this false positive is not an edge case reachable only
   through unusual fragments, it is exactly the shape every real caller in this file uses.

2. A live command line that produces exactly this token shape already exists in this batch's
   neighbourhood: `src/local_agent.py:421-424` builds
   ```python
   argv = [PY, "-c",
           "import sys; p = sys.argv[1]; "
           "compile(open(p, encoding='utf-8').read(), p, 'exec'); print('parses OK')",
           target or os.path.join(HERE, "src", "verify_math.py")]
   ```
   — i.e. `python.exe -c "<code>" <path-to-some-src-module>.py`, invoked by `t_run_check(check=
   "compile", path=...)`. Per CLAUDE.md's Hard Rule -1, this is the "it parses" gate of the
   foreman's autonomous patch-verification lane, called with `path` set to whatever file the
   model just patched — which can be any STANDING script (`publish.py`, `dashboard.py`,
   `foreman.py`, `overwatch.py`, `pipeline.py`, `read.py`) or `feats.py`. While that (short-lived,
   in-memory) subprocess is alive and a WMI poll happens to catch it, `running("publish.py")`
   (etc.) returns a false `True`.

3. Compared against `src/codewatch.py:282-336` (`runs_script`), the sibling implementation
   `overnight.py`'s own docstrings say this function was deliberately kept in sync with
   ("two spellings of one rule is how those two sites drifted apart in the first place",
   `_cmd_is_running`'s docstring). `runs_script` already handles this correctly — its loop
   breaks on the first argument that is neither a flag nor `.py` (`if not a.startswith("-"):
   break`, line 317-318) — and `drill.py:11842` has a synthetic test case,
   `([r"C:/py/python.exe", "-c", "import publish"], "publish", False, "python -c that merely
   imports it")`, asserting exactly this must NOT match. `overnight._cmd_is_running` has drifted
   from `codewatch.runs_script` on precisely the case the sync was meant to prevent.

**Direction of the fault.** A false `True` here means `running()` reports a stage as already up
when it is not, which makes `run()`/`start()` skip launching it (logged as "already running, left
alone"). That is the "job refuses to start" direction the file's own docstring calls out as a
real, previously-realized outage ("the other direction is a job that refuses to run for ever...
That failure has already cost this project one outage" — `_in_this_tree`'s docstring, line
301-303). The window is narrow (the compile-check subprocess is brief), so this is a transient,
self-healing miss rather than a permanent one, but it can recur every time the foreman's patch
lane verifies a patch to a STANDING script.

**Proposed remedy.** Mirror the existing `-m` short-circuit:
```python
if tok in ("-m", "-c"):
    return False
```
in the loop at overnight.py:401-408 — or, more robustly, adopt `codewatch.runs_script`'s
break-on-first-non-flag-non-`.py` shape so no third flag (`-W`, `-X`, etc.) needs its own special
case later.

---

## FINDING 2 — MINOR — src/overnight.py:1667-1669 (stale cross-file line citations)

**What is wrong.** The comment naming where every STANDING job's `main()` calls
`escalation.assert_clear` cites seven line numbers, all of which are now stale:

| cited as | actual line | drift |
|---|---|---|
| `dashboard.py:1068` | 1206 | +138 |
| `publish.py:1594` | 1814 | +220 |
| `foreman.py:1711` | 1941 | +230 |
| `overwatch.py:922` | 994 | +72 |
| `pipeline.py:2876` | 3210 | +334 |
| `read.py:1408` | 1561 | +153 |
| `feats.py:1813` | 2617 | +804 |

**How I verified it.** `grep -n "assert_clear" src/<each file>.py` — each file has exactly one
`_ESC.assert_clear(os.path.basename(__file__))` call at its own `main()` entry, at the line shown
in the "actual line" column above.

**Note on scope.** This batch's brief says overnight.py's OWN line numbers may have drifted ~35
lines from this shift's edit — these seven citations point at OTHER files, so the drift (72-804
lines) is unrelated to that and is pre-existing staleness from those files' own growth.

**Proposed remedy.** Same fix the file already applies elsewhere for the identical problem (e.g.
`measure_bit_value` in rigor.py, `_hash_offsets` in address_space.py): drop the line numbers and
cite by symbol only ("every STANDING job's `main()` calls `escalation.assert_clear` at its own
entry"), or verify by `grep` at read time rather than trusting a number that cannot self-invalidate.

---

## FINDING 3 — MINOR — src/overnight.py:202 (stale cross-file line citation)

**What is wrong.** `running()`'s docstring cites `` `publish.py:render_page()`, ~line 1266 `` as
the place `publish.py` computes its own local page. The actual definition is at
`src/publish.py:1364` — stale by 98 lines.

**How I verified it.** `grep -n "def render_page" src/publish.py` → line 1364.

**Proposed remedy.** Same as Finding 2: cite by symbol, not by line.

---

## FINDING 4 — MINOR — src/address_space.py:643-644 (stale cross-file line citations)

**What is wrong.** The comment explaining why `SHELFMARKS.json`'s write is gated cites two
readers by line number, both now stale:

- `` `pipeline.py:2138` (`_phase_input("SHELFMARKS.json")`) `` — actual call is at
  `src/pipeline.py:2799` (+661 lines).
- `` `standards.py:1177` `` — actual read is at `src/standards.py:1264` (+87 lines).

**How I verified it.** `grep -n "SHELFMARKS.json" src/pipeline.py` and `src/standards.py`; the
`_phase_input("SHELFMARKS.json")` call appears once, at 2799, and the `open(...,
"SHELFMARKS.json"...)` read in standards.py appears once, at 1264.

**Proposed remedy.** Same as Findings 2-3.

---

## FINDING 5 — MINOR — src/retry_synthesis.py:241 (stale cross-file line citation)

**What is wrong.** The comment above the dict this module's `synthesise()` returns says it must
be "SAME SHAPE AS `pipeline.py:1157`". Line 1157 of `pipeline.py` is inside `write_record`'s
docstring (an unrelated function — the tail of `_prune_stale_top_keys`-style code, `return
kept`), not the synthesis-block dict the comment is actually about. The synthesis dict this
comment is describing parity with is constructed at `src/pipeline.py:1722-1732`
(`"ceiling_entity"` at 1724 through `"assessed_at"` at 1732) — the neighbouring comment two lines
below (retry_synthesis.py:242) correctly cites `pipeline.py:1727` for the `"rationale"` key,
which sits inside that same 1722-1732 block, confirming 1157 is the wrong line for this claim
and not a second, differently-numbered thing.

**How I verified it.** `grep -n '"ceiling_entity"\|"provisional_magnitude"\|"method":' src/
pipeline.py` locates the dict at 1722-1732; `sed -n '1150,1160p' src/pipeline.py` shows line
1157 is inside `write_record`'s docstring, unrelated to the synthesis dict shape.

**Proposed remedy.** Correct the citation to `pipeline.py:1722` (or cite by the enclosing
function, `phase_synthesis`), or drop the line number per the same house fix used elsewhere in
this file (`pipeline._stored_cut`, cited by symbol two paragraphs later in the same function).

---

## QUESTION — src/overnight.py:329-349 (`_in_this_tree` / `_cmd_is_running`), trailing separator

Both `_in_this_tree` (`script = next((t for t in toks if t.endswith(".py")), None)`) and
`_cmd_is_running`'s scan (`if tok.endswith(".py"): ...`) require the token to end in the literal
substring `.py`. Verified by direct test that a token of `src/roll.py/` (trailing separator) does
NOT match `.endswith(".py")` and so is invisible to both functions — the fail-open direction the
batch brief calls out as priority (running() would answer False for a process legitimately
running that script, allowing a duplicate spawn). I could not find any command-line construction
anywhere in this batch or its immediate neighbours (`local_agent.py`, `drill.py`) that appends a
trailing separator to a script path, so I am not confident this is live rather than defensive-
coding-only. Flagging as a question rather than a finding per the audit method: is there a known
launcher (the Startup `.vbs`, a scheduled task, some other tool building these command lines)
that can produce a trailing-separator script path, or is this purely theoretical?

## QUESTION — src/overnight.py:330, 405 (`.pyw` scripts)

Same two functions require the script token to end in `.py` specifically; a script invoked as a
`.pyw` file would not match either `_in_this_tree` or `_cmd_is_running`'s scan, and `pythonw.exe`
is already used as an interpreter in this tree's own Startup launcher (quoted-path case fixed
this shift). I found no `.pyw` file anywhere under `src/` (`find src -iname "*.pyw"` — empty), so
this looks like a latent gap rather than a live one. Flagging as a question: is `.pyw` ever
expected as a script extension in this tree, now or in a plausible future job?

---

## WHAT I READ AND FOUND NOTHING WRONG IN

- **src/overnight.py** — `running()`'s tri-state contract (None/False/True) is honoured correctly
  at every one of its five call sites in this file (`_guarded_popen`, `run()`, `start()`, the
  startup twin-check, and the keeper thread) — each checks `is None` before falling through to a
  truthiness test, so a blind process-table probe cannot be mistaken for "not running" anywhere
  in this module. The keeper's STANDING restart logic correctly consults `_manager_stopped`
  before restarting a down job, and correctly treats "manager-stopped" and "probe-blind" as
  non-idle (not counted toward `IDLE_LIMIT`). The idle-halt / `assert_clear` interaction at the
  end of `main()`'s loop (lines ~1899-1941) fails closed on an unreadable halt file exactly as
  its own comment claims (`_halted = True` in the `except` arm, verified by reading the code, not
  just the comment). `_manager_stopped`'s own `except` also fails closed (`return True, "..."`).
  The `allsweep.py:248` citation for `Verifier("continuity inventory", ...)` (cited at
  overnight.py:525) is exact, not stale. `autostart.py:435`/`:463` citations for
  `supervisor_alive()`/`start_supervisor()` (cited at overnight.py:1442-1443) are both exact.
  `_BAD_CHARS` control-character self-check at import time is sound. `_cmd_tokens`'s `shlex`
  fallback on `ValueError` degrades to the pre-fix behaviour rather than raising, as documented.
- **src/rigor.py** — no fail-open `except`/swallow found; every `except` either notes and returns
  a labelled error or (in `RigorIntegrityError` sites) refuses outright. The two-sided CR/eta
  checks (`abs(cr) < 1e-9` etc.) are correctly two-sided per their own stated Saaty-theorem
  reasoning. Ford's-condition refusal logic in `bradley_terry` is un-chained (independent `if`s,
  not `elif`) as its own comment claims. `mathematical_resonance`'s `load_bearing` ranking is
  returned whole (never truncated in the function), and `main()`'s display cut of it correctly
  extends through ties and states the remainder count — no unmarked cap.
- **src/scout.py** — every shared-file read/write (`_mutate`, `hostless()`, `sweep()`'s
  `ATTEMPTS`/`LOG` handling) distinguishes "unreadable" from "empty" and fails closed rather than
  defaulting to `{}`/`[]` silently. `verify()`'s `MIN_NAME_HITS` floor correctly avoids the
  "check that cannot pass" trap for sources with too few probeable names. No `[:N]` truncation
  found on any operator-facing list (source names, URLs, deferred lists) — all are stated in full
  with counts.
- **src/address_space.py** — `_bits`/`WIDTHS`/`TOTAL_BITS` are derived from the live census, not
  hardcoded, matching the module's own repeated claim. `fit()`'s no-modulo fix and the
  `charted_gaps`/`uncharted` marking are both live and wired (`assign_and_mark` is used, not just
  `assign` alone, at its one call site in `main()`). `main()`'s writes are gated on
  `silence.write_json`'s verdict, not assumed to land.
- **src/address.py** — the spine-code matching cascade (equality, most-specific containment,
  opens/closes-with-remainder-check, token-overlap fallback) is heavily proven-by-measurement in
  its own comments; I re-derived the logic by hand for a few of the documented cases (`"Sword
  Coast Adventurer's Guide DC Edition"` etc.) and it matches what the comments claim.
  `tier_rank`/`promote` correctly return `None`/repair-up rather than silently defaulting an
  unrecognised tier to rank 0. `slugify` and `build_address` truncation removals are as documented
  (no `[:60]` remains).
- **src/retry_synthesis.py** — `save_side`'s read-modify-write-and-report-verdict pattern is
  sound; `do_merge()`'s unmerged-sources report is uncapped and the exit code correctly nets
  denied+unmerged. The three points where this module deliberately shares code with `pipeline`
  (block/prompt construction, transport, band-acceptance gate, evidence-cut) all call into
  `pipeline` rather than restating it, as claimed.
- **src/style_audit.py** — the `--self-test` fixture asserts by name and exact count in both
  directions (over-collapse and over-fire), as its own comment claims; I traced `opener_shape`
  and `TURN_ENDING` against both fixtures by hand and the asserted results are correct. No
  remaining `[:N]` cap without a stated remainder in `report()`.
- **src/profile.py** — `B32`'s 32-symbol alphabet and `_PROFILE_RE`'s derivation from it were
  checked against `_b32`/`_unb32`'s masking; no drift between encoder and validator alphabets.
  `main()`'s round-trip check correctly re-encodes decoded fields rather than comparing a
  fetched-back field to itself (which the comment says used to be a check that could not fail),
  and the exit code correctly carries the round-trip verdict.
