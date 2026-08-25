# Batch 16 — run33
Modules read: local_agent.py (714 lines), wiki_source.py (653 lines), health.py (528 lines),
workorders.py (449 lines, re-read once mid-audit — concurrently edited, see note), navtree.py
(273 lines), catalogue_codex.py (216 lines), retry_synthesis.py (183 lines)

NOTE ON CONCURRENT EDITS: workorders.py grew from 312 to 449 lines between my first and second
read (a new §5 "THE BATTERY" block was added). Line numbers below for workorders.py are from the
449-line version, fetched a second time specifically to keep this report accurate. health.py's
relevant line numbers were re-checked and were unchanged. If either file has moved again by the
time this is read, use the quoted text to relocate each finding.

## FINDINGS

### 1. local_agent.py:565-607, 655-697 — a failed auto-revert is invisible to the run's own audit trail and exit code  [severity: BLOCKING]
`t_propose_patch` writes the file, runs `_gates`, and on failure reverts from the in-memory
`backup`. If that revert write itself raises, the function correctly builds an `ALARM` message
("REVERT FAILED -- %s may be half-written on disk..."), but nothing that reaches a human or the
next process reliably carries it:

- `run()`'s per-call verbose print truncates the JSON result to 110 characters:
  `print("  [%s] %s -> %s" % (fn, json.dumps(args)[:90], json.dumps(res)[:110]), flush=True)`
  Since the dict is built as `{"applied":..., "reverted":..., "error":..., "ALARM":...}`, the
  `ALARM` key is last and near-certain to fall outside the 110-character window once `applied`,
  `reverted` and a real Python exception message are serialised first.
- The `patches` list returned by `run()` (and printed wholesale by `main()`) is populated by
  `log.append({"path": path, "why": ..., "find": ..., "replace": ..., "at": ...})` **before** the
  write is attempted, and is never updated with the outcome. So the final JSON `main()` prints —
  the one artifact meant to be the audit trail — contains only the intent of every patch, never
  whether it applied, reverted, or catastrophically failed to revert.
- `run()`'s "ok" flag and therefore `main()`'s exit code (`return 0 if out.get("ok") else 1`) are
  driven purely by whether the model produced a final answer, not by whether any patch it made
  left the repo in a bad state. A run in which a revert failed can still exit 0.

Net effect: the one path in this file that can leave a bona fide half-written module on disk
with the backup only in memory (already lost once the process exits) has no reliable channel to
a human. This is exactly what the module's own docstring promises cannot happen ("A backup is
written before and restored on ANY failure").

### 2. local_agent.py:461-471 — the JSON/YAML parse-gate is case-sensitive, unlike the hardened `.py` path next to it  [severity: MAJOR]
```python
elif full.endswith(".json"):
    try:
        json.load(open(full, encoding="utf-8"))
    ...
elif full.endswith((".yaml", ".yml")):
```
The `.py` branch immediately above this was explicitly folded to `full.lower().endswith(".py")`
after run #25 found that a case-sensitive extension test let `src/foreman.PY` skip every gate
while still landing on the real `foreman.py` (NTFS is case-insensitive). The exact same shape is
open here: a `.JSON` or `.YAML` file resolves to the same on-disk file as its lowercase name but
silently skips the parse-validation branch, leaving only the whole-suite `verify_math` run as a
backstop (which may not itself parse an arbitrary JSON/YAML file). Not currently exploitable
against real files — `prompts/` and `handoff/` (the writable, non-`.py` surface) hold no
`.json`/`.yaml` files today — but this is the same bypass class the file has paid for five times
already, reopened one branch over from the fix.

### 3. workorders.py:329-338 — quarantined-host orders are never resolved on recovery, contradicting the file's own comment and design principle  [severity: MAJOR]
```python
# 3. quarantined wiki hosts -- one order per host, so each closes on its own recovery
try:
    import binding_health as BH
    q = BH.quarantined()
    for host, rec in sorted(q.items()):
        file_order("HOST_QUARANTINED", "%s: %s" % (host, rec.get("reason", "")),
                   "BOTS", "MINOR", where=host, found_by="binding_health")
    filed.extend([])
except Exception:
    silence.note("workorders.py:bindings")
```
This block only ever *files*. Nowhere does it call `resolve_code("HOST_QUARANTINED", ..., where=host)`
for a host that has dropped out of `BH.quarantined()` (i.e. recovered). Every other block in this
same function (§1, §2, §4, §5, §6) uses the `_fire()` helper, which calls `resolve_code` when its
condition is clean — so the pattern for "close on recovery" exists and is used five times right
next to this one, making the omission look like a straightforward miss rather than a design
choice. Practical effect: once a host is ever quarantined, its `HOST_QUARANTINED` work order sits
open in `state/workorders.json` forever, even after `binding_health` clears it — directly against
the module's own headline claim, "DELETION IS THE POINT... never a growing backlog." (`filed.extend([])`
on the line above is also dead: it appends nothing, so newly-filed HOST_QUARANTINED orders are not
even counted in the `filed` return value that `main()` reports as "N filed/refreshed".)

### 4. workorders.py:305-403 — sweep_detectors()'s six bare `except Exception: silence.note(...)` blocks can throw away a whole detector's result, not just log a class name  [severity: MAJOR]
Each of the six sections (ledgers, liveness, quarantined hosts, secrets, battery, drill-close) is
wrapped in `try: ... except Exception: silence.note("workorders.py:<x>")`. `silence.note` records
the exception *class* to `health.py`'s ledger, which satisfies this project's own "never silent"
convention for exceptions — but it does **not** file or refresh the work order the detector was
trying to report. If, say, `LG.check_all()` itself raises (e.g. a ledger so corrupted the checker
can't even parse it — arguably a worse condition than "not intact") rather than returning a
`bad` list, the `_fire(not bad, "LEDGER_STRUCTURE", ..., "BLOCKING", ...)` call is never reached,
no BLOCKING order is filed, and the only trace is a generic `silent:workorders.py:ledgers` counter
bump in `state/failures.json` — a file nobody in the handler ladder is described as reading. Given
this module is now explicitly "what the whole maintenance process runs on" (per its own header),
a detector that throws instead of returning False is a fault that produces zero work order this
cycle, exactly the "check that cannot fail looks exactly like a check that passed" shape this
project's CLAUDE.md names as its standing lesson.

### 5. wiki_source.py:275-284 — `resolve_wiki()`'s hosts-file read only catches `OSError`, not a corrupt-JSON `WIKI_HOSTS.json`  [severity: MAJOR]
```python
try:
    with open(_hosts_path, encoding="utf-8") as f:
        known = json.load(f).get(source_name)
except OSError:
    silence.note("wiki_source-hosts-read")
    known = None
```
`json.load` raises `json.JSONDecodeError`, a subclass of `ValueError`, not `OSError` — a torn or
corrupted `data/WIKI_HOSTS.json` (a shared file, plausible given `silence.py`'s own documentation
of torn concurrent writes to shared JSON/JSONL state elsewhere in this project) propagates
straight out of `resolve_wiki()` uncaught. The comment immediately above this block explains the
author's intent broadly ("A missing hosts file is tolerable... so only the file operations sit
inside the try"), which reads as meaning "any problem reading this file", but the `except` clause
only covers the open-fails-to-find-the-file case, not the file-exists-but-is-garbage case. Both
call sites (`catalogue_web.py:156` and `:341`) call `resolve_wiki()` with no surrounding
try/except of their own, so this would propagate further (blast radius depends on code outside
this batch).

### 6. health.py:137-148 — the samples ledger has no corrupt-file recovery, despite a comment saying it needs one "more, not less"  [severity: MAJOR]
```python
# Same treatment, and this file needs it MORE than the ledger does, not less: it
# has no .corrupt self-healing path. Once torn, every future flush hits the blanket
# `except` below at the read step and drops its samples silently and permanently --
# the evidence bag going quietly empty and staying that way, with nothing recorded
# anywhere, because the recorder cannot safely record against itself.
stmp = SAMPLES_PATH + ".tmp"
with open(stmp, "w", encoding="utf-8") as f:
    json.dump(old, f, indent=1, sort_keys=True, ensure_ascii=False)
if silence.replace_retry(stmp, SAMPLES_PATH):
    _SAMPLES.clear()
except Exception:
    pass          # the evidence bag must never break the ledger write
```
Compare this to the ledger's own read step a few lines above, which explicitly does the thing
this comment says the samples file needs: on an unreadable `LEDGER_PATH` it renames the wreck to
`.corrupt`, prints a stderr diagnosis, and starts a fresh ledger while still keeping the counts.
The samples block has no equivalent — a corrupt `SAMPLES_PATH` just falls into the blanket
`except Exception: pass` at the very step the comment warns about, with no rename, no stderr
message, nothing. Since most callers of `health.flush()` are one-shot subprocesses (per
`silence.py`'s own docs — the atexit-armed flush), a process whose only flush hits this path loses
its whole ring of failure samples for that run, permanently, with zero diagnostic trace anywhere.
This reads as a known, described, and never-implemented fix rather than an oversight nobody
noticed — the comment is the postmortem for a bug that is still live underneath it.

### 7. health.py:333-355 (check_state) vs :405-418 (reopen_stranded) — the two "is this batch actually stranded" checks disagree about excluded entries  [severity: MAJOR]
`check_state()` counts a batch's un-worked entries as
`sum(1 for e in batch if not e.get("catalogued") and not e.get("excluded"))` — deliberately
excluding `excluded` entries, which by design never get `catalogued: true`.
`reopen_stranded()`, whose entire job is to repair the same "batch closed but has unworked
entries" condition, uses a simpler count that does not exclude them:
```python
missing = sum(1 for e in E[start:start + B] if not e.get("catalogued"))
```
A batch that is fully and correctly settled — every real entry catalogued, only its
deliberately-excluded entries lacking `catalogued: true` — will show `missing > 0` here and be
reopened by `--reopen --go`, even though `check_state()` (right above it in the same file) would
correctly call that same batch settled. Since excluded entries never become catalogued no matter
how many times the batch is reprocessed, a batch with any excluded entries can be repeatedly
"discovered" as stranded and reopened on every future `--reopen` run — wasted local-model spend
re-processing work that was already done, and a misleading "re-opened N batch(es)" report.
`reopen_stranded()` does not use `pipeline.batch_settled()` (the function `check_state()` uses for
its own, more careful UNREACHABLE-vs-QUEUED distinction) at all; it reimplements a strictly weaker
version of the same test.

### 8. catalogue_codex.py:54-67,159 — `TYPE_CATEGORY` is missing two element types that exist in the real codex, both silently mis-filed as "Vessels & Things"  [severity: MAJOR]
Verified directly against `THE_PRIME_OMNIVERSE_CODEX.md`: the codex's "Full Contents" manifests
use `Race Variant` (e.g. line 10754: `Race Variant (7): Mark of Detection; ...`; line 10792:
`Race Variant (2): Draconblood; Ravenite`) and `Background Variant` as real element types, neither
of which is a key in `TYPE_CATEGORY`. `entries.append(..., "category": TYPE_CATEGORY.get(etype.lower(), THINGS), ...)`
means both fall through to the `THINGS` ("Vessels & Things") default — the same default used for
magic items and weapons. `Race` and `Sub Race` are both correctly mapped to `FACTIONS`; their
`Race Variant` sibling (a lineage/heritage variant — people, not objects) is not, and lands under
Vessels & Things instead. `Background` is mapped to `POWERS`; its `Background Variant` sibling is
not, and also lands under Vessels & Things. This is a genuine, data-confirmed mis-categorisation,
not a hypothetical: these exact strings appear multiple times in the source file this module
parses.

### 9. local_agent.py:538-540 — "THE ALLOWLIST RUNS FIRST" comment does not match the actual check order  [severity: MINOR]
```python
# THE ALLOWLIST RUNS FIRST, because it is the one that fails closed. A path outside the
# agent's working surface is refused without any further question -- no denylist entry
# required, and none needed for whatever gets added to this repo next.
if not (any(_rel_l.startswith(p) for p in WRITABLE_PREFIXES)
```
In actual execution order, the module/path `DENYLIST` check (`if denied: return {...}`, around
line 531) runs and can return *before* this allowlist check is ever reached. The comment is
accurate only relative to `DENYLIST_PREFIXES` (which does run after this block), not relative to
the whole function. Harmless in practice — every one of these checks is a pure refusal gate, so
their relative order changes only which error message a caller sees, never whether a write is
allowed — but it is a real contract-drift between the comment and the code in a file whose whole
safety argument rests on precisely and correctly describing what runs when.

### 10. workorders.py:237-256 vs :416-420 — `resolve()` itself does not enforce the "how is required" rule; only the CLI does  [severity: MINOR]
`main()`'s `--resolve` handler refuses an empty `--how` with an explicit message ("A closed order
with no resolution recorded is indistinguishable from one that was deleted to tidy the queue").
The library function `resolve(oid, how, by="")` that it calls does not itself enforce this — it
happily does `rec.update({"resolution": str(how)[:400], ...})` for `how=""` or `how=None`
(`str(None)` = `"None"`). Every current caller (the CLI, and `resolve_code()`'s three callers in
`drill.py`/`escalation.py`-adjacent code) happens to pass a real string, so this is not live today,
but the invariant the module's own design depends on ("deletion is the point, but only with a
recorded reason") lives only in one caller, not in the function that actually deletes the order.

### 11. navtree.py:213-222 — `audit()`'s "child has no node" check cannot survive to report the fault it exists to catch  [severity: MINOR]
```python
for k, v in nodes.items():
    if v["k"]:
        s = sum(nodes[c]["n"] for c in v["k"])          # <- unconditional, crashes on missing c
        if s != v["n"]:
            problems.append(...)
    ...
    for c in v["k"]:
        if c not in nodes:
            problems.append(f"{k}: child {c} has no node")   # <- the check this is about
```
The `sum(nodes[c]["n"] for c in v["k"])` line dereferences every child key in `v["k"]` before the
later loop ever checks whether that key exists in `nodes`. If a child key were ever added to a
node's `"k"` set without a corresponding node being created (the exact condition the second loop
is written to detect), `nodes[c]` raises `KeyError` and `audit()` crashes outright instead of
reporting `"{k}: child {c} has no node"` — which defeats the entire purpose of that check ("Every
claim the terminal makes must be one the data can honour"). Currently unreachable: `build()`
always calls `touch(path)` for a child node in the same iteration, before that child's key is
added to its parent's `"k"` set, so the invariant currently holds by construction. But this is
precisely the shape of check the audit() function is supposed to survive a violation of, and as
written it cannot.

### 12. catalogue_codex.py:126-137 — codex-section matching takes the first substring hit with no preference for an exact or most-specific match  [severity: MINOR]
```python
for k, t in sec_by_norm.items():
    if n and (n in k or k in n):
        title = t
        break
```
Bidirectional substring containment, breaking on the first hit in codex-file order, with no
tie-break toward an exact match or the longest/most-specific overlap. A short or generic roll
source name could bind to an unrelated codex section whose normalised title happens to contain it
(or vice versa). I did not find a live collision — the actual codex's section titles (checked
directly) are mostly distinctive enough that this has probably not fired yet — but the matching
logic itself has no safeguard against it, in a module whose own header explicitly cites
"guessing a wiki... is how 'Curse of Strahd' ended up pointed at the Roblox CURSE Wiki" as the
exact failure shape it exists to avoid for wiki resolution; the same un-guarded fuzzy-match shape
is present here for section resolution.

### 13. retry_synthesis.py:44-48 — `save_side()` is a whole-file overwrite, not a merge, so two concurrent retry runs can clobber each other's progress  [severity: MINOR]
```python
def save_side(d):
    # `silence.write_json`, not a hand-rolled `path + ".tmp"`: the fixed tmp name collides when
    # two processes write at once, and the bare `os.replace` raises on the Windows lock this
    # project hits routinely...
    silence.write_json(SIDE, d, indent=2, ensure_ascii=False)
```
This comment shows the author was already reasoning about two `retry_synthesis.py` processes
writing at once, and fixed the tmp-filename collision (`silence.write_json` embeds pid+thread in
its temp name). It does not fix the read-modify-write race on the *content*: `main()` calls
`side = load_side()` once at startup, then repeatedly does `side[src] = got; save_side(side)`
inside the retry loop. Two concurrent invocations each hold their own separately-growing `side`
dict and each `save_side()` call replaces the whole file with that process's copy — so the second
process's next save silently discards any entries the first process had already persisted (and
vice versa). Nothing in this file prevents or detects a second concurrent invocation.

## QUESTIONS

1. local_agent.py:86-92,548-554 — `DENYLIST_PREFIXES` (`data/records/`, `reference/keystone_volumes/`,
   `output/index/`, `state/`, `.git/`) appears to be entirely unreachable under the *current*
   `WRITABLE_PREFIXES` (`src/`, `prompts/`, `handoff/`): none of the denylist prefixes overlap any
   allowlist prefix, so the allowlist check above it already refuses everything this check exists
   to catch. Is this deliberate defence-in-depth against a future widening of `WRITABLE_PREFIXES`
   (consistent with the file's own "BOTH ARE KEPT... they fail differently" argument), or is it
   dead code that should be flagged? I lean toward deliberate given how carefully this file
   reasons about independent layers, but can't confirm intent from the code alone.

2. retry_synthesis.py:112-145 (`do_merge`) — the guard `if rec.get("synthesis"): skipped += 1; continue`
   checks a `rec` snapshot taken by `PL.records()` at the *start* of the merge loop, not the
   current on-disk state at the moment `PL.write_record(path, rec)` is finally called. If
   `pipeline.write_record`'s merge logic (outside this batch) does not itself prefer an
   already-present disk-side `synthesis` over a caller-supplied one, a `--merge` run racing a live
   pipeline write could still push a stale retried synthesis over a fresher one the pipeline wrote
   in between. Settling this needs `pipeline.write_record`'s merge semantics, which are outside
   this batch's modules.

3. health.py:216 (`check_api_paths`) — every non-Wikipedia host in `F.HOSTS` is bucketed into a
   single "fandom" family and probed at Fandom's `/api.php` path
   (`fams.setdefault("wikipedia" if "wikipedia" in h else "fandom", h)`). Is it guaranteed every
   non-Wikipedia host on the roll is actually a Fandom wiki? `feats.py`, which owns `HOSTS`, is
   outside this batch, so I can't confirm whether a non-Fandom, non-Wikipedia host could exist in
   that map and be silently mis-probed.

## CLEAN
No module in this batch was free of findings, so there is nothing to list here as fully clean.
Every module above was read in full, end to end, including all docstrings and inline comments
(which in this codebase frequently document the exact prior incident a given guard exists to
prevent — several findings above were checked against that history before being written up).
