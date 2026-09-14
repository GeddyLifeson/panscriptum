# AUDIT batch04 — run56

Modules read in full, top to bottom: `src/mutate.py` (3197 lines), `src/catalogue_web.py` (785
lines), `src/gpu_lane.py` (685 lines), `src/withdraw_chapters.py` (519 lines), `src/hosts.py`
(396 lines), `src/catalogue_models.py` (339 lines), `src/resonance.py` (298 lines),
`src/lognames.py` (52 lines).

General note: every one of these files is heavily self-documented with "order <hash>" comments
narrating a prior defect and its fix. I read each comment before judging the code it explains,
per the task instructions, and did not re-file anything already disclosed and fixed in-file. The
findings below are things I could not find already disclosed, or that are disclosed but not
fully closed.

---

## DEFECT — stale line-number citation, `src/withdraw_chapters.py:511`

```
511:    # that matched nothing already raised SystemExit at :184 and never reaches here.
```
Actual text at line 511 (context lines 505-511):
```
    # Console output is not the machine-readable channel: this is a `--go` tool an operator or a
    # wrapper script runs, and rc 0 is the only thing a shell `&&`, a scheduled job or a keeper
    # restart looks at. Every printed line above is unchanged -- the rc is additive, and the
    # per-condition wording is still what a person reads. The dry-run path returns 0; a selector
    # that matched nothing already raised SystemExit at :184 and never reaches here.
    # Order b422c125e93e.
```
The `raise SystemExit(...)` for "part of that selection matches nothing in the catalog" is
actually at **line 209**, not line 184:
```
209:        raise SystemExit("part of that selection matches nothing in the catalog%s. Refusing to "
```
Line 184 in the current file is a comment line inside an unrelated block ("NAMING SOMETHING AND
WITHDRAWING NOTHING IS A TYPO, NOT A RESULT."). The citation has drifted, almost certainly
because lines were inserted above the raise (e.g. the `have_src`/`unknown_src`/`unknown_addr`
checks) after this trailing comment was written. This is a comment-accuracy defect only — the
code path itself is correct and I verified the actual guard does fire before this point — but it
is exactly the "stale line-number citation" class of finding the sweep is looking for, and a
future reader chasing `:184` to understand the guard will land on the wrong code.

Confidence: DEFECT (verified against current file content).

---

## DEFECT (medium confidence) — lost-update race on `data/SOURCE_HOSTS.json`, `src/hosts.py:114-145`

```python
114:def add(source, host, evidence=None, score=None):
...
128:    if not host or host == primary_host(source):
129:        return False
130:    data = _load(EXTRA, {})
131:    rows = data.setdefault(source, [])
132:    if any((r.get("host") if isinstance(r, dict) else r) == host for r in rows):
133:        return False
134:    rows.append({"host": host, "evidence": evidence, "score": score})
135:    # `silence.write_json`, not a fixed temp name plus a bare `os.replace`. SOURCE_HOSTS extras
136:    # are read live while `discover()` walks, the temp path was shared by every concurrent
137:    # writer, and an uncaught PermissionError from Norton's object lock took `discover()` down
138:    # mid-walk instead of reporting a denied write. ...
142:    if not silence.write_json(EXTRA, data, indent=1, ensure_ascii=False):
143:        silence.note("hosts.py:add-denied")
144:        return None
145:    return True
```
`add()` is a plain read-modify-write: it loads the *whole* `SOURCE_HOSTS.json` (line 130),
mutates an in-memory copy, and writes the whole document back (line 142). `silence.write_json`
(verified in `src/silence.py:773`) makes the individual write atomic and torn-write-proof — it
uses a pid+thread-qualified temp name and `os.replace` — but it performs no compare-and-swap
against what was read at line 130. Its docstring confirms this: "Returns True if the file
landed... Never raises on a denied replace" — nothing about detecting that the file changed
between the read and the write.

The comment at lines 135-141 shows the author was aware of "every concurrent writer" reading
and writing this same file — that was the motivation for switching from a bare temp name to
`silence.write_json`'s pid-qualified one — but that fix only prevents two writers' *temp files*
from colliding (a corruption hazard). It does not prevent this scenario: two processes each
call `add()` around the same time (e.g. two `--discover --only <different-subset>` runs, which
is a natural way to parallelise this exact workload per the project's own parallelism
convention); both read the same on-disk snapshot at line 130; both append their own host to
their own in-memory copy; whichever `write_json` lands second silently replaces the first's
addition with a copy of the document that never had it. Both writes report "landed"
successfully (`silence.write_json` returns True for both), so `add()` returns `True` (not
`None`) for the discovered-and-then-lost host, which is a different, quieter failure than the
"write denied" case (`None`) the docstring goes to some lengths to distinguish. The `lost` list
and `sys.stderr` escalation built for denied writes in `discover()` (reviewed and correct) does
not fire here, because from the caller's point of view the write succeeded.

This matches the audit brief's callout almost exactly: "writes must go through
`silence.write_json` / compare-and-swap helpers" — this write goes through `write_json` (which
covers torn-write safety) but not a compare-and-swap (which would be needed to close the
lost-update window). I did not find any lock or version check elsewhere in `hosts.py` guarding
concurrent `add()` calls across processes.

Severity note: the blast radius is bounded and self-healing in the same way write-denial already
is — a lost host is simply not recorded and would be rediscovered by a subsequent `--discover`
walk over the same source, not permanently corrupted data. I am filing this as a DEFECT rather
than a QUESTION because the mechanism is real and verifiable, but flagging the bounded severity
so the next reader can weigh it against the cost of adding a CAS layer (e.g.
`silence.replace_if_unchanged` with a digest taken at the same time as the line-130 read).

---

## QUESTION (low priority) — same read-modify-write shape on `state/MUTANTS_RULED_EQUIVALENT.json`, `src/mutate.py:1092` and `:1108`

```python
1070:def rule_equivalent(target, line, ruling, ruled_by="", path=RULED_EQUIVALENT):
...
1092:    entries = dict(ruled_equivalent(path))
1093:    entries[oid] = entry
1094:    _write_rulings(entries, path)
...
1098:def unrule_equivalent(target, line, path=RULED_EQUIVALENT):
...
1108:    entries = dict(ruled_equivalent(path))
1109:    if oid not in entries:
...
1111:    gone = entries.pop(oid)
1112:    _write_rulings(entries, path)
```
`_write_rulings` (line 1034) writes via `os.replace` after a temp-file write, which is
torn-write-safe but again not a compare-and-swap against the `ruled_equivalent(path)` read taken
a few lines above in each of these two functions. This is the identical shape to the hosts.py
finding above. I am filing it as a QUESTION rather than a DEFECT because `_write_rulings`'s own
docstring states plainly: "This is only ever called from the two human-driven CLI flags, never
from inside a mutation run" (`--rule-equivalent` / `--unrule`) — a person typing one CLI command
at a time is a much lower-probability race than two automated `--discover` subsets running in
parallel, and I could not find evidence this is ever invoked programmatically or concurrently.
Worth a second opinion on whether that's a safe-enough assumption to leave unguarded, given an
adjacent module (`hosts.py`, above) treats the identical shape as worth closing.

---

## Reviewed and found clean

**`src/lognames.py`** — nothing found. Pure constant definitions plus an `OWNER` dict; no logic
to break. The extensive header comments about `overnight.running()` fragment-matching are
consistent with the constants defined (`READ`, `ROLL`, `PIPELINE`, etc. all have distinct,
sufficiently-specific `OWNER` values).

**`src/resonance.py`** — nothing found beyond what the module's own docstring already discloses
(no production caller for `hodge_decompose`/`resonance_strength`; `incomparability_rate` is
exercised only by `verify_math.py`). Traced `hodge_decompose`'s Gauss-Seidel convergence logic,
the gauge-fix, the `no_evidence`/`converged` state machine, and `dominates()`/
`incomparability_rate()`'s UNMEASURED/TIED/INCOMPARABLE three-way split by hand against the
docstring's own worked examples; all matched. `resonance_strength()` correctly returns a
distinguishable "not in resonance" (0.0, false) rather than raising or defaulting to a
misleading positive.

**`src/catalogue_models.py`** — nothing found. Verified `sweep()`'s LISTED/EMPTY_LIST/
UNREACHABLE/UNCONFIGURED four-way outcome classification is exhaustive and that `live`,
`verified`, `unverified`, and the printed counts all agree with each other and with the
EMPTY_LIST-counts-as-verified fix described in the sweep42-batch14 comment. `LAST_WRITE_LANDED`
tri-state default (`None`) and `main()`'s `return 0 if LAST_WRITE_LANDED else 1` are consistent.
The write to `data/PROVIDER_MODELS.json` is a full deterministic recomputation each run (not a
merge of a prior read), so it carries no lost-update exposure the way `hosts.add()` does.

**`src/hosts.py`** — reviewed in full; only the one lost-update finding above. `_load()`'s
absent-vs-corrupt distinction (raises on corrupt, returns default only on `FileNotFoundError`)
is correctly fail-closed. `hosts_for()`'s `"pages:"/"doc:"` sentinel filter, `discover()`'s
per-source bound applying only to the speculative half of candidates (never the grounded half),
and the `_PROBE_FAILED` / `None` / `keep-list` three-way distinction in `work()` all check out
against their own commentary. Confirmed `work()`'s `if not res:` branch really is unreachable
(every path returns a 3-tuple) as its comment claims.

**`src/catalogue_web.py`** — nothing found beyond the one line-number citation checked (see
below). `MAX_PER_SOURCE`/`MAX_PER_CATEGORY`/`CATEGORY_SCAN_DEPTH` are genuinely `None` and the
import-time tripwire on `MAX_PER_SOURCE` fires correctly before any network work. Verified by
grep that `MAX_PER_CATEGORY`/`CATEGORY_SCAN_DEPTH` have no importers anywhere in `src/`, matching
the "reported dead, not deleted" comment. Traced `_singular()`'s three ordered rules against
every example in its own docstring; all correct, including the `-ss/-us/-is` and `-ies/-oes`
"leave intact" branches. `catalogue()` and `catalogue_composite()`'s provenance-tracking
(`first_cat`, `deduped`, `no_text`) and their note-building are internally consistent with each
other. `main()`'s exit-code logic (`return 1 if todo and tally["failed"] else 0`) correctly
distinguishes "nothing to do" from "did work, none failed" from "some/all failed". The
`catalogue_web.py:193` citation to `catalogue_codex.py:361, resync_roll.py:211` names files
outside this batch and was not verified (out of scope).

**`src/gpu_lane.py`** — nothing found. This module is unusually dense with prior-incident
commentary (m54/m55/M46-adjacent fixes); I traced the slot lifecycle (`_take_slot` →
`_touch`/`_heartbeat` → `_remove_retry`), the `False`/`None`/path three-way return of
`_take_slot` all the way through `lane()`'s queue loop, and the foreground refcount's
`_DEPTH_LOCK` nesting logic, and all matched their docstrings' claims. `_alive()`'s
Windows-specific `OpenProcess`/`GetExitCodeProcess` path correctly returns `False` only on
`ERROR_INVALID_PARAMETER` and fails toward "alive" on every other outcome, consistent with the
module's "FAIL OPEN, ALWAYS" mandate and the "unknown answers are treated as ALIVE" policy
stated for slot/claim staleness. `status()`'s `partial` flag is the only place in the module
that catches a bare `Exception` and it is deliberately called out as such in its own comment.
The `motoko/discord_bot.py:256-298` citation names a file outside this repository/batch and was
not verified.

**`src/mutate.py`** — read in full; only the one QUESTION above beyond what its own extensive
"order" commentary already discloses. This is the largest and most heavily self-audited file in
the batch (52 internal "order <hash>" citations). I specifically checked: the `CMP_SWAP` table's
ten `ast.cmpop` mappings against their negations (all correct); the O_EXCL-based
`_lock_acquire`/`_lock_release` token protocol (correct compare-then-clear-on-token pattern,
distinct from the hosts.py/rulings finding above because it uses `os.open(O_CREAT|O_EXCL)` for
mutual exclusion rather than a bare read-modify-write); the sandbox-vs-live-tree guard in
`_run_mutation` (correctly refuses `root == HERE`); the `base=None` refusal and `ungauged`-gate
refusal in `_run_mutation`; `hang_confirms_a_kill`'s double-reading protocol before scoring a
timeout as a kill; and `_mutations`'s per-occurrence, byte/column-aware AST-node location logic
(`_col`, `_spot`, `_between`, `_token_pos`) against the worked non-ASCII-column and
chained-comparison examples in its own docstring. All were internally consistent. Self-citation
`mutate.py:33` (used in a comment at line ~2397) was verified accurate. The
`escalation.py:409`/`assay.py:593`/`prose_gate.py:201`/`drill.py:4256`/`drill.py:9604`/
`verify_math.py:7990`/`verify_math.py:3639` citations all name files outside this batch and were
not verified.

**`src/withdraw_chapters.py`** — read in full; only the one stale citation above. Traced
`_file_state()`'s live/gone/unavailable three-way (stat, then directory-listing fallback,
distinguishing "positively absent" from "could not tell"); `_archive_name_free()`'s
FileNotFoundError-only "free" determination; the per-file (not per-entry) `stuck`/`entry_left`/
`amended` bookkeeping in the main withdrawal loop, including the partial-entry-left amendment
path; the dry-run vs `--go` parity of the `moved[sub]`/`extra` counters (both incremented outside
the `if a.go:` guard, by design — confirmed via the "(b) THE DRY RUN, ALWAYS" comment that this
symmetry is deliberate and not a bug: collisions and move failures both `continue` before
reaching the counter in both modes, so the preview and the real run count identically); and the
manifest-merge logic in `record_path`'s union-with-existing-file handling. The
`address_space.py:467-480` citation names a file outside this batch and was not verified.
