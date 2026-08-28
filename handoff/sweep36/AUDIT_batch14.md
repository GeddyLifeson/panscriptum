# AUDIT — batch 14, run #36

Modules: `hostcheck.py`, `workorders.py`, `chain.py`, `endpoint.py`, `worldseed.py`,
`catalogue_models.py`, `tells.py`, `halo.py`

Read in full (not skimmed): all eight, source only, current on-disk state as of this sweep.

---

## workorders.py

### MAJOR — `battery_faults()` still mirrors the OLD `allsweep` grade formula and does not read
the new `estate_faults` key, so an ESTATE-tier failure that fails the battery never files a work
order.

`allsweep.py` was changed today (run #36, batch 08, per its own comment) to compute
`est_faults = estate_faults(est)`, land it as its own top-level key
(`"estate_faults": est_faults`), and fold it into its own `bad` count:

```
bad = (len(broken)
       + sum(1 for r in verifiers if r["crashed"] or r.get("timeout"))
       + len(lint_bad)
       + len((est.get("artifacts") or {}).get("bad", []))
       + len(est_faults))
```

`allsweep.py`'s own comment says explicitly: *"`workorders.battery_faults` reads this file to
decide what the battery says, and it reads `estate.artifacts.bad` only -- so the four ESTATE
tiers were invisible to the queue as well as to the grade... (run #36, batch 08)"* — describing
the fix as done. It is not done on this side. `workorders.py`'s `battery_faults()` (still) builds
its `bad` list this way:

```python
        for r in (allsweep.get("imports") or []):
            if not r.get("ok"):
                bad.append("import %s: %s" % (r.get("module"), str(r.get("detail"))[:160]))
        for r in (allsweep.get("verifiers") or []):
            if r.get("crashed") or r.get("timeout"):
                bad.append("verifier %s %s" % (r.get("check"), ...))
        for ln in (allsweep.get("lint") or []):
            bad.append("lint %s" % str(ln)[:160])
        for art in (((allsweep.get("estate") or {}).get("artifacts") or {}).get("bad") or []):
            bad.append("estate artifact %s" % str(art)[:160])
```

There is no `allsweep.get("estate_faults")` anywhere in the file (`grep` confirms zero other
hits). So `MASTER CHARTER MISSING`, `CHARTER_SPINE_CODES.json MISSING`,
`TERMINAL HAS NO HTML ENTRY POINT`, `OLLAMA UNREACHABLE`, or any other CHARTER/WRITTEN/
TERMINAL/EXTERNAL fault can make `allsweep.py` exit 1 and print "N subsystem(s) in a bad state",
while `workorders.battery_faults()` — the thing that is supposed to turn that into a work order —
sees `bad == []`, leaves `out["BATTERY_GRADED"] = None`, and `sweep_detectors()` resolves/closes
`BATTERY_GRADED` as if the battery were clean. This is exactly the class of bug run #33 wrote
this function to fix (a red battery that files nothing), reintroduced by a formula drift between
two files that both claim to track each other.

The comment directly above the `bad` loop (line ~133-139) is now also stale and should be read
with that in mind: *"Mirrors allsweep's own `bad` formula exactly -- imports, crashed/timed-out
verifiers, lint, bad estate artifacts -- so the two cannot drift into disagreeing about what
'bad' means."* That claim is false as of today's `allsweep.py` change; the two have drifted.

**Fix shape** (not applied — I am read-only): add `for f in (allsweep.get("estate_faults") or
[]): bad.append("estate %s: %s" % (f.get("tier"), f.get("finding")))` alongside the existing four
loops.

### Verified correct, not a defect (recording so nobody re-flags it)

- `resolve()`'s ordering — "did it land" tested strictly before "did it exist" — is correct as
  written and matches its own docstring's stated intent (`landed, rec = _mutate(_change)` then
  `if not landed: ...` then `if rec is None: ...`).
- `_mutate()`'s CAS loop re-reads `(d, digest)` fresh on every attempt via `_load(with_digest=True)`
  inside the `for a in range(attempts)` loop, so a stale-write refusal genuinely re-applies
  `change` against a fresh copy rather than retrying the same doomed digest. Correct.
- `file_order()` is pure in the dict handed to it by `_mutate` (re-derives `first_seen`/`seen`
  from `prev = d.get(oid) or {}` on every call), which is required for the retry-and-reapply
  design to be safe. Correct.
- The `_mutate` temp name is `"%s.%d.%d.tmp" % (OPEN_FILE, os.getpid(), a)` — pid + attempt index,
  no thread id. This is the same convention `scout._mutate` uses. QUESTION, not a defect: nothing
  in the current call graph (`drill.py`, `escalation.py`, `mutate.py`, `secondopinion.py`) appears
  to call `file_order`/`resolve` from multiple threads of the same process, so the missing
  thread-id component is theoretical here, not demonstrated live.

### MINOR (pattern, not unique to this file) — evidence caps inside a filed work order

`PREFLIGHT_PROBLEM`'s `evidence=rows[:20]` and `BATTERY_GRADED`'s `evidence=bad[:20]` cap the
*evidence* attached to a work order at 20 items, while the `what` text does report the true count
(`"%d problem(s)"` / `"%d subsystem(s) bad"`). This is a QUESTION rather than a confirmed Hard
Rule 0 violation — the full count is preserved in the visible text, only the supporting detail
list is capped, and this matches a convention used elsewhere in the tree for diagnostic evidence
attached to a finding (as opposed to a catalogue roster). Flagging so a future sweep can decide
if it should be uncapped too.

---

## chain.py

### MINOR — persisted `unmatched` field in `data/CHAIN.json` is a ranked-then-truncated list
(Hard Rule 0 shape), with no total count recorded alongside it.

```python
        "unmatched": (unmatched.most_common(40) if hasattr(unmatched, "most_common")
                      else (unmatched or [])),
```

`unmatched` is a `Counter` of every name from a proposed contest outcome that failed to match the
entity index (per the `local_unmatched` accounting fixed in run #33 to stop the exact
undercounting this comment describes). `write_result()` — "THE ONE WRITER for `data/CHAIN.json`"
— lands only the top 40 by frequency into the persisted artifact, and nowhere in the written
`out` dict is `len(unmatched)` or the sum of all counts recorded, so a reader of `CHAIN.json` has
no way to tell "40 distinct unmatched names, that's all of them" from "40 of 400". This is
squarely the ranking-then-truncating shape Hard Rule 0 names. Impact is limited today — nothing
in `src/` currently reads `CHAIN.json`'s `unmatched` field back (grep confirms only `chain.py`
itself writes/reads it; it is diagnostic, not fed into the Bradley-Terry fit or any ranking), so
this is a finding about the artifact's honesty, not about a live correctness bug. Console output
(`unmatched.most_common(8)` in `main()`) is explicitly labelled "most common," which is fine —
the persisted file's silent 40-cap with no stated total is the part that doesn't announce itself.

### MINOR — four stale numeric `silence.note()` line tags

```
line 169: silence.note("chain.py:91")
line 276: silence.note("chain.py:155")
line 283: silence.note("chain.py:161")
line 345: silence.note("chain.py:252")
```

These are old-style numeric tags (predating the newer named-tag convention this same file also
uses, e.g. `silence.note("chain.py:inv-load")`, `silence.note("chain.py:tuning")`,
`silence.note("chain.py:epoch-unprobed")`) and none of the four numbers matches its current line.
Harmless functionally (they only key a failure-count bucket in `state/failures.json`), but they
are exactly the "hardcoded line-number tags that no longer match their own line" class the audit
brief calls out, and they make `state/failures.json` counts harder to trace back to source.

### Verified correct — the new `unprobed` counter (per this batch's specific guidance)

`adjudicate_mutuals()`'s three-way split (`split`, `kept`, `unprobed`) is coherent:

```python
        try:
            ea, eb = ID.epoch_of(sa, strict=True), ID.epoch_of(sb, strict=True)
        except ID.ProbeUnavailable:
            unprobed += 1
            ...
            continue
        if ea != eb:
            ...
            split += 1
        else:
            kept += 1
```

`kept` (the count labelled "recorded as genuine disagreement" in the final print) only increments
in the `else` branch, which is reached only when *both* `epoch_of` calls succeeded and returned
equal epochs — an unprobed pair takes the `except` branch and `continue`s before either counter
in the `if/else` can fire, so it cannot inflate `kept`. `identity.epoch_of(..., strict=True)`
(read in full) correctly distinguishes "the probe never ran" (raises `ProbeUnavailable`) from
"the probe ran and found no marker" (returns `""`), and does so on both the no-transport and the
unparseable-reply paths, so a transport outage genuinely surfaces as `unprobed`, not as a false
"kept as genuine disagreement." The tally is reported: `print(f"   {split} split by epoch, {kept}
recorded as genuine disagreement" + (f", {unprobed} NOT ADJUDICATED..." if unprobed else ""))`.
This matches the docstring's claim exactly. One purely cosmetic note: `identity.py`'s own
docstring for `epoch_of` still says "`chain.py:422` is the caller that should pass it" — the
caller is now at a different line (~428) since surrounding comments grew; same stale-line-tag
class as above, in the sibling file, not actionable here since `identity.py` belongs to another
batch.

---

## endpoint.py

### MAJOR — `ENDPOINTS.json` (`_MEM`/`_load`/`_save`) is a read-once-per-process,
write-whole-thing-back cache with NO staleness check, in a file whose own multi-process write
hazard for a *different* file (`SOURCE_PAGES.json`) was fixed today. The same hazard is live here.

```python
_MEM = None

def _load():
    global _MEM
    with _LOCK:
        if _MEM is None:
            try:
                with open(CACHE, encoding="utf-8") as f:
                    _MEM = json.load(f)
            except Exception:
                ...
                _MEM = {}
        return _MEM

def _save():
    with _LOCK:
        if _MEM is None:
            return
        try:
            silence.write_json(CACHE, _MEM, indent=1, sort_keys=True)
        ...

def detect(host, force=False):
    ...
    with _LOCK:
        mem[host] = found
    _save()
    return found
```

`_MEM` is loaded from disk **once** per process and never re-read afterward; every `detect()`
call in that process mutates and re-persists that same in-memory snapshot. `_save()`'s own
docstring says: *"`ENDPOINTS.json` is written by every process that probes a host -- `detect()`
is reached from `feats.py`, `hostcheck.py` and `completeness.py`, several of them threaded"* — so
multiple, separate, concurrently-running processes are the documented normal case. Given that:
process A starts, loads `_MEM` with N hosts on disk; process B starts later, loads its own
(newer) `_MEM`; B probes host X and calls `_save()`, landing X into the file; A — still holding
its older snapshot, which never learned about X — probes host Y and calls `_save()`, landing its
own (still-N-host-plus-Y, X-less) copy over the file. X's result is silently gone. This is the
exact "m42" lost-update shape this same file documents fixing for `register()`/`SOURCE_PAGES.json`
three functions below (*"two processes registering pages for two DIFFERENT sources both read the
file, both mutate their own key in their own in-memory copy, and both land the WHOLE dict...
Nothing failed."*) — but that fix (digest-at-read-time compare-and-swap, retry-and-remerge on
staleness) was applied only to `register()`. `detect()`/`_save()` for `ENDPOINTS.json` still does
the plain whole-file overwrite the `register()` docstring describes as the bug. Cost: a probe
verdict (`MODE_API`/`MODE_RAW`/`MODE_DEAD`) earned by one process's network round trip can be
silently dropped, forcing a re-probe next run — wasted network against a pipeline `_save()`'s own
docstring says paces itself per host on purpose, and (worse) a `MODE_DEAD` verdict landed by one
process could be overwritten back to missing/absent by a stale write from another, discarding
useful negative information too.

### MINOR — dead code: `return d[source]` after an unconditional `raise`, in `register()`

```python
    silence.note("endpoint.py:register-contended")
    raise RuntimeError("SOURCE_PAGES.json changed under this writer on every one of 8 attempts, "
                       "so %r's pages were NOT recorded: %s" % (source, last_why))
    return d[source]
```

The `return` can never execute — `raise` unconditionally transfers control. Harmless (nothing
reachable references it), but it reads as a leftover from an earlier version of `register()`
that returned the merged list on success; the current success path (`if landed: return`, inside
the loop) returns `None` instead. The one caller (`scout.py:281`, `EP.register(source, kept)`)
discards the return value entirely, so nothing depends on this today — flagged as a
correctness-hygiene finding, not a live bug.

---

## hostcheck.py

### MAJOR — `_land()` writes `WIKI_HOSTS.json` (and other shared artifacts) through a FIXED
`.tmp` suffix with no compare-and-swap, and this is a *known, named, still-open* hazard per
another module's own docstring written today.

```python
def _land(path, obj, sort_keys=True, ensure_ascii=True):
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(obj, f, indent=1, sort_keys=sort_keys, ensure_ascii=ensure_ascii)
    silence.replace_retry(tmp, path)
```

This has a fixed temp name (`path + ".tmp"`, not pid/thread-qualified like `silence.write_json`
or this project's other `_mutate`-style writers), and it is a whole-file overwrite with no digest
check — the "atomic-but-blind-to-another-writer's-read-modify-write" shape. `F.HOSTS` (i.e.
`data/WIKI_HOSTS.json`) is written through this exact function from **two call sites in this
file** — `sweep()`'s repair path (`_land(F.HOSTS, hosts)`) and `adopt()` (`_land(F.HOSTS, hosts)`)
— and `scout.py` is a **third, separate process** that also writes `WIKI_HOSTS.json`. `scout.py`
does NOT use `_land` for this file any more; its own `_mutate()` docstring (written the same day,
order `d3313adbf641`) says explicitly:

> *"SCOUT_ATTEMPTS.json, WIKI_HOSTS.json and SCOUT_BLOCKED.json were each read, mutated and
> written back here with no lock and no staleness check -- three whole-file read-modify-writes on
> artifacts at least one OTHER process also writes. `hostcheck.adopt()` writes WIKI_HOSTS.json
> from a separate process; a lost update there silently un-adopts a host."*

and `scout.py`'s `_land()` docstring adds:

> *"`hostcheck.py`'s own `_land` still builds the same fixed name for the files it writes -- there
> is no reason for this one to keep the hazard `silence.write_json` exists to end just because
> nothing currently collides with it."*

So the fix pattern (`_mutate`, digest-at-read compare-and-swap) was applied to `scout.py`'s side
of this exact three-writer collision on `WIKI_HOSTS.json` today, and left unapplied on
`hostcheck.py`'s side — despite `hostcheck.py`'s own comment at the `sweep()` call site (line
~624) asserting *"tmp + replace_retry, the pattern the rest of the tree already uses"*, which
reads as settled but, per `scout.py`'s newer docstring, is not the pattern the rest of the tree
now uses for this specific file. Practical effect: `hostcheck.py --repair`/`--adopt` running
concurrently with `scout.py`'s host-registration path (or with each other, or with a second
`hostcheck.py` invocation) can silently drop one side's host repointing/adoption — exactly the
"un-adopts a host" failure `scout.py`'s own comment names.

### MINOR — `null_rate()`'s cache is keyed by `host` only; the `exclude` parameter (the source
whose own names must be kept out of the baseline sample) is honoured only for whichever source
happens to trigger the first computation for that host, then silently ignored for every other
source scored against that host for the rest of the process's life.

```python
def null_rate(host, by=None, exclude=None, sample=40):
    with _NULL_LOCK:
        if host in _NULL_CACHE:
            return _NULL_CACHE[host]
    foreign = []
    for src, names in (by or {}).items():
        if src == exclude:
            continue
        foreign.extend(names[:3])
    ...
    with _NULL_LOCK:
        _NULL_CACHE[host] = rate
    return rate
```

`score()` calls `null_rate(host, by=by, exclude=source)` once per (host, source) pair it judges.
Universal candidate hosts (`en.wikipedia.org`, `www.dandwiki.com` — explicitly added to every
source's candidate list by `candidates()`) get scored against many different sources in one
`adopt()`/`sweep(--repair)` run. The very first source that causes a given host's baseline to be
computed permanently "bakes in" that source's exclusion; every subsequent source scored against
that same host reuses the cached rate, computed from a foreign sample that (for all sources after
the first) does **not** exclude the current source's own names. Since each source contributes at
most `names[:3]` to the pool, and the pool is drawn from every catalogued source, the practical
contamination per call is small, but it is systematic and not what `exclude` promises: after the
cache warms, the "baseline for names this host has no reason to hold" for source B on a
much-probed host may include up to 3 of B's own names. This biases `lift = rate - base` downward
for exactly the case `score()`'s own docstring warns about (rejecting a real match because the
baseline looks too generous). Not flagged as MAJOR because the dilution (3 names out of a
pool drawn from potentially hundreds of sources, further downsampled to `sample=40` via a strided
slice) likely keeps the numeric effect small in most cases, but the cache key is demonstrably
wrong for what the function's own parameter is supposed to guarantee.

### Verified correct / read, nothing found

- `probe()`'s `[:PROBE]` (40) and `relevance()`'s `[:sample]` (12) are statistical-sample caps
  for a fitness *measurement*, not roster truncations of a catalogue — the function's whole
  purpose is "ask a bounded sample, compare rate to a baseline," so this is not the Hard Rule 0
  shape (a listing silently shortened) and is not flagged.
- `GOOD`, `DEAD`, `ABOUT`, `MIN_PROBE`, `LIFT_MIN`, `GOOD_LIFT`, `ABOUT_VETO_ABOVE` are all live —
  checked each against actual call sites, none is dead/unread.
- `roster_audit()`'s `one()` early-return-for-empty-roster comment ("this sat AFTER the
  seen<MIN_PROBE return for a while -- unreachable") describes a bug already fixed in the current
  code (the check is now first); re-verified against the live source, current ordering is correct.
- `purge()`'s docstring section on the removed "independently rejected" check ("the check was
  loaded and unused") describes history, not a live defect; re-verified the current function has
  no such dead check.
- `sweep()`'s repair-candidate loop ranks candidates by raw `rate` rather than `lift` (unlike
  `adopt()`, which explicitly fixed a rate/lift unit-mixing bug and now ranks by lift). This is
  NOT the same bug: `sweep()`'s `ok = p["verdict"] in ("holds", "partial")` gate is itself
  lift-derived (via `score()`), so `rate` is only used as a secondary tie-break among candidates
  that already passed the lift-based verdict test. Defensible design, not flagged.

---

## worldseed.py

### MINOR — confirmed unreachable vocabulary entry: `"primitive"` in the `size` lookup can never
be selected.

```python
TECH = [
    ("spacefaring", ...), ("industrial", ...), ("magical", ...), ("medieval", ...),
]
...
        "size": {"spacefaring": 90, "industrial": 70, "magical": 55,
                 "medieval": 45, "primitive": 35}.get(f["tech"], 50),
```

`f["tech"]` comes from `features()` → `_first(TECH, ...)`, which can only return one of the four
names actually in the `TECH` table (via either an attested regex match or the seeded fallback,
which also only ever indexes into `TECH`). `"primitive"` is not one of those four names and is
therefore an unreachable branch of the `size` dict — `.get(f["tech"], 50)` will use the `50`
default in every case that isn't spacefaring/industrial/magical/medieval, never the `35` written
for "primitive." This is exactly the "unreachable era vocabulary" this batch's guidance said to
verify before repeating — verified by reading the `TECH` table and `_first()`/`features()` in
full; the fourth-entry set really does not include "primitive," so the claim holds.

By contrast, checked and NOT a defect: `CULTURE_SET`'s six keys (classical/guttural/liquid/
sibilant/compact/long) were checked against the actual `data/ONOMASTICON.json` register values on
disk — all six occur in the live data (`Counter({'long': 58, 'compact': 43, 'sibilant': 39,
'guttural': 34, 'classical': 32, 'liquid': 17})`), so `CULTURE_SET` is fully reachable; and
`CONDITION`'s three values (ruined/wartorn/thriving) are all reachable via regex match or the
uniform 1-of-3 seeded fallback — "thriving" has no special-cased numeric effect downstream
(`states` only branches on "wartorn"/"ruined"), but it IS recorded in `opt["features"]` and the
persisted `WORLDSEEDS.json` payload, so it is not dead, just not load-bearing for the `states`
formula. `TEMPLATE` and `CLIMATE_BAND` keys match their source tables exactly (6 and 6). Not
flagged.

### Verified correct — the `build_all()` write path

`main()`'s `--write` branch correctly checks the `silence.write_json` return value
(`if silence.write_json(path, payload, ...): print("wrote..."); else: print("WRITE DENIED...")`)
— this is the correct pattern, contrast with the discarded-verdict bug found in `halo.py` and
`catalogue_models.py` below.

---

## catalogue_models.py

### MAJOR — discarded write verdict: `sweep()` never checks whether `PROVIDER_MODELS.json`
actually landed before printing success.

```python
    # ATOMIC: standards.py polls PROVIDER_MODELS.json on its own cycle. 2026-08-25.
    silence.write_json(OUT, payload, indent=1, sort_keys=True)
    print(f"\n-> {OUT}")
    return payload
```

`silence.write_json()` returns `True`/`False` and — per its own docstring — "Never raises on a
denied replace... the caller's write lands next round," i.e. the caller is required to check the
return value if it wants to know whether the write happened. Here it is discarded, and
`print(f"\n-> {OUT}")` runs unconditionally, telling the operator the file was written whether or
not the `os.replace` actually landed. `standards.py` is documented (in the very comment above
this line) to poll this file on its own cycle — a denied write here means `standards.py` silently
keeps reading the previous cycle's provider/model data while the console output claims a fresh
report was produced. This is catalogue item #5 ("a discarded verdict") verbatim. Note this is not
unique to this file: the same exact pattern (`silence.write_json(OUT, out, ...)` immediately
followed by an unconditional `print("-> " + OUT)`, no `if` check) also exists in `wh40k.py:271`
and `zfighters.py:486`, and now `halo.py:194` (below) — flagging as a recurring pattern across
this family of "assay roster" modules, all outside today's edited set except `halo.py`.

### Verified correct / read, nothing found

- The two previously-documented Hard Rule 0 caps in this file (`[:8]` on `available_sample`, and
  a console `[:10]` on the "current alternatives" listing) are both confirmed FIXED in the
  current source — `available_sample": list(r["models"])` and `", ".join(r["models"])` are both
  full, uncapped lists, matching the comments describing the run #26 / run #33 fixes. Re-verified
  directly rather than trusted from the comment.
- `ask_provider()`'s `/v1` double-prefix guard (`if base.endswith("/v1") and
  path.startswith("/v1"): continue`) is correct: it skips only the `/v1/models` candidate when
  the base already ends in `/v1`, leaving `/models` to be tried against that base, which is the
  intended non-doubled URL.
- The four-outcome contract (`LISTED`/`EMPTY_LIST`/`UNREACHABLE`/`UNCONFIGURED`) is exhaustively
  returned on every path through `ask_provider()`; no path falls through without setting one.
- `unverified`/`verified`/`stale` denominators are reported together as the file's own comments
  intend (the "N stale over M verified of T total" fix), and this was re-checked against the
  printed lines, not just the comment claiming it.

---

## tells.py

Read, nothing MAJOR or MINOR found. Ran the module directly (`python src/tells.py`) to confirm it
actually executes and self-checks without error — no `_BAD_CHARS` trip, 138 total patterns
compiled cleanly, the demo passage correctly fires 8 distinct tells including one from each of
lexical/structural/discourse.

Specifically checked and confirmed NOT a bug (the alternation-precedence question a reviewer
would reasonably raise):

```python
"not merely X but Y": r"\bnot merely\b|\bnot simply\b|\bnot just\b.{0,40}\bbut\b",
```

`|` binds the whole alternatives, so `.{0,40}\bbut\b` applies only to the third branch
("not just"), not to "not merely"/"not simply". This is documented as deliberate in the comment
directly above (asymmetric on purpose: "not merely"/"not simply" are marked enough alone; "not
just" is ordinary English and needs the "...but" completion to avoid false positives on "he did
not just leave"). Verified against the live regex and the demo self-check, which does fire on
"not merely" with no "but" nearby. Correct as written.

Also checked `_anchor()`'s `pat[4:]` slicing against every `^\s*`-prefixed pattern in
`STRUCTURAL`/`DISCOURSE` (9 of them) — all nine literally start with the 4-character string
`^\s*`, so the slice is safe for every current entry. Would silently misfire only if a future
entry used a different-length anchor (e.g. `^\s+`) without updating `_anchor()`; flagging as a
QUESTION for future editors of this list, not a present defect.

QUESTION (not a defect): the `"rule of three"` pattern —
`r"\b\w+, \w+,? and \w+ (?:alike|all|together)\b"` — is much narrower than its label implies. An
ordinary "wise, powerful, and terrible"-shaped triple (extremely common in both human and machine
prose) will NOT match; only a triple followed by "alike/all/together" fires. This may be
deliberate narrowing to avoid flooding on completely ordinary lists (plausible, given the file's
general care about false-positive rates), but the label reads as if it catches the classic
rule-of-three tell broadly. Worth a decision, not a fix.

---

## halo.py

### MAJOR — discarded write verdict, same shape as `catalogue_models.py` above.

```python
    # ATOMIC -- the m100 tail, 2026-08-25.
    silence.write_json(OUT, out, indent=1, ensure_ascii=False)
    print("")
    print("-> " + OUT)
    return 0
```

`silence.write_json()`'s return value is discarded; `main()` unconditionally prints `-> {OUT}` as
though `data/HALO_ASSAYS.json` landed, even on a denied replace. Same pattern, confirmed also
present verbatim in `wh40k.py:271` and `zfighters.py:486` (sibling "assay roster" modules, not in
this batch) — this looks like a copy-pasted module skeleton across at least three files, all
carrying the same discarded-verdict defect.

### Verified correct / read, nothing else found

- `ROSTER`'s three entries (`The Precursors`, `The Gravemind`, `The Ur-Didact`) each score exactly
  the 11 axes `assay.WEIGHTS` actually weights (`ruin, continuity, celerity, reach, transgression,
  sustain, vector, volition, acumen, discernment, suasion` — checked against `assay.py`'s
  `CHARTER_PHYSICAL_WEIGHTS` (8 keys) + `FACULTY_AXES` (3 keys) = 11, matching exactly). No axis
  is missing and none is extra, so nothing here is silently excluded from or padding the
  composite.
- `attestation="Transcribed"` is a real, valid key in `assay.SIGMA_BY_ATTESTATION` (checked
  against `_RAW_SIGMA` in `assay.py`), not a typo'd/unrecognized grade that would silently fall
  back to the widest (`Disputed`) dispersion.
- `compute()`'s per-axis provenance tagging (`"[" + v[2] + "] " + v[1]`) matches the docstring's
  claim that this replaced a uniform "[wiki]" stamp — spot-checked against the three axes the
  docstring names as non-quoting (Precursors' celerity, Gravemind's celerity, Ur-Didact's
  celerity) and all three are tagged `"canon"` in the actual `ROSTER` data, not `"wiki"`, matching
  the fix as described.

---

## Modules I could NOT read / anything skipped

None. All eight assigned modules were read in full and reasoned about; none was skipped or read
only from docstring/name.
