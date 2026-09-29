# FIX_L3 (sweep67, run #67)

| id | verdict | how | net |
|---|---|---|---|
| 17719ce65b75 | FIXED | overwatch: `_fingerprint` stringifies actual/symbol; review() refuses non-dict/non-string findings before `_anchored`; WATCH.md render stringified | 17719ce65b75.py |
| ecff61c18fe9 | FIXED | overwatch: line cite replaced by `_merge_ledgers` docstring | comment-only |
| 303757a4c704 | FIXED | physics.kinetic docstring: "about a fifth (19 percent)" | comment-only |
| f7082f032948 | FIXED | pick_model.save_config removes the temp on failed write and on denied replace | f7082f032948.py |
| dce30dd870bc | FIXED | policy: both line cites replaced by symbol | comment-only |
| bca2ca48e316 | FIXED | read.queue prune keeps only `k.endswith(_QK + _QROW_RULE)`; state file untouched | bca2ca48e316.py |
| 91eccaf13360 | FIXED | read: all five stale line cites replaced by symbol | comment-only |
| d642a24afa2d | FIXED | reference: cite by symbol (`shelfmark`) | comment-only |
| 2c226602695b | FIXED | rosetta: dropped the three str(e) slices | 2c226602695b.py |
| a713b2598ed5 | FIXED | rosetta.check records `rho_reason` ("too few"/"tied"); printout and summary reworded | a713b2598ed5.py |
| e6cd86d4172e | FIXED | secondopinion: encoding utf-8 / errors replace on all three subprocess.run | e6cd86d4172e.py |
| d00e843b1765 | FIXED | secondopinion.mine_says counts only rows with silent true | d00e843b1765.py |
| 21c78921ec89 | FIXED | snapshot.before: label sanitised with re.sub, dot-dot neutralised | 21c78921ec89.py |

Every net printed True on the fixed source and False under its `_revert.json`. pyflakes is clean and all nine modules import.

Note: the snapshot revert run created a stray directory `%TEMP%\x` (the pre-fix defect writing outside its temp root); harmless, could not delete under the safety hook.
