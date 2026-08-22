# Owner Design Decisions — Pending the Step 4 / Xenoverse-Hyperverse Pass

This file exists because the owner has, from time to time, handed down a specific worldbuilding
rule for the omniverse's higher-rung structure (Xenoverse, Hyperverse, the Custodes' own
governance) *before* the actual Step 4 entanglement/design pass has started — which the owner
explicitly asked to hold until cataloguing is done (see
`../VERBATIM_SESSION_TRANSCRIPT.md`, 2026-08-19T17:40:41Z: *"don't worry about it yet then it
can wait for everything else to get catalogued"*).

**Purpose:** capture these rules durably and in order, so they don't get lost between sessions,
without prematurely expanding the charter or starting the design pass itself ahead of schedule.
When Step 4 actually starts, read this file first — every entry here is a locked-in constraint
on that design, not a suggestion.

---

### 2026-08-19 — Each Hyperverse has a Custos

**Owner's words:** "each hyperverse has a Custos, this is for the sake of efficiency in
information processing and also to better help refine and resolve disputes within the system"

**What this means for the eventual design pass:** the charter already establishes a Custodial
governance hierarchy — Custos-Prime Avar (current officeholder, Part Five), the Grand Custodes,
and the Custos Absolute (the singular office that owns the Custodial Paradox, Part One) — plus
an **accession chain** that ratifies events rung-by-rung up the Ladder of Being (town → world →
system → ... per Part Four, "gathering a countersign pedigree at each level"). This new rule
slots a **dedicated Custos office per Hyperverse** into that chain: every charted Hyperverse
(the `H` rung, 16th of 17 on the Ladder) gets its own Custos, functioning as the accession
checkpoint and dispute-resolution authority for everything under it (its Xenoverses,
Metaverses, Multiverses, Universes, and so on down).

**Open questions for when Step 4 actually starts:**
- Does every Hyperverse's Custos report to the Custos Absolute directly, or is there an
  intermediate tier (a "Grand Custos" per some grouping of Hyperverses)?
- Is the office singular-and-eternal like the Custos Absolute, or does it rotate/succeed like
  Custos-Prime Avar's own office implies elsewhere in the charter?
- How does this interact with entries whose Hyperverse position is still `H?` (uncharted) —
  presumably they have no assigned Custos yet either, which is consistent with "uncharted" but
  worth stating explicitly once the design pass writes this up formally.

**Status:** recorded, not yet built into the charter. Don't retroactively add "Custos: [name]"
fields to any generated entry's Shelfmark or Attestation until the design pass resolves the
open questions above and the charter itself is amended — per the same honesty discipline the
charter applies to `?` on unresearched rungs (Working Rule 2), a guessed Custos name is worse
than an honestly blank one.

---

### 2026-08-19 — Ability scores are the Custodes' own in-universe instrument, not a real-world
### game reference; and the Entry Template's "For the Table"/"Three Doors" sections are cut

**Context:** the first local pilot generation came back reading like padded plot synopses
rather than encyclopedia prose, and its "▣ For the Table" sections broke the fourth wall
outright — addressing a real-world DM directly ("tier of play: Epic... use as an NPC at your
table"). The owner's correction, verbatim: *"I don't want for the table shit, these books
should read like in-universe books only, nothing meta about the game they are designed for or
for the campaign or anything"* — and, on being asked to confirm scope, *"also yes cut the dm
hooks too"* (covering `✦ Three Doors` as well, same category of real-world-DM-facing content).

**The reframe, also verbatim from the owner:** *"The only reason D&D stats are used is that's
the in-universe system the Custos use to evaluate abilities, proficiencies, and the ability
scores are just their metric (and the ability score limit is technically 30 for the record)
for defining strength, dexterity, intelligence, constitution, wisdom, and charisma."* So the
six ability scores (STR/DEX/CON/INT/WIS/CHA, 1–30) are NOT a "for the table" DM convenience —
they are the Custodes' actual in-universe measurement instrument for a being's faculties, the
same epistemic category as the Magnitude/Assay system (Part Three) and every bit as canonical.

**What changed (`prompts/system_style.txt`, already applied):**
- `▣ For the Table` (5e DM sidebar, tier-of-play/NPC-usage language) — **removed entirely.**
- `✦ Three Doors` (three adventure hooks) — **removed entirely.**
- `▣ The Instrument` — **new section**, replacing "For the Table" in the same template slot:
  reports the six ability scores (1–30 cap) only where the supplied entry data honestly
  grounds them (a described feat of strength implies a Strength range, etc.), otherwise prints
  "uninstrumented — no faculties on file." Never mentions tiers of play, DCs, stat blocks, or
  any other real-world game term. Applies to Persons/Gods/Beasts; Places/Vessels/Factions/
  Events get "Not applicable — the Instrument measures beings, not [class]."
- Also fixed in the same pass: entries were padding thin source data with generic atmosphere
  instead of honestly staying short (system prompt's own Ground Rule 2 wasn't being followed),
  and one source's ceiling-entity Magnitude rationale was getting copy-pasted verbatim onto
  unrelated Place entries in the same file — both now explicitly forbidden in the prompt.

**Open question for the eventual charter amendment:** Part Seven of `00_MASTER_CHARTER.md`
still documents the old "▣ For the Table" / "✦ Three Doors" shape as canonical. The generation
prompts have moved off it; the charter document itself has not yet been formally amended to
match. Someone should reconcile this — either amend Part Seven to describe "The Instrument" as
canonical, or explicitly note this as a Custodes-vs-real-world-kit divergence if the owner
wants the charter's own text to stay as historical record of an earlier design.

**Status:** live in `prompts/system_style.txt` as of this entry. NOT yet reflected in
`00_MASTER_CHARTER.md` Part Seven — flagged above, not done in this pass.

**Follow-up same day:** owner noted the Instrument needed to stay consistent with the charter's
actual math, not float free of it. Tied it to Part Three's existing Magnitude table (which
already has a Levels/CR column per M-band) rather than inventing a second, disconnected
numeric system: each Magnitude band now bounds a plausible ability-score range (M0: 1-18 up
through M4-M5 approaching the 30 ceiling), and per Working Rule 2 ("Statting stops at M5"),
M6+ entries get "Beyond the Instrument's range" instead of scores — consistent with the
charter's own rule that M6+ beings aren't statted, only fought via avatars/aspects/narrative
mechanics (Vol. IX.2). Explicitly NOT deriving scores from the real Nine Measures Assay formula
(Collection X) — that would be fabricating worksheet-grade precision from data that doesn't
support it, the same violation Hard Rule 3 in `CLAUDE.md` already forbids for Magnitude
decimals. The Instrument is a bounded-plausibility check against existing charter math, not a
new formula.

**Second follow-up, same day — the real point, stated directly by the owner:** *"all math
shouldn't be made up but rigorously defined, scrutinized, and integrated so that everything is
uniform across the entire universe so that something like a sphere of annihilation and Mihai
can be talked about in the same way that the force of a punch and the force of a bullet use the
same terms."* This is the actual design bar for the whole Instrument, not just a one-off note —
worth re-reading if anyone touches this system again. Also, same session: *"change it so that
statting never stops until M[omega]"* — directly overriding Working Rule 2's "Statting stops at
M5" for the purposes of the Instrument specifically.

**Resolution (owner picked from 3 options via AskUserQuestion):** base ability scores stay
capped at 30 at every Magnitude band (matches the owner's earlier "cap is 30" rule and real 5e
math) — nothing above M5 gets a bigger raw number. Instead, M6+ entries carry an additional
**Transcendence Grade**, computed mechanically as `(integer Magnitude - 5)`: Grade I at M6
through Grade V ("Absolute") at M10/Ω. This grade is DERIVED from the entry's own
already-established Magnitude integer via a fixed formula — never a second, independently
invented number — so a Sphere of Annihilation and Mihai are read on the literal same six axes
and the same grade formula, differing only by where their own already-attested Magnitude places
them. Implemented in `prompts/system_style.txt`.

**Known open gap, flagged but not yet resolved — worth surfacing before this goes much further:**
the charter's existing Nine Measures (Collection X: Ruin, Continuity, Celerity, Reach,
Transgression, Sustain, Vector, Volition) are a *combat-capability* system. Strength, Dexterity,
and Constitution map onto it reasonably naturally (Ruin/Transgression ~ physical force,
Celerity ~ Dexterity, Continuity/Sustain ~ Constitution). Intelligence, Wisdom, and Charisma do
NOT have an obvious existing charter axis to derive from — the Nine Measures don't cover
cognition or social presence at all. Right now the prompt just asks the model to ground each
axis honestly in whatever the entry data says, without claiming a formal Nine-Measures mapping
for INT/WIS/CHA specifically. If the owner wants full rigor here too (a real, uniform
derivation for all six axes, not just three), that's its own extension to Collection X's method
— genuinely new charter math, not something to improvise inside a bulk-generation prompt. Not
blocking current work, but don't let this gap get forgotten.

**Third follow-up, same day — reading level as in-fiction characterization.** Owner's words:
"amend that when one is looking just for the d&d ability scores that's automatically somebody
that's at the most basic level of the 4 levels of literacy because they don't understand any
nuance above 'big or small number'." This ties the Instrument directly into the charter's own
**Four Literacies** doctrine (Vol. 0.1, `0-1_CUSTODIANS_VADE_MECUM.md`: Guest, Reader, Hand,
Custos — layperson finds, student reads, scholar writes, sage amends). A reader who only wants
the flat 1-30 Instrument numbers, without engaging the Magnitude band, the Nine/Eleven Measures,
or the Assay's error-honest worksheet reasoning behind them, is — in-universe — a **Guest**: the
lowest of the four literacies, capable of finding a number but not reading what produced it.
This should land as an explicit doctrinal note in whichever document formally establishes the
Instrument (the fascicle authored in the entry above), not just as a throwaway line — it's the
same "the number is not the point, the discipline for arguing about numbers is the point" ethos
Lector Moth states outright in X.2's colophon.

**Status:** handed to the in-progress fascicle-authoring pass (see the entry above) rather than
edited in directly here, to avoid a second writer colliding with that work mid-edit.

---

### 2026-08-19 — The faculty extension is written: Vol. X.6 (*Instrumenta Facultatum*), the
### INT/WIS/CHA axes, the Instrument conversion, and the Lay Reading clause

**What this resolves:** the "Known open gap" flagged in the entry above (INT/WIS/CHA had no
charter axis to derive from), under the owner's explicit design bar, verbatim: *"all math
shouldn't be made up but rigorously defined, scrutinized, and integrated so that everything is
uniform across the entire universe so that something like a sphere of annihilation and Mihai
can be talked about in the same way that the force of a punch and the force of a bullet use the
same terms"* — and, on whether published canon could be restructured to do it honestly rather
than force-fitting: *"if you need to restructure the published canon for this that's fine and
makes sense."*

**The analysis, in brief (full version is the fascicle itself,
`X6_INSTRUMENTA_FACULTATUM.md`):**
- **INT is NOT honestly derivable from the existing eight axes.** The closest candidate,
  Volition (θ), fails on three real grounds: it exists only relative to a connected contest
  graph, it's a quantile (an ordinal summary that can't support the ratio-scale log scoring
  rule every axis uses), and it confounds cognition with all eight material quantities.
  X.6 Proposition 1 demotes Volition to "the shadow Acumen casts on the defeat graph" —
  supporting evidence, never the quantity.
- **WIS and CHA are not derivable even in principle from the eight** — X.6 §1 proves it
  (faculty-underdetermination theorem): the eight axes are all output-side (agent → matter)
  quantities, and no function of them determines input-side perceptual fidelity or influence
  routed through other minds. Worse, X.2 had an internal *coverage* inconsistency the extension
  repairs: the Anchor explicitly honors hegemonic (social) decisiveness while no axis could
  score it — a purely charismatic M3 warlord anchored correctly and then scored near-zero on
  everything. Filed as Erratum 2 against X.2 ("the Suasion gap").
- **Crucially, no axiom changes.** Axiom M2 (power is what power does to macrostates) already
  admits all three faculties — beliefs and other agents' strategy choices ARE macrostates —
  so this is an extension of coordinates, not a revolution in axioms (X.6 Theorem 2). The
  restructuring the owner authorized turned out to be additive: three new axes, zero rewrites
  of existing math.

**The three new axes** (each with an operational quantity, a unit, and the same log-scale
band-relative scoring rule as the original eight; weights fitted from contest data, not
decreed): **Acumen** (INT — prediction/planning advantage over a declared reference predictor,
bits per epoch), **Discernment** (WIS — veridicality bits: mutual information between concealed
state and the agent's estimate under adversarial concealment; includes resisting compulsion),
**Suasion** (CHA — bits of other agents' choices set by message-scale, zero-exception-cost
influence; force-backed compliance is excluded as Ruin's shadow and mind-control is excluded as
Transgression, which is why a dominator can honestly print low CHA and high Transgression).
Combat battery keeps the name "Nine Measures"; the full instrument is "the Twelve Measures."

**The Instrument conversion is now deterministic** (X.6 §6): STR←Ruin (somatic), DEX←Celerity,
CON←mean(Continuity, Sustain), INT←Acumen, WIS←Discernment, CHA←Suasion; per-band windows
locked to the already-established table (M0: 1–18 ... M5: 30 flat); value =
round(floor + (s/10)·span), 30-cap absolute; Transcendence Grade unchanged and untouched:
Grade = (integer Magnitude − 5), Grade I at M6 through Grade V "Absolute" at M10/Ω, derived
only, never assigned. The worked example is the owner's own pairing: a Sphere of Annihilation
(whose faculty axes return *provable* nulls — a singleton strategy set makes every
choice-based supremum empty, so "Not applicable" is now a computed result, not a convention)
and Mihai Niculescu (real Reconstructed scores with honest intervals, widest on CHA exactly
where the force-confound theorem says identification is hardest).

**The Lay Reading clause** (implements the "Third follow-up" entry above, owner verbatim:
*"when one is looking just for the d&d ability scores that's automatically somebody that's at
the most basic level of the 4 levels of literacy"*): X.6 §6 now carries formal doctrine tying
the flat 1–30 numbers to the Four Literacies of Vol. 0.1 — consulting the Instrument values
without the band, the Measures, or the worksheet is a Guest-level Lay Reading, "fully
successful and entirely shallow," with in-voice statements from Avar and Moth.

**Honesty discipline, restated where it matters most (X.6 H5, "no worksheet, no number"):**
none of this licenses computing per-axis scores for the ~200k-entry bulk catalogue from
one-sentence blurbs. Thin attestation yields only the band-population prior, and printing a
point value from a band prior is fabrication — the formula's existence is not evidence. Bulk
generation continues to print "--"/"uninstrumented" per the existing prompt rules; real scores
await the same deliberate worksheet-grade research pass that Magnitude decimals already
require (CLAUDE.md Hard Rule 3).

**Files touched in this pass:** `X6_INSTRUMENTA_FACULTATUM.md` (new — the authoritative math);
`X2_MENSURA_FUNDAMENTA.md` (Erratum 2 appended to §10 plus a marked marginal notice at the §4
axis table — additive, clearly flagged, nothing rewritten); `00_MASTER_CHARTER.md` (Collection
X listing extended to 6 volumes with the X.6 entry; a marked Addendum under Part Three's Nine
Measures table); `prompts/system_style.txt` (▣ The Instrument section: plain-language
INT/WIS/CHA mapping added for the bulk-generation model, honesty constraints repeated,
banding/Grade table untouched).

**Status:** X.6 founded and filed; X.2 Erratum 2 pending in-fiction re-ratification up the
Chain of Record (same status convention as Erratum 1/Kenshiro). The bulk-generation prompt
remains band-bounded by design — no change to what the local model is allowed to fabricate,
which is nothing.

**Fourth follow-up, same day — the research standard, stated as policy.** Owner's words,
verbatim: "EVERYTHING IS FULL DEPTH FULL BREDTH [breadth] AND IS INCONCLUSIVE THEN STATED AS
SUCH BUT GENUINE ATTEMPTS MUST BE MADE." This is a standing research-depth policy, not scoped to
the Instrument alone — read broadly, it governs every catalogued fact in the project: a genuine
attempt at full depth and breadth must be made before anything is marked "uninstrumented,"
"unassayed," "pending," or otherwise left blank. Coming up empty AFTER a real attempt is honest
and correct (matches every existing honesty convention in this project — H5, Working Rule 2's
`?`, "None currently on file"); coming up empty because no attempt was made is not, and is now
explicitly disallowed by this policy.

**The practical consequence, why this isn't a small ask:** the current bulk-generation pipeline
(`src/generate.py`, the local Ollama pass) has NO research capability — it only ever reformats
whatever is already sitting in `data/records/*.json`. It cannot "make a genuine attempt" at
anything; it can only honestly report what's already there or honestly say nothing's there.
Satisfying this policy for the Twelve Measures (or for any fact) requires an actual per-entry
RESEARCH pass — real web search, checking wikis/vs-pages/official material as the owner
described the original methodology — layered BEFORE prose generation, not folded into it. That
research pass does not exist yet for the Twelve Measures' three new axes (Acumen/Discernment/
Suasion feats weren't what the original Step 1 sweep was looking for — see the scale_note
audit: real feat data exists for roughly 10-15% of even a well-covered source like Marvel, and
that's for the ORIGINAL Ruin/Transgression-style power feats, not the new faculty axes
specifically). Scoping and running that pass — across how many of the 215 sources, at what
depth per entry, via how many parallel research agents — is a decision with real time/resource
cost that the owner should make explicitly, not something to launch silently at full scale.
