## 2026-08-28 — Run #36b, the owner-directed follow-up (dandwiki removed; the local rung diagnosed a third time)

Short session, two owner instructions: "ollama back up, do the other two if you can" and "remove
dndwiki as a source". One of the two was done. The other is now understood.

**FOR THE OWNER — READ THESE FIRST.**

**1. OLLAMA WAS NOT BACK UP, AND THE REASON IS OURS.** Measured before trusting it: `llama-server`
pid 29452 was the **same process**, up since 2026-08-26 17:28, by then at **95,241 seconds of CPU
— 26 hours of compute — answering nothing.** Whatever was restarted, it was not the runner.

What followed corrects **two** previously-recorded diagnoses, both of which were confident and
both of which were wrong:

* `ollama stop qwen3:8b` moved `expires_at` from **2318-12-07** to now. The runner ignored it and
  kept burning CPU: a wedged runner cannot process its own unload.
* Killing it worked — and a **fresh runner was re-pinned at context 4096 with `expires_at` back
  to 2318 within seconds.** That re-pin is **our own code**.
* `pipeline.ask` sends `keep_alive: -1` on **every** request, and so does `standards.py`'s probe.
  Meanwhile **four call sites ask for a context that is not config's 12288**: `overwatch.py`
  (4096/8192), `pipeline.py` synthesis (4096), `pipeline.py` entrypass (4096), `magnitude.py`
  (8192). Ollama holds a model at ONE context, so a differently-sized request does not get a
  cheaper window — it forces a **rebuild**. `overwatch.py` is a **looping daemon**, which is what
  turned a mismatch into a continuous rebuild war: a 6 GB model being rebuilt on a loop cannot
  also serve, and the queue saturates.

**Run #35 blamed a foreign `semsearch` client** — it had already exited while the stall
continued. **Run #36 blamed the infinite keep_alive and explicitly refuted the reload theory**, on
a probe that watched the resident context hold still across four `num_ctx` values. It held still
because the 12288 request was **rejected from a full queue before any reload could begin** — the
probe measured a symptom of the jam and read it as evidence against its cause. That refutation is
the sharpest reminder yet that a measurement can be correct and still support the wrong
conclusion.

**Fixed tonight: `overwatch.py` only** — the looping one, because a loop is what makes this
lethal. The other three are one-shot, and changing them is a real design decision: **two doctrines
in this codebase contradict.** `pipeline.ask`'s own comment argues `num_ctx` should be *sized to
the call* to save VRAM on a 10 GB card; `gpu_lane`, `local_agent` and `verify_math` §19ab enforce
*one runner, one context*. On this hardware the second wins — VRAM saved is worth nothing if the
model spends its life being rebuilt — but that is your ruling, not a maintenance run's. **Order
`706215aabc5f`.**

**2. DANDWIKI IS REMOVED — and it was four sources, not one.** The order under-described it and
this run corrected that before acting. `www.dandwiki.com` is a **host** serving four roll sources:
Yorviing's Arcane Grimoire (478 entries), Dr. Firestorm's Engineering Corps (425), Mage Hand Press
(22), Savant (8) — **933 entries, all already catalogued, two of the four already assayed.** The
403 blocks *future* mining, not what is held.

All four excluded via `roll.exclude()` with a dated note recording the mechanism. **Non-destructive
by design — excluded sources keep their records — and all 933 entries were verified still on disk
afterwards.** A canonical snapshot was taken immediately before, so it reverses.

**And the operational half, which the exclusion alone would not have fixed.**
`health.check_caches` only excused an empty cache while a host's **quarantine** was active — and a
quarantine is TTL-gated at 24h, so the preflight went red every single day in the window between
lapse and next probe. On 2026-08-27 the dandwiki quarantine expired **167 seconds before** that
shift's sweep filed its orders. Widening the *quarantine* exemption to cover lapsed ones was
rejected: that weakens a live safety to quiet a symptom, and a lapsed quarantine genuinely is
unproven again. The exemption now keys off **the roll**, where the decision actually lives — a
host whose sources are *all* out-of-scope is excused, and one live source still bound to it keeps
the cache load-bearing. Proven in `handoff/excluded_cache_redcheck.py`: excused when all excluded,
**still a fault** when a live source shares the host, nothing excused when the roll is unreadable,
and **RED** with the exemption disabled.

**3. THE 31 NULL SYNTHESIS BLOCKS ARE STILL NULL, and the blocker moved.** Order `3c7c8a6e9102`
stays open and BLOCKING. Re-measured: 31 records, all `mode=web`, **191,029 entries**, Marvel
(59,170) and DC (55,560) the largest.

Two real defects in the rescue tool were found and fixed — both would have silently limited any
attempt:

* **It selected on the CAUSE, not the CONDITION.** `retry_synthesis` read the pipeline's
  failed-set, which holds **two** names. Twenty-nine of the thirty-one never failed anything; they
  were clobbered. A rescue tool whose whole job is "sources the pipeline will never revisit" could
  see two of the thirty-one that qualified. It now also takes `stranded_sources()` — no synthesis,
  and entries to reason over — giving **28**.
* **It asked a different model than the phase it stands in for.** It called `PL.ask` (Ollama only)
  while `phase_synthesis` calls `PL.ask_pool_first` (cloud first). Its docstring already records
  being burned once when the two built different *prompts*; they were also asking different
  *models*.

**The blocker is now transport, and neither arm is open.** The cloud pool answers with **2**
buckets against `tuning.CLOUD_MIN_BUCKETS = 3` (fresh `prove()` tonight). **Lowering that
threshold was considered and rejected** — the constant carries a written argument that two is not
enough, and weakening a policy to obtain a result is precisely the move this project exists to
catch. The local arm is the reload war above. A pilot on the smallest stranded source (Chowder)
ran end to end and failed at the transport with `HTTP 503`, which is the correct behaviour and is
the evidence.

**It becomes runnable the moment either arm opens** — one more answering cloud bucket, or your
ruling on the three remaining `num_ctx` sites. It can also be forced by quiescing the competing
model consumers (`read.py`, `pipeline.py`, `magnitude.py --calibrate`), which the `--merge` step
requires stopped anyway; that halts the library's overnight work for hours and was not done
unilaterally.

**Housekeeping.** `overwatch.py` was stopped so the keeper restarts it on the fixed code. One
duplicate order was minted and withdrawn in the same session: re-filing the standing order under
a new `where` hashes to a new id, and the original is cited from BUGS.md, NEXT_STEPS.md and
`pipeline.py`'s own docstrings, so it is the one that had to survive. Battery re-checked after
tonight's edits: pyflakes clean, `health --preflight` all checks pass.
