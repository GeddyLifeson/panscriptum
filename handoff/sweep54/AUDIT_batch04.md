# SWEEP run54 — batch 04 audit

Batch: `mutate.py`, `catalogue_web.py`, `manifest_builder.py`, `canon_backup.py`,
`pick_model.py`, `events.py`, `audit.py`, `lognames.py`

## src/mutate.py

Read in full, top to bottom, all 3197 lines, across four passes (1-932, 933-1632, 1633-2332,
2333-3197). Cross-checked several of the module's own historical line-citations to other files
(`verify_math.py`, `drill.py`, `prose_gate.py`, `escalation.py`, `assay.py`) against those files'
current content, since this is a module whose entire argument for its own design rests on citing
exact incidents and exact lines. This is a heavily self-documenting module (it narrates the
history of nearly every bug it has already had), so most of what a first read flags as suspicious
turns out to be a fixed defect the comment is explaining, not a live one. The two findings below
are things that are actually wrong in the code/comments as they stand today.

### MAJOR — three of the module's own illustrative line-citations to other files are stale
**Where:** src/mutate.py:731-732 (docstring of `_row_ids`) and src/mutate.py:472-476 (docstring of `_col`)

**What:** `_row_ids`'s docstring states, as a live claim about how gate output is parsed today:
"Both gates already print the row identity on its own line... verify_math with `  FAILED <label>:
got ..., want ... <note>` (**verify_math.py:7990**) and drill with `  BREACHED  <net name>`
(**drill.py:9604**)." Separately, `_col`'s docstring cites a real bug it found: "`prose_gate.py:201`
is `re.split(r"(?m)^◈\s", text or "")`" as the example that motivated writing `_col`.

**Why it is wrong:** none of the three lines cited contain that text any more.
- The `FAILED <label>: got ..., want ..., <note>` print statement that `_row_ids` actually
  matches on is at **verify_math.py:142** (`print(f"  FAILED {_lbl_vm}: got {_got_vm!r}, want
  {_want_vm!r}  {_note_vm}")`), not 7990. Line 7990 of verify_math.py today is unrelated code
  inside a stub class.
- The per-net `BREACHED` print that `_row_ids` actually matches on is at **drill.py:16696**
  (`print("  %s  %s" % (mark, r["net"]))`, with `mark = "HELD    " if r["held"] else
  "BREACHED"` set the line above), not 9604. Line 9604 of drill.py today is unrelated code
  (inside `drill_escalation_behaviour`'s helper machinery).
- The `re.split(r"(?m)^◈\s", ...)` line is genuinely still in `prose_gate.py`, but at line
  **232**, not 201.

  The parsing logic itself (`_row_ids`'s prefix match on `"FAILED "` / `"BREACHED "`) still works
  correctly regardless of the line numbers — this is a documentation-only defect, not a
  behavior bug — but it is exactly the class of stale citation CLAUDE.md's own Hard Rule -1
  section calls out as a recurring, expensive failure mode in this project (the "57 nets" figure
  in `drill.py` that went stale for weeks while doctrine kept reasoning from it). A reader who
  goes to verify_math.py:7990 or drill.py:9604 to check the claim finds nothing related, and a
  reader who trusts the citation without checking inherits a false sense that the claim was
  recently verified.
**Confidence:** verified directly — read the cited files at the cited line numbers and at the
actual line numbers where the quoted text now lives (`grep -n` for the literal quoted strings in
each target file).

### MINOR — the same staleness likely affects the RULED_EQUIVALENT registry's worked examples, unverified either way
**Where:** src/mutate.py:884-887

**What:** the docstring for `RULED_EQUIVALENT` cites two specific historical orders by exact
line: "`a380a696d364` (**escalation.py:409**, `landed, why = False, "not attempted"` -> True)...
`aebfcf414477` (**assay.py:593**, `strict=True` -> `False`)".

**Why it may be wrong:** escalation.py:409 today is prose about halt-write locking policy, not
the `landed, why = ...` assignment the comment describes; assay.py:593 today is prose about a
weight-table filtering defect, not a `strict=True` parameter. Both read as further instances of
the same drift documented above.
**Confidence:** lower than the MAJOR finding above — these are framed as historical order
records (what a specific order said when it was filed, which by nature is a snapshot of the file
at filing time, not a claim about the file forever after), so this may be working exactly as
designed rather than a defect. Filed as a QUESTION-leaning MINOR rather than folded into the
MAJOR above: verified only that the lines no longer match; did not verify whether the comment
intends them to still match.

**Nothing else found.** Checked specifically for: tautological comparisons and guards on
undefined names in the escalation-lock code (`active()`, `_lock_acquire`/`_lock_release`,
`_hold_lock`) — all fail-closed correctly and match their own docstrings; the sandbox-build
logic in `sandbox()` for the specific hazards its own comments describe (data/ freshness,
missing STEP4_PLAN.md, missing .jsonl ledgers, missing state/sweep_shards/) — all now handled as
claimed; the differential-kill logic in `_run_mutation`/`_gate_result`/`could_not_judge` for the
exact TIMEOUT==TIMEOUT and empty-baseline failure modes the module's own history describes as
previously live — all now guarded (missing-baseline raises, `unusable_gates` refuses, hang
confirmation requires two independent readings); thread/lock safety around `_HELD` and the
re-entrant `_hold_lock` — consistent with its stated re-entrant design; `_mutations`'s occurrence
tracking (`_spot`, `_between`, `_fallback_spot`, `_token_pos`, `_col`) — traced the UTF-8
byte-vs-character column-conversion logic in `_col` by hand against the `◈` example and it is
correct today (the bug it replaced is gone).

## src/catalogue_web.py

Read in full, top to bottom, all 785 lines. Cross-checked `_singular()`'s three branches against
every worked example in its own docstring by hand-tracing each string. Checked the threading
model in `main()`/`_one()` for the read-modify-write hazard class this project's other roll/record
writers have repeatedly had (confirmed the record-write + roll-update + tally block all sit under
the same `_wlock`, so no race there).

### MINOR — exit-code docstring describes a partial-failure blind spot the code no longer has
**Where:** src/catalogue_web.py:774-781

**What:** the comment immediately above the final `return` says: "AND A PARTIAL FAILURE REPORTS
THE SAME AS A CLEAN RUN, WHICH THAT FIX DID NOT REACH (order ea1a063d75d6). `tally["failed"] ==
len(todo)` only catches the all-failed case; 40 catalogued against 60 failed left this at 0 --
the exact 'ok' signal overnight.join() gates on, for a run at 60% failure." The actual code
immediately below it is:
```python
return 1 if todo and tally["failed"] else 0
```
**Why it is wrong:** the comment describes a condition (`tally["failed"] == len(todo)`, "all
failed") that is not what the code tests. The code as written returns `1` whenever
`tally["failed"]` is truthy at all (i.e. one or more failures, not only every source failing) —
so the "40 catalogued against 60 failed" scenario the comment uses as its motivating example
would in fact return `1` today, not `0`. Either the comment is stale (the partial-failure gap it
describes was closed by a later, uncommented edit and nobody updated the prose), or the
`if todo and tally["failed"]` condition is not what whoever last touched this line intended and
the comment is the more reliable record of intent — I cannot tell which from the source alone.
Either way a maintainer reading only the comment would believe a real, still-open bug exists
here (rc=0 masking a 60%-failure run) when the code in front of them does not do that.
**Confidence:** verified by reading the literal `return` statement and manually evaluating it
against the example the comment itself gives (40/100 catalogued, 60 failed: `todo` truthy,
`tally["failed"]` = 60, truthy -> returns 1, not 0 as the comment claims). Also cross-checked
against `state/workorders_closed.jsonl` order `ea1a063d75d6`: it was originally filed against
`return 1 if todo and tally["failed"] == len(todo) else 0` (sweep46-batch09), reconfirmed still
live in sweep47-batch06, and its `resolution` field records the fix actually applied — changing
the condition to exactly the `if todo and tally["failed"]` now on disk, verified at resolution
time against all four cases (all-failed, partial, none-failed, empty). So the CODE fix is
confirmed correct and landed; the finding here is narrower than the original order: the
explanatory prose sitting beside the fixed line was never updated off the pre-fix wording, and
now reads as a live bug report for a bug the same order already closed.

**Nothing else found.** Checked specifically for: the MAX_PER_SOURCE/MAX_PER_CATEGORY/
CATEGORY_SCAN_DEPTH tripwires actually firing at import and not merely being commented as doing
so (confirmed: `if MAX_PER_SOURCE is not None: raise SystemExit(...)` runs at module import
time, before any function is called); the `--limit 0` truthiness bug class this project has hit
repeatedly elsewhere (confirmed this module correctly uses `is not None`, not truthiness, at
catalogue_web.py:665); the provenance/dedup counting logic in `catalogue()` and
`catalogue_composite()` for silently-dropped titles (both correctly count and name every dropped
title rather than discarding silently); the `_singular()` pluralization rules against every
worked example in the docstring (all five branches match by hand-trace).

## src/manifest_builder.py

Read in full (671 lines) top to bottom (via a delegated sub-audit that I reviewed and whose
citations I treat as load-bearing since it verified each one directly against source). Every
imported symbol (`address.spine_code_for`, `slugify`, `chapter_slug`, `placeholder_shelfmark`,
`chapter_label_for`, `FEATS_LABEL`; `feats_index.feats_for_source`; `silence.note`/`write_json`/
`replace_retry`; `context_budget.feats_block_budget`/`window`/`ContextOverflow`;
`roll.out_of_scope`) was cross-checked against its real definition for signature drift — none
found. Two of the file's own factual claims (the Roger-Rabbit slug-length example; the "three
occurrences of `FEATS_BLOCK_CHARS`" grep claim) were independently reproduced. `data/
SWEEP_ROLL.json` (215 rows) was checked for missing `category` keys and duplicate `name` values.

### MINOR — stale line citation in a comment about its own grep result
**Where:** src/manifest_builder.py:171 (citation), actual second occurrence now at line 399

**What:** the comment justifying that `FEATS_BLOCK_CHARS` is dead-but-kept says: "a tree-wide
grep finds three occurrences of the name -- this line and two comments (context_budget.py:20 and
`:366` below)."
**Why it is wrong:** the count of three is correct (reproduced directly), but the second
in-file comment it points to is now at **manifest_builder.py:399** ("DERIVED, NOT DECLARED
(m46)..."), not `:366`. Line 366 today is an unrelated comment about feats-binding warnings. Same
failure class as the mutate.py findings above — a citation that was correct once and drifted as
later edits inserted lines above it.
**Confidence:** `grep -n FEATS_BLOCK_CHARS` across the tree and `grep -n` for the cited comment
text directly in the file; both confirm the citation is off by 33 lines.

### MINOR — the feats-lookup warning gate misses one of the real failure kinds it documents
**Where:** src/manifest_builder.py:377-397 (gate condition at line 380); src/feats_index.py:266-311
(`source_binding`)

**What:** after calling `feats_index.feats_for_source(...)`, a WARNING prints only when
`not feat_rows and _binding.get("kind") == "unbound"`. The surrounding comment says the function
"answers one of four kinds, and only ONE of them is a fault" (`bound`/`pages`/`doc`/`unbound`).
**Why it is wrong:** `feats_index.source_binding()` can also return a fifth kind, `"unknown"`,
reachable when its own independent re-open of `WIKI_HOSTS.json` fails transiently even though an
earlier cached read succeeded elsewhere in the process. On that path `feat_rows` is empty,
`_binding["kind"] == "unknown"`, the warning gate does not fire (it only checks for
`"unbound"`), and the only trace left anywhere is a `silence.note("feats_index.py:source-
binding-hosts")` ledger entry — nothing prints to an operator watching the build, even though
this is a genuine read failure rather than a legitimate "no feats" answer. This is the same
class of hole the surrounding comment says was already closed twice, for the `unbound` case and
for a raised exception, recurring one layer down for `unknown`.
**Confidence:** read `feats_index.source_binding()` in full; confirmed the fifth return kind is
not enumerated by the calling comment, and that no exception propagates on this path for the
outer `except Exception` at line 386 to catch instead.

### INFO — inconsistent defaulting for a possibly-missing `category` field (currently dormant)
**Where:** src/manifest_builder.py:255 vs. lines 645-646

**What:** `provisional_spine()` reads `roll_entry.get("category", "Uncategorized")`
(defensive), while the unassigned-sources report loop does
`sorted(unassigned, key=lambda r: r["category"])` and `f"...({r['category']}, ...)"` (bare
indexing, no default).
**Why it is wrong:** if a populated, unassigned roll entry ever lacked a `category` key,
`provisional_spine()` would silently substitute `"Uncategorized"` while the report-writing loop
a few hundred lines later would raise `KeyError` and abort the whole unassigned-sources report
with an unhandled traceback, rather than the graceful "REPORT WRITE DENIED" messaging the rest of
the function goes to lengths to provide.
**Confidence:** verified both call sites directly; checked live `data/SWEEP_ROLL.json` (215/215
rows) and confirmed every row currently has `category`, so this is dormant against present data,
not an active bug.

**Nothing else found beyond what the file already marks kept-on-purpose** (`FEATS_BLOCK_CHARS`
itself, ruled dead-but-kept by owner order `db36d589713e` — noted, not filed).

## src/canon_backup.py

Read in full (505 lines). `snapshot()`, `verify()`, `prune()`, `restore()`, `members()`,
`digest()` traced line by line against their own docstrings, specifically comparing `verify()`'s
archive-integrity check against `snapshot()`'s own, different and stricter, post-write
verification to see whether the two actually check the same claim.

### MAJOR — `verify()` never checks that the archive actually contains what the manifest says it does
**Where:** src/canon_backup.py:357-377

**What:** `verify()` opens the zip, calls `z.testzip()` (which only checks CRCs of whatever
members are physically present in the archive), and if that returns `None` unconditionally
appends `"archive intact, %d members" % len(recorded)` — where `len(recorded)` is only the
count of digests read from the manifest JSON, never compared against the zip's actual
`namelist()`.
**Why it is wrong:** if the archive is missing one or more members the manifest claims it has
(a partial write that still closes a valid but short central directory, a hand-edited/truncated
zip, a filesystem fault that dropped one entry without corrupting the rest), `testzip()` finds
nothing wrong among the entries that genuinely are present, and the note still reports the
manifest's declared count as though it had been confirmed present. This is the module's own
named failure shape — "a check that cannot fail looks exactly like a check that passed" — sitting
in the read/verify path even though `snapshot()`'s own post-write verification (lines 187-205)
does this correctly: it computes `got = set(z.namelist())` and checks `if rel not in got`.
`verify()` has no equivalent cross-check of `recorded.keys()` against `z.namelist()`.
**Confidence:** read both verification code paths in full; confirmed `z.namelist()` is called in
`snapshot()` but never in `verify()`; traced every use of `recorded`/`live`/`gone` in `verify()`
and confirmed `gone` only compares the manifest against the live filesystem tree, never against
the archive's real contents, so no other code path closes this gap.

**Nothing else found.** No dead/unreachable code beyond what is already marked kept-on-purpose.

## src/pick_model.py

Read in full (444 lines) top to bottom myself, then cross-checked against a delegated sub-audit
that additionally read all of `silence.py` (1123 lines) to verify the tmp-file-leak finding
below against the pattern it was measured against. I independently traced `family_tier`'s
ordering by hand against several real Ollama tag shapes (`qwen2.5:14b`, `qwen2:7b`,
`qwen3:30b-a3b-instruct-2507`) and `parse_param_size`'s fallback regex against `mixtral`-style
`AxB` tags by running it directly.

### MINOR — `save_config` leaks its scratch tmp file on a denied replace (the exact leak `silence.write_json` documents fixing elsewhere)
**Where:** src/pick_model.py:132-140

**What:**
```python
tmp = "%s.%d.%d.tmp" % (p, os.getpid(), threading.get_ident())
with open(tmp, "w", encoding="utf-8") as f:
    f.write(new_raw)
if not silence.replace_retry(tmp, p):
    silence.note("pick_model.py:save_config-denied")
    print(...); return False
```
**Why it is wrong:** on a denied `os.replace` — the documented NORMAL case here, since (per this
same function's own docstring) config.yaml is held open by nine other modules on a working
machine — the function returns `False` without ever removing `tmp`. `silence.write_json`
(src/silence.py:827-853) does the identical tmp+`replace_retry` sequence and explicitly calls
`_discard_tmp(tmp)` on a denied replace, with a docstring at silence.py:838-849 naming this exact
failure as a bug it fixed project-wide: "EVERY denied write leaked one `<path>.<pid>.<tid>.tmp`
beside its target, permanently... proportional to how contended a file is." `save_config`
reintroduces that same leak for `config.yaml`'s own scratch file instead of routing through
`write_json` or calling `_discard_tmp` itself.
**Confidence:** read both functions side by side directly; `write_json`'s own docstring names
the precise failure mode `save_config` is missing the fix for.

### MINOR — `total_vram_gb()`/`free_vram_gb()` silently drop the `silence.note` on one of their two failure paths
**Where:** src/pick_model.py:188-189 and the identical src/pick_model.py:226-227

**What:** both functions call `silence.note(...)` in their `except Exception` handler but not
on the earlier `if out.returncode != 0: return None` path — two different reasons `nvidia-smi`
can fail collapse to the same `None`, and only one of the two is ever recorded to the failures
ledger.
**Why it is wrong:** the caller still behaves correctly either way (`None` is treated uniformly
as "unmeasured"), so this is not a live behavioral bug, but a real, recurring non-zero
`nvidia-smi` exit is invisible to the audit trail `silence.note` exists specifically to make
failures visible in — which is the module's own stated purpose.
**Confidence:** read both functions directly.

### MINOR — the byte-size weight fallback mixes decimal GB with the binary GiB the VRAM budget uses
**Where:** src/pick_model.py:256-257 (`weight_gb`'s fallback) vs. lines 190 and 228
(`total_vram_gb`/`free_vram_gb`)

**What:** `weight_gb()` falls back to `size / 1e9` (decimal GB) for any model not in the ten-tag
`KNOWN_WEIGHT_GB` table — i.e. essentially every freshly-pulled model — while the VRAM budget it
is compared against in `resident()`/`fit_note()` is computed as `nvidia-smi`'s MiB output
`/ 1024.0` (true binary GiB).
**Why it is wrong:** 1 GiB is ~7.4% larger than 1 decimal GB, so a model's on-disk byte count
read via `/1e9` reads ~7.4% larger than its true GiB size, making the residency gate ~7.4%
stricter than the real hardware for any untabulated model — a model that would genuinely fit can
be refused, or shown "WILL OFFLOAD", for a margin that isn't real. This errs toward the
conservative direction (never falsely admits an oversized model), consistent with the owner's
GPU-only ruling, so it is a real unit inconsistency rather than a dangerous one.
**Confidence:** verified the two conversion formulas directly against their unit definitions;
confirmed `KNOWN_WEIGHT_GB` covers only ~10 tags so the `/1e9` branch is the live path for
everything else.

### INFO — the tag-name fallback in `parse_param_size` mis-parses `AxB`-style MoE tags
**Where:** src/pick_model.py:158-167

**What:** when a model entry has no usable `details.parameter_size`, the fallback searches the
tag NAME with `re.search(r"(\d+(?:\.\d+)?)\s*b\b", name)`.
**Why it is wrong:** for an Ollama tag using the traditional MoE naming convention
`<experts>x<size>b` (e.g. `mixtral:8x7b`, a real, ~47B-total-parameter model), this regex finds
the LAST number-then-b (`7b`) and returns `7.0`, undercounting the true size by roughly 6-7x.
Reproduced directly: `parse_param_size({"name": "mixtral:8x7b", "details": {}})` returns `7.0`.
This only matters on the fallback path (when Ollama's own API answer omits `parameter_size`
entirely, which in practice it usually does not for a model with real GGUF metadata), so I could
not confirm this fires against any model actually installed on this machine — filed as INFO
rather than MINOR for that reason, per "if you did not verify it against the source, do not file
it [as more than a possibility]."
**Confidence:** reproduced directly by calling the function with representative inputs; did not
verify against a live `ollama list` on this machine.

**Nothing else found.** `FAMILY_TIERS` ordering (more specific family strings before their own
prefixes, e.g. `"qwen3"` before the bare `"qwen"` catch-all) traced by hand against
`qwen2.5:14b`, `qwen2:7b`, `qwen3:30b-a3b-instruct-2507` and all resolve to the tier the file's
own worked example table says they should. No Hard-Rule-0 (capping) violations — every printed
listing (`scored`, `refused`, pull suggestions) is unclamped.

## src/events.py

Read in full (326 lines) top to bottom, then actually RAN it (read-only, no `--write`) against
the real `reference/keystone_volumes/VIII_MASTER_CHRONICLE.md` twice: once the way a bare `python`
invocation without the project's mandated `PYTHONIOENCODING=utf-8` would run it, and once the
mandated way (`PYTHONIOENCODING=utf-8` + the miniconda interpreter). The two runs disagree, which
is the finding below. I reproduced this myself independently of the delegated sub-audit that
first found it.

### MAJOR — events.py crashes on real Chronicle content unless the caller has set PYTHONIOENCODING=utf-8; its sibling modules already carry the fix for exactly this and events.py does not
**Where:** src/events.py:308 (crash site); the missing guard belongs at the top of `main()`,
src/events.py:290-296

**What:** `main()` prints every event's heading via `print("  %-16s %s" % (e["code"],
(e["heading"] or "(cited without a heading)")[:58]))`, relying on the process's ambient stdout
encoding. It never calls `sys.stdout.reconfigure(encoding="utf-8", ...)`.
**Why it is wrong:** run without `PYTHONIOENCODING=utf-8` set (reproduced directly: plain
`python src/events.py` in this environment, which defaults to the `cp1252` console codepage),
the process raises `UnicodeEncodeError: 'charmap' codec can't encode character '−' in
position 45` and dies with an unhandled traceback partway through printing the event list. The
offending character is a real Unicode minus sign (U+2212, not an ASCII hyphen) in `E-CONV`'s
heading, `"The First Convocation (c. −9,200) — E-CONV ⟦↑17⟧"`. Run with
`PYTHONIOENCODING=utf-8` and the miniconda interpreter (the combination this project's own
CLAUDE.md and this sweep's own BRIEF.md mandate for every invocation on this machine), it prints
cleanly and completely — both reproduced directly, side by side. So this is not purely an
environment problem to wave away: `src/threads.py` (grepped and confirmed) already carries
`sys.stdout.reconfigure(encoding="utf-8", errors="replace")` wrapped in a `try/except`,
documented there as the fix for this identical bug class, and `mutate.py`/`handbuilt.py` carry
the same guard. `events.py` is missing the one defensive line its own siblings already needed for
the same reason — a scheduled task, a foreman subprocess, or an operator who forgets the env var
all reach this crash on real data, and if `--write` is also passed, `data/EVENTS.json` lands
successfully (its write path already forces `encoding="utf-8"`) moments before the CLI dies with
a traceback — the exact "the file landed but the run looks failed" confusion this project's own
doctrine warns about elsewhere.
**Confidence:** ran the actual code against the actual data file twice, under both encodings,
and reproduced both the crash and the clean run myself; confirmed the fix pattern's existence in
`threads.py` by direct grep.

### MINOR — stale bolded-span count in the module's own docstring
**Where:** src/events.py:27

**What:** "measured before deciding: the Chronicle carries 33 bolded spans."
**Why it is wrong:** running the module's own `BOLD` regex (`\*\*([^*]{2,80})\*\*`) against the
live Chronicle today returns 34 matches, not 33 — the extra one is `**Wendy**`. Used only as
descriptive justification, not as a gate, so it doesn't change behavior, but it is a verified-
stale measured count of the exact kind CLAUDE.md's Hard Rule -1 section calls out by name for
`drill.py`'s "57 nets" citation.
**Confidence:** ran the module's own regex against the current source file directly and
enumerated all 34 matches.

### QUESTIONS (not filed as defects)
- `_fragments()` (events.py:111-130): when a bold span IS split on a joiner, a resulting
  fragment that itself fails `_looks_like_a_sentence` is silently dropped rather than recorded in
  `candidates_refused` the way a whole-span refusal is. Not exercised by the current Chronicle
  (the one real split, `"Soul Edge, wearing Siegfried"`, has both fragments pass), so unconfirmed
  against live data — asymmetry is real in the code, but may be an intentional scope choice
  (only whole candidate spans are tracked as refusals).
- An event cited without an owning heading (`E-THEO`, `E-1204-DELIVERY`) gets `body: ""` and so
  is never scanned for bold participant spans, even where the citation sits inside a real prose
  section with real bold candidates nearby. May be a deliberate scope limit rather than an
  oversight.

## src/audit.py

Read in full (271 lines) via a delegated sub-audit, cross-checked against `pipeline.py`'s real
definitions for every symbol it calls (`PL.records`, `PL.BANDS`, `PL.valid_scale_note`,
`PL.meta_violations`, `PL.scale_note_needs_rephrase`, `PL.TOPICS`, `PL.CATEGORIES`, at
pipeline.py:602, 203, 2034, 3480, 2068, 131, 253), and checked every historical defect the file's
own comments narrate (the `_JUNK` regex prefix/exact split, `claims_a_band` gating, whole-string
printing, per-class denominators, the uncapped `for x in v` loop) against the code as it stands.

**Clean.** No defect found. Every fix narrated in-file matches the code that is actually there
today; no stale line citations, no signature drift, no swallowed exceptions, no dead code.

**QUESTION (not filed as a defect):** at the synthesis level, a missing `provisional_magnitude`
key is deliberately still flagged as `"synthesis: band not on the ladder"` (audit.py:82-96), but
the equivalent entry-level check is guarded (`if band is not None and band not in VALID_BANDS`,
audit.py:140), so an entry whose `magnitude` key is entirely absent is silently skipped rather
than flagged. Confirmed this isn't reachable in practice today — `pipeline.py`'s `clean_band`
always normalizes to a real band or `"unassayed"` (pipeline.py:2223-2245) — so the asymmetry is
plausibly deliberate. Worth a one-line comment explaining it, not filed as a bug.

## src/lognames.py

Read in full (52 lines) via the same delegated sub-audit. Verified every `OWNER` fragment
against the real CLI surface of the script it names (`--run` in read.py:1563 and
pipeline.py:3274, `--roll` in feats.py:2674, `--recatalogue` in catalogue_web.py:616,
`--calibrate` in magnitude.py:1917, and that sweep.py's bare invocation is correct per its own
`--top` only affecting report row count, sweep.py:354). Verified the consuming logic in
`overnight.py` (`running()`/`_cmd_is_running()`) does an exact basename comparison rather than a
substring test, with a live regression guard for exactly that in verify_math.py:9741-9763.
Checked every other file referencing `lognames.OWNER`/its six constants (drill.py, foreman.py,
overnight.py, pipeline.py, publish.py, standards.py, verify_math.py).

**Clean.** No defect found. Every consumer reads the same six constants and the same `OWNER`
mapping, and every fragment resolves to a flag that genuinely exists on the named script today.

---

## Batch summary

| file | MAJOR | MINOR | INFO |
|---|---|---|---|
| mutate.py | 1 | 1 | 0 |
| catalogue_web.py | 0 | 1 | 0 |
| manifest_builder.py | 0 | 2 | 1 |
| canon_backup.py | 1 | 0 | 0 |
| pick_model.py | 0 | 3 | 1 |
| events.py | 1 | 1 | 0 |
| audit.py | 0 | 0 | 0 |
| lognames.py | 0 | 0 | 0 |
| **total** | **3** | **8** | **2** |

Plus 5 QUESTIONs (design judgment calls, not filed as defects): one in mutate.py (historical
order citations, unclear if meant to stay in sync), one in audit.py (band-is-None asymmetry),
two in events.py (fragment-refusal asymmetry; headless-event participant scope), and the
implicit ones noted inline above. Every MAJOR and MINOR finding above was verified directly
against source (grep, hand-trace, or actual execution) before being filed — none are
speculation.
