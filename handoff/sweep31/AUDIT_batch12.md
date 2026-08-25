# AUDIT — BATCH 12 (run31)

Modules: `src/overnight.py` (888 lines), `src/chain.py` (497), `src/identity.py` (423),
`src/backfill.py` (300), `src/tempus.py` (254), `src/propagation.py` (214), `src/catalog.py` (127).

Total lines read: **2,703** (every line of every file, in full — no sampling).

Read-only audit. No files were edited or run except read-only `cat`/`grep`/line inspections.

---

## FINDING 1 — `overnight.py:598-599` and `overnight.py:713-714` — the plant-wide interlock fails OPEN, silently, on ImportError

**Claim:** The escalation "HALT" check that gates the whole overnight run is wrapped in
`except ImportError: pass` with **no log line, no `silence.note`, nothing** — if `escalation.py`
cannot be imported, the interlock is skipped entirely and the supervisor proceeds as if the
library were clear.

```python
# line 595-599 (main(), before anything else runs)
try:
    import escalation as _ESC
    _ESC.assert_clear(os.path.basename(__file__))
except ImportError:
    pass

# line 710-714 (top of every cycle)
try:
    import escalation as _ESC
    _ESC.assert_clear("overnight.py cycle %d" % cycle)
except ImportError:
    pass
except Exception as e:
    log("  " + str(e).splitlines()[0])
    log("  The library is halted. Nothing further will start until a person rules on it.")
    break
```

**Why it is wrong:** This is not a hypothetical concern — this project's own `CLAUDE.md` (HARD
RULE -1, written 2026-08-25) states the exact incident this pattern reproduces: *"the gate that
should have prevented it had been DELETED... FAIL CLOSED — every layer answers 'I don't know'
with STOP... Silence must never authorise anything."* If `escalation.py` is ever deleted, fails
a syntax check (this repo's own `foreman.py --patch` self-patches modules unattended), or
otherwise raises `ModuleNotFoundError`/`ImportError` on import, this code takes the opposite of
the documented policy: it fails OPEN, and does so with zero record anywhere (not even a `log()`
line, let alone `silence.note`), so `ledger_report()` never surfaces it either. `escalation.py`
currently exists and imports cleanly, so this is latent, not firing today — but it is exactly the
failure mode the project's own postmortem exists to prevent, reintroduced at the two call sites
that are supposed to enforce it.

**Failure scenario:** `src/escalation.py` is deleted, renamed, or broken by an autopatch → both
try/excepts silently no-op → `overnight.py` runs a full unattended night with the OWNER-level halt
completely unenforced and no trace in any log that the check was skipped.

**Severity:** blocking. **Confidence:** high (direct code read; cross-referenced against the
project's own written policy in CLAUDE.md, which explicitly forbids fail-open/silent behavior at
exactly this layer).

---

## FINDING 2 — `identity.py:180-207` — the BRANCHING test contradicts its own docstring; the one-bearer case it advertises is mathematically unreachable

**Claim:** `_is_continuity()`'s branching test can never fire for a designator with exactly one
bearer, directly contradicting the worked example in its own docstring and the module's own
prose.

```python
def _is_continuity(desig, stat):
    ...
    n = stat["bearers"] if isinstance(stat, dict) else stat
    shared = stat.get("shared", 0) if isinstance(stat, dict) else 0
    if n >= MIN_BEARERS:          # MIN_BEARERS = 3
        return True
    return n >= 2 and shared >= max(2, 0.5 * n)
```

The docstring (lines 193-196) says: *"`(Fates)` has one bearer and is obviously a continuity
because that bearer exists in three other branches."* — an explicit n=1 example the branching test
is supposed to catch. But the code requires `n >= 2` before it even evaluates `shared`, and
`shared` is bounded above by `n` (it is a count of a subset of the `n` bearers), so for `n=1` the
function returns `False` unconditionally — the case never reaches the `shared` check at all. Worse,
even the reachable `n=2` case requires `shared >= max(2, 1) == 2`, i.e. **both** of the two bearers
must independently be shared elsewhere — a much stricter bar than "obviously a continuity" implies.
In practice this collapses the entire "BRANCHING is sufficient but not necessary" test (module
intro, lines 57-60) down to one narrow case: exactly 2 bearers, both shared elsewhere.

**Why this matters for correctness, not just prose:** the module's entire reason for existing is
the owner's ruling that continuities/timelines must never be merged (Kal-El New Earth vs Kal-El
Prime Earth). A single-bearer continuity designator that is provably a branch (its one name
occurs under other designators too) is silently classified as NOT a continuity and gets merged
into the base timeline — precisely the defect this module was built to prevent, on exactly the
input shape its own docstring uses as the motivating example.

**Failure scenario:** A young/rare continuity designator with exactly one written-up character,
whose name also appears under 3 other branch designators (the docstring's own `(Fates)` example)
→ `_is_continuity` returns `False` → `identify()` treats the parenthetical as noise and folds the
record into the base-name node → a real timeline split is silently merged.

**Severity:** major. **Confidence:** high (straightforward arithmetic trace; `shared <= n` is
structural, not incidental).

---

## FINDING 3 — `chain.py:354` — `unmatched` Counter mutated outside the thread lock inside `ThreadPoolExecutor` (data race)

**Claim:** `extract()` runs `work(chunk)` across up to 8 worker threads via
`ThreadPoolExecutor(max_workers=workers)` (line 367-368). Inside `work`, the shared
`collections.Counter` `unmatched` is incremented **outside** the `with lock:` block that protects
every other piece of shared state in the same function.

```python
# lines 351-364
            else:
                for side, k in ((w, wk), (l, lk)):
                    if k not in idx:
                        unmatched[side[:40]] += 1        # <-- line 354, NO LOCK HELD HERE
        with lock:
            done["n"] += len(chunk)
            done["pairs"] += len((got or {}).get("outcomes", []))
            for e, src in local:
                edges[e] += 1
                prov[e].append(src)
                done["kept"] += 1
```

**Why it is wrong:** `Counter.__getitem__`/`__setitem__` for `counter[key] += 1` is a
read-modify-write sequence, not a single atomic bytecode op. With multiple threads hitting the
same key concurrently and no lock, increments can be lost (classic lost-update race): thread A
reads 4, thread B reads 4, both write 5 — one increment vanishes. `edges`, `prov`, and `done` are
correctly protected by acquiring `lock` first; `unmatched` is the one piece of shared state that
is not, in the same function, written by the same threads.

**Concrete consequence:** `unmatched` is not purely cosmetic — `write_result()` (line 108) writes
`unmatched.most_common(40)` straight into the persisted `data/CHAIN.json`, and `main()` prints it
as "most common names that match nothing the library catalogues" (lines 455-458), which is the
signal used to spot systematic entity-index gaps. Under race conditions this count silently
undercounts.

**Severity:** major. **Confidence:** high (direct code read; this is the file:line the batch
brief flagged as a known-open concurrency instance — verified present and reproduced the specific
mechanism). No sibling of this exact "shared Counter written outside the lock inside the same
threaded function" pattern was found elsewhere in these 7 modules — it appears to be the only
instance in this batch.

---

## FINDING 4 — `identity.py:210-223` — `load()`'s cache write uses a fixed (non-unique) temp filename, not `silence.write_json`; reopens a bug class the project explicitly fixed elsewhere

**Claim:** `identity.load()` persists `data/DESIGNATORS.json` by hand-rolling a temp file with a
**fixed name** (`CACHE + ".tmp"`) and `silence.replace_retry`, rather than calling
`silence.write_json` (which exists specifically to give every writer of a shared file a
PID+thread-unique temp name).

```python
def load(refresh=False):
    if not refresh and os.path.exists(CACHE):
        try:
            with open(CACHE, encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            silence.note("identity.py:load")
    inv = mine()
    os.makedirs(os.path.dirname(CACHE), exist_ok=True)
    tmp = CACHE + ".tmp"                       # <-- fixed name, not unique per writer
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(inv, f, indent=1, sort_keys=True)
    silence.replace_retry(tmp, CACHE)          # return value also unchecked
    return inv
```

`silence.write_json`'s own docstring (`silence.py:290-309`) documents this exact defect class as
having been found and fixed at "TWELVE call sites across ten modules" project-wide, precisely
*because* a fixed temp name lets "two writers of the same path... collide on the temp file
itself, and the loser can replace the winner's target with a partial file." `chain.py`'s own
`write_result()` and `harvest()` both carry comments noting they were migrated to
`silence.write_json` for this reason ("chain.py's two were missed [from the twelve], run #26").
`identity.py:219` is a grep-confirmed **remaining** hand-rolled `+".tmp"` site in this batch (the
only other one in these 7 files was the chain.py pair, already fixed) — it was not part of that
sweep.

**Concrete failure scenario:** `identity.load(refresh=True)` (via `identity.py --refresh`) runs
at the same moment `chain.py harvest()` calls `ID.load()` and independently decides to rebuild
(cache missing/corrupt) — both processes `open(CACHE + ".tmp", "w")` on the *same path*; one
process's write can be interleaved/truncated by the other's truncating open, and whichever
`os.replace` lands second installs whatever ended up in the shared temp file, which may be a
torn/corrupted JSON blob. The next reader's `json.load` then raises, is caught, and the cache
rebuilds — so this is self-healing on the next read (unlike a genuinely permanent corruption),
but it is a live instance of the exact race class the project paid down elsewhere, and a return
value (`silence.replace_retry`'s bool) that is silently discarded, unlike every other writer in
these 7 files that checks it (`chain.py:120-123` and `chain.py:200-204` both gate on the return
value and log on denial; `identity.py:222` does not).

**Severity:** major (self-healing, but a confirmed-open instance of a bug class the project
otherwise treats as serious enough to fix at 12+ sites). **Confidence:** high.

---

## FINDING 5 — `overnight.py:617-639` — the keeper thread and the main cycle loop both call `start()` for the STANDING jobs with no mutex between them; the docstring's "can never double" claim is not actually enforced

**Claim:** A background daemon thread (`_keep`, started at line 639) re-asserts the STANDING jobs
every 5 minutes by calling `running(...)` then `start(...)`. The main cycle loop *also* calls
`start()` for the same jobs (dashboard/publish/foreman/overwatch/pipeline, lines 740-772) once per
lap. Both paths execute in the same process on separate threads, and the check-then-act sequence
(`running()` → decide → `subprocess.Popen()`) is not wrapped in any lock shared between the two
call sites.

```python
# line 622-623 (comment, asserting a guarantee)
# guard, so the keeper can never double anything.
```

**Why it is wrong:** `running()` reads a TTL-cached process snapshot (`_proc_lines`, 3s TTL) and
returns a boolean; nothing stops a second thread from performing the same check and reaching the
same "not running" conclusion inside that same TTL window, then both calling `Popen()`. The
`_PROCS_LOCK` in `_proc_lines()` only serializes the *cache refresh*, not the
check-then-launch decision as a whole — it prevents two threads from re-running the PowerShell
probe simultaneously, it does not prevent two threads from both deciding "not running, launch it."
The comment's claim that "the keeper can never double anything" is therefore not actually
guaranteed by the code — it happens to be true in the common case because the keeper only acts
every 5 minutes and the main loop's `start()` calls happen once at the very top of an
hours-long cycle, so the overlap window is narrow, but nothing in the code enforces it.

**Failure scenario:** the keeper thread's 5-minute tick lands within a few seconds of the main
loop reaching the top of a new cycle (both racing to check the same STANDING job at nearly the
same moment) → both see "not running" from the shared 3-second-stale cache → both call
`subprocess.Popen()` → two copies of e.g. `dashboard.py --port 8777` are launched, one of which
will then fail to bind the port (or, for `foreman.py --patch`, two self-patching processes racing
on the same file).

**Severity:** major (comment/code contradiction on a safety-relevant claim; narrow but real race
window). **Confidence:** medium (the race is real and provable from the code; I did not observe
it occur, and the timing window is genuinely narrow in practice).

---

## FINDING 6 — `identity.py:291-320` — a transport failure during epoch resolution is indistinguishable from a genuine "no epoch marker" answer

**Claim:** `_ask()` catches every exception (network/transport failures included) and returns
`None`; `epoch_of()` then treats that `None` identically to a well-formed model answer that
explicitly said "no epoch marker in this sentence."

```python
def _ask(prompt, system=EPOCH_SYSTEM):
    try:
        import read as R
        R.ensure_transport(verbose=False)
        return R._ask(R.config(), system, prompt, EPOCH_SCHEMA)
    except Exception:
        silence.note("identity.py:_ask")
        return None

def epoch_of(sentence):
    d = _json(_ask(sentence.strip()[:1200]))
    if not d.get("explicit"):
        return ""
    return str(d.get("epoch") or "").strip()[:60]
```

`_json(None)` → `raw or ""` → `""` → no `{...}` match → `{}` → `d.get("explicit")` is `None` →
falsy → `epoch_of` returns `""`, the exact same value it returns when the model legitimately says
"this sentence carries no epoch marker." This is the "transport failure cached forever as a
verified absence" pattern named in the sweep brief, applied to a single call rather than a
persisted cache — a network hiccup during `chain.adjudicate_mutuals()` (the sole caller,
`chain.py:408`) makes a mutual contest pair look like "neither sentence dates itself" (a genuine
disagreement, left standing) when the real answer is unknown. It is self-healing across separate
runs (a fresh `chain.py` invocation re-harvests and re-asks), but within one run there is no
retry and no way to tell "the model said no" from "the call never happened."

**Severity:** major. **Confidence:** high (direct code trace).

---

## FINDING 7 — `propagation.py:155-158` — dead/unreachable fallback in `observed_mark()`

```python
for rung in range(LADDER_HEIGHT, 0, -1):
    if lag >= ascension_years(rung):
        return rung
return 0
```

**Claim:** the trailing `return 0` can never execute given the current constants.
`ascension_years(1) == round(1.0**1.35 - 1.0, 1) == 0.0`, and the loop is only reached when
`lag >= 0` (the `lag < 0` case already returned above it, line 153-154). So when the loop reaches
`rung == 1`, `lag >= 0.0` is always true, and the loop always returns by then. The final
`return 0` is dead code under `RUNG_COST_EXPONENT = 1.35`. Not a functional bug today (the
semantics — "rung 1 ratifies in zero years, so any arrived news is at least rung 1" — are
mathematically self-consistent), but it is exactly the "check that cannot fail" shape the lens
calls out, and it would silently stop being dead if `RUNG_COST_EXPONENT` or `LADDER_HEIGHT` ever
changed such that `ascension_years(1) > 0`.

**Severity:** cosmetic/minor. **Confidence:** high.

---

## FINDING 8 (grouped, minor) — display-only truncations that are literal Hard-Rule-0-shaped patterns but do not shrink any written record

Per the letter of Hard Rule 0 ("ANY cap... `[:N]`... that makes the universe smaller than it
really is") these are flagged, but in every case checked here the underlying authoritative data
(what lands in `data/*.json` or the catalog) is written in full — only a terminal/log line is
shortened. Listed for completeness / in case reviewers judge the letter of the rule differently
than I did:

- `catalog.py:64` — `for n in missing[:30]:` in `cmd_stats` (CLI stdout only; the full `missing`
  list length is printed above it, only the enumeration is capped).
- `backfill.py:264` — `for x in rows[:26]:` in the `--audit` report print (the `--all` repair
  path uses the *full* `audit()` list, unaffected).
- `backfill.py:126-153` — `lead(wikitext, chars=420)` truncates each backfilled character's
  *description field* to ~420 characters. This does not shrink the roster (every character is
  still enumerated and written per Hard Rule 0's roster/list language), but it is a hard cap on
  a per-record text field; flagged as lower-confidence since a "lead paragraph" is arguably
  definitionally short by design, not a truncation of "the universe."
- `identity.py:317` — `sentence.strip()[:1200]` truncates the sentence text sent to the epoch
  model call; could in principle cut off a late epoch marker in an unusually long sentence.
- `identity.py:320` — `str(d.get("epoch") or "").strip()[:60]` truncates the returned epoch
  phrase (the prompt already asks for "six words at most," so this is a defensive floor more than
  an active truncation).
- `identity.py:365` / `identity.py:352` — `top[:6]` and implicit similar slices in `main()`'s
  console report (report display only; `continuities()` itself returns the full unsliced dict).
- `chain.py:354` — `unmatched[side[:40]]` (diagnostic Counter key truncation; see Finding 3 for
  the concurrency issue on the same line).
- `chain.py:457`, `chain.py:488` — `unmatched.most_common(8)`, `[...][:14]` in `main()`'s console
  summary only; `write_result()` persists the untruncated `edges`/`strengths`/`unmatched(40)` to
  `CHAIN.json` (line 108's `.most_common(40)` is itself a cap on the *persisted* file, worth
  noting separately — 40 is generous but is still a hard ceiling on how many distinct unmatched
  names get recorded to disk).
- `overnight.py:335`, `overnight.py:363`, `overnight.py:382-385`, `overnight.py:486` —
  `[:70]`/`[:96]`/`top=6`/`top=8`/`lines[-n:]` truncations, all in supervisor-log lines only
  (`WATCH.md` and `state/failures.json` — the underlying full records — are written by other
  modules, not truncated here).

**Severity (whole group): minor/cosmetic.** **Confidence:** high that these exist as literal
`[:N]`/`most_common(N)`/`top=N` patterns; low-to-medium confidence that any of them constitute a
real violation of the rule's intent, since in every case I traced, the *written* record (catalog,
CHAIN.json, DESIGNATORS.json) is unaffected — the one partial exception is `chain.py:108`'s
`.most_common(40)` into `CHAIN.json` itself, which is a cap on a persisted file's contents.

---

## Two-writer contract — compliant items checked

- `chain.py:write_result()` → `silence.write_json` (compliant, migrated per its own comment).
- `chain.py:harvest()` index write → `silence.write_json` (compliant, same comment).
- `identity.py:load()` → `silence.replace_retry` but with a **non-unique temp name** — see
  Finding 4 (partial compliance; the atomic-rename half is present, the unique-temp-name half is
  not).
- `backfill.py:backfill_source()` → `pipeline.write_record_catalogue(path, r)`, gated on its
  return value (compliant, correctly checks the write landed before reporting success).
- `catalog.py` — read-only tool, never writes records or state; not applicable.
- `propagation.py`, `tempus.py` — read-only/computational, no shared-file writes at all.

## Comment/docstring-vs-code contradictions found

- Finding 2 (identity.py `_is_continuity`) — docstring's own worked example (`(Fates)`, one
  bearer) is unreachable by the code it documents.
- Finding 5 (overnight.py `_keep`) — inline comment claims a guarantee ("the keeper can never
  double anything") the code does not actually enforce.

## Things checked and ruled OUT as false leads

- `overnight.py:preflight()`'s `"FAIL  control" in out` string match — verified against
  `health.py`'s actual `print(f"  FAIL  {label}")` output; the two spaces line up correctly, this
  is not a silently-never-matching regex/string check.
- `tempus.py:band_resolution()`'s `LADDER[i-1]` fallback for the top-of-Ladder case — confirmed
  `LADDER` has 11 entries (`assay.py:105`), so `i-1` is only reached at `i==10`, never `i==-1`; no
  out-of-bounds/wraparound bug.
- `catalog.py`'s `total_raw / max(total_compressed, 1)` and `coverage_snapshot()`'s
  `max(n, 1)` denominators — legitimate divide-by-zero floors, not tautological "checks that
  cannot fail."
- `chain.py:adjudicate_mutuals()`'s `out.pop((x, y))` (no default) — traced whether two distinct
  mutual pairs could ever share a popped key (which would raise `KeyError` on the second); ruled
  out because `mutual` is built from unique node-pair keys in a dict, so no pair is processed
  twice.
