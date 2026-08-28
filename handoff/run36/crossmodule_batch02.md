# run #36, batch 2 — cross-module changes I could not make

Batch 2 owns `axis_correlation.py`, `binding_health.py`, `propagation.py`, `silence.py`,
`withdraw_chapters.py`. Everything below is in a module owned by another agent this shift and is
written out here instead of edited.

---

## 1. `src/suppressions.py:81` — `_land()` still writes through a fixed `.tmp` name

**Order:** `98831f6e6f6d` (MAJOR). The order names two sites; I fixed
`binding_health._land` and left this one.

**Verified against the source this shift** (not the stale line number — the anchor text is
`tmp = FILE + ".tmp"` inside `def _land(rows)`):

```python
    os.makedirs(os.path.dirname(FILE), exist_ok=True)
    tmp = FILE + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(rows, f, indent=1, ensure_ascii=False)
    return silence.replace_retry(tmp, FILE)
```

Two writers of `SUPPRESSIONS.json` collide on the temp file itself: both open
`SUPPRESSIONS.json.tmp` for writing, the second truncates the first, and whichever renames second
can land a partial file over the target. `silence.write_json` puts pid and thread in the temp
name — the fix `runguard._land_claim` already took — and returns the identical `replace_retry`
verdict this function gates on, so the gate the docstring is entirely about is preserved.

**The exact replacement** (the docstring above it is unchanged; only the four statements go):

```python
    return silence.write_json(FILE, rows, indent=1, ensure_ascii=False)
```

`write_json` does the `os.makedirs` itself, so the `makedirs` line goes too. Note it also writes
UTF-8 explicitly, which the current code does not — `ensure_ascii=False` plus the platform
default encoding is one non-ASCII reason string away from a row `_load` (which reads utf-8)
cannot read back.

**What NOT to change:** the `False` return must keep flowing to `add()`. `add()`'s refusal path
and the `_load` `ok` gate above it are correct and are a different order's work.

This is exactly the change I made to `binding_health._land`, verified there by test: unique temp
name, no `path + ".tmp"` left on disk, non-ASCII round-trips, `replace_retry`'s verdict returned
unchanged.

---

## 2. Nothing else

No other module outside batch 2 needed touching for these seven orders. The drill nets that arise
from this batch are staged separately in `handoff/nets/batch02.md`, per the shift rule that
`src/drill.py` and `src/verify_math.py` are owned elsewhere today.
