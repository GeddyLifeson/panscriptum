# Sweep 58 — Batch 04 audit

Modules read IN FULL, top to bottom (line counts from `wc -l` / the last numbered line):

| module | lines |
|---|---|
| src/mutate.py | 3197 |
| src/onomast.py | 839 |
| src/weave.py | 709 |
| src/tiers.py | 554 |
| src/pick_model.py | 443 |
| src/suppressions.py | 353 |
| src/context_budget.py | 296 |

Read-only throughout. No file under `src/`, `data/`, `state/` or `prompts/` was edited. `mutate.py`
was read only — its detached pass was never run or interrupted. No subagents were spawned.

## Open queue checked first

Ran `workorders.open_orders()` and cross-referenced every order touching this batch's modules
before writing anything below, per the brief.

---

## src/onomast.py (839 lines)

**KNOWN a803028ab794 (ONOMASTICON_TWO_WRITERS_NO_CAS) — FIXED this shift, no longer accurate as an
open defect.** The order described two independent read-modify-writers of `data/ONOMASTICON.json`
(`onomast.main()` via `silence.write_json`, `pipeline.phase_weave` via `land_json`), neither
compare-and-swapped. `onomast.py` now has `land_onomasticon(resolved, attempts=5)` (onomast.py:702):
digest is taken (`silence.digest_of(OUT)`) *before* `name_worlds(resolved)` re-reads the prior file,
the write lands through `silence.replace_if_unchanged`, and a refusal because the file moved retries
by re-running `name_worlds` against the winner's copy (which re-seeds `taken` from the winner's
designations, so nothing is reissued); a refusal while the file stood still breaks out of the retry
loop rather than looping (correctly treated as a denial, not a race). Verified against
`silence.replace_if_unchanged`'s own contract (silence.py:624) — matches. **Verified the other
caller too**: `pipeline.py:3340` (`phase_weave`) now calls `O.land_onomasticon(resolved)` directly
(grep-confirmed, not `land_json`), so both callers do go through the one CAS writer as the docstring
claims. This order can be closed for onomast.py's half; I did not re-audit pipeline.py itself
(out of batch) beyond confirming the call site.

**KNOWN 3fc19ad4d1c6 item 2 (onomast.py:668-683, non-dict prior dropped with zero trace) — FIXED
this shift, no longer accurate.** `name_worlds`'s merge loop (onomast.py:667-691) now has a
distinct `silence.note("onomast.py:merge-dropped-non-dict-prior")` for a prior record that isn't a
dict at all, alongside the existing `merge-dropped-unschemad-prior` note for a dict missing
`catalogue_name`. Both silent-shrink paths are now traced.

**KNOWN 5d0fa30e4b09 item 6 (onomast.py:732, `v["attestations"][0]` could IndexError on an empty
list) — still accurate, unchanged.** Same code now sits at onomast.py:795 inside `main()`'s report
loop (`src = v["attestations"][0]`), still with no guard for an empty `attestations` list. This
remains a QUESTION per the standing order, not a new defect — no in-file guarantee attestations is
non-empty was found, consistent with the order's own "likely an upstream resolver invariant"
reading.

Nothing else found. Checked: `well_formed()`'s docstring claims against its code (all seven
constraints — length, echo, stutter, cluster, density, vowel-run, vowel-floor — verified to match
exactly what the code tests, unlike the historical miscount/misattribution the docstring itself
narrates as already fixed); `coin_well_formed_stamped`'s fallback ladder (ordinary → fallback →
extended salts → digest-tail, each step checked for both `well_formed` and `taken`); Hard Rule 0 in
`main()`'s report (`_endonyms[:4]` and `rows[:9]` both print "... and N more", not silent cuts).

## src/weave.py (709 lines)

**KNOWN 3fc19ad4d1c6 item 1 (`filtered_index()` fails open on an ImportError from `pipeline`) —
FIXED this shift, no longer accurate.** `filtered_index()` (weave.py:283-287) now does
`try: from pipeline import _STATBLOCK / except Exception: silence.note(...); raise` — it propagates
instead of setting `_STATBLOCK = None` and silently continuing. Confirmed both production callers
call it unwrapped and let the raise reach their own outer handler, matching the docstring's claim:
`tiers.py:252` (`_graph()`, no try/except) and `pipeline.py:3274` (`phase_weave`, grep-confirmed
unwrapped call).

**KNOWN fe99e57e1993 (weave.py:464 `[:34]` unmarked name cut) — FIXED, no longer accurate for this
site.** Grepped the whole file for `\[:[0-9]` — the only hits are inside comments narrating
already-fixed history (`desc[:400]`/`desc[:300]` describing the old windowed statblock test, and
the `names[k][:34]` comment describing a sweep45 fix). No live truncation remains; the surviving
diagnostics use `:<N` padding (no cut) or explicit "... and N more" disclosure.

Nothing else found. `components()`'s threshold<=0 refusal, `null_threshold_surprisal`'s
`NullThresholdUnmeasured` (never spent as a false 0.0), and the three atomic/gated writes in
`main()` (`--write`) were all re-checked against their own docstrings and are consistent.

## src/tiers.py (554 lines)

**KNOWN 5d0fa30e4b09 item 4 (tiers.py:165-166, bare `assert` for the CUTS invariants, stripped
under `-O`) — FIXED this shift, no longer accurate.** Lines 168-173 now `raise ValueError(...)` for
both invariants (CUTS loosen downward; `CUTS[0][1] <= MULTIVERSE_THRESHOLD`) instead of `assert`.
Verified the arithmetic itself is still correct: `itertools.pairwise(CUTS)` over
`[("metaverse",100.0,...), ("xenoverse",50.0,...)]` gives `100.0 > 50.0` (true, no raise), and
`CUTS[0][1]=100.0 <= MULTIVERSE_THRESHOLD=102.3` (true, no raise) — the checks pass on today's
constants and correctly fire only on a future edit that breaks the ordering.

**KNOWN fe99e57e1993 (tiers.py:403 `a[:26]`/`b[:26]` unmarked cut) — FIXED, no longer accurate for
this site.** `deliberate_joins()`'s print loop (tiers.py:475-483) now uses `_cut(a, 26)` /
`_cut(b, 26)` — the module's own display helper (tiers.py:143-152) that appends `chr(8230)` (…) when
it truncates. The `SAMPLE STACKS` block (tiers.py:509) uses the same helper. Both are disclosed
display-column cuts over data that is written whole to `data/TIERS.json`, which is the compliant
shape Hard Rule 0 asks for.

Nothing else found. `_load_groundings()`'s documented fail-open-for-bootstrap/fail-closed-for-write
split was checked end to end: `chart()` proceeds on an unreadable `GROUNDINGS.json` (deliberately,
so phase 5's first run isn't wedged), but `main()` refuses to write `TIERS.json` both before the
chart (`if not readable: return 2`) and after it (`if not tiers.get("groundings_readable"): return 2`,
re-asked because the graph build takes minutes) — the two refusal sites match the two failure
windows the docstrings claim to cover. The containment-violation gate (`split_sources`) is computed,
printed, and now actually blocks the write (`return 2`) rather than only being diagnostic, matching
its own comment.

## src/pick_model.py (443 lines)

Nothing found. Not one of the modules this shift rewrote, and none of the surviving prose reads as
inaccurate. Checked in particular: `save_config`'s targeted `model:` line replacement (won't touch
an indented/nested `model:` because `^` under `re.M` requires column 0, matching the "we don't
clobber comments/formatting elsewhere" comment) and its gated, atomic write; the two-budget split
(`total_vram_gb` "by class" vs `free_vram_gb` "right now") and the `is not None` vs truthiness fixes
around a genuine `0.0` free-VRAM reading. One thing checked and NOT filed: `weight_gb()`'s
`size / 1e9` fallback reports a slightly *larger* number of "GB" than the true GiB value nvidia-smi
reports for `total_vram_gb()`'s budget (decimal GB vs binary GiB, ~7% apart) — this makes the
residency gate marginally *more* conservative than it needs to be (a model that would technically
fit could be refused), which is the safe direction for a "GPU-only, refuse if it doesn't fit"
policy, so I'm not filing it; noting it here so nobody re-derives it as a bug in the dangerous
direction.

## src/suppressions.py (353 lines)

**DEFECT MAJOR — `add()`/`remove()` are a whole-document read-modify-write with no compare-and-swap;
concurrent callers can lose an update.**

```python
def _land(rows):
    return silence.write_json(FILE, rows, indent=1, ensure_ascii=False)

def add(detector, path_glob, reason, added_by="owner", ttl_days=DEFAULT_TTL_DAYS):
    ...
    rows, ok = _load()
    ...
    rows = [r for r in rows if not (...)]
    rows.append({...})
    if not _land(rows):
        raise IOError(...)
    return rows[-1]
```

`silence.write_json` (confirmed by reading its docstring at silence.py:773) is an *atomic replace*
(temp file + `os.replace`) with no digest comparison — it is not a compare-and-swap. `add()` and
`remove()` both read the whole file, mutate an in-memory list, and write the whole file back with no
staleness check between the read and the write, which is exactly the lost-update shape this same
sweep fixed in `onomast.land_onomasticon` (order a803028ab794), `roll.mutate` (order c9146abf92df /
f818a77293fc) and `chain.py` (order 972932ab89b0).

**Failure scenario.** Two callers invoke `suppressions.add()` for two different detectors at
nearly the same time (A for `detect_secrets` on one path, B for `ruff` on another). Both call
`_load()` and get the same N-row list. A appends its row and writes N+1 rows (including A's) to
disk — succeeds, returns `rows[-1]` (A's row) with no error. B, still holding its own stale N-row
copy (not containing A's new row), appends its own row and writes its own N+1 rows (including B's
but *not* A's) — this is a plain `os.replace`, so it wins unconditionally and also returns
successfully. The caller for A believes its suppression is recorded (`add()` raised nothing and
handed back the row it asked for); `active()`/`suppressed()` re-read from disk on every call (as the
module's own comments note) and will never show A's row again. The reverse case — a `remove()`
racing with a concurrent `add()` — is the more dangerous direction the module's own docstring names
by name ("an operator who believes a detector has been re-armed when it has not is trusting a scan
that is still waved through"): that discipline covers a *denied rename*, but not a second writer's
successful one landing over the first.

**Caveat, for the record:** `grep -rn "suppressions.add\|suppressions.remove" src/` finds zero
callers today (confirmed, matching order 34ec8a90c42f's own observation that `add` has no callers
yet), so this is currently latent rather than measured in production. Filed as a DEFECT rather than
a QUESTION because the shape is not ambiguous — it is the identical, already-repeatedly-diagnosed
lost-update pattern this project fixes with a CAS wrapper every time it is found elsewhere in this
same codebase this same shift — but the severity reflects that nothing calls it yet.

**Remedy**, following the shape already used by `onomast.land_onomasticon`: take
`silence.digest_of(FILE)` before `_load()`, land through `silence.replace_if_unchanged`, and on a
refusal because the file moved, re-read and re-apply the same add/remove against the winner's copy
before retrying.

**KNOWN 34ec8a90c42f item 8 (suppressions.add has no upper bound on ttl_days) — still accurate,
unchanged.** `add()` (suppressions.py:109-147) still computes
`"expires_at": time.time() + float(ttl_days) * 86400` with no bound on `ttl_days` and no rejection
of a non-finite or negative value. This is filed as an owner QUESTION already (design ruling
pending); confirmed the code is unchanged from what that order describes.

Nothing else found. `_load()`'s three-way unreadable/wrong-shape/missing handling, `active()`'s
fail-closed-on-unreadable, `suppressed()`'s deliberate `fnmatchcase` (not `fnmatch`) for
case-sensitivity, and `_repo_listing()`'s single-walk-built-lazily performance fix were all checked
against their own docstrings and are consistent.

## src/context_budget.py (296 lines)

**DEFECT MAJOR — an unreadable prompt file makes the content budget too *generous*, in the one
module built specifically to stop a prompt from being silently truncated by Ollama.**

```python
def feats_block_budget(cfg, system_text=None, template_text=None):
    if system_text is None:
        try:
            with open(os.path.join(PROMPTS, "system_style.txt"), encoding="utf-8") as f:
                system_text = f.read()
        except Exception:
            # SWEEP34 96ebf36510b8: an unreadable prompt file was silently making
            # scaffold_chars 0 and content_budget_chars LARGER -- the truncating direction
            # this module's own header says it exists to refuse. Recorded, not just swallowed.
            silence.note("context_budget.py:feats_block_budget-system_text")
            system_text = ""
    ...
```

The module's own comment names the fault direction explicitly ("the truncating direction this
module's own header says it exists to refuse") and describes the fix as "Recorded, not just
swallowed" — i.e. the prior behaviour was fully silent, and what was added is a `silence.note` call,
not a refusal. The function still proceeds with `system_text = ""` (and the same for
`template_text`), which means: `system_for("feats", "")` returns `""`, `scaffold_chars("", "")` is
`0`, and `content_budget_chars(cfg, 0, "feats")` treats the *entire* window (minus the reserve) as
available for content — the exact "truncating direction" the header's whole three-part remedy
exists to end, reachable via a plain transient I/O failure (an AV lock, a permission race, or the
owner editing `system_style.txt` for voice while a job is mid-flight — all patterns this same
codebase's own comments elsewhere describe happening on this machine).

**Failure scenario.** `manifest_builder.py:408` calls `_CBUD.feats_block_budget(cfg)` with no
`system_text`/`template_text` (confirmed by grep), so any transient failure reading
`prompts/system_style.txt` or `prompts/feats_prompt.txt` at that moment returns a budget computed
as if there were zero scaffolding overhead — far larger than correct. The actual API call built
downstream still carries the real, full system prompt (~18KB) and template (~2.8KB); if the content
packed against the inflated budget plus that real scaffolding exceeds `num_ctx`, Ollama truncates
the prompt and answers anyway — precisely the failure this module's header (`context_budget.py:1-58`)
describes as the reason the whole module exists, arriving through the one code path meant to
prevent it. (I confirmed `manifest_builder.py`'s own `budget <= 0` guard raises `ContextOverflow`
correctly — that check is fine; the bug is upstream of it, in the budget being wrong rather than
absent.) `report()` (context_budget.py:276-296) has the identical fallback for the same two files,
feeding a health/preflight number that would look falsely reassuring under the same fault.

**Remedy**, consistent with the rest of this project's fail-closed discipline for exactly this
class (`onomast.OnomasticonUnreadable`, `tiers`'s `_load_groundings` writer-side refusal): either
raise (there is no honest budget to compute without the real scaffolding size) or treat an
unreadable prompt file as if it were the *largest* plausible scaffolding, never the smallest.

Nothing else found. `content_budget_chars`'s "negative means refuse, never clamp" contract is
honored by its one caller (`manifest_builder.py:408-412` raises `ContextOverflow` on `budget <= 0`,
confirmed). `PROSE_CHARS_PER_TOKEN` vs `CHARS_PER_TOKEN` split and the `JOB_OVERHEAD_CHARS` /
`METADATA_INFLATION` corrections were checked against the measurements their comments cite and are
internally consistent.

## src/mutate.py (3197 lines)

Read in full. Per the brief: this module has a detached pass running right now — it was **read
only, never run, never interrupted**; no `run()`, `main()`, `sandbox()` or any gate command was
executed.

**KNOWN 58a00e909217 (a 16.3h run scored `escalation.py:409` KILLED when it cannot be detected —
confirmed false kill; mechanism narrowed to the `data/` junction, not proven) — still open,
accurate.** `sandbox()`'s docstring (mutate.py:1410-1449) documents the mitigation already landed
(order f40f701594a4: every top-level *file* directly under `data/` is now hardlinked at build time
instead of the whole tree being one junction, freezing a snapshot the same way a copy would), but
states plainly this is a partial fix: a file *inside* a junctioned subdirectory (`data/records/`)
is still live, and 4 of 221 record files were measured moving in a 17-hour window. The order's own
"per order 58a00e909217's direct re-attack, the only surviving explanation" language matches what's
in the code; nothing in this read closes the order.

**KNOWN d2d4ff880570 (20-hour mutation pass launched as a child of a 1-hour shift, no detach, no
roster) — remedies (a) and (c) are now landed, matching the order's own text.** `main()` now has a
`--detach` flag (mutate.py:2641-2694) that re-spawns itself with
`DETACHED_PROCESS | CREATE_NEW_PROCESS_GROUP` (confirmed at line 2683) and `python -u` with
`PYTHONUNBUFFERED=1` (confirmed at line 2678/2682), then returns immediately — this is the
"detached pass running right now" the brief refers to. I did not re-verify remedy (b)
(`codewatch.EXEMPT`) since `codewatch.py` is out of this batch. Remedy (d) — reproducing the
FileNotFoundError — is explicitly carried forward as its own order, see next.

**KNOWN 9ea4d3545524 (two mutation passes died on a FileNotFoundError for their own sandbox path,
mid-run, cause undetermined) — still open, accurate.** No new mechanism addressing this specific
failure was found in the current code; the "ownership beats age" reaper fix
(`_owner_pid`/`reap_orphans`, mutate.py:1141-1335) and the `BUILDING_PREFIX`→rename claim sequencing
(`sandbox()`, mutate.py:1481-1496) are both already-landed fixes for *other*, related incidents
(M46, the reaper deleting a live concurrent sandbox) and neither module comment claims to explain
this one. Matches the order's own "still open... candidate causes to test, not conclusions."

**KNOWN 1d45a56ae1d8 (stale `file.py:NNN` citations in mutate.py comments, pointing at real code in
the wrong place) — still present, confirmed accurate, and the drift has grown since the order was
filed.** All three citations are still at essentially the same source lines the order names:
`mutate.py:886` cites `assay.py:593` for a `strict=True` ruling — confirmed `assay.py:593` is inside
`_check_scores` and carries no `strict` parameter. `mutate.py:1264` cites `drill.py:4256` for
`reap_orphans()` — confirmed the real call sites are now at `drill.py:17520` and `drill.py:17688`
(the order recorded them at "~15214/15382" when filed; they have drifted roughly another 2,100-2,300
lines since). `mutate.py:1677` cites `verify_math.py:3639` for the live-failure-ledger check —
confirmed the actual check sites are `verify_math.py:399`, `:4399`, `:12860`, `:13027`, nowhere near
3639. This is exactly the citation-rot pattern this order (and the doctrine at `0c7592915a48`, cite
by symbol) exists to name; filing this confirmation rather than a new order since one is already
open and unresolved for these exact three lines.

Nothing else new found in mutate.py. This module is unusually heavily self-documented — nearly
every historical defect I could construct a failure scenario for is already narrated in a comment
at the site, with the measured incident, the fix, and the order id. I specifically checked (and
found already correctly handled, matching their own docstrings): the O_EXCL lock acquire (no
check-then-create race), `_lock_release`'s token-ownership check (an unreadable or wrong-shape
record is removed, matching "can only be our own" reasoning since O_EXCL prevents anyone else from
having written over the claim), the `root == HERE` live-tree refusal in `_run_mutation`, the
missing-baseline-is-refused-not-defaulted guard, `could_not_judge`'s prefix match (TIMEOUT/ERROR
never silently counted as a kill), `hang_confirms_a_kill`'s two-independent-readings requirement
before a timeout is scored as a kill, and the `_refresh_baseline` mid-run drift bookkeeping
(unusable refresh discarded rather than adopted; a moved baseline recorded with the row identities
on both sides of the move). One thing named but not filed: `_HELD` (mutate.py:334) is a plain
module-level global guarding lock re-entrancy, which would not be thread-safe if a future caller
ever ran two mutation sessions on separate threads in one process — no such caller exists today
(every real entry point is the single-threaded CLI), so this is a QUESTION for the future scheduler
the docstrings mention, not a present defect.

---

## Summary

- **DEFECT MAJOR** × 2 (both new): `suppressions.py` `add()`/`remove()` lost-update race (no CAS);
  `context_budget.py` `feats_block_budget()`/`report()` fail-open on an unreadable prompt file.
- **QUESTION** × 0 new (one non-issue noted and explicitly not filed: `pick_model.py`'s decimal-GB
  vs binary-GiB estimate, safe direction; one noted for the record: `mutate.py`'s non-thread-safe
  `_HELD` global, no current caller needs it thread-safe).
- **KNOWN** × 11 references across 6 open orders, each re-verified against current source:
  `a803028ab794` (onomast, FIXED), `3fc19ad4d1c6` items 1 & 2 (weave + onomast, both FIXED),
  `fe99e57e1993` (weave.py + tiers.py sites, both FIXED), `5d0fa30e4b09` item 4 (tiers.py, FIXED)
  and item 6 (onomast.py, still open), `34ec8a90c42f` item 8 (suppressions.py, still open),
  `58a00e909217` (mutate.py, still open), `d2d4ff880570` (mutate.py, mostly fixed this shift),
  `9ea4d3545524` (mutate.py, still open), `1d45a56ae1d8` (mutate.py, still open, drift worse).
