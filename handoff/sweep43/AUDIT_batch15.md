# Sweep 43, Batch 15 — Audit

Files read in full: `src/assay.py`, `src/dashboard.py`, `src/wiki_source.py`, `src/liveness.py`,
`src/address.py`, `src/pantheon.py`, `src/resync_roll.py`, `src/cachekey.py`, `src/catalog.py`.

Method note: every one of these files (assay.py, dashboard.py, wiki_source.py, liveness.py,
address.py especially) already carries an unusually large amount of inline history documenting
prior fixes for exactly the shapes this sweep is asked to look for (inverted predicates,
tautologies, Hard Rule 0 caps, detectors that can't fire). Most candidate defects I traced
turned out to be the *documented, already-fixed* state, verified correct by re-reading the
current code against its own comment. I did not re-file anything already recorded as fixed or
as the standing open question on `ATTESTATION_FLOOR`. What follows is what remained after that
filtering, each checked against actual runtime behaviour (two with a live reproduction).

---

## src/resync_roll.py

### FINDING 1 — MAJOR — missing type guard crashes the whole resync on a malformed record file
`src/resync_roll.py:89-101`

```python
with open(os.path.join(RECORDS, fn), encoding="utf-8") as f:
    rec = json.load(f)
except Exception:
    silence.note("resync_roll.py:record-unreadable")
    unreadable.append(fn)
    continue
src = rec.get("source")
```

`rec.get("source")` sits **outside** the try/except that guards `json.load`. If a record file
parses as valid JSON but is not a dict — a bare `[]`, a string, a null, anything a torn or
manually-edited write could leave behind — `json.load` succeeds and returns a non-dict, and
`rec.get(...)` raises `AttributeError: 'list' object has no attribute 'get'`, uncaught. That
exception is not caught anywhere in `main()`, so the whole resync run dies instead of recording
the one file as unreadable and continuing — which is exactly the outcome this function exists to
produce for a bad file (see `unreadable.append(fn)` two lines above, and the `unreadable` count
this run is supposed to keep going and report). Verified live:

```
>>> rec = json.loads('[]')
>>> rec.get('source')
AttributeError: 'list' object has no attribute 'get'
```

This is the identical fault class this project already fixed one file over: `wiki_source.py`'s
`resolve_wiki()` guards its own hosts-file read with `isinstance(_doc, dict) else None`, with the
comment "PARSING IS A FILE OPERATION TOO... a JSON list parses fine and has no `.get`." That fix
was not carried to `resync_roll.py`'s own record read, which does the identical `.get()` off a
freshly-parsed JSON value with no isinstance guard.

**Remedy:** guard with `if not isinstance(rec, dict): silence.note(...); unreadable.append(fn);
continue` immediately after the `json.load`, before `rec.get("source")` is reached. Mechanical,
same shape as the existing `wiki_source.py` fix — LOCAL-sized fix, but I'm filing it as RUN
because the blast radius (a full script crash instead of one skipped file) argues for a careful
look rather than an unreviewed mechanical patch.

### FINDING 2 — MINOR — source name truncated in the printed repair table (Hard Rule 0, lesser instance)
`src/resync_roll.py:226` and `:234`

```python
print(f"  {name[:44]:46s} {was:6d} -> {now:6d}   {fn}")
...
print(f"  {name[:44]:46s} {str(was)[:14]:16s} -> {now:14s} (entry_count {n})")
```

Both lines cut the source name to 44 characters for column alignment. The full name is not lost
anywhere else (the roll and record files hold it uncut, and it prints uncut in the
`unmatched_rows`/`unnamed_rows` sections a little further down), so this is the "lesser instance"
Hard Rule 0 explicitly allows for — but it is the exact pattern `pantheon.py` was fixed for
(`d["cited"][:58]`, `epoch[:40]`) under the ruling that a display cap on an identifying string is
still a truncation, just fixed by wrapping/widening rather than by removing the column. Flagging
for consistency with that ruling, at the severity the ruling itself implies for a display-only cut.

**Remedy:** either widen the column or drop the `[:44]` (a long source name breaks alignment, not
correctness) — same treatment `pantheon.py`'s `--full` view got.

---

## src/dashboard.py

### FINDING 3 — MINOR — movement() compares the very first sample against itself, reporting "no change" instead of "first reading"
`src/dashboard.py:418-472` (the bug surfaces at line 472: `base = older[-1] if older else (hist[0] if hist else {})`)

On the very first call ever made against a fresh or just-reset `state/dashboard_history.json` —
i.e. right after `os.path.exists(HISTORY)` is False, or right after the "corrupt history must
heal" branch resets `hist = []` — the function does:

```python
hist = []                          # nothing on disk / just reset
...
hist.append(row)                   # hist is now [row] -- the CURRENT sample
...
older = [h for h in hist if h.get("at", 0) <= window]   # empty: row is brand new
base = older[-1] if older else (hist[0] if hist else {})  # hist[0] IS row itself
```

`base` ends up being the identical object as `row`, so for every metric `was = base.get(k) == v`
and `delta = v - was == 0`. The panel then reports `"no change yet"` (or, once span happens to
reach 10 minutes, `"stalled"`) rather than the `delta is None -> "first reading"` case the JS
(`panelMovement`) is written to distinguish — this is precisely the case the docstring says the
function exists to get right ("A number that has not moved now SAYS it has not moved... the
difference between an instrument and a decoration"), and on a genuine cold start it says the
opposite of the truth: there is no prior sample to compare against at all. Verified live with a
standalone reproduction of the exact code path (`base is row` -> `True`, `delta` -> `0`).

Self-limiting: it only occurs on the single poll immediately following an empty/absent/just-reset
history file, and the very next poll five seconds later compares against a real prior sample and
is correct. Given the corrupt-history-must-heal branch a few lines above resets `hist = []` on
every torn-file recovery, this cold-start path is reachable more often than "process start" alone
(any history corruption event re-triggers it for one poll). Cosmetic only — no downstream code
reads `stalled`/`reset` off this one poll to gate anything else.

**Remedy:** compute `base` from `hist` **before** appending `row`, i.e. take the snapshot for
comparison first, then append. That makes `hist[0]` genuinely "no prior sample" (`{}`) on a true
cold start, which already yields the desired `was is None -> delta is None -> "first reading"`.

### INFO — dead branch in the quota-panel colour helper (no functional effect)
`src/dashboard.py:746`

```js
const cls=f=>f<=0.001?'bad':f<0.15?'bad':f<0.4?'warn':'good';
```

The `f<=0.001?'bad'` arm is unreachable as a distinct outcome: any `f<=0.001` also satisfies
`f<0.15`, which resolves to the same `'bad'` result. Not a correctness bug (both branches agree),
just a redundant condition — noted only because "a comparison that can't go the other way" is
explicitly in this sweep's scope; not filed as a work order given zero behavioural effect.

---

## Modules read and found clean (no findings beyond what was already documented as fixed)

- **src/assay.py** — re-verified the weight normalisation (`WEIGHTS` sums to 1 across 8 physical +
  3 faculty axes), the `_check_scores`/`_check_weights` Layer-1 refusals, the ceiling/floor clamp
  in `assay()`, the covariance term in `_interval`, and `_check_constants()`'s import-time
  monotonicity/ceiling guard. All consistent with their own extensive commentary. Did not re-file
  the standing `ATTESTATION_FLOOR` question per instructions.
- **src/wiki_source.py** — `resolve_wiki`'s hosts-file isinstance guard, `verify_wiki_matches`,
  `all_categories`'s removed hard-stop, `category_members`/`rank_by_size`/`clean_titles` (all
  correctly uncapped per Hard Rule 0) all read correctly against their documented intent.
- **src/liveness.py** — re-traced the scoped `used`/`used_local`/`self_attr` construction that
  fixed the tool's own founding false-negative (the `coverage._p()` case); confirmed a module's
  functions can no longer keep each other alive across module boundaries, and that DEAD/DEAD
  CLASS/DEAD MODULE/TAUTOLOGY/PHANTOM passes match their docstrings. No floor-reported-as-total
  regression found.
- **src/address.py** — traced `spine_code_for`'s four-stage fallback (exact match, most-specific
  containment with the opens/closes exception, token-overlap with the exact-set exception) by
  hand against the documented collision cases (DC, Halo, Doom); the logic matches its own
  extensive verification notes. `promote()` is promotion-only as documented.
- **src/pantheon.py** — verified against the live data files, not just by reading: confirmed
  `data/Z_FIGHTERS.json` has all 11 axis keys with `score`/`cited` present on every entity, and
  that only "Son Goku" lacks `provenance` (matching the code comment's claim exactly), so the
  `--full` view's axis loop (`rec["axes"][ax]`, `d["score"]`, `d.get("provenance","?")`) cannot
  KeyError against current data.
- **src/cachekey.py** — `load()`/`write_path()`/`owns()` collision handling traced by hand across
  multiple simultaneous collisions on one natural slot; each colliding entity gets a distinct
  suffix (sha1 of its own exact name), no cross-contamination.
- **src/catalog.py** — small and clean; `cmd_stats`'s missing-sources list and `cmd_search`'s hits
  are both uncapped per Hard Rule 0.

---

## Questions for the owner

None raised this batch beyond the standing filed one (`ATTESTATION_FLOOR`, not re-filed here).
