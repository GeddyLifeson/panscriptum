# AUDIT — batch04, run31

Modules: `src/foreman.py` (1358 lines), `src/health.py` (428 lines), `src/pantheon.py` (308
lines), `src/feats_index.py` (263 lines), `src/cleanup.py` (215 lines), `src/ledger_guard.py`
(143 lines). Total lines read: **2715 / 2715** (every line of every assigned module read).

Read-only audit. No files were edited except this report. No long-running or state-mutating
script was executed; two small read-only greps against `feats.py`, `pipeline.py`, `overwatch.py`
and `BUGS.md` were run to confirm cross-module claims (host-API design, symbol naming
convention, real BUGS.md section order) before writing findings that depend on them.

Both modules' own extensive self-documentation (run #19, #26, #27, #29, m18, m100, etc.) already
records a long history of prior fixes; this audit tries hard not to re-report those. Everything
below is either new or a gap the existing self-documentation does not mention.

---

## foreman.py

### F1 — Hard Rule 0: `scout_hostless` caps the hostless-source queue to 4 per round, ranked-then-truncated
**foreman.py:192**, calling into **scout.py:238-241**.

```python
# foreman.py:192
res = SC.sweep(limit=4)
```
```python
# scout.py:237-241
def sweep(limit=None, register=True):
    todo = hostless()
    order = sorted(todo, key=lambda s: -len(todo[s]))
    if limit:
        order = order[:limit]
```
`order` is sorted richest-first, then truncated to the top 4. This is exactly the shape the
project's own Hard Rule 0 forbids in the CLAUDE.md text: "Ranking is still allowed and is
encouraged... **Ranking then truncating is not.**" Sources ranked 5th and below by hostless-page
count are never scouted in a given round. Because the ranking key (`-len(todo[s])`) is
deterministic and `todo` only changes when a source's host is actually adopted, a source that
keeps failing to find a host (the common case — most of `SCOUT_BLOCKED.json` exists precisely
because scouting failed) stays in the top-4 forever and the 5th+ ranked sources are never
reached by this remedy, across any number of rounds, until every one of the top 4 succeeds.
Failure scenario: 6 hostless sources exist; the top 4 by page-count are storefronts that will
never yield a scoutable host (see `owner_queue`'s own `SCOUT_BLOCKED.json` handling, which
exists for exactly this situation); sources 5 and 6 are never scouted by any foreman round.
Severity: **major** (Hard Rule 0 is the project's own top-priority invariant; this is its exact
shape — "ranking then truncating"). Confidence: **VERIFIED** (traced both files).

### F2 — `_function_source` can silently patch the wrong function when a finding names `Class.method`
**foreman.py:858-871**

```python
def _function_source(path, symbol):
    ...
    want = symbol.split("(")[0].split(".")[-1].strip()
    for node in _ast.walk(tree):
        if isinstance(node, (_ast.FunctionDef, _ast.AsyncFunctionDef)) and node.name == want:
            ...
            return "".join(lines[start:end]), start, end
    return None, None, None
```
`symbol.split(".")[-1]` **discards any class qualifier**, keeping only the bare method name.
`ast.walk` is then matched purely on `node.name == want`, with no regard for which class (if
any) contains it, and returns the **first** match found by `ast.walk`'s traversal order.
`overwatch.py:122` defines `symbol` as free text — "the exact function, variable or attribute
involved" — model-generated, and a natural value for a method is a dotted `ClassName.method`.
Failure scenario: a module defines `class A: def check(self): ...` and, later in the file,
`class B: def check(self): ...`. A finding names `symbol="B.check"`. `_function_source` strips
the `B.` and returns **`A.check`**'s source instead. `attempt_patch` then asks the model to
"fix" `A.check` using a claim that was actually about `B.check`, and — if the model complies and
`_checks_pass` passes (which it can, since `A.check` still imports and the test suites may not
happen to exercise the exact regression) — **writes the patch into the wrong function** in live
source. This is the exact failure class the module's own 56-line docstring spends most of its
length warning about ("a model editing a live codebase unsupervised... the same defect class
that produced eighteen silent faults would produce silent patches"), and the guard fenced
against it (DENYLIST, regex-touch refusal, `verify_math`, `allsweep --quick`) does not catch a
patch to the *wrong but syntactically fine* function. Severity: **blocking** (the model-patch
lane is designed with more scrutiny than a human patch specifically because it is unsupervised;
this defeats targeting, not just validation). Confidence: **VERIFIED** the code path exists;
**HYPOTHESIS** that a same-named-method collision has actually occurred in this codebase yet.

### F3 — `attempt_patch`'s live-file write is a non-atomic, unlocked write to a src/*.py file other processes may be importing
**foreman.py:1052-1060**

```python
with open(path, encoding="utf-8") as f:
    lines = f.readlines()
lines[start:end] = [new]
with open(path, "w", encoding="utf-8") as f:
    f.writelines(lines)
```
Unlike every state/records write in this batch (all correctly routed through
`silence.replace_retry`), the patch write to the live module is a bare truncating `open(path,
"w")` with no temp-file-plus-rename and no lock. A concurrently running process (the supervisor,
a worker importing this exact module mid-write) can observe a partially-written file and hit
`SyntaxError`/`ImportError` for the wedge duration. The backup/revert machinery around it
protects against a *bad* patch, not against another reader mid-write. Severity: **minor** (the
window is narrow and the design already treats this as a heavily-supervised operation).
Confidence: VERIFIED code shape, HYPOTHESIS on real-world collision odds.

### F4 — `clear_learned_caps` leaks its sqlite connections
**foreman.py:120-132**. `c = sqlite3.connect(db)` is opened for each of up to two DB files and
never `c.close()`d on either the success or exception path. Harmless in a short-lived process,
but sloppy given `cascade_scratch.db` is explicitly called out elsewhere in the file as a
high-traffic shared file. Severity: **cosmetic**. Confidence: VERIFIED.

---

## health.py

### H1 — `flush()`'s sample-write failure path is a bare `except: pass` with **no** `silence.note()` call, inside the module whose entire purpose is "nothing raises, nothing counts is the real bug"
**health.py:141-144**

```python
if silence.replace_retry(stmp, SAMPLES_PATH):
    _SAMPLES.clear()
except Exception:
    pass          # the evidence bag must never break the ledger write
```
Every other exception handler in this file (and in every other module in this batch) calls
`silence.note(...)` so the failure at least lands in the very ledger this module maintains. This
one does not. If `SAMPLES_PATH` is corrupt, or the disk write fails, or `json.load` raises on a
torn read, the failure-samples evidence bag silently stops accumulating and **nothing anywhere
records that it happened** — not even health's own ledger, which is the one place in the whole
project built to catch exactly this shape. This directly contradicts the module docstring's
opening claim: "Eleven separate defects were found in one day... every layer converts a failure
into a plausible NEGATIVE RESULT... There are 45 bare `except Exception` handlers in this tree,
and that number is the real bug." This is a 46th, inside the file that exists to stop the other
45. Severity: **major**. Confidence: **VERIFIED**.

### H2 — `check_api_paths` still models host families as a wikipedia/fandom binary, which `feats.api()` has already moved past
**health.py:191-217**, cross-referenced against **feats.py:121-138**.

```python
# health.py:212
fams.setdefault("wikipedia" if "wikipedia" in h else "fandom", h)
```
Every host that isn't literally a `*wikipedia*` domain is bucketed as "fandom" and only **one**
representative host per bucket is ever probed (`setdefault` keeps only the first). But
`feats.py`'s own `api()` comment (feats.py:131-134) documents that this binary model was already
found wrong and replaced: *"a self-hosted MediaWiki (rimworldwiki.com serves /api.php but is not
Fandom) and an API-closed wiki (dandwiki.com answers every API call with 403) both mined to
exactly zero"* — `endpoint.api_url(host)` now probes each host's path individually rather than
assuming two families. `check_api_paths` was not updated to match: it still probes only one
arbitrary non-wikipedia host per preflight round and calls the result representative of every
other non-wikipedia host, so a specific broken third-party wiki (e.g. an API-closed one that
isn't the lucky host `fams.setdefault` happened to keep) can go down and this preflight will
never notice, because it never gets probed. Severity: **major** (silent preflight blind spot in
a check whose whole job is to catch exactly this class of host failure). Confidence:
**VERIFIED**.

### H3 — `check_caches` samples `files[:200]` per host directory and reports the result as if exhaustive within that sample
**health.py:241, 250-252**
```python
for fp in files[:200]:
    ...
n = min(len(files), 200)
if empty == n:
    out.append((f"{base}/{host}", f"all {n} sampled entries empty"))
```
Literally caps a "page list" per host — the letter of Hard Rule 0 ("no... sample... of a... page
list"). The output does correctly say "sampled" rather than claiming completeness, and this is a
diagnostic health check rather than the content pipeline itself, so the practical risk is low
(a host with >200 files, the first 200 of which are all empty while a later file happens to hold
real content, would be misreported as fully broken). Severity: **minor**. Confidence: VERIFIED.

### H4 — `reopen_stranded` is a read-modify-write on PIPELINE_STATE.json with no protection against a concurrent pipeline.py write
**health.py:322-364**. The function reads `PIPELINE_STATE.json` once (line 324-325), computes a
new `done["entrypass"]` list purely from that snapshot, and — if `--go` — writes the **whole
recomputed `st` dict** back via `silence.replace_retry` (atomic rename, but atomic replace of a
value computed from a stale read is still a lost-update race). The tool's own comment
acknowledges the danger context directly: *"it is invoked precisely when a pipeline may be
live, since that is when batches strand."* Any key `pipeline.py` itself writes into
`PIPELINE_STATE.json` between this tool's read and its write (a new `done` entry from a batch
that finished during that window, a new `failed` entry, etc.) is silently discarded by this
tool's blind write-back. Severity: **major** (data loss against the single most important state
file in the kit, in the exact situation the tool says it is meant to run in). Confidence:
VERIFIED code shape; HYPOTHESIS that the race window has actually been hit in practice.

### H5 — `summary()` has no exception handling, unlike every other read in this module
**health.py:147-151**. A corrupt or momentarily-torn `LEDGER_PATH` (e.g. read mid another
process's `replace_retry` swap, or a `.corrupt`-renamed file the JSON loader chokes on) raises
an unhandled `JSONDecodeError` straight out of `--failures`, rather than being reported the way
every other read failure in this file is (`silence.note` + a graceful fallback). Severity:
**cosmetic/minor**. Confidence: VERIFIED.

---

## pantheon.py

No correctness, swallowed-failure, cap, concurrency, or tautology findings. `OUT` is written via
`silence.write_json` (two-writer contract honored). Data-only content (hand-authored God stat
blocks) is out of scope for this lens. One trivial, not-worth-a-severity-tag observation: the
console-print `label` dict at pantheon.py:282-283 only covers M2-M4 and M7-M8 — a merged
`Z_FIGHTERS.json` entry at, say, M5 or M6 prints an empty label. Cosmetic, harmless
(`.get(b, "")`), not filed as a numbered finding.

---

## feats_index.py

### FI1 — `entries_by_norm.setdefault` silently drops the join for a same-normalized-name duplicate entry within one source
**feats_index.py:186-188**
```python
entries_by_norm = {}
for e in (record.get("entries") or []):
    entries_by_norm.setdefault(_norm(e.get("name")), e)
```
If a single source's own `entries` list contains two entries whose names fold to the same
normalized key (a data-quality duplicate that slipped past upstream dedup, or two names that
differ only in punctuation `_norm` strips), only the first survives in `entries_by_norm`; any
feats record matching that normalized name attaches only to the first entry, and the second
entry's own feats-eligibility is silently lost (it can never be joined even if it has its own
separately-mined feats record, since `feats_for_source` only ever emits one row per
`(host, ent_norm)` pair anyway — but if the two catalogue entries are genuinely different things
sharing a normalized name, this is a real conflation, not just an inefficiency). Severity:
**minor**. Confidence: HYPOTHESIS (requires an actual same-normalized-name duplicate within one
source's entries to manifest; not confirmed against real data in this read-only pass).

Everything else in this module — the NO CAPS claim in `feats_for_source` (verified: no
truncation anywhere in the function, matches the docstring), `_norm`'s deliberately-strict
folding (matches its own extensively self-corrected docstring), `audit()`'s counting — checked
out clean.

---

## cleanup.py

### C1 — `clean_ceiling`'s "prefix" strategy can silently pick the wrong entity when two catalogued names share a prefix
**cleanup.py:116-119**
```python
low_pref = [n for n in entry_names
            if n.lower().startswith(ce.lower()) and len(ce) >= 6]
if len(low_pref) >= 1:
    return min(low_pref, key=len), "prefix"
```
By the time this runs, the exact-match branch has already ruled out `ce` being a literal
catalogued name, so every candidate in `low_pref` is a *longer* name that merely starts with
`ce`. When more than one catalogued entry shares that prefix — e.g. two disambiguated forms of
the same base name — the shortest one is chosen with `min(key=len)` and **no check that it is
the correct referent**. `feats_index.py`'s own docstring (feats_index.py:39-43) documents this
exact shape as a real, measured case in this data: `Wally West (New Earth)` and `Wally West
(Prime Earth)` are two different DC continuities, both cataloged, both legitimately different
entities — if a source's ceiling-entity prose ever read simply "Wally West", both names would
match the prefix test here and one would be picked arbitrarily by string length, contradicting
the function's own docstring claim that prefix-matching "is safe" because "a name cannot prefix
an unrelated entity by accident the way it can appear inside one" — that claim covers a name
appearing as a substring, not two *different* same-prefixed names both being real entries.
Severity: **major** (silently mis-attributes a ceiling entity — the thing every downstream Assay
score keys off — to a specific, possibly-wrong character/continuity, and does so quietly:
`clean_ceiling` reports this as a confident "prefix" match, not an "unresolved" one, so it never
surfaces in the `ceil_unres` report for a human to catch). Confidence: VERIFIED the code path;
HYPOTHESIS that `len(low_pref) > 1` has actually occurred for any real ceiling entity (not run
against live data in this read-only pass).

### C2 — Dead guard entry for `_SETTING_META`
**cleanup.py:77-80**
```python
for _n, _p in (("_NAV", _NAV), ("_EMPTY_MECHANIC", _EMPTY_MECHANIC),
               ("_SETTING_META", None)):
    if _p is not None and any(ord(c) < 32 for c in _p.pattern):
        raise SystemExit(...)
```
`_SETTING_META` is not defined anywhere in `cleanup.py` — it is a regex that lives in
`pipeline.py` (pipeline.py:1012). The tuple entry here is permanently `None`, so `_p is not
None` is always false for it and the guard **never actually checks anything** for that name; it
is a phantom guard (LENS 7) — dead code that looks like a third net but is inert. Not a live
safety gap: confirmed `pipeline.py` has its own independent whole-file `_BAD_CHARS` scan
(pipeline.py:85-87) that would already catch corruption in `_SETTING_META`'s pattern, so no
actual coverage is lost. Severity: **cosmetic**. Confidence: VERIFIED (grepped `pipeline.py` to
confirm the independent guard exists).

Everything else — `clean_description`'s markup regex list, the `_NAV` scaffolding-vs-in-universe
guard, the `changed=True` on the thin-description branch (this batch found it already correctly
set — matches the file's own comment crediting run #29/batch 05 for fixing exactly that), the
records write going through `PL.write_record` — checked out clean. Console-print truncations
(`nav[:5]`, `ceil_fixed[:6]`, etc.) are sample previews only; every counted total and every
`--apply` mutation covers the full, untruncated set.

---

## ledger_guard.py

### L1 — `assert_intact()` discards `seal()`'s return value, so a failed chain-append is reported as "ledgers intact"
**ledger_guard.py:207-225**, specifically line 224.
```python
def assert_intact():
    ...
    ok, problems = verify_chain()
    if not ok:
        raise LedgerViolation(...)
    seal()
    return True
```
`seal()` (ledger_guard.py:120-157) itself swallows any write failure — the `try/except Exception:
return None` around the actual append at lines 151-156 — and returns `None` on failure with no
`silence.note()` or any other record. `assert_intact()` does not check that return value at all;
it always returns `True` after calling `seal()`, regardless of whether the append succeeded.
Given the docstring's own claim that this hash chain is *the only mechanism* that can detect an
out-of-band edit between runs ("A hash chain answers it... `check_append_only`... only if it is
called... `check_structure`... proves the file parses. Neither can answer... did anything change
these files between the last run and this one"), a `seal()` failure here means the chain quietly
stops being extended while `assert_intact()` — "called by `publish` before anything is pushed" —
keeps reporting success. A later run's `verify_chain()` would still nominally validate (the
existing links are all still self-consistent), so there is no alarm; the chain has simply gone
stale and stopped watching. Severity: **blocking** (this is the publish-time gate itself,
silently degrading to a no-op on its one irreplaceable check). Confidence: **VERIFIED**.

### L2 — `CHAIN` is written by a bare append `open()`, not through the mandated atomic-write helpers, and the read-prev-then-append sequence races across concurrent `seal()` calls
**ledger_guard.py:153** (`f.write(json.dumps(rec, ...) + "\n")` inside `with open(CHAIN, "a",
encoding="utf-8") as f`). `state/ledger_chain.jsonl` is a shared state file read by
`read_chain()`/`verify_chain()` and written by `seal()`, yet it never goes through
`silence.replace_retry` or `silence.write_json` — the two-writer contract's mandated path for
shared state files. Beyond the contract violation itself, `seal()`'s sequence at lines 141-150
(`read_chain()` to get `prev`, then build `rec`, then append) is not protected by any lock: two
processes calling `seal()` around the same time can both read the same last link as `prev` and
each append a new link claiming that same `prev`, forking the chain. `verify_chain()` would
eventually notice one of the two as "does not follow" the other, but only on the **next** run
that reads both — and by then it cannot tell which of the two forked links (if either) reflects
real tampering versus an honest race. Severity: **major**. Confidence: VERIFIED code shape;
HYPOTHESIS that two `seal()` calls have actually overlapped in practice (depends on whether more
than one process ever calls `assert_intact()`/`seal()` concurrently, which is plausible given
multiple publish-adjacent entry points in this project).

### L3 — The Open/Resolved duplicate-bug-id check silently goes dark if the sections are ever reordered
**ledger_guard.py:89-98**
```python
i, j = text.find("## Open"), text.find("## Resolved")
watch = text.find("## Watching")
op = text[i:(watch if 0 < watch < j else j)]
res = text[j:]
```
This assumes `"## Open"` occurs before `"## Resolved"` (`i < j`) and never checks it. If that
assumption is ever wrong — sections reordered, or a "## Resolved" appearing before an "## Open"
for any reason — `text[i:j]` (or `text[i:watch]`) becomes an **empty string** because Python
slicing with `start > stop` yields `""`, silently emptying the `op`/`res` sets the whole check
is built on; the cross-check then finds no shared ids and reports nothing, even if real
duplicate bug ids exist. Confirmed against the actual repo state
(`grep -n "^## " BUGS.md` -> `## Open` at line 7, `## Watching (...)` at line 1552, `## Resolved
(...)` at line 1572): the assumption currently holds, so this is **latent, not firing**, but the
code has no assertion protecting it and would fail exactly the way its own docstring warns other
checks fail ("indistinguishable from a healthy one"). Severity: **minor**. Confidence: VERIFIED
code shape and current non-triggering; the failure mode itself is HYPOTHESIS pending a future
reorder.

### L4 — `seal()` reads each ledger file twice to build one record, an unlocked TOCTOU on the exact files this module exists to protect
**ledger_guard.py:147**
```python
"ledgers": {n: {"digest": _digest(_read(n) or ""), "bytes": len((_read(n) or ""))}
            for n in sorted(MIN_BYTES)}
```
`_read(n)` is called once for the digest and again for the length, with no snapshot in between.
If a ledger file is modified between the two reads (a concurrent writer touching `HANDOFF.md`
mid-`seal()`), the recorded digest and the recorded byte count can describe two different
versions of the file, producing a self-consistent-looking but factually mismatched chain link —
undermining the tamper-evidence property on the one file class this module was built to get
right. Severity: **minor**. Confidence: VERIFIED code shape; HYPOTHESIS on real-world timing.

### L5 — The `"bytes"` field in each chain link is actually a character count, not a byte count
**ledger_guard.py:147** vs **ledger_guard.py:83-85**. `seal()` records `len((_read(n) or ""))` —
`len()` of a Python `str` is character count. `check_structure`'s `MIN_BYTES` floor, by contrast,
correctly measures `len(text.encode("utf-8"))`. These markdown ledgers are full of multi-byte
characters (em dashes "—" appear throughout this very module's own docstring, and elsewhere in
the project's prose), so the two "bytes" quantities are computed differently and the field name
in the chain link is not what it claims to be. Functionally harmless today — `verify_chain()`'s
SHRANK check only ever compares this field against its own prior value, not against
`MIN_BYTES` — but the mislabeling is real and would mislead anyone reading `ledger_chain.jsonl`
directly, or extending `verify_chain()` to check against the byte floors later. Severity:
**cosmetic**. Confidence: VERIFIED.

---

## Note on a false start

An initial full-file `Read` of `ledger_guard.py` appeared to omit `import json` from the top of
the file (module-level imports rendered as only `import os` / `import re`), which would have
been a **blocking** finding (`NameError` on every `seal()`/`read_chain()`/`verify_chain()` call).
A second, targeted re-read plus `grep -n "^import"` confirmed `import json` is present at line
30 and the first read was simply a transcription error on my part. Recorded here per the
project's own standing lesson about not trusting an unverified read of one's own tooling —
flagged and corrected before it reached this report, not after.
