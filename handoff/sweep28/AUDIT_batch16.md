# Sweep #28 — Batch 16 audit

Modules (read every line, 2,489 total): `src/build_terminal.py` (579), `src/local_agent.py`
(579), `src/generate.py` (421), `src/ingest_doc.py` (302), `src/hosts.py` (253),
`src/chord_field.py` (204), `src/scope.py` (152).

`NEXT_STEPS.md` §3 read first. Known items for this batch: `local_agent.py:561`, `:406-407`,
`:446-476`; `ingest_doc.py:216`; `scope.py:106-114`, `:81`, `:86-93`. All verified against
current source below.

---

## 1. `src/local_agent.py` — THE SPECIAL-FOCUS QUESTION FIRST

**Question asked: given `:406-407` sets `modname=None` for any non-`.py` extension, exactly
which files can a local model write through `propose_patch` with no real content check?**

The file has been partially repaired since the `NEXT_STEPS.md` description was written (its own
inline comments at `:397-433` and `:380-390` narrate three earlier bypasses being closed run
#23-25). Current state, verified by reading `_gates()` (`:324-390`) and `t_propose_patch()`
(`:393-476`) line by line:

- The **module-name denylist** (`DENYLIST` = foreman/silence/health/allsweep/estate/verify_math/
  local_agent) still only matches `modname`, which is `None` for anything not ending `.py`
  (`:407`). The **path denylist** (`DENYLIST_PATHS`) is checked as a fallback (`:429-430`) — but
  it contains exactly **one entry: `"config.yaml"`**. So the module-name gate is structurally
  unable to protect any non-Python file, and the path gate protects only that one file.
- `_gates()` DOES now run a per-type parse check (`ast.parse`+pyflakes+import for `.py`,
  `json.load` for `.json`, `yaml.safe_load` for `.yaml`/`.yml`, `:341-379`) **and unconditionally
  runs the whole-suite `verify_math.py` gate for every file type** (`:380-390`) — this is new
  since the bug was filed and it does close the literal "skips all three gates" claim for the
  whole-suite half.
- But the whole-suite gate only catches damage that `verify_math.py`'s own checks happen to
  test. I grepped `verify_math.py` for every file this batch touches (`registry_terminal`,
  `.html`, `.js`, `NEXT_STEPS`, `HANDOFF`) and for every prompt filename: the **only** content it
  ever reads back is `prompts/system_style.txt`, and only for one narrow length/budget check
  (`verify_math.py:2230,2240`, "the system prompt is charged at the prose rate"). Nothing in
  `verify_math.py` inspects the actual prose/instructions of any `.md`, `.html`, `.js`, or the
  other three prompt files.

**Concrete answer:** for any file whose extension is not `.py`/`.json`/`.yaml`/`.yml`, and whose
repo-relative path is not literally `config.yaml`, `propose_patch` applies the edit with **zero
content-specific validation** — the sole surviving gate is "does `verify_math.py` still print
`0 FAILED` somewhere in its output", which for these files is true almost by construction. That
is, concretely:
  - `prompts/chapter_prompt.txt`, `prompts/frontmatter_prompt.txt`, `prompts/feats_prompt.txt` —
    **fully unchecked**. These are the templates that constrain every prose call the pipeline
    makes; a corrupted template changes what every future chapter says with no gate noticing.
  - `prompts/system_style.txt` — checked only for **rough length**, not content; a local model
    could invert "don't invent facts" into its opposite and keep the file within the length band
    the one check tests, and it would pass.
  - `registry_terminal/PANSCRIPTUM_TERMINAL.html` and its `d0.js`…`d6.js`/`names.js`/`lex.js`
    data files — **fully unchecked**.
  - Every `reference/keystone_volumes/*.md` file — including `00_MASTER_CHARTER.md`, the
    project's own charter — **fully unchecked**.
  - `CLAUDE.md`, `NEXT_STEPS.md`, `HANDOFF.md`, `BUGS.md` — **fully unchecked**.
  - Any `.json` file the module-denylist doesn't name — including **`data/records/*.json`**, the
    entity catalogue — passes with only a "still valid JSON" check, no schema/content check. This
    is a second, distinct problem: `propose_patch` is then a **third writer** to files the
    project's own two-writer contract says must go through `pipeline.write_record` /
    `write_record_catalogue` only (see finding 1b below).

Severity: **HIGH**, status: **NEW** (the specific enumeration and the system_style.txt nuance are
new; the underlying `modname=None` shape was already flagged, but as "skips the denylist and all
three gates", which is no longer literally accurate — the whole-suite gate does run. The real,
still-open hazard is narrower than the old description and broader in a different way: it's not
"no gate at all", it's "a gate that structurally cannot see the kind of damage these files can
take").

### 1a. `local_agent.py:561` — `json.dumps(res)[:SLICE]` still produces invalid JSON. **KNOWN, STILL OPEN.**

```python
messages.append({"role": "tool", "content": json.dumps(res)[:SLICE]})
```
Reproduced live: a `read_file` result near the `SLICE` (12000-char) boundary serializes to valid
JSON, then gets hard-cut mid-string:
```
truncated len 12000
INVALID JSON as expected: Unterminated string starting at: line 1 column 54 (char 53)
```
This is a *second* truncation on top of `t_read_file`'s own `SLICE`-sized `slice` field — the
dict wrapper (path/offset/`chars_after_slice`/`total_chars`) plus JSON escaping overhead pushes
the serialized size past `SLICE`, and the cut lands inside the string, not at a field boundary.
The fields that exist specifically to disclose "you have not seen everything" (`chars_after_slice`,
`total_chars`) are exactly the fields most likely to be the ones chopped off, since they come
last in the dict. This directly contradicts the module's own docstring promise: "iterative
reads, never a truncation" (`:11`) — `:561` is a truncation. `t_grep`'s hit list (uncapped per
Hard Rule 0, correctly) is exposed to the same cut for any grep with enough matches.

### 1b. `local_agent.py` propose_patch is a third writer to two-writer-contract-protected files. **NEW.**

Because `_safe()` (`:233-271`) permits any path inside the project except `.git` and NTFS/prefix
tricks, and the denylist only names seven `.py` modules plus `config.yaml`, `propose_patch` can
target `data/records/*.json`, `data/*.json` state files, etc. — files the project's contract says
are written only via `pipeline.write_record`/`write_record_catalogue` (records) or
`silence.replace_retry` (shared state). `propose_patch` writes them directly with `open(full,
"w")` (`:447-448`), gated only by "valid JSON" + "verify_math still 0 FAILED". A local-model task
asked to "fix a typo in an entity description" could take an exact-match find/replace straight
into a record file, bypassing the drift-merge and disk-wins logic `pipeline.write_record`
implements, and no audit trail beyond the `patches` log (`why`, `find[:200]`, `replace[:200]`)
would show it happened outside the sanctioned writer. Severity: MED-HIGH (real bypass, but
requires the local model to actually be *asked* to edit a data file, which is outside the
harness's stated purpose of "read, search, and gated writes on this repo" as a maintenance
agent — still worth a denylist-of-directories entry, e.g. `data/records/`, `data/*.json`).

### 1c. `local_agent.py:446-476` — no lock around write/gate/revert. **KNOWN, STILL OPEN.**

Confirmed by reading: `t_propose_patch` reads `original`, writes the patched text, runs `_gates`,
and on failure rewrites `backup` — with no file lock, no `threading.Lock`, no cross-process
mutex of any kind. Within one `run()` invocation this is safe (`run()`'s tool-call loop is
sequential). The exposure is **cross-process**: if the foreman or a supervisor ever dispatches
two `local_agent.py` subprocesses concurrently against overlapping targets, this is the failure
mode — process A reads `original` (v1), process B reads the same `original` (v1, stale the
instant A writes), A writes+gates+succeeds (file now v2), B then writes its own patch on top of
its stale v1 basis (clobbering v2), and if B's gate then fails, B "reverts" to **its own captured
`backup`**, which is v1 — silently destroying A's successful, already-verified patch. Nothing
outside this file establishes whether local_agent is ever invoked with real parallelism (that is
in `foreman.py`, outside this batch), so I cannot confirm live occurrence — flagging the exact
mechanism per the task brief.

### 1d. Other things checked in `local_agent.py`, no issues found

- `_safe()`'s ADS/case-fold/prefix-boundary hardening (`:233-271`) reasoned through and looks
  correct for the attacks its own comments describe.
- `_gates()`'s pyflakes-exit-code check (`:346-358`) correctly distinguishes "pyflakes found
  nothing" (rc 0) from "pyflakes itself failed to run" (any other rc, or a traceback in stderr) —
  this specific class of bug (a gate that silently reads "ran clean" from "did not run") is
  **already fixed here**, contrary to how it reads elsewhere in the codebase per `NEXT_STEPS.md`.
- `t_find_symbol` correctly reports ambiguity (`unique`, `warning`) rather than silently picking
  one definition — matches its stated purpose.

---

## 2. `src/scope.py`

### 2a. `:106-114` — `build()` permanently memoises a scope failure as "done". **KNOWN, STILL OPEN.**

```python
for i, h in enumerate(todo, 1):
    try:
        sc = scope_for(h)
    except Exception:
        silence.note("scope.py:110")
        sc = None
    out[h] = sc
```
`todo` is computed as `{h for s, h in hosts.items() if h and h not in out ...}` (`:106-107`), so
once `out[h]` is set — to `None` from either a genuine "nothing found" or a network exception —
`h` is permanently excluded from every future `--build` run. A transient failure (timeout, 503,
malformed API response) is indistinguishable from "this wiki genuinely has no cosmology signal"
and both cause the host to never be retried. This is exactly the m143 failure-memoisation shape.

### 2b. `:81` — `titles[:8]` caps the pages fed into the scope decision. **KNOWN, STILL OPEN.**

```python
pages = F.fetch(host, titles[:8])
```
Up to 8 of the deduped search-result titles (from 4 queries × `srlimit=3`) are fetched and
concatenated for tier-counting; anything past the 8th found title is dropped before the regex
counts ever see it, silently narrowing the evidence a wiki's scope ceiling is decided from.

### 2c. `:86-93` — the no-signal fallback reintroduces the exact frequency bias the module's own
docstring says it rejects. **KNOWN, STILL OPEN.**

```python
if best is None:                       # nothing clears it: fall back to the commonest tier
    lab = max(counts, key=counts.get)
```
The module's header (`:25-30`) explicitly argues *against* picking by frequency ("Not by
frequency... The signal is the HIGHEST tier that appears with real usage, not the commonest").
When no tier clears `MIN_MENTIONS=10`, the code falls back to literally the commonest tier —
contradicting its own stated design principle in the one branch where the principle matters most
(weak-signal sources).

### 2d. `:74` — `srlimit="3"` per query, no continuation. **NEW.**

```python
d = F.api(host, {"action": "query", "list": "search", "srlimit": "3", "srsearch": q})
```
Four queries × 3 results = at most 12 raw titles before the `size>1200` filter and the `titles[:8]`
cap even apply. This is the same shape as the already-documented `feats.py:348-361`
`aplimit=500`/`srlimit=50` no-continuation cap (m82) and `NEXT_STEPS.md`'s lesson 16 ("sibling
caps still open… batch 01 found two inside verify_math itself") — a genuinely relevant
cosmology-signal page ranked below the top 3 hits for all 4 queries is never seen at all, before
the already-flagged `titles[:8]` even gets a chance to cut it.

Severity: MED (compounds 2b; the search API itself is the first, unlisted cap in the chain).

---

## 3. `src/ingest_doc.py`

### 3a. `:216` — `description[:2000]`, no truncation disclosure. **KNOWN, STILL OPEN.**

```python
"description": (e.get("description") or "").strip()[:2000],
```
Hard-truncates every mined entity's description to 2000 characters with no `"truncated": true`
flag and no length recorded anywhere in the stored entry — unlike other places in the sibling
codebase that disclose a truncation (e.g. `local_agent.py`'s own `run_check` output, or
`t_read_file`'s `chars_after_slice`).

### 3b. `record_path()` (`:116-126`) — unbounded substring fallback silently misroutes a new
source's entities into an unrelated existing record. **NEW, HIGH, reproduced live.**

```python
def record_path(source):
    p = os.path.join(RECORDS, slug(source) + ".json")
    if os.path.exists(p):
        return p
    want = slug(source)
    for fn in os.listdir(RECORDS):
        base = fn[:-5]
        if want in base or base in want:
            return os.path.join(RECORDS, fn)
    return p
```
When a new source's own record file does not yet exist (exactly the situation on the *very
first* `--pdf` ingest of a source, which is the documented first command in the module's own
docstring), the function falls back to a bare substring test with **no length floor, no word
boundary, no similarity threshold** against every existing filename in `data/records/`. Live
reproduction against the actual `data/records/` directory in this repo:

```
One  -> data\records\bone-jeff-smith.json
War  -> data\records\all-modern-warfare.json
Fire -> data\records\dr-firestorm-s-engineering-corps.json
Star -> data\records\battlestar-galactica.json
Dark -> data\records\darksiders.json
```

Any newly-ingested source whose slug is a short/generic substring of an already-catalogued
franchise's filename (or vice versa) gets routed to that unrelated franchise's record. This is
hit from **two call sites**, both reachable from a first-time `--pdf` run with no `--mine`
required:
  - `mine()` at `:174` — loads `rec = json.load(open(rp))` and later merges freshly-extracted
    entities into it via `write_record_catalogue`, so a wrongly-resolved `rp` means the new
    source's entire mined cast gets appended to a different, unrelated source's cast list.
  - `main()` at `:283` — even *without* `--mine`, a bare `--pdf` run resolves `rp` the same way
    and (`:284-293`) writes a provenance note ("Full text of the print sourcebook supplied by the
    owner…") into whatever record `record_path` returned, via `pipeline.write_record`. So the
    provenance corruption can happen on the very first command in the module's documented usage,
    before any entity mining occurs at all.

Failure scenario: owner runs `python src/ingest_doc.py --pdf book.pdf --source "Fire"` for a
brand-new sourcebook that hasn't been catalogued yet. `data/records/fire.json` doesn't exist, so
`record_path` substring-matches `"fire"` against every existing filename and returns
`dr-firestorm-s-engineering-corps.json` — a real, unrelated, already-catalogued source's record —
and appends a false provenance note to it (and, on `--mine`, merges the new document's entire
extracted cast into it).

### 3c. `extract()` (`:87-100`) writes `data/docs/<slug>/pages.json` with a raw `open(...,"w")` +
`json.dump`, unlike the atomic pattern the *same module* uses two functions later for
`ingest_state.json` (`:256-259`, `tmp` + `silence.replace_retry`). **NEW, MED.**

```python
with open(os.path.join(d, "pages.json"), "w", encoding="utf-8") as f:
    json.dump(out, f, indent=0, ensure_ascii=False)
```
A crash or kill mid-write (plausible for a "482-page book" extraction, per the module's own
docstring framing of scale) leaves a truncated/corrupt `pages.json`. `mine()` then does
`json.load(open(...pages.json...))` with no try/except around that specific read (`:153-154`,
contrast the guarded `state_p` read at `:156-161`) — a corrupt `pages.json` crashes `mine()`
outright with an unhandled exception rather than the "interruption must cost nothing" behaviour
the module's docstring (`:12-15`) promises. Re-running `--pdf` does regenerate it from the source
PDF, so this is recoverable as long as the PDF is still available, but it is inconsistent with
the atomic-write discipline the same file demonstrates two functions later.

---

## 4. `src/hosts.py`

### 4a. `add()` (`:78-97`) — unlocked cross-process read-modify-write on `data/SOURCE_HOSTS.json`. **NEW, MED-HIGH.**

```python
def add(source, host, evidence=None, score=None):
    if not host or host == primary_host(source):
        return False
    data = _load(EXTRA, {})
    rows = data.setdefault(source, [])
    if any(...):
        return False
    rows.append({"host": host, "evidence": evidence, "score": score})
    if not silence.write_json(EXTRA, data, ...):
        ...
```
`silence.write_json` makes the individual *write* atomic (no torn file), but does nothing about
the read→modify→write window: `add()` reads the whole `EXTRA` dict fresh on every single call
(one call per kept candidate host, from inside `discover()`'s serial result-processing loop at
`:190-199`). If two `hosts.py --discover` invocations run concurrently (e.g. one full run and one
`--only`-scoped run overlapping, which is exactly the shape the module's own CLI encourages:
`--only` restricts to a subset, inviting a targeted rerun alongside a standing full sweep), both
processes read the same base `SOURCE_HOSTS.json`, each adds a different host for a different (or
even the same) source in memory, and whichever finishes its `write_json` second **silently
discards** the first process's addition — the same lost-update shape `NEXT_STEPS.md` already
documents for `resync_roll.py:65-68` ("Fixed 2026-08-25 made only the WRITE atomic… the
read→full-scan→write clobber window is fully open") and `cascade_bridge.py:502-542`
("`record_unrecognised` RMW race across processes… only the write-collision half is fixed").
`hosts.py` is the same shape, previously unlisted.

### 4b. `_load()` (`:44-50`) collapses a read failure into the caller's `default`, indistinguishable
from a legitimately-empty file. **NEW, MED (logged, so not fully silent, but still ambiguous to callers).**

```python
def _load(path, default):
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        silence.note("hosts.py:load")
        return default
```
Every caller (`primary_host`, `hosts_for`, `add`, `coverage`, `discover`, `main`) treats the
return value as "the real file contents" with no way to distinguish "the file was empty/missing"
from "the read just failed" (a lock contention, a Norton-interception denial mid-write, a
transient corrupt-during-write state). `coverage()` in particular would report a source as having
zero extra hosts on a transient `SOURCE_HOSTS.json` read failure, exactly the same shape as the
`dashboard.py:284-305 _watch()` defaults-before-try pattern already flagged in `NEXT_STEPS.md`
lesson list (though here the default sits structurally inside `_load` rather than syntactically
before a `try`, the effect on the caller is identical: failure is unrecoverable-looking but reads
as "zero"). `silence.note` does log it, so it is not invisible to an auditor of `silence`'s own
output, but it is invisible to anyone reading `coverage()`'s or `--show`'s printed output.

### 4c. `discover()`'s `per_source=24` cap (`:125,166-167`) — checked against live data, confirmed
currently safe. **Not a finding; noted for the record.**

`hosts.py`'s own comment claims the cap "sits AFTER the evidence, never through it… what it drops
is guesses rather than known hosts" — this depends entirely on `hostcheck.candidates()` returning
`grounded + spec` with all grounded entries first and unbounded (verified true by reading
`hostcheck.py:266-369`, notably its own `EVIDENCE FIRST, SPECULATION AFTER` fix comment). I
measured the grounded-candidate count for every one of the 194 sources currently in
`WIKI_HOSTS.json` (via the position of the guaranteed-last-grounded `en.wikipedia.org` entry);
the worst case today is 15 grounded candidates (`"DMs Guild: Xanathar's Lost Notes to Everything
Else"`), well under the 24 cap. So the cap does not currently truncate any grounded evidence.
Flagging this only so a future run doesn't have to re-derive it: if the catalogued-roster overlap
between sources (`hostcheck.candidates`' "near neighbours" generator) ever grows past ~10 shared
neighbours for one source, or a source's name yields more than ~20 capitalizable tokens, the
24-cap would start eating real evidence, silently, exactly the pattern the comment says it avoids.

---

## 5. `src/generate.py`

### 5a. `_covered()` (`:163-176`) — the "every entry present" guard can be satisfied by an entry
that was never written. **NEW, HIGH, reproduced live.**

```python
def _covered(name, text):
    t = text.lower()
    n = (name or "").lower().strip()
    if not n:
        return True
    if n in t:
        return True
    words = [w for w in re.split(r"[^a-z0-9]+", n) if w]
    return bool(words) and words[0] in t and words[-1] in t
```
This is the sole mechanism behind the module's stated guarantee (`generate_job` docstring,
`:213-219`; header comment `:29-36`): "a missing entry retries once; still missing fails the
whole job LOUDLY… never a book quietly missing its own entries." The fallback path only checks
that the entry name's *first* and *last* word each appear **somewhere, anywhere** in the whole
multi-entry block of text — not adjacent, not near each other, not tied to that entry at all.
Reproduced directly:

```python
text = '''
The Great Library is a repository of knowledge founded in the third era.
Many scholars visited during a devastating regional war that lasted decades.
'''
_covered('The Great War', text)   # -> True
```
`"The Great War"` was never written into `text` at all — only `"The Great Library"` (an entirely
different entry) and an incidental mention of "war" elsewhere — yet the check reports it covered.
Any entry whose name starts with a common word ("The", "A", "Doctor", "King", "Captain" — all
plausible across the roll's catalogued names) is exposed to this: as long as its last word
independently appears anywhere in the same `WRITE_CHUNK`-sized block (very likely in an 8-entry
block covering a shared setting/vocabulary), the entry is marked present even if the model
dropped it entirely. This directly undermines the specific defence Hard Rule 0 and the module's
own header comment (`:29-36`, calling a book quietly missing entries "the prose version of the
catalogue cap") depend on. `_deed_shortfall`/`_deed_traced` (`:179-210`, used for feats blocks)
share the same "distinctive word found anywhere in the whole text" weakness, though that one is
explicitly self-documented as "BACKSTOP ONLY" (`:194-198`) with the trade-off acknowledged, so I
am not filing it as a separate finding — it is the same shape, lower severity because disclosed.

Secondary edge in the same function: `if not n: return True` (`:171-172`) means a manifest entry
missing its `"name"` key is *unconditionally* treated as covered, regardless of whether it was
actually written — no comment justifies this default the way `_deed_traced`'s equivalent (`:188-189`,
explicitly reasoned "nothing distinctive to look for; do not penalise it") does.

### 5b. Other things checked in `generate.py`, no issues found

- `save_json`/atomic catalog+failures writes via `silence.write_json` — correct, matches the
  two-writer contract.
- `context_budget.assert_fits` call before every `call_ollama` (`:132-133`) — correctly refuses
  an over-window prompt rather than letting Ollama silently truncate it (this is the fix the
  header comment at `:29-36` and the inline comment at `:125-131` describe, and it is present and
  wired in for both chapter and feats jobs).
- The bare-list vs `{"jobs":[...]}` manifest-shape handling (`:316-320`) is correct and loud
  about which shape arrived.
- Stale-vs-new job classification (`:332-339`) is correct for both the "never generated" and
  "generated under an old recipe" cases.
- `missing[:8]` in the final `RuntimeError` (`:298`) is a **disclosed** truncation ("+N more"),
  consistent with the project's accepted pattern for diagnostics that must stay short but not lie
  about completeness — not flagging this one.

---

## 6. `src/build_terminal.py`

Read in full, including all embedded JS in `TEMPLATE`. No correctness bugs found.

- `esc()` (JS, `:85-87`) is applied consistently everywhere a catalogue-derived string
  (name, tier label, tooltip) reaches `innerHTML`/SVG text content — spot-checked every
  `${...}` interpolation site that renders untrusted catalogue data; all are wrapped in `esc()`.
- The Python-side `data.replace("<", "\\u003c")` (`:568`) correctly neutralises `</script>`
  injection risk from a catalogue name containing that sequence, using `str.replace` (literal,
  not regex) so no backslash-escape hazard on the Python side either.
- `TIERS` (JS, `:88`, 5 entries) indexed by `shelfmark()` (`:461-471`) against `parts.length`:
  confirmed the maximum navigable key depth (universe tier, 5 dotted components) exactly matches
  `TIERS.length`, so no out-of-bounds access — verified by tracing `layout()`'s `OVERVIEW_DEPTH=3`
  recursion bound combined with repeated `descend()` calls compounding absolute depth.
- Division-by-zero guards (`Math.max(1,n)` in `discR`, `fitIn`) checked and present everywhere a
  count could be zero.

This module was read in full per the task's mandate; recording that explicitly since it produced
no findings, so the absence isn't mistaken for a skipped file.

---

## 7. `src/chord_field.py`

Read in full. Pure physics-reference/lookup module (`ADJUDICATIONS` dict) plus four small math
functions (`total_beta`, `per_system_beta_without_unification`, `landauer_floor`,
`recoil_momentum`, `recoil_velocity`, `critical_power_self_focus`). No file I/O, no shared state,
no caps on any listing. Checked every formula against the physics it claims (Landauer bound,
`p=E/c`, Kerr self-focusing critical power `P_cr = 3.77λ²/(8πn₀n₂)`) — all correct. No findings.

---

## Summary table

| Sev | Status | Location | Claim |
|---|---|---|---|
| HIGH | NEW | `local_agent.py` (`:406-407,341-390,DENYLIST_PATHS`) | Non-`.py`, non-`config.yaml` files (prompt templates, registry_terminal HTML/JS, keystone charter .md, CLAUDE.md/NEXT_STEPS.md) are writable by the local model through `propose_patch` with zero content validation — only an unrelated whole-suite pass/fail gate applies |
| HIGH | KNOWN, open | `local_agent.py:561` | `json.dumps(res)[:SLICE]` produces invalid JSON and drops the truncation-disclosure fields; reproduced live |
| MED-HIGH | NEW | `local_agent.py` (`_safe`+`propose_patch`, general) | `propose_patch` can write directly to `data/records/*.json` and other state files, bypassing `pipeline.write_record`/`write_record_catalogue` — a third writer |
| KNOWN | KNOWN, open | `local_agent.py:446-476` | No lock around write/gate/revert; cross-process race mechanism spelled out (A's successful patch silently destroyed by B's revert-to-stale-backup) |
| HIGH | NEW, reproduced | `ingest_doc.py:116-126` (`record_path`), hit from `:174` and `:283` | Unbounded substring fallback misroutes a new source's provenance/entities into an unrelated existing record (`"Fire"` → `dr-firestorm-s-engineering-corps.json`, live-reproduced) |
| KNOWN | KNOWN, open | `ingest_doc.py:216` | `description[:2000]`, no truncation disclosure |
| MED | NEW | `ingest_doc.py:87-100` (`extract`) | Raw `open(...,"w")`+`json.dump` for `pages.json`, inconsistent with the same module's atomic `ingest_state.json` write two functions later |
| HIGH | NEW, reproduced | `generate.py:163-176` (`_covered`) | Entry-presence guard passes on first+last word appearing anywhere in the block, not tied to that entry — reproduced marking an unwritten entry "covered" |
| MED-HIGH | NEW | `hosts.py:78-97` (`add`) | Unlocked cross-process read-modify-write on `data/SOURCE_HOSTS.json`; same lost-update shape as `resync_roll.py`/`cascade_bridge.py`'s already-documented instances |
| MED | NEW | `hosts.py:44-50` (`_load`) | Read failure collapses to caller's `default`, indistinguishable from legitimately empty/absent file for every downstream caller |
| KNOWN | KNOWN, open | `scope.py:106-114` | `build()` permanently memoises a scope failure (exception or genuine no-signal) as done; host never retried |
| KNOWN | KNOWN, open | `scope.py:81` | `titles[:8]` caps pages fed into the scope decision |
| KNOWN | KNOWN, open | `scope.py:86-93` | No-signal fallback picks by frequency, contradicting the module's own stated design principle |
| MED | NEW | `scope.py:74` | `srlimit="3"` per query, no continuation — first, previously-unlisted cap in the chain feeding `titles[:8]` |
| — | checked, not a finding | `hosts.py:125,166-167` (`per_source=24`) | Verified against live `hostcheck.candidates()` ordering and all 194 current sources; grounded-candidate count never exceeds 15 today, cap does not currently truncate evidence |
| — | reviewed, no findings | `build_terminal.py`, `chord_field.py` | Full read completed; no correctness/cap/two-writer/concurrency issues found |
