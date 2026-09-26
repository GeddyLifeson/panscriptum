# sweep64 batch12 audit

Scope, every module read in full, start to finish, sequentially, no sampling:

  - src/magnitude.py         1989 lines
  - src/generate.py          1306 lines
  - src/scout.py              836 lines
  - src/thread_integrity.py   722 lines
  - src/anchors.py            577 lines
  - src/pick_model.py         453 lines
  - src/catalogue_models.py   365 lines
  - src/roll.py               313 lines

Total 6561 lines. Read-only throughout: nothing under src/, data/, output/ or state/ was edited.
`prose_gate.py` (out of scope, not one of this batch's eight files) was read in part -- lines
240-540 -- because generate.py's own comments describe its contract in detail and the audit brief
specifically asks for a fresh-eyes trace of generate.py's 2026-09-25 change against the gates it
feeds; that trace cannot be honest without seeing what `assert_block_complete`,
`instrument_shortfall` and `assert_instrument_present` actually do. No finding is filed against
prose_gate.py itself -- it is out of this batch's edit/audit scope -- only against what
generate.py does with it. `sweep63/AUDIT_batch12.md` was read first (it covered magnitude.py
under a different eight-file grouping and found nothing outstanding); no other sweep63 report
names any of this batch's other seven files, so no other prior report was consulted.

No job was run. No subagent was spawned. No prose, backtick or regex was passed through a shell
argument; this file and the one shell command below (`mkdir`) are the only writes made.

## Method

Read each file top to bottom in Read-tool chunks (magnitude.py and generate.py needed two and one
extra page respectively; the rest fit in one read). For generate.py, traced the 2026-09-25
`complete_fixed_tail` / corrective-retry addition line by line against the actual prose_gate.py
functions it calls (`_entry_class`, `_INSTRUMENT_MARK`, `INSTRUMENT_CLASSES`,
`instrument_shortfall`, `section_shortfall`, `assert_block_complete`, `assert_instrument_present`)
rather than trusting generate.py's own comments about what those functions do, constructing the
truth table by hand for every (cls is None / being / non-being) x (Magnitude present / absent) x
(Instrument marker present / absent) combination the code can reach.

## Findings

**0 VERIFIED defects. 1 VERIFIED (non-defect, requested trace). 1 VERIFIED minor unit bug.
2 QUESTIONS.**

### VERIFIED — pick_model.py mixes binary and decimal gigabytes in the residency gate

`src/pick_model.py:183-199` (`total_vram_gb`) reads `nvidia-smi --query-gpu=memory.total
--format=csv,noheader,nounits`, which reports **MiB** (mebibytes, 2^20 bytes), and divides by
`1024.0` to get **GiB** (2^30 bytes). `free_vram_gb()` (line 218-237) does the same for free
memory. Both values are then treated as "GB" everywhere downstream (`budget`, `vram_gb`, every
printed message).

`weight_gb()` (line 257-264) computes a model's size from Ollama's `/api/tags` `size` field, which
is in **bytes**, via `size / 1e9` -- **decimal SI GB** (10^9 bytes), or from `KNOWN_WEIGHT_GB`,
whose values (e.g. `"qwen3:14b": 9.3`) are also decimal GB as sourced from Ollama/HuggingFace
listings.

`resident()` (line 202-215) then compares them directly: `weight_gb(model_entry) + KV_GB <=
budget_gb`. 1 GiB = 1.0737 GB, so a card whose `nvidia-smi` total is 10240 MiB is computed here as
"10.0 GB" when its true decimal capacity is 10.74 GB -- a ~7% understatement carried into every
residency decision.

**Concrete scenario:** a 10240 MiB (10 GiB) card, `VRAM_RESERVE_GB=1.0` reserve. `budget =
10.0 - 1.0 = 9.0`. A model reporting `weight_gb() == 7.9` (decimal GB, e.g. via Ollama's `size`
field) needs `7.9 + KV_GB(1.2) = 9.1 > 9.0` and is refused as "would offload" -- printed under
"REFUSED under the GPU-only residency ruling ... would offload." But the card's true decimal
capacity is `10 * 1.073741824 - 1.0 = 9.74` GB, and `9.1 <= 9.74`: the model would in fact fit
entirely resident. The tool refuses a model that fits and prints a specific (wrong) number
("~9.1GB needed vs 9.0GB budget") as though it were measured, not a unit artefact.

Direction of the error is conservative (refuses fitting models, never admits an over-budget one),
so it does not violate Hard Rule -1's fail-closed doctrine and is not a safety hole -- but it
directly undercuts this file's own stated purpose ("ranks by quality tier... tells you the
tradeoff") by discarding roughly 3/4 GB of real, usable card capacity on a 10 GB-class card purely
to a unit mismatch, which could silently drop the single best-fitting model from `scored` at
exactly the boundary the GPU-only ruling was written to police carefully.

### VERIFIED (requested trace, no defect found) — generate.py's 2026-09-25 `complete_fixed_tail` / corrective-retry change

Traced `complete_fixed_tail` (`src/generate.py:600-659`) and the one corrective retry in
`generate_job` (`src/generate.py:814-836`) against `prose_gate.py`'s actual
`_entry_class`/`_CLASS_LINE` (line 460-465), `INSTRUMENT_CLASSES = ("person","god","beast")`
(line 443), `_INSTRUMENT_MARK` (line 447), `instrument_shortfall` (line 468-497) and
`section_shortfall` (line 240-298), rather than only the surrounding comments.

Three required-refusal properties named in the brief all hold:

- **An assayed being with no scores** (Class is a being class, a real `Magnitude: M<n>` band is
  present, no Instrument section at all): `complete_fixed_tail`'s outer guard is
  `if cls is not None and not _INSTRUMENT_MARK.search(body):` -- true here (no marker at all) --
  but inside it, `elif not _MAG_FIELD.search(body):` is **false** (a real band is present), so
  neither the "Not applicable" nor the "uninstrumented" tail fires; `tail` stays empty for the
  Instrument. The entry reaches `instrument_shortfall` unmarked, unscored, unexcused, `being=True`
  -> falls to `else: missing.append(...)`, which `assert_instrument_present` (line 500-521) turns
  into a raise. Confirmed: still refused (after the one corrective retry, which is the change's own
  documented mechanism for giving the model one more chance -- the gate itself is unweakened).
- **A degraded entry with no Class line**: `cls = _PG._entry_class(body)` is `None`, so the entire
  `if cls is not None ...` block in `complete_fixed_tail` is skipped -- no Instrument tail is ever
  supplied for a classless entry. `instrument_shortfall` also skips it (`if cls is None: continue`)
  -- but `section_shortfall`'s `REQUIRED_PER_ENTRY` check (unrelated to this change, run by the
  unchanged `assert_block_complete`) still fires on the missing `Class:` line regardless. Confirmed
  still refused, via the pre-existing gate, untouched by this change.
- **An entry with no body**: `complete_fixed_tail` never inspects body length; `section_shortfall`
  (line 261-273, `MIN_ENTRY_BODY_CHARS`) is unrelated to and unaffected by the change. Confirmed
  still refused.

Also traced the corrective-retry's accept condition (`len(block_problems(_fix, len(g))) <
len(_faults)`, `generate.py:828`): both `_faults` and the retry's fault count are computed on
text that has already passed through `complete_fixed_tail`, so the comparison is apples-to-apples;
a tie or a worse retry keeps the original (tail-filled) text, and either way `assert_block_complete`
/ `assert_instrument_present` / the P8 meta-language ban (`pipeline.assert_in_universe`, called
separately in `main()` after `generate_job` returns) all still run, unweakened, on whichever text
is finally kept -- exactly as `block_problems`'s own docstring claims ("A DIAGNOSIS FOR THE MODEL,
NOT A GATE... If this under-reports, the gate refuses as before"). No path found by which the
change could let an invented Threads connection, a fabricated Instrument score, or a dropped entry
reach disk: `complete_fixed_tail` only ever *adds* the two fixed strings when a section is
*entirely absent*, and never touches, validates, or overwrites content the model actually wrote
(including a Threads line the model wrote itself, correct or not -- that validation, if any,
belongs to Hard Rule 5 enforcement elsewhere and is unchanged by this patch).

### QUESTION — roll.py's `in_scope()` fails open on an unreadable roll (deliberate, documented)

`src/roll.py:70-79`: `in_scope()`'s own docstring states "FAILS OPEN, deliberately and against
house habit. If the roll is unreadable this returns True and the source is worked," with the
stated reasoning that an unreadable-roll-as-mass-exclusion would be the worse failure. This is
exactly the shape the audit brief asks auditors to hunt (an unknown/unreadable state authorising
work), but it is explicitly reasoned, named as an exception to house policy, and traced: the one
production caller of the exclusion machinery in this batch's neighbourhood, `manifest_builder.py`,
calls `roll.out_of_scope(roll)` directly against its own already-loaded roll rather than through
`in_scope()`, so the fail-open path is not silently doubled up on by a second unreadable-roll
check. `in_scope()` itself has no caller in `src/` outside `drill.py`'s own test of the function.
Filed as a QUESTION per the brief's instruction to report such design choices rather than "fix"
them.

### QUESTION — generate.py's `_NOT_A_BEING` wording table covers 3 of 7 non-being classes

`src/generate.py:597`: `_NOT_A_BEING = {"world": "places", "polity": "polities", "event":
"events"}`. The template's actual `Class:` enum (`prompts/system_style.txt:134`) is "World /
Polity / Person / God / Beast / Relic / Vessel / Praxis / Event / Substance" -- ten classes, three
of them beings (`INSTRUMENT_CLASSES`). Of the seven non-being classes, only World/Polity/Event
have a specific noun in `_NOT_A_BEING`; Relic, Vessel, Praxis and Substance fall through to the
hard-coded default `"things"` (`generate.py:636`: `next((v for k, v in _NOT_A_BEING.items() if k
in cls), "things")`). This does not affect the gate's pass/fail decision -- `instrument_shortfall`
only checks for the `▣`/"Instrument" marker plus the "not applicable" phrase, not which noun
follows "not" -- so it is a cosmetic completeness gap in the synthesized sentence ("Not applicable
-- the Instrument measures beings, not things" for a Relic or Vessel entry, instead of a more
specific noun), not a defect. Filed as a QUESTION/nit rather than a finding.

## Modules read but not separately findable against

magnitude.py, scout.py, thread_integrity.py, anchors.py and catalogue_models.py were read in full
and checked by hand against the same categories (fail-open branches, tautological checks, caps/
truncations, comment-vs-code mismatches, regex/escape corruption, silent exception swallowing,
dead code claimed live). All five carry the same density of prior-fix commentary this project's
other audited files do (magnitude.py's five numbered guards, scout.py's ledger CAS discipline,
thread_integrity.py's DANGLING/asymmetric classification, anchors.py's graded invariants,
catalogue_models.py's LISTED/EMPTY_LIST/UNREACHABLE/UNCONFIGURED four-way outcome). Specifically
re-verified and found sound: magnitude.py's `_ask`/pool-then-local fallback ladder and the
`evidence_dropped_to_fit` field (confirmed always 0 today because `compose()` is called with
`budget=None` in `assay_entity`, matching its own comment); scout.py's `_mutate`/`_stamp`/
`_unstamp` rotation-preserving CAS logic; thread_integrity.py's `(b,a) in seen` dedup and its
`load_thread_graph` address-resolution loop; anchors.py's `vals`/`refused` split and its five
per-anchor CLAIMS table; catalogue_models.py's LISTED-vs-EMPTY_LIST-vs-UNREACHABLE accounting into
`stale`/`unverified`/`verified`. No new tautology, fail-open gate, uncommented truncation, wrong-
variable bug, or comment/code mismatch was found in any of the five beyond what is already
recorded in their own inline order-history comments.
