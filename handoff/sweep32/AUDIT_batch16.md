# Comprehensive sweep run32 — BATCH 16 audit

Modules read in full, every line:

| module | lines |
|---|---|
| src/local_agent.py | 661 |
| src/wiki_source.py | 653 |
| src/silence.py | 466 |
| src/estate.py | 339 |
| src/tuning.py | 264 |
| src/tells.py | 216 |
| src/resonance.py | 150 |

All findings below distinguish VERIFIED (reproduced or traced in source, or confirmed with a
throwaway script under the miniconda interpreter) from SUSPECTED (plausible from reading, not
independently reproduced). No files were modified. `local_agent.py` was not executed. No writes
were made to `data/records/`, `reference/keystone_volumes/`, `output/index/`, or `state/`.

---

## 1. `local_agent.py` — the headline lead

### 1a. BLOCKING (VERIFIED) — `t_propose_patch` writes the candidate patch to the LIVE file and
leaves it importable for the whole gate window before any check has run.

`src/local_agent.py:526-535`:

```python
backup = original
try:
    with open(full, "w", encoding="utf-8") as f:
        f.write(original.replace(find, replace, 1))
    fail = _gates(full, modname)
    if fail:
        with open(full, "w", encoding="utf-8") as f:
            f.write(backup)
        return {"applied": False, "reverted": True, "gate": fail}
    return {"applied": True, "why": why[:200]}
```

`full` is the real path under `src/` (`_safe()` resolves inside the actual project tree, not a
shadow copy — see `_safe()` at line 293). The write at line 528-529 lands on the real file
*before* any gate has run. `_gates()` (line 384-450) is called only *after* that write, and it is
itself a sequence of subprocess calls with independent timeouts, run serially against that same
live file:

- parse: `ast.parse` on the live file, near-instant (line 401-405)
- pyflakes: `subprocess.run(..., timeout=120)` (line 406-407)
- import check (`.py` only): `subprocess.run(..., timeout=180)` (line 432-437) — this literally
  does `import <modname>` from `src/`, i.e. it imports the patched file
- whole-suite `verify_math.py`: `subprocess.run(..., timeout=600)` (line 444-447)

So the window in which the live file on disk holds unvetted, model-authored content runs from the
`f.write()` at line 529 to whichever of (a) the revert write at line 532-533 (gate failure), or
(b) never (gate success — the patch simply stays, this is not a bug, it is the intended outcome
of a passed gate). **Worst-case duration of the exposure window, summing the gate subprocess
timeouts that can legitimately run to their limit: 120 + 180 + 600 = 900 seconds**, i.e. up to 15
minutes, not the ~600s quoted in the lead — the lead undercounts because it is citing only
`verify_math`'s timeout and not pyflakes' and the import-check's, which run to completion (or to
their own timeout) *before* `verify_math` is even invoked. In the common case where pyflakes and
the import check return quickly, the effective window is dominated by `verify_math`'s run time,
which `gpu_lane.py`'s own comments (referenced from this same file, line 561-565) record as
"240 s+, never completed" under load — so real-world exposure is plausibly minutes, not seconds.

**Blast radius during the window:** any other process on the machine that imports the same module
from `src/` — a concurrently running sweep, another `verify_math.py` invocation launched by a
different job, a scheduled task, a human's own `python -c "import <module>"` — gets the
CANDIDATE, unvetted patch, not the last-known-good file. This is a real concurrency hazard: the
module's own docstring (lines 16-21) promises "WRITES GO THROUGH THE FOREMAN'S OWN BAR... A patch
is applied only if..." — read naturally that says vetting happens *before* landing on disk. The
implementation is the opposite: it lands first, vets second, and reverts on failure. No lock is
taken during the window (no use of `silence`'s locking primitives, nor any OS-level lock) to stop
a concurrent reader/importer from observing the patched file. Confirmed no `threading.Lock`,
`filelock`, or similar guard anywhere in this function or `_gates()`.

**Also VERIFIED as a design choice that cannot simply be "fixed" by writing to a temp file
first:** the import-check gate (line 432-439) needs the file to be importable from its *real*
path (`sys.path.insert(0, .../src); import modname`) to prove the patched code actually imports
under its real module name — testing a copy elsewhere would not exercise the same import graph.
So the write-then-gate-then-maybe-revert ordering is not an oversight so much as an unexamined
tradeoff: the harness chose "test the real file" over "never expose the real file," and never
closed the resulting exposure window with a lock. This confirms the lead's core claim (unvetted
patch live in the import path of production jobs) and corrects its number (up to ~900s of
possible exposure, not 600s, though ~600s is the most likely real-world figure when only
`verify_math` is slow).

### 1b. MAJOR (SUSPECTED, exploitability bounded) — the denylist has no symlink defense.

`_safe()` (line 293-331) resolves paths with `os.path.abspath()`, never `os.path.realpath()`, and
nowhere in `local_agent.py` is `os.path.islink()` checked. If a symlink already exists under a
writable prefix (e.g. `src/alias.json` → `data/records/real_record.json`), `t_propose_patch`
computes `rel = "src/alias.json"`, which passes `WRITABLE_PREFIXES` (`"src/"`) and is not caught
by `DENYLIST_PREFIXES` (which only ever sees the string `"src/alias.json"`, never
`"data/records/real_record.json"`). The actual `open(full, "w")` at line 528 follows the symlink
at the OS level (Windows resolves reads/writes through a symlink transparently, same as POSIX),
so the write lands on the real protected file while every string-based check saw only the alias.
Whether this fully defeats a given attack depends on the gate's per-extension check in `_gates()`
(a `.py`-shaped symlink pointing at non-Python content would fail `ast.parse` and self-revert; a
`.json`-shaped symlink pointing at `data/records/*.json` would pass the `.json` gate cleanly,
since valid JSON is valid JSON regardless of which path it was reached through). **Bounded
exploitability**: the model's own tool surface (`read_file`, `list_dir`, `grep`, `propose_patch`,
`find_symbol`, `run_check`) contains no tool that can create a symlink, so this requires a
symlink to be planted by something outside local_agent's own reach (a human, another script, or
a prior compromised state) — it is not self-exploitable by the Ollama model through the tools it
is actually given. Still, the task explicitly asked whether the denylist survives a symlink, and
the answer is: **no, it does not**, and nothing in the code acknowledges the gap (contrast with
the ADS, case-folding, prefix and trailing-dot/space defenses at lines 296-331, which are each
narrated in detail as fixes to specific found bugs — no equivalent symlink narration exists).

### 1c. Denylist/allowlist logic itself — VERIFIED correct in outcome, comment is wrong about order.

Lines 494-514: the comment block at 498-500 says "THE ALLOWLIST RUNS FIRST, because it is the one
that fails closed" — but the actual execution order in the function is: (1) individual-file/module
denylist (lines 486-493), (2) allowlist (`WRITABLE_PREFIXES`, lines 501-507), (3) region denylist
(`DENYLIST_PREFIXES`, lines 508-514). The allowlist does not, in fact, run first; the module-name
denylist does. This does **not** create a security hole — every check is AND-ed (any failure
refuses the patch, regardless of order) — but it is a comment that contradicts its own code
(lens item 6), and worth fixing so the next person reading the ordering trusts what they read.
MINOR.

### 1d. Every other described defense (ADS, case-folding, prefix-boundary, trailing dot/space,
absolute-path, `..` traversal) — VERIFIED correct by reading. `_safe()`'s component-by-component
scan for `:` and `!= .rstrip(". ")` (line 314-318), the case-folded module/path denylist
(line 486-490), and the `full == HERE or full.startswith(HERE + os.sep)` boundary check
(line 327-328) each do what their comments claim. `os.path.abspath()` normalizes `..` before any
check runs, so `..`-traversal is closed. An absolute path outside the repo is rejected by the
prefix-boundary check; an absolute path inside the repo is reduced to a `rel` string before the
allow/deny checks, so it is treated identically to a relative one. These are genuinely fixed, not
just claimed fixed.

### 1e. MINOR — reraise-on-crash path still lets the gate machinery itself explode without
protection beyond a bare `except Exception`.

Lines 536-557: if the write, `_gates()`, or the revert attempt raises, the outer `except Exception
as e` catches everything, tries to revert, and reports an `ALARM` if even the revert failed
(line 551-556). This is well-reasoned and explicitly documented as a fix for a prior bug (the
comment at 538-543 references a `run #23` fix for a revert that used to lie about succeeding).
Read closely, it is correct: `reverted` starts `True`, is only set `False` in the nested except,
and the returned dict never claims `reverted: True` on a path where the second write actually
failed. NOTE, not a bug — recorded here because it was explicitly in scope to verify.

---

## 2. `silence.py` — the canonical two-writer contract implementation

### 2a. MAJOR (VERIFIED) — `_handlers()`'s "uses_exc" check is a tautology; it can never detect
a genuinely silent `except X as name: pass`.

`src/silence.py:115-138`, specifically line 133:

```python
uses_exc = bool(node.name) and node.name in body
```

`body = ast.dump(node)` (line 127) — the AST dump of the **entire exception handler node**,
which necessarily includes the handler's own `name=` field verbatim (e.g.
`ExceptHandler(type=Name(id='Exception', ...), name='e', body=[Pass()])`). So `node.name in body`
is checking whether the string is present in a text blob that is *guaranteed* to contain it,
regardless of whether the exception variable is ever referenced anywhere in the handler's actual
body. Reproduced directly:

```
>>> ast.dump(ExceptHandler for "except Exception as e: pass")
"ExceptHandler(type=Name(id='Exception', ctx=Load()), name='e', body=[Pass()])"
>>> node.name in body   # -> True, always, for ANY name, even a nonsense one never used elsewhere
```

Verified with `except Exception as zzzq: return None` (a name that appears nowhere else in the
handler) — `node.name in body` still evaluates `True`, because `name='zzzq'` is part of the
dump text itself. **This means `except <anything> as <name>: pass` (or `return None`, or
`continue`) — the single most common shape of a genuinely silent handler in Python — is
*always* classified as "observed" (`silent = False`) by this audit, for any binding name at
all**, which is exactly backwards: this is the shape `silence.py`'s own module docstring names as
the project's signature defect. The audit that exists specifically to catch "45 handlers that
return None with no record" cannot, by construction, ever flag one that happens to bind the
exception to a name and then ignore it.

**Current impact in this tree**: I scanned every `ExceptHandler` in `src/*.py` (110 handlers use
`except ... as <name>`) with a corrected version of this check (does the body's own statements
actually reference `node.name`, not the handler's self-describing dump) and found **zero**
handlers currently exploiting this hole — every existing `except X as name` handler in this repo
either genuinely uses the bound name or independently calls a recording keyword
(`silence`/`note`/`health`/etc.), so `records` already catches them by the other branch of the
`or`. So this is a latent defect in the checking machinery itself, not (yet) a false negative
that is hiding a real bug today. But it is exactly the "check that cannot fail" the lens asks
for: the very next contributor who writes `except Exception as e: pass` (an extremely common,
unremarkable-looking Python idiom) will have it silently pass `python src/silence.py`'s own
audit and `local_agent.py`'s `run_check(check="silence")` tool (line 184-192 of local_agent.py),
which is exactly the automated gate the local model is told to trust.

### 2b. MAJOR (SUSPECTED) — `digest_of` conflates "file absent" with "file unreadable for any
other reason," defeating the compare-and-swap it exists to implement.

`src/silence.py:223-233`:

```python
def digest_of(path):
    try:
        with open(path, "rb") as f:
            return hashlib.sha1(f.read()).hexdigest()[:16]
    except FileNotFoundError:
        return None
    except Exception:
        note("silence.py:digest_of")
        return None
```

Both branches return `None`. `replace_if_unchanged()` (line 236-260) uses `expected_digest=None`
specifically to mean "the caller asserts the file did not exist when it read" (docstring line
251-252: "`expected_digest=None` asserts the file did not exist when it was read, which is how a
first-write is distinguished from an overwrite"). But `digest_of` returns the identical `None` for
a transient read failure on an *existing* file — e.g. a `PermissionError` while another writer
holds the file mid-`os.replace()` (the exact race `replace_retry`, two functions below, exists to
outwait). If that happens at the moment `replace_if_unchanged` calls `digest_of(dst)` to check
staleness (line 254), `actual` comes back `None` for the wrong reason, matches a caller's
`expected_digest=None`, and the function proceeds to `replace_retry(tmp, dst)` — silently
overwriting a file that in fact existed and had a live writer, which is precisely the m42 hazard
this function's own docstring says cost the project real data twice. Only `drill.py` calls this
pair today (`replace_if_unchanged`/`digest_of` are not yet used by the other 15 dependent modules
this contract is meant for), so exposure is currently narrow, but the function's contract is
unsound for any future caller that adopts the documented "assert first-write with
`expected_digest=None`" pattern.

### 2c. MAJOR (VERIFIED) — `write_json` does not fsync; "atomic" is true only for the rename,
not for durability of the write.

`src/silence.py:290-327`. The docstring calls this "the one correct way to write a shared file in
this project" and stresses atomicity throughout, but the write itself is:

```python
with open(tmp, "w", encoding="utf-8") as f:
    _j.dump(obj, f, **dump_kw)
...
return replace_retry(tmp, path)
```

There is no `f.flush()` + `os.fsync(f.fileno())` before the `with` block closes the file, and no
fsync of the containing directory after `os.replace()` (inside `replace_retry`, line 263-280)
lands the rename. `os.replace()` is atomic with respect to *other processes observing the
rename* (no reader ever sees a half-written file — that guarantee holds), but it says nothing
about whether the tmp file's bytes have actually reached the disk before a crash/power loss. Python's
`file.close()` only flushes the language-level buffer into the OS; the OS may still hold the data
in its page cache. On an unexpected shutdown between the buffered write and physical flush, the
renamed target file can exist with truncated or stale-on-disk content, which is exactly the class
of corruption this whole module (and `estate.py`'s file-integrity sweep) is built around detecting
after the fact. This is a durability gap, not a rename-atomicity gap — worth flagging precisely
because the audit lens asked "is `write_json` atomic and does it fsync?": atomic, yes; fsync, no.

### 2d. MINOR — `replace_retry` leaves the tmp file behind on persistent failure.

`src/silence.py:263-280`. When all `attempts` are exhausted with `PermissionError`, the function
returns `False` and records `note("replace-denied:...")`, but never removes the tmp file it
created. Since `write_json`'s tmp names carry PID and thread id (line 316), a persistently locked
destination leaves an orphaned `*.tmp` file on every failed attempt, accumulating over the life of
a long-running or frequently-retried process. Not data-corrupting, just a slow disk-space/clutter
leak. The `False` return itself is unambiguous and is correctly treated by `write_json` as "did
not land" (it is simply propagated, not swallowed) — that part of the contract is sound.

### 2e. MINOR (concurrency) — `note()`'s flush counter is a global mutated without a lock.

`src/silence.py:330-362`, specifically `_SINCE_FLUSH += 1` / reset at line 357-360. `note()` is
called from worker threads in `wiki_source.py` (via `ThreadPoolExecutor`, e.g. inside `_get()`) as
well as from the main thread elsewhere. `_SINCE_FLUSH` is a bare module-level int mutated from
multiple threads with no lock. Two threads can race the `+=` (read-modify-write, not atomic across
the three bytecode-level steps) and lose an increment, or both cross the `>= FLUSH_EVERY`
threshold on the same "reading," causing `health.flush()` to run twice back-to-back or slightly
later than intended. Not corrupting (health.flush() is presumably idempotent-ish, writes the
in-memory ledger to disk), just an inexact counter — the failure ledger could reach disk a little
later than every 25 calls under heavy thread contention, which matters for the module's own
stated goal ("the count reaches disk while the run is still going and can still be stopped," line
353-356). MINOR.

---

## 3. `wiki_source.py`

No Hard Rule 0 violations found. This module is the one the batch brief specifically flagged as
"prime suspect," and on this pass it reads as *already hardened*: every listing-producing function
(`category_members`, `find_categories`, `rank_by_size`, `discover_categories`, `all_categories`)
defaults its cap parameter to `None`/uncapped and only slices when a caller explicitly passes a
limit. `all_categories`'s `hard_stop` kwarg literally has a docstring (lines 361-371) narrating
why the 6000 default was removed as a Hard-Rule-0 violation, with the kwarg kept only for a human
debugging a pathological wiki, and "nothing in the tree passes it." I confirmed no caller in
`catalogue_web.py` (the only consumer of `rank_by_size`/`find_categories`/`category_members`/
`page_texts`) passes a non-None `limit`/`top`. NOTE only:

- `page_text`'s `max_chars=900` and `extracts`'s `chars=700` truncate a single page's *prose*, not
  a roster/listing — this reads as legitimate "how much of one article's text to keep" rather than
  the roster-truncation Hard Rule 0 targets, but it is worth a human confirming that reading, since
  the charter's wording ("no truncation of... a chunk list") is broad enough that a very rich
  article's remaining prose is technically being discarded past 900/700 chars. NOTE, not flagged
  as a violation, since this is per-page evidence text feeding the model, not the entity roster
  itself, and every roster-producing function above is confirmed uncapped.
- `resolve_wiki()` (lines 256-303) catches only `OSError` around the `WIKI_HOSTS.json` read (line
  278), deliberately leaving a `json.JSONDecodeError` on a corrupt hosts file unhandled and fatal
  — the docstring explains this was itself a fix for an earlier bug (a bare NameError being
  swallowed). A malformed `WIKI_HOSTS.json` will crash `resolve_wiki` outright rather than degrade
  to guessing. This reads as an intentional fail-loud choice consistent with Hard Rule -1's
  "fail closed" doctrine, not a defect. NOTE.
- `_get()`'s retry loop calls `silence.note()` on every `429/503` HTTPError, including ones that
  are about to be successfully retried (line 189-194) — this means the failure ledger records a
  "failure" for transient, self-healing rate-limit backoffs indistinguishable from a genuine dead
  end, which could make `health.py --failures` look noisier than the true failure rate. MINOR —
  worth a human deciding whether a retried-and-succeeded 429 should count.

---

## 4. `estate.py`

Reads cleanly against its own stated goal ("every file, opened. No sampling."). Confirmed no
sampling anywhere in `artifacts()` — `roots` is a fixed list of top-level directories walked in
full via `_walk()`, and every path found is passed to `inspect()` with no slicing. NOTE-level
observations only:

- `written()` (lines 217-257): for `catalog.json`/`failures.json`, `if d: note(...)` (line 251)
  means an *empty but present and validly-parsed* file (e.g. `{}` or `[]`) produces no note at
  all — indistinguishable, from the report, from the file not existing (which is handled by the
  earlier `if not os.path.exists(p): continue`, line 245-246). A genuinely empty catalog after a
  real run would be silent here in the same "absence looks like a legitimate finding" shape the
  rest of the project has spent so much effort naming and fixing elsewhere. MINOR.
- Exception handlers in `charter()`/`written()`/`terminal()`/`external()` record findings into
  their own local `out` list rather than calling `silence.note()` — this is not swallowing (the
  finding is visible to every caller of these functions), just inconsistent with `inspect()`'s use
  of `silence.note()` in the same file. NOTE, not a bug.

---

## 5. `tuning.py`

Reads cleanly. The documented history of prior bugs (the `if requested` vs `is not None` boundary
bug, the hardcoded `ollama_host`, the reachability-vs-success conflation) all check out as
genuinely fixed in the current code — I traced `workers()` (line 226-244) and confirmed
`min(requested, n) if requested is not None else n` correctly treats `requested=0` as "run
nothing" rather than falling through to the full profile count. No Hard Rule 0 issues (all
constants here are timeouts/worker-counts/chunk-sizes, not listing caps). NOTE-level only:

- `_CACHE` (module-level dict, line 104) is updated by `regime()` (line 211) with no lock; if
  called concurrently from multiple threads the `.update()` call itself is safe at the bytecode
  level for a single dict assignment, but two threads can race to decide the cache is stale and
  both do the (cheap) recomputation — wasted work, not incorrect output. MINOR/NOTE.
- `_answering_buckets()` computes `age` from `os.path.getmtime(p)` and reports it in the "why"
  string only for the stale-proof case; if the file read subsequently fails for a reason other
  than "does not exist" (e.g. malformed JSON), the same generic `"no pool proof on disk"` message
  is returned, which is mildly misleading but does not affect the actual bucket count returned
  (`0` either way). NOTE.

---

## 6. `tells.py`

No correctness bugs found in the regex/matching machinery itself; the sentence-boundary anchor
fix (`_anchor()`, lines 130-131) is correctly implemented and reproducible by hand — it rewrites
any pattern beginning with the literal 4-character prefix `r"^\s*"` to instead anchor on
`(?:^|(?<=[.!?])\s+)`, and every pattern in `STRUCTURAL`/`DISCOURSE` that starts with `^` does in
fact start with exactly that 4-character prefix, so the rewrite fires for all of them today.
Findings:

- MINOR — double-counting from overlapping lexical entries. `LEXICAL` contains both `"myriad"`
  and `"myriad of"` (lines 47, 53); `LEXICAL_FICTION` contains both `"tapestry"`-adjacent entries
  and `"tapestry of"` (line 45 has "tapestry" in LEXICAL, line 62 has "tapestry of" in
  LEXICAL_FICTION). Since `scan()` (line 144-155) runs every lexical pattern independently and
  sums `len(pat.findall(text))` per word, a single occurrence of "myriad of border towers" is
  counted **twice** — once under `word: myriad` and once under `word: myriad of` — inflating the
  tell rate for any passage using the longer phrase, which directly affects the "rate, not mere
  presence" metric the module's own docstring (lines 23-26) says is what makes the audit
  meaningful ("a single 'vibrant' in fifty thousand entries is not a defect" — but a passage using
  "myriad of" gets counted as if it used two different tells).
- NOTE — the module docstring (lines 16-18) describes `LEXICAL` as "single words," but the actual
  list contains multi-word phrases throughout (`"realm of"`, `"landscape of"`, `"journey of"`,
  `"navigate the"`, `"myriad of"`, `"treasure trove"`, `"steeped in"`) — comment/code mismatch,
  cosmetic, does not affect the regex logic since `re.escape()` handles multi-word phrases
  correctly regardless of what the docstring calls them.
- NOTE — `_anchor()`'s rewrite is keyed on the literal string prefix `r"^\s*"` (line 131); a
  future pattern added with a different `^`-based prefix (e.g. `r"^In "` with no `\s*`) would
  silently skip the sentence-boundary upgrade and remain anchored to string-start only, with no
  error or warning. Fragile convention, not a present bug (no such pattern exists today).

---

## 7. `resonance.py`

### 7a. MAJOR (VERIFIED) — the entire module is dead code; nothing in the tree imports it.

```
grep -rln "import resonance|from resonance|resonance\.hodge|resonance\.incomparability|resonance\.resonance_strength" --include=*.py .
  -> only src/custodes.py, and that hit is a DOCSTRING SENTENCE, not an import or a call
```

`src/custodes.py` never contains `import resonance` anywhere (checked its full import block,
lines 54-61) — its only occurrence of the string "resonance" in the whole file is the prose at
line 297: "`eta` (from resonance.hodge_decompose) lets Threnody exercise her veto..." This is a
comment describing an integration that does not exist in code (lens item 6, and item 7 "dead
functions" at the whole-module scale): `hodge_decompose`, `incomparability_rate`,
`resonance_strength`, and `dominates` are defined, exported, and documented as the computational
backbone of the "Threnody veto" mechanism the charter-adjacent design describes, but are called
from nowhere. Any bugs inside this module (see below) are currently inert, but the module's own
framing — presented as already operational machinery ("the relational ontology, made
computable") — overstates what the codebase actually does today.

### 7b. MAJOR (VERIFIED, currently inert) — `dominates()` conflates "no comparable data" with
"genuinely incomparable," directly contradicting `incomparability_rate`'s own docstring claim.

`src/resonance.py:101-128`:

```python
def dominates(v1, v2):
    shared = [k for k in v1 if k in v2 and v1[k] is not None and v2[k] is not None]
    if not shared:
        return False
    return all(v1[k] >= v2[k] for k in shared) and any(v1[k] > v2[k] for k in shared)
```

When two vectors share **zero** scored axes (no data on either, on the same axis, at all),
`dominates(v1, v2)` and `dominates(v2, v1)` are **both** `False` — the same result as when they
share axes but genuinely disagree on them. `incomparability_rate()` (line 109-128) then counts
both cases identically as "incomparable" (line 122-123: `if not dominates(va, vb) and not
dominates(vb, va): inc += 1`). But its own docstring says, in the same breath: "An incomparable
pair is not an unresolved question; it is a resolved finding that no ordering exists between two
things" (lines 112-114) — that claim is false for any pair reached through the empty-`shared`
branch, which is exactly an *unresolved* question (no data was ever compared), not a resolved
finding of order-theoretic incomparability. This is the module's own governing thesis (η as "the
measure of Coexistent Contradiction," line 34) resting on a metric that cannot currently tell
"we have no evidence" from "we have evidence and it conflicts" — precisely the
absence-looks-like-a-finding shape `silence.py`'s docstring names as this project's signature
defect, reproduced here in the philosophy module built to formalize relational structure.
Currently inert (see 7a — nothing calls this), but load-bearing the moment `custodes.py`'s
described integration is actually written.

### 7c. NOTE (VERIFIED) — `hodge_decompose({})` raises `ZeroDivisionError` rather than returning
a sane empty-input result.

`src/resonance.py:71-79`: with `edges={}`, `nodes` is `[]`, the inner loop over `nodes` never
executes so `new` stays `{}`, and `shift = sum(new.values()) / len(new)` divides by
`len(new) == 0` on the very first outer iteration — an unhandled `ZeroDivisionError`, not a
silent/vacuous pass. This is the opposite failure shape from most of this lens (loud crash, not
swallowed failure) and is arguably the *correct* behavior for genuinely nonsensical input, but it
means the function has no graceful path for "no data yet," which will matter once something calls
it. Currently untriggered (no live callers).

---

## Summary tally

- BLOCKING: 1 (1a — local_agent.py live-file exposure window, confirmed and re-measured)
- MAJOR: 6 (1b symlink gap; 2a silence.py tautological uses_exc check; 2b digest_of None
  conflation; 2c write_json no-fsync; 7a resonance.py entirely dead code; 7b dominates() vacuous
  incomparability)
- MINOR: 8 (1c comment/order mismatch; 2d orphaned tmp files; 2e unlocked flush counter;
  wiki_source 429/503 noted-as-failure; estate.py empty-dict-skips-note; tuning.py unlocked
  cache race; tuning.py generic pool-proof-failure message; tells.py double-counted lexical
  overlaps)
- NOTE: 6 (1d confirmed-fixed defenses; 1e confirmed-correct revert path; wiki_source page-text
  truncation and resolve_wiki fail-loud; tells.py docstring mismatch and fragile anchor
  convention; resonance.py ZeroDivisionError on empty input)
