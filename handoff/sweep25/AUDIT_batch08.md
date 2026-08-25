# AUDIT batch08 — sweep25

Files in scope, all read in full, start to end, no sampling:

- `src/feats.py` — 991 lines, read in full.
- `src/completeness.py` — 455 lines, read in full.
- `src/tiers.py` — 347 lines, read in full.
- `src/feats_index.py` — 263 lines, read in full.
- `src/tells.py` — 215 lines, read in full.
- `src/sweep_plan.py` — 161 lines, read in full.

Total: 2,432 lines across 6 modules.

Cross-referenced: `src/silence.py` (`write_json`, `replace_retry`, `note`), `src/endpoint.py`
(`api_url`, `detect`, `MODE_RAW`), `NEXT_STEPS.md` §3, and the prior sweep's
`handoff/sweep24/AUDIT_batch08.md`, which happened to cover `feats.py` and `completeness.py` in
depth already (different file set for the rest — this run's `tiers.py`, `feats_index.py`,
`tells.py`, `sweep_plan.py` were not in that report). Every carried-forward finding below was
**independently re-read and re-verified against the current source**, not merely copied.

**Two findings in this report were proved by running real code**, not just inferred:
1. `feats.py`'s `WIKI_HOSTS.json` membership-cache bug — confirmed live in the real data file
   (7 sources currently cached `null`).
2. `sweep_plan.record()`'s cross-process lost-update race — **reproduced empirically** with two
   real concurrent OS processes (not threads) sharing the same coverage file; a batch's fully
   successful `record()` call vanished from disk, clobbered by a second process's stale write.

---

## feats.py (991 lines)

### F1. `resolve_title()` / `_page_exists()` — fully-written, dead code [KNOWN — m80]
**`feats.py:376-424`**. Grepped the entire `src/` tree for `resolve_title(` and `_page_exists(`:
the only hits are the two `def` lines themselves. No caller in `discover()`, `fetch()`,
`evidence_for()`, or `roll()` — all pass the catalogue's raw `name` straight through to `fetch()`,
which is exactly the mismatch (`"Hulk (Bruce Banner)"` vs. the wiki's `"Hulk"`) `resolve_title`'s
own docstring says costs 17,148 entries. **On "lost vs. withheld":** this repo has no commit
history to blame (`git log` returns "does not have any commits yet"), so provenance can't be
settled from version control. Circumstantial reading favors **LOST, not withheld**: the function
carries a fully-worked docstring with measured numbers and a careful ranking algorithm — the kind
of effort nobody invests in code they intend to leave switched off — and nothing anywhere (no
comment, no `NEXT_STEPS` note predating this run, no `# not wired in because...`) discloses an
intentional decision to withhold it. It reads as a fix that was written, tested standalone
(`--self-test`/`--probe` paths don't exercise it either), and never got the one-line
`resolve_title()` call spliced into `discover()`/`fetch()`/`evidence_for()`.
Already logged as **m80**; re-confirmed true as of this run. **VERIFIED.**

### F2. `discover()` — `aplimit=500` / `srlimit=50` truncate on `continue`; measured, not fixed [KNOWN — m82]
**`feats.py:311-368`**. `_CAP_BOUND` increments when MediaWiki signals `continue` (lines
350-351, 360-361) but no continuation loop follows either request — the entity's discovery list
is used as-is. **Quantifying "what is lost":** I could not run this against the live network from
this sandbox in the time available, and no prior `roll()` run's stdout/log survives on disk
(searched `state/*.log`, nothing named `feats` or containing "discovery caps"). The measurement
mechanism itself (`_CAP_BOUND`, printed at `roll()`'s end, `:912-917`) is real and correctly
wired — the honest answer is "the file can tell you the next time `--roll` actually runs," not
zero. Re-confirmed the cap and the missing loop are exactly as previously documented.
**UNVERIFIED for the magnitude** (no live network run performed this session); **VERIFIED** that
the cap and the counter-without-a-fix are present in the current source.

### F3. `api()`/`alive()` return `None` for both absence and transient failure, cached into `WIKI_HOSTS.json` by a MEMBERSHIP test [KNOWN, re-confirmed live against real data]
**`feats.py:120-174`** (`api()`), **`:177-178`** (`alive()`), **`:243-299`** (`resolve_hosts()`).
`alive()` calls `api(..., retries=0)` — one attempt, no retry budget — so a single transient
timeout makes a live wiki read as dead. In `resolve_hosts()`'s slug-guessing loop (`:282-288`),
if every candidate slug fails `alive()` (including from one bad probe), `known[src] = None` is
written and persisted via `silence.replace_retry` (the atomic write itself is correct). The bug is
the *read* path: `if src in known: continue` (`:265-266`) is `src in known`, not
`known.get(src)` — `True` even when the value is `None` — so a source that failed one network
blip is never reconsidered by any future `--hosts` run, and `--roll`'s call
(`:965`, `resolve_hosts(recs, verify=False)`) doesn't even attempt fresh guessing on unresolved
entries at all.
**Confirmed live against the real file:**
```
$ python -c "... json.load(open('data/WIKI_HOSTS.json'))"
203 total, 7 null entries
['JMBrew', 'Kobold Press (Midgard Heroes Handbook, Midgard Worldbook)',
 'The Amethyst / Cockroach King screenplay (Chroma Wastes)',
 "aurora_mods (Way of the Inkmaster)", "swordmeow's Atavist",
 'the Sex Worker background', 'the Weaveshaper Ateliers']
```
Whether these specific 7 are genuinely wiki-less or are transient-failure casualties can't be
told apart from the file alone — which is exactly the bug: the mechanism that would let you tell
them apart (a distinct "unresolved due to network failure, retry me" state) does not exist. The
membership-vs-truthiness defect itself is directly confirmed by reading `:265-266`.
**VERIFIED** (mechanism by source reading; real-world presence of null entries confirmed live).

### F4. `_RATE_LIMITED` / `_CAP_BOUND` incremented without a lock from `ThreadPoolExecutor` workers [KNOWN]
**`feats.py:73, 85, 162, 351, 361`**. Unlike `done` in `roll()` (correctly `lock`-protected,
`:869/881-899`), these two dicts are read-modify-written from every worker thread with no lock.
Diagnostic-only blast radius (undercounts the printed "429s absorbed" / "discovery caps BOUND"
summary lines by a small non-deterministic amount) — no entity data is corrupted.
**VERIFIED** (same as prior sweep; re-read, unchanged).

### F5. `silence.note()` site tags no longer match their line numbers [KNOWN, cosmetic]
**`feats.py:159, 171, 451, 743, 878`** — e.g. `"feats.py:125"` is now emitted from line 159.
Doesn't change behavior (opaque bucket key for `health.record`) but misleads anyone using the
failure ledger to jump to source. **VERIFIED.**

### F6. `remine()` — genuinely dead code, but honestly disclosed [not a finding]
**`feats.py:811-828`**. Grepped `src/*.py` for `\bremine\b`: only the `def` itself. Unlike F1,
this one's own comment says so accurately ("This function currently has no callers... 2026-08-25")
— the docstring does not claim a behavior the code lacks, it discloses the gap. Not filed as a
finding; noted for completeness since the batch instructions ask about dead-code call sites.

---

## completeness.py (455 lines)

### C1. `category_size_probe()` — shared global cache mutated *and* `json.dump`-iterated from unlocked `ThreadPoolExecutor` workers, over a fixed non-unique temp filename [KNOWN]
**`completeness.py:66-119`**, most importantly `:110-116`:
```python
cache = _cs_load()                       # returns the SAME dict object every call
cache[k] = {"at": time.time(), "n": got}  # mutated from every worker thread
tmp = _CS_CACHE_P + ".tmp"                # ONE shared path, no pid/thread differentiation
with open(tmp, "w", encoding="utf-8") as f:
    json.dump(cache, f)                   # iterates the SAME dict another thread may insert into
silence.replace_retry(tmp, _CS_CACHE_P)
```
Called from `audit()`'s `work()` under `ThreadPoolExecutor(max_workers=workers)` (default 6,
`:333`), 8 probes per source. Two live hazards: (a) `json.dump` iterating `cache` while another
thread inserts a new key can raise `RuntimeError: dictionary changed size during iteration`
(silently swallowed by the surrounding `except Exception: silence.note(...)`, dropping that
thread's cache write); (b) the fixed `.tmp` name means two threads racing on `open(tmp, "w")`
can interleave/truncate each other's bytes before either `replace_retry` call runs — the exact
pattern `silence.write_json()` (`silence.py:250-287`) was built to close project-wide (PID+thread
in the tmp name), but this call site was never migrated to it. `_cs_load()`'s own
`except Exception: pass` (`:76-77`) then treats resulting corruption identically to "no cache
yet" and silently resets to `{}`, forcing a full re-probe against fandom's API — the exact traffic
pattern the module's own docstring says got the machine IP-banned once already.
**VERIFIED** (re-read against current line numbers; matches prior sweep's finding exactly).

### C2. `land()` — correctly guarded [checked, no new finding]
**`completeness.py:342-407`**. Three separate guards, all present and correct in current source:
the empty-result refusal, the `SHRINK_FLOOR` (0.5) partial-loss refusal, and — the one many
similar modules in this tree get wrong — `land()` actually **checks and propagates**
`silence.replace_retry()`'s boolean return (`:401-406`), returning `False` and writing to stderr
if the atomic rename was denied. This is the two-writer contract done right; worth naming as a
positive result since NEXT_STEPS' "audit every ignored `write_json`/`replace_retry` return"
directive makes silent-ignore the default assumption. **No finding here.**

No other findings beyond C1 — the rest of the module (`audit()`, `host_reachable()`,
`catalogued_counts()`) reads correctly and matches its own extensive docstrings.

---

## tiers.py (347 lines) — CLEAN, re-confirmed

Read in full. Matches the prior sweep's CLEAN classification. Checked specifically for this run:
- `_components()` (`:203-223`): BFS component extraction, correct; isolated nodes (no edge above
  threshold) are deliberately excluded from `comps` and surface instead as `unaddressed` in
  `main()` — matches the module's own stated design, not a bug.
- Nesting/monotonicity assertions (`:119-120`) and the runtime containment check in `main()`
  (`:307-319`) are real checks that can fail (not tautologies) — `CUTS` ordering and
  `MULTIVERSE_THRESHOLD` are concrete numbers that could violate the assertions if edited
  carelessly, and the containment-violation counter walks real peer groups rather than asserting
  a constant.
- `main()`'s `unaddressed[:6]` (`:298`) and `deliberate_joins()`'s `shared.get((a,b), [])[:3]`
  (`:273`) are **stdout display truncations only** — the full `unaddressed` count is printed
  first (`len(unaddressed)`, uncapped), and the persisted `TIERS.json` (`:341`, via
  `silence.write_json`, correctly atomic) carries every source with no truncation anywhere.
  Consistent with `feats.py`'s own `_show()` display pattern; not a Hard Rule 0 violation since
  no data reaching disk or a downstream consumer is capped.
**No findings.**

---

## feats_index.py (263 lines)

### FI1. `load_index()` — hyphenated hosts stranded by an irreversible `_`→`.` replace [KNOWN]
**`feats_index.py:148`**: `host = host_dir.replace("_", ".").lower()`. Directory names under
`data/readfeats/` are sanitized host names (dots become underscores when the directory was
created), so this reversal is correct for ordinary hosts (`dragonball_fandom_com` →
`dragonball.fandom.com`) but wrong for any host whose real name itself contains a hyphen inside
what was originally a dot-separated segment being reconstructed from underscores — confirmed by
name in NEXT_STEPS as affecting `date-a-live`, `sakamoto-days`, `the-amazing-digital-circus`,
`uncle-grandpa`. Not independently re-verified against the live directory listing this run (time
budget went to the two empirically-tested items above), but the code at `:148` is unchanged from
what NEXT_STEPS describes. **KNOWN, re-read at current line, code unchanged.**

No other findings. `feats_for_source()` (`:166-209`) and `audit()` (`:212-239`) both correctly
implement "NO CAPS" as the module's own docstring insists — every match is appended, sort is
ranking-only (`:208`), and `audit()`'s stranded-record accounting has no truncation anywhere.
The shared-host handling (an entity legitimately joining more than one source's cast, `:56-60`
docstring, `:191-207` implementation) is intentional and correctly implemented, not a duplication
bug.

---

## tells.py (215 lines)

### T1. `"not merely X but Y"` — alternation precedence makes the `but`-requirement apply to only one branch [KNOWN, re-verified by execution]
**`tells.py:70`**:
```python
"not merely X but Y": r"\bnot merely\b|\bnot simply\b|\bnot just\b.{0,40}\bbut\b",
```
`|` has the lowest precedence in the regex, so this is three independent alternatives:
`\bnot merely\b`, OR `\bnot simply\b`, OR `\bnot just\b.{0,40}\bbut\b` — only the third actually
requires a following `but`. Bare "not merely" / "not simply" (with no `but` anywhere nearby) false-
positives as this tell.
**Re-verified by running the real `tells.scan()` against fresh test sentences this session:**
```
tells.scan("It was not merely impressive on its own, with no further clause at all.")
  -> {'not merely X but Y': 1}
tells.scan("It was not simply impressive by itself, nothing more said.")
  -> {'not merely X but Y': 1}
```
Both fire despite containing no "but" clause. Correct form would be
`r"\b(?:not merely|not simply|not just)\b.{0,40}\bbut\b"` (grouping the alternation so `.{0,40}\bbut\b`
applies to all three). **VERIFIED by execution** (fresh test, this session).

No other findings. The rest of `STRUCTURAL`/`DISCOURSE`/`LEXICAL` patterns read correctly; the
sentence-boundary anchor rewrite (`_anchor()`, `:127-131`, converting `^\s*` patterns to also fire
mid-paragraph after a sentence terminator) is correct and matches its own docstring's stated
motivation. `prompt_section()`'s claim that the prompt and the audit are generated from one list
(never drift) is true — both `_COMPILED`/`_LEX` and `wrap(sorted(...))` read from the same
`LEXICAL`/`LEXICAL_FICTION`/`STRUCTURAL`/`DISCOURSE` module-level lists.

---

## sweep_plan.py (161 lines) — the module that partitions this very audit

### SP1. `record()` — the cross-process lost-update race is real, reproduced empirically, and the docstring's framing invites the exact misplaced confidence it's meant to prevent
**`feats.py`'s sibling bug, but here — `sweep_plan.py:81-113`:**
```python
_RECORD_LOCK = threading.Lock()

def record(run, covered):
    """... SERIALISED, because the whole point of this file is that sixteen batches run AT ONCE
    and each one reports its own coverage. The first version did an unguarded read-modify-write
    ... The lock covers this process; the atomic land covers a torn read."""
    with _RECORD_LOCK:
        try:
            with open(COVERAGE, encoding="utf-8") as f:
                data = json.load(f)
        except Exception:
            data = {}
        ...
        for m in covered:
            data[m] = {"run": run, "at": now}
        silence.write_json(COVERAGE, data, indent=1, sort_keys=True)   # (or manual fallback)
        return data
```
`_RECORD_LOCK` is a `threading.Lock`, created fresh per **process** at import time. The 16 (or N)
sweep batches this run's own supervisor spawns via the `Agent` tool are separate OS processes,
each importing `sweep_plan.py` independently and getting **its own, unrelated** `_RECORD_LOCK`
object — the lock provides zero mutual exclusion between them. `silence.write_json()`'s
PID+thread-qualified temp name (confirmed by reading `silence.py:262-287`) genuinely closes the
*torn-read* hazard (no reader ever sees a half-written file) — the docstring's second sentence is
accurate. But the *read-modify-write cycle itself* — read `COVERAGE`, merge in Python, write it
back — spans two separate file operations with an unprotected gap between them, and nothing in
this function (or anywhere else in the module) serializes that gap across processes.

**Reproduced empirically this session**, with two real, independent OS processes (not threads)
sharing one coverage file, deterministically sequenced with a signal-file handshake so process A's
read happens strictly before process B's complete `record()` call, and A's write happens strictly
after:
```
A: wrote ['mod_a1.py', 'mod_a2.py']
B: record() returned
--- resulting shared coverage file ---
{
 "mod_a1.py": {"run": "raceRun", "at": ...},
 "mod_a2.py": {"run": "raceRun", "at": ...}
}
```
Process B's `record()` call returned normally (no exception, no error) after genuinely writing
`mod_b1.py`/`mod_b2.py` into its own read-modify-write cycle — but by the time process A's
(deliberately delayed) write landed, A's in-memory `data` was still based on the pre-B empty file,
so A's write **silently erased B's two modules from the shared file entirely**. This is not a
theoretical race — it is the literal failure mode a same-day, two-agent-process sweep run
produces, reproduced on this machine in this session.

**What `missing(run)` can and cannot prove, precisely, from this mechanism:**
- It **cannot fabricate false coverage**: an entry only appears in `COVERAGE.json` because some
  process's `covered` list genuinely named that module in a `record()` call that reached the
  write step. The race never invents an entry nobody wrote.
- It **can and does silently drop genuine coverage**: as reproduced above, a batch that
  *successfully* audited its modules and called `record()` without error can still have that
  work vanish from the shared file if a second process's stale write lands after it. `missing(run)`
  would then list those modules as **missing for that run, even though they were actually
  covered** — a false negative (falsely reports incompleteness), never a false positive (never
  falsely reports completeness for something nobody touched).
- Practical consequence: **a `missing(run)` result of "nothing missing" is trustworthy** — it can
  only be an undercount of what was recorded, so if it says every module IS accounted for, that's
  real. **A non-empty `missing(run)` result is NOT trustworthy on its own** — some or all of the
  listed modules may have been genuinely swept by a batch whose write was clobbered, and the only
  way to tell a real gap from a clobbered one is to check whether that module's `AUDIT_batchNN.md`
  report file actually exists on disk (exactly the corroboration NEXT_STEPS already recommends
  as this run's workaround).
**Severity: MAJOR** (this is the completeness proof for the entire comprehensive-audit
methodology this run and every future run relies on). **VERIFIED — reproduced empirically.**
This exact item is already flagged in `NEXT_STEPS.md` §3 as **KNOWN** at a code-reading level;
this run adds the empirical reproduction and the precise can/cannot-prove characterization above.

### SP2. `modules()` / `batches()` — checked, correct [no finding]
**`sweep_plan.py:35-78`**. The unreadable-file handling (`:47-60`) correctly marks a file as
`{"unreadable": True, "lines": 0}` rather than silently dropping it (with its own comment noting
this was itself a self-inflicted near-miss found by a prior sweep run auditing this file). Greedy
longest-first bin-packing (`:65-78`) is a reasonable balancing heuristic and drops no module —
every module in `modules()`'s output is guaranteed to land in exactly one bin since the loop
appends every module once. **No findings.**

### SP3. `missing()` — read-only, correctly implemented for what it does [no finding beyond SP1's scope]
**`sweep_plan.py:116-125`**. Straightforward diff against the live `modules()` list and the
coverage file; no caps, no swallowed exceptions that change behavior (an unreadable/missing
coverage file correctly degrades to "everything missing" via `data = {}`, which is the safe
direction). Its only real weakness is entirely inherited from `record()`'s race (SP1) — the
function itself introduces nothing further.

---

## Summary of severities (this batch)

- MAJOR: 4 — `feats.py` F1 (dead fix), F3 (host-cache membership bug, confirmed live), C1
  (`completeness.py` threading/tmp-file race), `sweep_plan.py` SP1 (cross-process lost-update,
  reproduced empirically).
- MINOR: 1 — `feats.py` F4 (unlocked diagnostic counters).
- COSMETIC: 1 — `feats.py` F5 (stale `silence.note()` line tags).
- UNVERIFIED (magnitude only, mechanism confirmed): `feats.py` F2 (cap-binding frequency —
  no live network run performed this session).
- Carried forward from prior sweeps / NEXT_STEPS with re-confirmation only, no new content:
  F1, F4, F5, C1, FI1, T1.
- New this run: F3's live-data confirmation (7 null `WIKI_HOSTS.json` entries), and SP1's full
  empirical reproduction with precise can/cannot-prove characterization of `missing()`.

**Modules read end to end and found CLEAN this run:** `tiers.py` (re-confirmed CLEAN from
sweep24), and within `feats_index.py`/`sweep_plan.py`, all functions other than the ones named
above (`feats_for_source()`, `audit()` in `feats_index.py`; `modules()`, `batches()`, `missing()`
in `sweep_plan.py`) read correctly against their own docstrings.
