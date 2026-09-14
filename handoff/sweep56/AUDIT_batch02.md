# sweep56 — AUDIT batch 02

**Module in scope:** `src/verify_math.py` (12,674 lines) — read in full, top to bottom, in eight
successive chunks. No sampling, no "interesting parts".

**Method.** Every finding below was verified against the actual source before being written down.
Where a claim in the file is a claim about a scan's output (`_prose_backed20z`, the disarm scan,
the discarded-`tol=` scan, the self-citation scan, the section-tag uniqueness scan, the §20e
console-window scan, the §20p interlock scan), the scan was **reimplemented offline and run**
against the live tree so the row's current verdict is known rather than assumed. Every cited
line number in another module was opened and read.

**What was NOT done.** The battery itself was not executed. It writes probe files into the live
`state/` directory (`_VM_ATOMIC_PROBE.json` at :6013, `_VM_UNRECOGNISED_TEST.json` at :2759),
spawns a real child process (§20a, :4695), drives `standards.check()` and `dashboard.state()`
against the live machine, and lands records through `pipeline.write_record`. The work order says
audit only and do not run anything that writes to the library.

---

## Summary

**4 DEFECT · 9 QUESTION.** Nothing found that makes a check unable to fail, nothing fail-open,
no dead code, no bare `except: pass`. Three of the four defects are the same shape: a claim in
this file about coverage or about another file's line numbers that measurement now falsifies.

Offline reproductions, all currently **clean**, recorded so the next run does not re-take them:

| scan | result today |
| --- | --- |
| `check(label, got, want)` with `dump(got) == dump(want)` | 0 of 1,157 rows |
| `_disarmed_rows20i` (constant-truthy / always-true disjunct `got`) | `[]` |
| `_discarded_tol20z` | `[]`, over **80** rows carrying `tol=` (floor 60) |
| `_self_cites20ad` | `[]` |
| §20y section-tag uniqueness | `[]`; **69** tags, 47 banner / 24 print / 4 dashed (floor 55) |
| §20e console-window scan | 0 unguarded, 0 `os.system`, 0 unparsed, 44 sites, 44 guarded, 14 importers by both readings |
| §20p interlock scan over `_INTERLOCKED` | all 10 modules at expected guard count, 0 non-raising handlers, all call `assert_clear` |
| `_prose_backed20z` | exactly the two pinned prose-only rows; unresolved exactly the pinned four; declined exactly the pinned three; 47 examined |
| uncalled functions / unread module-level names | none |

---

## DEFECTS

### D1 — the §18c temp-directory exemption enumeration is incomplete, and it claims not to be

**Lines 2088–2092** (comment), against **line 5165** and **line 9249**.

```
# WHAT IS ACTUALLY EXEMPT, re-enumerated by reading every temp-making site in this file rather
# than by trusting the old list: §19ab's token-flow root and §20p's halt-probe root, each
# rmtree'd from a `finally`; the two `TemporaryDirectory()` blocks; and batch6's `_tmp_guard`,
# which is a single FILE removed in a `finally`. That is five, not three -- §20p's was doing
# the right thing and was not credited. Everything else that makes a scratch directory goes
# through `_mkdtemp_vm` and is swept at exit.
```

An AST/grep enumeration of every temp-making site in the file finds **seven** that bypass
`_mkdtemp_vm`, not five. The two omitted:

* **line 5165** — `_scratch19ft = _tf19ft.mkdtemp(prefix="vm_feats_gate_")`, the §19
  `pages_read`-gating probe. Removed at :5176 inside the `finally` at :5174. Mentioned nowhere in
  the enumeration.
* **line 9249** — `scratch_dir = _tempfile_b2.mkdtemp()` inside `_codewatch_concurrency_b2`.
  Removed at :9286 in a `finally`. The paragraph *above* the enumeration (:2079–2084) discusses
  this site's `finally` repair by name, and then the enumeration that follows does not list it.

**Why it matters.** Nothing leaks today — both are cleaned in a `finally`. The defect is the
sentence "Everything else that makes a scratch directory goes through `_mkdtemp_vm` and is swept
at exit", which is false, inside a paragraph whose whole authority is that it was
"re-enumerated by reading every temp-making site in this file rather than by trusting the old
list". This is the file's own recurring class: a completeness claim that a later reader trusts
*instead of* re-counting. Order af447d21d634 was filed because the previous version of this list
was wrong in exactly this way (336 + 148 + 9 orphans); order 41e4489aa545 corrected it once and
over-claimed while doing so; this is the third iteration and it is short by two.

**Confidence: DEFECT** (measured; the two sites and their cleanup were read).

---

### D2 — §20p's `_INTERLOCKED` is a hand-kept roster, and three halt-consulting modules sit outside every one of its rows

**Lines 7222–7223:**

```python
_INTERLOCKED = ("dashboard.py", "feats.py", "foreman.py", "hostcheck.py", "overnight.py",
                "overwatch.py", "pipeline.py", "publish.py", "read.py", "withdraw_chapters.py")
```

An AST scan of all 118 modules under `src/` for a call to `escalation.assert_clear` returns
fifteen. Two are expected (`drill.py` attacks the guard; `verify_math.py`'s own synthetic-halt
probe at :7601). The other **three are real interlocked jobs and are not on the roster**:

* `ingest_doc.py` — fail-closed guard at **:70–75**, `_ESC.assert_clear("ingest_doc.py %s" % what)`
  at **:76**.
* `threads.py` — fail-closed guard at **:798–802**, `_ESC.assert_clear(...)` at **:803**.
* `local_agent.py` — `import escalation as _ESC` / `_ESC.assert_clear(who="local_agent.run")`
  at **:1433**, deliberately ungated (its own comment: "Raised, not swallowed").

`ingest_doc.py` and `threads.py` carry *precisely the shape §20p exists to protect* — a Try whose
body is only the escalation import, with a `raise SystemExit("REFUSING TO START: ...")` handler.
All three of §20p's rows (`_noguard20p`, `_openguard20p`, `_noclear20p`, lines 7317–7330) iterate
`_INTERLOCKED`, so replacing either module's `raise` with `pass` — the original 2026-08-25
incident, verbatim — would leave the entire battery green.

This is the defect §20x names in this same file at **lines 7144–7149**:

```
# THE ROSTER IS DERIVED, NOT LISTED. The first version of this check named four modules ...
# A hardcoded roster in a check is the identical defect m49 found in `allsweep` two days ago:
# it cannot report what it was never told to look at. So this scans EVERY module in src/ instead.
```

The roster's own history is the evidence: `withdraw_chapters.py` was added 2026-08-31 (order
bd107a18b13e) and `hostcheck.py` 2026-09-06 (order 77950336e3aa), each *after an audit found it
missing*. That is discovery by audit, which is what §20x's cachekey scan was rewritten to stop.

**Confidence: DEFECT.** (The remedy is a derived roster — every module in `src/` that calls
`assert_clear`, minus a named exemption for `drill.py` and this file — not a fourth hand-added
name. `local_agent.py`'s ungated import would need a declared exemption, since it is stronger
than the guarded shape rather than weaker.)

---

### D3 — §20z's ledger rows are evaluated ~630 lines before the battery ends, under a label that says "anywhere"

**Line 12045:**

```python
check("no probe anywhere in this battery writes into the live failure ledger", _escaped20z, [],
```

and its stronger sibling at **line 12035**:

```python
check("nothing this battery did reached the ledger by a route the in-process spy cannot see",
      _wrote_to_the_ledger_vm(_FLUSHED_VM, _H_vm.LEDGER), [],
```

Both are computed at lines 12036/12044 and the file runs to **12674**. Everything after them is
outside the guarantee: §20z's own controls, the label-uniqueness rows, the `tol=` scan, the
prose-backed scan, and — the one that can actually record — **§20ae at line 12596**:

```python
real = getattr(_imp20ae.import_module(modname), t.attr)
```

`_standins20ae` imports, by name, every module aliased anywhere in `drill.py`. Any of those not
already resident is executed at import time here, and this tree's modules do call
`silence.note()` from module scope on a bad read. Such a record lands in `_LEDGER_ESCAPES_VM` and
in `health.LEDGER` *after* both witnesses have already reported, and is then flushed by
`silence.note`'s atexit hook into the never-cleared `state/failures.json`.

The file states this class itself, at **line 4196**: "A check whose scope is smaller than its
name is how an unfixed defect reads as fixed."

Note also that the §20z abstention row (:11993) and the ledger-movement banner (:12007) read the
same pre-end snapshot, so an abstention taken by §20ae would not be printed either.

**Confidence: DEFECT** (structural, verifiable from line ordering plus the `import_module` call;
whether an escape fires on any given run depends on which modules are already resident).

---

### D4 — six stale cross-file line citations, and §20ad's stated reason for tolerating them is falsified

**Lines 11841–11847** (§20ad):

```
# WHY THE SELF-CITATIONS ROT AND THE CROSS-MODULE ONES DO NOT. Spot-checked the same day:
# `standards.py:751`, `standards.py:67`, `standards.py:1901`, `anchors.py:427`, `sevenfold.py:86`
# and `assay.py:147-189` were all still accurate. They hold because they point at OTHER files,
# which this file's own growth does not move.
```

Three of the six named in that sentence are wrong today, and three more elsewhere in the file.
Every target below was opened and read:

| citation | cited at | line 751/1901/… actually holds | real target |
| --- | --- | --- | --- |
| `standards.py:751` | 4525, 4547, 4549, 11842, 11944 | `def check(state=None):` | `if calls < MIN_CALLS_TO_JUDGE_RATE:` is **standards.py:868** |
| `standards.py:1901` | 4315 | `"no source outgrowing its code",` | the `ollama_token_flow()` call inside `check()` is **standards.py:2082** |
| `anchors.py:427` | 8042 | a `%r is named by this check and absent from ANCHORS…` message string | `A.INSTRUMENT_WINDOWS[b]` indexing is **anchors.py:546** and **:551** |
| `overnight.py:741` | 5240 | `p.wait(timeout=timeout_h * 3600)` | `def ledger_report` is **:939**; the `did[:5]` prose is **:889 / :894 / :926** |
| `silence.py:511, 518` | 4959 | comments in an unrelated function | `def replace_retry` **:722**, `def write_json` **:773** |
| `corpus_db.py:532, 562, 575` | 10388 | three ordinary code lines | the `LIMIT` comments are **:737, :767, :780** |
| `scope.py` "lines 72, 109, 233" | ~9350 | 72 correct; 109 is `def scope_for(...)`; 233 is an unrelated `--force` comment | the other two mentions are **:82** and **:409** |

Accurate and left alone: `standards.py:67`, `sevenfold.py:86`, `sevenfold.py:214`,
`cascade_bridge.py:18`, `assay.py:147-189`, `withdraw_chapters.py:176`, `prose_gate.py:34`,
`local_agent.py:421-424` (off by one; the `-c` argv begins at :422).

**Why it matters.** §20ad exists to stop rotted pointers, and the rule it enforces
(`_self_cites20ad`, currently clean) is scoped to *self*-citations only, on the strength of the
premise quoted above. The premise is false: `standards.py` has grown ~117 lines past :751 and
~181 past :1901, `anchors.py` ~119 past :427, and `corpus_db.py` ~200 past :575. The
worst of these, `standards.py:751`, is repeated five times, including inside the paragraph that
vouches for it.

**Confidence: DEFECT.** The remedy §20ad already argues for — cite by symbol, never by number —
applies unchanged; do not re-pin the numbers.

---

## QUESTIONS

### Q1 — the battery makes real DNS, daemon and process-table calls, and only the ledger echo is wrapped

`standards.check()` is driven at least a dozen times per run: `_pool19ai` (§19ai, :4354) is called
from eight rows, §20k calls it at :6627, :6651 and :6668, §b3 at :9622 and :9631. An AST scan of
`standards.check()`'s body finds `fandom_ipv4_reachable` (real `getaddrinfo` + TCP connect),
`ollama_runner_up` and `urlopen` (localhost:11434), `shutil.disk_usage`, and `overnight.running`
(a PowerShell/WMI spawn). §20k (:6622) and §b3 (:9606) additionally call `dashboard.state()`,
which reads every operational artefact on the machine and calls `standards.check()` again inside
itself.

`_third_party_vm(_LIVE_STATE_VM)` suppresses the **ledger echo** of those reads; it does not make
the reads hermetic. The file argues this at length (:395–:428, owner ruling 2026-09-08, "Live
machine state inside the battery", option (a)) and `_TOKENFLOW` is pinned so the 300-second
generation cannot fire — proved by the transport witness at :4456. Recorded here as a standing
fact about the battery's dependencies, **not as a fix request**: the owner ruled on it.

### Q2 — §20l is the one row whose *verdict*, not just its echo, is a function of another program's database

**Lines 6692–6701.** `_stuck20l` reads the live `state/UNRECOGNISED.json` via
`cascade_bridge.unrecognised_open()` and then calls `cascade_bridge.provider_error(bucket,
max_age_s=24*3600)` twice per row — a read of Cascade's own `state/cascade_scratch.db`. The
`_third_party_vm("cascade scratch DB")` wrapper keeps the echo out of §20z, but the row itself
reddens whenever another program's database genuinely holds a stuck row.

Order c121db910a17's finding is that a red baseline here cancels a whole `mutate.py` pass. Is the
verdict-level dependency deliberate — i.e. is a stuck row in Cascade's DB a fault of *this*
library that should fail the battery — or was only the echo considered when the wrapper was added?

### Q3 — one bare swallow with neither a noted site nor a declared exemption

**Lines 1535–1539** (§4.2, the thread-integrity floor):

```python
try:
    with open(_floor42, encoding="utf-8") as _f42:
        _fl42 = json.load(_f42).get("asymmetric_suspect_max")
except Exception:
    _fl42 = None
```

It is **fail-closed** — the row at :1541 asserts `isinstance(_fl42, int) and _fl42 >= 0`, so a
missing, torn or key-less file reddens. But it is the only handler in the file that carries
neither of the two forms this file states as doctrine three times (`verify_math.py:
unrecognised-probe-cleanup`, `:atomic-probe-cleanup`, `:b2-instrument-cleanup`): no
`silence.note()` site, no `silence-exempt:` marker, no written justification. Every other
non-noting handler in the file is a handler where *the exception is the measurement*, and this one
is not. Should it declare the exemption, or note a site? (A `silence.note` here would reach the
§20z spy — which is exactly the trap documented at :295–:304 — so the *declared exemption* form
looks like the right one.)

### Q4 — `_prose_backed20z`'s binding map is not function-scoped

**Lines 12364–12382.** `_binds20z[_n.targets[0].id] = _named_py20z(_seg)` is keyed by bare name
across the whole module. A name bound to `open("a.py").read()` in one function and to
`open("b.py").read()` in another collapses to whichever `ast.walk` visits last, and the first
function's membership tests are then resolved against the wrong file's source.

Measured today: two names are rebound (`_t20p` at :7226 and :7304, `src_txt` at :10673 and
:10816) and **both resolve to `None` in every binding**, so nothing is currently mis-resolved —
`src_txt` lands in the pinned `_unres20z` list instead. But this is the identical enclosing-scope
confusion `_own_nodes20p` was written for (orders 6a8444cad673 and b4af486851af), in a helper
written after both repairs, and the helper is already in this file. Deliberate, or an oversight?

### Q5 — two undisclosed truncations inside FAILED-row diagnostics

* **Line 11920** — `" ".join(_s20ad.split())[:90]`, the context string for a self-citation the
  scan caught.
* **Line 10632** — `note="sample=%s" % (res.get("sample") or [])[:3]`.

Order 7a379f99fe80 removed `str(_e36)[:160]` (:11322) and a 70-character label clip (:11356) from
exactly this position, with the argument that "a silent cut on the one sentence explaining a
FAILED row is the same act as a cut on a page list", and the `[9d4d0c4e6c6a]` row at :9465
asserts that `standards.py` no longer character-truncates its pending join. Are these two
survivors, or is a diagnostic *context* line held to a different standard from a diagnostic
*identifier*? (The 90-char cut is not marked with an ellipsis, so a reader cannot tell it happened.)

### Q6 — the onomast doctrine rows can each be satisfied by the wrong world's number

**Lines 10506–10516.** Each row asks `str(n) in doc or _b5_spelled(n) in doc` over the *whole*
`onomast` module docstring. Measured today, that docstring contains "twenty-six", "fifteen" and
"fourteen" (verified: `Resolution finds twenty-six distinct worlds named Earth, fifteen named
Moon, fourteen named Mars.`), and `_NUM_WORDS_b5` at :10519 maps exactly `{14, 15, 26, 12}`. So:

* if Earth's measured count fell to 15 and Moon's rose to 26, **all three rows still pass** —
  each number is present somewhere in the docstring, just against the wrong world;
* any count outside the four-entry hand map falls back to the digit string, and the docstring
  spells its numbers in words, so a legitimate corpus change reddens the row rather than
  reporting the drift it was written to report;
* `12: "twelve"` in the map is currently unreachable.

The row's stated intent ("Re-measures live rather than hardcoding the expected numbers") is right;
the substring test does not scope the number to its world. Worth a sentence-shaped assertion
instead?

### Q7 — five hardcoded population floors survived the two arguments that retired their siblings

`len(_tags20y) >= 55` (:11824), `_toln20z >= 60` (:12247), `_seen20zn >= 30` (:12456),
`len(_seen20ae) >= 50` (:12640), `_used20q >= 12` (:7659).

§20j (order ba7b55d6465f) retired `len(emitted) >= 40` and §20e (order 1e83e387cfc1) retired
`_guarded20e >= 20`, both with the same reasoning: a floor with headroom "just lowers a number
nobody reconciles", and "keeping the weak one costs a reader the belief that the floor meant
something". Measured today the surviving floors have 14, 20 and 17 of headroom respectively
(69 tags / 80 `tol=` rows / 47 prose-examined reads). Are these five a different instrument —
anti-vacuity population counts with no reconcilable declared set — or simply not yet reached?

### Q8 — the one surviving cap on a data listing, disclosed

**Line 1584** — `_rows = PR.build_all(limit=400)`, under the comment "A SAMPLE, and labelled as
one: 400 profiles is plenty to prove round-tripping and far cheaper than the full set. If decode
ever breaks it breaks on the first row, not the 40,001st."

Disclosed, argued, and about a *round-trip property* rather than a roster — so not a Hard Rule 0
truncation on its face. Recording it because it is the only remaining cap on a data listing
inside the file that refuses `--show` defaults (:9417), `[:3]` diagnostics (:9455) and `[:120]`
joins (:9465) everywhere else, and because the argument ("it breaks on the first row") is an
argument about *this* defect class and not about a new one.

### Q9 — `_at_vm` guards two subscripts; the same shape is unguarded elsewhere

`_at_vm` (:158) was added under order e0d71f507510 so that a control row subscripting a detector's
own output reddens rather than raising, "because a raise costs the whole run its RESULT line". It
is used at exactly two sites, :6349 and :6357. The same shape survives unguarded:

* **:3276–3277** — `_spans[0].startswith("1-")` and `_spans[-1].endswith("of 569")`. If
  `pack_feats` regressed to returning no blocks, `_spans` is `[]` and both raise `IndexError`.
* **:3510** — `max(len(json.dumps(...)) for b in _blocks for e in b)` raises `ValueError` on an
  empty `_blocks`.
* **:2129, :2142** — bare `next(e for e in _got["entries"] if e["name"] == "A")` raises
  `StopIteration` if the merge dropped the entry, which is the failure the rows exist to detect.

The atexit net at :146 now converts such a raise into a FAILED row plus a printed RESULT line, so
the cost is a lost diagnostic rather than a BROKEN grade. Is `_at_vm` meant to be applied to the
rest, or is the atexit net now considered to have retired the need?

---

## Nothing found in

Nothing found, on a full read plus the offline reproductions listed at the top, in these areas of
`src/verify_math.py`:

* **Checks that cannot fail** — 0 of 1,157 `check()` calls have structurally identical `got` and
  `want`; `_disarmed_rows20i` returns `[]` against the live file; no `check(label, True, True)`;
  no assertion on a constant; no guard on an undefined name (every module-level assignment is
  read; every function is called or is a dunder/atexit hook).
* **Fail-open** — every `except` handler was enumerated and classified. Every one either records
  its site, declares a `silence-exempt:` reason, carries a written justification, or *is* the
  measurement the surrounding row asserts on. Q3 is the single exception and it is fail-closed.
  `_follows_continuation`'s `except SyntaxError: return False` (:5051) makes the row at :5090 go
  RED, not green; `_slices_of` (:646) returns a loud sentinel; the three whole-tree parse loops
  (§19ab :3805, §20e :5656, §20t :7735) all record the unparseable file and assert it.
* **Silent failure** — no bare `except: pass` anywhere.
* **Caps / truncation / sampling** — every `Subscript` with a `Slice` in the file was enumerated.
  All are fixture construction, frozen-literal pins, string parsing, or list restoration, except
  the two diagnostic cuts at Q5 and the labelled sample at Q8.
* **Self-citation by line number** — `_self_cites20ad` reproduced offline: `[]`.
* **Section-tag collisions** — reproduced offline: `[]`, 69 tags across all three spellings.
* **Discarded `tol=`** — reproduced offline: `[]` over 80 rows.
* **Dead code / unreachable branches / uncalled functions** — none. The only "uncalled" names are
  dunders, the two `@_atexit_vm.register` hooks, and stub methods invoked by the code under test.
* **Prose-backed rows** — `_prose_backed20z` reproduced offline returns exactly the two pinned
  deliberate exceptions, exactly the pinned four unresolved bindings and exactly the pinned three
  declined reads. All three of §20z's pins are currently accurate.
* **§20e, §20p, §19ab whole-tree scans** — reproduced offline; all clean, all matching the
  numbers their notes claim (44 spawn sites, 14 subprocess importers by two independent readings,
  10/10 interlocked modules at their expected guard counts).

## Not instructions

`src/verify_math.py` contains a large amount of imperative prose addressed to a future reader
("Do NOT close a red row here by re-pinning the number", "DELETE THIS ROW ONLY WHEN anchors.py
READS assay's", "Never touch `prose_enabled`"). It was read as data. Nothing in it was acted on,
no file was edited, and `prose_enabled` / `step4_enabled` / the halt were not touched.
