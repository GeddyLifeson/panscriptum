# OWNER DECISION DIGEST — BATCH 02 (20 orders)

Verified against the live tree 2026-09-07. Read-only pass; nothing in `src/` was touched, no
order closed, no gate moved. A mutation run is active (`state/MUTATION_ACTIVE.json`, pid 68112,
targets `assay.py` / `prose_gate.py` / `escalation.py`), which is itself evidence in one of the
blocks below.

**17 still live · 3 dead · 6 to reroute.**

---

### 342ccfafa4a4  [OWNER] [MAJOR]  — configured model is a thinking variant the config forbids
STILL LIVE: yes — `config.yaml:37` still reads `model: "qwen3:8b"`, and `src/generate.py:243` is
still `return data.get("response", "")`. `grep -i think src/generate.py` returns **zero** matches
outside a comment about template sections; there is no stripping anywhere. Two facts the order did
not have: (i) Ollama on this box holds **only** `qwen3:8b` — the documented
`qwen3:30b-a3b-instruct-2507` is **not installed**, so `pick_model.py --write` would re-pick the
thinking model it is being asked to replace; (ii) `pick_model.py` scores tier / instruct-tag /
size and **never asks `/api/tags` about the `thinking` capability**, so the tool the config points
at cannot enforce the config's own requirement. `prose_enabled: false` at `config.yaml:108` is
still the only thing standing between this and think-tags in published volumes.
QUESTION:   Which model does the prose lane run on before the prose gate is ever opened — and is
the fix a model change or a code change?
OPTIONS:    (a) pull `qwen3:30b-a3b-instruct-2507` (18.6GB), point `model:` at it, and land the
mechanical check (configured model must not advertise `thinking`) as part of the same ruling
(b) keep `qwen3:8b` and BOTH strip `<think>` in `generate.py` before anything is written AND
rewrite the 30-line comment block so it describes the model actually in use
(c) split the lanes — thinking model for the repair rung, non-thinking for prose — which
`config.yaml` does not currently support and which is therefore a config-schema change first
RECOMMEND:  **(a)**, with (c) as a follow-on. `qwen3:8b` has never been benchmarked against a real
chapter job — the measured table in `config.yaml:11-16` covers the 30B, gemma3:12b and qwen2.5:14b
and not this model — so (b) asks you to keep an unmeasured model and write code to compensate for
it. Landing the capability check *with* the ruling is the point: written before it, the check would
freeze the current mismatch, which is exactly what the order warns against.
COST IF WRONG: (b) leaves the prose lane on a reasoning model that spends its answer budget
thinking before it emits — already measured this shift as rc=1 after 570s on the repair rung — and
`generate.py` has no output ceiling, so a padded response ends a chapter mid-entry.
UNBLOCKS:   9b54659bc403 (LOCAL rung returning empty-handed) is the transport half of the same
symptom and is already at RUN; this ruling tells that rung whether the model choice was the other
half. `pick_model.py`'s missing capability check is a RUN item that falls out of either answer.
THEME:      model configuration

---

### 5be28f56946c  [OWNER] [MAJOR]  — quarantine handoff brakes nothing; comment claims it does
STILL LIVE: yes — and worse than filed. `feats.py:168` is still the only `is_quarantined` call in
the tree outside `binding_health`/`drill`, and it still guards only against double-quarantining.
The fetch path (`api`, `_throttle`, `fetch`, `evidence_for`) asks nothing. New live evidence:
`data/HOST_QUARANTINE.json` currently holds **seven hosts** — marvel, onepiece, naruto, dragonball,
mtg, hokuto and dandwiki — and **every one of their `retry_after` stamps has already expired**
(-1.1h to -235.8h). So the "retries on a slow cadence" half of the comment is not running either;
`data/BINDING_HEALTH.json` was last written 2026-08-27. marvel was re-quarantined 2026-09-06 at 26x.
Six of the Acquisitions Roll's largest hosts are in this state right now.
QUESTION:   Should a quarantined host stop receiving requests from the running roll, and if so does
the roll DEFER it or DROP it?
OPTIONS:    (a) amend the comment to say the handoff is a RECORD, not a brake — local, honest, zero
behaviour change
(b) have the fetch path consult `is_quarantined()` and **DEFER** — re-queue the host at the end of
the roll at the floor pause, and report the source as incomplete rather than as mined
(c) consult and **DROP** the host for the pass
RECOMMEND:  **(b), with (a) applied inside the same change and never on its own.** Dropping is a
smaller universe wearing the same shape as the real one, which Hard Rule 0 forbids outright;
deferring costs latency and nothing else. Applying (a) alone deletes the only sentence currently
claiming the brake exists, which is how a missing safety stops being visible instead of being
fixed — the order says so and it is right.
COST IF WRONG: leaving it as-is means twelve workers keep queueing on six blocked fandom hosts at
the 32x ceiling — ~11s per request, never zero — for the rest of every roll, on a project that has
been IP-banned once already (`feats.py` says so in its own `_PAGES_TEXT` comment).
UNBLOCKS:   **959b98f38a63** (OWNER/MAJOR, still open) is the same condition seen from the
concurrency end — it measured 75 consecutive throttles on marvel and correctly says the setting is
wrong. 75 is only reachable *because* the handoff at 3 strikes brakes nothing. Rule on both at once:
lower **per-host** concurrency (not total workers) and make the quarantine defer. That also closes
the six recurring HOST_QUARANTINED orders and 3dc2832846bc that 959b98f38a63 names.
THEME:      crawl politeness

---

### 4f5fa3146cc4  [SESSION] [MAJOR]  — foreign edit during a mutation run halts the whole library
STILL LIVE: yes, and the exposure window is **open as you read this**. Lines drifted but the
mechanism is intact: `mutate.py:1913` `live_before`, `:2160` `live_after`, `:2191`
`live_file_untouched`, and `:2643-2650` still answers a difference with
`escalation.escalate(escalation.OWNER, "MUTATE_TOUCHED_LIVE_TREE", ...)` → `state/HALT.json`.
`state/MUTATION_ACTIVE.json` shows a pass running right now over exactly the three files the order
names — `assay.py`, `prose_gate.py`, `escalation.py` — i.e. the three this project's maintenance
shifts edit most.
QUESTION:   Should `MUTATE_TOUCHED_LIVE_TREE` keep the OWNER rung now that the sandbox rewrite makes
the failure it is named after impossible by construction?
OPTIONS:    (a) keep OWNER, but rewrite the message so it stops naming this process as the corrupter
(b) drop to a run-level abort: "someone else edited this file while we read it, so this target's
verdicts are void" — stop the run, do not halt the library
(c) keep OWNER and add nothing
RECOMMEND:  **(b), with the message from (a).** The finding is true and worth stopping on, but it
says the *run* is unsafe, not the library — and `mutate.py` already treats a concurrent editor as
an expected condition elsewhere (`tree_is_moving()` only WARNS). This does not weaken a safety: the
sandbox is what prevents the original incident, and the digest keeps reporting; only the rung and
the sentence change.
COST IF WRONG: choose (c) and one repair agent landing one line in `src/assay.py` during a sixteen-
hour `--target all` pass halts the entire library over a file the run never touched. Note the
check is *also* blind to the window between the two readings, so it cannot see the corrupt-then-
restore failure it commemorates — do not let it keep claiming that coverage under any option.
UNBLOCKS:   none directly, but it is the same "a breach read from a tree under active edit" question
the 2026-09-05 halt ruling in `state/HALT.json` explicitly deferred to an owner order.
THEME:      mutation harness

---

### c614f7c145fc  [OWNER] [MAJOR]  — a halt was lifted by an automated actor, not a person
STILL LIVE: yes, but **half of it is already answered**. The order asked two things. The record half
is done: `escalation.py:1083` now carries `--by`, its comment cites this order by id, and it works
in practice — `state/HALT.json` records the 2026-09-05 lift as
`cleared_by: "scheduled-maintenance-2026-09-05-daily"` rather than the `owner-cli` default. The
authority half is untouched: `clear()` still gates on `_by_a_person_at_the_cli()`
(`escalation.py:904-932`), which asks whether `escalation.py` is `__main__` and whether the caller
is its own `main()` — both true for a scheduled run — and the `--by` default is still `owner-cli`,
so honesty remains voluntary.
QUESTION:   Should lifting a halt require something a scheduled run cannot supply, and if so what?
OPTIONS:    (a) leave it: the guard is the strongest question code can ask, and the record is now
honest when the caller volunteers
(b) require an out-of-band token a scheduled run does not hold (a file the owner writes by hand, a
prompt on a real tty, a passphrase)
(c) keep the current gate but make the `--by` default refuse rather than read as a person —
`clear()` errors unless `--by` is passed explicitly
RECOMMEND:  **(c) now, (b) only if you want the asymmetry to be real.** (c) is small, closes the
"reads as a person" gap permanently rather than relying on an agent's good manners, and costs a
person at a terminal one extra flag. (b) is the only option that actually makes the charter's
asymmetry enforceable, and it is a genuine operational cost on unattended runs — that trade is
yours, not the code's.
COST IF WRONG: pick (a) and the next unattended run that lifts a halt on defensible merits does so
with the publish daemon resuming behind it — which is what happened on 2026-08-26 (public pushes at
01:01 and 01:07 that nobody decided on) and again on 2026-09-05.
UNBLOCKS:   none — but note this is not hypothetical any more; it has now happened twice, and the
second time the actor did sign its own name, which is the system working as far as it currently can.
THEME:      halt authority

---

### 6fc71f8ab76e  [OWNER] [MINOR]  — feat-less entries never nominated once a source has any feats
STILL LIVE: yes. Moved to `pipeline.py:1459-1460`; the short-circuit is unchanged:
`blocks = ([with_feats[i:i+14] ...] or [rest[i:i+14] ...])`. The 2026-08-25 owner ruling recorded
in the comment directly above it removed the **cap** on `rest` (the `[:14]`) but did not touch the
`or` that keeps `rest` from being reached at all whenever `with_feats` is non-empty.
QUESTION:   Does "this entity has no mined feats" mean the entity has no deeds, or only that the
miner has not reached it yet?
OPTIONS:    (a) intended — a ceiling drawn from an entity with no cited evidence is the fabrication
Hard Rule 1 forbids; `rest` is correctly a fallback for sources with nothing at all
(b) a silent stranding — feat coverage is partial, so the absence is partly a statement about crawl
progress, and an unmined entity is permanently excluded by three siblings that happened to be mined
RECOMMEND:  **(b) — nominate both, feat-bearing blocks first.** Your own 2026-08-25 ruling on the
line above already settled the underlying principle in the same direction ("the tail is now REACHED
rather than discarded"), and given the block above it — six of the roll's largest hosts quarantined
with expired retries — "has no feats" is demonstrably a statement about crawl progress right now.
Ranking survives; the truncation does not.
COST IF WRONG: (b) is the expensive answer — the same 65-calls-instead-of-1 spend the 2026-08-25
ruling accepted, now applied to sources that already have some feats. (a) is cheap and, while the
miner is behind, publishes ceilings chosen from a fraction of each source.
UNBLOCKS:   none — but the same "is an absence a fact or a gap" question is the live one in
c8dc624e4e02 below, and a consistent answer would help both.
THEME:      evidence semantics

---

### 1cdc2f8cd2f3  [OWNER] [MINOR]  — does Hard Rule 0 reach announced console truncation
STILL LIVE: yes. `identity.py:717` still reads `top[:6]` with a `+{len(top)-6} more` marker at :718,
and a second announced cut sits at `identity.py:354` (`missing[:6]`, ", and N more"). Both are
`print()` paths in `main()`; neither reaches data the pipeline consumes.
QUESTION:   Does the no-caps rule govern console reports, or only rosters the pipeline reads?
OPTIONS:    (a) rule that Hard Rule 0 governs pipeline-consumed data only — an announced console cut
is legitimate, and orders about them may be closed on sight
(b) rule that it governs every listing — uncap the console reports too
RECOMMEND:  **(b), and write it into CLAUDE.md so it stops being re-derived.** The precedent already
went that way once: order 6434c1ba7b20 uncapped `catalog.py:76-78` to print every missing source,
and a rule that has been applied to one console listing and denied to the next is not a rule. These
are terminal prints of at most a few dozen rows; the cost is a longer scroll.
COST IF WRONG: (b) makes some reports long. (a) is defensible on the merits but leaves this
question to be re-litigated by every sweep, which is the actual cost being paid today.
UNBLOCKS:   By the order's own account this settles the re-filings against `handbuilt.py cited[:58]`,
`repass_bands.py` 8/14, and `hosts.discover per_source=24`, and stops the family being re-filed
every sweep. Highest ratio of orders-closed to seconds-spent in this batch.
THEME:      truncation doctrine

---

### e68664e621bf  [OWNER] [MINOR]  — URL_SETTABLE is read by nothing and has already diverged
STILL LIVE: yes. `worldseed.py:262` still defines it; `grep -rn URL_SETTABLE src/*.py` returns that
line only; `worldseed.py:274` still builds its own dict literal including `"options": "default"`,
which `URL_SETTABLE` does not list.
QUESTION:   Keep the constant and make it load-bearing, or delete it?
OPTIONS:    (a) have `to_fmg_query` build its query FROM `URL_SETTABLE` (adding `options`), so a
parameter cannot be emitted without being declared
(b) delete it and let the measured comment block at :245-261 carry the finding as prose
RECOMMEND:  **(a).** The module's whole stated discipline is that the emitted set must match the
honoured set, and (a) makes that mechanical instead of aspirational for four lines of work.
COST IF WRONG: (b) is safe but throws away the one place a future parameter could be caught before
it is silently discarded by Azgaar — the exact failure the comment block was written about.
UNBLOCKS:   **This is one question asked four times.** Rule once on "an unread public symbol: mark,
or delete" and it settles e68664e621bf, de43fe54feb7 (`scope.ceiling_for`), c0384991bfc5
(`worldseed.unreachable_by_url`, still open) and retroactively 0b1cda11f4a2 below. The tree already
has a house answer — `feats.py:1346-1352` carries a REPORTED DEAD, NOT DELETED marker per order
25ec11447b4c — so the cheap ruling is "mark them all the same way, delete none."
THEME:      dead symbols

---

### de43fe54feb7  [OWNER] [MINOR]  — scope.ceiling_for has no callers anywhere in the tree
STILL LIVE: yes. Now at `scope.py:259`. Repo-wide grep (excluding `handoff/` and `__pycache__`)
returns the def line plus three of its own comments; `magnitude.host_ceiling` at `magnitude.py:942`
remains the live path to the same data.
QUESTION:   Delete a public function nothing calls, or mark it dead and keep it?
OPTIONS:    (a) delete
(b) mark it REPORTED DEAD, NOT DELETED, the way `feats.axis_evidence` is marked
(c) make `magnitude.host_ceiling` call it, so the ceiling rule has one definition
RECOMMEND:  **(b) unless you take (c).** (c) is the better engineering answer — `host_ceiling`
reimplements the live-probe fallback, so there are two definitions of one rule — but it touches a
live Magnitude path and is a bigger change than this order is asking for.
COST IF WRONG: deleting costs nothing today; the risk is only that the duplicate rule in
`magnitude.py` then has no visible sibling to be compared against.
UNBLOCKS:   settled by the same ruling as e68664e621bf. See that block.
THEME:      dead symbols

---

### 8fb33a0204c4  [OWNER] [MINOR]  — the printed shelfmark omits the star field entirely
STILL LIVE: yes, and there is a **new** contradiction the order did not have. The return at
`address_space.py:237-238` prints seven elements (H, X, Mt, Mv, U, G, P) and no star, while
`FIELDS` at :168-177 declares eight — but the docstring, as amended by order 3891e4317946, now says
at :229 *"the other four fields, U, G, the star and P, are hash draws"*, describing the star as part
of a line it is not on. So the module now states the defect in prose and still does not fix it.
No live collision: all 1,016 rows in `data/SHELFMARKS.json` remain distinct, absorbed by the 38-bit
galaxy draw.
QUESTION:   Is the charter's seven-tier notation authoritative, or is the eight-field address?
OPTIONS:    (a) notation wins — drop `star` from `FIELDS`, or keep it and have `shelfmark()`'s
docstring say out loud that it is a lossy projection, with `seed_from_card` keying on the address
rather than the printed name
(b) address wins — add an `S.` element to the format string
RECOMMEND:  **(a), the docstring-plus-`seed_from_card` variant.** The charter's own worked shelfmark
at `address_space.py:98` has no star either, so (a) is faithful to Part Two; and (b) re-addresses
every world's map seed, which `address_space.py:283-291` already flags as needing your ruling for
the sibling legacy-offset case, with 1,016 worlds standing.
COST IF WRONG: (b) invalidates every published map seed at once. (a) leaves 2^27 addresses sharing
a printed name — latent, not live, and only becomes real if `star` ever starts varying independently
of galaxy.
UNBLOCKS:   the legacy hash-offset ruling at `address_space.py:283-291` is the same "does
re-addressing 1,016 worlds cost more than the inconsistency" trade; answering one answers both.
THEME:      address notation

---

### 845dbaec182f  [OWNER] [MINOR]  — coin_well_formed's exhausted exit returns a rejected name
STILL LIVE: yes, narrowed. The diagnostic half was fixed by sweep42-batch16: `onomast.py:305-310`
now inspects the fallback and names the specific defect ("malformed" / "ALREADY TAKEN — this
designation now names two things") on stderr rather than only bumping a counter. The substantive
half stands, and stands **deliberately** — the comment at :291-293 says so: the function still
returns the byte-identical string it computed and rejected at :278-280.
QUESTION:   When the register runs out of namespace, does the library refuse to name, or issue a
name it knows may be a duplicate?
OPTIONS:    (a) raise — a duplicated shelfmark silently reassigns already-published citations, which
is worse than a loud stop
(b) keep returning a designation, but make the last resort **provably unique**: append a short
digest of `base` to the stem and stamp the record `coined_under: "exhausted"`
RECOMMEND:  **(b).** It keeps the module's stated position (refusing to name anything is the worse
failure) while ending the thing that is actually indefensible — an exit that returns a value it has
just tested and rejected, which is the shape of a check that cannot fail. "Shelfmarks are unique" is
one of the 39 standards and (b) restores it; (a) protects it by stopping the run instead.
COST IF WRONG: (b) yields names that read less well in the rare exhausted case. (a) stops world
naming dead when a register fills, which on a 10,000-candidate space means something upstream is
already wrong — arguably the right time to stop.
UNBLOCKS:   none.
THEME:      identity uniqueness

---

### c8dc624e4e02  [SESSION] [MINOR]  — unbound host and no-feats give one indistinguishable answer
STILL LIVE: yes. Drifted to `feats_index.py:270-271` (`if not hosts: return []`), and
`manifest_builder.py:351-364` still prints its WARNING only from the `except` branch — a clean
return of `[]` says nothing. Two halves, and only one of them is yours.
QUESTION (the owner half): the thirteen genuinely unrecorded sources — bind them, or accept that
they ship without a Feats chapter?
OPTIONS:    (a) bind the thirteen in `WIKI_HOSTS.json` (a data task, one sitting)
(b) leave them; they are small or hostless in practice
RECOMMEND:  **(a) for the data, and reroute the code half.** The `pages:` sentinels (5 of the 18)
are correct by design and should answer "not a wiki source", not "no feats" — that distinction is
what makes (a) safe to act on afterwards.
COST IF WRONG: thirteen volumes build with no Feats chapter and a build report that reads like a
clean run — the smaller-universe-in-the-same-shape failure, at 13/216 of the roll.
UNBLOCKS:   none.
THEME:      evidence semantics
**Reroute the code half to RUN/LOCAL — no ruling needed:** have `manifest_builder` ask
`feats_index.host_to_sources()` for membership before treating `[]` as "no attested feats", and
print the WARNING it already prints for an exception. The remedy is fully specified in the order.

---

### 85cdecef25f8  [OWNER] [MINOR]  — 'weapon property' unmapped in the codex type taxonomy
STILL LIVE: yes. `TYPE_CATEGORY` at `catalogue_codex.py:54-74` maps `rule` and `proficiency` to
POWERS (order ae3bd3847edf, done) but has no `weapon property` key, so its 35 occurrences still fall
through to the THINGS default. `weapon` itself maps to THINGS, which is correct and separate.
QUESTION:   Is a weapon property a THING or a POWER?
OPTIONS:    (a) POWERS, alongside `rule` and `proficiency`
(b) THINGS, alongside `weapon`
RECOMMEND:  **(a).** A weapon property (finesse, versatile, reach) is rules text describing what a
weapon grants, not an object — the same reading that put `rule`, `racial trait` and
`background feature` in POWERS. Ten seconds of your time; add one key.
COST IF WRONG: 35 rules entries filed beside the magic items in every codex volume that carries them.
UNBLOCKS:   none — this is the last of the three unmapped element types.
THEME:      codex taxonomy

---

### 4398d76f822f  [SESSION] [MAJOR]  — repass_bands --apply destroys rejected scale_note text
STILL LIVE: yes. `repass_bands.py:74-76` still reads `e["scale_note"] = ""` with no preservation,
against `pipeline.py:1547-1553` which writes the refused text to `scale_note_rejected` and explains
in the comment above it that the first version of that line blanked 51,611 entries and destroyed
~46,000 candidate feats. The demoted-SOURCE path two loops up (`repass_bands.py:49-57`) is handled
correctly — evidence kept, `demoted_by` written — so only the per-entry path discards.
**REROUTE TO RUN/LOCAL — no ruling needed.** The remedy is fully specified and field-for-field:
set `e["scale_note_rejected"] = sn[:500]` before clearing, matching `pipeline.py:1547-1551`; the
field is already in `MERGED_ENTRY_FIELDS`. The order also flags the one hazard for whoever takes it
(`ENTRY_REJECTION_COMPANIONS` pops a disk-side rejection when the in-memory entry lacks the key, so
the fix must SET the companion rather than leave it absent). No judgment is required at any step.
Worth doing **before** the next `--apply`: this module's whole purpose is re-applying the corrected
gate corpus-wide, so `--apply` is precisely the run that destroys the most evidence in one pass.
THEME:      evidence preservation

---

### 556c1b8fda9f  [SESSION] [MAJOR]  — NTFS hard links bypass the propose_patch denylist
STILL LIVE: yes. `local_agent.py:495` still gates the `_denied_target(rel_real)` interrogation on
`normcase(rel_written) != normcase(rel_real)` — the divergence test — and there is **no** `st_ino`,
`st_dev` or `os.path.samefile` anywhere in the module. `realpath()` returns a hard-linked path
unchanged, so written and real never diverge and the branch never fires.
**REROUTE TO RUN/LOCAL — no ruling needed.** The order specifies the fix exactly: compare file
IDENTITY (`st_ino` + `st_dev`) between the write target and every existing DENYLIST module /
`DENYLIST_PATHS` entry / file under a `DENYLIST_PREFIXES` region, refusing on a match the way the
junction check refuses today. This **hardens** an existing gate rather than weakening one, so it
needs no owner sign-off. Not currently reachable — no tool the local model has creates links, and
nothing in `src/` creates hard links (only `mklink /J` junctions, in `drill.py` and `mutate.py`) —
which is the same "not currently exploitable" condition that was true of bypass classes four and
five before they were closed.
THEME:      patch-gate hardening

---

### 9b3e59aeeb19  [SESSION] [MINOR]  — axis_score returns one None for five different conditions
STILL LIVE: yes, verbatim. `assay.py:221-229`: `if x is None or x <= 0 or band not in BAND_EDGES:
return None`, then `if not lo or not hi or hi <= lo: return None`. Six of the eleven Measures
(transgression, vector, volition, acumen, discernment, suasion) sit permanently in the missing-floor
case, and `anchors.py:37-42` already says so in prose and works around it in a comment.
**REROUTE TO RUN/LOCAL — no ruling needed.** The order prescribes all three branches: keep `None`
for genuinely-unscorable (`x is None`, `x <= 0`); raise `AssayIntegrityError` for
`band not in BAND_EDGES`, since `assay()` already raises `ValueError` for an anchor off the Ladder
and the two doors should agree; and refuse the six non-energetic axes by name, importing
`anchors.NON_ENERGETIC_AXES` (confirmed live at `anchors.py:42`) rather than restating it — checking
the import direction for a cycle first, and hoisting the dict into `assay.py` if it would cycle, the
same move order 6475cb78e185 made for `ATTESTATION_FLOOR`. Nothing here is a curatorial call.
THEME:      error distinguishability

---

### b248f8f706d3  [SESSION] [INFO]  — Hard Rule 0 tripwire fires only after hours of network work
STILL LIVE: yes. `catalogue_web.py:53` still holds `MAX_PER_SOURCE = None`; the guard is still at
`:452-453`, after the whole category-discovery and size-ranking pass at `:346-390`. And
`grep -c MAX_PER_SOURCE` returns **0** in both `src/drill.py` and `src/verify_math.py` — this
runtime raise remains the only enforcement anywhere in the tree.
**REROUTE TO RUN/LOCAL — no ruling needed.** The tripwire is to be **KEPT**; the order says so
explicitly and reading it as a dead branch would be the wrong conclusion. Two mechanical changes:
move the check to module import time immediately after the constant (~:54), where it costs nothing
and fires before a single request; and add a drill net asserting `catalogue_web.MAX_PER_SOURCE is
None`, which gives the guard the PROVEN property Hard Rule -1 asks for. Neither weakens anything.
THEME:      guard placement

---

### 9adb8291c16c  [SESSION] [INFO]  — suppressions.problems() re-walks the whole repo per row
STILL LIVE: yes. `suppressions.py:204-205` still builds `glob.glob(os.path.join(HERE, "**", "*"),
recursive=True)` inside the per-row loop, and `drill.py:2515` still calls `problems()` every cycle.
Both stated mitigations hold: three active suppressions, none with a dotted pattern, and the
dot-blindness fails in the safe direction (over-reports rather than silently covering).
**REROUTE TO RUN/LOCAL — no ruling needed.** Build the listing once before the loop with `os.walk`
(which sees dotted names) and match every wildcard row against it; keep `fnmatchcase`, which is
correct and argued at `:152-160`. Purely mechanical, and it removes a full-repo walk —
`data/records/`, `data/feats/`, `output/`, `.git` — from every drill cycle.
THEME:      detector cost

---

### f90795d5c6bd  [SESSION] [MINOR]  — codewatch.stamp ignores its who argument
STILL LIVE: **NO.** The order's central claim — "never reads its own argument" — is falsified by the
current file. `codewatch.py:354-364` uses `who` three times: it is interpolated into the
`CODEWATCH_NOT_STAMPED` message (`"%s could not fingerprint src/ in %d attempts at startup..." %
(who, STAMP_ATTEMPTS)`), and passed as `evidence={"job": who, ...}` and `source=who` to
`escalation.escalate`. The four callers' job names now reach the one report that matters — the
escalation raised when a daemon comes back unstamped and blind. Nothing owner-shaped remains.
Residual, mechanical, and **reroute to RUN/LOCAL if you want it at all**: `_START["who"] = who` is
still not recorded, so `exit_if_stale` cannot report a "this process stamped as something else"
disagreement, and the second-stamp rebase hazard at `:349-352` is unguarded. One line plus one
comparison. No ruling needed; consider closing this order as superseded.
THEME:      already resolved

---

### 0b1cda11f4a2  [OWNER] [MINOR]  — feats.axis_evidence is dead code duplicating the live gate
STILL LIVE: **NO.** Order 73aacce08418 settled it with a third answer better than either option this
order offered. The three axis-independent gates now have **one** definition —
`feats._axis_independent_gates` at `feats.py:1325-1344` — `by_axis` calls it once per sentence
(`feats.py:1373`, hoist preserved, so the measured 3x regex cost over the 874MB corpus does not come
back), and `axis_evidence` at `:1355-1357` is now a thin wrapper composed of that same predicate
plus the axis check. The duplication that made it dangerous is gone; the function cannot drift from
the live gate because they share the predicate. It carries an explicit REPORTED DEAD, NOT DELETED
marker at `:1346-1352` per house doctrine (order 25ec11447b4c).
Nothing to rule on. Close it — or, if you take the shared "unread public symbol" ruling under
e68664e621bf, note that this is the tree's existing precedent for it.
THEME:      already resolved

---

### d47ea56cca29  [SESSION] [INFO]  — the one unjudged assay mutant is a non-terminating loop
STILL LIVE: **NO — it was never a question.** This order is a finding filed to *remove* work, not to
request a ruling: it establishes that the mutant at `assay.py:1343` (`>` → `<=`) which scored NO
VERDICT under a `verify_math` TIMEOUT was detected as loudly as possible — flipping the comparison
inverts `interval_from_hands`' covering loop into one satisfied by construction, so it widens the
published interval by 0.01 forever (simulated: 200,001 iterations, interval 2000.33, no exit). The
timeout **is** the kill. The live code at that line is correct and now also publishes
`covered_before_widening`, `widening_added` and `quadrature_interval` for a future run to assert on.
Nothing to decide, nothing to fix, no rung above RUN involved. Its only action is on
**23dbbcd656f3** (RUN/MAJOR, still open): that order asks for a dedicated re-run of this one mutant,
which would spend hours reproducing a hang — this removes that item from its scope. Close it.
THEME:      already resolved

---

## Cross-cutting note

Three of the twenty are one question — **e68664e621bf**, **de43fe54feb7** and (retroactively)
**0b1cda11f4a2**, plus **c0384991bfc5** which is open and not in this batch: *what happens to a
public symbol nothing calls?* The tree already answered it once (REPORTED DEAD, NOT DELETED,
`feats.py:1346`). One sentence in CLAUDE.md closes four orders and stops the family being re-filed.

Two more are one condition — **5be28f56946c** and **959b98f38a63** (open, not in this batch): the
crawl out-requests six of the roll's largest hosts, the backoff correctly ratchets, and the
quarantine that is supposed to take over brakes nothing. Rule on the brake and the per-host rate
together, or neither answer works.
