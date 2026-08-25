# Step 4 — The Entanglement Pass: a plan, written before any of it is written

*Drafted 2026-08-25 at the owner's instruction: "plan out step four before you begin step four,
so that before any history itself is written, there's a plan on how to implement everything in
totality that's been catalogued." Nothing in this document has been executed. It is a proposal
with its open rulings named.*

---

## 0. The one-sentence version

**Threads are citations, not opinions.** The charter already says what a Thread is, and the whole
plan follows from taking that literally: entanglement is a *referencing* problem over an address
space that already exists, not a semantic-similarity problem over 98,145 entities.

---

## 1. What a Thread actually is (charter, Part Seven)

> **⌁ Threads.** Cross-references by spine code, shelfmark, and event-code — every factual claim
> in The Record anchors to a Law citation or an Annex event-code per the Doctrine of Derivation.

And the charter's own worked example:

> **⌁ Threads.** II.A.5 (home volume); II.A.11 (versus other Gyre arts); IV.6 (the wasteland's
> raider swarms); VIII.9 (the succession wars).

**Three consequences, and they decide the entire design:**

1. **A thread resolves to an ADDRESS.** A spine code (`II.A.5`), a shelfmark (an entity's
   Ladder-of-Being address), or an event-code (`VIII.9`, the Chronicle annex). It is checkable.
   A thread that resolves to nothing is not a weak thread, it is a **broken** one.
2. **Threads are therefore bounded.** The naive fear — 98,145 entities is 4.8 billion pairs —
   is a fear about the wrong object. Nothing pairs entities against each other. Each entry cites
   a handful of addresses out of a few thousand, the way a footnote does.
3. **Threads are DERIVED, not invented.** Hard Rule 1 forbids inventing facts, and Hard Rule 5
   currently holds every Threads section at "pending" precisely because the doctrine to derive
   them from had not been applied. The charter's Part Four *already contains* that doctrine — the
   Unification Doctrine, the Chord, the Silence, Terra Mosaica, the Five Ages, the Great
   Identifications, the Doctrine of Derivation, the Chain of Record. **Step 4 applies existing
   doctrine to the catalogue. It does not write new cosmology.**

---

## 2. What already exists (read this before assuming a blank page)

| Asset | State | Role in Step 4 |
|---|---|---|
| `thread_integrity.py` (184 ln) | **Written, and its design is right.** Classifies RECIPROCAL / ASYMMETRIC-LAWFUL / ASYMMETRIC-SUSPECT / DANGLING, and correctly treats one-way threads as *lawful* under the Aperture Doctrine or propagation delay | **The verifier.** m12 says its detection is "structurally unreachable" — it compares implied threads against a directed thread graph **it is never given**. Step 4 builds that graph. m12 closes as a side effect. |
| `data/CHARTER_SPINE_CODES.json` | 219 codes; 35 catalogued sources still unaddressed | The target space for volume-level threads |
| `VIII_MASTER_CHRONICLE.md` | Written (24 KB event spine) | The source of **event-codes** (`VIII.n`) |
| `I9_THE_CONCORDANCE.md` | Written | Political geography — governs which threads are *lawful* |
| `weave.py` (487), `chain.py` (497) | Written; `data/CHAIN.json` **has no reader** (m37) | Candidate thread *producers*; m37 resolves if Step 4 consumes CHAIN |
| `entity_match.py` (278) | Written | Name-level joining across sources — the risky one, see §6 |
| `resonance.py`, `chord_field.py`, `cosmography.py` | Written | The Chord substrate: physical/structural relations |
| `address_space.py`, `NAVTREE.json` | Written | Shelfmark resolution |

**Nothing here needs inventing. The gap is a graph and a generator, not a theory.**

---

## 3. The four thread classes, and where each one comes from

Every thread must belong to exactly one class, and each class has a **mechanical derivation** —
which is what makes the pass auditable rather than a model's opinion.

**T1 — HOME (`II.A.5 (home volume)`).**
The entry's own volume. Derivation: `address.spine_code_for(source)`. Zero judgment, 100%
coverage, cannot be wrong if addressing is right. **This alone gives every one of the 98,145
entries a non-empty, correct Threads section.**

**T2 — COHORT (`II.A.11 (versus other Gyre arts)`).**
Sibling volumes under a shared parent in the Collection→Set→Series tree, filtered to those the
entry's own record gives a reason to name — same category, shared faction, shared place.
Derivation: `NAVTREE.json` + the entry's own catalogued fields. Still no cross-verse claim.

**T3 — EVENT (`VIII.9 (the succession wars)`).**
An Annex event-code the entry participates in. Derivation: the Chronicle's event spine joined
against the entry's `origin_work` / catalogued events. **This is the first class that crosses
verses**, and it crosses them *through the charter's own history* rather than by resemblance.

**T4 — LAW (`X.3 §G-114`).**
A Law citation for a factual claim in The Record, per the Doctrine of Derivation. Derivation:
the claim's axis → the Law that governs it (the Chord for substrate claims, the Silence for
conflict, the Ladder for scale).

**Deliberately NOT a class: "these two characters are similar."** That is the Great
Identifications' territory, it is a curatorial ruling, and §7 keeps it that way.

---

## 4. The build order (each phase ships a verifiable artifact)

**Phase 4.0 — Close the addressing gap first.** 35 catalogued sources have no spine code
(~12,000 entries), including Lord of the Rings, Fallout, Elder Scrolls and all six Pantheons.
**T1 is undefined for them**, so they cannot be threaded at all. This is Hard Rule 2 territory —
owner work, not automatable. **It gates everything else.**

**Phase 4.1 — `threads.py`, T1 + T2 only.** Emit a directed graph
`data/THREADS.json: {shelfmark: [{"to": address, "class": "T1|T2", "why": "...", "from": "..."}]}`.
No model calls — pure derivation from the address space. **Deliverable: every entry has a real,
resolvable Threads section.** Verify with `thread_integrity.py`, which finally has its graph.

**Phase 4.2 — Wire `thread_integrity` into the battery.** DANGLING must be zero. ASYMMETRIC-
SUSPECT gets a floor. This runs *before* T3/T4 so the verifier is proven on the easy classes.

**Phase 4.3 — T3, the Chronicle join.** Parse the event spine into `data/EVENTS.json` with
stable codes, join to entries. **This is where cross-verse entanglement actually happens.**

**Phase 4.4 — T4, Law citations.** Per-claim, so it belongs with generation rather than before it.

**Phase 4.5 — Re-open the prose gate, per source, as each clears.** Not globally.

---

## 5. Scale — the arithmetic, so nobody has to fear it

98,145 entries × ~4 threads = **~390,000 edges**. `THREADS.json` at ~120 bytes/edge ≈ **47 MB** —
the same order as `manifest.json` (88 MB), which the kit already handles. T1/T2 are dictionary
lookups: the whole pass is **minutes of CPU and zero model calls**. Only T3's join needs care,
and it is entry×events (~98k × ~10²), not entry×entry.

**There is no combinatorial explosion anywhere in this design.** If a future revision introduces
one, that is the signal it has drifted into similarity-matching and left the charter behind.

---

## 6. The failure modes, named in advance

**The one that would do real damage: `entity_match` fabricating identity.** Joining "Wally West
(New Earth)" to "Wally West (Prime Earth)" is a *continuity* claim, and the ledger already shows
240 mined deeds stranded on exactly this question. **T3 must join on event participation, never
on name similarity.** If a thread's only evidence is that two names resemble each other, it is
not a thread.

**Dangling threads.** Mitigated by construction: emit an address only if it resolves *now*, and
`thread_integrity` re-checks. **DANGLING = 0 is a release gate, not a metric.**

**Hard Rule 0.** No `[:n]` anywhere in the pass. A thread list truncated at 5 silently decides
the sixth relation does not exist. If an entry has 40 lawful threads it carries 40.

**The quiet one: a Threads section that is present but empty.** Indistinguishable from
"pending" to a reader and from "done" to a checker. **An entry with zero threads after T1 is
impossible by construction** (T1 is its home volume) — so zero threads means the pass did not
run for that entry, and must be an OPERATOR-level refusal, not a blank.

---

## 7. Owner rulings needed before Phase 4.1

**A. The 35 unaddressed sources (Phase 4.0).** Blocking. Which Collection/Set does each belong
to? The six Pantheons (~2,798 entries) look like one coherent Collection missing its shelf.

**B. Do the Great Identifications get thread codes?** Part Four names them as the place "where
the walls come down entirely." They are the strongest cross-verse claims in the charter and they
are *curatorial*. Proposal: **T5, owner-authored only**, never derived. Machinery would serve them
unchanged; only the authorship rule differs.

**C. Reciprocity policy.** `thread_integrity` classifies one-way threads as lawful under the
Aperture Doctrine or propagation delay. Is a T2 cohort thread expected to be reciprocal? A
smaller volume naming a larger one is ordinary; the reverse may not be.

**D. Does Step 4 rewrite the 145 withdrawn chapters' Threads, or are they regenerated?**
Recommendation: **regenerate.** They are content-hashed, the sources were 0–9% cited, and they
should not return until their citations improve regardless of threading.

---

## 8. How this pass is gated (the 2026-08-25 safety doctrine applies in full)

- **The prose gate stays closed** through 4.0–4.4. Step 4 produces `THREADS.json`, not prose.
- **`thread_integrity` becomes a drill net**: DANGLING > 0 is a **SUPERVISOR**-level refusal for
  that source; a *corrupt or unreadable* `THREADS.json` is **OWNER**-level, because every entry
  in the library cites it.
- **Every phase adds its own attack to `drill.py`** before it ships — including the one that
  matters most: *can a thread be emitted that points at nothing?*
- **Each source is its own area.** A source failing thread integrity closes that source, not
  the library.
- **No phase may lower a floor to go green.** The ratchet rule.

---

## 9. What I recommend, plainly

Do **Phase 4.0 and 4.1 only**, then stop and look. T1+T2 need no model, no network and no new
theory, and they convert every "pending" in the library into a real, checkable cross-reference.
That is most of what "the library feels like one place" means, and it will surface the addressing
gaps and reciprocity questions against real data — which is a far better basis for ruling on B
and C than this document is.
