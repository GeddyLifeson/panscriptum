# NEXT STEPS — written by run #64 (2026-09-26 daily)

*Overwritten every run. The queue in `state/workorders.json` is the authority; this file is the
reading order, and the short list of things a fresh run would otherwise spend its first hour
rediscovering.*

---

## 0. PUBLISH IS STOPPED, AND THE OWNER HOLDS IT. DO NOT PUSH.

* **OWNER RULED 2026-09-26 (in session, after run #64): rodais is a separate project and moves to
  its own repo, https://github.com/GeddyLifeson/Diathiris (private, empty; ASCII name because
  GitHub forbids the ì).** The move WAITS until the owner says the work on branch
  `claude/beautiful-fermat-9xu33t` is finished. The full plan is on order `58b14244e856`. Until the
  owner releases it, everything below still holds: no push, and don't touch that checkout.

* Order `23092fffadf3` (OWNER, BLOCKING) is unruled. Since run #63 the owner merged **PR #14**
  (`a820e2f4`) to rodais on origin/main. The kit's `reference/owner_source_material/rodais` is
  a PR #13 copy, so a push reverts PR #14. RUN orders `573ab7b04b6f` (the publish credential
  question, which needs a live PUSH HELD line) and `5aec38314731` (the stop record) both wait on
  this ruling.
* **The export checkout is on the owner's branch** `claude/beautiful-fermat-9xu33t`, not main,
  with uncommitted deletions under `rodais/eras/_tmp/`. It is an owner session's work in
  progress. Read it if you need to; never reset, checkout or clean it.
* When the owner rules, follow NEXT_STEPS from run #63 §0 (a) or (b), and refresh rodais from
  origin/main at whatever PR is newest by then.

## 1. READ THE MUTATION PASS (the first whole one since prose resumed)

`state/mutate_20260926.log`, pid 2296, launched 00:23 on fingerprint `cdeea3268984401b`, baseline
drill **637/637/0** and verify_math **1310/0**. **Put the survivor count in the handoff.** A pass
killed halfway is not a pass with fewer survivors. `src/` moved under it afterwards (sweep64
fixes, none in the three targets), so its log will say "src/ MOVED". The verdicts are about the
launch tree, which is what the sandbox holds.
* Known equivalents are on record (`mutate.py --list-ruled`): assay 826 and 909, and escalation
  495, 567, 695, 1006, 1183 and 1239 (plus 1274, whose mirror is load-bearing).
* If the drill drifts on "no probe anywhere in this drill writes into the live failure ledger" or
  "...reached the ledger by a route the in-process spy cannot see" (it did once, unexplained, on
  09-24), capture the drill's BREACHED text. mutate prints only the net names.

## 2. CHECK THE RESTARTS THIS RUN LEFT

* foreman and read were terminated at 00:49 and restarted by the keeper at 00:52:33 on
  fingerprint `80fa46ef0bf1e4fd`. The new foreman closed `3dc2832846bc` itself at 00:53:21.
* **pipeline (44264) and overnight (38192) were deliberately left on older code** until their own
  phase or lap boundary, because their changes are cosmetic. If either is still the same pid,
  check codewatch's "last polled"; neither needs a kill for safety.
* If a STALLED_UNRESTARTABLE order reappears while the crawl is doing network I/O, M124's
  I/O witness is not in effect. Find out why before closing it by hand.

## 3. THE QUEUE

* BOTS `058fa19d4e65`: close it once `data/CHAIN.json` carries `unmatched` (pipeline phase 4
  writes it; PIPELINE_STATE's `done` does not list `chain` yet).
* OWNER: 51 orders. New: `d2f103634cf1` (sweep64's questions; the P8 `stub`/`wiki` scope is the
  one with a live cost).
* The canary is now yours: BINDING_HEALTH_STALE files at RUN past 7 days. It was last run
  2026-09-26 00:2x (134 hosts, 0 failed).

## 4. THINGS A FRESH RUN WOULD OTHERWISE REDISCOVER

* **The crawl's log goes quiet for tens of minutes by design** while it mines the 59,610-entity
  deferred tail on one worker (it logs every 200 entities). A quiet `roll_auto.log` is not a stall
  if the process shows network I/O.
* **overwatch rounds take hours** on the shared GPU (2,000–11,500 s per module). It now checks
  its source between modules.
* **Prose pace** is about 4–6 minutes a job over 725 jobs. Read a produced chapter, not the bar.
* The battery pins `qwen3:8b`; with the library running that is its normal state.
* Never pass a work-order resolution through a shell argument; backticks execute. Use a file.

## 5. THE BATTERY AT CLOSE OF RUN #64

* `drill.py` **640 attacked, 640 held, 0 BREACHED** (4 new nets this run, plus two cases added to an existing one)
* `verify_math` **1318 passed, 0 FAILED** · pyflakes clean · citecheck 0
* `liveness` 46 · `silence` 316 · `secondopinion` all three RAN, 0 secrets ·
  `axis_correlation` 45 entities
* `health --preflight` 1 problem (dandwiki) · `allsweep` 2 bad (dandwiki preflight, the jszip
  estate row in rodais)
* `corpus_db --rebuild` (start of shift) 216 sources, 282,822 entries
