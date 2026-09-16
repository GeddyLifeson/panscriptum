# NEXT STEPS — written by run #60 (2026-09-15) for the run that comes after it

*Overwritten every run. The queue in `state/workorders.json` is the authority; this file is the
reading order, and the short list of things a fresh run would otherwise spend its first hour
rediscovering.*

---

## 0. NOTHING IS BLOCKED AND NOTHING IS HALTED

`escalation.py --status` was clear at the start of this shift and is clear at the end of it. No
halt was raised by run #60 and none was found standing. The library is running: the watchdog,
overnight, dashboard, publish, foreman, overwatch, pipeline, read and the `feats.py --roll` crawl
were all live in the process table at close.

---

## 1. THE ONE THING WORTH DOING FIRST: LET THE CHAIN FINISH

**`data/CHAIN.json` is still dated 2026-08-22.** It is the only deliverable this run set out to
refresh and did not.

WHY IT IS STALE, and this part is now fixed: `chain.extract` died on `AttributeError: 'str' object
has no attribute 'get'` when a model answered with a list of strings instead of objects. The pass
had already harvested **31,927 contest sentences** and threw all of it away. That guard is in
(bug **M110**, with a drill net that reproduces the exact crash), so **the pipeline's own chain
phase can now complete on its own** — it could not before.

WHAT THE NEXT RUN SHOULD DO: check `data/CHAIN.json`'s mtime before anything else.
* If the pipeline has refreshed it — nothing to do; close order `058fa19d4e65`, whose remaining
  half was only ever "re-run the chain so CHAIN.json carries the current shape"
  (`fit_error`, `unmatched`, `unanswered`).
* If it has NOT, run `python src/chain.py --workers 12` directly and watch it. **Expect it to be
  slow for a reason that is filed, not mysterious** — see §2.

Run #60 started that pass by hand and then **killed it deliberately**: it holds the chain
singleton lock, so while it ran the pipeline's own chain phase was being refused, and it was
competing with the local agent for the one saturated GPU. Killing it was the cheaper trade. The
singleton guard retakes a dead holder's claim, so nothing is stuck.

---

## 2. WHY EVERYTHING MODEL-SHAPED IS SLOW RIGHT NOW — ORDER `3e6283e6dd78`, OWNER

The cascade cloud lane has **no working Groq bucket**, and it is not a quota problem.
`catalogue_models.py`, run live against the provider APIs this shift:

```
groq   13 model(s) available   CONFIG ASKS FOR 1 THAT NO LONGER EXIST
    stale: qwen/qwen3.6-27b
```

Every call 404s, `cascade_bridge` removes the bucket at runtime — correctly, and from scratch,
every single run — and everything falls back to one local 8B model. This run's chain pass was
reduced to **"2 answering, 8% ok over 90 calls"**.

The replacement is already on offer and is the same family and size: **`qwen/qwen3.8-27b`**. The
config is `C:/Users/imarl/cascade/config.json` line 510, which belongs to the **Cascade project,
not this kit** — which is why run #60 filed it instead of editing it. A one-line change there
would give the library its cloud lane back.

*(Run #59's handoff said this id lives in Cascade's config. It was right. `PROVIDER_MODELS.json`
here is only a mirror of what was asked for.)*

---

## 3. THE LOCAL MODEL GOT NOTHING DONE THIS SHIFT, AND THE REASON MATTERS

`local_agent.py` was given order `98301c3da870` (a genuinely small, mechanical fix) and after
**15 minutes produced no output and changed no file** before hitting its timeout. It was starved:
the chain pass and the agent were both queued against the same single loaded `qwen3:8b`.

So **do not read this as the local model failing the task** — it never got a turn. Retry the
LOCAL rung when nothing else is holding the GPU (check `curl.exe -s http://localhost:11434/api/ps`
first), and give it one order at a time. There are now **9 LOCAL orders** waiting, most of them
small:

| order | what |
|---|---|
| `98301c3da870` | `derivation.py` — read with `errors="replace"` like `sweep_plan` already does |
| `9f75ae0b8d96` | `render.py` — guard `main()` against an empty library |
| `e3472496a133` | `profile.py` — validate `attested`, or say why it needs no validation |
| `bcd9737c5447` | six comments that describe their own module wrongly (cite by symbol) |
| `7354d54f0e27` | two dead branches — INFO, and **deletion is not a maintenance-rung call** |
| `d7efd67caa6f` | refiles from `citecheck`; see §4 before touching it |

---

## 4. A NOTE ON `d7efd67caa6f` SO IT IS NOT RE-FOUGHT

Run #60 closed this by **fixing the detector, not the two sites** — both were false positives
(a `silence.note` tag being quoted as a corpse, and a comment recording a citation that was
already repaired). `citecheck` now tells a **use** from a **mention**, and reports what it set
aside by kind. It is currently **0 findings, 9 + 24 + 4 set aside**.

It refiled once during the shift — on a net description **this run had just written**, which
spelled a pointer-shaped token in prose. That was fixed the same way: write "feats.py line 139",
not the colon form. **If it refiles again, check first whether the citation is real or whether
someone wrote the colon form in running prose.**

Orders `89503c58409f` (sixty rotted citations) and `386c0d66e31e` are a different, real class and
are untouched by any of this.

---

## 5. STILL OPEN AND DELIBERATELY NOT CLOSED

* **`58a00e909217` (RUN, MAJOR) — the one confirmed FALSE KILL.** Its only surviving explanation
  (gates reading the live corpus through the `data/` junction) is fixed, and run #60 added the net
  that was missing: *"a hardlinked data file keeps the bytes it was taken from when the live name
  is replaced"*, HELD, and RED when `silence.write_json` stops landing by atomic replace.
  **It stays open because the decisive measurement does not exist yet** — a long pass scoring
  `escalation.py:409` as SURVIVED rather than KILLED. Closing it on the strength of the fix is
  precisely what the order itself warns against. **Run the mutation pass and read that mutant.**
* **`4c2101d54c10` (OWNER, BLOCKING) — nothing watches the watchdog.** Unchanged. The library was
  restored by hand on 2026-09-10 and the detection gap is still an operations ruling nobody has
  made.
* **43 OWNER orders.** Most are questions that four or more shifts have now each re-read and
  re-deferred. Order `e114b2d0fe48` is about exactly that cost.

---

## 6. THE MUTATION PASS

Launch it early and let it run overnight:

```
python src/mutate.py --target all --file-orders --detach
```

**Run #60 launched one at 23:16 — pid 30232, log `state/mutate_20260915.log`, sandbox fingerprint
860af1f51f1757ca.** It was launched LAST rather than first on purpose: this run edited six `src/`
modules, `mutate` snapshots `src/` at launch, and run #59's own log recorded its baseline being
taken from a half-edited tree. So the pass waited until `src/` was settled, the halt was cleared
and the push had landed.

**Check whether it is still alive before doing anything else, and do NOT relaunch while it is.**
Read the log and put the survivor count in the handoff. If it did not finish, say so — a pass
killed halfway is not a pass with fewer survivors.

`escalation.py` — the module the whole chain of command rests on — **has still never completed a
mutation pass.** Both of the deaths that stopped it are now explained and guarded (order
`9ea4d3545524`, closed this shift), so this is the first run with a real chance of finishing one.

---

## 7. THE BATTERY AT CLOSE OF RUN #60

Green, and the one red thing is the standing owner item, not a regression:

* `drill.py` — see the handoff entry for the final count; **0 BREACHED**
* `verify_math.py` — **1307 passed, 0 FAILED**
* `pyflakes` over `src/` — clean
* `liveness` 47 findings (unchanged) · `silence` 314 silent of 1208 (unchanged)
* `secondopinion` — ruff, vulture and detect-secrets all RAN; **0 secrets by two independent
  scanners**
* `axis_correlation` — `n_entities` 45, unchanged, so nothing was `--write`n
* `health.py --preflight` — **1 problem**: `dandwiki.com` does not answer its API. Standing owner
  item, same as run #59.
* `allsweep` — 2 bad subsystems: the cascade live call (§2) and that same preflight row.
* `corpus_db --rebuild` — 216 sources, **282,822 entries**, 280,401 evidence rows.
* `binding_health --run` — 134 hosts, **0 failed**.
* `sweep60` — 16 batches, **all 119 modules**, `missing()` empty.
