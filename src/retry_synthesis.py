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
    """Land the side file, MERGING with what is already on disk. -> the merged mapping.

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
    """
    merged = load_side()
    merged.update(d)
    silence.write_json(SIDE, merged, indent=2, ensure_ascii=False)
    return merged


def failed_sources():
    with open(PL.STATE, encoding="utf-8") as f:
        st = json.load(f)
    return sorted(st.get("failed", {}).get("synthesis", {}))


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
        got = PL.ask(c, PL.SYNTH_SYSTEM, prompt, PL.SYNTH_SCHEMA, timeout=420)
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
    args = ap.parse_args()
    if args.merge:
        return do_merge()

    c = PL.cfg()
    want = set(failed_sources())
    side = load_side()
    print(f"{len(want)} sources failed synthesis; {len(side)} already retried")

    todo = [(p, r) for p, r in PL.records()
            if r["source"] in want and r["source"] not in side and not r.get("synthesis")]
    print(f"{len(todo)} to do now\n")

    for path, rec in todo:
        src = rec["source"]
        print(f"  {src:<44}", end="", flush=True)
        got = synthesise(c, rec)
        if got is None:
            print("STILL FAILING")
            continue
        side[src] = got
        # Take the MERGED mapping back, so this run's own tally counts what is actually on
        # disk rather than only what this process rescued -- see `save_side`.
        side = save_side(side)
        print(f"{got['provisional_magnitude']:<10} {got['ceiling_entity']}")

    print(f"\nwrote {len(side)} results to data/SYNTHESIS_RETRY.json")
    print("merge with:  python src/retry_synthesis.py --merge   (pipeline must be stopped)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
