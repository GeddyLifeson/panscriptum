# sweep61 batch10 audit

Scope (read in full, start to finish, in chunks; line counts as of this run):

- src/publish.py — 2163 lines — READ IN FULL
- src/generate.py — 1184 lines — READ IN FULL
- src/catalogue_web.py — 821 lines — READ IN FULL
- src/ingest_doc.py — 702 lines — READ IN FULL
- src/address.py — 543 lines — READ IN FULL
- src/pick_model.py — 449 lines — READ IN FULL
- src/profile.py — 354 lines — READ IN FULL
- src/physics.py — 312 lines — READ IN FULL

Total: 6528 lines across 8 modules. Read-only; nothing run beyond `python -c` reasoning checks
against pure functions in-head from the source text (no code was executed).

Two brief-called-out changes checked directly:

- `generate.py` main()'s per-chapter loop now calls `_land_catalog(...)` after every chapter
  (line ~1132), not every fifth — confirmed by reading the code and its own comment ("SAVE AFTER
  EVERY CHAPTER, NOT EVERY FIFTH (maintenance run #61, 2026-09-16)"). Matches the brief.
- `profile.encode()` now refuses an out-of-range `attested` (lines 178-179): `if isinstance(attested,
  bool) or not isinstance(attested, int) or not 0 <= attested <= 4: raise ValueError(...)`. Bool
  is explicitly excluded before the int check (bool is an int subclass), and the range is
  correctly inclusive 0-4 matching `_PROFILE_RE`'s single `[0-4]` capture group. Verified correct.

## Findings

Findings by kind: 0 VERIFIED bugs, 1 SUSPECTED (the credential-helper question the brief asked
about), 1 QUESTION (low-confidence, not filed as a defect).

**SUSPECTED — publish.py `git()`, the gh.exe "No such file or directory" recurrence.**

`git()` (line ~733) sheds `GITHUB_TOKEN`/`GH_TOKEN` and tries to add gh-cli's directory to PATH:

```python
gh_dir = os.path.join(os.environ.get("LOCALAPPDATA", ""), "gh-cli", "bin")
if os.path.isdir(gh_dir) and gh_dir not in env.get("PATH", ""):
    env["PATH"] = env.get("PATH", "") + os.pathsep + gh_dir
```

If `LOCALAPPDATA` is absent or empty in the daemon's inherited environment (plausible for a
standing `pythonw`-launched publisher whose env differs from an interactive shell's — this
module's own comments already document two other cases of the daemon's environment differing
from a session's, at points 2 and 3 in this same function's comment block, both about this exact
symptom), `gh_dir` becomes the relative, almost-certainly-nonexistent path `"gh-cli\bin"`.
`os.path.isdir()` on that then evaluates relative to the process's actual current working
directory (not `SITE`, which is only used as `cwd=` for the `subprocess.run` call itself, not for
this check) and returns False. The `if` body is skipped **silently** — no `silence.note`, no
printed line, nothing — so PATH is left exactly as inherited, and if the daemon's inherited PATH
lacks gh-cli's directory (which point 2 of this same comment says has happened on this machine:
"the supervisor's children inherit a logon PATH that does not always carry the gh-cli directory"),
git's credential-helper `sh` fails to resolve `gh.exe` on PATH and reports exactly "gh.exe: No
such file or directory" — while `gh.exe` is on disk under the LOCALAPPDATA path this fix assumed
but could not read.

This reproduces the exact symptom described (gh.exe exists on disk; the daemon reports it
missing) and explains why it would appear only in the daemon's environment and not in a
hand-run session (whose `LOCALAPPDATA` is normally set): a standing pythonw-launched process's
environment inheritance is precisely what points 2 and 3 of this function's own comment already
identify as the recurring source of this class of fault. I did not run anything to confirm
`LOCALAPPDATA` is actually empty in the live daemon's environment — that would require reading
the running process's environment block, which is out of scope for a read-only audit and was
explicitly out of bounds ("do not run ... publish.py"). Flagging as SUSPECTED, with the
reasoning above, per the brief's request.

Secondary, weaker candidate in the same function: `_credential_probe()` (line ~773) is
"DISPLAY ONLY; it changes no verdict" and only fires on `PushHeld` from `push()`'s `git push`
step — it does not run on every `git()` call, so if the failure is happening on `git fetch`,
`git rebase`, or any other `git()` invocation before `push`, this diagnostic never engages at
all and the daemon's log would show only the bare `RuntimeError` from `git()` itself with no
probe output. Whether that's what's happening isn't verifiable from source alone.

**QUESTION (not filed as a defect) — generate.py `_covered()`, empty-name fail-open.**

```python
def _covered(name, text):
    ...
    n = (name or "").lower().strip()
    if not n:
        return True
```

An entry with an empty or missing `name` field is unconditionally treated as "covered," so a
retry is never triggered for it and it can never appear in `missing`/`ChapterRefused`, even if
the model genuinely wrote nothing about it. This is a fail-open shape by the brief's own
priority-2 criterion. However: every real call site passes `e.get("name", "")` from manifest
entries, and nothing in this batch's files shows evidence such entries are ever unnamed in
practice (that would be a `manifest_builder.py`/upstream data question, outside this batch).
Marking as a QUESTION rather than a finding since it may never have a live path, consistent with
this module's own house style of noting a defended-but-unreachable case rather than silently
leaving it undocumented (e.g. the `.encode()` ValueError note in profile.py, or generate.py's own
"NO CALLER ANY MORE" note on `save_json`).

## Coverage recorded

Recording via `sweep_plan.record('run61', [...], batch=10)` per the brief.
