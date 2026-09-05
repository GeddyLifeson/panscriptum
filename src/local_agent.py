#!/usr/bin/env python3
"""LOCAL_AGENT — the GPU model with hands: read, search, and gated writes on this repo.

OWNER RULING 2026-08-23: the delegation ladder runs bots -> OLLAMA -> Claude subagents ->
Claude, and the Ollama rung must be able to read and write files, not merely answer prompts.
A model is text-in/text-out; FILE ACCESS IS A HARNESS PROPERTY -- so this module is the
harness. It drives Ollama's /api/chat tool-calling loop (Qwen3 is tool-trained; the harness
PROBES rather than assumes, and names tool-capable models that fit the card if the configured
one is not) and hands the model six tools:

    read_file    any file under the project, sliced -- iterative reads, never a truncation
    list_dir     one level of the tree
    grep         a regex over src/ (or a named subtree), every match with file:line
    find_symbol  every definition of a name, with a uniqueness verdict
    run_check    one of the repo's own verifiers, read-only
    propose_patch  an exact find->replace on ONE file, STAGED -- never applied raw

WRITES GO THROUGH THE FOREMAN'S OWN BAR. A patch is applied only if: the file is not on the
foreman's denylist, the result parses, pyflakes finds no new undefined names in it, the
module still imports, and verify_math still reports 0 FAILED. A backup is written before and
restored on ANY failure, including a crash inside the checking. This is the same six-gate
discipline foreman's model lane uses, because a local model editing a live codebase
unsupervised is the documented hazard, not a convenience.

    python src/local_agent.py --task "Read src/lognames.py and report every constant."
    python src/local_agent.py --task "..." --no-apply     # stage patches, apply nothing
"""
import argparse
import ast
import json
import os
import re
import subprocess
import sys
import time
import urllib.error
import urllib.request

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import silence                                                          # noqa: E402

_BAD_CHARS = (chr(8), chr(11), chr(12), chr(7))
if any(c in open(os.path.abspath(__file__), encoding="utf-8").read() for c in _BAD_CHARS):
    raise SystemExit(__file__ + ": a regex escape was eaten in transit.")

_NO_WIN = getattr(subprocess, "CREATE_NO_WINDOW", 0)
PY = sys.executable

MAX_TURNS = 24
SLICE = 12000                 # chars per read_file call -- a WINDOW, not a cap: the model
                              # pages through a big file with offset, and the tool says how
                              # much remains so nothing silently falls off the end
# THE MESSAGE CAP IS NOT THE READ WINDOW, and conflating them is what produced order
# 1b35c5c95fdd. `run()` used to append tool output as `json.dumps(res)[:SLICE]`: a read_file
# result whose `slice` is already SLICE characters long serialises to MORE than SLICE once the
# envelope and the JSON escaping are added, so the cut landed INSIDE the slice string and took
# `chars_after_slice` and `total_chars` -- the two keys that exist to stop a silent truncation
# -- off the end with it. The model received malformed JSON and never learned how much
# remained. The bound is kept, because a context window is finite, but it is now applied by
# `_tool_message` to the LARGEST FIELD INSIDE the dict, so the envelope always serialises whole
# and the model is always told what it did not get.
TOOL_MSG_MAX = 12000          # chars per tool MESSAGE (the serialised envelope), not per read
DENYLIST = {"foreman", "silence", "health", "allsweep", "estate", "standards",
            "verify_math", "local_agent",
            # THE CONTRACT-ENFORCEMENT MODULES, added 2026-08-25 (run #29, batch 16).
            # The list above is the machinery that JUDGES a patch -- the gate, the linter, the
            # failure ledger, the standards. These four are the machinery that judges every
            # WRITE, and leaving them out was the same hole one layer down: the two-writer
            # contract lives in `pipeline.write_record` / `write_record_catalogue`, the claim
            # discipline in `runguard`, the card's arbitration in `gpu_lane`, and the proof
            # that a sweep covered everything in `sweep_plan`. A model permitted to patch
            # `pipeline` could widen the very drift-merge allowlist that stops a concurrent
            # writer's edits being dropped -- and every gate below would still pass, because
            # they check that a patch parses, lints, imports and leaves verify_math green,
            # not that it left the contract intact.
            "pipeline", "runguard", "gpu_lane", "sweep_plan",
            # THE DETECTION MACHINERY, added 2026-08-29 (order 6f4b1f51a0c3). Order
            # 881ff7f49438 found these five missing from `foreman.DENYLIST` and only that half
            # was closed; this list states the SAME rule -- "each is either the thing that would
            # have to be working to detect a bad patch, or the thing doing the patching" -- and
            # this is the copy enforced closest to the filesystem, since `_denied_target` below
            # is what `t_propose_patch` actually asks before writing. `drill` is the net battery
            # Hard Rule -1 names as the PROVEN property; `escalation` is the plant-wide
            # interlock; `codewatch` is the rc=17 stale-code interlock; `liveness` is the
            # check-that-cannot-fail detector; `overnight` is the supervisor that starts every
            # job. The two lists still differ deliberately -- local_agent adds itself and the
            # four contract-enforcement modules above, which are write-contract concerns the
            # dispatch side never touches -- but they may not differ on the detectors.
            "drill", "escalation", "codewatch", "liveness", "overnight",
            # THE GATE ITSELF, AND THE DOOR TO THE PUBLIC, added 2026-09-04 (maintenance run
            # #44). Both are named by the rule this list already states -- "each is either the
            # thing that would have to be working to detect a bad patch, or the thing doing the
            # patching" -- and both were missing from it. MEASURED, not read: before this line,
            # `_denied_target("src/prose_gate.py")` and `_denied_target("src/publish.py")` both
            # answered False, so the local model could write either.
            #
            # `prose_gate` is THE gate. The incident this whole project's chain of command was
            # built after is an autonomous run deleting it because it looked like an instruction
            # to a human, and 145 unauthorised chapters following. The comment on
            # DENYLIST_PREFIXES below says "config.yaml holds the prose gate", and that is true
            # of the FLAG and not of the ENFORCEMENT: `config.yaml` is denied, `src/prose_gate.py`
            # was not. Protecting the switch and leaving the wiring writable is the same half-fix
            # that order 881ff7f49438 found on the detector list. And the failure mode is already
            # on the record one module over -- `overnight.py` reimplemented this gate with
            # `bool()` instead of the strict check and `prose_enabled: "false"` OPENED it. A model
            # need never touch the flag to defeat the gate; it only has to relax the code that
            # reads it, and every gate below would stay green, because they check that a patch
            # parses, lints, imports and leaves verify_math passing.
            #
            # `publish` is the only module here that takes an IRREVERSIBLE, OUTWARD action: it
            # pushes to a public GitHub repository, and it carries `scan_for_secrets` in front of
            # that push. It is therefore both halves of the rule at once -- the thing that would
            # have to be working to detect a leaked credential, and the thing that makes the leak
            # permanent. It is also the module that, on 2026-08-25, pushed deliberately-corrupted
            # source to the public repo twice. A patch that loosened the scanner would be graded
            # by gates that do not look at the scanner at all.
            #
            # This NARROWS what the LOCAL rung may repair -- open orders against both modules now
            # need the RUN rung -- which is the intended trade and is flagged for the owner in
            # this run's handoff.
            "prose_gate", "publish"}

# The same bar, for files that are not python modules and therefore have no module name to
# match on. Repo-relative, forward slashes. config.yaml is here because every module in the kit
# reads it for the model, the host and num_ctx: one bad edit misroutes the whole pipeline, and
# unlike a broken .py it fails silently rather than at import.
DENYLIST_PATHS = {"config.yaml"}

# WHOLE REGIONS THE LOCAL MODEL MAY NEVER WRITE, matched by repo-relative prefix (M24, owner
# ruling 2026-08-25). The denylists above name individual files, which cannot express "every
# record", and M24 is exactly that shape: `propose_patch` could write `data/records/*.json`
# DIRECTLY, bypassing `pipeline.write_record` and becoming a third writer against a two-writer
# contract -- with every gate still green, because the gates check that a patch parses, lints,
# imports and leaves verify_math passing, not that it went through the right door.
#
# The prose gate taught the same lesson one layer up: the dangerous edit is not the one that
# breaks a test, it is the one that quietly removes a decision. So this list is not only about
# corruption. `config.yaml` holds the prose gate; `reference/keystone_volumes/` holds the
# CHARTER, where the addressing, the Ladder of Being and the Assay method live and where Hard
# Rules 2, 3 and 4 reserve judgment to the owner. An autonomous model must not be able to edit
# the document that defines what it is allowed to do.
DENYLIST_PREFIXES = (
    "data/records/",              # two-writer contract: pipeline.write_record only
    "reference/keystone_volumes/",  # the charter and the keystone volumes -- owner territory
    "output/index/",              # the catalog and manifest, written by their own tools
    "state/",                     # shared run state, landed via silence.replace_retry
    ".git/",
)

# THE ALLOWLIST, AND WHY IT EXISTS ALONGSIDE THE DENYLIST RATHER THAN INSTEAD OF IT.
#
# Borrowed from the Eli Felse Base project's `trusted_modules.json`, whose organising idea is
# that an autonomous model should choose from a FIXED MENU rather than compose arbitrary
# instructions. The distinction is not stylistic:
#
#     a DENYLIST fails OPEN  -- anything nobody thought of is permitted
#     an ALLOWLIST fails CLOSED -- anything nobody thought of is refused
#
# M24 is precisely that failure: `propose_patch` could write `data/records/*.json`, bypassing
# `pipeline.write_record` and becoming a third writer against a two-writer contract, purely
# because that prefix was not on a list. Four earlier bypasses of this same gate (case, name
# prefix, NTFS alternate data stream, case-sensitive extension) are all the same shape -- a
# denylist being asked a question it cannot answer.
#
# BOTH ARE KEPT. Not belt-and-braces for its own sake: they fail differently, which is the whole
# requirement (CLAUDE.md, Hard Rule -1). The allowlist bounds the surface to what the agent's job
# actually needs; the denylist keeps the specific, well-argued refusals inside that surface --
# `src/` is writable, but `src/verify_math.py` is not, because the checking machinery may not
# edit itself. Neither alone expresses that.
WRITABLE_PREFIXES = (
    "src/",        # the agent's job is code repair -- still subject to the module denylist
    "prompts/",    # prompt text, versioned by config's prompt_version
    "handoff/",    # audit reports
)
WRITABLE_FILES = ("README.md", "STATUS.md", "BUGS.md", "NEXT_STEPS.md")

# BLAST-RADIUS CAP, independent of every allow/deny decision above.
#
# This gate has been defeated FIVE times -- by letter case (m113), by a name prefix (m114), by an
# NTFS alternate data stream (m121), by a case-sensitive extension test (run #25), and by a whole
# directory nobody had listed (M24). Every one was a variation of "the string being compared did
# not have the shape the comparison assumed", and every one was found only after it had been
# open for a while.
#
# The honest conclusion is not that the sixth hole has been found. It is that there will be a
# sixth. So the damage of ANY undiscovered hole is bounded by something that does not depend on
# the hole being enumerated: a hard limit on how much one invocation may change, borrowed from
# Strix's per-turn tool-call limiter. Past it, the run aborts and asks for a person.
#
# Generous on purpose -- a real repair touches a handful of files -- so it never bites honest
# work, only a runaway.
MAX_FILES_PER_RUN = 8
MAX_PATCHES_PER_RUN = 24
_BLAST = {"files": set(), "patches": 0}


def _blast_ok(full):
    """-> (ok, reason). Count this write against the run's budget."""
    _BLAST["patches"] += 1
    _BLAST["files"].add(os.path.normcase(full))
    if _BLAST["patches"] > MAX_PATCHES_PER_RUN:
        return False, ("blast-radius cap: %d patches in one run (limit %d). A repair does not "
                       "look like this; stopping and asking for a person."
                       % (_BLAST["patches"], MAX_PATCHES_PER_RUN))
    if len(_BLAST["files"]) > MAX_FILES_PER_RUN:
        return False, ("blast-radius cap: %d distinct files touched in one run (limit %d). "
                       "This bound does not depend on knowing which gate was bypassed, which "
                       "is the entire reason it exists."
                       % (len(_BLAST["files"]), MAX_FILES_PER_RUN))
    return True, ""


def blast_reset():
    _BLAST["files"] = set()
    _BLAST["patches"] = 0

# Models known tool-trained and fitting a 10GB card, for the capability report when the
# configured model turns out not to emit tool calls at all.
# GPU-resident on a 10GB card AND tool-trained -- the ruling of 2026-08-24 excludes anything
# that offloads, which is why no 12B+ dense model or 30B MoE appears here any more.
TOOL_CAPABLE = ["qwen3:8b (the standing choice)", "qwen3:4b", "llama3.1:8b-instruct-q4_K_M"]

SYSTEM = (
    "You are a maintenance agent working on the Panscriptum library kit, a Python project. "
    "Use the tools to read real files before claiming anything about them. Cite file:line. "
    "When asked to change code, read the target first, then call propose_patch with an EXACT "
    "unique find string copied verbatim from the file. Small, surgical patches only. When "
    "the task is done, answer in plain text with your findings; do not call tools you do "
    "not need. Never invent file contents."
)

TOOLS = [
    {"type": "function", "function": {
        "name": "read_file",
        "description": "Read a slice of a file in the project. Returns the slice, plus how "
                       "many characters remain after it (page with offset until 0 remain).",
        "parameters": {"type": "object", "properties": {
            "path": {"type": "string", "description": "path relative to the project root"},
            "offset": {"type": "integer", "description": "character offset, default 0"}},
            "required": ["path"]}}},
    {"type": "function", "function": {
        "name": "list_dir",
        "description": "List one directory level in the project.",
        "parameters": {"type": "object", "properties": {
            "path": {"type": "string", "description": "relative path, default '.'"}},
            "required": []}}},
    {"type": "function", "function": {
        "name": "grep",
        "description": "Search a Python regex over every file in a subtree (default src/). "
                       "Returns every match as file:line: text.",
        "parameters": {"type": "object", "properties": {
            "pattern": {"type": "string"},
            "subtree": {"type": "string", "description": "default 'src'"}},
            "required": ["pattern"]}}},
    {"type": "function", "function": {
        "name": "propose_patch",
        "description": "Stage an exact find->replace on one file. The find string must "
                       "occur exactly once, verbatim. Applied only after it passes the "
                       "parse/lint/import/verify gates; you will be told the outcome.",
        "parameters": {"type": "object", "properties": {
            "path": {"type": "string"},
            "find": {"type": "string"},
            "replace": {"type": "string"},
            "why": {"type": "string", "description": "one sentence, for the audit trail"}},
            "required": ["path", "find", "replace", "why"]}}},
    {"type": "function", "function": {
        "name": "find_symbol",
        "description": "Locate every definition of a function or class by NAME. Returns each "
                       "as file:line with its enclosing class if it has one, and says how many "
                       "definitions share the name. Use this before patching a function, to "
                       "make sure you are changing the right one.",
        "parameters": {"type": "object", "properties": {
            "name": {"type": "string", "description": "bare function or class name"}},
            "required": ["name"]}}},
    {"type": "function", "function": {
        "name": "run_check",
        "description": "Run one of the project's own verifiers and return its output. "
                       "Read-only: these check the tree, they never modify it. Use this to "
                       "TEST a claim before proposing a patch, and again to confirm a patch "
                       "did what you said. Allowed: 'verify_math' (the full invariant suite), "
                       "'pyflakes' (lint one file or all of src), 'compile' (does a file "
                       "PARSE -- it is not run and it is not imported), 'silence' (the "
                       "swallowed-exception audit).",
        "parameters": {"type": "object", "properties": {
            "check": {"type": "string", "description":
                      "verify_math | pyflakes | compile | silence"},
            "path": {"type": "string", "description":
                     "for pyflakes/compile: the file to check, default all of src"}},
            "required": ["check"]}}},
]


def t_find_symbol(name, **_):
    """Every definition of `name`, with its enclosing class and a uniqueness verdict.

    THE MODEL LANE CAN OVERWRITE THE WRONG FUNCTION (m38): `foreman._function_source` resolves
    a symbol by bare name with no uniqueness check, and with `--patch` live that is a real
    edit to a real file. Giving the model a tool that SAYS a name is ambiguous is the cheap
    half of that fix -- it cannot disambiguate what it was never told was ambiguous.
    """
    want = (name or "").strip()
    if not want:
        return {"error": "no name given"}
    hits = []
    for root, dirs, files in os.walk(os.path.join(HERE, "src")):
        dirs[:] = [d for d in dirs if d not in ("__pycache__", "deprecated")]
        for fn in sorted(files):
            if not fn.endswith(".py"):
                continue
            full = os.path.join(root, fn)
            try:
                with open(full, encoding="utf-8") as f:
                    tree = ast.parse(f.read())
            except Exception:
                continue
            rel = os.path.relpath(full, HERE).replace("\\", "/")

            def walk(node, cls=None):
                for child in ast.iter_child_nodes(node):
                    if isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                        if child.name == want:
                            hits.append({"file": rel, "line": child.lineno,
                                         "kind": type(child).__name__.replace("Def", "").lower(),
                                         "enclosing_class": cls})
                        walk(child, child.name if isinstance(child, ast.ClassDef) else cls)
                    else:
                        walk(child, cls)
            walk(tree)
    return {"name": want, "count": len(hits), "definitions": hits,
            "unique": len(hits) == 1,
            "warning": (None if len(hits) <= 1 else
                        f"{len(hits)} definitions share this name -- say which file you mean "
                        f"and quote enough surrounding text that `find` matches only one")}


# The ONLY commands the model may cause to run. An allowlist of fixed argument vectors, not a
# shell string it can influence: the model proposes which CHECK to run, never what to execute.
_CHECKS = ("verify_math", "pyflakes", "compile", "silence")


def t_run_check(check="", path=None, **_):
    """Run one of the repo's own verifiers, read-only, and hand back what it said.

    WHY THIS TOOL EXISTS. The lane could read code and propose an edit but could not TEST
    anything, so every claim it made about behaviour was inference from reading -- and this
    project's most repeated lesson is that a comment or a reading is not evidence (three false
    claims found in day-old code across two runs). A model that can run `verify_math` before
    and after its own patch is arguing from a result instead of from a guess.

    Read-only by construction: none of the four writes to the tree. `propose_patch` remains the
    only path to a change, and it keeps every one of its existing gates.

    AND THAT SENTENCE IS NOW TRUE, which it was not (order deeb24037ede). The 'compile' check
    ran `py_compile.compile(path, doraise=True)`, and py_compile's whole job is to EMIT a
    `.pyc` -- running it against a file dropped `__pycache__/<name>.cpython-313.pyc` beside it,
    reproduced on a scratch file. The write was harmless; the CLAIM was the defect, and this
    project's standing lesson is that a comment is not evidence. The check now uses the builtin
    `compile()` on the file's text, which parses and byte-compiles entirely in memory: the same
    verdict, the same SyntaxError with file and line, and nothing on disk. Fixing the code
    rather than softening the docstring, because "read-only by construction" is the property
    the lane is designed around and it should be the true one.
    """
    check = (check or "").strip()
    if check not in _CHECKS:
        return {"error": f"unknown check {check!r}; allowed: {', '.join(_CHECKS)}"}
    target = None
    if path:
        target = _safe(path)
        if not target:
            return {"error": "path outside the project"}
    if check == "verify_math":
        argv = [PY, os.path.join(HERE, "src", "verify_math.py")]
    elif check == "silence":
        argv = [PY, os.path.join(HERE, "src", "silence.py")]
    elif check == "pyflakes":
        argv = [PY, "-m", "pyflakes", target or os.path.join(HERE, "src")]
    else:
        # The builtin `compile`, NOT `py_compile` -- see the docstring. py_compile writes a
        # `.pyc` into `__pycache__` beside whatever it is handed, which made the "read-only by
        # construction" promise above false. This parses and byte-compiles in memory and writes
        # nothing; a SyntaxError still names the file and the line, which is the whole product.
        argv = [PY, "-c",
                "import sys; p = sys.argv[1]; "
                "compile(open(p, encoding='utf-8').read(), p, 'exec'); print('parses OK')",
                target or os.path.join(HERE, "src", "verify_math.py")]
    try:
        env = dict(os.environ, PYTHONIOENCODING="utf-8")
        r = subprocess.run(argv, cwd=HERE, capture_output=True, text=True, timeout=900,
                           encoding="utf-8", errors="replace", env=env,
                           creationflags=_NO_WIN)   # never pop a console -- owner directive
    except Exception as e:
        return {"error": f"{type(e).__name__}: {str(e)[:160]}"}
    out = ((r.stdout or "") + (r.stderr or "")).strip()
    # The TAIL, because a verifier's verdict is at the end -- and it is labelled as a window
    # rather than presented as the whole output, so the model is never misled about what it
    # has seen. Hard Rule 0 is about listings the library serves, not about a console window,
    # but saying which part you are showing costs nothing and prevents a false conclusion.
    tail = out[-6000:]
    return {"check": check, "exit_code": r.returncode, "ok": r.returncode == 0,
            "output_tail": tail,
            "truncated": len(out) > len(tail),
            "note": "showing the last 6000 characters; the verdict line is at the end"}


def _safe(path):
    """A path the model may touch: inside the project, never the export copy or .git."""
    raw = str(path if path is not None else ".")
    # AN NTFS ALTERNATE DATA STREAM IS THE SAME FILE WEARING A NAME THE GATES DO NOT RECOGNISE.
    #
    # Found run #24 by the comprehensive sweep and reproduced on this machine. `src/foreman.py`
    # is denied; `src/foreman.py::$DATA` is not, and it is the SAME BYTES. `os.path.isfile()`
    # says True, the write goes through to the real file -- and because the string does not end
    # in `.py`, `t_propose_patch` derives `modname is None`, so the module denylist cannot match
    # and the path denylist is tested against a name (`foreman.py::$DATA`) that is not in it
    # either. For `health`, `allsweep`, `estate` and `local_agent` the loss is total: verify_math
    # never imports them, so the parse/lint/import gates have nothing to say about them either.
    #
    # This is m113 and m114's shape a third time -- a gate keyed on a STRING while the
    # filesystem resolves a DIFFERENT string to the same object. So the check is no longer "does
    # this name look denied" but "is this name a plain one at all": a colon anywhere past the
    # drive letter, or a component with a trailing dot or space (Windows strips both silently,
    # so `foreman.py ` and `foreman.py.` are also the same file), is refused outright.
    #
    # Refusing is the harmless direction, and nothing legitimate in this repo needs any of them.
    drive, tail = os.path.splitdrive(os.path.abspath(os.path.join(HERE, raw)))
    for comp in tail.replace("/", os.sep).split(os.sep):
        if not comp:
            continue
        if ":" in comp or comp != comp.rstrip(". "):
            return None
    if ":" in raw.replace("\\", "/").split("/")[-1]:
        return None
    full = drive + tail
    # A PREFIX IS NOT A DIRECTORY BOUNDARY. Found 2026-08-25 (run #23) by the comprehensive
    # sweep. `full.startswith(HERE)` is true for `C:\...\panscriptum-library-kit-EVIL\x.py`
    # and for `...-export\src\foo.py` -- any SIBLING whose name merely begins with this
    # project's name, including the export copy this whole file is forbidden to touch.
    # Comparing against `HERE + os.sep` makes the test mean what the docstring says.
    if not (full == HERE or full.startswith(HERE + os.sep)):
        return None
    if ".git" in full.split(os.sep):
        return None

    # AND THE SIXTH BYPASS: A JUNCTION IS A NAME INSIDE THE PROJECT THAT IS NOT A PLACE INSIDE
    # THE PROJECT. Found by the run #35 sweep, batch 16. Every check above this line runs on
    # `os.path.abspath`, which normalises a string and resolves NOTHING -- it does not follow a
    # symlink, a junction or a mount point. So a directory junction anywhere under `src/`,
    # `handoff/` or `prompts/` pointing at `state/`, `data/records/` or the charter satisfies
    # the allowlist, misses every denylist (the denied words are not in the path as written),
    # and `open(full, "w")` then follows the junction to the real protected file.
    #
    # This is the same family as the five bypasses documented above -- letter case, a name
    # prefix, an alternate data stream, a case-sensitive extension, an unlisted directory -- and
    # its shape is the one this file already names: A GATE KEYED ON A STRING WHILE THE
    # FILESYSTEM RESOLVES A DIFFERENT STRING TO THE SAME OBJECT. `mutate.py` junctions `data/`,
    # `prompts/` and `reference/` into its sandbox as a matter of course, so junctions pointing
    # out of a tree are not hypothetical here; they are a technique this project already uses.
    #
    # The decision is therefore made TWICE: once on the path as written, and once on the path
    # the filesystem actually resolves it to. A caller must satisfy both. Resolved with
    # `realpath` on both sides, because `HERE` may itself sit under a link.
    real = os.path.realpath(full)
    real_here = os.path.realpath(HERE)
    if not (real == real_here or real.startswith(real_here + os.sep)):
        return None
    if ".git" in real.split(os.sep):
        return None

    # ...AND THE JUNCTION FIX WAS INCOMPLETE AGAINST ITS OWN STATED THREAT MODEL (order
    # 6e0127c4f3ed). The resolved path used to be put to `_denied_region`, which asks ONE of the
    # three questions `t_propose_patch` asks -- the protected REGION prefixes -- and never the
    # protected PATHS. `config.yaml` is on `DENYLIST_PATHS` and in no `DENYLIST_PREFIXES`
    # region, so it was reachable through a junction from anywhere on the writable surface:
    # `handoff/cfg` -> the repo root made `handoff/cfg/config.yaml` an in-surface, undenied
    # string that `open(..., "w")` resolved onto the file holding `prose_enabled` and
    # `step4_enabled`. Reproduced end to end on a copy: `applied: True`, and `prose_enabled`
    # rewritten on disk. NOTHING DOWNSTREAM CATCHES IT -- `verify_math` asserts that
    # `prose_enabled` is a bool, never which bool, and says nothing at all about
    # `step4_enabled`, so the patch cleared the YAML parse gate and the whole-suite gate and
    # landed. That is bypass class SIX and the comment above names the very file it let through.
    #
    # The resolved path is now put to `_denied_target`, which asks all three -- module denylist,
    # DENYLIST_PATHS, DENYLIST_PREFIXES -- because "the same question" has to mean the same
    # question. Two spellings of this rule were two rules, and the narrower spelling was the one
    # standing behind the link.
    #
    # THE TRIGGER IS THE REDIRECTION, NOT `real != full`. `HERE` may itself sit under a link, in
    # which case `real != full` for EVERY path in the project and this test would start refusing
    # ordinary work. What matters is whether the path lands somewhere other than where it says:
    # compare the two project-relative spellings, and only interrogate the resolved one when the
    # filesystem disagrees with the string.
    rel_written = os.path.relpath(full, HERE)
    rel_real = os.path.relpath(real, real_here)
    if os.path.normcase(rel_written) != os.path.normcase(rel_real) and _denied_target(rel_real):
        # It resolved somewhere else INSIDE the project, and that somewhere is protected.
        # Refused rather than rewritten to the real path: a caller reaching a protected file
        # through a link is not a caller who should be quietly redirected.
        return None
    return full


def _denied_region(rel):
    """Is this project-relative path inside a protected REGION? -> bool (prefix rule only)."""
    rel = rel.replace("\\", "/").lower()
    return any(rel.startswith(p.lower()) for p in DENYLIST_PREFIXES)


def _denied_target(rel):
    """Is this project-relative path protected, by ANY of the three rules? -> bool.

    The three refusals `t_propose_patch` runs, in one predicate, so the junction check above can
    ask the SAME question of a resolved path that the patch gate asks of the written one:

      * the MODULE denylist, keyed on the basename of a `.py` -- the checking machinery, the
        contract-enforcement modules;
      * DENYLIST_PATHS, the non-module files with the same standing (`config.yaml`);
      * DENYLIST_PREFIXES, whole protected regions.

    Case-folded on both sides throughout, for the reason run #23 established one layer down: on
    this filesystem `Config.yaml` and `config.yaml` are the same bytes, and a denylist that errs
    toward denying is safe while one that errs toward allowing is the entire failure.
    """
    rel = rel.replace("\\", "/")
    rel_l = rel.lower()
    base = rel_l.rsplit("/", 1)[-1]
    if base.endswith(".py") and base[:-3] in {d.lower() for d in DENYLIST}:
        return True
    if rel_l in {p.lower() for p in DENYLIST_PATHS}:
        return True
    return _denied_region(rel)


def t_read_file(path, offset=0, **_):
    full = _safe(path)
    if not full or not os.path.isfile(full):
        return {"error": "no such file inside the project: " + str(path)}
    try:
        text = open(full, encoding="utf-8", errors="replace").read()
    except Exception as e:
        return {"error": type(e).__name__ + ": " + str(e)[:120]}
    off = max(0, int(offset or 0))
    return {"path": path, "offset": off, "slice": text[off:off + SLICE],
            "chars_after_slice": max(0, len(text) - off - SLICE), "total_chars": len(text)}


def t_list_dir(path=".", **_):
    full = _safe(path)
    if not full or not os.path.isdir(full):
        return {"error": "no such directory inside the project: " + str(path)}
    out = []
    for n in sorted(os.listdir(full)):
        p = os.path.join(full, n)
        out.append({"name": n, "dir": os.path.isdir(p),
                    "bytes": (os.path.getsize(p) if os.path.isfile(p) else None)})
    return {"path": path, "entries": out}


def t_grep(pattern, subtree="src", **_):
    """Search a regex over a directory OR A SINGLE FILE. -> {pattern, matches, hits}.

    A FILE USED TO BE A HARD ERROR AND IT COST THE WHOLE LOCAL RUNG A SHIFT. This required
    `os.path.isdir` and answered `no such subtree: src/drill.py` for a file -- a message that
    is true, useless, and does not say what to pass instead. Measured 2026-08-30 on a real work
    order: the model was told to confirm a symbol in `src/drill.py`, called
    `grep(pattern=..., subtree="src/drill.py")`, got that error, and RETRIED THE SAME CALL for
    all 24 turns and 70 tool calls before the turn budget killed it. Nothing was written and the
    order was not worked. Naming a specific file is the most natural thing a brief can ask for,
    so this refusal turned the free rung -- the one the owner's standing instruction says to
    route everything possible to -- into a deadlock generator.
    """
    full = _safe(subtree)
    if not full or not os.path.exists(full):
        return {"error": "no such path inside the project: %s. Pass a directory (e.g. 'src') "
                         "or a single file (e.g. 'src/drill.py')." % subtree}
    try:
        rx = re.compile(pattern)
    except re.error as e:
        return {"error": "bad regex: " + str(e)[:120]}
    hits = []

    def _scan(fp):
        try:
            for i, ln in enumerate(open(fp, encoding="utf-8", errors="replace"), 1):
                if rx.search(ln):
                    hits.append(os.path.relpath(fp, HERE) + ":" + str(i) + ": "
                                + ln.strip()[:200])
        except Exception:
            _ = "silence-exempt: an unreadable stray file is not this search's problem"

    if os.path.isfile(full):
        # NO EXTENSION FILTER ON AN EXPLICIT FILE. The filter below exists to keep a directory
        # walk off binaries and the mined corpus; a caller who named one file has already made
        # that choice, and second-guessing it would be another silent refusal.
        _scan(full)
    else:
        for base, dirs, files in os.walk(full):
            dirs[:] = [d for d in dirs if d not in ("__pycache__", ".git")]
            for f in files:
                if not f.endswith((".py", ".md", ".txt", ".yaml", ".json")):
                    continue
                _scan(os.path.join(base, f))
    return {"pattern": pattern, "matches": len(hits), "hits": hits}


def _gates(full, modname):
    """The foreman's bar, verbatim in spirit: parse, lint, import, whole-suite. Returns
    None when every gate passes, else the first failure's name.

    EVERY applied patch reaches this function, whatever the file's type. It used to be reached
    only for `.py` files -- `t_propose_patch` computed `modname` as None for anything else and
    then called the gates only `if modname`, so a patch to `config.yaml`, a prompt file or a
    `data/*.json` artifact was written to disk and reported `applied: True` having passed no
    check at all. That directly contradicted this module's own docstring, which promises a
    patch is applied only if it parses, lints, imports and leaves verify_math at 0 FAILED.

    The parse gate is per-format, because `ast.parse` on a YAML file is not a check, it is a
    guaranteed false rejection. verify_math runs for every type: it is the whole-suite gate,
    and a broken config.yaml is precisely the kind of damage only a whole-suite run catches.
    """
    # Case-folded, for the reason spelled out at `t_propose_patch` -- `src/foreman.PY` is the
    # same file on this filesystem and must get the same gates, not none of them.
    if full.lower().endswith(".py"):
        try:
            ast.parse(open(full, encoding="utf-8").read())
        except SyntaxError as e:
            return "does not parse: " + str(e)[:100]
        # PYTHONIOENCODING, LIKE EVERY OTHER SUBPROCESS IN THIS FILE (sweep42-batch16). The
        # three sibling calls all set it; this one did not, so pyflakes printing a non-ASCII
        # identifier or path could die on a UnicodeDecodeError on this machine. It fails safe --
        # the branch below treats a tool that did not run as a gate that did not pass, and the
        # patch is reverted -- so this is flakiness rather than a bypass. But a safety that
        # intermittently cannot run is a safety of unknown provenance, and the fix is one
        # argument long.
        r = subprocess.run([PY, "-m", "pyflakes", full], capture_output=True, text=True,
                           timeout=120, creationflags=_NO_WIN,
                           env=dict(os.environ, PYTHONIOENCODING="utf-8"))
        # A gate that cannot run has not passed. This tested `r.stdout` alone, so a pyflakes
        # that never executed -- uninstalled, or dying on its own traceback -- produced empty
        # stdout and was read as "no undefined names", waving the patch through. The very next
        # gate below checks `returncode`, which is what makes this an oversight rather than a
        # decision. pyflakes exits 0 clean and 1 when it has something to say, so only a code
        # outside that pair, or a stderr that looks like the tool itself failing, means the
        # check did not happen.
        _err = (r.stderr or "").strip()
        if r.returncode not in (0, 1) or "No module named" in _err or "Traceback" in _err:
            return ("pyflakes could not run (exit %s): %s" %
                    (r.returncode, (_err.splitlines() or ["no stderr"])[-1][:100]))
        if "undefined name" in (r.stdout or ""):
            return "pyflakes: " + r.stdout.strip().splitlines()[0][:120]
    # FOLDED HERE TOO. The `.py` branch above was case-folded after run #25 found that
    # `src/foreman.PY` lands on the real `foreman.py` (NTFS is case-insensitive) while failing a
    # case-sensitive `endswith(".py")`, so it skipped every gate. These two branches were left
    # case-sensitive in that same fix, which reopened the identical bypass one branch over:
    # `config.JSON` or a `.YAML` prompt file resolves to the same bytes on disk and skips its
    # parse check, leaving only verify_math -- and verify_math does not load arbitrary JSON or
    # YAML, so for those files the parse gate simply would not happen. Not reachable against any
    # file on the writable surface today (`prompts/` and `handoff/` hold no JSON or YAML), which
    # is exactly the condition under which the previous four bypasses were also "not currently
    # exploitable". This is bypass class five; fold the extension test every time one is written.
    elif full.lower().endswith(".json"):
        try:
            json.load(open(full, encoding="utf-8"))
        except Exception as e:
            return "not valid JSON: " + str(e)[:100]
    elif full.lower().endswith((".yaml", ".yml")):
        try:
            import yaml
            yaml.safe_load(open(full, encoding="utf-8"))
        except Exception as e:
            return "not valid YAML: " + str(e)[:100]
    if full.lower().endswith(".py") and modname:
        # THE IMPORT GATE USED TO CHECK A DIFFERENT FILE (order deeb24037ede, run #37). `modname`
        # is `os.path.basename(full)[:-3]`, and this ran `sys.path.insert(0, HERE/src); import
        # <modname>` -- so for a `.py` ANYWHERE BUT src/, the gate imported whichever src module
        # happened to share the basename. The writable surface includes `prompts/` and
        # `handoff/`, so a `handoff/silence.py` would have had its import gate satisfied by
        # `src/silence.py`: a file that was never patched, reporting `applied: True` on a patch
        # that may not import at all. Reproduced on a copy in %TEMP%: a temp `handoff/harmless.py`
        # patched to `import nosuchmodule_zzz_does_not_exist` returned `{'applied': True}`,
        # because `src/harmless.py` imported fine, and the broken file stayed on disk.
        #
        # Impact was bounded -- nothing imports `handoff/` or `prompts/`, and neither holds a
        # `.py` today -- and that is exactly the condition under which the five earlier bypasses
        # of this same gate were also "not currently exploitable". A gate checking the wrong
        # object is a gate, whether or not anything is standing in front of it yet.
        #
        # Fixed by asking WHERE the file is rather than what it is called. Inside src/, the
        # by-name import is kept unchanged: that is the real import path, it exercises the
        # package the way every caller will, and the existing five case-folding fixes all reason
        # about it. Outside src/, the file is loaded BY PATH, so the thing imported is the thing
        # patched -- with HERE/src still on sys.path so its own imports resolve exactly as they
        # would in a real run.
        _src_dir = os.path.join(HERE, "src")
        _in_src = (os.path.normcase(os.path.dirname(os.path.abspath(full)))
                   == os.path.normcase(os.path.abspath(_src_dir)))
        if _in_src:
            _code = "import sys; sys.path.insert(0, r'%s'); import %s" % (_src_dir, modname)
        else:
            _code = ("import sys, importlib.util as _u; sys.path.insert(0, r'%s'); "
                     "_s = _u.spec_from_file_location('_gate_probe', r'%s'); "
                     "_m = _u.module_from_spec(_s); _s.loader.exec_module(_m)"
                     % (_src_dir, full))
        r = subprocess.run([PY, "-c", _code],
                           capture_output=True, text=True, timeout=180,
                           env=dict(os.environ, PYTHONIOENCODING="utf-8"),
                           creationflags=_NO_WIN, cwd=HERE)
        if r.returncode != 0:
            return "import fails: " + (r.stderr or "").strip().splitlines()[-1][:120]
    # THE WHOLE-SUITE GATE RUNS FOR EVERY FILE TYPE, not just Python. config.yaml carries the
    # model, the host and the num_ctx every module reads; a prompt file carries the system text
    # the phases judge with. Breaking either does no damage that a parse check can see and every
    # damage a whole-suite run can. This is also the gate the docstring promises unconditionally.
    r = subprocess.run([PY, os.path.join(HERE, "src", "verify_math.py")],
                       capture_output=True, text=True, timeout=600,
                       env=dict(os.environ, PYTHONIOENCODING="utf-8"),
                       creationflags=_NO_WIN, cwd=HERE)
    # READ THE NUMBER, DO NOT SUBSTRING IT. verify_math prints "RESULT: N passed, M FAILED", and
    # `"0 FAILED" not in stdout` is FALSE for "10 FAILED", "20 FAILED" and "100 FAILED" -- the
    # zero is just the last digit of M -- so the gate PASSED any patch that broke a round number
    # of invariants. This is the last gate on the only lane in which a model may write into
    # `src/`, so the false positive kept exactly the patches worth reverting. `foreman._checks_pass`
    # carried the identical bug and was fixed with this same regex on 2026-08-23; the two are
    # deliberately kept in the same shape so a future reader sees one pattern, not two.
    # A missing or unreadable result line is a REFUSAL, not a pass: a verify_math that crashed
    # before printing is the state in which we know least about the patch.
    m = re.search(r"RESULT:\s*\d+\s+passed,\s*(\d+)\s+FAILED", r.stdout or "")
    if not m:
        return "verify_math produced no readable result line"
    if m.group(1) != "0":
        return "verify_math regressed (%s failing)" % m.group(1)
    return None


def t_propose_patch(path, find, replace, why="", apply=True, log=None, **_):
    # THE AUDIT TRAIL NOW RECORDS REFUSALS TOO, not only accepted patches. The entry used to be
    # created after every gate below had already passed, so a model repeatedly trying to patch a
    # denylisted path, a path outside the writable surface, a protected region, or a find string
    # that does not occur exactly once produced an empty `patches` list -- indistinguishable from
    # a run that never tried anything. `_settle` (below) already writes the outcome into this same
    # dict on every path out of the function; moving entry creation to the top and settling the
    # early refusals too means the log has an entry for every attempt, not only the ones that
    # cleared every gate. (Complement to the run #33 fix, which made outcome tracking honest for
    # ACCEPTED patches; this closes the identical gap for REFUSED ones. Found sweep34 batch 15.)
    entry = None
    if log is not None:
        entry = {"path": path, "why": (why or "")[:200], "find": (find or "")[:200],
                 "replace": (replace or "")[:200], "at": time.strftime("%H:%M:%S")}
        log.append(entry)

    def _settle(result):
        if entry is not None:
            entry["outcome"] = {k: result[k] for k in
                                ("applied", "staged", "reverted", "gate", "error", "ALARM")
                                if k in result}
        return result

    full = _safe(path)
    if not full or not os.path.isfile(full):
        return _settle({"applied": False, "error": "no such file: " + str(path)})
    # ...AND THE EXTENSION TEST HAS TO BE FOLDED TOO, which the run #23 fix below did not do.
    # Folding the denylist while deriving `modname` through a CASE-SENSITIVE `.endswith(".py")`
    # left the same door open one letter further along: `src/foreman.PY` resolves to the real
    # `foreman.py` on NTFS and passes `os.path.isfile`, but fails `endswith(".py")`, so
    # `modname` came out None, `_mod_l` came out "", and the case-folded module denylist was
    # never consulted at all. `DENYLIST_PATHS` holds only `config.yaml`, so nothing caught it
    # on the path side either -- and `_gates()` skipped the parse, lint and import checks for
    # the same reason, leaving only the whole-suite verify_math run. That is bypass FOUR, after
    # case (m113), name prefix (m114) and the NTFS alternate data stream (m121). Found run #25.
    _lower = full.lower()
    modname = os.path.basename(full)[:-3] if _lower.endswith(".py") else None
    # The denylist has to be answerable for NON-python files too. It used to be tested against
    # `modname`, which is None for anything that is not a `.py` -- so no non-python path could
    # ever be denied, and `config.yaml` (read by every module in the kit for model, host and
    # num_ctx) was freely writable by the local model. Match on the module name when there is
    # one, and on the repo-relative path otherwise.
    rel = os.path.relpath(full, HERE).replace(os.sep, "/")
    # THE DENYLIST IS CASE-SENSITIVE AND THE FILESYSTEM IS NOT. Found 2026-08-25 (run #23) by
    # the comprehensive sweep, reproduced on this machine: `path="src/Foreman.py"` passes
    # `os.path.isfile` (Windows resolves it to the real `foreman.py`), yields
    # `modname == "Foreman"`, which is not in a set holding `"foreman"` -- so the gate that
    # exists to stop the local model editing the checking machinery was defeated by ONE
    # CAPITAL LETTER, for `foreman`, `silence`, `standards`, `verify_math`, `health`,
    # `allsweep`, `estate` and `local_agent` (this file) alike.
    #
    # Folded on BOTH sides. A denylist that errs toward denying is safe; one that errs toward
    # allowing is the entire failure. This is not Windows-only defensiveness either: a
    # case-insensitive match on a case-sensitive filesystem can at worst refuse a patch to a
    # differently-cased file that does not exist, and refusing is the harmless direction.
    _deny = {d.lower() for d in DENYLIST}
    _deny_paths = {p.lower() for p in DENYLIST_PATHS}
    _mod_l = (modname or "").lower()
    denied = (modname if _mod_l in _deny
              else (rel if rel.lower() in _deny_paths else None))
    if denied:
        return _settle({"applied": False, "error": str(denied) + " is on the denylist -- the "
                                                                 "checking machinery may not "
                                                                 "edit itself"})
    _rel_l = rel.lower()
    # THE ALLOWLIST FAILS CLOSED, which is why it is here rather than last. A path outside the
    # agent's working surface is refused without any further question -- no denylist entry
    # required, and none needed for whatever gets added to this repo next.
    #
    # It is NOT, however, the first check in this function, and this comment used to say it was.
    # The real order is: name/path denylist, then this allowlist, then the protected-region
    # prefixes below. Nothing hangs on the order -- every one of the three refuses, none of them
    # writes, and a path that trips two is refused twice over -- but a comment that misdescribes
    # the sequence of a safety gate is how a later reader talks themselves into "re-ordering it
    # to match the comment", which is an edit to the gate made on a false premise. The order is
    # deliberate: the name denylist runs first because it is the narrowest and gives the most
    # specific refusal message ("the checking machinery may not edit itself"), which is the one
    # worth surfacing when both would fire.
    # ASKED OF BOTH SPELLINGS OF THE PATH — BYPASS CLASS SEVEN (found by sweep42-batch16,
    # verified against source and reproduced before fixing, 2026-09-02).
    #
    # `rel` is the path AS WRITTEN. `_safe()` above re-asks the DENYLIST of the RESOLVED path
    # when the two disagree, precisely because a junction can point one at the other — but it
    # never re-asks THIS list, and the two lists are not complements. A junction anywhere on the
    # writable surface (`src/`, `prompts/`, `handoff/`) pointing at a file that is merely
    # UNLISTED rather than denied therefore passed both gates: `src/link/COVERAGE.json` satisfies
    # the allowlist on the written spelling, and `data/COVERAGE.json` is on no denylist —
    # `DENYLIST_PREFIXES` holds `data/records/`, not `data/`. The write lands outside the
    # writable surface with every gate reporting a pass.
    #
    # That is the fifth-then-sixth lesson of this file arriving a seventh time, and it is the
    # same sentence each time: THE SAME QUESTION HAS TO MEAN THE SAME QUESTION. `_safe()`'s own
    # comment says it, about the denylist, forty lines up. The allowlist is the gate that FAILS
    # CLOSED, so leaving it asking about a string the filesystem has already disagreed with is
    # the more serious half of the pair — a denylist that misses is one hole, an allowlist that
    # misses is every file nobody thought to list.
    #
    # The check stays in `t_propose_patch` rather than moving into `_safe()` deliberately:
    # `_safe()` guards READS as well as writes, and the model is allowed to read a great deal
    # more of the project than it may write. Putting a write-surface test in there would refuse
    # honest reads.
    _spellings = [_rel_l]
    _real = os.path.realpath(full)
    _real_here = os.path.realpath(HERE)
    if _real == _real_here or _real.startswith(_real_here + os.sep):
        _spellings.append(os.path.relpath(_real, _real_here).replace(os.sep, "/").lower())
    for _s in _spellings:
        if not (any(_s.startswith(p) for p in WRITABLE_PREFIXES)
                or _s in {f.lower() for f in WRITABLE_FILES}):
            return _settle({"applied": False,
                    "error": "%s is outside the writable surface%s. The local model may write %s "
                             "and %s -- everything else is refused by default, including anything "
                             "added to this repo after this list was written."
                             % (rel, ("" if _s == _rel_l else
                                      " (it resolves to %s, which is not)" % _s),
                                ", ".join(WRITABLE_PREFIXES), ", ".join(WRITABLE_FILES))})
    # M24: whole protected REGIONS, folded the same way and for the same reason. Checked before
    # anything is read, so a protected path never even reaches the find/replace. Erring toward
    # refusal is the harmless direction.
    for _pfx in DENYLIST_PREFIXES:
        if _rel_l.startswith(_pfx):
            return _settle({"applied": False,
                    "error": "%s is inside the protected region '%s'. It is not edited by hand "
                             "or by a model: records go through pipeline.write_record, the "
                             "charter is the owner's, and shared state is landed via "
                             "silence.replace_retry." % (rel, _pfx)})
    original = open(full, encoding="utf-8").read()
    if original.count(find) != 1:
        return _settle({"applied": False,
                "error": "find string occurs %d times; it must occur exactly once -- copy "
                         "it verbatim from read_file" % original.count(find)})
    if not apply:
        return _settle({"applied": False, "staged": True,
                        "note": "run started with --no-apply; patch recorded for the audit trail"})
    # THE CAP IS CHARGED HERE, ONCE THE EDIT IS ACTUALLY ABOUT TO LAND, and not one line
    # earlier. It used to run right after the allow/deny checks -- BEFORE the find string had
    # even been checked for uniqueness and BEFORE `--no-apply` was consulted -- which billed the
    # budget for two more kinds of refusal the comment three lines up never accounted for: a
    # find string that does not occur exactly once, and a `--no-apply` dry run that stages but
    # never writes. Neither of those is an edit; both were being charged as if they were, so a
    # run that did nothing but propose ambiguous or staged patches could exhaust
    # MAX_PATCHES_PER_RUN/MAX_FILES_PER_RUN and trip the blast-radius refusal having never
    # written a byte. "A refused path costs no budget" now means what it says for every refusal
    # above this line, not only the allow/deny ones. Order 528e5b07fded.
    _ok, _why = _blast_ok(full)
    if not _ok:
        try:
            import escalation as _ESC
            _ESC.escalate(_ESC.MANAGER, "LOCAL_AGENT_BLAST_CAP", _why, who="local_agent")
        except Exception:
            # EVERY OTHER ESCALATION SITE IN THIS FILE RECORDS THE SWALLOW (see
            # local_agent.py:revert-escalate below); this one did not, so a broken or missing
            # escalation.py made the runaway signal vanish with no trace in the failure ledger.
            # The refusal itself still happens either way -- this is not a gate hole -- but the
            # blast cap's alarm should not be the quiet one. Found sweep34 batch 15.
            silence.note("local_agent.py:blast-cap-escalate")
        return _settle({"applied": False, "error": _why})
    backup = original
    try:
        with open(full, "w", encoding="utf-8") as f:
            f.write(original.replace(find, replace, 1))
        fail = _gates(full, modname)
        if fail:
            with open(full, "w", encoding="utf-8") as f:
                f.write(backup)
            return _settle({"applied": False, "reverted": True, "gate": fail})
        return _settle({"applied": True, "why": why[:200]})
    except Exception as e:
        silence.note("local_agent.py:apply")
        # A REVERT THAT FAILED MUST NOT REPORT ITSELF AS A REVERT. Found 2026-08-25 (run #23).
        # `"reverted": True` used to be a literal in this return, emitted even when the inner
        # write above had just raised -- so the one outcome that leaves a HALF-PATCHED MODULE
        # ON DISK was the outcome that claimed most confidently to have cleaned up after
        # itself. The gate's whole promise is "a bad patch cannot survive"; this path broke
        # that promise and then said it hadn't.
        reverted = True
        try:
            with open(full, "w", encoding="utf-8") as f:
                f.write(backup)
        except Exception:
            silence.note("local_agent.py:revert")
            reverted = False
        out = {"applied": False, "reverted": reverted,
               "error": type(e).__name__ + ": " + str(e)[:120]}
        if not reverted:
            out["ALARM"] = ("REVERT FAILED -- %s may be half-written on disk and the backup "
                            "is only in memory. Restore it by hand before anything imports "
                            "it." % rel)
            # AND IT NOW REACHES SOMETHING THAT OUTLIVES THE PROCESS. Until run #33 this ALARM
            # went nowhere a person would find: the console print in `run()` truncates the
            # result at `json.dumps(res)[:110]`, and the four keys ahead of it -- `applied`,
            # `reverted`, `error` (120 chars of it) -- push `ALARM` past the cut every time.
            # The `patches` audit trail records patch INTENT, never outcome, and neither
            # `run()`'s `ok` flag nor the exit code reflect a failed revert. So the one lane in
            # this project that lets a model write to `src/` could leave a half-written module
            # on disk while the run reported success. Found by the run #33 sweep (batch 16).
            #
            # SAFETY, deliberately -- rung 3 of the chain: "fail the BATTERY. No run may claim
            # success while this stands." That is the precise remedy for a source file left in
            # an unknown state, and it is one rung below OWNER because a person does not need
            # waking for a file that can be restored by hand; the library simply must not go on
            # pretending it is fine.
            try:
                import escalation as _ESC
                _ESC.escalate(_ESC.SAFETY, "LOCAL_AGENT_REVERT_FAILED", out["ALARM"],
                              source=rel, who="local_agent.propose_patch")
            except Exception:
                silence.note("local_agent.py:revert-escalate")
            silence.note("local_agent.py:REVERT-FAILED:" + str(rel))
        return _settle(out)


def _chat(model, messages, host, timeout=420):
    # num_ctx FROM CONFIG, not a literal. This read 8192 while config.yaml serves 12288, so
    # every local-agent task named a window the daemon did not have resident and paid for a
    # runner teardown+rebuild -- "240 s+, never completed" by gpu_lane.py's own measurement.
    # That is why this rung has been unreliable: not the model's competence, the window.
    # Same defect, same day, as standards.ollama_token_flow's 512. Pinned by verify_math S19ab.
    try:
        import yaml as _yaml
        _cfg = _yaml.safe_load(open(os.path.join(HERE, "config.yaml"), encoding="utf-8")) or {}
        _ctx = int(_cfg.get("num_ctx", 8192))
    except Exception:
        silence.note("local_agent.py:chat-ctx")
        _ctx = 8192
    body = {"model": model, "stream": False, "messages": messages, "tools": TOOLS,
            "options": {"num_ctx": _ctx, "temperature": 0.1}}
    req = urllib.request.Request(host.rstrip("/") + "/api/chat",
                                 data=json.dumps(body).encode(),
                                 headers={"Content-Type": "application/json"})
    # A 503 is Ollama's queue saying "not yet", not "no" -- under an evening pool the batch's
    # local fallbacks keep the queue full for minutes at a stretch. Waiting out a few rounds
    # is what every other patient consumer here does; a real outage still surfaces.
    import gpu_lane
    for attempt in range(4):
        try:
            # Background: the model lane is repair work, and it must never make the library's
            # own prose calls queue behind it. See gpu_lane's header for the measurements.
            with gpu_lane.lane("local_agent"):
                with urllib.request.urlopen(req, timeout=timeout) as r:
                    return json.loads(r.read()).get("message") or {}
        except urllib.error.HTTPError as e:
            if e.code != 503 or attempt == 3:
                raise
            time.sleep(60 * (attempt + 1))


def _tool_message(res, limit=TOOL_MSG_MAX):
    """Serialise one tool result for the transcript. ALWAYS valid JSON, never a blind prefix.

    Order 1b35c5c95fdd: the dispatch site used to append `json.dumps(res)[:SLICE]`, which cut
    the ENVELOPE. Every read of a file over ~11.9 KB -- most of src/ -- landed the cut inside
    the `slice` string, so the delivered content did not parse and the trailing
    `chars_after_slice` / `total_chars` keys, the two whose entire job is to say how much was
    not shown, were deleted. A `grep` with many hits was cut mid-list with no marker at all.

    The bound stays; where it applies changes. The largest field INSIDE the dict is shrunk
    before serialising and an explicit, readable marker is added, so:
      * the message always `json.loads()`, and
      * whatever was dropped is named in a key the model can read.
    For `slice` the companion `chars_after_slice` is recomputed to match the shorter slice,
    which keeps read_file's paging arithmetic true rather than merely non-lying. For list
    fields the count actually shown and the count omitted are both stated.
    """
    def dumped(d):
        return json.dumps(d)
    s = dumped(res)
    if len(s) <= limit or not isinstance(res, dict):
        return s
    out = dict(res)
    # Shrink whichever field is carrying the bulk, largest first, until the envelope fits.
    # Iterating rather than computing a budget once: JSON escaping makes the serialised cost
    # of a character unpredictable (a newline is two, a non-ASCII codepoint six), so the only
    # honest test of "does it fit" is to serialise and look.
    for _ in range(40):
        s = dumped(out)
        if len(s) <= limit:
            return s
        over = len(s) - limit
        # The list fields first: dropping whole hits is far more readable than a severed one.
        listy = [k for k in ("hits", "definitions", "entries")
                 if isinstance(out.get(k), list) and out[k]]
        if listy:
            k = max(listy, key=lambda k: len(dumped(out[k])))
            full_n = res.get(k)
            full_n = len(full_n) if isinstance(full_n, list) else len(out[k])
            keep = max(1, len(out[k]) - max(1, len(out[k]) * over // max(1, len(dumped(out[k])))))
            if keep >= len(out[k]):
                keep = len(out[k]) - 1
            out[k] = out[k][:keep]
            out[k + "_shown"] = keep
            out[k + "_omitted"] = full_n - keep
            # NOT the key `truncated`: t_run_check already returns one of its own and a marker
            # that overwrites another tool's verdict is a second silent loss.
            out["message_truncation"] = ("%d of %d %s shown -- narrow the pattern or ask again "
                                         "for the rest" % (keep, full_n, k))
            if keep <= 1 and len(dumped(out)) > limit:
                out[k] = []
                out[k + "_shown"] = 0
                out[k + "_omitted"] = full_n
            continue
        strs = [k for k in out if isinstance(out[k], str) and out[k]]
        if not strs:
            # Nothing left that can be shrunk honestly. Say so rather than cut the envelope.
            return dumped({"error": "tool result does not fit in %d characters and has no "
                                    "shrinkable field" % limit,
                           "keys": sorted(str(k) for k in out)})
        k = max(strs, key=lambda k: len(out[k]))
        keep = max(0, len(out[k]) - over - 64)
        out[k] = out[k][:keep]
        if k == "slice":
            # Keep read_file's paging arithmetic TRUE, not merely present: what remains after
            # the slice is measured from the slice actually delivered.
            base = res.get("total_chars")
            off = res.get("offset")
            if isinstance(base, int) and isinstance(off, int):
                out["chars_after_slice"] = max(0, base - off - keep)
            out["slice_shortened_to_fit"] = keep
        else:
            out[k + "_shortened_to_fit"] = keep
        out["message_truncation"] = ("field '%s' shortened to %d characters to fit the "
                                     "%d-character tool message budget" % (k, keep, limit))
    return dumped({"error": "tool result could not be reduced to %d characters" % limit})


def _achievement(patches, apply, answer=None):
    """-> {'attempted', 'landed', 'achievement'}: what this run actually DID to the repo.

    OK USED TO MEAN "THE MODEL STOPPED TALKING WITHOUT BREAKING ANYTHING", which is the one
    thing a caller never needs to know. Measured 2026-08-25 on a real order: the model spent 6
    turns and 5 tool calls, every propose_patch refused with "find string occurs 0 times"
    because it could not reproduce the target text verbatim, and the run returned
    {"ok": true, "patches": []} -- indistinguishable, to a caller, from work done. A
    maintenance run bulk-routing the LOCAL rung on that flag would close every such order
    having changed nothing. The outcomes were already in the audit trail (`_settle` writes
    one into every entry); nothing read them back.

    A run that ATTEMPTED patches and landed NONE is a failure, and `run()` sets ok=False on
    it. A run that attempted none is an answer-only task -- a question, a survey, a
    --no-apply dry pass -- and its verdict is left alone, because "changed no files" is the
    correct outcome there and failing it would make the flag lie in the other direction.

    ...EXCEPT WHEN THE ANSWER IS BLANK, which is the same lie one step over. Measured
    2026-08-30 on a real work order: the model read one file, said nothing at all, and the run
    returned `{"ok": true, "answer": "", "patches": []}` with the achievement line
    "no patch was attempted (answer-only run)". Neither work nor an answer, reported as success.
    The empty-answer guard that already existed covered only `turn == 0` -- "the model is not
    tool-trained" -- so a model that stopped talking on any LATER turn came back clean. An
    answer-only run whose answer is empty produced nothing at all, and a caller closing an order
    on `ok` gets exactly the outcome `_achievement` was written to stop.

    `answer=None` means the caller did not say, and is left alone: the drill's fixtures put
    patch lists to this function without one, and widening their meaning is not this guard's
    job.
    """
    attempted = len(patches)
    key = "staged" if not apply else "applied"
    landed = sum(1 for p in patches if (p.get("outcome") or {}).get(key) is True)
    if not attempted and answer is not None and not str(answer).strip():
        say = ("no patch was attempted AND the answer is empty -- this run produced nothing at "
               "all. Do not record it as work done.")
    elif not attempted:
        say = "no patch was attempted (answer-only run) -- nothing was written"
    elif landed:
        say = "%d of %d proposed patch(es) %s" % (landed, attempted,
                                                  "staged" if not apply else "landed")
    else:
        say = ("%d patch(es) proposed and NONE %s -- every one was refused or reverted. "
               "This run changed nothing; do not record it as work done."
               % (attempted, "staged" if not apply else "landed"))
    return {"attempted": attempted, "landed": landed, "achievement": say,
            "produced_nothing": bool(not attempted and answer is not None
                                     and not str(answer).strip())}


def run(task, model=None, apply=True, quiet=False):
    # THE HALT IS CHECKED HERE, AND UNTIL RUN #35 IT WAS NOT CHECKED ANYWHERE ON THIS LANE.
    #
    # Twelve modules consult `escalation.assert_clear()` before doing work -- pipeline, publish,
    # feats, read, foreman, overnight, overwatch, allsweep, dashboard, drill, verify_math and
    # escalation itself. This one did not, and it is the ONLY lane in the project on which a
    # model may WRITE TO `src/`. An OWNER halt means "nothing starts until a person rules on
    # it", and the actor most able to make a halted situation worse was the one actor not
    # asking. Found by the run #35 sweep, batch 16, which also noted that `local_agent` was
    # absent from verify_math's own roster of interlocked jobs -- so nothing was checking that
    # nothing was checking.
    #
    # Raised, not swallowed: `assert_clear` throws, and a refusal to start under a halt is the
    # correct outcome, not an error to route around.
    import escalation as _ESC
    _ESC.assert_clear(who="local_agent.run")
    # Each invocation gets a fresh blast budget; the cap bounds ONE run, not the life of
    # the process.
    blast_reset()
    import yaml
    cfg = yaml.safe_load(open(os.path.join(HERE, "config.yaml"), encoding="utf-8"))
    model = model or cfg.get("model")
    host = cfg.get("ollama_host", "http://localhost:11434")
    messages = [{"role": "system", "content": SYSTEM},
                {"role": "user", "content": task}]
    patches, tool_calls_seen = [], 0
    # A FAILED REVERT MUST REACH THE EXIT CODE. `t_propose_patch` raises the durable alarms for
    # this case -- a SAFETY escalation and a `silence.note` -- but this function's verdict never
    # heard about it: `ok` was True whenever the model produced an answer, and `main()` returns
    # `0 if out.get("ok")`, so a run that left a half-written module in `src/` exited zero and
    # any caller gating on the exit code read it as success. Every alarm in the world is worth
    # less than the one number the scheduler actually looks at. Collected here rather than
    # returned early on purpose: the run is already compromised, the model's remaining turns are
    # gated exactly as before, and stopping mid-conversation would lose the transcript that says
    # how the file got into this state.
    unreverted = []
    impl = {"read_file": t_read_file, "list_dir": t_list_dir, "grep": t_grep,
            "find_symbol": t_find_symbol, "run_check": t_run_check}
    for turn in range(MAX_TURNS):
        try:
            msg = _chat(model, messages, host)
        except Exception as e:
            return {"ok": False, "error": "transport: " + type(e).__name__ + " "
                    + str(e)[:120], "patches": patches}
        calls = msg.get("tool_calls") or []
        if not calls:
            answer = (msg.get("content") or "").strip()
            if turn == 0 and not answer:
                # Neither a tool call nor an answer on the very first turn: the model is
                # not carrying the tool template. Name ones that do, per the owner's brief.
                return {"ok": False, "error": "model '%s' emitted no tool call and no "
                        "answer -- likely not tool-trained. Tool-capable models that fit "
                        "this card: %s" % (model, "; ".join(TOOL_CAPABLE)),
                        "patches": patches}
            out = {"ok": not unreverted, "answer": answer, "turns": turn + 1,
                   "tool_calls": tool_calls_seen, "patches": patches}
            got = _achievement(patches, apply, answer=answer)
            out.update(got)
            if got["attempted"] and not got["landed"]:
                # TRIED AND LANDED NOTHING IS NOT SUCCESS. See the note on _achievement.
                out["ok"] = False
                out.setdefault("error", got["achievement"])
            elif got["produced_nothing"]:
                # NEITHER WORK NOR AN ANSWER IS NOT SUCCESS EITHER, and it read as one
                # until 2026-08-30. Same rule as the line above, one step over.
                out["ok"] = False
                out.setdefault("error", got["achievement"])
            if unreverted:
                out["ALARM"] = unreverted
                out["error"] = ("revert failed on %d patch(es) -- a source file may be "
                                "half-written on disk. This run does not claim success."
                                % len(unreverted))
            return out
        messages.append(msg)
        for c in calls:
            tool_calls_seen += 1
            fn = (c.get("function") or {}).get("name")
            args = (c.get("function") or {}).get("arguments") or {}
            if isinstance(args, str):
                try:
                    args = json.loads(args)
                except Exception:
                    args = {}
            # A MALFORMED TOOL CALL MUST NOT END THE RUN. `args` comes straight from the model
            # (a dict decoded from its own JSON), so a bad shape -- an `apply` key colliding
            # with the keyword this function already passes, a missing required `path` -- used
            # to raise an uncaught TypeError here and kill the whole turn loop with a traceback
            # instead of handing the model an error dict it could read and correct. Every other
            # bad input in this file is answered with {'error': ...}; this makes tool dispatch
            # consistent with that instead of being the one place that loses the transcript.
            # Found sweep34 batch 15.
            try:
                if fn == "propose_patch":
                    res = t_propose_patch(apply=apply, log=patches, **args)
                    if res.get("ALARM"):
                        unreverted.append(res["ALARM"])
                elif fn in impl:
                    res = impl[fn](**args)
                else:
                    res = {"error": "no such tool: " + str(fn)}
            except TypeError as e:
                res = {"error": "bad arguments for %s: %s" % (fn, str(e)[:160])}
            if not quiet:
                print("  [%s] %s -> %s" % (fn, json.dumps(args)[:90],
                                           json.dumps(res)[:110]), flush=True)
            # `json.dumps(res)[:SLICE]` here cut the ENVELOPE, not the payload -- see
            # `_tool_message` and TOOL_MSG_MAX. Every tool message this loop appends now
            # parses as JSON and names whatever it left out.
            msg_content = _tool_message(res)
            try:
                # THE STANDING CHECK, cheap and on every message. A tool result the model
                # cannot parse is the defect this order was filed for; if a future tool
                # returns a shape `_tool_message` cannot reduce, the model gets a readable
                # error instead of half a dict, and the ledger records that it happened.
                json.loads(msg_content)
            except ValueError:
                silence.note("local_agent.py:tool-message-not-json")
                msg_content = json.dumps(
                    {"error": "the %s result could not be delivered as valid JSON; nothing "
                              "from it is shown rather than part of it" % fn})
            messages.append({"role": "tool", "content": msg_content})
    out = {"ok": False, "error": "turn budget (%d) exhausted" % MAX_TURNS,
           "patches": patches, "tool_calls": tool_calls_seen}
    out.update(_achievement(patches, apply))
    if unreverted:
        # THE SAME ALARM THE "NO TOOL CALLS" EXIT PATH ABOVE ALREADY SURFACES, and until now
        # this path dropped it. The exit code here was already correct (`ok` is False either
        # way), but the diagnostic saying a source file may be half-written on disk went
        # missing on exactly the path a run going badly is most likely to take -- exhausting
        # MAX_TURNS while still cleaning up after a failed patch is a worse-behaving run than
        # one that simply finished talking, not a better-behaved one. Order d185007c4b8b.
        out["ALARM"] = unreverted
        out["error"] = ("turn budget (%d) exhausted, AND revert failed on %d patch(es) -- a "
                        "source file may be half-written on disk. This run does not claim "
                        "success." % (MAX_TURNS, len(unreverted)))
    return out


def main():
    ap = argparse.ArgumentParser(description="the GPU model, with gated hands on the repo")
    ap.add_argument("--task", required=True)
    ap.add_argument("--model", help="override config.yaml's model")
    ap.add_argument("--no-apply", action="store_true",
                    help="stage patches for the audit trail, write nothing")
    a = ap.parse_args()
    out = run(a.task, model=a.model, apply=not a.no_apply)
    # THE VERDICT FIRST, UNCONDITIONALLY, AND NEVER INSIDE THE CUT (order db8460375fdc).
    # `out['patches']` holds up to MAX_PATCHES_PER_RUN=24 audit entries carrying why/find/
    # replace text, and it is inserted BEFORE `achievement`, `error` and `ALARM` -- so on a
    # realistic run the dump is ~20 KB and the three keys that say what happened all fall past
    # the 8000th character. This is the same shape the ALARM at t_propose_patch's revert path
    # was rescued from: the durable channels were intact and the console, where a person looks
    # first, showed a wall of patch text and no conclusion.
    print("ok:          %s" % out.get("ok"))
    if out.get("achievement"):
        print("achievement: %s" % out["achievement"])
    if out.get("error"):
        print("error:       %s" % out["error"])
    if out.get("ALARM"):
        for _a in (out["ALARM"] if isinstance(out["ALARM"], list) else [out["ALARM"]]):
            print("ALARM:       %s" % _a)
    body = json.dumps(out, indent=1, ensure_ascii=False)
    # The dump stays bounded -- 24 patches of stored find/replace text is not a console read --
    # but the cut is now STATED, the way t_run_check labels its own output_tail, and the
    # verdict above is outside it either way.
    if len(body) > 8000:
        print("-- full result: %d characters, showing the first 8000 --" % len(body))
        body = body[:8000]
    print(body)
    return 0 if out.get("ok") else 1


if __name__ == "__main__":
    sys.exit(main())
