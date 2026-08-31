# run39 — AUDIT, batch 12

Modules owned (obtained from `sweep_plan.batches(16)[11]['modules']`, not from any typed list),
every one read IN FULL, no sampling:

    src/read.py                       1,384 lines
    src/health.py                       930
    src/identity.py                     700
    src/ingest_doc.py                   542
    src/sevenfold.py                    421
    src/deprecated/catalogue_local.py   333
    src/entity_match.py                 296
    src/scale_theories.py               174
    src/catalog.py                      138
                                      -----
                                      4,918

Read-only audit. No source file was edited. Every finding below was re-checked against the
current file (and, where it is a claim about another file, against that file too) before being
written down; where two readings are defensible it is filed as a QUESTION at the end rather
than as a finding.

Existing open orders were read first (`state/workorders.json`, 166 open) so that nothing here
duplicates one. `SWEEP34_FINDING` already covers `scale_theories.py`'s dead module, dead
functions and five unread constants — **not re-filed**.

---

## MAJOR

### M1. `read.py:160-191` — `_names()` cannot recognise 4,939 catalogued entities by name at all, and the feats it drops are counted as an honest absence

`_names(sentence, entity)` decides whether a verbatim-verified sentence is actually ABOUT the
entity. Its name test is:

```python
parts = [w for w in re.split(r'[^A-Za-z]+', entity) if len(w) > 3]      # :168
if any(t.startswith(w.lower()) for t in re.split(r'[^a-z0-9]+', low) if t for w in parts):
    return True                                                          # :183
```

`parts` has **no fallback**. When the entity's name contains no ASCII word longer than three
characters, `parts == []`, the `any(...)` is vacuously False, and the ONLY remaining route to
True is the personal-pronoun set at :189-191. Every sentence that names the entity outright and
uses no pronoun is dropped and tallied as `generic` → `generic_dropped`, whose documented
meaning at :844-848 is the opposite thing: "a techniques index describes moves generically ...
a rulebook entry, not a feat anybody performed."

Two independent causes, both verified:

* **the `len(w) > 3` floor** — short names. Measured over the live corpus
  (`pipeline.records()`, 282,822 named entries): **4,939 entries have no name-word longer than
  three characters.** `Ash`, `Vi`, `Ike`, `Uub`, `Omu`, `BMO`, `The Six`, `Mr. Fox`, `Kim`,
  `Lee`, `Ed`, `Moe`, `Air`, `Gum`.
* **the ASCII-only split** — `[^A-Za-z]` treats every accented or non-Latin letter as a
  separator, so a name shatters into short fragments. 3,064 catalogued names contain a
  non-ASCII letter; **391 of them are left with no usable word** by this split alone:
  `Môrgæn`, `Shānmén`, `Quảng Trị`, `Huế`, `Cádiz`, `León`, `Orléans`, `Aulë`, `König`,
  `Núñez`, `El Niño`.

Verified live against the code and against the cache:

```
read._names('Ash defeated the Gym Leader in a single blow.', 'Ash')  -> False
read._names('He defeated the Gym Leader in a single blow.',  'Ash')  -> True
read._names('The Six shattered the barrier around the citadel.', 'The Six') -> False
read._names('Goku destroyed the planet.', 'Goku')                    -> True
```

And in `data/readfeats`, over the first 1,835 records scanned, **38** belong to such entities
AND carry `generic_dropped > 0`: `Ike` 22 dropped / 46 kept, `Suì-Fēng` 21 / 31, `Uub` 21 / 19,
`Gem` 19 / 1, `Mai` 13 / 14, `Psi` 10 / 2, `Ray Gun` 9 / 1, `Bat` 8 / 14, `Copán` 2 / **0**.

The cost is not just a filter miss. `read_entity` at :731 gives the CHUNK-SELECTION filter the
fallback this function lacks — `keys = [...] or [name.lower()]` — so chunks for these entities
ARE selected, the model IS called, feats ARE returned and verbatim-verified, and only then are
they thrown away. GPU/pool spend is incurred and the evidence is discarded, and because
`unanswered == 0` the record is written to the permanent cache as a finished read
(:876-892). By this module's own doctrine that is the unrecoverable direction: the entity is
filed as having no feats in a passage that describes its feats.

The house already has a Unicode-safe fold: `feats_index._norm` uses `c.isalnum()`, which keeps
accents (verified at `feats_index.py:106-126`). `read._names` hand-spells a fifth, ASCII-only
convention — the exact drift `cachekey.py`'s docstring exists to end.

Remedy (per read.py's own run-#3 precedent at :176-182, this is a matching change and is not
verified until the whole corpus is diffed): give `_names` the same "or the whole name" fallback
`read_entity` already has, lower the floor when no long word exists, and split on a
Unicode-aware class rather than `[^A-Za-z]` / `[^a-z0-9]`. Then diff every `readfeats` record
before shipping and report kept/dropped both ways, exactly as the 39,198-sentence diff at
:176-182 did.

Filed: `READ_NAMES_DROPS_SHORT_AND_NONASCII_ENTITIES`, MAJOR, RUN.

### M2. `read.py:1320-1321` — the closing line of a reading pass omits the one number that says whether the pass read anything

`run()` tracks `done["unanswered"]` (:1204) and prints it in the every-five-entities progress
line as `%d UNANSWERED, not cached` (:1244). The FINAL line — the one an operator or a log
scrape actually keeps — is:

```python
print("done in %.2fh  %d feats kept, %d fabrications dropped, %d chunks skipped" ...)
```

No unanswered count. This module's own comments call that number the whole difference between
a pass and a fiction: :872-875 records "4,755 of 6,706 chunks in a single pass hit a benched
GPU ... Seventy-one percent of the passages in that pass were never seen by any model", and
`_local`'s docstring at :530-540 records 1,168 of 1,235 chunks unanswered over 7.5 hours by
"a job that looked healthy". A run in exactly that state still finishes on a line that says
"done in 7.50h, 0 feats kept, 0 fabrications dropped".

Remedy: print `done["unanswered"]` (and the entity-level failure count from M8) on the closing
line, and say plainly when it is non-zero that those entities were NOT cached and will be
retried.

Filed: `READ_RUN_FINAL_LINE_OMITS_UNANSWERED`, MAJOR, LOCAL.

---

## MINOR

### m3. `read.py:217-219` — `CASCADE_TRIES`'s comment is stale in two independent ways

```python
# Attempts through the pool before a chunk is handed to the local GPU. Each attempt claims a
# different bucket, so three is three providers, not one provider three times.
CASCADE_TRIES = 5
```

(1) The constant is **5**, the comment says **three**. (2) More seriously, the comment describes
the OLD ladder order. In the current `_ask_ungated` the GPU is tried at :396-401 *before* the
`for attempt in range(CASCADE_TRIES)` ladder at :403-413 — the change the comment block at
:377-387 documents ("two quick attempts at the pool, then the GPU, and only if BOTH decline
does the backoff ladder start"). So `CASCADE_TRIES` is the count of attempts made AFTER the GPU
has already declined, not "before a chunk is handed to the local GPU".

Filed with m4.

### m4. `read.py:58-73` — the entire CHUNK sizing argument rests on a `num_ctx` the config no longer uses

The header comment states three times that "num_ctx is 6144 tokens" and derives CHUNK=10000
from it. `read.config()` (:586-591) returns `cfg.get("num_ctx", 6144)` and **`config.yaml:82`
holds `num_ctx: 12288`**; `pipeline.ask` (:420-421) passes `num_ctx or c.get("num_ctx", 6144)`
straight to Ollama, so the real window is twice the stated one. Nothing is broken — the error
is in the conservative direction and the measured recall argument at :75-93 says the chunk
should stay small regardless — but the premise every reader is asked to trust is false, and
`health.check_context_budget` grades against the config value, so nothing anywhere would
notice. Same for `_local_carded`'s 360s/180s sizing note at :555-560.

Filed: `READ_STALE_TRANSPORT_AND_CTX_PREMISES`, MINOR, LOCAL.

### m5. `read.py:735` and `read.py:1261` — a conditional that cannot differ

```python
size = CLOUD_CHUNK if _CASCADE_OK else CHUNK
```

`CLOUD_CHUNK = CHUNK` since :94 ("the cloud unit is the local unit"), so both arms are the same
value and the transport flag decides nothing here. `read.py:441-443` already says so in a
comment ("CLOUD_CHUNK == CHUNK now (:94-96) -- there is no longer a cloud/local size difference
for this to compensate for") and the two live conditionals were not visited. Harmless today;
it reads as a live policy switch and would be believed by the next reader. `health.py:459` has
the mirror of it — it measures `R.CHUNK` only, so a re-divergence would go unchecked on the
cloud side.

Filed: `READ_CLOUD_CHUNK_CONDITIONAL_IS_INERT`, MINOR, LOCAL.

### m6. `read.py:1370` — an unmarked mid-value cut, immediately under a comment declaring this loop uncapped

```python
# NOT SLICED (order a84c002fb0e3, Hard Rule 0). This used to print `out["feats"][:12]` ...
for f in out["feats"]:
    print("   %-14s %s" % (f["axis"], f["feat"][:104]))
```

The LIST is no longer capped; each ROW is still cut at 104 characters with no ellipsis and no
"n chars omitted" marker, on the one interactive path whose stated purpose is "so a person can
look at everything that was mined for one entity". A truncated feat sentence read off this
screen cannot be checked against the page it was verified against.

### m7. `read.py:1179-1180` — two row fields nothing reads, one of them truncated

```python
rows.append(dict(row, name=e["name"], host=h, source=r["source"],
                 category=(e.get("category") or "?")[:20]))
```

`read.queue()` has exactly one caller (`read.run()`, :1187 — verified by grep across `src/`;
`priority()` is otherwise touched only by `verify_math`), and `work(r)` reads only `r["host"]`
and `r["name"]`. `source` and `category` are written and never read, and `category` is cut at
20 chars on the way in. Either they are diagnostics, in which case they should be printed
somewhere and not truncated, or they are dead.

m6 and m7 filed together: `READ_ONE_DISPLAY_TRUNCATION_AND_DEAD_ROW_FIELDS`, MINOR, LOCAL.

### m8. `read.py:1195-1200` — a per-entity crash is swallowed into an unreported skip

```python
try:
    out = read_entity(...)
except Exception:
    silence.note("read.py:work-read-entity")
    out = None
```

`done["n"]` is still incremented, so the entity counts toward "N/M" and toward completion, and
no counter anywhere distinguishes "this entity raised" from "this entity had nothing". The
`silence` ledger records the class, which is the right floor, but the run's own report cannot
say how many entities it failed on. Remedy: a `done["errored"]` counter, printed on the
progress line and the closing line beside `unanswered`.

Filed: `READ_WORK_SWALLOWS_PER_ENTITY_FAILURE_UNCOUNTED`, MINOR, RUN.

### m9. `health.py:279` and `health.py:295` — a citation into `foreman.py` that has drifted, in the file that argues against exactly this

Both comments cite `foreman.py:237` as the source of the sentence *"state/failures.json is the
highest-traffic shared file in the project -- the dashboard polls it, standards reads it, and
EVERY process read-modify-writes it through health.flush()."* Verified: `foreman.py:234-240` is
the body of a `scout` remedy helper (`SC.sweep(limit=4)` / `silence.note("foreman.py:scout_hostless")`)
and contains none of that. The real sentence is at **`foreman.py:294-296`** (and it is quoted
again at 301).

This is the same defect `summary()`'s own docstring at :405-418 was corrected for, with the
rule already written down: *"Line numbers in another file are a citation with a short shelf
life."* That correction fixed the two citations in `summary()` and left these two, twenty lines
away. Remedy: cite `foreman.py` by symbol (the function holding the write) as `summary()` now
does by `silence.note` tag, or re-point to 294.

Also verified as still CORRECT and left alone: `summary()`'s "dashboard.py:350-360 and
standards.py:1000-1028" — `silence.note("dashboard.py:failures")` is at `dashboard.py:360` and
`silence.note("standards.py:ledger")` at `standards.py:1027`.

Filed: `HEALTH_STALE_FOREMAN_CITATION`, MINOR, RUN.

### m10. `health.py:861` — the preflight stamp truncates its rows before `workorders` ever sees them

```python
rows.extend({"check": label, "what": str(a)[:200], "detail": str(b)[:300]}
            for a, b in found)
```

Those rows are the machine-readable trace the whole `stamp` mechanism exists to leave
(:839-850), and `workorders.sweep_detectors` files them verbatim as `evidence: rows` (verified
at `workorders.py:154-166`, where the sibling `rows[:20]` cap was already removed for being a
silent tail drop). `workorders.file_order` removed *all* of its own field caps under Hard Rule
0 for the stated reason that "a work order's REMEDY is written at the END" and 51 open orders
had been cut at exactly 600 characters. The same cut survives one layer upstream, on the
producer side, where it is not reversible. A `check_caches` detail naming every empty host
directory, or a `check_state` breakdown naming every source, is exactly the kind of value that
runs past 300 characters.

Filed: `HEALTH_PREFLIGHT_STAMP_TRUNCATES_ROWS`, MINOR, RUN.

### m11. `health.py:85, 456, 481, 638, 858` — the evidence bag and the failure detail are cut with no marker

* `:85` `"sample": str(sample)[:240]` — the persisted sample, in the ring `record()`'s own
  docstring calls "the evidence bag".
* `:456, :481, :638` `str(e)[:60]` and `:858` `str(e)[:60]` — the exception text of a check that
  failed. Sixty characters does not survive a `JSONDecodeError` message, a Windows
  `PermissionError` path, or a URL. These are the strings an operator diagnoses from, and they
  then pass through m10's second cut on the way to the queue.

Filed: `HEALTH_UNMARKED_DIAGNOSTIC_TRUNCATIONS`, MINOR, RUN.

### m12. `health.py:908` — `--preflight` is declared and never read

`ap.add_argument("--preflight", ...)` is parsed; `a.preflight` appears nowhere in the file
(verified by grep over all 930 lines). `main()` branches on `a.reopen` and `a.failures` and
otherwise falls through to `preflight()`, so the flag works only by coincidence of being the
default. It matters more than a tidy-up because `allsweep.py:162` invokes the verifier as
`["health.py", "--preflight"]` and `overnight.py:928` does the same — two standing callers whose
contract with this module is a flag the module does not actually consult. Any future branch
added ahead of the fall-through silently changes what those two run. Remedy: branch on it
explicitly (`if a.preflight or not (a.reopen or a.failures)`).

Filed: `HEALTH_PREFLIGHT_FLAG_NEVER_READ`, MINOR, RUN.

### m13. `health.py:525-528` — the quarantine read fails silently, unlike the exclusion read ten lines below it

```python
except Exception:
    # FAIL LOUD, NOT QUIET. ...
    quarantined = set()
```

The comment says FAIL LOUD; the handler is loud only in the sense that nothing is excused. It
records nothing — no `silence.note`, no print. The structurally identical handler for
`excluded_dirs` at :570-573 does exactly that (`silence.note("health.py:excluded-hosts-unreadable")`).
So `binding_health.quarantined()` breaking is invisible: the preflight simply starts reporting
quarantined hosts as fresh faults again, which is the condition run #33 removed and which
:504-509 says "is how a preflight stops being read". One `silence.note` closes it.

Filed: `HEALTH_QUARANTINE_READ_FAILS_WITHOUT_A_NOTE`, MINOR, RUN.

### m14. `identity.py:230-234` — the branching majority rule is unreachable; the branch collapses to a fixed test

```python
if n >= MIN_BEARERS:          # MIN_BEARERS = 3
    return True
if n == 1:
    return shared >= 1
return n >= 2 and shared >= max(2, 0.5 * n)
```

`n >= 3` returns above; `n == 1` returns above; `n == 0` cannot occur (`bearers[desig]` is built
by adding to a set, so every key has at least one member). The final line is therefore only ever
evaluated at `n == 2`, where `max(2, 0.5 * 2) == max(2, 1.0) == 2` — so it is exactly
`shared >= 2`, i.e. BOTH bearers must be shared. The `n >= 2` guard is always true there, and
the `0.5 * n` majority term the docstring advertises ("a designator most of whose bearers ALSO
exist under another designator") is dead arithmetic that can never be the binding value.

This is not currently wrong — requiring both of two is a defensible reading of "most" — but the
code presents a general majority rule and implements a constant, and it would silently start
behaving differently the day `MIN_BEARERS` is raised (at 4, `n == 3` would newly land here and
`max(2, 1.5)` would still be 2, i.e. a 2/3 minority would admit). Remedy: state the rule
actually intended for the reachable case, or make `MIN_BEARERS` and this line derive from one
another so raising the constant cannot quietly change the classifier.

Filed: `IDENTITY_BRANCHING_MAJORITY_RULE_UNREACHABLE`, MINOR, LOCAL.

### m15. `identity.py:565, 578` — two unmarked cuts on the epoch probe

* `:565` `_ask(sentence.strip()[:1200])` — the sentence handed to the probe is cut at 1,200
  characters with no marker. A sentence whose only temporal marker sits past that point is
  reported as carrying none, which `epoch_of`'s own docstring at :537-549 is emphatic must never
  be conflated with "nothing asked". The 1,200 cut produces a third case neither branch names:
  *asked, about a different sentence than the one on the page*.
* `:578` `str(d.get("epoch") or "").strip()[:60]` — the stored epoch, which becomes part of a
  comparison-graph key via `identity.node(base, continuity, epoch)` (`chain.py:631`). Two
  distinct epochs sharing a 60-character prefix would fold into one node.

Both are low-probability given the prompt's "six words at most" (:491) — filed at MINOR, not
higher — but a value that keys a graph node should be refused when overlong, not cut.

Filed: `IDENTITY_EPOCH_PROBE_UNMARKED_CUTS`, MINOR, LOCAL.

### m16. `ingest_doc.py:306-308` — the NEW-MATERIAL path raises a bare traceback for a source that has no record yet

`record_path()` (:195-218) returns the non-existent natural path `p` when nothing matches, which
is correct as a contract. `mine()` then does `with open(rp, encoding="utf-8")` at :307 with no
guard, and `main()` catches only `ValueError` (:525). So a source with no `data/records/<slug>.json`
exits by `FileNotFoundError` traceback.

That is precisely the case this module is built for — `record_path`'s own docstring at :180-181
says "this module is the NEW-MATERIAL path -- the one place a source routinely arrives before it
has a record" — and it is the one arrival mode the module does not answer in a sentence. The
sibling read directly above it (:256-259, the missing corpus) was converted to exactly such a
sentence in order `0c007141d39f` for the identical reason, and this read was not visited.

Remedy: raise the same `ValueError` naming the expected path and the slug, so `main()`'s
existing "MINE REFUSED: ..." / `return 1` path reports it.

Filed: `INGEST_MINE_TRACEBACKS_ON_A_MISSING_RECORD`, MINOR, LOCAL.

### m17. `ingest_doc.py:445-452` — a cumulative counter reported as "this run"

`state["found"]` is loaded from `ingest_state.json` at :263-268 and therefore carries every
previous run's total. Two lines describe it as this run's work:

* `:446` `"COUNTER BEHIND DISK: %d entries merged this run"` — `state["found"]`, cumulative.
* `:452` `"ingest complete: %d new entries merged"` — same value, printed at the end of every
  completed resume.

The GAP that message is about (`state["found"] - landed_found`) is computed correctly, because
`landed_found` is seeded from the same cumulative base at :325. Only the labels are wrong, and
they are wrong in the flattering direction: a resumed run that merged 3 entries reports the
book's lifetime total. Remedy: keep a separate `this_run` counter, or subtract the value read
from disk at entry.

Filed: `INGEST_CUMULATIVE_COUNTER_LABELLED_THIS_RUN`, MINOR, LOCAL.

### m18. `sevenfold.py:409-410` — stale citation into `zfighters.py`

The comment cites `zfighters.py:492-497` as "the identical situation ... answers with a 1".
Verified: `zfighters.py:488-500` is the `--full` axis-printing loop and its `provenance` note;
the write-denied → `return 1` it means is at **`zfighters.py:520-529`**. The argument holds, the
evidence offered for it does not — the same shape `identity.py:581-588` records for its own
`chain.py:381` citation.

Filed: `SEVENFOLD_STALE_ZFIGHTERS_CITATION`, MINOR, LOCAL.

### m19. `sevenfold.py:386, 389-394` — unmarked display truncations and two unflagged `[:8]` heads

* `:386` `a[:24]` / `b[:24]`, `:390` `s[:34]`, `:394` `d[:42]` — names cut mid-value with no
  marker. World designations are `source::world` strings and routinely exceed 42.
* `:389` `for s in sorted(coords)[:8]` and `:393` `for d in sorted(worlds)[:8]` — headed
  "sample shelfmarks", which is honest, but neither line says how many were not shown. The
  totals ARE printed above (`sources shelved`, `worlds shelved`), so this is the mildest form;
  `entity_match.candidates` and `catalog.cmd_stats` are the house standard here and both either
  flag the truncation or print everything.

Filed: `SEVENFOLD_SAMPLE_LISTINGS_AND_NAME_CUTS_UNMARKED`, MINOR, LOCAL.

### m20. `catalog.py:34-39, 112-135` — a missing catalogue reads as an empty one, and nothing sets an exit code

```python
def load_catalog(cfg):
    path = os.path.join(HERE, cfg["paths"]["catalog"])
    if not os.path.exists(path):
        return {}
```

`cmd_stats` then prints "Sources with at least one generated chapter: 0 / Total
chapters/frontmatter pages generated: 0" — byte-identical to a catalogue that exists and is
empty. CLAUDE.md's "When you're done with a batch" section tells the operator to report coverage
from this command, so the one output a person is instructed to trust cannot distinguish "nothing
generated yet" from "the catalog file is not where config says it is".

Separately, `main()` (:112-135) has no `return` and `__main__` calls `main()` without
`sys.exit`, so **every path exits 0** — including `cmd_address`/`cmd_read` printing "No entry
for address: X". Every other CLI in this batch ends `sys.exit(main())` and returns a non-zero
code on a refusal (`read.py:1383`, `health.py:926`, `identity.py:699`, `ingest_doc.py:541`,
`sevenfold.py:415`).

Filed: `CATALOG_ABSENT_INDEX_READS_AS_EMPTY_AND_RC_ALWAYS_0`, MINOR, LOCAL.

### m21. `liveness.py:187` — a citation into `entity_match.py` that points at nothing (cross-module, found from this batch's side)

```
Nested classes recurse, and the label carries the dotted path so a report line names the
class -- `entity_match.py:88 Resolver.rebuild()` is answerable, `rebuild()` is not.
```

Verified from the `entity_match.py` side: there is **no class `Resolver`** anywhere in `src/`
(grep: the only occurrence of the string is this comment), `entity_match.py` defines exactly one
class, `MatchReason` at :75, which has no methods, and `entity_match.py:88` is the `_QUAL`
comment. The paragraph two sentences earlier names `entity_match.py` as one of the twelve
class-defining modules the pass was extended to cover, so the example reads as a real report
line from this file and is not one. Remedy: use a real label (`entity_match.py:75
MatchReason.<x>` has no methods, so pick a module that has one) or mark the example as
hypothetical.

Filed: `LIVENESS_PHANTOM_ENTITY_MATCH_CITATION`, MINOR, RUN.

---

## INFO / noted, not filed as defects

* **`sevenfold.py:374`** `ok = "OK" if hi <= SPAN else "OVER SPAN"` genuinely cannot print
  "OVER SPAN": `seams()` clamps `k` to `min(span, len(block))` and every tier coordinate is an
  index in `range(span)`, so `len(parents[key])` is bounded by 7 by construction, including for
  the world tiers where two sources sharing an address union their children. The comment at
  :370-373 already says exactly this and says why it is kept. Correct as annotated; no order.
* **`sevenfold.py:283`** `srcs, w, shared = TI._graph()` — `shared` is never used. One-line dead
  binding; rolled into the m19 order rather than filed separately.
* **`read.py:594-605`** `cache_path()` has no callers (verified: the only other `cache_path` in
  `src/` is `sweep.py:72`, a separate function). The docstring says so and explains why it is
  kept as a delegating shim rather than deleted. Correct as annotated.
* **`entity_match.py`** has no production consumer — `verify_math.py:2447-2496` (§19r) exercises
  it and `tempus.py:94` / `liveness.py:176` only mention it. The module header states this and
  calls itself a seam. `embed_available()` likewise. Correct as annotated; no order.
* **`scale_theories.py`** — dead module, four dead functions, and five module-level constants
  (`C_LIGHT`, `G_NEWTON`, `HBAR`, `NUCLEAR_DENSITY`, `PLANCK_LENGTH`) that nothing in the file
  reads. Re-verified; **already filed** as open order `SWEEP34_FINDING`. Not duplicated.
* **`src/deprecated/catalogue_local.py`** — everything from :96 down is unreachable behind the
  module-level `raise SystemExit(_REFUSAL)` at :94, which is the point of the file. The six
  defects the quarantine block enumerates (:50-65) were re-checked and are all still present and
  still unreachable, including `slug()`'s `[:60]` at :198 and the `per_cat[key] = 0` at :230
  that files a network failure as "nothing in this category". Deliberately unrepaired; no order.
  Two open orders about this file carry citations that have drifted — see the next item.
* **Stale `where` fields on two OPEN orders**, noticed while checking for duplicates:
  - `deprecated-catalogue-local-writes-canonical-records-bare` cites
    `src/deprecated/catalogue_local.py:263,268` for the two bare `open(..., "w")` writes; they
    are now at **:316 and :321** (263/268 are `argparse` setup).
  - `ANNOUNCED_CONSOLE_TRUNCATION_SCOPE_OF_HARD_RULE_0` cites `src/catalog.py missing[:30]`; that
    slice no longer exists — order `6434c1ba7b20` removed it and `catalog.py:76-78` now prints
    every missing source. Half of that owner question is therefore already settled.
    Filed: `STALE_CITATIONS_ON_TWO_OPEN_ORDERS`, INFO, RUN.

---

## QUESTIONS (two defensible readings — not filed as findings)

* **`read.py:1188-1189`** `if limit: todo = todo[:limit]`. This is a truncation of the ordered
  queue, and `--chunks` was made INERT under Hard Rule 0 for being one. The two are not the
  same, though: a `cap_chunks` slice wrote a PARTIAL entity to the permanent cache as a finished
  record, whereas `--limit` reads fewer entities and each one it does read is complete and
  correctly cached; nothing marks the corpus finished. Reading it as a legitimate operator dial
  is at least as defensible as reading it as a cap. Left for the owner alongside the standing
  `ANNOUNCED_CONSOLE_TRUNCATION_SCOPE_OF_HARD_RULE_0` question.
* **`health.py:483-494`** `check_api_paths` buckets every non-Wikipedia host into one "fandom"
  family and probes whichever `dict.values()` order reaches `setdefault` first. Hosts that are
  neither (`www.dandwiki.com`, `minecraft.wiki`, and others) are represented by a member that
  may not share their API layout, so a real outage on them cannot be detected here. The
  docstring is explicit that this is deliberately "one live call per host FAMILY" for cost, and
  `binding_health` holds per-host faults, so this may be exactly the intended division of labour
  rather than a gap. Not filed.
* **`health.py:578-581`** `if len(files) < 25: continue` — a host directory with fewer than 25
  cached entries is never tested for the all-empty 404 signature, and its exclusion is not
  reported. Defensible as a statistical floor (the check's premise is "an ENTIRE host directory
  of empty entries"), and a small directory is cheap to eyeball. Not filed.

---

## PROCESS INCIDENT — this batch stamped coverage on seven modules it never opened, and corrected it

Recorded here because it happened DURING this audit and the shard is on disk.

The run39 instruction is to derive the module list from `sweep_plan.batches(16)[11]['modules']`
at the start and to record coverage at the end. `batches()` is **not stable across a run**:
`modules()` (`sweep_plan.py:69-99`) reads the LIVE line count of every file under `src/` and
`batches()` (`:102-115`) greedy-packs longest-first, so any edit anywhere in `src/` — and a
maintenance shift was editing eight files throughout this window — reshuffles the bins.

* Start of batch 12, `batches(16)[11]['modules']`:
  `read.py, health.py, identity.py, ingest_doc.py, sevenfold.py, deprecated/catalogue_local.py,
  entity_match.py, scale_theories.py, catalog.py` — the nine read in full for this audit.
* End of batch 12, the identical call:
  `workorders.py, health.py, scout.py, weave.py, address.py, grounding.py, scope.py,
  cosmology_graph.py` — **one** module in common out of nine.
* The nine actually read are now spread across **five** bins: 10, 12, 13, 13, 13, 14, 14, 15, 15.

Following the instruction literally wrote `state/sweep_shards/run39.12.44108.json` claiming
coverage of seven modules this batch never opened, while leaving eight of the nine it did read
unstamped. Caught within one command (the printed list did not match the audit already written),
the shard was deleted and the true nine re-recorded from a fresh process
(`run39.12.46252.json`). `missing('run39')` went 54 → 52 across the correction. No `src/` file
was touched.

Batch 15 hit the same defect independently in the same hour and had already filed
`SWEEP_BATCHES_UNSTABLE_UNDER_LIVE_EDITS` (MAJOR, SESSION, id `44c420f80448`). Rather than open a
near-duplicate, that order was **refreshed** with this second sighting appended — batch 15's text
and evidence preserved verbatim, `seen` now 2.

That order asks for every run39 shard to be checked against what its audit actually discusses.
Done at 23:07: for each of the eight run39 shards then on disk (batches 3, 4, 5, 7, 8, 12, 14,
15), every module named in the shard appears in that batch's `AUDIT_batch<NN>.md`. No further
false stamps among those eight. **This is a floor, not a clearance:** it is a name-in-text test,
and all sixteen audit files existed at 23:07 while only eight shards did — the other eight
batches must be re-checked the same way once they record.
