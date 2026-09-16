# OVERWATCH

round 571  ·  last run 2026-09-16 13:13

## Structure

- modules that will not import: **0**
- files that will not parse: **0** of 305,795 inspected
- catalogued sources with no host: **7** Curious DM Investigations (the Sharkin), Genuine Fantasy Press (Forgotten Secrets), JMBrew, Kobold Press (Midgard Heroes Handbook, Midgard Worldbook), Super Energy Apocalypse 1 & 2, aurora_mods (Way of the Inkmaster), and 1 more
- on the roll but never catalogued: **6** HAWX, Heaven's Lost Property, Lost Mines of Phandelver, Twilight Imperium, major live-action Disney films, the Witch Tradition

## What the model found in the code

**7 open** (3 high). Newest first.

- **wiki_source.py** `rank_by_size` — [HIGH] Order titles by article byte-length, longest first, but the function does not actually retrieve the byte-length data. The function is structured to fetch data but does not process or return the size information.
  - says: Order titles by article byte-length, longest first.
- **style_audit.py** `audit` — [HIGH] does not perform the audit but calls another function that does
  - says: audits a corpus of entries for style issues
- **assay.py** `assay` — [HIGH] Computes a Moth Number but the formula is incorrect due to missing covariance terms and incorrect variance calculation
  - says: Compute a Moth Number: 𝔄 = M_a + (sum w_i * s_i) / 10
- **withdraw_chapters.py** `select` — [MEDIUM] Returns all entries if no sources or addrs are provided, but the docstring claims it returns the whole catalog when no filters are applied. However, the code returns dict(cat) which is a shallow copy, but the docstring says it's PURE and the selection can be attacked by the drill without moving a file. The code does not actually return the whole catalog but a shallow copy, which may not be intended.
  - says: The entries this run will withdraw. -> {addr: rec}.
- **silence.py** `replace_retry` — [MEDIUM] uses the same name for different faults
  - says: A DIFFERENT FAULT WEARS A DIFFERENT NAME IN THE LEDGER
- **scout.py** `seen_ok` — [MEDIUM] initialized to True and set to False only if there's an exception reading the file
  - says: indicates if the attempts were successfully read
- **health.py** `return 1 if reopen_stranded(dry=not a.go) is None else 0` — [MEDIUM] return 1 if the result of reopen_stranded is None else 0
  - says: return 1 if the result of reopen_stranded is None else 0

---

Written by `src/overwatch.py`. Structure is checked every round; the model reads modules that changed first, then whichever has gone longest unread. A finding stays open until the file it points at changes.
