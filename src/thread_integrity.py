#!/usr/bin/env python3
"""
THREAD INTEGRITY — does the omniverse hold together when you walk it?

WHY THIS IS THE COHERENCE TEST
------------------------------
A library feels like one place when following a cross-reference pays off: you walk from an entry
to the thing it names, and the far end knows you are coming. It feels like a pile of files when
the thread leads somewhere that has never heard of where you came from.

The Panscriptum has the notation -- Threads (⌁) carry spine codes, shelfmarks and event-codes, and
the Doctrine of Derivation requires *every factual claim to cite a Law or a Deed*. What it has
never had is anything that CHECKS them. A thread that points at nothing, or points at something
that does not point back, is exactly the failure the Doctrine was written to prevent, and nothing
in the pipeline would notice.

THE ASYMMETRY IS THE INTERESTING PART
-------------------------------------
Naive reciprocity is wrong here, and this is where the charter is better than a normal
cross-reference checker. Some one-way threads are CORRECT:

  * The Aperture Doctrine (I.9) mandates it. A local entry carries a Position Paragraph naming
    the wider flows; the wider flows do not name the cloak. "The smith does not know about the
    Reapers. The entry should know that he does not know."
  * Propagation forbids it. If shelf B sits 1,126 years away and the event is 300 years old, B
    CANNOT thread back -- the news has not arrived. A reciprocal link there would be the error.

So the checker classifies rather than scolds:
    RECIPROCAL   both ends know each other -- the omniverse is joined here
    ASYMMETRIC-LAWFUL   one-way, and aperture or propagation explains why
    ASYMMETRIC-SUSPECT  one-way with no excuse -- a real hole
    DANGLING     points at nothing that exists
"""
import argparse
import collections
import json
import os
import sys

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Imported so a swallowed failure is COUNTED. `silence.py` is a battery verifier exactly
# so that swallows are countable; this module had one that never reached
# state/failures.json (order ae2afc775228).
import silence          # noqa: E402

# ------------------------------------------------------ PHASE 4.2 (STEP4_PLAN.md §7F, 2026-09-02)
#
# Until this date every caller passed `recorded=None` and this module printed, unconditionally,
# "no directed thread graph exists yet". That sentence had been false since 2026-09-01 11:34,
# when Phase 4.1 emitted `data/THREADS.json` -- 210 sources, 1,508,653 threads -- and the
# verifier written to read it had simply never been taught where it was. 100% of 5,782 source
# pairs read as IMPLIED-UNRECORDED against 1.5M recorded threads. Phase 4.1's own deliverable
# says "verify with thread_integrity.py, which finally has its graph"; this is that wiring, and
# the plan's build order assigns it to 4.2.
#
# TWO DIFFERENT THINGS ARE CALLED DANGLING, and 4.2 gates on both:
#   * `classify()`'s DANGLING -- weave drift: an implied pair whose every shared entity has gone
#     from the live records. Computed against `ents`, unchanged here.
#   * the plan's DANGLING (§1, §6, §8) -- a thread that resolves to NO ADDRESS. That is the
#     failure the whole design claims to prevent by construction, and `load_thread_graph`
#     re-checks it afterwards, per §8: "DANGLING = 0 is a release gate, not a metric."
THREADS = os.path.join(HERE, "data", "THREADS.json")
FLOOR = os.path.join(HERE, "state", "THREAD_INTEGRITY_FLOOR.json")
SPINE_CODES = os.path.join(HERE, "data", "CHARTER_SPINE_CODES.json")


class ThreadGraphUnreadable(RuntimeError):
    """`data/THREADS.json` EXISTS and cannot be read as a graph.

    OWNER-level by STEP4_PLAN.md §8, "because every entry in the library cites it". An absent
    file is a different thing -- the pre-4.1 state -- and is not this."""


def _charter_codes():
    """Every spine code the owner-extended Acquisitions Index knows. -> set of str.

    A childless Set is still an address a thread may lawfully point at, so the address space is
    the charter index UNION the codes the graph itself assigns; a code in neither is nothing."""
    try:
        with open(SPINE_CODES, encoding="utf-8") as f:
            raw = json.load(f)
    except FileNotFoundError:
        return set()
    except Exception:
        silence.note("thread_integrity.py:spine-codes-unreadable")
        return set()
    out = set()
    vals = raw.values() if isinstance(raw, dict) else (raw if isinstance(raw, list) else [])
    for v in vals:
        if isinstance(v, str):
            out.add(v)
        elif isinstance(v, dict):
            for k in ("code", "spine", "spine_code"):
                if isinstance(v.get(k), str):
                    out.add(v[k])
    return out


def load_thread_graph(path=None):
    """Read Phase 4.1's graph. -> None (no graph yet), or (recorded, unresolvable, meta).

      recorded      {(source_a, source_b), ...} -- the DIRECTED graph `classify(recorded=)`
                    wants, in ITS key space (source names). THREADS.json is keyed source ->
                    spine CODE, and a code is an address a whole Set of sources can share, so
                    an edge from a to code C records a -> b for every source b filed under C
                    other than a itself. That is what "the thread resolves" means at source
                    level: b is a volume a's reader can actually open.
      unresolvable  [(source, class, to), ...] -- every thread whose target is an address
                    that EXISTS NOWHERE: not in the charter index, not assigned to any source.
                    The plan's DANGLING. Uncapped (Hard Rule 0).
      meta          the file's own `counts` plus what was derived here.

    RAISES `ThreadGraphUnreadable` when the file exists and is not a graph -- not JSON, not a
    mapping, no `sources`, or a source row that is not a mapping with a code. That is deliberate
    and it is the fail-closed direction: an unreadable graph must never come back as an empty
    one, because an empty graph verifies perfectly. Returns None only when the file is ABSENT.
    """
    p = path or THREADS
    try:
        with open(p, encoding="utf-8") as f:
            doc = json.load(f)
    except FileNotFoundError:
        return None
    except Exception as exc:
        raise ThreadGraphUnreadable("%s: %s: %s" % (p, type(exc).__name__, exc))
    if not isinstance(doc, dict) or not isinstance(doc.get("sources"), dict):
        raise ThreadGraphUnreadable("%s is not a thread graph: no `sources` mapping" % p)
    sources = doc["sources"]
    code_to_sources = collections.defaultdict(list)
    for src, row in sources.items():
        if not isinstance(row, dict) or not isinstance(row.get("code"), str) or not row["code"]:
            raise ThreadGraphUnreadable("%s: source %r has no spine code -- not a graph row" % (p, src))
        code_to_sources[row["code"]].append(src)
    addresses = _charter_codes() | set(code_to_sources)

    recorded = set()
    unresolvable = []
    edges = 0
    for src, row in sources.items():
        targets = []
        t1 = row.get("T1")
        if isinstance(t1, dict):
            targets.append(("T1", t1.get("to")))
        for cat, lst in (row.get("T2") or {}).items():
            for e in (lst or []):
                if isinstance(e, dict):
                    targets.append(("T2", e.get("to")))
        for cls, to in targets:
            edges += 1
            if not isinstance(to, str) or to not in addresses:
                unresolvable.append((src, cls, to))
                continue
            for b in code_to_sources.get(to, ()):
                if b != src:
                    recorded.add((src, b))
    meta = dict(doc.get("counts") or {})
    meta.update({"path": p, "sources": len(sources), "source_level_edges": edges,
                 "recorded_directions": len(recorded), "addresses": len(addresses)})
    return recorded, unresolvable, meta


def _floor_verdict(measured, path=None):
    """The ASYMMETRIC-SUSPECT regression floor. -> (state, measured, bar).

    RULING C AND PHASE 4.2, RECONCILED. §7C says one-way threads are lawful by default and
    ASYMMETRIC is reported as a count and a list, NEVER failed, through 4.2. §4's Phase 4.2 says
    ASYMMETRIC-SUSPECT "gets a floor". Both hold at once when the floor is a REGRESSION gate:
    asymmetry that exists never fails; asymmetry that GROWS past the recorded baseline does. The
    first measurement records the baseline; a lower measurement ratchets it down; it is never
    raised by anything in the automation -- §8's rule that no phase may lower a floor to go
    green, read in the direction this floor points.

      baseline   no floor on record; this measurement becomes it
      held       measured == bar
      ratcheted  measured <  bar; bar lowered to measured
      REGRESSED  measured >  bar (fails)
      UNREADABLE the floor file exists and cannot be read (fails closed: cannot judge)
    """
    p = path or FLOOR
    try:
        with open(p, encoding="utf-8") as f:
            cur = json.load(f)
        bar = int(cur["asymmetric_suspect_max"])
    except FileNotFoundError:
        silence.write_json(p, {"asymmetric_suspect_max": int(measured),
                               "set_at": __import__("time").time(),
                               "by": "thread_integrity: first measurement (Phase 4.2 baseline)"},
                           indent=1)
        return "baseline", measured, measured
    except Exception:
        silence.note("thread_integrity.py:floor-unreadable")
        return "UNREADABLE", measured, None
    if measured > bar:
        return "REGRESSED", measured, bar
    if measured < bar:
        silence.write_json(p, {"asymmetric_suspect_max": int(measured),
                               "set_at": __import__("time").time(),
                               "by": "thread_integrity: ratcheted down from %d" % bar,
                               "was": bar},
                           indent=1)
        return "ratcheted", measured, bar
    return "held", measured, bar


def load_entities():
    """Every catalogued entity, by source, with its normalised key.

    THE KEY SPACE IS THE WHOLE POINT (BUGS d8719255faab, 2026-08-26). These keys are compared
    against `WEAVE_CANDIDATES.json`, whose keys are produced by `weave_index.norm`. This
    function used to fold by hand -- lowercase, drop parentheticals, strip non-alphanumerics --
    which is NOT that fold, and so the comparison was between two different key spaces. Every
    name the two folds disagreed on read as an entity that had vanished from its source, and
    got reported as a broken obligation when nothing was broken:

      * no accent folding      "Amelie" vs "amlie" -- `norm` does NFKD first
      * no title stripping     "The Ordning", "St Patrick's Day" keep their article/honorific
      * no @continuity suffix  0 such keys today, but 100% wrong the first time one appears

    Measured against live data before the fix: 24 of 2,775 candidate keys could not be produced
    by the hand fold at all, and 418 of 592 DANGLING pairs were pure artifacts of it.

    The correct fix was rejected once on cost -- `norm` was 13.0 ms/call, so ~43 min over this
    corpus. That was the `_records_sig` defect (BUGS 31715d371415), now fixed; `norm` is
    0.012 ms/call and the designation set is hoisted here exactly once for the whole pass.
    """
    import weave_index as WI
    ents = collections.defaultdict(set)
    names = {}
    known = WI.designations()
    for rec in WI.load_records():
        for e in rec.get("entries", []):
            k = WI.norm(e.get("name"), known)
            if k:
                ents[rec["source"]].add(k)
                names.setdefault(k, e.get("name"))
    return ents, names


def implied_threads(candidates_path=None):
    """Threads implied by shared entities: if two sources attest one entity, each should thread
    to the other through it. This is the weave's output read as an obligation."""
    path = candidates_path or os.path.join(HERE, "data/WEAVE_CANDIDATES.json")
    with open(path, encoding="utf-8") as f:
        cand = json.load(f)
    pairs = collections.defaultdict(set)
    for key, hits in cand.items():
        srcs = sorted({h["source"] for h in hits})
        for i in range(len(srcs)):
            for j in range(len(srcs)):
                if i != j:
                    pairs[(srcs[i], srcs[j])].add(key)
    return pairs


def classify(pairs, distance_fn=None, event_age_years=300.0, recorded=None, ents=None):
    """Sort threads into the classes -- honestly about which are measurable TODAY.

    THE 2026-08-24 CORRECTION (BUGS m12, owner: FIX IT ALL). `implied_threads` builds its
    pair map SYMMETRICALLY by construction -- both (a,b) and (b,a) exist for every shared
    entity -- so comparing it against itself made every pair RECIPROCAL and left the
    ASYMMETRIC classes structurally unreachable: the module was measuring its own input's
    shape and calling it the omniverse's. Asymmetry is real only against a DIRECTED record
    of which entries actually carry a Thread -- and per Hard Rule 5 that graph does not
    exist until the owner's Step 4 entanglement pass. So:

      recorded=None (today)   implied pairs classify as IMPLIED-UNRECORDED -- obligations
                              awaiting the entanglement pass, counted and listed, never
                              dressed as reciprocity nobody verified. DANGLING and
                              PARTIALLY-DANGLING are computed for real, against the live
                              records: a candidate key whose source no longer holds that
                              entity (weave drift), for all of a pair's shared keys or
                              only some of them.
      recorded={(a,b),...}    the future directed graph. The original four-way
                              classification runs, asymmetry classes and all. RECIPROCAL
                              requires BOTH (a,b) and (b,a); exactly one of them is the
                              asymmetric case and the pair is reported oriented so the first
                              name is the end that records the thread; neither of them is
                              IMPLIED-UNRECORDED, the same class as the recorded=None line
                              above, because a pair no directed edge touches is an unrecorded
                              obligation and not a one-way one.
    """
    out = collections.Counter()
    detail = collections.defaultdict(list)
    seen = set()
    for (a, b), shared in pairs.items():
        if (b, a) in seen or (a, b) in seen:
            continue
        seen.add((a, b))
        if ents is not None:
            gone = [k for k in shared if k not in ents.get(a, ()) or k not in ents.get(b, ())]
            if gone and len(gone) == len(shared):
                out["DANGLING"] += 1
                detail["DANGLING"].append((a, b, len(gone), len(shared)))
                continue
            if gone:
                # BUGS 2b4e0f497aac. Drift was only reported when EVERY shared key had gone,
                # so a pair sharing 100 entities of which 99 had drifted printed as a clean
                # obligation -- 99 broken threads invisible behind one survivor. Partial drift
                # gets its own class rather than being folded into DANGLING: the pair DOES
                # still hold live shared entities, so it is a real obligation, and calling it
                # wholly dangling would be the opposite error. Exclusive, like DANGLING, so
                # the classes still partition the pairs and the percentages still sum.
                out["PARTIALLY-DANGLING"] += 1
                detail["PARTIALLY-DANGLING"].append((a, b, len(gone), len(shared)))
                continue
        if recorded is None:
            out["IMPLIED-UNRECORDED"] += 1
            detail["IMPLIED-UNRECORDED"].append((a, b, len(shared)))
            continue
        # BOTH DIRECTIONS ARE TESTED, NOT ONE (order 7bffb5634d7a). This asked only
        # `back = (b, a) in recorded` and never whether (a, b) was recorded -- and the loop
        # above has already collapsed each unordered pair to whichever direction it happened to
        # meet first. So a genuinely ONE-WAY thread came out RECIPROCAL ("both ends know each
        # other -- the omniverse is joined here") whenever the recorded direction was the mirror
        # of the one the dedupe kept, and ASYMMETRIC-SUSPECT when it was not: the verdict was
        # decided by the insertion order of `pairs` rather than by the evidence, on the module's
        # two most important classes. Reproduced offline against the live module -- the same
        # single recorded direction gave RECIPROCAL or ASYMMETRIC-SUSPECT depending only on
        # which way round the pairs dict was iterated.
        #
        # LATENT UNTIL STEP 4: every caller passes recorded=None today (Hard Rule 5), so this
        # branch is unreachable and nothing wrong has been printed. It would have gone live at
        # exactly the moment the module was supposed to start being right.
        fwd, back = (a, b) in recorded, (b, a) in recorded
        if fwd and back:
            out["RECIPROCAL"] += 1
            detail["RECIPROCAL"].append((a, b, len(shared)))
            continue
        if not fwd and not back:
            # NEITHER END RECORDS IT. That is not asymmetry -- there is no direction to be
            # asymmetric about -- it is the same obligation-awaiting-the-pass that the
            # recorded=None branch above counts, and calling it one-way would invent a
            # direction the evidence does not contain.
            out["IMPLIED-UNRECORDED"] += 1
            detail["IMPLIED-UNRECORDED"].append((a, b, len(shared)))
            continue
        # ONE-WAY, ORIENTED SO THE FIRST NAME IS THE END THAT RECORDS THE THREAD. "a->b is
        # one-way" and "b->a is one-way" are different findings about different sources, and
        # the printed arrow is the only place that distinction survives.
        src, dst = (a, b) if fwd else (b, a)
        # is there a lawful excuse?
        excuse = None
        if distance_fn:
            d = distance_fn(src, dst)
            if d is not None and d * 1000.0 > event_age_years:
                excuse = f"propagation: {d*1000:.0f}yr away, event is {event_age_years:.0f}yr old"
        if excuse:
            out["ASYMMETRIC-LAWFUL"] += 1
            detail["ASYMMETRIC-LAWFUL"].append((src, dst, excuse))
        else:
            out["ASYMMETRIC-SUSPECT"] += 1
            detail["ASYMMETRIC-SUSPECT"].append((src, dst, len(shared)))
    return out, detail


def _namecol(rows, i=0):
    """Width of a name column, taken from the longest name ACTUALLY IN `rows`.

    THE NAMES USED TO BE SLICED. All four report loops printed `{a[:24]:26s} <-> {b[:24]}` or
    `{a[:26]:28s} -> {b[:26]}`, sitting directly under the sixteen-line argument above that
    these listings must never be shortened because main() is the ONLY reporting surface this
    module has. By that same argument the cut half of a source name is not recorded anywhere by
    anybody either, and a clipped name cannot be pasted into catalog.py, corpus_db.py or the
    roll -- which is the reader's very next action after reading a DANGLING row. Measured
    against SWEEP_ROLL.json's 215 sources: 50 names run past 24 characters and 39 past 26.
    Nothing was AMBIGUOUS today (no two share their first 24), which is what made it cheap to
    fix now. The rows are already materialised before each loop, so the true width is free.
    (order 8b08d0ecec8d)
    """
    return max((len(r[i]) for r in rows), default=0) + 2


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--age", type=float, default=300.0)
    args = ap.parse_args()

    ents, names = load_entities()
    print(f"sources with catalogued entities : {len(ents)}")
    print(f"distinct entity keys             : {len(names):,}")

    pairs = implied_threads()
    # NAMED FOR WHAT IT COUNTS (order 30581ee9cca2). `implied_threads` adds both (a,b)
    # and (b,a) for every shared entity, so this is DIRECTED and is exactly twice the
    # deduped pair count `classify` reports two lines below -- the same population,
    # printed twice, 2x apart, with nothing on the page saying so.
    print(f"implied thread directions        : {len(pairs):,} (directed; {len(pairs)//2:,} unordered source pairs)")
    print()

    # THREE DIFFERENT FAILURES USED TO PRINT ONE SENTENCE, AND NONE OF THEM WAS COUNTED
    # (order ae2afc775228). `import propagation`, `load_graph()` and the `dist` definition sat
    # inside one bare `except Exception`, which set dist=None and printed
    # "(propagation graph unavailable; ...)" for a missing module, a corrupt graph file and a
    # raising loader alike -- with the exception type never named and no `silence.note`, so the
    # swallow never reached state/failures.json. `silence.py` is a battery verifier precisely so
    # swallowed failures are countable, and this one was not counted.
    #
    # IT MATTERS MORE THAN IT LOOKS ONCE `recorded=` IS WIRED IN PHASE 4.2. `excuse` is only
    # assignable inside `if distance_fn:`, so with dist=None EVERY one-way thread falls to
    # ASYMMETRIC-SUSPECT and ASYMMETRIC-LAWFUL becomes structurally unreachable. STEP4_PLAN.md
    # §7C rules that one-way threads are lawful by default -- so the class that implements the
    # ruling is exactly the one that would quietly disappear, under a line that reads like a
    # footnote. The two conditions are told apart and both are recorded.
    dist = None
    try:
        import propagation as P
    except Exception as exc:
        silence.note("thread_integrity.py:propagation-import")
        print("(propagation module could not be imported: %s: %s -- asymmetry cannot be excused "
              "by distance, so every one-way thread will read as SUSPECT)"
              % (type(exc).__name__, exc))
    else:
        try:
            adj = P.load_graph()

            # Defined under its own name and then bound, rather than shadowing the
            # `dist = None` above: the shadow read to pyflakes as a redefinition of an
            # unused name, which is noise in the one file whose job is to be read.
            def _measure(a, b):
                d, path = P.shortest(adj, a, b)
                return None if not path else d

            dist = _measure
        except Exception as exc:
            silence.note("thread_integrity.py:propagation-graph")
            print("(propagation graph could not be loaded: %s: %s -- asymmetry cannot be excused "
                  "by distance, so every one-way thread will read as SUSPECT)"
                  % (type(exc).__name__, exc))

    # PHASE 4.2 (§7F): the graph this verifier was written to read, finally read.
    graph = None
    try:
        graph = load_thread_graph()
    except ThreadGraphUnreadable as exc:
        silence.note("thread_integrity.py:graph-unreadable")
        print("THREAD GRAPH UNREADABLE: %s" % exc)
        print("STEP4_PLAN.md §8: a corrupt or unreadable THREADS.json is OWNER-level, because "
              "every entry in the library cites it. An unreadable graph is not an empty one.")
        try:
            import escalation as _ESC
            _ESC.escalate(_ESC.OWNER, "THREAD_GRAPH_UNREADABLE",
                          "data/THREADS.json exists and cannot be read as a graph: %s" % exc,
                          who="thread_integrity.py")
        except Exception:
            silence.note("thread_integrity.py:graph-unreadable-escalation")
        return 1
    recorded = graph[0] if graph else None
    unresolvable = graph[1] if graph else []
    counts, detail = classify(pairs, dist, args.age, recorded=recorded, ents=ents)
    total = sum(counts.values())
    print("THREAD INTEGRITY")
    if graph is None:
        print("(no directed thread graph exists yet -- Hard Rule 5; asymmetry classes activate "
              "with the Step 4 entanglement pass)")
    else:
        m = graph[2]
        print("(directed thread graph %s -- %d sources, %s threads on record, %d source-level "
              "edges, %d recorded directions over %d addresses)"
              % (os.path.relpath(m["path"], HERE), m["sources"],
                 format(m.get("total_edges", 0), ","), m["source_level_edges"],
                 m["recorded_directions"], m["addresses"]))
    for k in ("IMPLIED-UNRECORDED", "RECIPROCAL", "ASYMMETRIC-LAWFUL", "ASYMMETRIC-SUSPECT",
              "PARTIALLY-DANGLING", "DANGLING"):
        if counts.get(k):
            print(f"  {k:20s} {counts[k]:6,}  ({counts[k]/total:5.1%})")
    print()
    # UNCAPPED, per Hard Rule 0, and this is the reason the rule is written the way it is.
    # These three lists used to print [:8], [:8] and [:6] under headers that read as complete
    # -- "one-way with no excuse (real holes, review these)" invites the reader to review the
    # holes, and showed six of them. main() is the ONLY reporting surface this module has: it
    # writes no JSON, and allsweep.py runs it as a bare subprocess health check without parsing
    # its output, so anything not printed here is not recorded anywhere by anybody. A truncated
    # ranked list is not a sample, it is a decision that everything past the cutoff does not
    # exist, wearing the same shape as the complete one. Ranking is kept -- richest first, so an
    # interrupted read still sees the worst -- and the count is now in the header, so the reader
    # can tell what they are looking at.
    # DANGLING FIRST, because it is the worst class and it was the one class NEVER PRINTED.
    # `classify()` computed it with the same per-pair detail as its three siblings and `main()`
    # itemised only the siblings, so the most severe finding this module makes -- a pair whose
    # EVERY shared entity has gone from the live records -- existed as a single number in the
    # count block above and nowhere else. Same defect as the truncation the paragraph above
    # describes, taken to its limit: not a shortened list but an absent one, under a report that
    # reads as complete. Ranked and uncapped like the rest (Hard Rule 0).
    if detail["DANGLING"]:
        rows = sorted(detail["DANGLING"], key=lambda x: -x[2])
        print(f"  DANGLING (every shared entity gone from the live records -- the thread points "
              f"at nothing) -- all {len(rows):,}, largest first:")
        wa = _namecol(rows)
        for a, b, n, tot in rows:
            print(f"     {n:4d}/{tot:<5d} gone     {a:{wa}s} <-> {b}")
        print()
    if detail["PARTIALLY-DANGLING"]:
        rows = sorted(detail["PARTIALLY-DANGLING"], key=lambda x: -x[2])
        print(f"  partial weave drift (obligation still real, some shared entities gone) "
              f"-- all {len(rows):,}, most-drifted first:")
        wa = _namecol(rows)
        for a, b, n, tot in rows:
            print(f"     {n:4d}/{tot:<5d} drifted  {a:{wa}s} <-> {b}")
        print()
    if detail["RECIPROCAL"]:
        rows = sorted(detail["RECIPROCAL"], key=lambda x: -x[2])
        print(f"  reciprocal bonds (the omniverse joined) -- all {len(rows):,}, strongest first:")
        wa = _namecol(rows)
        for a, b, n in rows:
            print(f"     {n:4d} shared  {a:{wa}s} <-> {b}")
    # THE FOURTH LISTING. ASYMMETRIC-LAWFUL was the one remaining class whose per-pair detail
    # was computed at :188 and then discarded: main() itemised its three siblings and this one
    # appeared only as a number in the counts block -- verbatim the defect the paragraph above
    # describes for DANGLING. It matters here in the other direction: the excuse string IS the
    # evidence for WAIVING a hole (the propagation arithmetic), and a waiver nobody can read is
    # a waiver nobody can check. Latent today -- every caller passes recorded=None per Hard
    # Rule 5, so this class is always 0 -- and it goes live the moment the Step 4 entanglement
    # pass starts producing directed edges. Sorted by name rather than by magnitude because
    # there is no magnitude on a waiver; alphabetical is at least deterministic. (9ba94e964314)
    if detail["ASYMMETRIC-LAWFUL"]:
        rows = sorted(detail["ASYMMETRIC-LAWFUL"], key=lambda x: (x[0], x[1]))
        print()
        print(f"  one-way WITH a lawful excuse (waived holes -- the excuse is the evidence, "
              f"check it) -- all {len(rows):,}:")
        wa = _namecol(rows)
        for a, b, excuse in rows:
            print(f"     {a:{wa}s}  -> {b}")
            print(f"         {excuse}")
    if detail["ASYMMETRIC-SUSPECT"]:
        rows = sorted(detail["ASYMMETRIC-SUSPECT"], key=lambda x: -x[2])
        print()
        # The arrow is directed and it means something: the LEFT source records the thread and
        # the right one does not. Which end is which is the finding, so it is stated (order
        # 7bffb5634d7a).
        print(f"  one-way with no excuse (real holes, review these; left records the thread, "
              f"right does not) -- all {len(rows):,}, most shared entities first:")
        wa = _namecol(rows)
        for a, b, n in rows:
            print(f"     {n:4d} shared  {a:{wa}s}  -> {b}")

    # THE VERDICT REACHES THE EXIT CODE, WHICH IS THE ONLY THING WATCHING (order
    # aa075aa80f5c). `main()` had no `return` on any path and was invoked bare, so the
    # process always exited 0 -- and `allsweep` reads the rc and nothing else. A run in
    # which EVERY implied thread was DANGLING was byte-identical, to its only automated
    # consumer, to a run in which none was. The comment two hundred lines up states the
    # premise ("main() is the ONLY reporting surface this module has") and stopped one
    # step short of the consequence. Same defect `allsweep` records as just fixed for
    # rosetta.py: "main() returned 0 whatever the rhos said".
    #
    # DANGLING ALONE IS THE FAILURE, and the other two classes are deliberately not.
    #   * IMPLIED-UNRECORDED is 100% today and that is CORRECT -- no directed thread
    #     graph exists before Step 4, so every implied direction is unrecorded by
    #     construction. Grading it would make this row red until the entanglement pass
    #     ships, i.e. an alarm that always sounds, which this project has had to walk
    #     back once already.
    #   * PARTIALLY-DANGLING means SOME shared entities went; it is degradation, not a
    #     pointer at nothing, and its meaning changes once a real graph exists. It is
    #     reported and left ungraded until there is a graph to read it against -- the
    #     ruling STEP4_PLAN.md §8 makes ("DANGLING = 0 is a release gate, not a metric")
    #     names only the one class.
    #
    # MEASURED BEFORE LANDING, so the next sweep's colour is known rather than
    # discovered: DANGLING 0, PARTIALLY-DANGLING 0, IMPLIED-UNRECORDED 5,782 of 5,782.
    # This returns 0 today and turns red the first time a thread points at nothing.
    dangling = counts.get("DANGLING", 0)
    if dangling:
        print()
        # THE UNIT IS SOURCE PAIRS, NOT THREADS, and this is the line the module will be
        # read on as a release gate (STEP4_PLAN.md §8), so it says which. Each DANGLING
        # row prints n of tot keys gone, so one pair here can stand for a hundred
        # vanished entities.
        print(f"THREAD INTEGRITY FAILED: {dangling:,} source pair(s) whose every shared "
              f"entity has gone -- their threads point at nothing. "
              f"A thread that resolves to nothing is not a weak thread, it is a broken "
              f"one (STEP4_PLAN.md §1).")
    failed = bool(dangling)

    # PHASE 4.2 RELEASE GATE (§8): a thread that resolves to NO ADDRESS. Every offender is
    # printed, by source, uncapped -- and each offending source is refused at SUPERVISOR,
    # which closes THAT source's area and nothing else (Hard Rule -1: every source is its own
    # area of the park).
    if unresolvable:
        failed = True
        by_src = collections.defaultdict(list)
        for src, cls, to in unresolvable:
            by_src[src].append((cls, to))
        print()
        print(f"THREAD INTEGRITY FAILED: {len(unresolvable):,} thread(s) resolve to NO ADDRESS "
              f"-- all of them, by source (STEP4_PLAN.md §8, DANGLING = 0 is a release gate):")
        for src in sorted(by_src):
            print(f"   {src}")
            for cls, to in by_src[src]:
                print(f"      {cls} -> {to!r}")
        try:
            import escalation as _ESC
            for src, items in sorted(by_src.items()):
                _ESC.escalate(_ESC.SUPERVISOR, "THREAD_UNRESOLVABLE",
                              "%d thread(s) from %s resolve to no address: %s"
                              % (len(items), src, ", ".join(repr(t) for _, t in items)),
                              source=src, who="thread_integrity.py")
        except Exception:
            silence.note("thread_integrity.py:unresolvable-escalation")

    # THE ASYMMETRIC-SUSPECT REGRESSION FLOOR (§7F). Only meaningful once a graph exists;
    # before that the class is structurally zero and a floor of zero would be a lie.
    if recorded is not None:
        state, measured, bar = _floor_verdict(counts.get("ASYMMETRIC-SUSPECT", 0))
        print()
        if state == "baseline":
            print(f"ASYMMETRIC-SUSPECT floor: {measured:,} recorded as the Phase 4.2 baseline "
                  f"(state/THREAD_INTEGRITY_FLOOR.json); a later count above it fails, below it "
                  f"ratchets the floor down. Existing asymmetry is not a failure (ruling C).")
        elif state == "held":
            print(f"ASYMMETRIC-SUSPECT floor: held at {measured:,}")
        elif state == "ratcheted":
            print(f"ASYMMETRIC-SUSPECT floor: {bar:,} -> {measured:,}, ratcheted down")
        elif state == "REGRESSED":
            failed = True
            print(f"THREAD INTEGRITY FAILED: ASYMMETRIC-SUSPECT REGRESSED, {measured:,} against "
                  f"a floor of {bar:,}. Asymmetry that exists is lawful (ruling C); asymmetry "
                  f"that GROWS is a hole opening, and the floor may not be raised to hide it.")
        else:
            failed = True
            print("THREAD INTEGRITY FAILED: the ASYMMETRIC-SUSPECT floor file exists and cannot "
                  "be read, so the regression gate cannot be judged. Fail closed.")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
