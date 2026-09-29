# VERIFY batch 12 (sweep67)
F1: SKIPPED (already fixed tonight)
F2: CONFIRMED - allsweep.py:370 no try; E.artifacts at :930 outside try. Order 1011c56d52a8
F3: CONFIRMED - magnitude.py:1231 admits quantity-only; compose() omits quantities. Order 5a2b91bf1b5d
F4: PARTIAL - overwrite of opinion is deliberate (in-line comment), but no relevance test: bare ton/metre readings become INSTRUMENT. Order 21ce9170f4d4 (MAJOR, RUN)
F5: PARTIAL - carry-forward and complete stamp real; verdict allowing unscored rows is documented in-line, the never-retry of DEFERRED is the defect. Order 6c2ee32b1465
F6: CONFIRMED - magnitude.py:1798-1800 generic except falls to cache None. Order efbfead57cb5
F7: CONFIRMED - _is_score (801) has no isfinite; max(0.0, nan) is 0.0. Order bcf499b464be
F8: CONFIRMED - magnitude.py:1745 and :1866 print truncated queue and len(done). Order 89a3c760aeb0
F9: CONFIRMED - secondopinion.py:472 sums all audit rows; silence.py:509/521 rows carry a silent flag. Order d00e843b1765
F10: CONFIRMED - text=True without encoding at :290/:322/:383. Order e6cd86d4172e
F11: CONFIRMED - coverage.py:317 via pipeline.records() skip (761-764), no retry. Order ee9365750ddf
F12: CONFIRMED - docstring says returns False; code writes unlocked and returns True; LK_LOCK blocks. Order f8dd772a0273
F13: CONFIRMED - no callers; __exit__ returns True for BaseException. Order 98650e9d31d7
F14: CONFIRMED - absolute tol at resonance.py:181. Order 1301ccb8fc44
F15: CONFIRMED - replace(os.sep) leaves "/" on Windows (snapshot.py:124). Order 21c78921ec89
F16: CONFIRMED - tiers.py:174 vs cited :122; magnitude.py:1278 says 6,144. Orders c35acac4ede1 (tiers), 4ca05cfcaac9 (magnitude)
