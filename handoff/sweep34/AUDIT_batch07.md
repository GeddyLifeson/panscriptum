# run34 sweep — batch 07

Modules read end to end: `feats.py` (1,259), `manifest_builder.py` (504), `onomast.py` (407),
`address.py` (322), `grounding.py` (258), `propagation.py` (214), `physics.py` (173),
`lognames.py` (36).

Every regex finding below was verified by RUNNING the compiled pattern out of the live module
against real strings, not by reading it. Every count claim was measured against the file on disk.

Two findings were excluded by instruction and are NOT re-filed: `feats._QUANTITY`'s
caret/superscript/multiplication-sign/negative-exponent gaps (order `f842daaba5c5`) and
`onomast.name_worlds()`'s unseeded `taken` set (order `49474966f971`).

---

## feats.py

### F1 — a refusal EARNS SPEED BACK: `note_ok()` fires before the body is parsed  (MAJOR)

`feats.py:277-281`:

```
            with urllib.request.urlopen(req, timeout=TIMEOUT) as r:
                _body = r.read().decode("utf-8", "replace")
                # A CLEAN RESPONSE EARNS SPEED BACK. Without this the backoff only ever
                # grows, so one bad minute would slow a host for the rest of the run.
                note_ok(host)
                return json.loads(_body)
```

`note_ok` is called on line 280; the body is not parsed until line 281. The one case that
reaches this ordering and is not a clean response is a 200 carrying HTML — which the
`json.JSONDecodeError` handler forty lines below describes in its own words as
"what happens when a WAF or a login wall answers an `/api.php` call with an HTML challenge
page" (`feats.py:313-320`). So the module's own named refusal case runs `note_ok`, which does:

```
def note_ok(host):
    """Call on a clean response. Decays the backoff and clears the strike run."""
    with _HOST_LOCKS[host]:
        cur = _BACKOFF.get(host, 1.0)
        if cur > 1.0:
            _BACKOFF[host] = max(1.0, cur * BACKOFF_DECAY)
        _STRIKE[host] = 0
```

Two consequences, both against the file's stated thesis that "a 429 that reads as an absence is
the project's signature failure arriving over the network":

* the host's backoff is decayed by an interstitial, i.e. we speed UP against a host that is
  refusing us;
* `_STRIKE[host] = 0` — so a host answering every API call with a challenge page can never
  reach `THROTTLE_STRIKES` and is never handed to `binding_health.quarantine`. The quarantine
  path exists (`note_throttled`, lines 143-162) and this ordering is what keeps it from firing
  on the refusal shape it most needs to catch.

A 404 does NOT reach this — it arrives as `HTTPError` and returns at line 294 — so the fix is
narrow: parse first, `note_ok` only on a successful parse.

### F2 — the two counters roll() prints are incremented without a lock  (MINOR)

`feats.py:299` (inside `except HTTPError`, and the `_HOST_LOCKS` lock is NOT held here — it is
taken and released inside `_throttle`/`note_throttled`):

```
                _RATE_LIMITED[host] = _RATE_LIMITED.get(host, 0) + 1
```

`feats.py:512` and `feats.py:522`, inside `discover()`, which runs on every worker thread:

```
    if (ap or {}).get("continue"):
        _CAP_BOUND["aplimit"] = _CAP_BOUND.get("aplimit", 0) + 1
...
    if (sr or {}).get("continue"):
        _CAP_BOUND["srlimit"] = _CAP_BOUND.get("srlimit", 0) + 1
```

`roll()` defaults to `workers=8` and the overnight supervisor launches it with `--workers 12`
(`overnight.py:824`). A read-modify-write on a plain dict from twelve threads loses updates.
Both dicts are printed as measurements in `roll()`'s summary (lines 1141-1160) under the file's
own rule that "a measurement nobody prints is not a measurement" — a measurement that undercounts
by an unknown amount is the same problem one floor down. `done` gets this right (it is guarded by
`lock`); these two were left outside it.

### F3 — `page_looks_real`'s `title` parameter is never read  (MINOR)

`feats.py:186`: `def page_looks_real(text, title="", wiki=True):` — `title` appears nowhere in the
body (verified by inspecting the function source at runtime; the only other occurrences of the
word in the function are in the docstring). `binding_health.py:183` passes one:
`real, why = F.page_looks_real(text, title)`. A caller supplying a title has reason to think the
title is being used — e.g. to catch the soft-404 case where a wiki returns a different article —
and it is not.

### F4 — `strip_wikitext` leaves table-cell attributes and inline cell separators in the prose  (MINOR)

`feats.py:730`:

```
    c = re.sub(r"^\s*[!|]\s*(?:[a-z\-]+=\"[^\"]*\"\s*)*\|?", " ", c, flags=re.M)
```

The attribute clause requires a QUOTED value and a lowercase attribute name, and only the cell
marker at the START of a line is handled. Measured by running `feats.strip_wikitext` on real
wikitable fragments:

| input | output |
|---|---|
| `{\| class="wikitable"` / `\|-` / `! colspan=2 \| Power Levels` / `\|-` / `\| Goku \|\| 9,000` / `\|}` | `colspan=2 \| Power Levels\n Goku \|\| 9,000` |
| `{\| class="wikitable"` / `\|-` / `! Style="color:red" \| Header` / `\|-` / `\| align=center \| 42` / `\|}` | `Style="color:red" \| Header\n align=center \| 42` |
| `{\|` / `\|-` / `\| style="width:10em" \| Kaioken` / `\|}` | `Kaioken` |

Only the third (lowercase name, quoted value, leading marker) cleans. The docstring one function
up says table cells are kept and "only the pipe-and-brace scaffolding is removed"; the scaffolding
survives in the first two. This text is what `mine()` splits into feat sentences and what
`magnitude.py` stores verbatim as an instrument-tier citation, so `colspan=2 |` can end up inside
a quoted feat in a published volume. (It does not break the verbatim check, which compares
cleaned text against cleaned text — the harm is a corrupted citation, not a false fabrication
flag.)

### F5 — four stale `silence.note()` line-number labels  (MINOR; BUGS.md m81, never filed as an order)

Measured with grep against the current file:

```
296:            silence.note("feats.py:125")
332:            silence.note("feats.py:139")
617:                silence.note("feats.py:374")
1101:            silence.note("feats.py:695")
```

Each label is 171 to 406 lines away from its own call site. BUGS.md m81 recorded the same drift
at 137/149/425/836 — it has grown since. The named-key labels in the same file
(`api-404`, `api-nonjson`, `corrupt-cache`, `throttle-quarantine`) do not drift.

### F6 — four functions with zero callers  (MINOR; BUGS.md m80, never filed as an order)

Verified by grep across all of `src/`: the only occurrence of each name is its own `def`.

* `resolve_title()` (feats.py:550) — its docstring says it exists because 17,148 entries mined to
  nothing on catalogue-name/wiki-title mismatch. `evidence_for()` calls `discover(host, name)`
  with the raw catalogue name and never calls it, so that loss is, per the call graph, still
  unmitigated.
* `_page_exists()` (feats.py:542)
* `axis_evidence()` (feats.py:876) — its three gates were hoisted into `by_axis()` (lines 904-910)
  and the standalone version was left behind.
* `remine()` (feats.py:1026) — its own comment admits "This function currently has no callers".

### Additional evidence for the already-filed `_QUANTITY` order (`f842daaba5c5`) — not re-filed

Measured against the live pattern:

* `released 10^44 joules of energy` -> `[('44', '', 'joules')]` — a bare power of ten with no
  mantissa parses as the EXPONENT taken as the value.
* `released 5 * 10^44 joules` -> `[('44', '', 'joules')]`
* `released 5 x 10^44 joules` -> `[('5', '44', 'joules')]` (correct)
* `3 x 10 ^ 9 megatons` -> `[('9', '', 'megatons')]` (the filed case, reproduced)

---

## manifest_builder.py

### M1 — the manifest is written with a bare truncating `open`  (MINOR)

`manifest_builder.py:462-464`:

```
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump({"jobs": all_jobs}, f, indent=2)
```

`silence` is already imported in this module (used at line 329). `output/index/manifest.json` is
the file `generate.py --manifest` reads on every generation run, and `generate.py`'s own
`save_json` was made atomic on 2026-08-25 with the comment "a truncate-then-fill here hands those
readers an empty or half-written file". The writer of the file it reads was left non-atomic.
`generate.load_json` does not swallow the parse error (it only defaults on a MISSING file), so the
failure mode is a crash in the middle of a generation run rather than a silent zero — still the
declared defect class, and `silence.write_json` is a one-line substitution.

### M2 — a Feats chapter's `content_hash` omits its `source_context`  (MINOR)

Chapter jobs (`manifest_builder.py:302`):

```
                "content_hash": content_hash({"entries": part, "context": source_context}),
```

Feats jobs (`manifest_builder.py:374`):

```
                "content_hash": content_hash({"entities": slim}),
```

but the feats job carries `"source_context": ctx` at line 373, where `ctx` holds `mode`,
`ceiling_entity`, `provisional_magnitude`, `entities_with_feats` and `feats_in_source`. The
`content_hash` docstring says it "changes automatically whenever the underlying entries/facts
change", and `address.recipe_hash`'s docstring says an address-only key means "generate.py skips
regenerating it, leaving a book built on stale facts with no warning". If a source's ceiling
entity or provisional magnitude is corrected, every chapter regenerates and the Feats chapter
does not — it keeps prose written against the superseded context.

---

## address.py

### A1 — `build_address()` is dead AND stale: it returns the pre-volume address  (MINOR)

`address.py:208` has zero callers anywhere in `src/`; the only other occurrence is its own
`__main__` demo at line 322. That would be a plain dead-code note except for what it returns:

```
    spine = spine_code_for(source_name)
    volume = chapter_slug(chapter_label)
    addr = f"{spine}/{volume}"
```

`manifest_builder.main()` deliberately does NOT use the bare `spine_code_for` result. It builds
`volume_code[name]` first (lines 437-447) precisely because a Series legitimately holds several
sources, and its comment records the measurement: "303 duplicate addresses across 916 of 3,502
jobs" before that fix. `build_address` still hands out the colliding form. A future caller
reaching for the module's named address builder gets the bug the manifest path was repaired to
avoid. Retire it or route it through the volume map — a public-function decision, not a repair.

---

## grounding.py

### G1 — `classify_text(top=3)` truncates a ranked list of 5 and inflates the published confidence  (MAJOR)

`grounding.py:125-130`:

```
def classify_text(text, top=3):
    scores = collections.Counter()
    for name, spec in GROUNDINGS.items():
        for pat, wt in spec["cues"].items():
            scores[name] += wt * len(re.findall(pat, text, re.I))
    return scores.most_common(top)
```

`GROUNDINGS` holds FIVE named types. `classify_source` calls this with the default and then uses
the truncated list as the denominator of the number it publishes (`grounding.py:175`, `183`, `192`):

```
    ranked = classify_text(" ".join(parts))
...
    total = sum(s for _, s in ranked) or 1
...
        "confidence": round(score / total, 3),
```

So two of five scored types are dropped from the denominator and `confidence` comes out too high.
`runners_up` (`ranked[1:]`) likewise only ever holds 2 of the 4 losers.

Measured over all 210 records via `pipeline.records()`, comparing the shipped path against the
same computation with `top=None`:

```
sources whose published confidence is INFLATED by top=3: 14
   major fantasy pantheons            published 0.558  true 0.473  (5 types scored)
   Pantheon: Mesoamerican             published 0.529  true 0.450
   Thomas the Tank Engine             published 0.625  true 0.556
   Marvel                             published 0.553  true 0.493
   Bleach                             published 0.536  true 0.484
   DC                                 published 0.448  true 0.396
   Pantheon: Hindu                    published 0.610  true 0.562
   ...
sources reported NOT contested that actually are (published >= 0.5, true < 0.5): 4
    Bleach 0.536 -> 0.484
    major fantasy pantheons 0.558 -> 0.473
    Marvel 0.553 -> 0.493
    Pantheon: Mesoamerican 0.529 -> 0.45
```

`main()` uses exactly that 0.5 line to report "contested cosmogonies (two accounts run close;
flagged, not forced)", so four sources — Marvel and Bleach among them — are currently reported as
settled cosmologies when the full ranking says they are contested. The number is written to
`data/GROUNDINGS.json` by `--write` and read by `navtree.py` and `pipeline.py`.

This sits directly under a docstring that refuses a different cap in the same function's sibling
("`cap` truncates the origin-entry list in STORED order ... Hard Rule 0 -- rank if you must, never
truncate"). Fixing it changes published numbers, so it is not a silent mechanical edit.

---

## propagation.py

### P1 — the distance anchor in the docstring disagrees with the graph on disk  (MINOR)

`propagation.py:62-64`:

```
# Anchored so that distance 1.0 -- the far end of the measured range, Left 4 Dead to Dragon Ball
# Z -- is a millennium of lateral travel. Same-universe pairs (Alien/Predator at 0.006) then
# come out at ~6 years, which is the right order for "news travels within a universe".
```

Measured today against `data/SHARED_STAGE_GRAPH.json` using the module's own `load_graph()` and
`shortest()` (172 shelves, 1,087 edges, zero disconnected ordered pairs):

```
Left 4 Dead -> Dragon Ball Z            d = 1.1258
Alien -> Predator                       d = 0.0057      (matches "0.006")
true diameter (max finite shortest path) = 4.0707
    Pantheon: Chinese -> DMs Guild: Xanathar's Lost Notes to Everything Else
```

The Alien/Predator anchor still holds. The far-end anchor does not: the far end of the measured
range is 4.07, not 1.0, and the pair named is no longer the extreme. `YEARS_PER_UNIT_DISTANCE`
is calibrated off that sentence, so the module's maximum lateral delay is ~4,071 years where the
prose says a millennium. The constant is a declared, reversible convention (Axiom M3) — the
finding is that its stated justification no longer describes the data.

### P2 — the trailing `return 0` in `observed_mark` cannot be reached  (MINOR)

`propagation.py:152-158`:

```
    lag = years_since - arrival_years(distance)
    if lag < 0:
        return 0
    for rung in range(LADDER_HEIGHT, 0, -1):
        if lag >= ascension_years(rung):
            return rung
    return 0
```

`ascension_years(1)` is `1.0 ** 1.35 - 1.0` = `0.0` (measured), and the guard above guarantees
`lag >= 0`, so the `rung == 1` iteration always returns. The final `return 0` is unreachable.
Harmless in effect, but it reads as the honest-[^0] branch the docstring describes at length,
and it is not — the honest [^0] comes solely from the `lag < 0` guard.

---

## physics.py

### Ph1 — `--table` does not do what its help says  (MINOR)

`physics.py:154` advertises `--table` as "print the specific energies". `main()` prints the
specific-energy table unconditionally (lines 156-163) and only THEN checks the flag:

```
    if a.table:
        return 0
```

Run with `--table` (measured): the table prints. Run without it: the identical table prints,
followed by three worked examples. The flag's only effect is to SUPPRESS the examples. Either the
help text or the ordering is wrong; as written, a reader who wants "just the table" and does not
pass the flag cannot tell the flag exists for a reason.

### Ph2 — `kinetic()` and `joules_for()` have no sign guard, unlike their two neighbours  (MINOR)

`sphere_volume` (line 123) and `binding_energy` (line 146) both refuse a non-positive radius, each
with a paragraph explaining that "a wrong number wearing the shape of a right one is the hardest
kind to catch". The other two entry points in the same file do not:

```
def kinetic(mass_kg, speed_ms):
    v = abs(float(speed_ms))
    m = float(mass_kg)
```

`abs()` is applied to the speed and not to the mass, so a negative mass returns a negative energy;
`joules_for` (line 108) is `float(volume_m3) * MATERIAL[material][mode]`, so a negative volume
returns negative joules. Sibling of the already-open order `adffa670486c`
(`binding_energy` squares a negative mass into a positive energy), which was explicitly scoped to
that one function. All current callers pass literals (`anchors.py:71`, `verify_math.py:107,109,114`),
so there is no live wrong number — this is the guard being absent, not a defect in flight.

---

## lognames.py

### L1 — the `sweep` job's owner fragment matches `allsweep.py`  (MAJOR)

`lognames.py:14,34`:

```
SWEEP = "sweep.log"             # the character sweep rebuild (sweep.py)
...
    SWEEP:       "sweep.py",
```

`overnight.running()` matches by plain substring (`overnight.py:180`):

```
        if fragment in cmd.replace("\\", "/").split("/")[-1] or fragment in cmd:
            return True
```

`src/allsweep.py` exists and its filename ENDS in `sweep.py`. Measured against the live constant:

```
sweep.log  fragment 'sweep.py'  MATCHES  ...python.exe .../src/allsweep.py
sweep.log  fragment 'sweep.py'  MATCHES  python .../src/sweep.py
```

`allsweep.py` is the only such collision among the six OWNER fragments. Three live consequences,
all read straight off the callers:

1. `foreman.run_character_sweep()` (`foreman.py:669`) opens with
   `if ON.running("sweep.py"): return True, "character sweep already running"` — so while
   `allsweep.py` runs, the character-sweep remedy reports success and starts nothing.
2. `overnight.start()` guards with `running(os.path.basename(args[0]))` (`overnight.py:248`),
   the same string, so the same block applies to the supervisor's own launch path.
3. `foreman.kill_stalled_job` resolves the reported job name through
   `owners = {fn[:-4]: frag for fn, frag in _LN.OWNER.items()}` and SIGTERMs every process whose
   command line contains the fragment. Told to kill a stalled `sweep`, it would take `allsweep.py`
   with it — the whole-tree sweep runner.

This is the exact failure the module's own comment was written to prevent: "it must be specific
enough to distinguish two invocations of the same script". `verify_math.py:3147` pins the
contiguity of the READ fragment only; nothing pins uniqueness.

Secondary, same fix: `foreman.py:669` hardcodes the literal `"sweep.py"` in the `ON.running(...)`
call even though it imports `lognames as LN` on the line above — the second hand-kept copy of the
identifier that `lognames` exists to abolish.

The other five fragments were checked and are clean: `read.py --run`, `feats.py --roll`,
`catalogue_web.py --recatalogue` and `magnitude.py --calibrate` all name flags that exist on
those scripts and all appear contiguously in the real invocations (`overnight.py:824,835`);
`pipeline.py` collides with no other filename in `src/`.

---

## onomast.py

### O1 — the doctrine's counts disagree with `data/RESOLVED_ENTITIES.json`  (MINOR)

Module docstring, line 7:

> Resolution finds thirty distinct worlds named Earth, eighteen named Moon, sixteen named Mars.

and again at line 27: "There are thirty worlds whose peoples remember it".

Measured against the file the module itself reads (44,329 resolved entities), using the module's
own `is_carried()`:

```
canonical name    entities   distinct keys   distinct continuities
earth                26            1                 26
moon                 15            1                 15     (12 "moon" + 3 "the moon")
mars                 14            1                 14
```

and after running `name_worlds()` on it: 223 worlds given a designation, endonym counts
`Earth 26, Mars 14, Moon 12, Venus 8, Japan 7, Jupiter 7`. No reading of the data I could
construct — entity count, distinct `key`, distinct `continuity_group`, before or after naming —
yields 30/18/16. The numbers are the opening of the doctrine's argument, so they are worth being
right even though nothing computes from them.

### Already filed, not re-filed

* `register_for`'s genre/feature voting is unreachable — `name_worlds` calls
  `register_for(v["continuity_group"])` with neither `genre_register` nor `features`, so the
  `not genre_register and not features` branch takes every call and `FEATURE_SHIFT`,
  `GENRE_WEIGHT` and `FEATURE_WEIGHT` are inert. Order `5d8533bc1ed6`.
* The unseeded `taken` set. Order `49474966f971`.

---

# QUESTIONS

1. **`manifest_builder.py`, `grounding.py`, `onomast.py`, `physics.py` and `propagation.py` have
   no `escalation.assert_clear` interlock.** Eleven modules carry it (`allsweep`, `dashboard`,
   `escalation`, `feats`, `foreman`, `overnight`, `overwatch`, `pipeline`, `publish`, `read`,
   `verify_math`); `feats.py`'s comment calls it a "PLANT-WIDE INTERLOCK ... placed first in
   main() so there is no path into this job that skips it" and names "nine sites". Is the
   boundary "jobs the supervisor launches" (in which case manifest_builder, which writes the file
   generation consumes, is arguably inside it), or "anything with a `main()`"? The library is
   HALTED right now and `python src/manifest_builder.py` would still rebuild the manifest.

2. **`grounding.py`'s `immanent` register carries the cue `the current`** (line 119, weight 3).
   That is ordinary English — "the current ruler", "the current age" — and the file already
   records tuning out two cues for exactly this reason ("'recurr' fired 214 times on 'recurring
   character'"). Was `the current` meant as the Avatar/Nen-style noun and left un-anchored, or is
   it deliberately broad? I did not measure its firing rate because the fix is a judgment about
   the vocabulary, not about the code.

3. **`grounding.main()` prints `low[:5]`** of the contested-cosmogony list (line 244). The full
   count is printed on the line above, so nothing is hidden about the SIZE — but `feats._show`
   in this same batch carries an explicit comment that "a cap on a diagnostic hides exactly the
   tail you opened it to read" and lists its refusals in full for that reason. Two files, two
   answers; worth one ruling rather than two habits.

4. **`onomast.coin_well_formed`'s exhaustion path returns a name it has already rejected**
   (line 269): after 10,000 candidates it does `silence.note(...)` and then
   `return coin_name(f"{base}|fallback", register)` — the identical expression tested and
   refused at line 260. The comment says this is deliberate ("the caller still gets a
   designation -- refusing to name anything would be the worse failure") and it is now LOUD
   rather than silent, which is the difference from the run #5 bug. Recording it as a question
   only: the path can still issue a duplicate catalogue designation against the "shelfmarks are
   unique" standard. Measured namespace per register over 4,000 salts —
   classical 2,938 / compact 2,416 / guttural 1,841 / long 1,476 / liquid 1,126 / sibilant 801
   distinct well-formed names — against 223 worlds actually named, so exhaustion is nowhere near
   in practice.

5. **`feats._HOST_OVERRIDES`' last pattern carries two alternatives that can never change its
   answer** (lines 396-397): `^Eastern astrology` and `^Western astrology` sit in the same
   alternation as an unanchored `astrology`, so any string either of them matches is already
   matched by the general term and routed to the same host. Cosmetic redundancy rather than a
   defect — flagged because "an alternative that cannot decide anything" is the shape of the
   class this sweep hunts, and someone reading the list may take those two as evidence that the
   anchored forms are needed.

6. **`feats.resolve_hosts` caches a failed guess as `None` permanently** a source
   whose slugs all fail verification gets `known[src] = None` (line 454), and the next run's
   `if src in known: continue` (line 426) never re-asks. An override can still overwrite it
   (line 415) but a later-registered wiki cannot. Deliberate (a verification round-trip per
   unresolved source per run is real cost) or an absence frozen into a fact? Not filed — it
   reads as a design choice.
