# SWEEP 37 — BATCH 14 AUDIT

Agent: sweep37-batch14. Date: 2026-08-28.

## Coverage

Read COMPLETELY, every line, no skimming:

| module | lines |
|---|---|
| src/publish.py | 1054 |
| src/binding_health.py | 838 |
| src/chain.py | 550 |
| src/rosetta.py | 443 |
| src/worldseed.py | 346 |
| src/wh40k.py | 289 |
| src/withdraw_chapters.py | 246 |
| src/physics.py | 193 |
| **total** | **3959** |

No source file was edited. `publish.py --push` was never invoked and nothing was run from
`C:\Users\imarl\panscriptum-export`. `withdraw_chapters.py` was never executed; only its pure
`select()` was called, on a synthetic catalog. `binding_health.py` was never run as a program;
functions were imported and exercised against temp files and a faked `_load`. No network calls.
No process started, stopped or killed.

**One side effect to declare.** Demonstrating B1 required calling `binding_health.quarantine()`,
which escalates unconditionally. It filed a real work order `ca22fd6d8754`
(`HOST_QUARANTINED gamma.fandom.com`) against a fictitious host. I resolved it immediately with
an explanation naming this audit. Nothing was written to the real `HOST_QUARANTINE.json` — the
module constant was pointed at a temp file first — but the escalation ledger carries the entry.
That `quarantine()` escalates before anybody can tell whether the host is real is worth knowing.

Severity totals: **8 MAJOR, 17 MINOR, 0 CRITICAL.** No caps applied to this report.

---

## MAJOR

### P1. `publish.push()` reports "nothing to send" while a commit sits unpushed — src/publish.py `push`

`push()` decides there is nothing to send from `git status --porcelain` alone:

```
git("add", "-A")
porcelain = git("status", "--porcelain")
if not porcelain:
    return False            # NOTHING TO SEND. The only outcome that may read as a no-op.
```

Nothing anywhere in `push()` asks whether the local branch is ahead of `origin/main`. So when
`git("push", "-q", "-u", "origin", "main")` fails — the 403 from a wrong credential that `git()`'s
own comment documents at length, a network failure, a remote rejection — the commit stays on the
local export branch, and the NEXT invocation, finding a clean worktree, takes this branch and
`main()` prints `no change to push` with **rc=0**.

That is the defect `PushHeld` was created for today, standing on the sibling branch. `PushHeld`
covers only the fetch/rebase failure; a failed `git push` raises a plain `RuntimeError` out of
`git()` into `main()`'s generic `except Exception`, where it is clipped to 180 characters and
printed as `publish failed: RuntimeError: ...` rather than as the whole-message, stdout,
"the commit was made and NOTHING reached the public repo" statement `PushHeld` exists to make.

The module's own SITE comment records the observed consequence: *"the remote fell 122 commits
behind while 'synced N files' kept printing above it."*

Proven offline in a scratch repo (bare origin + clone, one pushed commit, one commit never
pushed): `git status --porcelain` returns `''` while `git rev-list --count origin/main..HEAD`
returns `1`.

Confidence: **high** (mechanism demonstrated; the live export repo was deliberately not touched).

### P2. `sync_tree`'s COPY_FILES withdrawal deletes on one failed stat, with none of `prune_export`'s guards — src/publish.py `sync_tree`

```
elif os.path.exists(dstp) and not _same_dir(SITE, HERE):
    try:
        os.remove(dstp)
    except OSError:
        silence.note("publish.py:prune-remove")
```

Three problems, all in a delete path aimed at a PUBLIC repo:

1. **`os.path.exists` answers False for a path it could not read.** It catches `OSError` (and
   `ValueError`) and returns False, so a permission denial, a lock, or an over-long path is
   spelled exactly the same way as "the file is gone." Demonstrated. This module's own docstring
   says *"Norton locks newly-written objects under the project directory"* — the exact condition.
   `HANDOFF.md`, `STATUS.md`, `BUGS.md` are all live-written ledgers.
2. **No `.is-export-copy` marker check.** `prune_export` requires BOTH `not _same_dir(SITE, HERE)`
   AND the marker file before it will delete anything, precisely because a misresolved `SITE`
   "must read as nothing to do, never as permission to delete a live tree." This branch has only
   the first half.
3. **Silent.** `prune_export` prints `pruned N file(s)` because "a file leaving the public repo is
   a bigger event than a file entering it". This path prints nothing at all.

Net effect of one locked ledger file: it is withdrawn from the public repo, and put back the next
cycle by a second commit, so the history reads as though somebody meant it — which is verbatim the
harm `sync_tree`'s own docstring describes for the COPY_DIRS side and fixed there with
`_live_root_state`. The COPY_DIRS half got the live/gone/unavailable classification; the
COPY_FILES half two lines below did not.

This is NOT the MIRROR case f2271d9ee843 (a root removed from `COPY_DIRS`), and it is not the
`.pre*`/`.presilence` gitignore mismatch e14c1f1c494e. Different path, different trigger.

Confidence: **high**.

### B1. An unreadable HOST_QUARANTINE.json reads as "nothing is quarantined", then gets overwritten — src/binding_health.py `_load` / `quarantine` / `quarantined`

`_load` returns the same default for `FileNotFoundError` and for every other exception:

```
except FileNotFoundError:
    return default
except Exception:
    silence.note("binding_health.py:load")
    return default
```

A torn, locked or non-UTF-8 `HOST_QUARANTINE.json` therefore reads as `{}`. Three consequences,
all demonstrated or read directly out of the consumers:

* `quarantined()` returns `{}` and `is_quarantined()` answers False for every rotten host.
* `quarantine()` does `q = _load(...) or {}` and then `_land(QUARANTINE, q)` — a **blind
  overwrite**. Demonstrated: a file holding two live quarantines, corrupted at the tail, was
  replaced by a one-key map. Both records gone, no error, no note about the loss.
* **`workorders.sweep` auto-closes the orders.** src/workorders.py:571-573 iterates every open
  order and resolves any `HOST_QUARANTINED` whose `where` is not in `q`. With `q == {}` that
  closes ALL of them as *"host is no longer quarantined"*, while the hosts go on being mined and
  their empty results go on being filed as honest absences — which is this module's whole subject.
* `dashboard.py:568-570` shows the same empty quarantine list on the published panel.

This is distinct from order 8ee268ce32cc (which is about `quarantine()` lacking the CAS
`release()` now has). This is about the READ that feeds it. A CAS on a `{}` read still lands `{}`.

Confidence: **high** (demonstrated end to end).

### B2. `run()` lands an empty whole-estate report when WIKI_HOSTS.json cannot be read — src/binding_health.py `run`

`hosts_map = _load(os.path.join(HERE, "data", "WIKI_HOSTS.json"), {}) or {}`. Unreadable → `{}` →
`hosts = []` → `out = []` → `merged = []` → the whole-estate branch runs
`_land(OUT, {"checked": 0, "failed": 0, "hosts": []})`.

Demonstrated: a `BINDING_HEALTH.json` holding 203 host verdicts was replaced by a 0-host report.

The partial-pass branch is armed against exactly this shape and the whole-estate branch is not.
The partial branch has a CAS (`_land_cas`) and refuses outright when the standing report cannot be
read (*"Unreadable is NOT empty. Landing a five-host file over a report that could not be read
would destroy the very thing this guard exists to protect"*). The whole-estate branch has neither
— and it reaches the same destination through the INPUT file rather than the output one. The
comment at binding_health.py:736-743 names the failure precisely: *"The same smaller-universe
shape as a cap: nothing fails, the file is well-formed, and it describes a library that is mostly
not there."*

`workorders.sweep`'s 3b detector then reads `hosts: []` and sees no suspect bindings at all.

Confidence: **high** (demonstrated).

### B3. `release()`'s NOT-RELEASED verdict is discarded at both of its call sites — src/binding_health.py `run`

`release()` was rewritten today so that a lost CAS returns
`"NOT RELEASED: HOST_QUARANTINE.json could not be written after 5 attempts (...); <host> is still
quarantined despite: <why>"` rather than lying. Its docstring: *"A release that does not reach
disk leaves the host quarantined while the caller is told it is free."*

Both call sites in this module throw that string away:

```
elif rec.get("healthy") is True and is_quarantined(h):
    release(h)
elif rec.get("healthy") is None and is_quarantined(h):
    release(h, "host is reachable; the failure was in the titles, not the host")
```

And unlike `quarantine()` — which escalates `HOST_QUARANTINE_NOT_RECORDED` from inside itself when
`landed` is False — `release()` neither prints nor escalates. So a release that loses five rounds
is completely invisible: `main()` prints `ok` for the host, the sweep reports it recovered, and the
host stays closed off. A discarded write verdict in the function whose entire rewrite was about
not discarding it.

Confidence: **high** (read directly from `inspect.getsource(BH.run)`).

### C1. `extract()` cannot tell "no contests found" from "no model answered" — src/chain.py `extract` / `_ask`

`_ask` returns `None` when the cloud bridge fails AND the local model fails. The consumer:

```
got = _ask(SYSTEM, "SENTENCES:\n" + "\n".join(lines), SCHEMA)
...
for o in (got or {}).get("outcomes", []):
...
done["pairs"] += len((got or {}).get("outcomes", []))
```

`done = {"n": 0, "pairs": 0, "kept": 0}` — there is no failure tally anywhere in `extract`. A
chunk whose model call never landed contributes zero outcomes and is counted in `done["n"]` as
though it had been read.

The realistic case is not total outage but PARTIAL: this function's own comment at chain.py:308-309
records *"Eight extractors against one local model is the shape that produced HTTP 503 and dropped
this pass from 64 edges to 25."* Under that, some fraction of chunks silently yield nothing, the
graph comes out smaller than the corpus, and `write_result` persists it to CHAIN.json with the
progress line reporting a clean run.

`adjudicate_mutuals` guards precisely this shape one function down — *"With transport down, every
mutual pair would otherwise be filed as a genuine disagreement and the run would look clean — a
check that cannot fail"* — for the epoch probe, which touches a handful of pairs. The main
evidence path, which touches thousands, has no such guard.

Confidence: **high**.

### R1. `--mine` overwrites the working mine AND its only fallback with the same degraded pass — src/rosetta.py `main` / `scales_for`

```
for path in (OUT, OUT.replace(".json", ".raw.json")):
    if not silence.write_json(path, out, indent=1, ensure_ascii=False):
        ...
```

Both files get the SAME `out`. `ROSETTA.raw.json` is not a backup of the previous mine; it is a
second copy of this one. Its stated purpose (rosetta.py:365-367) is to protect `--refine` from
being run twice, and it does that. It offers nothing at all against a bad `--mine`.

And a bad `--mine` is easy. `scales_for` reads `d = F.api(host, {...})` and immediately does
`(d or {}).get("query", {}).get("search", [])`, so a throttled, blocked or 429'd search is
indistinguishable from a wiki that publishes no scale. `if not seen: return {}` and the host
simply does not appear in `out`. Nothing counts hosts that yielded nothing; nothing compares the
new mine's row count against the standing file's before overwriting it. The comment on those very
lines records that a stale copy already cost *"a good 3,514-row mine"* once.

Secondary, same function: `scales_for` does not catch `F.api` raising, and `--mine`'s loop does not
either, so ONE host raising aborts the whole pass before either write — every host mined up to
that point is lost. `binding_health.run` and `chain.harvest` both guard per item for exactly this.

This module holds *"the library's only large-N external ground truth"* (its own words).

Confidence: **high** for the overwrite and the swallow; **high** for the abort.

### D1. An entry whose file could not be STATTED loses its catalog record — src/withdraw_chapters.py `main`

```
src = _abs(rec.get(key))
if not src or not os.path.exists(src):
    missing += 1
    continue
```

The `missing` branch does not add `_addr` to `stuck`. So the address lands in `withdrawn`, is
excluded from `remaining`, and its catalog record is deleted — for a file that may still be in the
library, because `os.path.exists` returns False for an unreadable path as readily as for an absent
one (demonstrated: an over-long path and a path with an illegal character both answer False with
no exception).

The module's contract, stated twice in its docstring and once at the `move failed` branch, is
*"Anything that failed to move keeps its record"*, and the harm it names is exactly this:
*"a chapter still sitting in `output/raw` lost its catalog record anyway, which is a file the
library no longer knows it has."* The `move failed` half was fixed; the `could not stat` half was
not, and it is the half that fires on a lock rather than on a genuine absence.

Confidence: **high**.

---

## MINOR

### P3. `_scrub` does not scrub dictionary KEYS — src/publish.py `_scrub`

`{k: _scrub(v) for k, v in obj.items()}` — the key is passed through untouched. The module
docstring promises the snapshot *"carries no keys, and `_scrub` refuses anything credential-shaped
even if a future edit puts one in the state dict by accident."* Demonstrated:
`_scrub({"ghp_bbbb…": "value"})` returns the key verbatim while scrubbing the value.

Not a leak: LOCK THREE reads the rendered `docs/state.json`, finds the pattern, and refuses the
push. But that converts a redaction into a hard publish stoppage, and the docstring's guarantee is
false as written.

### P4. `render_page`'s three swaps are unverified string presence — src/publish.py `render_page`

`D.PAGE.replace("'/api/state'", "'./state.json'")` and two more. All three literals are present in
`dashboard.PAGE` today (verified), so this is healthy right now. Nothing checks that any swap
occurred. If `dashboard.py` is ever re-quoted or reformatted, the published static page keeps
fetching `/api/state` from the GitHub Pages origin — a permanently broken panel, with no error
anywhere and no way to tell it from the network being slow.

### P5. `scan_for_secrets` reports two different path spellings — src/publish.py `scan_for_secrets`

Suppressed findings are reported under `rel_for_supp` (forward slashes); real findings under `rel`
(`os.sep`). The refusal message and the escalation evidence therefore mix separators. Cosmetic,
but the refusal message is what a person reads at the worst moment.

### P6. The mutation interlock is checked at push time, after the copy has already been staged

`main()` runs `sync_tree()` (which copies `src/` into the export) and THEN `push()`, which asks
`_MUT.active()`. A mutation run that begins after `sync_tree` starts and ends before `push()` asks
leaves deliberately-corrupt bytes staged with the interlock seeing nothing. Low likelihood today
because `mutate.py` is sandboxed and no longer writes under `src/` — but the interlock's stated
premise is that it might, and its window is not the window it guards.

### B4. `checked` counts the whole file while `failed` counts only this pass — src/binding_health.py `run`

`doc = {"at": ..., "checked": len(merged), "failed": failed, "hosts": merged}`. On a `--host`
pass, `merged` is the whole estate and `failed` came from the five hosts probed, so the report can
read `checked: 203, failed: 1` where 1 of 5 failed. The merge comment deliberately made `checked`
whole-file and left `failed` alone. Nothing in `src/` reads `failed`, so the harm is confined to
whoever reads the report.

### B5. A host with no candidate titles skips the quarantine/release block entirely — src/binding_health.py `run`

```
title = known_present_titles(h, hosts_map)
if not title:
    out.append({... "reason": "no catalogued entry to probe with"})
    continue
```

The `continue` jumps past the `quarantine`/`release` cascade. A host that is already quarantined
and later loses all its catalogue candidates (records deleted, a source unbound, or
`known_present_titles`' own `except` swallowing every record file) is never released and never
re-quarantined — it just stays closed off, for ever, with the report saying only that it could not
be probed.

### C2. The `unmatched` roster's identity key is a 40-character truncation, and it is persisted — src/chain.py `extract` / `write_result`

`local_unmatched[side[:40]] += 1`, and `write_result` stores `unmatched.most_common()` into
CHAIN.json. Demonstrated: `"Commander Shepard of the Systems Alliance Navy"` and
`"…Alliance Marines"` collapse into one row.

`write_result`'s comment on this very field cites Hard Rule 0 to justify removing
`most_common(40)`; chain.py:227-234 fixed the identical defect for `sentence[:120]` with
*"Hard Rule 0: an identity key may not be a truncation"*. The truncation eight lines below that
comment, feeding the same persisted artifact, was left standing.

### C3. `adjudicate_mutuals` splits a pair when only ONE side is dated — src/chain.py `adjudicate_mutuals`

The split condition is `if ea != eb`. With `ea = None` and `eb = "X"` that is True, so the pair is
split; then `if not ep: continue` skips re-keying the undated side. The result is one epoch-keyed
edge and one bare edge, no longer mutual — a real disagreement in the record dissolved on half the
evidence. The docstring's rule is *"where they date differently"*, and an undated side is not a
different date; the "left standing" case is written only for *"where neither sentence dates
itself."*

### C4. `harvest()` reads an absent corpus root as an empty one — src/chain.py `harvest`

`glob.glob` returns `[]` for a missing or unmountable directory rather than raising, so `live`
shrinks and every index entry under that root is deleted by
`for rel in [k for k in idx if k not in live]: del idx[rel]` — classified as *"a file that
vanished takes its contests with it."* The index rebuilds safely on the next healthy pass, but the
pass it happens in harvests a partial corpus and says nothing.

### R2. `ordinal_rows` slices `wikitext` with offsets taken from `wikitext.lower()` — src/rosetta.py `ordinal_rows`

```
low = wikitext.lower()
for m in re.finditer(r"\b" + re.escape(tier), low):
    seg = wikitext[max(0, m.start() - 160):m.start()]
```

`str.lower()` is not length-preserving in Unicode. Demonstrated: `'İ'` (U+0130) lowercases to two
code points, and a 36-character sample became 37. Any such character earlier in a page shifts
every subsequent 160-character context window, so the `[[names]]` harvested for each tier drift
away from the tier they sit beside. Low frequency; silent when it happens.

### R3. `check()` matches assay names globally, and drops unscorable scales without a trace — src/rosetta.py `check`

`a_by = {_norm(k): v for k, v in assays.items()}` is a single global map with no host scoping — the
same construction `refine()`'s docstring calls *"how a filter becomes a rubber stamp"* and
deliberately avoids by building `by_host`. Two further edges in the same three lines: `_norm`
collisions in that comprehension silently drop assays (last wins, nothing counts them), and a
scale with fewer than four overlapping names gets `rho = None` from `spearman` and is dropped from
the report with no row saying it could not be scored.

### W1. Both `silence.note` tags cite line numbers, and both have drifted — src/worldseed.py:256, 264

| tag | actual line | drift |
|---|---|---|
| `"worldseed.py:248"` | 256 | 8 |
| `"worldseed.py:255"` | 264 | 9 |

chain.py:181-186 records this exact repair being made in `ingest_doc.py` and pinned by run #35
with a check that no `silence.note` tag in that file is a bare number, and gives the reason:
*"a tag that points at an unrelated line is worse than an opaque one, because it sends the next
reader somewhere confidently wrong."* `worldseed.py` was not swept. The idiom is to cite by
symbol — `worldseed.py:onomasticon-load`, `worldseed.py:continuity-groups`.

### W2. An unreadable ONOMASTICON gives the whole library one culture set — src/worldseed.py `build_all`

`ono = {}` on any exception → `reg_by_group = {}` → `reg_by_group.get(g, "classical")` for every
world → `CULTURE_SET["classical"] = "antique"` for every world. That is precisely the failure
`_first`'s docstring was written against (*"200 of 1,068 worlds ended up sharing one identical
option vector"*), reached through the input file rather than through the matcher. The only trace
is a `silence.note`; `main()` then prints a `culture_set distribution` that would read as a
finding about the catalogue.

### W3. `--write` keys the payload on `designation`, and duplicates collide silently — src/worldseed.py `main`

`payload = {w["designation"]: {...} for w in worlds}` with `designation = f"{src}::{nm}"`. Two
entries in one source sharing a name produce one row (last wins), and nothing compares
`len(payload)` against `len(worlds)`, so the printed `worlds encoded: N` can exceed what
WORLDSEEDS.json actually holds.

### D2. A per-entry PARTIAL move leaves the kept record pointing at a file that moved

The loop moves `raw_path` and `compressed_path` independently. If the first succeeds and the
second raises, `stuck.add(_addr)` keeps the whole record — including a `raw_path` that no longer
exists. The report cannot show this: `moved` and `missing` count PATHS while `stuck` counts
ENTRIES, and the printed lines read as entry counts.

### D3. A `--addr` that matches nothing is silently ignored whenever another selector matched — src/withdraw_chapters.py `main`

Demonstrated: `select(cat, sources=["Song of Syx"], addrs=["II.ZZ.9/TYPO"])` returns the Syx entry
and says nothing about the bogus address. The refusal at withdraw_chapters.py:98-106 fires only
when the WHOLE selection is empty, and its `unknown` list is computed from `a.source` alone — an
`--addr` typo is never named, even on that branch. The rule the refusal states is
*"NAMING SOMETHING AND WITHDRAWING NOTHING IS A TYPO, NOT A RESULT"*, and it is applied per-run
rather than per-selector.

### PH1. `kinetic()` accepts a NaN speed and returns NaN — src/physics.py `kinetic`

Demonstrated: `kinetic(75, float('nan'))` → `nan`, no exception. `abs(nan)` is nan; `nan >= C` is
False; `nan < 0.1*C` is False; the relativistic branch computes `gamma = nan`. `joules_for(inf)`
likewise returns `inf`.

`kinetic(nan, 10)` and `sphere_volume(nan)` DO raise, because `not nan > 0.0` is True — the guard
shape this module already uses for mass, volume and radius happens to catch NaN, and the speed
argument is the one parameter with no such guard. This is the module that says three separate
times that *"a wrong number wearing the shape of a right one is the hardest kind to catch"*, and
NaN is the only value that gets through it.

---

## Verified HEALTHY

Recorded so a later reader knows these were examined and not merely passed over.

**publish.py**
* `_SECRET` and `_is_real_secret` behave correctly across seven probes: AWS access-key id, GitHub
  PAT, `Bearer <token>`, PEM private-key header and a postgres URL carrying a high-entropy
  password (shape `postgres://<user>:<10-char mixed-case alphanumeric>@`) are all caught; the
  `sk-age-of-apocalypse` slug and the `postgres://user:pass@` documentation example are both
  correctly cleared. No eaten escapes: the module's own `_BAD_CHARS` check passes and all
  regexes compile.
  *(The literal probe strings were redacted from this file by the coordinator after
  `publish.scan_for_secrets` refused the push on them — correctly. They were fabricated
  fixtures, never real credentials, but a credential-shaped literal must not reach the public
  repo, and an audit that documents a secret scanner is the last place that should teach anyone
  to wave one through. The probes themselves are reproducible from the shapes named above.)*
* `_is_skipped` matches the `.pre*` family by shape, not by name — `mod.pre1`, `mod.presilence`,
  `x.preview` all refused; `a.py` and `README.md` pass. Nothing in `src/`, `prompts/`,
  `reference/`, `registry_terminal/` or `handoff/` currently matches the pattern by accident
  (0 files), so the false-positive risk noted in e14c1f1c494e is not currently firing.
* `_scan_units` is correct for all four shapes I traced: a trailing newline, no trailing newline,
  a line spanning several blocks, and the carry/overlap handoff when a newline finally arrives.
  Splitting can only add findings, as its docstring claims.
* `scan_for_secrets` treats UNSCANNABLE as a hit (line 0) and `push()`'s filter only strips
  `SUPPRESSED`, so an unreadable file genuinely does refuse the push.
* `_same_dir` uses `realpath` + casefold on BOTH delete paths, and its "equal means decline"
  failure direction is the safe one.
* `_live_root_state`'s three-way live/gone/unavailable classification is correct: it asks twice,
  requires a positive answer from an enumerated parent before it will say "gone", and `sync_tree`
  additionally holds a root when any mid-walk `onerror` arrives.
* All three fail-closed imports (`escalation`, `ledger_guard`, `mutate`) raise with a message
  naming the module and the reason. The mutation interlock refuses a lock with no `sandboxed` key.
* `write()` gates on `silence.write_json`'s verdict and raises rather than printing "wrote".
* `export_root` refuses a throwaway `PANSCRIPTUM_EXPORT` on the RESOLVED path and warns loudly.
* `codewatch.claim_singleton` is loop-mode only, so a hand-run one-shot is not blocked.

**binding_health.py**
* `verdict()` — I walked every combination of the three probe outcomes. `ok_absent is None` is
  handled first and cannot reach `return True`; `not ok_absent` is a host fault regardless of
  reachability; `ok_reachable` with a failed present-probe correctly returns `None` rather than
  quarantining. No branch is unreachable and none is tautological.
* `_probe_absent` returning `None` (not `True`) on an exception, and `_probe_present`'s bounded
  multi-candidate search with the bound reported in the detail, are both correct as documented.
* `binding_verdict`'s published reason for leaving 30854f11f322 open **reproduces exactly**. I ran
  rapidfuzz on the calibration pair: `eberron` vs `eberron rising from last war` scores
  `token_set_ratio 100 / ratio 40.0 / token_sort 40.0 / WRatio 90`, and `legends` vs
  `league legends` scores `100 / 66.7 / 66.7 / 90`. Every metric ranks the false positive at or
  above the true confirmation. The claim that no threshold can separate them is sound, the
  evidence is now published beside the score in `containment`/`tight`, and I agree the order
  should stay open for content evidence rather than be closed with a tuned number.
* `_land_cas` takes the digest BEFORE the read and cleans up its temp file on refusal; the
  partial-pass merge refuses outright on an unreadable standing report.
* `known_present_titles` records unreadable record files with a note rather than skipping silently.

**wh40k.py** — no findings. `A.WEIGHTS` holds exactly 11 axes and all five ROSTER entries carry
exactly those 11, none missing and none extra (verified programmatically), so `compute()` hands
`A.assay` a complete score set and `main --full`'s `rec["axes"][ax]` cannot `KeyError`.
`_provenance` defaults to `unattributed` rather than asserting `wiki`, and `main()`'s write is
gated with rc=1 and a message naming the file and the remedy. The curatorial provenance gap is
already 82fc93f056d4.

**chain.py** — `write_result`'s `unmatched` is genuinely uncapped with totals beside it;
`extract`'s `local`/`local_unmatched` thread-local tallies merged under the lock are correct;
the model-supplied `index` is bounds-checked (`0 <= pos < len(chunk)`) rather than inferred from
position; `entity_index`'s clash-drop for ambiguous short forms is correct.

**physics.py** — apart from PH1 this is the cleanest module in the batch. Every constant carries
its provenance, every other domain edge (`m <= 0`, `v >= C`, `v <= 0`, `r <= 0`, unknown material,
unknown mode) raises with a sentence explaining the domain rather than returning a plausible
number, `binding_energy` refuses `R = 0` by name instead of by `ZeroDivisionError`, the
Newtonian/relativistic switch is correct at the stated threshold, `--table` short-circuits
correctly, there is no I/O and there are no caps.

**worldseed.py** — I specifically checked `states = min(40, ...)` and
`cultures = max(3, min(24, ...))` against Hard Rule 0 and judge them **clean**: they clamp derived
map-generator parameters, not a roster, a list, or an inventory of real things. `unreachable_by_url`
naming what the query string cannot deliver, and `URL_SETTABLE` being cut to the four parameters
Azgaar actually honours, are both the right call. The `primitive: 35` entry is already
40e98eed6870 / ad681057369a and carries an owner-question comment.

**withdraw_chapters.py** — the snapshot-and-verify gate before the irreversible step raises on a
backup that does not restore; `select()` is pure and exact-match; the stray sweep is correctly
gated on `not filtered` and its moves are individually guarded; both writes keep their verdict and
name a distinct remedy; the catalog is edited rather than erased.

---

## Not re-filed (already open, confirmed still live)

* **f2271d9ee843** — the MIRROR case: a root removed from `COPY_DIRS` leaves its export copy in
  public for ever. Confirmed still true; `prune_export` iterates `COPY_DIRS` and nothing else.
* **8ee268ce32cc** — `quarantine()`'s CAS. Still not applied: `quarantine()` is a plain
  `_load` + `_land` read-modify-write while `release()` one function down now has the full CAS.
  My view, since the brief asks for one: the two writers `release()`'s own docstring describes (a
  scheduled `--run` releasing recovered hosts while a targeted `--host` quarantines a rotten one)
  lose updates in the quarantine direction exactly as they did in the release direction, so the
  order is correct and worth closing. But B1 above must be fixed with it — a CAS over a `{}` read
  still lands `{}`, so the CAS alone would make the wipe atomic rather than prevent it.
* **8d14f0adda1b** — the `withdraw_chapters` archive-name collision. I reproduced it: `shutil.move`
  onto an existing file path raises no exception, falls back to `copy2` + `unlink`, and silently
  replaces the archived file (the first withdrawal's only copy). Two additions for whoever takes
  the order: (a) the `--label` default is now `date.today()`, so two withdrawals **on the same
  day** share an archive and collide by default; (b) the same collision overwrites
  `<arch>/catalog.withdrawn.json`, so the second run's manifest replaces the first's — the archive
  loses both the file and the record of it.
* **30854f11f322** — `binding_verdict` containment. Reproduced and endorsed as infeasible to
  threshold (see HEALTHY above).
* **e14c1f1c494e**, **40e98eed6870**, **ad681057369a**, **c0384991bfc5**, **82fc93f056d4**,
  **d19d705925e3**, **cdcb11e3d7fa**, **18a2053bc62d** — all checked against current source and
  all still accurate.

---

## Orders filed (25)

| id | severity | code |
|---|---|---|
| 3778bc42499f | MAJOR | PUBLISH_AHEAD_READS_AS_NOOP |
| d2edc81326da | MAJOR | PUBLISH_COPYFILES_DELETE_ON_FAILED_STAT |
| dd3ff361db49 | MAJOR | BH_UNREADABLE_QUARANTINE_READS_EMPTY |
| 9979963c093a | MAJOR | BH_EMPTY_ESTATE_LANDS_OVER_FULL_REPORT |
| a29c38c9eff3 | MAJOR | BH_RELEASE_VERDICT_DISCARDED |
| 6d35eacf252d | MAJOR | CHAIN_TRANSPORT_FAILURE_READS_AS_NO_CONTESTS |
| 6447bcc2f18c | MAJOR | ROSETTA_MINE_OVERWRITES_ITS_OWN_FALLBACK |
| 22394233dbad | MAJOR | WITHDRAW_FAILED_STAT_DROPS_CATALOG_RECORD |
| b1147f53971e | MINOR | PUBLISH_SCRUB_SKIPS_DICT_KEYS |
| 3d1efe60b4cf | MINOR | PUBLISH_RENDER_PAGE_UNVERIFIED_SWAPS |
| df572f47255f | MINOR | PUBLISH_SCAN_PATH_SPELLING_INCONSISTENT |
| d56228616f9c | MINOR | PUBLISH_MUTATION_INTERLOCK_WINDOW |
| 6c5faf62b2c6 | MINOR | BH_CHECKED_AND_FAILED_COUNT_DIFFERENT_THINGS |
| 5e2aaac58753 | MINOR | BH_UNPROBEABLE_HOST_NEVER_RELEASED |
| 29dde10c569c | MINOR | CHAIN_UNMATCHED_KEY_IS_A_TRUNCATION |
| 679368768c02 | MINOR | CHAIN_MUTUAL_SPLIT_ON_ONE_UNDATED_SIDE |
| b9c013a041db | MINOR | CHAIN_ABSENT_CORPUS_ROOT_READS_AS_EMPTY |
| f045ffe20c52 | MINOR | ROSETTA_ORDINAL_OFFSETS_FROM_LOWERCASED_TEXT |
| 0bba50a6d76b | MINOR | ROSETTA_CHECK_MATCHES_ASSAYS_GLOBALLY |
| 13f18179d05f | MINOR | WORLDSEED_NOTE_TAGS_CITE_DRIFTED_LINES |
| ef19733afaa7 | MINOR | WORLDSEED_MISSING_ONOMASTICON_UNIFORMS_LIBRARY |
| 8b86e70ce8b7 | MINOR | WORLDSEED_DESIGNATION_COLLISIONS_SILENT |
| 1687ff8084b9 | MINOR | WITHDRAW_PARTIAL_MOVE_LEAVES_STALE_RECORD |
| c8ac7dbab3c5 | MINOR | WITHDRAW_UNMATCHED_ADDR_SILENTLY_IGNORED |
| 7909342fefa4 | MINOR | PHYSICS_NAN_SPEED_RETURNS_NAN |

Coverage recorded via `sweep_plan.record('run37', [...], batch=14)`; all eight modules confirmed
stamped `run37`.

The filing script is kept at `handoff/sweep37/file_batch14_orders.py` (written with the Write
tool, never through a shell heredoc, because several of these orders quote regexes and paths).
