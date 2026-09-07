# OVERWATCH

round 424  ·  last run 2026-09-07 16:05

## Structure

- modules that will not import: **0**
- files that will not parse: **0** of 299,182 inspected (deep scan as of round 421)
- catalogued sources with no host: **7** Curious DM Investigations (the Sharkin), Genuine Fantasy Press (Forgotten Secrets), JMBrew, Kobold Press (Midgard Heroes Handbook, Midgard Worldbook), Super Energy Apocalypse 1 & 2, aurora_mods (Way of the Inkmaster), and 1 more
- on the roll but never catalogued: **6** HAWX, Heaven's Lost Property, Lost Mines of Phandelver, Twilight Imperium, major live-action Disney films, the Witch Tradition
- NOT RUNNING: **0** autostart.py

## What the model found in the code

**12 open** (5 high). Newest first.

- **wiki_source.py** `all_categories` — [HIGH] A FAILED WALK IS RETURNED AS THE ANSWER
  - says: A FAILED WALK RAISES; IT IS NEVER RETURNED AS THE ANSWER, MEMOISED OR NOT
- **verify_math.py** `path` — [HIGH] is read from the entire module, not the function's scope
  - says: is scoped to the function
- **verify_math.py** `call_idxs` — [HIGH] was deleted due to a conditional check that no longer exists
  - says: finds the call site of verify_restore
- **verify_math.py** `A._interval` — [HIGH] the code inverts the guard, which turns the one safe case into the crash case and vice versa
  - says: Between-hand dispersion is only defined for MORE THAN ONE reading
- **verify_math.py** `_chunk_key` — [HIGH] produces the same key for entities reading the same passage
  - says: two entities reading the SAME passage get different cache keys
- **withdraw_chapters.py** `main` — [MEDIUM] Exits 1 if --go and any refusal condition is met, else 0
  - says: Every refusal above was printed and discarded; exit 0 unconditionally
- **withdraw_chapters.py** `silence.write_json` — [MEDIUM] The code writes a merged manifest that combines existing entries with new withdrawals, but the comment suggests it should keep the selection (withdrawn) rather than merge.
  - says: The withdrawn catalog is the record of WHAT was withdrawn; keep it beside the files.
- **withdraw_chapters.py** `claimed_raw` — [MEDIUM] a set of filenames from the catalog's raw_path entries
  - says: Anything left in output/raw that the catalog never claimed -- the pilot's strays.
- **weave.py** `pair_weights` — [MEDIUM] Summed idf of everything each source-pair shares, but with no cap on the contribution of each entity, which can lead to overcounting.
  - says: Summed idf of everything each source-pair shares.
- **verify_math.py** `_ALL_SRC` — [MEDIUM] list of all .py files in the current directory (not necessarily the src directory)
  - says: list of all .py files in the src directory
- **verify_math.py** `_pool19ai` — [MEDIUM] Returns a mock object when the standard is absent, but the code around it expects it to return a real standard or raise an error
  - says: Run the real standards.check() over a synthetic throughput window.
- **verify_math.py** `BG.HAMLET_FLOOR` — [MEDIUM] the value is re-spelt here instead of read from the module
  - says: the floor was RE-SPELT here rather than read, which is the "one spelling in one place" rule broken

---

Written by `src/overwatch.py`. Structure is checked every round; the model reads modules that changed first, then whichever has gone longest unread. A finding stays open until the file it points at changes.
