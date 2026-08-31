# run39 comprehensive source audit — BATCH 02

**Module owned by this batch (derived, not typed):** `src/drill.py` — one module, 7,570 lines.
Obtained from `sweep_plan.batches(16)[1]["modules"]`. Read IN FULL, no sampling.

**Method.** Every finding below was verified against the current source before it was written
down, and the defeatability findings (F1–F3) were each **proved with a scratch fixture driven
through the real net function** via its `src=` parameter, in the session scratchpad — never under
`handoff/`. Every `file.py:NNN` citation in `drill.py` was checked against the current line. No
source file was edited. `drill.py --to-halt` was never run and `main()` was never invoked; only
individual pure/AST net functions were called.

**State of the live tree.** All fourteen read-only AST nets return True against the real tree and
`_counts_decided_by_substring()` returns `[]`. Nothing here is a net that is red today. Everything
here is a net that **cannot go red when it should**, a swallow, a stale reference, or a claim that
outruns its code.

**Re-read after the maintenance shift**, per the batch briefing: `denied()` (:2086–2135),
the two scratch-probe nets (:2150–2178, :2307–2335), the uncapped breached-net lists (:7536,
:7551), and the new `_the_loop_reasks_the_halt` (:2804–2848). `denied()` is now **sound** — it
tells a `_safe()` containment refusal from a genuinely absent file by asking `_safe` itself
(`local_agent.py:718–720` emits `no such file` for both events), and `_safe` returns only `None`
or a path, so `is None` is the right test. The breached-net lists are genuinely uncapped in both
the stdout line and the halt sentence. The other three carry findings, below.

---

## VERIFIED FINDINGS

### F1 — MAJOR — `_the_loop_reasks_the_halt` accepts a `while` loop that cannot be entered

`drill.py:2804–2848`. Line **2834** is `for loop in ast.walk(main):` and line **2839** is
`for handler in ast.walk(loop):`. Both are `ast.walk`, not `_live_walk`. `_live_stmts` only drops a
`While` when it meets it *as a statement in a list*; starting the walk at the `While` node itself
never evaluates its own test. So a `while False:` (or a loop inside `if False:`) satisfies the net.

**Proved.** A fixture `publish.py` whose `main()` contains a live `while True:` that calls
`sync_tree()` and `push()` and never asks the halt, followed by a dead `while False:` holding
`_ESC.assert_clear(...)` inside `try/except _ESC.SystemHalted: break`:

```
_the_loop_reasks_the_halt(src=poc)  ->  True     # HELD, over a daemon that pushes for ever
_the_loop_asks_the_gate(src=poc)    ->  False    # its sibling, same area, correctly refuses
```

This is the incident the net was written for (order 5905045ff433: `main()` asserted the halt once
at startup, an OWNER halt never reached the daemon, it kept pushing to the PUBLIC repo on its
timer), and it is the exact defeat class this file has already filed three times — orders
c54a22a4e6fc, 78f04bec15ad, 18612d60c3f2, and its own `_live_stmts` docstring at :379–392.

**Remedy.** Use `_live_walk(main)` for the loop search and `_live_walk(loop)` for the handler
search, exactly as `drill_does_not_halt_during_a_mutation_run` does at :6825 and as
`_gate_precedes_spawn` does at :683–687. The `break` search at :2846 already uses
`_live_stmt_walk(_live_stmts(...))` and needs no change.

---

### F2 — MAJOR — `_failed_revert_is_escalated` is scoped to the module, so an uncalled helper answers for `run()`

`drill.py:1868–1923`. Line **1907** is `for n in _live_walk(tree):` — the whole module tree.
`_live_walk` descends into every `def` in a file whether or not anything calls it; drill.py states
this itself at :506–513 ("`_calls(..., reachable=True)` answers 'on a path that can be entered',
which an UNCALLED HELPER still satisfies"). The ALARM branch, the `escalation.escalate` call and
the `escalation.SAFETY` rung may therefore all live in a function nothing invokes.

**Proved.** A fixture `local_agent.py` whose real `run()` sets `out["ALARM"]` and escalates
nothing, with the SAFETY escalation parked in `_a_helper_nothing_ever_calls`:

```
_failed_revert_is_escalated(src=poc)  ->  True
```

That is verbatim the outcome the net's own expectation names at :2084 — "a half-written module on
disk while the run reports success". Its two siblings in the same area are correctly scoped:
`_write_lane_checks_the_halt` (:2065–2069) and `_run_marks_a_landless_run_failed` (:1940–1945)
both take `_defn(tree, "run")` first. Only this one does not.

**Remedy.** Take `run = _defn(tree, "run")` (refuse if absent) and walk `_live_walk(run)` — or, to
also close the delegated-helper form, follow `run` and its intra-module callees the way
`mutation_never_touches_the_live_tree` builds `bodies` at :6447–6451.

---

### F3 — MAJOR — `_local_buckets_excluded_from_cloud_claims` uses the quantifier order 5ed81099fc49 already condemned

`drill.py:4256–4320`. Line **4319** is `return True` on the *first* qualifying `if`, so the net
asks "does a gated site exist", not "does every hand-out go through a gate". Order 5ed81099fc49 is
quoted in this same file at :3854–3860 against `_identity_probe_is_gated`: *"'THERE EXISTS A GATED
SITE' IS THE WRONG QUANTIFIER … adding an UNGATED `_probe_identity(h)` beside it restored the whole
fault with the net green."* That net was rewritten to the universal form (:3884–3887); this one was
not — even though its own docstring at :4280 says it is "modelled on
`resync_cannot_revert_an_exclusion` below", which is universal (:6981–6983).

**Proved.** A fixture `cascade_bridge.py` whose `_router_walk` keeps the correct
`if cand.bucket.startswith(LOCAL_PREFIX): continue` loop and adds a second, ungated loop beside it
that claims every candidate including `ollama:` ones:

```
_local_buckets_excluded_from_cloud_claims(src=poc)  ->  True
```

The failure this guards is named at :4665 — "the router handing out ollama buckets flooded a 10GB
card with its own queue". One added line restores it with the net green.

**Remedy.** State it universally, as `_identity_probe_is_gated` now does: collect every reachable
`claim` call site inside functions that reachably claim, collect the reachable gated-and-skipping
arms, and require that every hand-out is either inside a gated arm or provably downstream of one.
At minimum, require that *no* claiming function contains a reachable claim loop with no
`LOCAL_PREFIX` skip.

---

### F4 — MAJOR — `_no_runtime_clear` can lift the live halt if the guard it is testing regresses

`drill.py:2341–2371`. The net calls the **real** `escalation.clear(r)` four times with
`r = "a ruling long enough to pass the written-ruling check"` (47 characters, deliberately valid).
`escalation.clear()` validates in this order: ruling → `_by_a_person_at_the_cli()` → `status()` →
`silence.write_json(HALT_FILE, ...)`. The only thing between this drill and writing
`cleared: true` into the live `state/HALT.json` is `_by_a_person_at_the_cli()` — **the guard the
net exists to test**. If that guard regresses, the net's own four calls lift the standing halt and
the net then also returns False, raising a fresh halt over the halt it just cleared.

This is the shape drill.py has already removed from itself twice, with the reasoning written out
at length both times: `_gates_agree` (run #31, writing the live `config.yaml`, :1327–1342) and
`_step4_needs_its_plan` (renaming the owner's `STEP4_PLAN.md`, :1268–1292). The docstring here
(:2354–2361) acknowledges the risk and answers it with "CHECKED AGAINST THE SOURCE BEFORE IT WAS
RUN" — an assurance taken once at authoring time, against a function whose own docstring says
"Order of refusals is part of what is tested here", i.e. a function whose ordering is expected to
be edited.

**Remedy.** The redirect is already in this file: `_halt_fails_closed` (:1846–1863) points
`ESC.HALT_FILE` at a scratch path and restores it in a `finally`. Do the same around the four
probes — write a synthetic standing halt into a scratch `HALT.json`, point `ESC.HALT_FILE` at it,
run the four spellings, and additionally assert the scratch file is byte-identical afterwards. Then
even a broken caller check cannot reach the owner's halt, and the net gains a second property it
does not currently have: that the refusal happened *before* any write.

---

### F5 — MINOR — three probe-file cleanups are swallowed, one of them into the PUBLIC export

drill.py states its litter discipline repeatedly and enforces it for work orders — :2254–2258
("A FAILED CLEANUP IS NOT NOTHING. Was `except Exception: pass`; a resolve that did not happen
leaves a LOCAL_AGENT_BLAST_CAP order standing in the live queue on every cycle"), :1705–1710,
:2031, :3643–3645, :5326–5327. Three file removals do not follow it:

| site | file left behind on failure | where it lands |
|---|---|---|
| `blast_cap_bites` :2246–2249 | `handoff/__drill_blast_probe__.md` | `handoff` is in `publish.COPY_DIRS` (`publish.py:133`) — **it gets published** |
| `cannot_edit_shared_run_state` :2174–2178 | `state/__drill_state_probe__.json` | live shared run state |
| `cannot_write_an_unlisted_top_level_file` :2331–2335 | `__drill_unlisted_probe__.txt` | repo root |

All three are a bare `except OSError: pass`. The first is the sharpest: in the **same `finally`
block**, twenty lines lower (:2259–2265), the work-order cleanup failure IS recorded with
`silence.note("drill.py:blast-cap-cleanup")` while the file-removal failure directly above it is
discarded. A denied `os.remove` on Windows is not exotic — a reader holding the file, or the
Norton interference this machine is already known for, is enough — and the result is a
`drill blast-radius probe` marker file in a public repository with nothing anywhere recording why.

**Remedy.** Replace each `except OSError: pass` with `silence.note("drill.py:<site>-probe-cleanup")`,
matching the four sites in this file that already do it.

---

### F6 — MINOR — ten of thirteen `file.py:NNN` cross-references are stale

Each checked against the current file today. Two are correct and are listed for completeness.

| drill.py | cites | claims | actually at that line | correct location |
|---|---|---|---|---|
| :2275 | `local_agent.py:157-159` | `blast_reset` clears both halves | a comment ("Past it, the run aborts…") | **182–184** |
| :3526 | `withdraw_chapters.py:50` | the "A COPY BEFORE THE IRREVERSIBLE STEP" paragraph | `p = p.replace("\\", os.sep)…` | **191–194** |
| :4274 | `cascade_bridge.py:1118-1120` | the router's actual local-bucket skip | — | **1310** |
| :4275 | `cascade_bridge.py:282` | the `cloud_buckets` de-duplication `if` | `def _pace(bucket):` | **317** (`cloud_buckets` begins 303) |
| :4462 | `feats.py:148` | `min(BACKOFF_MAX, _BACKOFF.get(...) * BACKOFF_GROWTH)` | `time.sleep(wait)` | **159** |
| :4693 | `cascade_bridge.py:1192` | the `permanent_refusal` branch that benches a bucket | a metrics-append comment | `permanent_refusal` at **740** |
| :4891 | `feats.py:918-923` | a comment block naming cachekey | nothing of the kind | cachekey at 45, 359, 1370–1388, 1537 |
| :4891 | `pipeline.py:822` | names cachekey in a comment | "NO DRIFT IS NOT NO CHANGE…" | **988** |
| :5055 | `pipeline.py:2122` | "is enforced in code like scale_note…" | blank line | **2621** |
| :7239 | `corpus_db.py:488-539` | names the denied atomic replace as EXPECTED | the evidence-caveat block | `datasette_metadata` **594**, the note **602–619** |
| :7456 | `dashboard.py:529` | "puts it on the page" | `out = []` | **607** (doc at 547) |
| :7456 | `workorders.py:564` | "GRADES THE BATTERY … closes a DRILL_BREACH order" | an unrelated docstring line | **1000–1012** |
| :57, :5090 | `liveness.py:10` | names `coverage._p()` | ✅ exact match | correct |
| :4889 | `coverage.py:53` | "verifies via `cachekey.owns()` before believing a file" | ✅ exact match | correct |

None of these changes any net's behaviour. They matter because this file's arguments are its
evidence: a reader sent to `feats.py:148` to check the backoff clamp finds `time.sleep(wait)` and
has no way to tell a moved line from a deleted guard, which is the distinction the whole file is
about.

---

### F7 — MINOR — `_junction_out_of_the_writable_surface` says it skips and actually halts the library

`drill.py:1999–2034`. The docstring at :2011–2013 says it *"Skips rather than fails if the junction
cannot be created (no mklink, a filesystem that does not support them)."* The code at :2022–2023 is
`return False`, which `net()` records as `held=False`, which `main()` (:7549) escalates to
**OWNER** — a full halt. Worse, off Windows `subprocess.run(["cmd", "/c", "mklink", …])` raises
`FileNotFoundError`, which `net()` (:153) also records as a breach; the file demonstrably knows
about non-Windows elsewhere (`if os.name == "nt"` at :3732).

The file already rules on this exact class in the opposite direction, at :7243–7247
(`datasette_config_is_generated_not_copied`): *"an ordinary file lock would have halted the library
… A path that could not be written is a measurement that did not happen, and a measurement that did
not happen must not be graded either way"* — and that net notes it and returns True.

**Remedy.** Pick one rule and apply it to both. If "cannot stage the attack" is not a breach, note
it (`silence.note("drill.py:junction-probe-unstageable")`) and return True, as the datasette net
does. If it is a breach, delete the word "Skips" from the docstring and say that an environment
without junctions halts the library. Either is defensible; the two nets currently disagree.

---

### F8 — MINOR — `drill_no_caps`' two nets do not drive the branch their names claim

`drill.py:1480–1502`. Both fixtures use `{"source": "T", …}`. `pipeline._mined_feats` looks the
source up in `data/WIKI_HOSTS.json` and returns `{}` when there is no host — verified, `"T"` is not
in the map. So `with_feats` is empty in both nets and `pipeline.synthesis_blocks` takes the
`or [rest[i:i+14] …]` arm in both.

* `nomination_drops_nothing` (:1480, named "no entry is dropped from nomination, **feats or not**")
  only ever exercises the *no-feats* half of "or not".
* `feat_bearing_path_unchanged` (:1497, named "the feat-bearing path is untouched by the fix") does
  not touch the feat-bearing path at all. It is `nomination_drops_nothing` again with 30 entries
  instead of 97 and a `sum(len(b))` instead of a name comparison.

Two consequences. The net's printed name promises more than its code tests — the fault
`coverage_totals_never_exceed_their_entry_count` was renamed for at :5004–5008 ("a net whose name
and docstring promised a completeness check while its code did an overflow check"). And the mixed
case is untested by anything in this file: `blocks = ([with_feats chunks] or [rest chunks])`
short-circuits, so **the moment one entry in a source has mined feats, every feat-less entry is
dropped from nomination entirely** — which may well be the intended selection rule, but no net in
`drill_no_caps` states it, tests it, or distinguishes it from a cap.

**Remedy.** Give one net a fixture with a real host in a redirected `feats.HOSTS` (or a stand-in
`_mined_feats`) so that some entries carry feats and some do not, and assert whichever rule the
owner intends for the mixed case. Rename `feat_bearing_path_unchanged` if it is going to keep
driving the feat-less path.

---

### F9 — MINOR — the coverage overflow check sums four of the five state columns its own docstring names

`drill.py:5001–5035`. The docstring at :5015–5016 says: *"The real state columns are `cited`,
`read`, `no_page`, `no_host` and `not_attempted`, and re-measured against those on 2026-08-26 they
sum to the entry count EXACTLY for all 210 rows."* Line **5032** sums four of them:

```python
parts = sum(r.get(k, 0) for k in ("cited", "read", "no_page", "no_host"))
```

Verified against the live `data/COVERAGE.json`: 210 rows, `not_attempted` present as a real column
in every one of them, and all five sum to `entries` exactly in all 210 (0 over, 0 under). Because
of that exact identity, the four-column sum equals `entries - not_attempted` and can only exceed
`entries` if `not_attempted` goes negative. An entry double-counted **into** `not_attempted` — the
M23 shape this net is named for, in one of the five buckets — is invisible to it.

**Remedy.** Sum all five columns the docstring names. (Do not add the equality check the earlier
docstring wrongly claimed; the correction at :5010–5020 is right that the overflow direction is the
one worth keeping, and it should simply cover every column.)

---

### F10 — MINOR — `paid_access_stays_switched_off` reaches outside the repo, and its swallow makes it unfailable

`drill.py:5243–5250`.

1. **The path is a raw string with doubled backslashes.** The parsed constant contains eight
   backslashes (verified via AST). Windows tolerates the doubled separators and the file opens on
   this machine — `allow_paid` reads `False` — so this is latent, not live.
2. **It reads a file in a different project** (`C:\Users\imarl\cascade\config.json`), by absolute
   path, from a safety battery whose module header says every attack is built in memory or in a
   scratch directory.
3. **`except Exception: return True`** conflates four different conditions under one verdict:
   "not this machine" (intended), the config is corrupt JSON, the read is denied, and the schema
   changed. Every one of them makes the net unfailable, silently, in the direction the ruling
   forbids.
4. **And the other direction halts the library.** If `allow_paid` is ever absent rather than
   `False`, `cfg.get("allow_paid")` is `None`, `None is False` is `False`, the net BREACHES and
   `main()` raises an OWNER halt — over a missing key in an unrelated project's config file.

**Remedy.** Separate the conditions: `FileNotFoundError` → note and return True ("not this
machine"); any other exception → note and return False, or note and return True with the reason
recorded, but not both under one arm. Treat an absent `allow_paid` key as the same refusal as
`True` rather than as a breach, or state explicitly that absence is a fault. Better still, take the
path from configuration rather than a literal.

---

### F11 — MINOR — `seam = P._SCAN_BLOCK and 2_000_000` is a no-op conjunct over a duplicated default

`drill.py:2595`, in `_the_scanner_reads_files_over_two_megabytes`. Verified:

* `publish._SCAN_BLOCK` is **262,144** (`publish.py:347`) — the *read* block size. It has nothing
  to do with the segment seam.
* The seam is `scan_for_secrets`'s `max_bytes` default of **2,000,000** (`publish.py:415`), passed
  through to `_scan_units(path, line_cap)` (`publish.py:350`, cut at :380–384).
* So `P._SCAN_BLOCK and 2_000_000` evaluates to `2_000_000` always. The conjunct changes the answer
  only if `_SCAN_BLOCK` becomes falsy, in which case `seam` is `0`/`None` and `long_line[:seam - 10]`
  raises — recorded by `net()` as a breach, i.e. an OWNER halt over a constant rename in another
  module. That is the "pinned to a name" hazard order 7cc460706efe filed against two nets here.

The fixture **does** straddle correctly today — verified: 2 segments of 2,000,000 and 404,106, the
AWS key absent from segment 0 and whole in segment 1, and absent from every segment of a naive
non-overlapping split of the same body, so `_SCAN_OVERLAP` is genuinely what saves it and the arm
has teeth. The defect is the coupling: the literal duplicates another function's default, and if
that default moved to, say, 262,144 the key at offset 1,999,990 would land well inside a segment,
the arm would silently stop testing a seam, and the net would still report HELD.

**Remedy.** Derive the seam from the value actually used —
`seam = P.scan_for_secrets.__defaults__[0]`, or better, call `only(...)` with an explicit
`max_bytes` and build the fixture around that same number — and drop the `_SCAN_BLOCK and`.

---

### F12 — INFO — 19 of 269 net sites carry an empty expectation, and `main()` suppresses the line for exactly those

Static count: **269** `net()` call sites (runtime count is higher; two sites are inside `for`
loops). Nineteen pass `""` as the fourth argument, and `main()` at :7441 reads
`if not r["held"] and r["expected"]:` — so a breach in any of them prints the net name and nothing
else. The nineteen, by line: 1027, 1058, 1065, 1068, 1196, 1206, 1528, 1547, 1549, 1640, 1644,
1658, 1742, 2164, 2327, 2526, 2958, 2966, 2980.

Recoverable — the halt sentence at :7550 names every breached net — but it sits oddly in a file
whose `_a_refusal_names_the_block_it_refused` (:1108–1137) exists precisely because
`ProseRefused` must carry "the reason a person needs, never a bare False". Several of the nineteen
are the *second half* of a pair whose sibling carries the prose, which is a defensible reason to
leave them; the ones that stand alone (2526, 2958, 2966) are not.

---

### F13 — INFO — the `LIVENESS_CEILING` comment's measurement is one out

`drill.py:48–52` states "measured 2026-08-29 … 35 dead module-level functions and methods, 1 dead
class, 10 dead MODULES, 0 syntactic tautologies, 0 phantom guards, 0 unparsed files. Total 46", and
:74 states "46 measured, 52 here, so six". Re-measured today:

```
{'dead': 36, 'dead_class': 1, 'dead_module': 10, 'tautology': 0, 'phantom': 0, 'unparsed': 0}
TOTAL 47   CEILING 52   headroom 5
```

The block itself anticipates exactly this ("the count MOVES during ordinary work … watched go
34 → 35 → 37 across this single shift"), so this is not drift of the kind the ceiling forbids. It
is still a paragraph asserting a measurement that no longer holds, in the file whose
`drill_inspector` docstring lists "a comment asserting a measurement that was backwards" among the
four failures it was built for. The founding example is intact: `coverage._p()` is present in
`scan()["dead"]`.

---

### F14 — INFO — `CLAUDE.md` says the drill "attacks all 57 nets"

`CLAUDE.md`, Hard Rule -1, third property (PROVEN). The static count of `net()` call sites in
`drill.py` is **269**. This is owner doctrine rather than a drill defect, and the number is the one
thing in that paragraph a reader can check, so it is worth correcting or replacing with "every
net".

---

## QUESTIONS — two defensible readings, filed here rather than as orders

**Q1. `_gate_precedes_spawn` still uses a line number.** `drill.py:696` is
`if all(id(s) not in inside and s.lineno > g.lineno for s in spawns)`. The docstring of
`the_keeper_asks_before_restarting` (:5402–5406) criticises exactly this — *"'BEFORE' WAS A LINE
NUMBER, WHICH IS NOT A PATH"* — and the inline keeper version at :5435 does the same thing. One
reading: the lineno test is now only the third of three conjuncts (bound answer, skipping arm,
outside-and-after), the first two carry the property, and textual order is a reasonable proxy for
the remaining claim. The other: it is a residue that can still mis-order a correct refactor (a
spawn hoisted above the gate but reached only after it), and a False here is a library halt. I do
not think either reading is obviously right, so no order.

**Q2. `mutation_never_touches_the_live_tree` clause 4 is unscoped.** `drill.py:6483` walks
`_live_walk(tree)` at module level for the `if …["live_file_untouched"]` branch, so that branch and
its OWNER escalation could sit in a helper nothing calls. Clauses 1–3 (:6444–6480) are correctly
scoped to `run` and its intra-module delegates and do the load-bearing work, so exploiting clause 4
alone does not restore a live-tree write — it only removes the alarm. Whether "the alarm can be
orphaned while the write gate holds" is worth an order is a judgement about how much clause 4 is
carrying.

**Q3. A redundant conjunct at :1197–1199.** `PG.cited_names_for(...) is not None and
isinstance(PG.cited_names_for(...), set)` — the first test is subsumed by the second, and the
function (which reads the live feats cache) is called twice. Harmless: the property is really
covered by `_cited_names_for_can_credit_a_name` (:1212–1264), and the weak net is kept
deliberately as its shallow twin. Noted, not filed.

---

## OBSERVATIONS (outside this batch's module, recorded for whoever owns them)

* **`publish.py:383`** — `carry = seg[-_SCAN_OVERLAP:]`. If `_SCAN_OVERLAP` were ever set to `0`,
  `seg[-0:]` is `seg[0:]`, i.e. the **whole segment** carried forward, not none. Latent (nobody
  sets it to zero) and it fails in the safe direction, but it is a slice whose zero case does the
  opposite of what it reads as. Found while confirming F11.
* **`handoff/` holds roughly twenty scratch `.py` scripts** (`canon_net_redcheck.py`,
  `dump_orders.py`, `ctx_probe.py`, `file_batch2_extras.py`, …) and `handoff` is in
  `publish.COPY_DIRS` (`publish.py:133`), so all of them are published. This is the condition the
  batch briefing names as having raised a `SECRET_IN_EXPORT` halt once. Pre-existing and not
  `drill.py`'s to fix, but it is the same surface F5 leaks a probe file onto.

---

## WHAT WAS CHECKED AND FOUND SOUND

Recorded so the next sweep does not re-derive it.

* **Hard Rule 0 in drill.py's own output.** No cap anywhere on a reported list: `main()`'s report
  loop (:7432–7442) prints every row, the mutation-run line (:7536) and the halt sentence (:7550)
  both `"; ".join` every breached net, and `evidence={"breached": […]}` is the full list. Every
  `[:N]` in the file is fixture construction or an expected-value literal.
* **`denied()`** (:2086–2135) after today's change: sound. `t_propose_patch` emits `no such file`
  for both a `_safe()` refusal and a genuinely absent file (`local_agent.py:718–720`); asking
  `_safe` directly is the right discriminator, and `_safe` returns only `None` or a path
  (`local_agent.py:374–470`), so `is None` cannot be fooled by a falsy string.
* **`_no_programmatic_clear`'s exemptions** (:2419) are matched on the *relative path* produced by
  `_src_py_files` (`"escalation.py"`, `"deprecated/escalation.py"`), so the docstring's claim at
  :2410–2414 that a `deprecated/escalation.py` cannot exempt itself by basename holds.
* **`blast_cap_bites`** (:2184–2265) genuinely drives the charge: `_blast_ok` (`local_agent.py:166`)
  increments before comparing, so `MAX_* = 0` makes the first charge over budget and
  `_BLAST["patches"] == 1` is the correct assertion.
* **The allowlist claim at :2162** — "`src/`, `prompts/`, `handoff/` and four root documents and
  nothing else" — matches `WRITABLE_PREFIXES` and `WRITABLE_FILES` (`local_agent.py:139–144`).
* **All fourteen read-only AST nets pass against the live tree**, and `_counts_decided_by_substring()`
  returns `[]`.
* **`main()`'s area roster** (:7394–7402) contains all thirty-four `drill_*` functions defined in
  the file; none is orphaned, and the per-area `try/except` at :7422–7429 correctly records an area
  that dies rather than losing the run.
* **No dead helpers.** Every private helper in the file has at least one live caller;
  `_SRC_OVERRIDE` (:242) is written by nothing but is read by `_srcdir` and is a documented
  out-of-band hook — it is what made the fixtures for F1–F3 possible.

---

*Batch 02 of run39. `src/drill.py`, 7,570 lines, read in full. Fourteen findings filed as work
orders, three questions and two out-of-scope observations left here.*
