# sweep60 batch12 — audit report

Modules read in full, uncapped: `src/magnitude.py` (1989 ln), `src/dashboard.py` (1248 ln),
`src/threads.py` (1022 ln), `src/build_terminal.py` (668 ln), `src/handbuilt.py` (518 ln),
`src/render.py` (430 ln), `src/profile.py` (346 ln), `src/audit.py` (275 ln),
`src/compress_store.py` (149 ln). Total 6,645 lines, all read start to finish, no sampling.

General note before the findings: these nine files are unusually heavily self-audited already
— nearly every function carries a comment citing an `order <hex>` fix for exactly the failure
classes this sweep looks for (tautologies, fail-open guards, stale citations, caps). I traced a
large number of those claims against the actual code rather than trusting the comment, and in
every case I checked, the code matched what the comment says was fixed (verify()'s round-trip
fix in threads.py, profile.py's re-encode round-trip fix, magnitude.py's `_ST.charter_regression_verdict`
fix, the `esc()` coverage in build_terminal.py's `selectWorld`, etc.). I'm reporting that as
background rather than as individual findings. What follows is what I found that is NOT already
called out and fixed in the surrounding comments.

---

## Finding 1 — HIGH confidence — render.py crashes uncaught on an empty library, unlike its own sibling function and unlike profile.py's identical, already-fixed case

**File:** `src/render.py`, `main()`, lines 307–311:

```python
import worldseed as WS
import address_space as AS
w = WS.build_all(limit=1)[0]
seed = AS.map_seed(w["seed"])
sample = next(iter(tree["worlds"].values()))
```

**What makes it go wrong:** if `worldseed.build_all(limit=1)` returns `[]` (no worlds have been
generated yet — e.g. a fresh NAVTREE.json, or a run before `worldseed` has produced anything),
`[0]` raises an uncaught `IndexError` and `main()` dies with a traceback instead of a message.
Separately, if `tree["worlds"]` is an empty dict, `next(iter({}.values()))` raises an uncaught
`StopIteration`, same effect.

**This is the exact defect class `profile.py` documents fixing for itself**, in the same
codebase, against the same `worldseed` dependency — `profile.py:274-280`:

```python
if not rows:
    # `min(lens)` raises on an empty list and `sum(lens)/len(lens)` divides by zero, so a
    # library with no worlds in it crashed here before it could say so. ... (order b9ff8dbf2c77)
    print("\nno worlds profiled: worldseed.build_all() returned nothing.")
    return 1
```

And **`render.py`'s own `write_views()` function, further down the same file, already guards
the identical data source** (`render.py:375-382`):

```python
if sample is None:
    worlds = tree.get("worlds") or {}
    if not worlds:
        return 0, ["SEVENFOLD.json charts no worlds, so no coordinate names a node"]
    sample = next(iter(worlds.values()))
```

So one function in this file (`write_views`) treats an empty `tree["worlds"]` as an honest,
handled case; the other (`main()`, which runs unconditionally on every invocation, not just
`--write`) does not, and also has no guard at all on `WS.build_all(limit=1)` coming back empty.

**Verified by reading the surrounding source directly** — no try/except anywhere around these
two lines in `main()`, and I confirmed by reading `write_views()` in the same file that the
project already knows this needs a guard and applies it there.

---

## Finding 2 — MEDIUM confidence, latent — profile.py's `encode()` validates `band` but not `attested`, despite both landing in the same fixed-width, regex-validated tail

**File:** `src/profile.py`, `encode()`, lines 130–172.

The profile format's last two characters are `<band><attested>`, matched on decode by
`([0-9au])([0-4])` (`_PROFILE_RE`, line 95). `band` is defended carefully: unparseable input
falls back to `"u"` with a `silence.note`, and an out-of-range tier is clamped to 10 with
another `silence.note` (lines 162–171). `features[axis]` is *also* explicitly discussed and
left unguarded on purpose, with a comment that greps the whole tree and names every caller as
safe by construction (lines 134–146, "UNGUARDED ON PURPOSE, CHECKED").

`attested` gets neither treatment:

```python
return f"PS-{a}-{g}-{f}-{b}{attested}"
```

It is spliced in raw. If a caller ever passes something other than a single digit 0–4 (a bug
upstream in `worldseed.py`, or a future caller that isn't `build_all()`), the resulting string
silently fails to round-trip: `decode()`'s `_PROFILE_RE.fullmatch` simply won't match (the tail
would be, e.g., 2 or 3 characters instead of 1), and it raises `ValueError: not a world profile`.
That exception is *not* caught anywhere in `main()`'s round-trip loop (`profile.py:311-323`,
`d = decode(r["profile"])` with no try/except), so a single bad `attested_axes` value would
crash the whole report rather than being counted as a "bad" round-trip the way `main()`'s own
closing section is designed to report.

**What I verified:** there is no bounds check, no `silence.note`, and no "grepped the tree, every
caller is safe" comment for `attested` anywhere in this file, in contrast to the other two
free-form inputs to `encode()` which both got exactly that treatment. **What I did not verify:**
whether `worldseed.build_all()` (not in this batch) can ever actually produce an
`attested_axes` outside 0–4. So this is reported as a real, verified *gap in the file's own
defensive pattern*, but I can't say whether it's reachable today.

---

## Finding 3 — LOW confidence / unsure — the split-path assay gate skips the relevance re-check the one-shot gate performs, relying entirely on an external module's pre-filtering

**File:** `src/magnitude.py`, `_split_gate()`, lines 1165–1225, vs. `verify()`, lines 817–904.

`verify()` (the one-shot gate) explicitly re-checks guard 2 (relevance) against the model's own
citation:

```python
if not AXIS_RE[ax].search(text):
    rejects.append((ax, f"feat does not bear on {ax}: {text}"))
    scores[ax] = A.UNESTIMABLE
    continue
```

`_split_gate()` (the DEFAULT path for anything over `ONE_SHOT_MAX`, i.e. the heaviest,
best-documented entities — the exact population this file's own docstring says the split path
exists to serve) has no equivalent check. Its docstring justifies this as: "Axis-relevance is by
construction (each axis was scored only from its own candidate list)" — i.e. it trusts that
`cand[ax]`, built by `candidates()` calling `F.by_axis(clean, page)` in `feats.py`, already only
contains sentences relevant to `ax`.

That trust is only as good as `feats.by_axis`'s own relevance test matching magnitude.py's own
`AXIS_LEXICON`/`AXIS_RE` (lines 213–239) — and `feats.py` is not in this batch, so I could not
verify whether the two definitions of "relevant to this axis" actually agree. If they don't
(e.g. `feats.by_axis` uses a looser or different lexicon), a feat that would fail guard 2 on the
one-shot path could publish on the split path with no relevance check at all — a double
standard between two code paths that are supposed to produce the "same sheet shape" (the split
docstring's own words). **Flagged as unsure**: the logic inside this file is internally
consistent with its stated design; the risk is entirely at the boundary with a module outside
this batch, which I have not read.

---

## Finding 4 — LOW confidence / unsure — handbuilt.py applies one Attestation grade ("Transcribed") uniformly across three different provenance types

**File:** `src/handbuilt.py`, `compute()`, lines 425–437.

Every entry in `ROSTER` is scored with `attestation="Transcribed"` regardless of its per-axis
`provenance` tag, and those tags are explicitly NOT uniform: most axes are marked `"wiki"`, some
`"canon"` (e.g. Undertaker's celerity, several of Rune King Thor's and Molecule Man's axes), and
all eleven of the IRS's axes are marked `"record"` — with the entry's own docstring stressing
"Provenance is marked [record] throughout: this is the public record, not a mined wiki, and the
sheet says so rather than borrowing the authority of a citation format it has not earned"
(lines 121–124). That paragraph draws a real distinction between provenance types, but the
`Attestation` grade actually passed to `A.assay()` — the field the charter's own ladder ranks
(magnitude.py's docstring: "the Attestation ladder puts Instrumented above Transcribed") — does
not reflect that distinction anywhere; every one of the nine hand-built sheets, wiki- or
record-sourced alike, is filed as "Transcribed". **Flagged as unsure** because I don't have
Part Three of the charter (`reference/keystone_volumes/`, out of this batch) in front of me to
know whether "Transcribed" is in fact charter-defined broadly enough to cover public-record
evidence, or whether a public record should carry a different, perhaps higher, Attestation
grade. Worth a person checking against the charter text directly.

---

## Not reported as findings (checked and judged not worth flagging)

- `src/dashboard.py`'s `_TTL_MEMO` module-level dict (lines 280–293) is read and written by
  every `/api/state` request with no lock, and the server is threaded
  (`daemon_threads = True`). Two concurrent pollers could both miss the cache and both recompute
  `_library()`/`_watch()` at once. This is a wasted-work race, not a correctness one — CPython
  dict assignment is atomic and both threads compute the same answer from the same files — so I
  did not write it up as a finding proper.
- `src/compress_store.py`'s gzip fallback path (`gzip.compress(raw_bytes, compresslevel=9)`,
  line 40) does not pin `mtime=0`, so two separate `store()` calls for identical text at
  different times produce different compressed bytes at the same content-addressed path when
  the optional `zstandard` package is absent. This does not break anything `load()` checks (it
  verifies the *decompressed* text's hash, which is unaffected), so it is cosmetic rather than a
  bug, and I did not write it up as a finding proper.
- I went looking hard for a fresh tautological check ("a check that cannot fail") per this
  sweep's priority 1, since that is this project's signature failure mode. I did not find a new
  one in these nine files — every candidate I traced (the round-trip checks in `profile.py` and
  `threads.py`, the calibration verdict in `magnitude.py`) had already been repaired, and I
  verified the repair is actually present in the code as it stands today, not just claimed in a
  comment.

---

## Summary

- 1 HIGH-confidence finding, verified directly: `render.py` `main()` crashes uncaught on an
  empty library at `render.py:309` and `render.py:311`.
- 1 MEDIUM-confidence finding, verified within-file but reachability unconfirmed:
  `profile.py`'s `encode()` has no guard on `attested` (`profile.py:172`), unlike its siblings
  `band` and `features` in the same function.
- 2 LOW-confidence/unsure findings that depend on modules outside this batch
  (`magnitude.py`'s `_split_gate` relevance-check gap depending on `feats.py`;
  `handbuilt.py`'s uniform Attestation grade depending on the charter text).
- 2 items considered and explicitly not raised as findings (dashboard.py TTL-cache race,
  compress_store.py gzip mtime nondeterminism), with reasoning given above.
