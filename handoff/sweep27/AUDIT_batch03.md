# BATCH 03 audit — run27

Modules read in full, every line, no sampling:
- src/standards.py — 1307 lines
- src/publish.py — 379 lines
- src/entity_match.py — 278 lines
- src/runguard.py — 219 lines
- src/halo.py — 178 lines
- src/compress_store.py — 65 lines

Total: 2426 lines across 6 files.

---

## src/runguard.py

### F1. `claim()` has no atomic test-and-set (KNOWN-OPEN, RECONFIRMED) — runguard.py:98-121 — HIGH — CONFIRMED

`claim()` does `prior = read(path)` (a plain file read), evaluates `holder_is_live(prior)` in
Python, and only THEN calls `_land(rec, path)` which writes a temp file and `silence.replace_retry`s
it onto `GUARD`. There is no lock, no `O_EXCL`, no compare-and-swap between the read and the write.
Two processes that both call `claim()` within the same window (e.g. two supervisor cycles firing
close together, or a manual `--claim` racing the standing loop) can both read the same "not live"
prior state and both proceed to `_land()`. Whichever `_land()` (i.e. whichever `replace_retry`)
lands last wins the file, and BOTH callers receive `(True, "claimed")` — both believe they hold
the guard simultaneously. This is exactly the m27 failure class one step earlier in the sequence:
`beat()`/`release()` correctly check ownership before acting, but `claim()` itself has no such
protection at the moment two claims race. Concrete scenario: supervisor cycle N and a manually
invoked maintenance script both call `claim("agentA")` and `claim("agentB")` within the same
sub-second window while the guard is free; both read `prior=None`, both build a fresh record, both
call `_land`; the second `_land`'s `replace_retry` succeeds after the first's, silently discarding
agentA's claim record — agentA believes it holds the guard (`ok=True`) and proceeds to do
maintenance work while agentB's record is now the one on disk. Nothing downstream would detect
this until `beat()`/`release()` calls from agentA start failing with "guard now belongs to agentB",
at which point agentA has already been running unguarded for however long the gap was.

This is a genuine cross-process race; `threading.Lock` would not fix it (different processes), and
nothing in the module attempts inter-process exclusion (no lockfile with `O_CREAT|O_EXCL`, no
Windows named mutex). The module's own docstring is candid that `beat()`/`release()` enforce
ownership but never claims `claim()` itself is atomic — so this is not a comment-contradicts-code
issue, just an open, real race with no code-level defense.

---

## src/halo.py

### F2. `--full` print output truncates cited text to 54 chars — halo.py:169 — LOW — CONFIRMED (design question)

```python
print("   %-15s%5.1f  %s" % (ax, d["score"], d["cited"][:54]))
```

This is a terminal-column display truncation only — the underlying `HALO_ASSAYS.json` written via
`silence.write_json` at line 171 carries the full, untruncated `cited` string for every axis (see
`compute()`, which stores `v[1]` verbatim into `axes[k]["cited"]`). So no data is lost to disk; only
the human-facing `--full` CLI printout clips each citation to fit one line. Given Hard Rule 0's
literal wording ("no truncation ... of an entry list"), this is worth flagging, but it reads as
deliberate CLI-formatting rather than a data-integrity violation, since the stored record is
complete. Framing as a question rather than a bug: is a fixed-width terminal column an acceptable
exemption from Hard Rule 0, or should `--full` wrap/word-break instead of slicing?

No other findings in halo.py — the module is straightforward (a static ROSTER dict, an `assay()`
call per entry, and an atomic `silence.write_json` write). No swallowed failures, no raw
open+json.dump on the shared output file, no two-writer concern found (this appears to be the sole
writer of `data/HALO_ASSAYS.json`).

---

## src/compress_store.py

### F3. `content_hash()` truncates SHA-256 to 128 bits — compress_store.py:20-21 — MEDIUM — CONFIRMED

```python
def content_hash(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()[:32]
```

The hash is deliberately truncated from 64 hex chars (256 bits) to 32 hex chars (128 bits) via
`[:32]`. This literally matches the Hard Rule 0 pattern of a `[:N]` slice, and it is not merely
cosmetic: `store()` uses this truncated hash as the sole key for the content-addressed filename
(`{h}.zst` / `{h}.gz`, compress_store.py:37/41), and (per `src/generate.py:386-390`) the SAME
truncated hash becomes both the catalog's `content_hash` field and an input to
`address.babel_coordinate()` — i.e. it is used as a real identity/addressing key across the
library, not just an internal cache key. `store()` never verifies that a pre-existing file at the
same path actually holds the same content before overwriting it (compress_store.py:43-44, a plain
`open(path, "wb")`), so if two DIFFERENT chapter texts ever produced the same 128-bit prefix, the
second `store()` call would silently overwrite the first's compressed blob on disk with no error,
no warning, and no record that a collision occurred — the first chapter's stored bytes would be
permanently lost while its catalog entry still points at the (now different) file. 128-bit
collision resistance is large in absolute terms but is a real, measurable reduction from what
SHA-256 already computes for free (the full 64-char digest is discarded for no evident reason —
there's no length constraint on the CAS filename that would require it). CONFIRMED by direct code
reading; the collision itself is not reproduced (would require a targeted birthday search), but the
truncation and the silent-overwrite-on-collision behavior are both directly verified in the code.

### F4. `store()` writes the compressed blob non-atomically — compress_store.py:43-44 — LOW/MEDIUM — CONFIRMED

```python
with open(path, "wb") as f:
    f.write(blob)
```

Direct write to the final content-addressed path, not a `tmp` + `os.replace`/`silence.replace_retry`
pattern. If the writing process is killed or crashes mid-write (e.g. Ctrl-C during `generate.py`'s
loop, which the project's own CLAUDE.md explicitly says is expected/supported — "safe to Ctrl-C and
restart"), a partially-written `.zst`/`.gz` file can be left on disk under a hash-named path that
looks complete (the file exists) but is truncated. `catalog.py:97` later calls
`compress_store.load()` on that path, which will raise (zstd/gzip decompression error) the next
time anything tries to read that chapter — a crash discovered only at read time, arbitrarily far
from when the write actually failed, with no record in `state/failures.json` pointing at the
write. This is a lower-severity finding than F3 because content-addressed filenames make same-run
retries idempotent in the common case (same text → same hash → same path gets rewritten cleanly on
a re-run), but the crash-mid-write / corrupt-file-persists scenario is real and this file is
plainly a "shared" artifact (read by `catalog.py`, written by `generate.py`) that the project's own
`silence.py` module exists specifically to protect against this failure class for.

---

## src/entity_match.py

No CONFIRMED or SUSPECTED correctness/safety findings. This module is read-only/proposal-only by
design (the header is explicit and the code matches it — nothing in the file mutates any file or
catalogue). The `limit` parameter on `candidates()` is the one place a cap-shaped mechanism exists,
and it is handled correctly per Hard Rule 0: default `None` (uncapped), callers must opt in, and a
`truncated: True` flag is always returned alongside a truncated list so a caller can never mistake
it for the full set (compress_store.py:174-182, 226-228). The `qualifier_compatible()` gate, the
STRONG/WEAK thresholds, and the `MatchReason` contract all match their docstrings on inspection.
Not called from generation/production code yet (only `verify_math.py` exercises it), consistent
with the module's own header claim — verified by grep.

---

## src/publish.py

### F5. `write()` writes the shared, multi-writer `state.json` outside the project's own atomic-write contract — publish.py:283-290 — HIGH — CONFIRMED

```python
def write(state=None):
    os.makedirs(DOCS, exist_ok=True)
    data = state if state is not None else snapshot()
    tmp = STATE_JSON + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=1)
    os.replace(tmp, STATE_JSON)
    return STATE_JSON
```

Two problems, both squarely inside the Two-Writer Contract this sweep is checking for:

1. **Fixed temp filename.** `tmp = STATE_JSON + ".tmp"` is a static name, not tagged with PID/thread
   the way `silence.write_json` deliberately is (`"%s.%d.%d.tmp" % (path, os.getpid(),
   threading.get_ident())` — see `src/silence.py:266`). `silence.write_json`'s own docstring
   explains exactly why this matters: "Two writers of the same path otherwise collide on the temp
   file itself, and the loser can replace the winner's target with a partial file." `publish.py`'s
   own `push()` docstring two functions below (publish.py:296-300) states outright: **"Two writers
   publish into this tree (the standing loop and whatever session is working)"** — so this file
   documents its own two-writer hazard on the very file `write()` is unprotected on.
2. **Bare `os.replace`, no retry.** `silence.replace_retry` exists specifically because Windows
   denies a rename onto a path any reader currently has open (`silence.py:223-236`, citing a
   real 2026-08-23 WinError 5 incident), and this project's own dashboard/state files "all have
   readers on their own clocks." `write()`'s raw `os.replace(tmp, STATE_JSON)` has no such
   protection; a `PermissionError` here is not merely un-retried, it is **uncaught inside `write()`
   itself** — it propagates up to `main()`'s outer `try/except Exception` (publish.py:359-372),
   where it is swallowed via `silence.note("publish.py:main")` and the whole cycle's work
   (`sync_tree()` + `render_page()` + `write()`) is silently discarded for that loop iteration
   with only a `publish failed: PermissionError: ...` line to stderr.

Concrete failure scenario: the standing `--loop` supervisor and a manually-invoked one-off
`publish.py --push` both run `write()` within the same few hundred milliseconds (plausible any time
a maintenance session runs publish by hand while the loop is live, which is the exact situation the
`push()` docstring says already happened — "run #5 counted five such silent-ish failures in one
morning" for the analogous push race). Both open `docs/state.json.tmp` for writing; whichever
process's `json.dump` finishes last determines what bytes land at that path; the other process's
subsequent `os.replace(tmp, STATE_JSON)` either (a) succeeds and stomps the file with its own
version anyway (a lost-update race, silent), or (b) hits `FileNotFoundError` if the other process's
`replace` already consumed/renamed the shared tmp file first — uncaught, propagates to the outer
handler, logged as a generic `publish failed` with no indication it was a concurrency collision.
Either way this is precisely the failure class `silence.write_json`/`replace_retry` were written in
this same codebase to eliminate (see `silence.py:250-268`'s docstring: "TWELVE call sites across
ten modules were writing shared `data/` and `state/` files with a bare `open(path, 'w')` +
`json.dump`... Four of those sites were writing the SAME file... from four different scripts").
`publish.py:write()` is a thirteenth, undiscovered by that sweep, and it fits the pattern exactly:
a shared file (docs/state.json), acknowledged multiple writers, fixed temp name, no retry.

*(Lower-risk siblings, not flagged as findings: `ensure_site()`'s `.gitignore`/`.nojekyll` writes
and `sync_tree()`'s `.is-export-copy` marker also use raw `open(...,'w')`, but these are static,
idempotent, content-invariant files written once per `--init` or once per cycle with identical
bytes each time — a race there just re-writes the same content, not a data-loss risk.)*

### F6. `_scrub()`'s docstring overclaims universal credential coverage — publish.py:145-164 — MEDIUM — CONFIRMED

The module docstring says: "it carries no keys, and `_scrub` refuses anything credential-shaped
even if a future edit puts one in the state dict by accident" (publish.py:32-33). The actual
`_SECRET` regex (publish.py:145-148) only matches eight specific, hardcoded vendor key prefixes:
`sk-`, `gsk_`, `AIza`, `github_pat_`, `ghp_`, `hf_`, `xai-`, `csk-`. This is "a guard matching only
ONE spelling" in the audit lens's terms, generalized to a fixed enumeration rather than a shape
test. A generic bearer token, a plain password string, an AWS-style key (`AKIA[0-9A-Z]{16}`), a
Slack token (`xoxb-...`), a database connection string with embedded credentials, or a PEM/private
key block would all pass through `_scrub()` completely unredacted and be published to the public
GitHub Pages `docs/state.json` if any future `dashboard.state()` field ever carried one — exactly
the scenario the docstring says this function exists to catch ("the day somebody adds a field
carrying a provider error message with a key in it"). The function does correctly recurse through
every dict/list/str in the snapshot, so *within its pattern set* it is thorough; the gap is the
pattern set itself, and the docstring's "anything credential-shaped" is not an accurate description
of a fixed eight-prefix allowlist.

### F7. `render_page()`'s string substitution has no verification it matched — publish.py:254-260 — LOW — SUSPECTED (currently working, latent fragility)

```python
html = D.PAGE.replace("'/api/state'", "'./state.json'")
html = html.replace("setInterval(tick,5000)", "setInterval(tick,30000)")
html = html.replace("Refreshes every 5 seconds.", "...")
```

Verified against the current `src/dashboard.py` (lines 546, 705, 712) — all three literal strings
are present today, so this is NOT a live bug. But `str.replace()` silently no-ops if the substring
isn't found; there is no count check or assertion. If `dashboard.py`'s JS/HTML wording ever changes
even slightly (a space added, quote style changed, the refresh interval literal reformatted), the
published static page would silently keep fetching `'/api/state'` — an endpoint that does not exist
on a static GitHub Pages export — with no error raised anywhere in the publish pipeline; the page
would just show a JS fetch failure to any visitor. Given `render_page()`'s own docstring promises
"same markup, `./state.json` instead of the live endpoint" as a load-bearing guarantee, a silent-
no-op path here would directly contradict that promise the next time `dashboard.py` is edited for
unrelated reasons. Framing as latent/preventive rather than a confirmed active bug.

### F8. Commit-message file list truncated to 6 + "+N" — publish.py:320-324 — LOW — likely deliberate, noted for completeness

```python
head = ", ".join(sorted(code)[:6])
more = f" +{len(code) - 6}" if len(code) > 6 else ""
```

A `[:6]` slice, but only of the human-readable commit *message* summary — `git add -A` /
`git commit` still stage and commit every changed file regardless of this list; nothing about what
gets published or committed is capped. The `+N` suffix means the truncation is disclosed rather
than silently hidden. Given Hard Rule 0's literal wording bans "any... truncation... of an entry
list," this technically slices a list, but it's message cosmetics with no data consequence — flagged
as a question, not a bug.

---

## src/standards.py

This is the largest and most consequential file in the batch — it is the project's own
"what does working mean" instrument. Findings below.

### F9. Probe/unexpected classification over-matches on real fetch failures (KNOWN-OPEN, RECONFIRMED + new concrete instance) — standards.py:538-541 — HIGH — CONFIRMED

```python
probe = sum(v for k, v in ledger.items()
            if any(t in k for t in ("endpoint.py:detect", "endpoint.py:fetch",
                                    "hostcheck.py:probe", "hostcheck.py:candidates",
                                    "hostcheck.py:relevance", "scout.py:verify")))
real = sum(ledger.values()) - probe
```

This classifies `state/failures.json` ledger entries as "probe failures" (expected, reported but
never judged — the standard at line 551-555 is hardcoded `holds=True` with "no floor") versus "real"
failures (judged against `MAX_SWALLOWED_NEW`) purely by **substring containment** against six
literal site-name fragments, not by exception type or by any structural marker on the call site
itself. I traced every actual `silence.note(...)` call site in `endpoint.py`, `hostcheck.py`, and
`scout.py` against this list:

- `endpoint.py:fetch_html` (endpoint.py:331) — a genuine content fetch of ordinary web pages (the
  function's own docstring: "these are one-author sites... the entire point of reading them is that
  the author put the material there to be read" — not a six-paths-expect-five-to-fail probe like
  `detect`). Its site string, `"endpoint.py:fetch_html"`, contains the substring
  `"endpoint.py:fetch"` (intended to match `fetch_raw`'s three variant site strings), so EVERY
  `fetch_html` failure is silently classified as "probe" and excluded from the judged
  "unexpected swallowed failures" standard. Concrete failure scenario: a homebrew D&D wiki host
  goes down, or a batch of source URLs 404 systematically — every one of those failures increments
  only the always-`True` "probe failures (reported, not judged)" counter, never the HIGH-severity
  judged standard, no matter how many hundreds of real fetches fail. This is the dangerous-direction
  default the audit lens specifically calls out: a real, systematic failure folded into a
  success-shaped ("not judged", no floor) bucket.
- `"hostcheck.py:candidates"` (standards.py:540) matches **no actual call site** anywhere in the
  current codebase — grepped across all of `src/*.py`, the only occurrence of that exact string is
  in this classification list itself. It is dead/stale: either a site name that was renamed and
  never updated here, or one that was never implemented. Harmless on its own (matches nothing, so
  it neither over- nor under-classifies), but it is direct evidence the six-item allowlist has
  already drifted out of sync with the code it claims to describe — exactly the kind of drift this
  sweep is watching for. (standards.py:540, LOW, CONFIRMED via grep.)

The general shape — a hardcoded substring allowlist standing in for "is this call site a
know-many-will-fail probe" — will silently misclassify any future site whose name happens to
contain or be contained by one of the six fragments, in either direction, without anyone having to
touch `standards.py` at all.

### F10. Four standards read evidence files with no staleness gate, while siblings in the same function do (KNOWN-OPEN, RECONFIRMED) — standards.py:626-633, 637-650, 657-685, 793-828 — HIGH — CONFIRMED

Re-verified by direct reading, matching the brief's description exactly:

- **"rosters that name their own fiction"** (standards.py:611-633) reads `data/ROSTER_AUDIT.json`
  and `data/ROSTER_PURGES.json` with no `os.path.getmtime` check anywhere in the block.
- **"shelfmarks are unique"** (standards.py:637-650) reads `data/SHELFMARKS.json`, HIGH severity,
  no age check.
- **"hand-built assays match the charter"** (standards.py:657-685) reads
  `data/REFERENCE_ASSAYS.json`, HIGH severity, no age check — and sits directly beside its own
  sibling standard, "the automation reproduces the charter" (standards.py:693-720), which DOES
  compute `age_h` from `CHARTER_REGRESSION.json`'s own `at` field and fails closed
  (`holds = bool(scored) and not bad and age_h <= 26`) when the file is old or absent. The two
  standards sit in the same "instrument itself" section, one hardened, one not.
- **"every source is fully catalogued"** (standards.py:793-828) reads `data/COMPLETENESS.json`,
  HIGH severity, no `os.path.getmtime` check — despite this exact block containing the most
  sophisticated UNMEASURED-vs-zero handling in the whole file (the `if not wiki:` branch at
  standards.py:811-814, explicitly written after a 2026-08-24 incident where an empty file read as
  a false 0%). That fix addresses "no denominator," not "old denominator" — a `COMPLETENESS.json`
  that was accurate a week ago and has a real, non-empty `wiki`/`have` split, but that predates a
  large recatalogue (the exact "derived data is FRESH" hazard this same file's own
  standards.py:832-839 comment describes for `CHARACTER_SWEEP.json`), would report a confident,
  stale coverage percentage as if current, with no signal to the reader that it might be wrong.

Concrete failure scenario for any of the four: `data/SHELFMARKS.json` is generated once during a
Phase 7 run and never touched again while ten more sources are catalogued and shelved by hand
in the meantime — those new shelfmarks, and any collision among them, are invisible to this
standard until the file happens to be regenerated, and nothing on the dashboard indicates the
evidence is old. Compare to "coverage figures are current" (standards.py:478-483,
`MAX_COVERAGE_AGE_H`) and "the full audit is recent" (standards.py:781-788, `MAX_SWEEP_AGE_H`),
both of which exist specifically to guard against this in siblings of these same four.

### F11. Most data-file-backed standards vanish entirely (no `out.append`) on any read/parse failure, contradicting this file's own documented fix for exactly this pattern — standards.py, throughout — HIGH — CONFIRMED, NEW

The file contains an explicit, hard-won lesson at standards.py:739-750, applied to fix "the
library's counters are moving":

> "A STANDARD THAT DOES NOT EMIT IS WORSE THAN ONE THAT FAILS: it does not appear on the page at
> all, so nobody can even see that it went unmeasured... It now always emits."

That fix pattern — always append an entry, with `holds=True` and an explanatory "not enough
evidence yet" observed string when the data can't support a real verdict — is applied to exactly
one standard. Nearly every other data-file-backed standard in `check()` uses the opposite pattern:

```python
try:
    with open(os.path.join(HERE, "data", "SOMEFILE.json"), encoding="utf-8") as f:
        ...
    out.append(_s("some standard", ...))
except Exception:
    silence.note("standards.py:...")
```

If the `open`/`json.load` (or anything else in the block) raises for ANY reason — file missing,
truncated by a concurrent writer (a real risk elsewhere in this same codebase per the Two-Writer
Contract findings in this sweep), corrupted JSON, a KeyError on an unexpected shape — the whole
`out.append(...)` is skipped and `silence.note()` merely logs it to the internal failure ledger.
The standard simply does not exist in that run's `check()` output: it is absent from
`work_orders()`, absent from `report()`'s per-group listing, and — per the very
"every declared floor is measured" standard's own scope (see F13 below) — its declared floor
constant would still show as "measured" (the constant is textually referenced in `check()`'s
source), so even the file's own self-audit cannot catch this failure mode; it only catches a floor
that is never referenced at all.

At minimum the following standards share this exact silent-vanish pattern, several of them HIGH
severity and explicitly meant to catch serious faults:
- "rosters that name their own fiction" / "shelfmarks are unique" / "hand-built assays match the
  charter" (611-685, one shared and two individual try/excepts)
- "files that parse", "verifiers all run", "the full audit is recent" — all three share ONE
  `try` wrapping `data/ALLSWEEP.json` (764-790): if that single file fails to load, all three
  HIGH/MEDIUM standards disappear together, not just one.
- "every source is fully catalogued" (793-830)
- "the character sweep is newer than the catalogue" (840-858)
- "promotions have their spine codes amended" (1015-1033) — partially hardened (a `FileNotFoundError`
  is deliberately treated as "phase 7 hasn't run yet," which is a reasonable exemption) but any
  OTHER exception (corrupt JSON, unexpected shape) still falls into the generic
  `except Exception: silence.note(...)` with no `out.append`.
- "model IDs their providers still serve" (1161-1204) — despite being the standard whose own
  comment (1165-1179) most explicitly warns about the "false ALL-CLEAR from stale/absent evidence"
  failure mode and hardens against STALE data, it does nothing if the `open()`/`json.load()` itself
  raises (e.g., file simply doesn't exist yet) — that case still silently vanishes rather than
  reporting UNMEASURED the way a merely-stale file does.

Contrast with the standards that DO fail closed instead of vanishing: "calls that succeed"
(413-429, explicit UNMEASURED branch), "the automation reproduces the charter" (693-720, `reg=None`
still produces an `obs="never run"`, `holds=False` row), "the library's counters are moving"
(731-762, the fixed one), and "model IDs their providers still serve"'s STALE-but-present case
(1161-1204). Those four demonstrate the project knows how to do this correctly and has done it in
several places — the pattern above is simply not applied uniformly, and the un-hardened majority is
larger than the hardened minority.

Concrete failure scenario: any concurrent-write corruption of `data/SHELFMARKS.json` (plausible
given this project's broader Two-Writer Contract exposure — not confirmed to be actively racing,
but the file is written by the cataloguing pipeline while this standard reads it with no lock)
would silently remove the ONLY standard in this file that checks for address collisions, at exactly
the moment collision risk is highest (mid-write). The dashboard would show one fewer row and nobody
would know why.

### F12. `_SECRET`-adjacent note: not applicable here (see publish.py F6) — no separate standards.py finding.

### F13. "every declared floor is measured" self-check scans past the end of `check()`'s body — standards.py:1212-1233 — MEDIUM — CONFIRMED, NEW

```python
src = open(os.path.abspath(__file__), encoding="utf-8").read()
declared = set(_re.findall(r"^(M(?:IN|AX)_[A-Z_]+)\s*=", src, _re.M))
body = src[src.index("def check("):]
...
dead = sorted(d for d in declared
              if not _re.search(wordb + _re.escape(d) + wordb, body_code))
```

`body = src[src.index("def check("):]` has no closing index, so it is the entire rest of the
file's source from the start of the `check` function definition through end-of-file — which
includes not just `check()`'s own body but also `work_orders()`, `_wrap()`, `report()`, `main()`,
and the `if __name__ == "__main__":` block, everything after `check(` in the file. The standard's
own remedy text says the fix for a dead floor is to "wire it into check()," and the docstring
frames this whole self-check as verifying exactly that — but the actual word-boundary search would
count a `MIN_`/`MAX_` constant as "measured" if it is referenced ANYWHERE textually below
`def check(`, including inside `report()` or `main()`, even if `check()` itself never once uses it
to build a standard. Concrete failure scenario: a future edit declares `MAX_FOO = 5` at module
level and only references it in a debug `print` inside `main()` (or in a comment inside
`report()`/`work_orders()` that survives the `#`-stripping applied only per-line, not
cross-function) — this self-check, whose entire stated purpose is to catch precisely this class of
dead-floor ("Three were found dead in this very file... all measured nothing. This standard is the
one that would have said so," standards.py:1208-1211), would report "all measured" and be wrong.
Not reproduced against a live dead constant (none currently in this exact blind spot as far as I
traced), so this is a latent scope bug in the guard rather than an active false-clear today — but it
is a real gap in a check whose whole job is catching exactly this shape of bug, which the audit
lens flags as the highest-value finding class in this project.

### Other notes (not filed as standalone findings)

- standards.py:1021 `", ".join(_pending)[:120]` — the "promotions have their spine codes amended"
  standard's `observed` string is truncated to 120 chars for display, but the pass/fail verdict
  (`not _pending`) is computed from the full, untruncated `_pending` list — the decision is correct,
  only the human-readable message can hide sources beyond the cutoff. Same shape as publish.py F8:
  a display-only slice, not a decision-affecting one. Flagged for awareness given Hard Rule 0's
  literal wording, not filed as a bug.
- standards.py:551-555 ("probe failures (reported, not judged)", hardcoded `holds=True`) is a
  standard that literally cannot fail by construction — but its own label says "not judged" and its
  `order` text explains it is a volume report, not a floor. This is the ALSO-WATCH-FOR "check that
  cannot fail" shape, but it is self-disclosed as such rather than dressed up as a real floor, so
  it reads as deliberate rather than a bug.
