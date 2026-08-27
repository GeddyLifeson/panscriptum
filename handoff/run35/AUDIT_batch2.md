# Run35 batch 2 audit (agent scope: src/silence.py, src/codewatch.py, src/catalogue_aurora.py, src/sevenfold.py, src/scope.py, src/weave.py, src/reference.py)

## 1018d49b186e -- write_json's verdict discarded in catalogue_aurora.py, scope.py, sevenfold.py

Confirmed at all three sites: `catalogue_aurora.py:172` (`silence.write_json(ROLL, roll, ...)`),
`scope.py:119` (`silence.write_json(OUT, out, ...)`), and `sevenfold.py:267`
(`silence.write_json(p, {...}, ...)`) each called `write_json` as a bare statement and then
printed an unconditional success line ("Wrote N records...", "N/M wikis scoped -> SCOPE.json",
"wrote {p}") regardless of whether the atomic replace actually landed -- the exact defect
`catalogue_aurora.py`'s own preceding 20 lines exist to argue against for the per-record write,
just not for the roll write beside it. Fixed all three: `catalogue_aurora.main()` now captures
`roll_landed = silence.write_json(...)` and prints a WRITE DENIED line instead of the success
banner when it's False; `scope.build()` now returns `(out, ok)` (its one caller, `main()`, is in
this same file, so the signature change is contained) and gates the "N/M wikis scoped" line on
`ok`; `sevenfold.main()` captures `landed = silence.write_json(...)` and only prints `wrote {p}`
when `landed`. Verified `pyflakes` and a bare `import` clean on all three files.

## 4ec15db6540b -- stale numeric silence.note tags in weave.py and reference.py

Confirmed both exactly as reported: `weave.py:190` was tagged `"weave.py:187"`, and line 187 is
`    try:`, three lines above the import that actually fails -- not the call site. `reference.py:241`
was tagged `"reference.py:232"`, and line 232 is `def shelfmark(rec):` itself. Converted both to
content labels matching `wiki_source.py`'s already-converted sites (e.g. `"wiki_source-hosts-read"`):
`silence.note("weave.py:statblock-import")` and `silence.note("reference.py:shelfmark-navtree")`.
`pyflakes` and import clean on both files.

## af1d0b1524e6 -- silence.py instrument()'s classification rule disagreed with _handlers()/audit()

Confirmed live before fixing: `instrument()`'s site-detection tested `ast.dump(node)` (the WHOLE
handler -- exception type and bound name included) against a token tuple that omitted `"silence"`,
unlike `_handlers()`, which tests only `"".join(ast.dump(stmt) for stmt in node.body)` and does
include `"silence"`. Built a synthetic handler carrying this project's documented exemption marker
(`_ = "silence-exempt: ..."`, the pattern used 50+ times across chain.py, completeness.py,
coverage.py, dashboard.py, gpu_lane.py, runguard.py, sweep.py and others) and ran both
classifiers against it directly: `_handlers()`/`audit()` correctly call it observed (the
`"silence"` in `"silence-exempt"` matches); the old `instrument()` logic did not, because
`"silence"` was never in the tuple it checked. `instrument()` would have rewritten every one of
those 50 handlers, inserting a redundant `silence.note(...)` call into code the project has
explicitly marked as deliberately, permanently silent. Fixed `instrument()` to mirror
`_handlers()` exactly: body-only `ast.dump`, `"silence"` added to the token tuple (kept `"note"`
too, so an already-instrumented handler still short-circuits on a second `--instrument` pass),
and the same `uses_exc` bound-name check `_handlers()` uses. Re-ran the synthetic case post-fix
via the real `silence.instrument(dry=True)` against a scratch file with one exempt handler and one
genuinely silent one: found exactly the silent one. `pyflakes` and import clean.

## d99b11ec050e -- codewatch.py's _record_restart() races on the shared ledger

Confirmed the read-modify-write is unserialised: `_record_restart` opens `state/CODEWATCH.json`,
mutates only its own key, and writes the whole doc back via `silence.write_json` (atomic on its
own, but that doesn't make the READ-then-write atomic across processes). `foreman`, `overwatch`
and `publish` each call `exit_if_stale()` independently, and the ordinary case -- one `src/` edit
-- goes stale for all three at once, landing multiple processes in `_record_restart` within the
same second. Reproduced the loss directly: three threads each calling the pre-fix
`_record_restart` 20 times against a scratch ledger dropped entries under the write-write race.
Grepped the whole tree for any existing lock primitive (`flock`, `msvcrt`, `LockFile`) --
none exists; `silence.py` has none either, and its public API is off-limits for anything beyond
order af1d0b1524e6, so the fix lives entirely in `codewatch.py`. Added `_ledger_lock()`, a
per-process mutex using the same `O_CREAT|O_EXCL` primitive `gpu_lane._take_slot()` already uses
for its lease files (atomic create-or-fail on Windows and POSIX alike), with stale-lock theft
after `LOCK_STALE_SECONDS = 30` and fail-open (proceed unlocked) after 50 failed attempts,
matching `gpu_lane`'s own "cannot arbitrate -- caller proceeds unmetered" philosophy rather than
ever hanging a daemon on a stuck lock file. Wrapped `_record_restart`'s whole read-modify-write in
it. Re-ran the identical three-thread x 20-call reproduction post-fix: all 60 restarts landed
(`foreman: 20, overwatch: 20, publish: 20`), zero loss. `pyflakes` and import clean.

## 44ca86b7a565 -- sevenfold.shelve() collapses when every seam ties

Confirmed live: `shelve(list(range(100)), {}, depth=2)`'s `seams()` returned cuts `[0,1,2,3,4,5]`
-- six one-member children and one 94-member child -- because every gap defaults to
`weights.get(..., 0.0) = 0.0` when `weights` is empty, and `gaps.sort()` (stable) leaves ties in
original-index order, so `gaps[:k-1]` always takes the first six POSITIONS rather than the
weakest six SEAMS. `build()` hits this on every call for worlds (`inner = shelve(names, {},
depth=len(WORLD_TIERS))` always passes an empty dict, since `worldseed` computes no pairwise
affinity within a source) -- not an edge case, the routine path. This directly contradicts the
function's own docstring ("Balance is by construction... no branch can swell into the giant
component"). Fixed `seams()` to detect the no-signal case (`len({g for g,_ in gaps}) <= 1`, which
covers the empty-weights case and any other all-tied block) and fall back to evenly spaced cuts
(`step = len(block)/k`) instead of the front-loaded slice; real affinity data (weights present and
varying) still sorts by weight and cuts the genuinely weakest seams exactly as before. Reverified
the same 100-member, empty-weights case post-fix, called directly against the real
`sevenfold.shelve`: child sizes are now `[14,15,14,14,14,15,14]`. `pyflakes` and import clean.

## b68ca666da79 -- scope.py's scope signal drawn from a truncated ranked list -- Hard Rule 0

Confirmed live before fixing: `srlimit: "3"` capped each of the four fixed search queries, and
`pages = F.fetch(host, titles[:8])` dropped everything past the eighth relevance-ranked title
before a single tier-mention was counted. Both are internal fixed numbers, not a human `--limit`,
which is the textbook Hard Rule 0 shape ("No limit, no cap, no sample, no 'top N'..."); the
resulting counts feed `MIN_MENTIONS` -> `SCOPE.json` -> `magnitude.host_ceiling()`, which clamps
every entity in that source. This exact finding was already reported and marked
"Severity: MAJOR. VERIFIED" at `handoff/sweep24/AUDIT_batch06.md:320` and left unfixed across
every sweep since. Rather than invent a new resolution, used the project's own already-accepted
precedent for the identical `list=search` API surface: `feats.discover()` (feats.py:480-529)
raised its own `srlimit` from a low fixed value to the API's practical per-call ceiling and logs a
`continue`-key hit rather than building a full pagination loop up front, reasoning explicitly that
the loop is "only worth its cost if the cap ever binds." Applied the same shape here: `srlimit`
raised `"3"` -> `"500"`, with `silence.note("scope.py:srlimit-bound")` recorded whenever a
response still carries `continue` (so a genuine miss is now visible in the ledger instead of
silent). The `titles[:8]` truncation is removed outright, not just raised -- `F.fetch`'s own
docstring already promises "up to any number of titles, batched where batching is possible," so
passing the full `titles` list is a complete fix for that half of the bug, not a bigger cap.
`scope.py`'s call volume is low (4 queries per host, ~200 hosts total, not per-entity like
`discover()`), so 500 removes the truncation in the overwhelming majority of real cases; a wiki
whose relevant search results for one of the four fixed cosmology phrases genuinely exceed 500 hits
would still need the full continuation loop `feats.py` itself deferred -- now at least measurable
via the new note. `pyflakes` and import clean. NOTE: the `--how` text passed to
`workorders.py --resolve` for this order got truncated mid-sentence by an unescaped backtick in
the shell command (bash read `` `continue` `` as command substitution); the closed-ledger entry at
`state/workorders_closed.jsonl` for `b68ca666da79` therefore ends abruptly at "...and " -- the
code fix and this paragraph are the complete, accurate record.
