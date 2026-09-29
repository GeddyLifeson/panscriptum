# FIX_L1 (sweep67, run #67)

| order | verdict | how | net |
|---|---|---|---|
| 6233a825716b | FIXED | anchors.py: "ninety lines above" now cites the DECLARED LADDER comment at the `order` list | comment-only |
| bc0815a6bd21 | FIXED | binding_health: new `_filter_hosts(hosts, only)` returns (kept, unmatched); run() escalates unmatched --host names at JANITOR via `_report_not_written` (BINDING_FILTER_HOST_UNMATCHED) | nets/bc0815a6bd21.py |
| 11b79335243e | FIXED | binding_health: both line citations replaced by symbols (feats.note_throttled / run(), and `quarantine`) | comment-only |
| 246bb41d30f6 | FIXED | canon_backup: `:312-320` -> `verify`; "LIKE LINE 188" -> the snapshot writer's `replace_retry` | comment-only |
| 0c789022ef15 | FIXED | catalogue_web._singular: dropped "zes"/"ches" from the sibilant tuple; docstring example Witches->Witch replaced (Witches now -> Witche, same as the old rstrip, noted) | nets/0c789022ef15.py |
| 1d85d7c0c608 | FIXED | compress_store.store: write wrapped in try/except OSError, guarded unlink of tmp, re-raise | nets/1d85d7c0c608.py |
| f2f20bac493d | FIXED | context_budget: quoted measurements marked "as measured 2026-08-24" | comment-only |
| 3953d4d6177b | FIXED | corpus_db.main: unknown --canned (no --sql) prints choices and returns 2 | nets/3953d4d6177b.py |
| d7efd67caa6f | FIXED | completeness.py: `endpoint.py:275-278` -> `endpoint.api_url` (only citation in the order's list) | comment-only |
| 64582589f887 | FIXED | custodes: comment now says table_faults() refuses the pairing from main() but is not in the battery | comment-only |
| ba367da8f3ba | FIXED | events.BOLD `{2,80}` -> `{2,}`; _looks_like_a_sentence refuses over-long spans with a recorded reason | nets/ba367da8f3ba.py |

Nets: each passes on fixed code and goes False under its `_revert.json` (checked on a scratch copy of src/). pyflakes clean and import OK on all 10 modules.

QUESTION: 0c789022ef15 makes "Witches" singularise to "Witche" (the order's prescribed fix accepts this; a proper fix would need a dictionary). Left as ordered.
