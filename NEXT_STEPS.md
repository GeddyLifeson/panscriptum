# Next Steps — priority queue for the next maintenance run

*Overwritten each run; history lives in HANDOFF.md. Run #6 wrote this on 2026-08-24 ~15:35.*

**Read this first.** Three things shape what is worth doing next run:

1. **fandom is still blocked at the socket** (probed 14:06Z: HTTP 000 after 21.3s; Wikipedia 200
   in 0.23s from the same second). It has been down across runs #5 and #6. Nothing fandom-facing
   can progress until it answers, and that is not a code fault.
2. **There are TWO writers on this tree.** An interactive session worked alongside run #6 and
   took the run guard mid-run. Assume it may happen again; read the guard AND `git -C
   C:\Users\imarl\panscriptum-export log --oneline` before believing you know the tree's state.
3. **Real money is involved now** (item 1 below). That outranks everything else here.

## 1. Verify first

1. **[M4 — money] Check `state/PAID_BURST.json` before anything else.** Run #6 found it at
   **598 used / 500 cap** and fixed the enforcement hole, but **deliberately did not reset the
   counter** — it is the evidence of ~$1.96 spent past a hard cap. Confirm with one command that
   the lane is genuinely shut now:
   `python -c "import sys;sys.path.insert(0,'src');import json,cascade_bridge as c;pb=json.load(open('state/PAID_BURST.json'));print(c.paid_lane_open(pb))"`
   → must print `False` while `used >= cap`. **If `used` has grown since 598, the fix is not
   holding and that is a top-severity finding.** The owner may have raised `cap` or set
   `enabled: false` in the meantime; either is fine, a *rising counter past a closed lane* is not.
2. **Confirm the seven re-classified sources actually re-derive.** Run #6 uncapped
   `genre.classify_source`, which changes the answer for Marvel, KibblesTasty, Bleach, Yorviing's,
   Dr. Firestorm's, Crash Bandicoot and Digimon. Nothing was regenerated — the change lands
   whenever the phase next runs. Check that `GENRES`/the shelving artifacts now carry the new
   values, and that no downstream artifact still holds the old ones. Marvel moving
   `post_apocalyptic → mythology` changes `register` and `priors`, i.e. prose voice.
3. **Confirm the 149 struck entries stay struck.** Run #6 made `excluded` durable
   (`batch_settled` + `phase_entrypass`). All 149 had already been flipped back to `catalogued`
   before the fix, so they are currently *in* the catalogue. Re-count them:
   they should stop being flipped, but they will not un-flip themselves. **Read m29 before
   re-running `cleanup.py --apply` to re-strike them** — that predicate has an open owner question.
4. **The pipeline was NOT bounced** and was mid-phase-2 on the old `pipeline.py`. Confirm it has
   since restarted onto the new `batch_settled`; if it is still the same PID as run #6 saw
   (34872), it is still running pre-fix code.
5. **Completeness now reads honestly with 164 rows** (the interactive session's work, not run
   #6's — its `land()` gained a `SHRINK_FLOOR` and the reachability gate now asks the API per
   host). The HIGH standard says `UNMEASURED -- 164 row(s), 0 measurable`. That is the correct
   answer *while fandom is down*. **When fandom answers, this is the first thing to watch**: rows
   should convert from `unreliable` to real denominators and the standard should print a genuine
   percentage. Until then it is not measurable, and that is not a fault to fix.

## 2. Human decisions needed (owner)

6. **[M4] The burst lane itself** — 598/500. Raise `cap`, set `enabled: false` (which now works),
   or delete the file (now safe; before run #6 it was the worst option, silencing the counter
   without stopping the spend). Retire the lane entirely?
7. **[m29] `cleanup.py`'s `_EMPTY_MECHANIC` predicate** strikes an entry on *empty description +
   name ending in* `variant|feature|trait|slot|...`. An empty description is a signal this project
   has repeatedly shown to be unreliable, and Loki *Variants* are real entities. **This matters
   more now that run #6 made exclusions permanent.** Decide before `--apply` runs again.
8. **[m26] The completeness audit cannot see 46 of 210 sources** (its `todo` filters on a
   fandom-only `subdomain(h)`). Should it measure Wikipedia- and other-hosted sources, or be
   renamed to say what it actually measures? Raised by the interactive session, still open.
9. **[m25 / m16 / dashboard `findings` cap of 12] — ONE decision, three sites: does Hard Rule 0
   bind diagnostics and run logs, or only reader-facing listings?** Carried from run #5 and still
   the highest-leverage single ruling available; it would also settle how to treat
   `overwatch`'s `WATCH.md` display slices and `health.check_caches`'s 200-file sample.
10. **[m12] `thread_integrity.py`'s asymmetric/dangling detection is structurally unreachable.**
    Is it meant to compare implied threads against a separately-recorded DIRECTED thread graph it
    is not currently given? Not a one-line fix either way.
11. **[m13] `phase_synthesis`'s 14-entity ceiling sample** can clamp a whole source to a lesser
    band if the true strongest entity is not sampled. Raise, re-rank, or accept. **Note this is
    the same family as the two caps run #6 removed** — a ranked-then-truncated list deciding an
    answer — so the evidence standard is now set: diff the whole corpus, do not reason about it.
12. **[M1] dandwiki.com** — browser-UA HTML reader vs. owner-supplied text. Politeness/ToS call,
    open since run #1. `health --preflight` keeps reporting its cache all-empty until decided;
    that FAIL is this decision, not a fault.
13. **[m24] `cascade_bridge.dead_forever`** buries buckets on `no such model` / `needs billing` /
    `bad key`, which its own docstring's "permanent codes only" rule does not cover. Inert today.
    Document those three as permanent, or drop them?
14. **[m23] job logs truncated on every restart** — blocked a diagnosis in runs #4 and #5. Run #6
    worked around it again by transcribing `state/overwatch.log` *before* bouncing the job. Fix is
    small but changes an operational convention; wants an owner glance.
15. **Permanently hostless roll entries** (Clockwork Angels, Twilight Imperium, HAWX, …) — stay on
    the roll as owner-supplied-text candidates, or come off? Also **the 91 DECIDED spine codes**
    from the interactive session are **still not written to `CHARTER_SPINE_CODES.json`** — and note
    that session's finding that the JSON has no writer in `src/`, so rulings must land in the
    charter appendix first or they are erased on the next re-derive.

## 3. Small implementable items (no decision needed)

16. **[m27] The run guard's heartbeat does not check whose record it is refreshing.** Run #6 spent
    ~45 minutes refreshing another agent's record, making a finished run look live. Refuse to
    refresh a record whose `agent` is not ours, loudly. **Do this one early** — every future run
    depends on the guard, and this is the flaw most likely to cause a real collision.
17. **[m28] `overwatch.load()` turns a corrupt ledger into an empty one**, discarding every open
    finding and the round counter. `health.flush()` handles the identical case properly (preserve
    as `.corrupt`, say so on stderr) — copy that.
18. **[m30] Two checks that cannot fail**: `custodes.convene`'s `covers_every_reading` is true by
    construction, and `sevenfold`'s `OVER SPAN` can never print because `seams()` already clamps to
    `SPAN`. Harmless, but they present as verification while being incapable of catching anything.

## 4. Surface rotation for the next audit fan-out

Covered, do **not** re-read unless the diff touched them: the round-1 full-codebase audit and
evening sweep (`handoff/AUDIT_*.md`); run #2's four surfaces (derivation/rigor/handbuilt;
sweep/endpoint/wiki_source/coverage; build_terminal/weave/weave_index/navtree/render;
pipeline/ledger/thread_integrity); run #3's two (ingest_doc/manifest_builder/generate/address/
catalog; foreman/standards/publish/overnight/dashboard); run #5's three (assay/magnitude/identity;
hostcheck/scout/tuning/compress_store; read/feats/estate/worldseed/onomast); **run #6's four**
(health/overwatch/silence; catalogue_web/backfill/cleanup; custodes/tiers/sevenfold/grounding;
plus cascade_bridge's widen/paid path read directly).

**Not yet audited line-by-line** — pick from here: `chain.py`, `module_index.py`, `local_agent.py`,
`address_space.py`, `profile.py`, `burgs.py`, `tells.py`, `style_audit.py`, `audit.py`,
`descending_ladder.py`, `cosmography.py`, `genre.py` (only its cap was touched), `reference.py`,
`resync_roll.py`, `retry_synthesis.py`, `pick_model.py`, and `address.py` + `completeness.py` +
`foreman.py` **as they now stand after the interactive session's promotion-ladder work** — those
three changed substantially on 2026-08-24 and their new code has had no line-by-line pass.

Three findings from run #5's audits remain un-actioned and still deserve a second opinion:
`hostcheck`'s `judgeable` flag is computed and respected by `standards.py` but ignored by
hostcheck's own two consumers; `onomast.coin_well_formed`'s fallback skips both its quality and
uniqueness checks; `feats._unwrap_templates` miscounts brace nesting on `{{{`.

## 5. Lessons worth keeping

- **Measure the corpus; do not reason about the corpus.** Run #6's two cap removals were both
  justified by a full 210-record diff, and the diff is what showed one cap changed seven answers
  while the other changed none. Either conclusion reached by argument would have been a guess.
  It cost minutes on 14 processes.
- **A fixture that fits inside the bug's threshold tests nothing.** §19i's first version was 18,000
  characters against a 120,000-character cap — it passed against the buggy code. This is the run #5
  lesson recurring in a new shape: *pin the arithmetic, then falsify the pin against the pre-fix
  code.* Both new sections were falsified that way before shipping.
- **A comment naming the right file is not the same as fixing it.** `foreman.py:237` states
  plainly that every process writes `failures.json` through `health.flush()` — and m18 hardened
  foreman's own writes while leaving `health.flush()` untouched for a day. When a fix is motivated
  by a shared file, check every writer of that file, not the one you happened to be reading.
- **"Written by X, read by nothing" is a finding, not a curiosity.** `excluded` looked like a
  harmless annotation; grep proved nothing consumed it, and the corpus proved 149 of 149 decisions
  had been silently reverted. When a field records a DECISION, find its reader or it has none.
