# OVERWATCH

round 425  ·  last run 2026-09-07 16:53

## Structure

- modules that will not import: **0**
- files that will not parse: **0** of 299,182 inspected (deep scan as of round 421)
- catalogued sources with no host: **7** Curious DM Investigations (the Sharkin), Genuine Fantasy Press (Forgotten Secrets), JMBrew, Kobold Press (Midgard Heroes Handbook, Midgard Worldbook), Super Energy Apocalypse 1 & 2, aurora_mods (Way of the Inkmaster), and 1 more
- on the roll but never catalogued: **6** HAWX, Heaven's Lost Property, Lost Mines of Phandelver, Twilight Imperium, major live-action Disney films, the Witch Tradition
- NOT RUNNING: **0** autostart.py

## What the model found in the code

**18 open** (6 high). Newest first.

- **workorders.py** `resolve_code` — [HIGH] files when healthy, resolves when not
  - says: resolves; NOT healthy files
- **workorders.py** `resolve` — [HIGH] Closes an order by updating its resolution in the open file without removing it, and does not append to the paper trail as described.
  - says: Close an order: REMOVE it from the open file, append it to the paper trail.
- **wiki_source.py** `all_categories` — [HIGH] A FAILED WALK IS RETURNED AS THE ANSWER
  - says: A FAILED WALK RAISES; IT IS NEVER RETURNED AS THE ANSWER, MEMOISED OR NOT
- **verify_math.py** `path` — [HIGH] is read from the entire module, not the function's scope
  - says: is scoped to the function
- **verify_math.py** `call_idxs` — [HIGH] was deleted due to a conditional check that no longer exists
  - says: finds the call site of verify_restore
- **verify_math.py** `A._interval` — [HIGH] the code inverts the guard, which turns the one safe case into the crash case and vice versa
  - says: Between-hand dispersion is only defined for MORE THAN ONE reading
- **worldseed.py** `build_all` — [MEDIUM] build_all is not properly handling the case where the ONOMASTICON file is empty or malformed, leading to incorrect state in LAST_BUILD and potential misreporting of errors
  - says: build_all is supposed to read and process the ONOMASTICON and CONTINUITY_GROUPS JSON files, handling errors and reporting issues
- **workorders.py** `want` — [MEDIUM] want is checked against LADDER, but if invalid, it still proceeds to print the entire queue instead of refusing
  - says: want not in LADDER causes a refusal message and return 2
- **workorders.py** `shown` — [MEDIUM] shown is set to LADDER (show everything) by default, and only set to [want] if a.handler is valid
  - says: An unknown rung REFUSES rather than falling back to "show everything"
- **workorders.py** `BATTERY_CODES` — [MEDIUM] codes that the battery checks, but the battery does not check all codes
  - says: codes that the battery checks
- **workorders.py** `closed` — [MEDIUM] tracks closed codes, but the code is not closed when it should be
  - says: tracks closed codes
- **workorders.py** `resolve_code` — [MEDIUM] resolves a code to a resolution, but the code is not closed when it should be
  - says: resolves a code to a resolution
- **workorders.py** `filed.append` — [MEDIUM] appends to the filed list, which is then filtered by [f for f in filed if f] at the end of the function
  - says: COUNTED, like every sibling section. This block's `filed` results used to be discarded, so `swept: N filed/refreshed` under-reported by exactly the number of binding orders -- and the None a REFUSED queue write returns went the same way, so a finding that never reached the file could not be told from one that did. Both directions are the same fault: a sweep reporting on work it did not verify. The `[f for f in filed if f]` at the end of this function drops the Nones.
- **workorders.py** `filed` — [MEDIUM] defined in the same block
  - says: used but never defined
- **withdraw_chapters.py** `main` — [MEDIUM] Exits 1 if --go and any refusal condition is met, else 0
  - says: Every refusal above was printed and discarded; exit 0 unconditionally
- **withdraw_chapters.py** `silence.write_json` — [MEDIUM] The code writes a merged manifest that combines existing entries with new withdrawals, but the comment suggests it should keep the selection (withdrawn) rather than merge.
  - says: The withdrawn catalog is the record of WHAT was withdrawn; keep it beside the files.
- **withdraw_chapters.py** `claimed_raw` — [MEDIUM] a set of filenames from the catalog's raw_path entries
  - says: Anything left in output/raw that the catalog never claimed -- the pilot's strays.
- **weave.py** `pair_weights` — [MEDIUM] Summed idf of everything each source-pair shares, but with no cap on the contribution of each entity, which can lead to overcounting.
  - says: Summed idf of everything each source-pair shares.

---

Written by `src/overwatch.py`. Structure is checked every round; the model reads modules that changed first, then whichever has gone longest unread. A finding stays open until the file it points at changes.
