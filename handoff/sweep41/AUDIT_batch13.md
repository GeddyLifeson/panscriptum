# Sweep 41 — Batch 13 Audit

Modules audited, in full, line by line: `src/read.py` (1441), `src/overwatch.py` (979),
`src/wiki_source.py` (689), `src/codewatch.py` (578), `src/address.py` (461),
`src/retry_synthesis.py` (342), `src/catalogue_models.py` (301), `src/suppressions.py` (242).
5,033 lines total, all read this pass, no sampling.

## Context

All eight modules carry an unusually high density of prior fixes with detailed docstring
post-mortems (most dated 2026-08-2x through 2026-09-01, several from *today's* session per the
task brief). The bulk of the obvious Hard Rule 0 / silent-empty / fail-open shapes this project's
history warns about have already been found and fixed in these files, with the fix left in place
as a load-bearing comment. This audit's job was therefore mostly to check whether the fixes hold
together and to look for what a previous pass, focused on one incident, would not have been
looking for.

## Findings filed

### 1. `CODEWATCH_STAMP_CAN_STICK_AT_NONE` — MAJOR — order `e3c220e87d57`

`codewatch.stamp()` (src/codewatch.py:293-299) sets `_START["digest"] = fingerprint()` exactly
once, at daemon startup, with no retry and no re-stamp anywhere in the module.
`fingerprint()` (src/codewatch.py:80-104) returns `None` whenever any `.py` file directly under
`src/` cannot be opened right now — its own docstring names this as the ordinary signature of a
file mid-write (an editor's write-temp-then-rename, `local_agent.py` applying a patch).

If that race lands during *this process's own* `stamp()` call, `_START["digest"]` is `None`
forever. `stale()` (src/codewatch.py:454-456) then returns `(False, "not stamped; call stamp()
at startup")` on every future call for the rest of the process's life — no retry path exists —
and `exit_if_stale()` (src/codewatch.py:510-512) treats that exactly like the ordinary
nothing-changed case: `if not is_stale: return False`, no log line, no escalation. A daemon that
hit this race at startup is now permanently blind to source changes, indistinguishable from a
healthy freshly-stamped one, for as long as it runs.

Verified all six live call sites — `src/autostart.py:379`, `src/dashboard.py:1078`,
`src/foreman.py:1714`, `src/overwatch.py:960`, `src/pipeline.py:2616`, `src/publish.py:1502` —
discard `stamp()`'s return value and call it exactly once. Every standing daemon that relies on
the rc=17 interlock is exposed. The trigger scenario is not exotic: it is precisely what
codewatch.py exists to make routine — a daemon restarting to pick up a patch — landing at the
same moment a second patch write is still in flight, so the freshly-restarted process's own
startup stamp hits the file mid-write. Filed to RUN: the fix (retry `fingerprint()` in `stamp()`
with backoff, and/or escalate — at minimum JANITOR — if it still comes back `None`) needs care
against the drill nets that already cover this module's other races.

### 2. `READ_QUEUE_ROW_OWN_PAGE_NORMALIZATION_MISMATCH` — MINOR (filed as an OWNER question) —
order `fc08e056e1ab`

`read.py` has two different tests for "is this the entity's own page," and they disagree.
`read_entity()` — the function that actually mines feats — folds curly quotes/dashes/ellipses and
collapses whitespace before comparing: `own = _norm_q(title).lower() == _norm_q(name).lower()`
(src/read.py:791). `_queue_row()` — which builds the four numbers `priority()` sorts the entire
read queue by — instead does a raw `t.strip().lower() == name.strip().lower()` with no
normalization (src/read.py:1144).

For an entity whose own-page wiki title differs from its catalogued name only by curly-vs-straight
punctuation — the exact class `_norm_q` exists to fold, and the exact class of Unicode
normalization gap today's `_names()` fix addressed elsewhere in this same file — `read_entity()`
correctly reads it as the own page, but `_queue_row()` scores it `own=0`. `priority()`
(src/read.py:949-1035) uses that flag as its primary sort key, so the entity falls out of the
`have_page` deep/light interleave into the thinner `no_page`/`thin` buckets, read later than the
file's stated "deepest evidence first" design intent calls for. Nothing is dropped — the Hard
Rule 0 fix already in `priority()` means every entity is still read eventually — so this is a
ranking defect, not an evidence-loss one.

Measured live against `data/feats/`: sampling 3,000 cached evidence records, about 0.2% (6/3000)
carry a title with this punctuation class, so the affected population is real but small.

Filed as a question rather than a flat bug because there is a defensible reading of (b): `_queue_row`
runs over the full evidence index every pass and its own docstring is explicit about the cost of
opening each file, so a cheaper raw comparison could be a deliberate trade against `_norm_q`'s
extra work at that volume, and nothing downstream treats `_queue_row`'s own-page number as
authoritative for anything but ranking. Nothing in the code documents that this is a known,
accepted gap, though — which is what makes it worth asking rather than assuming either way.

## Checked closely, no finding filed

- **`read.py` transport ladder, chunk cache keying, `priority()`'s three buckets, `--chunks`
  inertness, `--one`'s uncapped feat printout.** All match their docstrings; the historical bugs
  named in the task brief (name-matching gate, `priority()` dropping 668 rows, the chunk-cache
  cross-entity key) read as genuinely fixed, not merely claimed fixed — traced the code, not just
  the comment.
- **`overwatch.py` ledger merge/CAS, `write_report`'s uncapped findings list, `verify_open`'s
  budget-vs-yield accounting, `rotation()`'s stale/changed split.** All consistent and exhaustive.
  `_STATE_RANK` carries two dict keys (`"stale"`, `"confirmed"`) that no code path ever assigns to
  `f["state"]` (actual states used are only `open`/`retired`/`closed`) — dead entries, not a fault;
  too weak to file.
- **`wiki_source.py`** — every Hard Rule 0 cap named in its own comments (`all_categories`'s
  `hard_stop`, `find_categories`'s `limit`, `category_members`'s `limit`) is genuinely uncapped by
  default now, and `clean_titles`'s O(n²)→O(n) fix is real. `resolve_wiki`'s known-host short
  circuits (fandom / non-fandom / override) are mutually exclusive and correctly ordered.
- **`codewatch.py`** — `fingerprint()`/`quiet_seconds()` scan only the top level of `src/`
  (`os.listdir`, not `os.walk`), which is the same shape `sweep_plan.py` was fixed for on a
  different axis (missing `deprecated/catalogue_local.py` from *coverage*) — but verified nothing
  in `src/` imports from `deprecated/`, so codewatch's non-recursion has no live daemon it could
  fail to watch. Not filed. `_ledger_lock`'s stale-lock steal, `_take_locked`'s fail-closed budget
  accounting, and `twins()`'s self-exclusion all check out against their documented incidents.
- **`address.py`** — `spine_code_for`'s three-tier match (exact normalize → worded containment
  with the new title-placement exception → token-overlap fallback) traced by hand against the
  documented adversarial cases (`Halo Around The Moon`, `Doom Marines`, `Sword Coast ... DC
  Edition`) and the logic correctly falls through to `UNASSIGNED` in each. No invented-address
  path found. `slugify`'s cap removal and `promote()`'s promotion-only asymmetry both hold.
- **`retry_synthesis.py`** — `save_side`'s re-read-and-merge narrows the multi-writer race to a
  single-entry window and reports its own landing verdict everywhere that matters; `do_merge`'s
  unmerged-name detection and non-zero exit on partial merge both check out. `synthesise()`'s
  `ev[:600]`/`rationale[:900]` caps are single-field summary caps mirroring `pipeline.py`'s own
  synthesis-block shape (explicitly cited in the docstring), not a roster/list truncation — judged
  out of Hard Rule 0's scope and out of this batch (`pipeline.py` wasn't assigned here).
- **`catalogue_models.py`** — `ask_provider`'s four-outcome taxonomy (`LISTED`/`EMPTY_LIST`/
  `UNREACHABLE`/`UNCONFIGURED`) is exhaustive and every branch is reachable. One soft question,
  **not filed** (too speculative to write up as a finding): `sweep()` buckets an `EMPTY_LIST`
  provider into `unverified` (`live.get(name)` is falsy for an empty `models` list) rather than
  treating its configured model ids as confidently stale, even though `EMPTY_LIST` is a verified,
  authoritative answer ("the API is alive and serves nothing") and not an unknown. Could be
  deliberate — a restricted `/models` listing endpoint doesn't necessarily mean inference is dead
  — and the `outcome` field is preserved and printed either way, so nothing is actually hidden.
  Left it out because I couldn't verify which reading the owner intends and it isn't load-bearing
  the way the two filed findings are.
- **`suppressions.py`** — confirmed it is genuinely wired into `publish.py`'s secret scanner
  (`src/publish.py:482`, aliased `_SUP`) and into `drill.py`'s net suite
  (`src/drill.py:3195-3208`, including a net titled "a suppressed finding is still REPORTED"), not
  an orphaned module — my first grep for the unaliased `suppressions.suppressed(` missed both call
  sites because they import under a local alias; re-verified with an import-only grep before
  concluding it was live. `problems()`'s EXPIRED/DANGLING checks, `add()`'s refuse-on-unreadable,
  and `suppressed()`'s case-sensitive `fnmatchcase` all match the module's stated doctrine — a
  suppression narrows a detector for a named case and never turns it off, and a suppressed finding
  is reported, never dropped.

## Coverage

Recorded via `sweep_plan.record('run41', [8 modules], batch=13)` — landed cleanly, all 8 modules
now show `run41` in `state/SWEEP_COVERAGE.json`.
