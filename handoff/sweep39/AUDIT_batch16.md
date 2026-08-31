# run39 — comprehensive source audit, BATCH 16

Modules owned by this batch, taken programmatically from `sweep_plan.batches(16)[15]["modules"]`
and every one read IN FULL (no sampling, Hard Rule 0):

| module | lines |
|---|---|
| `src/binding_health.py` | 1218 |
| `src/local_agent.py` | 1212 |
| `src/catalogue_web.py` | 630 |
| `src/handbuilt.py` | 514 |
| `src/burgs.py` | 401 |
| `src/navtree.py` | 335 |
| `src/recover_folder_records.py` | 283 |
| `src/suppressions.py` | 242 |

Read-only audit. No source file was edited. Every finding below was verified against the file
as it stands today; where two readings are defensible it is filed as a QUESTION and not as a
finding.

---

## binding_health.py

### B1 — MINOR — the exception text is cut at 120 chars and that cut text is STORED

`_fetch_chars` (`binding_health.py:486`), `_probe_reachable` (`:692`) and `_probe_identity`
(`:826`) all build their detail as `"%s: %s" % (type(e).__name__, str(e)[:120])`. None of the
three marks the cut.

That string is not a console line. It is stored:

* `_probe_present`'s error list carries it into `"every probe failed: %s" % errors[0]` (`:583`)
  → `det_p` → `rec["present"]["detail"]` in `data/BINDING_HEALTH.json` (`:892-893`);
* `_probe_reachable`'s goes to `rec["reachable"]["detail"]` (`:895`) **and** through `verdict()`
  (`:857`, `:867`) into `reason`, which `run()` (`:1065`) hands to `quarantine()`, which stores
  it as the quarantine's `reason` in `data/HOST_QUARANTINE.json`;
* `_probe_identity`'s goes to `rec["binding"]["probe"]` (`:903-904`).

This module already ruled on exactly this shape. `quarantine()`'s comment at `:348-355`
(order d6ca84486153) removed `str(reason)[:300]` because it was "a hard slice on a STORED field,
which is Hard Rule 0's exact shape", and measured a fireemblem 429 reason at 330 characters cut
mid-title. The identical cut one level up, on the text that FEEDS that reason, survived.

**Remedy:** store the exception text whole, or route it through the marker-bearing preview
`suppressions._preview` (`suppressions.py:45-56`, order 6160ef68b229) established as house
doctrine — a display cut is accepted only when something says it happened, and a stored cut is
not accepted at all.

### B2 — MINOR — `main()`'s two tables cut without a marker

`binding_health.py:1203` — `r.get("reason", "")[:60]`
`binding_health.py:1210` — `r.get("host", "?")[:34]` and `(r.get("reason") or "")[:60]`

`quarantine()`'s own comment (`:353-355`) authorises these: "the two renderers that print it
... already truncate at their own call sites, which is where the house puts display cuts." That
was true when written. The doctrine settled since (`suppressions._preview`, order 6160ef68b229,
and `suppressions.py:228-235`, order 0a87f4dcd5a7) is narrower: display truncation is accepted
**because it is reversible**, and refused **when nothing says the cut happened**. Neither of
these two says so.

`--quarantined` (`:1203`) is the view an operator reads to decide whether a hold is still
justified; the reason is the only record of WHY the host was closed off, and 60 characters of a
330-character reason is the first clause of it.

**Remedy:** route both through a `_preview`-style helper that appends U+2026.

### B3 — MINOR — `quarantine()`'s landed verdict is discarded by `run()`, while `release()`'s is captured

`binding_health.py:1063-1065`:

```
if rec.get("healthy") is False:
    failed += 1
    quarantine(h, rec.get("reason") or "canary failed")
```

`quarantine()` returns a record whose `landed` key (`:392`) says whether
`HOST_QUARANTINE.json` actually took the write. It is thrown away. The two sibling branches
immediately below do the opposite — `:1070` and `:1077` both capture `release()`'s verdict into
`rec["released"]` through `_report_not_released`, and `_report_not_released`'s docstring
(`:243-266`) is an argument about precisely why a discarded write verdict here is intolerable.

Consequences, both verified by reading:

* the report row for a failed host carries no `quarantined` field at all, while the
  no-title branch at `:1049` does carry one — so a reader cannot tell a host that was held from
  one whose hold was refused;
* `main()`'s summary at `:1211` prints `"%d host(s) checked, %d failed and quarantined"`, and
  `failed` counts hosts whose canary said False, not hosts that were actually quarantined.

This is not a lost alarm — `quarantine()` raises `HOST_QUARANTINE_NOT_RECORDED` itself at
`:400-404`. It is a report and a console line asserting an action that may not have happened,
which is the same fault `_report_not_released` was written for, pointing the other way.

**Remedy:** `rec["quarantined"] = bool((quarantine(...) or {}).get("landed"))`, and take
`main()`'s summary count from that field rather than from `failed`.

### QUESTION B4 — the 8-title candidate bound is reported as a total

`known_present_titles` returns as soon as `len(out) >= want` (`:955-956`, `want` defaults to
`PRESENT_CANDIDATES = 8`) and says nothing about how many catalogued titles exist beyond it.
`_probe_present`'s failure detail then reads `"%d known-present title(s) all returned nothing"`
(`:591-592`), which a reader is invited to read as the whole catalogue.

Two defensible readings and I do not think either is obviously right:

* it is a documented **probe budget** — `_probe_present`'s docstring (`:541-543`) argues for it
  explicitly ("The failure branch IS bounded, at `PRESENT_CANDIDATES` ... the reader can see how
  many were asked"), and the cost of the failure branch is one network call per candidate;
* it is an **unmarked cut on the number a person uses to judge a false quarantine** — the
  distinction between "8 of 8 catalogued titles missed" and "8 of 4,000 missed" is the whole
  question when a live host fails its canary, and `--titles` (`:1176-1178`) is documented as the
  first thing to run at that moment while showing the same bounded 8.

Filed as a QUESTION. If it is to be closed, the cheap half is to have
`known_present_titles` report the count it stopped at alongside the list.

---

## local_agent.py

Checked first, per the brief, that today's maintenance-shift changes are complete rather than
half-landed. They are:

* `t_grep` (`:527-571`) takes a single FILE as well as a directory: `_safe(subtree)` +
  `os.path.exists` (`:540-541`), `os.path.isfile` branch at `:559-563` with the extension filter
  deliberately skipped, and the error message names both forms.
* `_achievement` (`:989-1036`) takes `answer=None`, and `run()` really does act on it —
  `got = _achievement(patches, apply, answer=answer)` at `:1095` and the
  `elif got["produced_nothing"]: out["ok"] = False` branch at `:1101-1105`. The turn-budget exit
  at `:1162` calls `_achievement` without `answer` on purpose; that path is already `ok=False`
  (`:1160`), so nothing is lost.
* `DENYLIST` (`:64-90`) and `foreman.DENYLIST` (`foreman.py:117-118`) agree on all five
  detectors (`drill`, `escalation`, `codewatch`, `liveness`, `overnight`), which is what the
  comment at `:87-89` claims they may not differ on. Verified.

### L1 — MINOR — a fully-gated patch is reverted, and misreported, when the model sends `"why": null`

`local_agent.py:830`:

```
return _settle({"applied": True, "why": why[:200]})
```

`t_propose_patch`'s signature is `why=""` (`:695`), but `run()` dispatches with
`t_propose_patch(apply=apply, log=patches, **args)` (`:1132`) where `args` is a dict decoded
from the model's own JSON — so `{"why": null}` binds `why=None`, overriding the default. Every
other use of `why` in the function is guarded: `:707` is `(why or "")[:200]`. `:830` is not.

The failure lands **inside** the `try` opened at `:822`, so the `except Exception` at `:831`
fires after the file has already been written (`:823-824`) and has passed `_gates` (`:825-826`).
The handler reverts the file and returns
`{"applied": False, "reverted": True, "error": "TypeError: 'NoneType' object is not subscriptable"}`.

So a patch that parsed, linted, imported and left `verify_math` at 0 FAILED is discarded, and
the reported cause is a `TypeError` that names nothing the model could act on — an
argument-shape fault wearing the message of an apply/revert fault. It fails in the safe
direction (nothing is left on disk) and reports the wrong thing.

`find=None` and `replace=None` are NOT affected: `original.count(find)` at `:791` is outside the
try and raises up to `run()`'s `except TypeError` at `:1139-1140`, which answers the model with
a readable error before anything is written. `why` is the one that gets past that.

**Remedy:** `(why or "")[:200]` at `:830`, matching `:707`.

### L2 — INFO — the pyflakes gate is the one subprocess in `_gates` with no encoding contract

`local_agent.py:596-597`:

```
r = subprocess.run([PY, "-m", "pyflakes", full], capture_output=True, text=True,
                   timeout=120, creationflags=_NO_WIN)
```

No `encoding=`, no `errors=`, no `env=dict(os.environ, PYTHONIOENCODING="utf-8")`, no
`cwd=HERE`. The two other subprocess calls in the same function both set the env
(`:664-667`, `:674-677`), and `t_run_check` sets `encoding="utf-8", errors="replace"`
(`:357-359`).

`text=True` without an explicit encoding decodes with the platform default (cp1252 here) and
`errors="strict"`, so a non-decodable byte raises `UnicodeDecodeError` out of the lint gate.
Because `_gates` is called from inside `t_propose_patch`'s try (`:825`), the effect is again a
revert reported as an apply error rather than as "the lint gate could not run" — which is the
exact conflation the returncode/stderr check three lines below (`:605-608`) was added to
prevent, and whose own comment says "A gate that cannot run has not passed."

Low likelihood on today's tree (pyflakes output is normally ASCII paths and messages), which is
the condition under which this file's five documented gate bypasses were also "not currently
exploitable".

**Remedy:** add `encoding="utf-8", errors="replace"` and the `PYTHONIOENCODING` env, matching
its two siblings.

### L3 — MINOR — stale cross-reference into this module, from drill.py

`drill.py:2275` states:

> `_BLAST` is `{"files": set(), "patches": 0}` and `blast_reset` clears both
> (local_agent.py:157-159)

Verified against the current file: `local_agent.py:157-159` is
`# ...borrowed from Strix's per-turn tool-call limiter.` / `#` / `# Generous on purpose ...`,
and `:161` is `MAX_FILES_PER_RUN = 8`. `_BLAST` is at `:163`; `blast_reset` is at `:182-184`.
The citation is off by roughly 25 lines and lands on prose, not on the function it names.

The net's own subject is that it only ever checked one of the two counters, so the citation is
load-bearing for the next reader.

### L4 — INFO — the per-tool-call console line still cuts at 110 with no marker

`local_agent.py:1141-1143` — `json.dumps(args)[:90]` and `json.dumps(res)[:110]`. The ALARM
comment at `:852-859` names this very cut as the reason a failed revert used to be invisible
("the console print in `run()` truncates the result at `json.dumps(res)[:110]`, and the four keys
ahead of it ... push `ALARM` past the cut every time"). The durable channels were fixed and
`main()` now prints the verdict first and unconditionally (`:1192-1199`), so nothing
load-bearing rides this line any more — but the unmarked cut is still there and still silently
decides what a person watching the run sees.

---

## catalogue_web.py

### C1 — MINOR — three stale cross-references, all verified wrong

**(a)** `catalogue_web.py:174`:

> write_json returns the same landed/not-landed verdict replace_retry did, so no call site
> changes -- catalogue_web.py:504 still gates on it.

`:504` is argparse help text (`"largest gap first")`). The gate on `save_roll`'s verdict is at
`:608` (`if not save_roll(roll, [name]):`).

**(b)** `catalogue_web.py:588-590`:

> write_record_catalogue returns whether the rename LANDED ... (pipeline.py:381-396;
> pipeline.py:641 and ingest_doc.py:246 both check it).

`write_record_catalogue` is defined at `pipeline.py:515`. `pipeline.py:381-396` is the
cloud-pool-first helper (`_pool_answering` / `CB.ask`); `pipeline.py:641` is `keys.append(unit)`
in the phase-done helper; `ingest_doc.py:246` is prose inside `mine()`'s missing-corpus comment.
The real gated call sites are `ingest_doc.py:395`, `backfill.py:275`,
`catalogue_aurora.py:261` and `catalogue_codex.py:329`.

**(c)** `catalogue_web.py:158-160`:

> roll.py:127, resync_roll.py:115, catalogue_aurora.py:271 and catalogue_codex.py:260 all land
> through write_json, whose temp name carries pid and thread.

None of the four is a write site: `roll.py:127` is `digest = silence.digest_of(path)`;
`resync_roll.py:115` is `if not r.get("name"):`; `catalogue_aurora.py:271` is
`written.append((r, record))`; `catalogue_codex.py:260` is `entries.append({`. The substance of
the claim now holds only indirectly — those modules land the roll through `roll.update_rows` /
`roll.mutate` (`roll.py:253`, `catalogue_codex.py:361`, `resync_roll.py:210`), which use
`write_json` internally. `catalogue_codex.py` contains no `write_json` call of its own at all.

### C2 — MINOR — `catalogue_composite` still hardcodes the entity type, the defect order 6eb20e8d3565 repaired next door

`catalogue_web.py:239-247` writes, for every entry from every sub-wiki and every category:

```
"type": "Deity",
"category": "Persons (named individual characters, real or fictional)",
```

The single-wiki path was repaired for exactly this. `catalogue()` now builds `first_cat`
(`:366`, `:370`) so each entry records the category the title actually came from
(`:453`, `_singular(first_cat.get(title) or ...)`), and the comment at `:355-365` states the
measured damage of the old behaviour: 3,521 Media entries typed 'Ability', 1,696 Vessels &
Things typed 'Character', 690 Events typed 'Total War: Warhammer'. It also states why `type` is
not cosmetic — `corpus_db.py` indexes it and `manifest_builder.py` puts the entry dict into the
prose prompt, so a wrong type reaches finished prose.

`catalogue_composite` never got that fix. The composite loop has the category in hand at `:217`
(`for c in cats:`) and discards it.

Today's only composite source is `"major fantasy pantheons"` (`wiki_source.py:72-92`), whose
categories are all deity-shaped, so "Deity" is not currently a WRONG value — but the
distinction between `Archons`, `Aedra`, `Daedra`, `Divines`, `Goddesses` and `Gods` is thrown
away, and the next `COMPOSITE_SOURCES` entry that is not a pantheon inherits a silent mislabel
with no gate anywhere that would notice.

**Remedy:** build the same `first_cat` map in `catalogue_composite` and run it through
`_singular()`, exactly as `catalogue()` does.

### C3 — MINOR — the empty-composite return conflates transport failure with genuine absence

`catalogue_web.py:251-252`:

```
if not entries:
    return None, "composite produced no entries"
```

`failed_cats` and `no_text` are both in scope and both discarded on this path. `_one` then
prints `-> SKIPPED {name} (composite produced no entries)` (`:581`), which reads identically for
"every sub-wiki's transport failed" and "the categories are genuinely empty" — two conditions
with opposite remedies.

The function goes to real trouble to keep exactly that distinction when it DOES return a record
(`:254-290`, and the provenance text at `:277-290` that says a count is "the UPPER bound on
genuine absence and the upper bound on lost fetches alike"). The all-failed case is the one
where the distinction matters most and is the one where it is dropped.

Practical damage is bounded — `entry_count` stays 0 so the source stays retryable — so the cost
is entirely to the person reading the log.

**Remedy:** build the same `bits` list before the empty check and fold it into the note.

### C4 — INFO — two constants nothing reads

`MAX_PER_CATEGORY` (`:55`) and `CATEGORY_SCAN_DEPTH` (`:60`). Both comments justify their
survival as "kept only as a name other code may import". Grepped across `src/`: the only
occurrences of either name are their own definitions and the comments about them
(`:54-60`, `:377`). No importer exists. `MAX_PER_SOURCE` is read only by its own tripwire (C5).

### C5 — INFO — the Hard Rule 0 tripwire cannot fire, and sits after the expensive work

`catalogue_web.py:400-403`:

```
if MAX_PER_SOURCE is not None:
    raise SystemExit("catalogue_web: MAX_PER_SOURCE was set to ...")
```

`MAX_PER_SOURCE = None` at `:53` and nothing else assigns it, so this branch is unreachable as
the module stands. That is deliberate and worth keeping — it is a tripwire against a future
re-introduction of the cap, and it is the right instinct. Two observations, neither an argument
for removing it:

* it is placed **after** the whole category-discovery and size-ranking pass (`:346-390`), which
  on DC is measured in this same file at hours (`:313-327`) — so a re-introduced cap would be
  refused only after all the network work had been spent;
* nothing in `drill.py` or `verify_math.py` asserts `MAX_PER_SOURCE is None`, so the runtime
  raise is the only enforcement.

**Remedy:** assert it at module import, where it costs nothing and fires immediately.

### C6 — MINOR — the skip reason is cut to 60 characters, unmarked

`catalogue_web.py:578` — `record, note = None, f"error: {type(e).__name__} {str(e)[:60]}"`,
printed at `:581` as the SKIPPED reason. Sixty characters is short enough to lose the whole
actionable part of a wrapped exception, and nothing says it was cut.

---

## handbuilt.py

### H1 — MINOR — three stale cross-references in one comment block

**(a)** `handbuilt.py:457-458`:

> the temp name carried no pid/thread, so two writers of this path collide on the TEMP FILE and
> the loser can replace the target with a partial one (silence.py:425-428 ...)

`silence.py:420-428` is `replace_retry`'s docstring about the Windows denied-rename retry, which
says nothing about temp names. The pid/thread temp name is `silence.py:511`
(`tmp = "%s.%d.%d.tmp" % (path, os.getpid(), _th.get_ident())`).

**(b)** `handbuilt.py:458-460`:

> a denied replace leaked `HANDBUILT_ASSAYS.json.tmp` beside the target permanently, with no
> cleaner anywhere in the tree (silence.py:461-472)

`silence.py:461-472` is the tail of `replace_retry` plus the head of `write_json`'s docstring.
The leaked-temp reasoning ("EVERY denied write leaked one `<path>.<pid>.<tid>.tmp` beside its
target, permanently, with no cleaner anywhere in the tree") is at `silence.py:519-530`.

**(c)** `handbuilt.py:500`:

> catalogue_models.py:215-221 already ruled on the console half of this exact shape -- "the
> persisted copy being complete does not help someone looking at the terminal"

The quoted sentence is at `catalogue_models.py:227-228`. `:215-221` holds a related but
different fix in the same function (the `available_sample` `[:8]` removal, run #26).

Verified ACCURATE in the same block, and worth recording so nobody re-checks them:
`standards.py:1521` really is the `JOB_WATCH + ".tmp"` migration comment;
`retry_synthesis.py:47-49` really is the `path + ".tmp"` paragraph; and handbuilt's own
`(:182-201)` for Zalama's `unestimable` axes is exactly right (`ruin` at `:182` through
`discernment` at `:201`).

No other findings in this file. Checked specifically: every sheet in `ROSTER` carries all
eleven of `assay.WEIGHTS`' axes (verified by running the set difference), so `main()`'s
`rec["axes"][ax]` at `:486` cannot `KeyError`; the write is gated (`:463-466`) and lands before
anything is printed, which the comment at `:444-452` argues for; and the `--full` citation is
wrapped rather than cut (`:495-508`).

---

## burgs.py

### BG1 — MINOR — two stale line citations, one of them in the module header

**(a)** `burgs.py:49` and `:52` both cite `:292`:

> in a file whose own body already said 5,986 at :292 ... The 5,986 at :292 is correct as
> written

`:292` is `# roll, measured at ~2.15 s and 45.6 MB of heap per 130,603-burg world, ...`. The
5,986 figure is at `:301` (`# ... silently overwrote: 5,986 worlds carry 5,939 distinct`).

The irony is on the record: this citation was itself written by order d5a06f9c6dee to repair a
header that disagreed with its own body, and the repair's pointer has since drifted.

**(b)** `burgs.py:335-336`:

> The designation is the world's IDENTITY -- and not even a unique one, see the collision note
> at :291

The collision note ("AND THE KEY IS A LIST, BECAUSE `designation` IS NOT UNIQUE", order
65ae84ee4bd7) begins at `:300`. `:291` is the burg-dict heap measurement.

Verified ACCURATE in the same file: `:294`'s "navtree.py:56 takes the scalar `burg_count` and
nothing else" — `navtree.py:56` is `"b": p1, "nb": BG.burg_count(s, era, cond, p1),`, and
nothing else in `navtree.py` touches `burgs`; and `:88`'s quoted verify_math check
(`check("small settlements route to the village generator", ...)`) exists verbatim at
`verify_math.py:1123`.

### BG2 — MINOR — `--limit` is an override, not a cap, and the sample table never says what it cut

`burgs.py:242`:

```
for k in range(1, (limit or n) + 1):
```

Three separate consequences, all reachable from `main()`'s `--limit` flag (`:278`, passed at
`:347`):

* **`--limit` larger than the world's burg count FABRICATES settlements.** `n` is
  `world_parameters(...)["burgs"]` — the number of burgs the rank-size rule says this world
  has. When `limit > n` the loop runs past it and `rank_population` keeps returning
  `HAMLET_FLOOR`-floored values, so the table prints ranks the world does not have as if it
  did. For a medieval/settled world `p1` lands between 12,000 and 28,000 and `n` between about
  300 and 700, so `--limit 1000` is enough.
* **`--limit 0` means "no limit".** `(0 or n)` evaluates to `n`, so asking for zero burgs prints
  the whole roll — 130,603 rows on the world this file's own comment measures at `:292`.
* **the ordinary case cuts silently.** `--limit 20` prints 20 rows and nothing anywhere in the
  sample block prints `prm["burgs"]` for `w0`, so a reader has no way to know whether 20 is all
  of them or 20 of 130,603. That is the Hard Rule 0 shape: nothing fails, the table is
  well-formed, and it describes a smaller world.

**Remedy:** `min(limit, n)` for a positive integer limit, treat `limit == 0` as zero rows, and
print a trailing "… and N more of this world's M burgs" line when the table was cut.

---

## navtree.py

No findings. Checked specifically, because each is the shape this sweep is looking for:

* `audit()` (`:217-233`) does not collapse to a `want == got` tautology. The `if v["k"]` branch
  compares a node's claimed `n` against a sum over its children's `n`, which are accumulated in
  a different loop (`:107-116`); the `elif` branch compares a claimed count against a
  materialised list; and the missing-child report at `:230-232` is a separate loop, so the
  deliberate `if c in nodes` guard at `:225` (documented at `:222-224`) cannot suppress it.
* the console claim at `:261` ("branches holding sources but no catalogued worlds yet") is
  honest. `empty` selects `v["n"] == 0`, and every node created by the worlds loop has `n`
  incremented on every path prefix (`:109-112`), so an `n == 0` node can only have come from the
  sources loop and therefore has `src >= 1`.
* both hash-order tie-breaks are deterministic and both carry the m41 argument:
  `register_for` at `:175` and the grounding pick at `:187`.
* the three `silence.note` keys (`:74`, `:128`, `:134`) are keyed by symbol and subject, not by
  line, as order 87795c671285 requires — and they name three different files, which is the point.
* the exit code carries every verdict (`:329-330`), including the read-only-run-with-problems
  case the comment at `:314-328` describes.

---

## recover_folder_records.py

### R1 — MINOR — the map's declared counts are unpacked and thrown away

`recover_folder_records.py:140`:

```
for register_source, _declared_count in mapped:
```

`_declared_count` is never read. The header describes `FOLDER_SOURCE_MAP.json` (`:19-22`) as
"the cloud session's OWN mapping from roll source name -> the register `source` strings that
belong to it, **with counts**" — so the file already carries, per mapping, how many register
items the cloud session expected to find, and this transcription never compares it against
`len(by_source.get(register_source, []))` at `:143`.

A mapping declaring 350 items against a register that holds 3 is transcribed silently; the
record lands, the roll row is stamped `status: "catalogued"` with `entry_count: 3`
(`:226-228`), and because work selection everywhere is `entry_count == 0` the source is never
revisited. That is the same "a truncated catalogue is indistinguishable from a complete one"
shape `catalogue_web.py:508-513` documents, arriving through a cross-check the data already
paid for and nobody spends.

This is a free consistency check, not new research: both numbers are already in hand at `:140`.

**Remedy:** compare, and report a shortfall by name the way `skipped_no_items` is reported at
`:265-267` — this file's own order aff81a1f1029 established that these buckets must be NAMED,
not counted, because they prescribe different work.

### R2 — MINOR — stale cross-reference

`recover_folder_records.py:116-118`:

> The comment at line 161 already says the roll is a SNAPSHOT and the record folder is the
> truth

`:161` is blank. The comment it names ("THE ROLL IS A SNAPSHOT; THE RECORD FOLDER IS THE
TRUTH") begins at `:168`.

### R3 — MINOR — the written-records table cuts the source NAME, in the file whose header is about exactly that

`recover_folder_records.py:253`:

```
print(f"  {n:5d}  {name[:48]:50s} -> {fn}")
```

Unmarked, and it is the source name — the row's identity. This file's own header (`:55-63`)
argues at length that cutting a record's identity is the defect that lost a 304-entry record its
path back to the roll, and the example it uses is exactly the kind of name this line cuts:
`Who Framed Roger Rabbit (incl. all content from its associated crossover-toon IPs)` is 79
characters, so what prints is `Who Framed Roger Rabbit (incl. all content from t` with nothing
saying more existed — and the `-> {fn}` column beside it is the un-truncated filename, so the
two halves of the line disagree about what the source is called.

`burgs.py:337-339` quotes the settled house ruling on this exact column shape, from
`suppressions.main()` (`suppressions.py:228-235`, order 0a87f4dcd5a7): "A column that stretches
is a worse-looking table and a truthful one."

**Remedy:** print `{name}` whole, as `suppressions.main()` does for its path column.

---

## suppressions.py

### S1 — INFO — `problems()` re-globs the whole repository per row, and `glob` cannot see dotted names

`suppressions.py:193-194`:

```
hits = [p for p in glob.glob(os.path.join(HERE, "**", "*"), recursive=True)
        if fnmatch.fnmatchcase(os.path.relpath(p, HERE).replace(os.sep, "/"), pat)]
```

Two observations, neither of which bites the three suppressions live today:

* the full-tree glob is rebuilt **inside the loop**, once per wildcard row, and it walks
  `data/records/`, `data/feats/`, `output/` and `.git` each time. `drill.py:2515` calls
  `problems()` every cycle (`net(a, "no suppression is expired or dangling", lambda:
  SUP.problems() == [], ...)`).
* `glob.glob` does not match names beginning with a dot, at any component. A suppression whose
  pattern names a dotted path would be reported DANGLING although the path exists — a false
  fault, in the one function whose job is to distinguish a real fault from a silent pass. The
  failure direction is the safe one (it over-reports), which is why this is INFO and not a
  finding against the detector.

**Remedy:** walk once with `os.walk` before the loop and reuse the listing, and match on that
walk rather than on `glob`, so dotted components are not silently invisible.

Everything else in this module checked clean, and several of them are the shapes this sweep
hunts:

* `_load` (`:59-77`) really does distinguish absent from unreadable, and every caller honours it
  — `add` refuses to write over an unreadable file (`:103-108`), `problems` reports the
  unreadability as a fault in its own right (`:182-185`), and `active`'s discarded `_ok`
  (`:142`) is argued fail-closed in the docstring (`:137-139`) rather than dropped.
* `add` refuses on a denied write (`:125-130`) instead of returning a row that was not recorded.
* `suppressed` uses `fnmatchcase`, not `fnmatch` (`:165`), for the reason given at `:152-160`.
* `_preview` (`:45-56`) marks its cut, which is the doctrine several findings above are measured
  against.
* none of the three public entry points is a safety declared and never called:
  `active` → `drill.py:2512`, `problems` → `drill.py:2515`, `suppressed` → `drill.py:2518` and
  `publish.py:482` (where the result is genuinely consumed at `publish.py:497-506`, not
  discarded).

---

## Summary

21 work orders filed, all under `found_by="sweep39-batch16"`:

| severity | count |
|---|---|
| CRITICAL | 0 |
| MAJOR | 0 |
| MINOR | 15 |
| INFO | 6 (one of them the QUESTION, B4) |

No check that cannot fail was found in the load-bearing sense — the one unreachable guard
(`catalogue_web.py:400`, C5) is a deliberate tripwire and is filed as INFO with a placement
remedy, explicitly not a removal. No declared-but-uncalled safety was found: all three of
`suppressions`' entry points have live callers (`drill.py:2512/2515/2518`, `publish.py:482`,
whose result is genuinely consumed at `publish.py:497-506`), and both halves of
`binding_health`'s quarantine/release pair are reached from `run()`.

The dominant real class in this batch is **stale cross-references** — 5 orders covering 11
individual citations, every one verified line by line against the file it names — and **unmarked
truncation**, 6 orders, of which one (B1) lands on data written to disk rather than printed and
is the same shape this module already repaired one level down under order d6ca84486153. The two
behavioural findings are L1 (a fully-gated patch reverted and misreported when the model sends
`"why": null`) and BG2 (`--limit` fabricating settlements a world does not have).

Nothing was edited. Scratch work was kept out of `handoff/`.
