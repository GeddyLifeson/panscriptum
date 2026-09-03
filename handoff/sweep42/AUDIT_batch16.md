# sweep42 batch 16 — audit of binding_health.py, local_agent.py, wiki_source.py, onomast.py,
# worldseed.py, snapshot.py, resonance.py, descending_ladder.py

Read in full: src/binding_health.py (1219 lines), src/local_agent.py (1213 lines),
src/wiki_source.py (690 lines), src/onomast.py (582 lines), src/worldseed.py (467 lines),
src/snapshot.py (363 lines), src/resonance.py (299 lines), src/descending_ladder.py (227 lines).
CLAUDE.md read first.

All eight files carry an unusually high density of already-fixed, already-documented historical
defects (each with its own "order <hash>" and a full post-mortem in the docstring). The findings
below are things NOT already covered by that documentation -- i.e. still-open gaps.

## CONFIRMED DEFECTS

### 1. src/local_agent.py:461-467 — the junction-following fix in `_safe()` re-checks the
DENYLIST on the resolved path, but never re-checks the WRITABLE-surface ALLOWLIST on it

```python
    rel_written = os.path.relpath(full, HERE)
    rel_real = os.path.relpath(real, real_here)
    if os.path.normcase(rel_written) != os.path.normcase(rel_real) and _denied_target(rel_real):
        # It resolved somewhere else INSIDE the project, and that somewhere is protected.
        return None
    return full
```

The file's own DENYLIST/ALLOWLIST design is explicit and load-bearing: "a DENYLIST fails OPEN
... an ALLOWLIST fails CLOSED ... BOTH ARE KEPT ... they fail differently, which is the whole
requirement." The junction-defence comment block above this code (the "SIXTH BYPASS" and
"AND THE JUNCTION FIX WAS INCOMPLETE" passages) walks through fixing `_denied_target` for a
resolved path that disagrees with the written one, but the fix only asks the DENY question of
the resolved path. It never asks the ALLOW question (WRITABLE_PREFIXES / WRITABLE_FILES) of it.

`t_propose_patch` computes its allowlist check afterwards from `rel = os.path.relpath(full,
HERE)` — i.e. from the path AS WRITTEN, not the resolved one. So: a junction that sits under a
writable prefix (`src/`, `prompts/`, `handoff/`) and resolves to any location that is (a) inside
the project, (b) NOT under `.git/`, and (c) not matched by `_denied_target` (module denylist,
`DENYLIST_PATHS = {"config.yaml"}`, or `DENYLIST_PREFIXES = ("data/records/",
"reference/keystone_volumes/", "output/index/", "state/", ".git/")`) passes `_safe()` and is then
fully readable AND writable through `propose_patch`, because the written-path string still starts
with `src/` and clears the allowlist trivially.

Concretely: `DENYLIST_PREFIXES` protects `data/records/` but not `data/` itself — files that sit
directly in `data/` (`WIKI_HOSTS.json`, `HOST_QUARANTINE.json`, `BINDING_HEALTH.json`,
`CHARTER_SPINE_CODES.json`, `SWEEP_ROLL.json`, `CONTINUITY_GROUPS.json`, `ONOMASTICON.json`, …)
are neither in `DENYLIST_PATHS` (only `config.yaml` is) nor under any `DENYLIST_PREFIXES` entry.
A junction such as `src/<name> -> ../data` would let `propose_patch(path="src/<name>/WIKI_HOSTS
.json", ...)` open, edit and write that file directly — corrupting exactly the kind of
CAS-protected registry `binding_health.py` goes to great lengths to protect from concurrent
writers, or `address.py`'s `CHARTER_SPINE_CODES.json` (Hard Rule 2's real spine-code map) —
while every gate in `_gates()` still passes (JSON parse gate + whole-suite `verify_math`, neither
of which validates the *semantics* of an arbitrary data file).

This is not purely theoretical inside this project: `_safe()`'s own comment states "`mutate.py`
junctions `data/`, `prompts/` and `reference/` into its sandbox as a matter of course, so
junctions pointing out of a tree are not hypothetical here; they are a technique this project
already uses" — i.e. the mechanism the gap depends on is one this codebase already employs
elsewhere. The local model's own tool surface (`read_file`, `list_dir`, `grep`, `propose_patch`,
`find_symbol`, `run_check`) cannot itself CREATE a junction, so this is a latent/architectural
gap rather than something reachable purely through a chat prompt today — but it means the
allowlist's own stated guarantee ("anything nobody thought of is refused") is false whenever a
junction is present under the writable surface, which the fifth bypass fix one comment-block up
was specifically trying to close for the deny side only.

**Fix shape**: `_safe()`'s junction branch should refuse whenever `rel_written != rel_real`
UNLESS `rel_real` *also* clears the same WRITABLE_PREFIXES/WRITABLE_FILES test `t_propose_patch`
applies to `rel_written` — i.e. ask the identical three-way question (deny AND allow) of both
spellings, not just the deny half of it.

Confidence: high on the mechanism (traced through the actual code paths); the "how load-bearing"
question (whether such a junction exists on this machine right now) is unverified — I did not
scan the working tree for existing junctions, per the read-only instruction for this audit.

### 2. src/onomast.py:238-265 — `coin_well_formed()`'s final exhaustion fallback can return a
name that is malformed or a duplicate, with only a bare `silence.note`, no `escalation` call

```python
    for salt in range(max_tries, max_tries * 25):
        nm = coin_name(f"{base}|{salt}", register)
        if well_formed(nm) and nm.lower() not in taken:
            return nm
    # Genuinely exhausted: 10,000 deterministic candidates and every one taken or malformed.
    ...
    silence.note("onomast.py:coin-exhausted")
    return coin_name(f"{base}|fallback", register)
```

The function's own docstring names the exact failure this reintroduces: "THE FALLBACK USED TO
ABANDON BOTH INVARIANTS AT ONCE... `well_formed` check and, worse, no `taken` check, so the one
path taken when naming is HARDEST returned a name that could be malformed AND could duplicate a
name already issued. 'Shelfmarks are unique' is one of the 39 standards, and this was the single
code path capable of breaking it silently." That description was written about the OLD one-line
fallback and is presented as fixed — but the new, much-harder-to-reach final fallback (after
~10,400 deterministic tries) is the exact same shape: `coin_name(f"{base}|fallback", register)`
returned with no `well_formed`/`taken` check at all. The comment argues this is deliberate
("refusing to name anything would be the worse failure") — a defensible design call — but the
only trace of an actual uniqueness/well-formedness violation, should this path ever fire, is
`silence.note("onomast.py:coin-exhausted")`, which every other invariant-breaking condition
documented in the codebase's own comments (e.g. binding_health.py's `HOST_QUARANTINE_NOT_
RECORDED`, `LOCAL_AGENT_REVERT_FAILED`) escalates through `escalation.py` at SUPERVISOR or
higher, not merely `silence.note`. A silent `note` is this project's own documented shape for
"benign/expected, no action needed" (see binding_health.py's extensive commentary on the
distinction) — using it for "a hard uniqueness invariant just broke" looks like the wrong channel
for the severity the comment itself describes.

Confidence: medium-high on the code reading; the practical likelihood of ever reaching 10,400
exhausted deterministic candidates in one register is presumably very low, so this is a
low-probability, real-consequence gap.

### 3. src/worldseed.py:456-462 — the `--write` write-denied path prints a demonstrably-false
promise and never fails the exit code, unlike the sibling fix this exact bug already received
elsewhere in the codebase

```python
        if silence.write_json(path, payload, indent=2, ensure_ascii=False):
            print(f"\nwrote {path} ({len(payload):,} row(s))")
        else:
            print(f"\nWRITE DENIED {path} — replace refused; it lands on the next run")
    return 0
```

Two problems, both already-diagnosed-and-fixed elsewhere in this exact codebase but missed here:

1. The message "it lands on the next run" is the precise wording `onomast.py`'s own `main()`
   comment (lines 565-568) calls out as false and already corrected there: "The old wording said
   'it lands on the next run', which is a promise this module cannot make -- it is only true if a
   next run happens." `worldseed.py` still makes that promise.
2. `onomast.py:main()` (and, per its own comment, `genre.py:327-331`, `sevenfold.py:412-415`,
   `wh40k.py:290-295`) were all fixed under "order dc5c92aad5c1, the run #36 discarded-verdict
   ruling 3e65dbed45a6" to return a non-zero exit code when a write is denied. `worldseed.py`'s
   sibling list does not include itself, and indeed it was not fixed: after printing "WRITE
   DENIED", execution falls through unconditionally to `return 0` at the end of `main()`. A
   scheduler or caller gating on the exit code (exactly the discarded-verdict failure mode this
   project has repeatedly hardened against, per Hard Rule -1's fourth property) sees a failed
   `WORLDSEEDS.json` write reported as success.

Confidence: high — directly comparable to a fix the codebase already made to a sibling module,
and the code path is unambiguous (`return 0` is unconditional and outside the if/else).

### 4. src/snapshot.py:333-337 (`listing()`) + 356-357 (`main()`) — a corrupted/unreadable
snapshot manifest is silently indistinguishable from an empty, healthy snapshot in `--list` output

```python
def listing():
    ...
    for sid in sorted(os.listdir(ROOT)):
        try:
            out.append(manifest(sid))
        except Exception:
            out.append({"id": sid, "broken": True})
    return out
...
    for m in listing():
        print("  %-40s %s  %s" % (m.get("id"), len(m.get("took") or []), m.get("label", "")))
```

`listing()` correctly catches an unreadable manifest and marks the row `"broken": True` — but
`main()`'s plain `--list` display never reads that key. For a broken entry, `m.get("took") or
[]` is `[]` (key absent) and `m.get("label", "")` is `""` (key absent), so the printed line reads
identically to a legitimate snapshot that captured zero paths and was given no label — there is
no visible difference between "this snapshot's index cannot be read" and "this snapshot is
empty". This is exactly the failure mode this module's own header argues against at length
("NEVER SILENTLY. A snapshot that fails to take is an OPERATOR-level refusal, not a warning
printed above the destructive step"), reached through the read/list side instead of the take
side. `--verify` (which calls `manifest()` directly rather than going through `listing()`'s
catch) does surface the corruption correctly as `FAILED`; only the plain, no-argument `--list`
path loses the signal. `listing()` also does not call `silence.note` on the caught exception,
unlike the equivalent catches elsewhere in this file and its sibling modules.

Confidence: high — the code is straightforward and the `"broken"` key is provably never read by
the only consumer of `listing()`'s output in this file.

### 5. src/local_agent.py:596-597 — the pyflakes subprocess call inside `_gates()` omits the
`PYTHONIOENCODING=utf-8` env override that every other subprocess call in this file sets

```python
        r = subprocess.run([PY, "-m", "pyflakes", full], capture_output=True, text=True,
                           timeout=120, creationflags=_NO_WIN)
```

Compare to the three sibling subprocess calls in the same file (`t_run_check`, the import-gate
check, and the `verify_math` gate two blocks below this one), all of which pass `env=dict(
os.environ, PYTHONIOENCODING="utf-8")`. This is the exact environment variable this machine's own
documented constraints require ("use PYTHONIOENCODING=utf-8 for any python"). On Windows,
`subprocess.run(..., text=True)` without an explicit encoding decodes stdout/stderr using the
locale's preferred encoding, which is not UTF-8 by default on this machine's codepage; pyflakes
output containing non-ASCII bytes (plausible if a proposed patch touches non-ASCII source text
that pyflakes echoes back in a diagnostic) can raise `UnicodeDecodeError` here. Because this call
sits inside `t_propose_patch`'s enclosing `try/except Exception`, the failure mode is fail-safe
(the patch is reverted and reported as a gate failure rather than landed uninspected) rather than
a bypass — but it is a real inconsistency that could cause spurious reverts of otherwise-good
patches specifically on the machine this kit is built to run on.

Confidence: medium — the encoding mismatch is real and the omission is plainly inconsistent with
every neighbouring call; whether it has actually fired depends on pyflakes ever emitting
non-ASCII bytes on a real run, which I did not test.

## QUESTIONS (may be deliberate; not filed as defects)

### Q1. src/wiki_source.py — `rank_by_size(..., top=N)` and `find_categories(..., limit=N)` still
expose a truncating parameter after ranking

`rank_by_size()`'s docstring and the module's other functions (`category_members`,
`find_categories`) were explicitly hardened against Hard Rule 0 (roster caps removed, `limit`
defaults to `None`/uncapped). `rank_by_size` itself still accepts a `top` kwarg that truncates
the ranked list (`return ranked[:top] if top else ranked`), and none of my eight modules pass a
non-`None` value for it — the only two callers of `rank_by_size` are in `wiki_source.py` itself
(none) and `catalogue_web.py` (outside my scope, not audited here). Whether any caller invokes it
with `top` set for something that is actually a roster (as opposed to, say, picking the largest
candidate categories to explore, which is a legitimate ranking-for-selection use rather than a
roster truncation) is a question for whoever audits `catalogue_web.py`, not something I can
confirm or refute from these eight files alone.

### Q2. src/resonance.py — the whole module is a documented, currently-unwired safety
(`hodge_decompose`'s eta never reaches `custodes.convene()`'s curl-veto)

The module's own header already states this in full ("This module has NO PRODUCTION CALLER...
eta 1.0 is never asserted and the veto is never declined; it is simply never asked... Left as an
OPEN order") and explicitly frames it as the fourth HARD RULE -1 property (a safety that exists
in a file is not a safety that is running). I am not filing this as a new finding since it is
already tracked in-file as open and owner-visible; flagging only so this audit's coverage of
resonance.py is not read as having missed it.

## Modules read in full for this batch
binding_health.py, local_agent.py, wiki_source.py, onomast.py, worldseed.py, snapshot.py,
resonance.py, descending_ladder.py.
