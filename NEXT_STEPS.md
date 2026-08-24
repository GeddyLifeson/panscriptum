# Next Steps — priority queue for the next maintenance run

*Overwritten each run; history lives in HANDOFF.md. Run #7 wrote this on 2026-08-24 ~11:45 local.*

**Read this first.** Three things shape what is worth doing next run:

1. **fandom is still blocked at the socket.** Down across runs #5, #6 and #7. Nothing
   fandom-facing can progress until it answers, and it is not a code fault. `health --preflight`
   reports it every run; that FAIL is the outage, not a bug to fix.
2. **The free cloud pool has collapsed to 2 of 36 answering** (`reprove_pool`, 11:14 local).
   That is *below* `ask_pool_first`'s `>= 3` gate, so the phases currently run local-only. This
   matters for verifying item 2 below: while the pool is under the gate, the cloud path is not
   exercised at all and a fix to it cannot be observed working.
3. **Run #6 shipped a correct fix that production never read** (genre — see the run #7 handoff).
   When you fix something, check what actually consumes it before recording it as landed.

## 1. Verify first

1. **[m31 — the one that matters] Did the entrypass fix actually stop the 0/20 batches?**
   Run #7 changed `ask_pool_first` so an unusable cloud answer falls through to local, bounced
   the pipeline onto it (PID 34872 → **3056**, 11:17 local), and could NOT reproduce the original
   failure because the pool had already dropped below the gate. So the fix is **verified by
   construction and by unit test, not by observation.** Check:
   `grep -c "returned 0/20" state/pipeline_auto.log` and
   `grep "unusable shape" state/pipeline_auto.log`.
   * Batches now returning **20/20** (or any non-zero) = fixed.
   * Still **0/20** with no "unusable shape" line = the cause was NOT the pool path, and the real
     cause is still open. That would be a top-severity finding; do not assume the diagnosis.
   * "unusable shape" lines present = the fix is firing and the cloud really was returning junk.
   **Note `state/pipeline_auto.log` was truncated by the bounce (m23);** run #7's copy of the
   pre-bounce log is in the scratchpad but that is session-scoped and probably gone. The four
   original `0/20` lines are transcribed in the run #7 handoff entry.
2. **Did the genre regeneration reach the things that read it?** `data/GENRES.json` was rewritten
   this run and **12 of 209 sources changed genre, 11 changed register**. Its consumers are
   `profile.build_all` (genre and register are encoded into every world profile string) and
   `navtree` (tier naming). Confirm those now reflect the new values — in particular Marvel,
   whose register moved `compact → classical`. Nothing was regenerated downstream.
3. **Two keys were dropped from `GENRES.json` by re-derivation** — `Lost Mines of Phandelver` and
   `the Witch Tradition`, both sources with no record in the corpus. Flagged rather than silent.
   If either should still be classified, the source needs a record first.
4. **[M4 — money] Confirm the lane is still shut.** Run #7 verified `used` is still **598/500**,
   unchanged from run #6, and `paid_lane_open()` is False. Re-check with one command:
   `python -c "import sys;sys.path.insert(0,'src');import json,cascade_bridge as c;pb=json.load(open('state/PAID_BURST.json'));print(c.paid_lane_open(pb))"`
   → must print `False` while `used >= cap`. **A counter that has grown past 598 means the fix is
   not holding and that is top severity.**
5. **The 149 struck entries are still all `catalogued: True`** — re-verified this run, unchanged,
   none re-flipped. They will not un-flip themselves. **Read m29 before running `cleanup.py
   --apply`**, which is what would re-strike them, and which is still an open owner question.

## 2. Human decisions needed (owner)

6. **[M4] The burst lane** — 598/500, closed by the cap rather than by intent. Raise `cap`, set
   `enabled: false` (which now works), delete the file (now safe), or retire the lane.
7. **[NEW] Should `data/GENRES.json` have an automated writer?** It is the only bridge from
   `genre.py` into the running system and it has none — only the manual `genre.py --write`, which
   had not been run since 2026-08-20, so a fix to the classifier changes nothing until a person
   remembers. `grounding`'s equivalent is called by `pipeline.py:1274` every phase and needs no
   one. Either genre joins the phases, or the hand-run step is deliberate curatorial control and
   should be written down as such. Run #7 regenerated the artifact but did NOT wire a job,
   because that changes a cadence.
8. **[m29] `cleanup.py`'s `_EMPTY_MECHANIC` predicate** strikes on *empty description + name
   ending in* `variant|feature|trait|slot|...`. An empty description is a signal this project has
   repeatedly shown to be unreliable, and Loki *Variants* are real entities. Exclusions are
   permanent since run #6, so a wrong strike now sticks. Decide before `--apply` runs again.
9. **[m26] The completeness audit cannot see 46 of 210 sources** (`todo` filters on a fandom-only
   `subdomain(h)`). Measure the Wikipedia- and other-hosted sources, or rename the measure to say
   what it actually covers?
10. **[m25 / m16 / dashboard `findings` cap of 12] — ONE decision, three sites: does Hard Rule 0
    bind diagnostics and run logs, or only reader-facing listings?** Carried from runs #5 and #6
    and still the highest-leverage single ruling available. **Run #7 added a data point that may
    settle it**: `FOR_OWNER.md` was capped at 3 URLs per blocked source, and that one was
    obviously wrong because the listing fed a *human decision*. "Does anything downstream act on
    the truncated list?" may be the workable test.
11. **[m38] `foreman._function_source` resolves symbols by bare name, no uniqueness check** —
    it can hand the model lane the wrong same-named function and, with `--patch` live, overwrite
    it. Refuse an ambiguous symbol, or honour the class qualifier `overwatch` already emits?
12. **[m39] `scout.sweep(limit=4)`** can starve lower-ranked hostless sources forever — the
    ranking is deterministic and recomputed each round. Uncapping changes per-round load.
13. **[m12] `thread_integrity.py`'s asymmetric/dangling detection is structurally unreachable.**
    Is it meant to compare implied threads against a separately-recorded DIRECTED thread graph it
    is not currently given? Not a one-line fix either way.
14. **[m13] `phase_synthesis`'s 14-entity ceiling sample** can clamp a whole source to a lesser
    band if the true strongest entity is not sampled. Raise, re-rank, or accept.
15. **[M1] dandwiki.com** — browser-UA HTML reader vs. owner-supplied text. Politeness/ToS call,
    open since run #1. The `health --preflight` cache FAIL is this decision, not a fault.
16. **[m24] `cascade_bridge.dead_forever`** buries buckets on `no such model` / `needs billing` /
    `bad key`, which its docstring's "permanent codes only" rule does not cover. **Run #7 watched
    a single `CB.ask` bury nine buckets** — five on HTTP 402, four on HTTP 404 for LOCAL ollama
    models that are simply not pulled right now (qwen3:30b, llama3.1, gemma3:12b, qwen2.5:14b).
    Those four are not permanent: `ollama pull` restores them. Worth revisiting with that in hand.
    (The removals are in-memory per process and did not persist — `POOL_PROOF.json` was untouched.)
17. **[m23] job logs truncated on every restart** — bit run #7 again (the pipeline log was lost on
    bounce and had to be transcribed first). Fix is small (`"a"` plus a session separator, or
    rotate to `<job>.N.log`) but changes an operational convention and the dashboard's
    `_tail_match` readers assume one current file.
18. **[m30 follow-on] `custodes.convene` could report something real.** `covers_every_reading` is
    true by construction. The informative quantity — whether the **1.96·sd band alone** covered
    every reading, i.e. whether the widening-to-cover had to fire — is currently invisible. Adding
    it is a contract addition, not a repair, so it is a question.
19. **Permanently hostless roll entries** (Clockwork Angels, Twilight Imperium, HAWX, …) — stay on
    the roll as owner-supplied-text candidates, or come off? Note **catalogued sources with no
    host grew 16 → 20** this week. Also the **91 DECIDED spine codes** from the interactive session
    are **still not written to `CHARTER_SPINE_CODES.json`**, and that file has no writer in `src/`,
    so rulings must land in the charter appendix first or they are erased on the next re-derive.

## 3. Small implementable items (no decision needed)

20. **[m37] Confirm or refute: does anything read `data/CHAIN.json`?** An audit subagent reported
    that `chain.write_result` persists the Bradley-Terry strengths and the Ford's-condition
    verdict every cycle and that **no reader exists** — meaning the cross-check the module calls
    its entire purpose never runs against the Assay. **Not independently verified.** Same agent
    flagged `chain.py:191`'s `sentence[:120]` dedup key (a Hard Rule 0 truncation that decides
    which contests exist), a bare `open(OUT,"w")`, and a discarded `replace_retry`. Verify each
    against source before touching anything.
21. **`pick_model.py` tells the operator "config.yaml updated" without checking the write.**
    `save_config` discards `replace_retry`'s boolean and `main()` prints success unconditionally —
    the same family run #7 fixed in four other places (m33-m35). Reported by an audit agent; the
    line numbers were right in the other cases, but verify before fixing.
22. **`local_agent`'s pyflakes gate ignores `returncode`** (only checks stdout for "undefined
    name"), so a pyflakes that fails to execute passes the gate silently. The very next
    subprocess call does check `returncode`, which makes this look like an oversight.

## 4. Surface rotation for the next audit fan-out

Covered, do **not** re-read unless the diff touched them: the round-1 full-codebase audit and
evening sweep (`handoff/AUDIT_*.md`); run #2's four surfaces; run #3's two; run #5's three
(assay/magnitude/identity; hostcheck/scout/tuning/compress_store; read/feats/estate/worldseed/
onomast); run #6's four (health/overwatch/silence; catalogue_web/backfill/cleanup;
custodes/tiers/sevenfold/grounding; cascade_bridge's widen/paid path); **run #7's five**
(address/completeness/foreman as they now stand; chain/module_index/local_agent/pick_model).

**Not yet audited line-by-line** — pick from here: `address_space.py`, `profile.py`, `burgs.py`,
`tells.py`, `style_audit.py`, `audit.py`, `descending_ladder.py`, `cosmography.py`, `genre.py`
(only its cap and its artifact were touched), `reference.py`, `resync_roll.py`,
`retry_synthesis.py`, and **`pipeline.py`'s `ask`/`ask_pool_first`/`phase_entrypass` as they now
stand after run #7**, plus the new `runguard.py`.

Three findings from run #5's audits remain un-actioned and still deserve a second opinion:
`hostcheck`'s `judgeable` flag is computed and respected by `standards.py` but ignored by
hostcheck's own two consumers; `onomast.coin_well_formed`'s fallback skips both its quality and
uniqueness checks; `feats._unwrap_templates` miscounts brace nesting on `{{{`.

## 5. Lessons worth keeping

- **A fix is not landed until something in production reads it.** Run #6's genre uncap was
  correct, tested, and completely inert for a day, because the only bridge from that module into
  the system is a hand-run CLI nobody had run since the 20th. Its sibling `grounding` fix landed
  by itself because `pipeline.py` calls it every phase. Same run, same shape of fix, opposite
  outcomes — and the difference was invisible from the diff. **After fixing, grep for the
  caller.** If there is none, that is the finding.
- **"Not None" is not "usable", and a fallback that cannot be reached is not a fallback.**
  `ask_pool_first` had a working local arm the whole time; the guard in front of it just never
  let anything through to it. When a helper is named X-first-Y-second, the interesting question
  is what exactly makes it stop trying X.
- **Report the mechanism and the reproduction separately.** The 0/20 diagnosis is well-evidenced
  and the fix is right, but the pool died before it could be caught in the act, and saying so is
  what lets the next run tell a working fix from a plausible story. Item 1 above is written to be
  falsifiable for exactly that reason.
- **Run the linter even on a rename.** pyflakes caught two `undefined name 'delta'` references
  left behind when a variable was renamed inside `foreman.attempt_patch` — in a function the
  model lane uses to edit live source. The battery is not ceremony.
- **An audit subagent is right about WHERE more often than about WHY, and can understate.** The
  `local_agent` finding was real and the agent missed half of it (the denylist consequence). One
  agent also died on a 403 auth error mid-run and had to be relaunched — normal, not a signal.
  Verify every finding against source; record the unverified ones as unverified (m37).
