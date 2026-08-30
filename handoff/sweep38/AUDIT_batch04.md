# SWEEP 38 — AUDIT, batch 04

Agent: `sweep38-batch04`. Run: `run38`. 7 modules, 4,466 lines, all read in full.

Modules: `standards.py`, `rosetta.py`, `handbuilt.py`, `axis_correlation.py`,
`retry_synthesis.py`, `catalogue_models.py`, `halo.py`.

Everything below was verified against the code as it stands today (2026-08-29), not against an
older audit. Where a fault was cheap to demonstrate it was demonstrated; the reproductions live
in the batch scratch directory (`repro_band.py`, `repro_names.py`) and their output is quoted
inline.

---

## standards.py (2,141 lines) — read in full

The file is in good shape: the `_dropped` mechanism now covers twenty-odd handlers, the
`UNMEASURED is a reading, silence is not` doctrine is applied consistently across the
data-file-backed standards, and every declared floor is genuinely reachable (`MIN_CALLS_TO_JUDGE_RATE`
derived from `tuning`, `CHARTER_REGRESSION_MAX_AGE_H` used inside the pulled-out verdict, the
self-check searching the whole file rather than from `def check(` onward). Purity extractions
(`context_verdict`, `resident_context`, `model_matches`, `charter_regression_verdict`,
`provider_pool_denominator`, `job_stamp`) all look correct and all check their own inputs.

### FINDING — a printed field is cut at 18 characters, in the expression whose own comment forbids it

`check()`'s `every source is fully catalogued` standard builds its `worst:` detail as

```
detail = "; ".join("%s %.1f%%" % (str(c["source"])[:18], 100 * c.get("coverage", 0))
                   for c in worst)
```

The comment directly above it (`standards.py:1364-1368`) says **"ALL OF THEM, WORST FIRST -- not
`[:3]`"** and cross-references the `[:3]`/`[:60]` fix on the unrecognised-pool standard. The list
is indeed uncapped — and every *name* in it is truncated. Three other standards in this same file
were repaired for precisely this shape: `[:120]` on the promotions name list (`:1672`),
`resident[0][:28]` on the runner standard (`:1721`, "ranking is allowed here, truncating is not"),
`[:60]` on the unrecognised-pool error text (`:1575`).

Measured against the live `data/COMPLETENESS.json` (216 rows):

```
total rows 216   names longer than 18 chars: 89   colliding truncated forms: 0
  Arcanum Worlds (Odyssey of the Dragonlords)  -> 'Arcanum Worlds (Od'
  Critical Role (Tal'Dorei Campaign Setting)   -> 'Critical Role (Tal'
  Curious DM Investigations (the Sharkin)      -> 'Curious DM Investi'
```

No two names collide today, so nothing is currently *ambiguous* — but the same order text tells
its reader to run `catalogue_web --recatalogue --shortfall 100` largest-gap-first, and the sibling
roster standard tells them to run `hostcheck.py --purge --go --source NAME`. A name cut mid-word
cannot be pasted into a `--source` argument, which makes the field unusable as the identifier the
remedy needs.

The same file carries a second instance at `:604`, in `provider_pool_denominator`'s derived
branch: `str(r.get("error") or "no model list")[:40]` cuts the reason a provider went unverified,
on the field the order text tells the reader to read.

Filed as `STD_WORST_NAME_CUT` (MINOR / LOCAL).

### QUESTION — the fabrication standard goes red whenever the reader is legitimately down

`sentences that survive the verbatim check` (`:1106-1147`) emits `holds=False`,
`observed="UNMEASURED -- the reader has logged no progress line yet"` whenever
`jobs["corpus read"]` is absent. The comment at `:1102-1105` argues for exactly this
("UNMEASURED is a reading; silence is not").

Two hundred and fifty lines earlier, the four corpus-read standards make the **opposite** call on
the **same input**: `:844-859` routes an absent reader to `_dropped` rather than emitting red,
with the written reason that "the reader is a main-lap job that is legitimately DOWN between
supervisor laps" and that a red row would dispatch a remedy against a job nothing is wrong with.

The distinguishing factor named there is whether the standard carries a `foreman.REMEDIES` entry.
`sentences that survive the verbatim check` does not appear in `REMEDIES` (checked:
`foreman.py:1059-1096`), so `round_once` routes it to `log["owner"]` — a recurring HIGH row in the
owner's file for a condition that is not a fault. That is the shape `standards.py:1830` itself
complains about for the `include_self` bug: "The standard has no remedy, so the false name went to
the owner's file every round and hid the one job that was genuinely down."

Both readings are defensible and both are written down, so this is a question, not a finding.
Filed as `STD_FAB_UNMEASURED_ROUTING` (INFO / OWNER).

### Checked and clean

* `ollama_token_flow` — the config-derived `num_ctx`, the `eval_count` predicate, the
  build-vs-probe split and the `_flow_failure` branch table all behave as documented; the
  `return None, None` build-failure path correctly does **not** poison `_TOKENFLOW`.
* `fandom_ipv4_reachable` — memo keyed by `(host, timeout)`, value stamped with the finish time,
  `_sk` stub bypasses the memo in both directions, `ttl=0` forces a fresh probe. Matches the
  docstring exactly.
* `job_stamp` / the job-advance block — the carried-forward stamp on an unstattable log, the
  `unmeasurable` list kept out of `watched`, and the `raise` on a denied `write_json` are all
  correct; the `kill_stalled_job` parse-safety note about the phrasing holds.
* The feats-per-chunk parse (`:826-831`) was checked against `dashboard.RE_READ` and
  `dashboard._read_row`'s actual `detail` format — `"N/N entities · N feats · R chunks/s"` — and
  the digit-strip yields the right number.
* `every declared floor is measured` — the comment-stripped, word-bounded, whole-file,
  second-appearance rule is right, and the `(?:[A-Z][A-Z0-9]*_)*M(?:IN|AX)_` pattern does catch
  `CHARTER_REGRESSION_MAX_AGE_H`.
* `main()` builds one state dict and hands it to both `report()` and `work_orders()`.

### Observations, not filed

* `report()` re-prints a group heading whenever rows of one group are non-contiguous (the `pool`
  group appears three times, since `every pool failure is recognised` and `model IDs their
  providers still serve` are emitted far below the first five). Cosmetic.
* `dashboard.py:226` cites `standards.py:663` for the `read.get("raw")` bug; line 663 today is
  `per_hour = tp.get("per_hour", 0)`. `dashboard.py` is another batch's module, so this is left
  here as a note rather than filed, to avoid a duplicate order.

---

## rosetta.py (635 lines) — read in full

The parsers and the arithmetic are sound: `numeric_rows` is row-structural rather than
proximity-based with a documented prose fallback, `ordinal_rows` matches case-insensitively on the
original text (the `str.lower()` offset-drift fix), `spearman` averages ties, `assays_by_host`
splits the `host|Name` key and reports its collisions, `refine` scopes per host and rejects
progression ladders by dynamic range, and `--check` now carries its verdict in the exit code. The
`MINE_FLOOR` guard and both `silence.write_json` gates are correct and their verdicts are read.

### FINDING — three caps and three mid-name cuts on the CLI output

* `--probe` (`:457-459`): `sorted(...)[:6]` keeps six rows per scale and `n[:34]` cuts each name.
* `--refine` (`:567-569`): `sorted(...)[:12]` keeps twelve hosts, and
  `', '.join(sorted(scales))[:44]` cuts the joined scale-title list mid-title.
* `--check` (`:606,613`): `r['scale'][:38]` cuts the scale title on both the scored and unscored
  lines.

None announces what it cut. This is the shape `standards.py:1575` and `catalogue_models.py:215`
both record removing, and `catalogue_models.py`'s note is directly on point: "The persisted copy
being complete does not help someone looking at the terminal."

Live evidence from today's `data/ROSETTA.json` (6 hosts, 8 scales, 230 rows) — the `[:44]` is
**already cutting**:

```
     13  callofduty.fandom.com    Ranks/Call of Duty: Black Ops 6, Ranks/Call    <-CUT
```

The `[:12]` host cap does not bind at 6 hosts, but `--mine` asks 191 hosts and the module's own
history records an 8-wiki / 3,514-row mine.

Filed as `ROSETTA_CLI_CAPS` (MINOR / LOCAL).

### FINDING — `--probe` cannot tell a blocked wiki from an empty one

`scales_for(host, verbose, errors)` grew its `errors` parameter (order 6447bcc2f18c) precisely
because the function "CANNOT otherwise distinguish 'this wiki publishes no scale' from 'we were
not allowed to look': both end at `if not seen: return {}`". `--mine` passes a list and prints
every failure by name. `--probe` (`:456`) does not pass one, so the single interactive mode a
person uses to ask "does this wiki publish a scale?" prints nothing and exits 0 on a throttled,
429'd or blocked wiki — indistinguishable from a genuinely empty one.

Filed as `ROSETTA_PROBE_ERRORS` (MINOR / LOCAL).

### Observation, not filed

`check()` writes `"ambiguous_assay_names": len(collided)` onto every row, where `collided` is
computed from the **global** normalisation even when `by_host` scoping is in force — so under the
scoped path (the only path `main()` uses) the per-row number counts collisions that cannot bite
that row. The docstring acknowledges the distinction; the field does not. No live consumer reads
the field, so it is recorded here rather than queued.

---

## handbuilt.py (495 lines) — read in full

Nine hand-built sheets, each with its `why_missed`, its `presence` paragraph, per-axis provenance
marks and cited evidence. `compute()` is correct; the `"unestimable"` sentinel is handled by the
`isinstance` guard at `:486` and by `assay.py`'s status machinery; the write-before-print ordering
is deliberate and documented; the `replace_retry` verdict is read and turned into `rc=1`.

### FINDING — a hand-rolled fixed `.tmp`, in a tree that has a helper for exactly this

```python
tmp = OUT + ".tmp"
with open(tmp, "w", encoding="utf-8") as f:
    json.dump(out, f, indent=1, ensure_ascii=False)
if not silence.replace_retry(tmp, OUT):
```

`silence.write_json`'s docstring names this shape by name — "THE TMP NAME CARRIES PID AND THREAD,
which the older hand-rolled `path + '.tmp'` sites did not. Two writers of the same path otherwise
collide on the temp file itself, and the loser can replace the winner's target with a partial
file" — and `standards.py:1521` and `retry_synthesis.py:47` each record being repaired for it.
`halo.py`, `wh40k.py` and `zfighters.py`, this module's twins, all route through `write_json`.

Second cost: `write_json` discards its temp when the replace is refused (`silence.py:461-472`,
added because "EVERY denied write leaked one `<path>.<pid>.<tid>.tmp` beside its target"). This
hand-rolled site leaks `data/HANDBUILT_ASSAYS.json.tmp` on every denied replace with no cleaner.

Filed as `HANDBUILT_TMP_WRITE` (MINOR / LOCAL).

### FINDING — `--full` cuts each cited quotation at 58 characters

`:489`: `d["cited"][:58]`. `--full` exists to show the evidence a score rests on, and the
citations run to 250+ characters ("CEILING, AND EARNED TWICE OVER. He is not merely hard to
kill — he DIES ON SCREEN AND RETURNS…"). Nothing marks the cut.

Filed as `HANDBUILT_CITE_CUT` (MINOR / LOCAL).

---

## axis_correlation.py (397 lines) — read in full

The cleanest module in the batch. `_no_matrix`'s three channels and its once-per-site dedup are
right, `write()` gates on `write_json`'s verdict and `main()` turns a denial into `rc=1`,
`_scores_of` handles both on-disk shapes purely, `observations()` reports which sources it read
and which it did not, `_pearson` refuses a constant column, `rho()`'s two branches are documented
against orders c00cab9d0412 and 1b29e38dbb17, and `--top` defaults to all-of-them and announces
what it cut. No caps, no discarded verdicts, no fail-open handlers.

### FINDING — two stale citations in the docstrings

* `observations()` (`:170`): "All seven SOURCES exist today" — `SOURCES` has held **eight** entries
  since run #34 added `data/ASSAYS.json` (`:82`). All eight exist on disk today (checked).
* `main()` (`:376`): "`mean_r` is None when no pair cleared MIN_N (measure(), line ~157)" —
  `measure()` begins at line 207 and the `mean_r` expression is at 229. The citation is ~72 lines
  out and lands inside `_scores_of`'s docstring.

Filed as `AXCORR_STALE_CITES` (INFO / LOCAL).

---

## retry_synthesis.py (301 lines) — read in full

`save_side`'s re-read-then-merge, the returned landed-verdict, `stranded_sources()` selecting on
the condition rather than the cause, `do_merge`'s routing through `PL.write_record`, and both
non-zero exit paths are all correct and all match their documentation. `--smallest` is honestly
labelled a pilot order rather than a cap, and the default is the full run.

### FINDING — the band gate is NOT the pipeline's, despite the module's central claim

`synthesise()` (`:162-164`) cleans the model's band with its own regex:

```python
m = re.match(r"^(M(?:10|[0-9]))\b", band)
band = m.group(1) if m else "unassayed"
```

`pipeline.phase_synthesis` (`:1111`) uses `clean_band()`, which is a **fullmatch** —
`pipeline.py:146-149`, docstring "The band a value actually is, or 'unassayed'. **Never a prefix
of one.**" The retry's regex is the shape of `ceiling_band()`, the *deliberately laxer* clamp-side
reader whose docstring says "Acceptance is strict, clamping is forgiving; the asymmetry is the
point."

Reproduced (`repro_band.py`):

```
model said         pipeline     retry_synthesis
'M7'               M7           M7
'M10'              M10          M10
'M7.3'             unassayed    M7             <-- DIVERGES
'M4 (planetary)'   unassayed    M4             <-- DIVERGES
'M9 -- universal'  unassayed    M9             <-- DIVERGES
'm7'               unassayed    unassayed
'M11'              unassayed    unassayed
' M6 '             M6           M6
```

This is the exact drift the function's own docstring says was already closed once: "THE DOCSTRING
HERE USED TO SAY 'byte-identical prompt construction to phase_synthesis' AND IT WAS NOT TRUE", and
the transport divergence (`ask` vs `ask_pool_first`) beside it. The block rule and the prompt now
come from `pipeline`; the acceptance gate still does not. The persisted `method` string asserts
"same prompt and same invariants as the main synthesis phase", which is a claim written into every
rescued record.

Filed as `RETRY_BAND_GATE_DRIFT` (MAJOR / LOCAL).

### Observations, not filed

* The retry's synthesis dict omits the `assessed_at` key `pipeline.py:1136` writes, so a record
  merged by `--merge` carries a synthesis block shaped differently from every other one. Nothing
  in `src/` reads `assessed_at` today (grepped), so this rides along in the order above as a
  secondary note rather than as its own finding.
* `valid_scale_note(ev)` is evaluated on the already-`[:600]`-truncated evidence, where
  `pipeline.py:1115-1116` evaluates it on the untruncated string. The prompt asks for "at most 20
  words", so this cannot bite in practice.
* `load_side()` has no handler: a corrupt `SYNTHESIS_RETRY.json` raises out of `main()`. That is
  fail-closed and is the right direction.

---

## catalogue_models.py (285 lines) — read in full

The four-outcome model (`LISTED` / `EMPTY_LIST` / `UNREACHABLE` / `UNCONFIGURED`), the
`unverified` list with its `unchecked` counts, the `counts` block, the printed denominator and the
gated write whose verdict becomes `main()`'s exit code are all correct, and they line up exactly
with what `standards.provider_pool_denominator` expects to read. The `/v1/v1/models` guard and the
"a 200 with an empty list is an answer" branch are both right.

### FINDING — two drifted line citations, and two surviving truncations of the error text

* `:175` cites `standards.py:1400` for the "0 stale in the cloud pool" line. `standards.py:1400`
  today sits inside the *catalogue-coverage* remedy text; the provider-models standard is at
  `standards.py:1905-1997` and the reading it means is at `:1958-1977`.
* `:216` says the `[:8]` cap was "fixed at line 151 in run #26". That fix is at `:208` today;
  line 151 is inside the `LAST_WRITE_LANDED` comment block.
* `:130` stores the provider's failure reason as `str(e)[:70]` — a cap on a **persisted** field
  (`providers[].error`, `unverified[].why` in `data/PROVIDER_MODELS.json`), which
  `standards.py:604` then cuts again to `[:40]`.
* `:235` prints `u['why'][:52]`, cutting that reason a third time on the console line whose whole
  purpose (`:224-226`) is to say *why* each provider could not be asked.

Filed as `CATMODELS_CITES_AND_CUTS` (MINOR / LOCAL).

---

## halo.py (212 lines) — read in full

Three sheets, per-axis provenance marks (the `zfighters.py` pattern, correctly applied — `wiki`
only where the sentence is verbatim), the M6-not-M7 reasoning stated in the module docstring, and
a gated `silence.write_json` whose denial becomes `rc=1` with an accurate message. All eleven
`assay.WEIGHTS` axes are present in all three sheets (checked), and every score is numeric, so
`--full`'s `%5.1f` cannot hit the `TypeError` `handbuilt.py:481-487` was repaired for.

### FINDING — `--full` cuts each cited quotation at 54 characters

`:192`: `d["cited"][:54]`, unmarked. Same fault and same remedy as `handbuilt.py:489`. The
Precursors' continuity citation — "CEILING, AND THE CLEANEST CASE IN THE LIBRARY. The Forerunners
'rose to seize the Mantle BY KILLING ALMOST EVERY PRECURSOR' -- and the survivors came back as the
Flood…" — renders as its first 54 characters.

Filed as `HALO_CITE_CUT` (MINOR / LOCAL).

---

## Summary

| module | lines | read in full | findings |
|---|---|---|---|
| standards.py | 2,141 | yes | 1 finding, 1 question |
| rosetta.py | 635 | yes | 2 |
| handbuilt.py | 495 | yes | 2 |
| axis_correlation.py | 397 | yes | 1 (stale citations) |
| retry_synthesis.py | 301 | yes | 1 (MAJOR) |
| catalogue_models.py | 285 | yes | 1 |
| halo.py | 212 | yes | 1 |

No module in this batch was skimmed, sampled or grepped in place of being read.
