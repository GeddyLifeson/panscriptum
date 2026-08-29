#!/usr/bin/env python3
"""
RETRY the sources whose synthesis failed, WITHOUT touching anything the running pipeline owns.

Twelve sources -- Dragon Ball Z and Dune among them -- carry `"ollama failure"` in the pipeline's
failed-set. They failed during the memory-thrashing window, not because anything about them is
hard, and the synthesis phase has since been marked done, so the pipeline will never revisit them
on its own. Left alone they would reach the write phase with no ceiling and no band.

THE CONSTRAINT THAT SHAPES THIS FILE
------------------------------------
The pipeline is still running. It owns state/PIPELINE_STATE.json and it read-modify-writes
data/records/*.json as phase 2 bands each source. A second writer racing it on either would lose
updates or truncate a record mid-write.

So this script writes NEITHER. It reads records, calls the SAME already-loaded Ollama instance
(no new model, no extra VRAM -- requests just queue behind the pipeline's), and appends results to
data/SYNTHESIS_RETRY.json, which nothing else touches. Merging happens later, once the pipeline is
idle, via --merge. That keeps the fix completely off the critical path.
"""
import argparse
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)

import pipeline as PL          # noqa: E402
import silence                 # noqa: E402

SIDE = os.path.join(ROOT, "data", "SYNTHESIS_RETRY.json")


def load_side():
    if os.path.exists(SIDE):
        with open(SIDE, encoding="utf-8") as f:
            return json.load(f)
    return {}


def save_side(d):
    """Land the side file, MERGING with what is already on disk. -> (merged mapping, landed?).

    `silence.write_json`, not a hand-rolled `path + ".tmp"`: the fixed tmp name collides when
    two processes write at once, and the bare `os.replace` raises on the Windows lock this
    project hits routinely -- here that would abort the whole retry run mid-pass. Run #31.

    AND THE CONTENT RACE THE TMP-NAME FIX DID NOT COVER, found by the run #33 sweep. Run #31
    was already reasoning about two `retry_synthesis.py` processes writing at once, and closed
    the collision on the temp FILENAME. The collision on the FILE'S CONTENTS stayed open:
    `main()` reads `side` once at startup and then whole-file overwrites it after every
    rescued source, so two concurrent invocations each publish their own separately-growing
    copy and each save silently drops every entry the other had already persisted. Nothing in
    this file prevents or detects a second invocation, and the loss is invisible -- the file
    stays well-formed and the run prints a confident "wrote N results" for its own N. These
    are the twelve sources the pipeline will never revisit on its own; a dropped entry here is
    a source that reaches the write phase with no ceiling and no band, which is the exact
    outcome this script exists to prevent.

    Re-reading at save time narrows the window from the whole run to the microseconds between
    this read and the replace. That residual is deliberately NOT papered over with a lock: a
    lock file is another thing to leave behind on a killed run, and the honest statement is
    that this script is still meant to be run once at a time. What it now guarantees is that a
    second runner costs at most one overlapping entry rather than every entry it ever wrote.

    AND THE VERDICT ITSELF, which the two paragraphs above both reasoned about losing entries
    and then threw away. `write_json` answers whether the rename LANDED -- on Windows it is
    denied whenever any reader holds SYNTHESIS_RETRY.json open, which is the ordinary case
    here, not an exotic one -- and this returned the in-memory `merged` either way. The caller
    then printed the rescued magnitude and moved to the next source, so a denied write read
    exactly like a successful one while the model call that produced it was gone: nothing
    re-runs it, `--merge` never sees it, and the source arrives at the write phase with no
    ceiling and no band. That is the outcome named in this module's own opening paragraph as
    the thing it exists to prevent. The verdict now rides back with the mapping.
    """
    merged = load_side()
    merged.update(d)
    ok = silence.write_json(SIDE, merged, indent=2, ensure_ascii=False)
    if not ok:
        silence.note("retry_synthesis.py:save_side-denied")
    return merged, ok


def failed_sources():
    with open(PL.STATE, encoding="utf-8") as f:
        st = json.load(f)
    return sorted(st.get("failed", {}).get("synthesis", {}))


def stranded_sources():
    """Sources with NO synthesis that the pipeline will never revisit. -> sorted [names].

    THE FAILED-SET IS NOT THE POPULATION THAT NEEDS RESCUING, and measuring it is what showed
    that. On 2026-08-28 thirty-one records carried a null synthesis -- 191,029 entries, Marvel
    (59,170) and DC (55,560) among them -- and the pipeline's failed set held exactly TWO names.
    The other twenty-nine never failed anything. Their blocks were written correctly and then
    CLOBBERED by the catalogue-side writer, which returned "synthesis": None for a wiki lead
    paragraph and landed that None on top of the pipeline's work (order 3c7c8a6e9102, and the
    same defect was still live on the pipeline's own writer until it was fixed on 2026-08-27).

    So this tool, whose entire job is "sources the pipeline will never revisit on its own", could
    see two of the thirty-one that qualified. A rescue tool that selects on the CAUSE rather than
    on the CONDITION misses every casualty whose cause it did not anticipate -- and the whole
    reason these are stranded is that `phase_synthesis` skips any source already in its done-keys,
    which is true of a clobbered source exactly as it is true of a failed one.

    Selecting on the condition instead: no synthesis block, and entries to reason over. A source
    with no entries has nothing to synthesise FROM and is not stranded, it is empty.
    """
    out = []
    for _p, rec in PL.records():
        if rec.get("synthesis"):
            continue
        if not (rec.get("entries") or []):
            continue
        out.append(rec["source"])
    return sorted(out)


def synthesise(c, rec):
    """Same nomination method as `phase_synthesis`, because it now literally shares the code.

    THE DOCSTRING HERE USED TO SAY "byte-identical prompt construction to phase_synthesis"
    AND IT WAS NOT TRUE (found run #31). This function built a single
    `sorted(entries, by description length)[:14]` block and never consulted a mined feat --
    the construction `phase_synthesis` was rewritten AWAY from under the owner's m13 ruling of
    2026-08-24 ("FIX IT ALL"). So a source that failed the main phase for an infrastructure
    reason -- which is the entire population this script exists to rescue -- was re-scored by a
    weaker method than its neighbours, which is the exact outcome the old docstring promised
    could not happen. Worse, it was Hard-Rule-0-shaped: rank the cast, keep fourteen, and let
    a source's true ceiling fall outside the window while the run reports success.

    Both the block rule and the prompt text now come from `pipeline`, so the two cannot drift
    apart again. Best band across blocks wins, exactly as in the main phase.
    """
    src = rec["source"]
    chunks, feats_for = PL.synthesis_blocks(rec)
    best = None
    for ci, sample in enumerate(chunks):
        prompt = PL.synthesis_prompt(src, sample, feats_for, ci, len(chunks),
                                     len(rec["entries"]))
        # POOL FIRST, LOCAL SECOND -- the same transport `phase_synthesis` uses, which this
        # function is otherwise at pains to match. It called `PL.ask` (Ollama only) while the
        # phase it exists to stand in for calls `PL.ask_pool_first`, and that divergence is the
        # same class of drift this docstring already records being burned by once: the prompt
        # construction was made to share code precisely so the two could not answer differently,
        # and then the two asked DIFFERENT MODELS anyway.
        #
        # It stopped being cosmetic on 2026-08-28. The Ollama runner had been pinned and
        # saturated for 31 hours -- every request timing out or rejected with "maximum pending
        # requests exceeded" -- while two groq buckets in the cloud pool were answering in under
        # a second. So the main phase would have succeeded on exactly the sources this rescue
        # tool could not touch, which is the precise inversion of what a rescue tool is for.
        got = PL.ask_pool_first(c, PL.SYNTH_SYSTEM, prompt, PL.SYNTH_SCHEMA, timeout=420,
                                tag="retry_synthesis")
        if got is None:
            continue

        band = (got.get("magnitude") or "").strip()
        m = re.match(r"^(M(?:10|[0-9]))\b", band)
        band = m.group(1) if m else "unassayed"

        ev = (got.get("evidence") or "").strip()[:600]
        # The pipeline's own invariant: no feat, no band. A retry must not smuggle in a band
        # that the main phase would have refused.
        if not PL.valid_scale_note(ev):
            band = "unassayed"

        rank = int(band[1:]) if band != "unassayed" else -1
        if best is None or rank > best[0]:
            best = (rank, got, band, ev)

    if best is None:
        return None
    _, got, band, ev = best

    return {
        "ceiling_entity": (got.get("ceiling_entity") or "").strip(),
        "provisional_magnitude": band,
        "evidence": ev,
        "rationale": (got.get("rationale") or "").strip()[:900],
        "method": ("Band-only nomination by local model over the source's own catalogued "
                   "entries; retried after an infrastructure failure, same prompt and same "
                   "invariants as the main synthesis phase."),
    }


def do_merge():
    """Fold the side file into the records. Run ONLY when the pipeline is stopped."""
    side = load_side()
    if not side:
        print("nothing to merge")
        return 0
    merged = skipped = denied = 0
    for path, rec in PL.records():
        src = rec["source"]
        if src not in side:
            continue
        if rec.get("synthesis"):
            skipped += 1
            continue
        rec["synthesis"] = side[src]
        # THROUGH THE SANCTIONED WRITER. This wrote `data/records/*.json` itself -- a bare
        # truncating temp plus `os.replace`, bypassing `pipeline.write_record` and therefore the
        # entire two-writer contract that verify_math §18c exists to enforce.
        #
        # The bypass was not merely procedural. `write_record` re-reads the file and MERGES,
        # precisely so a stale in-memory copy cannot be published over a fresher disk one; this
        # loop holds a `rec` from `PL.records()` taken before an unbounded number of model calls,
        # so on a source re-catalogued in the meantime it wrote the OLD entry list back whole --
        # the 30,207-entries-to-1,051 revert `write_record`'s docstring names, performed by the
        # one caller that had opted out of the guard. The "run ONLY when the pipeline is stopped"
        # note in the docstring above is a convention, and nothing enforced it. (run #26)
        if not PL.write_record(path, rec):
            print("  MERGE DENIED  %s -- record left as it was on disk; rerun the merge"
                  % src, flush=True)
            denied += 1
            continue
        merged += 1
    print(f"merged {merged}, skipped {skipped} (already had synthesis), "
          f"{denied} denied (write refused -- rerun the merge)")
    return 0


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--merge", action="store_true",
                    help="fold results into records; run only with the pipeline stopped")
    ap.add_argument("--only", nargs="*", metavar="SOURCE",
                    help="retry only these named sources")
    ap.add_argument("--smallest", type=int, metavar="N",
                    help="pilot: do the N smallest pending sources first, to prove the "
                         "transport before committing to the largest")
    args = ap.parse_args()
    if args.merge:
        return do_merge()

    c = PL.cfg()
    failed = set(failed_sources())
    stranded = set(stranded_sources())
    want = failed | stranded
    side = load_side()
    print(f"{len(failed)} failed synthesis, {len(stranded)} stranded without one "
          f"({len(want)} together); {len(side)} already retried")

    todo = [(p, r) for p, r in PL.records()
            if r["source"] in want and r["source"] not in side and not r.get("synthesis")]
    if args.only:
        todo = [(p, r) for p, r in todo if r["source"] in set(args.only)]
    if args.smallest:
        # A PILOT ORDER, not a cap: `--smallest N` is for proving the transport end to end on
        # cheap sources before committing to Marvel's 59,170 entries. The full run is the
        # default and takes no argument, so nobody reaches for a truncation by accident.
        todo = sorted(todo, key=lambda pr: len(pr[1].get("entries") or []))[:args.smallest]
    print(f"{len(todo)} to do now\n")

    # True until a save is refused; a run that saves nothing has nothing outstanding.
    landed = True
    for path, rec in todo:
        src = rec["source"]
        print(f"  {src:<44}", end="", flush=True)
        got = synthesise(c, rec)
        if got is None:
            print("STILL FAILING")
            continue
        side[src] = got
        # Take the MERGED mapping back, so this run's own tally counts what is actually on
        # disk rather than only what this process rescued -- see `save_side`. The second half
        # of that return says whether it reached disk at all; a rescue that did not land must
        # not print like one that did, because nothing re-runs the model call behind it.
        side, landed = save_side(side)
        if not landed:
            # Not necessarily lost for good: every save re-writes the WHOLE accumulated map, so
            # the next source's save carries this one too. It is lost if the run ends here.
            print("SAVE DENIED -- %s is NOT on disk (replace refused); the next successful "
                  "save this run carries it, but if the run ends now this synthesis is gone "
                  "and the source must be rerun" % src)
            continue
        print(f"{got['provisional_magnitude']:<10} {got['ceiling_entity']}")

    # `len(side)` is this process's memory, not the file. Saying "wrote N" when the last save
    # was refused is the same lie the per-source line above was fixed for, one level up.
    if landed:
        print(f"\nwrote {len(side)} results to data/SYNTHESIS_RETRY.json")
    else:
        print(f"\n{len(side)} results in memory, but the LAST save to "
              f"data/SYNTHESIS_RETRY.json was REFUSED -- the file is behind by at least the "
              f"final source. Rerun; anything missing is retried.", file=sys.stderr)
    print("merge with:  python src/retry_synthesis.py --merge   (pipeline must be stopped)")
    return 0 if landed else 1


if __name__ == "__main__":
    sys.exit(main())
