# sweep45 — batch 07

**Scope:** `src/feats.py`, `src/corpus_db.py`, `src/estate.py`, `src/address_space.py`,
`src/sevenfold.py`, `src/genre.py`, `src/catalogue_models.py`, `src/cachekey.py`, `src/catalog.py`
— 5,449 lines.

**Read:** all of it, every line of all nine modules, no sampling. Read-and-report only; no source
file was edited. The standing DRILL_BREACH halt was respected — no battery tool was run.

---

## Filed this batch

### 5be28f56946c — `FEATS_THROTTLE_HANDOFF_BRAKES_NOTHING` (OWNER, MAJOR)

`feats.note_throttled` at `THROTTLE_STRIKES=3` calls `binding_health.quarantine(host, ...)` under
a comment that reads *"HAND OFF RATHER THAN HAMMER … continuing to spend requests on it costs the
whole pool's politeness budget."* **The crawl never asks whether a host is quarantined.**

Verified across all 116 modules including `src/deprecated/`: the only `is_quarantined` call outside
`binding_health.py`, `drill.py` (stubbed self-tests), `health.py` (reporting), `dashboard.py:645`
(display) and `workorders.py` (files orders about it) is `feats.py:168` — and that one guards only
against quarantining the same host **twice**. Nothing in `api()`, `_throttle()`, `fetch()`,
`discover()`, `evidence_for()`, `roll()` or `endpoint.py` consults it. `quarantine()` writes
`HOST_QUARANTINE.json` and escalates at SUPERVISOR; it has no other effect on a running roll.

This is the mechanism missing from open order **959b98f38a63**, which measured the symptom
(`marvel.fandom.com` throttled **75 times consecutively** at 32x backoff). A counter cannot reach 75
if the handoff at 3 brakes anything. That order is about the concurrency *setting* and does not name
this.

Two remedies of different sizes, and the order says not to apply the cheap one alone:
1. *(local)* amend the comment to say the handoff is a **record**, not a brake;
2. *(owner)* have the fetch path defer a quarantined host — **defer, not drop**: dropping is a
   smaller universe and runs into Hard Rule 0.

### ef4ca9edd61f — `FEATS_EMPTY_EVIDENCE_CACHED_WITH_NO_REASON` (OWNER, MAJOR)

`evidence_for` writes its per-entity record **unconditionally** (`feats.py:1585-1602`). When `api()`
returns a bare `None` for a fetch batch — a 429 that exhausted retries, a non-JSON 200 from a WAF, a
network fault — `fetch()` returns `{}` and the record lands as `pages_read=[]`, `chars_read=0`,
`feats=[]`, `text={}`, `pages_refused={}`: byte-identical to a genuinely page-less entity, because
`pages_refused` only ever holds pages that **arrived** and failed `page_looks_real`.

And it is a **permanent** cache hit. On the next roll `cachekey.load` returns it, `owns()` passes,
and neither staleness predicate can reject it — `mined_under_superseded_gate` returns `False` for any
`reads_as_wiki` host, `mined_without_name_matching` is scoped to `pages:` hosts. So on every wiki
host a throttled fetch is cached as an honest absence for ever. That is this module's own stated
signature failure ("1,364 swallowed HTTPErrors … every pantheon and astrology source read as *no
wiki holds this fiction*") reproduced one layer down, at rest.

**Measured over all 275,029 files in `data/feats`, nothing sampled:**

| | files | share |
|---|---:|---:|
| `pages_read == []` **and** `pages_refused == {}` | **34,676** | 12.6% of the cache |
| — of which `marvel.fandom.com` | 13,490 of 52,733 | **25.6%** |
| — compare `dc.fandom.com` | 4,802 of 55,565 | 8.6% |
| — `en.wikipedia.org` | 2,964 of 6,392 | 46.4% |
| hosts with at least one | 79 | |

Marvel — the host measured at 75 consecutive throttles — sits at three times the rate of a
comparable corpus on the same wiki farm. That is *consistent with* throttling being written to disk
as absence. It cannot be turned into proof, **because the record does not say**. That is the finding.

Not covered by the open neighbours: `6d594a775899` is the opposite direction (refused pages counted
*inside* `pages_read`, which incidentally confirms that an empty `pages_read` means nothing arrived
at all); `b9584c782d95` is about hostless sources in `roll()`'s summary; `33000660ddac` is the exit
code.

Remedy in two halves: `api()` **already computes** the missing fact (the `outcome` channel added for
order `64e4db060ad6` — ok / no-api / http-404 / throttled / http-N / nonjson / network) and throws it
away at the return. Thread it through `fetch()` into `mined_under` and treat a non-404 empty as a
MISS. The 34,676 records already on disk carry no stamp and can only be cleared by re-mining, which
is network spend against hosts already throttling us — hence OWNER.

### 3b9812ae8ab7 — `FEATS_QUANTITY_MACH_IS_UNIT_FIRST_IN_THE_CORPUS` (OWNER, MINOR)

The coordinator asked for *other* patterns with the shape of the known `power level` one. There is
exactly one: **`mach`**. `_QUANTITY` is anchored on a leading figure, so it can only match
`<N> mach` — but English writes the Mach number unit-first.

Measured across the whole feats cache, nothing sampled: **210** occurrences of `Mach <digit>` against
**33** of `<N> mach`. **86% of the Mach evidence in the corpus is unreachable by this pattern**, for
the identical structural reason as power level, and the in-source note at `feats.py:1187-1199` is
silent about it. Volume is far smaller than power level's and should be weighed as such.

Every other alternative was checked and is clear: tons/tonnes/kilotons/megatons/gigatons, joules,
watts, newtons, metres/kilometres, miles, light-years, parsecs, `kili`, degrees, kelvin, celsius and
"times the speed of light" are all written number-first in this corpus; "degrees Celsius" is reached
via the `degrees` alternative.

### f231ee4e5424 — `ESTATE_ARTIFACTS_ROOTS_DO_NOT_COVER_THE_TREE` (LOCAL, MINOR)

`artifacts()` docstring: *"Every file in the project, opened and checked. No sampling anywhere."*
Measured against the live tree with estate's own `SKIP_DIRS` applied: it reaches **296,560** files and
**60 are never opened or even sized** — `backup/` (29), `.ruff_cache/` (20), `site/` (2), `.claude/`
(1), `.gitignore` (1), and the seven root ledgers **BUGS.md, FOR_OWNER.md, HANDOFF.md,
MAINTENANCE.md, NEXT_STEPS.md, STEP4_PLAN.md, WATCH.md**. `docs/` is empty today and equally unlisted.

This is the same defect the module header already records repairing once (`estate.py:23-31`, order
`19fc2fdda102`) — that repair was to the **extension** list; the **roots** list was not visited. The
seven `.md` files are the ones that matter: they are the documents an operator reads, and a zero-byte
or non-UTF-8 `HANDOFF.md` would be reported by nothing. Preferred fix is to add the roots and glob the
root's `*.md` rather than naming five files — a hand-enumerated list going stale is exactly what
`_effective_ext` (`:127-148`) refuses to commit, in this same file.

### 8e5b951c1e2f — `CORPUS_DB_WORST_CITED_SORTS_UNMEASURED_FIRST` (LOCAL, MINOR)

`CANNED["worst_cited"]` orders by `ROUND(100.0*cited/entries,1) ASC`. A source with no
`COVERAGE.json` row is inserted with `cited` NULL (`rebuild()` `:204`, `:238-240`), `pct` is NULL, and
**SQLite orders NULL first on ASC** — demonstrated on a three-row stand-in, where `cited=NULL` sorts
ahead of 1.0 and 99.0. "Nobody asked" is then rendered in the same column and the same position as
"asked and found almost nothing", on the one canned query the file itself calls a WORK LIST (`:679`).

**Latent today and said plainly:** 6 of 216 sources have no coverage row (HAWX, Heaven's Lost
Property, Lost Mines of Phandelver, Twilight Imperium, major live-action Disney films, the Witch
Tradition) and all six hold **0 entries**, so the `entries>=40` filter excludes them; the live head is
8 genuine 0.0% rows. It becomes live the first time a 40+-entry source is catalogued before
`coverage.measure()` reaches it — the ordinary sequence, since the record and COVERAGE.json are
written by different passes. One clause fixes it (`AND cited IS NOT NULL`, or `NULLS LAST`). Note the
same file already did exactly this for the other NULL-bearing column: `SPINE_LOOKUP_FAILED` exists so
a failed lookup stops being swept up by `WHERE spine IS NULL`.

---

## Corroborated, not refiled

| open order | what this batch confirms |
|---|---|
| `959b98f38a63` | backoff state is genuinely in-memory (`_BACKOFF`/`_STRIKE`/`_HOST_LAST` are plain module dicts; nothing reads or persists them across processes). See the coordinator note below. |
| `6d594a775899` | `out["pages_read"] = sorted(pages)` does include titles that failed `page_looks_real` — confirmed at `feats.py:1563` against the `unreal`/`continue` at `:1548-1551`. |
| `b9584c782d95` | `roll()`'s `h = hosts.get(...); if not h: continue` is still the one loss category the summary never names. |
| `f27d210d4fea`, `4f308dbd9d2c`, `665e3609bc82`, `0b1cda11f4a2` | `alive()`, `_page_exists()`, `resolve_title()`, `axis_evidence()`, `remine()` all still have zero callers. `evidence_for` still passes the raw catalogue name to `discover()`. |
| `be9e9f089d62` | `shelfmark()` still prints seven of the eight fields and omits `star`, so it is not injective over addresses. |
| `1e9a348ea2ca` | `sevenfold.main()`'s `a[:24]`/`s[:34]`/`d[:42]` cuts and the two unflagged `[:8]` heads are unchanged. |
| `3f4d2d058fdc` | `catalog.main()` still returns `None` on every path, so `cmd_address`/`cmd_read` exit 0 on "No entry for address". |
| `189532cbf41a`, `3dd5b6caef38` | `charter()`'s `un[:4]` is unchanged. **Two more instances of the same question** found this batch, folded in here rather than filed as a third and fourth: `genre.py:300` cuts a source name to `s[:30]` in the low-confidence **work list** (the list whose whole job is "do not trust this classification") and `genre.py:310` to `s[:26]`. One owner ruling on display truncation settles all four. |

## Considered and deliberately not filed

- **`feats.discover(extra=...)` and `genre.classify_source(cap=...)` raising `SystemExit`.** Both are
  guards no production caller can trip. Both are the documented "refuse loudly rather than honour
  silently" pattern with the parameter kept for signature compatibility — deliberate, and the
  docstrings say so.
- **`sevenfold.main()`'s `"OVER SPAN"` column.** Cannot print, and the comment at `:370-373` says so
  in terms ("This displays a GUARANTEE, not a discovery … it becomes a real check only if `seams()`
  ever stops clamping"). Honest as written.
- **`address_space.HASH_BYTES > 32`** raise. Cannot fire today; it is a real bound that fires if the
  census grows, and it fails loud rather than silently reading zero. Correct as written.
- **`corpus_db.rebuild()`'s `if not isinstance(e, dict): continue`** at `:244-245` is a silent,
  uncounted drop that would put `n_entry` below `drift()`'s `real`. Measured across all 216 record
  files: **282,822 entries, 0 non-dict**. Latent with no live instance; not worth an order today.
- **`feats._units` takes the global `_COUNTS_LOCK` once per text unit**, twice per sentence across
  `mine()` and `by_axis()`, on every page of an 874MB corpus with 12 workers. Structurally a
  serialization point, but the roll is network-bound at ≥0.34s per host request, so this is very
  unlikely to be the throughput constraint. Recorded here rather than filed as a speculative
  performance order.
- **`estate.inspect()`'s control-character branch (`:283-287`)** sets `rec["error"]` without a
  `silence.note`, unlike every sibling branch. Cosmetic inconsistency in the ledger tags only.

## On the coordinator's two standing questions

**Does anything depend on the backoff surviving a restart?** No — and that is the smaller half of the
problem. `_BACKOFF`, `_STRIKE` and `_HOST_LAST` are module dicts with no persistence and no reader
outside `feats.py`; `backoff_state()` is a reporting accessor with no caller in the crawl. A restart
does silently reset a hard-won 32x back to 1.0 and resume at full rate. **But the persistent thing
that *should* survive a restart — the `binding_health` quarantine — already does, and is never
consulted anyway** (order `5be28f56946c` above). Persisting the backoff would be building a second
brake next to a first one nobody connected; the quarantine consult is the cheaper and more honest
fix, and it survives restarts by construction.

**Is `estate._brief` actually used by its callers?** Yes. Verified at `:213`, `:250`, `:254`, `:257`,
`:264`, `:267`, `:270`, `:277`, `:281`, `:377`, `:397`, `:496`, `:521`, `:543`, `:574`, `:663` — every
`str(e)[:n]` site in the module goes through it, and the marker is appended only when the cut actually
happened. The house form is intact here.
