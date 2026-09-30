# sweep68 batch05 audit (run68)

Read-only. Nothing under src/, data/, state/, output/, prompts/ or config.yaml was touched.
Scratch scripts are in `%TEMP%/aud68_05` (`r1.py` ... `r8.py`); every reproduction redirected
`silence.note` and its write paths to a temp directory.

## Scope (every line read with the Read tool, in chunks, no skimming)

| module | lines | chunks |
|---|---|---|
| src/feats.py | 2993 | 1-520, 520-1080, 1080-1640, 1640-2200, 2200-2600, 2598-2993 |
| src/sweep_plan.py | 1155 | 1-400, 400-800, 799-1155 |
| src/derivation.py | 816 | 1-420, 420-816 |
| src/feats_index.py | 636 | 1-330, 330-636 |
| src/scope.py | 493 | whole |
| src/snapshot.py | 387 | whole |
| src/style_audit.py | 342 | whole |
| src/cachekey.py | 217 | whole |

Also run: `derivation.check_graph()` (returns [], 112 quantities); a whole-cache scan of
`data/feats` (285,477 files) for the keys `work()` indexes directly (`feats`, `quantities`,
`pages_read`, `chars_read`, `entity`, `host`): none missing, none unreadable, none non-dict; a scan of
all 216 `data/records/*.json` for blank, non-string or no-alphanumeric entry names: none.

## Prior-audit cross-check (handoff/sweep67/AUDIT_batch05.md, plus other sweep67 batches that named these files)

All seven of last sweep's findings in this batch's modules were fixed in code and I re-verified each by
running it, not by reading the comment:

- F1 (feats `api()` HTTP-200 `error` body read as success): FIXED at feats.py:891-912. Stubbed urlopen:
  `readapidenied` -> `None`, `{'ok': False, 'why': 'api-error-readapidenied'}`, `alive_verdict` ->
  `(None, ...)`; `ratelimited` -> retried, then `why: 'throttled'`, `note_throttled` called instead of
  `note_ok`. Does not stand.
- F2 (`_unwrap_templates` loses the tail of an unclosed template): FIXED (`_brace_end` returns
  `(j, closed)`). `'{{Infobox|power=Goku lifted 5 tons'` -> `' Goku lifted 5 tons '`. Nested `{{{1|Unknown}}}}}`
  still correct. Does not stand.
- F3 (HTTP-date `Retry-After` raised out of `api()`): FIXED at 944-948 (`except (TypeError, ValueError)`).
- F4 (fixed `.tmp` for `evidence_for` / `resolve_hosts`): FIXED, both go through `silence.write_json`.
  (The 1,333 duplicate (host, entity) jobs per roll still exist, but the landing is now atomic.)
- F6 (feats_index docstring credited feats.py with `data/readfeats`): FIXED (lines 6-9 name read.py).
- F7 (scope_for did not follow `continue`): FIXED, `sroffset` is now walked. Two new concerns about that
  loop are filed below (L2, Q3).
- Question 1 (scope.py has no halt interlock): still true, restated as Q1.
- Question 2 (`_units` drops every unit of 400+ chars): still true, still under order eacc5444288c,
  restated as Q2.
- Question 4 (`_mentions` with a blank name attributes every page): code unchanged; I measured it this
  time, no catalogue entry has a blank or no-alphanumeric name (0 of 216 record files), so it stays latent.
- sweep67 findings against sweep_plan/snapshot/style_audit from other batches (sweep_plan `unknown_claims`
  UnboundLocalError, `--check-briefs` precedence, snapshot label sanitiser): all present as fixed in the
  code I read.
- cachekey.py, derivation.py, feats_index.py: no prior finding; no regression.

## Findings

### M1. MEDIUM, reproduced. A `pages:` record that is honestly empty is re-mined on every load, for ever
`src/feats.py:754-755` `hosts, measured = anomalous_empty_hosts()` / `return bool(measured and host in
hosts)`, together with `src/feats.py:2354` `"transport": dict(transport) or None`.

The legacy arm of `mined_under_failed_transport` re-mines an empty, unstamped record when its host is on
the anomalous list, on the stated premise that the re-mine will write a transport stamp and so stop
firing ("IT FIRES ONCE PER ENTITY" style argument, and the docstring's "cannot loop"). That holds for
wiki hosts, where `fetch()` fills `transport`. It does not hold for `pages:` or `doc:` hosts: neither arm
of `evidence_for` touches `transport`, so `dict({}) or None` stores `transport: None` on every record,
and the record can never acquire a stamp. `data/FEATS_EMPTY_RATES.json` currently lists four `pages:`
hosts as anomalous (`pages:all Creeper World` 100% of 364, `pages:The Elements Beyond` 96.5% of 680,
`pages:Guildmasters' Guide to Ravnica` 44%, `pages:KibblesTasty (techno-psionic line)` 40% of 1,290).
Scenario: any entity of those sources that no registered page mentions (the correct answer, per the
comment at 2237-2255) is stored with `pages_read=[]`, `pages_refused={}`, `transport: None`; next
`evidence_for(..., cache=True)` calls `mined_under_failed_transport` -> True, counts it in `_STALE_GATE`,
re-mines, rewrites the identical empty record, and does the same on the following call. Roughly 1,600
records are in this state (364 + 656 + 52 + 521 by the measured rates), each a rewrite plus a
`_source_pages_text` lookup per load, and every `roll()` prints them under "cache entries RE-MINED for
having been gated by the superseded wiki-markup check", which is the wrong diagnosis for them.
Repro (`r1.py`): a name-match record with empty pages and `transport: None` on `pages:all Creeper World`
-> `anomalous: True`, `mined_under_failed_transport(...) -> True`.
Fix: skip the legacy arm when `not reads_as_wiki(host)` (a non-wiki corpus has no transport to fail), or
stamp `transport` for the name-match arms so the record can say it was read.

### L1. LOW. `scope.build()` selects the seven `pages:`/`doc:` sentinel hosts for a live probe every build
`src/scope.py:256-258` `todo = sorted({h for s, h in hosts.items() if h and not F.is_wikipedia(h) and
...` filters Wikipedia only. Computed against the live files: 139 hosts are due, and seven of them are
`pages:all Creeper World`, `pages:The Elements Beyond`, `pages:Guildmasters' Guide to Ravnica`,
`pages:KibblesTasty (techno-psionic line)`, `pages:A Plethora of Paladins`, `pages:the Sex Worker
background` and `doc:arcanum-worlds-odyssey-of-the-dragonlords`. `scope_for` -> `F.api` ->
`endpoint.detect(host)` on a string that is not a host, which (endpoint.py:243-249) tries
`https://pages:all Creeper World/api.php`, fails inside `except Exception`, and stores a MODE_DEAD entry
under that key in the endpoint cache (`_save()` writes it; I did not run the write). Result: every build
prints seven `NOT READ` lines, never stamps them, and leaves junk sentinel keys in the endpoint cache. The
sentinel is not a wiki and cannot have a scope; it should be excluded the way `feats.reads_as_wiki` and
`feats_index.host_to_sources` already exclude it. Cache pollution half UNVERIFIED (read from the code).

### L2. LOW, UNVERIFIED. The new `sroffset` walk in `scope_for` has no repeated-token guard
`src/scope.py:139-155` `while True: ... params = dict(params, **cont)`. `feats._api_list_all` stops when a
wiki returns the same continuation token twice and counts it; this loop does not. A search backend that
re-answers the same `sroffset` (a stuck or capped CirrusSearch shard) never exits, and `build()` has no
timeout, so one host hangs the whole 139-host probe. Not reproducible offline; the guard is three lines.

### L3. LOW, reproduced. The coverage aggregate masks an unreadable shard, against `_read_shards`' own rule
`src/sweep_plan.py:734-747` (the aggregate fallback in `covered_by`), against `_read_shards`'s docstring
"a shard that will not parse is a batch whose coverage we cannot prove". Every `record()` folds the
current shards into `state/SWEEP_COVERAGE.json`, so the aggregate is not "coverage recorded before shards
existed", it is a copy of the shards, and `covered_by(run)` credits any `{module: {"run": run}}` row in
it. Repro (`r2.py`, temp SHARDS/COVERAGE): `record('rX', ['cachekey.py'], batch=1)`; overwrite the shard
with `{torn`; `covered_by('rX')` still contains `cachekey.py` (True), and only deleting the aggregate too
makes it False. So a corrupted or hand-edited shard cannot un-prove a batch, and `missing()` reports a
complete sweep over a batch nobody can now verify. Direction is fail-open (the aggregate should count only
for rows that predate `at`-stamped shards, or `covered_by` should report unreadable shards).

### L4. LOW, reproduced. `feats_index.load_index` raises on a record that is valid JSON but not an object
`src/feats_index.py:246` `entity = rec.get("entity") or fn[:-5]`. Only `open`/`json.load` are inside the
`try`; a file containing `[]` or `null` parses, then `.get` raises `AttributeError` and the whole index
build dies instead of counting the file under `faults["unreadable"]`. Repro (`r4.py`): one good record plus
`B.json` = `[]` -> `load_index RAISED: AttributeError 'list' object has no attribute 'get'`. Loud, not
silent (manifest_builder prints the exception), but every feats chapter is lost for the build over one
file the module already has a counter for. Fix: `isinstance(rec, dict)` inside the try.

### L5. LOW, reproduced. `snapshot.before` on a directory that contains `state/snapshots` copies the snapshot into itself
`src/snapshot.py:152` `shutil.copytree(src, tgt, dirs_exist_ok=True)`. `_rel` guards containment of the
source in the repo, not containment of the destination in the source. Repro (`r5.py`, HERE/ROOT
redirected to a temp repo): `before("x", ["state"])` and `before("x", ["."])` both die with
`RecursionError: maximum recursion depth exceeded`, wrapped as `SnapshotFailed` (fail closed, correct),
but `dest` is left behind holding a partial self-nesting tree, and on the live repo `"."` copies gigabytes
of `data/` before it tips over. No live caller passes such a path (`withdraw_chapters.py:296` passes
`output/index/catalog.json`), so latent. Fix: refuse a source whose realpath is an ancestor of, or equal
to, `ROOT`, and remove `dest` on the `except` path.

### L6. LOW, reproduced. `check_graph` cannot fail three of the rules the module docstring states
`src/derivation.py:506-507` `if q["kind"] == OWNER and not q["source"]:`. The docstring (lines 21-29)
requires a MEASURED value to carry "a real citation" and an OWNER declaration to be "signed, and must state
what it is anchored to". Only an OWNER row with a literally empty `source` is flagged. Repro (`r3.py`):
`Q(OWNER, "   ")`, `Q(MEASURED, "")` and `Q(CHARTER, "")` all produce zero problems; and eight OWNER rows
(`years_per_unit_distance`, `f_life`, `f_complex`, `f_civilization`, `f_survives`, `beta_constants`,
`pareto_tail_index`, `sevenfold_span`) have no parents, so "anchored to" is not enforced (several do state an
anchor in prose, which nothing checks). Same shape as the order-72bc85d74ccf `kind` typo the file already
fixed. Fix: `not str(q["source"]).strip()` for every kind, and decide whether an anchorless OWNER row is a
problem or a documented root.

### L7. LOW. `style_audit` exits 0 over an empty or unparseable corpus
`src/style_audit.py:328-331` (no files -> `return 0`) and `report()` (never returns nonzero; OVERUSED only
prints). `entries()` splits on `^◈`; if a chapter format drops that marker, or `output/raw` is empty, the
report prints "0 entries", "none" for machine tells, 0.0% turn endings and returns 0, which reads as a
clean prose-quality result. The self-test does have fixtures, so the detector is proven, but the live path
has no "zero entries read" refusal. Fix: return nonzero when `files` is empty or `entries == 0`.

### L8. LOW. `feats.py --roll` exits 0 when every cache write was denied
`src/feats.py:2954-2969`. The rc gate counts `_HOSTS_DENIED`, zero jobs, and all-errored. `_UNCACHED` (the
"evidence that did NOT reach disk" tally, printed at 2696-2704 with "if this number is large the roll
bought nothing") does not reach it, so a roll in which a reader held every evidence file open mines the
whole corpus, writes nothing, and exits 0 to the supervisor. Also cosmetic: `_roll_jobs` counts a hostless
source before the `only` filter (feats.py:2452-2458), so `--only X` prints every hostless source in the
catalogue under "excluded from this roll entirely".

## Questions (possibly deliberate; owner decides)

1. `scope.py` (writes data/SCOPE.json via `mutate`) carries no `escalation.assert_clear`, and
   `sweep_plan.record` / `snapshot.before` write state without one. Carried from sweep67 Q1; is the
   ruling's list of interlocked writers meant to include SCOPE.json?
2. `feats._units` still drops every unit of 400+ characters before either gate sees it (order
   eacc5444288c). Restated, not re-filed.
3. `scope.MIN_MENTIONS = 10` is an absolute count, calibrated when a probe read at most eight pages. The F7
   fix now walks every `srlimit` hit over 1,200 bytes for four queries, so the text volume can be two orders
   of magnitude larger, and `universal` (no word boundary, so also `universally`) and `alternate reality`
   will clear 10 on almost any large wiki. Today 43 hosts sit at M7 and 21 at M8 of 155 on the old cap.
   After the owed re-probe the ceilings may drift up until they clamp nothing. Should the floor scale with
   corpus size? (Also: the F7 change altered what a probe sees, and `PROBE_VERSION` is still 2. Moot today,
   since all 155 stored rows are unstamped, but the constant's own comment says to bump it.) UNVERIFIED, no
   network here.
4. `derivation.LEDGER`: seven MEASURED roots have no child (`planck_length`, `planck_time`, `earth_radius`,
   `sun_mass`, `sun_radius`, `tnt_yield`, `seconds_per_year`), and the DERIVED physics rows
   (`binding_energy` "3GM^2/5R", `schwarzschild`, `compton_energy`, `landauer`) name only the constants
   they use, not the mass, radius, length or temperature the formulas take. If those are call-time inputs
   that is right; `math_resonance` reads "orphan rate" off this graph, so is the rate meant to include
   them?
5. `feats.py` `main --roll`: only `errored >= n` fails the run. A roll where 90% of entities raised exits 0.
   Deliberate threshold, or should a rate trip it?

## Cleared (examined closely, found correct)

- feats.py: `registrable_domain`, `_throttle`/`note_throttled`/`note_ok` locking and the snapshot iteration;
  `quarantine_view` unreadable-not-empty handling; `page_looks_real` layering and `parsed=True`; the four
  `mined_under_*` predicates for wiki hosts (transport stamp does terminate the re-mine there),
  `CLEAN_NEGATIVES` and `failed_dirty`; `api()` outcome stamping on every exit path; `_api_list_all`
  first-request-failure count and repeated-token stop; `resolve_hosts` ruled/override/null/no-candidate
  branches and gated write; `discover` refusing `extra`; `resolve_title` ranking; `fetch` outcome counting
  (a 404 then a throttle in one pass still counts as dirty); `_QUANTITY` exponent groups and
  `_QUANTITY_UNIT_FIRST`; `_roll_jobs` shelved/extra fail-closed; deferred tail; `empty_rates` keyed on the
  record's own host; the disk-record key scan above (`work()` cannot KeyError).
- sweep_plan.py: `_src_py_files` recursion, `batches` packing and unreadable carry-through, `freeze_plan`
  create-if-absent CAS and refusal of every non-"absent" reason, `normalise_module` exactness, `record`
  shard naming and gated landing, `unknown_claims` two-pass import fix, `missing_detail` roster split,
  `check_briefs` frozen-plan comparison, `--check-briefs` precedence.
- derivation.py: cycle/dangling/rootless/kind rules, `depth`, `_target_names`, `scan_constants_with_reason`,
  the early return on a cyclic ledger.
- feats_index.py: `host_to_sources` raising and not caching, `source_binding` tri-state, `binding_report`
  bucket accounting, `audit` denominators (files_seen), collision recording.
- scope.py: `ProbeUnread` vs a real empty, highest-tier-clearing-floor selection, `mutate` CAS with
  pid/thread/attempt temp names, unreadable-not-overwritten, `--host` and `--build` rc.
- snapshot.py: `_rel` containment, `_safe_join` on restore, unique sid with `exist_ok=False`, partial-capture
  refusal, `_dir_matches` byte compare, manifest landed through gated `write_json`.
- style_audit.py: `TURN_ENDING` anchored on `\Z`, `opener_shape` NAME collapsing, the `_cut` remainder line,
  self-test asserting by name and count with a negative control.
- cachekey.py: sanitiser byte-identity, `owns` with host, `load` treating a foreign file as a miss,
  `write_path` disambiguation, `text_digest`/`provenance_ok` three-valued result.
