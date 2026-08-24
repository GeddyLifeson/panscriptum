# Bug Ledger

*Open bugs by severity (blocking > major > minor > cosmetic). Resolved bugs move to the
bottom with root cause and the export-repo commit that fixed them — a paper trail, never a
deletion. Maintained by the maintenance pass; humans welcome to add.*

## Open

### Major
- **[M1] dandwiki.com is API-blocked (HTTP 403 to every non-browser client)** — 4 homebrew
  sources unhosted; HTML answers a browser UA, so a design decision is needed: build an
  HTML-path reader with a browser UA (politeness/ToS question — HUMAN CALL) or leave the four
  sources owner-supplied. Noted in `data/SCOUT_BLOCKED.json`. Not auto-fixable.
### Minor
- **[m1] Marvel completeness row 25h stale** (0.4% vs 30,207 on disk) — re-measure was
  launched this run (`completeness.py --workers 6`); verify the row after it lands. If still
  wrong after a fresh run, the byslug matching in `completeness.py` becomes a real suspect.
- **[m2] `sources on the roll but never catalogued`: 6** (HAWX, Heaven's Lost Property, Lost
  Mines of Phandelver, Twilight Imperium, +2) and **16 catalogued sources with no host** —
  scout/adopt remedies keep retrying; some (music albums, board games) may be permanently
  hostless and deserve an owner ruling on whether they stay on the roll.
- **[m3] `completeness.py category_size()` masks its own `unreliable` bucket** — a source whose
  every category probe hits `URLError` returns `None` from `work()` and vanishes from
  `COMPLETENESS.json` entirely, instead of landing in the `unreliable` list the module's own
  docstring built specifically for this case. 313 `URLError`s recorded at this site as of run
  #2. Fix: on all-probes-failed, append to `unreliable` rather than returning `None` silently.
- **[m4] `wiki_source.page_text()` gives up after one transient failure on section 0** —
  `except Exception: return ""` instead of `continue`, so a single timeout fetching section 0
  skips sections 1/2 entirely even though they are independent calls. Reproduces the exact
  "transient hiccup read as genuine silence" failure the module's own header essay names as
  its worst historical bug class. Fix: `continue` instead of `return ""`.
- **[m5] duplicate `silence.note()` label `wiki_source.py:278`** used by two unrelated failure
  sites (a local `WIKI_HOSTS.json` read failure vs. a live per-candidate category probe miss) —
  defeats the ledger's own stated purpose of making a failure class legible. Give each site its
  own content label.
- **[m6] `pipeline.py` 9 shared/cross-phase-read JSON writes still non-atomic** —
  `phase_cosmology` (TIERS/GROUNDINGS/CENSUS/SHELFMARKS.json), `phase_history`
  (CHRONICLE.json), `phase_shelve` (SHELVES.json), `phase_weave` (CONTINUITY_GROUPS/
  RESOLVED_ENTITIES/RESONANCE_GRAPH/ONOMASTICON.json), `phase_write` (manifest.json) all use
  raw `open(...,'w')` + `json.dump`, not the `pipeline._landed`/`silence.replace_retry`
  discipline run #2 just extended to `write_record`/`write_record_catalogue`. Several of these
  are read by later phases in the same run, so a crash mid-write leaves the next phase reading
  a truncated file — and `phase_history`'s own `TIERS.json` read failure handler
  (`pipeline.py:1156`) currently mislabels that exact corruption as "phase 5 has not run" and
  marks phase 6 done with an empty result. Medium surgery, 9+ call sites; do in a quiet window.
- **[m7] `handbuilt.py`'s own artifact write is non-atomic** — even after run #2's fix moved
  the write before the crashing report loop, it's still a raw `open+json.dump`, not routed
  through `silence.replace_retry`. No live second writer of `HANDBUILT_ASSAYS.json` today, so
  lower priority than [now-fixed] the ordering bug was.
- **[m8] `build_terminal.py` "Shelved here" note caps at 8 with no "+N more"** — Hard Rule 0,
  display layer: `nd.s.slice(0,8)` in the side-panel note, while the ring SVG and the "sources
  below" count above it are both uncapped. Small, targeted fix.
- **[m9] `build_terminal.py` "contains" row undercounts a node with both branch-children and
  directly-shelved sources** — `nd.k.length||nd.w.length||nd.s.length` short-circuits instead
  of summing; a node with 2 catalogued children AND 5 shelved sources shows "2" not "7".
- **[m10] `build_terminal.py` interpolates catalogue text into `innerHTML` unescaped
  throughout**, and splices `NAVTREE.json` into an inline `<script>` block via plain string
  replace with no `</script>`-sequence guard. A name containing `&`/`<`/`>`/`"` (plausible —
  "Dungeons & Dragons") can corrupt the resulting markup; `render.py`'s `containment_svg()`
  already does this correctly (`html.escape()`) in the same codebase. Multi-site JS-generation
  fix; do as its own pass.
- **[m11] `navtree.py sources_under()`'s `key.startswith(path)` arm has no `.`-boundary
  check** (the sibling arm does) — key `"0.1.20"` can false-match path `"0.1.2"`, pulling an
  unrelated sibling branch's sources into a node's naming-vote register.
- **[m12] `thread_integrity.py`'s asymmetric-thread detection is structurally unreachable** —
  `implied_threads()` builds `pairs` symmetrically by construction, so `classify()`'s `back =
  pairs.get((b,a))` is always truthy and every implied thread reports RECIPROCAL; the
  ASYMMETRIC-LAWFUL/-SUSPECT branches (including the propagation-distance "lawful excuse"
  logic) can never fire. `DANGLING` is a documented output category that is never computed.
  This looks design-shaped rather than a one-line fix — HUMAN CALL: is the module meant to
  compare the weave's implied threads against a separately-recorded directed thread graph it
  currently isn't given? See NEXT_STEPS.
- **[m13] `pipeline.py phase_synthesis`'s 14-entity ceiling-nomination sample can silently
  clamp the whole source to a lesser band** — the sampled 14 (by feat-count then description
  length) may not include the source's true strongest entity; that entity's own later-mined M6
  feat then gets clamped down to whatever lesser ceiling was nominated. UNCERTAIN whether this
  is Hard-Rule-0-shaped; HUMAN CALL requested in NEXT_STEPS.
- **[m14] `pipeline.py phase_entrypass` can mark an entry permanently topicless** — `topic`
  fails its `TOPICS` enum check silently (no fallback, unlike `magnitude`'s explicit
  `"unassayed"`), yet `catalogued=True` is still set, and the `done_keys` resume gate then
  never revisits it.
- **[m15] `endpoint.py fetch_raw` treats every HTTPError as "page doesn't exist"** — 403/429/500
  are indistinguishable from a genuine 404 at this layer; a rate-limit or transient block during
  raw fetching would be misfiled as permanent absence. `endpoint.py register()` also mutates
  `SOURCE_PAGES.json` without the lock `ENDPOINTS.json` uses elsewhere in the same file — no
  concurrent caller observed, flagged UNCERTAIN.
- **[m16] `weave.py`'s per-pair `shared_sample` field is capped (8, then re-sliced to 6)** —
  diagnostic evidence for why the weave linked two shelves, not a reader-facing catalogue
  listing, but Hard Rule 0's text says "no sample" without carving out diagnostics explicitly.
  HUMAN CALL requested in NEXT_STEPS rather than assumed out of scope.
- **[m17] `weave_index.py designations()` caches forever with no invalidation** — unlike its
  sibling `load_records()`, which is signature-keyed by (file count, max mtime). Low exposure
  today (the one caller never varies the `records` arg), but the same stale-cache shape that
  bit `chain_harvest_idx` and `weave_index.load_records` before their own fixes.

## Watching (not bugs — expected states with a clock on them)
- Charter regression first run dispatched autonomously 21:31 (`magnitude.py --calibrate`,
  foreman AUTO). Verify `data/CHARTER_REGRESSION.json` lands and the standard flips.
- Dragonlords ingest miner: patient loop (60-miss ≈ 5h), waiting out the evening pool for the
  midnight free-tier window. Cursor at chunk 1/252 after the writer fix.
- Deferred assay backlog (heavyweights, Jace accessions, Infinity Gauntlet) self-requeues
  when the pool window rolls.

## Resolved (paper trail)

*Run #2 (2026-08-23 late, export commit pending as of this write). Root causes one line each —
full detail in HANDOFF.md's run #2 entry:*

- **`cascade_bridge._bury()` raised `UnboundLocalError` on every call, never benching a
  provider** — a dead `if _DEAD is None: _DEAD = {}` guard made `_DEAD` local-by-assignment for
  the whole function; removed, mutate the module-level dict directly.
- **Phase-1/phase-2 band gates laundered a fabricated Assay decimal into a clean band**
  (`re.match(...)\b` matches a `.`) — replaced with `pipeline.clean_band()` (full-match) at
  acceptance, `pipeline.ceiling_band()` (still lenient) at the clamp.
- **`write_record`/`write_record_catalogue` marked a unit done even when the write was denied**
  — both now return whether the rename landed (`pipeline._landed`); both call sites gate on it.
- **`handbuilt.py` crashed on its own `moth_number`'s Fraktur A before ever writing its
  artifact** (cp1252 console) — write now happens before the report loop; console reconfigures
  to UTF-8 after.
- **`rigor.bradley_terry()`'s `undefeated`/`winless` always empty once a prior was set** — the
  symmetric prior was folded into `W` before those two lists were read from it; now computed
  from a pre-prior copy.
- **`rigor.mathematical_resonance()`'s returned `load_bearing` field capped at 8** (Hard Rule 0)
  — uncapped; console print still slices for display only.
- **`render.children_of()`'s child-tier gate asserted a schema (`SF.TIERS`) instead of reading
  the actual tree** — changed to `child_tier is None`; the existing per-entry check does the
  honest work. (No behavior change today — SEVENFOLD.json doesn't chart past `universe` yet —
  but the old form would have silently stayed empty once it does.)
- **stale `silence.note()` label** `derivation.py:490` said `:488` — renamed to a content label.
- **disk pressure (BUGS M2)** — resolved itself between runs (~5 GB -> 135 GB free); no fix
  needed, moving straight to paper trail.

*Run #1 (2026-08-23, commits fc390a9…b16f631). Root causes one line each:*

- **ingest_doc used `write_record` (disk-wins merge) and its first 14 finds were discarded** —
  wrong side of the two-writer contract; → `write_record_catalogue`, cursor reset, both merge
  directions pinned by verify_math §18c (b16f631).
- **`os.replace` PermissionError killed an assay worker mid-batch** — Windows denies rename
  while a reader holds the target; → `silence.replace_retry` shared helper on every
  reader-raced state file (fc390a9).
- **standards' floors self-check blind to a dead floor** — substring match defeated by a
  comment mention and a prefix collision (`MAX_UNANSWERED[_RECORDS]`); → word-bounded,
  comment-stripped matcher; dead floor deleted (fc390a9).
- **Catalogue tools wrote records raw** (truncating, non-atomic, racing the pipeline) — →
  routed through the new catalogue-side merge writer (fc390a9).
- **feats/read evidence caches: truncated file = permanent silent entity loss** — unguarded
  json.load of a cache killed mid-write; → atomic writes + self-healing reads (fc390a9).
- **`_WIDEN_RR` rotation cursor raced by worker threads** — re-pinned the pool to one bucket;
  → locked (fc390a9).
- **`foreman._retire` truncating write on overwatch's ledger** — → atomic (fc390a9).
- **`restart_reader` never restarted anything** (both branches returned without acting) and
  **both foreman process-killers filtered `python.exe` only** (jobs run under pythonw) — →
  reader bounce implemented; filters widened (fc390a9).
- **standings jobs stayed down for hours after a mid-cycle death** — the cycle only re-asserts
  at its top, then blocks in run/join; → keeper thread re-asserts every 5 min (d4745fa).
- **`silence.py --instrument` resurrected the 5,672-row probe-noise ledger class** — the
  rewriter can't distinguish deliberate silence; → `silence-exempt` string markers honoured by
  both audit and instrumenter (fc390a9).
- **Epoch-mandate bypass through the split retry** (morning); **split-gate accepted fabricated
  wrappers**; **entry bands could exceed their source's ceiling** (Starkiller Base M5 in M4)
  — all gated/clamped; reconcile check added (earlier commits, same day).
- **~146 PowerShell spawns per standards.check** (dashboard polls it at 5s) — one shared
  enumeration, 3s TTL, invalidated on launch; check now 2.3s (d4745fa).
- **chain.harvest re-parsed 56k files/900MB per cycle** — incremental mtime index; 3.1s warm
  (fc390a9). **weave_index.load_records re-parsed 63MB per dashboard poll** — signature cache
  (fc390a9). **13MB sweep parsed twice per batch** — once (fc390a9).
