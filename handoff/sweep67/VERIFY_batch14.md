# VERIFY batch14 (sweep67)
F1 skipped (already fixed tonight)
F2 skipped (already fixed tonight)
F3 CONFIRMED manifest_builder.py:521-523 unmatched --only names dropped, writes paths.manifest; order d3dddc44ef08
F4 CONFIRMED stale citations (line numbers have shifted since audit but each is still wrong): liveness order 7c6f11de95ea, binding_health order 11b79335243e, generate order fb195debf1de
F5 CONFIRMED binding_health.py:1414-1415 mistyped --host dropped when others match; order bc0815a6bd21
F6 CONFIRMED manifest_builder.py:504 (null entry_count TypeError) and :680 (r["category"] KeyError); order 9d50fd3906e7
