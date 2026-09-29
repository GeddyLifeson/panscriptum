# AUDIT batch 06 -- sweep67 (run67)

## Scope

Read-only. Every line of each module was read with the Read tool, in sequential chunks:

| module | lines |
|---|---|
| src/workorders.py | 2,581 (1-450, 450-949, 950-1449, 1450-1999, 2000-2581) |
| src/overwatch.py | 1,146 (1-400, 400-799, 800-1146) |
| src/thread_integrity.py | 825 (whole) |
| src/endpoint.py | 654 (whole) |
| src/catalogue_codex.py | 515 (whole) |
| src/retry_synthesis.py | 423 (whole) |
| src/roll.py | 347 (whole) |
| src/ledger.py | 232 (whole) |
| src/scale_theories.py | 215 (whole) |

Nothing under src/, data/, state/, output/, prompts/, reference/ or the repo root was edited. No daemon,
pipeline phase, generate/publish/mutate/verify_math/drill was run. Scratch probes live in %TEMP%
(`cc_probe.py`, `ep_probe.py`, `ti_probe.py`, `ow_probe.py`, `wo_probe.py`, `lg_probe.py`); the workorders probe
repointed `OPEN_FILE` at a temp dir first, the thread_integrity probe used `load_thread_graph(path=<temp>)`.
No subagents.

## Prior-audit cross-check (handoff/sweep66)

- **b06 finding 1 (LOCAL-denial door/detector disagreement, `DENYLIST_PATHS`)**: FIXED. `file_order`'s door and
  `sweep_detectors`' misrouted-local detector now share `local_door_targets` (workorders.py:933-957, 554,
  2113), which reads `DENYLIST_PATHS`/`DENYLIST_PREFIXES`. Does not stand.
- **b06 finding 2 (HOST_QUARANTINED / BINDING_SUSPECT filed at BOTS, no bot can close them)**: STILL STANDS.
  Now at workorders.py:1557-1558 and :1702-1710 (file grew 70 lines, lines drifted). `state/workorders.json`
  currently holds nine open HOST_QUARANTINED orders, all handler BOTS, MINOR. foreman/overnight/scout reference
  neither the code nor `binding_health.canary`. Unchanged owner-routing question, not re-filed.
- **b03 question 1 (`retry_synthesis` exit code follows last save only)**: RESOLVED in code. `still_failing`
  is collected and `return 0 if (landed and not still_failing) else 1` (retry_synthesis.py:381-419).
- **b03 ledger.py dead functions**: now carry the owner's "retained, no production caller" markers (order
  7099a092abd3, ledger.py:154-198); behaviour unchanged. Their standing is settled. See new finding 8 for a
  stale citation in the same header.
- **b05 scale_theories.py (held, unwired)**: unchanged, still true; `surviving_theory()`'s field-based
  selection and raised arity check re-verified.
- **b07 overwatch.py (zero findings)**: structure unchanged; my re-read found two things the prior pass did not
  name (findings 2 and 3).
- **b08 catalogue_codex.py (zero findings)**: mechanisms re-verified; two things not previously named
  (findings 5, 6).
- **b11 thread_integrity.py, order a724ec57e0d5 (question: should DANGLING escalate)**: RESOLVED by code:
  `_escalate_dangling` (thread_integrity.py:466-506), wired at :737. File grew 721 -> 825 lines.
  Order 21c075e5e2d6/`_assert_not_halted` also landed (:509-530, :770-784) and reads correctly
  (`assert_clear` returns True or raises `SystemHalted`, escalation.py:1283).
- **b14 roll.py**: `update_rows`' `seen` fix still in place; `exclude()` gained the halt interlock (roll.py:269-274).
  Orders 1e6f99e54b25/21c075e5e2d6/3099138a82bd: overwatch, retry_synthesis, roll, thread_integrity are all on
  `verify_math._INTERLOCKED` (verify_math.py:7755). catalogue_codex is not (finding 5).
- **b06 endpoint.py clearances** (`_save` CAS, `DEAD_TTL`, `fetch_raw_verdict` tally, `source_pages`/`register`
  absent-vs-unreadable): all re-verified, still hold.

`state/workorders.json` (10 open orders) was grepped for all nine module names and for HOST_QUARANTINED. The
only hits are the nine HOST_QUARANTINED orders above; none names any module in this batch.

## Findings

### 1. endpoint.py:470-472 -- `html_text` decodes 8 entities, leaves every other one, and double-decodes `&amp;` -- MEDIUM (VERIFIED)

`html_text` replaces `&nbsp; &amp; &lt; &gt; &quot; &#39; &mdash; &ndash;` in that order. Anything else survives
into the text the miners match against, and `&amp;` is replaced before `&lt;` so `&amp;lt;` becomes `<`.

Repro (`%TEMP%/ep_probe.py`):
```
in : <p>Dr. Firestorm&#8217;s Corps &amp; Caf&eacute; &ldquo;Mage&rdquo; &amp;lt;b&amp;gt; &hellip;</p>
out: 'Dr. Firestorm&#8217;s Corps & Caf&eacute; &ldquo;Mage&rdquo; <b> &hellip;'
html.unescape(tag-stripped) : 'Dr. Firestorm’s Corps & Café “Mage” &lt;b&gt; … '
```
`_get` already decodes the body as UTF-8, so only entity-encoded characters are affected, which is exactly
what WordPress-style homebrew pages emit (`&#8217;`, `&rsquo;`, `&hellip;`). Consumers: `feats._source_pages_text`
via `fetch_html` (feats.py:2095) and `scout.py:334`. Neither unescapes afterwards (grep for `unescape` outside
endpoint/drill/verify_math: none). Effect: an entity whose name has an apostrophe or accent on a `pages:<source>`
host does not match its own page text, and reads as uncited with nothing recording why. This is the
"error turned into a plausible negative" shape. I cannot size it without running the miner.
Fix: after `_TAG.sub`, `body = html.unescape(body)` (stdlib) and delete the replacement table. `_SCRIPT` already
removes script bodies before this, so unescaping late is correct.

### 2. overwatch.py:997, 1006, 1012 -- module digest is taken AFTER the model has read the file, so an edit mid-review is stamped as reviewed -- MEDIUM-LOW (SUSPECTED, by inspection)

`review()` reads `src` at :618 and slices at :572, then makes one model call per 7,000-char slice. The
:1030 comment records a single module read taking 2,033-11,548 s. Only afterwards does `round_once` compute
`d = _digest(...)` (:997) and write it into `led["seen"][m]` (:1006) and every new finding (:1012).
If the module is edited during those minutes-to-hours, the model read the old text but the ledger says the new
digest was read: `rotation()` (:768-778) sees `prev["digest"] == d` and never queues the edited module as
"changed", and findings anchored to old line ranges carry the new digest so `round_once`'s retire loop (:963)
will not retire them. This project edits `src/` constantly (the :1030 comment itself cites "three source edits old").
Not reproduced (needs a live model call and a concurrent edit); the ordering is unambiguous in the code.
Fix: take `d0 = _digest(path)` before `review()` and use it for both stamps; or have `review()` hash the exact
`src` string it sliced and return it.

### 3. overwatch.py:287, 593-597, 1009 -- a model answer with `"actual": null` or a non-string `symbol` crashes the round -- LOW-MEDIUM (VERIFIED)

`_fingerprint` does `f.get('actual','')[:80]`; `_anchored` does `(finding.get("symbol") or "").strip()`. The
cloud arm returns whatever the router hands back and `pipeline._pool_answer_usable` only checks top-level
required keys. Repro (`%TEMP%/ow_probe.py`):
```
usable: True                                   # {"findings":[{"symbol":"x_func","claim":"c","actual":None,...}]}
fingerprint raises TypeError 'NoneType' object is not subscriptable
usable2: True                                  # symbol: 5
anchored raises AttributeError
```
`_anchored` runs inside `review`, inside the `try` at :991, so the whole module review is discarded ("review
failed") and not stamped seen, which is safe. `_fingerprint` is called at :1009 OUTSIDE any try, after `seen` was
set in memory (:1006) and before `save(led)` (:1019): the round dies, that module's reads are lost, and the
standing `--loop` job restarts into the same module. Loud, not silent, but a single null field takes the
watcher down for the round.
Fix: coerce with `str(f.get('actual') or '')` in `_fingerprint`, and reject non-string `symbol`/`actual`
in `review()`'s filter loop (:627-631).

### 4. thread_integrity.py:186-199 -- malformed thread rows are skipped, not counted, so a corrupt graph can verify clean -- MEDIUM-LOW (VERIFIED)

`load_thread_graph`'s docstring: "an unreadable graph must never come back as an empty one, because an empty
graph verifies perfectly." But only row `code` shape is validated. Repro (`%TEMP%/ti_probe.py`, `path=` a temp graph):
```
T2 entries as strings : ('ok', 0, [], 0)          # a: T2={"x": ["II.A.2", "nowhere"]}
T1 as string          : ('ok', 0, [], 0)          # a: T1="II.A.2"
T2 as list            : AttributeError 'list' object has no attribute 'items'
T2 entry dict no 'to' : ('ok', 0, [('a','T2',None)], 1)   # correctly unresolvable
```
A thread that is a string, or a T1 that is not a dict, contributes no edge and no `unresolvable` row
(`isinstance(e, dict)` / `isinstance(t1, dict)` at :189, :193), so the DANGLING=0 release gate passes over it.
A T2 that is a list raises `AttributeError` rather than `ThreadGraphUnreadable`, so `main()` skips the OWNER
escalation at :599-606 and just tracebacks. The graph is machine-written by `threads.py`, so this needs a writer
bug to trigger; that is the situation a verifier is for.
Fix: in the two `isinstance` branches, append `(src, cls, <the raw value>)` to `unresolvable` instead of skipping,
and raise `ThreadGraphUnreadable` when `T2` is not a dict or a list value is not a list.

### 5. catalogue_codex.py (whole `main`) -- hand-run corpus writer with no halt interlock -- LOW (VERIFIED)

`main()` writes `data/records/*.json` (`write_record_catalogue`, :447) and lands `SWEEP_ROLL.json`
(`roll.update_rows`, :484) without `assert_clear`. The 2026-09-28 ruling (orders 1e6f99e54b25 / 21c075e5e2d6 /
3099138a82bd, "TWENTY HAND-RUN WRITERS JOINED") names `retry_synthesis`, `roll`, `thread_integrity`,
`overwatch`, `sevenfold`, `resync_roll` and others; `verify_math._INTERLOCKED` does not list `catalogue_codex.py`
(grep: its only verify_math mention is the ROLL-constant roster at :6475). `catalogue_web.py`, `catalogue_aurora.py`
and `recover_folder_records.py` are also absent from the roster (not in this batch, not read for this point).
Filed as a finding rather than a question because the owner already decided the class; this module was simply not
on the list. Fix: the `_assert_not_halted` used in retry_synthesis.py:310-334, called after `parse_args` and skipped
for `--dry-run`, plus a `_INTERLOCKED` row.

### 6. catalogue_codex.py:256-262, 461-462 (and roll.py:19-20) -- the owner's out-of-scope exclusion is not consulted, and the cataloguers overwrite `status` with "catalogued" -- LOW here (latent), MEDIUM as a cross-batch fact (VERIFIED)

`roll.py`'s header says an excluded source is "removed from WORK: nothing crawls it, nothing generates from it".
`catalogue_codex.main` selects `entry_count > 0 -> skip` only, never `roll.in_scope`/`OUT_OF_SCOPE`, and on a
write sets `"status": "catalogued"` (:461-462), which reverts exactly the exclusion the roll.py docstring calls
"the trap that nearly ate it". Probe (`%TEMP%/cc_probe.py`) against the live roll and codex:
```
Dr. Firestorm's Engineering Corps 425  exact
Savant 8                                exact
Yorviing's Arcane Grimoire 478          exact
Mage Hand Press 22                      ['Mage Hand Press Orders']
```
Four out-of-scope rows bind to codex sections. Today all four have `entry_count > 0`, so none is picked. If a
resync or withdrawal ever set one to 0, `catalogue_codex` would re-catalogue it and flip its status.
Same fact, live, one module over (not in this batch): `catalogue_web.py:649`
`todo = [r for r in roll if r.get("entry_count", 0) == 0]` has no scope filter (grep of `in_scope|out_of_scope|
out-of-scope` in catalogue_web.py and catalogue_aurora.py: no hits), and four out-of-scope rows have
`entry_count: 0` right now: HAWX, Heaven's Lost Property, major live-action Disney films, Twilight Imperium. The
default `catalogue_web.py` run will attempt them (probably resolving no wiki, since the exclusion reason is "no
verifiable wiki source", but it spends the lookups and would set `status: catalogued` on any that resolves).
`drill.py:23222` only pins `manifest_builder.main` as consulting `roll.out_of_scope`, so nothing watches the
cataloguers. Fix: in each cataloguer's work selection, `if not roll.in_scope(r["name"], roll_rows): continue`; and
correct roll.py:19-20 either way. Please route the catalogue_web half to whoever holds that module's batch.

### 7. retry_synthesis.py:356-366 -- names that select nothing exit 0 with "0 to do now" -- LOW (SUSPECTED, by inspection)

`want = failed | stranded`; `todo` is filtered by `r["source"] in want and not in side and no synthesis`; then
`--only` filters `todo` again by exact string. A mistyped or differently-cased `--only` name, a name already in
the side file, or a `failed_sources()` name that no longer has a record, all yield an empty `todo`, print
"0 to do now", skip the loop and return 0 (`landed=True`, `still_failing=[]`). The
`unmerged` accounting `do_merge` does for the merge direction (:294-301) has no counterpart on the run
direction. `roll.exclude()` raises on the same typo shape; this does not.
Fix: after building `todo`, name every requested `--only` and every `failed` name that matched no record, and
return 1 if any requested name was unmatched.

### 8. Stale in-file citations and counts -- LOW (VERIFIED)

- ledger.py:43 cites `verify_math.py:266-284` as the place the battery "drives `to_standards`, `from_standards`,
  `cross_rate`, `work_value` and `assay_to_standards`". Those lines are the Ollama-port tripwire setup. The
  drive is verify_math.py:1170-1188. `citecheck` only flags provably-impossible targets (EOF, blank, bare bracket),
  so this passes it. The sentence is the "measurement it is held against" in an owner-ruled HELD docstring;
  cite `verify_math.py` "section that imports `ledger as L`" or the symbol instead.
- overwatch.py:343 "The comment at :341 says `last_run` values are zero-padded ..." -- that text is at
  :391 (`_merge_ledgers` docstring); :341 is inside `_finished_at`'s docstring.
- thread_integrity.py:671 "per-pair detail was computed at :188 and then discarded" -- :188 is in
  `load_thread_graph`; the ASYMMETRIC-LAWFUL detail row is built at :441-442.
- workorders.py:12 "127 drill nets" -- CLAUDE.md records that the drill's count was 455+ `net(` call sites on
  2026-09-08 and calls counts in doctrine "stale weekly".

### 9. workorders.py:561-564 -- `file_order`'s LOCAL-door `except Exception: pass` records nothing -- LOW (VERIFIED by reading)

If importing `local_agent` or `local_door_targets` raises, the order is filed at LOCAL as addressed with no
`silence.note`, so nothing counts how often the door could not decide. The comment defends the fall-through
("the post-hoc detector still catches this") and it does, but the rest of this file's `except` sites all note.
Fix: `silence.note("workorders.py:file-order-door")` inside the handler.

## Questions (possible deliberate design)

1. **workorders.py:490-512 + escalation.py:367-370.** `_refuse_cap_hit` raises `BadOrder` when `what` is exactly
   600 characters (or `where` 200, `found_by` 80). `sweep_detectors` turns that into a loud DETECTOR_FAILED
   (section `except`), but `escalation.escalate` wraps `WO.file_order` in `except Exception: silence.note(
   "escalation.py:workorder")`. Repro (`%TEMP%/wo_probe.py`, temp queue): `what` of 599 and 601 file, 600 raises
   `BadOrder`. So a real escalation whose composed text lands on exactly 600 characters (THREAD_DANGLING,
   built from an uncapped pair list, is a candidate) is logged and halts as designed but gets no work order,
   with only a ledger count. The text says "do NOT pad", so this may be intended; is a note-only outcome on the
   escalation path what the owner wants, given the door was hardened precisely so a coincidence is not filed?
2. **endpoint.py:222-239 (`detect(force=True)`).** The cache's asymmetry is "live is forever, dead expires".
   A `--force` probe during a network outage overwrites a formerly-live API/RAW verdict with MODE_DEAD (`mem[host]
   = found`, :269), which then holds for 24 h and is merged onto disk by `_save`. The comment at :213-218 argues
   against exactly this for non-forced probes. Is force meant to be able to demote a live host?
3. **endpoint.py:494-502 (`fetch_html` drops any page whose text is <= 400 chars).** It is noted in the ledger,
   but a short real page (a one-paragraph stat block on a one-author site) is discarded the same as an interstitial.
   Is 400 a deliberate floor for registered pages, given Hard Rule 0's stance on silent cutoffs?
4. **overwatch.py:761-778, 987 (rotation).** `changed` is in `A.modules()` order, unranked; only `[:limit]` (6)
   are read per round. Modules leave the list only on a complete read. A huge module that keeps yielding on a busy
   GPU stays near the front. Is alphabetical-first acceptable for the changed set, or should it be ranked
   (mtime, size)? Not a truncation (every module cycles through), so filed as a question.

## Cleared (examined closely, found correct)

- **workorders.py**: `_load`'s absent/unreadable/non-object three-way and `_mutate`'s digest-before-read CAS with
  pid+thread+attempt temp names; `resolve()`'s landed-then-existed ordering and append-after-delete with the
  loud failed-append handler; `reroute()`'s three dispositions and `_refuse_cap_hit` on both writers of `found_by`;
  `file_order`'s re-route-survives-refresh rule and its `_rerouted`-only refusal; `_fire`'s healthy-resolves polarity
  at every call site; section 4's `scanned` gate (an unrun scan neither files nor closes SECRET_STAGED); section 3b's
  absent-vs-torn `BINDING_HEALTH.json`; `battery_faults`' fail-closed rows (absent, unreadable, no `estate_faults`,
  ungraded rc); `ghost_orders`' time-based test; `twins`' interval overlap; `cap_boundary_scan`; `_closed_rows`;
  `check_closed`'s refusal of an absent directory; drill-close reading `drill_last.json` (the drill writes it
  before escalating, drill.py:26687 then :26844, so a fresh breach is never closed against a stale clean file);
  STRANDED_SYNTHESIS/AGENT_SCRATCH labelled samples with complete `evidence`; `--handler` refusing an unknown rung.
- **overwatch.py**: `load()`'s preserve-the-wreck path and `_UNPRESERVED` refusal; `save()`/`_reconcile_with_disk`/
  `_merge_ledgers`' monotone per-key union; `_finished_at`'s single time scale; `verify_open`'s stamp-only-on-answer
  and `yielded` accounting; `_LOCAL_BUSY` reset per round (:904); the retire loop's absent-file-only rule; WATCH.md
  uncapped lists; the halt re-asked every round with fail-closed re-import.
- **thread_integrity.py**: `_charter_codes` absent/corrupt/wrong-shape split; `_floor_verdict`'s eight states and
  `write=False` under halt; `classify`'s both-directions test and mirror dedupe (`fwd`/`back`); DANGLING as the sole
  graded class with `_escalate_dangling` per source; every listing uncapped, `_namecol` sized from the rows.
- **endpoint.py**: `_save` merge-not-overwrite with `_DIRTY`; the `save-reread` heal is safe because a locked file
  makes `digest_of` disagree with `replace_if_unchanged`'s swap-time digest (refused and retried, not wiped);
  `fetch_raw_verdict` tally; `source_pages`/`register` absent-vs-unreadable; the `__main__` guard at the end.
- **catalogue_codex.py**: manifest count cross-check; `(type, name)` dedupe key; ambiguous-substring binds nothing;
  register-collision descriptions attested only when members agree; all report lists uncapped; denied write and
  denied roll both reach rc; `load_register_index` keeps every colliding member.
- **retry_synthesis.py**: `synthesise` shares `synthesis_blocks`/`synthesis_prompt`/`clean_band`/`valid_scale_note`/
  `_stored_cut` with pipeline (signatures re-checked against pipeline.py:1753, 1838, 221, 2326, 240);
  `save_side` merge-then-write and its landed verdict; `do_merge` through `write_record`, with `unmerged` named;
  `--smallest` is a pilot order, documented as such.
- **roll.py**: `mutate`'s CAS and unreadable/non-list refusals; `update_rows`' `seen`-on-found; `exclude`'s required
  note, raise on typo, caller-supplied `rows` staying in memory; `in_scope` failing open with the reason on record.
- **ledger.py**: arithmetic exercised by hand (`work_value`, `cross_rate` gil->zenny 0.7917, poneglyph -> None);
  `assay_to_standards` M10 branch continuous with M9 at ruin 10 (4.67e90); `JOULES_PER_STANDARD` = 2.14e8 imported.
- **scale_theories.py**: T2's 6.3e18 J / ~1,500 Mt arithmetic; `bulk_export_beta` floor branch; `surviving_theory`
  raises on any arity other than one survivor; held-module status matches order 01695fe3ef26.

## Coverage

Recorded with `sweep_plan.record('run67', ['workorders.py', 'overwatch.py', 'thread_integrity.py', 'endpoint.py',
'catalogue_codex.py', 'retry_synthesis.py', 'roll.py', 'ledger.py', 'scale_theories.py'], batch=6)`.
