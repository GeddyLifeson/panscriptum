# Cross-module needs — LOCAL batch 4

## b635a4818c81 (compress_store.py:56) — generate.py needs a catch around `compress_store.store()`

**Fixed in compress_store.py** (owned module): `store()` now raises `RuntimeError` when
`silence.replace_retry()` fails to land the blob, instead of silently returning a success dict
that points at a file which was never written. This closes the hole where `generate.py:468-476`
wrote a `compressed_path` into the catalogue for a blob that never landed, for `catalog.py:97`
to fail on much later, disconnected from the actual event.

**Needs a change in `generate.py`, which I do not own.** The call site is:

```python
# src/generate.py, ~line 520, inside `for job, rh in tqdm(pending, ...)`
store_info = compress_store.store(text, compressed_dir)
```

This call is **not** inside any `try/except` — unlike every other failure mode in that same loop
(`generate_job()` failures and the P8 meta-language refusal, both above it), which are caught,
logged to `failures[job["address"]]`, and `continue`d so one bad job doesn't end a multi-hour
run. Now that `compress_store.store()` can raise, an unlucky `PermissionError` streak on one
chapter's rename (a reader holding the target open, per `silence.replace_retry`'s own docstring)
will propagate uncaught and crash the whole `generate.py` run instead of just failing that one
job.

**Suggested fix**, matching the existing pattern in that loop:

```python
try:
    store_info = compress_store.store(text, compressed_dir)
except Exception as e:
    silence.note("generate.py:store-failed")
    fail_count += 1
    failures[job["address"]] = {
        "error": str(e),
        "job_type": job["type"],
        "source_name": job["source_name"],
        "timestamp": datetime.datetime.utcnow().isoformat() + "Z",
    }
    save_json(cfg["paths"]["failures"], failures)
    continue
```

Whoever owns `generate.py` should add this before the store() call is exercised in production
(it is not exercised by the pilot/dry-run paths, so this won't surface until a real write
contention happens — but the current code would then crash the batch rather than skip one job).
