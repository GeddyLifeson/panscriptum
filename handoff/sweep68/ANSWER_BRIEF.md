# Sweep68 — answer your own questions (owner ruling 2026-09-30)

The owner has ruled: **open questions are answered in-run, by us, not queued for a person** —
unless they are on the reserved list below. You left questions in your `FIX_batchNN.json`. Answer
every one now. Same rules as `FIX_BRIEF.md` (your modules only, never drill.py / verify_math.py /
config.yaml, never run daemons or model calls, no heredoc backslashes, `pyflakes` clean, do not
spawn subagents).

## Reserved for the owner — do NOT decide these, only restate them with options + a recommendation
1. The owner-held gates: `prose_enabled`, `step4_enabled` (never touch config.yaml).
2. Money, accounts, credentials, paid or external services.
3. Irreversible destruction of the owner's data (deleting records/chapters/history). Moving aside
   to a restorable place is fine.
4. CLAUDE.md Hard Rules 2-4: which spine code / shelfmark / assay decimal a source or entity gets;
   curatorial wording inside assay sheets or chapters.
5. Anything that LOOSENS a safety gate (a prose gate letting more through, removing a halt check, an
   assay guard accepting more). Tightening is yours.

## Everything else: decide it
For each question: read the code and data, decide, and either
* **change it** — smallest root-cause change, a comment citing "sweep68 bNN <id>, answered under
  the 2026-09-30 ruling" with the reasoning, and a drill net + meta + revert exactly as in
  `FIX_BRIEF.md` (key `bNN_q_<slug>`, proved False under the revert and True on the fix); or
* **keep it** — when it is deliberate or the change costs more than it buys. Say why concretely.
  A keep needs no net.

For a genuine judgment call, argue the opposite side to yourself in writing before deciding, and
record both sides in `how`. Adding a halt interlock to a derived-data writer that lacks one IS in
scope (it tightens); if you add one, say so, because the coordinator must add the module to the
interlock rosters.

## Deliverable
`handoff/sweep68/ANSWER_batchNN.json`: one object per question —
`{"id", "file", "verdict": "changed|kept|reserved", "decision": "<one sentence>", "how":
"<reasoning, both sides for judgment calls>", "net": "<key or null>", "red_green_checked": bool,
"new_interlock": "<module or null>"}`.
Return ONLY a compact summary (under 120 words): counts by verdict, files changed, interlocks
added, and each `reserved` item in one line.
