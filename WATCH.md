# OVERWATCH

round 37  ·  last run 2026-08-23 11:32

## Structure

- modules that will not import: **0**
- files that will not parse: **0** of 58,031 inspected
- catalogued sources with no host: **17** Arcanum Worlds (Odyssey of the Dragonlords), Clockwork Angels (Rush), Curious DM
- on the roll but never catalogued: **6** HAWX, Heaven's Lost Property, Lost Mines of Phandelver, Twilight Imperium, major

## What the model found in the code

**6 open** (3 high). Newest first.

- **autostart.py** `sys.exit(main())` — [HIGH] exit with the return value of main() but discard any exception it raises
  - says: exit with the return value of main()
- **build_terminal.py** `place` — [HIGH] The function uses a fixed arc fraction (0.08 and 0.92) to determine the span of each child node's wedge, which does not properly account for the total available arc. This causes in
  - says: The function recursively lays out nodes in a radial tree with the given root at the center, distributing child nodes around the circle based on weighted arcs pr
- **assay.py** `interval` — [HIGH] The while loop condition checks `any(abs(v - centre) > interval for v in vals)`, but the loop body increases `interval` by 0.01 each time. However, the `interval` is rounded to 2 d
  - says: The interval must cover every signed reading, enforced by a while loop that increases interval until all readings are within bounds.
- **completeness.py** `silence.note` — [MEDIUM] The code does not actually log anything, as `silence.note` is never called.
  - says: Logs a note when category_size fails.
- **backfill.py** `missing` — [MEDIUM] Truncated by cap if provided
  - says: Ranked by article size so the deepest arrive first if this is ever interrupted, but NOT truncated: every character the wiki lists is a character the library sho
- **assay.py** `SIGMA_MAX` — [MEDIUM] SIGMA_MAX is defined as 9.9 / sqrt(12), which is correct for the standard deviation of a uniform distribution over [0.0, 9.9], but this value is used as a hard ceiling for uncertai
  - says: The maximum standard deviation for any axis, derived from a uniform prior over 0.0-9.9.

---

Written by `src/overwatch.py`. Structure is checked every round; the model reads modules that changed first, then whichever has gone longest unread. A finding stays open until the file it points at changes.
