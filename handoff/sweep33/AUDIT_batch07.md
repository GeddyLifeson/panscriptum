# Batch 07 — run33
Modules read: read.py (1173 lines), zfighters.py (485 lines), pick_model.py (357 lines), context_budget.py (278 lines), ledger_guard.py (244 lines), descending_ladder.py (186 lines), scale_theories.py (148 lines)

## FINDINGS

### 1. context_budget.py:164,256 — JOB_OVERHEAD_CHARS is charged at the prose token ratio, not the content ratio, understating its true token cost  [severity: MAJOR]
`feats_block_budget()` folds `JOB_OVERHEAD_CHARS` (2000, described in its own comment as "the source name, the chapter label, the page span, the ceiling entity" — i.e. proper-noun-heavy content, not English instruction prose) into the `scaffold_chars` argument passed to `content_budget_chars()`:

```
255	    room = content_budget_chars(
256	        cfg, scaffold_chars(sys_used, template_text) + JOB_OVERHEAD_CHARS, "feats")
```

Inside `content_budget_chars`, that whole quantity is converted to tokens via `estimate_prose_tokens`, which uses `PROSE_CHARS_PER_TOKEN = 4.0` (measured against `system_style.txt` English prose):

```
164	    usable = window(cfg) - reserve_for(job_type) - estimate_prose_tokens("x" * int(scaffold_chars))
```

The file's own header is explicit that content (entity/source names, JSON) tokenizes far more densely and must stay at the pessimistic `CHARS_PER_TOKEN = 3.0` because it "has NOT been measured" and "guessing upward here is the direction that truncates evidence." Charging JOB_OVERHEAD_CHARS at 4.0 instead of 3.0 understates its cost by roughly 33% (at the max observed 2000 chars: 500 tokens counted vs. ~667 tokens actually likely), silently widening `content_budget_chars()`'s returned headroom in exactly the dangerous direction this module exists to refuse. This is real unit confusion (prose-rate applied to name/label content), not a rounding nicety — it works directly against the file's stated pessimism discipline.

### 2. ledger_guard.py:210 — `verify_chain()`'s SHRANK check never fires when a ledger is truncated to zero bytes  [severity: MAJOR]
```
207	                was = ((links[i - 1].get("ledgers") or {}).get(name) or {}).get("bytes")
208	                now = (cur or {}).get("bytes")
209	                if was and now and name in APPEND_ONLY and now < was:
210	                    problems.append("%s SHRANK between link %d and %d (%d -> %d bytes)"
```
`was and now and ...` treats `0` the same as "missing" (`None`). If HANDOFF.md is wiped to a genuinely empty file between two seals, `now == 0`, which is falsy, so the whole condition short-circuits to `False` and the shrink is never reported — the exact class of silent truncation this function exists to catch. In the current codebase this is masked because `check_all()` (via `check_structure`'s `MIN_BYTES` floor of 20000 for HANDOFF.md) runs before `verify_chain()` inside `assert_intact()` and would independently reject an empty HANDOFF.md — but that is incidental redundancy from the caller, not a property of `verify_chain()` itself. Anyone calling `verify_chain()` on its own (a drill script, a health check, a future caller) gets a clean pass on a chain whose most recent link records a wiped ledger. The fix is checking `was is not None and now is not None`, not truthiness.

### 3. ledger_guard.py:89-95 — the BUGS.md duplicate-id check is a tautology if the file's sections are not in the assumed order  [severity: MAJOR]
```
89	    if name == "BUGS.md" and "## Open" in text and "## Resolved" in text:
90	        i, j = text.find("## Open"), text.find("## Resolved")
91	        watch = text.find("## Watching")
92	        op = text[i:(watch if 0 < watch < j else j)]
93	        res = text[j:]
94	        both = sorted(set(re.findall(r"\[([Mm]\d+)\]", op))
95	                      & set(re.findall(r"\[([Mm]\d+)\]", res)))
```
This code hard-assumes `"## Open"` occurs before `"## Resolved"` in the file (`i < j`). If that ordering is ever reversed — sections re-ordered by a human edit, or a future template change — `i > j`, and Python slicing `text[i:j]` with `start > stop` silently returns `""`. `op` becomes empty, `both` becomes the empty set unconditionally, and the very check this code exists for — "no bug id may appear in both Open and Resolved" — passes even when every bug in Resolved is also still sitting in Open. This is a check that cannot fail once its ordering assumption is violated, with nothing else that would catch a bug filed twice.

### 4. read.py:518-524 — `_local_carded`'s oversized-prompt re-split path swallows a failed sub-call as "zero feats" instead of "unanswered"  [severity: MAJOR, currently dormant]
```
518	    head, _, body = prompt.partition(chr(10) + chr(10))
519	    merged = {"feats": []}
520	    for i in range(0, len(body), CHUNK):
521	        got = P.ask(c, system, head + chr(10) + chr(10) + body[i:i + CHUNK],
522	                    schema, timeout=180)
523	        merged["feats"].extend((got or {}).get("feats", []))
524	    return merged
```
Everywhere else in this file, a `None` reply from the model is treated as "nobody answered" and is carefully NOT cached and NOT allowed to mark an entity complete (`read_entity`'s `unanswered` counter, and the giant comment block above it explaining why that distinction is load-bearing). Here, if `P.ask` times out or errors on any sub-piece (`got is None`), `(got or {}).get("feats", [])` silently converts that into an empty feats list that gets merged into `merged` as if the piece had been read and found nothing. `merged` is never `None` even when every sub-call failed, so the caller (`read_entity`) treats the whole chunk as answered, caches it, and may write the entity as complete — exactly the "signature failure" this file's own comments describe at length elsewhere (a passage never seen by any model, filed as finished). This path is currently unreachable in ordinary operation because `CLOUD_CHUNK = CHUNK` (line 94) keeps every built prompt under the `CHUNK + 2000` threshold that triggers the re-split branch (line 507) — but it is live code, and the file's own history shows `CLOUD_CHUNK` has been tuned before and could be again.

### 5. context_budget.py:152 — `window()`'s default (8192) does not match the project's real num_ctx (6144)  [severity: MINOR]
```
151	def window(cfg):
152	    return int((cfg or {}).get("num_ctx", 8192))
```
`read.py`'s `config()` (the normal way `cfg` is built) defaults `num_ctx` to 6144, and this very file's header is built entirely around a measured 6144-token window ("num_ctx is 6144 tokens"). If `window()` is ever called with a `cfg` dict that omits `num_ctx` — a bare `{}`, or a config built by some other caller not going through `read.py.config()` — it silently assumes a window 33% larger than the real one, which pushes `content_budget_chars()` and `assert_fits()` toward exactly the overflow-and-silent-truncation failure this module exists to prevent. Two different silent fallbacks for the same physical constant, in coordinated modules, is a latent contract mismatch even though it does not fire under the current normal call path.

### 6. descending_ladder.py:91-95 — `rung_for_length()` silently returns rung 0 ("Continental") for any length above the whole descending ladder's domain  [severity: MINOR]
```
91	    best = DESCENDING[0]
92	    for r in DESCENDING:
93	        if metres <= r[3]:
94	            best = r
95	    return best[0], best[2]
```
`DESCENDING`'s largest edge is rung 0 at 1e6 m. For any `metres > 1e6` (i.e. bigger than the entire sub-planetary domain this file addresses), no entry in the loop satisfies `metres <= r[3]`, so `best` is never overwritten past its initialisation and the function reports "Continental" regardless of how far over 1e6 the input actually is — 5e6, 5e12, or 5e30 metres would all come back labelled the same rung-0 bucket instead of signalling "out of range for this ladder" the way `metres <= 0` does. Not exercised by `shrink_report`'s normal shrink-downward use, but nothing in the function guards against a caller passing an oversized value.

### 7. descending_ladder.py:129-149 — `shrink_report()`'s `from_m` parameter is accepted, never used, and never returned  [severity: MINOR]
```
129	def shrink_report(mass_kg, from_m, to_m):
130	    """Full accounting of a mass-conserving descent. Returns the physics, and the verdict."""
131	    rho = density_at_scale(mass_kg, to_m)
132	    conf = compton_confinement_energy(to_m, mass_kg)
133	    r_s = schwarzschild_radius(mass_kg)
134	    rung, name = rung_for_length(to_m)
...
143	    return {
144	        "target_rung": rung, "target_rung_name": name,
145	        "density_kg_m3": rho, "confinement_energy_J": conf,
146	        "schwarzschild_radius_m": r_s,
147	        "mass_conserved_is_lawful": not verdict,
148	        "objections": verdict,
149	    }
```
`from_m` never appears again after the signature. There is no assertion that the descent is actually downward (`to_m < from_m`), and the returned report doesn't even echo `to_m` (or `from_m`) back, so a caller holding only the returned dict cannot tell which descent it describes without keeping its own copy of the inputs. Either the parameter is dead, or a check/field that was meant to use it was dropped.

### 8. pick_model.py:242,295,308,324 — the printed "fits/offloads" note for each usable model is computed against currently-free VRAM while the accept/reject residency gate uses total-minus-reserve VRAM  [severity: MINOR]
```
295	    budget = (total_vram_gb() or 10.0) - VRAM_RESERVE_GB
...
308	    vram_gb = free_vram_gb()
...
324	        note = f"  [{fit_note(m, vram_gb)}]" if vram_gb else ""
```
`resident()` (the actual pass/fail test that sorts models into `scored` vs. `refused`, and therefore what `--write` will select) is deliberately built against total VRAM minus a fixed reserve, per its own docstring: "sizes against TOTAL minus a reserve, not against free... the mandate is about the model class, not the moment." But the human-readable annotation printed next to each already-`scored` model (`fit_note`, called with `vram_gb = free_vram_gb()`) uses momentarily-free VRAM instead. A model that has already passed the strict total-based residency gate — the one config.yaml will actually be pointed at — can still be printed with a "WILL OFFLOAD: ... expect a large speed penalty" warning purely because a browser or Wallpaper Engine happens to be holding VRAM at the moment the tool runs, producing self-contradictory output right next to the model the tool is about to select.

### 9. read.py:211,386,403 — `_FELL_BACK[0] += 1` is incremented from multiple worker threads with no lock  [severity: MINOR]
```
211	_FELL_BACK = [0]
...
386	                    _FELL_BACK[0] += 1
...
403	            _FELL_BACK[0] += 1
```
Both increments happen inside `_ask_ungated`, called concurrently by every worker in the `ThreadPoolExecutor` pool, with no lock — unlike the `done` dict in `run()`'s `work()`, which is correctly protected by `lock = threading.Lock()`. `+= 1` on a shared list slot is a read-modify-write, not an atomic operation; concurrent increments from multiple threads can lose updates. The only consequence here is a slightly-understated "N to GPU" figure in the progress line, so the blast radius is a cosmetic statistic rather than corrupted data, but it is a genuine unguarded read-modify-write on shared state in a file that is otherwise careful about exactly this class of bug.

## QUESTIONS

- **ledger_guard.py `verify_chain()`**: a hash chain of this shape cannot, on its own, detect tampering that also rewrites the *most recent* link and doesn't touch anything after it — there is no link downstream to disagree with it. In the current call graph this is covered because `assert_intact()` runs `check_all()` (which re-validates the live files directly) before `verify_chain()`, so a forged last link that doesn't match the real on-disk files would be caught by the structural check instead. Is that redundancy the intended second line of defence, or is `verify_chain()` meant to be trustworthy standalone (e.g. from a future drill/health check that calls it without `check_all()` first)? If the latter, it may need an external anchor (e.g. compare the last link's recorded digest against a fresh read of the live files) rather than relying on internal self-consistency alone.
- **descending_ladder.py `rung_for_length()` out-of-range behaviour** (finding 6): could be intentional "clamp to the coarsest rung available" behaviour rather than an oversight, if every caller is already guaranteed to only pass sub-planetary lengths. Worth confirming there's no path (e.g. a malformed source attestation) that could feed it a larger value expecting a signal rather than a silent Continental label.

## CLEAN

- **zfighters.py** — read in full. Hand-authored roster data plus straightforward glue (`compute()`, `value()`, `main()`). The Son Goku fallback-on-exception and the `anchor`/`epoch` "carried in from elsewhere" `.get(...) or ...` fallbacks are deliberate degrade-gracefully behaviour, not defects. No logic bugs found.
- **scale_theories.py** — read in full. All formulas (`bulk_export_beta`, `growth_strike`, `penetration_pressure`, `surviving_theory`) checked against their stated physics and unit conversions (TNT-equivalent constant, momentum/impulse force); all correct. No defects found.
- **pick_model.py `family_tier`, `score_model`, `save_config`, `resident`, `weight_gb`** — checked the tier-ordering logic (tier 5 checked before tier 1's "qwen" catch-all resolves correctly regardless of within-tier list order), the atomic-write path in `save_config`, and the residency arithmetic. All correct; only the one VRAM-baseline mismatch above (finding 8) stood out.
- **context_budget.py `estimate_tokens`'s `+0.999` ceiling approximation** — checked for an off-by-one at the epsilon boundary; it can theoretically undercount by one token when a fractional remainder falls below 0.001, but with the only two ratios actually used in this codebase (3.0 and 4.0), the possible fractional remainders are always multiples of 1/3 or 1/4 and never land in that danger zone. Not reported as a finding since it cannot currently fire.
