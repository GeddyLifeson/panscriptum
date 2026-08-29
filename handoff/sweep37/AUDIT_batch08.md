# SWEEP 37 — BATCH 08 AUDIT

Modules read in full, every line:

| module | lines |
|---|---|
| `src/magnitude.py` | 1428 |
| `src/allsweep.py` | 630 |
| `src/zfighters.py` | 504 |
| `src/estate.py` | 403 |
| `src/sevenfold.py` | 327 |
| `src/anchors.py` | 280 |
| `src/style_audit.py` | 231 |
| `src/roll.py` | 144 |
| **total** | **3,947** |

(The brief said 4,037; the tree holds 3,947 today. Every one read end to end, no skimming.)

No source file was edited. `prose_enabled` and `step4_enabled` untouched. No live model
calls; `roll.py` and `estate.py` were never run as programs. Every finding below was
demonstrated by execution or by measurement against `data/`, and the HEALTHY section
records what was checked and held.

---

## MAJOR

### M1 — `magnitude.SYSTEM` asks for a citation form guard 1 cannot accept
`src/magnitude.py:497` (SYSTEM, STEP 2) vs `src/magnitude.py:557-583` (`verify`, guard 1)

The prompt says, verbatim:

> `Cite, for each axis, the exact feat number that justifies it.`

Guard 1 demands the opposite: the citation must MATCH a mined SENTENCE
(`hit = next((i for i, t in mined_norm.items() if t and (t in cn or cn in t or _overlap(t, cn) > 0.6)), None)`).
The instrument instructs the model to answer in a form its own gate throws away.

**The model obeys the prompt.** Measured across all 507 records in `data/ASSAYS.json`:
41 published worksheet lines are bare feat numbers — `starwars.fandom.com|Yoda` has
`{"ruin": "1", "reach": "4", "vector": "8", "volition": "13", "acumen": "28", "suasion": "41"}`;
`worldofwarcraft.fandom.com|Sylvanas Windrunner` has nine of them; `mario.fandom.com|Luigi`
has `"[4]"`, `"[5]"`, `"[8]"`, `"[11]"`, `"[12]"`, `"[16]"`, `"[17]"`.

**And this is the instrument's largest single loss.** Of 1,687 rejections recorded across
the corpus:

```
 1032  citation not in the mined feats     (61.2%)
  607  guard 2: feat does not bear on axis
   37  cross-axis index
   11  guard 3: entity is not the actor
    0  no citation given
```

Every one of those 1,032 cost an axis its number, and the reason string blames the model
for doing what the prompt told it to.

**The second half is worse than the loss.** `_norm("41")` is `"41"`, and the match test
includes `cn in t` — plain substring containment against the normalised feat text. A numeric
citation therefore selects whichever mined feat happens to contain those digits anywhere.
Demonstrated:

```
feats = [ "Beerus erased the universe with a flick of his wrist, all 41 of its sectors.",
          "Goku destroyed a mountain range with a Kamehameha." ]
verify("Goku", {"ruin": {"score": 8.8, "feat": "41"}}, ev)
  -> guard 1 MATCHED feat #1 (the Beerus sentence)
  -> rejects=[('ruin', 'feat does not bear on ruin: Beerus erased the universe ... all 41')]
```

Guard 2 happened to catch that one. It did not have to: guards 2 and 3 were handed a
sentence the model never pointed at, which is exactly the shape the run-#27 comment above
this code describes for the EMPTY citation — "a check that cannot fail looks exactly like a
check that passed, in the one place where passing means fabricated provenance." The empty
case was closed; the one-token and numeric cases were not. `verify("Goku", {"ruin": 9.1,
"feat": "destroyed"}, ev)` returns **ruin = 9.1 with zero rejections**, citing a sentence the
model gave one word of.

Confidence: HIGH (prompt text, gate code, and 507 live records all read directly).

---

### M2 — guard 5 (QUANTITY) bypasses guards 2 and 3 and OVERWRITES their refusals
`src/magnitude.py:1011-1016`, `quantity_scores` at `src/magnitude.py:421`

`quantity_scores()` never calls `subject_refusal`, and `assay_entity` assigns its result
**unconditionally**, after `verify`/`_split_gate` and after the cross-axis index check:

```python
for ax, q in quantity_scores(ev, anchor).items():
    scores[ax] = q["score"]
    sheet[ax] = f"INSTRUMENT {q['measured']} = ..."
```

So an axis that guard 3 has just refused as a bystander's deed is re-instated by the
instrument path with no doer check at all. Demonstrated:

```
sentence: "Beerus destroyed the planet with a blast measured at 50000 megatons."
quantity_scores(...) -> {"ruin": {"score": ..., "by": "instrument", "feat": <that sentence>}}
subject_refusal("Goku", <that sentence>, "ruin") -> "Beerus leads the act and Goku is not named"
```

The module docstring calls guard 5 "the highest-grade evidence the library can hold" and
the Attestation ladder puts Instrumented above Transcribed — which makes the missing doer
check more serious, not less. This is the same shape as the settled `_split_gate` fault:
a guard that exists, can refuse, and is not asked on one of the paths that reaches
publication.

Confidence: HIGH (executed).

---

### M3 — the split-retry quality gate `if not sheet` can essentially never fire
`src/magnitude.py:974`

The retry exists for "a one-shot whose every citation failed verbatim" — the Jace case.
But `verify()` writes into `sheet` for every axis returned as a STRING status
(`src/magnitude.py:551`, `sheet[ax] = cited or st`), and SYSTEM actively asks for statuses:
"Returning nine statuses and two scores is a correct answer."

Demonstrated — a one-shot in which the only numeric axis was rejected as fabricated:

```
every numeric axis rejected; sheet non-empty?  True   len: 10
sheet sample: {'continuity': 'n/a', 'celerity': 'n/a', 'reach': 'n/a'}
-> `if not sheet` is False, so the split retry does NOT fire
```

Corroborated on live data: `transport` across 507 records is
`pool 153 / local 127 / split 3 / null 224`. **`split-retry` appears zero times.** The path
the comment at 975-981 was written for has never run.

Second consequence of the same conflation: those status strings are passed straight into
`A.assay(..., worksheet=sheet)`. **321 of 1,457 worksheet lines in the live corpus (22.0%)
are a bare status word** (`"n/a"`, `"none"`, `"unestimable"`) standing where a citation
should be, and **99 SCORED, published records** carry at least one. 34 of the 259 records
holding a worksheet have no sentence in it at all — only numbers and status words.

Confidence: HIGH (executed and measured).

---

### M4 — allsweep's VERIFY tier: every verifier's own verdict is computed, printed, landed, and graded by nothing
`src/allsweep.py:598-599`, mirrored at `src/workorders.py:183-186`

```python
bad = (len(broken)
       + sum(1 for r in verifiers if r["crashed"] or r.get("timeout"))   # rc is never read
       + len(lint_bad) + ... )
```

`rc` is stored in `ALLSWEEP.json` and consulted by no one. `workorders.battery_faults`
copies the same rule, so a verifier's verdict reaches neither the sweep's exit code nor the
work-order queue. This is the identical hole this file documents twice for other tiers —
LINT at line 575 ("computed, printed to the console and dropped") and ESTATE at line 591
("computed, printed, landed in ALLSWEEP.json — and excluded from this sum").

The concrete case is one the file itself argues for. `src/allsweep.py:112-117`:

> `--check` now exits 1 on a real disagreement (rho < 0.3), **so this row can actually fail.**

and `src/rosetta.py:426-436`:

> THE EXIT CODE HAS TO CARRY THE VERDICT ... so nothing that gates on rc (a shell,
> allsweep's VERIFIERS, a scheduler) could ever learn a franchise's own published ordering
> disagreed with our Assay

Verified: `rosetta.py --help` exits **0** (it has argparse), so rosetta's verdict does not
reach the IMPORT tier either. `rosetta.py --check` returning 1 is invisible everywhere.
The run-#26/batch-3 change was made and never wired.

The complication the fix has to respect, and which is why this is not a one-line change:
`silence.py` and `audit.py` exit 1 BY CONTRACT when they have findings (both are rc=1 in
today's `ALLSWEEP.json` and both are healthy). Some verifiers' rc=1 means "I have findings";
others' means "the instrument is broken". The tier needs that distinction declared per
verifier in `VERIFIERS`, not a blanket `rc != 0`.

Note in mitigation, so this is not overstated: `anchors.py` has no argparse, so
`check_import` running `anchors.py --help` executes the whole validation and its rc DOES
land — in the IMPORT tier, by accident. Verified by running it.

Confidence: HIGH (code, live `ALLSWEEP.json`, and both exit codes executed).

---

### M5 — sevenfold's balance guard only fires when EVERY seam ties, and the live shelving is unbalanced because of it
`src/sevenfold.py:138`

`seams()` has an even-split fallback added precisely because clustering all six cuts at one
end "produced exactly the giant component this function's own docstring says can't happen".
The fallback is guarded by:

```python
if len({g for g, _ in gaps}) <= 1:
```

which requires ALL gaps to be identical. **One nonzero seam anywhere defeats it**, and the
weakest-seam path then sorts the still-tied 0.0 gaps by index and takes the first six — the
clustering the fix was written against. Demonstrated on 100 members with exactly one
weighted pair:

```
all seams tied        -> children 14,15,14,14,14,15,14      (the fallback, balanced)
ONE nonzero seam      -> children  2, 1, 1, 1, 1, 1, 93     (guard skipped)
```

**And it is happening on the live data.** Driving `tiers._graph()` and
`shelve(srcs, w, depth=3)` against the real resonance graph (209 sources, 3,638 weight
entries, 46 of 208 adjacent seams exactly 0.0):

```
top tier (hyperverse) members per child : 55, 43, 19, 1, 16, 9, 66
largest xenoverse                        : 48
distinct (H,X,Mt) leaves occupied        : 120 of 343
largest leaf                             : 38 sources at ONE address
addresses holding more than one source   : 17
sources sharing an address with another  : 106 of 209  (50.7%)
example: Ω › H6 › X6 › Mt.6  holds "2112 (Rush)", "A Plethora of Paladins",
         "Chowder", "Curse of Strahd", "Darksiders", ... 38 in all
```

`shelve()`'s docstring: *"Balance is by construction: the ordered list is cut into `span`
contiguous blocks at each level, so no branch can swell into the giant component that
wrecked every discovered scheme."* That is not true of the code as written. `build()`'s
docstring reasons from "343 slots, comfortably more than 209"; 120 are occupied and half the
roll shares an address.

**The report cannot see it.** `main()`'s balance table (`src/sevenfold.py:277-295`) prints
CHILDREN PER PARENT, which `seams()` clamps to ≤ 7 by construction — the module's own
comment at line 290 already flags `"OVER SPAN"` as a display that cannot print. Members per
branch, which is the quantity the balance claim is about, is never printed. So the tier
whose collapse this whole two-stage design exists to prevent is unmeasured in the report
that exists to measure it.

Confidence: HIGH (synthetic demonstration plus live measurement).

---

## MODERATE

(The order queue's severity vocabulary is INFO/MINOR/MAJOR/BLOCKING, so these were
filed as noted per finding: D1 as MAJOR, D2/D3/D4 as MINOR.)

### D1 [filed MAJOR] — anchors: four of the five anchors' stated tests are printed and never asserted
`src/anchors.py:175-259`

`run()` computes an ASSAY, an INSTRUMENT reading, a COLLEGE interval and a bit-value per
anchor, prints them all, and gates the exit code on exactly one thing: the monotone
floor→ceiling ordering. Each anchor's `note` states a testable claim and none of them is
tested. The Seat of the Creator's is explicit:

> the Instrument's M10 window is (30, 30), so every faculty pins at 30 regardless of score,
> **and the Transcendence Grade must read V.** A ceiling that keeps climbing is a broken ruler.

That is an assertion written as a comment. Nothing checks it.

What the missing assertion is hiding, from today's own run:

```
Goku  [person]  anchor M5
  INSTRUMENT {'Strength': 30, 'Dexterity': 30, 'Constitution': 30,
              'Intelligence': 30, 'Wisdom': 30, 'Charisma': 30}   Grade None
The Seat of the Creator  [office]  anchor M10
  INSTRUMENT {'Strength': '30 (Grade V)', ... all six at 30 ...}   Grade V
```

Goku's faculty values are identical to the ceiling's. `assay.INSTRUMENT_WINDOWS` is
`(30, 30)` for M5 through M10, so `min(30, round(lo + (s/10)*span))` returns 30 for **every**
score from 0.0 to 9.9 at those six bands — the Instrument's faculties carry zero information
for any entity at M5 or above, which is most of the library's headline entities. Goku's own
anchor comment reads `acumen=4.0,  # not a planner, and the charter should not pretend
otherwise`, and the Instrument prints Intelligence 30.

The window table belongs to `assay.py` / charter X.6 §6 and may well be intended; the defect
filed here is anchors.py's, because this file's docstring says *"The point is to find
breakage, not to display success. Anything that reads absurdly here is a defect in the
instrument"* — and this reads absurdly with nothing in the file able to say so.

Confidence: HIGH for "printed and not asserted" (code). HIGH for the reading itself
(executed; windows table printed directly). MEDIUM on whether the window degeneracy is a
defect or a declared convention — that is an owner question, which is the more reason for the
anchor to state a verdict rather than a paragraph.

### D2 [filed MINOR] — the cross-axis citation check is dead on the DEFAULT path
`src/magnitude.py:1004-1009`

```python
m = re.match(r"\s*\[(\d+)\]", cited)
```

Only `compose()` labels evidence `[N]` (`src/magnitude.py:815`). `_split_assay`'s per-axis
prompt emits bare `- ` bullets (`src/magnitude.py:709`) and `_split_gate` stores the raw
citation, so the pattern cannot match anything the split path produces — and split is the
default for everything over `ONE_SHOT_MAX`. Verified:

```
split prompt evidence line : '- Goku destroyed a mountain range.'
one-shot evidence line     : '  [1] Goku destroyed a mountain range.'
re.match(r'\s*\[(\d+)\]', '- Goku destroyed...') -> False
corpus: all 37 cross-axis rejections are on pool(3)/local(34); split records = 3, zero hits
```

Practical loss is small — a foreign-axis citation on the split path is caught by
`_split_gate`'s verbatim test instead, because each axis is matched only against its own
candidate list. But the comment at 1002 claims *"Cross-axis citation is now checkable by
INDEX rather than by lexicon ... so a line filed elsewhere is caught exactly"*, and on the
default path it is not checked by index at all.

Confidence: HIGH.

### D3 [filed MINOR] — an unrecognised anchor becomes M0 on one path and DEFERS on the other
`src/magnitude.py:965` vs `src/magnitude.py:744`

```python
anchor = got.get("anchor") if got.get("anchor") in A.LADDER else "M0"     # one-shot / local
...
if not got or got.get("anchor") not in A.LADDER:  return None             # _split_assay
```

A model returning a garbage anchor gets a published `M0` on the one-shot path and a retry on
the split path. `M0` is a claim about a village-scale entity, not a null, and it flows into
`A.assay()` and into the ceiling clamp comparison. The split path's behaviour is the right
one.

Confidence: HIGH (code).

### D4 [filed MINOR] — `estate.charter()`'s errata are string-presence tests whose verdict is fixed
`src/estate.py:252-254`

```python
for rung in ("Supercluster", "Filament", "Hyperverse"):
    if rung.lower() in text.lower():
        note("charter erratum (open)", rung + " is a rung with no Magnitude band")
```

The finding claims the rung has no Magnitude band; the test only asks whether the word
appears anywhere in the charter. Amending the document to give Supercluster a band would not
silence the row — the erratum can never be cleared by fixing it, only by deleting the rung's
name. The docstring names a fourth erratum ("M0-M2 sit below rung 1") that is not checked at
all. Blast radius is low because these rows are deliberately `bad=False`.

Confidence: HIGH (code).

---

## MINOR

- **N1** `src/estate.py:145` — `artifacts()`'s `roots` is a fixed allowlist, while the
  docstring says *"Every file in the project, opened and checked. No sampling anywhere"* and
  allsweep prints *"every file this project owns, opened"*. Three top-level directories are
  never walked: `backup/` (29 `.py.presilence` files), `docs/` (empty), `site/` (2 real
  files; the other 18 are `.git`, already in `SKIP_DIRS`). Low impact today because
  `.presilence` is not in `TEXT_EXT` so those would only be size-checked anyway — but a new
  top-level directory is invisible to the tier by default, which is the wrong default for a
  tier whose whole claim is completeness.
- **N2** `src/allsweep.py:473` — `lint_bad[:20]` prints without a "... and N more" remainder,
  unlike the artifacts list at line 511 which does. The full list lands in ALLSWEEP.json and
  the count is graded, so display-only.
- **N3** `src/sevenfold.py:322-323` — prints `WRITE DENIED` and still `return 0`.
  `src/zfighters.py:497` returns 1 in the identical situation and is the pattern to copy.
- **N4** `src/anchors.py:242` — the monotone invariant runs only over the five names
  hardcoded in `order`. An anchor added to `ANCHORS` and not to `order` is silently
  unchecked; one in `order` and not in `ANCHORS` raises KeyError.
- **N5** `src/style_audit.py:227` — the real path returns 0 whatever the `OVERUSED` / `OVER`
  flags say, and the module is not in allsweep's `VERIFIERS`. `--self-test` gates correctly
  but asserts nothing about `TURN_ENDING`, which is the measurement found wrong today; a
  regression guard is absent exactly where the bug was. (The prose gate is shut, so nothing
  is at risk right now.)
- **N6** `src/roll.py:101` — the docstring states *"`exclude()` has no callers anywhere in
  `src/`"*. `src/drill.py:2863` and `:2869` call it. They are the net that attacks the path,
  which is presumably what was meant, but the sentence as written is false and is the kind of
  claim a later reader acts on.
- **N7** `src/zfighters.py:6` — the docstring says "these fifteen"; `ROSTER` holds 14 (the
  fifteenth, Son Goku, is carried in from `REFERENCE_ASSAYS_PRESENCE.json` and is not
  hand-built here).

---

## HEALTHY — checked, not assumed

- **`_split_gate` guard 3 works and is wired** (today's settled fix, re-verified against the
  full candidate sentence): `subject_refusal("Goku", "Beerus erased the universe with a flick
  of his wrist.", "transgression")` -> `"Beerus leads the act and Goku is not named"`;
  the same sentence for `"Beerus"` -> `None`. Refuses in one direction, passes in the other.
- **`saturated()` is NOT dead.** 89 of 507 records carry ≥6 numeric axes, so guard 4 has a
  live population to reject. `min(nums) >= 9.0` is reachable. Statuses are strings
  (`A.NONE`/`UNESTIMABLE`/`INAPPLICABLE`) so they correctly do not count toward `nums`.
- **`queue()`'s `NOT_AN_ENTITY.search`** (not `.match`) — both arms of the pattern reachable,
  as its comment claims.
- **`_one_axis` never truncates.** The `size == 0` clause sends a single over-SPLIT_SLICE row
  alone rather than dropping it. `candidates()` ranks longest-first and its `cap` parameter is
  `None` at every call site. Hard Rule 0 holds through the whole split path.
- **`_published()`** renders the charter decimal correctly (`band + ("%.2f" % val)[-3:]`).
- **`anchors.NON_ENERGETIC_AXES` is exactly right today.** Measured: the six axes for which
  `assay.axis_score()` returns `None` are `{acumen, discernment, suasion, transgression,
  vector, volition}` — identical to the declared set. Nothing enforces the correspondence
  (the constant has no reader in `src/`), but the claim is true as it stands.
- **`style_audit._WATCHED` does not double-count.** `138 == len(TELLS._COMPILED) 46 +
  len(TELLS._LEX) 92`, and `TELLS.scan` iterates exactly those two. The printed "138 patterns
  watched" is honest.
- **`style_audit.TURN_ENDING` on `\Z` fires correctly.** `--self-test` -> 1 of 3 entries,
  33.3%, on the one entry that actually closes on a turn. Self-test PASSED, rc=0.
- **`zfighters` is sound end to end.** All 14 roster sheets carry all 11 axes and no extras;
  the carried-in `Son Goku` sheet has all 11 axes, every score numeric, and a non-None
  decimal — so `value()` and `--full`'s `%5.1f` cannot crash on it. The write is gated and
  returns 1 on denial. This remains the right pattern.
- **`roll.py`'s central claim holds.** `src/resync_roll.py:88-90` imports `roll` and preserves
  `OUT_OF_SCOPE`. The `rows`-supplied write trap is genuinely closed (`caller_supplied`
  short-circuits before `write_json`), and the un-supplied path returns `write_json`'s verdict
  rather than `changed`.
- **`allsweep`'s report write is gated and counted** (`landed`, `+ (0 if landed else 1)`),
  `estate_faults` is published as its own key and summed, and `_row_is_fault` fails closed on
  a keyless row. The three fixes from runs #33/#36 are all in effect.
- **`sevenfold.seams()` really does clamp children to ≤ SPAN**, so the `"OVER SPAN"` display
  at line 294 is a tautology — which the code already says out loud at 290-293. Correctly
  documented, not a new finding.
- **`estate.inspect()`** opens and parses rather than sizing: JSON via `json.load`, Python via
  `ast.parse`, all TEXT_EXT via a control-character scan. The empty-log exemption is scoped to
  `.log/.tmp/.out/.err` only.

---

## Fault classes checked for and NOT found in this batch

- No `[:N]` truncation of any roster, evidence list, page list or stored field.
  `candidates(cap=None)` is never called with a cap; `queue(limit)` is CLI-opt-in; every
  `[:6]`/`[:8]`/`[:25]` found is a console display beside a full count and a full list on
  disk.
- No discarded write verdict: `allsweep`, `zfighters`, `sevenfold`, `roll` and
  `magnitude._land` all read `silence.write_json`'s return. (`sevenfold` reads it and then
  drops it from the exit code — filed as N3.)
- No citation by line number in these eight files except `src/allsweep.py:562`
  (`workorders.py:158`, `standards.py:1132`); both still point at the right code today,
  verified.
- No eaten regex escapes: every module carries the `_BAD_CHARS` guard and all eight pass it.

---

## ORDERS FILED (all `found_by=sweep37-batch08`)

| id | severity | code |
|---|---|---|
| 66696f8ee28f | MAJOR | magnitude-system-prompt-asks-for-a-citation-guard1-refuses |
| 41e8ffc2e490 | MAJOR | magnitude-guard5-quantity-skips-subject-and-overwrites-refusals |
| dd76d4a930f7 | MAJOR | magnitude-split-retry-gate-not-sheet-cannot-fire |
| 14bd09740627 | MAJOR | allsweep-verify-tier-verdicts-graded-by-nothing |
| 2a48315d26e6 | MAJOR | sevenfold-seams-balance-guard-only-fires-on-a-total-tie |
| 237356c82d06 | MAJOR | anchors-stated-tests-printed-never-asserted |
| d4a18a25f780 | MINOR | magnitude-cross-axis-index-check-dead-on-the-split-path |
| 8f14aff37392 | MINOR | magnitude-garbage-anchor-becomes-M0-on-the-one-shot-path |
| 7c9d763fa17c | MINOR | estate-charter-errata-are-string-presence-tests |
| 3e65dbed45a6 | MINOR | sevenfold-write-denied-still-exits-zero |
| 1618d9790f0d | MINOR | anchors-monotone-invariant-covers-only-a-hardcoded-list |

N1, N2, N5, N6 and N7 are recorded here and deliberately NOT filed: N2/N5/N7 are display or
docstring drift with no live consequence (the prose gate is shut), N1's unwalked directories
hold nothing `inspect()` would parse today, and N6 is a one-sentence correction to a
docstring. Filing them would be the "alarm that always sounds" this project's own
`estate.inspect()` docstring argues against. They are here so a later reader can act on them.

Coverage recorded: `sweep_plan.record('run37', [...eight modules...], batch=8)` — all eight
stamped `run37`.
