# AUDIT — BATCH 06 (run31)

Modules: `src/read.py` (1164 lines), `src/gpu_lane.py` (479), `src/prose_gate.py` (347),
`src/sevenfold.py` (274), `src/autostart.py` (218), `src/snapshot.py` (175),
`src/resync_roll.py` (81).

Total lines read: 2738 (every line of every file, in full).

Mode: read-only audit. No files edited. No long-running or state-mutating scripts executed;
only `Read`, `Grep`, and light cross-file lookups (`cachekey.py`, `tiers.py`, `overnight.py`,
`generate.py`, `system_style.txt`) to verify claims about callers/collisions before writing them
up.

`prose_gate.py` is the owner-held prose gate. It was audited for correctness only. No finding
below suggests weakening, opening, or removing it; where a gap is reported it is a proposal to
make the gate's checks *stricter*, never looser.

---

## Findings

### F1 — VERIFIED / MAJOR — TOCTOU on entity-cache write path defeats the M23 collision fix
`src/read.py:627` and `src/read.py:776-780`.

`read_entity()` computes the write target once, at entry:

```python
path = cachekey.write_path(CACHE, host, name)          # line 627
```

`cachekey.write_path()` (src/cachekey.py:119-135) is the M23 anti-collision fix: it checks
whether the entity's *natural* sanitised path is already owned by a *different* entity (two
distinct names, e.g. `Tag Der Toten` / `Tag der Toten`, can fold to the same filename on a
case-insensitive filesystem) and if so routes the write to a disambiguated sibling path instead.
That check reads the current on-disk state **at the moment `write_path()` is called**.

But `read_entity()` calls `write_path()` before doing any of its (slow, model-call-bound)
evidence gathering, then uses the *same* `path` variable ~150 lines and possibly minutes/hours
later to actually write the result (lines 776-780, `tmp = path + ".tmp"` ... `silence.replace_retry(tmp, path)`)
— with no re-check.

**Failure scenario**: entity A (`Tag Der Toten`) and colliding entity B (`Tag der Toten`) are
both queued and start near-simultaneously on different worker threads. At the instant both call
`write_path()`, neither natural path exists yet, so *both* get routed to the same natural path
(`write_path` only diverts when the natural path is *already occupied by someone else* — it does
not reserve it). If B's read finishes first and writes the natural path, then A's read finishes
later and writes using its own stale `path` (still the natural path, decided before B existed),
A silently overwrites B's freshly-written, correct cache entry. This is exactly the M23 bug
(`coverage.measure()` crediting one entity's evidence to a different entity) reintroduced through
a race window instead of a static sanitiser bug — on the one write path `cachekey.py` was built
specifically to protect.

Confidence: VERIFIED by code trace across `read.py` + `cachekey.py`; the docstring at
`read.py:617-626` independently confirms this exact collision (`Tag Der Toten`/`Tag der Toten`)
is real and live in the corpus, which is what makes the race exploitable rather than theoretical.

### F2 — VERIFIED / MINOR-MODERATE — entity-cache temp file not per-writer, unlike the sibling fix
`src/read.py:777` (`tmp = path + ".tmp"`) vs. `src/read.py:602-610` (`_chunk_put`, which was
explicitly fixed to use `"%s.%d.%d.tmp" % (p, os.getpid(), threading.get_ident())` with a comment
explaining exactly why a bare `p + ".tmp"` is unsafe: two workers answering/writing the same
target open and truncate ONE shared temp file, each writing over the other mid-dump).
`read_entity()`'s own final-record write (lines 776-780) still uses the un-fixed bare
`path + ".tmp"` pattern. Combined with F1, two workers that land on the same `path` (via the
TOCTOU above, or simply two concurrent invocations of `read_entity` for the same host+entity)
race on the identical temp filename. Mitigated somewhat by `_corrupt()`'s self-healing (a
JSON-parse failure deletes and re-earns the cache rather than serving garbage), but that still
means real GPU/API spend for one or both entities is thrown away, not merely "safely retried".

### F3 — VERIFIED / MODERATE — `snapshot.verify()` only byte-compares files, not directory contents
`src/snapshot.py:109-116`.

```python
for rel in m.get("took", []):
    a = os.path.join(ROOT, sid, rel.replace("/", os.sep))
    b = os.path.join(tmp, rel.replace("/", os.sep))
    if not os.path.exists(b):
        return False, "restore omitted %s" % rel
    if os.path.isfile(a) and not filecmp.cmp(a, b, shallow=False):
        return False, "restored bytes differ for %s" % rel
return True, "%d path(s) restored and byte-identical" % n
```

When `a` is a directory (any snapshot taken via `shutil.copytree`, since `before()` explicitly
supports directories), `os.path.isfile(a)` is False, so the byte-comparison branch is skipped
entirely — only `os.path.exists(b)` (does *something* exist at the target) is checked. No file
inside the directory is ever compared. The function's own success message then claims
`"N path(s) restored and byte-identical"` for a path that was never compared byte-for-byte —
the message asserts something the code did not verify. This directly undercuts the module's
stated purpose ("PROVE IT RESTORES... An untested backup is a belief, not a backup"): for any
directory snapshot, `verify()` currently proves only "a directory with this name exists", which
is close to a check that cannot fail for content-corruption purposes. Not currently exercised by
the one live caller (`withdraw_chapters.py` snapshots a single file), so no observed real-world
miss yet — but the module is written and documented as general-purpose infrastructure for future
destructive operations, and the gap is real in the code as written.

### F4 — HYPOTHESIS / MINOR — `snapshot.before()` has no path-containment check
`src/snapshot.py:44-46, 62-67`. `_rel()` computes `os.path.relpath(src, HERE)`; if a caller ever
passes an absolute path outside `HERE` (the docstring's own signature, `before(label, paths, ...)`,
places no restriction on this), `rel` can contain `..` segments, and
`tgt = os.path.join(dest, rel.replace("/", os.sep))` can then resolve *outside*
`state/snapshots/<sid>/`. Not triggered by the current caller (`withdraw_chapters.py`, which
only passes a repo-relative path), so this is latent rather than observed.

### F5 — VERIFIED / MINOR — silent last-write-wins collision in `resync_roll.py`'s source index
`src/resync_roll.py:38-50`.

```python
by_source = {}
for fn in os.listdir(RECORDS):
    ...
    src = rec.get("source")
    if src:
        by_source[norm(src)] = (rec, fn)
```

`norm()` (line 26-27) strips every non-alphanumeric character and lowercases. If two *different*
record files declare sources that normalize to the same key (e.g. differ only in punctuation or
hyphenation), the later one in `os.listdir()`'s (filesystem-dependent, not guaranteed sorted)
iteration order silently overwrites the earlier entry in `by_source`, and the earlier source's
record file is never considered when reconciling the roll — its roll row is left un-synced with
no warning printed. Given this tool's whole purpose is fixing exactly this class of silent-drift
bug for `entry_count`, a same-shaped collision inside its own indexing step is worth closing:
detect and report (not silently overwrite) when two record files collide on `norm(source)`.

### F6 — VERIFIED / MINOR — backwards-looking default status for a newly-zeroed record
`src/resync_roll.py:63`.

```python
r["status"] = "catalogued" if n else r.get("status", "catalogued")
```

When the corrected count `n` is 0 and the roll row previously had **no** `status` key at all,
the fallback default is `"catalogued"` — i.e. a source resync just determined has zero entries
in its record file gets labelled `"catalogued"` by default. That reads as the wrong default
direction: a source with 0 entries defaulting to "catalogued" (rather than something like
"pending"/"empty") produces a self-contradicting row (`entry_count: 0, status: catalogued`) for
exactly the population this script is meant to make trustworthy.

### F7 — VERIFIED / COSMETIC — dead padding loop, comment describes an unreachable case
`src/sevenfold.py:147-149`.

```python
for m in coords:                          # pad shallow branches with slot 0
    while len(coords[m]) < depth:
        coords[m].append(0)
```

Traced `split()` (lines 131-146): for any non-empty block, `seams()` never returns duplicate cut
indices (each `i` in `gaps` is drawn from a strict `range()`, so `bounds` is strictly increasing
and every `chunk = block[lo:hi]` is non-empty), so every member's recursion always continues
through every level from 0 to `depth` inclusive before the `level >= depth` base case fires.
Every `coords[m]` therefore already has exactly `depth` entries by the time this loop runs, for
every possible input (including a single-member block, which just keeps recursing with one
element per level). The `while` condition can never be true; this is dead code whose comment
describes a scenario ("shallow branches") that the surrounding recursion structure already
precludes. Harmless (a no-op), but it is exactly the "comment says X, code cannot do X" shape
called out in the module's own house style elsewhere.

### F8 — VERIFIED / COSMETIC — self-acknowledged tautological display, not a live check
`src/sevenfold.py:241-245`. `ok = "OK" if hi <= SPAN else "OVER SPAN"` can never print "OVER
SPAN" for any input, because `seams()` already clamps every child count to `SPAN` by
construction. The code's own comment says as much ("this displays a GUARANTEE, not a discovery
... it becomes a real check only if seams() ever stops clamping"). Flagged per the audit's
"checks that cannot fail" lens for completeness — this one is self-aware and intentional, not a
mistaken invariant, so treat as informational rather than an actionable defect.

### F9 — HYPOTHESIS / MINOR — `shelve()`'s returned tier labels are only correct for prefix-depth callers
`src/sevenfold.py:99-150`, specifically `return {m: dict(zip(TIERS, c)) for m, c in coords.items()}`
(line 150). This always zips against the module-global 5-tuple `TIERS`, regardless of the
`depth` parameter actually used to build `c`. For the `WORLD_TIERS` call in `build()`
(`shelve(names, {}, depth=len(WORLD_TIERS))`, depth=2), the returned dict keys are
`"hyperverse"`/`"xenoverse"` — semantically wrong names for what are actually multiverse/universe
coordinates. `build()` (lines 206-208) knows this and manually remaps
(`worlds[d]["multiverse"] = inner[d]["hyperverse"]`), so the current two call sites produce a
correct final result, but the mislabeling is silent and undocumented in `shelve()` itself: any
future caller that uses `shelve()`'s return value directly (as the docstring's generic signature
invites) without knowing to remap would get confidently-wrong tier labels. Not a live bug against
current callers; a latent trap in a function whose docstring promises more generality than its
implementation safely provides.

### F10 — HYPOTHESIS / MINOR — silent world-drop on source-key mismatch
`src/sevenfold.py:199-202`.

```python
for src, ws in by_source.items():
    base = coords.get(src)
    if base is None:
        continue
```

If `worldseed.build_all()`'s designation prefix (`designation.split("::")[0]`) ever fails to
match a key in `coords` (built from `tiers._graph()`'s `srcs`) — e.g. due to any naming drift
between the two subsystems — that source's entire world population is dropped from the shelved
output with no count, no log, and no note. Not verified to be currently firing (would require
auditing `worldseed.py`/`tiers.py`, outside this batch), but the failure shape is exactly Hard
Rule 0's "a smaller universe wearing the same shape as the real one": a run finishing cleanly
while silently having shelved 0 worlds for some sources would look identical to a run that
finished normally.

### F11 — HYPOTHESIS / MINOR — `_HAS_ACTION` verb-list gaps could reject a chunk that holds a real feat
`src/read.py:103-110`. The regex is deliberately generous per its own comment ("cheaper to send a
doubtful chunk to the model than to silently drop a real feat"), but it is still a hand-maintained
verb list, and it is missing some plausible feat verbs (e.g. `vaporiz-`, `annihilat-`,
`pulveriz-`, `vanquish`, `eviscerat-`, `smash`). A chunk whose only feat-bearing sentence uses
none of the listed roots and none of the covered ones incidentally (via a different sentence in
the same chunk) is silently excluded before ever reaching the model — the intended fail-safe
direction the comment claims ("send doubtful chunks") only holds for chunks the regex judges
doubtful, not for chunks it flatly rejects. Partially mitigated: excluded chunks are counted in
`chunks_skipped` (visible in the output/queue diagnostics), so this is not a *silent* loss in the
sense of going unlogged, but it is an undercount of *why* they were skipped (mention-mismatch and
missing-action-verb are lumped into one counter) and a real, if narrow, recall gap in a module
whose header explicitly frames recall as the entire point of the reader.

### F12 — HYPOTHESIS / MINOR — `chunks_skipped` arithmetic is an approximation that can be wrong by more than the `max(0, ...)` floor suggests
`src/read.py:689, 758`. `skipped = sum(len(b) for b in text.values()) // size - len(chunks)`
computes total-corpus-chars // size as an estimate of "how many chunks exist in total", then
subtracts the actually-included count. Because chunking happens per-title
(`for i in range(0, len(body), size)`), a page whose length is not an exact multiple of `size`
contributes one extra partial chunk that the combined-length division does not account for; with
multiple titles this undercounts the true total chunk count, and the diagnostic can read low
(already anticipated by the code, given the `max(0, skipped)` clamp at line 758, but the clamp
only prevents a negative number — it does not fix the undercount that produces it). Cosmetic:
affects only a reported diagnostic count, not what is actually read or written.

### F13 — HYPOTHESIS / MINOR — `_save_qcache` writes a non-unique temp filename
`src/read.py:894-902` (`tmp = QCACHE + ".tmp"`), the same class of hazard `_chunk_put` (line 602)
and `gpu_lane._write_claim`/`_touch` were explicitly hardened against elsewhere in this batch
(unique-per-writer temp names). `queue()` — the only caller — currently runs once per `run()`
invocation, single-threaded, before the worker pool starts, so no live race is confirmed; but if
`read.py --run` were ever launched twice concurrently (no lock/singleton check inside `read.py`
itself; `overnight.py` invokes it once per cycle via its own `running()` guard, but that
guard lives in the caller, not in this module), two processes' `queue()` calls would race on the
identical temp filename while writing `state/read_queue_index.json`.

### F14 — HYPOTHESIS / MINOR — TOCTOU in `autostart._twin_watchdog()`
`src/autostart.py:121-145`. The single-watchdog guarantee this function exists to provide (per
its own docstring: three watchdog copies once looped, restarting supervisors and fighting each
other) is enforced by a one-shot process-list snapshot taken at startup, with no claim/lock file
comparable to `gpu_lane`'s lease mechanism elsewhere in this codebase. Two `--watch` processes
that start within the query's latency window of each other (e.g. the Startup `.vbs` firing at
login at the same moment as a manually-run watchdog) can each see no twin and both proceed. Given
the module exists specifically because this exact failure happened once already, the fix (a
one-time WMI query) does not fully close the class of bug it names in its own history.

### F15 — COSMETIC — unused variable, possible drift risk
`src/autostart.py:31` (`_NO_WIN = getattr(subprocess, "CREATE_NO_WINDOW", 0)`) is computed but
never referenced; both actual subprocess call sites (`start_supervisor` line 115,
`_twin_watchdog` line 130) independently re-derive the same flag inline instead. Not a bug today,
but dead state in a file whose entire job is guaranteeing no console window ever appears — worth
consolidating so a future subprocess call site can't be added without the flag by mistake.

### F16 — HYPOTHESIS / COSMETIC — `gpu_lane._write_claim`'s temp file is not per-thread
`src/gpu_lane.py:242-256`. Unlike `_touch` (line 307, explicitly made per-pid) and unlike
`_chunk_put` in `read.py`, `_write_claim` uses a bare `path + ".tmp"`. Since `_claim_path()` is
itself namespaced by PID (`fg.<pid>.json`), this is safe across processes; it is only unsafe if
two threads of the *same* process call `foreground()`/`lane(priority=True)` concurrently, which
would also race the in-memory depth-refcount read-modify-write (`rec = _read(path) or {};
depth = int(rec.get("depth") or 0) + 1`) with no thread lock. Checked all current callers
(`generate.py`, `pipeline.py`, `local_agent.py`); none currently invoke `lane(priority=True)`
from more than one thread of the same process, so this is not observed live, only latent.

### F17 — HYPOTHESIS / MINOR — narrow regex gap in the prose-gate's anti-fabrication layer 4b
`src/prose_gate.py:284-286` (`_AXIS_RE`). The pattern requires the axis label to be followed
(after only whitespace/markdown-decoration characters `[\s*_]*`) directly by a colon:
`(Strength|...)[\s*_]*:[\s*_]*(\d+)`. Any inserted text between the axis name and its colon (a
parenthetical qualifier, a footnote marker, a numbered-list prefix like `"1. Wisdom: 28"` where
the leading-decoration class `[\s*_#>-]*` does not include digits/periods) would not match, so
`unearned_instrument()` would fail to flag a numeric score in that line as unearned even when the
entity has zero cited feats — the exact fabrication this layer exists to catch. The house style
guide (`prompts/system_style.txt`) specifies the plain `"Strength: 30 (...)"` format the regex
already handles correctly, so this is not confirmed to occur against real model output — flagged
as a coverage gap worth hardening (broadening the check), not a demonstrated bypass.

---

## Summary by severity

- Major: 1 (F1)
- Moderate: 2 (F2, F3)
- Minor: 9 (F4, F5, F6, F9, F10, F11, F13, F14, F17)
- Cosmetic: 4 (F7, F8, F12, F15, F16 — F16 is cosmetic/latent, listed above)

No Hard Rule 0 (caps/truncation) violations found in these seven modules. `cap_chunks` in
`read.py` is an explicit, opt-in, off-by-default CLI parameter (`--chunks`, help text: "omit to
read every chunk of every page") — documented, uncapped by default, not a hidden truncation.
`THIN_CHARS`/`WEAVE` in `read.py`'s `priority()` only affect ordering, never membership (verified
against the module's own 2026-08-24 fix commentary for the prior version of that exact bug).

No violations of the two-writer contract found: every shared JSON write inspected in this batch
goes through `silence.replace_retry` or `silence.write_json`, except `snapshot.py`'s manifest
write (F-adjacent to F3/F4, noted inline) which writes directly but is wrapped in a `try/except`
that surfaces failure as `SnapshotFailed` rather than swallowing it.

`prose_gate.py` layers 1-4 were traced in full; `gate_open`/`step4_gate_open` use strict `is not
True` checks (immune to the `bool("false")`-style defect the file's own header describes as the
2026-08-25 incident's root cause), fail closed on unreadable/missing config and on unmeasured
sources, and the block/section/body-length checks correctly compensate for undercounted `◈`
blocks via the `ghosts` term even under a hypothetical marker-format edge case. One gap found
(F17) is a proposal to broaden — never loosen — the anti-fabrication regex.
