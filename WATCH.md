# OVERWATCH

round 468  ·  last run 2026-09-09 22:31

## Structure

- modules that will not import: **0**
- files that will not parse: **0** of 302,144 inspected (deep scan as of round 463)
- catalogued sources with no host: **7** Curious DM Investigations (the Sharkin), Genuine Fantasy Press (Forgotten Secrets), JMBrew, Kobold Press (Midgard Heroes Handbook, Midgard Worldbook), Super Energy Apocalypse 1 & 2, aurora_mods (Way of the Inkmaster), and 1 more
- on the roll but never catalogued: **6** HAWX, Heaven's Lost Property, Lost Mines of Phandelver, Twilight Imperium, major live-action Disney films, the Witch Tradition

## What the model found in the code

**29 open** (8 high). Newest first.

- **corpus_db.py** `main` — [HIGH] It skips the freshness check for --canned queries, leading to potential unhandled exceptions when the database file is missing
  - says: The code says it handles --canned queries safely
- **corpus_db.py** `rebuild` — [HIGH] Rebuilds the index but does not process JSON files correctly, leading to potential data loss or incorrect counts.
  - says: Rebuild the index from the canonical JSON. -> counts.
- **binding_health.py** `run` — [HIGH] Returns an empty list and 0 on an empty or unreadable hosts map, which contradicts the claim that it canary every bound host.
  - says: Canary every bound host. Error-resilient: one bad host never aborts the sweep.
- **magnitude.py** `verify` — [HIGH] Applies guards 1-3 but also handles status scores and fabricates provenance for empty citations
  - says: Apply guards 1-3. Returns (scores, worksheet, rejections).
- **endpoint.py** `register` — [HIGH] Attempts to write a temporary file without proper atomic operations, leading to potential data loss or corruption due to concurrent writes.
  - says: Record where a source's material actually lives.
- **overnight.py** `snap` — [HIGH] snap is updated with cycle and at information even when there's an error
  - says: A crashed snapshot carries ONLY an "error" key
- **read.py** `return done["errored"] == 0` — [HIGH] returns 0 if no errors occurred, but the exit code should reflect whether any errors occurred
  - says: THE EXIT CODE IS THE NUMBER A SCHEDULER ACTUALLY LOOKS AT
- **grounding.py** `silence.write_json` — [HIGH] writes JSON to the file and returns a boolean indicating success
  - says: uses to mean "this run did not do what it was asked"
- **burgs.py** `burg_link` — [MEDIUM] Generates a URL that includes the 'burg' parameter, which is supposed to be handled by Azgaar, but the function's implementation may not correctly reflect this if it's not using the correct parameters or if there's a misunderstanding in the URL construction.
  - says: The route to a settlement's own map: THROUGH Azgaar, not around it.
- **binding_health.py** `tight` — [MEDIUM] a fuzz ratio score between 0 and 100
  - says: the same pair judged as whole strings, and the distance between them is how one-sided the match is
- **binding_health.py** `containment` — [MEDIUM] a boolean indicating whether one set of words is a subset of the other
  - says: the strength of the evidence, not a second verdict. `containment` says one name's words sit wholly inside the other's, which is what `token_set_ratio` scores 100
- **binding_health.py** `binding_verdict` — [MEDIUM] Returns a verdict based on string similarity between the sitename and source names, but the function's purpose is to determine if the binding is correct or not, which is not directly related to the string similarity score.
  - says: Does the wiki's own name correspond to the source bound to it?
- **binding_health.py** `available` — [MEDIUM] passed in
  - says: UNMEASURED
- **binding_health.py** `PRESENT_CANDIDATES` — [MEDIUM] hardcoded value
  - says: bound
- **physics.py** `joules_for` — [MEDIUM] Energy to do `mode` to `volume_m3` of `material` with a default material of 'rock' and mode of 'pulv'.
  - says: Energy to do `mode` to `volume_m3` of `material`.
- **hosts.py** `discover` — [MEDIUM] Only keeps hosts that score well on LIFT, and discards others
  - says: Find every ADDITIONAL host each source can be read from, and keep all that hold.
- **verify_math.py** `phase_cosmology` — [MEDIUM] phase 5 does not refuse, but instead returns (False, False) as per the code
  - says: phase 5 REFUSES an unparseable WORLDSEEDS.json instead of re-addressing from nothing
- **verify_math.py** `verify_restore` — [MEDIUM] the function's call site is checked to ensure it uses the sandbox copy
  - says: protects a sandbox copy, not the three ledgers
- **overnight.py** `write_status` — [MEDIUM] Attempts to write a temporary file and replaces it with the new content, but the function's return value is not directly tied to the success of the file write operation as the function's name suggests.
  - says: Land STATUS.md. -> True if it landed, False if the replace was denied.
- **overnight.py** `CB.snapshot()` — [MEDIUM] raises exceptions which are caught and logged
  - says: NEVER RAISES
- **overnight.py** `CB.newest()` — [MEDIUM] uses the timestamp of the newest snapshot to determine if a backup is needed
  - says: RATE-LIMITED BY THE NEWEST SNAPSHOT'S OWN TIMESTAMP
- **overnight.py** `_cmd_is_running` — [MEDIUM] Checks if a command line fragment is being run by splitting and matching parts.
  - says: PURE. Does this command line show `fragment` BEING RUN, rather than merely mentioned?
- **overnight.py** `_cmd_tokens` — [MEDIUM] Returns split tokens of a command line, used to determine if a script is running.
  - says: Is the script on this command line THIS checkout's copy? -> bool.
- **health.py** `a.preflight` — [MEDIUM] used as a condition to trigger preflight checks
  - says: used to work only by coincidence of being the fall-through default
- **health.py** `silence.write_json` — [MEDIUM] write_json is called in a context where a return value of False indicates a denied write, but the code proceeds to return None when the write is denied
  - says: write_json returns False when the atomic replace is denied
- **health.py** `dump_kw.setdefault` — [MEDIUM] overriding the default for sort_keys
  - says: set default for sort_keys
- **feats.py** `known` — [MEDIUM] A CLEAN NEGATIVE IS CACHED, BUT A NULL IS ALSO CACHED (for a source that was never probed)
  - says: AND ONLY A CLEAN NEGATIVE MAY BE CACHED
- **feats.py** `known` — [MEDIUM] A NULL IS A CACHED FAILURE, BUT A NULL IS ALSO A CACHED ANSWER (for a source that was never probed)
  - says: A NULL IS A CACHED FAILURE, NOT AN ANSWER
- **feats.py** `alive` — [MEDIUM] Returns the first element of `alive_verdict` which is True if the wiki answered, but the function is not called anywhere, making it effectively unused.
  - says: Unchanged contract: True only when the wiki answered. See `alive_verdict` for the third answer, which every caller that CACHES a negative must ask for instead of this.

---

Written by `src/overwatch.py`. Structure is checked every round; the model reads modules that changed first, then whichever has gone longest unread. A finding stays open until the file it points at changes.
