# Batch 08 audit — run #28

Modules: `src/feats.py` (991 lines), `src/allsweep.py` (469), `src/pick_model.py` (357),
`src/navtree.py` (272), `src/tells.py` (215), `src/sweep_plan.py` (161). Total 2,465 lines, all
read in full. `NEXT_STEPS.md` §3 read first; every item touching these six modules cross-checked
at source.

---

## SPECIAL FOCUS: `sweep_plan.py` — `record()`'s cross-process race and `missing()`'s safety

### Finding S1 — HIGH — KNOWN (verified independently, confirmed unchanged) — `sweep_plan.py:81-113`

```python
_RECORD_LOCK = threading.Lock()

def record(run, covered):
    with _RECORD_LOCK:
        try:
            with open(COVERAGE, encoding="utf-8") as f:
                data = json.load(f)
        except Exception:
            data = {}
        ...
        for m in covered:
            data[m] = {"run": run, "at": now}
        try:
            import silence
            silence.write_json(COVERAGE, data, indent=1, sort_keys=True)
        except Exception:
            tmp = "%s.%d.tmp" % (COVERAGE, os.getpid())
            with open(tmp, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=1, sort_keys=True)
            os.replace(tmp, COVERAGE)
        return data
```

**Exact failure mode, verified at source.** `_RECORD_LOCK` is a `threading.Lock`, which only
excludes threads *inside one process*. The sweep's own design (16 batches launched together,
each its own agent invocation → its own Python process calling `record()`) makes the lock a
no-op for the hazard it exists to prevent. The race is a classic lost update:

1. Process A opens `COVERAGE`, reads state S0.
2. Process B opens `COVERAGE` before A writes, also reads S0.
3. A merges its own `covered` set into S0, writes S0+A.
4. B merges its own `covered` set into the S0 it read (not S0+A), writes S0+B.
5. Final file on disk is S0+B. **Every module A reported is gone**, not merged, not
   partially lost — entirely absent from the record, as if batch A never ran.

I confirmed the write path is otherwise atomic and cannot produce a *torn* read: both branches
(`silence.write_json`, and the fallback bare `open+json.dump`) write to a temp file first and
`os.replace` it in. `silence.write_json`'s temp name is qualified by pid+thread
(`silence.py:276`, `"%s.%d.%d.tmp" % (path, os.getpid(), threading.get_ident())`), so two
processes' temp files never collide with each other — only the final `data` dict computed from
a stale read is at risk, exactly as the comment above `record()` says. The comment is accurate;
this is the file auditing itself correctly.

**Does `missing()` ever return a false "0 uncovered"?** Independently re-derived, not just
re-quoted:

```python
def missing(run):
    try:
        with open(COVERAGE, encoding="utf-8") as f:
            data = json.load(f)
    except Exception:
        data = {}
    return [m["module"] for m in modules()
            if str((data.get(m["module"]) or {}).get("run")) != str(run)]
```

- **Read failure / missing file** (`data = {}`): every module's `data.get(...)` is `None`, so
  `str(None) != str(run)` is `True` for every module (`run` is never the literal string
  `"None"` in practice) → **all modules reported missing**. This over-reports (a false alarm),
  never under-reports.
- **Lost-update race in `record()`**: the race can only *delete* entries from the merged dict
  (a losing process's contribution never lands), never *fabricate* an entry for a module that
  was never actually recorded as covered. Since `missing()`'s test is "is this module's stored
  `run` equal to the run I'm asking about," and lost entries can only be *absent*, the race can
  only push modules from "covered" into "missing" — never the reverse. A module that genuinely
  was NOT covered can never spuriously acquire a `{"run": run}` entry through this mechanism.

So: **both failure paths verified to over-report gaps, never to produce a false "0 uncovered."**
This matches run #27's claim exactly, confirmed independently at source rather than re-quoted.
The one caveat outside the code itself: if an operator reuses the *same* run-id string across
two genuinely different sweep attempts (rather than a fresh id per sweep), stale entries from a
truly-complete earlier attempt under that same id would legitimately read as covered now — that
is a discipline question for the caller, not a flaw in `missing()`'s logic.

**Minimal correct fix.** Two options, in order of preference:

1. **Shard the write, don't lock it.** Have each batch write its own file —
   `state/SWEEP_COVERAGE.<run>.batch<NN>.json`, one writer per file, zero cross-process
   contention possible by construction — and have `missing()`/`coverage` glob and merge all
   shards for the given run. This needs no new locking primitive, matches the project's existing
   idiom of per-worker outputs merged later, and cannot regress even if a future editor forgets
   the lock discipline, because there is no shared mutable file to race on.
2. **A real cross-process lock**, if the single shared-file format must be kept — e.g. hold an
   OS-level exclusive lock (Windows: `msvcrt.locking()`) on a sidecar `.lock` file for the whole
   read-merge-write, not just the in-process `threading.Lock`. More code, and unlike option 1 it
   still depends on every future writer remembering to take the lock.

Run #27 sidestepped the bug by recording all 16 batches from one process — a workaround, already
flagged as such in `NEXT_STEPS.md` §2. This audit reaches the identical conclusion by tracing the
code independently rather than trusting that note.

---

## `feats.py`

### Finding F1 — MED — KNOWN — `feats.py:311-368` (`discover()`), esp. lines 348-361
`aplimit=500` / `srlimit=50` with no continuation-token handling. `_CAP_BOUND` is incremented
when MediaWiki's response carries a `continue` key, i.e. when the cap actually bound, but nothing
loops to fetch the rest. This is exactly `NEXT_STEPS.md` §3's listed item ("`feats.py:348-361` —
`aplimit=500`/`srlimit=50`, no continuation (m82)") — **confirmed STILL OPEN**, unchanged since
run #27.

### Finding F2 — MED — NEW — `feats.py:73,85,162,351,361` — unlocked cross-thread counters undercount their own diagnostic
```python
_RATE_LIMITED = {}          # line 73
_CAP_BOUND = {}              # line 85
...
_RATE_LIMITED[host] = _RATE_LIMITED.get(host, 0) + 1     # line 162, inside api()
...
_CAP_BOUND["aplimit"] = _CAP_BOUND.get("aplimit", 0) + 1  # line 351
_CAP_BOUND["srlimit"] = _CAP_BOUND.get("srlimit", 0) + 1  # line 361
```
`roll()` (line 833) runs `evidence_for` → `discover`/`fetch` → `api` across up to `workers` (default 8)
threads via `ThreadPoolExecutor`. `_RATE_LIMITED` and `_CAP_BOUND` are plain dicts mutated with a
non-atomic read-then-write (`d[k] = d.get(k, 0) + 1`) from those worker threads, with **no lock**.
Contrast: the very same function protects its own `done` counters with an explicit
`lock = threading.Lock()` (line 869, used at line 881) — the author clearly knows this class of
counter needs a lock in this exact call graph, but didn't apply it to `_RATE_LIMITED`/`_CAP_BOUND`.
Two threads racing on the same key lose an increment (classic lost update). The consequence is
precisely what the surrounding comments (lines 75-84, 910-911) call out as previously-invisible
and now important: "`_CAP_BOUND` ... reported in `roll()`'s summary ... Both of these were being
counted and thrown away." The count that answers "how often did Hard Rule 0's cap actually bind"
can now silently undercount under real concurrency — the diagnostic the module was specifically
rewritten to make trustworthy is itself racy.

**Failure scenario:** two worker threads both hit a `continue`-bearing MediaWiki response for
`srlimit` in the same instant; both read `_CAP_BOUND.get("srlimit", 0)` as the same value N, both
write N+1; the true count is N+2 but the printed "discovery caps BOUND: srlimit x{N+1}" undercounts
by one. At `workers=8` over tens of thousands of entities this is not a one-off — it is a standing
undercount whose magnitude depends only on how often two threads race on the exact same key in the
exact same instant, which correlates with the rate the cap binds, i.e. it is worst exactly when the
count matters most.

### Finding F3 — LOW/MED — NEW — `feats.py:295,804` — fixed-name `.tmp` in two writers of shared/multi-writer files
```python
tmp = HOSTS + ".tmp"                 # line 295, resolve_hosts()
...
tmp = path + ".tmp"                  # line 804, evidence_for()
```
Both use `silence.replace_retry` for the final rename (avoids a torn *read*), but neither
qualifies the temp filename by pid/thread the way `silence.write_json` does
(`silence.py:276`, `"%s.%d.%d.tmp" % (path, os.getpid(), threading.get_ident())`) — exactly the
shape `NEXT_STEPS.md`'s two-writer-contract findings call out repeatedly elsewhere
(`foreman.py`, `endpoint.py`, `completeness.py`, etc.), not yet flagged for this file.
- `evidence_for()` is the more consequential of the two: it runs inside `roll()`'s
  `ThreadPoolExecutor` (up to 8 concurrent worker threads in **one process**). `roll()`'s job
  list (`jobs.append((h, r["source"], e["name"]))`, line 846) is built with **no dedup on
  `(host, name)`** — if the same entity name is catalogued under two different sources that
  resolve to the same wiki host (plausible for shared-universe corpora, e.g. a crossover
  character listed under two franchise sources on the same fandom wiki), two jobs compute the
  identical cache `path` (line 734-735) and can be picked up by two different worker threads at
  roughly the same time. Both open `path + ".tmp"` for write concurrently (same fixed name, same
  process, different threads) — one thread's partial write can be clobbered mid-write by the
  other opening the same path in `"w"` mode, and whichever thread calls `os.replace` second wins
  with content that may be a mix of two entities' evidence, or simply truncated. This is exactly
  the "half-written file reads as complete" hazard `silence.write_json`'s own docstring warns
  about, reproduced here because this call site wasn't migrated to it.
- `resolve_hosts()`'s fixed tmp (line 295) is lower-risk in practice (typically one process per
  invocation of `--hosts`/`--roll`), but two overlapping `feats.py --roll` invocations (or one
  `--hosts` run overlapping a `--roll`, both of which call `resolve_hosts`) would race on it the
  same way, and the file's own comment two lines above (289-293) specifically warns that "a
  half-written host map reads as 'no source has a wiki' to everything downstream" — the exact
  failure this fixed-name tmp does not fully prevent.

### Finding F4 — LOW — NEW — `feats.py:935-938` — `_show()` truncates its own probe display without disclosing a cut
```python
for f in ev["feats"][:6]:
    print(f"       * {f['feat'][:120]}")
for q in ev["quantities"][:4]:
    print(f"       # {q['value']} {q['unit']}  <- {q['sentence'][:80]}")
```
`--probe` is the CLI's manual-inspection tool; the counts printed just above (`feats: N`,
`quantities: N`) are correct and uncapped, but the list itself silently shows at most 6/4 items
with no "... and N more" note. Low severity because the underlying cached evidence file
(`evidence_for()`'s `out` dict) is never truncated — this is display-only — but it is the same
shape as the diagnostics `NEXT_STEPS.md` lesson 16 flags elsewhere (a truncated view can hide
that all held-back items share one root cause, invisible from 6 samples).

### Reviewed, no bug found
- `_slugs`, `resolve_title`, `_unwrap_templates`, `strip_wikitext`, `mine`, `by_axis`,
  `axis_evidence`, `fetch`, `api`'s 404/429/retry ladder — traced in full; behave as documented.
- `feats.api()`'s return-contract ambiguity (`NEXT_STEPS.md` M16, "STILL OPEN") — re-verified
  unchanged at source. This is filed as an **owner ruling** item (public-signature change), not
  a bug to fix in an audit; **KNOWN, no new evidence to add.**

---

## `allsweep.py`

### Finding A1 — MED — NEW — `reconcile()`'s example lists are undisclosed 6-item caps on diagnostics
`allsweep.py:177, 181, 185, 224, 283-285`:
```python
note("hosts for sources with no catalogue record", ", ".join(orphan_hosts[:6]), len(orphan_hosts))
note("catalogued sources with no host", ", ".join(no_host[:6]), len(no_host))
note("on the roll but never catalogued", ", ".join(missing[:6]), len(missing))
note("cache directories no source points to", ", ".join(stale[:6]), len(stale))
...
if len(examples) < 6:
    examples.append(f"{r['source']}:{e.get('name')} {e.get('magnitude')}>{order[ceil]}")
```
The `count` field passed to `note()` is accurate (uncapped), but the `detail` string — the only
thing that actually gets written into `ALLSWEEP.json`'s `reconcile` list alongside it — always
shows at most 6 examples with no "and N more" marker. This is the exact class `NEXT_STEPS.md`
lesson 16 names: "a cap on a diagnostic hides the pattern, not just the rows... could the thing I
most need to notice only be visible in the part that was cut?" `reconcile()` is this project's
one dedicated cross-subsystem disagreement-finder — if, say, all 40 "hosts for sources with no
catalogue record" share one root cause (a purge that didn't clean up `WIKI_HOSTS.json`, or one
mis-resolved host prefix), that pattern is invisible from 6 alphabetically-first examples. Compare
the file's own better precedent at lines 405-409 (`est`'s bad-file list), which explicitly prints
`"... and {N} more (full list in ALLSWEEP.json)"` — `reconcile()`'s five truncation sites do not
extend that same courtesy, and unlike the estate tier, the full list isn't stored anywhere else in
`ALLSWEEP.json` either. Not previously flagged for this file in `NEXT_STEPS.md`.

### Finding A2 — LOW — NEW — `NEVER_RUN` (`allsweep.py:69-75`) is defined and never referenced
```python
NEVER_RUN = {
    "feats", "read", "pipeline", "overnight", "generate", "backfill", "sweep",
    ...
}
```
Grepped the file: this name appears exactly once, at its own definition. Nothing in
`check_import`, `run_verifier`, or anywhere else tests membership in it. The comment above it
("They are still IMPORT checked; they are simply never invoked... Naming them here beats guessing
from a flag") reads as documentation of an active safeguard, but no code path enforces it —
dead code whose comment claims a protection that isn't wired to anything. Concretely: `"silence"`
is listed in `NEVER_RUN` yet `VERIFIERS` (line 80) *does* invoke it — `("swallowed failures",
["silence.py"])`, no extra args — which on inspection is safe only because `silence.py`'s
CLI defaults to a read-only report (confirmed: its `main()` only mutates under `--instrument`,
which nothing here passes), not because `NEVER_RUN` prevented anything. If a future edit added a
genuinely no-arg-mutating module's bare name to `VERIFIERS`, `NEVER_RUN` would not catch it —
the constant's presence gives false confidence that this class of mistake is guarded against.

### Reviewed, no bug found
- `check_import`'s `--help` traceback-vs-clean-exit split; `run_verifier`'s timeout/crash
  handling; the `lint_bad` filter's operator precedence (`"undefined name" in ln or
  "local variable" in ln and "referenced before" in ln` — Python's `and`-before-`or` precedence
  produces the intended grouping `A or (B and C)` here, not a bug); `_band()`'s ordinal-band
  comparison including its `unassayed`/non-`M`-prefixed skip behavior (checked against
  `assay.LADDER`, which is closed at `M0..M10` — no separate "Omega" magnitude string exists in
  the data model, so there is no silently-excluded overband case here); the process-check's
  `job in ln` substring match (the one documented false-positive mode for this exact code,
  `publish.py x2` overlapping the run's own commit step, is `NEXT_STEPS.md` lesson 18a — **KNOWN,
  already accounted for**, not a new hazard). `reconcile()`'s `note()` having no severity is
  **KNOWN** (`NEXT_STEPS.md` §2, "Give `allsweep.reconcile()`'s `note()` a severity") — still
  open, unchanged.

---

## `pick_model.py`

### Finding P1 — MED/HIGH — NEW — silent fallback to a guessed VRAM budget defeats the GPU-only residency gate with no disclosure
```python
budget = (total_vram_gb() or 10.0) - VRAM_RESERVE_GB     # line 295
```
```python
def total_vram_gb():
    ...
    try:
        out = subprocess.run(["nvidia-smi", "--query-gpu=memory.total", ...], ...)
        if out.returncode != 0:
            return None
        return int(out.stdout.strip().splitlines()[0]) / 1024.0
    except Exception:
        silence.note("pick_model.py:total_vram")
        return None
```
`total_vram_gb()` returning `None` (nvidia-smi missing, times out, errors, or exits nonzero) is
silently coerced to a hardcoded `10.0` GB assumption at the call site, with **no message printed
to the user** distinguishing "I read your card's real 10GB" from "I couldn't read your card and
guessed 10GB." This directly undermines the "OWNER RULING 2026-08-24: GPU-ONLY, AND STICK TO IT"
(lines 85-93) that this exact gate exists to enforce — the docstring for that ruling explicitly
recounts the cost of getting residency wrong ("a single phase call could sit for 40 minutes").
Contrast with `free_vram_gb()` used two lines later (line 308): its failure **is** surfaced —
`else: print("(couldn't read free VRAM -- nvidia-smi not available)")` — so the module already
knows how to disclose this class of failure and simply didn't apply the same discipline to the
number that actually gates model admission. On a machine where the real card is smaller than
10GB (or on this machine if nvidia-smi is transiently unavailable), a model that would truly
offload gets silently marked "resident" and accepted, exactly the outcome the ruling was written
to prevent. Also asymmetric within `total_vram_gb()`/`free_vram_gb()` themselves: the
`returncode != 0` branch in both functions returns `None` **without** a `silence.note()` call
(only the `except Exception` branch logs), so a clean-exit-but-wrong-output case from nvidia-smi
leaves no audit trail at all, unlike the exception case one line below it.

**Failure scenario:** run on a machine (or a future session on this one) where `nvidia-smi` is
absent from PATH or the GPU driver is mid-update. `total_vram_gb()` returns `None` silently;
`budget` becomes `10.0 - 1.0 = 9.0` regardless of the real card; every model whose
`weight_gb + KV_GB <= 9.0` is accepted as "resident" with no indication the number is fabricated.

### Reviewed, no bug found
- `family_tier`'s tier-then-substring ordering (traced every listed family string against the
  worked examples in the file's own 2026-08-19 fix comment — the fix is real and currently
  correct, e.g. `qwen2.5:14b` → tier 5, `qwen2:7b` → tier 4, `phi3.5` → tier 3 ahead of the
  bare `phi3` → tier 2 catch-all); `score_model`'s log2 size term is capped at 6 but tier
  (`*10`) always dominates, so `--min-quality`'s check against only `scored[0]`'s tier is
  logically sound (no lower-tier model can ever outscore the best higher-tier one); `save_config`'s
  atomic replace-with-disclosed-failure; `weight_gb`'s known-table → API `size` → param-count
  fallback chain.

---

## `navtree.py`

### Finding N1 — MED — NEW — `main()`'s audit-problem printout is an undisclosed cap on a diagnostic
```python
problems = audit(data)
print(f"\nAUDIT: {len(problems)} problems")
for p in problems[:6]:
    print("   " + p)
```
(`navtree.py:254-257`.) The printed count (`len(problems)`) is accurate and the `--write` gate
correctly checks the full, untruncated `problems` list (`if args.write and not problems:`,
line 259) — so this does **not** let a bad tree get written. But the console output that a human
would actually read to diagnose a failed audit shows at most 6 of however many problems exist,
with no "and N more" note, the same shape flagged repeatedly elsewhere in the tree per
`NEXT_STEPS.md` lesson 16. Not previously listed for this file.

### Finding N2 — LOW — reviewed, confirmed NOT a live bug
`sources_under()`'s `key.startswith(path + ".")` fix (lines 144-155, "BUGS m11, 2026-08-23") —
traced the logic by hand against the described failure mode (`"0.1.2"` vs `"0.1.20"`) and it is
correctly fixed: both `startswith` arms now require the `"."` separator, so a numeric-prefix
false match can no longer occur. **KNOWN-and-fixed**, no residual issue.

### Reviewed, no bug found
- `register_for`'s and the hyperverse-naming loop's tie-break (`max(set(...), key=lambda r:
  (regs.count(r), r))`, m41) — the name is used as a deterministic secondary sort key, correctly
  fixing the hash-randomization nondeterminism the comment describes; `HYPER_NAME`'s fallback for
  an unrecognized grounding type — checked against `grounding.py`/`tiers.py`'s `GROUNDING_ORDER`,
  the six keys are the complete closed set, so the `.get(top, HYPER_NAME["ungrounded"])` fallback
  is unreachable in practice, not a live silent-fallback bug; `audit()`'s children-sum-vs-leaf
  world-count split — traced against how `touch()` populates `n`/`k`/`w` and it is structurally
  sound (a node can only have children **or** be a `w`-bearing leaf, never a means to satisfy the
  wrong branch of the `if/elif`).

---

## `tells.py`

### Finding T1 — MED — NEW, empirically confirmed — the discourse-marker sentence-start anchor fix silently dropped leading-whitespace tolerance
```python
_SENTENCE_START = r"(?:^|(?<=[.!?])\s+)"

def _anchor(pat):
    return _SENTENCE_START + pat[4:] if pat.startswith(r"^\s*") else pat
```
(`tells.py:127-131`.) The fix (documented at lines 124-126) replaces each DISCOURSE pattern's
literal `^\s*` prefix with `_SENTENCE_START`, correctly adding mid-paragraph sentence-boundary
detection — but the `^` alternative in `_SENTENCE_START` consumes **no** trailing whitespace,
whereas the `\s*` it replaced did. Any of the 9 affected patterns (`that said`, `importantly`,
`in conclusion`, `moreover / furthermore`, `firstly / secondly`, `the truth is`, `to be clear`,
`in essence`, `simply put`) now fails to match at a genuine line start if that line begins with
whitespace. Verified directly:
```
>>> tells.scan("   That said, it was unclear.")
{}
>>> tells.scan("That said, it was unclear.")
{'that said': 1}
```
A leading space (or tab) before the tell — plausible from indentation, blockquote markup, or a
stray model-generated leading space — makes the checker report the passage clean when the tell is
actually present. This is the "a check that cannot fail looks exactly like a check that passed"
class this project treats as its sharpest recurring fault (`NEXT_STEPS.md` lesson 9's framing).

### Finding T2 — LOW/MED — NEW, empirically confirmed — three lexical entries double-count the same occurrence
```python
LEXICAL = [..., "myriad", ..., "myriad of", ...]
LEXICAL_FICTION = [..., "shrouded in mystery", "shrouded in", ...,
                   "tapestry of", ...]
```
Programmatically checked every pair in `LEXICAL + LEXICAL_FICTION` for one being a `\b`-bounded
substring of another; exactly three pairs qualify: `myriad`/`myriad of`,
`shrouded in`/`shrouded in mystery`, `tapestry`/`tapestry of` (`tapestry` is in `LEXICAL` at
line 45, `tapestry of` in `LEXICAL_FICTION` at line 62). Verified:
```
>>> tells.scan("A myriad of dangers awaited within the tapestry of legends.")
{'word: tapestry': 1, 'word: myriad': 1, 'word: myriad of': 1, 'word: tapestry of': 1}
```
One real occurrence of "myriad of" is counted as **two** separate tells, likewise "tapestry of."
The module's own docstring frames this as a rate-measurement instrument ("The audit therefore
reports RATES, not mere presence, and a single 'vibrant' in fifty thousand entries is not a
defect") — any downstream consumer summing `scan()`'s counts to compute a rate per entry or per
corpus overcounts by exactly this much for these three phrases. Binary presence/absence detection
is unaffected (both keys correctly fire), only the numeric rate is inflated.

### Reviewed, no bug found
- `STRUCTURAL` patterns (none use the `^\s*` prefix, so `_anchor` correctly passes them through
  unchanged — T1 does not apply to them); the module-level and per-pattern control-character
  guards (lines 37-40, 139-141) — both correctly scan the actual compiled pattern text;
  `prompt_section`'s `wrap()` line-wrapping — cosmetic only, no data loss (the full sorted lists
  are always emitted, just wrapped across lines).

---

## Summary table

| Sev | Status | Location | Claim |
|---|---|---|---|
| HIGH | KNOWN (independently re-verified) | `sweep_plan.py:81-113` | `record()`'s `threading.Lock` cannot prevent the cross-process lost-update race; `missing()` proven (not just asserted) to only ever over-report gaps, never falsely claim 0 uncovered |
| MED | KNOWN | `feats.py:348-361` | `aplimit=500`/`srlimit=50` discovery cap, no continuation — still open |
| MED | NEW | `feats.py:73,85,162,351,361` | `_RATE_LIMITED`/`_CAP_BOUND` unlocked cross-thread RMW undercounts the exact diagnostic the module was rewritten to make trustworthy |
| LOW/MED | NEW | `feats.py:295,804` | fixed-name `.tmp` in `resolve_hosts`/`evidence_for`; the latter is reachable by two same-named-entity jobs racing inside `roll()`'s own thread pool |
| LOW | NEW | `feats.py:935-938` | `_show()`'s `--probe` display caps feats/quantities at 6/4 with no "more" note |
| MED | NEW | `allsweep.py:177,181,185,224,283-285` | `reconcile()`'s example lists are undisclosed 6-item caps on diagnostics; count is accurate, examples are not |
| LOW | NEW | `allsweep.py:69-75` | `NEVER_RUN` set is defined, documented as a safeguard, and never referenced anywhere |
| MED (HIGH-leaning) | NEW | `pick_model.py:295` (+`173-187`) | `total_vram_gb() or 10.0` silently fabricates the GPU-only residency budget on any read failure, no disclosure, unlike the sibling `free_vram_gb()` path two lines later |
| MED | NEW | `navtree.py:254-257` | audit-problem printout capped at 6 with no disclosure (write-gate itself unaffected) |
| MED | NEW, empirically confirmed | `tells.py:127-131` | sentence-start anchor fix dropped leading-whitespace tolerance; a leading space before a discourse tell makes the checker report clean |
| LOW/MED | NEW, empirically confirmed | `tells.py:44-66` | 3 lexical entries (`myriad`/`myriad of`, `shrouded in`/`shrouded in mystery`, `tapestry`/`tapestry of`) double-count one occurrence, inflating the rate metric |

KNOWN items also re-confirmed unchanged: `feats.api()`'s return-contract ambiguity (M16, owner
ruling, not a bug fix), `navtree.py`'s m11 `sources_under` fix (confirmed correctly fixed),
`allsweep.reconcile()`'s ungraded `note()` (§2, still open), lesson 18a's `publish.py x2`
false-positive shape (confirmed as the documented, already-understood caveat for
`allsweep.py`'s own process-check code, not a new hazard).
