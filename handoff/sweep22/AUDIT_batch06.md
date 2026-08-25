# AUDIT — batch 06

Modules: `magnitude.py`, `identity.py`, `estate.py`, `backfill.py`, `cleanup.py`, `cosmology_graph.py`

Every file was read in full, top to bottom (not sampled). Line numbers cite the file state at
audit time. All findings are annotated VERIFIED (confirmed by direct code reading, and in
several cases by tracing the actual data files on disk or the other modules that call the
function in question) or UNVERIFIED (plausible from reading the code, not independently traced).

---

## HIGH

### H1 — `magnitude.py:244` (`quantity_scores`) — the instrument path inherits M18's band-edge collapse, not just the model path
**VERIFIED**

```python
s = A.axis_score(x, anchor, axis)
```

`quantity_scores()` is the "guard 5" path described in the module's own docstring as producing
"the highest-grade evidence the library can hold" — a measured quantity ("40 tons", "3,000
kilometres") converted to SI and scored *arithmetically*, explicitly bypassing the model. But it
calls the exact same `assay.axis_score()` that M18 already tracks as broken:

```python
# assay.py:219-223
if x is None or x <= 0 or band not in BAND_EDGES:
    return None
i = LADDER.index(band)
if i + 1 >= len(LADDER):
    return 9.9
```

`assay.LADDER` ends at `"M10"` (`assay.py:105`). For any entity anchored at the top rung, every
instrument-measured axis (`ruin` from joules, `reach` from metres) collapses to a flat `9.9`
regardless of the actual magnitude of `x`. An M10 entity with "40 tons" of attested output and
one with "40 googol tons" score identically on the instrument path. This is a second, distinct
occurrence of the M18 defect shape, in the one path the module's own comments call the most
trustworthy evidence in the library ("An instrument outranks an opinion" — `magnitude.py:707`).
It silently destroys exactly the information the instrument path exists to preserve, for every
M10-anchored entity with a measured quantity.

This is downstream of M18's root cause (`axis_score`) rather than a new independent bug in
`magnitude.py`, but it is a second call site the task specifically asked to check for, and it is
not merely cosmetic: it can affect published Assay decimals for top-band entities.

**Suggested repair**: either extend `axis_score`'s M18 fix to cover `magnitude.py`'s call, or
have `quantity_scores()` special-case the top rung (e.g., report the SI value directly in the
worksheet without collapsing to a 9.9 axis score, or widen the axis interval instead of pinning
a point value).

### H2 — `cosmology_graph.py:138` — bare `open(OUT, "w")` on a shared data file, no atomic write, no `silence`
**VERIFIED**

```python
if args.write:
    with open(OUT, "w", encoding="utf-8") as f:
        json.dump({...}, f, indent=2, ensure_ascii=False)
    print(f"\nwrote {OUT}")
```

`OUT = os.path.join(HERE, "data/SHARED_STAGE_GRAPH.json")`. This is a direct, non-atomic write
to a shared data file — no `.tmp` + `silence.replace_retry`, and the module doesn't even
`import silence`. Every other module in this batch (`magnitude.py`, `identity.py`, `estate.py`,
`backfill.py`, `cleanup.py`) goes through the sanctioned `silence.replace_retry` pattern for
exactly this reason (`magnitude.py`'s own comment at line 970-974 explains why: "On Windows
`os.replace` is DENIED while any reader holds the target open... A short retry outwaits any
honest reader"). This file is read directly by two other live modules —

```
src/propagation.py:46:  GRAPH = os.path.join(HERE, "data/SHARED_STAGE_GRAPH.json")
src/resonance.py:141:  path = graph_path or os.path.join(HERE, "data/SHARED_STAGE_GRAPH.json")
```

— so a reader racing this write on Windows is a live, reachable failure mode (`WinError 5`,
per the precedent already documented in `magnitude.py`), and a crash mid-`json.dump` (or an
interrupted process) can leave `SHARED_STAGE_GRAPH.json` truncated/corrupt for both consumers,
which — per `silence.py`'s own stated design goal — is exactly the "corrupt cache
indistinguishable from empty cache" failure class this project has been repeatedly bitten by.

**Suggested repair**: write to `OUT + ".tmp"` then call `silence.replace_retry(tmp, OUT)`,
matching every other writer in this batch.

---

## MEDIUM

### M1 — `magnitude.py:235` — stale/wrong `silence.note` site tag inside `quantity_scores`
**VERIFIED**

```python
def quantity_scores(ev, anchor):
    ...
    for q in ev.get("quantities", []):
        try:
            val = float(str(q["value"]).replace(",", ""))
        except (ValueError, KeyError):
            silence.note("magnitude.py:151")     # <-- line 235, not 151
            continue
```

Line 151 is inside `_ask()` (`nc = 4096 if len(prompt) + len(system) < 11000 else 8192`), a
completely unrelated function. `silence.py`'s whole reason for existing is that "the class is
what makes a pattern visible" (`silence.py:84`) — `health.record` groups failures by the
`site` string. A wrong site tag means a malformed-quantity failure here shows up in
`health.py --failures` grouped under (or confusable with) an unrelated `_ask` sizing branch,
undermining the exact diagnostic value the mechanism is built to provide. Purely a logging
label bug — does not affect the returned scores — but directly relevant to this project's
stated top defect (silent/misleading failure attribution).

**Suggested repair**: `silence.note("magnitude.py:quantity_scores-badvalue")` or similar,
independent of line number so it doesn't drift again.

### M2 — `magnitude.py`, `_split_assay`/`_one_axis` (~451-482) — a per-slice transport failure is recorded as "unestimable," indistinguishable from genuine absence of evidence
**VERIFIED** (logic traced; not runtime-reproduced)

```python
got = _ask(c, SYSTEM, prompt, AXIS_SCHEMA)
if not got:
    continue
...
return ax, ({"score": best[0], "feat": best[1]} if best
            else {"score": A.UNESTIMABLE, "feat": ""})
```

If `_ask()` fails for every slice of a given axis (pool + local both down/timing out for that
call), `best` stays `None` and the axis is reported as `A.UNESTIMABLE` — the identical value
used for "the axis applies but was genuinely never observed being exercised." `_split_assay`
still returns a normal (non-`None`) worksheet as long as *some* other axis got a citation
(`cites` check at line 488), so the entity as a whole is not routed to the `DEFERRED` path.
Once the entity is filed as a scored assay or a legitimate "no axis cleared its gate" — see
`settled()` at `magnitude.py:885` — it is never revisited. A transient transport failure on one
axis's evidence slices can therefore be filed as a permanent, real finding ("this axis has no
evidence") rather than retried — exactly the defect class `silence.py`'s own header describes
("a batch closed on write instead of on result -> 'judged' (378 entries stranded)").

Each individual `_ask` failure IS recorded via `silence.note` for `health.py` purposes, so it
is not literally "unobserved," but the *worksheet itself* — the record other code and humans
read — cannot distinguish "no evidence" from "the model never got asked."

**Suggested repair**: track whether every slice for an axis actually got a transport response;
if none did, mark that axis `"status": "transport-failed"` (or similar) distinct from
`unestimable`, and consider that state disqualifying for `settled()`.

### M3 — `estate.py` — docstring claims "every file, opened," but content is only verified for `.json` and 8 hardcoded text extensions
**VERIFIED** (confirmed against real files on disk)

```python
TEXT_EXT = (".py", ".md", ".txt", ".yaml", ".yml", ".js", ".html", ".css")
...
if ext == ".json":
    ...
elif ext in TEXT_EXT:
    ...
```

Anything outside those two branches is only `os.path.getsize()`d — never opened for content —
despite the module's own repeated framing: *"So: every file, opened. No sampling."*
(line 18), and the header's central thesis that a corrupt file must never look like a
genuinely-empty one. Real files under the tree's own `roots` bypass content verification
entirely:

```
data/records/getter-robo.json.precatfix          (JSON content, but ext != ".json")
data/records.precap_backup/getter-robo.json.precatfix
data/WIKI_HOSTS.json.postsweep
state/backups/allsweep.py.presilence             (Python source, but ext != ".py")
state/*.jsonl, state/*.db-wal, state/*.db-shm
state/*.log  (non-empty ones — .log is exempted from the zero-byte check but is
              never in TEXT_EXT, so a non-empty corrupted log is never read at all)
```

These are largely backup/legacy artifacts rather than live pipeline inputs, which lowers the
practical stakes, but they are exactly the kind of file this module's own docstring says it
exists to catch, and the `.precatfix`/`.presilence` files in particular are the safety-net
backups a repair script would fall back to — the one place you would most want corruption
caught before it's needed.

**Suggested repair**: either loosen the extension gate (e.g., sniff content instead of trusting
the exact suffix, or match on `.json` anywhere in a compound extension) or narrow the docstring's
claim to what the code actually verifies.

### M4 — `cleanup.py:41-48` (`_NAV`) — un-anchored alternatives can unpublish a real entity whose name merely starts with a common word
**VERIFIED** (regex behavior confirmed by reading; not confirmed against a real false-positive in the data)

```python
_NAV = re.compile(
    r"^(?:season\s+\d+\b|category:|list of |index of |gallery$|navigation$|main page$|"
    r"contents?$|glossary$|episodes?$|seasons?$|appearances?$|references?$|trivia$|"
    r"see also$|external links$|sitemap$|all pages$|recent changes$"
    r"|characters?\b|gameplay\b|mechanics\b|controls\b|achievements?\b|trophies\b"
    r"|downloadable content\b|patch notes?\b|version history\b|soundtrack\b)", re.I)
...
if nm and _NAV.match(nm):
```

`.match()` only anchors at the *start* of the string, and the second alternation group
(`characters?\b`, `gameplay\b`, `mechanics\b`, `controls\b`, `achievements?\b`, `trophies\b`,
`downloadable content\b`, `patch notes?\b`, `version history\b`, `soundtrack\b`) has no
trailing `$`. So any entry name that *begins* with one of those words — even as the first word
of a longer, legitimate in-fiction name — matches and gets soft-excluded
(`catalogued = False`, `excluded = "wiki navigation, not an entity of any fiction"`). The
in-file comment explains this is deliberate ("Site furniture takes qualifiers like anything
else does" — matching "Character condition" as well as bare "Character" is the intended fix for
an under-matching bug), but the same widening also means a genuine entity named e.g.
"Soundtrack of the Fallen Choir," "Controls of the Ancients," or "Trophies of the Vanquished"
(all plausible in-fiction item/relic names) would be silently unpublished with no human review,
since this branch (unlike `clean_ceiling`'s "unresolved" path) has no escape hatch — it is a
straight match-and-exclude.

Because the effect is "soft delete" (flag + reason, record preserved, reversible), this is not
data-destroying, but it is a real risk of silently misclassifying legitimate catalogued content
as site furniture given only a name-prefix heuristic.

**Suggested repair**: require the matched word to be the *entire* name (`_NAV.fullmatch`) or add
`$`/word-final anchoring back for the generic single-word alternatives, keeping the looser match
only for the phrases that are unambiguously website furniture (`category:`, `list of `, etc.).

### M5 — `cleanup.py:116-119` (`clean_ceiling`, "prefix" strategy) — can pick the wrong continuity-qualified entity
**VERIFIED** (logic traced against the codebase's own continuity-splitting design in `identity.py`; not confirmed against a real record)

```python
low_pref = [n for n in entry_names
            if n.lower().startswith(ce.lower()) and len(ce) >= 6]
if len(low_pref) >= 1:
    return min(low_pref, key=len), "prefix"
```

This project deliberately keeps continuity variants of the same base character as separate
catalogue entries with a parenthetical suffix (`identity.py`'s entire module: "Kal-El (New
Earth) and Kal-El (Prime Earth) are two accessions... and never averaged"). If a source's
`ceiling_entity` prose names just the base name (e.g. `"Anthony Stark"`) and that source's
`entries` list contains more than one continuity variant (`"Anthony Stark (Earth-616)"`,
`"Anthony Stark (Earth-1610)"`), *both* satisfy the prefix test, and `min(..., key=len)`
silently picks whichever qualified name happens to be textually shorter — not necessarily the
one the ceiling prose actually meant. Unlike the `"unresolved"` path (which is explicitly left
alone and reported precisely to avoid "guessing a name would be worse"), this ambiguous case is
resolved silently with no flag distinguishing "one unambiguous prefix hit" from "one arbitrarily
chosen among several."

**Suggested repair**: when `len(low_pref) > 1`, treat it the same as `"unresolved"` (report for
human review) rather than picking the shortest by default.

---

## LOW / judgment calls

### L1 — `magnitude.py:396-411` (`candidates(ev, cap=None)`) — latent Hard-Rule-0 risk, currently inert
**VERIFIED — not a live violation.** The function *can* truncate the per-axis evidence list
(`sorted(...)[:cap] if cap else sorted(...)`), which is exactly the shape Hard Rule 0 forbids,
but every call site in the tree (`magnitude.py:576`'s `candidates(ev)` and `sweep.py:157`'s
`M.candidates(ev)`) passes no `cap`, so today this is dead capability rather than an active
truncation. Flagged because the parameter exists and a future caller could invoke it silently.

### L2 — `magnitude.py:821-848` (`queue(host=None, limit=None)`) — ranks then truncates, but is a resumable batch-size control, not a content loss
**Judgment call, not a violation.** `return out[:limit] if limit else out` truncates a
richest-evidence-first ranked list when `--limit` is passed. Unlike the roster/page-list caps
Hard Rule 0 was written about, this is an explicit, opt-in CLI knob (`--limit`, default
unbounded) for chunking a long-running batch, and anything not processed this run is simply not
yet `settled()` — it is picked up automatically on the next run, not permanently dropped.

### L3 — `magnitude.py:792,804` (`calibrate()` console print) — float-truncation display bug
**VERIFIED, reproduced.**

```python
print(f"{name:<20}{band + '.' + str(int(val % 1 * 100)):>10}...")
...
print(f"{name:<20}{band}.{int(val % 1 * 100):02d}...")
```

`int(x % 1 * 100)` truncates rather than rounds, and float representation error means this is
frequently wrong by one: for the calibration set's own `2.88` (Jace Beleren),
`2.88 % 1 * 100 == 87.99999999999999`, so `int(...)` prints `87`, not `88`. Confirmed by direct
computation:
```
2.14 -> 14 (correct)   3.52 -> 52 (correct)   4.08 -> 08 (correct)
4.31 -> 30 (correct)   7.62 -> 62 (correct)   2.88 -> 87 (WRONG, should be 88)
```
Console-only — the stored `row["published"]` value used for the actual `consistent` calculation
elsewhere in the same function is unaffected. Purely cosmetic, but it means a human skimming the
calibration table sees the wrong "charter" target for at least one of the six published
benchmarks.

**Suggested repair**: `round(val % 1 * 100)` (or format `val` directly with `%.2f` and split on
the decimal point as a string) instead of truncating.

### L4 — `magnitude.py:373` — reaches into `pipeline.py`'s private `_PATIENT` attribute
**VERIFIED, not a bug, a coupling note.** `if P._PATIENT.search(text) or _HANDOFF.search(text):`
deliberately reuses `pipeline.py`'s underscore-prefixed patient-check regex (per the adjacent
comment). Functionally fine as long as `pipeline.py` doesn't rename or restructure `_PATIENT`;
flagged only because it's a private name crossing a module boundary with no accessor.

### L5 — `identity.py:365` (`main()` console printer) — display cap correctly labeled
**Not a violation.** `top[:6]` with `more = f" +{len(top) - 6} more" if len(top) > 6 else ""` —
a console-summary cap that always discloses how many were omitted. This is the good pattern; contrast with L8 below.

### L6 — `identity.py:317` (`epoch_of`) — sentence truncated to 1200 characters before the epoch-tagging model call
**Judgment call, not a violation.** Bounds a single sentence handed to an LLM call, not a
roster/entry list; sentences this long would be unusual input to begin with.

### L7 — `estate.py` — `inspect()`'s `silence.note` site tags drift by a few lines from their actual call sites
**VERIFIED, very low severity.** E.g. `silence.note("estate.py:83")` at actual line 85,
`silence.note("estate.py:85")` at actual line 88, `silence.note("estate.py:87")` at actual line
91 — off by 2-4 lines each, all still inside the same function and exception cascade, unlike the
much larger drift in M1 above. Same root cause (hand-maintained line-number tags rot as the file
is edited); not worth a fix on its own, but the pattern is the same one M1 documents more
seriously.

### L8 — `backfill.py:222` (`--audit` printer) — display cap with no "+N more" disclosure
**Judgment call.** `for x in rows[:26]:` prints only the first 26 audit rows with no indication
more exist, unlike `identity.py`'s equivalent (L5). Console-only; the underlying `audit()`
function itself returns the full, untruncated list.

### L9 — `backfill.py:146-147` — `next()` without a default raises unhandled `StopIteration` for an unknown `--source`
**VERIFIED.**

```python
rec = next((p, r) for p, r in records if r["source"] == source)
```

If `source` doesn't match any record, this raises a bare `StopIteration` (not caught inside a
generator, so it propagates normally per PEP 479). In `--all` mode this is caught by the
surrounding `try/except Exception` in `main()` (prints `ERROR StopIteration`, unhelpful but
non-fatal). In direct `--source NAME` mode (`main()`'s final loop, lines 251-253) there is no
such guard — an invalid source name crashes the whole script with a raw traceback rather than a
clean "unknown source" message.

**Suggested repair**: `next(((p, r) for p, r in records if r["source"] == source), None)` and
return a clean `{"source": source, "error": "not found"}` when `None`.

### L10 — `backfill.py:54,165-166` (`roster(host, limit=...)`, `backfill_source(..., cap=...)`) — both can truncate a character roster, both opt-in and currently safe as used
**VERIFIED — `roster()`'s `limit` is dead (only ever called with none, per `grep`).**
`backfill_source`'s `--cap` is live but explicitly opt-in, defaults to `None` (unbounded), its
own help text says *"omit for everything, which is the intended use"*, and anything left out by
a cap is not marked "already held" — it simply reappears as `missing` on the next run rather
than being permanently lost. Flagged per instructions ("flag every cap") but this is the
judgment-call end of the spectrum, not the alphabetical-truncation violations the module's own
docstring documents as its reason for existing.

### L11 — `cosmology_graph.py:143` — `if w >= 1.0` filter on persisted graph edges
**VERIFIED, judgment call — but flagged because two other live modules consume this exact file.**
`build_graph()` computes a weight for every co-attested source pair, but only pairs with
`weight >= 1.0` are written into `data/SHARED_STAGE_GRAPH.json`. `len(pair_w)` (the true count)
is printed to console, but `propagation.py` and `resonance.py` both read
`data/SHARED_STAGE_GRAPH.json` directly (`propagation.py:46`, `resonance.py:141`) and never see
the sub-1.0 edges at all. This is a defensible signal/noise threshold on a *derived analytical*
graph (co-attestation strength), not a truncation of primary catalogued content in the
roster/page-list sense Hard Rule 0 was written about — but it silently narrows what two other
modules can ever see from this file, so it's worth the owner's explicit sign-off rather than
being an implicit side effect of the writer.

### L12 — `cosmology_graph.py:86-87` — `pair_shared[p]` capped at 8 examples, self-labeled as a sample
**Not a violation.** The cap only bounds the illustrative "shared entity" examples attached to
a pair (`shared_sample` in the output JSON — correctly named), never the accumulated `weight`
itself, which is computed from every co-attested entity regardless of the cap.

### L13 — `cosmology_graph.py` — missing the project's `_BAD_CHARS` self-check guard present in the other five modules
**VERIFIED.** Every other file in this batch opens itself and checks for the five control
characters that a mangled regex escape has produced repeatedly in this project's history. This
file has neither that guard nor an `import silence` at all. Lower stakes here specifically
because the file contains no regex (`re` isn't even imported), so the failure mode the guard
protects against doesn't currently apply — but the inconsistency means a future edit that adds
a regex to this file wouldn't be protected, and the missing `import silence` is the same root
cause as H2 above (no writer discipline available in this file at all).

### L14 — `cosmology_graph.py:68,121` — `src_entities` is computed and returned but never used
**VERIFIED — dead code.** `build_graph()` builds `src_entities[s] += 1` for every source
touching a shared-evidence key; `main()` unpacks it (`pair_w, pair_shared, src_entities =
build_graph()`) and never references it again. Harmless (cheap to compute), but dead.

---

## Per-module summary

- **`magnitude.py`** — 1 HIGH (H1), 2 MEDIUM (M1, M2), 4 LOW (L1-L4). Not clean; the HIGH finding
  is a direct extension of the task's M18 lead.
- **`identity.py`** — **CLEAN.** Read in full; no correctness bugs, no swallowed-failure
  violations (all exceptions route through `silence.note`), no Hard Rule 0 violations (`mine()`
  explicitly samples nothing; the one console display cap discloses its own truncation — L5).
  Writes go through `silence.replace_retry` correctly. Well-documented dead-code removal
  (lines 322-328) matches what's actually gone. This is a genuinely solid module.
- **`estate.py`** — 1 MEDIUM (M3), 1 LOW (L7). Otherwise clean: correct extension-gated content
  checks for what it does check, proper `ThreadPoolExecutor` usage with no shared-state races,
  no Hard Rule 0 issues (its own display caps are explicitly labeled "e.g." samples with full
  counts preserved).
- **`backfill.py`** — 0 HIGH, 0 MEDIUM, 3 LOW (L8, L9, L10). Core Hard-Rule-0 discipline is
  strong and self-aware (the module's whole reason for existing is repairing past cap/truncation
  bugs, and its own `roster()` and cap-ordering are correctly un-capped by default); the real
  finding is the unhandled `StopIteration` (L9).
- **`cleanup.py`** — 0 HIGH, 2 MEDIUM (M4, M5), 0 LOW beyond what's noted. Importantly: **this
  module does not delete anything.** Every "removal" is `catalogued = False` plus an `excluded`
  reason string, with the original name/description/etc. preserved on the record and reversible;
  writes go through `PL.write_record` correctly. The task's framing ("cleanup.py deletes
  things") does not match what the code does — it soft-excludes, and that's the right design.
  The two MEDIUM findings are about *which* entries get soft-excluded/misattributed, not about
  destructive deletion.
- **`cosmology_graph.py`** — 1 HIGH (H2), 3 LOW (L11-L14). The one HIGH finding (bare
  non-atomic write to a file two other live modules read) is the most clear-cut two-writer-
  contract violation found in this batch.
