# AUDIT batch13 (sweep42, run42)

Modules read in full: src/read.py, src/overwatch.py, src/identity.py, src/codewatch.py,
src/policy.py, src/retry_synthesis.py, src/physics.py, src/audit.py

## CONFIRMED DEFECTS

### 1. identity.py:392-397 — corrupted/unreadable cache silently treated as "genuinely empty",
defeating the guard it sits inside

```python
392	    if not inv and os.path.exists(CACHE):
393	        try:
394	            with open(CACHE, encoding="utf-8") as f:
395	                prior = json.load(f)
396	        except Exception:
397	            prior = {}
398	        if prior:
399	            silence.note("identity.py:refused-empty-over-populated")
400	            print("identity: the mine found no designators at all while %s holds %d host(s) -- "
401	                  "REFUSING to overwrite it. ..."
402	            return inv
403	    if not silence.write_json(CACHE, inv, indent=1, sort_keys=True):
```

This block exists specifically to stop a freshly-mined *empty* inventory (`inv == {}`) from
overwriting a DESIGNATORS.json that actually holds good data — the function's own docstring calls
a wrong merge here "unrecoverable". But the `except Exception: prior = {}` on line 396-397 makes
"the existing cache file failed to parse" indistinguishable from "the existing cache file
genuinely holds `{}`". A transient read race (another writer mid-`write_json` on Windows, or a
truncated file) raises here exactly as a real empty file would, `prior` becomes `{}`, the `if
prior:` guard does not fire, and the function falls through to `write_json(CACHE, inv, ...)` on
line 403 — silently landing an empty inventory over a DESIGNATORS.json that may have held a
populated one moments before. No `silence.note` is called on this exception at all, unlike the
`except Exception: silence.note("identity.py:load")` a few dozen lines above (327-332) in the
*same function*, which handles the structurally identical "cache present but unreadable" case
correctly by falling through to a fresh mine rather than asserting an answer about the file's
contents. This is precisely the "check that cannot fail looks exactly like a check that passed"
shape CLAUDE.md names, on the one guard in this file whose entire job is preventing an
unrecoverable wrong merge.

Confidence: high.

### 2. read.py:604 vs 620-621 — inconsistent GPU timeout for identically-sized chunks in
`_local_carded`

```python
597	    if len(prompt) <= CHUNK + 2000:
...
604	        got = P.ask(c, system, prompt, schema, timeout=360)
...
608	    # Order 5bf48fa9f70d: ...
...
617	    head, _, body = prompt.partition(chr(10) + chr(10))
618	    merged = {"feats": []}
619	    for i in range(0, len(body), CHUNK):
620	        got = P.ask(c, system, head + chr(10) + chr(10) + body[i:i + CHUNK],
621	                    schema, timeout=180)
```

The comment directly above line 604 explains at length why the timeout for a full CHUNK-sized
(10,000-char) passage was raised from 180s to 360s: "At 180s the card burned at 98% while 94% of
handed chunks died at the deadline AFTER their compute was spent." The `else` branch just below
(the re-split path for an oversized prompt) splits `body` into pieces of exactly `CHUNK` size —
the same size the 360s figure was sized for — but calls `P.ask` with `timeout=180` on line 621,
the very value the surrounding comment names as having caused a 94% discard rate on full-size
chunks. Any entity whose evidence triggers the re-split path (prompt > CHUNK + 2000 chars) will
have its pieces measured against the timeout already proven insufficient, silently discarding
work and benching the GPU (`_GPU_DOWN_UNTIL`) on a false "the card is down" signal caused only by
an avoidably-short deadline.

Confidence: high that this is a genuine oversight (the two branches were clearly meant to share
the same timeout rationale); the "180" may possibly have been left as a leftover from before the
360 fix, un-migrated to the sibling branch.

### 3. read.py:1427 — feat sentence silently truncated to 104 chars in `--one` output, contradicting
the comment immediately above it

```python
1420	        # NOT SLICED (order a84c002fb0e3, Hard Rule 0). This used to print `out["feats"][:12]`
1421	        # with no marker, so Goku's 241 feats came back as twelve rows and nothing on the page
1422	        # said the other 229 were rows you could have seen. `--one` is the interactive
1423	        # inspection path -- it exists precisely so a person can look at everything that was
1424	        # mined for one entity -- and the volume is bounded by the single entity, so there is
1425	        # nothing here worth capping and nothing to reverse a cap with.
1426	        for f in out["feats"]:
1427	            print("   %-14s %s" % (f["axis"], f["feat"][:104]))
```

The list-level cap (`[:12]`) was fixed per the comment, but the fix did not touch the per-item
`f["feat"][:104]` on line 1427: every feat sentence longer than 104 characters is still cut, with
no "..." or any other marker that anything was removed, and `--one` is the only place this data is
ever displayed (there is no companion file the way WATCH.md backs up overwatch.py's console
truncation). The comment's own claim — "nothing here worth capping" — is false for the text of
each row, only true for the count of rows. A long feat sentence (the SYSTEM prompt in this same
file explicitly asks the model to "copy the sentence VERBATIM," so many are full clauses well
over 104 characters) is silently shown incomplete in the one interactive tool built for reading
everything mined about an entity.

Confidence: high that this is a truncation without a marker, matching Hard Rule 0's stated shape;
medium-high that it's an oversight rather than accepted display-width cosmetics, since the
adjacent comment explicitly disclaims any remaining cap.

### 4. audit.py:190-193 — invariant-violation occurrences ranked then truncated to 4 per class,
in the pass the file's own docstring calls exhaustive

```python
188	        print(f"\n  {k}")
189	        print(f"     {len(v):,} occurrences ({rate:.2%} {unit}; {denom:,} in that population)")
190	        for x in v[:4]:
191	            print(f"       - {x}")
192	        if len(v) > 4:
193	            print(f"       ... and {len(v)-4:,} more")
```

`audit.py`'s module docstring frames INVARIANTS as running "over EVERY entry ... Cheap,
exhaustive, and the only way to catch a rule that quietly stopped applying" — explicitly
contrasted against the SAMPLE pass a few lines later, which is allowed to be partial. Yet the list
of concrete occurrences printed for each violation class is capped to the first 4 (post-sort),
with only a count of the remainder shown. This is the identical shape `overwatch.py` (lines
722-731, this same sweep's other assigned file) explicitly names and fixes as "Hard Rule 0's
exact shape: the ranking is kept and encouraged, the truncation is the fault," citing this project's
own house rule by name. Here the specific sources/entries beyond the 4th for every violation
class are never printed anywhere (no equivalent of WATCH.md backing this report up) — an operator
chasing down, say, "entry: BAND WITH NO SCALE NOTE" only ever sees 4 concrete examples no matter
how many hundred there are.

Confidence: medium-high. This is a console-summary report rather than a persisted ledger, so it
is arguably closer to a legitimate display convenience than identity.py's or read.py's findings
above — but the file's own stated purpose ("exhaustive... the only way to catch a rule that
quietly stopped applying") and this codebase's own prior ruling on the identical pattern in
overwatch.py argue it is in scope as a real Hard Rule 0 finding rather than acceptable cosmetics.

## QUESTIONS (not fixes — flagging for owner judgment)

### Q1. physics.py `kinetic()` — potential unguarded `ZeroDivisionError` at the relativistic
boundary

`kinetic()` (lines 75-139) meticulously converts every domain error (negative/NaN/infinite mass
or speed, non-finite results) into a descriptive `ValueError`. The relativistic branch is:

```python
120	    if v < RELATIVISTIC_ABOVE * C:
121	        result = 0.5 * m * v * v
122	    else:
123	        gamma = 1.0 / math.sqrt(1.0 - (v / C) ** 2)
124	        result = (gamma - 1.0) * m * C * C
```

`v >= C` is refused earlier (line 114), but for a `v` extremely close to `C` — within roughly
`C * 2.2e-16` (float64 epsilon), i.e. within about 6.6e-8 m/s of light speed — `v / C` rounds to
exactly `1.0` in floating point even though the true quotient is `< 1`. That drives
`1.0 - (v/C)**2` to exactly `0.0`, `math.sqrt(0.0)` to `0.0`, and the division on line 123 raises
a bare `ZeroDivisionError` rather than the module's own descriptive `ValueError` — exactly the
"names arithmetic, not a domain error" failure shape this same file's `sphere_volume()` and
`binding_energy()` docstrings explicitly call out and guard against for their own OverflowError
cases (lines 205-212, 261-272). Whether this is worth a guard depends on whether any caller could
plausibly hand `kinetic()` a speed described in fiction as "99.9999999999% of light speed" or
similar — plausible for this project's subject matter, so flagging rather than dismissing.

Confidence this is a real, reachable edge case: medium (the input window is narrow but not
contrived, and the codebase's own stated policy is that every domain failure here should surface
as a descriptive ValueError, not a raw arithmetic exception).

### Q2. identity.py:690-691 — `top[:6]` display cap in the no-`--host` summary listing, marked
but still a cap

```python
689	        top = sorted(cont.items(), key=lambda kv: -kv[1])
690	        names = ", ".join(f"{d} ({n})" for d, n in top[:6])
691	        more = f" +{len(top) - 6} more" if len(top) > 6 else ""
```

Per-host, only the top 6 continuities are named in the whole-corpus summary printout; the rest are
folded into a "+N more" count. This is marked (unlike the confirmed findings above) and is a
console summary rather than the file's primary data (`--host <name>` prints every row uncapped).
Raising only because Hard Rule 0's text is unconditional ("no top N... Ranking then truncating is
not [allowed]") with no stated exemption for a marked summary line the way overwatch.py's `--show`
carries an explicit "house exemption" citation. Judgment call for the owner: is a marked cap on a
whole-corpus overview line, when the same data is available in full via `--host`, in scope of the
rule or not.

Confidence this rises to the level of the confirmed findings: low — flagging for a ruling, not
proposing a fix.

## Not flagged (reviewed and found sound)

- codewatch.py, policy.py, retry_synthesis.py: read in full; no new defects found beyond what is
  already documented and fixed in their own extensive inline history. Their exception handling,
  locking, and truncation-avoidance (e.g. policy.py's `_observed()`, retry_synthesis.py's
  `do_merge()` UNMERGED reporting) all match Hard Rule 0 and the fail-closed rule as written.
- overwatch.py: read in full; the WATCH.md findings list, the `--show` per-item truncation (marked,
  points to WATCH.md), and the ledger merge/preservation logic all check out.
- read.py's `priority()`/`queue()` ranking-not-truncating logic (Hard Rule 0's own worked example
  in this file) is correctly uncapped throughout.
