# AUDIT — sweep43, batch 05

Files read in full: `src/cascade_bridge.py` (2047 lines), `src/ledger_guard.py` (767 lines),
`src/secondopinion.py` (622 lines), `src/reference.py` (485 lines), `src/burgs.py` (402 lines),
`src/catalogue_aurora.py` (325 lines), `src/scope.py` (276 lines), `src/repass_bands.py`
(155 lines), `src/lognames.py` (53 lines).

Every finding below was checked against the source and, where practical, proven with a small
read-only reproduction (shown inline). No file was edited. The standing open question about
`cascade_bridge.py` re-dispatching to a bucket that just said "retry in 499s" is NOT re-filed
here per instructions.

General note: all nine files are already extremely heavily audited — most contain dense
in-source commentary documenting a long chain of prior sweep fixes. The five findings below are
what survived actually re-deriving the runtime behaviour rather than trusting the comments.

---

## src/ledger_guard.py

### MAJOR — `_lost_fraction` measures distinct-line loss, not content loss, and the real ledger already sits close to the cliff

`src/ledger_guard.py:372-385`

```python
def _lost_fraction(old, new):
    def body(t):
        return {ln.strip() for ln in (t or "").splitlines()
                if ln.strip() and set(ln.strip()) - set("-=*_# ")}
    was = body(old)
    if not was:
        return 0.0
    return len(was - body(new)) / len(was)
```

`body()` returns a **set** of distinct stripped lines, and the loss fraction is `|was - new| /
|was|` — set difference over set size. This is the fallback truncation detector
`check_since_snapshot()` uses whenever `check_append_only`'s strict containment/one-insertion
test fails (i.e. exactly the case this function exists to arbitrate: "was this an edit or a
truncation?").

Because it is set-based rather than multiset-based, any line that recurs verbatim across
multiple entries is only "lost" once ALL of its occurrences are gone. Proven with a read-only
repro (no files touched):

```
template = ["## Maintenance run", "- Status: OK", "- Notes: nothing to report", "- Next: continue"]
old = "\n".join(template * 100)     # 100 near-identical entries
new = "\n".join(template)           # 99 of 100 deleted, one survives

_lost_fraction(old, new) -> 0.0     # MAX_LOST_FRACTION is 0.05
```

99% of the ledger's actual entries were deleted and the function reports **zero** loss, because
every one of the four surviving lines already existed somewhere in `old`'s set. `check_since_snapshot`
would read this as "edited rather than appended to... under the truncation floor" and PASS —
letting `assert_intact()` clear a push that just destroyed 99 of 100 entries.

This is not a purely theoretical shape for this project's own ledgers. Measured against the live
files (read-only, `_lost_fraction`'s own `body()` filter applied):

```
HANDOFF.md               7,201 non-rule content lines, 7,120 distinct  -> 1.1% baseline duplication
handoff/HANDOFF.md         733 non-rule content lines,   700 distinct  -> 4.5% baseline duplication
```

`handoff/HANDOFF.md` — the newer of the two append-only ledgers, added 2026-08-31 specifically
because it carries "the project's deep engineering history, doctrine, and architecture" — is
already sitting at 4.5% baseline set-level duplication against a 5.0% detection floor. It does
not take an adversarial truncation to close that gap: ordinary growth of this file (which
itself repeats stock phrases like "silence.note", "a check that cannot fail looks exactly like a
check that passed", and specific order-id citation sentences) pushes the baseline duplication up
over time, shrinking the margin the truncation detector has to work with. A run that deletes a
block of genuinely unique entries while leaving behind even a modest number of boilerplate
lines that also appear elsewhere in the file could report under the 5% floor and pass.

The docstring's own stated reason for using set membership — "so a reordering or a reflowed
paragraph is not read as a loss" — is achieved just as well by counting occurrences (a multiset)
while still ignoring position; it does not require discarding occurrence counts entirely.

**Remedy (RUN, not LOCAL — needs verification against the two live ledgers before/after):**
replace the set-difference with a multiset (`collections.Counter`) comparison — e.g.
`sum(max(0, was_counts[ln] - new_counts[ln]) for ln in was_counts) / sum(was_counts.values())` —
which still tolerates reordering and reflowing but correctly counts a duplicated line's lost
occurrences rather than collapsing them to "still present somewhere."

---

## src/cascade_bridge.py

### MINOR — `_extract_json`'s brace counter is not string-aware and mis-parses valid JSON containing a literal `}`/`{` inside a string value

`src/cascade_bridge.py:184-199` (the non-fenced fallback path)

```python
start = text.find("{")
while start != -1:
    depth, i = 0, start
    while i < len(text):
        if text[i] == "{":
            depth += 1
        elif text[i] == "}":
            depth -= 1
            if depth == 0:
                try:
                    return json.loads(text[start:i + 1])
                ...
```

The depth counter treats every literal `{`/`}` character as a structural brace, including ones
that occur inside a JSON string value. Proven with a read-only repro:

```python
text = '{"feats": [{"sentence": "He shouted \'Get in the robot }\' before the launch.", "axis": "volition"}]}'
_extract_json(text)   # -> None
```

That text is valid JSON (`json.loads` on it directly succeeds); `_extract_json` returns `None`
because the `}` inside the quoted sentence closes the object early at the wrong offset, the
resulting slice is not valid JSON, `json.loads` raises, and the outer loop moves on to the next
`{` (none) without ever trying the *correct* closing brace.

Consequence, per the module's own docstring: "A reply that yields nothing parseable returns None
and is treated as a failed call." So a cloud model that correctly answers with a feat sentence
containing a brace character (plausible for a fiction quoting in-game HUD text, code, math, or
just a stray typographic aside) has its genuinely-correct answer discarded as a parse failure,
counted as `"unparseable reply"` with the reply recorded verbatim (not silently lost — the
failure is reported per `served["outcome"]`), and the caller retries or falls through. It is not
a silent-corruption bug, but it is a real, verified correctness defect in the single most
load-bearing module in this pipeline, and it wastes a claim/deadline on an answer that was
already correct.

Scope is narrower than it first looks: cloud replies wrapped in a ` ```json ` fence go through
`json.loads` directly (no brace counting) and are unaffected; only the un-fenced fallback path
is exposed, and the docstring already notes fenced replies are the common case for cloud models.

**Remedy (RUN):** use `json.JSONDecoder().raw_decode(text, idx)` at each candidate `{` offset
instead of a hand-rolled brace counter — it respects string escaping and returns both the parsed
value and the correct end offset in one call.

---

## src/secondopinion.py

### MINOR — `_vulture`'s line parser breaks on Windows absolute paths (drive-letter colon), masked by the existing rc/out cross-check

`src/secondopinion.py:280-291`

```python
for line in (r.stdout or "").splitlines():
    parts = line.split(":", 2)
    if len(parts) != 3:
        continue
    try:
        lineno = int(parts[1])
    except ValueError:
        continue
```

Vulture's own output format varies with the caller's working directory: when invoked from
inside the scanned tree it prints paths relative to cwd (`src\foo.py:42: ...`); when invoked
from a cwd outside the tree it prints absolute Windows paths (`C:\Users\...\foo.py:42: ...`).
Proven directly against the installed binary, read-only:

```
cd panscriptum-library-kit && vulture "C:\...\src" --min-confidence 90
  -> src\verify_math.py:3020: unused variable 'socktype' (100% confidence)

cd /tmp && vulture "C:\...\src" --min-confidence 90
  -> C:\Users\imarl\panscriptum-library-kit\src\verify_math.py:3020: unused variable 'socktype' (100% confidence)
```

`"C:\...\foo.py:3020: msg".split(":", 2)` yields `["C", "\...\foo.py", "3020: msg"]` — the
drive-letter colon consumes the split point meant for the line-number separator, `parts[1]` is
a path string, `int(parts[1])` raises `ValueError`, and the finding line is dropped without a
`silence.note` or any other trace.

**This is bounded, not silent-clean, given the existing safeguard**: `_vulture`'s own
returncode/output cross-check —
`if r.returncode not in (0, 1, 3) or (r.returncode in (1, 3) and not out): return "TOOL ERROR"` —
already catches the all-lines-unparseable case (rc=3, `out=[]`) and reports it as `TOOL ERROR`,
which `report()` prints as `<-- NOT AN ALL-CLEAR`, not as a clean pass. So under the documented
usage pattern (run from the repo root per CLAUDE.md's `cd panscriptum-library-kit`), this is
inert; if secondopinion.py is ever invoked from a different working directory (a scheduled task,
a different launcher), vulture's real findings go dark and are misreported as a generic tool
error rather than the actual findings it produced.

**Remedy (LOCAL):** parse on `re.match(r"^(.*):(\d+):\s*(.*)$", line)` (greedy `.*` up to the
*last* `:digits:` pair) instead of a fixed `split(":", 2)`, so a drive letter earlier in the
string cannot be mistaken for the line-number delimiter.

---

## src/repass_bands.py

### MAJOR — Hard Rule 0: the SURVIVORS console list stays capped at 14 despite its own sibling being uncapped in the same file's history

`src/repass_bands.py:115-124`

```python
_survivors_shown = kept_entries[:14]
if len(_survivors_shown) < len(kept_entries):
    print(f"\n  SURVIVORS — each is an act upon an object, or a measured quantity "
          f"(showing {len(_survivors_shown)} of {len(kept_entries):,}; "
          f"{len(kept_entries) - len(_survivors_shown):,} more not shown):")
```

This is a `[:N]` truncation of an ordered entry listing — exactly the shape Hard Rule 0 names.
The comment directly above it (order 89fc2eaf23f1) records that this exact list used to claim
"every one of these" over a slice of fourteen, and that the fix applied was to make the label
honest about the cut rather than to remove the cut. The comment at line 126, describing the
sibling DEMOTED list a few lines further down in the same file, records that list's identical
disease being cured completely — capped-with-a-false-label became fully uncapped, printing
every entry. The SURVIVORS list was left as "disclosed but still capped," which is inconsistent
within the same script and, per CLAUDE.md's own zero-tolerance wording ("No limit, no cap, no
sample... Ranking then truncating is not [allowed]"), still a fault: the console line is a
console display (the "lesser instance" the rule names), but there is no other output anywhere
in this run that carries the full SURVIVORS roster — only `kept_entries` in memory, which is
gone when the process exits.

**Remedy (LOCAL, mechanical):** delete the `[:14]` slice and print every row, exactly matching
the fix already applied a few lines below to the DEMOTED list in the same function.

---

## src/burgs.py

### MINOR — `burgs_for(..., limit=0)` silently returns the FULL roster instead of an empty one (truthiness bug)

`src/burgs.py:242`

```python
for k in range(1, (limit or n) + 1):
```

`limit or n` treats an explicit `limit=0` the same as `limit=None` (both falsy), so a caller
that means "give me zero burgs" gets the entire roster instead. Proven read-only:

```python
burgs_for(12345, {...})            # -> 507 rows
burgs_for(12345, {...}, limit=0)   # -> 507 rows (expected 0)
```

Low real-world exposure — the only caller, `main()`'s `--limit` argparse flag defaults to
`None` and nobody has an obvious reason to pass `--limit 0` — but it is a genuine logic defect
of exactly the "truthiness vs. `is not None`" shape this project's own commentary calls out
repeatedly elsewhere in this same codebase as a recurring, worth-fixing bug class.

**Remedy (LOCAL):** `range(1, (limit if limit is not None else n) + 1)`.

---

## Modules read and found clean (on the specific things checked)

- **src/lognames.py** — the `OWNER` dispatch-fragment table was cross-checked against the actual
  `argparse` flags in `read.py`, `feats.py`, `pipeline.py`, `catalogue_web.py` and `magnitude.py`;
  every fragment matches a real, currently-registered flag. No drift found.
- **src/reference.py** — `compute()`/`card()` were run read-only (no `main()`, no write) against
  the three hardcoded worksheets; all three land inside their charter's published interval
  (Goku delta 0.18/0.41, Naruto delta 0.25/0.30, Luffy delta 0.40/0.55), confirming the file is
  currently self-consistent with `assay.py`'s live weights and ladder. `shelfmark()`'s
  defensive clamp for an over-long rung list was traced and is correct (verified the pre/post
  truncation ordering does not desync `upper`/`lower`).
- **src/catalogue_aurora.py** — dedup key, slug/record-path legacy-fallback resolution, and the
  write/roll compare-and-swap gating were traced end to end; all match their documented intent.
- **src/scope.py** — the highest-tier-clears-floor selection loop, the PROBE_VERSION-based
  re-probe selection, and the empty-vs-failed-probe caching distinction were traced and are
  correct.

---

## QUESTIONS (for the OWNER, not findings)

None this batch. Every candidate ambiguity resolved cleanly to either "correct as designed" or
a provable defect above; nothing here is a genuine judgment call between two defensible readings.
