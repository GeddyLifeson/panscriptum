# SWEEP run55 — AUDIT batch 01

**Module read:** `src/drill.py` (17,679 lines) — the whole file, top to bottom, in nine
contiguous passes. 493 `net(` call sites, no duplicate `(area, name)` pairs, no constant-valued
attack outside the deliberate `_probe_area` at :9167 (checked by parsing the module's own AST in
the scratchpad; nothing was executed from `src/`, `data/` or `state/`).

**How the reading was done.** Every line read in order. Then, for each claim that leaves the
file, the target was opened and checked: `silence.note`, `health.record`/`is_selftest`/`flush`,
`escalation._halt_lock`/`_a_probe_release`/`resume_subsystem[_verdict]`,
`prose_gate.instrument_shortfall`/`assert_instrument_present`, `citecheck.stale_citations`/
`_classify`/`_PLACEHOLDERS`/`_PATH_LEAD`, `chain.extract`/`fit`/`write_result`,
`pipeline.phase_chain`, `manifest_builder`/`scout`/`foreman.scout_hostless` signatures,
`withdraw_chapters.main`, `ingest_doc.register`/`mine`, and eleven cited line numbers in other
modules. Where a citation points outside this batch it is named as such below.

**This shift's new nets were audited specifically, as instructed.** `drill_citations` (7 nets),
the layer-4c Instrument family (10 nets in `drill_train`), the two halt-lock nets plus
`_lock_verdict`, the two rung-4 person-check nets, and the two float-rung nets. Findings against
them are M2 and m1; everything else in that set held up to the attack, and the reasoning for
each is in the "what was checked and found sound" section at the end.

---

## MAJOR

### MAJOR — ~27 `silence.note()` sites inside drill probes reach the live ledger and will halt the library over an antivirus hiccup

**Where:** src/drill.py:609, 2880, 3718, 3734, 3738, 3797, 3803, 3811, 3823, 3827, 3838, 4116,
4203, 4225, 4302, 4352, 6307, 9281, 9297, 9315, 9470, 9473, 9476, 9567, 9596, 9802, 16280.
(The mentions at :3193, :6713, :9161 and :9655 are docstring prose, not call sites, and are
excluded. The four in `main()` at :17491, :17497, :17508 and :17637 are a separate, milder case —
see INFO i4.)

**What the code does now.** Each of these sites is a probe cleanup or a "measurement declined"
arm that calls `silence.note("drill.py:<site>")`. None of them is wrapped in
`_deliberately_failing` and none is declared through `_not_a_leak`. Examples:

    3718  _si.note("drill.py:junction-probe-cleanup")        # os.rmdir denied
    4116  _si.note("drill.py:state-probe-cleanup")           # os.remove denied
    4203  _si.note("drill.py:blast-probe-cleanup")           # os.remove denied
    9470  _si.note("drill.py:paid-lane-config-absent")       # not this machine
   16280  silence.note("drill.py:datasette-config-unwritable")

**Why it is wrong.** `silence.note` (src/silence.py:871-889) does `import health` and calls
`health.record(...)`. `drill.py:130` replaced `health.record` with `_spy_record` at import, on
that same module object, so every one of these notes:

  * appends a row to `_LEDGER_ESCAPES`, which makes
    `no_probe_writes_into_the_live_failure_ledger` (drill.py:17087-17096) **raise**; and
  * increments `health.LEDGER`, which makes
    `nothing_reached_the_ledger_by_a_route_the_spy_cannot_see` (drill.py:17103-17112) **raise**.

`net()` records a raised attack as `held=False`; `main()` re-reads the breach on a settled tree
(where `_LEDGER_ESCAPES` is unchanged, so it reproduces by construction) and escalates
`DRILL_BREACH` at OWNER (drill.py:17640). **An `os.remove` denied by a scanner for one second
halts the whole library.** The keys carry no `__drill…__` marker, so `health.is_selftest`
(health.py:137-140) is False and they also land in the operational ledger a person reads.

The file already knows this and has written it down at exactly one of the twenty-seven sites.
`_src_mtime_preserved` (drill.py:450-453) **prints instead of noting**, with the reason in full:
"`silence.note` reaches `health.record` and this helper runs inside probes, so a note here would
be a battery rehearsal writing into the operational failure ledger — the leak THE LEDGER WITNESS
halts the library over (order 400d5c76e6f8)."

Worse, two of these sites were *created* as the remedy for this same halt arriving by a
different route. `_junction_out_of_the_writable_surface`'s docstring (drill.py:3748-3757) records
that the net used to end `and not os.path.exists(link)`, that "a denied `os.rmdir` — an antivirus
scanner holding the directory for a moment is enough on this machine — turned a held net into a
breached one, and `main()` escalates a breached net to OWNER", and that the fix was to have
`unstage()` file a note instead. The note now produces the identical OWNER halt one area later.
`cannot_edit_shared_run_state` (drill.py:4104-4116) makes the same argument in the same words —
"killing the battery over a permissions error would lose every other verdict with it" — and takes
the same route.

**Confidence.** Traced end to end by reading: `silence.note`, `health.record`, `health.is_selftest`,
`_spy_record` (drill.py:93-113), both witness nets, `_reread_the_breaches` and `main()`'s
escalation. Not observed firing — every one of these is an error path and none of them is taken
on a healthy machine today (`~/cascade/config.json` exists, so :9470 is not live either). It is
latent, not current.

### MAJOR — `a_resume_is_refused_to_a_program` attacks the LIVE rung-4 ledger, and its failure mode is lifting a real stop

**Where:** src/drill.py:9644-9677 (net registered at :9678). Landed this shift.

**What the code does now.** It first requires the REAL ledger —
`if E.STOPPED != E._REAL_STOPPED: return False` — and then calls, for real:

    for fn in (E.resume_subsystem_verdict, E.resume_subsystem):
        if not _refuses(lambda f=fn: f("catalogue_web", ruling), PermissionError):
            return False

**Why it is wrong.** The docstring asserts "Nothing is written — the refusal is raised before the
compare-and-swap loop". That is true *only while the guard under test holds*.
`escalation.resume_subsystem_verdict` (escalation.py:961-1010) validates the ruling, then
`if not _a_probe_release(name) and not _by_a_person_at_the_cli(): raise PermissionError`, then
falls into the CAS loop that rewrites `state/STOPPED.json`. The mutant this net was written for —
the 2026-09-10 pass dropping the `not` from that person check, named in the net's own docstring —
is therefore also the condition under which this probe **resumes `catalogue_web` on the live
tree**. `catalogue_web --recatalogue` is not a hypothetical subsystem: it is the one the whole
rung-4 area exists because of, stopped on 2026-08-26 for nulling 26 synthesis blocks.

This is the exact shape `_no_runtime_clear` was repaired out of. drill.py:4373-4382 (order
9495caa65d06): "This called the REAL `clear()` four times against the LIVE `state/HALT.json`, and
the only thing between it and lifting a standing halt was the very guard it exists to test … A
regression in it, or a reordering that put the caller check after the status read, turned this net
into the thing it forbids." One rung down, in a net landed today, the same probe shape is back.

The net's own reason for refusing a sandbox is real and is written down: inside `_esc_sandbox`,
`escalation._a_probe_release` returns True for **every** name by its condition (1)
(escalation.py:916), so a sandboxed version could not fail. That makes this a genuine design
problem rather than an oversight — see QUESTION Q1.

**Confidence.** Read `resume_subsystem`, `resume_subsystem_verdict` and `_a_probe_release` in
full and traced both branches. The refusal does hold on today's tree, so nothing has been lifted.

### MAJOR — `the_destructive_tool_asks_before_it_moves_anything` runs `withdraw_chapters --go` against the LIVE tree

**Where:** src/drill.py:10393-10420.

**What the code does now.** It builds an `_esc_sandbox()` (which redirects `escalation`'s four
paths and stubs `workorders.file_order` / `health.record`), writes a synthetic standing halt into
the scratch `HALT.json`, sets `sys.argv = ["withdraw_chapters.py", "--go"]`, and requires
`WC.main` to raise `SystemHalted`. **`WC.HERE` and `WC.CATALOG` are not redirected.**

**Why it is wrong.** The property under test is that the halt interlock is present and reached. If
it is not — a deleted `assert_clear`, a loosened import guard, a reordering below `argparse` —
then `main()` proceeds under `--go` and, per `withdraw_chapters.py`'s own header at :131-142,
`shutil.move`s every catalogued chapter out of the library, moves every unclaimed stray in
`output/raw`, and rewrites `output/index/catalog.json`. Every action there is a MOVE, so the
archive is the only copy afterwards. The blast radius is currently zero — `withdraw_chapters.py:150-156`
does assert the halt above `argparse`, and `output/raw` is empty while the prose gate is closed —
but a probe whose failure mode is the irreversible act it is testing for is the class this file
refuses everywhere else.

The containment pattern already exists in this same file: `withdraw_dry_run_does_not_count_
catalogued_chapters_as_strays` (drill.py:14614-14675) redirects `WC.HERE` and `WC.CATALOG` into a
scratch root, builds its own `output/raw` and `catalog.json` there, and deliberately omits `--go`.
It was landed later and got it right.

**Confidence.** Read both drill nets and `withdraw_chapters.main()`. Verified the interlock is
present today at withdraw_chapters.py:150-156.

### MAJOR — `_the_kill0_scan_reads_both_answers` is a control over a private COPY of the matcher, so it cannot do the job it says it does

**Where:** src/drill.py:13412-13437, registered at :13305 with the expectation "the ratchet asserts
set equality, which passes just as happily when the matcher is dead".

**What the code does now.** The control defines its own local `calls(text)` whose AST test —

    isinstance(node, _ast.Call) and isinstance(node.func, _ast.Attribute)
    and node.func.attr == "kill" and isinstance(node.func.value, _ast.Name)
    and node.func.value.id == "os" and len(node.args) == 2
    and isinstance(node.args[1], _ast.Constant) and node.args[1].value == 0

— is a character-for-character duplicate of the test inside `_no_new_bare_kill0_probe`
(drill.py:13403-13408). It then asserts that its own copy catches a real call and is not fooled by
the same words in a comment or a string.

**Why it is wrong.** The ratchet's assertion is `found == set(_KNOWN_KILL0_SITES)`, and the whole
reason a control exists beside it is that a matcher which found nothing would also need
`_KNOWN_KILL0_SITES` emptied — which is one edit away, and is invisible to a second, independent
copy of the predicate. Break `_no_new_bare_kill0_probe`'s matcher and this control keeps passing,
because it never calls it. Its sibling one screen down, `_the_wired_claim_scan_reads_both_answers`
(drill.py:13514-13537), was built correctly: it drives the **shared pure helper** `_unwired_claims`
over four synthetic trees, and drill.py:13483-13495 records that doing so is exactly what caught
the lookbehind bug that had made the live row unfailable.

**Confidence.** Diffed the two predicates line by line; read both controls and both ratchets. Not
exploited — the matcher is correct today.

---

## MINOR

### MINOR — `drill_citations`' seventh net passes vacuously on an empty result

**Where:** src/drill.py:16101-16107. Landed this shift.

**What:** `all(f["reason"] in ("PAST_EOF", "BLANK_LINE", "BARE_BRACKET", "UNRESOLVED")
for f in _citecheck_over({...}))`.

**Why it is wrong.** `all([])` is True. The fixture (`t.py` = `_CITE_TARGET`, `c.py` =
`"# t.py:2 and t.py:5 and gone.py:9\n"`) is built to produce exactly three findings, and the net
asserts neither the count nor that any of the three reasons actually appeared. A `stale_citations`
that returned `[]` for that fixture — the detector dead — reports HELD. The same file names this
shape twice: `_write_phase_stays_open_when_everything_refuses` (drill.py:5578, "`all([])` is True,
and two very different histories arrive at an empty list") and `_meta_ban_has_no_fall_through`
(drill.py:6742, "An empty list is the 'absence read as clean' shape"). The three positive nets
above it would catch a totally dead detector, so this is a hole in this net rather than in the
area; `len(...) == 3` and a reason-set equality would close it.

**Confidence.** Read `citecheck.stale_citations`, `_classify`, `_PLACEHOLDERS` and `_PATH_LEAD`
and hand-evaluated the fixture: `t.py` splits to 4 lines, so `:5` is PAST_EOF, `:2` is BLANK_LINE,
`gone.py` is not in the scratch root and not a placeholder, so UNRESOLVED.

### MINOR — stale line citation: `anchors.py:427`

**Where:** src/drill.py:11886 and :11907 (the second is inside the net's printed expectation, so
it reaches a breach report and a halt record).

**What it claims:** "anchors.py:427 indexes INSTRUMENT_WINDOWS[b] for every b in LADDER with no
guard, so the same divergence arrives as a KeyError raised from inside production code."

**What is there:** `src/anchors.py:427` is `"%r is named by this check and absent from ANCHORS, so
the claim could not "` — a verdict string in an unrelated block. The unguarded index is at
`src/anchors.py:546`: `collapsed = [b for b in A.LADDER if A.INSTRUMENT_WINDOWS[b][0] ==
A.INSTRUMENT_WINDOWS[b][1]]`. The substance of the claim is correct; the address is not.

**Confidence.** `grep -n INSTRUMENT_WINDOWS src/anchors.py` returns 533, 546, 548, 551 only, and
line 427 was read directly. `anchors.py` is outside this batch; the finding is about drill.py's
citation, not about anchors.

### MINOR — stale line citation: `feats.py:159`

**Where:** src/drill.py:8076, in `_backoff_stops_at_its_ceiling`'s docstring.

**What it claims:** "the clamp it is named after is `feats.py:159`,
`min(BACKOFF_MAX, _BACKOFF.get(host, 1.0) * BACKOFF_GROWTH)`, and deleting the `min(...)` leaves
the constant exactly as it was."

**What is there:** `src/feats.py:159` is `h = h.split("/")[0].split(":")[0].rstrip(".")`, inside a
host normaliser. The clamp is at `src/feats.py:238`. `BACKOFF_MAX` itself is defined at
`feats.py:173`. Again the substance holds and only the address has rotted.

**Confidence.** `grep -n BACKOFF_MAX src/feats.py` → 173, 238; line 159 read directly.

### MINOR — `_chain_done_key_follows_the_disk`'s `chain` stubs are pinned narrower than the real module

**Where:** src/drill.py:5541-5546.

    stub.extract      = lambda rows, workers=8: ({("a","b"): 1}, [], {})
    stub.write_result = lambda edges, res, unmatched: stub.built

**Why it is wrong.** The real signatures are `chain.extract(rows, batch=8, limit=None, workers=8)`
(chain.py:492) and `chain.write_result(edges, res, unmatched=None, unanswered=None)`
(chain.py:107). Today's caller, `pipeline.phase_chain` (pipeline.py:2535 and :2549), happens to
pass exactly `workers=` and exactly three positionals, so the stubs match — but they match the
CALLER, not the function they stand for, and both kwargs the stub cannot accept already exist in
the real module. The day `phase_chain` passes `limit=` (a partial run) or `unanswered=`, this net
takes a TypeError, `net()` grades a raised attack as a breach, and the library halts over a correct
change. This is the class the file has already been bitten by twice and repaired twice with
`**kw`: `_cited_names_for_can_credit_a_name` (drill.py:2209-2224 — "A stub narrower than the
function it stands for is not a stricter test, it is a test of the signature, and the signature is
not what this net is about") and `_partial_canary_merges` (drill.py:6554-6562, which halted the
library once for exactly this when `binding_health.canary` grew `available=`).

**Confidence.** Read the three real signatures and the live call site in `pipeline.phase_chain`.
Not live today.

### MINOR — `the_document_ingester_asks_about_the_halt`'s docstring claims a second line of defence the code does not have

**Where:** src/drill.py:10499-10546.

**What it claims:** "with the gate removed, neither call can actually move anything, because HOSTS
points into the temp tree and the record writer is stubbed."

**What the code does:** it redirects `ESC.HALT_FILE` and `ID.HOSTS` and nothing else. Nothing
stubs `pipeline.write_record_catalogue`, which is what `ingest_doc.mine()` writes
`data/records/*.json` through (ingest_doc.py:510, inside `mine`). Its own sibling forty lines up,
`the_tool_that_deletes_mined_evidence_asks_about_the_halt` (drill.py:10458-10462), really does stub
every writer it names (`HC.ROSTERS`, `HC.entities_by_source`, `HC._land_hosts`, `HC._land`,
`WI.load_records`), which is what makes the contrast legible.

**Why it matters.** Latent rather than live — `mine("__drill_source__")` would almost certainly
fail earlier for want of a corpus under `data/docs/__drill_source__/` — but a stated guarantee
that is not the one the code provides is the thing a later reader relies on when deciding this
probe is safe to leave in the standing battery.

**Confidence.** Read the net, and grepped `ingest_doc.py` for `write_record_catalogue`, `HOSTS`
and every `open(`. `ingest_doc.py` is outside this batch.

### MINOR — `_sandbox_without_its_target_refuses`'s litter clause is still unfalsifiable (order 156c2e28f823, unchanged)

**Where:** src/drill.py:7438-7482, final line `return refused and not any(os.path.isdir(r) for r
in roots)`.

The `finally` at :7478-7480 already `shutil.rmtree`s every remembered root, so the second conjunct
is True by construction on every path that reaches the return. Recorded here only to confirm it is
unchanged on today's tree, and that a deliberate search for the same shape across all 493 nets
turned up **no other instance**: every other "and the cleanup worked" clause I checked
(`blast_cap_bites`, `the_cap_resets_per_run`, `abandoned_sandboxes_are_reaped`,
`_a_reap_never_takes_a_live_runs_sandbox`, `_a_sandbox_under_construction_is_invisible_to_the_reaper`,
`a_refused_write_leaves_no_litter_beside_the_ledger`, `a_refused_lift_leaves_no_temp_file_behind`)
is evaluated **inside** the `try`, before its own cleanup runs, and is therefore real.

### MINOR — `an_unusable_rung_lands_at_MANAGER_rather_than_raising` carries a meaningless `self=None` parameter

**Where:** src/drill.py:11455. Landed this shift.

`def an_unusable_rung_lands_at_MANAGER_rather_than_raising(self=None):` — `net()` calls the attack
with no arguments (drill.py:398), so the default absorbs it and the net works. But `drill.py`
defines no classes, `self` is not a `src=`-style override the way `_srcdir`-taking nets use one,
and it is the only net in the file with a parameter no caller supplies. It reads as a paste
artefact. Harmless today; the risk is a later reader adding a second parameter beside it and
expecting `net()` to fill it.

---

## INFO

### INFO — `drill_citations` adds five fixture citations to `citecheck`'s own view of `src/`

`drill.py` now contains the literal strings `t.py:2`, `t.py:3`, `t.py:4`, `t.py:5` (:16057,
:16064-16085) and `gone.py:9` (:16104). `citecheck._PLACEHOLDERS` (citecheck.py:80-83) covers
`foo.py`, `bar.py`, `baz.py`, `qux.py`, `x.py`, `y.py`, `z.py`, `example.py`, `module.py`,
`mymodule.py` and `somefile.py` — not `t.py`, `c.py` or `gone.py`. They resolve to nothing under
`src/`, so they come back UNRESOLVED, which `stale_citations` suppresses unless
`include_unresolved=True`; nothing is filed as work. `python src/citecheck.py --unresolved` now
prints five rows that are drill fixtures rather than citations, and `citecheck.py`'s own docstring
enumerates the known UNRESOLVED sites without them.

### INFO — two historical examples in `drill_citations`' expectations no longer point where they say

drill.py:16072 — "standards.py:604 was exactly this [a blank line]". `src/standards.py:604` is now
`return a == b or a == b + ":latest" or b == a + ":latest"`.
drill.py:16077 — "address_space.py:381 was exactly this [a bare closing bracket]".
`src/address_space.py:381` is now a docstring sentence.
Both are past-tense claims about citations that have since moved, so they are not false about
history; but a reader checking them against today's tree learns the opposite of what the sentence
says. `citecheck.py`'s module docstring carries the same two examples. Cited by drill.py; both
targets are outside this batch.

### INFO — `citecheck._lines`' process-wide cache retains the contents of every scratch file `_citecheck_over` deletes

`citecheck._lines(path, _cache={})` (citecheck.py:93) never evicts. `_citecheck_over`
(drill.py:16027-16046) creates a fresh `mkdtemp` per call and removes it in a `finally`, so seven
nets leave fourteen cache entries describing directories that no longer exist. Paths are unique per
`mkdtemp`, so nothing is mis-answered and the memory is trivial. Noted only because a cache that
outlives the tree it describes is the shape this project usually flags.

### INFO — three `silence.note` calls in `main()` are outside the witness's reach by ORDERING, not by design

drill.py:17491 (`drill.py:liveness-scan`), :17497 (`drill.py:src-fingerprint`), :17508
(`drill.py:stamp`) and :17637 (`drill.py:breach-copy`) all run *after* `drill_ledger_witness` has
already been graded, so they cannot breach it. They are correct where they are. The observation is
that the guarantee here rests on the statement order inside `main()`, while the equivalent property
for AREAS is called out as load-bearing and given a written rule (drill.py:17346-17350, "New areas
go ABOVE this line"). The stamp path has no such rule.

### INFO — the ledger-witness property holds in `drill_escalation_behaviour` by construction rather than by the witness

`_esc_sandbox` (drill.py:9955-9960) replaces `health.record` outright for the duration of every
`_esc_probe`, so a `silence.note` raised by any of that area's ~60 probes lands in a local list and
never reaches `_LEDGER_ESCAPES`, `health.LEDGER` or disk. That is correct and is the right design —
prevention beats detection — but it means the witness's printed claim, "no probe **anywhere** in
this drill writes into the live failure ledger", is enforced by two different mechanisms in two
different places, and only one of them is the thing the net measures. Not a defect; recorded so a
future reader does not conclude the witness has coverage it does not exercise.

---

## QUESTIONS (possible deliberate design decisions — reported, not proposed as fixes)

**Q1.** `a_resume_is_refused_to_a_program` and `the_person_check_is_not_defeated_by_choosing_a_name`
both open with `if E.STOPPED != E._REAL_STOPPED: return False`, i.e. they deliberately refuse to
run in a sandbox, because `escalation._a_probe_release` answers True for every name when `STOPPED`
is redirected (escalation.py:916, condition 1). That is a real constraint and the nets are right
about it. But it forces the rung-4 person check to be attacked against the live ledger with a live
subsystem name (MAJOR #2). Is the intended resolution (a) to give `_a_probe_release` a form whose
sandbox exemption does not swallow the name check, (b) to have the drill repoint `_REAL_STOPPED`
alongside `STOPPED` for the duration, or (c) to accept the live attack because the guard is proven
by two independent nets? This is escalation.py's contract, not drill.py's, so it is put as a
question.

**Q2.** The "a measurement that could not be taken is NOTED, not graded" convention — ruled twice
in this file (order ef0b67732a3b at drill.py:3672-3691, order 5eea5c20db8a at drill.py:16258-16269)
— and the ledger witness (order 895a99602bf0) are in direct conflict: the note IS the write the
witness halts over. MAJOR #1 assumes the witness is the newer and stronger rule and the note sites
should be wrapped or declared. If instead the intent is that a declined measurement should be
*visible in the ledger* and the witness should tolerate a declared class of them, then the remedy
is a widening of `_not_a_leak` rather than twenty-seven wrappers. Either reading is defensible from
what is written down; the choice is the owner's.

**Q3.** `_reread_the_breaches` (drill.py:17210-17274) re-runs each breached net's *attack* after the
battery has finished. For probes with side effects — `blast_cap_bites` recharges the cap,
`_junction_out_of_the_writable_surface` re-stages a junction under live `src/`,
`a_resume_is_refused_to_a_program` re-attempts the live resume — that is a second execution of the
side effect, after `drill_ledger_witness` has already been graded, so anything it writes to the
ledger is unwitnessed. The re-read is clearly deliberate and its fail-closed behaviour is correct;
whether re-running side-effecting probes (rather than only re-reading source-shape ones) was
intended is not recorded anywhere I could find.

---

## What was checked in the new nets and found sound

Recorded so the coordinator can see what the absence of a finding rests on.

**`drill_citations` (7 nets, drill.py:16027-16107).** `_citecheck_over` writes only into a fresh
`tempfile.mkdtemp` and passes `src_dir=root` to `citecheck.stale_citations`; `_classify` joins
`src_dir or SRC` (citecheck.py:129), so both the scan root and the resolution root are the scratch
tree and nothing reads or writes live `src/`. The scratch tree is removed in a `finally`. The
fixture arithmetic was hand-evaluated against `_BARE_BRACKET`, `_PLACEHOLDERS` and `_PATH_LEAD`:
`t.py` is four lines, so `:5` → PAST_EOF, `:2` → BLANK_LINE, `:3` (`)`) → BARE_BRACKET, `:4` →
clean; `motoko/discord_bot.py:256` is skipped by the `_PATH_LEAD` lookbehind; `foo.py:12` is a
declared placeholder. The three "is caught" nets and the three "is NOT flagged" nets are each
falsifiable in both directions. Only the seventh is vacuous (m1).

**Layer-4c Instrument family (10 nets, drill.py:1947-2023).** Every fixture was traced through
`prose_gate.instrument_shortfall` (prose_gate.py:464-491) and `assert_instrument_present`
(prose_gate.py:496-521) by hand. `◈` (U+25C8, the entry marker) and `▣` (U+25A3, the Instrument
marker) are distinct, so `_INSTRUMENT_MARK`'s bare-`▣` alternation cannot be satisfied by a head
line. `_I_BARE` reaches `missing` because `marked and (scored or excused or not being)` is False
for a Person with neither a score nor an excuse; `_I_PLACE` reaches `present` through the
`not being and excused` arm; `_I_FEATS` has no `Class:` line so `required` stays 0 and both
functions return the exempt answer. `_an_instrument_refusal_names_the_block_it_refused` reads the
message and rejects a bare crash. No vacuous arm.

**Halt-lock nets and `_lock_verdict` (drill.py:11490-11539, 11542-11552).** `escalation._halt_lock`
(escalation.py:390-450) keys off `HALT_FILE` at call time, so `_esc_probe`'s redirection reaches
the lock; both probes run inside `_esc_sandbox`, whose `health.record` stub means their notes
cannot reach the live ledger, and the contended path is additionally wrapped in
`_deliberately_failing`. `a_fresh_lock_is_not_stolen` restores `HALT_LOCK_ATTEMPTS` in a `finally`
and is falsifiable in both directions (invert the staleness comparison and `got` becomes True at
the first check). `a_stale_lock_is_stolen` asserts both the steal and the release. `_lock_verdict`
exists because the live call site is `with _halt_lock():` with no `as`, which is a correct reason
for a helper.

**Rung-4 person-check nets (drill.py:9602-9642, 9644-9683, 9685-9738).**
`the_person_check_is_not_defeated_by_choosing_a_name` drives `_a_probe_release` as a pure
predicate and asserts both directions against `health.SELFTEST_RESUME_SUBJECTS`; it writes nothing.
`the_probe_exemption_fails_closed_without_its_evidence` correctly wraps arm (1) (where `health` is
importable and the note lands for real) and correctly does NOT wrap arm (2) (where
`sys.modules["health"] = None` makes `silence.note`'s own `import health` fail inside its total
`except`), and restores `sys.modules["health"]` in a `finally`. Both use `is False` rather than a
truthiness test. The only finding against this trio is the live-ledger attack in
`a_resume_is_refused_to_a_program` (MAJOR #2).

**Float-rung nets (drill.py:11435-11473).** Both run inside `_esc_probe`; neither reaches the OWNER
rung, so no halt file is written even in the scratch tree. `a_float_rung_is_honoured_or_refused_
but_never_truncated` asserts both limbs (3.0 stays SAFETY and is not flagged unrecognised; 2.7
lands at MANAGER *and* carries `unrecognised_level == "2.7"`), which is what stops a
switched-off guard passing. `an_unusable_rung_lands_at_MANAGER_rather_than_raising` covers
`None`, `[]`, `object()` and `bytes` — the four inputs the `and -> or` mutant reaches
`level.is_integer()` with. Only the stray `self=None` parameter is filed (m7).

**Sandbox cleanup, generally.** `_esc_sandbox`'s `restore()` puts back all four `escalation` path
constants plus `workorders.file_order` and `health.record` and rmtrees the directory; `_esc_probe`
calls it in a `finally` and lets the exception travel, which is the correct grading.
`_ledger_redirected` restores four `ledger_guard` globals and asserts every redirected path lands
under the scratch root before the body runs. Both were re-read against the new probes.

---

## Other things checked and found clean

* **No duplicate `(area, net)` registrations** across 493 call sites, so `_ATTACKS` never shadows a
  net and `_reread_the_breaches` always re-asks the row it recorded.
* **No constant-valued attack** in any production area (`lambda: True` appears once, at
  drill.py:9167, inside `_probe_area`, which is reachable only through `main(areas=...)` and is
  explicitly excluded from the production tuple).
* **No empty `expectation` string** on any net, so `main()`'s breach printer (drill.py:17398-17400)
  always has something to say.
* **Every new area is in `main()`'s production tuple** (drill.py:17325-17350), `drill_citations` at
  :17344, and `drill_ledger_witness` is still last.
* **Reachability primitives** (`_live_stmts`, `_live_walk`, `_breaks_out_of`, `_arm_leaves`,
  `_static_truth`) read correctly against the four fixtures in
  `the_reachability_primitive_understands_loop_else`; the `while True:` `orelse` skip in
  `_live_walk` and the fall-through break in `_live_stmts` are both present and agree with the
  net's assertions.
* **Stub signatures** for `manifest_builder.build_jobs_for_source`, `scout.scout`, `scout.sweep`,
  `escalation.assert_clear`, `pipeline.write_record_catalogue` and `foreman`'s `scout` stand-in all
  match their real counterparts; only `chain`'s are narrower (m4).
* **Cited line numbers verified sound:** `liveness.py:12` (names `coverage._p()`),
  `context_budget.py:276` (`def report(cfg)`), `anchors.py:37-40` (the six-axes comment),
  `coverage.py:53` (the `cachekey.owns()` sentence), `withdraw_chapters.py:216-219` (the "A COPY
  BEFORE THE IRREVERSIBLE STEP" paragraph), `foreman.py:115` (the block recording that foreman does
  not run drill.py). Two were stale (m2, m3). `mutate.py:731` does still cite
  `verify_math.py:7990`, so `drill_citations`' first expectation is current.
* **Nothing in this batch was executed.** No module under `src/` was run; the only thing run was a
  read-only AST scan of `drill.py`'s own source from the session scratchpad.
