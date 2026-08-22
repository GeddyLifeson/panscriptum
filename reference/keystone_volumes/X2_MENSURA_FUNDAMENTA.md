# MENSURA FUNDAMENTA
## On the Measurement of Power
### *Being the mathematical foundations of the Custodial Assay — Vol. X.2, first fascicle. The first volume of the Panscriptum to be written rather than planned.*

> *"Evidence tells you the system worked once. A system tells you when it must work, when it cannot, and by exactly how much it may be wrong. I was never interested in being right. I was interested in being wrong by a declared amount."*
> — Lector Moth, defense of the first Fundamenta

---

## §0 — PROGRAM

This treatise founds a measurement discipline for **power**: the capability of an agent to transform the state of a system, however that capability manifests and whatever the local laws of the system are. It proceeds in the only order a foundation can: primitives and axioms (§1); what power *is* as a mathematical object and the first impossibility theorem (§2); the anchor as causal decisiveness (§3); the eight axes as operational scales with units (§4); estimation from contest data (§5); aggregation with *fitted*, not decreed, weights (§6); the error doctrine (§7); commensurability across systems with different physics (§8); the honesty theorems — what this system can never do, proved rather than confessed (§9); revisions the mathematics forces on prior doctrine, including a correction to a published Assay (§10); and open problems (§11).

The stance throughout is the one demanded at the founding: **systems before evidence.** Every convention is declared before use. Every estimate carries its interval as a function of evidence. Every limit is stated as a theorem, not discovered as an embarrassment.

---

## §1 — PRIMITIVES AND AXIOMS

**Definition 1 (System).** A *system* is a triple **S = (Ω, 𝔇, {q_r})** where Ω is a state space; **𝔇** is the *law* of S — the set of admissible trajectories through Ω (the local physics, magic system, or game-rule, codified); and **{q_r}** is the *rung filtration*: a family of coarse-graining maps q_r : Ω → Ω⁽ʳ⁾ for r = 1, …, 17, sending microstates to macrostates at each rung of the Ladder (the planet-scale description, the system-scale description, and so up). Coarse-grainings are required to be consistent (q_{r+1} factors through q_r).

**Definition 2 (Agent).** An *agent* A embedded in S is a subsystem equipped with a strategy set Σ_A; each strategy σ ∈ Σ_A induces a probability measure P_σ over trajectories of S. Nothing else is assumed — not intent, not biology, not personhood. A storm front with one strategy is a degenerate agent; a Saiyan is a rich one.

**Axiom M1 (Locality of law).** Every system carries its own 𝔇. There is no privileged physics; there is only *each* physics, codified. (This axiom is what later makes Transgression well-defined and what makes cross-system measurement a real problem rather than an oversight — see §8.)

**Axiom M2 (Operationalism).** Every claim about power is reducible to a claim about induced distributions over macrostates: *power is what power does to the coarse-grained future.* Claims not so reducible (auras, titles, reputations, prophecies) are admissible as *evidence about* capability, never as capability.

**Axiom M3 (Declared conventions).** All thresholds, reference scales, and priors used below (δ, band edges, codifications of 𝔇) are conventions: chosen, published, and frozen before measurement, exactly as a confidence threshold is chosen before an experiment. A convention is not a truth; it is a promise not to move the goalposts.

---

## §2 — WHAT POWER IS, AND THE FIRST IMPOSSIBILITY

**Definition 3 (Capability set).** For agent A in S, the capability set is
**C_A = { (s, T, t, p) : from state s, A has a strategy driving the system into target set T ⊆ Ω within time t with probability ≥ p }.**

**Definition 4 (The capability preorder).** A ⪰ B iff C_B ⊆ C_A — *A can do everything B can do, at least as fast, at least as reliably.*

**Proposition 1 (Partiality).** ⪰ is reflexive and transitive but not total: there exist agents A, B with A ⋡ B and B ⋡ A.
*Proof sketch.* Exhibit two agents whose capability sets are incomparable under inclusion: one whose reachable targets concentrate in high-energy transformations of local states (Ruin-dominant), one whose reachable targets concentrate in low-energy transformations of distant or informational states (Vector/Transgression-dominant). Neither capability set contains the other. ∎
*(The canonical instance is filed in Part Four of the Charter: a duel, a chase, and a game of secrets ordering the same two beings three different ways.)*

**Theorem 1 (No lossless scalarization).** There is no map 𝔄 : Agents → ℝ such that 𝔄(A) ≥ 𝔄(B) ⇔ A ⪰ B, whenever the preorder contains an incomparable pair.
*Proof.* ℝ is totally ordered; the biconditional would force totality on ⪰, contradicting Proposition 1. ∎

**Consequence — the founding design decision.** Every scalar "power level" is a *projection* of a partially ordered object onto a line, and projection destroys information *necessarily*, not accidentally. The Custodial response, now given its true justification: publish the **vector** (the eight axes) as the primary object; publish the scalar 𝔄 as a declared, calibrated projection for the common case; and *quantify* the information the projection destroys (§5, the curl). Scouter-style single numbers are not wrong because they are crude; they are wrong because Theorem 1 says they must be.

---

## §3 — THE ANCHOR: DECISIVENESS AS CAUSAL INFLUENCE

The integer Magnitude was defined doctrinally as "the scale of conflict the agent can decide." This is now made exact using interventional causality.

**Definition 5 (Influence at rung r).** For agent A in S:
**I_r(A) = sup over σ, σ′ ∈ Σ_A of d_TV( q_r ∘ P_σ , q_r ∘ P_σ′ )**
— the total-variation distance between the distributions over *rung-r macrostates* induced by A's best pair of divergent strategies. I_r(A) = 1 means A's choice fully determines some rung-r outcome; I_r(A) = 0 means the rung-r future is invariant to everything A can choose.

**Definition 6 (Anchor).** **M_a(A) = max { r : I_r(A) ≥ δ }**, with the decisiveness threshold **δ = ½** declared per Axiom M3.

Three properties fall out correctly. *Hegemonic, not destructive:* I_r is about steering macro-outcomes, not about energy release — a warlord who decides a planet's political future without cracking its crust anchors at M3, as doctrine always insisted. *Anti-inflation:* participation in rung-r events without decisive influence contributes nothing; standing near a big battle is not power. *Threshold honesty:* δ = ½ is a convention like 5σ — a different community could pick differently, and the notation would say so.

---

## §4 — THE AXES AS OPERATIONAL SCALES

Each of the eight power axes is now an *operational quantity* with a unit, mapped to a band-relative score by a common rule. Power quantities range over many orders of magnitude, so all axes are **logarithmic** (a ratio scale in the sense of representational measurement theory).

**The scoring rule.** For axis quantity x and rung band r with declared reference edges x_r (band floor) and x_{r+1} (band ceiling):
**s(x) = 10 · clamp₍₀,₁₎ ( (ln x − ln x_r) / (ln x_{r+1} − ln x_r) ).**
Scores saturate at the band edges; an axis value below the floor scores near 0 *even for a legitimately anchored agent* (see §10 for the correction this forces).

**The eight quantities.**

| Axis | Operational quantity | Unit | Note |
|------|---------------------|------|------|
| **Ruin** | Peak deliverable structured work W_peak against resistant targets | J (log) | Band edges = rung-characteristic binding energies (e.g., the M3 band spans crust-disruption to planetary gravitational binding, ~10²⁴–10³² J) |
| **Continuity** | Expected removal cost R = ρ · E[minimal work an optimal band-peer must expend per removal] | J·removals (log) | ρ = E[number of removals required] captures resurrection, backups, phylacteries, loops |
| **Celerity** | Decisive-action tempo ν | actions·s⁻¹ (log) | Measured at contest tempo, not travel speed |
| **Reach** | Effective operational radius ℓ | m (log) | Band edges = rung-characteristic lengths |
| **Transgression** | **Exception bits β** = minimum description length of the *patch* to the local law 𝔇 required to admit A's attested trajectories | bits (log) | The formalization of "hax": how many bits of amendment local physics needs before A's feats are lawful. Time-stop patches locality *and* thermodynamics: expensive. A strong punch patches nothing: β = 0 |
| **Sustain** | Peak half-life τ½ (duration at ≥ 50% of peak output) | s (log) | |
| **Vector** | Access rate α = growth rate of the reachable region (rungs modeled as graph transitions) | (log) | A Spark is a Vector asset of an entirely different order than a fast ship — now visible in the unit |
| **Volition** | Latent skill θ from the contest model of §5, mapped to band quantile | — | The one axis estimated *socially* rather than physically, because skill only exists relative to opposition |

*[Later marginal notice, printed per the errata regime of §10: this table is the **combat battery**. It was subsequently proved incomplete as a coordinate system for the capability preorder — see §10, Erratum 2, and Vol. X.6, which extends it by three faculty axes (Acumen, Discernment, Suasion) without amendment to anything else on this page.]*

Transgression deserves one further remark, because it is the axis the mathematics dignifies most. β is defined *relative to a codification* of 𝔇 (Axiom M3: the codification is declared). This is not a weakness — it is the discovery that **"breaking the rules" is rigorously a property of the description of the rules**, which is why the same feat can be mundane in one universe and a miracle in another, and why the axis was always the one that made hax legible.

---

## §5 — THE DEFEAT GRAPH: ESTIMATION FROM CONTESTS

The Chain of Defeats — who has beaten whom, when, in what context — is the library's richest data, and it admits the full machinery of paired-comparison statistics.

**Model.** Contests form a directed multigraph G with context tags. The base model is Bradley–Terry: **P(A defeats B) = e^{θ_A} / (e^{θ_A} + e^{θ_B})**, with latent strengths θ estimated by maximum likelihood (or Bayesianly, with band priors), and standard errors from the Fisher information of G.

**Connectivity theorem (why the Circuit matters).** θ differences are identifiable *only within connected components* of G. Two populations that never fight are statistically incomparable, whatever anyone's opinion. Corollary, in-fiction and load-bearing: **the Circuit is the omniverse's bridge generator** — sanctioned contest is what makes the omniverse measurable at all — and an isolated universe's inhabitants carry wide intervals *as a theorem*, not as a prejudice. (This is the mathematical content of the Emperor's ±0.85: sparse graph.)

**The Hodge decomposition (the ladder and the chord).** The win-rate flow on G decomposes orthogonally (HodgeRank):
**F = grad(θ) ⊕ curl ⊕ harmonic.**
The gradient part is the best-fitting *ranking* — the Assay's scalar lives here. The **curl** part is irreducible non-transitivity: rock-paper-scissors structure, style-matchups, the cycles where A beats B beats C beats A. Define the **consistency index η = ‖grad F‖² / ‖F‖²**: the fraction of contest reality that a ladder can represent at all.

**Theorem 2 (Quantified projection loss).** The predictive error of *any* scalar assay is bounded below by the curl fraction (1 − η) of the defeat flow.
*This is the doctrine's poetry made math: "the omniverse is not a ladder; it is a chord" is the statement η < 1, and η is measurable.*

---

## §6 — AGGREGATION: FITTED WEIGHTS, NOT DECREED ONES

The published composite is 𝔄 = M_a + (Σ wᵢ sᵢ)/10. The Fundamenta's central reform: **the weights wᵢ are parameters of a predictive model, estimated from data, published with standard errors, and re-estimated as the Ledger grows.**

**The fitting model.** For a contest between A and B in context c:
**logit P(A > B) = κ_c · Σᵢ wᵢ⁽ᶜ⁾ (s_{iA} − s_{iB})**,
a regularized logistic regression of outcomes on axis differentials, with context interactions (duel, chase, siege, contest-of-minds…). The headline weights (0.20 Ruin, 0.18 Transgression, …) are hereby reinterpreted as the posterior means for the *neutral context* (open engagement), and their apparent reasonableness is now a hypothesis under permanent test rather than an aesthetic.

**Model selection.** Aggregation families beyond the linear (weighted power means of order p) compete by out-of-sample predictive log-loss. The linear form holds office only until beaten.

**Gap doctrine, derived.** The table-facing thresholds stop being folklore: with fitted κ, Δ𝔄 maps to win probability. The declared bands (Δ < 0.15 peers; 0.15–0.49 advantage; 0.50–0.99 decisive; ≥ 1.00 outclassed) are calibrated to approximately 55%, 65–75%, 76–90%, and >95% neutral-context win probability respectively — and *those* numbers are now the definition, with the thresholds re-derivable whenever κ updates.

**Context is not noise.** By Theorem 1 and the curl, no single-context weight vector suffices. The axis-interaction model *is* the real object; the scalar is its neutral-context shadow. At the table: use the vector for any engagement with a shape (chase, heist, duel), the scalar for logistics.

---

## §7 — THE ERROR DOCTRINE

The founding instruction was: intervals as small as possible *for any given entrant* — but never smaller.

**Sources of variance, separated.** (1) *Observation noise* — attestation grades enter as likelihood widths (Witnessed narrow, Reconstructed wide, Disputed as mixture components — both filed readings kept, per doctrine). (2) *Model error* — bounded below by the curl (Theorem 2); irreducible by more data of the same kind. (3) *Bridge sparsity* — cross-component comparisons inflate variance in inverse proportion to bridge count (§8). (4) *Epoch drift* — nonstationarity of the subject.

**The pipeline.** Bayesian throughout: band-population prior → likelihood from feats (axis observations) and contests (defeat graph) → posterior on the axis vector and 𝔄. **The published ± is the posterior credible interval**, and it shrinks as √(effective evidence) — which converts the instruction into procedure: *to narrow an interval, commission more attested feats and more bridged contests.* The interval is not a confession; it is a purchase order.

**Ascension Curves as state-space models.** Power is a latent state 𝔄_t evolving in time; feats are noisy observations. Kalman-class filtering and smoothing yield the epoch estimates; "promotion watch" is now precisely: *posterior mass above the band ceiling exceeds 5%.* (Gyre-world subjects break linear-Gaussian assumptions during training explosions; see Open Problems.)

---

## §8 — COMMENSURABILITY ACROSS SYSTEMS (THE ROSETTA THEOREMS)

Different systems have different 𝔇 — different physics, different magic. Why is cross-system measurement possible at all?

**Three invariance strategies, stacked.** (1) *Rung-relative units:* band edges are defined by rung-threat scales (binding energies, characteristic lengths and tempos), and every inhabited system has a binding hierarchy — planets, stars, structure. The Ladder is the shared ruler because it is the shared *situation*. (2) *Law-relative axes:* Transgression is defined against local 𝔇 by construction; it never needed translating. (3) *Bridge calibration:* residual scale freedom between systems is fixed empirically by cross-system contests — bridge edges in the defeat graph — precisely as separate rating pools are linked by inter-pool games.

**Identifiability proposition.** Cross-system Assays are jointly identifiable iff the inter-system contest graph is connected; the variance of any cross-system comparison scales like 1/(number of independent bridges). Crossover-poor shelves are wide-interval shelves *by theorem* — and the Rosetta Tables (X.4) are revealed to be, mathematically, a table of fitted bridge parameters with their standard errors.

---

## §9 — THE HONESTY THEOREMS

What the system cannot do, proved and framed.

**H1 (Projection).** No scalar represents the capability preorder losslessly (Thm 1); the loss is measurable (Thm 2, the curl). *The Assay is a shadow, and we have measured the angle of the light.*

**H2 (Probe scale — the Assay Ban as physics).** To *instrumentally verify* deliverable work of scale E, the measurement interaction must couple at scale E; apparatus and observer are then part of a system-scale event. Direct instrumented assay above ~M8 therefore requires M8-scale apparatus — **measurement is touch** is conservation of energy, not etiquette. High-band values are permanently inferential (Reconstructed), exactly as doctrine held.

**H3 (Reflexivity — the Goodhart clause).** Published assays alter strategy sets: agents train to the test, farm the defeat graph, or hide from it. The measured system contains its measurers; all fitted parameters are subject to periodic mandatory re-estimation, and any assay used as a target degrades as a measure.

**H4 (Domain).** 𝔄 is a functional on Agents(Ω) — things embedded in state spaces. Ground-of-being claimants are, by their own claim, not elements of any Ω. **DECLINED is a domain error, not a large value.** The Omega Band (charter, Part Three) operates on a different space entirely — arguments, not agents — and no refinement of *this* calculus will ever reach it. The wall between M10 and MΩ is type-theoretic.

---

## §10 — REVISIONS THE MATHEMATICS FORCES (ERRATA REGIME)

A foundation that never corrects its own prior publications is decoration. First filing:

**Erratum 1 — Kenshiro, Ruin axis.** Under §4's scoring rule, Ruin for an M3-anchored agent is scored against the M3 band's energy edges. The successor's attested peak deliverable work (anti-personnel absolute; structural demolition order ~10⁹–10¹¹ J) lies *below the M3 band floor*; the clamp applies, and the hand-scored 2.1 cannot be sustained. Revised Ruin ≈ 0.6. Propagating (Δs = −1.5, w = 0.20): Σ drops from 5.214 to 4.914, and
**𝔄(Kenshiro, post-Raoh) : M3.52 → M3.49 ± 0.12 (proposed).**
The anchor is untouched — hegemonic decisiveness never depended on joules, which is the system behaving exactly as designed: *the man still decides the fate of his world; the fists were never the reason.* Filed as proposed erratum, pending re-ratification up the Chain of Record; the Charter's ledger retains 3.52 with an erratum flag until countersigned.

**Standing rule.** Where hand-scored axes conflict with operational scoring, the operational value governs after re-derivation and review. Evidence never overrules the system; the system re-processes the evidence.

**Erratum 2 — the Suasion gap** *(notice printed by later filing; the full derivation and repair are Vol. X.6, the* Instrumenta Facultatum*, second fascicle of this Collection).* §3 of this volume counts **hegemonic** influence toward the Anchor — the warlord who decides a planet's political future without cracking its crust anchors at M3 — while §4's axis table provides no coordinate for the faculty by which he decides it. A purely suasive band-decisive agent therefore anchors correctly and scores near the band floor on all eight axes: the composite misrepresents, by construction, a class of agents the doctrine explicitly intended to honor. §6's own contest tags (*contest-of-minds*) and §2's canonical instance (*a game of secrets*) were accepting data for which this vector has no columns. **Repair, as ratified into review:** the axis vector is extended by three operational faculty axes — **Acumen** (prediction–planning advantage, bits·epoch⁻¹), **Discernment** (veridicality bits under adversarial concealment), **Suasion** (policy-determination bits at message-scale footprint and β = 0) — with fitted, not decreed, weights per §6's own reform. The axioms, primitives, Anchor, scoring rule, and every theorem of this volume are untouched (X.6, Theorem 2: an extension of coordinates, not of axioms). The battery of eight axes plus Attestation retains its name, the Nine Measures, as the combat battery; the full instrument is the Twelve Measures. Filed as proposed extension, pending re-ratification up the Chain of Record.

---

## §11 — OPEN PROBLEMS (THE THESIS LIST)

1. **Coalition power.** Team capability is not additive; formalize via cooperative game theory (Shapley attribution of contest outcomes to members; superadditivity conditions — when is a party more than its Assays?).
2. **Curl-aware prediction.** Beat the scalar: practical match-forecasting using the full Hodge decomposition; style taxonomies as curl clusters.
3. **The codification problem.** β (Transgression) depends on the declared compression of 𝔇; characterize invariance classes of codifications and bound β's codification-sensitivity.
4. **Nonstationary ascension.** State-space models for Gyre-class subjects whose latent power is self-exciting (training arcs, rage thresholds); detect phase transitions (promotion) in real time.
5. **Backreaction quantification.** Measure H3: how much does publishing a ledger shift the defeat graph's subsequent statistics?
6. **Exotic rung edges.** Reference scales for rungs 11–16, where "binding energy" needs generalization (what is the crust of a filament?).
7. **The Omega ordinal conjecture.** Whether MΩ scores admit a principled refinement via proof-theoretic strength (ordinal analysis of grounding arguments) — the only known candidate for putting mathematics under the Seat without committing H4's domain error. Flagged speculative; filed one desk up.

---

## COLOPHON — WHAT HERE IS REAL

*Out of character, for the record: this treatise's load-bearing components are established mathematics, cited by their true names — representational measurement theory (Krantz–Luce–Suppes–Tversky); interventional causality and do-calculus (Pearl); total-variation influence; minimum description length (Rissanen) and Kolmogorov complexity for the Transgression formalization; Bradley–Terry (1952) and its Bayesian descendants (TrueSkill) for paired comparison; HodgeRank (Jiang–Lim–Yao–Ye) for the gradient/curl decomposition of preference flows; Kalman filtering for latent-state tracking; Shapley values for coalition attribution; and the Goodhart/Lucas critique for reflexivity. The synthesis — anchoring magnitude in coarse-grained causal decisiveness, pricing rule-breaking in exception bits, and treating a fictional multiverse's crossover fights as bridge edges in a rating graph — is original to this document. The impossibility results (Theorems 1, H2, H4) are genuine: they hold for any power-measurement scheme, in any world, including the real one, which is why sports rankings disagree, why "strongest character" debates never terminate, and why this volume's most useful export is not a number but a discipline for arguing about numbers.*

*— Vol. X.2, first fascicle. The Fundamenta is founded; the theses are posted; the desk lamp at the Athenaeum burns.*
