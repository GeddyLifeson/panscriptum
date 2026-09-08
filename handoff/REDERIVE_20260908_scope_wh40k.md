# RE-DERIVE, 2026-09-08 — `data/SCOPE.json` and `data/WH40K_ASSAYS.json`

**Owner rulings of 2026-09-08**, question 10 ("Stored files a fixed writer would now compute
differently", option (a): *re-derive all of it, with a snapshot and a before/after table*) and
question 20 ("Which measurement passes get commissioned now", option (a): *take the cheap passes;
abstain where there is no honest input*).

Orders `481ef92af785` (SCOPE), `82fc93f056d4` (WH40K), and — recorded here as **not taken, with
its cost** — `f27c121c6cb7` (the stored-type re-catalogue).

Sibling file: `handoff/REDERIVE_20260908_genre_grounding.md`, which covers `GENRES.json` and
`GROUNDINGS.json` under the same ruling.

This file **is** the before/after table the ruling requires. These are published numbers —
`magnitude.host_ceiling` clamps every published Magnitude against `SCOPE.json` — and a re-derive
that moves them silently is indistinguishable from a corruption.

---

## The snapshots

Taken before anything ran, and kept:

| file | snapshot |
|---|---|
| `data/SCOPE.json` (61,799 B) | `state/backups/SCOPE.json.pre-rederive-20260908` |
| the 28 withdrawn rows alone, verbatim | `state/backups/SCOPE.withdrawn-ceilings-20260908.json` |
| `data/WH40K_ASSAYS.json` | `state/snapshots/b09-wh40k-provenance-1788903473935826500-72260/` (verified: *1 path(s) restored and byte-identical*) |

---

## `data/SCOPE.json` — 28 invented ceilings withdrawn, 0 re-probed

### What was wrong

`scope_for()` used to answer the sub-floor case with `max(counts, key=counts.get)` — the
**commonest** tier — which is the one method the module header exists to refuse ("never the most
frequent one"), applied at exactly the moment the evidence is too thin to support any method at
all. The code was repaired under order `09d47bc950d9`: below `MIN_MENTIONS = 10` it now returns
`None`. The rows written before that repair were never reachable by it.

### What was re-derived, and how, without a single request

The repaired writer's rule is `best is None` when **no tier's count reaches MIN_MENTIONS**. Those
counts are already stored in each row. So for every row whose stored counts do not clear the
floor, the value the fixed writer would compute is knowable offline, exactly: `None`. That is
what was written.

The rows are **left unstamped** (`probe_version` absent, reading as 0 < `PROBE_VERSION` 2), so
`build()` still lists every one of them in its `todo`. Nothing here retires a host.

| measure | before | after |
|---|---|---|
| rows | 155 | 155 |
| rows carrying a ceiling | 146 | 118 |
| rows carrying no ceiling (`None`) | 9 | **37** |
| ceilings resting on fewer than 10 mentions | **28** | **0** |
| M1 | 8 | 3 |
| M2 | 1 | 1 |
| M3 | 65 | 46 |
| M6 | 4 | 4 |
| M7 | 47 | 43 |
| M8 | 21 | 21 |
| rows stamped at `PROBE_VERSION` 2 | 0 | 0 |

### The 28, named in full — no cut (Hard Rule 0)

Ordered by how thin the evidence was. Every one of these was clamping published Magnitudes.

| host | scope claimed | ceiling claimed | mentions behind it |
|---|---|---|---|
| tales.fandom.com | universe | M7 | 1 |
| cosmoteer.fandom.com | planet | M3 | 2 |
| ghosts.fandom.com | planet | M3 | 2 |
| katanazero.fandom.com | planet | M3 | 2 |
| outofabyss.fandom.com | planet | M3 | 2 |
| root.fandom.com | universe | M7 | 2 |
| rosariovampire.fandom.com | universe | M7 | 2 |
| unearthed.fandom.com | planet | M3 | 2 |
| wizardwithagun.fandom.com | nation | M1 | 2 |
| left4dead.fandom.com | nation | M1 | 3 |
| rise.fandom.com | planet | M3 | 3 |
| skate.fandom.com | nation | M1 | 3 |
| baki.fandom.com | nation | M1 | 4 |
| elements.fandom.com | universe | M7 | 4 |
| rime.fandom.com | planet | M3 | 4 |
| vampyr.fandom.com | planet | M3 | 4 |
| waterdeep.fandom.com | nation | M1 | 4 |
| bindingofisaac.fandom.com | planet | M3 | 5 |
| palworld.fandom.com | planet | M3 | 5 |
| yakuza.fandom.com | planet | M3 | 5 |
| chowder.fandom.com | planet | M3 | 6 |
| kenichi.fandom.com | planet | M3 | 8 |
| problemsolverz.fandom.com | planet | M3 | 8 |
| riskofrain.fandom.com | planet | M3 | 8 |
| terminator.fandom.com | planet | M3 | 8 |
| acquisitionsincorporated.fandom.com | planet | M3 | 9 |
| rockofages.fandom.com | planet | M3 | 9 |
| sakamoto-days.fandom.com | planet | M3 | 9 |

The "mentions" column is the highest count any tier reached in the row's own stored `counts`
map — the number the repaired `scope_for()` compares against `MIN_MENTIONS = 10`. The
authoritative verbatim copy of all 28 rows is the JSON snapshot named above.

### Which direction the published numbers moved

**Loosened, not tightened.** A withdrawn ceiling removes a clamp, so entities on these 28 hosts
are no longer bounded by a band nobody measured. That is the ruled direction: an unearned ceiling
is not the conservative choice, it is a number describing a fiction no source ever recorded.

### What is NOT done here, and what it would cost

**No host was re-probed.** All 155 rows remain at `probe_version` 0, so the counts every row
holds — including the 118 that still carry a ceiling — were taken under the *pre-repair* contract
(`srlimit=3`, `titles[:8]`). 80 of the 146 originally-scored hosts sat exactly on that removed
eight-page cap, which is the cap's fingerprint. Those counts are a **floor**, and a real re-probe
could well restore a legitimate ceiling to some of the 28.

The re-probe is a **live crawl on the Fandom edge**, which this maintenance run is not permitted
to start, and it is not a small one:

* 155 hosts × 4 `list=search` calls at `srlimit=500`, then `F.fetch` over every returned title
  over 1,200 bytes — hundreds of titles per host on the large wikis.
* Paced by `feats._throttle` at `PAUSE = 0.34 s` per host, and under owner ruling 6 of the same
  session that pacer now locks on the **registrable domain**, so every `*.fandom.com` host shares
  one lane rather than twelve.
* This is the domain that has IP-banned this machine once.

**To finish this re-derivation:** `python src/scope.py --build` (every unstamped row is already
in its `todo`; no `--rebuild` needed), then append the second before/after table to this file.

---

## `data/WH40K_ASSAYS.json` — provenance re-derived, no Magnitude moved

### What was wrong

`compute()` stamped `[wiki]` onto all 55 axis worksheet lines unconditionally. The ROSTER is a
mixture of verbatim quotation and the assayer's own reading, so a mark applied to everything
distinguished nothing — the exact defect `halo.py` was repaired for on 2026-08-27, where 24 of 33
tags turned out to be false. The interim repair replaced the false claim with `unattributed`,
which was honest and unfinished.

### How the reading was done — mechanically, against evidence

Not by re-reading and forming an impression. The criterion is `zfighters.py`'s own: **[wiki]**
where the sentence is in the mined cache verbatim, **[canon]** where the reading is the assayer's
and the miner did not surface the line.

Every single-quoted fragment in each axis's evidence string was case- and punctuation-folded and
looked up in the folded text of all **3,917** mined pages under
`data/feats/warhammer40k_fandom_com` — **47,457,024 characters**. An axis with a fragment of 25
folded characters or more found verbatim is `wiki`; one whose quotes are absent, or which quotes
nothing, is `canon`. The 25-character floor is there because a verbatim match on a short common
phrase is not evidence of quotation.

| measure | before | after |
|---|---|---|
| axes | 55 | 55 |
| tagged `wiki` | 0 (55 blanket `[wiki]`, then 55 `unattributed`) | **13** |
| tagged `canon` | 0 | **42** |
| tagged `unattributed` | 55 | **0** |
| ROSTER tuple shape | 2-tuple (all) | 3-tuple (all) |

**The blanket `[wiki]` was therefore false for 42 of 55 axes — 76%**, the same order of magnitude
the `halo.py` precedent found.

### No Magnitude moved, which is the check

| entity | before | after |
|---|---|---|
| Tzeentch | 𝔄 M7.86 ± 0.15 | 𝔄 M7.86 ± 0.15 |
| Slaanesh | 𝔄 M7.85 ± 0.15 | 𝔄 M7.85 ± 0.15 |
| Nurgle | 𝔄 M7.80 ± 0.15 | 𝔄 M7.80 ± 0.15 |
| Khorne | 𝔄 M7.76 ± 0.15 | 𝔄 M7.76 ± 0.15 |
| The Emperor of Mankind | 𝔄 M6.76 ± 0.15 | 𝔄 M6.76 ± 0.15 |

Provenance changed; nothing else did.

### Two results worth naming

* **Slaanesh / reach** quotes a sentence that is **not in the mined cache at all**. Tagged
  `canon`.
* **The Emperor / acumen** cites *"the Primordial Truth"* — a real term on that wiki, but too
  short to establish that this line was transcribed rather than recalled. Its sibling quote on
  the same axis IS verbatim, so the axis is `wiki`; the short fragment alone would not have
  earned it.

The 2-tuple shape is still accepted and `_provenance()` still answers `unattributed` for one.
Nothing uses it today; it is kept so a new axis added without a reading says so out loud instead
of inheriting a neighbour's tag.

---

## `data/records/*.json` stored types — NOT re-catalogued, and what it would cost

Order `f27c121c6cb7`. The ruling asks for "the targeted re-catalogue of the roughly 25,000 entries
whose stored type is not an entity kind". **It was not started**, for the same reason the SCOPE
re-probe was not: `--recatalogue` is a live crawl, and this is the largest one in the project.

### The before-state, measured on disk 2026-09-08

| measure | value |
|---|---|
| records with `mode='web'` | 156 |
| entries in them | 272,004 |
| distinct stored `type` values | 12,759 |
| (record, class, type) groups | 14,177 |
| worst single group | Warhammer Fantasy / Events → `'Total War: Warhammer'`, **690 entries** |

The ten largest records, which are where the cost lives: Marvel (59,170 entries), DC (55,560),
all Final Fantasy (26,679), Legend of Zelda (8,874), Mario and his expanded universe (7,191),
Warhammer Fantasy (7,012), Dragon Ball Z (6,923), Gundam (6,182), SpongeBob SquarePants (6,145),
Transformers (6,019).

### What it would cost

* `--recatalogue` re-walks every category and re-fetches page text per source. The DC Persons
  class alone resolves to 360 categories, the first of which lists 33,614 titles and takes about
  3.8 minutes just to rank.
* Two records account for 42% of all entries (Marvel and DC, 114,730 of 272,004) and are hours
  each on their own.
* All of it against `*.fandom.com`, now sharing **one** pacer lane at `PAUSE = 0.34 s` under the
  same session's ruling 6 — so the aggregate is a multi-day pass, not a multi-hour one.
* The count of entries that are actually WRONG **is not computable offline**: the right answer is
  "which Fandom category is this title in", which needs the live calls. Only the unmistakable
  half — types that are proper nouns rather than entity kinds — can be counted from disk.

### Why it is still worth doing, and why now is still the cheap moment

`corpus_db` indexes `type`; `manifest_builder` puts the entry dict into the model prompt; and
`prompts/system_style.txt` tells the model to pick the closest fit to the entry's type — so a
wrong type is carried into finished prose. **The prose gate is shut**, which is what makes this
cheap to fix now and expensive later. The writer is already fixed (order `6eb20e8d3565`); only
the stored side is stale.

---

*Recorded by the maintenance run of 2026-09-08, brief 09.*
