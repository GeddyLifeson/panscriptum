# Sweep41 — Batch 16 audit

Modules (8, 5,060 lines total, all read in full):

| module | lines |
|---|---|
| src/binding_health.py | 1,218 |
| src/local_agent.py | 1,212 |
| src/gpu_lane.py | 684 |
| src/sweep_plan.py | 571 |
| src/worldseed.py | 466 |
| src/render.py | 336 |
| src/runguard.py | 303 |
| src/roll.py | 270 |

This is an audit. No file under `src/` was edited. `src/drill.py` was not run against the live
tree. `gpu_lane.LANE` was never pointed anywhere in this session (no gpu_lane call was executed).
`local_agent.py` was read only, never run. Coverage recorded via
`sweep_plan.record('run41', [...8 modules...], batch=16)`.

## Findings filed

| id | code | severity | handler | module |
|---|---|---|---|---|
| 556c1b8fda9f | LOCAL_AGENT_HARDLINK_BYPASS | MAJOR | SESSION | src/local_agent.py |
| c738ca184269 | RENDER_VIEWS_WRITE_NOT_ATOMIC | MINOR | LOCAL | src/render.py |
| 60cb4e0e3595 | ROLL_UPDATE_ROWS_SEEN_ON_EMPTY_CHANGE | MINOR | LOCAL | src/roll.py |

### 1. LOCAL_AGENT_HARDLINK_BYPASS (MAJOR, SESSION) — a seventh gate bypass

`local_agent.py`'s brief asked to look for a fifth bypass of `propose_patch`'s denylist; the file
as it stands has already documented and fixed five (case, name prefix, NTFS alternate data
stream, case-sensitive extension x2) plus a sixth (directory junctions/reparse points, closed via
`os.path.realpath()` comparison in `_safe()`). I looked for a seventh and found one: **NTFS hard
links**.

Verified experimentally on this machine (not against the live repo — a throwaway pair of files in
the scratchpad, `mklink /H`):

- writing through a hard link mutates the exact same underlying file as its target (confirmed: a
  write through the link showed up reading the target)
- `os.path.realpath()` on a hard-linked path returns the path **as written, unchanged** — unlike a
  junction or symlink, there is no reparse point for `realpath` to follow, because a hard link is
  just a second ordinary directory entry pointing at the same file record

`_safe()`'s junction defence only interrogates `_denied_target()` on the resolved path when
`rel_written != rel_real` — i.e. when the filesystem disagrees with the string. For a hard link,
it never disagrees, so the branch never fires, and none of `t_propose_patch`'s three refusals
(module denylist / `DENYLIST_PATHS` / `DENYLIST_PREFIXES`) ever see the protected file's real
name, because the path as written never contains it. A hard link placed inside the writable
surface (e.g. `handoff/notes.py`) pointing at the same file record as `src/foreman.py` or
`config.yaml` would pass every gate and silently corrupt the protected file's real bytes.

This is the identical shape to bypasses four through six, verbatim in the file's own words: "a
gate keyed on a string while the filesystem resolves a different string to the same object" — the
one difference is that a hard link needs no resolution step at all, which is exactly why
`realpath()` is blind to it.

**Not currently reachable**: `local_agent`'s own model has no tool that creates a link of any
kind, and nothing in `src/` creates hard links today (only `mklink /J` junctions, in `drill.py`
and `mutate.py`) — the same "not currently exploitable" condition the docstring itself records for
bypass classes four and five before they were closed. Filed anyway, at the same standard this file
already holds itself to: a gate checking the wrong object is a gate whether or not anything is
standing in front of it yet.

Filed at SESSION rather than LOCAL deliberately: this is the module that gates the local model's
own write access to `src/`, and a bad self-patch here is a worse failure mode than the bug it
would fix. Recommended remedy left in the order: compare file identity (`st_ino`/`st_dev`, or
`GetFileInformationByHandle` on Windows) between the write target and every protected file that
currently exists on disk, alongside the existing string-based checks.

### 2. RENDER_VIEWS_WRITE_NOT_ATOMIC (MINOR, LOCAL)

`render.py main()`'s `--write` path writes each of the five drawn tiers' SVGs to
`output/views/<tier>.svg` with a bare `open(p, "w") ` + `f.write(...)` — truncate-then-fill, not
atomic. This is the same defect class `worldseed.py`'s own `--write` path documents fixing for
`WORLDSEEDS.json` ("the 2026-08-25 sweep found twelve such sites across ten modules and moved
them onto `silence.write_json`... every sibling cross-cycle artifact already goes that way"), and
`generate.py` already writes `output/raw` chapter files through `silence.replace_retry` rather
than a bare `open()` — so `output/` is not treated as exempt from atomic-write discipline
elsewhere in this codebase.

Checked reachability before filing: grepped `src/*.py` and `registry_terminal/*.js` /
`*.html` for any reader of `output/views/*.svg` — none exists today, so the practical exposure is
low (single CLI invocation, no known concurrent reader). Filed at MINOR, for consistency with
house convention rather than as a live hazard. SVGs aren't JSON so `silence.write_json` doesn't
apply directly; the fix is the tmp-with-pid + `silence.replace_retry(tmp, p)` pattern several
other modules in this batch already use for non-JSON atomic writes, with the landed/not-landed
verdict reported rather than discarded (the current code doesn't check for a write failure at
all).

### 3. ROLL_UPDATE_ROWS_SEEN_ON_EMPTY_CHANGE (MINOR, LOCAL)

`roll.py update_rows()`'s inner `_apply()` marks a source name `seen` only `if ch:` (i.e. only
when the caller's per-source change dict is truthy/non-empty). `missed` — reported to the caller
as `"no roll row is named %s any more"` — is every name in `changes` not in `seen`. So a caller
that passes an *existing* source name with an *empty* change dict gets that row reported as
vanished/renamed even though it demonstrably exists on the roll: the code conflates "found the row
but there was nothing to change" with "no row is named this any more."

Checked the one relevant caller in `src/` before filing: `catalogue_web.py:190-193` builds change
dicts as `{k: v for k, v in r.items() if k != "name"}`, and a roll row always carries more fields
than `name` in practice (status, entry_count, ...), so this is not observed to fire there today.
Filed anyway as a verified logic defect independent of today's callers — `catalogue_aurora.py`,
`catalogue_codex.py` and `recover_folder_records.py` also call `update_rows` and were not traced
field-by-field for the same guarantee. Fix: track `seen` on row match, not on change-dict
truthiness.

## Checked and found sound (no new findings)

- **`binding_health.py`** — the three-probe canary (present/absent/reachable), the CAS-protected
  `quarantine()`/`release()`, the `binding_verdict()` fuzzy-name confirm/misbound/unclassified
  logic, and `run()`'s partial-pass merge guard were all read in full and are internally
  consistent with their own extensive docstrings. Spot-checked the one live cross-module claim
  that mattered here — `_BLOCKED_MARK = "refusal marker"` is asserted to be a substring of
  `feats.page_looks_real`'s own refusal wording — against `src/feats.py:251` ("carries a refusal
  marker (%r)"): confirmed, it matches.
- **`gpu_lane.py`** — already carries today's fixes (`_unreadable_and_stale`, `status()`'s
  `partial` flag). Read the rest in full (foreground refcounting under `_DEPTH_LOCK`, the
  three-way `_take_slot` return, the heartbeat thread, `_remove_retry`'s backoff) and found no
  further defect.
- **`sweep_plan.py`** — already carries today's fixes (shard-write temp cleanup on a denied
  replace, `batches()`'s `unreadable` carry-through). Specifically hunted for "coverage recorded
  without being read" per the brief: `record()`'s trust boundary (a caller's `covered` list is
  taken on faith) is structural to a self-reporting coverage system and not fixable at this layer;
  a bogus/typo'd module name in a shard cannot hide a real gap because `missing()` iterates real
  `modules()` and only asks membership. No new gap found. (Per instructions, did not re-file order
  4d44a6363245 — `batches()` shifting under live line-count edits — which is already known.)
- **`worldseed.py`** — already carries today's fixes (the whole-description regex scan, the
  ONOMASTICON/CONTINUITY_GROUPS read-failure reporting, the atomic `WORLDSEEDS.json` write, the
  designation-collision report). The one open item in the file (`"primitive"` tier being
  unreachable from `TECH`) is already a standing owner question (order ad681057369a) — not
  re-raised.
- **`runguard.py`** — read in full. `claim()`/`beat()`/`release()` all take the CAS digest before
  the read (verified the ordering argument holds: an intervening successor claim is caught either
  by the fresh ownership check in `beat()`/`release()`, or by `_land_claim`'s own re-digest at
  write time). No new defect found.
- **`roll.py`** — `mutate()`'s CAS-based read-modify-write and `exclude()`'s
  `silence.write_json` direct write both already match the house atomic-write convention the
  brief asked me to check for; no bare `open(path, "w")` full-document write exists in this file.
  (The one logic defect found, above, is in the merge helper `update_rows`, not the write path.)

## Not filed, and why

- The batch-membership-shifts-under-live-edits behaviour of `sweep_plan.batches()` — already known
  (order 4d44a6363245), instructed not to re-file.
- `worldseed.py`'s unreachable `"primitive"` TECH tier — already a standing owner question (order
  ad681057369a), not new.
- A theoretical concern in `roll.py exclude()`'s non-`mutate()` direct-write path (a blind
  `silence.write_json` rather than a CAS, when `rows` isn't supplied) — this is explicitly argued
  and signed off in the function's own docstring (short window, no `src/` callers, pinned by a
  live battery check naming this exact call site) rather than an oversight. Not filed as a
  question either, since the docstring already represents a reasoned owner-adjacent decision, not
  an open one.
