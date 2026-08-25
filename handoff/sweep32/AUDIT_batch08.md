# AUDIT — BATCH 08 — run32

Modules read in full, every line:
- `src/drill.py` — 1033 lines
- `src/weave.py` — 487 lines
- `src/reference.py` — 358 lines
- `src/cosmography.py` — 282 lines
- `src/ledger_guard.py` — 244 lines
- `src/thread_integrity.py` — 184 lines
- `src/catalogue_aurora.py` — 171 lines

`drill.py` was not run (supervisor's job; a breach halts the library). All findings below are from static reading, cross-checked where possible by grepping the referenced target files (`prose_gate.py`, `cascade_bridge.py`) for the tokens the nets look for.

---

## BLOCKING

### `ledger_guard.py:224` — `assert_intact()` discards `seal()`'s return; a failed chain-append still reports "ledgers intact" to publish
**VERIFIED.** `assert_intact()` (207-225):
```
ok, problems = verify_chain()
if not ok:
    raise LedgerViolation(...)
seal()          # line 224 — return value discarded
return True     # line 225 — unconditional
```
`seal()` (120-157) itself ends in a bare `except Exception: return None` (155-156) with no `silence.note` call — any write failure (permission error, disk full, a kill mid-write) is swallowed silently and `seal()` returns `None` instead of the new link. `assert_intact()` never inspects that return value, so a run where the chain-append genuinely failed still returns `True` to its only caller, `publish.py:456` (`_LG.assert_intact()` immediately before push). The next run's `verify_chain()` would silently be missing a link (or `read_chain()` shows a gap), but by then the ledgers have already been published as "intact." Concrete scenario: disk fills or the process is SIGTERM'd (the foreman routinely does this, per `escalation.py`'s own incident history) during the `open(CHAIN, "a")` write in `seal()` — `assert_intact()` still returns `True`, `publish.py` proceeds to push.

### `drill.py:117-120` (`drill_queue`) — "COVERAGE.json unreadable" net never makes the file unreadable
**CONFIRMED**, matches the reported finding exactly.
```
net(a, "COVERAGE.json unreadable is a refusal, not a pass",
    lambda: PG.cited_fraction("anything", None) is None
    or PG.evidence_ok("nope", 0.35, [])[0] is False,
    "unknown must mean stop")
```
Checked `prose_gate.py:148-160` (`cited_fraction`) and `163-194` (`evidence_ok`): both disjuncts route through the ordinary "source not found in rows" path (`cited_fraction` returns `None` at line 160 because the for-loop over `rows` never matches `source`), not through the `except Exception: return None` branch at line 152-153 that actually models an unreadable/corrupt file. `evidence_ok("nope", 0.35, [])` passes an empty list, same "not found" path. This is functionally identical to the already-tested "an unmeasured source is refused" net two lines above it (105-107) — it is a duplicate net wearing a different label, and the real unreadability path (152-153) has zero coverage anywhere in `drill_queue`.

---

## MAJOR

### `drill.py` — six more nets whose "attack" is a source-text substring/token check, not an AST assertion or an execution of the guarded code (Lens item 7, the batch's core ask)
Each is evadable by an honest reflow, a rename, or by the exact literal existing only in a comment/docstring rather than in enforcing code — the shape the task specifically flagged at 853-864/676-680 (current line numbers have drifted slightly from the report; the matching nets in the present source are listed below with their real locations).

1. **`drill.py:539-545`** `_halt_is_not_breakage` — `"_ESC.status()" in src[i:j]` where `src` is `overnight.py`'s raw text between two other substring markers. Never calls `overnight.py`; a comment containing `_ESC.status()` between those two markers satisfies it, and a working call spelled `ESC.status()` (no underscore alias) or reformatted across lines fails it.
2. **`drill.py:626-635`** `_no_programmatic_clear` — scans every `src/*.py` for the literal substrings `"escalation.clear("` / `"ESC.clear("` and passes if **absent**. Evadable by `import escalation as X; X.clear(...)`, `getattr(escalation, "clear")()`, or splitting the call across a line break — none of which contain the literal substring, so a programmatic halt-clear could be added and this net would keep reporting HELD.
3. **`drill.py:756-760`** (`drill_snapshot`) "the withdrawal script takes one before moving anything" — `"snapshot" in open(...withdraw_chapters.py...).read()`. Pure substring presence; satisfied by a comment mentioning "snapshot" with no call to `SNAP.before(...)` at all, and does not check that the snapshot happens *before* the move (only that the word appears anywhere in the file).
4. **`drill.py:846-848`** (`drill_cascade`) "burial is documented as permanent-codes-only" — `all(c in src for c in ("401","402","404","410")) and "429" in src` against `cascade_bridge.py`'s raw text. Confirmed by grep: `"429"` appears throughout comments/docstrings in that file regardless of what `dead_forever()` actually does (line 338 currently correctly excludes it) — so if a future edit added `"429"` into the `dead_forever()` tuple itself (the exact regression the surrounding docstring warns against), this net would **still read HELD**, because `"429"` was already present in the file's prose. It provides no protection against its own stated failure mode.
5. **`drill.py:850`** "there is no paid lane to spend" — `"THERE IS NO PAID LANE" in src`. Grep-confirmed: this string exists **only inside a comment** at `cascade_bridge.py:180`. The net verifies a comment exists, not that any code enforces the absence of a paid lane.
6. **`drill.py:853`** "the local prefix is excluded from cloud claims" — `"LOCAL_PREFIX" in src and "cand.bucket.startswith(LOCAL_PREFIX)" in src`. Grep-confirmed the second literal currently matches real code at `cascade_bridge.py:839`, but the check is against the exact source string: renaming `cand`, wrapping the line, or moving the exclusion to the (equally valid) enclosing-function version at line 673 all correctly preserve the invariant while flipping this net to BREACHED — a false alarm — while a comment containing the literal string would pass it with zero enforcing code. This is precisely the reported shape (matches the task's 853-864 citation).
7. **`drill.py:933-943`** `guards_are_wired_where_claimed` — for six files (`generate.py`, `overnight.py`, `coverage.py`, `feats.py`, `pipeline.py`, `hostcheck.py`) checks that a literal token (`"assert_gate_open"`, `"_prose_enabled()"`, `"cachekey"`) appears anywhere in the file's text. An unused/dead import, a stale comment, or a string inside an unrelated error message satisfies this; it never confirms the token is actually *called* in the enforcing path. This is the file-level generalization of the same defect — direct evidence for the drill's own `liveness.py` ratchet.

### `drill.py:993-1007` — the drill's own results file bypasses the two-writer contract, and the write failure is silently swallowed
```
out = os.path.join(HERE, "state", "drill_last.json")
try:
    ...
    with open(out, "w", encoding="utf-8") as f:
        json.dump({...}, f, indent=1, ensure_ascii=False)
except Exception:
    pass
```
This is a hand-rolled truncating `open(w)` write to a file under `state/`, not `silence.write_json`/`replace_retry` — the exact recurring defect the lens calls out, and it sits in the module that is itself the proving instrument for every other safety net. `dashboard.py:518` reads `state/drill_last.json` to report drill freshness to the operator (`dashboard.py:472`). A crash or SIGTERM mid-write (the foreman's own routine kill behaviour, documented elsewhere in this codebase) leaves a truncated/corrupt file; the surrounding `except Exception: pass` means the failure is never surfaced anywhere, and the dashboard would either error or silently show a stale/missing drill status — masking a recent BREACHED result from the operator. `drill.py`'s exit code / `ESC.escalate` call for a real breach still fires correctly regardless (this bug doesn't defeat that), but the persisted status record other tooling relies on can silently go stale.

### `thread_integrity.py:104-134` `classify()` — DANGLING only fires when *every* shared key in a pair has drifted; partial drift is silently absorbed as valid evidence
```
gone = [k for k in shared if k not in ents.get(a, ()) or k not in ents.get(b, ())]
if gone and len(gone) == len(shared):
    out["DANGLING"] += 1
    ...
    continue
```
If even one of N shared keys is still present on both sides, the pair is **not** flagged DANGLING at all, and falls through to `IMPLIED-UNRECORDED`/`RECIPROCAL`/etc. using the full, un-pruned `shared` set — so entity keys that a source has actually lost (weave drift) still count toward the reported evidence strength (`len(shared)`) for that pair as long as at least one other shared key survives. The docstring claims "DANGLING is computed for real, against the live records: a candidate key whose source no longer holds that entity" — that description is per-*key*; the implementation is per-*pair* and only catches total collapse, undercounting drift in the (presumably much more common) partial case. Comment-vs-code contradiction plus a real detection gap.

### `catalogue_aurora.py:140,150-153,161-165` — a WRITE DENIED record is still reported as written
```
written.append((r, record))                       # line 140 — appended unconditionally
if not args.dry_run:
    import pipeline as _P
    if not _P.write_record_catalogue(...):
        print(f"      -> WRITE DENIED {source_name}; roll left untouched", flush=True)
        continue                                    # line 153 — outer loop continues; `written` entry is NOT removed
    r["entry_count"] = len(entries)
    r["status"] = "catalogued"
...
print(f"{verb} {len(written)} records from Aurora XML:\n")
for r, rec in sorted(written, key=lambda x: -len(x[1]["entries"])):
    ...
    print(f"  {len(rec['entries']):5d} entries ({withtext} with description)  {r['name']}")
```
`written` gains the tuple **before** the write is attempted (line 140), and the denial branch (`continue` at 153) never removes it. The final summary counts and prints the denied source exactly like a successful one (only `r["entry_count"]`/`r["status"]` on the roll itself are correctly left untouched — that part of the fix from the run #25 finding this file's own comment documents is intact). Net effect: the operator-facing report can claim "Wrote 3 records" and list a source's entry count when only 2 actually landed on disk — a swallowed failure reported as an absence-of-problem, the same shape `drill.py`'s own "Inspector" section exists to catch.

---

## MINOR

- **`ledger_guard.py:228-240`** `main()` (the standalone `python src/ledger_guard.py` CLI) only calls `check_all()`; it never calls `verify_chain()` or `seal()`. Running the checker directly therefore cannot detect a broken hash chain — only `assert_intact()` (invoked solely from `publish.py`) does. Likely intentional (chain-checking is a publish-time gate) but worth confirming with the owner, since a human running the ledger checker mid-session would get a false "all intact" if only the chain were compromised.
- **`drill.py:594-595`** `denied()` (in `drill_local_agent`) disambiguates "refused" from "failed for an unrelated reason" via substring match on the error string (`"denylist" in err or "protected region" in err or ...`). This is execution-based (it does call `LA.t_propose_patch` for real) so it is not in the same class as the MAJOR findings above, but it is still fragile to a wording change in `local_agent.py`'s error messages silently turning a real refusal into an apparent unrelated failure (and thus a false breach) or vice versa.
- **`weave.py:74-76`** self-check for eaten regex escapes reads the whole module source at import time — fine, but note it means every import of `weave.py` pays a full-file disk read; not a bug, just a cost worth knowing about.
- **`weave.py`** — `pair_weights()` (156-173) and `null_threshold()` (249-273), the idf-weighted (non-surprisal) pair/threshold functions, and the `idf` value returned by `idf_table()`, are computed but never called/used by `main()` (which uses `surprisal_pair_weights`/`null_threshold_surprisal` throughout). Apparent dead code left behind by the surprisal-scoring rewrite; candidate for `liveness.py`'s dead-function ledger.
- **`weave.py:196-198`** `filtered_index()` only inspects `desc[:400]` (`_STATBLOCK`) and `desc[:300]` (`_RULES_VOICE`) of each entity's description when deciding whether it is "mechanics" text to drop. A rules/stat-block signature occurring after those character offsets would not be detected, letting a mechanics entry slip into the entity index and potentially seed a spurious cross-source fusion — the opposite of what this module exists to prevent. Not a roster/page truncation (Hard Rule 0 is about listing caps, not search-window caps), so I'm not calling it BLOCKING, but it is a real detection gap worth the owner's attention.
- **`thread_integrity.py:58-63`** `load_entities()` catches `json.load` failures per file but then indexes `rec["source"]` (direct subscript, not `.get`) outside that try block — a well-formed-JSON-but-missing-`source`-key record would raise an uncaught `KeyError` and crash the whole pass rather than being skipped and logged like the JSON-parse-failure case just above it.

## NOTE

- `drill.py:1014` truncates the halt-escalation message to the first 5 breached net names (`breached[:5]`) but the accompanying `evidence` dict at line 1015 carries the full, untruncated list — pure display truncation with the real data preserved, consistent with the Hard Rule 0 exception for display formatting. Not a bug.
- `weave.py`'s `main()` print loops (`multi[:12]` at 446, `sorted(...)[:8]` at 458, `most_common(6)` at 464) are console-summary truncations only; the underlying `groups`/`resolved`/`w` written to disk via `silence.write_json` are whole. Not a bug.
- `cosmography.py` — read in full; no caps, no swallowed exceptions, math checks out internally (`validate()` correctly refuses physically-impossible censuses, `KARDASHEV_MIX` sums to 1.0 exactly). Clean.
- `reference.py` — read in full; data-plus-reporting module, uses `silence.write_json` correctly for its one write, uses `silence.note` on its one caught exception. Clean.
- `catalogue_aurora.py:150` correctly gates the roll-row update on `write_record_catalogue`'s return value (this is the run #25 fix the file's own comment documents, and it is intact) — only the *summary print* has the residual bug described under MAJOR above.

---

## Summary count
- BLOCKING: 2
- MAJOR: 5 (six drill.py "checks that cannot fail" counted as one MAJOR item with six locations, plus the drill.py state-write bug, plus the thread_integrity.py DANGLING gap, plus the catalogue_aurora.py false-success report)
- MINOR: 5
- NOTE: 4
