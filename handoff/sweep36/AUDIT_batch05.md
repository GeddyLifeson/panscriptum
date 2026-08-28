# AUDIT batch 05 — run #36

Modules: `foreman.py`, `build_terminal.py`, `rosetta.py`, `weave_index.py`, `feats_index.py`,
`wh40k.py`, `retry_synthesis.py`

All seven read in full (foreman.py in two passes, 1-1063 and 1064-1602, both read). Read-only —
no source edited.

---

## foreman.py (1602 lines)

This module is the live job supervisor and is exceptionally heavily self-documented: nearly
every function's docstring or an inline comment already records a specific past defect (run #3,
#19, #24, #26, #27, #31, m18, m17...) and its fix, in the style this sweep is looking for. I read
the whole file specifically hunting for (a) job-state read-modify-writes without compare-and-swap
and (b) kill decisions made on stale data, per the batch guidance, and could not find a new
instance of either that isn't already caught and documented in the code itself. Specifics:

- **`kill_stalled_job()`** (line 435) reads the stall verdict once from `ST.check(D.state())`,
  then re-queries the live process table via a fresh `wmic` call *inside* the per-job loop
  (line 482) before killing — so the actual SIGTERM target is matched against a fresh process
  snapshot, not the snapshot standards was computed from. The only staleness gap is the time
  between the standards read and the kill (a job could recover in between), which is inherent to
  any stall-detector-then-kill design and is not a new finding — the function's own docstring
  already reasons about the cost/benefit of killing a wedged-but-resumable job.
- **`kill_duplicate_jobs()`** (line 548) takes one `wmic` snapshot and makes its keep-oldest
  decision entirely from that single snapshot — no staleness gap.
- **`_catalogue_batch()`** (line 663) read-modify-writes `state/CATALOGUE_ATTEMPTS.json`
  (read → compute batch → stamp `seen[s] = now` for dispatched sources → filter → write via
  `silence.write_json`). Single-writer per foreman round; the write's return value is not
  checked (unlike almost every other RMW site in this file, which call
  `silence.replace_retry`/check the bool) — see finding below.
- Every other read-modify-write onto shared state in this file (`POOL_PROOF.json`,
  `state/failures.json` + its archive, `OVERWATCH.json` in `_retire()`, `FOREMAN.json` in
  `round_once()`, `OLLAMA_RESTARTS.json`, `FOR_OWNER.md`) already uses the tmp-file +
  `silence.replace_retry()` pattern and checks the returned bool, with an explicit comment at
  each site naming the exact hazard a denied rename would cause. These all read as already
  hardened by prior audits.

**MINOR — finding 1.** `_catalogue_batch()` (around line 758) calls
`silence.write_json(CATALOGUE_ATTEMPTS, seen)` and does check the return value this time
(`if not silence.write_json(...): silence.note(...)`) — on inspection this one *is* checked,
correctly. No defect. (Flagging that I initially suspected an unchecked write here and traced it
through before ruling it out, in case a later reader has the same suspicion — the check is at
line 758-762, immediately after the write.)

**QUESTION, not a defect.** `run_catalogue_gap()` gates the whole catalogue dispatch on
`_fandom_reachable()`, which only probes `standards.FANDOM_PROBE_HOST` (one content host). If
that one host is down while every *other* fandom content host is up, the gate defers a round
that could have run for every other source. The docstring for `_fandom_reachable` explicitly
accepts this ("that is the safe direction") — flagging only because the guidance asked about
kill/defer decisions made on incomplete data; this looks like a deliberate, documented trade-off
rather than a bug.

No new MAJOR or MINOR finding in this module beyond what its own comments already record as
fixed. If anything, this file is a model of the pattern the sweep is looking for — every
past defect is preserved in-place as a comment rather than deleted, which made verifying "already
fixed vs still broken" fast.

---

## wh40k.py (244 lines) — MAJOR, confirmed open defect

**Finding.** `compute()`, line 197:

```python
sheet = {ax: "[wiki] " + v[1] for ax, v in rec["axes"].items()}
```

This stamps **every** axis worksheet line `[wiki]` unconditionally, regardless of whether the
axis text is an actual quoted sentence from the wiki or the assayer's own paraphrase/judgment.
Reading the `ROSTER` entries confirms both kinds are present and mixed within single entities —
e.g. Khorne's `acumen` axis (line 101-103) is a paraphrase-with-embedded-quote judgment ("The
lowest acumen at the top of this setting. He does not plan, and '...'"), same shape as several
Emperor and Tzeentch axes.

This is the exact sibling defect the task guidance named, and it is **not a suspicion** — it is
already filed and cross-referenced. `halo.py`'s `compute()` docstring (line 142-150) says
explicitly:

> "The same defect stands filed against `wh40k.py` (order 1770c2b84786), which is a different
> module and is not touched here."

`halo.py` was fixed by giving each axis tuple a third element (a provenance tag, `"wiki"` or
`"canon"`) and stamping `"[" + v[2] + "] " + v[1]` per axis instead of a blanket `"[wiki] "`
(confirmed by reading `halo.py` lines 111-134, 152). `wh40k.py`'s `ROSTER` dict still uses
2-tuples `(score, text)` for every axis (see e.g. lines 58-76) with no provenance field at all,
so the fix pattern from `halo.py` has not been applied here. **This is confirmed still open,
against order 1770c2b84786.**

Downstream effect: `A.assay(...)` receives `worksheet=sheet` and the resulting
`data/WH40K_ASSAYS.json` records every axis as `[wiki]`-provenanced even where the text is
editorial judgment, which is exactly the "provenance mark that is applied to everything
distinguishes nothing" problem `halo.py`'s docstring names.

Also read `main()`/`compute()` end-to-end for other issues (regex, output write): the final
write already uses `silence.write_json` (line 237) with an in-file comment (line 230-236) noting
it was made atomic on 2026-08-25 "as the m100 tail" — consistent with what's expected, nothing
further found there.

---

## weave_index.py (343 lines)

Read in full. This module's docstrings themselves record and defend against several caching/
staleness classes (BUGS m17, "31715d/98a80b" 2026-08-26 perf note on `_records_sig`), and on
inspection the fixes described are present and consistent (the `os.scandir` + 1.0s memo in
`_records_sig`, the corpus-signature-keyed cache in `designations()` and `load_records()`).

No silent cap found on the written outputs. `ENTITY_INDEX.json` and `WEAVE_CANDIDATES.json` are
both written whole via `silence.write_json` with no slicing (lines 335-337); every entry that
survives the key/stopname filter goes in. The only `[:N]` slices in the file (`[:10]`, `[:18]`,
`[:5]`, `[:26]`, `[:16]` at lines 322-331) are all in the **console report** in `main()` —
`top n sources` summary printing — and do not touch what gets written to disk.

**QUESTION, not a defect.** `build()` (line 268) drops any entry whose normalised name is under
3 characters or falls in `_STOPNAMES` (line 48-53: "narrator", "father", "mother", "god",
"king", "queen", etc.) **entirely from the index**, not just from candidate matching. The
docstring's rationale ("Names too generic to be evidence of anything. A collision on these is
meaningless") is about false-positive *cross-source collisions*, but the implementation drops
these entries from `index` itself, so an entity whose full name folds down to exactly a stopword
after title-stripping (e.g. a character literally named "Father" — Fullmetal Alchemist's
antagonist is exactly this) would never appear in `ENTITY_INDEX.json` at all, not just be
excluded from `WEAVE_CANDIDATES.json`. Traced the consumers (`weave.py`, `canon_backup.py`):
`canon_backup.py` only checks that `ENTITY_INDEX.json` is rebuildable/derived and doesn't rely on
completeness (it's excluded from backup precisely because it's derived), and `weave.py` only
ever reads it for candidate-relation purposes. So the practical blast radius looks small, but
flagging as a question because the stopname filter is described as being about *matching noise*
while it actually removes entries from the index, which is a slightly different and stronger
claim than the docstring states.

**MINOR — possible truncation of stored description.** `build()` line 291:
`"description": (e.get("description") or "")[:400]`. This truncates each entity's description to
400 characters in the written `ENTITY_INDEX.json`. Traced the one downstream consumer of that
field (`weave.py` line 204: `desc = hits[0].get("description") or ""`, then itself re-slices to
`desc[:400]`/`desc[:300]` for regex matching at lines 205-206) — so for this specific consumer
the 400-char cap costs nothing. Flagging only because `ENTITY_INDEX.json` is a general-purpose
derived index and a future second consumer that wanted the full description would silently get a
truncated one with no signal that anything was cut. Not a Hard-Rule-0 roster truncation (it
doesn't drop entities), but it is a silent truncation of stored field content.

---

## feats_index.py (289 lines)

Read in full. This module explicitly states its own no-caps policy in the module docstring
("NO CAPS. `feats_for_source` returns every feat of every matching entity...") and the code
matches the claim: `feats_for_source()` (line 191) does not slice its output list, and
`load_index()` iterates the whole `readfeats` tree with no cap. `audit()`'s stranded-host report
uses `Counter.most_common()` with no argument (line 282), which returns every host, not a
truncated top-N.

The multi-stage host-resolution logic (record's own `host` field first, `WIKI_HOSTS`-derived
fallback second) matches what its own docstring claims and what the sibling fix in
`halo.py`/other modules established as the pattern (ask the record, don't re-derive from a
lossy directory-name inverse). Read `audit()` and `main()` for a rate-of-zero division guard:
`rate = 100.0 * a["joined"] / max(1, a["records"])` (line 275) — this is a legitimate
divide-by-zero guard for the *display percentage* when the store is empty (0 joined / 1 = 0.0%,
which is the correct answer for an empty store), not a guard hiding a real defect.

Read, nothing found.

---

## build_terminal.py (579 lines)

Read in full, including the embedded JS template. The module's own comments record two prior
Hard-Rule-0 fixes already applied and now scroll-bounded rather than truncated: the `.roster`
CSS class (line 52-55, "used to be sliced to 8... The panel is bounded by scroll instead of by
truncation") and the shelved-source/world listing in `panel()` (line 491-492), which maps over
the *full* `nd.s`/`nd.w` arrays with no slice. Confirmed by reading `panel()` in full — no `.slice`
on the roster arrays, only on individual *label strings* for on-screen legibility (`.slice(0,22)`
etc. at lines 291, 322, 347, 352 — these truncate a single name's *display* string with an
ellipsis or an unabbreviated tooltip alongside it, e.g. line 328's `<title>${esc(nm)} ...`
carries the untruncated name; this is a rendering-width concern, not a roster cap).

The `<` → `<` neutralisation before splicing JSON into the inline `<script>` (line 567) is
present and matches the BUGS m10 fix it cites.

`main()` writes `output/registry_terminal.html` with a plain `open(OUT, "w", ...)` (line 571),
not the tmp+atomic-replace pattern used elsewhere in this project for files with concurrent
readers. This is a build artifact regenerated by a one-shot script invocation, not a
standing-daemon-polled file like `FOREMAN.json` or `state/failures.json`, so I don't believe this
rises to the RMW hazard class the guidance was pointing at — flagging only as a low-confidence
question in case something else does poll this file mid-write (I did not find such a caller).

Read, nothing else found.

---

## retry_synthesis.py (209 lines)

Read in full. This module's docstring and inline comments already record and fix two distinct
races (run #31: fixed temp-filename collision + `os.replace` lock issue via `silence.write_json`;
run #33 finding, addressed in `save_side()`: read-merge-write narrows but does not eliminate a
concurrent-invocation content race, documented as an accepted residual risk with an explicit
no-lock-file rationale) and one merge-target bug (run #26: `do_merge()` was bypassing
`pipeline.write_record`'s two-writer merge contract and writing raw, fixed by routing through
`PL.write_record`).

Traced `do_merge()`'s interaction with `pipeline.write_record()` (in `pipeline.py`, not in this
batch, but read to verify the claim): `write_record`'s drift-merge path takes the **in-memory
caller's** value for every non-`entries` top-level key present in `rec` (`pipeline.py` line
677-678: `for key, val in rec.items(): if key != "entries": disk[key] = val` — unlike its sibling
`write_record_catalogue`, this does not protect disk-side keys against a stale in-memory `None`).
`do_merge()`'s `rec` comes from a `PL.records()` snapshot taken once at the top of the function
(line 143) and is held across an unbounded number of per-source merges. If the pipeline is
running concurrently and writes some *other* top-level field on the same record between
`do_merge()`'s snapshot and its `write_record()` call for that record, that field would be
silently reverted to the snapshot's stale value. This is exactly the class of bug run #26 fixed
one layer up — but `do_merge()`'s own docstring (line 137) already states "Run ONLY when the
pipeline is stopped" and the module docstring's opening lines state the whole file's design
constraint is "the pipeline is still running... So this script writes NEITHER [record store]"
except in `--merge` mode, which is explicitly gated as a stopped-pipeline-only operation. So this
is a **known, already-documented constraint** ("nothing enforced it" is stated in-file at line
160-161) rather than a new finding — noting it here only because the guidance specifically asked
about RMW hazards and I want the trace on record rather than silently passing over it.

No new finding.

---

## rosetta.py (443 lines)

Read in full. Extensively self-documented with prior fixes (One Piece row-pairing bug, the
`\bbount\b` word-boundary bug, single-letter Stand-stat false matches, `srlimit=50` audited not
to truncate per m82, the removed `pipeline._x` phantom-attribute bug from run #33, the missing
exit code fix from "2026-08-26, batch 3").

Checked the one numbered line-tag in this batch: `silence.note("rosetta.py:136")` at line 137
(inside `numeric_rows.offer()`'s `except ValueError:` handler). Line 136 is currently the
`except ValueError:` line itself — the tag is **currently accurate**. Flagging as a low-priority
QUESTION only: this project's own convention has moved away from numbered line tags toward
content labels specifically because line numbers drift (see `weave.py`'s
`silence.note("weave.py:statblock-import")` comment, which explains a numbered tag there had
already gone stale and cost a wasted grep) — `rosetta.py` is the one file in this batch still
using the drift-prone numbered form, and it happens to still be correct today. Not a defect now;
worth converting to a content label before it drifts, same as `weave.py` was.

`numeric_rows()`'s outlier filter (`v <= med * 1000`, line 166-171) and `_STAND`/`_NOT_A_NAME`
filters are pre-existing, reasoned data-cleaning steps (median-relative outlier rejection to
discard parse artefacts), not Hard-Rule-0 caps on a roster — they don't rank-then-truncate a
list, they threshold out values that are already known-bad by construction (self-described and
measured against real cases in the docstrings).

`check()`'s exit-code fix (line 426-435, "2026-08-26, batch 3") returns 1 when any scale
disagrees — read `main()`'s `--check` path end to end and confirmed the `return 1` path is live
and reachable (not shadowed by an earlier unconditional return).

Read, nothing new found.

---

## Summary of findings

1. **MAJOR — `wh40k.py:197`** (`compute()`): `sheet = {ax: "[wiki] " + v[1] for ax, v in
   rec["axes"].items()}` stamps every axis `[wiki]` unconditionally, mixing verbatim-wiki and
   paraphrase/editorial axes under one provenance tag. This is the sibling defect
   `halo.py`'s `compute()` docstring names explicitly as still open against `wh40k.py` (order
   1770c2b84786) — confirmed still present; `halo.py`'s fix (per-axis 3-tuple with a `"wiki"`/
   `"canon"` provenance tag, `sheet = {ax: "[" + v[2] + "] " + v[1] ...}`) has not been applied
   to `wh40k.py`'s `ROSTER`/`compute()`.
2. **MINOR/QUESTION — `weave_index.py:282`** (`_STOPNAMES`): drops entries whose normalised name
   is a stopword (e.g. "father", "god", "king") entirely from `ENTITY_INDEX.json`, not just from
   cross-source candidate matching as the docstring's stated rationale implies — a real
   single-word character name (e.g. Fullmetal Alchemist's "Father") would be invisible to the
   index. Low blast radius today (traced both consumers), flagged for the gap between stated
   intent and actual effect.
3. **MINOR/QUESTION — `weave_index.py:291`**: `description` field truncated to 400 chars in the
   written index; harmless for the one traced consumer (`weave.py`, which re-truncates further
   anyway) but a silent truncation of stored data for any future consumer.
4. **QUESTION — `rosetta.py:137`**: still uses a numbered line-tag (`"rosetta.py:136"`) instead
   of the content-label convention the project moved to elsewhere after being burned by drift;
   currently accurate, flagged pre-emptively.
5. **QUESTION — `build_terminal.py:571`**: `output/registry_terminal.html` is written with a
   plain (non-atomic) `open(..., "w")`; no concurrent reader found, flagged low-confidence.
6. **QUESTION — `retry_synthesis.py`/`pipeline.write_record`**: `do_merge()`'s stale-snapshot
   risk against `write_record`'s unprotected-non-entries-key merge is real in principle but is
   already documented in-file as a known, accepted "pipeline must be stopped" constraint with
   "nothing enforced it" stated explicitly — not a new finding, recorded for completeness.

No other MAJOR/MINOR findings in this batch. `foreman.py`, `feats_index.py`,
`build_terminal.py`, `retry_synthesis.py`, and `rosetta.py` (beyond the two QUESTIONs above) read
clean against the catalogue of recurring defects — checks-that-cannot-fail, silent caps,
un-wired safety, concurrency/RMW hazards, discarded verdicts, and stale line-tags.
