# BATCH 08 AUDIT — run30

Modules (every line of every file read top to bottom, no sampling):
`feats.py` (1006 lines), `zfighters.py` (485), `tiers.py` (360), `cosmography.py` (282),
`wh40k.py` (244), `recover_folder_records.py` (180), `repass_bands.py` (119).

**COMMITTED SECRETS: NONE FOUND.** Grepped all seven files for API keys, tokens, passwords,
bearer headers, cloud-credential patterns — the only hit was the word "secret" inside Tzeentch's
lore text in `wh40k.py`.

Method: read every file completely before judging. Where a claim could be checked by running
code, it was run read-only against real repo data (no repo file was ever written by this audit)
or against a throwaway scratch directory
(`C:\Users\imarl\AppData\Local\Temp\claude\...\scratchpad\repro_feats\`). Findings are labelled
REPRODUCED, CONFIRMED (verified by direct code inspection / grep, no execution needed to see
it), or HYPOTHESIS.

---

## feats.py

### FINDING F1 — HIGH — REPRODUCED — fixed-name temp file race in `resolve_hosts()` and `evidence_for()`

`resolve_hosts()` (lines 291–299) and `evidence_for()` (lines 807–814) both write shared JSON
state using the OLD hand-rolled pattern:

```python
tmp = HOSTS + ".tmp"          # resolve_hosts, line 296
...
tmp = path + ".tmp"           # evidence_for, line 811
with open(tmp, "w", ...) as f: json.dump(...)
silence.replace_retry(tmp, HOSTS_or_path)
```

`silence.write_json()` (the project's own designated-safe writer, `src/silence.py:290-327`)
exists specifically to fix this: its docstring explains the tmp name must "carry PID and
thread," because two writers of the same path otherwise "collide on the temp file itself, and
the loser can replace the winner's target with a partial file." `resolve_hosts()`'s own comment
(line 291) claims "tmp + replace_retry, not a bare open('w')" as if that were sufficient — it
is not; it is the exact anti-pattern `silence.write_json`'s docstring names.

**Reproduced** (scratch dir, two threads mirroring the exact pattern): two writers racing on a
fixed `path + ".tmp"` name produced (a) a silent LOST UPDATE — one thread's dict entry vanished
from the final file with no error — and (b) worse, an **uncaught `FileNotFoundError`** in the
losing thread, because `silence.replace_retry` only retries on `PermissionError` (`src/silence.py:271-280`);
a `FileNotFoundError` (exactly what happens when the other writer's `os.replace` already
consumed the shared tmp file) propagates unhandled.

```
Exception in thread Thread-1 (worker):
FileNotFoundError: [WinError 2] ... 'HOSTS_sim.json.tmp' -> 'HOSTS_sim.json'
worker_B: replace_retry returned True, wrote keys=['seed', 'source_B_host']
FINAL FILE CONTENT: {'seed': 'orig', 'source_B_host': 'worker_B'}
LOST UPDATE(S): ['source_A_host']
```

**This is not merely theoretical for `evidence_for()`.** `roll()` builds its job list directly
from every entry of every record (`jobs.append((h, r["source"], e["name"]))`, lines 848-853)
with **no de-duplication by (host, name)**. Checked against the real `data/records/` corpus:

```
sources with duplicate entity names: 66   total extra duplicate entries: 981
```
e.g. `adventurers-league.json` has `"Mahadi's Traveling Emporium": 4`, `"Order of the Gauntlet": 3`;
`acquisitions-incorporated.json` has 60 different names each appearing twice. Every duplicate
name in a source becomes a **separate `roll()` job for the identical `(host, name)` cache path**.
Since `evidence_for()` checks the cache, then does real network I/O, then only writes at the
end, two duplicate jobs both starting before either has written will both take the "miss, fetch,
mine, write" path concurrently and race on the same fixed `path + ".tmp"`.

Impact is asymmetric by call site:
- Inside `roll()`, the crash is caught by `work()`'s broad `except Exception` (line 884), counted
  as `errored`, and does not take down the run — self-healing on the next invocation since the
  cache is retried. Net effect: wasted duplicate network fetches, an inflated `errored` count,
  and last-writer-wins content for that entity.
- `resolve_hosts()`'s equivalent write is called directly in `main()` (`--hosts` and the top of
  `--roll`, lines 969-981) **before any ThreadPoolExecutor exists and with no surrounding
  try/except anywhere in `main()`**. If two `feats.py` invocations (e.g. an operator's `--hosts`
  run overlapping a scheduled `--roll`) hit this concurrently, the uncaught `FileNotFoundError`
  would crash the whole script, not just one entity.

This confirms and upgrades sweep29 batch08 finding #7 (`feats.py:293-296, 803-807`, filed
MEDIUM/VERIFIED-BY-READING) — now REPRODUCED live, with concrete evidence the duplicate-job
trigger condition is real in production data, not hypothetical.

**Fix:** route both writes through `silence.write_json()` instead of hand-rolled
`tmp + replace_retry` — it is a drop-in replacement and already the project's designated fix for
this exact defect class.

### FINDING F2 — MEDIUM — CONFIRMED — `discover()`'s allpages/search calls still cap without continuation

Lines 349-350 (`aplimit: "500"`) and 359-360 (`srlimit: "50"`) are real MediaWiki page-size
limits with **no continuation loop anywhere in the file** (grepped for `continue`/`cmcontinue`/
`apcontinue`/`sroffset` — the only handling is `_CAP_BOUND[...] += 1` when a `continue` token is
returned, i.e. measurement, not remedy). The `m82` comment says so itself: "no continuation is
handled." Per Hard Rule 0 ("no cap, no sample... EVER... If something is genuinely too slow, the
answer is more workers... It is never a smaller universe"), a MediaWiki page/search listing that
returns a `continue` token means results were withheld — a real cap on an entry list, only
mitigated by self-measurement rather than eliminated.

Checked `state/roll_auto.log` for real evidence: three logged production rolls all report
`"discovery caps bound: never (m82: aplimit=500 / srlimit=50 did not truncate)"` — so this has
not dropped data in practice to date. Still, the structural gap remains: any entity with more
than 500 evidence-titled subpages or more than 50 relevant search hits would be discovered in
part with no signal beyond a console line in `roll()`'s summary. Note the module's other Hard
Rule 0 fix (the `discover(extra=...)` truncation) IS fully closed and actively drill-tested (see
Clean notes below) — this residual cap on the underlying API calls was not.

### FINDING F3 — MEDIUM (architectural, needs owner ruling) — `api()`'s return contract, and every caller's assumption

**The contract as written today:** `api()` returns `Optional[dict]` — the parsed JSON on
success, or `None` on every failure path: a confirmed 404 (line 157-159, tagged
`"feats.py:api-404"`), 429 with retries exhausted (line 161-166), any other HTTP error with
retries exhausted (line 168-170), or any other exception with retries exhausted (line 171-175).
**All of these distinct situations collapse onto the same `None`.**

Grepped every caller of `F.api(`/`api(` across `src/`:

| caller | pattern used |
|---|---|
| `feats.discover` (x2), `feats.resolve_title`, `feats._page_exists`, `feats.fetch`, `feats.alive` | `(d or {}).get(...)` / `bool(api(...))` |
| `backfill.py:85` (`members()`) | **raises `RosterIncomplete`** on `not d`, by design |
| `backfill.py:182` | `(d or {}).get(...)` |
| `health.py:214` | `if not d or "query" not in d:` |
| `rosetta.py:194` | `(d or {}).get(...)` |
| `scope.py:74` | `(d or {}).get(...)` |

Every call site correctly guards against a crash on `None`. But **only `backfill.py`'s
`roster()`** treats "the API answered nothing" as a distinguishable, escalatable event — its own
docstring names the ambiguity directly: `"F.api() answers None both for 'this page does not
exist' and for a timeout (open bug M16)"`, and it raises rather than returning a possibly-partial
result, specifically because "the two outcomes are indistinguishable in the data." The other
seven-plus call sites (`discover`, `resolve_title`, `_page_exists`, `fetch`'s per-batch loop,
`health.py`'s preflight, `rosetta.scales_for`, `scope.scope_for`) all silently read a transient
failure as "nothing here," which is exactly the class of defect `silence.py`'s own charter exists
to eliminate project-wide (a swallowed failure that looks identical to an honest absence).

This is presented as a characterization for the owner to rule on, per the task's framing, not a
bug to autofix: either (a) `api()` grows a second return channel (raise, or a distinguishable
sentinel) for "retries exhausted on a non-404" versus a genuine confirmed-absent 404, and every
caller but `backfill.roster()` is updated to use it, or (b) the ambiguity is accepted as-is and
`backfill.py`'s workaround is the exception rather than a pattern to spread. Either is a public
signature decision, not something to make unilaterally.

### FINDING F4 — LOW — CONFIRMED — `remine()` is dead code

`remine()` (line 818) has zero callers anywhere in `src/` (grepped `.remine(` / `F.remine(` /
`feats.remine(` — no hits outside its own definition). This matches the function's own
2026-08-25 comment: "This function currently has no callers, which is exactly when a truncation
race is easiest to leave in place and hardest to notice later." It is internally consistent
(already uses the safe `silence.write_json`, unlike F1's finding) and harmless as-is, but it
duplicates logic already inline in `evidence_for()` for no live purpose. Either wire up a real
caller (a "re-tune the gate over cached evidence without a network re-fetch" CLI flag, which is
exactly what its docstring promises) or remove it.

### FINDING F5 — LOW — CONFIRMED — stale `silence.note()` site labels

Several `silence.note("feats.py:NNN")` calls carry line numbers from an earlier revision of the
file and no longer point at their actual location: `"feats.py:139"` is raised from line 172,
`"feats.py:125"` from line 160, `"feats.py:374"` from line 452, `"feats.py:695"` from line 885.
Cosmetic only — the string is a grouping key for `state/failures*.json`, not a live reference —
but on a codebase this disciplined about traceability it makes correlating a failure ledger entry
(e.g. `state/failures_archive.json`'s `"silent:feats.py:139:URLError": 2039`) back to the real
source line slower than it should be.

### Clean, verified

- `discover()`'s Hard Rule 0 fix (the old `extra=25` rank-then-truncate) is genuinely closed: a
  numeric `extra` now raises `SystemExit` (lines 325-328), and this is actively drill-tested —
  `src/verify_math.py:1480-1487` calls `_FT.discover("h", "n", extra=25)` inside a
  `try/except SystemExit` and asserts the refusal fires. Confirmed by reading; this is a real,
  enforced fix with a real regression test, not a paper one.
- `axis_evidence()`/`by_axis()`'s statblock/patient/object gates are real and non-tautological;
  the "hoisted once per sentence instead of once per axis" optimization changes nothing about the
  logic, only its cost.
- `api()`'s 404-vs-other-error note ordering matches its own comment (note fires only after the
  status code is known).
- `main()`'s `--self-test` computes a real, failable condition (`>=5 feats`, `>=1 quantity`, a
  named page present) and returns exit code 0/1 accordingly — not a tautology.
- HOSTS/CACHE writes correctly attempt atomicity via `tmp + replace_retry` even though the tmp
  name itself is the F1 defect — the *intent* (never truncate-in-place a file with live readers)
  is right, the mechanism is the bug.

---

## zfighters.py

### FINDING Z1 — MEDIUM — REPRODUCED — docstring (lines 24-29) makes a false ranking claim

The module docstring states: *"ANDROID 17 ANCHORS AT M7, above Vegeta and every Earth-raised
fighter except Goku."* Ran `compute()`/`value()` live against the actual `ROSTER` data:

```
Vegito           M7    dec=0.63 val=7.63
Android 17       M7    dec=0.60 val=7.60
Gogeta           M7    dec=0.60 val=7.60
Vegeta           M7    dec=0.53 val=7.53
```

Two things are wrong with the claim:
1. Vegeta's `anchor` is **also `"M7"`** (line 54-55) — Android 17 does not anchor "above" him;
   they anchor at the identical tier. The only thing that differs is the assay *decimal*
   (7.60 vs 7.53), which the docstring conflates with the anchor itself.
2. Even taking the claim as being about final rank (decimal-inclusive), it is still false:
   **Vegito ranks above Android 17** (7.63 > 7.60), and **Gogeta ties him exactly** (7.60 = 7.60).
   "Above Vegeta and every Earth-raised fighter except Goku" does not hold even loosely.

The `ROSTER` table and the computed assay values are not themselves wrong — only the narrative
claim in the docstring is. Suggested fix: either drop the "above Vegeta" framing (they're tied at
the anchor level) and correct the "except Goku" list to acknowledge Vegito/Gogeta, or state the
actual, true claim ("Android 17 shares the roster's top anchor and edges out every other
Earth-raised individual — not fusion — fighter").

### Clean, verified

- `compute()`, `value()`, `main()`'s ranking/print logic are correct and match the ROSTER data.
- The Goku-sheet merge in `main()` (lines 435-440) is properly wrapped in `try/except Exception:
  silence.note(...)` — a real failure-observed pattern, not a swallow.
- `data/Z_FIGHTERS.json` write (line 478) uses `silence.write_json` — atomic, compliant with the
  two-writer contract for shared state.
- wh40k.py's parallel comment (line 230-236) about "the sibling one module over" being fixed
  first is accurate — this file's write WAS separately made atomic, confirmed by reading.

---

## tiers.py

### FINDING T1 — HIGH — CONFIRMED (structural) — the containment/monotonicity self-check never gates the write

`main()` (lines 320-332) computes:
```python
ok = all(counts[i] >= counts[i + 1] for i in range(len(counts) - 1))
print(f"   monotone: {ok}")
...
print(f"   containment violations (a lower group split across two higher ones): {bad}")
```
and then, unconditionally, at line 354: `silence.write_json(out, charted, indent=2, ...)`.
Grepped lines 317-356 for any gating construct (`raise`, `SystemExit`, `assert`, `sys.exit`,
`return 1`, `if not ok`, `if bad`) — **zero matches**. `main()` always `return 0`. There is no
code path in this file, at any value of `ok`/`bad`, that refuses to write `TIERS.json` or that
even calls `silence.note`/`health.record` on failure — the finding is not caught by anything
below the level of a human reading stdout.

Ran `chart()` live (read-only, no write) against the real corpus: `counts=[168, 8, 6]`,
`monotone: True`, `bad: 0`. **The invariant currently holds** — `TIERS.json` is not presently
corrupted by this gap. But the module's own docstring calls containment essential ("A tier that
does not contain its own members is not a tier," repeated twice, once for the metaverse-cut fix
and once for the hyperverse-grounding fix) and the check that is supposed to defend it has no
enforcement path — a future data change (a re-run of `weave.py`'s index, a threshold edit, a
grounding update) that broke monotonicity or containment would still print "monotone: False" /
"containment violations: N" to a console nobody is required to read, still write `TIERS.json`,
and still exit 0. This is precisely the "check that computes ok/bad and never asserts" pattern —
and per this project's own escalation doctrine (`CLAUDE.md` Hard Rule -1), it doesn't even reach
the bottom JANITOR rung ("record it") since nothing is recorded to `health`/`silence`, only
printed.

**Fix:** at minimum, call `silence.note("tiers.py:containment")` when `bad > 0` or `ok` is
`False` so it surfaces in the failure ledger; for a real gate, refuse the write (`raise
SystemExit`) or set `return 1` and let the escalation chain (`escalation.py`) decide the
appropriate rung, consistent with how `feats.py`'s own `--self-test` already fails loudly.

### Clean, verified

- Module-level asserts (lines 119-120) are real and non-vacuous: `assert all(a[1] > b[1] ...)`
  checked against the actual 2-element `CUTS` list (100.0 > 50.0 → True) and
  `assert MULTIVERSE_THRESHOLD >= CUTS[0][1]` (102.3 ≥ 100.0 → True) — both would actually fire
  on a misconfiguration, per the historical bug they were written to prevent (documented in the
  comment above them).
- `deliberate_joins()`'s Hard Rule 0 fix is real: the function returns the whole `shared.get((a,
  b), [])` list, not a `[:3]` slice — confirmed by reading; matches its own docstring's account
  of the fix.
- `hyperverse_of()` is accurately self-described as "Diagnostic only -- NOT the hyperverse" and
  is consumed exactly once, for exactly that diagnostic field (`own_grounding`).
- `_groundings` load failure is properly observed (`except Exception: silence.note(...)`).
- `unaddressed[:6]` in `main()`'s print (line 311) is display-only — the full, uncapped
  `len(unaddressed)` is printed immediately before it, and nothing downstream (`TIERS.json`)
  is truncated. Compliant with the display-only exception to Hard Rule 0.

---

## cosmography.py

**No findings.** This module is clean. `validate()` (lines 215-253) performs five real,
non-tautological physical-consistency checks (Type III can't exceed galaxy count, Type II can't
exceed star count, Type I can't exceed habitable-world count, extant civilizations can't exceed
life-bearing worlds, `KARDASHEV_MIX` must sum to 1.0) and `census()` (line 169-212) **actually
raises `ValueError`** if any of them fail — this is an enforced check, unlike tiers.py's T1. The
occupancy-ratio computations correctly guard divide-by-zero (`if c["galaxies"] else None`, etc).
No caps, no truncated listings, no dead code, no stale comments found. `GALAXIES_DEFAULT`,
`ETA_EARTH` and the `KARDASHEV_MIX` correction (the docstring's own account of the 2026-08-20 fix
for the "six galaxy-spanning empires per galaxy" bug) all check out against the code as written.

---

## wh40k.py

**No findings.** Verified the docstring's specific numeric claims against `ROSTER`: Tzeentch does
have the highest `transgression` among the four Chaos Gods (9.9 vs Nurgle 9.0, Khorne 7.0,
Slaanesh 8.5) and the lowest `volition` ("worst discipline": 6.0 vs 8.5/9.5/7.5) — both true,
unlike zfighters.py's Z1. All four Chaos Gods anchor `"M7"` and the Emperor `"M6"`, matching the
docstring's framing exactly ("the four anchor at M7 ... and the Emperor at M6"). `data/
WH40K_ASSAYS.json` write uses `silence.write_json` — atomic, compliant. No caps, no dead code.

---

## recover_folder_records.py

Repair/one-shot tool — audited specifically for destructive-overwrite risk, two-writer-contract
compliance, and caps, per the task's instructions.

### FINDING R1 — MEDIUM — HYPOTHESIS (not currently firing, checked directly) — overwrite decided by a flag, never by the file's real content

The record write (lines 143-160) is unconditional once a source is selected: it never reads the
pre-existing file at `path` (if any) to check what is actually on disk before replacing it. The
sole gate for "is this source empty and therefore safe to (re)write" is
`roll_entry.get("entry_count", 0) == 0` in the separately-maintained `data/SWEEP_ROLL.json`.

This project's own `resync_roll.py` names `recover_folder_records.py` by name as one of four
scripts whose roll-writing behavior can drift the roll away from the real record files ("every
cataloguer ... rewrites the whole roll ... two of them running concurrently will have one clobber
the other's counters with a stale copy read minutes earlier"), citing a real incident where a
concurrent write reset two sources' real entry counts (425 and 681 entries) back to 0 while
leaving their record files untouched. If `recover_folder_records.py` were ever run against a roll
snapshot that is stale in that direction — showing `entry_count: 0` for a source that in fact
already has a real, researched record on disk — it would silently **replace the real record with
the deliberately thinner register-transcription**, with no error, no diff, and no signal beyond
the record file's content having changed.

Checked directly against the current repo (read-only): only 6 rows in `data/SWEEP_ROLL.json`
currently show `entry_count == 0`, and **0 of those 6** have a mismatched non-empty file already
on disk — so this is not corrupting anything today. But the code has no defense if that ever
becomes untrue (e.g. run right after a fresh cataloguing session and before anyone runs
`resync_roll.py`). Suggested fix: before writing, `if os.path.exists(path)`, load it and refuse
(or merge) if its own `entries` is non-empty, rather than trusting the roll flag alone — the same
discipline `pipeline.write_record_catalogue` provides for its own callers (see R2).

### FINDING R2 — MEDIUM — CONFIRMED, self-acknowledged, tracked across four prior sweeps

Records are written via raw `silence.write_json` (line 155) rather than
`pipeline.write_record_catalogue`, which is the two-writer contract's designated path for writing
to `data/records/`. The script's own comment (lines 145-148) already discloses this: "the
two-writer contract says a RECORD should be written through `pipeline.write_record_catalogue`,
not straight to disk at all. Making the write atomic is the safe half of that repair; routing
this recovery tool through the catalogue writer changes its merge semantics and is flagged in
NEXT_STEPS." Confirmed present in sweep22 (batch03), sweep24 (batch04, downgraded to
"MINOR (self-documented, half-fixed)"), and sweep28 (batch12, "LOW, present but
self-acknowledged in-code"). The atomicity half genuinely is fixed now (`silence.write_json`,
unlike the bare `open("w")` sweep22 originally found) — what remains open is exactly the
merge-semantics gap that R1 above shows is not merely cosmetic: `write_record_catalogue`'s merge
logic is precisely the mechanism that would prevent R1's overwrite scenario. Recommend the owner
confirm whether a live NEXT_STEPS tracking item still exists for this, since the current
half-fixed state is now four sweeps old.

### FINDING R3 — LOW — CONFIRMED — stale comment citing a nonexistent file

Line 54: `"Matches ingest.py's slug(), so recovered files land where the cloud session would have
put them."` **There is no `src/ingest.py` in this repository** (only `ingest_doc.py`, a
different tool with its own, different `slug()`). The actual `slug()` implementation here is
byte-for-byte identical to `catalogue_web.py`, `catalogue_aurora.py`, and `catalogue_codex.py`'s
`slug()` (all `re.sub(r"[^a-z0-9]+", "-", s.lower()).strip("-")[:60]`) — so the *behavior* is
correctly matched to the real cataloguers, and there is no functional bug, but the comment
attributes it to a file that doesn't exist (or was renamed away at some point and never updated
here).

### FINDING R4 — LOW — HYPOTHESIS, not currently live — 60-character slug truncation could collide two sources

`slug(s)[:60]` (line 59) truncates; two roll source names sharing an identical first-60-character
slug would silently write to the same path, with the second write overwriting the first's real,
recovered record with no error or warning — the exact same class of hazard as R1 but from a
different cause. Checked against the real 215-source `SWEEP_ROLL.json`: no such collision exists
today (the longest name is 82 characters — "Who Framed Roger Rabbit (incl. all content from its
associated crossover-toon IPs)" — and its 60-char slug prefix is unique among all 215). Purely
theoretical at present.

### Clean, verified

- `EXCLUDED_REGISTER_SOURCES = {"ME"}` is verified **accurate** against the real register:
  `LOCAL_REGISTER.json` holds exactly 7 items under `source: "ME"`, and all 7 are indeed
  "Trickster" archetype D&D features (Distracting Curse, Extended Protection, Harvest their
  Anger, Instatly Annoying, Reactive Casting, Trickster Spells, and the Trickster archetype
  itself) — matching the comment's justification precisely.
- The write-denial gate (lines 149-157, "GATE ON THE WRITE") correctly checks
  `silence.write_json`'s boolean return and explicitly skips updating the roll entry on a denied
  write, printing `WRITE DENIED` and `continue`-ing rather than marking a phantom success —
  matches its own comment's account of the run #25 fix.
- No cap anywhere on the actual repair work: the `mapped` list (every `(register_source,
  declared_count)` pair) and `by_source.get(register_source, [])` are iterated in full for every
  source; `--dry-run` correctly performs zero writes; `FOLDER_SOURCE_MAP.json` is consumed
  whole, not sliced.
- No duplicate `name` keys exist in `SWEEP_ROLL.json` (checked: 215 rows, 215 unique names), so
  the `roll_by_name[name]` direct-index lookup (line 127) cannot silently pick the wrong row.

---

## repass_bands.py

**No findings.** This is the cleanest file in the batch.

- Writes go through `PL.write_record(path, rec)` (line 84) — the correct, two-writer-contract
  path for records, unlike `recover_folder_records.py`'s R2. The write's boolean return is
  checked and a denial is reported rather than silently counted as applied (lines 84-87, "GATE ON
  THE WRITE," matching its own account of a run #25 fix identical in shape to F1/T1's pattern
  elsewhere in this batch).
- Demotion touches only `synthesis["provisional_magnitude"]`/`synthesis["demoted_by"]` and
  `entry["magnitude"]`/`entry["scale_note"]` — verified by reading every line of the loop body
  (lines 43-87) that no other field is ever written. This matches the docstring's explicit
  promise ("The entry keeps its name, description, topic and category; it loses a claim nobody
  had earned") exactly — a repair tool that actually keeps its stated destructive footprint
  minimal.
- No cap on the actual repair: `PL.records()` and `rec["entries"]` are iterated in full for every
  record. The only truncations in the file (`kept_entries[:14]`, `demoted_entries[:8]`, lines 102
  and 108) are report-sample prints in the console summary; the real counts driving the summary
  (`total_banded`, `len(kept_entries)`, `len(demoted_entries)`, `by_band` Counter) are all
  computed over the full, untruncated lists first. Compliant with the display-only exception to
  Hard Rule 0.
- `--apply` correctly gates every mutation; without it the script is a pure dry-run report.

---

## Summary table

| # | Sev | File:line | Status | Finding |
|---|-----|-----------|--------|---------|
| F1 | HIGH | feats.py:296,299,811,814 | REPRODUCED | Fixed-name temp file race (no PID/thread scoping); `replace_retry` doesn't catch `FileNotFoundError`, so a losing writer crashes uncaught. 981 real duplicate-entity jobs across 66 sources make this a live trigger inside `roll()`, not theoretical. |
| F2 | MEDIUM | feats.py:349-350,359-362 | CONFIRMED | `discover()`'s allpages/search calls cap at aplimit=500/srlimit=50 with no continuation loop — a real Hard Rule 0 tension, empirically never bound in 3 logged production rolls (`state/roll_auto.log`). |
| F3 | MEDIUM | feats.py:121-176 + 9 callers | CONFIRMED (architectural) | `api()`'s `None` conflates confirmed-404 with transient-failure-exhausted; only `backfill.roster()` works around it (raises `RosterIncomplete`); 8 other call sites treat both the same. Owner ruling needed. |
| F4 | LOW | feats.py:818 | CONFIRMED | `remine()` has zero callers anywhere in src/ — dead code, self-admitted in its own comment. |
| F5 | LOW | feats.py:172,160,452,885 | CONFIRMED | `silence.note()` site labels carry stale line numbers from an earlier revision. |
| Z1 | MEDIUM | zfighters.py:24-29 | REPRODUCED | Docstring claims Android 17 anchors above Vegeta and outranks every Earth-raised fighter but Goku; live computation shows Vegeta shares the same M7 anchor, and Vegito (7.63) actually outranks Android 17 (7.60), Gogeta ties him exactly. |
| T1 | HIGH | tiers.py:320-354 | CONFIRMED | Monotonicity/containment self-check computes `ok`/`bad`, prints them, and never gates the `TIERS.json` write — no raise/assert/exit path exists. Currently passes on real data (ok=True, bad=0, live-verified) but has no enforcement if it ever doesn't. |
| R1 | MEDIUM | recover_folder_records.py:143-160 | HYPOTHESIS (checked, not firing today) | Record overwrite trusts only the roll's `entry_count==0` flag, never the real on-disk file content; `resync_roll.py` names this exact script as a documented roll-staleness risk with a real past incident. 0/6 current empty-roll rows are mismatched. |
| R2 | MEDIUM | recover_folder_records.py:155 | CONFIRMED, self-acknowledged, 4 prior sweeps | Writes records via raw `silence.write_json` instead of `pipeline.write_record_catalogue`, bypassing its merge-against-concurrent-copy protection — the exact protection that would close R1. |
| R3 | LOW | recover_folder_records.py:54 | CONFIRMED | Comment cites `ingest.py`'s `slug()`, a file that does not exist in this repo. |
| R4 | LOW | recover_folder_records.py:59 | HYPOTHESIS, not live | `slug()[:60]` could collide two long source names onto one file; no collision exists among the current 215 sources. |

**Clean modules, no findings:** `cosmography.py`, `wh40k.py`, `repass_bands.py`.

**Hard Rule 0 caps identified:** F2 only (feats.py discover, mitigated by measurement, empirically
inert to date). All other apparent truncations in this batch (`_show()`'s `[:6]`/`[:4]`,
`tiers.py`'s `unaddressed[:6]`, `repass_bands.py`'s `kept_entries[:14]`/`demoted_entries[:8]`)
were checked individually and are provably display-only — the underlying repair/data work and
the persisted files they feed are computed over full, untruncated collections.
