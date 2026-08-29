## 2026-08-28 — Run #36c: the local rung fixed, and the standing BLOCKING bug closed

**The queue holds ZERO BLOCKING orders for the first time in this project's recent history.**

**FOR THE OWNER — READ THESE FIRST.**

**1. THE LOCAL RUNG IS ALIVE, AND THE CAUSE WAS THE SERVER, NOT ANY CLIENT.**
`OLLAMA_NUM_PARALLEL` was set to **3** as a user environment variable. Ollama divides a model's
context across parallel slots, so config's `num_ctx: 12288` became **12288 ÷ 3 = 4096** — which
is exactly the `context_length: 4096` this project has been staring at for three runs and
attributing, every time, to a client asking for it. **No client ever asked for 4096. The server
was dividing.** Every request naming 12288 then wanted a differently-shaped runner, which is a
rebuild, and a 6 GB model rebuilt on a loop cannot also serve — that is the saturation, the 90
second timeouts, and the 26 hours of CPU burned answering nothing.

Set to **1** and restarted:

| | before | after |
|---|---|---|
| request at `num_ctx=12288` | 90 s timeout | **9 s** |
| `/api/ps` `context_length` | 4096 | **12288** |

Previous value and the revert command are in `state/run36b_env_before.json`.

**Three diagnoses were wrong before this, and each reasoned correctly from a real measurement.**
Run #35 blamed a foreign `semsearch` client — it had already exited while the stall continued.
Run #36 blamed the infinite `keep_alive` and *refuted* the reload theory, on a probe that watched
the resident context hold still — it held still because requests were being rejected from a full
queue before any reload could start. Run #36b blamed four of our own call sites. What settled it
was stopping **every** Panscriptum model consumer and watching a fresh runner still come up at
4096, with nothing of ours left to blame.

The four code fixes are kept (`overwatch`, `pipeline` synthesis and entrypass, `magnitude` all now
take config's value). They were not the cause, they are correct on their own terms — one runner,
one context — and they stop the tree recreating the war if parallelism is ever raised again.

**2. THE STANDING BLOCKING BUG IS CLOSED. 27 synthesis blocks restored.** Order `3c7c8a6e9102`,
open since 2026-08-25. Records carrying a synthesis went **185 → 212**. The only four still null
hold **zero entries** and are the sources the owner excluded in August as having no verifiable
wiki — null is the correct state for them.

Getting there needed three separate things, and two were defects in the rescue tool itself:

* **It could not see the casualties.** `retry_synthesis` selected on the CAUSE — the pipeline's
  failed-set, which held **two** names. Twenty-nine of the thirty-one never failed anything; they
  were clobbered. A tool whose whole job is "sources the pipeline will never revisit" could see
  2 of the 31 that qualified. It now also selects on the CONDITION.
* **It asked the wrong model.** It called `PL.ask` (Ollama only) while `phase_synthesis` — whose
  prompt construction it deliberately shares so the two cannot drift — calls `PL.ask_pool_first`.
  They were also asking different *models*.
* And the local rung had to be alive at all, which is item 1.

**Verified against a snapshot taken immediately before the merge**, because this order is about a
writer clobbering things and "the merge said it worked" is not evidence: all 216 record files
re-read and compared — **0 entries lost, 0 top-level keys nulled, 0 files missing.** Marvel still
holds 59,170 entries and now names **Franklin Richards at M10**.

A sample of what came back: DC M10 *Star Conqueror*, Dragon Ball Z M10 *Shabbet*, Transformers
M10 *Elephorca*, Digimon M10 *Tooru*, Mario M10 *Megabug*, Naruto M9 *Kaguya Ōtsutsuki*,
Adventure Time M9 *The Glitch*, Invincible M9 *Stripevincible*, He-Man M9 *Nepthu*, Rick and
Morty M8 *Universe Bomb*, Gundam M7 *ELS*, Zelda M7 *Triforce*, Soul Calibur M6 *KOS-MOS* — and
four honest `unassayed` where the source genuinely shows no quantified feat (Chowder, Ghost
Recon, Baki, Terminator). That is the "no feat, no band" invariant working, not failing.

**3. DANDWIKI REMOVED — four sources, not one.** `www.dandwiki.com` is a host serving Yorviing's
Arcane Grimoire (478 entries), Dr. Firestorm's Engineering Corps (425), Mage Hand Press (22) and
Savant (8) — **933 entries, all already catalogued.** All four excluded via `roll.exclude()` with
a dated note; **non-destructive, and all 933 entries verified still on disk.** `health.check_caches`
now excuses an empty cache on a host whose sources are *all* out-of-scope, which is what ends the
24-hour red — the quarantine exemption it relied on is TTL-gated and lapsed daily.

---

### THINGS THIS RUN DID THAT NEED SAYING

**The restore reproduced the port exhaustion I closed the night before.** Three of the 28 sources
failed with `WinError 10048/10055` — ephemeral port exhaustion, caused by this run's own
connection rate. It cleared on its own and two of the three succeeded on retry. The order closed
on 2026-08-27 said plainly that nothing had been fixed and recurrence was not harder; that turned
out to be true within a day.

**Stale failure records were cleared under compare-and-swap.** `health --preflight` reported
"failures recorded that already succeeded" — Marvel and Bone (Jeff Smith) were still listed as
synthesis failures while their records carried a synthesis. Dropped, with a CAS write against the
pipeline's own state file, because a blind read-modify-write there would have been the exact
lost-update this project spent the week repairing, committed while tidying up after it.

**The library ran without its daemons for the duration of the restore** so they would not compete
for the model, and they were restarted afterwards through `autostart.py --watch`, which is the top
of the tree — one process, and the keeper rebuilds the rest.

**Filed, not fixed: `1f39177464cf`.** The clobbering is fixed in both writers and the 31 blocks
are restored, but **nothing automatically detects a lost synthesis.** `phase_synthesis` still
skips anything in its done-keys, so a block lost tomorrow would sit null and unreported.
`retry_synthesis.stranded_sources()` already computes exactly that list — the missing piece is
only that nobody calls it on a schedule. That converts a four-day BLOCKING outage into an order
that files itself the same hour.
