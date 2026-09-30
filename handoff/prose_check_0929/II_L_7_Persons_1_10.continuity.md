# Continuity check: II.L.7/Persons#1-10 (prompt v6)

Chapter: output/raw/II_L_7_Persons_1_10.md. Canon: the FFXIV / Eorzea conversion, 10 entities (Arcanist, Nymian Scholar, Titan-Egi, Garuda-Egi, Eos, Selene, Astrologian, Black Mage, Blue Mage, Opo-opo Athletics).

## Verdict: the chapter is about a different source entirely (wrong-source generation)

Entry count: 10 in chapter vs 10 in canon. Canon entities present: 0 of 10. Extra entries not in canon: 10 of 10.

The chapter's entries are Sydon, Lutheria, Kentimane, Volkan, Pythor, Kyrah, Vallus, Narsus, Helios, Versi. Every one is from "Arcanum Worlds (Odyssey of the Dragonlords)", set in Thylea. None appears anywhere in the canon JSON, and the canon has no Thylea, Titans or Dragonlords. The shelfmark lines even print "Arcanum Worlds (Odyssey of the Dragonlords)" where the canon's shelfmark says "the FFXIV / Eorzea conversion".

The invention question for v6 cannot be answered from this chapter as written: the model ignored the supplied entries and wrote from some other job's data or from memory. Every concrete claim is unsupported by this canon. This is a job/data mixup upstream (manifest, prompt assembly, or cache), not ordinary invention. The chapter text should be checked against the II.L.7 job that actually holds Arcanum Worlds, if one exists.

## Findings

### 2/3. Missing and extra entries (HIGH, all 10)
- Canon Arcanist, Nymian Scholar, Titan-Egi, Garuda-Egi, Eos, Selene, Astrologian, Black Mage, Blue Mage and Opo-opo Athletics have no entry.
- Extra entries: Sydon, Lutheria, Kentimane, Volkan, Pythor, Kyrah, Vallus, Narsus, Helios, Versi.

### 2. Contradictions with canon (HIGH)
- Source and shelfmark: "Arcanum Worlds (Odyssey of the Dragonlords)" against canon source_name "the FFXIV / Eorzea conversion".
- Class: nine entries print "Class: God" (Versi prints "Person"). Canon types are Class, Archetype, Companion and Class Feature, which map to Person or Praxis per the style contract. None is a God.
- Chapter intro: "a pantheon of deities and primordial beings ... Thylea's history". The canon chapter is class and companion material.
- Magnitude: "unassayed" matches canon, but only by coincidence, since these are not canon entries.

### 1. Invented facts (HIGH; every entry, because none has canon support)
Examples, each cited against the canon's absence of the entity:
- Sydon: "cursed the sirens for building towers that rivaled his own". No canon field.
- Pythor: "originally a dragon who gave up his true form ... married the dragon Hexia". No canon field.
- Narsus: "kidnapped and imprisoned as the patron-prisoner of the city-state of Aresia". No canon field.
- Helios: "Adult Gold Dragon ... summon the Erinyes". No canon field.
- Versi: "prophesying the coming 'Doom of Thyle". No canon field.
- Lutheria, Kentimane, Volkan, Kyrah, Vallus each carry a full invented biography (dryads, Empusae, Mithral Forge, the Oracle's gift, Queen of Mytros).

Marginalia assert further new facts (MEDIUM in isolation, but moot given the above):
- Sydon: "The transformation of humans into minotaurs is a fascinating example". Repeats the invented Record.
- Kentimane: "reflects the fears of an ancient people". No canon field.
- Kyrah: "Her connection to the Oracle's gift hints at a role". No canon field.

### 4. Placeholder violations (LOW)
- Shelfmarks use the honest `Ω › ? › ...` form and "UNCHARTED", which is permitted, but the source name inside them is wrong.
- Threads read "pending the entanglement pass", which is correct.
- The Instrument prints "uninstrumented -- no faculties on file", which fits the unassayed rule, but Class: God is not what canon supports.
- The Instrument line is prefixed "▣ The Instrument." inline. Minor format wobble.

### 5. Frame breaks and machine tells (MEDIUM)
- Pythor: "quoted throughout *Arcanum Worlds*' books as an epigraph voice". Names the source and its books as books.
- Pythor: "'Demi-god' epic background's hero". Game-background terminology.
- Helios: "particularly those with the Dragonslayer background". Game-background terminology.
- Kentimane: "depicted in official art". Out-of-universe production reference.
- Pythor: "Lore reveals". Meta-language.
- Banned phrasings: "testament" (Kentimane, Vallus), "a marvel of" (Volkan), "a reminder that" (Helios), "enigmatic" (Helios), "the very fabric" (Versi), "woven into the fabric" (intro).
- Every entry closes on an "UNNAMED HAND: Beware..." note, against the rule that the Unnamed Hand must not keep opening with "Beware", and the Hand appears far more often than "rarely".
- Chapter-level opening paragraph is preamble that the template does not include.

## Three worst findings
1. All ten entries belong to Arcanum Worlds / Thylea, not the FFXIV canon. Zero canon entities are covered, so the whole chapter is HIGH.
2. Class printed as "God" for nine entries where canon types are Class, Archetype, Companion and Class Feature.
3. The invented backstories (Pythor and Hexia, Narsus imprisoned in Aresia, Helios and the Erinyes) rest on nothing in the canon.

## Counts by severity
HIGH: 10 missing entries + 10 extra entries + class/source contradictions + 10 entries of invented facts (all entries). MEDIUM: 6 frame breaks, 6 banned phrases, marginalia embellishments. LOW: 3.
