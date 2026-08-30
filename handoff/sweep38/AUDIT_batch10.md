# SWEEP 38 — AUDIT, batch 10

Agent: `sweep38-batch10`. Run: `run38`. 8 modules, 4,471 lines, all read IN FULL.

Modules: `publish.py`, `corpus_db.py`, `scout.py`, `secondopinion.py`, `burgs.py`,
`cosmography.py`, `render.py`, `suppressions.py`.

Every finding below was verified against the code as it stands today (2026-08-29), and every
one that could be demonstrated cheaply was run in the batch scratch directory. Reproductions
are quoted inline.

---

## publish.py (1,413 lines) — read in full

Extremely well-worked file; the three publish locks, the prune/hold classification, `PushHeld`
and the `_unpushed()` confirmation are all sound as written. Four findings.

### 1. `--loop` never re-asserts the plant-wide halt — MAJOR
`main()` calls `_ESC.assert_clear()` once at line 1332, *before* the `while True:` at 1367. The
loop body (sync → render → write → push) never asks again, so a halt raised by any other job
while the daemon is up does not stop it pushing to the PUBLIC repo. `escalation.assert_clear`
re-reads `status()` on every call, so a per-cycle call would work. `overnight.py:1160-1172` is
the house pattern and carries the reasoning verbatim ("A supervisor that cannot read the halt
must stop the cycle loop"). `codewatch.exit_if_stale` at 1408 covers *code* drift only; a halt
is data, so it fires on nothing. This is Hard Rule -1's own IN EFFECT incident — the 14:28
`publish.py --loop` daemon — in the one dimension the codewatch fix did not close.

### 2. `render_page()` writes `docs/index.html` truncate-then-fill — MINOR
Line 996: `with open(PAGE, "w", ...)`. `write()`, twenty lines up, carries a long docstring
arguing exactly why `state.json` must not be written this way, and routes through
`silence.write_json`. `index.html` is the other half of the published page and gets the bare
open. A kill between truncate and flush leaves a partial `docs/index.html` that the next
cycle's `git add -A` stages and pushes. (`ensure_site` has the same shape for `.gitignore` /
`.nojekyll`, much lower stakes.)

### 3. `git()` clips git's own stderr to 220 characters with no marker — MINOR
Line 565-566, `(r.stderr or r.stdout).strip()[:220]`. `push()` then re-clips the same text to
`[:120]` (rebase) and `[:160]` (push refusal), and `main()`'s generic handler to `[:180]`.
Unlike a display cut over a database, this one is destructive: the subprocess has exited and
the rest of the message does not exist anywhere.

### 4. `snapshot()` swallows a failing `standards.check` — MINOR
Lines 537-541. On any exception the `standards` key is simply absent from the published state,
so the page renders without a standards panel and nothing anywhere says the check failed. This
is the module's own "absent is not clean" doctrine inverted.

### Not findings (checked and cleared)
- `leaks[:20]` / `leaks[:10]` at 1205/1210: both are preceded by `len(leaks)` in the same
  sentence, so the count is disclosed. Left alone.
- `scan_for_secrets` calling `suppressions.suppressed()` per file re-reads
  `SUPPRESSIONS.json` once per file (no cache in `suppressions.active()`). Fine for the ~550
  staged files; noted only because the `only=` docstring records a drill net walking 277,221.
- Files git ignores (`*.tmp`, `*.pre*`) are scanned but not published — false refusals only,
  the safe direction.

---

## corpus_db.py (747 lines) — read in full

### 5. `age_seconds()` has no caller anywhere — MINOR
Line 343. `grep -rn "age_seconds()" src/` outside its own definition returns only two comment
mentions. Its own docstring says "every reader in this module now asks [`freshness()`]
instead", which is true — `_freshness_banner`, `main()` and `drill.py:6462` all read
`freshness()["age_seconds"]`. Either delete it or say in the docstring that it is a public
helper kept for external callers; a live-looking function nothing calls is what `liveness.py`
exists to surface.

### Checked and cleared
- `INSERT OR REPLACE INTO source` keys on `name`, so two record files naming the same source
  would overwrite each other while `n_src` counted both — the `burgs.py` order 65ae84ee4bd7
  shape. **Not live**: measured 216 record files, 216 distinct non-null `source` values, zero
  duplicates. `meta.sources` = 216 = `SELECT COUNT(*) FROM source`. Latent only; recorded here
  rather than filed.
- `worst_cited`'s `ROUND(100.0*cited/entries,1)` yields NULL for a source with no COVERAGE row,
  and NULL sorts first under `ORDER BY pct ASC`. **Not live**: zero sources with
  `entries>=40 AND cited IS NULL`.
- `_cell()`'s ellipsis, the `CANNED` de-LIMITing, the `SPINE_LOOKUP_FAILED` third state, the
  pid/thread temp name and the gated `replace_retry` are all correct.

---

## scout.py (618 lines) — read in full

### 6. `EP.register()` raising aborts the whole sweep — MINOR
`scout()` line 394 calls `endpoint.register(source, kept)` outside any handler. `register()`
raises deliberately on an unreadable registry and after eight consecutive CAS refusals (it
returns `None` on success). `sweep()`'s loop at 503-504 has no handler either, so one
contended `SOURCE_PAGES.json` kills the cycle: `results` is discarded, and the SCOUT.json /
archive write at 551-586 never runs, so the cycle leaves no record at all — while the
attempt stamps written at 499 stand, costing every source in the batch its rotation slot. The
`never_asked` unstamp at 536 also never runs. Contrast the *host* registration ten lines
below, which is already wrapped and noted.

### Checked and cleared
Everything else here is in good order: `_mutate`'s CAS with the wrong-shape refusal, the
`reached is False` distinction, the uncapped `probeable` list passed to `verify()`, the
ranked-and-labelled prompt sample, the whole-name deferral print, and the
archive-before-trim roll-off. `hostless()` and the `_BAD_CHARS` self-check leave file handles
to the refcounter (ruff SIM115, which `secondopinion.py` now files as a real finding — already
covered there, not re-filed here).

---

## secondopinion.py (493 lines) — read in full

### 7. `mine_says(paths)` scopes one of its three answers — MINOR
Lines 358-386. The function's own comment at 375-380 records fixing exactly this fault for
`publish.scan_for_secrets` ("Comparing unlike measurements is this project's most expensive
recurring reporting bug"), and it fixed one of three:
- `liveness.scan()` — signature is `scan()`, takes no root at all. Always `src/`.
- `silence.audit(root=None)` — *does* take a root, and is called with none.
- `publish.scan_for_secrets(root)` — the only one that honours `paths`.

`run(paths)` meanwhile hands *every* path to ruff/vulture/detect-secrets. So
`report(["src", "prompts"])` prints outside numbers over two trees against house numbers over
one, under the word "vs". Default `[SRC]` hides it today.

### 8. Ruff/vulture messages stored at `[:160]` with no marker — INFO
`_ruff` line 250 and `_vulture` line 276. Measured live: 1,071 ruff findings on `src/`, 2 of
them over 160 characters, longest 162. `file_orders` puts `hits[0]["message"]` into the order
body, so a cut message can reach the queue. Same shape `corpus_db._cell` was repaired for
(order 6160ef68b229, "A MARKER, NOT REMOVAL"). Filed jointly with the sibling sites below.

### Question, not a finding
The module docstring's closing line says it "escalates to JANITOR (record it), not to OWNER",
but nothing here imports `escalation` — the recording is `silence.note`. Either that sentence
means "records at the JANITOR level of severity", in which case it is fine as written, or it
promises a call that is not there. Filed as a question.

---

## burgs.py (387 lines) — read in full

### 9. The module docstring's world count is ~4x stale — MINOR
Line 44: "Running the map generator 1,521 times to count hamlets is not a plan", and line 43
"across a thousand worlds nobody has rendered". Measured today: `worldseed.build_all()`
returns **6,005** worlds in 6.1 s. The in-file order note at line 292 says 5,986, so the header
and the body of the same file disagree. The 5,986 is a dated measurement inside a historical
note and is fine; 1,521 is stated as the present roll.

### 10. `SAMPLE — {w0['designation'][:60]}` — MINOR (bundled)
Line 326. The designation is the world's identity, cut to a column width with no marker, in
the header of the table a reader is about to interpret. Same argument `suppressions.main()`
already makes about the path column ("THE PATH IS THE ROW'S IDENTITY AND IS NOT TRUNCATED").

### Checked and cleared
`class_histogram` sums exactly to `n` (verified by construction: `hamlet` gets
`n - within_village`, and `_rank_at_or_above` returns `n` for any `lo <= HAMLET_FLOOR`).
`_rank_at_or_above`'s closed-form-then-correct is exact. The `per_world` list-valued keying,
the same-pass numerator/denominator, and the gated `write_json` are all right.
`burgs_for(limit=0)` falls through to `n` because `0 or n` — cosmetic, not filed.

---

## cosmography.py (335 lines) — read in full, nothing found

Verified live:
- `KARDASHEV_MIX` sums to exactly 1.0.
- `census("STANDARD")` validates: Type III 1.2e10 against 2.0e11 galaxies (6% occupancy,
  against the declared ~5% target); Type II, Type I and extant-vs-life-bearing all clear.
- `kardashev_to_magnitude(1e-30)` → `None` (the order be783948fd66 fix holds);
  `kardashev_to_magnitude(4e26)` → `M4`.
- `census("POCKET")` and `census("MINOR")` both refuse, exactly as the
  `SIZE_CLASS_MAX_GALAXIES` block says they will and says is an owner ruling to resolve.
  **No caller passes either**: every call site in `src/` (`address_space.py:397-398`,
  `pipeline.py:1900`, `verify_math.py:178,771,773`) passes `"STANDARD"`. The pending owner
  decision is therefore inert rather than breaking anything; filed as a question so it is in
  front of the owner rather than only in a comment.

---

## render.py (252 lines) — read in full

### 11. The SVG caption lies twice on one line — MINOR
Line 122. Two independent faults in the same f-string, both reproduced:

```
>>> R.containment_svg('universe','U1',[])       # zero children
caption: "1 child · span 1–7"
>>> R.view('universe', coord=sample, tree=tree)
{'children': 0, ...}   # the dict is right; the picture is not
```

- `n = max(1, len(children))` at line 111 is the *layout* divisor (it guards a division by
  zero at line 129) and is reused at 122 as the *count*. A node with no charted children is
  captioned "1 child" while the ring beside it is empty. `universe` is exactly that node on
  the live tree today.
- `span 1&#8211;7` is a hardcoded literal. Measured on `SEVENFOLD.json`: hyperverse,
  xenoverse and metaverse children are ids **0–6**, multiverse is `[0]`, universe is `[]`.
  The caption claims a span the data never has.

Remedy: caption from `len(children)` (keep `n` for the geometry), and either derive the span
from the ids present or drop the clause.

### 12. `children_of` truncates the `name` field it RETURNS — MINOR
Line 186: `"name": (v[0].split("::")[0][:24] if v else "")`. This is a returned data field, not
a render-time display cut — `containment_svg` applies its own separate `[:26]` at line 140.
Live on the current tree: 4 of the 22 children across the drawn tiers are cut mid-word, e.g.
`'Arcanum Worlds (Odyssey '` and `"DMs Guild: Xanathar's Lo"`. Remedy: return the whole name
and leave the truncation to the SVG, which is the reversible half.

### Noted, not filed
`v[0]` picks the first name in a bucket in record order rather than a ranked representative
(the id-3 hyperverse bucket has weight 97). `weight` discloses the count, so the reader is not
handed a smaller universe — left alone.

---

## suppressions.py (226 lines) — read in full

### 13. The code cap was removed; the damaged row was not repaired — MINOR
Order 7a6362fa3c91 removed `str(reason).strip()[:300]` and the comment records what it had
already eaten: "one of the three live rows was sitting at exactly 300 characters with its
closing SCOPE CAVEAT cut mid-word ('...this only sur')". That row is **still on disk**,
still 300 characters, still ending mid-word:

```
$ python -c "import suppressions as S; [print(len(r['reason']), repr(r['reason'][-40:]))
             for r in S.active()]"
175 ...
137 ...
300 "...the export SITE tree; this only sur"
```

The removed cap stops the *next* reason being destroyed; it cannot restore this one. The
clause a reviewer needs to judge whether the `data/feats/bloons_fandom_com/Encrypted.json`
exemption is still narrow is gone from the only copy. This needs the author's words back, so
it goes to OWNER.

### 14. Display reason cuts carry no marker — INFO (bundled with 8 and 10)
`problems()` line 175 (`reason[:60]`) and `main()` line 221 (`reason[:44]`). The module's own
comment defends these as reversible previews, which is right — but `corpus_db._cell` settled
the house form for a reversible cut (order 6160ef68b229): keep the width, add the ellipsis so
the reader can see there is more. `publish.py:506` has the identical `reason[:60]` inside the
`SUPPRESSED (...)` line.

### Checked and cleared
`_land`'s gated write, `add()`'s refusal on an unreadable file, `active()`'s deliberate
fail-closed, `fnmatchcase`, the `--check`/`--list` mutual refusal, and `problems()`'s
UNREADABLE row. Ran `S.problems()` live: `[]`, three active suppressions, none expired or
dangling. `problems()` re-globs the whole repo once per glob-shaped row — three rows today,
so it costs nothing; noted, not filed.

---

## Coverage

All eight modules read in full. Nothing skipped, nothing sampled.
