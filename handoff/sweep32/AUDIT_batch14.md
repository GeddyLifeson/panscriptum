# AUDIT — run32, BATCH 14

Modules read in full, every line:

| module      | lines |
|-------------|-------|
| rigor.py    | 865   |
| publish.py  | 579   |
| rosetta.py  | 416   |
| address.py  | 290   |
| render.py   | 252   |
| liveness.py | 188   |
| scope.py    | 152   |

All findings below are VERIFIED against source and/or live execution (miniconda python,
read-only) unless explicitly marked SUSPECTED. No files were modified. `publish.py` was not
executed; only pure functions (`_SECRET`, `scan_for_secrets` read-only walk, `_is_real_secret`)
were exercised directly.

---

## BLOCKING

### 1. `publish.py:272-307` (`scan_for_secrets`), specifically `publish.py:290` — Lock Three has a hard blind spot over 2MB, and the repo already has files that fall in it

```python
def scan_for_secrets(root, max_bytes=2_000_000):
    ...
    for f in sorted(files):
        p = os.path.join(base, f)
        try:
            if os.path.getsize(p) > max_bytes:
                continue          # <-- line 290: silently skipped, no warning printed
```

Lock Three is the *only* lock that scans files copied wholesale via `COPY_DIRS`/`COPY_FILES`
(`_scrub`, Locks One/Two, only ever touch the `snapshot()` dict built by `dashboard.state()`,
never the files `sync_tree()` copies verbatim with `shutil.copy2`). Any staged file over 2MB
is skipped from Lock Three entirely, with no log line, no count, nothing — `push()` cannot even
report "N files were not scanned."

Checked the real repo for files currently in the copied trees (`reference`, `registry_terminal`
are both in `COPY_DIRS`) that exceed the 2MB threshold:

```
3363987  reference/keystone_volumes/LOCAL_REGISTER.json
2969665  reference/keystone_volumes/LOCAL_REGISTER_CITATIONS.md
2684708  registry_terminal/PANSCRIPTUM_TERMINAL.html
2470102  registry_terminal/lex2.js
```

All four are staged for the public export today and all four receive **zero** secret scanning
of any kind — not Lock One/Two (never touched, they're copied not built from the state dict)
and not Lock Three (skipped by size). I grepped all four for common vendor patterns (AKIA,
ghp_/gho_/ghs_, sk-, PEM headers, xox tokens, AIza, github_pat_) and found none — so there is
**no live leak today** in these specific files. But the exposure is structural, not
hypothetical: `handoff/HANDOFF.md` (58KB today) is exactly the kind of free-text,
session-narration file the docstring at `publish.py:278` names as the reason Lock Three exists
("a log excerpt pasted into HANDOFF.md, a provider error quoted in BUGS.md ... all arrive this
way") — and it, or any other `handoff/` file, only has to cross 2MB once for the safety net
protecting the PUBLIC repo to go silently inert for it. The failure mode is also irreversible
(a key pushed public stays public even after a fix), which is exactly the property the module's
own docstring says Lock Three exists to prevent.

**Fix direction (not applied):** either scan in a bounded streaming fashion instead of skipping,
or lower/raise the threshold with a loud warning when a file is excluded, so an excluded file is
at minimum visible in the "publish failed"/"pushed" output.

### 2. `address.py:101-114` (`spine_code_for`, token-overlap fallback) — ties are broken by JSON/dict insertion order, not refused to UNASSIGNED; live-confirmed invented address

```python
target_tokens = _token_set(source_name)
if target_tokens:
    best, best_overlap = None, 0
    for name, code in codes.items():
        name_tokens = _token_set(name)
        if not name_tokens:
            continue
        overlap = len(target_tokens & name_tokens)
        coverage = overlap / min(len(target_tokens), len(name_tokens))   # line 110
        if coverage >= 0.8 and overlap > best_overlap:                   # line 111
            best, best_overlap = code, overlap
```

Confirmed live:

```
>>> address.spine_code_for("Alien Predator Doom Crossover")
'II.N'
```

`"Alien Predator Doom Crossover"` tokenizes to `{alien, predator, doom, crossover}`. Three
single-word spine-code entries each independently satisfy the loop's threshold:

```
('Alien',    'II.N',   overlap=1, coverage=1.0)
('Doom',     'II.N.2', overlap=1, coverage=1.0)
('Predator', 'II.I',   overlap=1, coverage=1.0)
```

Root cause is two-layered:

1. **The coverage formula is the real bug.** `coverage = overlap / min(len(target), len(name))`
   means any single-word spine entry ("Alien", "Doom", "Predator") that shares even one token
   with a multi-word target automatically scores `1/min(4,1) = 1.0` — perfect "coverage" — no
   matter how small a fraction of the *target* that one word represents. This is what lets three
   unrelated one-word entries all clear the `>= 0.8` bar on a completely different four-word
   fictional crossover title.
2. **The tie-break is dict order.** `overlap > best_overlap` is strict, so once `"Alien"` (the
   first of the three to appear in `data/CHARTER_SPINE_CODES.json`, JSON key index 8) sets
   `best_overlap = 1`, neither `"Doom"` (index 46) nor `"Predator"` (index 135) can replace it
   even though they tie exactly. Verified the index ordering directly against the JSON file.

This is a direct violation of Hard Rule 2 ("Don't invent addresses") happening *inside the
mechanism whose entire job is to avoid inventing addresses* — a source with no real match should
fall through to `"UNASSIGNED"` (which surfaces it in `output/index/unassigned_sources.md` for
owner sign-off per `manifest_builder.py`), but instead gets a confident-looking, wrong,
fabricated spine code that will never be flagged for review.

---

## MAJOR

### 3. `publish.py:426-433` (`write()`) — hand-rolled tmp+`os.replace`, bypassing the project's own two-writer-safe write path

```python
def write(state=None):
    os.makedirs(DOCS, exist_ok=True)
    data = state if state is not None else snapshot()
    tmp = STATE_JSON + ".tmp"                 # line 429 — no PID/thread suffix
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=1)
    os.replace(tmp, STATE_JSON)               # line 432 — bare, no retry
    return STATE_JSON
```

(Original lead cited `publish.py:107`; that line is inside the `export_root()` docstring, not
this function — the actual hand-rolled instance is here at 429/432. Substance confirmed
regardless of line-number mismatch.)

`silence.write_json`/`silence.replace_retry` exist specifically because a sweep found "TWELVE
call sites across ten modules" doing exactly this pattern (`silence.py:290-307`'s own docstring).
Two concrete hazards this reintroduces:

- **No PID/thread suffix on the tmp name.** `push()`'s own docstring two functions below states
  plainly: "Two writers publish into this tree (the standing loop and whatever session is
  working)." If both write `docs/state.json` around the same time, both use the literal same
  tmp path `docs/state.json.tmp`; one writer's `open(tmp, "w")` can truncate/overwrite the
  other's in-flight tmp file before either calls `os.replace`, landing a torn or wrong-writer's
  copy. `silence.write_json` avoids exactly this by naming the tmp file with
  `os.getpid()`/`threading.get_ident()`.
- **No retry on Windows `PermissionError`.** `silence.replace_retry`'s docstring explains this
  project's state files "all have readers on their own clocks (the dashboard polls records...)"
  and that a bare `os.replace` gets `WinError 5` when a reader holds the target open — this
  publish loop's own dashboard-snapshot use case is precisely that reader. A bare `os.replace`
  here can raise uncaught inside `write()`.

`publish.py` already imports `silence` (line 53) and calls `silence.note` elsewhere in the same
file — it is the only one of the seven audited modules that hand-rolls this pattern instead of
using the shared helper (`scope.py:119` and `rosetta.py:368,383` both correctly call
`silence.write_json`).

### 4. `publish.py:172` — bearer-token pattern excludes `+` and `/`, both legal base64 characters

```python
r"(?i:bearer)\s+[A-Za-z0-9_\-\.=]{24,}|"
```

Confirmed empirically: a token containing `+` or `/` within its first 24 characters does not
match at all (the match simply stops short of the length floor at the `+`/`/`):

```
tok = "Bearer " + "A"*20 + "+/" + "Bb"*5
_SECRET.search(tok)  ->  None
```

vs. a token using only `A-Za-z0-9_-.=`, which matches fine. Standard base64 (the encoding most
bearer/session tokens actually use) legally contains `+` and `/`; this pattern misses any such
token outright rather than catching a truncated/weaker match.

### 5. `publish.py:157-158` — vendor list omits GitHub `ghu_`/`ghr_` prefixes

```python
r"github_pat_[A-Za-z0-9_]{20,}|ghp_[A-Za-z0-9]{20,}|gho_[A-Za-z0-9]{20,}|"
r"ghs_[A-Za-z0-9]{20,}|hf_[A-Za-z0-9]{20,}|"
```

Confirmed empirically: `ghp_`, `gho_`, `ghs_` tokens match; `ghu_` (GitHub user-to-server OAuth
token) and `ghr_` (GitHub refresh token) do not match at all — no candidate substring, so Lock
Two's entropy check never even runs on them. The shape-blind `_SECRET_ASSIGN` lock provides
partial backup only when the token sits in an explicit `name = value` / `name: value` form next
to a credential-sounding key; a `ghu_`/`ghr_` token pasted inline in free prose (a quoted error
message in `HANDOFF.md`/`BUGS.md` — the exact scenario Lock Three's docstring names) would pass
both locks and, per finding #1, only be caught by Lock Three if the containing file is under
2MB.

---

## MINOR

### 6. `scope.py:74` (`srlimit="3"`) and `scope.py:81` (`titles[:8]`) — confirmed caps in the MAGNITUDE CEILING evidence path

```python
d = F.api(host, {"action": "query", "list": "search", "srlimit": "3", "srsearch": q})   # :74
...
pages = F.fetch(host, titles[:8])                                                        # :81
```

Both confirmed present exactly as described. `scope_for()`'s result flows into `SCOPE.json` via
`build()`, and `ceiling_for()` (used by `magnitude.py`/`pipeline.py` per the code's own comment
at `scope.py:118`) reads that ceiling directly into the Magnitude scoring pipeline — this is
scoring-path code, not report code, matching the concern.

That said, this is a bounded *evidence sample* feeding a coarse band signal (a word-frequency
tier count against a `MIN_MENTIONS=10` floor), not a truncation of an entity roster/listing —
the shape Hard Rule 0's own examples describe (`roster(limit=600)`, `cap_chunks=12`, etc.). The
caps here bound how many wiki pages are read to estimate a fiction's own scale vocabulary, and
the module's docstring gives an explicit engineering reason (avoid diluting a targeted signal
with irrelevant pages). It is still a real, unlabeled cap sitting upstream of a scoring decision,
and with only 3 results/query × 4 queries × top-8-pages, a genuinely universe/multiverse-scale
fiction whose defining pages don't surface in the first 3 hits per query could plausibly
undercount and silently fall to the "commonest tier" fallback. Flagged for owner attention
rather than BLOCKING, since Hard Rule 0's stated harm (an entity silently ceasing to exist) does
not directly apply here — the harm is a possibly-conservative ceiling, not a vanished roster
entry — but the instruction to confirm this precisely: **confirmed, both caps are real, both sit
in the scoring path.**

### 7. `rosetta.py:402` — dead/vestigial no-op term, `pipeline._x`

```python
assays = {k: v["result"]["decimal"] + P.__dict__.get("_x", 0)
          for k, v in json.load(open(path, encoding="utf-8")).items()
          if v.get("result") and v["result"].get("decimal") is not None}
```

Grepped `pipeline.py` and the whole of `src/` for `_x` — `pipeline._x` is never defined,
assigned, or set anywhere. `P.__dict__.get("_x", 0)` therefore always evaluates to `0`; this term
is currently a harmless no-op but reads as if it should mean something (a calibration offset?),
and is presumably a leftover from a debugging session that was never cleaned up. No functional
bug today (decimal values pass through unchanged), but confusing and worth removing or
documenting.

### 8. `liveness.py` — answers to the audit's specific questions about the instrument itself

- **Can it miss a dead function?** Yes, and by design more than by oversight. The DEAD pass's
  "used" signal (`scan()`, lines ~92-99) is *any* occurrence of the function's bare name as an
  `ast.Name`, an `ast.Attribute.attr`, or a string `Constant` — **anywhere in any of the 103
  modules in `src/`**, with no requirement that the occurrence have anything to do with the
  function in question. A genuinely dead function named e.g. `build`, `check`, or `run` — all
  common words that already appear as identifiers/attributes dozens of times elsewhere in this
  codebase — can never be flagged dead, regardless of whether it is ever actually called, purely
  because its name coincidentally recurs elsewhere. The docstring documents the *tautology* pass's
  semantic blindness explicitly ("Reporting zero tautologies must not be read as 'there are
  none'") but does not name this equally real blindness in the DEAD pass.
- **Is the ceiling/ratchet gameable?** `drill.py:38` sets `LIVENESS_CEILING = 38`, checked as
  `n <= LIVENESS_CEILING` (`drill.py:947-957`) — this is a one-directional ratchet by explicit
  design (comment: "LOWER this when code is cleaned up... the ceiling is a ratchet"), so it is
  *intentionally* not a floor, and that alone is not a defect. But combined with the point above:
  a newly-added dead function whose name collides with any existing identifier/string anywhere in
  `src/` would not even increment the live count, so it would never be visible to the ratchet at
  all — the ratchet can be silently defeated by ordinary naming choice, no adversarial intent
  required.
- **Hardcoded count that would drift?** `LIVENESS_CEILING = 38` — ran `liveness.scan()` live as
  part of this audit: current totals are 38 dead / 0 tautology / 0 phantom, i.e. **no drift as of
  this audit** (2026-08-25). Not itself a bug, but it is exactly the shape of hardcoded count the
  brief asked to check, and the ratchet only enforces upward — if dead functions are cleaned up
  later, the ceiling silently becomes stale-permissive (38 when the true count might be 20) with
  nothing prompting anyone to tighten it, since only growth is checked.
- **Additional, unprompted finding:** the PHANTOM pass (`scan()`, lines ~130-161) builds its
  `defined` name set once per module by walking the *entire* module tree (all `ast.Name` nodes
  with `Store` context, wherever they occur), not per-function/per-scope. A name defined only as
  a local variable inside function A is added to the module-wide `defined` set, so a genuinely
  undefined guard name in an unrelated function B of the same module can be masked by that
  unrelated local variable sharing the same identifier. Same shape of over-permissiveness as the
  DEAD pass, undocumented in the module's own stated limitations.
- **Minor, related:** `_modules()` (`liveness.py:66-69`) uses `os.listdir(SRC)`, not a recursive
  walk, so `src/deprecated/catalogue_local.py` (the only `.py` file under a `src/` subdirectory)
  is silently excluded from all three passes. Currently harmless (it's explicitly deprecated),
  but the exclusion is implicit rather than declared, and any future subpackage under `src/`
  would silently escape liveness checking entirely with no note printed.

---

## NOTE — publish.py halt/export-copy interlocks (checked, not changed)

Per the brief, verified without modification:

- **HALT check:** `publish.py:main()` (lines ~519-536) imports `escalation` and calls
  `_ESC.assert_clear(os.path.basename(__file__))` as literally the first thing in `main()`, with
  the `ImportError` path failing closed (`raise SystemExit(...)`, explicitly commented as the
  run #31 fix for a prior silent-pass bug). This correctly refuses to publish while a halt
  stands, and correctly refuses to start at all if the escalation chain itself cannot be read.
- **Export-copy refusal:** `publish.py` does not check `.is-export-copy` itself; the guard lives
  in `silence.py:66-70` (checked at *import* time, `if os.path.exists(_MARKER): raise
  SystemExit(...)`), and `publish.py:53` imports `silence` before anything else runs. Confirmed
  this correctly makes any run of `publish.py` from inside the exported copy fail immediately at
  import.

Both interlocks work as claimed. No changes made; `publish.py` was not executed per instructions.

---

## Coverage

`sweep_plan.record('run32', ['rigor.py','publish.py','rosetta.py','address.py','render.py',
'liveness.py','scope.py'], batch=14)` run from repo root — see summary for result.
