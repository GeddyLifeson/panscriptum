# Sweep 58 — Batch 09 audit

Modules read in full (top to bottom, offset-paged where large):

| module | lines |
|---|---|
| foreman.py | 2204 |
| silence.py | 1126 |
| rosetta.py | 809 |
| build_terminal.py | 667 |
| handbuilt.py | 516 |
| render.py | 429 |
| style_audit.py | 338 |
| tells.py | 303 |

Open queue checked first via `workorders.open_orders()` (scratch script in
`.../scratchpad/sweep58/check_orders.py`); every finding below that matches an open order is
tagged KNOWN with its id and a freshness note.

---

## foreman.py (2204 lines)

**KNOWN b750409c76be — FIXED this shift.** `RESTART_OLLAMA_CANNOT_START_AN_ABSENT_TRAY`. Traced
`restart_ollama()` end to end: `_ollama_processes()` now probes tray+daemon via `tasklist`,
returning `None` (not "absent") on an unreadable table; when the tray is absent,
`_ollama_tray_exe()` locates the exe and `_start_ollama_tray()` launches it with
`CREATE_NO_WINDOW | DETACHED_PROCESS`, `close_fds=True`, all three standard streams to
`DEVNULL` — genuinely windowless and detached, matching the shift note. Kill-and-wait only fires
when a daemon is present or the process table could not be read (blind, old behaviour preserved
as the safe fallback). The two outcomes are worded differently in the return string exactly as
the order's remedy asked. Verdict: order's remedy fully implemented and correct.

**KNOWN d9328fe1ee38 — PARTIALLY addressed, differently than the order's remedy (a).**
`STALL_STANDARD_WATCHES_THE_LOG_NOT_THE_WORK`. `kill_stalled_job()` now gates every kill on
`_io_moving(pid)` (new this shift, `STALL_KILL_IO_WINDOW_SECONDS = 20`): samples
`psutil.Process(pid).io_counters()` twice, `window` seconds apart, and only proceeds to kill when
`moving is False` (exact match). `True` or `None` (unreadable) both spare the job as "working",
which is the fail-closed shape the order calls for ("only ever narrows a kill"). This is a
*different* second witness than the order's suggested "output-tree mtime" (remedy a), not the one
proposed, but it satisfies the same requirement: a kill now needs positive evidence of true
idleness, not log silence alone. Verified `psutil>=7.2` is a declared dependency and is installed
(7.2.2) on this machine, so the fail-closed "unreadable" path is not the common case.
QUESTION (not a defect — could not demonstrate a concrete failure without feats.py, out of this
batch's scope): the order's own measured example was a crawl in 32x host backoff that still wrote
a catalogue entry every ~1.1 minutes while its log sat quiet for 82 minutes. `_io_moving`'s
20-second sampling window is far shorter than that write cadence; whether the process performs
enough *network* I/O (not just file writes) inside any given 20s slice during deep backoff to be
correctly read as "moving" is unverified from this batch. The order's remedy (c) — a drill net
driven by a synthetic log/output tree needing no live process — does not appear to have landed
(drill.py is batch 1 of this sweep, out of scope to confirm).

**KNOWN ff77e242b830 — still open, confirmed still accurate.** `restart_ollama`/`_ollama_answers`
owner question. Re-read against current code: both the "restarted" and "start-tray" paths still
gate `did=True` purely on `_ollama_answers()` (a bare `/api/tags` HEAD-equivalent), never on a
completed generation, and the return strings say exactly what the order quotes ("daemon
answering, model reloads on first call"). No change since the order was filed; still a live
owner ruling to make, not a defect.

**KNOWN c9146abf92df — NO LONGER ACCURATE for the foreman.py half.** `ROLL_LOST_UPDATE_REMAINING_WRITERS`
names "src/foreman.py:189" as a whole-document writer of `data/SWEEP_ROLL.json`. Grepped
foreman.py for `SWEEP_ROLL`, `roll.update_rows`, `roll.mutate`, `import roll` and any
`write_json` call naming a roll path: zero hits. Foreman.py currently has no `SWEEP_ROLL.json`
writer at all — the code the order describes at line 189 (now inside `clear_learned_caps`,
unrelated) is gone. The `roll.py:127` half of the order is outside this batch and untouched by
this note.

**KNOWN 89503c58409f — accurate, independently reproduced.** `STALE_LINE_CITATIONS` names
foreman.py's citations to "verify_math.py:6051/6283/5504" for the "verify_math and drill are
unsafe to run concurrently" rule as stale, real content having drifted to
"verify_math.py:8592/9006/9828/10249". Verified independently: `_contracts_pass`'s docstring
cites `verify_math.py:5504` and the `DENYLIST` comment cites `verify_math.py:6051` and `:6283`;
none of those three lines mentions the rule (checked each). `grep -n "not safe to run"
verify_math.py` finds the real text at lines **8893** and **9274** (the run35 batch-1/batch-2
proposed-checks docstrings). The order's own "actual" pointers (:8592/9006/9828/10249) have
themselves drifted further since it was filed — unsurprising given how fast verify_math.py grows
— but the underlying finding (the citations are stale) still holds.

**DEFECT MINOR — a distinct stale citation not covered by 89503c58409f's nine listed sites.**
`foreman.py:1954` (inside `owner_queue()`):

```python
# `"%s.%d.%d.tmp"` shape as silence.py:511, inline rather than a new helper.
```

cites `silence.py:511` for the pid/thread-qualified temp-name pattern. Read silence.py in full
this batch: the real site is `write_json()` at line **827** —
`tmp = "%s.%d.%d.tmp" % (path, os.getpid(), _th.get_ident())`. Line 1954 is not among the nine
locations order 89503c58409f already lists for foreman.py ({122,123,232,294,389,580,638,1426,1774}
— note foreman.py:232's citation of the same "silence.py:511" IS in that list, so only :1954 is
new). Remedy: cite by symbol (`silence.write_json`'s tmp-naming line) per the project's own
existing rule (order 0c7592915a48/a09a0e003c31), not by line number.

**Other checks performed, nothing found:** every `subprocess.run`/`Popen` call in the file passes
`creationflags=_NO_WIN` (verified all ten call sites: `_run`, `restart_reader`'s wmic,
`kill_stalled_job`'s wmic, `kill_duplicate_jobs`'s wmic, `_stop_ollama`'s powershell,
`_start_ollama_tray`, `_ollama_processes`'s tasklist, `_contracts_pass` via `_run`) — no console-
window risk. `main()`'s loop re-asks `escalation.assert_clear()` every round before dispatching
any remedy, and re-imports `escalation` fresh each round rather than trusting a startup-time
handle (fail-closed on a deleted/unparseable module). `attempt_patch`'s MODEL-lane gates
(`regex_touched`, `lines_changed`, `_contracts_pass`, `DENYLIST`) all read as designed, no
tautologies found in this pass.

---

## silence.py (1126 lines)

Nothing found. Read in full including `swallow`, the observed-handler/suppress detectors
(`_handler_is_observed`, `_suppressed_names`, `_suppress_is_declared`), `_src_py_files`,
`replace_if_unchanged`/`replace_retry` (the CAS and retry helpers foreman.py and rosetta.py both
depend on), `write_json`, `append_line`'s Windows-append-is-not-atomic fix, and the
`instrument()`/`_ensure_import`/`_handler_tags` rewriter. All of the extensively-documented past
defects in the header comments correspond to code that now does what the comment says it does —
spot-checked several against the live logic (word-boundary token matching in `_OBSERVED_RX`,
the re-raise-via-AST-walk fix, the tautology fix in `_handler_is_observed`'s bound-name check,
the digest-vs-unreadable three-way split in `_digest_or_unreadable`). Not part of this shift's
rewritten-module list, and none of the stale-citation orders name this file as a *source* of a
bad citation (only as the correct target other files should point at — see foreman.py and
handbuilt.py above, both confirmed independently against this file's actual line numbers).

---

## rosetta.py (809 lines)

**KNOWN 0182eb4ff49c — FIXED this shift.** `SMALL_DEFECTS_SWEEP57` flagged that the `--mine`
write-denial stderr line falsely claimed "the mine above is NOT on disk" even when only the
`.raw.json` backup write failed (the primary having already landed). Traced the fix: the new
`_mine_write_denied_message(path, primary_path)` (matches the shift note "rosetta: gained
`_mine_write_denied_message`") correctly branches on `path == primary_path` — true only for the
first write in the loop `for path in (OUT, OUT.replace(".json", ".raw.json")):` — and only then
says "NOT on disk"; the `.raw.json` branch says "the mine above IS on disk ..., but its .raw.json
backup did not update." Since the loop calls `return 1` immediately on the first (`OUT`) write's
failure, the function can only ever be called with `path != primary_path` after `OUT` has already
landed, so the branching is sound. Order fully resolved.

**KNOWN 5bb12b398783 (item 5) — accurate, still open.** Order asks whether
`dashboard.py`'s owner-ruled `escalation.assert_clear()` requirement (ruling `aad11acb1183`)
extends to writers of `data/` outside `output/`/`state/`, naming rosetta.py and navtree.py as
candidates and render.py as a probable non-issue (writes only inside `output/`). Confirmed by
grep: `escalation` does not appear anywhere in rosetta.py, so `--mine` and `--refine` both write
`data/ROSETTA.json` (a network-fetching pass that can run for a long time under `--mine`) with no
halt check at all. No new information beyond what the order already states; filed as KNOWN,
still unresolved.

**QUESTION — a third module in the same shape, not named by 5bb12b398783.** `handbuilt.py` (read
this batch) also writes `data/HANDBUILT_ASSAYS.json` via `silence.write_json(OUT, ...)` with zero
mentions of `escalation` anywhere in the file (grepped alongside rosetta.py/render.py/
build_terminal.py). It is a much smaller, hand-authored dataset (no network calls), so the risk
profile differs from rosetta's mining pass, but it is the same class of write the order is asking
the owner to rule on. Flagging so the ruling, whenever made, is checked against all three modules
rather than just the two named.

**Other checks performed, nothing found:** the historically-fixed defects documented in comments
(`assays_by_host`'s bare-key split, `check()`'s host-scoping and its `_norm` collision counting,
`refine()`'s kept/dropped accounting, the `MINE_FLOOR` compare-and-refuse logic, the exit-code
contract on `--check`) all match the code as written. `numeric_rows`'s row-vs-proximity parsing
and the "first number, never the max" column-order fix both read correctly against their stated
failure scenarios. No eaten regex escapes (`_BAD_CHARS` guard present and the file contains none).

---

## build_terminal.py (667 lines)

Nothing found. Not part of this shift's rewritten-module list. Read the whole assembled page
(Python wrapper plus the embedded JS `TEMPLATE`). The `esc()` XSS-hardening fixes referenced in
comments (`shelfmark()`'s escape-at-entry, the `selectWorld()` `cat`/`f.*` sinks fixed under order
c000fbc3c378, the `</script>`-breakout neutralisation via `<` substitution in `main()`) are
all present and match their descriptions. The uncapped shelved-here roster (`.roster{max-height:
190px;overflow-y:auto}` instead of a slice) and the marked `trimmed()` cuts (nucleus title, shell-2
labels, world labels — all append `…`) match the Hard Rule 0 fixes their comments describe.
`main()`'s `--help`-must-not-rebuild fix (argparse rather than a bare argv test) and the atomic
`replace_retry`-based write with a checked exit code are both correct. See the render.py section
below for a citation issue found *in render.py* that points at this file.

---

## handbuilt.py (516 lines)

**KNOWN 1d45a56ae1d8 — accurate, confirmed exact.** `STALE_CITATIONS_SWEEP57_NOT_IN_EXISTING_ORDERS`
lists `handbuilt.py:455-464,502`. Read the cited block directly:

- Line 459 cites `silence.py:511` (order says real ~786; independently confirmed this batch it is
  now **827**, `write_json`'s tmp-naming line — drifted further since the order was filed, as
  expected for a fast-growing file).
- Line 461 cites `silence.py:519-530` (order says real ~838-844; this batch's full read of
  silence.py places `_discard_tmp` at **856-868** — again, further drift, same defect).
- Line 459 also cites `standards.py:1534` and line 502 cites `catalogue_models.py:227-228` — both
  outside this batch's modules, not independently re-verified, but the order's claim stands as
  filed.

No new handbuilt.py findings beyond confirming this KNOWN order and the escalation QUESTION
raised under rosetta.py above.

---

## render.py (429 lines)

**DEFECT MINOR — a stale self-citation, not in any open order** (grepped every open order's
`what` text for "render.py": only 5bb12b398783 mentions it, on an unrelated escalation point).
`write_views()`'s docstring:

```
This module is the dispatcher for all nine cosmology view tiers and NOTHING imported it -- the
only mention anywhere in src/ was a comment in build_terminal.py:83
```

Read build_terminal.py in full this batch: line 83 is `const DATA = __DATA__;`. The actual
mention of render.py is four lines later, at **build_terminal.py:87**:
`// render.py's containment_svg() already does exactly this with html.escape(); this is the same`.
Remedy per the project's own standing rule: cite by symbol (`build_terminal.py`'s `esc()`
docstring / the comment naming `containment_svg`) rather than by line number.

**Other checks performed, nothing found:** `children_of()`'s coordinate-completeness guard (the
`missing = [t for t in prefix if t not in coord]` refusal, fixing orders 3270e0172391 and
3b422bc17939) is correct and total — every prefix key must be present or it raises, so no partial
coordinate can silently pool unrelated nodes. `containment_svg`'s child-count-vs-geometry split
(`n = max(1, len(children))` for layout only, `_kids = len(children)` for the caption) is
correctly separated, matching order 48c1388144bd. The `[:26]` name truncation inside
`containment_svg` for ring labels has no ellipsis marker, which looked at first read like a Hard
Rule 0 gap — but it is already the subject of a **closed** order (d1a008863b02, confirmed not in
the open queue) whose ruling is exactly the code's current comment ("the caller who wants the
whole name still has it" via calling `children_of()` directly rather than through `view()`), so
this is not re-raised as a new finding. No subprocess calls in this file (no console-window
exposure). `_probe()` never raises by construction and is only invoked under `--probe`, so it
cannot make a "read-only" sweep touch the network unasked.

---

## style_audit.py (338 lines)

Nothing found. Not part of this shift's rewritten-module list, but it directly imports `tells.py`
(this shift's other changed module in this batch), so it was checked for any interaction with the
`_SENTENCE_START`/`_anchor` change: the self-test's GAMMA/DELTA fixtures only exercise STRUCTURAL
patterns ("not merely X but Y", "stands as a testament") and the local `TURN_ENDING` regex, none
of which use the DISCOURSE `^\s*` anchoring path that changed this shift, so there is no
behavioural coupling to verify further. The self-test's own documented past defects (the
shape-detector tautology, the missing negative control, the missing turn-ending/em-dash
assertions) are all present as fixed. The three Hard-Rule-0 cap removals documented via `_cut()`
(opening shapes, exact openers, vocabulary) are correctly uncapped with "showing X of Y; N more
not shown" reporting.

---

## tells.py (303 lines)

**KNOWN f0677ea9bc68 — FIXED this shift.** `TELLS_ANCHOR_MISSES_TEXT_THAT_STARTS_WITH_WHITESPACE`.
Matches the shift note exactly ("tells._SENTENCE_START: the true-start branch is now `^\s*`").
Traced the fix directly: `_SENTENCE_START = r"(?:^\s*|(?<=[.!?])\s+)"` and
`_anchor(pat) = _SENTENCE_START + pat[4:] if pat.startswith(r"^\s*") else pat`. Every DISCOURSE
pattern that originally began `^\s*...` (verified all 15: "that said", "importantly", "in
conclusion", "moreover / furthermore", "firstly / secondly", "the truth is", "to be clear", "in
essence", "simply put" — 9 of the 15 DISCOURSE entries carry this prefix, matching the order's
"nine of the fifteen discourse patterns") is stripped of exactly its literal 4-character `^\s*`
prefix and re-spliced onto `_SENTENCE_START`, which itself re-supplies `^\s*` as one branch of
its alternation. So the true-start leading-whitespace tolerance the order says was silently
dropped is now present again, and the mid-sentence branch `(?<=[.!?])\s+` is untouched — matches
the order's own description of the intended fix precisely. No residual gap found.

**Other checks performed, nothing found:** the `_BAD_CHARS` eaten-escape self-check, the
regex-metacharacter escape guard on every compiled pattern (`_COMPILED`/`_LEX` loop asserting no
control character `< 0x20` other than `\n`/`\t`), and `prompt_in_sync()`'s three-way
True/False/None contract (an unreadable prompt file must not read as agreement) are all correct.
`scan()` and `prompt_section()` are unchanged from what their docstrings describe.

---

## Summary of NEW findings (not previously filed)

1. DEFECT MINOR — `foreman.py:1954` stale citation to `silence.py:511`; real line is `silence.py:827`.
2. DEFECT MINOR — `render.py`'s `write_views()` docstring stale citation to `build_terminal.py:83`; real line is `build_terminal.py:87`.
3. QUESTION — `handbuilt.py` writes `data/HANDBUILT_ASSAYS.json` with no `escalation.assert_clear()` call, the same shape order 5bb12b398783 (item 5) raises for rosetta.py/navtree.py but does not name.
4. QUESTION — `foreman.kill_stalled_job`'s new `_io_moving()` second witness (this shift) samples I/O over a fixed 20-second window, materially shorter than the ~1-minute write cadence measured in order d9328fe1ee38's own example of a deep-backoff crawl; whether socket-level I/O during backoff reliably falls inside that window could not be confirmed without feats.py (out of batch scope).
