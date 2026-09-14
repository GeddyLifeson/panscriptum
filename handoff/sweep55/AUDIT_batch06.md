# SWEEP run55 — AUDIT batch 06

Modules read in full, every line: `standards.py` (2,467), `codewatch.py` (1,027), `estate.py` (723),
`policy.py` (574), `scope.py` (473), `cosmography.py` (375), `physics.py` (312), `halo.py` (219),
`cachekey.py` (213).

Read-only throughout. Nothing under `src/`, `data/`, `state/` or any ledger was written. Two
offline scratch scripts were run (in the session scratchpad, not in the tree) to drive
`estate.charter()`'s own regexes and `standards.py`'s "every declared floor is measured" logic as
pure string work against the live files — neither imports the module under test and neither writes
anywhere. Live data was read (`data/HOSTS.json` via `cachekey.host_dir`, `state/failures.json`,
`state/CODEWATCH.json`, `state/codewatch_poll/`) to check claims against reality.

---

## scope.py

**How read:** every line, then the two specific questions the coordinator asked. Cross-checked
`drill.py:367-386`, `drill.py:544-583`, `drill.py:6960-7015`, `health.py:60-165` and
`silence.note` (871-903) — all four are OUTSIDE this batch and are named here rather than assumed.

### ANSWER TO THE COORDINATOR'S QUESTION — yes, a caller can still manufacture the signal

`scope.mutate` has five `silence.note` refusal sites: `mutate-unreadable` (345),
`mutate-nondict` (351), `mutate-tmp` (363), `mutate-tmp-cleanup` (372), `mutate-contended` (374).
The 2026-09-09 halt came from the first two.

**Nothing in `scope.py` changed, and nothing in `scope.py` can tell the two cases apart.** The
notes are unconditional and keyed by a literal site string. `mutate()` takes a `path=` argument
precisely so a caller can sandbox the file (docstring 326-329), but the note sites do not consult
`path` — so a refusal on a scratch temp file writes the byte-identical
`silent:scope.py:mutate-unreadable` row into `state/failures.json` as a refusal on the real
`data/SCOPE.json`. The whole of the fix is caller-side: `drill._deliberately_failing`
(drill.py:544) monkey-patches `health.record` to a no-op around the wrapped call.

Three consequences worth the coordinator's attention:

1. **Any new caller re-opens it.** `drill.net`'s own docstring (drill.py:374-385) says the
   discipline "HAS BEEN FORGOTTEN AT LEAST THREE TIMES, and the last one halted the library".
   The witness is detection, not prevention, and it costs a halt each time.
2. **`health.is_selftest` cannot help here.** It routes a row to the self-test ledger when the
   composed key or an explicit `subject=` matches `__drill[A-Za-z0-9_]*__` (health.py:97-101).
   `silence.note` composes the key as `silent:<site>:<ExcType>` and passes no `subject`, so a
   scope-mutate note can never be routed. The two mechanisms do not overlap.
3. **Even in production the row is evidence-free.** It does not say which file was refused, so a
   person reading the ledger cannot tell a sandbox refusal from a real corrupt SCOPE.json. The
   `why` string that names the basename is returned to the caller and never recorded.

Filed below as a MINOR because the live drill is correctly wrapped today; the structural hazard is
unchanged.

### MINOR — a sandbox refusal in `mutate` is indistinguishable, in the ledger, from a real one
**Where:** src/scope.py:344-352 (with 297-333 for the `path` parameter)
**What:** `silence.note("scope.py:mutate-unreadable")` / `("scope.py:mutate-nondict")` fire
unconditionally on the refusal paths, with no reference to `path`.
**Why it is wrong:** `mutate(apply, path=<scratch>)` is the supported way to drive this function
against a throwaway file, and doing so writes the same operational-ledger class that a genuine
unreadable `data/SCOPE.json` writes. The only thing standing between that and another library halt
is a caller remembering to wrap the call in `drill._deliberately_failing`.
**Confidence:** read `scope.mutate` line by line, then the breach account in `drill.py:6987-7012`
and the wrapper at `drill.py:544-583`. `drill.py` and `health.py` are outside this batch.

### MINOR — a failed temp-file stage leaks the temp file
**Where:** src/scope.py:358-364
**What:** the `except` around `json.dump` into `tmp` notes and returns `False` without removing
`tmp`. Every other exit from the attempt loop removes it (369-372).
**Why it is wrong:** a partially written `SCOPE.json.<pid>.<tid>.<n>.tmp` is left beside the real
table for ever — the shape `estate.inspect()` then has to classify, and the exact litter the
pid/thread naming scheme exists to keep bounded.
**Confidence:** read; the only `os.remove(tmp)` in the function is on the not-landed path.

### INFO — `build()` performs a full read-modify-write even when it probed nothing
**Where:** src/scope.py:291
**What:** `mutate(lambda cache: cache.update(probed))` is called unconditionally, including when
`todo` was empty and `probed == {}`.
**Why it matters:** a no-op `--build` still takes the digest, re-reads, re-stages and re-lands the
whole table, and can print "SCOPE.json was NOT updated: …" for a write that had nothing to say.
**Confidence:** read.

### INFO — `ceiling_for` is marked dead-and-kept; saw the marking, moved on
**Where:** src/scope.py:378-393. The owner ruling of 2026-09-08 ("mark and keep, delete nothing")
is cited in place. No action.

Also checked and found sound: `scope_for`'s `ProbeUnread` gate fails closed when `oc` is never
populated (`oc.get("ok")` None → falsy, `why` None → not in `_CLEAN_NEGATIVE` → raises); the
`best` loop takes the HIGHEST tier clearing `MIN_MENTIONS` because `TIERS` is ascending and the
loop latches the last match; `_stamp` reads unstamped and `None` records as 0; `main()` propagates
the denied-write verdict to rc.

---

## codewatch.py

**How read:** every line, then the "last polled Ns ago" column specifically, driven against the
live `state/codewatch_poll/` stamps and `state/CODEWATCH.json`.

### The NOT KNOWN case is honest — verified against live state
`last_polled()` (854-866) returns `None` for: no stamp file, an unparseable one, a document with
no `at`, and an `at` that is not a number. `json.JSONDecodeError` and `UnicodeDecodeError` are both
`ValueError` subclasses and are caught. `_stamp_poll` and `last_polled` build the filename with the
identical `re.sub(r"[^A-Za-z0-9_.-]", "_", str(who))`, so they cannot disagree. The `who` strings
at all six live call sites (`dashboard`, `foreman`, `overnight`, `overwatch`, `pipeline`,
`publish`, `read`) match the basenames `main()` derives from `overnight.ALL_JOBS`, so the
normalisation at 958-960 is correct. Live check: `read` has no stamp file and no ledger key, and
therefore renders as "no source-change restart ever recorded (covered, budget 4); last poll NOT
KNOWN" — which is exactly the run #48 shape the column was added for, rendered honestly.

### MINOR — a future-dated stamp renders as the healthiest possible reading, not as NOT KNOWN
**Where:** src/codewatch.py:864
**What:** `return max(0.0, time.time() - float(at)) if isinstance(at, (int, float)) else None`
**Why it is wrong:** `max(0.0, …)` converts a stamp in the future into `0.0`, and `main()` renders
`0.0` as "last polled 0s ago" — the single most reassuring value the column can print. A clock
correction, a stamp written under a different clock, or a corrupted-but-numeric `at` therefore
reads as a daemon polling continuously, including for a daemon that is dead. The docstring two
lines above insists `None` is "a THIRD answer and the report must render it as one"; this is the
one bad input that is routed to the best answer instead of the third one.
**Confidence:** read the clamp and both render branches (972-980). Not reproduced against a live
skewed clock.

### MINOR — the "LONG" threshold sits below a covered job's own poll cadence, so a healthy foreman is labelled LONG every cycle
**Where:** src/codewatch.py:975 (`elif age > 10 * STABLE_SECONDS:` → 1800 s)
**What:** any job whose last poll is more than 30 minutes old is printed with "— LONG".
**Why it is wrong:** `overnight.STANDING` runs `foreman.py --go --patch --loop 30`, and
`foreman.main()` polls then sleeps 30 minutes then runs `round_once()` before polling again — so
foreman's inter-poll gap is *always* greater than 1800 s, by the duration of one round. It is
therefore flagged LONG for part of every single cycle while nothing at all is wrong. Measured
against live state at the time of this audit: `state/codewatch_poll/foreman.json` stamped 22:08
against an `overnight.json` stamp of 22:48 → 40 minutes → "LONG". The same reading correctly flags
`overwatch` (20:18, ~150 min, against a `--loop 20`), so the column is not useless — the threshold
is simply set under the cadence of one of the jobs it grades.
**Confidence:** read the threshold, read `overnight.STANDING` (overnight.py:985-995, outside this
batch) and `foreman.main()`'s loop order (foreman.py:1962-1988, outside this batch), then compared
the live stamp mtimes.

### INFO — 90 seconds is rendered as "2 min"
**Where:** src/codewatch.py:977-978. `elif age >= 90: "last polled %.0f min ago" % (age / 60.0)`
rounds 90 s to "2 min". Harmless, but the switchover point is the one place the two units disagree
most.

### INFO — the poll stamp records a `pid` that nothing reads
**Where:** src/codewatch.py:846 writes `{"job", "at", "pid"}`; `last_polled` reads only `at` and
`main()` never opens the file. The one fact that would separate "polled 40 min ago and is still
alive" from "polled 40 min ago and died" is collected and dropped.

### INFO — `fingerprint()` and `quiet_seconds()` see only `*.py` directly under `src/`
**Where:** src/codewatch.py:238 and 285 (`os.listdir`, not `os.walk`). `src/deprecated/` holds one
`.py` file today, so a change to it would not trip any daemon's staleness check. Currently
harmless; noted because both functions are the whole basis of the rc=17 contract.

Also checked and found sound: `_ledger_lock`'s `O_CREAT|O_EXCL` + stale-steal, and the deliberate
"proceed unlocked rather than lose the record" fallthrough; `_take_locked`'s fail-closed on a
denied `write_json`; `_claim_restart_slot`'s check-and-take under one lock; `stale()`'s two clocks
and the mtime-vs-stamp corroboration at 707 (`(time.time() - quiet) <= started` correctly discards
mtime evidence older than process start); `runs_script`'s three named non-run shapes;
`twins()`'s additive `exclude_pid`; `coverage()`'s fail-loud UNREADABLE row.

---

## standards.py

**How read:** every line, in three passes. The "every declared floor is measured" self-check was
re-implemented offline and run against the live file.

### Self-check verified, offline: no dead floors
28 constants match the declared-floor pattern and every one appears at least twice in
comment-stripped code, so `every declared floor is measured` currently reports "all measured"
honestly. Six sit at exactly two occurrences (`MAX_CORRUPT_FILES`, `MAX_STALE_MODEL_IDS`,
`MIN_CALLS_PER_HOUR`, `MIN_CATALOGUE_COVERAGE`, `MIN_DISK_GB`, `MIN_LIVE_BUCKETS`) and in every one
of the six the second occurrence is a real `holds` expression, not a display string.

### MINOR — `main() --json` runs `check()` twice, under the comment that says it must not
**Where:** src/standards.py:2440-2451
**What:** `state = D.state()`, then `bad = work_orders(state)` (which calls `check(state)`), then
`print(json.dumps(check(state), indent=1))` — a second full `check()`.
**Why it is wrong:** the comment at 2437-2439 says both are given one state precisely because
"asking both without one would run every live probe twice"; sharing the state fixes the
`dashboard.state()` half and leaves the probe half exactly as it was. `check()` is documented
(754-759) as NOT a pure read: it spawns `tasklist`, opens a live TCP socket, can fire a real
generation with a 300 s timeout, walks `data/readfeats`, runs a 60 s `Get-CimInstance`, and reads
nine JSON files. The memos blunt some of that, but `duplicates`, `job-advance`, the file reads and
the `JOB_WATCH`/`READ_WATCH` stamp writes all run twice. Worse, the exit code comes from pass one
and the printed JSON from pass two, so `--json` can print a green row and exit 1 (or the reverse).
**Confidence:** read; `work_orders()` at 2373-2377 calls `check(state)` directly.

### MINOR — the first fifteen standards are computed outside any `try`, so one malformed state key deletes the whole pass
**Where:** src/standards.py:866-867, 1111 (and everything from 800 to 1117)
**What:** `calls = sum(b["calls"] for b in tp.get("buckets", []))`,
`errs = sum(b["calls"] - b["ok"] for …)` and `missing = [p["name"] for p in ph if not p["built"]]`
use subscripts, not `.get`, and sit outside every handler; `check()` itself has no outer `try`.
**Why it is wrong:** a dashboard-state bucket row missing `calls`/`ok`, or a phase row missing
`built`, raises `KeyError` out of `check()` and takes all ~46 standards with it — the total
opposite of the `_dropped` discipline the rest of the function applies to exactly this class of
input fault ("a vanished standard is not a met one"). The failure is loud rather than silent, which
is why this is MINOR and not MAJOR, but the module's own remedy for an unreadable input is a
`_dropped` row, not a traceback out of the instrument panel's poll loop.
**Confidence:** read; confirmed there is no outer `try` in `check()`.

### MINOR — `feats per chunk` turns an unparseable detail string into a red, while the standard forty lines down turns the same failure into a labelled reading
**Where:** src/standards.py:963-975 against src/standards.py:1306-1319
**What:** the first parses `det.split("·")` and takes `int(join(digits))`, defaulting `feats = 0`
when no segment contains "feats"; the second parses the same `det` with
`_re.search(r"([\d,]+) feats", det)` and, on failure, sets `why = "the reader's progress line did
not parse"` and reports UNMEASURED.
**Why it is wrong:** two parsers for one string in one function is the drift shape this file
complains about elsewhere ("two hand-kept spellings of one rule"), and the two disagree about what
a parse failure MEANS: one publishes `0.00` against a floor of `0.5` — a medium breach describing a
reader that may be perfectly healthy — and the other says it could not measure. Today
`dashboard.py:248` emits `"{done}/{total} entities · {feats} feats · {rate} chunks/s"` and both
parsers agree, so this is latent; it becomes live the first time that format changes.
**Confidence:** read both; checked `dashboard._read_row`'s detail format and `_num()` (which
returns an int, so the thousands separator is the only formatting either parser has to survive).

### INFO — `report()` repeats group headings
**Where:** src/standards.py:2398-2402. The heading is emitted whenever `r["group"]` differs from
the previous row, and `out` is built in source order with groups interleaved (`pool` appears at the
top, again at 1839, again at 2308; `machine` twice). The printed report therefore shows POOL three
times rather than one POOL section.

### INFO — `_wrap` emits an empty first line for an over-width first word
**Where:** src/standards.py:2380-2390. With `line == ""`, `len(line) + len(w) + 1 > width` is true
for a long first word and `out.append("")` runs. `codewatch._wrap` (codewatch.py:1016) guards the
same expression with `if line and …`.

### INFO — the floor self-check credits display-only uses
**Where:** src/standards.py:2342-2343. A constant is "measured" on a second word-bounded appearance
in comment-stripped code, so a floor used only in the `floor=` display argument and never in the
`holds` expression would pass. The block's own comment already concedes the class ("a source-grep
cannot tell a used constant from an unreachable one"); recorded so the limit is not re-discovered.
None of the 28 is in that state today.

Also checked and found sound: `read_progress_verdict`'s tri-state and its persisted stamp;
`job_stamp`'s carry-forward; `charter_regression_verdict`'s in-progress branch (a pass with no `at`
and `complete` false can never hold); `provider_pool_denominator`'s two shapes; the UNMEASURED
readings on coverage/settled/host-coverage/catalogue/reference-assays/provider-models, each of
which breaches rather than passing; `resident_context`'s by-identity lookup and `model_matches`'s
`:latest` fold; the `_dropped` aggregate at the foot. `sum(ledger.values())` at 1177 was checked
against the live `state/failures.json`, which is a flat dict of 25 int counters — the arithmetic is
valid on the real file.

---

## estate.py

**How read:** every line, then `charter()`'s table parsing driven offline against the live
`00_MASTER_CHARTER.md`.

### `charter()` verified against the live document
The 2026-09-08 rewrite from string-presence to table-reading is real and the four errata all fire
for the right reason. Driving the module's own regexes offline: 11 band rows parsed with no
duplicate keys (so `dict()` cannot pick up a stray row from another table), 17 ladder rungs, the
`set(band_rows) != {M0…M10} or len(rung_rows) != 17` gate passes, `threatens` contains none of
`supercluster`/`filament`/`void`/`hyperverse`, and `low` is `"a village; a city or nation; a
continent"` against rung words that include no match — so all four errata are genuine findings of
the document, not artefacts.

### MINOR — `external()`'s outer handler publishes "OLLAMA UNREACHABLE" for faults that are not the daemon's
**Where:** src/estate.py:631-698
**What:** the outer `try` opens at the Ollama probe (631) and closes at 694 with
`note("OLLAMA UNREACHABLE", type(e).__name__, bad=True)` — but it also spans the whole config.yaml
block (645-693) and the `names = [m.get("name") for m in tags.get("models", [])]` decode at 635.
**Why it is wrong:** this is verbatim the mis-routing the inner "FOUR CONDITIONS, FOUR ROWS" split
(637-644) was made to prevent, one level out. An `/api/tags` payload whose `models` list holds a
string rather than an object raises `AttributeError` and is published as an unreachable daemon; so
would an `OSError` out of `os.path.exists(cfg_path)`. The row is `bad=True` and
`allsweep.estate_faults()` gates on it, so the sweep reddens and the reader is sent to restart a
daemon that answered fine.
**Confidence:** read the handler's span. The `tags` shape fault was not reproduced.

### INFO — the zero-bytes branch does not exempt the kept-damaged family
**Where:** src/estate.py:218-229 against KEPT_DAMAGED_EXT at 86-90
**What:** the zero-bytes exemption is keyed on `TRANSIENT_EXT` only, so a zero-byte `.corrupt`
keepsake would be reported `error: "zero bytes"`.
**Why it matters:** `KEPT_DAMAGED_EXT` exists because "Reporting it as damaged would be a
permanently red row that no repair can ever clear" — and a preserved zero-byte corruption is a
plausible thing to preserve. Measured: both live `.corrupt` files (`state/failures.json.corrupt`
140 bytes, `state/failure_samples.json.corrupt` 4,579 bytes) are non-empty, so this is latent.

Also checked and found sound: `_effective_ext`'s marker-peeling (derived, not enumerated);
`inspect()`'s stat retry with GONE vs UNREADABLE named apart; the `.jsonl` line-at-a-time parse;
`_brief`'s cut marker; `artifacts()`'s discovered roots; `written()`'s always-emitted rows and its
TOCTOU-guarded `getsize`; `terminal()`'s husk test; every `note(..., bad=True)` grading.

---

## policy.py

**How read:** every line, plus the three rule tables checked argument-by-argument against `OPS`,
`TYPES` and `ARG_REQUIRED`.

### MINOR — a malformed rule is filed as an unreadable DOCUMENT at both sweep call sites
**Where:** src/policy.py:352-364 and src/policy.py:413-427 (against check_rule's own comment at
161-165)
**What:** `check_rule` raises `BadRule` for a missing field, an unknown op, a bad `is_type` arg, a
malformed `in_range` arg or a wrong-typed arg for the other seven ops. `evaluate()` propagates it.
Both sweeps call `evaluate()` inside `except Exception as e:` handlers that append to `unreadable` /
return the unreadable tuple.
**Why it is wrong:** `check_rule`'s own comment says the refusal exists so "a malformed rule
reported as a failing document … sends the reader to the wrong place entirely" — and at these two
call sites a rule-table typo is reported as a corrupt corpus: one bad `EVIDENCE_RULES` entry would
print `UNREAD <file> BadRule: …` for all ~255,000 cache files, scope `evidence_unreadable` to the
same number, and exit 1 under "a record could not be read". The refusal is designed correctly and
then reclassified by its callers. Latent — all three tables pass correct args today, which the
file's own comments say is exactly why it is "a landmine for the next table".
**Confidence:** read `check_rule`, `evaluate` and both handlers; no test run.

### MINOR — an empty or vanished corpus is a clean pass
**Where:** src/policy.py:350-351, 408-411, 550-570
**What:** `all_records = sorted(glob.glob(data/records/*.json))` and
`all_feats = sorted(glob.glob(data/feats/*/*.json))` return `[]` for a missing directory exactly as
for an empty one. With both empty: `evals == []`, `failed == []`, `unreadable == []`,
`ev_unreadable == []` → `report()` lands → `return 0`, printed as "scope: records 0 of 0, coverage
rows 0 of 0" and "evidence cache: 0 of 0 file(s) swept … 0 clean, 0 with a finding, 0 unreadable".
**Why it is wrong:** this module's opening thesis is that "a rule that passed because it looked at
`None` is … visible in the report as a rule that looked at `None`", and its `--limit` banner exists
because "a window nobody can see the far side of reads exactly like a complete list". A
mis-pathed or renamed `data/` is the widest such window there is and it produces rc 0. The twin
check in `standards.py:1231` takes the other choice for the same directory
(`if not os.path.isdir(_readfeats): raise FileNotFoundError`) with the note that glob "returns `[]`
for a directory that is not there exactly as it does for an empty one" — the identical hazard,
already diagnosed in another file, still open here.
**Confidence:** read; live counts are 216 records and 143 feats host directories, so this is
latent.

### INFO — the rule table is re-validated once per document
**Where:** src/policy.py:154-179 inside `check_rule`, called for every rule of every one of
~255,000 files. Correctness is unaffected; it is roughly 765,000 redundant validations per sweep.

Also checked and found sound: `resolve`'s separate `found`; `_observed`'s declared cut;
`OPS["nonempty"]`'s `hasattr(v, "__len__")` (a number in a name field now FAILS rather than
ERRORS); the `absent`-only vacuous exemption and the explicit refusal to extend it to
`not_matches`; `report()`'s gated landed verdict; the three exit codes (1 for failures, 1 for
unreadable inputs, 2 for a report that did not land); `coverage.cited_nonneg`'s honest rename.

---

## cachekey.py

**How read:** every line, then all call sites of `load` / `write_path` / `owns` across the tree, and
the live `data/HOSTS.json` fold measured with the module's own `host_dir`.

### MAJOR — `load()` treats ANY read failure as corruption, and both production `on_corrupt` handlers DELETE the file
**Where:** src/cachekey.py:137-144, with `feats.evidence_for._corrupt` (feats.py:2048-2056) and
`read.read_entity._corrupt` (read.py:808-817)
**What:**
```python
        try:
            with open(fp, encoding="utf-8") as f:
                doc = json.load(f)
        except Exception:
            # A truncated file must be re-earned, never allowed to masquerade as evidence.
            if on_corrupt:
                on_corrupt(fp)
            continue
```
The handler spans `open()` as well as `json.load()`, so `OSError`/`PermissionError` — a file
briefly inaccessible while a concurrent writer's `os.replace` lands on it, a permissions fault, a
transient share violation — reaches `on_corrupt`. Both live handlers call `os.remove(fp)`.
**Why it is wrong:** the comment, and `read.py`'s handler comment ("a cache that will not parse is
deleted and re-earned"), both scope the deletion to a file that will not PARSE. The code scopes it
to a file that will not READ. On this tree — thirteen concurrent writers, every cache landed
through `silence.write_json`'s tmp+replace — a transient `open()` failure therefore deletes a
perfectly good evidence file, and the entity is re-mined against a Fandom edge that has IP-banned
this machine once. The note is written (`feats.py:corrupt-cache` / `read.py:corrupt-cache`), so it
is not silent, but the delete is taken on a signal that is not the one the comment names.
**Confidence:** read `cachekey.load` and both `_corrupt` handlers. I did NOT reproduce an
`OSError` here, and the current `state/failures.json` window carries no `corrupt-cache` rows — so
this is a documented-contract-versus-code mismatch with a destructive consequence, not an observed
incident. `feats.py` and `read.py` are outside this batch.

### INFO — the disambiguating suffix digests the NAME only, so it cannot separate hosts
**Where:** src/cachekey.py:77-89
**What:** `_suffix(name)` is `sha1(name)`, and `disambiguated_path` is
`name_stem(name) + "__" + _suffix(name)`. `owns()` (105-125) now also compares `host`, and
`host_dir()` applies the same lossy sanitise-and-cap that produced the founding name collision.
**Why it matters:** if three or more distinct host strings fold onto one `host_dir()` and hold an
entity of the same name, one takes the natural path and the other two contend for the SAME
suffixed path — each failing `owns()` on the other's file, each re-mining on every pass, which is
the perpetual re-mine the suffix exists to prevent. Measured against the live table with the
module's own function: 141 distinct hosts, **0** `host_dir` collisions today — but
`doc:arcanum-worlds-odyssey-of-the-dragonlords` already sanitises to exactly 40 characters, i.e. it
sits precisely at `HOST_CAP`, which is the fold's precondition.
**Confidence:** read, then computed the fold over `data/HOSTS.json`.

Also checked and found sound: `owns()`'s `host=None` skip and the fact that `load()` always passes
a host (so every load enforces it); verified that `read.py:962` and `feats.evidence_for` both stamp
`entity` and `host` with the same raw host string the readers pass, so the host check does not
turn every readfeats hit into a miss; `provenance_ok`'s three outcomes; `write_path`'s
check-then-write.

---

## cosmography.py

**How read:** every line; the two non-standard size classes were re-derived by hand against their
ceilings.

### Derivation verified
`MINOR` → `1/GALAXIES_DEFAULT` × `GALAXIES_DEFAULT` = exactly 1.0 galaxy against a ceiling of 1.0
(`>` so it passes). `POCKET` → `1/(2e11 × 1e8)` × 2e11 = 1e-8 galaxies = **one star's worth**,
matching its own description. Neither refuses, and `SIZE_CLASS_MAX_GALAXIES` remains the check that
would catch a multiplier drifting off its prose again.

### INFO — `validate()`'s mix-sum clause inspects the module constant, not the census it was handed
**Where:** src/cosmography.py:325-326
**What:** `if abs(sum(KARDASHEV_MIX.values()) - 1.0) > 1e-6:` — the only clause in a function
documented to "Refuse a census" that never touches `c`.
**Why it matters:** a hand-built census dict carrying a different `kardashev` distribution is
validated against the module's constants regardless. The constants sum to exactly 1.00000 today, so
the clause can only ever fire on an edit to this file — which is a real (if different) thing to
check, just not the thing the function's contract says it checks.

### QUESTION — an explicit `galaxies=` argument is still multiplied by the size-class multiplier
**Where:** src/cosmography.py:254
**What:** `n_galaxies = (galaxies if galaxies is not None else GALAXIES_DEFAULT) * mult`, so
`census("MINOR", galaxies=5)` yields 2.5e-11 galaxies rather than 5.
**Why it is a question, not a fix:** it may be deliberate ("scale THIS universe by its class"). No
caller passes `galaxies=` today — `address_space.py:570-571`, `pipeline.py:2637` and
`verify_math.py:799/1428/1430` all pass the literal `"STANDARD"`, where `mult` is 1.0 — so nothing
is wrong in production either way. Worth one sentence in the docstring.

### INFO — `kardashev_K(nan)` returns nan rather than None
**Where:** src/cosmography.py:207-209. `if watts <= 0` is False for NaN, so `math.log10(nan)`
propagates and the function returns `nan` from a guard written to answer `None` for inadmissible
input. `physics.py` refuses exactly this shape on purpose with `not v >= 0.0` (physics.py:110-121);
this is the version without that accident.

Also checked and found sound: `kardashev_to_magnitude`'s `reached = None` initialiser and the
ascending-latch loop; `census()`'s raise on an invalid verdict; `validate()`'s three ratio ceilings
and the size-class category ceiling; the `"REFERENCE ONLY"` markings on
`GALAXIES_CONSELICE_2016` / `STARS_MILKY_WAY` (marked kept-on-purpose — saw the marking).

---

## physics.py

Clean. Read every line.

Checked for: sign-preserving inputs that produce a plausible-looking wrong answer (mass, volume,
radius all refused with `not x > 0.0`, which catches NaN by the shape of the comparison); the one
parameter whose guard is written the other way round (`speed`, given its own explicit
`not v >= 0.0` NaN test at 110-121); infinity on every input (`kinetic` mass 99-109, speed 122-127,
`joules_for` volume 169-176, `sphere_volume` radius 205-210, `binding_energy` radius 247-254 — the
quiet one, since R is the denominator and inf returned a finite-looking 0.0 — and mass 260-266);
the RESULT of otherwise-legal arithmetic (`kinetic` 133-146, `joules_for` 178-186, `sphere_volume`
211-223 catching `OverflowError` out of `r ** 3`, `binding_energy` 267-285 catching it out of
`m ** 2`); `joules_for` refusing an unknown material or mode rather than defaulting to rock; the
Newtonian/relativistic switch matching its docstring at `0.1c`; and the docstring claim that
`binding_energy` deliberately disagrees with `assay.BAND_EDGES`'s literature value for the Sun,
which is stated as a limitation rather than a defect. No check here can fail to fail.

---

## halo.py

Clean. Read every line.

Checked for: axis coverage against the live weights — all three roster entries carry exactly the
eleven axes in `assay.WEIGHTS` (the eight `CHARTER_PHYSICAL_WEIGHTS` plus the three
`FACULTY_AXES`), so `--full`'s `rec["axes"][ax]` loop cannot `KeyError`; the per-axis provenance
tag being genuinely per-axis rather than the blanket `"[wiki] "` the docstring records replacing
(each tuple carries its own `canon`/`wiki` third element, and the low-confidence axes named in the
docstring — Precursors' celerity, Gravemind's celerity, Ur-Didact's celerity — are each marked
`canon`, matching the claim); both anchors used (`M6`, `M4`) present in `assay.LADDER`, so the
ranking key cannot raise; `textwrap.wrap` in place of a `[:54]` cut; and the write path gating on
`silence.write_json`'s landed verdict with rc 1 and an explicit WRITE DENIED line on refusal.

---

## Citations I could not close inside this batch

Per the brief, named rather than guessed at: `drill._deliberately_failing` / `drill.net` /
`drill._scope_lands_key_wise`, `health.is_selftest` / `health.record`, `silence.note`,
`overnight.STANDING` / `overnight.ALL_JOBS`, `foreman.main`'s loop cadence, `feats.evidence_for`
and `read.read_entity` are all outside batch 06. I read them to check the claims above and have
said so at each finding; the coordinator can resolve any of them across batches.
