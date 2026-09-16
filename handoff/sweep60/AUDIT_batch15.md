# sweep60 batch15 audit

Modules read in full, uncapped: `src/hostcheck.py` (1688 lines), `src/escalation.py` (1446
lines), `src/corpus_db.py` (1053 lines), `src/gpu_lane.py` (685 lines), `src/prose_gate.py` (541
lines), `src/sevenfold.py` (441 lines), `src/events.py` (350 lines), `src/roll.py` (313 lines).
Total 6,514 (+1 blank EOF) lines, all read start to finish, no sampling.

Given how many prior sweeps (references to sweep33/34/36/37/38/42/44/46/58/59, run #14-#59,
dozens of named `order <hex>` fixes) have already passed over every one of these files, most of
the obvious defects have plainly already been found and fixed. This audit therefore reports two
findings I am reasonably confident are still live, one self-acknowledged non-issue worth
recording for completeness, and an otherwise clean read of the remaining six files.

---

## FINDING 1 (HIGH confidence, HIGH severity) — `src/hostcheck.py:206-207`, `_land_hosts()`

```python
202    for attempt in range(HOST_MERGE_ATTEMPTS):
203        # Digest BEFORE the read: anything landing between the two then fails the swap rather
204        # than passing on a copy that is already behind.
205        digest = silence.digest_of(F.HOSTS)
206        hosts = {}
207        if os.path.exists(F.HOSTS):
208            try:
209                with open(F.HOSTS, encoding="utf-8") as f:
210                    hosts = json.load(f)
211            except Exception:
212                # NEVER heal this one by starting empty. An empty host map reads downstream as
213                # "no source has a wiki", which is how COMPLETENESS.json came to hold zero rows
214                # on 2026-08-24, and the file cannot be rebuilt from anything else on disk.
215                silence.note("hostcheck.py:hosts-unreadable")
216                return False, ("WIKI_HOSTS.json could not be read, so it cannot be merged into "
217                               "-- refusing to write. It is not reconstructible; fix the file.")
218        if not isinstance(hosts, dict):
219            silence.note("hostcheck.py:hosts-nondict")
220            return False, "WIKI_HOSTS.json is not an object; refusing to overwrite it"
```

**The bug.** The `except Exception` block explicitly refuses to proceed when
`data/WIKI_HOSTS.json` exists but will not parse ("NEVER heal this one by starting empty" —
comment in capitals, with a named incident: COMPLETENESS.json holding zero rows on 2026-08-24).
But that guard is only reached when `os.path.exists(F.HOSTS)` is **True**. When the file is
simply **absent** — `os.path.exists()` is False — line 206's `hosts = {}` is never overwritten,
`isinstance(hosts, dict)` at line 218 passes trivially (`{}` is a dict), and execution falls
straight through into the merge-and-write logic a few lines below, with no `silence.note`, no
refusal, and nothing distinguishing this from a legitimately-empty map. The function then writes
`data/WIKI_HOSTS.json` back out containing **only the keys touched by this pass's `merge` dict**.

This is the exact failure the adjacent comment says must never happen ("an empty host map reads
downstream as 'no source has a wiki'"), reached through the one path the comment doesn't guard.
`WIKI_HOSTS.json` is one of the two files this project's own docstrings call "confirmed not
reconstructible from anything else on disk" (this module's own header, line ~87-88, and
`_land_hosts`'s docstring at line ~136). `roll.py`'s parallel writer (`mutate()`, same tree,
line ~107) explicitly treats "unreadable OR absent" as the same refuse-to-write case for exactly
this class of file — "AN UNREADABLE OR ABSENT ROLL IS NOT WRITTEN OVER... 'we could not read it'
is not evidence of what it should contain" — and even cites a concrete precedent: the sibling
canonical file `SWEEP_ROLL.json` was destroyed twice on 2026-08-26 by a test harness. This
function does not apply that same standard to its own absent case.

**What triggers it.** The two public callers in this file (`sweep(repair=True)`,
`adopt(dry=False)`) each open `F.HOSTS` directly at their own top with a bare
`json.load(open(F.HOSTS, encoding="utf-8"))`, which would itself raise `FileNotFoundError`
immediately if the file were missing at call start — so under ordinary operation the file exists
when the pass begins. The gap is the **race window** between that initial read and this
function's own independent re-read inside its retry loop: `adopt()`'s docstring says its own
probe phase runs "eight threads... minutes, often much longer" before `_land_hosts` is reached.
If `data/WIKI_HOSTS.json` is deleted or moved out from under a long-running `adopt --go` or
`sweep --repair` pass in that window — by another process, a bad manual edit, or the kind of
test-harness mistake that has already destroyed the sibling `SWEEP_ROLL.json` file twice — this
function will silently write a near-empty host map over the real one instead of refusing.

**Verified by reading:** the full function body, its docstring, the two live callers'
call-then-later-write pattern, and the parallel (correct) handling in `roll.py::mutate()` for the
identically-critical `SWEEP_ROLL.json`.

**Suggested framing for the owner** (not a fix — this file is audit-only): the `if
os.path.exists(F.HOSTS):` guard should distinguish "absent" from "empty by design" the same way
`roll.mutate()` does, rather than letting absence silently satisfy the `isinstance(hosts, dict)`
check with an invented empty map.

---

## FINDING 2 (MEDIUM confidence, MEDIUM severity) — `src/prose_gate.py:538-539`, `unearned_instrument()`

```python
524def unearned_instrument(text, cited_names):
    """-> [entity names] that were given numeric axis scores without a single cited feat. ..."""
532    out = []
533    for b in _entry_blocks(text):
534        head = b.splitlines()[0] if b.splitlines() else ""
535        name = head.strip().strip("*").strip()
536        if not _AXIS_RE.search(b):
537            continue
538        base = re.sub(r"\s*\(.*", "", name).strip()
539        if name not in cited_names and base not in cited_names:
540            out.append(name or "(unnamed entry)")
541    return out
```

**The bug.** This is layer 4b, the "Assay honesty" veto that Hard Rule 3 requires: an entry that
carries a numeric axis score (`Wisdom: 28 ...`) must be dropped as fabricated unless its name is
in `cited_names` (the set of entity names that actually have mined, cited evidence — see
`cited_names_for()` just above it, which matches **exactly**, by design, "an entity must not be
credited with a neighbour's citations here of all places").

Line 538 computes `base`, the entry's headline name with any trailing parenthetical stripped
(`"Wally West (New Earth)"` -> `"Wally West"`), and line 539 only flags the entry as unearned if
**neither** the full name **nor** the stripped base is in `cited_names`. That means: if a
different, separately-catalogued entity that happens to share the same base name is cited
elsewhere (e.g. `"Wally West (Prime Earth)"` is cited, `"Wally West (New Earth)"` is not), a
fabricated axis score on the **uncited** variant passes this check, because its stripped base
string coincidentally collides with the cited one.

This directly contradicts the exact-match doctrine this same codebase states explicitly and at
length elsewhere in this very batch — `events.py`'s header (lines 9-16, 254-257): "T3 MUST JOIN
ON EVENT PARTICIPATION, NEVER ON NAME SIMILARITY... Joining 'Wally West (New Earth)' to 'Wally
West (Prime Earth)' is a *continuity* claim" — using precisely this pair of names as the
canonical example of two names that must never be treated as interchangeable. `unearned_instrument`
is a different module solving a different problem (fabrication detection, not thread-joining),
but the underlying hazard is the same: two catalogued entities that share a base name are not the
same entity, and evidence for one must not license a claim about the other.

No comment anywhere in `prose_gate.py` explains or justifies the `base` fallback — unusual for a
codebase where every other design choice in this file carries a paragraph of rationale
(`floor_ok`, `evidence_ok`, `_AXIS_RE`'s own adversarial-audit history, `cited_names_for`'s
`on_corrupt` trace). Its silent, undocumented presence next to an exhaustively-justified exact
name lookup reads like an unreviewed loosening rather than a deliberate decision.

**What triggers it.** Two catalogued entities in the corpus that reduce to the same base string
under `re.sub(r"\s*\(.*", "", name)` (a bare continuity/variant parenthetical strip), where one
has cited feats and the other does not, and a chapter block gives the **uncited** one a numeric
axis score. Given this corpus explicitly catalogues continuity variants with exactly this naming
convention (the Wally West / New Earth / Prime Earth example is drawn from this project's own
docs), the precondition is plausible rather than contrived.

**Verified by reading:** `unearned_instrument`, `cited_names_for` (confirms `cited_names` is
built from exact-string cache lookups only), and `events.py`'s explicit doctrine on this exact
naming pattern. Not runtime-tested against the live corpus, so I cannot confirm a live collision
exists today — flagged as a real gap in the check's logic regardless of whether it has fired yet.

---

## Lower-confidence / informational item

**`src/sevenfold.py:377`**, inside `main()`:
```python
377        ok = "OK" if hi <= SPAN else "OVER SPAN"
```
This is a textbook "check that cannot fail" (category 1 of this sweep's brief): `hi` is the max
over `seams()`'s own child counts, and `seams()` clamps every split to `k = max(1, min(span,
len(block)))`, so `hi <= SPAN` always holds and `"OVER SPAN"` is unreachable from any input.
**Not reporting this as a new finding** — the code's own comment three lines above (373-376)
already says so explicitly: "`seams()` already clamps every child count to SPAN, so 'OVER SPAN'
cannot print for any input. This displays a GUARANTEE, not a discovery... It becomes a real check
only if seams() ever stops clamping." Recorded here only to confirm it was seen and evaluated:
it is a deliberate, self-documented display choice, not a hidden defect, and matches the
project's own stated exception ("kept because it states the bound where a reader looks for it").

---

## Files read with no findings

**`src/escalation.py`** (the chain of command / halt machinery) — read in full with particular
care per the brief. Traced every fail-open/fail-closed branch: `_halt_lock()` (deliberately fails
open, per an explicit owner ruling, and only ever *removes* a race, never adds a refusal);
`_read_halt_raw()` / `_read_stopped()` (both correctly fail closed — unreadable, wrong-shape, or
`null` all read as halted/stopped, never as clear); `_land_halt()`'s handling of an existing
`_unreadable_halt()` stand-in (a new OWNER fault appends to and replaces the corrupt file with a
valid one that still names the original unreadable-halt condition as the top fault — preserves
rather than discards the original alarm); `escalate()`'s level-coercion logic for strings,
out-of-range ints, and non-integral floats (each malformed input lands at MANAGER with the bad
value preserved in evidence, never silently truncates to a different real rung); `clear()` and
`resume_subsystem_verdict()`'s person-and-ruling gates (`_by_a_person_at_the_cli()` correctly
requires *both* that `__main__` is this file *and* that the immediate caller frame is this file's
own `main()`, for both of its two call sites — the docstring at line 1165 only narrates the
`clear()` call site by name, but the check is structurally identical and correct for the
`resume_subsystem_verdict()` call site too, so this is at most a stale comment, not a functional
gap). All halt/stop file writes are compare-and-swapped with digest-before-read ordering and
readback verification. No tautological check, no fail-open gap, and no dead code found.

**`src/corpus_db.py`** — the derived SQLite index. `freshness()`, `drift()`, `rebuild()`'s
partial-read accounting (records, evidence, spine lookups, host/coverage lookup failures) all
correctly propagate "could not measure" as a distinct state from "measured zero," and none of the
sentinel values (`SPINE_LOOKUP_FAILED`, `HOST_LOOKUP_FAILED`) can be confused with real data by
type or by the CANNED queries' own WHERE clauses. `age_seconds()` is explicitly self-documented
dead-in-practice code, not a hidden finding. No caps found on any listing.

**`src/gpu_lane.py`** — the cross-process model-call arbiter. Every fail-open path (`_slot_count`,
`_take_slot`'s three-valued return, `_alive`'s Windows `OpenProcess` logic, `_touch`'s
never-resurrect guard, `lane()`'s priority/queue/heartbeat sequencing) matches its extensive
documentation and behaves as described on inspection. No bug found.

**`src/events.py`** — the Chronicle event-spine parser. Exact-string, no-fuzzy-match discipline is
upheld throughout (`_fragments`, `parse`'s bold-span handling, `shelf_positions`). No cap, no
tautology, no dead code found.

**`src/roll.py`** — the Acquisitions Roll / out-of-scope gate. `mutate()`'s CAS loop, `exclude()`'s
required-reason and caller-supplied-rows handling, and `in_scope()`'s fail-open-by-design
behaviour (documented and deliberate: an unreadable roll must not read as "everything excluded")
all check out. One item is already self-documented by the code itself as a latent, unexploited
defect and not something this audit is claiming credit for finding: `update_rows()`'s inner
`_apply()` (around line 195) has a comment acknowledging that `seen.add(name)` sitting outside the
`if ch:` check means a caller passing an existing source name with an *empty* change dict would
be misreported via `missed` as a row that no longer exists — the code says plainly "Not observed
to trigger today... The logic is wrong independently of whether a live caller hits it." Recorded
here only for completeness of the read; not counted as a new finding.

---

## Summary of findings by severity

- **HIGH**: 1 — `src/hostcheck.py:206-207`, `_land_hosts()` treats an absent `WIKI_HOSTS.json` as
  a fresh empty map instead of refusing, unlike its own handling of a corrupt one, on one of the
  project's two non-reconstructible files.
- **MEDIUM**: 1 — `src/prose_gate.py:538-539`, `unearned_instrument()`'s undocumented base-name
  (parenthetical-stripped) fallback can let a fabricated axis score on an uncited entity pass as
  earned if a same-base-name, differently-qualified entity is cited elsewhere — a resemblance
  match inside a check whose whole point is exact-match fabrication detection.
- **INFO**: 1 — `src/sevenfold.py:377`, a self-acknowledged tautological "OK"/"OVER SPAN" check;
  already documented in-code as deliberate, not newly discovered here.
- **Clean**: `src/escalation.py`, `src/corpus_db.py`, `src/gpu_lane.py`, `src/events.py`,
  `src/roll.py` (one already-self-documented latent item in `roll.py`, not counted as new).
