# Audit batch 12 — overnight.py, weave.py, health.py, context_budget.py, burgs.py, audit.py, ledger.py

Full line-by-line read of all 7 files (1754 lines across overnight/weave/burgs/audit/ledger, plus health.py and context_budget.py). Findings below, each cited `file.py:LINE`, labeled VERIFIED (read + traced consequence) or UNVERIFIED (plausible, not traced).

---

## overnight.py (719 lines)

### Confirming the known findings

1. **overnight.py:414-428 (`coverage_snapshot`) and overnight.py:431-455 (`preflight`) — missing `returncode` checks. VERIFIED.**
   ```python
   def coverage_snapshot():
       try:
           subprocess.run([PY, os.path.join(SRC, "coverage.py")], cwd=HERE,
                          capture_output=True, text=True, timeout=1800, ...)
           rows = json.load(open(os.path.join(HERE, "data", "COVERAGE.json"), encoding="utf-8"))
       except Exception as e:
           ...
   ```
   `subprocess.run(...)`'s return value (with `.returncode`) is discarded. If `coverage.py` crashes mid-run but leaves the previous cycle's `COVERAGE.json` on disk untouched, `json.load` succeeds and the stale numbers are reported as this cycle's fresh measurement — no exception is raised, so the `except` branch (which correctly flags `snap["error"]`) never fires. Same shape in `preflight()`:
   ```python
   r = subprocess.run([PY, os.path.join(SRC, "health.py"), "--preflight"], ...)
   out = r.stdout
   ...
   n = out.count("FAIL")
   return n, blocking
   ```
   `r.returncode` is never read. If `health.py --preflight` crashes after printing partial (or zero) output, `n` and `blocking` are computed from whatever partial stdout exists — e.g. a crash before any "FAIL" line yields `n=0, blocking=False`, indistinguishable from "checked, all clean," even though the `except` block's own comment (lines 440-449) explicitly says this exact class of silent pass must not happen. The comment's fix only covers the case where `subprocess.run` itself raises (timeout/launch failure); it does not cover the case where the child launches, crashes with a nonzero exit code, and produces truncated/empty stdout.

2. **overnight.py:462 — non-atomic write. VERIFIED.**
   ```python
   with open(p, "w", encoding="utf-8") as f:
   ```
   in `write_status()`, writing `STATUS.md` directly (bare `open(..., "w")`), not through `silence.write_json`/`replace_retry`. `STATUS.md` is read by `publish.py` (copied verbatim, per the file's own comment at line 678) and is the file "somebody looks at in the morning" — a shared, externally-consumed file with a truncate-then-fill write.

3. **overnight.py:344-347 (`STANDING` set) — `read.py` deliberately absent. VERIFIED.**
   `STANDING` (lines 372-380) lists exactly `dashboard, publish, foreman, overwatch, pipeline`. `read.py` and `feats.py --roll` are explicitly called out as NOT in this set (comment at lines 382-389: "`read.py` and `feats.py --roll` hang off this supervisor's hours-long main lap"), so the keeper thread (`_keep()`, lines 509-522) never restarts a killed reader — only the next full cycle's `run("read", ...)` call would relaunch it.

   **No stall-detection logic of its own — VERIFIED.** The only occurrences of "kill_stalled_job" / "stalled" in this file are in comments (line 119, line 295) describing `foreman.py`'s behavior being *replayed* through `foreman_report()` (lines 272-310), which reads `data/FOREMAN.json` and re-logs what the foreman already did. The file's own timeout mechanisms — `run()`'s `p.wait(timeout=timeout_h*3600)` (line 189) and `join()`'s equivalent (line 252) — kill a job only after a fixed multi-hour wall-clock ceiling with zero output, which is not stall detection (a job producing occasional output but effectively wedged would never trip it); nothing in overnight.py itself watches for silence/staleness mid-run. Confirmed: all stall-kill logic lives in foreman.py; overnight.py only surfaces it after the fact.

### New finding

4. **health.py:180-181 vs context_budget.py — a second, independently-maintained context-arithmetic source of truth. VERIFIED (duplication exists) / UNVERIFIED (functional impact on read.py).**
   ```python
   sys_toks = len(R.SYSTEM) / 4
   body_toks = R.CHUNK / 3.7
   ```
   (`health.py:180-181`, inside `check_context_budget()`). `context_budget.py` was built specifically to be *the* calibrated source of context-window arithmetic — it measures `PROSE_CHARS_PER_TOKEN = 4.0` (system/template prose) and keeps `CHARS_PER_TOKEN = 3.0` (entity JSON content) deliberately pessimistic, with an extensive header explaining exactly why a second, hand-copied ratio is dangerous (see `ledger.py`'s own parallel argument about `MATERIAL["rock"]["pulv"]`, "a literal copied by hand here would be a second, silently-drifting source of truth"). `health.py`'s preflight check — whose own docstring cites the *exact* historical bug ("chunks overflowed num_ctx -> looked like 'the model fabricates 51% of the time'") that `context_budget.py` was written to fix — does not import or call `context_budget.py` at all; it re-derives the arithmetic from scratch with its own `/4` and `/3.7` constants, sourced from an un-cited "English wiki prose runs ~3.7 characters per token" claim in its docstring (`health.py:172`) rather than the measured `prompt_eval_count` calibration `context_budget.py` did on 2026-08-24. `3.7 > 3.0` means this check is *more permissive* than the officially pessimistic content ratio — the opposite direction context_budget.py's header says is safe ("being wrong in the other costs silently truncated evidence"). Whether this ever produces a live discrepancy depends on what ratio `read.py` actually sends to Ollama, which is outside this batch (`read.py` not read) — flagging as a maintenance/architecture gap regardless: the module built to be the single source of truth for this exact arithmetic is not the one health.py's preflight uses.

### Clean

Concurrency: `_PROCS`/`_PROCS_LOCK` correctly guard the shared process-listing cache in `_proc_lines()`. The unguarded `_PROCS["at"] = 0.0` writes in `run()` (line 188) and `start()` (line 239) are single-key dict assignments, atomic under the GIL — no corruption risk, at worst a harmless stale-cache read for one cycle. `_keep()` and `_keep_warm()` daemon threads are both correctly wrapped in try/except with `silence.note`. The `ledger_report`/`watch_report`/`tail()` truncations (`[:top]`, `[:12]`, `[:n]`, `did[:5]` removed per the file's own comment) are all diagnostic console/log previews over data whose full form is preserved on disk elsewhere (`failures.json`, `OVERWATCH.json`, per-job log files) — not Hard Rule 0 violations.

---

## weave.py (487 lines)

### Confirming the known finding

5. **weave.py — `len(srcs) > 60` skip. CONFIRMED, with a load-bearing nuance.**
   The active production path is `surprisal_pair_weights()` (weave.py:205-226), called from `pipeline.py:1744` and `tiers.py:199`:
   ```python
   def surprisal_pair_weights(occ, sur, min_sources=2, max_sources=60):
       for k, srcs in occ.items():
           if not (min_sources <= len(srcs) <= max_sources):
               continue
   ```
   Any entity attested in more than 60 of ~211 sources is excluded from contributing evidence weight to continuity-group pair linking. **This does not truncate the entity roster or catalog** — `resolve()` (weave.py:385-415) iterates the full unfiltered `index`, so every entity, including hyper-common ones, is still output in `RESOLVED_ENTITIES.json` with its full attestation list. The exclusion only removes such entities from the pairwise-evidence sum used to decide which sources share a continuity. So this is a statistical filter on which entities count as *evidence*, not a truncation of an ordered listing of entities/sources being catalogued — it does not fit the letter of Hard Rule 0 as cleanly as `[:N]` on a roster would, though it is a silent, undocumented-as-measured cutoff (60 is a round number, not derived) that discards real information from the clustering computation. Flagging for the supervisor's judgment rather than calling it a clear-cut violation.

   Separately: the older `pair_weights()` (weave.py:156-173) and `null_threshold()` (weave.py:249-273) idf-based functions carry the identical `> 60` skip and are **dead code** — confirmed via repo-wide grep, neither is called anywhere except by nothing (only `surprisal_pair_weights`/`null_threshold_surprisal` are used in `main()`, `pipeline.py`, `tiers.py`). Not a live bug, just stale code worth noting.

### Clean

`OUT_GROUPS`/`OUT_RESOLVED`/`OUT_GRAPH` writes (weave.py:472-481) already use `silence.write_json` — this module's own comment (lines 469-471) documents that these were previously `json.dump(obj, open(path,"w"))` (truncate + leaked handle) and were fixed 2026-08-25. Confirmed atomic now — no two-writer-contract violation remains here. `shared[p].append(k)` at line 172 and line 225 both carry explicit "NO CAP" comments and are genuinely uncapped in the current code (verified: no `[:N]` slicing anywhere on `shared[p]`). `components()`'s complete-linkage clustering (lines 276-325) is O(n²) per merge but not a truncation bug. No new correctness issues found in `idf_table`, `name_surprisal`, `resonance_graph`, or `resolve`.

---

## health.py (403 lines)

### Confirming the known finding

6. **health.py:124-144 (SAMPLES write) — bare `except: pass`. VERIFIED**, at approximately the cited range (lines shift slightly to 124-143 in the version read, same code):
   ```python
   if _SAMPLES:
       try:
           old = {}
           if os.path.exists(SAMPLES_PATH):
               with open(SAMPLES_PATH, encoding="utf-8") as f:
                   old = json.load(f)
           ...
           if silence.replace_retry(stmp, SAMPLES_PATH):
               _SAMPLES.clear()
       except Exception:
           pass          # the evidence bag must never break the ledger write
   ```
   Traced consequence: on a torn/corrupt `SAMPLES_PATH`, `json.load` at the read step raises, jumps straight to `except: pass`, and `_SAMPLES.clear()` (which only runs on success) is skipped — so in-memory samples are *not* lost immediately, but the on-disk file is never repaired (no `.corrupt`-and-restart fallback exists for this file, unlike `LEDGER_PATH`'s handling one block up), so **every subsequent `flush()` in this and future processes hits the same read failure forever**, and the evidence bag is permanently stuck un-persisted until someone manually intervenes — exactly as the module's own comment (lines 133-137) states. Confirmed correct as filed.

### Clean

`check_control_chars`, `check_context_budget` (aside from the cross-file duplication noted under overnight.py finding #4, which is really a health.py-sourced issue — see above), `check_api_paths`, `check_caches`, `check_state`, and `reopen_stranded` were all read in full. No new bugs found:
- `check_caches`'s `files[:200]` sampling (line 241) is an explicitly documented, deliberate diagnostic size-check to avoid parsing gigabytes of page text every preflight cycle — the `if empty == n` condition (all sampled files empty) is a conservative signal that doesn't misrepresent a genuinely mixed cache as broken.
- `reopen_stranded`'s `for k in reopen[:20]: print(...)` (line 327) truncates only the console preview; the actual state mutation `st["done"]["entrypass"] = [k for k in done if k not in set(reopen)]` (line 330) correctly uses the full, untruncated `reopen` list. Its final write (lines 336-341) is correctly atomic via `silence.replace_retry`, with an explicit comment about why (matching `pipeline.py`'s own contract for `PIPELINE_STATE.json`).
- `flush()`'s primary LEDGER write (lines 119-123) is atomic and correctly gated on `replace_retry`'s success before clearing `LEDGER`.

---

## context_budget.py (279 lines)

**CLEAN.** Read in full. No file writes at all — only reads (`prompts/system_style.txt`, `prompts/feats_prompt.txt`), each independently wrapped in try/except with an empty-string fallback, so no two-writer-contract or atomicity concern. No caps/truncation of any roster. The arithmetic in `content_budget_chars`, `measure`, `fits`, `assert_fits`, `feats_block_budget`, and `report` was traced end to end and is internally consistent: `assert_fits` raises `ContextOverflow` rather than returning a value indistinguishable from success, satisfying the project's "no plausible negative result" rule. `split_system_prompt`'s heading-based split degrades safely (returns the whole text as both halves) if the heading is missing, rather than guessing an offset. The one issue this module surfaces is external to it — `health.py`'s preflight check doesn't use it (see overnight.py finding #4 above).

---

## burgs.py (235 lines)

### Confirming the known finding

7. **burgs.py:227 — non-atomic write. VERIFIED.**
   ```python
   p = os.path.join(HERE, "data", "BURGS_SAMPLE.json")
   with open(p, "w", encoding="utf-8") as f:
       json.dump(per_world, f, indent=2, ensure_ascii=False)
   ```
   Bare `open(..., "w")` + `json.dump` directly on a `data/` file, not via `silence.write_json`.

### New finding

8. **burgs.py:230 — the print message contradicts what the code actually writes. VERIFIED.**
   ```python
   worlds = WS.build_all()          # every world; Hard Rule 0
   ...
   per_world = {}
   for w in worlds:
       ...
       per_world[w["designation"]] = bs
   ...
   if args.write:
       p = os.path.join(HERE, "data", "BURGS_SAMPLE.json")
       with open(p, "w", encoding="utf-8") as f:
           json.dump(per_world, f, indent=2,          # every world; Hard Rule 0
                     ensure_ascii=False)
       print(f"\nwrote {p} (sample of 50 worlds; the rest regenerate on demand)")
   ```
   `per_world` is built from `worlds = WS.build_all()` — explicitly commented "every world; Hard Rule 0" — with no slicing anywhere before the `json.dump` call, which itself repeats the same "every world; Hard Rule 0" comment. The data actually written is complete (Hard Rule 0 *is* honored in the artifact). But the very next line's console message tells the operator the opposite: that only "a sample of 50 worlds" was written and "the rest regenerate on demand." This is a stale message (and a stale filename — `BURGS_SAMPLE.json` — left over from an earlier design, presumably before the "every world; Hard Rule 0" fix was made) actively contradicting the code that immediately precedes it. Low severity (the data itself is correct and complete) but exactly the class of comment-vs-code mismatch the project treats as a first-class bug, because an operator reading only the printed output would wrongly believe the file is a 50-world sample and might skip re-running for full coverage, or misjudge the file's size/completeness.

### Clean otherwise

The rank-size math (`burg_count`, `largest_city`, `classify`) was traced and is internally consistent with the documented derivation (`n = (P1/P_min)^(1/q)`). `burgs_for`'s optional `limit` parameter (line 128) does truncate the settlement list when explicitly passed a value, but production callers (`main()`, line 199) never pass it — only `verify_math.py`'s test harness does (confirmed via grep) — so this is a diagnostic/test-only knob, not a live truncation of real data. No concurrency concerns (single-threaded CLI script, no shared-state races).

---

## audit.py (177 lines)

**CLEAN.** Read in full. This is a read-only reporting tool — no writes to any file at all. `audit_invariants()` correctly runs over **every** record and **every** entry with no slicing (confirmed: no `[:N]` anywhere in the invariants pass). The two truncations present are both explicitly-designed, documented diagnostic previews consistent with Hard Rule 0's own carve-out for sampling/ranking-for-display:
- `for x in v[:4]: ... if len(v) > 4: print(... "and {N} more")` (lines 145-148) — prints only 4 example violations per failure class, but `total_f += len(v)` (line 141) and the reported occurrence count both use the full, untruncated list. The undisplayed remainder is explicitly announced ("... and N more"), not silently dropped.
- The `RANDOM SAMPLE` and `BANDED SAMPLE` sections (lines 152-172) are, by the module's own stated design ("SAMPLE — a seeded random draw... Invariants catch violations of rules we thought to write; reading catches the rest"), intentionally a sample for human reading, with a fixed seed for reproducibility — this is the tool's actual purpose, not a violation.

No bugs found in the synthesis-level or entry-level invariant checks; logic was traced and is self-consistent given the fields it reads.

---

## ledger.py (136 lines)

### Confirming the known finding

9. **ledger.py:127-133 — M10 `hi == lo` collapse. VERIFIED, traced independent of assay.py's actual values.**
   ```python
   def assay_to_standards(magnitude_band, ruin_score=5.0):
       from assay import BAND_EDGES, LADDER
       if magnitude_band not in BAND_EDGES:
           return None
       i = LADDER.index(magnitude_band)
       lo = BAND_EDGES[magnitude_band]["ruin"]
       hi = BAND_EDGES[LADDER[min(i + 1, len(LADDER) - 1)]]["ruin"]
       joules = math.exp(math.log(lo) + (ruin_score / 10.0) * (math.log(hi) - math.log(lo)))
       return {"joules": joules, "standards": work_value(joules), ...}
   ```
   For `magnitude_band` equal to the last entry of `LADDER`, `i = len(LADDER) - 1`, so `min(i + 1, len(LADDER) - 1) = i` — `LADDER[i]` resolves to the *same* band, meaning `hi = lo` by construction, purely from the index-clamping logic in this file (does not depend on what `assay.py`'s actual band values are — this holds for whichever band is `LADDER`'s last element, presumably M10). With `hi == lo`, `math.log(hi) - math.log(lo) == 0` identically, so `joules = math.exp(math.log(lo) + 0) = lo` for *every* value of `ruin_score` — the parameter is accepted, appears in the formula, but has zero effect on the result whenever the top band is reached. Confirmed exactly as filed (part of bug M18).

### Clean otherwise

`CURRENCIES`, `CONDENSATES`, `to_standards`, `from_standards`, `cross_rate`, `work_value` were all read and traced — straightforward table lookups and arithmetic, no bugs found. `JOULES_PER_STANDARD` is correctly imported from `physics.MATERIAL` rather than hand-copied (the file's own comment explains why, mirroring the exact anti-pattern flagged elsewhere in this batch for `health.py`'s duplicated context-budget ratios). No file I/O in this module at all — no two-writer-contract or concurrency surface.

---

## Summary table

| # | Location | Status |
|---|---|---|
| 1 | overnight.py:414-455 | CONFIRMED (known) |
| 2 | overnight.py:462 | CONFIRMED (known) |
| 3 | overnight.py:344-347, no stall detection | CONFIRMED (known) |
| 4 | health.py:180-181 vs context_budget.py | NEW |
| 5 | weave.py:205-226 (`>60` skip, live path) | CONFIRMED w/ nuance (known) |
| 6 | health.py:124-144 | CONFIRMED (known) |
| 7 | burgs.py:227 | CONFIRMED (known) |
| 8 | burgs.py:230 | NEW |
| 9 | ledger.py:127-133 | CONFIRMED (known) |
