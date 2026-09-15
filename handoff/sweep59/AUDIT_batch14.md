# Sweep 59 -- AUDIT batch 14

Modules read in full: | module | lines | read (top to bottom? mtime) |
| src/read.py | 1671 | yes; mtime 2026-09-13 23:56:32 |
| src/health.py | 1319 | yes; mtime 2026-09-13 23:40:12 |
| src/liveness.py | 1058 | yes; mtime 2026-09-14 00:03:30 |
| src/weave.py | 709 | yes; mtime 2026-09-13 22:30:53 |
| src/anchors.py | 576 | yes; mtime 2026-09-08 16:32:49 |
| src/axis_correlation.py | 443 | yes; mtime 2026-09-06 22:31:47 |
| src/descending_ladder.py | 362 | yes; mtime 2026-09-13 23:44:43 |
| src/roll.py | 313 | yes; mtime 2026-09-13 23:24:41 |

## src/read.py

### New findings

**DEFECT MAJOR -- `_names()`'s short-single-word fallback misattributes feats via unguarded prefix match**
where: src/read.py `_names` (lines 228-244 at mtime 23:56)
evidence:
```
228	    # NO WORD ABOVE THE FLOOR (order e61e1c8e9ac4). 4,939 catalogued entities -- Ash, Vi, Ike,
...
239	    if not parts:
240	        whole = [w for w in re.split(r'\W+', entity_f) if w]
241	        if whole:
242	            pattern = r'\b' + r'\s+'.join(re.escape(w) for w in whole)
243	            if re.search(pattern, low, re.IGNORECASE):
244	                return True
```
The docstring's own reasoning for this branch ("a raw substring here would let a short word like
'The' ... match on its own -- the exact generic-word risk the length floor exists to stop.
Instead the entity's own words are required TOGETHER, in order") only protects MULTI-word
short-named entities (e.g. "The Six": "The" alone won't match, "The Six" together will). For an
entity whose name is a SINGLE word of length <=3 -- the module's own named examples "Ash", "Vi",
"Ike" -- `whole` has exactly one element, "together, in order" is vacuous, and `pattern` collapses
to a bare `\bWORD` prefix search with no length floor at all: precisely the raw-substring risk the
branch's own comment says it exists to avoid, just for the entities with the shortest names.
failure: verified directly (regex logic copied verbatim from the file, not run as `read.py`):
`_names("The volcanic ashes covered the entire valley for miles.", "Ash")` -> `True`;
`_names("The village was destroyed in the attack that day.", "Vi")` -> `True`;
`_names("He bought a table from Ikea last week for the house.", "Ike")` -> `True`.
A sentence about ashes, a village, or Ikea furniture would pass this gate and its feat (if it also
clears `_HAS_ACTION` and the verbatim check) would be filed as a feat of the Pokemon trainer Ash,
the champion Vi, or Ike -- silently contaminating exactly the entities this function's own
docstring names as its worked examples for the opposite fix.
remedy: for the `not parts` branch, either require a following non-word-character/boundary too
(`pattern + r'\b'`, blocking `Ikea`/`Ashes`/`Village` while still allowing a trailing possessive
`'s` the way the multi-word case does) when `whole` has exactly one element, or require a
minimum entity-name length before trusting a bare-prefix match at all, falling back to the
pronoun test alone below that floor.

**DEFECT MINOR -- `axis_correlation.py` main()'s independence check ignores a negative mean_r**
where: src/axis_correlation.py `main` (line 428 at mtime 2026-09-06 22:31)
evidence:
```
428	    if doc["mean_r"] and doc["mean_r"] > 0.1:
429	        print("   The Measures are NOT independent. rho = 0 is ruled out by this data.")
```
The module's whole thesis is that a nonzero correlation (in either direction) rules out the
`rho = 0` independence assumption -- the printed matrix today is all-positive so this has not
misfired yet, but the check as written only looks at the positive side: a matrix that measured a
strong NEGATIVE mean_r (e.g. -0.5) would still rule out independence just as surely, and this
line would print nothing, silently understating the finding to a reader of the console report
(the persisted `AXIS_CORRELATION.json` itself is unaffected; this is a report-only gap).
failure: a hypothetical future population with mean_r <= -0.1 prints no "NOT independent" line
even though independence is equally ruled out.
remedy: `if doc["mean_r"] and abs(doc["mean_r"]) > 0.1:`

### Known (already open orders)
- 8b3f2911fa0c (DANDWIKI_API_IS_403...) -- still accurate. `check_api_paths` (health.py:614-728)
  still probes www.dandwiki.com every cycle (not quarantined, not excluded via the roll) and the
  headline it emits is still the literal string "probed host did not answer" (health.py:727),
  which the order already documents as false for a host that answers 403. No code changed here
  since the order was filed; owner ruling (a/b/c/d) still pending.
- 34ec8a90c42f item 1 (axis_correlation.write() has no floor guard) -- still accurate. `write()`
  (axis_correlation.py:245-281) computes `doc`, stamps `degraded` when sources are known-missing,
  and lands unconditionally via `silence.write_json` with no comparison of the new `n_entities`/
  `measured_pairs` against the standing file. Owner ruling (guard vs. no guard, which floor)
  still pending; nothing here should be changed on this sweep's say-so.
- 1d45a56ae1d8 (STALE_CITATIONS_SWEEP57) -- the `read.py ~232` item is **no longer accurate**.
  The cited comment (now at read.py:232-238) no longer carries a bare `file.py:NNN` citation at
  all; it refers to `read_entity`'s chunk-selection filter and its `keys = [...] or
  [name.lower()]` line by description, not by line number. `grep -n "731" src/read.py` and
  `grep -n "835" src/read.py` both return nothing. This looks like the "read.py/handbuilt.py:
  comment citations only" edit named as in-flight in the sweep brief already landed here; the
  other files this order names (mutate.py, handbuilt.py, verify_math.py, drill.py) are outside
  this batch and not re-checked.
- 21c075e5e2d6 / 1e6f99e54b25 (writers without a halt interlock) -- still an open OWNER
  question, and this batch found THREE MORE instances not yet named on either order's roster:
  `weave.py:main()` writes CONTINUITY_GROUPS.json / RESOLVED_ENTITIES.json /
  SHARED_STAGE_GRAPH_IDF.json under `--write` with no `escalation.assert_clear()` anywhere in the
  file; `axis_correlation.py:write()`/`main()` likewise write AXIS_CORRELATION.json with no such
  check; and `roll.py:mutate()`/`exclude()` write the canonical (non-derivable) SWEEP_ROLL.json,
  also with no check, which is arguably the stronger case under the order's own proposed rule
  ("writers of non-derivable or canonical data refuse under a halt"). Not filed as new orders
  per se -- they are the same undecided class, and the order itself says the ruling "extends to
  future modules without a new ruling each time" once made.

### Checked and clean
- `roll.py:mutate()` -- digest-before-read ordering verified correct: anything landing between
  the digest take and the read makes the eventual `replace_if_unchanged` refuse (fail closed),
  it does not silently land a stale copy.
- `roll.py:exclude()`/`update_rows()` -- compare-and-swap re-applies `_apply` against a freshly
  read copy on every retry; `seen` vs "changed" distinction in `update_rows` matches its own
  documented (unreached) edge case.
- `health.py:_flush_ledger`/`_flush_samples` -- the lost-update fix (digest-before-read, re-read-
  and-re-merge on refusal, settle only what landed) is implemented as documented; the wrong-shape
  (`not isinstance(doc, dict)`) guard correctly routes through the same preserve-and-restart path
  as a parse failure.
- `health.py:check_api_paths` -- registered-domain bucketing and quarantine-exemption logic are
  correct; a quarantine-record read failure fails loud (empties the exemption set) rather than
  silently excusing every host.
- `liveness.py` -- `_credit_attrs`/`_scope_aliases` per-function alias scoping verified against
  the `drill.py`/`roll`-vs-`resonance` worked example in the module's own docstring; the module
  pass's self-reference exclusion (`g != me`) and the `_stem()` basename normalisation used
  consistently between the dead-module and receiver-resolution passes are both correct.
- `descending_ladder.py:rung_for_length` -- domain boundaries at both ends (`metres <= 0`,
  `metres > DESCENDING[0][3]`, `metres < PLANCK_LENGTH`) all refuse or route to the Fold rather
  than defaulting into a nearby rung; `shrink_report`/`transgression_bits` both correctly refuse
  (rather than silently zero-price) non-positive `to_m`/`mass_kg`.
- `anchors.py:run()` -- the CLAIMS table's per-anchor tests, the `scored`-vs-`vals` membership
  check (order 1618d9790f0d) and the finite-interval/positive-bit-value verdicts all match their
  documented intent; no tautological or unreachable verdict found.
- `weave.py:components()` -- complete-linkage `min_cross` early-exit is sound (the running
  minimum can only decrease, so an early return below threshold cannot invalidate the merge
  decision); `threshold <= 0` is refused before it could degenerate to "merge everything".
