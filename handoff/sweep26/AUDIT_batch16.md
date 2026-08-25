# BATCH 16 AUDIT — run26

Modules (read in full, every line): `build_terminal.py` (579), `local_agent.py` (579),
`custodes.py` (418), `ingest_doc.py` (302), `render.py` (252), `chord_field.py` (203),
`repass_bands.py` (119). Total 2,452 lines.

Subprocess spawn check: all four `subprocess.run` calls (all in `local_agent.py`, lines
216, 346, 373, 384) pass `creationflags=_NO_WIN`. Compliant, no bare-window spawns found in
this batch.

Bare `except:` check: none found in any of the seven files — every catch is `except Exception`
(often with `silence.note(...)`). No new swallowed-failure class found here beyond what's noted
below.

---

## 1. `local_agent.py` — attacker's-eye audit (special focus)

This module has already absorbed four documented gate-bypass fixes (case-folding m113,
name-prefix m114, NTFS-ADS m121, and the case-sensitive `.endswith(".py")` fix from run #25,
all narrated in the source's own comments at `_safe()` lines 233-271 and `t_propose_patch()`
lines 393-433). I re-derived each from source rather than trusting the comments, and hunted for
a fifth.

### MAJOR — `.pyw` is not covered by either denylist path (latent bypass #5-shaped)

`t_propose_patch()` line 407:
```python
_lower = full.lower()
modname = os.path.basename(full)[:-3] if _lower.endswith(".py") else None
```
`"foo.pyw".lower().endswith(".py")` is `False` (the last three characters are `"pyw"`, not
`".py"`), so for any `.pyw` file `modname` comes out `None` — the exact same shape as the run
#25 bug (`src/foreman.PY` case bypass), just via a different literal extension instead of a
different case. Consequences, traced through:

- `_deny`/`_deny_paths` in `t_propose_patch()`: `modname` is `None` so the module denylist can't
  match; `rel` (e.g. `"src/foreman.pyw"`) isn't in `DENYLIST_PATHS` (which holds only
  `"config.yaml"`), so the path denylist can't match either. **Denylist is bypassed.**
- `_gates()` line 341: `if full.lower().endswith(".py")` is `False` for `.pyw` → parse and lint
  are skipped entirely (same as every prior bypass). Line 372: `if full.lower().endswith(".py")
  and modname:` is also `False` → the import gate is skipped too. Only the whole-suite
  `verify_math` run applies (same residual coverage the four prior bugs left).

**Verdict: ADMITTED in the code, but currently unexploitable in practice** — `find . -iname
"*.pyw"` over the whole repo returns nothing (verified), and `propose_patch` requires
`os.path.isfile(full)` to already be true, so there is no live `.pyw` file to patch through this
door today. Flagging because the shape is identical to four bugs already fixed here, and CPython
does not import `.pyw` via `import modname` anyway, so this can't presently be used to edit
`foreman`/`silence`/etc. under an alias — but it CAN silently degrade the parse/lint/import
guarantee for any `.pyw` file added to the repo later (e.g. a `pythonw`-launched helper).
**Recommended fix**: derive the "is this Python" test once (`_lower.endswith((".py", ".pyw"))`)
and reuse it in both `t_propose_patch` and `_gates`, the same way case-folding was centralized.

### Full enumeration of the paths I tried to reach a write through, and how I determined the verdict

All verified by reading `_safe()` (lines 233-271) and `t_propose_patch()` (lines 393-433)
directly, and cross-checked several with a **read-only** Python repro (`os.path.splitdrive` /
`os.path.abspath` against `HERE`, no files touched):

| Spelling tried | Verdict | How determined |
|---|---|---|
| `src/Foreman.py` (case) | DENIED | `_deny`/`_deny_paths` are built by lowercasing both sides (line 426-427); confirmed by reading run #23's own fix comment and the set-comprehension. |
| `src/foreman.PY` (case-sensitive `.endswith`) | DENIED | Fixed at run #25 — `modname` now derived via `_lower.endswith(".py")`, case-folded first. |
| `src/foreman.py::$DATA` (NTFS ADS) | DENIED | Colon-in-component check in `_safe()` (lines 253-260) refuses any path component containing `:` past the drive letter. Reproduced the abspath/splitdrive split by hand; the ADS suffix survives into `tail` and is caught. |
| `src/foreman.py ` / `src/foreman.py.` (trailing space/dot) | DENIED | `comp != comp.rstrip(". ")` per-component check in `_safe()`; `rstrip(". ")` strips both trailing dots and spaces, so any component Windows would silently normalize away is refused outright. |
| `..\..\evil.py` (traversal) | DENIED | `os.path.abspath` resolves `..` before the `HERE + os.sep` prefix check; anything outside collapses to a path that fails `full.startswith(HERE + os.sep)`. |
| `panscriptum-library-kit-EVIL\x.py` / the `-export` sibling (prefix, not boundary) | DENIED | Already fixed (run #23): the check compares against `HERE + os.sep`, not a bare `startswith(HERE)`, exactly to close this. Confirmed by reading lines 262-268. |
| `\\server\share\foreman.py` (UNC) | DENIED | Read-only repro: `os.path.splitdrive` gives `drive="C:"` (from `HERE`, since `os.path.join` on Windows keeps the base drive when joining a rootless UNC-ish string) or the raw UNC drive; in every combination tested the resulting `full` does not start with `HERE + os.sep`. Confirmed empirically (see repro output). |
| `\\?\C:\...\src\foreman.py` (extended-length prefix) | DENIED | Repro shows `os.path.abspath` does **not** strip the `\\?\` marker the way it would a normal path — `full` becomes `C:\?\C:\Users\...`, which fails the `HERE + os.sep` prefix test. Denied, but for an accidental reason (string mismatch) rather than deliberate handling — flagged as a QUESTION below. |
| `C:foreman.py` (drive-relative, no root) | DENIED (falls through to "no such file") | Repro shows this resolves to `HERE\foreman.py` (not `HERE\src\foreman.py`), which doesn't exist, so `os.path.isfile` fails. Inside the boundary, but not the file an attacker wants. |
| Absolute path already under `HERE` (e.g. `C:\...\panscriptum-library-kit\src\foreman.py`) | DENIED (correctly, on the denylist) | Resolves inside the project, `modname == "foreman"`, case-folded denylist match fires as designed. This is the control case confirming the mechanism works, not a bypass. |
| `src/foreman.pyw` (new extension) | **ADMITTED in the code / no live target** | See MAJOR finding above. |
| Symlink/junction under a different name pointing at `foreman.py` | **ADMITTED in the code / no creation vector** | `_safe()` never calls `os.path.realpath`, only `os.path.abspath` — so a same-repo symlink named e.g. `src/helper2.py` that actually points at `foreman.py`'s bytes would resolve `modname == "helper2"`, missing the denylist, and the write would land on the real file through the alias. **However**: the harness gives the model no tool that can create a symlink (`os.symlink`/junction is never called anywhere in `local_agent.py`, and the four exposed tools are read_file/list_dir/grep/propose_patch/find_symbol/run_check — none can create filesystem objects), and `find . -type l` over the whole repo returns nothing today. So this is a real structural gap (worth closing with `os.path.realpath` + a re-check against `HERE` and the denylist) but not presently reachable by the model acting alone. |
| Unicode homoglyph (e.g. Cyrillic "е" for Latin "e" in `foreman.py`) | DENIED | NTFS does not fold Unicode look-alikes; the literal bytes wouldn't match the real `foreman.py` filename, so `os.path.isfile` fails on the homoglyph path and there is nothing to write to. |
| `src/foreman` (no extension, matching module name with a data file) | DENIED (no such real file) | Not a live file in this repo; if it existed `rel` would need to be added to `DENYLIST_PATHS` (path-based match works for any non-`.py` name), but nothing currently creates a bare `foreman` file. |

### MINOR — `_safe()`'s second colon check (line 259-260) looks dead

```python
if ":" in raw.replace("\\", "/").split("/")[-1]:
    return None
```
This re-checks the colon condition against the **pre-abspath** `raw` string's last component,
after the per-component loop over the **post-abspath** `tail` (lines 254-258) has already
checked every component including the last one for a colon. I could not construct an input
where the second check catches something the first doesn't — belt-and-suspenders, not a bug,
but worth confirming intentionally next time this function is touched rather than assuming it
does independent work.

### QUESTION — `\\?\` extended-length prefix is denied by accident, not by design

Noted in the table above: it's refused because `os.path.abspath` mangles the `\\?\` marker into
something that no longer string-matches `HERE`, not because `_safe()` recognizes and rejects
the form deliberately. The outcome (deny) is correct today, but a future Python/OS path-handling
change that normalizes `\\?\` prefixes differently could silently flip this. Worth a comment or
an explicit check if anyone wants this hardened rather than accidentally safe.

---

### MAJOR — `SLICE` is reused for both the read-file *window* and the tool-message *transport
cap*, so paging metadata is silently eaten (lines 49-51, 274-284, 561)

```python
SLICE = 12000   # chars per read_file call
...
def t_read_file(path, offset=0, **_):
    ...
    return {"path": path, "offset": off, "slice": text[off:off + SLICE],
            "chars_after_slice": max(0, len(text) - off - SLICE), "total_chars": len(text)}
...
messages.append({"role": "tool", "content": json.dumps(res)[:SLICE]})
```

The module's own docstring promises: *"read_file any file under the project, sliced --
iterative reads, never a truncation"* (line 11), and `t_read_file`'s tool description says the
model can "page with offset until 0 remain" by watching `chars_after_slice`. But the *same*
constant, 12000, is used both to build the raw slice **and** to cap the JSON-serialized message
sent back to the model. For any file read from `offset=0` where the remaining text is >= SLICE
chars (i.e. almost any file in this batch — all seven audited modules are 4-20 KB), the `"slice"`
field alone is already ~12000 characters before JSON-escaping and wrapper overhead (`"path"`,
`"offset"`, the trailing `"chars_after_slice"`/`"total_chars"` fields, quoting). `json.dumps(res)`
is therefore reliably **longer** than 12000 characters, and `[:SLICE]` chops it — cutting into
the tail of `"slice"` itself and, because dict insertion order puts them last, **always
discarding `"chars_after_slice"` and `"total_chars"` entirely, with no `"truncated": true` flag
or any other disclosure.**

This directly contradicts:
- the docstring's "never a truncation" claim,
- the tool description's explicit paging contract ("says how much remains so nothing silently
  falls off the end" — line 50-51's own comment),
- and the pattern the rest of this same file follows correctly: `t_run_check` (lines 221-230)
  explicitly labels its own tail-truncation (`"truncated": len(out) > len(tail)`, `"note":
  "showing the last 6000 characters..."`). `t_read_file`/`t_grep`/`t_find_symbol` get no such
  disclosure when the *transport* layer truncates them at line 561 — only `t_run_check`
  deliberately truncates and says so; everything else is truncated by accident, silently.

Same mechanism silently truncates `t_grep`'s (correctly Hard-Rule-0-uncapped) `hits` list and
`t_find_symbol`'s `definitions` list whenever they're large — the internal computation is
uncapped as designed, but the transport hop back to the model is not, and nothing tells the
model that's what happened. A model reasoning from `"matches": 340` but receiving 40
JSON-truncated `hits` entries has no way to know it saw a partial view.

**Recommended fix**: give the message-transport cap its own constant (distinct from the
content-window size), and when it fires, truncate a serialized *string* field inside the result
dict (not the whole JSON blob) and set an explicit `"truncated": true` — the same discipline
`t_run_check` already uses.

### MINOR — `custos`/veto plumbing in `custodes.py` is not actually this module's concern (see
below); no additional local_agent findings beyond the two above and the enumeration table.

---

## 2. `custodes.py`

**Not a guard/gate module** — it's the assay's "college of standpoints" statistics engine
(dispersion of ten Custodes' readings into a consensus decimal + interval), not file-write
policing. The adversarial-guard lens from the special focus doesn't apply structurally, but I
still read every line for the general lens (correctness, swallowed failures, unreachable
guards, dead code).

### QUESTION — `covers_every_reading` (line 344) is a tautology, and the code already says so

```python
"covers_every_reading": all(abs(v - consensus) <= half + 1e-12 for v in vals),
```
`half` is defined a few lines above as `max(1.96*total_sd, max(abs(v-consensus) for v in
vals))` and only ever widened afterward — so this is true by construction for every input and
cannot fail. **This is already fully self-documented** in the comment directly above it (lines
335-343: *"this is a GUARANTEE being published, not a check being run... it must not be mistaken
for verification"*), including the honest admission of what a real check would look like
(whether the un-widened 1.96·sd band alone covered every reading). Flagging per the sweep's
lens #7 for completeness; no new information — the author already caught and documented this.

### MINOR — the per-reading `veto` field is computed but never consulted

`_custos_reading()` line 267 returns `"veto": bool(c.get("veto"))` for every Custos (only
`Threnody` has `veto=True` in `CUSTODES`). Nothing in `convene()` reads this field back off any
`readings[i]["veto"]` — the actual veto mechanism is entirely separate, gated on `eta` and
`CURL_VETO_THRESHOLD` (lines 352-356). The per-reading flag is vestigial: harmless, but a reader
skimming `convene()` could reasonably expect the `veto` field on Threnody's reading to be what
triggers `threnody_veto`, and it isn't.

No other correctness issues found — the derived-attestation-quality table (`ATTESTATION_QUALITY`,
lines 221-234), the private-weights-dict-per-Custos fix (line 246-252, correctly avoiding the
documented "mutate the shared global" hazard), and `staleness_widening`'s clipping are all sound.

---

## 3. `ingest_doc.py`

### MAJOR — the provenance write in `main()` doesn't gate on `write_record`'s return (line 292-293)

```python
if "ingest_doc" not in (rec.get("provenance") or ""):
    rec["provenance"] = (rec.get("provenance") or "") + note
    import pipeline as P
    P.write_record(rp, rec)
except Exception:
    silence.note("ingest_doc.py:provenance")
```
`pipeline.write_record()` returns `False` on a denied/refused write (confirmed by reading its
source: it returns `_landed(tmp, path)` on the normal path and `False` on an unmergeable read —
see `pipeline.py` lines 503-556). That return value is discarded here. If the write is refused
(e.g. concurrent access on Windows, or a torn file mid-write by another process), nothing
raises — `write_record`'s whole contract is to fail *without* an exception — so the `except
Exception` guard never fires, and the run proceeds believing the provenance note landed, with no
warning printed.

**This is the identical class of bug this exact file's own `mine()` function goes out of its way
to prevent 25 lines later** (lines 233-251, with an extensive comment explicitly titled
"ADVANCE ON THE WRITE, NOT ON THE INTENT"), and the same discipline `repass_bands.py` implements
at line 84-87 ("GATE ON THE WRITE"). The provenance note is lower-stakes than the entity list
(it's a descriptive sentence, not catalogued data), and a subsequent `--pdf` run would retry it
(the `"ingest_doc" not in provenance` guard re-checks disk state each invocation), so this
self-heals on a later run — but today it fails *silently* rather than printing the same
"WRITE DENIED" message the file's other writer paths do.

**Recommended fix**: `if not P.write_record(rp, rec): print("  provenance write denied for %s"
% rp)` to match the file's own established idiom.

### MINOR — `record_path()`'s substring fallback is non-deterministic and unguarded against
ambiguity (lines 116-126)

```python
want = slug(source)
for fn in os.listdir(RECORDS):
    base = fn[:-5]
    if want in base or base in want:
        return os.path.join(RECORDS, fn)
```
`os.listdir()` order is filesystem-dependent (not sorted), and the containment test
(`want in base or base in want`) is a first-match-wins scan with no disambiguation and no
warning if more than one file matches. **Verified empirically against the live corpus** (216
record files): zero pairs currently collide under this test, so there is no live misrouting
today. But nothing prevents two future sources whose slugs are substrings of each other (e.g. a
"Warhammer 40,000" and a later "Warhammer 40,000: Dawn of War" companion doc) from silently
routing an ingest into the wrong record, with whichever file `os.listdir` happens to return
first. Recommend sorting candidates and/or raising when more than one match is found, rather
than silently picking one.

No other issues: the resumable-cursor write (lines 253-259, atomic tmp+`silence.replace_retry`),
the pool-then-local `_ask()` fallback, the 60-miss stop-condition, and the `[:2000]` description
truncation (line 216) were all checked against Hard Rule 0 — the `[:2000]` is a per-field content
bound (not a roster/listing cap), consistent with the project's established "sample vs. cap"
distinction; the entity *list* itself (`entries`) is fully uncapped, matches the file's own "the
whole document is extracted... every chunk is mined" claim.

---

## 4. `render.py`

No correctness bugs found. `children_of()`'s tree-driven (not schema-asserted) gating on
whether the sevenfold tree charts a child tier is exactly the kind of "checks the data, not an
assumption about the data" the file's own comment (lines 169-175) claims it to be — verified by
reading the logic, not just the comment. `containment_svg()` correctly `html.escape()`s every
interpolated string. `view()`'s `galaxy`/`star`/`map_seed` params are un-validated (a caller
passing `galaxy=None` for tier `"galaxy"` would get a URL with the literal string `"None"` in
it) but `view()` is an internal dispatcher called only from `main()`'s own demo code and (per
grep) `generate.py` elsewhere with real values — not a live bug, just unguarded, noting as a
QUESTION only if the caller surface grows.

`main()`'s `WS.build_all(limit=1)[0]` (line 222) is a one-sample fetch for the CLI printout demo
table only — does not touch generation output — legitimate bound, not a Hard Rule 0 violation.

---

## 5. `chord_field.py`

Pure physics-constants/adjudication-table module (no file I/O, no writes, no subprocess). No
correctness bugs found in the formulas (`landauer_floor`, `recoil_momentum`,
`recoil_velocity`, `critical_power_self_focus` all match their stated real-physics formulas).

### MINOR — `G_NEWTON` and `HBAR` (lines 36-37) are defined but never used in this file

Both constants are duplicated (with identical values) in `scale_theories.py` and
`descending_ladder.py`, which is where they're actually consumed. Dead code in this file —
harmless, but worth removing or noting as intentionally-kept-for-reference if that's the intent.

---

## 6. `repass_bands.py`

Correctly gates every record write on `PL.write_record()`'s return (lines 84-87, with its own
explicit comment citing the run #25 lesson) — this is the file the `ingest_doc.py` MAJOR finding
above should be brought in line with.

### MINOR — hardcoded `"of 211"` in the source-ceiling report line (line 98)

```python
print(f"  demoted to unassayed: {len(demoted_sources):,} of 211")
```
`211` is a magic number for "how many sources exist," not derived from `len(recs)` (which is
already available at that point in `main()`). If the corpus grows or shrinks, this label goes
silently stale while the rest of the report stays accurate. Recommend
`{len(recs)}` in place of the literal.

The `kept_entries[:14]` / `demoted_entries[:8]` slices (lines 102, 108) are console-report
samples only — the actual demotion logic above (lines 43-87) operates over the full,
un-truncated `rec["entries"]` for every record, and the print statement at line 105 explicitly
labels its own slice "a sample of what was carrying a Magnitude." Consistent with the project's
established ranking/sampling-for-display carve-out, not a Hard Rule 0 violation.

---

## 7. `build_terminal.py`

The `<script>`-injection defense (`data.replace("<", "\\u003c")`, line 568, with its own m10
citation) is correct: JSON syntax never uses a bare `<` outside a quoted string, so every
literal `<` in the source `NAVTREE.json` text must be inside a JSON string value, where
`\u003c` is a valid escape that round-trips to the same character — verified by reasoning
through JSON grammar, not just trusting the comment. This also defeats `<!--`/`<script` parser
tricks since both require a leading `<`.

The `roster` panel (line 55, with its own comment citing the earlier Hard-Rule-0 fix where a
cap of 8 hid 30 of 38 sources) is correctly uncapped now — bounded by CSS `overflow-y:auto`
scroll, not truncation. All source/world rings (`ss`, `ws` loops) render every element; only the
*displayed label text* is shortened (`.slice(0,18)`/`.slice(0,22)` etc.) while the full name
survives in the `<title>` tooltip and the side panel — consistent with the same established
carve-out.

### QUESTION — `shelfmark()`'s tier-label lookup would silently print `"undefined"` if a node
key ever exceeded 5 segments (lines 461-471, JS)

```js
const TIERS=["hyperverse","xenoverse","metaverse","multiverse","universe"];
...
function shelfmark(k){
  ...
  for(let i=0;i<parts.length;i++){
    const key=parts.slice(0,i+1).join("."), nd=DATA.nodes[key];
    s+=" › "+((nd&&nd.name)||LABEL[TIERS[i]]+parts[i]);
  }
```
If `parts.length > TIERS.length` (5), `TIERS[i]` is `undefined` for the 6th+ segment, so
`LABEL[undefined]` is `undefined`, and the breadcrumb would literally print `"undefined" +
parts[i]` (e.g. `"undefined5"`) for any node whose `name` field is also missing. **Not currently
reachable**: `DATA.nodes` keys top out at the `universe` tier (5 dot-separated segments) per the
`TIER_OF` mapping and the data this file's own comments describe (worlds/sources are attached
as leaf arrays on a universe node, not given their own deeper dotted keys), and `shelfmark()` is
only ever called with `rootKey` (max 5 segments) — confirmed by tracing every call site
(`panel()`, `selectSource()`, `selectWorld()` all pass `rootKey`, never a synthesized deeper
key). Flagging as fragile-if-the-invariant-changes, not a live bug.

No other issues found in the JS: the dynamic-radius/font-fit math (`discR`, `fitIn`, `ringR`,
`ringFits`) is self-consistent with the comments explaining each fix; `resetView()`/
`applyView()`/`clampView()` correctly guard against the documented divide-by-zero-on-detached-svg
regression; `bindStage()`'s `_stageBound` guard correctly prevents double-binding across
redraws; the `holds` SUM-not-short-circuit fix (line 480-484) is correctly implemented as
described.

---

## Summary of severities

- **MAJOR**: `local_agent.py` SLICE double-duty (transport truncation eats paging metadata,
  contradicts docstring); `local_agent.py` `.pyw` extension gap (latent, same shape as 4 prior
  fixed bugs); `ingest_doc.py` ungated provenance write (same bug class the file's own `mine()`
  and `repass_bands.py` already defend against).
- **MINOR**: `local_agent.py` symlink/realpath gap (no creation vector today); `local_agent.py`
  dead redundant colon check; `ingest_doc.py` `record_path()` ambiguous substring fallback (0
  live collisions, unguarded); `repass_bands.py` hardcoded "211"; `custodes.py` unused `veto`
  field; `chord_field.py` unused `G_NEWTON`/`HBAR`.
- **QUESTION**: `local_agent.py` `\\?\` prefix denied by accident not design; `custodes.py`
  self-documented tautological `covers_every_reading`; `build_terminal.py` shelfmark tier-index
  fragility if the tree ever grows a 6th coordinate tier; `render.py` unvalidated `galaxy`/`star`
  params in `view()`.
