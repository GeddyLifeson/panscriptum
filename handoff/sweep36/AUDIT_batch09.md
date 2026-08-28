# AUDIT batch09 — run #36

Modules (9): `src/read.py`, `src/corpus_db.py`, `src/gpu_lane.py`, `src/address_space.py`,
`src/ingest_doc.py`, `src/canon_backup.py`, `src/catalogue_aurora.py`, `src/cachekey.py`,
`src/compress_store.py` (3,793 lines total, matches the assignment).

Read-only audit. No edits made. Method: full read of every file in the batch (not excerpts),
cross-file tracing of call sites for the two flagged focus areas (`canon_backup.py`'s
verification/prune/restore paths, and `catalogue_aurora.py`'s dedup-key fix), and targeted
`grep` across `src/` to check claims about callers before reporting anything as dead, unused,
or currently-exploitable versus latent.

## Findings

### 1. MAJOR — `canon_backup.py`: the manifest write's verdict is discarded, contradicting the
zip write three lines above it

`snapshot()` checks the zip's landing verdict and raises on failure:

```python
if silence.replace_retry(tmp, final) is False:
    raise RuntimeError("snapshot could not be renamed into place: %s" % final)
```

but the manifest write right after it does not:

```python
silence.replace_retry(*_write_manifest(final, manifest))
```

(line ~149). `replace_retry` never raises — it returns `True`/`False` and silently retries on
`PermissionError` (per its own docstring in `silence.py:331-348`, "persistent denial is
recorded, never raised"). If the manifest's replace is denied (a reader has
`canon-<stamp>.manifest.json` open — plausible, since nothing else in the tree treats this file
as exclusive), `snapshot()` still returns `(final, manifest)` normally and the caller
(`main()`'s `--snapshot` branch) prints "snapshot: N files, ... verified" and exits 0. The zip
itself did land and IS verified — but its manifest, which is what `verify()` reads to compare
against the live tree (`recorded = json.load(man)...get("digests")`), silently did not. A
`verify()` call afterward would see no manifest file, fall back to `recorded = {}`, and report
every canonical file as "new since the snapshot" rather than comparing digests at all — a
degraded verification that never says the manifest write failed. This is exactly the
"discarded verdict" shape (audit catalogue item 5): the project's own convention two lines
above shows the correct way to handle this return value, and the manifest write does not follow
it. Fix: check the return value the same way the zip's replace is checked, and raise or at
least `silence.note` + surface it in the printed summary.

### 2. MAJOR — `canon_backup.py`: `members()` can silently back up a subset and still report
`"verified": True`

Guidance for this file specifically asked whether `members()` can under-collect. It can, in two
ways, and neither is guarded beyond the all-empty case:

- **A named file goes missing.** `CANON_FILES` entries are only added `if os.path.isfile(p)`
  (line 89). If `data/WIKI_HOSTS.json` or `data/CHARTER_SPINE_CODES.json` — both explicitly
  called out in the module's own docstring as hand-authored and irreplaceable — is deleted or
  transiently absent, `members()` just omits it. No `silence.note`, no warning; contrast with
  `digest()` two functions above, which *does* call `silence.note` when a file exists but can't
  be read. `snapshot()`'s only sanity check is `if not items: raise` (line 110) — that only
  fires if *every* canonical file is gone, not if one of three is.
- **The whole records directory goes missing.** `CANON_DIRS` entries are skipped entirely if
  `not os.path.isdir(d)` (line 93) — again silently, again with no note. If `data/records/`
  were transiently unavailable (a mount hiccup, a race with whatever process manages it, a bad
  `HERE` resolution), `members()` returns only the 2-3 small top-level files. Since that set is
  non-empty, the `if not items: raise` guard does **not** fire, and `snapshot()` proceeds to
  write, verify, and report success on a "backup" that omits all 217 corpus sources — the exact
  scenario named in the assignment brief: "a backup of a subset verifies perfectly." The
  verification loop (lines 126-141) is real and would catch a *corrupted* write, but it can only
  ever verify what `members()` handed it; it has no way to know 217 files are missing from the
  input.

Neither of these needs an attacker — a transient filesystem hiccup or an accidental delete
during the exact second `snapshot()` runs is enough, and the daily cadence (`KEEP = 7`, ~8 days
of history) means a bad snapshot could roll all the way through the retention window before
anyone notices, if nobody happens to run `--verify` in between. Suggested fix: have `members()`
(or `snapshot()`) compare the collected count against the *previous* manifest's `files` count
and refuse (or at minimum loudly warn) on a large unexplained drop, the same way `prune()`
already refuses to guess at ordering by trusting only the stamp.

### 3. MINOR/question — `canon_backup.py`: concurrent invocations share a `.tmp` name at
second resolution

`tmp = os.path.join(ROOT, "_writing-%s.zip" % stamp)` (line 119) where `stamp` defaults to
`time.strftime("%Y%m%d-%H%M%S")` — second resolution, no PID/thread disambiguation, unlike
every other write site touched by today's other edits in this same batch (`corpus_db.py`'s
`rebuild()`, `compress_store.py`'s `store()`, `read.py`'s `_chunk_put()` all now carry
PID+thread in their temp names specifically because of this exact hazard — see their own
comments). Two `canon_backup.py --snapshot` invocations started within the same second (a
manual run overlapping a scheduled one, say) would both compute the same `stamp`, both target
`_writing-<stamp>.zip`, and race on the write. There's no lock file preventing concurrent
snapshot runs. Flagging as a question rather than a confirmed defect because it requires
same-second concurrent invocation, which may never actually happen given how this is scheduled
— but it's the same shape audit item 4 calls out by name, in a module whose whole reason to
exist is being the last line of defence, so the cost of getting it wrong once is out of
proportion to the cost of a PID+thread suffix.

### 4. Verified correct — `canon_backup.py`: `prune()` cannot delete the newest snapshot

Checked specifically per the assignment brief. `prune()` sorts snapshot filenames (the
timestamp *string*, not mtime — correctly, per its own comment) ascending and removes
`snaps[:-keep]`. Traced the slicing for `keep<=0` (explicitly disabled via `if keep>0 else []`,
so `--keep 0` disables pruning rather than deleting everything — mildly surprising but safe),
`keep >= len(snaps)` (Python slicing correctly yields `[]`), and `keep == len(snaps)` exactly
(also correctly yields `[]`). No path found that removes the newest snapshot. Sound.

### 5. Verified correct — `canon_backup.py`: `restore()` cannot write outside its intended
location under normal use

`dest` defaults to `os.path.join(ROOT, "restored", os.path.basename(rel))` — confined by
`os.path.basename`, safe. A caller-supplied `dest` is not validated for traversal, but this is
an explicit owner-invoked CLI override (`--restore REL`, with `dest` only reachable as a
function argument, not exposed on the CLI at all — `main()`'s `--restore` branch never passes
`dest`), not something fed from untrusted external data, so not flagging as a defect — noting
it as a question in case a future caller wires `dest` to something less trusted.

### 6. MAJOR — `read.py`: an unreadable host map silently empties the ENTIRE read queue,
contradicting the comment three lines above it that says it must not

`queue()` (line 944) loads the host map with a documented self-healing guard:

```python
try:
    with open(FF.HOSTS, encoding="utf-8") as _hf:
        hosts = json.load(_hf)
except Exception:
    silence.note("read.py:hosts-unreadable")
    hosts = {}
```

The comment directly above this (lines 957-960) states the intent explicitly: *"An unreadable
host map is a real fault, so it is recorded rather than shrugged off -- but it must not be able
to discard the pass."* But every row built afterward is gated on the host map:

```python
for _, r in recs:
    h = hosts.get(r["source"])
    if not h:
        continue
```

When `hosts == {}` (the exception path), `h` is `None` for every single record, so `if not h:
continue` fires unconditionally and `rows` ends up empty. `priority([])` returns `[]`, `run()`
prints "0 entries with pages, N workers" and exits cleanly having done nothing — no exception,
no failed exit code, nothing structurally different from a legitimately-empty queue. This
directly contradicts the comment's own stated invariant: the pass *is* discarded, just without
crashing. Given the docstring's own note that the host map "has three writers" and a race is
exactly why this try/except exists, and given the batch's own framing that read.py is "the
library's main throughput and has been stalled," a transient read failure at the exact moment
`queue()` runs (plausible in a multi-hour, multi-process pipeline) is a real, if
race-triggered, way for an entire overnight `--run` invocation to complete "successfully" while
reading nothing. Fix direction: either retry the host-map read a few times before giving up, or
have `queue()` refuse to proceed (raise, or return a sentinel distinct from "genuinely empty
queue") when the map came back empty via the exception path specifically, rather than silently
treating "map unreadable" and "map legitimately empty" as the same case downstream.

### 7. MAJOR (cross-file, with `cachekey.py`) — `read_entity()`'s write path is decided once at
entry and reused, unvalidated, after the entire mining run — a TOCTOU race matching the exact
case-collision pair the module's own comments cite as real

`read_entity()` computes its write target once, at the top:

```python
path = cachekey.write_path(CACHE, host, name)   # line 665
```

`cachekey.write_path()` (in `src/cachekey.py`) is a check-then-decide function: if the natural
path doesn't exist yet, or exists and already belongs to *this* entity, it returns the natural
path; only if the natural path exists and belongs to someone *else* does it redirect to a
disambiguated, hash-suffixed sibling. That decision is correct *at the moment it runs*. But
`read_entity()` then does the actual model-driven mining — which the module's own comments
document as running for many minutes per entity for a "deep" own-page subject (line 822's
`DEEP_CHARS` threshold, "tens of model calls") — and only writes to the *already-decided*
`path` at the very end (line 817):

```python
if not silence.write_json(path, out, indent=1, ensure_ascii=False):
    silence.note("read.py:read-entity-write-denied")
```

`path` is never re-derived or re-validated against the current state of disk before this write.
`read.py` runs a `ThreadPoolExecutor` with multiple workers processing many *different*
entities concurrently (`run()`, line 1156). If two entities whose sanitised stems collide only
by case are both mid-flight at once — and this is not hypothetical: `read_entity()`'s own
comment block (lines 658-664) names this exact scenario as a real, previously-found production
collision ("`Tag Der Toten`... and `Tag der Toten`... two distinct catalogued entities on one
host, and NTFS folds their sanitised filenames together") — both workers can call
`cachekey.write_path()` early, at a moment when *neither* file exists yet, and both correctly
receive the *natural* path (not knowing about each other). Minutes later, both finish mining
and both call `silence.write_json` against their own copy of `path` — two Python strings that
differ only in case, which NTFS treats as the same underlying file. Whichever write lands last
silently overwrites the other's cache file. `cachekey.owns()`'s exact-name check protects
*readers* — a later `load()` of the clobbered entity correctly sees a content mismatch and
re-mines rather than serving wrong data — so this is not a wrong-answer bug, but it is a
real, silent cache-eviction: the earlier entity's freshly-mined evidence for that pass is
discarded on disk (though the in-memory `out` already returned to `run()`'s counters for
*that* invocation is unaffected), and the loss is invisible until a *later* run re-mines that
entity from scratch, wasting a full mining pass on it. This is the same shape as audit item 4
("read-modify-write without compare-and-swap") — the "read" (does this path belong to someone
else) and the "write" happen minutes apart with no re-check, and `cachekey.write_path()`'s
contract doesn't document that it must be called immediately before the write it authorizes,
not once at the top of a long-running function. Suggested fix: re-derive (or at least
re-verify ownership of) `path` immediately before the final `silence.write_json` call, not once
at entry.

### 8. MINOR — `corpus_db.py`: `evidence_truncated` is a guard that can never fire —
dead code left behind by today's earlier fix

`evidence_truncated = False` is set once (line 211) and never reassigned anywhere in
`rebuild()`. This matches the comment directly above it explaining that `evidence_limit` "no
longer truncates" (fixed today, per run36 batch05's own citation in the comment) — so the flag
being permanently `False` is *consistent* with the current behaviour, not misleading about the
data. But the machinery built around it is now unreachable: `main()`'s `--rebuild` branch still
carries a full `if got["evidence_truncated"]:` block (lines 558-563) printing a WARNING about a
"TRUNCATED file list" that can never print, and the `meta` table still records
`evidence_truncated` on every rebuild, always `"0"`. This is the exact shape of audit item 1 (a
check that cannot fail) — harmless in its current form since it fails toward "never warns"
rather than "falsely claims all-clear" on something that still happens, but it's dead
scaffolding for a failure mode that no longer exists in the code, and a future edit that
reintroduces any real truncation path would silently inherit a flag nobody is setting. Worth
either removing the whole `evidence_truncated` plumbing or leaving one comment at the
declaration site making clear it is deliberately inert (the way `corpus_db.py`'s own
`evidence_limit` handling already does one paragraph above it, at lines 215-223).

### 9. Verified correct — `corpus_db.py`: no `LIMIT` survives in `CANNED`, concurrency and
verdict-handling in `rebuild()` are sound

Checked all nine `CANNED` queries by hand against the module's own header comment claiming they
were all de-capped this run — confirmed none carry a `LIMIT` clause. `rebuild()`'s temp name
carries PID+thread (line 125) and its own pre-delete only ever touches that PID's leftovers.
The final `replace_retry` verdict is checked and propagated (`got["landed"]`, checked by
`main()` at line 550) rather than discarded. `age_seconds()` closes its connection on the
failing path too (the `finally` block, with its own comment explaining why that matters on
Windows). No caps found on the `unreadable_records`/`unreadable_evidence` name lists printed in
`main()`. Nothing found wrong here beyond finding 8 above.

### 10. MINOR/latent — `gpu_lane.py`: `foreground()`'s refcount is a read-modify-write on a
per-process (not per-thread) file, unsafe under concurrent threads, but its only current caller
is single-threaded

`foreground()` (line 220) implements re-entrancy by reading a shared file keyed only by PID
(`_claim_path()` = `fg.{pid}.json`), incrementing a `depth` field, and writing it back — with no
lock:

```python
rec = _read(path) or {}
depth = int(rec.get("depth") or 0) + 1
_write_claim(path, depth, label)
```

If two *threads* in the same process both call `lane(priority=True)` concurrently, both can
read `depth=0` before either writes, both compute `depth=1`, and the classic lost-update race
follows — worse, when the first thread to *finish* reads `cur.get("depth")` back (now `1`,
written by whichever thread wrote last) and decrements to `0`, it removes the claim file while
the second thread's `foreground()` context is still logically open, silently ending the
foreground claim early and letting background work proceed against `foreground_active()`
reporting "false" while priority work is still in flight — undermining rule 2 of the module's
own header. This is the RMW-race shape from audit item 4, and the module's own docstring for
`foreground()` addresses *nesting* (same thread, re-entrant calls) explicitly but not
*parallel* calls from sibling threads of the same process.

Checked before reporting: `grep -rn "priority=True"` across `src/` shows exactly one caller,
`generate.py:156`, and `generate.py` has no `ThreadPoolExecutor` or `threading.Thread` anywhere
in it (confirmed by grep) — it is a sequential, single-threaded script. So this race is not
currently reachable; flagging as latent rather than active, but the primitive itself is unsafe
and would silently misbehave the moment a second `priority=True` caller is added, or if
`generate.py` is ever parallelised the way `read.py` and other batch jobs in this tree already
are.

### 11. Verified correct — `gpu_lane.py`: `_alive()`, lease expiry, and the non-priority
`lane()` path

Traced `_alive()`'s Windows `OpenProcess` branch against its own docstring's claims (unparseable
pid -> alive, `ERROR_INVALID_PARAMETER` -> dead, `ERROR_ACCESS_DENIED` -> alive, anything
unknown -> alive) — matches. `_touch()`'s never-resurrects guard (checks `rec.get("pid") ==
os.getpid()` before writing) is sound. The non-priority `lane()` path used concurrently by
`read.py`'s worker pool (via `pipeline.py:403`) uses `O_CREAT|O_EXCL` for slot acquisition,
which is atomic and race-free — no RMW there, unlike the `foreground()` path above.

### 12. MINOR/question — `address_space.py`: `assign()`'s hash-slice offsets for
galaxy/star/planet are hardcoded literals, not derived from `WIDTHS`, in a module whose entire
stated design philosophy is that nothing here should be a hand-picked number that can drift

The module's docstring is emphatic and repeated: "THE WIDTHS ARE DERIVED, NOT CHOSEN," "Change
the census and the widths change with it. Nothing here is a round number picked because it
looked tidy," and the whole `main()`-table refactor earlier in the file exists specifically to
stop hand-transcribed numbers from going stale. But `assign()` (line 272) draws its
galaxy/star/planet sub-values from one 128-bit hash using **fixed** shift offsets:

```python
n % (1 << WIDTHS["universe"])          # bits 0..~5
(n >> 8)  % (1 << WIDTHS["galaxy"])     # bits 8..~45
(n >> 48) % (1 << WIDTHS["star"])       # bits 48..~74
(n >> 78) % (1 << WIDTHS["planet"])     # bit 78
```

`8`, `48`, and `78` are literals, not computed from the actual field widths the way `pack()`
and `unpack()` two functions above correctly do (`out = (out << w) | v`, fully width-driven). At
today's populations this is safe with a few bits of headroom between fields (galaxy currently
needs ~38 bits starting at 8, ending at ~46, two clear of star's 48; star currently needs ~27
bits starting at 48, ending at ~75, three clear of planet's 78). But the module's own header
explicitly anticipates the census growing ("moves whenever TIERS.json is re-charted") — if
`C.STARS_PER_GALAXY_MEAN` grows enough to push the star field past ~30 bits, its high bits would
start overlapping the same hash bits `(n >> 78)` reads for `planet`, silently correlating two
supposedly-independent address sub-fields (not a crash — `pack()`'s own range validation still
holds since each field's *value* is still correctly masked via its own `% (1 << W)` — just a
quiet loss of the intended hash independence). Flagging as a question rather than a hard defect
since it is currently safe and the failure mode is a statistical-quality regression, not data
loss or a crash, but it is exactly the "hand-picked number that can drift" pattern this module
otherwise goes out of its way to eliminate everywhere else in the file.

### 13. Verified correct — `address_space.py`: `pack()`/`unpack()` round-trip, `main()`'s
by-name table and keyword-only demo call

Traced the bit layout by hand: `pack()` shifts fields in `FIELDS` order (hyperverse first, most
significant), `unpack()` walks `reversed(FIELDS)` (planet first, extracting from the
least-significant end) — consistent, and independently confirmed by the module's own
`assert unpack(a) == fields` in `main()`'s round-trip demo, which exercises all eight fields by
keyword. The `main()` table's `srcs` dict is correctly keyed by field name (not the old
positional `zip` the file's own comments say used to silently mispair citations) — every
`FIELDS` entry has a citation, no field silently falls through to the `'?'` default.

### 14. MINOR/question — `address_space.py`: the console preview of addressed worlds is capped
to 6, but the persisted data is not

`main()`'s demo section prints `for d, a in list(addrs.items())[:6]:` (line 378) — a display-only
slice. The full, uncapped `addrs` dict is what gets written to `SHELFMARKS.json` via
`silence.write_json` two lines later, so this is not a Hard Rule 0 violation in the data that
persists — flagging only because the shape (`[:6]` on an enumerated list, in a project this
sensitive about that exact pattern) is worth a second pair of eyes confirming it really is
display-only, which it is.

### 15. MAJOR/question — `ingest_doc.py`: `mine()`'s chunking can silently exceed `CHUNK`,
with no re-split safety net the way `read.py`'s local fallback has for the identical hazard

`mine()`'s chunk builder (lines 167-175) only flushes the current chunk *before* adding a page
if doing so would exceed `CHUNK` **and** the current chunk is already non-empty:

```python
if cur and len(cur) + len(pages[label]) > CHUNK:
    chunks.append((cur, list(cur_pages)))
    cur, cur_pages = "", []
cur += "[" + label + "]\n" + pages[label] + "\n\n"
```

If a single page's cleaned text alone is larger than `CHUNK` (9000 chars), there is no
protection: `cur` is empty at that point, so the check is skipped, and that oversized page
becomes (or is folded into) a chunk larger than `CHUNK` on its own. This module's sibling,
`read.py`, spends a long comment block (lines 58-73, 433-452) establishing that Ollama silently
truncates an overlong prompt rather than refusing it, and specifically builds `_local_carded()`
to re-split any prompt over `CHUNK + 2000` chars into pieces before sending it, exactly to avoid
this. `ingest_doc.py`'s `_ask()` (line 132) has no equivalent — it sends whatever `mine()` hands
it straight to `CB.ask()` or `P.ask()` with no size check or re-split. A dense sourcebook page
(small font, dual-column, a table-heavy appendix) plausibly exceeds 9000 characters of cleaned
text on its own. Flagging as a question rather than a certainty because I have not measured
whether any page in the owner's actual PDFs currently crosses that threshold, but the failure
mode if one does is the same one `read.py` treats as serious enough to rebuild its transport
layer around: a silently truncated passage, fewer entities extracted than the text actually
contains, and no signal that anything was cut.

### 16. MINOR — `ingest_doc.py`: `mine()`'s misses/retry loop, resumable-cursor discipline, and
write-verdict gating are sound

Traced the `misses >= 60` bound (60 x 300s naps = ~5h ceiling, matches its own comment) — this
terminates, does not hang forever. The resume cursor (`state["next"]`) is only advanced *after*
`P.write_record_catalogue()`'s verdict is checked (lines 249-254), with `known` correctly
rewound on a denied write so a retry doesn't skip re-offering those names — matches the "advance
on the write, not the intent" discipline the comments describe, and I found no place where this
discipline is dropped elsewhere in the file. `description` values are truncated to 2000 chars
per entity (line 219) — noting only as a question, since Hard Rule 0 is stated in terms of
rosters/entry lists, not the character length of one field within a kept entry; this doesn't
drop any entity from the extraction.

### 17. Verified correct (per the batch's specific ask) — `catalogue_aurora.py`: the dedup-key
fix is coherent, and I found no recurrence of the same shape elsewhere in the file

The described fix — widening the dedup key from `(type, normalised_name)` to
`(type, normalised_name, description)` (line 104) — is exactly what the docstring above
`parse_folder()` claims, and it is the correct fix for the stated failure (same-named
XML `<element>`s across different homebrew files with genuinely different rules text,
previously collapsed on name alone). Checked the surrounding logic: `dropped` is only appended
to on an actual key collision, and the count is surfaced in `main()`'s printed summary rather
than silently absorbed. Checked the rest of the file for the same "narrow key drops distinct
content" shape — `main()`'s `written` list, roll-write, and per-record write are all gated on
their actual landing verdict (`_P.write_record_catalogue`, `silence.write_json`), consistent
with the run #25/#33 fixes cited in the comments; no other collapsing/keying logic in the file
besides the one `parse_folder()` fixed today.

### 18. MINOR/question — `catalogue_aurora.py`: `slug()` truncates to 60 characters; the
project's other `slug()` (in `ingest_doc.py`, same batch) does not

`catalogue_aurora.slug()` (line 60): `re.sub(...).strip("-")[:60]`. `ingest_doc.slug()` (line
77, same batch, same conceptual purpose — turning a source name into a filesystem-safe
identifier): `re.sub(...).strip("-")` with **no** length cap. Two independent implementations
of "make this source name a safe file/dict key," one of which silently truncates. For
`catalogue_aurora.py`'s own current ten `FOLDER_SOURCE` entries this is nowhere near 60 chars
and causes no collision today, but a 60-char truncation on a filename-generating slug is exactly
the shape `cachekey.py`'s whole module (`M23`, elsewhere in this same batch) exists to fix for
entity names — two different source names sharing a 60-char prefix would silently collide on
the same record file (`os.path.join(RECORDS, slug(source_name) + ".json")`, line 186), with the
second write overwriting the first's record entirely (unlike `cachekey.py`'s collision-aware
`write_path()`, `catalogue_aurora.py`'s direct record path has no ownership check before
writing). Flagging as a question given current inputs are safe, but noting the inconsistency
between the two `slug()`s as worth reconciling, especially since one of them (`cachekey.py`)
already demonstrates the house pattern for handling exactly this hazard.

### 19. MAJOR — `compress_store.py`: stale `silence.note()` line-number tag, off by the exact
shape audit item 6 names

```python
try:
    import zstandard as zstd
    _HAVE_ZSTD = True
except ImportError:
    silence.note("compress_store.py:14")
    _HAVE_ZSTD = False
```

The `silence.note()` call is on line 16 (the `except ImportError:` handler), but it tags itself
`"compress_store.py:14"` — line 14 is `_HAVE_ZSTD = True`, the **success** path, not the
exception handler the note is actually recording. This is exactly the class of defect audit
item 6 names by name: a `silence.note("module.py:NNN")` tag that no longer matches its own
line. Low-stakes on its own (the tag is only ever used as a free-text label in `health.record`,
per `silence.py`'s own docstring — nothing parses it back into a line number
programmatically as far as this batch's files show), but it is a live, quotable instance of the
project's own named recurring defect, in a file this same run's guidance says was edited
earlier today.

### 20. Verified correct — `compress_store.py`: the write-verdict handling and temp-name
discipline the module's own comments describe

`store()`'s temp filename carries PID+thread (line 53), and a denied `replace_retry` now raises
`RuntimeError` rather than returning the old "reported stored either way" dict the comment
describes as the prior bug — checked the raise happens before the return, and the function has
no path back to a success return once `landed` is `False`. `load()` correctly gates
zstd-decompression on `_HAVE_ZSTD` and raises rather than guessing on an unknown codec string.
Nothing else found wrong in this 90-line file beyond finding 19.

### 21. Verified correct — `cachekey.py`: the collision-fix mechanism itself (natural path,
disambiguated suffix, content-verified reads)

Traced `load()`/`write_path()`/`owns()` by hand against three scenarios: (a) the documented
80-char-stem-fold collision, (b) an NTFS case-only collision (the same "Tag Der Toten" /
"Tag der Toten" pair `read.py` cites) — confirmed `owns()`'s exact-string `entity` comparison
against file *content* (never trusting the path alone) correctly detects a mismatch in both
cases and forces a re-mine rather than serving another entity's data, and (c) three-or-more
entities colliding on one natural stem — confirmed each gets its own uniquely-suffixed
disambiguated path since `_suffix()` hashes each entity's own exact name, so siblings cannot
collide with each other on the fallback path either. No defect found in the module's own logic
in isolation; the real exposure is the caller-side timing issue in `read.py`, reported as
finding 7 above (cross-filed here since `cachekey.write_path()`'s contract is the other half of
that story — its guarantee is only as good as how promptly the caller writes after calling it,
and that isn't documented anywhere in this file).

## Modules I could NOT read

None — all nine modules in the assignment were read in full.
