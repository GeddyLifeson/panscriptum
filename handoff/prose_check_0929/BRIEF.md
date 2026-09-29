# Prose continuity check — brief (2026-09-29)

Repo: C:\Users\imarl\panscriptum-library-kit. READ-ONLY: never edit anything under output/, data/, src/, prompts/.
Do not spawn subagents. Do not run any project script except reading files.

You are checking ONE generated chapter of the Panscriptum (a Library-of-Babel style encyclopedia of
fictional worlds) against its CANON: the exact job the writing model was given.

Inputs (paths given in your prompt):
- the chapter: output/raw/<name>.md
- its canon: handoff/prose_check_0929/<name>.canon.json -- the manifest job: `entities` (each with name,
  category, description, magnitude, etc.) and source context. This is the ONLY factual canon.
- the house style contract, read first: prompts/system_style.txt (and skim CLAUDE.md "Hard rules" 1, 3, 4, 5).
  It defines the Entry Template, the Four Hands marginalia (in-world commentary voices), the honest
  placeholders (`Ω › ? › ...` shelfmarks, "Magnitude: unassayed", "Threads pending"), and what the
  prose may and may not add. Something the contract explicitly permits is NOT a finding.

Check for, in order of severity:
1. INVENTED FACTS (Hard Rule 1): any concrete claim about an entity -- relationship, event, ability,
   location, date, number, role -- that its canon description does not support. Marginalia voices
   are in-world commentary; a marginal note that asserts a NEW concrete fact still counts.
2. CONTRADICTIONS with canon (wrong category, wrong magnitude/band, a description reversed or
   conflated with another entity, an entity from a different source).
3. MISSING OR EXTRA ENTRIES: every canon entity should have an entry; flag any entry not in canon.
4. PLACEHOLDER VIOLATIONS: an invented shelfmark, an assay decimal (e.g. "M3.52 ± 0.12") where the
   contract asks for band-only, cross-franchise Threads asserted while Threads are pending.
5. FRAME BREAKS: meta-language (talking about "the model", "the prompt", "the data", "wiki") inside
   in-world prose.

For each finding quote the chapter text (under 20 words), name the entity, cite the canon field it
contradicts or lacks, and give a severity: HIGH (invented/contradicted fact or placeholder violation),
MEDIUM (unsupported embellishment that reads as fact), LOW (vague flourish, frame wobble).

Write your report to handoff/prose_check_0929/<name>.continuity.md and return ONLY a compact summary
(under 150 words): entry count vs canon, counts by severity, and the three worst findings.
