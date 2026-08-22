# Deprecated — do not run

**`catalogue_local.py`** asked the local model to catalogue franchises from memory. It produced
confidently wrong facts that nothing on this machine could detect — it recorded Bleach's
Yasutora Sado as "Chad (Seraura Urahara)" — and it violates the owner's standing research
policy (OWNER_DESIGN_DECISIONS.md, 2026-08-19): *"EVERYTHING IS FULL DEPTH FULL BREDTH AND IS
INCONCLUSIVE THEN STATED AS SUCH BUT GENUINE ATTEMPTS MUST BE MADE."* Model recall is not a
genuine attempt; it is a guess wearing a citation.

Superseded by `src/catalogue_web.py` (real wiki retrieval, Attestation: Transcribed) and
`src/catalogue_aurora.py` (the owner's own XML). Kept only as a record of the failure mode.
