# AUDIT — batch 13

Modules: `overwatch.py`, `handbuilt.py`, `health.py`, `scout.py`, `genre.py`, `profile.py`,
`lognames.py`. Every file read in full, top to bottom. Findings below are grouped by severity
within each module; a per-module CLEAN line is given where nothing survived scrutiny.

Total: **3 HIGH, 7 MEDIUM, 5 LOW**.

---

## HIGH

### `overwatch.py:330-343` and `overwatch.py:524-563` — a structural-check crash is silently reported as "clean"

```python
    try:
        import allsweep as A
        ...
    except Exception as e:
        silence.note("overwatch.py:193")
        out["error"] = f"{type(e).__name__}: {str(e)[:90]}"
    if not deep:
        return out
    try:
        import estate as E
        art = E.artifacts(workers=8)
        out["corrupt_files"] = [...]
        out["files"] = art["total"]
    except Exception as e:
        silence.note("overwatch.py:202")
        out["estate_error"] = f"{type(e).__name__}: {str(e)[:90]}"
```

`structure()` catches any exception from `allsweep`/`estate` and records it in `out["error"]` /
`out["estate_error"]`. Grepped the whole file: **neither key is ever read again.**
`write_report()` (lines 524-563) only consults `struct.get("broken_modules")`,
`struct.get("corrupt_files")`, `struct.get("files")`, and `struct.get("reconcile")`. Nothing in
`write_report` or `main()` prints `error`/`estate_error`.

Effect: if `allsweep` fails to import (a real break — this is literally the check that "caught
four dead modules" per this file's own docstring) or `estate.artifacts()` throws, `structure()`
returns a dict with no `broken_modules`/`corrupt_files` keys at all, and `write_report` renders:

```
- modules that will not import: **0**
- files that will not parse: **0** of 0 inspected
```

That reads as "everything imports and every file parses" when the truth is "the checker itself
crashed and nothing was measured." This is precisely the failure mode the file's own docstring
calls out as the point of overwatch's existence — a fault "detectable by a measurement nobody
was taking," except here overwatch takes the measurement and then throws it away.

**VERIFIED.** Suggested repair: surface `struct.get("error")`/`struct.get("estate_error")` as a
loud line in `write_report`, e.g. `- STRUCTURE CHECK FAILED: <error>` before the counts, so a
crash cannot present as a clean bill of health.

---

### `overwatch.py:326-329` — the reconcile filter silently drops most real findings, including every internal exception from `allsweep.reconcile()`

```python
        out["reconcile"] = [r for r in A.reconcile()
                            if r["finding"].isupper() or "no host" in r["finding"]
                            or "never catalogued" in r["finding"]
                            or "MORE THAN ONE" in r["finding"]]
```

Tested this filter against every `kind` string `allsweep.reconcile()` actually emits
(`src/allsweep.py:161-318`):

```
DROP  hosts for sources with no catalogue record
KEEP  catalogued sources with no host
KEEP  on the roll but never catalogued
DROP  source reconciliation failed
DROP  coverage says CITED
DROP  readfeats records holding text
DROP  COVERAGE.json is stale
DROP  coverage reconciliation failed
DROP  cache directories no source points to
DROP  cache reconciliation failed
DROP  purged sources that still carry entries
DROP  purge reconciliation failed
DROP  phases implemented
KEEP  PHASES NAMED BY THE RUNNER WITH NO IMPLEMENTATION
DROP  phase reconciliation failed
KEEP  ENTRIES BANDED ABOVE THEIR OWN SOURCE'S CEILING
DROP  band reconciliation failed
KEEP  MORE THAN ONE INSTANCE RUNNING
DROP  running
KEEP  NOT RUNNING
DROP  process check failed
```

Two distinct problems fall out of this:

1. **Every one of `allsweep.reconcile()`'s own internal `except` blocks** (`source
   reconciliation failed`, `coverage reconciliation failed`, `cache reconciliation failed`,
   `purge reconciliation failed`, `phase reconciliation failed`, `band reconciliation failed`,
   `process check failed` — one per reconcile sub-check) is swallowed a **second time** by this
   filter. If any of those six independent try/except blocks in `allsweep.py` catches an
   exception, `allsweep.reconcile()` faithfully records it as a finding — and `overwatch.py`
   then throws it away before it ever reaches `WATCH.md`, because none of those strings are
   `.isupper()` or match the three substrings. A subsystem crash inside reconcile is completely
   invisible to a human reading the report.
2. Several **legitimate, non-exceptional** reconcile findings are dropped for the same reason:
   orphan hosts (`hosts for sources with no catalogue record`), a stale coverage snapshot
   (`COVERAGE.json is stale`), stale cache directories (`cache directories no source points
   to`), and ghost entries from purged sources (`purged sources that still carry entries`). All
   four are exactly the class of "subsystems disagree" fact `reconcile()`'s own docstring says
   is worth surfacing — they simply don't happen to be spelled in upper case or contain one of
   the three magic substrings.

**VERIFIED** (tested the exact filter expression against the exact strings `allsweep.py` emits).
Suggested repair: the filter should be built from an explicit allow/deny list keyed on intent
(e.g. every `"* reconciliation failed"` / `"process check failed"` entry should always pass —
those ARE the self-check failures this file exists to surface), not from surface typography.

---

### `health.py:124-144` — `flush()`'s evidence-bag write ends in a bare `except: pass` with **no** logging, in the one file whose entire purpose is "no silent failures"

```python
    if _SAMPLES:
        try:
            old = {}
            if os.path.exists(SAMPLES_PATH):
                with open(SAMPLES_PATH, encoding="utf-8") as f:
                    old = json.load(f)
            for k, ring in _SAMPLES.items():
                merged = (old.get(k) or []) + ring
                old[k] = merged[-SAMPLES_KEEP:]
            # Same treatment, and this file needs it MORE than the ledger does, not less: it
            # has no .corrupt self-healing path. Once torn, every future flush hits the blanket
            # `except` below at the read step and drops its samples silently and permanently --
            # the evidence bag going quietly empty and staying that way, with nothing recorded
            # anywhere, because the recorder cannot safely record against itself.
            stmp = SAMPLES_PATH + ".tmp"
            with open(stmp, "w", encoding="utf-8") as f:
                json.dump(old, f, indent=1, sort_keys=True, ensure_ascii=False)
            if silence.replace_retry(stmp, SAMPLES_PATH):
                _SAMPLES.clear()
        except Exception:
            pass          # the evidence bag must never break the ledger write
```

Every other exception handler in this file either calls `silence.note(...)` or prints to
`stderr` (see the ledger's own corrupt-read branch a few lines above, lines 90-101, which does
both). This one does neither. The block comment directly above it **documents the exact failure
this leaves open**: a torn `SAMPLES_PATH` makes every future flush hit this `except` and "drop
its samples silently and permanently... with nothing recorded anywhere." That is not a
hypothetical — it is the comment's own description of what the code beneath it does, in the
module whose stated mission (docstring, lines 1-35) is turning exactly this shape of bug into a
loud one. `check_control_chars`, the whole preflight apparatus, and the ledger's own
`.corrupt`-preservation path all exist to stop this pattern; this five-line `except` reintroduces
it inside the failure-recorder itself.

**VERIFIED.** Suggested repair: at minimum, `silence.note("health.py:flush-samples")` and a
`print(..., file=sys.stderr)` line matching the ledger branch's treatment, so a torn samples file
shows up somewhere instead of nowhere.

---

## MEDIUM

### `overwatch.py:486` — `verify_open()` marks a finding "just re-verified" even when the model call failed

```python
        got = _ask(VERIFY_SYSTEM, prompt, VERIFY_SCHEMA, local=local)
        f["last_verified"] = time.time()
        checked += 1
        verdict = (got or {}).get("verdict")
        why = str((got or {}).get("why") or "")[:300]
        if verdict == "refuted":
            ...
        elif verdict == "confirmed":
            ...
```

`_ask` returns `None` on a genuine failure (GPU busy past `CLOUD_BUDGET`, a malformed/rejected
model reply, a transport exception inside `R._ask`). When that happens, `verdict` is `None`,
which correctly avoids the `refuted` branch (so this does not, by itself, close a real finding —
the specific risk the task asked to check), but `f["last_verified"]` is stamped with the current
time and `checked` is incremented regardless, exactly as if a real judgment had been rendered.
Since `rotation`'s/`verify_open`'s own sort key is
`f.get("last_verified", f.get("first_seen", 0))` (oldest first), a finding that merely *failed*
to get checked is pushed to the back of the re-verification queue — it will not be looked at
again until every other open finding has had a turn, even though nothing was actually learned
about it this round. The printed summary ("N open finding(s) re-verified, M refuted") also
overstates how many findings were genuinely judged.

**VERIFIED.** Suggested repair: only set `last_verified` (and increment `checked`) inside the
branch where `got` is not `None`.

---

### `health.py:85-144` — `flush()` mutates the shared `LEDGER` Counter without the lock that `record()` uses

```python
LEDGER = collections.Counter()
_LOCK = threading.Lock()
...
def record(kind, detail="", sample=None):
    with _LOCK:
        key = f"{kind}:{detail}" if detail else kind
        LEDGER[key] += 1
        ...

def flush():
    if not LEDGER:
        return
    ...
    for k, v in LEDGER.items():        # line 102 — no _LOCK held
        prev[k] = prev.get(k, 0) + v
    ...
    if silence.replace_retry(tmp, LEDGER_PATH):
        LEDGER.clear()                 # line 123 — no _LOCK held
```

`record()` is careful to hold `_LOCK` around every mutation of `LEDGER`. `flush()` iterates and
then clears the same dict without ever acquiring it. `silence.note()` calls `health.record()`
from arbitrary call sites across the tree (any `except` block anywhere `--instrument` rewrote)
and, every 25 calls, triggers `health.flush()` from that same call path (`silence.py:277-280`) —
so if two threads are both hitting instrumented `except` blocks around the 25-call boundary, one
can be inside `flush()`'s `for k, v in LEDGER.items()` while another concurrently does
`LEDGER[key] += 1` in `record()`. Two distinct bad outcomes follow: (a) if the concurrent
`record()` call adds a *new* key, Python raises `RuntimeError: dictionary changed size during
iteration` inside `flush()` — which then gets swallowed by `note()`'s own outer `except
Exception: pass` (`silence.py:281-282`), so the crash itself vanishes silently; (b) if a
`record()` call lands in the gap between the `for` loop finishing and `LEDGER.clear()` running,
that increment is added to `LEDGER` and then immediately discarded by `.clear()` without ever
reaching `prev`/disk — a straightforward lost update.

**VERIFIED** (race exists on paper; triggering it live requires the right interleaving, so
severity is capped at MEDIUM rather than HIGH — but note the irony that a `RuntimeError` this
race can throw is invisible by construction, given how `note()` is wired).

Suggested repair: hold `_LOCK` for the iterate-and-clear in `flush()` too (snapshot LEDGER under
the lock, e.g. `with _LOCK: snap, LEDGER = dict(LEDGER), collections.Counter()`, then work from
`snap` unlocked).

---

### `scout.py:162-165` — a transient network failure is mislabeled as "the URL was invented," contradicting the function's own documented 3-way distinction

```python
    except urllib.error.HTTPError as e:
        silence.note("scout.py:verify-http")
        kind = "exists but declines readers" if e.code in (401, 403, 429) else f"HTTP {e.code}"
        return {"url": url, "ok": False, "why": kind, "code": e.code}
    except Exception as e:
        silence.note("scout.py:verify")
        return {"url": url, "ok": False, "why": "no such host or no route",
                "code": type(e).__name__}
```

`verify()`'s own docstring (lines 139-149) is explicit that three failure shapes must be told
apart, and that "no such host" means "the URL was invented... do not try it again." But the
`except Exception` catch-all is not restricted to DNS/connection failures — it also catches
`socket.timeout`, `TimeoutError`, `ssl.SSLError`, `ConnectionResetError`, and anything else
`urllib.request.urlopen` can raise that isn't an `HTTPError`. A page that is genuinely real but
timed out (slow homebrew site, transient network blip) gets exactly the same `"why": "no such
host or no route"` text as a fully hallucinated URL, even though the docstring's own taxonomy
says these deserve opposite treatment ("nothing to do; do not try it again" vs. a page that is
in fact there). The raw exception class name does survive in `"code"`, so the fact isn't
unrecoverable from the JSON log — but the human-facing `why` field, and the `sweep()` printout
built from it (`scout.py:253`), actively mischaracterize a transient failure as a durable
negative.

**VERIFIED.** Suggested repair: catch `TimeoutError`/`socket.timeout` (and similar) separately
and label them e.g. `"timed out (may be real; not yet proven)"` rather than folding them into
the "invented" bucket.

---

### `scout.py:200-204` — read-modify-write race on `WIKI_HOSTS.json`, one of (at least) three uncoordinated writers

```python
        try:
            import feats as F
            hosts = json.load(open(F.HOSTS, encoding="utf-8"))
            hosts[source] = "pages:" + source
            _land(F.HOSTS, hosts)
        except Exception:
            silence.note("scout.py:register-host")
```

`_land()` (line 55-65) does the tmp-file + `silence.replace_retry` dance correctly, which
protects against a *torn* write. It does not protect against a *stale* one: this reads the whole
`WIKI_HOSTS.json`, adds one key in memory, and replaces the whole file. `hostcheck.py` itself
documents (`hostcheck.py:582-589`) that this exact file "is written from THREE call sites in two
modules (this function, `adopt()` below, and `scout.py`'s host registration)" and is read by
several long-running processes — but that comment only addresses the torn-write problem the
same way `_land`/`replace_retry` do; none of the three call sites re-reads-and-merges before
writing. If two of the three writers run in the same window (plausible: `scout.py --dry`/sweeps
and `hostcheck.py --adopt` are both meant to run unattended), the second writer's whole-file
replace silently discards whatever key(s) the first writer added in between — the identical
failure shape `overwatch.py`'s own ledger explicitly solved for itself via
`_merge_ledgers`/`_reconcile_with_disk` (see `overwatch.py:236-304`), just not applied here.

**VERIFIED** as a structural race (the read-then-write-whole-file pattern is present in the code
as quoted); whether it fires in a given run depends on scheduling overlap between scout.py and
hostcheck.py, hence MEDIUM not HIGH.

Suggested repair: give `WIKI_HOSTS.json` the same reconcile-before-write treatment
`overwatch.py`'s ledger has, or serialize the three writers behind a lock file.

---

### `genre.py:234-238` — `data/GENRES.json` is written with a bare `open(path, "w")`, not the project's two-writer pattern

```python
    if args.write:
        p = os.path.join(HERE, "data", "GENRES.json")
        with open(p, "w", encoding="utf-8") as f:
            json.dump(out, f, indent=2, ensure_ascii=False)
        print(f"\nwrote {p}")
```

Every other shared-data write touched by this batch (`overwatch.py`'s ledger,
`handbuilt.py`'s `HANDBUILT_ASSAYS.json`, `health.py`'s `failures.json`/`failure_samples.json`,
`scout.py`'s `SCOUT.json`/`SCOUT_BLOCKED.json`/`WIKI_HOSTS.json`) goes through a
`tmp` file + `silence.replace_retry`. `GENRES.json` is read downstream by
`profile.py:build_all()` (`genres = json.load(open(os.path.join(HERE, "data",
"GENRES.json")...))`) and is described in this very file's own docstring as feeding
`onomast.py`/`worldseed.py`. A process killed mid-`json.dump` (this file is written once per
`--write` run over the whole records set, so the window is not tiny) truncates it to whatever
was flushed, and any reader that opens it in that window gets a `json.JSONDecodeError`.
`profile.py` happens to catch that specific case defensively (`except Exception: silence.note(...);
genres = {}`), which masks the corruption as "no source classified" rather than surfacing the
truncated write — but the root cause, a non-atomic write on a shared data file, is in this
function.

**VERIFIED** (two-writer contract violation, item #4 of the audit brief).

---

### `profile.py:52` — the Crockford-alphabet comment is wrong, and the alphabet it describes has one more symbol than a real base-32 codec, with a live decode-corruption edge case

```python
B32 = "0123456789abcdefghjkmnpqrstuvwxyz"      # Crockford-style: no i, l, o, u
```

Counted the string directly: it is 33 characters (10 digits + 23 letters), and the only letters
actually missing from a-z are `i`, `l`, `o` — `'u'` **is present** (`...rstuvwxyz`). The comment
claims four exclusions; the code has three. True Crockford Base32 has exactly 32 symbols
(0-9 + 22 letters, excluding I/L/O/U) so that each symbol maps to exactly 5 bits; this alphabet
has 33.

Consequence: `_b32()` (lines 69-76) extracts nibbles with `n & 31`, which can only ever
produce indices 0-31 — so the 33rd character, `B32[32]` = `'z'`, is **unreachable dead output**
from `encode()`; nothing this codebase emits will ever contain `'z'` in an address segment,
which is why the round-trip self-test in `main()` never notices. But `_unb32()`/`decode()`
(lines 79-83, 94-99) accepts input via a regex that is *not* restricted to this alphabet
(`r"PS-([0-9a-z]+)-..."` — any lowercase letter, not just B32's own symbols) and calls
`B32.index(ch)`, which happily returns `32` for `'z'`. `(n << 5) | 32` then ORs a 6-bit value
into what the rest of the loop treats as a 5-bit field, silently corrupting the reconstructed
address integer (rather than raising) for any externally-supplied or hand-edited profile string
that happens to contain a `'z'` in its address portion.

**VERIFIED** (comment-vs-code mismatch confirmed by direct count; the dead-symbol/decode-
corruption consequence is a real but currently-dormant edge case, hence MEDIUM not HIGH — no
live code path in this batch ever constructs a `'z'`-bearing address).

Suggested repair: fix the comment (only i/l/o excluded), and either drop `'z'` from the alphabet
to make it truly 32 symbols, or validate `decode()`'s regex against the real alphabet so a stray
`'z'` raises instead of corrupting.

---

### `lognames.py:1-8` — the module's central claim ("a constant shared by writer and reader cannot drift") is contradicted by two of its own six constants

```python
"""LOGNAMES — the one place a job's log file is named.

The dashboard's Jobs panel, the `corpus read is progressing` standard, the stall detector and
the foreman's restart remedy are all keyed on these filenames. They used to be string literals
repeated in overnight.py and dashboard.py independently — one rename in one place and the whole
observability chain went quietly blind: panel empty, standard vacuously green, remedy never
firing. A constant shared by writer and reader cannot drift.
"""
...
PIPELINE = "pipeline_auto.log"  # the phase runner, when the supervisor drives it
...
RECATALOGUE = "recatalogue.log"  # catalogue_web --recatalogue, foreman-dispatched
```

Grepped every use of these filenames across `src/`. `overnight.py` imports `lognames as LN` and
correctly uses `LN.ROLL` / `LN.READ` (lines 647, 659) — but hardcodes the literal string
`"pipeline_auto.log"` four separate times instead (`overnight.py:379` in the `STANDING` table,
`overnight.py:479` in a written report string, `overnight.py:636` and `:665` in two `start()`/
`run()` calls), never once referencing `LN.PIPELINE`. `foreman.py` imports `lognames` in three
places and correctly uses `LN.SWEEP`/`LN.CALIBRATE` (`foreman.py:608, 665`) — but hardcodes the
literal `"recatalogue.log"` at `foreman.py:594` instead of `LN.RECATALOGUE`. Confirmed with a
whole-tree grep: `LN.PIPELINE` / `LN.RECATALOGUE` / `lognames.PIPELINE` /
`lognames.RECATALOGUE` do not appear **anywhere** — both constants are defined and dead, while
their string values are duplicated independently at exactly the call sites the docstring says
this file was built to unify. If either filename is ever renamed here, `PIPELINE`/`RECATALOGUE`
change and the four/one call sites above silently keep writing to and reading from the old name
— the exact "panel empty, standard vacuously green, remedy never firing" failure this file's own
docstring describes as fixed.

**VERIFIED** (cross-file grep confirms both the dead constants and the live hardcoded
duplicates). This is a finding about `lognames.py`'s documented guarantee not holding in
practice; the repair belongs in `overnight.py`/`foreman.py` (swap the four/one literals for
`LN.PIPELINE`/`LN.RECATALOGUE`), which are outside this batch's assignment but are named here
because the contradiction is with this file's stated purpose.

---

## LOW

### `overwatch.py:598-604` — a finding against a *deleted* module never retires

```python
    for fid, f in list(led["findings"].items()):
        if f.get("state") != "open":
            continue
        d = _digest(os.path.join(SRC, f["module"] + ".py"))
        if d and d != f.get("digest"):
            f["state"] = "retired"
            f["retired_at"] = led["last_run"]
```

`_digest()` returns `""` when the target file cannot be opened (e.g. the module was deleted or
renamed) — its own `except Exception: return ""` at `overwatch.py:213-219`. The retire
condition `if d and d != f.get("digest")` treats an empty digest as falsy, so it never fires for
a module that no longer exists; the finding stays `"open"` forever. `verify_open()` then also
makes no progress on it — reading the (missing) file raises, is caught, and the loop just
`continue`s past it (`overwatch.py:469-473`) — so a finding for a deleted module sits open,
unverifiable and unretireable, indefinitely. Rare in practice (modules are seldom deleted), but
a real gap in an otherwise carefully-reasoned lifecycle.

**VERIFIED.**

### `overwatch.py:225` — vestigial `_STATE_RANK` entries for states never assigned

```python
_STATE_RANK = {"open": 0, "stale": 1, "confirmed": 1, "refuted": 2, "retired": 2, "closed": 2}
```

Grepped every `f["state"] = ...` assignment in the file: only `"open"` (`round_once`, line 629),
`"retired"` (`round_once`, line 603), and `"closed"` (`verify_open`, line 491) are ever set.
`"stale"` and `"confirmed"` are dead keys in this dict (note: `"confirmed"` *is* used elsewhere
as a `verdict` string and as `f["confirmed_n"]`'s trigger, but never as `f["state"]`). Harmless,
but worth pruning so a future reader doesn't assume a `"confirmed"` state exists to filter on.

### `health.py:220-253` — `check_caches()`'s 200-file sample is unrandomized and skips small hosts entirely

```python
    for host in sorted(os.listdir(root)):
        files = glob.glob(os.path.join(root, host, "*.json"))
        if len(files) < 25:
            continue
        ...
        for fp in files[:200]:
```

Both caps are explicitly reasoned about in the surrounding comment as a deliberate
performance trade-off for a *health-check sample*, not a truncation of catalogued library
content — this is a judgment call, not a Hard Rule 0 violation. Two things worth flagging
anyway: (1) a host with fewer than 25 cached files can never trigger the "systematically empty"
alarm even if 100% of its (small number of) files are empty; (2) `glob.glob()` order is
filesystem-dependent, not randomized or sorted by recency, so "first 200" may inspect the same
subset of a large host's cache on every run rather than a representative sample.

### `scout.py:77-78` — `PROBE_NAMES = 25` caps the name-vocabulary used for both the model prompt and the page-verification test

```python
MIN_NAME_HITS = 2
PROBE_NAMES = 25
...
    sample = [n for n in names if n and len(n) > 3][:PROBE_NAMES]
```

Judgment call, not a violation: this is a *verification sample* (does the fetched page mention
enough of this source's catalogued names to be believed) rather than a truncation of catalogued
output — `scout()` never registers or discards catalogue entries based on this list, only
proposed host URLs. Flagged per the audit brief's instruction to flag every cap and say which
kind it is; this one bounds a measurement, it does not narrow the library.

### `overwatch.py:538, 541, 553` — `WATCH.md` report-line truncations (`broken[:4]`, `corrupt[:3]`, `sorted(...)[:40]`)

Judgment call, not a violation: `write_report()` truncates only what it *prints* to the
human-readable `WATCH.md` digest. The underlying ledger (`data/OVERWATCH.json`) retains every
finding untruncated (`led["findings"]` is never sliced anywhere in `save()`/`load()`), and
`--show` (`overwatch.py:664-669`) prints every open finding with no cap. This is display
pagination on a summary document, not a smaller universe standing in for the real one.

---

## CLEAN modules

- **`handbuilt.py`** — CLEAN. Hand-curated assay data with no caps, correct
  `tmp` + `silence.replace_retry` write pattern for `HANDBUILT_ASSAYS.json`, and the
  write-before-print ordering (lines 444-460) is a deliberately-documented and correctly
  implemented fix for a prior Unicode-crash-before-write bug. No correctness issues found.
- **`genre.py`** — CLEAN with respect to its flagged history. Directly verified that the
  `classify_source(cap=...)` character-budget bug described in the task brief is fully fixed:
  `cap` is now refused with `SystemExit` for any non-`None` value (lines 172-176), the scoring
  loop at lines 177-181 walks `rec.get("entries", [])` in full with no slicing, and a
  whole-tree grep confirms no live call site (only `verify_math.py`'s own test suite) still
  passes a numeric `cap`. One real finding remains — see MEDIUM, the bare `open(path, "w")`
  on `GENRES.json`.

---

## Summary table

| module | HIGH | MEDIUM | LOW |
|---|---|---|---|
| overwatch.py | 2 | 1 | 3 |
| handbuilt.py | 0 | 0 | 0 |
| health.py | 1 | 1 | 1 |
| scout.py | 0 | 2 | 1 |
| genre.py | 0 | 1 | 0 |
| profile.py | 0 | 1 | 0 |
| lognames.py | 0 | 1 | 0 |
| **total** | **3** | **7** | **5** |
