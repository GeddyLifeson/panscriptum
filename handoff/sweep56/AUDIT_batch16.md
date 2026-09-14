# AUDIT — sweep56, batch 16

Modules read in full, top to bottom: `src/hostcheck.py` (1636 lines), `src/binding_health.py`
(1545 lines), `src/rosetta.py` (793 lines), `src/secondopinion.py` (693 lines),
`src/handbuilt.py` (516 lines), `src/render.py` (429 lines), `src/events.py` (336 lines),
`src/citecheck.py` (260 lines), `src/whoruns.py` (159 lines).

No edits made. No network probes run. No fixes applied.

---

## DEFECT 1 — citecheck.py: the `_PATH_LEAD` guard silently skips real, in-tree citations
written with a `src/` prefix, and this is a *proven* live undercount, not a theoretical one.

**Where:** `src/citecheck.py:73` (definition), used at `src/citecheck.py:189-190`:

```python
_PATH_LEAD = ("/", "\\")
...
if m.start() > 0 and raw[m.start() - 1] in _PATH_LEAD:
    continue
```

**What is wrong.** The module's stated purpose is to catch `file.py:NNN` citations that have
rotted. The `_PATH_LEAD` check exists to exclude citations into *other trees on this machine* —
the docstring names `cascade/engine.py`, `motoko/discord_bot.py`,
`deprecated/catalogue_local.py`. But the check is purely syntactic: it treats **any** character
immediately before the matched filename that is `/` or `\` as proof the citation names "another
tree" — it does not distinguish a genuinely foreign path from a citation that merely spells out
`src/` before a file that **is** `src/citecheck.py`'s own resolvable target. A citation written
as `src/liveness.py:197` matches `CITATION` starting at `liveness.py`, sees `/` immediately
before it, and is skipped entirely — not even counted as `UNRESOLVED`. It is never classified,
never checked against the file, and never reported.

**This is not hypothetical.** `src/secondopinion.py:438` contains exactly this citation:

```
* `liveness.scan()` takes NO root (src/liveness.py:197) and always reads `src/`. It cannot
```

I checked `src/liveness.py:197` directly: it is `elif isinstance(n, ast.ImportFrom) and n.module:`
— an unrelated line inside an import-alias walker. `def scan():` is actually at
`src/liveness.py:348`. The citation has rotted (the line has drifted from wherever it used to
point). `citecheck.py` never reports this, and cannot, because the `src/` prefix routes it
straight past `_classify` via the `_PATH_LEAD` continue at line 189-190. This is the exact
"detector cannot silently undercount" failure mode the sweep brief calls out for this module: a
whole class of real, resolvable, currently-broken citations (any citation that spells out `src/`
or `src\` before the filename) is invisible to `stale_citations()`, with no UNRESOLVED entry, no
count, nothing — the report reads as if those citations do not exist.

Also affected the same way (not independently confirmed stale, but equally invisible to the
checker): `src/verify_math.py:5618` cites `src/prose_gate.py:34`.

**Why it matters.** This is precisely the module's own stated failure class ("line citations in
`src/` comments that have rotted, because every edit above a cited line moves it and NOTHING
ANYWHERE CHECKS") reoccurring inside the checker meant to close it, for the specific subset of
citations that happen to be written with a leading `src/`/`src\`.

**Confidence: DEFECT.** Verified against the live file contents (`liveness.py:197` vs. the actual
`def scan()` location at line 348), not inferred.

---

## DEFECT 2 — unmarked display truncations reintroduced in three modules this batch, after the
identical pattern was hunted down and fixed everywhere else in the tree

The project's own established doctrine (stated explicitly in `binding_health.py`'s `_preview`
docstring, and enforced via repeated "UNCUT" fixes cited by order-hash in `hostcheck.py`,
`rosetta.py`, `render.py` and `handbuilt.py`, all read in this batch) is: a display truncation is
acceptable *only* when something marks that the cut happened (an appended ellipsis, or an "and N
more" note); a bare `[:N]` slice with no marker is refused, because a reader cannot tell a short
field from a clipped one. Three sites in this batch's other, less-visited modules still have the
bare, unmarked form:

**`src/events.py:319`**
```python
print("  %-16s %s" % (e["code"], (e["heading"] or "(cited without a heading)")[:58]))
```
A Chronicle event heading longer than 58 characters is cut with no ellipsis and no note. The
stored `EVENTS.json` keeps the whole heading (this is `main()`'s console report only), but the
operator reading the CLI has no way to know the line was clipped.

**`src/events.py:326`**
```python
print("    %-16s %-46s (%s)" % (r["event"], r["span"][:46], r["rule"]))
```
Same shape, on the `--refused` listing of bolded spans that were not offered to the join — the
one view whose entire purpose is letting a person check the refusal was reasonable.

**`src/whoruns.py:154`**
```python
print("   %-7d %s" % (pid, cmd[:150]))
```
A running process's full command line (returned intact and uncapped by `running()`) is cut to
150 characters on the console with no marker, in the one tool whose whole purpose is telling an
operator exactly what is running.

**`src/citecheck.py:229`**
```python
out.append("           %s" % f["text"][:160])
```
The citing line's text, cut at 160 with no marker, inside `report()` — whose own docstring says
"the findings as printable lines, grouped by citing file, uncapped," which is true of the finding
*list* but not of this per-line field.

**Why it matters.** Same reasoning the sibling fixes already wrote down: a truncated field and an
honestly short one render identically, so a reader cannot know evidence is missing. Low severity
individually (all four are console-only, not stored artifacts), but it is the same class this
project has spent multiple orders closing everywhere else, apparently not yet reaching these four
sites.

**Confidence: DEFECT** (moderate — display-only, not a data-integrity issue, but matches an
established, named anti-pattern exactly and with no offsetting comment arguing these four are
deliberate exceptions).

---

## QUESTION 1 — `binding_health.binding_verdict()` CONFIRMED threshold can be reached by pure
name containment

`src/binding_health.py:858-939`. `token_set_ratio` reaches 100 whenever one name's words are a
subset of the other's, so `BINDING_CONFIRMED_AT = 85` can be crossed by containment alone
(`Prime` inside `Prime World Equipment` scored 50, safely below, but the function's own docstring
says the false positive and the true positives are geometrically the same shape and cannot be
separated by any string metric tried). This is exactly the "false CONFIRMED binding" the sweep
brief asks about — but the module's own docstring already documents this at length, already
explains why tightening the threshold provably makes it worse (`legends` vs `league legends`
would be refused before `Eberron` vs `Eberron: Rising from the Last War` would), and already
surfaces a `containment` field on the record specifically so a caller can distrust a
containment-only CONFIRMED. This reads as a knowingly-open limitation with its evidence already
recorded, rather than an unflagged defect. Noted as a QUESTION rather than a DEFECT because I
have no candidate fix that the module's own docstring has not already tried and rejected with
measurements.

## QUESTION 2 — `citecheck.stale_citations()` scans only the top level of `src/` (`os.listdir`,
not recursive)

`src/citecheck.py:175-177`. If a citing `.py` file existed under a subdirectory of `src/` (e.g.
`src/deprecated/`), its citations would never be scanned — `os.listdir(root)` does not descend.
Today `src/deprecated/catalogue_local.py` is the only such file and it currently contains zero
`file.py:NNN`-shaped citations, so this is not manifesting as a live miscount. It also appears
consistent with the module's own design, which treats everything outside the flat `src/`
namespace (including `deprecated/`) as "another tree" for citation *targets* — so treating it the
same way as a citation *source* may be deliberate rather than an oversight. Flagged as a QUESTION
because the docstring's own phrase ("every provably broken `file.py:NNN` under src/") reads as
broader than what the code does, but I found no live instance where it changes the count.

---

## Modules with nothing found

- **hostcheck.py** — read in full. Extremely heavily self-documented with named orders for prior
  fixes (lift-vs-rate selection, halt re-checks around `_land_hosts`, candidate-list truncation
  vs. Wikipedia's rank, control-sample floor, etc.). Checked the CAS write path
  (`_land_hosts`), the fail-closed import guard in `_assert_not_halted`, and the `score()`
  verdict ladder line by line against its own stated thresholds; found no tautological check, no
  fail-open path, and no undisclosed truncation of a roster or entity list (the `PROBE=40`,
  `sample=12`/`8` and `[:3]` foreign-name caps are all explicitly documented statistical sampling
  bounds on a *measurement*, not truncations of a catalogued list presented as complete).
- **binding_health.py** — read in full. The three-probe canary, the `verdict()` truth table, the
  `_spread` sampling (fixing an earlier alphabetical-head bug), and both compare-and-swap paths
  (`quarantine()`, `release()`, and `run()`'s filtered-merge `_land_cas`) all take the digest
  before the read, fail closed on an unreadable quarantine file (`QuarantineUnreadable`), and
  capture every write verdict into the stored row rather than discarding it. No CAS gap found
  beyond the containment-scoring question noted above.
- **rosetta.py** — read in full. `numeric_rows`/`ordinal_rows`/`stand_rows` row-vs-proximity
  parsing, the `MINE_FLOOR` shrink guard on `--mine`, and the host-scoped `check()`/`refine()`
  join were all checked against their own worked examples (Gecko Moria/Blackbeard row-bleed,
  the `Ｉ`-lowercasing offset bug, the `_norm(key)` global-vs-scoped join). No undercount or
  fail-open path found.
- **secondopinion.py** — read in full, with particular attention to the sweep brief's specific
  concern. Verified on every path that a tool reporting other than `"RAN"` (including
  `"NOT INSTALLED"`) never contributes to `ran_clean()`, is always surfaced by `missing()`, is
  always printed as "NOT AN ALL-CLEAR" in `report()`, and is always filed as its own
  `SECONDOPINION_ABSENT_*` work order in `file_orders()` rather than silently dropped. The
  `_ruff`/`_vulture`/`_detect_secrets` return-code handling was checked against each tool's
  documented exit codes and does not read a CLI-usage error (rc=2, empty stdout) as a clean pass.
- **handbuilt.py** — read in full (mostly transcribed assay data). `compute()` and `main()`
  checked for the same truncation/tautology classes; none found. The `--full` sentinel handling
  for `"unestimable"` scores is correct or the module would crash on Zalama's own sheet.
- **render.py** — read in full. `children_of()`'s coordinate-completeness guard (raises on any
  missing prefix key, closing two previously-fixed pooling bugs) and `write_views()`'s atomic
  per-file write were checked; both fail closed / report their verdict rather than discarding it.

---

## Summary

- **DEFECTs: 2** (one multi-site: citecheck.py `_PATH_LEAD`; one four-site: unmarked console
  truncations in events.py ×2, citecheck.py ×1, whoruns.py ×1)
- **QUESTIONs: 2** (binding_verdict containment-CONFIRMED; citecheck.py non-recursive scan)
