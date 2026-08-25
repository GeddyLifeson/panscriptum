# AUDIT — batch 10 (run30)

Files: `src/hostcheck.py`, `src/handbuilt.py`, `src/catalogue_web.py`, `src/sweep_plan.py`,
`src/grounding.py`, `src/thread_integrity.py`, `src/withdraw_chapters.py`

Method: every line of every file read top to bottom. Reproductions used isolated scratch
scripts in the session scratchpad — no repo file was ever written to, and `hostcheck.py
--purge`/`--repair`, `withdraw_chapters.py`, and any generate/prose command were never
executed, per instructions. Where a reproduction imports the real function it is noted;
otherwise findings are static-reading conclusions and labeled HYPOTHESIS.

**Committed secrets: none found** in these 7 files (checked for API keys, tokens, passwords,
bearer headers, cloud credential patterns — only false-positive substring hits on prose like
"Paul Bearer" and "Secret Wars").

---

## src/hostcheck.py

### 1. [CRITICAL] `--repair` has no dry-run / `--go` gate at all — REPRODUCED (source reading)
`sweep(only=None, repair=False, workers=8)` (line 487) has **no `dry` parameter**, unlike
`purge(dry=True, ...)` (line 613) and `adopt(dry=True, workers=4)` (line 844), both of which
correctly gate their real write behind `dry=not a.go`. Inside `sweep()`, when `repair=True` and
`wrong` is non-empty, the block at lines 525-595 runs the full replacement search and, if
`fixed` is non-empty, calls `_land(F.HOSTS, hosts)` and `_land(UNFIT, unfit)` **unconditionally
— there is no `if a.go` or `if not dry` check anywhere on this path.** `main()`'s
`ap.add_argument("--repair", ...)` (line 914) never wires in `a.go` either. A bare
`python hostcheck.py --repair` immediately rewrites `WIKI_HOSTS.json` and `HOST_UNFIT.json`
for real — the first run, no preview. This is inconsistent with `--purge` and `--adopt`, both
of which require `--go` to write, and explains why this project's own instructions treat
`--repair` as something nobody may run casually.
**Fix:** give `sweep()` a `dry=True` parameter, gate the two `_land()` calls behind
`not dry`, and require `--go` in `main()` before passing `dry=False`.

### 2. [HIGH] `sweep(repair=True)`'s replacement search ranks by raw rate, not lift — REPRODUCED (isolated simulation)
Lines 534-546 (`best = (0.0, None)` ... `if ok and p["rate"] is not None and p["rate"] > best[0]: best = (p["rate"], h)` ... `if best[0] >= GOOD: break`). This is exactly the bug `adopt()` (lines 869-889) documents fixing in its own docstring: *"an earlier version stored the RATE there... so a worse-lift host could win."* `adopt()` ranks by `r["lift"]`; `sweep()`'s repair path still ranks by `p["rate"]`.
Reproduction (`repro_repair_logic.py`, mock `score()` results, no network/repo touched):
two synthetic candidates — a generous, weak-lift host (rate 90%, lift 10%, verdict `partial`)
and the true host (rate 45%, lift 40%, verdict `holds`) — the rate-based loop picks the
generous host; the lift-based loop (transcribing `adopt()`'s logic) correctly picks the true
host. Output confirmed the mismatch.
**Why it matters:** `score()`'s own docstring describes this exact failure mode happening for
real (`Rocket League` nearly adopted onto Wikipedia). The verdict gate (`ok = verdict in
("holds","partial")`) filters the worst cases, but among several "ok" candidates the ranking
can still promote a `partial` generous host over a `holds` true host.
**Fix:** make the repair-loop `best` track `(lift, host)` like `adopt()` does, and break on
`GOOD_LIFT` not `GOOD`.

### 3. [HIGH] `judged_any` is poisoned by the one candidate that's always reachable — REPRODUCED (isolated simulation)
Lines 535, 550-553. `judged_any` is set True the moment **any single** candidate in the full
list returns a non-`UNREACHABLE` verdict. `candidates()` (line 319) unconditionally does
`add("www.dandwiki.com")` **first**, for every source — a host that is almost always reachable
and, for any non-D&D source, will almost always score `WRONG FICTION`. So in a throttled repair
pass where the genuine replacement host (and everything else) times out, `judged_any` still
becomes True from dandwiki alone, and the `elif not judged_any:` safety branch ("no candidate
answered; keeping {host} for now", lines 550-553) — the one branch designed to protect a source
from losing its host to a network blip — is effectively dead in the realistic case. The source
instead falls to the final `else:` (line 559-563) and is **unassigned** (`fixed[src] = None`),
written to `ROSTER... /HOST_UNFIT.json`, on what may be nothing but a bad afternoon for the
network.
Reproduction confirmed: with dandwiki reachable+wrong and 3 other candidates (including a
stand-in for "the actual right host") all `UNREACHABLE`, `judged_any` evaluates `True`.
**Fix:** `judged_any` should require the loop to have judged a *meaningful fraction* of
candidates (or specifically the ones ranked above the current host), not merely "at least one."

### 4. [HIGH] `null_rate()` caches the baseline on `host` alone, ignoring `exclude` — REPRODUCED (live call against the real function, network mocked)
Lines 391-424. `_NULL_CACHE` is keyed by `host` only; `exclude` only affects what's fed into
the *first* call's foreign-name pool. Reproduction (`repro_null_rate_cache.py`) imported the
real `hostcheck.null_rate` with `probe()` monkeypatched (no network, no repo write): scoring
`SourceX` (exclude="SourceX") on a shared host first computed and cached a baseline that
**included SourceY's own real names** in the "foreign" pool (since only X was excluded).
Scoring `SourceY` (exclude="SourceY") immediately afterward on the same host returned the
identical cached value — `probe()` was called exactly once total, never re-run with `SourceY`
properly excluded. Confirmed: Y's baseline was inflated by its own genuine hits.
**Why it matters:** this drags `lift = rate - baseline` down for whichever source loses the
cache race, which can flip a genuine `holds` into `WRONG FICTION`/`NAMES ONLY` — the exact
false-negative class this file exists to prevent, now reintroduced by the baseline cache.
**Fix:** key `_NULL_CACHE` on `(host, exclude)`.

### 5. [HIGH — Hard Rule 0] `relevance()` (the ABOUT veto) truncates the title list to 12
Line 188/200: `def relevance(host, titles, source, sample=12):` ... `titles = [t for t in
titles if t][:sample]`. `probe()` (line 122-162) does NOT truncate its `titles` field (only
`examples` is capped at 5) — so `relevance()` receives every hit, then throws away all but the
first 12 before computing what fraction of hits are "about" the source. `_bodies()` (line 227,
called from `relevance()` at line 220) truncates a further time for raw-mode hosts:
`EP.fetch_raw(host, list(titles)[:8])` (line 247) reads only 8 of the (already-12-capped)
titles. This is a judgment-affecting statistic (`r["about"]`, used to set the `NAMES ONLY`
verdict at line 478) computed from a sampled subset of a hit-title list, not a display-only
truncation — this is exactly the shape Hard Rule 0 names ("`sample=12`... ranking is fine,
ranking then truncating is not"), except here there isn't even a size-based ranking first —
it's a straight positional slice of whatever order the MediaWiki API happened to return.
**Fix:** read all hits (or rank by size first, per the rest of the file's own convention,
before reading — but never drop the tail silently from a judgment input).

### 6. [HIGH] `--purge`'s `--help` text still asserts a safety gate `purge()`'s own docstring says never existed
Lines 916-917: `ap.add_argument("--purge", ..., help="remove rosters the audit rejected AND
whose host was independently rejected")`. `purge()`'s own docstring (lines 643-648) explicitly
disclaims exactly this: *"An earlier docstring claimed the code also required the host to have
been independently rejected; it never did (the check was loaded and unused), and pretending a
safeguard exists is worse than naming the real one: nothing is purged except sources a person
explicitly listed with --source."* The function body confirms this — there is no such check
anywhere in `purge()` now. The false claim was removed from the function's docstring but is
**still live in the CLI's own `--help` output**, for a command that deletes catalogued entries.
Someone reading only `--help` (not the function source) would believe a safety net exists that
does not.
**Fix:** update the `--purge` argparse help string to match the function's real, honest
contract (human-selected `--source` only).

### 7. [MEDIUM] `_land()` swallows write failures — no reproduction needed, contract violated in-file
Lines 67-80: `_land()` calls `silence.replace_retry(tmp, path)` and **discards its return
value**. `replace_retry` (src/silence.py:263) returns `False` on persistent denial (after
retries) rather than raising — by design, so the caller can react. `_land()` reacts to nothing:
every one of its 6 call sites (`sweep()` twice, `purge()` twice, `roster_audit()`, `adopt()`)
prints an unconditional success line ("`-> {OUT}`", "`WIKI_HOSTS.json updated...`") even when
the underlying file never actually landed. Contrast with `handbuilt.py`'s sibling writer in the
very same tree (see finding 10 below), which checks this exact return value and fails loudly.
Also contrast with `pipeline.write_record_catalogue`, cited by name inside this very file's own
`purge()` docstring as the pattern to follow ("returns whether the rename LANDED... a denied
write is not recorded as done"). `WIKI_HOSTS.json` is explicitly the highest-stakes file this
module touches (its own comment at lines 583-590 describes an empty host map reading downstream
as "no source has a wiki," and cites a real 2026-08-24 incident).
**Fix:** have `_land()` return the boolean and have every call site check it, exactly as
`handbuilt.py` does.

### 8. [REFUTED / already fixed] "probe swallows HTTPError" — checked against live evidence
`probe()` (lines 122-162) does not conflate a caught exception with a zero rate: on exception
it returns `{"rate": None, "error": ...}` and calls `silence.note("hostcheck.py:probe")`,
matching its own docstring's stated fix for exactly this failure mode. Corroboration: grepped
`state/failures.json` (1 hit) and `state/failures_archive.json` (31 hits) for
`hostcheck.py:probe` — confirms the situation happens often in live runs, but the recorded
`rate: None` there is handled as `"UNREACHABLE — no judgement"` in `score()` (line 470-472),
not as a zero. As currently written this item is **REFUTED as a live bug** — the module already
does the right thing here. (The "92 live occurrences" figure in the open-items list may
predate this fix, or may refer to a different accounting; worth a one-line confirmation with
the owner rather than further code changes.)

### Clean / notable in hostcheck.py
`candidates()`'s `add()` dedup is correct (no duplicate hosts ever added); the two-list
grounded/speculative split (avoiding a truncate-then-mix) is correctly implemented and matches
its docstring; `entities_by_source()` and `roster_audit()` scan every record with no cap.

---

## src/handbuilt.py

### 9. [REFUTED] The Zalama "eleven axes vs five" comment (lines 165-168) checked line-by-line against the ROSTER dict
Zalama's `axes=dict(...)` (lines 181-204) has exactly 11 keys, matching every other entity, but
6 carry the string `"unestimable"` (ruin, continuity, celerity, vector, volition, discernment)
and 5 carry real numeric scores (reach, transgression, sustain, acumen, suasion). Every other
entity in `ROSTER` (The Undertaker, The Internal Revenue Service, Molecule Man, Rune King Thor,
The Sentry, The Black Winter, Getter Emperor, Mister Mxyzptlk) has all 11 axes numeric —
verified by reading each dict. The comment's claim ("Every other entity in this file scores
eleven axes; this one scores five") is **accurate as written**. Not a bug. (The further claim
in the same comment — "its published interval is four times wider as a direct result" —
depends on `assay.py`'s handling of `"unestimable"` scores, which is out of this batch's scope
and was not independently verified.)

### 10. [CLEAN] Write-before-print ordering and failure gating are done correctly
Lines 452-460: writes `HANDBUILT_ASSAYS.json` via tmp + `silence.replace_retry`, **checks the
return value**, calls `silence.note` and prints "WRITE DID NOT LAND" with a nonzero exit if the
write failed, all *before* any Unicode-risky console printing happens. This is the pattern
`hostcheck._land()` (finding 7) should be using and currently is not.

No caps, no dead code, no secrets found in this file.

---

## src/catalogue_web.py

### 11. [HIGH] `save_roll()` still uses the pre-fix fixed-name temp file — REPRODUCED (cross-file evidence)
Lines 75-84: `tmp = ROLL + ".tmp"`. `silence.write_json`'s own docstring (src/silence.py:290-318)
documents that this exact pattern was found, project-wide, to collide across concurrent
writers of the same shared file ("the loser can replace the winner's target with a partial
file") and was fixed by giving the temp name a **PID + thread-id** suffix. Grepped every other
script that writes `data/SWEEP_ROLL.json`: `catalogue_aurora.py` and `catalogue_codex.py` both
carry the comment `# ATOMIC: four scripts write this same roll (see silence.write_json).
2026-08-25.` and call `silence.write_json(ROLL, ...)`; `recover_folder_records.py` and
`resync_roll.py` do the same. `src/verify_math.py`'s own completeness list of repaired writers
(`_REPAIRED_20g`, around line 3639) enumerates exactly those four scripts for `ROLL` — **not**
`catalogue_web.py**. `verify_math.py`'s surrounding comment even quotes `catalogue_web.py`'s
own "kills the next run of either script outright" line as one of the places that *already
knew* about the hazard in prose — implying the sweep believed `catalogue_web.save_roll()` was
already safe (it does call `silence.replace_retry`) and left it out of the migration to
collision-safe naming. It is not: two concurrent writers of `ROLL + ".tmp"` — e.g. two
`catalogue_web.py` invocations, or interference from anything else that still uses the bare
pattern — can still interleave on that one shared temp path.
Note: within a single `catalogue_web.py` process, the 3 worker threads' calls to `save_roll()`
**are** correctly serialized via `_wlock` (verified — it's called from inside the same
`with _wlock:` block that gates `write_record_catalogue`). So the "unlocked write" half of the
originally-flagged item is not accurate; the fixed-temp-name cross-process race is the real
and confirmed part of it.
**Fix:** replace `save_roll()`'s body with `silence.write_json(ROLL, roll, indent=2,
ensure_ascii=False)`, exactly like its four siblings, and add it to `verify_math.py`'s
`_REPAIRED_20g` list (flagged for whichever batch owns `verify_math.py`).

### 12. [MEDIUM] `save_roll()` also discards `replace_retry`'s return value
Line 84: `_sil.replace_retry(tmp, ROLL)` — return value unused. `_one()` (line 358-394) goes on
to unconditionally print `"-> {name}: {N} entries in {T}s"` and increment `tally["done"]` even
if the roll write was persistently denied, leaving `SWEEP_ROLL.json` stale while the console
and `tally` both claim success. Same class of bug as hostcheck.py finding 7; by contrast, the
record write two lines above it (`_P.write_record_catalogue(...)`) IS correctly gated at line
385-388 in this very function, which makes the un-gated roll write beside it stand out as the
one lapse in the same code path.

### 13. [MEDIUM] `_short` stale-closure bug in `catalogue()` — REPRODUCED (isolated simulation)
`_short` is set at line 199 inside the first loop (`for canon in ws.CATEGORY_KEYWORDS:`) and
used for progress labels there. The second loop (`for canon, cats, titles in planned:`, lines
232-262) reads `_short` again at line 244 (`_beat(_short + " fetching", ...)`) but **never
reassigns it** — so every "fetching" progress heartbeat for every category in the second loop
prints whichever category's label was last set in the first loop. Reproduction
(`repro_short_closure.py`, pure Python, mirrors the two loops exactly) confirmed: 3 distinct
categories in the second loop all emit the identical (wrong) `"Factions fetching"` label.
**Why it matters, given the surrounding comment's own stated purpose:** the elaborate `_beat`/
`PROGRESS_EVERY_S` machinery exists specifically so a slow-but-healthy job "looks like a
working job" to a human or a stall-detector reading its output (the comment cites DC being
repeatedly killed by `foreman.kill_stalled_job` because it went silent for too long). The
heartbeat's *timing* is unaffected by this bug (so the anti-stall property still holds), but
its *content* is wrong throughout the entire fetch phase of every multi-category source — which
directly undermines the observability the comment says this code exists to provide. Purely
cosmetic (no effect on the actual catalogued data), so scored MEDIUM rather than HIGH.
**Fix:** capture `_short` per-iteration in the second loop too, e.g. reintroduce
`_short = canon.split(" (")[0][:16]` at the top of `for canon, cats, titles in planned:`.

### Clean / notable in catalogue_web.py
`MAX_PER_SOURCE`/`MAX_PER_CATEGORY`/`CATEGORY_SCAN_DEPTH` are correctly neutralized to `None`
with a loud `SystemExit` guard if `MAX_PER_SOURCE` is ever re-set (lines 226-229); every
category-listing call in both `catalogue()` and `catalogue_composite()` consistently uses
`top=None` / `limit=None` ("rank, never truncate") — Hard Rule 0 compliance here is solid and
deliberate. `write_record_catalogue`'s return value IS correctly checked (line 385).

---

## src/sweep_plan.py — the sweep's own instrument, audited hardest per instructions

This file has clearly already been through several fix cycles (dated 2026-08-25 in its own
docstrings describing prior bugs found by earlier sweep runs). Checked every invariant named
in the task brief directly against the current implementation:

### 14. [CLEAN — verified] `modules()` excludes nothing
Lines 36-63: iterates every `*.py` under `src/`, no filter, no early-return exclusion list —
literally the opposite is asserted and true ("Not even this file, and not `verify_math.py`").
An unreadable file is appended with `{"unreadable": True, "lines": 0}` rather than silently
dropped or miscounted as an empty stub (this was itself a fix for a prior bug, per the comment
at lines 49-59) — confirmed present and correct in the current code.

### 15. [CLEAN — verified] `batches()` cannot drop or duplicate a module
Lines 66-79: single `for m in modules():` loop, exactly one `.append()` per module into
whichever bin currently has the fewest lines. No module is skipped, no module can be appended
twice — verified by direct reading of the loop body; there is no other code path.

### 16. [CLEAN — verified] `missing(run)` answers "did run N cover module X", not "who touched X last"
`missing()` (line 245-249) calls `covered_by(run)` (line 199-242), which unions modules from
**every shard whose `run` field equals the requested run**, plus a fallback fold from the
pre-shard-era aggregate file filtered the same way (`str(r.get("run")) == want`). It does
**not** go through `coverage_map()` (line 179-196), which is explicitly the newest-wins,
last-touched view and is documented as "the wrong instrument for `missing()`." Confirmed the
separation is real in the code, not just asserted in the docstring — `missing()`'s only call
into shard data is `covered_by()`, never `coverage_map()`.

### 17. [LOW] `record()`'s per-shard write bypasses `silence.replace_retry`
Line 151: `os.replace(tmp, p)` — a bare call, not `silence.replace_retry`. Given the audit
lens's stated contract ("shared state ONLY via silence.replace_retry / silence.write_json"),
this is a literal deviation. Practically low-risk: `p` is named uniquely per
`(run, batch, pid)` (line 85-92), so no other writer should ever already have that exact path
open when this rename happens — the Windows PermissionError-on-open-reader race
`replace_retry` exists to retry around requires a *pre-existing* reader of that destination
path, which nothing can be, since the filename didn't exist before this call. Recommend
aligning to `silence.replace_retry` anyway for consistency and because "should never happen"
is exactly the class of assumption this project's own history (WinError 5, 2026-08-23) has
burned it on before.

### 18. [LOW, documented, not a new bug] Aggregate `SWEEP_COVERAGE.json` fold is still theoretically racy across processes
The `with _RECORD_LOCK:` block (lines 158-176) uses a `threading.Lock`, which — per the
function's own docstring — cannot serialize the 16-separate-processes topology this sweep
actually runs under. This is the **same** race the docstring describes fixing for the
authoritative data path, but here it's left in place for the *aggregate convenience file only*,
and that is explicitly, correctly called out ("nothing draws a conclusion from it that the
shards do not support"). Verified this claim holds: `coverage_map()`, `covered_by()`, and
`missing()` all read shards directly and only use the aggregate file to fill gaps for
pre-shard-era records. No actual defect — flagging only so a future change that starts trusting
`SWEEP_COVERAGE.json` as authoritative doesn't silently reintroduce the exact bug this file's
own history already paid to fix once.

---

## src/grounding.py

### 19. [LOW — Hard Rule 0] `classify_text(text, top=3)` caps the ranked-groundings list, and the drop reaches a persisted file
Line 112-117: `scores.most_common(top)` with default `top=3`, against only 5 possible
`GROUNDINGS` keys. `classify_source()` (line 120-186) uses `ranked[0]` for the primary verdict
(unaffected by the cap) but also returns `"runners_up": ranked[1:]` (line 185) — i.e. up to 2
of the remaining 4 types, silently dropping up to 2 more. This **is** written to disk:
`main()`'s `--write` path (lines 235-240) persists the full `out` dict, runners_up included, to
`data/GROUNDINGS.json`. So this is not purely a console-display truncation — it's a capped
ordered list feeding a persisted artifact, which is the letter of what Hard Rule 0 forbids,
though materiality is low given the fixed universe of 5 grounding types and that the primary
`grounding`/`verdict`/`confidence` fields are never affected.
**Fix:** default `top=None` (return the full ranked list; 5 entries is cheap) or explicitly
pass `top=len(GROUNDINGS)`.

### Clean / notable in grounding.py
`classify_source`'s `cap` parameter is correctly neutralized with a loud `SystemExit` guard
(lines 143-147), matching the pattern the docstring says it shares with `feats.discover` and
`genre.classify_source`. Entry scanning (`for e in rec.get("entries", [])`) reads every entry,
no limit. `main()`'s "SAMPLE" section (hardcoded list of showcase sources) and `low[:5]` are
genuinely console-only diagnostics that don't affect the written `GROUNDINGS.json` — correctly
exempted, unlike finding 19.

---

## src/thread_integrity.py

### 20. [MEDIUM] Partial entity drift is not filtered out of the reported "shared" counts
`classify()` (lines 82-135): the `ents` check (lines 108-113) only marks a pair `DANGLING` when
**every** shared key has drifted out of both sides' live records (`len(gone) == len(shared)`).
That's a reasonable, documented design choice (a pair with even one still-valid shared entity
is real evidence of *something*). But for a pair that's only **partially** drifted, the
`shared` set used for `detail[...].append((a, b, len(shared)))` (lines 116, 121, 134) and for
`out[...]` counts is the **original, pre-drift** set from `implied_threads()` — the stale/gone
keys are never subtracted before being counted. So a pair reported as "40 shared entities" may
include entity keys that no longer exist in one of the two sources' current records, inflating
both the raw counts in `THREAD INTEGRITY`'s printed breakdown and the ranking used for
"strongest reciprocal bonds" (`detail["RECIPROCAL"]` sorted by `-x[2]`, printed `[:8]`) and
"one-way with no excuse" (`detail["ASYMMETRIC-SUSPECT"]`, printed `[:6]`).
**Fix:** when `ents is not None`, filter `shared` down to `{k for k in shared if k in
ents.get(a, ()) and k in ents.get(b, ())}` before using its length anywhere, for every
classification branch, not just the DANGLING gate.

### Clean / notable in thread_integrity.py
`RECIPROCAL`/`ASYMMETRIC-LAWFUL`/`ASYMMETRIC-SUSPECT` are currently unreachable in production
(`main()` never passes `recorded`) but this is explicitly and correctly documented as
forward-looking, tied to Hard Rule 5 (the directed thread graph doesn't exist until the owner's
Step 4 pass) — not dead code in the pejorative sense, just not-yet-activated and honestly
labeled as such in both the docstring and the printed banner ("no directed thread graph exists
yet"). `implied_threads()`'s deliberately-symmetric pair construction matches its own docstring
about the m12 bug fix. `load_entities()` reads every record file with no cap.

---

## src/withdraw_chapters.py

Never executed (per instructions). Read in full; findings below are static.

### 21. [MEDIUM] The pre-withdrawal snapshot covers only the catalog index, not the chapter content being moved
Lines 52-59: `SNAP.before("withdraw-chapters", ["output/index/catalog.json"], ...)` snapshots
**one file** — the small JSON index — then verifies and raises `SnapshotFailed` if it doesn't
restore. The surrounding comment reads as a general safety claim about the withdrawal ("A COPY
BEFORE THE IRREVERSIBLE STEP... the instinct was the ONLY thing standing behind 145 chapters...
an untested backup is a belief, not a backup") but the actual snapshot never touches the 145
chapters' `raw_path`/`compressed_path` content files that are about to be `shutil.move`d. If a
move fails partway, or (see finding 22) two entries collide on the same destination basename,
there is no verified backup of the *content* to recover from — only of the tiny index that
pointed at it. The "moves, does not unlink" design (module docstring, lines 8-11) is itself the
real safety net for ordinary moves; the *verified snapshot* specifically only backs up the
index.
**Fix:** either narrow the comment to say plainly that only the catalog index is
snapshot-verified, or extend the snapshot to include `output/raw/` and the compressed store
(or at minimum, sample-verify a few moved files post-hoc).

### 22. [LOW, unconfirmed against live data] Possible destination-basename collision on `shutil.move`
Lines 66-78: for each catalog entry, both `raw_path` and `compressed_path` are moved to
`os.path.join(arch, sub, os.path.basename(src))`. If two different catalog entries'
`safe_filename(address, ext)` (in `generate.py`, `re.sub(r"[^A-Za-z0-9]+", "_", address)`)
normalize to the same string — plausible in principle since the regex collapses all
non-alphanumerics to a single underscore, though addresses are drawn from `address.py`'s
structured spine-code scheme and a real collision was not observed in the live
`output/index/catalog.json` present on disk (197KB, not exhaustively diffed for this specific
collision here) — the second `shutil.move` would silently overwrite the first inside `arch/`,
permanently losing one withdrawn chapter's content with no snapshot behind it (see finding 21).
Flagged as HYPOTHESIS / worth a one-time basename-uniqueness check against the real
`catalog.json`, not confirmed as an active bug.

### 23. [LOW] Dry-run counters are labeled as if the move happened
Lines 78, 90: `moved[sub] += 1` and `extra += 1` increment unconditionally, whether or not
`a.go` was passed — so a dry run prints the same `"raw moved: N"` / `"compressed moved: N"`
figures it would print after a real `--go` run. The trailing `"DRY RUN -- pass --go to move"`
banner (line 108) clarifies overall intent, but the field names themselves ("moved") are
inaccurate during a dry run — they mean "would move."

### 24. [LOW] Final catalog-clearing write also discards `replace_retry`'s return value
Line 98: `silence.replace_retry(tmp, CATALOG)` — return value unused, same pattern as findings
7/12. Lower priority here since it's the very last step of an already-`--go`-gated,
snapshot-preceded operation, but for consistency it should be checked and reported like
`handbuilt.py` does.

---

## Severity tally

- CRITICAL: 1 (hostcheck #1 — `--repair` has no `--go`/dry-run gate)
- HIGH: 5 (hostcheck #2 rate-vs-lift, #3 judged_any, #4 null_rate cache, #5 ABOUT-veto 12-title
  cap [Hard Rule 0], #6 false `--purge` help text; catalogue_web #11 fixed-temp-name race)
  — *(6 HIGH items across 2 modules; see full list above)*
- MEDIUM: 8 (hostcheck #7 `_land` swallows failure; catalogue_web #12 `save_roll` swallows
  failure, #13 `_short` stale closure; thread_integrity #20 partial-drift count inflation;
  withdraw_chapters #21 snapshot scope)
- LOW: 6 (sweep_plan #17, #18; grounding #19; withdraw_chapters #22, #23, #24)
- REFUTED / already-fixed: 2 (hostcheck #8 probe-HTTPError; handbuilt #9 "eleven vs five axes"
  comment)
- CLEAN sections explicitly verified: sweep_plan `modules()`/`batches()`/`missing()` (the
  instrument itself), handbuilt.py's write gating, catalogue_web's Hard Rule 0 discipline,
  grounding.py's `cap` guard, thread_integrity.py's documented-dead asymmetry branches.

No committed secrets found in this batch.
