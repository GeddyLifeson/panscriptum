# VERIFY batch05 (sweep67)

Skipped as already fixed tonight: F1, F3, F7.

- F2 CONFIRMED. `_brace_end` returns j==n on no closer (feats.py:1660); callers slice `j-2`/`j-3` regardless. Order 926b5f0f997b.
- F4 CONFIRMED. Fixed `path + ".tmp"` at feats.py:2359 (evidence_for) and :1256 (resolve_hosts). Order 888b8b52467a.
- F5 CONFIRMED (latent). Diagonal keys add to total_wins but not N; no validation (rigor.py:485-491). Order 2b1e87355d3e.
- F6 CONFIRMED. feats_index.py:6-8 names feats.py; feats.py writes data/feats, data/readfeats is read.py's. Order fc56eda04e77.
- F8 CONFIRMED. parse_folder skips an unparseable XML with a note only (catalogue_aurora.py:162); main() never counts it. Order ed5f75ec19fe.
- F9 CONFIRMED. `open(tmp,"wb")`/write at compress_store.py:54 has no cleanup; the sweep covers a denied replace only. Order 1d85d7c0c608.
