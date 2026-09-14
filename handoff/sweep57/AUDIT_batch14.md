# Sweep57 batch14 audit

Modules: src/read.py, src/health.py, src/ledger_guard.py, src/gpu_lane.py, src/canon_backup.py,
src/render.py, src/style_audit.py, src/ledger.py, src/cachekey.py. All nine read in full,
top to bottom (read.py 1671 lines, health.py 1307 lines, both in two chunks; the other seven
in one shot each). Open work-order queue was pulled first (`workorders.open_orders()`, run
from repo root) and cross-checked against every candidate finding below.

Prior-audit note: `handoff/sweep56/` batches 04, 08, 11, 14 exist but were not re-read line by
line (out of scope for this batch's time budget); the one item the task text asked me to
specifically re-check against sweep56 batch08 (canon_backup.verify) is covered below.

---

## Preliminary note: `src/ledger.py` is not a tamper-evident ledger

The task brief asked me to check `ledger_guard.py` and `ledger.py` together for "tamper-evidence
gaps (a ledger whose chain can be rewritten or truncated undetected)". `src/ledger.py` is in fact
**"DE PRETIO — the Ledger Standard, formalised"** — the in-fiction omniversal currency/economy
module (gil/zenny/credits/caps conversion against the Assay's energy-anchored Standard unit). It
has nothing to do with append-only history, hash chains, or tamper evidence; that entire subject
lives solely in `ledger_guard.py`. Filing this as a QUESTION for whoever assigned batch scope,
not a code defect — the module itself is fine (see below). All tamper-evidence findings are
therefore under `ledger_guard.py` only.

---

## NEW findings

### DEFECT — ledger_guard.py:407-417 — the floor ratchet can silently absorb tolerated loss, defeating its own stated purpose

```python
try:
    floor_text = _read_floor_snapshot(n)
    if floor_text is None or (sum(_substantive_lines(text).values())
                               >= sum(_substantive_lines(floor_text).values())):
        ftmp = os.path.join(SNAPSHOT_DIR,
                            "%s.floor.%d.%d.tmp" % (flat, os.getpid(),
                                                     threading.get_ident()))
        os.makedirs(SNAPSHOT_DIR, exist_ok=True)
        with open(ftmp, "w", encoding="utf-8") as f:
            f.write(text)
        os.replace(ftmp, _floor_snapshot_path(n))
```

`check_since_floor()` exists (per its own extensive docstring, order 284db4af1db6) specifically
to close "the compounding hole `check_since_snapshot` cannot see": a sequence of pushes that
each lose ~4% of a ledger — each individually under `MAX_LOST_FRACTION` — would otherwise pass
`check_since_snapshot` every time because that check's baseline (`_snapshot_path`) is
overwritten with the ledger's own post-loss content on every seal. The floor snapshot is
supposed to be a monotonic peak that this compounding cannot erode.

But the ratchet condition that advances the floor (quoted above) compares only the **aggregate
count** of substantive lines (`sum(_substantive_lines(text).values())`), not whether the new
text actually retains the floor's specific content. `assert_intact()` calls
`check_since_floor(name)` (against the *old* floor) and only afterwards calls `seal()`, which
runs this ratchet. So the sequence per push is: (1) lose up to 5% of the old floor's distinct
lines — passes `check_since_floor` because it is under the tolerance: (2) `seal()` then compares
*total line count*, not *retained content*, against the old floor. Because `HANDOFF.md` is an
actively-growing history file, an ordinary push nearly always adds more new substantive lines
than it drops (that is what "newest on top" ordinary use looks like) — so the aggregate count
after even a genuinely lossy push is very likely to be `>=` the floor's count, and the floor
silently ratchets forward to the new, already-degraded text. The lost lines are now gone from
the floor **permanently**, and the next push's `check_since_floor` is measured against a floor
that has already quietly absorbed the previous loss.

Concretely: floor holds 26 distinct historical lines. A push drops one old line and adds two new
ones (28 kept from before minus 1, i.e. new total 27 substantive lines) — passes
`check_since_floor` (1/26 ≈ 3.8% < 5%) and `27 >= 26` so the floor is replaced with the new text,
which no longer contains the dropped line. Repeat over many pushes and an unbounded fraction of
the *original* peak content can be erased, each step individually tolerated and each step
re-basing the peak the next step is measured against — which is exactly the "individually-
tolerated losses ... compound[ing] past the ... truncation floor" failure mode
`check_since_floor`'s own docstring says it exists to catch, reappearing one level up inside the
mechanism meant to catch it. The property actually needed for a true peak-tracker is that the
new text be a (near-)superset of the floor's own multiset content, not merely that its total
volume not shrink — the same distinction `_lost_fraction`'s own sweep43-batch05 fix drew between
sets and multisets, not yet applied to the ratchet's advance condition.

Not found in the open queue under any order id (order 284db4af1db6, which introduced
`check_since_floor`, is not open — it appears to have been landed and closed as fixing the
original compounding hole; this is a residual gap in that same fix, not the original defect).
Severity: real but narrow — it only bites when a push's aggregate growth happens to offset its
own loss, which is the common case for a growing, actively-edited ledger rather than the rare
case, so this is worth a ruling rather than a silent leave-as-is.

### QUESTION — canon_backup.py:315-442 (`verify()`) — `ok` is hardcoded `True` even when a canonical file is confirmed GONE from the live tree

```python
def verify(path=None):
    ...
    gone = [r for r in recorded if r not in live]
    notes.append("archive intact, %d members" % len(inside))
    if changed: notes.append(...)
    else: notes.append("0 canonical files changed since the snapshot")
    if unreadable: notes.append(...)
    if added: notes.append(...)
    if gone:
        notes.append("%d canonical files present in the snapshot are GONE from the live tree: %s"
                     % (len(gone), ", ".join(sorted(gone))))
    return True, notes
```

This is exactly the item the task brief named as "raised as a question in sweep56 batch08" —
confirmed still present verbatim in the current source. `verify()`'s only early `return False`
paths are for archive corruption (`broken`), a missing manifest, or a member the manifest
records but the *archive* itself lacks (`absent`). A canonical file that the *manifest and
archive both agree existed* but that has since vanished entirely from the **live tree**
(`gone`) is appended as a note only; the function still returns `ok=True`. `main()`'s CLI prints
`VERIFY: ok` as the headline verdict with the notes below it — an operator or an automated
caller that checks only the boolean (which is exactly what a scheduled health check would do)
would see a clean pass while a canonical record file — the corpus itself, per this module's own
docstring ("`data/records/*.json` ... derived from nothing") — has disappeared from disk.

The docstring's stated philosophy ("Divergence is NOT a failure. The live tree moves constantly
... What this answers is ... which canonical files have changed") could be read as covering
`gone` deliberately (the live tree is allowed to diverge from a morning snapshot). But `gone` is
not an ordinary "changed" — it is the single most alarming state this function can observe (a
non-derivable, irreplaceable file has vanished), and the module's own comment on `gone`
elsewhere calls it "the single most actionable thing this module can tell anyone." Leaving `ok`
insensitive to it means the boolean contract disagrees with the module's own stated priorities.
Marking QUESTION rather than DEFECT because the docstring's "divergence is not a failure" framing
is a plausible deliberate design position — but it reads as exactly the kind of "check that
cannot fail [on the one condition that matters most]" this project's own doctrine warns about
repeatedly, and it was flagged once already (sweep56-batch08) without being turned into either a
work order or a documented ruling. Recommend a ruling: either `gone` should flip `ok` to `False`,
or the docstring should say explicitly why a vanished canonical file is not considered a verify
failure.

### DEFECT (likely same class as KNOWN(89503c58409f)/KNOWN(386c0d66e31e)) — read.py:232 — stale self-citation, off by ~104 lines

```python
# read_entity's chunk-selection filter (read.py:731) already falls back to the whole name
# for exactly this case; this is the same fallback, but phrase-bound rather than a raw
```

`read.py:731` today is inside `_chunk_key`'s docstring (the paragraph about `generic_dropped`
and cache keys), which has nothing to do with a "chunk-selection filter" or a "fallback to the
whole name." The code actually being pointed at — `read_entity`'s
`keys = [w.lower() for w in re.split(r"[^A-Za-z0-9]+", name) if len(w) > 3] or [name.lower()]`
(the `or [name.lower()]` *is* the whole-name fallback) — is at **read.py:835** in the current
file. Verified directly against both line numbers. This is the same defect *shape* the open
orders `89503c58409f` ("LINE_CITATIONS_IN_SRC_COMMENTS_HAVE_ROTTED_AT_SCALE", 60 sites across 30
modules) and `386c0d66e31e` ("STALE_LINE_CITATIONS_SWEEP54") already exist to track, but this
specific site (read.py:232 → read.py:731, should read read.py:835) was not confirmed against
either order's enumerated list within this batch's time budget, so it is reported here rather
than assumed already covered.

---

## KNOWN

### KNOWN(8b3f2911fa0c) / KNOWN(32eaec248adf) — health.py:726 — confirmed, no siblings found in this batch's modules

```python
out.append((f"{fam}: probed host did not answer", f"{host} ({klass})"))
```

Confirmed exactly as described in the task brief: `check_api_paths()` always headlines with
"probed host did not answer" regardless of `klass`, including when `klass` is `"answered without
a \`query\` block"` (i.e. the host DID answer, e.g. with an HTTP 403 that produced no JSON
`query` key) or any other non-`unknown`/`network` class. The headline collapses "nobody home"
and "somebody answered with something we can't use" into the same alarming sentence, even though
`why.get("why")`/`why.get("ok")` inside the same function already have the information to tell
them apart (the code sets `klass = "answered without a \`query\` block"` specifically for the
"ok but no query" case, then buries that distinction inside the parenthetical rather than the
headline). Matches the task's stated known orders `8b3f2911fa0c` (DANDWIKI_API_IS_403_BY_POLICY)
and `32eaec248adf` (PREFLIGHT_PROBLEM) exactly.

**Sibling search**: grepped `did not answer|unreachable|UNREACHABLE|no answer|not answer` across
all nine assigned modules. No other site in this batch reproduces the "headline says absence,
detail says otherwise" shape. Worth noting `render.py:_probe` (lines 273-288) gets this
distinction *right* as a point of contrast: it returns `"answered HTTP %d"` for a real HTTP error
response and reserves `"UNREACHABLE (...)"` for a genuine transport exception — the pattern
`check_api_paths` should arguably follow.

---

## Clean — nothing found

- **read.py** — Extremely heavily self-audited already (every major defect class in the file
  carries its own "found/fixed, order NNNN" comment: transport races, lost-update chunk-cache
  writes, Hard-Rule-0 caps on `priority()`/`--limit`/`--one`, NTFS case-folding collisions,
  stale token-budget arithmetic explicitly marked stale-but-harmless). No new fail-open-where-
  should-fail-closed, no new uncapped truncation, no new lost-update race found beyond what is
  already documented and fixed. `queue()`'s host-map read/retry and `_save_qcache` are read-heavy
  and single-writer-per-run in the way the file is actually invoked; no new race identified.
- **health.py** — Aside from the KNOWN item above, the ledger flush/CAS logic
  (`_flush_ledger`, `_flush_samples`) is a correct compare-and-swap with proper re-read-and-remerge
  on refusal; `preflight()`'s stamp-write failure is itself checked and reported (not a
  check-that-cannot-fail). `check_caches`' quarantine/exclusion logic fails closed on every
  read failure. Nothing new found beyond the read.py:232 stale citation noted above (which is a
  read.py issue, listed under NEW findings, not a health.py one).
- **gpu_lane.py** — Deliberately, explicitly fail-open by design (documented rationale: an
  arbitration lane that can deadlock nine standing jobs is worse than no lane), which is a
  considered exception to the house FAIL CLOSED rule rather than an oversight — the module's own
  header states and defends this explicitly, and it is a resource-scheduling lane, not a safety
  gate. `_alive()`'s Windows-specific PID check, the slot/claim lease reclaim logic, and the
  heartbeat thread are all correctly bounded and already carry fix history for the exact races
  (stale env parsing, un-refreshed leases, `_touch` resurrection) an adversarial read would look
  for. Nothing new found.
- **canon_backup.py** — Aside from the QUESTION above, `members()`/`snapshot()`/`prune()`/
  `restore()` are uncapped, verify-by-readback, atomic-write-with-checked-verdict throughout,
  each carrying its own "found and fixed" history for exactly the failure classes the task asked
  about (checks that cannot fail, silent write-verdict discarding, orphaned scratch files).
  Nothing else new found.
- **render.py** — `children_of()`'s coordinate-completeness guard (refuses a partial coordinate
  outright, order 3270e0172391/3b422bc17939) and `write_views()`'s atomic per-file write with
  checked verdict are both sound. No caps, no silent failures, no stale citations found beyond
  what is already noted as fixed in-line.
- **style_audit.py** — `TURN_ENDING`'s anchor-at-`\Z` fix and the `--self-test`'s asserted-by-
  name-and-count fixtures (with an explicit negative control) close the two "check that cannot
  fail" classes this file previously had. All four rankings in `report()` are either uncapped or
  disclose their cut via `_cut()`. Nothing new found.
- **ledger.py** — Not a tamper-evident ledger (see note above); as the DE PRETIO currency module
  it is self-consistent, its one piece of "dead" code (`STANDARD_GLYPH`, `CONDENSATES`) is
  reported-dead-not-deleted per an explicit owner ruling (order 1a9c237dda4d), and its M10
  band-edge handling is already fixed and explained (order 5082a529e937). Nothing found.
- **cachekey.py** — `owns()`/`load()`/`write_path()` are exactly the verify-before-trust pattern
  the rest of the tree is being pushed toward; every function here has documented callers per its
  own module docstring. No caps, no silent failures, no stale citations. Nothing found.

---

## Coverage recorded

```
C:/Users/imarl/miniconda3/python.exe -c "import sys; sys.path.insert(0,'src'); import sweep_plan; print(sweep_plan.record('run57', ['read.py','health.py','ledger_guard.py','gpu_lane.py','canon_backup.py','render.py','style_audit.py','ledger.py','cachekey.py'], batch=14))"
```
(see terminal output for this session for the exact return value)
