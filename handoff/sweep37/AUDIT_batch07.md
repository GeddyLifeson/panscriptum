# SWEEP 37 — BATCH 07

Modules read IN FULL, every line (4,001 lines total):

| module | lines | read |
|---|---|---|
| src/feats.py | 1,536 | yes, all |
| src/generate.py | 619 | yes, all |
| src/handbuilt.py | 495 | yes, all |
| src/weave_index.py | 387 | yes, all |
| src/sweep.py | 323 | yes, all |
| src/tempus.py | 274 | yes, all |
| src/descending_ladder.py | 226 | yes, all |
| src/resync_roll.py | 141 | yes, all |

No source file was edited. No program in this batch was run (a live `feats.py --roll`
is in flight at PID 16752); every demonstration below imports the module and exercises
one function with stubs, offline, with no network call and no write into `data/`.
`resolve_hosts` was exercised with `feats.HOSTS` repointed at a temp file.

---

## FINDINGS

### MAJOR

**B07-1 — `feats.resolve_hosts`: a FAILED host probe is cached as a permanent "this source
has no wiki".** `src/feats.py:resolve_hosts` (the `if src in known: continue` at :534, the
`for/else` at :556-562).

`alive(h)` is `bool(api(host, {...}, retries=0))` — ONE attempt, and `api()` swallows every
exception into `silence.note` and returns None. So a throttle, a DNS blip, or this machine's
ephemeral-port exhaustion makes `alive()` answer False. When every candidate slug answers
False the loop's `else` writes `known[src] = None`, and that None is persisted to
`data/WIKI_HOSTS.json`. On every later run the `if src in known: continue` at the top of the
loop sees the key PRESENT and never probes again — a `None` value is still `in` the dict.
`roll()` then drops the source entirely (`h = hosts.get(...); if not h: continue`), so every
entity of that source is silently outside the universe for ever.

Demonstrated offline (stub `alive` returning True for everything, temp hosts file
pre-seeded with `{"Nightmare Comix": None}`):

    cached value for 'Nightmare Comix' : None
    alive() probes attempted this run  : []

Zero probes: the source is never re-asked even though every host is now answering.
`data/WIKI_HOSTS.json` today holds 4 such nulls (JMBrew, Kobold Press, aurora_mods,
the Weaveshaper Ateliers). Those four are plausibly genuine absences — the fault is that
nothing in the code can tell a genuine absence from one failed request, and the file cannot
distinguish them either. This is the file's own signature failure (a refusal wearing the
costume of an absence) with the costume made PERMANENT by the cache.
Confidence: high (mechanism read in source and demonstrated).

**B07-2 — `weave_index.designations()` caches the FAILURE path's empty set against a LIVE
signature; entity identity then silently merges.** `src/weave_index.py:designations`
(:115-121, cache store at :120).

    except Exception:
        silence.note("weave_index-designations-load")
        if cacheable:
            _DESIGNATIONS = (sig, set())
        return set()

`sig` here is the real, current corpus signature. So one transient failure inside
`load_records()` stores `(live_sig, set())` and every later call in that process is served
the empty set until a record file is written. `load_records()` immediately below guards
against exactly this (`if sig is not None and sig == _REC_CACHE["sig"]`); `designations()`
does not. The failure path also loses `_SEED` and the `_EARTH` pattern, so not even the
hardcoded designations survive.

Demonstrated offline (stub `load_records` to raise once, then restore it):

    during the failure : designations() -> 0 designations (seed lost too: False)
    AFTER it recovers  : designations() -> 0   <-- still the cached empty set
    cache key held     : (216, 1787975769.8648784)
    norm('Thor Odinson (Earth-616)') poisoned -> 'thorodinson'
    norm('Thor Odinson (Earth-616)') healthy  -> 'thorodinson@earth616'

The consequence is the one the module's own header calls the expensive direction: with the
designation set empty, `(Earth-616)` reads as a gloss rather than a continuity, and
Earth-616 Thor folds onto Earth-1610 Thor — "merging two entities INVENTS a composite being
that never existed and fuses two universes' evidence into one worksheet". A failed read
recorded as a genuine answer, and then cached. Sibling of the `_api_list_all` error-path fix
made today.
Confidence: high (demonstrated).

**B07-3 — `feats.mine()` / `feats.by_axis()` silently discard every text unit of 400
characters or more.** `src/feats.py:mine` (:979) and `src/feats.py:by_axis` (:1119),
both `if not (20 < len(s) < 400): continue`.

The module docstring promises the opposite of this: "it keeps everything it gathers,
including what the gate turned down, because the previous pass discarded its rejections and
left the rejection rate unauditable." The length filter runs BEFORE the gate, so its drops
reach neither `feats`, nor `gate_rejected`, nor `quantities`, nor any counter, and nothing
in `roll()`'s summary can see them. The 20-character floor is noise control; the 400
ceiling is an upper bound on evidence.

Demonstrated: a 450-character unit containing `5 x 10^44 joules` mines to `feats 0,
rejected 0, quantities 0` and `by_axis` returns no candidate for any axis; the identical
quantity in an 81-character unit yields `{'value': '5e44', 'unit': 'joules', ...}`.

Measured on real mined text (4,000 evidence files sampled at random from the 255,853 on
disk, seed 7):

    units > 20 chars     : 479,804
    units dropped (>=400):     980  (0.20%)
      carrying a physical quantity :   2
      passing valid_scale_note     :   9
      would evidence >=1 axis      : 358

Extrapolated to the whole cache that is roughly 62,700 dropped units, ~22,900 axis
candidates, ~575 gate-passing feats and ~128 quantities — none of them counted anywhere.
Small as a fraction, real as a number, and invisible by construction. The remedy is not
necessarily "raise the number": it is that a unit dropped for length must land in
`gate_rejected` (or its own counter) like every other refusal in this file.
Confidence: high (measured).

**B07-4 — `resync_roll.py` never lets its verdict reach the shell: a denied
`SWEEP_ROLL.json` write exits 0.** `src/resync_roll.py:128-133` and `:140-141`.

The write is properly gated (`landed = silence.write_json(...)`) and the denial is properly
printed — and then `if __name__ == "__main__": main()` discards the return value, and the
denial branch returns a bare `None` anyway. `sys.exit(None)` is 0. Every sibling in this
batch does it the other way and says why: `generate.py:612-619` ("THE EXIT CODE IS THE
NUMBER THE SCHEDULER ACTUALLY LOOKS AT"), `weave_index.py:383-387`, `sweep.py:322-323`,
`feats.py:1535-1536`, `handbuilt.py:494-495`. A supervisor running this after a cataloguing
session is told the roll now agrees with the record files when it does not.
Confidence: high (read in source; two independent defects — no `sys.exit`, and a bare
`return` on the failure branch).

**B07-5 — `weave_index.build()` drops 415 entries from the STORED index, uncounted.**
`src/weave_index.py:283` — `if not key or len(key) < 3 or key in _STOPNAMES: continue`.

This is the same loop the 400-character description cap was just removed from (order
b974e9ed76de), and it is the same shape: a rule written for MATCHING applied to STORED
DATA. Candidates are computed downstream in `main()` from `index`; the filter could live
there and leave the index whole. `weave.py:load_index` reads `ENTITY_INDEX.json` as the
entity population and builds its idf table over it, so an excluded entry is not merely
unmatched, it does not exist to the weave.

Measured over the live corpus (282,822 entries):

    empty key                : 3
    key shorter than 3 chars : 257
    key in _STOPNAMES        : 155
    TOTAL excluded           : 415  (0.15%)

Short-key casualties are real named characters: `'Ed'` and `'X'` and `'Y5'` (Adventure
Time), `'Vi'` (Acquisitions Incorporated), `'IX (Gladiatorial Arena Incident)'` (Black Ops),
`'A.D.A.'` (Creeper World), `'2P'`, `'Ur'`, `'Zu'`, `'Ei'` (Final Fantasy). Stopname
casualties include `'Ghost'` (Star Wars, x2), `'Queen (Acheron)'` and `'The Dragon'`
(Alien), `'Child'` (Fallout).

The `_STOPNAMES` half is already open as **8f50f37255b5** and is not re-filed; this order
covers the `len(key) < 3` half, which that order does not mention, and supplies the number
for both. Nothing prints either count: `main()` reports `entries` and `distinct keys` and
never says 415 entries did not make it, which is this file's own "a measurement nobody
prints is not a measurement" rule broken in the one place it would show a loss.
Confidence: high (measured).

### MINOR

**B07-6 — `feats.resolve_title` caps its candidate list at `srlimit=8` with no
continuation.** `src/feats.py:763`. `discover()` was corrected to walk `continue` through
`_api_list_all` precisely because `aplimit`/`srlimit` are per-request maxima and not
answers; `resolve_title` (and `_page_exists`, harmlessly, since it asks about one title)
was not. The function's whole reason for existing is the 17,148 entries whose catalogue
name is not the wiki's page title, and a correct title ranked ninth by relevance is
invisible to it. Ranking is fine; the cutoff is the cap. (Both functions are currently
callerless — open order 665e3609bc82 — which is why this is MINOR rather than MAJOR.)
Confidence: high on the fact, medium on the impact.

**B07-7 — `evidence_for` runs the WIKITEXT stripper over plain prose for `pages:` hosts.**
`src/feats.py:1181` (`plain = host.startswith("doc:")`) against `:1187`
(`wiki_source = reads_as_wiki(host)`).

`reads_as_wiki` answers False for a `pages:` host that has registered URLs, and the page
gate correctly drops its markup layer — but `clean = wt if plain else strip_wikitext(wt)`
keys off `doc:` alone, so `endpoint.fetch_html`'s extracted prose still goes through
`strip_wikitext`. The comment two lines above states the reason not to
("running the wikitext stripper over real prose eats legitimate brackets") and then wires it
only to `doc:`. Live for five sources bound `pages:` in WIKI_HOSTS today (A Plethora of
Paladins, Guildmasters' Guide to Ravnica, KibblesTasty, all Creeper World, the Sex Worker
background). Demonstrated damage is small but real, e.g.
`'Roll 1d20 <plus> your proficiency'` -> `'Roll 1d20 your proficiency'`, and a leading
`!` or `;`/`:`/`=` on a prose line is eaten as table/heading scaffolding.
Confidence: high.

**B07-8 — `generate.py`'s raw-markdown write is unguarded while the call three lines below
it has a handler for the identical failure.** `src/generate.py:543-545`.

    raw_path = os.path.join(raw_dir, safe_filename(job["address"], "md"))
    with open(raw_path, "w", encoding="utf-8") as f:

A `PermissionError`/`OSError` here escapes the per-job `try` (which closed at :509) and ends
the whole pass — the exact outcome the `compress_store.store()` handler immediately below
was added to prevent ("ONE BLOB THAT WOULD NOT LAND MUST NOT END THE RUN ... a
PermissionError streak on one chapter's rename would have taken a multi-hour pass down with
it"). It is also a truncate-then-fill on a path `catalog.json` then advertises.
Confidence: high.

**B07-9 — `output/index/failures.json` is never pruned, so a refusal that was later fixed
is indistinguishable from a live one.** `src/generate.py` — six `failures[...] = {...}`
sites, no `failures.pop(...)` on success anywhere. The closing line prints THIS run's
`fail_count` and points the reader at a file that today holds six failures from four
different runs spanning 2026-08-19 to 2026-08-25 (all transport: Ollama read timeouts, a
500, a connection reset) while `catalog.json` is `{}`. The project solves this problem
properly one module over — `workorders.resolve()` deletes on close and appends to a paper
trail — and its argument applies verbatim: "an order that is 'resolved' but still listed is
indistinguishable from an open one to the next reader".
Confidence: high.

**B07-10 — `resync_roll` repairs `status` only inside the count-mismatch branch, and an
unreadable record file leaves a row silently stale.** `src/resync_roll.py:78-103` and
`:60-62`. A roll row whose `entry_count` already agrees but whose `status` does not (the
`entry_count: 0` + `status: catalogued` pair the code at :95-103 exists to end) is never
visited, because the status assignment sits inside `if r.get("entry_count", 0) != n`. And a
record file that fails to parse is `continue`d with only a `silence.note`, so its source
keeps whatever counts the roll already held while the summary prints
`roll now: X/Y sources catalogued` as though everything had been checked. Neither the
unreadable-file count nor the "row had no record file" count reaches the printed diff.
Confidence: high.

**B07-11 — `rigor.py:119` cites `tempus.py:182-186` for a rationale that is at
`tempus.py:194-222`.** The cited lines are the closing paragraph of
`rung_description_length`'s docstring ("This is not a new scale..."); the passage that
"split `band_resolution` out for exactly this reason" is `band_resolution`'s own docstring
starting at :194. The same paragraph goes on to argue "a section tag rather than a line
number, because a line drifts and a tag does not" while itself using a line number. Cite by
symbol: `tempus.band_resolution`.
Confidence: high (verified against both files this run).

---

## HEALTHY — verified, not merely unexamined

* **The fixes named in the brief all hold.** `_api_list_all` counts a first-request failure
  before returning `rows` (`_CAP_BOUND[cap_key]` is incremented outside any `if rows:`);
  `page_looks_real` has no `title` parameter and `wiki` is keyword-only, so an old positional
  call raises instead of loosening the gate; `resolve_hosts` sets `_HOSTS_DENIED` and
  `main()` returns 1 on it; `evidence_for`'s cache write feeds `_UNCACHED` and `roll()`
  prints it; `generate.save_json` returns `landed` and `main()` turns the two final writes
  into the exit code; `weave_index`'s description field is uncapped and both writes are
  gated with a distinct SPLIT message for the half-landed case. All read fresh; all correct.
* **`discover()` refuses `extra` loudly** rather than honouring a numeric cap, and the
  `aplimit=500`/`srlimit=50` in it really are per-request maxima behind a continuation walk
  whose only stop conditions are "the wiki said that is all" and "the wiki repeated a token"
  (the latter counted). This is the correct shape and the rest of the fetch layer should
  match it (see B07-6).
* **The adaptive backoff is sound.** `note_ok` is taken only after `json.loads` succeeds, so
  an interstitial 200 cannot decay the backoff or zero the strike counter; `note_throttled`
  widens on the first 429/503 and hands the host to `binding_health` at three consecutive
  strikes; `_COUNTS_LOCK` guards the read-modify-write on `_RATE_LIMITED`/`_CAP_BOUND`
  (which `_HOST_LOCKS` could never have serialised, `_CAP_BOUND` not being keyed by host);
  `_HOST_LOCKS` is a `defaultdict(threading.Lock)` whose factory is a C builtin, so the
  missing-key insert does not race. `backoff_state()` is read by `dashboard.py:569`.
* **The 404 / non-JSON / network split in `api()`** puts three different facts in three
  different silence buckets, and the retry behaviour is identical across them.
* **`_QUANTITY` group numbering is right** — group 4 is the unit, groups 2 and 3 are the two
  exponent shapes, and the superscript translation lands both in one `exponent` field.
  Verified live: `5 x 10^44 joules` -> `value '5e44', exponent '44'`.
* **`_unwrap_templates`** handles `{{{param|default}}}` at three braces before the two-brace
  branch can eat it, splits on top-level pipes only, and keeps values.
* **`sweep.nested_run`** genuinely tests subset-hood on the rows in hand rather than
  asserting the funnel; within a verified nested chain `drop` cannot go negative, which was
  the defect it replaced.
* **`descending_ladder`'s constants check out**: PLANCK_ENERGY = PLANCK_MASS x c^2 to four
  figures; the binding energies for Molecular (5 eV), Atomic (13.6 eV), Nuclear (8 MeV) and
  Nucleonic (938 MeV) all convert correctly; `DESCENDING` is strictly decreasing in length,
  which is what `rung_for_length`'s scan requires; the top of the domain now answers
  `(None, None)` instead of rounding a galaxy into "Continental".
  Note for a future consumer: `binding_J` is NOT monotonic in rung (it falls from 1e5 J at
  Organic to 1e-11 J at Cellular and rises again below Molecular). That is physically right
  and it means the column cannot be used as an ordered Ruin ladder by bisection. No consumer
  exists today (open order 66f96febdb3a).
* **`tempus`**: `band_resolution` deliberately differs from `rung_description_length` and
  `rigor.measure_bit_value` divides by 10 at the call site, as `verify_math` pins;
  `prescience_horizon_bits` refuses a non-positive lead time rather than returning a
  plausible small number; `apparent_lag_years` returns one shape on both branches.
* **`handbuilt`** writes the artifact BEFORE printing (so a cp1252 console cannot cost the
  file), gates the replace, returns 1 on denial, and handles the `"unestimable"` sentinel in
  `%5.1f`. Its `(:182-201)` line citation for Zalama's unestimable axes is ACCURATE as of
  this run (`:182` is `ruin=("unestimable"`, `:201` is `discernment=("unestimable"`) — but
  it is the fragile idiom, and it will drift the first time a sheet is added above it.
* **Display truncations are display truncations**, and were checked one by one rather than
  assumed: `feats._show` (`feats[:6]`, `quantities[:4]`, and the refusal list deliberately
  NOT capped), `generate` (`refused_src[:20]` with "+N more", `missing[:8]` with "+N more",
  `_unearned[:5]` alongside the full count, `dry-run pending[:3]` with the total),
  `weave_index` (`spread[:10]`, `top[:18]`, `srcs[:5]` with an ellipsis), `sweep`
  (`best[:top]`, `gap.most_common(10)`, `bysrc.most_common(8)`), `handbuilt`
  (`cited[:58]`). None of them touches stored data. Two are worth a note rather than an
  order: `sweep`'s "BIGGEST GAPS" and "REACHED BUT SILENT" lists state neither the number of
  sources omitted nor a "+N more", so a reader cannot tell the list is partial —
  which is the one thing `feats._show`'s own comment says a diagnostic must not do.
* **Operator-supplied limits are not caps in the Hard Rule 0 sense** and are left alone:
  `roll(limit=None)` / `--limit`, `generate --limit`, `sweep --top`. Each defaults to the
  whole set and is named on the command line by a person.

## OBSERVED IN PASSING (outside this batch, not filed)

* `src/secondopinion.py:24` cites `descending_ladder.py:129 from_m` for vulture's dead-store
  finding. Line 129 is now inside `compton_confinement_energy`'s docstring, `from_m` is at
  :156, and the finding itself was fixed (the argument is reported in `shrink_report`'s
  return). The passage reads as an open finding at a line that never held it.
* `src/verify_math.py:3743-3755` already records that `sweep.load`'s docstring claim of a
  call site at `sweep.py:129` is false and says it is "that file's to correct". It is still
  uncorrected in `sweep.py:84`, and is inside the scope of open order 2b695c192470, so it is
  not re-filed here.
* `drill.py:3096`'s `... or True` is a QUOTATION of the defect inside the docstring that
  documents its repair, not a live tautology. Checked, not a finding.

---

## ORDERS FILED (handler RUN, found_by sweep37-batch07)

| id | severity | code |
|---|---|---|
| 64e4db060ad6 | MAJOR | FEATS_RESOLVE_HOSTS_FREEZES_A_FAILED_PROBE_AS_NO_WIKI |
| 75307186e12a | MAJOR | WEAVE_INDEX_DESIGNATIONS_CACHES_THE_ERROR_PATHS_EMPTY_SET |
| eacc5444288c | MAJOR | FEATS_MINE_DROPS_EVERY_TEXT_UNIT_OVER_400_CHARS_UNCOUNTED |
| 8605c2ed6061 | MAJOR | RESYNC_ROLL_EXIT_CODE_NEVER_REACHES_THE_SHELL |
| e959f566275d | MAJOR | WEAVE_INDEX_SHORT_KEY_FILTER_DROPS_ENTITIES_FROM_THE_STORED_INDEX |
| 09a410dc7457 | MINOR | FEATS_RESOLVE_TITLE_SRLIMIT_8_IS_A_CAP_ON_A_CANDIDATE_LIST |
| abe49b3ba7b3 | MINOR | FEATS_STRIPS_WIKITEXT_FROM_PROSE_ON_PAGES_HOSTS |
| 74b37b4c6c3a | MINOR | GENERATE_RAW_MARKDOWN_WRITE_IS_UNGUARDED_AND_NON_ATOMIC |
| b3c806f694d6 | MINOR | GENERATE_FAILURES_JSON_IS_NEVER_PRUNED_ON_SUCCESS |
| 2ab24aeb63f7 | MINOR | RESYNC_ROLL_STATUS_REPAIR_IS_GATED_ON_A_COUNT_CHANGE |
| ad6496327a94 | MINOR | RIGOR_CITES_A_DRIFTED_LINE_RANGE_IN_TEMPUS |

Not re-filed (already open): 8f50f37255b5 (_STOPNAMES half of B07-5, now quantified at 155
entries), 944274e8bfd8 (ENTITY_INDEX.json on disk still truncated), 665e3609bc82
(resolve_title/_page_exists/axis_evidence/remine callerless), 2b695c192470 (sweep.load
callerless and its ":129" docstring claim), 66f96febdb3a (descending_ladder has no
consumers), 0291835411d9 (tempus.DEGENERATE_TIME dead).

Coverage recorded: `sweep_plan.record('run37', [...8 modules...], batch=7)` — all eight now
read `run37`.
