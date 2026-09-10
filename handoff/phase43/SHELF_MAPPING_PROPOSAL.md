# Phase 4.3 — Concordance shelf mapping: SIGNED, and TWO ROWS STILL OPEN

**Nothing here has been written to the spine, and nothing can be yet — see the blocker at the foot of this file.** This maps the 31 shelves of the Chronicle's *THE CONCORDANCE NOW — CANON POSITIONS BY SHELF* table onto Acquisitions Roll sources. Order `c39a2c0e1bef`.

**Signed by the owner 2026-09-09**: 28 shelves mapped, reaching **85,281 entries** against the 3 threads the thin leg yields today. One shelf — **The One War** — is signed as mapping to NO source, and the charter settles it: Collection VIII's own Canon list carries `VIII.8 — CANON OF THE ONE WAR (30 vols)`, so that row is a position of the Library, not of a shelf.

**TWO SHELVES REMAIN OPEN AND WERE DECLINED ON PURPOSE**, including under a general instruction to proceed: **Masked Multiverses** and **Rot City**. Neither sentence names a work, character or place. §7G's one hard constraint is that T3 joins on EVENT PARTICIPATION and never on resemblance, and Masked Multiverses alone would put a thread on Marvel and DC — 114,730 entries — on the strength of the phrase "comic-time perpetual". Rot City has two equally good candidates at the same spine code. Both need a person's word.

**Every mapped source was checked to exist on the roll by exact name and to resolve to a spine code.** A source that is not on the roll cannot appear here — the first draft proposed `Magic: The Gathering - all planes` with a hyphen where the roll uses an em dash, and that check refused the row.

## Summary

| grade | shelves | meaning |
|---|---|---|
| MAPPED | 28 | signed; the evidence names a work, character or place unique to that source |
| SIGNED, NO SOURCE | 1 | The One War = VIII.8, a Canon of the Annex, not a shelf |
| STILL OPEN | 2 | the evidence names nothing; mapping would be resemblance |

**THE BLOCKER, found 2026-09-09 and not previously named.** No T3 edge can be emitted yet whatever this table says. `threads.edge()` refuses any address that does not resolve NOW (§6, the anti-dangling rule), and its `known_codes` is built only from the SOURCES' own spine codes. A T3 points at an Annex address — STEP4_PLAN §3's worked example is `VIII.9 (the succession wars)` — and no `VIII.n` code is loaded anywhere a program can reach. The charter DOES define them, all 17 Canons and 275 volumes, and they are now parsed to `data/ANNEX_CANONS.json`; what is still missing is the shelf-to-Canon mapping, which is a second curatorial call. See the work order.

A row left open stays unmapped rather than guessed.

---

### Dragon Courses  —  **DIRECT**

> Post-Tournament of Power; Moro and Granolah incidents ratified; Black Frieza on promotion watch

| proposed source | spine | entries |
|---|---|---|
| Dragon Ball Z | `II.A.1` | 6,923 |

Tournament of Power, Moro, Granolah and Black Frieza are Dragon Ball Super arcs.

---

### Grand Line  —  **DIRECT**

> Egghead incident in progress; the Void Century's erasure cracking; final war forming

| proposed source | spine | entries |
|---|---|---|
| One Piece | `II.A.3` | 785 |

The Egghead incident and the Void Century are One Piece, and 'Grand Line' is its own in-universe geography.

---

### Shinobi Countries  —  **DIRECT**

> Boruto era; the God Tree question reopened; Naruto's curve plateaued, disputed

| proposed source | spine | entries |
|---|---|---|
| Naruto | `II.A.4` | 2,969 |

Names Naruto outright, plus the Boruto era and the God Tree.

---

### Joestar Meridian  —  **DIRECT**

> Second timeline current (post-JoJolion); first timeline sealed at Stone Ocean's reset

| proposed source | spine | entries |
|---|---|---|
| JoJo's Bizarre Adventure | `II.A.2` | 823 |

Names JoJolion and Stone Ocean; the two-timeline structure is JoJo's own.

---

### Hokuto Star  —  **DIRECT**

> Post-Raoh; Kenshiro walking; Erratum 1 pending ratification

| proposed source | spine | entries |
|---|---|---|
| Fist of the North Star | `II.A.5` | 90 |

Names Raoh and Kenshiro. Hokuto is the series' own name for its school.

---

### Circuit worlds  —  **DIRECT**

> SF6/Tekken 8 era; Chōjin Perfect Origin resolved; Soul Edge contained, not destroyed

| proposed source | spine | entries |
|---|---|---|
| Street Fighter | `II.A.7` | 1,121 |
| Tekken | `II.A.7` | 129 |
| Kinnikuman | `II.A.7` | 241 |
| Soul Calibur | `II.A.7` | 3,333 |

Four named: SF6, Tekken 8, Chojin Perfect Origin (Kinnikuman), Soul Edge (Soul Calibur). DELIBERATELY NOT EXTENDED to Killer Instinct or ARMS -- both are fighting games on the roll, neither is named here, and adding them would be resemblance.

---

### Masked Multiverses  —  **REFUSED**

> Comic-time perpetual; latest renewals filed as refractions per standing doctrine

**No source proposed.** 

'Comic-time perpetual; renewals filed as refractions' names NO work. The register points at the superhero shelf (Marvel, DC, possibly Invincible), but that is inference from tone, which is exactly what §6 forbids. OWNER TO NAME THE MEMBERS.

---

### Blind Eternities  —  **DIRECT**

> Post-Phyrexian invasion; the Omenpaths open, Sparks scarce; Rabiah still closed

| proposed source | spine | entries |
|---|---|---|
| Magic: The Gathering — all planes | `II.E` | 421 |

Phyrexian invasion, Omenpaths, Sparks and Rabiah are all Magic's own vocabulary.

---

### Far Galaxy  —  **DIRECT**

> Post-sequel restoration; New Jedi Order forming; Legends canon co-ratified as mirror

| proposed source | spine | entries |
|---|---|---|
| Star Wars | `II.F.1` | 694 |

New Jedi Order and the Legends/canon distinction are Star Wars.

---

### Federation Reaches  —  **DIRECT**

> Braided: Picard-era prime, 32nd-century Discovery relief, Kelvin mirror — all filed

| proposed source | spine | entries |
|---|---|---|
| Star Trek | `II.F.2` | 585 |

Picard-era prime, 32nd-century Discovery and the Kelvin timeline are Star Trek.

---

### Relay Network  —  **DIRECT**

> Post-Crucible; ending indeterminate by design; the geth question memorialized

| proposed source | spine | entries |
|---|---|---|
| Mass Effect | `II.F.3` | 2,569 |

The Crucible and the geth question are Mass Effect's ending.

---

### Forerunner Sphere  —  **DIRECT**

> Post-Infinite; the Endless pending; Chief active

| proposed source | spine | entries |
|---|---|---|
| Halo | `II.F.4` | 2,515 |

Post-Infinite, the Endless, and Chief are Halo.

---

### Traveler's Wake  —  **DIRECT**

> Post-Final Shape; the Witness ended; Echoes and the new frontier current

| proposed source | spine | entries |
|---|---|---|
| Destiny 1 & 2 | `II.F.5` | 128 |

The Final Shape, the Witness and Echoes are Destiny.

---

### Grim Dark  —  **DIRECT**

> Era Indomitus: the Rift open, Guilliman regent, the Lion awake; Embargo holding

| proposed source | spine | entries |
|---|---|---|
| Warhammer 40,000 | `II.G.1` | 3,917 |

Era Indomitus, Guilliman as regent and the Lion awakening are 40k.

---

### Old World  —  **DIRECT**

> Ended (End Times ratified); records complete; successor-age noted but unshelved

| proposed source | spine | entries |
|---|---|---|
| Warhammer Fantasy | `II.G.2` | 7,012 |

The End Times ended the Old World; 'successor-age noted but unshelved' is Age of Sigmar, correctly left off the roll.

---

### Aurbis  —  **DIRECT**

> Late Fourth Era (Skyrim's dragon crisis ratified); the next kalpa unscheduled

| proposed source | spine | entries |
|---|---|---|
| all Elder Scrolls | `II.L.2` | 205 |

Aurbis is the Elder Scrolls' own cosmological term; Skyrim's dragon crisis is named.

---

### Sanctuary  —  **DIRECT**

> Diablo IV era: Lilith's incursion done, Mephisto moving

| proposed source | spine | entries |
|---|---|---|
| Diablo | `II.L.3` | 5,480 |

Diablo IV, Lilith and Mephisto are named; Sanctuary is Diablo's world.

---

### Wraeclast  —  **DIRECT**

> Post-Sirus Atlas era; the Exile ascendant

| proposed source | spine | entries |
|---|---|---|
| Path of Exile | `II.L.4` | 262 |

Wraeclast is Path of Exile's continent; Sirus and the Atlas are named.

---

### Crystal Multiverse  —  **DIRECT**

> XVI complete; XIV at Dawntrail; the shards' story ongoing

| proposed source | spine | entries |
|---|---|---|
| all Final Fantasy | `II.L.5` | 26,679 |
| the FFXIV / Eorzea conversion | `II.L.7` | 685 |

XVI and XIV at Dawntrail are named. BOTH roll entries are proposed because the roll carries the FFXIV conversion as its own source, and the sentence names XIV explicitly.

---

### Great Wheel  —  **SIGNED**

> 5e-era Realms (post-Second Sundering) per your shelf's supplements

| proposed source | spine | entries |
|---|---|---|
| Curse of Strahd | `II.L.7` | 33 |
| Descent into Avernus | `II.L.7` | 34 |
| Dungeon of the Mad Mage | `II.L.7` | 388 |
| Hoard of the Dragon Queen | `II.L.7` | 10 |
| Out of the Abyss | `II.L.7` | 324 |
| Princes of the Apocalypse | `II.L.7` | 185 |
| Rime of the Frostmaiden | `II.L.7` | 106 |
| Rise of Tiamat | `II.L.7` | 140 |
| Storm King's Thunder | `II.L.7` | 40 |
| Sword Coast Adventurer's Guide | `II.L.7` | 176 |
| Tomb of Annihilation | `II.L.7` | 219 |
| Waterdeep: Dragon Heist | `II.L.7` | 135 |
| Lost Mines of Phandelver | `II.L.7` | 0 |
| Ghosts of Saltmarsh | `II.L.7` | 15 |
| Tales from the Yawning Portal | `II.L.7` | 54 |
| DMs Guild: Mirt's Undermountain Survival Guide | `II.L.7` | 107 |
| DMs Guild: The Great Dale | `II.L.7` | 129 |
| Acquisitions Incorporated | `II.L.7` | 356 |
| Adventurers League | `II.L.7` | 477 |
| Extra Life | `II.L.7` | 12 |

OWNER-SIGNED 2026-09-09: the REALMS PROPER only -- the 20 Forgotten Realms adventures and settings. The row says '5e-era Realms', and II.L.7 holds 60 sources of which only these are set in the Realms. DELIBERATELY EXCLUDED: the 7 setting-neutral core rules (the PHB is not IN the Realms), the 9 other settings (Eberron, Ravnica, Theros, Wildemount, Tal'Dorei, Thylea, Midgard -- a Great Wheel canon position would be a claim the Chronicle never made about them), and the 24 third-party mechanical lines. Note the FFXIV/Eorzea conversion sits in that excluded set and is already mapped to Crystal Multiverse, so including it here would have double-mapped it.

---

### 2077 branch  —  **DIRECT**

> c. 2296 local: NCR-Brotherhood aftermath, Commonwealth settled, TV-era Coast events filed

| proposed source | spine | entries |
|---|---|---|
| all Fallout | `II.J.1` | 245 |

NCR-Brotherhood aftermath, the Commonwealth and the TV-era Coast events are Fallout; 2077 is its war year. Note Cyberpunk 2077 is NOT on the roll, so the name is not ambiguous in practice.

---

### Fury / Metro / Swarm branches  —  **DIRECT**

> Furiosa-to-Fury-Road era; Metro Exodus east; Sera post-Locust; flu endemic

| proposed source | spine | entries |
|---|---|---|
| Mad Max | `II.J.2` | 251 |
| all Metro | `II.J.3` | 303 |
| Gears of War | `II.J.4` | 2,312 |

Three named branches: Furiosa/Fury Road, Metro Exodus, and Sera post-Locust (the Swarm is Gears').

---

### Century of Fire  —  **DIRECT**

> MW/BF refractions in their reboot cycles; Black Ops at the Gulf War file

| proposed source | spine | entries |
|---|---|---|
| all Modern Warfare | `II.I.2` | 528 |
| all Battlefield | `II.I.2` | 1,029 |
| all Black Ops | `II.I.1` | 1,470 |

MW, BF and Black Ops at the Gulf War are named. DELIBERATELY NOT EXTENDED to Call of Duty Zombies, which is a separate roll entry and is not named here.

---

### Neon Meridian  —  **DIRECT**

> Post-MGSV century locked; Yakuza at Infinite Wealth; Bebop's session ended (see you, space cowboy)

| proposed source | spine | entries |
|---|---|---|
| Metal Gear Solid | `II.H.2` | 622 |
| Yakuza | `II.H.3` | 1,499 |
| Cowboy Bebop | `II.H.1` | 383 |

MGSV, Yakuza at Infinite Wealth, and Bebop's session ending are named.

---

### Companion Worlds  —  **DIRECT**

> Paldea league current; Digital World's third sovereignty; Palpagos industrializing

| proposed source | spine | entries |
|---|---|---|
| Pokemon | `II.K` | 357 |
| Digimon | `II.K.2` | 2,577 |
| Palworld | `II.K.3` | 194 |

Paldea (Pokemon), the Digital World (Digimon) and Palpagos (Palworld) are named.

---

### Realms of Heart  —  **DIRECT**

> Post-KH3: Sora missing, Riku searching; the door not yet dark

| proposed source | spine | entries |
|---|---|---|
| Kingdom Hearts (binding cosmology of the Disney set) | `II.O.1` | 390 |

Post-KH3, Sora and Riku are named.

---

### Ludic Spheres  —  **SIGNED**

> The Island's current season; arenas in service; skaters skating; the Aeons popping

| proposed source | spine | entries |
|---|---|---|
| Fortnite | `II.P.1` | 245 |
| the Skate games | `II.P.3` | 67 |
| all Bloons TD | `II.M.3` | 341 |
| Rocket League | `II.P.2` | 107 |

OWNER-SIGNED 2026-09-09. Three rest on the sentence: 'The Island's current season' is Fortnite, 'skaters skating' is the Skate games, 'the Aeons popping' is Bloons TD (popping is its verb). THE FOURTH RESTS ON SHELVING, NOT ON THE SENTENCE, and is marked so it can be reversed: 'arenas in service' fits Rocket League and ARMS equally, and Rocket League was taken because the charter already numbers Fortnite, Rocket League and Skate as II.P.1/.2/.3 -- one family -- while ARMS sits at the bare parent II.P beside Crash Bandicoot and Rock of Ages.

---

### Long Night  —  **DIRECT**

> Slayer sealed post-Dark Lord; Elysium's pale advancing 2mm/year; Isaac still in the basement

| proposed source | spine | entries |
|---|---|---|
| Doom | `II.N.2` | 661 |
| Disco Elysium | `II.N.4` | 247 |
| The Binding of Isaac | `II.N.3` | 924 |

The Slayer and the Dark Lord (Doom), Elysium's pale advancing 2mm/year (Disco Elysium's own figure), and Isaac in the basement.

---

### Rot City  —  **REFUSED**

> Mid-reset, as always

**No source proposed.** 

'Mid-reset, as always' names nothing at all. Hotline Miami and Katana Zero both sit on the roll and both suit a looping violent city, which is precisely why this must not be guessed. OWNER TO NAME IT, or rule the row unmapped.

---

### Chroma Wastes  —  **DIRECT**

> Rowan and Wendy, deep crimson and deep blue; the amethyst working attested

| proposed source | spine | entries |
|---|---|---|
| The Amethyst / Cockroach King screenplay (Chroma Wastes) | `II.A.10` | 23 |

The strongest row in the table: the roll entry CARRIES the shelf name in its own title, and Rowan, Wendy and the amethyst working are the screenplay's.

---

### The One War  —  **SIGNED-UNMAPPED**

> Holding, mostly; losing, slowly; recording, always

**No source proposed.** 

OWNER-SIGNED 2026-09-09 as MAPPING TO NO SOURCE, and the charter settles it rather than a reading: Collection VIII's Canon list contains 'VIII.8 - CANON OF THE ONE WAR (30 vols)'. The One War is the Annex's own Canon -- the Silence's offensives as dated campaign history -- not a catalogued property. So the Concordance table's last line is a position of the LIBRARY, not of a shelf, and 'Holding, mostly; losing, slowly; recording, always' reads as the Custodes describing their own front. No source is mapped and none should be.

