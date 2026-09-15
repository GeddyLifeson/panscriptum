# Sweep 59 -- AUDIT batch 10

Modules read in full: | module | lines | read (top to bottom? mtime) |
| src/publish.py | 2155 | yes, top to bottom, three Read calls (mtime 22:19:35) |
| src/sweep_plan.py | 1150 | yes, top to bottom (mtime 00:02:20) |
| src/catalogue_web.py | 821 | yes, top to bottom (mtime 22:14:57) |
| src/ingest_doc.py | 702 | yes, top to bottom (mtime 23:22:12 9/13) |
| src/prose_gate.py | 541 | yes, top to bottom (mtime 22:14:57) |
| src/render.py | 430 | yes, top to bottom (mtime 23:43:26 9/13) |
| src/wh40k.py | 350 | yes, top to bottom (mtime 16:37:34 9/8) |
| src/audit.py | 275 | yes, top to bottom (mtime 22:14:57) |
| src/compress_store.py | 149 | yes, top to bottom (mtime 00:10:07) |

## src/publish.py -- THE REQUESTED LIVE-FACT INVESTIGATION

### New findings

**QUESTION -- the `git()` PATH-widening fix (lines 745-750) cannot be what governs the
"gh.exe: No such file or directory" symptom, because the credential helper is invoked by an
ALREADY-ABSOLUTE path, not a bare command PATH has to resolve**

where: src/publish.py `git()` (lines 733-763, the PATH block at 745-748)

evidence: quoted from `git()`:
```
745	    env = {k: v for k, v in os.environ.items() if k not in ("GITHUB_TOKEN", "GH_TOKEN")}
746	    gh_dir = os.path.join(os.environ.get("LOCALAPPDATA", ""), "gh-cli", "bin")
747	    if os.path.isdir(gh_dir) and gh_dir not in env.get("PATH", ""):
748	        env["PATH"] = env.get("PATH", "") + os.pathsep + gh_dir
```
The comment above this block (lines 741-744) attributes the historical "gh.exe: No such file or
directory" failure to PATH not carrying the gh-cli directory. I checked the actual git config
this repo/user account uses (`git config --global --list`, read-only, no push attempted):
```
credential.https://github.com.helper=!'C:/Users/imarl/AppData/Local/gh-cli/bin/gh.exe' auth git-credential
credential.https://gist.github.com.helper=!'C:/Users/imarl/AppData/Local/gh-cli/bin/gh.exe' auth git-credential
```
The helper string is a `!`-shell command whose FIRST WORD IS ALREADY THE FULL ABSOLUTE PATH to
gh.exe, single-quoted. `sh -c` (git's own bundled MSYS sh, invoked internally to run this
string) does not need PATH to locate `gh.exe` at all -- it execs the literal quoted path. So
`git()`'s PATH-widening at lines 746-748 can only ever help a DIFFERENT failure mode: a bare
unqualified `gh` invocation somewhere relying on PATH search. It cannot be the mechanism that
prevents, or now fails to prevent, `sh` reporting "'.../gh-cli/bin/gh.exe': No such file or
directory" for a path that is confirmed to exist on disk (verified: `ls -la
"$LOCALAPPDATA/gh-cli/bin"` shows `gh.exe`, 41,504,056 bytes).

failure: this is why the fix documented in the comment above `git()` ("the supervisor's children
inherit a logon PATH that does not always carry the gh-cli directory") does not close the loop on
the CURRENT symptom (every `--push --loop` cycle failing on exactly this message since the
2026-09-14 18:00 reboot): the code's own theory of what causes/fixes this message is inapplicable
to how the helper is actually configured on this machine. `_credential_probe` (lines 766-797,
inserted this shift) already independently concluded "the difference is in the daemon's process
context, not in its variables" -- consistent with my finding, since PATH content is a variable and
the helper's resolution does not consult PATH for this string.

remedy (this is a QUESTION for the owner/next shift, not a code fix I can prescribe from a
read-only pass): the two live candidates that remain, given PATH content is ruled out as the
mechanism for THIS symptom, are (a) `sh.exe` ITSELF resolving to a different binary depending on
process-launch context -- something earlier in the daemon's PATH order that is not Git for
Windows' own bundled MSYS sh, which would not perform the automatic `C:/...`-style absolute-path
exec translation the real one does; `git()` only APPENDS to PATH (line 748), it never ensures
git's own directories are ordered first, so if the daemon's post-reboot launch context puts some
other `sh`/`bash` ahead in PATH this code does nothing to correct it -- or (b) something entirely
outside src/'s control (a security product on this machine intercepting exec calls from that
specific process's security/logon context; this machine has a documented history of exactly this
class of interference with Python/Java HTTPS and MSI installs per the user's own standing notes).
Distinguishing (a) from (b) needs comparing `where sh`/`where bash` (and ideally `type -a sh`
inside the actual failing process, not a reproduction) at the moment of failure, which
`_credential_probe` does not currently capture -- it calls `shutil.which()` against the CURRENT
process's own `os.environ`, which is a reasonable proxy but was not captured AT the moment of an
actual failing `git()` call, only in a follow-up investigation.

### Known (already open orders)
- 91bb70c85e31 (CODEWATCH_RESTART) -- INFO-severity log evidence tied to the same investigation
  (a codewatch restart from a src/ fingerprint change), not itself a defect; still accurate as a
  log entry, no action needed.
- a66423722e45 (AGENT_SCRATCH_IN_PUBLISHED_TREE) -- still accurate. Verified directly: `git()`'s
  neighbours `CODE_FREE_DIRS`, `_is_agent_scratch`, and `gitignore_lines()` (lines 211-266) exist
  exactly as the order describes and correctly refuse/withdraw `.py`/`.sh`/etc. under `handoff/`.
  This remains a file-housekeeping decision (move or delete the 28 scratch scripts) pending the
  owner, not a code defect -- nothing here needed re-filing.
- d56cb7f2bed0 (PROSE_GATE_LACKS_EATEN_ESCAPE_GUARD) -- NO LONGER accurate. `src/prose_gate.py`
  now carries the `_BAD_CHARS` self-check at lines 45-47, exactly matching the house pattern in
  its 51 siblings. This was inserted by tonight's run #59 (named in SWEEP_BRIEF.md's "known
  concurrent activity" list) and is present and correct as read.
- 21c075e5e2d6 (MORE_WRITERS_WITHOUT_A_HALT_INTERLOCK_SWEEP58) -- still accurate for
  `src/wh40k.py`: verified directly, `wh40k.py` has no import of `escalation` anywhere and
  `main()` writes `data/WH40K_ASSAYS.json` (via `silence.write_json`) with no
  `escalation.assert_clear()` call. Matches the order's own description of this module exactly
  ("writes documented-regenerable, unread-downstream artifacts"). Still an open OWNER policy
  question, not something to re-file.
- de265a105279 (A_NEW_MODULE_REDS_A_SAFETY_ROW_UNTIL_A_WHOLE_SWEEP_RUNS) -- names
  `src/sweep_plan.py:missing()`/`modules()` as part of the mechanism. Not independently
  re-verified against `verify_math.py` (out of my module list and I was told not to run it); the
  `missing_detail()`/`roster_of()` split this order's shift-note describes as already landed is
  present and reads correctly in the current `sweep_plan.py` (lines 838-911). The owner's half of
  the ruling (whether an `added_since` gap should fail a Hard-Rule-1 safety at all) is still
  unresolved as far as this module shows.
- f27c121c6cb7 (CATALOGUE_WEB_STORED_TYPES_NEED_RECATALOGUE) -- still accurate. The writer fix it
  refers to (order 6eb20e8d3565: `first_cat` provenance tracking + `_singular()`) is present and
  correct in the current `catalogue_web.py` (`catalogue()` lines 461-587,
  `catalogue_composite()` lines 237-406). The 272,004 already-stored entries this order is about
  are a data question, unaffected by re-reading the writer code; still an OWNER decision on
  `--recatalogue` scope, not a code defect.

### Checked and clean (publish.py)
- `_scrub`/`scrub_text`/`_scan_units`/`scan_for_secrets` (the three secret-scan locks): read in
  full, logic matches every docstring claim (per-line marker, dict-key/tuple/set recursion,
  streamed scanning with no size skip, bytecode exclusion). No tautology or fail-open found.
- `push()`'s ordering of ledger_guard / mutate / secret-scan / commit / fetch-rebase / push /
  post-push confirmation: each failure mode raises a distinct, named exception (`PushHeld`,
  `RuntimeError`) rather than silently succeeding; `main()`'s halt re-check inside the loop and
  the `rc=1` on the halt-break path (fixed this run per its own comment) are both present and
  correctly wired.
- `export_root()`/`home_export()`/`_is_throwaway()`: the temp/scratchpad refusal is structural
  (segment-name match), not an enumerated list, and warns loudly on every refusal cycle rather
  than silently substituting the fallback.
- `prune_export`/`sync_tree`'s "held vs. gone vs. live" three-way classification for both
  directories and files: correctly distinguishes an unreadable root from a genuinely deleted one
  in every branch checked.

## src/sweep_plan.py
### Checked and clean
- `batches()`/`freeze_plan()`/`record()`/`covered_by()`/`missing()`/`missing_detail()`: read in
  full. The shard-based, per-process coverage recording (no shared mutable file on the write
  path), the roster-based `skipped`/`added_since`/`undetermined` split, and the
  compare-and-swap freeze are all internally consistent with their own docstrings and with each
  other; no tautology, no silent swallow found. `_table_digest()`'s `json.dumps(..., sort_keys=
  True)` on a list-of-lists does not sort the list itself (`sort_keys` only orders dict keys),
  but the digest only needs to be stable for a given tree state, which `modules()`'s deterministic
  ordering (stable sort over an alphabetically-walked file list) already guarantees -- not a
  defect, just noted as verified rather than assumed.

## src/prose_gate.py

### New findings

**QUESTION -- `instrument_shortfall()` accepts a bare Instrument marker with no content
(no score, no "uninstrumented", no "Not applicable") as satisfying a NON-being entry's
Instrument requirement**

where: src/prose_gate.py `instrument_shortfall()` (lines 468-497, the branch at line 488)

evidence:
```
487	        being = any(c in cls for c in INSTRUMENT_CLASSES)
488	        if marked and (scored or excused or not being):
489	            present += 1
490	        elif not being and excused:
491	            present += 1
```
For a non-being entry (`being=False`), line 488 reduces to `marked and (... or True)` = `marked`
alone. So an entry whose Class is e.g. "Place" or "Faction" passes this check the moment
`_INSTRUMENT_MARK` finds the word "Instrument" or the `▣` glyph ANYWHERE in the block -- it does
not have to contain the template's required "Not applicable -- the Instrument measures beings,
not [...]" sentence, or anything else. This is documented as deliberate two paragraphs above
("a non-being entry needs the marker or the sentence" -- an explicit OR), so it is not a
code/docstring mismatch.

failure: a header-only Instrument section for a non-being entry (e.g. a bare "▣ The Instrument"
line with no "Not applicable" text following it) would be scored as present here, which is the
same "header survived, content vanished" shape the 2026-08-25 incident produced for the Threads
section and that this whole layer-4c function exists specifically to catch for the Instrument
section (see the module's own header comment on 1,155 of 1,268 entries losing this section). The
being-class branch (line 488 with `being=True`) correctly demands `scored or excused` in addition
to `marked`; the non-being branch does not demand the equivalent `excused` alongside `marked`.

remedy: this needs an owner ruling rather than a unilateral fix, because two readings are both
defensible: (1) tighten line 488 to require `marked and (scored or excused)` unconditionally
(drop the `or not being` escape hatch), so a non-being entry must show the actual Not-applicable
sentence, not just the header word -- consistent with the rest of this module's zero-tolerance
posture (`SECTION_LOSS_FLOOR = 0.0`); or (2) leave it as designed, on the reasoning that a model
which writes "▣ The Instrument" for a Place is already very likely also writing the fixed
template sentence right after it, and the stricter test would cost nothing today but is a
sharper edge to add later if a real header-only-no-content non-being entry is ever measured on
the corpus (matching this module's own stated philosophy elsewhere of fixing what is measured
rather than what is merely possible).

### Known (already open orders)
- d56cb7f2bed0 -- see the publish.py section above; recorded once, applies identically here since
  it names `src/prose_gate.py` directly. NO LONGER accurate: the guard is present at lines 45-47.

## src/catalogue_web.py, src/ingest_doc.py, src/render.py, src/wh40k.py, src/audit.py,
src/compress_store.py
### Checked and clean
No new DEFECT or QUESTION found in any of these six modules beyond the Known items above. Each
was read in full; the extensive per-line commentary in all six (dozens of named prior orders)
matches the code as it stands today -- spot-checked the load-bearing claims (catalogue_web's
`_singular()` ordering, ingest_doc's oversize-page re-chunking and resume-cursor rollback-on-
denied-write, render's `children_of()` whole-coordinate refusal, wh40k's `_provenance()`
3-tuple default, audit's `_JUNK` anchor placement, compress_store's content-hash verification on
load) against the current source and found each to behave as documented.

QUESTIONS: 2
