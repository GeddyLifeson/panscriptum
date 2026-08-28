"""LIVENESS — find the checks that cannot fail and the code that never runs.

THE STANDING LESSON THIS AUTOMATES. "A check that cannot fail looks exactly like a check that
passed" is the most-repeated finding in this project's ledger, and every instance has been found
by a person reading the file. Instances already caught by hand:

  * `profile.py:182-187` -- a round-trip self-test comparing a decoded field against the input it
    was handed, so `d["profile"] != r["profile"]` is tautologically False. Green for ever.
  * `cleanup.py:77-80` -- a guard whose condition names a regex that is never defined.
  * `coverage._p()` -- a fully documented cache-path helper with no callers, free to drift out of
    step with the real formula it duplicates.
  * `overnight._prose_enabled` -- for one commit, a docstring-only "FAILS CLOSED" claim tested by
    `"FAILS CLOSED" in __doc__`, which passes no matter what the function does.
  * `standards.py`'s vanished HIGH guard -- a check that read a job-dict key nothing sets, so it
    was never appended to the page at all. Not red, not green: ABSENT, for its whole life.

Reading for these is not a strategy that scales to 95 modules and 40,000 lines. This finds the
three mechanical shapes:

  DEAD        a module-level function OR A METHOD nobody calls, from anywhere in src/. It cannot
              fail because it never runs, and it silently drifts from whatever it duplicates.
              (Methods were invisible to this pass until run #36 -- it walked `Module.body` and
              stepped over every `ClassDef` whole. See `_defs`.)
  TAUTOLOGY   a comparison whose two sides are the same expression. Always True or always False,
              regardless of the data it claims to be checking.
  PHANTOM     a name used in a condition that is never defined, imported or assigned in its
              module -- the `cleanup.py` shape, which raises only on the branch nobody takes.

WHAT IT DELIBERATELY DOES NOT DO. It does not judge whether a live check is a GOOD check; that is
what the drill and the adversarial audits are for. It answers the narrower, mechanical question
this project keeps losing money on: is this code capable of running, and is this comparison
capable of being false?

AND ITS HONEST LIMIT, STATED BECAUSE THE ALTERNATIVE IS FALSE ASSURANCE. The TAUTOLOGY pass is
SYNTACTIC: it finds comparisons whose two sides are the same expression. It does NOT find the
`profile.py:182-187` instance that motivated it, because that one is SEMANTIC --
`d = decode(r["profile"])` and then `d["profile"] != r["profile"]`, which is always False only
if you know what `decode` returns. Two different expressions, one guaranteed answer. Catching
that class needs dataflow this module does not do, so `profile.py` stays on the human list.
Reporting zero tautologies must not be read as "there are none".

FALSE POSITIVES ARE EXPECTED AND ARE NOT SUPPRESSED SILENTLY. Entry points, CLI handlers, tool
callbacks and test scaffolding are legitimately "uncalled" within src/. They are listed in
`EXEMPT` with a reason each, because an exemption with no reason attached is how a real finding
gets waved through next time.
"""
import argparse
import ast
import os

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.dirname(os.path.abspath(__file__))

# Names that are legitimately never called from inside src/, with the reason. A bare skip-list
# rots into a place to hide findings; a reason makes each entry answerable.
EXEMPT = {
    "main": "CLI entry point, called by __main__",
    "__init__": "constructor",
    "__repr__": "protocol",
    "__str__": "protocol",
    "__enter__": "protocol",
    "__exit__": "protocol",
    # Added run #36 with the widening of DEAD to methods (see `_defs`). Both are framework
    # hooks on an http.server handler, dispatched BY THE SERVER and correctly never called from
    # src/ -- `handle_one_request` does `getattr(self, 'do_' + command)`. They are the only two
    # false positives the widening produced across the whole tree, and they are named here with
    # their reason rather than waved through by a broad `do_*` prefix, which would also exempt
    # any ordinary method somebody happened to call `do_thing`.
    "do_GET": "http.server dispatches request handlers by verb name via getattr",
    "do_POST": "http.server dispatches request handlers by verb name via getattr",
    "do_HEAD": "http.server dispatches request handlers by verb name via getattr",
    "log_message": "BaseHTTPRequestHandler hook called by the server; overridden to silence it",
}
# Prefixes for tool callbacks dispatched by name through a table rather than called directly.
EXEMPT_PREFIXES = ("t_", "test_", "cmd_", "phase_", "check_", "drill_")


def _modules():
    for f in sorted(os.listdir(SRC)):
        if f.endswith(".py") and not f.startswith("_"):
            yield f, os.path.join(SRC, f)


def _parse(path):
    try:
        with open(path, encoding="utf-8") as fh:
            return ast.parse(fh.read(), filename=path)
    except Exception:
        return None


def _defs(tree, prefix=""):
    """Every function the DEAD pass considers, as (name, label, node).

    MODULE-LEVEL FUNCTIONS **AND METHODS**. Until run #36 this pass iterated `Module.body` and
    skipped anything that was not a FunctionDef there, so a `ClassDef` was stepped over whole
    and every method inside it was never a DEAD candidate -- not exempted, not judged, absent.
    Twelve modules in this tree define classes; `entity_match.py` and `verify_math.py` among
    them. A detector that never looks at a construct reports zero findings in it, and zero
    findings is exactly what a clean module also reports. This is the same shape as the flat
    `used` set that hid `coverage._p()`: a floor being read as a total.

    A method is not harder to judge than a function, because Python resolves it the same way
    the `used` set already models: `self.foo()` and `obj.foo()` are ATTRIBUTES, which are
    collected globally, so any method reached through an instance anywhere in src/ counts as
    used. What surfaces is the method nothing ever names.

    Nested classes recurse, and the label carries the dotted path so a report line names the
    class -- `entity_match.py:88 Resolver.rebuild()` is answerable, `rebuild()` is not.
    """
    for node in tree.body:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            yield node.name, prefix + node.name, node
        elif isinstance(node, ast.ClassDef):
            for got in _defs(node, prefix + node.name + "."):
                yield got


def scan():
    """-> {'dead': [...], 'tautology': [...], 'phantom': [...]} over every module in src/."""
    trees, used, unparsed = {}, set(), []
    for name, path in _modules():
        t = _parse(path)
        if t is None:
            # A MODULE THAT WILL NOT PARSE IS NOT A CLEAN MODULE. Until run #33 this `continue`
            # was silent, so a source file that failed to parse -- including from the literal
            # control-character corruption this project has hit more than once, and from
            # `local_agent`'s gated writes being killed mid-write -- vanished from every check
            # below and reported exactly like a module with nothing wrong in it. The scanner
            # whose whole purpose is finding checks that cannot fail had one at its own
            # foundation. Reported as a finding of its own, so the count rises and the ratchet
            # in `drill.py` sees it. Found by the run #33 sweep (batch 08).
            unparsed.append("%s: will not parse -- excluded from every liveness check" % name)
            continue
        trees[name] = t

    # USAGE IS RESOLVED THE WAY PYTHON RESOLVES IT: a bare name only reaches a function in the
    # SAME module; a cross-module call has to arrive as `mod.name`, `from mod import name`, or a
    # string handed to getattr/a dispatch table.
    #
    # THE BUG THIS REPLACES, and it hid the founding example in this file's own docstring. The
    # `used` set was one flat, scope-blind, module-blind bag of every identifier anywhere in
    # `src/`. So a LOCAL LOOP VARIABLE named `_p` -- `for _p in ...` in cleanup.py and tells.py
    # -- marked every module-level `_p()` in the project as called, and `coverage._p()`, which
    # has zero callers and is named at liveness.py:10 as the reason this module exists, was
    # absent from its own report. A detector that cannot see its own worked example is reporting
    # a floor and calling it a total, and `drill.LIVENESS_CEILING` was ratcheting that floor.
    #
    # Bare names are collected PER MODULE and only count for that module's own functions.
    # Attributes, `from X import name`, and string constants are global, because all three are
    # how a name legitimately crosses a module boundary. Erring toward "it is used" is still the
    # rule -- a false DEAD is expensive to chase -- but the erring is now scoped.
    used_local = {}
    for name, t in trees.items():
        local = set()
        for node in ast.walk(t):
            if isinstance(node, ast.Name):
                # LOAD only. A `for _p in ...` or `_p = 1` BINDS the name, it does not call
                # anything, and counting bindings as calls is precisely what went wrong.
                if isinstance(node.ctx, ast.Load):
                    local.add(node.id)
            elif isinstance(node, ast.Attribute):
                used.add(node.attr)                       # `mod.thing()` -- crosses modules
            elif isinstance(node, ast.ImportFrom):
                for al in node.names:
                    used.add(al.name)                     # `from mod import thing`
                    if al.asname:
                        used.add(al.asname)
            elif isinstance(node, ast.Constant) and isinstance(node.value, str):
                used.add(node.value.strip())              # getattr / dispatch table
        used_local[name] = local

    dead, taut, phantom = [], [], []
    for name, t in trees.items():
        # --- DEAD: module-level defs and METHODS nobody references (see `_defs`)
        for fn, label, node in _defs(t):
            if fn in EXEMPT or fn.startswith(EXEMPT_PREFIXES) or fn.startswith("__"):
                continue
            # Membership in the pre-built sets. The first version re-walked every tree for every
            # function -- 95 modules x ~40,000 lines, per def -- and did not finish inside two
            # minutes. A check nobody can afford to run is a check that does not run, which is
            # the very thing this module exists to find.
            #
            # TWO SETS, not one: `used` is the cross-module surface (attributes, from-imports,
            # dispatch strings) and `used_local[name]` is what this module itself loads. A bare
            # name in ANOTHER module cannot reach this function, which is the whole correction.
            if fn not in used and fn not in used_local.get(name, ()):
                dead.append("%s:%d %s()" % (name, node.lineno, label))

        # --- TAUTOLOGY: a comparison whose sides are the same expression
        for node in ast.walk(t):
            if not isinstance(node, ast.Compare) or len(node.comparators) != 1:
                continue
            try:
                left = ast.dump(node.left)
                right = ast.dump(node.comparators[0])
            except Exception:
                continue
            if left == right and not isinstance(node.left, ast.Constant):
                op = type(node.ops[0]).__name__
                taut.append("%s:%d both sides identical (%s)" % (name, node.lineno, op))

        # --- PHANTOM: a name used in an `if` test that the module never defines
        # Seeded from `EXEMPT` and, below, from the `builtins` MODULE. It used to seed from
        # `dir(__builtins__)` as well, which is only the builtins module when a file runs as
        # `__main__`: on import CPython binds `__builtins__` to the builtins DICT, so `dir()`
        # returned dict methods -- `get`, `items`, `keys`, `update`, `pop`, `copy` and 37 more
        # -- and every one of them became a spurious exemption. A guard naming an undefined
        # `get` would have been waved through, in the module whose whole job is finding guards
        # that cannot fire. Nothing was lost by dropping it: `import builtins` below supplies
        # the real names, which is why this never showed as a false negative on the real ones.
        defined = set(EXEMPT)
        for n2 in ast.walk(t):
            if isinstance(n2, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                defined.add(n2.name)
            elif isinstance(n2, ast.Name) and isinstance(n2.ctx, ast.Store):
                defined.add(n2.id)
            elif isinstance(n2, ast.arg):
                defined.add(n2.arg)
            elif isinstance(n2, (ast.Import, ast.ImportFrom)):
                for al in n2.names:
                    defined.add((al.asname or al.name).split(".")[0])
            elif isinstance(n2, ast.ExceptHandler) and n2.name:
                defined.add(n2.name)
            elif isinstance(n2, (ast.Global, ast.Nonlocal)):
                defined.update(n2.names)
        import builtins
        defined |= set(dir(builtins))
        # Module globals the interpreter supplies. Omitting these made every `_BAD_CHARS` source
        # self-check in the kit -- 43 of them, one per module -- report as a guard on an
        # undefined name. A detector whose output is 100% false positives gets ignored within a
        # day, and an ignored detector is indistinguishable from an absent one.
        defined |= {"__file__", "__name__", "__doc__", "__package__", "__spec__",
                    "__loader__", "__builtins__", "__debug__"}
        # EVERY CONDITION, NOT ONLY `if`. Until run #36 this walked `n2.test` only when `n2` was
        # an `ast.If`, so the identical shape -- a branch or filter that raises NameError only
        # when taken, and which nothing takes today -- was structurally invisible in a `while`
        # condition, an `assert`, a ternary, and a comprehension's `if` filter. cleanup.py:77-80,
        # the founding example in this file's own docstring, is an `if`; nothing made it an `if`
        # except where the author happened to write it. A detector that only inspects the syntax
        # its worked example used is measuring the example, not the fault.
        for n2 in ast.walk(t):
            tests = []
            if isinstance(n2, (ast.If, ast.While, ast.IfExp)):
                tests.append(("guard", n2.test))
            elif isinstance(n2, ast.Assert):
                tests.append(("assertion", n2.test))
            elif isinstance(n2, (ast.ListComp, ast.SetComp, ast.DictComp, ast.GeneratorExp)):
                for gen in n2.generators:
                    for cond in gen.ifs:
                        tests.append(("comprehension filter", cond))
            for kind, test in tests:
                for sub in ast.walk(test):
                    if isinstance(sub, ast.Name) and isinstance(sub.ctx, ast.Load) \
                            and sub.id not in defined:
                        phantom.append("%s:%d %s names '%s', never defined in this module"
                                       % (name, n2.lineno, kind, sub.id))
    return {"dead": sorted(set(dead)), "tautology": sorted(set(taut)),
            "phantom": sorted(set(phantom)), "unparsed": sorted(set(unparsed))}


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--quiet", action="store_true", help="counts only")
    a = ap.parse_args()
    r = scan()
    total = sum(len(v) for v in r.values())
    if not a.quiet:
        for kind, label in (("tautology", "CANNOT FAIL — both sides of the comparison are equal"),
                            ("phantom", "GUARDS AN UNDEFINED NAME — raises only on the branch "
                                        "nobody takes"),
                            ("dead", "NEVER RUNS — no caller anywhere in src/"),
                            ("unparsed", "WILL NOT PARSE — excluded from every check above")):
            rows = r[kind]
            print("\n%s  (%d)" % (label, len(rows)))
            print("-" * 78)
            for x in rows:
                print("   " + x)
    print("\nliveness: %d finding(s) — %d tautology, %d phantom, %d dead, %d unparsed"
          % (total, len(r["tautology"]), len(r["phantom"]), len(r["dead"]), len(r["unparsed"])))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
