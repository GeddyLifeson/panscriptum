#!/usr/bin/env python3
"""
CHAIN — phase 4, the Chain of Defeats. Who has beaten whom, and what that orders.

Charter Part Three names three sources of evidence for an Assay: "a feat somebody witnessed, an
instrument somebody read, or a defeat somebody suffered." The library has been collecting the
first two for days. This is the third, and it is the only one that checks the others.

A feat says what an entity did. A DEFEAT says how it stands against a named opponent, which is
the only evidence that directly constrains an ordering. If our Assay puts A above B while the
source records B beating A, that is a defect visible without anyone's opinion -- which is exactly
what an accuracy leg has to be.

WHY IT IS BUILDABLE NOW AND WAS NOT BEFORE
------------------------------------------
The blurb corpus had 2,276 sentences mentioning a win or a loss, in 170-character descriptions
that rarely named both parties. The mined pages carry 3,612 and they read like records:

    "Once he becomes serious, he casually overpowers Glorio with his Power Pole."
    "However, Goku and Duu quickly tired and Gomah was able to overpower and defeat them."

Naming the opponent is the whole problem, and it is a reading task rather than a parsing one --
a regex that pulls the noun after "defeated" also pulls "the Gendarmerie" and "concedes". So the
model reads the sentence and returns the pair, and every pair is then CHECKED against the entity
index before it is allowed to become an edge.

WHAT THIS REFUSES TO DO
-----------------------
Ford (1957): the Bradley-Terry MLE exists and is unique if and only if the comparison graph is
strongly connected. `rigor.bradley_terry` already enforces that and returns components rather
than pretending. So this reports strengths WITHIN a component and refuses to compare across them,
because between two entities who have never met, through anyone, there is no number to have.
"""
import argparse
import collections
import json
import os
import re
import sys
import glob
import silence

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import rigor as RG                                                      # noqa: E402
import weave_index as WI                                                # noqa: E402
import identity as ID                                                   # noqa: E402

_BAD_CHARS = (chr(8), chr(11), chr(12), chr(7))
if any(c in open(os.path.abspath(__file__), encoding="utf-8").read() for c in _BAD_CHARS):
    raise SystemExit(__file__ + ": a regex escape was eaten in transit.")

OUT = os.path.join(HERE, "data", "CHAIN.json")

OUTCOME = re.compile(
    r"\b(defeat(?:ed|s)?|beat(?:en)?|kill(?:ed|s)?|slew|slain|overpower(?:ed|s)?|bested|"
    r"outmatched|lost to|fell to|surrender(?:ed)? to|conced(?:ed|es)|"
    r"destroy(?:ed|s)?|struck down|put down|subdued)\b", re.I)

SYSTEM = """You read NUMBERED sentences from a fiction wiki and report CONTEST OUTCOMES.

For each sentence that records one, name who WON and who LOST, and give that sentence's own
number in `index`. Both parties must be named or clearly referred to in the sentence itself.

Skip freely -- most sentences record no contest at all -- but never renumber. `index` is the
bracketed number printed in front of the sentence you read, not the position of your answer in
your reply. An outcome carrying the wrong number is filed against a different page, and takes
that page's continuity with it.

Return nothing when:
  - the sentence names no opponent ("he destroyed the city" has no loser, a city is not a party)
  - the outcome is hypothetical, attempted, or predicted
  - the parties are groups too vague to identify ("the soldiers", "his enemies")
  - you would have to use knowledge from outside this sentence to fill either side

An empty result is the common and correct answer. A guessed pair is worse than none, because a
single wrong edge reorders everything downstream of it."""

SCHEMA = {
    "type": "object",
    "properties": {
        "outcomes": {"type": "array", "items": {
            "type": "object",
            "properties": {"index": {"type": "integer"},
                           "winner": {"type": "string"}, "loser": {"type": "string"}},
            "required": ["index", "winner", "loser"]}}},
    "required": ["outcomes"],
}


# Filled by `extract()`, read by `write_result()`. MODULE STATE rather than a fourth return
# value or a fourth argument, because both of those shapes are pinned from outside this file:
# drill.py's phase-4 net drives `pipeline.phase_chain` against a stand-in chain module whose
# `extract` is `lambda rows, workers=8: (edges, unmatched, prov)` and whose `write_result` is
# `lambda edges, res, unmatched: doc`, and drill.py belongs to another agent. Widening either
# signature would break that net rather than the code it guards. `None` means "extract did not
# report", which is NOT the same claim as "nothing failed" -- see write_result's `unanswered`.
_LAST_EXTRACT = None


def write_result(edges, res, unmatched=None, unanswered=None):
    """THE ONE WRITER for data/CHAIN.json, whatever schema the fit came back in.

    This file used to be written by two callers with two different shapes: this module's own
    main() wrote {edges, names, strengths, identified, components, deviance_per_df} and
    pipeline.phase_chain wrote {edges, unmatched, fit}. Every consumer worked against whichever
    writer had run last and broke against the other. One schema, both callers, and the fit's
    refusal is a field rather than a different document.
    """
    out = {
        "edges": [[a, b, n] for (a, b), n in edges.items()],
        "identified": bool(res.get("identified")),
        "components": [sorted(c) for c in (res.get("components") or [])],
        "names": res.get("names"),
        "strengths": (list(res["strengths"]) if res.get("strengths") is not None else None),
        "deviance_per_df": res.get("deviance_per_df"),
        "fit_error": res.get("error") or res.get("refusal"),
        # UNCAPPED, ranked, per Hard Rule 0. This was `most_common(40)`: a RANKED-THEN-TRUNCATED
        # roster in a PERSISTED artifact, which the rule forbids outright and for the reason it
        # gives -- 40 rows and 40-of-900 rows are the same shape on disk, so every later reader
        # of CHAIN.json would have been reading a smaller universe with no way to tell. Nothing
        # here is a console preview: `main()` prints its own short list to the terminal and this
        # file is the only place the whole roster is ever written down. `most_common()` with no
        # argument keeps the ordering (commonest first, so an interrupted read still sees the
        # worst offenders) and drops only the cutoff. The totals ride along beside it so a
        # reader never has to trust that the list is whole -- they can check.
        "unmatched": (unmatched.most_common() if hasattr(unmatched, "most_common")
                      else (unmatched or [])),
        "unmatched_distinct": (len(unmatched) if unmatched is not None else 0),
        "unmatched_mentions": (sum(unmatched.values()) if hasattr(unmatched, "values")
                               else None),
        # HOW MUCH OF THE CORPUS WAS ACTUALLY READ, beside the edge count that came out of it.
        # A chunk whose model call never landed yields no outcomes, which is byte-for-byte the
        # same contribution to this file as a chunk the model read and found no contest in --
        # so a pass that lost a third of its chunks to HTTP 503 wrote a third-smaller contest
        # graph and said nothing. `null` here means extract did not report (an older file, or a
        # caller that built the document some other way); it does not mean zero failures.
        "unanswered": (unanswered if unanswered is not None else _LAST_EXTRACT),
    }
    # Write-then-rename, not a bare truncating open. This is a published phase artifact, and a
    # bare open() leaves a TORN CHAIN.json if the process dies mid-dump or a reader holds it --
    # the half-written state being indistinguishable, to anything that later reads it, from a
    # fit that genuinely found fewer edges. Every other phase artifact in the kit lands this way.
    # `silence.write_json`, not a hand-rolled `OUT + ".tmp"`. The rename was already atomic; the
    # TEMP NAME was not unique. `write_result` has two documented concurrent callers -- chain.main
    # and pipeline.phase_chain -- and both would build the same fixed temp path, so one could
    # rename the other's half-written file into place. That is the collision m100 closed at
    # twelve sites on 2026-08-25; chain.py's two were missed. (run #26)
    if not silence.write_json(OUT, out, indent=1, ensure_ascii=False):
        silence.note("chain.py:write_result-denied")
        print("chain: CHAIN.json could not be replaced; it still holds the PREVIOUS cycle's fit.",
              file=sys.stderr)
    return out


HARVEST_IDX = os.path.join(HERE, "state", "chain_harvest_idx.json")


def _corpus_root_state(base):
    """Classify `data/<base>` in the live project: 'live', 'gone' or 'unavailable'.

    `publish._live_root_state`'s question, asked about a CORPUS root, because harvest's prune had
    none of it: it turned on `glob.glob`, which returns `[]` for a directory that is missing, a
    directory that is merely unreadable right now, and a directory that genuinely holds no JSON,
    and never raises for any of them. `live` is built only from what globbed and the prune below
    deletes every index entry that is not in it -- so one unreadable mount (a Norton lock, an
    offline junction, a permissions blip on ~56,000 files) reads as "the whole feats corpus was
    deleted", and the pass harvests a fraction of the corpus while saying nothing.

    So this asks twice. A root that lists is 'live'. A root that does not list AND whose name is
    ABSENT from a successfully enumerated `data/` is 'gone' -- positive evidence of removal,
    because the parent answered. Anything else is 'unavailable', and the caller holds the prune
    for that subtree. (order b9c013a041db)
    """
    root = os.path.join(HERE, "data", base)
    try:
        if os.path.isdir(root):
            os.listdir(root)              # present is not the same as readable
            return "live"
    except OSError:
        return "unavailable"
    try:
        present = base in os.listdir(os.path.join(HERE, "data"))
    except OSError:
        # We could not even read `data/`. Nothing may be withdrawn from the index on that.
        return "unavailable"
    return "unavailable" if present else "gone"


def _held_root(rel, held):
    """Does index key `rel` sit under one of the roots we could not read this pass? -> bool.

    Keys are `os.path.relpath(fp, HERE)`, so they carry the platform's separator -- and an index
    written on one platform is read on another when the kit moves. Both spellings are checked so
    the hold cannot be defeated by a slash.
    """
    r = rel.replace("\\", "/")
    return any(r.startswith("data/%s/" % b) for b in held)


def harvest():
    """Every mined feat sentence that reads like a contest outcome.

    INCREMENTAL. The feats corpus is ~56,000 files and ~900MB, and this re-parsed all of it
    every pipeline cycle to re-derive contests that only grow between runs (2026-08-23
    optimization sweep: minutes of I/O per cycle). The index keeps, per file, its mtime and
    the contest rows it yielded; only files newer than their indexed mtime are re-opened.
    Deleting the index file is always safe -- the next run rebuilds it whole."""
    try:
        with open(HARVEST_IDX, encoding="utf-8") as f:
            idx = json.load(f)
    except Exception:
        _ = "silence-exempt: a missing or corrupt index rebuilds whole; documented safe"
        idx = {}
    # The designator inventory, loaded ONCE. identify() with inv=None re-reads
    # DESIGNATORS.json from disk per call, and harvest called it per outcome sentence --
    # thousands of 54KB parses per pass (round-2 optimization audit, finding 5).
    try:
        _inv = ID.load()
    except Exception:
        silence.note("chain.py:inv-load")
        _inv = None
    live, changed, held = set(), 0, []
    for base in ("readfeats", "feats"):
        # ABSENCE OF EVIDENCE IS NOT EVIDENCE OF DELETION. A root that will not list is HELD:
        # its index entries survive the prune below, so this pass still returns the rows it
        # cached for them last time and the corpus does not silently shrink. A root that is
        # genuinely 'gone' globs to nothing and prunes normally, as it always did.
        if _corpus_root_state(base) == "unavailable":
            held.append(base)
            silence.note("chain.py:harvest-root-unavailable")
            print(f"chain: data/{base} could not be listed this pass (locked? offline mount?). "
                  f"Its index entries are HELD rather than pruned, and this harvest re-uses the "
                  f"rows cached for them; nothing under it was re-read.", file=sys.stderr)
            continue
        for fp in glob.glob(os.path.join(HERE, "data", base, "**", "*.json"), recursive=True):
            rel = os.path.relpath(fp, HERE)
            live.add(rel)
            try:
                mt = os.path.getmtime(fp)
            except OSError:
                _ = "silence-exempt: a file deleted mid-scan is simply not part of this harvest"
                continue
            cached = idx.get(rel)
            if cached and cached.get("mt") == mt:
                continue
            try:
                with open(fp, encoding="utf-8") as f:
                    d = json.load(f)
            except Exception:
                # Named for WHAT FAILED, not for where it sat. This was `chain.py:91` and the
                # line moved to 169 -- a tag that points at an unrelated line is worse than an
                # opaque one, because it sends the next reader somewhere confidently wrong.
                # Same repair as ingest_doc.py's, which run #35 pinned with a check that no
                # `silence.note` tag in that file is a bare number.
                silence.note("chain.py:harvest-feats-unreadable")
                continue
            ent = d.get("entity")
            host = d.get("host") or os.path.basename(os.path.dirname(fp)).replace("_", ".")
            found = []
            for x in (d.get("feats") or []):
                t = x.get("feat") or ""
                if not OUTCOME.search(t):
                    continue
                # The page a sentence was mined from carries the branch it belongs to. Keeping
                # it here is what lets an Earth-616 win stay an Earth-616 win instead of being
                # averaged into a being no source recorded.
                page = x.get("page", "")
                _, cont = ID.identify(page, host, inv=_inv)
                found.append({"entity": ent, "sentence": t, "page": page,
                              "host": host, "continuity": cont})
            idx[rel] = {"mt": mt, "rows": found}
            changed += 1
    # A file that vanished takes its contests with it -- an index must never outlive its corpus.
    # Unless we never got to look: a key under a HELD root was not proven absent, only unread.
    for rel in [k for k in idx if k not in live and not _held_root(k, held)]:
        del idx[rel]
        changed += 1
    if changed:
        try:
            # Unique temp name via silence.write_json -- see write_result above; same two
            # concurrent callers reach this index. (run #26)
            # The VERDICT, not just the attempt. A denied rename here is not harmless: the index
            # is the incremental cache, so a silent failure means every following cycle re-parses
            # ~900MB of feats to rediscover the same rows -- minutes of I/O per cycle presenting
            # as "the pipeline is just slow". Deleting the index is documented safe; NOT KNOWING
            # whether it was written is what costs. (Same family as m33-m35.)
            if not silence.write_json(HARVEST_IDX, idx, ensure_ascii=False):
                silence.note("chain.py:harvest-idx-denied")
                print("chain: harvest index could not be replaced (reader holding it?); this "
                      "cycle's incremental gains are lost and the next pass re-parses whole.",
                      file=sys.stderr)
        except Exception:
            silence.note("chain.py:harvest-idx")
    rows, seen = [], set()
    for rel in sorted(idx):
        for r in idx[rel].get("rows", []):
            # m37. The key was `sentence[:120]`, which made the dedup DECIDE WHICH CONTESTS EXIST:
            # two different sentences about the same entity sharing a 120-character prefix -- the
            # ordinary shape of wiki prose, which front-loads the subject -- collided, and the
            # second was dropped as a duplicate it was not. Measured over the live index on
            # 2026-08-24: 6,317 rows, of which 2 distinct contests were being discarded this way
            # (a Frieza technique entry and a Phlox entry, both long lead-ins). Hard Rule 0: an
            # identity key may not be a truncation. The full sentence can only make the dedup
            # finer, never coarser, so nothing that was kept before stops being kept.
            k = (r.get("entity"), r.get("sentence") or "")
            if k in seen:
                continue
            seen.add(k)
            rows.append(r)
    return rows


def _partials(name):
    """Keys a name might also be known by: surname, given name, the head of a title.

    The index missed "Ichigo" against "Ichigo Kurosaki", "Tien" against "Tien Shinhan" and
    "Perfect Cell" against "Cell" -- a wiki writes the short form far more often than the
    catalogue's full one, and every one of those was a real contest edge thrown away.
    Tokens of three characters or fewer are excluded: "Big", "The" and "Kid" each collide with
    dozens of unrelated entities, and one wrong edge reorders everything beneath it.
    """
    parts = [w for w in re.split(r"[^A-Za-z0-9']+", name) if len(w) > 3]
    return {WI.norm(w) for w in parts}


def entity_index():
    """{normalised name: canonical name} over everything the library catalogues.

    Continuity-aware, because `weave_index.norm` keeps a declared timeline in the key. An
    Earth-616 win must not become an Earth-1610 edge.

    Short forms resolve only when they are UNAMBIGUOUS across the whole library. A surname shared
    by two catalogued entities resolves to neither, because guessing which one fought would
    invent a contest that never happened.
    """
    idx, partial, clash = {}, {}, set()
    for r in WI.load_records():
        for e in r.get("entries", []):
            n = e.get("name")
            if not n:
                continue
            idx.setdefault(WI.norm(n), n)
            for k in _partials(n):
                if k in partial and partial[k] != n:
                    clash.add(k)
                else:
                    partial[k] = n
    for k in clash:
        partial.pop(k, None)
    for k, v in partial.items():
        idx.setdefault(k, v)          # full names always win
    return idx


def _ask(system, prompt, schema):
    try:
        import cascade_bridge as CB
        if CB.engine():
            got = CB.ask(system, prompt, schema)
            if got is not None:
                return got
    except Exception:
        silence.note("chain.py:ask-cloud")   # was `chain.py:155`; the line is now 276
        pass
    try:
        import pipeline as P
        import read as R
        return P.ask(R.config(), system, prompt, schema, timeout=300)
    except Exception:
        silence.note("chain.py:ask-local")   # was `chain.py:161`; the line is now 283
        return None


def extract(rows, batch=8, limit=None, workers=8):
    """(winner, loser) pairs, read out of the sentences and checked against the index."""
    import threading
    from concurrent.futures import ThreadPoolExecutor
    # Same ceiling rule as the assay. Eight extractors against one local model is the shape that
    # produced HTTP 503 and dropped this pass from 64 edges to 25.
    try:
        import tuning as T
        prof = T.profile(force=True)
        workers = T.workers(workers)
        print("   regime: %s (%s) -> %d worker(s)" % (prof["regime"], prof["why"], workers),
              flush=True)
    except Exception:
        silence.note("chain.py:tuning")
    idx = entity_index()
    rows = rows[:limit] if limit else rows
    edges = collections.Counter()
    prov = collections.defaultdict(list)
    unmatched = collections.Counter()
    lock = threading.Lock()
    # `unanswered_*` are the transport tally, and they are the reason the rest of these numbers
    # can be read at all. See `work` below.
    done = {"n": 0, "pairs": 0, "kept": 0, "unanswered_chunks": 0, "unanswered_rows": 0}

    def work(chunk):
        lines = [f"[{i}] (filed under: {r['entity']}) {r['sentence']}"
                 for i, r in enumerate(chunk, 1)]
        got = _ask(SYSTEM, "SENTENCES:\n" + "\n".join(lines), SCHEMA)
        # ANSWERED WITH NOTHING IS NOT THE SAME ANSWER AS NEVER ANSWERED, and until this tally
        # existed the two were indistinguishable everywhere downstream: `(got or {})` turns both
        # into an empty outcome list, `done['n']` counted the chunk as read either way, and
        # write_result persisted the smaller graph to CHAIN.json under a clean progress line.
        # `_ask` returns None ONLY when both arms failed -- the cascade bridge raised or declined,
        # and `pipeline.ask` returned None after its retries -- so `got is None` is exactly "no
        # model answered". An empty `outcomes` list from a model that did answer is the common and
        # correct result and is NOT counted here.
        #
        # The realistic case is partial, not total: this function's own ceiling comment records
        # the pass that HTTP 503 dropped from 64 edges to 25. `adjudicate_mutuals` guards this
        # exact shape one function down for the epoch probe, over a handful of pairs; this is the
        # path that touches thousands of sentences. (order 6d35eacf252d)
        unanswered = got is None
        local = []
        # TALLIED LOCALLY, MERGED UNDER THE LOCK, for the same reason `local` exists.
        #
        # This was `unmatched[side[:40]] += 1` written straight into the shared Counter from
        # inside the worker, while every other shared structure here (`edges`, `prov`, `done`)
        # was correctly deferred to the `with lock:` block below. `counter[k] += 1` is a
        # read-modify-write -- __getitem__, add, __setitem__, with bytecode boundaries between
        # them -- so with `workers` commonly at 8 two threads can read the same count and both
        # write back the same successor, losing increments. Nothing in the graph was at risk;
        # what was at risk is the "most common names that match nothing" diagnostic printed by
        # `main()` and stored in CHAIN.json's `unmatched` field, which would UNDERCOUNT exactly
        # the names most worth chasing (the commonest ones collide most). Found by the run #33
        # sweep (batch 12).
        local_unmatched = collections.Counter()
        for o in (got or {}).get("outcomes", []):
            # THE SENTENCE IS NAMED BY THE MODEL, NOT GUESSED FROM POSITION.
            #
            # This read `chunk[min(i, len(chunk) - 1)]` -- outcome number i belongs to sentence
            # number i. The model is handed eight sentences and told that skipping is "the
            # common and correct answer", so the two lists are almost never the same length.
            # Every outcome after the first skipped sentence was therefore attributed to the
            # wrong sentence, and inherited the wrong page and the wrong CONTINUITY.
            #
            # The names on the edge stayed correct, which is why this never looked like a bug:
            # a real contest between two real fighters, filed under a branch neither of them
            # was in. Then `ID.node(name, continuity)` keys them onto branch-specific nodes,
            # and a graph that should connect fragments into per-branch islands -- 21 of them,
            # 70 of 82 fighters holding a single edge. Ford's condition cannot be met by a
            # graph assembled this way no matter how many sentences are fed to it.
            try:
                pos = int(o.get("index", 0)) - 1
            except (TypeError, ValueError):
                # was `chain.py:252`; the line is now 345
                silence.note("chain.py:extract-bad-index")
                continue
            if not (0 <= pos < len(chunk)):
                continue
            src = chunk[pos]
            w, loser = (o.get("winner") or "").strip(), (o.get("loser") or "").strip()
            if not w or not loser or w.lower() == loser.lower():
                continue
            wk, lk = WI.norm(w), WI.norm(loser)
            # BOTH sides must be things the library catalogues. An edge to a name that exists
            # only in this sentence cannot be ranked against anything and would inflate the
            # graph with singletons that break Ford's condition for everyone attached to them.
            if wk in idx and lk in idx:
                # A contest happens inside one branch. The branch is known for the page the
                # sentence came from, and both parties inherit it -- an Earth-616 page does not
                # narrate an Earth-1610 fight. Where the page names no branch the node stays
                # bare, which is the right answer for a single-timeline source.
                c = src.get("continuity")
                local.append(((ID.node(idx[wk], c), ID.node(idx[lk], c)), src))
            else:
                for side, k in ((w, wk), (loser, lk)):
                    if k not in idx:
                        # THE WHOLE NAME IS THE KEY, not `side[:40]`. Hard Rule 0: an identity
                        # key may not be a truncation -- the same repair m37 made twelve lines
                        # above for `sentence[:120]`, and for the same reason, except that this
                        # roster is PERSISTED (write_result stores it in CHAIN.json, uncapped,
                        # precisely so a later reader can chase every name). "Commander Shepard
                        # of the Systems Alliance Navy" and "... Marines" are two names sharing
                        # a 40-character prefix, and they were arriving as one row whose count
                        # was the sum of two different unmatched entities. A longer key can only
                        # split rows that were wrongly merged; nothing that was counted stops
                        # being counted. (order 29dde10c569c)
                        local_unmatched[side] += 1
        with lock:
            unmatched.update(local_unmatched)
            done["n"] += len(chunk)
            done["pairs"] += len((got or {}).get("outcomes", []))
            if unanswered:
                done["unanswered_chunks"] += 1
                done["unanswered_rows"] += len(chunk)
            for e, src in local:
                edges[e] += 1
                prov[e].append(src)
                done["kept"] += 1
            if done["n"] % 200 < batch:
                print(f"   {done['n']:>6}/{len(rows)}  pairs {done['pairs']:>5}  "
                      f"kept {done['kept']:>5}"
                      + (f"  UNREAD {done['unanswered_rows']:>5}"
                         if done["unanswered_rows"] else ""), flush=True)

    chunks = [rows[i:i + batch] for i in range(0, len(rows), batch)]
    with ThreadPoolExecutor(max_workers=workers) as ex:
        list(ex.map(work, chunks))
    # Handed to write_result through module state -- see `_LAST_EXTRACT` above for why it cannot
    # ride on the return value. Set unconditionally, including the all-clear, so a zero here is a
    # measurement rather than an absence.
    global _LAST_EXTRACT
    _LAST_EXTRACT = {"chunks": len(chunks), "sentences": done["n"],
                     "chunks_unanswered": done["unanswered_chunks"],
                     "sentences_unanswered": done["unanswered_rows"]}
    if done["unanswered_chunks"]:
        # Loud, and on the way out rather than only in CHAIN.json: this is the difference between
        # "the corpus records this many contests" and "this is what we managed to read today".
        print(f"   TRANSPORT: {done['unanswered_chunks']:,} of {len(chunks):,} chunks "
              f"({done['unanswered_rows']:,} of {done['n']:,} sentences) were NEVER READ -- no "
              f"model answered. The contest graph below is a floor, not the corpus.", flush=True)
        silence.note("chain.py:extract-unanswered")
    return edges, unmatched, prov


def adjudicate_mutuals(edges, prov):
    """Split mutual pairs in time before fitting anything to them.

    A mutual pair -- A beats B and B beats A -- is the one shape in a contest graph that cannot
    be taken at face value. It is either a genuine split decision, or an identity that has
    dropped a coordinate. Both of the pairs found so far were the second kind:

        Goku loses to Mercenary Tao.
        Goku beats Mercenary Tao "after training with Korin".

    Nothing there is inconsistent. It is one entity at two points in its own history, and
    collapsing them manufactures a contradiction the source never contained -- then feeds it to
    Bradley-Terry, which has no way to know and dutifully splits the difference.

    So EVERY provenance sentence recorded for each side of a mutual pair is dated
    (identity.epoch_of, one model call each -- an edge carries one sentence per recorded win, not
    one in total), a side takes the epoch its sentences agree on, and where the two sides date
    differently the winner is re-keyed onto an epoch-specific node. Where a single side's own
    sentences date to different epochs the pair is left whole and that is reported: it is a
    finding about the record, not a chronology. Where neither side dates itself, the pair is
    LEFT STANDING: that is a real disagreement in the record,
    and dissolving it with an invented chronology would be the same fabrication this library
    exists to refuse.

    A pair whose probe NEVER RAN is a third case and is reported as its own tally: it is left
    standing too, but UNJUDGED, because "nobody asked" is not evidence that the record disagrees
    with itself. With transport down, every mutual pair would otherwise be filed as a genuine
    disagreement and the run would look clean -- a check that cannot fail.

    Only mutual pairs are dated. A sentence that contradicts nothing gains nothing from a
    timestamp, and there are eleven thousand of those.
    """
    mutual = [(w, loser) for (w, loser) in edges if (loser, w) in edges and (w, loser) < (loser, w)]
    if not mutual:
        print("\nmutual pairs: none -- no contest is recorded in both directions")
        return edges
    # Was indented one level deeper, i.e. after the `return` inside `if not mutual` -- so the
    # one line announcing that mutual pairs are being adjudicated could only ever run when
    # there were none. The dating below has always executed; nothing said so.
    print(f"\nmutual pairs: {len(mutual)} -- dating each side before it reaches the fit")
    out = collections.Counter(edges)
    split = kept = unprobed = half_dated = self_split = 0

    def side_epoch(e):
        """-> (epoch, its own sentences' disagreement, whether anything probed) for one side.

        EVERY PROVENANCE SENTENCE, NOT THE FIRST (order 0d71cb2b08df). `prov[e].append(src)` runs
        once per KEPT OUTCOME in `extract` (:492), so `len(prov[e]) == edges[e]` and this side
        can carry several sentences. Reading only `[0]` meant a side whose first sentence happens
        not to date itself was recorded as a genuine disagreement even when a later sentence for
        the very same edge does date it -- an adjudication reached on one sentence of several,
        which is the same shape one level down from the half-evidence fault order 679368768c02
        closed in the branch below. The docstring's "each mutual pair's two sentences" was only
        ever true of an edge with exactly one recorded win.

        A side whose OWN sentences date to different epochs is not resolved by list order: that
        disagreement is itself a finding, so it is returned and the caller leaves the pair whole.
        UNPROBED stays as it was -- a side counts as unprobed only if EVERY one of its sentences
        failed to probe, because one sentence that answered means the run learned something.
        """
        eps, probed = [], False
        for row in (prov.get(e) or [{}]):
            try:
                ep = ID.epoch_of((row or {}).get("sentence", ""), strict=True)
            except ID.ProbeUnavailable:
                continue
            probed = True
            if ep:
                eps.append(ep)
        uniq = sorted(set(eps))
        return (uniq[0] if uniq else ""), (uniq if len(uniq) > 1 else []), probed

    for (w, loser) in mutual:
        ea, conf_a, probed_a = side_epoch((w, loser))
        eb, conf_b, probed_b = side_epoch((loser, w))
        if not (probed_a and probed_b):
            # UNPROBED IS NOT UNDATED. The pair is left standing either way, but it must not be
            # counted as a genuine disagreement: nothing asked, so nothing was found out.
            unprobed += 1
            silence.note("chain.py:epoch-unprobed")
            print(f"   NOT ADJUDICATED: {w} vs {loser} -- the epoch probe did not run, so this "
                  f"pair is left standing UNJUDGED rather than recorded as a disagreement")
            continue
        if conf_a or conf_b:
            # A SIDE THAT DISAGREES WITH ITSELF. Two recorded wins on one edge dating to
            # different epochs is a real finding about the record, not a list to take the head
            # of. Re-keying the side onto either epoch would pick one by array order and bury
            # the other, so the pair is left whole and the epochs are named.
            self_split += 1
            print(f"   left standing: {w} vs {loser} -- one side's own sentences date to "
                  f"different epochs ({' / '.join(conf_a or conf_b)}), which is a finding about "
                  f"the record rather than a chronology to split on")
            continue
        if ea and eb and ea != eb:
            # BOTH SIDES DATED, AND DATED DIFFERENTLY. The condition was a bare `ea != eb`, which
            # is also true when one side dates itself and the other does not ("" != "X") -- and
            # the loop below then skipped the undated side on `if not ep`, so the pair was torn
            # in half: one epoch-keyed edge, one bare edge, no longer mutual and no longer a
            # disagreement anybody would see. A real contradiction in the record was being
            # dissolved on half the evidence, which is the fabrication this module's docstring
            # refuses. An undated side is not a different date. (order 679368768c02)
            #
            # The two records place themselves at different points in the subject's history, so
            # they are longitudinal rather than contradictory. Re-key each dated side onto its
            # own node. Equal epochs are NOT split: two accounts of the same moment disagreeing
            # is a real disagreement, and re-keying it would only hide it behind a label.
            for (x, y), ep in (((w, loser), ea), ((loser, w), eb)):
                # No `if not ep: continue` guard any more -- the branch condition proves both
                # epochs are non-empty, and a guard that cannot fire is one more thing that looks
                # like it is doing work.
                n = out.pop((x, y))
                out[(ID.node(x, epoch=ep), y)] += n
            split += 1
            print(f"   split: {w} vs {loser}   [{ea}] / [{eb}]")
        elif bool(ea) != bool(eb):
            # ONE SIDE DATED, THE OTHER NOT -- its own case, counted like `unprobed` is, because
            # it is neither a settled disagreement nor a chronology. The pair is left standing
            # whole; splitting it would invent a date for the silent side by implication.
            half_dated += 1
            print(f"   left standing: {w} vs {loser} -- only one side dates itself "
                  f"([{ea or '-'}] / [{eb or '-'}]), and an undated side is not a different date")
        else:
            kept += 1
            why = f"both dated [{ea}]" if ea else "neither sentence dates itself"
            print(f"   left standing: {w} vs {loser} -- {why}")
    print(f"   {split} split by epoch, {kept} recorded as genuine disagreement"
          + (f", {half_dated} left whole -- only one side dated" if half_dated else "")
          + (f", {self_split} left whole -- a side's own sentences date differently"
             if self_split else "")
          + (f", {unprobed} NOT ADJUDICATED -- the probe did not run" if unprobed else ""))
    return out


def fit(edges, prior=0.0):
    """Bradley-Terry over the recorded outcomes, with Ford's condition reported either way."""
    wins = {k: v for k, v in edges.items()}
    if len(wins) < 3:
        return {"error": "too few edges to fit"}
    return RG.bradley_terry(wins, prior=prior)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=int)
    ap.add_argument("--workers", type=int, default=8)
    ap.add_argument("--harvest-only", action="store_true")
    ap.add_argument("--prior", type=float, default=0.0,
                    help="virtual contests per pair; >0 returns regularised strengths on a "
                         "disconnected graph instead of refusing")
    a = ap.parse_args()

    rows = harvest()
    print(f"contest sentences harvested: {len(rows):,}")
    if a.harvest_only:
        return 0

    edges, unmatched, prov = extract(rows, limit=a.limit, workers=a.workers)
    edges = adjudicate_mutuals(edges, prov)
    print(f"\ndistinct edges: {len(edges):,}   total recorded wins: {sum(edges.values()):,}")
    if unmatched:
        # A console PREVIEW, and now labelled as one: the whole roster is written to CHAIN.json
        # uncapped (see write_result), so this short list is a glance rather than the record.
        # It said "most common names that match nothing" over eight rows with no total, which
        # reads as the complete list of them.
        print(f"names that match nothing the library catalogues: {len(unmatched):,} distinct, "
              f"{sum(unmatched.values()):,} mentions. Commonest 8 (all of them are in "
              f"{os.path.basename(OUT)}):")
        for n, c in unmatched.most_common(8):
            print(f"   {c:>4}  {n}")

    res = fit(edges, prior=a.prior)
    if "error" in res:
        print(res["error"])
        return 1
    comps = res.get("components") or []
    print(f"\nentrants: {len(res['names']):,}")
    print(f"strongly connected components: {len(comps)}   "
          f"largest: {max((len(c) for c in comps), default=0)}")
    print(f"Ford's condition satisfied (one component covering all): {res['identified']}")
    print(f"deviance/df: {res['deviance_per_df']:.2f}   "
          f"(high = intransitive contests, a chord rather than a ladder)")
    print(f"undefeated (no finite strength): {len(res['undefeated'])}   "
          f"winless: {len(res['winless'])}")

    if res.get("strengths") is None:
        # The honest outcome on raw data, and on a corpus of unconnected fictions the usual one.
        # The edge list is still the finding, so it is written either way.
        print()
        # The refusal is the fit's whole explanation of why it returned nothing, and it was
        # printed cut to 240 characters with no marker -- a truncation of the one sentence a
        # reader is here for. Printed whole. (order 01df9304f918)
        print("NO STRENGTHS RETURNED -- " + (res.get("refusal") or ""))
        print()
        print("Re-run with --prior 0.5 for regularised strengths. They exist for every entrant,")
        print("but order ACROSS components by the prior's assumption rather than by evidence.")
        write_result(edges, res, unmatched)
        print(f"-> {OUT}   (edges kept; the graph is the result)")
        return 0
    order = sorted(zip(res["names"], res["strengths"], strict=True), key=lambda kv: -kv[1])
    big = max(comps, key=len) if comps else set()
    # LABELLED, LIKE THE OTHER PREVIEW THIRTY LINES UP (order 01df9304f918). This printed
    # "strongest inside the largest component:" over fourteen rows with no total and no word
    # that it was a preview, which reads as the complete ranking of the component -- the exact
    # fault the unmatched list above was corrected for, in the same function. It IS a genuine
    # preview: `write_result` persists `names` and `strengths` whole, so the fix is to say so.
    # The `n[:50]` cut went with it: node names carry ID.node's continuity and epoch suffixes
    # and are therefore longer than bare names, so fifty characters was cutting the part that
    # distinguishes two entrants with the same name.
    inside = [x for x in order if x[0] in big]
    print(f"\nstrongest inside the largest component: {len(inside):,} entrant(s). "
          f"Strongest 14 (all of them are in {os.path.basename(OUT)}):")
    for n, s in inside[:14]:
        print(f"   {s:.5f}  {n}")

    write_result(edges, res, unmatched)
    print(f"\n-> {OUT}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
