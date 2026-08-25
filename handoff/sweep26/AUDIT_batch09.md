# BATCH 09 audit — run26

Modules (2,440 lines total, read in full, no sampling):

| module | lines |
|---|---|
| hostcheck.py | 955 |
| manifest_builder.py | 478 |
| pick_model.py | 357 |
| sevenfold.py | 274 |
| catalogue_codex.py | 215 |
| sweep_plan.py | 161 |

---

## SPECIAL FOCUS 1 — sweep_plan.py `record()` cross-process lost update

**Confirmed and characterized against the source.**

`record()` (sweep_plan.py:84-113) wraps its read-modify-write in `_RECORD_LOCK`, a
module-level `threading.Lock()` created at sweep_plan.py:81. That lock is a **per-process**
object — every separate `python -c "...sweep_plan.record(...)"` invocation (which is exactly
how this batch's own sweep is driven: one process per batch, N batches at once) gets its own
fresh, uncontended lock. It serializes threads *inside* one interpreter; it provides **zero**
mutual exclusion between OS processes.

Sequence that loses an update (two real processes, A and B, finishing close together):

1. A opens COVERAGE (`state/SWEEP_COVERAGE.json`), reads it into `data_A`.
2. B opens the same file before A writes back, reads the same content into `data_B`.
3. A merges its own `covered` modules into `data_A`, writes it out — atomically (`silence.write_json` → tmp + `os.replace`, or the inline tmp+replace fallback at sweep_plan.py:109-112 if `import silence` fails).
4. B merges its own `covered` modules into `data_B` — which never saw step 3's additions, because B's read happened first — and writes it out, atomically **replacing A's file whole**.
5. A's batch's coverage rows are gone. Nothing raised, nothing logged; the file is perfectly valid JSON throughout, just wrong.

The docstring at sweep_plan.py:87-92 states: *"The lock covers this process; the atomic land
covers a torn read."* That sentence is accurate but incomplete — it stops the two failure modes
it names (concurrent threads in one process; a reader catching a half-written file) but not the
third one, which is the one that actually reproduced: a lost update from two independent,
non-conflicting-at-the-OS-level writers each doing an honest atomic replace of stale data.

**`missing()` was checked and does NOT paper over this** — verified directly:
- If COVERAGE is unreadable/corrupt, `json.load` raises → `data = {}` (sweep_plan.py:121-123) → every module compares against a run of `None` → **all modules report missing**, not zero.
- If COVERAGE is valid-but-incomplete because of the lost-update race above, the clobbered batch's modules simply aren't keyed to the requested `run` → they too report as missing.

Both failure paths fail toward *over*-reporting gaps, never toward a false "0 uncovered." That
is the correct direction for a coverage prover to fail in, and it's explicitly not the bug here.
The actual damage from the race is upstream of `missing()`: a completed batch's coverage can
silently regress to "never covered," which would show up as spurious re-work or a spurious
"gap" investigation, not as a false-green sweep.

**Proposed fix (reported, not applied):**

- **Preferred — stop sharing one mutable file.** Have each `record()` call write its own
  per-writer fragment, e.g. `state/coverage/<run>/<pid>-<uuid>.json` containing just that
  call's `{module: {run, at}}` rows. `missing()`/`--coverage` glob every fragment for the
  run and union them at read time. No writer ever reads-modifies-writes another writer's
  file, so there is nothing to race — this matches the "many independent writers, no shared
  mutable state" pattern the rest of the tree already uses (e.g. per-entity cache files
  under `data/feats/`).
- **Minimal alternative — real cross-process locking.** Keep the single COVERAGE.json but
  hold an OS-level exclusive lock for the full read+merge+write, not just the in-process
  `threading.Lock`: an exclusive lockfile via `os.open(lockpath, os.O_CREAT | os.O_EXCL)` in
  a short retry/backoff loop (same shape as `silence.replace_retry`'s Windows backoff),
  removed after the write lands. `threading.Lock` alone cannot do this job regardless of
  where it's placed in the function.

---

## SPECIAL FOCUS 2 — hostcheck.py: hosts silently going permanently hostless (M16 shape)

**Confirmed — two compounding defects in `sweep(..., repair=True)` (hostcheck.py:486-599),
matching the M16 shape exactly: one transient failure can permanently strip a source's host.**

### (a) `null_rate()` folds a failed baseline probe into a rate of 0.0

hostcheck.py:394-423:
```python
r = probe(host, foreign) or {}
rate = r.get("rate")
rate = 0.0 if rate is None else rate      # <-- line 420
...
_NULL_CACHE[host] = rate                  # cached for the rest of THIS process
```
`probe()` returns `rate: None` specifically when the request raised (network error, throttle,
timeout — see the `except Exception` branch at hostcheck.py:146-155, whose own comment is a
direct warning against this exact conflation for the *primary* probe: *"NOT a rate of zero. A
request that failed is not a wiki that holds nothing... Seventy-four throttled probes came back
as 0% and the repair pass unassigned `warhammer40k.fandom.com`."* `null_rate()` reintroduces
precisely that mistake for the **baseline** probe instead, and then **caches the wrong value**
in the process-lifetime `_NULL_CACHE` (hostcheck.py:390-391), so every other source sharing that
host for the rest of the run scores against a falsely-low baseline. Since `lift = rate - base`
(hostcheck.py:463), a falsely-zeroed baseline **inflates** lift for every subsequent probe of
that host — biasing `score()` toward false "holds"/"partial" verdicts, the opposite direction
of a naive reading but just as wrong, and it's the mechanism that feeds defect (b).

### (b) `judged_any` only requires *some* candidate to answer, not the *right* one

hostcheck.py:524-594, repair loop for a source whose current host scored WRONG FICTION / NAMES
ONLY / partial:
```python
judged_any = False
for h in candidates(src, r["host"], by=by, hosts=hosts):
    p = score(h, by[src], src, by=by)
    ok = p["verdict"] in ("holds", "partial")
    judged_any = judged_any or not p["verdict"].startswith("UNREACHABLE")   # line 538
    ...
if best[1] and ...:
    fixed[src] = best[1]                       # repointed
elif not judged_any:
    ... keep r["host"] for now                  # safe: no candidate answered at all
elif r["verdict"] == "partial":
    ... keep r["host"]                          # safe
else:
    fixed[src] = None                           # <-- marks source PERMANENTLY hostless
```
`candidates()` always tries `www.dandwiki.com` first (hostcheck.py:318) and `en.wikipedia.org`
last (hostcheck.py:355-356) — both are near-universally *reachable* even when they don't hold
the fiction. So `judged_any` goes True almost every run, **regardless of whether the one
candidate that would actually hold the fiction was reachable this run**. If that specific
correct candidate happened to fail transiently (throttle, timeout — exactly the failure mode
`_get()`'s own docstring at hostcheck.py:99-109 says was observed at scale: "1,364 swallowed
HTTPErrors in a single adoption pass"), the loop still falls through to the `else` branch:
the source is marked unfit (written to `HOST_UNFIT.json`), popped out of `WIKI_HOSTS.json`
entirely (hostcheck.py:581), and stays that way until someone runs `--adopt` again — a single
bad network moment converted into a standing, silently-recorded "no wiki holds this fiction"
finding.

### (c) No dry-run gate on `--repair` at all

Unlike `purge()` (hostcheck.py:612, `dry=True` default, requires `--go`) and `adopt()`
(hostcheck.py:846, same pattern), `sweep()`'s repair branch has **no `dry` parameter and no
`--go` requirement** — `main()` (hostcheck.py:950) calls `sweep(only=a.only, repair=a.repair,
workers=a.workers)` and the repair block writes `_land(F.HOSTS, hosts)` /
`_land(UNFIT, unfit)` unconditionally the moment `--repair` is passed (hostcheck.py:590-591).
`--repair`'s own `--help` text says "rewrite the map," so this may be deliberate, but it means
defect (b) has **no preview step and no confirmation flag** standing between one bad network
run and a live host eviction — the asymmetry with `purge`/`adopt` (both of which the docstrings
explicitly frame as needing a human to confirm) is worth the owner's explicit sign-off if it's
intentional.

**Net finding:** hostcheck.py can and (per the mechanism above) plausibly does turn a transient
probe failure into a permanent "source has no wiki" state, via the combination of (a) inflating
false-positive lifts on OTHER hosts and (b) treating "some candidate answered" as "we searched
adequately," with (c) providing no safety net. This is very likely part of why "sources with a
reachable wiki" sits at 93% (15/210 hostless) rather than closer to 100%.

**Not part of this bug (checked and clear):** `adopt()` (hostcheck.py:846-910) only ever *adds*
hosts to `WIKI_HOSTS.json` — a hostless source that fails to find a good candidate stays
hostless, it is never made *worse*. And a source's own probe returning `rate: None` correctly
produces `"UNREACHABLE — no judgement"` (hostcheck.py:469-471), which is explicitly excluded
from the `JUDGED` tuple (hostcheck.py:516) — so a straightforwardly-unreachable *current* host
does not get evicted by itself. The defect is specifically in how the *replacement search*
treats reachability of irrelevant candidates as license to give up on the real one.

---

## SPECIAL FOCUS 3 — pick_model.py: can it silently fall back to a different model or CPU load?

**CPU load: no.** `RESIDENT_ONLY = True` is a hardcoded module constant with no CLI flag to
disable it (pick_model.py:91). `resident()` (pick_model.py:190-192) is checked for every
installed model before it's allowed into `scored`; anything that would spill to CPU goes into
`refused` and is only ever *displayed*, never selectable (pick_model.py:296-306, 315-319). If
nothing qualifies, `main()` exits 1 with pull suggestions rather than silently picking a
disqualified model (pick_model.py:327-330). This path is solid.

**Different model: not pinned, and that's a design choice worth confirming with the owner.**
The script doesn't hardcode `qwen3:8b` as *the* answer — it ranks every installed,
VRAM-resident, non-excluded model by `(family_tier, instruct_bonus, log2(size))`
(pick_model.py:258-270) and picks the top scorer. `qwen3:8b` is presented only as the
*recommended pull* in `print_pull_suggestions()` (pick_model.py:215-226), not as a pinned
target. So if the owner ever installs `qwen3:14b` or `gemma3:12b` alongside `qwen3:8b` and both
fit in VRAM, `--write` will happily switch `config.yaml` to whichever scores higher — silently,
in the sense that nothing flags "this is a different model than last time." That's consistent
with the script's stated purpose ("picks the best available," not "pins one tag"), but it's
worth confirming that's what "the standing local model (qwen3:8b)" in the task brief means in
practice, versus a hard pin. See QUESTION 1 below.

`save_config()` (pick_model.py:104-134) is correctly defensive: it does a targeted `re.sub` on
the `model:` line only (not a blind overwrite), checks the substitution actually matched
(returns `False` and prints to stderr if not), and checks `replace_retry`'s return value instead
of assuming success — the module's own docstring (pick_model.py:105-114) documents both as
previously-real bugs it fixed. Verified correct as written.

---

## MAJOR

1. **hostcheck.py:419-420, `null_rate()`.** Converts an unreachable/failed baseline probe
   (`rate=None`) to `0.0` and caches it in `_NULL_CACHE` for the rest of the process — the exact
   "not a rate of zero" mistake the file's own `probe()` docstring warns against (hostcheck.py:
   150-155), reintroduced for the baseline. Poisons every subsequent `score()` call against that
   host this run (inflated lift → false "holds"/"partial"). See Special Focus 2(a) above for the
   full mechanism.

2. **hostcheck.py:538, `judged_any` in `sweep(repair=True)`.** A source's current host is
   evicted (`fixed[src] = None`, popped from `WIKI_HOSTS.json`, logged to `HOST_UNFIT.json`) the
   moment *any* candidate — including the near-always-reachable `www.dandwiki.com` and
   `en.wikipedia.org` — returns a non-UNREACHABLE verdict, even if the one candidate that would
   actually hold the fiction failed transiently this run. One bad network moment → permanent
   "no wiki holds this fiction." See Special Focus 2(b).

3. **hostcheck.py: `--repair` has no dry-run/`--go` gate**, unlike `purge()` and `adopt()`
   (hostcheck.py:486 vs. 612/846, and main() at 935-951). Combined with #2, there is no preview
   step before a host gets evicted. Confirm with the owner whether this asymmetry is intentional.

4. **catalogue_codex.py:130-137.** Section matching is unranked bidirectional substring
   containment (`n in k or k in n`), first-match-wins by dict iteration order:
   ```python
   for k, t in sec_by_norm.items():
       if n and (n in k or k in n):
           title = t
           break
   ```
   This is the identical defect class already found and fixed twice elsewhere in this codebase —
   `manifest_builder.py`'s `load_record()` (this very batch, hostcheck.py-adjacent file,
   manifest_builder.py:72-100) was rewritten specifically to rank candidates by length-closeness
   after an unranked version sent "DC" to `sword-coast-adventurer-s-guide.json`; that same
   comment cites address.py as the original site of the bug. `catalogue_codex.py` still has the
   unranked, unranked-by-closeness, first-hit-by-iteration-order version. Since `parse_codex()`
   builds `sections` (and therefore `sec_by_norm`) in **document order**, not alphabetically or
   by length, whichever codex section happens to come first in the file and share a substring
   with a short roll source name wins — silently attributing that source's homebrew content to
   the wrong codex section. This module's entire purpose is exact transcription of the owner's
   own authored material ("Attestation is Transcribed... No model generated any of it" —
   catalogue_codex.py:26-27), which makes a wrong-section mismatch here worse than the same class
   of bug elsewhere: it's not a wrong wiki, it's mislabeled first-party content written into a
   record file under provenance text (catalogue_codex.py:175-183) that asserts it's correct.

## MINOR

5. **pick_model.py: `fit_note()` display uses `free_vram_gb()` while selection uses a
   `total_vram_gb() - VRAM_RESERVE_GB` budget** (pick_model.py:295 vs. 308, 324). A model that
   passed the residency gate (accepted into `scored`) can still print "WILL OFFLOAD" in its own
   listing line because free VRAM (which fluctuates with whatever's on the desktop) is lower
   than the total-based budget it was actually judged against. Cosmetic only — doesn't affect
   which model gets picked — but confusing to read.
6. **pick_model.py:211**, `silence.note("pick_model.py:150")` — stale line-number tag; the
   function is no longer near line 150. Harmless, but misleading if anyone greps the note site
   back to source.
7. **pick_model.py:242**, `fit_note(model_entry, vram_gb, num_ctx_gb=1.2)` duplicates the
   `KV_GB = 1.2` constant (pick_model.py:92) as a separate literal instead of defaulting to
   `KV_GB`. Drift risk if one is retuned without the other.
8. **sevenfold.py:198-208, `build()`.** If a world's `designation`'s source prefix isn't a key
   in `coords` (i.e., `tiers._graph()` didn't shelve that source), `base is None` and the world
   is dropped from the returned `worlds` dict with no note, count, or print (sevenfold.py:
   200-202). Given how sensitive this project is to silent drops (Hard Rule 0's whole point),
   this warrants at minimum a `silence.note(...)` or a printed "N worlds dropped, source not
   shelved" count, even though it may currently be zero in practice.
9. **hostcheck.py `candidates()` docstring vs. code (hostcheck.py:276-368).** The docstring's
   "TWO LISTS" reasoning frames `grounded` as evidence (neighbour hosts, Wikipedia, the named
   D&D Wiki) and `spec` as guesses (suffix variants). But the bare-token and adjacent-pair
   `.fandom.com` guesses (hostcheck.py:323-327) are added via `add(h)` — default
   `speculative=False` — landing in `grounded`, not `spec`, contradicting the docstring's own
   description of what counts as "evidence." No functional impact today since neither list is
   truncated anymore, but it does affect *order* (title-guesses get tried before Wikipedia/
   neighbour evidence) and the comment misdescribes what the code does.
10. **manifest_builder.py:143, `FEATS_BLOCK_CHARS = 20000`** is dead code — no longer used to
    compute the actual budget (superseded by `context_budget.feats_block_budget(cfg)` at
    manifest_builder.py:329-331). Deliberately retained per its own comment ("RETAINED AS THE
    MEASUREMENT OF RECORD, NOT AS A DEFAULT") — flagged only so it isn't mistaken for live logic
    on a future pass.

## QUESTIONS

11. pick_model.py ranks and selects the best-scoring *resident* model rather than pinning
    `qwen3:8b` specifically (see Special Focus 3). Confirm whether "the standing local model"
    should be a hard pin or "best available under the GPU-only mandate" (current behavior).
12. catalogue_codex.py:159, `TYPE_CATEGORY.get(etype.lower(), THINGS)` — confirm THINGS is the
    intended default bucket for any codex element type not in the explicit map, versus e.g.
    Powers or a distinct "uncategorized" marker.
13. sweep_plan.py:59, an unreadable module is recorded with `lines: 0` and `unreadable: True`.
    It's correctly *reported* now (not silently dropped, per the file's own fix), but it still
    sorts last in `batches()`'s largest-first bin packing (sweep_plan.py:65-78) because its
    packing weight is 0 — should an unreadable file get a nonzero placeholder weight so it isn't
    always crammed into whichever bin is emptiest, or does "reported + wherever it lands" fully
    satisfy the concern this file exists to address?

## Confirmed correct (no action needed)

- pick_model.py's two `subprocess.run` calls (nvidia-smi, pick_model.py:179-181, 204-206) both
  pass `creationflags=_NO_WIN` — CREATE_NO_WINDOW correctly applied. No other module in this
  batch spawns a subprocess.
- manifest_builder.py's `pack_feats()` (manifest_builder.py:146-217) is genuinely Hard-Rule-0
  compliant pagination, not truncation: an entity whose feats exceed the budget is sliced across
  multiple whole blocks, every slice emitted, oversized single deeds get their own block rather
  than being dropped. Verified the flush-before-append fix is correct and doesn't lose data.
- sweep_plan.py `missing()` cannot report a false "0 uncovered" from either a corrupted or a
  lost-update-clobbered COVERAGE.json — both failure paths fail toward reporting *more* modules
  missing, never fewer. See Special Focus 1.
- sevenfold.py's `seams()` cut count is provably clamped to `SPAN` by construction
  (sevenfold.py:126-129); the "OVER SPAN" branch in `main()`'s printout (sevenfold.py:241-245)
  is a guard that can never fire, and the code already says so in its own comment ("this displays
  a GUARANTEE, not a discovery"). Not a new finding, confirmed correctly self-documented.
