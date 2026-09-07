# run46 / batch 2 — `src/verify_math.py`

Read end to end, all 10,475 lines, 2026-09-07. Read-only: nothing in `src/` was edited, and the
battery was not run (a 20-hour mutation pass is taking its baseline from the live tree).

Every claim below was checked against the executable line, and every claim about behaviour was
measured rather than reasoned. Where I measured, the command and the numbers are given.

---

## Summary

Three findings filed. In priority order as the brief asked:

1. **A check that is green against its own defect on 23% of hash seeds** — §19n's tie-break rows,
   the direct sibling of the row removed from §16 today. Measured across 13 seeds.
2. **The rows that make this suite non-deterministic** — identified and enumerated. They are the
   live `dashboard.state()` / `standards.check()` / `overnight._proc_lines()` calls, and the
   larger half of that is already owned by order `74f1bc47da2a`.
3. **Another `SF.build()`** — the same six call sites are also *ledger-escape* sites. This half is
   owned by nobody. It is the mechanism that turns a transient machine fault into a red §20z,
   and a red §20z cancels the whole mutation pass.

Plus two questions and a set of smaller notes.

---

## FINDING 1 — §19n's tie-break rows are a hash-seed lottery (order filed: see below)

**Where:** `src/verify_math.py:2897-2917`.

§16 records, at :1574-1582, that a permuted-input comparison was written for `affinity_order`,
found to be *a row that CANNOT FAIL*, and removed rather than kept — because two module loads in
one interpreter share `PYTHONHASHSEED`, so a set iterates identically in both. §16 replaced it with
a frozen expectation and a source row.

**§19n still carries that exact construction**, against the same idiom (`max(set(xs), key=count)`),
and it was not part of that repair. Line :2905-2906:

    check("and does not depend on the order the values arrive in",
          _mode_stable(["classical", "compact"]), _mode_stable(["compact", "classical"]))

I measured all four of §19n's behavioural rows against the defect they name — `_mode_stable` with
the `, v` tie-break deleted — under `PYTHONHASHSEED` 0-9, 42, 99 and 1234:

| row | asserts | GREEN under the defect |
|---|---|---|
| :2902 | `_mode_stable(["compact","classical"]) == "compact"` | 5 of 13 seeds |
| :2905 | permuted inputs agree | **12 of 13 seeds** |
| :2907 | a clear majority still wins | 13 of 13 seeds |
| :2910 | `_mode_stable(["a","b","c"]) == "c"` | 4 of 13 seeds |

Two consequences, and the second is the one that matters:

* :2905 is the §16 row. It detects the defect it exists for on one seed in thirteen.
* **On seeds 0, 3 and 5 — roughly one run in four — every one of the four behavioural rows is
  green against the defect simultaneously.** `PYTHONHASHSEED` is unset in production, so this is a
  fresh lottery every run.

:2907 is *not* a fault: a majority never reaches the tie-break, and the row's own note says it is
guarding against the tie-break becoming a plain lexicographic sort. It is doing its stated job.

**What actually holds §19n today** is the source row at :2912-2917, which greps `navtree.py` for
`key=lambda r: (regs.count(r), r)`. That row is deterministic and always catches. So the section is
not undefended — but its four *behavioural* rows are decoration, and a reader counting rows would
conclude otherwise. §16 was given a frozen expectation for precisely this reason; §19n was not.

**Remedy is additive** — nothing is removed. Give §19n the §16 treatment: a frozen expectation over
an all-tied fixture of several distinctly-named values, so the answer is pinned rather than
compared to a permutation of itself.

Reproduction (read-only, no project code imported):

    def fixed(xs): return max(set(xs), key=lambda v: (xs.count(v), v))
    def buggy(xs): return max(set(xs), key=xs.count)

run under `PYTHONHASHSEED` 0 and 3, comparing the four predicates above.

---

## FINDING 2 — the rows that make this suite non-deterministic

The brief asked which rows make the battery non-deterministic run-to-run, and named four
`BASELINE DRIFTED on clean code (verify_math)` events costing ~7 mutant verdicts each.

**They are the rows that call the live dashboard, the live standards checker, and the live process
table.** Enumerated at source:

| line | call | what it touches |
|---|---|---|
| :4643 | `_D20.jobs()` | `state/read_auto.log`, `state/roll_auto.log`, lognames import |
| :4725 | `_on21._proc_lines()` | PowerShell/WMI enumeration of the live process table, 60 s timeout |
| :4008 | `_STx.check(st)` inside `_pool19ai` — invoked **6×** (:4014, :4022, :4024, :4031, :4035, :4044) | the whole standards battery, per call |
| :5793, :5823 | `_dash20k._read_row(...)` | fixture log (safe) |
| :5834 | `_dash20k.state()` | every panel, **and `standards.check()` internally** (dashboard.py:739) |
| :5838, :5861, :5876 | `_stmod20k.check(...)` | the whole standards battery, ×3 |
| :7463 | `standards.check(dashboard.state())` | ×2 (state calls check itself) |
| :7953, :7967 | `dashboard.state()`, then `standards.check(_state_b3)` | ×2 |

`dashboard.state()` calls `standards.check(s)` itself, so **`standards.check()` executes roughly
fifteen times per battery run.** Each full execution performs, verified at source in
`src/standards.py`:

* `fandom_ipv4_reachable()` (:1675) — a real DNS lookup and TCP connect to a `*.fandom.com` host,
  on a machine CLAUDE.md records as IP-banned from fandom;
* `ollama_token_flow()` (:1901) — a real generation posted to `localhost:11434`, `timeout=300`;
* `urlopen("http://localhost:11434/api/ps")` (:1768);
* a PowerShell spawn for the duplicate-job standard;
* ~28 reads of live `state/` and `data/` artefacts, each behind a `_dropped.append` handler that
  *deletes* its standard's row when the read raises.

Both network probes carry a 300 s TTL, so within one run they are cached after the first call — but
the first call is a genuine coin flip, and the file reads are not cached at all.

**This half is already filed.** Order `74f1bc47da2a` (SESSION/MAJOR, `sweep45-batch02`) names the
same call sites, the same network work, the ~28 `_dropped.append` handlers, and the two rows that go
red off them (`_missing_b1 == []` at :7464-7470, and batch3's set-difference at :7996-8002, whose
own note claims an immunity to flapping that it does not have). I confirmed every mechanical claim
in that order against current source and found it accurate. **I have not duplicated it.**

Two sites it does not name, which I have added to my own order below because they leak (Finding 3)
as well as flap: `_D20.jobs()` at :4643 and `_on21._proc_lines()` at :4725.

`_proc_lines` deserves a sentence of its own. §20v's own comment at :4728-4737 records that two
sibling rows were *removed* from this section for depending on "who else is on the machine". The
third one — `check("the process probe returned a listing at all", bool(_probe21), True)` at
:4726 — was left. `overnight._proc_lines` returns `None` when the PowerShell spawn raises or comes
back empty (overnight.py:152-157), so this row reddens on a busy machine, which is the one
condition under which a 20-hour mutation pass runs.

**Secondary, and by design rather than by accident:** §13's Phase-4.2 rows (:1356-1379) read
`data/THREADS.json` and `state/THREAD_INTEGRITY_FLOOR.json` live, and §16 builds the whole
sevenfold shelving from the live corpus (:1522-1628). Those are release gates whose subject *is*
the live corpus; I flag them as known-live rather than as faults.

---

## FINDING 3 — another `SF.build()`: six unwrapped ledger-escape sites

This is the finding the brief asked for by name, and it is the same six call sites wearing their
other face.

**The mechanism, verified end to end:**

1. `silence.note(site)` does `import health; health.record(...)` (silence.py:815-818).
2. `_H_vm.record` has been replaced by `_spy_record_vm` since verify_math.py:232.
3. `_spy_record_vm` appends to `_LEDGER_ESCAPES_VM` **unconditionally** — the frame filter at
   :222-224 only decides *what name* is recorded, and a call from outside the battery is recorded
   as `<outside the battery>` rather than dropped (:226-228).
4. §20z:10013 asserts `_escaped20z == []`, and §20z:10003 asserts `_wrote_to_the_ledger_vm(...) == []`
   over `health.LEDGER`, which `record` also fills.
5. `mutate.py` refuses to run on a red baseline. **A red §20z cancels the whole mutation pass.**

`standards.py` carries ~40 `silence.note("standards.py:*")` sites and `dashboard.py` ~31
`silence.note("dashboard.py:*")` sites, every one of them on the read-failure path of a live
artefact. `overnight._proc_lines` notes `overnight.py:proc-lines` and `proc-lines-blind`
(overnight.py:152, 156). None of the six call sites listed in Finding 2 is inside `_no_ledger_vm()`
or `_third_party_vm()` — the only wrapped `standards.check()` in the file is :7976, the
deliberately-broken-`open` run, and its clean twin at :7967 is bare.

**This is §16's fault exactly.** §16's own comment at :1511-1521 records `SF.build()` reaching
`weave.load_index()` and putting `weave.py:index-stale` into `state/failures.json` on every run,
reddening §20z's two ledger rows; it was wrapped on 2026-09-06. The comment also says the leak was
*"invisible until then only because the battery was crashing at §20u before §20z ran"* — so §20z has
only recently begun to see anything at all, and these six sites have never been looked at through it.

The exposure is larger than §16's by an order of magnitude: one note class there, ~70 possible
classes here, on read paths that fail exactly when the machine is loaded.

Order `895a99602bf0` (OWNER/MAJOR) names §16's leak and asks the right open question — *what stops a
tenth site* — but it explicitly states the nine known sites are done, and does not name
`standards.check` / `dashboard.state` / `dashboard.jobs` / `_proc_lines` among them. Order
`74f1bc47da2a` names these call sites but only for the rows they redden, never for what they write.
The intersection is unowned, which is why I have filed it.

**Remedy is a judgement, not an edit** — which is why the order is SESSION and not RUN. Blanket
`_no_ledger_vm()` around a live `standards.check()` would suppress the echo of a *genuine* library
fault occurring during that call, and this file's own doctrine (`_third_party_vm`, :353-405) says the
instrument for "somebody else's resource was down" is a *named abstention*, not a blanket
suppression. The two purely mechanical sites (:4643 and :4725) can be wrapped without a ruling.

---

## QUESTIONS (both readings given; neither filed as a finding)

**Q1 — `measure_bit_value` is checked against its own body, twice.**
`rigor.measure_bit_value(band)` is `T.band_resolution(band) / 10.0` (rigor.py:150-151). §8:890-891
and §20f:5035-5036 both assert `R.measure_bit_value("M5") == T.band_resolution("M5") / 10.0` — the
row reproduces the function body. *Reading A:* it is a rebuilt expectation of the class this file
refuses at :7026-7027 ("a check that reimplements the line it is guarding cannot fail when that
line is corrupted"), and any corruption of `band_resolution` moves both sides together and is
invisible here. *Reading B:* it is deliberate and adequate — the `10.0` is a literal on the right,
so a change to the divisor *is* caught, and `band_resolution` is independently pinned at
§12:1187-1197 (non-zero for every band, and distinct from `rung_description_length`). §8's own note
records that an earlier form compared `measure_bit_value("M7")` to itself and was repaired to this.
I lean to B and did not file it. Worth a sentence in the section note saying which corruption the
row cannot see.

**Q2 — `PR.build_all(limit=400)` at §14:1419.**
An explicit cap in the battery, labelled "A SAMPLE, and labelled as one", with the argument that
decode breaks on the first row rather than the 40,001st. *Reading A:* Hard Rule 0 says no caps,
ever, and a capped roster in the file that enforces Hard Rule 0 elsewhere (§19g, §19i, §19o, §20g)
is the rule broken at its own gate. *Reading B:* the rule is about *the library's* rosters and
outputs, not about a test fixture's size, the cap is announced rather than silent, and the round-trip
property genuinely is uniform across rows. Deliberate and declared, so a question rather than a
finding.

---

## SMALLER NOTES (recorded, not filed)

* **Probe files written into live `state/`.** §19h-bis (:2489-2491) writes
  `state/_VM_UNRECOGNISED_TEST.json` and §20g (:5232-5251) writes `state/_VM_ATOMIC_PROBE.json`.
  Both are removed in a `finally` and both record the cleanup failure via `silence.note`, so the
  discipline is followed. A kill in the window (and §20a documents `kill_stalled_job` as routine)
  leaves a synthetic file where the dashboard and `standards` look for real ones. Both sites say so
  in their own comments; nothing to add.
* **Unclosed file handles.** `json.dump(..., open(_gp, "w"))` at :2645-2646 and :2684-2685 (§19k)
  relies on CPython refcounting to close. Harmless here, and §20g's own row at :5276-5278 forbids
  this shape in `weave.py`. Cosmetic asymmetry only.
* **Timing-dependent rows.** §19t (:3297-3328) starts `GATE_LOCAL_N * 4` threads with
  `join(timeout=20)`; §19ad (:3694-3764) uses `time.sleep(0.35)` against a 0.05 s beat and
  `join(timeout=30)`. Both assert on stranded-thread counts. Correct today; on a machine at 99% GPU
  and mid-mutation-pass these are the rows most likely to flap next. Not filed — they are bounded
  and generously timed.
* **`§20a` spawns a real child and SIGTERMs it** (:4180-4191) on every run. Guarded with
  `CREATE_NO_WINDOW`, wrapped so a misbehaving kill reddens rather than wedges. Correct.
* **Cross-type module-level rebinds.** The file has repaired eight of these by hand (orders
  `7916f7063ee0`, `a05eb35ebe4f`, `44539ab9be89`, and the §19v pair) and §20z has a row for the
  class. I found no new one: `_sc`/`_as` at :7069-7072 rebind §19e's `_sc` but to the same *type*
  (a score dict), and nothing reads §19e's binding afterwards.
* **Comments citing line numbers.** I spot-checked the paragraphs that carry them. §19h's
  `_here19h`/`_here19` note (:2434-2438), §20v's `sweep.load` note (:4805-4815) and §20f's
  `verify_math.py:382-384` note (rigor.py:145) have all already been converted to symbol- or
  tag-citation with the drift recorded. `:2358-2362`, `:5076-5079` and `:7285-7293` in the §0
  doctrine paragraph (:277-281) now point into the wrong sections after the file grew — the
  paragraph's claim is still true, only its three line numbers have moved. Too small to file; noted
  here so the next reader does not re-derive it.
* **Two rows I checked and cleared.** `check("axis_score CLAMPS at zero...")` at :1130-1132 compares
  `axis_score` at two different inputs rather than to itself, and is anchored by :2360-2365's
  refusal rows. `check("and does not depend on the KEY ORDER...")` at :1387-1391 passes a genuinely
  reversed dict and is not a permutation-of-a-set comparison. Neither is a Finding-1 sibling.

---

## Coverage

`sweep_plan.record('run46', ['verify_math.py'], batch=2)` — recorded. `verify_math.py` was read end
to end, every line, in seven passes over the file. No other module is claimed; `standards.py`,
`dashboard.py`, `overnight.py`, `silence.py` and `rigor.py` were opened only at the specific
functions named above, to verify findings, and are not claimed as read.
