# VERIFY batch07 (sweep67)
F1 SKIPPED (already fixed tonight)
F2 CONFIRMED standards.py:1195 phases 0/0 reads MET when pipeline import fails; order 9addfa9acbc2
F3 CONFIRMED weave_index.py:350-359 skipped record cached under valid sig, short index written; order 50c54c488e6a (MAJOR)
F4 CONFIRMED sweep_plan.py:1032 if a.batches precedes elif a.check_briefs; order 2a0dd1d54ff6
F5 CONFIRMED address_space.py:586-635 tiers={} still writes SHELFMARKS.json; order 655176b6ac80 (MAJOR)
F6 CONFIRMED standards.py:2552-2573 check() runs twice per invocation; order fd2d04fa0aea
F7 CONFIRMED sweep_plan.py:770/781/804 local import makes silence unbound at 804; order 939cb74c818a
F8 CONFIRMED standards.py:1470 counts address only, empty file reads MET; order ac4d00993598
