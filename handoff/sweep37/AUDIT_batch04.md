# Sweep 37 — batch 04 audit

**Modules read IN FULL (every line, 4,054 total):**
`src/standards.py` (1887), `src/escalation.py` (556), `src/scout.py` (440),
`src/prose_gate.py` (347), `src/feats_index.py` (289), `src/catalogue_codex.py` (271),
`src/scale_theories.py` (148), `src/module_index.py` (116).

Halt status read `clear — the library is running.` at the start of this batch and again at the
end. Nothing was raised, lifted, edited, or toggled. `prose_enabled` / `step4_enabled` were
never opened, read for value, or exercised against the live config; `prose_gate.py` was reasoned
about from source and driven only with synthetic in-memory inputs.

Every finding below was reproduced by running the real source (extracted line ranges or the
imported module) against synthetic inputs, never against live state. Demonstrations are quoted.

---

## MAJOR

### M1. `prose_gate.section_shortfall` — the invented-entry check cannot fail

**Where:** `src/prose_gate.py`, `section_shortfall` (the `extra = max(0, len(blocks) - expected_entries)`
branch) and `assert_block_complete`.

The block computes `extra`, appends a sentence to `missing` — *"N entries the manifest never
asked for -- an invented entry is a fabricated record, not a bonus"* — and **does not add
anything to `required`.** Each extra block contributes its own 5 to `required` and, if
well-formed, its own 5 to `present`. So `frac` stays exactly 1.0, and `assert_block_complete`
gates only on `frac < (1.0 - SECTION_LOSS_FLOOR)`. The `missing` list is only ever rendered
*inside the exception that is not raised.*

Demonstrated (real module, synthetic text):

```
=== A. extra entries the manifest never asked for ===
blocks=5 expected=2 -> present=25 required=25 frac=1.000
missing list says: ['3 entries the manifest never asked for -- an invented entry is a fabricated record, not a bonus']
assert_block_complete RETURNED 1.000  -> GATE DID NOT REFUSE

=== A2. one asked-for entry, four invented ones, all well formed ===
present=25 required=25 frac=1.000
assert_block_complete -> 1.0 NO REFUSAL

=== B. ghosts (fewer than asked) still refuse, for contrast ===
REFUSED as expected: demo: the block kept 5 of 25 required entry sections (20%).
```

The source comment directly above the branch states the fault as fixed: *"`max(0, ...)` floored
the ghost term at zero, so a model returning MORE entries than the manifest requested paid
nothing -- padding with invented or duplicated entities was free, and Hard Rule 1 forbids
exactly that."* It still pays nothing. The fix named the fault in a string; it did not price it.

**Why it matters:** this is layer 4 of the owner-held prose gate, and the thing it fails to
refuse is a *fabricated record* — Hard Rule 1's central prohibition, and the precise shape the
withdrawn 145 chapters took ("the model padded from a bare name and category"). Duplicated and
invented entries pass at a reported 100%.

**And the PROVEN property does not cover it.** `drill.py:732` and the §20x checks in
`verify_math.py` (around :4763–4771) assert only that the *string* appears in
`section_shortfall(...)[2]`. No net anywhere asserts that `assert_block_complete` **refuses** an
over-length block, while the ghost direction has exactly such a net. A net that tests the
message rather than the behaviour is the shape this project calls a decoy.

**Confidence: certain** (reproduced twice, two shapes).

---

### M2. `scout._mutate` overwrites a corrupt or wrong-shape shared artifact with an almost-empty one, and reports success

**Where:** `src/scout.py`, `_mutate` — the `except Exception: ... d = {}` arm and the
`d = d if isinstance(d, dict) else {}` line.

`_mutate` takes `silence.digest_of(path)` **before** reading. If the read then fails (invalid
JSON) or yields the wrong shape (a list, a string, a number), `d` becomes `{}`, `change(d)` adds
the single key, and `silence.replace_if_unchanged` compares the *unchanged* digest, matches, and
**lands**. The file's whole prior contents are gone and the caller is told `landed=True`.

Demonstrated against scratch copies (never the live files):

```
--- B. file readable as bytes but INVALID JSON (truncated mid-write, hand-edit) ---
   before (60 bytes): {  "Marvel": "marvel.fandom.com",  "DC": "dc.fandom.com",  "
   landed=True
   after  (35 bytes): {  "NewSource": "pages:NewSource" }

--- C. valid JSON of the WRONG SHAPE (a list) ---
   before (38 bytes): ["marvel.fandom.com", "dc.fandom.com"]
   landed=True
   after  (35 bytes): {  "NewSource": "pages:NewSource" }

--- D. valid JSON, wrong shape (a bare string) ---
   landed=True
   after  (35 bytes): {  "NewSource": "pages:NewSource" }
```

`_mutate`'s three live targets are `data/WIKI_HOSTS.json` (via `feats.HOSTS`, written on every
successful `scout()` registration), `data/SCOUT_BLOCKED.json` and `data/SCOUT_ATTEMPTS.json`.
Losing WIKI_HOSTS.json un-adopts every host in the library at once: `scout.hostless()`,
`feats_index.host_to_sources`, `hostcheck`, and the `MIN_HOST_COVERAGE = 1.0` standard all read
it. `hostcheck.adopt()` writes it from a separate process, which is exactly the interleaving
that produces a torn read.

Note the asymmetry with the sibling module in this same batch: `escalation._read_stopped` was
fixed in run #36 for *precisely* this shape — *"Wrong-shape is not better evidence than
unparseable. It is the same fact"* — and it fails closed. `scout._mutate` fails open **and
destructive**. Cases C and D do not even emit a `silence.note`.

**Confidence: certain** (reproduced, three shapes).

---

### M3. `standards.check()` — two standards report a clean ZERO off an input they could not read

**Where:** `src/standards.py`, the swallowed-failures ledger block (`ledger = {}` … the two
`out.append(_s(...))` for `unexpected swallowed failures` / `probe failures`) and the
unanswered-records block (`unans_files = 0` … `cached records that were fully read`).

Unlike the ~18 blocks that route a failure to `_dropped`, in these two the `out.append` sits
**outside** the `try`, so a failed read falls through with the initialiser and the standard is
emitted as **met**.

Demonstrated by executing the exact source line ranges with `HERE` pointed at an empty
directory:

```
--- state/failures.json unreadable ---
   unexpected swallowed failures              holds=True  observed='0'
   probe failures (reported, not judged)      holds=True  observed='0'
--- data/readfeats unreadable ---
   cached records that were fully read        holds=True  observed=0
```

`cached records that were fully read` is the worse of the two and is **HIGH severity**: a
missing or renamed `data/readfeats` makes `glob.glob` return `[]` without raising, so the
`except` never fires, **no `silence.note` is emitted at all**, and `_UNANS_CACHE` caches the
fabricated zero for 120 s. There is no trace anywhere. The order text for that standard tells
the reader to delete permanently-incomplete cached records — over a number that means "I could
not look".

A partial failure is the same shape: if the glob loop raises on file 400 of 500, `unans_files`
holds the partial count and the standard is emitted with it.

This is the file's own documented defect class one layer in — see the `_dropped` preamble
("a run losing three standards to a missing file reads as MORE consistent, not less") and the
fabrication standard's note ("UNMEASURED is a reading; silence is not"). Here the standard does
not vanish; it reports a *number it did not measure*.

**Confidence: certain** (reproduced with the real source lines).

---

### M4. `standards.check()` — `one instance of each job` vanishes silently; `_dropped` does not see it

**Where:** `src/standards.py`, the duplicates block: `except Exception: silence.note("standards.py:duplicates"); _dup = None`, then `if _dup: out.append(_dup)`.

Every other outer handler in `check()` records `_dropped.append(...)`. This one does not, so the
HIGH standard disappears from `out` **and** `every standard could read its own input` stays
green while it is gone. A static walk of `check()` confirms it is the only outer handler in that
state:

```
line 863   note=standards.py:ledger              -> re-emits a fabricated 0   (M3)
line 906   note=standards.py:unanswered-records  -> re-emits a fabricated 0   (M3)
line 1631  note=standards.py:duplicates          -> SILENT VANISH             (M4)
(all 21 others -> DROPPED-RECORDED)
```

The probe is `powershell Get-CimInstance Win32_Process` with `timeout=60` on a 16-core machine
that routinely runs fifteen jobs plus a crawl — a timeout here is an ordinary event, not an
exotic one. `report()` then divides by the smaller `len(rows)` and the run reads *more*
consistent for having lost a standard.

**Honest mitigation:** `verify_math.py`'s `[d9b895708c45]` declared-vs-emitted reconciliation
*would* name this standard as missing — but only during a battery run, and only if the probe
happens to fail in that window. The live page that `foreman`/`dashboard` dispatch work orders
from carries no such reconciliation; `_dropped` is that page's mechanism and it is not wired
here.

**Confidence: certain** (static, unambiguous; the handler is three lines).

---

### M5. `escalation.escalate()` discards `_raise_halt()`'s verdict — a halt that did not land returns as a halt that did

**Where:** `src/escalation.py`, `escalate()`: `if level >= OWNER: _raise_halt(rec)`, then
`return rec`.

`_raise_halt` was fixed in run #34 to stop discarding the write verdict: it now returns `landed`
and writes to stderr when the rename is refused. **The caller throws that verdict away.** The
returned `rec` carries no `landed` field, and `_append_log(rec)` runs *before* the write attempt,
so the janitor's log — the rung whose stated job is that "the lowest log always holds the whole
story even when the top rung fires" — records the OWNER escalation with no indication that the
halt file never appeared.

The module's own comment says this is the ordinary case here: *"on Windows -- where the rename is
DENIED while any reader holds the target, and this file has readers on their own clocks (every
`assert_clear` opens it, the dashboard polls it)."* When it happens, every other process's
`assert_clear()` finds no halt file and carries on, and the caller that escalated has no way to
know. The only durable trace is a `silence.note` counter and a stderr line — and every standing
daemon on this machine runs under `CREATE_NO_WINDOW`, so stderr is not a channel a person reads.

The fix stopped one frame short of the caller. **Confidence: high** (static; the discarded return
is unambiguous, the reachability is quoted from the module's own account).

---

### M6. `escalation.py --clear` prints **"nothing was halted."** when the lift was refused

**Where:** `src/escalation.py`, `clear()` returns `False` both for "nothing was halted"
(`if not halted: return False`) and for "the write was refused" (`if not landed: ... return False`);
`main()` then prints `"halt cleared." if did else "nothing was halted."`.

So a person who runs the documented lift command against a **standing** halt whose write is
denied is told, on stdout, that **there was no halt to lift**. The stderr line says the opposite
("The library is STILL HALTED"), and the two interleave on one console.

This is the mirror of the defect the same function's comment says it fixed: *"a refused rename
left `cleared: false` on disk while this returned True and the CLI printed 'halt cleared.' A
person would walk away believing the library was running."* The return value was corrected and
the CLI's two-way collapse of `False` was left, so the person now walks away believing there was
never anything wrong — which for a standing OWNER halt is the more expensive of the two wrong
beliefs.

`clear()` needs a third state (or `main()` needs to re-read `status()` before printing).
**Confidence: certain** (static, three lines, no ambiguity).

---

### M7. `feats_index` swallows a failed host-map read, caches the emptiness, and defeats `manifest_builder`'s guard

**Where:** `src/feats_index.py`, `host_to_sources` (`except Exception: silence.note(...); wh = {}`
followed unconditionally by `_CACHE["hosts"][path] = dict(out)`) and `load_index`
(`if not os.path.isdir(root): _CACHE["index"][root] = idx; return idx`).

An unreadable/missing `data/WIKI_HOSTS.json` yields an empty host map, which is then **cached for
the life of the process**. `feats_for_source` finds no hosts and returns `[]` for every source,
for ever, with no retry.

`manifest_builder.py` (around :352) wraps the call in `except Exception` specifically so that a
failure "says so, OUT LOUD", with a printed WARNING and the comment: *"a BUG in `feats_index` …
produce[s] the identical observable result to 'this source genuinely has no attested feats'."*
**No exception escapes `feats_index`, so that warning can never print.** The guard is at the
wrong layer — the swallow is one module below it.

Demonstrated:

```
host_to_sources(unreadable) -> {}  (no exception raised)
cached under that path?  True
feats_for_source('Marvel') -> []   len=0
```

Same shape one level down: `load_index` skips a record file that will not parse
(`except Exception: silence.note(...); continue`), and `audit()` reports `records = len(idx)` —
so corrupt records are subtracted from the *denominator* and the printed join rate goes **up**.
The module's own docstring says a stranded record is "counted and named rather than left to be
inferred from a smaller total"; a corrupt one is neither counted nor named. (Duplicate
`(host, _norm(entity))` keys are silently overwritten with the same effect.)

**Confidence: certain** for the empty-map path (reproduced); **high** for the denominator path
(static, unambiguous).

---

## MINOR

### N1. `escalation.resume_subsystem` has no person-check; rung 4's "stickiness" is a 20-character string
`resume_subsystem` validates only `len(ruling.strip()) >= 20`. `clear()` requires *both* a
ruling and `_by_a_person_at_the_cli()`. `stop_subsystem`'s docstring says the resume is
"deliberately STICKY: `resume_subsystem` demands a written ruling, **exactly as `clear` does**,
because the thing that undid the last one was an automated actor with good intentions and a
restart timer." It does not do exactly what `clear` does — the half that stops an automated
actor is absent. Any autonomous run can reopen a MANAGER-stopped subsystem with twenty
characters of anything. (`drill.py:3963/3984/4017` do exactly that, programmatically, today.)
There is also no `--resume` in `main()`, so no person-facing path exists at all. Whether the
programmatic path is intended is an owner call; the docstring currently overclaims either way.
**Confidence: certain** on the code, **medium** on intent.

### N2. Both layers of the "no programmatic clear" guarantee share one blind spot
`_by_a_person_at_the_cli` requires `__main__.__file__ == escalation.py` and the immediate caller
to be this file's `main()`. `drill.py:_no_programmatic_clear` greps `src/` for
`escalation.clear(` / `ESC.clear(`. Neither sees `subprocess.run([sys.executable,
"src/escalation.py", "--clear", "--ruling", "..."])`, nor `runpy.run_path(..., run_name="__main__")`
with a spoofed `sys.argv` — the latter satisfies *both* of the runtime conditions. Two layers
that both miss the same spelling is one layer. Not filed as an order: a shell-out is available to
any autonomous actor by construction and closing it fully may not be possible; recorded so the
guarantee is not read as stronger than it is. **Confidence: high.**

### N3. `standards.py` — `hand-built assays match the charter` passes on an empty file
`inside >= len(refs) if refs else True` parses as `(inside >= len(refs)) if refs else True`, so a
`REFERENCE_ASSAYS.json` holding `{}` makes this HIGH standard hold with observed `0/0`. A
non-dict file raises and is correctly `_dropped`; an empty dict is the one shape that reads
green. Same "no denominator is not a pass" lesson the catalogue-coverage standard twenty lines
below states in capitals. **Confidence: certain.**

### N4. `standards.py` — eight standards vanish on a conditional with no `_dropped` record
`if read:` (4 standards), `if roll:` (1), `if cov:` (2), `if src.get("total"):` (1). None record
`_dropped`, so `every standard could read its own input` stays green and `report()`'s
denominator shrinks. `if read`/`if roll` are arguable (the job genuinely is not running); `if cov`
and `if src.get("total")` are not — an empty or missing `library.sources` block silently deletes
`sources with a reachable wiki`, the deliberately-unsatisfiable `MIN_HOST_COVERAGE = 1.0`
standard whose entire stated purpose is to *keep the foreman scouting*. Losing it makes the page
greener and stops the remedy. **Confidence: certain** on mechanism.

### N5. `standards.py` — per-job stall watching fails open on two paths
Inside the job-advance loop, `except Exception: silence.note("standards.py:job-size"); continue`
and `except Exception: silence.note("standards.py:job-alive")` (leaving `alive = False`, then
`continue`) each remove **that job** from the watch list. `watched` shrinks and the standard
still reports "N running, all advancing" — a job whose log cannot be statted, or whose liveness
probe throws, is silently unwatched rather than reported unmeasurable. **Confidence: certain.**

### N6. `standards.py` — the served context is read off the *first* resident model, not the configured one
`served = next((m.get("context_length") for m in resident_raw if m.get("context_length")), None)`
takes whichever model `/api/ps` lists first. `cfg_num_ctx()` correctly reads `config.yaml`, but
nothing matches the resident row against `cfg["model"]`. With two models resident, this HIGH
standard compares the project's configured window against a stranger's runner — and the very
incident it was written for (2026-08-27) is *"an unrelated process had pinned qwen3:8b at 4096"*,
i.e. exactly the multi-resident case. **Confidence: high.**

### N7. Caps on the fields a person reads to act (Hard Rule 0 shape)
All verified in source, all on evidence or identifier fields:
1. `prose_gate.assert_block_complete` — `"; ".join(missing[:6])`, and the message does **not**
   say how many were omitted. Demonstrated: 150 findings, 6 rendered, no count.
2. `scout.sweep` — `reasons[:60]`, cutting the per-source failure reason mid-sentence. This is
   the identical `[:60]` shape `standards.py`'s unrecognised-pool block already removed with the
   note *"fix a shape, then grep the tree for it"*.
3. `scout.sweep` — `", ".join(s[:30] for s in deferred)`, cutting source **names** mid-name; the
   same shape `standards.py`'s shelf-ranks block removed (`not [:120] characters`).
4. `scout.sweep` — `src[:38]` in the per-source result line.
5. `scout.main` — `print(json.dumps(r, indent=1)[:2000])`, silently truncating the single-source
   result a person asked for.
6. `scout._land(LOG, prev[-40:])` — the SCOUT.json history is trimmed to 40 cycles on every
   write; older cycles are deleted from disk with nothing said.
7. `scout.scout` — `sample = [...][:PROBE_NAMES]` (25) and `sample[:18]` in the prompt. This one
   is load-bearing rather than cosmetic: the same capped list is passed to `verify()`, so a
   genuine page whose catalogued names all sit past index 25 in **record order** scores zero
   hits and is rejected. Truncation without ranking — the rule permits ranking then taking work
   in order, not an unordered cut.
8. `escalation._safe_name` — `out[:60]` on the per-source escalation log filename; two sources
   agreeing in their first 60 sanitised characters merge into one "area of the park" file.
9. `generate.py:349` — `"; ".join(_unearned[:5])` (out of batch; states its count, so noted only).

Confidence: certain on all; severity is genuinely minor for 3–6 and 8–9.

### N8. `scout._ask` reports a transport failure as "model proposed nothing"
`_ask` returns `None` for every exception, and `scout()` then returns
`{"proposed": 0, "note": "model proposed nothing"}`. A dead transport, a closed gate in `read`,
and a model honestly answering "I don't know" are one string. `sweep()` stamps the source as
attempted **before** the work (correctly, for rotation), so an outage burns every source's slot
and the log records a clean negative result for each. `silence.note("scout.py:_ask")` is the only
distinguishing trace. **Confidence: certain.**

### N9. `catalogue_codex.main()` returns `None`; a denied roll write still exits 0
`if __name__ == "__main__": main()` — no `sys.exit`. When `silence.write_json(ROLL, ...)` is
refused, the script prints the WRITE DENIED banner and exits **0**. Any supervisor or script
checking the return code sees a clean run. The per-record write verdict and the roll write
verdict are both honoured *in prose* and neither reaches the process boundary.
`module_index.py` in this same batch gets this right (`return 1` on a denied replace).
**Confidence: certain.**

### N10. `catalogue_codex` source→section binding: the acknowledged hazard is still live
The fallback `for k, t in sec_by_norm.items(): if n and (n in k or k in n): title = t; break`
is bidirectional and breaks on the first hit in codex order. The comment above it names the
danger correctly ("the 'Curse of Strahd pointed at the Roblox CURSE Wiki' shape") and says "No
live collision was found, which is the moment to add the guard" — but the guard added is only
the exact-match preference above it, which does nothing for the substring case. A short source
name can still bind to an unrelated section and be catalogued from it, with `provenance` naming
the wrong section. Also `sec_by_norm = {norm(t): t for t in sections}` silently drops a section
whose normalised title collides. **Confidence: certain** on the code path; the collision itself
is latent, not observed.

### N11. `scale_theories.surviving_theory()` decides physics by a string-presence test
`return {name: t for name, t in THEORIES.items() if t["falsified_by"].startswith("Nothing attested")}`
— the survivor is chosen by prose prefix, not a structured field. Rewording T3's `falsified_by`
returns `{}` (no surviving theory, silently); a new theory whose text begins "Nothing attested
yet, but…" is admitted. It also cannot fail in the other direction: it will report T3 surviving
regardless of any evidence. **Not filed as an order** — the whole module is already queued for
removal in `handoff/queue/OWNER.md` (nothing in `src/` imports it; all four public functions and
all five constants are dead), and a second order on dead code would be queue noise. Recorded so
the next reader does not re-derive it. Related, same module, same status:
`bulk_export_beta` silently returns the 64.0 floor for a negative `resident_mass_kg`;
`growth_strike` and `penetration_pressure` use `max(x, tiny)` so a zero or negative time/area
produces a finite plausible number instead of refusing.

---

## HEALTHY — verified working, recorded so it is not re-derived

**`escalation.py`**
- `_read_halt_raw` shape-check (edited earlier today) is **correct**: `FileNotFoundError` → `None`
  (the only thing allowed to mean clear), parse failure → stand-in, `null` → stand-in, non-dict →
  stand-in. `status()` can no longer hand a list or a string to a caller doing `.get()`.
- `_read_stopped` fails closed on both unparseable **and** wrong-shape, and `subsystem_stopped`
  honours `__unreadable__` by reporting *every* subsystem stopped. This is the model the rest of
  the tree should copy (cf. M2).
- The unrecognised-level policy is right and non-obvious: a typo lands at **MANAGER**, not OWNER,
  so a misspelling cannot halt the library, and the bad value travels in the evidence. `BY_NAME`
  is derived from `NAMES` rather than hand-kept.
- `brief()` is a whitelist, not a blacklist — a field added later must be admitted on purpose.
- `clear()` validates the ruling **before** the caller, deliberately, so `drill.py`'s
  `clear("")`/`clear("ok")` probes exercise the ruling rule rather than being answered by the
  wrong refusal. Order of refusals is load-bearing and is correct.
- `stop_subsystem` escalates to OWNER when the stop cannot be *recorded* — the right rung for
  the one MANAGER failure that genuinely needs everything to stop.
- `_write_stopped` uses `os.replace`, which **raises** rather than returning a verdict, so both
  its callers do get a real answer (`stop_subsystem` catches and escalates; `resume_subsystem`
  lets it propagate, leaving the subsystem stopped — fail closed).

**`standards.py`**
- The `silence.write_json(JOB_WATCH, cur)` gate (edited earlier today) is correct: the verdict is
  checked and a denied write `raise`s into the same handler that records `_dropped`, so a stale
  `prev` can no longer make `job_stamp()` structurally unable to reach `MAX_JOB_SILENCE_MIN`.
- `main()` builds `dashboard.state()` **once** and hands the same dict to `report()` and
  `work_orders()` — the double-probe is gone and the two can no longer disagree.
- `charter_regression_verdict` correctly refuses a pass in progress (`not complete and at is None`
  → `False, "pass IN PROGRESS"`), refuses a non-dict, and requires `bool(scored)` so an all-unscored
  file cannot hold.
- `context_verdict` returns `None` (not `False`, not `True`) when either side is unreadable, and
  the caller routes that to `_dropped` rather than emitting a row that reads as a pass.
- `cfg_num_ctx()` never defaults to a plausible number — the one thing that would make the context
  standard compare the runner against a literal this file invented.
- `MIN_CALLS_TO_JUDGE_RATE = tuning.MIN_CALLS_TO_JUDGE` is derived, not a second literal; there is
  nothing left to diverge.
- The `calls that succeed` UNMEASURED branch reports a thin sample as a **breach**, not a quiet
  hold, and says so in the observed string.
- The fabrication standard is appended unconditionally and `fab is not None and fab <= MAX_FABRICATION`
  — UNMEASURED correctly fails.
- `every declared floor is measured` strips comments, word-bounds the name, searches the **whole**
  file (not from `def check(` onward), and requires a **second** appearance so a declaration line
  cannot count towards its own defence. `MIN_CALLS_TO_JUDGE_RATE` and `CHARTER_REGRESSION_MAX_AGE_H`
  are both correctly reachable by that pattern.
- `provider_pool_denominator` reports the denominator with the numerator, names **every**
  unverified provider uncapped, and refuses to let `stale` absorb providers nobody could ask.
- `job_stamp` carries `at` forward while the size holds — the fix that made `quiet_min` mean
  silence rather than checker cadence.
- `_FANDOM_V4_CACHE` stores `(taken_at, answer)` and is stamped at probe **completion**; the TTL
  makes a long-lived dashboard able to change its mind about an outage.
- `_s(... holds=bool(holds) ...)` — every verdict is coerced, so no truthy string can pass as a
  hold.

**`prose_gate.py`** (reasoned about from source; never exercised against the live config)
- `gate_open` / `step4_gate_open`: strict `is not True` identity, read fresh every call, non-dict
  refused, unreadable config refused. `"true"`, `1`, `"false"` and an absent key all close it.
- `step4_gate_open` additionally requires `STEP4_PLAN.md` to exist — a gate whose precondition is a
  document checks the document is there.
- `evidence_ok`'s floor-on-the-floor is right: a non-numeric floor and any floor outside `(0, 1]`
  refuse **everything**, so a future `prose_min_cited_fraction: 0` cannot silently delete the layer.
- `cited_fraction` returns `None` (refusal) for a source absent from COVERAGE.json **and** for a
  source with `entries: 0` — no division producing a flattering zero.
- `cited_names_for` fails closed to `set()`, which makes every axis score unearned and refuses the
  block; it looks evidence up through `cachekey` so an entity cannot be credited with a
  neighbour's citations.
- `_AXIS_RE` and the `REQUIRED_PER_ENTRY` matcher both skip leading markdown decoration
  (`^[\s*_#>-]*`), so `**Wisdom:** 28` and `**Shelfmark:**` are caught — the adversarial-audit fix
  holds.
- The body-length floor (`MIN_ENTRY_BODY_CHARS`) is applied per entry and counted into `required`,
  so a four-label stub cannot score 100%. The **ghost** direction is correctly priced. Only the
  *extra* direction is not (M1).

**`scout.py`**
- `verify()`'s `needed = max(1, min(MIN_NAME_HITS, probeable))` correctly fixes a check that could
  not *pass* for a single-name source, without lowering the bar for a normal one, and returns
  `needed` alongside `hits` so the applied bar is visible.
- `sweep()`'s ordering is last-attempted-first with entry count as tie-break only, and the deferred
  set is **named in full** — the rotation genuinely rotates.
- Attempts are stamped **before** the work, so a crash cannot pin the window.
- `_land` and every `_mutate` call site honour the write verdict (`if not landed: silence.note(...)`),
  including the SCOUT.json log write, which also writes a stderr line distinguishing "no entry for
  that cycle" from "that cycle never ran".
- `hostless()` reads `F.HOSTS` with no `try`, so a missing/corrupt host map crashes the sweep
  rather than reporting "no source is hostless" — correct direction (contrast M2, which is the
  *write* side of the same file).
- `_names_in` requires a boundary either side and skips names under 4 characters.

**`feats_index.py`**
- `_norm` is deliberately strict and the docstring was corrected after measurement rather than
  left claiming a capability the code lacks.
- `load_index` asks the record for its own `host` instead of trying to invert `cachekey.host_dir`,
  and derives the fallback map through the one helper — the only sound direction.
- `_CACHE` is keyed by the path asked for, so a non-default argument cannot be answered with the
  default path's result.
- `feats_for_source` is ranked (`-feat_count`, then name) and never truncated; shared hosts
  deliberately attach an entity to both sources.

**`catalogue_codex.py`**
- `slug`/`record_path` delegate to `catalogue_aurora` — one implementation in the tree, and the
  60-character identity cap is gone with a legacy-prefix fallback so a truncated record is reunited
  rather than duplicated.
- The per-record write is gated on `pipeline.write_record_catalogue`'s verdict and the roll row is
  left untouched on denial, so a `entry_count == 0` selection still revisits it.
- `attestation: "Transcribed"`, `synthesis: None`, `scale_note: ""` and the honest fallback
  description ("No transcribed description on file…") all refuse to invent content.
- `parse_codex`, `load_register_index` and the roll read have no `try` — a missing codex crashes
  rather than cataloguing nothing.

**`module_index.py` — CLEAN.**
- Writes to a pid+thread temp file and **checks** `replace_retry`'s verdict, returning `1` and
  writing a stderr line naming the previous-page situation. This is the pattern N9 says
  `catalogue_codex` lacks.
- The hand-kept `GROUPS` list cannot silently drop a module: unknown names are reported to stderr
  and noted, and every module outside the groups lands in "Everything else".
- No count is written into prose anywhere — the docstring explains why, and the code obeys it.
- `first_line` degrades to `(no docstring)` / `(unparseable)` and still lists the module.

---

## Method note

`standards.check()` was **not** run live: it opens TCP connections to Cloudflare, spawns
`tasklist` and a 60 s `Get-CimInstance`, walks `data/readfeats`, and writes
`state/job_progress.json`. A live crawl and a mutation pass were running. Every standards finding
above was instead reproduced by executing the **exact source line ranges** in an isolated
namespace with `HERE` redirected to an empty temp directory, or by an AST walk of `check()`.
`scout._mutate` was driven against scratch copies in a temp directory; no file under
`data/` or `state/` was written by this audit.

---

## Orders filed (16)

| id | code | severity | handler |
|---|---|---|---|
| 212e3096edfc | PROSE_GATE_EXTRA_ENTRIES_FREE | MAJOR | RUN |
| 17e6cba194ce | SCOUT_MUTATE_WIPES_CORRUPT_ARTIFACT | MAJOR | RUN |
| 1ebd28c8cd85 | STANDARDS_FABRICATED_ZERO_ON_UNREAD_INPUT | MAJOR | RUN |
| b901c088890e | STANDARDS_DUPLICATES_VANISHES_UNRECORDED | MAJOR | RUN |
| d2085b1d8dd3 | ESCALATE_DISCARDS_HALT_WRITE_VERDICT | MAJOR | RUN |
| 4b308c6b750d | HALT_CLEAR_CLI_SAYS_NOTHING_WAS_HALTED | MAJOR | RUN |
| e16a93099bbe | FEATS_INDEX_SWALLOWS_HOST_MAP_FAILURE | MAJOR | RUN |
| ddb5eadd8934 | RESUME_SUBSYSTEM_HAS_NO_PERSON_CHECK | MINOR | SESSION |
| c426af1de74f | STANDARDS_EMPTY_REFERENCE_ASSAYS_READS_GREEN | MINOR | RUN |
| b8686a5c9772 | STANDARDS_CONDITIONAL_STANDARDS_VANISH | MINOR | RUN |
| 1def9a6ce0d5 | STANDARDS_JOB_WATCH_FAILS_OPEN_PER_JOB | MINOR | RUN |
| dddf4d96bb3e | STANDARDS_CONTEXT_READ_OFF_WRONG_RUNNER | MINOR | RUN |
| e8cd908ce5e4 | EVIDENCE_AND_IDENTIFIER_CAPS_BATCH04 | MINOR | RUN |
| 7f2cbf26a60e | SCOUT_TRANSPORT_FAILURE_READS_AS_NO_PROPOSAL | MINOR | RUN |
| 0e8ef2e30f2b | CATALOGUE_CODEX_EXITS_ZERO_ON_DENIED_ROLL_WRITE | MINOR | RUN |
| 5da00dda2c8e | CODEX_SUBSTRING_SECTION_BINDING_STILL_LIVE | MINOR | RUN |

Not filed, deliberately: N2 (both no-programmatic-clear layers miss a `subprocess`/`runpy`
shell-out — inherent to an autonomous actor having a shell, recorded so the guarantee is not
over-read) and N11 (`scale_theories.surviving_theory`'s string-presence test — the whole module
is already queued for removal in `handoff/queue/OWNER.md`, and a second order on dead code is
queue noise).

Coverage recorded via `sweep_plan.record('run37', [...8 modules...], batch=4)`; all eight now
carry `{'run': 'run37'}`.
