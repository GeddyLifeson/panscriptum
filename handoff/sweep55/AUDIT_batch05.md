# AUDIT — batch 05 (run55, 2026-09-11)

Modules read in full, line by line: `feats.py` (2,783), `allsweep.py` (1,013),
`thread_integrity.py` (721), `autostart.py` (564), `axis_correlation.py` (443), `sweep.py` (374),
`entity_match.py` (310), `catalog.py` (167). 6,375 lines total.

Method: every line read in source order. Where a finding depended on data shape I inspected the
artifact read-only (`data/THREADS.json`, `data/CHARTER_SPINE_CODES.json`, directory listings for
`data/NAVTREE.json` / `ROSETTA.json` / `WIKI_HOSTS.json`). **Nothing under `src/`, `data/`,
`state/` or any ledger was written or executed.** No module in this batch was run — in particular
`sweep.py`, `feats.py` and `axis_correlation.py --write` all land files in `data/` and were read
rather than driven.

Cross-batch citations I could not close myself are named as such below.

---

## The allsweep question the coordinator asked

**Can allsweep tell an external outage from a code fault?  No.** `run_verifier`
(`src/allsweep.py:389`) computes exactly one severity bit:

    failed = bool(crashed or (r.returncode != 0 and rc_means == RC_BROKEN and not refused))

There are four possible outcomes for a row — `ok`, `findings`, `refused` (the plant-wide halt),
`FAILED` — and no fifth for "the upstream is down". `preflight` (`allsweep.py:222`) and
`cascade live call` (`allsweep.py:280`) are both `RC_BROKEN`, so dandwiki.com not answering its
API and every cloud free tier being rate-limited are graded byte-identically to a module that
crashed: `failed=True`, counted into `bad` at `:977`, and handed to the queue by
`workorders.battery_faults` as `verifier X exited rc=N and its rc means 'broken'`. The only
"this is not our fault" concession in the file is `_HALT_REFUSAL`, which is a fault of *ours* by
definition. The comment at `allsweep.py:215-221` that grades `preflight` BROKEN reasons only
about double-counting against `workorders`, not about the check's dependence on a remote host.

**Is a verifier that cannot run reported as UNKNOWN rather than as clean?  Yes in the main —
with two holes, both filed below.** A timeout (`:408`) and a failure to even launch (`:414`) both
set `failed=True` and carry the reason in `tail`, which is the right direction. The two holes are
MAJOR-2 (an `RC_FINDINGS` verifier that dies via bare `SystemExit` grades green) and MAJOR-1
(`--quick` publishes a report in which the VERIFY and ESTATE tiers left *no rows at all*, which
every consumer reads as zero faults).

Neither RED row named in the tasking is a code defect in this batch's files. I did not file them.

---

## src/allsweep.py

### MAJOR — `--quick` overwrites the battery's verdict with a report that cannot say it is partial
**Where:** `src/allsweep.py:818`, `:843`, `:932-937`, `:1002-1008`
**What:** `--quick` sets `verifiers = []` (the `if not a.quick:` at `:818` is skipped) and leaves
`est = {}` (`:843`). `main()` then lands the report unconditionally at `:932`:

    landed = silence.write_json(OUT, {"at": time.time(),
                                      "imports": imports, "verifiers": verifiers,
                                      "lint": lint_bad,
                                      "reconcile": findings, "estate": est,
                                      "estate_faults": est_faults, ...})

There is no `quick` key, no `tiers_run` key, and no marker of any kind distinguishing "the VERIFY
tier ran and every verifier passed" from "the VERIFY tier did not run".
**Why it is wrong:** `foreman.py:1499` runs `allsweep.py --quick` as a live pre-mutation check, so
this is not a hypothetical invocation. Each such run replaces `data/ALLSWEEP.json` — the file the
whole plant treats as the battery's answer — with a report whose `verifiers` and `estate_faults`
are empty lists and whose `at` is *fresh*. I traced the consumer: `workorders.battery_faults`
(`src/workorders.py:268-322`) iterates `allsweep.get("verifiers") or []`, so zero rows contributes
zero faults; its fail-closed arm for ungraded ESTATE (`workorders.py:310`) is gated on
`faults is None and est` carrying a tier key, and `--quick` supplies `estate_faults: []` with
`est = {}`, so that arm does not fire either; and the fresh `at` actively *clears* `BATTERY_STALE`
(`workorders.py:261-266`). Net effect: a foreman pass that ran 2 of 5 tiers leaves behind an
artifact that reads, to the queue and to `standards.py`, as a complete and current green battery.
This is the same defect the file documents three times against itself (LINT until run #26, ESTATE
until #36, VERIFY until #37) — a tier that is not allowed to fail — arriving through an absent row
rather than an ungraded one. The console is honest (`:1003` prints `verifiers 0`); the artifact is
not, and the artifact is what the automation reads.
**Confidence:** high. Read both sides of the contract (`allsweep.main` and
`workorders.battery_faults`) and confirmed the live caller by grep (`foreman.py:1499`). I did not
execute anything. `workorders.py` and `foreman.py` are outside my batch — the coordinator should
confirm the consumer reading independently.

### MAJOR — the VERIFY tier is blind to a bare `SystemExit` from a findings-class verifier
**Where:** `src/allsweep.py:383-389`
**What:** `run_verifier` decides a row is broken only via `crashed = "Traceback" in out` plus a
nonzero rc *when* `rc_means == RC_BROKEN`. For an `RC_FINDINGS` row a nonzero exit is never a
fault, and a `SystemExit` prints no traceback.
**Why it is wrong:** three of the twelve verifiers are `RC_FINDINGS` — `swallowed failures`
(`silence.py`, `:224`), `thread integrity` (`:241`), `catalogue backscan` (`audit.py`, `:246`) —
and `silence.py` carries two guards that exit exactly this way: the `_BAD_CHARS` corruption guard
at `silence.py:81-83` and the published-copy refusal at `silence.py:78`. If either fires, the
child exits nonzero, prints one sentence, emits no traceback, and this tier grades it
**`findings`** — green, counted as zero, published as `failed: false`, and read by
`workorders.battery_faults` as a healthy row. The verifier whose entire product is "here are the
swallowed failures" would then be reporting nothing, and nothing would say so.
The IMPORT tier has exactly this guard and explains why (`allsweep.py:336-346`: *"anything dying
via `raise SystemExit(msg)` — which prints no traceback — was graded green… The IMPORT tier was
blind to its own corruption detector."*). `verify_math.py:7598` nets that fix — and nets it for
the import tier **only** (`"the import tier is not blind to a bare SystemExit"`, asserting the
string `"exited without a traceback"` appears in `allsweep.py`). That string does appear, at
`:346`, inside `check_import`. `run_verifier` twenty lines below has no equivalent and no net.
**Confidence:** high. Read `run_verifier` and `check_import` side by side; confirmed the guard
shapes by grep over every module named in `VERIFIERS`; read the verify_math net at `:7598-7601`
and confirmed its subject is the import tier.

### MINOR — no verifier may report UNKNOWN for an unavailable dependency
**Where:** `src/allsweep.py:120-121` (the `rc_means` vocabulary), `:389`
**What:** the grading vocabulary is exactly two values, `RC_BROKEN` and `RC_FINDINGS`, with
`refused` bolted on for the halt.
**Why it is wrong:** two of the twelve rows depend on a remote party this project does not
control — `preflight` reaches dandwiki.com's API, `cascade live call` makes a real model call
across thirty free-tier providers — and both are currently RED for that reason. Under the present
grading a provider outage fails the battery and files a work order indistinguishable from a
regression, which is the "alarm that always sounds" the file itself walks back at `:117-119` for
`silence`/`audit`. The same argument applies one category over and was never made. Reported as a
gap rather than a fix: whether an external dependency should be able to fail the battery is an
owner call (it is arguably correct that a crawl target being unreachable is a real, actionable
fault), so this is a **QUESTION** — but the current code cannot express either answer, because
there is no third class to put the row in.
**Confidence:** high on the code, deliberately undecided on the remedy.

### INFO — the LINT subprocess is the only spawn in the file that does not carry `env`/`cwd`
**Where:** `src/allsweep.py:770-773` against `:316-318` and `:375-381`
**What:** `check_import` and `run_verifier` both pass `env=ENV, cwd=HERE`; the pyflakes call
passes neither.
**Why it is worth a line:** `ENV` exists to force `PYTHONIOENCODING=utf-8`, and the reason is
stated at `:376-379` — Windows otherwise decodes in cp1252 and *"a verifier whose report contains
an em-dash would have crashed the auditor"*. pyflakes echoes source lines, and this tree's source
is full of the charter's typography. The failure is not silent (a child that dies encoding its
own output exits outside `{0,1}` and the `:794` predicate appends the BLIND line, which counts),
so this is an inconsistency that degrades to a false BLIND rather than to a false pass. Noted
rather than filed as a defect.
**Confidence:** read the three call sites.

### INFO — the module filter is a prefix test on a path, not on a basename
**Where:** `src/allsweep.py:750`
**What:** `mods = [m for m in modules() if not m.startswith("_")]`, where `modules()` (`:286-304`)
now returns subdirectory-relative names such as `deprecated/catalogue_local`.
**Why it is worth a line:** a private module inside a subdirectory (`deprecated/_helper`) does not
start with `_` as a relative path, so it would be import-checked and linted where a top-level
`_helper` would not. Dormant today — I listed `src/` and there is no such file — and it is the
*safe* direction (more coverage, not less). Recorded so the next reader does not re-derive it.
**Confidence:** read `modules()` and the filter; checked the tree.

---

## src/thread_integrity.py

### MAJOR — the Phase 4.2 release gate never walks T3, and 280,345 threads (16% of the graph) are therefore never checked for resolvability
**Where:** `src/thread_integrity.py:186-202` (`load_thread_graph`'s edge walk)
**What:** the walk collects targets from `T1` and `T2` only:

    t1 = row.get("T1")
    if isinstance(t1, dict):
        targets.append(("T1", t1.get("to")))
    for cat, lst in (row.get("T2") or {}).items():
        for e in (lst or []):
            if isinstance(e, dict):
                targets.append(("T2", e.get("to")))

`T3` is never read. Nothing in the function, the docstring, or the Phase 4.2 comment block at
`:48-63` mentions T3 at all.
**Why it is wrong:** measured against the live `data/THREADS.json` (read-only):

    counts.T1_edges      282,822
    counts.T2_edges    1,213,110   -> walked:      1,495,932
    counts.T3_edges      280,345   -> NOT walked
    counts.total_edges 1,776,277
    sources carrying T3:     80 of 210
    classes declared:  ['T1', 'T2', 'T3', 'T4']   (no source carries a T4 key today)

T3 rows are the same shape the walk already understands — a flat list of
`{"to": "VIII.17", "class": "T3", "why": ..., "from": ...}` — so this is an omission, not an
unhandled schema. And the omission is load-bearing, not cosmetic: I built the same address space
this function builds (`_charter_codes() | set(code_to_sources)`, 96 addresses) and checked the T3
targets against it. **All ten distinct T3 targets — `VIII.2`, `VIII.6`–`VIII.12`, `VIII.15`,
`VIII.17` — are in the address space nowhere.** So every one of those 280,345 edges is, by this
module's own definition at `:197`, a thread that resolves to NO ADDRESS: the plan's DANGLING, the
thing `:659-663` calls the Phase 4.2 release gate (*"DANGLING = 0 is a release gate, not a
metric"*). The module currently returns 0 on this graph. A gate that exits clean while 16% of the
graph it is gating has never been looked at is this project's signature shape.

The honest half of the finding: the `VIII.*` codes are the Chronica Annex volumes, which are real
(`reference/keystone_volumes/VIII_MASTER_CHRONICLE.md`), so the correct repair is probably to
teach the address space about the Annex rather than to raise 80 SUPERVISOR escalations. That is an
owner call. What is *not* ambiguous is that the checker does not look, and reports nothing about
not looking.
**Confidence:** high. Read the walk; measured the graph and the address space directly from the
two data files with a read-only script (no writes, nothing executed from `src/`).

### MINOR — the header prints the complete edge count beside a partial walk, which hides the gap above
**Where:** `src/thread_integrity.py:538-543`
**What:**

    print("(directed thread graph %s -- %d sources, %s threads on record, %d source-level "
          "edges, %d recorded directions over %d addresses)"
          % (..., format(m.get("total_edges", 0), ","), m["source_level_edges"], ...))

`total_edges` comes straight from the file's own `counts` (1,776,277); `source_level_edges` is the
walk's own tally (1,495,932).
**Why it is wrong:** the one line a reader would use to notice MAJOR-1 prints both numbers with no
statement that they should agree, and the two are 280,345 apart. Two different denominators, one
sentence, no relation asserted. The file elsewhere is scrupulous about exactly this (`:465-469`
adds an explicit *"directed; N unordered source pairs"* gloss so a 2x difference cannot be misread);
this line is the same hazard unlabelled.
**Confidence:** read the print and the `meta` construction at `:203-205`.

### MINOR — a malformed T1 or T2 entry is dropped silently rather than counted unresolvable
**Where:** `src/thread_integrity.py:188-194`
**What:** `if isinstance(t1, dict)` and `if isinstance(e, dict)` skip anything of the wrong type
without appending to `targets`, without incrementing `edges`, and without appending to
`unresolvable`.
**Why it is wrong:** a corrupted thread entry (a bare string, a null) vanishes from the count
entirely, so `source_level_edges` shrinks and nothing anywhere says an edge was discarded. That is
the opposite of the contract two dozen lines up (`:160-163`): *"an unreadable graph must never come
back as an empty one, because an empty graph verifies perfectly."* A target that is present but
not a string IS caught (`:197`, `not isinstance(to, str)` -> unresolvable); an *entry* that is not
a dict is not. The two malformations are one class and get opposite treatment.
**Confidence:** read the walk. Dormant against today's file — every T1 is a dict and every T2 value
is a list of dicts — so this is latent, not live.

### MINOR — a wrong-shaped `T2` escapes as `AttributeError`, bypassing the OWNER escalation the docstring promises
**Where:** `src/thread_integrity.py:191` against `:160-163` and `:516-528`
**What:** `for cat, lst in (row.get("T2") or {}).items()` raises `AttributeError` when `T2` is a
list rather than a mapping. `main()` catches only `ThreadGraphUnreadable` (`:516`).
**Why it is wrong:** the docstring at `:160-163` enumerates what "not a graph" means and promises
`ThreadGraphUnreadable` for all of it; `:519-525` then escalates that at **OWNER** level, per
STEP4_PLAN.md §8, *"because every entry in the library cites it"*. A `T2` of the wrong shape is
precisely "not a graph", but it leaves as a bare traceback: no `ThreadGraphUnreadable`, no OWNER
escalation, no `silence.note`, and `rc` set by the interpreter rather than by `:528`'s `return 1`.
It would still be *noticed* — allsweep's `run_verifier` sees "Traceback" and grades it crashed — so
this fails loud, in the wrong lane and one rung too low.
**Confidence:** read `load_thread_graph` and `main`'s handler; traced which exception types each
arm can produce.

Otherwise clean. I checked specifically for: a `total == 0` division in the percentage loop at
`:547` (guarded — the `if counts.get(k)` test cannot be true when `total` is 0); the `seen` dedupe
in `classify` (`:360-362`, the `(a,b) in seen` half correctly removed per order 9038da917a70 and
the mirror half does real work); the exclusivity of DANGLING / PARTIALLY-DANGLING (both `continue`,
so the classes still partition); the both-directions fix at `:406`; and `_floor_verdict`'s six
states, every one of which fails closed on an unreadable or unwritable floor.

---

## src/feats.py

### MAJOR — `_throttle` iterates `_BACKOFF` while another worker can insert into it, and the resulting `RuntimeError` is filed as a network fault
**Where:** `src/feats.py:209-217` (reader) against `:237-239` (writer)
**What:**

    def _throttle(host):
        dom = registrable_domain(host)
        with _HOST_LOCKS[dom]:
            ...
            for h, m in _BACKOFF.items():          # :215
                if m > mult and registrable_domain(h) == dom:

and

    def note_throttled(host):
        with _HOST_LOCKS[registrable_domain(host)]:
            _BACKOFF[host] = min(BACKOFF_MAX, _BACKOFF.get(host, 1.0) * BACKOFF_GROWTH)   # :238

**Why it is wrong:** the lock is taken on the **registrable domain**. A worker on
`marvel.fandom.com` and a worker on `dandwiki.com` hold *different* locks, so nothing serialises
them. `note_throttled` on a host that has never been throttled **inserts a new key**, which
changes the dict's size; if that lands while another thread is inside the `.items()` loop at
`:215`, CPython raises `RuntimeError: dictionary changed size during iteration`.

The conditions are not incidental, they are engineered: `roll()` runs 8 workers by default and 12
under `overnight.py` (`:98-103`), and the job list is **deliberately interleaved by host**
(`:2356-2367`) precisely so that *"the workers are on eight different wikis at any moment"* — i.e.
the code arranges for the exact cross-domain concurrency the lock does not cover.

The consequence is worse than the crash. `_throttle(host)` is called at `:866`, **inside** `api()`'s
`try`, so the `RuntimeError` lands in `except Exception: silence.note("feats.py:api-network-fault")`
(`:938-939`) and, on the final attempt, stamps `why="network"` (`:941`). So a throttle arriving on
host A can make a perfectly healthy request to host B retry twice and then be recorded — on the
entity's permanent cache record, in `mined_under.transport` — as a network fault. That is exactly
the ledger confusion this file spends `:917-932` eliminating for the non-JSON 200 case: *"the
ledger's count for a site is only readable if 'the network is failing', 'the page does not exist'
and 'we are being refused' land in different buckets."* This adds a fourth cause, our own race,
into the first bucket.

The module already owns the correct instrument and does not use it here: `_COUNTS_LOCK` exists at
`:106` and its comment (`:95-105`) says in as many words that a per-host lock *"could never have
serialised"* a globally-keyed structure. `_BACKOFF` is globally keyed and globally iterated, and
was not included.
`backoff_state()` (`:278-280`) iterates the same dict with **no lock at all**; its only caller is
`dashboard.py:679`, which runs in a different process where `_BACKOFF` is empty, so that one is
currently harmless.
**Confidence:** high. Read all three functions and the lock's own comment; confirmed the worker
count and the interleaving from `roll()`; traced the exception's landing site. Not reproduced by
execution — running the roll would write into `data/`.

### MAJOR — two atomic writes use an unqualified `.tmp` name, against this project's own stated rule
**Where:** `src/feats.py:2267` (`evidence_for`) and `src/feats.py:1179` (`resolve_hosts`)
**What:**

    tmp = path + ".tmp"          # :2267, per-entity evidence file
    tmp = HOSTS + ".tmp"         # :1179, data/WIKI_HOSTS.json

**Why it is wrong:** `silence.write_json`'s docstring (`src/silence.py:785-788`) states the rule
and the reason: *"THE TMP NAME CARRIES PID AND THREAD, which the older hand-rolled `path + '.tmp'`
sites did not. Two writers of the same path otherwise collide on the temp file itself, and the
loser can replace the winner's target with a partial file."* `autostart.py:177-180`, in this same
batch, cites order 521b551b790b and applies it (`"%s.%d.%d.tmp" % (VBS, os.getpid(),
threading.get_ident())`). These two sites are the shape the rule was written against.

Both are reachable, not theoretical:

* **`evidence_for`** — `cachekey.write_path` (`src/cachekey.py:197-213`) resolves a collision by
  `os.path.exists(nat)` then reading the file. Two threads mining two different entities that fold
  to the same natural path (`Magic 8 Ball` / `Magic 8-Ball` is the documented live case, cited at
  `feats.py:2041-2045`) both see `nat` absent, both return `nat`, and both then write `nat + ".tmp"`
  concurrently. The interleaved JSON gets renamed into place by `replace_retry`. Self-healing
  exists (`_corrupt` at `:2048-2056` deletes it on next load), so the loss is a spurious re-mine
  plus a `silence.note`, not permanent — but it is a re-fetch against hosts this file says have
  IP-banned the machine once. Cross-process makes it worse: `read.py:823` and `magnitude.py:1206`
  both call `F.evidence_for` on their own clocks.
* **`resolve_hosts`** — an operator running `feats.py --hosts` while `overnight` runs
  `feats.py --roll` (which also calls `resolve_hosts` and also writes the file, `:2723`) puts two
  processes on `WIKI_HOSTS.json.tmp`. The comment immediately above (`:1174-1177`) names the exact
  harm: *"a half-written host map reads as 'no source has a wiki' to everything downstream."*

**Confidence:** high on the rule and the sites (read `silence.write_json`, `cachekey.write_path`,
and both call sites, and grepped the other `evidence_for` callers). Medium on the practical
frequency — I did not execute a concurrent roll. `cachekey.py`, `read.py`, `magnitude.py` and
`silence.py` are outside my batch; the coordinator should confirm the caller set.

### MINOR — on a non-wiki corpus the AMBIGUOUS refusal markers behave as SUFFICIENT ones
**Where:** `src/feats.py:416-421`
**What:**

    markup_present = wiki and any(m in low for m in _WIKI_MARKERS)
    for m in _REFUSAL_MARKERS_AMBIGUOUS:
        if m in low and not markup_present:
            return False, ("carries a refusal marker ...")

**Why it is wrong:** `_REFUSAL_MARKERS_AMBIGUOUS` was split out (order 572918512dbc, `:338-345`)
because *"a real article can legitimately contain them (the Doom UAC announcer's canonical line IS
'Access denied'…)"*, and the safeguard is that an ambiguous hit *"now requires the ABSENCE of
positive wiki-markup evidence to count."* But `markup_present` is `wiki and …`, so when
`wiki=False` it is unconditionally `False` and the safeguard cannot ever engage. `wiki=False` is
exactly the `doc:` and `pages:` corpora — the owner-ingested books and homebrew author sites — and
the reason it exists (`:396-404`) is that *"Real prose has no `[[`, no `{{` and no `==` in it"*.
So on the one corpus where corroborating markup is structurally impossible, every ambiguous phrase
becomes a sufficient refusal. A rulebook page saying "access denied", "captcha" or "temporarily
unavailable" is thrown away as a block page and recorded in `pages_refused` with a reason that
reads as a diagnosis. That is the same class of false refusal the `wiki=False` flag was added to
end (measured there at 401 of 443 pages), at a smaller volume.
Marked MINOR rather than MAJOR because I cannot measure the live rate without walking the corpus,
and the seven ambiguous phrases are not common in rulebook prose.
**Confidence:** high on the logic (read the three layers and both flags); unmeasured on frequency.

### INFO — the hostless tally is taken before the `--only` filter
**Where:** `src/feats.py:2346-2353`
**What:** the `if not h:` arm that fills `hostless_sources` / `hostless_entities` sits *above* the
`if only and only not in r["source"]: continue` line.
**Why it is worth a line:** under `--only X`, the summary at `:2564-2569` prints every hostless
source in the whole corpus as *"excluded from this roll entirely"*, including ones the operator
never asked for. The comment at `:2341-2344` argues carefully for keeping the involuntary
exclusion separate from the deliberate one, and the ordering makes the involuntary count span a
population the deliberate filter had already removed. Cosmetic on a full roll (the default), wrong
only under `--only`.
**Confidence:** read the loop.

### INFO — `--self-test` passes off the cache by default
**Where:** `src/feats.py:2765-2776`
**What:** `evidence_for("dragonball.fandom.com", "Goku", cache=not a.no_cache)` — `--no-cache`
defaults False, so the assertion at `:2771` is evaluated against whatever is already on disk.
**Why it is worth a line:** the stated claim is *"The miner has to beat what the catalogue blurb
gave us, or it is not worth running"*, which is a claim about the miner; as invoked it is a claim
about the cache. A cached green record keeps the self-test green through any breakage of
`discover`/`fetch`/`mine`. `--no-cache` exists and exercises the real thing. Not filed as a defect
because `NEVER_RUN` (`allsweep.py:101`) means nothing invokes this automatically, so it only ever
runs when a person types it and can type the flag.
**Confidence:** read the branch.

Otherwise clean. Specifically checked and found correct: `api()`'s retry loop returns on every
terminal path so it cannot fall through unstamped (`:864-943`); the `_stamp(False, "unknown")`
pre-stamp at `:843` makes an unstamped return read as undetermined rather than clean;
`mined_under_failed_transport`'s monotone `failed_dirty` arm (`:732-734`) and its now-reachable
404 exemption; `_units`' tally bounds matching its yield bound exactly (`:486-493`); the exponent
capture at `:1857-1859` including all three shapes; `_api_list_all`'s repeat-token stop and its
`_CAP_BOUND` increment on a first-request failure (`:1266-1278`); `roll()`'s deferred-tail
accounting (`done["n"]` not incremented on deferral, `total` recomputed at `:2477`); and
`--roll`'s three failing conditions reaching the exit code (`:2744-2758`). The `alive`,
`_page_exists`, `axis_evidence` and `remine` retentions all carry the 2026-09-08 owner-ruling
marking; I saw the marking and moved on.

---

## src/sweep.py

### MAJOR — three missing-file loads return empty silently, and the funnel then reports them as measured zeros into a file four modules read as fact
**Where:** `src/sweep.py:132-133` (`rosetta_index`), `:149-150` (`navtree_names`), `:162` (`sweep`)
**What:**

    if not os.path.exists(p): return {}                 # :132  data/ROSETTA.json
    if not os.path.exists(p): return {}, {}             # :149  data/NAVTREE.json
    hosts = json.load(...) if os.path.exists(F.HOSTS) else {}   # :162  data/WIKI_HOSTS.json

Nothing prints, notes, or records that a file was absent.
**Why it is wrong:** each of the three feeds a named stage of the report that `report()` then
presents as a measurement:

* `NAVTREE.json` absent -> `where` is `{}` -> every `row["shelfmark"]` is `None` ->
  **`addressed` = 0** (`STAGE_TESTS`, `:213`)
* `WIKI_HOSTS.json` absent -> `hosts` is `{}` -> every `row["host"]` is `None` ->
  **`reachable` = 0**, **`read` = 0**, **`evidenced` = 0**, **`assayable` = 0** (`:192` is gated on
  `if host:`), and the `BIGGEST GAPS — sources whose characters are unreachable` block at `:336`
  prints *every source in the library*
* `ROSETTA.json` absent -> **`ranked` = 0**

and then `main()` (`:365`) lands the whole thing in `data/CHARACTER_SWEEP.json` regardless. The
comment at `:358-364` names the readers itself: *"CHARACTER_SWEEP.json is read LIVE and unguarded
by `hostcheck.py`, `magnitude.py` and `standards.py`"*, and `:186-190` adds `foreman`. So a missing
input file produces a complete-looking cast list in which every character is unaddressed,
unreachable and unread, written to the artifact four other modules treat as ground truth.

This is the defect `catalog.py:34-53` — in this same batch — was repaired for, under order
3f4d2d058fdc, with the repair stated in the same words: *"A MISSING INDEX USED TO READ AS AN EMPTY
ONE… That is this project's signature failure shape: a broken read wearing the face of an honest
negative."* `catalog.py` prints a NOTE to stderr and keeps returning `{}`; the identical change
here (three sentences, no behaviour change) was never made. All three files exist on disk today, so
this is latent rather than live.
**Confidence:** high. Read all three loaders, `STAGE_TESTS`, `report()` and `main()`, and traced
each absent file to the stage it zeroes. Confirmed the three files are present today
(`ls data/NAVTREE.json data/ROSETTA.json data/WIKI_HOSTS.json`) so nothing is currently wrong on
disk. `hostcheck.py`, `magnitude.py`, `standards.py` and `foreman.py` are outside my batch — the
consumer claim is the file's own comment, not my verification.

### INFO — absent fails silent and corrupt fails loud, in the same function
**Where:** `src/sweep.py:132-135` and `:149-151`
**What:** both loaders test `os.path.exists` and return empty, then call
`json.load(open(p, ...))` with no `try`.
**Why it is worth a line:** a *missing* NAVTREE returns `{}` and zeroes `addressed` in silence; a
*corrupt* NAVTREE raises `JSONDecodeError` and takes the whole run down. Those are the two opposite
policies, three lines apart, with no comment choosing between them. Fail-loud is the better of the
two and is the direction the other should move.
**Confidence:** read both.

Otherwise clean. `nested_run` (`:221-235`) is correct — it always returns a run of length >= 1 so
`chain[0]` at `:252` cannot IndexError, and because the chain is verified nested the `drop` at
`:262` can never go negative, which is the fault the module docstring says it was rewritten to fix.
`cache_path` (`:90`) carries the 2026-09-08 owner ruling "mark and keep"; saw the marking.

---

## src/axis_correlation.py

### INFO — `widening`'s docstring asserts a branch is not taken, and it is the branch that is taken
**Where:** `src/axis_correlation.py:356-360` against `:331-337`
**What:** the docstring says the sentinel `{"pairs": {}, "mean_r": 0.0}` reproduces rho = 0
*"(no pair hits, and the `doc.get("mean_r")` fallback below is never reached because `rho()` always
finds `doc` truthy and takes the `hit`-missing branch instead)"*. In `rho()`, the hit-missing branch
**is** `return float(doc.get("mean_r") or 0.0)` (`:337`) — there is no other. So the sentence says
a line is unreached by naming the path that reaches it.
**Why it is only INFO:** the *value* is unaffected — the sentinel's `mean_r` is `0.0`, so the
result is the 0.0 the paragraph promises and the drill net at
`drill.py:correlation_actually_widens_the_bar` still stands guard. It is possible the author meant
the `if not doc:` fallback at `:330`, which is genuinely unreached from `widening` once the
sentinel is installed; if so the sentence names the wrong constant. Either way the paragraph
cannot be read correctly, in a docstring whose entire job is to prove a fallback value was not
re-decided.
**Confidence:** read `rho()` and `widening()` together and traced the sentinel through every branch.

### INFO / QUESTION — `_scores_of` cannot see `result.scores` on a row that also carries an `axes` mapping
**Where:** `src/axis_correlation.py:150-163`
**What:**

    ax = v.get("axes")
    if isinstance(ax, dict):
        return {...}                 # returns even when the comprehension yields {}
    res = v.get("result")

**Why it is worth asking:** the early return is unconditional on `axes` being a dict, so a row
carrying an empty-or-unscored `axes: {}` alongside a populated `result.scores` yields `{}` and is
dropped by the caller's `>= 2` test at `:201`. The docstring at `:143-145` argues the opposite
intent — *"adding a third shape later is a change in one place rather than a second `for` loop
that drifts from this one — which is precisely how the automated pass came to be invisible here
for weeks"* — and this is a fourth way for the automated pass to stay invisible. Filed as a
**QUESTION** rather than a fix: whether an `axes` key should shadow `result.scores` is a decision
about `assay.py`'s record shape, which is outside my batch, and I cannot confirm any live row has
both keys without reading `data/ASSAYS.json` at length.
**Confidence:** high on the control flow; unverified against live records.

Otherwise clean. Checked specifically: `widening`'s `if indep else 1.0` guard evaluates the
condition before the division so there is no ZeroDivisionError at `:379`; `_pearson`'s
constant-column and `n < MIN_N` returns; `measure()` builds `xs` and `ys` from the same filtered
comprehension so the pairing cannot skew; `write()` gates on `silence.write_json`'s verdict and
stamps `degraded` from a *known* non-empty `sources_missing` (leaving it absent, not False, when
the caller bypassed `observations()`); and `main()`'s `mean_str` guard at `:426`, which is the
repair for a `%+.4f` on `None`.

---

## src/entity_match.py

### INFO — `candidates`'s docstring promises a list and the function returns an envelope
**Where:** `src/entity_match.py:370-371`
**What:** *"Returns a list of {name, score, reason} sorted best-first, plus the reason the BEST one
is what it is."* The function returns a dict with keys `query`, `reason`, `matches`, `truncated`,
`considered`, `blocked_by_qualifier`.
**Why it is worth a line:** in a module whose stated contract is *"ONE RETURN SHAPE, ALWAYS"*
(`:383`) and which has already been bitten once by getting the shape of one key wrong
(`:389-393`, order 21f729df8884: `[]` where `{}` was needed), the summary line describing the whole
return being a shape it is not is the same hazard at the top level. The rest of the docstring and
`best()` both use the dict correctly, so nothing acts on the wrong reading today.
**Confidence:** read the function and its one in-repo consumer (`best()`).

Otherwise clean, and this is the strongest module in the batch. Checked specifically for: the
qualifier gate being unconditional and un-overridable by score (`:404-413` — the `continue` is
before any scoring); the qualifier-conflict tally only counting near-base-name rejections so the
diagnostic stays meaningful; the deterministic sort at `:423`; `truncated` being set whenever
`limit` bites; both early-exit shapes now carrying `blocked_by_qualifier: {}`; and the import-time
ratchet at `:362` (`assert 0.0 < WEAK < STRONG <= 1.0`), which is a genuine guard — dormant today
but able to fail, which is more than most assertions in this tree.

---

## src/autostart.py

### INFO — `--status` is declared and never read
**Where:** `src/autostart.py:484`, against `:488-520`
**What:** `ap.add_argument("--status", ...)` is defined; `a.status` appears nowhere. The status
report is the fall-through at `:518-560`, reached when none of `--uninstall`, `--install` or
`--watch` was given.
**Why it is worth a line:** behaviourally harmless — typing `--status` produces the status report,
because nothing else claims the invocation — but a flag the code never inspects is a flag whose
future meaning is unenforceable, and this file's own house style is that a declared thing has a
reader. Not a defect; recorded so it is not re-derived.
**Confidence:** read `main()` end to end and grepped for `a.status`.

### INFO — the start budget is process-local, so a watchdog restart resets it
**Where:** `src/autostart.py:429`, `:454-466`
**What:** `starts = []` is a local list; nothing persists it.
**Why it is worth a line:** `MAX_STARTS_PER_HOUR` is argued at `:61-66` as the thing standing
between this module and *"a respawn loop, and this module's own docstring is the incident report
for that shape"*. A watchdog that itself dies and is relaunched at logon comes back with an empty
budget and may start three more supervisors within the same hour. The twin check at `:392` covers
the case where two watchdogs run *simultaneously*, which is the sharper version of the risk, and
`_log` leaves a durable trail either way — so this is a narrow residual, not the incident. Filed
as INFO rather than a fix because persisting the budget is a design decision (a restarted watchdog
arguably *should* get a fresh budget after a reboot) and belongs to whoever owns the module.
**Confidence:** read `watch()` and the constants.

Otherwise clean, and unusually careful. Checked specifically: the tri-state handling of
`supervisor_alive()` at `:447` (`alive is None` -> log and do nothing), at `:508` (`alive is False`,
the comment at `:504-506` explicitly refusing a bare truth test), and at `:527-530` and `:554-557`
in the status report — all four keep the third answer; `installed_state()`'s round-trip comparison
survives Windows newline translation because both the write and the read are text-mode; `install()`
removes the scratch file on both failure arms and reads the launcher back before claiming
"installed"; `uninstall()`'s third state; `_twin_watchdog`'s retry-then-fail-open with the sleep
correctly skipped on the last attempt (`:353`); the `_vbs_body` `Chr(34)` construction, which I
expanded by hand and which produces `"<pythonw>" -u "<script>" --watch` correctly; and the
deliberate, argued decision at `:404-411` to use `codewatch.stale()` rather than `exit_if_stale()`.

---

## src/catalog.py

Clean. Checked for: a missing catalogue reading as an empty one (`load_catalog`, `:34-55` — this is
the *repaired* site and the model the `sweep.py` MAJOR above should follow: it prints a NOTE naming
the configured path and saying the zeros mean "not found"); every CLI path reaching the exit code
(`main()`, `:147-163`, with `cmd_address` and `cmd_read` returning 1 on a miss and an unknown
subcommand returning 2); the uncapped missing-sources listing at `:92-94` (the `[:30]` removal,
order 6434c1ba7b20); and the `raw_bytes`/`compressed_bytes`/`generated_at` keys read at `:67-68`
and `:103`, which I confirmed `generate.py:911-920` actually writes, so the unguarded subscripts
are safe.

One note, not a finding: `cmd_stats` and `cmd_search` return 0 even when `load_catalog` printed its
NOTE. That is deliberate and argued at `:147-152` — the non-zero contract is for an address MISS,
not for an empty catalogue — and the NOTE goes to stderr where a person reads it. Saw the reasoning
and left it.

---

## Summary

| severity | count |
|---|---|
| MAJOR | 6 |
| MINOR | 5 |
| INFO  | 10 |

MAJOR, in the order I would work them:

1. `thread_integrity.py:186` — the Phase 4.2 release gate never walks T3; 280,345 edges unchecked,
   all 10 T3 targets unresolvable against the address space the module itself builds.
2. `allsweep.py:932` — `--quick` (run live by `foreman.py:1499`) publishes an ALLSWEEP.json with no
   VERIFY/ESTATE rows and a fresh timestamp; the queue reads it as a clean, current battery.
3. `allsweep.py:389` — an `RC_FINDINGS` verifier that dies via bare `SystemExit` grades green; the
   IMPORT tier has this guard and `verify_math:7598` nets it there only.
4. `feats.py:215` — `_throttle` iterates `_BACKOFF` under a per-domain lock while a worker on
   another domain can insert into it; the `RuntimeError` is filed as `api-network-fault`.
5. `feats.py:2267` / `:1179` — unqualified `.tmp` names on two concurrently-written files, against
   `silence.write_json:785`'s stated rule and `autostart.py:177`'s application of it.
6. `sweep.py:149` — three silent-empty loads zero four funnel stages and land the result in
   `data/CHARACTER_SWEEP.json`, which four modules read as fact.

### Citations I could not close inside this batch

* `foreman.py:113` and `foreman.py:1399` both cite **`allsweep.py:702, :727`** as where `--quick`
  skips the VERIFY and ESTATE tiers. I can close the target half from inside my batch: in the
  current `allsweep.py`, `:702` is the `def estate_faults(est):` line and `:727` is the
  `for tier in ESTATE_TIERS:` loop inside it. The real `if not a.quick:` guards are at **`:818`**
  and **`:843`**. The citation is stale by roughly 116 lines and now points at an unrelated
  function. `foreman.py` is outside my batch, so I have not checked whether the surrounding claim
  is otherwise still true — flagging the line numbers only.
* The consumer side of MAJOR-2 (`workorders.battery_faults`) and of MAJOR-6
  (`hostcheck`/`magnitude`/`standards`/`foreman` reading `CHARACTER_SWEEP.json`) lives outside this
  batch. For MAJOR-2 I read `workorders.py:183-330` directly and am confident; for MAJOR-6 the
  consumer claim is `sweep.py`'s own comment at `:358-364`, which I did not independently verify.
* The `cachekey.write_path` collision window underpinning half of MAJOR-5 is in `cachekey.py`,
  outside this batch; I read `:197-213` to confirm the TOCTOU shape but did not audit that module.

### Not filed

The two RED allsweep verifiers named in the tasking — `preflight` (dandwiki.com's API not
answering) and `cascade live call` (every cloud free tier rate limited) — are external outages and
are **not** filed as code defects. What I did file, from looking at that question, is MINOR-3: the
grading vocabulary has no class that can express "the upstream is down", so those two rows are
currently indistinguishable from broken subsystems in both the exit code and the work-order queue.
