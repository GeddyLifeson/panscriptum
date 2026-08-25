# Batch 11 audit — sweep #28

Modules: `src/dashboard.py` (766), `src/weave.py` (487), `src/catalogue_web.py` (403),
`src/scout.py` (287), `src/wh40k.py` (244), `src/halo.py` (178), `src/module_index.py` (83).
Every line of every file was read start to finish. Total: 2,448 lines.

---

## SPECIAL FOCUS ANSWERS (asked first, as instructed)

### (a) `dashboard.py:296` vs `:301` — is `swallowed[:6]` still an unfixed cap, and are there other caps in the page-rendering path?

**Confirmed still open.** Current code (`_watch()`, lines 284-305):

```python
284 def _watch():
...
293        out["findings"] = [{"module": f.get("module"), "symbol": f.get("symbol"),
294                            "actual": (f.get("actual") or "")[:160],
295                            "severity": f.get("severity", "medium")}
296                           for f in openf]     # ALL open findings -- a monitoring cap ruled a truncation, 2026-08-24
297    except Exception:
298        silence.note("dashboard.py:watch")
299    try:
300        f = json.load(open(os.path.join(STATE, "failures.json"), encoding="utf-8"))
301        out["swallowed"] = sorted(f.items(), key=lambda kv: -kv[1])[:6]
302        out["swallowed_total"] = sum(f.values())
```

The comment on line 296 is genuinely true for the `findings` list — it is a full list
comprehension over `openf` with no slice, so every OPEN overwatch finding really does reach the
page. But five lines later, `swallowed` (line 301) is hard-capped to the top 6 failure tags by
count, with no comment claiming a fix. This is the exact adjacent-cap contrast the task
description; I verified it against the live state files:

```
state/failures.json: 20 distinct swallowed-failure tags, sum = 5226
top 6 shown on the page: silent:endpoint.py:fetch_raw-absent:HTTPError (3699),
  silent:endpoint.py:detect-api:HTTPError (450), silent:endpoint.py:detect-raw:HTTPError (450),
  silent:dashboard.py:movement:JSONDecodeError (82), silent:hostcheck.py:probe:HTTPError (72),
  silent:verify_math.py:47:ValueError (58)
HIDDEN: 14 more distinct tags, 415 occurrences, never shown on the instrument page.
```

The page is captioned "swallowed failures recorded: N" using `swallowed_total` (the true sum,
5226) right next to a table that only lists 6 of the 20 categories — so the total looks honest
while the breakdown silently omits 14 categories. **Severity HIGH, KNOWN (matches NEXT_STEPS.md
section 3 verbatim), still open.**

**Other caps found in the page-rendering path** (new, beyond the known `swallowed[:6]`):

- `dashboard.py:294` — `(f.get("actual") or "")[:160]` truncates the diagnostic detail text of
  *every* open-finding row shown on the page to 160 characters. The list itself is uncapped (per
  the line-296 comment), but each row's evidence string is truncated with no "…" marker and no
  way to see the rest from the dashboard. For a finding whose `actual` value is long (e.g. an
  assertion diff or multi-line traceback fragment), the operator sees a silently clipped
  string and cannot tell it was clipped. NEW, LOW-MED.
- `dashboard.py:732` — in `Handler.do_GET`, `f"{type(e).__name__}: {str(e)[:120]}"` truncates the
  exception message returned by `/api/state` on a hard failure of `state()` itself — the one
  error path that fires when everything else in the file has already failed. Low-stakes (a
  transient client-visible error string) but still an uncommented truncation on a diagnostic
  surface. NEW, LOW.

No cap was found on the `movement`, `standards`, `quotas`, `jobs`, `metrics`, or `library` panels'
own list bodies — those are all genuinely unbounded loops over their source data.

### (b) `dashboard.py:284-305 _watch()` — is the live `watch.open: 0, high: 0` measured or defaulted?

**Measured, right now.** `_watch()` sets `out = {"open": 0, "high": 0, ...}` *before* the `try:`
(line 286), so a read/parse failure of `data/OVERWATCH.json` is structurally indistinguishable
from a genuinely empty overwatch ledger — this part of the known finding is real and still
present in the code as written. But I read `data/OVERWATCH.json` directly to check whether it is
*currently* failing:

```
data/OVERWATCH.json: 57,328 bytes, parses cleanly as JSON.
rounds: 76
findings: 69 total, of which 0 have state == "open"
high-severity among the 0 open: 0
```

The file parses without error and genuinely records 0 open findings out of 69 total (all 69 are
presumably resolved/retired). So the `0, 0` currently shown on the live page is the **real,
correctly-measured value**, not a symptom of a swallowed exception. The hazard (a future
`OVERWATCH.json` corruption or transient read failure would silently present as "0 open findings,
everything is fine" instead of "watch status unknown") is still live and unfixed as a code
pattern — sibling `movement()` at line 335-358 was explicitly hardened against this exact class
of bug (see its own inline essay) and `_watch()` was not given the same treatment. **KNOWN
(matches NEXT_STEPS.md verbatim), still open as a code hazard; NOT currently manifesting.**

---

## src/dashboard.py (766 lines, read in full)

1. **HIGH, KNOWN, still open** — `dashboard.py:301` `out["swallowed"] = sorted(...)[:6]`. See
   special-focus (a) above for full evidence (5226 total, 20 tags, only 6 shown, 14/415 hidden
   with no indication on the page that anything was cut).
2. **HIGH, KNOWN, still open (as a hazard; not currently manifesting)** — `dashboard.py:286-305`
   `_watch()` sets `{"open": 0, "high": 0, ...}` before the `try:` block that reads
   `OVERWATCH.json`. See special-focus (b): verified live that the current 0/0 is a real measured
   value, but the code still cannot distinguish "genuinely zero" from "file unreadable" the way
   `movement()` (lines 335-358) was explicitly rewritten to do for `dashboard_history.json`.
3. **NEW, LOW-MED** — `dashboard.py:294` `"actual": (f.get("actual") or "")[:160]` truncates each
   open finding's evidence text on the run's opening diagnostic page with no truncation marker.
4. **NEW, LOW** — `dashboard.py:732` `str(e)[:120]` truncates the `/api/state` top-level error
   message.
5. **NEW, LOW (dead-code adjacent)** — `dashboard.py:286` the `_watch()` default dict includes a
   `"broken": []` key that is never populated anywhere in the function body and never read by the
   JS (`panelWatch` in the page script, lines 686-702, does not reference `w.broken` at all). Not
   a bug, just a vestigial field — flagged in case it is meant to carry something and silently
   isn't.
6. No other caps found. `_tail_match(path, rx, keep=400)` (lines 78-96) and
   `metrics(tail_bytes=250_000)` (line 401) are documented, justified tail-reads of ever-growing
   log/ledger files for a "what is happening right now" panel, not caps on findings/diagnostics —
   these read the same class of file `dashboard_history.json` handles correctly and are not part
   of this run's special focus, but are worth a second look if the metrics panel is ever asked to
   answer a completeness question rather than a recency one.
7. Verified: `movement()` (lines 314-398) correctly isolates the read of `HISTORY` from the
   write, per its own extensive comment — re-read the code, the isolation is real (separate
   try/except blocks at lines 350-358 vs 359-369), so this file's own documented fix for that
   exact bug class is genuine and still in place. Confirmed no regression.
8. Verified: `quotas()`, `throughput()`, `jobs()`, `library()`, `metrics()` all wrap their bodies
   in `try/except` with `silence.note(...)` calls that name the failing panel — no bare
   `except: pass` found anywhere in this file. `state()` (line 451) itself also isolates the
   `standards.check()` call into its own try/except so one bad panel cannot blank the whole
   `/api/state` response — this matches the file's own stated design goal (`jobs()`'s docstring,
   lines 171-193) and I found no case where it has NOT been applied.

## src/weave.py (487 lines, read in full)

1. **KNOWN, still open** — `weave.py:196-198`:
   ```python
   196    if (_MECHANIC.match(nm)
   197            or (_STATBLOCK is not None and _STATBLOCK.search(desc[:400]))
   198            or _RULES_VOICE.search(desc[:300])):
   ```
   Matches NEXT_STEPS's `weave_index.py:224 + weave.py:195-198` finding almost line-for-line. The
   mechanic-detection filter only searches the first 400 (or 300) characters of an entity's
   description, so a class-feature/statblock tell appearing later in a long description is
   invisible to this gate and the entity is NOT dropped as a mechanic — it survives into the
   entity index and can then wrongly contribute continuity evidence between two sources that only
   share a rules-text artifact. Confirmed still present verbatim.
2. **NEW, LOW (dead code)** — `pair_weights()` (lines 156-173) and `null_threshold()` (lines
   249-273) are the original idf-weighted (not surprisal-weighted) pair-evidence functions. I
   grepped the whole `src/` tree: nothing calls `pair_weights` or `null_threshold` anywhere,
   including `weave.py`'s own `main()` (which calls only `surprisal_pair_weights` and
   `null_threshold_surprisal`, lines 436-438). `idf_table` itself IS still used, by `pipeline.py`
   and `tiers.py`, but only to build the `occ`/`idf`/`sources` tuple that those callers then feed
   into `surprisal_pair_weights` (`pipeline.py:1776-1778`, `tiers.py:197-199`) — the raw idf-based
   pair-weighting path is dead in every caller I could find. Not a correctness bug (nothing
   produces wrong output because it is simply unreached), but worth flagging because it is the
   *un-hardened* twin of `surprisal_pair_weights` sitting right next to it with no `NO CAP`
   comment and no permutation-null caller wired to it — if anyone re-wires a caller onto it later
   expecting parity with its sibling, they will silently get the un-audited, non-mechanic-aware
   version.
3. Verified the two already-repaired caps (`surprisal_pair_weights`'s `shared[p]` list, lines
   217-225, and `OUT_GRAPH`'s `shared_sample`, line 478) are genuinely uncapped in the current
   code — no `[:8]` or similar remains. The self-critical comments describing the prior bug are
   accurate descriptions of a fix that is actually in place.
4. Verified the three `json.dump(obj, open(path, "w"))` leaked-handle/non-atomic writes the
   line-469 comment says were fixed are in fact now routed through `silence.write_json` (lines
   472-481) for all three outputs (`OUT_GROUPS`, `OUT_RESOLVED`, `OUT_GRAPH`) — confirmed
   genuine, no raw `open(..., "w")` + `json.dump` remains in this file.
5. No other correctness issues found in `idf_table`, `name_surprisal`, `filtered_index`,
   `components` (complete-linkage clustering with early-exit `min_cross`), or `resonance_graph`
   (BFS eccentricity/diameter) — traced each for off-by-one and edge cases (empty clusters, single
   source, isolate handling) and found none.

## src/catalogue_web.py (403 lines, read in full)

1. **NEW, MED** — `catalogue_web.py:199` vs `:244` — stale-closure-style variable reuse causes
   wrong progress-line labels during the page-fetch phase for every multi-category source.
   `_short` is assigned exactly once, inside the FIRST loop over `ws.CATEGORY_KEYWORDS`
   (line 199: `_short = canon.split(" (")[0][:16]`), and used for the "cats" and "ranking"
   heartbeat lines inside that same loop (lines 206, 214). The SECOND, independent loop that
   actually fetches page text (`for canon, cats, titles in planned:`, starting line 232) reuses
   the *same* `_short` variable at line 244:
   ```python
   243        texts = ws.page_texts(sub, wanted,
   244                              progress=lambda d, t: _beat(_short + " fetching", d, t))
   ```
   but never reassigns it from the current `canon` in that loop. Because `_short` is an ordinary
   function-local (not loop-scoped) variable, every "fetching" heartbeat line printed during the
   second loop shows the label from whichever category happened to be LAST in the first loop —
   not the category actually being fetched. Concrete failure scenario: a source with categories
   `Persons`, `Places`, `Factions` (in that iteration order) will label every "… fetching N/M"
   progress line for Persons, Places, AND Factions as `"Factions   fetching"` (or whatever the
   last-planned category's short name is), because `_short` was last set while processing
   Factions in the first loop. On a large wiki (the file's own commentary, lines 162-181,
   describes DC taking hours per source and depending on these heartbeat lines to prove the job
   is alive rather than stalled) an operator watching the log during the fetch phase is told the
   wrong thing is in progress for potentially most of the run. This does not affect the entries
   written (those use the correct `canon`/`cats`/`title` per iteration) — it is a diagnostic-only
   bug, but it directly undermines the stated purpose of this exact code path ("A WORKING JOB MUST
   LOOK LIKE A WORKING JOB", lines 162-181).
2. Verified `MAX_PER_SOURCE`, `MAX_PER_CATEGORY`, `CATEGORY_SCAN_DEPTH` are all `None` and the
   file raises `SystemExit` if `MAX_PER_SOURCE` is ever set non-`None` (lines 226-229) — genuine
   Hard-Rule-0 compliance, not just a comment. Grepped the rest of `src/` — nothing else reads
   these three names, so they're inert as claimed.
3. Verified `save_roll()` (lines 75-84) and `_land`-equivalent pattern used by `catalogue()`'s
   caller are compliant with the two-writer contract's stated exception for `silence.replace_retry`
   (fixed-name `.tmp` + `silence.replace_retry`, not a bare `os.replace`).
4. Verified `_one()` (lines 358-394) correctly gates `roll_by_name[...]["status"]="catalogued"`
   and the roll save on `write_record_catalogue`'s own success return value (lines 385-391) — the
   comment's claim that this was the one call site previously throwing away that verdict is
   consistent with what I see now: the gate is real, `return` fires before any state mutation if
   the write is denied.
5. `catalogue_composite()` (lines 87-148) and `catalogue()` (lines 151-282) both rank-not-truncate
   (`top=None` passed to `ws.rank_by_size` at lines 105 and 213) — confirmed no truncation of the
   entity list itself anywhere in this file.

## src/scout.py (287 lines, read in full)

1. **KNOWN, still open** — `scout.py:197-206`, unlocked read-modify-write of `F.HOSTS`
   (`WIKI_HOSTS.json`):
   ```python
   197        try:
   198            import feats as F
   199            hosts = json.load(open(F.HOSTS, encoding="utf-8"))
   200            hosts[source] = "pages:" + source
   201            _land(F.HOSTS, hosts)
   ```
   `_land()` makes the individual write atomic (tmp + `silence.replace_retry`), but the
   read-then-mutate-then-write as a whole is not — `scout.py`'s own docstring for `_land` (lines
   56-61) says this exact file is "written from here AND from two call sites in `hostcheck.py`".
   Two processes (or `sweep()`'s serial-but-long-running loop racing a concurrent `hostcheck.py`
   run) reading the same snapshot before either writes back will silently drop whichever host
   entry was added second-to-write. Matches NEXT_STEPS verbatim, confirmed still present.
2. **KNOWN, still open** — `scout.py:207-218`, `--dry` still writes `SCOUT_BLOCKED.json`:
   ```python
   207    blocked = [c for c in checked if c.get("code") in (401, 403, 429)]
   208    if blocked:
   209        try:
   ...
   216            _land(BLOCKED, prev)
   ```
   This block is gated only on `if blocked:` — it is never conditioned on the `register` argument
   (which is what `--dry` sets to `False` via `main()`, line 279: `register=not a.dry`). So a
   `--dry` invocation, whose whole point per `--help` is "verify but do not register", still
   performs a real read-modify-write to `data/SCOUT_BLOCKED.json` on disk whenever it finds any
   403/401/429 response. Confirmed still present, matches NEXT_STEPS.
3. **NEW, MED** — `scout.py:176` + `:193` — `verify()`'s safety check runs against a truncated
   name sample, not the source's full catalogued name list.
   ```python
   174 def scout(source, names, register=True):
   175     """Ask where the material lives, then prove each answer before believing it."""
   176     sample = [n for n in names if n and len(n) > 3][:PROBE_NAMES]   # PROBE_NAMES = 25
   ...
   192     for u in urls:
   193         r = verify(u, sample)
   ```
   `PROBE_NAMES = 25` (line 78) is sized for the LLM prompt (`scout()` only sends
   `sample[:18]` to the model at line 178) — that part is a legitimate prompt-context decision.
   But the SAME 25-name `sample` is then reused as the entire evidence pool for `verify()`'s
   safety property (`_names_in(text, names)`, called from `verify()` at line 169), which is a
   pure-Python substring check against already-fetched page text with no LLM/token cost at all —
   there is no technical reason to cap it. `verify()`'s own docstring (lines 136-149) and the
   module's central design claim ("CONTAINS THIS SOURCE'S OWN CATALOGUED ENTITY NAMES", line 27)
   promise the FULL catalogued name list is checked, not a 25-item subset. Concrete failure
   scenario: a source with 200 catalogued names, where a genuine hosting page for that material
   happens to only mention 2-3 names that are NOT among the (arbitrary-order) first 25 — `hits`
   comes back below `MIN_NAME_HITS = 2` (or right at the edge) and a real, correct page is
   discarded as "not about this material" (`ok: False`), which is exactly the kind of "smaller
   universe wearing the same shape as a complete one" Hard Rule 0 warns about — except here it
   silently rejects real material rather than truncating a result list. The adjacent comment
   block (lines 181-186) explicitly says the URL-count cap was removed for Hard Rule 0 in
   2026-08-24 but does not address this deeper cap on the verification evidence pool, which
   remains.
4. No other issues found in `hostless()`, `sweep()`, or `main()` — `sweep()`'s `SCOUT.json`
   history retention (`prev[-40:]`, line 262) is a bounded log-rotation of past sweep RUNS
   (comparable to `dashboard.py`'s `dashboard_history.json` 24h/2000-row retention, which
   NEXT_STEPS does not flag as a Hard-Rule-0 violation), not a cap on the current run's own
   findings — noted but not flagged as a primary issue.

## src/wh40k.py (244 lines, read in full)

1. No correctness bugs found. Static `ROSTER` data (5 entities × 11 axes each — verified all
   five entries carry the same 11 axis keys: ruin, continuity, celerity, reach, transgression,
   sustain, vector, volition, acumen, discernment, suasion) feeding `A.assay()`; `compute()` and
   `main()` are straightforward.
2. Verified the write (`silence.write_json(OUT, out, ...)`, line 237) is genuinely atomic — the
   file's own comment (lines 230-236) claims this was fixed "as the m100 tail" alongside
   `zfighters.py:478`; confirmed no raw `open(..., "w")` remains in this file.
3. `LOW, NEW (cosmetic)` — `wh40k.py:229` `d["cited"][:56]` truncates the citation text in the
   `--full` terminal print only. The underlying `WH40K_ASSAYS.json` written to disk (line 202,
   `out[name]["axes"][k]["cited"] = v[1]`) carries the FULL, untruncated citation text — this is
   purely a human-readable console print, not a data or diagnostic truncation, so it does not
   violate Hard Rule 0 in spirit. Noting only because it is the same code shape as the flagged
   `dashboard.py` truncations; here it is benign.

## src/halo.py (178 lines, read in full)

1. No correctness bugs found. Structurally identical to `wh40k.py` (3 entities × 11 axes,
   verified all three carry the same 11 keys); same atomic-write pattern already in place
   (`silence.write_json`, line 171, commented as "the m100 tail, 2026-08-25").
2. Same cosmetic `[:54]` print-only truncation of citation text in `--full` mode (line 169) as
   `wh40k.py` — benign for the same reason (full text is written to `HALO_ASSAYS.json`).

## src/module_index.py (83 lines, read in full)

1. **KNOWN, still open** — `module_index.py:75`:
   ```python
   75        with open(OUT, "w", encoding="utf-8") as f:
   76            f.write("\n".join(lines))
   ```
   Raw `open(path, "w")` + direct write, not routed through `silence.write_json` /
   `silence.replace_retry`. Matches NEXT_STEPS's `module_index.py:75` entry verbatim, confirmed
   still present, unfixed. `handoff/MODULE_INDEX.md` is a generated onboarding doc rather than a
   file another running process reads mid-pipeline, so the practical blast radius of a torn write
   here is smaller than the other flagged raw writes (`worldseed.py`, `manifest_builder.py`,
   `burgs.py`, `retry_synthesis.py` in the same NEXT_STEPS line) — but the two-writer contract
   draws no such exception, and the fix is trivial (swap for `silence.write_text`/manual
   tmp+`replace_retry`, matching every sibling module in this batch).
2. **NEW, LOW (stale docstring claim)** — `module_index.py:2`: `"the map of the 87 modules"`.
   The actual current module count is 95 (`ls src/*.py | wc -l` = 95, ~2026-08-25), and the code
   itself does NOT hardcode 87 anywhere — `main()` correctly computes `len(mods)` dynamically
   (line 77) and prints the true count every run, so the generated output is accurate. Only the
   English-prose docstring number has drifted out of sync with the codebase it describes, which
   is exactly the "hand-kept copy... with no merge strategy" problem this module's own docstring
   (lines 4-8) says it exists to avoid — ironic but functionally harmless.
3. No other issues: `first_line()` parses each module via `ast.parse` (not `import`), so it
   correctly avoids triggering any target module's own top-level side effects (e.g. the
   `_BAD_CHARS` `SystemExit` checks present in most of this batch's other files); failures are
   caught and logged via `silence.note`, never silently swallowed to a misleading default (the
   fallback string is `"(unparseable)"`, clearly distinguishable from a real docstring line).

---

## Summary table

| Severity | Status | Location | Claim |
|---|---|---|---|
| HIGH | KNOWN, open | dashboard.py:301 | `swallowed[:6]` hides 14/20 failure tags (415/5226 occurrences) with no on-page indication |
| HIGH | KNOWN, open (hazard, not live) | dashboard.py:284-305 | `_watch()` defaults before try; verified live 0/0 is currently a real measured value, not a swallowed-failure artifact |
| MED | NEW | catalogue_web.py:199,244 | stale `_short` var mislabels every "fetching" progress line with the wrong category during the page-fetch phase |
| MED | NEW | scout.py:176,193 | `verify()` checks catalogued names against a 25-name sample, not the full list, risking false-negative rejection of real hosting pages |
| KNOWN | open | scout.py:197-206 | unlocked cross-process RMW of WIKI_HOSTS.json |
| KNOWN | open | scout.py:207-218 | `--dry` still writes SCOUT_BLOCKED.json (write not gated on `register`) |
| KNOWN | open | weave.py:196-198 | `desc[:400]`/`desc[:300]` blinds mechanic-detection regex to late-appearing tells |
| KNOWN | open | module_index.py:75 | raw `open(...,"w")` write, no atomic tmp+replace |
| LOW-MED | NEW | dashboard.py:294 | per-finding `actual` text truncated to 160 chars, no marker |
| LOW | NEW | dashboard.py:732 | API error message truncated to 120 chars |
| LOW | NEW | weave.py:156-173,249-273 | `pair_weights`/`null_threshold` (idf-based) are dead code, unreached by any caller |
| LOW | NEW | module_index.py:2 | docstring says "87 modules", actual count is 95 (code itself is correct/dynamic) |
| LOW | NEW (cosmetic) | wh40k.py:229, halo.py:169 | `[:56]`/`[:54]` truncation is print-only; underlying JSON is untruncated |
