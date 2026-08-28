# Batch 12 audit — run #36

Modules: `mutate.py`, `wiki_source.py`, `manifest_builder.py`, `scout.py`, `genre.py`,
`tempus.py`, `cleanup.py`, `physics.py` (3,710 lines total, all read in full).

Special brief for this batch: audit today's M46 fix in `mutate.py` (owner-pid reaping)
adversarially, and give `cleanup.py` the same "anything that deletes" scrutiny.

---

## mutate.py (1,084 lines)

### The M46 fix itself (`_owner_pid`, `_claim_sandbox`, `reap_orphans`) — adversarial read

**1. Can a sandbox become permanently undeletable?** No mechanism makes a sandbox
*permanently* undeletable, but the ownership check is weaker than it looks, for two
independent reasons:

- **PID recycling is the actual attack surface, and the fix does nothing to close it.**
  `_claim_sandbox` (line ~529) writes `{"pid": os.getpid(), "started": time.time(), "argv": ...}`
  to `_owner.json`. `_owner_pid` (line ~507-519) reads back **only** the `pid` field:
  ```
  pid = json.load(fh).get("pid")
  ...
  return pid if isinstance(pid, int) else None
  ```
  `started` is captured and then never read by anything — not by `_owner_pid`, not by
  `_pid_alive`, not by `_pid_alive_windows`. `reap_orphans` (line ~595-598) then does:
  ```
  owner = _owner_pid(p)
  if owner is not None and _pid_alive(owner):
      silence.note("mutate.py:reap-skipped-live-owner")
      continue
  ```
  If the process that built a sandbox is hard-killed (exactly the M46/incident scenario the
  whole module exists to survive) and the OS later reuses that same PID for *any other,
  unrelated, long-lived process* — a daemon, a scheduled job, anything the machine happens to
  run — `_pid_alive(owner)` reports ALIVE and the orphaned sandbox is protected for as long as
  that unrelated process runs, with no way to tell the two apart. `started` was clearly written
  for exactly this cross-check (compare it against the live process's own start time) and is
  simply never consulted. This is a "safety recorded to disk but not in effect" bug, not a
  design question — the data needed to close the hole already exists in the file.
  CLAUDE.md's own list of 2026-08-25 incidents notes "fifteen long-lived jobs were running that
  day" on this machine, so PID reuse landing on a live long-runner is not a far-fetched scenario
  here specifically.

- **Narrow creation-window race.** In `sandbox()` (line ~696-701), `reap_orphans()` runs
  *before* `tempfile.mkdtemp()`, and `_claim_sandbox(root)` runs immediately after `mkdtemp`
  — so under `reap_orphans`'s **default** 6-hour `older_than`, the age gate (`mtime > cutoff`)
  protects this window by a wide margin regardless of ownership. But the module's own comments
  (line ~571-577) confirm the drill net legitimately calls `reap_orphans()` with a very small/
  zero `older_than` to make reaping observable in a test. Under that mode, a second process's
  `mkdtemp()` → (not yet claimed) window is no longer protected by age, and a reap sweeping
  through at that exact moment would see `owner=None` (file doesn't exist yet) and delete the
  half-built sandbox out from under its own creator — a smaller-radius recurrence of the exact
  M46 failure shape. This is not exercised anywhere (see finding 3 below), so it is unconfirmed
  in practice, but it is real by construction: ownership is not atomic with directory creation.

**2. Can a recycled pid protect a dead run's sandbox forever?** Effectively yes, for practical
purposes, per finding 1 above — "forever" in the sense of "for as long as some process holds
that recycled pid, and then potentially again the next time it's reused," which on a machine
running many long-lived daemons is not bounded by anything in this code.

**3. Is there any other code path that deletes `panscriptum_mutate_*` directories without going
through `reap_orphans`?** No — checked, not found. `grep -rn "panscriptum_mutate\|SANDBOX_PREFIX"
src/` turns up exactly three deletion sites: `reap_orphans`'s own `shutil.rmtree` (ownership-
gated), and two direct-by-path self-cleanups of `root` in `_run_mutation`'s `finally` (line 925)
and `_session`'s `finally` (line 1080) — both operate only on the calling process's *own*,
already-known sandbox path, which is inherently safe (a process doesn't need an ownership check
to delete the directory it just built). No script outside `src/` (no `.ps1`/`.bat`/`.cmd` in the
repo) touches `%TEMP%`. `cleanup.py` (this batch) does not reference sandboxes or `%TEMP%` at
all — confirmed by direct read, not by inference.

**4. The most valuable gap: the M46 fix's live-owner branch is never exercised by any test.**
`drill.py`'s `abandoned_sandboxes_are_reaped` net (drill.py:4214-4262, read for context since it
is the only other code in the tree that calls `reap_orphans`) builds two probe directories —
`aged` and `fresh` — with **no `_owner.json` in either one** (it only writes `marker.txt`). So
`_owner_pid()` returns `None` for both, and `reap_orphans`'s decision for both probes is made
entirely by the **age** branch, exactly as it was before the M46 fix. The net proves "an old,
unowned sandbox is reaped" and "a fresh, unowned sandbox is not" — it does **not** prove the
fix's actual claim, "an OLD sandbox with a LIVE owner is not reaped." That is precisely the
behaviour M46 was about, and precisely the behaviour the drill net's own docstring credits
this fix with adding. Per CLAUDE.md's own "PROVEN" pillar ("a guard nobody has watched refuse
is a guard nobody has evidence about"), the ownership half of this fix is currently unproven.
Reported as a finding about `mutate.py`'s fix even though the missing assertion lives in
`drill.py`, since `drill.py` wasn't otherwise in scope for this batch.

**Severity:** MAJOR (finding 1: `started` captured-but-unused defeats the cross-check the fix
clearly intended) / MINOR (finding 1b, the recycled-pid exposure itself, since it requires an
adversarial coincidence) / MINOR (finding 1, creation-window race, unconfirmed in practice) /
MAJOR (finding 4: the fix's core behaviour is untested).

### A confirmed, reproducible bug in the mutation generator itself: same-line duplicate operators collapse to one untested mutant

`_mutations()` (line 312-369) generates one candidate edit per AST node, but the edit itself is
computed by **string-level `line.replace(old_token, new_token, 1)`** — the `, 1` means "replace
only the first occurrence in the line." When a single line carries more than one instance of the
same comparison operator, boolean connective, `not`, or `True`/`False` literal, every AST node
past the first produces the *identical* `new_src` (because `.replace(..., 1)` always targets the
same first occurrence regardless of which node triggered the check), and the existing dedup
(`key = (m[0], m[1])`, i.e. `(lineno, description)`) collapses them into one entry. The
docstring's justification ("several AST nodes can sit on one line and produce the same edit")
frames this as harmless redundancy, but it is not: the second, third, etc. occurrence of the
operator on that line is **never independently mutated at all** — not merged-and-tested, simply
absent — so a line like `if (a < b) and (c < d):` only ever gets `a < b` flipped; `c < d`'s `<`
is structurally invisible to this tool forever, with nothing in the `mutants: N, killed: N`
report to say so.

Reproduced directly against the live `_mutations()`:
```
def f(a, b, c, d):
    if (a < b) and (c < d):
        return True
    return False
```
produces exactly one `< -> >=` mutation (targeting `a < b`) and one `and -> or` mutation, but
**no** mutation for `c < d`'s `<`. `TARGETS` (`assay.py`, `prose_gate.py`, `escalation.py`) are
described in this module's own docstring as "the checks are densest" — dense arithmetic and
guard-heavy code is exactly where chained/compound comparisons on one line are most likely, so
this is a real, silent coverage hole in the tool whose entire purpose is finding coverage holes.
It is column-fixable (track `node.col_offset` and replace at that offset instead of the first
textual match) without disturbing the "surgical single-token edit" design the module is
otherwise careful about.

**Severity: MAJOR** — this is exactly the project's most-repeated finding category ("a check
that cannot fail") applied one level up: a mutation that can never be generated is a hole that
mutation testing itself cannot report.

### Everything else read and checked, nothing further found
- Lock re-entrancy (`_HELD` / `_hold_lock`), staleness handling (`_pid_alive`,
  `_pid_alive_windows`), the differential `_gate_result` scoring, `unusable_gates`/`flaky_gates`,
  `verify_restore`, the `gates=gates+confirm` consistency between `baseline()` and
  `flaky_gates()` under `--no-confirm` (line 1017-1021) — all read carefully, all internally
  consistent with their own extensive commentary and no contradictions found.
- `_journal`/`_record_reap`/`survivors_on_record` are correctly append-only, `Exception`-safe,
  and write outside the sandbox tree they describe.
- `file_orders`, `main`, `_session` — no defects found.

---

## cleanup.py (234 lines) — read with the "anything that deletes" lens

This module never deletes files. Its only destructive-looking actions are in-place edits to
`data/records/*.json` via `PL.write_record`, gated behind `--apply` and printed as a dry-run
otherwise. Nothing here touches the filesystem the way `mutate.py`'s reaper does.

**Finding — `clean_ceiling`'s prefix-match strategy can silently pick the wrong entity when
two catalogued names share a stem (MINOR/QUESTION, not reproduced against live data).**
Lines 135-138:
```python
low_pref = [n for n in entry_names
            if n.lower().startswith(ce.lower()) and len(ce) >= 6]
if len(low_pref) >= 1:
    return min(low_pref, key=len), "prefix"
```
If a source catalogues two entries whose names share a common 6+ character stem (e.g. a base
form and a longer "Skarsgard Abraxis" / "Skarsgard Abraxis II" style variant that are genuinely
*different* entities rather than the same one written at greater length — the case the comment
above it explicitly designs for), `min(low_pref, key=len)` picks the shortest candidate with no
check for ambiguity, and on a length tie the choice is effectively arbitrary iteration order.
The function has no signal to distinguish "same entity, written longer" from "different entity,
same stem" — it assumes the former unconditionally. I did not find a live case where this
misfires (would need to scan `ceiling_entity` values against every source's entry-name list),
so this is flagged as a question about the algorithm's edge case, not a confirmed wrong output.

Everything else — the `_NAV`/`_MARKUP`/`_EMPTY_MECHANIC` regexes, the mangled-escape guard at
line 95-99 (confirmed real: it checks `_SETTING_META` imported from `pipeline.py` too, not just
this file's own patterns), `clean_description`, and the thin-description `changed = True` bug
documented in the code itself as already fixed (line 197-203, "run #29, batch 05, reproduced")
— all read, all correct, all consistent with their commentary. `nav[:5]` / `ceil_fixed[:6]` /
etc. in `main()`'s printed report (lines 212-227) are **not** a Hard Rule 0 violation: full
counts are printed alongside (`len(nav):,`), and the loop above applies fixes to every record
regardless of what the console preview shows — only the terminal display is capped, not the
work performed or the data reported as existing.

---

## genre.py (326 lines) — edited today

**Finding — discarded `write_json` verdict, MAJOR.** Line 319-320:
```python
silence.write_json(p, out, indent=2, ensure_ascii=False)
print(f"\nwrote {p}")
```
`silence.write_json` returns `True`/`False` (`False` on a persistently denied `os.replace`,
per `silence.replace_retry`'s docstring). The return value here is thrown away and `"wrote {p}"`
prints unconditionally, so a denied write is reported as a success — this is precisely category
5 from the sweep brief, and precisely the bug class `verify_math.py` already has a named,
numbered regression check for (order `1018d49b186e`, `_writejson_calls_discarded_b2`,
line ~5660-5680) — but that check's file list is hardcoded to exactly three files
(`catalogue_aurora.py`, `scope.py`, `sevenfold.py`) and does not cover `genre.py`. The comment
immediately above this call (line 315-318) discusses *atomicity* at length ("`GENRES.json`
could not have been half-written even so") but never addresses the *discarded-verdict* half of
the same write — the exact distinction the order-`1018d49b186e` fix elsewhere was written to
correct. `data/GENRES.json` feeds `navtree.py` and (per this same docstring) `profile.py`, whose
own load path silently falls back to `{}` on a failed load — so a refused write here plus a
stale file left in place reads downstream as legitimate data, indistinguishable from a real run.

Everything else read and checked, nothing found: the `GENRES` cue tables (spot-checked several
regexes — no unescaped word-boundary issues, no obviously wrong weights), `classify_text`'s
`top=None` fix and `classify_source`'s `cap=None` refusal (both already correctly land as hard
`SystemExit`s per Hard Rule 0, matching their own extensive commentary and measured numbers),
`_project_pipeline`'s interpreter-diagnosis wrapper, and `main()`'s unbounded low-confidence
report (line 294, correctly ranks without truncating).

---

## manifest_builder.py (503 lines)

**Finding — discarded `write_json` verdict, MAJOR, same class as genre.py above.** Line 462:
```python
silence.write_json(out_path, {"jobs": all_jobs}, indent=2)
print(f"Wrote {len(all_jobs)} jobs from {len(build_pool)} sources -> {out_path}")
```
Identical shape to the `genre.py` finding: the boolean landed/denied verdict is discarded and
the success line prints regardless. `manifest.json` (or `manifest.pilot.json`) is the input
`generate.py` reads to drive the entire local-model generation run — a silently-stale manifest
here (e.g. a concurrent reader holding the file open, which `silence.replace_retry`'s own
docstring says is a real recurring situation on this project's shared state files) means
`generate.py` would run against yesterday's job list while the console log for *this* run claims
the fresh one landed. Also uncovered by `verify_math.py`'s `1018d49b186e` regression check (same
three-file allowlist as above).

Everything else read and checked, nothing further found:
- `content_hash` — straightforward, sorts keys, stable.
- `load_record`'s closeness-ranked filename matching (lines 66-104) — the documented DC /
  Sword Coast Adventurer's Guide collision fix is real and the current data confirms it: `dc.json`
  exists as an exact match (`data/records/dc.json`), so `abs(len(norm_fname)-len(norm_target))`
  scores it 0 and it always wins over any coincidental longer substring match. The general
  algorithm still has no length floor on the free `norm_target in norm_fname` branch, so a
  *hypothetical* short source name with no close-length record file of its own could in
  principle still collide — flagged as a structural question, not a live bug: checked the
  current roll's short names (`Alien`, `ARMS`, `Baki`, `DC`, `Doom`, `Dune`, `Halo`, `HAWX`,
  `XCOM`) and every one has its own close-length record file, so nothing currently misfires.
- `pack_feats`'s pagination-not-truncation of oversized entities (lines 146-217), the
  flush-before-exceeding fix, and the single-deed-larger-than-budget case — all match their
  commentary and correctly avoid Hard Rule 0.
- `provisional_spine`, `build_jobs_for_source`'s frontmatter/chapter/feats job construction, the
  feats-lookup-failure loud-warning fix (lines 326-333, confirmed real: catches `Exception`,
  notes it, AND prints a warning distinguishable from "no feats"), `context_budget` integration
  and `budget <= 0` refusal — all read, all correct.
- `main()`'s volume-numbering-per-Series fix, owner-exclusion handling, and the
  `unassigned_sources.md` report that is correctly rewritten (not just conditionally appended)
  every run so it can't go stale in the direction described in its own comment (lines 471-499)
  — read and correct.

---

## scout.py (431 lines)

**Finding — one more discarded `write_json`-family verdict, MINOR (lower severity than the two
above: no explicit success line follows it).** Line 403, inside `sweep()`:
```python
_land(LOG, prev[-40:], sort_keys=False)
```
`_land` (line 59-75) is itself just `return silence.write_json(...)` — its own docstring is
explicit that it exists specifically so this module's writes go through the atomic path — but
this one call site to it discards the returned bool. Every *other* shared-state write in this
same file (`_mutate`'s callers at lines 288-292, 302-306, 381-383) correctly checks `landed` and
calls `silence.note(...)` when it's `False`; this is the one call in the file that doesn't. No
false "success" message is printed afterward (the function just returns `results`), so the
externally-visible damage is smaller than the `genre.py`/`manifest_builder.py` cases — but a
refused write here silently caps `data/SCOUT.json`'s log at whatever it last successfully held,
with nothing recording that the append was dropped.

Everything else read and checked, nothing further found: `_mutate`'s compare-and-swap
read-modify-write (correctly uses `silence.digest_of` + `silence.replace_if_unchanged`, not a
bare read-then-write — this is the fixed version of exactly the concurrency hazard category 4 in
the sweep brief describes), `verify`'s reason-distinguishing 404/403/no-names logic and its
`min(MIN_NAME_HITS, len(usable names))` floor for single-name sources (lines 212-228, confirmed
by reading — the floor is `max(1, min(MIN_NAME_HITS, probeable))`, matches the docstring's
worked example), `scout()`'s uncapped URL verification (correctly proves every proposed URL,
Hard Rule 0 note at line 263-268 is accurate to the code), and `sweep()`'s last-attempted-first
rotation with `deferred` printed by name rather than silently dropped (lines 338-363, matches
its own extensive commentary about the entry-count-ordering bug it replaced).

---

## wiki_source.py (675 lines)

Read in full. This module does not write any shared JSON state itself (no `write_json`/`_land`
calls anywhere in the file — it's pure fetch/parse), so the discarded-verdict pattern found
elsewhere in this batch doesn't apply here. Nothing found:

- `_get`'s rate limiting is a real global lock plus a per-host throttle borrowed from `feats.py`
  (line 174-179) — not a fixed-name-tmp-file concurrency hazard, just a shared in-memory rate
  gate; correctly guarded with `threading.Lock()`.
- `resolve_wiki`'s host-map-first resolution, the `isinstance(known, str)` guard against a
  non-dict `WIKI_HOSTS.json`, and the non-fandom-known-host short-circuit (avoiding wasted
  requests against an IP-banned host) — all read and match their extensive commentary exactly.
- `verify_wiki_matches` — reasonable heuristic (`matched >= max(1, len(distinctive)//2)`); a
  design choice, not a defect.
- `all_categories`'s `hard_stop=None` default (the removed 6,000-category truncation) and
  `category_members`'s `limit=None` default are both genuinely uncapped by default, and I
  traced every live call site (`catalogue_web.py`) to confirm nothing passes a non-None limit
  in the actual pipeline — `catalogue_web.py:117` explicitly comments `top=None  # rank, never
  truncate` and `catalogue_web.py:274-277` hard-refuses (`raise SystemExit`) if `MAX_PER_SOURCE`
  is ever set to a non-None value, so a caller can't silently reintroduce a cap. This confirms
  Hard Rule 0 compliance for this module's actual usage, not just its defaults.
- `_paragraphs`'s infobox/quote-box stripping order (pull `<p>` before removing anything) — the
  documented reasoning for the ordering checks out against the two failure modes it names.
- `rank_by_size`, `clean_titles` — no defects found.

---

## tempus.py (267 lines)

Read in full — a small, mostly self-contained arithmetic module (institutional simultaneity,
description-length pricing derived from `assay.BAND_EDGES`). No defects found.

`apparent_lag_years`'s uniform-return-shape fix (both branches always carry `distance`/
`lag_years`/`path`/`note`) is real and correct. `contemporaneous`, `is_present_at`,
`concordance_now`, `loop_report`, `rung_description_length`, `band_resolution` (including its
M10-inherits-M9-width edge case) and `retrocausality_beta` were each checked against their
docstrings' worked formulas and are consistent.

**Minor inconsistency (QUESTION, not a live bug):** `prescience_horizon_bits(band, lead_time_years)`
(line 225-254) does not validate `lead_time_years > 0` the way `physics.py`'s functions in this
same batch validate mass/radius/volume — a negative `lead_time_years` would silently produce a
negative `bits_required` with the same "wrong number wearing the shape of a right one" character
`physics.py` explicitly writes long comments about avoiding. Checked every call site
(`verify_math.py`, the only caller in the tree) and all pass positive literals, so this is not
currently reachable with bad input — flagged only because the module sits right next to a
sibling file that treats exactly this class of input defensively and this one does not.

---

## physics.py (193 lines) — edited today

Read in full. All four physical-quantity functions (`kinetic`, `joules_for`, `sphere_volume`,
`binding_energy`) were checked against their stated formulas:
- `kinetic`: Newtonian `0.5*m*v²` below `0.1c`, relativistic `(γ-1)mc²` above it — correct, and
  the `v >= C` refusal is checked before the relativistic branch so no domain error can reach
  `math.sqrt` with a negative argument.
- `sphere_volume`: `4/3·π·r³` — correct.
- `binding_energy`: `3GM²/(5R)` — correct; separately validates `r > 0` (denominator) and
  `m >= 0` (mass may legitimately be zero, unlike the other three functions where a zero input
  is treated as "no body to speak of" and refused).
- All four correctly raise rather than silently defaulting or computing a sign-wrong result, and
  each one's raise carries a distinct value in its error text, so `assay.py`/callers can't
  mistake one non-positive-input rejection for another. `MATERIAL`'s specific-energy table and
  the Ledger-Standard cross-reference to `assay.BAND_EDGES` (asserted by `verify_math`, not by
  this file) are consistent with the module's own docstring.

**Minor/cosmetic (QUESTION):** the mangled-escape guard at lines 53-55 —
```python
_BAD_CHARS = (chr(8), chr(11), chr(12), chr(7))
if any(c in open(...).read() for c in _BAD_CHARS):
    raise SystemExit(__file__ + ": a regex escape was eaten in transit.")
```
— is the same guard `cleanup.py` and `scout.py` (this batch) carry, but unlike those two files,
`physics.py` contains **no regex at all** (`import re` is absent; grepped the whole file to
confirm). The guard is harmless (it can only ever pass here) but its error text names a failure
mode ("a regex escape was eaten in transit") that cannot occur in this specific file — reads as
boilerplate copied from a sibling module rather than something reasoned about for this one. Not
worth removing on its own (defense-in-depth against *any* transit corruption, not just regex),
but the message is misleading if it ever did fire for an unrelated reason.

---

# Findings summary

1. **MAJOR** — `mutate.py` `_owner_pid`/`_claim_sandbox`: the `started` timestamp is recorded
   but never cross-checked against the live process, so a recycled PID landing on any other
   live process defeats the M46 ownership fix and can re-leak sandboxes indefinitely.
   Anchor: `pid = json.load(fh).get("pid")` (`_owner_pid`, mutate.py ~line 516) never reads
   `started`; written at `mutate.py:530`.
2. **MAJOR** — `mutate.py`/`drill.py`: the M46 fix's core claim (live owner protects an old
   sandbox) is not exercised by any test. `abandoned_sandboxes_are_reaped` in drill.py never
   writes an `_owner.json` for either probe directory. Anchor: `os.makedirs(p, exist_ok=True)`
   with only `marker.txt` written, drill.py ~line 4247.
3. **MAJOR** — `mutate.py` `_mutations()`: `line.replace(old, new, 1)` only ever mutates the
   FIRST occurrence of a repeated operator/keyword on a line, so a line with two instances of
   the same comparison/boolop/`not`/`True`/`False` never gets its second instance independently
   mutated — a silent, reproducible hole in mutation-testing coverage. Anchor:
   `line.replace(got[0], got[1], 1)`, mutate.py line 337 (and the identical pattern at 344, 349,
   355, 360); reproduced directly against `_mutations()`.
4. **MAJOR** — `genre.py:319-320`: `silence.write_json(p, out, ...)` return value discarded,
   followed by an unconditional `print(f"\nwrote {p}")`. Same bug class as order `1018d49b186e`
   (verify_math.py ~line 5651), which fixed three other files but not this one.
5. **MAJOR** — `manifest_builder.py:462-464`: `silence.write_json(out_path, {"jobs": all_jobs},
   indent=2)` return value discarded, followed by an unconditional `print(f"Wrote {len(all_jobs)}
   jobs ... -> {out_path}")`. Same bug class as #4; `manifest.json` is the input to `generate.py`'s
   whole run.
6. **MINOR** — `scout.py:403`: `_land(LOG, prev[-40:], sort_keys=False)` return value discarded
   (every other shared write in this file checks it). Lower severity than #4/#5: no false-success
   line is printed afterward.
7. **MINOR** — `mutate.py` `sandbox()`/`reap_orphans()`: unproven narrow race between
   `tempfile.mkdtemp()` and `_claim_sandbox()` when `reap_orphans` is called with a small
   `older_than` (as the drill net legitimately does); the age gate no longer covers this window.
   Not reproduced in practice.
8. **MINOR/QUESTION** — `cleanup.py` `clean_ceiling`'s prefix-match (lines 135-138): picks
   `min(low_pref, key=len)` with no ambiguity check when two different catalogued entities share
   a 6+ character name stem. Not reproduced against live data.
9. **MINOR/QUESTION** — `manifest_builder.py` `load_record`'s free substring-match branch
   (line 97) has no length floor; the documented DC/Sword-Coast fix works because the closest-
   length candidate is always correct in current data, but the algorithm doesn't structurally
   guarantee that for a hypothetical future short source name with no close-length record file.
   Checked all current short (≤5 char) roll names — none currently misfire.
10. **MINOR/QUESTION** — `tempus.py` `prescience_horizon_bits`: no positivity check on
    `lead_time_years`, unlike its sibling `physics.py` in this same batch. Not currently
    reachable with bad input (only caller passes positive literals).
11. **QUESTION (cosmetic)** — `physics.py` lines 53-55: the mangled-regex-escape guard is
    boilerplate carried over from sibling files; this file has no regex, so the guard's message
    ("a regex escape was eaten in transit") can never be the true cause if it ever fires.

No modules were unreadable; all eight were read in full.
