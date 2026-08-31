# run39 — AUDIT batch 08

Modules owned (from `sweep_plan.batches(16)[7]`), all read in full, no sampling:

| module | lines |
|---|---|
| `src/magnitude.py` | 1763 |
| `src/generate.py` | 763 |
| `src/secondopinion.py` | 601 |
| `src/address_space.py` | 486 |
| `src/backfill.py` | 387 |
| `src/thread_integrity.py` | 317 |
| `src/tells.py` | 280 |
| `src/audit.py` | 226 |

Read-only audit. No source file was edited. Every finding below was verified against the
current source (and, where it made a claim about data, against the live files on disk) before
being written down. Where two readings are defensible the item is filed as a QUESTION and not
as a finding.

`tells.py` produced no findings. Everything I suspected there was checked and disproved — see
the DISPROVED section at the end, which is recorded so nobody re-runs those checks next sweep.

---

## MAJOR

### B08-1 — `generate.py:513-559,736-753` a MISCONFIGURED evidence floor is reported as an ordinary holdback, and the run exits 0

`main()` reads the floor as

```python
floor = float(cfg.get("prose_min_cited_fraction", 0.35) or 0.0)      # generate.py:513
```

Note the `or 0.0`: a config value of `0` (or `null`, or `""`) becomes `0.0`. `prose_gate.evidence_ok`
then treats a floor outside `(0, 1]` as MISCONFIGURED and refuses **every** source
(`prose_gate.py:181-185`). Verified live:

```
>>> prose_gate.evidence_ok('One Piece', float(0 or 0.0), None)
(False, 'the evidence floor is 0.0, outside (0, 1] — refusing. A floor of 0 admits a source
 with no citations at all, which is the failure this layer exists for; ...')
```

Every one of those refusals lands in `refused_src` and is printed under the header at
`generate.py:555-559`:

```
EVIDENCE FLOOR — 215 source(s) held back at 0% cited, all of them:
   ...
   These are NOT failures. They are sources the reader has not finished.
```

That footer is a **wrong diagnosis**. Nothing is wrong with the reading; the safety's own
configuration is broken. The run then prints `N total jobs, 0 pending`, `Done. 0 generated this
run, 0 failed this run`, falls off the end of `main()` and exits **0** — a run that did nothing,
reporting exactly like a run that did everything, which is the failure shape this same function
names by hand two branches earlier and exits 1 for:

```python
except Exception as e:                                               # generate.py:516-526
    print("REFUSING EVERYTHING: data/COVERAGE.json unreadable (%s). ...")
    return 1
```

A corrupt `COVERAGE.json` correctly halts loudly; a misconfigured floor — the same class of
fault, a broken safety rather than thin data — halts silently and green. Second, smaller half:
the two misconfigured-floor reason strings at `prose_gate.py:179-185` do **not** name the
source, unlike the other two branches, so the "all of them" listing degenerates into N
identical unattributable lines.

**Remedy.** Ask `evidence_ok` once, before the job loop, with a sentinel source, or have
`evidence_ok` return a third state that distinguishes MISCONFIGURED from BELOW-FLOOR. Route
MISCONFIGURED to the same treatment `COVERAGE.json`-unreadable already gets: its own header
("REFUSING EVERYTHING: the evidence floor is misconfigured"), no "these are not failures"
footer, and `return 1`. Drop the `or 0.0` so an explicit `0` reaches `evidence_ok` as `0` and
is refused as the number it is rather than being coerced first.

### B08-2 — `thread_integrity.py:212-313` the module's findings never reach its exit code, and rc is its only automated reader

`main()` has no `return` statement on any path and is invoked bare
(`thread_integrity.py:316-317`), so the process always exits 0. Its two computed-for-real
classes — `DANGLING` ("every shared entity gone from the live records — the thread points at
nothing") and `PARTIALLY-DANGLING` — change nothing about that.

`allsweep.py:169-171` is the only automated consumer and it reads the rc alone:

```python
# thread_integrity.py's main() returns None and is called bare, so it can only exit nonzero
# by dying. Declared BROKEN because that is what a nonzero would then mean.
Verifier("thread integrity", ["thread_integrity.py"], RC_BROKEN),
```

The module's own comment at `thread_integrity.py:249-252` states the consequence and stops one
step short of it: "main() is the ONLY reporting surface this module has: it writes no JSON, and
allsweep.py runs it as a bare subprocess health check without parsing its output". So a run in
which every implied thread is DANGLING is byte-identical, to the only thing watching, to a run
in which none is. This is the exact defect `allsweep.py:194-199` records as having just been
fixed for `rosetta.py` ("`main()` returned 0 whatever the rhos said... `--check` now exits 1 on
a real disagreement, so this row can actually fail").

**Remedy.** Have `main()` return `1` when `counts["DANGLING"]` (and, on a decision,
`PARTIALLY-DANGLING`) is nonzero, `sys.exit(main())` at the bottom, and change the `allsweep`
row from `RC_BROKEN` to `RC_FINDINGS` in the same change — drift is a finding, not a broken
subsystem. Both halves must land together or the sweep turns red for the wrong reason. Do NOT
give this to the local model: the change touches `allsweep.py`, which is on
`local_agent.DENYLIST`.

### B08-3 — `magnitude.py:1741` the `--calibrate` exit code does not mean what its own comment says it means

```python
return 0 if calibrate() == len(BENCHMARKS) else 1
```

with a comment asserting "the exit code here must mean the same thing the standard it feeds
does". `calibrate()` returns `band_hits`, incremented at `magnitude.py:1518` and
`magnitude.py:1498` on `got_band == band` — **band match only**. The standard it feeds computes
a different verdict:

```python
bad = [r for r in scored if not r.get("consistent")]                 # standards.py:541
holds = bool(scored) and not bad and age_h <= CHARTER_REGRESSION_MAX_AGE_H
```

and `consistent` is the stricter `got_band == band and abs(got_val - val) <= ci + got_ci`
(`magnitude.py:1523`). The two disagree in both directions:

* six band matches whose decimals all sit outside the combined intervals → `calibrate()` returns
  6, exit **0**, standard **red**;
* four benchmarks that could not be scored at all plus two consistent ones → `band_hits` is 2,
  exit **1**, while `charter_regression_verdict` returns `holds=True` (it requires
  `bool(scored)` and zero inconsistent rows, not that every benchmark scored).

**Remedy.** Have `calibrate()` return the verdict rather than a count — reuse
`standards.charter_regression_verdict` on the payload `_land()` just wrote, so there is one
implementation of the question and not two — and exit on that. If a count is still wanted for
the console, print it separately from the value `main()` gates on.

### B08-4 — `audit.py:190-193` offender lists are cut to four and the names past four are recorded nowhere

```python
for x in v[:4]:
    print(f"       - {x}")
if len(v) > 4:
    print(f"       ... and {len(v)-4:,} more")
```

`audit.py` writes no artifact of any kind — no `json.dump`, no `write_json` — so `main()`'s
stdout is the only place these names ever exist, and `allsweep.py:174` runs it as a subprocess
reading only the rc. Measured live on the current corpus:

```
   177  entry: wiki navigation artefact, not an entity
    66  entry: empty description
    57  entry: description too short to be evidence
    34  synthesis: ceiling entity not among the source's own entries
```

334 offenders exist; 16 are ever named. The remaining 318 are reachable only by re-running the
audit with the code edited. This is the shape the project has already filed and fixed three
times under exactly this argument — `backfill.py:312-320` (order 03c0fe609e89),
`generate.py:548-554` (order 4e437987e382), `thread_integrity.py:246-255` (order 8b08d0ecec8d) —
and `generate.py:307-310` states the house standard verbatim: *"no cap, no 'and N more' — because
this is the listing a person reads to decide whether the coverage number means anything"*.
`audit.py`'s own `_field` docstring at `audit.py:49-61` cites the same doctrine (order
01eff1b24759) for the SAMPLE pass and leaves the INVARIANTS pass capped.

**Remedy.** Print every occurrence, ranked, with the count in the header — the same fix
`backfill.py --audit` took. The population is bounded by the corpus and is 334 today. If a class
can plausibly run to five figures, write the full list to an artifact alongside the console
summary rather than reintroducing a cap.

---

## MINOR

### B08-5 — `magnitude.py:736` stale cross-reference `assay.py:930`

`_status_score`'s docstring: *"INAPPLICABLE leaves the coverage denominator entirely
(assay.py:930)"*. Verified: `assay.py:930` is `raise AssayIntegrityError(` inside the
zero-weight-denominator refusal, which is about a weights table, not about INAPPLICABLE. The
line the sentence describes is **`assay.py:945`**:

```python
applicable = [k for k in W if scores.get(k) != INAPPLICABLE]
```

The sibling citation on the line above (`assay.py:174`, "It earns full coverage credit, because
it IS knowledge") is CORRECT and verified — only the second one has drifted.

**Remedy.** Change `assay.py:930` to `assay.py:945`, or cite the symbol (`assay.assay`'s
`applicable` filter) as `secondopinion.py:28-31` argues for: *"a line number in prose is a
citation with a decay rate."*

### B08-6 — `generate.py:619` stale cross-reference `pipeline.py:2122`

The comment claims *"`pipeline.py:2122` states the ban 'is enforced in code like scale_note and
the Marginalia cap before it'"*. Verified: `pipeline.py:2115-2130` is the Hard Rule 2 /
unspined-source block and contains no such sentence. The quoted sentence is at
**`pipeline.py:2621`**, immediately above `meta_violations` (2635) and `assert_in_universe`
(2640). A transposition of `2621`.

**Remedy.** `pipeline.py:2621`, or cite `pipeline.assert_in_universe` by name.

### B08-7 — `address_space.py:459-460` two stale cross-references in one sentence

The justification for gating the `SHELFMARKS.json` write cites its two readers by line:

```python
# Windows case here, since `pipeline.py:2024` reads this file as a phase input and
# `standards.py:1009` reads it on its own clock, and either holding it open is enough --
```

Verified, both wrong:

* `pipeline.py:2024` is `tiersd = json.load(open(_tp, ...))` — reading **TIERS.json**, not
  SHELFMARKS.json. The phase-input read of SHELFMARKS.json is `pipeline.py:2138`
  (`marks, m_bad = _phase_input("SHELFMARKS.json")`), and the other read is `pipeline.py:1971`.
* `standards.py:1009` is inside the "unexpected swallowed failures" standard and does not touch
  SHELFMARKS.json. The read is `standards.py:1177`.

The *reasoning* is sound (both modules do read the file concurrently) — only the citations are
stale, which is the worse case, because a reader who follows either one finds unrelated code and
concludes the whole argument is fabricated.

**Remedy.** `pipeline.py:2138` and `standards.py:1177`, or cite
`pipeline._phase_input("SHELFMARKS.json")` and the `standards.py` reader by symbol.

### B08-8 — `magnitude.py:157-165` `_ask` still forces a runner rebuild on the DEFAULT split path, on a premise that is no longer true

```python
# Sized, not defaulted: a split slice is ~8k chars and fits 4096 tokens with room; the
# config default of 6144 was both too big for slices (wasted KV on a shared card) and
# too small for anything larger (Ollama truncates the tail silently, no error).
nc = 4096 if len(prompt) + len(system) < 11000 else 8192
return P.ask(c, system, prompt, schema, timeout=timeout, num_ctx=nc, tag="assay-split")
```

Two verified problems.

1. **The stated premise is stale.** `config.yaml:82` declares `num_ctx: 12288`, not 6144. The
   sentence justifying this branch describes a default that no longer exists.
2. **This is the same fault order 706215aabc5f fixed one function down, still live here.**
   `assay_entity`'s local one-shot carries that fix and its reasoning verbatim
   (`magnitude.py:1180-1187`): *"Asking for 8,192 anyway bought a runner REBUILD, not a bigger
   window, because Ollama holds a model at one size. Order 706215aabc5f."* That call site
   correctly stopped passing `num_ctx` and now inherits config's 12288
   (`pipeline.py:420-421`, `num_ctx or c.get("num_ctx", 6144)`). `_ask` was not touched, and
   `_ask` is the **split** transport — the default for everything over `ONE_SHOT_MAX`, i.e. the
   heaviest entities, called once per slice per axis with `max_workers=6`
   (`magnitude.py:936-979`). Each slice that crosses the 11,000-character line flips the runner
   between 4096 and 8192 and back.

Filed with the tension stated rather than as a clean bug, because the two comments in this one
file argue opposite sides: the older one wants a small window to save KV on a shared card, the
newer one says a mismatched request costs a full model reload. That is a decision to make, not a
typo to correct.

**Remedy.** Decide once and record the ruling. If order 706215aabc5f's finding holds — and it
was measured — drop the `num_ctx=` argument from `_ask` so every magnitude call runs at the one
declared window. Either way, delete or correct the "config default of 6144" sentence, which is
false today whichever way the decision goes.

### B08-9 — `address_space.py:214-215` `shelfmark()` drops the 27-bit `star` field entirely

`FIELDS` has eight fields; `shelfmark()` prints seven:

```python
return (f"Ω › H{f['hyperverse']} › X{f['xenoverse']} › Mt.{f['metaverse']} › "
        f"Mv.{f['multiverse']} › U-{f['universe']} › G.{f['galaxy']:x} › P.{f['planet']}")
```

Verified live:

```
>>> AS.WIDTHS
{'hyperverse': 3, 'xenoverse': 2, 'metaverse': 3, 'multiverse': 8,
 'universe': 6, 'galaxy': 38, 'star': 27, 'planet': 1}       # TOTAL_BITS 88
>>> a = pack(..., star=1, ...); b = pack(..., star=2, ...)
addr differ: True
shelfmark same: True   Ω › H1 › X1 › Mt.1 › Mv.1 › U-1 › G.1 › P.1
```

So the published name distinguishes 2^61 of the address space's 2^88 positions. It matters
beyond cosmetics because `seed_from_card` (`address_space.py:248-264`) hashes the shelfmark as
the world's generator seed and argues explicitly that a reader holding the printed volume must
be able to recompute the map — two worlds one bit apart in `star` therefore share a shelfmark
AND a terrain.

**No live collision today**: all 1,016 rows in `data/SHELFMARKS.json` have distinct addresses,
distinct shelfmarks and distinct map seeds, because the 38-bit galaxy draw absorbs the
variation. This is latent, not broken.

**This is filed with the counter-reading stated.** The charter's own worked Shelfmark, quoted at
`address_space.py:98`, is `Ω › H? › X? › Mt.ASC › Mv.DRG › U-7 › G.North › P.Earth` — seven
tiers, no star. So the omission may be faithful to Part Two and the defect may instead be that
`FIELDS` reserves a field the notation cannot express. Either way one of the two is wrong and
the module does not say which.

**Remedy.** An owner ruling on which is authoritative. If the notation is: `star` should not be
a field, or `shelfmark()` should state out loud that it is a lossy projection of the address and
`seed_from_card` should key on the address rather than the printed name. If the address is:
add an `S.` element to the format string — note that doing so **re-addresses every world's map
seed**, which `address_space.py:283-291` already flags as requiring an owner's ruling for the
sibling case of the hash offsets.

### B08-10 — `magnitude.py:1141-1143,1344-1347` the two PERMANENT record shapes are the two that omit `host`

Every return in `assay_entity` carries `"host": host` except two:

```python
return {"entity": entity, "result": None,
        "reason": "no axis cleared its gate on this entity's own source pages"}   # :1143
```
```python
return {"entity": entity, "result": None, "anchor": anchor,
        "reason": "sheet saturated: ...", "rejections": rejects}   # :1344
```

Those are exactly the two reasons `settled()` (`magnitude.py:1606-1626`) calls a FINDING and
never recomputes — so they are the records that stand for ever. Verified on disk:

```
data/ASSAYS.json: 507 records, 10 without 'host'
  7  "no axis cleared its gate on this entity's ..."
  3  "sheet saturated: every scored axis at th..."
```

The dict key (`h + "|" + n`) still carries the host, so nothing is lost outright, but any reader
doing `rec["host"]` raises on 10 of 507 rows and any reader doing `rec.get("host")` silently
attributes them to nothing.

**Remedy.** Add `"host": host` to both returns. Existing rows keep their shape until re-assayed,
and `settled()` will not re-run them — that is accepted the same way
`magnitude.py:1339-1341` already accepts it for the truncated instrument worksheets.

### B08-11 — `magnitude.py:852-855` guard 4's docstring is stronger than guard 4

```python
def saturated(scores):
    """Guard 4. Every scored axis at the top means the model did not refuse anywhere."""
    nums = [v for v in scores.values() if isinstance(v, (int, float))]
    return len(nums) >= 6 and min(nums) >= 9.0
```

"Every scored axis at the top" describes `min(nums) >= 9.0`. The `len(nums) >= 6` conjunct is an
additional, undocumented condition: a sheet with five axes all at 9.9 and six statuses is
*every* scored axis at the ceiling and is not caught. The module docstring's statement of guard 4
(`magnitude.py:43-44`) is the same unqualified claim, and its motivating incident — "all eleven
axes scored 9.9" — is silent on where the line sits.

Filed as a doc/behaviour mismatch, not as a wrong threshold: a floor on the number of scored
axes is defensible (three axes at 9.9 on a genuinely extreme entity is not evidence of a
non-refusing model), and `SYSTEM` itself tells the model that "Most entities have evidence for
two or three axes", which makes a low-N saturated sheet common and probably honest.

**Remedy.** State the threshold and its reason in the docstring and in the module's guard-4
paragraph. If 6 is not the intended number, that is a separate ruling.

### B08-12 — `magnitude.py:1683-1714` the batch summary conflates a refusal with a deferral

```python
if (r.get("result") or {}).get("decimal") is not None:
    tally["scored"] += 1
else:
    tally["band_only"] += 1
...
print("band-only or refused  : %d" % tally["band_only"])
```

A `status: DEFERRED` record has `result: None`, so it is counted as "band-only or refused". It
is neither: `settled()` returns False for it and the next run picks it up. `settled()`'s own
docstring (`magnitude.py:1607-1619`) is written entirely around this distinction — *"Everything
else is a transport failure wearing a result's clothes"* — and the summary line, which is the
only thing an operator reads at the end of an hours-long batch, throws it away. An entire batch
lost to a rate-limited pool prints identically to a batch of honest refusals.

**Remedy.** Three counters against `settled(r)` / `status == "DEFERRED"`: scored, refused
(no-gate + saturated), deferred. Print all three. `settled()` already computes the predicate.

### B08-13 — `secondopinion.py:564-577` the DISAGREEMENT line fires on two conditions that are not disagreement

```python
if ds["status"] == "RAN" and not ds["findings"] and mine["secrets"] == 0:
    print("  AGREEMENT: ...")
elif ds["status"] == "RAN":
    print("  DISAGREEMENT: detect-secrets found %d and publish.scan_for_secrets found %s. ..."
          ... "Two independent scanners differ; that IS the finding this module exists to "
              "surface.")
```

Two verified false positives:

* **The house scanner errored.** `mine_says` sets `out["secrets"] = None` on any exception
  (`secondopinion.py:419-421`). `None == 0` is False, so the `elif` fires and prints
  *"detect-secrets found 0 and publish.scan_for_secrets found None. Two independent scanners
  differ; that IS the finding"* — a tool that did not run, reported as a tool that disagreed.
  That is precisely the confusion this module's own docstring (`secondopinion.py:61-65`) exists
  to forbid: *"An optional tool that is not installed produces no findings, and no findings looks
  exactly like a clean bill of health."* Here it is the mirror: a tool that could not answer
  looks exactly like a tool that dissented.
* **Both found the same thing.** If both scanners find one real secret, the AGREEMENT branch is
  skipped (it requires `not ds["findings"]`) and the run prints
  *"DISAGREEMENT: detect-secrets found 1 and publish.scan_for_secrets found 1"* — a sentence that
  contradicts its own numbers.

**Remedy.** Three branches keyed on the comparison rather than on zero: `mine["secrets"] is None`
→ "the house scanner could not answer; this is unmeasured, not a disagreement";
`len(ds["findings"]) == mine["secrets"]` → AGREEMENT (say whether it is agreement on zero or on
a count); otherwise DISAGREEMENT.

### B08-14 — `backfill.py:233-253` titles dropped between `queued` and `added` leave no trace

The write loop drops a title on two silent paths:

```python
pages = F.fetch(host, missing[i:i + 40])
for title, wt in pages.items():
    desc = lead(wt)
    if len(desc) < 40:
        continue # a stub is not a record
```

* `F.fetch` returns only titles it actually resolved — `feats.py:1007-1014` skips a page that is
  `missing` or has no revisions, and skips a bad revision after a `silence.note`. Nothing here
  compares the returned set against the requested one.
* the `len(desc) < 40` stub filter drops the rest, uncounted.

The result dict reports `queued` and `added` and nothing between them, so `added < queued` has no
explanation on the page. This module's whole subject is telling near-identical outcomes apart —
it already added `size_lookup_failed` (order 0a67628cfa8f) and `write_denied` (order
f57f145468f7) for exactly this reason, and `main --all`'s comment at `backfill.py:336-345` says
so: *"THE OUTCOMES backfill_source IS CAREFUL TO DISTINGUISH USED TO DIE HERE."*

**Remedy.** Two counters — `not_fetched` (requested minus returned, per batch) and
`dropped_as_stub` — returned in the result dict and summed into `main --all`'s closing line
beside `size_lookup_failed`.

### B08-15 — `backfill.py:145-152` `lead()` can return a mid-word 420-character cut with no marker

```python
cut = block[:chars]
dot = cut.rfind(". ")
return (cut[:dot + 1] if dot > 120 else cut).strip()
```

When the 420-character window contains no `". "` past index 120, the `else cut` arm returns the
raw slice — cut mid-word, with nothing saying so — and that string becomes the `description`
field of a record written to `data/records/*.json` (`backfill.py:239-252`), which Hard Rule 1
makes the substrate every generated entry is dressing on. The fallback path at
`backfill.py:149-152` has the identical shape. Compare `secondopinion._message`
(`secondopinion.py:97-109`), which settles the house position on this: display truncation is
fine *because it is reversible*, and refused when nothing marks it.

Genuinely arguable — a "lead extract" is not a truncated value in the way a roster is — which is
why it is MINOR and not MAJOR. But the marker costs one character.

**Remedy.** Append `chr(8230)` when the returned string is not sentence-terminated, matching
`_message`. Alternatively raise the sentence-boundary floor so the `else cut` arm is only ever
reached for a genuinely unpunctuated block.

### B08-16 — `audit.py:80-93` a synthesis with no band produces up to three fail rows, two of them mislabelled

```python
band = syn.get("provisional_magnitude")
if band not in VALID_BANDS:
    fails["synthesis: band not on the ladder"].append(f"{src}: {band!r}")
if band != "unassayed" and not ce:
    fails["synthesis: band claimed with no ceiling entity"].append(src)
...
if band != "unassayed" and not PL.valid_scale_note(ev):
    fails["synthesis: band rests on evidence that is not a scale feat"].append(...)
```

`PL.BANDS` is `['M10'...'M0', 'unassayed']` (verified) and contains no `None`, so a synthesis
missing the key takes the first branch correctly and then takes both `band != "unassayed"`
branches as well — reporting "band claimed with no ceiling entity" and "band rests on evidence
that is not a scale feat" about a synthesis that claims no band at all. Two of the three rows are
false statements about the fault, in the one report whose premise (`audit.py:7-9`) is checking
the pipeline's claims from outside.

**LATENT: zero occurrences today.** Verified — 0 of 210 synthesis rows are missing
`provisional_magnitude`. Filed because the guard reads as though it had considered the case.

**Remedy.** `elif` the two dependent checks onto the ladder check, or gate them on
`band in VALID_BANDS and band != "unassayed"`.

---

## INFO

### B08-17 — `magnitude.py:858,872-873` `candidates(ev, cap=None)` carries a truncation lever nothing pulls

```python
def candidates(ev, cap=None):
    ...
    return {ax: sorted(v, key=lambda r: -len(r["feat"]))[:cap] if cap
            else sorted(v, key=lambda r: -len(r["feat"])) for ax, v in out.items()}
```

Both callers pass no cap (`magnitude.py:1140`, `sweep.py:188`), verified by grep. The docstring's
own body argues against it — *"never truncated: capping at six decided that an entity with forty
pieces of Ruin evidence had six"* — while the signature keeps the parameter that would do it.
Harmless today; it is a loaded gun sitting under a comment explaining why it must never be fired.

**Remedy.** Delete the parameter and the conditional. If it is kept for a future caller, the
docstring should say who and under what ruling, since Hard Rule 0 forbids the only thing it does.

### B08-18 — `backfill.py:67-74` `roster()`'s docstring describes a default limit the signature no longer has

```python
def roster(host, limit=None):
    """...
    The limit is deliberately far above any real roster. ..."""
```

There is no default limit — it is `None`, and `backfill_source` calls `roster(host)` with no
limit at all (`backfill.py:176`), which is correct per Hard Rule 0 and per the comment at
`backfill.py:118-122` ("NO CAP"). The docstring is describing a previous design.

**Remedy.** Rewrite the paragraph to say what is true: the roster is enumerated in full, `limit`
exists for callers who want a bounded probe, and the historical Dragon Ball A-through-G incident
is why the default is None.

### B08-19 — `thread_integrity.py:125` an always-false disjunct

```python
for (a, b), shared in pairs.items():
    if (b, a) in seen or (a, b) in seen:
        continue
    seen.add((a, b))
```

`pairs` is a dict, so each `(a, b)` is yielded exactly once, and `seen` only ever receives keys
already visited. `(a, b) in seen` can therefore never be True. Harmless — the `(b, a)` arm is the
one doing the work and it is correct — but it is a comparison that cannot fail, which is the
mechanical shape `liveness.py` is pointed at and `drill.py` ratchets.

**Remedy.** Drop the second disjunct, or leave it and note why (defensive against a future
caller passing a list of pairs rather than a dict).

### B08-20 — `address_space.py:326-327` `assign()`'s docstring omits `universe` from the hashed fields

*"Galaxy, star and planet remain unknown in the sources and are hashed from the designation"* —
but `_HASHED_FIELDS` is `("universe", "galaxy", "star", "planet")` (`address_space.py:293`) and
`assign` calls `drawn("universe")` at `address_space.py:364`. So the `U-7` element of a printed
shelfmark is a hash draw, not a measurement, and the docstring reads as though it were charted
alongside the four tiers above it. `shelfmark()`'s docstring (`address_space.py:203-208`)
compounds this slightly: *"what prints is a measurement, not a filled-in blank"* — true of H and
X, which is what that paragraph is about, and not true of U, G or P.

**Remedy.** Name all four hashed fields in `assign`'s docstring, and scope `shelfmark`'s
"measurement" sentence to H/X/Mt/Mv explicitly.

### B08-21 — `thread_integrity.py:44-75` `load_entities()` builds a name map used only for its length

`names` maps normalised key → first-seen original name and is returned; `main()` reads it once,
at `thread_integrity.py:219`, as `len(names)`. Every original name is retained for a count. Not a
defect — the map is the obvious thing to want when a DANGLING row is printed — but as it stands
the DANGLING/PARTIALLY-DANGLING listings print source pairs and never the entity keys that
drifted, so the data collected is the data not shown.

**Remedy.** Either drop `names` and count `len(set of keys)`, or use it: print the drifted keys'
readable names beside each PARTIALLY-DANGLING row, which is what a reader needs to act on the
finding.

### B08-22 — `address_space.py:452` a display cap with no marker

```python
for d, a in list(addrs.items())[:6]:
```

The count is printed two lines above (`worlds addressed : {len(addrs):,}`), so this is honest by
the corpus_db `_cell` standard, and the full data lands in `data/SHELFMARKS.json` on the next
line, so nothing is only reachable by re-running. Recorded for completeness, not as a
violation — this is the case where a display cap is fine, and it is noted so the next sweep does
not re-file it.

---

## QUESTIONS (two defensible readings; not filed as findings)

**Q1 — `secondopinion.py:452-456` files every rule order with `handler="LOCAL"` regardless of
which files the sites are in.** A `BLE001` order whose `where` lists `escalation.py:412,
drill.py:88` is addressed to the local model, and every one of those modules is on
`local_agent.DENYLIST` (`local_agent.py:64-90`). Not filed as a defect because
`local_agent._denied_target` is asserted to be what `t_propose_patch` actually asks before
writing, so the refusal happens at the right layer and the order is simply unworkable rather
than dangerous. Worth an owner's view on whether an order the assigned handler can never work
should be filed to that handler at all.

**Q2 — `magnitude.py:1652-1655` `host_ceiling` caches a `None` result for the whole run.** Both
lookup failures are recorded via `silence.note`, so this is not silent, and proceeding without a
clamp is a defensible fail-open. But the clamp is what the docstring credits with catching Jace
Beleren at M10.77 against a published M2.88, and a run in which `SCOPE.json` is briefly
unreadable will assay every entity on that host unclamped for the rest of the batch with no mark
on the resulting records. Whether the record should carry `ceiling: null` is a judgment call.

**Q3 — `generate.py:359-362, 399-402` the retry-acceptance test is unreachable in one degenerate
case.** `if retry.strip() and len([...not covered in retry...]) < len(lacking)` — when the retry
was triggered by `not text.strip()` alone with `lacking == []`, the comparison is `n < 0`, always
False, so a good retry would be discarded and the block would raise "empty response". Reaching it
requires an empty model response over a block whose entities all have empty names (`_covered`
returns True on an empty name, `generate.py:255`), so it is not reachable with real manifest data.
Recorded rather than filed.

---

## DISPROVED — checked and found NOT to be defects

Recorded so the next sweep does not spend the same time.

* **`tells.py` duplicate patterns / an overstated `_WATCHED`.** Measured:
  `LEXICAL + LEXICAL_FICTION` is 92 entries, 92 unique; `_LEX` is 92, `_COMPILED` is 46;
  `style_audit._WATCHED` is 138 = 92 + 46 exactly. No key collides between `STRUCTURAL` and
  `DISCOURSE`. The count is honest.
* **`tells.py` overlapping lexical entries double-count a rate.** "myriad of" does fire both
  `word: myriad` and `word: myriad of`. Checked the consumer: `style_audit.py:137-140` accumulates
  into a Counter keyed by name and reports a per-tell rate, never a summed total, so each row is
  correct for its own pattern. Not a defect.
* **`tells._anchor` strips the wrong number of characters.** `r"^\s*"` is exactly 4 characters, so
  `pat[4:]` is exact.
* **`tells.prompt_in_sync` is a safety nobody calls.** It has a live caller:
  `standards.py:958-972`. In effect.
* **`magnitude.AXIS_LEXICON` may not cover every axis in `assay.WEIGHTS`.** `AXIS_RE[ax]` is
  indexed unguarded at `magnitude.py:827`. Measured: the two key sets are identical, both
  directions empty. No KeyError is reachable.
* **`backfill.py` may mis-parse the MediaWiki `pages` response as a dict.** `feats.api` stamps
  `formatversion: "2"` on every query (`feats.py:448`), so `pages` is always a list. Correct.
* **`secondopinion.py:391` cites `src/liveness.py:197` for `def scan()`.** Verified correct.
* **`magnitude.py:735` cites `assay.py:174` for NONE earning full coverage credit.** Verified
  correct — that line reads "this band. It earns full coverage credit, because it IS knowledge."
* **`address_space.py:475` cites `handoff/run35/checks_L4.py`.** The file exists.
* **`audit.py` core invariant "no feat, no band" is failing.** Measured on the live corpus: 244
  banded entries, 278 with a scale note, **0** occurrences of "entry: BAND WITH NO SCALE NOTE".
  The invariant holds.
* **`thread_integrity.py:288` cites its own `:188` for where ASYMMETRIC-LAWFUL detail is
  computed.** Verified correct.
