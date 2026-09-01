# Sweep 40 — Batch 09 audit

Modules read in full: `src/foreman.py` (1738 lines), `src/generate.py` (787 lines),
`src/gpu_lane.py` (620 lines), `src/ledger_guard.py` (509 lines), `src/catalogue_codex.py`
(392 lines), `src/deprecated/catalogue_local.py` (333 lines), `src/render.py` (278 lines),
`src/profile.py` (222 lines).

General note: this batch is unusually heavily audited already — most of these files carry
extensive inline "here's the bug we found and fixed" comments from prior runs. `gpu_lane.py`,
`catalogue_codex.py`, `deprecated/catalogue_local.py` (deliberately frozen, refuses to run),
`render.py` and `profile.py` were read end to end and no new defect was found in any of them
beyond what follows. The findings below are concentrated in `foreman.py`, `generate.py` and
`ledger_guard.py`.

---

## Finding 1 (MAJOR) — `ledger_guard.py`'s continuity protection omits `handoff/HANDOFF.md`,
the one file already burned by exactly this failure mode

**Where:** `src/ledger_guard.py:44-48` (`APPEND_ONLY`, `MIN_BYTES`), and the module docstring
at `src/ledger_guard.py:5-9`.

**The claim:**
```
src/ledger_guard.py:5-9
Every maintenance run is a fresh session with no memory of the last one. What survives is four
files -- `HANDOFF.md`, `BUGS.md`, `NEXT_STEPS.md`, `MAINTENANCE.md` -- and they are the ONLY
thing carrying continuity.
```
```
src/ledger_guard.py:44,47-48
APPEND_ONLY = ("HANDOFF.md",)
MIN_BYTES = {"HANDOFF.md": 20000, "BUGS.md": 8000, "NEXT_STEPS.md": 3000,
             "MAINTENANCE.md": 5000}
```

**Why it's wrong:** `HERE` in this module (`src/ledger_guard.py:36`) resolves to the repo root,
so every one of these names reads/writes `<root>/HANDOFF.md` — the *run journal*. The project
also has a second, distinct file, `handoff/HANDOFF.md`, and its own header says outright what
it is:

```
handoff/HANDOFF.md, lines 1-4
# PANSCRIPTUM — HANDOFF
*Hand-written. `src/pipeline.py` rewrites its own status block below the line; everything above
it is durable and should be read first.*
```

and the root `HANDOFF.md`'s own header (read as data, not code, but it's the project's own
account of the split) says:

```
HANDOFF.md, lines 1-5
# Handoff Log — the maintenance-pass run journal
*One dated entry per maintenance run, newest on top. This is the RUN LOG only; the project's
deep engineering history, doctrine, and architecture live in `handoff/HANDOFF.md` ...*
```

So `handoff/HANDOFF.md` is explicitly billed, by the project's own convention, as the durable
carrier of "the project's deep engineering history, doctrine, and architecture" — arguably
*more* load-bearing for continuity than any of the four files this module actually protects.
And it has already suffered exactly the failure class this module exists to prevent.
`src/pipeline.py:74-77` documents it happening:

```
src/pipeline.py:74-77
# This pointed at handoff/HANDOFF.md, which is also the hand-written document that carries every
# defect this project has found and the reasoning that keeps each one from recurring. The runner
# rewrote it after every completed unit, so running the phases destroyed 629 lines of it and
# replaced them with a status table. Nothing failed, nothing warned, and the loss was only
# visible because a later edit could not find its own anchor.
```

Confirmed on disk: `handoff/HANDOFF.md` is 58,748 bytes, last modified 2026-08-23 — eight days
stale as of this audit, while the root `HANDOFF.md` is 565,855 bytes and current (2026-08-31).
`grep -rn "handoff/HANDOFF" src/*.py` finds exactly two hits, both comments in `pipeline.py`
documenting the *old* bug and the fix that stopped `pipeline.py` itself from writing there —
neither is a guard. `src/publish.py:133` copies the whole `handoff/` directory
(`COPY_DIRS = ("src", "prompts", "reference", "registry_terminal", "handoff")`) into the public
export tree, with no integrity check on its contents, while `assert_intact()` — the function
`publish.push()` actually calls before pushing — never looks at it.

None of `ledger_guard.py`'s three independent mechanisms (append-only containment check,
structure/byte-floor check, hash-chain seal) currently see this file at all. If it is ever
truncated or clobbered again by a future automated writer, nothing in this module will notice,
`assert_intact()` will pass, and the corrupted file will be published — silently, exactly the
profile the module's own docstring says it exists to catch ("a failure that is silent AND
outlives the run that caused it").

**Remedy:** add `"handoff/HANDOFF.md"` to `APPEND_ONLY` and to `MIN_BYTES` (a floor somewhat
below its current ~58KB, e.g. 30000, following the same "well below current size" convention
the other floors use — see the comment at `src/ledger_guard.py:45-46`). Two mechanical wrinkles
to handle in the same change: (1) `seal()`'s snapshot writer
(`src/ledger_guard.py:250-267`) builds `os.path.join(SNAPSHOT_DIR, n)` directly from the name;
with a name containing a `/` this needs either the subdirectory created first or the name
flattened for the snapshot filename (e.g. `n.replace("/", "__")`) so the write doesn't fail on
a missing `state/ledger_snapshot/handoff/` directory. (2) Update the module docstring's "four
files" framing to five, since the current wording is itself a now-false completeness claim.

---

## Finding 2 (MINOR) — `foreman.py`'s DENYLIST justification cites the wrong lines in
`allsweep.py`, and its claim that `drill.py` is invisible to `allsweep` is false

**Where:** `src/foreman.py:107-110`.

**The claim:**
```
src/foreman.py:107-110
# net battery Hard Rule -1 names as the PROVEN property ... And `_checks_pass` does
# not cover for the omission: it runs `import`, `verify_math` and `allsweep --quick`, and
# `--quick` runs only the IMPORT and LINT tiers (allsweep.py:479, :498) while `drill` appears
# nowhere in allsweep at all -- so after a patch to drill.py NOT ONE NET fires before the patch
# is kept.
```

**Why it's wrong, verified two ways:**

1. **The cited lines don't say what the comment claims.** `allsweep.py:479` and `allsweep.py:498`
   are both inside `reconcile()` (tier 3 — "where the subsystems DISAGREE", starting at
   `allsweep.py:348`), not the IMPORT tier (`allsweep.py:224` area) or the LINT tier
   (`allsweep.py:642` area, inside `main()`). Line 479 is the tail of the phase-reconciliation
   block (`note("phase reconciliation failed", ...)`), and line 498 is inside the
   over-banded-entry check (`ceil = _band((r.get("synthesis") or {}).get("provisional_magnitude"))`).
   Neither has anything to do with which tiers `--quick` runs.

2. **The underlying claim is also false.** `allsweep.modules()` (`allsweep.py:226-243`) walks
   `src/` recursively with `os.walk` and returns every `.py` file under it — verified directly:
   ```
   >>> import allsweep as A; 'drill' in A.modules()
   True
   ```
   The IMPORT tier (`allsweep.py:634-640`) runs `check_import` over every name `modules()`
   returns, and it runs unconditionally — it is **not** gated behind `if not a.quick:` (only
   the VERIFY and ESTATE tiers are, at `allsweep.py:702` and `:727`). So `python src/drill.py
   --help` *is* executed by `allsweep.py --quick`, which `_checks_pass` (`foreman.py:1253-1308`)
   does run. The claim "`drill` appears nowhere in allsweep at all ... NOT ONE NET fires" is
   incorrect; at minimum the IMPORT tier's syntax/import/argparse check does fire on drill.py
   even under `--quick`.

**Does this change the actual safety decision?** No — the broader point (IMPORT-tier coverage
cannot catch "a weakened comparison inside one net", which is the shape a model-authored
semantic patch takes) still holds, and `drill` staying on `DENYLIST` remains the correct,
conservative call. This is a documentation/reasoning defect, not a live behavioural one — but
it is exactly the kind of comment a future maintainer would use to decide whether the DENYLIST
can be loosened, and right now it overstates the case (claims zero coverage where there is
partial coverage), which could cut the wrong way in a future argument about "is this
necessary".

**Remedy:** correct the line citations (the IMPORT tier is `allsweep.py:224-243`, the LINT tier
begins around `allsweep.py:642`) and correct the substantive claim to something like "the
IMPORT tier's `--help` smoke-test does run against drill.py even under `--quick`, but it only
proves the module parses and imports — it cannot catch a weakened comparison inside a working
net, which is the shape a model patch takes."

---

## Finding 3 (MINOR) — two more stale `file.py:NNN` cross-references in `foreman.py`, and one
in `generate.py`

Same defect class as Finding 2 — comments citing a specific line number as evidence, where the
cited line no longer (or never did) say what the comment claims. Each verified directly against
the current file content.

### 3a. `src/foreman.py:193` and `src/foreman.py:1528` — `silence.py:408`

```
src/foreman.py:193 (inside reprove_pool)
# thread (silence.py:408), which is the collision the helper exists to make unavailable.
```
```
src/foreman.py:1528 (inside owner_queue)
# `silence.write_json` cannot be used here -- this file is MARKDOWN, not JSON -- but the hazard
# the helper was written for is the temp NAME, not the format: ... Same
# `"%s.%d.%d.tmp"` shape as silence.py:408, inline rather than a new helper.
```

`silence.py:408` is inside `replace_if_unchanged()` (which starts at `silence.py:336`) — it is
mid-sentence in an `OSError` handler ("...most likely a reader holding it open) -- nothing
landed. Retry next round.""). The pid/thread-qualified temp-name construction both comments are
actually pointing at (`tmp = "%s.%d.%d.tmp" % (path, os.getpid(), _th.get_ident())`) is inside
`write_json()`, at **`silence.py:511`**, a different function entirely.

### 3b. `src/foreman.py:497` — `overnight.py:619`

```
src/foreman.py:496-497 (inside restart_reader)
# a future `build_read.py --run-tests` -- was a valid SIGTERM target. `kill_stalled_job` below
# documents having fixed exactly this loose-match class for its own matching and got the
# remedy: `lognames.OWNER` publishes the one fragment ... The fragment is "read.py --run", which is how overnight.py:619 actually launches it.
```

`overnight.py:619` is inside a comment about `_guarded_popen`'s log-separator write ("stamp
'started' into one job's log for a single real process start"). The actual launch of
`read.py --run` is at **`overnight.py:1425`**:
`statuses.append(run("read", [os.path.join(SRC, "read.py"), "--run", ...`.

### 3c. `src/foreman.py:113` — `verify_math.py:5504`

```
src/foreman.py:112-114
# Adding `python src/drill.py` to `_checks_pass` would close the rest of it and is NOT done
# here: verify_math.py:5504 records a standing rule that verify_math and drill "are not safe to
# run" from an agent context, ...
```

`verify_math.py:5504` is inside an unrelated block (item 33, "§20q — A WRITE VERDICT THAT
NOBODY READS...", about `pipeline._landed`'s discarded return value). The actual "are not safe
to run" rule text is at **`verify_math.py:6050`** (and repeated near `:6282`).

### 3d. `src/generate.py:643` — `pipeline.py:2122`

```
src/generate.py:641-644
# THE P8 META-LANGUAGE BAN, ENFORCED FOR THE FIRST TIME. `pipeline.assert_in_universe`
# was written to reject prose that breaks the in-fiction frame -- "as a DM you might",
# "in this sourcebook" -- and `pipeline.py:2122` states the ban "is enforced in code
# like scale_note and the Marginalia cap before it". It was not. ...
```

`pipeline.py:2122` is inside phase 7's shelving logic (spine-code assignment from
`address.py`/`weave_index.py`), unrelated to the P8 meta-language ban. The actual quoted phrase
is at **`pipeline.py:2621`**, in the real P8 comment block ("`# ------ P8: the meta-language
ban`", starting `pipeline.py:2616`).

**Impact:** low — these are all backward-looking commentary explaining an already-fixed defect
(the substantive fixes described in each comment are real and correctly implemented in the code
around them); nobody currently depends on the cited line number for anything executable. The
risk is purely to a future reader who tries to go verify the claim at the cited location and
finds something unrelated, which is the exact failure `generate.py`'s own comment at
`generate.py:618-623` already calls out and fixed for its *own* prior self-reference
("a line number in a string is a comment that cannot be kept honest by anything").

**Remedy:** correct each of the four citations above to the verified locations
(`silence.py:511`, `overnight.py:1425`, `verify_math.py:6050`, `pipeline.py:2621`), or better —
per `generate.py:618-623`'s own stated preference — replace them with the symbolic form other
modules already use (e.g. cite the function name, not a line number) so the reference survives
edits above it.

---

## Not filed as findings (checked and ruled out)

- **`foreman.py:324`**, `health.py:198-210` cited for "the interleaved-writer corruption of
  `state/failures.json` verbatim": the cited range is the general `_flush_ledger` lost-update
  docstring, which is on-topic but not the specific verbatim incident account (the 102-byte /
  38-byte detail is actually at `health.py:294-300`). Lower confidence and lower severity than
  3a-3d (the range at least discusses the right file and the right class of fault), and
  `health.py` is outside this batch's module list, so it is noted here rather than filed as its
  own numbered finding.
- **`foreman.py:1158` (`_function_source`'s bare-name fallback when a qualified symbol
  resolves to nothing):** re-introduces the same same-named-method ambiguity the qualifier
  lookup was built to prevent, but this is explicitly documented as the deliberate fallback
  behaviour in the function's own docstring ("a qualifier that names no scope in this file ...
  falls through to the original bare-name search unchanged") — a design tradeoff, not an
  undocumented defect. Filed here as INFO only, no work order.
- **`gpu_lane.py`, `catalogue_codex.py`, `deprecated/catalogue_local.py`, `render.py`,
  `profile.py`:** read in full; no tautological checks, no discarded return values, no fail-open
  contradicting a fail-closed docstring, and no further stale cross-references found beyond
  what's listed above (`gpu_lane.py`'s `discord_bot.py:256-298` citation points into the
  separate `motoko` project and was not checked — out of scope for this repo's audit).
