# Net staged by run #36 — THE DISCARDED WRITE VERDICT

**Merge target:** `src/drill.py` (not edited here; it was owned by another agent this shift).
**Status on merge: RED — 46 sites flagged** at 2026-08-27, none of them in the ten modules this
run repaired. Read "Where it starts" below before merging: this net is not a ratchet you can drop
in green, and the number moves.

## The defect

`silence.write_json(...)` and `silence.replace_retry(...)` **return whether the write LANDED.**
They are documented to: "Returns True if the file landed. Never raises on a denied replace:
`replace_retry` records it and the caller's write lands next round." On Windows the atomic
rename is DENIED for as long as any reader holds the target open, and this project's state files
all have readers on their own clocks — the dashboard polls records, standards scans readfeats,
`generate.py` reads the manifest. One such collision took an assay worker down mid-batch on
2026-08-23 (WinError 5). This is routine here, not exotic.

A call site that throws that verdict away and then prints `wrote X` or returns 0 is not merely
unhelpful. It **reports a write that did not happen**, the previous file stays on disk, and
every downstream consumer trusts it. The run looks identical to a successful one. This is the
house's own standing lesson — *a check that cannot fail looks exactly like a check that passed* —
arriving one layer down, at the write instead of the check.

The whole-tree sweep found the same shape in roughly ten modules independently. Ten independent
patches is a coincidence; a net is the end of it.

## The guard the net asserts

> Every call to `silence.write_json` / `silence.replace_retry` — or to a module-local wrapper
> that returns one — must have its return value **consumed**: assigned, tested, returned, or
> passed on. A bare expression statement discards it.

That is a syntactic property, which is the point: it is decidable, it cannot be argued with, and
it does not depend on anyone remembering the Windows rename behaviour at 2am.

## Why the parse tree, not the file text

Same reason as the run #36 `roll.out_of_scope` net. A grep for `silence.write_json` matches the
paragraph explaining why a write is atomic just as happily as the call — and these call sites are
*heavily* commented, precisely because they were repaired once already. Prose about a guard
reliably outlives the guard. The claim here is "the return value reaches nothing," and only the
tree can answer it.

## The net

Uses drill's existing `_srcdir()` (so it can be shown going red against a doctored tree) and the
`net(area, name, attack, expectation)` convention where the attack returns True for HELD.

```python
# --------------------------------------------------------------------------------------------
# THE DISCARDED WRITE VERDICT (run #36).
#
# `silence.write_json` and `silence.replace_retry` return whether the rename LANDED and never
# raise on denial. A bare-expression call throws that away, and the caller then reports success
# for a file that did not change. Found in ten modules independently by the run #36 sweep;
# repaired there, and netted here so the eleventh cannot arrive quietly.
_VERDICT_RETURNING = ("write_json", "replace_retry")

# The ALLOWLIST, and it fails CLOSED in both directions. Key: (file, callee-spelling, first-arg
# source text). NOT line number -- line numbers drift, which is the whole reason the run #36
# sweep had to re-find every site it had been handed. The value is a REASON, and it is
# mandatory: an entry with a blank, missing or placeholder reason BREACHES the net rather than
# silencing the site, so the allowlist cannot become a way to make the net stop talking. A stale
# entry -- one matching no site in the tree -- also breaches, because an allowlist nobody prunes
# is a list of permissions for code that no longer exists.
_DISCARDED_VERDICT_ALLOWED = {
    # ("dashboard.py", "silence.write_json", "HISTORY"):
    #     "Rolling 24h movement sample, rewritten by every /api/state poll (seconds apart) "
    #     "inside a try/except that already returns [] on any failure. A denied replace is "
    #     "re-attempted by the next poll before any reader could act on the gap, and nothing "
    #     "downstream treats HISTORY as authoritative. NOT PRE-APPROVED -- written here as the "
    #     "worked example of what an acceptable reason looks like. The owner of dashboard.py "
    #     "decides whether it is true.",
}

_ALLOW_PLACEHOLDERS = ("", "tbd", "todo", "n/a", "na", "?", "see above", "obvious")


def _verdict_wrappers(tree):
    """Module-local functions that RETURN a silence write verdict, e.g. `scout._land`.

    One level deep, deliberately. `hostcheck._land`, `scout._land` and `runguard._land_claim`
    are all `return silence.write_json(...)` one-liners, which is the shape that actually
    recurs. Deeper indirection is named as a known gap in the staging note rather than guessed
    at -- a net that half-follows a call chain is worse than one that says where it stops.
    """
    out = set()
    for fn in ast.walk(tree):
        if not isinstance(fn, (ast.FunctionDef, ast.AsyncFunctionDef)):
            continue
        for r in ast.walk(fn):
            if not isinstance(r, ast.Return):
                continue
            vals = (r.value.elts if isinstance(r.value, ast.Tuple)
                    else [r.value] if r.value is not None else [])
            for v in vals:
                if isinstance(v, ast.Call) and _dotted(v.func).split(".")[-1] in _VERDICT_RETURNING:
                    out.add(fn.name)
    return out


def _dotted(f):
    """`silence.write_json` for an Attribute chain, `_land` for a bare Name, "" otherwise."""
    parts = []
    while isinstance(f, ast.Attribute):
        parts.append(f.attr)
        f = f.value
    if not isinstance(f, ast.Name):
        return ""
    parts.append(f.id)
    return ".".join(reversed(parts))


def _discarded_verdict_sites(srcdir=None):
    """-> [(filename, lineno, callee, first-arg-text)] for every discarded write verdict."""
    srcdir = srcdir or _srcdir()
    found = []
    for fname in sorted(os.listdir(srcdir)):
        if not fname.endswith(".py"):
            continue
        try:
            with open(os.path.join(srcdir, fname), encoding="utf-8") as fh:
                text = fh.read()
            tree = ast.parse(text)
        except (OSError, SyntaxError):
            # FAIL CLOSED: a file the net cannot read is not a file the net has cleared.
            found.append((fname, 0, "<unparseable>", ""))
            continue
        local = _verdict_wrappers(tree)
        for node in ast.walk(tree):
            if not (isinstance(node, ast.Expr) and isinstance(node.value, ast.Call)):
                continue          # an Expr statement IS the discard: nothing consumes its value
            name = _dotted(node.value.func)
            if not name:
                continue
            tail = name.split(".")[-1]
            if not (tail in _VERDICT_RETURNING or (name == tail and tail in local)):
                continue
            args = node.value.args
            target = _dotted(args[0].func) if args and isinstance(args[0], ast.Call) else (
                ast.unparse(args[0])[:60] if args else "")
            found.append((fname, node.lineno, name, target))
    return found


def _no_write_verdict_is_discarded():
    """A write nobody checked is a write nobody can say happened.

    `silence.write_json` and `silence.replace_retry` RETURN whether the rename landed, and on
    Windows that rename is denied for as long as any reader holds the target open. Ten modules
    called them as bare statements and then printed "wrote X" -- reporting, every time, a file
    that had not changed. The net is syntactic on purpose: the verdict must reach SOMETHING.
    """
    sites = _discarded_verdict_sites()

    # Arm 1 -- every allowlist entry must carry a real written reason.
    for key, why in _DISCARDED_VERDICT_ALLOWED.items():
        if not isinstance(why, str) or why.strip().lower() in _ALLOW_PLACEHOLDERS or len(why.strip()) < 40:
            return False

    # Arm 2 -- no stale permissions. An allowlist entry matching nothing is pruned or explained.
    live = {(f, callee, target) for f, _ln, callee, target in sites}
    if set(_DISCARDED_VERDICT_ALLOWED) - live:
        return False

    # Arm 3 -- the finding itself.
    return not [s for s in sites if (s[0], s[2], s[3]) not in _DISCARDED_VERDICT_ALLOWED]


net(a, "no module discards a silence write verdict",
    _no_write_verdict_is_discarded,
    "write_json/replace_retry return whether the rename LANDED; a bare call reports a write "
    "that may not have happened")
```

`ast` and `os` are already imported in `drill.py`. `ast.unparse` needs 3.9+; the tree is on
miniconda 3.11+.

## Showing it refuse — done, 2026-08-27

Not proposed: **run and watched refusing**, with the code above copied out verbatim and
`_srcdir()` stubbed. All four behaviours confirmed against the live tree:

| probe | result |
|---|---|
| Arm 1 — allowlist entry with reason `"todo"` | BREACHED (the placeholder does not silence the site) |
| Arm 2 — allowlist entry matching no live site | BREACHED (stale permission refused) |
| Arm 3 — allowlist entry with a real reason | clears exactly its own site, and only that one |
| regression probe — `genre.py`'s repaired gate reverted to a bare call in a temp copy of `src/` | CAUGHT, named `genre.py`, count +1 |

(The probe run's baseline was 47; the tree had moved to 46 by the time the site table below was
regenerated minutes later. The deltas are what the arms prove, not the absolute figures.)

The regression probe is the one that matters: it shows the net catching the exact defect this run
removed, in a module that is currently clean, so the net is known to refuse and not merely known
to be green.

## Where it starts: RED, 46 sites

Measured 2026-08-27 against `src/` with an empty allowlist. **None are in the ten modules run
#36 repaired** (`genre`, `manifest_builder`, `cosmology_graph`, `weave`, `catalogue_codex`,
`catalogue_models`, `halo`, `wh40k`, `zfighters`, `scout` — all now consume their verdicts).

**Re-measure before merging; do not trust this number.** It moved four times during this run
alone — 57 → 44 → 43 → 47 → 46 — because other agents were editing `src/` in parallel, some repairing
this shape and at least one (in `hostcheck.py`, 1 → 5) adding sites while doing other work. That
volatility is itself the argument for the net: the shape is still being *introduced*, by people
who are not thinking about writes at all. `_discarded_verdict_sites()` above is standalone —
call it with a `srcdir` and it needs nothing else from `drill.py`.

Line numbers were accurate at the moment of the scan and have already drifted in the
actively-edited files; the file names have not.

| file | line | call |
|---|---|---|
| address_space.py | 382 | `silence.write_json(out, ...)` |
| allsweep.py | 556 | `silence.write_json(OUT, {"at": time.time(), ...)` |
| axis_correlation.py | 189 | `silence.write_json(OUT, doc, indent=2, sort_keys=True)` |
| cascade_bridge.py | 691 | `silence.write_json(UNRECOGNISED, rows, ...)` |
| catalogue_web.py | 86 | `_sil.replace_retry(tmp, ROLL)` |
| codewatch.py | 321 | `silence.write_json(LEDGER, doc, indent=2)` |
| completeness.py | 144 | `silence.write_json(_CS_CACHE_P, snap, indent=None)` |
| corpus_db.py | 525 | `silence.write_json(path, doc, indent=2)` |
| dashboard.py | 402 | `silence.write_json(HISTORY, hist)` |
| feats.py | 541 | `silence.replace_retry(tmp, HOSTS)` |
| feats.py | 1188 | `silence.replace_retry(tmp, path)` |
| feats.py | 1208 | `silence.write_json(path, ev, ...)` |
| generate.py | 58 | `silence.write_json(full, obj, indent=2)` |
| gpu_lane.py | 273 | `silence.replace_retry(tmp, path)` |
| gpu_lane.py | 327 | `silence.replace_retry(tmp, path)` |
| grounding.py | 314 | `silence.write_json(p, out, ...)` |
| health.py | 680 | `silence.write_json(PREFLIGHT_STAMP, ...)` |
| hostcheck.py | 736 | `_land(UNFIT, unfit)` |
| hostcheck.py | 747 | `_land(OUT, results)` |
| hostcheck.py | 857 | `_land(fp, r, sort_keys=False, ensure_ascii=False)` |
| hostcheck.py | 885 | `_land(PURGED, prev)` |
| hostcheck.py | 993 | `_land(ROSTERS, {r["source"]: r for r in out})` |
| identity.py | 231 | `silence.write_json(CACHE, inv, ...)` |
| ingest_doc.py | 102 | `silence.write_json(os.path.join(d, "pages.json"), out, ...)` |
| ingest_doc.py | 115 | `silence.write_json(HOSTS, hosts, ...)` |
| ingest_doc.py | 287 | `silence.replace_retry(tmp_state, state_p)` |
| navtree.py | 267 | `silence.write_json(audit_out, {"count": ..., "problems": ...}, ...)` |
| navtree.py | 275 | `silence.write_json(OUT, data, ...)` |
| overwatch.py | 168 | `silence.replace_retry(LEDGER, LEDGER + ".corrupt")` |
| overwatch.py | 202 | `silence.replace_retry(tmp, LEDGER)` |
| overwatch.py | 611 | `silence.replace_retry(_tmp, REPORT)` |
| pantheon.py | 261 | `silence.write_json(OUT, out, ...)` |
| pipeline.py | 212 | `silence.replace_retry(tmp, STATE)` |
| pipeline.py | 1674 | `silence.replace_retry(tmp, HANDOFF)` |
| policy.py | 168 | `silence.write_json(REPORT, {...evaluations...}, ...)` |
| read.py | 648 | `silence.replace_retry(tmp, p)` |
| read.py | 953 | `silence.write_json(QCACHE, d)` |
| reference.py | 347 | `silence.write_json(OUT, out, ...)` |
| retry_synthesis.py | 71 | `silence.write_json(SIDE, merged, ...)` |
| standards.py | 1305 | `silence.replace_retry(tmp, JOB_WATCH)` |
| sweep_plan.py | 163 | `silence.replace_retry(tmp, p)` |
| sweep_plan.py | 186 | `silence.write_json(COVERAGE, data, ...)` |
| tiers.py | 355 | `silence.write_json(out, charted, ...)` |
| weave_index.py | 335 | `silence.write_json(OUT_INDEX, ...)` |
| weave_index.py | 337 | `silence.write_json(OUT_CAND, candidates, ...)` |
| withdraw_chapters.py | 170 | `silence.write_json(.../catalog.withdrawn.json, withdrawn, ...)` |

**`hostcheck.py`'s five are the wrapper rule earning its keep.** At the first scan of this run it
had ONE site, a bare `silence.replace_retry(tmp, path)`. Someone then correctly refactored those
writes behind a local `_land()` helper — and every one of the five call sites discards what
`_land` returns. A net that only knew the two `silence.*` spellings would have watched that file
go from one violation to five and reported an improvement.

Several sites look load-bearing on sight and should be read before anyone reaches for the
allowlist — `overwatch.py:168` (`LEDGER -> LEDGER.corrupt`, the quarantine move that `health.py`
gates correctly in its own copy of the same code), `pipeline.py:212` (STATE, "readers poll this
file", per its own comment), `generate.py:58`, `standards.py:1305`, and `weave_index.py:335/337`
— which read the very artifacts `weave.py` writes, so until this shift both halves of that join
were discarding their verdicts.

## Merging it while it is red

`drill.py`'s contract is that a BREACHED net is an OWNER-level event that halts the library, so
merging this as-is stops everything. Three honest options, in preference order:

1. **Repair first, merge green.** ~46 sites, mostly the same three-line change; the ten this run
   did took one shift between them. This is the option the repaired modules argue for.
2. **Seed the allowlist with every current site, each carrying a real reason**, and let the net
   catch only the next one. Arm 1 makes this expensive on purpose — 46 written justifications is
   a lot of typing for a defect that mostly should just be fixed — and the reasons would be
   fiction for the load-bearing ones above. Recorded as available, not recommended.
3. **Merge as a RATCHET:** replace Arm 3 with `len(unallowed) <= _DISCARDED_VERDICT_CEILING`,
   set the ceiling to today's count, and lower it as sites are repaired. Starts green, cannot
   get worse, needs no fiction. Note the cost plainly: a ratchet on a *count* lets a newly
   introduced discard hide behind a repaired one, so it is a holding position and not the
   finished net. If it is used, the ceiling belongs in the same ratchet mechanism `drill.py`
   already applies to `liveness.py`'s count.

## Known gaps, stated rather than left to be discovered

* **One level of wrapper.** `_verdict_wrappers` finds functions that directly `return` a
  `write_json`/`replace_retry` call (`scout._land`, `hostcheck._land`, `runguard._land_claim`).
  A wrapper that computes the verdict into a local and returns *that* — `scout._mutate` returns
  `(True, value)` / `(False, last_why)` from a retry loop — is NOT found. There are currently no
  bare `_mutate(...)` statements anywhere in `src/`, so the gap costs nothing today. If it ever
  needs closing, the honest fix is a hand-declared `_NAMED_VERDICT_WRAPPERS` set rather than
  chasing dataflow.
* **Cross-module wrappers.** A wrapper is only recognised inside the file that defines it, so
  `pipeline.write_record_catalogue` (which returns a landed verdict and IS correctly gated by
  its callers today) is not tracked. Same remedy if it becomes a problem.
* **`src/` only, non-recursive.** Matches every other source-shape net in `drill.py`;
  `src/deprecated/` is deliberately out of scope.
* **Consumed but ignored.** `landed = silence.write_json(...)` followed by nothing that reads
  `landed` satisfies this net and is still the same defect. `liveness.py` is the tool that finds
  dead assignments; the two nets are complementary and neither should grow into the other.
