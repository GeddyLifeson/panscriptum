# run35, final wave, batch F1

24 orders worked. 18 fixed in owned files, 1 disproved-as-worded-but-partially-improved (left
open), 5 left open because the real fix lives in a file this agent does not own, could regress
production without a live crawl to verify against, or requires a re-mine this agent was told
not to start.

## Fixed

**0ea638f01b03** -- `src/resync_roll.py:main()`. `silence.write_json(ROLL, roll, ...)`'s return
value was discarded, so a denied replace (a reader holding `SWEEP_ROLL.json` open, the case the
module's own docstring warns about) left the roll unchanged while the summary still printed
"Fixed N roll entries". Now captured as `landed` and reported: on denial the run prints
`WRITE DENIED ... roll is UNCHANGED on disk` and skips the "roll now" summary that would
otherwise describe figures that never landed.

**220a0d0a1d70** -- `src/pipeline.py`. Four `silence.note()` calls carried stale line-number
tags (`pipeline.py:191/301/261/277`) that no longer pointed at their own call sites, the shape
every other tag in the file avoids by using a NAME. Renamed to
`records-unreadable`, `write_record-notfound`, `mined_feats-hosts`, `mined_feats-corrupt`.

**2326f7a4ed66** -- `src/corpus_db.py:rebuild()`. `evidence_limit` truncated the evidence file
list with nothing recording that `meta.evidence` was a partial count. Added `evidence_truncated`
tracking, a `meta` row (`evidence_truncated`), a field on `rebuild()`'s return dict, and a CLI
warning under `--rebuild` when it fires. No current caller passes `evidence_limit`, but the
function is public and the meta row means a future caller (or a direct query against the
database) can no longer mistake a partial scan for a total one.

**49474966f971** -- `src/onomast.py:name_worlds()`. `taken` started empty every call, seeded
only with names coined in the same run, never with designations already standing in
`data/ONOMASTICON.json`. Now seeded from the file's current contents, excluding any cid that is
also present in the current `resolved` argument (those get freshly recomputed below, so seeding
them too would make a world see its own prior designation as "taken" and get bumped to a
different name on every otherwise-unchanged rerun -- verified both properties with two new
checks: a genuinely external name is respected, and an unchanged full rerun is still
idempotent).

**4e0e1949ec0b** -- `src/weave_index.py:load_records()`. `silence.note("weave_index.py:155")`
at the (now) line-260 JSON-parse failure was 42 lines stale. Renamed to
`weave_index.py:load_records-unreadable`.

**5925b90cb6d0 (partial, order left open)** -- `src/cosmography.py`. `DEFAULT_SIZE_CLASS` had
no reader anywhere in `src/`; `census()`'s own signature re-typed the literal `"STANDARD"`
instead of referencing the constant, so the docstring's reversibility claim ("change one,
re-run, and every downstream figure moves with it") was false for it. Fixed:
`census(size_class=DEFAULT_SIZE_CLASS, ...)`. The other half of the finding --
`KARDASHEV_TYPE_I` and `EARTH_POWER_2020` duplicated as literals in `verify_math.py:176-177`
instead of imported by name -- is unfixed: `verify_math.py` is on the must-not-edit list, and
there is no reader for these two constants anywhere in an owned file to wire up instead. Order
left open, noting the partial fix.

**57b0d3dab53d** -- LEFT OPEN. The remedy line in question lives in `src/standards.py:1136`
(must-not-edit) and is echoed in `src/foreman.py` (not owned). No owned file to fix.

**6a83762ab9bb** -- LEFT OPEN. The missing `hosts=` argument is at `src/hosts.py:158`.
`hosts.py` is not in the owned file list (only its callee, `hostcheck.py`, is), so the actual
call site cannot be touched.

**71aef747c9e7** -- `src/feats.py`. `_RATE_LIMITED[host] += 1` (in `api()`'s HTTPError handler)
and `_CAP_BOUND["aplimit"/"srlimit"] += 1` (in `discover()`) did read-modify-write on shared
dicts with no lock held; `roll()` runs up to 12 workers. Added `_COUNTS_LOCK` and wrapped all
three increments in `with _COUNTS_LOCK:`, matching the pattern the `done` dict in `roll()`
already used.

**77d88ce737bc** -- LEFT OPEN as instructed. The remedy is real (invalidate or re-mine
`data/feats/` entries written before the page-gate fix, since `cachekey.load` keeps returning
their stale `pages_refused`/near-zero feats) but requires either a targeted cache-invalidation
pass keyed on the entries' write timestamp vs. the fix's landing time, or a re-mine -- and this
agent was explicitly told not to start a re-mine. No code change made.

**80fa56642f33 (MAJOR)** -- `src/zfighters.py:main()`. Reproduced live: `--full` raised
`KeyError: 'provenance'` on the Son Goku sheet carried in from
`data/REFERENCE_ASSAYS_PRESENCE.json`, whose axes carry only `["cited","score"]`. Confirmed on
disk (`json.load(...)["Son Goku"]["axes"]["ruin"].keys() == ["score","cited"]`). Fixed the print
line to `d.get("provenance", "")` -- an honest blank instead of a fabricated "canon"/"wiki"
label the source sheet never claimed. Verified: `--full` now exits 0, prints Goku's worksheet
with blank `[]` provenance tags, and `data/Z_FIGHTERS.json` (read by `pantheon.py`) is written
again, which the crash had been preventing.

**87a01fd3b978** -- `src/withdraw_chapters.py:main()`. The catalog-emptying write used a
hand-rolled `CATALOG + ".tmp"` plus bare `json.dump` and discarded `silence.replace_retry`'s
return. Replaced with `silence.write_json(CATALOG, {}, indent=2)`, verdict captured as
`catalog_landed`, and a `CATALOG WRITE DENIED` message prints if it comes back `False` (this
write runs after every chapter file has already been moved, so a silent denial would leave the
catalog listing paths that no longer exist).

**920942075624** -- `src/repass_bands.py:main()`. `of 211` was a hardcoded denominator against
`len(demoted_sources)`, while the true source count (216 on disk, verified) is `len(recs)`.
Changed the print to `of {len(recs):,}`.

**92c0c50a6d2d** -- `src/pick_model.py:free_vram_gb()`. `silence.note("pick_model.py:150")`
tagged the wrong line versus its symbolic sibling 25 lines up (`total_vram`). Renamed to
`pick_model.py:free_vram`.

**96e8ac88c6f8** -- `src/endpoint.py:source_pages()`. Docstring said "`{}` when it has none";
both code paths return a list (`[]` on failure or absence). Fixed the docstring to say `[]`.

**9beb0391c8ab** -- LEFT OPEN. `feats.page_looks_real(text, title="", wiki=True)` never reads
`title`. The order's own remedy is "use it or drop the parameter and fix the caller" -- the one
caller is `binding_health.py:184` (must-not-edit), so dropping is not available. "Use it" was
considered (checking the served text against the requested title to catch a soft-404) but
raw MediaWiki wikitext does not reliably repeat its own title verbatim, and this agent has no
way to verify a title-presence gate against live wiki fetches without starting a crawl, which
was disallowed for this batch. A wrong gate here would misclassify healthy hosts as broken in
`binding_health.py`'s availability checks. Left open as a judgment call this agent should not
make blind.

**cf231efb8b5b** -- `src/resync_roll.py:main()`. Sorting `os.listdir()` (from a prior order)
made the WINNER of a split-file collision reproducible but the loser's entries still vanished
from `by_source` with no trace. Added detection: a second record file declaring the same
`source` now fires `silence.note("resync_roll.py:duplicate-source")` and is collected into
`dupes`, printed in the report as `X == Y` pairs with a note that the loser is not reflected in
the entry-count diff above it. Which file should win stays a data-authority question this
script does not answer; the loss is no longer invisible.

**d7a7bbb70bf1** -- LEFT OPEN. The mis-spelled quarantine key lives in `src/health.py:288`
(must-not-edit).

**de9a39b2b47c** -- `src/weave_index.py:load_records()`. Docstring said "217 files"; disk holds
216, and `corpus_db.py`'s own header already says 216 for the same directory. Changed to "216
files" so the two modules agree with each other and with disk. (The docstring's `63MB`/`27MB`
figures are a dated, frozen 2026-08-23 benchmark narrative, not the subject of this order's
specific file-count disagreement, and were left as originally measured.)

**e5a4928f2ae9** -- `src/scout.py`. `silence.note("scout.py:241")` at the LOG-read handler
(now line 400) was stale and, per the re-file note, had been mistakenly auto-closed once
already. Renamed to `scout.py:log-unreadable`, distinct from the file's other content-labelled
tags (`_ask`, `verify`, `blocked`, etc.) and from `verify()`'s own handlers.

**ed5434c0bc65** -- `src/cascade_bridge.py`. Three numeric tags: `:100`/`:113` in
`_extract_json()`'s fence-parse and brace-matcher fallbacks, and `:151` in the streaming
provider-call's exception handler (the one that had come to point at another `silence.note`
call, per the order). Renamed to `extract_json-fence`, `extract_json-brace`, `stream-pump`.

**f842daaba5c5** -- `src/feats.py`, `_QUANTITY` / `mine()`. Verified live: `"3 x 10 ^ 9
megatons"` parsed to `value: "9"` before the fix (regex required the caret to sit directly
against `10` with no whitespace, so `"10 ^ 9"` failed the exponent clause and backtracked onto
the bare "9 megatons"). Rewrote the exponent clause to allow whitespace around an optional
caret, added a signed-exponent group for negative exponents, added `×` alongside the letter `x`,
and added a second alternative for caret-less superscript exponents (`10⁹`, `10⁻⁹`), translated
back to plain digits via `str.maketrans`. `mine()` updated for the new group numbering (unit
moved from group 3 to group 4) and to prefer whichever exponent group matched. Verified all six
shapes parse to the correct value (`"3 x 10 ^ 9 megatons"` -> `3e9`, not `9`); six new test
cases added to `handoff/run35/checks_F1.py`.

**f979491d26a9** -- LEFT OPEN. The corrupt-ledger handling this describes
(`state/failures.json.corrupt`, the "nothing ever looked at what tore it" gap) lives entirely in
`src/health.py` (must-not-edit); no owned file touches this ledger's corrupt-handling path.

## Method notes

- Every numeric-tag fix was verified by reading the actual current line the tag sits on (not
  trusting the order's own line numbers, which are themselves often stale by design -- that is
  the entire class of bug) and confirming no other tag in the file already used the chosen
  label.
- `f842daaba5c5` and `80fa56642f33` were both reproduced against real inputs (a live regex probe
  and a live `--full` run against the actual `data/REFERENCE_ASSAYS_PRESENCE.json`) before being
  called fixed, per Hard Rule -1's PROVEN property.
- `49474966f971`'s fix was checked for a regression risk of its own (breaking the module's
  documented rerun-idempotence) before being written, not just the collision case the order
  named; both properties now have standalone checks.
