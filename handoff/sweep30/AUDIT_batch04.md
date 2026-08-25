# AUDIT — batch 04 (sweep30)

Files: `src/foreman.py`, `src/silence.py`, `src/pantheon.py`, `src/feats_index.py`,
`src/cleanup.py`, `src/cosmology_graph.py`. Every line of every file was read top to bottom.
Read-only reproductions were run against the real `data/` files where noted; nothing in the repo
was edited.

**No committed secrets found in this batch** (grepped for api key / secret / token / password /
bearer / `sk-` patterns across all six files — the only hits were the English words "tokens" in
`foreman.py`'s Ollama-restart prose, not credentials).

---

## 1. `src/cosmology_graph.py`

### 1.1 HIGH — undisclosed `w >= 1.0` filter drops 71% of computed source-pair edges; 25 sources vanish downstream entirely — Hard Rule 0 — `cosmology_graph.py:151` — **REPRODUCED**

`main()`'s `--write` path:

```python
"pairs": [{"a": a, "b": b, "weight": round(w, 3), "shared_sample": pair_shared[(a, b)]}
          for (a, b), w in sorted(pair_w.items(), key=lambda kv: -kv[1])
          if w >= 1.0],
```

`build_graph()` computes a weight for *every* co-attested source pair (`pair_w`) with no
threshold. The write step then silently drops every pair whose weight is below 1.0 before
persisting to `data/SHARED_STAGE_GRAPH.json`. This is exactly Hard Rule 0's shape — rank, then
truncate the tail — and unlike the `shared_sample` truncation fixed in the same function (see the
comment at lines 86–92, explicitly citing the 2026-08-24 owner ruling), this filter carries **no
comment, no owner ruling, and no reported count of what it drops.**

Reproduced by running `build_graph()` against the live `data/WEAVE_CANDIDATES.json`
(read-only, no write):

```
total source-pair edges computed: 3753
kept (w>=1.0):                    1087
dropped (w<1.0):                  2666
sources appearing in ANY computed edge: 197
sources appearing in a KEPT edge:       172
sources FULLY ABSENT from the written graph: 25
```

25 sources (e.g. `Warhammer Fantasy`, `Rainbow Six`, `Xanathar's Guide to Everything`, `Date A
Live`, `Ghosts of Saltmarsh`, `the Lovecraftian mythos`, `Sakamoto Days`, full list captured in
the repro run) have real, computed, evidence-bearing co-attestation weight with at least one
other source, and after `--write` they have **zero** edges in `SHARED_STAGE_GRAPH.json` — they
do not exist to `propagation.py` or `resonance.py`, both of which the file's own comment (line
144) says read this file live and would "silently trust" an incomplete graph. `main()`'s printed
summary (`source pairs sharing >=1 entity : {len(pair_w):,}`) reports the pre-filter total
(3753), so even the console output misrepresents what actually lands on disk (1087).

Why the threshold produces this: `w = 1.0/math.log(n+1.5)`, and for the minimum qualifying
`n=2` (two sources sharing exactly one entity), `w ≈ 0.798` — already under 1.0 from a single
shared entity. Any pair whose accumulated weight from ALL its shared entities never crosses 1.0
is dropped outright, regardless of how many genuine (if individually weak) shared entities it
has.

**Fix:** either drop the `if w >= 1.0` filter entirely and persist every computed pair (the
`threshold` argument already exists for consumers that want to cluster above a cutoff — see
`components()`, which takes `--threshold` as an explicit, disclosed, printed parameter), or if a
floor is kept, report the drop count and the list of now-absent sources the way `_retire`/
`triage_swallowed` report every other filtered quantity elsewhere in this batch.

### 1.2 LOW — `src_entities` computed, returned, and never used — dead value, not dead code — `cosmology_graph.py:68,76,94,127`

`build_graph()` builds and returns a full `{source: count}` map; `main()` unpacks it into
`src_entities` and never reads it again (no print, no field in the written JSON). Confirmed via
grep — no other module imports `build_graph` or reads this value. Not incorrect, just wasted
computation / a report line that looks intended but was never wired up.

### Clean
`components()`'s BFS/connected-components logic is correct and unbounded (no cap on cluster
size or count). The `[:16]` / `[:8]` / `[:6]` / `[:4]` slices in `main()`'s printed report are
all display-only — the full `pair_w`, `comps`, and `pair_shared` are what get written to disk,
matching the comment's own claim. The write is atomic via `silence.write_json` (two-writer
contract respected).

---

## 2. `src/silence.py` — the anti-silence module's own detector is provably tautological, and the codebase now depends on the hole

### 2.1 HIGH — `uses_exc` (`:133`) is a tautology: a named exception handler is ALWAYS "observed", regardless of whether the name is ever used — **REPRODUCED**

```python
uses_exc = bool(node.name) and node.name in body
```

`body = ast.dump(node)`. `ast.dump` of an `ExceptHandler` always serialises the handler's own
`name` field verbatim (e.g. `ExceptHandler(type=Name(id='Exception', ...), name='e', body=[...])`),
so `node.name in body` is true for *any* named handler independent of what the handler's body
actually does. Minimal repro:

```python
>>> ast.dump(handler_for("except Exception as e:\n    return None"))
"ExceptHandler(type=Name(id='Exception', ctx=Load()), name='e', body=[Return(value=Constant(value=None))])"
>>> node.name in body   # 'e' in the string above
True
```

`except Exception as e: return None` — a handler that discards `e` completely — is classified
"observed" by this check alone. This is exactly the class of fault the file's own docstring
describes (`silent = not (records or uses_exc)`), inverted: the second half of the "or" can never
meaningfully be False when a name is bound. **Empirically**, scanning all 103 files in `src/`
found zero handlers in the *current* tree that this specific path currently misclassifies (every
`except X as name:` in this codebase happens to genuinely reference `name` in its body) — so this
is a live logic bug with (currently) no live victim, not a hypothetical. It is one `as e` away
from silently certifying any of this file's own "45 silent handlers" as clean.

**Fix:** test whether the bound name is referenced as an `ast.Name` load somewhere in the
handler's *statements*, not whether the dump-string of the whole node (which trivially embeds the
name declaration itself) contains the name.

### 2.2 HIGH — the "observed" trigger words (`:128-129`) match anywhere in the AST dump, including inside string literals — and the codebase has built a 40+-site convention that depends on exploiting exactly this — **REPRODUCED**

```python
records = any(t in body for t in ("health", "record", "log", "print", "raise",
                                  "swallow", "silence", "LEDGER"))
```

`body` is the full `ast.dump()` text, which includes every string literal's contents verbatim.
A handler whose only text containing one of these eight words is inside a *string* — not a call,
not an identifier — is still marked "observed".

This is not a theoretical false positive: **16 files use the literal idiom
`_ = "silence-exempt: <reason>"` inside an otherwise-bare `except` body, specifically because the
string "silence-exempt" contains the substring "silence"**, one of the eight trigger words. Grep
confirms 43 occurrences of `silence-exempt` across `chain.py`, `completeness.py`, `coverage.py`,
`dashboard.py`, `feats.py`, `gpu_lane.py`, `handbuilt.py`, `local_agent.py`, `overnight.py`,
`pipeline.py`, `read.py`, `runguard.py`, `standards.py`, `sweep.py`, `verify_math.py`,
`weave_index.py`. None of these calls `health.record`, `logging`, `print`, `raise`, or
`silence.note` — the assignment is a no-op dummy string, and `silence.py` itself contains **no
recognition of `silence-exempt` as a real keyword** (confirmed: neither `silence.py` nor
`verify_math.py` references the literal string `"silence-exempt"` as logic, only inside these
same dummy comments/strings). The entire convention works purely because the word "silence"
happens to be both (a) one of the eight substring triggers and (b) the natural word a developer
would write to explain "this is deliberately silent." If the substring-match bug were fixed
without also giving `silence-exempt` real recognition, all 40+ of these deliberately-documented,
legitimately-silent handlers would flip to being reported as SILENT by `audit()` — the opposite
of what their authors intended and documented.

Separately, this also means the check can produce **false negatives in the other direction**: a
genuinely silent handler that happens to sit inside a function whose docstring mentions any of
these eight common English words ("log", "print", "record"...) anywhere in its `ast.dump` — e.g.
a nested lambda default, an f-string containing "logged", a dict key named `"raise_on_error"` —
would also read as "observed" with nothing actually recorded. (Scanned specifically for this: no
other live instance beyond the `silence-exempt` idiom was found in the current tree, but the
mechanism is not scoped to that idiom.)

**Fix:** restrict the trigger-word check to identifiers actually called or referenced in the
handler's statements (`ast.Name`/`ast.Attribute`), not to arbitrary substrings of the dumped
tree text — and give `silence-exempt` (or an equivalent) explicit, intentional recognition as its
own third category, separate from "observed-via-recording", since a deliberately-silent handler
and a recording handler are not the same thing and currently both count as "not silent" by
accident.

### 2.3 MEDIUM — `_handlers()` returns `[]` for a file that fails to parse, indistinguishable from a file with zero handlers — `silence.py:117-122` — **REPRODUCED** (by code inspection; confirmed no compensating signal exists)

```python
try:
    with open(path, encoding="utf-8") as f:
        src = f.read()
    tree = ast.parse(src)
except Exception:
    return []
```

A syntactically broken module (or one with a transient read failure) is reported by `audit()` and
`main()` identically to a module that genuinely has no exception handlers at all — the summary
counts silently exclude it rather than flagging it. `main()`'s top-level report has no "N files
could not be parsed" line anywhere, so a module dropping out of the audit entirely (e.g. mid-edit,
or hit by the exact 0x08-escape corruption this project has been bitten by repeatedly per this
file's own docstring) looks like a clean pass, not a gap. This is the file whose entire purpose
is to make swallowed failures visible, doing the same thing to its own scan.

**Fix:** track and report parse failures as their own bucket (count + filenames), distinct from
"0 handlers found."

### 2.4 MEDIUM — `swallow.__exit__` (`:99-112`) swallows a failure of `health.record` itself with a bare `pass`, and nothing downstream is told the failure went unrecorded — `silence.py:107-111`

```python
try:
    import health
    health.record(f"{self.kind}:{exc_type.__name__}", self.detail)
except Exception:
    pass          # the recorder itself must never be the thing that breaks a run
```

The comment states the design intent correctly (a broken recorder must not crash the caller) but
the consequence is that if `health.record` itself fails — a corrupt `_SAMPLES` ring, an import
error in `health.py`, a threading issue in `_LOCK` — the *original* exception that `swallow` was
protecting against is now recorded nowhere at all, and nothing else in the process learns that
the recorder is broken. This is a deliberate, reasoned tradeoff (matching `note()`'s identical
pattern at `:321-322`, which has the same shape and the same one-line justification), so it is
not miscategorized code — but it means the one specific failure mode "the recorder is itself
broken" is structurally invisible everywhere `swallow`/`note` are used, for the life of the
process. Worth a periodic self-check (e.g. `health.py` import succeeding at process start) rather
than only discovering it when every subsequent failure across a multi-hour run goes unrecorded.

### Stale statistic (LOW, cosmetic)
The module docstring's "There are 45 such handlers in this tree" (dated 2026-08-21/22) is stale:
running `silence.audit()` against the current tree returns **84** silent handlers by the tool's
own (flawed — see 2.1/2.2) logic. Framed as historical narrative in the docstring, not a
contradiction of current code, but worth updating given how load-bearing the number is
rhetorically.

### Clean
`replace_retry` (`:223-240`) and `write_json` (`:250-287`) are both correct: PID+thread-qualified
temp names avoid the same-name-temp collision class this project has been bitten by elsewhere,
`write_json` cleans up its temp file on a failed dump before re-raising, and both correctly
report (never silently swallow) a denied rename via their boolean return. `note()`'s atexit-arm +
periodic-flush logic (`:301-322`) is sound. `instrument()`'s bottom-up line rewriting to keep
earlier offsets valid, and its parse-after-rewrite verification (`:410-414`) before ever touching
disk, are both correct and were exercised mentally against the one-line-suite (`except X: pass`)
special case at `:398-405`, which correctly splits the suite rather than corrupting it.

---

## 3. `src/foreman.py`

### 3.1 HIGH — `_retire()` bypasses the merge/reconcile discipline `overwatch.py` built for the exact same file, reintroducing the lost-update race `overwatch.save()` was hardened against — `foreman.py:1026-1052` — **REPRODUCED by code inspection of both write paths**

`overwatch.py`'s own `save()` (the module that owns `data/OVERWATCH.json`) does a documented,
deliberate merge-before-write specifically because two processes hold this ledger at once (m40,
referenced in its docstring: "an orphaned 09:02 call... was one return away from wiping four
findings and regressing the round counter"). `_merge_ledgers`/`_reconcile_with_disk` implement
that.

`foreman._retire()` writes the same file through a completely independent path:

```python
with open(path, encoding="utf-8") as f:
    led = json.load(f)
for fid, v in (led.get("findings") or {}).items():
    if (...match...):
        v["state"] = "retired"
tmp = path + ".tmp"
with open(tmp, "w", encoding="utf-8") as f:
    json.dump(led, f, indent=1, sort_keys=True)
silence.replace_retry(tmp, path)
```

This is a naive read-modify-write of the *whole ledger*, with no call into `overwatch`'s merge
logic (confirmed by grep: `foreman.py` never imports `overwatch`, and `_reconcile_with_disk` /
`_merge_ledgers` have no caller outside `overwatch.py` itself). If `overwatch.py`'s standing
`--loop` job writes a fresh round of findings between `_retire()`'s read and its write, `_retire`'s
write clobbers them with the stale snapshot it read — plus one retirement flag — exactly the
class of loss `overwatch.save()`'s docstring says it was built to prevent, now reintroduced by a
second, independent writer of the identical file. `silence.replace_retry` makes the *individual*
write atomic (no torn file), but atomicity does not prevent a whole-file overwrite from discarding
a concurrent writer's update — that is a distinct hazard from the one `replace_retry` solves, and
CLAUDE.md's own INDEPENDENT principle ("no two layers may share a failure mode... two layers
enforcing *different* invariants is not defence in depth, it is one layer and a decoy") names
this exact shape.

**Fix:** route `_retire()`'s write through `overwatch.save()` (which already merges), or at minimum
`overwatch._reconcile_with_disk()`, rather than a bespoke read-modify-write.

### 3.2 MEDIUM — `triage_swallowed()`'s unconditional `{}` clear races `health.flush()`'s concurrent read-modify-add-write of the same file — `foreman.py:221-283` vs `health.py flush()` — **HYPOTHESIS, reasoned from both code paths, not executed concurrently**

`health.flush()` (called "every 25 records and again at exit, from every one-shot subprocess in
the kit" per its own comment) reads `state/failures.json`, adds its in-memory counts on top, and
writes the merged result back — a correct additive read-modify-write. `foreman.triage_swallowed()`
reads the same file, archives its contents, then writes a **bare `{}`** to it regardless of what
is on disk at that moment:

```python
with open(path + ".tmp", "w", encoding="utf-8") as f:
    json.dump({}, f)
if not silence.replace_retry(path + ".tmp", path):
    ...
```

If any process's `health.flush()` lands between `triage_swallowed`'s read (top of the function)
and this write, that flush's freshly-persisted counts are silently discarded by the `{}` — not
archived (they weren't present in the snapshot `triage_swallowed` read), not reported, simply
gone. Given `health.flush()`'s stated call frequency across many concurrent one-shot subprocesses,
this is a real, if narrow, window. This function's own comments show the author already fixed two
adjacent variants of "check the write actually landed" here (see the extensive m18/run#19
commentary at `:250-283`) but did not address this specific blind-overwrite-vs-concurrent-append
race.

**Fix:** re-read the file immediately before the `{}` write (or better, subtract only the
already-archived keys/counts rather than replacing wholesale), so a flush landing in the gap is
preserved rather than erased.

### 3.3 MEDIUM — five `silence.note()` tags carry line numbers stale by 164–316 lines — `foreman.py:661,827,1099,1242,1283` — **REPRODUCED**

```
661:            silence.note("foreman.py:497")     # actual line 661, stale by 164
827:        silence.note("foreman.py:595")         # actual line 827, stale by 232
1099:        silence.note("foreman.py:824")        # actual line 1099, stale by 275
1242:        silence.note("foreman.py:942")        # actual line 1242, stale by 300
1283:            silence.note("foreman.py:967")    # actual line 1283, stale by 316
```

These tags are the ONLY identifying detail the failure-ledger sample carries for these five sites
(`health.record(f"silent:{site}", ...)` — the site string IS the diagnostic key). Every other
`silence.note()` call in this file uses a descriptive tag (`"foreman.py:attempt_patch-apply"`,
`"foreman.py:round-log-denied"`, etc.) that survives refactoring; these five are the only ones
using a bare line number, and all five have drifted as the file grew, presumably from edits made
above each site after the tag was written. A future grep for "line 497" to find the site described
in `state/failures.json` lands on `run_charter_regression`'s `POOL_PROOF.json` read, not wherever
line 497 used to be.

**Fix:** replace all five with descriptive tags matching the file's own prevailing convention
(e.g. `"foreman.py:charter-regression-pool-read"`, `"foreman.py:literals-parse-fail"`,
`"foreman.py:scout-blocked-load"`, `"foreman.py:round-log-load"`,
`"foreman.py:keyboardinterrupt"`).

### 3.4 LOW — dry-run prints every remedy in a list as "would run", but a live run stops at the first success — `foreman.py:1156-1161` vs `:1194-1207` — **REPRODUCED by code inspection**

```python
for fn in remedies:
    if dry:
        print(f"   AUTO   {o['standard']} -> would run {fn.__name__}")
        log["auto"].append(...)
        continue
    ...
    if did and not getattr(fn, "always", False):
        ...
        break
```

In dry mode the loop always `continue`s, so every remedy in a standard's list is printed as
"would run" every round. In a live run, the first remedy that returns `did=True` breaks the loop
(remedies are "alternatives" by design, per the extensive comment at `:1181-1193`), so for any
standard with 2+ remedies (`"calls that succeed": [clear_learned_caps, reprove_pool]`, etc.) a
dry run systematically over-reports what a live run would actually do — it cannot do otherwise,
since dry mode never calls `fn()` and so has no `did` to branch on. This is an inherent limitation
rather than a fixable logic error, but it means the tool's own `--go`-less preview is not a
faithful preview of `--go` behavior, and nothing in the printed output says so.

**Fix:** either note in the dry-run banner that later remedies in a list may not run once an
earlier one succeeds, or (cheaper) print only the first remedy per standard in dry mode to match
what a typical live round would attempt.

### Clean
The `DENYLIST` / `MAX_PATCH_LINES` / `_checks_pass` / `lines_changed` / `regex_touched` model-patch
gates are all correctly wired and match their docstrings' claims about what was previously broken
and is now fixed (the `"0 FAILED"` substring bug, the `abs(len(new)-len(old))` net-delta bug, the
missing `import ast` NameError) — read closely for a repeat of any of those three specific classes
and found none. `attempt_patch`'s backup-then-revert-on-failure path correctly distinguishes "the
patch was reverted" from "the revert itself also failed" (`:1013-1021`) and reports the latter
loudly rather than optimistically. `kill_duplicate_jobs`'s refusal to guess a missing creation
timestamp (`:500-506`), and its supervisor/watchdog self-exemption (`:489-499`), are both correct
and match their justifying comments. `owner_queue`'s "every URL, not the first three" (`:1109-1117`)
correctly honors Hard Rule 0 — verified no cap remains on that loop.

---

## 4. `src/cleanup.py`

### 4.1 MEDIUM — `_SETTING_META` guard-tuple entry references a regex that is never defined anywhere in the file; the control-character guard is unconditionally skipped for it — `cleanup.py:77-80` — **REPRODUCED**

```python
for _n, _p in (("_NAV", _NAV), ("_EMPTY_MECHANIC", _EMPTY_MECHANIC),
               ("_SETTING_META", None)):
    if _p is not None and any(ord(c) < 32 for c in _p.pattern):
        raise SystemExit(...)
```

Grepped the whole file: `_SETTING_META` appears exactly once, right here, hardcoded to `None`.
There is no `_SETTING_META = re.compile(...)` anywhere in `cleanup.py`. Because `_p` is `None`,
`_p is not None and ...` short-circuits to `False` for this tuple entry — the check does not run,
cannot fail, and cannot ever raise for it, which is a tautological guard in the sense the lens
asks for: a check that is structurally incapable of catching what it exists to catch. The module's
own header comment two lines above frames this exact block as the fix for "Three regexes in this
project have been silently broken by an escape being eaten in transit," but only two of the three
listed guard entries are wired to a real regex — the third is a name with nothing behind it,
either orphaned from a regex that was removed in a later edit, or a regex that was intended
(`_SETTING_META` reads like a companion to `_NAV`'s "wiki navigation" filtering — perhaps meant to
catch "Setting" / "World" meta-pages) but never written.

**Fix:** either write the missing `_SETTING_META` regex and wire it in for real, or remove the
dead tuple entry so the comment above it doesn't overstate what's actually guarded.

### Clean
The previously-flagged `thin_description` branch not setting `changed` (originally `:178-184`
per an earlier batch's finding) is **already fixed in the current tree** — `changed = True` is
present on that branch, with an inline comment documenting the fix ("run #29, batch 05,
reproduced"). `clean_ceiling`'s three-strategy resolution (exact / head / prefix) correctly
refuses to guess when none land, and its docstring's claim about why a substring strategy was
removed is consistent with the code (no substring strategy present). All record mutation goes
through `PL.write_record` (two-writer contract respected) and only when `changed` is actually
True. The `[:5]`/`[:6]`/`[:4]` slices in `main()`'s printed report are all display-only — the
underlying `for path, rec in PL.records()` loop and the `--apply` writes are unbounded across the
full record set, and the printed `len(...)` counts reflect the true totals, not the truncated
display.

---

## 5. `src/pantheon.py`

No correctness bugs, no swallowed-failure issues beyond a properly-recorded one, no CAP
violations, no committed secrets, no dead code, no stale line-number tags. This is a small,
hand-authored data module (six curated Dragon Ball entities) computed once through `assay.assay()`
and written atomically via `silence.write_json` (two-writer contract respected). The one
`except Exception: silence.note("pantheon.py:merge")` at `:270-271` (failure to load
`Z_FIGHTERS.json` for the combined ranking) is genuinely observed, not a tautology victim — it
calls `silence.note` directly rather than relying on any substring coincidence.

### Clean
Everything. No findings.

---

## 6. `src/feats_index.py`

No correctness bugs found. `feats_for_source()`'s docstring claim "NO CAPS... Ranked, never
truncated" is accurate — verified no `[:N]`/`limit=` on the entity or feats lists it returns; the
only slicing in the file (`pair_shared[(a,b)][:4]`-style patterns do not appear here — this file
has none at all) is absent. `audit()`'s stranded/joined accounting matches the module docstring's
methodology description. `_norm()`'s docstring is unusually careful about correcting an earlier,
wrong claim about itself (it explicitly documents that it does NOT strip parentheticals, contrary
to what an older version of the same docstring said) — exactly the kind of self-correction the
lens is looking for evidence of, not against.

### LOW — `feats_for_source()` iterates the full index per host instead of doing a direct key lookup — `feats_index.py:190-207` (performance, not correctness)

```python
for host in hosts:
    for (h, ent_norm), rec in idx.items():
        if h != host or ent_norm not in entries_by_norm:
            continue
```

This is O(`len(hosts) * len(idx)`) where a direct `idx.get((host, ent_norm))` per
`entries_by_norm` key would be O(`len(hosts) * len(entries_by_norm)`). Not a correctness issue —
the two are equivalent in output — but worth flagging since `load_index()`'s own docstring
motivates the `(host, entity)` dict specifically to avoid a re-walk. Not fixed, since it is out of
scope for a read-only audit; flagged for anyone touching this function next.

### Clean
Otherwise clean. Two-writer contract not applicable (read-only join module, writes nothing).

---

## Summary of severities

| Severity | Count | 
|---|---|
| HIGH | 4 |
| MEDIUM | 5 |
| LOW | 4 |

HIGH: cosmology_graph.py §1.1 (Hard Rule 0, w>=1.0 filter), silence.py §2.1 (uses_exc tautology),
silence.py §2.2 (substring trigger words + silence-exempt convention), foreman.py §3.1 (_retire
second-writer bypass).
