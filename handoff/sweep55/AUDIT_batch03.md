# AUDIT — run55, batch 03

Modules: `pipeline.py`, `identity.py`, `feats_index.py`, `cleanup.py`, `snapshot.py`, `roll.py`,
`scale_theories.py`, `module_index.py` — 6,364 lines, every line read.

Read-only. Nothing under `src/`, `data/`, `state/` or any ledger was edited, and no module in
this batch was executed. Verification was by reading the source, by `grep` over `src/` for
call sites and readers, and by `sed -n` on the exact lines a comment cites.

---

## pipeline.py (3,493 lines)

Read end to end in eight passes. Checked specifically for: gates whose condition cannot fail;
the two-writer record contract in both directions; every `except` that turns a failure into a
plausible empty result; whether each phase's return value actually reaches `gate_done`; whether
every field the model is asked for reaches a record; and whether the in-file line citations
still point where they say.

### MAJOR — `physiology` is asked for, paid for on every call, and reaches no record
**Where:** `src/pipeline.py:1805-1810` (prompt), `:1901`, `:1907-1908` (schema), and the result
loop at `:2191-2274`.

**What:** `ENTRY_SYSTEM` instructs the model to return a `physiology` clause for every category-8
entry. `ENTRY_SCHEMA` declares `"physiology": {"type": "string"}` and lists it in `required`, so
Ollama's constrained generation emits it on every result object of every entrypass batch. The
result walk at `:2191-2274` reads `index`, `category`, `scale_note`, `magnitude`, `topic` and
`subroom` and **never reads `res.get("physiology")`**. It is not written to `batch[i]`, and
`physiology` is not in `MERGED_ENTRY_FIELDS` (`:690-695`), so even a value written by some other
path could not survive `write_record`'s per-entry fold.

**Why it is wrong:** the field is computed and dropped on the floor. `grep -rn physiology src/`
returns four hits, all inside this file, all inside the prompt string and the schema — no
consumer, no drill net, no `verify_math` check, nothing in `data/records`. Concretely: the model
is paid for output tokens describing what a people is made of, on every one of ~14,000 batches,
and the answer is discarded at the moment of receipt. The schema comment at `:1890-1900` states
the reason the field is `required` with an explicit `""`: *"A physiology nobody recorded and one
that does not apply must be distinguishable, and only an always-present field can do that."*
Neither is recorded; both are equally absent from disk. Order `6c7495ee66be` commissioned the
field alongside the `Peoples & Species` category, and the category half landed (`:275`,
`:2202-2203`) while this half did not.

**Confidence:** high. Read the whole result loop line by line and grepped the tree for any other
reader.

### MAJOR — `save_state` is a whole-object dump from a snapshot taken at process start, so it silently reverts `health.reopen_stranded`
**Where:** `src/pipeline.py:304-335` (`load_state` / `save_state`), the single `load_state()`
call at `:3295`, and the eight `save_state(st)` sites — in particular `:2320`, inside
`phase_entrypass`'s per-batch loop.

**What:** `main()` calls `load_state()` exactly once (verified by grep: the only other
`load_state` references in `src/` are drill stand-ins). `st` is then held in memory for the whole
run — days, for phase 2 — and `save_state(st)` `json.dump`s that whole object over
`PIPELINE_STATE.json` after every unit.

**Why it is wrong:** any concurrent modification of that file is a lost update. The concrete
other writer is `health.reopen_stranded` (`src/health.py:1010-1156`), which removes stranded
batch keys from `st["done"]["entrypass"]` and lands the result at `health.py:1150`.
`health.py` guards **its own** write with a read-and-compare-and-swap (`:1118-1134`) — it refuses
if the file moved while it was computing. Nothing guards it in the other direction: once
`health` lands, the pipeline's *next* `save_state` writes the load-time `done` list back over it.
In `phase_entrypass` that next save is at `:2320`, after every batch — seconds away. So the
documented recovery action (`health --reopen --go`) prints `-> PIPELINE_STATE.json`, returns the
list of reopened keys, and is undone before the next batch finishes, with no signal on either
side. The reopened entries stay stranded and the operator has been told they were freed.

The asymmetry is the finding: `write_record` was given a whole watermark mechanism
(`_TOP_SNAPSHOT`, `:617-667`, and `_merge_top_keys`'s `snapshot` arm, `:1142-1174`) for exactly
this hazard on `data/records/*.json`, under order `a4b5ffc46f95`, because a long-lived in-memory
copy re-stamping load-time values over a concurrently-refreshed disk copy is *"the project's
signature defect"*. `save_state` writes a shared file with a second known read-modify-write
writer and got only rename-denial reporting (`:311-335`) — which covers the case where the write
does **not** land, and says nothing about the case where it lands and clobbers.

**Confidence:** high on the mechanism (read both writers; confirmed `load_state` has exactly one
non-stand-in call site). I did not run the race — the brief forbids executing anything that
writes `state/`.

### MINOR — `subroom_rejected` is the one stored, bounded field that bypasses `_stored_cut`
**Where:** `src/pipeline.py:2273` — `batch[i]["subroom_rejected"] = sub[:120]`.

**What:** every other rejected/stored field in this file is cut through `_stored_cut`, which
appends `"... (+N chars)"` when a cut actually happened: `evidence` (`:1748`), `rationale`
(`:1749`), `scale_note` (`:2213`), `scale_note_rejected` (`:2215`), `topic_rejected` (`:2262`).
Five sites — exactly the "five fields (order `19c507a16430`)" `_stored_cut`'s own docstring names
at `:237-250`. `subroom_rejected` is a sixth field of the same kind, written into
`data/records/*.json` and carried by `MERGED_ENTRY_FIELDS` (`:691`), and it is cut with a bare
slice.

**Why it is wrong:** the docstring's stated reason applies verbatim — a value cut at the bound
"reads as a COMPLETE value with nothing distinguishing it from one that simply ended there."
Its twin one line up (`topic_rejected`, `:2262`) is bounded at the same 120 and marks itself.
Low blast radius today (a rejected subroom is a short label), which is why it is MINOR rather
than MAJOR, but it is the shape the idiom exists to forbid.

**Confidence:** high; grepped all `_stored_cut(` sites and read the docstring against them.

### MINOR — four in-file line citations, in the two comment blocks that govern the merge fields, all point somewhere else
**Where:** `src/pipeline.py:621` (`:1576`), `:712` (`:1718`), `:713` (`:1707`), `:715` (`:554`).

**What, checked with `sed -n` against the live file:**

| citation | what the comment claims is there | what is actually there | real site |
|---|---|---|---|
| `:1576` | ``phase_entrypass`` calls ``records()`` ONCE | `return s[:limit].rstrip() + ...` (inside `_budgeted`) | `:2116` |
| `:1718` | pops `subroom_rejected` when `subroom_ok` passes | `for ci, sample in enumerate(chunks):` (phase 1) | `:2269` |
| `:1707` | pops `topic_rejected` | `# their feat text with them.` (a comment fragment) | `:2258` |
| `:554` | `subroom_rejected` declared in `MERGED_ENTRY_FIELDS` | `"keep_alive": -1,` (inside `ask()`) | `:691` |

**Why it is wrong:** these two blocks are the ones a future reader consults before touching the
per-entry fold, and all four pointers now land in unrelated code — one of them in the middle of a
comment, the shape `identity.py:592-595` records as having previously asserted something false.
The same file already carries the ruling against this: `:688-689` cites order `7716ac4884cc`
("cited by name rather than line per order `7716ac4884cc` -- a line number here has already gone
stale twice") and the next comment block down does it four more times. The conclusions still
hold; the evidence offered for them does not.

**Confidence:** high; each of the four verified by reading the cited line.

### INFO — `st["failed"]` and `st["done"]` are subscripted directly on a dict that comes off disk unvalidated
**Where:** `:1674`, `:1739`, `:1766`, `:2115`, `:2187`, `:2311` (direct subscript) against
`:3415`, `:3425`, `:1777`, `:2290` (`setdefault` / `get`).

**What:** `load_state` (`:304-308`) returns the parsed file as-is and only supplies
`{"phase", "done", "failed", "started", "units_done"}` when the file is absent. A
`PIPELINE_STATE.json` missing either key raises `KeyError` on the first unit of phase 1 or 2.
Not reachable from any writer in the tree today (both `save_state` and `health.py` preserve the
keys), so this is robustness rather than a live defect — but the file is hand-editable and
`--phase N` is the documented recovery action.

### INFO — phase 6's "median" is the upper-middle element
**Where:** `:2796` — `sorted(known)[len(known) // 2]`, printed as `median %.0f yr`.
For an even-length list this is the upper of the two central values, not their mean. Reporting
only; nothing consumes it.

### QUESTION — `_now_rank > _at_rank` can raise on a `None` left operand
**Where:** `:2915-2917`.
`AD.tier_rank(now)` and `AD.tier_rank(at_code)` are compared as
`(_at_rank is None or _now_rank > _at_rank)`. The `or` short-circuits a `None` **right** operand;
a `None` **left** operand (`_now_rank`) reaches `None > int` and raises. The comment at
`:2910-2914` asserts this cannot happen because "`AD.promote` only ever returns a real tier".
`src/address.py` is **outside this batch**, so I did not verify that assertion — flagging it for
the coordinator rather than guessing.

### Citations pointing outside this batch, not verified
Stated explicitly per the brief rather than dropped: `cascade_bridge.py:18` (`:457`),
`catalogue_web.py:244-246` and `:456-458` (`:732`), `overnight.py:911,1600,1650-1651` (`:3431`),
`onomast.py:569-573`, `reference.py:363-373`, `genre.py:327-331`, `sevenfold.py:412-415`,
`wh40k.py:289-293` (`:3435-3436`), `overnight.py:602-660` (`:3451`).

---

## identity.py (752 lines)

Read whole. Checked for: a continuity test that is always true or always false; an `except` that
turns a transport failure into an honest-looking negative; whether the stale-cache repair can
cache its own failure; and whether `split()` survives nested parentheticals.

**Clean on all four.** Specifically verified:

* `_is_continuity` (`:228-244`) — the three arms are genuinely reachable and none is vacuous.
  The `n == 2` case falls to `shared >= (n // 2) + 1 == 2`, which is the strict majority the
  comment claims; the `n == 1` case is handled separately as documented; `n == 0` is
  unconstructible because `mine()` only creates a key by adding a bearer.
* `epoch_of` (`:566-621`) — the distinction it was written for actually holds. An honest model
  answer `{"epoch": "", "explicit": false}` is a **non-empty** dict, so `if not d:` is False and
  the function reaches `if not d.get("explicit"): return ""`; only `raw is None` or an unparseable
  reply reaches the `ProbeUnavailable` arm. The two cases are genuinely separable.
* `load()` (`:309-434`) — every arm notes and prints, the empty-over-populated guard is applied,
  and the `except` on the fast-path read falls through to a full re-mine rather than returning a
  cached emptiness.

### INFO — a vestigial empty format slot
**Where:** `:355-365`. The format string carries five `%s`/`%d` specifiers and the argument tuple
supplies five, the last being a literal `""` that renders nothing. Harmless; reads like a leftover
from the `SA._cut` port under order `1cdc2f8cd2f3`.

### INFO — `continuities()` cannot distinguish "mined, nothing found" from "never mined" when choosing a key
**Where:** `:474-477` — `for k in _inv_keys(host): if inv.get(k): counts = inv[k]; break`.
`mine()`'s comment at `:189-196` deliberately gives a visited directory a key with an **empty
dict**, precisely so "mined, nothing found" and "never mined" stay different facts. The truthiness
test here collapses them again for key selection: a host whose current `cachekey` spelling was
mined to `{}` falls through to the legacy `host` / `hand` spellings. The returned value is `{}`
either way today, so nothing is currently wrong; the exposure is a stale non-empty entry under an
old spelling winning over a fresh mined-empty one.

---

## feats_index.py (573 lines)

Read whole. Checked for: a join whose empty answer is indistinguishable from a real negative
(the module's own stated theme), whether every counted fault reaches a printer, and whether the
caching keyed by path actually is.

### MINOR — `_ENTRY_COLLISIONS` is written and has no reader and no accessor
**Where:** declared `:110`, written `:392`.
`grep -rn _ENTRY_COLLISIONS src/` returns exactly two hits, both in this file. Its sibling
`_UNBOUND_ASKED` (`:265`) has `unbound_asked()` (`:315-322`) and is read by the manifest build;
this one has nothing. Its own comment at `:106-109` says *"Accumulated across calls rather than
reset, so a caller that walks the roll ends holding the whole picture"* — no caller can hold it,
because nothing exports it.

**Why it is wrong (and why it is MINOR, not MAJOR):** no information is permanently lost. The
corpus-wide figure is recovered independently by `audit()`'s own rewalk at `:473-482` and printed
uncapped at `:538-542`. What fails is the claim: the per-source record order `04a3f79b7f55` asked
for reaches no ledger, no report and no caller. **Confidence:** high, by grep.

### MINOR — a `doc:` source is reported through the binding out-channel as `bound`
**Where:** `:357-359` against `source_binding` at `:288-312`.
`host_to_sources` (`:172-174`) strips only the `pages:` sentinel; `doc:` pseudo-hosts survive the
inversion. So a document-ingested source resolves to a non-empty `hosts` list, skips the
`if not hosts:` arm entirely, and gets `binding.update({"kind": "bound", ...})` — a hard-coded
literal — while `source_binding` would answer `"doc"` (`:293-294`, `:311-312`) and `main()`
counts and prints `doc` as its own category (`:551`). The out-channel exists specifically so the
caller can tell *why* a list is empty (`:328-332`); for this class of source it reports the wrong
reason. **Confidence:** high, read both paths.

### INFO — an unreachable branch, already marked
**Where:** `:291-292`. The `pages` arm inside `source_binding`'s first loop can never fire,
because `host_to_sources` removed every `pages:` host before the loop sees it. The comment at
`:296-298` says so and the reachable answer comes from the raw-file read below it. Saw the
marking, moving on.

Otherwise clean: `host_to_sources` genuinely raises rather than caching an empty map (`:158-171`),
`load_index`'s fault tallies all reach `audit()` and `main()`, `files_seen` is the honest
denominator (`:501`, `:524`), and the `_CACHE` slots are keyed by the path argument as their
comment claims (`:98-103`).

---

## cleanup.py (445 lines)

Read whole, including both replacement callbacks and the mangled-escape roster. Checked for:
an `--apply` path that can write without the caller knowing; the idempotence of
`clean_description` (which `pipeline._is_cleaned_twin` depends on); a report whose numbers
disagree with the records it just wrote.

`clean_description` idempotence traced by hand against `(?<!\?\?)` at `:170`: on `"...???)"`
the first `?` fails the following `\s*(?=\))`, and the second and third fail the lookbehind, so
nothing matches — the convergence the comment at `:138-166` claims. On `"... Furansu ? )"` the
match succeeds and `_ruby_question_mark`'s non-ASCII scan admits it. Both hold.

### MINOR — two of the six uncapped rosters do not print which source a row came from
**Where:** `:409-412` (`desc_fixed`) and `:413-415` (`thin`).
Both lists are built with the source as their first element (`:333`, `:338`) and both printers
unpack it and never use it:

```
for s, n, b, a in desc_fixed:
    print(f"     {str(n):<24}{b!r}")
```

Rosters 1 and 1b print `{s:<28}{n}` (`:384-385`, `:393-394`) and all three ceiling rosters print
the source. **Why it is wrong:** these two are routinely the largest lists in the report (the
markup roster's own measurements in `pipeline.py:740-743` and this file's `:108-116` run to
thousands of sites across 216 records), and an entry name with no record beside it is not
something a curator can go and look at. The value is collected and dropped at the printer.
**Confidence:** high; read both loops.

### MINOR — an unmarked character cut the governing comment says was removed
**Where:** `:333` — `desc_fixed.append((src, nm, d[:46], cd[:46]))`.
The comment at `:374-382` that uncapped the five rosters ends *"The per-name character cuts in
the same statements go with them."* They did go for the ceiling rosters — `:288-293` records the
70- and 52-character cuts being removed and says why ("the half that got cut is routinely the
half that says why"). They did not go here: both the before and after descriptions are still
sliced at 46 with no remainder marker, and printed with `!r` so the truncation is invisible as
truncation. Under the ruling `identity.py:731-738` cites ("every cut prints its remainder;
nothing is silently short"), this is the last unmarked console cut in the file.
**Confidence:** high; the comment and the code are eleven lines apart in the same function.

### QUESTION — the entry loop only ever inspects entries phase 2 has already judged
**Where:** `:308-310` — `for e in rec["entries"]: if not e.get("catalogued"): continue`.
An entry with no `catalogued` key (never through `phase_entrypass`) is skipped by every branch:
nav striking, empty-mechanic striking, markup stripping and thin marking. Intentional sequencing,
or a gap? It matters downstream: `pipeline._is_cleaned_twin` (`pipeline.py:810-824`) decides
whether the catalogue writer may keep the disk's cleaned description, and it can only ever answer
True for entries cleanup has actually reached. Filed as a question, not a fix.

Otherwise clean: every write is gated on `args.apply`, the thin-mark branch's `changed` flag is
set exactly once per entry (`:347-355`), `write_record`'s verdict is consumed (`:367-369`), and
`main()` returns 1 when anything failed to land.

---

## snapshot.py (376 lines)

Read whole. Checked for the failure this module exists to prevent: a `verify()` that cannot fail,
a partial capture or restore that reports as whole, and a path escaping the tree.

**Those three are all genuinely closed** — `_dir_matches` (`:203-230`) walks the snapshot side
file by file with `shallow=False`, `before()` refuses both the empty and the partial capture
(`:180-194`), `restore()` raises rather than returning a short count (`:320-325`), and `_rel` /
`_safe_join` guard both the capture and the write ends (`:70-84`, `:267-284`).

### QUESTION — a directory "restore" is a merge, and `verify()` structurally cannot see that
**Where:** `:316` — `shutil.copytree(src, tgt, dirs_exist_ok=True)` inside `restore()`, whose
default `into` is `HERE` (`:304`).

**What:** restoring a snapshotted *directory* over the live tree merges the snapshot into
whatever is currently there. Files created after the snapshot was taken survive; a file the
snapshot does not contain is not removed. So the tree after `restore()` is the union, not the
state at capture.

**Why it may matter:** `verify()` (`:245-247`) restores into a fresh `tempfile.mkdtemp()`, where
an empty target makes merge and replace indistinguishable. The module's stated product is
*"PROVE IT RESTORES"* and *"An untested backup is a belief"* (`:18-20`), and the proof it offers
covers only the empty-target case, never the populated-target case the actual recovery path runs.
Plausibly deliberate — the module is emphatic elsewhere about never deleting anything, and a
replacing restore would delete — so this is a question about intent, not a filed fix.

### INFO — `--list` is declared and never read
**Where:** `:344`. `a.list` is never consulted; the listing block at `:356-372` runs whenever
`--verify` is absent, so the flag changes nothing either way.

---

## roll.py (318 lines)

Read whole. Checked for: the fail-open decision being applied where it was not argued for;
whether `mutate`'s compare-and-swap window is actually closed; and whether `exclude`'s
`rows` trap is really shut.

`mutate`'s digest ordering (`:126-152`) is correct in both directions — taking the digest
**before** the read means a write landing in either gap (digest→read, or read→replace) makes
`replace_if_unchanged` refuse, so the failure is closed, as the comment claims. `exclude`'s
`caller_supplied` split (`:240-254`) does now return before reaching the module-level `ROLL`
write, so the 2026-08-26 trap is shut.

### MINOR — the CLI reports a clean zero from a roll it could not read
**Where:** `:300-313`, via `load()` at `:44-52`.
`load()` returns `[]` for **any** read failure and for a non-list, recording it only with
`silence.note` — which writes to `state/failures.json` and prints nothing (verified against
`silence.py:871-896`). So on an unreadable, torn, or absent `SWEEP_ROLL.json`, `main()` prints

```
ACQUISITIONS ROLL — 0 source(s), 0 excluded
Excluded sources keep their records. They are removed from WORK, not from disk.
```

with exit 0 — indistinguishable from a healthy roll with nothing excluded. The fail-open
reasoning is argued for `in_scope` (`:71-78`) and is right there: an unreadable roll must not
silently exclude the library. That argument does not extend to a **report** whose entire purpose
is to name the exclusions, and the module's own header is that "a decision recorded somewhere
nobody reads is a decision that looks taken and is not." **Confidence:** high; read `load`,
`out_of_scope`, `main` and `silence.note`.

### MINOR — `mutate` gives an absent roll and a corrupt roll the same message
**Where:** `:129-135`. One `except Exception` produces
*"...could not be read, so nothing was written to it -- the roll is canonical and not derivable
from a failed read"* for both `FileNotFoundError` and `JSONDecodeError`. The docstring at
`:107-111` explicitly invokes the opposite standard: *"Same distinction endpoint.register draws:
absent and unreadable are different facts."* Both outcomes refuse, so nothing is at risk in the
data — what is wrong is that an operator on a fresh tree is told the canonical roll is damaged.
`pipeline.py` needed this same ruling four separate times (phases 5, 6, 7, 8) and got it;
this refusal reads as the one that did not. **Confidence:** high.

### INFO — `main()` drops the `isinstance` guard its siblings apply
**Where:** `:305` — `r.get("entry_count")` over raw `load()` rows. `out_of_scope` (`:65`) and
`exclude` (`:242`) both guard with `isinstance(r, dict)`; a roll containing a non-dict element
raises `AttributeError` here instead of being skipped.

### INFO — `in_scope` re-reads and re-parses the roll on every call
**Where:** `:79` → `:64` → `:44`. Cost only (216 rows), no correctness consequence. Noted because
the obvious caller shape is a per-source loop.

`exclude`'s deliberately-unported state (`:260-295`, blocked on `handoff/run35/checks_L4.py`) is
marked at length with the reason and the exact port. Saw the marking, left it.

---

## scale_theories.py (215 lines)

Read whole. This module is explicitly **held on purpose** under order `01695fe3ef26` and owner
ruling 2026-09-08 (`:21-56`), and the five physical constants are held under order
`a78d5cd748b2`. Saw both markings. Verified the held-ness claims still measure true where I could:
`grep` finds no `import scale_theories` anywhere in `src/`, and no other file reads any of its five
constants (`chord_field.py` and `descending_ladder.py` each declare their own, as the docstring
says). `surviving_theory`'s arity assertion (`:208-215`) does fire on real data — exactly one
theory carries `falsified: False` — and the switch/argument separation at `:87-88` and `:124-125`
is what the selection actually reads, so order `e7dc70db782b` is genuinely closed.

### MINOR — the "only mention anywhere" claim is stale twice over, and contradicts this same docstring
**Where:** `:34-36` — *"Nothing in `src/` imports this module. Its only mention anywhere is its own
name inside `derivation.SCAN_MODULES`, and `liveness.py` lists it as NEVER REACHED."*

**What:** the import half still holds. The "only mention anywhere" half does not, in two separate
ways.

1. `derivation.SCAN_MODULES` is no longer a literal list. It is
   `SCAN_MODULES = _scan_modules()` (`src/derivation.py:584-596`), computed by walking `src/` at
   import time — so the name `scale_theories` is not *inside* it at all; it appears there only as
   a filesystem entry at runtime.
2. The module is named by name in at least five other files: `drill.py:249-250`,
   `liveness.py:360`, `:362`, `:400`, `:410`, `onomast.py:453`, `tempus.py:46`, and
   `descending_ladder.py:94`.

**Why it is wrong:** the last of those is cited by this very docstring eighteen lines further down
(`:52-55`): *"`descending_ladder.py` carries a comment cross-referencing 'scale_theories.py names
the same value as G_NEWTON', and removing them would silently make an existing comment false."*
The docstring therefore asserts at `:34` that a mention it itself documents at `:52` does not
exist. The same paragraph at `:31` corrects an earlier version of itself for exactly this class of
error — *"a comment asserting a completed action that never happened is worse than no comment: the
next reader takes it as settled and stops looking."*

**Confidence:** high; both halves verified by grep and by reading `derivation.py:584-596`.

---

## module_index.py (192 lines)

Read whole. Checked the two hand-kept-list detectors against the failure the module's own
docstring argues about, and verified every name in `GROUPS` resolves to a real file.

All 48 names across the six `GROUPS` lists exist as `src/<name>.py` (checked each), and no name is
repeated across groups — so neither detector is live today.

### MINOR — the duplicate-group check has a blind spot for the same name twice in one group
**Where:** `:113-124`.

**What:** `first_title = seen_in.setdefault(n, title)` followed by `if first_title != title`. A
name listed twice inside a **single** group's list yields `first_title == title` on the second
sighting and is never appended to `dupe_names`. The rendering loop at `:132-139` then builds
`rows` straight from `names`, so the module is emitted twice under one heading — no stderr line,
no `silence.note`, `rc = 0`.

**Why it is wrong:** the comment introducing the check at `:107-112` states its purpose as
*"NO GROUP MAY CLAIM THE SAME MODULE TWICE"* and describes the harm as *"the module would render
silently under two different '## <stage>' headings -- no error, no stderr line, rc=0 -- the exact
'hand-kept table drifting silently' shape this file's own docstring exists to argue against."*
The within-group case produces that outcome under one heading and the check cannot see it. This is
the shape the brief calls a gate that refuses one of the two things it names.
**Confidence:** high; read the accumulator and the renderer together. Not live (no repeats today).

### INFO — `stale_names` can double-count
**Where:** `:126-128` — `stale_names.extend(stale)` runs per group, so a missing name claimed by
two groups is counted twice in the `%d module(s)` at `:173`. The name list itself is still
complete, which is what the Hard Rule 0 comment at `:172` is protecting.

### INFO — `first_line` leaves the handle to refcount close
**Where:** `:51` — `ast.parse(open(path, encoding="utf-8").read())`. Cosmetic; noted only because
this file argues elsewhere about writes being explicit.

---

## Summary

| severity | count |
|---|---|
| MAJOR | 2 |
| MINOR | 10 |
| INFO | 11 |
| QUESTION | 3 |

Both MAJORs are in `pipeline.py`: a model-computed field that reaches no record, and a
whole-object state dump that silently reverts the repair tool built to fix the state.
`identity.py` and `snapshot.py` are the two cleanest modules in the batch; `scale_theories.py` is
held on purpose and its only defect is a stale claim about itself.
