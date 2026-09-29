# sweep67 batch 15 audit (run67)

Read-only throughout. Nothing under src/, data/, state/, output/, prompts/, reference/ or the repo root was edited. No subagent spawned. No daemon, pipeline phase, generate/publish/mutate/verify_math/drill run. `escalation.escalate/--clear/--pause` and every writer of the live ledger were never called; escalation was only imported with `HALT_FILE` redirected to a temp dir for one `status()` probe. Scratch scripts live under %TEMP%\s67b15 (t1..t6.py). Network calls in repros were monkeypatched out, and `completeness._cs_put` was stubbed so `state/category_sizes.json` was never touched.

## Scope (every line read, sequential chunks, matches `wc -l`)

| module | lines |
|---|---:|
| src/tells.py | 319 |
| src/anchors.py | 576 |
| src/grounding.py | 361 |
| src/sevenfold.py | 471 |
| src/identity.py | 763 (1-400, 400-763) |
| src/completeness.py | 920 (1-330, 330-629, 629-920) |
| src/escalation.py | 1624 (1-330, 330-669, 669-998, 998-1325, 1325-1624) |
| src/hostcheck.py | 1754 (1-300, 300-599, 599-898, 898-1197, 1197-1476, 1476-1754) |

CLAUDE.md Hard Rule -1 and Hard Rule 0 read first.

## Prior-audit cross-check (sweep66 batches 04, 06, 08, 12, 14, 15; sweep65 refs)

- b14 DEFECT 2 (hostcheck `score()` misreports cause when `_tokens(source)` is empty, e.g. `DC`): FIXED. `score()` now branches on `not _tokens(source)` (hostcheck.py:980-986) and says "a name problem, not a fetch failure". Closed.
- b12 Question 1 (tells `_anchor()` `pat[4:]` slice assumes the `^\s*` prefix): CLOSED by code. tells.py:184-188 now stops the import on any DISCOURSE pattern line-anchored any other way (order beb7db270826). Re-checked against every current DISCOURSE entry: all start `^\s*`.
- b08 Question 1 (sevenfold writes with no halt interlock, orders 1e6f99e54b25/21c075e5e2d6): CLOSED by code. `_assert_not_halted` at sevenfold.py:327-351, called on the `--write` path only (line 360), fail-closed on the import.
- b04 completeness shared-non-fandom-host question (f5b8e4afb558): now a ruled constant `SHARED_NON_FANDOM_HAS_NO_PRIMARY` (completeness.py:61, 715-725). Still behaves as the ruling says; nothing to re-file.
- b15 escalation dead store (`landed = False` after the `clear()` retry loop): STILL STANDS, now at escalation.py:1427. Harmless (reassigned by `_land_clear` at the top of every iteration; not read after the loop). Not filed.
- b15 grounding, b14 anchors, b06 identity: no earlier finding or question outstanding. identity.py grew 752 to 763 lines (new `_inv_counts` present-and-empty semantics, order 6b59a5d4302a item 6): re-traced, correct (a host recorded with `{}` answers "none" and no longer falls to another host's spelling).
- No earlier finding on any of the eight modules still stands except the dead store above.

## Findings

### F1. MEDIUM (reproduced) - hostcheck.py:444-473 `probe()` reads an API error body as `rate: 0.0`, i.e. "WRONG FICTION"; `null_rate` then caches a 0.0 baseline

Only a raised transport error returns `rate: None`. A 200 response whose JSON has no `query` (MediaWiki `{"error": {"code": "ratelimited"}}`, a `warnings`-only body, `{"batchcomplete": ""}`) falls through `query = d.get("query") or {}` to `pages = {}`, `live = []`, `hits = 0`, `rate = 0.0` with no `error` field. This is exactly the defect the module's own comments (lines 436-443, 835-848) say was fixed for thrown errors (warhammer40k unassigned from Warhammer 40,000), reached through the door beside it.

Evidence (`%TEMP%\s67b15\t5.py`, `EP.detect`/`_get` patched):
`{"error": {...ratelimited...}} -> rate 0.0, hits 0, probed 20, error None`; `{"warnings": {}}` and `{"batchcomplete": ""}` identical. With a 0.02 control, `score()` returns verdict `WRONG FICTION`.

Consequences: (a) in `sweep(--repair)` a WRONG FICTION verdict is in `JUDGED`; if the candidate probes are throttled too (same body), `judged_any` is True (WRONG FICTION is not "UNREACHABLE"), so the source lands in the `else` at line 1128 and `fixed[src] = None` unassigns the host and files it in HOST_UNFIT.json. (b) `null_rate` (line 833-855) calls `probe`; a throttled control body gives `rate = 0.0`, which is cached in `_NULL_CACHE` for the rest of the run as the host's baseline (the flattering-baseline direction the comment at 843 calls worse). Hand-run only (`--repair`), not scheduled, but the write is to the non-reconstructible WIKI_HOSTS.json.

Fix: after `d = _get(...)`, `if not isinstance(d, dict) or "query" not in d: return {..., "rate": None, "error": "no query in API reply: %r" % list(d)[:5]}`. `_bodies` and `relevance` already degrade to `(None, 0)` safely.

### F2. MEDIUM (live exposure, irreversible, human-gated) - hostcheck.py:1436-1453 `purge --go` deletes the WHOLE host cache directory even when other sources share the host

For each purged source the code removes every `*.json` under `data/feats/<mined host>/` and `data/readfeats/<mined host>/`. Those directories hold evidence for every source mined from that host, not only the purged one. On live data: `data/ROSTER_AUDIT.json` has 3 rows below the 0.10 bar; two of them (`Explorer's Guide to Wildemount`, `Player's Handbook`) are mined from `forgottenrealms.fandom.com`, which `WIKI_HOSTS.json` assigns to 30 sources (27 of 43 audit rows sit on a shared host). `purge --source "Player's Handbook" --go` would clear the entries for that one record but remove the cached pages backing the other 29 sources' entries. The docstring says the caches are "the only supporting evidence" and that "the caches those entries wrote" go, but nothing restricts the delete to those entries' files.

Fix: refuse (or dry-run-warn) when `sum(1 for h in hosts.values() if h == mined) > 1` or when any other source's `mined_host` equals `mined`; or delete only the cache files whose key matches this source's entity names (`cachekey` already resolves per-entity paths).

### F3. LOW-MEDIUM (reproduced) - completeness.py:199-206 and 275-281 an API error body is filed as "no such category" and cached 12h

`category_size_probe` and `category_size_probe_host` treat any reply without a `categoryinfo` page as `got = None` and return `(None, None)`, meaning "answered, category missing". A reply with no `query` at all (`{"error": {"code": "ratelimited"}}`) takes the same path, and `_cs_put(k, None)` caches it for `_CS_TTL` (12h). `work()` then counts it as an answered miss, not a failure (`failed` stays 0). Two effects: an all-throttled source reports "every category probe was answered and none exists" (still an `unreliable` row, so no false number), and a mixed source computes `best = max(sizes)` over the categories that did answer, so if the throttled one was the big category `best` is an undercount and coverage reads flatteringly high with `probe_failures: 0`.

Evidence (`t4.py`, `ws._api` patched to return the error dict): `(None, None)` and `_cs_put('marvel|Characters', None)`; identical to the genuine `missing` reply.

Fix: `if "query" not in d: return None, "NoQueryInReply"` before the loop (both functions), so it counts as `failed` and is not cached.

### F4. LOW (reproduced) - escalation.py:675, 580, 1450 `cleared` is tested for truthiness, so a wrong-typed value lifts the halt

`status()` returns `not rec.get("cleared", False)`. `_read_halt_raw` guarantees a dict but not the type of `cleared`. A HALT.json carrying `"cleared": "false"` (or `"no"`, `"0"`, a non-empty list or dict) reads as CLEARED, so `assert_clear()` passes and the library runs. Same test in `_land_halt` (a standing halt with a string `cleared` is treated as absent and replaced, losing the first fault) and `_halt_file_cleared`. The module's premise is that "a halt that a corrupted file can lift is not a halt" and it already hardened the null/list/non-dict shapes.

Evidence (`t1.py`, HALT_FILE redirected to a temp dir): `'false'`, `'no'`, `'0'`, `True`, `{'x':1}` all give `status()[0] == False`; `0`, `None`, `False`, `[]`, `''` give True. Not exploitable by this module's own writers (they write real bools); needs a hand edit or a foreign writer.

Fix: `cleared = rec.get("cleared") is True`, and treat any other truthy non-True value in `_read_halt_raw` as the unreadable stand-in.

### F5. LOW - hostcheck.py:1248 `sweep(only=...)` overwrites HOST_FITNESS.json with the filtered slice

`_land(OUT, results)` is unconditional, and `results` holds only sources matching `--only`. `completeness.land()` refuses exactly this ("--only is a spot check") and hostcheck has no equivalent. Nothing in src/ reads HOST_FITNESS.json (only a human), so the harm is a whole-corpus report replaced by a spot check with nothing saying so. Fix: skip the write (or write to a sibling file) when `only` is set.

### F6. LOW (reproduced) - tells.py:95, 128 two patterns lack a leading `\b`

`stands? as a (?:testament|monument|reminder)` and `stands? the test of time` match inside "understands". `scan("He understands as a reminder of the war.")` reports `stands as a testament`; `scan("She understands the test of time.")` reports `stands the test of time`. Both are in STRUCTURAL and are handed to the model verbatim as banned shapes. Fix: prefix `\b`.

### F7. LOW (reproduced) - tells.py:46-68 overlapping lexical entries double-count, and inflected forms are inconsistent

`scan("A tapestry of myriad of things.")` returns four hits for two phrases (`tapestry` plus `tapestry of`, `myriad` plus `myriad of`); `shrouded in mystery` also fires `shrouded in`. The audit reports RATES (module docstring), so each such phrase counts twice. Separately `\bunlock\b`, `\bleverage\b`, `\bfoster\b`, `\bembark\b`, `\bcultivate\b`, `\bharness\b` do not match "unlocks/unlocked/fostering/leveraged", while other entries list `-s`/`-ing` forms by hand (`delve`/`delving`, `boasts`/`boasting`). `scan("It unlocks doors. She unlocked it. fostering peace")` reports only `foster` for the "foster growth" clause. The prompt tells the model "do not use close variants", so the checker is narrower than the instruction. Fix: drop the shorter or longer duplicate of each pair, and give the inflected list a regex stem form (`unlock(?:s|ed|ing)?`).

### F8. LOW (diagnostic wording) - hostcheck.py:1655-1691 `adopt()` reports unreachable candidates as "genuinely without a wiki"

`one()` only records `ok` verdicts, so a source whose every candidate was `UNREACHABLE` (network down, throttled) prints `none` and is counted in `len(hostless) - len(found)` under "genuinely without a wiki". Nothing is written for them (only `found` lands), and the foreman only reads the "N adopted" line, so no state is affected. `sweep()` already distinguishes the two ("did not answer and were left exactly as they are"). Fix: track `judged_any` as `sweep` does and print "no candidate answered" for the unmeasured case.

### F9. LOW - completeness.py:788-793 `land()` reads an existing-but-unreadable prior file as "no prior file", disarming the shrink floor

The `except Exception` after `json.load(OUT)` is annotated "no prior file is a legitimate first state", but it also swallows a torn/corrupt COMPLETENESS.json and a PermissionError (a Windows reader holding the file). In those cases `prior = []`, the `len(rows) < len(prior) * SHRINK_FLOOR` guard cannot fire, and a 3-row run lands over the real file. `identity.load()` handles the same shape explicitly (tags it, prints that the guard cannot be applied). Fix: catch `FileNotFoundError` as the silent case; on any other exception `silence.note` and refuse the write (or at least print that the floor was not applied).

### F10. COSMETIC - anchors.py:510 stale relative reference

"The comment ninety lines above" refers to the ruling comment at lines 263-289, which is about 245 lines above line 510. Cite by symbol (`the DECLARED LADDER comment at the `order` list`), which this repo's own convention (identity.py:606) prefers over line distances.

## Questions (possible deliberate design, not filed as findings)

1. hostcheck.py:298, 359, 410-411, 520, 568: host fitness is judged from a 40-name head sample (`PROBE`), a 12-name RAW sample, and 12 (API) or 8 (RAW) article bodies for aboutness, always taken from the front of the roster in `CHARACTER_SWEEP.json` order (rank-ordered, not alphabetical: I checked, Marvel starts with Bruce Banner, Peter Parker; only 3 of 131 rosters over 40 names are sorted). This is a measurement of a host, not a roster, so Hard Rule 0's "no sample" may not apply. But it is a head-of-list cut on a ranking, and prominent names hit a right wiki more often than the tail does, so it flatters the lift. Is a head sample the intended probe, or should it be a deterministic stride like `null_rate`'s control?
2. hostcheck.py:1392-1427 `purge` rewrites each record with a read-modify-write `_land(fp, r)` (atomic, but no compare-and-swap and not `pipeline.write_record`). The comment explains why the merging writer is wrong for emptying a list. A concurrent catalogue pass that wrote the same record between the read and the rename is overwritten. Is a CAS via `silence.replace_if_unchanged` wanted here, given `--go` is human-run?
3. sevenfold.py module docstring: "hyperverse exactly 7 - the declared root", but `seams()` may cut fewer (the median-eligibility rule), so an 8-member weighted block yields 6 top branches (`t3.py`: 8 members, weighted, gives 6; the live 209-source graph gives 7). Is "exactly 7" a promise for any input or only for the live roll?
4. escalation.py:637-667, 579-590: a transient failed READ of a real HALT.json (PermissionError while another process is mid-replace) returns the fail-closed stand-in, `_land_halt` then appends the new fault to the stand-in and, if the digest read succeeded a moment later, lands it over the real halt, so the first fault's `code`/`what` leave HALT.json (they stay in escalation.log). `replace_if_unchanged` refuses when the digest is unreadable, so the window is a two-open race. Accepted as too narrow, or should `_land_halt` refuse to build on a stand-in?
5. identity.py:147-150 `_titles()` calls `d.get(...)` on whatever `json.load` returns. A feats cache file holding a JSON list would raise AttributeError outside the try and abort the whole `mine()` (loud, not silent). Are feats caches always objects (I did not scan the 261,000 files)?

## Cleared (examined by hand, found correct)

- tells.py: `_anchor` plus the new import-time DISCOURSE anchor check; `_SENTENCE_START` whitespace tolerance; `prompt_in_sync` CRLF fold and three-valued verdict; the deliberate asymmetry of "not merely X but Y" and the "alike/all/together" scope of the rule-of-three label (both ruled, both documented).
- anchors.py: `vector_score` clamp; all five ANCHORS score dicts against their notes; `run()`'s refused-assay handling (bool excluded, `scored` vs `vals` membership), the `order`/`CLAIMS` membership checks, the graded college/bit invariants, the exit code carrying `ok`; the printed-not-graded INSTRUMENT_WINDOWS owner question is still accurate (`A.INSTRUMENT_WINDOWS` is (30, 30) from M5).
- grounding.py: `classify_text` full-field ranking (`top=None`), `classify_source` refusing `cap`, whole-field confidence denominator, synthesis-blob exemption as documented, uncapped contested list and uncut names, gated `write_json` with exit 1; every GROUNDINGS entry carries the regress kwargs `assay.regress_test` accepts.
- sevenfold.py: `_even_cuts` clamping (never an empty chunk), the window plus weaker-half `seams()` (repro: 209 random-weighted members gave 7 balanced top branches; unweighted gave 7), `build()`'s UNSHELVED accounting to stderr, `main()`'s per-tier member-per-branch table, gated write with exit 1, halt interlock on the writing path only.
- identity.py: `_is_continuity` at n=1/2/>=3 (`t6.py`), `mine()` visited-key rule, `stale_hosts`/`load()` incremental repair and the empty-over-populated refusal, `_inv_keys`/`_inv_counts`, `epoch_of(strict=True)` refusing on an unprobed or over-long answer, `epoch_acceptable` list, `SA._cut` usage (format string arity verified by running it).
- completeness.py: `wiki_host` sentinel/None filter, `_cs_put` snapshot-under-lock with `silence.write_json`, `host_reachable`'s DEAD/RAW/API three-way, `work()`'s branch ladder (unmeasured row shapes, `n is not None`, existing-but-zero), `land()`'s three outcomes and the atomic write, `main()`'s sized columns and printed remainder (`--top` cut is stated).
- escalation.py: `escalate()`'s level coercion (typo lands at MANAGER, non-integral float and out-of-range refused), `brief` whitelist, `_safe_name` injective truncation, `_halt_lock` fail-open lock, `_raise_halt` CAS plus read-back convergence, `clear()`'s ruling then person then signature order and its no-retry-on-changed-identity rule, `_by_a_person_at_the_cli` frame logic (and `main()` deliberately calling `resume_subsystem_verdict`, not the wrapper), `stop_subsystem`/`resume_subsystem_verdict` CAS loops and their unlanded-order handling, pause/unpause, fail-closed `_read_stopped`.
- hostcheck.py: `_land_hosts` CAS with absent/unreadable/non-dict refusals and the second halt check; `candidates_split` (Wikipedia and neighbours never truncated); `null_rate` dedupe-then-stride and MIN_PROBE floor; `score()` ladder ordering (about-n=0, about-n<ABOUT_MIN, veto placement); `sweep(--repair)` lift-based selection; `purge()` per-file accumulation and not deleting caches when the record write is denied; `roster_audit` judgeable split; halt interlock on the writing paths only.
