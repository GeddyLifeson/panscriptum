# OVERWATCH

round 254  ·  last run 2026-09-01 10:38

## Structure

- modules that will not import: **0**
- files that will not parse: **1** of 287,541 inspected (deep scan as of round 253)  — state\model_metrics.jsonl — malformed JSON on line 102599: Expecting value: line 1 column 1 (char 0)
- catalogued sources with no host: **8** Curious DM Investigations (the Sharkin), Genuine Fantasy Press (Forgotten Secrets), JMBrew, Kobold Press (Midgard Heroes Handbook, Midgard Worldbook), Super Energy Apocalypse 1 & 2, The Elements Beyond, and 2 more
- on the roll but never catalogued: **6** HAWX, Heaven's Lost Property, Lost Mines of Phandelver, Twilight Imperium, major live-action Disney films, the Witch Tradition
- NOT RUNNING: **0** autostart.py

## What the model found in the code

**19 open** (5 high). Newest first.

- **magnitude.py** `band_hits` — [HIGH] counts BAND MATCHES ONLY (got_band == band), but the code returns it as the verdict which requires all scored rows to be consistent
  - says: counts BAND MATCHES ONLY (got_band == band)
- **foreman.py** `clear_learned_caps` — [HIGH] it does instead
  - says: the code says it does
- **feats.py** `roll` — [HIGH] the return value of roll() is discarded and 0 is returned unconditionally
  - says: THE COUNTERS REACH THE EXIT CODE
- **feats.py** `extra` — [HIGH] is now a parameter that is checked for being numeric
  - says: was a cap on a ranked page list
- **escalation.py** `clear` — [HIGH] clear() is not called here and its behavior is not used in this code slice
  - says: clear() raises PermissionError for non-person callers
- **magnitude.py** `anchor` — [MEDIUM] assigned based on got.get("anchor") and ceiling[1]
  - says: a fiction cannot be out-scaled by its own inhabitant
- **magnitude.py** `quantity_scores` — [MEDIUM] Axis scores computed from quantities, but the function does not properly handle the case where the entity is not the one performing the act, and the function does not properly handle the case where the quantity is not convertible to the required units.
  - says: Axis scores computed arithmetically from measured quantities. No model opinion involved.
- **health.py** `silence.write_json` — [MEDIUM] silence.write_json returns False when denied, but the code does not handle this case properly, leading to a potential failure to record problems
  - says: NEVER FATAL. A preflight that dies because it could not write its own report is worse than one that cannot report
- **generate.py** `generate_job` — [MEDIUM] generate_job is called but the code does not handle any exceptions or errors that may occur during generation
  - says: generate_job is called to generate the job's text
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
- **allsweep.py** `allsweep.VERIFIERS` — [MEDIUM] a list of Verifier objects
  - says: A plain three-tuple was the obvious shape
- **drill.py** `net` — [MEDIUM] net runs a test that is not properly scoped to the function it's testing
  - says: net runs a test
- **ingest_doc.py** `mine` — [MEDIUM] mine(a.source) is called but its return value is not checked for the early stops conditions
  - says: mine(a.source) returns True only when every chunk was processed, and False on both of its early stops

---

Written by `src/overwatch.py`. Structure is checked every round; the model reads modules that changed first, then whichever has gone longest unread. A finding stays open until the file it points at changes.
