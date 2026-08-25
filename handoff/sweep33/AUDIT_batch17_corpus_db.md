# Batch 17 — run33 — `corpus_db.py`, read by the maintenance run itself

Modules read: `corpus_db.py` (270 lines), in full.

**Why this exists as a seventeenth batch.** `corpus_db.py` did not exist when the run33 sweep
partition was computed. It appeared in `src/` at **15:28**, mid-run, written by a concurrent
session (its own docstring records the owner asking whether established tools would beat
home-made ones, so this is an attended session, not an unattended writer). `verify_math`'s
sweep-completeness check went red the moment it landed — `got ['corpus_db.py'], want []` — which
is that check doing exactly its job. Read and recorded by the maintenance run so the proof is
honest rather than waived.

## FINDINGS

### 1. corpus_db.py:189 — `rebuild()` discards the verdict of its own final write  [severity: MAJOR]

```python
    silence.replace_retry(tmp, DB)
    return {"sources": n_src, "entries": n_entry, "evidence": n_ev,
            "seconds": round(time.time() - t0, 2)}
```

`replace_retry` returns True/False precisely so the caller can tell whether the file landed, and
on Windows it returns **False** rather than raising when a reader holds the target open — which
is this file's exact situation, since the whole point of the module is that other processes read
`state/corpus.db`. The verdict is dropped, so `rebuild()` returns full counts and `main()` prints
`rebuilt: N sources, M entries...` **whether or not the database was replaced**. The failure is
silent and self-outliving: the old DB stays on disk, `age_seconds()` keeps reporting the *old*
`built_at`, and every later query answers from stale data while the rebuild that was supposed to
refresh it reported success.

This is the same shape as BUGS M36 (the write verdict that reached no caller) and as the
`suppressions.py:62` finding from batch 03 in this same sweep — a third instance of one pattern.

**Failure scenario:** the dashboard or a second session holds `corpus.db` open; `--rebuild` runs;
`replace_retry` exhausts its retries and returns False; `corpus_db.py --rebuild` prints
`rebuilt: 216 sources, 109295 entries ...` and exits 0 over an unchanged database.

**Suggested fix:** `landed = silence.replace_retry(tmp, DB)`, carry it in the returned dict, and
have `main()` say so and exit non-zero when it is False.

## QUESTIONS

### Q1. Six of the nine `CANNED` queries end in `LIMIT`; three deliberately do not.

`unaddressed`, `hostless` and `categories` carry **no** limit. `coverage`, `unjudged`,
`worst_cited`, `evidence` and `refused` end in `LIMIT 15`, and `types` in `LIMIT 25`.

Hard Rule 0 names "top N" outright, and the harm it describes is precisely this: an ordered
listing that is truncated returns a smaller universe wearing the shape of the real one. The
counter-argument is real too — these are interactive diagnostics, `--sql` accepts any query, and
the three unlimited ones suggest the author drew the line consciously rather than by accident.

**What would settle it:** whether the author considers a canned diagnostic a *report* (where a
top-15 is a legitimate summary) or a *listing* (where Hard Rule 0 forbids the cut). If the
former, a comment saying so would stop every future sweep re-raising it. If the latter, the six
`LIMIT` clauses should go. **Not changed by this run** — it is the owner's rule and the module is
hours old and still being written.

### Q2. `evidence_limit` in `rebuild()`

Defaults to `None` and exists to make a fast partial rebuild possible. Reads as a deliberate
opt-in speed control rather than a cap on the corpus, but it does mean a DB built with it holds
a silently partial `evidence` table with nothing in `meta` recording that. A `meta` row noting a
partial build would make the difference legible.

## VERIFIED, NOT A FINDING

`(d.get("provenance") or {}).get("roll")` was checked against the writer: `cachekey.text_digest`
returns `{"pages":…, "roll":…, "n":…}`, and older evidence files carry `provenance: null`, which
the `or {}` handles. Correct as written.

`query()` opens the database with `mode=ro` via URI, so `--sql` cannot write through it.

## CLEAN

The rebuild-whole-not-incremental decision, the schema and indices, the batched 5,000-row
inserts, the JSON-remains-canonical contract, and the `meta` bookkeeping all read correctly. The
module's own docstring is unusually honest about what it evaluated and rejected, including the
DuckDB attempt that Norton blocked.
