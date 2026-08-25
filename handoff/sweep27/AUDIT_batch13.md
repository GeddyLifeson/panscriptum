# BATCH 13 — sweep run27

Modules read in full (every line, no sampling): src/overwatch.py (707 lines), src/handbuilt.py
(487 lines), src/rosetta.py (416 lines), src/backfill.py (300 lines), src/genre.py (247 lines),
src/descending_ladder.py (186 lines), src/catalog.py (127 lines). Total 2,470 lines.

Cross-checks performed against files outside the assigned batch (read-only, to confirm/refute a
finding, never edited): assay.py (LADDER/decimal semantics, lines ~105-450), pipeline.py (grep
for `_x` attribute), allsweep.py (grep for the `structure()` reconcile-filter substrings),
data/WIKI_HOSTS.json (DC/SpongeBob/Thomas host mapping), state/backfill.log,
state/dc_backfill.log, state/foreman_backups/backfill.*.py (to date-check whether a suspicious
log pattern was pre- or post-fix).

---

## overwatch.py

### 1. HIGH / CONFIRMED — the whole-file digest retirement mechanism (KNOWN-OPEN, re-confirmed)
`overwatch.py:623-629`, inside `round_once()`:
```python
for fid, f in list(led["findings"].items()):
    if f.get("state") != "open":
        continue
    d = _digest(os.path.join(SRC, f["module"] + ".py"))
    if d and d != f.get("digest"):
        f["state"] = "retired"
        f["retired_at"] = led["last_run"]
```
Confirmed present exactly as described in the brief: this loop runs **unconditionally** every
round (not gated behind `if not skip_model`, so it fires even under `--structure-only`),
iterates **every** open finding with no budget/throttle, and executes **before**
`verify_open(led, ...)` is called (line 632). It compares only the whole-file SHA-256 digest, so
any edit anywhere in a module — including one nowhere near the finding's cited line range —
retires every open finding filed against that file, without a model verdict. `write_report()`'s
"N open (M high)" headline (line 570) is computed straight off `led["findings"]` state, so this
is exactly the mechanism that makes "0 high-severity findings open" green without anything being
fixed.

### 2. HIGH / CONFIRMED — retired/closed findings can never be reopened, compounding #1
`overwatch.py:650-656`, inside `round_once()`'s model-review loop:
```python
for f in found:
    fid = _fingerprint(m, f)
    if fid in led["findings"]:
        continue
    f.update({"state": "open", "first_seen": time.time(), "digest": d})
    led["findings"][fid] = f
    fresh += 1
```
`_fingerprint()` (line 208-210) hashes `module|symbol|actual[:80]` lowercased. The dedup check
(`if fid in led["findings"]: continue`) tests only **key existence**, never **state** — there is
no branch anywhere in the file that transitions a `retired` or `closed` finding back to `open`
when the model rediscovers the same defect. So once #1 retires a finding (because some unrelated
part of the file changed), and the model later re-reads the module and reports the *same still-
real* bug again, the new report is silently swallowed as a "duplicate" of the dead entry — unless
the model's free-text phrasing of `actual` (which varies with temperature/sampling) happens to
differ enough in its first 80 characters to produce a different SHA. This means the retirement in
#1 is not merely "premature," it is frequently **irreversible in practice**: a genuinely open bug
can vanish from the report on one round and then never resurface even though the model keeps
finding it, because every rediscovery collides with the dead key. This is the strongest additional
mechanism making the page's "0 open" claim unreliable beyond the retirement policy itself.

### 3. LOW / CONFIRMED — stale self-referential line-number tags in `silence.note()` calls
`overwatch.py:331` reads `silence.note("overwatch.py:193")` and `overwatch.py:341` reads
`silence.note("overwatch.py:202")`. Verified by direct line count: those tags no longer match
where the calls actually live (they're off by 138 lines — evidently left over from before a
refactor added ~138 lines earlier in the file). Every other `silence.note()` call in this file
uses a stable semantic tag (`"overwatch.py:load"`, `"overwatch.py:save"`, etc.) except these two,
which still use the old line-number convention and are now simply wrong. Cosmetic only — doesn't
affect behavior, but anyone grepping the silence log for "overwatch.py:193" to find this code path
will land on the wrong place.

### 4. LOW / SUSPECTED (question, not a clear bug) — WATCH.md's findings list is capped at 40
`overwatch.py:572-573`: `for f in sorted(open_f, ...)[:40]:` — the rendered list of open findings
in WATCH.md shows at most the newest 40, though the "**N open** (M high)" headline above it
(line 570) is computed from the full uncapped `open_f`, so the count itself is honest. Given Hard
Rule 0's blanket wording ("no cap... on an entry list"), flagging this as a question: is a
report-rendering truncation (with an honest total above it) meant to be exempt, the way
`catalog.py`'s CLI listing is (see finding #15)? Not treated as a hidden-data violation since the
true count is never hidden, just the detail rows past #40.

---

## rosetta.py

### 5. HIGH / CONFIRMED — `--check`'s Assay score omits the magnitude band entirely
`rosetta.py:402-404`:
```python
assays = {k: v["result"]["decimal"] + P.__dict__.get("_x", 0)
          for k, v in json.load(open(path, encoding="utf-8")).items()
          if v.get("result") and v["result"].get("decimal") is not None}
```
Verified against `assay.py:437-447`: `decimal` is `round(_dec, 2)` where
`_dec = value - LADDER.index(anchor)` — i.e. it is **only the within-band fractional remainder**
(roughly 0.00–1.5), never the M0–M10 band index itself (`LADDER.index(anchor)`, the dominant term
for any real cross-character power comparison — this is exactly the composite
`A.LADDER.index(magnitude) + decimal` that `handbuilt.py:468` builds for its own sort key, so the
correct pattern exists in a sibling file and was not used here). Verified `P.__dict__.get("_x", 0)`
is dead/nonsense: `grep` of `pipeline.py` finds no `_x` attribute defined anywhere, so this term
is always exactly `0`. Net effect: every entity's "assay" value fed into `check()`'s Spearman
correlation is just its **within-band decimal**, discarding the magnitude band completely. Since
`check()`'s whole stated purpose (module docstring, lines 9-14, 260-265) is to catch cases where
"our Assay ranks two [characters] in the order their bounties forbid" — a comparison that is
overwhelmingly determined by band, not by the 0-1 decimal remainder — the `--check` command's
rank correlations and DISAGREES flags are close to uninformative regardless of whether the
underlying Assay scores are actually correct or wrong. This is the module's central validation
path and it is broken.

### 6. MEDIUM / CONFIRMED — comment claims Stand statistics are parsed; no code path does it
`rosetta.py:88-92` (comment on `ORDINAL_LADDERS`): "...Stand stats are read from their parameter
block instead (see `_STAND`)." `_STAND` is compiled at line 104-105. Grepped the whole file: no
function ever calls `.finditer`/`.search`/`.match` on `_STAND` — it is referenced nowhere except
that one comment. `numeric_rows()` and `ordinal_rows()` (the only two row-extraction functions
that ever populate `scales_for()`'s output) never touch it either. So JoJo's Bizarre Adventure
Stand statistics ("Power: A", "Speed: B" parameter blocks) are never actually mined by this
module, despite the docstring stating plainly that they are, via a specific named mechanism that
exists in source but is disconnected from every caller. Classic case of lens item #6 (comment
claiming behaviour the code does not have).

### 7. MEDIUM / SUSPECTED — scale-page discovery is capped at 5 search hits per query, unpaginated
`rosetta.py:194`: `d = F.api(host, {"action": "query", "list": "search", "srlimit": "5", ...})`.
No `sroffset`/`continue` handling anywhere in `scales_for()`. MediaWiki's search API caps results
per call at whatever `srlimit` says; with no pagination, any candidate scale page ranked 6th or
lower for *every one* of the 29 `SCALE_QUERIES` terms is permanently invisible to the miner, on
every wiki. This is the same `limit=` shape that `backfill.py`'s `roster()`/`members()` was
specifically fixed (run #26, m140/m141) to remove via full `cmcontinue` pagination — that fix
pattern exists as a sibling in this very batch and was not carried over to rosetta.py's own
search calls. Marked SUSPECTED rather than CONFIRMED because I did not verify live whether any
real wiki actually has >5 relevant hits for a given query term (plausible on large wikis with
many per-arc/season scale pages, e.g. multiple "Power Level" subpages), but the code shape itself
is unambiguous.

### 8. LOW-MEDIUM / SUSPECTED (question) — value-based outlier filter could drop genuine extremes
`rosetta.py:169-171`:
```python
if len(out) >= 8:
    med = sorted(out.values())[len(out) // 2]
    out = {k: v for k, v in out.items() if v <= med * 1000}
```
Framed in the comment as removing parse artifacts (a table-column misread producing an
absurd figure), but it is a blanket value threshold, not a check that the row actually looks
malformed. Many power-level fictions (Dragon Ball chief among them) canonically publish figures
that are genuinely >1000x the field median at the very top of the scale — exactly the kind of
real outlier a Spearman check would most want to keep. Framed as a question rather than a bug:
worth confirming this hasn't quietly deleted a franchise's real top-of-scale figure.

### 9. LOW / SUSPECTED — `ordinal_rows()` only searches backward from the tier keyword
`rosetta.py:181`: `seg = wikitext[max(0, m.start() - 160):m.start()]` — only text **before** a
matched tier phrase (e.g. "god level") is scanned for a `[[Name]]` link within a 160-character
window; there is no complementary forward-window search. Any wiki table/list formatted
"**Tier: Name**" (label precedes the name) rather than "**Name ... Tier**" would silently produce
zero rows for that ladder on that wiki, with no error or signal distinguishing "this ladder
genuinely isn't published here" from "this ladder is published in the other layout." Not verified
against a live wiki page, so SUSPECTED.

---

## backfill.py

### 10. HIGH / CONFIRMED — the "already held" filter is not scoped to Persons, in the dangerous direction
`backfill.py:176`:
```python
have = {re.sub(r"[^a-z0-9]+", "", e["name"].lower()) for e in r["entries"]}
```
This builds the "we already have this" set from **every** entry in the source's record —
Persons, Places, Factions, Vessels/Things, Events, Media, Powers/Systems alike — not just the
`PERSON_CATEGORY` entries the rest of this file is exclusively about (see finding #13). Any wiki
character page whose normalized title collides with an existing non-Person entry's normalized
name (a team, place, vessel, or event sharing a character's name/alias — not an unusual pattern in
long-running franchises) is treated as "already held" at line 178 and is silently excluded from
`missing`, so that real, uncatalogued character is never added. This fails in the dangerous
direction for a module whose entire purpose is recovering under-counted casts: false "already
held" matches directly undercount `missing` and therefore `added`, with no log signal
distinguishing a true duplicate from a name collision.

### 11. MEDIUM / CONFIRMED (mechanism) + SUSPECTED (real-world trigger) — single hardcoded category name, no fallback
`backfill.py:96` and `112`: the entire character discovery walk starts from the literal string
`"Category:Characters"` (top level) with one level of subcategories beneath it, and there is no
alternate spelling, no discovery of what the wiki's actual root character category is called, and
no distinguishing error between "this wiki has zero characters in this category" and "this wiki
doesn't use this category name at all." Confirmed via `data/WIKI_HOSTS.json` that DC, SpongeBob
SquarePants, and Thomas the Tank Engine (the three worst-off sources named in the sweep brief) are
mapped to `dc.fandom.com`, `spongebob.fandom.com`, and `thomasthetankengine.fandom.com`
respectively (all Fandom, so not excluded by the `F.is_wikipedia()` guard in `audit()`). Whether
each of those wikis' actual character category is literally titled "Category:Characters" was not
checked live (no network calls made), so the failure mode itself is SUSPECTED, not confirmed — but
if any of the three uses a different top-level category name, `roster()` returns an empty list for
it silently, matching the "stuck at <2%" symptom exactly.

### 12. MEDIUM / CONFIRMED — `--source` mode has no per-source exception handling (unlike `--all`)
`backfill.py:293-295`:
```python
for s in a.source:
    print(json.dumps(backfill_source(s, recs, hosts, cap=a.cap, dry=a.dry),
                     ensure_ascii=False))
```
Compare `--all`'s loop at lines 276-282, which explicitly wraps each `backfill_source()` call in
`try/except Exception as e: print(...ERROR...); continue`. The `--source` path has no such
guard. `RosterIncomplete` (raised deliberately by `members()` on any transport failure — this
file's own docstring at lines 48-59 names this exact scenario as "the exact defect THIS FILE
EXISTS TO REPAIR, performed by the repair" if it were silently swallowed) or any other exception
raised while resolving one `--source` name will crash the whole process and abort every other
`--source` argument queued in the same invocation, with zero partial results recorded. An operator
running `backfill.py --source "DC" --source "SpongeBob SquarePants" --source "Thomas the Tank
Engine"` to fix the three worst sources in one pass gets nothing if the first one hits a timeout.

### 13. LOW / CONFIRMED-BY-DESIGN (framed as a question) — this module can only ever repair the Persons slice
`backfill.py:45,163,204` (`PERSON_CATEGORY` and every write site): `backfill_source()` only ever
appends entries carrying `"category": PERSON_CATEGORY`. It has no equivalent path for Places,
Factions, Vessels/Things, Events, Media, or Power/Systems categories. Since the sweep brief's
"every source is fully catalogued" standard (17.2% overall, DC 0.5%, Thomas 1.2%, SpongeBob 1.7%)
presumably spans all of those categories, not just Persons, a fully-working `backfill.py` has a
hard ceiling on how far it alone can move any source's overall percentage — it cannot be the
whole explanation for a source stuck under 2%, only the Persons-shaped part of it. Worth
confirming with the owner whether sibling cast-growing repairs for the other categories exist or
are planned, since this file's docstring frames itself as a full "recover the main casts" repair
without noting this scope boundary.

---

## genre.py

### 14. MEDIUM / CONFIRMED — a second, more subtle truncation in the same function family whose primary cap was just removed
`genre.py:135`, `182`, `187`:
```python
def classify_text(text, top=3):
    scores = collections.Counter()
    for g, spec in GENRES.items():
        for pat, w in spec["cues"].items():
            scores[g] += w * len(re.findall(pat, text, re.I))
    return scores.most_common(top)              # line 141

...
ranked = classify_text(" ".join(parts))          # line 182, top defaults to 3
...
total = sum(s for _, s in ranked) or 1           # line 187
```
`classify_text()` scores **all 11** genres in `GENRES` against the full text (no truncation of the
input — the module's own `cap=None` enforcement for `classify_source`'s entry-text scan, lines
144-177, is exactly correct and already fixed), but then returns only the **top 3** via
`most_common(top)`. `classify_source()` uses that 3-item `ranked` list to compute
`confidence = score / total` where `total` sums only those 3 genres' scores — never the other 8.
Any real cue signal in genres ranked 4th or lower (plausible for a source that reads as a blend of,
say, 4-5 genres) is silently excluded from the confidence denominator, which **inflates**
`confidence` and understates how mixed a source actually is — directly undermining the
`< 0.45` "genuinely mixed, flagged not forced" check at `main()` line 218, which relies on this
same value. This is a sibling truncation to the one already fixed in this file (over *ranked
genres* rather than over *input characters*) that the run-27-preceding fix pass did not catch.

---

## handbuilt.py

No correctness, swallowed-failure, cap, two-writer, or concurrency defects found. It is a small,
hand-authored data file (10 entities' Assay worksheets) plus a `compute()`/`main()` that writes
`data/HANDBUILT_ASSAYS.json` correctly via `open(tmp,"w")` + `silence.replace_retry(tmp, OUT)`
(atomic, satisfies the two-writer contract) and checks the return value before declaring success
(lines 456-459).

One cross-module note, not confirmed as a bug in this batch: `compute()` (line 426) builds a
`scores` dict per entity that mixes numeric floats with the literal string `"unestimable"` (all
five of Zalama's un-evidenced axes, lines 182-197) in the same dict passed straight into
`A.assay()`. Whether `assay.py` (outside this batch) actually handles a mixed numeric/string
`scores` dict correctly, or silently miscomputes/crashes on it, was not verified here — worth a
check by whichever batch owns `assay.py`.

---

## descending_ladder.py

No correctness, swallowed-failure, cap, two-writer, or concurrency defects found. Pure
math/constants module (Planck-scale rung table plus a few closed-form physics functions), no
shared state, no writes, single reader. Traced `rung_for_length()`'s stepwise-ceiling loop by
hand against several boundary values (exactly at a rung edge, between two rungs, deep in the
sub-Planck Fold) and it selects the correct rung in every case tried.

One question, not a bug: `rung_for_length()` (line 85-95) silently returns rung 0
("Continental", the file's own top/coarsest rung) for any `metres` **above** the Continental
ceiling of 1e6 m — the loop's `best` initializer is simply never overwritten in that case, with
no error and no signal that the input was outside this module's documented "rungs below Planet"
scope. Likely an intentional "caller's job to only call this for sub-planetary sizes" contract
(the file exists specifically to extend the Ladder *downward*), but there is no guard enforcing
that, so a caller elsewhere that passes a genuinely planet-or-larger size gets a silently wrong
answer rather than an error.

---

## catalog.py

### 15. LOW / CONFIRMED — CLI display truncation on a read-only query tool
`catalog.py:64-67`:
```python
for n in missing[:30]:
    print(f"  - {n}")
if len(missing) > 30:
    print(f"  ... and {len(missing) - 30} more")
```
`cmd_stats`'s "Populated sources with NO books yet" listing shows only the first 30 names. This
is the mildest possible form of the pattern Hard Rule 0 targets — it is a terminal print
truncation on a read-only stats command (not an ingestion path, and the true count is stated both
before the list, at line 63, and after it via "...and N more") — but flagging it per the letter
of the rule ("no cap... on an entry list"), since `catalog.py` is otherwise a purely read-only
tool with no other findings.

No two-writer or concurrency issues: `catalog.py` never writes anything (`load_config`,
`load_catalog`, `load_roll` are all read-only `open(...)` calls, appropriate for a query tool with
no shared-state writes to guard).
