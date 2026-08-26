# SWEEP 34 — BATCH 14 AUDIT

Modules read end to end: `src/rigor.py` (865), `src/wiki_source.py` (662), `src/weave.py` (487),
`src/reference.py` (358), `src/cosmography.py` (282), `src/genre.py` (247), `src/audit.py` (188),
`src/cosmology_graph.py` (165). Total 3,254 lines.

Auditor only. No file under `src/` was edited. Every finding below was verified against the
source and, where a number is claimed, against the data on disk. Anything unproven is a QUESTION.

Not re-filed (already known / already filed): `reference.py:345` bare-name lookup against
`ASSAYS.json`'s `host|entity` keys; `weave.pair_weights` (~156) and `weave.null_threshold` (~249)
dead; `cosmology_graph`'s console-list truncation.

---

## rigor.py

### FINDING R1 — `ceiling_confidence` describes a sampling rule the pipeline abolished, and the rule's abolition inverts the result (MAJOR)

`rigor.py:640` returns, for any argument pair:

```
        "sampling": "NOT random: 14 longest descriptions, biased toward prominence",
        "bound_direction": "n/N is a FLOOR; informative selection raises it by an unmeasured amount",
```

and `rigor.py:849` prints:

```
    print("   sampling is NOT random (14 longest descriptions) — n/N is a floor, and the")
```

The docstring at `rigor.py:619-623` builds the whole argument on it:

```
    **BUT THE PIPELINE DOES NOT SAMPLE RANDOMLY**, and it would be dishonest to quote n/N as if it
    did. `phase_synthesis` takes the 14 LONGEST descriptions.
```

`phase_synthesis` no longer does. `pipeline.synthesis_blocks` (pipeline.py:740-793) was rewritten
under the owner's 2026-08-25 ruling and now blocks **every** entry:

```
    blocks = ([with_feats[i:i + 14] for i in range(0, len(with_feats), 14)]
              or [rest[i:i + 14] for i in range(0, len(rest), 14)])
```

with the removed cap written up in the comment above it ("IT WAS A CAP. OWNER RULING 2026-08-25 …
the tail is now REACHED rather than discarded"). `grep -rn "\[:14\]" src/*.py` shows `rigor.py:640`
and `rigor.py:849` are the only two surviving statements of the abolished rule in the tree.

Consequence: `rigor.main()` §5 prints `P(max seen | RANDOM) >= 1.6%` for N=900 against a pipeline
that now nominates all 900. The published floor understates the library's own ceiling confidence,
and it does so in the module whose job is to keep the library honest about that number.

Two sub-defects ride along:
* the `sampling` string is a constant — pass `n_scored=500` and it still says "14 longest".
* `verify_math.py:429-430` pins the stale prose:
  `check("ceiling sampling is reported as non-random", "NOT random" in R.ceiling_confidence(900, 14)["sampling"], True)`
  so the fix is multi-file. Handler RUN.

### FINDING R2 — an unconditional verdict printed beneath evidence that could contradict it (MINOR)

`rigor.py:795-803`:

```
        ok = "above floor" if declared >= floor else "BELOW FLOOR — underpriced"
        print(f"   {nm:<16} floor {floor:7.2f}   declared {declared:4d}   "
              f"x{ratio:5.2f}   {ok}")
    ...
    print("   FINDING: every declared cost sits above its MDL floor, and the ratios cluster —")
```

The FINDING line is outside the loop and unguarded. Were any row to print "BELOW FLOOR —
underpriced", the very next lines would still announce that every declared cost sits above its
floor. This is the identical defect fixed at `rigor.py:746-759` for the faculty weights, whose own
comment states the rule: *"A diagnostic that cannot be contradicted by its own evidence is not a
diagnostic."* One instance was fixed; its twin thirty lines down was not visited.

### FINDING R3 — dead parameter on a public function (MINOR)

`rigor.py:100`: `def measure_bit_value(band, module=None):` — `module` is never referenced in the
body (lines 125-129 use only `band`). No caller passes it: `anchors.py:208`
`R.measure_bit_value(a["anchor"])`; `verify_math.py:403, 663, 3525, 3531` all one-arg. Note
`verify_math.py:407` already asserts a *different* leftover parameter (`axis`) is gone, so this
signature has been pruned once before and this one was missed.

---

## wiki_source.py

### FINDING W1 — seven stale numeric `silence.note` tags (MINOR)

`silence.note(site)` writes `site` straight into the health ledger as the failure class
(`silence.py:404`: `health.record(f"silent:{site}", ...)`). The module already recognises the
problem — `wiki_source.py:289-292`: *"Content labels, not line numbers: this label was shared with
the live category probe … That defeats the whole point of the ledger."* Four sites were converted;
seven were not, and every one now names an unrelated line:

| call site | tag | what that line actually is |
|---|---|---|
| 190 | `wiki_source.py:155` | a comment inside the MIN_GAP block |
| 196 | `wiki_source.py:160` | blank line |
| 241 | `wiki_source.py:204` | `params = dict(params, format="json")` in `_api` |
| 305 | `wiki_source.py:229` | a docstring line in `verify_wiki_matches` |
| 577 | `wiki_source.py:376` | a docstring line in `all_categories` |
| 596 | `wiki_source.py:394` | `out, cont, complete = [], None, True` |
| 623 | `wiki_source.py:420` | the `discover_categories` docstring |

`:155` and `:160` are `_get`'s two distinct except branches (HTTPError vs everything else) and both
now point into the same comment block, so the ledger cannot distinguish a 429 from a socket death.

### FINDING W2 — `resolve_wiki` throws away 39 of the 203 hosts the library has already resolved (MINOR)

`wiki_source.py:295-296`:

```
    if isinstance(known, str) and known.endswith(".fandom.com"):
        cands.append(known[: -len(".fandom.com")])
```

Measured on `data/WIKI_HOSTS.json` (203 keys, keyed by source name — the key shape *does* match
`source_name`, so this is not the reference.py class):

```
164 fandom   22 en.wikipedia.org   7 None   4 www.dandwiki.com   1 rimworldwiki.com   5 pages:/doc: entries
```

For those 39 non-fandom sources the recorded host is silently dropped and the function proceeds to
`subdomain_candidates()` and guesses **fandom** subdomains for a source the library already knows
is not on fandom — then spends verification requests against the host this machine is IP-banned
from. That is the failure the function's own docstring says it exists to end: *"a resolver failing
to resolve a host the library had already resolved."* The module is fandom-only by construction
(`_api` hardcodes `https://{subdomain}.fandom.com/api.php`), so the honest answer for a recorded
non-fandom host is `(None, None)`, not a guess. Judgment call on the right refusal — handler RUN.

---

## weave.py

Nothing new beyond the already-filed dead pair. Stale tag folded into the joint order below.

`weave.py:190` reads `silence.note("weave.py:187")`; line 187 is the `try:` three lines above, not
the call site.

---

## reference.py

Nothing new. The `--compare` key-shape defect at line 345 is already filed and is not repeated here.

`reference.py:241` reads `silence.note("reference.py:232")`; line 232 is `def shelfmark(rec):`.

---

## cosmography.py

### FINDING C1 — declared constants with no reader, in the module that stakes its admissibility on reversibility (MINOR)

The module docstring, lines 18-20:

```
  REVERSIBLE -- every convention is a named module-level constant with an erratum note. Change
                one, re-run, and every downstream figure moves with it.
```

`DEFAULT_SIZE_CLASS = "STANDARD"` (line 133) is read by nothing in `src/` (grep: defined once, no
other reference). `census()` hardcodes the same string in its own signature instead:
`def census(size_class="STANDARD", galaxies=None, verbose=False)` (line 169). Change
`DEFAULT_SIZE_CLASS` and re-run, and no downstream figure moves at all.

Same shape, milder: `KARDASHEV_TYPE_I` (line 66) and `EARTH_POWER_2020` (line 69) have no reader in
`src/` — `verify_math.py:176-177` re-types their values as literals `1e16` and `2e13` rather than
importing the constants, which is one fact in two copies, the project's named failure class.
(`KARDASHEV_TYPE_II`/`III` *are* imported at `verify_math.py:180,184`; only these two are duplicated.)

---

## genre.py

### FINDING G1 — the ranked genre list is truncated to three, and the confidence figure is divided by the truncated total (MAJOR)

`genre.py:135-141`:

```
def classify_text(text, top=3):
    """Score every genre against a body of text. Returns ranked (genre, score)."""
    ...
    return scores.most_common(top)
```

`genre.py:182-196`:

```
    ranked = classify_text(" ".join(parts))
    ...
    total = sum(s for _, s in ranked) or 1
    return {
        ...
        "confidence": round(score / total, 3),
        ...
        "runners_up": ranked[1:],
```

Eleven genres are scored; three survive. Two separate consequences, both live:

1. **`confidence` is computed against a truncated denominator.** Measured on the real corpus:

   ```
   Adventure Time  all 11 genres: whimsy 12619, high_fantasy 6416, grimdark 1436, military_modern 1186,
                   post_apocalyptic 902, cyberpunk 730, mythology 513, space_opera 409,
                   superhero 218, eastern 179, cosmic_horror 174
                   confidence over top-3 = 0.616      over all 11 = 0.509
   2112 (Rush)     confidence over top-3 = 0.567      over all 11 = 0.530
   ```

   The published number is systematically inflated. `genre.py:218` flags mixed sources with
   `v["confidence"] < 0.45`, so the inflation directly under-flags the cases the docstring says the
   record must own: *"A source that scores 40 for grimdark and 38 for horror is NOT confidently
   either, and the record should say so rather than pick."*

2. **`runners_up` is truncated to two.** On disk, `data/GENRES.json`, 210 sources:
   `Counter({2: 207, 0: 3})` — every classified source carries exactly two runners-up out of a
   possible ten. This is a ranked list cut to N and written to a file, which Hard Rule 0 names
   directly.

The irony is local: this is the file whose `classify_source` raises `SystemExit` on any `cap`
because a cap "changed the answer for 7 of 210 sources". The cap it refuses is on the *input*; the
cap on the *output ranking* sat three functions away untouched.

**`grounding.py` carries the identical shape** — `grounding.py:125` `def classify_text(text, top=3)`,
`:175` `ranked = classify_text(...)`, `:192` `score / total`, `:198` `ranked[1:]` — and
`grounding.py:149` records that the two modules already diverged once this way. Fix both or it
recurs. Handler RUN.

---

## audit.py

**No findings.**

### `_JUNK` verified, not assumed

`audit.py:41-43`:

```
_JUNK = re.compile(r"^(?:characters?\b|category:|list of |index of |gallery$|navigation$|"
                   r"main page$|contents?$|glossary$|timeline$|episodes?$|seasons?$|"
                   r"appearances?$|references?$|trivia$|see also$|external links$)", re.I)
```

Every alternative now carries its own anchor. Executed against the exact strings the comment names
as the old false positives:

```
MATCH   Characters          MATCH   Category:Heroes     MATCH   List of ships
MATCH   Character           MATCH   Gallery             MATCH   Trivia
MATCH   Characters in Naruto  (deliberate — the comment says 'Characters' takes qualifiers)
 ---    Timeline of the Fallen Empire     ---   Seasons of War
 ---    Gallery of Rogues                 ---   References Codex
 ---    Navigation Beacon                 ---   Chronicles
```

The fix holds and behaves exactly as its comment describes.

Other checks in `audit_invariants` were traced and all can fire: `VALID_BANDS = set(PL.BANDS)` and
`PL.BANDS` (pipeline.py:123) does include `"unassayed"`, so line 61's membership test is not a
guard that rejects every honest synthesis. `PL.records()` (pipeline.py:399) returns a **list**, so
`main()`'s three separate iterations over `recs` (lines 137, 138, 164) are all populated — this was
checked because a generator there would have silently emptied the sample pool.

---

## cosmology_graph.py

### FINDING X1 — an undeclared magic threshold drops 71% of the graph from the file two modules read live (MAJOR)

`cosmology_graph.py:147-151`:

```
        silence.write_json(OUT, {
            "pairs": [{"a": a, "b": b, "weight": round(w, 3),
                       "shared_sample": pair_shared[(a, b)]}
                      for (a, b), w in sorted(pair_w.items(), key=lambda kv: -kv[1])
                      if w >= 1.0],
```

Measured by running `build_graph()` against the real `data/WEAVE_CANDIDATES.json`:

```
pairs total 3753   written (w >= 1.0) 1087   dropped 2666   71.0%
```

`1.0` appears nowhere else in the module, is not `--threshold` (default 3.0, which governs only
`clusters` at line 138), is not mentioned in the docstring or in any comment, and is not surfaced
in the written JSON — the file records `"threshold": args.threshold`, i.e. **3.0**, which is not
the number that selected its own `pairs`. `propagation.py` and `resonance.py` read this file live
(stated at lines 144-145), so 2,666 shared-stage pairs do not exist to anything downstream and the
file's own metadata misdescribes why.

The comment immediately above, at lines 86-92, insists on the opposite discipline for the same
write: *"WHOLE list, no cap — Hard Rule 0, ruled 2026-08-24 … a ninth shared entity simply did not
exist to anything downstream."* The per-pair sample was uncapped; the pair list itself was not.

Whether 1.0 should become 0.0, become `args.threshold`, or become a declared and recorded constant
is a judgment about downstream consumers — handler RUN.

### FINDING X2 — docstring states a weighting the code does not use (MINOR)

Module docstring, line 40:

```
correctly binds exactly the Forgotten Realms corpus). So each shared entity contributes
1/log(sources attesting it) -- rare shared entities bind, ubiquitous ones barely count.
```

Code, lines 78-80:

```
        w = 1.0 / math.log(n + 1.5)
        if n > UBIQUITOUS_CUTOFF:
            w *= 0.15
```

Two departures: the `+1.5` smoothing (at n=2 the documented formula gives 1.443, the code gives
0.803 — not a rounding difference) and the `×0.15` ubiquity penalty, which the docstring never
mentions at all despite `UBIQUITOUS_CUTOFF` being the module's only tunable constant.

---

# QUESTIONS

These may be deliberate. None were filed as orders.

**Q1 — console-display truncation of ranked lists, five sites in three of my modules.**
`rigor.py:858` `mr["load_bearing"][:6]`; `weave.py:446` `multi[:12]`, `:458` `[:8]`, `:464`
`most_common(6)`; `genre.py:220` `low[:5]`. `rigor.py:717-719` explicitly rules on its own case
(*"Ranked, never truncated (Hard Rule 0). The sole consumer slices for display"*), which reads as a
standing decision that display slicing is permitted where the returned/written data is whole. Is
that ruling general? If so `cosmology_graph`'s already-filed console truncation is arguably the
same permitted shape and the sibling sites here need no work; if not, all five want the
`... and N more` form that `audit.py:158-159` already uses.

**Q2 — `bradley_terry`'s refusal message truncates the evidence for its own refusal.**
`rigor.py:448-449`: `f"comparison graph is not strongly connected: {len(comps)} components {[c[:3] for c in comps][:4]}."` A refusal is the one output nobody can re-derive from a smaller
copy, and the count is printed alongside so nothing is hidden — but four components of three names
each is what a human gets to act on. Deliberate?

**Q3 — `cosmography.validate` guards that cannot fire under the declared constants.**
`cosmography.py:240` `if c["civilizations_extant"] > c["life_bearing"]` — but
`civs_now == life * F_COMPLEX * F_CIVILIZATION * F_SURVIVES == life * 0.002` identically, for any
inputs, so this can only fire if someone edits those three constants above a product of 1. Same for
line 237's Type I check (t1 is ~5e-5 of `habitable_zone_rocky` by construction). Under the module's
REVERSIBLE doctrine these are exactly the right guards — a constant *is* meant to be edited and
re-run. Under "a check that cannot fail looks like a check that passed" they are furniture on the
current values. I read them as the former and did not file; flagging so the ruling is on record.

**Q4 — `reference.shelfmark`'s rung indices collide if a `tier_key` ever gains a fourth part.**
`reference.py:244-245`:
```
    marks = [f"{RUNGS[i]}{v}" for i, v in enumerate(upper)]
    marks += [f"{RUNGS[3 + i]}{v}" for i, v in enumerate(lower)]
```
`upper` is one entry per dotted component of `tier_key`; `lower` always starts at `RUNGS[3]`. All
three current records have three-part tier keys (`"1.6.1"`, `"4.2.0"`, `"1.2.5"`) so it is exact
today. A four-part key would emit `Mv.` twice and silently produce an eight-rung Shelfmark with the
wrong rung labels. Latent, not live — is a fourth tier level ever expected here?

**Q5 — `weave.main()` computes `idf` and `N` and uses neither.**
`weave.py:428` `occ, idf, sources, N = idf_table(index)`. `idf` is consumed only by
`pair_weights` and `null_threshold`, the two functions already known dead; `N` by nothing. This is
the tail of the already-filed dead pair rather than a separate finding, so it is a question: should
`idf_table` shed its idf computation when those two go, or does the idf path stay as the documented
alternative the module header spends thirteen lines arguing for?

**Q6 — `wiki_source` retains `limit=`/`top=` kwargs that default to `None`.**
`find_categories(..., limit=None)`, `rank_by_size(..., top=None)`, `category_members(..., limit=None)`,
`all_categories(..., hard_stop=None)`. Each carries a comment saying the parameter survives only so
no caller's signature breaks, and I verified no caller in `src/` passes a truncating value
(`catalogue_web.py:100,105,205,213` pass `limit=None`/`top=None` explicitly). Keeping a live
truncation path for a human debugging a pathological wiki is a stated design choice — recording it
so it is not re-litigated next sweep.
