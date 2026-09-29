# Prose continuity check — 2026-09-29

Ten recent chapters (5 Digimon Places, 5 Arcanum Worlds: Powers, Peoples, Media, Events,
Persons) were each checked by a `continuity-checker` agent against the exact manifest job the
writing model was given (`<name>.canon.json`), under the house style contract. A separate
`avoid-ai-writing` detect pass read all ten (`AI_PROSE_DETECT.md`). Nothing was edited.

## The finding: every sampled chapter breaks Hard Rule 1

| chapter | entries vs canon | HIGH | MEDIUM | LOW |
|---|---|---|---|---|
| II_K_2_Places_321_330 | 10/10 | 10 entries | 4 | 6 |
| II_K_2_Places_231_240 | 10/10 | 11 | 9 | 5 |
| II_K_2_Places_151_160 | 10/10 | 13 | 19 | 8 |
| II_K_2_Places_51_60 | 10/10 | 9 | ~12 | ~7 |
| II_K_2_Places_1_10 | 10/10 | 6 clusters | 8 | 6 |
| II_L_7_4_Powers_31_40 | 10/10 | 10 entries (~25 claims) | 6 | 5 |
| II_L_7_4_Peoples_11_20 | 10/10 | 6 | ~16 | ~14 |
| II_L_7_4_Media_21_30 | 10/10 | ~25 | ~15 | ~11 |
| II_L_7_4_Events_121_130 | 10/10 | 9 | 9 | 8 |
| II_L_7_4_Persons_171_180 | 10/10 | 5 | 11 | 4 |

What HOLDS everywhere: entry coverage (100 of 100), honest shelfmarks, "unassayed", Threads
pending, no assay decimals. The structural guards work.

What FAILS everywhere: the prose expands one-line canon descriptions with invented detail
(domains for gods, contents for books, roles for characters), and the QUILL marginalia assert
first-person eyewitness events in ~87 of ~100 entries ("I was there when the Hypnos towers
fell", "I fought one in the ruins"). Some are outright contradictions of canon (a clash
attributed to the wrong person; "Class: Event" for a Character; Gennai's forms given to Dark
Gennai). Frame breaks recur ("I played through Digimon Data Squad", "XP", "the text does not
elaborate"). Template drift: a literal `[places/things/events]` placeholder, a truncated
shelfmark, wrong Instrument lines, stray glyphs.

## Upstream cause of the Digimon "Places" chapters

The canon for II_K_2_Places_321_330 is ten entries with `type: Character` and
`category: Places & Locations`. Corpus-wide, **13,394 of 133,118 Character-typed entries
(10.1%) carry the Places category**, every one of them already judged by phase_entrypass
(Marvel 7,684, DC 1,462, Mario 819, SpongeBob 705, Digimon 463, ...). A random sample is
unambiguously people. Two cheap explanations were tested and ruled out: a trailing universe
qualifier in the name (8.7% with, 10.6% without) and an off-by-one in the batch (misfiled
entries' neighbours are no more place-like than correctly filed ones'). The prompt numbers the
categories correctly. So a person reaches a Places chapter and the writing model, told to
describe a place, invents one.
