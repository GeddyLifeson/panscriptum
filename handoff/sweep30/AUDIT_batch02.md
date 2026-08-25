# AUDIT — batch 02 (run30)

Files: `src/pipeline.py`, `src/entity_match.py`, `src/coverage.py`, `src/audit.py`,
`src/resync_roll.py`. Read top to bottom, in full, before any finding below was written.
No secrets found in any of the five files.

No committed secrets found.

## KNOWN OPEN ITEM — verdict: REFUTED, no longer live

Claim: the entity cache path collides distinct entities at `pipeline.py:636` and
`coverage.py:44-46` (`Ten-Towns` vs `Ten Towns`, `Vár` vs `Vör`).

Both cited spots are **comments describing the historical M23 bug**, not live collision code.
The actual mechanism at both sites now routes through `src/cachekey.py` (M23 fix, dated
2026-08-25 in its own docstring):

- `pipeline.py:642` — `_mined_feats()` calls `cachekey.load(base, host, e["name"], on_corrupt=...)`,
  which opens each candidate path and calls `cachekey.owns(doc, name)` (exact-name equality
  against the stored `entity` field) before trusting the file. A collision now produces a MISS,
  not a wrong hit.
- `coverage.py:52,95,132` — `_p()` calls `cachekey.natural_path`, `state_of()` iterates
  `cachekey.candidate_paths()`, and `_state_of_file()` gates on `cachekey.owns(d, name)` before
  counting a file's feats/pages as evidence for `name`.

REPRODUCED: grepped all five files for the old inline sanitiser pattern
(`re.sub(r"[^A-Za-z0-9]+", ...)`, `A-Za-z0-9`, `sanitis`) — zero hits outside `cachekey.py`
itself. Every read/write path in this batch that touches the per-entity cache goes through
`cachekey`'s ownership-verified helpers. `Ten-Towns` vs `Ten Towns` still fold to the same
filename (`cachekey.name_stem` is deliberately unchanged, by design, to avoid a mass rename),
but a reader can no longer be handed the wrong entity's feats: a mismatch is a cache MISS that
gets re-mined, not a merge.

**Residual risk carried over from the same lossy-fold pattern, in a different file**: see
`resync_roll.py` finding R-1 below — the SAME class of bug (fold-and-collide, no ownership
check) exists today, unfixed, one layer up (source names, not entity names).

---

## src/pipeline.py (1975 lines)

### P-1. HIGH — fixed-name temp file race across `write_record`, `write_record_catalogue`, `land_json`, `save_state`
**Lines:** 186 (`save_state`), 462 (`write_record_catalogue`), 499 (`land_json`), 564 (`write_record`)
**REPRODUCED**

All four writers build their temp path as `tmp = path + ".tmp"` — a name that depends only on
the destination path, with no PID or thread disambiguator — then either call
`silence.replace_retry(tmp, path)` (via `_landed`) or, in `land_json`/`save_state`'s siblings,
the same pattern. `write_record` and `write_record_catalogue` are explicitly two different
functions invoked from two different processes on the *same* `data/records/*.json` path — that
is the whole premise of "the two-writer contract" the module's own comments describe at length
(pipeline vs. `catalogue_web.py`/`catalogue_aurora.py`/`catalogue_codex.py`/`backfill.py`/
`ingest_doc.py`, confirmed by grep: all call `P.write_record_catalogue` or `PL.write_record` on
`data/records/*.json`).

`src/silence.py`'s own `write_json()` docstring (lines ~250-269) names this exact defect and
says it was fixed there by putting the PID and thread in the tmp name:

> "THE TMP NAME CARRIES PID AND THREAD, which the older hand-rolled `path + ".tmp"` sites did
> not. Two writers of the same path otherwise collide on the temp file itself, and the loser can
> replace the winner's target with a partial file."

`pipeline.py`'s own two-writer functions are exactly the "older hand-rolled" sites that fix
describes, and they were not updated to match. I reproduced the mechanism directly (two threads
racing on a shared `path+".tmp"` name in the scratch directory, mimicking two processes):

```
PermissionError: [Errno 13] Permission denied: '...\race_target.json.tmp'
replace failed: PermissionError [WinError 32] The process cannot access the file because
it is being used by another process: '...\race_target.json.tmp' -> '...\race_target.json'
```

Two consequences, both real:
1. `open(tmp, "w")` itself can raise `PermissionError` when the other writer already holds that
   exact tmp path open — this is **not caught** anywhere in `write_record`,
   `write_record_catalogue`, or `land_json` (only the final `os.replace`, inside
   `silence.replace_retry`, has a try/except, and that only catches `PermissionError`, not
   `FileNotFoundError`). A crash here takes down the whole phase run (caught one level up by
   `main()`'s `except Exception: log("PHASE CRASHED..."); return`, so the process exits rather
   than corrupting state, but the run stops).
2. `silence.replace_retry` only catches `PermissionError`. If writer B's `os.replace` already
   consumed the shared `tmp` file (renamed it away) before writer A's `os.replace` runs, A's
   call raises `FileNotFoundError`, which `replace_retry` does **not** catch — propagates as an
   unhandled exception.

**Why it matters:** this is precisely the "two authors writing one file" failure the module's
own header calls "this project's defect in its most literal form" (re: `HANDOFF.md`), and the
fix for it elsewhere in the same sweep (`silence.write_json`) is not applied to the four
functions that are the sanctioned writers for the two-writer contract itself.

**Suggested fix:** give the tmp path a PID/thread suffix (mirror `silence.write_json`'s scheme)
in all four functions, e.g. `tmp = f"{path}.{os.getpid()}.{threading.get_ident()}.tmp"`, and
widen `silence.replace_retry`'s except clause (or add a `FileNotFoundError` branch) so a
consumed-by-someone-else tmp is treated as "the other writer already landed the newer content"
rather than propagating.

### P-2. HIGH — `_ACT` verb whitelist is missing the most common defeat verbs; real feats are wrongly rejected to "unassayed"
**Line:** 941 (`_ACT = re.compile(...)`), used by `valid_scale_note` (line ~1016) via `_act_upon_object`
**REPRODUCED, against real corpus data**

`_ACT` lists: destroy, annihilate, obliterate, shatter, erase, unmake, raze, level, vaporize,
incinerate, disintegrate, sunder, split, cleave, collapse, wipe out, blow up/apart, conquer,
subjugate, reshape, rewrite, drain, consume, devour. It does **not** contain `defeat`, `slay`,
`crush`, `vanquish`, `topple`, `overthrow`, `slaughter`, or `overpower` — plain "who-beat-whom"
verbs that are the backbone vocabulary of exactly the kind of contest evidence this project's
Chain of Defeats phase (`phase_chain`) exists to harvest.

Grepped the real corpus (`data/feats/*/*.json`) for these verbs' file counts:

```
defeated   -> 11604 files
crushed    ->  1591 files
slew       ->  1206 files
vanquish   ->   576 files
toppled    ->   281 files
```
(a wider grep across the remaining candidate verbs timed out after these 5 of 9 patterns;
already conclusive)

Ran `pipeline.valid_scale_note()` directly against clearly-scaled synthetic feats using these
verbs:

```
'' <- defeated an entire army single-handedly
'' <- slew the dragon that terrorized the kingdom
'' <- crushed the rebellion within a single day
'' <- vanquished the demon lord and his legions
'' <- toppled the empire that had stood for a thousand years
'' <- defeated a god in single combat
```

Every one is rejected outright (returns `""`), forcing `magnitude` to `"unassayed"` even though
each names an act (defeat/slay/crush/vanquish/topple) performed by the subject upon a
scale-bearing object that IS in `_OBJECT` ("army", "empire" via no match — actually "empire" is
not even in `_OBJECT` either, compounding the miss). Contrast with an in-list verb:

```
'destroyed the city of Metropolis' <- destroyed the city of Metropolis   (passes)
'shattered the moon with a single blow' <- shattered the moon with a single blow  (passes)
```

**Why it matters:** `valid_scale_note` is the single gate deciding whether a mined feat can ever
carry a Magnitude band, for both phase 1 (`phase_synthesis`) and phase 2 (`phase_entrypass`), and
`audit.py`'s own core invariant re-checks entries against this same function. A verb gap this
large (11,604+ files containing "defeated" alone) means a large, unmeasured fraction of
genuinely evidenced defeats are silently discarded as unassayed, undercounting exactly the
"suffered defeat" evidence class Charter Part Three names as one of three kinds — the same class
`phase_chain` (`chain.harvest()`) separately mines from prose, so this gap is likely compensated
for on the *chain* side but not on the *entrypass/synthesis* band-gate side, meaning the two
passes can disagree for no principled reason.

**Suggested fix:** add `defeat(?:ed|s)?|slew|slain|slay(?:s|ing)?|crush(?:ed|es|ing)?|vanquish(?:ed|es)?|topple[ds]?|overpower(?:ed|s)?|slaughter(?:ed|s)?|overthrew|overthrown|overthrow(?:s|n)?` to `_ACT`, and re-run the 225-entry-style backscan the module's own comment describes to confirm the false-negative rate before/after.

### P-3. MED — comment directly contradicts the code it is documenting, using its own worked example
**Lines:** 1003-1010 (`_SETTING_META` comment) vs. `valid_scale_note` (line ~1016) / `_ACT` (line 941)
**REPRODUCED**

The comment immediately above `_SETTING_META` says, using its own example:

> `"overthrew the Titans roughly 500 years before the campaign's start"` is a genuine deed
> wearing one wrong word. **The feat survives**; the wording is flagged so the write phase
> rephrases rather than the evidence being thrown away.

Ran it through the actual code:

```
>>> P.valid_scale_note("overthrew the Titans roughly 500 years before the campaign's start")
''
```

It does **not** survive — `overthrow/overthrew` is absent from `_ACT` (see P-2), so
`_act_upon_object()` never fires and the whole note is discarded before `scale_note_needs_rephrase`
(which is only ever called on notes that already passed `valid_scale_note`, per its one real
caller in `audit.py:97`) is reachable. The comment describes a design intent — reject on
*wording*, not on *substance* — that the code does not implement for this exact example. This
is the same root cause as P-2, filed separately because the comment's claim is independently
checkable and independently false regardless of how P-2 is fixed.

**Suggested fix:** fix P-2 (add `overthrow`/`overthrew` to `_ACT`) and re-verify this exact
example survives `valid_scale_note` and then trips `scale_note_needs_rephrase`, or rewrite the
comment to match current behaviour if the rejection is in fact intended.

### P-4. MED — `update_handoff`'s file write bypasses the two-writer contract's sanctioned atomic-write path
**Lines:** 1382, 1385
**REPRODUCED (by reading; matches the contract text verbatim)**

```python
tmp = HANDOFF + ".tmp"
with open(tmp, "w", encoding="utf-8") as f:
    f.write(md)
os.replace(tmp, HANDOFF)
```

This is a raw `os.replace`, not `silence.replace_retry` — every other atomic write in this same
file (`_landed`, used by `write_record`/`write_record_catalogue`/`land_json`) goes through
`silence.replace_retry` specifically because "on Windows the rename is DENIED while any reader
holds the target open" (silence.py:224-229), and `HANDOFF` (`handoff/RUN_STATUS.md`) is read by
exactly the kind of concurrent reader that comment warns about (dashboards, `--status` calls).
The whole `update_handoff` body is wrapped in `except Exception: log(...)`, so a `PermissionError`
here does not crash the run — but unlike `replace_retry` it never retries with backoff, so a
transient reader collision costs this update outright rather than surviving a brief wait, and
(per the two-writer rule quoted in the task) `handoff/RUN_STATUS.md` is a shared state file that
should land only via `silence.replace_retry` / `silence.write_json`.

**Suggested fix:** `return silence.replace_retry(tmp, HANDOFF)` instead of the bare `os.replace`.

### P-5. LOW/MED — Hard Rule 0: fallback chunk in `phase_synthesis` truncates instead of chunking
**Line:** 765

```python
chunks = [with_feats[i:i + 14] for i in range(0, len(with_feats), 14)] or [rest[:14]]
```

The `with_feats` branch (feat-bearing entries) is explicitly chunked so **every** entry is
eventually nominated across calls — the surrounding comment says so in capitals ("no feat-bearing
entry is ever excluded from nomination"). The fallback branch, used only when a source has *no*
feat-bearing entries at all, takes `rest[:14]` and stops: entries 15+ of `rest` (sorted by
description length, longest first) are never shown to the model, in any call, ever. This is a
`[:N]` slice on a ranked, ordered entry list with no continuation — the exact shape Hard Rule 0
prohibits ("ranking-then-truncating is NOT" allowed).

**Mitigating context:** the surrounding comment gives a real reason (a lead-paragraph-only
source is unlikely to have its ceiling entity beyond the 14 longest descriptions, per the
project's own measurement that description-only nomination is weak evidence generally — see the
long comment above `phase_synthesis`). That is a judgment call about where evidence is likely to
be, not a display or pagination construct, so it does not qualify for the stated exception.

**Verdict:** VIOLATION of Hard Rule 0 as literally stated, though weakly consequential (only
applies to sources with zero feat-bearing entries, and only entries ranked 15+ by description
length within those sources).

**Suggested fix:** chunk `rest` the same way `with_feats` is chunked (`[rest[i:i+14] for i in
range(0, len(rest), 14)]`), or, if the cost tradeoff is intentional, say so explicitly next to
the slice itself (not just in the paragraph above) and get an owner ruling recorded the way the
`with_feats` fix cites "owner 2026-08-24: FIX IT ALL" immediately above it.

### Clean areas in pipeline.py
- `clean_band`/`_CLEAN_BAND` (full-match only) is correct and was verified live: `clean_band("M4.31 +/- 0.30")` → `"unassayed"`, `clean_band("m4")` → `"unassayed"` (case-sensitive, correct — the model is asked for `M0`-`M10` exactly), `clean_band("M4")` → `"M4"`.
- `ceiling_band`'s deliberately-laxer prefix match is documented as asymmetric-by-design (clamp only ever lowers a band) and I could not find a path where it is used to raise or launder a band — it is only read into `syn` for a min-clamp comparison.
- `entry_settled` / `batch_settled` — the resume-gate consolidation (run #20 finding) is sound and self-consistent; excluded entries correctly count as settled.
- `ask_pool_first` / `_pool_answer_usable` — correctly distinguishes "cloud answered nothing usable" from "cloud is down" and only falls back to local on the former after logging it; no swallowed distinction here.
- `records()`, `_mined_feats()` — bounded, exception-safe, no caps on the returned list.
- Phase 5/6/7 (`phase_cosmology`, `phase_history`, `phase_shelve`) correctly distinguish "absent" (tolerate, proceed with `{}`) from "corrupt" (refuse, leave phase open) per their own BUGS-m6-referencing comments — checked each `except FileNotFoundError` / `except Exception` pair by hand; none of them collapse the two the way the comments say used to happen.
- No committed secrets.

---

## src/entity_match.py (278 lines)

Clean module. `candidates()` defaults `limit=None` and only truncates on an explicit caller-
supplied limit, always setting `truncated` accordingly — compliant with Hard Rule 0's own
carve-out language almost verbatim.

Verified live (REPRODUCED):
```
qualifier_compatible('Ten-Towns', 'Ten Towns') -> (True, None)
candidates('Ten-Towns', ['Ten Towns', 'Ten-Town', 'Icewind Dale'])
  -> Ten Towns scored 1.0 "exact", Ten-Town scored 0.933 "strong" — proposed, not merged
candidates('Wally West (New Earth)', ['Wally West (New Earth)', 'Wally West (Prime Earth)',
           'Wally West (Earth-16)', 'Wally West'])
  -> only the exact New-Earth match scores; Prime Earth and Earth-16 are blocked_by_qualifier
     (qualifier-conflict x2), the bare name is blocked (qualifier-missing x1). Zero score leakage.
```
This confirms the module's central safety claim (the three Wally West continuities never score
against each other) holds in the live code, not just in the docstring.

**Dead-code note (not a defect):** grepped the whole `src/` tree — the only importer of
`entity_match` is `verify_math.py` (its own self-test harness). The module's docstring already
says "nothing calls this module yet" and explains why (it is a proposal-only seam awaiting a
caller). This is accurately self-documented, not a silently-rotting dead function, so I am not
flagging it as a finding — noting it here only so the next reader does not have to re-derive it.

No caps beyond the documented, flagged `limit`. No writes at all (pure functions). No secrets.

---

## src/coverage.py (219 lines)

### C-1. MED — `_so_save()` discards `replace_retry`'s failure signal, marking a lost write as done
**Lines:** 74-85, specifically 82-83

```python
_sil.replace_retry(tmp, _SO_CACHE_P)
_SO["dirty"] = 0
```

`silence.replace_retry` returns `True`/`False` and is documented as "never raises on a denied
replace... the caller's write lands next round" — i.e. callers are expected to check the return
value and NOT consider the write done if it is `False`, exactly the pattern `pipeline.py`'s own
`_landed()` implements two lines away in a sibling module of the same sweep. `_so_save()` ignores
the return value entirely and unconditionally sets `_SO["dirty"] = 0` right after the call. If
the rename is persistently denied (Windows reader collision — the documented, real-world trigger
in `silence.py`'s own docstring), the in-memory dirty flag is cleared as if the persist
succeeded, so **no later `_so_save()` call in this process will ever retry it** — this run's
cache updates for potentially many entities are silently lost from disk, even though
`replace_retry` itself does still call `note("replace-denied:...")` internally (so it is not
completely invisible — `health.record` gets an entry — but `coverage.py`'s own bookkeeping treats
it as a non-event).

**Why it matters less than a HIGH:** `_SO["d"]` (the in-memory dict) is not cleared, so within
the SAME process, later reads still see the correct memoized values — the only cost is that a
later, separate invocation of `coverage.py`/`drill.py` re-parses those files from scratch,
regressing the exact "874MB corpus" performance problem this cache exists to solve, without any
correctness impact on `COVERAGE.json` itself (which is written unconditionally, via
`silence.write_json`, from freshly-computed `rows`, not from the disk cache).

**Suggested fix:** `if not _sil.replace_retry(tmp, _SO_CACHE_P): return` (leave `dirty` set so
the next `_so_save()` call in this or a later run retries), mirroring `_landed()`'s pattern.

### Hard Rule 0 review of `report()` — verdict: compliant (display-only), one nit
**Lines:** 189 (`[:12]`), 194 (`[:show]`, default 26), 199 (`[:10]`)

All three are terminal-print truncations inside `report()`. The persisted artifact
(`data/COVERAGE.json`, written at `main()` line 213 via `silence.write_json(OUT, rows, ...)`)
contains every row from `measure()` — `rows` itself is never capped, filtered only by the
`have = [r for r in rows if r["host"] and r["entries"] >= 40]` relevance filter (a substantive
filter on attributes, not a roster-length cap, so not a Hard Rule 0 concern on its own). Because
the full, untruncated data reaches disk and every other consumer named in the code comment
(dashboard, standards, allsweep, published page), these three `[:N]` slices are display-only
truncations of a human-facing terminal report and fall under the stated exception.

**Nit (not a violation):** unlike `audit.py`'s equivalent sample printer, which prints
`"... and N more"` after a truncated list, `report()`'s three truncated sections give no
indication that more rows exist beyond what's printed. Cosmetic only — recommend matching
`audit.py`'s convention for consistency.

### Clean areas in coverage.py
- Known-open-item collision claim: REFUTED, see top of this report — `_p()`, `state_of()`,
  `_state_of_file()` all correctly route through `cachekey`'s ownership-verified helpers.
- `_state_of_file()`'s cache key (`os.path.relpath(fp, HERE) + "|" + name`) correctly
  disambiguates path+name, matching its own M23 comment.
- `main()` writes `OUT` via `silence.write_json` — compliant with the two-writer/shared-state
  contract.
- No secrets.

---

## src/audit.py (177 lines)

Clean. Read-only report generator; no writes at all, so the two-writer contract does not apply.

`audit_invariants()` re-derives every gate from outside `pipeline.py`'s own enforcement code
(`PL.valid_scale_note`, `PL.meta_violations`, `PL.TOPICS`, `PL.CATEGORIES`, `PL.BANDS`) rather
than trusting flags the pipeline already set — exactly the "checked from outside" design the
module docstring claims, and I did not find a place where it instead trusts a flag it should be
re-deriving.

**Hard Rule 0 review — verdict: compliant.** `fails[k]` (the invariant-violation lists) are
never truncated internally; the `for x in v[:4]: ... if len(v) > 4: print("... and N more")`
pattern (lines 145-148) is a textbook-correct display-only truncation with an explicit remainder
count, and the two random samples (`args.sample`, default 14; `min(10, len(banded))`) are
explicitly, by the module's own docstring, "a seeded random draw ... printed in full so a person
can read actual rows" — a deliberate sampling method for human review, not a silent cap on a
roster that claims completeness. This is the pattern the rest of the codebase should be pointed
at as the correct way to do a bounded print.

No secrets. No dead code (both `audit_invariants` and `main` are reached from `__main__`).

---

## src/resync_roll.py (81 lines)

### R-1. MED — `norm()` fold-and-collide key with no ownership check (same class of bug as the M23 entity-cache collision, unfixed here)
**Line:** 50 (`by_source[norm(src)] = (rec, fn)`), key function at line 27

```python
def norm(s):
    return "".join(c for c in (s or "").lower() if c.isalnum())
```

This strips **all** punctuation and whitespace and lowercases — the identical shape of fold that
`cachekey.py`'s own docstring names as the root cause of the M23 entity-collision bug
("`Magic 8 Ball` and `Magic 8-Ball` become the same file"). Here it operates one layer up, on
**source names**, to match `SWEEP_ROLL.json` roll entries to `data/records/*.json` files. Unlike
`cachekey`, there is no ownership/exact-name verification: `by_source[norm(src)] = (rec, fn)` is
a plain dict assignment, so if two distinct sources' names fold to the same key (e.g. two D&D
supplements distinguished only by a hyphen, or two adaptations differing only in capitalisation
already stripped by `.lower()`), the second processed **silently overwrites** the first in
`by_source`, and the roll entry for the first source then gets updated with the **second**
source's entry count — a silent misattribution of one source's catalogue size onto another's
roll row.

**REPRODUCED, with a live-data result:** wrote a standalone check against the actual
`data/SWEEP_ROLL.json` (roll names) and every `data/records/*.json` (`source` field) currently
on disk: **0 collisions in either set today** (217 record files, matching count of roll names).
So this is a live, unguarded hazard with zero current casualties — a latent bug, not an active
one, but structurally identical to the exact defect this project's own `cachekey.py` was written
this week to eliminate, one layer up and unpatched.

**Suggested fix:** either (a) verify the matched record's own `source` field equals `r["name"]`
exactly (or after only case/whitespace folding, not full punctuation-stripping) before trusting
the match — mirroring `cachekey.owns()` — or (b) keep a list per `norm()` bucket and refuse
(log + skip) any bucket with more than one distinct exact source name, rather than silently
picking last-write-wins.

### Clean areas in resync_roll.py
- `silence.write_json(ROLL, roll, ...)` at the one real write site — compliant with the
  two-writer/shared-state contract, and the module's own comment (line 66-68) correctly narrates
  that this was the fix for the exact clobber hazard its docstring describes.
- `--dry-run` path correctly never touches disk (`if not dry:` guards both the mutation and the
  save).
- The `changed` list and final "roll now: X/Y sources" summary are computed over the full,
  untruncated `roll` / `changed` lists — no caps.
- No secrets.

---

## Summary counts

| Severity | Count |
|---|---|
| HIGH | 2 (P-1, P-2) |
| MED | 5 (P-3, P-4, P-5, C-1, R-1) |
| LOW | 0 standalone (one LOW/MED merged into P-5) |

Known open item (entity-cache collision at pipeline.py:636 / coverage.py:44-46): **REFUTED** —
fixed via `cachekey.py` (M23), confirmed live in both files.
