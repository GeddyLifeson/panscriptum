# BATCH 06 AUDIT — run32

Modules read in full, every line:

| file | lines |
|---|---|
| src/read.py | 1173 |
| src/completeness.py | 482 |
| src/prose_gate.py | 347 |
| src/weave_index.py | 276 |
| src/burgs.py | 235 |
| src/audit.py | 177 |
| src/resync_roll.py | 81 |

---

## PROSE GATE — explicit verdict (per the task's safety instructions)

**VERIFIED: `prose_gate.py` fails closed correctly and has NOT been weakened.**

- `gate_open()` (prose_gate.py:68-87) checks `cfg.get("prose_enabled", False) is not True` —
  strict identity, not truthiness. A missing key, `"false"` (string), `0`, `[]`, `"true"`
  (string) all correctly fail closed. Only the Python boolean `True` opens it.
- Unreadable/unparseable config, or a config that doesn't parse to a `dict`, both fail closed
  (lines 74-83).
- `step4_gate_open()` additionally requires `STEP4_PLAN.md` to exist on disk before even
  looking at the flag (lines 90-116) — fails closed if the plan is missing.
- `evidence_ok()` (line 163) rejects a floor `<= 0` as MISCONFIGURED rather than silently
  admitting everything — closes the exact "floor=0 admits a zero-cited source" hole.
- `unearned_instrument()` / `cited_names_for()` look up real mined citations through
  `cachekey`, fail closed (empty set) on any read error, so an axis score with no cited feat
  is always flagged, never silently passed.
- Cross-checked `overnight.py:71-72` (`_prose_enabled`): it now **delegates directly to
  `prose_gate.gate_open(cfg)[0]`**, not a reimplemented `bool()` check — the previously-reported
  `"false"`-string bug is fixed and there is no second, looser copy of the check anywhere in
  `src/`. `config.yaml:108` confirms `prose_enabled: false` on disk right now — the gate is
  closed as ruled.

No loosening proposed or found. Did not touch this file.

---

## BLOCKING

**`src/read.py:627` + `src/read.py:776-780` — TOCTOU on the entity cache write path (confirmed).**
`path = cachekey.write_path(CACHE, host, name)` is computed once at function entry (line 627),
before minutes of model calls (the chunk-read loop, lines 706-753). `write_path()`
(cachekey.py:119-134) decides `path` by checking, **at that instant**, whether the natural path
is already owned by a *different* entity (colliding sanitised filename) — if free, it returns
the natural path; if taken by someone else, a disambiguated sibling. That decision is then acted
on minutes later (lines 776-780) with no re-check. `read.py` runs entities concurrently via
`ThreadPoolExecutor` (`run()`, line 1116), and `cachekey.py`'s own docstring documents **real,
measured collisions in this corpus** ("5 colliding key slots, 10 entities... plus 59 entities at
the 80-char cap"). If two colliding-name entities on the same host are both mid-read at once
(a realistic scenario at workers=8-16 over an hours-long pass), both can see the natural path
free at entry, both compute `path = nat`, and whichever finishes second silently overwrites the
first entity's completed record with its own — defeating the entire M23 fix (`cachekey.py`'s
"WRITES DISAMBIGUATE" guarantee) under the exact concurrency this module runs with. The lost
entity's evidence is not flagged; nothing errors.

**`src/read.py:777` — hand-rolled `tmp = path + ".tmp"`, not pid/thread-tagged (confirmed, and
inconsistent with the same file's own fix 170 lines earlier).** The entity-record write does:
```
tmp = path + ".tmp"
with open(tmp, "w", encoding="utf-8") as f:
    json.dump(out, f, indent=1, ensure_ascii=False)
silence.replace_retry(tmp, path)
```
This is exactly the anti-pattern `silence.write_json`'s own docstring names as fixed
elsewhere in this same file: `_chunk_put` (read.py:596-613, specifically line 607) tags its temp
file with `os.getpid()` and `threading.get_ident()` *precisely because* two workers writing the
same passage at once would otherwise "collide on the temp file itself, and the loser can
replace the winner's target with a partial file." The entity-level write directly below it does
not carry that fix. Combined with the TOCTOU above, two colliding-name entities racing to finish
at once don't just target the same final path — they can share the same staging file mid-write,
producing a corrupted/interleaved JSON or a silent full overwrite. This is the same defect class
flagged for `burgs.py:225` in the task brief (see below) and matches lens item 4 exactly. Fix
direction (not applied, audit only): call `silence.write_json(path, out, ...)` here instead of
the hand-rolled block, same as everywhere else the project has already converged on.

---

## MAJOR

**`src/burgs.py:225-230` — the reported "hand-rolled tmp+os.replace" lead does not match current
code; what's actually there is worse (confirmed, different defect).** At the reported location
(`if args.write:` block) there is **no tmp file and no `os.replace`/`silence.replace_retry` at
all** — it's a bare `open(p, "w")` + `json.dump`, the exact "m6 pattern" `completeness.py`'s own
docstring (lines 373-380) calls out as one of "this project's oldest species" of bug: it
truncates the target before serialising, so a crash mid-write or an unencodable value leaves
`data/BURGS_SAMPLE.json` permanently corrupt, and any concurrent reader sees a truncated file.
No other module currently reads `BURGS_SAMPLE.json` (grepped), so there's no live two-writer
collision today, but the write itself is not even single-writer-safe against a crash. Either the
lead's line number drifted from an earlier version of this file, or the tmp+replace pattern was
already removed since the lead was recorded — either way, confirm the *concern* (unsafe write in
`burgs.py`), not the literal mechanism described.

**`src/burgs.py:230` print message contradicts the code it describes (comment/docstring vs.
code, lens item 6).** `worlds = WS.build_all()` is called with no `limit` (line 190, itself
commented "every world; Hard Rule 0"), and the write loop iterates `for w in worlds` with no
slicing, so `per_world` written to disk holds **every** world's full burg roster. The very next
line prints `"wrote {p} (sample of 50 worlds; the rest regenerate on demand)"` (line 230) — a
claim the code directly contradicts. Not a data-loss bug (the file holds more than the message
claims, not less), but it will mislead an operator about the size/content of
`BURGS_SAMPLE.json` and about whether Hard Rule 0 is honestly satisfied here (it is, the message
is just stale/wrong).

---

## MINOR

- **`src/burgs.py:147`** — `for k in range(1, (limit or n) + 1):` treats an explicitly-passed
  `limit=0` the same as "no limit" (0 is falsy), silently returning the full `n`-length roster
  instead of zero rows. No caller currently passes `limit=0` (CLI `--limit` defaults to `None`,
  and `0` isn't a meaningful ask), so low real-world exposure, and the failure direction is
  "returns more, not less" — the safe direction under Hard Rule 0 — but it is a genuine
  truthiness bug (should be `n if limit is None else limit`).

- **`src/completeness.py:112-116`** — `category_size_probe`'s on-disk cache
  (`state/category_sizes.json`) is written with a hand-rolled `tmp = _CS_CACHE_P + ".tmp"`, not
  pid/thread-tagged, same class of defect as `read.py:777` but far lower stakes: it's a
  12h-TTL, self-healing lookup cache (worst case on a lost/corrupted write is a few extra API
  probes next run), not authoritative data. `land()` in the same file, by contrast, is a model
  example of getting this right — checks `replace_retry`'s return value, refuses to shrink the
  corpus below `SHRINK_FLOOR`, and reports failure loudly on stderr with a non-zero exit.

- **`src/weave_index.py:224`** — `"description": (e.get("description") or "")[:400]` truncates
  each entity's description before it's written to `data/ENTITY_INDEX.json`. This file is read
  by `weave.py`'s `filtered_index()` to decide whether an entry is game-mechanics text that
  should be dropped from cross-source matching (`_STATBLOCK.search(desc[:400])`,
  `_RULES_VOICE.search(desc[:300])` — both slices are already no-ops against an input that's
  never longer than 400 chars, confirming the truncation happens upstream in `weave_index.py`,
  not there). A description whose rules-voice or statblock markers sit past character 400 would
  never be seen by that filter. Not a roster/list truncation (Hard Rule 0's literal target) but
  a same-shaped silent data reduction feeding an automated classification step; worth measuring
  how often real descriptions exceed 400 chars before ruling it out.

- **`src/resync_roll.py`** — reads the whole `data/SWEEP_ROLL.json` into memory at the start
  (line 34), walks every record file (which can take real wall-clock time over 217 files), then
  writes the **entire** in-memory `roll` list back atomically (line 68) even for entries it
  didn't touch. The atomic write (added "2026-08-25" per its own comment) fixes the
  *truncate-then-fill* corruption hazard the docstring describes, but not the *stale-read*
  hazard in the same docstring's own incident story: if a cataloguer writes a fresh
  `SWEEP_ROLL.json` while this script is mid-run, this script's final write will still silently
  revert that concurrent change to what it read at start, because nothing detects that the file
  changed underneath it (no mtime/hash check before the final write). The docstring's prescribed
  usage is "after any cataloguing session" (sequential, not concurrent), so this is a latent risk
  rather than an active one, but nothing in the code enforces that ordering.

## NOTE

- **`src/audit.py:49-53`** — `band = syn.get("provisional_magnitude")` is checked against
  `VALID_BANDS` (which does not include `None`) whenever the outer `if syn:` truthy-dict check
  passes. Traced every writer of the `synthesis` key: `catalogue_web.py` (lines 137, 271) always
  writes the whole key as `None` (so `syn` is falsy and the block is skipped, correctly), and
  `pipeline.py`'s synthesis phase (line 831) always writes a fully-populated dict where `band`
  is guaranteed to be `"unassayed"` or a real `M#` string, never `None`. So this did **not**
  reproduce as a live false-positive against current writers — flagging only because the
  invariant ("if `syn` is truthy, `provisional_magnitude` is never `None`") is enforced by
  convention across multiple files rather than by one shared constructor, which is the exact
  shape of assumption this project's own standing lessons warn drifts silently. A future partial
  write (crash mid-`rec["synthesis"] = {...}`, or a new caller following `repass_bands.py`'s
  pattern less carefully) would make every such source falsely fail "band not on the ladder."

- **`src/prose_gate.py`, `src/completeness.py`, `src/resync_roll.py`, `src/weave_index.py`** —
  all other atomic-write call sites checked use either `silence.write_json` or a pid/thread-safe
  hand-rolled temp name; no other Hard-Rule-0-style caps found outside what's listed above (all
  `[:N]` slices located are either print/display formatting or explicitly-documented, bounded
  sampling with the full data still written to disk).

---

## Summary of severities

- BLOCKING: 2 (both `read.py`, compounding: TOCTOU on write path + non-unique tmp name)
- MAJOR: 2 (`burgs.py` write safety, `burgs.py` stale/contradictory message)
- MINOR: 4
- NOTE: 2
