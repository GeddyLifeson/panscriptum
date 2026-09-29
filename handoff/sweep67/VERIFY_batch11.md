# VERIFY batch 11 (sweep67)
F1: SKIPPED (already fixed tonight)
F2: CONFIRMED - build_all 14,592 worlds vs SEVENFOLD 1,569 re-measured; audit only self-checks. Order c4d79f533471 (MAJOR, RUN)
F3: CONFIRMED - extract rows[:limit] at chain.py:672 then write_result with no limit marker. Order ec824ade998f
F4: CONFIRMED - comment now at overnight.py:1615-1616; calls are autostart.py:478 and :539. Order 7fb8805a1501
F5: CONFIRMED - gpu_lane.py:449-453 reads, judges, removes unconditionally. Order 9310fefed227
F6: CONFIRMED - gpu_lane.py:260 float() unguarded, lane() does not wrap _take_slot. Order 76598c5d0cdc
F7: CONFIRMED - Newtonian/relativistic at 0.5c = 0.808 (19% under), not a third. Order 303757a4c704
