# THE PANSCRIPTUM — AUTONOMOUS COMPLETION PLAN

*Authored 2026-08-19. This is the working spec for finishing the library without supervision.
`src/pipeline.py` implements it; the hourly custodian check-in builds the next phase from it.*

---

## 0. Operating principles

These are not preamble. Every phase below is constrained by them, and a phase that violates one
is wrong even if its output reads well.

**P1 — Nothing is invented.** Every factual claim traces to transcribed source text. The model's
job is judgment and composition over supplied evidence, never recall. This is the rule the whole
project exists to protect, and it has already been violated once: asked to catalogue *Bleach*
from memory, the model produced "Chad (Seraura Urahara)" for a character named Yasutora Sado.
That is why cataloguing was rebuilt around wiki retrieval.

**P2 — Attestation is honest.** Each record carries the grade its provenance earns, per Vade
Mecum §II.4 (`Witnessed → Instrumented → Transcribed → Reconstructed → Disputed`).
Currently: cloud-researched = as filed; wiki-scraped = `Transcribed`; Aurora XML and Local
Register = `Transcribed`. Nothing is promoted without new evidence.

**P3 — No fabricated Assay.** Band only (`M4`), never a decimal (`𝔄 M4.31 ± 0.30`). Decimals
require the nine-measure worksheet of Charter Part Three against cited feats. Hard Rule 3.

**P4 — Unknown stays unknown.** `?` for uncharted rungs, `unassayed` for unmeasured power,
"None currently on file" for absent contradictions. Absence is a correct answer, and a short
true entry beats a padded invented one (Ground Rule 2).

**P5 — Every unit is checkpointed.** State is written atomically after each unit. A crash costs
one unit, never a phase. Assume the process will be killed.

**P6 — Token frugality.** The heavy work is local (Ollama or plain Python). Claude supervises
hourly, builds one phase per check-in, and never re-verifies verified work.

**P7 — Aperture governs scope** (I.9 Part One). An entry shows exactly as much of the omniverse
as its subject's attested reach warrants — Local (+ mandatory Position Paragraph), Road,
Concordance, or Full. Under-scoping and over-scoping are both review failures with their own
stamps. Length is computed, never chosen.

**P8 — No meta, anywhere in the text.** No DM, player, NPC, tier of play, CR, saving throw, hit
points, campaign, or table. The books are read in-universe only. The owner's ruling is on file
verbatim; the charter's own Parts Six, Seven, and the Collection III/IV/IX descriptions all
still violate it and are pending amendment. **This document governs entry shape until they are
amended.**

**P9 — A genuine attempt precedes every "unknown."** Owner policy, verbatim: *"EVERYTHING IS
FULL DEPTH FULL BREDTH AND IS INCONCLUSIVE THEN STATED AS SUCH BUT GENUINE ATTEMPTS MUST BE
MADE."* Coming up empty after real research is honest; coming up empty because nobody looked is
not. Note this sits in real tension with P3/H5 — the resolution is that the *attempt* is a
research pass (wiki retrieval, the Chain of Defeats), and only its *failure* licenses
`unassayed`. A blank field with no attempt behind it is a policy violation, not a modest one.

### The doctrine every phase must not violate

| Rule | Source | Consequence if broken |
|---|---|---|
| No lossless scalar | X.2 Thm 1 | Publish the **vector**; 𝔄 is a declared projection |
| Curl is measurable | X.2 Thm 2 | Report η; a ladder cannot represent cycles |
| Anchor is hegemonic, not energetic | X.2 §3 | Kenshiro anchors M3 without cracking continents |
| Measurement is touch | X.2 H2 | M8+ is permanently Reconstructed |
| DECLINED is a **type error**, not a big number | X.2 H4 | The MΩ wall is type-theoretic; no refinement crosses it |
| No worksheet, no number | X.6 H5 | Bulk entries are band-bounded, never scored |
| Faculties are underdetermined by the eight axes | X.6 Thm 1 | INT/WIS/CHA need Acumen/Discernment/Suasion |
| Honest nulls are **computed** | X.6 Thm 3(ii) | A relic's "Not applicable" is an empty supremum |
| Suasion excludes force and compulsion | X.6 §3 | A mind-controller prints low CHA, high Transgression |

---

## 1. Where things stand

| | |
|---|---|
| Sources catalogued | **211 / 215** |
| Total entries | **52,343** |
| Volumes written | 0 (deliberately — see §2) |

**The 4 uncatalogued:** HAWX, Heaven's Lost Property, major live-action Disney films, Twilight
Imperium. All resolve to a wiki whose containment check fails. Left uncatalogued on purpose —
the check is what stopped *Curse of Strahd* being scraped from the *Roblox CURSE Wiki*. Fix by
adding a verified subdomain to `WIKI_OVERRIDES` in `src/wiki_source.py`, not by loosening the
check.

**Provenance mix** — this matters for every downstream phase, because a thread anchored to weak
material propagates that weakness:

| Provenance | Sources | Grade |
|---|---|---|
| Cloud session, researched | 115 | as filed |
| Wiki transcription | ~72 | Transcribed |
| Aurora XML (owner's homebrew) | 10 | Transcribed |
| Local Register recovery | 14 | Transcribed |

---

## 2. Why volumes come last

Volume writing was started and deliberately stopped. The owner's constraint: **volumes may only
be written after all 215 are catalogued**, because the Step 4 entanglement pass must interweave
the complete omniverse. A volume written against a two-thirds-populated library would need
rewriting the moment the rest arrived — and worse, its Threads section would be silently
incomplete rather than visibly pending.

`generate.py` hashes source data into its recipe key, so re-cataloguing correctly invalidates
anything built on the old version. That safety net exists, but it is not a licence to write
early.

---

## 3. The phase ladder

Each phase is resumable, and each produces something the next consumes.

### Phase 1 — `synthesis` *(BUILT, complete: 211/211 sources)*

**Unit:** one source. **Cost:** ~13s each, ~186 units, ~45 min total.

Nominates the source's power ceiling and a magnitude band from its own catalogued text. Feeds
the model the 22 longest entry descriptions (longest ≈ most likely to carry a feat) and demands
a quoted `evidence` string.

Guards: output is regex-clamped to `M0`–`M10` or `unassayed`; anything else becomes `unassayed`.
Each record's `synthesis.method` states plainly that this is *not* a Custodial Assay.

Sanity so far: Adventure Time → M7 (GOLB); Alien → M4 (Xenomorph); A Plethora of Paladins →
`unassayed`; Civilization → `unassayed`. Correctly declining is as important as scoring.

### Phase 2 — `entrypass` *(BUILT, running: see HANDOFF.md for live progress)*

**Unit:** 20 entries. **Cost:** ~2,600 units, 35–50h. Runs unattended for days; that is fine.

Two corrections per entry:
1. **Category** — currently inherited from whatever a wiki called it, which is how *Bankai*
   landed in "Vessels & Things". The model reclassifies from the description into the seven
   canonical buckets.
2. **`scale_note`** — extracted **only** where the supplied text states a demonstrated feat.
   Explicitly forbidden from estimating or importing outside knowledge. Empty is the expected
   answer for most entries.

Marks each entry `catalogued: true` so progress is measurable and resumable mid-record.

> **ARCHITECTURE CORRECTION, 2026-08-20 — and its own correction, after reading Part Five.**
>
> The owner's ruling: volumes are organised **by topic across the whole omniverse, never by
> source IP.** Grouping chapters by franchise presumes the library is a shelf of franchise
> encyclopedias, when it is one omniverse whose sources are merely where the evidence came from.
>
> My first response was to design a new two-collection scheme. That was wrong, and it was wrong
> because I had not read Charter Part Five. **The charter is already topical**, and says so in
> Part One: *"COLLECTION — defined by **kind of knowledge**, not by franchise: Worlds, Gods,
> Beasts, Persons, Relics, Powers, Measures, History, Practice."* Collection II is the only
> per-IP one, because it is the *geography* — and even there, a Set is a metaverse, not a
> publisher.
>
> The 523-volume manifest already provides every series the owner asked for. See Phase 6 for
> the mapping. Phase 6's job is **assignment into existing shelves**, not design.
>
> What genuinely follows from the ruling is a requirement on Phase 3: **"Zeus" must be ONE
> canonical entity** carrying four attestations (Marvel, God of War, Riordan, Smite), not four
> entries in four volumes. V.1–V.11 is a *master alphabet across all of Collection II* — the
> charter's own words — which is impossible without cross-source entity resolution. That makes
> `weave` load-bearing for everything downstream.
>
> The history is woven **bottom-up from evidence**, never top-down from a vision — and note
> that the spine already exists: `VIII_MASTER_CHRONICLE.md` is Fascicle One, Ages I–V written,
> closing with the Concordance-Now table of every shelf's canon position at Delivery (1,204 AS).
> Phase 5 expands that spine; it does not start from a blank page. The retired
> `THE_PRIME_OMNIVERSE_CODEX.md` was the top-down artifact, and is exactly what this replaces.

### Phase 3 — `weave` *(BUILT — `src/weave.py`, wired into the runner)*

The charter's Step 4 entanglement. **This is the phase the owner cares most about** — "so that
the omniverse creates consistent storytelling across all the references and IPs."

**Unit:** one source's outbound threads.

Method, and it must be mechanical-first to stay honest:
1. Build a **global entity index** across all 211 records — name → (source, category, id). Plain
   Python, no model.
2. Find **literal cross-source name collisions and near-matches** (normalised). A "Zeus" in
   Marvel, God of War, Riordan and Smite is a real, checkable link.
3. For each candidate pair, ask the model **only** whether the two entries describe the same
   underlying entity, a variant, or an unrelated homonym — supplying both descriptions.
   Three-way classification, not free composition.
4. Emit typed threads: `same-entity`, `variant-of`, `homonym` (recorded so future passes stop
   re-testing it), `archetype-kin`.
5. Anything the text does not support stays `pending the entanglement pass`, per Ground Rule 5.

Output: `data/threads/<source>.json`, plus a global `data/THREAD_INDEX.json`.

Hard constraint: a thread whose two endpoints are both `Reconstructed`/thin material is flagged
`provisional: true`. The grand history must be able to show which of its connective tissue is
load-bearing and which is scaffolding.

**Output revised:** the weave no longer just annotates sources with threads. It produces
`data/CANONICAL_ENTITIES.json` — the resolved entity set, where each canonical entity carries:

```json
{
  "canonical_name": "Zeus",
  "topic": "Persons",
  "attestations": [
    {"source": "Marvel", "entry": "Zeus", "attestation": "Transcribed", "relation": "variant-of"},
    {"source": "God of War", "entry": "Zeus", "attestation": "Transcribed", "relation": "variant-of"},
    {"source": "Pantheon: Greek", "entry": "Zeus", "attestation": "Transcribed", "relation": "same-entity"}
  ],
  "contradictions": ["God of War depicts his death; Riordan does not"],
  "provisional": false
}
```

`contradictions` is populated where attestations genuinely conflict — that is the Contradictions
register doing its job (Vade Mecum §III.4: log both, resolve neither).

### Phase 4 — `chain` — THE CHAIN OF DEFEATS *(to build; Bradley-Terry already written in `rigor.py`, with Ford's condition enforced)*

Owner request 2026-08-20, and it turns out to be charter-native rather than a workaround. The
Master Charter §129 names the **Chain of Defeats** — *"the Order's transitive lattice of who has
beaten whom"* — as one of the three sources a published Assay may derive from, alongside
witnessed feats and instrument readings. X.2 §5 gives the full method.

**The problem it solves.** After the "no feat, no band" rule, most entities are `unassayed` —
correctly, since most text states no feat. But an entity with no feat of its own may still be
*placed* by comparison: if Frost > Tournament-of-Power base Goku, and base Goku > Z-era Whis by
attested feats, Frost inherits a floor. That is the standard scaling argument, and the charter
already formalises it.

**Method, per X.2 §5 (do not improvise past this):**

1. **Extract contests.** Regex pre-filter for contest language (`defeated|slew|surpassed|
   stronger than|no match for|…`) reduces 52,343 entries to ~2,324 candidates. Keyword
   matching alone is far too noisy — observed false positives include "stronger than the
   pain", "can't be beat" as a boast, and "Kill the Past" as a maxim — so each candidate goes
   to the model, which returns a triple only where **two named entities** and a **directed
   outcome** are both present. ~116 batched calls.
2. **Build the multigraph** G of A-defeats-B edges, with context tags (era, form, arc), since
   "Goku" at two power states is not one competitor.
3. **Fit Bradley–Terry** per connected component: `P(A beats B) = e^θA / (e^θA + e^θB)`, θ by
   maximum likelihood, standard errors from the Fisher information of G.
4. **Anchor.** Within a component, entities that already carry an *evidenced* band calibrate
   θ onto the M scale. A component containing no anchored entity yields ordering but no band —
   report the ordering, assign no magnitude.
5. **Propagate** bands to unanchored entities from their fitted θ.

**Honesty constraints, all of which are theorems in X.2 rather than preferences:**

- **Connectivity theorem.** θ differences are identifiable *only within connected components*.
  Two franchises that never contest each other are **statistically incomparable, whatever
  anyone's opinion.** Cross-franchise scaling is legitimate only through an actual attested
  contest edge — never by "vibes" equivalence. Isolated sources get wide intervals *as a
  theorem, not a prejudice*.
- **Curl / non-transitivity.** Real contest data contains cycles (A beats B beats C beats A).
  HodgeRank decomposes the flow `F = grad(θ) ⊕ curl ⊕ harmonic`; the ranking lives in the
  gradient. Compute the **consistency index η = ‖grad F‖² / ‖F‖²** per component and publish
  it. Theorem 2: the predictive error of *any* scalar assay is bounded below by (1 − η). Where
  η is low, say so rather than pretending the ladder holds.
- **Derived ≠ attested.** A band from the chain is stamped `source: "chain-of-defeats"` with
  its citation path (`Frost > ToP-base Goku > Z-Whis`), never presented as a witnessed feat.
  Still band-only; still no decimals without a worksheet.

**Ordering:** must run *after* Phase 3 (`weave`). Cross-source scaling requires resolved
identity — a "Goku" attested in three sources has to be one competitor before any edge
involving him means anything.

### Phase 5 — `cosmology` *(partly built — the tiers are charted in `tiers.py`)*

Builds the omniverse's structural spine **bottom-up from the resolved entity set** — the thing
the retired codex used to assert top-down.

Method:
1. From `CANONICAL_ENTITIES.json`, extract every entity whose text describes a *world, plane,
   realm, dimension or reality-layer* (Places topic + the `Powers` entries that describe
   reality-structure).
2. Cluster by the containment language the sources themselves use ("plane of", "pocket
   dimension", "parallel Earth", "outside time"), plus the Magnitude bands from Phase 1 — a
   source with an M8 ceiling implies a multiversal frame, an M9 a metaversal one.
3. Assemble the ladder empirically: **universe → multiverse → metaverse → xenoverse →
   hyperverse → omniverse**, placing each source's home reality at the rung its own evidence
   supports, and `?` where it does not.
4. Where two sources' cosmologies genuinely touch (a shared entity attested in both), record a
   **convergence** — with the attesting entity as the citation.

Output `data/COSMOLOGY.json`. Every rung placement carries the quoted evidence that put it
there; unsupported placements are `?`, never guessed (P4).

### Phase 6 — `history` *(to build)*

Writes **The History of the Omniverse** — the narrative spine, and the first thing an actual
reader encounters.

Volumes are chronological/structural, not alphabetical, and are derived from the cosmology and
the Events topic:

| Vol | Subject |
|---|---|
| I | Cosmography — the rungs, how the verses nest, what convergence means |
| II | The First Ages — earliest attested events across all sources |
| III+ | The Convergence Wars — where cosmologies collide, ordered by attested scale |
| … | continuing by era, drawn from Events A–Z ordered by Magnitude and attestation depth |

Each claim cites its canonical entity and that entity's attestations. Where the evidence is thin
or the attestations conflict, the history *says so in the text* rather than smoothing it —
"argued" is a legitimate thing for a history to be (Vade Mecum §II.4).

### Phase 7 — `shelve` *(to build; the declared 1–7 order is in `sevenfold.py`)*

**DO NOT INVENT A VOLUME STRUCTURE. IT ALREADY EXISTS.** Charter Part Five is a complete
523-volume manifest (522 delivered, one missing by design — XI.∅, "The Last Page", the campaign
macguffin). An earlier draft of this plan proposed inventing a topical A–Z scheme; that was a
failure to read Part Five, because the charter is *already* topical at the Collection level —
Part One states it outright: *"COLLECTION — defined by **kind of knowledge**, not by franchise."*

The owner's shelving rulings map onto existing shelves rather than replacing them:

| Owner ruling | Existing shelf |
|---|---|
| Persons of Importance A–Z | **V.1–V.11**, "Persons, A through Z, roughly two letters per volume" |
| …banded by Magnitude | **V.12 The Crowned and the Damned** (M5+); and the **Bestiary IV.1–IV.5 is already band-shelved** (M0–M1 / M2–M3 / M4–M5 / M6–M7 / M8–M10) — precedent exists |
| Relic weapons file as Weapons | **VI.1 Arms and Panoplies** vs **VI.2 Relics and Regalia** — the ruling settles a boundary between two existing shelves |
| Wars | **VIII.9 Canon of the Great Wars** (40 vols) |
| Powers | **Collection VII**, by system type |
| Media | **Collection II** volumes' own apparatus; in-fiction media per entry |

So Phase 6's real job is **assignment, not design**: route each canonical entity to its existing
volume, and extend the banding *within* V.1–V.11 per the owner's `Mx A–Z` ruling.

**The genuinely open curatorial work** is the Acquisitions Index (Charter Appendix). 47 populated
sources are on the Acquisitions Roll but have no line in the Index — Bleach, Baki, Invincible,
Rosario + Vampire, Sakamoto Days among them. `manifest_builder.py` skipping them is correct
behaviour, not a bug. Placement is a judgment call the owner made deliberately for the other
~105; propose additions for sign-off, or generate under `UNSORTED.<Category>.PROVISIONAL` as a
clearly-marked stopgap. Never silently invent placement.

**Card format** (Catalog A declares it, and Files A and B already hold 24 + 168 cards; C, D and E
do not exist yet):

```
▮ SPINE — TITLE (vernacular name, where one exists)
Kind • Shelf-load role • Hz hazard • Attestation posture
Scope: one governing sentence — what the volume is for.
⌁ principal threads.
```

**Hazard scale** (declared per Axiom M3, and a field nothing in this pipeline currently captures):
Hz 0 open shelf · Hz I caution, read the preface · Hz II restricted, registry sign-out ·
Hz III sealed stack, a Hand's countersignature · Hz IV *do not open alone; the policy has a
casualty list* · Hz ∅ special conditions printed on the volume.

### Phase 8 — `write` *(to build; `generate.py` is the engine)*

**THE APERTURE DOCTRINE GOVERNS ENTRY LENGTH AND SCOPE** (I.9 Part One). This is the editorial
law the whole library runs on, and no entry may be written without first computing its aperture:

> *"Every entry's aperture — how much of the wider omniverse it must show — equals its subject's
> attested reach."* Set by Magnitude + Vector axis + attestation footprint.

| Aperture | Requirement |
|---|---|
| **Local** | Written wholly in its home frame, closing with a **mandatory Position Paragraph**: where this thing sits in the wider flows *whether it knows it or not* (what it fetches at the Freeport; whether the Survey noted its kind; which Canon files its loss) |
| **Road** | Must situate the subject in at least its own metaverse — rivals abroad, market position, treaty exposure |
| **Concordance** | Written as omniversal civics; assumes no home frame |
| **Full** | Mandated sections: standing in the Concordats; Circuit and Ledger exposure; Office relations; Silence-war relevance; known copies, refractions and impersonators |

Review stamps are mechanical: an entry narrower than its subject warrants is returned
**UNDERSCOPED — WIDEN**; a village blacksmith digressing into multiversal politics is
**OVERSCOPED**. Moth's note on the model case: *"The smith does not know about the Reapers. The
entry should know that he does not know. That, too, is information."*

This is the precise answer to the owner's instruction that a rewritten blurb carry "a few
sentences, maybe some extra details surrounding the thing." The amount is **not uniform** — it is
computed from the subject's own reach. A +1 longsword earns its Position Paragraph; Goku earns
seven mandated sections.

**Volume anatomy** (Charter Part Six), with the owner's amendment applied:

1. The Provenance Plate · 2. Spine Data · 3. Epigraph · 4. The Custos's Preface ·
5. How to Read This Volume · 6. The Entries · 7. ~~Appendix A — For the Table~~ **CUT** ·
8. Appendix B — Thread Index · 9. Appendix C — Contradictions Register · 10. The Colophon

**Entry anatomy** (Charter Part Seven), with the owner's amendment applied:

```
◈ ENTRY NAME
Shelfmark:   Ω › … ›   (? uncharted, ⌀ pervasive — never guessed)
Class:       World / Polity / Person / God / Beast / Relic / Vessel / Praxis / Event / Substance
Magnitude:   band only unless a worksheet exists (H5)
Attestation: the record's real grade — never defaulted to Witnessed
The Record.        in-fiction body, scoped by aperture
Contradictions.    variant canon as unresolved scholarship, or "None currently on file."
Marginalia.        1–3 of the four Hands, each reacting to something specific in THIS entry
▣ The Instrument.  six faculties 1–30 + Transcendence Grade, or "uninstrumented", or the
                   computed null for a relic
⌁ Threads.         every factual claim anchors to a Law citation or an Annex event-code
```

**CUT, and they must not be reinstated:** `▣ For the Table` and `✦ Three Doors`. The owner's
ruling is on file verbatim — *"I don't want for the table shit, these books should read like
in-universe books only, nothing meta about the game they are designed for"* — and *"also yes cut
the dm hooks too."*

⚠️ **The charter itself has not been amended to match, and this is a live hazard.** Part Six
still mandates "Appendix A — For the Table"; Part Seven still prints `▣ For the Table` and
`✦ Three Doors` as canonical; Collection IV is described as shelved *"so a DM can open exactly
one book for the tier they're running"*; Collection III promises "For the Table sidebars";
Collection IX is *"the DM's operational core."* Any future writer reading Part Seven as canon
**will reinstate meta content**. A charter amendment pass is required, and until it happens this
document is the governing text on entry shape.

**Meta-language filter (mechanical, because instruction alone has failed twice).** 7.4% of
`description` evidence text — 3,870 entries, concentrated in the D&D homebrew (Unearthed Arcana
364, KibblesTasty 334, The Elements Beyond 334) — contains `saving throw`, `hit points`,
`players`, `DM`, `CR`. That text is *evidence* and stays as-is, but generated prose must be
scanned for it and rejected, exactly as `scale_note` is scanned for real scale evidence.

## 4. Operating the run

```bash
python3 src/pipeline.py            # resume wherever it stopped
python3 src/pipeline.py --status   # report only
python3 src/pipeline.py --phase 2  # force one phase
python3 src/resync_roll.py         # after ANY concurrent cataloguing
```

**Resync matters.** Every cataloguer rewrites the whole roll after each source, so two running
concurrently will have one clobber the other with a stale copy. This already happened: the
Aurora run wrote 425 entries for Dr. Firestorm's and 681 for The Elements Beyond, then the wiki
run's final save reset both to 0 while leaving the record files intact. Records are the
authority; the roll is an index over them.

### THE SINGLE BIGGEST PERFORMANCE FACT — model eviction

Measured 2026-08-20. A phase-1 call costs **12.5s warm** and **183s cold**. That is a **14×
penalty**, and overnight the pipeline was paying it on nearly every call — which is why it
averaged ~4 minutes per source after starting at 13 seconds.

Cause: something on this machine polls `nomic-embed-text` on a timer. The 20GB MoE does not fit
alongside anything else, so each embed request evicted it, and the next pipeline call spent
~170s reloading 18.6GB from disk.

Fix — set at User scope, and required before any long run:

```
OLLAMA_KEEP_ALIVE       = -1     # never unload; `ollama ps` should read UNTIL "Forever"
OLLAMA_MAX_LOADED_MODELS = 2     # let the embed model coexist instead of evicting the MoE
OLLAMA_FLASH_ATTN       = 1
OLLAMA_KV_CACHE_TYPE    = q8_0
OLLAMA_NUM_PARALLEL     = 1      # single 10GB card; concurrency just splits the same VRAM
```

Verify with `ollama ps`: **both** models must show `Forever`. If the MoE shows a countdown, it
will be evicted and the run reverts to 4 min/call.

**What is NOT a lever** (measured, so nobody re-tries them):
- `num_ctx` 12288 vs 8192 vs 6144 — 41s / 42s / 46s warm. No meaningful difference; the KV
  cache is small next to 18.6GB of weights.
- Smaller quant — Q3_K_M is *slower* than Q4_K_M despite better GPU residency (see the model
  section of `config.yaml`).

**Remaining floor:** phase 2 is output-bound — 52,343 entries × ~30 tokens each ≈ 1.57M output
tokens at ~25 tok/s ≈ **17 hours**. Batching more entries per call does not help, because output
scales with entry count either way. Reducing what each entry emits is the only further lever.

**Hardware notes that bite:**
- Reap orphaned `llama-server.exe` before long runs — three were found pinning ~8GB of a 10GB
  card, forcing every model onto the CPU:
  `Get-Process llama-server -ErrorAction SilentlyContinue | Stop-Process -Force`
- `nomic-embed-text` loads itself periodically; something on the machine polls Ollama for
  embeddings. Small, but it competes.

---

## 5. Custodian duties (the hourly check-in)

Fires at :23 past each hour. Session-only, expires after 7 days.

1. `--status`; tail `state/pipeline.log` for crashes or repeated Ollama failures.
2. Relaunch the runner if the process died.
3. If the current phase is unimplemented **and** the previous is complete: build exactly one
   phase from this spec, test on 1–2 units, relaunch.
4. Update this plan if it changed.
5. Report in ≤5 lines. If nothing needed doing, say so in one line.

**One phase per check-in, never more.** Six untested scripts written blind is how an overnight
run dies at 2am with nothing to show.

---

## 6b. Owner decisions — 2026-08-20 (all settled)

1. **Attestation in the Entry Template** — *yes.* Applied. `prompts/system_style.txt` now prints
   the record's real grade and defaults to `Transcribed`, never `Witnessed`. Every entry has been
   stamped with its record's attestation; `prompt_version` → v4 so anything written under the old
   template regenerates.
2. **The 4 unresolved sources** — *leave them out.* HAWX, Heaven's Lost Property, major
   live-action Disney films and Twilight Imperium are marked `status: out-of-scope` on the roll
   with the reason recorded. In-scope corpus is **211/211 catalogued**.
3. **`major fantasy pantheons` as a 13-wiki composite of the invented pantheons** — *confirmed.*
4. **Weave bottom-up from evidence, not top-down from vision** — *confirmed*, and it is the
   reason the retired codex is not being replaced with another authored cosmology. Phase 4 derives
   the rungs from what the sources themselves say.
5. **Volume organisation** — *corrected by the owner*; see the architecture note above §Phase 3.
   Topic-first, two collections, History before Encyclopedia.

6. **Persons of Importance shelving** — *by Magnitude band, then A–Z.* Applied to Phase 2
   (per-entry band assignment) and Phase 6 (shelving). Supersedes the proposed
   "≥2 attestations OR a band OR a scale_note" importance filter, which is no longer needed:
   the band *is* the shelf.
7. **Relics vs Weapons** — *relic weapons are still Weapons.* Encoded in Phase 2's `topic` enum.

## 6c. Still open

- **Volume page targets** in §6 are proposed, not derived from the charter. Adjust when the first
  History volume exists and its real length is known.
8. **Unassayed overflow** — *subdivide by home verse* when a band exceeds 60% of its topic.
   Rule and its Phase 4 dependency written into Phase 6 above.


- **Check the band histogram when Phase 2 is ~10% done**, not at the end. A cheap scan of
  `data/records/*.json` counting `magnitude` values gives it. Two things to look for: the
  unassayed share (does the overflow rule trigger?) and any sign of band inflation — if M6+
  is more than a percent or two of all Persons, the model is ranking reputation rather than
  feats and Phase 2's prompt needs tightening before it processes the remaining 90%.

---

## 7. Built 2026-08-20/21 — what exists now that the plan did not describe

The plan above covers the pipeline. A large amount of supporting machinery was built alongside it
and runs standalone. Everything here is verified by `src/verify_math.py` (237 checks, 17 sections,
0 failing) and registered in `src/derivation.py` (111 quantities, 59.5% derived, graph closes).

### The measurement layer

- **`assay.py`** — the Custodial Assay. Band edges corrected against X.2 §4 (they sat two bands
  low). **Faculty parity erratum:** Int/Wis/Cha were weighted zero and `FACULTY_WEIGHTS` was never
  read by anything, so the Assay was a Str/Dex/Con scale wearing a general name. Each faculty now
  takes 1/11; the eight physical Measures keep their charter proportions and hold 8/11 together.
  Every existing physical-only decimal is unchanged, because the composite renormalises over
  scored axes.
- **Four axis statuses.** A number, `NONE` (nil, a finding), `UNESTIMABLE` (applies but never
  exercised), `INAPPLICABLE` (category error). `axis_score` clamps at zero, so a plain 0.0 is a
  BOUND; `NONE` is the point value the clamp destroys.
- **`rigor.py`** — commensuration. Ruin and Acumen share a unit via bits (X.6 §3 + X.10 §6); the
  1:1 rate is the unique zero-parameter choice. Perron/AHP, Bradley-Terry (MM, Hunter 2004) with
  **Ford's condition enforced** — it refuses on a disconnected graph rather than reporting a
  cross-component ranking that is a solver artifact. Log-normal census propagation, and P(N≥1)
  integrated rather than evaluated at the mean.
- **`custodes.py`** — one Custos per independent degree of freedom in the Assay. Ten of them; the
  charter's Quill/Moth/Avar map onto three. The ± is the measured dispersion of their readings and
  splits into prior divergence (irreducible) and attestation floor (fieldwork fixes it). Their
  tilts are the largest free-parameter block in the library and are filed as OWNER, not derived.
- **`anchors.py`** — validation at floor, standard and ceiling (the Skate Guy, Goku, the Seat of
  the Creator, a sword, Yggdrasil). Found five defects that 154 per-formula tests had not.

### Cosmology and addressing

- **`weave.py`** — identity by **name surprisal**, not source-idf. Source-idf welded Cowboy Bebop
  to Thomas the Tank Engine through "Gordon". Complete linkage, not connected components, which
  chained 95 sources into one continuity. A shared name is not an identity: Earth resolves to 30
  distinct worlds.
- **`onomast.py`** — the Doctrine of Carried Names, and **two naming layers**: the Library's
  catalogue designation, and the world's own endonym. Azgaar will not take a culture set from a
  query string, so the map's internal toponymy is the world's own and the record carries both.
- **`tiers.py`** — multiverse (168, shared origin), metaverse (8, resonance), xenoverse (6,
  deliberate joins standing an order of magnitude above the 99.5th percentile). Hyperverse is
  grounding type, per `grounding.py`, assigned per xenoverse so containment holds.
- **`sevenfold.py`** — the owner's declared order. Seven hyperverses, **1–7 children at every tier
  below**. Seven is a bound, not a quota. Shape declared, placement measured from resonance.
- **`address_space.py`** — the charter's Shelfmark with the question marks filled:
  `Ω › H0 › X3 › Mt.2 › Mv.6 › U-6 › G.x › P.n`. The seed derives from the citation card's
  IDENTITY half only, so re-assaying a world does not move its mountains.

### Generation surfaces

- **`worldseed.py`** — map parameters. **Only `seed`, `template`, `width` and `height` reach
  Azgaar**; the other six were tested and silently discarded, so they are no longer emitted.
- **`burgs.py`** — settlements by the rank-size rule (Auerbach 1913, Zipf 1949). Burg COUNT is
  derived from the law (n = P₁/P_min), not chosen alongside it.
- **`profile.py`** — a whole world in ~30 characters, round-tripping exactly.
- **`navtree.py`** — the navigation data. Every addressed thing gets a node, and every node gets
  a NAME: 734 of them, all distinct. The seven hyperverses take their names from their grounding
  type, and where two share a type they take different words for the same ground (a second
  emanation hyperverse is The Effusion, not "The Outflow the Second") — an ordinal says nothing
  about the place and doubles the length of a label that has to fit inside a circle. Writes
  `data/NAVTREE.json`, and only with `--write` after a clean audit.
- **`build_terminal.py`** — the Registry Terminal, published as an artifact. The omniverse as an
  atom: nucleus to valence, every branch reachable, handing off to Azgaar and Watabou.

  Four things about the drawing that were arrived at by measuring rather than by taste:

  1. **Focus re-roots the layout.** The first version drew the whole omniverse once and "focus"
     only un-dimmed a branch, which left an opened hyperverse crammed into the same two-degree
     wedge it had as one of seven, with 146 names stacked on each other. `layout(root)` now
     recomputes with the clicked node at the nucleus and its descendants across the full circle.
     Clicking the nucleus steps back out one tier; the breadcrumb reads in names.
  2. **A ring's circles are sized by the ring, not by preference.** `discR(n, R)` gives the
     largest disc that fits the arc each of n things gets. Above 90 units the disc can hold its
     own name and does; below it the ring falls back to dots with names set outside.
  3. **Every child gets the arc its circle occupies before any weighting.** Weighting alone put
     four of the seven hyperverses on top of each other, because a quiet branch was handed less
     arc than its own disc needs. The floor is allotted first and only the slack is weighted.
  4. **Dots are sized from each ring's measured tightest gap**, not from circumference ÷ count —
     the wedges are weighted, so a ring's closest pair is far tighter than its average, and the
     average-based sizing still left 87 overlapping pairs. Measured: 0 overlaps at every tier.

  5. **Every addressed thing gets a node, sources included.** Sources shelved at an address but
     not yet through the cosmology pass had no node — the panel listed them as text and the
     branch below them was empty, so **83 metaverses were dead ends holding 95 sources between
     them**. Diving into one arrived nowhere. A source is now drawn on a dashed shelf outside the
     tier rings, open-bordered because what is under it has not been written yet. Dead ends: 0.
  6. **Rings grow to fit what they carry.** One universe holds 157 worlds and another 140; on a
     fixed ring every name lay across its neighbour's. `ringR(base, n, fs)` returns the radius at
     which n labels have the circumference to stack.
  7. **The view is a centre and a width, with the height derived from the stage's aspect.** A
     square viewBox on a landscape stage was letterboxed into the shorter side, throwing away a
     third of the width and a third of the type size on every label. A resize needs no
     bookkeeping — the height re-derives.
  8. **The fit is measured, not estimated.** Budgeting for the longest label a ring could ever
     hold zoomed the omniverse out to leave room for a source shelf that was not on screen, and
     its own names fell to 7px. `resetView()` draws first, reads `getBBox()`, then fits.

  A name draws only where its own wedge has the arc to hold a line of it, so crowded sectors go
  quiet and hand their names to the tooltip; opening one widens the wedge and the names return.
  One ring of dots is named, never two — a shell-2 name is set outward and runs through the
  radius where shell 3's names sit, which the wedge test cannot see, since it only protects a
  name from its neighbours on its own ring.

  **The check to re-run after touching any of this** drives all 735 nodes and, at each one,
  compares drawn children / worlds / sources against what the node holds, tests every pair of
  circles for overlap, and tests every pair of labels with an ORIENTED box (SAT). Axis-aligned
  boxes are useless here: the AABB of a diagonal label is far larger than its glyphs, and it
  reported 734 of 735 nodes as broken when 5 were. Current state: **0 missing, 0 circle overlaps,
  0 label collisions, median name 15px** on a 659px-wide pane.

### Quality gates — RUN THESE BEFORE PHASE 8

- **`audit.py`** — the backscan. It found that **~90% of assigned Magnitude bands rested on no
  feat**: one regex accepted any mention of `planet|world|galaxy`, so "resource-rich jungle
  planet" licensed a band. The gate now demands an act upon an object, or a measured quantity,
  with the subject as the doer and reputation excluded. 225 bands → 27.
- **`cleanup.py`** — wiki navigation, prose ceilings, markup, thin descriptions.
- **`tells.py` + `style_audit.py`** — 138 machine-writing tells. **`prompts/system_style.txt`
  Rule 7 is GENERATED from `tells.py`**, so instruction and audit cannot drift. Run
  `style_audit.py` on the pilot before scaling and every few hundred chapters after.

### Operating hazards learned the hard way

1. **One runner only.** Two concurrent instances write the same state file and records.
2. **Free RAM is the throughput variable.** Below ~3 GB the MoE thrashes at 0.9 tok/s; at 12 GB
   it runs 38× faster. `pages input/sec` distinguishes real pressure from reclaimable cache.
3. **Regex escapes get eaten in transit.** A `\b` arriving as a literal `0x08` matches nothing and
   reports clean, which looks like success. `cleanup.py` and `tells.py` now refuse to load if any
   pattern contains a control character. This happened three times.
4. **A phase-1 band needs evidence too.** 70 sources carried a synthesis band whose evidence field
   was the empty string, because only phase 2 enforced the invariant. Both enforce it now.
