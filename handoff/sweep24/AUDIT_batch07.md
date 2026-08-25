# Sweep 24 — Batch 07 Audit

**Files in batch:** `src/cascade_bridge.py`, `src/allsweep.py`, `src/tiers.py`, `src/backfill.py`,
`src/tells.py`, `src/sweep_plan.py`

**Coverage:** all six files read in full, every line, via the `Read` tool in overlapping
windows (no gaps). Line counts: cascade_bridge.py 999, allsweep.py 447, tiers.py 347,
backfill.py 258, tells.py 215, sweep_plan.py 161 — 2,427 lines total. Findings below were
additionally cross-checked against the live state of `state/POOL_UNRECOGNISED.json` (48 rows,
read directly) to confirm the cascade_bridge.py findings against real data rather than
inferring from code alone.

---

## cascade_bridge.py

### 1. `POOL_UNRECOGNISED.json` double-counts on a case-sensitivity fracture — MAJOR — **VERIFIED**

`cascade_bridge.py:822`
```python
err = (box.get("error") or "").lower()
```
`cascade_bridge.py:873`
```python
record_unrecognised(pinned.bucket, err or box.get("error") or "")
```
`err` is built by lower-casing `box["error"]` at line 822 (for case-insensitive classifier
matching — comment at 813: "Matching is case-folded because providers do not agree on
capitalisation"), and every subsequent reassignment of `err` (line 844, `deeper =
provider_error(pinned.bucket).lower()`) is *also* lower-cased. Because `err` is non-empty
whenever `box["error"]` is non-empty, the fallback `box.get("error")` at line 873 is
**never actually reached in practice** — the ledger key/text is always the lower-cased
string, under the code as it stands right now.

The live double-counting is therefore not an ongoing per-call flip-flop — it is a scar left by
the moment this `.lower()` was introduced. I pulled `state/POOL_UNRECOGNISED.json` directly and
checked `first_seen`/`last_seen` on the case-pair rows:

```
1.78h last  1.99h first  count=2  cerebras:free|Every model in this pool is rate limited or unconfigured.
1.00h last  1.63h first  count=3  cerebras:free|every model in this pool is rate limited or unconfigured.
1.78h last  1.99h first  count=4  gemini:models/gemini-2.5-flash-lite|Every model in this pool is rate limited or unconfigured.
1.00h last  1.63h first  count=5  gemini:models/gemini-2.5-flash-lite|every model in this pool is rate limited or unconfigured.
... (6 more pairs, same pattern)
```
Every capitalised-key row stopped being written at ~1.78h ago and every lower-case-key row for
the *same bucket and the same fault* started immediately after, at ~1.63–1.78h ago, and is still
being written (as recently as 1.00h ago). That is the exact moment the `.lower()` at line 822
went live: after it landed, the identical fault started keying into a *new* row instead of
incrementing the old one, and nothing ever merges, renames, or retires the orphaned old-case row.
Right now **8 of the 48 rows in the ledger are pure case-duplicates of another row** (verified by
grouping on `(bucket, text.lower())`), each pair silently splitting one recurring fault's count
across two "open" entries that `standards.py` (line 937, `_CB.unrecognised_open()`) will both
report.

**Concrete failure:** any dashboard/`standards` metric built on `len(unrecognised_open())` or on
per-row `count` for "how many times has this fault fired" currently overstates the number of
*distinct* unrecognised faults by 8, and undercounts how many times the single real fault (e.g.
`cerebras:free` reporting "every model in this pool is rate limited or unconfigured") actually
recurred, because its true occurrence count is split `2 + 3` etc. across two rows instead of
summed in one.

### 2. `unrecognised_open()` never re-triages — MAJOR — **VERIFIED**

`cascade_bridge.py:504-520`
```python
def unrecognised_open(max_age_h=24):
    ...
    with open(UNRECOGNISED, encoding="utf-8") as f:
        rows = json.load(f)
    cut = time.time() - max_age_h * 3600
    live = [r for r in rows.values()
            if isinstance(r, dict) and float(r.get("last_seen", 0)) >= cut]
    return sorted(live, key=lambda r: -float(r.get("last_seen", 0)))
```
This function (the only reader) applies nothing but a `last_seen` recency filter. It never
re-runs `named_transient()`/`pool_exhausted()` against a stored row's text to see whether
*today's* classifier would now recognise a fault that was unrecognised when first written.
Nothing else in the codebase does either — `record_unrecognised` (`cascade_bridge.py:458-501`)
only ever adds/updates rows, and grepping the whole `src/` tree for `POOL_UNRECOGNISED` /
`unrecognised_open` turns up exactly one writer and one reader, neither of which deletes or
reclassifies anything. A row, once written, is permanent until it ages out of the 24h window on
its own **and stops recurring** — if the same literal text keeps arriving (because whatever
produces it upstream hasn't changed), `last_seen` keeps refreshing and the row never ages out at
all, however wrong its classification has become.

**Live proof that this already happened**, not just a hypothetical: the ledger currently holds
"exhausted-pool" rows this session's own `pool_exhausted()` (added earlier today, referenced in
the big comment block at `cascade_bridge.py:339-403`, "Found 2026-08-25 (run #23)") would now
correctly suppress:
```
1.78h last  count=3  cerebras:free|All 10 candidates failed: GLM 4.7 (Cerebras), Codestral (Mistral), DeepSeek V3.2
1.8h last   count=1  groq:openai/gpt-oss-120b|All 11 candidates failed: GPT-OSS 120B (Groq), GLM 4.7 (Cerebras)...
```
I confirmed directly that `pool_exhausted()` on this exact text returns `True` (regex `\ball
(\d+) candidates failed\b` matches "10"/"11", both > 1) — meaning if this fault fired right now,
the classifier would route it to the `elif pinned and (exhausted or named_transient(err)): pass`
branch and it would **never** reach `record_unrecognised` at all. These rows are frozen at
~1.8-2h old — i.e. they were written in the window just before `pool_exhausted()` went live, and
have sat "open" and unre-examined ever since, because the file's `last_seen` timestamps stopped
advancing exactly when the classifier fix made them unreachable going forward. **What would have
cleared them:** nothing does, automatically. A maintenance pass that re-ran `named_transient`/
`pool_exhausted` over every stored row's `error` text and dropped/archived the ones that now
classify would clear both this case and the case-duplication in finding #1 — no such pass exists.

### 3. `record_unrecognised` can log a diagnostically-empty row — MINOR — **VERIFIED (code path); not yet observed live**

`cascade_bridge.py:822` / `:850-873`
```python
err = (box.get("error") or "").lower()
...
if pinned and not exhausted and (re.search(r"\b(401|402|403)\b", err)
                                 or any(w in err for w in permanent_words)):
    _bury(pinned.bucket, AUTH_BENCH)
elif pinned and (exhausted or named_transient(err)):
    pass
elif pinned:
    record_unrecognised(pinned.bucket, err or box.get("error") or "")
```
If `box["error"]` is `""` (reachable: `pump()` line 758 sets `box["error"] =
str(ev.get("error") or ev.get("text") or "")[:300]`, which is `""` if a provider's `type:"error"`
event carries neither field), then `err == ""`. None of the three branches' guards fire on empty
text (`pool_exhausted("")` is False, `named_transient("")` explicitly short-circuits to False at
line 423-424, and the regex/word checks against `""` are all False), so control falls through to
`elif pinned: record_unrecognised(...)` with `err or box.get("error") or ""` evaluating to `""`.
The row is recorded keyed `bucket + "|"` with `error: ""`, directly contradicting
`record_unrecognised`'s own docstring rationale ("Spotting it requires that it exist somewhere
... WITH ENOUGH TEXT TO CLASSIFY IT. A counter cannot be investigated; the error string can.").
Not currently present in the live ledger (checked: 0 of 48 rows have empty `error`), so this is a
latent gap rather than an active one — flagging because it's a real, reachable path that silently
produces the exact "counter with no text" failure the function exists to avoid.

### Classification order at ~842-873 for empty/None `box["error"]` — checked, clean

Traced every path that sets `box["error"]`: the `type:"error"` branch in `pump()` (line
756-759) and the `except` handler (line 760-771) both always assign a string (possibly `""`,
never `None`), and `err = (box.get("error") or "").lower()` at 822 safely handles the absent-key
case too. `pool_exhausted("")` and `named_transient("")` both degrade to `False` without raising.
No crash path found for empty/None `error` text; the only defect in this area is the empty-text
*recording* described in finding 3, not a classification-order fault.

---

## sweep_plan.py

### 4. `record()`'s lost-update fix does not cover the actual concurrency model — MAJOR — **VERIFIED**

`sweep_plan.py:81-113`
```python
_RECORD_LOCK = threading.Lock()

def record(run, covered):
    """...
    SERIALISED, because the whole point of this file is that sixteen batches run AT ONCE and
    each one reports its own coverage. The first version did an unguarded read-modify-write:
    two batches reading the same file, each adding its own modules, each writing back its own
    copy -- and the loser's modules vanish from the record. ...
    """
    with _RECORD_LOCK:
        try:
            with open(COVERAGE, encoding="utf-8") as f:
                data = json.load(f)
        except Exception:
            data = {}
        ...
        for m in covered:
            data[m] = {"run": run, "at": now}
        try:
            import silence
            silence.write_json(COVERAGE, data, indent=1, sort_keys=True)
        except Exception:
            tmp = "%s.%d.tmp" % (COVERAGE, os.getpid())
            ...
```
`_RECORD_LOCK` is a `threading.Lock`, which only orders callers within one Python process. The
docstring's own framing — "the whole point of this file is that sixteen batches run AT ONCE" —
describes 16 independently-launched sweep batches (this very audit is one of them, running as a
separate agent/process, not a thread inside a shared interpreter). Across separate OS processes,
`threading.Lock` provides zero mutual exclusion: two batch processes can both open and
`json.load()` `SWEEP_COVERAGE.json` before either has written back, each add their own `covered`
modules to their own in-memory `data` dict, and then each call `silence.write_json`/`os.replace`
— whichever writes second **overwrites the first process's additions wholesale**, because the
write is "whole dict out," not a merge. `silence.write_json`'s atomic `os.replace` only guarantees
no *reader* ever sees a torn/partial file mid-write; it does nothing to prevent this classic
cross-process lost-update, which is precisely the bug the docstring claims is fixed ("the loser's
modules vanish from the record"). This directly undermines `missing()` (`sweep_plan.py:116-125`),
whose entire purpose per the module docstring is "the proof that a sweep was complete" — a lost
update here can make `missing()` wrongly report a batch's modules as never covered (or, if the
timing goes the other way and a stale write clobbers a real gap-fill, mask a real one).
Reproducing this requires two batch processes calling `record()` within the same
read-then-write window, which is plausible whenever multiple sweep batches finish at close to the
same wall-clock moment — exactly the scenario 16-batches-at-once creates.

---

## allsweep.py

### `reconcile()`'s exception handlers — checked, clean (not a bug)

Every one of the seven `try/except Exception as e` blocks inside `reconcile()`
(`allsweep.py:165-318`) catches its own section's failure and calls `note(...)` with a
`"<section> reconciliation failed"` finding plus `type(e).__name__` and the message. Those
`note()` calls land in the `out` list `reconcile()` returns, which `main()` prints in full
(`allsweep.py:424-428`) and writes into `ALLSWEEP.json` verbatim (`allsweep.py:436-438`). A
failure inside any one reconciliation block is therefore visible to the caller and to the
written report, not swallowed — this "known suspect" did not pan out as a defect on direct
inspection.

### `NEVER_RUN` set is dead code — COSMETIC — **VERIFIED**

`allsweep.py:69-75` defines `NEVER_RUN`, a set of modules the comment says "are still IMPORT
checked; they are simply never invoked," implying some code path treats them specially. Grepped
the whole `src/` tree: `NEVER_RUN` is referenced nowhere else in `allsweep.py` or anywhere in the
project — it is assigned and never read. (It happens to be harmless, because `check_import()`
only ever runs `--help` on every module regardless of this set, so nothing is currently invoked
"for real" that shouldn't be — but the set's documented purpose is not enforced by any code, so
it's inert documentation dressed as a guard.)

---

## tiers.py — checked, clean

Read in full. The multiverse/metaverse/xenoverse cut ordering assertions
(`tiers.py:119-120`), the complete-linkage-vs-reachability distinction between `chart()`'s
multiverse computation (`W.components`, all-pairs) and `_components()` (single-linkage
reachability) for the other two cuts, and the xenoverse-level grounding vote in
`xenoverse_grounding()` (`tiers.py:150-186`) are all internally consistent with the file's own
stated design and with each other. No caps, no swallowed exceptions beyond the module's two
`silence.note()`-guarded config reads (both leave a benign empty-dict/None fallback, correctly
non-fatal for a diagnostic chart). No findings.

---

## backfill.py

### `roster()`'s subcategory walk is silently skipped for wikis with a substantial top-level listing — MAJOR — **VERIFIED (code logic)**

`backfill.py:79-94`
```python
for t in members("Category:Characters"):
    if t not in seen and not _NOT_A_CHARACTER.match(t):
        seen.add(t)
        out.append(t)
# One level down, for wikis that keep the roster in subcategories rather than the top.
if len(out) < 40:
    # Every subcategory. Twelve was a cap on an alphabetical listing, so a wiki that
    # files its roster under "Villains", "Heroes", "Kryptonians"... lost everything
    # after the twelfth letter of the alphabet.
    for sub in members("Category:Characters", "subcat"):
        for t in members(sub):
            if t not in seen and not _NOT_A_CHARACTER.match(t):
                seen.add(t)
                out.append(t)
        if limit and len(out) >= limit:
            break
```
The `len(out) < 40` gate assumes a wiki's roster lives *either* directly under
`Category:Characters` *or* in subcategories, never both. That is not how most wikis are
organised in practice: it is extremely common for a wiki to list a healthy number of characters
directly under the top category **and** additionally sort its full cast into subcategories
("Female characters", "Deceased characters", "Antagonists", etc. — this exact pattern is called
out by name in the code's own comment as the thing this file exists to catch). Any source whose
top-level listing already reaches 40 members skips the entire subcategory walk, silently
discarding every character that exists *only* in a subcategory — which is precisely the failure
shape this file's own docstring was written to repair (Goku, Kratos, Arthas falling outside a
window). This is a magic-number cap gating whether an entire branch of enumeration runs at all,
in a project under an explicit, repeatedly-stated "no caps, ever" rule, inside the very file
built to fix an earlier instance of this exact bug class. I did not run this against a live wiki
to measure how many sources are affected (that would require live MediaWiki calls against
`F.api`), so the *scale* of impact is unverified, but the code path itself is unambiguous.

---

## tells.py

### 5. Regex alternation precedence breaks the "not merely X but Y" structural check — MAJOR — **VERIFIED**

`tells.py:70`
```python
"not merely X but Y": r"\bnot merely\b|\bnot simply\b|\bnot just\b.{0,40}\bbut\b",
```
`|` has the lowest precedence in a regex, so this compiles as three fully independent
alternatives: `(\bnot merely\b)`, `(\bnot simply\b)`, `(\bnot just\b.{0,40}\bbut\b)`. Only the
third alternative ("not just") actually requires the trailing "but Y" that gives this tell its
name and its "reveal sentence" definition (per the module docstring: "STRUCTURAL sentence shapes
used as a reveal"). The first two match "not merely"/"not simply" **anywhere, with no "but"
required at all**. Confirmed directly:
```python
>>> pat = re.compile(r"\bnot merely\b|\bnot simply\b|\bnot just\b.{0,40}\bbut\b", re.I)
>>> bool(pat.search("The sword was not merely decorative."))
True   # no "but" anywhere in the sentence, still flagged as the reveal-shape tell
>>> bool(pat.search("She was not just tall."))
False  # the one branch that DOES require "but" correctly rejects this
```
Effect: any ordinary sentence containing a bare "not merely" or "not simply" — with no reveal
structure at all — is over-counted as a "not merely X but Y" structural machine-tell by every
consumer of `tells.scan()` (the style audit). This inflates the measured tell rate for prose that
does not actually exhibit the banned shape, undermining the frequency-based signal the module's
own docstring says is the point ("a single 'vibrant' in fifty thousand entries is not a defect" —
the rate has to be trustworthy for that reasoning to hold).

### Overlapping lexical entries double-count a single occurrence — MINOR — **VERIFIED**

`tells.py:45` lists `"myriad"`; `tells.py:53` separately lists `"myriad of"`. `tells.py:45` also
lists `"tapestry"`; `tells.py:62` (in `LEXICAL_FICTION`) separately lists `"tapestry of"`. Both
pairs are compiled into independent `\b...\b` patterns in `_LEX` (`tells.py:135`) and scanned
independently in `scan()` (`tells.py:144-155`). One occurrence of "a myriad of reasons" therefore
registers as **two** hits — `word: myriad` and `word: myriad of` — for a single instance of
machine-tell phrasing, inflating that word's measured rate versus every other lexical entry that
has no such overlapping bigram. Same mechanism for "tapestry"/"tapestry of".

---

## Summary of severities

- MAJOR, VERIFIED: cascade_bridge.py:822/873 (case-split double-counting, live-data confirmed)
- MAJOR, VERIFIED: cascade_bridge.py:504-520 (`unrecognised_open` never re-triages, live-data confirmed)
- MAJOR, VERIFIED: sweep_plan.py:81-113 (`record()`'s lock does not cover cross-process races)
- MAJOR, VERIFIED (logic): backfill.py:84-94 (`roster()` subcategory walk skipped above 40 top-level members)
- MAJOR, VERIFIED: tells.py:70 (regex alternation drops the "but Y" requirement for two of three alternatives)
- MINOR, VERIFIED (code path, not yet observed live): cascade_bridge.py:873 (empty-text ledger row possible)
- MINOR, VERIFIED: tells.py (overlapping lexical entries double-count: myriad/myriad of, tapestry/tapestry of)
- COSMETIC, VERIFIED: allsweep.py:69-75 (`NEVER_RUN` set unused anywhere)
- Checked, clean: cascade_bridge.py classification order for empty/None error text
- Checked, clean: allsweep.py `reconcile()` exception handlers (failures are visible, not swallowed)
- Checked, clean: tiers.py (full file, no findings)
