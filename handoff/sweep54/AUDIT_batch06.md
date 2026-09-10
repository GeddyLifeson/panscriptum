# AUDIT — sweep run54, batch 06

Modules: `standards.py`, `allsweep.py`, `identity.py`, `feats_index.py`, `cleanup.py`,
`snapshot.py`, `roll.py`, `scale_theories.py`, `repass_bands.py`

All nine read in full, line by line (`standards.py` is 2,464 lines and was read in four
sequential chunks covering the whole file; the rest were read whole in one or two passes).
Where a finding cites a companion location inside another batch-06 file, that companion location
was also opened and read directly, not inferred. Two findings cite a companion location in
`catalogue_models.py`, which is **outside this batch** — those claims were left unfiled rather
than reported on the strength of a grep alone, per "if you did not verify it, do not file it."

---

## standards.py

Read whole (2,464 lines / four passes). This is the densest file in the batch: ~35 individually
try/excepted standards inside `check()`, each with a multi-paragraph docstring recording a prior
incident. Checked every `try/except` for a swallowed finding, every constant against its
docstring's claimed floor, and every internal line-number citation against the line it actually
names (the file cites itself repeatedly as precedent for its own repairs).

### MAJOR — a self-citation in `_flow_failure` points at a blank line, not the fix it claims
**Where:** src/standards.py:204 (citing "standards.py:604")
**What:** The docstring for the UNCLASSIFIED exception branch says: "A [:80] cut with no marker
on the one field that carries the cause is the same shape already repaired at `standards.py:604`
and `catalogue_models.py:130-138`."
**Why it is wrong:** Line 604 of the current file is a blank line between `model_matches()` and
`resident_context()` — it has nothing to do with a `[:80]`-cut repair. The comment is citing
evidence for its own claim that no longer exists where it says it does; a reader who goes to
verify the precedent finds nothing there.
**Confidence:** Read line 604 directly (`return a == b or a == b + ":latest" or ...` is at 603;
604 is blank). No candidate "[:80] cut" repair comment exists anywhere near it.

### MAJOR — two more self-citations in the COMPLETENESS.json block point at the wrong lines
**Where:** src/standards.py:1584-1586 (citing ":1671" and ":1742")
**What:** The comment above the `worst`-sources sort says this file "has already fixed the
identical shape twice, at :1671 ('ALL OF THEM, not [:120] characters...') and at :1742 ('EVERY
RESIDENT NAME... ranking is allowed here, truncating is not')."
**Why it is wrong:** Line 1671 is a blank line inside the "every running job is advancing" block
(`if os.path.exists(JOB_WATCH):` sits at 1668, `import lognames as LN` at 1672), and line 1742
is mid-comment inside the `job_stamp`/`silence.write_json` discussion of `JOB_WATCH`, not the
"EVERY RESIDENT NAME" text. The two comments this citation is actually pointing at do exist in
the file — "ALL OF THEM, not `[:120]`" is at line 1891, and "EVERY RESIDENT NAME, not
`resident[0][:28]`" is at line 1985 — roughly 200-300 lines downstream of where they are cited.
**Confidence:** Grepped the file for both phrases and read the citing lines and the real lines
directly; both drifted after later edits inserted code above them.

### MINOR — a dead branch in `read_progress_verdict`
**Where:** src/standards.py:503-510
**What:**
```python
if done <= 0 and total > 0:
    return False, "no chunk has completed", keep
if total <= 0:
    return None, (...), keep
if done <= 0:
    return False, "no chunk has completed", keep
```
**Why it is wrong:** The third `if done <= 0:` can never execute. Reaching it requires having
fallen through both earlier checks, which means `NOT(done<=0 and total>0)` AND `NOT(total<=0)`
hold simultaneously — i.e. `total>0` is established by the second check, and combined with the
negation of the first check that forces `done>0`. The docstring calls this "THE COLD START...
kept, because it was the one condition the old check could actually detect" — but it is already
fully handled by the first `if`, one statement earlier. This is a "check that cannot fail" in the
narrow, harmless sense: it changes no observable behaviour (the first branch already returns the
same tuple for the same case), so it is dead code rather than a wrong verdict.
**Confidence:** Traced the boolean algebra directly against the three guards as written; no
external state needed since `read_progress_verdict` is pure.

### Verified NOT a bug (recorded so the coordinator doesn't re-chase it)
`standards.py`'s "cached records that were fully read" standard (~line 1223-1250) reads only the
first 700 bytes of each `data/readfeats/**/*.json` file (`f.read(700)`) looking for
`"chunks_unanswered"`. This looked like a plausible false-positive risk (a record whose JSON puts
that key past byte 700 would be counted as if written "before the guard existed"). Measured
directly against 40 randomly sampled files across `data/readfeats/` (2,871 files on disk): the
key appears between byte 99 and byte 310 in every sample, comfortably inside the 700-byte window.
Not filed.

---

## allsweep.py

Read whole (1,014 lines). Checked the `Verifier`/`RC_BROKEN`/`RC_FINDINGS` table against each
verifier's own documented exit contract, the `NEVER_RUN` roster against modules actually walked
by `modules()`, the LINT-tier's pyflakes rc handling, and the whole `reconcile()` function's
seven independent comparisons.

No findings. The `RC_BROKEN` comment on `identity.py` ("identity.py returns 0 on every path it
can reach") was checked against `identity.py`'s own `main()` — both `return 0` statements are
confirmed, so the grading comment is accurate. `scale_theories`/`repass_bands` are correctly
listed together with `cleanup` in `NEVER_RUN`, consistent with what those three modules actually
do when invoked bare. One citation, `verify_math.py:6824-6825` (line 190), names a file outside
this batch and was not checked — flagging as unverified rather than filing it.

---

## identity.py

Read whole (753 lines). Checked the three structural tests in `_is_continuity` (orthography,
population, branching) against the `n == 0` impossibility claim, the cache-staleness logic in
`load()`, and `epoch_of()`'s three-way UNPROBED/absent/overlong handling.

No findings. `_is_continuity`'s claimed invariant ("n == 0 cannot occur; mine() only ever
populates bearers[desig] by adding at least one base name to it") was traced against `mine()`
directly: `bearers[desig].add(base)` is the only way a key enters the dict, so `len(b) >= 1`
always holds. `epoch_of()`'s distinction between "unprobed" (`_ask` returned None, or `_json`
parsed to `{}`) and a genuine "no marker" answer (`{"epoch": "", "explicit": False}`) is
correctly kept apart by testing dict truthiness before reading `.get("explicit")`.

---

## feats_index.py

Read whole (572 lines). Checked the `_norm`/join-key logic, `load_index`'s fault accounting,
and every module-level mutable cache (`_CACHE`, `_UNBOUND_ASKED`, `_ENTRY_COLLISIONS`) for a
reader.

### MAJOR (cross-file, verified) — a citation into standards.py names the wrong lines
**Where:** src/feats_index.py:162-164 (citing "standards.py:174-181")
**What:** The comment beside the `RuntimeError` in `host_to_sources()` says: "A hard [:110]
slice on the underlying exception text is Hard Rule 0's exact shape on a stored/reported
diagnostic -- the same one already repaired at standards.py:174-181..."
**Why it is wrong:** standards.py:174-181 is inside `_flow_failure`'s docstring, discussing
concurrent probes contending for the single-slot GPU runner — nothing about a character-cut
repair. The actual "UNCUT" repair this comment means to point at (the `[:80]`-cut discussion in
the same function) is at standards.py:198-207, roughly 24 lines further down.
**Confidence:** Read both the citing text and the cited line range directly in standards.py,
which is also in this batch.

*(A second citation two lines later — "catalogue_models.py's `provider_pool_denominator` [:40]
cut" — could not be checked: `provider_pool_denominator` is actually defined in **standards.py**
(line 673), not `catalogue_models.py`, but `catalogue_models.py` is outside this batch and may
independently contain its own similarly-shaped cut under a different name. Not filed — this
needs someone auditing `catalogue_models.py` to confirm or refute it.)*

### MINOR — `_ENTRY_COLLISIONS` is written once and read nowhere in `src/`
**Where:** src/feats_index.py:110, 390
**What:** `_ENTRY_COLLISIONS` is a module-level dict the docstring (lines 105-109) describes as
"Accumulated across calls rather than reset, so a caller that walks the roll ends holding the
whole picture." `feats_for_source()` writes into it at line 390 whenever a within-source name
collision is found.
**Why it is wrong:** Nothing reads it. `audit()` — the function the same docstring names as the
other consumer ("`audit()` reports the corpus-wide figure independently by rewalking the
records") — indeed does its own separate, independent computation of the identical figure a few
lines later, and never touches `_ENTRY_COLLISIONS`. Grepped the entire `src/` tree (not just this
batch) for any read of the name: zero hits outside its own declaration and its one write site.
Unlike its sibling `_UNBOUND_ASKED`, which has a public `unbound_asked()` accessor, this counter
has no accessor at all, so even a hypothetical external caller has no supported way to read it.
The mechanism the docstring describes is fully wired for writing and entirely unwired for
reading — a value computed and left on the floor.
**Confidence:** Grepped `src/**` for `_ENTRY_COLLISIONS`; only the declaration and the one
assignment appear anywhere in the tree.

---

## cleanup.py

Read whole (446 lines). This module documents (and appears to have already fixed) four separate
prior regex/truncation bugs in its own comments — the ruby-annotation question-mark eraser, the
ruby-parenthetical eraser, the ceiling-prefix ambiguity guess, and the thin-description
re-marking loop. Re-derived each fix independently rather than trusting the comment:

- `_ruby_question_mark`: traced the backward paren-nesting scan by hand against
  `"(フランス, Furansu ? )"` and `"(and, uh, Hawkeye?)"` — the non-ASCII test correctly
  distinguishes them.
- `clean_ceiling`'s prefix branch: confirmed `len(low_pref) == 1` is required before returning a
  "prefix" match, and `len(low_pref) > 1` returns `(ce, "prefix-ambiguous")` rather than picking
  the shortest — matches the docstring's claim that the old shortest-wins guess was removed.
- The thin-description guard (`if args.apply and not e.get("thin_description")`) correctly
  scopes `changed = True` to the first time the flag is set, so a record whose only edit is a
  thin-description mark is not silently dropped on a later re-run (traced against the two other
  branches, which have no such re-fire risk because they flip `catalogued` off first).
- The `_BAD_CHARS`-style guard over `_NAV`, `_EMPTY_MECHANIC`, `PL._SETTING_META`, and every
  `_MARKUP` pattern (checking for `ord(c) < 32` in each pattern's source) covers every regex
  actually used in this module; none were missed from the roster.

No findings.

---

## snapshot.py

Read whole (377 lines). Checked the containment logic end to end: `_rel()`'s refusal of
out-of-tree paths, `_safe_join()`'s refusal of a manifest entry that resolves outside its base,
and `verify()`'s use of a temp directory plus `_dir_matches()` for a snapshotted directory (not
just a file).

No findings. Confirmed `_dir_matches` walks the **snapshot** side and checks both existence and
byte-identity on the restored side for every file beneath a snapshotted directory (not merely
`os.path.exists()` on the directory itself, which the docstring says was the old, silently-always-
passing check). Confirmed `before()` raises `SnapshotFailed` (rather than returning a falsy id)
on total failure, on a completely empty capture, and on a partial capture unless
`allow_missing=True` — and that `requested`/`skipped` are recorded in the manifest on every path,
including the ones that raise.

---

## roll.py

Read whole (319 lines). Checked `mutate()`'s compare-and-swap (digest-before-read, re-read and
re-apply on contention rather than blind retry), `update_rows()`'s `seen` tracking, and
`exclude()`'s two return paths.

No findings, one already-self-documented residual: `exclude()` is explicitly called out in its
own comment (lines 260-296) as the one roll-writer **not yet** moved onto `mutate()`'s
compare-and-swap, with the reason (a pinned literal in `handoff/run35/checks_L4.py`, outside this
batch and this shift's ownership) and the exact follow-up patch spelled out. Confirmed this
function currently has zero callers anywhere in `src/` (only `drill.py`'s test harness calls it,
against a repointed throwaway file) — matching the comment's own claim, so the residual
lost-update window it describes is real but not live today. Not re-filed as a new finding since
it is already tracked in the source with more detail than an audit line could add; noted here so
the coordinator doesn't need to re-discover it.

---

## scale_theories.py

Read whole (216 lines). This module is explicitly documented (owner ruling 2026-09-08, order
`01695fe3ef26`) as held/marked/never-wired — matches the brief's "much of it here is deliberate
and marked" carve-out. Confirmed the claim itself rather than taking it on faith: grepped all of
`src/` for `import scale_theories` / `from scale_theories` — zero hits, matching the docstring's
"Nothing in `src/` imports this module."

Checked `surviving_theory()`'s arity guard against `THEORIES`: exactly one entry
(`T3_BULK_EXPORT`) has `"falsified": False`, so `len(survivors) == 1` holds today and the
function returns without raising. No findings.

---

## repass_bands.py

Read whole (190 lines). Checked the demotion gate (`PL.valid_scale_note`), the write-gating on
`PL.write_record`'s return value, and the accounting of denied writes into the closing summary
and exit code.

### MINOR — undisclosed truncation of evidence/scale-note text in the console report
**Where:** src/repass_bands.py:53, 67, 69
**What:**
```python
demoted_sources.append((src, band, (syn.get("evidence") or "")[:70]))
...
kept_entries.append((src, e.get("name"), b, sn[:70]))
...
demoted_entries.append((src, e.get("name"), b, sn[:70]))
```
**Why it is wrong:** Each of these silently truncates the evidence/scale-note text to 70
characters with no ellipsis or "N more characters" marker, for the text printed to the console.
This is the exact undisclosed-cut shape that other files in this same codebase (`cleanup.py`'s
`_marked`-equivalent handling, `standards.py`'s `_marked()`/`SA._cut()` idiom, and this project's
own Hard Rule 0 doctrine) have been repeatedly repaired for elsewhere — a reader cannot tell a
70-character note from a longer one that got cut. It is lower severity than the list-truncation
findings this project usually flags because nothing is written to disk here (the full
`scale_note`/`evidence` strings on the record are untouched; only the printed report is short),
so no data is lost — but the report itself cannot be trusted to show the whole note when deciding
whether a demotion looks right.
**Confidence:** Read the three call sites directly; confirmed no marker is appended anywhere in
this file's print statements (`print(f"     [{b}] {str(n):<32}{sn}")`), unlike the comparable
lines in `cleanup.py` and `standards.py` which do append one.

---

## Summary of MAJOR findings

- standards.py:204 — self-citation "standards.py:604" points at a blank line
- standards.py:1584-1586 — self-citations ":1671"/":1742" point at unrelated lines (real text is
  at :1891 and :1985)
- feats_index.py:162 — citation "standards.py:174-181" points at unrelated text (real fix is at
  standards.py:198-207)

MINOR: 3 (standards.py dead branch in `read_progress_verdict`; feats_index.py's unread
`_ENTRY_COLLISIONS`; repass_bands.py's undisclosed 70-char report truncation)

INFO/unverified, not filed: the `catalogue_models.py`-side citation in feats_index.py (needs a
reader of that file to confirm); `verify_math.py:6824-6825` cited from allsweep.py (same reason);
roll.py's `exclude()` residual lost-update window (already tracked in-source, restated here only
for coordinator visibility).
