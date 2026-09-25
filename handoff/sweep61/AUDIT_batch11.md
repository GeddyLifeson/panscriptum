# sweep61 batch 11 — audit

Scope (read in full, start to finish, chunked where the harness truncated a single Read call):
- src/overnight.py (2007 lines)
- src/dashboard.py (1248 lines)
- src/onomast.py (844 lines)
- src/weave.py (709 lines)
- src/anchors.py (576 lines)
- src/cleanup.py (452 lines)
- src/sweep.py (374 lines)
- src/roll.py (313 lines)

All eight modules confirmed read in full (no sampling). This is a heavily self-audited codebase
already — the large majority of what looks odd on first read is a documented, already-fixed past
defect explained in situ. Only genuinely new observations are reported below; known/handled
items are not re-filed.

## Special note requested: overnight.py's prose-start decision

Traced the exact logic in `overnight.main()`'s cycle body (~line 1732 onward):

```python
drill_rc = safety_drill()
...
if os.path.exists(manifest) and _prose_enabled() and drill_rc != 1:
    start("prose", [os.path.join(SRC, "generate.py"), "--manifest", manifest], "prose_auto.log")
elif os.path.exists(manifest) and _prose_enabled() and drill_rc == 1:
    log("  prose: NOT started -- a safety net was breached this cycle ...")
```

Two findings came out of tracing this, both VERIFIED by reading the source directly (no execution).

### Finding A — the prose gate is fail-OPEN on an ambiguous/failed drill result, not just on a clean one

`safety_drill()`'s own comment states the gate's intent: "`== 1` only: rc 0 is a clean inspection,
and None or any other code means the drill DID NOT RUN ... and is not evidence of a breach."
Reading `safety_drill()` end to end: on a subprocess exception/timeout it returns `None`; on a
returncode outside `{0, 1}` (argparse failure, an unnamed Windows NTSTATUS crash code, anything
else) it logs "DID NOT COMPLETE" but still falls through to `return r.returncode` — it does not
return early. So `drill_rc` can be `None` or any non-1 integer whenever the drill did not actually
complete an inspection, and the gate `drill_rc != 1` treats every one of those the same as a clean
`0`: prose starts.

This is the one job the surrounding comment itself flags as needing this gate ("`generate.py` ...
has NO halt interlock anywhere in it ... It is the one job this cycle can start that would not
notice the library halting under it"), and it is gated the opposite way from Hard Rule -1's own
stated discipline elsewhere in this project ("FAIL CLOSED ... An unreadable config ... a corrupt
halt file: all refuse. Silence must never authorise anything"). Concretely: if the same kind of
fault that breached the drill tonight instead made `drill.py` itself time out or crash (rather than
cleanly exiting 1), `drill_rc` would be `None`/some other code, and prose would start anyway,
unblocked, on the exact cycle the library's condition is least understood. Marking this a finding
rather than a pure question because the observed behavior contradicts Hard Rule -1's own wording,
even though the surrounding comment argues for it on purpose — worth an owner ruling either way.

### Finding B — a halt already standing at startup crashes overnight.py instead of waiting, unlike the identical case handled inside the cycle loop and unlike dashboard.py's precedent for the same call

`main()`'s startup interlock (~line 1483) calls `_ESC.assert_clear(os.path.basename(__file__))`
with **no try/except around the call itself** (only the `import escalation` above it is guarded,
against `ImportError`). `escalation.assert_clear` raises `escalation.SystemHalted(RuntimeError)`
when a halt is standing (confirmed in `src/escalation.py`: `class SystemHalted(RuntimeError)` at
line 80, raised at line 1131). An unhandled `SystemHalted` here propagates out of `main()` as an
uncaught exception — a crash with a Python traceback, not a logged message.

Contrast with two things in the same file/codebase:
- overnight.py's own **per-cycle** interlock (~line 1701-1706) wraps the identical call in
  try/except, logs "The library is halted. Nothing further will start until a person rules on it."
  and breaks the loop cleanly (`return 0`, "supervisor finished").
- `dashboard.py`'s `main()` (lines 1205-1211) explicitly imports `_ESC.SystemHalted`, catches it at
  the *same* call site (`_ESC.assert_clear(os.path.basename(__file__))`), and prints a clear
  message before continuing (it's read-only, so it may continue) — the established codebase pattern
  for handling this exact exception gracefully at startup.

Practical effect: `autostart.py --watch` restarts the supervisor whenever none is found running.
After a drill breach, the cycle loop's own graceful path (finding the halt on the next lap) logs
the halt and exits cleanly with `return 0` — which autostart reads as "no supervisor running" and
restarts. The restarted process then hits the **startup** interlock while the halt is still
standing (nobody has cleared it — by design, per Hard Rule -1, only a person may) and crashes
instead of entering the same "waiting for a person to clear it" loop the mid-cycle code provides.
This is a plausible mechanism behind tonight's "a halt that overnight cannot work its way out of":
rather than a legible, continuously-logged waiting state, the log would show terse crash
tracebacks (or, once `autostart.MAX_STARTS_PER_HOUR` is spent, nothing at all — the supervisor
just stays down until a person notices and clears the halt by hand). The halt itself correctly
requiring a person to clear it is not in question; the manner of failing while waiting for that
person is inconsistent with the file's own mid-loop behavior and with dashboard.py's demonstrated
handling of the identical call.

Both findings are in `src/overnight.py` only; nothing in `escalation.py`, `drill.py`, `generate.py`
or `autostart.py` was edited or needed editing to verify them (traced by reading their relevant
exact lines only where cited above: `escalation.SystemHalted`'s definition/raise site, and
`dashboard.py`'s contrasting startup handler).

## Everything else in the batch

Read in full; no new findings of the kinds in the brief's priority list (tautologies, other
fail-open guards, caps/truncations, off-by-ones/crashes, false comments, dead code) beyond what
the files' own extensive in-line history already documents as found-and-fixed or
found-and-deliberately-held (e.g. onomast.py's naming-collision fallback history, weave.py's
superseded idf-weighted functions kept per owner ruling, cleanup.py's ruby-regex idempotency
fixes, sweep.py's funnel-nesting fix, roll.py's compare-and-swap migration). None of these are
re-filed per the brief's instruction not to re-report handled items.

## Coverage

Recorded via `sweep_plan.record('run61', [...], batch=11)` for all eight modules listed above.
