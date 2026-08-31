# SWEEP 39 — BATCH 03 AUDIT

Batch obtained programmatically from `sweep_plan.batches(16)[2]["modules"]`, not from a typed list.

**Modules read in full (7, 4,800 lines):**
`pipeline.py` (2,648) · `codewatch.py` (578) · `policy.py` (476) · `feats_index.py` (369) ·
`style_audit.py` (308) · `tuning.py` (272) · `repass_bands.py` (149)

None of the seven is in the maintenance shift's changed-today set — all seven carry mtimes of
2026-08-29 (verified by `ls -l`), so nothing here was read mid-edit.

Every finding below was checked against the current source, and where the claim was measurable it
was measured against the live corpus rather than argued from the code. Two candidates were dropped
during verification because the source did not support them (recorded at the bottom, under
NOT FINDINGS, so nobody re-files them next sweep).

---

## F1 — MAJOR — phase 1's own fix is defeated one line later; 44 sources can never be re-nominated

**Where:** `src/pipeline.py:1085-1090` (`phase_synthesis`), against its docstring at `:1076-1084`.

The docstring records a fix and states the reasoning at length:

> A source that FAILED still had a synthesis block written, with empty fields. Filtering on the
> block's mere presence therefore made failure permanent: the source could never appear in `todo`
> again... Sixty-nine sources sat with `ceiling_entity: ""` and no way back. ... Those sixty-nine
> include SpongeBob, Mario, **Overwatch**, Yakuza, Fire Emblem and Gundam — sources whose ceilings
> came back empty because phase 1 examined them BEFORE their casts existed... **They have casts
> now, so the nomination is worth making again.**

The `todo` filter was duly changed to select on `ceiling_entity` rather than on the block:

```python
todo = [(p, r) for p, r in records()
        if not (r.get("synthesis") or {}).get("ceiling_entity")]      # :1085-1086
done_keys = st["done"].setdefault("synthesis", [])                    # :1088
for path, rec in todo:
    src = rec["source"]
    if src in done_keys:                                              # :1092
        continue
```

`done_keys` comes off `state/PIPELINE_STATE.json` and persists across runs, so the membership test
at `:1092` restores exactly the permanence the `todo` filter at `:1085` was rewritten to remove. A
source written with an empty ceiling lands in `done_keys` at `:1164` on the very same pass.

**Measured live, this run:**

* `done.synthesis` holds 186 keys.
* 49 records carry no `ceiling_entity`.
* **44 of those 49 are already in `done.synthesis`** — every one of them carrying a *present*
  synthesis block with `provisional_magnitude: "unassayed"` and `ceiling_entity: ""`.
* 0 of the 44 lack a block.

The 44 include **Overwatch (259 entries)** — the source the docstring names — plus
`the FFXIV / Eorzea conversion` (685), `Ghost Recon` (808), `swecky's Nature Traditions` (489),
`Yorviing's Arcane Grimoire` (478), `Splinter Cell` (468), `Dr. Firestorm's Engineering Corps`
(425), `Mad Max` (251), `Disco Elysium` (247), `witchcraft traditions in full` (254),
`Chowder` (239), `Eberron: Rising from the Last War` (212). Full list in the order's evidence.

**And the rescue tool does not reach them.** `retry_synthesis.stranded_sources()`
(`src/retry_synthesis.py:107-118`) exists for precisely this population — its own docstring says
"the whole reason these are stranded is that `phase_synthesis` skips any source already in its
done-keys" — but it selects on `if rec.get("synthesis"): continue`, i.e. on the block's ABSENCE.
All 44 have a block. **It covers 0 of the 44.** Measured: sources in `done.synthesis` with no
block at all = 0.

This is the shape `batch_settled` (`:1428-1446`) already ruled on for phase 2, in this same file:
"The rule is deliberately NOT 'the key is recorded'... Membership plus a fully judged span is the
honest gate; membership alone strands every later-appended entry." Phase 1 uses membership alone
over a `todo` list whose own filter says the work is not done.

**Remedy.** Do not simply drop the `done_keys` test — that would re-nominate every genuinely
feat-less source on every pass, which is real spend on a constrained pool and is why the gate is
there. Make phase 1's gate say what phase 2's says: skip only when the key is recorded AND the
work still stands. Concretely: record the negative verdict explicitly in the block
(`synthesis["unassayable"] = True` beside the existing `assessed_at`) together with the cast size
or `_entry_digest` the verdict was reached against, and re-admit a source whose cast has grown
since. That distinguishes "the model looked at 259 entries and honestly found no feat" — a correct,
expected answer under SYNTH_SYSTEM hard rule 3 — from "the model looked at 14 entries in April and
the source has 259 now", which is the exact population the owner already ruled is worth
re-nominating. Alternatively widen `retry_synthesis.stranded_sources()` to select on
`ceiling_entity` rather than on the block, which is the same correction that function's own
docstring makes about selecting on the CAUSE rather than the CONDITION.

---

## F2 — MAJOR — `repass_bands --apply` destroys the rejected scale-note text the pipeline preserves

**Where:** `src/repass_bands.py:72-77`.

```python
# A note that no longer evidences scale should not sit in the record claiming to.
if sn and not PL.valid_scale_note(sn):
    cleared_notes += 1
    if args.apply:
        e["scale_note"] = ""
        changed = True
```

The raw text is overwritten with `""` and preserved nowhere. `pipeline.phase_entrypass` handles
the identical event — a note the gate refuses — the opposite way, and the comment above it
(`src/pipeline.py:1540-1546`) is explicit about why:

> NEVER DISCARD WHAT THE GATE REJECTED. The first version assigned the gated result straight over
> the field, so a rejected note left no trace: 51,611 entries ended up holding an empty string and
> ~46,000 candidate feats were destroyed. The cost is not only the feats. It is that the rejection
> rate became **unauditable** — with the raw text gone there is no way to tell a gate that is
> correctly refusing biography from one that is too tight.

`pipeline.py:1547-1553` therefore writes the refused text to `scale_note_rejected`.
`repass_bands.py:76` is the only other site in `src/` that empties a `scale_note`
(verified: `grep -rn '\[.scale_note.\] *=' src/*.py` returns exactly `pipeline.py:1549` and
`repass_bands.py:76`), and it is the one that does not preserve. Since this module's whole purpose
is re-applying the corrected gate corpus-wide, `--apply` is precisely the run that would destroy
the largest number of candidate feats in one pass, and it would do so while its own docstring says
"Demotion is not data loss."

Note the demoted SOURCE ceiling is handled correctly two loops up (`:52-57`): the evidence string
is kept and a `demoted_by` reason is written. Only the per-entry path discards.

**Remedy.** In the `--apply` branch, write `e["scale_note_rejected"] = sn[:500]` before clearing
`e["scale_note"]`, matching `pipeline.py:1547-1551` field-for-field (`scale_note_rejected` is
already in `MERGED_ENTRY_FIELDS` at `pipeline.py:493-497`, so the writer will carry it). While
there, note the second-order hazard for whoever implements it: `ENTRY_REJECTION_COMPANIONS`
(`pipeline.py:511`) makes `write_record` POP a disk-side `scale_note_rejected` whenever the
in-memory entry has `scale_note` and lacks the rejection key — harmless today because
`repass_bands` mutates the same dicts it loaded from disk, but it means the fix must SET the
companion rather than leave it absent.

---

## F3 — MAJOR — `fl[:3]`: a silent cap on mined feats inside the ceiling-nomination prompt

**Where:** `src/pipeline.py:1064`.

```python
fl = feats_for.get(e["name"]) or []
if fl:
    d = " | ".join(re.sub(r"\s+", " ", x)[:150] for x in fl[:3])[:420]
```

Three cuts, none marked: at most **3** of an entity's feats, each cut at 150 chars, the join then
cut at 420. `feats_index.py`'s own header measures the store at "47,017 of them across 1,412
records, **averaging 33 per entity**" — so for a typical entity this shows the model 3 of 33, and
`fl` is in stored order, so it is not even the ranked head; it is whichever three the miner wrote
first.

This is load-bearing, not cosmetic. `synthesis_blocks` (`:1021-1023`) sorts feat-bearing entries
first *because* "an entity with a feat on record is exactly what a ceiling nomination wants to see,
so those go first and **carry their feat text with them**" (`:1109-1111`) — and then this line
carries three of them. The band the block produces becomes `provisional_magnitude`, which
`phase_entrypass` uses at `:1576-1580` to CLAMP every entry in the source. A ceiling chosen from a
truncated feat list clamps a whole shelf.

It sits ten lines below the comment (`:1026-1052`) in which the owner ruled a cap of exactly this
shape out of this same function on 2026-08-25 — "*ranking then truncating is not sampling, it is
deciding on the entity's behalf that everything past the cutoff does not exist*" — and that ruling
removed the cap on the BLOCK list while leaving the per-entity feat cap untouched. That is this
project's recorded failure shape stated in the same function's own words at `:1016-1019`: "a ruling
gets applied to the file in front of the person applying it, and the identical construction one
module over is never visited."

**Remedy.** Take the same shape the block loop already uses: page the entity's feats across
nomination blocks rather than cutting them, or at minimum emit the whole list with the house
remainder marker (`... (+N more feats)`) so a truncation declares itself — `policy._observed`
(`policy.py:105-126`) and `style_audit._cut` (`style_audit.py:156-170`) are the two existing house
idioms for this. If a per-call bound is genuinely needed for the local context window, it must be
derived from `num_ctx` the way `manifest_builder`'s `FEATS_BLOCK_CHARS` was (m46), not a bare 3.

---

## F4 — MAJOR — the pool-proof staleness check is delegated to a function that does not apply it, and the answer is discarded

**Where:** `src/pipeline.py:296-316` (`_pool_answering`) and `src/tuning.py:145-164`
(`_answering_buckets`).

`_pool_answering`'s docstring justifies delegating the count:

> This used to re-open POOL_PROOF.json and count `verdict == "answers"` on its own, with no notion
> of the proof's age — so an arbitrarily old proof was trusted as current, while **tuning's copy of
> the identical count already compared the file's mtime against `PROOF_STALE_SECONDS`**.

Read against the source, that claim does not hold up in the way the sentence implies.
`tuning._answering_buckets` compares the mtime, and then returns the count **unchanged**:

```python
n = sum(1 for r in rows if isinstance(r, dict) and r.get("verdict") == "answers")
if age > PROOF_STALE_SECONDS:
    # A stale proof is a claim about a pool that may no longer exist. Believe it, but say so.
    return n, "%d answering (proof is %.1fh old)" % (n, age / 3600)
return n, "%d answering" % n
```

`tuning.py` is honest about this — `PROOF_STALE_SECONDS`' own comment (`:62-66`) says a stale proof
is "annotated as stale but still counted at full strength", and that whether it should be
DISCOUNTED "is a live question (m59...) and is not settled here". The staleness lives entirely in
the second return value, the caption.

And `_pool_answering` throws that second value away:

```python
_PHASE_POOL["n"], _ = _T._answering_buckets()        # pipeline.py:311
```

So the routing gate at `:381` (`if _pool_answering() >= _min_buckets`) is exactly as age-blind as
the hand-rolled count it replaced: a week-old POOL_PROOF.json routes every phase judgment call
cloud-first, and neither the caption nor the age reaches any log line in `pipeline.py`. The order
that motivated the delegation (54cd47a337dc) did remove a duplicate spelling of the count, which is
a real gain; what it did not do is what the docstring says it did.

Measured now: proof age 0.81 h, `tuning._answering_buckets()` -> `(3, '3 answering')`,
`pipeline._pool_answering()` -> `3`, `CLOUD_MIN_BUCKETS` 3, `PROOF_STALE_SECONDS` 3600. The gate is
sitting exactly on its threshold today, so the difference between a fresh 3 and a stale 3 is the
whole decision.

**Remedy.** Two acceptable directions, and the choice is a judgment the code should not keep
hiding: either (a) keep the caption — capture the second return value in `_PHASE_POOL` and log it
on the fall-through at `:392` so a cloud-first decision taken on an eight-hour-old proof says so;
or (b) settle the live question tuning declines to settle and discount a stale count. Whichever is
chosen, correct `_pool_answering`'s docstring: as written it tells the next reader that the age is
already handled.

---

## F5 — MINOR — four stale `file.py:NNN` cross-references in `pipeline.py`, each verified

Each was checked against the current file; the line cited holds something else.

| Comment at | Cites | Claims to hold | What that line actually holds now | Correct line |
|---|---|---|---|---|
| `:490-491` | `pipeline.py:1552` | where `phase_entrypass` WRITES `topic_rejected` | `else:` (of the `scale_note_rejected` branch) | **1598** |
| `:503` | `:1532` | the `scale_note_rejected` POP | the `if batch[i].get("excluded"): continue` guard | **1553** |
| `:504` | `:1573` | the `topic_rejected` POP | inside the ceiling-clamp comment | **1594** |
| `:1936` | `:1948` | "the ruling phases 6 and 7 carry" — phase 6's absent/corrupt ruling | `silence.note("pipeline.py:phase_cosmology-seeds-absent")`, inside phase **5** itself | ~**2017-2035** |
| `:1936` | `:2054` | phase 7's ruling | `def depth(stack):` inside phase **6** | ~**2123-2136** |
| `:1884` | `profile.py:20` | "was carrying a third stale copy, 89 against a live 88" | `att  how many of the four world axes...`; the 88 now lives at `profile.py:16` | **profile.py:16** |

The `:490-491` one is the most misleading of the set, because the sentence around it is making a
measured claim ("`topic_rejected` ... appears 0 times in 282,822 entries") and points the reader at
a line that has nothing to do with topics.

**Remedy.** Correct the six numbers. Better, where the cited construct is unique in the file, cite
it by name instead — `phase_entrypass`'s topic branch, `phase_history`'s TIERS.json handler — since
a name does not go stale when a line moves. Verified NOT stale, and left alone: `cascade_bridge.py:18`
(cited at `pipeline.py:322`, quotes that line verbatim and correctly), `verify_math` section 18d
(cited at `:1431`, exists at `verify_math.py:1387` and does drive `batch_settled`), and
`manifest_builder.py:342-358` (cited at `feats_index.py:137-141`, lands exactly on the try/except
it describes).

---

## F6 — MINOR — `style_audit._cut` cites a line range that no longer holds the idiom it credits

**Where:** `src/style_audit.py:158`.

> """The house line for a ranking that had to be cut, from **repass_bands.py:106-113**.

`repass_bands.py:106-113` is the `SOURCE CEILINGS` print block plus the opening of an unrelated
comment. The house line it is crediting — the `showing X of Y; N more not shown` construction — is
at **`repass_bands.py:115-122`**. The citation is off by roughly nine lines, and it is the kind
that matters slightly more than usual: it is the provenance of a shared idiom, so a reader
following it to copy the idiom lands on a print of demotion counts.

**Remedy.** Repoint to `repass_bands.py:115-122`.

---

## F7 — MINOR — `feats_for_source` returns `[]` for an unbound source, which is the one conflation both modules forbid

**Where:** `src/feats_index.py:262-265`.

```python
idx = load_index()
hosts = [h for h, srcs in host_to_sources().items() if source_name in srcs]
if not hosts:
    return []
```

`host_to_sources` was deliberately taught to RAISE rather than return `{}` (`:129-143`) so that an
unreadable `WIKI_HOSTS.json` could not "produce the identical observable result to *this source
genuinely has no attested feats*". The bare `return []` at `:265` produces that identical
observable result for a source that is simply not IN `WIKI_HOSTS.json` — and the guard one level up
(`manifest_builder.py:351-358`, verified at those exact lines) only prints its WARNING on an
**exception**, so nothing distinguishes the two cases at the one call site that matters.

**Measured:** 216 record files on disk, 198 sources bound to a host, **18 unbound**. Five of the 18
are legitimate `pages:` sentinels — owner-supplied books that correctly have no wiki host
(`A Plethora of Paladins`, `Guildmasters' Guide to Ravnica`, `KibblesTasty (techno-psionic line)`,
`all Creeper World`, `the Sex Worker background`). The other **13** are simply not recorded:
`Curious DM Investigations (the Sharkin)`, `Genuine Fantasy Press (Forgotten Secrets)`, `HAWX`,
`Heaven's Lost Property`, `JMBrew`, `Kobold Press (Midgard Heroes Handbook, Midgard Worldbook)`,
`Super Energy Apocalypse 1 & 2`, `The Elements Beyond`, `Twilight Imperium`,
`aurora_mods (Way of the Inkmaster)`, `major live-action Disney films`,
`the Weaveshaper Ateliers`, `the Witch Tradition`.

Mitigating, and the reason this is MINOR rather than MAJOR: `audit()`/`main()` DO surface the
condition from the other end — a feats record on an unbound host lands in `stranded_hosts` and
prints `NOT IN WIKI_HOSTS`. The blind spot is the generation path, not the project's ability to
find out at all.

**Remedy.** Distinguish the two answers at the return. Either return a sentinel the caller can
test, or (cheaper and consistent with `host_to_sources`' own precedent) have `manifest_builder`
ask a second question — `feats_index.host_to_sources()` membership — before treating `[]` as "no
attested feats", and print the same WARNING it already prints for an exception. A `pages:` source
should answer "not a wiki source" rather than "no feats", since those five are correct-by-design.

---

## F8 — MINOR — `most_common(6)` over a population of exactly 6

**Where:** `src/pipeline.py:1928`.

```python
kinds = collections.Counter(_kind(v) for v in grounds.values())
log("  grounding: " + ", ".join("%s %d" % (k, n) for k, n in kinds.most_common(6)))
```

`grounding.GROUNDINGS` holds exactly 5 kinds (`ex_nihilo`, `emanation`, `eternal_cycle`,
`demiurgic`, `immanent`) plus `grounding.UNGROUNDED` = **6 possible values**, so the cap has zero
margin: it truncates silently the day a sixth grounding type is added, in a log line whose whole
job is to report the distribution. This is a cap that has not bitten yet rather than one that has,
which is why it is MINOR — but it is the exact latent shape Hard Rule 0 is about, and there is no
reason for a bound here at all: the population is bounded by the doctrine.

**Remedy.** `kinds.most_common()` with no argument. If a bound is ever wanted, use the `_cut`
idiom so the remainder prints.

---

## F9 — MINOR — `codewatch.stamp(who)` ignores its own argument

**Where:** `src/codewatch.py:293-299`.

```python
def stamp(who="?"):
    """Record the code this process actually started with. Call once, at startup."""
    _START["digest"] = fingerprint()
    ...
```

`who` is never read. Four callers pass a meaningful job name that goes nowhere:
`autostart.py:372`, `dashboard.py:1066`, `foreman.py:1683-1684`, `pipeline.py:2456`. The parameter
invites the belief that stamping is per-job, when `_START` is a single process-global slot.

Two consequences, both latent rather than live: a process that stamped twice under two names would
silently rebase its own comparison point (`stamp` also clears `_PENDING`, discarding accumulated
settling progress), and the stamp cannot be attributed in a report — `main()`'s output can name the
current fingerprint but not which job took which stamp. A drill net at `drill.py:5583` asserts
`codewatch.stamp` is CALLED within `main`, so the call sites are pinned; nothing pins the argument
because nothing consumes it.

**Remedy.** Either record it (`_START["who"] = who`, and have `exit_if_stale` warn when its own
`who` disagrees with the stamp's — that is a genuine "this process stamped as something else"
signal), or drop the parameter and update the four call sites. Recording it is the better of the
two: it costs nothing and turns an inert argument into an attribution.

---

## F10 — MINOR — `policy.main()` reads COVERAGE.json unguarded while the record loop treats an unreadable file as a finding

**Where:** `src/policy.py:325-335`, against `:307-324`.

The record loop was deliberately taught (run #33, batch 15) that "A RECORD THAT COULD NOT BE READ IS
A FINDING, NOT A GAP IN THE SAMPLE", and names each unreadable file in the summary. Nine lines
later:

```python
if os.path.exists(cov):
    with open(cov, encoding="utf-8") as f:
        rows = json.load(f)
```

A torn or truncated `COVERAGE.json` raises out of `main()` — so it is loud, which is why this is
MINOR and not MAJOR — but the blast radius is the whole run rather than one row: the evidence
sweep never starts, `report()` is never called, the previous run's `state/policy_report.json`
stands, and the module exits on a traceback rather than on either of the two exit codes
`:462-472` documents for exactly the "the report on disk is not this run's" case.

**Remedy.** Wrap it the way the record loop is wrapped: catch, `silence.note`, add to the
`unreadable` list under a distinct subject, and let the run continue and report. `COVERAGE.json` is
also the file `pipeline.phase_write` (`:2251-2270`) treats with the absent/corrupt distinction, so
the house ruling for this exact file already exists.

---

## F11 — INFO — `OPS["nonempty"]`'s second conjunct cannot be False

**Where:** `src/policy.py:51`.

```python
"nonempty":  lambda v, _a: bool(v) and len(v) > 0,
```

For every sized value, `bool(v)` is already `len(v) > 0`; the second test can never change the
verdict. For a non-sized truthy value (an int, a float) `len(v)` raises `TypeError`, which
`check_rule`'s handler at `:149-153` records as a **rule failure** on the document — i.e. a
document is reported as failing `record.source` because the rule could not be evaluated against it.
That is the distinction the comment at `:138-142` says must not be blurred ("a malformed rule
reported as a failing document ... sends the reader to the wrong place entirely"), arriving from
the value side rather than the rule side.

No live impact: the three rules using `nonempty` (`record.source`, `evidence.entity`,
`evidence.host`, `coverage.source`) all target string fields, and the corpus does not currently put
numbers there.

**Remedy.** `lambda v, _a: bool(v)` is the honest spelling. If the intent is "a non-empty
*container or string*", say so explicitly (`hasattr(v, "__len__") and len(v) > 0`) so a number in a
name field FAILS rather than ERRORS.

---

## F12 — INFO — dead assignment in `policy.check_rule`

**Where:** `src/policy.py:150`. `ok = False` is assigned and then never read — the very next
statement returns a dict literal carrying `"ok": False` directly. Harmless; remove.

---

## F13 — INFO — five unmarked store-time cuts in `pipeline.py`

**Where:** `:1151` `evidence[:600]`, `:1152` `rationale[:900]`, `:1549` `scale_note[:500]`,
`:1551` `scale_note_rejected[:500]`, `:1598` `topic_rejected[:120]`.

These are not display caps — they are what lands in `data/records/*.json` and is read back by
`repass_bands` (`PL.valid_scale_note(syn.get("evidence"))`), `audit.py` and the assay path. A value
cut at the bound reads as a complete value, which is the property `policy._observed` was rewritten
to remove for its own field (`policy.py:105-126`: "a cut now declares itself and its size, so a
short value and a shortened one are distinguishable").

Mitigating: the prompts ask for terse output — `evidence` "at most 20 words", `scale_note` "at most
15 words" — so these bounds are generous and are unlikely to be hit by a compliant answer. That is
exactly why they are INFO. But a NON-compliant answer is the one case they fire on, and that is the
case a reader most wants to see intact.

**Remedy.** Apply the `_observed` idiom — append `"... (+%d chars)"` when a cut happens — or drop
the bounds, since `workorders.file_order`'s comment already argues the general case ("a cap is
acceptable exactly where it is reversible", and a stored record field is not).

---

## NOT FINDINGS — checked, and the source did not support them

Recorded so the next sweep does not re-open them.

* **`_SCALE_PATTERNS` / `_SCALE_EVIDENCE` (`pipeline.py:1332-1333`) are dead — and the comment
  above them says so accurately.** Verified: `grep -rn '_SCALE_EVIDENCE\|_SCALE_PATTERNS' src/`
  returns only those two definition lines (plus stale `__pycache__` binaries). The comment's claim
  "Nothing in src/ reads either name below — grep confirms only their own definitions" HOLDS as of
  this sweep, and its argument for keeping them (as the recorded shape of a REJECTED approach, so
  nobody re-wires the disjunction the corpus measurement disproved) is sound. Not filed.
* **`style_audit._WATCHED` (`:34-35`) does not double-count.** Suspected `ALL_PATTERNS` might
  already contain the lexical sets. Measured: `ALL_PATTERNS` 46 (= `STRUCTURAL` 31 + `DISCOURSE`
  15), `LEXICAL` 60, `LEXICAL_FICTION` 32, total **138**; `tells.scan` walks `_COMPILED` (46) and
  `_LEX` (92 = 60+32), so all 138 are genuinely scanned and none is counted twice. This also
  confirms the figure transcribed at `pipeline.py:1697` ("tells 60+31+15+32 = 138") is still
  correct.
* **`codewatch.py:534` passing the literal `"MANAGER"`** where neighbouring calls pass the
  `escalation.JANITOR` constant. Checked `escalation.escalate` (`escalation.py:177+`): it accepts
  the NAME as well as the number, deliberately and at length, resolving through `BY_NAME`. Correct
  as written.
* **`codewatch._budget_left`'s "NO PRODUCTION CALLER" docstring.** Verified: driven by
  `drill.py:5664-5675`. The docstring is accurate and the function is not dead.
* **`style_audit.py:200` `[:14]` on MACHINE TELLS.** It looks like the fourth uncut ranking, but
  `:204` prints `({len(a['banned'])} distinct tells present)` immediately after, so the remainder is
  disclosed. Consistent with order 1cb7bd3ad0ce's own scope ("THREE OF THE FOUR RANKINGS").
* **`repass_bands.py:129` `demoted_entries[:8]`.** Labelled "a sample of", with the full count
  printed at `:105` and the complete by-band distribution at `:128`. Consistent with the comment at
  `:110-114`, which deliberately left this one as a declared sample.

## QUESTIONS — two readings are defensible, filed as questions rather than findings

* **`pipeline.py:1911` shadows the module-level `records()` inside `phase_cosmology`**
  (`records = {r["source"]: r for r in WI.load_records()}`). Verified harmless today: the function
  makes no call to `records()` after that line. It is a smell rather than a defect, and renaming it
  is a one-word change — but it is also the kind of shadowing that turns into a `TypeError: 'dict'
  object is not callable` the first time someone adds a `records()` call to that function.
* **`update_handoff`'s phase table (`pipeline.py:1680-1683`)**: `"**built**" if i in IMPLEMENTED
  else "to build"`. Since `IMPLEMENTED` is derived from `PHASES` and all eight `phase_*` functions
  exist, the `"to build"` branch is currently unreachable. That is by construction and the module
  docstring says so explicitly ("The orchestrator still stops cleanly at any gap, should one ever
  reopen"), so it reads as deliberate retention rather than dead code. Recorded, not filed.
