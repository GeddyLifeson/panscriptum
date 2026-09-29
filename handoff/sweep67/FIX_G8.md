# FIX_G8 -- run #67 (pipeline.py, manifest_builder.py, standards.py, weave.py, publish.py, workorders.py)

| id | verdict | how | net |
|---|---|---|---|
| a8fa52a33445 | FIXED | new `pipeline._dump_tmp` removes its tmp on a raising dump (used by both record writers and `land_json`); `_landed` removes tmp on a denied rename. The `_landed_cas` CAS and the widened watermark are unchanged. The 4 existing orphan .tmp files in data/records are left for the owner | nets/a8fa52a33445.py |
| f6a751c55c84 | FIXED | `pipeline._entry_index` refuses non-dict items and bool indexes (used by `_judged_something` and the loop). Bool category is excluded. `_res_text` coerces non-str scale_note/topic/subroom into their rejected-answer trail. Non-str physiology is refused. `results: null` iterates as empty | nets/f6a751c55c84.py |
| 073752d048bc | FIXED | `update_handoff` counts only records whose `synthesis.ceiling_entity` is truthy | nets/073752d048bc.py |
| 98eae835e14e | FIXED | `phase_write` logs every `thin` source by name, uncapped | nets/98eae835e14e.py |
| 419c88eb746a | FIXED | stale cites replaced by symbols (`phase_entrypass` "at its top"; `catalogue_web.catalogue_composite` / `catalogue_web.catalogue`) | comment-only |
| d3dddc44ef08 | FIXED + QUESTION | `--only` prints every name that matches no buildable source and returns 1 before writing anything (it also refuses an empty pool). QUESTION for owner: should `--only` write to its own path instead of `paths.manifest` even when it matches? Left as is | nets/d3dddc44ef08.py |
| 9addfa9acbc2 | FIXED | logic moved into `standards.phases_standard(lib)`, following the `charter_regression_verdict` precedent so a net can run it without check()'s live probes. Absent phases now read UNMEASURED and do not hold. Rows use `.get` and non-dict rows are ignored | nets/9addfa9acbc2.py |
| ac4d00993598 | FIXED | logic moved into `standards.shelfmarks_standard(marks)`. It counts printed-shelfmark collisions as well as address collisions, and an empty file reads UNMEASURED and does not hold. Live data has 0 of each | nets/ac4d00993598.py |
| fd2d04fa0aea | FIXED | `main()` calls `check()` once on every path. `report()` and `work_orders()` gained an optional `rows=` keyword, and the rc comes from the same rows that were printed | nets/fd2d04fa0aea.py |
| 87add9d671b5 | FIXED | `weave.filtered_index` filters each hit. A key is dropped and counted only when no hit survives. The weave outputs (ENTITY/RESONANCE artifacts) are NOT regenerated: that is a pipeline phase and is off-limits here | nets/87add9d671b5.py |
| 200dd0c070b0 | FIXED | publish.py comment now cites `push()`, not a line number | comment-only |
| 8e020082d8f6 | FIXED | "127 drill nets" changed to "every drill net" | comment-only |
| 913f31fb9c10 | FIXED | the LOCAL-door `except` now calls `silence.note("workorders.py:file-order-door")` | nets/913f31fb9c10.py |

Verification: each net prints True on the fixed code. Each `_revert.json`, applied to a scratch copy of src/, turns its net False. pyflakes is clean and the import succeeds for all six modules. The reverts are byte-exact: pipeline.py and weave.py are CRLF, so their reverts carry `\r\n`.

Not fixed (out of the order's scope): `pipeline.update_handoff` still leaves its RUN_STATUS.md tmp behind when the rename is denied. It is the same shape as a8fa52a33445 and needs a one-line `os.remove`.
