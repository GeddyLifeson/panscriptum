# Batch 10 audit — run36

Modules: `assay.py`, `health.py`, `handbuilt.py`, `reference.py`, `sevenfold.py`, `anchors.py`,
`cosmology_graph.py`, `ledger.py`, `module_index.py`

All nine read in full (line counts checked against the 3804-line batch total before starting:
1148+634+495+411+327+280+226+172+111 = 3804, matches).

---

## assay.py (1149 lines) — closest read, per instructions

This module is unusually well self-audited already: nearly every historical defect (the X.11
faculty-weight-zero erratum, the halved-interval sigma bug, the silent-axis-drop gap, the
`_check_constants` monotonicity/ceiling guards, the `calibration_report` shared-state sigma
mutation, the `_rho` fallback provenance) carries its own long comment explaining what broke and
why the current code is correct. I read every one of those and did not find any of them to be
wrong or stale.

**1. `denom = sum(W[k] for k in applicable) or 1.0` (line 864) — CONFIRMED, per the guidance
already given for this run.** The comment directly above it (lines 856-863) already documents
that this guard is reachable only through the public `weights=` override, and I reproduced it
independently before reading that conclusion:

```
assay.assay('M3', {'ruin': 5.0}, worksheet='w', weights={'ruin': 1.0, 'celerity': -1.0})
-> 𝔄 M3.50 ± 0.45, axis_coverage=1.0, interval=0.45
```

Without the `or 1.0` fallback this call raises `ZeroDivisionError`; with it, `axis_coverage`
prints `1.0` (perfect coverage) off a denominator substituted for a real zero, which is a
plausible-looking number standing in for "the caller's weight table cancelled itself out." I
also checked reachability from production code: the only real caller that supplies `weights=`
is `custodes.py:253-257` (`_custos_reading`), which builds its table as
`A.WEIGHTS[k] * emph.get(k, 1.0)` where every `axis_emphasis` value in `CUSTODES` is a positive
multiplier (1.05–1.45, `custodes.py:109-216`) — so in the live pipeline this path is not
currently exercised; it is only reachable by a caller constructing `weights=` by hand (a script,
a drill, a future feature). Confirming this as already-known rather than re-filing it new.

**2. Weight tables that can sum to zero.** No *built-in* weight table (`WEIGHTS`,
`CHARTER_PHYSICAL_WEIGHTS`, `FACULTY_WEIGHTS`, `ATTESTATION_FLOOR`) can sum to zero — all entries
are fixed positive constants. The only route to a zero/negative-sum table is the public
`weights=` parameter itself, which (per point 1) is validated nowhere — `_check_scores` validates
`scores` against the table, never the table's own values. This is the same finding as point 1
from a different angle: there is no guard on `weights=` itself, only on what's scored against it.
QUESTION rather than a new defect, since it's the identical reachable-but-unexercised surface
already flagged for this run.

**3. `axis_score()` saturating at 9.9 instead of 10.0`** (line 231, `round(10.0 * max(0.0,
min(1.0, frac)), 2)` — max frac is 1.0, giving 9.9 not 10.0 after rounding *only* because 10.0
capped at frac=1.0 gives exactly 10.0 — wait, re-checked: `10.0 * 1.0 = 10.0`, not 9.9). On
inspection this doesn't actually saturate below 10.0 arithmetically; the "M18, its own open bug"
comment at `AXIS_MAX` (line 316-322) is the module's own citation of a known, already-filed
issue, not something I'm re-diagnosing. Leaving as already-known per that comment.

No other defects found in `assay.py`. `_check_constants()` (import-time) verifies monotonicity
and the ceiling correctly; `calibration_report()`'s sweep uses `sigma=` per-call rather than
mutating the shared table (confirmed no `SIGMA_BY_ATTESTATION` mutation anywhere in the sweep
loop); `_rho_doc()`'s fallback-and-announce behaviour is correctly one-shot-cached and stamped
onto every assay via `correlation_source`.

---

## health.py (635 lines) — MAJOR, new finding

**`flush()` (lines 89-201) races `record()` (lines 75-86) on `LEDGER` (and identically on
`_SAMPLES`), and the race is real, not theoretical.**

`_LOCK = threading.Lock()` (line 66) exists and is used correctly inside `record()`:
`with _LOCK: LEDGER[key] += 1; ...`. But `flush()` never acquires `_LOCK` anywhere in its body —
it does `for k, v in LEDGER.items(): prev[k] = prev.get(k, 0) + v` (lines 123-124) completely
unguarded, then later `LEDGER.clear()` (line 152), and the identical shape again on `_SAMPLES`
(`for k, ring in _SAMPLES.items():` line 185, `_SAMPLES.clear()` line 198).

`flush()` is reachable from any thread: `silence.note()` (silence.py:409-430) calls
`health.record()` then, every `FLUSH_EVERY` calls, `health.flush()` — and `silence.note()` is
called from `except` bodies threaded throughout the tree, including inside the
`ThreadPoolExecutor` worker functions in `feats.py`, `hosts.py`, `hostcheck.py`, `wiki_source.py`,
`endpoint.py` etc. So two worker threads can legitimately be inside `record()` and `flush()` at
the same moment.

Reproduced directly (six writer threads calling `health.record()` with varying keys, one thread
iterating `LEDGER.items()` the way `flush()` does, no other synthetic elements):

```
errors: 235
RuntimeError('dictionary changed size during iteration')  x5 shown, 235 total
```

`Counter` is a `dict` subclass; a writer inserting a *new* key (the common case here — failure
`detail` strings vary by hostname/exception/etc., so the key space is not fixed and small) while
`flush()` iterates raises `RuntimeError: dictionary changed size during iteration`.

**Where this lands:** the periodic call is `silence.note()`'s own `_SINCE_FLUSH >= FLUSH_EVERY:
health.flush()`, and that whole call is inside `note()`'s blanket `try/except Exception: pass`
(silence.py:410-430) — so the RuntimeError is silently swallowed. The practical effect: the
`for k, v in LEDGER.items(): ...` loop aborts partway through, before `silence.write_json(...)`
is ever reached (line 151), so `state/failures.json` — "the highest-traffic shared file in the
project" per this file's own comment at line 126-130 — silently fails to update for that flush
cycle under exactly the concurrent-worker conditions the project runs in most often. `LEDGER` is
not cleared (the crash is before `.clear()`), so counts aren't lost, only delayed and the flush
attempt is wasted; but because the crash is inside the unguarded read/aggregate loop and not
caught locally, every one of the extensive, carefully-built write-hardening comments in `flush()`
(the `.corrupt` preservation logic, the pid+thread temp name, the landed/not-landed gate) never
gets a chance to run on an affected cycle. This is the module whose entire premise is "make
failures loud," and this specific failure mode is invisible — no `health.record()` call
documents it, because the crash happens inside the recorder itself, upstream of where it would
record anything.

**Fix shape** (not applied — read-only audit): `flush()` needs to snapshot-and-clear `LEDGER`
and `_SAMPLES` under `_LOCK` (e.g. `with _LOCK: snap = dict(LEDGER); LEDGER.clear()`) before
doing any of the unguarded disk-write work, the same pattern `record()` already uses for the
increment side.

---

## handbuilt.py (496 lines) — nothing new found

Nine hand-built entities (The Undertaker, IRS, Zalama, Molecule Man, Rune King Thor, The Sentry,
The Black Winter, Getter Emperor, Mister Mxyzptlk), each with a full 11-axis worksheet or an
honest `unestimable` where evidence doesn't support a number (Zalama scores 5 of 11). `compute()`
iterates the whole `ROSTER` dict with no cap. The write path is correctly ordered (JSON lands via
`silence.replace_retry` *before* any console printing, specifically because `moth_number` opens
with a non-cp1252 character that used to crash the process mid-report before the write — the
comment at lines 444-452 explains this and it's correct) and its verdict is checked (`if not
silence.replace_retry(tmp, OUT): ... return 1`).

One thing worth naming as a QUESTION, not a defect: in `main()`'s `--full` printout, `d["cited"]
[:58]` (line 489) truncates the citation text for console display. This is display-width
truncation of a preview, not a data cap — the full text is already in the JSON that was written
moments earlier — so it doesn't read as a Hard Rule 0 violation, but it's adjacent enough in
shape to flag for a second opinion.

---

## reference.py (411 lines) — MINOR, new finding: stale claim

`main()`'s `--compare` path prints, unconditionally (lines 396-406):

> "per-axis SCORES are not persisted by the assay pass, so a per-axis diff cannot be\ncomputed
> ... (b03f2ab9951a)."

This is now false for any `ASSAYS.json` row computed after 2026-08-26. `assay.py`'s own `assay()`
return dict was extended under **that same order id, b03f2ab9951a** ("THE PRIMARY MEASUREMENT,
PERSISTED (added 2026-08-26, order b03f2ab9951a)", assay.py lines 895-915) to include a `"scores"`
key — the per-axis numeric readings, keyed by axis. `magnitude.py:997` stores the *whole*
`assay()` return dict as `"result": res` into `ASSAYS.json`, so `row["result"]["scores"]` is
present for any post-fix row. `reference.py`'s `--compare` loop reads `got = row.get("result")`
(line 378) and uses `got.get("axes_scored")` (line 387) but never `got.get("scores")` — the field
the fix it cites was written specifically to add. The order id in the comment matches the fix
that closed the gap it's describing; the comment (and the printed user-facing message) was
apparently never revisited once that fix landed one day earlier. Cosmetic/documentation-only —
nothing crashes and no data is lost — but the printed message actively misinforms whoever runs
`--compare` today about what's available to diff, and the per-axis diff column the comment says
"cannot be computed" now can be, at least for fresh rows.

No other issues found. `shelfmark()`'s length-clamp (lines 254-257) is a real bounds guard (not
a tautology — the three hardcoded entries all happen to fit `RUNGS`, but a future entry with a
different `tier_key`/`lower_rungs` length would not, and the clamp plus `silence.note` correctly
handles that rather than raising).

---

## sevenfold.py (328 lines) — nothing new found

Also unusually self-documented (the "no signal to read" degenerate-gaps fix at `seams()`, the
`UNSHELVED` accounting for sources present in `worldseed` output but absent from the resonance
graph, the discarded-verdict fix on `--write` at lines 316-322). Checked each of those claims
against the current code and they hold.

The `sorted(coords)[:8]` / `sorted(worlds)[:8]` slices in `main()` (lines 306, 310) are
explicitly labelled "sample shelfmarks" in the printed output, and `--write` persists the
complete, uncapped `coords`/`worlds` dicts to `SEVENFOLD.json` (line 320) — so this is a labelled
console preview, not a Hard Rule 0 violation; noting it only because it's the kind of slice this
sweep is told to look at closely.

`m30`-tagged comment at line 290-294 ("`ok = 'OK' if hi <= SPAN else 'OVER SPAN'`... this
displays a GUARANTEE, not a discovery") — checked: `seams()` genuinely clamps `k = max(1,
min(span, len(block)))`, so this branch cannot currently fire. Correctly labelled as such by the
module's own comment rather than presented as a live check; not a tautology-passed-off-as-a-test.

---

## anchors.py (280 lines) — QUESTION only, already known

Confirmed the item flagged in this run's guidance. `run()` calls `CU.convene(a["anchor"],
a["scores"], attestation=a["attestation"], worksheet="anchors.py")` (lines 190-191) without ever
passing `distance`/`years_since`. `custodes.staleness_widening()` (custodes.py:276-292) returns
`0.0` whenever either is `None`, and `convene()` defaults both to `None`. Checked every other
call site of `custodes.convene()` in the tree (`verify_math.py`, and `anchors.py` itself) — **no
caller anywhere in `src/` ever supplies `distance`/`years_since`**, so Lumen's staleness
contribution (the whole point of the "dispersive, not directional" tilt=0 design at
custodes.py:199-207) is dead weight in every live computation, always contributing exactly 0.0
to `half` in `convene()`. This matches the guidance's description exactly ("its staleness
widening always adds exactly 0.0 in production"). Reporting as the QUESTION it was flagged as,
not as a new defect: it isn't clear from the code alone whether this is (a) a feature nobody has
wired a caller for yet, or (b) evidence the whole Lumen-staleness mechanism was designed but the
distance/years_since inputs were never plumbed through from wherever an entity's real-world
observation lag would be known. Not resolving it here per instructions.

The five anchors themselves (Skate Guy, Goku, Seat of the Creator, A Sword, Yggdrasil) and the
monotone floor-to-ceiling invariant read correctly, including the fixed exit-code bug documented
at the bottom of the file (`_rows, _ok = run(); sys.exit(0 if _ok else 1)` — confirmed this is
what actually runs, not a discarded `ok`).

---

## cosmology_graph.py (226 lines) — MAJOR, new finding: discarded write verdict

`main()`'s `--write` path (lines 198-218) calls `silence.write_json(OUT, {...}, indent=2,
ensure_ascii=False)` and **discards the return value** — it is not assigned to a variable, not
checked with `if`, nothing. Immediately after, lines 219-222 print unconditionally:

```
print(f"\nwrote {OUT}")
print(f"  pairs written : {len(ranked):,} of {len(pair_w):,} (all of them, unfiltered)")
...
```

`silence.write_json`'s own docstring (silence.py:358-377) is explicit: "Returns True if the file
landed. Never raises on a denied replace" — a denied `replace_retry` (the WinError-5-class
failure this whole codebase has hardened against repeatedly, including twice more in this same
batch's `health.py`) is the expected, documented failure mode, and this call site has no branch
for it at all. Compare the two sibling modules in this same batch that get this right:
`sevenfold.py:320-322` (`landed = silence.write_json(...); print(...) if landed else
print("WRITE DENIED...")`) and `health.py:151` (`if silence.write_json(LEDGER_PATH, prev, ...):
LEDGER.clear()`).

This module's own docstring (lines 59-67, 188-197) is unusually emphatic that
`SHARED_STAGE_GRAPH.json` must never silently regress — it recounts, at length, an earlier bug
where an undeclared `if w >= 1.0` dropped 71% of pairs while the file still claimed
`"threshold": 3.0`, and states plainly at line 189: "propagation.py and resonance.py both read
SHARED_STAGE_GRAPH.json live, so a truncate-then-fill here hands them an empty graph they would
silently trust." The write is correctly made atomic via `write_json` (no truncate-then-fill
risk), but the *verdict* of that atomic write is thrown away — so on a denied rename (a reader
holding the file, which is exactly the condition this codebase's own comments describe as
routine on Windows), the script prints "wrote {OUT}" and a full breakdown of pair/cluster/source
counts as though the fresh graph landed, while the file on disk is still whatever
`SHARED_STAGE_GRAPH.json` held before this run. `propagation.py`/`resonance.py` would then read
a stale graph while every visible signal (exit code 0, "wrote ..." on stdout) says the refresh
succeeded.

Not applying a fix per the read-only mandate; flagging the exact site: `cosmology_graph.py`,
lines 199-222, `silence.write_json(OUT, {...})` call with no captured/checked return value.

---

## ledger.py (172 lines) — nothing found

Small, clean module (the Ledger Standard / currency conversion table). `JOULES_PER_STANDARD` is
imported from `physics.MATERIAL["rock"]["pulv"]` rather than hand-copied, closing exactly the
kind of drift risk this sweep watches for. `currency_status()` / `to_standards()` /
`from_standards()` correctly distinguish "unlisted" from "listed but deliberately
non-convertible" per their own docstrings, and every currency table entry (`CURRENCIES`,
`CONDENSATES`) is a fixed positive rate or an explicit `None` with a stated reason — no
divide-by-zero surface. `assay_to_standards()`'s M10-ceiling handling (extrapolating the M10 band
width from the M9→M10 ratio rather than collapsing `hi == lo`) is a real, already-fixed bug per
its own comment (lines 154-163); verified the arithmetic does what the comment claims (`hi = lo *
(lo/prev)`, giving M10 the same log-width as the M9→M10 gap, anchored at M10's own floor).

---

## module_index.py (111 lines) — MINOR, new finding: stale entry in GROUPS

`GROUPS["The corpus"]` (line 35) lists `"wikipedia_source"` as a module name. **No
`src/wikipedia_source.py` exists** — only `src/wiki_source.py` does, and that name is already
listed separately in the same group (line 33). Checked every other name across all six `GROUPS`
lists against the actual contents of `src/*.py`: `wikipedia_source` is the only entry that
doesn't resolve to a real file.

This is functionally harmless — `main()`'s `rows = [(n, first_line(mods[n])) for n in names if n
in mods]` (line 68) filters on `n in mods`, so the phantom entry is silently skipped, never
raises, and doesn't cause any module to go unlisted (real modules not in any `GROUPS` list still
surface under the generated "Everything else" section via `rest = sorted(set(mods) - placed)`).
But it's exactly the category of drift this module's own docstring calls out as the reason it
exists at all ("a hand-kept copy of information the code already carries is a second writer with
no merge strategy" — and `GROUPS` itself is exactly such a hand-kept copy, just of module names
rather than descriptions). Likely a leftover from a rename (`wikipedia_source` → `wiki_source`,
or a planned split that never happened) that nothing ever caught because the failure mode is
silent by construction.

The write path here is otherwise correct: pid+thread temp name, `silence.replace_retry`'s verdict
is checked and a denied write correctly returns exit code 1 with a message naming the file as
stale rather than claiming success (lines 92-104) — this module does NOT have the
discarded-verdict defect found in `cosmology_graph.py` above.

---

## Modules NOT read

None — all nine modules in the batch list were read in full.
