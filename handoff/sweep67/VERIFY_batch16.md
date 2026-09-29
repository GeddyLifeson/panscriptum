# sweep67 batch16 verify
F1 CONFIRMED - weave.py:240-296 filtered_index reads hits[0] only, then keeps or drops the whole key. Order 87add9d671b5
F2 skipped (already fixed).
F3 CONFIRMED - local_agent.py:351-355 except Exception: continue and deprecated skip, then unique = len(hits)==1. Order 9e59609b76b2
F4 CONFIRMED - wiki_source.py:577-593 all three sections raising falls through to return "", same as a page with no prose. Order 882065c6b19d
F5 CONFIRMED - sweep.py:162 absent HOSTS gives {}; rosetta_index/navtree_names return empty on absent file; result lands in CHARACTER_SWEEP.json (:365). Order 273bd193d454
F6 CONFIRMED (by logic; the 152 MB measurement not re-run) - read.py:1362 `_QK in k` also matches pre-rule keys (path SEP name); key format at :1241 has two separators. Order bca2ca48e316
F7 CONFIRMED - read.py :74, :584, :887/:889, :1569/:1571 cite stale line numbers (measurement now ~:99-107, CLOUD_CHUNK at :111). Order 91eccaf13360; sweep.py:86 cachekey.load is at :192 not :160, order 6240f4d889a0
