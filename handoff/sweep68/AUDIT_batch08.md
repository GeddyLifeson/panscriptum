# Sweep68 audit, batch 08

Read-only. Scratch repros in `%TEMP%/aud68_08` (nothing under `state/` or `data/` written; `overwatch`
repro ran against a temp ledger/SRC; every other repro imported pure functions or read data files).
CLAUDE.md Hard Rules -1 and 0 read first. Every line of every module below was read with the Read tool.

## Scope

| module | lines | read |
|---|---|---|
| src/cascade_bridge.py | 2544 | 1-2544 (6 chunks) |
| src/overwatch.py | 1162 | 1-1162 (3 chunks) |
| src/rosetta.py | 866 | whole (2 chunks) |
| src/address_space.py | 664 | whole (2 chunks) |
| src/catalogue_codex.py | 540 | whole |
| src/pantheon.py | 432 | whole |
| src/resync_roll.py | 381 | whole |
| src/repass_bands.py | 244 | whole |
| src/chord_field.py | 210 | whole |

## Prior-audit cross-check (sweep67 batches 06/07/08/09/10/13, and VERIFY files)

| prior item | status now |
|---|---|
| b08 F3 cascade_bridge `length_stopped` ignores `done.truncated` | FIXED (`cascade_bridge.py:786`). Residual in F6 below. |
| b08 F4 size refusal learned as output ceiling for input TPM | FIXED for the ceiling (`:695` requires "output tokens"/"otpm"). The loop half (no bench) stands as Q1. |
| b08 F5 `record_unrecognised` reads any failure as empty ledger | FIXED (`:1259-1271`). |
| b08 Q5 length-stopping / size-refusing bucket never benched | STANDS (Q1). |
| b06 F2 overwatch digest taken after review | FIXED (`overwatch.py:1007`, before `review`). |
| b06 F3 overwatch `actual: null` / non-string symbol | FIXED (`:289`, `:638`). |
| b06 F5 catalogue_codex no halt interlock | FIXED (`catalogue_codex.py:208-230`). |
| b06 F6 catalogue_codex ignores out-of-scope | FIXED (`:282`, `roll.in_scope`); see F4 for the residual substring-bind hazard. |
| b07 F5 address_space overwrites SHELFMARKS from placeholders | FIXED for the fallback and empty-TIERS cases (`:624`). Wider case is F3 below. |
| b07/b12 Q4 address_space, pantheon, onomast write with no halt interlock | STANDS. `address_space.main` (`:643`) and `pantheon.main` (`:265`) still call `silence.write_json` with no `assert_clear`. Owner's call (derived-state writers vs corpus). |
| b07 Q7 `pipeline.records()` skips unreadable records silently, used by repass_bands | STANDS (records() still `continue`s with only a `silence.note`, and also drops any record whose `entries` is empty). |
| b10 rosetta F3 srlimit=50, no continuation | FIXED (`rosetta.py:306-329`, pagination). Unbounded-loop note in Q3. |
| b10 rosetta F4 cut exception text | FIXED. |
| b10 rosetta F5 all-tied labelled "needs 4" | FIXED (`rho_reason`). |
| b10 rosetta Q1 `len(row) > 600` row drop | STANDS (`rosetta.py:180`). |
| b13 resync_roll #5 stale `entry_count` re-landed by `_apply` | STANDS (`resync_roll.py:197-202, 260-276`), unchanged. |
| b09 pantheon items | still clean; `compute`/`value` run against live `Z_FIGHTERS.json` merge (21 entities, all 11 axes present). |
| chord_field, repass_bands (b07) | unchanged logic, still clean. |

## Findings

### F1 (MEDIUM, VERIFIED) overwatch.py:1026 / :958-976 -- a finding retired by ANY edit to its file can never be re-reported, so a real defect vanishes from WATCH.md after an unrelated edit

Quote: `if fid in led["findings"]:` `continue`. `round_once` retires every open finding of a module
whose whole-file digest changed (`f["state"] = "retired"`), but leaves the row in `led["findings"]`. When
the model re-reads the changed file and reports the same defect, `_fingerprint` is
`module|symbol|actual[:80]` (no line, no digest), so `fid` is already in the ledger and the finding is
skipped, staying `retired`. The header promises "stays open until the code it points at changes"; in
fact it stays open until ANY line of the file changes, and then the defect is silenced.

Scenario: high finding on `foo.landauer_floor`. A maintenance run edits an unrelated comment in the
file. Next round: retired. Model re-reads, reports the identical defect, 0 new, WATCH.md says "Nothing
open. Every finding so far has been fixed or was retired when the code it pointed at changed."

Repro (`aud68_08/ow.py`, temp ledger, `review` monkeypatched to return the same finding both rounds):
round1 states `['open']`; append a comment to the module; round2 states `['retired']`, "0 new",
WATCH.md "Nothing open". Live evidence of scale: `data/OVERWATCH.json` has 1,275 retired rows of 2,491
(only 9 open) at round 588. Whether the real model re-emits an identical `actual[:80]` is UNVERIFIED;
the code path that would drop it is not.

Fix: on a fingerprint hit whose stored state is `retired`, re-open it (state open, new digest/first_seen)
instead of skipping.

### F2 (LOW-MEDIUM, VERIFIED) rosetta.py:855-859 -- `--check` returns 0 when it scored nothing

`return 0` unless `bad` is non-empty; unscored rows are counted and printed but never affect rc.
`allsweep.VERIFIERS` runs `rosetta.py --check` (RC_BROKEN) as the "franchise rank agreement" check.
Live data through `check()` (`aud68_08/ro.py`): of 8 scales only Dragon Ball "List of Power Levels"
scores (n=4, rho 0.6); One Piece `Bounty/List` overlaps 1 of 96 names, six others overlap 0-2. With an
empty assay map every row is unscored and `main()` still exits 0. This is the failure the `check()`
docstring says was fixed ("printed an empty list and exited 0 while measuring nothing at all"),
repaired for the printout but not the exit code. Fix: return nonzero (or a distinct rc) when no scale
scored, or when fewer than N did.

### F3 (MEDIUM, VERIFIED mechanism) address_space.py:140-146, 242, 643 -- a legitimate TIERS.json re-chart silently re-addresses all 1,016 published worlds

Upper-tier widths come from `max(v[k]) + 1` over TIERS.json at import. Crossing a power of two changes
a width, which moves every packed address and every `map_seed(addr)`, while the printed `shelfmark`
text is unchanged. `main()` publishes whenever TIERS.json reads (the b07 F5 fix only blocks the
fallback/empty case). The module says re-addressing needs an owner ruling and floors the hash offsets
for exactly this reason; the tier widths have no such floor and no comparison against the standing file.

Repro (`aud68_08/as.py`): `assign('Src::World', row)` with metaverse width 3 vs 4 gives different
addresses and different `map_seed`, identical shelfmark strings (`False True False`). Against live data
the current widths reproduce all 1,016 standing addresses (0 mismatches), so nothing is wrong today; the
next re-chart that adds a metaverse/xenoverse/hyperverse/multiverse crossing 2^n would rewrite every
map seed on the next hand-run, printed "wrote SHELFMARKS.json" and exit 0.
Fix: before `write_json`, compare against the standing file and refuse (rc 1) if any existing
designation's address changes, unless an explicit override flag is passed.

### F4 (LOW, latent, VERIFIED binding) catalogue_codex.py:305 -- substring section match binds a short roll name to an unrelated section

`cands = {t for k,t in sec_by_norm.items() if n in k or k in n}`. `norm("DC") == "dc"` is a substring of
`norm("Sword Coast Adventurer's Guide") == "swordcoastadventurersguide"` ("swor-dc-oast"), the only
candidate, so `title` binds. Verified with the live roll and codex (`aud68_08/cc.py`): the roll row `DC`
and the row `Sword Coast Adventurer's Guide` both bind to the same section. Today `DC` has 55,560
entries so it is skipped; if `hostcheck.purge` or a resync ever zeroes it, the next `catalogue_codex`
run writes SCAG's 176 homebrew entries into DC's record and marks it `catalogued`, attested
"Transcribed". Other non-exact binds on the live roll look sensible (`Player's Handbook`,
`Dungeon of the Mad Mage`, etc.). Fix: require a minimum norm length (or a word-boundary/prefix rule)
for the substring arm, and refuse a title already bound to another roll row.

### F5 (LOW, VERIFIED on constructed strings) cascade_bridge.py:1058 -- bare `\b(401|402)\b` reads a token count or a retry-after as a dead key

`permanent_refusal("...Limit 200000, Used 199599, Requested 401. try again in 6m51s")` and
`permanent_refusal("HTTP 429 too many requests, retry after 401")` are both True (run
`aud68_08/cb1.py`), so `_bury(bucket, AUTH_BENCH)` costs a live bucket four hours. Word boundaries stop
`req_4403abc`, not a standalone number. `402ms` does not match. Probability on live traffic is small
(a request of exactly 401/402 tokens, or a bare-seconds retry hint of 401/402); UNVERIFIED that any
provider emits these. Fix: require the code to follow "http"/"status"/"error" or open the string.

### F6 (LOW, VERIFIED residual of b08 F3) cascade_bridge.py:189-229 -- `_extract_json` still returns an inner object for a cut-off reply

`_extract_json('{"feats":[{"sentence":"a","axis":"x"},{"sen')` returns `{'sentence': 'a', 'axis': 'x'}`
(same for an unterminated fence). The `done.truncated` / `finish_reason` gate now catches flagged
truncation, but a reply the engine did not flag (or a caller on an older engine) still parses as a
smaller answer of the wrong shape. Only the downstream `accept` predicate stands between it and a
result. Fix: prefer the outermost object: if the first `{` fails to decode, return None rather than
scanning inward, unless the reply is prose that precedes the JSON.

### F7 (LOW, VERIFIED by reading) rosetta.py:767-779 -- `--refine` can overwrite ROSETTA.json with `{}` and has no floor

`refine()` keeps only rows naming a Persons entry on the same host. If `P.records()` comes back short
(it silently skips unreadable records and any record with empty `entries`) or `F.HOSTS` misses keys,
every scale falls under the four-row floor and `{}` is written over `data/ROSETTA.json`; `--refine`
reads `OUT`, not the raw copy, so a second run cannot recover. `--mine` has `MINE_FLOOR` for this;
`--refine` does not. Recovery exists by hand (`ROSETTA.raw.json`). Fix: refuse when kept is under a
fraction of before, the way `--mine` does.

### F8 (LOW) resync_roll.py:197 -- `entries: null` in one record file crashes the whole resync

`len(rec.get("entries", []))` raises TypeError for `"entries": null`, an unguarded shape in a loop
whose other malformed-record shapes (non-dict, no source) are all handled and counted. Nothing has
written that shape on disk (I scanned 216 records: none). Also latent: two record files declaring one
source pick the alphabetically last file as winner regardless of entry count (`:149-152`), so a stub
file sorting last would set the roll to the stub's count (0 -> "uncatalogued" and re-catalogue). No live
duplicates today. Reported to the operator in the output, so this is not silent.

## Questions

Q1. cascade_bridge: an input-size refusal (Groq TPM "Requested > Limit") and a capped call whose
provider gives no `finish_reason` are named and recorded but never benched, so the same bucket can be
re-claimed each call (b08 Q5 restated). Should N consecutive of either earn a bench like
`UNPARSEABLE_STRIKES_BEFORE_BENCH`?
Q2. cascade_bridge `_ask_call` `:2158`: on a success where the engine failed over off the pinned bucket
(pinned 429/401, neighbour answered) `_clear(pinned.bucket)` still runs, resetting the pinned bucket's
deadline strikes. A bucket that alternates deadline misses with failover successes never escalates past
the first 60 s bench. Intended?
Q3. rosetta `scales_for` `:307-329`: the `sroffset` follow has no iteration bound; a wiki that returns the
same `continue` forever would spin one query. Add a page cap or a seen-offset check?
Q4. `dead_forever()` returns an empty set once POOL_PROOF.json is over an hour old (`PROOF_TTL`), so if
the prover stops, every permanent exclusion not in `OWNER_EXCLUDED` silently lapses. Intended fail-open
on age?
Q5. `repass_bands` (and `pipeline.records()` under it) never sees a record with empty `entries`, so an
unearned source-level `synthesis.provisional_magnitude` on a purged record is never demoted. Intended?
Q6. Halt interlock for `address_space.main` / `pantheon.main` (carried from b07 Q4).

## Cleared (read closely, nothing found)

- chord_field.py: whole file; `total_beta` (sum 328), `landauer_floor`, `recoil_momentum`,
  `critical_power_self_focus` formulae correct; the two constants used are used; nothing else imports
  dropped names.
- repass_bands.py: gate-on-write (`write_record` verdict counted, `denied` reaches rc), `scale_note_rejected`
  companion set before the note is cleared, halt only on the `--apply` path, uncapped listings, dry-run
  writes nothing.
- pantheon.py: `compute` runs against `assay.assay` for all six hand-built gods (M8 x4... anchors match
  bands), merge failure and `_incomplete` both reach rc, write verdict reaches rc, `--full` prints all
  ranked entries and reads provenance defensively.
- resync_roll.py: argparse dry-run, halt asked only on the write path, `_apply` re-checks the OUT_OF_SCOPE
  guard on the fresh row, closing figure is read back from disk, denied write returns 1.
- catalogue_codex.py: manifest count cross-check, `(type,name)` dedupe with reported repeats, ambiguity
  binds nothing, register descriptions used only when unanimous, write goes through
  `write_record_catalogue` (merges with the disk copy) and `roll.update_rows` (CAS), rc carries both
  denials. Live parse: 64 sections, 4,489 elements, 0 count mismatches, no `####` splitting.
- rosetta.py parsers: `numeric_rows` first-number rule, 1000x-median cut, `ordinal_rows` case-safe offsets,
  `stand_rows`, `spearman` tie ranks, `assays_by_host` partition, `refine` kept/dropped arithmetic,
  `--mine` floor and both-file write gate.
- address_space.py: `pack`/`unpack` round trip, `_hash_offsets` legacy floor (reproduces 8/48/78; all 1,016
  standing addresses reproduce with today's widths), `fit()` no-modulo, fallback flag blocks the write.
- overwatch.py: `load()` wreck preservation and `_UNPRESERVED`, `save()`/`_reconcile_with_disk`/
  `_merge_ledgers` monotone merge, `_finished_at` single scale, per-round `_LOCAL_BUSY` reset, `seen`
  stamped only on complete reads, yielded findings not stamped in `verify_open`, halt re-asked each round.
- cascade_bridge.py: `engine()` double-checked build, pace gate, `dead_forever` freshness memo,
  `_alive`/`_bury`/`_clear`, reservation try/finally covers every return, `local_excluded_kw`,
  `record_unrecognised` CAS + read-back, `unrecognised_open` re-triage, `length_stopped` (engine
  `truncated` now honoured, capped-without-reason refused), `--help` does not spend a call.
