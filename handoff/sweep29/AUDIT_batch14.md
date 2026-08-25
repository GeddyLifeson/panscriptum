# AUDIT — BATCH 14 (run29)

Modules: `wiki_source.py`, `chain.py`, `silence.py`, `worldseed.py`, `render.py`, `chord_field.py`, `catalog.py`

Method note: every module was read in full. Reproductions were driven with
`PYTHONIOENCODING=utf-8 C:/Users/imarl/miniconda3/python.exe` against small driver scripts in the
scratchpad dir; none of them touched anything under `src/`, and the one live-data experiment
(corrupting `data/WIKI_HOSTS.json` to prove a crash) copied the original aside first and restored
it byte-for-byte afterward — verified with a fresh `json.load` at the end of the session.

---

## silence.py — the anti-silence module (audited hardest, per the special charge)

### FINDING S1 — `uses_exc` in `_handlers()` is a tautology: it can never be False (CRITICAL)
**File:line:** `src/silence.py:133`
```python
uses_exc = bool(node.name) and node.name in body
```
`body` is `ast.dump(node)` — the AST dump of the **entire** `ExceptHandler` node. When a handler
binds a name (`except Exception as e:`), that name is itself a field of the `ExceptHandler` node
(`name='e'`), so it is *always* present in `ast.dump(node)`'s own output, independent of whether
the name is ever referenced anywhere in the handler's body. The check is therefore checking
whether the string "e" appears in a string that is guaranteed to contain "e" (it also appears
inside the word "Exception" itself). The intended check — "does the body of the handler actually
*use* the bound exception, e.g. to log or re-raise it" — is never performed.

**Consequence:** every `except X as name: <do nothing useful>` handler in the codebase — the
single most common shape a silent swallow takes in Python — is misclassified as "observed" and
excluded from the SILENT count `audit()` reports, and from what `instrument()` will insert a
`note()` call into. `grep -c "except .* as [a-zA-Z_]*:" src/*.py` finds **91** such handlers across
`src/`; every one of them is invisible to this detector regardless of what its body actually does.

**REPRODUCED.** Driver:
```python
except Exception as e:
    return None   # classic silent swallow
```
`silence._handlers()` on this returns `{'silent': False}`, and a direct check confirms
`node.name in ast.dump(node)` is `True` purely because the dump text contains `name='e'` (and
independently because "Exception" contains the letter "e").

### FINDING S2 — the `records` check in `_handlers()`/`instrument()` matches incidental text, not calls (HIGH)
**File:line:** `src/silence.py:128-129` (audit) and `:386-388` (instrument) — same shape twice
```python
records = any(t in body for t in ("health", "record", "log", "print", "raise", "swallow", "silence", "LEDGER"))
```
`body` is again the whole `ast.dump(node)` text. This matches the trigger words against *any*
substring anywhere in the handler — a local variable name (`logbook = "..."`), a string literal,
an attribute name, anything — not specifically a call to `health.record`/`print`/`silence.note`/etc.

**Consequence:** a genuinely silent handler that happens to contain an identifier or string
containing one of those eight substrings is misreported as "observed," further inflating the
undercount from S1 independently.

**REPRODUCED.** Driver: a handler whose entire body is
```python
except Exception:
    logbook = "nothing happened"   # a variable name, not a log call
    return None
```
is reported `silent: False`, purely because the identifier `logbook` contains "log". A control
case (`raisin = 1`, which does not contain the literal substring "raise") is correctly reported
`silent: True`, confirming the mechanism is exactly this naive substring match and not some other
cause.

**Combined effect of S1+S2:** running `silence.audit()` against the live tree reports **433 total
handlers, 50 silent**. Given that 91 handlers alone bind an exception name (all structurally
immune to detection per S1, whether or not they log anything), the true silent count is almost
certainly higher than 50 — this audit tool, whose whole purpose is to make the "swallowed
failure" defect visible project-wide, is itself under-reporting the defect it exists to catch.
This is exactly the shape the module's own docstring warns about ("a silent null costs a full
investigation... the honest-looking answer is the one that gets believed") — turned inward on the
tool itself.

### FINDING S3 — `note()` and `swallow.__exit__` are *totally* silent on their own failure, with no fallback trace (HIGH, intentional-but-risky)
**File:line:** `src/silence.py:99-112` (`swallow.__exit__`) and `:290-322` (`note()`)
Both wrap their call into `health.record(...)` in a bare `except Exception: pass`, with an explicit
comment that this is deliberate ("the recorder itself must never be the thing that breaks a run").
That reasoning is sound for *not raising*, but the current code goes further than that: there is
no fallback observation of any kind (not even a `print(..., file=sys.stderr)`), so if `health.py`
ever fails to do its job — a bug in `health.record`, `health.py` failing to import, a lock
mis-state — **both** the original failure being reported **and** the fact that the recorder itself
broke vanish completely, forever, with zero trace anywhere on disk or in any stream.

**REPRODUCED.** Driver: monkeypatch `sys.modules["health"]` to a stub whose `record()` raises
`RuntimeError`, trigger a real `ZeroDivisionError`, call `silence.note("test-site")`. Result:
`note()` returns normally, and the process produces **no output of any kind** — no stderr line, no
exception, nothing — despite two distinct failures having occurred (the original divide-by-zero,
which was supposed to be logged, and the health-recording call itself, which broke).

Since `health.py` is a single, non-redundant point of failure for the *entire* project's failure
ledger (every module funnels through `silence.note`/`swallow` → `health.record`), a bug introduced
into `health.py` at any point in the future would silently disable failure-recording across all
~30+ modules in `src/`, and there would be no signal anywhere that this had happened — the project
would simply appear to have stopped having failures. Recommend at minimum a best-effort
`print(..., file=sys.stderr)` inside the `except Exception: pass` blocks (itself wrapped so it
cannot raise) so a human watching the console has *some* breadcrumb even when the ledger itself is
broken.

### FINDING S4 — `_handlers()` silently drops any file it cannot parse, with zero indication (MEDIUM)
**File:line:** `src/silence.py:117-122`
```python
try:
    with open(path, encoding="utf-8") as f:
        src = f.read()
    tree = ast.parse(src)
except Exception:
    return []
```
A file that fails to open or parse (syntax error, bad encoding, or — ironically — a file caught
mid-write by another process, the exact hazard `write_json`/`replace_retry` exist to prevent
elsewhere) contributes `[]` to `audit()`'s `rows`, which is **indistinguishable from a file that
genuinely contains zero `except` blocks**. `audit()`'s printed total and "SILENT" count give no
indication that a whole file was skipped rather than clean.

**REPRODUCED.** Driver: a temp `.py` file with a deliberate syntax error but a real
`except Exception: pass` inside it. `silence._handlers()` on it returns `[]` — the genuinely silent
handler it contains is invisible, and nothing anywhere records that the file could not be audited.

**Consequence:** currently all files under `src/` parse cleanly (verified: `audit()` returns 433
non-empty rows total across the tree, so nothing is silently dropped today), so live impact is
zero right now — but this is a structural blind spot in the one tool responsible for catching
exactly this class of defect, and it would fail exactly the way it is designed to prevent: quietly.

### Not re-derived (already known, confirmed still present)
None of `silence.py`'s own known issues were pointed at me for this module; the four findings
above (S1–S4) are new.

### Other silence.py review notes (no bug found)
- `write_json`/`replace_retry`: atomic write with PID+thread-qualified temp name, bounded retry on
  `PermissionError` specifically (Windows rename-while-open), records-but-never-raises on persistent
  denial. Read closely for a race between two writers of the *same* temp name — none found; the
  temp name is unique per (path, pid, thread), matching the m100 fix the comments describe.
- `append_line`: single `os.write` to an `O_APPEND` fd, correctly reasoned as atomic for a
  sub-page write; best-effort, records failure via `note()`. No issue found.
- `instrument()`/`_ensure_import()`: manual, developer-invoked tooling (writes `.presilence`
  backups before mutating). Re-parses its own rewritten source before committing and bails with a
  message if the rewrite doesn't parse. No correctness issue found, though it inherits the S1/S2
  detection blind spots (an already-silent handler that happens to bind a name or contain a
  matching substring will not be selected for instrumentation either).

---

## wiki_source.py

### FINDING W1 — `resolve_wiki` catches only `OSError` around a `json.load()`, and crashes uncaught on a malformed/torn `WIKI_HOSTS.json` (HIGH)
**File:line:** `src/wiki_source.py:275-284`
```python
try:
    with open(_hosts_path, encoding="utf-8") as f:
        known = json.load(f).get(source_name)
except OSError:
    silence.note("wiki_source-hosts-read")
    known = None
```
`json.JSONDecodeError` (a `ValueError` subclass) is **not** an `OSError` and is not caught here.
The surrounding comment explains this is deliberate for a *different* reason (avoiding masking a
`NameError` from a previous bug in this same block), but the practical effect is that this
function no longer tolerates a malformed hosts file at all — only a *missing* one. `data/
WIKI_HOSTS.json` is a genuinely shared, concurrently-written file: `hostcheck.py`'s own comments
say it is "written from THREE call sites in two modules," and `feats.py`, `completeness.py`,
`ingest_doc.py` and others all read it independently. A reader that catches one of those writers
mid-update (or any other source of corruption) does not degrade to the guess-based fallback this
function's own docstring promises ("A missing hosts file is tolerable") — it crashes the whole
`resolve_wiki()` call, which in turn aborts wiki resolution for whatever source was being
processed (and, depending on the caller, potentially the whole cataloguing run).

**REPRODUCED.** Driver: backed up `data/WIKI_HOSTS.json`, overwrote it with a truncated/malformed
JSON string (`'{"Marvel": "marvel.fandom.co'`), called `wiki_source.resolve_wiki("Marvel")`.
Result:
```
resolve_wiki CRASHED with: JSONDecodeError Unterminated string starting at: line 1 column 12 (char 11)
```
Original file restored and verified to re-parse cleanly afterward — no lasting change to
`data/WIKI_HOSTS.json`.

**Fix direction (not applied — proposal only):** widen the `except` to also catch
`json.JSONDecodeError`/`ValueError` and `AttributeError` (the latter guards `.get(source_name)`
raising if the parsed JSON is not a dict — e.g. a torn write that happens to leave valid-but-wrong
JSON, such as a bare `[`-terminated array).

### Known issue confirmed present, not re-derived
`category_members` (`:549-573`) breaks its `cmcontinue` walk on any exception and returns
whatever partial roster it has so far, with no signal to the caller distinguishing a complete
category walk from a partial one cut short by a transient API failure. Confirmed still present as
described in the task brief; not re-analyzed further here per instructions.

### Nearby observation (related to the known issue above, same shape)
**File:line:** `src/wiki_source.py:456-484` (`page_text`) and `:487-514` (`page_texts`)
`page_text()` tries sections 0/1/2, and — per its own inline comment — was specifically fixed to
`continue` rather than `return ""` on a per-section failure so a transient timeout on section 0
doesn't hide sections 1/2. That fix is real and correct. But if **all three** sections fail (e.g.
persistent timeout for a specific page during a network hiccup), the function still returns `""`
— the same string a page that genuinely has no qualifying prose would also produce. `page_texts()`
then simply omits that title from its output dict (`if text: out[title] = text`), with only a
`silence.note()` call (three of them, one per failed section) as the trace. This means a page that
failed to fetch three times in a row is **filed as "no evidence for this entity"** exactly like a
real content-free page, and the entity silently gets no prose from this pull. This is
VERIFIED-BY-READING (not independently reproduced — would require simulating a real network
failure), and is the same "failure wearing the shape of a real negative" pattern the project's own
`silence.py` docstring calls out as the recurring defect (its Marvel/233-entries example is
structurally identical). Worth the supervisor's attention alongside the known `category_members`
issue since both live in the same file and share a cause: no way, from outside, to tell "genuinely
no evidence" from "the network failed and we gave up."

### Reviewed, no issue found
- `_get`/`_api`: retry/backoff on HTTPError 429/503 and generic exceptions; final attempt re-raises
  (not silent). Rate limiting via `_rate_lock` correctly serializes only the *gap enforcement*, not
  the request itself — matches the documented "overlap the network wait" design.
- `all_categories`: `hard_stop` defaults to `None` (no cap) as the docstring claims; only cached
  when the walk completed (`complete=True`) and `hard_stop is None`, so a partial/failed walk is
  correctly never memoized as the truth. Matches its own extensive docstring exactly.
- `find_categories`, `discover_categories`: `limit=None` by default, no truncation; ranked, not
  capped, matching Hard Rule 0.
- `clean_titles`: drops subpages/disambiguation pages by name pattern — a legitimate dedup filter,
  not a truncation of the entity universe.
- `rank_by_size`: ranks by article byte-length, `top=None` default (no truncation unless a caller
  explicitly asks for one, which is the documented intended use for "rank, never truncate").

---

## chain.py

### FINDING C1 — `write_result` truncates the persisted `unmatched` diagnostic to the top 40 names, discarding the rest and the total (LOW-MEDIUM, DATA truncation)
**File:line:** `src/chain.py:108-109`
```python
"unmatched": (unmatched.most_common(40) if hasattr(unmatched, "most_common")
              else (unmatched or [])),
```
This is written into `data/CHAIN.json`, a persisted data artifact, not merely printed to the
console (`main()` separately prints only the top 8 for display, which is fine). The written field
keeps only the 40 most frequent unmatched name-strings and drops both the remaining distinct names
and the total occurrence count of everything past the 40th — so nothing later reading `CHAIN.json`
can recover how many distinct names failed to match the entity index, or the true total. This is a
smaller-but-real instance of the pattern Hard Rule 0 names: a cap on an output artifact that looks
complete but silently isn't. Its blast radius is limited (this is diagnostic data about
unmatched names, not the entity roster or the edge list itself, both of which are written in
full), so I've scored it LOW-MEDIUM rather than flagging it at the severity of a roster cap.
VERIFIED-BY-READING.

### Reviewed, no issue found
- `harvest()`: incremental mtime-keyed cache is correctly invalidated per-file on content change,
  correctly drops entries for files that vanished (`live` vs `idx` diff), and correctly never
  caches a file it failed to parse (the `continue` on JSON-load failure leaves that `rel` absent
  from `idx`, so it's retried next run rather than being permanently treated as empty). The dedup
  key documented as fixed at m37 (`(entity, full sentence)` rather than a 120-char prefix) is
  exactly as described.
- `extract()`/`work()`: the outcome-to-sentence attribution bug described in the file's own
  extensive comment (using the model's own `index` field rather than positional inference) is
  fixed as claimed — `pos = int(o.get("index", 0)) - 1` is bounds-checked
  (`if not (0 <= pos < len(chunk)): continue`) before indexing `chunk[pos]`.
- `adjudicate_mutuals`: re-keys mutual (A beats B / B beats A) pairs onto epoch-specific nodes only
  when both sides date differently; leaves genuinely undated or equally-dated pairs standing as a
  real disagreement rather than inventing a resolution. Traced through the `out.pop((x,y))` calls
  for potential KeyError on overlapping mutual pairs sharing a node — did not find a case where the
  same `(x,y)` key could be popped twice, since `mutual` is built from unique `edges` keys and each
  mutual pair's two directions are disjoint tuples.
- `entity_index`/`_partials`: ambiguous short-form names (`clash`) are correctly excluded from the
  partial-name index rather than resolved to an arbitrary one of the colliding entities.
- No writer to `data/CHAIN.json` or the harvest index other than `write_result`/`harvest()`'s own
  `silence.write_json` calls — matches the two-writer contract's intent (shared state via
  `silence.write_json`/`replace_retry`), no bare `open(path, "w")` on shared data found in this
  file.

### Out-of-scope cross-module note (not part of this batch, flagged for awareness only)
`chain.py:182`'s call to `ID.identify(page, host, inv=_inv)` inside `harvest()`'s per-feat loop is
**not** wrapped in a try/except, unlike the JSON-load two lines above it. `identity.identify()`
itself is defensively written (pure string logic; did not find a path that raises for the current
call shape), so this is a HYPOTHESIS only, not a reproduced or even fully verified bug — but if
`host` is ever a non-string (e.g. a JSON file whose `"host"` field is a number, since
`d.get("host") or os.path.basename(...)` only falls back when the field is falsy, not when it's
the wrong type), `identity.continuities()`'s `host.replace(".", "_")` would raise `AttributeError`
uncaught, aborting the *entire* harvest for all remaining files rather than skipping just the one
bad row. `identity.py` is not in this batch, so this is reported for the record rather than
audited further.

---

## worldseed.py

### FINDING WS1 — `main()`'s `--write` path writes `data/WORLDSEEDS.json` with a bare `open(path, "w")` + `json.dump`, not `silence.write_json` (MEDIUM-HIGH, two-writer-contract / concurrency)
**File:line:** `src/worldseed.py:317-321`
```python
if args.write:
    path = os.path.join(HERE, "data", "WORLDSEEDS.json")
    with open(path, "w", encoding="utf-8") as f:
        json.dump({w["designation"]: {"address": address(w), **w} for w in worlds},
                  f, indent=2, ensure_ascii=False)
    print(f"\nwrote {path}")
```
This is precisely the anti-pattern `silence.write_json`'s own docstring describes fixing at twelve
other call sites project-wide ("a bare `open(path, 'w')` + `json.dump`... not a write but a
TRUNCATE-THEN-FILL. A reader arriving in the gap sees an empty or half-written file; a crash in the
gap leaves it that way permanently"). `WORLDSEEDS.json` is not a private scratch file — it is read
by at least `pipeline.py` and `address_space.py` elsewhere in the tree (confirmed via
`grep -rl WORLDSEEDS src/*.py`), so a reader racing this write (or a crash mid-`json.dump`, e.g.
an unencodable value) can observe or permanently land a truncated/empty file, exactly the hazard
the rest of the codebase has been hardened against. `worldseed.py` already imports `silence` for
`silence.note()` elsewhere in the same file, so `silence.write_json(path, {...})` is a drop-in
replacement.

VERIFIED-BY-READING (grep-confirmed cross-module readers; not independently reproduced with a
live race, since that would require corrupting a real shared data file with concurrent processes —
the mechanism is the same one `silence.write_json`'s docstring already demonstrates was real
elsewhere in this project).

### Reviewed, no issue found
- `build_all()`: reads `ONOMASTICON.json`/`CONTINUITY_GROUPS.json` with broad `except Exception`,
  but defaults are recorded via `silence.note()` and the fallback (`register="classical"`,
  `continuity_group=0`) is a documented, reasonable default rather than a fabricated fact — this
  matches the project's own stated tolerance for "a failure may be tolerated, but never
  unobserved."
- `_first()`: explicitly tags every derived axis as `"attested"` vs `"seeded"` rather than silently
  defaulting — this is the module doing exactly what Hard Rule 0 and the silence discipline ask
  for (a filled value that says it was filled).
- `TEMPLATE`/`CLIMATE_BAND` dict coverage checked against `LANDFORM`/`CLIMATE` table keys — exact
  match, no `KeyError` risk.
- `to_fmg_query`/`unreachable_by_url`: correctly documented and implemented split between what the
  external generator's query string actually honours (empirically tested, per the file's own
  comment) versus what the canonical struct derives but cannot be pushed through a URL — no
  parameter is silently dropped without being named in `unreachable_by_url`.
- `build_all(limit=...)`: `limit` is only ever set by an explicit `--limit` CLI flag (developer/
  testing use), not a silent default — consistent with the project's `--pilot N` convention
  elsewhere.

---

## render.py

No correctness bugs, swallowed failures, caps, tautological checks, writer-contract violations, or
concurrency races found. Notes:
- `containment_svg`'s `nm = str(ch.get("name", ""))[:26]` is a DISPLAY truncation of a text label
  inside a generated SVG diagram (not a data write of the underlying roster) — explicitly fine per
  the display/data distinction.
- `children_of()` correctly derives full, uncapped children lists from the sevenfold tree; no
  cap on bucket size or count.
- `_tree()` and the `--write` block open files with a bare `open()` — `_tree()` is a read of a
  project-owned reference file (`SEVENFOLD.json`), and the `--write` block writes generated SVG
  diagrams to `output/views/`, which (unlike `WORLDSEEDS.json`) is not established elsewhere in the
  tree as a file with concurrent readers; did not find evidence this is a real hazard the way
  `worldseed.py`'s write is.
- Minor, low-severity robustness gap (not raised as a finding): `main()`'s
  `w = WS.build_all(limit=1)[0]` would raise an uncaught `IndexError` if `build_all` returned an
  empty list; this is demo/CLI code, not a data-path concern, and always raises loudly rather than
  swallowing, so it doesn't fit the lens categories being hunted here.

## chord_field.py

No correctness bugs, swallowed failures, caps, tautological checks, writer-contract violations, or
concurrency races found — this module is pure static lore data (`ADJUDICATIONS`) plus a handful of
stateless physics formulas with no I/O and no exception handling to audit. Spot-checked the
formulas against known physics: `landauer_floor` (bits·k·T·ln2) and `recoil_momentum` (E/c) are
textbook-correct; `critical_power_self_focus` matches the standard Marburger critical-power
expression for Kerr self-focusing. Nothing to report.

## catalog.py

No correctness bugs, swallowed failures, or writer-contract issues found — this module only reads
(`load_config`, `load_catalog`, `load_roll`) and never writes shared state, so the two-writer
contract doesn't apply here.
- `cmd_stats`'s `missing[:30]` with an explicit "... and N more" trailer is a DISPLAY truncation
  with the omitted count stated inline — compliant with the project's own display-vs-data
  distinction, not a Hard Rule 0 violation.
- `cmd_search` returns and prints every match with no cap.
- `load_catalog` returning `{}` when the catalog file doesn't exist yet is a legitimate "nothing
  generated yet" state, not a masked failure — no `try/except` is involved.

---

## Summary table

| # | Module | Severity | Status |
|---|--------|----------|--------|
| S1 | silence.py:133 | CRITICAL | REPRODUCED |
| S2 | silence.py:128-129 / 386-388 | HIGH | REPRODUCED |
| S3 | silence.py:99-112 / 290-322 | HIGH | REPRODUCED |
| S4 | silence.py:117-122 | MEDIUM | REPRODUCED |
| W1 | wiki_source.py:275-284 | HIGH | REPRODUCED |
| (nearby) | wiki_source.py:456-514 | — | VERIFIED-BY-READING |
| C1 | chain.py:108-109 | LOW-MEDIUM | VERIFIED-BY-READING |
| (cross-module note) | chain.py:182 | — | HYPOTHESIS |
| WS1 | worldseed.py:317-321 | MEDIUM-HIGH | VERIFIED-BY-READING |
| — | render.py | clean | — |
| — | chord_field.py | clean | — |
| — | catalog.py | clean | — |
