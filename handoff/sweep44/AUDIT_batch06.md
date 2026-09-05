# Audit — sweep44, batch 6

Modules read in full: `src/cascade_bridge.py` (2,047 lines), `src/corpus_db.py` (796 lines),
`src/thread_integrity.py` (628 lines), `src/address_space.py` (491 lines), `src/pick_model.py`
(404 lines), `src/deprecated/catalogue_local.py` (334 lines), `src/roll.py` (276 lines),
`src/scale_theories.py` (175 lines).

All eight modules are already heavily self-documented with dozens of prior fixes cited by order
ID and sweep number. Most of what a first read flags as suspicious turns out, on checking the
surrounding comments, to be a previously-fixed defect explained at length. This audit reports
only what survived that check, plus two items already filed that I looked at again as asked.

## Already-filed items (checked, not re-filed)

**`_TRANSIENT_WORDS` cooling down a permanent OTPM refusal (order af47010df391).** Confirmed
present exactly as described at `src/cascade_bridge.py:542-549`. I looked for whether the
matching is wider than the filed description: `"try again"` (line 545) is the broadest of the
markers — it also appears in ordinary per-minute throttle messages ("Please try again in
6m51s", quoted at line 689), so the false-positive surface isn't limited to the specific Groq
OTPM wording in the filed report. It's the same underlying class (a phrase generic enough to
appear in both a genuine temporary throttle and a permanent per-request-size refusal), not a
new bug, but worth noting that "Request too large" is not the only shape of permanent refusal
`"try again"` can paper over.

**`corpus_db.py freshness()` blind to deletions (order bf729d9664b1).** Confirmed at
`src/corpus_db.py:440-448`: `freshness()` stats only files currently present under
`data/records/*.json` and can never see a deletion. I checked whether `drift()` (a few
functions below, :454-492) shares the blind spot, since it's the other staleness-measuring
function in the same file. It does not — `drift()` does a full recount of `entries` across the
currently-present files and compares against the indexed total, so a deleted record shows up as
a real (negative) gap there. The defect is confined to `freshness()`'s mtime-only fast path, as
filed; it is not wider than described.

## New findings

### 1. `cascade_bridge.py` — the pin path can dispatch a live call to a local Ollama bucket, which the module elsewhere treats as an absolute invariant never to do

**Confidence: high — verified against the live `C:\Users\imarl\cascade\config.json` and
`cascade\router.py`, not just against `cascade_bridge.py`'s own text.**

The module states, more than once, that a claim on a local bucket must never happen because the
GPU is a single shared resource that callers manage themselves (e.g. the comment block at
`cascade_bridge.py:1360-1369`, "THE ROUTER NEVER HANDS OUT A LOCAL BUCKET"). That invariant is
enforced in exactly one place: the round-robin claim loop used when no bucket is pinned.

```python
# cascade_bridge.py:1355-1369
for _ in range(4 if pin is None else 0):
    claimed = _ROUTER.claim(pool, 1)
    if not claimed:
        break
    cand = claimed[0]
    # THE ROUTER NEVER HANDS OUT A LOCAL BUCKET. ...
    if cand.bucket.startswith(LOCAL_PREFIX):
        _ROUTER.release(cand)
        continue
    if _alive(cand.bucket):
        pinned = cand
        _tried_add(cand.bucket)
        break
    _ROUTER.release(cand)
```

The *pinned* path, a few lines above, has no equivalent check:

```python
# cascade_bridge.py:1329-1354
pinned = None
if pin:
    pinned = next((m for m in _ROUTER.models if m.id == pin), None)
    if pinned is None:
        ...
        return None
    _ROUTER.reserve(pinned)
    ...
    _tried_add(pinned.bucket)
```

Nothing here tests `pinned.bucket.startswith(LOCAL_PREFIX)`. If `pin` names a local Ollama
model, `_ask_call` reserves it, paces it, and dispatches through `e.stream_chat(...)` exactly as
it would a cloud model — the same path the claim-loop guard exists to prevent.

This is not hypothetical. `try_disabled()` (`cascade_bridge.py:1941-2007`) is a real, in-tree
caller that passes `pin=m.id` for every model in the pool that is currently disabled but "does
have a working key":

```python
# cascade_bridge.py:1963-1981
for m in _ROUTER.models:
    if pool not in (m.pools or []):
        continue
    st = _ROUTER.model_status(m)
    if st.get("available") or st.get("reason") != "model disabled":
        continue
    prov = m.provider or {}
    if not (prov.get("api_key") or prov.get("local")):
        out.append({"model": m.id, "bucket": m.bucket, "verdict": "no key"})
        continue
    was = m.enabled
    ...
    try:
        m.enabled = True
        got = ask("Reply with JSON only.", 'Return {"ok": true}',
                  {...}, pool=pool, timeout=timeout, pin=m.id,
                  max_attempts=1, served=served)
```

The gate at line 1970, `if not (prov.get("api_key") or prov.get("local"))`, treats "this
provider is local" as equivalent to "this provider holds a working key" — so a disabled *local*
model passes the gate exactly as a disabled *cloud* model with a key would, and the function
proceeds to pin it.

I checked this against the actual live config rather than trusting the docstring's framing
("Twelve providers are disabled for the only good reason there is -- no key. Seven models are
disabled while holding one"), because that framing reads as though it's only about cloud
providers. It is not, in practice: `C:\Users\imarl\cascade\config.json` currently carries six
`provider: "ollama"` model entries with `"enabled": false` in the `"coding"` pool
(`local-qwen25-14b`, `local-qwen3-14b`, `local-gemma3`, `local-qwen3-30b`, `local-qwen3-30b-q3`,
`local-gemma3-12b` — several annotated `"is not installed"`), and I traced `router.py`'s
`model_status()` (`cascade\router.py:281-296`) to confirm that for a local, disabled model it
sets `ready, reason = False, "model disabled"` before the local-specific branch, then reports
`available=False, reason="model disabled"` — exactly the shape `try_disabled()`'s guard at
line 1967 requires to proceed rather than skip.

So `python -c "import cascade_bridge; cascade_bridge.try_disabled()"` run today will, for each
of those six local models, flip `m.enabled = True`, pin it, and call `ask()` — which reaches the
pin branch above with no local-bucket check, reserves the bucket, and asks Cascade's engine to
run inference through Ollama for a model the file's own commentary says must never be reached
this way, several of which are not even installed. The likely outcome per model is either a
60-second deadline burn (this file's own `_ask_call` deadline machinery) or an Ollama load
failure surfacing as a generic engine error — not a clean "no key" skip, and not the "GPU stays
the caller's own fallback, never a hiding place for cloud traffic" invariant the surrounding
2,000 lines of commentary describe as load-bearing.

**Two possible readings**, since this file explicitly asks for QUESTION over DEFECT when the
line between tuning and bug is unclear:
- **Defect reading:** the pin path was written for cloud pins only, and the local-exclusion
  guard was simply never carried over from the claim loop when `try_disabled()`'s `prov.get`
  check was written to also admit local providers. This matches the shape of several other
  defects this file's own history describes (a guard present on one path and silently absent on
  its sibling).
- **Design reading:** perhaps `try_disabled()` is meant to also probe disabled *local* models as
  a way of testing "does this local model actually work if re-enabled" — but if so, the function
  should route that probe through the caller's own local fallback (the same one every other
  caller of this bridge is documented as already having), not through Cascade's engine and a
  90-second-class cloud deadline against a resource this file elsewhere calls "read.py's own
  fallback... reaching it through here would hide that fact behind a 'Cascade' label."

Given the extensive, repeated commentary in this exact file insisting the local bucket must
never be reached through Cascade, I lean toward defect, but flag both readings as asked.

### 2. `cascade_bridge.py` — a successful non-dict JSON reply is logged with the "tried:" label meant for failures

**Confidence: low — cosmetic/telemetry only, not a functional defect.**

```python
# cascade_bridge.py:1256-1280 (ask())
"ok": got is not None,
...
"model": ((got.get("_via") or "") if isinstance(got, dict)
          else ("tried:" + ",".join(_tried()) if _tried() else "")),
```

`_ask_call` only stamps `_via` onto `got` when `got` is a `dict` (`cascade_bridge.py:1758-1759`);
a schema-conforming reply that parses to a bare JSON list or scalar is returned as-is, non-`None`
and non-`dict`. In `ask()`'s metrics row this is logged with `"ok": True` (correct — the call
succeeded) but `"model": "tried:<buckets>"` — the exact string shape the surrounding comment
(`cascade_bridge.py:1263-1277`) describes as identifying a *failed* call's attempted buckets. A
reader of `state/model_metrics.jsonl` skimming for `"model"` starting with `"tried:"` to find
failed rows would misclassify a genuinely successful non-dict-payload call as one. This can't
crash anything (the crash this exact code was written to prevent, from `(got or {}).get(...)`
on a non-dict, is already fixed here), so it's a labeling ambiguity in the ledger rather than a
functional bug — flagged at low confidence since it may not be worth its own order.

### 3. `pick_model.py` — the per-model VRAM warning and the accept/refuse gate are sized against different quantities

**Confidence: low — plausibly deliberate (a live status hint vs. a policy gate), flagged as a
question.**

The residency gate that sorts models into `scored` vs. `refused` sizes against **total** VRAM
minus a fixed reserve:

```python
# pick_model.py:308-310
_measured_vram = total_vram_gb()
vram_measured = _measured_vram is not None
budget = (_measured_vram or 10.0) - VRAM_RESERVE_GB
...
if RESIDENT_ONLY and vram_measured and not resident(m, budget):   # line 328
```

`total_vram_gb()`'s own docstring explains this choice: "sizes against TOTAL minus a reserve,
not against free -- free varies with whatever the desktop holds this minute, and the mandate is
about the model class, not the moment" (`pick_model.py:176-178`).

But the per-model `[fit note]` printed beside every already-`scored` (i.e. already accepted)
model uses **free**, moment-of-run VRAM instead:

```python
# pick_model.py:340, 357
vram_gb = free_vram_gb()
...
note = f"  [{fit_note(m, vram_gb)}]" if vram_gb else ""
```

So a model that passed the policy gate (fits within total-minus-reserve) can still print
`[WILL OFFLOAD: needs ~X GB vs Y GB free ...]` if something else happens to be holding VRAM at
the moment the script runs, and conversely a model just barely refused by the total-based gate
would not necessarily show as tight if free VRAM briefly looked generous (though it never
reaches the fit-note line at all, since only `scored` models get one). This isn't necessarily
wrong — a live "will it actually fit right now" hint alongside a stable "is this model class
appropriate" policy decision are two different, both useful, pieces of information — but nothing
in the two docstrings cross-references the other, so a reader could easily take the fit-note's
"WILL OFFLOAD" as contradicting the "resident and usable" bucket the model was just placed in
one line above it.

### 4. `scale_theories.py` — `penetration_pressure`'s time divisor isn't guarded the way its area divisor is

**Confidence: low — no in-tree caller currently passes zero, and the function's own docstring
frames this as illustrative physics rather than a hardened API.**

```python
# scale_theories.py:139-147
def penetration_pressure(mass_kg, velocity_ms, contact_area_m2, contact_time_s=1e-3):
    force = (mass_kg * velocity_ms) / contact_time_s
    return {"force_N": force, "pressure_Pa": force / max(contact_area_m2, 1e-30)}
```

`contact_area_m2` is defended against a zero/negative caller value with `max(contact_area_m2,
1e-30)`, but `contact_time_s` — also a divisor — has no equivalent floor and will raise
`ZeroDivisionError` if a caller passes `contact_time_s=0` (e.g. modeling an idealized
instantaneous impact, which is exactly the kind of edge case a "what if the strike is
instantaneous" caller might reach for). The asymmetry between the two guards is the only reason
I'm flagging this rather than treating the missing-guard-on-a-default-only-parameter as normal;
it may simply not have come up yet because the only caller today is `main()`-less exploration.

## Modules with no findings beyond what they already disclose

- **`thread_integrity.py`** — read in full; extensively cross-checked its `classify()`,
  `load_thread_graph()`, and `_floor_verdict()` logic (dedup-by-unordered-pair, the
  both-directions RECIPROCAL test, the regression-floor ratchet). All uncapped listings verified
  uncapped (`main()`'s DANGLING/PARTIALLY-DANGLING/RECIPROCAL/ASYMMETRIC-* blocks all print `all
  {len(rows):,}`, no slicing). No new defect found.
- **`address_space.py`** — read in full; verified the derived-not-literal bit widths, the
  `_hash_offsets()` legacy-floor arithmetic (confirmed it cannot overlap fields as currently
  configured and grows monotonically), and the `pack()`/`fit()` no-modulo-on-charted-tiers vs.
  modulo-on-hashed-tiers split, which is a deliberate and correct distinction, not a bug. No new
  defect found.
- **`corpus_db.py`** — read in full beyond the already-filed `freshness()` item (see above); the
  CAS/atomic-write patterns in `rebuild()`, the CANNED query dict (verified no `LIMIT` anywhere,
  matching the file's own Hard-Rule-0 commentary), and `datasette_metadata()`'s write-verdict
  handling all check out. No new defect found.
- **`roll.py`** — read in full; the `mutate()` compare-and-swap, `exclude()`'s
  caller-supplied-rows write-verdict handling, and `in_scope()`'s fail-open behaviour all match
  their documentation and each other. No new defect found.
- **`src/deprecated/catalogue_local.py`** — confirmed the deprecation guard is real and
  effective: the unconditional `raise SystemExit(_REFUSAL)` at module level (line 94) executes
  before any of the function/class definitions below it, so nothing past that line is reachable
  by import or execution short of `--help`. Every defect the file's own header lists about
  itself (the `[:60]` slug truncation, the non-atomic `SWEEP_ROLL.json` rewrite, `main()`
  returning `None`, the swallowed-failure `per_cat[key] = 0`, the third-writer violation of the
  two-writer contract) is present exactly as described and deliberately unfixed; none of it is
  reachable at runtime. No new finding.

## Summary of findings by severity

- **High confidence, worth a work order:** 1 (`cascade_bridge.py` — `try_disabled()`'s pin path
  can dispatch a live call to a disabled *local* Ollama bucket through Cascade's engine, bypassing
  the local-bucket exclusion enforced only in the non-pin claim loop; verified reachable against
  six real disabled `ollama` entries in the live `coding` pool).
- **Low confidence / cosmetic:** 2, 3, 4 (metrics-label ambiguity on a non-dict success in
  `cascade_bridge.ask()`; a live-VRAM vs. total-VRAM inconsistency between `pick_model.py`'s
  accept gate and its per-model hint; an unguarded zero-divisor in
  `scale_theories.penetration_pressure`).
- **Already filed, re-verified (not re-filed):** the Groq OTPM `_TRANSIENT_WORDS` cooldown
  (af47010df391) and `corpus_db.freshness()`'s deletion blind spot (bf729d9664b1); neither is
  wider than already described, though the `"try again"` marker's false-positive surface extends
  to ordinary per-minute throttle text as well as the specific OTPM wording originally cited.
