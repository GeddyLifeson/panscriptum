# Cross-module changes required by batch 08 (run #36, RUN rung)

Batch 08 owned `allsweep.py`, `entity_match.py`, `estate.py`, `runguard.py`, `standards.py`.
Everything below needs a file this batch did NOT own, so it is written here instead of edited.
Each entry states the exact change and the evidence behind it.

---

## 1. `src/workorders.py` — `battery_faults()` must read the new `estate_faults` key

**Owner of the file this shift:** not batch 08.
**Comes from:** order `5863bd9f566a` (MAJOR), whose `where` names both `src/allsweep.py:444-521`
and `src/workorders.py:130-172`. The allsweep half is DONE; this half is not.

`allsweep.main()` now grades the four named ESTATE tiers (CHARTER / WRITTEN / TERMINAL /
EXTERNAL) and lands the graded list at a new **top-level** key in `data/ALLSWEEP.json`:

```
"estate_faults": [ {"tier": "charter", "finding": "MASTER CHARTER MISSING", "detail": "..."} ]
```

`workorders.battery_faults()` (around lines 130-172) mirrors the OLD allsweep formula and reads
only `allsweep["estate"]["artifacts"]["bad"]`. So the queue still cannot see a fault in those
four tiers even though the sweep now fails on one. **Required change:** alongside the existing
`artifacts.bad` loop, iterate `allsweep.get("estate_faults") or []` and file each row the same
way, using `row["tier"]` and `row["finding"]` in the order text.

Deliberately NOT derived by re-reading `estate` and re-deciding severity in `workorders.py`.
The severity is set once, at the `note()` call in `estate.py`, and published by `allsweep`; a
second consumer inventing its own rule about which findings are red is how two layers end up
enforcing different invariants (the `prose_enabled` lesson in CLAUDE.md).

Note for whoever takes it: `estate_faults` is absent from any ALLSWEEP.json written before
run #36, so use `.get(...) or []` — a missing key there means "written by the old sweep", not
"no faults".

---

## 2. `src/drill.py` — lower `LIVENESS_CEILING` (a ratchet, in the lawful direction)

**Comes from:** order `84b584da5935`. `runguard._land` was dead and is now deleted, so the
liveness count fell.

Measured after batch 08's edits, on this tree:

```
liveness.scan() -> 33 findings total (33 dead, 0 tautology, 0 phantom, 0 unparsed)
drill.LIVENESS_CEILING = 41
```

The comment on the constant says: *"LOWER this when code is cleaned up."* Nothing in batch 08
may edit `drill.py`, so it is filed here. **Take the measurement again at the END of the shift
before lowering** — seven other batches are removing dead code in the same tree right now, so
33 is a reading from batch 08's moment, not necessarily the shift's final number. Lower it to
whatever `liveness.scan()` totals when the tree is quiet. Never raise it to go green.

---

## 3. `src/health.py` — three shared fixed `.tmp` names, and they tore two ledgers

**Comes from:** order `f979491d26a9` (`state/failures.json.corrupt` never triaged). The wreck
has now been read. The diagnosis points at `health.py`, which batch 08 does not own.

**What the wreck says.** `state/failures.json.corrupt` is 140 bytes:

```
{
 "silent:wiki_source-page_text-section:URLError": 53,
 "silent:wiki_source.py:160:URLError": 99
}nt:wiki_source.py:160:URLError": 79
}
```

The first 102 bytes are a **complete and valid** JSON document. The remaining 38 bytes are the
**tail of a different, longer document** — and that older document carried `79` for the very key
the newer head carries as `99`. So this is not a truncated write and not a half-flush: it is a
SHORTER document written from offset 0 over a LONGER one whose tail was never removed. Two
processes writing the same path, interleaved: both truncate, the loser writes its longer
payload, the winner then writes its shorter payload over the front, and the loser's tail
survives past the winner's closing brace.

**Why that can still happen today.** `health.py` writes through a temp file and
`silence.replace_retry`, which makes the RENAME atomic — but the temp name is FIXED and
therefore shared by every process in the kit:

```
health.py:140   tmp  = LEDGER_PATH  + ".tmp"
health.py:185   stmp = SAMPLES_PATH + ".tmp"
health.py:503   tmp  = path + ".tmp"
```

`state/failures.json` is, in `foreman.py`'s own words, *"the highest-traffic shared file in the
project"*, read-modify-written by `health.flush()` from every one-shot subprocess in the kit,
every 25 records and again at exit. Two concurrent flushes both open the SAME `.tmp`, interleave
into it, and one of them then renames the spliced result over the ledger. The rename being
atomic does not help when the bytes being renamed were written by two processes.

This is the identical collision `silence.write_json` was written to end (pid + thread in the
temp name) and that `runguard._land` was fixed for in run #33 — on a file with far more writers.

**Required change:** land all three of those writes through `silence.write_json` (or, if the
`replace_retry`-and-only-then-clear-`LEDGER` sequencing must be kept by hand, at minimum give
the temp name `os.getpid()` and `threading.get_ident()` the way `runguard._land_claim` does).

**Second wreck, same neighbourhood, different verdict:** `state/failure_samples.json.corrupt`
(4,579 bytes, 2026-08-26 06:32) **parses cleanly as JSON today**. It was set aside by the same
corrupt-branch, so that branch fired on a file that is not malformed — consistent with a reader
catching a mid-write state or a transient decode failure rather than a tear. Worth a look by
whoever owns `health.py`, but it is weaker evidence than the failures.json one.

**Neither wreck should be deleted.** They are the only physical evidence of this hazard.
