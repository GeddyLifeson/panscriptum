# FIX_G2 (run #67): cascade_bridge.py, scout.py, wiki_source.py, worldseed.py

| order | verdict | how | net |
|---|---|---|---|
| 9034467cae85 | FIXED | record_unrecognised: only FileNotFoundError is an empty ledger; unreadable or wrong-shape notes and returns without writing | nets/9034467cae85.py |
| 477be064b969 | FIXED | size_refusal_limit learns a ceiling only when the text names output tokens/OTPM; an input TPM refusal returns None and falls to the unrecognised ledger | nets/477be064b969.py |
| 5a0545df6d2a | FIXED | verify: 429 no longer "declines readers"; scout records 401/403 only if a control invented path on the host 404s (new _control_404); a registered source's SCOUT_BLOCKED entry is pruned | nets/5a0545df6d2a.py |
| 2f9c45993f46 | FIXED | verify returns transport=True for non-HTTP exceptions; scout returns reached=False when every checked URL failed by transport, so sweep unstamps the slot | nets/2f9c45993f46.py |
| 882065c6b19d | FIXED | page_text raises new PageFetchFailed when no section call answered; page_texts catches it, notes it, and fills an optional `failed=` list (additive kwarg) | nets/882065c6b19d.py |
| 4c7cf744461d | FIXED | short-word stems (ice, dust, sea, ash, plain, war, dead, front, space, fleet, warp, keep, lord) given explicit suffix lists instead of `\w*`; long stems unchanged | nets/4c7cf744461d.py |

All six nets: True on fixed src, False on the revert JSON applied to a copy of src. pyflakes clean and import OK on all four modules.

Notes for the coordinator:
- catalogue_web.py (not mine) still counts failed titles in `no_text`; it can pass `failed=[]` to page_texts to split them out. The failure is now in the ledger regardless.
- Order 477b: the input-TPM refusal now goes to the unrecognised ledger (the existing fallthrough), not a bench. If a bench is wanted for it, that is a routing decision left open.
