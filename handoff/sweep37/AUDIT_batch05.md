# SWEEP 37 — BATCH 05 AUDIT

Modules read IN FULL, every line (4,010 lines total):

| module | lines |
|---|---|
| `src/cascade_bridge.py` | 1,622 |
| `src/build_terminal.py` | 593 |
| `src/identity.py` | 489 |
| `src/tiers.py` | 367 |
| `src/pantheon.py` | 318 |
| `src/burgs.py` | 272 |
| `src/profile.py` | 222 |
| `src/catalog.py` | 127 |

No source file was edited. No live model call was made; `prove()` was not run. Every finding
below was demonstrated offline, against the real data files or against stubs.

---

## MAJOR

### M05-1 — `catalog.py:64` truncates the operator's work queue to its alphabetical head
`cmd_stats` prints `for n in missing[:30]` and then `... and {len(missing)-30} more`.

Measured, live, this run:

```
Populated sources with NO books yet (209):
  - 2112 (Rush)
  ...
  - Curious DM Investigations (the Sharkin)
  ... and 179 more
```

**209 populated sources have no books; 30 are shown; 179 are hidden.** First hidden entry is
`Curse of Strahd`. This is the exact pathology HARD RULE 0 names by example — "`cap=250` took
the alphabetical head of every missing-cast repair" — and `catalog.py stats` is the interface
CLAUDE.md's own "When you're done with a batch" section tells an operator to report from. The
count is disclosed, so it is not a *silent* truncation; but there is no flag anywhere in the
module that shows the rest, so the roster is unreachable, not merely folded.

Confidence: **certain** (reproduced by running the documented command).

### M05-2 — `burgs.py:205-209` keys the whole artifact on a field that is not unique, then claims completeness
`main()` builds `per_world[w["designation"]] = bs` over `WS.build_all()`.

Measured offline:

```
worlds:                        5,940
distinct designations:         5,893
designations appearing >once:     44
worlds silently overwritten:      47
```

Collisions are real and ordinary — `Adventurers League::Phlan` appears three times,
`Adventure Time::Ice Kingdom`, `all Battlefield::Russia`, `all Pixar films::Pizza Planet`
twice each. The `--write` branch then prints:

> `wrote data/BURGS_SAMPLE.json (5,893 worlds — every one, Hard Rule 0; the SAMPLE in the
> filename is historical)`

That line asserts completeness over a dict that lost 47 worlds, and the number it quotes is
`len(per_world)` — the post-loss count — so the message cannot contradict itself no matter how
many worlds are dropped. This is the same family as the drifted "sample of 50 worlds" message
the branch already carries a long comment about: the count was made honest about the dict, and
the dict is the thing that is wrong.

Secondary consequence: the class histogram divides a numerator taken from `per_world.values()`
by a denominator (`total`) accumulated over all 5,940 worlds, so the printed settlement-class
percentages cannot sum to 100%.

Confidence: **certain** (counted from `worldseed.build_all()`).

### M05-3 — `burgs.py` main() materialises ~91 million burg records and cannot run on this machine
`main()` builds every burg of every world into memory unconditionally — before `--write` is
even consulted.

Measured (one real world built, the rest extrapolated from it):

```
burg_count summed over all 5,940 worlds : 90,972,641
largest single world                    : 193,089  (Predator::Transept)
80.8M of the 91M come from `spacefaring` worlds (base P_1 = 3,000,000)

measured: one 130,603-burg world -> 2.15 s, 45.6 MB of Python heap
extrapolated: ~1,496 s (24.9 min) and ~31.7 GB of heap
              --write would then serialise ~16 GB of JSON
```

`python src/burgs.py` with no flags therefore exhausts memory on a machine that does not have
32 GB free for one dict. And line 212 prints

> `storage       : 0 bytes — every one is derived from its world's seed`

immediately before the branch that would write 16 GB of exactly those derived burgs. The
docstring is right that the module is an *estimator* — "Running the map generator 1,521 times
to count hamlets is not a plan" — and `navtree.py:56` already consumes only `burg_count`, the
scalar. It is `main()` that insists on the full roll.

This is not a Hard Rule 0 conflict: nothing downstream reads a burg roster, and `burg_count`
(the number actually published, as the terminal's "burgs (est.)") is already uncapped. The
fault is that the module's own entry point demands a materialisation nothing needs.

Confidence: **certain** for the counts and the single-world measurement; **high** for the
extrapolation.

### M05-4 — `cascade_bridge._CLIENT_REJECTION` contains a live provider's NAME, so that provider can never be classified dead

```python
_CLIENT_REJECTION = re.compile(r"error code:\s*10\d\d|cloudflare|browser integrity|"
                               r"just a moment|attention required")
```

`cloudflare` is a bare alternative, and `cloudflare` is also the name of a configured provider.
Both `permanent_refusal()` and `dead_forever()` open by returning/skipping on a
`_CLIENT_REJECTION` hit, so any Cloudflare error text that names its own provider is dismissed
as a WAF rejection whatever status code it carries.

Demonstrated:

```
'HTTP 401 Authentication error'                       permanent_refusal=True
'Cloudflare Workers AI: HTTP 401 Authentication error' permanent_refusal=False
'HTTP 402 payment required (Cloudflare account)'       permanent_refusal=False

dead_forever() over two proof rows carrying the identical 401:
   groq:free        -> EXCLUDED
   cloudflare:free  -> NOT EXCLUDED
```

Scanned every configured provider name against every classifier vocabulary in the module;
`cloudflare` is the only collision (`_DEAD_WORDS`, `_LOCAL_TRANSPORT`, `_PERMANENT_WORDS`,
`_TRANSIENT_WORDS` are all clean).

This is the file's own warning, unclosed on the receiving side. The comment above `box` in
`_ask_call` says exactly this — *"`_CLIENT_REJECTION` looks for 'cloudflare', which appears in
the label of every Cloudflare model whatever went wrong. Feeding a labelled string to a
classifier makes the label decide the verdict."* — and the fix applied there was to split
`failovers` (labels) from `reasons` (dispositions). But the guard itself was never narrowed,
and two paths still deliver provider-naming text to it: `_ask_call`'s `_why = raw` keeps the
engine's `All 1 candidates failed: <label>` wrapper when no failover reason exists, and
`provider_error()` returns the provider's own `bucket_state.last_error`, which a provider is
free to open with its own name.

Corroboration that this has already cost something: `OWNER_EXCLUDED` had to strike
`cloudflare:free` off **by hand** with the note `"HTTP 401 -- credential dead, needs rotation"`,
and the comment above that dict says in terms that `dead_forever()` "cannot help either". One
of the four buckets the owner had to exclude manually is the one bucket the classifier is
structurally blind to.

Confidence: **certain** for the behaviour; **high** that it is load-bearing.

### M05-5 — the `prove()` / `dead_forever` repair is correct in source and NOT IN EFFECT
The rewritten `dead_forever()` is right. Verified offline against a synthetic proof file,
12 cases, 0 mismatches — 401/402/404 excluded; a throttle, an engine wrapper, a curl transport
line, a Cloudflare-1010 WAF page, an empty reason, `no API key`, a healthy row, `curl exited
401`, and a digit-adjacent `req_4401abc` all correctly **not** excluded. The mtime-keyed cache
was confirmed to re-read after a re-proof.

But the live artifact says the fix is not running:

```
data/POOL_PROOF.json   written Fri Aug 28 22:56:38 2026 (0.7 h old)
36 rows.  verdicts: {'provider disabled': 10, 'no answer': 21, 'answers': 1, 'local': 4}
rows carrying a `reason` key:  0
rows carrying a `served` key:  0
```

Sample row: `{'bucket': 'cloudflare:free', 'model': 'cf-qwen-coder', 'verdict': 'no answer',
'seconds': 0.2}`. The post-fix `prove()` writes `reason` and `served` on **every** non-local
branch, so a file this new with neither key was written by a process still holding the
pre-fix module. `foreman.py:160` is the caller.

Consequence: `dead_forever()` returns the empty set in production right now, exactly as it did
before the repair, and an empty set is indistinguishable from "no bucket is permanently dead."

This is CLAUDE.md's fourth property — *"a safety that exists in a file is not a safety that is
running ... a Python process does not re-read its own source"* — and the question it raises is
whether `codewatch`'s rc=17 fingerprint is reaching the foreman that writes this file. I did
not start, stop or inspect any running process, per instruction.

Confidence: **certain** for the artifact's state; **high** for the inference about the writer.

---

## MINOR

### M05-6 — `prove()`'s served-bucket cross-check cannot fire when the served model is unresolvable
```python
by = str(served.get("bucket") or "")
if verdict == "answers" and by and by != bucket:
```
`served["bucket"]` is `_bucket_of(box["answered_id"] or box["answered"])`, and `_bucket_of`
returns `""` for anything not matching a `Model.id` or `Model.label` (verified:
`_bucket_of("an-unknown-model-id") == ""`). When that happens `by` is falsy, the guard is
skipped, the verdict stays `answers`, **and** the row's `served` field is written as `""`.

So the belt-and-braces check and the audit trail that would let anyone reconstruct it go blank
together, in the same condition. The docstring's promise — "WHO ACTUALLY SERVED IT, recorded
whether or not it matched. A proof that cannot name its own subject cannot be audited by
anyone later" — is not kept in exactly the case where it matters. `max_attempts=1` is the
primary guard and is present, so the exposure is small; but this is the fail-open direction of
a check whose whole job is to catch the engine's contract changing underneath it, which is
precisely when `_bucket_of` is most likely to stop resolving.

Confidence: **certain** for the structure; the frequency depends on the engine's `model` event.

### M05-7 — `try_disabled()` still measures a neighbour (confirming an already-filed order)
Confirmed by inspection: `prove()` passes `max_attempts=1`, `try_disabled()` does not. It pins
`m.id`, the engine walks the rest of the pool behind the pin, and a neighbour's success is
written down as `verdict: "ANSWERS"` for the disabled model — the identical defect
`prove()` was repaired for today. Reported for confirmation only; already filed.

Separately: `try_disabled` mutates `m.enabled` on the **shared** `_ROUTER` model objects while
other threads may be routing through them. `finally: m.enabled = was` restores it, but the
window is a live cloud call wide.

### M05-8 — `build_terminal.py`: three catalogue-derived sinks bypass `esc()`, against the module's own stated discipline
The template's own comment reads *"Every catalogue-derived string goes through this before it
reaches innerHTML."* Scanned all 157 `${...}` interpolations in the template. Three
catalogue-derived, non-numeric ones are unescaped:

* `shelfmark()` (line 471 builds from `nd.name` with no `esc`) reaches `innerHTML` at
  **line 490** (`panel`), **line 506** (`selectSource`) and **line 527** (`selectWorld`).
  Latent: no node name in the live `data/NAVTREE.json` carries `& < > " '` (checked all 734).
* **line 540**: `<b>${cat}</b>` — while **line 525** escapes the very same value as
  `<h2>${esc(cat)}</h2>`. **Live**: three worlds carry `&` in `cat` — `Baskets & Boots`,
  `DunBroch Castle & Kingdom`, `Cortex Power & Gas Co.` No world name carries `<` or `>`
  today, so nothing renders wrong yet; the exposure is the next name that does.

Everything else is safe on inspection: `f.landform/climate/condition/tech` come from closed
vocabularies (verified against NAVTREE: 6/6/3/4 values), `w.s` is always an `int`, `u` is
built from an int and a fixed template key, and the `.roster` list and `selectSource` both
escape correctly.

This is BUGS m10's fault class surviving in the rooms the m10 pass did not sweep.

### M05-9 — `pantheon.py:308` — `--full` truncates the evidence for every score
`print(... d["cited"][:58])`. **54 of the 66 axis citations are cut**; the longest (Vados,
`acumen`) is 294 characters. This is the view whose flag is named `--full`, and the cited
sentence is the whole warrant for the score beside it.

Same shape as `tiers.deliberate_joins`, which returned `shared.get((a,b), [])[:3]` and was
brought in line in run #27 on the owner's 2026-08-24 ruling — its docstring's argument applies
verbatim here: *"A cap on the evidence for a claim is not a display convenience."*
`data/PANTHEON.json` holds the full text, so nothing is lost on disk.

Also `pantheon.py:293`: `epoch[:40]` in the ranked table.

### M05-10 — `identity.py` — two line-number citations, both drifted, one of them now false
* **line 364**: *"`chain.py:422` is the caller that should pass it, and that is filed as a
  cross-module change in `handoff/run36/crossmodule_batch04.md` rather than edited here."*
  **That change has landed.** `chain.py:446` calls `ID.epoch_of(sa, strict=True)` and
  `chain.py:447` catches `ID.ProbeUnavailable`. The docstring describes a live gap that no
  longer exists and points a reader at a handoff file for work already done. `chain.py:422` is
  now the middle of an unrelated docstring.
* **line 387**: *"`epoch_of()` above it is still live -- `chain.py:381` calls it directly."*
  `chain.py:381` is `local.append(((ID.node(...` — `ID.node`, not `epoch_of`. The conclusion
  survives (446 does call it); the evidence cited does not.

The idiom here is to cite by symbol, and both of these show why.

---

## LOW / INFORMATIONAL

* **`pantheon.py:288-290`** — the band-label table covers M1–M8. The charter's ladder
  (`assay.LADDER`) is M0–M10, so **M0, M9 and M10 have no label**. The `.get` fallback prints
  `(no label on file for M9)`, so it degrades honestly rather than blank — the comment's own
  requirement is met. Nothing in `Z_FIGHTERS.json` (bands M2/M3/M4/M7) or `GODS` (M7/M8)
  reaches them today.
* **`tiers.py:248`** — `silence.note("tiers.py:248")` is the only line-number-keyed note tag
  in all eight modules; every other one cites a symbol (`pantheon.py:merge`,
  `identity.py:_titles`, `cascade_bridge.py:dead_forever`, …). It is accurate *today*; it
  drifts on the next edit above it.
* **`tiers.py:323-333`** — `bad` increments once per SOURCE (there is a `break` inside the
  source loop) but is printed as `containment violations (a lower group split across two
  higher ones)`, a GROUP count. Demonstrated with a synthetic: one group-level violation
  involving two sources reports as `2`.
* **`build_terminal.py:581-588`** — a denied `replace_retry` leaves
  `output/registry_terminal.html.<pid>.<tid>.tmp` on disk; there is no cleanup branch. (None
  are present now.) `silence.write_json` cannot be used here because the payload is HTML, so
  the hand-rolled temp is justified; only the cleanup is missing.
* **`profile.py:109`** — `decode`'s address group is `([0-9a-z]+)`, which accepts `i l o u`;
  `B32` excludes exactly those four. `decode("PS-iou-hfc-0000-u0")` passes the regex and then
  raises `ValueError: substring not found` from `B32.index`, instead of the module's own
  `not a world profile: ...`. Both are `ValueError`, so a caller catching it is unharmed; the
  message is the loss. The run #33 repair (removing `u`, bringing the alphabet to 32) is
  otherwise correct — the encoder's `& 31` mask and the decoder now agree exactly.
* **`identity.py:216`** — `return n >= 2 and shared >= max(2, 0.5 * n)` is reachable only at
  `n == 2`, because `n >= MIN_BEARERS` (3) returns True above it and `n == 1` is handled
  separately. At `n == 2`, `max(2, 1.0)` is always 2, so the branch is exactly
  `n == 2 and shared == 2`. The `0.5 * n` scaling is dead and the docstring calls it "the
  general majority test below". Harmless today; it becomes live only if `MIN_BEARERS` rises.
* **`cascade_bridge.py:1463`** — `for lab in ready[:12]` in `selftest()`. The full count is
  printed on the line above, so the cap is disclosed, and `selftest` is `__main__`-only.
* **`identity.py:479-480`** — `top[:6]` with `+{N} more` in the summary listing; `--host`
  prints the host's full list, so nothing is unreachable.
* **`catalog.py:127`** — `main()` is called bare rather than `sys.exit(main())`, so
  `catalog.py read <unknown address>` prints "No entry" and exits **0**.
* **`burgs.py:136`** and **`profile.py:141`** — both carry a `limit=` parameter. Checked every
  caller: only `verify_math.py` passes either (`burgs_for(..., limit=3/200)`,
  `PR.build_all(limit=400)`). Neither is a production cap. **Not** a Hard Rule 0 finding.

---

## VERIFIED HEALTHY

Recorded so the next sweep does not re-litigate them.

* **`dead_forever()`** — the rewrite is correct in both directions. 12 synthetic cases,
  0 mismatches. It excludes on 401/402/404/410 in either `verdict` or `reason`, and correctly
  refuses to exclude on: a throttle, an engine wrapper (`All 1 candidates failed: …`), a curl
  `Could not resolve host`, a Cloudflare 1010 WAF page, an empty reason, `no API key`,
  `answers`, `curl exited 401` (local-transport wins), and `req_4401abc` (word boundary
  refuses a digit-adjacent 401). The mtime-keyed memo re-reads after a re-proof — verified by
  rewriting the file and bumping its mtime.
* **The predicate family is mutually consistent** on twelve measured provider strings.
  `permanent_refusal` catches HTTP 401, `Insufficient balance or no resource package`,
  `depleted your monthly included credits`, `limited to 1000 API calls / month`;
  `named_transient` catches the Groq `try again in 6m51.264s`; `pool_exhausted` fires on
  `All 7 candidates failed` and correctly refuses `All 1`; `empty_content` is a whole-string
  match; and the Cohere trap works — `limited to 40 API calls / minute` matches nothing
  permanent while the `/ month` form does.
* **`prove()` carries `max_attempts=1`.** The isolation repair is present in source.
* **The write verdicts are gated and the messages are accurate.** `tiers.main()` (`wrote` /
  `WRITE DENIED`), `pantheon.main()` (`-> OUT` / `WRITE DENIED`), `build_terminal.main()`
  (atomic temp + `replace_retry`, both branches honest), `burgs.main() --write` (gated **and**
  returns rc=1 on denial, to stderr), `identity.load()` (gated, and additionally warns on
  stderr that other readers still hold the previous inventory — the best of the five, because
  it names the consequence rather than the event), `cascade_bridge.record_unrecognised` and
  `_metric` (both gated to distinctly-named `silence.note` tags).
* **`identity.continuities()`'s host-key normalisation is right.** `host.replace(".","_")
  .replace("-","_")` matches the on-disk shape in both `data/DESIGNATORS.json` and
  `data/feats/` (`adventuretime_fandom_com`). The `or inv.get(host)` fallback is belt-and-
  braces, not a bug.
* **`identity.epoch_of`'s unprobed/unmarked split is real.** A parsed `{"epoch":"",
  "explicit":false}` is a non-empty dict and takes the `not d.get("explicit")` path; only a
  `None` from `_ask` or an unparseable reply reaches the `ProbeUnavailable` arm. Verified by
  reading both arms; `chain.py:446-447` consumes it correctly.
* **`tiers.deliberate_joins`** returns the whole `shared` list, uncapped. The run #27 fix
  holds.
* **`build_terminal`'s `.roster`** is uncapped and bounded by scroll, per its own comment; the
  `data.replace("<", "\\u003c")` guard against `</script>` splicing is correct and lossless
  (inside a JSON string `<` parses back to `<`).
* **`_bury`'s missing-guard note is accurate** — there is no assignment to `_DEAD` anywhere in
  that function's scope today, so the `UnboundLocalError` trap is genuinely disarmed.
* **`record_unrecognised` folds its dedup key and stores `text` verbatim**, which is the right
  way round; the m132/case-splitting fault cannot recur.
* **`profile.py`'s round-trip check in `main()` can now fail.** It re-encodes what `decode`
  extracted rather than comparing `d["profile"]` with itself, so genre, register, features,
  band and attestation are actually exercised. (Caveat, not a fault: an unknown genre encodes
  to `un` and round-trips cleanly, so the check cannot detect a genre outside `GENRE_CODE` —
  that is a property of the format, not of the test.)
* **`pantheon.value()` cannot raise on today's data** — all 15 `Z_FIGHTERS.json` rows carry an
  `assay.magnitude` in `assay.LADDER` (M7×5, M4×1, M3×8, M2×1).
* **`cascade_bridge` widen-fallback rotation** is correct: the round-robin offset is taken
  under `_RR_LOCK`, and the re-`sort` after rotation is stable, so proof-winners stay ahead
  while consecutive calls still spread across the alive set.

---

## ORDERS FILED (sweep37-batch05)

| id | severity | code |
|---|---|---|
| 6434c1ba7b20 | MAJOR | catalog-stats-caps-the-missing-books-roster |
| 65ae84ee4bd7 | MAJOR | burgs-per-world-dict-drops-47-worlds-then-claims-every-one |
| 47e4e1ace8f1 | MAJOR | burgs-main-materialises-91-million-burgs-and-cannot-run |
| 62f4b7caae73 | MAJOR | client-rejection-regex-contains-a-live-provider-name-cloudflare |
| 1661efdee019 | MAJOR | pool-proof-fix-is-correct-in-source-and-not-in-effect |
| fdebedb8d0ce | MINOR | prove-served-bucket-crosscheck-goes-blank-with-its-own-audit-trail |
| 3b37494e20db | MINOR | build-terminal-three-catalogue-strings-bypass-esc |
| 9d24c8a5febf | MINOR | pantheon-full-view-truncates-the-evidence-for-every-score |
| 328c1dd39f3d | MINOR | identity-two-drifted-line-citations-one-now-false |

Coverage recorded: `sweep_plan.record('run37', [...8 modules...], batch=5)` — all eight now
stamped `run37`.

Not re-filed (already open): `try_disabled()`'s missing `max_attempts=1`, confirmed still
present by inspection.
