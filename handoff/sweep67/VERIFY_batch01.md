# sweep67 batch01 verify
F1 CONFIRMED (MINOR): cleanup/readback notes at drill.py 4812, 4893/4899, 4937, 5210, 5260, 9005, 24532/24569 still call silence.note outside a sandbox; _decline_notes regex (24202) does not cover them. Order 8d6f876efd0a
F2 skipped (already fixed tonight)
F3 skipped (already fixed tonight)
F4 CONFIRMED (MINOR): drill.py:23638 in_scope(name, rows=[]); out_of_scope only calls load() when rows is None (roll.py:64), so the unreadable path is never driven. Order 3fa970025680
F5 CONFIRMED (MINOR): drill.py:14267-14270 skips non-dict rows; a dict/non-list COVERAGE.json returns True. Order e4942f481232
F6 CONFIRMED (INFO): _reread_the_breaches docstring (26197) says 2-tuple, returns 3 (26274); "two nets up" (13855) points at a net defined later. Order 4495e7d8c8b0
