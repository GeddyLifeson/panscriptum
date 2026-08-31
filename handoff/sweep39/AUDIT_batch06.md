# run39 — AUDIT, batch 06

Modules owned by this batch (obtained from `sweep_plan.batches(16)[5]['modules']`, not from any
typed list), every one read in full, no sampling:

| module | lines |
|---|---|
| `src/feats.py` | 1866 |
| `src/chain.py` | 740 |
| `src/onomast.py` | 581 |
| `src/reference.py` | 480 |
| `src/prose_gate.py` | 371 |
| `src/cleanup.py` | 311 |
| `src/tempus.py` | 274 |
| `src/ledger.py` | 172 |
| `src/module_index.py` | 116 |

Read-only audit. No source file was edited. `pyflakes` over all nine is clean; `vulture` was run
as an independent second opinion and every one of its 30 hits was checked by hand against a
repo-wide grep — most are cross-module callers vulture cannot see, and only the ones confirmed
dead repo-wide appear below.

`prose_gate.py` is owner-held. Nothing below proposes opening `prose_enabled` or
`step4_enabled`, and nothing below proposes removing or weakening any gate. The one prose_gate
finding is that an enforcement function is *not wired in*, and its remedy is to wire it in.

---

## MAJOR

### M1 — `feats.resolve_title()` is the fix for 17,148 unmined entries and has never been called
`src/feats.py:933`

`resolve_title(host, name)` exists to solve a stated, measured problem: *"17,148 entries mined to
nothing because the entity's catalogue name is not the wiki's page title -- 'Hulk (Bruce Banner)'
where the wiki says 'Hulk'"*. It contains the careful ranking (exact normalised match, then
name-plus-disambiguator, nothing else) that makes such a lookup safe.

**Verified dead.** `grep -rn resolve_title --include=*.py .` returns exactly one line: the `def`.
It is not called from `feats.py` itself, and `grep -rn "def .*resolve.*title\|wiki_title\|title_for"`
over all of `src/` shows this is the **only** title-resolution function in the codebase, so no
other module is doing the job under another name.

The live path does not do it: `evidence_for` (`feats.py:1476`) calls `discover(host, name)`, and
`discover` (`feats.py:872-917`) puts the raw catalogue name in via `add(name)`, asks `allpages`
for the prefix `f"{name}/"`, and filters search hits on `key in row["title"].lower()`. Both
call sites of `evidence_for` pass the raw catalogue name (`read.py:719`, `magnitude.py:1139`).
`fetch()`'s `redirects=1` rescues a redirect, but not `Hulk (Bruce Banner)` → `Hulk`.

This is the file's own signature failure: the entity mines to zero pages, `roll()` counts it
under `empty`, and it reads downstream as an entity with no evidence.

**Remedy:** call it. In `discover()`, resolve the entity's own title before `add(name)` and add
the resolved title alongside (never instead of) the raw name, and use the resolved title as the
`apprefix` for the subpage walk; or resolve in `evidence_for` before `discover` and pass both.
Whichever is chosen, record on the cached record which name the pages were found under (the
`mined_under` stamp already exists for exactly this kind of question), so a re-mine after the
change is not invisible the way `mined_under_superseded_gate`'s docstring describes. If the
owner's judgement is that the ranking is not safe enough to switch on, then the function should
say so in its own docstring rather than reading as live machinery.

### M2 — `resolve_hosts` writes a clean "no wiki" negative for a source it never probed
`src/feats.py:720-734`

```python
undetermined = []
for slug in _slugs(src):
    ...
else:
    if undetermined:
        unprobed[src] = undetermined
        known.pop(src, None)
    else:
        known[src] = None
```

The comment immediately above promises the opposite: *"a source with any such candidate is left
OUT of the map entirely rather than recorded as absent"*, and order `64e4db060ad6` is quoted at
length for the rule that **only a clean negative may be cached**.

When `_slugs(src)` returns an **empty list** the `for` body never runs, `undetermined` stays
empty, the `else` clause fires, and `known[src] = None` is written — a recorded absence reached
without a single probe. `roll()` then drops every entity of that source from the universe
(`h = hosts.get(r["source"]); if not h: continue`, `feats.py:1605-1607`).

**Measured against the live roll.** `_slugs` drops any candidate of length ≤ 2, so a short source
name yields nothing at all:

```
sources: 215
EMPTY slug list: 1  ['DC']
```

`DC` — one of the largest sources in the library — produces **zero** candidates today. It
survives only because the `wiki_page`-netloc branch above (`feats.py:692-697`) answers first
(`data/WIKI_HOSTS.json` has `DC -> 'dc.fandom.com'`). Any future short-named source with no
stored `wiki_page` takes the unprobed-null path, and because `known.get(src)` is falsy for `None`
the source is re-probed and re-nulled identically on every run — permanent in effect even though
it is recomputed.

**Remedy:** treat "no candidate was generated" as its own third case, not as a negative. Put it
in `unprobed` with the reason "no slug candidate could be derived from the source name" and
`known.pop(src, None)`, exactly as the transport-failure case does; or lower the `len(c) > 2`
floor so a two-letter name still produces a candidate to probe. The `else` branch must only write
`None` when at least one candidate actually returned a clean 404.

### M3 — `feats.py --roll` exits 0 whatever happened, and it is a standing job
`src/feats.py:1838-1842`

```python
if a.roll:
    recs = P.records()
    hosts = resolve_hosts(recs, verify=False)
    roll(recs, hosts, workers=a.workers, limit=a.limit, only=a.only)
    return 0
```

`roll()` returns a `done` dict carrying `errored` and prints `_UNCACHED` (entities mined and then
denied a cache write), `_CAP_BOUND` (discovery walks that could not finish) and `_STALE_GATE`.
Every one of those verdicts is dropped at the call site; the return value is discarded entirely.

The sibling branch does the opposite eleven lines up — `--hosts` ends `return 1 if _HOSTS_DENIED
else 0` (`feats.py:1836`), under a comment saying *"resolving the map and failing to save it is a
failed run, not a successful one with a note attached"*. The same reasoning applies here and was
not applied.

This matters more than for a hand-run tool: `feats.py --roll` is a **standing job**
(`overnight.py:798`, and `overnight.py:297` names it as a real fragment). A roll in which every
`replace_retry` was denied prints the `_UNCACHED` paragraph — *"if this number is large the roll
bought nothing"* — and then hands the keeper a clean rc=0.

**Remedy:** capture `done` and carry a verdict. Nonzero when `sum(_UNCACHED.values())` is
nonzero (nothing reached disk is not a successful mining pass), and nonzero when
`done["errored"] == done["n"]` with `done["n"] > 0` (nothing was read at all). A partial error
rate should stay rc=0 — a long best-effort pass legitimately raises on some entities, and
escalating that would be the alarm-that-always-sounds failure Hard Rule -1 names.

### M4 — `chain.main()` reports success over a CHAIN.json that was never written
`src/chain.py:149-153`, `src/chain.py:715`, `src/chain.py:734`

`write_result` checks its own write and prints to stderr on denial —

```python
if not silence.write_json(OUT, out, indent=1, ensure_ascii=False):
    silence.note("chain.py:write_result-denied")
    print("chain: CHAIN.json could not be replaced; ...", file=sys.stderr)
return out
```

— but returns `out` unconditionally, so the verdict is available to no caller.

`pipeline.phase_chain` compensates: it does not trust the writer, it asks the disk
(`pipeline._chain_landed`, `pipeline.py:1795-1824`, then `gate_done(st, "chain",
[_chain_landed(CH, out)])` at `pipeline.py:1869`). That path is sound, and its docstring says
plainly why: *"`write_result` hands back the DATA it tried to write, unconditionally, whatever
the disk said."*

`chain.main()`, the other documented caller, has no such check. Both of its `write_result` calls
(`chain.py:715` and `chain.py:734`) discard the return and both fall through to `return 0`. A
denied replace exits clean with `-> data/CHAIN.json` printed underneath it, over last cycle's fit.

This is the same class the sweep of 2026-08-25 and rulings `dc5c92aad5c1` / `3e65dbed45a6` closed
at `onomast.py:569-573`, `reference.py:363-373`, `genre.py:327-331`, `sevenfold.py:412-415` and
`wh40k.py:289-293`. `chain.main()` is the site that was not visited.

**Remedy:** give `chain.main()` the same disk check `phase_chain` uses — call
`pipeline._chain_landed`-equivalent logic (or have `write_result` return `(out, landed)` and
update both callers, which is cleaner but widens a signature `drill.py`'s phase-4 net pins; see
the `_LAST_EXTRACT` comment at `chain.py:91-98` before choosing that route). Then
`return 0 if landed else 1`, and say WRITE DENIED rather than `-> data/CHAIN.json`.

### M5 — `page_looks_real`'s refusal-marker layer is refusing real articles, and on the API path it cannot do anything else
`src/feats.py:196-199`, `:249-252`

This started as a question about a possible false positive and the corpus settled it.

**Mechanism.** `_REFUSAL_MARKERS` is matched as a plain substring against the lowercased page,
and a hit returns `False` on its own (`feats.py:249-252`). The layering argument the docstring
borrows from maigret/sherlock — length, then refusal, then positive markup evidence, *"a page
must clear SEVERAL"* — does **not** apply to this layer; one signal is sufficient.

`page_looks_real` is called on `wt`, the raw text as fetched (`feats.py:1501`). On a `MODE_API`
host `wt` is `p["revisions"][0]["slots"]["main"]["content"]`, taken out of a 200 that **already
parsed as JSON** (`feats.py:1005-1011` via `api()`). A block page, a WAF interstitial or a login
wall **cannot arrive down that path at all** — it fails `json.loads` and is already caught,
correctly and separately, by `api()`'s `except json.JSONDecodeError` arm as `"nonjson"`
(`feats.py:520-540`). So on the API path every hit of this layer is necessarily a false positive:
it is matching the fiction's own words.

**Measured, uncapped, over the whole of `data/feats/`.** 119 records carry a
`carries a refusal marker` refusal:

| marker | records |
|---|---|
| `rate limit` | 101 |
| `temporarily unavailable` | 13 |
| `access denied` | 3 |
| `captcha` | 2 |

**Every one of the 119 is on a Fandom host whose `data/ENDPOINTS.json` mode is `"api"`** —
`finalfantasy` ×100, `legendofzelda` ×10, `dc` ×2, `masseffect` ×1, `diablo` ×1 (the rate-limit
and temporarily-unavailable families), plus `doom` ×2, `warhammer40k` ×2, `regularshow` ×1 (the
access-denied and captcha families). **Not one** is on the single `MODE_RAW` host or on a
`pages:` / HTML corpus — that is, not one is on a transport where this layer could have caught a
real block page.

The bodies are article-sized, which settles it independently of the transport argument. Opened
and checked:

```
finalfantasy/Bladedance (Final Fantasy XIV)   41,125 chars   0 feats   'rate limit'
finalfantasy/Chimatsuri                       41,125 chars   0 feats   'rate limit'
finalfantasy/ATK Up (VII Remake)              22,636 chars   0 feats   'rate limit'
finalfantasy/Auto-Remedy                      22,636 chars   0 feats   'rate limit'
doom/Union Aerospace Corporation              14,960 chars   0 feats   'access denied'
doom/UAC announcer                             9,680 chars   0 feats   'access denied'
regularshow/Ladonna                            3,702 chars   0 feats   'access denied'
warhammer40k/Hecaton Aiakos                    3,373 chars   0 feats   'captcha'
warhammer40k/Spiculus Bolt Launcher            1,982 chars   0 feats   'captcha'
```

A Cloudflare interstitial is not forty-one kilobytes of wikitext. The Doom UAC announcer's
canonical voice line *is* "Access denied." `data/ENDPOINTS.json` holds **321 `api` hosts, 2,991
`dead`, and exactly one `raw`** — so this layer is running almost entirely on the one transport
where it can only be wrong.

Each of these 119 is now on disk as an entity with no evidence *and a recorded reason that reads
as an honest diagnosis* — which is worse than a blank, and is the exact inversion of what the
gate was written to prevent.

*One caveat, stated so it is not mistaken for certainty:* the endpoint mode read here is
**today's**, not necessarily the mode in force when each record was mined. The article-sized-body
evidence does not depend on that, and is what the finding rests on.

**Remedy:** gate the refusal-marker layer on the **transport**, not on the `wiki` flag. It earns
its keep on the paths that return an unparsed body — `endpoint.fetch_raw` (`MODE_RAW`) and
`endpoint.fetch_html` (the `pages:` corpora) — and is dead weight plus a false-positive source on
`MODE_API`. Add a keyword (`parsed=False`) that callers holding API revision content set, which
skips the marker layer while keeping the length floor and the wiki-markup layer;
`binding_health.py:494` and `:661` fetch raw bodies and must keep the default. Do **not** simply
drop the ambiguous markers — on the raw and HTML paths `"access denied"` and `"captcha"` are
exactly the signals wanted; for those paths, require corroboration for the ambiguous markers only
(a body carrying `"captcha"` that also clears the wiki-markup layer and runs to thousands of
characters is an article about captchas, not a captcha). And the cache must be re-earned: *"A FIX
WHOSE EFFECT IS CACHED AWAY IS NOT IN EFFECT"* (`feats.py:352-376`) — the `mined_under` stamp is
the existing mechanism for that, and needs a marker-layer version field.

---

## MINOR

### N1 — `mine()` silently discards most of what the evidence gate refused
`src/feats.py:1181-1188`

```python
for s in _units(text, "mine"):
    if P.valid_scale_note(s):
        kept.append({"feat": s, "page": page})
    elif _QUANTITY.search(s) or re.search(r"\b(destroy|obliterat|shatter|surviv)", s, re.I):
        rejected.append({"text": s, "page": page})
```

The module docstring (`feats.py:27-29`) states the opposite as a design commitment: *"it keeps
everything it gathers, **including what the gate turned down**, because the previous pass
discarded its rejections and left the rejection rate unauditable."* `mine`'s own docstring
repeats it: *"Rejections are kept — see the module docstring."*

The `elif` means only *interesting* rejections are kept. A unit that fails `valid_scale_note` and
carries neither a `_QUANTITY` match nor one of four verbs reaches **nothing**: not `feats`, not
`gate_rejected`, not `quantities`, and not `roll()`'s summary. This is precisely the shape order
`eacc5444288c` closed one line above for the 20/400-character length filter — the `_UNIT_DROPS`
tallies exist because a drop that reaches no counter is indistinguishable from a drop that never
happened. The rejection *rate* the docstring promises is auditable is therefore a rate over a
pre-filtered denominator.

**Remedy:** add a third `_UNIT_DROPS`-style counter — `{"gate_failed_uninteresting": n}` per
gate, incremented in the `else` — and print it in `roll()`'s summary beside the length-filter
line. Do not widen `gate_rejected` itself: storing every refused sentence would multiply the
per-entity file size by a large factor for no evidentiary gain, and the counter answers the
auditability question the docstring actually raises. Then correct the two docstrings to say what
the code does: rejections *that carry a quantity or a ruin verb* are kept, and the rest are
counted.

### N2 — `pages_read` and `chars_read` count pages that were refused as not-the-article
`src/feats.py:1481-1517`, consumed at `src/coverage.py:177-179`

`evidence_for` builds `pages` from `fetch()` / `_source_pages_text()`, records refusals in
`unreal`, and `continue`s past them — but the refused titles stay in `pages`:

```python
out = {"entity": name, "host": host, "pages_read": sorted(pages),
       "chars_read": sum(len(v) for v in pages.values()), ...
       "pages_refused": unreal, ...}
```

So an entity every one of whose pages was a Cloudflare interstitial or a soft-404 is recorded
with a non-empty `pages_read` and a large `chars_read`.

Inside `feats.py` this is handled — `roll()` counts `refused` and `refused_entities` separately
(`feats.py:1664-1669`). One layer up it is not. `coverage.py:177-179`:

```python
pages = d.get("pages_read") or d.get("pages") or []
feats = d.get("feats") or []
st = "CITED" if feats else ("READ" if pages else "NO PAGE")
```

A wholly-blocked entity is classified **READ** with zero feats — i.e. read-and-silent — which is
exactly the "an absence wearing the costume of a failure" confusion `pages_refused` was added to
end, restored at the consumer. 119 cached records under `data/feats/` currently carry a
`carries a refusal marker` refusal (measured by `grep -rlo` over the whole corpus, uncapped).

`magnitude.py:1367` also copies `ev["pages_read"]` verbatim into an assay row's `"pages"` field,
so refused titles can appear in a provenance list.

**Two readings are defensible and this is filed as a finding with an open remedy**, not as a
settled one: (a) `pages_read` is misnamed and should hold only the pages that passed the gate,
with the refused ones reachable through `pages_refused`; or (b) the field is a fetch log and
`coverage.py`/`magnitude.py` should subtract `pages_refused` themselves. (a) changes a persisted
schema and invalidates readers that predate `pages_refused`; (b) leaves the trap set for the next
consumer. My reading is that (a) is right and should carry a `pages_fetched` field for anyone who
wants the old number, but the schema call is the owner's. Either way `coverage.py`'s three-way
status needs a fourth state ("REFUSED"), because "we were served a block page" is not "READ".

### N3 — `axis_evidence()` is a dead duplicate of the gate `by_axis()` runs inline
`src/feats.py:1301-1310` against `src/feats.py:1322-1333`

`axis_evidence(sentence, axis)` applies `P._STATBLOCK`, `_AXIS_ACT_RE[axis]`, `P._PATIENT`, and
then `_OBJ | P._MAGNITUDE | _CMP`. `by_axis` applies the identical four gates with the
axis-independent three hoisted out of the per-axis loop (its own comment explains the hoist as a
3× regex saving over an 874 MB corpus). `by_axis` is live (`magnitude.py:867`); `axis_evidence`
has **zero callers repo-wide** (verified by grep across all `*.py`).

That is not merely dead weight: the axis gate now has two definitions, and anyone tuning
`axis_evidence` — the one with the explanatory name and the docstring — would change nothing,
while anyone tuning `by_axis` leaves the named function silently disagreeing with the live one.

**Remedy:** delete `axis_evidence`, or reduce it to a thin wrapper that calls into the same
predicate `by_axis` uses so the two cannot drift. Do not "fix" it by calling it from `by_axis` —
that would undo the deliberate hoist.

### N4 — three dead functions in `feats.py`, one of them documented as such
`src/feats.py:576` (`alive`), `src/feats.py:925` (`_page_exists`), `src/feats.py:1559` (`remine`)

All three verified with zero callers repo-wide.

* `alive(host)` — a one-line wrapper over `alive_verdict`. `resolve_hosts` calls
  `alive_verdict` directly (`feats.py:723`). The wrapper's own docstring warns that any caller
  caching a negative must use `alive_verdict` instead; with no callers at all, it is a trap
  standing open for the next person who greps for "alive".
* `_page_exists(host, title)` — a title-existence probe with no caller; it is the natural
  companion to the also-dead `resolve_title` (M1), which suggests both belong to one unwired
  feature rather than to two separate oversights.
* `remine(path)` — its own comment states *"It has no callers yet, so nothing today has a
  handler to break; a future one is told."* Deliberate, correctly documented, and listed here
  only for completeness. **No action.**

**Remedy:** delete `alive` and `_page_exists` if M1 is declined; wire `_page_exists` in with
`resolve_title` if M1 is accepted. Leave `remine`.

### N5 — four stale `chain.py:NNN` cross-references, each verified against the current file
`src/chain.py:251-252`, `:364`, `:371`, `:449`

| comment | claims | actually at |
|---|---|---|
| `chain.py:251-252` | *"This was `chain.py:91` and the line moved to 169"* | the `silence.note("chain.py:harvest-feats-unreadable")` it describes is at **line 256**; line 169 is blank |
| `chain.py:364` | *"was `chain.py:155`; the line is now 276"* | the note is at **364**; line 276 is the harvest prune comprehension |
| `chain.py:371` | *"was `chain.py:161`; the line is now 283"* | the note is at **371**; line 283 is inside an unrelated comment |
| `chain.py:449` | *"was `chain.py:252`; the line is now 345"* | the note is at **450**; line 345 is inside `entity_index()` |

Each was checked by reading the cited line. The irony is exact: the comment at `chain.py:251-253`
gives the reason these matter — *"a tag that points at an unrelated line is worse than an opaque
one, because it sends the next reader somewhere confidently wrong"* — and then hardcodes a line
number that has since moved.

One reference in the same file **is** correct and was checked: `chain.py:567`'s
*"`prov[e].append(src)` runs once per KEPT OUTCOME in `extract` (:492)"* — `prov[e].append(src)`
is on line 492.

**Remedy:** the file already knows the answer. Replace the numbers with the same thing that
replaced the note *tags*: name the function and the fact, not the line. `"was tagged
chain.py:155; this is _ask's cloud arm"`. A number in a comment in a file that is edited every
sweep will go stale again by construction.

### N6 — two stale cross-file references in `cleanup.py`, plus one in `onomast.py`
`src/cleanup.py:131`, `src/cleanup.py:255`, `src/onomast.py:562`

* `cleanup.py:131` — *"`_SETTING_META` ... lives at `pipeline.py:1204`"*. It is defined at
  **`pipeline.py:1366`**; line 1204 is a paragraph of the magnitude-band prompt. Verified by
  `grep -n "_SETTING_META" src/pipeline.py` (hits at 1366 and 1406) and by reading 1198-1212.
* `cleanup.py:255` — *"like every other caller of the two-writer contract
  (`catalogue_web.py:498` gates `write_record_catalogue` the same way)"*. The gate is at
  **`catalogue_web.py:600`** (its comment at 588); line 498 is `ap.add_argument("--limit", ...)`
  inside `main()`.
* `onomast.py:562` — cites three siblings that carry a denied write into the exit code:
  `genre.py:327-331` ✔ (verified, correct), `sevenfold.py:412-415` ✔ (verified, correct),
  `wh40k.py:277-282` ✘ — that range is a paragraph of commentary about atomicity; wh40k's
  actual write-denied-and-return-1 block is at **`wh40k.py:289-293`**.

**Remedy:** as N5 — name the symbol, drop the number. `"`pipeline._SETTING_META`"`,
`"`catalogue_web.main`'s `write_record_catalogue` gate"`, `"`wh40k.main`'s write-denied branch"`.

### N7 — `coin_well_formed`'s exhausted path returns a name it has already proven unusable
`src/onomast.py:238-265`

The final line is

```python
silence.note("onomast.py:coin-exhausted")
return coin_name(f"{base}|fallback", register)
```

and `coin_name` is deterministic, so this is byte-for-byte the same string already computed and
rejected twelve lines up at `onomast.py:253-255` — rejected precisely because it failed
`well_formed` or was already in `taken`. So the one exit taken when naming is hardest returns a
designation that is known malformed, known duplicate, or both.

The comment at `onomast.py:244-249` describes exactly this defect as the thing being fixed
(*"the one path taken when naming is HARDEST returned a name that could be malformed AND could
duplicate a name already issued. 'Shelfmarks are unique' is one of the 39 standards"*), and the
repair widened the salt space from 400 to 10,000 rather than closing the exit. Beyond 10,000 the
original hazard is intact.

It is **loud** — `silence.note` fires — and `name_worlds` adds the returned name to `taken`
afterwards, so a duplicate will not compound. It is nevertheless a path that can break a stated
invariant and return.

**Remedy:** two options, and this is a judgement call. (a) Raise. The comment argues against it
— *"refusing to name anything would be the worse failure"* — but a duplicated shelfmark
silently reassigns published citations, which is worse than a loud stop, and the exhaustion is
already recorded as an alarm. (b) If a value must be returned, make the last resort provably
unique rather than merely deterministic: append a short digest of `base` to the coined stem so
the result cannot collide even though it may be less pronounceable, and mark the record with a
`coined_under: "exhausted"` flag so a reader can see which designations came from the degraded
path. Either way, do not return a string the function has just tested and rejected.

### N8 — `clean_ceiling`'s prefix branch guesses between several candidates
`src/cleanup.py:175-179`

```python
low_pref = [n for n in entry_names
            if n.lower().startswith(ce.lower()) and len(ce) >= 6]
if len(low_pref) >= 1:
    return min(low_pref, key=len), "prefix"
```

The docstring's contract is *"If none of those land, the ceiling is left ALONE and reported --
guessing a name would be worse than admitting phase 1 answered the wrong question"*, and the
comment above records that a substring strategy was **removed** for returning the wrong entity.

`len(low_pref) >= 1` admits the ambiguous case. Where two or more catalogued entries share the
prefix — `Kratos (God of War)` and `Kratos Aurion`, a family surname, a numbered series — the
shortest wins by `min(..., key=len)`, which is a guess, silently labelled `"prefix"` and (with
`--apply`) written into `synthesis.ceiling_entity`. The `exact` branch above already handles the
unambiguous identity case, so this branch only ever fires on a proper prefix.

The safety argument in the comment — *"A name cannot prefix an unrelated entry by accident the
way it can appear inside one"* — is sound for **one** match and does not extend to several.

**Remedy:** `if len(low_pref) == 1: return low_pref[0], "prefix"`, and otherwise fall through to
`return ce, "unresolved"` so the ambiguity is reported in the "still unresolved (left alone, not
guessed)" list, which is what that list is for. Optionally add a `"prefix-ambiguous"` reason so
the two kinds of unresolved are distinguishable.

### N9 — `cleanup.py`'s report truncates five lists and every row inside them, with no marker and no artifact
`src/cleanup.py:271-287`, and the field cuts at `:200`, `:202`, `:230`, `:276`, `:279-280`, `:283`, `:287`

The report prints `nav[:5]`, `ceil_fixed[:6]`, `ceil_unres[:4]`, `desc_fixed[:5]` and `thin[:5]`
with no "... and N more", and cuts individual fields mid-value: `ce[:70]`, `ce[:52]`, `d[:46]`,
`cd[:46]`, `s[:26]`, `s[:22]`, `str(n)[:22]`, `str(n)[:26]`.

The totals **are** printed on each heading line, so the reader knows the size — this is the
mitigating fact and it is why this is MINOR rather than MAJOR. But the `unwritten` block twenty
lines below does it properly (`unwritten[:12]` followed by an explicit `... and N more`), so the
file holds two disciplines in one function — the same fault `onomast.main` was corrected for
under order `89fc2eaf23f1`.

The aggravating difference from `chain.main` and `onomast.main` is that **there is no artifact**.
Those two can say "all of them are in CHAIN.json / ONOMASTICON.json"; `cleanup.py` writes nothing
but the records themselves, so the 6th nav name and the 5th unresolved ceiling are unreachable by
any means short of editing the source. A dry run whose whole purpose is to show an operator what
`--apply` would do shows them five of it.

**Remedy:** add `... and N more` to all five, and either widen or mark the field cuts (`%-Ns`
pads without cutting; `textwrap.shorten(..., placeholder=" …")` marks). If the tail is genuinely
wanted, a `--json PATH` flag writing the full five lists would make the previews honest previews.
Do not simply raise the constants — that moves the cliff without marking it.

### N10 — `prose_gate.assert_step4_open()` is the Step-4 interlock and nothing calls it
`src/prose_gate.py:119-124`

`step4_gate_open()` — the read-only predicate — is called by `dashboard.py:580` for display, and
is discussed in a comment at `mutate.py:1172`. `assert_step4_open()`, the function that actually
**raises `ProseRefused`**, has zero callers repo-wide.

**This is not a request to open the gate, and the gate must not be removed.** The finding is the
opposite: the enforcing half of layer 1's Step-4 sibling is not wired to anything, so the refusal
exists only as a function definition. Today that is arguably harmless — Step 4 has not been
built, so there is no entry point to guard — but Hard Rule -1's fourth property is **IN EFFECT**,
and an interlock whose only caller is a dashboard readout is not in effect. The 2026-08-25
incident began with a guard that was present in a file and absent from the running path.

**Remedy:** when the entanglement pass gains an entry point, `assert_step4_open()` must be its
first statement, before argument parsing, the way `escalation.assert_clear` is at
`feats.main:1813`. Until then, `verify_math`/`drill` should pin that the function exists and
still refuses when `step4_enabled` is absent, so it cannot be deleted as dead code by a future
sweep — which is exactly how the prose gate was lost the first time. Consider adding it to the
same PROVEN net family as layers 1-4.

### N11 — `module_index.py` detects a stale hand-kept group list and exits 0
`src/module_index.py:69-72`

```python
stale = [n for n in names if n not in mods]
if stale:
    print(f"module_index: GROUPS[{title!r}] names a module not in src/: "
          f"{', '.join(stale)} -- fix the hand-kept list", file=sys.stderr)
    silence.note("module_index.py:stale-group-name")
```

The check is real and it does reach `state/failures.json` through `silence.note`. But `main()`
returns 0, and the module's own docstring is an argument about hand-kept copies drifting: *"a
hand-kept copy of information the code already carries is a second writer with no merge
strategy"*, and *"the docstring of the module whose entire argument is that hand-kept copies
drift had drifted by twenty-six"*. The one hand-kept list left in the file detects its own drift
and cannot make anything go red.

The denied-write branch four lines below **does** return 1, so the file already accepts that a
verdict belongs in the exit code; this verdict just does not get one. Same family as
`reference.py`'s order `d049dbbfed6e` (*"`inside` was computed, printed, and dropped ... rc is
the only channel out"*).

**Remedy:** track the stale names across all groups and `return 1` at the end if any were found,
distinguishing the two failures in the printout the way `reference.main` distinguishes WRITE
DENIED from CALIBRATION OUTSIDE. The page still regenerates correctly, so this must not skip the
write — it should write, report, and exit nonzero.

### N12 — `reference.py --compare` cuts the one field that explains a refusal
`src/reference.py:431`

```python
print(f"{name:<20}{'--':>12}{status.lower():>12}"
      f"{'':>8}  {str(row.get('reason') or '')[:44]}")
```

`reason` is the automated pass's explanation of why an entity has no result — e.g.
`magnitude.assay_entity`'s *"no axis cleared its gate on this entity's own source pages"*, which
is 62 characters and arrives cut to *"no axis cleared its gate on this entity's own "*. There is
no marker, so the operator cannot tell a complete short reason from a cut long one, and the row
is one of only three this report prints.

The same file already made this repair elsewhere: `reference.py:437-439` records that slicing
`moth_number` *"cut it mid-figure and printed 'M7.44 ±'"* and replaced the slice with a format.
Order `b0e69b869473` made the identical repair for `feats._show`'s refusal reasons — *"The half
that was cut is the half that explains WHY"*.

**Remedy:** print `reason` whole. The column is the last on the line so nothing else is
disturbed; if a very long reason must be shortened, mark it (`reason[:44] + " …"`) and say where
the whole one is (`data/ASSAYS.json`, keyed `host|entity`).

### N13 — `onomast.main` cuts an attestation mid-value four lines below the marker it added
`src/onomast.py:548`

```python
print(f"     {v['catalogue_name']:<16}{v['register']:<11}{src[:34]}")
```

`src` is `v["attestations"][0]` — a source attribution. Order `89fc2eaf23f1` corrected this same
function's outer `[:4]` for being a silent cut, and the block carries a comment saying so: *"SAY
WHAT WAS CUT, THE WAY THE INNER LOOP ALREADY DOES"*. The inner loop's `rows[:9]` prints
`... and N more`; the outer `_endonyms[:4]` now prints `... and N more`; the field inside each
row still cuts at 34 characters with nothing to show for it, and an attestation is the provenance
of a designation.

**Remedy:** pad rather than cut (`{src:<34}`), or mark it. The line is not width-constrained by
anything.

---

## INFO

### I1 — `reference.py`: three functions take a `name` parameter none of them reads
`src/reference.py:215` (`compute`), `:263` (`citation`), `:299` (`card`)

All three take `name` first and use only `rec` / `res`. Harmless, but it means the call sites
read as though the name is load-bearing when identity actually comes from `rec["styled"]` and
`rec["aka"]`. Remedy: drop the parameter, or use it (a `card()` that never prints the dict key it
was given cannot notice a `REFERENCE` key that disagrees with its own `styled` field).

### I2 — `reference.py` imports `silence` twice
`src/reference.py:50` (module level, used at `:245`) and `src/reference.py:362` (inside `main`).
The inner `import silence` is a no-op. Remedy: delete line 362.

### I3 — `alive_verdict` can answer `(None, "ok")`
`src/feats.py:567-573`. `api()` stamps `outcome = {"ok": True, "why": "ok"}` after a successful
`json.loads`, but the caller tests the *truthiness of the parsed body*: `if api(host, {...},
retries=0, outcome=out)`. A wiki answering `200` with a body that parses to `null`, `{}` or `[]`
gives a stamped `"ok"` and a falsy return, so the verdict computed is
`False if why == "http-404" else None` → `(None, "ok")` — "undetermined, because everything was
fine". The behaviour is safe (undetermined re-probes; nothing is cached), only the reason string
is incoherent. Remedy: test `out.get("ok")` rather than the body's truthiness, or add an
`"empty-body"` reason so the ledger can tell that case from a genuine transport failure.

### I4 — `feats._show` cuts feat and quantity text mid-value
`src/feats.py:1782` (`f['feat'][:120]`) and `src/feats.py:1787` (`q['sentence'][:80]`). The
surrounding comments correctly fixed the *list* truncations — the counts are now declared
("first 6 of N (all of them are in the record)") and the `pages_refused` rows are printed whole
under a comment that says *"AND THE ROWS ARE NOT CUT EITHER"*. That claim is true of the refusal
rows and not of the two lines below them. This is a console preview with a declared count and the
whole text is on the record, so it is the mildest form of the fault; noted for consistency with
`b0e69b869473` rather than as a live risk.

### I5 — `cleanup.py` counts two different exclusions under one heading
`src/cleanup.py:212-227` and `:271`. Wiki-navigation strikes (`_NAV.match`) and empty-mechanic
strikes (`_EMPTY_MECHANIC` with a blank description) both append to `nav`, and the report prints
one number under *"1. wiki navigation removed from the catalogue"*. The second kind is tagged
inline (`nm + "  [empty mechanic]"`) so a reader who sees the row can tell, but only the first
five rows print (see N9), so the count itself conflates two conditions with two different
`excluded` reasons written to the records. Remedy: separate lists and separate lines.

### I6 — module constants and one function with no reader anywhere in the repo
`src/ledger.py:45` (`STANDARD_GLYPH`), `src/ledger.py:71` (`CONDENSATES`),
`src/ledger.py:87` (`currency_status`), `src/tempus.py:128` (`concordance_now`).

Verified with a repo-wide grep including `verify_math.py` and `drill.py`: nothing reads any of
them. Every other public symbol in both files **is** read — `to_standards`, `from_standards`,
`cross_rate`, `work_value`, `assay_to_standards` by `verify_math.py:338-351`;
`DEGENERATE_TIME`, `loop_report`, `contemporaneous`, `is_present_at`, `retrocausality_beta`,
`band_resolution`, `rung_description_length`, `prescience_horizon_bits` by `verify_math.py` and
`rigor.py` and `pipeline.py` — so these four are the exceptions rather than the rule for their
files.

`currency_status` was added by order `e9167885aef6` explicitly *"for a caller that wants to say
WHY"*, and no such caller has arrived. `CONDENSATES` is doctrinal reference data. `tempus.py`'s
own header comment records the removal of exactly this kind of unread pair (`SECONDS_PER_YEAR`,
`C_LIGHT`, run35 batch 6) on the grounds that *"the dead pair is removed rather than
re-declared, since nothing here has ever needed them"*.

**Filed at INFO, and the remedy is a question rather than a change:** confirm with the owner
whether these are intended as reference data awaiting a consumer (in which case no action, and a
one-line note in each saying so would stop the next sweep re-finding them) or leftovers, in
which case `tempus.py`'s own precedent applies. Do not delete doctrinal data on an audit's
judgement.

---

## QUESTIONS — two defensible readings, filed as questions rather than findings

### Q2 — `side_epoch` treats an edge with no provenance as probed-and-undated
`src/chain.py:580-590`

```python
for row in (prov.get(e) or [{}]):
    try:
        ep = ID.epoch_of((row or {}).get("sentence", ""), strict=True)
    except ID.ProbeUnavailable:
        continue
    probed = True
```

When `prov` has no entry for an edge, the loop runs once over `{}` and probes the empty string.
If `ID.epoch_of("")` returns without raising, `probed` becomes `True` and the pair is recorded as
a **genuine disagreement** rather than as `unprobed` — and the docstring is emphatic that those
two must not be confused (*"'nobody asked' is not evidence that the record disagrees with
itself"*).

Along `chain.main`'s path this cannot happen: `extract` appends to `prov[e]` in the same locked
block that increments `edges[e]` (`chain.py:490-492`), so `len(prov[e]) == edges[e]` always, as
the docstring at `:567` states and as I verified. So this is only reachable by a caller that
builds `edges` and `prov` separately. Filed as a question because I could not determine whether
`adjudicate_mutuals` is contractually private to `extract`'s output; if it is, the `or [{}]`
should probably be `or []` with an explicit `probed=False`, which is both more honest and free.

### Q3 — `roll(limit=...)` truncates the job list
`src/feats.py:1622-1623`. `--limit` is an operator flag defaulting to `None`, applied **after**
the by-host interleave, so a limited run gets a spread across wikis rather than an alphabetical
head — which is the good version of this. It is nevertheless an unmarked `jobs[:limit]` in the
file whose own `discover()` raises `SystemExit` on a numeric `extra` under Hard Rule 0. Almost
certainly fine as a deliberate operator knob, noted so a future sweep does not re-find it as a
cap; if the owner wants symmetry with `discover`, the fix is a one-line print
(`"LIMITED RUN: N of M entities"`) rather than removing the flag.

---

## Checked and found sound — recorded so a later sweep does not re-open them

* `feats._api_list_all` (`:799-852`) — the continuation walk is genuinely uncapped;
  `aplimit=500`/`srlimit=50` are per-request maxima and both incomplete-walk cases (repeated
  token, mid-walk API failure) increment `_CAP_BOUND`, including when `rows` is empty
  (order `051244c2628f`).
* `feats.discover`'s `extra` refusal (`:868-871`) — raises on a numeric value; verified no caller
  passes one.
* `feats._units` / `_UNIT_DROPS` (`:305-329`) — the floor/ceiling tallies are counted per gate
  under `_COUNTS_LOCK`, and `roll()` prints them **even when zero** (`:1726-1742`), which is the
  distinction between "nothing dropped" and "nobody counted".
* `feats.main`'s escalation interlock (`:1794-1813`) — fails closed on `ImportError`, with the
  original exception chained via `from _esc_gone`.
* `feats._SRC` control-character guard (`:415-419`) and the equivalents in `chain.py:49-51`,
  `reference.py:58-61`, and `cleanup.py:135-139` — all present, all built from `chr()` codes.
  `cleanup.py`'s roster correctly covers `_MARKUP` and the imported `PL._SETTING_META`.
* `chain.extract`'s `_LAST_EXTRACT` / `unanswered` tally (`:395-517`) — "answered with nothing"
  and "never answered" are kept apart, set unconditionally including the all-clear, printed
  loudly, and persisted.
* `chain.adjudicate_mutuals`'s five outcomes (split / kept / half_dated / self_split / unprobed)
  — each is a distinct condition with its own counter and its own printed sentence; no two are
  folded together.
* `onomast.load_onomasticon` (`:346-377`) — missing vs unreadable are genuinely different
  answers, and `OnomasticonUnreadable` propagates so no write happens over an unread prior.
* `onomast.name_worlds`'s `merged` (`:496-499`) — `retired` is `cid not in resolved`, so a
  standing designation on a shrunken shelf is not flagged withdrawn (order `e5001f0b0153`), and
  the `taken` seeding reads `naming` rather than the flag, so the reservation survives.
* `prose_gate.evidence_ok`'s floor-on-the-floor (`:176-185`) — a floor of 0 or ≤0 or >1 or
  non-numeric refuses everything rather than admitting everything. This one is worth naming: it
  is the only place in the batch where a *misconfigured* safety refuses instead of waving through.
* `prose_gate.section_shortfall` (`:205-263`) — both the ghost term and the extra term now charge
  the denominator, so neither a short block nor an over-long one can reach `frac == 1.0`; the
  2026-08-28 note explaining that a message is not a price is accurate.
* `prose_gate.assert_block_complete`'s `missing[:6]` (`:283-292`) — the truncation is
  **declared**, the total is given, and the message names where the whole list lives. This is the
  correct pattern the four MINOR truncation findings above should be brought to.
* `prose_gate.unearned_instrument` and `cited_names_for` — verified live at `generate.py:424-425`,
  with the answer used to raise `ChapterRefused` and the full list carried into `failures.json`.
  Both fail closed (empty cited set ⇒ every axis score unearned ⇒ refusal).
* `reference.main`'s exit code (`:390-476`) — `return 0 if (landed and calibrated) else 1`, with
  WRITE DENIED and CALIBRATION OUTSIDE kept verbally distinct because their remedies differ.
  `allsweep.py:191` runs this file as `RC_BROKEN`, so the rc has a consumer.
* `reference.shelfmark`'s rung clamp (`:254-257`) — bounded by `len(RUNGS)` and recorded via
  `silence.note` rather than raising an `IndexError` on unfamiliar data.
* `cleanup.py`'s thin-description branch (`:244-252`) — the flag is only an edit the first time,
  and `changed = True` is set (order `2b83e058be3f` plus the run #29 repair); the report is
  appended outside the guard so a re-run still lists every thin entry.
* `cleanup.py:264-266` — `PL.write_record`'s verdict is gated, `unwritten` is reported by name
  with a proper `... and N more`, and `main` returns 1.
* `cleanup._ruby_question_mark` (`:63-96`) — the enclosing-parenthetical test with nesting is
  correct for the `( 女神 ( めがみ ) , Megami ? )` shape and declines on plain English.
* `tempus.band_resolution` vs `rung_description_length` — the split is real and pinned:
  `verify_math.py:484-485` asserts `rigor.measure_bit_value("M5") == band_resolution("M5")/10`,
  and `verify_math.py:767` asserts the two functions disagree. The docstring's *"and /10 per
  decimal point"* aside is honoured by the caller (`rigor.py:150`), not by the return value —
  checked, not a defect.
* `ledger.assay_to_standards`'s M10 ceiling (`:164-168`) — `hi = lo * (lo / prev)` anchored at
  M10's own floor rather than shifted to M9's; `verify_math.py:346-351` pins the monotonicity and
  the caveat string.
* `module_index.py`'s write (`:97-109`) — pid+tid temp name, `replace_retry` verdict checked,
  `return 1` on denial.

---

## Already open elsewhere — deliberately NOT re-filed

* **`onomast.register_for`'s genre/feature voting is dead.** `name_worlds` makes the only call in
  this module, `register_for(v["continuity_group"])` at `onomast.py:460`, with no `genre_register`
  and no `features` — so the `if not genre_register and not features` fallback at `:318-320` is
  the only branch that ever runs, and `FEATURE_SHIFT`, `GENRE_WEIGHT`, `FEATURE_WEIGHT` and the
  whole voting block at `:322-334` are unreachable. The other caller, `navtree.py:199`, uses its
  own local `register_for`, not this one. I verified all of this, then found it is **already
  filed as order `5d8533bc1ed6` and explicitly LEFT FOR OWNER** — `verify_math.py:7144-7148`
  records the reasoning: *"Wiring real genre/feature data into `name_worlds()`'s one call site is
  a cross-module design decision (which of genre.py/grounding.py's classifiers feeds it, where
  per-continuity-group world-feature data would come from), not a mechanical fix, so there is
  nothing yet to pin."* No duplicate order filed. Recorded here only so the next sweep does not
  spend the same hour rediscovering it.

---

## Work orders filed

24 orders, all `found_by="sweep39-batch06"`: **5 MAJOR, 13 MINOR, 6 INFO**.

| id | severity | handler | code |
|---|---|---|---|
| `4f308dbd9d2c` | MAJOR | SESSION | feats-resolve-title-never-called |
| `c2bbe43e0f2d` | MAJOR | SESSION | feats-hosts-unprobed-null |
| `33000660ddac` | MAJOR | SESSION | feats-roll-rc-always-zero |
| `e8466cd6ed14` | MAJOR | SESSION | chain-main-rc-ignores-denied-write |
| `572918512dbc` | MAJOR | SESSION | feats-refusal-marker-false-positives-on-api-path |
| `fa86e8b92150` | MINOR | SESSION | feats-mine-drops-uninteresting-rejections |
| `6d594a775899` | MINOR | OWNER | feats-pages-read-includes-refused |
| `73aacce08418` | MINOR | LOCAL | feats-axis-evidence-dead-duplicate |
| `f27d210d4fea` | MINOR | SESSION | feats-alive-and-page-exists-dead |
| `260a4a2bc0de` | MINOR | LOCAL | chain-stale-line-cross-refs |
| `4bda96cc8338` | MINOR | LOCAL | cleanup-onomast-stale-cross-file-refs |
| `845dbaec182f` | MINOR | OWNER | onomast-coin-exhausted-returns-rejected-name |
| `ed6e66c0c12d` | MINOR | LOCAL | cleanup-ceiling-prefix-ambiguity |
| `d1794144717c` | MINOR | LOCAL | cleanup-report-unmarked-truncations |
| `cefcad5fc513` | MINOR | OWNER | prose-gate-step4-enforcer-unwired |
| `e4ccce54d7dd` | MINOR | LOCAL | module-index-stale-group-rc-zero |
| `4ad714a362ba` | MINOR | LOCAL | reference-compare-reason-truncated |
| `478dea657aaf` | MINOR | LOCAL | onomast-attestation-cut |
| `595673139291` | INFO | LOCAL | reference-unused-name-param-and-dup-import |
| `8350f7a183d1` | INFO | SESSION | feats-alive-verdict-ok-but-undetermined |
| `86b9f6b2f32d` | INFO | LOCAL | feats-show-preview-row-cuts |
| `c3eb0a80bb8a` | INFO | LOCAL | cleanup-nav-count-conflates-two-exclusions |
| `1a9c237dda4d` | INFO | OWNER | ledger-tempus-unread-symbols |
| `423e35500033` | INFO | SESSION | chain-side-epoch-no-provenance |

No module in this batch is on `local_agent.DENYLIST`, so `LOCAL` is permissible for the
mechanical items; it is used only for comment-only edits, unmarked truncations, an unused
parameter, and two well-specified one-line guard changes. Everything requiring judgement about a
persisted schema, a gate, or a naming invariant is `SESSION` or `OWNER`.

---

## Coverage

All nine modules read end to end. Recorded via `sweep_plan.record('run39', [...], batch=6)`.
