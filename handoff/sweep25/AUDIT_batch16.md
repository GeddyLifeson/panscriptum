# AUDIT batch 16 — run #25

Files: `src/build_terminal.py`, `src/local_agent.py`, `src/custodes.py`, `src/pantheon.py`,
`src/genre.py`, `src/cleanup.py`, `src/lognames.py`. Every line of every file was read.
PYTHON = `C:/Users/imarl/miniconda3/python.exe`.

---

## HEADLINE — a FOURTH `_safe()` bypass, found and VERIFIED

### local_agent.py — bypass #4: case-sensitive `.py` suffix check

`t_propose_patch` (local_agent.py:391-465) computes `modname` like this (line 395):

```python
modname = os.path.basename(full)[:-3] if full.endswith(".py") else None
```

`full.endswith(".py")` is a **case-sensitive literal suffix check**. `_gates()` (line 339) repeats
the identical case-sensitive test, as does the JSON/YAML branch (`.endswith(".json")`,
`.endswith((".yaml",".yml"))`, lines 359/364).

Windows/NTFS filenames are case-insensitive-but-preserving, so `src/foreman.PY` and
`src/foreman.py` are **the same on-disk file** — `os.path.isfile()` resolves both to it. But
`"src/foreman.PY".endswith(".py")` is `False` in Python (case matters to `str.endswith`), so:

- `modname` computes as `None` instead of `"foreman"`.
- The module-name denylist check (`_mod_l in _deny`) never runs, because `_mod_l` is `""`.
- It falls through to the path-based check (`rel.lower() in _deny_paths`), but
  `DENYLIST_PATHS = {"config.yaml"}` — it does **not** contain any of the eight protected
  source modules (`foreman`, `silence`, `health`, `allsweep`, `estate`, `standards`,
  `verify_math`, `local_agent`).
- Result: **not denied**. The write proceeds.
- Worse: because `full.endswith(".py")` is also `False` inside `_gates()`, the entire
  parse/pyflakes-lint/import block is skipped too — only the unconditional whole-suite
  `verify_math` run at the end of `_gates()` still applies. A syntactically-broken patch that
  `verify_math` happens not to exercise would land on disk with **zero** of the four documented
  gates having run.

**VERIFIED.** Ran `_safe()` and the exact `t_propose_patch` denylist-resolution logic
(imported `local_agent`, called `_safe()` and reproduced the `modname`/`denied` computation)
against every candidate below, with `apply=False` so nothing was ever written (the denylist
check in `t_propose_patch` executes and returns *before* the `if not apply:` branch, so this is
provably read-only — confirmed by reading the function body). Full candidate table:

| # | Case | raw path | `_safe()` result | isfile | modname | denied? | VERDICT |
|---|------|----------|-------------------|--------|---------|---------|---------|
| 1 | plain foreman.py | `src/foreman.py` | resolves | True | `foreman` | `foreman` | DENIED |
| 2 | NTFS ADS `::$DATA` (m121, already patched) | `src/foreman.py::$DATA` | `None` | — | — | — | DENIED (rejected by colon check) |
| 3 | ADS, backslash form | `src\foreman.py::$DATA` | `None` | — | — | — | DENIED |
| 4 | case-insens name, lower ext (m113, already patched) | `src/Foreman.py` | resolves | True | `Foreman` | `Foreman`→matches lowered | DENIED |
| 5 | **UPPERCASE extension `.PY`** | `src/foreman.PY` | resolves | True | **`None`** | **`None`** | **ADMITTED — bypass** |
| 6 | **uppercase name + ext** | `src/FOREMAN.PY` | resolves | True | `None` | `None` | **ADMITTED — bypass** |
| 7 | **mixed-case ext `.Py`** | `src/foreman.Py` | resolves | True | `None` | `None` | **ADMITTED — bypass** |
| 8 | **mixed-case ext `.pY`** | `src/foreman.pY` | resolves | True | `None` | `None` | **ADMITTED — bypass** |
| 9 | **same bug, `silence.py`** | `src/silence.PY` | resolves | True | `None` | `None` | **ADMITTED — bypass** |
| 10 | **same bug, `verify_math.py`** | `src/verify_math.PY` | resolves | True | `None` | `None` | **ADMITTED — bypass** |
| 11 | mixed-case dir + upper ext | `SRC/FOREMAN.PY` | resolves | True | `None` | `None` | **ADMITTED — bypass** |
| 12 | trailing dot | `src/foreman.py.` | strips to `foreman.py` | True | `foreman` | `foreman` | DENIED |
| 13 | trailing space | `src/foreman.py ` | strips to `foreman.py` | True | `foreman` | `foreman` | DENIED |
| 14 | drive-relative `C:foo` | `C:src/foreman.py` | resolves via cwd-join | True | `foreman` | `foreman` | DENIED |
| 15 | `\\?\` prefix | `\\?\C:\...\src\foreman.py` | `None` | — | — | — | DENIED (fails HERE-prefix test) |
| 16 | UNC `\\localhost\c$\...` | `\\localhost\c$\...\src\foreman.py` | `None` | — | — | — | DENIED |
| 17 | forward slashes | `src/foreman.py` | resolves | True | `foreman` | `foreman` | DENIED |
| 18 | `..` traversal (normalizes back in) | `src/../src/foreman.py` | resolves | True | `foreman` | `foreman` | DENIED |
| 19 | `..` escape attempt | `../panscriptum-library-kit/src/foreman.py` | resolves (same tree) | True | `foreman` | `foreman` | DENIED |
| 20 | sibling-prefix collision (run #23 fix) | `../panscriptum-library-kit-EVIL/x.py` | `None` | — | — | — | DENIED |
| 21 | export-copy prefix | `../panscriptum-export/src/foreman.py` | `None` | — | — | — | DENIED |
| 22 | all-uppercase absolute path | `C:\USERS\IMARL\...\SRC\FOREMAN.PY` | `None` | — | — | — | DENIED (case-sensitive `HERE` prefix — over-strict, not a bypass) |
| 23 | mixed-case dir only, lower ext | `SRC/foreman.py` | resolves | True | `foreman` | `foreman` | DENIED |
| 24 | reserved device name | `src/CON` | resolves (string) | **False** | — | — | N/A, not a file on this volume |
| 25 | reserved device name + ext | `src/CON.py` | resolves | False | — | — | N/A, not a file |
| 26 | colon mid-component | `src/fore:man.py` | `None` | — | — | — | DENIED |
| 27 | double extension | `src/foreman.py.txt` | resolves | False | — | — | N/A, not a real file |
| 28 | Cyrillic homoglyph `а` for `a` | `src/foаreman.py` | resolves | False | — | — | N/A, not a real file (would be a *different*, new file — not a bypass onto the protected one) |

**Short (8.3) name bypass: not applicable on this machine.** `dir /x src\foreman.py` (and
`silence.py`) shows no short-name alias column populated — 8.3 name generation is disabled on
this volume (`fsutil 8dot3name query` itself needs elevation and was denied, but the empty `/x`
column is conclusive). Symlink/junction bypass: no reparse points exist under `src/` (none were
created, per instructions — read-only), so it could not be tested live; reasoning only
(UNVERIFIED): if a symlink `src/x.py -> C:\real\foreman.py` existed, `os.path.isfile` would
report True, `modname` would be `"x"` (not on the denylist), and `open(full,"w")` follows the
link on Windows by default, so this would also be a bypass **if such a link were ever planted**
— worth a defensive `os.path.islink`/reparse-point check even though nothing exploits it today.

**Total: 28 candidates tested, 8 ADMITTED (all the same root cause: case-sensitive `.py`
suffix check), 0 of the three previously-patched bypasses (ADS, case-insensitive name,
directory-prefix) reopened.**

**Fix shape** (not applied — read-only audit): compare extensions case-insensitively
everywhere `_safe()`/`_gates()`/`t_propose_patch` test `.endswith(".py"/".json"/".yaml")`,
e.g. `os.path.splitext(full)[1].lower() == ".py"`, and compute `modname` from that normalized
check so a differently-cased extension still resolves to the real module name and hits the
existing lowercased-denylist comparison.

---

## local_agent.py:391-465 (docstring ~lines 16-21) — the promised backup is NEVER written to disk

Docstring (module header, lines 16-21):

> "WRITES GO THROUGH THE FOREMAN'S OWN BAR. ... **A backup is written before and restored on
> ANY failure, including a crash inside the checking.**"

Code (`t_propose_patch`, lines 391-464):

```python
original = open(full, encoding="utf-8").read()
...
backup = original                                   # line 433 — a Python str, nothing else
try:
    with open(full, "w", encoding="utf-8") as f:
        f.write(original.replace(find, replace, 1))
    fail = _gates(full, modname)
    if fail:
        with open(full, "w", encoding="utf-8") as f:
            f.write(backup)                          # restore FROM THE IN-MEMORY VARIABLE
        return {"applied": False, "reverted": True, "gate": fail}
    return {"applied": True, "why": why[:200]}
except Exception as e:
    ...
    try:
        with open(full, "w", encoding="utf-8") as f:
            f.write(backup)                          # same — in-memory only
    except Exception:
        ...
```

`backup` is a plain Python string held in process memory. **Nothing in this function ever
writes a `.bak` file, copies the original to a second path, or persists it anywhere on disk.**
If the process is hard-killed (crash, `TerminateProcess`, power loss) between the initial write
(line 436) and the restore (line 440/454), the module is left corrupted on disk with the *only*
correct copy having existed solely inside the now-dead process's heap — permanently
unrecoverable except from source control. The docstring's "a backup is written" promise is
false as written; the real behaviour is "a backup is *held*, and *sometimes* re-written back
over the same path."

**VERIFIED** by direct source read — both the docstring text and the code quoted above are
copied verbatim from the file at its current line numbers.

This exact finding is flagged in `NEXT_STEPS.md` §3 (top of "The ones I would take first") —
**marking [KNOWN]**, but this is the first run to confirm the *exact* current line range and
quote both sides after run #24's edits (the function shifted from the previously-cited
407-438 to 391-464 because m121's `_safe()` fix added lines above it).

---

## build_terminal.py:468, 487, 503, 524 — `nd.name`/`shelfmark()` spliced into innerHTML unescaped [KNOWN]

Confirmed at the cited line numbers, unchanged from run #24's finding.

`esc()` is defined at line 85-87 and is applied to *every other* dynamic string reaching
`innerHTML` in this file (lines 237, 241, 242, 251, 261, 334, 340, 355, 359, 365, etc.) — this
is the file's own documented invariant (comment at 80-84, "BUGS m10, 2026-08-24").

`shelfmark()` (line 461-471) is the one path that breaks it:

```python
function shelfmark(k){
  let s="&#937;"; if(k==="") return s;
  const parts=k.split(".");
  for(let i=0;i<parts.length;i++){
    const key=parts.slice(0,i+1).join("."), nd=DATA.nodes[key];
    s+=" › "+((nd&&nd.name)||LABEL[TIERS[i]]+parts[i]);   // line 468 — NOT esc()'d
  }
  return s;
}
```

and it is called, unescaped, directly inside three `innerHTML` template literals:

- line 487: `<div class="mark">${shelfmark(k)}</div>` (inside `panel()`)
- line 503: `<div class="mark">${shelfmark(rootKey)}</div>` (inside `selectSource()`)
- line 524: `<div class="mark">${shelfmark(rootKey)} › P<br>seed ${w.s}</div>` (inside
  `selectWorld()`)

**Data provenance**: `nd.name` comes from `data/NAVTREE.json`, itself built from the
Acquisitions Roll and wiki article titles — this file's own comment two lines above `esc()`'s
definition says exactly that ("The names come from the roll and from wikis, so 'Dungeons &
Dragons' is not a hypothetical"). This is **not** live attacker input, but it *is* arbitrary,
uncontrolled text scraped from the public MediaWiki API — a franchise or character name
containing `<`, `"`, or `&` (e.g. an ampersand-bearing title, a `<3` in a nickname) would break
the panel's markup or inject markup into it, same class of hazard the m10 fix already
addressed for every *other* name in this file. VERIFIED by direct read; the four call sites and
line numbers match `NEXT_STEPS.md` §3 exactly. **[KNOWN — confirmed, no new ground.]**

Also unchanged/KNOWN: `build_terminal.py:572-573` non-atomic write of the generated HTML
(`with open(OUT, "w") ... f.write(html)`, bare, no `silence.write_json`/`replace_retry`) — this
is a single-writer generated *artifact* file (not multi-writer shared state), so the practical
blast radius is small, but it is still on the "non-atomic shared writes" list in NEXT_STEPS §3
verbatim (`build_terminal.py:571-573`, off by one line from source edits since).

---

## custodes.py:229-230 — `_ATT_BASE` vs `assay.py:630-631` — [KNOWN, re-verified numerically]

`custodes.py:229-230`:
```python
_ATT_BASE = {"Witnessed": 0.10, "Instrumented": 0.08, "Transcribed": 0.20,
             "Reconstructed": 0.40, "Disputed": 0.55}
```

`assay.py:630-631` (`interval_from_hands`):
```python
floor = {"Witnessed": 0.10, "Instrumented": 0.08, "Transcribed": 0.20,
         "Reconstructed": 0.40, "Disputed": 0.55}.get(attestation, 0.30)
```

**VERIFIED numerically identical, key-for-key and value-for-value**, as of 2026-08-25: Witnessed
0.10=0.10, Instrumented 0.08=0.08, Transcribed 0.20=0.20, Reconstructed 0.40=0.40, Disputed
0.55=0.55. No import links the two dicts — `custodes.py` does `import assay as A` but never
references `A.<anything>` for this table, so a future edit to either copy alone will silently
drift them apart. **[KNOWN]** — this is finding "E" in `NEXT_STEPS.md` §2, confirmed again this
run.

## custodes.py:254 — unknown attestation grade → MID quality (0.4), not worst-case [KNOWN]

```python
q = ATTESTATION_QUALITY.get(attestation, 0.4)
```

`ATTESTATION_QUALITY` (line 234) is derived from `_ATT_BASE`: `Witnessed`≈0.818,
`Instrumented`≈0.855, `Transcribed`≈0.636, `Reconstructed`≈0.273, `Disputed`=0.0 (worst).
An attestation string that doesn't match any of the five known grades (typo, new grade added
elsewhere and not mirrored here, etc.) silently gets quality 0.4 — between Transcribed and
Reconstructed, i.e. treated as **moderately trustworthy**, not as the worst case (`Disputed`,
quality 0.0) the way `assay.py`'s own `floor.get(attestation, 0.30)` defensively degrades
(0.30 sits worse than Transcribed's 0.20 floor, erring toward *wider* intervals, the safe
direction — `custodes.py`'s 0.4 quality is the same idea inverted: since higher `q` means a
*smaller* evidential-uncertainty contribution to the tilt, defaulting to 0.4 quality is the
*optimistic* direction, the wrong one for an unrecognised grade). **[KNOWN]**, listed verbatim
in `NEXT_STEPS.md` §3's "Smaller, verified" list.

---

## cleanup.py:174-177 — `thin_description` sets the flag but never sets `changed` [KNOWN, VERIFIED]

```python
if len(cd) < _THIN:
    thin.append((src, nm, cd))
    if args.apply:
        e["thin_description"] = True
```

Contrast with every other qualifying branch in the same loop (`nav.append` at 152-157,
`_EMPTY_MECHANIC` at 161-167, `desc_fixed` at 168-173) — each of those sets `changed = True`
next to its mutation. This one does not. If a record's *only* qualifying condition this run is
"description too thin" (no nav removal, no ceiling fix, no markup strip), `changed` stays
`False`, so `PL.write_record(path, rec)` (line 179-180) is **skipped** — `e["thin_description"]`
is mutated only in the in-memory `rec`, never persisted, and the record is still printed in the
"marked" tally with `--apply` on, misreporting success. VERIFIED by direct read; matches
`NEXT_STEPS.md` §3 exactly. **[KNOWN]**.

---

## New findings, not previously called out by file

### pantheon.py:261 and genre.py:241 — ignored `silence.write_json` return value

```python
# pantheon.py:261
silence.write_json(OUT, out, indent=1, ensure_ascii=False)
```
```python
# genre.py:241
silence.write_json(p, out, indent=2, ensure_ascii=False)
```

`silence.write_json` (confirmed by reading `silence.py:246-287`) returns `True` only if the
atomic replace succeeded; on a persistent Windows `PermissionError` (a reader holding the file
open across all retry attempts) it returns `False` **and never raises** — "the caller's write
lands next round" is `replace_retry`'s own stated contract. Neither `pantheon.py`'s nor
`genre.py`'s call site checks the return value, so on a denied replace the process prints
"wrote {path}" (genre.py:242) or exits 0 (pantheon.py, no message but no error either) while the
file was **not actually updated** — the previous, now-stale copy of `PANTHEON.json` /
`GENRES.json` remains on disk, and nothing downstream is told. This is the exact pattern
`NEXT_STEPS.md` §3 already generalises ("audit every ignored `write_json` return in the tree")
against three *other* named files (`navtree.py:263`, `catalogue_codex.py:203`, `scope.py:119`)
— **these two are new instances of that same known pattern, not previously named.**
VERIFIED (silence.py's return contract read directly; both call sites read directly; neither
captures or branches on the return).

Practical severity: low-to-moderate. `GENRES.json` is read by `navtree.py` and `profile.py`
(genre.py's own comment at 237-240 says so); `profile.py:129-138` (flagged elsewhere in
NEXT_STEPS) already turns a failed *load* into a silent `{}` default-everything fallback, so a
silently-stale `GENRES.json` compounds with that existing gap rather than introducing a new
failure mode on its own — but it is still a write that can silently no-op.

---

## Modules read end to end and found CLEAN this run

- **`src/lognames.py`** (36 lines, full read) — plain constants module (`READ`, `ROLL`,
  `PIPELINE`, `RECATALOGUE`, `SWEEP`, `CALIBRATE` log filenames + their `OWNER` process-fragment
  map). No logic, no writes, no caps. Matches the already-CLEAN listing from run #24.
- **`src/genre.py`** — aside from the ignored-`write_json`-return instance above (a return-value
  hygiene issue, not a correctness bug), the module is otherwise sound: the Hard Rule 0 `cap`
  parameter is explicitly *refused* with a `SystemExit` and a worked before/after example
  (lines 173-177), `classify_text`/`classify_source` are uncapped over `rec["entries"]`, and the
  `low[:5]` / genre-distribution prints in `main()` are console-report truncations of an
  already-fully-computed, uncapped `out` dict — not data loss.
- **`src/custodes.py`** — the module's actual math (degrees-of-freedom coverage check, Custos
  reading computation, `convene()`'s dispersion/interval logic, Threnody's veto threshold) is
  internally consistent and was traced end to end; the only defects are the two already-KNOWN
  ones (`_ATT_BASE` duplication, MID-quality default) documented above.

---

## Summary of severity

- **1 new security-critical finding, VERIFIED with 28-candidate test table, 8 ADMITTED**:
  `local_agent.py` denylist bypass #4 (case-sensitive `.py`/`.json`/`.yaml` suffix checks in
  `_safe()`'s caller and `_gates()`).
- **4 KNOWN findings re-confirmed at source** (backup-never-on-disk, build_terminal innerHTML
  x3+1, custodes `_ATT_BASE` duplication + MID-quality default, cleanup.py `changed` bug).
- **2 new instances of an already-known pattern** (ignored `write_json` return in `pantheon.py`,
  `genre.py`).
- **3 modules fully clean** (`lognames.py`; `genre.py` and `custodes.py` clean apart from the
  items above).
