# Verify batch 03 (sweep67)

F1, F2: skipped (already fixed tonight).
F3: PARTIAL. write_record/catalogue CAS path now removes tmp (_landed_cas). Still orphaned: _landed (pipeline.py:1297) on denied rename, and json.dump raising (no try/finally, incl. write_json :1393). 4 orphan .tmp files still in data/records. Order a8fa52a33445.
F4: CONFIRMED. _judged_something any() only; res.get / .strip() unchecked on later items; bool passes isinstance(ci,int) at pipeline.py:2550. Order f6a751c55c84.
F5: CONFIRMED. pipeline.py:2711 counts truthy synthesis, not ceiling_entity. Order 073752d048bc.
F6: CONFIRMED. `thin` only assigned (3379, 3383), never read. Order 98eae835e14e.
F7: CONFIRMED. catalogue_web.py:308-315 and 543-550 set seen[key] before page_texts; no_text titles shadow twins. Order 0173de67d95a.
F8: CONFIRMED. Reproduced: Prizes->Priz, Mazes->Maz, Caches->Cach, Niches->Nich. Order 0c789022ef15.
F9: CONFIRMED (line numbers slightly off in audit: records() call is :2464). Orders 419c88eb746a (pipeline), dce30dd870bc (policy), d642a24afa2d (reference).
