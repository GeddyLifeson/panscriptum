# sweep47 — AUDIT batch02 — `src/verify_math.py`

**Coverage: lines 1–10910, every line, in thirteen contiguous reads. No range unread.**
(The brief says 10,796 / 10,869 lines; the file on disk is 10,910. The extra lines are the
2026-09-07 additions, so the brief's count was taken before the last edit landed.)

Method: full read, then five mechanical passes over the file's own parse tree (tautology scan,
`X == X` scan, conditional-`check()` scan, ExceptHandler scan, duplicate-label scan), plus
verification of every claim the new rows make against the module they are about
(`assay.py`, `standards.py`, `sevenfold.py`, `anchors.py`, `thread_integrity.py`, `sweep_plan.py`).

---

## 1. The 2026-09-07 additions — what I checked, and what holds

**§19n (`_mode_stable`, the all-tied triple).** Correct and genuinely frozen. Hand-evaluated:
with every count 1 the key collapses to `(1, v)`, so `max` returns the lexicographically largest
member — `zeta`, `xi`, `upsilon` for the three fixtures. Deterministic under any `PYTHONHASHSEED`,
and a different answer under thirteen seeds once `, v` is dropped, exactly as the note claims.
The companion source row (`key=lambda r: (regs.count(r), r)` in `navtree.py`) is what actually
holds the section. **No defect.**

**§16's sibling frozen list** (`affinity_order`, line 1607) also checks out by hand against
`sevenfold.affinity_order`: `alpha, beta, zeta, theta, gamma, eta, epsilon, delta`. Verified.
Note that `affinity_order`'s **start** element — `max(members, key=<weight sum only>)` at
`sevenfold.py:87` — carries no name tie-break, so on an all-tied graph the start is decided by
the caller's list order rather than by a rule. It is deterministic today because `members`
arrives as a list; the pinned source row at :1617 pins only the *loop* tie-break. Raised as a
question below.

**§20r INSTRUMENT_WINDOWS block (7 new rows).** Verified against `assay.py:696–700` — both halves
of the refusal string, both `or "no rungs"` operands, both fixtures, and the two-sided ACCEPTED
control. `anchors.py:427` really does index `INSTRUMENT_WINDOWS` across the whole Ladder
unguarded, so the KeyError claim in the comment is true. Restore is in a `finally`.
**Sound work.**

**§20r assay-transparency block (~24 new rows).** Verified field by field against
`assay.py:1543–1610` and `:1222–1236`. `interval` and `_quadrature` are both `round(...,2)`, so
the `interval - quadrature == widening_added` row is safe under `tol=1e-9`. `hands_source`
really carries `UNRECOGNISED signature(s)`; `unrecognised_hands` really judges a key whose value
is `None`, which is the property the comment says it is keeping. **Sound work.**

**§20r rho-fallback (unconditional replacement).** The new rows at :7395–7455 construct the
fallback state instead of waiting for it, which is the substance of open order **92fd876c2f0e**.
That order looks effectively addressed — but the *conditional* `if _stamp.startswith("FALLBACK")
/ else` pair at **:7376–7382 is still standing** beside it, and my conditional-`check()` scan
found those two to be the only environment-branched rows left in the file (the others are the
deliberate secondopinion pair and §20u's fold-back). Not re-filed; reported so the order gets
closed properly rather than half-closed.

**§19ai boundary rows (order c1d6ddfe148b).** The repair is real: :4148–4187 now drives
`standards.py:751`'s cut from both sides, swaps `MIN_CALLS_TO_JUDGE_RATE` under the live function
and watches the answer move, then re-execs `standards.py` with `tuning.MIN_CALLS_TO_JUDGE` bumped
+7. Verified `standards.py:751` is `if calls < MIN_CALLS_TO_JUDGE_RATE:` and `standards.py:67` is
the derivation. `standards.py` has no import-time network or spawn, so the re-exec is safe.
**c1d6ddfe148b looks answerable.**

---

## 2. THE TOKEN-FLOW PIN — the three questions the brief asked

### Is the restore exception-safe?
**Yes, in practice.** `_pool19ai` snapshots `_flow_held19ai = dict(_STx._TOKENFLOW)` and calls
`.update()` *before* the `try:`, and restores with `clear()/update()` in the `finally`. The only
unprotected window is a raise inside `dict.update` on a plain dict, which cannot occur. The pin
mutates the dict **in place**, so `ollama_token_flow`'s module-global read sees it. Verified.

### Does the pin actually suppress the probe?
**Yes today — and only by the coincidence of a default argument.**
`ollama_token_flow(ttl=300.0, timeout=300)` returns the cache when
`now - _TOKENFLOW["at"] < ttl`; the pin writes `at = time.time()`; and `standards.py:1901` calls
`ollama_token_flow()` with **no ttl**. All three verified at source.

### Does the control row prove the probe did not fire?
**No — and nothing else does either.** See finding F1.

### And the general question
`§19ai`'s fix closed **one** of this file's ten live-operational-state call sites, and today's
new rows added three more calls to that same site: `_pool19ai` went from six live
`standards.check()` runs to nine. The full enumeration is §4 below.

---

## 3. FINDINGS FILED

### F1 — `VM_S19AI_TOKENFLOW_PIN_IS_ITSELF_UNTESTED` (MINOR / SESSION)

The pin is load-bearing — it is what stops a 300-second live generation and a permanent
`silent:standards.py:token-flow` row in the operational ledger — and **nothing asserts that it
works**. Its effectiveness rests entirely on `standards.py:1901` calling `ollama_token_flow()`
with the default `ttl=300.0`. Change that one call to `ollama_token_flow(ttl=0)` — the exact
spelling **§19ab uses eleven hundred lines earlier in this same file** — and the pin becomes a
no-op, the probe fires again, and **every §19ai row stays green**.

The `[control]` row at :4193 asserts the cache was **restored**, which is a different property,
and one that would hold identically whether or not a probe fired: the `finally` clobbers the
probe's own write on the way out. So the only remaining detector is §20z, and only on the runs
where the probe *fails* — i.e. the flake this fix was landed to remove is still the sole witness
that the fix is working. That is this file's own §0 doctrine broken on its newest guard: "a guard
nobody has watched refuse is a guard nobody has evidence about."

**Remedy** (cheap; the machinery is already in the file): inside one `_pool19ai` call, stub
`urllib.request.urlopen` to raise `AssertionError("the pin did not hold")` — §19ab at :3623
already does exactly this stubbing — and assert the call returned normally. That row goes red the
day the pin stops suppressing, whatever the reason.

### F2 — `VM_SELF_CITATIONS_BY_LINE_HAVE_ALL_DRIFTED` (MINOR / SESSION)

`verify_math.py` cites **itself** by line number in thirteen places and **every one of them now
points at unrelated code**. Verified target by target. Three of the thirteen are in the §19ai
comment block written **today** for order c1d6ddfe148b (`:8026-8033`, `:8023`, `:4273-4301`).

| cite sits at | claims | actually at |
|---|---|---|
| :279 | `:2358-2362` "Every other deliberate swallow…" | 2517–2521 |
| :280 | `:7285-7293` "inventory of every ExceptHandler" | 8036–8044 |
| :1516 | `verify_math.py:1457` (the §16 SF.build leak) | 1523 |
| :1649 | `:1287` "reads `BG.HAMLET_FLOOR` correctly" | 1657 / 1663 |
| :1653 | `:346` "the `tol=` was silently discarded" | 566–584 |
| :4136 | `:8026-8033` batch3 source row | 8461–8468 |
| :4137 | `:8023` batch3 equality row | 8458–8460 |
| :4146 | `:4273-4301` the restart-horizon device | 4406–4434 |
| :8733 | `:6771-6779` order c8704a41a70f's construction | 7522–7530 |
| :8868 | `:5556-5588` §20k's "it was ABSENT" passage | 5866–5880 / 7527 |
| :8881 | `:7609` "an UNMEASURED reading on a breaching row" | 8365–8367 |
| :9856 | `:7541` standards' `[:120]` join row | 8292–8295 |
| :10598 | `:337` "an AST scan of all 68 rows passing `tol=`" | 574–581 |

This file's cross-*module* citations are accurate (`standards.py:751`, `standards.py:67`,
`standards.py:1901`, `anchors.py:427`, `assay.py:147-189`, `sevenfold.py:86` all check out), so
this is specifically the self-citation class — and it is the class most likely to rot, because
the file grows by fifty rows a shift.

The file has already ruled on this. **§24 at :4941 records "CITED BY SYMBOL, NOT BY LINE (order
a09a0e003c31, run #37)"** — written about a citation of `sweep.py`. The ruling was never applied
to the file's citations of itself.

The damage is not cosmetic. `:279–280` is the **swallow-exemption inventory** — the paragraph a
reader consults to decide whether a bare `except` in this tree is sanctioned doctrine or a defect
— and both of its self-citations are wrong, so the doctrine cannot be looked up from the place
that points at it. §20y asserts that no two section TAGS collide and §20z asserts that no two row
LABELS collide; nothing asserts that a self-citation resolves, which is the ratchet-shaped remedy
(and a cheap one: the tag/label scanners already read this file's own source).

---

## 4. EVERY REMAINING NON-HERMETIC ROW — enumerated, as the brief asked

Sites whose verdict can turn on something outside the tree. **(a) = already owned by an open
order; not re-filed.**

| where | touches | owned by |
|---|---|---|
| :4776 `_D20.jobs()` | live `state/read_auto.log`, `roll_auto.log` | (a) 728d9e99e9ec |
| :4858 `_on21._proc_lines()` and the row asserting it returned a listing | PowerShell/WMI spawn; reddens on a loaded machine | (a) 728d9e99e9ec — names this row explicitly |
| :4072 `_STx.check(st)` inside `_pool19ai` — **nine calls now, was six** | fandom TCP probe, PowerShell spawn, disk. Token flow is now pinned; the rest is not | (a) 728d9e99e9ec / 74f1bc47da2a |
| :5967 `_dash20k.state()` | calls `standards.check()` internally | (a) 728d9e99e9ec |
| :5971, :5994, :6009 `_stmod20k.check(...)` | **the first unpinned token-flow probe of the run lands here** | (a) 728d9e99e9ec / 79d51aef8b71 |
| :7898 `standards.check(dashboard.state())` | same | (a) 74f1bc47da2a |
| :8388, :8402 `dashboard.state()` / the clean `standards.check()` twin | same. :8411 IS wrapped; its clean twin at :8402 is not | (a) 74f1bc47da2a |
| :4313 real `subprocess.Popen` + `os.kill` | spawns a child on every run | design — it is §20a's subject |
| :3733 / :3752 / :3782 `time.sleep` + heartbeat comparisons | wall clock under load | design |
| :6150–6181 §20n shard glob + `time.time()` | live `state/sweep_shards/`, written by the sweep in flight | design (b18acbb35760's repair) |
| :1357–1379 `load_thread_graph()`, `THREAD_INTEGRITY_FLOOR.json` | live `data/THREADS.json`; live `state/`. The floor is written atomically via `silence.write_json`, so a torn read is not reachable | (a) f40f701594a4 (the `data/` junction) |
| :2489, :5365 probe files written into the **live** `state/` directory | shared dir; both removed in a `finally` | design, noted in place |
| :4229 `_PBx.SITE` | process environment at import time | design |

**Order 79d51aef8b71's step (2) is answerable now.** That order says "the live connection comes
from somewhere else and that call site has NOT been located. Do not assume 19ab." It was
`_pool19ai → standards.check() → ollama_token_flow()`, and today's edit located and pinned it.
Five unpinned sites remain, so the order should not be closed — but its open question is
answered, and 728d9e99e9ec's site list can be narrowed by one and widened by three.

---

## 5. QUESTIONS (not filed — each may be deliberate)

1. **`affinity_order`'s start element has no name tie-break.** `sevenfold.py:87` is
   `max(members, key=<weight sum>)` over a *list*, so on an all-tied block the start is
   `members[0]`. §16's source row pins only the loop's `, m`. Is the caller's list order
   guaranteed stable across processes at every `shelve()` call site, or is this the same
   hash-seed exposure one line above the one that was repaired?
2. **`_as_bad["attestation_sigma"] == round(A.SIGMA_MAX, 4)` (:7301).** `_attestation_sigma`
   computes `min(SIGMA_MAX, .get(attestation, SIGMA_MAX))`, so for *any* unrecognised grade this
   equals SIGMA_MAX by construction of that one expression. It still pins *which* sentinel is
   substituted, so it can fail — but it is the shape order c1d6ddfe148b was filed about.
   Deliberate?
3. **`covers_all_signatures` rows (:7184, :7267).** `assay.py`'s own return dict states this
   field "CANNOT be False". :7267 is honestly labelled `[control]`; :7184 is not, and reads as a
   live assertion. The independent re-derivation at :7186 is what actually carries the claim.
4. **§20n's `except Exception: continue` on an unreadable shard (:6154)** carries a prose comment
   but neither a `silence.note` site nor the `"silence-exempt:"` string this file's doctrine
   requires three times over. An unreadable shard belonging to the newest run silently shifts the
   completeness proof onto an *older* run — honest per the comment, but uncounted.
5. **`_iw_verdict` and `_sigma_table_verdict` have no `[control]` row asserting the module table
   was put back**, unlike the neighbouring `BAND_EDGES` block at :7015 and the `_RHO_CACHE` block
   at :7451, which both do. `_iw_verdict(_iw_saved)` at :7170 restores only as a side effect.

---

## 6. CLEAN

- No `check(label, X, X)` textual tautology anywhere — 1085 static `check()` call sites scanned.
- No `check(label, X == X, ...)` self-comparison.
- No duplicate literal labels (1056 literal + 29 computed).
- Exactly one bare `except: pass` (:8662) and it is the correct spelling of the measurement.
- The `_slices_of`, `_disarmed_rows20i`, `_interlock20p`, `_follows_continuation`,
  `_writes_the_config20p`, `_prose_backed20z`, `_discarded_tol20z` and `_dup_labels20z`
  detectors all carry two-sided controls.
- No Hard Rule 0 truncation (silent or otherwise) found in this file.
