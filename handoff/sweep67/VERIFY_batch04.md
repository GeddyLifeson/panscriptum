# Verify batch 04 (sweep67)

F1: CONFIRMED. mutate.py:3247 file_orders block runs after rc,stopped_at=4,i (3167, 3209) for the same target. Order 6093d3475efc.
F2: CONFIRMED. mutate.py:2189 string compare of abspath, no normcase/realpath. Order 2a91c40e9442.
F3: CONFIRMED. _owner_pid docstring (1185-1189) says hours / one day; constant is 72h, comment says ~30h. Order 15b304488904.
F4: CONFIRMED. _write_rulings (1055-1069) fixed .tmp name, bare os.replace, no CAS. Order 1e2e6aad5fca.
F5: CONFIRMED. mutate.py:250-256 remove-then-O_EXCL without checking the record is still the stale one. Order 0620969b742d.
F6: CONFIRMED. (a) bare pass at 1705-1706; (b) live_before at 2252 precedes the try at 2254. Order 59b534837fb2.
F7: CONFIRMED. suppressions._load (103-106) checks only top-level list. Order 2beb0a7fa5b3.
F8: CONFIRMED. threads.py:261/285 doc.get and c.get sit outside the try. Order 5c24b8e36cfe.
F9: CONFIRMED. threads.py:118 comment vs DERIVABLE (141); argparse text 938; banner 969. Order cc82eb5e8c61.
F10: CONFIRMED. handbuilt.compute(): sustain 9.5 three-way tie (IRS, Black Winter, Getter Emperor). Thor/Undertaker claims taken from audit and strings present (lines 111, 272, 378). Order cd77e492b26b (OWNER).
F11: CONFIRMED. tuning.py:193 connect() without mode=ro; mutate.py:1748 documents the side effect. Order 554adb29161e.
