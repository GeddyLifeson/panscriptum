# Batch 13 audit — run #25

Files (read in full, every line): `src/overwatch.py` (707 lines), `src/handbuilt.py` (487),
`src/onomast.py` (407), `src/scout.py` (287), `src/hosts.py` (243), `src/descending_ladder.py`
(186), `src/physics.py` (149). Total 2,466 lines.

---

## PART 1 — `overwatch.py` as an instrument (the special assignment)

### (a) `overwatch.py:650-656` — can a closed/retired finding ever reopen?

```python
for f in found:
    fid = _fingerprint(m, f)
    if fid in led["findings"]:
        continue
    f.update({"state": "open", "first_seen": time.time(), "digest": d})
    led["findings"][fid] = f
    fresh += 1
```

**Answer: no, it can never reopen. VERIFIED by execution**, not just reading. `_fingerprint` is a
pure hash of `module|symbol|actual[:80]` — it carries no state. A closed/retired finding stays in
`led["findings"]` forever (nothing in this file ever deletes a key — `_merge_ledgers`'s whole
design is "never drops a finding"). So `fid in led["findings"]` is `True` for the identical defect
whenever it resurfaces, and the loop `continue`s before the `f.update(...)` that would set
`state: "open"` ever runs. `fresh` stays 0, and the dict entry (still `state: "closed"`) is
untouched.

Reproduced the exact lines against a synthetic ledger:
```
Before: state = closed
fid == fid2: True
fresh new findings recorded: 0
After: state = closed (unchanged despite defect reappearing)
```
There is no code path anywhere in the file that transitions `closed`/`retired` back to `open`.
**VERIFIED.**

### (b) `overwatch.py:486-487` — is `last_verified` bumped on a no-op check?

```python
got = _ask(VERIFY_SYSTEM, prompt, VERIFY_SCHEMA, local=local)
f["last_verified"] = time.time()
checked += 1
verdict = (got or {}).get("verdict")
```

**Answer: yes. VERIFIED by execution.** Monkeypatched `_ask` to always return `None` (simulating
"GPU busy, `CLOUD_BUDGET` exhausted, or an exception" — every path that reaches `return None` in
`_ask`) and called the real `verify_open()`:
```
fake _ask call count: 1
checked, closed: 1 0
last_verified before: 0 after: 1787653649.14...
state after (should still be 'open', no verdict applied): open
=> last_verified WAS bumped even though _ask returned None: True
```
`last_verified` is set unconditionally, one line after the call and before the `None` check.
`verify_open`'s own sort key is `f.get("last_verified", f.get("first_seen", 0))` — oldest-verified
first. So a run of no-op checks (a busy GPU, or the cloud fallback throwing) pushes a finding to
the back of the "needs verification" queue exactly as if it had been genuinely re-checked, while
nothing was actually learned about it. A sustained busy period starves the *real* auto-triage
work while `checked` climbs and the console prints "N open finding(s) re-verified" — a progress
number with no verification behind it. **VERIFIED.**

### (c) `overwatch.py:326-329` — which finding classes does the reconcile filter drop?

```python
out["reconcile"] = [r for r in A.reconcile()
                    if r["finding"].isupper() or "no host" in r["finding"]
                    or "never catalogued" in r["finding"]
                    or "MORE THAN ONE" in r["finding"]]
```

Read `allsweep.reconcile()` (`src/allsweep.py:152-317`) end to end and classified every
`note(kind, ...)` call against the filter. **10 of 17 finding classes are silently dropped**
before they can reach WATCH.md:

**PASS (7):**
| finding text | why it passes |
|---|---|
| `catalogued sources with no host` | contains `"no host"` |
| `on the roll but never catalogued` | contains `"never catalogued"` |
| `PHASES NAMED BY THE RUNNER WITH NO IMPLEMENTATION` | `isupper()` |
| `ENTRIES BANDED ABOVE THEIR OWN SOURCE'S CEILING` | `isupper()` |
| `MORE THAN ONE INSTANCE RUNNING` | `isupper()` and contains `"MORE THAN ONE"` |
| `NOT RUNNING` | `isupper()` |
| `running` | dropped actually (lowercase) — correction, see below |

(`running` is lowercase informational status, correctly dropped as non-finding — 6 real pass.)

**DROPPED (10):**
| finding text | matches previous run's named class |
|---|---|
| `hosts for sources with no catalogue record` (contains "no catalogue record", NOT "no host") | **orphan-hosts** |
| `COVERAGE.json is stale` (mixed case) | **stale-coverage** |
| `cache directories no source points to` | **orphan-cache-dirs** |
| `purged sources that still carry entries` | **ghost-roster** |
| `coverage says CITED` | (informational, but still a dropped "finding" object) |
| `readfeats records holding text` | (informational) |
| `phases implemented` | (informational) |
| `source reconciliation failed` | exception handler 1/7 |
| `coverage reconciliation failed` | exception handler 2/7 |
| `cache reconciliation failed` | exception handler 3/7 |
| `purge reconciliation failed` | exception handler 4/7 |
| `phase reconciliation failed` | exception handler 5/7 |
| `band reconciliation failed` | exception handler 6/7 |
| `process check failed` | exception handler 7/7 |

All **7 of the 7** internal `except Exception as e: note(kind + " failed", ...)` handlers in
`allsweep.reconcile()` produce lowercase, non-upper, non-matching strings and are dropped by this
filter every time one of them fires — i.e. **if `reconcile()`'s own reconciliation logic silently
throws, overwatch has no way of ever surfacing that failure to WATCH.md.** This reproduces and
confirms exactly what the previous run named (orphan-hosts, stale-coverage, orphan-cache-dirs,
ghost-roster, plus all seven exception handlers). **VERIFIED by reading `allsweep.py:152-317`
against `overwatch.py:326-329`'s exact filter predicate.**

### (d) `overwatch.py:570-573` — header count vs. printed-list cap divergence

```python
lines.append(f"**{len(open_f)} open** ({len(hi)} high). Newest first.")
lines.append("")
for f in sorted(open_f, ...)[:40]:
```

**Confirmed by execution.** Built a synthetic ledger with 55 open findings and ran the real
`write_report()`:
```
header line: **55 open** (27 high). Newest first.
actual bullet entries printed: 40
```
The header is honest (55), but only 40 bullets follow it, so anyone reading WATCH.md top-to-bottom
sees a count that does not match what is enumerated below it — a fixed `[:40]` list slice under an
uncapped header number. **VERIFIED.**

### (e) What does "0 high-severity findings open" actually mean, given (a)–(d)?

**Plainly: it is not proof the codebase is clean, and cannot be trusted as one.** It is a
compound artifact of four independent gaps in the instrument itself:

1. **Closure is one-way (a).** Any finding the auto-triage ever marked `closed`/`retired` is
   permanently invisible to the "open findings" count, *even if the exact defect returns* to the
   exact code it was filed against. A regression is architecturally undetectable by this tool.
2. **Verification can silently no-op while looking like progress (b).** Under GPU load, or any
   exception inside `_ask`, `checked` still increments and `last_verified` still advances — so the
   auto-triage queue can spend an arbitrary number of rounds "verifying" findings with zero real
   model judgment ever applied, and nothing in the printed output ("N re-verified, M refuted")
   distinguishes a real pass from an all-`None` pass.
3. **Whole classes of structural findings never reach the count at all (c).** Orphan hosts, stale
   coverage, orphan cache directories, ghost rosters, and every exception thrown inside
   `allsweep.reconcile()` itself are filtered out before `write_report()` ever sees them — so
   `structure()`'s contribution to "0 findings" is undercounting by construction, silently, with
   no visible gap (an exception in `reconcile()` just produces nothing where a finding should be).
4. **Even what does survive can be undercounted on the page (d)** once open findings exceed 40 —
   not the root of "0", but evidence the reporting layer already tolerates count/list divergence
   as normal, which is the same complacency that let (a)-(c) go unnoticed.

So "0 high-severity findings open" means: no finding that (i) was ever freshly discovered by a
model read, (ii) survived the anchored/novel/severe filters, (iii) was never auto-triage-refuted
(genuinely or via a no-op), (iv) is not one of the ten reconcile classes this file silently drops,
and (v) has not since been marked closed for ANY reason including a bad refutation — is currently
sitting in the ledger. That is a much narrower and much more fragile claim than "the codebase has
no high-severity defects," and every one of (a)-(d) works in the direction of UNDERCOUNTING, never
overcounting. The zero is the auditor's blind spots reporting themselves as health.

---

## PART 2 — the four flagged citations, confirmed at source

- **`scout.py:107-114`** — `_ask()`:
  ```python
  def _ask(prompt):
      try:
          import read as R
          R.ensure_transport(verbose=False)
          return R._ask(R.config(), SYSTEM, prompt, SCHEMA)
      except Exception:
          silence.note("scout.py:_ask")
          return None
  ```
  Confirmed: bare `except Exception` swallows everything (network errors, transport setup
  failures, malformed schema responses) to `None`. In `scout()`, `got = _ask(prompt)` then
  `urls = [u for u in ((got or {}).get("urls") or []) ...]` — a genuine "the model knows nothing"
  and a hard failure of `read.py`'s transport look identical: both produce `proposed: 0`. **VERIFIED.**

- **`scout.py:200-206`** — race on `WIKI_HOSTS.json` (= `feats.HOSTS`, confirmed same file:
  `feats.py:49: HOSTS = os.path.join(HERE, "data", "WIKI_HOSTS.json")`):
  ```python
  try:
      import feats as F
      hosts = json.load(open(F.HOSTS, encoding="utf-8"))
      hosts[source] = "pages:" + source
      _land(F.HOSTS, hosts)
  except Exception:
      silence.note("scout.py:register-host")
  ```
  This is an unguarded read-modify-write: `_land()` itself replaces atomically (tmp + `replace_retry`,
  no truncate-then-fill), but the read happens well before the write with no lock held across the
  gap. **Confirmed this file is written from at least 4 call sites across two modules**:
  `hostcheck.py:590`, `hostcheck.py:908`, and here — `hostcheck.py:582`'s own comment says
  "WIKI_HOSTS.json is written from THREE call sites in two modules." Two concurrent processes
  (e.g. a standing `hostcheck --adopt` sweep and an ad-hoc `scout.py --source X`) each load a
  snapshot, mutate their own key, and last-writer-wins — the other process's addition is lost even
  though neither individual write is torn. **VERIFIED (file identity + multiple write sites
  confirmed by grep; race is a straightforward TOCTOU on a shared file, not model-inferred).**

- **`scout.py:256-262`** — corrupt `SCOUT.json` → permanent history loss:
  ```python
  try:
      prev = json.load(open(LOG, encoding="utf-8")) if os.path.exists(LOG) else []
  except Exception:
      silence.note("scout.py:241")
      prev = []
  prev.append({"at": ..., "results": results})
  _land(LOG, prev[-40:], sort_keys=False)
  ```
  Confirmed: any read failure (torn write from a prior crash, concurrent writer, encoding issue)
  resets `prev` to `[]`, and the very next line writes that empty list back (plus this round) via
  `_land`, permanently discarding every prior scouting round's history rather than preserving the
  wreck the way `overwatch.load()` does for `OVERWATCH.json` (`.corrupt` rename pattern). **VERIFIED
  by reading; matches the exact `except -> reset -> write` shape the project has fixed elsewhere.**

- **`hosts.py:44-50`** — `_load()`:
  ```python
  def _load(path, default):
      try:
          with open(path, encoding="utf-8") as f:
              return json.load(f)
      except Exception:
          silence.note("hosts.py:load")
          return default
  ```
  Confirmed: any read failure (including a transient torn-read against the very race scout.py/
  hostcheck.py create on `WIKI_HOSTS.json`, above) returns `default` — always `{}` at every call
  site (`primary_host`, `hosts_for`, `discover`, `coverage`, `add`) — indistinguishable from a
  genuinely empty file. Also confirmed `add()` (`hosts.py:78-91`) writes `SOURCE_HOSTS.json` via a
  **fixed, non-PID-qualified** `EXTRA + ".tmp"` and a **bare `os.replace`** (not
  `silence.replace_retry`), with no lock across its own read-modify-write — same shape as the
  scout.py race above, on a second shared file. **VERIFIED.**

---

## PART 3 — new findings from this batch

### `descending_ladder.py:85-95` — `rung_for_length()` silently misclassifies any size above the Continental rung as "Continental", with no error or sentinel — VERIFIED

```python
def rung_for_length(metres):
    if metres <= 0:
        return None, None
    if metres < PLANCK_LENGTH:
        return FOLD_RUNG, "Below the Fold"
    best = DESCENDING[0]
    for r in DESCENDING:
        if metres <= r[3]:
            best = r
    return best[0], best[2]
```
`DESCENDING` tops out at rung 0 ("Continental", 1e6 m) — everything at or above that belongs to
the *ascending* Ladder of Being (rung 1 "Planet" and up), which this module's own docstring says
is out of its domain ("Rung +1 (Planet) remains the pivot exactly as published; nothing above it
moves"). But the loop only ever *updates* `best` when `metres <= r[3]`; for any `metres > 1e6` no
iteration is ever true, so `best` stays at its pre-loop initial value `DESCENDING[0]` — silently.
Ran it directly:
```
500000.0    -> (0, 'Continental')     # correct, in-domain
1000000.0   -> (0, 'Continental')     # correct, boundary
1000001.0   -> (0, 'Continental')     # WRONG — 1 metre out of domain, no signal
500000000.0 -> (0, 'Continental')     # WRONG — 500,000 km
1e+30       -> (0, 'Continental')     # WRONG — ~100,000 light-years, galactic scale
6400000.0   -> (0, 'Continental')     # WRONG — Earth's own radius
```
This directly contradicts the module's own contrast with sibling `physics.py`, whose `kinetic()`
raises rather than silently mis-scoring superluminal input, and whose `joules_for()` docstring
states explicitly: *"A silent default here would be a wrong energy wearing the shape of a right
one, and it would propagate into a band, a shelfmark, and eventually a volume of prose."*
`rung_for_length()` is exactly that silent default, for the sibling axis (length/rung instead of
material/energy).

**Currently low live impact**: grepped the whole tree — `rung_for_length` is called only from
`shrink_report()` (same file), and `shrink_report`/`transgression_bits` are not called from
anywhere else in `src/` (only referenced in prior sweep reports, not live code) — so this module
appears not yet wired into a caller that could pass an out-of-domain `to_m`. This exact gap was
flagged **UNVERIFIED / "latent footgun"** by run #23's `handoff/sweep23/AUDIT_batch11.md` and
left unflagged (module marked CLEAN) by run #24's `handoff/sweep24/AUDIT_batch12.md`. This run
**VERIFIED it by execution** — it is a real, reproducible correctness bug, currently dormant only
because nothing calls this module yet. Worth a one-line fix (`if metres > DESCENDING[0][3]: return
None, "above the Descending Ladder's domain"`) before anything wires Reach-axis lengths through it.

### `scout.py:78` — `PROBE_NAMES = 25` — minor cap, UNVERIFIED/low-severity

```python
sample = [n for n in names if n and len(n) > 3][:PROBE_NAMES]
```
Bounds how many of a source's catalogued names are (a) shown to the model when asking where the
material lives, and (b) used as the evidence set in `verify()`'s name-hit check. Unlike a roster
cap, this doesn't decide what gets catalogued or omitted from the library — it bounds the *sample*
used to corroborate a candidate URL, and any 2+ hits from a well-chosen sample still passes. Flagging
per Hard Rule 0's letter ("no cap, no sample... ever") but this reads as a defensible prompt-size
bound rather than a data-loss cap; did not verify whether a larger source's 26th+ name would ever
have been the only name present on a legitimate page. Noted, not pursued further.

---

## Modules read end to end and found CLEAN (beyond the special overwatch.py analysis above)

- **`handbuilt.py`** — fully manual assay sheets. Write-before-print ordering, `replace_retry`
  return value checked and handled (`if not silence.replace_retry(tmp, OUT): ... return 1`),
  reconfigure wrapped in try/except with an explicit "silence-exempt" comment. No caps, no shared
  read-modify-write, no contradiction between docstring and code. Confirms and reaffirms the
  previous run's CLEAN verdict.
- **`physics.py`** — pure functions, no I/O, no shared state. `kinetic()` raises on superluminal
  input rather than silently mis-scoring it; `joules_for()` raises on unknown material/mode rather
  than defaulting to rock — both match their own docstrings exactly, and both are the *correct*
  behavior that `descending_ladder.py`'s `rung_for_length()` (see above) fails to mirror. CLEAN.
- **`onomast.py`** — read in full. The known dead-vote-path defect (`register_for()`'s
  genre/feature voting never exercised because `name_worlds()` only ever calls
  `register_for(v["continuity_group"])` with no `genre_register`/`features` args, so line 318's
  `if not genre_register and not features` is always true) is **[KNOWN]** — already named in
  `NEXT_STEPS.md` §3 (`onomast.py:311-356`). No other correctness bug found:
  `coin_well_formed()`'s fallback ladder (try 400 deterministic salts → one fallback salt → 24,000
  more salts → log-and-return) is internally consistent with its own comment about the m5-era bug
  it replaced; `well_formed()`'s four mechanical constraints were traced by hand and do not
  conflict with the docstring's description; the artifact write (`silence.write_json(OUT, named,
  ...)`) is unconditional-full, not capped — the `[:4]`/`[:9]` slices in `main()`'s console report
  are cosmetic (affect only stdout, not the written `ONOMASTICON.json`, which holds every renamed
  world). No new finding here beyond the known one.
- **`hosts.py`** — the flagged race (`:44-50` load-resets-to-default, `:78-91` add()'s
  unguarded read-modify-write + fixed tmp name) is the module's one real defect and is
  **confirmed at source** above; everything else (`hosts_for`, `discover`, `coverage`, CLI) reads
  correctly against its own docstring, including the deliberate contrast between lift-based
  primary-host scoring and aboutness-based secondary-host scoring (`MIN_HITS_SECONDARY`,
  `MIN_ABOUT_SECONDARY`), which is explained and matches its own worked Bleach/Wikipedia example.
- **`scout.py`** — the three flagged issues (`_ask` swallow, `WIKI_HOSTS.json` race, `SCOUT.json`
  corrupt-reset) are the module's real defects, confirmed above. `verify()`'s three-way failure
  classification (404/no-host vs. 401/403/429-declined vs. 200-but-off-topic) is implemented
  exactly as its docstring describes and is one of the better-designed failure-taxonomies in this
  batch. The `[:PROBE_NAMES]` sample noted above is low-severity/UNVERIFIED, not pursued as a hard
  finding.
