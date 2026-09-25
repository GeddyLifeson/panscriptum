# sweep61 batch 06 audit

Scope (read start to finish, in chunks, no sampling):

- `src/workorders.py` -- 2507 lines. Read in full (1-700, 700-1400, 1400-2100, 2100-2507).
- `src/overwatch.py` -- 1124 lines. Read in full, one pass.
- `src/identity.py` -- 752 lines. Read in full, one pass.
- `src/endpoint.py` -- 654 lines. Read in full, one pass.
- `src/scope.py` -- 473 lines. Read in full, one pass.
- `src/genre.py` -- 385 lines. Read in full, one pass.
- `src/navtree.py` -- 335 lines. Read in full, one pass.
- `src/cosmology_graph.py` -- 261 lines. Read in full, one pass.
- `src/whoruns.py` -- 159 lines. Read in full, one pass.

Total: 6,650 lines across 9 modules, all read in full.

## Context

All nine modules are unusually heavily self-documented: nearly every non-trivial line is
accompanied by a comment recording an earlier order number, the incident that motivated it, and
the class of bug it forecloses (tautologies, fail-open guards, caps/truncations, lost-update
races, discarded write verdicts). Per the brief, none of that prior, already-recorded work is
re-reported here. The search below was for defects NOT already named in the surrounding
docstrings/comments.

## Findings

### 1. VERIFIED -- `overwatch.py`: a finding against a DELETED module is never retired

`round_once()`'s digest-retirement loop is:

    d = _digest(os.path.join(SRC, f["module"] + ".py"))
    if d and d != f.get("digest"):
        f["state"] = "retired"

and `_digest()` returns `""` (not `None`) on any failure to read the file, including
`FileNotFoundError`:

    try:
        with open(path, "rb") as f:
            return hashlib.sha256(f.read()).hexdigest()[:16]
    except Exception:
        silence.note("overwatch.py:digest")
        return ""

`""` is falsy, so `if d and d != f.get("digest")` is False whenever the module file no longer
exists at `SRC/<module>.py` -- the retirement never fires. A module that is deleted or moved
(this project does exactly that: `deprecated/catalogue_local.py` is a real, named precedent for
a module leaving `src/`) leaves every one of its still-open findings permanently stuck in state
`"open"`, forever, with no path to close them:

- The retire loop above never touches them (as shown).
- `verify_open()` tries to open the same path to build the re-check prompt, hits the same
  `FileNotFoundError`, and does `silence.note(...); continue` -- so the finding is not checked,
  not counted as `checked` or `yielded`, and its `last_verified` stamp is never touched either.
- `rotation()` cannot rediscover it either, because it iterates `modules_all` (the live module
  list from `allsweep.modules()`), not the ledger's findings -- a module absent from that list is
  simply never visited.

The result is a finding that sits in `WATCH.md` under "open findings" indefinitely, citing a
module that no longer exists in `src/`, directly contradicting the report's own closing line
("A finding stays open until the file it points at changes") -- deletion is the most total
"change" a file can undergo, and it is exactly the one case this mechanism does not detect.

Verified by: reading `_digest`'s exception path (returns `""`, not `None`, on any failure
including absence), the retire-loop's truthiness test in `round_once`, and `verify_open`'s
silent `continue` on the same read failure -- all three read together, no execution needed since
the control flow is unconditional on the input shown.

Not previously recorded: grepped `overwatch.py` for "deleted", "renamed", "does not exist" and
found no comment addressing this path (the two hits are unrelated: a temp-file race note and the
`escalation` import-failure guard).

Suggested fix (not applied -- read-only batch): have `_digest` distinguish "file absent" from
"digest computed" (e.g. return `None` for absence, keep `""`/hash for content), and retire on
`d is not None and d != f.get("digest")` as well as on `d is None` (absence itself is a terminal
change). Left as a work order candidate rather than an edit, per this sweep's read-only rule.

## Other observations (not filed as findings)

- `endpoint.py:register()`'s unreadable-file branch does a bare `raise` of the original
  exception, while the sibling `source_pages()` wraps the identical fact in a dedicated
  `PagesRegistryUnreadable`. Both are documented as deliberately refusing to overwrite an
  unreadable registry; the difference is only in what shape the caller catches. Not filed as a
  finding -- it doesn't affect correctness (any caller catching `Exception` still sees it), and
  the surrounding docstring's argument for "raise rather than heal" is intact either way. Flagged
  here only in case a future pass wants the two call sites to match structurally.
- `workorders.py`'s door-guard `_refuse_cap_hit` is deliberately not applied to `resolve()`'s
  `resolution` field (only to `file_order`'s `what`/`where`/`found_by` and `reroute`'s
  `found_by`). This looked at first read like an inconsistency but is explicitly argued for in
  both functions' own comments: `resolution` only ever lands in the append-only closed log, which
  `cap_boundary_scan()` treats as a measurement rather than a live regression, so the door-guard
  (which exists to prevent regressions in the *open* queue) has nothing to protect there. Marked
  a QUESTION at most, already answered by the code's own comments -- not reported as a finding.
- No tautologies, fail-open guards, or Hard-Rule-0-style caps/truncations were found beyond what
  the modules' own comments already record as fixed. `all()`/`any()` usages were checked
  individually; the one `all(...)` over a potentially-empty generator
  (`workorders.py file_order`'s LOCAL-denylist check) is correctly guarded by `targets and
  all(...)` immediately to its left, so it cannot silently pass on an empty list.
- Dead code: none newly found. `scope.py`'s `ceiling_for()` is already self-reported dead in its
  own comment (order de43fe54feb7) and correctly not re-reported here per the brief.

## Coverage

Recorded via `sweep_plan.record` for all nine modules listed above, batch 06.
