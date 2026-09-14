# SWEEP run55 — batch 15

Modules: `local_agent.py`, `escalation.py`, `generate.py`, `endpoint.py`, `tiers.py`,
`coverage.py`, `resync_roll.py`, `propagation.py`, `repass_bands.py` (6,392 lines, all read
line by line, `cat -n` / Read, no module in this batch was executed).

Nothing in this batch was run. `escalation.py` was read only; no halt was raised, no ledger
touched, `clear()` / `_land_clear` / `_raise_halt` were never driven. `generate.py` was not run
and `prose_enabled` was never opened. Cross-batch citations I could not verify from here are
named as such at the end.

---

## 1. The four un-netted mutation gaps in `escalation.py` (asked for by name)

### GAP 1 — `escalation.py:303` — `if not recorded:` → `if recorded:`

**Reachable: YES, on every escalation in the library.** `escalate()` is the single entry point
for all six rungs and every call reaches line 301-308.

**What changes observably.** Line 302 (`rec["recorded"] = bool(recorded)`) is untouched by the
mutation, so the *record* stays truthful — which is exactly why the mutant survives: the
existing net `a_lost_escalation_says_so_on_the_record` (`drill.py:10181-10221`) asserts only
`rec.get("recorded")`, in all three of its arms. What inverts is the **stderr corroboration**,
and the comment at 298-300 states its whole reason: "SAID ON stderr WHEN IT IS False, because by
construction it cannot be said in the log -- the log is the thing that just failed." Under the
mutant:

* every healthy escalation prints `ESCALATION NOT RECORDED — …` to stderr. On a library that
  escalates at JANITOR routinely, that is a permanent false alarm, and an alarm that always
  sounds is furniture (this module's own opening argument);
* a genuinely lost append — a locked `state/`, a Norton object lock, a full disk — prints
  **nothing at all**, on the one channel that exists precisely because the log is gone.

So the mutation does not merely mute a warning: it swaps the two conditions, so the channel is
loud exactly when there is nothing wrong and silent exactly when the janitor's rung failed.

**The net that kills it.** Extend the existing `a_lost_escalation_says_so_on_the_record` probe —
it already builds all three worlds — by capturing stderr around each arm
(`contextlib.redirect_stderr(io.StringIO())`) and asserting on the sentinel `ESCALATION NOT
RECORDED`:

* arm 1 (both appends land): the sentinel must be **ABSENT** from stderr — this is the half that
  kills the dropped `not`;
* arm 2 (`silence.append_line` returns False for everything): the sentinel must be **PRESENT**;
* arm 3 (only the per-source area log fails): the sentinel must be **PRESENT**.

Two-sided by construction, costs no new fixture, and needs no halt: `escalate(SUPERVISOR, …)`
never touches `HALT.json`. (`drill._quietly` swallows stderr today; this net needs a capturing
variant rather than a swallowing one.)

### GAP 2 — `escalation.py:1297` — `bool(cur.get("cleared", False))` → default `True`

**Reachable: yes, but only through a halt record that does not carry a `cleared` key.** Every
writer inside this module sets it — `_land_halt`'s fresh payload (`:556`), `_land_clear`'s record
(`:1256`), and `_unreadable_halt` (`:597`) — so on the module's own writes the mutant is
equivalent. The key is absent only for a **hand-written or externally-written** `state/HALT.json`,
which is a real path: a person stopping the library by hand edits this file (there is a
`--raise-halt`, but a half-finished hand edit or a restored partial backup is exactly the shape
here), and the file is also what a person opens at the worst moment.

**What changes observably.** With the key absent, `_halt_file_cleared()` answers True, so
`clear()`'s guard at 1270 (`if landed and _halt_file_cleared():`) passes, the `HALT_CLEARED`
ledger line is appended and `clear()` returns True — the CLI prints `halt cleared.` — over a
file that never said `cleared`. That is precisely the failure the comment at 1266-1269 says this
readback exists to prevent, and it is worse than no readback because there is now a positive
ledger entry saying the lift happened. It also puts `_halt_file_cleared()` in direct
contradiction with `status()` (`:641`), which reads the same missing key as **halted** — so the
library would go on refusing every job while the log says it was lifted, the exact
file/log disagreement `drill`'s neighbouring net cites as the thing to keep out of the ledger.

**Why the existing net misses it.** `the_readback_asks_what_the_file_says_not_what_shape_it_is`
(`drill.py:11165-11197`) writes `{"code": "TEST", "cleared": False}` and
`{"code": "TEST", "cleared": True}` — the key is present in **both** arms, so the default is
never exercised.

**The net that kills it.** One more arm in that same probe, three lines:

```
on_disk_without_the_field()            # json.dump({"code": "TEST"}, f)  -- no `cleared` key
if ESC._halt_file_cleared() is not False:
    return False                       # a halt record with no verdict is NOT a lifted one
```

Optionally strengthen it into a consistency assertion against the sibling reader — for the same
file, `ESC.status()[0] is True and ESC._halt_file_cleared() is False` — which pins the two
readers of the same field to the same fail-closed default and would also catch the inverse
mutation in `status()`.

### GAP 3 — `escalation.py:1324` — `return False, "raised"` → `return True, "raised"`

**Reachable: yes** (the `except` arm runs whenever `os.makedirs`, the temp `open`, `json.dump` or
`replace_if_unchanged` throws — a missing `state/`, a read-only directory, a disk full).

**What changes observably: at the caller, NOTHING — and that is the honest answer.** I traced
every path. `clear()` consumes the pair at 1265 and immediately gates on
`landed and _halt_file_cleared()`. The write threw, so the file on disk still holds the standing
halt with `cleared: false`; `_halt_file_cleared()` therefore returns False, `landed` is reset at
1274, the loop goes round, and the run ends in the same `THE HALT WAS NOT LIFTED after %d
attempts (raised)` branch with the same rc, the same stderr and the same `why`. The mutant is
**observably equivalent through its only caller**, covered end to end by the readback — the same
situation `drill._a_refused_landing_reports_that_it_was_refused` documents for the mirror arm in
`_land_halt` (`:590`) and explicitly refuses to accept: "It is still a hole. Nothing measured
`_land_halt`'s own contract, so the read-back was load-bearing without anybody knowing it was."

The identical argument applies here, and one rung more sharply, because `clear()`'s readback is
itself the subject of GAP 2 above: the two layers that make this mutant harmless are the readback
at 1270 and the `cleared`-field default at 1297, and relaxing either turns an inverted return into
a lift that reports success having written nothing.

**The net that kills it** must therefore measure `_land_clear`'s own contract directly, mirroring
`_a_refused_landing_reports_that_it_was_refused`'s ARM 2 verbatim one function over:

```
blocker = os.path.join(d, "a-file-not-a-directory")   # a regular FILE, not a directory
open(blocker, "w").write("x")
ESC.HALT_FILE = os.path.join(blocker, "HALT.json")    # makedirs() must now raise
landed, why = _quietly(lambda: ESC._land_clear({"code": "TEST", "cleared": True}, None))
assert landed is False and why == "raised"
```

It lifts nothing, asks nobody's permission (no person check on `_land_clear`), and pairs
naturally with the existing `a_refused_lift_leaves_no_temp_file_behind` net, which today drives
only the `if not landed:` refusal branch and never the `except`. Note the stderr is loud by
design here, so the probe needs `_quietly` exactly as ARM 2 does.

### GAP 4 — `escalation.py:1379` — `by=(a.by or "cli")` → `by=(a.by and "cli")`

**Reachable: yes, on the person-facing resume path**, `python src/escalation.py --resume <name>
--ruling "…"`. This is the only sanctioned way a person lifts a rung-4 stop.

**What changes observably — attribution on a safety lift, in both directions:**

* `--by "imarl"` (a signed resume): `"imarl" and "cli"` evaluates to `"cli"`, so the name the
  operator supplied is **discarded** and replaced by the channel label. `resume_subsystem_verdict`
  then writes `escalate(JANITOR, "SUBSYSTEM_RESUMED", …, who="cli")` into
  `state/escalation.log` and `state/escalations/<source>.log`, and closes the standing
  `SUBSYSTEM_STOPPED` work order with `by="cli"` and the reason string `resumed by cli: …`. A
  signed lift is recorded unsigned.
* no `--by` (the default `None`): `None and "cli"` is `None`, so `who=None` reaches `escalate()`,
  which falls through to `who or os.path.basename(sys.argv[0])` and records
  **`escalation.py`** — the process, not the actor — while `WO.resolve_code(..., by=str(None))`
  writes the literal string `"None"` into the queue.

Both outcomes are the exact fault order `c614f7c145fc` was filed for one function over: "A
default that reads as a person is worse than no attribution at all, because the ledger then
carries a positive false statement about who decided." The comment at 1376-1378 states the
intended contract in as many words — `"cli"` "names the CHANNEL, which is a fact, rather than a
person" — and the mutation makes the code say the opposite of its own comment on the one record
that says who lifted a rung-4 stop.

**Why nothing catches it:** `drill.py` has no `--resume` net at all (`grep -n -- "--resume"
src/drill.py` returns nothing), so the whole `main()` resume arm is unexercised.

**The net that kills it**, in-process and touching no disk — the CLI arm can be driven without
satisfying `_by_a_person_at_the_cli`, because that check lives inside
`resume_subsystem_verdict`, which the net stands in for:

```
seen = {}
real = ESC.resume_subsystem_verdict
ESC.resume_subsystem_verdict = lambda name, ruling, by="?": (seen.update(by=by) or (True, "ok"))
try:
    sys.argv = ["escalation.py", "--resume", "X", "--ruling", "a ruling long enough to pass",
                "--by", "NET-PROBE"]
    ESC.main();  assert seen["by"] == "NET-PROBE"     # a signed lift keeps its signature
    sys.argv = ["escalation.py", "--resume", "X", "--ruling", "a ruling long enough to pass"]
    ESC.main();  assert seen["by"] == "cli"           # an unsigned lift names the CHANNEL
finally:
    ESC.resume_subsystem_verdict = real
```

Both arms are required: the first kills `or`→`and`, the second kills `or`→a literal or a dropped
default. An end-to-end alternative is a subprocess against the reserved synthetic subject
`__drill_rung4__` (which `_a_probe_release` exempts by equality), asserting the `who` field of the
`SUBSYSTEM_RESUMED` row in `state/escalations/__drill_rung4__.log` — but that writes to the live
`state/STOPPED.json`, so the in-process form above is the one to prefer.

---

## 2. The QUESTION: `escalation.py:1274` (dead) vs `escalation.py:515` (live)

**The finding is confirmed as stated.** `clear()`'s post-loop return is the literal `return
False` at `:1279`, so the `landed = False` at `:1274` is a dead store — `why` is read at 1278,
`landed` is not read again on any path. `_raise_halt` ends `return landed` at `:522`, so its
`landed = False` at `:515` does decide the returned value.

**Which half is wrong: the literal return is the safe spelling, and `_raise_halt`'s
`return landed` is the fragile half.** The two are behaviourally identical *today* — both answer
False after an exhausted loop — so neither is a bug. The asymmetry is in what each costs if
someone edits it:

* Delete `:1274` and `clear()` is unchanged.
* Delete `:515` and `_raise_halt` returns the **last `_land_halt` verdict**, which can be `True`
  in exactly the case the loop exists for: the write landed but `_halt_file_records(rec)` said our
  fault is not in the file, because a competing writer landed over us. `_raise_halt` would then
  report `halt_landed: True` for a fault that is in no file — the "verdict saying it did not
  happen" defect the comment at 502-514 says it was rewritten to close, restored by deleting one
  line that looks like a redundant reset.

So `:515` is load-bearing for a safety verdict while looking exactly like the dead store at
`:1274` — which is also precisely why the dead store survived mutation: mutating `:515` to
`landed = True` is a live, dangerous mutant, and mutating `:1274` the same way is equivalent. A
matched pair whose two halves grade differently under the same mutation is not matched.

**My reading, for the owner to rule on:** make both post-loop returns the literal `return False`
(the function has *proved* it did not land — that is not an inference, it is what an exhausted
loop means), and keep both `landed = False` resets as belt-and-braces. That makes
`_raise_halt`'s pessimism structural rather than dependent on a reset, and makes the pair
genuinely matched. The alternative — making `clear()` `return landed` to match `_raise_halt` —
restores symmetry by moving `clear()` onto the fragile spelling, and I would not. **Not fixed;
flagged.**

---

## 3. Order abc943bb6464 — the three 70-character slices in `repass_bands.py`

All three are located. Quoted verbatim, with line numbers:

**`src/repass_bands.py:53`**

```
            demoted_sources.append((src, band, (syn.get("evidence") or "")[:70]))
```

**`src/repass_bands.py:67`**

```
                    kept_entries.append((src, e.get("name"), b, sn[:70]))
```

**`src/repass_bands.py:69`**

```
                    demoted_entries.append((src, e.get("name"), b, sn[:70]))
```

### MAJOR — three undisclosed 70-character cuts on the evidence itself (Hard Rule 0)

**Where:** `src/repass_bands.py:53`, `:67`, `:69`

**What:** each cuts the *evidence text* (`synthesis.evidence` at 53, the entry's `scale_note` at
67 and 69) to 70 characters at the moment it is put on the report list, with no marker and no
remainder count. Lines 67/69 are printed at `:159` and `:170` as the `sn` column of the
SURVIVORS and DEMOTED tables. Line 53's value is never printed at all — `demoted_sources` is only
measured with `len()` at `:133` — so that slice cuts a string nothing reads, which makes it the
cheapest of the three to remove.

**Why it is wrong:** this is the one column a person reads to decide whether the corrected
evidence gate is right. The SURVIVORS heading calls each row "an act upon an object, or a
measured quantity" — a claim *about the note* — and the reader is shown at most 70 characters of
the note that claim is about, with nothing saying more exists. The same file already argues this
in its own comments: the `str(n)[:30]` name cut was removed as "the `str(n)[:30]` name cut goes
with it" (`:155`), the list caps were removed by orders `89fc2eaf23f1` and sweep42-batch04 with
the standing conclusion at `:151-152` — "Hard Rule 0 is not a disclosure rule … A stated cut is
better than a silent one and is still a smaller universe" — and these are not even stated. The
module also has the house spelling for a bound that declares itself twelve lines below, at `:100`:
`PL._stored_cut(sn, 500)`, "used rather than a bare `sn[:500]` so a note longer than the bound
declares its own cut and its size". Three bare slices sit above a comment explaining why a bare
slice is not acceptable in this same function.

**Confidence:** read every line of the module and traced each of the three tuples to its
consumer (`:133` for `demoted_sources`; `:158-159` and `:169-170` for the other two). The
`{str(n):<32}` at `:159`/`:170` is a *pad*, not a cut, so the entity names are genuinely uncapped
as the comments claim — only the evidence column is cut. A previous attempt failed twice because
the slices were described rather than quoted; the three lines above are the exact text.

---

## 4. `escalation.py` — other findings

### MAJOR — a wrong-shaped entry in `STOPPED.json` reads as NOT STOPPED (fail-open)

**Where:** `src/escalation.py:872-875`

**What:** `subsystem_stopped()` does `hit = doc.get(str(name))` / `if not hit: return False, ""`.
Any **falsy** value under a subsystem's key — `{}`, `null`, `0`, `""` — is reported as "this
subsystem is not stopped". A truthy non-dict value (a string, a list) instead reaches
`hit.get("reason", …)` and raises `AttributeError`.

**Why it is wrong:** this function is the enforcement half of rung 4 — the whole point of
`stop_subsystem`'s docstring ("The chain had recorded that rung 4 fired. Nothing read it"). Its
one production caller is `overnight.py:677`, the supervisor deciding whether to start a job.
A `state/STOPPED.json` of `{"publish": {}}` or `{"publish": null}` therefore restarts a stopped
subsystem with nothing anywhere saying so. The module has already been repaired for exactly this
reasoning one level up, in `_read_stopped` (`:792-806`): "Wrong-shape is not better evidence than
unparseable. It is the same fact -- this file does not say what it is supposed to say -- so it
gets the same answer." That argument was applied to the whole document and not to its entries.
The `AttributeError` branch fails *closed* at `overnight.py:677` (its `except Exception` answers
"refusing to start on an unknown answer"), so the dangerous half is the falsy one.

**Reachability, stated honestly:** no production writer produces such an entry today —
`stop_subsystem` always writes a dict carrying `at`/`reason`/`by`. The paths are a hand edit
(there is no `--stop` CLI, so a person stopping a subsystem by hand edits this file), a restored
partial backup, or a future writer. That is the same standing this module accepted for its own
`_read_stopped` fix and the same standing `local_agent.py` uses for its five closed bypasses
("not currently exploitable" is the condition under which the previous ones were also closed).

**Suggested shape (not applied):** treat a non-dict or empty entry the way `_read_stopped` treats
a non-dict document — report `True` with a reason naming the malformed row — so an unreadable
stop reads as a stop.

**Confidence:** read the function and both call sites; `overnight.py:668-683` read directly
(cross-batch, cited as read, not inferred).

### MINOR — raising a halt over an UNREADABLE `HALT.json` destroys the corrupt bytes

**Where:** `src/escalation.py:546-548` (with `:594-600`, `:619-633`)

**What:** `_land_halt` reads through `_read_halt_raw`, which on a parse failure or wrong shape
returns the synthetic `_unreadable_halt(...)` stand-in — a normal dict with `cleared: False`. The
`isinstance(cur, dict) and not cur.get("cleared", False)` arm therefore treats it as a standing
halt, appends the new fault to its `also`, and lands **the stand-in** over the real file.

**Why it is wrong:** the fail-closed reading is right (an unreadable halt is a halt), but the
side effect is that the only copy of the corrupted bytes is replaced by a synthesised record
whose `what` says the file "does not parse" — about a file that now parses. The evidence a person
would need to work out *why* `HALT.json` was corrupt (a torn write, a truncation, a hand edit) is
gone, and the resulting payload also has no `raised_at`, so `--status` prints `raised_at None`.
`clear()` has the same shape at `:1255-1257`. Cheap fix: copy the unreadable file aside
(`HALT.json.unreadable.<ts>`) before landing over it.

**Confidence:** traced `_read_halt_raw` → `_land_halt` → `replace_if_unchanged`; the digest passed
to the CAS is the corrupt file's own digest, so the swap succeeds.

### MINOR — `resume_subsystem_verdict`'s ruling check raises `AttributeError` on a non-string

**Where:** `src/escalation.py:975` vs `src/escalation.py:1183`

**What:** `if not (ruling or "").strip() or len(str(ruling).strip()) < 20` — `(ruling or "")`
leaves a non-string ruling (a number, a dict) intact and calls `.strip()` on it.
`clear()` at `:1183` writes the same check correctly as `not ruling or not str(ruling).strip()
or len(str(ruling).strip()) < 12`.

**Why it is wrong:** the two bars are deliberately different (order `8b1b81bcfee4`) but the two
*spellings* need not be, and the resume path answers a caller error with an `AttributeError`
instead of the sentence it carefully writes one line down. Low impact — the CLI always passes a
string — but this is the halt chain, where a reader copying one spelling onto the other is a
real hazard.

**Confidence:** read both; `str(12345).strip()` vs `(12345).strip()` is the difference.

### INFO — citations in this module that point outside batch 15

Per the brief, named rather than guessed at or dropped. `escalation.py:36` cites
`drill.py:_no_programmatic_clear`; `:1072-1080` cites `binding_health.py:291,416,419`,
`foreman.py:659`, `thread_integrity.py:678` as the refusal sites owed adoption of
`refuse_unit`/`refuse_source`; `:894` cites `health.py`'s `SELFTEST_RESUME_SUBJECTS` /
`is_resume_probe`. I verified only the two I needed for the gap analysis (`drill.py` nets, read
directly). The rest are unverified from this batch and are for the coordinator to resolve
across batches.

---

## 5. `tiers.py`

### MAJOR — the containment gate cannot fail; the refusal at `:522` can never fire

**Where:** `src/tiers.py:446-459` (the scan) and `:522-528` (the refusal it gates)

**What:** the scan walks each source and, for `(multiverse, metaverse)` and
`(metaverse, xenoverse)`, collects peers sharing the lower group index and asks whether they span
more than one higher group. Any hit refuses the `TIERS.json` write with "A tier that does not
contain its own members is not a tier."

**Why it is wrong — it is structurally impossible for the set to be non-empty.** The tiers are
nested cuts of the *same* weight map `w`, and the file asserts the nesting at import:

* `:165` `assert all(a[1] > b[1] for a, b in itertools.pairwise(CUTS))` — 100.0 > 50.0;
* `:166` `assert CUTS[0][1] <= MULTIVERSE_THRESHOLD` — 100.0 <= 102.3.

For `(metaverse, xenoverse)`: `_components(srcs, w, 100)` builds its adjacency from edges
`v >= 100`, which is a **subgraph** of the adjacency built from `v >= 50`. Connectivity at 100
therefore implies connectivity at 50, so every metaverse component lies inside exactly one
xenoverse component. `len({xenoverse of each peer})` is always 1. For
`(multiverse, metaverse)`: `weave.components` is complete-linkage at 102.3 (read directly:
`weave.py:408-436`, "a continuity group is one in which EVERY pair clears the bar"), so every
pair inside a multiverse group scores >= 102.3 >= 100 and is connected in the metaverse graph —
again one component. Sources with no adjacency get `None` and are excluded by the
`c[lo] is not None` clause at `:452`, and singleton groups give a one-element set.

So `split_sources` is always `[]`, `:459` always prints 0, and the refusal at `:522` refuses
nothing — not "today", but for any thresholds the asserts at `:165-166` permit. The comment at
`:520-521` ("Measured 2026-09-01 … 0 violations over 208 shelves, so this gate refuses nothing
today") reads the emptiness as a fact about the corpus when it is a fact about the arithmetic,
which is what makes it the dangerous kind: a gate that looks like a gate and refuses nothing, in
the file that writes the top of the Ladder of Being, read by `address_space` at import.

This is a QUESTION about intent as much as a defect: the gate may be wanted as a tripwire against
a future change to how the three tiers are derived (the comment at `:441-445` already notes that
`multi` and the other two come from *different* builders). If so it should say that it is a
structural invariant rather than a measurement, and the `assert`s at `:165-166` — which are what
actually hold it, and which vanish under `python -O` — are the real gate. If it is meant to catch
live data, it cannot.

**Confidence:** proved from this file for the metaverse/xenoverse pair; the multiverse pair
depends on `weave.components`, which is outside batch 15 and which I read at `weave.py:408-436`
to confirm complete linkage. Not run.

### MINOR — `s[:26]` in SAMPLE STACKS, 22 lines below the `_cut` that was added for exactly this

**Where:** `src/tiers.py:498` — `print(f"   {s[:26]:<28}H{c['hyperverse']} › …")`

**What:** a bare 26-character slice on the shelf name, with no marker.

**Why it is wrong:** `:469-475` in the same function records orders `1d1ac500342d` and
`fe99e57e1993` removing exactly this — "These were `a[:26]` and `b[:26]`, bare slices … with
nothing marking it" — and replacing them with `_cut(a, 26)`, the module's declared helper
("One display field, cut only if it must be, and NEVER silently"). The SAMPLE STACKS block 22
lines later kept the old spelling. It cannot fire against the six hardcoded names today (the
longest, `"Warhammer 40,000"`, is 16 characters), so this is a latent inconsistency rather than a
live loss — but it is the same defect in the same function and will bite the first time the
sample list is edited.

**Confidence:** read both blocks; measured the six literals.

### INFO — `max(len(g) for g in multi)` raises on an empty graph

**Where:** `src/tiers.py:405`, and `:409` for each cut. `max()` over an empty sequence raises
`ValueError` before any of the refusals below can report anything. Only reachable on an empty or
fully-disconnected corpus; noted, not filed as a defect.

---

## 6. `generate.py`

`generate.py:552` confirmed as the **only production caller** of
`prose_gate.assert_instrument_present`: `grep -rn assert_instrument_present src/` returns
`generate.py:552`, the definition at `prose_gate.py:496` (plus its own comment at `:435`), and
otherwise only test drivers — `drill.py:1980-2048` and `verify_math.py:7088-7100`. Nothing was
run and `prose_enabled` was not opened.

### MINOR — `build_prompt(...)[:1500]` is a silent cut inside a disclosed one

**Where:** `src/generate.py:756`

**What:** the `--dry-run` preview prints `build_prompt(job, chapter_tpl, front_tpl)[:1500]`. The
*number of jobs shown* is disclosed at `:757` ("showed 3 of N pending prompts"); the *length of
each prompt* is not — 1,500 characters of a prompt that routinely runs to tens of thousands, with
no marker and no remainder.

**Why it matters:** `--dry-run` exists so an operator can check what is about to be sent, and
`context_budget.assert_fits` refuses over-long prompts precisely because the tail is where the
loss is. Showing the head silently is showing the half that is never the problem. This may be a
deliberate "just enough to eyeball the template" decision, so it is filed as a **QUESTION**; the
house fix is one call to the idiom `local_agent._clip` / `tiers._cut` already spell.

**Confidence:** read; the slice has no accompanying marker anywhere in the block.

### INFO — tautological second conjunct in the staleness test

**Where:** `src/generate.py:710` — `if cached and cached.get("recipe_hash") != rh:`

**What:** line 708 has already `continue`d on `cached.get("recipe_hash") == rh`, so at 710 the
inequality is true whenever `cached` is truthy. Harmless — the branch only increments
`stale_count` and the behaviour is correct — but it is the "comparison against a value the code
itself just tested" shape the brief asks for, so it is on the record rather than off it.

### INFO — a corrupt `catalog.json` / `failures.json` ends the run with a traceback

**Where:** `src/generate.py:643-644`, via `load_json` at `:109-114`

**What:** `load_json` returns the default when the file is **absent** and re-raises when it is
present but unparseable. Every sibling data load in `main()` has been given an explicit refusal —
the missing manifest (`:627`), the misconfigured floor (`:674`), the unreadable `COVERAGE.json`
(`:683`) — each with a stated reason and a nonzero rc. The resume ledger and the failure ledger
have none, so they exit on an uncaught `json.JSONDecodeError`. It fails in the *safe* direction
(nothing is generated) and `silence.write_json` makes corruption unlikely, so this is INFO, not a
defect: the inconsistency is that the two files this program exists to maintain are the two whose
unreadability is the only one not reported in the program's own voice.

The rest of `generate.py` reads clean against what I looked for: every refusal in the job loop
files into `failures` and `continue`s (never aborts the pass); the meta-language gate fails
closed including on `ImportError` (`:830-861`); the derived-unattempted branch at `:501-504`
cannot fire before `missing` is populated at `:578`; `--limit 0` is honoured via `is not None`;
the final writes decide the exit code; `strip_think` fails toward the empty string and every
caller refuses an empty response.

---

## 7. `local_agent.py`

### MINOR — the durable audit trail cuts `find`, `replace` and `why` at 200 characters, silently

**Where:** `src/local_agent.py:893-894` (and the same cut repeated at `:1092`)

**What:**

```
        entry = {"path": path, "why": (why or "")[:200], "find": (find or "")[:200],
                 "replace": (replace or "")[:200], "at": time.strftime("%H:%M:%S")}
```

**Why it is wrong:** these three are not console output — they are the `patches` list, which is
returned from `run()`, printed by `main()`, and is the record of what the local model tried to do
to `src/`. `t_propose_patch`'s contract is that `find` must occur **exactly once, verbatim**, so
a truncated `find` in the trail is not reproducible: a reviewer cannot tell from the record which
of two similar edits was attempted, and cannot re-run it. The file has already ruled on this
class twice — `_clip` (`:212-234`) was written under order `cca253138a62` ("every cut prints its
remainder"), and `_whole_line` (`:666-687`) under order `f15279b5e869` for "the one unlabelled
truncation in a file that labels every other cut it makes". These are three more, in the durable
channel rather than the console one, and the `_clip` helper that fixes them is 680 lines above.

**Confidence:** read; traced `entry` through `_settle` to `run()`'s `patches` to `main()`'s dump.

### MINOR / QUESTION — the only lane that writes to `src/` writes non-atomically

**Where:** `src/local_agent.py:1076-1077` (apply), `:1080-1081` (revert on a failed gate),
`:1103-1104` (revert on an exception)

**What:** all three are `open(full, "w")` + `f.write(...)` — truncate-then-fill on a live source
file, while every other writer in this tree lands through `silence.replace_retry` /
`replace_if_unchanged`.

**Why it may matter:** CLAUDE.md's own rc=17 doctrine says "a digest taken mid-write is a digest
of garbage", and `codewatch` fingerprints `src/` on a clock this module does not coordinate with;
a concurrent import or fingerprint landing inside the window reads a truncated module. The window
is real and repeated — apply, then revert, then possibly revert again — and the file is by
construction one of the checking machinery's neighbours.

Filed as a **QUESTION** rather than a fix because there may be a deliberate reason: an atomic
`os.replace` changes the file's identity, and `_protected_identities` / `_identity_denied`
(`:548-604`) compare `st_dev`+`st_ino` — a replace would break a hard link rather than write
through it, which changes what bypass class eight looks like. Whether that is wanted is a design
call, not a sweep call.

**Confidence:** read; the three writes are the only writes in the module.

### INFO — `_tool_message` can shrink its own truncation marker

**Where:** `src/local_agent.py:1297-1317`

**What:** `strs = [k for k in out if isinstance(out[k], str) and out[k]]` includes the
`message_truncation` key that the previous iteration just added, so on a pathological result the
largest remaining string could be the marker itself, which would then be cut. Not reachable
against any tool in `impl` today (the marker is ~80 characters and the payload fields are orders
larger), so INFO rather than a defect.

The rest of `local_agent.py` reads clean against what I checked: `_safe()` refuses ADS/trailing-dot
components, prefix-sibling escapes, `.git` on both spellings, and re-asks `_denied_target` of the
resolved path; `t_propose_patch` asks the allowlist of **both** spellings and the identity gate of
the file; `_gates` case-folds every extension test, treats a pyflakes that could not run as a
failure, and reads the verify_math count with a regex rather than a substring; `_blast_ok` is
charged only at the point a write is about to land; `_chat` always returns or raises (the 503
ladder raises on the fourth attempt); `run()` calls `assert_clear` before anything; a failed
revert reaches `ok`, the exit code, a SAFETY escalation and the ledger on **both** exit paths.

---

## 8. `endpoint.py`

### MINOR — `_load()` does not shape-check the cache, and `_save()`'s docstring says it does

**Where:** `src/endpoint.py:78-88` (the reader) against `:151-153` (the writer) and the claim at
`:146-148`

**What:** `_load()` catches a failed `json.load` and heals to `{}`, but accepts **any** parsed
value. An `ENDPOINTS.json` holding `[]`, `"x"` or `3` becomes `_MEM` unchanged. `detect()` then
does `host in mem` (on a list: a value test, not a key test), `mem[host]` (`TypeError`) and
`mem[host] = found` (`TypeError`). `_save()`, reading the same file, *does* guard:
`if not isinstance(disk, dict): silence.note("endpoint.py:save-nondict"); disk = {}`.

**Why it is wrong:** the docstring at `:146-148` justifies the writer's self-healing by asserting
the reader already does it — "an unreadable one is healed rather than preserved, which is what
`_load()` above already does with the same file". `_load()` heals a **parse** failure, not a
wrong **shape**, so the claim is false for exactly the case the writer bothered to add a guard
for. Same class as the repair already made in this project to `escalation._read_halt_raw`
(`:606-617`) and `resync_roll`'s `if not isinstance(rec, dict)` (`:112`): valid JSON of the wrong
shape parses cleanly and is handed straight back.

**Consequence:** a hand-edited or externally-written cache turns every `detect()` — reached from
`feats.py`, `hostcheck.py` and `completeness.py`, several of them threaded — into a `TypeError`,
rather than into a re-probe. The same missing check reaches `main()`'s `--list` at `:357`
(`d["mode"]` on a non-dict row).

**Confidence:** read; the asymmetry between the two readers of the same file is in the source.

The rest of `endpoint.py` reads clean: `_save()` is a genuine key-wise merge over `_DIRTY` with a
digest taken before the read; `register()` refuses to overwrite a registry it could not read and
raises rather than reporting a silent success; `fetch_raw` separates 404/410 from every other
status and notes the 200-with-HTML block page; the DEAD-only TTL is asymmetric on purpose;
`main()` prints every mode in the cache rather than the three it knows (order `df960819fdf8`);
the `__main__` guard is last in file order (order `a60c150b6303`).

---

## 9. `coverage.py`

### MINOR — "all shown" is printed over a list that has already been filtered

**Where:** `src/coverage.py:378-388` (and `:390-403` for the twin)

**What:** `have = [r for r in rows if r["host"] and r["entries"] >= 40]`. The WORST COVERED
heading then prints either "(showing N of M; … --show to raise)" or, when uncapped,
`"WORST COVERED WITH A HOST — where the work is ({len(worst)}, all shown)"`.

**Why it is wrong:** "all shown" is true of `worst`, and `worst` is already the `>= 40`-entry
subset. A source with a host and 39 entries and 0% coverage appears in neither list and is not
counted anywhere in the two headings, under a label that says everything is on the page. The
`>= 40` floor is a reasonable relevance filter and I am not proposing to remove it — the defect
is the claim. Saying "(N of M sources with a host; sources under 40 entries are not listed)"
costs one clause and makes the sentence true. This is the mild form of the same shape order
`89fc2eaf23f1` corrected in `repass_bands` ("THE HEADING SAID 'every one of these' OVER A SLICE
OF FOURTEEN").

**Confidence:** read; `have` is the only input to both lists and the filter is unmentioned in
either heading.

### INFO — `_empty_state` assumes `mined_under.transport` is a mapping

**Where:** `src/coverage.py:226-232` — `tr.get("why")` on whatever `transport` holds. A
non-mapping (a string, from a hand-edited or legacy evidence file) raises `AttributeError` out of
`_state_of_file` at `:267`, which sits outside that function's `try`, and takes `measure()` down.
Written by `feats.py` today, so INFO.

Everything else checked out: the `--show-best 10` default is a *ruled* decision (order
`89fc2eaf23f1`, with `0` meaning all) and is marked as such, so it is noted and passed over per
the brief; the strict precedence at `:185-192` matches its docstring (CITED returns immediately,
READ overwrites anything below it, NO PAGE only over NOT ATTEMPTED/UNREACHABLE, UNREACHABLE only
over NOT ATTEMPTED); `_CLASSIFIER_VERSION` discards the memo wholesale on a mismatch and the
discard message counts rows rather than keys-minus-one; the host map read fails **closed** with a
`SystemExit` rather than an empty dict; `report()` guards every division.

---

## 10. `resync_roll.py`

### MINOR — the roll itself is read unguarded and unretried, in the module about roll writers

**Where:** `src/resync_roll.py:55-56`

```
    with open(ROLL, encoding="utf-8") as f:
        roll = json.load(f)
```

**Why it is wrong:** the module's own docstring is about the roll having several writers, and
`:212-217` records that every one of them now lands through `roll.mutate`'s compare-and-swap —
i.e. through an atomic replace, which on Windows leaves the file momentarily unopenable and, on a
torn read, unparseable. `coverage.measure()` puts exactly this argument to exactly this class of
file and answers it with a four-attempt retry (`coverage.py:275-305`, quoting `read.py`'s "the
host map has three writers; an unguarded load meant a single racing write could end the whole run
with a JSONDecodeError and no note"). Here, a racing write ends the resync with a traceback
before any repair is computed. There is also no shape check: a roll that parses as an object
rather than a list makes `for r in roll` iterate key strings and raises `AttributeError` at
`:154` — while the *record* files two dozen lines below are explicitly guarded for precisely that
(`:112`, "PARSES IS NOT THE SAME AS IS-A-RECORD").

**Confidence:** read; compared against the sibling guard in `coverage.py` in this same batch.

### MINOR — the closing figures describe this process's copy, not the file that landed

**Where:** `src/resync_roll.py:319-321` against `:230-248`

**What:** on the success path, `have` and `total` are summed over the in-memory `roll`, which the
repair loop mutated at `:171` and `:204`. What actually landed is `_roll.mutate(_apply, …)`,
which **re-reads** the file and re-applies only this run's rows — deliberately, so another
writer's rows survive. The printed "roll now: X/Y sources catalogued, N entries" therefore
describes the merge of *this* process's snapshot, not the merged file: rows another writer added
or changed while this run walked `data/records/` are missing from `len(roll)` and from both sums,
and a row this run wanted to relabel but which `_apply`'s fresh out-of-scope re-check (`:244`)
correctly refused still reads as relabelled in the summary.

**Why it matters:** the denied-write branch was already repaired for exactly this reasoning —
`have_on_disk` exists at `:64` because recomputing from `roll` after the loop "reads the REPAIRED
figures, not the disk figures" (order `590964e48e63`). The success branch has the same defect one
step further along: it reads the repaired figures rather than the *landed* ones. The honest
version is to have `_apply` report the merged rows back, or to re-read `ROLL` once after a
successful `mutate` and count that.

**Confidence:** read both branches and `_apply`; the mutation of `roll` in place at `:171`/`:204`
is what makes the two diverge.

The dupes accounting (`:119-122`, `:292-296`) checks out: files are visited in sorted order, the
last one wins, the message says so, and the losers are named. The unreadable / unmatched /
unnamed lists are uncapped and the caveat travels with both closing figures.

---

## 11. `propagation.py`

### MINOR — `--from` without `--to` is silently ignored

**Where:** `src/propagation.py:200` — `if args.src and args.dst:`

**What:** a caller who passes only `--from X` (or only `--to Y`) falls through to the default
diameter survey. The named shelf is never mentioned, nothing says the argument was dropped, and
the exit code then reflects the six hardcoded probe pairs rather than the query the operator
asked. Since `--from X` alone is the natural way to ask "how far is X from things", the run reads
as an answer to a question it did not answer.

**Why it matters here specifically:** this module was already repaired once for exactly this
class — order `d773ad5756ab`, "A VERDICT, NOT JUST A LINE … an automated caller could not tell a
resolved pair from a disconnected one" (`:204-207`). A silently ignored argument is the same
fault at the input end. One `elif args.src or args.dst: print(...); return 2` closes it.

**Confidence:** read `main()` in full; `argparse` defaults both to `None` and nothing else reads
them.

The rest of `propagation.py` is clean and its one marked dead line is honest: I verified that
`ascension_years(1)` is exactly `1.0 ** 1.35 - 1.0 == 0.0`, so the countdown loop at `:181-183`
always matches on its **last** iteration once `lag >= 0`, and the trailing `return 0` at `:184`
is genuinely unreachable — the docstring's claim at `:168-176`, including its own correction
about which iteration matches, is correct as written. `shortest()` handles `src == dst`, the
disconnected case and the defaultdict correctly; `load_graph` keeps the minimum distance per pair
and clamps a non-positive weight.

---

## Severity roll-up

MAJOR (3): `repass_bands.py:53,67,69`; `tiers.py:446-459/522`; `escalation.py:872-875`.
MINOR (11): `escalation.py:546`, `escalation.py:975`, `generate.py:756`, `local_agent.py:893`,
`local_agent.py:1076`, `endpoint.py:78-88`, `tiers.py:498`, `coverage.py:378-388`,
`resync_roll.py:55`, `resync_roll.py:319`, `propagation.py:200`.
INFO (6): `generate.py:710`, `generate.py:643`, `local_agent.py:1297`, `tiers.py:405`,
`coverage.py:226`, plus the cross-batch citation list in `escalation.py`.
Plus the four gap readings and the `:1274` / `:515` question above, which are answers to
questions rather than new findings.
