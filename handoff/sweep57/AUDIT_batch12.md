# AUDIT — sweep57, batch 12 (run57)

Modules read in full, top to bottom, in successive chunks: `src/overnight.py` (1968 lines),
`src/rigor.py` (1132), `src/chain.py` (915), `src/build_terminal.py` (667),
`src/catalogue_codex.py` (511), `src/sevenfold.py` (441), `src/navtree.py` (335),
`src/cosmology_graph.py` (260), `src/compress_store.py` (149). AUDIT ONLY -- no files edited,
nothing run beyond the two read-only queries the brief specifies.

## Known-work check

Before reading, `workorders.open_orders()` was queried and the open queue's full text for
`LINE_CITATIONS_IN_SRC_COMMENTS_HAVE_ROTTED_AT_SCALE` (order `89503c58409f`) was read. All nine
of these modules were also already read in full by three sweep56 batches:
`handoff/sweep56/AUDIT_batch10.md` (navtree.py, cosmology_graph.py, compress_store.py),
`AUDIT_batch11.md` (overnight.py, chain.py, build_terminal.py), `AUDIT_batch13.md`
(catalogue_codex.py), plus rigor.py and sevenfold.py in still-earlier sweep56 batches
(old-numbering batch12 and batch07). Every finding those batches recorded was re-verified
against the CURRENT source below rather than taken on trust; repeats are marked KNOWN and not
re-filed. Two genuinely new findings came out of this pass, both in the areas the brief asked to
be looked at hardest (chain-of-custody races, and overnight.py's rc=17/halt handling).

---

## NEW DEFECT 1 — `src/chain.py` — `harvest()`'s plain write can silently clobber
`refresh_continuity()`'s compare-and-swap patch (lost-update race)

**Lines:** 240-244 (harvest's initial read), 310-325 (harvest's unconditional write),
368-374 (refresh_continuity's own claim of safety).

`harvest()` reads the incremental cache once at the top:

```python
239    try:
240        with open(HARVEST_IDX, encoding="utf-8") as f:
241            idx = json.load(f)
242    except Exception:
243        _ = "silence-exempt: a missing or corrupt index rebuilds whole; documented safe"
244        idx = {}
```

...mutates that in-memory `idx` for whatever feats files changed, and lands it with a **plain,
unconditional** write -- no digest check, no compare-and-swap, no re-read-and-merge:

```python
310    if changed:
311        try:
...
319            if not silence.write_json(HARVEST_IDX, idx, ensure_ascii=False):
320                silence.note("chain.py:harvest-idx-denied")
```

`refresh_continuity()` (lines 345-428), by contrast, is explicitly built as a compare-and-swap
loop against the same file -- digest immediately before the read, retry against a fresh copy on
any mismatch, land through `silence.replace_if_unchanged` -- and its own docstring stakes a
safety claim on this asymmetry, arguing only one direction is protected:

```python
368    SAFE EVEN IF `chain.harvest()` IS MID-PASS, which is why this was not done as a bare script
...
373    exactly like `workorders._mutate`... A `harvest()` write landing in the gap is not lost:
374    this re-reads its output and re-applies the patch on top of it.
```

That paragraph proves `refresh_continuity()`'s own write is safe against a concurrent
`harvest()` write. It does not, and cannot, protect the other direction: `harvest()`'s write at
line 319 is unconditional on whatever `idx` it read at line 241. If `refresh_continuity()` lands
a patched `HARVEST_IDX` (fixing rows whose `continuity` was `None`, per its own docstring's
measured case: "44 [rows], across 11 hosts") in the window between `harvest()`'s read (240-241)
and its write (319), `harvest()`'s write overwrites the just-patched file with the older,
unpatched copy it is still holding in memory -- silently discarding the continuity patch, with
no digest mismatch, no exception, and no `silence.note` anywhere, because `harvest()` never asks
whether the file changed under it.

**Why it matters:** this is exactly the lost-update shape the sweep brief asks for. The module
went to real trouble to make `refresh_continuity()` safe against a concurrent `harvest()`, using
the same CAS primitive as `workorders._mutate`, but treated the hazard as one-directional. The
two are documented as safe to run concurrently ("this was not done as a bare script from the
queue: `chain.py` owns `HARVEST_IDX` and may be holding it during a shift"), which is precisely
the condition under which the un-protected direction fires. The failure mode is silent and
recurring: any `--refresh-continuity` run that lands while a `harvest()` pass (a normal part of
`chain.main()`, itself called from the pipeline) is mid-read has its patch erased the moment
that `harvest()` pass finishes, with nothing to indicate it happened -- the exact "answered with
nothing indistinguishable from answered honestly" shape this project's own doctrine (`silence.py`)
exists to prevent elsewhere.

**Confidence: DEFECT.** Verified directly against current source; not present in any prior
audit of this file (sweep56 batch11 read this file in full and reported it clean). Not KNOWN --
checked the open queue for `harvest_idx`/`refresh_continuity`/`chain_harvest`, no hits.

---

## NEW DEFECT 2 — `src/overnight.py` — a deliberate `rc=17` restart (or any other
"on-purpose" exit named by `name_rc`) is not distinguished from a real crash when the
supervisor decides whether a cycle was idle

**Lines:** 743-746 and 834-838 (`run()`/`join()` return `f"rc={rc}"` for every nonzero code,
`name_rc(...)` used only in the *log line*, not in the returned status), 1794-1797 (the two
calls that feed `statuses`), 1890-1897 (the `busy` computation), and the code's own comment at
line 1835 acknowledging the gap without closing it.

`run()` and `join()` both correctly *name* an exit code for the log (`name_rc(p.returncode)`,
which explicitly labels `rc==17` as `"(ON PURPOSE — source changed, restarting to run the
current code)"` at line 1104-1105) -- but the **status string returned to the caller**, which is
what the idle/broken-cycle logic actually acts on, collapses every nonzero code to the same
generic shape:

```python
746        return "ok" if p.returncode == 0 else f"rc={p.returncode}"   # run()
838        return "ok" if rc == 0 else f"rc={rc}"                        # join()
```

Those strings feed `statuses`, and the idle-cycle test only excuses three specific values:

```python
1890        busy = [x for x in statuses if x in ("already-running", "manager-stopped",
1891                                             "probe-blind")]
1892        if busy and snap["cycle_seconds"] < MIN_CYCLE_SECONDS:
```

`"rc=17"` is not one of them. The module's own comment fifty lines above this, added when
`read.py` was promoted into `STANDING`, walks the three cases a fast cycle can be in and states
this outcome directly, without treating rc=17 as special:

```python
1834      * the reader ran and DIED ON STARTUP, returning in seconds -> read returns
1835        "rc=..." -> NOT busy -> the cycle counts toward IDLE_LIMIT.
```

So a `read.py`/`feats.py --roll` invocation that exits **on purpose** because `codewatch`
noticed `src/` changed under it (rc=17 -- the exact mechanism Hard Rule -1's own text calls out
by name as "this project's longest outage came from a watcher reading jobs-exiting-on-purpose as
jobs-crashing") is counted identically to a job that crashed on line one. Three such fast,
non-busy cycles in a row (`IDLE_LIMIT = 3`) drive the supervisor into:

```python
1956        log("  HALT: every job has returned instantly for "
1957            f"{IDLE_LIMIT} cycles. That is not an idle library, it is a broken one.")
1958        log("  Read the job logs named above; the failure is in the first lines of one.")
1959        break
```

...which **ends the supervisor process outright** (the `break` falls through to `"supervisor
finished"` and `return 0` at the bottom of `main()`). The branch immediately above this one
(lines 1940-1955) does check the *owner-level escalation halt* first and waits rather than
breaking if the library is halted -- but a burst of `rc=17` restarts is not an owner halt; it is
routine `codewatch` behaviour, and the code has no path that recognises it as such before
reaching the "broken" verdict.

**Why it matters, and why it is live risk right now:** this run (run57) is itself a
16-batch/multi-agent sweep with a foreman `--patch` lane that edits `src/` unattended, which is
exactly the condition the file elsewhere calls "the NORMAL condition of the tree during a sweep"
(quoting `sweep_plan.py`'s docstring about the same hazard). If `codewatch` trips `rc=17` on
`read.py` or `feats.py --roll` (both invoked via `run()`/`join()` in the cycle body, not only via
the keeper's `STANDING` restarts, which correctly stay out of `statuses` entirely) three cycles
running during an active edit burst, the supervisor will misdiagnose deliberate, healthy
restarts as "the library is broken" and stop itself -- the identical outage class this same file
spent great effort closing for the *keeper's* restarts (`_manager_stopped`, the blind-probe
handling) and for the *idle-vs-halted* distinction thirty lines below (2026-08-25 lesson
recorded in-line: "The safety mechanism caused the outage it exists to prevent"). This is the
one gap in that otherwise very thorough treatment.

**Confidence: DEFECT.** The code's own comment (line 1834-1835) proves the author considered
"rc=..." as a generic case and reasoned about *why it should count toward IDLE_LIMIT* (to keep
the counter strict against real startup crashes) without separately considering the `rc==17`
sub-case that `name_rc` itself treats as categorically different everywhere else in this same
file. Checked the queue for an existing order on this exact shape (`IDLE_LIMIT`, `busy`,
`rc=17`+`idle`): no hits. This is the "mirror of the watchdog issue" the brief asked to be
checked for; it is not identical to `autostart.py`'s filed issue (that one is about the hourly
start-budget after a halt lift; this one is about the per-cycle idle/broken verdict), and is
filed as its own finding rather than assumed to be the same one.

Everything else asked about specifically for overnight.py checked out clean on this fresh read:
- **A MANAGER stop stays stopped.** `_manager_stopped()` (lines 645-683) is asked, module-level,
  by both `run()` (688-696) and `start()` (770-774), and separately and explicitly by the
  keeper thread (1556-1560) before any restart of a `STANDING` job -- verified all three call
  sites are present and none bypasses it.
- **No stage starts before the drill/halt checks.** In the per-cycle loop, `codewatch.exit_if_stale`
  (1642-1654), the re-asked plant-wide `escalation.assert_clear` (1656-1672), `safety_drill()`
  (1697), and `preflight()`'s blocking check (1699-1704, which `break`s the loop on a control-
  character corruption) all run and are all evaluated **before** the first `start("dashboard", ...)`
  call (1715) -- verified by reading the loop body in order; nothing between `main()`'s entry and
  the first stage launch skips any of the four.

---

## Repeat findings from sweep56 (re-verified against current source, unchanged, not re-filed as new)

- **`overnight.py:1685-1688`** — the seven `assert_clear` cross-file citations
  (`dashboard.py:1068`, `publish.py:1594`, `foreman.py:1711`, `overwatch.py:922`,
  `pipeline.py:2876`, `read.py:1408`, `feats.py:1813`) are still stale, unchanged from the
  `overnight.py:1686-1688` finding in `handoff/sweep56/AUDIT_batch11.md`. This matches the open
  queue's `LINE_CITATIONS_IN_SRC_COMMENTS_HAVE_ROTTED_AT_SCALE` order (`89503c58409f`), whose own
  evidence names "`overnight.py:1667-1669` -- seven assert_clear call sites" as one of its
  examples. **KNOWN(89503c58409f).**
- **`overnight.py:202`** — the `publish.py:render_page(), ~line 1266` self-hedged citation is
  still stale and has drifted further: `render_page` is now at `publish.py:1383` (was 1364 at
  sweep56's time, ~1266 when the comment was written). Previously flagged as a QUESTION in
  `AUDIT_batch11.md` (batch11 found it at ~98 lines off; it is now ~117 off). Not re-filed as new;
  still open, still hedged with `~`.
- **`build_terminal.py:647-648`** — the two citations (`catalogue_codex.py:315-331`,
  `generate.py:700-706`) are still stale; the actual content is at `catalogue_codex.py:488-496`
  and `generate.py:147` respectively (verified by grep against current line numbers). Identical
  to the `build_terminal.py:647` finding in `AUDIT_batch11.md`. Not re-filed as new.
- **`cosmology_graph.py:131-132`** — still cites `weave.py:519` and `pipeline.py:2401`; the real
  `shared_sample` write sites are now `weave.py:671` and `pipeline.py:3179` (verified by grep).
  Identical to the `cosmology_graph.py:131-132` finding in `AUDIT_batch10.md`. Not re-filed as new.
- **`catalogue_codex.py`, main()'s element loop (`if not key: continue`)** — still the one
  drop path in this file that does not follow its own report-everything convention, still
  dormant (0 of 4,489 parsed manifest names currently normalise to empty). Identical to the
  QUESTION in `AUDIT_batch13.md`. Not re-filed as new.

All four of the above are drift-only re-confirmations: the underlying code has not changed since
the prior sweep, only (in two cases) the drift has grown by a handful of lines as the cited files
kept growing. None required new investigation beyond a grep to confirm the current target line.

---

## Nothing found (explicit, per module, beyond what is listed above)

- **`src/rigor.py`** — read in full. `_validate_reciprocal_matrix` still refuses non-square,
  non-finite, non-positive and non-reciprocal input before any arithmetic runs (raises, never
  clamps). `bradley_terry`'s Ford's-condition refusal and the two-fault independent-evaluation
  fix (order `0fa1ad406c7e`) are both real and reachable, not decorative. `main()`'s two display
  cuts (`_AUDIT_ROWS`/`_unaccounted` warning, and the `load_bearing` tie-extended cut at
  1118-1125) are both disclosed and neither splits a tie silently. No re-implemented gate, no
  fail-open path, no new stale citation found beyond what sweep56 already recorded as fixed.
  Nothing new.
- **`src/sevenfold.py`** — read in full. The `_sample`/`_wsample[:8]` console previews are
  explicitly headed "(first 8 of N)" and do not touch the uncapped `SEVENFOLD.json` write, which
  is itself gated on `silence.write_json`'s landed verdict with the verdict reaching the exit
  code (lines 423-436). `UNSHELVED` tracking (263-265, 305-324) reports rather than silently
  drops sources absent from the resonance graph. Nothing new.
- **`src/navtree.py`** — read in full. `audit()` is still load-bearing: `main()` refuses
  `--write` when `problems` is non-empty (311-313) and the exit code reflects both a non-clean
  audit and a denied audit-record write (329-330). The register/hyperverse naming tie-breaks
  (`register_for`, the hyperverse `top = max(...)` at line 187) use the deterministic
  `(count, name)` secondary key, not raw hash order. Nothing new.
- **`src/cosmology_graph.py`** — read in full beyond the citation drift above. `build_graph()`
  still writes the whole `shared_sample` list uncapped and the pair list is written complete
  (`pairs_filtered: False` stated in the artifact itself); the `--write` path gates on
  `silence.write_json`'s landed verdict and does not print a false "wrote" line on denial.
  Nothing new.
- **`src/compress_store.py`** — read in full. `store()` still writes through a pid+thread-
  stamped temp name and `silence.replace_retry`, raises (never returns a fabricated success
  dict) on a denied replace, and cleans up its own temp file with the cleanup failure itself
  guarded and noted. `load()` still re-hashes decompressed content against the address the
  filename claims and refuses (raises) on a mismatch rather than returning unverified text.
  Nothing new.
- **`src/build_terminal.py`** — read in full beyond the citation repeat above. The atomic-write
  pattern for `output/registry_terminal.html` is intact (unique pid+thread temp name,
  `silence.replace_retry`, denied write returns rc 1). `<script>` injection is neutralised
  (`data.replace("<", "\\u003c")`) before the JSON is spliced in. JS-side `esc()` is applied at
  every sink checked (`shelfmark`, `panel`, `selectSource`, `selectWorld`), matching the
  in-line history of the `esc()` gaps that were previously found and closed (orders `3b37494e20db`,
  `c000fbc3c378`). Nothing new beyond the repeat citation above.
- **`src/catalogue_codex.py`** — read in full beyond the repeat QUESTION above. All five
  collision classes it tracks (section-title `norm()` clashes, ambiguous section binding,
  ambiguous register descriptions, duplicate `(type,name)` elements, unmapped element types) are
  still reported uncapped. The roll write and the per-record write are both gated on their
  landed verdict, and both verdicts reach the process exit code (lines 443-449, 480-489,
  500-506). Nothing new beyond the repeat QUESTION above.
- **`src/chain.py`** — read in full beyond NEW DEFECT 1 above. `write_result` is still the one
  writer for `CHAIN.json`, still unconditionally called on every code path in `main()` including
  both refusal paths, and still persists `unmatched`/`edges`/`strengths` uncapped with only the
  console previews capped and disclosed. `adjudicate_mutuals`'s three-way UNPROBED/self-split/
  half-dated handling is internally consistent with its own docstring. On the specific concern
  in the task brief about `chain.py` being a "ledger" with tamper-evidence gaps: `CHAIN.json` is
  not a cryptographic or append-only ledger -- it is a derived artifact recomputed and
  atomically overwritten each cycle from the live feats corpus, with no hash-chaining between
  versions and no claim to be tamper-evident across time. No such gap was found because no such
  property is claimed by this module; the actual concurrency hazard found is NEW DEFECT 1 above,
  a lost-update between this module's own two internal writers, not an external-tampering gap.

---

## Coverage

Recorded via `sweep_plan.record` for run57 batch 12 (see command output below); all nine modules
were read in full, top to bottom, in this pass.
