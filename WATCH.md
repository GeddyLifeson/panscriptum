# OVERWATCH

round 510  ·  last run 2026-09-14 07:31

## Structure

- modules that will not import: **0**
- files that will not parse: **0** of 304,616 inspected (deep scan as of round 505)
- catalogued sources with no host: **7** Curious DM Investigations (the Sharkin), Genuine Fantasy Press (Forgotten Secrets), JMBrew, Kobold Press (Midgard Heroes Handbook, Midgard Worldbook), Super Energy Apocalypse 1 & 2, aurora_mods (Way of the Inkmaster), and 1 more
- on the roll but never catalogued: **6** HAWX, Heaven's Lost Property, Lost Mines of Phandelver, Twilight Imperium, major live-action Disney films, the Witch Tradition

## What the model found in the code

**17 open** (8 high). Newest first.

- **standards.py** `bool(refs) and inside >= len(refs)` — [HIGH] the condition is based on the length of refs, which may not be the correct denominator
  - says: the assay reading is valid
- **standards.py** `unans_files` — [HIGH] unans_files is initialized to 0 before the try block, and if any errors occur (like unreadable files or missing data directories), the count is not updated, leading to a cached zero value that is never corrected. This results in a false positive where the system believes there are no unanswered files, even when there are issues.
  - says: THIS ONE LEFT NO TRACE AT ALL (2026-08-28). `unans_files = 0` sat before the try and the only out.append sat after it, so a HIGH-severity evidence standard was emitted MET with an observed `0` in three separate unmeasurable cases
- **silence.py** `append_line` — [HIGH] Does not set O_BINARY flag on Windows, leading to CRLF line endings instead of LF
  - says: NOT BINARY. `os.open` without `O_BINARY` gives a TEXT-mode descriptor on Windows
- **silence.py** `append_line` — [HIGH] Implements a lock but does not handle the case where the lock cannot be acquired, leading to potential data corruption
  - says: NOT SERIALISED. Fixed by taking an OS-level lock on a sidecar for the duration of the write
- **silence.py** `append_line` — [HIGH] Appends a line but does not ensure atomicity on Windows due to lack of O_BINARY flag and lock handling
  - says: Append ONE line to a shared ledger without tearing it (m62).
- **silence.py** `audit` — [HIGH] audit() returns rows of handlers, but the function's name and purpose imply it should audit for silence, not collect handlers
  - says: audit(root=None)
- **scout.py** `verify` — [HIGH] A page is judged against the first 25 names of the source
  - says: A page is judged against every name catalogued under the source
- **render.py** `containment_svg` — [HIGH] Generates an SVG with a caption that incorrectly states a span based on ids that are not actually used in the tree
  - says: A containment diagram: this node, and what it holds.
- **scout.py** `order` — [MEDIUM] sorted by the number of sources and then by the time of last attempt
  - says: sorted by the number of sources
- **scout.py** `seen` — [MEDIUM] read the SCOUT_ATTEMPTS.json file but then used as a dictionary for tracking attempts
  - says: read the SCOUT_ATTEMPTS.json file
- **runguard.py** `claim` — [MEDIUM] Mints a per-claim secret, stores its digest in the record, and returns (ok, reason) as specified
  - says: Take the guard for `agent`, or refuse.
- **runguard.py** `holder_is_live` — [MEDIUM] Returns True for stale heartbeats and missing records, but not for cases where the holder is provably alive with a stale heartbeat
  - says: Is this record a predecessor that is still working?
- **rosetta.py** `check` — [MEDIUM] The function 'check' is called with 'rosetta' and 'assays', but the actual implementation of 'check' is not provided in the given code slice. The code slice does not include the definition of 'check', so it's unclear what 'check' does. However, based on the context, it's expected that 'check' performs some validation or comparison between 'rosetta' and 'assays' based on the host information.
  - says: HOST-SCOPED, off ASSAYS.json's own `host|Name` keys (order 0bba50a6d76b): a scale row can only be vouched for by an assay recorded on that same wiki. This is also what makes the check match anything at all -- see check()'s docstring on the bare-name lookup that scored 0 overlap on all eight standing scales.
- **render.py** `view` — [MEDIUM] call view() for fetched tiers with map_seed and galaxy etc.
  - says: call view() for non-fetched tiers with coord=sample and tree=tree
- **render.py** `view` — [MEDIUM] call view() for non-fetched tiers with coord=sample and tree=tree
  - says: call view() for fetched tiers with map_seed and galaxy etc.
- **health.py** `return 1 if reopen_stranded(dry=not a.go) is None else 0` — [MEDIUM] return 1 if the result of reopen_stranded is None else 0
  - says: return 1 if the result of reopen_stranded is None else 0
- **feats.py** `main` — [MEDIUM] returns 0 or 1 based on the roll's success, but the comment claims it should follow the same pattern as `--hosts` and `resolve_hosts` which return 1 if _HOSTS_DENIED else 0 and exit nonzero on failure
  - says: the sibling branches in this same file already do it: `--hosts` twenty lines up returns `1 if _HOSTS_DENIED else 0`, and `resolve_hosts`'s own docstring promises "main() exits nonzero on it". `--roll` was the one place the pattern was never applied, even though `roll()` has always returned exactly the counters needed.

---

Written by `src/overwatch.py`. Structure is checked every round; the model reads modules that changed first, then whichever has gone longest unread. A finding stays open until the file it points at changes.
