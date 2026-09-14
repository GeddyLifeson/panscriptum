# AUDIT batch05 — run56

Modules read in full, top to bottom: src/feats.py (2783 lines), src/allsweep.py (1013 lines),
src/thread_integrity.py (721 lines), src/autostart.py (564 lines), src/axis_correlation.py
(443 lines), src/sweep.py (374 lines), src/entity_match.py (310 lines), src/catalog.py
(167 lines).

Also ran `python -m pyflakes` over all eight modules directly (read-only) as a cross-check:
zero findings, consistent with allsweep's own LINT tier.

All eight files are unusually heavily self-documented, including extensive first-person
narration of past bugs and their fixes, order numbers, and owner rulings. Most of the classic
defect shapes this sweep looks for (fail-open on missing config, silent `except: pass`,
tautological checks, undisclosed caps) have already been found and fixed by prior passes, with
the fix and the incident narrated in the surrounding comment. The most productive line of
attack this batch was independently verifying the many `file.py:NNN` line citations these
comments make about *other* code (and about themselves) — and a real, recurring defect pattern
turned up there: comments that were correct when written have not been kept in sync with the
files they cite, including files inside this very batch correcting their own earlier stale
citations and introducing new wrong numbers in the same edit.

---

## DEFECT — feats.py: stale citation `magnitude.py:867` (appears twice)

**Location:** src/feats.py:1952 and src/feats.py:1972

```
1952:    that is the whole of order 73aacce08418. `by_axis` is the live one (magnitude.py:867);
...
1972:# magnitude.py:867 calls. It is kept as a WRAPPER over the shared predicate rather than as a
```

Both comments assert that `magnitude.py` calls `feats.by_axis` at line 867. Verified against
the actual file: `magnitude.py` has no call to `F.by_axis` anywhere near line 867 (that region
is inside the per-axis citation-scoring loop of `assay_entity`, unrelated). The real call site
is:

```
magnitude.py:935:        for ax, rows in F.by_axis(clean, page).items():
```

**Why it matters:** the comment is the sole piece of evidence for `axis_evidence`'s "no callers
repo-wide, `by_axis` is the live spelling" claim (order 73aacce08418), which is itself the
justification for keeping `axis_evidence` around as dead code rather than deleting it. The
underlying claim (by_axis is live, axis_evidence is dead) still checks out — I independently
grepped and confirmed `by_axis` has one caller (magnitude.py:935) and `axis_evidence` has zero —
so this is a pure citation-drift defect, not a live behavioural bug. But a future reader who
trusts the pinned line number to go find the call site will land in the wrong function.

**Confidence:** DEFECT (verified independently against magnitude.py; the numeric claim is wrong,
the underlying reasoning is not).

---

## DEFECT — allsweep.py: five stale cross-file line citations in one comment block

**Location:** src/allsweep.py:188, :267, :789, :926-927

1. Line 188: `` `verify_math.py:6824-6825` `` — the cited check
   (`any(argv == ["rosetta.py", "--check"] for _label, argv in allsweep.VERIFIERS)`) is not at
   6824-6825 (that region of verify_math.py is unrelated ledger/quiet-window code for a
   different section). The actual check is at **verify_math.py:9758-9759**:
   ```
   9758:check("[6e3e3e553fd5] allsweep.VERIFIERS now runs rosetta.py --check",
   9759:      any(argv == ["rosetta.py", "--check"] for _label, argv in _ALLx_b3.VERIFIERS), True,
   ```

2. Line 267: `` rosetta.py:618-624 `` — cited for "the exit code has to carry the verdict ...
   so nothing that gates on rc ... could ever learn a franchise's own published ordering
   disagreed with our Assay". That text is not at 618-624 (which is inside the per-host
   search/fetch error-splitting code). It is actually at **rosetta.py:776-782**:
   ```
   776:        # THE EXIT CODE HAS TO CARRY THE VERDICT, not just the printout. This used to
   777:        # `return 0` unconditionally, so nothing that gates on rc (a shell, allsweep's
   778:        # VERIFIERS, a scheduler) could ever learn a franchise's own published ordering
   779:        # disagreed with our Assay -- the one check this module exists for. ...
   ```

3. Line 789: `` overnight.py:1007-1015 `` — cited for the "code outside {0,1}, or rc=1 with none
   of the stdout that contract requires, CONTRADICTS the contract" predicate `preflight()` uses.
   Lines 1007-1015 of overnight.py are part of an unrelated comment about
   `foreman.restart_reader` killing `read.py --run`. The actual predicate is at
   **overnight.py:1287** (inside `preflight()`, which starts at line 1197):
   ```
   1287:    if r.returncode not in (0, 1) or (r.returncode == 1 and not fails):
   ```

4. Lines 926-927: `` `workorders.py:158` `` and `` `standards.py:1132` `` — cited as the places
   that respectively call a missing/unreadable ALLSWEEP.json "allsweep has left no result" and
   read it "for a standard". workorders.py:158 is inside the unrelated
   `BINDING_HEALTH_MAX_AGE` comment; the actual "allsweep has left no result" string is at
   **workorders.py:253**. standards.py:1132 is inside an unrelated style-prompt-sync check; the
   actual `data/ALLSWEEP.json` read is at **standards.py:1536** (and :1553).

**Why it matters:** these are all in one contiguous comment block explaining why `Verifier` is
an object rather than a plain 3-tuple / why VERIFY/LINT/ESTATE now feed the exit code — i.e.
exactly the kind of comment a future maintainer would use as a map to go verify the claim before
touching this file. Every one of the five pointers currently leads somewhere unrelated. The
underlying claims (that these checks/strings exist somewhere in the named file) all check out on
independent re-grep; only the line numbers are wrong. This reads as a codebase that has grown by
several thousand lines in verify_math.py and hundreds in the others since these comments were
written, with no pass keeping citations in sync.

**Confidence:** DEFECT (all five independently verified against the current files).

---

## DEFECT — sweep.py: comment that already tried to fix a stale citation introduces new wrong ones

**Location:** src/sweep.py:81-89 (comment above `def load(path):`)

```
84:    # deprecated/): `sweep.load` has no caller anywhere; the only references are verify_math's own
85:    # probes at 3358/3368/3374, and the battery is NOT counted as a reader. `sweep()`'s live read is
86:    # `cachekey.load` at :160. Kept because it is the one place the FileNotFoundError-is-normal
87:    # reasoning below is written down, and because deleting it would take that reasoning with it.
88:    # The docstring's stale claim about "the only call site (`:129`)" -- which named neither
89:    # `def sweep():` at :129 nor `cachekey.load` at :160 -- is corrected in the body.
```

This comment is explicitly *about* correcting a previously-stale line citation (the old
docstring claim `sweep.py:129`), and cites `src/verify_math.py`'s own note on that history. But:

- `def sweep():` really is at **sweep.py:160** — that part is correct.
- `cachekey.load(...)` is claimed to be at `:160` as well, in both line 86 and line 89. It is
  actually at **sweep.py:192**:
  ```
  192:                ev, _ = cachekey.load(F.CACHE, host, e["name"],
  ```
  Line 160 is `def sweep():` itself, not the `cachekey.load` call inside it.
- The claim that `verify_math`'s probes of `sweep.load` sit at **3358/3368/3374** is also wrong.
  Those verify_math.py lines are unrelated checks ("allsweep reads the shared roster instead of
  keeping its own" and the entrypass-prompt-count check). The actual `sweep.load` probes are at
  **verify_math.py:5554** (`check("a missing evidence cache returns None", _sw21.load(...))`)
  and **verify_math.py:5570** (`check("a CORRUPT cache still returns None", _sw21.load(_bad21),
  None)`), inside the block starting around verify_math.py:5519.

Confirming the irony: `verify_math.py` itself, in the comment immediately preceding those two
checks (verify_math.py:5522-5533), already documents that `sweep.load`'s own docstring "repeats
the same ':129' claim, which is that file's to correct, not this one's" — i.e. verify_math.py
had already flagged that sweep.py owed itself a fix here. The fix that landed (this comment)
corrected the `:129`/`def sweep():` half but put a wrong line number on the `cachekey.load` call
and copied forward (or introduced) wrong verify_math.py line numbers for the probes.

**Why it matters:** same class as the allsweep.py finding above — a citation trail a
maintainer would actually follow (verify_math.py explicitly says "go check sweep.py") that leads
nowhere useful on either end. Low behavioural risk (this is prose, not code — `sweep.load`
genuinely has no caller in src/, which I independently confirmed by grep, so the substantive
claim survives), but it is the second and third generation of the same drift in the same
sentence.

**Confidence:** DEFECT (independently verified against current sweep.py and verify_math.py).

---

## DEFECT — thread_integrity.py: stale self-citation `:188`

**Location:** src/thread_integrity.py:592-593

```
592:    # THE FOURTH LISTING. ASYMMETRIC-LAWFUL was the one remaining class whose per-pair detail
593:    # was computed at :188 and then discarded: main() itemised its three siblings and this one
```

The per-pair detail append for `ASYMMETRIC-LAWFUL` (`out["ASYMMETRIC-LAWFUL"] += 1;
detail["ASYMMETRIC-LAWFUL"].append((src, dst, excuse))`) is actually at
**thread_integrity.py:430-431**, inside `classify()`, not at line 188 (which today falls inside
`load_thread_graph`'s target-resolution loop, an unrelated function).

**Why it matters:** same drift pattern as the rest of this batch's findings — a self-reference
inside the same file that has not tracked edits made to the file since. Low severity (a reader
who doubts the number can just grep `ASYMMETRIC-LAWFUL` in the same file and find it
immediately, which is how I confirmed it), but it's the same shape of defect this sweep is
explicitly asked to catch, so it's recorded.

**Confidence:** DEFECT (independently verified against current thread_integrity.py).

---

## QUESTION — feats.py: `this module's own docstring at line 7` does not contain the referenced material

**Location:** src/feats.py:1758

```
1757:    # write "3,000 kili". The corpus form for the other one is "a power level of 5,000" (see
1758:    # this module's own docstring at line 7, and zfighters.py:302, :328, :365), which is
```

I checked feats.py's module docstring (lines 1-33) in full: it never says "a power level of
5,000" or discusses that phrasing at all (line 7 there reads "instrument somebody read, or a
defeat somebody suffered.") — that exact string only occurs at feats.py:1757 and :1791, both
inside this same comment block. The `zfighters.py:302, :328, :365` half of the citation is
correct — I checked, and those lines really do carry "power level of 5,000"-style examples.

I'm filing this as a QUESTION rather than a DEFECT because I can't rule out that the author
meant something looser by "this module's own docstring" (e.g. a much earlier draft of the
top-of-file docstring that did carry a Goku "power level of 5,000" example and was later
trimmed, with this citation never updated) — but as it reads today, following the citation to
"line 7" finds nothing supporting the claim.

**Confidence:** QUESTION.

---

## QUESTION — entity_match.py: threshold-ordering guard is a bare `assert`

**Location:** src/entity_match.py:195

```
195:assert 0.0 < WEAK < STRONG <= 1.0, "entity_match: STRONG/WEAK threshold ordering is broken"
```

The comment directly above (188-194) explains this exists specifically so "a future edit ever
moved STRONG below WEAK" would "fail loudly instead of silently" in a module whose whole purpose
is refusing over-confident identity merges. `assert` statements are stripped when Python is run
with `-O`/`PYTHONOPTIMIZE`, which would silently turn this loud check back into the same silent
misordering it was written to prevent — the same "check that cannot fail" shape this sweep is
asked to flag, except here the failure mode is "check that can be compiled away" rather than
"check that always passes". I don't know whether anything in this project's run configuration
(pythonw invocations, `-O`, `PYTHONOPTIMIZE=1` in a service wrapper, etc.) ever runs modules
optimized, so I'm not confident this is live risk — flagging as a QUESTION for whoever owns the
project's run configuration to confirm optimized mode is never used, or to convert this to a
`raise` if it might be.

**Confidence:** QUESTION.

---

## QUESTION — thread_integrity.py: `_floor_verdict`'s read-decide-write on the ratchet file has no compare-and-swap

**Location:** src/thread_integrity.py:209-266 (`_floor_verdict`)

The ASYMMETRIC-SUSPECT regression floor is read, compared, and (on a lower measurement)
rewritten via `silence.write_json`, which guarantees the *write itself* lands atomically or is
reported as denied — but there is no guard against two concurrent `thread_integrity.py`
processes (e.g. a manual run overlapping a scheduled sweep) each reading the same old floor,
each deciding independently to ratchet down (or one ratcheting while the other's `REGRESSED`
verdict was computed against the pre-ratchet bar), and the two writes racing. `silence.write_json`
protects the bytes on disk from corruption but not the read-then-decide logic from a stale read.
Given how carefully this same codebase treats read-modify-write races elsewhere (this exact
concern is the explicit subject of several comments in feats.py, e.g. `_COUNTS_LOCK`'s docstring
and the roll()/note_throttled() discussion of per-host locks), the absence of any such guard here
looks like it could be an oversight rather than an accepted risk — but this file is normally run
as a single subprocess once per sweep, so the practical exposure may be negligible. Filing as a
QUESTION rather than a DEFECT since I have no evidence this file is ever actually invoked
concurrently in this project's operation.

**Confidence:** QUESTION.

---

## Nothing found — clean read, no findings

- **src/autostart.py** — full read, no findings. The tri-state `supervisor_alive()`/`ON.running`
  handling, the start-budget in `watch()`, the temp+replace_retry idiom in `install()`/atomic
  write pattern, and the twin-watchdog fail-open are all consistent with their own documentation
  and with each other. No undisclosed caps, no bare swallows, no tautological checks found.
- **src/axis_correlation.py** — full read, no findings beyond the one confirmed-*accurate*
  citation checked above (`dashboard.py:77-80`, which does point at the right lines). The
  `rho()`/`widening()` fallback-and-announce logic, the `MIN_N` guard in `_pearson`, and the
  `write()`/`load()` gating are all internally consistent.
- **src/catalog.py** — full read, no findings. Exit codes, missing-catalog reporting, and the
  uncapped `missing` list are all as documented.
- **src/entity_match.py** — full read, no findings beyond the `assert` QUESTION above. The
  `qualifier_compatible` gate, `similarity()`'s difflib-vs-rapidfuzz reasoning, and
  `candidates()`'s reason-code contract were all checked against their own stated rationale and
  hold up; the module is currently uncalled anywhere in the tree (confirmed by its own header and
  not contradicted by anything I found), so none of this is live-wired yet.

No undisclosed truncation/`[:N]` slicing was found in any of the eight modules beyond slices that
are explicitly documented as bounded previews with the full data available elsewhere (e.g.
feats.py's `_show()` "first N of M (all of them are in the record)" preview rows, and sweep.py's
`--top` "DEEPEST EVIDENCE" table, which is an explicit CLI parameter, not a silent cap). No bare
`except: pass` swallows were found that are not explicitly marked "silence-exempt" with a stated
reason (feats.py:2054-2056 is the one such case, and it is documented). No tautological
assertions-on-constants or guards-on-undefined-names were found; `python -m pyflakes` over all
eight files independently confirms no undefined names.
