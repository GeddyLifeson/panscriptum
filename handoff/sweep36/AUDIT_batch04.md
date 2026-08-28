# AUDIT batch 04 — run #36

Modules: `standards.py`, `catalogue_web.py`, `tiers.py`, `pantheon.py`, `tuning.py`,
`propagation.py`, `scope.py` (3,720 lines total, confirmed via `wc -l`). All seven read in full,
current on-disk source (not from memory of any earlier description).

---

## standards.py (1,871 lines)

### MAJOR — `state/job_progress.json` written with a fixed `.tmp` name from two long-lived processes

`check()`'s "every running job is advancing" block (around line 1302-1305):

```python
tmp = JOB_WATCH + ".tmp"
with open(tmp, "w", encoding="utf-8") as f:
    json.dump(cur, f)
silence.replace_retry(tmp, JOB_WATCH)
```

This is the exact hand-rolled `path + ".tmp"` pattern that `silence.write_json`'s own docstring
(silence.py:358-395) says was found at **twelve call sites** writing shared state with a bare
`open()+dump` and was fixed everywhere by qualifying the tmp name with PID+thread — "Two writers
of the same path otherwise collide on the temp file itself, and the loser can replace the
winner's target with a partial file." This site still uses the pre-fix pattern, and `check()` is
not a single-process function: `dashboard.py:583-584` calls `ST.check(s)` on every HTTP poll of
its own long-lived `serve_forever()`, and `publish.py:444-445` calls it inside a `while True`
loop in a *separate* long-lived process (confirmed via grep — both call sites exist and match
the docstring in `standards.py`'s own `fandom_ipv4_reachable` about "the two REAL production
callers"). If both processes' `check()` calls land inside this block close together, both open
`state/job_progress.json.tmp` for writing; one can truncate the other's in-flight write, and
`os.replace` can then land the truncated/interleaved content over the real file. This is
precisely the "cost this project real data twice" hazard the audit brief calls out, and it is
current, unfixed code, not a historical anecdote. The return of `replace_retry` is also discarded
here (a denied replace already retries next round per its own contract, so that half is
low-stakes on its own — the fixed-name race is the real issue). Fix: use `silence.write_json`
like every other state file in this module now does (`data/TIERS.json` in `tiers.py` was fixed
for exactly this the same way).

### MINOR — two `silence.note("standards.py:NNN")` line-number tags no longer match their own line

`silence.note("standards.py:370")` at (current) line 991, and `silence.note("standards.py:449")`
at (current) line 1073. Neither number matches the line it sits on any more — the file has grown
since these were written (compare every other `note()` call in this file, which now use
descriptive names like `"standards.py:cfg-num-ctx"` rather than numbers). This is exactly the
"line-number tags that no longer match their own line" pattern the audit brief names, and the
file's own text (line ~875) promises the opposite: "The class names the module and the line;
`python src/health.py --failures` lists them." A reader following that promise to `standards.py`
line 370 or 449 today lands on unrelated code. Low impact (these are just failure-ledger
dedup/label keys, not logic), but worth a cheap fix — rename to descriptive tags like the rest of
the file already does.

### Verified correct / no defect — `MIN_CALLS_TO_JUDGE_RATE` derivation

Per the batch guidance: `MIN_CALLS_TO_JUDGE_RATE = tuning.MIN_CALLS_TO_JUDGE` (line 67) is a
genuine derivation, not a re-typed literal — confirmed `tuning.py` line 86 defines
`MIN_CALLS_TO_JUDGE = 20` and nothing in `standards.py` (or the other six modules in this batch)
re-types `20`, `0.35` (`CLOUD_MIN_SUCCESS`), `3` (`CLOUD_MIN_BUCKETS`) or `3600`
(`PROOF_STALE_SECONDS`) as a bare literal. Grepped explicitly; clean.

### Everything else read, nothing found

The rest of the file (the fandom-IPv4 family probe, `ollama_token_flow`/`_flow_failure`,
`charter_regression_verdict`, `provider_pool_denominator`, the ~40 standards in `check()`
proper, `work_orders`, `report`) is unusually heavily self-documented with the exact defect and
fix history for each block, and cross-checks out: the `_dropped`/"every standard could read its
own input" mechanism genuinely covers every `except: silence.note(...)` branch that has an
`out.append` inside its `try`; the self-check regex for "every declared floor is measured" was
manually traced against `CHARTER_REGRESSION_MAX_AGE_H` and does match it (declared with a
compound prefix, used twice — once as declaration, once inside `charter_regression_verdict`).
No tautologies or unreachable branches found beyond the two items above.

---

## catalogue_web.py (478 lines)

### Verified honest — the new `no_text` count (per batch guidance)

Checked the specific caveat: `wiki_source.page_text()` (src/wiki_source.py:479-507) does indeed
return the same falsy `""` both when all three section fetches (0, 1, 2) raised an exception
*and* when the page genuinely has no prose in any of the three sections — confirmed by reading
the function directly (the `except: ... continue` path and the final `return ""` are the same
return value as a text-less page). `page_texts()` (wiki_source.py:510-537) drops every falsy
result silently (`if text: out[title] = text`). `catalogue_web.py`'s `no_text` counter (both in
`catalogue()` line ~284-308 and `catalogue_composite()` line ~106-130) counts every title in the
wanted list whose lookup in `texts` is missing/falsy — that is an accurate count of drops, and
the module does **not** claim it is "no evidence exists"; the provenance text it writes says so
explicitly and correctly: *"The API answers the same empty string for a failed fetch and for a
page with no prose, so this count is the UPPER bound on genuine absence and the upper bound on
lost fetches alike — it is not a claim that those entities have no evidence."* This is exactly
right and disclosed, not hidden. No defect — reported as requested, not found.

### MINOR — `save_roll()`'s write verdict is neither returned nor checked

```python
def save_roll(roll):
    import silence as _sil
    tmp = ROLL + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(roll, f, indent=2, ensure_ascii=False)
    _sil.replace_retry(tmp, ROLL)
```

`replace_retry`'s return (whether the rename actually landed) is discarded inside `save_roll`
itself — the function doesn't even return it, so its one call site (`_one()`, line 461) has no
way to check even if it wanted to. Contrast this with the very next lines of the same function
(447-458), which explicitly gate on `pipeline.write_record_catalogue`'s return value with a long
comment about exactly this failure mode ("This was the one call site throwing the verdict away
... so a persistent PermissionError left a stale record on disk beside a roll claiming N
entries"). `save_roll` is the one write in this file that never got the same treatment: if the
roll rename is denied (a reader holding it open — the same collision `replace_retry`'s own
docstring names as the normal case here), `tally["done"] += 1` and the success line still print,
while `data/SWEEP_ROLL.json` on disk keeps the old `entry_count: 0` for that source. Impact is
bounded (the record itself was already verified-written; the source would simply be re-picked-up
and re-fetched from the wiki on the next `catalogue_web.py` run, not lose data permanently) but
it is the same discarded-verdict shape as the bug the surrounding comment describes, on the
adjacent line. `tiers.py` (main(), line 355) and `pantheon.py` (main(), line 261) have the same
discarded-return pattern on `silence.write_json`, but those are one-shot CLI reports whose
established doctrine ("the caller's write lands next round") applies cleanly since nothing
branches on success; `save_roll` is different because its caller *does* branch on success
(`tally["done"]`/"the print line") without being able to see the real result.

### Read, nothing else found

`MAX_PER_SOURCE`/`MAX_PER_CATEGORY`/`CATEGORY_SCAN_DEPTH` are correctly neutralized (`None`) with
a `raise SystemExit` guard against `MAX_PER_SOURCE` ever being set again (line 274-277) — a real,
armed guard, not a dead one. The historical `TypeError` from comparing `len(titles) >
MAX_PER_CATEGORY` against `None` is fixed (ranking is now unconditional). Threading model in
`main()` (3-worker pool, `_wlock`-serialized writes) is consistent and the `_wlock` does cover
`save_roll()`'s call, so the fixed `.tmp` name is safe against *this process's own* threads; it
is only unsafe against a second concurrent `catalogue_web.py` process, and `foreman.py:782`
(`if ON.running("catalogue_web.py"): return True, "catalogue pass already running"`) confirms the
project's automated dispatcher already enforces single-instance before launching one, so this is
a latent risk (e.g. a person manually running it while the foreman also has one going) rather
than a live one today — noted, not raised as a standalone finding.

---

## tiers.py (361 lines)

### MINOR — `silence.write_json`'s return discarded in `main()`

Line 355: `silence.write_json(out, charted, indent=2, ensure_ascii=False)` — return value not
captured — followed unconditionally by `print(f"\nwrote {out}")` (line 356). A denied replace
would still print "wrote" for a file that, this round, did not change. Low severity: this is a
one-shot CLI report (`python src/tiers.py`), the write lands next invocation per the project's
stated `write_json` doctrine, and nothing downstream branches on the boolean the way
`catalogue_web.py`'s tally does. Contrast with `scope.py`'s `build()` in this same batch, which
was explicitly fixed for this exact shape (`ok = silence.write_json(...); return out, ok`, with
`main()` printing "WRITE DENIED" when `ok` is false) — worth the same treatment here for
consistency, but not urgent.

### Verified correct — Hard Rule 0 compliance

`deliberate_joins()` (line 272-288) returns the whole `shared.get((a, b), [])` list, no `[:N]`
slice — confirmed clean, matching the docstring's own account of the fix. The two `assert`
statements at module scope (lines 120-121, cuts must loosen downward / multiverse tighter than
metaverse) are genuine structural invariants over the `CUTS`/`MULTIVERSE_THRESHOLD` constants,
not tautologies — they would actually fire if someone misordered the constants.

`silence.note("tiers.py:248")` at line 248 — this one **does** match its own line number
(self-referential and current), unlike the two stale ones found in `standards.py` above.

### Read, nothing else found

`xenoverse_grounding`'s per-xenoverse (not per-source) grounding vote, the containment checks in
`main()`, and the hyperverse-declined-by-design argument in the module docstring were all traced
against the code and hold together; this is a case where the "might be deliberate design"
guidance applies directly — the whole point of the module is a *documented refusal* to chart the
hyperverse, which is a design decision, not an omission.

---

## pantheon.py (308 lines)

### MINOR (dormant) — magnitude-band label table in `main()` is missing three bands

```python
label = {"M8": "multiverses", "M7": "a universe", "M4": "a stellar system",
         "M3": "a planet", "M2": "a continent"}.get(b, "")
```

M1, M5 and M6 have no entry, so a merged `Z_FIGHTERS.json` (or future) entry landing on one of
those bands would print an empty label rather than crashing (`.get(b, "")` fails soft). Checked
`data/Z_FIGHTERS.json` directly: its bands are currently `{M2, M3, M4, M7}` only, so this does
not manifest today. Flagging because it is exactly the kind of dormant boundary case this
project's own `tuning.workers()` docstring warns about ("dormant rather than live... a contract
that inverts itself... is exactly what the next caller will trust") — cheap to complete the
table now.

### MINOR — `silence.write_json`'s return discarded

Line 261, same shape as `tiers.py` above: `silence.write_json(OUT, out, indent=1,
ensure_ascii=False)`, return not checked, followed unconditionally by `print("-> " + OUT)`. Same
low-severity assessment as `tiers.py` for the same reason (one-shot CLI report, nothing branches
on it).

### Question, not a defect — the presence-thesis judgment calls

The module's own docstring is explicit that "This is the single call in the set most worth
arguing with" (Whis/Vados/Zeno at M8 vs. a counter-reading that keeps them at M7) and argues its
own position by name. This is declared, argued design, exactly the "deliberate closed seam" the
brief says to treat as a question rather than a defect — noted, not raised.

### Read, nothing else found

`compute()`, `value()`, and the `--full`/`--gods-only` CLI branches trace correctly against the
`GODS` dict; the `combined.setdefault(k, v)` merge with `Z_FIGHTERS.json` deliberately lets the
hand-authored gods win any name collision, and `if n not in out: continue` in the `--full` branch
correctly restricts full-sheet printing to the gods this module actually computed (not the merged
Z Fighters), matching the module's stated scope.

---

## tuning.py (263 lines)

### Read, nothing found

This is the module the other six were checked against for re-typed threshold literals (see the
`standards.py` section above — clean). Read fully in addition to that grep:

- `regime()`/`profile()`/`workers()` all trace correctly, including the `workers()` "ZERO IS A
  REQUEST, NOT AN ABSENCE" fix, which is itself the audit-brief's #1 pattern (a check that used
  to accept the wrong branch) already caught and fixed by an earlier run, with a live regression
  pin cited (`verify_math S19ac`) — verified the fix is actually in the code (`min(requested, n)
  if requested is not None else n`, not the old falsy `if requested:` test).
- `_ollama_host()` reads `config.yaml` rather than hardcoding a host, with a documented fallback;
  correct.
- `cloud_success_rate()` and `_answering_buckets()` both return `(None, 0)` / `(0, "...")` shaped
  sentinels for "no evidence" rather than fabricating a rate, consistent with the project's
  house style for unmeasurable inputs.
- No fixed `.tmp` writes in this module (it never writes shared state, only reads).

---

## propagation.py (235 lines)

### Verified correct — the "unreachable" claim in `observed_mark`'s docstring

The docstring asserts: "once lag is non-negative, `ascension_years(1) == 0.0`... so the loop's
first iteration always matches and always returns; the trailing `return 0` after the loop is
unreached." Checked this by hand rather than taking the comment's word for it (per the audit
brief's "audits are wrong in both directions" instruction):

- `ascension_years(1) = round(1.0**1.35 - 1.0, 1) = 0.0` — confirmed.
- `ascension_years(rung)` is strictly increasing in `rung` for `RUNG_COST_EXPONENT = 1.35 > 1`
  and `rung >= 1` — confirmed by the shape of `x**1.35 - 1`.
- The loop runs `rung` from `LADDER_HEIGHT` down to `1`; given `lag >= 0` (guaranteed by the
  early `if lag < 0: return 0`), the `rung == 1` iteration's condition `lag >= 0.0` is always
  true, so the loop always returns from inside its body on or before that final iteration.

So the trailing `return 0` genuinely is dead code, and the docstring's claim about it is accurate
— a rare case where a self-diagnosed "this line cannot execute" note is actually correct on
inspection rather than being the kind of unverified claim the brief warns about. No defect;
noted as a positive verification per the brief's own emphasis on checking both directions.

### Read, nothing else found

`shortest()` is a standard Dijkstra over the co-attestation graph with an early-exit on reaching
`dst`; `load_graph()` correctly keeps the minimum distance when duplicate pairs appear
(`if b not in adj[a] or d < adj[a][b]`); `YEARS_PER_UNIT_DISTANCE`'s comment is unusually candid
about being a "declared convention... fictional and reversible" whose *justification* drifted
out of sync with the live graph (a stale hardcoded example, already caught and corrected by an
earlier run per its own text, "order 9736a5a73b02") while the constant itself was correctly left
unchanged. This module does not write any shared file (read-only against
`data/SHARED_STAGE_GRAPH.json`), so no concurrency exposure to check.

---

## scope.py (204 lines)

### MAJOR — 28 of 155 hosts in `data/SCOPE.json` hold stale invented ceilings that the fix cannot see or refresh, and at least one downstream consumer reads them as measured

Per the batch guidance, this is the specific defect to verify, and it is real and currently live
on disk. Confirmed directly:

```
root.fandom.com {'scope': 'universe', 'ceiling': 'M7', 'counts': {..., 'universe': 2, ...}, ...}
rosariovampire.fandom.com {'scope': 'universe', 'ceiling': 'M7', 'counts': {..., 'universe': 2, ...}, ...}
```

(`data/SCOPE.json`, 155 hosts total, checked by loading the file directly.) Both hold an `M7`
("universe") ceiling on exactly 2 mentions of "universe" — well under the module's own
`MIN_MENTIONS = 10` floor that `scope_for()` now enforces (lines 100-125). The module's own
comment (lines 104-120) names these two hosts and explains they were written by the *old*
argmax-over-counts fallback before the floor existed, and that the floor fix "does not purge"
existing rows. That comment is correct, and the consequence it does not spell out is confirmed by
reading the rest of the pipeline:

1. **`build()`'s `todo` selection never revisits an existing key.** Line 136:
   `todo = sorted({h for s, h in hosts.items() if h and h not in out and ...})` — membership as a
   *key* in `out` is sufficient to skip a host forever, regardless of whether its value was
   written under the old buggy logic or the current floored one. There is no version/timestamp
   field on a `SCOPE.json` row distinguishing "measured under the current floor" from "invented
   by the pre-fix fallback," so nothing can ever tell the 28 stale rows apart from the 127 good
   ones without manual deletion from the file.
2. **`ceiling_for()`** (line 171-178) reads whatever `cache.get(hosts.get(source))["ceiling"]`
   holds with no distinction — it cannot know a row is stale either.
3. **`magnitude.py` consumes exactly this ceiling as an authoritative clamp.**
   `magnitude.host_ceiling()` (magnitude.py:1219-1245) reads `data/SCOPE.json` directly off disk
   (`row.get("ceiling")` at line 1235-1236) and only falls back to a live `SCOPE.scope_for()`
   call when the disk row is *absent* — never when it is present but stale. That ceiling is then
   passed into `assay_entity(..., ceiling=cl)`, which clamps: "`if ceiling and
   A.LADDER.index(anchor) > A.LADDER.index(ceiling[1]): anchor = ceiling[1]`" (magnitude.py:936-
   937, repeated 968-969) — "a fiction cannot be out-scaled by its own inhabitant." So any entity
   catalogued under `root.fandom.com` or `rosariovampire.fandom.com` (and the other 26 stale
   hosts) is being clamped against an M7 "universe" ceiling that the module's own current logic
   says should never have been established from 2 incidental mentions — the exact fabrication
   `scope.py`'s floor fix exists to prevent, still in effect for these 28 hosts.

This is not a hypothetical cross-module concern; it is a confirmed, currently-live data
inconsistency with a concrete downstream reader. Remedy is straightforward given the module's own
existing machinery: either purge the 28 stale rows from `data/SCOPE.json` so `build()`'s
`h not in out` check naturally re-probes them under the current floor, or add a schema field
(e.g. a version/`min_mentions` stamp per row) so `build()` and `ceiling_for()` can tell a
pre-floor row from a post-floor one and refuse to trust the former.

### Read, nothing else found

`build()`'s write-verdict handling is a positive example in this batch — `ok =
silence.write_json(...)`, returned as `(out, ok)`, and `main()` prints a distinct "WRITE DENIED"
message when `ok` is false (lines 162-198) — the pattern `catalogue_web.save_roll()`,
`tiers.main()` and `pantheon.main()` above should each be brought in line with. The `except`
branch around `scope_for()` inside `build()` (lines 141-157) correctly avoids caching a
*transport* failure as a verdict (explicitly does not write `out[h] = None` on exception, only on
a genuine empty read) — traced this against the comment's claim and it holds: the `continue`
after the exception really does leave `h` out of `out` entirely, so next build's `todo` picks it
up again.

---

## Coverage note

All seven modules — `standards.py`, `catalogue_web.py`, `tiers.py`, `pantheon.py`, `tuning.py`,
`propagation.py`, `scope.py` — were read in full (every line), not sampled or read from
docstrings/names. No module in this batch could not be read.
