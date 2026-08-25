# Batch 13 Audit — run #24 whole-tree sweep

Files in batch and read completeness:
- `src/overwatch.py` (707 lines) — read in full, every line.
- `src/handbuilt.py` (487 lines) — read in full, every line.
- `src/onomast.py` (407 lines) — read in full, every line.
- `src/cosmography.py` (282 lines) — read in full, every line.
- `src/sweep.py` (240 lines) — read in full, every line.
- `src/halo.py` (178 lines) — read in full, every line.
- `src/physics.py` (149 lines) — read in full, every line.

Also read for cross-verification (not part of the batch, but required to check claims made
against them): `src/allsweep.py` (`reconcile()`, lines 152-320, and `main()` header) and
`src/assay.py` (`assay()` signature, `LADDER`, `moth_number` formatting). Grepped the whole
`src/` tree for callers of `onomast.register_for`.

Clean, no findings: `cosmography.py`, `physics.py`, `handbuilt.py` (data-heavy module; its
`compute()`/`main()` logic is small and correct, and it already carries the write-before-print
fix — see the halo.py finding below, which is the same bug class *not* fixed there).

---

## overwatch.py

### 1. MAJOR — `overwatch.py:326-329` — the reconcile filter still drops real findings, and drops ALL SEVEN of `allsweep.reconcile()`'s exception handlers

```python
out["reconcile"] = [r for r in A.reconcile()
                    if r["finding"].isupper() or "no host" in r["finding"]
                    or "never catalogued" in r["finding"]
                    or "MORE THAN ONE" in r["finding"]]
```

I read `allsweep.reconcile()` in full (`src/allsweep.py:152-320`) and enumerated every distinct
string its `note(kind, ...)` calls can produce, then checked each against the four-way filter
above.

**KEPT** (6 distinct finding strings): `catalogued sources with no host` (matches `"no host"`),
`on the roll but never catalogued` (matches `"never catalogued"`), `PHASES NAMED BY THE RUNNER
WITH NO IMPLEMENTATION` (isupper), `ENTRIES BANDED ABOVE THEIR OWN SOURCE'S CEILING` (isupper),
`MORE THAN ONE INSTANCE RUNNING` (isupper, and matches `"MORE THAN ONE"`), `NOT RUNNING`
(isupper).

**DROPPED**, confirmed real, non-noise findings that a human would want to see:
- `hosts for sources with no catalogue record` (allsweep.py:177, "orphan hosts") — does **not**
  contain the substring `"no host"` (it contains "no catalogue record"), is not all-upper. This
  is a genuine orphan-host finding, silently discarded.
- `COVERAGE.json is stale` (allsweep.py:206) — matches none of the four conditions. This is
  exactly the "discards stale coverage" class named in the brief.
- `cache directories no source points to` (allsweep.py:224, "orphan cache dirs") — matches none
  of the four conditions. Confirmed dropped.
- `purged sources that still carry entries` (allsweep.py:237, "ghost roster entries") — matches
  none of the four conditions. Confirmed dropped.

**DROPPED**, all internal exception handlers of `reconcile()` — I count **seven** distinct
`except Exception as e: note(...)` blocks in `allsweep.reconcile()`, not six:
`source reconciliation failed` (allsweep.py:187), `coverage reconciliation failed` (:209),
`cache reconciliation failed` (:226), `purge reconciliation failed` (:239), `phase
reconciliation failed` (:257), `band reconciliation failed` (:290), `process check failed`
(:318). None of these strings is all-upper, none contains `"no host"`, `"never catalogued"`,
or `"MORE THAN ONE"`. Every one is silently discarded by overwatch's filter. Because
`reconcile()` catches its own exceptions internally and always returns a list (never raises),
`structure()`'s own outer `try/except` (overwatch.py:318-332) never fires either — so a
crashing internal reconcile check produces **no signal anywhere** in WATCH.md. A check that
crashes is reported identically to a check that never had anything to say, which is precisely
the fault class run #23's fix (documented at overwatch.py:537-548) was supposed to close, and
it is still open one layer down.

**Failure scenario**: `COVERAGE.json` goes stale for a day (nobody re-runs the coverage pass);
or a source gets purged from the roster but a stray record still carries its entries; or one of
the seven internal `try` blocks in `reconcile()` starts raising because a JSON file it depends
on (`SWEEP_ROLL.json`, `COVERAGE.json`, `ROSTER_PURGES.json`, `pipeline.PHASES`, …) goes
missing or malformed. In every case `allsweep.py --quick` or `allsweep.py` itself would show the
finding on stderr/stdout, but WATCH.md — the file whose entire purpose is to be the thing a
human actually reads — shows nothing wrong. **VERIFIED** (read both files in full, enumerated
every `note()` call site and its exact string, checked each against the filter).

### 2. MAJOR — `overwatch.py:650-656` — a closed or retired finding can never reopen, even if the identical defect reappears

```python
for f in found:
    fid = _fingerprint(m, f)
    if fid in led["findings"]:
        continue
    f.update({"state": "open", "first_seen": time.time(), "digest": d})
    led["findings"][fid] = f
    fresh += 1
```

`save()`'s own docstring (overwatch.py:180-192) states as an invariant that "NOTHING in this
module ever deletes a finding or a `seen` entry — retirement is a state change, not a removal."
That is true, but the corollary is that `fid in led["findings"]` is `True` forever once a
fingerprint has ever been filed, **regardless of its current state**. The discovery loop above
skips re-adding a finding whenever its fingerprint already exists in the ledger, whether that
entry's state is `open`, `retired`, or `closed`. There is no code path anywhere in the file that
transitions a `closed` or `retired` finding back to `open`.

Concrete scenario: `verify_open()` (overwatch.py:453-501) marks a finding `closed` when the
local model's re-check verdict is `"refuted"` — itself an LLM judgment call that can be wrong.
If it was wrong, or if a genuinely-fixed defect is later reintroduced (a revert, a merge, a
copy-paste of old code), the model's next `review()` pass over that module will rediscover the
identical `symbol`/`actual` text, compute the identical fingerprint (`_fingerprint()` hashes
`module|symbol|actual[:80]`, not the digest or line numbers), find it already present in
`led["findings"]`, and silently drop it — never surfacing in WATCH.md again. Same for `retired`
findings whose file changed away from the defect and then changed back to it. **VERIFIED** (read
the full state-transition surface: `state` is only ever set at overwatch.py:491 `"closed"`,
:628 `"retired"`, and :654 `"open"`; grepped for every assignment/read of `f["state"]` in the
file to confirm no reopen path exists).

### 3. MAJOR — `overwatch.py:486-487` — a failed re-verification attempt is recorded identically to a successful one, starving the auto-triage queue

```python
got = _ask(VERIFY_SYSTEM, prompt, VERIFY_SCHEMA, local=local)
f["last_verified"] = time.time()
checked += 1
verdict = (got or {}).get("verdict")
```

`_ask()` (overwatch.py:348-380) returns `None` whenever the local model was busy past
`CLOUD_BUDGET` for the round (yield path, line 378) or whenever the cloud fallback call itself
fails. `verify_open()` bumps `f["last_verified"]` and increments `checked` **unconditionally**,
before it even looks at whether `got` is `None`. `rotation`'s open-findings queue
(`verify_open`, line 463-465) sorts by `last_verified` ascending — oldest first — precisely so
every finding eventually gets a turn. But a finding whose verification attempt *failed* gets its
`last_verified` bumped exactly as if it had *succeeded*, so it goes to the back of the queue
without ever having actually been checked. During any stretch where the GPU is busy or the
cloud call is failing, open findings can cycle through repeated no-op "checks" that never
produce a verdict, while `print("auto-triage: %d open finding(s) re-verified, %d refuted and
closed" % (checked, closed))` reports the failed attempts as if they were real re-verifications.
This is the project's signature failure class — a check that cannot fail, because failure and
success update the bookkeeping the same way. **VERIFIED** (traced `_ask`'s `None`-return paths
and `verify_open`'s unconditional bump against `rotation`'s reliance on `last_verified` for
scheduling — the docstring at overwatch.py:454-462 does not mention this).

Note: I also checked the brief's other stated suspicion for this path — "can a model failure be
read as a refutation?" It cannot: `verdict = (got or {}).get("verdict")` evaluates to `None`
when `got` is `None`, and only the literal string `"refuted"` triggers the close branch, so a
`None` response is not mistaken for a refutation. **VERIFIED not a bug** (ruled out). Likewise,
closing a finding always records a non-empty `f["verdict"]` string (line 492) — a finding cannot
be closed with no recorded verdict. **VERIFIED not a bug** (ruled out).

### 4. MAJOR — `overwatch.py:570-573` — WATCH.md's open-finding count and its listing diverge (Hard Rule 0)

```python
lines.append(f"**{len(open_f)} open** ({len(hi)} high). Newest first.")
lines.append("")
for f in sorted(open_f, key=lambda x: (-(x.get("severity") == "high"),
                                       -x.get("first_seen", 0)))[:40]:
```

The header count `len(open_f)` (line 570) is uncapped and reflects the true total, but the
enumeration that follows is truncated to the newest/highest-severity **40** (`[:40]` at line
573). Once open findings exceed 40, WATCH.md's header and its body disagree — the report says
"**87 open**" (say) and then lists only 40 of them, with nothing in the text telling the reader
that 47 findings exist but are not shown. This is exactly the class Hard Rule 0 forbids: a
truncation of an ordered listing wearing the shape of a complete one, on the one file whose job
is to be the complete, trustworthy record of what's broken. **VERIFIED** (read directly; no
other code path surfaces the remaining 47).

### 5. MEDIUM — `overwatch.py:626-629` — a finding for a deleted module is never retired

```python
d = _digest(os.path.join(SRC, f["module"] + ".py"))
if d and d != f.get("digest"):
    f["state"] = "retired"
    f["retired_at"] = led["last_run"]
```

`_digest()` (overwatch.py:213-219) returns `""` when the target file can't be opened (e.g. the
module was deleted or renamed), catching the exception via `silence.note`. The retirement
condition `if d and d != f.get("digest")` is falsy whenever `d == ""`, since an empty string is
falsy — so a finding whose module file no longer exists at all is **never** retired, and stays
`open` (and therefore listed in WATCH.md) indefinitely, pointing at code that has been deleted.
This is the most-stale possible case (total removal) being the one case the staleness check
silently lets through. **VERIFIED** by reading `_digest`'s exception path and the retirement
condition directly; this is a logic read, not empirically exercised against an actual deleted
module.

### 6. MINOR/COSMETIC — `overwatch.py:225` — `_STATE_RANK` carries two dead states

```python
_STATE_RANK = {"open": 0, "stale": 1, "confirmed": 1, "refuted": 2, "retired": 2, "closed": 2}
```

I grepped every assignment to `f["state"]` in the file: only `"open"` (line 654), `"closed"`
(line 491), and `"retired"` (line 628) are ever written. `"stale"`, `"confirmed"`, and
`"refuted"` are never assigned as a `state` value anywhere (verify_open's confirmed path only
increments `f["confirmed_n"]`, at line 496 — it does not set `state` to `"confirmed"`). The
comment above `_STATE_RANK` ("a terminal verdict outranks an open one... the stale writer is not
always the one with less to say") describes a richer lifecycle than the code actually has. Not a
functional bug — the merge logic (`_progress`/`_merge_ledgers`) still works correctly for the
three states actually in use — but the mapping and its comment overstate the real state machine.
**VERIFIED**.

---

## onomast.py

### 7. MAJOR — `onomast.py:311-356` — `register_for()`'s genre/feature voting is dead code; every world uses the hash fallback

```python
def register_for(group_id, genre_register=None, features=None):
    """...
    Falls back to a hash of the group id ONLY when neither a genre nor features are known. That
    fallback used to be the whole function, and it produced the register that gave Alien and Doom
    the flowing elvish sound and denied Greek myth the classical one.
    """
    if not genre_register and not features:
        return REGISTER_ORDER[int(hashlib.sha256(str(group_id).encode()).hexdigest(), 16)
                              % len(REGISTER_ORDER)]
    votes = {}
    ...
```

and the sole call site, `onomast.py:356`, inside `name_worlds()`:

```python
reg = register_for(v["continuity_group"])
```

`register_for` is called with only the positional `group_id`; `genre_register` and `features`
both default to `None`. That means `if not genre_register and not features:` is always `True`,
and the function **always** takes the hash-fallback branch the docstring says was replaced — the
entire voting mechanism below it (the `votes` dict, `FEATURE_SHIFT` table at lines 278-300,
`GENRE_WEIGHT`/`FEATURE_WEIGHT` at lines 307-308, and the tie-break logic at lines 329-334) is
unreachable in current usage. I grepped the entire `src/` tree for other callers of
`register_for`:

```
src/navtree.py:157:    def register_for(key):        # a DIFFERENT, locally-defined function
src/navtree.py:192:            nm = O.coin_well_formed(f"tier|{k}", register_for(k), taken)
src/onomast.py:311:def register_for(group_id, genre_register=None, features=None):
src/onomast.py:356:            reg = register_for(v["continuity_group"])
```

`navtree.py` defines its own separate `register_for(key)` (shadowing the name, not importing
onomast's) and never calls `onomast.register_for` with genre/features either. So the only call
to `onomast.register_for` anywhere in the codebase never supplies a genre or a feature set — the
carefully-tuned two-way-influence system (the comment at :301-306 specifically justifies the 3:2
weight balance so "the world had... a voice") produces zero effect on any world actually named by
this pipeline; every world's register is still the pure hash of its `continuity_group`, which is
exactly the bug the docstring claims was fixed. **VERIFIED** (found the sole call site and
confirmed via repo-wide grep that no caller supplies `genre_register` or `features`).

---

## sweep.py

### 8. MAJOR — `sweep.py:20-22` docstring claims strict funnel nesting the code does not enforce

```
Each stage is a strictly smaller set than the one above, and the size of each drop is the real
statement of where the project stands. A number that only ever gets reported at the top of the
funnel is a number that hides the four stages below it.
```

I read `sweep()` (lines 125-164) and `report()` (lines 167-224) in full. The seven funnel stages
are computed as follows, each an **independent** boolean read from an unrelated data source:

- `catalogued` = `bool(e.get("catalogued"))` — a per-entry flag on the catalogue record itself.
- `addressed` = `bool(shelf)`, where `shelf` comes from `navtree_names()`/`NAVTREE.json`,
  looked up by `src` (the *source*, not the entry) — independent of the entry's `catalogued`
  flag.
- `reachable` = `bool(host)`, from `feats.HOSTS`, looked up by `src` — independent of both of
  the above.
- `read` = `pages > 0`, only set `if host:` — genuinely nested under `reachable` by
  construction (line 150-159), so this one dependency **is** real.
- `evidenced` = `axes > 0`, set only if `ev.get("text")` is truthy inside the same `if host:`
  block — nested under `reachable`, but not provably nested under `read` (it is possible for
  `ev.get("text")` to be truthy while `ev.get("pages_read")` is empty, i.e. `axes>0` with
  `pages==0`).
- `assayable` = `axes >= 2` — trivially nested under `evidenced` since it's the same variable.

Nothing in the code cross-checks that a source with a shelfmark (`addressed`) is also
`catalogued`, or that a `reachable` source is `addressed`. These three come from three separate
JSON files (`RESOLVED`/per-entry catalogue flag, `NAVTREE.json`, `feats.HOSTS`) with no join
enforcing containment between them. It is entirely possible in the underlying data for a source
to have a host mapping (`reachable`) without a navtree shelfmark (`addressed`), or to have a
shelfmark without the entry itself being marked `catalogued` — in either case the funnel's
"strictly smaller set" claim breaks for that row, and `report()`'s `drop = prev - f[k]` figures
(line 185, printed as "-{drop:,}" at line 188) are computed as plain count differences, not as
true set differences. If the sets are not actually nested, those printed drop counts do not mean
what the docstring says they mean — they can even be misleading in either direction depending on
how the independent flags actually correlate in the data. **VERIFIED** as a logic property of
the code (no enforced containment exists for the first three stages); I did not additionally
run the sweep against live data to quantify how often the three diverge in practice, since that
would require executing the pipeline, which is out of scope for a read-only audit.

---

## halo.py

### 9. MAJOR — `halo.py:146-174` — the same UnicodeEncodeError-before-write bug that `handbuilt.py` fixed was never applied here

```python
def main():
    ...
    out = compute()
    rank = sorted(...)
    print("=" * 74)
    print("HALO -- BY MAGNITUDE (presence thesis)")
    print("=" * 74)
    for n, rec in rank:
        print("  %-20s %-16s %s" % (n, rec["assay"]["moth_number"], rec["anchor"]))
    if a.full:
        for n, rec in rank:
            ...
            print("%s   %s" % (n, rec["assay"]["moth_number"]))
            ...
    # ATOMIC -- the m100 tail, 2026-08-25.
    silence.write_json(OUT, out, indent=1, ensure_ascii=False)
```

`rec["assay"]["moth_number"]` is formatted by `assay.py:450` as
`f"𝔄 {anchor}.{...} ± {interval:.2f}"` — it begins with U+1D504 FRAKTUR CAPITAL A. `handbuilt.py`
(same batch, lines 438-465) hit this exact character on this exact field and documented the
consequence in a comment: on a default cp1252 Windows console, printing `moth_number` before the
JSON write raises `UnicodeEncodeError`, killing the process mid-print, **before** the write runs
— so the output file (there, `HANDBUILT_ASSAYS.json`; here, `HALO_ASSAYS.json`) silently stops
being regenerated while a stale copy on disk keeps looking current. `handbuilt.py`'s fix was
twofold: move the write before any printing (handbuilt.py:453-460), and additionally call
`sys.stdout.reconfigure(encoding="utf-8", errors="replace")` (handbuilt.py:462-465) as a
belt-and-suspenders measure for the console itself.

`halo.py:main()` does neither: the print loop over `moth_number` (lines 157-158, and again under
`--full` at lines 160-169) runs first, and `silence.write_json(OUT, out, ...)` runs last, at
line 171 — after every print. There is no `sys.stdout.reconfigure` call anywhere in the file.
Under the identical console-encoding condition that motivated the `handbuilt.py` fix,
`python src/halo.py` would raise before ever reaching the write, and `HALO_ASSAYS.json` would go
stale exactly the way `HANDBUILT_ASSAYS.json` did before it was fixed. **VERIFIED** by direct
comparison of the two files' `main()` functions and the shared `moth_number` format string in
`assay.py:450`; not reproduced by actually forcing a cp1252 console in this session, but the
code path and the offending character match `handbuilt.py`'s documented incident exactly.

---

## Summary table

| # | Severity | Location | Verified |
|---|----------|----------|----------|
| 1 | MAJOR | overwatch.py:326-329 | VERIFIED |
| 2 | MAJOR | overwatch.py:650-656 | VERIFIED |
| 3 | MAJOR | overwatch.py:486-487 | VERIFIED |
| 4 | MAJOR | overwatch.py:570-573 | VERIFIED |
| 5 | MEDIUM | overwatch.py:626-629 | VERIFIED |
| 6 | MINOR/COSMETIC | overwatch.py:225 | VERIFIED |
| 7 | MAJOR | onomast.py:311-356 | VERIFIED |
| 8 | MAJOR | sweep.py:20-22 vs 125-224 | VERIFIED |
| 9 | MAJOR | halo.py:146-174 | VERIFIED |
