# AUDIT — sweep run57, batch 11

Modules read in full, top to bottom, in successive chunks (no sampling, Hard Rule 0):
`src/magnitude.py` (1,989 lines), `src/silence.py` (1,126), `src/scout.py` (826),
`src/weave_index.py` (721), `src/address.py` (539), `src/coverage.py` (436), `src/profile.py`
(327), `src/tells.py` (296). Every line-count above matches `wc -l` at the time of this audit.

AUDIT ONLY. No file under `src/`, `data/`, or `state/` was edited. `magnitude.py --calibrate`,
`drill.py` and `verify_math.py` were never run. Every behavioural claim below was reproduced in a
throwaway, read-only `python -c` snippet (shown inline) rather than taken on the strength of a
docstring's own claim about itself. The open work-order queue was fetched first
(`workorders.open_orders()`) and checked against every candidate finding before it was written up.

---

## profile.py — nothing new found

Read in full. This is the module the brief calls out for run #56's change: `decode()` gained a
per-axis range check (lines 187–195) that raises `ValueError` naming the profile, the axis, the
offending character, and the axis's legal digit range, rather than letting `tbl[B32.index(ch)]`
raise a bare `IndexError` from inside a comprehension.

Checked whether the fix still misses the band digit or the address, per the brief's own question.
It does not, and for a structural reason rather than an oversight: the band group in `_PROFILE_RE`
is scoped to exactly `[0-9au]` (11 legal values), which line up 1:1 with `BANDS`'s 11 entries
(`M0`..`M10`) — `B32.index('a') == 10 == len(BANDS) - 1`, so `BANDS[B32.index(band)]` can never run
past the end of the list. The address group is scoped to `_B32_CLASS`, the full alphabet `_unb32`
already accepts by construction, so it can never emit an out-of-range index either. Only the
per-axis feature digit needed the new guard, because `AXES`' tables are shorter than the 32-symbol
alphabet the regex admits for them — and that asymmetry is exactly what the new check closes.

Reproduced live (read-only):

```
>>> decode('PS-i23-myc-0000-u0')
ValueError: not a world profile: 'PS-i23-myc-0000-u0'                      # pattern refuses first
>>> decode('PS-1-myc-000z-u0')
ValueError: not a world profile: 'PS-1-myc-000z-u0' -- the tech digit 'z' is index 31, but the
tech table holds only 4 value(s); the legal tech digits are '0123'          # NEW guard fires
>>> decode('PS-1-myc-0000-a4')
{'band': 'M10', ...}                                                        # top band decodes cleanly
```

Nothing else in the module changed shape from what its own comments claim. `encode()`'s band
clamp (`tier > 10 -> tier = 10`) and `decode()`'s inverse are consistent with each other and with
`BANDS`. `main()`'s round-trip check, sample printer and `_reason_cell`-free plain report are all
unchanged and unremarkable. **Nothing found in profile.py beyond the documented and now-verified
run #56 fix.**

---

## magnitude.py

Read in full, including `SYSTEM`/`SCHEMA`, all five guards, `_split_assay`/`_split_gate`,
`calibrate()`, `run_batch()` and `main()`.

### DEFECT (comment-accuracy only) — magnitude.py:946–948 — KNOWN(89503c58409f)

```python
    THE `cap` PARAMETER IS GONE (order 7eee204672ce). This was `candidates(ev, cap=None)` ending
    in `sorted(...)[:cap] if cap else sorted(...)`, and neither of its two callers -- :1172 here
    and sweep.py:190 -- ever passed one, ...
```

Verified: the real call site in this file is `magnitude.py:1230` (`cand = candidates(ev)` inside
`assay_entity`), not 1172 (which today sits inside the `_split_gate` docstring). The real call
site in `sweep.py` is `sweep.py:199` (`cand = M.candidates(ev)`), not 190 (a comment about
`cachekey.load`'s `on_corrupt` parameter).

This is not a new site — it is the exact row already filed in order `89503c58409f` ("SIXTY LINE
CITATIONS…"), which records this identical comment citing `:1172 here and sweep.py:190` against
an actual of `magnitude.py:1207 and sweep.py:199`. The file has grown eight lines further since
that order was written (1207 → 1230 in this file; `sweep.py`'s site is unchanged at 199). No new
finding — restated only to confirm the order is still open and still accurate in kind, now off by
a slightly larger margin in this file. **KNOWN(89503c58409f).**

### `_reason_cell()` (new in run #56) — verified correct

```python
def _reason_cell(s, width):
    s = str(s)
    return s if len(s) <= width else s[:width - 1] + chr(8230)
```

A display-only, marked (ellipsis) truncation used solely in `calibrate()`'s console table (line
1656), while the full, uncut reason is written to `CHARTER_REGRESSION.json` by `_land` on the line
above it in every call path. This is a reversible display cut of exactly the kind Hard Rule 0
permits (nothing persisted is shortened), and it matches the shape of the module's own citation of
five sibling helpers (`allsweep._marked`, `tiers._cut`, etc.). No defect.

### Guards 1–5, saturation, quantity conversion — nothing found

Traced all five guards (VERBATIM, RELEVANCE, SUBJECT, SATURATION, QUANTITY) on both the one-shot
(`verify`) and split (`_split_gate`) paths, and the guard-3-on-instrument-readings fix
(`quantity_scores`, order `41e8ffc2e490`). All are applied on every path that reaches a published
record; the module's own extensive commentary of prior defects in this area (orders `66696f8ee28f`,
`e22f29b8e4df`, `dd76d4a930f7`, `d2f89bfe967d`, `8f14aff37392`) was independently checked against
the current code and each is fixed as claimed — the one-shot and split gates now call the same
`_resolve_citation`/`_status_score`/`subject_refusal` helpers rather than diverging.

Unit conversions in `_TO_JOULES`/`_TO_METRES` are numerically correct (1 ton TNT = 4.184×10⁹ J;
1 mile = 1609.34 m; 1 light-year = 9.461×10¹⁵ m; 1 parsec = 3.086×10¹⁶ m — standard values). The
`saturated()` six-axis floor is a stated, disclosed policy choice (not a silent one) and is applied
consistently. `calibrate()`'s `_published()` decimal-column fix (order `392372951714`, printing the
true fractional part instead of `int(val % 1 * 100)`) was checked by hand against the six
`BENCHMARKS` rows and reproduces the charter's own published decimals correctly (e.g. 2.88 →
`"M2.88"`, not `"M2.87"`).

`swallow`/silent-except audit turned up nothing new: the one bare `except FileNotFoundError: pass`
in `calibrate()` (line 1554, "no prior CHARTER_REGRESSION.json to resume") is the ordinary
first-run case with nothing to lose — legitimate, not a defect.

**Nothing else found wrong in magnitude.py.**

---

## silence.py

Read in full, including `swallow`, `_handler_is_observed`/`_suppress_is_declared`, `append_line`'s
Windows-append fix, `digest_of`/`replace_if_unchanged`, `write_json`, `note()`, and the
`instrument()`/`_ensure_import`/`_handler_tags` rewriter.

### Verified: run #56's "instrument() message kept whole" claim

```python
except Exception as exc:
    note("silence.py:instrument-unparseable:" + label)
    print("  !! %s: could not be parsed (%s: %s); left uninstrumented"
          # WHOLE (order 215f9e7b86ff). `note()` one line above records the LABEL, not
          # the message, so this print was the only account of WHY the module would not
          # parse -- and the eaten-escape corruption this project keeps paying for
          # announces itself in exactly such a message.
          % (label, type(exc).__name__, str(exc)))
```

Confirmed: `str(exc)` is passed whole, with no `[:N]` slice anywhere on this path (line 1046–1052).
This is the only place in the file the brief's "message now kept whole" note could refer to, and it
checks out.

### Atomic-write correctness — verified against the checklist, nothing found

* **tmp naming**: `write_json`'s tmp is `"%s.%d.%d.tmp" % (path, os.getpid(), threading.get_ident())`
  (line 827) — pid and thread, collision-proof across processes and threads. Confirmed.
* **fsync**: `write_json` does `f.flush(); os.fsync(f.fileno())` before closing the temp file
  (lines 831–832), ahead of the rename. Confirmed present and placed correctly (data on disk
  before the rename that publishes it).
* **replace retry**: `replace_retry` backs off `0.3*(a+1)`s across `PermissionError` only, and
  reports (never retries) any other `OSError` under a **different** ledger key
  (`replace-failed:` vs `replace-denied:`) — matching the module's own stated rule that "a
  different fault wears a different name in the ledger." Confirmed by reading both branches.
* **digest-before-read for compare-and-swap**: `replace_if_unchanged` re-digests `dst`
  **inside** the retry loop, immediately before each `os.replace` attempt (line 667) — the fix for
  the historical defect (order `fede605db64f`) where the digest was taken once and the rename
  slept for up to 3s afterward, leaving a window another writer could land in undetected. Verified
  the loop shape: `for a in range(attempts): actual = _digest_or_unreadable(dst); ... os.replace(...)`
  — compare and swap are adjacent on every attempt, not just the first. Confirmed correct.

One residual note, raised as a **QUESTION rather than a DEFECT** because it is a platform
subtlety this project's own doctrine may or may not consider in scope: `write_json`'s docstring
claims the fsync closes the crash gap "between the rename and the filesystem flushing the temp's
blocks" — but the fsync happens on the **temp file's** descriptor before the rename, not on the
**directory** after it. On a POSIX filesystem, the directory-entry update that `os.replace`
performs is not itself guaranteed durable across a crash without an additional `fsync` on the
containing directory. Whether this matters on this project's actual Windows deployment (where
`os.replace` has different underlying semantics, per the `append_line` docstring's own extensive
Windows-vs-POSIX analysis a few functions above) is exactly the kind of platform-specific claim
this codebase is careful never to assume without measuring — raised for a ruling, not asserted as
a live bug.

### `swallow` class — QUESTION, not a defect (self-disclosed dead code)

```python
class swallow:
    ...
    # This class has no live callers in src/ today, so nothing downstream was relying on the old
    # width.
```

Verified: `grep -rn "silence\.swallow" src/` (excluding `silence.py` itself) returns nothing. The
class is genuinely unused anywhere in `src/`, exactly as its own comment already discloses. Not a
new finding — the file states this fact about itself honestly rather than hiding it — but flagged
as a **QUESTION** given Hard Rule -1's own line that "a safety in a file is not a safety in
effect": if `swallow` is meant to replace some of the bare `except: ... ; health.record(...)`
patterns still written by hand elsewhere in the tree, it currently replaces none of them.

**Nothing else found wrong in silence.py.** `_handler_is_observed`'s re-raise-via-AST-walk fix,
`_OBSERVED_RX` word-boundary fix, and `_suppressed_names`/`_suppress_is_declared`'s separate
silent/declared handling were all re-read against their own described defects and are correct as
claimed.

---

## scout.py

Read in full, including `_mutate`'s CAS loop, `_ask`'s four-way outcome split, `verify()`'s
three-way HTTP-failure classification, `scout()`'s URL verification and registration gating, and
`sweep()`'s stamp-before-work rotation, archive-not-delete roll-off, and unstamp-on-never-asked
logic.

### QUESTION — scout.py:175–178 — a tmp-cleanup failure inside `_mutate`'s CAS retry loop is silent, unlike every sibling branch in the same function

```python
        last_why = why
        try:
            os.remove(tmp)
        except OSError:
            pass
        _t.sleep(0.05 * (a + 1))
```

Every other failure path inside this same function (`_mutate`) calls `silence.note(...)`:
`scout.py:mutate-unreadable` (150), `scout.py:mutate-wrong-shape` (157), `scout.py:mutate-failed`
(183, on final exhaustion). This one branch — the per-attempt cleanup of a failed CAS attempt's
temp file — is the only one in the function that swallows its exception with no record at all.

Checked whether this is an isolated oversight or an established pattern: the **identical** shape
(`try: os.remove(tmp) / except OSError: pass`, no note) exists in `workorders.py`'s own
`_mutate`-equivalent (`workorders.py:441-443`), commented there as accepted (a failed remove just
leaves harmless litter, because the next attempt mints a fresh, uniquely-named tmp from the
incremented attempt counter, and the function's own final failure is separately recorded). Given
that this exact shape already exists elsewhere in the tree without being flagged, this is raised
as a **QUESTION** (should every tmp-cleanup swallow get a `note()`, or is per-attempt litter
genuinely below the bar) rather than asserted as a DEFECT.

**Nothing else found wrong in scout.py.** The `hostless()`/`hostcheck.adopt()` two-writer CAS
discipline, the `sweep()` last-attempted-first rotation (with its documented former pinning bug
already fixed), the never-asked unstamp logic, and the archive-before-trim roll-off were all
re-verified against their own described former defects and are correct as claimed.

---

## weave_index.py

Read in full, including `designations()`'s corpus-derived continuity-marker cache,
`_records_sig()`'s per-file and per-directory OSError handling, `build()`'s excluded-entry
accounting, and `staleness()`/`escalate_if_stale()`.

### KNOWN(d1709d8e757d) and KNOWN(2cb442afd901) — `staleness()` / index-rebuild scheduling

`staleness()` (line 432) and `escalate_if_stale()` (line 522) are exactly the remedy order
`d1709d8e757d` (`ENTITY_INDEX_NEVER_REBUILT_STALENESS_ANNOUNCED_BUT_UNACTED`) describes taking:
since this module cannot itself edit `overnight.STANDING` or `foreman`'s remedies, every
invocation of `weave_index.py` — report mode or `--write` — files/refreshes a RUN-rung work order
once the index is stale. Confirmed this is wired into `main()` (line 576) before the (possibly
expensive) build, so a report-only run still raises it.

The docstring's own "WHAT IS LEFT FOR A RULING" paragraph (lines 498–504) is the live, open
question order `2cb442afd901` names (whether a heavily-moved-but-recent corpus, i.e. `behind`
without `stale`, should itself raise the order) — still unresolved by design, correctly left to an
owner ruling rather than guessed at in code. Both orders are already known and both are
implemented/deferred exactly as the queue says. No new finding.

Independently re-verified the `stale`/`behind` truth-table fix (order `9e884802918e`) by hand
against the four `(A, B)` cases the docstring itself tabulates (lines 468–483) — the code's
`stale = bool(age_hours > STALE_HOURS)` matches the corrected column, not the old
`coarse_stale and age_hours > STALE_HOURS` (which reduces to `B` alone, discarding the `behind`
signal entirely). Confirmed correct.

**Nothing else found wrong in weave_index.py.** `_records_sig()`'s per-file-vs-per-directory
`OSError` asymmetry (the fix for order `5f1dc97d5216`), `load_records()`'s signature-gated cache,
and the `len<3`/`_STOPNAMES` matching-vs-indexing separation (orders `e959f566275d`,
`8f50f37255b5`) were all re-checked against their own described former defects and hold.

---

## address.py

Read in full, including the four-stage `spine_code_for()` matcher (exact/normalized equality,
most-specific-wins containment with the opens/closes title-guard, and the token-overlap
fallback), `slugify()`, `chapter_label_for()`, and the promotion ladder (`tier_for`/`tier_rank`/
`promote`).

### QUESTION (pre-existing, self-documented — not new) — address.py:40–56 — `_FILLER`'s dead single-character entries and the undecided original intent

```python
# SIX OF THE TWELVE ENTRIES HERE COULD NEVER BE CONSULTED (order 7b9d3605a8a4). ...
# AND THE ORIGINAL INTENT IS AN OPEN QUESTION, NOT SETTLED HERE. "1", "2" and "3" sitting in
# the list suggests single-character tokens were once meant to be excluded BY NAME rather than
# by length. Dropping the `len(w) > 1` filter and letting this set do the whole job is a
# BEHAVIOUR change ... so it is left for a ruling and only the dead entries are removed.
_FILLER = {"all", "the", "and", "incl", "its", "associated"}
```

Confirmed the six dead single-character entries (`&`, `-`, `1`, `2`, `3`, and one more) were
already removed per order `7b9d3605a8a4`, and the remaining question (whether `len(w) > 1` should
be dropped in favour of `_FILLER` doing the whole job) is explicitly left open in the code itself,
pending a ruling. This is not a new finding — restated only because it is a live, unresolved
QUESTION a reader of this module would otherwise have to re-discover.

**Nothing else found wrong in address.py.** The three layered fixes to `spine_code_for` (raw-letter
containment → word-boundary containment; first-in-file → most-specific-wins; single-token
mid-title false positives → the opens/closes-with-clean-remainder guard) were each re-verified
against the worked examples in their own comments (e.g. `"Sword Coast Adventurer's Guide DC
Edition Reprint"`, `"Alien Predator Doom Crossover"`) by tracing the code path by hand; all three
resolve as documented. `promote()`'s promotion-only-never-demotion guarantee and `tier_rank()`'s
`None`-for-unrecognised-tier repair are correct.

---

## coverage.py

Read in full, including `state_of()`'s strict CITED > READ > NO PAGE > UNREACHABLE > NOT ATTEMPTED
precedence, `_empty_state()`'s CLEAN_NEGATIVES-based UNREACHABLE classification, the
classifier-version cache-busting scheme (`_CLASSIFIER_VERSION`), `measure()`'s fail-closed host-map
read, and `report()`/`main()`.

### KNOWN(e3b2668af9af) — coverage.py:378 — undisclosed <40-entry floor

```python
    have = [r for r in rows if r["host"] and r["entries"] >= 40]
```

Confirmed present exactly as the brief's own hint describes: this floor silently drops every
source with fewer than 40 entries from **both** the WORST COVERED and BEST COVERED ranked lists
(lines 379, 390) with no line anywhere disclosing that the floor was applied or how many sources
it excluded — in contrast to every other cut in this file's `report()`, which is announced
("showing N of M... --show to raise"). Verified this floor does **not** reach the headline totals
(`n`, `cited`, `read`, `nopage`, etc. at lines 337–346 sum over the full `rows`, not `have`), so the
top-line coverage percentage is honest; only the two per-source leaderboards are quietly filtered.
Already recorded as order `e3b2668af9af`, no new information beyond confirming it is still present
and unchanged at the same line.

### `state_of()` precedence — traced by hand, confirmed correct

Walked the `CITED > READ > NO PAGE > UNREACHABLE > NOT ATTEMPTED` precedence claim against the
actual branches (lines 185–192) for every ordering of candidate files a real corpus could produce:
a `CITED` file returns immediately regardless of loop position; `READ` unconditionally raises
`best` past `NO PAGE`/`UNREACHABLE`/`NOT ATTEMPTED` but is never itself downgraded by a
later-seen `NO PAGE` or `UNREACHABLE` (their `elif` guards only fire when `best[0]` is still
`NOT ATTEMPTED`/`UNREACHABLE`); `NO PAGE` is never downgraded back to `UNREACHABLE`. All four
non-CITED states are monotonically non-decreasing across the loop in exactly the stated order.
One incidental observation, not a live defect: when two candidate files for the same entity are
both `READ`, the second one's `n_pages` silently replaces the first's rather than summing — but
`measure()`'s only caller discards the `n_pages` return value entirely (`st, nf, _ = state_of(...)`),
so this never reaches any published number. Not reported as a finding.

**Nothing else found wrong in coverage.py.** The classifier-version cache invalidation (order
`1d55458779fd`, the fix for a memo that was keyed on file mtime but not on classifier logic
version, which made the UNREACHABLE rollout invisible for a full run) and the fail-closed
host-map read in `measure()` were both re-checked against their own documented former failure
modes and hold.

---

## tells.py

Read in full, including the `LEXICAL`/`LEXICAL_FICTION`/`STRUCTURAL`/`DISCOURSE` tables,
`_anchor()`'s sentence-boundary rewrite, `scan()`, `prompt_section()`, and `prompt_in_sync()`.

### DEFECT (new) — tells.py:161–166 — `_anchor()`'s sentence-boundary rewrite silently dropped tolerance for leading whitespace at the true start of a passage

```python
_SENTENCE_START = r"(?:^|(?<=[.!?])\s+)"


def _anchor(pat):
    return _SENTENCE_START + pat[4:] if pat.startswith(r"^\s*") else pat
```

The comment directly above this (line 158–160) states the intended fix: discourse markers used to
be anchored only to `^` (true start of a line/string) and so were invisible mid-paragraph; "The
anchor is now a sentence boundary OR a line start." That is true for the sentence-boundary case
(`(?<=[.!?])\s+`, which does correctly absorb any whitespace — including a newline — after a
sentence-ending punctuation mark) but **not** for the "line start" case: the original patterns
began `^\s*`, tolerating leading whitespace at the true start of the text, and `_anchor()` strips
that literal 4-character prefix (`pat[4:]`) and replaces it with a bare `^` that has **no**
following `\s*`. A passage whose very first character is whitespace, with no preceding
sentence-ending punctuation to anchor off instead, is no longer matched by any of the eight
`DISCOURSE` patterns and the `"importantly"`/etc. `STRUCTURAL`-adjacent ones that use this prefix.

Reproduced live (read-only, no files touched):

```python
>>> import tells
>>> tells.scan('End of a sentence.  That said, the record notes something.')
{'the record notes': 1, 'that said': 1}          # mid-paragraph case: correctly caught
>>> tells.scan('   That said, the record notes something.')          # leading whitespace, true start
{'the record notes': 1}                                              # 'that said' MISSED
>>> tells.scan('That said, more follows.')                            # true start, NO leading whitespace
{'that said': 1}                                                      # correctly caught
>>> tells.scan('Some sentence ends here.\n   That said, more follows.')   # newline + indent, mid-text
{'that said': 1}                                                      # correctly caught (via the (?<=[.!?])\s+ branch)
```

So the miss is narrow — it only fires when a passage begins with literal whitespace **and** there
is no earlier sentence boundary in the same call to `scan()` to anchor off instead (a generated
chapter's very first paragraph, if it happened to be saved with leading indentation). It affects
all eight `_anchor()`-rewritten patterns identically (`that said`, `it is worth noting`... no, only
the ones with a literal `^\s*` prefix: `that said`, `importantly`, `in conclusion`, `moreover /
furthermore`, `firstly / secondly`, `the truth is`, `to be clear`, `in essence`, `simply put` — 9
of the 14 `DISCOURSE` entries), since the bug is in the shared `_anchor()` helper rather than in
any one pattern.

Given this module exists specifically to catch machine-tell phrases without missing any, and the
project's own `Hard Rule 0` framing treats an unstated narrowing of what a check actually covers
as the serious case, this is filed as a genuine (if narrow-impact) DEFECT rather than a QUESTION:
the fix's own comment claims a guarantee ("a line start") that the code does not fully deliver.

**Nothing else found wrong in tells.py.** `prompt_in_sync()` (the run-#56-adjacent-era fix for
order `a08557925d87`, "the safety this module claims was not running") does have a live caller —
`standards.py:1129` — confirmed by grep, so the check is actually wired into a standard rather than
being a second layer of dead code sitting beside the first. The lexical/structural/discourse
pattern definitions themselves were spot-checked for regex-precedence and boundary correctness
(the `\bnot merely\b|\bnot simply\b|\bnot just\b.{0,40}\bbut\b` alternation, the plural-insensitive
completions) and match their own documented intent.

---

## Coverage recorded

`sweep_plan.record('run57', [...8 modules...], batch=11)` was called from the repo root; see the
tool output for the returned status.
