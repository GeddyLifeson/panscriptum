# OVERWATCH

round 508  ·  last run 2026-09-14 06:12

## Structure

- modules that will not import: **0**
- files that will not parse: **0** of 304,616 inspected (deep scan as of round 505)
- catalogued sources with no host: **7** Curious DM Investigations (the Sharkin), Genuine Fantasy Press (Forgotten Secrets), JMBrew, Kobold Press (Midgard Heroes Handbook, Midgard Worldbook), Super Energy Apocalypse 1 & 2, aurora_mods (Way of the Inkmaster), and 1 more
- on the roll but never catalogued: **6** HAWX, Heaven's Lost Property, Lost Mines of Phandelver, Twilight Imperium, major live-action Disney films, the Witch Tradition

## What the model found in the code

**16 open** (4 high). Newest first.

- **render.py** `containment_svg` — [HIGH] Generates an SVG with a caption that incorrectly states a span based on ids that are not actually used in the tree
  - says: A containment diagram: this node, and what it holds.
- **publish.py** `push` — [HIGH] push() returns a boolean indicating whether a push occurred, but does not raise or return PushHeld, which is supposed to be handled separately with a specific error handling block.
  - says: push() now has only two RETURN values, and both are honest ones: it landed, or there was nothing to land. The third outcome -- committed but held -- comes out as `PushHeld` and is caught below, where it prints and sets rc=1, because a held push reported as "no change to push" with rc=0 is this comment block's own rule broken one line further down the function.
- **publish.py** `git` — [HIGH] The function is supposed to handle credential failures by removing specific environment variables, but the code does not actually remove the GITHUB_TOKEN and GH_TOKEN from the environment, which are the exact variables that should be excluded.
  - says: Two credential failures live in the environment, not the repo, and both are shed here.
- **publish.py** `_scrub` — [HIGH] scrubs values but not keys, and does not handle tuples or sets as described
  - says: refuses anything credential-shaped even if a future edit puts one in the state dict by accident
- **rosetta.py** `check` — [MEDIUM] The function 'check' is called with 'rosetta' and 'assays', but the actual implementation of 'check' is not provided in the given code slice. The code slice does not include the definition of 'check', so it's unclear what 'check' does. However, based on the context, it's expected that 'check' performs some validation or comparison between 'rosetta' and 'assays' based on the host information.
  - says: HOST-SCOPED, off ASSAYS.json's own `host|Name` keys (order 0bba50a6d76b): a scale row can only be vouched for by an assay recorded on that same wiki. This is also what makes the check match anything at all -- see check()'s docstring on the bare-name lookup that scored 0 overlap on all eight standing scales.
- **render.py** `view` — [MEDIUM] call view() for fetched tiers with map_seed and galaxy etc.
  - says: call view() for non-fetched tiers with coord=sample and tree=tree
- **render.py** `view` — [MEDIUM] call view() for non-fetched tiers with coord=sample and tree=tree
  - says: call view() for fetched tiers with map_seed and galaxy etc.
- **read.py** `left` — [MEDIUM] calculated as the maximum of 0 and CHUNK_BUDGET minus done['chunks'], but the comment suggests it should represent an upper bound based on the total chunks that can be processed given the size of each chunk.
  - says: The honest denominator: every chunk the queue can produce at the size this run will use. An upper bound -- the mention and action filters remove some -- so the estimate is pessimistic rather than flattering, which is the right direction for a number anyone is going to plan a night around.
- **read.py** `crate` — [MEDIUM] calculated as the difference in chunks divided by the time difference between the first and last entries in the rate log, but if the time difference is less than 1 second, it defaults to 0.0. However, if the calculated rate is <= 0, it is replaced with the total chunks divided by the maximum of the elapsed time and 1e-9.
  - says: A ROLLING RATE, because the queue opens with whatever is already cached and those entities complete in microseconds. Averaged from t0 they reported 1,595 chunks per second and an ETA of 0.0 hours for eight hours of work -- a number that is not merely wrong but reassuring, which is worse.
- **publish.py** `print` — [MEDIUM] prints a formatted string that may be clipped
  - says: PRINTED WHOLE, exactly as the PushHeld arm three lines above already is
- **publish.py** `token_env` — [MEDIUM] is assigned the value of `GUARD_TOKEN_ENV` if `token_env` is None, but the variable `token_env` is not defined in the scope where it's used in the function `token_matches`
  - says: defaults to `GUARD_TOKEN_ENV`; overridable only so a test can point this at a private variable instead of the real process environment.
- **publish.py** `prune_export` — [MEDIUM] Deletes files not in 'wanted' but also removes directories that are no longer in COPY_DIRS
  - says: Remove files not in 'wanted' from the export root
- **publish.py** `scan_for_secrets` — [MEDIUM] Reads files that are staged for publication, but the description implies it should read what is meant to be published, not what is about to be published.
  - says: LOCK THREE — read what is about to be PUBLISHED, not what we meant to publish.
- **publish.py** `_scan_units` — [MEDIUM] Yields segments of a file, but the line numbers and text may not accurately represent the original file's structure due to splitting long lines into overlapping segments.
  - says: Yield (line number, text) for every scannable piece of a file, at any size.
- **health.py** `return 1 if reopen_stranded(dry=not a.go) is None else 0` — [MEDIUM] return 1 if the result of reopen_stranded is None else 0
  - says: return 1 if the result of reopen_stranded is None else 0
- **feats.py** `main` — [MEDIUM] returns 0 or 1 based on the roll's success, but the comment claims it should follow the same pattern as `--hosts` and `resolve_hosts` which return 1 if _HOSTS_DENIED else 0 and exit nonzero on failure
  - says: the sibling branches in this same file already do it: `--hosts` twenty lines up returns `1 if _HOSTS_DENIED else 0`, and `resolve_hosts`'s own docstring promises "main() exits nonzero on it". `--roll` was the one place the pattern was never applied, even though `roll()` has always returned exactly the counters needed.

---

Written by `src/overwatch.py`. Structure is checked every round; the model reads modules that changed first, then whichever has gone longest unread. A finding stays open until the file it points at changes.
