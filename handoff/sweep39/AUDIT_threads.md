# run39 — AUDIT: the entanglement pass (`threads.py`, `thread_integrity.py`)

Independent audit of the two modules written or changed on 2026-08-31, neither of which had been
reviewed by anybody. Both read **in full, no sampling** (Hard Rule 0).

| module | lines | state |
|---|---|---|
| `src/threads.py` | 399 | NEW today — Step 4 Phase 4.1, the T1/T2 pass |
| `src/thread_integrity.py` | 349 | CHANGED today — `main()` returns a verdict; module ends `sys.exit(main())` |

Also read to check the claims these two make: `STEP4_PLAN.md` (all of it, not only §§1/4/6/7/8),
`src/drill.py:5544-5645` (the nine new nets), `src/allsweep.py:110-200,300-345,700-725`,
`src/address.py:51-219` (`spine_code_for`), `src/prose_gate.py:90-124`,
`src/silence.py:471-531` (`write_json`), `src/weave_index.py:276-302` (`load_records`),
`src/escalation.py:640-656`, and the live queue in `state/workorders.json`.

Read-only. No source file was edited. `data/THREADS.json` was **not** created and does not exist;
`config.yaml:132` still reads `step4_enabled: false`. The only executions were
`python src/threads.py --dry-run` (writes nothing), `python src/thread_integrity.py` (writes
nothing), `src/liveness.py`, and three scratch probes kept in the session temp area — nothing
under `handoff/`.

**A caution about the numbers below.** `data/records/` is being written while this audit runs
(newest mtime 23 s before one probe). `build()` is deterministic within a process — proved by
building twice off one record list and hashing both graphs (`dbbdce6f…` twice) — but T2 rose
605,630 → 605,670 → 605,710 across three runs at a *constant* 282,822 entries, which is
consistent with category strings churning under the corpus rather than entries being added. See
T-2, which is about exactly that vocabulary.

---

## MAJOR

### T-1 — `threads.py:363` the CLI crashes on this machine's console, every time, on both interpreters

`main()` prints, before the gate and before the write:

```python
print("   recorded source\u2192source directions: %s" % format(len(recorded_pairs(graph)), ","))
```

U+2192 is not in cp1252, and `sys.stdout.encoding` is `cp1252` under **both** the documented
interpreter and the system one. Reproduced:

```
$ python src/threads.py --dry-run
   sources with NO address  : 0
Traceback (most recent call last):
  File "...\src\threads.py", line 399, in <module>   sys.exit(main())
  File "...\src\threads.py", line 363, in main
UnicodeEncodeError: 'charmap' codec can't encode character '\u2192' in position 18
```

```
$ C:/Users/imarl/miniconda3/python.exe -c "print('a\u2192b')"
UnicodeEncodeError: 'charmap' codec can't encode character '\u2192' in position 1
```

Everything else in the report survives — `—` (U+2014) and `§` (U+00A7) are both in cp1252, which
is why only this one line dies. Set `PYTHONIOENCODING=utf-8` and the same command completes and
prints `recorded source→source directions: 1,646` and the gate line.

Why it is not caught anywhere:

* `threads.py` is the **only** module in `src/` that prints a literal `→` to stdout
  (`grep -rln $'→' src/*.py` returns exactly one file).
* It is a hand-run CLI. Nothing launches it as a subprocess — `grep -rn 'threads\.py' src/*.py`
  outside the file itself returns only `drill.py:5554,5591,5635`, which *import* it and read its
  parse tree. So it never inherits the `PYTHONIOENCODING="utf-8"` environment that
  `allsweep.py:80`, `foreman.py:87`, `overwatch.py:89`, `overnight.py`, `autostart.py` and
  `local_agent.py` all set for their children, and it has no
  `sys.stdout.reconfigure(encoding="utf-8", errors="replace")` of its own — the idiom
  `handbuilt.py:470` uses for the same problem.
* The nine drill nets never invoke `main()`. Net 8 asks the *parse tree* whether `main` calls
  `prose_gate.step4_gate_open`; net 9 asks the gate directly. Neither runs the CLI, so a net
  green today coexists with a CLI that cannot finish.

Consequence, and it is the whole deliverable: line 363 sits **before** the `problems` check
(:364) and **before** the ratification gate (:374-387). So the crash is not confined to
`--dry-run` — on the day the owner sets `step4_enabled: true`, the pass will derive the graph,
crash on this print, and write nothing, with a traceback and rc=1. Nothing is corrupted (the
write is never reached), and no automation depends on the module today, which is why this is
filed MAJOR and not BLOCKING.

### T-2 — `threads.py:155-167,232-233` the T2 cohort key space is two vocabularies, and ~17,000 lawful cohort threads are silently absent

`_category_of` takes `topic` first and `category` second, and its docstring states the premise
the design rests on:

> `topic` first, `category` second: **both are present on every entry measured** … Cohorting on
> the short form groups **the seven catalogue categories** the way the roll does.

Measured against the live corpus (210 record files, 282,822 entries):

| | count |
|---|---|
| entries carrying `category` | 282,822 (100%) |
| entries carrying `topic` | **138,886 (49.1%)** |
| entries carrying neither | 0 |
| sources whose entries are short-form only | 175 |
| sources carrying **both** styles among their own entries | **35** |
| distinct category keys in the built graph | **16** |
| distinct `topic` values | **9** — `Events, Factions, Media, Persons, Places, Powers, Relics, Wars, Weapons` |
| distinct `category` long forms | 7 |

Both halves of the docstring's premise are false: `topic` is on half the corpus, and the short
form has nine values, not seven — `Weapons`, `Relics` and `Wars` are re-cuts of
`Vessels & Things (…)` and `Events (…)`, not synonyms of them.

Cohort membership is exact string equality:

```python
sibs = sorted(s for s in siblings.get(parent_of(code), ()) if s != code
              and cat in cats_at_code[s])        # threads.py:232-233
```

So `"Persons"` and `"Persons (named individual characters, real or fictional)"` are two
different rooms. A sibling volume that holds the same catalogue category under the other
spelling never cohorts, in either direction. Counterfactual, measured on the same graph with a
crude fold of the long form to its head word:

```
T2 edges as built : 605,710
T2 with folded keys: 622,664      missed: 16,954   (+2.8%)
```

16,954 is a **floor**, not the number: my fold still leaves `Weapons`/`Relics`/`Vessels` apart,
so a real reconciliation recovers more. The failure is in the safe direction — it produces
*missing* threads, never wrong ones — but it is exactly the shape Hard Rule 0 exists to forbid:
nothing fails, and the artifact silently decides those relations do not exist. It is also not
visible in the report: the counts block prints 605,710 with no denominator.

---

## MINOR

### T-3 — `threads.py:284-308` `verify()` cannot fail on anything `build()` produces, and the refusal it feeds is dead code

Each of the four checks, against the current source:

1. `if not edges:` (:295) — `edges = [rec["T1"]] + [e for lst in rec["T2"].values() for e in lst]`
   (:293). A list literal with one element, concatenated. It is never empty. This is a
   tautology in the strict sense: no input can make it true.
2. `if e.get("class") not in DERIVABLE:` (:299) — every edge in the graph came from `edge()`
   (:229, :236), which raises `ThreadRefused` for any class outside `DERIVABLE` (:141). Nothing
   else constructs an edge dict.
3. `if e.get("to") not in known:` (:302) — `verify`'s `known` is `{v["code"] for v in
   sources.values()}`; `build`'s `known` is `{c for c in code_of.values() if c and c !=
   UNADDRESSED}`, and `build` emits a source **iff** its code is in that set (:216-222). The two
   sets are equal by construction, and every `to` is drawn from it (T1 is the source's own code,
   T2's `sibs` ⊆ `siblings[parent]` ⊆ `known`).
4. `if rec["T1"]["to"] != rec["code"]:` (:305) — `home = edge(code, "T1", …)` and
   `out[src] = {"code": code, …, "T1": home}` (:229, :240-241). The same local variable on both
   sides of the comparison.

Confirmed empirically: `verify(g)` returns `[]` on the full live corpus, and the drill's own net
asserts `TH.verify(g) == []` on its fixture. The consequence is that `main()`'s
`REFUSING TO WRITE — the derived graph breaks its own promises` branch (:364-369) is unreachable.

This is defensible as defence-in-depth for a graph read back from disk, and if that is the
intent it should say so — nothing reads `THREADS.json` yet, so no caller exercises it that way.
What is *not* defensible is where check 1 sits: it is written as the guard for §6's "quiet one"
(the message even cites §6), and it is placed on the one expression that can never be empty,
while the path that actually produces an empty thread section is unguarded. See T-4.

### T-4 — `threads.py:266-281` `threads_for()` hands back a blank for an unaddressed source, and cites a refusal that does not exist

```python
rec = (graph.get("sources") or {}).get(source)
if not rec:
    return []
```

An entry in a source with no resolvable spine code gets `[]` — no exception, no marker, no
`ThreadRefused`. STEP4_PLAN.md §6 rules that this must be an **OPERATOR-level refusal, not a
blank**, and `threads.py:68-71` repeats that promise in its own module docstring. Verified:
`TH.threads_for(g, "NoSuchSource", {"topic": "Persons"})` returns `[]`.

The docstring one line above the code compounds it:

> Every entry gets its home volume by construction, so this can never return an empty list for
> an addressed source — **see `verify`, which treats an empty one as an OPERATOR-level fault**

`verify` does no such thing. It appends a string to a list which `main()` prints and returns 1
on; it never touches `escalation`, and per T-3 it cannot reach that string in any case.

Latent today — `build()` reports 0 unaddressed sources on the live corpus (the plan's
`Bone (Jeff Smith)` now resolves through `spine_code_for`), so `build`'s `refused` branch
(:216-222) takes no traffic. It goes live the first time a source is added to the roll ahead of
the Acquisitions Index, which CLAUDE.md Hard Rule 2 says is the ordinary case.

### T-5 — `thread_integrity.py:225-234` the propagation failure is swallowed, and two conditions share one message

```python
try:
    import propagation as P
    adj = P.load_graph()
    def dist(a, b): ...
except Exception:
    dist = None
    print("(propagation graph unavailable; asymmetry cannot be excused by distance)")
```

A bare `except Exception` over both an import and a graph load. "The module is missing", "the
graph file is corrupt", "`load_graph` raised" and anything else print the same sentence, and the
exception type is never named. There is no `silence.note(...)`, so unlike the rest of this
project the swallow does not reach `state/failures.json` either — `silence.py` is a battery
verifier precisely so swallowed failures are countable, and this one is not counted.

It matters more than it looks once `recorded=` is wired in Phase 4.2: `excuse` can only be set
inside `if distance_fn:` (:182-185), so with `dist = None` **every** one-way thread lands in
ASYMMETRIC-SUSPECT and the ASYMMETRIC-LAWFUL class becomes unreachable. The waiver mechanism
fails silently in the direction of noise, under a one-line notice that reads like a footnote.

### T-6 — `thread_integrity.py:339-345` + `allsweep.py:181,719-723` the new verdict reaches the exit code and stops there (QUESTION)

*Filed as a QUESTION: two readings are defensible.*

The return value itself is **correct**: `dangling = counts.get("DANGLING", 0);
return 1 if dangling else 0`, `DANGLING` is a real key of the Counter, and the module ends
`sys.exit(main())` (:348-349). Verified live — the module runs clean and exits 0, with
`IMPLIED-UNRECORDED 5,782 (100.0%)`, `DANGLING` and `PARTIALLY-DANGLING` absent, exactly the
"measured before landing" figures the comment at :336-338 claims.

The classes it grades are also the right ones, and the argument at :324-334 holds:
IMPLIED-UNRECORDED is 100% by construction until Step 4 ships, so grading it would be the
alarm-that-always-sounds; §8 names only DANGLING as the release gate; §7C says ASYMMETRIC is
reported, never failed, through Phase 4.2. PARTIALLY-DANGLING ungraded is the one arguable call,
and the reasoning given (degradation, not a pointer at nothing) is sound.

`allsweep.py:181` agrees with it — RC_FINDINGS is the right classification for a
"rc=1 means I have findings" contract, the same as `silence.py` and `audit.py`, and reclassifying
it in the same change was necessary rather than optional.

**The question is what happens next.** For an RC_FINDINGS row, `failed` is false
(`allsweep.py:329`), and the tail is printed only `if r.get("failed") or r["crashed"] or
r.get("timeout")` (:720). So on a run where every implied thread is DANGLING, the sweep prints
one line —

```
   findings  thread integrity            12.3s   rc=1 (findings)
```

— suppresses the uncapped DANGLING listing that `main()` went to such lengths to print, files no
work order, and stays green. STEP4_PLAN.md §8 rules that `DANGLING > 0` is a **SUPERVISOR-level
refusal for that source**; `thread_integrity.py` never imports `escalation` and never calls
`escalate()`, and nothing else reads its verdict.

Reading A: a hole — the verdict is computed, printed, exit-coded, and acted on by nobody, which
is the same "computed, printed and dropped" shape `allsweep.py:110-113` records for LINT and
ESTATE. Reading B: wiring `thread_integrity` into the battery **is** Phase 4.2, which §7E
explicitly does not authorise, so escalating now would be doing unratified work. Both are
honest. It needs a ruling, not a patch, and it should not be forgotten when 4.2 is authorised.

---

## INFO

### T-7 — `threads.py:284,311` dead parameters, and a branch nothing takes

* `def verify(graph, code_of=None)` (:284) — `code_of` is never referenced in the body.
* `def recorded_pairs(graph, code_of=None)` (:311) — likewise; the function rebuilds `at_code`
  from `graph` itself.

Both are constants nothing reads, on the two functions Phase 4.2 is meant to wire up, so they
read as a contract that does not exist. `build`'s `unaddressed` branch (:216-222) is a third
path with no traffic today (0 unaddressed sources measured) — correct code, but unproven by any
run, and no drill net drives it.

`src/liveness.py` reports neither module: 47 findings, none in these two files, and 0 tautologies
overall. Its tautology check is mechanical (`x == x` shapes), so the structural ones in T-3 are
outside what it can see — worth knowing before treating a green liveness as coverage here.

### T-8 — `threads.py` docstring claims that the measurement contradicts

Checked one by one against the current file and the live data:

| claim | where | verdict |
|---|---|---|
| "282,822 entries collapse to 1,370 (source, category) keys" | :49-50 | **TRUE** — measured exactly 1,370 |
| "282,822 entities" | :9 | **TRUE** |
| "every entry sharing a key gets a byte-identical thread list, and none comes back empty" | :50-51 | **TRUE** for addressed sources; expansion cross-checks (see below) |
| "There is no `[:n]` anywhere in this pass" | :73 | **FALSE as written** — `parts[:2]` at :120. It is an address decomposition, not a listing cap, so the *rule* is honoured; the absolute sentence is not, and this file's own audience reads that sentence as a checked fact |
| "Ten siblings is the measured worst case today" | :235 | **WRONG** — measured max cohort is **9** (histogram: 0×465, 1×102, 2×122, 3×100, 4×159, 5×190, 6×157, 7×21, 8×13, 9×41) |
| "both are present on every entry measured" / "the seven catalogue categories" | :158-161 | **FALSE** — see T-2 |
| plan §2: "`thread_integrity.py` (184 ln)" | STEP4_PLAN.md:49 | stale — the file is 349 lines (317 at batch 08 this morning) |

Cross-references that are **correct** and should not be re-checked next sweep:
`thread_integrity.py:286` cites ":188" for where ASYMMETRIC-LAWFUL's detail is computed — line
188 is exactly `detail["ASYMMETRIC-LAWFUL"].append((src, dst, excuse))`. Every `STEP4_PLAN.md §n`
citation in both modules resolves to the section it claims (§1, §4, §6, §7B, §7E, §8), and §7E
does say "PHASE 4.0 AND 4.1 ONLY".

The counts block was verified rather than trusted: expanding the graph per entry through
`threads_for` over the whole corpus gives T1 282,822 / T2 605,670 against a counts block of
282,822 / 605,670 in the same process. The normalised store really is lossless for T1/T2.

### T-9 — `threads.py:109-120` 60 of 210 sources can never carry or receive a cohort thread (QUESTION)

`parent_of` returns `None` for any code with fewer than three components, which is deliberate and
argued (:112-115: cohorting at Collection level "would put every D&D supplement in a room with
every anime"). The scale is not stated anywhere:

* 26 of the 93 distinct emitted codes have two components — `II.A`, `II.C` … `II.Q`, all eleven
  `III.n` pantheons, `VII.6`, `VII.7`.
* **60 of 210 sources** (29%) sit at one of those codes. Their entries carry exactly one thread,
  the home volume, forever.
* **465 of the 1,370 (source, category) keys** get an empty cohort list.

There is also an asymmetry worth a ruling: a source at `II.A.3` cohorts with other `II.A.n`
volumes but never with a source shelved at bare `II.A` — which is the Set those siblings live in.
Whether that is right is curatorial. What is certainly missing is that nothing surfaces it: the
CLI reports "sources with NO address: 0" and no line for "sources with no cohort", so a reader
cannot tell "this volume has no siblings" from "the cohort pass did not reach it" — a smaller
version of §6's quiet one, one level up.

### T-10 — `thread_integrity.py:222,236-244,342` the report counts three different things and calls them all threads

Verified from a live run:

```
implied thread directions        : 11,564      <- len(pairs), DIRECTED (a,b) and (b,a) both
  IMPLIED-UNRECORDED    5,782  (100.0%)        <- classify() dedupes to UNORDERED pairs
```

The two numbers describe the same population and differ by exactly 2×, with nothing on the page
saying so; the percentage denominator (`total = sum(counts.values())`, :237) is the deduped one,
so the percentages are internally right and externally confusing.

The failure line inherits it: `f"THREAD INTEGRITY FAILED: {dangling:,} thread(s) point at
nothing"` (:342) counts **pairs of sources**, not threads — each DANGLING row prints `n/tot` keys
gone, so one "thread" in that sentence can stand for a hundred vanished entities. On the one line
that will ever be read as a release gate, the unit should be the one §8 rules on.

---

## Checked and NOT a finding — recorded so nobody re-runs these

* **Can a T3/T4/T5 edge be produced?** No. `edge()` (:128-152) is the only constructor of an edge
  dict in the module, and it refuses any class outside `DERIVABLE = ("T1", "T2")` before it does
  anything else. `build` calls it with the string literals `"T1"` and `"T2"` only. Nothing else
  in `src/` imports `threads` except `drill.py`. The §7B ruling is honoured in code, and drill
  nets 5 and 6 attack it (`cls="T5"`, then `"T3"` and `"T4"`), with a `refused()` helper that
  correctly counts a `TypeError` as a broken probe rather than a refusal.
* **Can a thread be emitted at an address that does not resolve?** Not by this code. Every `to`
  is a value returned by `address.spine_code_for`, which returns either a code read out of
  `data/CHARTER_SPINE_CODES.json` or the literal `"UNASSIGNED"` (`address.py:60-219`) — it never
  mints a code. Verified end-to-end: all 93 distinct emitted codes are present in the charter
  file's 96 values, and no emitted code has more than three components. The check inside `edge()`
  is nonetheless unreachable from `build` (both call sites pass values already proved to be in
  `known`), so the *live* mitigation is the `if code not in known: continue` at :216, not the
  refusal — which is fine, but it means drill net 1 proves the refusal works, not that the pass
  uses it.
* **Name similarity justifying a thread.** `threads.py` never calls `entity_match`, never
  compares two entity names, and never pairs entities at all — confirmed by reading and by grep.
  The only fuzzy matching anywhere near it is `spine_code_for`'s source-title resolution, which
  is the pre-existing address layer with its own hardening history and its own drill nets, and it
  is used here for addressing rather than for identity. §6's failure mode is not present.
* **Truncation.** No `[:n]` in either module's live code paths besides `parent_of`'s `parts[:2]`
  (T-8) and `_namecol`'s historical note. Both files' listing loops are uncapped and print their
  own totals. `allsweep` truncating a child's output at `tail[-14:]` and `ln[:150]` is the
  battery's own display, not these files'.
* **Duplicate sources in the corpus.** `survey` assigns rather than accumulates
  (`n_of[src] = len(entries)`, `cats_of[src] = cats`), so two record files naming one source
  would silently lose the first. Checked: 210 record files with entries, **zero** duplicate
  `source` values, so the hazard is theoretical today.
* **Divide-by-zero in the percentage loop** (`thread_integrity.py:243-244`) — guarded by
  `if counts.get(k)`, which cannot be true when `total` is 0. Safe.
* **`escalation.assert_clear` missing from `thread_integrity.main()`.** It is missing, but so is
  it from `audit.py`, `silence.py`, `coverage.py`, `identity.py`, `anchors.py`, `reference.py`
  and `rosetta.py` — 7 of the 9 read-only verifiers. `threads.py` does call it (:344), correctly,
  because it can write. This is the house pattern for pure reporters, not a gap in today's change.
* **`classify`'s `if gone and len(gone) == len(shared)`** (:130) — the `gone and` is redundant,
  since `pairs[(a,b)]` always holds at least one key so `shared` is never empty. Harmless, and
  correct if it ever were. Not filed; the always-false `(a, b) in seen` disjunct on :125 is
  already filed as `THREAD_INTEGRITY_ALWAYS_FALSE_DISJUNCT` (INFO, sweep39-batch08) and is not
  re-filed here.
* **`_namecol(rows, i=0)`** — `i` is never passed by any of the five call sites. A dead parameter,
  one line, no behavioural effect; recorded here rather than filed.
* **The shelfmark deviation is genuinely recorded**, as `threads.py:54-56` claims:
  `THREADS_JSON_NOT_KEYED_BY_SHELFMARK_AS_THE_PLAN_SPECIFIES`, MINOR, OWNER, found_by
  `step4.1 build 2026-08-31`, is in the live queue. The deviation itself is sound — per-entity
  shelfmarks do not exist (Hard Rule 4), and the normalised store is lossless for T1/T2, which I
  verified by expansion rather than taking on trust.
* **The nine drill nets exist and attack what they claim** (`drill.py:5556-5645`): dangling,
  UNASSIGNED, empty string, a positive control, T5, T3+T4, every-addressed-entry-has-a-home
  (against a fixture, with `spine_code_for` monkeypatched and restored in a `finally`), an AST
  check that `main` calls `step4_gate_open` reachably, and the gate being shut right now. Two
  observations, neither filed against these two files: the last net duplicates
  `drill.py:1018-1020`, which already asserts `not PG.step4_gate_open()[0]` in the gates area, so
  the day the owner ratifies, **two** nets breach and a BREACHED net halts the library by itself
  (that is the established house pattern for the prose gate, so it is a known cost, not a new
  one); and no net invokes `main()`, which is why T-1 is invisible to a green drill.

---

## Orders filed

All `found_by="audit-threads-2026-08-31"`, all `handler="RUN"` (`thread_integrity.py` is not on
`local_agent.DENYLIST`, but `threads.py` is new and unproven and the two are one change).

| code | sev |
|---|---|
| `THREADS_CLI_CRASHES_ON_CP1252_CONSOLE` | MAJOR |
| `THREADS_T2_COHORT_SPLIT_ACROSS_TWO_CATEGORY_VOCABULARIES` | MAJOR |
| `THREADS_VERIFY_CANNOT_FAIL_AND_ITS_REFUSAL_IS_DEAD` | MINOR |
| `THREADS_FOR_RETURNS_A_BLANK_FOR_AN_UNADDRESSED_SOURCE` | MINOR |
| `TI_PROPAGATION_FAILURE_SWALLOWED_AND_CONFLATED` | MINOR |
| `TI_DANGLING_VERDICT_STOPS_SHORT_OF_THE_LADDER` | MINOR (QUESTION) |
| `THREADS_DEAD_PARAMS_AND_AN_UNTRAVELLED_BRANCH` | INFO |
| `THREADS_DOCSTRING_CLAIMS_CONTRADICTED_BY_MEASUREMENT` | INFO |
| `THREADS_T1_ONLY_FOR_60_OF_210_SOURCES` | INFO (QUESTION) |
| `TI_REPORT_MIXES_DIRECTIONS_PAIRS_AND_THREADS` | INFO |
