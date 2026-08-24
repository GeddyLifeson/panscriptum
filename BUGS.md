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
- **[m16] `weave.py`'s per-pair `shared_sample` field is capped (8, then re-sliced to 6)** —
  diagnostic evidence for why the weave linked two shelves, not a reader-facing catalogue
  listing, but Hard Rule 0's text says "no sample" without carving out diagnostics explicitly.
  HUMAN CALL requested in NEXT_STEPS rather than assumed out of scope.
*Everything still open above is a HUMAN CALL (M1, m12, m13, m16) or an operational state being
watched (m1, m2). As of run #4 there are no open bugs awaiting only implementation.*

## Watching (not bugs — expected states with a clock on them)
- **`MAX_JOB_SILENCE_MIN = 15` is a live threshold as of run #3** — the stall detector could not
  previously reach it (see the Resolved entry). During run #3 a healthy `roll_auto.log` sat
  unchanged for 4.5 minutes; a page roll waiting on a slow host could plausibly cross 15 and
  trigger the AUTO kill remedy. Watch for false alarms; raise the constant if they appear.
- **Local model throughput is the live constraint.** Not a 503 any more (that was the run-#3b
  wedge, resolved) — the runner is up and measurably pegged at ~8 cores, but a 30B MoE at 8.5 GB
  on a 10 GB card means heavy CPU offload, and a phase-2 batch can sit for a long time. Run #4
  watched `units_done` hold at 3382 across a 40s sample with the state file freshly written:
  blocked inside one call, not broken. If phase 2 makes no measurable progress over a few hours,
  the question is model choice / offload split, not correctness.
- **`entries stranded in closed batches: 5`** — the reopen gate is **proven** (run #4: the batch
  appears in `failed.entrypass` while its key is still in `done.entrypass`, which the old gate
  made impossible). The count clears when a phase-2 model call finally lands on that batch.
  Do NOT re-fix the gate on the strength of this number.
- Charter regression: `data/CHARTER_REGRESSION.json` **landed** (22:24, run #3 confirmed it on
  disk). Verify the `automation reproduces the charter` standard now takes a real reading.
- Dragonlords ingest miner: patient loop (60-miss ≈ 5h), waiting out the evening pool for the
  midnight free-tier window. Cursor at chunk 1/252 after the writer fix.
- Deferred assay backlog (heavyweights, Jace accessions, Infinity Gauntlet) self-requeues
  when the pool window rolls.

## Resolved (paper trail)

*Run #4 (2026-08-24 00:45). Full detail in HANDOFF.md's run #4 entry:*

- **The stranded-batch fix is PROVEN IN PRODUCTION** — live state holds
  `failed.entrypass["Arcanum Worlds (Odyssey of the Dragonlords)#280"]` while that same key is
  still in `done.entrypass`. Phase 2 attempted a batch whose key was already recorded done,
  which the old gate made impossible. `--preflight` still reads 5 only because no phase-2 model
  call has landed since (the pipeline is blocked inside one slow call, not broken).
- **[m6] eleven phase artifacts made atomic** via the new `pipeline.land_json()` — the old
  `json.dump(obj, open(path,"w"))` truncates before serialising, so an unencodable value left
  the real file unparseable (reproduced). **And the second half**: `phase_history` treated absent
  and corrupt identically, reported both as "phase 5 has not run", and marked phase 6 **done with
  an empty result** so the corruption was never revisited. Absent and corrupt are now separate,
  corrupt leaves the phase open. Same fix in `phase_shelve`, which would otherwise have shelved
  the whole library tierless and marked itself done. verify_math §19c pins the write contract.
- **[m10] build_terminal escaping** — new JS `esc()` applied to every catalogue-derived
  interpolation (headings, endonym, roster, 4 SVG titles, `data-k`, 7 SVG text renders), and the
  `NAVTREE.json` splice now neutralises `<` as `<`, killing `</script>` / `<script` / `<!--`.
  Live-verified: 734 nodes still parse, and a name carrying `<img onerror=…>` renders as literal
  text with 0 injected nodes.
- **[m14] topicless entries** — a `topic` failing its enum check left no key while
  `catalogued=True` blocked revisiting, silently dropping the entry from `worldseed` and `weave`
  forever. Now an explicit `"unclassified"` sentinel plus `topic_rejected`, matching the
  `magnitude`/`scale_note` idiom. **Prophylactic: 0 of 55,653 catalogued entries are currently
  affected.**
- **[m15] `endpoint.fetch_raw` filed refusals as absences** — 403/429/500 were indistinguishable
  from 404 to the caller. Signature unchanged; the ledger now splits `fetch_raw-absent` from
  `fetch_raw-refused-<code>`, where the counts are what tell a block from a missing page.
- **[m20] dead loop deleted** with owner sign-off. Its comment is kept — the decision it records
  (counting instances belongs to the reconcile tier) is still true.
- **[m7] was already fixed; the entry was stale.** `handbuilt.py` writes through
  `tmp` + `silence.replace_retry` with a landed check.
- **NEW: `the local model has a live runner` standard added** (high, machine, OWNER lane) —
  `/api/ps` naming a resident model with no `llama-server.exe` process is a flat contradiction
  and was the exact shape of run #3b's 31-minute invisible outage. Fires on a simulated wedge,
  silent when it cannot tell, TTL-cached at 120s. No REMEDIES entry by design: restarting a
  service is not automation this pass will switch on unasked.

*Run #3b (2026-08-24 00:00, continuation pass). Full detail in HANDOFF.md's run #3b entry:*

- **Ollama was hard down and self-sustainingly wedged** — queue saturated (`maximum pending
  requests exceeded`) while `/api/ps` reported a resident model with **no `llama-server.exe`
  runner process in existence**, so nothing drained the queue and every call, including each
  attempt to load a model, failed instantly. The phase runner logged 59 unbroken 503s in 31
  minutes doing zero work. Fixed by restarting the daemon; a real runner now holds 8.5 GB VRAM
  and the 503 loop stopped dead. **This corrects run #3's diagnosis of "GPU contention"** — a
  wedge, not contention, and it would never have cleared by waiting.
- **[m18] `foreman.py`'s three shared-state writes** (`POOL_PROOF.json`, `FOREMAN.json`,
  `failures_archive.json` + the `failures.json` reset) now use `tmp` + `silence.replace_retry`,
  the pattern `_retire()` in the same file already used. Readers confirmed live in all three
  cases; the `failures.json` reset was the one that could lose a concurrent `health.flush()`.
- **[m19] `standards.report()` sorted work orders alphabetically** (`high < low < medium`, so
  every MEDIUM printed below every LOW). Now uses the rank dict `work_orders()` already defines.
  Verified live: HIGH, HIGH, MEDIUM×5, LOW, LOW.
- **[m21] `kill_duplicate_jobs` was registered as a bare lambda**, so it logged itself as
  `<lambda>` in the operational log. Unwrapped.
- **[m22] `catalog.py`'s docstring advertised a `PANSCRIPTUM://…` address form the code has
  never implemented.** Replaced with real `SpineCode/Chapter[#PageRange]` examples, both verified
  to answer.

*Run #3 (2026-08-23 23:06, export commit `cc42d0c`). Root causes one line each — full detail in
HANDOFF.md's run #3 entry:*

- **Doc-ingested entries stranded permanently by the entrypass resume gate** — the resume key
  `source#start` names a span `entries[start:start+B]` that GROWS when `ingest_doc` appends
  through `write_record_catalogue`, so the tail batch widened under a key already in
  `done_keys` (Arcanum Worlds: 292 → 297 entries, 5 never judged). Gate now reads the span, not
  the ledger (`pipeline.batch_settled`); verify_math §18d pins it.
- **`ingest_doc.mine()` advanced its resume cursor on a denied write** — `write_record_catalogue`'s
  landed-flag was discarded, so entities never written were skipped forever and `known` had
  already absorbed their names. Denied write now rewinds `known` and stops without advancing;
  state file also made atomic.
- **[m3] `completeness.py` dropped any source whose every category probe failed** — `work()`
  returned `None`, deleting the row from `COMPLETENESS.json`, where absence reads as "no wiki
  presence". New `category_size_probe()` returns `(n, error)`; all-probes-failed lands in
  `unreliable`. `category_size()` unchanged for other callers.
- **[m4] `wiki_source.page_text()` abandoned a page after one transient failure** — `return ""`
  instead of `continue` on a section-0 exception skipped the independent sections 1 and 2. High
  volume: 1,700–3,200 URLErrors per foreman round at this site.
- **[m5] duplicate `silence.note()` label `wiki_source.py:278`** across two unrelated sites —
  split into content labels; `:301` likewise.
- **[m8] Hard Rule 0: "Shelved here" roster sliced to 8** (node 6.6.6 hid 30 of 38) — uncapped,
  bounded by scroll rather than by a "+N more" that would still leave 30 names unreachable.
- **[m9] "contains" row undercounted** — `a||b||c` returns the first non-zero, so 6.6.6 showed
  7 instead of 45; 37 nodes affected. Now sums. m8/m9 live-verified in the browser.
- **[m11] `navtree.sources_under()` false-matched on a digit prefix** — `key.startswith(path)`
  lacked the `.` boundary its sibling arm has; `0.1.2` counted as above `0.1.20`.
- **[m17] `weave_index.designations()` cached forever** — now keyed on the same directory
  signature as `load_records()` (shared `_records_sig()`); explicitly-passed record lists are
  no longer cached at all, having no signature to key on.
- **`address.spine_code_for()` shelved two sources into DC Comics** — the index's two-letter
  `"DC"` matched raw letters with spaces stripped (`swor-d-c-oast`), so `Sword Coast
  Adventurer's Guide` and `Who Framed Roger Rabbit (…)` both returned II.D.2, and matching
  *wrong* kept them out of the unassigned report that would have caught it. Containment now
  runs on whole words, with letter-equality kept as its own tier for spacing variants
  (`Soulcalibur`/`Soul Calibur`). No volumes were mis-shelved; nothing to regenerate.
- **`manifest_builder.load_record()` missed truncated record slugs** — tested only `target in
  filename`, so a 304-entry catalogued record reported as "no matching record file". Reverse
  arm is prefix-anchored, candidates ranked by closeness.
- **`foreman._checks_pass` kept patches that broke a round number of checks** — `"0 FAILED" not
  in stdout` is satisfied by `"10 FAILED"`, `"20 FAILED"`, `"100 FAILED"`. Now parses the count
  numerically and fails closed on an unreadable result line.
- **`standards.py`'s stall detector could never fire, for any job** — the watch stamp was
  re-written every pass, so "how long silent" measured checker cadence; and jobs were derived
  from log filenames (`read_auto.py` has never existed), hiding the three live jobs while
  matching stale legacy logs as alive. Stamp now carried forward (`standards.job_stamp`); jobs
  taken from the new `lognames.OWNER` map, which `foreman.kill_stalled_job` also now uses.
  verify_math §19b pins both. **Its AUTO remedy is destructive and was previously inert — see
  the flagged item at the top of HANDOFF.md run #3.**

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
