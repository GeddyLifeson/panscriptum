# Batch 04 — run33
Modules read: foreman.py (1367 lines), silence.py (465 lines), sweep_plan.py (325 lines), sweep.py (258 lines), runguard.py (219 lines), catalogue_models.py (176 lines), lognames.py (36 lines)

## FINDINGS

### 1. runguard.py:73-80 — `_land()` writes the overlap guard through a non-unique tmp filename  [severity: BLOCKING]
`_land(rec, path)` does:
```python
tmp = path + ".tmp"
with open(tmp, "w", encoding="utf-8") as f:
    json.dump(rec, f, indent=2)
...
return silence.replace_retry(tmp, path)
```
`tmp` is a fixed name (`GUARD + ".tmp"`), the same for every caller in every process. Compare
`sweep_plan._shard_path()` in this same batch, whose docstring explains exactly why this is unsafe:
"A filename no other writer can collide with: run + batch + pid ... The batch id alone is not
enough — an agent that is retried... would land on the same name as its predecessor mid-write."
`runguard.py`'s own module docstring describes the scenario this file exists to police —
*two processes racing to claim `state/MAINTENANCE_RUN.json`* — which is precisely the scenario in
which two `claim()` calls (or a `claim()` racing a `beat()`/`release()` held by a different agent)
open, truncate, and write the *same* `path + ".tmp"` concurrently. One writer's partial buffer can
land under the other's `os.replace`, or the second `open(tmp, "w")` can truncate the first writer's
already-written bytes out from under its still-open file handle, producing an interleaved or
truncated `MAINTENANCE_RUN.json`. `silence.replace_retry` only protects the *rename* step (Windows
`PermissionError` while a reader holds the destination); it does nothing for a torn write into a
shared tmp path. `HANDOFF.md`/`BUGS.md` record `runguard._land:PermissionError` firing **99 times**
in production, which is direct evidence multiple writers are already contending on this file live.
This is the exact defect class `silence.py`'s own module docstring is a monument to, reproduced
inside the module that is supposed to prevent overlapping runs.

### 2. runguard.py:98-121 — `claim()` has an unguarded check-then-write race  [severity: MAJOR]
```python
prior = read(path)
if holder_is_live(prior):
    ...
    return False, (...)
...
if not _land(rec, path):
    return False, "could not write the guard record"
return True, "claimed"
```
Between `read()` and `_land()` there is no lock and no compare-and-swap (`silence.replace_if_unchanged`
exists in this exact codebase for exactly this purpose and is not used here). Two processes racing
`claim()` within the same window can both read a "free" guard and both proceed to write — combined
with finding 1's tmp-name collision, both can come away believing `ok=True` while only one (or
neither, if the tmp write interleaves) actually holds a coherent record. This defeats the single
invariant the module's docstring states as its whole reason to exist: "A run may only ever refresh,
or close, a record that carries its own name" — that only holds if claiming itself is atomic, and
it is not.

### 3. silence.py:133 — the "handler observes its exception" check is a tautology  [severity: MAJOR]
```python
uses_exc = bool(node.name) and node.name in body
silent = not (records or uses_exc)
```
where `body = ast.dump(node)` — the AST dump of the `ExceptHandler` node *itself*. `ast.dump` of an
`ExceptHandler` always serialises the handler's own `name=` field into the dump string whenever
`except X as name:` is used (e.g. `ExceptHandler(type=..., name='e', body=[...])`), independent of
whether `name` is referenced anywhere inside the handler body. So `node.name in body` is true for
*every* `except Exception as e:` regardless of whether `e` is ever used — a handler shaped exactly
like the fifteen faults this module's own docstring lists as the project's one recurring defect:
```python
except Exception as e:
    return None
```
is classified `silent=False` ("observed") purely because it named the exception, never because it
did anything with it. This is the canonical detector `silence.audit()`, `main()`, and (by extension)
every dashboard/standard reading `silence --all`'s output trusts to find real silent failures across
`src/`. A check that cannot fail on the exact shape it was built to catch is worse than no check —
`HANDOFF.md`'s run #32 notes already name this line as found-but-unrepaired; it is still present
verbatim in the source I read.

### 4. foreman.py:192 — `scout_hostless()` permanently starves sources ranked 5th and lower  [severity: MAJOR]
```python
res = SC.sweep(limit=4)
```
`scout.sweep()` (src/scout.py:237-241) computes `order = sorted(todo, key=lambda s: -len(todo[s]))`
then `order[:limit]`, i.e. a deterministic, stable ranking by entry count, truncated to `limit`.
A source that is attempted and fails to find a host (`kept` empty) stays in `hostless()` next round
with an unchanged rank — so the same top-4 sources are retried every foreman round for the
`"sources with a reachable wiki"` standard (`REMEDIES["sources with a reachable wiki"] =
[adopt_hosts, scout_hostless]`), and any source ranked 5th or lower by entry count is never
attempted, ever, for as long as the top 4 keep failing. This is Hard Rule 0's exact shape — a
ranked-then-truncated list silently deciding which sources exist for this remedy's purposes — and
was already confirmed by a prior sweep run against `scout.py:237-241`; I independently re-verified
both sides of the call (foreman's call site and scout's ranking/truncation logic) against the
current source.

### 5. silence.py:223-260 — `digest_of()` conflates "absent" with "unreadable," undermining the CAS it backs  [severity: MAJOR]
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
Both "the file genuinely does not exist" and "the file exists but could not be read right now"
(e.g. a transient `PermissionError` from a concurrent writer mid-replace) return the same sentinel,
`None`. `replace_if_unchanged()` is built entirely on that sentinel meaning something specific:
"`expected_digest=None` asserts the file did not exist when it was read, which is how a first-write
is distinguished from an overwrite." If `digest_of(dst)` inside `replace_if_unchanged` hits a
transient read failure on a file that in fact now exists (created by a different writer in the
interim — exactly the race this function exists to catch), it returns `None`; if the caller's own
`expected_digest` was also legitimately `None` (an honest first write), the compare passes
(`actual == expected == None`) and the stale-looking write is landed anyway — silently overwriting
whatever the concurrent writer placed there. The docstring for `replace_if_unchanged` says this
hazard "has cost this project real data twice (m42)"; the one distinction it depends on
(absent vs. merely-unreadable) is not actually made by the function it depends on.

### 6. foreman.py:858-871 — `_function_source()` can select the wrong function when names collide  [severity: MAJOR]
```python
want = symbol.split("(")[0].split(".")[-1].strip()
for node in _ast.walk(tree):
    if isinstance(node, (_ast.FunctionDef, _ast.AsyncFunctionDef)) and node.name == want:
        ...
        return "".join(lines[start:end]), start, end
```
`symbol.split(".")[-1]` discards any class qualifier the finding's `symbol` field carries (the
module docstring explicitly says findings can name "a top-level function or method"), so
`ClassA.__init__` and `ClassB.__init__` in the same file are indistinguishable to this lookup, as
are any two same-named functions/methods anywhere in the module. `ast.walk()` is a breadth-first
traversal, not a source-order one, so the match returned is not even guaranteed to be the
textually-first occurrence. This function feeds the MODEL lane — the one `attempt_patch()` fences
harder than anything else in the file specifically because it edits live source unsupervised. A
finding naming `ClassB.__init__` can have its patch silently written over `ClassA.__init__`'s body
instead; `_checks_pass()` only verifies the module still imports and `verify_math`/`allsweep` still
pass, neither of which would detect a syntactically-fine patch landed on the wrong same-named
function while the actually-defective one goes untouched and gets `retire`d as if fixed.

### 7. sweep_plan.py:143-151 — the shard write is the one write in this file that bypasses `silence.replace_retry`  [severity: MINOR]
```python
p = _shard_path(run, batch if batch is not None else "x")
tmp = "%s.tmp" % p
with open(tmp, "w", encoding="utf-8") as f:
    json.dump({"run": run, "batch": batch, "at": now, "modules": covered}, f, indent=1)
os.replace(tmp, p)
```
Every other landing in this file (`silence.write_json(COVERAGE, ...)`, used twice) goes through the
atomic/retried path; this one — the write the module's own docstring calls "WRITTEN AS A PER-BATCH
SHARD, because the whole point of this file is that sixteen batches run AT ONCE" — uses a bare
`os.replace` with no retry. Practical risk today is low because `_shard_path` embeds run+batch+pid
so `p` is normally a brand-new filename each call (a bare rename onto a not-yet-existing path is not
the Windows-deny-while-open case `replace_retry` guards against), but it is a real deviation from
the pattern this file exists to enforce, and it stops being safe the moment a caller retries
`record()` for the same run/batch inside the same process (same `p`, and `_read_shards()` in a
sibling process may be mid-`glob`/`open()` over exactly this directory at the same moment).

### 8. catalogue_models.py:158 — the console "current alternatives" line truncates to 10 models  [severity: MINOR]
```python
print(f"  {name}: " + ", ".join(r["models"][:10]))
```
This is the same file that (line 151, per its own comment) was already fixed for this exact class
of bug — `stale.append({..., "available_sample": list(r["models"])})` deliberately keeps the whole
list "only because the written record may already be on disk under [the `_sample` key]; the value
is no longer a sample." Line 158 still truncates. The consequence is narrower than the earlier fix
because the full list is already persisted (in `stale[]` and in `payload["providers"]`, both
written whole via `silence.write_json`), so nothing downstream that reads `PROVIDER_MODELS.json`
loses data — only the human-facing console summary can hide a valid replacement model ranked 11th
or later at the moment someone is reading the terminal to pick one.

## QUESTIONS

- **sweep.py:176-198** — `report()`'s funnel prints `drop = prev - f[k]` for each successive stage
  and documents "Each stage is a strictly smaller set than the one above," but nothing in `sweep()`
  enforces that `"addressed"` (shelfmark presence, derived from `NAVTREE.json`) is a subset of
  `"catalogued"` (the `e.get("catalogued")` flag stored per entry) — the two are computed from
  unrelated data. If a source is shelved but its entries aren't yet flagged catalogued, `addressed`
  could exceed `catalogued` and `drop` goes negative, printing a doubled minus sign. This may be
  guaranteed true by the upstream catalogue/shelving pipeline in practice (every catalogued source
  is already shelved) in which case it's cosmetic-only; I couldn't confirm that invariant from the
  files in this batch alone.
- **sweep_plan.py:158-176** — `record()`'s fold into `SWEEP_COVERAGE.json` discards
  `silence.write_json`'s boolean return, and the `except Exception` fallback around it also catches
  a non-import failure from `write_json` itself, falling through to a raw `os.replace` with no
  retry and no further error handling. The docstring calls this file "a CONVENIENCE VIEW... nothing
  draws a conclusion from it that the shards do not support," which would make a silent failure
  here low-stakes by design — worth confirming that no caller (e.g. `--coverage` reporting, or a
  human skimming it) is actually treated as authoritative anywhere outside this batch.
- **silence.py:290-327** — `write_json()`'s docstring calls it "the one correct way to land a JSON
  file" and stresses atomicity; it does not `fsync` before `os.replace`. That's consistent with the
  literal claim (no reader ever observes a torn/partial file) but not with durability across an OS
  crash between the tmp write and the rename. Worth a ruling on whether durability was meant to be
  part of the contract, since several call sites describe files as safe to kill the process around.

## CLEAN

- **catalogue_models.py** — read in full. Well-hardened against the stale-model-ID and truncation
  classes of bug it was written to fix; the one remaining truncation is covered above (finding 8)
  and is low-stakes because the full data is persisted separately.
- **lognames.py** — read in full. A pure constants/mapping module (log filenames and their owning
  command-line fragments); nothing to find.
