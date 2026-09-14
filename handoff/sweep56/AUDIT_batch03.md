# Sweep56 batch03 audit — pipeline.py, identity.py, feats_index.py, cleanup.py, snapshot.py, roll.py, scale_theories.py, module_index.py

Every module below was read in full, top to bottom, in successive chunks (pipeline.py at 3,493
lines was read in ~400-line windows; the rest were read whole in one pass each). No sampling.

All line numbers below were read directly off the file at audit time (2026-09-11) via the `Read`
tool; none are carried over from memory or another document.

---

## pipeline.py (3,493 lines)

### DEFECT — stale self-referential line citations, `pipeline.py:712-715`

```
711  # AND `subroom`, WHICH WAS THE ONE FIELD ADDED AFTER THIS MECHANISM WAS WRITTEN
712  # (sweep43-batch03). The judging loop treats it identically to `topic` -- `:1718` pops
713  # `subroom_rejected` the moment a subroom passes `subroom_ok`, exactly as `:1707` pops
714  # `topic_rejected` -- and `subroom_rejected` is already declared in `MERGED_ENTRY_FIELDS` at
715  # :554. It was simply never added here, so the pop stayed in memory and could not reach disk:
```

This comment cites three line numbers into pipeline.py itself: `:1718` (subroom_rejected pop),
`:1707` (topic_rejected pop), `:554` (MERGED_ENTRY_FIELDS declaring `subroom_rejected`). None of
the three still points at the cited code:

- The `topic_rejected` pop is now at line **2258** (`batch[i].pop("topic_rejected", None)`), not 1707.
- The `subroom_rejected` pop is now at line **2269** (`batch[i].pop("subroom_rejected", None)`), not 1718.
- `MERGED_ENTRY_FIELDS`'s `"subroom_rejected",` entry is now at line **691**, not 554.

The conclusion the comment draws (subroom's pop couldn't reach disk until it was added to
`MERGED_ENTRY_FIELDS`) is still correct and matches the code as it stands today — only the
citations have rotted, by roughly 550-1700 lines. This is exactly the failure mode CLAUDE.md and
this project's own doctrine warn about elsewhere in this same file (e.g. the `identity.py`
`epoch_of` docstring: "a line number is a citation with an expiry date nobody can see"). Ironic
that the file containing that lesson has its own drifted citation.

**Confidence: DEFECT** (stale citation, mechanically verified against current line numbers).
Low real-world cost — the claim is still true, just unverifiable-by-line from the comment.

### DEFECT — stale cross-file line citation, `pipeline.py:732`

```
730  # (`catalogue_web.py:244-246` and `:456-458`, and the same shape in
731  # `catalogue_aurora`, `catalogue_codex`, `ingest_doc` and `backfill`). So `sv` was always truthy
```

Checked against `src/catalogue_web.py` as it stands: lines 244-246 and 456-458 are inside a
provenance-tracking comment/`first_cat` construction, not the per-entry dict literal that
actually sets `"category"` and `"description"` unconditionally. The real per-entry dict literals
that back the claim ("every cast-builder sets BOTH on every entry it emits and never leaves
either empty") are at `catalogue_web.py:304-317` (`"description": text, ... "category": "Persons
(named individual characters, real or fictional)",`) and `catalogue_web.py:554-565`
(`"description": text, ... "category": canon,`) — roughly 60-110 lines past the cited numbers.
The underlying claim in pipeline.py still holds against the current file; the citation that was
supposed to let a reader verify it without re-deriving it does not.

**Confidence: DEFECT** (stale citation, spot-checked against catalogue_web.py's current content).

### DEFECT — `subroom_rejected` is silently truncated; its sibling `topic_rejected` is not, `pipeline.py:2258-2273`

```
2255  topic = (res.get("topic") or "").strip()
2256  if topic in TOPICS:
2257      batch[i]["topic"] = topic
2258      batch[i].pop("topic_rejected", None)
2259  else:
2260      batch[i]["topic"] = "unclassified"
2261      if topic:
2262          batch[i]["topic_rejected"] = _stored_cut(topic, 120)
...
2266  sub = (res.get("subroom") or "").strip()
2267  if sub and subroom_ok(batch[i].get("category"), sub):
2268      batch[i]["subroom"] = sub
2269      batch[i].pop("subroom_rejected", None)
2270  else:
2271      batch[i]["subroom"] = SUBROOM_UNCLASSIFIED if sub else SUBROOM_NONE
2272      if sub:
2273          batch[i]["subroom_rejected"] = sub[:120]
```

`topic_rejected` is written through `_stored_cut(topic, 120)` (line 2262), which — per its own
docstring at line 237 — "mark[s] it when a cut actually happened" by appending
`"... (+N chars)"`. `subroom_rejected`, added later (per the file's own comment at line 711,
"the ONE FIELD ADDED AFTER THIS MECHANISM WAS WRITTEN"), is instead written with a bare
`sub[:120]` slice at line 2273 — the exact silent-truncation shape `_stored_cut` exists to close,
and the exact shape this project's Hard Rule 0 doctrine treats as a defect elsewhere in this same
file (`_stored_cut`'s own docstring: "a value cut at the bound reads as a COMPLETE value with
nothing distinguishing it from one that simply ended there"). This field is written into
`data/records/*.json` (per `_stored_cut`'s docstring, describing "these five fields" as exactly
this class of stored, re-read value), so a `subroom_rejected` value at or past 120 characters is
indistinguishable on disk from one that happened to be exactly 120 characters long.

**Confidence: DEFECT.** Verified against the sibling field's correct handling three lines above.
Low-to-moderate real-world cost (subroom_rejected is a diagnostic/audit field, not a shelved
value), but it is a genuine, silent, undisclosed truncation of a value written to canonical
storage, which is the shape Hard Rule 0 and `_stored_cut`'s own docstring both name as the thing
to avoid.

### QUESTION — phases 1-7 never consult `roll.py`'s exclusion list

`roll.py`'s docstring states its purpose as being the *one* place exclusion is decided, so "the
consumers ask it rather than each deciding for themselves," and names what out-of-scope removes a
source from: "nothing crawls it, nothing generates from it, nothing counts it as a coverage
shortfall, and nothing files work orders about how badly cited it is."

`pipeline.py` never imports `roll` and never calls `roll.in_scope`/`roll.out_of_scope` anywhere
except inside `phase_write` (phase 8), where it builds `roll = {source: row}` (line 3032) purely
to hand a single row into `manifest_builder.build_jobs_for_source` (line 3038) — it does not
itself check exclusion. Phases 1 (`phase_synthesis`), 2 (`phase_entrypass`), 3 (`phase_weave`), 4
(`phase_chain`), 5 (`phase_cosmology`), 6 (`phase_history`) and 7 (`phase_shelve`) all operate over
every record `records()`/`weave_index`/etc. returns, with no reference to roll status at all.
Confirmed by grep: the only match for `roll\.` or `import roll` anywhere in this file is the one
at line 3032/3038.

Whether this is a gap or is deliberate is genuinely unclear from the text available to this
audit: roll.py's own list of what "removed from WORK" means does not explicitly name the
model-judgment passes (synthesis nomination, entrypass classification), only crawling,
generation, and coverage/work-order accounting — all of which other modules (`catalogue_web`,
`catalogue_aurora`, `catalogue_codex`, `manifest_builder`, `health`) do check. It is plausible the
owner intended judgment/scoring to continue running over an excluded source's already-cached
entries (harmless, since nothing downstream will publish it), and equally plausible that this is
an oversight that spends real constrained-pool/local-model calls scoring a source that will never
be shelved. Flagged as a QUESTION rather than a DEFECT because the scope of the owner's intent
for `OUT_OF_SCOPE` is not settled by anything read in this batch.

### QUESTION (minor) — undisclosed 240-char truncation of entry description fed to the entrypass classifier, `pipeline.py:2153-2157`

```
2153  # 380 -> 240 chars. Classification needs the opening clause ("X is a city in
2154  # ...", "a technique used by ..."), not the whole lead paragraph. Feats, when
2155  # present, are almost always stated early too.
2156  d = re.sub(r"\s+", " ", e.get("description", ""))[:240]
2157  lines.append(f"[{i}] {e['name']} (type: {e.get('type','')}): {d}")
```

This is a bare slice with no disclosure to the model that text was cut, unlike this same file's
established convention for exactly this situation: `_budgeted()` (line 1566) is documented as
existing precisely so that "Hard Rule 0's objection to a cap is not that a bound exists, it is
that an unmarked one 'returns a smaller universe wearing the same shape as the real one.'" The
comment's justification ("feats... are almost always stated early") is an unmeasured claim of the
same shape the file elsewhere explicitly repudiates for the ceiling-nomination cap ("If a lead
paragraph genuinely cannot carry a ceiling feat, then the number kept is irrelevant... If a lead
paragraph CAN carry one, then keeping the top fourteen... is a ranked truncation"). Unlike that
cap (which excluded whole entities from nomination), this one only trims the evidence shown for
an entity that IS being judged, and a missed feat here fails safe (produces "unassayed" rather
than a fabricated band) — so the blast radius is smaller. Flagged as a QUESTION, not a DEFECT,
because it may be an accepted token-budget trade-off rather than an oversight, and because
`valid_scale_note`'s gates make an under-evidenced answer default to `unassayed` rather than to a
wrong band.

### QUESTION (minor, cosmetic) — "median" is actually the upper-median for even counts, `pipeline.py:~2792-2796`

```
for d in sorted(groups):
    known = [lags[x] for x in groups[d] if isinstance(lags.get(x), (int, float))]
    log("    depth %d: %4d shelves, %d with a measurable lag%s"
        % (d, len(groups[d]), len(known),
           (", median %.0f yr" % sorted(known)[len(known) // 2]) if known else ""))
```

`sorted(known)[len(known) // 2]` is the upper-median element for an even-length list, not the
usual averaged median. This only affects a log line in `phase_history`'s console output, not any
stored artifact or downstream decision — flagged only because it is mislabeled ("median") rather
than because it matters materially.

### Nothing else found

The rest of pipeline.py — `ask`/`ask_pool_first`/`_pool_answer_usable` cloud-then-local routing,
`write_record`/`write_record_catalogue`'s two-writer merge logic, `_entry_pair_key`/duplicate-name
pairing, `save_state`/`land_json`/`_landed`'s gated atomic writes, `gate_done`, `phases_never_closed`,
`valid_scale_note`'s four gates, `main()`'s phase-pointer and exit-code handling, `codewatch`
staleness checks, and the escalation-chain import guard — were read in full and no further
tautological checks, fail-open paths, silent swallows, undisclosed caps, or dead code were found.
This module has an unusually dense internal audit trail of its own (each of these areas carries a
multi-paragraph comment describing a bug that was found and fixed there previously); nothing
observed contradicts what those comments claim about the current code.

---

## identity.py (753 lines)

Nothing found. Read in full. `_is_continuity`'s three-test branching (orthography, population,
branching-at-n==1, majority-at-n==2) was checked arithmetically against its own docstring and is
internally consistent; `load()`'s cache-staleness repair, its refusal to overwrite a populated
inventory with an empty mine, and its `_STALE_REMINED` once-per-process guard are all correctly
wired. `epoch_of`'s `strict=False` default does fail open (returns `""` rather than raising when
the probe never ran) but this is explicitly documented, in detail, as a deliberate additive
keyword whose real caller (`chain.adjudicate_mutuals`, outside this batch) is stated to pass
`strict=True`. Not flagged as a defect: the file's own docstring already treats the non-strict
default as a known, reasoned trade-off rather than an oversight, and this batch has no way to
verify or dispute the claim about the calling convention in `chain.py` without reading a module
outside its assignment.

---

## feats_index.py (574 lines)

Nothing found as a DEFECT. Read in full; `host_to_sources`'s raise-rather-than-cache-empty
behavior, `load_index`'s fault-counting (`unreadable`/`collided`), `feats_for_source`'s
within-source name-collision reporting, and `audit()`'s file-count-vs-index-count reporting were
all checked against their own stated rationale and hold up.

QUESTION (very low confidence, not verified against live data): `_norm(e.get("name"))` in
`feats_for_source` (around line 385) folds a missing/`None` entry name to `""` via `_norm(None)
-> ""`. If a source's catalogue carried more than one entry with no `name` field, they would
collide on the empty-string key and be reported through the same `collisions`/`_ENTRY_COLLISIONS`
path as a real name collision, with `kept %r, dropped %r` showing `None`. This is speculative —
nothing in this batch establishes that any catalogue entry actually lacks a `name` — so it is
filed as a question rather than a finding.

---

## cleanup.py (446 lines)

Nothing found. Read in full. `_ruby_question_mark`/`_ruby_parenthetical`'s non-ASCII guards,
`_MARKUP`'s idempotence (the `(?<!\?\?)` lookbehind), `clean_ceiling`'s exact/head/prefix/
prefix-ambiguous ladder, and `main()`'s five uncapped report rosters were all checked against the
extensive in-file history of previously-fixed defects, and the code matches what those comments
claim is now true (no remaining literal `[:N]` caps on any of the five rosters; the `unwritten`
list is genuinely printed in full).

---

## snapshot.py (377 lines)

Nothing found. Read in full. `_rel`'s containment check, `before()`'s partial-snapshot refusal and
nanosecond+pid unique id, `_dir_matches`'s whole-directory byte comparison, `verify()`'s
restore-to-temp-and-compare, `_safe_join`'s second containment check on restore, and `restore()`'s
missing-file refusal were all checked and are consistent with their documented intent. No caps, no
silent failures, no tautological checks.

---

## roll.py (319 lines)

Nothing found as a DEFECT. Read in full. `mutate()`'s compare-and-swap (digest-before-read,
pid+thread+attempt temp names, re-read-and-reapply on contention) and `update_rows`'s `seen`
tracking (a row was found vs. a row was changed) are both already correct in the code as it
stands — the in-file comments describing prior bugs in these functions describe fixes already
landed, verified by reading the current code rather than assuming the comment.

QUESTION: `in_scope()` (line 70-79) deliberately fails OPEN — an unreadable `SWEEP_ROLL.json`
returns `True` (source stays in scope) rather than failing closed. This is explicitly documented
as a considered exception to house doctrine ("FAILS OPEN, deliberately and against house habit")
with a stated reason (an unreadable roll must not silently exclude the entire library). Not filed
as a defect since it is a reasoned, disclosed departure, not an oversight — flagged only so the
next reader can confirm the reasoning still holds rather than re-deriving it.

---

## scale_theories.py (216 lines)

Nothing found. Read in full. This module is confirmed-dead code by its own docstring and by
cross-reference (`liveness.py` lists `bulk_export_beta`, `growth_strike`, `penetration_pressure`
and `surviving_theory` as NEVER REACHED, and the module is held rather than wired or deleted for
stated reasons). `surviving_theory()`'s arity assertion (exactly one theory must have
`falsified: False`) is real logic, not a check that cannot fail — it is exercised by the
`THEORIES` dict having exactly one `"falsified": False` entry today, and would correctly raise if
that arithmetic changed. No caps, no silent failures.

---

## module_index.py (193 lines)

Nothing found. Read in full. `_modules()`'s recursive walk (fixed from a prior non-recursive-glob
defect per its own comment), the stale-group-name and duplicate-group-name checks, and the
gated atomic write via `silence.replace_retry` with a real non-zero exit code on denial, were all
checked and are consistent with the file's stated intent. No line-number citations to verify (this
file deliberately carries none of its own module count in prose, per its own docstring, for
exactly the staleness reason this sweep is checking for elsewhere).

---

## Summary

| Module | DEFECTs | QUESTIONs |
|---|---|---|
| pipeline.py | 3 | 3 |
| identity.py | 0 | 0 |
| feats_index.py | 0 | 1 |
| cleanup.py | 0 | 0 |
| snapshot.py | 0 | 0 |
| roll.py | 0 | 1 |
| scale_theories.py | 0 | 0 |
| module_index.py | 0 | 0 |
| **Total** | **3** | **5** |
