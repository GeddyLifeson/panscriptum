# AUDIT — sweep run55, batch 08

Modules read in full, line by line: `workorders.py`, `liveness.py`, `wiki_source.py`,
`address_space.py`, `canon_backup.py`, `recover_folder_records.py`, `grounding.py`, `profile.py`.

Method, per module, is stated under each heading. Nothing under `src/`, `data/`, `state/` or any
ledger was written. Two live measurements were taken by driving pure functions from a scratch
script outside the repo (`liveness.scan()`, `citecheck.stale_citations()` with `silence.note`
shimmed out) and by reading `data/TIERS.json`, `data/WORLDSEEDS.json`, `data/SHELFMARKS.json`,
`data/SWEEP_ROLL.json`, `data/CONTINUITY_GROUPS.json`,
`reference/keystone_volumes/LOCAL_REGISTER.json` and
`reference/pipeline_tooling/FOLDER_SOURCE_MAP.json` directly. No module that writes into `data/`
or `state/` was executed — `address_space.main()`, `grounding.main(--write)` and
`profile.main()` were read, not run.

Where a citation points at a file outside this batch it is named as such and the verification is
stated (`pipeline.py`, `standards.py`, `local_agent.py`, `drill.py`, `escalation.py`,
`publish.py`, `cleanup.py`, `coverage.py`, `catalogue_web.py`, `citecheck.py`).

---

## workorders.py

Read every line of all 2,139. Traced `_load` / `_mutate`'s compare-and-swap, `file_order`'s
door-check, `resolve` / `resolve_code` / `reroute`'s three return dispositions and `main()`'s
land-then-exist ordering, then walked every one of the twelve `_fire` call sites in
`sweep_detectors` and checked its predicate's polarity by hand against the thing it watches.

**The `_fire(ok, ...)` polarity is CORRECT at all twelve sites.** Checked individually:
`not bad` (1216), `chain_ok` (1220), `n <= _D.LIVENESS_CEILING` (1234),
`bh_age <= BINDING_HEALTH_MAX_AGE` (1300), `not hits` (1421), `f is None` (1456, inside a
four-iteration loop over `BATTERY_CODES`), `not stranded` (1509), `not scratch` (1608),
`not _cap["open_hits"]` (1651), `not _ghosts` (1704), `not _stuck` (1764), `not _cites` (1816).
Every one is TRUE when the watched thing is healthy, which is the contract `_fire`'s own comment
states. The new section 12 is on the right side of it.

I also chased the natural suspicion about section 4 and section 6 and it does NOT hold:
`resolve_code("SECRET_IN_EXPORT", ...)` (1428) and `resolve_code("DRILL_BREACH", ...)` (1481)
both default `where=""`, and the matching filings go through `escalation.escalate`, which files
`where=rec.get("source") or ""` (escalation.py:338) from callers that pass no `source=`
(publish.py:1598, drill.py:17640). The identities match; those two closes land. Recorded because
it looks like the `order_id` trap and is not one. (Cross-batch verification: escalation.py,
publish.py and drill.py are not in batch 08; established by reading the three call sites.)

### MAJOR — the new STALE_CITATION order is filed at LOCAL with `where=""`, so four of its ten findings are structurally unreachable by LOCAL and neither guard against that can see it

**Where:** src/workorders.py:1816-1825 (the `_fire` call), src/workorders.py:512-525
(`file_order`'s door-check), src/workorders.py:1749-1786 (the post-hoc detector).

**What:** section 12 calls

```
_fire(not _cites, "STALE_CITATION", "...", "LOCAL", "MINOR",
      found_by="citecheck.stale_citations", evidence={"citations": _cite_rows})
```

with **no `where=` argument**, so the order is filed under `where=""`. That empty string defeats
both mechanisms this module has for catching a LOCAL order the LOCAL rung cannot work:

* `file_order`'s door-check runs `WHERE_TARGET.findall(str(where or ""))` and only re-addresses
  to RUN `if targets and all(_LA._denied_target(t) ...)`. With `where=""` there are no targets,
  so `targets` is falsy and the re-address never fires.
* `sweep_detectors`'s `ORDER_ADDRESSED_TO_A_RUNG_THAT_CANNOT_REACH_IT` (1756-1760) explicitly
  `continue`s when `where` names no module: *"No module named in `where` at all -- this detector
  has nothing to say."*

**Why it is wrong:** the order's contents are per-module and four of them name modules on
`local_agent.DENYLIST`. Measured now by driving `citecheck.stale_citations()` read-only — ten
findings, citing files `chain.py`, `cosmology_graph.py`, `handbuilt.py`, `ledger.py`,
**`overnight.py`**, **`pipeline.py`**, **`prose_gate.py`**, `scope.py`, **`verify_math.py`**.
All four bolded are in `DENYLIST` (src/local_agent.py:65-124; cross-batch, read directly).
`_fire` resolves this order only on `not _cites` — i.e. only when ALL TEN are repaired. LOCAL is
structurally forbidden to write four of them, so the order can never self-close by the route the
detector's own comment promises, and it sits at the cheap rung reading as work waiting to be
picked up. That is precisely the failure `ORDER_ADDRESSED_TO_A_RUNG_THAT_CANNOT_REACH_IT` was
written for, arriving through the one shape that detector declines to look at.

**Confidence:** high. The order is live: `state/workorders.json` holds `d7efd67caa6f`, code
`STALE_CITATION`, handler `LOCAL`, `where` `''`, `seen: 1`, `what` opening "10 `file.py:NNN`
citation(s)…". Read the queue, drove `stale_citations()` in a scratch process with `silence`
shimmed so nothing could reach `state/failures.json`, and read `local_agent.DENYLIST` and both
guard sites in source.

**Not a fix, a report.** Whether the remedy is a per-citing-file `where` (one order per file, at
the rung that can reach it), a fixed non-empty `where` plus a RUN rung, or leaving it as one
LOCAL order and accepting the residue, is a routing judgment — the same judgment `reroute()`'s
docstring says is "not made here".

### MINOR — `_fire`'s own comment says "eleven call sites below"; there are twelve

**Where:** src/workorders.py:1132-1133.

**What:** *"the two arms were the other way round, and every one of the eleven call sites below
passes a predicate that is TRUE when the thing it watches is FINE"*.

**Why it is wrong:** `grep -n "_fire(" src/workorders.py` returns twelve calls (1216, 1220, 1234,
1300, 1421, 1456, 1509, 1608, 1651, 1704, 1764, 1816). Section 12 added the twelfth and the
count was not moved. This is the exact shape CLAUDE.md Hard Rule -1 records correcting in
`drill.py` under order 864a626a258e — *"a count in doctrine goes stale weekly and then gets
reasoned from"* — and the sentence it sits in is the one a reader consults to decide whether a
new detector is on the right side of the polarity. Harmless today; it is the enumeration that
rots, not the rule.

**Confidence:** high, counted from grep and confirmed by reading each site.

### MINOR — `where=""` puts STALE_CITATION permanently in the twin check's blind spot

**Where:** src/workorders.py:1816 (no `where`), src/workorders.py:853-858 and 2028-2032
(`twins()` / `--twins`).

**What:** `where_targets("")` returns two empty lists, so `twins()` files the order under
`no_file_in_where`, which its own report line calls *"ungroupable, and invisible to any twin
check"*.

**Why it is wrong:** `STALE_CITATION` is a multi-file class, and the queue's existing
hand-filed citation orders (44's, 48's `89503c58409f`, 54's `386c0d66e31e`) are exactly the
twins `twins()` exists to surface. This one cannot cluster with any of them. Measured: 2 of the
71 open orders carry an empty `where`, and this is one of them.

**Confidence:** high — read `where_targets` and `twins`, and counted the live queue.

### INFO — the detector section numbering is now decorative

**Where:** src/workorders.py:1200, 1229, 1241, 1263, 1383, 1437, 1464, then five unnumbered
blocks (1488, 1531, 1636, 1675, 1731), then src/workorders.py:1788 `# 12. STALE CITATIONS`.

**What:** the run of numbers is 1, 2, 3, 3b, 4, 5, 6, then five blocks with no number, then 12.
"12" is correct only if the five unnumbered blocks are counted 7-11, which nothing says.

**Why it is minor:** nothing reads the numbers. Noted because a reader looking for sections 7-11
will not find them.

**Confidence:** read every section header in the function.

---

## liveness.py

Read all 1,054 lines. Traced `_modules` → `_parse` → the three usage bags (`used`,
`used_local`, `used_by_module`) → `scoped` → the five passes, then `reachability()`'s four
subprocess gates. Ran `liveness.scan()` read-only (pure AST, writes nothing) to compare the
docstring's recorded measurements against the live tree: **48 findings today (dead 39,
dead_module 9, dead_class 0, tautology 0, phantom 0, unparsed 0) against
`drill.LIVENESS_CEILING = 52`.**

### MINOR — the module docstring says the dead-module limb "is NOT here yet"; `scan()` says it landed, and it is returning nine rows

**Where:** src/liveness.py:29-30 against src/liveness.py:351.

**What:** the header reads *"(order 209391b4f990; the module limb of that order, a module nothing
imports, is NOT here yet -- see `scan()`.)"* while `scan()`'s own docstring opens *"THE MODULE
PASS IS NOW HERE (order 209391b4f990, landed 2026-08-29 with the ceiling raise it needed)"*.

**Why it is wrong:** the two sentences in one file assert opposite things about the same order,
and the header is the half a reader meets first. Live `scan()` returns nine `dead_module` rows,
so the limb is not merely present, it is firing. This is the module whose subject is a check that
cannot fail; a header saying its newest limb does not exist is the documentation form of that.

**Confidence:** high — read both docstrings, ran `scan()`, counted nine `dead_module` rows.

### MINOR — "This finds the three mechanical shapes" introduces four, and `scan()` returns six kinds

**Where:** src/liveness.py:19-34 against src/liveness.py:746-749.

**What:** *"This finds the three mechanical shapes:"* then DEAD, DEAD CLASS, TAUTOLOGY, PHANTOM.
`scan()` returns `dead`, `dead_class`, `dead_module`, `tautology`, `phantom`, `unparsed`.

**Why it is wrong:** same class as the item above — a count in prose that two subsequent limbs
(`dead_module`, `unparsed`) walked past. `main()`'s `KINDS` tuple has all six and is the thing
that cannot drift; the docstring is not.

**Confidence:** high, both sites read.

### MINOR — `reachability()`'s docstring carries the corrected-elsewhere "57 nets" figure

**Where:** src/liveness.py:772.

**What:** *"`drill.py`'s 57 nets are NOT included: running them is restricted to the agent that
owns the drill"*.

**Why it is wrong:** CLAUDE.md's PROVEN paragraph records this exact figure being struck out —
*"This line read 'all 57 nets' from run #14 until 2026-09-08 while the real figure went 269 → 394
→ 433 → 455 `net(` call sites… Corrected under the owner ruling of 2026-09-08, question 18, order
`864a626a258e`."* `grep -c "net(" src/drill.py` returns **522** today. The correction was applied
to the doctrine and to `drill.py` and not propagated here, so the figure the owner ruled against
is still standing in the module `drill.py` ratchets. The argument the sentence makes (that the
drill's nets are excluded from this pass) is unaffected and correct; only the number is wrong.

**Confidence:** high — grepped `drill.py`, read CLAUDE.md's paragraph, and confirmed
`src/liveness.py:772` is the only remaining "57 nets" site in `src/` apart from two in
`dashboard.py:629-630` which use it as an illustrative sentence rather than a claim about
drill.py's size.

### MINOR — the docstring's `profile.py:196-208` citation has rotted, and citecheck cannot catch it

**Where:** src/liveness.py:7-9. Target in batch: src/profile.py.

**What:** *"`profile.py`'s round trip -- FIXED, now at `profile.py:196-208`: … It now re-encodes
what `decode()` extracted and compares THAT."*

**Why it is wrong:** `profile.py:196-208` is inside `build_all()` — line 196 is
`silence.note("profile.py:genres-unreadable")`, 203 is `out = []`, 208 is
`register = gspec.get("register", "classical")`. The re-encoding round trip is at
**profile.py:260-272**. The claim is true; the address is not. Worth naming because it is the
clean demonstration of `citecheck`'s stated limit: `profile.py:196` is a non-blank, non-bracket
line, so `stale_citations()` calls it CLEAN and the new STALE_CITATION detector will never see
it. `citecheck`'s docstring is explicit that CLEAN means "not provably broken", and this is what
that costs.

**Confidence:** high — read profile.py:196-208 and profile.py:260-272, and confirmed
`stale_citations()` does not return this site.

### INFO — the ten never-imported modules named in `scan()`'s docstring are now nine, and a different nine

**Where:** src/liveness.py:358-363.

**What:** *"TEN modules are never imported or named by any other module -- chord_field,
descending_ladder, halo, handbuilt, module_index, pantheon, render, scale_theories, wh40k,
zfighters"*.

**Why it is noted, not filed as a defect:** live `scan()` returns nine — `descending_ladder`,
**`events`**, `halo`, `handbuilt`, `module_index`, `pantheon`, `scale_theories`, `wh40k`,
`zfighters`. `chord_field` and `render` are now reached; `events.py` is not and was not on the
list. A dated measurement drifting is not itself a fault, but this one is written in the present
tense and names the tree rather than a date.

**Confidence:** high — ran `scan()` and diffed the two lists.

### INFO — the receiver-aware pass's recorded landing figure (49) is 48 today

**Where:** src/liveness.py:413-415 (*"findings before this pass 48 … the receiver-aware pass,
measured LANDED +1 -- landing at 49, three points left"*).

**Why it is noted:** live total is 48 against ceiling 52, so there are four points of headroom,
not three. The reasoning the block exists to record (the pass landed inside existing headroom,
no ceiling move) is unaffected.

**Confidence:** ran `scan()`, read `drill.LIVENESS_CEILING = 52` at drill.py:313 (cross-batch,
read directly).

### INFO — two exemption tables are empty, so two conjuncts cannot fire; both are marked

**Where:** src/liveness.py:98 (`EXEMPT_MODULES = {}`) used at 599; src/liveness.py:114
(`EXEMPT_CLASSES = {}`) used at 616.

**What:** `_stem(n) not in EXEMPT_MODULES` is always True and `if cls in EXEMPT_CLASSES: continue`
never fires.

**Why it is not filed:** both carry an owner-ruling marking with a written reason (orders
e3451d1e056d and 962bc293ec32) explaining that empty is the correct starting content and that a
separate table with its own reason is the point. Saw the marking; moving on.

### INFO — a broken sentence in `reachability()`'s docstring

**Where:** src/liveness.py:843-844.

**What:** *"…and only actually running the check answers that). A subprocess, not an\nEVERY STEP
RUNS AS A SUBPROCESS, INCLUDING THE ANALYSIS…"* — the clause "A subprocess, not an" ends
mid-phrase and a later heading has crashed into it.

**Why it is noted:** it reads as a lost edit rather than prose, and the sentence that was cut may
have carried a distinction (subprocess vs something) the block needed.

### INFO — a comment narrates in the present tense a defect the code no longer has

**Where:** src/liveness.py:548-551.

**What:** *"so the `if seen else set()` here could never take its `else` arm … A conditional that
cannot take one branch, left in the file whose whole subject is checks that cannot fail."* The
line below is `scoped[key] = set().union(*[self_attr[k][1] for k in seen])` — no conditional.

**Why it is noted:** the fix landed and the comment still reads as a live finding.

---

## wiki_source.py

Read all 789 lines. Traced `_get`'s retry/throttle, `resolve_wiki`'s hosts-map-first path,
the `all_categories` → `discover_categories` → `find_categories` chain and its floor, and the
four walkers that were converted to raise under order de0681cb9edc.

### MAJOR — `category_floor_report()` has no caller anywhere, and the account it reads is in-process only, so the owner ruling's "report the dropped count" half is declared but not in effect

**Where:** src/wiki_source.py:402-418 (the function), src/wiki_source.py:399 and 490-491
(`_FLOOR_APPLIED`, written), src/wiki_source.py:375-394 (the ruling it answers).

**What:** the constant's own comment states the ruling: *"order 4d78c426afb3; owner ruling
2026-09-08 … the 40-page MediaWiki category floor is declared and its dropped count reported"*,
and then: *"`category_floor_report` below reports what IS known -- the floor that was applied and
how many categories cleared it, per wiki."*

**Why it is wrong, two ways:**

1. Nothing calls it. `grep -rn "category_floor_report\|_FLOOR_APPLIED"` over the whole repo
   returns only its definition, its own two mentions in this file, and one line in
   `handoff/sweep48/AUDIT_batch13.md`. `liveness.scan()` independently reports
   `wiki_source.py:402 category_floor_report()` as DEAD. `catalogue_web.py` — the caller that
   drives `find_categories` — never asks for it. So the floor's effect is recorded into a dict
   and dropped on the floor.
2. Even if it were called, `_FLOOR_APPLIED` is a module-level dict populated only by
   `all_categories` in the *same process*. A separate `python src/wiki_source.py`-style
   invocation, or any process that did not itself walk a wiki, gets `{}` and therefore `[]` — an
   empty list, which reads as "the floor excluded nothing worth reporting" and is the
   absence-read-as-clean shape this module already refuses elsewhere (`all_categories`' "a
   failed walk RAISES; it is never returned as the answer").

This is Hard Rule -1's fourth property applied to a report rather than a guard: a safety that
exists in a file is not a safety that is running.

**Confidence:** high — grepped the repo for both names, confirmed independently by
`liveness.scan()`, and read `_FLOOR_APPLIED`'s only write site.

### MINOR — `rank_by_size` still swallows a transport failure while its three siblings were changed to raise

**Where:** src/wiki_source.py:731-737.

**What:**

```
def fetch(batch):
    try:
        return _api(subdomain, {...})
    except Exception:
        silence.note("wiki_source.py:rank-by-size-api")
        return {}
```

**Why it is wrong:** a failed batch contributes no `length` for its fifty titles, so
`sizes.get(t, 0)` scores every one of them zero and `sorted(titles, key=lambda t: -sizes.get(t, 0))`
sinks them to the bottom of the ranking. Hard Rule 0 permits ranking precisely so the richest
material lands first when a run is interrupted, which makes a silently corrupted ranking a real
loss of that property — and this is the one walker in the file that order de0681cb9edc did not
convert: `all_categories` (476-477), `category_members` (681-683) and `extracts` (708-710) all
note-then-`raise`, this one notes and returns `{}`. Not a truncation today: both call sites pass
`top=None` (`catalogue_web.py:288` and `:482`, cross-batch, read directly), so `ranked[:top] if
top else ranked` returns everything. It becomes a truncation the moment anything passes `top`.

**Confidence:** high — read all four handlers side by side and both call sites.

### MINOR — the floor account is keyed one field narrower than the cache it rides beside

**Where:** src/wiki_source.py:462 (`key = (subdomain, min_pages, hard_stop)`) against
src/wiki_source.py:490-491 (`_FLOOR_APPLIED[(subdomain, min_pages)] = len(out)`).

**What:** `hard_stop` was added to the cache key under order 83bf7498d135 *because* "a cache key
omitting an argument that changes the answer is a trap". The floor account was not given the same
treatment, and it is written unconditionally — including after a `hard_stop`-bounded walk, which
is deliberately not cached.

**Why it is wrong:** a bounded walk would overwrite the unbounded count with a smaller number,
and `category_floor_report` would then publish a truncated `categories_above_floor` as the
measurement. Dormant exactly as the cache-key case was: nothing in the tree passes `hard_stop`.

**Confidence:** high, read both sites.

### INFO — a comment names a symbol that does not exist

**Where:** src/wiki_source.py:289-292: *"this label was shared with the live category probe at
`category_probes` below"*. There is no `category_probes`; the constant is `CATEGORY_PROBES`
(334) and the probe loop is inside `find_categories` (538-547), where the label is now
`"wiki_source-category-probe"` (544). The fix the comment describes is in place; the pointer is
not.

### INFO — `zip(..., strict=True)` needs Python 3.10, against a stated 3.8 floor

**Where:** src/wiki_source.py:611-612 (and src/profile.py:163 uses the same keyword).

**What:** `zip(titles, pool.map(...), strict=True)`. `liveness.py:817` says *"`end_lineno`
(stdlib `ast`, present since the 3.8 floor this project already assumes)"*.

**Why it is noted, not filed:** the interpreter in use is 3.13 and the keyword is correct there;
the two modules simply disagree about what the floor is. A QUESTION for the owner rather than a
fix — if 3.10 is the real floor, `liveness.py`'s sentence is the one to move.

---

## address_space.py

Read all 673 lines. The two blocks of remembered measurements order `386c0d66e31e` flags were
re-measured against `data/TIERS.json`, `data/WORLDSEEDS.json` and `data/SHELFMARKS.json` by
reading the files directly and by driving `_tier_counts`, `WIDTHS` and `charted_gaps` in a
scratch process. **`main()` was NOT run** — it writes `data/SHELFMARKS.json`.

### THE RE-MEASUREMENT (the task's explicit ask)

**BLOCK A — the `fit()` census note, src/address_space.py:477-482.**

> MEASURED AGAINST THE LIVE CENSUS FIRST, so this cannot break a run that works today:
> TIERS.json holds 209 rows with hyperverse 2..5, xenoverse 0..5, metaverse 0..7 and
> multiverse 0..167 against field capacities of 8/8/8/256, and all 1,016 designations in
> WORLDSEEDS.json address with zero out-of-range tiers.

| claim | live, measured 2026-09-10 |
| --- | --- |
| TIERS.json holds **209** rows | **208** |
| hyperverse **2..5** | **1..5** (170 rows charted, 38 `None`) |
| xenoverse **0..5** | **0..2** (170 charted, 38 `None`) |
| metaverse **0..7** | **0..5** (145 charted, 63 `None`) |
| multiverse **0..167** | **0..142** (208 charted, 0 `None`) |
| field capacities **8/8/8/256** | **8 / 4 / 8 / 256** |
| 1,016 designations, zero out-of-range | **TRUE — 1,016 designations, 0 out of range** |

Live `WIDTHS` = `{hyperverse: 3, xenoverse: 2, metaverse: 3, multiverse: 8, universe: 6,
galaxy: 38, star: 27, planet: 1}`, `TOTAL_BITS = 88`.

**The capacity line is the one that matters.** `_TC["xenoverse"]` is 3, so
`_bits(max(2, 3))` is 2 bits and the xenoverse field's real capacity is **4**, not 8. The
paragraph is written as a safety argument — "this cannot break a run that works today" — and its
own figures, taken at face value, would prove the opposite: a xenoverse range of 0..5 does not
fit in a 4-value field, and `pack()` would raise `ValueError: xenoverse=5 does not fit in 2 bits`
on any such row. Nothing raises only because the live maximum is 2. A reassurance whose arithmetic
no longer closes is worse than none, because it is the paragraph a maintainer reads before
touching `fit()`.

**BLOCK B — the `shelfmark()` uncharted-tier note, src/address_space.py:295-299.**

> 38 of 208 TIERS.json rows carry an uncharted hyperverse and xenoverse, 65 an uncharted
> metaverse, and 16 of the 1,016 designations in data/SHELFMARKS.json are affected.

| claim | live |
| --- | --- |
| **38 of 208** rows, uncharted hyperverse **and** xenoverse | **38 of 208** — exact, and the two sets coincide exactly |
| **65** an uncharted metaverse | **63** |
| **16 of the 1,016** SHELFMARKS.json designations affected | **14 of 1,016** |

Live `data/SHELFMARKS.json` breakdown: 14 rows carry an `uncharted` key; by field, metaverse 14,
hyperverse 6, xenoverse 6. All 1,016 shelfmarks are distinct. Driving `charted_gaps` over
`WORLDSEEDS.json` against `TIERS.json` independently reproduces 14 of 1,016, so the file and the
code agree and it is the comment that has moved.

**A third fact the re-measurement turned up: the two blocks contradict each other.**
Line 478 says TIERS.json holds **209** rows; line 296 says **208**. The live figure is 208, so
the older of the two is right and the newer one is wrong, within one file, about the same file.

**Also still current, recorded so it is not re-measured:** live `tier_census()` renders
`"143 multiverses -> 6 metaverses -> 3 xenoverses -> 6 hyperverses"`, which matches the
`143 -> 6 -> 3 -> 6` quoted at src/address_space.py:132 and :185 exactly. Order 60dc7c624c06's
repair — render the sentence instead of typing it — is holding.

### MAJOR — Block A: five of the seven figures in the `fit()` census note are stale, including the capacity that carries its safety argument

**Where:** src/address_space.py:477-482. **What / Why / Confidence:** the table above. Measured
by reading `data/TIERS.json` (208 rows) and `data/WORLDSEEDS.json` (1,016) directly and by
reading `address_space.WIDTHS` from the live import.

### MINOR — Block B: the metaverse and SHELFMARKS counts have drifted

**Where:** src/address_space.py:296-298. 65 → **63**, 16 → **14**. The 38-of-208 half is exact.
Measured as above, and cross-checked two ways (from `TIERS.json` and from `SHELFMARKS.json`).

### MINOR — `pipeline.py:2138` no longer names `_phase_input("SHELFMARKS.json")`

**Where:** src/address_space.py:643. Target outside batch 08 (`pipeline.py`); verified by reading
the cited line and grepping the real site.

**What:** *"since `pipeline.py:2138` (`_phase_input("SHELFMARKS.json")`) reads this file as a
phase input"*.

**Why it is wrong:** pipeline.py:2138 is a comment about batches acquiring unjudged entries
(*"nothing reopened a batch that acquired unjudged entries afterwards"*). The
`marks, m_bad = _phase_input("SHELFMARKS.json")` call is at **pipeline.py:2845**. `citecheck`
does not catch it: 2138 is a non-blank, non-bracket line.

**Confidence:** high — `sed -n '2136,2140p' src/pipeline.py` and `grep -n SHELFMARKS src/pipeline.py`.

### MINOR — `standards.py:1177` no longer names the SHELFMARKS read

**Where:** src/address_space.py:645. Target outside batch 08 (`standards.py`); verified the same way.

**What:** *"and `standards.py:1177` reads it on its own clock"*.

**Why it is wrong:** standards.py:1177 is inside the swallowed-failure ledger's hostcheck label
tuple (`"hostcheck.py:probe", "hostcheck.py:candidates", …`). The
`open(os.path.join(HERE, "data", "SHELFMARKS.json"))` is at **standards.py:1375**. Again invisible
to `citecheck` for the same reason.

**Confidence:** high — read the cited line and grepped the real site.

### MINOR — `seed_from_card()`'s "(see :195-200)" points at the wrong docstring

**Where:** src/address_space.py:381.

**What:** *"it is written down here because this docstring has already been wrong once (see
:195-200) and the difference was in neither of them."*

**Why it is wrong:** lines 195-200 are `charted_gaps()`'s `def` line and its two-sentence
docstring — a function that has never been recorded as wrong. The docstring that "has already been
wrong once" is `shelfmark()`'s, at 270-319, which says so itself at 277-282 (*"THIS DOCSTRING SAID
THE OPPOSITE FOR THREE SWEEPS"*). Bare `:NNN` form, so structurally outside `citecheck`'s
`([A-Za-z_][A-Za-z0-9_]*\.py):(\d{1,6})` pattern — the new detector cannot see this class at all.

**Confidence:** high — read 195-200 and 270-319.

### MINOR — "roughly 5,200 have ever been written down" is a projection stated as a count

**Where:** src/address_space.py:77.

**What:** *"Of those 1.0e20 living worlds, roughly 5,200 have ever been written down."*

**Why it is wrong:** the library has written down **1,016** — `data/WORLDSEEDS.json` holds 1,016
designations and `data/SHELFMARKS.json` 1,016 rows. The 5,200 figure comes from
`worldseed.py:7-8` (cross-batch), where it is stated as a forecast — *"The catalogue is on course
for roughly 5,200 inhabited worlds"* — and it has been restated here in the past tense as work
already done, a factor of five out.

**Confidence:** high — counted both data files, read worldseed.py:7-8.

### INFO / QUESTION — the module uses two different multiverse populations

**Where:** src/address_space.py:53-54 and 93-99 and 233 and 570-571.

**What:** the derivation table says *"multiverse (live) continuity groups the catalogue
resolved"*, but `FIELDS` takes the multiverse population from `_TC["multiverse"]` (TIERS.json,
**143**) while `main()`'s headroom line uses `_continuities()` (CONTINUITY_GROUPS.json, **168**).

**Why it is a question and not a finding:** both are defensible readings and the width is
unaffected (8 bits covers 168 as well as 143). But the module's whole thesis is that one derived
number cannot be allowed to disagree with another, and these two do. Raising it for the owner
rather than proposing a change, because moving either one re-addresses worlds.

**Confidence:** read `_continuities()`, `_tier_counts()`, `FIELDS` and `main()`; measured
CONTINUITY_GROUPS.json at 168 groups and TIERS.json's multiverse max at 142 (→143).

### INFO — "a factor of a thousand" is a factor of about 300

**Where:** src/address_space.py:74-75: *"a 64-bit scheme cannot address it at all. It falls short
by a factor of a thousand."* 5.4e21 planets ÷ 2^64 (1.845e19) = **293**. The neighbouring claim
in the same paragraph checks out exactly: living worlds 1.0e20 ÷ 1.8e19 = 5.5, and
`census('STANDARD')['life_bearing']` (6e17) × 168 continuities = 1.008e20.

### INFO — `citation_card()` and `seed_from_card()` are dead, and `map_seed()`'s docstring points readers at the dead one

**Where:** src/address_space.py:330, :360, :390.

**What:** `liveness.scan()` reports both as DEAD (`address_space.py:330 citation_card()`,
`address_space.py:360 seed_from_card()`), and `grep -rn` over the repo confirms zero callers.
`map_seed()`'s docstring says *"Retained for worlds with no card yet; prefer seed_from_card()."*
while `main()` writes `map_seed(a)` into all 1,016 SHELFMARKS.json rows.

**Why it is INFO and not a finding:** both functions are explicitly marked kept-on-purpose —
`handoff/run35/checks_L4.py:198-207` records them as *"confirmed dead (zero callers)"* and
*"deliberately left for owner call"*. Saw the marking; moving on. The half worth naming is the
"prefer" sentence, which sends a reader to a function nothing uses while the published artefact
uses the other one.

---

## canon_backup.py

Read all 536 lines. Traced `members(strict=)`'s refusal, `snapshot()`'s write-verify-rename-
manifest sequence, `prune()`'s two loops, `verify()`'s five comparisons and `restore()`'s
open-source-first ordering. Nothing executed — `--snapshot` writes into `state/`.

The module's main invariants hold on reading: `members(strict=True)` refuses on any absent
declared path; `snapshot()` re-hashes every member out of the archive before landing it and
deletes the temp on any mismatch; `verify()` fails closed with no manifest, on an unparseable
manifest, and on a member the manifest records but the archive lacks; `prune()` counts a
half-removed pair as not removed; `restore()` opens the zip member before creating the
destination and gates `replace_retry`'s verdict.

### MINOR — "LIKE LINE 188" points at the read-back, not at the `replace_retry` it means

**Where:** src/canon_backup.py:475.

**What:** *"THROUGH `replace_retry`, LIKE LINE 188 AND UNLIKE ITSELF"*.

**Why it is wrong:** line 188 is `with zipfile.ZipFile(tmp) as z:` — the opening of the
verification read-back. The `replace_retry` this sentence is drawing a parallel to is
`if silence.replace_retry(tmp, final) is False:` at **line 208**. Bare "LINE NNN" form, so
outside `citecheck`'s pattern entirely.

**Confidence:** high, read both lines.

### MINOR — "(:312-320)" points at `newest()`'s tail and `verify()`'s signature, not at the fail-closed arm

**Where:** src/canon_backup.py:223.

**What:** *"`verify()` fails CLOSED with no manifest (:312-320) but a present one parses"*.

**Why it is wrong:** 312 is `return os.path.join(ROOT, snaps[-1]) if snaps else None`, 315 is
`def verify(path=None):`, 320 is a docstring line. The fail-closed arm is
`if not recorded: … return False, notes + [...]` at **348-356**. Bare `:NNN` form again.

**Confidence:** high, read 306-356.

### INFO — `snapshot()`'s empty-items guard cannot fire

**Where:** src/canon_backup.py:158-161.

**What:** `items = members()` then `if not items: raise RuntimeError("no canonical files found …
refusing to write an empty snapshot")`.

**Why it is noted:** `members()` is called at `strict=True`, and at that setting it raises on any
absent `CANON_FILES` entry, on an absent `CANON_DIRS` directory, and on a present directory
holding no `.json`. `CANON_FILES` and `CANON_DIRS` are both non-empty tuples, so there is no
input on which `members(strict=True)` returns an empty list rather than raising. The guard is
belt-and-braces and harmless; it is named because this is the module that argues at length about
verification that only ever compares what was collected, and it has one guard that can never
refuse.

**Confidence:** read `members()` in full and enumerated its exits.

### INFO — `prune(keep=0)` deletes nothing

**Where:** src/canon_backup.py:274: `for f in snaps[:-keep] if keep > 0 else []:`.

**What:** `--keep 0` reads as "retain none" and prunes nothing at all. Errs safe (nothing is
lost), and the CLI default is `KEEP = 7`.

### INFO / QUESTION — `verify()` returns ok=True when a canonical file is GONE from the live tree

**Where:** src/canon_backup.py:404, 436-442, 442, and src/canon_backup.py:510-515 (`main`).

**What:** `gone = [r for r in recorded if r not in live]` is reported in the notes, and the
function still `return True, notes`. `main()` then prints `VERIFY: ok` and returns 0.

**Why it is a question:** the same function's comment at 437-439 calls this *"the single most
actionable thing this module can tell anyone"*, and its docstring separately rules that
*"Divergence is NOT a failure"*. Both are defensible; a record file that has disappeared from
`data/records/` is arguably divergence (the tree moved) and arguably the loss the whole module
exists for. Raised as a design question, not a fix — deciding it changes an exit code the
supervisor may gate on.

### INFO — `restore(rel, dest=<bare filename>)` raises before it starts

**Where:** src/canon_backup.py:455-456: `dest = dest or …; os.makedirs(os.path.dirname(dest),
exist_ok=True)`. A `dest` with no directory component gives `os.path.dirname(dest) == ""` and
`os.makedirs("")` raises `FileNotFoundError`. Unreachable from the CLI, which never passes
`dest`; reachable from the API.

---

## recover_folder_records.py

Read all 379 lines. Re-measured every header figure against the live data, since the docstring
itself instructs that (*"re-run the same check before trusting these counts on a later date"*).

**Header measurements re-verified, all still exact:**

* *"6 of the 215 sources on the Acquisitions Roll show `entry_count: 0`"* — `data/SWEEP_ROLL.json`
  holds **215** rows and **6** at `entry_count == 0`: HAWX, Heaven's Lost Property, major
  live-action Disney films, Lost Mines of Phandelver, Twilight Imperium, the Witch Tradition.
* *"LOCAL_REGISTER.json -- 14,576 items"* — **14,576** exactly, across 213 register sources.
* *"'ME' … its 7 items … SEVEN unrelated roll sources"* — **7** items under `"ME"`, and exactly
  **7** roll sources map at it; the seven names listed at src/recover_folder_records.py:80-83
  match `FOLDER_SOURCE_MAP.json` byte for byte.
* the comment at :137-139 — *"'Lost Mines of Phandelver' and 'the Witch Tradition' are present in
  FOLDER_SOURCE_MAP.json with [], the other 4 are genuinely absent"* — **confirmed exactly**.

### MINOR — the SHORT-AGAINST-ITS-OWN-MAPPING report asserts of every member that it landed as a record, and two paths out of the loop make that false

**Where:** src/recover_folder_records.py:193-194 (the accumulator) against
src/recover_folder_records.py:356-359 (the report), with the two exits at :223-225 and :290-299.

**What:** `short_sources[name] = list(shortfalls)` is recorded deliberately early — the comment at
190-192 explains why — and then the loop can still leave by `skipped_populated` (`if already:
continue`) or by `WRITE DENIED` (`denied = True; continue`). The report nonetheless prints:

> These landed as records and were stamped 'catalogued', and work selection is entry_count == 0,
> so nothing will revisit them on its own

**Why it is wrong:** for a source that was short **and** already populated, nothing landed and
nothing was stamped — the existing record is untouched and is precisely the thing that must not be
revisited. For a source that was short **and** denied, nothing landed either, and the roll was
deliberately left at `entry_count: 0` so that it *will* be revisited. The sentence states the
opposite of the remedy in both cases, in the one bucket the same comment says *"is the one bucket
whose members otherwise look like successes"*.

**Confidence:** high — traced all three exits from the per-source loop and read the report.

### MINOR (latent, not live today) — an excluded register source routes its roll source into the wrong bucket, and the exclusion is recorded nowhere

**Where:** src/recover_folder_records.py:162-163 (`if register_source in
EXCLUDED_REGISTER_SOURCES: continue`) against src/recover_folder_records.py:196-197 and
:344-346, and the provenance string at :243-252.

**What:** the exclusion `continue`s **before** `_got`, before the shortfall check and before the
entry loop. A roll source whose mapping names only excluded register sources therefore reaches
`if not entries: skipped_no_items` and is printed under *"mapped, but the register holds no items
for them"*.

**Why it is wrong:** that sentence is false for this case — the register does hold items (7, for
`"ME"`), and this module excluded them on purpose. It is the same mislabel order `37d3d588847a`
was filed for, where an empty mapping was reported under the "no local data exists" bucket whose
remedy was wrong for it; the exclusion path reintroduces it one branch over. The two buckets
prescribe different work (fix the mapping / fix the register versus go and research the source),
and a third remedy — "this mapping is deliberately refused, and here is why" — has nowhere to be
recorded: not in the console report, and not in the record's `provenance` string, which only ever
names *shortfalls*. Order 729c26e0e63c's own principle is *"record every drop and re-ask"*, and a
deliberate exclusion is a drop.

**Confidence:** high on the code path, and I checked whether it is live: it is **not**. Measured —
all 7 roll sources mapping at `"ME"` currently carry `entry_count > 0`, so none of them enters the
`empty` list, and none of the 6 `entry_count == 0` sources maps at `"ME"` (four are absent from
`FOLDER_SOURCE_MAP.json`, two map to `[]`). This is a latent hazard, not a present fault, and it
is reported as such.

### INFO — the empty-source selector misses a `null` entry count

**Where:** src/recover_folder_records.py:109: `empty = [r["name"] for r in roll if
r.get("entry_count", 0) == 0]`. A row whose `entry_count` is JSON `null` gives `None == 0` →
False and is skipped. Measured: **0** such rows in `data/SWEEP_ROLL.json` today. Noted because the
default `0` covers the *missing-key* case and reads as though it covers the null case too.

---

## grounding.py

Read all 361 lines. Traced the `_BAD_CHARS` self-check, `_ORIGIN`, the five `GROUNDINGS` cue
tables, the uncapped `classify_text` / `classify_source` path and every diagnostic in `main()`.
Nothing executed — `main(--write)` writes `data/GROUNDINGS.json`, and a no-write run still
imports `pipeline` and reads the whole 206 MB corpus.

Verified clean and worth recording so it is not re-derived: `cap` is refused loudly rather than
honoured (200-204); `top` defaults to `None` so `most_common(None)` returns the whole field;
`total = sum(s for _, s in ranked)` is therefore the full-field denominator, which was the
substantive half of order e2b3af23cb8a; every diagnostic in `main()` is uncapped and sorted
most-contested-first; and the claim at 332-334 that *"every name in that literal tuple is under 26
characters and cannot truncate"* holds — the longest is "the Lovecraftian mythos" at 23.

### INFO — `classify_source`'s `if not ranked` disjunct cannot fire

**Where:** src/grounding.py:240-246, against src/grounding.py:170-174.

**What:** `classify_text` does `scores[name] += wt * len(...)` for every name in `GROUNDINGS`.
`Counter.__setitem__` inserts the key even when the value is 0, so `most_common(None)` always
returns exactly five rows. `ranked` is therefore never empty, and neither the `not ranked`
disjunct, nor the `ranked[0][1] if ranked else 0` else-arm, nor the `"runners_up": ranked`
fallback's empty case can be reached.

**Why it is noted rather than filed:** harmless defensiveness, and the reachable half of the
branch (`ranked[0][1] < floor`) is the one that does the work. Named because this project's
standing lesson is that a branch that cannot be taken looks exactly like one that was not taken
this time, and `liveness.py`'s PHANTOM/TAUTOLOGY passes are both syntactic and cannot see this
shape (it is semantic — `Counter` behaviour, not an identical comparison).

**Confidence:** high — read `classify_text`, confirmed `Counter` insertion semantics.

### INFO — "THE TYPES / Six" against five `GROUNDINGS` entries

**Where:** src/grounding.py:38-41 against src/grounding.py:78-122.

**What:** *"Six, derived by running the regress test's three questions to their combinations"* —
`GROUNDINGS` has five (`ex_nihilo`, `emanation`, `eternal_cycle`, `demiurgic`, `immanent`), plus
`UNGROUNDED` as a sixth answer.

**Why it is ambiguous rather than wrong:** the same paragraph says *"Each is a distinct way for
the regress to halt, **or to fail to**"*, which reads UNGROUNDED into the six. But
`classify_text`'s docstring twice says the field is five wide (*"with only five groundings in the
field"*, *"The field there is eleven wide, here it is five"*) — and that is the number that
matters, because it is the denominator. Noted so a reader does not take "six" as the field size.

### INFO — the whole-corpus measurements are stated over 210 records; `data/records/` holds 216

**Where:** src/grounding.py:148-168 and :186-195.

**What:** *"Whole-corpus measurement, 210 records (59 classified, 151 ungrounded at floor 6)"* and
*"Whole-corpus check before this changed (210 records)"*.

**Why it is INFO:** `data/records/*.json` is **216** files today. I did **not** re-run the
classification — it would re-read the whole corpus and the figures are explicitly dated and
attached to a specific change. Flagged as a dated measurement whose population has moved, not as
a wrong one. If the coordinator wants it re-measured, `classify_source` is pure and can be driven
over `data/records/` without touching anything.

### INFO — a string `synthesis` would raise out of `classify_source`

**Where:** src/grounding.py:234-235: `syn = rec.get("synthesis") or {}` then
`syn.get("rationale")`. If a record's `synthesis` is a string rather than a dict or `None`, `syn`
is that string and `.get` raises `AttributeError`. Records are written with dict-or-`None`
synthesis (which is the invariant `workorders`' STRANDED_SYNTHESIS detector is built on), so this
is a shape assumption rather than a live fault.

---

## profile.py

Read all 295 lines. Traced `B32` / `_B32_CLASS` / `_PROFILE_RE`'s construction, `_b32` / `_unb32`,
`encode`'s band-degrade path, `decode`'s five reconstructions, and `main()`'s round trip.
`main()` was not run (it drives `worldseed.build_all()` over the corpus); `decode` was exercised
on three hand-made strings in a scratch process, which reads nothing and writes nothing.

Verified clean: `B32` is 32 unique symbols with `i`, `l`, `o`, `u` absent; `_PROFILE_RE` is built
from `B32` so the two cannot drift; the band round trip holds through the degrade and the clamp
(`"M3.52 ± 0.12"` → `'3'` → `"M3"` → `'3'`; `"M12"` → `'a'` → `"M10"` → `'a'`); and the round
trip at 260-272 genuinely re-encodes what `decode` extracted, so the tautology
`liveness.py:7-9` records as fixed **is** fixed (only its address is wrong — see that finding).

### MAJOR — `decode()` admits all 32 base-32 symbols in each feature position while the tables are 6, 6, 3 and 4 long, so a string that passes the validator raises a bare `IndexError` from inside the decoder

**Where:** src/profile.py:90-92 (the pattern), src/profile.py:104-105 (`AXES`),
src/profile.py:163 (the lookup), against the comment block at src/profile.py:72-89.

**What:** `_PROFILE_RE` spells the feature group `(%s{4})` with `%s` = `_B32_CLASS`, i.e. any four
of the 32 symbols. `decode` then does

```
features = {axis: tbl[B32.index(ch)][0] for (axis, tbl), ch in zip(AXES, feats, strict=True)}
```

with `AXES = [("landform", WS.LANDFORM), ("climate", WS.CLIMATE), ("condition", WS.CONDITION),
("tech", WS.TECH)]`. Measured lengths: **LANDFORM 6, CLIMATE 6, CONDITION 3, TECH 4.**

**Why it is wrong:** only 6 of the 32 admitted symbols are valid in position 1, 6 in position 2,
**3** in position 3 and **4** in position 4. Every other combination matches `re.fullmatch`,
sails past the `raise ValueError(f"not a world profile: {profile!r}")` written for exactly this
case, and dies at `tbl[B32.index(ch)]` with `IndexError: list index out of range` — naming
neither the profile nor the offending character. Reproduced in a scratch process:

```
decode("PS-1-myc-000z-u0")  ->  IndexError: list index out of range
decode("PS-1-myc-zzzz-u0")  ->  IndexError: list index out of range
decode("PS-1-myc-0000-u0")  ->  ok
```

This is the *same* defect, in the *same* function, that the comment block immediately above the
pattern says was closed. That block cites three separate filings (`ed46a60bc2dc`, `559b09f35e5c`,
`6f1652a21efb`) against this one line and states the lesson explicitly:

> the `raise ValueError(f"not a world profile: …")` written for exactly that case therefore NEVER
> FIRED on them: execution carried on into `_unb32`, and `B32.index(ch)` raised a bare
> `ValueError: substring not found` from inside a private helper, naming neither the profile nor
> the offending character. … What was wrong is WHICH LAYER refused it, and with what. That is the
> difference between a validator and a crash.

The repair narrowed the pattern from `[0-9a-z]` to `B32`, which fixed the four removed letters —
and left the *table bound* unguarded, which is the larger hole by count: 26 of 32 symbols are
invalid in landform, 26 in climate, 29 in condition, 28 in tech. The same comment shows the shape
of the fix it did not take: *"The band group stays `[0-9au]` -- it is already scoped to exactly
the values `encode` can emit, which is the pattern this restores to the other two groups."* The
feature groups are the ones that were not so scoped.

**Confidence:** high — read the pattern, `AXES` and the lookup; measured the four table lengths
from `worldseed`; reproduced both failures and the success case.

### MINOR — the format table names the fourth feature axis "era"; the code's fourth axis is `tech`

**Where:** src/profile.py:18 and :27 against src/profile.py:104-105.

**What:** the profile grammar is given as `PS-<address>-<gr><rg>-<lcce>-<band><att>` and `lcce` is
glossed *"landform, climate, condition, era: what the world IS LIKE"*. `AXES` is
`landform, climate, condition, **tech**`, and `decode` returns the key `"tech"`.

**Why it is wrong:** the mnemonic and the gloss both encode a field the format does not have. A
reader building or parsing a profile string from this docstring alone will look for an era digit
and find a technology digit — and the two are not interchangeable (`WS.TECH` starts at
`spacefaring`). The docstring is the specification here; it is what the "two referees who have
never met can exchange one and mean the same world" paragraph is about.

**Confidence:** high — read both sites and the live `decode` output
(`{'landform': …, 'climate': …, 'condition': …, 'tech': 'spacefaring'}`).

### MINOR — "(line 125 above)" points at a blank line

**Where:** src/profile.py:266.

**What:** *"`d["profile"]` is decode()'s own argument echoed back (line 125 above)"*.

**Why it is wrong:** line 125 is blank (it sits between `_unb32`'s `return n` and `def encode`).
The echo — `"profile": profile` — is at **line 174**. Bare "line NNN" form, so outside
`citecheck`'s pattern; ironically, 125 *is* a blank line, which is one of the three conditions
`citecheck` proves, and the detector still cannot see it because the citation does not name a
file.

**Confidence:** high — read line 125 and line 174.

### INFO — an undated remembered measurement in the docstring

**Where:** src/profile.py:41: *"Only 29.9% of world axes come from a source; the rest are
seeded."* No date, no order, and nothing in the module derives it. I did not re-measure (it needs
a full `worldseed.build_all()` pass). Named because it is the figure the whole "WHAT THE PROFILE
DELIBERATELY CARRIES" argument rests on.

### INFO — missing separator in a console line

**Where:** src/profile.py:281: `print(f"   neighbourhood{n}")` renders as
`neighbourhoodhttps://…`. The two sibling lines pad their labels; this one does not.

---

## A cross-cutting note for the coordinator, about the new detector's reach

Not a defect in `citecheck.py` — its docstring is scrupulous that CLEAN means "not provably
broken" — but worth stating in one place, because this batch turned up **seven** rotted citations
and the new STALE_CITATION detector would catch **none** of them:

* `liveness.py:7` → `profile.py:196-208` — right form, but the cited line is non-blank, so
  `_classify` returns `None` and it reads CLEAN.
* `address_space.py:643` → `pipeline.py:2138` — same.
* `address_space.py:645` → `standards.py:1177` — same.
* `address_space.py:381` → `:195-200` — bare `:NNN`, no filename, outside `CITATION`'s pattern.
* `canon_backup.py:223` → `(:312-320)` — same.
* `canon_backup.py:475` → `LINE 188` — prose form, outside the pattern.
* `profile.py:266` → `line 125 above` — prose form, and the target genuinely IS a blank line.

The order's own text is honest about the first three (*"proves only that a cited line CANNOT be
the one meant"*), and the detector is still worth having as the floor it claims to be. The last
four are a different matter: the **bare `:NNN` and "line NNN" self-citation is a common house form
in this codebase**, and it is not merely under-detected, it is structurally invisible — which
means the floor does not stop the class growing in the form the class most often takes here. That
is a question for the owner about `CITATION`'s pattern, not a fix I am proposing.

`citecheck.py` is outside batch 08 and I did not audit it; I read it only far enough to verify
what section 12 of `workorders.py` is wired to. One thing I saw in passing and am naming rather
than dropping: `citecheck.py`'s own docstring offers `standards.py:604` *"(a blank line)"* and
`address_space.py:381` *"(a bare bracket)"* as sites this detector would have caught. Neither is
true of the live tree — `standards.py:604` is `return a == b or a == b + ":latest" or b == a +
":latest"` and `address_space.py:381` is a line of docstring prose — so both examples have since
been repaired or moved, and the module's own evidence for its value no longer reproduces. A batch
that owns `citecheck.py` should confirm.
