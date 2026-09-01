# Sweep 40, batch 04 — audit

Modules read in full: `src/standards.py` (2217 lines), `src/completeness.py` (737 lines),
`src/sweep_plan.py` (576 lines), `src/worldseed.py` (466 lines), `src/pantheon.py` (365 lines),
`src/context_budget.py` (296 lines), `src/halo.py` (219 lines).

This is a mature, heavily-reviewed corner of the tree. Six of the seven modules
(`halo.py`, `context_budget.py`, `worldseed.py`, `pantheon.py`, `completeness.py`'s logic,
`sweep_plan.py`) show no live defects — every cap, gate, and discarded-verdict shape that a
sweep like this one hunts for has already been found and fixed in place, with the fix and its
reasoning left in the comment. `standards.py`, at 2217 lines, is likewise almost entirely a
record of previously-found-and-fixed defects. What I found and could verify against the source
follows.

---

## FINDING 1 — stale cross-references in `completeness.py:71`, two of them, same comment

**File:** `src/completeness.py`, line 71
**Quoted:**
```python
# `pages:<source>` and `doc:<slug>` are PROVENANCE SENTINELS, not hosts: an owner-supplied
# document or a hand-registered page list, recorded in the same column because that column is
# "where this source's material comes from". The project's own idiom for telling them apart is
# `str(h).startswith(("pages:", "doc:"))` -- binding_health.py:406 and health.py:255-257 both
# do exactly this, and health.py's comment says why: probing one as a host is meaningless.
```

**Verification:**
- `binding_health.py:406` is `silence.note("binding_health.py:escalate")` inside an unrelated
  exception handler in `quarantine()`. The actual `str(h).startswith(("pages:", "doc:"))` idiom
  in that file is at **`binding_health.py:1018`**:
  `hosts = sorted({h for h in hosts_map.values() if h and not str(h).startswith(("pages:", "doc:"))})`
- `health.py:255-257` is inside a compare-and-swap ledger-landing routine
  (`landed, why = _cas_land(LEDGER_PATH, prev, digest)`), nothing to do with sentinels. The
  actual sentinel check in that file is at **`health.py:486-488`**, and it isn't even the same
  spelling the comment claims ("both do exactly this"): it is two separate calls,
  `if h.startswith("pages:") or h.startswith("doc:"):`, not the tuple-arg form
  `str(h).startswith(("pages:", "doc:"))`.

**Why it's wrong:** both citations point at unrelated code. A reader who follows either link to
check "is this idiom really shared" lands on the wrong paragraph in the wrong function.

**Remedy:** update the comment to `binding_health.py:1018` and `health.py:486-488`, and either
correct "both do exactly this" to note health.py's is the two-call form, or align health.py's
spelling to the tuple form if that's actually intended to be the shared idiom.

---

## FINDING 2 — stale cross-reference in `completeness.py:345`

**File:** `src/completeness.py`, line 345 (inside `host_reachable`'s docstring)
**Quoted:**
```python
        # This asked `api_url(host)` and treated None as "unreachable". But `api_url` returns
        # None for MODE_RAW exactly as it does for MODE_DEAD -- `endpoint.py:176-179` -- and
```

**Verification:** `endpoint.py:176-179` is unrelated code inside `detect()`'s disk/memory cache
merge (`for h, v in disk.items(): if h not in _DIRTY: _MEM[h] = v`). The actual `api_url`
function the comment is describing is defined at **`endpoint.py:275-278`**:
```python
def api_url(host):
    """The API base for this host, or None when it has no usable API."""
    d = detect(host)
    return f"https://{host}{d['path']}" if d["mode"] == MODE_API else None
```
which does confirm the claimed behavior (None for both MODE_RAW and MODE_DEAD) — the *claim* is
correct, only the line number is wrong.

**Remedy:** `endpoint.py:176-179` → `endpoint.py:275-278`.

---

## FINDING 3 — stale cross-reference in `sweep_plan.py:273`

**File:** `src/sweep_plan.py`, line 273 (inside `record()`'s docstring/comment on the
`COVERAGE.json` fallback write path)
**Quoted:**
```python
            # AND THE PROMISE ABOVE WAS STILL HALF TRUE UNTIL ORDER 6794cb447987. Only the
            # LANDING was guarded; the `open` and the `json.dump` sat bare, and they are the
            # likelier raiser of the two. `silence.write_json` re-raises a failed dump
            # (silence.py:409-415, `except Exception: _discard_tmp(tmp); raise`), so the very
```

**Verification:** `silence.py:409-415` is the tail of `replace_retry`'s `OSError` handler
(`note("replace-failed:" + ...)`, `return False, (...)`), nothing to do with `write_json`'s dump
step. The literal pattern quoted, `except Exception: _discard_tmp(tmp); raise`, actually appears
at **`silence.py:515-516`**, inside `write_json`:
```python
    try:
        with open(tmp, "w", encoding="utf-8") as f:
            _j.dump(obj, f, **dump_kw)
    except Exception:
        _discard_tmp(tmp)
        raise
```

**Remedy:** `silence.py:409-415` → `silence.py:515-516`.

*(Note: `pantheon.py:359`'s cross-reference to `cosmology_graph.py:238-239` was checked and is
correct — cited alongside these three as a contrast, not a finding.)*

---

## FINDING 4 — silent truncation of diagnostic evidence, contradicting the function's own docstring

**File:** `src/standards.py`, line 604, inside `provider_pool_denominator()` (defined at line 555)
**Quoted (docstring, line 576):**
```
    NOTHING IS CAPPED -- every unverified provider is named. Pulled out of `check()` on purpose,
```
**Quoted (code, lines 600-605), the legacy/no-`counts` fallback branch:**
```python
        n_ver = len([r for r in rows if r.get("models")])
        n_unver = n_prov - n_ver
        unchecked = None
        names = sorted("%s (%s)" % (r.get("provider") or "?",
                                    str(r.get("error") or "no model list")[:40])
                       for r in rows if not r.get("models"))
```

**Why it's wrong:** the docstring's "NOTHING IS CAPPED" claim is true of the *list* (every
unverified provider gets a row, no `[:N]` on the list itself — that part is fine and matches the
rest of this file's Hard-Rule-0 discipline). But each row's **error text**, which is the actual
diagnostic content a person reads to find out *why* a provider is unverified, is silently sliced
to 40 characters with no ellipsis or truncation marker. This is the exact shape this same file
documents fixing at least four other times nearby (the `[:3]`/`[:60]` unrecognised-pool cap at
:1589, the `[:18]` source-name cap at :1371, the `[:120]` join cap at :1684, `epoch[:40]` in
`pantheon.py:313`) — a cap on the evidence for a claim, not a display convenience — except this
one was never caught. `names` and the sentence built from it feed `_over`, which lands in the
`observed` field of the HIGH-severity "model IDs their providers still serve" standard.

**Reachability caveat, stated honestly:** this branch only executes when
`data/PROVIDER_MODELS.json` lacks a `counts` key. `catalogue_models.py` (verified — its only
`"counts"` assignment is at line 263) always writes `counts` today, so the branch is a
backward-compatibility path for an old-format snapshot rather than the normal one. That is why
this is filed MINOR rather than MAJOR, not why it should be left alone: a fresh checkout, a
manually-edited snapshot, or a reintroduced old writer would hit it, and it would fail exactly
the way `epoch[:40]` and the other four already-fixed sibling caps did.

**Remedy:** drop the `[:40]`, or if the field genuinely needs bounding for display width, wrap
(as `pantheon.py --full` now does for its citations) rather than truncate silently.

---

## Coverage

`sweep_plan.record('run40', [...7 modules...], batch=4)` called to record this batch's coverage.
