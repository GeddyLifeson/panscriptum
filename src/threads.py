#!/usr/bin/env python3
"""
THREADS — Step 4: the T1/T2/T3/T4 entanglement pass (Phases 4.1, 4.3 and 4.4).

WHAT A THREAD IS, and the whole design follows from taking the charter literally (Part Seven,
via STEP4_PLAN.md §1): a Thread is a CITATION, not an opinion. It resolves to an ADDRESS — a
spine code, a shelfmark, or an Annex event-code — and a thread that resolves to nothing is not a
weak thread, it is a BROKEN one. So entanglement is a referencing problem over an address space
that already exists, not a semantic-similarity problem over 282,822 entities. Nothing here pairs
entities against each other; each entry cites a handful of addresses, the way a footnote does.

THE FOUR CLASSES THIS MODULE EMITS, and only these four:

  T1 HOME    the entry's own volume, from `address.spine_code_for(source)`. Zero judgment,
             100% coverage, cannot be wrong if the addressing is right. This alone gives every
             entry in the library a non-empty, correct Threads section.
  T2 COHORT  sibling volumes under a shared parent in the Collection→Set→Series tree, filtered
             to those the entry's own record gives a reason to name.
  T3 EVENT   the Chronicle join, to a Chronica Annex address (`VIII.n`). ADMITTED 2026-09-09
             under §7G, which authorised Phase 4.3 on 2026-09-08 and scopes it to exactly this.
             THE JOIN IS ON EVENT PARTICIPATION NAMED BY THE CHARTER, never on resemblance:
             a shelf earns a Canon only where that Canon's own description names a particular
             belonging to it -- VIII.9 names "the Cell and Buu crises", "the Void Century and
             its erasure", "the Great Ninja Wars", "the Horus Heresy". A shelf whose Canon
             names nothing of its gets no T3, and that silence is correct rather than a gap.

  T4 LAW     the Law citation, to a Collection X address. ADMITTED 2026-09-09 under §7H,
             which authorised Phase 4.4. Per the Doctrine of Derivation every Digest claim must
             cite a Law or a Deed; T3 is the Deed half and this is the Law half. DERIVED PER
             ENTRY in `threads_for`, not stored -- see the note there -- because unlike the
             other three it depends on whether THIS entry asserts a Magnitude.

             ITS POPULATION IS SMALL AND HONESTLY SO. A Law citation attaches to a claim in
             The Record, and The Record is generated prose, which is gated -- so T4 today covers
             only the claim the CATALOGUE makes: 447 of 282,711 entries assert a Magnitude band.
             Citing a Law for every entry regardless would be decoration, which the Doctrine
             itself calls a Digest sentence with neither citation.

DELIBERATELY NOT EMITTED:

  T5         the Great Identifications. Owner-authored ONLY, by the §7B ruling — never derived,
             never inferred. `edge()` REFUSES to construct one, and a drill net attacks that
             refusal. Part Four names them as the place "where the walls come down entirely",
             and a claim of that weight must have a person's name on it.

  "these two characters are similar" is not a class here and must never become one. That is the
  Great Identifications' territory and it is a curatorial ruling. If a thread's only evidence is
  that two names resemble each other, it is not a thread — STEP4_PLAN.md §6 names `entity_match`
  fabricating identity as the one failure mode that would do real damage, and the ledger already
  shows 240 mined deeds stranded on exactly that question. This module never calls it.

WHY THE FILE IS NOT KEYED BY SHELFMARK, WHICH IS WHAT THE PLAN SAYS
-------------------------------------------------------------------
STEP4_PLAN.md §4 specifies `data/THREADS.json: {shelfmark: [...]}`. **Per-entity shelfmarks do
not exist.** `address.placeholder_shelfmark` is per-SOURCE and returns an honest
`Ω › ? › ? › ... [UNCHARTED]`, because CLAUDE.md Hard Rule 4 forbids inventing one: a real
shelfmark needs Ladder-of-Being research per entity that has not been done. Keying on the
placeholder would make every entry of a source collide under one key, and minting a synthetic id
to stand in for a shelfmark would be inventing the address the rule forbids.

So the graph is stored NORMALISED, by (source, category), and `threads_for()` expands it to the
per-entry view the plan actually asks for. This is lossless, not a reduction: for T1 and T2 every
entry in a source sharing a category has, by construction, exactly the same thread set — the
classes are derived from the address space and the record, never from the entry's own text — so
the normalised form and the expanded form carry identical information. Measured over the whole corpus:
282,822 entries collapse to 1,370 (source, category) keys, every entry sharing a key gets a
byte-identical thread list, and none comes back empty -- so the file is kilobytes rather
than the ~136 MB an expanded one would take.

THAT IS A DEVIATION FROM A RATIFIED PLAN AND IS FLAGGED AS ONE. It is recorded here, in the
handoff, and in a work order, rather than made quietly. Nothing about the threads themselves
changes; only where they are written down.

WHAT REFUSES, AND WHY EACH REFUSAL EXISTS
-----------------------------------------
  * the plant-wide HALT, first, like every other entry point (Hard Rule -1).
  * `prose_gate.step4_gate_open()` — the ratification. This module may be IMPORTED and its pure
    functions exercised at any time (that is how the drill proves it), but it may not WRITE
    without the owner's ratification, and the CLI refuses outright. The gate asserts three
    things at once: the plan has been read, its §7 rulings are answered, and Phase 4.0 is done.
  * an address that does not RESOLVE is never emitted — mitigation by construction for the
    dangling-thread failure mode (§6). `thread_integrity` re-checks afterwards, and DANGLING = 0
    is a release gate, not a metric.
  * an entry with ZERO threads after T1 is impossible by construction, so if one is ever
    produced that is an OPERATOR-level refusal and not a blank. §6 calls this "the quiet one":
    a Threads section that is present but empty is indistinguishable from "pending" to a reader
    and from "done" to a checker.

HARD RULE 0 APPLIES IN FULL. No LIST in this pass is ever truncated: if an entry has forty
lawful threads it carries forty, and a thread list cut at five would silently decide the
sixth relation does not exist, which is the precise shape the rule exists to forbid.

The one `[:n]` in this file is `parts[:2]` in `cohort_family`, which decomposes an ADDRESS
into its Collection and Set -- not a listing, and not a cap on anything a reader would
count. This paragraph used to claim "there is no `[:n]` anywhere in this pass", which was
false as written and is the kind of absolute sentence this file's audience reads as a
checked fact (order eb74d9cd9bae).
"""
import argparse
import collections
import json
import os
import sys

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# A regex escape eaten in transit is this project's oldest bug; every module carries the guard.
_BAD_CHARS = (chr(8), chr(11), chr(12), chr(7))
if any(c in open(os.path.abspath(__file__), encoding="utf-8").read() for c in _BAD_CHARS):
    raise SystemExit(__file__ + ": a regex escape was eaten in transit.")

import address as ADDR          # noqa: E402
import silence                  # noqa: E402

OUT = os.path.join(HERE, "data", "THREADS.json")

# The classes this module is permitted to derive. T4 is a later phase; T5 is owner-authored only
# and is not in this tuple BY RULING, not by oversight -- see `edge()`.
#
# T3 ADMITTED 2026-09-09 UNDER STEP4_PLAN §7G, which authorised Phase 4.3 on 2026-09-08 in the
# owner's own words ("get 4.3 started too") and scopes it to exactly one thing: T3, the Chronicle
# join. This tuple and `edge()`'s refusal text both cited §7E as the authority for refusing T3 --
# and §7E has been superseded TWICE, by §7F (which authorised 4.2) and §7G. The citation was two
# rulings stale, which is the same defect class this tree has 50 open instances of.
#
# T4 ADMITTED 2026-09-09 UNDER STEP4_PLAN §7H, which authorised Phase 4.4 and scopes it to the
# Law citation alone. Per the Doctrine of Derivation every Digest claim must cite "a Law (by Part
# or spine code) or a Deed (by event-code)": T3 carries the Deed half, T4 carries the Law half.
#
# §7H ALSO RECORDS WHAT T4 CANNOT REACH YET, and it is worth repeating here because the number
# looks small. A Law citation attaches to a factual claim in THE RECORD, and The Record is
# generated prose, which is gated. So T4 today covers only the claim the CATALOGUE itself makes:
# an entry asserting a Magnitude band. Measured at the ruling: 447 of 282,711 entries carry one.
# A thin T4 that is honestly thin is correct; citing a Law for every entry regardless of whether
# it makes a claim would be decoration, which the Doctrine explicitly calls a Digest sentence
# with neither citation.
#
# T5 STILL STAYS OUT, by §7B: owner-authored only, never derived. And 4.5 -- re-opening the prose
# gate -- was NOT authorised by §7H; `prose_enabled` is untouched.
DERIVABLE = ("T1", "T2", "T3", "T4")

# THE ANNEX IS AN ADDRESS SPACE, AND UNTIL 2026-09-09 NOTHING LOADED IT (order d57a66d25b11).
# A T3 points at a Collection VIII address -- §3's worked example is `VIII.9 (the succession
# wars)` -- but `known_codes` was built from the SOURCES' spine codes alone, so `_resolves` said
# no to every Annex code and `edge()` refused every T3 by construction, whatever mapping it was
# handed. `data/CHARTER_SPINE_CODES.json` does not carry them because it is the source-to-shelf
# map and the charter says so: "Cross-shelvings in Collections III-VIII not repeated here."
#
# The charter DOES define them -- "COLLECTION VIII — THE CHRONICA ANNEX (17 Canons, 275 volumes)"
# -- so `data/ANNEX_CANONS.json` is a transcription of the charter's own list, not an invention,
# and Hard Rule 2 is satisfied. Absent or unreadable, T3 simply cannot resolve and every T3 is
# refused: fail-closed, and the same answer this module gave before the file existed.
ANNEX_CANONS = os.path.join(HERE, "data", "ANNEX_CANONS.json")
# The shelf-to-Canon join itself -- see `annex_join()`.
ANNEX_JOIN = os.path.join(HERE, "data", "ANNEX_JOIN.json")
# Collection X, the measurement doctrine -- the LAW a T4 cites. See `law_codes()`.
LAWS = os.path.join(HERE, "data", "LAWS.json")

# The Law that governs a Magnitude claim. X.1 is "The Nine Measures (the axes and weights of the
# Custodial Assay ... the Attestation grades)" -- the volume that DEFINES the bands an entry is
# asserting. Deliberately not X.3: that is the Ledger of per-person worksheets, and citing it for
# a band-only magnitude would claim an Assay that was never run (Hard Rule 3).
MAGNITUDE_LAW = "X.1"

# A band the entry actually asserts. "unassayed" is the honest non-claim the prompt asks for when
# a description demonstrates no feat, and an absent/empty value is the same thing less explicitly
# -- neither is a claim, so neither earns a citation.
_NOT_A_CLAIM = ("", "unassayed", "none", "n/a")


def asserts_a_magnitude(entry):
    """Does this entry make a scale CLAIM that a Law governs? -> bool. PURE."""
    m = (entry or {}).get("magnitude")
    return bool(m) and str(m).strip().lower() not in _NOT_A_CLAIM

# `spine_code_for` never raises; it returns this when the Acquisitions Index cannot place a
# source. An UNASSIGNED code is not an address, so it is never threaded to and never threaded
# from -- emitting one would be exactly the dangling thread §6 forbids.
UNADDRESSED = "UNASSIGNED"


class ThreadRefused(Exception):
    """A thread this module is not permitted to derive, or one that resolves to nothing."""


def cohort_family(code):
    """The Collection.Set whose members cohort with each other. -> str or None.

    `II.A.3` -> `II.A`, and `II.A` -> `II.A` as well. Both a Series and the bare Set it sits
    under belong to the same room.

    THE BARE SET USED TO BE EXCLUDED, AND THE OWNER RULED IT IN (2026-08-31, order
    a8864d2361de). This was `if len(parts) >= 3 else None`, so any two-component code returned
    None and a source shelved at a bare Set could neither carry nor receive a cohort thread.
    Measured then: 60 of 210 sources (29%) and 465 of 1,370 (source, category) keys had an empty
    cohort list, their entries carrying exactly one thread -- the home volume -- for ever. It
    also produced an asymmetry nobody had ruled on: a source at `II.A.3` cohorted with the other
    `II.A.n` volumes but never with a source shelved at bare `II.A`, which is the very Set those
    siblings live in.

    WHAT IS STILL EXCLUDED, AND WHY THAT IS THE SAME RULE RATHER THAN AN EXCEPTION. The family
    is the FIRST TWO components, so a Set still never cohorts with its neighbouring Sets:
    `II.A` and `II.B` remain different rooms. Cohorting there would be Collection level, which
    would put every D&D supplement in a room with every anime -- the case the original exclusion
    was written for, and it is untouched. `III.1` and `III.7` are two Sets under Collection III,
    so the eleven pantheons still do not cohort with each other.

    MEASURED AFTER THE RULING: of the 26 two-component codes, 11 gain siblings because Series
    exist beneath them (II.A, II.C, II.D, II.F, II.H, II.I, II.J, II.K, II.L, II.N, II.P); 15
    do not, because nothing is shelved beneath them at all (II.E, II.Q, the eleven III.n
    pantheons, VII.6, VII.7). An empty cohort for those is a fact about the shelf, not a gap in
    the pass, and `main()` now reports the count either way.

    THE RULING'S EFFECT, measured immediately after it landed: sources with no cohort at
    all fell from 60 of 210 to 31 of 210, and T2 edges rose from 885,123 to 1,226,923
    (5.34 threads per entry, up from 4.13). The 31 that remain are the 15 childless Sets
    above plus sources whose category holds no counterpart anywhere in their family.
    """
    if not code or code == UNADDRESSED:
        return None
    parts = [p for p in str(code).split(".") if p]
    return ".".join(parts[:2]) if len(parts) >= 2 else None


def annex_codes():
    """The Chronica Annex's Canon codes. -> set of 'VIII.n', or an EMPTY set if unreadable.

    FAILS CLOSED, and the direction is chosen rather than inherited. An empty set means every T3
    is refused by `edge()`'s anti-dangling test -- which is exactly the behaviour this module had
    before the Annex existed as an address space, so a missing or corrupt file degrades to
    "cannot derive T3" and never to "derive T3 to an address nobody can resolve". The opposite
    default would put broken threads in the artifact on the strength of a read error.

    Not cached: `build()` calls it once per run, and a stale set held across a charter revision
    would be a smaller address space wearing the right shape.
    """
    try:
        with open(ANNEX_CANONS, encoding="utf-8") as f:
            doc = json.load(f)
    except Exception:
        silence.note("threads.py:annex-unreadable")
        return set()
    out = {str(c.get("code")) for c in (doc.get("canons") or []) if c.get("code")}
    # THE FILE DECLARES ITS OWN POPULATION, SO CHECK IT. A truncated table would silently make
    # some Canons unaddressable and refuse exactly the T3s that pointed at them, which is a
    # smaller universe and this project's oldest failure shape.
    declared = ((doc.get("declared") or {}).get("canons"))
    if declared and len(out) != declared:
        silence.note("threads.py:annex-short")
        return set()
    return out


def law_codes():
    """The Collection X volume codes. -> set of 'X.n', EMPTY if unreadable.

    FAILS CLOSED exactly as `annex_codes` does: an empty set means `edge()` refuses every T4 on
    the anti-dangling rule, which is the behaviour this module had before Collection X was an
    address space. Never the other way.
    """
    try:
        with open(LAWS, encoding="utf-8") as f:
            doc = json.load(f)
    except Exception:
        silence.note("threads.py:laws-unreadable")
        return set()
    out = {str(c.get("code")) for c in (doc.get("laws") or []) if c.get("code")}
    declared = ((doc.get("declared") or {}).get("volumes"))
    if declared and len(out) != declared:
        silence.note("threads.py:laws-short")
        return set()
    return out


def _known_for_t4():
    """The address set a T4 is checked against. Just the Laws: a T4 never points anywhere else."""
    return law_codes()


def annex_join():
    """Which Annex Canons does each source's history belong to? -> {source: [{to, why}]}.

    THE JOIN IS THE CHARTER'S OWN, NOT AN INFERENCE. `data/ANNEX_JOIN.json` records, per source,
    the Canon whose description in `00_MASTER_CHARTER.md` NAMES one of that source's events --
    VIII.9's subject line contains "the Cell and Buu crises", so Dragon Ball's history belongs to
    the Canon of the Great Wars because the charter put it there, in its own voice. Its builder
    verifies every `why` is a verbatim substring of that Canon's own subject line and refuses to
    write the file otherwise, so a row cannot rest on a phrase somebody remembered.

    That is what makes T3 satisfy §7G's one hard constraint. The join is on EVENT PARTICIPATION,
    stated by the charter; nothing here compares names for similarity, and a source the Annex
    never names gets NO T3 -- a silence that is correct rather than a gap.

    FAILS CLOSED: unreadable or absent means an empty join, which means no T3 is emitted at all.
    """
    try:
        with open(ANNEX_JOIN, encoding="utf-8") as f:
            doc = json.load(f)
    except Exception:
        silence.note("threads.py:annex-join-unreadable")
        return {}
    return doc.get("join") or {}


def _resolves(code, known_codes):
    """Is this an address that exists RIGHT NOW? -> bool. The anti-dangling test."""
    return bool(code) and code != UNADDRESSED and code in known_codes


def edge(to, cls, why, frm, known_codes):
    """Build one thread edge, or refuse. -> dict.

    TWO REFUSALS, AND THEY ARE THE POINT OF THE FUNCTION:

    1. A class this pass may not derive. T5 is the Great Identifications and the §7B ruling is
       that they are owner-authored only -- never derived, never inferred, never emitted by
       `threads.py`. T3 was authorised by §7G on 2026-09-08 and T4 by §7H on 2026-09-09, so both
       are in `DERIVABLE` and neither is refused here any more; T5 alone is. Refusing here rather
       than at the call site means a future caller cannot reach the wrong class by a new path.
    2. An address that does not resolve. §6: emit an address only if it resolves NOW. A thread
       that points at nothing is broken, and building it and hoping the verifier catches it
       later is the wrong order.
    """
    if cls not in DERIVABLE:
        raise ThreadRefused(
            "class %r may not be derived by threads.py. T1/T2 are Phase 4.1; T3 (the Chronicle "
            "join) was authorised by STEP4_PLAN.md §7G on 2026-09-08 and T4 (Law citations) by "
            "§7H on 2026-09-09, so all four are in DERIVABLE; T5 (the Great Identifications) is "
            "OWNER-AUTHORED ONLY by the §7B ruling and must never be machine-derived. (This "
            "refusal has now been stale twice: it cited §7E after §7F and §7G superseded it, and "
            "it went on calling T4 UNAUTHORISED after §7H admitted it the same evening. A "
            "refusal message naming a ruling is a citation and rots like one.)" % (cls,))
    if not _resolves(to, known_codes):
        raise ThreadRefused(
            "refusing to emit a thread to %r, which does not resolve to a live address. A thread "
            "that resolves to nothing is not a weak thread, it is a broken one "
            "(STEP4_PLAN.md §1, §6)." % (to,))
    return {"to": to, "class": cls, "why": why, "from": frm}


# The three `topic` values that are NOT simply a shorter spelling of a `category`. Measured over
# the live corpus 2026-08-31: of the 139,289 entries carrying a topic, 76.1% restate their
# category under a shorter name ("Places" for "Places & Locations") and add nothing, 11.0%
# CONTRADICT it (a catalogue fault, under investigation, deliberately not split on), and 12.9%
# -- these three -- carve a genuinely finer room out of a coarser one.
FINER = {"Weapons": "Vessels & Things", "Relics": "Vessels & Things", "Wars": "Events"}

# Which room each SUBROOM shelf belongs to -- the same shape as FINER above and for the same
# reason: a shelf that names the wrong room must open nothing. Derived from `pipeline.SUBROOMS`
# rather than restated, because two hand-kept copies of one mapping is how they come to
# disagree, and this one decides the shape of the thread graph.
# WHY THE TABLE MIGHT BE EMPTY, ON A MODULE-LEVEL CONSTANT, THE WAY `assay.RHO_FALLBACK_REASON`
# DOES FOR THE IDENTICAL PROBLEM (order 04c6360636bf). None means the table was built; a string
# means it was not, and says what stopped it.
#
# WHAT AN EMPTY TABLE DOES, and it is not a degraded corner: `category_path` gates the finer room
# on `SUBROOM_PARENT.get(sub) == coarse`, so with `{}` no entry can ever reach its subroom and
# EVERY finer room in the graph disappears -- the pass silently reverts to the pre-2026-09-01
# shape the comment in `category_path` calls "a regression dressed as a correction". Nothing
# downstream catches it: `verify()` tests structural properties that still hold, `main()` prints
# counts that are internally consistent and merely smaller, the ratification gate is about
# authorisation and not shape, and THREADS.json lands derived under a different rule with nothing
# in the artifact or on the console saying so. The only reader who could tell is one who happened
# to remember last run's numbers.
#
# The fallback itself is right -- an import cycle or a partial tree must not stop the module
# loading. The silence was the fault, in the file whose docstring is a list of refusals and whose
# sibling paths record every gap they meet by name: `build()` writes an `unaddressed` list into
# the artifact under the heading NOT SILENTLY DROPPED, `threads_for` raises rather than return a
# blank, and `main()` reports sources with no cohort "because a reader cannot otherwise tell
# 'this volume has no siblings' from 'the cohort pass did not reach it'". This is the same
# distinction, about the rule the graph was built with.
SUBROOM_FALLBACK_REASON = None

try:
    import pipeline as _PL
    SUBROOM_PARENT = {v: room for room, vs in _PL.SUBROOMS.items() for v in vs}
except Exception as _e:                 # pragma: no cover -- import cycle or a partial tree
    SUBROOM_PARENT = {}
    SUBROOM_FALLBACK_REASON = (
        "pipeline.SUBROOMS could not be read (%s: %s), so the subroom->room table is EMPTY and "
        "no entry can reach a finer room. Every finer room in this graph is absent, and the "
        "graph is the pre-subroom shape -- not a measurement that the shelves are empty."
        % (type(_e).__name__, _e))
    silence.note("threads.py:subrooms-unavailable")
    sys.stderr.write("threads: " + SUBROOM_FALLBACK_REASON + "\n")


def _key(path):
    """A path as one JSON-safe string. `("Vessels & Things", "Weapons")` -> the two rooms
    joined by " > ", coarsest first, so the stored key reads as the shelf reads."""
    return " > ".join(path)


def category_path(entry):
    """The category rooms an entry belongs to, coarsest first. -> tuple.

    `("Vessels & Things",)` for a vessel with no finer label; `("Vessels & Things", "Weapons")`
    for one the catalogue has actually called a weapon.

    OWNER RULING 2026-08-31: SPLIT. The pass used to cohort at the seven catalogue categories
    alone, which put a weapon in a room with a spaceship. It now cohorts at the finest room the
    data supports -- but at the finest room BOTH volumes support, which is the part that matters
    and is why this returns a path rather than a single key.

    WHY NOT SIMPLY KEY ON THE FINEST VALUE. Because `topic` is not evenly present: 175 of 210
    sources carry it on every entry, and 35 carry it on some (Marvel is missing it on 45,590
    entries, DC on 16,417). Keying on the finest value alone would mean a labelled weapon never
    cohorts with an unlabelled one, which is the two-vocabulary defect of order 9b9e7d33399d
    wearing new clothes -- and worse, it would be asserting that Marvel holds no weapons when
    what is true is that nobody has said which of its vessels are weapons.

    SO: a volume qualifies as a cohort if it holds ANY room on the path, and the edge is recorded
    at the FINEST room the two share. Against a fully-labelled sibling a weapon threads to
    `Weapons` and never to that sibling's spaceships, which is the split. Against an unlabelled
    one it threads at `Vessels & Things`, which claims only what is known. Nothing is invented in
    either direction, and no relation is denied on absent data.

    The 11.0% where `topic` and `category` contradict each other are NOT split on: only the three
    values in `FINER` open a finer room, and each is checked against the parent it is supposed to
    sit inside. A `topic: Powers` under `category: Vessels & Things` is a catalogue fault, not a
    finer grain, and it is being investigated separately rather than encoded into the graph.
    """
    long_form = (entry or {}).get("category")
    coarse = None
    if isinstance(long_form, str) and long_form.strip():
        coarse = long_form.split("(")[0].strip() or long_form.strip()
    short = (entry or {}).get("topic")
    short = short.strip() if isinstance(short, str) and short.strip() else None
    if coarse is None:
        # No category at all. `topic` is the only thing on offer, so it IS the coarse room.
        return (short,) if short else ()

    # `subroom` FIRST, `topic` AS THE FALLBACK (2026-09-01). The finer room is a CATALOGUE fact
    # -- which shelf inside this room -- and `subroom` is the field that answers exactly that.
    # `topic` was standing in for it, badly: it is the ENCYCLOPEDIA SERIES axis, so its
    # `Weapons` means "publishes into Weapons A-Z", not "sits on the weapons shelf". Those
    # coincide often enough to have been mistaken for each other and not always: of 14,984
    # entries whose topic said Weapons, only 1,191 were typed as a weapon and 966 were vehicles.
    #
    # THE FALLBACK IS NOT TIDINESS, IT IS THE MIGRATION. `subroom` is populated on a minority of
    # entries today and fills in as the catalogue passes re-run. Reading it alone would SHRINK
    # every finer room in the graph the moment this landed, which is a regression dressed as a
    # correction; reading it first and falling back keeps today's rooms and improves them as the
    # field arrives. When coverage is complete the fallback can go, and that is a measurement
    # somebody should take rather than a date somebody should pick.
    #
    # Both are checked against the parent they claim to sit inside, exactly as before: a shelf
    # that names the wrong room is not a finer grain, it is a fault, and it opens nothing.
    sub = (entry or {}).get("subroom")
    sub = sub.strip() if isinstance(sub, str) and sub.strip() else None
    if sub and sub not in ("none", "unclassified") and SUBROOM_PARENT.get(sub) == coarse:
        return (coarse, sub)
    if short in FINER and FINER[short] == coarse:
        return (coarse, short)
    return (coarse,)


def canonical_category(entry):
    """The coarsest room an entry belongs to. -> str or None. The `by_category` key."""
    path = category_path(entry)
    return path[0] if path else None


def survey(records=None):
    """Read the corpus once. -> (code_of_source, categories_of_source, entries_of_source).

    `records` is an injection point for the drill: a list of record dicts stands in for the
    corpus so a net can drive this against a fixture without touching data/records.
    """
    if records is None:
        import weave_index as WI
        records = WI.load_records()
    code_of, cats_of, n_of = {}, {}, {}
    for rec in records:
        src = (rec or {}).get("source")
        if not src:
            continue
        entries = rec.get("entries") or []
        code_of[src] = ADDR.spine_code_for(src)
        n_of[src] = len(entries)
        cats = collections.Counter()
        for e in entries:
            # THE WHOLE PATH IS THE KEY, so two entries cohort identically only when the
            # catalogue says the same thing about both. Every ROOM on the path is also
            # counted separately, so `cats_at_code` knows a source holds both
            # "Vessels & Things" and "Weapons" and a cohort can match at either level.
            path = category_path(e)
            if path:
                cats[path] += 1
        cats_of[src] = cats
    return code_of, cats_of, n_of


def build(records=None):
    """Derive the T1/T2 graph. PURE: reads the corpus, writes nothing. -> dict.

    Runnable without the Step 4 ratification ON PURPOSE. The gate holds the WRITE and the CLI,
    because what the owner ratifies is the pass landing its artifact -- but a module nobody can
    exercise until the gate opens is a module whose first run is also its first test, and this
    project does not ship those. The drill drives this function against fixtures.
    """
    code_of, cats_of, n_of = survey(records)
    known = {c for c in code_of.values() if c and c != UNADDRESSED}
    # THE ANNEX JOINS THE ADDRESS SPACE (order d57a66d25b11). Widening `known` can only ever let
    # MORE addresses resolve, so T1 and T2 are untouched by this: both point at source codes,
    # which were already in the set. What it changes is that a T3 to `VIII.9` now has somewhere
    # to land instead of being refused as dangling.
    known |= annex_codes()
    known |= law_codes()
    joined = annex_join()

    # Which categories does each ADDRESS hold? A volume code can be shared by several sources
    # (II.L.7 holds a dozen D&D titles), so the cohort question is asked of the address, not of
    # the source: "does that sibling volume contain anything of this kind?"
    # Which ROOMS does each address hold? Flattened from the paths, so a code whose
    # entries are labelled `Weapons` holds both "Weapons" and its parent
    # "Vessels & Things", and a cohort can match at whichever level both sides support.
    cats_at_code = collections.defaultdict(set)
    for src, code in code_of.items():
        if code in known:
            for path in cats_of.get(src, ()):
                cats_at_code[code] |= set(path)

    siblings = collections.defaultdict(set)
    for code in known:
        p = cohort_family(code)
        if p:
            siblings[p].add(code)

    out, refused = {}, []
    for src, code in sorted(code_of.items()):
        if code not in known:
            # NOT SILENTLY DROPPED. An unaddressed source cannot be threaded -- there is no
            # address to thread to or from -- and that is a curatorial gap for a person, so it
            # is recorded in the artifact rather than omitted from it.
            refused.append({"source": src, "why": "source has no resolvable spine code",
                            "code": code, "entries": n_of.get(src, 0)})
            continue
        home = edge(code, "T1", "home volume", code, known)
        cohort = {}
        for path in sorted(cats_of.get(src, ())):
            # A sibling qualifies on ANY room of the path, and the edge is recorded at
            # the FINEST room the two share -- so a weapon threads to another volume's
            # `Weapons` where that volume is labelled, and only falls back to
            # `Vessels & Things` where nobody has said which of its vessels are weapons.
            # Claiming the finer relation against an unlabelled volume would be inventing
            # knowledge; refusing the coarse one would be denying a relation on absent
            # data. Neither is allowed, so it matches at the level actually shared.
            sibs = []
            for s_ in sorted(siblings.get(cohort_family(code), ())):
                if s_ == code:
                    continue
                shared = [room for room in path if room in cats_at_code[s_]]
                if shared:
                    sibs.append((s_, shared[-1]))
            # UNCAPPED. If a cohort becomes forty the entry carries forty (Hard Rule 0).
            #
            # THE NUMBER IN THIS COMMENT WAS WRONG AND IS NOW RIGHT BY ACCIDENT, which is
            # worth saying rather than quietly leaving correct. It read "ten siblings is
            # the measured worst case"; when order eb74d9cd9bae checked it the true
            # maximum was NINE. The bare-Set ruling of 2026-08-31 then raised it to ten.
            # A claim that drifts back into truth is still a claim nobody measured, so
            # here is the whole distribution instead of a single number -- cohort sizes
            # over the live graph, measured after the ruling:
            #   0 x170  1 x49  2 x66  3 x74  4 x109  5 x112  6 x166  7 x213  8 x56
            #   9 x17  10 x53
            cohort[_key(path)] = [
                edge(s_, "T2",
                     "sibling volume under %s also holding %s" % (cohort_family(code), room),
                     code, known)
                for s_, room in sibs]
        # T3 -- THE CHRONICLE JOIN (Phase 4.3, §7G). Per SOURCE, not per category: the
        # charter places a source's HISTORY in a Canon, and that is true of every entry the
        # source holds regardless of which room it sits in. Uncapped: Warhammer 40,000 earns
        # two Canons and carries two; a source the Annex never names carries none, and that
        # empty list is a fact about the Annex rather than a gap in the pass.
        event = [edge(e["to"], "T3", e["why"], code, known)
                 for e in joined.get(src, ())]
        out[src] = {"code": code, "entries": n_of.get(src, 0), "T1": home,
                    "T2": cohort, "T3": event,
                    "by_category": {_key(k): v for k, v in cats_of.get(src, {}).items()}}

    # STAMPED BESIDE `classes`, because it is a fact about the RULE this graph was derived under
    # and not about its contents (order 04c6360636bf). None on every ordinary run; a sentence
    # when the subroom table was unavailable, so a reader of THREADS.json can tell a graph with
    # no finer rooms from a graph built by a pass that could not see them. See
    # SUBROOM_FALLBACK_REASON.
    return {"classes": list(DERIVABLE), "subroom_fallback": SUBROOM_FALLBACK_REASON,
            "sources": out, "unaddressed": refused,
            "counts": counts(out)}


def counts(sources):
    """The edge totals the graph actually expands to. -> dict.

    T1 is one edge per entry, by construction. T2 is, for each source and each category, the
    number of entries in that category times the number of sibling volumes that hold it -- which
    is what `threads_for` will hand back per entry, so the totals here and the expansion agree by
    the same arithmetic rather than by two hand-kept counts.
    """
    t1 = sum(v["entries"] for v in sources.values())
    t2 = 0
    for v in sources.values():
        for key, n in (v.get("by_category") or {}).items():
            t2 += n * len(v["T2"].get(key, ()))
    # T3 RIDES ON EVERY ENTRY OF ITS SOURCE, so it multiplies the same way T1 does -- per
    # source, not per category, because the charter places a SOURCE's history in a Canon.
    # Counted here rather than left out, because the report printed a "total" that would
    # otherwise disagree with what `threads_for` actually hands back, and a total that
    # undercounts the artifact it describes is worse than no total.
    t3 = sum(v["entries"] * len(v.get("T3") or ()) for v in sources.values())
    with_t3 = sum(1 for v in sources.values() if v.get("T3"))
    entries_with_t3 = sum(v["entries"] for v in sources.values() if v.get("T3"))
    return {"sources": len(sources), "entries": t1,
            "T1_edges": t1, "T2_edges": t2, "T3_edges": t3,
            "T3_sources": with_t3, "T3_entries": entries_with_t3,
            "total_edges": t1 + t2 + t3,
            "edges_per_entry": round((t1 + t2 + t3) / t1, 3) if t1 else 0.0}


def threads_for(graph, source, entry):
    """The complete, uncapped thread list for ONE entry. -> [edge]. REFUSES for an unaddressed
    source rather than returning a blank.

    IT USED TO RETURN `[]` HERE, AND CITED A REFUSAL THAT DID NOT EXIST (audit T-4). The old
    docstring said "see `verify`, which treats an empty one as an OPERATOR-level fault" --
    `verify` does no such thing; it appends a string to a list. So an entry in a source with no
    resolvable spine code got a silent empty Threads section, which is precisely §6's "quiet
    one": indistinguishable from "pending" to a reader and from "done" to a checker, and the one
    outcome the plan singles out as an OPERATOR-level refusal rather than a blank.

    LATENT WHEN IT WAS WRITTEN, NOT HARMLESS. `build()` reports zero unaddressed sources today,
    so nothing took this path -- but CLAUDE.md Hard Rule 2 says a source added to the roll ahead
    of the Acquisitions Index is the ORDINARY case, and that is exactly when it would have gone
    live and silently written blanks.

    An entry the graph has no record for is a caller error and refuses the same way, because
    "this source is not in the graph" and "this source has no threads" must not answer alike.
    """
    rec = (graph.get("sources") or {}).get(source)
    if not rec:
        unaddressed = {u["source"] for u in (graph.get("unaddressed") or [])}
        raise ThreadRefused(
            "refusing to hand back a Threads section for %r: %s. STEP4_PLAN.md §6 rules that an "
            "entry with no threads is an OPERATOR-level refusal, not a blank -- a Threads "
            "section that is present but empty reads as 'pending' to a person and as 'done' to a "
            "checker."
            % (source, "the source has no resolvable spine code, so the pass did not run for it"
               if source in unaddressed else "no such source in this graph"))
    out = [dict(rec["T1"])]
    # T3 rides on every entry of the source, for the reason `build` gives: the charter places a
    # SOURCE's history in a Canon. `.get` rather than `[...]` so a graph written before 4.3 --
    # THREADS.json on disk predates it -- still expands instead of raising.
    out.extend(dict(e) for e in (rec.get("T3") or ()))
    # T4 IS DERIVED HERE AND NOT STORED, and that is a structural fact about the class rather
    # than a shortcut. T1, T2 and T3 are constant across every entry sharing a (source, category)
    # -- which is exactly why this file can be stored normalised at kilobytes instead of the
    # ~136 MB an expanded one would take. T4 is NOT: it depends on whether THIS entry asserts a
    # Magnitude, which varies entry by entry. Storing it would force the expanded shape on the
    # whole artifact to carry a field 447 entries in 282,711 actually have.
    #
    # `threads_for` already receives the entry, so the per-entry class is computed at the one
    # place that has the per-entry evidence. Refusals are swallowed to nothing rather than
    # raised: an unreadable LAWS.json means `law_codes()` is empty, `edge()` refuses, and the
    # entry keeps its T1/T2/T3 -- degrading to the previous phase, never to a broken citation.
    if asserts_a_magnitude(entry):
        try:
            out.append(edge(MAGNITUDE_LAW, "T4",
                            "Magnitude %s is a claim under the Registry of Magnitudes; the axes, "
                            "weights and Attestation grades that define the bands are X.1"
                            % str((entry or {}).get("magnitude")).strip(),
                            rec["code"], set(_known_for_t4())))
        except ThreadRefused:
            silence.note("threads.py:t4-refused")
    
    # Looked up by the entry's whole path, so a labelled weapon gets the weapon cohort
    # and an unlabelled vessel gets the vessel cohort -- the two are different rooms and
    # the store keeps them apart.
    key = _key(category_path(entry))
    if key:
        out.extend(dict(e) for e in rec["T2"].get(key, ()))
    return out


def verify(graph):
    """Check a graph against its own promises. -> [problem].

    EVERY ONE OF THESE WAS A TAUTOLOGY WHEN IT WAS WRITTEN (audit T-3), and the reason is worth
    keeping: the checks were run against the object `build()` had just returned, where each
    property holds BY CONSTRUCTION. `if not edges` tested a list literal with one element
    concatenated to another list -- no input could make it true. Every edge came from `edge()`,
    which refuses a bad class and an unresolvable address before returning, so checks 2 and 3
    could not fire either. And `T1["to"] != code` compared one local variable with itself. Four
    checks, zero reachable failures, feeding a `REFUSING TO WRITE` branch in `main()` that was
    therefore dead code -- in a module whose whole subject is refusals.

    SO IT IS NOW POINTED AT THE ONE GRAPH THAT CAN ACTUALLY BE WRONG: the round-tripped one.
    `main()` serialises, parses back, and verifies THAT -- so these test the artifact a reader
    will get rather than the object the builder still holds, and a serialisation that drops or
    mangles a field is caught before the file lands. That also makes the function useful to a
    future reader of `THREADS.json` on disk, which is the caller it was really written for and
    did not have.

    The emptiness check is repaired rather than kept: it now asks the question §6 actually poses
    -- does every (source, category) the record carries expand to a non-empty Threads section --
    which is the property `threads_for` delivers and the one that can genuinely fail.
    """
    problems = []
    sources = graph.get("sources") or {}
    if not sources:
        return ["the graph carries no sources at all"]
    known = {rec.get("code") for rec in sources.values() if isinstance(rec, dict)}
    for src, rec in sources.items():
        if not isinstance(rec, dict) or "T1" not in rec or "T2" not in rec:
            problems.append("%s: record is not a thread record (%r)" % (src, type(rec).__name__))
            continue
        t1 = rec.get("T1") or {}
        edges = [t1] + [e for lst in (rec.get("T2") or {}).values() for e in lst]
        for e in edges:
            if not isinstance(e, dict):
                problems.append("%s: an edge is not an edge (%r)" % (src, type(e).__name__))
                continue
            if e.get("class") not in DERIVABLE:
                problems.append("%s: carries a %r edge, which this pass may not derive"
                                % (src, e.get("class")))
            if e.get("to") not in known:
                problems.append("%s: thread points at %r, which is not a live address"
                                % (src, e.get("to")))
        if t1.get("to") != rec.get("code"):
            problems.append("%s: T1 does not point at the source's own volume (%r != %r)"
                            % (src, t1.get("to"), rec.get("code")))
        # §6's "quiet one" -- an empty Threads section -- is NOT checked here, and that is a
        # deliberate omission rather than an oversight. A first attempt at repairing this
        # function put the check back as "every category expands to something", and it was a
        # tautology for the second time: `threads_for` prepends T1 unconditionally, so the
        # expansion is non-empty for any source present in the graph. The only way to reach an
        # empty one is a record with no usable T1, which the shape check at the top of this loop
        # already catches by name.
        #
        # So the property holds by construction and the REFUSAL lives where the caller is:
        # `threads_for` raises `ThreadRefused` for a source the graph has no record for. Writing
        # a third version of a check that cannot fire would be the defect this whole module is
        # supposed to be careful about, restated as diligence.
    return problems


def recorded_pairs(graph):
    """The directed source→source relation `thread_integrity.classify(recorded=...)` wants.

    Phase 4.2 wires the verifier to this. Threads are emitted per ADDRESS, and the verifier
    reasons about SOURCES, so a thread from source A to a code that source B also occupies is a
    recorded direction A→B.
    """
    sources = graph.get("sources") or {}
    at_code = collections.defaultdict(set)
    for src, rec in sources.items():
        at_code[rec["code"]].add(src)
    out = set()
    for src, rec in sources.items():
        for lst in rec["T2"].values():
            for e in lst:
                for other in at_code.get(e["to"], ()):
                    if other != src:
                        out.add((src, other))
    return out


def main():
    # THIS CLI COULD NOT FINISH ON THIS MACHINE, AND NOTHING NOTICED (audit T-1).
    # One `\u2192` in a print killed it: `sys.stdout.encoding` is cp1252 here under both
    # interpreters, and this is the only module in src/ that printed that character. It
    # survived every test because a hand-run always set PYTHONIOENCODING=utf-8, and no
    # parent process sets it for this module -- `allsweep`, `foreman`, `overwatch`,
    # `overnight`, `autostart` and `local_agent` all pass it to THEIR children, and none
    # of them launches this. Worse, the crash sat BEFORE the ratification gate, so on the
    # day `step4_enabled` was set the pass would have derived the whole graph, died on a
    # print, and written nothing.
    #
    # Fixed twice over, because either alone is a coincidence away from coming back: the
    # arrow is gone, and stdout is reconfigured the way `handbuilt.py` does it. A drill
    # net now RUNS this CLI as a subprocess with PYTHONIOENCODING unset and requires
    # rc=0 -- the nine nets that existed all asked the parse tree or the gate, and a net
    # green on the source of a CLI that cannot finish is the exact shape this project
    # calls a check that cannot fail.
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass        # an older stdout without reconfigure is not a reason to refuse to run
    ap = argparse.ArgumentParser(description="Step 4 Phase 4.1 - derive the T1/T2 thread graph")
    ap.add_argument("--dry-run", action="store_true",
                    help="derive and report, write nothing (does not need the ratification)")
    a = ap.parse_args()

    # THE PLANT-WIDE INTERLOCK, first, like every other entry point (Hard Rule -1). Fails closed:
    # a job that cannot ask whether the library is halted has no business starting.
    try:
        import escalation as _ESC
    except ImportError as gone:
        raise SystemExit("REFUSING TO START: the escalation chain could not be imported (%s), so "
                         "the halt cannot be read. Hard Rule -1." % gone) from gone
    _ESC.assert_clear(os.path.basename(__file__))

    graph = build()
    # VERIFIED AFTER A ROUND TRIP, not on the object build() just returned -- see
    # `verify`. Checking the in-memory graph proved only that the builder had just done
    # what it had just done; checking the parsed-back copy tests the artifact a reader
    # actually gets, and catches a serialisation that drops or mangles a field before
    # the file lands rather than after.
    problems = verify(json.loads(json.dumps(graph)))
    n_src = len(graph["sources"])
    c = graph["counts"]

    print("THREADS — Step 4, Phases 4.1 and 4.3 (T1 home + T2 cohort + T3 Chronicle join)")
    print("=" * 78)
    if SUBROOM_FALLBACK_REASON:
        # ON THE CONSOLE, ABOVE THE COUNTS IT EXPLAINS (order 04c6360636bf). The counts below
        # would be internally consistent and simply smaller, which is the one thing a reader
        # cannot detect from the numbers themselves.
        print("   !! SUBROOMS UNAVAILABLE: " + SUBROOM_FALLBACK_REASON)
    print("   addressed sources        : %d" % n_src)
    print("   entries behind them      : %s" % format(c["entries"], ","))
    print("   T1 edges (home)          : %s" % format(c["T1_edges"], ","))
    print("   T2 edges (cohort)        : %s" % format(c["T2_edges"], ","))
    # NAMED WITH ITS REACH, not just its total. A T3 count alone reads as tiny (29 source-level
    # edges); what a reader needs is how much of the corpus the Annex actually claims, and how
    # much it does not -- the silence is the more interesting half and it is not a gap.
    print("   T3 edges (Chronicle join): %s   across %d source(s), %s entries (%.1f%% of the corpus)"
          % (format(c["T3_edges"], ","), c["T3_sources"], format(c["T3_entries"], ","),
             100.0 * c["T3_entries"] / c["entries"] if c["entries"] else 0.0))
    print("   total                    : %s  (%.2f per entry)"
          % (format(c["total_edges"], ","), c["edges_per_entry"]))
    # T4 IS COUNTED BY WALKING THE RECORDS, not read off the graph, because it is derived per
    # entry at expansion and deliberately not stored -- see `threads_for`. Reported anyway: a
    # report that omits a class the pass emits is a report that disagrees with the artifact, and
    # that is exactly the defect the T3 line was added to fix one ruling ago.
    try:
        import weave_index as _WI
        _t4 = sum(1 for _r in _WI.load_records()
                  for _e in ((_r or {}).get("entries") or []) if asserts_a_magnitude(_e))
        print("   T4 edges (Law citation) : %s   on the entries that assert a Magnitude band; "
              "the rest make no claim a Law governs" % format(_t4, ","))
    except Exception:
        silence.note("threads.py:t4-count")
        print("   T4 edges (Law citation) : could not be counted (records unreadable); "
              "the class is still emitted at expansion")
    print("   sources with NO address  : %d" % len(graph["unaddressed"]))
    # A SOURCE WITH NO COHORT IS REPORTED, because a reader cannot otherwise tell "this
    # volume has no siblings" from "the cohort pass did not reach it" (order
    # a8864d2361de). That is section 6's quiet one a level up: an empty cohort is a fact
    # about the shelf for a childless Set, and would be a defect for anything else.
    _no_cohort = sorted(src for src, rec in graph["sources"].items()
                        if not any(rec["T2"].values()))
    print("   sources with NO cohort   : %d (their entries carry the home volume alone)"
          % len(_no_cohort))
    for u in graph["unaddressed"]:
        print("      %s (%s entries) — %s" % (u["source"], format(u["entries"], ","), u["why"]))
    print("   recorded source->source directions: %s" % format(len(recorded_pairs(graph)), ","))
    if problems:
        print()
        print("REFUSING TO WRITE — the derived graph breaks its own promises:")
        for p in problems:
            print("   " + p)
        return 1

    # THE RATIFICATION GATE. Everything above is derivation and reporting; only the WRITE is the
    # pass. `--dry-run` exists so this module can be exercised and reviewed before the owner
    # rules, which is the whole point of building it ahead of the ruling.
    import prose_gate as PG
    ok, why = PG.step4_gate_open()
    if a.dry_run:
        print()
        print("DRY RUN — nothing written. The ratification gate says: %s" % ("OPEN" if ok else why))
        return 0
    if not ok:
        print()
        print("REFUSING TO WRITE %s" % OUT)
        print("   " + why)
        print("   Setting step4_enabled asserts three things at once: the plan has been read, "
              "its §7 rulings are answered, and Phase 4.0 is done. Nothing in the automation "
              "may flip it.")
        return 3

    landed = silence.write_json(OUT, graph, indent=1)
    if not landed:
        print("WRITE DENIED -> %s: nothing landed." % OUT)
        return 1
    print()
    print("wrote " + OUT)
    return 0


if __name__ == "__main__":
    sys.exit(main())
