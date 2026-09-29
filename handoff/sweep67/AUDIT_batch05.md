# sweep67 batch05 audit (run67)

Read-only. Nothing under src/, data/, state/, output/, prompts/ or reference/ was touched. Scratch
scripts live under %TEMP% (`unwrap.py`, `apierr.py`, `dupjobs.py`, `dupkeys.py`).

## Scope (every line read, in chunks, no skimming)

| module | lines | chunks |
|---|---|---|
| src/feats.py | 2961 | 1-600, 600-1250, 1250-1900, 1900-2450, 2449-2961 |
| src/rigor.py | 1144 | 1-580, 580-1144 |
| src/derivation.py | 816 | 1-420, 420-816 |
| src/feats_index.py | 635 | 1-340, 340-635 |
| src/scope.py | 488 | whole |
| src/wh40k.py | 384 | whole |
| src/catalogue_aurora.py | 328 | whole |
| src/compress_store.py | 149 | whole |

Also run: pyflakes over all eight (clean); an AST scan for duplicate dict keys in all eight (none);
`derivation.check_graph()` (returns [], 112 quantities); `wh40k.compute()` (Nurgle 7.80, Khorne 7.76,
Tzeentch 7.86, Slaanesh 7.85, Emperor 6.76, matching the docstring). Interpreter is 3.13.9, so the
nested-double-quote f-strings at feats.py:2869-2872 (3.12+ only) parse.

## Prior-audit cross-check (handoff/sweep66/AUDIT_batch03,05,06,07,08,09,10)

- feats.py (b05): zero findings then. Every mechanism it re-traced still holds (registrable-domain
  pacer, `_api_list_all`, the four `mined_under_*` predicates, roll counters and exit code). NOT
  regressed; the findings below are new and are in code the earlier audit did not exercise (F1, F2,
  F3, F4).
- feats_index.py (b03): zero findings; `host_to_sources` raise-not-cache still there. Still stands.
  New: F6 (stale docstring).
- rigor.py (b06): its one question, `adjudication_beta` charging one law for zero (`max(1, ...)`),
  is now RESOLVED in code: lines 677-681 raise ValueError for `n_laws_touched < 1`, per order
  28f335ecefd3 item 6. wh40k.py's stale present-tense comment (sweep65 b03) is still fixed. New: F5.
- scope.py (b07): Question 1 (TIERS has no M0/M5/M9/M10 entry) still true; the source now carries a
  written rationale (lines 52-65), so it reads as decided-and-documented rather than open. Carried
  below as Cleared, not re-filed. `ProbeUnread` design re-verified.
- catalogue_aurora.py (b08), derivation.py (b09), compress_store.py (b10): zero findings then; code
  unchanged in shape (catalogue_aurora line count identical at 328, derivation identical at 816).
  New: F8, F9. derivation.py: still none.
- Line counts moved (feats 2817->2961, rigor 1132->1144, scope 473->488, wh40k 353->384,
  feats_index 633->635): the growth is the 2026-09-28 changes (ruled bindings, shelved/extra hosts,
  `_roll_jobs`, `_assert_not_halted`, the `n_laws_touched` validation). Those were read in full.

## Findings

### F1. MEDIUM, reproduced. `feats.api()` treats an HTTP-200 MediaWiki `error` object as a clean success
`src/feats.py:887-900` (also flows into `fetch` 1598-1617, `_api_list_all` 1310-1338,
`alive_verdict` 983-995, `scope.scope_for` 137-144).
MediaWiki reports many failures as HTTP 200 with a body `{"error": {"code": ..., "info": ...}}`
(`ratelimited`, `maxlag`, `readapidenied`, `internal_api_error_*`). `api()` only checks that
`json.loads` succeeded, then calls `note_ok(host)` (which DECAYS the backoff and zeroes the strike
counter) and stamps `{"ok": True, "why": "ok"}`. grep for `"error"` / `"warnings"` in feats.py,
scope.py and endpoint.py: no hits.
Repro (`%TEMP%/apierr.py`, urlopen stubbed to return a `ratelimited` body):
```
parsed: {'error': {'code': 'ratelimited', ...}}  outcome: {'ok': True, 'why': 'ok'}
fetch-shape pages: []
_api_list_all: []   cap_bound: {}
alive_verdict: (True, 'siteinfo answered')
```
Consequences, all of the file's own named failure shape (an error wearing an absence):
- `fetch()` stamps transport `ok`, returns {}; `evidence_for` writes a record with no pages and
  `transport.why == "ok"`, and `mined_under_failed_transport` (which forgives ok) never re-mines it.
  A rate-limit answered on a 200 becomes a permanent honest-looking absence.
- `_api_list_all` returns [] for the first-request error without touching `_CAP_BOUND`, so
  `discover()` reports "discovery lists: complete" over an entity whose search never ran.
- `alive_verdict` answers True (a wiki lives here) for a host that answered `readapidenied`.
- Because `note_ok` fires, an edge that is throttling us on 200s can never accumulate strikes and
  never reaches `THROTTLE_STRIKES` / quarantine.
Suggested fix: after the parse, `if isinstance(parsed, dict) and "error" in parsed:` treat
`ratelimited`/`maxlag` like 429 (note_throttled, retry, stamp "throttled"), and any other code as
`_stamp(False, "api-error:<code>")` returning None, WITHOUT calling `note_ok`.

### F2. LOW, reproduced. `_unwrap_templates` loses the last 2 (or 3) characters of an unclosed template
`src/feats.py:1631-1659` returns `j == n` for an opener with no close, and the callers slice
`c[i + 2:j - 2]` (line 1709) and `c[i + 3:j - 3]` (line 1704) as though a closer had been consumed.
The docstring says an unclosed opener "runs to the end of the text, as before", true, minus the
tail. Repro (`%TEMP%/unwrap.py`, functions pulled out of the file by AST):
```
'{{Infobox|power=Goku lifted 5 tons'  ->  ' Goku lifted 5 to '
'{{{1|default value'                  ->  ' default va '
```
"5 tons" becomes "5 to", so the `_QUANTITY` unit is lost on the last sentence of any page that ends
inside an unterminated template; the stored `text` and `provenance` then carry the corrupted
sentence. Suggested fix: have `_brace_end` return `(j, closed)` and slice off the closer width only
when `closed`.

### F3. LOW. An HTTP-date `Retry-After` raises out of `api()`
`src/feats.py:919`: `int(e.headers.get("Retry-After") or 0)` sits inside the `except HTTPError`
handler, so the ValueError from `Retry-After: Wed, 21 Oct 2026 07:28:00 GMT` (legal per RFC 9110)
is not caught by the sibling `except json.JSONDecodeError` / `except Exception` clauses of the same
`try`; it leaves `api()` whose contract is "parsed JSON, or None". `alive_verdict`, `_api_list_all`,
`scope_for` and `fetch` do not catch it. In `roll` it is absorbed as `errored`; in `--hosts` and
`scope --build` it would abort the walk. Fix: parse defensively (`try int() except ValueError: 0`).

### F4. LOW. `evidence_for` and `resolve_hosts` land through a fixed `path + ".tmp"`
`src/feats.py:2330` and `:1227`. Every other shared writer in this tree carries pid and thread in
the temp name (compress_store.py:52-53 explains why; scope.mutate does too). Measured with
`%TEMP%/dupjobs.py` over data/records x data/WIKI_HOSTS.json: 282,752 (host, entity) jobs, 281,166
unique, so 1,333 keys (1,586 extra jobs) are mined twice in one roll, e.g. `('en.wikipedia.org',
'The Guitar')`, `('forgottenrealms.fandom.com', 'Jim Darkmagic')` x3. The interleave in `roll`
usually separates them, but it is not guaranteed, and a `--probe` beside a running roll collides
the same way. Two writers on one `.tmp` interleave `json.dump` output and the loser's
`replace_retry` may land the other's partial file. Fix: use `silence.write_json` (already used by
`remine`) or a pid/thread-qualified temp.

### F5. LOW (latent). `rigor.bradley_terry` accepts diagonal and negative entries unvalidated
`src/rigor.py:481-486`. The AHP entry points validate their input (`_validate_reciprocal_matrix`);
this one does not. A self-contest `('a','a')` adds to `total_wins[a]` but never to `N` (the loop skips
`i == j`), so it inflates a's strength. Repro: `bradley_terry({('a','a'):3,('a','b'):2,('b','a'):1})`
returns strengths `[0.833, 0.167]`; the real 2:1 record gives `[0.667, 0.333]`. `chain.py:757`
drops case-insensitive self-pairs at input, so nothing live produces one today, but the re-keying at
chain.py:940-942 (`ID.node(x, epoch=...)`) is the kind of step that could fold two names to one node.
Fix: raise `RigorIntegrityError` on `a == b` keys and on non-finite or negative counts.

### F6. LOW (stale comment). feats_index.py credits feats.py with writing data/readfeats
`src/feats_index.py:6-8` says "`feats.py` mines attested deeds ... and lands them under
`data/readfeats/<host>/<Entity>.json`". feats.py writes `data/feats/` (`CACHE`, feats.py:56);
`data/readfeats` is `read.py`'s cache (read.py:62), and the `{feat, axis, page}` shape the module
joins is read.py's model-tagged output. A reader debugging a stranded record is sent to the wrong
producer. Fix: name read.py.

### F7. LOW (SUSPECTED, ranking-then-truncating). `scope_for` notes `continue` and does not follow it
`src/scope.py:137-150`. It asks for `srlimit=500` on four fixed queries, and if the response carries
`continue` (MediaWiki saying it withheld results) it only calls `silence.note("scope.py:srlimit-bound")`.
The queries are `world`, `universe`, `multiverse` and a cosmology string; on any large wiki they have
far more than 500 hits, so the ceiling is computed from the top-500-by-relevance slice per query.
`feats._api_list_all` exists to follow `continue` to the end and its docstring says "measuring a
truncation is not the same as not truncating"; scope.py's own comment says the same about the old
`srlimit=3`. Not confirmed against a live wiki (no network here); marked SUSPECTED for that reason.
Fix: use `F._api_list_all(host, {..., "list": "search", "srlimit": "500"}, "srlimit", ...)`.

### F8. LOW. `catalogue_aurora.parse_folder` drops an unparseable XML file with only a ledger note
`src/catalogue_aurora.py:153-162`. `continue  # a malformed homebrew file should not abort the whole
source` loses every element of that file, and `main()` then records the source `catalogued` with an
`entry_count > 0`, which the default selection (`entry_count == 0`, line 222) never revisits. Verbatim
duplicates are counted and printed (lines 224-228); an unparseable file is not, so the run prints a
clean total over a smaller universe. Fix: collect `unparsed` paths, print them, and count them into
`refused` so rc is 1 (or refuse to mark the roll row).

### F9. LOW. `compress_store.store` leaks its uniquely named temp when the write itself fails
`src/compress_store.py:54-56`. The temp sweep at 70-75 covers a denied replace only. A failure inside
`open(tmp, "wb")` / `f.write(blob)` (ENOSPC, AV lock) leaves a torn `<hash>.<pid>.<tid>.tmp` behind;
the name is deliberately unique, so repeats accumulate, which is exactly what the comment at 58-62
says it wants to prevent. Fix: wrap the write in try/except OSError that unlinks tmp and re-raises.

## Questions (possibly deliberate; owner decides)

1. `scope.py` (writes data/SCOPE.json) and `catalogue_aurora.py` (writes data/records/* and
   SWEEP_ROLL.json) carry no halt interlock. verify_math's `_INTERLOCKED` roster (line 7755) names
   the twenty hand-run writers that joined on 2026-09-28 and neither is among them, though the
   ruling text says every tool "that writes the corpus" refuses under a halt. Intended exclusion, or
   the ruling's list is not yet complete? (Same class as open orders 1e6f99e54b25 / 21c075e5e2d6.)
2. `feats._units` drops every unit of 400+ characters before either gate sees it (`long` tally,
   feats.py:498-503). The tally is now printed, and the docstring calls the ceiling "an upper bound on
   EVIDENCE"; whether that bound is acceptable under Hard Rule 0 is still open under order
   eacc5444288c. Restated, not re-filed.
3. `wh40k.py:91-94` calls Khorne's ruin (9.5) "the highest ruin in the setting", while Slaanesh's ruin
   is also 9.5 (line 150). Tie worded as a superlative; cosmetic, but it sits in the evidence string
   that is rendered in --full.
4. `feats._mentions` (feats.py:2167-2176): an entity whose name has no alphanumerics gives `low == ""`,
   and `"" in tl` is True, so every page is attributed to it. No such name exists in the catalogue
   today (not measured over all 282k entries); flagging as latent only.

## Cleared (examined closely, found correct)

- feats.py: `registrable_domain`, `_throttle` snapshot iteration, `note_throttled`/`note_ok` locking;
  `page_looks_real` three-layer gating and `parsed=True` skip; `_units` tally under `_COUNTS_LOCK`;
  the four `mined_under_*` staleness predicates and the `failed_dirty` 404 exemption; `resolve_hosts`
  ruled/override/cached-null/no-candidate branches; `_api_list_all` repeated-token stop and
  first-request-failure count; `discover` refusing `extra`; `resolve_title` ranking; `fetch` outcome
  accounting; `_QUANTITY` exponent groups and `_QUANTITY_UNIT_FIRST`; `by_axis` hoist;
  `_roll_jobs` shelved/extra handling; `roll` deferred tail and rc propagation; every legacy cache
  file carries `feats`, `quantities`, `chars_read` (grep -L over all of data/feats: none missing), so
  `work()`'s direct indexing cannot KeyError on disk data.
- rigor.py: `_validate_reciprocal_matrix` four refusals; `perron_weights`/`logrank_weights`/
  `theorem_1_check` None-aware verdicts; `SAATY_RI` matches the published table; Ford's two
  independent refusals; `adjudication_beta` new `>= 1` guard; `gumbel_return_level` reasons;
  `measure_bit_value("M5")` = 3.043 as the docstring says; `mathematical_resonance`. The
  `mdl_floor` note "ratio near 3" is loose but true (1.74 to 3.99, mean 3.12).
- derivation.py: `check_graph` kind/dangling/rootless/cycle rules, `depth` seen-guard,
  `_target_names`/`scan_constants_with_reason`, the early return on a cyclic ledger; ledger closes.
- feats_index.py: `host_to_sources` raising and not caching, `load_index` fault tallies, collision
  recording, `source_binding` tri-state, `audit` denominators.
- scope.py: `ProbeUnread` vs genuine empty, highest-tier-clearing-floor selection, `mutate` CAS with
  pid/thread/attempt temp names, TIERS gaps (documented at lines 52-65). SCOPE.json currently holds 155
  hosts all unstamped (probe_version None), i.e. the re-probe the docstring calls "still owed".
- wh40k.py: per-axis provenance (13 wiki, 42 canon by count), gated atomic write, halt check placed on
  the writing path only.
- catalogue_aurora.py: uncapped slug with legacy-cap `record_path`, description-in-key dedup with
  printed collapse count, write/roll gating and rc.
- compress_store.py: pid/thread temp name, swept temp before raising on a denied replace, verifying
  `load` against the filename address.
