# Sweep run 37 — coverage repair: `compress_store.py` and `lognames.py`

**Why this file exists, and it is not a flattering reason.** When the coordinator transcribed
the 16 batch briefs it dropped one module from each of two batches: `compress_store.py` belongs
to batch 08 (9 modules, brief listed 8) and `lognames.py` belongs to batch 15 (9 modules, brief
listed 8). Both agents read and recorded exactly what they were given, correctly. The gap was
found by `sweep_plan.missing('run37')`, which is the check that exists for precisely this, and
it is worth recording that the gap was invisible in every other signal: both batch reports read
as complete, both said "all modules read in full", and both were telling the truth about their
own brief. **A sweep that covers less than it claims is this project's signature failure, and
the only thing that caught it was the coverage ledger.** That is the argument for `record()`
being called by the agent that did the reading, and for `missing()` being run afterwards.

Both modules were then read in full by the coordinator. They are small — 90 and 36 lines — and
this audit covers every line of each.

---

## `src/compress_store.py` (90 lines, read in full)

### FINDING 1 — MAJOR. A content-addressed store whose loader never checks the address.

`content_hash()` computes `sha256(text)[:32]` and that hash NAMES the file — `<hash>.zst` or
`<hash>.gz`. `load(path, codec)` then reads the blob, decompresses it, and returns the text
**without ever hashing it back**. The one property a content-addressed store gets for free is
that the filename is a checksum, and this store computes it, writes it into the filename, and
then declines to use it.

That matters here specifically, not in the abstract. The comment at the write site records that
a bare `open(path, "wb")` at the final path "leaves a torn blob sitting there permanently if the
process dies mid-write — and because the store is keyed by content, nothing ever comes back to
overwrite it unless the identical text happens to be stored again." The temp-then-replace fix
stops NEW torn blobs. It does nothing about any already on disk from before that fix, and it
cannot: the store never revisits a path that exists. A verifying `load()` is the only thing that
would find one, and it would find it at the moment the damage matters — when `catalog.py:97`
serves the chapter to a reader.

Cheap to close: hash the decompressed text and compare against the hash embedded in the
filename; refuse loudly on mismatch rather than returning wrong text. A stored chapter that
silently decompresses to something other than what was stored is the quietest possible corpus
corruption.

Filed.

### FINDING 2 — MINOR. The raise on a denied replace leaves its temp file, and nothing collects it.

`store()` correctly raises rather than reporting success when `replace_retry` is denied, and the
message even names the leftover: "the temp file %s is still on disk". That is honest and it is
the right direction — the caller (`generate.py:547`) catches it and moves on. But nothing ever
removes that temp, and the name carries pid and thread, so repeated denials on a hot path
accumulate uniquely-named files rather than overwriting one.

This is the same shape repaired in `silence.write_json` this shift (order b464a0311775), where
the denied-replace branch was leaking its temp for the same reason. The difference is that this
one is announced in an exception message rather than silent, which is why it is MINOR and not a
repeat of that order. Removing the temp before raising loses nothing: the blob is reproducible
from the text the caller still holds.

Filed.

### Checked and found HEALTHY (recorded so the next run does not re-derive it)

- **The write path is correct.** Temp-then-`replace_retry`, with a pid+thread-qualified temp
  name, and the reasoning for both is written down accurately. Two processes storing the same
  text compute the same `h` and would otherwise collide on `path + ".tmp"` — the comment says
  so and the code does it.
- **The failure direction is right.** `store()` raises instead of returning a success dict for a
  blob that did not land. The comment records why: the old behaviour let `generate.py:468` write
  a `compressed_path` into the catalogue for `catalog.py:97` to open later and fail on. A
  poisoned catalogue entry is worse than a raise, and the caller has a handler.
- **`silence.note("compress_store.py:zstd-unavailable")`** is on the `except ImportError` branch
  and is symbolically tagged — this was the line-number tag corrected earlier this shift, and
  the correction is right: the tag now names the condition rather than a line that had drifted.
- **The codec round-trip is sound.** `store()` records the codec it actually used and `load()`
  dispatches on the recorded value, so a corpus written under gzip stays readable after
  zstandard is installed, and a zstd blob raises a clear, named error if zstandard is later
  removed rather than returning garbage.
- **No caps.** Nothing here truncates text, and `content_hash`'s `[:32]` is a hash prefix used
  as an identifier, not a truncation of content — 128 bits is not a collision risk at this
  corpus size.

### Noted, not filed

`store()` recompresses and re-lands a blob even when the content-addressed path already exists.
Because the store is keyed by content the result is byte-identical, so this is wasted CPU and a
redundant write rather than a correctness fault. Recorded rather than filed: an existence check
would be a behaviour change on a path where the current behaviour is harmless, and the
compression cost is trivial beside the model call that produced the text.

---

## `src/lognames.py` (36 lines, read in full)

### FINDING 3 — MINOR. This file's own rule is broken by two of its own six entries.

The `OWNER` table maps each log to the command-line fragment that identifies its writer, and the
comment above it states the rule plainly: the fragment "must be specific enough to distinguish
two invocations of the same script: `feats.py --roll` is the page roll, a bare `feats.py` is
something else."

Four entries follow that rule (`read.py --run`, `feats.py --roll`,
`catalogue_web.py --recatalogue`, `magnitude.py --calibrate`). Two do not: `PIPELINE` maps to a
bare `pipeline.py` and `SWEEP` to a bare `sweep.py`.

`PIPELINE` is the one with a live second invocation. `pipeline.py` runs both as a member of the
supervisor's STANDING set and as a serial `run("pipeline", ...)` call in the same cycle — that
duality is the subject of open order 5d14e90b5043. `overnight.running()` matches the fragment as
a substring of the live command line, so the stall detector, the dashboard's Jobs panel and the
foreman's restart remedy cannot tell those two apart, and a hand-run `pipeline.py --phase X`
would answer for the daemon as well. Everything downstream of this table is keyed on it, which
is the whole reason the file exists.

Latent rather than live: the standing copy is the one that writes `pipeline_auto.log`, so today
the answer happens to be right. It is right by circumstance, not by construction, which is the
distinction this file was written to hold.

Filed.

### Checked and found HEALTHY

- **The constants are genuinely single-source.** All six are referenced through `LN.` by their
  readers, and the four literals that had survived in `overnight.py` and `foreman.py` were
  replaced with these constants earlier this shift (order bc98d8655e26), so writer and reader
  now share one definition — which is the entire premise of the module.
- **The `OWNER` mapping solves the real bug it documents.** Deriving a script name from a log
  stem asked whether `read_auto.py` was running; nothing by that name has ever run, so the
  reader, the roll and the pipeline were permanently invisible to the standard built to catch a
  job that is up and producing nothing. The table replaces that inference with a stated fact,
  and the account of both failure directions — the blind spot and the false alarm from stale
  legacy logs — is accurate.
- **No caps, no writes, no swallowed exceptions.** The module is declarations and comments; it
  has no failure modes of its own beyond the fragment specificity above.

---

## Coverage

`sweep_plan.record('run37', ['compress_store.py'], batch=8)` and
`sweep_plan.record('run37', ['lognames.py'], batch=15)` were recorded by the coordinator, who
read both files, after `missing()` reported them unread. Both modules were read in full before
either call.
