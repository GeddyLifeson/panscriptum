# VERIFY batch06 (sweep67)

Skipped as already fixed tonight: F1.

- F2 CONFIRMED. `_digest` taken at overwatch.py:997 after review() finished. Order 599bfad87a6b.
- F3 CONFIRMED. `f.get('actual','')[:80]` at overwatch.py:287 on None raises; called outside try at ~:1009. Order 17719ce65b75.
- F4 CONFIRMED. thread_integrity.py:186-199 skips non-dict T1/entries silently; list T2 raises AttributeError. Order 969ebdbbda98.
- F5 CONFIRMED. catalogue_codex.py has no assert_clear; not on verify_math._INTERLOCKED (:7755). Order 6d800a399592.
- F6 CONFIRMED. Live check: catalogue_web.py:649 selects entry_count==0 with no scope filter; HAWX, Heaven's Lost Property, Disney films, Twilight Imperium are out-of-scope with 0 entries today. Codex half latent (:257). Orders 56a4ed35c11e (web), 081f6c79b882 (codex).
- F7 CONFIRMED. A mistyped `--only` name gives todo=[] and rc 0 (retry_synthesis.py:365-366). Order 6c3f5f7df5f2.
- F8 CONFIRMED (all four). ledger.py:43 -> 888609d44b32; overwatch.py:343 -> ecff61c18fe9; thread_integrity.py:671 -> 22293ecca974; workorders.py:11 "127 drill nets" -> 8e020082d8f6.
- F9 CONFIRMED. `except Exception: pass` at workorders.py:561 has no silence.note. Order 913f31fb9c10.

## Prior-audit cross-check: nine HOST_QUARANTINED orders "no bot can close them"

REFUTED. `workorders.sweep_detectors` section 3 (workorders.py:1566-1569) resolves every open HOST_QUARANTINED order whose host is absent from `binding_health.quarantined()`, with resolution "host is no longer quarantined". `quarantined()` (binding_health.py:381-406) drops a record once `retry_after` passes (24 h, RETRY_AFTER_S), and `release()` removes it earlier when the canary passes. state/workorders_closed.jsonl already holds 68 orders closed this way. The nine open orders match nine hosts still in data/HOST_QUARANTINE.json with about 20 h left. They close on the first `workorders --sweep` after expiry. No order filed. What nothing in src/ does is schedule that sweep (only the maintenance run invokes it); that is a scheduling question, not a missing close path.
