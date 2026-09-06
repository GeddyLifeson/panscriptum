# sweep45 — batch 05

READ-AND-REPORT ONLY. No source file was edited. The DRILL_BREACH halt was left standing and no
battery tool (`drill.py`, `verify_math.py`, `allsweep.py`, `publish.py`, `mutate.py`) was run.

## Coverage

All eight assigned modules read **in full, every line, no sampling** (5,394 lines total).

| module | lines | read |
| --- | ---: | --- |
| `src/standards.py` | 2,247 | all |
| `src/generate.py` | 820 | all |
| `src/secondopinion.py` | 642 | all |
| `src/policy.py` | 517 | all |
| `src/catalogue_codex.py` | 404 | all |
| `src/deprecated/catalogue_local.py` | 333 | all |
| `src/scope.py` | 275 | all |
| `src/repass_bands.py` | 156 | all |

Supporting files read as evidence, not as coverage: `src/feats.py:424-545` (`api`) and
`:989-1015` (`fetch`), `src/context_budget.py` (whole), `config.yaml` (model/window keys).

Recorded via `sweep_plan.record('sweep45', [...], batch=5)` — the deprecated module is stamped
under its directory-qualified name `deprecated/catalogue_local.py`.

## Findings filed — worst first

### 6e2dab4c3981 · MAJOR · LOCAL — `scope.py`: an API failure is cached as an honest empty verdict

`scope_for()` reads its four MediaWiki searches as `(d or {}).get("query", {}).get("search", [])`.
`feats.api()` **does not raise** — it returns `None` for a throttled host, any non-404 HTTP status,
a non-JSON 200 (a WAF or login-wall interstitial), a network fault, and "no usable API here". All
of those yield `titles == []` and `return None`, which is the same value as the genuine
"read it, nothing cleared `MIN_MENTIONS`" answer. `build()` then writes
`out[h] = sc or {"scope": None, "ceiling": None, "probe_version": PROBE_VERSION}` and its `todo`
filter skips any host already stamped at the current version — so the host is never probed again.

This is precisely what the exception handler twelve lines above was written to prevent
(*"A FAILURE IS NOT A VERDICT, AND IT MUST NOT BE CACHED AS ONE"*), arriving by the path that does
not raise. `feats.api()`'s own docstring names this confusion as the reason its `outcome=` channel
exists (order `64e4db060ad6`); `scope.py` passes it at none of its call sites.

Measured on disk 2026-09-05: `data/SCOPE.json` holds 155 hosts, 146 dict records **all at
`probe_version` 0** plus 9 bare nulls — so every host is in the next build's `todo`, and the next
`scope.py --build` is the run that stamps them. This machine's fandom reachability is documented as
intermittently dead for hours (`standards.py:300-357`). Same shape as the already-open
`481ef92af785`, one generation of bad rows later.

### f4f3c1d15915 · MAJOR · LOCAL — `catalogue_codex.py`: 88 elements dropped by a name-only dedupe

`main()`'s per-section loop keys `seen` on `norm(name)` alone. The manifest's element identity is
the pair `(type, name)` — the parsed line is literally `Dragonmark (12): Mark of Detection; …` — so
two different element types sharing a name collapse and the second is dropped with no count, no
name and no report.

Measured by running `catalogue_codex.parse_codex()` against the live codex, 2026-09-05:
**64 sections, 4,489 manifest elements, 88 dropped, 28 of them in sections that bind to a current
`SWEEP_ROLL` row** (Eberron 12, Player's Handbook 4, Ravnica 3, Unearthed Arcana 3, six more at 1).

The drops are not duplicates — they land in *different* catalogue categories:

| kept | dropped |
| --- | --- |
| Race `Troglodyte` → Factions | Language `Troglodyte` → Powers |
| Race Variant `Mark of Detection` → Factions | Dragonmark `Mark of Detection` → Powers |
| Companion `Mastiff` → Persons | Item `Mastiff` → Things |
| Class `Arcanist` | Archetype `Arcanist` |
| Item `Armor: AC +1` | Item `Armor: AC -1` |

The last row is a second failure of the same key: `norm()` strips `+`/`-`, so two genuinely
different items collapse to `armorac1`.

The record is written under attestation **Transcribed** with a provenance sentence saying the names
come from the section's Full Contents manifest. 2% of them do not, and nothing says so. This module
reports the other two `norm()` collision classes *uncapped and before the write report* — section
titles (`5da00dda2c8e`) and register descriptions (`096f6efc33d2`, whose docstring calls the
identical silent-drop shape unacceptable at 974 items). This is the third instance in one file and
the only one still silent — and the one that drops catalogue entries rather than descriptions.

### 491269a0f908 · MINOR · LOCAL — `policy.py`: the evidence sweep's unreadable files reach neither the report nor the exit code

The block comment at `:359-363` says *"Every failure, every vacuous pass and every unreadable file
is named in full, here and in the report."* The scope dict carries only
`"evidence_unreadable": len(ev_unreadable)` — an integer. The names and parse errors exist only in
the stdout loop and die with the process. That is the defect `c19d9ebcac14` was filed for on the
*record* sweep, whose fix (`records_unreadable_detail`) sits eight lines above; the evidence half
never got it, because `c19d9ebcac14` cited the evidence sweep's bare count as the model to copy.

Matching gap in the exit code: `:509-510` returns 1 on unreadable *records* under the comment
*"A RECORD THAT COULD NOT BE READ IS NOT A PASS, AND THE EXIT CODE HAS TO SAY SO"*.
`ev_unreadable` is consulted by nothing — a run in which every one of ~255,000 `data/feats` files
failed to parse prints its lines and returns **0**.

Two unmarked cuts survive in the same block, both already repaired in the record loop beside it:
`:385 str(exc)[:70]` and `:447 subj[:40]`. These are the surviving half of `fe99e57e1993`'s
"policy.py:323,369" entry — one of the two named sites is fixed, one is not.

### 61d2d34d580a · MINOR · LOCAL — `secondopinion.py`: an unaskable tool is reported as NOT INSTALLED

`_exe()` swallows every failure of its `[cand, "--version"]` probe with a bare
`except Exception: silence.note(...)` and returns `None` both when the executable is genuinely
absent and when the probe could not complete (`TimeoutExpired` at 30 s, `PermissionError`, an AV
hook). The runners then return the literal `"NOT INSTALLED"`, `report()` prints *"install before
treating this page as a second opinion"*, and `file_orders()` files a remedy of
`python -m pip install <tool>`.

The module's docstring preserves absence as a third answer distinct from clean, then collapses it
against *unaskable*. Same class of mis-diagnosis it already fixed for vulture's exit codes
(*"a guard on an exit code has to know what the exit codes MEAN"*). Not hypothetical here:
`standards.py:1981-1993` argues a subprocess timeout on this machine is *"an ORDINARY event, not an
exotic one"*, and `_exe` spawns up to nine of them per run; `CLAUDE.md` records Norton blocking
executables outright, which is exactly the case that reads as NOT INSTALLED today.

### e2728130fef3 · MINOR · LOCAL — `secondopinion.py`: three unmarked `[:200]` cuts on the tool-error text

`_ruff`, `_vulture` and `_detect_secrets` each build
`"TOOL ERROR (… rc=%d): %s" % (rc, (r.stderr or r.stdout or "?").strip()[:200])` — no ellipsis, no
`+N chars`. ruff and detect-secrets both write multi-line usage errors to stderr, which is the very
behaviour order `12694407d245` added these branches for.

`_message()` in the same file fixes this exact class 150 lines above, and its stated reason applies
verbatim: `file_orders()` puts the status string straight into a `SECONDOPINION_ABSENT_*` order
body, and `workorders.file_order` keeps `what` uncapped *because a remedy is written at the end*.
The cut happens upstream of that guarantee. Remedy is one line per site: route through
`_message(s, width=200)`.

### 43f43c0d8e60 · INFO · LOCAL — `policy.py`: only `is_type` validates its `arg` at load

`check_rule`'s own comment says an unevaluable rule is refused at load *"like an unknown op; a false
verdict is never issued for one."* Only `is_type` gets that. Measured by calling `check_rule`
directly against `{"n": 5, "s": "abc"}` with each op and no `arg` key:

```
gte / lte / len_gte  -> ok=False, TypeError: '>=' not supported between int and NoneType
in_range             -> ok=False, TypeError: 'NoneType' object is not subscriptable
matches/not_matches  -> ok=False, TypeError: first argument must be string or compiled pattern
glob                 -> ok=False, TypeError: expected str, bytes or PathLike, not NoneType
is_type              -> BadRule refused at load   (correct)
```

Each of the seven lands in `failed`, prints a FAIL line naming the **document**, and drives rc=1 —
a typo in a rule table reads as a corrupt corpus. No live impact: all three tables pass a correct
arg today. Filed for the reason the `TYPES` comment gives for its own fix — *"a landmine for the
next table"*.

### 3859043e365e · INFO · OWNER — `generate.py`: the output reserve assumes a non-thinking model

**Question, not a defect claim, and explicitly not a refile of `342ccfafa4a4`** (which is about
think tags reaching disk and the model-id/comment mismatch). This is a different consequence:
`call_ollama` gates every generation on `context_budget.assert_fits`, which passes only when
`system + user + reserve <= num_ctx`, with `reserve` = 2048 (chapter) / 1024 (feats), described as
*"Room the model needs to WRITE its answer, inside the same window as the prompt."*

`config.yaml` names `qwen3:8b` at `num_ctx: 12288`. That is a reasoning model, and this repo has its
own measurement of the fact (`standards.py:266-274`: *"its first tokens land in `thinking`, and
`response` stays empty until the reasoning closes"*). Reasoning tokens are spent from the same
window, and no term in `measure()` accounts for them, so a block sized to exactly clear its reserve
has its visible answer squeezed by however much the model thinks first.

Likely presents as an elevated refusal rate rather than silent loss (`prose_gate` and `_covered`
would catch a badly cut block), which is the safe direction. Gate is closed today
(`prose_enabled: false`). One measured generation splitting `eval_count` between `thinking` and
`response` would settle it; the fix is either a `THINKING_RESERVE_TOKENS` term or sending
`think: false`, and both are owner calls.

## Already open — corroborated, not refiled

* **`de43fe54feb7`** — `scope.ceiling_for()` still has **zero callers**. Re-verified across all 116
  modules including subdirectories: `grep -rn "ceiling_for" --include=*.py .` returns only its own
  `def` line in `src/scope.py`.
* **`fe99e57e1993`** — of the two `policy.py` sites named, `str(e)[:70]` in the record loop is
  **fixed**; `str(exc)[:70]` in the evidence sweep (`:385`) is not, and `subj[:40]` at `:447` is a
  third site in the same file. `repass_bands.py`'s `sn[:70]` cuts at `:52`, `:66`, `:68` are all
  still present as listed; `:126`/`:137` are now the uncapped `str(n):<32` **padding**, so those two
  entries look resolved.
* **`df76f922f635`** — both halves appear **repaired in source**: `nonempty` is now
  `hasattr(v, "__len__") and len(v) > 0` and the dead `ok = False` is gone (the removal is recorded
  in a comment at `:160-161`). The order is still open with `status: None`.
* **`c19d9ebcac14`** — the exit-code half is **fixed** (`policy.py:509-510` returns 1 on unreadable
  records); the durable-report half is fixed for records and never existed for evidence files
  (filed above as 491269a0f908).
* **`85cdecef25f8`** / **`ef8940b363b3`** — `TYPE_CATEGORY`'s `THINGS` default and the
  non-most-specific substring fallback both still stand as described.
* **`4398d76f822f`** — `repass_bands.py:76` still does `e["scale_note"] = ""` with no
  `scale_note_rejected` sibling. Confirmed as the only other site in `src/` that empties the field.
* **`4ed4041c3b78`** — the falsy-zero `if args.limit:` is present at `generate.py:589` as listed. A
  **fourth** instance exists at `deprecated/catalogue_local.py:277`, but it is behind the module's
  refusal and therefore dead; not worth adding.
* **`342ccfafa4a4`** — not refiled. See 3859043e365e above for the separate arithmetic question.

## `src/deprecated/catalogue_local.py` — the quarantine is intact and reachable

Read in full. The refusal at `:91-94` is **module-level, unconditional, and above everything**: the
only code preceding it is stdlib imports, so importing the module stops as hard as running it,
before `sys.path` is touched, before `yaml` is imported, before any config is read or any path is
built. `--help` prints `_REFUSAL` and exits 0 (the documented exemption that keeps
`allsweep.check_import` from filing a MAJOR against a module behaving as intended); **every other
argv, including none at all, exits non-zero with the refusal text.**

Verified there is no in-process importer that could trip the `--help` exemption inside another
program: `grep -rn "import catalogue_local\|from catalogue_local"` over all `.py` files returns only
comments and string literals in `drill.py`, `liveness.py`, `sweep_plan.py` and `workorders.py`.
**Nothing here is proposed for removal.**

Nothing was filed against this module. Beyond the six defects its own header deliberately leaves
unrepaired, three more are visible and all are equally dead behind the refusal:

* `catalogue_source()`'s `seen` set spans **all seven categories**, so an entity that legitimately
  belongs to two is dropped from the second — the same shape as the live `catalogue_codex` finding
  above, except that here it is deliberate and documented (system-prompt rule 9, near-duplicate
  collapse). Worth recording because it shows the codex module inherited the shape without
  inheriting the reasoning.
* `call()` does `json.loads(json.loads(...).get("response", "{}"))`, which on the currently
  configured reasoning model would parse `""` and raise into the handler that files
  `per_cat[key] = 0`.
* `str(e)[:70]` at `:229` and the falsy-zero `if args.limit:` at `:277`.

## Deliberate design, examined and not filed

* **`standards.py:1037-1041`** — `"probe failures (reported, not judged)"` is `_s(..., True, ...)`,
  a standard hard-wired to hold. It cannot fail, but it is labelled as such in its own name, its
  floor is the string `"no floor"`, and the block above it argues the case at length (counting
  probe failures as faults kept a standard permanently red for doing its job). It does inflate
  `report()`'s "N/N standards met" denominator by one guaranteed pass; that is a reporting nit, not
  a check that cannot fail masquerading as one that can.
* **`standards.py:1345-1347`** — `"the library's counters are moving"` holds by construction when
  the history is under 40 minutes. Documented, and the `observed` field says
  `"not enough history yet (Nm of 40)"` rather than a verdict. Correct as written.
* **`standards.py:1199-1200`** — shelfmark collisions are counted as
  `len(addrs) - len(set(addrs))` over `v.get("address")`, so rows missing an `address` would all
  read as `None` and collide with each other on a HIGH standard. Checked `data/SHELFMARKS.json`:
  1,016 rows, **0 with a missing address, 0 collisions**. Latent only; not filed.
* **`generate.py:253`** — `_covered()` returns `True` for an empty name. Combined with
  `job["entries"]` always carrying names in practice, this never fires; the loose match is argued
  for in the docstring.
* **`scope.py:99-101`** — a `continue` key in the search response (MediaWiki withholding results
  past `srlimit=500`) is noted to the silence ledger but not carried into the SCOPE.json record, so
  a verdict built on a withheld corpus is indistinguishable on disk from a complete one. The module
  states this choice explicitly (*"worth knowing rather than pretending away, so it goes into the
  ledger"*), so it is a stated trade rather than a silent cut. Recorded here rather than filed.
* **`secondopinion.py:377-378`** — `run()`'s `except Exception` keeps only `type(e).__name__` and
  takes no `silence.note`, but the result *is* recorded: it becomes the tool's `status`, which
  `missing()`, `report()` and `file_orders()` all read. Not a silent drop.
* **`generate.py:596-601`** — the `--dry-run` `pending[:3]` cut is marked (`"showed 3 of N"`).
* **`catalogue_codex.py:94-104`** — `slug()`'s docstring claim of zero callers **re-verified**
  across all 116 modules: only its own `def` plus three comment mentions. Kept deliberately as a
  public helper; `record_path()` is the live entry point.
