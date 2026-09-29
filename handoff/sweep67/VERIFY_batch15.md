# sweep67 batch15 verify
F1 skipped (already fixed). F2 skipped. F3 skipped. F4 skipped.
F5 CONFIRMED - hostcheck.py:1254 _land(OUT, results) unconditional with results filtered by only; nothing in src reads HOST_FITNESS.json. Order 33ec3804e2df
F6 CONFIRMED - tells.py:95,128 no leading \b; scan("understands as a reminder") returns 'stands as a testament' (rerun). Order a5dfa403f8ac
F7 CONFIRMED - scan('A tapestry of myriad of things.') gives 4 hits; 'unlocks/unlocked/fostering' give no hit (rerun). Order dccbc1cddd13
F8 CONFIRMED - hostcheck.py adopt(): one() keeps only ok verdicts, so unreachable prints none and counts as 'genuinely without a wiki'; wording only. Order d39cbbe8759d
F9 CONFIRMED - completeness.py:812-818 except Exception on json.load(OUT) leaves prior=[], disarming SHRINK_FLOOR at :828. Order 9bd9d77d5e0d
F10 CONFIRMED - anchors.py:510 "ninety lines above", ruling comment at :263. Order 6233a825716b
