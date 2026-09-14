# OVERWATCH

round 509  ·  last run 2026-09-14 06:58

## Structure

- modules that will not import: **0**
- files that will not parse: **0** of 304,616 inspected (deep scan as of round 505)
- catalogued sources with no host: **7** Curious DM Investigations (the Sharkin), Genuine Fantasy Press (Forgotten Secrets), JMBrew, Kobold Press (Midgard Heroes Handbook, Midgard Worldbook), Super Energy Apocalypse 1 & 2, aurora_mods (Way of the Inkmaster), and 1 more
- on the roll but never catalogued: **6** HAWX, Heaven's Lost Property, Lost Mines of Phandelver, Twilight Imperium, major live-action Disney films, the Witch Tradition

## What the model found in the code

**13 open** (3 high). Newest first.

- **scout.py** `verify` — [HIGH] A page is judged against the first 25 names of the source
  - says: A page is judged against every name catalogued under the source
- **render.py** `containment_svg` — [HIGH] Generates an SVG with a caption that incorrectly states a span based on ids that are not actually used in the tree
  - says: A containment diagram: this node, and what it holds.
- **publish.py** `push` — [HIGH] push() returns a boolean indicating whether a push occurred, but does not raise or return PushHeld, which is supposed to be handled separately with a specific error handling block.
  - says: push() now has only two RETURN values, and both are honest ones: it landed, or there was nothing to land. The third outcome -- committed but held -- comes out as `PushHeld` and is caught below, where it prints and sets rc=1, because a held push reported as "no change to push" with rc=0 is this comment block's own rule broken one line further down the function.
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
- **read.py** `left` — [MEDIUM] calculated as the maximum of 0 and CHUNK_BUDGET minus done['chunks'], but the comment suggests it should represent an upper bound based on the total chunks that can be processed given the size of each chunk.
  - says: The honest denominator: every chunk the queue can produce at the size this run will use. An upper bound -- the mention and action filters remove some -- so the estimate is pessimistic rather than flattering, which is the right direction for a number anyone is going to plan a night around.
- **health.py** `return 1 if reopen_stranded(dry=not a.go) is None else 0` — [MEDIUM] return 1 if the result of reopen_stranded is None else 0
  - says: return 1 if the result of reopen_stranded is None else 0
- **feats.py** `main` — [MEDIUM] returns 0 or 1 based on the roll's success, but the comment claims it should follow the same pattern as `--hosts` and `resolve_hosts` which return 1 if _HOSTS_DENIED else 0 and exit nonzero on failure
  - says: the sibling branches in this same file already do it: `--hosts` twenty lines up returns `1 if _HOSTS_DENIED else 0`, and `resolve_hosts`'s own docstring promises "main() exits nonzero on it". `--roll` was the one place the pattern was never applied, even though `roll()` has always returned exactly the counters needed.

---

Written by `src/overwatch.py`. Structure is checked every round; the model reads modules that changed first, then whichever has gone longest unread. A finding stays open until the file it points at changes.
