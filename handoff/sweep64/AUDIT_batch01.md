# sweep64 batch 01 — AUDIT

Scope: `src/drill.py` (23,831 lines as of this read). Read sequentially, start to finish, via the
Read tool in ~1,000-line chunks, line 1 through line 23831 (the `if __name__ == "__main__":`
guard). No sampling, no grep-driven skimming.

Previous audits of this module: `handoff/sweep63/AUDIT_batch01.md` (0 VERIFIED, 0 SUSPECTED, full
sequential read at 23,728 lines) and `handoff/sweep61/AUDIT_batch01.md` (0 VERIFIED, 0 SUSPECTED,
full sequential read at 23,532 lines). This sweep re-read the file in full rather than trusting
either verdict, per the brief's instructions, and gave particular attention to what run #64 added
today (2026-09-26): the module-level `_catalog_matches_disk` helper, the new net "a mutation
sandbox sees the same shelf the live catalog names" in `drill_inspector`, and the addition of
`output/raw` to `_remove_scratch_tree`'s `shared` list.

## Method

Read every line via the Read tool in sequential offset/limit chunks. Cross-referenced the three
items named in the brief against their actual implementation and against the code they depend on
in `src/mutate.py` (the new `output/raw` junction in `mutate.sandbox()`, and `_junction`'s
fail-loud behaviour on a failed junction). Traced `catalog.json`'s `raw_path` field back to its
one production writer (`generate.py:1215`) to determine whether a code path in the new helper that
looks reachable is actually exercised. Re-derived, rather than assumed, the failure scenario for
every candidate finding before writing it down.

## The three items called out in the brief

### `_catalog_matches_disk(root=None)` (drill.py, module level, ~line 12393)

```python
root = root or HERE
cat = os.path.join(root, "output", "index", "catalog.json")
if not os.path.exists(cat):
    return True
d = json.load(open(cat, encoding="utf-8"))
claimed = set()
for rec in d.values():
    p = (rec or {}).get("raw_path") or ""
    p = p.replace("\\", os.sep).replace("/", os.sep)
    if not p:
        continue
    full = p if os.path.isabs(p) else os.path.join(root, p)
    if not os.path.exists(full):
        return False                   # a book the library thinks it has
    claimed.add(os.path.normcase(os.path.basename(full)))
raw = os.path.join(root, "output", "raw")
if os.path.isdir(raw):
    for f in os.listdir(raw):
        if not os.path.isfile(os.path.join(raw, f)):
            continue
        if os.path.normcase(f) not in claimed:
            return False               # a book on the shelf in no catalogue
return True
```

This correctly implements both directions the docstring claims (catalog→disk and disk→catalog),
which is the whole point of the fix it documents. Basename-only comparison in the `claimed` set is
safe given how the sole production writer works: `generate.py`'s `raw_dir` is a flat directory
(`output/raw`, no per-source subdirectories — confirmed by reading `generate.py:1064-1215`), and
every `raw_path` is written as `os.path.relpath(raw_path, HERE)` off `safe_filename(job["address"],
"md")`, which is unique per catalogued address. So two different catalog entries cannot collide on
a basename in practice, and the disk→catalog walk over `output/raw` (also flat) compares apples to
apples.

**QUESTION, not a defect**: `full = p if os.path.isabs(p) else os.path.join(root, p)` takes an
absolute `raw_path` literally, ignoring `root` entirely. If a catalog entry ever carried an
absolute path, calling `_catalog_matches_disk(root=<sandbox>)` would resolve that one entry against
the **live** filesystem regardless of which root was asked about — which would silently defeat the
new net's whole purpose (comparing live vs. sandbox) for that entry. Verified this is not live
today: the only writer of `raw_path` in the tree (`generate.py:1215`) always writes a relative path
via `os.path.relpath`, and every fixture in `drill.py` that builds a `raw_path` also uses a relative
string (`"output/raw/s1.md"` etc.) — grepped across `src/` and found no absolute-path writer. So
this is dead code today, not a live bug, and is filed as a question for whoever owns the module
rather than a fix: is the `os.path.isabs` branch meant to be reachable at all, and if so should it
resolve against `root` too?

### `the_mutation_sandbox_sees_the_shelf_the_live_tree_sees` (drill_inspector, ~line 12462)

```python
import mutate as M
root = M.sandbox()
try:
    live_has = os.path.isdir(os.path.join(HERE, "output", "raw"))
    box_has = os.path.isdir(os.path.join(root, "output", "raw"))
    if live_has and not box_has:
        raise AssertionError(...)
    live, box = _catalog_matches_disk(HERE), _catalog_matches_disk(root)
    if live != box:
        raise AssertionError(...)
    return True
finally:
    _remove_scratch_tree(root)
```

Verified against `src/mutate.py:1738-1755`: `sandbox()` now junctions `output/raw` to the live
directory (added the same run, right after the pre-existing `output/index` junction), guarded by
`if os.path.isdir(shelf):`, which matches this net's `live_has`/`box_has` asymmetry check (if the
live tree has no `output/raw` yet, nothing is asserted about the sandbox having one). `_junction`
(`mutate.py:867-881`) raises `RuntimeError` on failure rather than silently leaving the target
directory absent, so `sandbox()` itself would fail before this net ever ran in the one case that
could make `live_has and not box_has` fire spuriously — consistent, not a gap.

The net's own property is "the two worlds agree on the *verdict*", not "the verdict is `True`" —
it compares `live == box`, so if the live catalog were genuinely broken, both sides would report
`False` and the net would still hold. That is deliberate and consistent with this file's own
stated convention elsewhere (agreement between worlds, not correctness of either world) — the
existing net "the catalog and the shelf agree in BOTH directions" is the one that grades the live
tree's actual health; this new net grades only whether the sandbox construction faithfully mirrors
it. Not a defect.

Cleanup: `_remove_scratch_tree(root)` is called on a root obtained directly from `M.sandbox()`,
which is exactly what `scratch_tree()` (used by `prove_net`/`ledger_dry_run`) does internally, so
reusing the same cleanup helper here is consistent with the rest of the file.

### `output/raw` added to `_remove_scratch_tree`'s `shared` list (~line 900)

```python
shared = ["prompts", "reference", os.path.join("output", "index"),
          os.path.join("output", "raw")]
```

Matches the new junction `mutate.sandbox()` creates. The unlink loop does `os.rmdir(link)` only
`if os.path.isdir(link)`, so a live tree with no `output/raw` (hence no junction created) is a
no-op here, consistent with the conditional junction. If `output/raw` were ever a **real**
directory inside a sandbox (e.g. because a mutation run actually wrote chapters into it during
testing, rather than it being the live-tree junction), `os.rmdir` would fail on non-empty, be
caught, and — since it's neither a junction nor a symlink — silently *not* be added to `stuck`;
the subsequent `shutil.rmtree(root, ...)` then deletes it along with everything else in the
scratch tree, which is correct (real, sandbox-only content should be deleted, not preserved).
Correctly implemented; no unlink-order or double-free issue found.

## Rest of the file

The remaining ~23,700 lines are the pre-existing battery, read in full. This file is unusually
self-auditing: a very large fraction of its content is prose recording a defect's own discovery,
the fixture that beat the old form, and the corrected net, for every failure class this sweep was
asked to hunt (tautological checks, fail-open branches, caps/truncations, wrong-variable/off-by-one
bugs, races, regex/escape corruption, silent exception swallowing, dead code, and false comments).
I traced a sample of the reachability/AST-walking primitives (`_live_stmts`, `_live_walk`,
`_arm_leaves`, `_gate_precedes_spawn`, `_carries_result_of`) against their own docstrings and the
fixtures that exercise them and found them internally consistent with the properties claimed.
I did not find a new instance, outside the three items above, of any defect class in the brief's
priority list. `prose_enabled`/`step4_enabled` are each pinned to an exact owner-ruled state by a
net that reads the real gate against the real `config.yaml`; neither is touched, opened, or
recommended-for-opening anywhere in this file, per the audit's own constraint.

## Findings

**0 VERIFIED, 0 SUSPECTED (0 with concrete failure scenario), 1 QUESTION.**

- **QUESTION** — `drill.py:_catalog_matches_disk`, the `os.path.isabs(p)` branch (~line 12417): if
  a `catalog.json` entry's `raw_path` were ever absolute, `_catalog_matches_disk(root=<sandbox>)`
  would check that entry against the live filesystem instead of the sandbox, defeating the new
  live-vs-sandbox comparison net for that entry. Not reachable today — the only production writer
  of `raw_path` (`generate.py:1215`) always writes a relative path — so this is a design question
  for the module owner (should the branch resolve against `root`, or should it be removed since
  nothing writes an absolute path?) rather than a defect with a live failure scenario.

## Coverage

Recorded via `sweep_plan.record('run64', ['drill.py'], batch=1)` after this file was read in full.
