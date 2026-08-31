#!/usr/bin/env python3
"""
THREADS — Step 4, Phase 4.1: the T1/T2 entanglement pass.

WHAT A THREAD IS, and the whole design follows from taking the charter literally (Part Seven,
via STEP4_PLAN.md §1): a Thread is a CITATION, not an opinion. It resolves to an ADDRESS — a
spine code, a shelfmark, or an Annex event-code — and a thread that resolves to nothing is not a
weak thread, it is a BROKEN one. So entanglement is a referencing problem over an address space
that already exists, not a semantic-similarity problem over 282,822 entities. Nothing here pairs
entities against each other; each entry cites a handful of addresses, the way a footnote does.

THE TWO CLASSES THIS MODULE EMITS, and only these two:

  T1 HOME    the entry's own volume, from `address.spine_code_for(source)`. Zero judgment,
             100% coverage, cannot be wrong if the addressing is right. This alone gives every
             entry in the library a non-empty, correct Threads section.
  T2 COHORT  sibling volumes under a shared parent in the Collection→Set→Series tree, filtered
             to those the entry's own record gives a reason to name.

DELIBERATELY NOT EMITTED:

  T3 EVENT   the Chronicle join. Phase 4.3, and NOT AUTHORISED by the §7E ruling, which scopes
             the pass to "PHASE 4.0 AND 4.1 ONLY, then stop and look".
  T4 LAW     per-claim, so it belongs with generation.
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

HARD RULE 0 APPLIES IN FULL. There is no `[:n]` anywhere in this pass. If an entry has forty
lawful threads it carries forty. A thread list truncated at five silently decides the sixth
relation does not exist, which is the precise shape the rule exists to forbid.
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

# The classes this module is permitted to derive. T3/T4 are later phases; T5 is owner-authored
# only and is not in this tuple BY RULING, not by oversight -- see `edge()`.
DERIVABLE = ("T1", "T2")

# `spine_code_for` never raises; it returns this when the Acquisitions Index cannot place a
# source. An UNASSIGNED code is not an address, so it is never threaded to and never threaded
# from -- emitting one would be exactly the dangling thread §6 forbids.
UNADDRESSED = "UNASSIGNED"


class ThreadRefused(Exception):
    """A thread this module is not permitted to derive, or one that resolves to nothing."""


def parent_of(code):
    """The Collection.Set a volume code sits under. -> str or None.

    `II.A.3` -> `II.A`. A bare `II.P` (a Set with no Series) has no parent ABOVE it that this
    pass threads within, so it returns None rather than `II`: cohorting at Collection level
    would put every D&D supplement in a room with every anime, which is not what "sibling
    volumes under a shared parent" means.
    """
    if not code or code == UNADDRESSED:
        return None
    parts = [p for p in str(code).split(".") if p]
    return ".".join(parts[:2]) if len(parts) >= 3 else None


def _resolves(code, known_codes):
    """Is this an address that exists RIGHT NOW? -> bool. The anti-dangling test."""
    return bool(code) and code != UNADDRESSED and code in known_codes


def edge(to, cls, why, frm, known_codes):
    """Build one thread edge, or refuse. -> dict.

    TWO REFUSALS, AND THEY ARE THE POINT OF THE FUNCTION:

    1. A class this pass may not derive. T5 is the Great Identifications and the §7B ruling is
       that they are owner-authored only -- never derived, never inferred, never emitted by
       `threads.py`. T3 and T4 are unauthorised phases. Refusing here rather than at the call
       site means a future caller cannot reach the wrong class by a new path.
    2. An address that does not resolve. §6: emit an address only if it resolves NOW. A thread
       that points at nothing is broken, and building it and hoping the verifier catches it
       later is the wrong order.
    """
    if cls not in DERIVABLE:
        raise ThreadRefused(
            "class %r may not be derived by threads.py. T1/T2 are this phase; T3 (the Chronicle "
            "join) and T4 (Law citations) are later phases and unauthorised by STEP4_PLAN.md "
            "§7E; T5 (the Great Identifications) is OWNER-AUTHORED ONLY by the §7B ruling and "
            "must never be machine-derived." % (cls,))
    if not _resolves(to, known_codes):
        raise ThreadRefused(
            "refusing to emit a thread to %r, which does not resolve to a live address. A thread "
            "that resolves to nothing is not a weak thread, it is a broken one "
            "(STEP4_PLAN.md §1, §6)." % (to,))
    return {"to": to, "class": cls, "why": why, "from": frm}


def canonical_category(entry):
    """The catalogue category an entry belongs to, in ONE vocabulary. -> str or None.

    THE KEY SPACE WAS TWO VOCABULARIES AND IT COST ~17,000 LAWFUL COHORT THREADS (audit T-2).
    This took `topic` first and `category` second and asserted in its own docstring that "both
    are present on every entry measured" -- which was measured on ONE record. Across the live
    corpus: `category` is on 100% of 282,822 entries, `topic` on 49.1%. Cohort membership is
    exact string equality, so `"Persons"` and
    `"Persons (named individual characters, real or fictional)"` were two different rooms, and a
    sibling volume holding the same catalogue category under the other spelling never cohorted
    in either direction. Nothing failed; the artifact just silently decided those relations did
    not exist, which is precisely the shape Hard Rule 0 forbids.

    THE FOLD IS THE LONG FORM'S HEAD WORD, AND NOTHING ELSE. `Persons (named individual
    characters, real or fictional)` -> `Persons`, which is exactly the short form. That is a
    SPELLING reconciliation and it is safe.

    `category` IS PREFERRED BECAUSE IT IS THE AUTHORITATIVE FIELD, not merely the present one: it
    is on 100% of entries and carries exactly the seven catalogue categories, while `topic` is on
    49.1% and carries nine values. The extra two are `Weapons`, `Relics` and `Wars` (against
    `Media`, which is both) -- finer RE-CUTS rather than synonyms.

    SO THOSE RE-CUTS DO LAND INSIDE THEIR PARENT CATEGORY, AND THAT IS DERIVED, NOT DECIDED HERE.
    An entry whose `topic` is `Weapons` carries `category: Vessels & Things (...)`, so it cohorts
    as a Vessel because THE RECORD SAYS SO -- this function never asserts an equivalence of its
    own. Measured over the live corpus: `Weapons` -> `Vessels & Things` (14,214 entries),
    `Relics` -> `Vessels & Things` (2,568), `Wars` -> `Events` (263). The result is one vocabulary
    of exactly seven keys.

    WHETHER SEVEN IS THE RIGHT GRAIN IS A CURATORIAL QUESTION AND IS FILED, NOT ANSWERED. Cohorting
    at `Vessels & Things` puts a weapon in a room with a spaceship; a finer grain would mean fewer
    and more meaningful cohort threads. This module derives, it does not rule.

    The cross-tab also shows the two fields genuinely DISAGREEING in places -- 781 entries carry
    `topic: Persons` under `category: Places & Locations`, and 1,361 carry `topic: Media` under
    `category: Vessels & Things`. Those are catalogue-level inconsistencies, not threading ones,
    and they are reported in the same order rather than papered over here.
    """
    long_form = (entry or {}).get("category")
    if isinstance(long_form, str) and long_form.strip():
        return long_form.split("(")[0].strip() or long_form.strip()
    short = (entry or {}).get("topic")
    if isinstance(short, str) and short.strip():
        return short.strip()
    return None


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
            c = canonical_category(e)
            if c:
                cats[c] += 1
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

    # Which categories does each ADDRESS hold? A volume code can be shared by several sources
    # (II.L.7 holds a dozen D&D titles), so the cohort question is asked of the address, not of
    # the source: "does that sibling volume contain anything of this kind?"
    cats_at_code = collections.defaultdict(set)
    for src, code in code_of.items():
        if code in known:
            cats_at_code[code] |= set(cats_of.get(src, ()))

    siblings = collections.defaultdict(set)
    for code in known:
        p = parent_of(code)
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
        for cat in sorted(cats_of.get(src, ())):
            sibs = sorted(s for s in siblings.get(parent_of(code), ()) if s != code
                          and cat in cats_at_code[s])
            # UNCAPPED. Ten siblings is the measured worst case today; if it becomes forty, the
            # entry carries forty (Hard Rule 0).
            cohort[cat] = [edge(s, "T2",
                                "sibling volume under %s also holding %s" % (parent_of(code), cat),
                                code, known)
                           for s in sibs]
        out[src] = {"code": code, "entries": n_of.get(src, 0), "T1": home,
                    "T2": cohort, "by_category": dict(cats_of.get(src, {}))}

    return {"classes": list(DERIVABLE), "sources": out, "unaddressed": refused,
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
        for cat, n in (v.get("by_category") or {}).items():
            t2 += n * len(v["T2"].get(cat, ()))
    return {"sources": len(sources), "entries": t1,
            "T1_edges": t1, "T2_edges": t2, "total_edges": t1 + t2,
            "edges_per_entry": round((t1 + t2) / t1, 3) if t1 else 0.0}


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
    cat = canonical_category(entry)
    if cat:
        out.extend(dict(e) for e in rec["T2"].get(cat, ()))
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


def recorded_pairs(graph, code_of=None):
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

    print("THREADS — Step 4 Phase 4.1 (T1 home + T2 cohort)")
    print("=" * 78)
    print("   addressed sources        : %d" % n_src)
    print("   entries behind them      : %s" % format(c["entries"], ","))
    print("   T1 edges (home)          : %s" % format(c["T1_edges"], ","))
    print("   T2 edges (cohort)        : %s" % format(c["T2_edges"], ","))
    print("   total                    : %s  (%.2f per entry)"
          % (format(c["total_edges"], ","), c["edges_per_entry"]))
    print("   sources with NO address  : %d" % len(graph["unaddressed"]))
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
