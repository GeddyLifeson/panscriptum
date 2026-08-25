# Audit batch 07 — feats.py, allsweep.py, address_space.py, feats_index.py, propagation.py, cosmology_graph.py

Read every line of all six files (991 + 447 + 346 + 263 + 214 + 153 = 2,414 lines). All source
citations are `file.py:LINE`.

---

## src/feats.py (991 lines)

### Confirmed / refuted, against the pre-filed list

**feats.py:120-174 (`api()`), CONFIRMED (M16).** The bare `except Exception:` at `:170-174`
returns `None` after retries — the identical value returned for a clean HTTP 200 that legitimately
has no page. Traced the consequence two ways:

- `alive()` (`:177-178`, `retries=0`) feeds `resolve_hosts()`'s slug-guess loop (`:282-288`). One
  transient timeout on the single unretried probe writes `known[src] = None`. Worse than the filed
  note suggests: `resolve_hosts()` at `:265-266` has `if src in known: continue` — once a source is
  cached as `None` in `WIKI_HOSTS.json`, **every subsequent run skips it before ever calling
  `alive()` again**, because presence in `known` (not the truthiness of its value) is what gates
  re-resolution. The false negative is permanent, not merely "sticky for one run", until a human
  deletes the entry or runs with `verify=False` and gets nothing back either.
- `evidence_for()` (`:786-808`) writes the per-entity cache unconditionally with whatever `pages`
  came back — empty on both "no page exists" and "every fetch failed" — and there is no
  fetch-failed flag in the written JSON (`:800-802`). `roll()` (`:868-891`) does distinguish
  `errored` (an exception escaping `evidence_for`) from `empty` (`ev["pages_read"]` empty), which
  helps for a hard raise, but a `fetch()` that quietly returns `{}` because every `api()` call
  inside it exhausted retries records as `empty`, indistinguishable from genuine absence.

**feats.py:311-368 (`discover()`), CONFIRMED, still live.** The docstring at `:315-323` says "the
truncation is gone" — true only for the `extra`-parameter slice that used to run
`sorted(hits, reverse=True)[:extra]` on top of an already-fetched search-hit list; that slice is
in fact removed and a numeric `extra` now raises (`:324-327`). But the two underlying MediaWiki
query caps are untouched:
- `:348-349` — `apprefix` allpages query capped `"aplimit": "500"`.
- `:358-359` — search query capped `"srlimit": "50"`.

Both calls check `(ap or {}).get("continue")` / `(sr or {}).get("continue")` (`:350-351`,
`:360-361`) and only increment `_CAP_BOUND[...]` — there is no continuation loop, no `apcontinue`/
`sroffset` re-query. When MediaWiki signals it withheld results, the code counts that fact and
throws the rest away; the entity is silently mined from a partial page list. This is exactly Hard
Rule 0 ("ranking then truncating"), now instrumented but not fixed. The module is honest about
this in the `_CAP_BOUND` block's own comment (`:75-85`) and in `roll()`'s summary print
(`:912-917`), so it is not a doc/code contradiction — it is a correctly self-labeled, still-open
cap.

**feats_index.py:148 known finding** — see below; it belongs to feats_index.py, not this file, but
its root cause is downstream of the directory-naming convention set here at `:734-735`
(`re.sub(r"[^A-Za-z0-9]+", "_", host)[:40]`), which folds `.` and `-` to the same character and
makes the mapping non-invertible.

### New findings

**feats.py:734-735 — UNVERIFIED, minor.** Cache path is built from
`re.sub(r"[^A-Za-z0-9]+", "_", host)[:40]` and `re.sub(r"[^A-Za-z0-9]+", "_", name)[:80] + ".json"`.
Two distinct hosts or two distinct 80+-character entity names that share their first 40/80
normalized characters collide on the same cache file, silently overwriting one entity's evidence
with another's on the next write. Not traced to an actual collision in the current data (didn't
find one), but the truncation exists and is unguarded — flagging as plausible, not confirmed.

**feats.py: two-writer / atomicity — CLEAN.** `resolve_hosts()` (`:294-298`) and `evidence_for()`
(`:803-807`) both write via tmp-file + `silence.replace_retry`. `remine()` (`:827`) uses
`silence.write_json`. No bare `open(...,"w")` + `json.dump` on a shared file anywhere in this
module.

**feats.py — concurrency — CLEAN.** `_HOST_LOCKS`/`_HOST_LAST` throttle state is a
`defaultdict(threading.Lock)` guarded per-host (`:95-101`); `_RATE_LIMITED`/`_CAP_BOUND` are
plain dicts mutated from worker threads without a lock (`:162`, `:351`, `:361`) but are only ever
incremented (never read-modify-write in a way that loses updates catastrophically — worst case
under a race is a slightly undercounted diagnostic counter, not a truncated dataset). `roll()`'s
`done` dict is correctly protected by `lock` (`:869`, `:881-899`). Nothing here writes shared
*data* files without the lock/atomic-write pattern.

---

## src/allsweep.py (447 lines)

CLEAN. This is a read-only diagnostic/reconciliation sweep; every truncation found is a bounded
*preview* inside a printed or JSON-dumped **report**, with the real count always computed and
carried alongside:

- `:177,181,185` — `orphan_hosts[:6]`, `no_host[:6]`, `missing[:6]` in `note(...)` calls, but
  `note()`'s third arg (`n=len(...)`) always carries the true count (`:177-185`).
- `:224` — `stale[:6]` display, `len(stale)` is the real count.
- `:283-288` — `examples` capped at 6 in the over-band reconciliation, `over` (the real count) is
  what gets reported as `count`.
- `:369,405,409` — `lint_bad[:20]`, `art["bad"][:25]` are CLI print previews only; the full lists
  are written into `ALLSWEEP.json` uncapped (`imports`/`verifiers`/`reconcile`/`est` at
  `:436-438` pass the untruncated Python objects, not the printed slices).

These match the brief's own carve-out ("merely bounds a diagnostic/preview") — the underlying data
is never truncated, only what's echoed to the terminal.

Output write (`:436-438`) uses `silence.write_json` — correct two-writer-contract pattern for the
`ALLSWEEP.json` shared file. `run_verifier()` (`:124-147`) and `check_import()` (`:98-119`) capture
child-process exceptions and record them as findings (`crashed: True`, tail text) rather than
silently discarding them — not a swallowed failure, this is the diagnostic doing its job.

No writes to any other shared file. No correctness bugs found.

---

## src/address_space.py (346 lines)

**address_space.py:130-140 — VERIFIED, comment/docstring contradicts code.** The module docstring
(`:29-41`) asserts "THE WIDTHS ARE DERIVED, NOT CHOSEN" and gives per-field derivations, including
`universe 24 continuities per hyperverse, from the 168 the catalogue resolved`, closing with
"Nothing here is a round number picked because it looked tidy." The actual `FIELDS` table
(`:130-139`) hard-codes `("universe", 1 << 6)` — a literal 64, i.e. exactly a round binary number
picked because it is tidy, not derived from `_continuities()` (`:66-72`, which returns 168) or
from the stated 24. Confirmed by grep: `_continuities()` is called nowhere except the informational
census print at `:278-279` — it plays no role in sizing any field. `WIDTHS["universe"]` is
consumed by `pack`/`unpack`/`assign` (`:258`) using the hard-coded 64, not a derived value. This
does not corrupt data (64 > 24 just means more headroom than claimed, addresses still round-trip),
but it directly contradicts the docstring's central claim about how the scheme is built, which is
exactly the class of bug this project treats as first-class.

**address_space.py — two-writer / atomicity — CLEAN.** `SHELFMARKS.json` is written via
`silence.write_json` (`:337-340`), correctly noted inline as atomic because `pipeline.py` and
`standards.py` both read it.

**address_space.py — no Hard Rule 0 issues found.** `list(addrs.items())[:6]` at `:333` is a CLI
print preview only (`for d, a in list(addrs.items())[:6]`) — the full `addrs` dict is what gets
written to `SHELFMARKS.json` (`:337-340`), uncapped.

`pack()`/`unpack()` round-trip logic (`:145-168`) is correct and raises rather than silently
wrapping on overflow (`:156-157`), which is the right failure mode per its own docstring. No
swallowed-failure issues: the `except Exception` blocks at `:70-72`, `:114-116`, `:304-306`,
`:320-322` all call `silence.note(...)` before falling back to a documented default, which is the
project's accepted pattern (not a bare `except: pass`).

---

## src/feats_index.py (263 lines)

**feats_index.py:148 — VERIFIED, confirmed and root-caused (matches and sharpens the pre-filed
finding).** `host = host_dir.replace("_", ".")` in `load_index()` attempts to reverse the
directory-name mangling `feats.py` performs when caching
(`re.sub(r"[^A-Za-z0-9]+", "_", host)`, feats.py:734). That forward mangling folds **both** `.`
and `-` to `_`, so the reverse is not invertible: any host containing a hyphen gets every
underscore turned back into a dot, producing a host string that never existed.

Confirmed against real data on disk:

| WIKI_HOSTS.json value        | readfeats directory            | `load_index()` reconstructs   |
|---|---|---|
| `date-a-live.fandom.com`     | `date_a_live_fandom_com`       | `date.a.live.fandom.com` (wrong) |
| `sakamoto-days.fandom.com`   | `sakamoto_days_fandom_com`     | `sakamoto.days.fandom.com` (wrong) |
| `the-amazing-digital-circus.fandom.com` | `the_amazing_digital_circus_fandom_com` | `the.amazing.digital.circus.fandom.com` (wrong) |
| `uncle-grandpa.fandom.com`   | `uncle_grandpa_fandom_com`     | `uncle.grandpa.fandom.com` (wrong) |

These are exactly the four hosts the module's own docstring (`:36-38`) blames on "hosts with no
`WIKI_HOSTS` entry at all... A gap in that file rather than in this join, and binding those four
hosts fixes them." **That diagnosis is itself wrong** — I read `data/WIKI_HOSTS.json` directly and
all four hosts ARE bound (table above). The docstring's proposed fix (bind the hosts) would do
nothing, because they are already bound; the actual bug is the irreversible `_`→`.` reconstruction
at `:148`. This is a second, independent instance of lens 6 (comment/docstring contradicts code) on
top of being the lens-3-adjacent join failure the pre-filed note flagged.

Sharper still: the correct host string is sitting unused in the record itself. `feats.py:800`
writes `"host": host` (the real, unmangled value) into every per-entity JSON. Confirmed by reading
`data/readfeats/date_a_live_fandom_com/Kurumi_Tokisaki.json` directly: `"host": "date-a-live.fandom.com"`.
But `load_index()` (`:158-161`) does `rec.setdefault("host", host)` — a no-op since the key is
already present — and then indexes with the **local, mangled** `host` variable
(`idx[(host, _norm(entity))] = rec`, `:161`), discarding the correct value already sitting in
`rec["host"]`. The fix is immediate and doesn't need to touch the mangling scheme at all: index on
`rec.get("host", host)` instead of the recomputed directory-derived `host`.

Traced consequence: `host_to_sources()` (`:114-129`) keys correctly off the *unmangled*
`WIKI_HOSTS.json` values, so `feats_for_source()`'s `hosts` list (`:183`) contains the right string
(`date-a-live.fandom.com`), but the inner loop (`:191-194`) filters `idx.items()` by `h != host`
where `idx`'s `h` is the mangled string — it never matches, so **every feat for these sources is
permanently unreachable from the generation path**, silently, for as long as the host is
hyphenated. Of 6 hyphenated entries in `WIKI_HOSTS.json`, 4 are real fandom hosts (the two others
are `doc:` and `pages:` sentinels, handled by a separate code path and not directly affected by
this particular bug, though see `_PAGES_SENTINEL` note below).

**feats_index.py — no other findings.** `_norm()` (`:90-111`) has an accurate, self-correcting
docstring (explicitly documents a past false claim and how it was fixed 2026-08-24) — a good
example of the opposite of lens 6. `feats_for_source()` (`:166-209`) is correctly ranked-not-capped
per its own docstring and matches the module header's "NO CAPS" claim (`:62-63`) — verified no
`[:N]` on the entity or feats lists themselves. `audit()` (`:212-239`) is read-only and correctly
computed.

---

## src/propagation.py (214 lines)

CLEAN. Pure read-only computation module (Dijkstra shortest-path over the shared-stage graph plus
two closed-form time formulas); no file writes anywhere in this module.

- `load_graph()` (`:71-82`) reads `SHARED_STAGE_GRAPH.json` with a plain `open()` — read-only, no
  two-writer contract concern.
- `shortest()` (`:85-112`) is a standard Dijkstra with an early-exit on popping the destination;
  correct given all edge weights are positive (`d = 1.0 / max(p["weight"], 1e-6)` in
  `load_graph()`, always > 0).
- `observed_mark()` (`:135-158`) iterates rungs from `LADDER_HEIGHT` down to 1 and returns the
  first (i.e. highest) rung whose ascension cost the elapsed lag clears — correct, since
  `ascension_years(rung)` is monotonically increasing in `rung`.
- `main()`'s `probes` list (`:190-197`) is a fixed demo sample for the CLI report, not a truncation
  of any real listing.

No caps, no swallowed failures (no `except` blocks at all in this module), no shared-state writes.

---

## src/cosmology_graph.py (153 lines)

**cosmology_graph.py:86-87 — VERIFIED, Hard Rule 0 violation, consumed as evidence downstream (not
just a preview).** In `build_graph()`:

```python
if len(pair_shared[p]) < 8:
    pair_shared[p].append(name)
```

This caps the list of co-attested entity names recorded per source-pair at 8, even though the pair
weight itself (`pair_w[p] += w`, `:85`) correctly accumulates over every co-attested entity
uncapped. The capped list is written verbatim to `data/SHARED_STAGE_GRAPH.json` as `"shared_sample"`
(`:141-148`) for every pair with `w >= 1.0`.

This is not a display-only preview: `src/resonance.py:133-149` (`resonance_strength()`) reads this
exact file and exact field — `"shared": p.get("shared_sample", [])` — and returns it as part of
the citable evidence for why two shelves are "in resonance." Any pair genuinely co-attesting more
than 8 entities has its evidence list silently truncated to 8 wherever `resonance_strength()` is
consulted.

Strong corroborating evidence that this is a known, ruled-on bug class that simply wasn't applied
here: `src/weave.py:475-481` builds an analogous graph and writes an identically-named
`"shared_sample"` field, with this comment directly on the line:

```python
"shared_sample": shared[(a, b)]}   # WHOLE list (key name kept: resonance.py reads it) -- Hard Rule 0, ruled 2026-08-24
```

i.e. `weave.py`'s equivalent field was deliberately fixed to hold the *whole* list under an
explicit 2026-08-24 Hard Rule 0 ruling, specifically because `resonance.py` reads it as evidence,
not decoration — and `cosmology_graph.py`'s copy of the same pattern was never brought in line
with that ruling. This is the strongest and most concretely-traced finding in this batch.

**cosmology_graph.py — everything else — CLEAN.**
- `:125` (`top = sorted(...)[:16]`) and `:134` (`comps[:8]`) are CLI print previews only; the
  written output (`:141-148`) uses the full `pair_w`/`comps` objects, not these slices.
- `:145` (`if w >= 1.0`) is a weight threshold filter, not an order-then-truncate cap.
- Output write (`:141-148`) uses `silence.write_json` with an inline comment correctly explaining
  why atomicity matters here (`propagation.py` and `resonance.py` both read it live) — correct
  two-writer-contract pattern for everything *except* the pre-truncated `shared_sample` field
  itself, which is capped upstream of the write rather than by the write mechanism.
- No concurrency: single-threaded, no shared mutable state across threads/processes.

---

## Summary of severities

| Finding | Severity | Status |
|---|---|---|
| feats.py:120-178 — `api()`/`alive()` swallow real failures as absence, permanently sticky via `resolve_hosts()`'s `if src in known: continue` | High | VERIFIED (confirms + sharpens filed M16) |
| feats.py:786-808 — `evidence_for()` caches fetch-failure and genuine-absence identically, no flag | High | VERIFIED (confirms filed M16) |
| feats.py:311-368 — `aplimit=500`/`srlimit=50` truncate on `continue`, only counted not fixed | High (Hard Rule 0) | VERIFIED (confirms filed finding; correctly self-documented as still open) |
| feats_index.py:148,158-161 — irreversible host-directory reconstruction strands 4+ hosts' feats; docstring misdiagnoses as "unbound hosts" | High | VERIFIED (confirms + root-causes filed finding) |
| cosmology_graph.py:86-87 — `shared_sample` capped at 8, consumed as evidence by resonance.py | Medium-High (Hard Rule 0) | VERIFIED |
| address_space.py:130-140 — "universe" field width hard-coded, contradicts "derived not chosen" docstring | Low-Medium (doc/code contradiction) | VERIFIED |
| feats.py:734-735 — cache filename truncation to 40/80 chars, possible collision | Low | UNVERIFIED |

allsweep.py and propagation.py: no findings, both fully read and clean.
