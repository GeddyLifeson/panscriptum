# SWEEP 38 — AUDIT, BATCH 02

Agent: `sweep38-batch02`. Run: `run38`. Date: 2026-08-29.
Module list: `src/drill.py` (one module, 7,109 lines as read — the brief said ~6,775, so the file
grew again between dispatch and this read).

Audit pass only. Nothing under `src/` was edited. Every probe below ran from a scratch directory
against `C:/Users/imarl/miniconda3/python.exe`, read-only or in a temp tree; the one probe that
touched `local_agent` ran with `apply=False` throughout and restored every module global it
swapped.

---

## src/drill.py — READ IN FULL

### What it is, and what state it is in

271 nets over 34 areas (261 `net(` call sites; the `_fixtures()` loop expands to 8 and the
struck-off-provider loop to 4, which is 261 + 7 + 3 = 271 — matching the count in the brief).
All 34 `drill_*` area functions are present in `main()`'s dispatch tuple; none is defined and
left unrun.

The file is in good order. Every pure-AST net I could evaluate without side effects currently
returns True, and the liveness ratchet has headroom:

| probe | result |
|---|---|
| `liveness.scan()` total | 47 (dead 36, dead_class 1, dead_module 10, tautology 0, phantom 0, unparsed 0) |
| `LIVENESS_CEILING` | 52 — holds, five of headroom |
| `_guards_are_wired_where_claimed` | True |
| `_no_programmatic_clear` | True |
| `_counts_decided_by_substring` | `[]` |
| `_halt_is_not_breakage` | True |
| `_failed_revert_is_escalated` | True |
| `_run_marks_a_landless_run_failed` | True |
| `_withdrawal_takes_a_snapshot` | True |
| `_the_loop_asks_the_gate` | True |
| `_publish_never_swallows_a_missing_safety` | True |
| `_identity_probe_is_gated` | True |
| `_supersession_is_called` | True |
| `_refusal_is_recorded` | True |
| `_local_buckets_excluded_from_cloud_claims` | True |
| `_policy_corpus_clean` (whole corpus) | True |
| `_suppressed_still_visible` (new `only=` scope) | True |
| `_the_scanner_reads_files_over_two_megabytes` | True |

The three edits the brief flagged all check out: `LIVENESS_CEILING = 52` is above a measured 47;
`publish.scan_for_secrets`'s new `only=` scope works and `_suppressed_still_visible` depends on it
correctly (`P.COPY_DIRS + P.COPY_FILES` includes `src`, so `src/drill.py`'s suppression is in
range); and `drill_cache`'s live-collision net is genuinely reading the corpus — all four of its
`(host, name)` probes load a real, distinct document under `data/feats/`, so it is not vacuous.

### Findings

**1. MAJOR — `it cannot write a brand-new top-level file` cannot fail.**
Order `DRILL_UNLISTED_FILE_NET_VACUOUS`, handler RUN, `src/drill.py:1809-1823,1966-1968`.

`local_agent.t_propose_patch` answers `no such file` at `local_agent.py:696-698`, before the
denylist, before the `WRITABLE_PREFIXES`/`WRITABLE_FILES` allowlist at `local_agent.py:751-757`,
and before `DENYLIST_PREFIXES`. drill.py's `denied()` helper counts `"no such file" in err` as a
gate refusal. `something_nobody_listed.txt` does not exist, so the net holds on the existence
check and never reaches the allowlist.

Reproduced: with `WRITABLE_PREFIXES=('',)`, `WRITABLE_FILES=()`, `DENYLIST=set()`,
`DENYLIST_PATHS=set()` and `DENYLIST_PREFIXES=()` — every list this net exists to prove, deleted —
`denied('something_nobody_listed.txt')` is still `True`. The control in the same run,
`denied('data/COVERAGE.json')`, correctly goes `False`, so the two neighbouring allowlist nets do
have teeth; only the invented-name one is empty, and its expectation calls it "the test that
matters".

`denied()`'s own docstring is the other half of the finding: it says it exists to tell "refused BY
A GATE" from "failing for an unrelated reason", and `no such file` is exactly the unrelated
reason.

**2. MINOR — eleven of fourteen `file.py:NNN` citations have drifted.**
Order `DRILL_CITATION_DRIFT_RUN38`, handler LOCAL.

Each was checked by opening the target at the cited line; corrected numbers found by grepping the
quoted construct. Drifted: `local_agent.py:157-159` → 163/182-184; `withdraw_chapters.py:50` →
193-204; `cascade_bridge.py:282` → 317; `cascade_bridge.py:1118-1120` → 1265;
`feats.py:148` → 159; `cascade_bridge.py:1192` → 1552-1553; `pipeline.py:822` → 988;
`feats.py:918-923` → 1370-1375; `pipeline.py:2122` → 2621; `corpus_db.py:488-539` → 574-580;
`dashboard.py:529` → 607; `workorders.py:564` → 828. Still accurate and to be left alone:
`liveness.py:10` (cited twice) and `coverage.py:53`.

**3. MINOR — the breached-net list is capped at five in the halt sentence.**
Order `DRILL_BREACH_LIST_CAPPED_AT_FIVE`, handler RUN, `src/drill.py:7084,7090`.

`breached[:5]` with no "and N more", in the OWNER escalation's `what` — the sentence a person
reads in HALT.json to rule on restarting the library — and in the mutation-run print `mutate.py`
reads. Mitigated (the count is in the sentence, `evidence` and `state/drill_last.json` carry the
full list, the per-area report prints every row), hence MINOR rather than MAJOR. It is still a
`[:N]` on a read-to-act field inside the file that enforces Hard Rule 0 on everybody else.

**4. MINOR — the cited-set net asserts only a type.**
Order `DRILL_CITED_SET_NET_ASSERTS_ONLY_A_TYPE`, handler RUN, `src/drill.py:1082-1086`.

`isinstance(PG.cited_names_for(...), set)` is satisfied by `set()`, which is precisely the
condition its own expectation names as AUDIT DEFEAT 5 ("the old set was ALWAYS empty"). Empty is a
live outcome: `cited_names_for('DC', ['Superman'])` returns `set()` today. A verified
both-directions replacement is in the order (`{'Bruce Banner (Earth-616)'}` for a cited name,
`set()` for an invented one — both measured this run).

**5. MINOR — the segment-seam fixture is pinned to a literal, gated on the wrong constant.**
Order `DRILL_SEAM_OFFSET_IS_A_LITERAL`, handler RUN, `src/drill.py:2220-2221`.

`seam = P._SCAN_BLOCK and 2_000_000  # the default line cap`. `_SCAN_BLOCK` is 262,144 and is the
read-block size, not the line cap; the expression is the literal `2_000_000` for any truthy
value. It equals `scan_for_secrets`'s `max_bytes` default *today*, so the fixture does straddle a
seam — measured: cutting `_SCAN_OVERLAP` to 8 makes the net go False, so the property is
exercised. But with the segment size moved to 300,000 and the same 8-byte overlap the net returns
True: the credential lands mid-segment, the seam case silently stops being one, and the net
reports HELD over a scanner that can no longer see a secret across a boundary — at the last gate
before a public push. Remedy: pass an explicit `max_bytes` into the probe and place the
credential at `cap - 10`, which also makes this net (three multi-megabyte writes per run) cheap.

Side observation recorded in the order: `_SCAN_OVERLAP = 0` is not a way to simulate deleting the
overlap, because `seg[-0:]` is the *whole* segment — a publish.py property, noted only because it
is what makes the 8-byte form the honest regression to test against.

**6. MINOR — `_publish_never_swallows_a_missing_safety` is unscoped and breaches on an improvement.**
Order `DRILL_IMPORTERROR_NET_UNSCOPED`, handler RUN, `src/drill.py:2284-2298`.

Two things. The `raise` is found with a plain `ast.walk(n)`, so a dead `raise` below a `return`
inside the handler satisfies it — the last AST net in the file that is not reachability-scoped,
after orders c54a22a4e6fc and 78f04bec15ad removed exactly this from four others. And
`return arms >= 3`: publish.py has exactly three ImportError arms (measured: lines 1142, 1166,
1387, all raising), so hardening any one of them into an unconditional import — strictly stronger,
no handler left to swallow anything — drops the count to two, the net returns False, and a False
here halts the library at OWNER. That is drill.py's own line at 598-599 turned on itself.

**7. MINOR — the commentary says a deleted helper "remains".**
Order `DRILL_CALLED_NAMES_COMMENT_CONTRADICTS`, handler LOCAL, `src/drill.py:224-228,452,471-482`.

`src/drill.py:224-228` says `_called_names` "has gone the same way as `_calls`"; `src/drill.py:481-482`
says "`_called_names(path, reachable=True)` remains for the honest middle form". It is defined
nowhere (`hasattr(drill, '_called_names')` is False). The false half sits in the paragraph a
reader consults to choose between the three degrees of "is this guard wired", so it offers a
middle option that has to be re-invented to be used — which that same paragraph says removing
`_calls` was meant to prevent.

**8. INFO — two stated counts no longer match.**
Order `DRILL_STALE_COUNTS_IN_COMMENTS`, handler LOCAL, `src/drill.py:48-52,2374-2377`.

The LIVENESS_CEILING preamble states a present measurement of 35 dead / total 46; it is 36 / 47
today, so the headroom argued as "six" is five (still inside the comment's own four-to-nine band,
and the comment already documents this drift). And `_a_broken_maintenance_guard_fails_open`'s
docstring says "Six ways of not being a live shift" over a `cases` list of eight — the two it
omits, a JSON string rather than an object and a non-numeric heartbeat, are separate labelled
cases in the code.

**9. INFO — an unfailable tail expression.**
Order `DRILL_INDEX_STALENESS_TAIL_UNFAILABLE`, handler LOCAL, `src/drill.py:6690-6694`.

`return f["stale"] == (newer > 0) or newer == 0` returns True in all four reachable states given
the guard two lines above it. Not a fault — the real assertion is the guard, and the docstring is
honest that the overstating direction is deliberately not graded — but it reads as a check and
cannot fail, two lines from the only line doing work.

**10. INFO — publish.py names a drill net that does not exist.**
Order `PUBLISH_NAMES_A_DRILL_NET_THAT_DOES_NOT_EXIST`, handler LOCAL, `src/publish.py:441-448`.

`scan_for_secrets`'s docstring justifies the `only=` parameter — which its own text calls "a
loaded gun" — by citing "the drill's `_secret_scan_reads_every_staged_file` fixture". No such net
exists. The one it means is `_the_scanner_reads_files_over_two_megabytes` at `src/drill.py:2179`,
which does exactly what the sentence claims. Filed from this side because the claim is about a
drill net; it may duplicate the publish.py batch's own finding, which is the cheaper error.

### Question (not a finding)

**`there_is_no_paid_lane` still grades a comment.**
Order `DRILL_PAID_LANE_NET_READS_A_COMMENT`, handler OWNER, `src/drill.py:4167-4211`.

`return not named and "THERE IS NO PAID LANE" in text`. The structural half is sound and is the
whole point of order 64dfe6bec15c's rewrite. The text half is the question. Reading one: the
docstring says the documentation half is KEPT on purpose, because the owner's ruling is worth
pinning in the code it governs. Reading two: a False here escalates to OWNER and halts the
library, so reflowing or rewording one comment in `cascade_bridge.py` stops the park — the class
of defect orders 7cc460706efe and 8ee268ce32cc were filed for, and the only remaining net in this
file whose verdict depends on a comment's presence. Either answer is defensible and only the
owner's is binding.

### Things I checked and cleared

- **`denied()`'s other ten targets.** All exist on disk and come back with a real gate message
  (`denylist` for verify_math / Verify_Math / config.yaml, `writable surface` for the six
  out-of-surface paths). Only the invented-name one is empty. The `it CAN still be given ordinary
  work` control correctly returns a non-gate error.
- **`drill_cache`'s live colliding pairs.** Both pairs load two distinct real files under
  `data/feats/` with correct ownership; the net is measuring the corpus, as it claims.
- **`paid_access_stays_switched_off`.** The literal is `r"C:\\Users\\imarl\\cascade\\config.json"`
  — a raw string, so the doubled backslashes survive. Windows collapses the duplicated separators,
  the file opens, and `allow_paid` reads `False`, so the net is measuring something. Recorded here
  rather than filed: it is a latent oddity, not a live fault.
- **Every `[:N]` in the file.** Only `breached[:5]` (finding 3) is on a field a person reads;
  `seed[:3]` is fixture arithmetic and `long_line[:400_000]` is fixture construction. The three
  other `[:N]` mentions are inside docstrings describing caps in *other* modules.
- **`main()`'s area dispatch.** All 34 defined areas are listed; the per-area `try/except` that
  records "AREA DID NOT RUN" as a breach is correct and matches its comment.
- **Unused helpers.** Every module-level helper has a live caller. `_SRC_OVERRIDE` is never set,
  which its own docstring states and justifies.
- **`_no_programmatic_clear`'s exemptions.** Matched on the relative label, not the basename, so a
  `deprecated/escalation.py` could not exempt itself — the docstring's claim holds.

---

## COVERAGE

`sweep_plan.record('run38', ['drill.py'], batch=2)` — recorded.
