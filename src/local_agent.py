#!/usr/bin/env python3
"""LOCAL_AGENT — the GPU model with hands: read, search, and gated writes on this repo.

OWNER RULING 2026-08-23: the delegation ladder runs bots -> OLLAMA -> Claude subagents ->
Claude, and the Ollama rung must be able to read and write files, not merely answer prompts.
A model is text-in/text-out; FILE ACCESS IS A HARNESS PROPERTY -- so this module is the
harness. It drives Ollama's /api/chat tool-calling loop (Qwen3 is tool-trained; the harness
PROBES rather than assumes, and names tool-capable models that fit the card if the configured
one is not) and hands the model four tools:

    read_file    any file under the project, sliced -- iterative reads, never a truncation
    list_dir     one level of the tree
    grep         a regex over src/ (or a named subtree), every match with file:line
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
DENYLIST = {"foreman", "silence", "health", "allsweep", "estate", "standards",
            "verify_math", "local_agent"}

# The same bar, for files that are not python modules and therefore have no module name to
# match on. Repo-relative, forward slashes. config.yaml is here because every module in the kit
# reads it for the model, the host and num_ctx: one bad edit misroutes the whole pipeline, and
# unlike a broken .py it fails silently rather than at import.
DENYLIST_PATHS = {"config.yaml"}

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
                       "parse and import), 'silence' (the swallowed-exception audit).",
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
        argv = [PY, "-c",
                "import py_compile,sys; py_compile.compile(sys.argv[1], doraise=True); "
                "print('parses OK')", target or os.path.join(HERE, "src", "verify_math.py")]
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
    return full


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
    full = _safe(subtree)
    if not full or not os.path.isdir(full):
        return {"error": "no such subtree: " + str(subtree)}
    try:
        rx = re.compile(pattern)
    except re.error as e:
        return {"error": "bad regex: " + str(e)[:120]}
    hits = []
    for base, dirs, files in os.walk(full):
        dirs[:] = [d for d in dirs if d not in ("__pycache__", ".git")]
        for f in files:
            if not f.endswith((".py", ".md", ".txt", ".yaml", ".json")):
                continue
            fp = os.path.join(base, f)
            try:
                for i, ln in enumerate(open(fp, encoding="utf-8", errors="replace"), 1):
                    if rx.search(ln):
                        hits.append(os.path.relpath(fp, HERE) + ":" + str(i) + ": "
                                    + ln.strip()[:200])
            except Exception:
                _ = "silence-exempt: an unreadable stray file is not this search's problem"
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
    if full.endswith(".py"):
        try:
            ast.parse(open(full, encoding="utf-8").read())
        except SyntaxError as e:
            return "does not parse: " + str(e)[:100]
        r = subprocess.run([PY, "-m", "pyflakes", full], capture_output=True, text=True,
                           timeout=120, creationflags=_NO_WIN)
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
    elif full.endswith(".json"):
        try:
            json.load(open(full, encoding="utf-8"))
        except Exception as e:
            return "not valid JSON: " + str(e)[:100]
    elif full.endswith((".yaml", ".yml")):
        try:
            import yaml
            yaml.safe_load(open(full, encoding="utf-8"))
        except Exception as e:
            return "not valid YAML: " + str(e)[:100]
    if full.endswith(".py") and modname:
        r = subprocess.run([PY, "-c", "import sys; sys.path.insert(0, r'%s'); import %s"
                            % (os.path.join(HERE, "src"), modname)],
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
    if "0 FAILED" not in (r.stdout or ""):
        return "verify_math regressed"
    return None


def t_propose_patch(path, find, replace, why="", apply=True, log=None, **_):
    full = _safe(path)
    if not full or not os.path.isfile(full):
        return {"applied": False, "error": "no such file: " + str(path)}
    modname = os.path.basename(full)[:-3] if full.endswith(".py") else None
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
        return {"applied": False, "error": str(denied) + " is on the denylist -- the checking "
                                                         "machinery may not edit itself"}
    original = open(full, encoding="utf-8").read()
    if original.count(find) != 1:
        return {"applied": False,
                "error": "find string occurs %d times; it must occur exactly once -- copy "
                         "it verbatim from read_file" % original.count(find)}
    if log is not None:
        log.append({"path": path, "why": why[:200], "find": find[:200],
                    "replace": replace[:200], "at": time.strftime("%H:%M:%S")})
    if not apply:
        return {"applied": False, "staged": True,
                "note": "run started with --no-apply; patch recorded for the audit trail"}
    backup = original
    try:
        with open(full, "w", encoding="utf-8") as f:
            f.write(original.replace(find, replace, 1))
        fail = _gates(full, modname)
        if fail:
            with open(full, "w", encoding="utf-8") as f:
                f.write(backup)
            return {"applied": False, "reverted": True, "gate": fail}
        return {"applied": True, "why": why[:200]}
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
        return out


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


def run(task, model=None, apply=True, quiet=False):
    import yaml
    cfg = yaml.safe_load(open(os.path.join(HERE, "config.yaml"), encoding="utf-8"))
    model = model or cfg.get("model")
    host = cfg.get("ollama_host", "http://localhost:11434")
    messages = [{"role": "system", "content": SYSTEM},
                {"role": "user", "content": task}]
    patches, tool_calls_seen = [], 0
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
            return {"ok": True, "answer": answer, "turns": turn + 1,
                    "tool_calls": tool_calls_seen, "patches": patches}
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
            if fn == "propose_patch":
                res = t_propose_patch(apply=apply, log=patches, **args)
            elif fn in impl:
                res = impl[fn](**args)
            else:
                res = {"error": "no such tool: " + str(fn)}
            if not quiet:
                print("  [%s] %s -> %s" % (fn, json.dumps(args)[:90],
                                           json.dumps(res)[:110]), flush=True)
            messages.append({"role": "tool", "content": json.dumps(res)[:SLICE]})
    return {"ok": False, "error": "turn budget (%d) exhausted" % MAX_TURNS,
            "patches": patches, "tool_calls": tool_calls_seen}


def main():
    ap = argparse.ArgumentParser(description="the GPU model, with gated hands on the repo")
    ap.add_argument("--task", required=True)
    ap.add_argument("--model", help="override config.yaml's model")
    ap.add_argument("--no-apply", action="store_true",
                    help="stage patches for the audit trail, write nothing")
    a = ap.parse_args()
    out = run(a.task, model=a.model, apply=not a.no_apply)
    print(json.dumps(out, indent=1, ensure_ascii=False)[:8000])
    return 0 if out.get("ok") else 1


if __name__ == "__main__":
    sys.exit(main())
