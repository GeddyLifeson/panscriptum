# SWEEP 38 — AUDIT, BATCH 13

`found_by: sweep38-batch13` · run38 · 8 modules, 4,473 lines · all eight read in full.

Environment: `C:/Users/imarl/miniconda3/python.exe`, `PYTHONIOENCODING=utf-8`, cwd = kit root.
Scratch: `…/scratchpad/sweep38/batch13/` (`v1.py`, `v2.py`, `v3.py`, `file_orders.py`).
No file under `src/` was modified.

Ten orders filed:

| id | code | sev | handler |
|---|---|---|---|
| 72aa074235d6 | ASSAY_INSTRUMENT_SENTINEL_TYPEERROR | MINOR | RUN |
| d444e7a90cff | RIGOR_DOCSTRING_FACULTIES_ZERO | MINOR | LOCAL |
| 52c99c58c50d | RIGOR_MAIN_LOADBEARING_TRUNCATED | MINOR | LOCAL |
| b422c125e93e | WITHDRAW_CHAPTERS_RC_ALWAYS_ZERO | MINOR | LOCAL |
| b54fbcf84962 | GPU_LANE_MAX_SLOTS_IMPORT_RAISE | MINOR | LOCAL |
| b9ff8dbf2c77 | PROFILE_MAIN_RC_IGNORES_ROUNDTRIP | MINOR | LOCAL |
| b2ca6e962383 | PROFILE_DOCSTRING_88BIT_SHELFMARK | INFO | LOCAL |
| 0b43bb663c36 | HOSTS_PER_SOURCE_SLICES_COMBINED_LIST | INFO | LOCAL |
| 5c06839ed0e3 | ASSAY_SWEEP_COUNT_DRIFTED | INFO | LOCAL |
| be9e9f089d62 | ADDRESS_SPACE_SHELFMARK_DROPS_STAR | INFO | OWNER (question) |

---

## assay.py (1,291 lines) — read in full

### FILED — 72aa074235d6, MINOR, RUN — `instrument()` crashes on the sentinels `_check_scores` admits

`_check_scores` deliberately passes `NONE` / `INAPPLICABLE` / `UNESTIMABLE` / `None` through
(`:484`). `instrument()`'s faculty loop handles only `None`. Reproduced live:

```
instrument("M4", {"continuity": "n/a", "sustain": 5.0}, worksheet="w")
    -> TypeError: can only concatenate str (not "float") to str
instrument("M4", {"ruin": "unestimable"}, worksheet="w")
    -> TypeError: unsupported operand type(s) for /: 'str' and 'float'
instrument("M4", {"celerity": "none"}, worksheet="w")
    -> TypeError: unsupported operand type(s) for /: 'str' and 'float'
assay("M4", {"continuity": "n/a", "sustain": 5.0}, worksheet="w")
    -> 𝔄 M4.50 ± 0.23        (clean, same input)
```

The single in-tree caller, `anchors.py:186-188`, pre-filters to numerics — which is why nothing
had caught it, and which makes the "numeric score dict" precondition at `assay.py:1087-1091` an
unstated, unenforced one. Order 5f99aa19c059 added the `_check_scores` call to this door on the
ground that "a gate on one of two doors is not a gate"; the gate now admits at both doors and
only one door can compute.

### FILED — 5c06839ed0e3, INFO, LOCAL — the "~800 iterations" figure has drifted to 649

Replayed the loop bounds against the live constants: start 0.5, stop
`min(SIGMA_MAX=3.7444, saved+2.0=3.7973)`, step 0.005 → **649**. Quoted as `~800` at both `:638`
and `:865`, in both cases as evidence for a design decision. Presumably predates `SIGMA_MAX`
being rebound to the Disputed grade at `:416`, which is what now binds the upper end.
Same order notes that `AXIS_MIN + 0.5` at `:641` borrows an axis-score constant as a sigma floor.

### VERIFIED SOUND — not filed

* `calibration_report()` re-derives the charter, live: interval **0.12** vs want 0.12, decimal
  **0.52** vs want 0.52, `holds=True`, `margin=0.997`. The margin is near the middle of the
  reproducing band, which is exactly the property the comment at `:626-628` asks for.
* `_check_constants()` runs at import; monotonicity and both ceiling branches confirmed present
  and confirmed non-tautological by the argument at `:580-586` (they watch edits to `SIGMA_MAX`
  and `SIGMA_UNKNOWN`, not to `_RAW_SIGMA`). Do not re-file these as dead.
* `_check_weights` / `_check_scores` / the `wsum <= 0.0` refusal / the `or 1.0` backstop at
  `:952` — the `or 1.0` is honestly labelled as no-longer-reachable and kept as a structural
  backstop with the reasoning written out. Correct as it stands; the note at `:943-951` already
  forbids citing it as reachable, and this audit does not.
* Decimal clamped at BOTH ends with `at_ladder_ceiling` / `promotion_due` / `at_ladder_floor` /
  `demotion_due` flags; `moth_number` carries the tag. No silent clamp.
* `_rho_doc()`'s fallback: broad `except Exception` but it records the cause on
  `RHO_FALLBACK_REASON`, prints to stderr once, and stamps `correlation_source` on every assay.
  That is an announced degradation, not a swallow.
* `band_for_quantity(1.0, "ruin")` returns `"M0"` for a quantity below the M0 floor, which reads
  like a docstring mismatch — **checked and it is deliberate**: `verify_math.py:5470` asserts
  "a quantity beneath the ladder's own floor sits at M0" explicitly. Not filed.
* `axis_score()` saturating at 9.9 for M10 is already tracked as open bug M18 (`:316-317`).
  Not re-filed.
* `interval_from_hands()`'s `covers_all_signatures` is True by construction after the widening
  loop. Considered as a "check that cannot fail" — but it is a *reported invariant* of a loop
  three lines above it, not a test, and the Vade Mecum countersign check (III.4) is what reads
  it. Not filed.
* `_BAD_CHARS` self-check present and passing.

---

## rigor.py (918 lines) — read in full

### FILED — d444e7a90cff, MINOR, LOCAL — module docstring still asserts the faculties are weighted zero

The docstring (`:8-16`, `:50-53`) states in the present tense:
`FACULTY_WEIGHTS acumen 0.0, discernment 0.0, suasion 0.0` … "**The faculties are weighted
zero.**" … "k = 0, the rate currently in force". Measured live:

```
assay.FACULTY_WEIGHTS = {'acumen': 0.0909…, 'discernment': 0.0909…, 'suasion': 0.0909…}
assay.WEIGHTS['ruin'] = 0.14545…      sum(assay.WEIGHTS.values()) = 1.0
```

Both quoted numbers are wrong (`ruin 0.20` is the pre-scaling charter proportion; the live weight
is 0.145 after the 8/11 block scaling). The **body** of this same file was repaired for exactly
this — `:771-784` derives `_muted` from the live table and now prints "FINDING: none … Closed by
assay.py's ERRATUM (X.11)". So the module opens by asserting the defect and closes by reporting
it closed.

### FILED — 52c99c58c50d, MINOR, LOCAL — `main()` prints 6 of 75 load-bearing quantities, cutting mid-tie

`mathematical_resonance()['load_bearing']` has **75** entries; `main():911` prints `[:6]` with no
count. 26 of the hidden 69 have fanout ≥ 2. The 7th, `('name_surprisal', 4)`, **ties** the four
printed entries at fanout 4 — so the report shows five quantities at fanout 4 where six qualify.
The returned field is correctly uncapped and the comment at `:743-745` says why; the truncation
just moved one line downstream into the "sole consumer" it names.

### VERIFIED SOUND — not filed

* `bradley_terry()`'s Ford refusal: `identified` is computed from the RAW wins even when a prior
  is supplied, `observed` is kept separate so the undefeated/winless report is about real data,
  and both refusal paths null out `strengths`. The `prior > 0` branch returns `refusal: None` with
  a `caveat` naming the component count. The success path sets no `refusal` key at all — checked
  every caller (`chain.py:117`, `chain.py:664`, `verify_math.py:425`) and all use `.get`.
  Not a fault.
* `main()` sections 1 and 3 both derive their FINDING from the loop's own data (`_muted`,
  `_underpriced`) rather than printing a fixed verdict. Ran the file end to end: MDL table prints
  five rows all above floor, mean ratio 3.12; Jensen gap section reproduces
  P(alone) = 0.3331 on the Milky Way case.
* `adjudication_beta`'s five-row/six-adjudication asymmetry is explained at `:813-820` (A4 has no
  exception to price). Confirmed deliberate.
* `_strongly_connected` is an iterative Tarjan with the recursion reason stated; `_log2_choose`
  via `lgamma`; `lognormal_product` adds covariance terms. No caps anywhere in the returns.

Noted but not filed: `perron_weights` falls back to `SAATY_RI.get(n, 1.6)` for n > 15 with no
marker — a magic default, but it is a diagnostic index on a matrix nothing in this tree builds
above n=11, and inventing a finding there would be noise.

---

## gpu_lane.py (573 lines) — read in full

### FILED — b54fbcf84962, MINOR, LOCAL — `MAX_SLOTS` can raise at import, in the fail-open module

```
OLLAMA_NUM_PARALLEL=auto  python -c "import gpu_lane"
    -> ValueError: invalid literal for int() with base 10: 'auto'
OLLAMA_NUM_PARALLEL=4     python -c "import gpu_lane; print(gpu_lane.MAX_SLOTS)"   -> 4
```

An ImportError here takes down `lane()` for all nine standing jobs at once — strictly worse than
the unarbitrated lane the module explicitly accepts at `:349` and `:510-518`, and a direct
contradiction of the header's "FAIL OPEN, ALWAYS … a bug in it must never be able to stop the
library from working". The quieter half of the same line: `OLLAMA_NUM_PARALLEL=0` is the daemon's
own *auto* value and `max(1, 0)` silently reads it as one slot — the serialisation the comment at
`:59-60` says two slots exist to prevent, arriving with no signal.

### VERIFIED SOUND — not filed

* `_alive()`'s Windows `OpenProcess` path, including the `GetExitCodeProcess` follow-up and the
  unknown→alive policy, matches its docstring exactly (this was a comment-vs-code fault once and
  is not one now).
* `_take_slot()`'s three-answer contract (`path` / `False` busy / `None` unarbitrable) is honoured
  by `lane()`'s queue loop at `:506-519`, and both falsy answers survive every `if slot:` test in
  the `finally`.
* `_touch()` refuses to resurrect a released or foreign slot; the heartbeat is stopped before
  release; `_heartbeat` keeps the slot AND the foreground claim on one beat; `_BEAT_SECONDS` is
  derived from `min(SLOT_LEASE, CLAIM_LEASE)/3`.
* `_write_claim`'s verdict is returned and the entry claim's denial is noted to `silence`; the
  decrement's non-escalation is argued at `:265-269` and the argument holds (a depth left high
  errs toward yielding).
* `status()` enumerates every holder with no cap and skips `.tmp` files.
* `_DEPTH_LOCK` is held across the file write and released before the `yield`, as documented.

Noted but not filed: `except Exception: raise` at `:533-534` is a no-op clause; and `_expired()`
would propagate a `ValueError` out of `lane()` if a claim record carried a non-numeric
`heartbeat` (a dict that parses as JSON but has a string beat). Both are real but the second
requires a hand-crafted file that no writer in this module can produce, and the first is inert —
filing either would be noise against the module's genuine faults.

---

## address_space.py (486 lines) — read in full

### FILED — be9e9f089d62, INFO, OWNER — **QUESTION**: `shelfmark()` silently drops the `star` field

`FIELDS` has eight entries; `shelfmark()` prints seven. Demonstrated with two addresses differing
only in `star`:

```
star=11   -> 49570754757658962525421591
star=999  -> 49570754757658962525423567     (different addresses)
both      -> "Ω › H1 › X1 › Mt.1 › Mv.1 › U-1 › G.7 › P.1"   (identical shelfmark)
```

27 of 88 bits are discarded by the printed name. **Two readings**, and the first is my leading
one: the charter's own worked Shelfmark (quoted at `:98`) has seven tiers below Ω and no star, so
this is charter fidelity and the only work is documentary. Against that, the module's title is
"one fixed-width name for every planet", `seed_from_card()` keys the generator seed on the
shelfmark (so two worlds around different stars in one galaxy get the same terrain, where
`map_seed(addr)` would separate them), and `main()`'s collision counter counts addresses rather
than shelfmarks so it cannot see this class. **Not an active fault**: data/SHELFMARKS.json holds
1,016 rows with 1,016 unique addresses *and* 1,016 unique shelfmarks.

### VERIFIED SOUND — not filed

* Live widths: `hyperverse 3, xenoverse 2, metaverse 3, multiverse 8, universe 6, galaxy 38,
  star 27, planet 1` → `TOTAL_BITS = 88`. The docstring genuinely carries no transcribed number,
  as `:32-45` promises.
* `_hash_offsets()` derives from `WIDTHS` with the legacy 8/48/78 as a floor; verified the three
  slices do not overlap today (universe 0-5, galaxy 8-45, star 48-74, planet 78) and cannot as the
  census grows, since each offset is `max(running_total, legacy)`.
* `HASH_BYTES` derived from the span with a hard `> 32` refusal at import.
* `assign()`'s `fit` no longer wraps with `%` — an over-large tier now reaches `pack()`, which
  names the field and width. `main()`'s round-trip `assert` and its keyword-only `pack(**fields)`
  call both hold.
* `main()` returns 1 on a denied `SHELFMARKS.json` write, with the reasoning written out at
  `:455-466`. This is the precedent cited in the `withdraw_chapters` order.
* `main()`'s `list(addrs.items())[:6]` sample display is preceded by `worlds addressed : 1,016`,
  so the reader is told the size. Not filed as a cap.

---

## withdraw_chapters.py (398 lines) — read in full

### FILED — b422c125e93e, MINOR, LOCAL — every refusal prints and the process still exits 0

`main()` has no `return` on any path and the entry point is a bare `main()`, so rc is always 0 —
including when `catalog_landed` is False ("CATALOG WRITE DENIED … still lists the paths just moved
away"), when `record_landed` is False (the archive left with no manifest, explicitly noted as
non-reproducible by a re-run), and when `stuck` / `unreadable` / `collided` / `stray_stuck` are
non-empty. Console output is not the machine-readable channel for a `--go` tool. The sibling
module in this same batch (`address_space.py:480`) returns 1 for the identical condition with the
argument written out.

### VERIFIED SOUND — not filed

* `select()` is pure and exact-match; the per-selector unknown check at `:175-188` catches an
  `--addr` typo *alongside* a matching `--source`, which the previous per-run version did not.
* `_file_state()` distinguishes live / gone / unavailable and keeps the record on unavailable —
  the `os.path.exists`-swallows-OSError trap is properly closed.
* `_archive_name_free()` treats only `FileNotFoundError` as free; the collision guard is applied
  to both the catalogued moves and the stray sweep.
* The snapshot is taken **and verified** before the first move, and a failed verify raises.
* The catalog is edited rather than erased; entries whose files did not move keep their record;
  partial entries are amended to point at the archive; both writes go through
  `silence.write_json`.
* `--label` defaults to today's date rather than a baked-in one.
* Every summary list (`stuck`, `unreadable`, `collided`, `amended`, `stray_stuck`) is printed
  uncapped, with the unit named in each label. No Hard Rule 0 issue anywhere in this file.

---

## runguard.py (303 lines) — read in full, nothing found

The tightest module in the batch. Checked in detail and found correct:

* The one-line invariant ("a run may only ever refresh, or close, a record that carries its own
  name") is enforced in both `beat()` and `release()`, and both refuse loudly on a foreign or
  already-closed record.
* All three writers go through `_land_claim` → `silence.replace_if_unchanged`, i.e. a real CAS,
  with the temp name carrying pid **and** thread ident.
* **Digest-before-read** in `claim()`, `beat()` and `release()`. Traced the argument through
  `silence.digest_of` (`:308-315`) and `silence.replace_if_unchanged` (`:318-359`): a competitor
  landing in the gap leaves us holding the older digest, and the swap refuses — the safe
  direction, exactly as the comment claims.
* The absent-vs-unreadable case resolves correctly. `digest_of` returns `None` for both, but
  `replace_if_unchanged` re-checks with `_digest_or_unreadable` and refuses on `UNREADABLE`, so a
  guard file that exists but cannot be read fails the claim closed rather than being overwritten.
* The read path's deliberate fail-open (a corrupt guard reads as "free") is documented at `:56-58`
  with the reason — refusing would wedge the pass permanently on a file nothing else repairs —
  and is consistent with `holder_is_live()` returning False for a non-numeric heartbeat.
* `_land` is gone rather than kept beside `_land_claim`, and its history is recorded in prose.
* `main()` returns 2 / 1 / 0 appropriately and the entry point is `sys.exit(main())`.

**Read in full, nothing found.**

---

## hosts.py (282 lines) — read in full

### FILED — 0b43bb663c36, INFO, LOCAL — `cands[:per_source]` slices the combined list, and the invariant is unenforced

The comment at `:174-177` asserts the cap "sits AFTER the evidence, never through it". I measured
the whole roll rather than trusting it — replicating `hostcheck.candidates`' grounded/speculative
split exactly and asserting `grounded + spec` equals its real output for every source:

```
sources measured (in WIKI_HOSTS, with a roster) : 189
longest candidate list                          : 75   (DMs Guild: Xanathar's Lost Notes…)
largest GROUNDED prefix                         : 15   (same source)
sources whose grounded prefix exceeds 24        :  0
grounded hosts dropped by the cap               :  0
speculative hosts dropped by the cap            : 615
```

**The comment is true today** — filed as INFO, an unenforced precondition with nine hosts of
headroom, not a live Hard Rule 0 breach. It is worth closing because the grounded list is
unbounded: it includes every neighbour host whose roster shares `max(3, 25%)` of this source's
names (`hostcheck.py:449-460`, an unbounded loop over all 193 sources), and the D&D shelf already
tops the table. `hostcheck.py:408-418` records the last time this exact slice ate a grounded host.

### VERIFIED SOUND — not filed

* `add()`'s three-state return (`True` / `False` / `None`) is real, and `discover()` is the caller
  that distinguishes them — a denied write is collected into `lost`, written to stderr naming
  every lost host, and escalated via `silence.note`. This is the opposite of green-by-absence and
  is the strongest thing in the file.
* `work()` uses the **whole** roster to score a host, with the `[:40]` removal and its reason
  recorded at `:161-164`.
* The secondary-host bar (`MIN_HITS_SECONDARY` / `MIN_ABOUT_SECONDARY`) is argued from a measured
  Bleach/Wikipedia case, and `specialist or substantial` genuinely admits both routes.
* `hosts_for()` returns primary followed by every extra, deduped, uncapped.

Noted but not filed: `main()`'s discover table prints `str(src)[:39]` for column alignment (a name
truncation in a two-column report, not a list cut); and `add()` is a read-modify-write of
`SOURCE_HOSTS.json` without a CAS. The latter I looked at hard, since `silence.replace_if_unchanged`
exists and `runguard` uses it for exactly this shape — but `discover()` calls `add()` only from the
main thread as it consumes `ex.map` results, so there is no intra-run race, and the cross-process
case needs two concurrent `--discover` walks. Below the bar for an order; recording it here so the
next reader does not have to re-derive it.

---

## profile.py (222 lines) — read in full

### FILED — b9ff8dbf2c77, MINOR, LOCAL — the round-trip verdict is printed and discarded

`main()` counts `bad`, prints `failures: {bad}`, and returns 0 regardless (`:208`, `:218`). The
check itself is good and was deliberately repaired (`:199-203` records that the old version
compared `d["profile"]` with itself and could never fail) — but a check whose failure changes
nothing is one step from a check that cannot fail. Same order flags the empty-`rows` case at
`:175-179`, where `min(lens)` and `sum(lens)/len(lens)` raise before anything else runs.

### FILED — b2ca6e962383, INFO, LOCAL — "the 88-bit shelfmark in base32"

Two problems in `:20`, one latent. The base32 field is the **address** integer, not the
**shelfmark** — `decode()` returns those as two separate keys (`:116-118`). And 88 is a hand-copied
width: `AS.TOTAL_BITS` is 88 today so the number is *correct as of now*, but `address_space.py:32-45`
exists almost entirely to say that no other file may state it ("It was 74, then 89; it moves
whenever TIERS.json is re-charted … THIS TABLE WENT STALE ONCE AND MUST NOT AGAIN"). It was removed
from address_space.py for that reason; profile.py is the remaining copy.

### VERIFIED SOUND — not filed

* `B32` is 32 symbols and the encoder mask (`n & 31`) and decoder now agree; `u` is reserved
  unambiguously for the unassayed band. Confirmed the alphabet excludes `i l o u`.
* `decode()`'s `zip(..., strict=True)` will not silently pair short.
* The `rows[:8]` block is explicitly headed `SAMPLE` and follows a printed total.

Noted but not filed: `decode()`'s regex admits `i l o u` in the address and feature groups, so a
profile carrying a stray excluded letter raises `ValueError: substring not found` from
`B32.index` rather than the clean `not a world profile` refusal. It *does* raise, which is the
property the `B32` comment cares about ("an alphabet that can read what it cannot write is a
decoder that cannot say 'this is not one of mine'"), so the invariant holds and only the error
message is poor. Tightening the two character classes to `[0-9a-hjkmnp-tv-z]` would be a one-line
improvement if someone is in the file for the docstring fix.

---

## COVERAGE

`sweep_plan.record('run38', [...], batch=13)` — all eight modules, each read line-by-line in full,
none sampled:

`assay.py`, `rigor.py`, `gpu_lane.py`, `address_space.py`, `withdraw_chapters.py`, `runguard.py`,
`hosts.py`, `profile.py`.
