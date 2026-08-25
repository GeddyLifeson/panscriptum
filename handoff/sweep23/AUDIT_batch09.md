# Audit batch 09 — hostcheck.py, manifest_builder.py, tiers.py, navtree.py, style_audit.py, retry_synthesis.py

Full line-by-line read of all six files. Findings below, per module.

---

## hostcheck.py (956 lines) — read in full

### Confirming the two pre-filed findings

**hostcheck.py:134-139 — RAW-MODE probe() returns rate=0.0 with no error key on network failure — VERIFIED**

```python
if EP.detect(host)["mode"] == EP.MODE_RAW:
    got = EP.fetch_raw(host, names[:12])
    n = min(len(names), 12)
    return {"host": host, "probed": n, "hits": len(got),
            "rate": round(len(got) / n, 3), "examples": sorted(got)[:5],
            "titles": sorted(got)}
```

`EP.fetch_raw` presumably returns `{}` (or a partial dict) both when a fetch genuinely finds
nothing AND when every request errored/threw — there is no try/except here at all, so any
exception inside `fetch_raw` propagates instead of being caught, OR (if `fetch_raw` itself
swallows per-title fetch errors, which is plausible given the naming) an all-failed batch comes
back as `got == {}` and this returns `rate: 0.0` with no `"error"` key. Compare directly to the
batched-API branch immediately below (:146-155), which explicitly catches the exception and
writes `"error": f"{type(e).__name__}..."`, rate `None`. The RAW branch has no equivalent
try/except around `EP.fetch_raw(...)`, so a network failure on a raw-mode host either crashes
the whole sweep (uncaught) or — if `fetch_raw` itself is defensive — reports indistinguishably
from "this wiki holds none of these names," exactly the defect this module's own docstring says
it exists to catch. Given `score()` treats `rate=0.0, no error key` identically to a genuine
zero-hit probe (there's no `"error"` check anywhere in `score()`), this branch is not held to
the same standard as its sibling. **Confirmed as filed** — HIGH, since this is the exact
mechanism by which a reachable host could fail to be adopted (a raw-mode wiki throttled or
briefly down reads as "holds nothing").

**hostcheck.py:150-155 — batched-API branch handles the same case correctly — VERIFIED**

```python
except Exception as e:
    silence.note("hostcheck.py:probe")
    return {"host": host, "probed": len(names), "hits": 0, "rate": None,
            "error": f"{type(e).__name__} {str(e)[:60]}"}
```

`rate: None` (not 0.0) plus an explicit `error` key. `score()` (:469-471) checks `if rate is
None:` first and sets `verdict = "UNREACHABLE — no judgement"`, which `sweep()`'s repair loop
explicitly excludes from the wrong-fiction/repair set (:516-521, `JUDGED` tuple) and `adopt()`'s
scan treats as "not ok" (verdict not in `("holds","partial")`) without ever counting it as a
rejection. Correct handling, confirmed.

**Consequence for the RED 93% standard**: `adopt()` (:846-910) is the tool that assigns hosts to
the 15 currently-hostless sources. If any of their `candidates()` include a raw-mode wiki (Fandom
wikis that have closed their API — `EP.MODE_RAW`) and that wiki is transiently unreachable during
the run, `probe()`'s RAW branch reports a false zero instead of an honest unreachable, `score()`
marks it `"WRONG FICTION"` or leaves it out of consideration entirely rather than retriable, and
a genuinely reachable host is silently rejected instead of adopted. This directly matches the
brief's HIGH-severity criterion.

### Other findings

**hostcheck.py:59-60 and silence.py:74-75 — self-mutilation guard, informational, not a bug — VERIFIED (clean)**
Both files read their own source at import time checking for four control characters that a
past encoding-in-transit accident introduced. Harmless, deliberate, documented. No action.

**hostcheck.py:66-79 `_land()` — correct use of `silence.replace_retry` — VERIFIED clean.**
Every shared-file write in this module (`OUT`, `UNFIT`, `F.HOSTS`, `ROSTERS`, `PURGED`, per-record
files in `purge()`) goes through `_land()`, which does tmp-write + `silence.replace_retry`. This
module was the one explicitly named in its own docstring (:66-79) as the post-2026-08-24 fix for
the truncate-then-fill defect — confirmed it was actually applied everywhere in this file, not
just claimed. Clean.

**hostcheck.py:707 `purge()` direct write to catalogue records — correctly justified, not a
violation — VERIFIED.** The comment explains this is deliberately NOT
`pipeline.write_record_catalogue` because that writer merges/grows entries and a purge needs to
shrink one; the write goes through `_land()` (atomic) instead of a bare open. This is a
considered, documented exception to the "write via pipeline.write_record_catalogue" rule, landed
atomically. Acceptable — the two-writer contract's concern is atomicity + not racing the growth
path, both respected here.

**No caps found beyond the two already-known limiters (`PROBE=40`, `sample=12` in `relevance()`,
`sample=40` in `null_rate()`).** These are all diagnostic/measurement sample sizes for a fitness
*test*, not truncations of an ordered *listing* being delivered to the library — `probe()`
explicitly documents PROBE=40 as "One API call takes 50; forty leaves room for redirects," a
batch-size choice for a single round-trip, not a ranked-then-cut roster. `candidates()` (:264-368)
was explicitly rewritten (with its own docstring calling out the exact Hard-Rule-0 shape of the
old bug) to NEVER slice the grounded candidate list — confirmed clean by inspection: `spec` (the
speculative subdomain guesses) has no visible truncation in `candidates()` itself either; it's
capped implicitly only by how many tokens/suffixes exist, not by an artificial `[:N]`.

**CLEAN beyond the two confirmed items above.** No swallowed-failure bugs beyond the RAW-mode gap
already covered; every `except Exception` in this file calls `silence.note(...)` before
returning (grep confirms: :148-155, :380-382, :572-573, :692-694, :727-728, :767-768, :803-804).

---

## manifest_builder.py (478 lines) — read in full

**manifest_builder.py:436, :455, :463 — non-atomic writes of output/index/manifest.json and
unassigned_sources.md — VERIFIED, not via silence.write_json/replace_retry.**

```python
with open(out_path, "w", encoding="utf-8") as f:
    json.dump({"jobs": all_jobs}, f, indent=2)
```
and the two `report_path` writes at :455 and :463 (same bare pattern). None of these three sites
import or call `silence.write_json`/`silence.replace_retry`; `manifest_builder.py` never imports
`silence` for writing at all (only imports `silence` for the swallowed-exception recorder at
:319). This is the exact shape the project's own `silence.write_json` docstring calls out
("TWELVE call sites... writing shared data/ and state/ files with a bare open(path,'w') +
json.dump"), except these three targets are under `output/index/`, not `data/` or `state/`.

Severity assessment: LOWER than the `data/`-tier findings. `manifest_builder.py` is a one-shot,
single-process CLI tool (not threaded, not run by ThreadPoolExecutor workers), so there is no
in-process race. The residual risk is (a) a crash mid-`json.dump` leaving `manifest.json`
truncated for the NEXT reader (`generate.py`), and (b) a concurrent `generate.py` run holding
`manifest.json` open for read while this script rewrites it — on Windows this is the same
`PermissionError` class `replace_retry` exists to survive, but here a crash would just raise
uncaught rather than fail with an honest, recorded denial. **VERIFIED as present, MEDIUM
severity** (real deviation from the now-established convention on a file that is read
downstream, but not on the `data/`-tier hot path and not concurrently written).

**manifest_builder.py:68-104 `load_record()` — CLEAN, well-reasoned fuzzy-match logic —
VERIFIED.** The bidirectional substring/prefix match with closeness-ranking is exactly what its
own comment claims: exact match wins, then smallest length delta; the reverse arm is anchored
with `.startswith()` (prefix only), preventing the false-positive containment bug it explicitly
documents ("DC" matching "sword-coast-adventurer-s-guide"). Traced through: `norm_target in
norm_fname or norm_target.startswith(norm_fname)` — the first arm is free containment (target
found anywhere in filename), the second is anchored (filename is a literal prefix of target).
Correct as described.

**manifest_builder.py:146-217 `pack_feats()` — CLEAN, genuinely a pagination not a truncation —
VERIFIED.** Every feats row is either packed into a block under budget or, if oversized, sliced
across as many blocks as needed with an explicit `feat_span` field (:173-174, :203, :213) — no
`[:N]` anywhere drops data. The "flush before exceeding, not after" fix (:192-199) is correctly
implemented: the `if slice_ and cost(slice_ + [f]) > budget` check runs BEFORE appending `f`, so
a slice never silently overshoots by absorbing one deed after the check. Traced correctly.

**manifest_builder.py:332-337 — `budget <= 0` raises `ContextOverflow` rather than silently
proceeding with a clamped tiny budget — VERIFIED clean, matches Hard Rule 0's spirit (loud
failure over silent truncation).**

**manifest_builder.py:376-390 — pilot/only filtering — CLEAN, not a Hard-Rule-0 violation.**
`build_pool = sorted(...)[:args.pilot]` (:390) truncates, but only when `--pilot N` is explicitly
requested by the operator as a deliberate small test run (per CLAUDE.md's own instructed
workflow: "Pilot before you scale"). This is a user-requested sample, not a silent cap on the
full-manifest path (`args.pilot` defaults to 0 / falsy, in which case this branch never runs).
Not a finding.

**manifest_builder.py:405-422 — Volume-number assignment for multi-source Series codes — CLEAN,
verified correct.** Deterministic sort by name, documented as non-curatorial, addresses a real
prior collision bug (303 duplicate addresses). No cap involved.

**No swallowed-failure issues** — the one `except Exception` at :318-320 (`feats_index.feats_for_source`) correctly calls `silence.note()` before falling back to an empty list, and an empty feat list is a legitimate "this source has no feats chapter" outcome (not conflated with any other state).

---

## tiers.py (347 lines) — read in full

**CLEAN.** No writes other than the final `silence.write_json(out, charted, ...)` at :341, which
the file's own comment notes was deliberately fixed to match `pipeline.py`'s `land_json` pattern
on 2026-08-25 (bug m6) — verified this is genuinely atomic via `silence.write_json`, not a bare
open. No caps on real data: `unaddressed[:6]` at :298 is a console print preview only (the full
`unaddressed` list and its `len()` are used for the actual reported count; only the sample printed
to stdout is sliced) — this is diagnostic output, not a truncation of a listing being persisted
or delivered downstream, matching the brief's own carve-out for "bounds a diagnostic/preview."
Similarly `deliberate_joins()`'s `shared.get((a,b), [])[:3]` (:273) truncates only the *example*
entity names printed alongside a link-strength row for human readability in `main()`'s printed
report (:325) — the underlying `shared` dict and `w` dict driving all real clustering/tier
assignment are never sliced. The clustering logic itself (`_components`, `chart`,
`xenoverse_grounding`) processes every source and every link with no `[:N]` anywhere. Threshold
math (`MULTIVERSE_THRESHOLD >= CUTS[0][1]`, cuts loosen downward) is asserted at import time and
verified consistent (102.3 ≥ 100.0 ≥ 50.0). The tie-break fix at :162-168 and :178-180 (secondary
sort key on register/grounding name, avoiding Python's hash-randomized `set()` iteration order) is
correctly applied in both call sites that needed it. No findings.

---

## navtree.py (270 lines) — read in full

**navtree.py:260 — non-atomic write of data/NAVTREE.json — VERIFIED, confirms the pre-filed
finding.**

```python
if args.write and not problems:
    with open(OUT, "w", encoding="utf-8") as f:
        json.dump(data, f, separators=(",", ":"), ensure_ascii=False)
```

`navtree.py` imports `silence` (line 30) and uses `silence.note()` correctly at :67, :121, :127
for its three read-side `except Exception` handlers, but the write at :260 is a bare
`open(OUT, "w")` + `json.dump`, not `silence.write_json`/`replace_retry`, despite `silence`
already being imported into this exact module. This is the clearest case in the batch of a file
that had every tool it needed already in scope and simply didn't use it for the write. `NAVTREE.json`
is explicitly the terminal's navigation data (per the module docstring, feeds the registry
terminal), so a reader (the terminal, or any dashboard) holding it open during a `--write` run
risks the same Windows `PermissionError` class `replace_retry` exists to survive — and unlike
`replace_retry`, a bare `os.replace`-free `open(...,"w")` here doesn't even attempt a
temp-file swap; it truncates `OUT` directly in place, so a crash mid-`json.dump` (or a
`PermissionError` from `os.makedirs`/open itself, though less likely) leaves the file exactly
as truncated. **Confirmed as filed, VERIFIED, and worse than a typical tmp+bare-replace
site** — this one doesn't even stage a tmp file first. **HIGH** given this is the terminal's
production navigation data and the file is gated behind an `audit(data)` pass specifically to
guarantee correctness before writing (:259) — that correctness guarantee is undermined by the
write itself being unsafe.

**navtree.py:153 — the `+ "."` fix in `sources_under()` — VERIFIED correct.** Traced the boundary
condition described in the comment: `path.startswith(key + ".")` and `key.startswith(path +
".")` both require a literal dot after the shorter string, so "0.1.2" cannot match as a
false-descendant of "0.1.20" (would need "0.1.20." as a prefix of "0.1.2", which it is not, and
"0.1.2." is not a prefix of "0.1.20"). Correct.

**navtree.py:99 — "No cap: a universe lists every world it holds" — VERIFIED true.** `touch(path)["w"].append(...)` for every world in `worlds.items()`, no slicing anywhere in the loop (:100-109). Confirmed against the docstring's Bug #2 (worlds truncated at 40) — genuinely fixed, no cap present.

**No other findings.** `audit()` (:210-223) is a real consistency check (children-sum-to-parent, orphan-child detection) gating the write, and is itself correct by inspection.

---

## style_audit.py (211 lines) — read in full

**CLEAN — pure read/report tool, no shared-file writes at all.** `style_audit.py` never writes
any JSON or shared state; it only reads generated `.md`/`.txt` output files and prints a report
to stdout. All apparent "caps" (`report(a, top=8)`'s `most_common(top)` at :143 and :148,
`[:14]` at :157, `most_common(10)` at :172) operate on `collections.Counter` objects that were
built by scanning the FULL corpus with no truncation anywhere in `audit()` (:104-133) — every
entry, every banned-pattern hit, every vocabulary word across every file is counted. Only the
human-readable top-N *printout* of an already-complete aggregate is sliced, which is squarely
the brief's own carve-out ("merely bounds a diagnostic/preview"). Confirmed by reading `audit()`
in full: `for t in texts: for e in entries(t): ...` iterates unconditionally over everything
passed in, and `main()` (:195-196) globs `**/*.md` and `**/*.txt` recursively with no head/limit
on the file list either. Self-test (:183-193) is a real, non-trivial check that the detector
actually fires on synthetic repetition, not a rubber stamp. No findings of any kind in this
module.

---

## retry_synthesis.py (152 lines) — read in full

### Confirming the pre-filed finding, WITH an added dimension not in the filing

**retry_synthesis.py:60 — `sorted(...)[:14]` truncates the sample fed to synthesis — VERIFIED, HARD RULE 0, and additionally: the docstring's claim of parity with the main pipeline is FALSE.**

```python
def synthesise(c, rec):
    """Byte-identical prompt construction to phase_synthesis, so a retried source is not
    scored by a different method than its neighbours."""
    src = rec["source"]
    sample = sorted(rec["entries"], key=lambda e: -len(e.get("description", "")))[:14]
```

This is confirmed as filed: a straight `[:14]` slice of a description-length-sorted list, one
sample, one model call — any entity outside the top 14 longest descriptions is never nominated
for ceiling/magnitude, for these 12 already-failed sources (Dragon Ball Z and Dune among them).

**Beyond the filed severity, I traced `pipeline.py`'s actual current `phase_synthesis`
(pipeline.py:621-706) and the docstring's claim is contradicted by the code it claims to
mirror — this is a Lens-6 finding (comment contradicts code) layered on top of the Lens-3
finding.** `phase_synthesis` was explicitly rewritten under "BUGS m13, Hard-Rule-0-shaped, ruled
by the owner 2026-08-24: FIX IT ALL" (pipeline.py:653-660) to:
  1. Rank by **feats present**, not by raw description length (`with_feats = [e for e in
     rec["entries"] if feats_for.get(e["name"])]`, pipeline.py:651-652) — feats being the actual
     evidence a ceiling nomination needs, per the same file's own comment about the
     99.6%-unassayed lesson (pipeline.py:637-641).
  2. **Paginate ALL feat-bearing entries in chunks of 14** (pipeline.py:673,
     `chunks = [with_feats[i:i+14] for i in range(0, len(with_feats), 14)] or [rest[:14]]`),
     issuing one model call per chunk and keeping the best (highest) band across every chunk
     (pipeline.py:674-698) — explicitly so that "no feat-bearing entry is ever excluded from
     nomination" (pipeline.py:657-659).

`retry_synthesis.synthesise()` (:56-91) does neither: it sorts by raw `description` length (not
feats), takes exactly one slice of 14, and makes exactly one model call — this is precisely the
OLD, pre-m13-fix method that `phase_synthesis` was rewritten specifically to stop doing. The
docstring's assertion that this is "byte-identical... so a retried source is not scored by a
different method than its neighbours" is the opposite of true: these 12 retried sources
(explicitly named as including Dragon Ball Z and Dune — both large-cast, feat-rich sources where
the true ceiling entity is plausibly outside the top-14-by-description-length) are scored by a
strictly weaker, already-abandoned method, and could receive a lower/wrong magnitude band or a
wrong `ceiling_entity` than a fresh run of the real `phase_synthesis` would give them, with the
result then merged into their permanent records via `do_merge()` and never revisited (per the
module's own docstring, "the pipeline will never revisit them on its own"). **VERIFIED, HIGH** —
this is a comment that actively misdirects anyone checking whether the retry path is safe to
merge, on exactly the sources the retry exists to fix correctly.

### Second class of finding: this module's own writes bypass the project's atomic-write convention

**retry_synthesis.py:43-47 (`save_side`) and :109-112 (`do_merge`'s per-record write) — both use
a bare `tmp = path + ".tmp"` + `os.replace()` pattern, never importing or calling
`silence.write_json` / `silence.replace_retry` — VERIFIED, `silence` is not imported anywhere in
this file (confirmed via `import` grep: only `argparse, json, os, re, sys, pipeline`).**

```python
def save_side(d):
    tmp = SIDE + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(d, f, indent=2, ensure_ascii=False)
    os.replace(tmp, SIDE)
```
and, in `do_merge()`:
```python
rec["synthesis"] = side[src]
tmp = path + ".tmp"
with open(tmp, "w", encoding="utf-8") as f:
    json.dump(rec, f, indent=2, ensure_ascii=False)
os.replace(tmp, path)
```

Two distinct gaps versus `silence.write_json`/`replace_retry`:
  1. **No PID/thread-tagged tmp name.** `silence.write_json`'s docstring explicitly calls this
     out as a fix for a real observed race ("Two writers of the same path otherwise collide on
     the temp file itself"). Here the tmp name is the bare `path + ".tmp"`.
  2. **No retry-on-`PermissionError`.** `silence.replace_retry`'s whole reason to exist is that
     "on Windows the rename is DENIED while any reader holds the target open" and this project's
     state files "all have readers on their own clocks." A bare `os.replace()` here will raise
     uncaught if any reader (a dashboard, `catalog.py`, another `pipeline.py` phase) has the
     target open at the exact moment of replace.

Severity split by target:
  - `save_side()` writing `SYNTHESIS_RETRY.json` (:33): this file is explicitly documented as
    single-writer, sequential (this script's own `main()` loop, never threaded) and touched by
    "nothing else" per the module docstring (:18) — so the PID/thread-collision risk is low, but
    the reader-holds-it-open risk is real if e.g. a human or a dashboard tails the file while the
    retry loop is running. **MEDIUM.**
  - `do_merge()` writing `data/records/*.json` (:109-112) is the SAME class of file
    `pipeline.py`'s own `write_record`/`write_record_catalogue` normally own exclusively (per
    this module's own opening docstring, "The pipeline... read-modify-writes data/records/*.json
    as phase 2 bands each source"). `do_merge()` is explicitly gated to "Run ONLY when the
    pipeline is stopped" (:95), so the concurrency half of the two-writer contract is honored by
    operator discipline rather than by code — but the write itself still isn't going through
    `pipeline.write_record`/`write_record_catalogue` OR `silence.write_json`; it's a third,
    independent bare-write path onto a file class the project otherwise funnels through exactly
    two writers. If `--merge` is ever run while the pipeline is NOT actually stopped (operator
    error, no code-level guard against it — I checked, there is no PID/lockfile check anywhere in
    `do_merge()` or `main()`), this becomes an unguarded read-modify-write racing
    `pipeline.py`'s own record writer on the identical file, with neither side's tmp file
    protected against the other. **VERIFIED as a real code-level gap; HIGH** given it writes
    directly into the two-writer-contract's protected file class with no runtime enforcement of
    the "pipeline must be stopped" precondition it depends on — a documented human protocol, not
    a checked one.

**retry_synthesis.py:50-53 `failed_sources()` — CLEAN.** Reads `PIPELINE_STATE.json` directly
(read-only), no write, no cap on the returned failed-source list.

**retry_synthesis.py:126-146 `main()` — CLEAN control flow**, correctly re-checks `side` and
`not r.get("synthesis")` before adding each source to `todo` (:131-132), so a source that gets a
synthesis block written by the live pipeline between runs is correctly skipped rather than
double-processed.

---

## Summary table

| Location | Severity | Status |
|---|---|---|
| hostcheck.py:134-139 | HIGH | VERIFIED — confirms filed finding |
| hostcheck.py:150-155 | — | VERIFIED correct (confirms filed finding, no bug) |
| manifest_builder.py:436,455,463 | MEDIUM | VERIFIED — non-atomic writes, single-process, lower risk |
| navtree.py:260 | HIGH | VERIFIED — confirms filed finding, worse than typical (no tmp-file staging at all) |
| retry_synthesis.py:56-60 | HIGH | VERIFIED — confirms filed finding + docstring is factually false vs. current pipeline.py |
| retry_synthesis.py:43-47, 109-112 | MEDIUM/HIGH | VERIFIED — bypasses silence.write_json/replace_retry entirely; do_merge's record write has no runtime guard against the pipeline actually running |
| tiers.py | — | CLEAN, no findings |
| style_audit.py | — | CLEAN, no findings |
