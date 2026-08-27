# Next Steps — written by run #35 for the run that follows it

*Overwritten every run. The queue in `state/workorders.json` is the authority on what is open;
this file is the reading of it — what to do first, and why.*

---

## 0. THE LIBRARY IS RUNNING, AND NOTHING IS HALTED.

`escalation.py --status` says **clear**, and run #35 neither raised nor lifted a halt. The
battery closed green: `verify_math` 1,052/1,052, `drill` 247 nets 0 breached, pyflakes clean,
`health --preflight` 0 problems. The queue went **341 → 158** with **282 orders closed** and 58
filed (51 of those from the whole-tree sweep, which is the sweep working, not the queue rotting).

**Do not re-derive any of that.** Open the shift the way the card says: `escalation --status`,
the run guard, `workorders --sweep`, `corpus_db --rebuild`. Then work the queue.

---

## 1. START HERE: THE MUTATION MANDATE IS STILL BLOCKED, AND IT IS THE ONE THING RUN #35 DID NOT
   DELIVER.

**M46.** `mutate.py --target all` died twice with a bare `FileNotFoundError` on
`<sandbox>/src/assay.py`, ~4 minutes in, **after its baseline gates had already run and passed in
that same sandbox** — once with agents editing `src/`, once on a completely stable tree, so
concurrent edits are ruled out. So **run #35 produced no mutation results at all.**

What is already measured, so you do not repeat it:

* `sandbox()` copies all 113 modules correctly; `assay.py` is present at 67,842 bytes.
* The file **survives the `import` gate and the `verify_math` gate** (checked by running each
  against a live sandbox and stat-ing the file after).
* The **`drill` gate is the remaining suspect** and was still under test when the shift closed —
  a probe is in `handoff/` notes; re-run it first:
  build a sandbox, run only the drill gate against it with `cwd=root`, and stat
  `<root>/src/assay.py` afterwards.
* Note the sandbox baseline reports `drill rc=2`, which is not drill's ordinary 0/1. That may be
  the same story.

Mitigated but not fixed: `sandbox()` now refuses when a target did not land, so the next failure
will be a legible message instead of a traceback. **Fixing this unblocks the whole §3b mandate**,
which is the highest-value single item in the queue.

## 2. THE SWEEP'S 51 FINDINGS ARE FRESH AND UNWORKED.

Run #35 swept **every one of the 113 modules** (`sweep_plan.missing('run35')` → 0) and filed 51
`SWEEP35_FINDING` orders that nobody has yet worked. They are the newest and best-evidenced
material in the queue. The ones to read first, because they are about the checking machinery
itself:

* **Nine drill nets that verify a guard by whole-file substring search**, filed by batch 2 with a
  concrete defeat for each (a comment or dead branch reproducing the string). Run #35 committed
  this exact defect while fixing something else — a net written for the halt check passed against
  a build where the call had been deleted, because the comment still named it — and had to
  rewrite it against the parse tree. **The same fix applies to all nine.**
* **`abandoned_sandboxes_are_reaped` cannot go red** (`drill.py:3831`): it calls
  `reap_orphans(older_than=10**9)`, a ~31.7-year cutoff, so `== []` holds whether reaping works
  or not.
* **Two literal-tautology checks in `verify_math`** (`check(label, True, True)`) that call no
  code, and a backfill check that hand-reimplements the algorithm and asserts against its own
  copy.
* **`allsweep`'s ESTATE tier findings never reach the `bad` grade** (batch 13) — a named fault
  like "MASTER CHARTER MISSING" can stand forever without failing the battery.

## 3. TWO CONCURRENCY FINDINGS THAT LOOK LIKE THE ONES THAT HAVE ALREADY COST THIS PROJECT.

* `binding_health._land` and `suppressions._land` still use a fixed `path + ".tmp"` name — the
  exact collision `runguard._land` was replaced for this shift (batch 11, `98831f6e6f6d`).
* `binding_health.run()`'s new merge is itself an uncompare-and-swapped read-modify-write, which
  can reintroduce the partial-over-complete bug the merge was added to fix (`23d84e6f8e81`).

## 4. THE LOCAL RUNG IS THE ECONOMICS, AND IT IS CURRENTLY CLOSED.

Order `505177847f43`. A **foreign** process (`pythonw -m semsearch.cli watch`, pid 11468) held
9,599 established connections to Ollama; a real `local_agent` order ran >15 minutes and landed
nothing. Run #35 therefore escalated the whole 200-order LOCAL rung to Claude subagents — correct
once the cheaper handler is measured unable, but **not the intended cost**. Before routing
anything to LOCAL next shift, spend one cheap measurement: count connections to port 11434 and
time a single `local_agent` task. If it is still starved, say so and escalate deliberately rather
than discovering it order by order. **Do not kill pid 11468** — it is the owner's and is nothing
to do with this library.

Second, independent local-model fact worth remembering: `qwen3:8b` is a THINKING model, and at a
small `num_predict` it spends the whole budget on reasoning and returns an **empty content
string** — which looks like a refusal rather than a truncation.

## 5. WHAT IS WAITING ON THE OWNER — 47 ORDERS, NONE DECIDED.

Do not work these; they are judgment calls. The four that matter most:

1. `3c7c8a6e9102` **BLOCKING** — a re-catalogue nulls the pipeline-authored synthesis block.
   Re-measured this shift: **31 of 216 records null, 185 intact, and the count has not moved in
   ~23h.** Restoring 31 synthesis blocks is a curatorial decision.
2. `ec67de571754` — **canonical data files have no backup.** `SWEEP_ROLL.json` was destroyed
   twice this shift and was only recoverable because it is derivable from the records.
   `WIKI_HOSTS.json` and `CHARTER_SPINE_CODES.json` are **not** derivable from anything on disk.
3. `505177847f43` — the local rung starved by a foreign process (above).
4. The two **misbound hosts** now measured rather than suspected: `prime.fandom.com` serves the
   Prime Hydration drink wiki, `starrealms.fandom.com` serves "The Brain World Wikia". Rebinding
   or unbinding a source is curatorial. The other three of that family are now correctly filed as
   "the binding is right, the entry names are feature-level" and need no bot at all.

## 6. A DESIGN QUESTION RUN #35 RAISED AND DID NOT ANSWER.

**M47.** `codewatch.stale()` needs the `src/` fingerprint to hold still for 180s before a daemon
exits rc=17. A maintenance shift rewrites `src/` for hours, so **no daemon bounces for the entire
shift** — measured: `publish.py --push --loop 10` pushed to the public repo for 2.5 hours on
pre-shift code. Nothing broke this time. The settle rule is right; the interaction is not
obviously wrong either, which is why it is a question and not a fix. Worth an owner ruling on
whether a maintenance run should quiesce the publisher for its duration.

---

**HYGIENE NOTES FOR WHOEVER RUNS NEXT.**

* Two agents this shift closed orders they did not own and re-filed them; one wrote a literal
  backspace into an evidence field through a shell heredoc — **the eaten-escape corruption this
  project has warned about since the beginning.** Use the file tools for anything containing a
  backtick or a backslash, never `python -c` through the shell. Run #35 hit it twice itself.
* When you merge agent-authored checks into `verify_math`, **run the merge before trusting it**.
  Two batches shipped their own `PASS, FAIL = [], []`, their own `check()` and a `sys.exit(1)`;
  pasted in unchanged they would have reset the accumulators mid-run and shadowed the real
  `check()`, discarding every result from sections 1–34 while still printing a confident RESULT
  line. Section 36 now runs those files in isolated namespaces for exactly this reason.
* `allsweep` will grade `verify_math` BROKEN while a sweep is mid-flight — the coverage check is
  reading a `sweep_plan` run that has not finished recording. Not a fault; re-run after.
