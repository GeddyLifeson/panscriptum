# OVERWATCH

round 175  ·  last run 2026-08-29 20:29

## Structure

- modules that will not import: **0**
- files that will not parse: **0** of 276,686 inspected
- catalogued sources with no host: **8** Curious DM Investigations (the Sharkin), Genuine Fantasy Press (Forgotten Secret
- on the roll but never catalogued: **6** HAWX, Heaven's Lost Property, Lost Mines of Phandelver, Twilight Imperium, major

## What the model found in the code

**4 open** (2 high). Newest first.

- **read.py** `read_entity` — [HIGH] Reads entity's pages but uses local GPU instead of cascading through providers, leading to inefficient use of resources
  - says: Read one entity's cached pages with the model. Returns verified feats by axis.
- **read.py** `ensure_transport` — [HIGH] Decides the transport ONCE, before any worker starts, but does not announce the result, leading to potential silent failures and incorrect routing of requests.
  - says: Decide the transport ONCE, before any worker starts, and say which one won.
- **policy.py** `report` — [MEDIUM] reports the evaluation scope but does not include the unreadable records, which are separate from the evaluated set
  - says: WHAT WAS AND WAS NOT LOOKED AT, first, before any verdict. A window nobody can see the far side of reads exactly like a complete list, so the scope is stated wh
- **overnight.py** `main` — [MEDIUM] the code around it says it should be derived
  - says: the main function

---

Written by `src/overwatch.py`. Structure is checked every round; the model reads modules that changed first, then whichever has gone longest unread. A finding stays open until the file it points at changes.
