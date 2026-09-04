# Sweep43 batch06 audit

Files read in full: `src/mutate.py`, `src/corpus_db.py`, `src/thread_integrity.py`,
`src/autostart.py`, `src/pick_model.py`, `src/deprecated/catalogue_local.py`, `src/tells.py`,
`src/scale_theories.py`, `src/module_index.py`.

Method: every candidate below was re-read against the exact lines cited, and traced for what
actually happens at runtime, before being written down. Several plausible-looking candidates were
checked and dropped because the code already handles them correctly (see "checked, not filed" at
the end of each section for the ones worth recording so nobody re-derives them).

---

## src/corpus_db.py

### FINDING C1 — MAJOR — `freshness()` cannot detect a deleted record, so the staleness banner
can UNDERSTATE the gap

`src/corpus_db.py:440-448`:

```python
newer = 0
for p in glob.glob(os.path.join(HERE, "data", "records", "*.json")):
    try:
        if os.path.getmtime(p) > built:
            newer += 1
    except OSError:
        newer += 1                 # a record we cannot stat is a record we cannot vouch for
out["newer_records"] = newer
out["stale"] = newer > 0
```

What happens: `freshness()` (and therefore `_freshness_banner()`, the line printed above every
query result) decides staleness purely by walking the CURRENT contents of `data/records/*.json`
and comparing each file's mtime to the index's `built_at`. If a record file is *modified* after
the index was built, its later mtime is caught and `stale` correctly becomes `True`. But if a
record file is *deleted* after the index was built — a source re-filed, a duplicate removed, a
correction that drops a bad record — there is nothing left in the glob to compare: the loop simply
never sees it, `newer` is not incremented, and if no other file changed, `freshness()` returns
`stale=False`, `"no record has changed since the index was built"`. The `source`/`entry` rows for
the deleted record are still sitting in `corpus.db` (a whole rebuild is the only thing that would
drop them), so the index is now describing a source that no longer exists, under a banner that
says nothing has changed.

Why it matters: this is exactly the class of defect the module's own docstring exists to rule
out — `freshness()`'s docstring says outright "this index does not promise to be fresh. It
promises to SAY how stale it is, every time it is read... a report that has drifted from the
thing it describes is worse than no report, and the difference between the two is entirely
whether the report admits its own age." A deletion is a real, unremarkable way for `data/records/`
to change (source re-filing, dedup, a correction), and it is invisible to this detector by
construction — the banner can read clean while the index quietly still contains a ghost. `drift()`
(the `--drift` path) does catch it indirectly — `real` would drop below `indexed`, producing a
negative gap — but nothing there names deletion as the cause either, and `drift()` is not on the
default query path; `_freshness_banner()` is the one every canned query and every `--sql` result
prints, and that is the one with the blind spot.

Remedy (OWNER/RUN judgment, not mechanical): `freshness()` needs a second signal alongside mtime
— e.g. compare the CURRENT set of source names on disk (via a cheap `os.listdir`/glob of stems)
against the set of source names recorded in `corpus.db.source` at rebuild time, and treat a source
present in the index but absent from disk as stale too. This changes what gets written into `meta`
at rebuild time (the set of source basenames, not just counts), so it is a real design change, not
a one-line fix — filed as RUN.

### Checked, not filed
- The nine `CANNED` queries carry no `LIMIT` (compliant with Hard Rule 0); `_cell()`'s 40-char
  display truncation is reversible (marked with an ellipsis, full value stays in the DB, `--sql`
  recovers it) and is the disclosed exception Hard Rule 0 itself allows for display-only cuts.
- `rebuild()`'s tmp-file naming, the spine-code three-state handling (`SPINE_LOOKUP_FAILED` vs
  `NULL` vs a real code), and the `evidence_limit` no-op are all correctly implemented and match
  their docstrings.
- `connect(path=None)` re-reads module-level `DB` at call time rather than binding it at import
  — verified correct, not a stale-binding bug.

---

## src/mutate.py

This file has an unusually dense internal audit trail (dozens of `order <hash>` citations to
prior fixes across at least four earlier sweeps). It was read in full and cross-checked; most
candidate defects turned out to be already-fixed history recorded in the comments. One residual
gap was found.

### FINDING M1 — MINOR — `active()` can raise instead of returning a verdict, if the lock file
holds valid-but-non-dict JSON

`src/mutate.py:197-212`:

```python
def active():
    try:
        with open(LOCK, encoding="utf-8") as f:
            rec = json.load(f)
    except FileNotFoundError:
        return False, None
    except Exception:
        return True, {"unreadable": True}
    pid = rec.get("pid")
    ...
```

What happens: the docstring says "An unreadable lock is treated as HELD" and the `except
Exception` branch delivers that for anything `json.load` cannot parse. But if the file parses to
valid JSON that is not a mapping — `null`, `42`, `[]`, a bare string — `json.load` succeeds, the
`except` block is never entered, and `rec.get("pid")` raises `AttributeError` (lists/ints/strings
have no `.get`), uncaught, straight out of `active()`. That is neither of the two states the
function promises ("not held" / "held"): it is an unhandled exception that will propagate into
whatever called `active()` — `_lock_acquire`, and indirectly `publish.py`'s own read of the lock.

Why it matters: it is a narrow gap in the file's own fail-closed argument. `_lock_acquire` always
writes a dict, so this needs external corruption or a partial/mixed write to trigger — but a
partial write (kill mid-`json.dump`) is exactly the scenario `_lock_release`'s docstring spends a
paragraph reasoning about, so the file already treats "truncated on disk" as a live risk elsewhere
and just doesn't cover this one shape of it (valid JSON, wrong type).

Remedy: add `if not isinstance(rec, dict):` right after the `json.load`, and route it through the
same `return True, {"unreadable": True}` path the parse-failure case uses. Small, mechanical —
LOCAL.

### Checked, not filed
- The sandbox/junction architecture (`sandbox()`), the live-file digest check in `_run_mutation`,
  `verify_restore`, `_lock_acquire`'s O_EXCL race-free create, and the ownership-vs-age reaper
  logic in `reap_orphans`/`_owner_pid` were all traced end-to-end and match their docstrings — no
  path was found where a sandbox mutation could land on the live tree, and no restore path skips
  the `finally: _write(path, original)`.
- `_pid_alive`/`_pid_alive_windows`: both fail toward ALIVE on any ambiguous signal, as claimed.
- `_lock_release`'s handling of an unreadable-but-token-checked record (falls through to
  unconditional remove) matches its own documented reasoning (O_EXCL means an unreadable record
  can only be this process's own).
- The mutation-site locator machinery (`_spot`, `_between`, `_token_pos`, `_col`'s UTF-8
  byte-vs-character fix) was re-derived by hand against a couple of the cited examples
  (`prose_gate.py`'s three-byte marker case) and is correct.

---

## src/thread_integrity.py

Read in full. `classify()`'s DANGLING/PARTIALLY-DANGLING/IMPLIED-UNRECORDED/RECIPROCAL/
ASYMMETRIC-LAWFUL/ASYMMETRIC-SUSPECT partition, `load_thread_graph()`'s address resolution, the
`_floor_verdict()` regression floor, and every report list in `main()` (all uncapped, correctly
ranked, correctly oriented for the directed asymmetric case) were traced by hand and are correct.
No findings. This module already carries its own dense history of fixed defects (BUGS m12,
2b4e0f497aac, order 7bffb5634d7a, order aa075aa80f5c) and none of them have regressed.

---

## src/autostart.py

### FINDING A1 — MINOR — the staleness check itself is not throttled the way its sibling
rate-limits are, only the log line is

`src/autostart.py:391-400`:

```python
if codewatch is not None and now - said_stale_at >= START_WINDOW_SECONDS:
    is_stale, why = codewatch.stale("autostart")
    if is_stale:
        said_stale_at = now
        _log("THIS WATCHDOG IS RUNNING OLD CODE (%s). ...")
```

Compare the sibling pattern immediately below for `said_unknown_at`:

```python
if now - said_unknown_at >= START_WINDOW_SECONDS:
    said_unknown_at = now
    _log(...)
```

and for `said_budget_at`:

```python
if len(starts) >= MAX_STARTS_PER_HOUR:
    if now - said_budget_at >= START_WINDOW_SECONDS:
        said_budget_at = now
        _log(...)
```

What happens: in both sibling cases the timestamp is stamped unconditionally inside the outer
`>= START_WINDOW_SECONDS` gate, so the *check* (not just the log line) only fires once per hour
once the gate closes. For `said_stale_at`, the stamp only happens inside the nested `if is_stale:`
— so as long as the tree stays NOT stale, `said_stale_at` never advances past `0.0`, and the outer
condition `now - said_stale_at >= START_WINDOW_SECONDS` is true on every single iteration of the
loop. `codewatch.stale("autostart")` — a real fingerprint comparison against `src/` — therefore
runs every `CHECK_SECONDS` (180s, 20x/hour) for the entire life of this permanently-running
watchdog, rather than once per `START_WINDOW_SECONDS` (3600s) as the surrounding comment block
("all three of these are rate-limited... a persistent condition would otherwise [fire] twenty
identical lines an hour") implies was intended for all three variables uniformly.

Why it matters: the LOG line is still correctly throttled (it only ever fires when `is_stale` is
actually `True`, and then the stamp does update), so this is not a user-visible spam bug — it's an
efficiency/consistency defect: this is the one file in the project whose docstring is specifically
about a daemon that runs forever and "watches everything except itself," and its own self-check is
running 20x more often than designed, for the life of every login session on the machine, with
nothing to show for the extra 19 calls.

Remedy: move `said_stale_at = now` out from under `if is_stale:` so it is stamped unconditionally
inside the outer gate, matching `said_unknown_at`/`said_budget_at`. One-line, mechanical — LOCAL.

### Checked, not filed
- `_twin_watchdog()`'s retry loop, `install()`'s atomic-write-then-readback, `installed_state()`'s
  three-way current/stale/unreadable classification, `supervisor_alive()`'s tri-state passthrough,
  and the hourly start budget in `watch()` were all traced and are correct.
- `main()`'s `--status` path prints `ON.running(job)` for the roster (`ON.ALL_JOBS`) with a plain
  truthy test rather than the tri-state distinction `supervisor_alive()` uses two lines above it in
  the same function — so an unreadable process table would print "not running" for every other job
  even though the correct answer is "could not tell." This looked at first read like the same bug
  class the rest of the file goes to great lengths to avoid. It is NOT filed as a finding because
  `overnight.running()`'s own docstring explicitly signs off on exactly this collapse for
  "read-only" consumers of the value ("the read-only callers that only ever ask `if running(x)`...
  behave exactly as they did — they were already getting False from a blind probe"), naming
  foreman's repair gates and standards' roster as the blessed callers. Whether a human-facing
  `--status` line belongs in that same blessed category, or should show UNKNOWN like the
  supervisor line right above it, is a judgment call — moved to Questions below.

---

## src/pick_model.py

Read in full. `family_tier()`'s tier-descending substring match, `score_model()`'s log-scaled size
term, the GPU-only residency gate (`resident()`, `RESIDENT_ONLY`, the `vram_measured` provenance
flag that keeps a guessed 10GB fallback from silently driving a hard refusal), and `save_config()`'s
atomic write-then-readback were all traced and are correct. No findings.

One observation, not filed as a finding because it is very unlikely to matter in practice:
`budget = (_measured_vram or 10.0) - VRAM_RESERVE_GB` (`pick_model.py:310`) uses `or`, not
`is None`, so a real-but-exactly-zero `total_vram_gb()` reading would silently fall back to the
guessed 10.0GB even though `vram_measured` (computed separately via `is not None`) would report
`True`. `nvidia-smi` reporting 0 MB total VRAM for a real card is not a realistic failure mode, so
this is noted rather than filed.

---

## src/deprecated/catalogue_local.py

Read in full. The module refuses to run (and refuses to even finish importing) for any invocation
except `-h`/`--help`, exactly as its own header describes — `raise SystemExit(_REFUSAL)` executes
at module-load time, before any of the six previously-real defects it documents (bare `open(...,
"w")` writes to `data/records/`, non-atomic `SWEEP_ROLL.json` rewrites, the swallowed-failure
`per_cat[key]=0`, etc.) are reachable. This matches Hard Rule -1's fourth property being correctly
applied here: the refusal is IN the code, not only in `src/deprecated/README.md`. No findings —
the six documented defects are already known, already deliberately unrepaired (kept as "the record
of a failure mode"), and out of scope per this task's own instructions not to relitigate settled
owner questions.

---

## src/tells.py

Read in full. The `_BAD_CHARS` transit guard, the `_anchor()` sentence-boundary rewrite for
`^\s*`-prefixed patterns, the escape-mangling control-character check over every compiled pattern,
and `prompt_in_sync()`'s line-ending-folded substring comparison were all traced and are correct.
No findings.

---

## src/scale_theories.py

Read in full. `surviving_theory()`'s exactly-one-survivor assertion (raises, not `assert`, so it
survives `python -O`), and `bulk_export_beta()`/`growth_strike()`/`penetration_pressure()`'s
arithmetic were checked and are correct. The five module-level constants (`C_LIGHT`, `G_NEWTON`,
`HBAR`, `NUCLEAR_DENSITY`, `PLANCK_LENGTH`) are confirmed unused by any function in this file —
this matches the standing owner question named in this task's own brief and is NOT re-filed.

---

## src/module_index.py

Read in full. The `GROUPS` stale-name check, the `placed`/`rest` set bookkeeping that guarantees
every module in `src/` appears exactly once (either under a named group or under "Everything
else"), and the atomic tmp-then-`replace_retry` write with a checked verdict were all traced and
are correct. No findings.

---

## Questions (owner/curatorial judgment — not filed as work orders)

1. **autostart.py `--status`'s job-roster line** (`autostart.py:492-495`): should it distinguish
   "could not tell" from "not running" the way the supervisor line two statements above it does?
   `overnight.running()`'s own docstring blesses collapsing None to False for "read-only" callers
   by name (foreman's repair gates, standards' roster), but does not name this status display.
   Given this file's central theme is exactly this tri-state distinction, an inconsistent
   presentation within the same function is at minimum worth a ruling on whether `--status`
   counts as one of the blessed callers.

2. **corpus_db.py `freshness()`'s deletion blind spot (finding C1)**: the remedy requires deciding
   what "the index knows about the set of sources on disk" should look like structurally (a new
   `meta` row at rebuild time, most likely) — filed as a RUN work order rather than resolved here
   because it changes what gets written to the database, not just how it's read.
