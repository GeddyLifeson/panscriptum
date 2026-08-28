# run36 wave2a — cross-module needs from the read/ingest/cachekey/gpu_lane/corpus_db agent

Owner of this batch: `read.py`, `ingest_doc.py`, `cachekey.py`, `gpu_lane.py`, `corpus_db.py`.
Everything below touches a file this agent does not own, so it is filed rather than edited.

## 1. `handoff/run35/checks_F1.py` — a proposed check that is now stale (ACTION NEEDED)

`check_corpus_db_records_evidence_truncation()` (checks_F1.py:189-196) asserts the literal
string `evidence_truncated` appears in `corpus_db.rebuild`'s source. Order
`CORPUS_DB_EVIDENCE_TRUNCATED_DEAD_BRANCH` removed that flag today: `evidence_limit` was made
inert earlier this shift, so the flag could never be set and the WARNING built on it could never
fire. Nothing in `src/` reads it (checked: only `handoff/`, `__pycache__` and the built
`state/corpus.db` mentioned it), so no adopted net breaks — but that proposal must not be
adopted into `verify_math.py` / `drill.py` as written. Replacement, same intent, on the one
condition that can still make the evidence table partial:

```python
# order 85230c5c8c90 -- src/corpus_db.py, rebuild()
# An evidence table that was NOT SCANNED must be distinguishable from one that was scanned and
# found nothing. `--no-evidence` is now the only way to get the first, and it must say so.
def check_corpus_db_records_evidence_omission():
    import inspect
    import corpus_db as CDB
    src = inspect.getsource(CDB.rebuild)
    assert "evidence_included" in src, \
        "corpus_db.rebuild() no longer records whether evidence was scanned at all"
    assert "'evidence_included'" in src or '"evidence_included"' in src, \
        "corpus_db.rebuild() no longer writes an evidence_included row to meta"
    assert "evidence_truncated" not in src, \
        "the dead evidence_truncated flag is back; evidence_limit cannot truncate anymore"
```

## 2. Proposed nets for the three orders fixed today (for `drill.py` / `verify_math.py`)

Not added here — this agent does not own those files. All three are executable as written and
were run this shift in the scratchpad; each was also run against a pre-fix copy of the module,
and each pre-fix control reproduced the fault.

* **`read.queue()` must refuse an unreadable or empty host map** (order
  `READ_UNREADABLE_HOSTS_EMPTIES_THE_QUEUE`). Point `feats.HOSTS` at a truncated JSON file, an
  absent path, and `{}` in turn; `read.queue()` must raise `SystemExit` containing
  `REFUSING TO READ` in all three, and must still return a list over a populated map. This is
  the shape of the fault: the old code returned `[]` and `run()` printed a finished pass over
  zero entities and exited 0.
* **`read.read_entity()` must derive its write path at write time** (order
  `READ_CACHEKEY_WRITE_PATH_TOCTOU`). Stub `F.evidence_for` and `_ask` so that the *other*
  member of a colliding pair (`Magic 8 Ball` / `Magic 8-Ball`) lands at the natural path during
  the mining window; afterwards the natural path must still hold the other entity and this one
  must be at its disambiguated sibling. The pre-fix control clobbers.
* **`ingest_doc.mine()` must not emit a chunk larger than `CHUNK`** (order
  `INGEST_DOC_OVERSIZE_CHUNK_NO_RESPLIT`). Copy `data/docs/<slug>/pages.json` to a scratch tree,
  redirect `ingest_doc.DOCS` / `RECORDS`, stub `_ask`, and assert the largest passage handed to
  the transport is `<= CHUNK + label scaffolding`. Measured on the live Arcanum Worlds corpus:
  pre-fix largest chunk 12,620 chars against a 9,000 budget; post-fix 9,012.

## 3. Notice for the keeper / supervisor: `read.py` is running the old code

`read.py` was live throughout this shift and was deliberately not restarted. A Python process
does not re-read its own source (Hard Rule -1's fourth property), so the running reader still
has the fail-open host load and the entry-time write path. `codewatch` should exit it rc=17 on
the changed `src/` fingerprint and the STANDING set should bring it back on the current code;
if that has not happened within the restart budget, the fixes are not IN EFFECT yet.

## 4. No question left open for the owner

None of the five orders in this batch looked like deliberate design. The one judgement call
worth recording: `read.queue()` now also refuses a host map that reads cleanly but is EMPTY,
because an empty map produces the identical symptom the order was filed about (an empty queue
reported as a finished pass). If a genuinely empty `WIKI_HOSTS.json` is ever a legitimate state
for this tree, that refusal is the line to revisit — the message points the operator at
`src/feats.py --hosts`.
