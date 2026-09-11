# OVERWATCH

round 491  ·  last run 2026-09-10 20:02

## Structure

- modules that will not import: **0**
- files that will not parse: **0** of 303,086 inspected (deep scan as of round 487)
- catalogued sources with no host: **7** Curious DM Investigations (the Sharkin), Genuine Fantasy Press (Forgotten Secrets), JMBrew, Kobold Press (Midgard Heroes Handbook, Midgard Worldbook), Super Energy Apocalypse 1 & 2, aurora_mods (Way of the Inkmaster), and 1 more
- on the roll but never catalogued: **6** HAWX, Heaven's Lost Property, Lost Mines of Phandelver, Twilight Imperium, major live-action Disney films, the Witch Tradition

## What the model found in the code

**9 open** (3 high). Newest first.

- **roll.py** `apply` — [HIGH] Apply a function to rows, returning modified rows
  - says: Apply `{source_name: {field: value, ...}}` to the roll, key-wise.
- **onomast.py** `well_formed` — [HIGH] Implements seven constraints but the docstring claims four, and three of the four original constraints are misattributed
  - says: Is this a name a Custos could say aloud and write down twice the same way?
- **foreman.py** `lines_changed` — [HIGH] Calculates the number of lines changed based on the diff between old and new code, but the docstring says it's not `abs(len(new) - len(old))` and instead explains a different method. However, the code correctly implements the described logic using difflib's SequenceMatcher. The docstring's claim is accurate, and the code aligns with it. Therefore, no defect of fact is found here.
  - says: How many lines a rewrite actually touches.
- **tells.py** `prompt_in_sync` — [MEDIUM] compares the block with the text after replacing \r\n with \n, but the code uses `block.replace("\r\n", "\n")` which replaces all instances of \r\n with \n, while the text is replaced with `text.replace("\r\n", "\n")` which replaces all instances of \r\n with \n, but the comparison is done on the modified strings, which may not reflect the actual content of the file
  - says: returns True if the prompt file contains the generated block, False otherwise
- **sweep.py** `sweep` — [MEDIUM] the comparison eight lines down (`sc["n"] > idx[k][3]`) is what implements the finer-grained-scale-wins rule
  - says: the comparison eight lines down (`sc["n"] > idx[k][3]`) is what implements the finer-grained-scale-wins rule
- **sweep.py** `sweep` — [MEDIUM] reads `hit[3]` as the `of` field of `row["native"]`
  - says: reads `hit[3]` as the `of` field of `row["native"]`
- **publish.py** `push` — [MEDIUM] push() raises a PushHeld exception when a push is held, which is caught in an except block that prints the exception and sets rc=1
  - says: push() now has only two RETURN values, and both are honest ones: it landed, or there was nothing to land. The third outcome -- committed but held -- comes out as `PushHeld` and is caught below, where it prints and sets rc=1
- **foreman.py** `_contracts_pass` — [MEDIUM] Returns a tuple indicating success or failure of the contracts pass
  - says: Everything that must still be true after a patch.
- **verify_math.py** `max` — [MEDIUM] the tolerance is silently discarded as the code compares integers exactly
  - says: the k-th burg holds P1/k, independently recomputed

---

Written by `src/overwatch.py`. Structure is checked every round; the model reads modules that changed first, then whichever has gone longest unread. A finding stays open until the file it points at changes.
