# sweep67 batch10 verify

- F1: PARTIAL. Non-trailing parentheticals are deliberately treated as name text (entity_match.split_qualifier docstring), but the "absolute" qualifier rule overreaches and a differing digit run (Issue 1 vs Issue 11) is a real identity difference scored fuzzily. Latent, no caller acts on best(). Order f5176479c60a.
- F2: skipped (already fixed).
- F3: skipped (already fixed).
- F4: CONFIRMED. rosetta.py:315, 337, 669 use str(e)[:60] / [:70] with no marker. Order 2c226602695b.
- F5: CONFIRMED. rosetta.spearman returns None for both <4 pairs and zero variance; main() prints "needs 4 overlapping names" (:825) for both. Order a713b2598ed5.
- F6: CONFIRMED. pick_model.py:138-146 never removes the .tmp on denied replace or write failure (silence.replace_retry does not remove it). Order f7082f032948.
- F7: CONFIRMED (three stale-comment sites, cosmetic). custodes.py:189 (64582589f887), canon_backup.py:223/496 (246bb41d30f6), publish.py:1566 (200dd0c070b0).
