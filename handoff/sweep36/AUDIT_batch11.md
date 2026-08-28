# AUDIT — sweep36 batch11

Modules: overnight.py, completeness.py, weave.py, ledger_guard.py, address.py, burgs.py,
catalogue_codex.py, chord_field.py

Read-only audit. No source files were edited.

---

## ledger_guard.py

Read in full, adversarially, per the batch guidance ("can the new containment check be fooled
by an edit that both removes and adds?").

**`_one_insertion(old, new)` (lines 57-87) — adversarial analysis, no bypass found.** The
function proves `p + s >= n` where `p` is the longest common prefix and `s` the longest common
suffix of `old` vs `new`. This is mathematically equivalent to "there exists a split point `k`
such that `old[0:k] == new[0:k]` and `old[k:] == new[len(new)-(n-k):]`" — i.e. exactly "one
contiguous insertion, nothing removed, order preserved." I tried to construct a combined
remove+insert that survives this:

- A deletion anywhere strictly inside `old` (e.g. removing a middle entry `E2` from
  `header+E1+E2+E3` while also inserting a new entry at the top) breaks the prefix match at the
  insertion point AND the suffix match at the deletion point simultaneously, so `p+s < n` unless
  the deleted span is empty. Verified by hand-tracing several placements (delete-from-middle,
  delete-at-tail, replace-in-place) — every one drives `p+s` strictly below `n`.
- The suffix-loop's cap `s < n - p` cannot let `p+s` exceed `n` from the loop itself, and no
  out-of-bounds indexing is possible (`old[n-1-s]` and `new[len(new)-1-s]` stay in range given
  the loop bound and the `len(new) >= len(old)` guard at the top).

So `_one_insertion` genuinely closes the "newest-on-top insertion" gap it was written for
without reopening a remove+add bypass, as far as I could construct one. This is a legitimate,
sound fix — not a tautology.

**Fallback tolerance is real but is documented, deliberate design — flagged as a QUESTION, not
a defect.** When `_one_insertion` correctly rejects a write (because content was actually
removed), `check_since_snapshot()` doesn't fail outright — it falls through to
`_lost_fraction()` and accepts anything losing `<= MAX_LOST_FRACTION` (5%) of the ledger's
lines as "edited rather than appended." This is explicitly there so a person fixing a typo in
an old entry doesn't get blocked (the docstring is candid about the trade-off). But the
mechanism cannot distinguish "typo fix" from "someone deliberately rewrote/removed a handful of
old, load-bearing lines" — both look identical to a line-set diff under the 5% floor on a
473KB+ file (5% of thousands of lines is a lot of room to quietly alter a specific historical
claim without triggering the truncation alarm). Worth a ruling on whether that's an accepted
residual risk or whether a future pass should require exact-append for anything but a tiny
absolute line count, not just a percentage.

**Wiring verified.** `assert_intact()` (lines 373-408) really does call `check_since_snapshot()`
for every `APPEND_ONLY` name (394-397), and `publish.py` really does call
`_LG.assert_intact()` before push, with the ImportError path raising rather than being
swallowed (checked `publish.py` directly — see below).

**Minor: stale line-number tag.** `check_since_snapshot`'s docstring (line 273) says
"`publish.py:622` already calls before every push." The actual call site today is
`publish.py:698: _LG.assert_intact()`. Anchor text: `"which `publish.py:622` already calls
before every push"` (ledger_guard.py:273). This is exactly the "line-number tags that
contradict the code" pattern the project catalogues — low stakes here since the surrounding
prose still names the right function, but it will cost the next reader a grep.

No other issues found in this file. `read_chain()`'s narrowed `except FileNotFoundError` (not
a blanket `except Exception`), `verify_chain()`'s `is not None` fix for the SHRANK check, and
`assert_intact()`'s check on `seal()`'s return value are all real, in-effect fixes — traced each
one to its caller and confirmed no swallowed failure remains silent.

---

## overnight.py

Read in full. Per the guidance ("look for per-cycle state that two threads both write"), I
focused on shared mutable state touched by more than one of: the main cycle loop, the `_keep()`
keeper thread (every 300s), and the `_keep_warm()` thread (every 120s).

**MINOR — `start()`'s log-separator write is not covered by `_guarded_popen`'s lock, so a
keeper/cycle race can still duplicate a job's "started" banner even though the actual double
process-spawn is correctly prevented.** `_guarded_popen` (lines 291-321) is explicitly the
run #36 fix for "two threads that both make [the check-then-spawn] pair of calls for the SAME
job names: the keeper... and the cycle's own standing starts" — and it does correctly close
that race via `_spawn_lock()`. But `start()` (415-451) does its own *unlocked* cheap
`running()` check first (line 424), and only if that returns False does it open the per-job
log file and write a session-separator banner (441-445) — *before* calling `_guarded_popen`.
If the keeper thread and the main loop's top-of-cycle `start()` calls for the same STANDING job
(e.g. `foreman`, `dashboard`) both observe `running() == False` inside the same ~3s
`_proc_lines()` cache window (plausible right after a job dies, since the keeper polls every
300s and the main loop restarts STANDING jobs at the top of every lap), both threads will open
independent handles to the *same* log file and both write a `"=== {name} started ..." ` banner,
even though `_guarded_popen`'s lock guarantees only one of them actually spawns a process. The
loser's `start()` call still returns `None` and closes its handle (447-450), so no data is
corrupted — but the log now shows two start banners for one real start, which matters in this
project specifically because `state/*.log` is the evidence base multiple incidents in this same
file's own docstrings were reconstructed from (see the `name_rc()` docstring on why bare exit
codes and misleading timestamps have cost real investigation time here).

Anchor text: `def start(name, args, logfile):` (overnight.py:415) and the unlocked precheck at
`if running(os.path.basename(args[0])):` (overnight.py:424), contrasted with the authoritative
locked check inside `_guarded_popen` (overnight.py:312-315).

**Minor/style, not a bug in effect:** `_guarded_popen` sets `_PROCS["at"] = 0.0` (line 320)
without holding `_PROCS_LOCK`, while `_proc_lines()` (104-127) is the only other
reader/writer of `_PROCS` and does hold that lock. CPython's GIL makes the single dict-item
assignment atomic, and forcing the timestamp to `0.0` is safe regardless of any interleaving
(it can only make the next cache check *more* eager to refresh, never less), so I don't believe
this can produce a wrong `running()` answer — flagging only as inconsistent locking discipline
against the module's own stated pattern, not a functional defect.

Everything else in the two background threads (`_keep`, `_keep_warm`) only touches
`_PROCS`/`_REACH`-style caches guarded the way the module documents, or state private to that
thread (`_gl` set once before the loop). `history`, `idle`, and `snap` in `main()`'s cycle loop
are touched only by the main thread. No other cross-thread write race found.

---

## address.py

Read in full against Hard Rule 2 ("an unknown source cannot silently acquire a real-looking
address"). `spine_code_for()` has four fallback stages after the exact match: normalized
letter-equality, a "most specific wins" bidirectional substring match (already hardened against
the historical "DC"/"Sword Coast Adventurer's Guide" false-positive per the file's own
comments), a word-order-independent token-overlap fallback, then `"UNASSIGNED"`.

**MAJOR (latent, not yet triggered) — the token-overlap fallback's coverage formula lets a
short Acquisitions-Index entry hijack an unrelated title.** Lines 127-140:

```python
target_tokens = _token_set(source_name)
...
for name, code in codes.items():
    name_tokens = _token_set(name)
    ...
    overlap = len(target_tokens & name_tokens)
    coverage = overlap / min(len(target_tokens), len(name_tokens))
    if coverage >= 0.8 and overlap > best_overlap:
        best, best_overlap = code, overlap
```

`coverage` is normalized by `min(len(target_tokens), len(name_tokens))`, not by
`len(target_tokens)`. When the *index* entry is short (1-2 significant tokens), `min()` is
dominated by the index side, so `coverage` hits `1.0` as soon as the index entry's own (few)
tokens all appear *anywhere* in the target title — no adjacency, no order, and no accounting
for how much of the target's own content is unrelated padding. I measured the actual
`data/CHARTER_SPINE_CODES.json`: **125 of 220 entries (57%) have 2 or fewer significant
tokens** after filler-stripping — e.g. `"Alien"` → `II.N`, `"Doom"` → `II.N.2`, `"Dune"` →
`II.F.6`, `"Halo"` → `II.F.4`, `"Diablo"` → `II.L.3`, `"DC"` → `II.D.2`. Any future/unassigned
source whose title merely contains one of those words as a token — regardless of what the
source actually is — would score `coverage=1.0` against that entry and silently receive its
spine code instead of falling through to `"UNASSIGNED"` for owner sign-off. This is exactly the
invented-address shape Hard Rule 2 forbids, and it is the same failure class the file's own
"MOST SPECIFIC WINS, NOT FIRST-IN-FILE" fix (lines 94-114) closed for the substring stage —
just still open one branch further down, in the token-overlap fallback.

**Verified this has NOT actually mis-fired on the current 215-source roll.** I instrumented
`spine_code_for` to find every roll entry that resolves *only* via the token-overlap branch
(i.e. the earlier exact/norm/substring stages found nothing) and inspected what each one
matched:

```
'all Battlefield'                 -> II.I.2  (index: 'Battlefield (all)')
'all Black Ops'                   -> II.I.1  (index: 'Black Ops (all)')
'all Bloons TD'                   -> II.M.3  (index: 'Bloons TD (all)')
'all Creeper World'               -> II.M.2  (index: 'Creeper World (all)')
'Eastern astrology (BaZi, ...)'   -> VII.6   (index: 'Astrology, Western & Eastern (...)')
'all Elder Scrolls'               -> II.L.2  (index: 'The Elder Scrolls (all)')
'all Fallout'                     -> II.J.1  (index: 'Fallout (all)')
'major live-action Disney films'  -> II.O.3  (index: 'Disney (major live-action films)')
'all Metro'                       -> II.J.3  (index: 'Metro (all)')
'all Modern Warfare'              -> II.I.2  (index: 'Modern Warfare (all)')
'all Pixar films'                 -> II.O.2  (index: 'Pixar (all films)')
'the Skate games'                 -> II.P.3  (index: 'Skate games (...)')
'the Solomonic tradition (...)'   -> III.11  (index: 'Solomonic tradition (...)')
'War Thunder + World of Tanks...' -> II.F.8  (index: 'War Thunder / World of Tanks...')
'Western astrology'               -> VII.6   (index: 'Astrology, Western & Eastern (...)')
'The Amethyst / Cockroach King...'-> II.A.10 (index: 'Amethyst / Cockroach King (...)')
```

All 16 are genuine near-paraphrases of their matched entry (word-order variants, "all X" vs
"X (all)"), not false hits — so no live misassignment exists today. But the safety of this
branch is entirely a property of what happens to be on the current 215-item roll, not a
property of the code: it is a latent single-shared-word collision waiting on the next
unassigned source that happens to contain "Alien", "Doom", "Halo", "War", "Diablo", etc.
Recommend either requiring `overlap >= 2` or normalizing `coverage` by `len(target_tokens)`
(the candidate side) rather than the smaller of the two, matching the "most specific wins"
philosophy already applied one stage up.

No other issues found — `promote()`'s promotion-only asymmetry, `tier_for()`'s floor ladder,
and `build_address()`/`placeholder_shelfmark()` all check out against Hard Rules 2 and 4.

---

## weave.py

Read in full.

**MAJOR — discarded write verdicts in `main()`'s `--write` branch (lines 480-494).** All three
`silence.write_json()` calls have their boolean return value thrown away:

```python
silence.write_json(OUT_GROUPS, {"threshold": thr, "groups": groups}, indent=2, ensure_ascii=False)
silence.write_json(OUT_RESOLVED, resolved, indent=2, ensure_ascii=False)
silence.write_json(OUT_GRAPH, {...}, indent=2, ensure_ascii=False)
print("\nwrote CONTINUITY_GROUPS / RESOLVED_ENTITIES / SHARED_STAGE_GRAPH_IDF")
```

`silence.write_json` (src/silence.py:358-390) returns `True`/`False` — `False` specifically
when `replace_retry` was denied every attempt (Windows, a reader holding the target open),
which its own docstring says is "the established behaviour here," i.e. an expected, real
failure mode, not a hypothetical one. `weave.py` ignores the verdict for all three files and
prints a success line unconditionally. If any of the three renames is denied (plausible: these
are exactly the kind of `data/` files other modules — `weave_index.py`, `resonance.py`,
`cosmology_graph.py`, per the comment two lines above — hold open on their own clocks), the run
reports success while one or more of `CONTINUITY_GROUPS.json` / `RESOLVED_ENTITIES.json` /
`SHARED_STAGE_GRAPH_IDF.json` silently keeps its stale prior content. This is catalogue item #5
("a discarded verdict") verbatim, in the same file whose own comment two lines above shows the
author is aware of the pattern (`# ATOMIC, and the file handles now actually close...`) — the
atomicity was fixed, but the caller-side verdict check was not carried through to `main()`.

No other issues found in `weave.py`. The complete-linkage `components()` clustering, the
permutation null (`null_threshold_surprisal`), the "NO CAP" comments on `shared[p].append(k)`
in both `pair_weights` and `surprisal_pair_weights` (verified: nothing slices these lists), and
`filtered_index`'s mechanic/rules-voice gating all check out. `pair_weights()` is confirmed
genuinely dead code per its own docstring (no caller in `weave.py`, `pipeline.py`, or
`tiers.py` besides the def itself) — already reported per house doctrine, not re-filed here.

---

## completeness.py

Read in full. This module already carries the marks of several prior hardening passes
(atomic `land()`, `SHRINK_FLOOR`, per-mode unreachable-host handling) — most of the obvious
defect classes have already been closed here.

**MINOR — fixed-name temp file shared across concurrent worker threads (the exact "two writers,
one `.tmp` name" pattern from the batch catalogue).** `category_size_probe()` (108-145) and
`category_size_probe_host()` (174-220) both cache into the same on-disk file,
`state/category_sizes.json` (`_CS_CACHE_P`), via:

```python
tmp = _CS_CACHE_P + ".tmp"
with open(tmp, "w", encoding="utf-8") as f:
    json.dump(cache, f)
silence.replace_retry(tmp, _CS_CACHE_P)
```

— a *fixed* temp filename with no PID/thread disambiguation, unlike `silence.write_json`'s
`"%s.%d.%d.tmp" % (path, os.getpid(), threading.get_ident())` used elsewhere in this same
project specifically to prevent this collision. `audit()` (329-546) calls `work()` — which
calls whichever of the two probe functions applies per source — via
`ThreadPoolExecutor(max_workers=workers)` (default 6, line 540), so multiple threads probing
*different* sources concurrently can (and, at default concurrency, likely do) race on this one
`.tmp` path: one thread's `open(tmp, "w")` can truncate another's in-flight write, and whichever
`replace_retry` runs first can install a half-written or truncated cache file. Both write sites
also read-modify-write the *same* in-process `_CS_CACHE["d"]` dict object (`_cs_load()` returns
a shared reference) without a lock, so an update from one thread can be lost if another thread's
`cache[k] = ...` / dump interleaves with it.

Blast radius is limited and mostly self-healing: `_cs_load()` wraps its own read in
`except Exception: pass` (97-105, explicitly marked "silence-exempt: no cache yet is the normal
first state"), so a corrupted cache file is simply treated as empty on the next process start,
and the cache write itself is wrapped in `try/except` that only calls `silence.note` on
failure — it cannot crash the audit or corrupt `COMPLETENESS.json` (which is written separately,
correctly, through the hardened `land()`). Rated MINOR rather than MAJOR for that reason, but
it is a live instance of the pattern the batch guidance called out, in a file that runs under
real concurrency (`ThreadPoolExecutor`) by construction.

Anchor text: `tmp = _CS_CACHE_P + ".tmp"` (completeness.py:139 and :214, identical in both
functions).

No other issues found. `land()`'s three-layer guard (empty-file refusal, `SHRINK_FLOOR`,
and the `replace_retry` verdict check with a loud stderr message) is a model of the "discarded
verdict" fix done correctly — checked it end to end and it is genuinely in effect, including
returning a non-zero exit from `main()` when the write is denied.

---

## burgs.py

Read in full. No issues found.

Checked specifically for a silent cap given the module computes and can print/write a
per-world settlement roster: `burgs_for(world_seed, features, limit=None)` accepts an optional
`limit`, but the only production caller, `main()` (line 207:
`bs = burgs_for(seed, w["features"])`), never passes it — the full rank-size roll is always
computed and written (`--write` dumps `per_world` unsliced through `silence.write_json`, whose
return value IS checked here, lines 260-267, with a correct not-written message on denial). The
`limit` keyword is exercised only by `verify_math.py`'s test suite (`BG.burgs_for(424242, _f,
limit=3)` etc.) for cheap sampling during tests, which is legitimate — grep confirms no
production call site passes it. The CLI's own `--limit` only slices the console *sample table*
print for `w0` (one world, for human reading), not the underlying data or the write.

The historical "SAMPLE" naming bug (console message drifting from what was actually written)
is already fixed and the message is now derived from `len(per_world)` rather than hardcoded.
`GENERATORS` (the display-string dict flagged dead in six prior sweeps) is now genuinely wired
into the sample table print (line 231) — verified it is in fact reachable from `main()`.

---

## catalogue_codex.py

Read in full.

**MINOR — discarded write verdict on the roll file, inconsistent with the per-record write two
lines above.** `main()`, line 223:

```python
silence.write_json(ROLL, roll, indent=2, ensure_ascii=False)
```

The return value is discarded. Contrast with the per-record write immediately above it in the
loop (211-215), which correctly gates on the verdict:

```python
if not _P.write_record_catalogue(
        os.path.join(RECORDS, slug(r["name"]) + ".json"), rec):
    print(f"      -> WRITE DENIED {r['name']}; roll left untouched", flush=True)
    continue
r["entry_count"] = len(rec["entries"])
r["status"] = "catalogued"
```

So each individual record write is checked and skipped-with-a-message on denial, but the final
`SWEEP_ROLL.json` write that persists all of this run's `entry_count`/`status` bookkeeping is
not. If it is denied (a reader holding `SWEEP_ROLL.json` open — plausible; it is described
elsewhere in this same file's own comment as a file "four scripts write"), the run prints
nothing about it and exits looking clean, while the roll on disk keeps stale `entry_count: 0`
rows for sources whose records were, in fact, just written correctly to `data/records/`. Net
effect on a denial is redundant recatalogue work next run rather than data loss (the record
files themselves are safe), which is why this is MINOR rather than MAJOR, but it is the same
discarded-verdict shape as the weave.py finding above, in the same run.

**QUESTION / latent, not yet triggered — the section-matching substring fallback keeps the
non-"most-specific-wins" shape address.py was rewritten to fix for the same bug class.**
Lines 145-149:

```python
if not title:
    for k, t in sec_by_norm.items():
        if n and (n in k or k in n):
            title = t
            break
```

This is a bidirectional substring test that returns on the *first* dictionary-order hit, guarded
only by an exact-match check one stage earlier (138-144, whose own comment names the risk
explicitly: "a short source name can bind to whichever unrelated section happens to contain it
before its own section is reached... No live collision was found, which is the moment to add
the guard"). That comment is accurate as far as it goes — I re-verified it: instrumenting the
matcher against the live `THE_PRIME_OMNIVERSE_CODEX.md` (64 sections) and `data/SWEEP_ROLL.json`
(215 rows), **zero** roll entries currently have more than one candidate section match. But the
guard actually added was only the exact-match short-circuit, not a most-specific-wins scoring
pass — the underlying order-dependent substring ambiguity `address.py`'s "MOST SPECIFIC WINS,
NOT FIRST-IN-FILE" fix (address.py:94-114) was written to close for the identical failure shape
(there: `"DC"` swallowing `"Sword Coast Adventurer's Guide"`) is structurally still present
here, one guard short of it. Lower stakes than address.py's finding (this only affects the
owner's own homebrew catalogue, a much smaller and slower-growing set of section titles), so
flagging as a question for the next time a new codex section or roll entry is added, not as a
live defect.

---

## chord_field.py

Read in full, and checked whether it is actually dead per the batch guidance ("believed to be
imported by nothing; verify before reporting").

**Verified: chord_field.py is imported by nothing.**

```
$ grep -rn "chord_field" src/ --include=*.py | grep -v "^src/chord_field.py"
src/tempus.py:45:# a fourth hand-copied instance of quantities already declared in cosmography.py, chord_field.py,
```

That is the only hit anywhere in `src/`, and it is a comment in `tempus.py`, not an import or a
call. No `import chord_field` / `from chord_field import` exists anywhere in the tree. None of
its public functions (`total_beta`, `per_system_beta_without_unification`, `landauer_floor`,
`recoil_momentum`, `recoil_velocity`, `critical_power_self_focus`) nor `ADJUDICATIONS` itself
has a caller outside this file.

**This is not a new finding — it is already filed and open.** `HANDOFF.md:255` carries it
verbatim from sweep34: `` `7e360eaec3a6` **MINOR** SWEEP34_FINDING — chord_field.py is never
imported anywhere and none of its public functions has a caller. `` It has also been noted
across sweeps 22-35's `AUDIT_batchNN.md` files repeatedly (batch14/15/16 in several rounds).
Re-confirming it here per the batch instructions rather than re-filing it as new.

**Framed as a question about intent, per the guidance, since it may be deliberate.** The module
reads as a genuinely finished, self-contained piece of theoretical scaffolding — a fully worked
adjudication table (six named laws, each with what ki/shrinking demand, what real physics
already permits, what must be declared, and a discriminating experiment) plus small pure
helper functions (`landauer_floor`, `recoil_momentum`, `critical_power_self_focus`) that read
like they were built to be called from somewhere that computes per-power-system beta costs or
runs the recoil/Kerr-threshold checks against actual attested feats — e.g. from
`pipeline.py`'s Assay/beta-cost machinery, or from `verify_math.py` as a discriminator check.
Nothing currently calls it. Two readings seem live: (a) it is reference/design material —
the charter's own I.7 Chord claim made checkable by a person, not by code, in which case
"imported by nothing" is simply correct and expected; or (b) it was meant to feed
`total_beta()`/`per_system_beta_without_unification()` into the Transgression-axis (β) scoring
`pipeline.py` or the Assay worksheet actually uses, and that wiring was never done. Worth an
owner ruling on which, since six sweeps re-finding the same MINOR without a ruling either way
is itself a small instance of "a decision recorded where nobody reads it."

---

## Modules I could NOT read

None. All eight modules in this batch (overnight.py, completeness.py, weave.py,
ledger_guard.py, address.py, burgs.py, catalogue_codex.py, chord_field.py) were read in full.
