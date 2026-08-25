# AUDIT — BATCH 15 — run32

Modules read in full (every line):
- overwatch.py — 724 lines
- build_terminal.py — 579 lines
- manifest_builder.py — 478 lines
- worldseed.py — 327 lines
- feats_index.py — 263 lines
- catalogue_codex.py — 215 lines
- snapshot.py — 175 lines

Total: 2,761 lines.

---

## BLOCKING

### 1. overwatch.py:369-378, :421-430, :647-648 — HEADLINE LEAD, CONFIRMED
`_ask()` (348-380): on a busy GPU, `_LOCAL_BUSY[0] += 1` then, once `_LOCAL_BUSY[0] > CLOUD_BUDGET`
(line 370), returns `None` (line 378) with **no cloud fallback** — this is correct per the
comment's intent ("the watcher yields"), but the consequence is not handled anywhere downstream.

`review()` (412-431) absorbs that `None` silently: `got or {}` → `{}` → `.get("findings", [])` →
`[]` (line 423-424). A slice that got no model response is indistinguishable from a slice that
was genuinely read and found clean — same empty list either way.

`round_once()` (591-673) then does, unconditionally after `review()` returns without raising
(lines 647-648):
```
d = _digest(os.path.join(SRC, m + ".py"))
led["seen"][m] = {"digest": d, "at": time.time()}
```
This happens regardless of how many of the module's slices actually got a real answer. So a
module whose review was entirely (or mostly) budget-starved still gets a **fresh digest and a
fresh timestamp** recorded as "seen."

Consequence, traced into `rotation()` (504-521): the next round computes `stale` as
`(prev.get("at",0), m)` tuples sorted ascending, so a module with a just-refreshed `at` goes to
the **back** of the re-review queue — behind every module that has gone longer without a
(real-or-fake) review. If a busy-GPU stretch coincides with a module's turn in `todo`
(line 637), that module can be marked reviewed, contribute zero findings, and be pushed to the
back of the line every time its turn comes up again during a busy period — a plausible path to
permanent starvation with the ledger reporting it as covered. Confirmed exactly as briefed:
partial coverage during a busy GPU is structurally indistinguishable from a full clean pass in
the persisted state.

Note: `verify_open(led, local=local, budget=limit)` runs *before* the module loop (line 632) and
draws on the same shared, per-round `_LOCAL_BUSY` budget, so on a busy round it can consume some
or all of the 20-call allowance before any module review even starts.

Severity: BLOCKING (silent, permanent-starvation-capable coverage gap in the tool whose entire
job is guaranteeing coverage).

### 2. worldseed.py:317-321 — two-writer contract violation
```python
if args.write:
    path = os.path.join(HERE, "data", "WORLDSEEDS.json")
    with open(path, "w", encoding="utf-8") as f:
        json.dump({w["designation"]: {"address": address(w), **w} for w in worlds},
                  f, indent=2, ensure_ascii=False)
```
Plain truncating write. No `path + ".tmp"` + `os.replace`, no `silence.write_json`/
`replace_retry` — despite the module already `import silence` (line 65) and using
`silence.note()` elsewhere (250, 258). Matches the reported instance exactly.

### 3. manifest_builder.py:435-437 (and 452-472) — two-writer contract violation
```python
os.makedirs(os.path.dirname(out_path), exist_ok=True)
with open(out_path, "w", encoding="utf-8") as f:
    json.dump({"jobs": all_jobs}, f, indent=2)
```
`manifest.json` / `manifest.pilot.json` written via a plain `open(...,"w")`, no tmp+replace, no
`silence.write_json`, even though `silence` is imported (line 37, used only for `.note()` at
319). Matches the reported instance.

Additional, previously-unreported instance in the **same file**: `output/index/unassigned_sources.md`
is written the identical way at lines 455-461 and 463-472 (two separate plain `open(path,"w")`
blocks). Same hazard, same missing atomicity.

### 4. build_terminal.py:572-573 — two-writer contract violation
```python
with open(OUT, "w", encoding="utf-8") as f:
    f.write(html)
```
`output/registry_terminal.html` is written directly, no tmp file, no `os.replace`, no
`silence.replace_retry` — and this module doesn't even `import silence` (grepped: no hit for
`silence`, `tmp`, or `replace_retry` anywhere in the file). This is a plain truncate-then-fill
write, the exact hazard `overwatch.write_report()`'s own comment calls out by name ("a
truncate-then-fill leaves it empty for the length of the write"). Given as `build_terminal.py:571`
in the brief; confirmed mechanism sits at 572-573.

### 5. snapshot.py:74-75 — two-writer contract violation, in the safety-net module itself
```python
with open(os.path.join(dest, "_manifest.json"), "w", encoding="utf-8") as f:
    json.dump(manifest, f, indent=1, ensure_ascii=False)
```
Plain write, no tmp+replace, no `silence.write_json`, despite `import silence` at line 35 and
its use at line 77. This is the reported "snapshot.py (line unknown)" instance.

### 6. snapshot.py:109-116 — `verify()` does not actually verify directories; contradicts its own docstring
```python
for rel in m.get("took", []):
    a = os.path.join(ROOT, sid, rel.replace("/", os.sep))
    b = os.path.join(tmp, rel.replace("/", os.sep))
    if not os.path.exists(b):
        return False, "restore omitted %s" % rel
    if os.path.isfile(a) and not filecmp.cmp(a, b, shallow=False):
        return False, "restored bytes differ for %s" % rel
return True, "%d path(s) restored and byte-identical" % n
```
`verify()`'s own docstring (94-99) says it "Restore[s] into a TEMPORARY directory and compares
bytes." The comparison line only runs `filecmp.cmp` when `os.path.isfile(a)` is true. When a
snapshot entry is a **directory** (`before()` snapshots whole directories via `shutil.copytree`,
line 68-69 — the module's own worked example is "145 generated chapters", i.e. a directory), the
`isfile` check is False, the byte comparison is skipped entirely, and the only check performed is
`os.path.exists(b)` — true even if the restored directory is missing files, has corrupted files,
or is otherwise not byte-identical to the snapshot. `verify()` then returns
`True, "N path(s) restored and byte-identical"` — a false claim of a check that was never
performed for the case (directories) this module exists to protect. This is precisely the
project's own named failure shape: "a check that cannot fail looks exactly like a check that
passed," inside the one module whose entire purpose is proving a backup is trustworthy before an
irreversible step proceeds.

Fix direction (not applied — audit only): walk the directory with `filecmp.dircmp` or
`os.walk`+`filecmp.cmp` per file rather than trusting `os.path.exists` on the top-level dir.

---

## MAJOR

### 7. snapshot.py:56-60 — second-granularity sid collision (TOCTOU)
```python
sid = "%s-%d" % (str(label or "snap").replace(os.sep, "_"), int(time.time()))
dest = os.path.join(ROOT, sid)
...
os.makedirs(dest, exist_ok=True)
```
`sid` has only whole-second resolution. Two `before()` calls with the same `label` inside the
same wall-clock second collide on an identical `sid`/`dest`. `exist_ok=True` masks the collision
instead of raising, so the second call's file copies land in the first's directory and the second
call's (non-atomic, see #5) manifest write can overwrite the first's `_manifest.json` mid-copy or
after — leaving a manifest whose `took` list doesn't match what the directory actually holds, or
losing the first snapshot's manifest outright. In a module built specifically to guarantee a
trustworthy pre-destruction copy, this is a real race, not a style nit. SUSPECTED as to whether
it's ever hit in practice (depends on caller cadence), but the mechanism is unguarded and
provable by inspection.

### 8. overwatch.py:485-497 — `verify_open` deprioritizes failed re-checks exactly like successful ones
```python
got = _ask(VERIFY_SYSTEM, prompt, VERIFY_SCHEMA, local=local)
f["last_verified"] = time.time()
checked += 1
verdict = (got or {}).get("verdict")
```
`last_verified` is stamped unconditionally, even when `_ask` returns `None` (budget exhaustion,
model timeout, or an unparseable/failed reply — no verdict at all). Since `opens` (line 463-465)
is sorted ascending by `last_verified`/`first_seen`, a finding whose re-check **failed for
infrastructure reasons** is pushed to the back of the queue exactly as if it had been genuinely,
successfully re-verified. Same "an infra failure looks like a success" shape as finding #1, one
level down in the auto-triage lane.

Explicitly checked per the brief's second worry — **the actual closing logic is safe**: only an
exact `verdict == "refuted"` (line 490) closes a finding (491-494); `None`, `"unclear"`, and
`"confirmed"` all leave `state` untouched. A model error, timeout, or unparseable reply cannot
silently close a finding. That specific concern is REFUTED by the code as written.

### 9. catalogue_codex.py:130-137 — unranked substring match repeats an already-fixed bug class
```python
sec_by_norm = {norm(t): t for t in sections}
...
for k, t in sec_by_norm.items():
    if n and (n in k or k in n):
        title = t
        break
```
Bidirectional substring containment, first match in dict-insertion order wins — no
closeness/length ranking. This is structurally identical to the bug `manifest_builder.py`'s own
`load_record()` (lines 72-100 of that file) documents having found and fixed by adding
closeness-based ranking, citing a real incident: unranked substring matching sent source "DC" to
`sword-coast-adventurer-s-guide.json` because "dc" appears inside "swor-D-C-oast". Here in
`catalogue_codex.py`, the identical unranked-substring pattern is used to match a roll source
name against a codex section title, with no such fix applied. SUSPECTED rather than VERIFIED
triggered — the owner's homebrew section titles ("Dr. Firestorm's Engineering Corps", "Draconic
Cult Relics") are fairly distinctive, so a collision may not currently occur — but the exact
footgun the project has already been burned by twice is present, unguarded, in this file.

---

## MINOR

### 10. build_terminal.py:525-528 — unescaped interpolation contradicts the file's own stated rule
```js
<div class="row"><span>landform</span><span>${f.landform||"?"}</span></div>
<div class="row"><span>climate</span><span>${f.climate||"?"}</span></div>
<div class="row"><span>condition</span><span>${f.condition||"?"}</span></div>
<div class="row"><span>era</span><span>${f.tech||"?"}</span></div>
```
The file's own `esc()` comment (80-84) states "Every catalogue-derived string goes through this
before it reaches innerHTML." These four fields are catalogue-derived (`w.f`, sourced from
`worldseed.py`'s `features()`) and reach `innerHTML` via `panel.innerHTML=...` (selectWorld,
512-538) unescaped. Practical risk is low — `landform`/`climate`/`condition`/`tech` are drawn
from fixed closed vocabularies (`LANDFORM`/`CLIMATE`/`CONDITION`/`TECH` tables in
`worldseed.py`), not free wiki text — but the code doesn't enforce that boundary and directly
contradicts its own documented invariant.

### 11. overwatch.py:331, :341 — stale line-number tags in `silence.note()`
```python
except Exception as e:
    silence.note("overwatch.py:193")   # line 331 in the current file
    out["error"] = ...
...
except Exception as e:
    silence.note("overwatch.py:202")   # line 341 in the current file
    out["estate_error"] = ...
```
These two tags are raw line numbers from an earlier revision and no longer match their actual
location (now ~330/340). Every other `silence.note()` call in this file uses a stable descriptive
tag (`"overwatch.py:load"`, `"overwatch.py:digest"`, `"overwatch.py:merge-rounds"`, etc.) — these
two are the only ones that drifted, and a line-number tag is exactly the kind that goes stale
silently as the file is edited around it. Cosmetic (doesn't affect behavior), but will mislead
anyone using the tag to find the call site.

### 12. overwatch.py:324-325 vs 615-616 — `broken_modules` full list is never persisted, unlike `corrupt_files`
`structure()` computes `out["broken_modules"]` fresh every round. `round_once()` explicitly
carries `corrupt_files` forward into `led["last_deep"]` (612-616) so a non-deep round doesn't
report "0" when the truth is "not looked at this round" — but does the same for `corrupt_files`
only, not for `broken_modules`. `write_report()` shows only the first 4 names (line 554) and the
console print (617-618) shows only a count. Past 4, the identities of any additional
import-broken modules are unrecoverable once the round ends — not written to the ledger, not
shown in full anywhere. Not a Hard Rule 0 violation in the strict sense (the displayed count is
always accurate), but it is an avoidable loss of diagnostic detail in the one file whose job is
surfacing exactly this.

---

## NOTE

### 13. overwatch.py:572-573 — `open_f[...][:40]` display cap
`write_report()`'s open-findings list is capped to the top 40 (severity/recency-sorted) in
`WATCH.md`. Judged compliant with the "pure display formatting" exception in the brief: the full,
untruncated set lives in `data/OVERWATCH.json` forever (nothing in this module ever deletes a
finding — see `_merge_ledgers`'s docstring, 236-247), and the report header states the true total
(`f"**{len(open_f)} open** ({len(hi)} high)"`, line 570) before the truncated list. Flagged for
visibility only, not reported as a bug.

### 14. feats_index.py — no defects found
Read in full. The module is unusually well self-audited already: its own docstrings document and
correct three prior mistakes (the URL-join dead end, a false claim about `_norm` stripping
parentheticals, a stranded-feats miscount). No caps (`feats_for_source` is explicitly
"RANKED, NEVER TRUNCATED" and the code matches that claim), no writers (so no two-writer
exposure), and the join logic (`host_to_sources` / `load_index` / `feats_for_source` / `audit`)
traced clean.

### 15. catalogue_codex.py — writer discipline is correct here
Unlike the other six modules in this batch, `catalogue_codex.py` does the two-writer contract
correctly: catalogue records go through `pipeline.write_record_catalogue()` (gated on success,
198-201) and `data/SWEEP_ROLL.json` is written via `silence.write_json()` (209), with an explicit
comment (206-208) noting this was fixed specifically because "Four scripts write this roll."
Noted as a positive control, not a finding.

---

## Summary count
- BLOCKING: 6
- MAJOR: 3
- MINOR: 3
- NOTE: 3
