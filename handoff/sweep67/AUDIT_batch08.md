# Sweep67 batch08 - AUDIT (run67)

READ-ONLY audit. Nothing under src/, data/, state/, output/, prompts/, reference/ or the repo root
was edited. No subagents. Scratch scripts lived under %TEMP%/b8 only. runguard was never called
against the real guard path (state/MAINTENANCE_RUN.json untouched; only read by inspection of code).
One outbound test: a plain urllib GET of two public https pages to check the TLS path (both 200).

## Scope (every line read with the Read tool, in chunks)

| module | lines |
|---|---|
| cascade_bridge.py | 2526 (6 chunks) |
| ledger_guard.py | 1157 (3 chunks) |
| scout.py | 835 (2 chunks) |
| runguard.py | 660 |
| worldseed.py | 536 |
| hosts.py | 424 |
| events.py | 350 |
| propagation.py | 254 |
| catalog.py | 167 |

CLAUDE.md hard rules -1 and 0 read first. cascade_bridge (2340 -> 2526) and ledger_guard (1111 ->
1157) are larger than sweep66 saw: both carry edits dated 2026-09-28 (orders cb4fbedeb0db,
30122bf3a5a7, a5faab7f3ede). Those new paths got the closest reading.

## Prior-audit cross-check (handoff/sweep66)

- cascade_bridge (b08): sweep66 said zero findings on the 2340-line file. Its open Groq
  `finish_reason`/`max_tokens` question (af47010df391) has since been answered in code (size
  refusal class, learned ceiling, `length_stopped`, `exclude_local`). Read in full: two findings on
  that new code (F3, F4). `CASCADE_BRIDGE_HAS_NO_REACHABLE_MODEL` is config outside this tree; not
  re-verified (would need reading <CASCADE_HOME>/config.json), the header comment is unchanged.
  `OWNER_EXCLUDED` still has no clearing path: still true.
- ledger_guard (b05): the open floor-advance question a5faab7f3ede is now implemented as
  `_floor_union` (comment says decided under the owner's 2026-09-28 instruction). Traced, sound as a
  multiset union; consequences raised as Q1 and Q2. The `_snapshot_path` drift fix, the
  heading-vs-substring section detection and the multiset `_lost_fraction` still hold. I checked the
  bug-id check against the live BUGS.md: `[m14]` and `[M14]` are two different series (61 vs 16 ids),
  so the case-sensitive comparison is correct; a case-folded one would give 11 false hits.
- hosts (b05/b13, order 3fb312a72435 "no caller"): NO LONGER TRUE. feats.py:2482 imports it
  (`HS.hosts_for(..., include_primary=False)`, fail-closed on an unreadable file). Three other files
  still say it has zero callers: onomast.py:454, descending_ladder.py:42, scale_theories.py:26 (all
  outside this batch; stale comments, not filed as a finding here).
- scout (b11): sweep66 cleared it. It has real defects (F1, F2) that the earlier reads missed.
- runguard (b10): zero findings then, zero findings now (see Cleared; three questions).
- worldseed (b16): cleared then; F7 and F8 are new.
- events (b03): cleared then; F6 is new.
- propagation, catalog: zero then, zero now.

## Findings

### F1 - scout.py:328, :485 - a 403 is treated as proof the page exists, and a 429 as "declines readers". MEDIUM, VERIFIED on live data
`verify()` maps HTTP 401/403/429 to "exists but declines readers", and `scout()` writes every such
URL into SCOUT_BLOCKED.json. foreman.py:2098-2118 then prints that file in FOR_OWNER.md under
"Material that exists but declines automated readers ... Mostly paid products". But a WAF answers
403 for any path on the host, existing or not, and 429 is a rate limit, not a refusal.
Evidence: the live data/SCOUT_BLOCKED.json lists, for "Curious DM Investigations (the Sharkin)",
twelve gmbinder.com/share/ URLs such as `-L-9J1-y-1-y-1-y-1-y-1` and `-L-9J_5_1_2_3_4_5_6_7_8_9_0`,
which are model inventions; and SCOUT.json's 40 logged cycles hold 16 checked URLs at
`(403, exists but declines readers)`. Entries are add-only (`sorted(urls_blocked | prev)`), never
cleared even when the source is later registered. The owner's decision document is being fed
hallucinated URLs labelled as existing material.
Fix: treat 403 as "unknown" (not "exists") unless a cheap control shows the host 404s a
deliberately invented path; drop 429 from the set and retry/bench instead; prune a source's blocked
entry when `registered is True`.

### F2 - scout.py:330-333 - every transport exception becomes "no such host or no route". LOW-MEDIUM, VERIFIED by reading, live counts
`except Exception` in `verify()` covers DNS failure, timeout, connection reset and TLS verification
errors (this machine has a Norton TLS root that breaks Python HTTPS elsewhere) and reports them all
as an invented URL ("Nothing to do; do not try it again" in the docstring). SCOUT.json holds 12
`URLError` rows recorded that way. `sweep()` stamps attempts before the work and only unstamps when
`reached is False` (the model leg); a network outage during the fetch leg burns the rotation slot
for every source and writes a clean negative for each. This is the fault order 7f2cbf26a60e fixed
for `_ask`, left unapplied to `verify`. Fix: return `"transport": True` for non-HTTPError
exceptions and have `scout()` set `reached` False (or a separate `unverified`) when every checked
URL was a transport failure.

### F3 - cascade_bridge.py:2158-2168 - the engine's `truncated` flag is ignored, and `_extract_json` turns a cut-off reply into an inner object. MEDIUM, VERIFIED (offline)
The 2026-09-28 gate refuses replies whose `finish_reason` is a length stop. The engine's `done`
event also carries `truncated` / `truncated_reason` for a stream that broke, timed out or ended
without a completion marker (engine.py:497-530, :631-636); `length_stopped()` does not read them.
Repro: `_extract_json('{"feats":[{"sentence":"a","axis":"b"},{"sentence":"c","ax')` returns
`{'sentence': 'a', 'axis': 'b'}` (raw_decode fails at the outer `{`, then succeeds at the first
inner one). `length_stopped({"finish_reason":"stop","truncated":True,"truncated_reason":"stream
ended without terminator"}, False)` returns False. So a dropped stream yields a smaller answer in
the shape of a complete one, the Hard Rule 0 truncation the new code was written to stop. Only the
downstream `accept` predicate stands in the way, and for a schema whose inner object is itself valid
nothing does. Fix: in `length_stopped` also return True when `done.get("truncated")`.

### F4 - cascade_bridge.py:635, :687-717, :2031-2045 - the size-refusal class cannot tell an OUTPUT limit from an INPUT/TOTAL limit, and never benches. MEDIUM, classifier VERIFIED, loop consequence INFERRED
`_SIZE_REFUSAL` matches any "request too large ... Limit N ... Requested M" with M > N. Groq's
ordinary TPM refusal ("on tokens per minute (TPM): Limit 12000, Requested 14000, please reduce your
message size") matches: `size_refusal_limit()` returns 12000 and it is learned as an OUTPUT ceiling
(`output_cap_for` = 10800). That refusal is about the prompt, which `max_tokens` cannot shrink. On a
cap-capable engine the branch at :2032 returns None without `_bury` (bury only happens when the
engine cannot cap) and without a ledger row or `silence.note`, so the same oversized prompt can be
routed to the same bucket every call, silently. Before this change it at least reached the
unrecognised ledger. Fix: require the provider's text to name OUTPUT tokens ("output tokens",
"otpm") before learning an output ceiling; otherwise bury the bucket for the stated retry/floor bench
or record it as unrecognised.

### F5 - cascade_bridge.py:1249-1254 - `record_unrecognised` reads any failure as an empty ledger. LOW, VERIFIED by reading
`except Exception: rows = {}` and `if not isinstance(rows, dict): rows = {}` mean a readable-but-
corrupt or transiently unreadable POOL_UNRECOGNISED.json is replaced whole by one row when the
compare-and-swap digest matches. `silence.replace_if_unchanged` refuses only an unreadable target,
not a corrupt one. Only FileNotFoundError is legitimately empty; scout._mutate states the rule
("an unreadable shared artifact is not an empty one"). The ledger is the place a fault nobody has
spotted lives, so losing it is quiet. Fix: on any non-FileNotFoundError, note and return without
writing (or retry the read).

### F6 - events.py:65 - a bolded span over 80 characters is dropped without a record. LOW, VERIFIED on live data
`BOLD = \*\*([^*]{2,80})\*\*` never matches longer spans, so they are neither named nor listed in
`candidates_refused`, against the module's own claim (lines 67-69) that a filter never silently
drops rows. The Chronicle has 35 bold spans; 34 match. The missed one is the 93-character
"End of Fascicle One. E-1204-DELIVERY ..." (a sentence, so harmless today). Fix: match `{2,}` and let
`_looks_like_a_sentence` refuse over-long spans with a recorded reason (add an 80-character or
word-count rule).

### F7 - worldseed.py:433-522 - `--limit N --write` overwrites data/WORLDSEEDS.json with the subset. LOW-MEDIUM, VERIFIED by reading
`build_all(limit)` returns the first N worlds and `--write` lands them whole via `silence.write_json`.
Nothing refuses or warns. pipeline.py:2955-2984 refuses an unparseable file but happily
re-addresses from a valid partial one, and address_space.py:571 reads it too. Fix: refuse `--write`
when `--limit` is set (or write to a different path).

### F8 - worldseed.py:83-103 - short-stem `\w*` patterns label a match "attested" that is not. LOW, VERIFIED (repro)
`war\w*`, `sea\w*`, `ash\w*`, `ice\w*`, `keep\w*`, `plain\w*` and friends match word prefixes.
`features("X", "The Warden of Ashford keeps the seat of the Search Guild in a warm keeper's hall.")`
returns condition=wartorn, climate=oceanic, tech=medieval, all tagged "attested". The
attested/seeded tag exists so a reader can trust it; a prefix hit on "Warden" or "Search" defeats
that. Fix: put a trailing `\b` on the short stems or list the intended suffixes.

### F9 - stale or wrong comments and diagnostics. LOW, VERIFIED
- ledger_guard.py:722: the failure message names `os.path.join(SNAPSHOT_DIR, name)`, i.e.
  `state/ledger_snapshot/handoff/HANDOFF.md`. The real copy is at `_snapshot_path(name)`
  (`handoff__HANDOFF.md`); the directory listing confirms only the flattened files exist. This is
  the drift `_snapshot_path`'s docstring warns about, in the one message a person reads on a refused
  push.
- ledger_guard.py:805-809 (`_read_chain_lines` docstring): says `seal()` appends with a plain
  `open(..., "a")`; it has used `silence.append_line` since order f7b611d107cb (seal, :390-411).
- worldseed.py:371-373: refers to "line 315" for the `reg_by_group` initialisation; it is at :359.

## Questions (possibly deliberate design)

Q1. ledger_guard `_floor_union` (:600-625, :527-536): the floor is add-only, so every honestly
    edited or re-wrapped old line stays in it as "lost" forever, and `check_since_floor` measures
    against it with the fixed 5%. Rewrapping one 6-line paragraph costs six lines of the ~35-line
    budget on handoff/HANDOFF.md (733 substantive lines). The comment says rebuilding the floor is
    a person's act, but no CLI or procedure for it exists. Is the eventual permanent refusal of
    `publish.push()` intended, and who documents the rebuild?
Q2. ledger_guard `check_since_snapshot`/`check_since_floor`: a missing snapshot or floor file
    passes as "no sealed snapshot yet" even though the chain holds hundreds of links. Deleting
    state/ledger_snapshot/ resets both baselines silently. Fail-open by design (bootstrap)?
Q3. runguard `beat()`/`release()` check only the agent name, while `claim()`'s docstring argues a
    name proves nothing and mints a token. Intentional (token only for publish --push)?
Q4. runguard `main()` inspection: a torn guard prints "no readable record - a run may proceed" and
    an unfinished record with no heartbeat prints "nan min ago ... free"; `read_verdict`'s fault is
    not surfaced there, only in `claim()`. Also `holder_is_live` treats a heartbeat far in the
    future (or `Infinity`) as live forever. Acceptable for a CLI that only reports?
Q5. cascade_bridge: a bucket that keeps length-stopping or size-refusing on a cap-capable engine
    is never benched; a capped call to a provider that omits `finish_reason` is refused every time.
    After N consecutive such outcomes should the bucket earn a bench like `UNPARSEABLE_STRIKES...`?
Q6. scout `scout()`/`verify()`: model-proposed URLs (anything starting with "http") are fetched with
    no private-address filter (http://localhost:11434/..., LAN hosts). GET only and the body is only
    name-matched. Acceptable for a local research tool?
Q7. events `parse()`: a heading's body runs to the next heading of the same or higher level, so a
    coded child heading's bold spans are also credited to its coded parent. I did not check whether
    the live Chronicle has such nesting. Intended?

## Cleared (read closely, no defect)

- cascade_bridge: `engine()` double-checked build and publication order; `_extract_json`'s
  raw_decode scan (apart from F3); `dead_forever` freshness memo; `_DEAD_CODES`/`_TRANSIENT_*`/
  `_PERMANENT_*` word-boundary classifiers and `local_transport`/`client_rejection` guards;
  `retry_after_seconds` clamps; `_bury`/`_clear`/`_alive`; claim/reserve/release pairing inside the
  single `try/finally` (every return path releases); `local_excluded_kw` (engine.py:273-284 does
  accept `max_attempts`, `max_tokens` and `exclude_local`); `ask()`'s metric expression precedence;
  unparseable-reply strike/bench/reset; `prove()`/`try_disabled()` isolation checks.
- ledger_guard: `_one_insertion` prefix+suffix proof; heading-anchored section spans; multiset
  `_lost_fraction`; `_floor_union` idempotence (order of kept lines can shift once, then stable);
  `verify_chain` unit selection across legacy/new links; acknowledgement validation; check ordering
  in `assert_intact` (checks before `seal`).
- scout: `_mutate` fail-closed read, thread-id temp names, `_unstamp` restore logic, `seen_ok`
  handling, SCOUT.json archive-before-trim, `--limit 0`; `verify()`'s `needed` floor arithmetic.
- runguard: CAS ordering (digest before read) in claim/beat/release; three-fault `read_verdict`;
  stale-but-alive arm only ever answers "live"; `guard_fault` positive-evidence-only arm.
- hosts: `_load` absent-vs-corrupt, `add()` CAS loop and three-state return, `discover()` outcome
  tallies (thin roster / probe failed / lost writes all reported, none capped).
- events, propagation, catalog: Dijkstra, `observed_mark` loop (trailing `return 0` unreachable as
  documented), exit-code verdicts, missing-catalog note, uncapped missing-source list.
