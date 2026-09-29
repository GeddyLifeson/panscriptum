# FIX_G1 (run #67)

| order | verdict | how | net |
|---|---|---|---|
| 0be9eabfe057 | FIXED | assay.axis_score returns None for NaN (isnan only; inf keeps its meaning) | nets/0be9eabfe057.py |
| ad6d78d6d545 | FIXED | interval_from_hands jumps to floor(max_dev*100)/100, and takes max_dev when +0.01 is absorbed | nets/ad6d78d6d545.py |
| 1011c56d52a8 | FIXED | check_import catches TimeoutExpired/OSError per module; E.artifacts wrapped like sibling tiers (main-level wrap not net-tested) | nets/1011c56d52a8.py |
| 1301ccb8fc44 | FIXED | hodge_decompose tolerance scaled by max abs flow (order's max(1.0, ..) form would keep 1e-10 flows absolute) | nets/1301ccb8fc44.py |
| 2b1e87355d3e | FIXED | bradley_terry refuses self-contest keys and non-finite/negative counts (RigorIntegrityError) | nets/2b1e87355d3e.py |
| 5032684974ff | FIXED | backfill._name_key: NFKD + isalnum; '' never counts as held | nets/5032684974ff.py |
| 49e01317e5e0 | FIXED | encode notes unknown genre/register; decode refuses codes not in GENRE_FROM/REG_FROM | nets/49e01317e5e0.py |
| f5176479c60a | FIXED (digits half) / QUESTION (parens half) | similarity returns 0.0 unless digit-run multisets are equal; differing non-numeric mid-name parentheticals left as documented (part of the name) | nets/f5176479c60a.py |

Nets proven green on fixed code and red under the `_revert.json` substitutions. pyflakes clean on all seven modules. assay.py and rigor.py are CRLF files; edits kept CRLF.
Not done: no verify_math checks added (verify_math.py is off limits).
