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


def write_result(edges, res, unmatched=None):
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
        "unmatched": (unmatched.most_common(40) if hasattr(unmatched, "most_common")
                      else (unmatched or [])),
    }
    with open(OUT, "w", encoding="utf-8") as f:
        json.dump(out, f, indent=1, ensure_ascii=False)
    return out


HARVEST_IDX = os.path.join(HERE, "state", "chain_harvest_idx.json")


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
        idx = {}
    live, changed = set(), 0
    for base in ("readfeats", "feats"):
        for fp in glob.glob(os.path.join(HERE, "data", base, "**", "*.json"), recursive=True):
            rel = os.path.relpath(fp, HERE)
            live.add(rel)
            try:
                mt = os.path.getmtime(fp)
            except OSError:
                continue
            cached = idx.get(rel)
            if cached and cached.get("mt") == mt:
                continue
            try:
                with open(fp, encoding="utf-8") as f:
                    d = json.load(f)
            except Exception:
                silence.note("chain.py:91")
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
                _, cont = ID.identify(page, host)
                found.append({"entity": ent, "sentence": t, "page": page,
                              "host": host, "continuity": cont})
            idx[rel] = {"mt": mt, "rows": found}
            changed += 1
    # A file that vanished takes its contests with it -- an index must never outlive its corpus.
    for rel in [k for k in idx if k not in live]:
        del idx[rel]
        changed += 1
    if changed:
        try:
            tmp = HARVEST_IDX + ".tmp"
            with open(tmp, "w", encoding="utf-8") as f:
                json.dump(idx, f, ensure_ascii=False)
            silence.replace_retry(tmp, HARVEST_IDX)
        except Exception:
            silence.note("chain.py:harvest-idx")
    rows, seen = [], set()
    for rel in sorted(idx):
        for r in idx[rel].get("rows", []):
            k = (r.get("entity"), (r.get("sentence") or "")[:120])
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
        silence.note("chain.py:155")
        pass
    try:
        import pipeline as P
        import read as R
        return P.ask(R.config(), system, prompt, schema, timeout=300)
    except Exception:
        silence.note("chain.py:161")
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
    done = {"n": 0, "pairs": 0, "kept": 0}

    def work(chunk):
        lines = [f"[{i}] (filed under: {r['entity']}) {r['sentence']}"
                 for i, r in enumerate(chunk, 1)]
        got = _ask(SYSTEM, "SENTENCES:\n" + "\n".join(lines), SCHEMA)
        local = []
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
                silence.note("chain.py:252")
                continue
            if not (0 <= pos < len(chunk)):
                continue
            src = chunk[pos]
            w, l = (o.get("winner") or "").strip(), (o.get("loser") or "").strip()
            if not w or not l or w.lower() == l.lower():
                continue
            wk, lk = WI.norm(w), WI.norm(l)
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
                for side, k in ((w, wk), (l, lk)):
                    if k not in idx:
                        unmatched[side[:40]] += 1
        with lock:
            done["n"] += len(chunk)
            done["pairs"] += len((got or {}).get("outcomes", []))
            for e, src in local:
                edges[e] += 1
                prov[e].append(src)
                done["kept"] += 1
            if done["n"] % 200 < batch:
                print(f"   {done['n']:>6}/{len(rows)}  pairs {done['pairs']:>5}  "
                      f"kept {done['kept']:>5}", flush=True)

    chunks = [rows[i:i + batch] for i in range(0, len(rows), batch)]
    with ThreadPoolExecutor(max_workers=workers) as ex:
        list(ex.map(work, chunks))
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

    So each mutual pair's two sentences are dated (identity.epoch_of, one model call each), and
    where they date differently the winner is re-keyed onto an epoch-specific node. Where neither
    sentence dates itself, the pair is LEFT STANDING: that is a real disagreement in the record,
    and dissolving it with an invented chronology would be the same fabrication this library
    exists to refuse.

    Only mutual pairs are dated. A sentence that contradicts nothing gains nothing from a
    timestamp, and there are eleven thousand of those.
    """
    mutual = [(w, l) for (w, l) in edges if (l, w) in edges and (w, l) < (l, w)]
    if not mutual:
        print("\nmutual pairs: none -- no contest is recorded in both directions")
        return edges
    # Was indented one level deeper, i.e. after the `return` inside `if not mutual` -- so the
    # one line announcing that mutual pairs are being adjudicated could only ever run when
    # there were none. The dating below has always executed; nothing said so.
    print(f"\nmutual pairs: {len(mutual)} -- dating each side before it reaches the fit")
    out = collections.Counter(edges)
    split = kept = 0
    for (w, l) in mutual:
        sa = (prov.get((w, l)) or [{}])[0].get("sentence", "")
        sb = (prov.get((l, w)) or [{}])[0].get("sentence", "")
        ea, eb = ID.epoch_of(sa), ID.epoch_of(sb)
        if ea != eb:
            # The two records place themselves at different points in the subject's history, so
            # they are longitudinal rather than contradictory. Re-key each dated side onto its
            # own node. Equal epochs are NOT split: two accounts of the same moment disagreeing
            # is a real disagreement, and re-keying it would only hide it behind a label.
            for (x, y), ep in (((w, l), ea), ((l, w), eb)):
                if not ep:
                    continue
                n = out.pop((x, y))
                out[(ID.node(x, epoch=ep), y)] += n
            split += 1
            print(f"   split: {w} vs {l}   [{ea or '-'}] / [{eb or '-'}]")
        else:
            kept += 1
            why = f"both dated [{ea}]" if ea else "neither sentence dates itself"
            print(f"   left standing: {w} vs {l} -- {why}")
    print(f"   {split} split by epoch, {kept} recorded as genuine disagreement")
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
        print("most common names that match nothing the library catalogues:")
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
        print("NO STRENGTHS RETURNED -- " + (res.get("refusal") or "")[:240])
        print()
        print("Re-run with --prior 0.5 for regularised strengths. They exist for every entrant,")
        print("but order ACROSS components by the prior's assumption rather than by evidence.")
        write_result(edges, res, unmatched)
        print(f"-> {OUT}   (edges kept; the graph is the result)")
        return 0
    order = sorted(zip(res["names"], res["strengths"]), key=lambda kv: -kv[1])
    big = max(comps, key=len) if comps else set()
    print("\nstrongest inside the largest component:")
    for n, s in [x for x in order if x[0] in big][:14]:
        print(f"   {s:.5f}  {n[:50]}")

    write_result(edges, res, unmatched)
    print(f"\n-> {OUT}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
