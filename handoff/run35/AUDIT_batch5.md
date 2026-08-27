# Batch 5 — run35 — read.py / onomast.py / feats.py / backfill.py / hostcheck.py / scout.py / wiki_source.py / cachekey.py / corpus_db.py

Eleven orders worked. Nine were real and fixed; one (5d8533bc1ed6) is left open as a genuine
cross-module design decision; one (f53381169f79) is disproved against current source. Every fix
was verified against the actual source lines first, per this run's method — quoted below.

## 5bf48fa9f70d — FIXED — `read.py`'s oversized re-split branch could cache a total failure as an empty answer

Verified against source: `_local_carded` (read.py:511-531) re-splits a prompt only when
`len(prompt) > CHUNK + 2000` (12,000 chars), and `CLOUD_CHUNK == CHUNK == 10000`
(read.py:94-96), so in the ordinary case this branch is effectively unreachable — confirming the
order's "unreachable" half. The bug in the branch itself was real: `merged["feats"].extend((got
or {}).get("feats", []))` folded a `None` from any sub-call into an empty list, so a total
failure across every piece returned `{"feats": []}` — answered-with-nothing, not
unanswered — permanently caching an empty result and skipping the GPU bench that the ordinary
single-piece path (read.py:521-524) already does on failure. Fixed: any `None` from a sub-call
now benches the GPU and returns `None` immediately, matching the ordinary path's contract.
Updated the stale comment above it, which still described a cloud/local chunk-size difference
that no longer exists (read.py:94, `CLOUD_CHUNK = CHUNK`) — the branch is now correctly
documented as a safety margin for the `ENTITY:`/`PAGE:` header overhead, not a cloud/local size
gap. Verified: `python -m pyflakes src/read.py` clean, `import read` clean, plus a standalone
check (checks_batch5.py) forcing every sub-call to fail and confirming `None` + GPU-benched.

## 6b7f51f8ec2e — FIXED — cascade mode could still fall through to the local GPU

Verified against source: `_ask_ungated` (read.py:346-429) only touches the local GPU inside `if
_TRANSPORT in ("auto", "cascade")` / `if ensure_transport(verbose=False):` — and when
`ensure_transport()` returns `False` (cascade_bridge unimportable or `CB.engine()` falsy), the
entire inner block was skipped with no `else`, so control fell all the way out to the
unconditional `return _local(...)` at the end of the function — sending a cascade-only call to
the GPU, contradicting the explicit `if _TRANSPORT == "cascade": return None` guard 20 lines
above it. Second, smaller defect confirmed in the same block: `_FELL_BACK[0] += 1` fired before
the `if _TRANSPORT == "cascade": return None` check, so the "(%d to GPU)" progress counter
included chunks that were never actually sent to the GPU. Fixed both: added an `elif _TRANSPORT
== "cascade": return None` for the `ensure_transport() is False` case, and reordered the
increment to fire only when a chunk is actually about to reach `_local()`. Verified: pyflakes
and import clean; a standalone check patches `ensure_transport` to return `False` under
`_TRANSPORT="cascade"` and confirms `_local` is never called and `_FELL_BACK` does not move.

## 36d1dd86fb78 — FIXED — onomast.py's doctrine prose disagreed with its own measured data

Verified directly: ran `onomast.is_carried()` and `onomast.name_worlds()` against the live
`data/RESOLVED_ENTITIES.json` (44,329 entities). Measured earth=26, moon=15 (12 "moon" + 3 "the
moon"), mars=14; `name_worlds()` produces 223 named worlds with endonym counts Earth 26 / Mars
14 / Moon 12 — exactly matching the order's proof. The module's own docstring (lines 7, 16, 28,
57-58) still said "thirty" / "eighteen" / "sixteen", a stale claim from before the corpus (or
the doctrine's scope) changed. Fixed: replaced every stale figure with the measured one
(twenty-six / fifteen / fourteen), rewrapped one line that ran long afterward. This is prose-only
— the mechanism (`is_carried`, `name_worlds`) was already correct; only the doctrine's own
illustration of itself was wrong. Verified: pyflakes and import clean; a standalone check
re-measures live and confirms the docstring's numbers track the measurement rather than
hardcoding today's figures as tomorrow's expectation.

## 5d8533bc1ed6 — LEFT FOR OWNER — `register_for`'s genre/feature voting is real dead code, but the fix is a design decision

Verified: `name_worlds()`'s only call to `register_for` (onomast.py:356) is `register_for(v
["continuity_group"])` — no `genre_register`, no `features`. Since both default to `None`,
`register_for`'s `if not genre_register and not features:` branch (onomast.py:318) fires on
literally every call from production code, so the weighted-voting logic below it
(`GENRE_WEIGHT`/`FEATURE_WEIGHT`/`FEATURE_SHIFT`, lines 322-334) never executes outside a test
that calls `register_for` directly with real arguments. Grepped the whole `src/` tree: the only
other `register_for` in the codebase is `navtree.py`'s own, unrelated, locally-defined function
of the same name — it does not call into `onomast.py` at all. So every disambiguated world
(Earth, Moon, Mars, etc.) is still named by the pure hash `register_for`'s own docstring says was
already replaced.

This is real, but genre.py's module docstring is explicit that this wiring was meant to exist
("register -> culture set and naming (onomast.py, worldseed.py)") and was never completed — no
module in `src/` currently calls `genre.classify_source`/`classify_text` and threads the result
into `onomast.register_for`. Doing it properly requires deciding: which continuity_group maps to
which source record(s) (a `continuity_group` can span multiple `attestations`), which classifier
(`genre.classify_source` vs `grounding.classify_source`) owns the call, and where the `features`
argument's per-world axis data (landform/climate/condition/tech) would come from for a
`continuity_group` rather than a single source. That is cross-module architecture, not a
mechanical fix, and touches files (`genre.py`, `grounding.py`, `worldseed.py`) outside this run's
owned-file list — left open per this run's method (judgment calls about deliberate design are
not mine to make). No check added to checks_batch5.py for this one; see that file's header for
why.

## d097dc4db7c4 — FIXED — feats.py's four numeric silence.note() labels had drifted 171-406 lines from their call sites

Verified with `grep -n 'silence.note("feats.py:'`: labels `"feats.py:125"` (actual line 296,
171 off), `"feats.py:139"` (actual 332, 193 off), `"feats.py:374"` (actual 617, 243 off), and
`"feats.py:695"` (actual 1101, 406 off) — matching BUGS.md m81's account that this drifts as the
file grows and was never filed as its own order. The file already establishes a named-key
convention for its other four notes (`api-404`, `api-nonjson`, `corrupt-cache`,
`throttle-quarantine`), and BUGS.md itself records a prior, identically-shaped fix
(`dashboard.py:362`, resolved run #20) that chose renaming over "accepting the drift" — so this
follows that established precedent rather than making a fresh call. Renamed: `feats.py:125` ->
`feats.py:api-http-error` (non-404 HTTP error status), `feats.py:139` ->
`feats.py:api-network-fault` (the generic `except Exception:` — connection-level failures),
`feats.py:374` -> `feats.py:fetch-bad-revision` (malformed revision content shape in `fetch()`),
`feats.py:695` -> `feats.py:roll-evidence-error` (an `evidence_for()` exception inside `roll()`'s
worker). Also fixed a comment at line ~316 that quoted the old `"feats.py:139"` label by name.
**Cost, stated per the order's own framing:** this splits the ledger's cumulative counts for
these four sites off their history — the renamed keys start counting from zero. Verified:
pyflakes and import clean; a standalone check confirms none of the four stale strings remain and
all four named replacements are present.

## 0a67628cfa8f — FIXED — backfill.py silently scored a failed size lookup as a 0-byte article

Verified against source: `backfill.py:182-183` (now shifted a few lines by the fix) did `d =
F.api(host, {...})` then `for pg in (d or {}).get("query", {}).get("pages", []):` — so a `None`
from `F.api` (which the same file's `RosterIncomplete`/`members()` explicitly treats as
ambiguous between "timeout" and "absent", 100 lines up) silently contributed zero entries to
`sizes` for every title in that batch of 50. Under ranking (`sorted(missing, key=lambda t:
-sizes.get(t, 0))`) those titles then sank to the bottom purely because their lookup failed, not
because they were small — exactly where `--cap` would drop them first. Fixed: titles in a
batch whose `F.api` call returned `None` are now excluded from `sizes` entirely (not scored 0),
tracked in a new `size_lookup_failed` counter that is threaded into all three returned dicts (dry,
write-denied, and success paths), and the sort key changed to `(t not in sizes, -sizes.get(t,
0))` so an unmeasured title ranks WITH the deepest known articles rather than below the shallowest
ones. Verified: pyflakes and import clean; a standalone check simulates a failing batch and
confirms its titles are absent from `sizes`, the failure count is reported, and ranking never
sinks an unmeasured title below a measured-small one.

## f35826ab7a3f — FIXED — backfill.py's "NOT truncated" comment sat directly above a truncation

Verified against source: `backfill.py:187` (pre-fix numbering) read "...but NOT truncated: every
character the wiki lists is a character the library should hold" immediately above
`missing = sorted(missing, key=lambda t: -sizes.get(t, 0))` / `if cap: missing = missing[:cap]`
— a literal false claim about the two lines beneath it. Checked whether this is actually the
Hard-Rule-0 shape or a documentation bug: `--cap` defaults to `None` with its own `argparse` help
text reading "omit for everything, which is the intended use"; `missing` is recomputed fresh
from `have` (the current on-disk entry set) on every call, so a title left off by `--cap` this
run is still there, ranked the same way, next run — nothing is permanently dropped, unlike
`roster(limit=600)`'s Hard-Rule-0 example where a source could never reach a truncated title at
all; and the pre-cap `absent` count is already reported beside the post-cap `queued` count
(fixed for a different reason, 2026-08-24, per the comment two lines above it) — satisfying Hard
Rule 0's own second remedy, "stating the count not shown." So the actual defect here is the
comment's false claim, not the cap's existence. Fixed: rewrote the comment to state what is
actually true and why an opt-in, visible, resumable per-run cap is not the shape Hard Rule 0
forbids. Verified: pyflakes and import clean; a standalone check confirms the default is `None`
and the false "NOT truncated" phrasing is gone from the source right before `if cap:`.

## d3313adbf641 — FIXED — scout.py's three shared-artifact read-modify-writes had no compare-and-swap

Verified against source: `scout.py` read-modified-wrote `WIKI_HOSTS.json` (register-host,
former lines 227-229), `SCOUT_BLOCKED.json` (former lines 236-241), and `SCOUT_ATTEMPTS.json`
(former lines 284/305-307) each with a bare `json.load` / mutate / `_land`, no lock, no
staleness check — over files `hostcheck.adopt()` (WIKI_HOSTS.json) and potentially a concurrent
`scout.py` invocation (the other two) also write. This is exactly the shape `workorders._mutate`
and `runguard._land_claim` were both given compare-and-swap for, using
`silence.digest_of`/`silence.replace_if_unchanged` as the primitive. Fixed: added a `_mutate
(path, change, attempts=8)` helper to scout.py using that same primitive, and rewired all three
call sites through it — `change(d)` is a pure function of the dict it is handed, matching the
established contract. Left `_land`'s fourth call site (`SCOUT.json`'s run-log append) alone: it
is the same shape but out of this order's explicit three-file scope, and `_mutate` as written
assumes a dict root while `SCOUT.json`'s root is a list — flagged separately as a follow-up
task rather than folded in here. Verified: pyflakes and import clean; a standalone check drives
`_mutate` through a genuine concurrent-write race (a second writer lands mid-`change()`) and
confirms the write is refused and nothing is silently overwritten, plus confirms an uncontended
write still lands normally.

## e86eec8ac173 — FIXED — resolve_wiki discarded a known non-fandom host and burned banned-host requests re-guessing it

Verified against source and data: `wiki_source.py:295`'s guard, `if isinstance(known, str) and
known.endswith(".fandom.com"):`, is the only place a recorded `WIKI_HOSTS.json` entry is used —
for any other string value (en.wikipedia.org, www.dandwiki.com, rimworldwiki.com, or scout.py's
own `"pages:"`/`"doc:"` markers) `known` is silently dropped and the function falls through to
`subdomain_candidates()`, guessing FANDOM subdomains for a source the library has already
resolved to somewhere else — and `_api()` (wiki_source.py:203-206) hardcodes
`https://{subdomain}.fandom.com/api.php`, so every one of those guesses is a request against
fandom.com specifically, the host this machine is IP-banned from. Measured live against the
current `data/WIKI_HOSTS.json` (206 keys, counts drifted slightly from the order's 203 since it
was filed, per this project's norm that sweep data is a snapshot): 164 fandom, 27
en.wikipedia.org, 4 www.dandwiki.com, 1 rimworldwiki.com, 5 pages:/doc:, 5 None — confirming
real, non-trivial non-fandom string entries exist. Fixed: added an `elif isinstance(known, str)
and source_name not in WIKI_OVERRIDES: return None, None` immediately after the fandom check, so
a confirmed-non-fandom host short-circuits before any guessing or network call — while a source
that also has a `WIKI_OVERRIDES` entry (deliberate curation) still gets to use it, since that
signal should win over a possibly-unrelated recorded host. Verified: pyflakes and import clean;
a standalone check patches `_api` to raise if ever called and confirms `resolve_wiki` returns
`(None, None)` with zero network attempts for a known non-fandom, non-overridden source.

## 5159320dd758 — PARTIALLY FIXED (hostcheck.py; allsweep.py not owned this run) — cachekey.host_dir() had two hand-spelled twins

Verified against source: `cachekey.py:56-58` defines `host_dir(host)` specifically so
`_SANITISE.sub("_", host or "")[:HOST_CAP]` has one spelling — its own docstring says "ONE
HELPER, NOT FOUR SPELLINGS." `hostcheck.py:711` and `allsweep.py:242` both still hand-spelled
`re.sub(r"[^A-Za-z0-9]+", "_", X)[:40]` instead of calling it, confirmed by direct grep of both
files. Fixed `hostcheck.py` (owned this run): replaced the hand-spelled purge-target-directory
line with `cachekey.host_dir(mined)` — the module already imports `cachekey` for `load()`
elsewhere, so no new import was needed. `allsweep.py` was **not** touched: it is not in this
run's owned-files list, so a follow-up task was spawned instead (`task_46e8858a`) with the exact
line and fix needed. Verified: pyflakes and import clean on hostcheck.py; a standalone check
confirms the source now calls `cachekey.host_dir(mined)`, the old hand-spelled formula is gone
from that line, and `cachekey.host_dir()` still agrees with what the removed hand-spelled formula
used to compute (belt-and-braces).

## f53381169f79 — DISPROVED — corpus_db.py's CANNED queries do not carry LIMIT clauses in current source

Verified directly: `grep -n LIMIT src/corpus_db.py` finds exactly two hits, both inside a
comment (lines 426, 439) — none inside the `CANNED` dict itself (lines 441-458). Read all nine
query strings: `coverage`, `unaddressed`, `hostless`, `categories`, `types`, `unjudged`,
`evidence`, `refused`, `worst_cited` — none end in `LIMIT 15` or `LIMIT 25`. The order's finding
was true when filed against run33's snapshot (see `handoff/sweep33/AUDIT_batch17_corpus_db.md`,
Q1: "Six of the nine CANNED queries end in LIMIT... Not changed by this run — it is the owner's
rule"), but `corpus_db.py` has since been edited by another session, and the module's own comment
at lines 426-440 now narrates exactly that history and states the resolution ("NO LIMIT. SIX OF
THESE NINE CARRIED ONE... ranking THEN TRUNCATING is forbidden... If a listing is genuinely long,
the answer is `--sql` with the reader's own LIMIT"). `datasette_metadata()` renders `CANNED`
verbatim with no separate hardcoded limit. Per this run's method — "Sweep audits are wrong in
both directions... if wrong, say so... do not fix a non-bug" — no change made. No check added to
checks_batch5.py; see that file's header for why one would be redundant with reading the source.
