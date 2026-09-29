# sweep67 — orders fixed directly by the run coordinator (run #67)

| order | verdict | how | net |
|---|---|---|---|
| 4495e7d8c8b0 | FIXED | drill.py: `_reread_the_breaches` docstring now names the 3-tuple it returns; `_catalog_matches_disk` cites `gate_claim_matches_reality` by location, not "two nets up" | comment-only |
| 8d6f876efd0a | FIXED | drill.py: all twelve `*-probe-cleanup` / `*-probe-readback` / `empty-snapshot-cleanup` notes now go to `_DECLARED_ESCAPES` (the sweep66 D1 decline idiom) instead of the spied ledger; `_decline_notes` widened to those words so a new one written the old way is caught; ten now-unused local `import silence` lines removed | existing net "a net that cannot measure DECLARES it..." proved RED with handoff/sweep67/revert_cleanup_decl.json, HELD after |
| 3fa970025680 | FIXED | drill.py: `unreadable_roll_does_not_exclude_the_library` now points `roll.ROLL` at a torn scratch file and calls `in_scope` with no rows, so `roll.load()`'s fail-open arm is really driven | proved RED with handoff/sweep67/revert_roll_torn.json (load raises), HELD after |
| e4942f481232 | FIXED | drill.py: the coverage-overflow net returns False for a COVERAGE.json with no dict rows; new control "[control] the coverage-overflow net refuses a file with nothing checkable in it" | control proved RED with handoff/sweep67/revert_cov_shape.json, HELD after |
| 184019026dd3 | FIXED | verify_math.py: restored the eaten `__file__` in the run35 batch5 header comment | comment-only |
| 3e608ea959e1 | FIXED | verify_math.py: the self-citation control note no longer hard-codes fixture counts | comment-only |
| 79a03304bcac | FIXED | verify_math.py: §18c temp-site enumeration names `_lane_root_vm` and `_synthetic_dir_b2`; count corrected to nine | comment-only |
| 9d50fd3906e7 | FIXED | manifest_builder.py: `(r.get("entry_count") or 0) > 0` and `.get("category") or "Uncategorized"` in the populated filter and the unassigned report | no net (null-guard on a report path) |
