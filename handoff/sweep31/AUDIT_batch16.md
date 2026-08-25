# AUDIT — BATCH 16 (run31)

**Modules covered:** `src/local_agent.py` (660 lines), `src/wiki_source.py` (653 lines),
`src/silence.py` (465 lines), `src/worldseed.py` (327 lines), `src/sweep.py` (258 lines),
`src/style_audit.py` (211 lines), `src/ledger.py` (136 lines)

**Total lines read: 2,710** (every line of every file, in full, via `cat -n`; no file was sampled
or skipped).

Known open bug **not re-filed**: `ledger.py:132`, `hi == lo` at the top magnitude band (M10), inside
`assay_to_standards()`. I looked specifically for siblings of this exact shape (a `min(i+1,
len(X)-1)` boundary clamp that collapses to `i` at the top of a ladder) across all seven modules in
this batch and found none. See finding 11 below for a related-but-different observation on the same
function.

---

## 1. `local_agent.py:628-636` — silent JSON-parse fallback crashes the tool loop instead of reporting a per-call error

```python
if isinstance(args, str):
    try:
        args = json.loads(args)
    except Exception:
        args = {}
if fn == "propose_patch":
    res = t_propose_patch(apply=apply, log=patches, **args)
elif fn in impl:
    res = impl[fn](**args)
```

**Why it is wrong.** The `except Exception: args = {}` is a bare, unobserved swallow — no
`silence.note()`, no logging, the exception variable is never even bound. Per `silence.py`'s own
audit criteria this handler is SILENT. Worse: nothing wraps the subsequent
`t_propose_patch(**args)` / `impl[fn](**args)` calls in a `try/except`. `t_read_file(path, ...)`,
`t_grep(pattern, ...)`, `t_find_symbol(name, ...)` and `t_propose_patch(path, find, replace,
why="", ...)` all have **required positional parameters**. Calling any of them with `**{}` raises
`TypeError: missing N required positional arguments`, which is not caught anywhere in `run()`'s
turn loop and crashes the entire task with an unhandled traceback — unlike every other failure mode
in this module (`_chat` transport errors, gate failures, revert failures), which are all
deliberately turned into a structured `{"ok": False, "error": ...}` return.

**Failure scenario.** The local model (a small, imperfect tool-caller) emits a `tool_calls` entry
whose `arguments` string is malformed JSON (truncated, or with a stray comma — a documented failure
mode for small local models). `args` silently becomes `{}`, `t_grep(**{})` (pattern required) raises
`TypeError`, `run()` dies with a raw traceback instead of `{"ok": False, "error": "..."}`. Also, the
model's actual (malformed) argument string is discarded and never recorded, so there is nothing to
diagnose after the fact.

**Severity:** major. **Confidence:** VERIFIED (read directly off the code; the required-parameter
signatures are all in the same file).

---

## 2. `local_agent.py:213-218` — `t_find_symbol` silently drops any file that fails to parse

```python
full = os.path.join(root, fn)
try:
    with open(full, encoding="utf-8") as f:
        tree = ast.parse(f.read())
except Exception:
    continue
```

**Why it is wrong.** No `silence.note()`, no log — an unparseable `.py` file (encoding error,
`SyntaxError`, permission error) is silently excluded from the symbol search, and nothing records
that it happened. This directly undermines the tool's own documented purpose:

> "THE MODEL LANE CAN OVERWRITE THE WRONG FUNCTION (m38)... Giving the model a tool that SAYS a
> name is ambiguous is the cheap half of that fix -- it cannot disambiguate what it was never told
> was ambiguous."

If a second definition of the same function name lives in a file that currently fails to parse
(for instance, mid-edit, or — see finding 3 below — a file `propose_patch` has *already* written an
unvalidated candidate patch into), `t_find_symbol` will report `"count": 1, "unique": true` for the
*other*, parseable definition, and the model will patch it believing there is no ambiguity — the
exact m38 failure this tool exists to prevent, reintroduced by an ordinary silent swallow.

**Failure scenario.** Two files define `foo()`. File A currently fails to parse (e.g. a live,
not-yet-gated `propose_patch` write left it momentarily broken — see finding 3). `find_symbol("foo")`
silently skips File A, returns `count: 1, unique: true` pointing at File B. The model patches File B
confidently, `find` matches uniquely there too, and the patch lands — while File A's `foo()` (the one
that actually needed fixing, or the one that would have made the "unique" claim false) was never
seen.

**Severity:** major. **Confidence:** VERIFIED.

---

## 3. `local_agent.py:526-557` (`t_propose_patch`) — the candidate patch is live, unreviewed, on disk for the entire multi-minute gate window

```python
backup = original
try:
    with open(full, "w", encoding="utf-8") as f:
        f.write(original.replace(find, replace, 1))
    fail = _gates(full, modname)          # pyflakes + import + verify_math (timeout=600)
    if fail:
        with open(full, "w", encoding="utf-8") as f:
            f.write(backup)
        return {"applied": False, "reverted": True, "gate": fail}
    return {"applied": True, "why": why[:200]}
```

**Why it is wrong.** This is a bare, truncating `open(full, "w")` straight onto the live project
file, not a write-to-temp-then-`silence.replace_retry`. `_gates()` runs pyflakes, an import
subprocess, and a full `verify_math.py` run with a 600-second timeout — all *after* the file has
already been overwritten with the unreviewed candidate. For up to ten minutes, any other process on
the machine that imports or reads that exact module (another batch job, `foreman`, a concurrently
running sweep) sees the **unvalidated patch candidate**, not the last-known-good file and not an
atomic swap to the new one. This is precisely the "read-modify-write on a shared file without atomic
replace" hazard `silence.replace_retry`/`silence.write_json` exist to close (see `silence.py`'s own
header on this exact defect class) — but the module that is supposed to be the most careful writer
in the whole codebase (per its own docstring: "WRITES GO THROUGH THE FOREMAN'S OWN BAR") bypasses
that primitive for the one write it actually performs.

**Failure scenario.** `local_agent.py` proposes a patch to `src/pipeline.py` (allowed — not on the
module denylist). Mid-`_gates()` (verify_math running, ~2 minutes in), a concurrently running
`foreman` batch job imports `pipeline` fresh (e.g. a worker process restart) and gets the
not-yet-validated candidate — which, if the patch turns out to fail the gate a few seconds later, is
exactly the code that was supposed to be un-observable by anything outside this function.

**Severity:** major (this is the systemic hazard class the batch brief specifically asked to read
this file hardest for). **Confidence:** VERIFIED.

---

## 4. `wiki_source.py:275-284` (`resolve_wiki`) — `except OSError` does not cover a malformed WIKI_HOSTS.json

```python
try:
    with open(_hosts_path, encoding="utf-8") as f:
        known = json.load(f).get(source_name)
except OSError:
    silence.note("wiki_source-hosts-read")
    known = None
```

**Why it is wrong.** `json.load()` raises `json.JSONDecodeError`, a subclass of `ValueError`, **not**
of `OSError`, when the file exists but is empty, truncated, or otherwise malformed. That case is not
caught here at all — it propagates straight out of `resolve_wiki()` and crashes whatever called it
(`catalogue_web.py`, both call sites). `data/WIKI_HOSTS.json` is written from at least three
different call sites (`hostcheck.py`, `scout.py`, `feats.py`, per grep) and has a **documented
history of exactly this kind of corruption** — `silence.py`'s own module docstring names it by name:
"`WIKI_HOSTS.json` was written from a stale snapshot exactly this way, and `overwatch`'s ledger
nearly lost 68 rounds to the same shape." This is not a hypothetical file.

**Failure scenario.** A writer crashes or is killed mid-write to `WIKI_HOSTS.json` (not itself
impossible even with `silence.write_json`, since a denied replace only *defers* the write — see
finding 12) leaving a truncated/partial JSON file on disk at the moment a catalogue run starts.
`resolve_wiki()` raises an uncaught `JSONDecodeError` instead of degrading gracefully to the
subdomain-guessing path it already has, and the whole catalogue run for that source dies instead of
falling back.

**Severity:** major. **Confidence:** VERIFIED.

---

## 5. `style_audit.py:38-39` — `TURN_ENDING` uses `re.M`, so `$` matches end-of-line, not end-of-entry

```python
TURN_ENDING = re.compile(
    r"(?:\.|\?)\s+(?:And|But|Yet|Still|Which|That)\b[^.]{0,80}\.\s*$", re.M)
...
if TURN_ENDING.search(r):
    turns += 1
```

**Why it is wrong.** `re.M` makes `$` match immediately before *every* `\n` in the string, not only
at the true end of `r`. `record_of()` extracts `rec` with `re.S` (dotall) specifically so a Record's
prose can span multiple lines — the code itself proves multi-line Records are the expected shape.
For any such multi-line Record, a turn-construction sentence that occurs on an *earlier* line (not
the entry's actual final sentence) still matches, because that line's own end also satisfies `$`
under `re.M`. The function name and the report label ("entries ending on a turn", target "<=25%")
both claim this measures whether the entry's *last* sentence is a cheap grammatical flourish — the
regex as written measures whether *any* line does.

**Failure scenario.** A generated Record: `"...the city fell into ruin. But it endured for
centuries more.\nHowever, nothing since has changed."` — the middle sentence trips `TURN_ENDING`
at its own line-end, and the entry is counted in `turn_rate` as "ending on a turn" even though its
actual last sentence does not use a turn construction at all. This inflates the corpus-wide
`turn_rate` metric the whole module exists to police, which can either wrongly trip the "OVER
(target <= 25%)" warning on compliant prose, or (more insidiously) mask the true per-entry rate by
mixing genuine violations with false positives so the number stops meaning what the report claims.

**Severity:** major (this is a QA measurement module; a systematically biased metric is exactly the
kind of "plausible-looking wrong answer" the project's whole SILENCE doctrine is about). **Confidence:**
VERIFIED (regex semantics + `record_of`'s own `re.S` proves multi-line input is expected).

---

## 6. `worldseed.py:317-322` — `data/WORLDSEEDS.json` is written with a bare `open()`+`json.dump`, bypassing `silence.write_json`

```python
if args.write:
    path = os.path.join(HERE, "data", "WORLDSEEDS.json")
    with open(path, "w", encoding="utf-8") as f:
        json.dump({w["designation"]: {"address": address(w), **w} for w in worlds},
                  f, indent=2, ensure_ascii=False)
    print(f"\nwrote {path}")
```

**Why it is wrong.** This is precisely the anti-pattern `silence.py`'s own module docstring names as
the project's single most expensive recurring defect class:

> "TWELVE call sites across ten modules were writing shared `data/` and `state/` files with a bare
> `open(path, "w")` + `json.dump`, which is not a write but a TRUNCATE-THEN-FILL. A reader arriving
> in the gap sees an empty or half-written file; a crash in the gap leaves it that way permanently."

`data/WORLDSEEDS.json` is exactly the kind of shared `data/` file the two-writer contract described
in this batch's brief requires to land via `silence.write_json`/`silence.replace_retry`. This module
imports `silence` already (line 65) — the fix is a one-line swap to `silence.write_json(path, {...})`.

**Failure scenario.** `worldseed.py --write` is interrupted (killed, crashes on an unrelated
exception between the `json.dump` writing its first bytes and closing the file — e.g. a disk-full
condition, or the process being reaped by whatever supervises long batch jobs in this project) while
another process is reading `data/WORLDSEEDS.json` (e.g. anything that regenerates a map from a
stored address): it observes a truncated/empty file, or — on the next run — a half-written one is
left permanently on disk with no record of the failure and no automatic fallback to a previous good
copy, unlike every file `silence.write_json` protects (which fails safe by leaving the *previous*
version in place and recording the denial).

**Severity:** major. **Confidence:** VERIFIED.

---

## 7. `local_agent.py:642` — tool results are blind-truncated to 12,000 chars, unlike `read_file`'s own paging

```python
messages.append({"role": "tool", "content": json.dumps(res)[:SLICE]})
```

**Why it is wrong.** `SLICE` (12000) is explicitly documented at its definition (line 49) as "a
WINDOW, not a cap: the model pages through a big file with offset, and the tool says how much
remains so nothing silently falls off the end" — but that guarantee is only actually implemented
inside `t_read_file` (`chars_after_slice`) and, separately, `t_run_check` (its own `"truncated"`
flag over the last 6000 chars). This line applies a second, blanket truncation to the *serialized
JSON of every tool result*, including `t_grep`'s `hits` list (which has no internal cap — see the
truncation inventory below) and `t_find_symbol`'s `definitions` list. Neither carries any signal
that the message the model actually receives was cut, and the cut can land mid-JSON-string, further
garbling whatever content did survive.

**Failure scenario.** The model calls `grep` with a broad pattern across all of `src/`; the tool
function itself returns every match (potentially hundreds, no cap in `t_grep`). Once serialized and
passed through this line, results past ~12,000 characters of JSON are silently gone from what the
model actually sees, without any `truncated: true` marker — the model can be led to conclude a
pattern is rare when it is actually common, purely because of a downstream truncation the tool layer
itself never applied.

**Severity:** major (matches Hard Rule 0's letter directly — "truncation ... that makes the universe
smaller than it really is" — even though the effect here is confined to a single conversation turn
rather than permanent corpus data). **Confidence:** VERIFIED.

---

## 8. `local_agent.py:494-514` — the `DENYLIST_PREFIXES` loop in `t_propose_patch` is currently unreachable

```python
if not (any(_rel_l.startswith(p) for p in WRITABLE_PREFIXES)
        or _rel_l in {f.lower() for f in WRITABLE_FILES}):
    return {"applied": False, "error": "... outside the writable surface ..."}
for _pfx in DENYLIST_PREFIXES:
    if _rel_l.startswith(_pfx):
        return {"applied": False, "error": "... protected region ..."}
```

**Why it is wrong (as a documentation issue, not a hole).** `WRITABLE_PREFIXES = ("src/",
"prompts/", "handoff/")` and `DENYLIST_PREFIXES = ("data/records/", "reference/keystone_volumes/",
"output/index/", "state/", ".git/")` — no entry in the second set is a sub-path of any entry in the
first. Since the allowlist check runs strictly *before* this loop and already refuses anything not
under a writable prefix, `_rel_l` can never simultaneously pass the allowlist and match a deny
prefix; the `for _pfx in DENYLIST_PREFIXES` loop's `if` can never be true today. This is **not** a
live security hole — the allowlist alone already refuses `data/records/*`, `state/*`, etc. — but the
adjacent comment ("Checked after the name denylist and before anything is read, so a protected path
never even reaches the find/replace") reads as though this check is the thing doing that protection,
when currently the allowlist is. If `WRITABLE_PREFIXES` is ever widened (e.g. to legitimately permit
`data/` for some new tool), this loop would silently start being the only thing standing between that
wider surface and `data/records/`/`state/` — worth knowing it is currently untested-by-use.

**Severity:** minor (comment/behavior mismatch; no live bypass). **Confidence:** VERIFIED.

---

## 9. `style_audit.py` — no `import silence`; no export-copy guard; no `_BAD_CHARS` self-check on a file that itself contains a `\b`-heavy regex

**Why it matters.** Every other module in this batch (`local_agent.py`, `wiki_source.py`,
`silence.py` itself, `sweep.py`, `worldseed.py`) imports `silence`, which is what makes the
"you're running the PUBLISHED EXPORT COPY, stop" guard universal — silence.py's own comment says so
explicitly: "Every module imports `silence`, so this one check guards all of them." `style_audit.py`
never imports `silence` at all, so it has none of that protection: run against
`panscriptum-export/src/style_audit.py` by mistake (a documented, twice-already-happened hazard per
`silence.py`'s header) and it will read whatever `output/raw` exists in that tree (likely nothing,
printing "no generated output" and exiting 0) rather than failing fast with a clear reason.
Separately, `style_audit.py` also lacks the `_BAD_CHARS` self-check present in `local_agent.py`,
`silence.py`, and `sweep.py` — a check that exists specifically because a `\b` word-boundary escape
written through a shell heredoc has been silently corrupted into a literal control character *five
times* in this project (per `sweep.py`'s own comment). `style_audit.py`'s `TURN_ENDING` regex (see
finding 5) contains exactly such a `\b` escape, unguarded.

**Severity:** minor (defense-in-depth gap, not an active bug by itself). **Confidence:** VERIFIED
(absence confirmed by full read; no `import silence` and no `_BAD_CHARS` anywhere in the file).

---

## 10. `wiki_source.py` — stale line-number labels in `silence.note()` calls

Lines 190, 196, 241, 295, 567, 586, 613 pass labels like `"wiki_source.py:155"`,
`"wiki_source.py:160"`, `"wiki_source.py:204"`, `"wiki_source.py:229"`, `"wiki_source.py:376"`,
`"wiki_source.py:394"`, `"wiki_source.py:420"` — none of which match the line the call actually sits
on any more (e.g. the `:155` label is on the code now at line 190; line 155 is presently inside an
unrelated comment block about worker counts). These are pure health-ledger grouping keys, not used
to navigate code, so this is not a functional bug — but it does mean anyone diagnosing a failure via
`health.py --failures` and grepping the current file for `"wiki_source.py:155"` to find the
offending code will land on the wrong lines. Newer handlers in the same file already use semantic
labels instead (e.g. `"wiki_source-hosts-read"`, `"wiki_source-category-probe"`) — the module itself
has moved away from this pattern but not finished migrating.

**Severity:** cosmetic. **Confidence:** VERIFIED.

---

## 11. `ledger.py` — known M10 bug not re-filed; sibling search; one related (separate) gap

Confirmed `ledger.py:130-133` — `hi == lo` at `magnitude_band == "M10"` (the top of `LADDER`) because
`min(i + 1, len(LADDER) - 1)` clamps to `i` itself once `i == len(LADDER) - 1`, collapsing the
log-interpolation range to a point regardless of `ruin_score`. **Not re-filed, per instructions.**

Searched all seven modules in this batch for the same shape (a `min(i+1, len(X)-1)`-style
last-index clamp): none found outside `ledger.py:132` itself. No sibling in this batch.

One related but distinct gap in the same function, noted for completeness rather than filed as the
known bug: `assay_to_standards(magnitude_band, ruin_score=5.0)` never validates or clamps
`ruin_score` to its documented 0–10 domain. A caller passing a value outside that range would
silently extrapolate `joules` below `lo` or above `hi` with no bound and no warning. No caller in
this batch passes an out-of-range value (`ledger.py` has no other callers of this function within
this batch), so this is a HYPOTHESIS / low-severity latent gap, not a demonstrated bug.

---

## 12. `silence.py:263-280` (`replace_retry`) — only `PermissionError` is caught, contradicting the "never raises" promise for other `os.replace` failures

```python
def replace_retry(tmp, dst, attempts=5):
    for a in range(attempts):
        try:
            os.replace(tmp, dst)
            return True
        except PermissionError:
            if a == attempts - 1:
                note("replace-denied:" + os.path.basename(dst))
            else:
                _t.sleep(0.3 * (a + 1))
    return False
```

**Why it is worth flagging.** The docstring's promise ("persistent denial is recorded, never
raised") and `write_json`'s own docstring ("Never raises on a denied replace") are scoped to the
Windows-reader-holds-the-file case (`PermissionError`, WinError 5) that this function was built for
— and it handles that case correctly. But `os.replace` can also raise other `OSError` subtypes (for
instance `FileNotFoundError` if `tmp` has already been removed by something else between its
creation and this call), which are not `PermissionError` and are not caught here, so they propagate
straight out of `replace_retry` — and, since `write_json` calls `replace_retry(tmp, path)` outside
its own `try/except` (that `try` covers only the `open(tmp, "w")`/`json.dump` step), straight out of
`write_json` too, contradicting its "never raises" documentation for that narrower case.

**Severity:** minor. **Confidence:** HYPOTHESIS on real-world frequency (the mechanism is verified
in the code; whether `tmp` ever actually vanishes out from under a caller in practice was not
observed, only reasoned about).

---

## Hard Rule 0 truncation inventory (every `[:N]` / `limit` / `top` / `head` found in this batch)

Grepped every file for `[:` truncation and `limit`/`top`/`hard_stop` parameters, and classified each
occurrence. **No live "universe of results" cap was found** — the module that had the worst history
of this (`wiki_source.py`) has already been hardened for it, verified below.

- **Verified clean (all defaults are `None`, all live callers pass `None`):**
  `wiki_source.find_categories(limit=None)`, `category_members(limit=None)`,
  `rank_by_size(top=None)`, `all_categories(hard_stop=None)`. Grepped every call site in the tree
  (`catalogue_web.py`, the only caller of all four) — every one explicitly passes `None`/`limit=None`
  /`top=None`, several with an inline `# rank, never truncate` comment. These four functions each
  carry extensive docstrings describing a *previously real* Hard Rule 0 bug that was fixed here
  (6-item category cap, 6000-category `hard_stop`, alphabetical-first-N category-member cap) — this
  batch found no regression of any of them.
- **Display-only samples, full data preserved underneath (not a Hard Rule 0 violation):**
  `sweep.py` `report()`: `sorted(rows, ...)[:top]` (default 18), `gap.most_common(10)`,
  `bysrc.most_common(8)` — console-only; the complete `rows` list is what gets written to
  `CHARACTER_SWEEP.json` via `silence.write_json`, untruncated.
  `style_audit.py` `report()`: `a["shapes"].most_common(top)`, `a["openers"].most_common(top)`,
  `sorted(a["banned"].items(), ...)[:14]`, `a["vocab"].most_common(10)` — console-only; the
  underlying `Counter`s used for `self_test`'s pass/fail check and for `len(a['banned'])` are full.
  `worldseed.py` `main()`: `worlds[:6]` sample print (explicitly labeled "SAMPLE"), a `Counter(...).
  most_common(6)` distribution print — the `--write` path serializes every world.
- **Diagnostic-string / log-line bounds, not data-completeness truncation:** every `str(e)[:100..200]`
  in `local_agent.py`'s gate/tool-error paths and `wiki_source.py`'s exception messages;
  `silence.swallow.detail[:60]`; `local_agent.py`'s `why[:200]`/`find[:200]`/`replace[:200]` audit-log
  fields.
  fields.
- **Hash/digest truncation, not data truncation:** `silence.digest_of`'s `hexdigest()[:16]`
  (a compare-and-swap fingerprint); `worldseed.seed_for`/`_first`'s `hexdigest()[:6]`/`[:8]`
  (deterministic seed derivation).
- **Considered, documented performance tradeoffs (flagged per instruction to report every
  truncation; not treated as bugs):** `wiki_source.page_text(max_chars=900)`,
  `_paragraphs`'s `[:max_chars]`, `extracts(chars=700)` — these bound how much lead-prose text is
  pulled *per article* (documented: fetching a whole page "costs ~420KB per article... over tens of
  thousands of pages is absurd"), not which entities/pages get processed. `subdomain_candidates`'s
  `words[:2]` and `verify_wiki_matches`'s `words[:4]` build search-query/guess strings, not result
  listings.

---

## Summary counts

- Major: 7 (findings 1–7)
- Minor: 3 (findings 8, 9, 12)
- Cosmetic: 1 (finding 10)
- Known bug (not re-filed) + sibling search + one related gap noted: finding 11
