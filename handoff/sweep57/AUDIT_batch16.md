# Sweep 57, batch 16 — audit

Modules: `src/hostcheck.py`, `src/binding_health.py`, `src/rosetta.py`, `src/weave.py`,
`src/handbuilt.py`, `src/axis_correlation.py`, `src/catalogue_models.py`, `src/halo.py`,
`src/repass_bands.py`. All nine read in full, top to bottom. Open queue checked first
(`workorders.open_orders()`); prior audits (sweep56 batches 06, 13, 15, 16) not re-read in full
but their subjects (30854f11f322, 8b3f2911fa0c) were cross-checked directly against current
source.

AUDIT ONLY. No file edited, no network probe run, no `--apply`/`--write`/`--go` run.

---

## src/binding_health.py

### DEFECT — `_probe_reachable()` cannot ever succeed for a RAW-mode (API-closed) host, so the three-probe design's central discriminator collapses to "host fault" for that whole host class

`canary()` only calls `_probe_reachable` when the present-titles probe failed:

```
1014	    ok_r, det_r = (True, "not probed -- the known-present title resolved") if ok_p \
1015	        else _probe_reachable(host)
```

`_probe_reachable` itself (binding_health.py:806-818):

```
806	    try:
807	        import feats as F
808	        d = F.api(host, {"action": "query", "meta": "siteinfo"}, retries=0)
809	    except Exception as e:
...
816	    if not isinstance(d, dict) or "query" not in d:
817	        return False, "siteinfo returned nothing usable -- the API is not answering"
818	    return True, "siteinfo answered"
```

`F.api()` (feats.py:857-862) resolves the endpoint through `endpoint.api_url()` *before* making
any request:

```
858	    base = EP.api_url(host)
859	    if not base:
860	        # NOT a clean negative: `endpoint.detect()` probes to decide this, so "no usable API"
861	        # can itself be the answer of a failed probe. Reported as undetermined.
862	        _stamp(False, "no-api")
863	        return None                       # no usable API here; fetch() takes the raw path
```

and `endpoint.api_url()` (endpoint.py:275-278) returns `None` for **every** host whose detected
mode is not `MODE_API`:

```
275	def api_url(host):
276	    """The API base for this host, or None when it has no usable API."""
277	    d = detect(host)
278	    return f"https://{host}{d['path']}" if d["mode"] == MODE_API else None
```

So for a RAW-mode host (`www.dandwiki.com` and any other API-closed wiki — the class
`_fetch_chars`'s own docstring names explicitly: *"For a RAW-mode host (every API-closed wiki,
D&D Wiki among them) nothing else in the chain catches it either"*), `F.api(host, ...)` returns
`None` with **no HTTP request made at all** — not an exception, not a live 403, just a
short-circuit on `api_url()`. `_probe_reachable` then unconditionally takes the
`not isinstance(d, dict)` branch and returns `False`. There is no path by which
`_probe_reachable` can return `True` for a RAW-mode host, because the query API it probes does
not exist for that host by construction — this is not a fact about whether the *wiki* is up.

This matters because `verdict()` (binding_health.py:990-993) uses `ok_reachable` as the exact
discriminator between "the binding/entry names are the problem, host is fine" (→ `None`, no
quarantine) and "the host itself is broken" (→ `False`, quarantine):

```
990	    if ok_reachable:
991	        return None, ("host is UP but no catalogued title resolved (%s) -- suspect the binding "
992	                      "or the entry names, not the host" % det_p)
993	    return False, "host unreachable: %s (present probe: %s)" % (det_r, det_p)
```

The module's own docstring for `_probe_reachable` (binding_health.py:800-805) argues this exact
distinction using `www.dandwiki.com` and `eberron.fandom.com` as the two contrasting examples —
eberron (API host, siteinfo answers 200) correctly lands on `None`; dandwiki is offered as the
case that should land on `False` because "it fails this probe outright: 403". But the mechanism
by which dandwiki fails is not a live 403 — `F.api()` never asks — and the same short-circuit
fires for *any* RAW-mode host regardless of whether the wiki is alive, well short of an actual
403. Concretely: if a RAW-mode host's known-present candidate titles ever fail to resolve for a
reason that has nothing to do with the host being down (the exact eberron shape — catalogued
entries whose names are not article titles on an otherwise-live wiki — applied to a RAW-mode
source instead of an API one), `_probe_reachable` still returns `False` unconditionally, `verdict()`
returns `False, "host unreachable"`, and `run()` (binding_health.py:1319-1320) quarantines the
host with a 24-hour `retry_after`. Because the underlying condition (no query API at all) is
permanent, not transient, the host will fail the identical `_probe_reachable` call on every future
canary regardless of whether the wiki itself has recovered, and will be re-quarantined every
`RETRY_AFTER_S` indefinitely. This is exactly the shape order 8b3f2911fa0c already names for a
different call site (`health.py`'s `check_api_paths`) — *"quarantine is a temporary `retry_after`
backoff, and a host whose API is 403 by policy can never be expressed by it"* — reappearing here
in `binding_health.py`'s own reachability probe. Filed as a new finding rather than KNOWN(8b3f2911fa0c)
because that order's `where` names `health.py`, not `binding_health.py`, and this is a distinct
mechanism (a structurally-unreachable fallback probe, not a config check).

Severity: real and reachable for the one named RAW-mode host the project depends on
(`www.dandwiki.com`, called out in `hostcheck.py` as "the one host this project needs that no
generator can derive"), plus any future API-closed source. Whether it fires *today* depends on
whether dandwiki's current known-present candidate titles happen to resolve; the defect is in the
mechanism, not contingent on today's data.

### KNOWN(30854f11f322) — containment-only CONFIRMED binding

`binding_verdict()` (binding_health.py:858-939) is exactly the code this order is filed against.
The docstring at :867-889 already documents, in detail and with the same examples
(`Prime World Equipment`, `eberron`/`war thunder`/`aneurism`), that a score of 100 "CAN COME FROM
CONTAINMENT ALONE" and that the false positive this order names cannot be separated from the true
positives by any measured metric. The `containment` field is recorded on every verdict
(binding_health.py:933) specifically so a caller "that wants to distrust a containment-only
CONFIRMED can now see which ones they are." Nothing new to add; the order is correctly left open
per its own text ("the order stays open for the evidence that would actually settle it").

### Nothing else found

- Quarantine/release CAS (`quarantine()`, `release()`, `_land_cas`) — both correctly re-read the
  digest before the read, retry `CAS_ATTEMPTS` times, and report a distinct "NOT RELEASED"/
  "not recorded" string on exhaustion rather than silently discarding the failure. Both write
  verdicts are captured at every call site checked (`run()` lines 1319-1333).
- `quarantined()`/`is_quarantined()` — the strict/non-strict split and its justification
  (binding_health.py:300-339) hold up: the one non-strict reader is argued correctly (both its
  callers fail closed on the write side already).
- `run()`'s whole-estate-vs-partial-pass guards (empty hosts map, zero-host report, filtered pass
  matching nothing, CAS-guarded merge) — all four refusal branches were traced and each refuses
  before landing a report that would misrepresent the estate, per their own comments.
- The `_probe_absent`/`_probe_present`/`page_looks_real` symmetry argued at length in the
  docstrings checks out against the code as written.

---

## src/hostcheck.py

### KNOWN(386c0d66e31e) — stale internal line citations in the `_PROSE_ONLY_GOOD_RATE` comment

hostcheck.py:256-261:

```
256	# NAMED FOR WHAT IT ACTUALLY IS (order 4c1f531236ad). This was `GOOD = 0.35`, sitting in the
257	# threshold block beside four constants that are read by live code, and read by NOTHING: grep
258	# across src/ finds the binding, the module docstring at :37, and two historical comments at
259	# :800 and :815 describing the selection path that USED to consult it. Its sibling `DEAD` right
260	# below IS live (score(), :719-742); `GOOD_LIFT` at :219, which the live code does read, is a
261	# different constant measuring a different thing.
```

Order 386c0d66e31e's "STILL OPEN" roster names this exact spot: *"b16 src/hostcheck.py:256-270
the dead-code defence cites :37 (correct), :219, :719-742 and :800/:815 (all wrong)."* Re-checked
against the current file and the citations are indeed still off (`GOOD_LIFT` is defined at :293
not :219; `score()` runs :751-893 not :719-742; the historical comments about the old selection
path are at :952-970/:1567 in the `sweep(repair=True)` block, not :800/:815). Already filed;
nothing new.

### Nothing else found

`_land_hosts`'s compare-and-swap (hostcheck.py:151-244), the `--repair`/`--purge`/`--adopt` halt
gates, `purge()`'s per-record and per-cache-file write verdicts, and `roster_audit()`'s
`judgeable` split were all read end-to-end and match their own extensive doctrinal comments. No
new fail-open path, no new cap, no new lost-update found.

---

## src/rosetta.py

### DEFECT — misleading "the mine above is NOT on disk" message when only the `.raw.json` backup write fails

rosetta.py:692-696, inside `--mine`'s write step:

```
692	        for path in (OUT, OUT.replace(".json", ".raw.json")):
693	            if not silence.write_json(path, out, indent=1, ensure_ascii=False):
694	                print("rosetta: %s could not be replaced; the mine above is NOT on disk."
695	                      % os.path.basename(path), file=sys.stderr)
696	                return 1
```

The loop writes `OUT` (`ROSETTA.json`) first and the raw backup copy second. If the first write
lands and only the *second* (`ROSETTA.raw.json`) is denied, the printed message names
`ROSETTA.raw.json` as `%s` but asserts categorically that "the mine above is NOT on disk" — which
is false in that case: `ROSETTA.json`, the working file every other command in this module reads
(`--check`, `--refine`), did land. An operator reading stderr has no way to tell "the whole mine
was lost" from "only the backup copy was lost" from this line alone; both print the identical
sentence. This is the same class of fault the surrounding code is otherwise scrupulous about
(every other denied-write message in this file names exactly what did and did not happen — see
`--refine`'s and `--check`'s own messages a few lines below). Low severity (the working file's
own content is not at risk, and a re-run fixes the backup), but the message actively
misinforms.

### Nothing else found

`MINE_FLOOR`'s degraded-mine guard, `scales_for`'s error/empty distinction, `numeric_rows`'s
row-vs-window pairing, `assays_by_host`'s `partition("|")` fix, and `check()`'s per-host scoping
were all read against their docstrings and hold up. No caps, no silent swallow beyond what's
already `silence.note`d.

---

## src/weave.py

Nothing found. `components()`'s threshold<=0 refusal, `null_threshold_surprisal`'s
`NullThresholdUnmeasured` (never silently spent as 0.0), the mechanic/rules-voice filter's
whole-description scan, and the three-artifact write-verdict gating in `main()` were all traced
and match their docstrings. `pair_weights()`/`null_threshold()` are declared SUPERSEDED-but-kept
per house dead-code doctrine and are correctly unreferenced by any live caller (`main()`,
`pipeline.py`, `tiers.py` all call the surprisal-weighted twins) — verified with a call-site
check, not just trusted from the comment.

---

## src/handbuilt.py

### DEFECT — four stale `file.py:NNN` citations in one docstring, none covered by the two existing aggregate stale-citation orders

handbuilt.py:455-464 (inside the `main()` write-gating comment):

```
455	    # THROUGH `silence.write_json`, NOT A HAND-ROLLED FIXED TEMP NAME (order f9c7a2c55536).
456	    # The five lines this replaces staged to `OUT + ".tmp"`, which costs two things silence.py
457	    # documents against itself: (1) the temp name carried no pid/thread, so two writers of this
458	    # path collide on the TEMP FILE and the loser can replace the target with a partial one
459	    # (silence.py:511, and the same repair already made at standards.py:1534 and
460	    # retry_synthesis.py:47-49); (2) a denied replace leaked `HANDBUILT_ASSAYS.json.tmp` beside
461	    # the target permanently, with no cleaner anywhere in the tree (silence.py:519-530) -- and a
462	    # denied replace is the ORDINARY case on Windows, which is why replace_retry exists at all.
```

Checked each citation against the file it names:

- **`silence.py:511`**, cited for "the loser can replace the target with a partial one" — actual
  text (`silence.py:785-788`): *"THE TMP NAME CARRIES PID AND THREAD ... Two writers of the same
  path otherwise collide on the temp file itself, and the loser can replace the winner's target
  with a partial file."* Line 511 in the current file is inside `append_line`'s unrelated
  "RECORDED HERE, NOT IN THE `except` ABOVE" discussion of lock-failure ledgering. Drift: ~275
  lines.
- **`standards.py:1534`**, cited for "the same repair already made" (the pid/thread temp-name
  fix) — actual text (`standards.py:1745-1754`): *"THROUGH `silence.write_json`, not a hand-rolled
  fixed `JOB_WATCH + ".tmp"`: the fixed name collided across `dashboard.py`'s polling and
  `publish.py --loop`'s own writes of this same file..."* Line 1534 in the current file is inside
  the unrelated `counters-moving` standard. Drift: ~211 lines.
- **`retry_synthesis.py:47-49`** — accurate. `retry_synthesis.py:48-49` reads *"`silence.write_json`,
  not a hand-rolled `path + ".tmp"`: the fixed tmp name collides when two processes write at
  once..."* — within one line of the cited range.
- **`silence.py:519-530`**, cited for "a denied replace leaked ... permanently, with no cleaner
  anywhere in the tree" — actual text (`silence.py:838-844`): *"AND THE TEMP GOES WHEN THE REPLACE
  IS REFUSED ... EVERY denied write leaked one `<path>.<pid>.<tid>.tmp` beside its target,
  permanently, with no cleaner anywhere in the tree."* Line 519-530 in the current file is the
  tail of the same unrelated `append_line` discussion cited above. Drift: ~320 lines.

And separately, handbuilt.py:502 (inside `main()`'s `--full` citation-wrapping comment):

```
497	                # THE WHOLE CITATION, WRAPPED -- NOT `d["cited"][:58]` (order 9c6a23625865).
...
502	                # so on. catalogue_models.py:227-228 already ruled on the console half of this
```

cites `catalogue_models.py:227-228` for *"the persisted copy being complete does not help someone
looking at the terminal."* That sentence actually lives at `catalogue_models.py:260-261`; lines
227-228 of the current file are `unverified = []` / `for name in sorted(provs):` — unrelated.
Drift: ~33 lines.

Checked both existing aggregate orders for this class (`89503c58409f`, sweep 48's 60-site roster,
and `386c0d66e31e`, sweep 54's roster) in full: neither lists `handbuilt.py` as a source of a bad
citation, so these four are new sites, not a re-derivation. All four are display/documentation
only (no code path reads a citation string), so severity is MINOR per the project's own doctrine
on this class, but they are concentrated (one function, one paragraph) and one of the four is
correct, which argues against "the whole paragraph just needs updating" being a stale-file
artifact — these were individually wrong at write time or drifted independently.

### Nothing else found

The `"unestimable"` sentinel handling in `--full` (handbuilt.py:490-496), the write-then-print
ordering rationale, and every hand-scored sheet's own arithmetic were checked; no new issue.

---

## src/axis_correlation.py

### QUESTION — no floor/comparison guards `write()` against silently overwriting a larger matrix with a smaller one when all sources are readable

`observations()` names `sources_missing` and `write()` stamps `doc["degraded"]` only when
`sources_missing` is non-empty (axis_correlation.py:275-277). That correctly flags the case where
a *source file* vanished or failed to parse. It does **not** cover the case where every one of the
eight `SOURCES` files is read successfully (so `sources_missing == []`, no `degraded` stamp) but
the number of entities carrying `>= 2` numeric axis scores nonetheless *shrinks* between runs —
e.g. entities losing their `scores`/`axes` shape through an unrelated edit to one of the hand-built
rosters (`HANDBUILT_ASSAYS.json`, `HALO_ASSAYS.json`, etc.), or `ASSAYS.json` rows being
re-assayed without carrying forward `result["scores"]`. In that scenario `measure()`'s `n_entities`
and `pairs` both drop, `write(doc)` unconditionally overwrites `AXIS_CORRELATION.json`
(axis_correlation.py:278-281) with the smaller matrix, and nothing on the face of the file — no
`degraded` key, `sources_read` shows all 8 — distinguishes it from a genuine, larger measurement.
`rosetta.py` has an explicit, documented guard for exactly this shape (`MINE_FLOOR`, rosetta.py:61-67,
"a pass that comes back with three quarters of what is already on disk ... `--force` is the
deliberate override"), including the specific argument that a source can silently degrade (there,
a throttled wiki) without any file going missing. `axis_correlation.py` has no analogous
comparison against the standing file's `n_entities`/`measured_pairs` at all.

This is asked as a QUESTION rather than filed as a DEFECT because: (1) it is a design gap, not a
demonstrated live failure — I did not find a code path that actually shrinks the entity population
today; (2) every published `+/-` computed from a degraded-but-unflagged matrix is still *closer to
independent* than the current no-matrix fallback (rho=0), so the failure mode is "less-wide bars
than the true population would support," not "wrong direction" or a safety-doctrine violation of
the kind Hard Rule -1 is written against; and (3) it's plausible the owner considers 8-source
completeness a sufficient proxy and the `n_entities` figure printed on every `--write` run
(axis_correlation.py:397-398) sufficient operator-visible signal, given a human runs `--write`
deliberately rather than a schedule doing it unattended. Worth a ruling on whether `write()` should
gain a floor comparable to `rosetta.MINE_FLOOR`.

### Nothing else found

`_scores_of`'s dual-shape handling (including the `bool`-is-an-`int` exclusion), `rho()`'s
documented default-to-mean-not-zero, and `widening()`'s single-`load()`-per-call fix (order
1b29e38dbb17) were all read against the code and check out. The module's own stated finding — that
`ASSAYS.json`'s 507 automated assays are (as of the last write on disk) still only contributing
their scored population once `result["scores"]` exists — is a data-freshness fact, not a code
defect, and is already filed as an owner-facing note in the module docstring itself.

---

## src/catalogue_models.py

Nothing found. `ask_provider`'s four-outcome vocabulary (LISTED/EMPTY_LIST/UNREACHABLE/
UNCONFIGURED), the `EMPTY_LIST`-counts-as-verified fix, the `LAST_WRITE_LANDED` three-state
default (None, not True), and the gated final write were all read end-to-end; no fail-open path,
no cap, no lost-update (this file has exactly one writer per invocation and produces a complete,
self-contained snapshot each time — no partial merge to race).

---

## src/halo.py

Nothing found. Every `ROSTER` entry's axes are plain numeric tuples (no `"unestimable"` sentinel
here, unlike `handbuilt.py`'s Zalama sheet), so the `"%5.1f" % d["score"]` formatting in `--full`
(halo.py:197) cannot hit the `TypeError` `handbuilt.py` had to guard against — confirmed by
reading every axis value in `ROSTER`, not merely absence-of-crash. Per-axis provenance marking and
the gated final write match their own doctrinal comments (both are argued as "already fixed here,
still open in wh40k.py" and wh40k.py is out of scope for this batch).

---

## src/repass_bands.py

Specifically re-audited for the run #56 changes named in the brief (`_preview()`, `demoted_sources`
roster now printed).

- `_preview(s, width=70)` (repass_bands.py:31-45) — correctly cut-with-marker (`chr(8230)`), and
  every one of its three call sites (:70, :84, :86) passes a `str(...)` already, so it cannot be
  handed a non-string.
- `demoted_sources` roster print (repass_bands.py:157-158) — now prints every entry
  (`for _src, _band, _evidence in sorted(demoted_sources): ...`), matching the comment's claim that
  this was previously length-only. `sorted()` over `(src, band, evidence)` tuples sorts on `src`
  first in practice since each source contributes at most one row per pass (one `if` per record in
  the loop above), so no evidence-string ever needs to be compared for ordering; no crash risk from
  mixed types.
- Both the entry-level and source-level demotion paths correctly preserve rejected `scale_note`
  text into `scale_note_rejected` via `PL._stored_cut` rather than discarding it (repass_bands.py:
  114-120), consistent with owner ruling 21 cited in the comment.
- The write-verdict gating (`PL.write_record` checked per record, `denied` list surfaced in the
  closing summary and forcing `rc=1`) is intact and unchanged from its own documented fix.

Order `386c0d66e31e`'s "STILL OPEN" list carries a line for `src/repass_bands.py, src/allsweep.py
— a verify_math.py citation the batch could not check from inside its own batch". Grepped the
current file for any `verify_math` reference; there is none (`grep -n "verify_math" src/repass_bands.py`
returns nothing). Either the citation was already removed/rewritten in the run #56 rewrite this
batch was asked to audit, or it lives only in `allsweep.py` (out of scope here). Nothing to file
against this module today.

Nothing else found.

---

## Summary of new findings

| # | Module | Location | Class | Disposition |
|---|--------|----------|-------|-------------|
| 1 | binding_health.py | `_probe_reachable` (:806-818) vs `endpoint.api_url` (:275-278) | fail path always returns False for RAW-mode hosts | **DEFECT** |
| 2 | rosetta.py | `main()` `--mine` write loop (:692-696) | misleading failure message | **DEFECT** |
| 3 | handbuilt.py | `main()` write-gating comment (:455-464) | 3 stale citations (silence.py:511, silence.py:519-530, standards.py:1534) | **DEFECT** |
| 4 | handbuilt.py | `main()` `--full` comment (:502) | 1 stale citation (catalogue_models.py:227-228) | **DEFECT** (same class as #3) |
| 5 | axis_correlation.py | `write()` (:278-281) vs rosetta.py's `MINE_FLOOR` precedent | missing floor guard | **QUESTION** |

Plus two confirmed-current KNOWN items: `binding_health.py`'s containment-only `CONFIRMED`
binding (order `30854f11f322`) and `hostcheck.py`'s dead-code-comment citation drift (order
`386c0d66e31e`, batch 16's own prior line).

"Nothing found" reported explicitly, per-module, for: `weave.py`, `catalogue_models.py`,
`halo.py`, `repass_bands.py`'s run-#56 changes specifically, and every remaining area of
`hostcheck.py`, `binding_health.py`, `rosetta.py`, and `handbuilt.py` not called out above.
