# FIX G3 (run #67) -- catalogue_aurora, catalogue_codex, catalogue_web, chain, retry_synthesis

| order | verdict | how | net |
|---|---|---|---|
| ed5f75ec19fe | FIXED | `parse_folder(..., unparsed=None)` collects unparseable XML paths; `main()` prints them and adds them to `refused` (exit 1) | nets/ed5f75ec19fe.py |
| 6d800a399592 | FIXED | `_assert_not_halted` (retry_synthesis idiom) added to catalogue_codex, catalogue_web, catalogue_aurora, called after parse_args unless `--dry-run`. COORDINATOR: add `catalogue_codex.py`, `catalogue_web.py`, `catalogue_aurora.py` to `verify_math._INTERLOCKED` | nets/6d800a399592.py (3 revert entries) |
| 081f6c79b882 | FIXED | catalogue_codex.main skips rows failing `roll.in_scope(name, roll)`. roll.py:19-20 claim not edited (not my module) | nets/081f6c79b882.py |
| 56a4ed35c11e | FIXED | catalogue_web.main filters `todo` through `roll.in_scope` after both selections (covers `--recatalogue`) | nets/56a4ed35c11e.py |
| 0173de67d95a | FIXED | new `_dedup_fetch` helper used at both sites: a key is held only by a title that produced text; twins of a textless title are fetched in its place; only true twins reach `deduped` | nets/0173de67d95a.py |
| ec824ade998f | FIXED | `extract` records `limit` and `rows_harvested` in `_LAST_EXTRACT`, which `write_result` persists as CHAIN.json `unanswered` (option 3: record, not refuse) | nets/ec824ade998f.py |
| 6c3f5f7df5f2 | FIXED | unmatched `--only` names printed to stderr; `main()` returns 1 when any exist (matched names still run) | nets/6c3f5f7df5f2.py |

Verification: each net prints True on fixed code; each `_revert.json` substitution (applied on a scratch copy of src/) turns its net False; a control run with old==new stays True. pyflakes clean on all five modules; all five import.

Notes: the four catalogue_*/chain files are CRLF on disk, retry_synthesis is LF; revert JSONs use LF (drill reads in text mode). Unmatched `--only` also fires for a name already retried/with synthesis (not pending); the message says so.
