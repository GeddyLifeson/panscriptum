# OVERWATCH

round 252  ·  last run 2026-09-01 05:59

## Structure

- modules that will not import: **0**
- files that will not parse: **0** of 286,381 inspected (deep scan as of round 247)
- catalogued sources with no host: **8** Curious DM Investigations (the Sharkin), Genuine Fantasy Press (Forgotten Secrets), JMBrew, Kobold Press (Midgard Heroes Handbook, Midgard Worldbook), Super Energy Apocalypse 1 & 2, The Elements Beyond, and 2 more
- on the roll but never catalogued: **6** HAWX, Heaven's Lost Property, Lost Mines of Phandelver, Twilight Imperium, major live-action Disney films, the Witch Tradition
- NOT RUNNING: **0** autostart.py

## What the model found in the code

**23 open** (7 high). Newest first.

- **foreman.py** `clear_learned_caps` — [HIGH] it does instead
  - says: the code says it does
- **feats.py** `roll` — [HIGH] the return value of roll() is discarded and 0 is returned unconditionally
  - says: THE COUNTERS REACH THE EXIT CODE
- **feats.py** `extra` — [HIGH] is now a parameter that is checked for being numeric
  - says: was a cap on a ranked page list
- **escalation.py** `clear` — [HIGH] clear() is not called here and its behavior is not used in this code slice
  - says: clear() raises PermissionError for non-person callers
- **allsweep.py** `run_verifier` — [HIGH] the code does not call `run_verifier`
  - says: Run one verifier and PUBLISH ITS GRADE, not just its exit code.
- **allsweep.py** `check_import` — [HIGH] the code does not call `check_import`
  - says: Does it import, and does its CLI parse?
- **allsweep.py** `sweep_plan.modules()` — [HIGH] the code does not call `sweep_plan.modules()`
  - says: had (order f42c55355431). Both consumers below join `SRC` with the name plus `.py`
- **foreman.py** `lines_changed` — [MEDIUM] uses difflib to measure the actual content difference
  - says: measuring `abs(len(new) - len(old))` -- a net total
- **foreman.py** `lines_changed` — [MEDIUM] measures the number of lines changed, not the actual content difference
  - says: bounding how much of a function a model rewrite may touch
- **foreman.py** `frag` — [MEDIUM] a value from _LN.OWNER[_LN.READ], which is not the fragment for each managed job
  - says: the one fragment that identifies each managed job
- **feats.py** `_AXIS_ACT_RE` — [MEDIUM] compiles regex patterns for axis keywords but uses the same pattern for all axes
  - says: compiles regex patterns for axis keywords
- **feats.py** `val` — [MEDIUM] constructed by concatenating the mantissa and exponent, but the exponent is not properly parsed
  - says: value of the quantity
- **feats.py** `_QUANTITY` — [MEDIUM] matches regex patterns for physical quantities but does not tag them with the page
  - says: physical quantities, each tagged with the page it came from
- **escalation.py** `_read_halt_raw` — [MEDIUM] returns None when there is no halt file, but returns the fail-closed stand-in when the file exists but is unreadable
  - says: -> the halt record, None when there is no halt file, or the fail-closed stand-in.
- **dashboard.py** `codewatch.exit_if_stale` — [MEDIUM] Exits when the dashboard code has changed and is held still
  - says: Exits rc=17 on purpose when src/ has changed and held still
- **dashboard.py** `tick` — [MEDIUM] Does not handle errors properly when fetching state
  - says: Fetches and updates the dashboard state periodically
- **chain.py** `side_epoch` — [MEDIUM] returns (epoch, its own sentences' disagreement, whether anything probed) for one side, but the 'epoch' is the minimum of the unique epochs, which may not be the one that the side's sentences actually date to
  - says: -> (epoch, its own sentences' disagreement, whether anything probed) for one side.
- **anchors.py** `vector_score` — [MEDIUM] Returns a value derived from the LADDER_RUNGS constant, which is 17, but the comment says it's derived from the Ladder's own height. The function is named 'vector_score' but the comment says it's derived from the Ladder's own height, which is not the same as the LADDER_RUNGS constant.
  - says: Vector on the 0-10 decimal scale, derived from the Ladder's own height. No new quantity.
- **allsweep.py** `bad` — [MEDIUM] counts some subsystems but excludes reconcile findings and some estate findings
  - says: count the number of bad subsystems
- **allsweep.py** `allsweep.Verifier.__iter__` — [MEDIUM] returns an iterator over (label, argv)
  - says: it would have broken verify_math.py:6824-6825
- **allsweep.py** `allsweep.VERIFIERS` — [MEDIUM] a list of Verifier objects
  - says: A plain three-tuple was the obvious shape
- **drill.py** `net` — [MEDIUM] net runs a test that is not properly scoped to the function it's testing
  - says: net runs a test
- **ingest_doc.py** `mine` — [MEDIUM] mine(a.source) is called but its return value is not checked for the early stops conditions
  - says: mine(a.source) returns True only when every chunk was processed, and False on both of its early stops

---

Written by `src/overwatch.py`. Structure is checked every round; the model reads modules that changed first, then whichever has gone longest unread. A finding stays open until the file it points at changes.
