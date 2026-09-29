# sweep67 batch09 verify

- F1 (remainder only; kill_duplicate_jobs already fixed): PARTIAL. restart_reader and kill_stalled_job match by lognames.OWNER fragment (+ "python") with no tree check; narrower than the audit (fragment match is already fairly tight). Order 2a5344d24132.
- F2: CONFIRMED. onomast.py:610-617 skips `naming` cids when seeding `taken`, so a new earlier-sorting world can take a standing designation (needs a collision). Order c9c29a2305f1.
- F3: skipped (already fixed).
- F4: CONFIRMED. backfill.py:201-203 `[^a-z0-9]+` key collapses non-Latin titles to "". Order 5032684974ff.
- F5: PARTIAL. _record_restart has no production caller, but is deliberately kept as a verify_math test entry (verify_math.py ~9924-9936); the real defect is the two stale docstrings. Order 05576868dd8f (docstring reword, do not delete).
- F6: CONFIRMED. foreman.py:1312-1313 remedies comment sits above RESTART_STAMP. Order d6e486885673.
- F7: CONFIRMED (dormant). profile.py:132 encode / :227-228 decode fall back to plausible values. Order 49e01317e5e0.
- F8: CONFIRMED. context_budget.py header quotes 6,964/11,147/18,112-char measurements of a changed prompt. Order f2f20bac493d.
