# RE-DERIVE, 2026-09-08 — `data/GENRES.json` and `data/GROUNDINGS.json`

**Owner ruling of 2026-09-08, question 10, "Stored files a fixed writer would now compute
differently", option (a): *re-derive all of it, with a snapshot and a before/after table.***
Orders `b317ba3a4f36` (GENRES) and `3eff62be6cc3` (GROUNDINGS).

This file **is** the before/after table the ruling requires. The point of the requirement is that
these are PUBLISHED numbers: `navtree.py` and `pipeline.py` read them, and a re-derive that moves
them silently is indistinguishable from a corruption. So the movement is written down.

## The snapshot

Taken before anything ran, and kept:

| file | snapshot |
|---|---|
| `data/GENRES.json` (87,473 B) | `state/backups/GENRES.json.pre-rederive-20260908` |
| `data/GROUNDINGS.json` (82,442 B) | `state/backups/GROUNDINGS.json.pre-rederive-20260908` |

## What was re-derived, and why it moved

Both modules carried the identical defect: `classify_text(text, top=3)` truncated a ranked list
and `classify_source` then used the **truncated** list as the denominator of the confidence it
published. Eleven genres scored, three survived; five groundings scored, three survived. The code
was fixed on 2026-08-25 (`top=None` in both, orders `bc0b85ea353b` and `e2b3af23cb8a`) and the
stored files were deliberately left stale because re-deriving them moves published numbers. This
ruling authorised the move.

Commands, both rc=0: `src/genre.py --write` (12.6 s), `src/grounding.py --write` (23.6 s).

## `data/GENRES.json` — 210 rows before, 210 after

| measure | before | after |
|---|---|---|
| rows | 210 | 210 |
| confidence figures that changed | — | **193** |
| genre labels that changed | — | **9** |
| rows whose `runners_up` widened | — | **210** (all of them: 2 of 10 → the full field) |
| flagged mixed-source (`confidence < 0.45`) | **46** | **110** |
| newly flagged | — | **67** |

**Every confidence moved DOWN**, which is the expected direction: the denominator grew from three
scores to eleven. Largest moves:

| source | genre | before | after |
|---|---|---|---|
| Transformers | cyberpunk | 0.672 | 0.347 |
| Rick and Morty | space_opera | 0.715 | 0.393 |
| Marvel | mythology | 0.535 | 0.225 |
| Ghost Recon | military_modern | 0.771 | 0.461 |
| Gundam (all centuries, incl. G Gundam) | space_opera | 0.687 | 0.383 |
| The Amazing World of Gumball | whimsy | 0.602 | 0.315 |
| Yakuza | high_fantasy | 0.671 | 0.385 |
| Mario and his expanded universe | high_fantasy | 0.538 | 0.258 |
| Call of Duty Zombies | military_modern | 0.595 | 0.323 |
| Getter Robo | space_opera | 0.690 | 0.422 |
| City Hunter | superhero | 0.515 | 0.250 |
| Rosario + Vampire | eastern | 0.708 | 0.466 |

**The nine label changes**, which the order did NOT predict — it measured **zero** label changes
on 2026-08-25. The difference is the corpus, not the fix: these files are derived from
`data/records/`, which the crawl has been rewriting continuously for two weeks, so this pass
re-derives against more text as well as against a corrected denominator. Recorded rather than
smoothed over, because "0 label changes" is what a later reader would otherwise expect to find.

| source | before | after |
|---|---|---|
| Adventure Time | high_fantasy | whimsy |
| Arcanum Worlds (Odyssey of the Dragonlords) | mythology | high_fantasy |
| He-Man / Masters of the Universe | high_fantasy | mythology |
| Legend of Zelda | mythology | high_fantasy |
| Soul Calibur | eastern | military_modern |
| Splinter Cell | eastern | military_modern |
| Terminator | cyberpunk | military_modern |
| Thomas the Tank Engine | mythology | whimsy |
| all Final Fantasy | high_fantasy | military_modern |

The mixed-source flag going 46 → 110 is the whole point of the fix and not a regression: those 67
sources were always mixed, and the truncated denominator was under-flagging them. `genre.py`'s own
docstring states the intent — *"a source that scores 40 for grimdark and 38 for horror is NOT
confidently either, and the record should say so rather than pick."*

## `data/GROUNDINGS.json` — 209 rows before, 210 after

| measure | before | after |
|---|---|---|
| rows | 209 | 210 |
| confidence figures that changed | — | **38** |
| grounding labels that changed | — | **21** |
| rows whose `runners_up` widened | — | **207** (2 of 4 → the full field) |
| rows below the 0.5 contested line | **165** | **159** |
| newly below it | — | **9** |
| added | — | Bone (Jeff Smith), aurora_mods (Way of the Inkmaster), the Sex Worker background |
| removed | — | Lost Mines of Phandelver, the Witch Tradition |

Largest downward moves:

| source | grounding | before | after |
|---|---|---|---|
| Soul Calibur | eternal_cycle | 1.000 | 0.400 |
| Diablo | emanation | 1.000 | 0.593 |
| Legend of Zelda | immanent | 0.702 | 0.348 |
| KibblesTasty (techno-psionic line) | immanent | 0.667 | 0.500 |
| Dragon Ball Z | ex_nihilo | 0.600 | 0.451 |
| all Final Fantasy | immanent | 0.516 | 0.421 |
| major fantasy pantheons | ex_nihilo | 0.558 | 0.473 |
| Pantheon: Mesoamerican | demiurgic | 0.529 | 0.450 |
| DC | ex_nihilo | 0.471 | 0.403 |
| Pantheon: Hindu | eternal_cycle | 0.610 | 0.562 |

**The four sources the order named as wrongly reported settled are now reported contested**, which
was the finding's whole substance: Marvel 0.45, Bleach, major fantasy pantheons 0.473 and Pantheon:
Mesoamerican 0.450 all sit under the 0.5 line in the new `contested cosmogonies` list, which now
prints 14 sources.

**Eighteen of the 21 label changes are `ungrounded -> <a real type>`.** That is the corpus growing,
not the denominator: a source with no matching cue text scores nothing and is stored `ungrounded`
with confidence 0.00, and eighteen of them have since been mined enough text to score at all. Three
are genuine re-rankings under the full field: DC `ex_nihilo -> emanation`, Dragon Ball Z
`ex_nihilo -> emanation`, all Final Fantasy `immanent -> emanation`, plus Soul Calibur
`eternal_cycle -> emanation`.

## Reversal

`copy state\backups\GENRES.json.pre-rederive-20260908 data\GENRES.json` (and the same for
GROUNDINGS) puts the previous numbers back exactly. Nothing else was touched by this pass.

## What this pass did NOT do

`scope.build()` — the third limb of ruling 10a, order `481ef92af785` — is **not** part of these two
orders and was not run here. `SCOPE.json`'s 146 unstamped ceilings and `magnitude.host_ceiling`
reading them as authoritative clamps are still outstanding and belong to whoever holds that order.
