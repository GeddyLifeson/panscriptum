# VERIFY batch13 (sweep67)
F1 CONFIRMED ingest_doc.py:154-157 `if t:` only, no empty/textless count; order 9cc87ededee1
F2 CONFIRMED assay.py:1881 linear +0.01 loop, no closed form (dead code); order ad6d78d6d545
F3 CONFIRMED assay.py:334 `x <= 0` misses NaN, min/max yields 1.0; order 0be9eabfe057
F4 CONFIRMED whoruns.py:69 exact-token -m/-c only; order d8ad47ebf10d
F5 CONFIRMED corpus_db.py:1011 CANNED.get -> None -> rc 0; order 3953d4d6177b
F6 CONFIRMED corpus_db.py:281 INSERT OR REPLACE vs entry rows from both (latent); order 92b6168fdd74
