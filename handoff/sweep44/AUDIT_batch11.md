# Sweep 44, batch 11 — audit

Modules read in full, top to bottom: `src/overnight.py` (1,556 lines), `src/silence.py` (969),
`src/gpu_lane.py` (684), `src/endpoint.py` (563), `src/address.py` (461), `src/sweep.py` (346),
`src/catalogue_models.py` (323), `src/cachekey.py` (190), `src/catalog.py` (138). 5,230 lines
total.

Overall impression: this is some of the most heavily self-audited code in the tree. Nearly every
function carries a docstring recording a previous incident, the fix, and how it was measured.
Most of the classic defect shapes this sweep looks for — caps on ordered listings, `bool()`
laundering of a strict gate, tautological guards, silent swallows — have already been found and
fixed here, several of them explicitly in the last few weeks. What follows is what survived that
scrutiny: a handful of genuine findings, several explicit "checked, confirmed still correct"
notes on the highest-risk spots the task asked me to check hardest, and two items reported as
open questions rather than defects because I could not settle them from the modules in this
batch alone.

---

## 1. `src/overnight.py`

### 1.1 `safety_drill()`'s return code is discarded by its only caller — a same-cycle breach doesn't stop that cycle's launches (moderate confidence, mitigated but real)

`safety_drill()` (line 1036) runs `drill.py`, which is documented to raise an OWNER-level halt
itself if a safety net is breached:

```
1077:    if r.returncode == 1:
1078:        for x in (r.stdout or "").splitlines():
1079:            if x.strip().startswith("BREACHED"):
1080:                log("    " + x.strip())
1081:        log("  A SAFETY NET DID NOT HOLD — the library has halted itself. "
1082:            "Clear it with: python src/escalation.py --clear --ruling \"...\"")
1083:    return r.returncode
```

Its docstring says: *"this does not need to decide anything; it runs the inspection and reports
what the inspector found."* That's true as far as it goes — but its one call site, in `main()`'s
cycle loop, is a bare statement that throws the return value away:

```
1360:        safety_drill()
1361:
1362:        n, blocking = preflight()
```

`main()` only re-checks `escalation.assert_clear()` at the *top* of the *next* cycle iteration
(line 1351). Between `safety_drill()` finding a breach and that next check, the same cycle goes
on to `preflight()` and then to `start()`-ing dashboard, publish, foreman (with `--patch`,
i.e. autonomous code repair), overwatch and pipeline, plus conditionally prose, the roll, and a
blocking `run("read", ...)` that can hold the process for up to `--read-hours` (default 3h). None
of `run()`/`start()` re-ask the OWNER-level halt themselves — they only ask `_manager_stopped()`,
which is the rung-4 (MANAGER) ledger, a different and narrower check.

I confirmed `escalation.assert_clear()`'s own docstring says *"EVERY entry point calls this
before doing anything"* (`src/escalation.py:816-821`), which means each spawned job almost
certainly self-halts within its own `main()` the moment it starts — so the practical damage is
probably limited to wasted process spawns and log noise, not hours of unauthorized work. I
can't fully verify that from this batch (the individual job scripts are not in it), so I'm
reporting this as: the supervisor's own immediate reaction to a breach it just detected is
delayed by up to one full cycle, and the return value that would let it react sooner is thrown
away. Given how much of this module's own design is "ask the halt state as often as the cost of
being wrong justifies," this reads as an oversight rather than a deliberate choice — but the
mitigating self-check in each job means I'd rate impact as moderate rather than severe.

### 1.2 Residual un-marked truncations on diagnostic strings, inconsistent with this file's own fixes to the same class of cut (question, low-to-moderate confidence)

This file has, in the last few weeks, explicitly *removed* character caps on several diagnostic
strings on the grounds that they are forensic evidence a person reads to diagnose a failure —
`tail()`'s job-log lines (order fc7d688c1c6a), `preflight()`'s and `safety_drill()`'s stderr
tail lines (same order), the foreman/overwatch/ledger report lines (same order, three separate
sites). Each of those removals is documented with the same reasoning: *"a log line has no width
constraint."*

Six sites in the same file still cut an exception's `str(e)` to a fixed width with no removal
comment and no "..." marker:

```
569:        log(f"  {name}: {type(e).__name__} {str(e)[:80]}")
658:        log(f"  {job['name']}: {type(e).__name__} {str(e)[:80]}")
940:        return {"error": f"{type(e).__name__} {str(e)[:60]}"}
965:            f"-- continuing, but this cycle was NOT checked")   # str(e)[:120] two lines above
1056:            f"-- the nets were NOT inspected this cycle")      # str(e)[:120] two lines above
1150:            f"-- the page on disk is the previous cycle's")    # str(e)[:120] two lines above
```

Line 940's is the sharpest case: it lands in `snap["error"]`, which is then printed verbatim in
the supervisor log (`log(f"  coverage: SNAPSHOT FAILED ({snap['error']}) ...")`) — functionally
the same kind of "diagnostic string that becomes the log line" as `tail()`'s job-log lines, which
this same file's own comments call out as exactly the shape that must not be cut.

I'm not filing this as a confirmed defect: an exception's `type(e).__name__ + str(e)` is usually
short (unlike a wiki host name, a stderr tail, or a foreman remedy result, which can genuinely run
long), so 60-120 characters is plausibly always enough in practice and the omission may simply
be that nobody has hit a case where it truncated something that mattered. But given this file's
own explicit doctrine that a diagnostic string is "the whole content of the line, not decoration
around it" and the fact that five *other* diagnostic-string caps in this same file were treated
as bugs worth an order number, these six read like the same class of finding, just not yet
noticed. Flagging as a question for the owner rather than asserting these are load-bearing.

### 1.3 Confirmed clean — the areas flagged for particular care

- **The `prose_enabled` gate** (`_prose_enabled()`, line 48): delegates to `prose_gate.gate_open(cfg)[0]`
  inside a `try/except` that fails to `False` on any error. No `bool()` re-implementation
  survives; the historic defect this docstring describes (a quoted `"false"` opening the gate)
  is not present. Confirmed by reading the function body, not just the docstring's own claim.
- **`sweep.py`'s DEEPEST EVIDENCE table** (see §6.1 below) — did not re-file the already-filed
  order, per instructions.

---

## 2. `src/silence.py`

This is the module every atomic write in the project routes through, and I read it hardest per
the task's instruction. I did not find a new defect in the compare-and-swap primitives
(`replace_if_unchanged`, `replace_retry`, `digest_of`/`_digest_or_unreadable`), `write_json`,
`append_line`, or the AST-based audit/instrument pair (`_handler_is_observed`, `_handlers`,
`instrument`). Specifically checked and confirmed correct:

- `replace_if_unchanged` (line 510): re-digests `dst` immediately before every `os.replace` inside
  the retry loop (not once before the loop), so the compare-and-swap window is a single
  digest-then-rename rather than a compare followed by a sleeping retry — matches its own
  docstring's account of the m42/fede605db64f fix, and I traced the loop to confirm the digest
  read really does happen on every iteration (line 553), not just the first.
- `_handler_is_observed` (line 166): the re-raise test walks the AST for an `ast.Raise` node
  rather than string-matching `"raise"` against `ast.dump()` output (which would never match,
  since `ast.dump` capitalizes `Raise`); the "carries the exception into its own return value"
  test asks whether `node.name` is actually loaded in the body, not whether the literal string
  `node.name` occurs in the AST dump (which would be true for `except Exception as e:` on every
  handler, tautologically). Both of the tautologies this docstring says were found are, in fact,
  gone from the code as it stands.
- `append_line` (line 305): the Windows-specific lock/binary-mode fix is applied correctly —
  `_lock_exclusive` calls `msvcrt.locking` on Windows and `fcntl.flock` elsewhere; the data write
  opens with `getattr(os, "O_BINARY", 0)` so CRLF expansion is disabled on Windows; the "record
  unlocked" note fires only when a row actually landed without the lock (after the write
  succeeds), not inside the lock-acquisition `except` (which would double-count a write that then
  also failed).
- `note()` (line 733): a fully swallowing `try/except: pass` around its own body, correctly —
  the recorder itself must never raise, which the docstring states and the code delivers.

No new findings in this file. Given its role, I'd flag this as the strongest module in the
batch, not the weakest.

---

## 3. `src/gpu_lane.py`

### 3.1 A slot whose corrupt file can't be removed reads as "busy" rather than "unarbitrable" (question, low confidence)

`_take_slot()` (line 380) tries to reclaim a slot file that is present but unparseable (`rec is
None`, meaning either absent or corrupt — see the comment at line 411 explaining why the two are
collapsed) by checking `_unreadable_and_stale()` and, if stale, calling `_remove_retry()`:

```
436:            if _unreadable_and_stale(path):
437:                _remove_retry(path)
443:        try:
444:            fd = os.open(path, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
445:        except FileExistsError:
446:            continue
```

`_remove_retry()`'s own return value is not checked here. If removal genuinely fails on every one
of its four attempts (a persistent lock — Norton's file-scan interference is already documented
elsewhere in this project as a real, not hypothetical, cause of exactly this kind of denial), the
file is still there, `os.open(..., O_EXCL)` raises `FileExistsError`, and the loop `continue`s to
the next slot index rather than retrying this one. If this happens for every slot (`MAX_SLOTS` is
2 by default), `_take_slot()` returns `False` ("busy — ask again") for a condition that is not
actually a live holder, and `lane()` will wait out the full `SLOT_LEASE_SECONDS` (900s) before
falling through unmetered, rather than the near-immediate fallthrough the module's header
mandates for "a slot that cannot be created." This is the same defect *class* as the one this
module already fixed at order d316c46b67bd (the `None`-vs-`False` distinction for an unarbitrable
lane) — but that fix covers the `os.open` raising for reasons *other* than `FileExistsError`; a
persistently un-removable stale/corrupt file, which keeps raising `FileExistsError` specifically,
falls outside it. I'm reporting this as a question rather than a confirmed defect because it
requires `_remove_retry`'s four attempts to fail consecutively, which the module treats elsewhere
as a rare, near-worst-case condition rather than the steady state.

Everything else in this file — the slot/foreground lease heartbeat, the `_alive()` Windows PID
check, the `foreground()` refcounting under `_DEPTH_LOCK`, `status()`'s partial-listing flag —
matches its own docstrings on inspection; no other findings.

---

## 4. `src/endpoint.py`

No confirmed defects found. `detect()`'s DEAD-verdict TTL, `_save()`'s merge-not-overwrite CAS,
`register()`'s CAS-with-raise-on-persistent-failure, and `fetch_raw()`/`fetch_html()`'s
distinct-outcome-per-HTTP-status handling all match their documentation on reading. One
observation, reported as a question rather than a finding because it depends on server behavior
I can't verify from this batch:

### 4.1 `catalogue_models.py` sends an empty `Authorization` header rather than omitting it for keyless "local" providers (question, low confidence — flagged under the module it appears in, `src/catalogue_models.py`, not `endpoint.py`; noted here because it's the same shape as `endpoint.py`'s own care around not sending a malformed request to a picky server)

See §5.1.

---

## 5. `src/catalogue_models.py`

### 5.1 Empty `Authorization` header for keyless local providers (question, low confidence)

```
109:            req = urllib.request.Request(url, headers={
110:                "Authorization": f"Bearer {key}" if key else "",
111:                "User-Agent": "PanscriptumResearchBot/1.0"})
```

`ask_provider()` requires *either* a key *or* `prov.get("local")` to proceed past the
`UNCONFIGURED` check (line 91: `if not key and not prov.get("local")`). For a `local` provider
with no key, this sends a literal empty-string `Authorization` header rather than omitting the
header entirely. Most servers treat an absent and an empty auth header the same way, but some
strict implementations reject a malformed (empty-value) `Authorization` header outright, which
would make a legitimately-configured local provider probe as `UNREACHABLE` rather than `LISTED`.
I have no evidence this has actually happened — it's a code-smell observation, not a measured
failure — so it's reported as a question, not a finding.

Otherwise this module is clean on inspection: the `EMPTY_LIST` vs `UNREACHABLE` vs `UNCONFIGURED`
distinction is threaded correctly through `sweep()`'s `live`/`unverified`/`stale` accounting (the
three-outcome fix this file documents at "sweep42-batch14" is intact), and none of the "whole
list, not `[:N]`" fixes documented in comments (`available_sample`, the per-provider "Current
alternatives" line, the per-unverified-provider reason line) have regressed — I confirmed each of
the three call sites still prints/stores the full list rather than a slice.

---

## 6. `src/sweep.py`

### 6.1 DEEPEST EVIDENCE per-row truncation — likely the already-filed order, noted for scope only (not re-filed)

```
288:    best = sorted(rows, key=lambda r: (-r["axes"], -r["quantities"], -r["chars"]))[:top]
289:    print(f"   {'axes':>4}{'qty':>5}{'chars':>10}   {'character':<30}{'source':<26}native")
290:    for r in best:
291:        nat = f"{r['native']['value']:,.0f} (#{r['native']['rank']})" if r["native"] else ""
292:        print(f"   {r['axes']:>4}{r['quantities']:>5}{r['chars']:>10,}   "
293:              f"{r['name'][:29]:<30}{r['source'][:25]:<26}{nat}")
```

The `[:top]` slice on `best` is explicitly documented three lines above (line 306 in the
surrounding comment block) as an intentional `--top` request and is not a Hard Rule 0 violation.
What remains is that each displayed row's own `name` and `source` strings are still silently cut
to 29 and 25 characters with no ellipsis or "truncated" marker — a character or source name
longer than that loses its tail on the page with nothing saying so. I was told this exact table's
column-cutting is already filed under order 4f66afc16fbd, so I am not re-filing it; I confirmed
the cut is present and did not find it any wider than that description implies (only the two
identity columns, name and source, are affected; every numeric column is unclipped).

No other findings in this file. The funnel/nesting logic (`nested_run()`, the `STAGE_TESTS`
membership tests) was checked against its own stated "tested, not asserted" design and is
internally consistent: `nested_run` correctly tests `sets[order[j]] <= sets[order[j-1]]` (Python
set-subset comparison) to find the longest run of genuinely nested stages, and `report()` prints
the non-nested stages separately with both-direction crossover counts rather than folding them
into one misleading funnel. `ledger_report`-style "no cap" fixes elsewhere in this run's batch are
mirrored here correctly too (the "BIGGEST GAPS" and "REACHED BUT SILENT" source lists are
unclipped, matching the docstring's account of the fix).

---

## 7. `src/cachekey.py`

No defects found. `load()`, `write_path()`, `owns()`, `provenance_ok()` and `text_digest()` all
match their documentation: reads verify the stored `entity` field before trusting a hit (so the
80-char-stem/punctuation-fold collision this module exists to close can't silently hand one
entity another's evidence), and writes disambiguate onto a suffixed path only when the natural
path is genuinely held by a different entity. `provenance_ok()`'s three-way `(True, False, None)`
return is implemented as documented — `None` really is distinct from `False` (line 166-167: the
`None` branch is reached only when nothing was recorded at all, not when the digest merely
differs).

---

## 8. `src/catalog.py`

No defects found. All three query commands (`search`, `address`, `read`) and `stats` are
un-capped where the module's own history says they should be — `cmd_stats`'s "Populated sources
with NO books yet" list prints every entry, not a slice, matching the order-6434c1ba7b20 fix
documented in its comment. This is the smallest of the nine modules and the least eventful to
read; nothing to add.

---

## Summary of findings by confidence

**Moderate confidence (real code fact, impact judged mitigated but non-zero):**
- `src/overnight.py:1360` — `safety_drill()`'s return code is discarded, so a breach the drill
  detects doesn't stop the current cycle's own job launches; only the *next* cycle's
  `assert_clear()` check would. Likely mitigated by each spawned job's own entry-point halt check
  (per `escalation.assert_clear`'s docstring), which I could not verify from this batch.

**Questions (both readings given, not asserted as defects):**
- `src/overnight.py:569,658,940,965,1056,1150` — six residual `str(e)[:N]` diagnostic-string
  truncations, inconsistent with this same file's explicit removal of the same-shaped cut
  elsewhere (tail(), preflight/drill stderr, foreman/overwatch/ledger report lines).
- `src/gpu_lane.py:436-446` (`_take_slot`) — a persistently un-removable corrupt/stale slot file
  would read as "busy" (retry) rather than "unarbitrable" (proceed now), delaying fail-open up to
  the full 900s lease. Requires `_remove_retry`'s four attempts to fail consecutively, which the
  module treats as rare.
- `src/catalogue_models.py:110` — sends a literal empty `Authorization` header (rather than
  omitting it) when probing a keyless `local` provider; could make a strict local server probe as
  UNREACHABLE. No measured failure observed.
- `src/sweep.py:293` — DEEPEST EVIDENCE table still truncates `name`/`source` to 29/25 chars with
  no marker; very likely the same defect already filed under order 4f66afc16fbd — noted for
  scope confirmation only, not re-filed.

**Confirmed clean on the areas flagged for particular care:**
- `src/silence.py` — audited hardest per instructions; no defects found in the CAS primitives,
  `write_json`, `append_line`, or the AST-based silent-handler detector. The two historic
  tautologies this file's own docstrings describe are genuinely gone from the code.
- `src/overnight.py`'s `_prose_enabled()` — confirmed it delegates to `prose_gate.gate_open()`
  under a fail-closed `try/except`; no surviving `bool()`-style laundering of the gate.
- `src/sweep.py`'s DEEPEST EVIDENCE table's chapter/evidence-column cut — already filed (order
  4f66afc16fbd); not re-filed. Confirmed not wider than described.
