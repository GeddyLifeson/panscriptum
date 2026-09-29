# FIX_L4 (run #67)

| order | verdict | how | net |
|---|---|---|---|
| 6240f4d889a0 | FIXED | sweep.py comments cite `sweep()` / `cachekey.load` / `cache_path` by symbol | comment-only |
| dccbc1cddd13 | FIXED | tells.scan suppresses a phrase contained in a longer listed phrase; `_INFLECT` regex for six stems. Lists untouched, so prompts/system_style.txt stays in sync | dccbc1cddd13.py |
| a5dfa403f8ac | FIXED | leading `\b` on both STRUCTURAL patterns (Edit tool) | a5dfa403f8ac.py |
| 22293ecca974 | FIXED | thread_integrity comment cites `classify()` | comment-only |
| cc82eb5e8c61 | FIXED | threads.py comment, argparse description and banner say T1-T4 derived, T5 owner-authored | comment-only (strings) |
| 5c24b8e36cfe | FIXED | annex_codes/law_codes: isinstance(doc, dict) guard and isinstance(c, dict) rows | 5c24b8e36cfe.py |
| c35acac4ede1 | FIXED | tiers.py comment cites symbols; "13 unaddressed" count dropped | comment-only |
| 554adb29161e | FIXED | cloud_success_rate opens the db `mode=ro` via pathname2url | 554adb29161e.py |
| d8ad47ebf10d | FIXED | script_of returns None for any token starting -m or -c | d8ad47ebf10d.py |
| 103074a4bdb6 | FIXED | worldseed comment cites the `reg_by_group` init by symbol | comment-only |
| 28868e940226 | FIXED | worldseed.main refuses `--write` with `--limit` (rc 2) | 28868e940226.py |

Nets pass on fixed code and go red on the `_revert.json` substitution (checked on a copy of src/).
pyflakes clean and import OK for all eight modules.

Notes: tells.py, threads.py and tuning.py are CRLF files; the revert JSONs use CRLF for them.
The threads.py `build()` docstring still says "T1/T2 graph" (not cited by the order; left).
