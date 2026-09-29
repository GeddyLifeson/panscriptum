# VERIFY batch08 (sweep67)
F1 CONFIRMED scout.py:328,485 401/403/429 -> "exists but declines readers"; order 5a0545df6d2a
F2 CONFIRMED scout.py:330 all exceptions -> "no such host or no route"; order 2f9c45993f46
F3 CONFIRMED cascade_bridge.py:765 length_stopped ignores done.truncated; order ed64f2e394ed (MAJOR)
F4 PARTIAL cascade_bridge.py:635 regex matches input TPM refusals (classifier real; loop effect inferred); order 477be064b969
F5 CONFIRMED cascade_bridge.py:1249 corrupt ledger read as {}; order 9034467cae85
F6 CONFIRMED events.py:65 {2,80} drops long bold spans unrecorded; order ba367da8f3ba
F7 CONFIRMED worldseed.py:433 --limit with --write lands subset; order 28868e940226
F8 CONFIRMED worldseed.py:83-103 \w* prefix stems tag "attested"; order 4c7cf744461d
F9 CONFIRMED ledger_guard.py:722 wrong snapshot path, docstring ~805 stale (order 0ceb29ffae61); worldseed.py:371 "line 315" is :359 (order 103074a4bdb6)
