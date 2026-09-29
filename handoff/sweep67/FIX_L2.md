# FIX_L2 (sweep67, run #67)

| order | verdict | how | net |
|---|---|---|---|
| fc56eda04e77 | FIXED | feats_index docstring now names read.py / read.CACHE as producer, feats.py -> data/feats | comment-only |
| fb195debf1de | FIXED | generate.py comment: incremental saves land every chapter, only the final two writes decide exit code | comment-only |
| 33ec3804e2df | FIXED | hostcheck.sweep skips the HOST_FITNESS.json write when `only` is set, prints spot-check notice | nets/33ec3804e2df.py |
| d39cbbe8759d | FIXED | hostcheck.adopt tracks judged_any; all-UNREACHABLE sources print "no candidate answered" and are counted "unmeasured" | nets/d39cbbe8759d.py |
| 888609d44b32 | FIXED | ledger.py cites the verify_math block after `import ledger as L` by content, not lines | comment-only |
| 0ceb29ffae61 | FIXED | ledger_guard refusal message uses _snapshot_path(name); _read_chain_lines docstring says seal() uses silence.append_line | nets/0ceb29ffae61.py |
| 4ca05cfcaac9 | FIXED | magnitude comment window 12,288; assay credit cited by symbol | comment-only |
| 89a3c760aeb0 | FIXED | run_batch banner counts settled() records only and flags a queue at --limit. Total pre-cut size not shown: queue() truncates internally and changing its return would break its signature | nets/89a3c760aeb0.py |
| bcf499b464be | FIXED | _is_score adds math.isfinite (import math added) | nets/bcf499b464be.py |
| 15b304488904 | FIXED | _owner_pid docstring reworded to 72 hours / about 30 hours | comment-only |
| 2a91c40e9442 | FIXED | mutate live-tree guard compares normcase(realpath()) for both root and root/src | nets/2a91c40e9442.py |

All six nets: True on fixed src, False on a scratch copy with the revert applied. pyflakes clean and import OK for all seven modules.
