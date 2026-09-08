"""LIVENESS — find the checks that cannot fail and the code that never runs.

THE STANDING LESSON THIS AUTOMATES. "A check that cannot fail looks exactly like a check that
passed" is the most-repeated finding in this project's ledger, and every instance has been found
by a person reading the file. Instances already caught by hand:

  * `profile.py`'s round trip -- FIXED, now at `profile.py:196-208`: it used to compare a decoded
    field against the input it was handed, so `d["profile"] != r["profile"]` was tautologically
    False, green for ever. It now re-encodes what `decode()` extracted and compares THAT.
  * `cleanup.py`'s `_ruby_question_mark` -- FIXED: the guard whose condition named a regex that
    was never defined is gone; the function is now a plain scan with no such guard.
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
  DEAD CLASS  a class whose name is never instantiated, inherited from, imported or named as a
              string, anywhere in src/. It was invisible to the DEAD pass above, which recurses
              INTO a ClassDef and never judges the ClassDef -- while the class's methods keep
              each other alive by calling one another on `self`. (order 209391b4f990; the module
              limb of that order, a module nothing imports, is NOT here yet -- see `scan()`.)
  TAUTOLOGY   a comparison whose two sides are the same expression. Always True or always False,
              regardless of the data it claims to be checking.
  PHANTOM     a name used in a condition that is never defined, imported or assigned in its
              module -- the `cleanup.py` shape, which raises only on the branch nobody takes.

WHAT IT DELIBERATELY DOES NOT DO. It does not judge whether a live check is a GOOD check; that is
what the drill and the adversarial audits are for. It answers the narrower, mechanical question
this project keeps losing money on: is this code capable of running, and is this comparison
capable of being false?

AND ITS HONEST LIMIT, STATED BECAUSE THE ALTERNATIVE IS FALSE ASSURANCE. The TAUTOLOGY pass is
SYNTACTIC: it finds comparisons whose two sides are the same expression. It would NOT have found
the `profile.py` instance that motivated it (now fixed, see above), because that one was
SEMANTIC -- `d = decode(r["profile"])` and then `d["profile"] != r["profile"]`, which was always
False only if you knew what `decode` returned. Two different expressions, one guaranteed answer.
Catching that class needs dataflow this module does not do -- a live instance of that shape,
were one to appear elsewhere, would still land on the human list, not here.
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

# Modules that are legitimately never imported or named from inside src/, with the reason.
# SEPARATE FROM `EXEMPT` ON PURPOSE (order e3451d1e056d, 2026-09-01). `EXEMPT` above is a table
# of FUNCTION and METHOD names -- main, __init__, do_GET, and so on -- and the module-dead pass
# used to test a MODULE STEM against it (`_stem(n) not in EXEMPT`). No file in src/ is named
# after any of those keys, so that conjunct was always True and the clause never filtered a row;
# had it ever matched by coincidence, the attached reason ("CLI entry point, called by
# __main__") would have been the wrong one for a whole module being unreached. A module reached
# only from OUTSIDE src/ -- a scheduled task line, a `python src/x.py` in a shell script, a job
# roster entry the string pass above cannot see -- is a real, legitimate case; it now has
# somewhere honest to be recorded, with its own reason, instead of nowhere. Empty today: nothing
# currently claims this exemption. Add an entry here, never to `EXEMPT`, if one is found to need
# it -- the function pass and the module pass need different reasons, and one table serving both
# is how the reason stops matching the finding.
EXEMPT_MODULES = {}

# Classes that are legitimately never named from inside src/, with the reason.
# SEPARATE FROM `EXEMPT` FOR THE SAME REASON `EXEMPT_MODULES` IS (order 962bc293ec32). The
# dead-CLASS pass -- the third of the three -- was still filtering class names through `EXEMPT`
# and `EXEMPT_PREFIXES`, which are tables of FUNCTION and METHOD names with a FUNCTION's reason
# attached: main, __init__, do_GET, t_, cmd_, phase_. Measured over all 116 modules under src/
# (deprecated/ included) there are 32 ClassDefs and not one matches any key or any prefix, so
# that conjunct had never filtered a row in its life -- and had it ever matched by coincidence,
# the reason recorded beside the exemption would have been "CLI entry point, called by
# __main__" for a class nobody instantiates. This is the module whose whole subject is clauses
# that cannot fire, and it had one.
#
# Empty is the correct starting content: nothing claims this exemption. Add an entry HERE,
# never to `EXEMPT` -- the three passes need three different reasons, and one table serving all
# of them is how the reason stops matching the finding.
EXEMPT_CLASSES = {}


def _modules():
    """Every `.py` under `src/`, SUBDIRECTORIES INCLUDED. -> (label, full path) pairs.

    THE DETECTOR THAT CANNOT FAIL WAS BLIND TO A WHOLE DIRECTORY (order aeeba9364147). This
    listed candidates with `os.listdir(SRC)`, which does not descend, and `src/deprecated/`
    exists and holds `catalogue_local.py` (280 lines, kept on purpose as a record of a failure
    mode). That file therefore never entered `trees`: never a DEAD or DEAD_CLASS or TAUTOLOGY
    or PHANTOM candidate, never contributing to `referenced` for the dead-module pass, never
    reportable as a dead module itself. A subdirectory nothing can see reads exactly like a
    clean one -- zero findings either way -- and this file is the project's designated check
    that cannot fail. Third occurrence of the same defect class: `sweep_plan._src_py_files`
    (order f42c55355431) and `drill._src_py_files` (order cf9ee9000be8) were both walked for
    this same reason and the fix was never propagated here.

    `__pycache__` holds no source and is skipped. The `_` prefix filter is kept and now applies
    to directories too, for the same reason it applies to files. The label carries the relative
    path with forward slashes, so a finding names the file a person has to open; `_stem` below
    takes the basename before matching, because a reference spells the module (`catalogue_local`)
    and never the path.
    """
    out = []
    for root, dirs, files in os.walk(SRC):
        dirs[:] = [d for d in sorted(dirs) if not d.startswith("_")]
        for f in sorted(files):
            if f.endswith(".py") and not f.startswith("_"):
                full = os.path.join(root, f)
                out.append((os.path.relpath(full, SRC).replace(os.sep, "/"), full))
    return sorted(out)


def _parse(path):
    """-> (tree, None) on success, or (None, reason) on failure.

    THE REASON RIDES ALONG, not just the fact of failure. The three causes this pass exists to
    catch -- a real SyntaxError, control-character corruption, and a mid-write truncation from a
    killed gated write -- each produce a different exception (SyntaxError, UnicodeDecodeError,
    and usually SyntaxError with an "unexpected EOF" message respectively), and a bare `None`
    collapsed all three into the same "will not parse" row with nothing left to tell them apart
    by. See the docstring above and `scan()`'s use of this.
    """
    try:
        with open(path, encoding="utf-8") as fh:
            return ast.parse(fh.read(), filename=path), None
    except Exception as e:
        return None, "%s: %s" % (type(e).__name__, e)


def _self_attrs(node):
    """The names this class body reads off `self` or `cls`, EXCLUDING nested class bodies.

    `self.foo()` is the ordinary way a method is reached, and it is the reason the DEAD pass can
    judge methods at all. But it is a scoped reference: it can only reach a method of THIS class
    or of something in its MRO, never a same-named method on an unrelated class in an unrelated
    module. Collecting these globally, alongside `obj.foo`, is the attribute-shaped version of
    the flat `used` bag that hid `coverage._p()` -- see `scan()`.

    A nested class gets its own entry rather than donating to its parent, for the same reason.
    """
    out = set()
    stack = list(node.body)
    while stack:
        n = stack.pop()
        if isinstance(n, ast.ClassDef):
            continue                    # its own entry; it does not donate to its parent
        if isinstance(n, ast.Attribute) and isinstance(n.value, ast.Name) \
                and n.value.id in ("self", "cls"):
            out.add(n.attr)
        stack.extend(ast.iter_child_nodes(n))
    return out


def _classes(tree, prefix=""):
    """-> {dotted class name: (base names, self/cls attribute names)} for one module."""
    found = {}
    for node in tree.body:
        if isinstance(node, ast.ClassDef):
            label = prefix + node.name
            bases = []
            for b in node.bases:
                if isinstance(b, ast.Name):
                    bases.append(b.id)
                elif isinstance(b, ast.Attribute):
                    bases.append(b.attr)
            found[label] = (bases, _self_attrs(node))
            found.update(_classes(node, label + "."))
    return found


def _classdefs(tree, prefix=""):
    """Every class the DEAD-CLASS pass considers, as (simple name, dotted label, node).

    `_defs` recurses INTO a ClassDef but never yields the ClassDef itself, so a class was not a
    DEAD candidate at all -- and its methods were meanwhile credited to each other through
    `scoped`, because they call one another on `self`. A class nothing ever instantiates is
    therefore structurally invisible to a detector whose whole subject is code that cannot run:
    measured over this tree, `escalation.py`'s `class Refused` -- "An OPERATOR- or SUPERVISOR-level
    stop: this unit or this source, not the library" -- is never raised, caught, imported or
    named anywhere in src/, while its sibling `SystemHalted` is raised and caught in two modules.
    Two rungs of Hard Rule -1's chain had a declared exception type with no raiser: a safety in a
    file rather than in effect. (order 209391b4f990)

    Nested classes recurse and the label carries the dotted path, exactly as `_defs` does, so a
    row names the enclosing class rather than a bare name nobody can find.
    """
    for node in tree.body:
        if isinstance(node, ast.ClassDef):
            yield node.name, prefix + node.name, node
            for got in _classdefs(node, prefix + node.name + "."):
                yield got


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
    class -- e.g. `foo.py:12 Bar.baz()` is answerable, `baz()` is not. (`entity_match.py`'s one
    class, `MatchReason`, is a bare constant namespace with no methods, so it cannot supply a
    real example here; this is illustrative, not a citation.)
    """
    for node in tree.body:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            yield node.name, prefix + node.name, node
        elif isinstance(node, ast.ClassDef):
            for got in _defs(node, prefix + node.name + "."):
                yield got


def scan():
    """-> {'dead', 'dead_class', 'dead_module', 'tautology', 'phantom', 'unparsed'} over src/.

    THE MODULE PASS IS NOW HERE (order 209391b4f990, landed 2026-08-29 with the ceiling raise it
    needed). It was specified in this docstring and left unbuilt for one shift, because a
    function is credited as used by `used_local[name]` -- a bare-name Load anywhere in its OWN
    module -- so every function in a module nothing imports is kept alive by its siblings, and
    that module reports ZERO findings, identical to what a clean, live module reports. No amount
    of sharpening the per-symbol passes can reach that: inside an orphan file every name really
    is reached. Measured by AST over src/ (imports, from-imports, and every string constant equal
    to a module name or `<name>.py`, so a job roster or dispatch-table entry counts): TEN modules
    are never imported or named by any other module -- chord_field, descending_ladder, halo,
    handbuilt, module_index, pantheon, render, scale_theories, wh40k, zfighters -- and six of
    them produced no row here at all before this limb existed. Two were already known and filed
    by hand (render 707fefc17465, scale_theories SWEEP34_FINDING), which is what having no
    instrument for a class of finding looks like.

    It had to land in the same change as `drill.LIVENESS_CEILING`, because adding it raises the
    finding count by ten and the ratchet net would otherwise breach -- halting the library over a
    detector that got sharper rather than code that got worse. The class limb above fitted inside
    the existing headroom; this one did not. The ceiling moved 41 -> 52 with its reasoning
    written out beside it.

    ALSO MEASURED AND EMPTY, recorded so it is not re-measured: a function whose only in-module
    reference is its own recursive call would likewise be credited as used. Zero instances in the
    tree today.
    """
    trees, used, unparsed = {}, set(), []
    for name, path in _modules():
        t, reason = _parse(path)
        if t is None:
            # A MODULE THAT WILL NOT PARSE IS NOT A CLEAN MODULE. Until run #33 this `continue`
            # was silent, so a source file that failed to parse -- including from the literal
            # control-character corruption this project has hit more than once, and from
            # `local_agent`'s gated writes being killed mid-write -- vanished from every check
            # below and reported exactly like a module with nothing wrong in it. The scanner
            # whose whole purpose is finding checks that cannot fail had one at its own
            # foundation. Reported as a finding of its own, so the count rises and the ratchet
            # in `drill.py` sees it. Found by the run #33 sweep (batch 08).
            #
            # THE REASON IS CARRIED, not just the fact -- `_parse` now returns why (SyntaxError,
            # UnicodeDecodeError, ...) so the row can distinguish the three causes named above
            # instead of collapsing them all into the same "will not parse".
            unparsed.append("%s: will not parse (%s) -- excluded from every liveness check"
                            % (name, reason))
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
    #
    # AND `self.foo` IS SCOPED TOO, which is the same correction one level in. When DEAD was
    # widened to methods it leaned on "any method reached through an instance anywhere in src/
    # counts as used" -- and implemented that by putting EVERY attribute name, `self.x` included,
    # into the one global `used` bag. `self.foo()` cannot reach an unrelated class's `foo` any
    # more than a bare `_p` can reach another module's `_p()`; it is the identical fault in
    # attribute clothing, and it means a dead method can never be flagged so long as ANY class
    # anywhere in the tree happens to use that name. Zero collisions today among the non-dunder
    # methods in scope -- which is exactly why it is cheap to fix now rather than after one
    # appears. `self`/`cls` reads are collected PER CLASS by `_self_attrs` and credited to that
    # class, its ancestors and its descendants (a base's template method calls `self.step()` and
    # a subclass implements it; both directions are real). Every other attribute stays global.
    used_local, self_attr = {}, {}
    for name, t in trees.items():
        local = set()
        for node in ast.walk(t):
            if isinstance(node, ast.Name):
                # LOAD only. A `for _p in ...` or `_p = 1` BINDS the name, it does not call
                # anything, and counting bindings as calls is precisely what went wrong.
                if isinstance(node.ctx, ast.Load):
                    local.add(node.id)
            elif isinstance(node, ast.Attribute):
                if isinstance(node.value, ast.Name) and node.value.id in ("self", "cls"):
                    continue                              # scoped to its class, below
                used.add(node.attr)                       # `mod.thing()` -- crosses modules
            elif isinstance(node, ast.ImportFrom):
                for al in node.names:
                    used.add(al.name)                     # `from mod import thing`
                    if al.asname:
                        used.add(al.asname)
            elif isinstance(node, ast.Constant) and isinstance(node.value, str):
                used.add(node.value.strip())              # getattr / dispatch table
        used_local[name] = local
        for label, pair in _classes(t).items():
            self_attr[(name, label)] = pair

    # The MRO, approximated BY NAME because that is all a syntax pass has. Erring toward "it is
    # used" remains the rule: a base named in another module still joins by its simple name, and
    # so does anything that inherits from this class. What no longer joins is an unrelated class
    # that merely shares a method name, which was the whole of the old behaviour.
    by_simple = {}
    for key in self_attr:
        by_simple.setdefault(key[1].rsplit(".", 1)[-1], []).append(key)
    scoped = {}
    for key in self_attr:
        seen, stack = set(), [key]
        while stack:
            k = stack.pop()
            if k in seen:
                continue
            seen.add(k)
            for b in self_attr[k][0]:                     # upward: this class's bases
                stack.extend(by_simple.get(b.rsplit(".", 1)[-1], []))
            simple = k[1].rsplit(".", 1)[-1]              # downward: anything inheriting it
            for k2, (bases2, _a) in self_attr.items():
                if k2 not in seen and any(x.rsplit(".", 1)[-1] == simple for x in bases2):
                    stack.append(k2)
        # `seen` always holds at least `key` itself (added the moment the loop above pops it),
        # so the `if seen else set()` here could never take its `else` arm -- order 114a34e9a97a,
        # 2026-09-01. A conditional that cannot take one branch, left in the file whose whole
        # subject is checks that cannot fail.
        scoped[key] = set().union(*[self_attr[k][1] for k in seen])

    # --- DEAD MODULE: a whole file nothing else reaches. THE LIMB THE PER-SYMBOL PASSES CANNOT
    # HAVE, and the reason it had to be its own pass (order 209391b4f990). A function is credited
    # as used by `used_local[name]`, a bare-name Load anywhere in its OWN module, so every
    # function in a module nothing imports is kept alive by its siblings -- and that module then
    # reports ZERO findings, which is byte-for-byte what a clean, live module reports. The
    # per-symbol passes cannot see this by construction, however sharp they get: they ask
    # "is this name reached", and inside an orphan file every name reaches every other.
    #
    # THE THREE ROUTES A MODULE IS LEGITIMATELY REACHED BY, and all three are counted, because
    # erring toward "it is used" is this module's standing rule: `import x` / `import x as y`,
    # `from x import ...` (and `from pkg import x`, where the imported name may itself be the
    # module), and a STRING naming it -- `"halo"` or `"halo.py"` or a path ending in it. The
    # string route is not generosity: `overnight.STANDING` builds every daemon's command line
    # with `os.path.join(SRC, "pipeline.py")`, and a job roster is as real a reference as an
    # import statement.
    #
    # SELF-REFERENCE DOES NOT COUNT. A module that imports itself, or names its own filename in
    # its own `__main__` help text, has not been reached by anything -- crediting that would make
    # this limb unable to fire on precisely the files it exists for.
    # `trees` is keyed by FILENAME (`silence.py`) while every reference spells the module
    # (`import silence`). Compared without stemming, the two never match and this limb reports
    # the entire tree dead -- which is how it read on first measurement, and a limb that fires on
    # everything is as useless as one that fires on nothing.
    def _stem(s):
        # BASENAME FIRST, because `_modules()` now walks subdirectories and labels them by
        # relative path (`deprecated/catalogue_local.py`) while every reference to a module
        # spells the bare name (`import catalogue_local`, or the string `src/catalogue_local.py`).
        # Compared unstemmed the two can never match, which would report every module in a
        # subdirectory as dead on the strength of its directory alone.
        s = s.replace("\\", "/").rsplit("/", 1)[-1]
        return s[:-3] if s.endswith(".py") else s

    referenced = set()
    for name, t in trees.items():
        me = _stem(name)
        for node in ast.walk(t):
            got = ()
            if isinstance(node, ast.Import):
                got = [al.name.split(".")[0] for al in node.names]
            elif isinstance(node, ast.ImportFrom):
                got = [al.name for al in node.names]
                if node.module:
                    got.append(node.module.split(".")[0])
            elif isinstance(node, ast.Constant) and isinstance(node.value, str):
                got = [_stem(node.value.strip().replace("\\", "/").rsplit("/", 1)[-1])]
            for g in got:
                if g and g != me:
                    referenced.add(g)
    dead_module = ["%s: nothing in src/ imports or names this module, so every function in it "
                   "is kept alive only by its siblings and the per-symbol passes above report "
                   "it as clean" % n
                   for n in sorted(trees)
                   if _stem(n) not in referenced and _stem(n) not in EXEMPT_MODULES]

    dead, dead_class, taut, phantom = [], [], [], []
    for name, t in trees.items():
        # --- DEAD CLASS: a ClassDef whose simple name is never referenced anywhere (see
        # `_classdefs`). Resolved with the SAME three-way rule the function pass uses, because a
        # class is reached by exactly the same routes a function is: `Refused(...)` and
        # `except Refused:` and `class X(Refused)` are bare Name Loads in the defining module,
        # `mod.Refused` is an attribute, `from mod import Refused` is a from-import, and a
        # dispatch table names it as a string. All four are already collected above. There is no
        # `self`/`cls` limb here: a class is not reached through an instance of itself.
        for cls, label, node in _classdefs(t):
            # AGAINST THE CLASS TABLE, NOT THE FUNCTION ONE (order 962bc293ec32). See
            # EXEMPT_CLASSES. The finding count is unchanged by this -- the old conjunct
            # matched nothing -- so it does not move drill.LIVENESS_CEILING.
            if cls in EXEMPT_CLASSES:
                continue
            if cls not in used and cls not in used_local.get(name, ()):
                dead_class.append("%s:%d class %s" % (name, node.lineno, label))

        # --- DEAD: module-level defs and METHODS nobody references (see `_defs`)
        for fn, label, node in _defs(t):
            if fn in EXEMPT or fn.startswith(EXEMPT_PREFIXES) or fn.startswith("__"):
                continue
            # Membership in the pre-built sets. The first version re-walked every tree for every
            # function -- 95 modules x ~40,000 lines, per def -- and did not finish inside two
            # minutes. A check nobody can afford to run is a check that does not run, which is
            # the very thing this module exists to find.
            #
            # THREE SETS, not one: `used` is the cross-module surface (non-self attributes,
            # from-imports, dispatch strings), `used_local[name]` is what this module itself
            # loads by bare name, and `reachable` is what THIS CLASS AND ITS RELATIVES read off
            # `self`/`cls`. A bare name in ANOTHER module cannot reach this function, and a
            # `self.foo` in an UNRELATED class cannot reach this method.
            reachable = ()
            if "." in label:
                reachable = scoped.get((name, label.rsplit(".", 1)[0]), ())
            if fn not in used and fn not in used_local.get(name, ()) and fn not in reachable:
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
            elif isinstance(n2, ast.MatchAs) and n2.name:
                defined.add(n2.name)                      # `case X() as thing:` / `case other:`
            elif isinstance(n2, ast.MatchStar) and n2.name:
                defined.add(n2.name)                      # `case [a, *rest]:`
            elif isinstance(n2, ast.MatchMapping) and n2.rest:
                defined.add(n2.rest)                      # `case {"k": v, **rest}:`
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
        #
        # THE TWO THE WIDENING STILL MISSED, closed here for the same reason and while the count
        # is still zero. A `match`/`case` GUARD is a condition in every sense -- it is evaluated
        # only when its pattern matches, so a name it gets wrong raises on exactly the branch
        # nobody takes. And a bare `cond and action()` STATEMENT is an `if` written as an
        # expression: the right-hand side runs only when the left is true, and Python does not
        # care that the author chose an operator over a keyword. Both measure zero in this tree
        # today (no `match` statements at all, no bare boolean statements), which is precisely
        # when a detector is cheap to widen -- widening it after the first instance appears means
        # the instance was missed. Case-pattern CAPTURES are added to `defined` above, or every
        # guard naming its own capture would be a false positive.
        for n2 in ast.walk(t):
            tests = []
            if isinstance(n2, (ast.If, ast.While, ast.IfExp)):
                tests.append(("guard", n2.test))
            elif isinstance(n2, ast.Assert):
                tests.append(("assertion", n2.test))
            elif isinstance(n2, ast.match_case) and n2.guard is not None:
                tests.append(("match guard", n2.guard))
            elif isinstance(n2, ast.Expr) and isinstance(n2.value, ast.BoolOp):
                # `and` and `or` alike: both short-circuit, so in both the trailing operand is
                # code that runs only on a branch. Reported as one test over the whole
                # expression -- an undefined name anywhere in it raises only when reached.
                tests.append(("short-circuit statement", n2.value))
            elif isinstance(n2, (ast.ListComp, ast.SetComp, ast.DictComp, ast.GeneratorExp)):
                for gen in n2.generators:
                    for cond in gen.ifs:
                        tests.append(("comprehension filter", cond))
            for kind, test in tests:
                # `ast.match_case` is not a statement and carries NO `lineno` of its own, so the
                # line is taken from the test instead -- a report row that cannot say where the
                # finding is would be a finding nobody acts on.
                line = getattr(n2, "lineno", None) or getattr(test, "lineno", 0)
                for sub in ast.walk(test):
                    if isinstance(sub, ast.Name) and isinstance(sub.ctx, ast.Load) \
                            and sub.id not in defined:
                        phantom.append("%s:%d %s names '%s', never defined in this module"
                                       % (name, line, kind, sub.id))
    return {"dead": sorted(set(dead)), "dead_class": sorted(set(dead_class)),
            "dead_module": sorted(set(dead_module)),
            "tautology": sorted(set(taut)), "phantom": sorted(set(phantom)),
            "unparsed": sorted(set(unparsed))}


# ================================================================================================
# GATE REACHABILITY (order 8950aa8d3f62) -- THE DETECTOR THAT DID NOT EXIST.
#
# `scan()` above finds the mechanical SOURCE shapes of "a check that cannot fail looks exactly
# like a check that passed" -- dead code, tautologies, phantom guards. It has nothing to say
# about a different shape of the same failure: code that is neither dead nor tautological, that a
# person genuinely reaches, but that NO CHECK IN THE BATTERY can ever execute -- so a mutation
# dropped anywhere inside it is unkillable by construction, and nothing says so.
#
# Demonstrated on `escalation.clear()` while working order a67d4b81f963: `clear()` validates its
# ruling (reachable, tested) and then calls `_by_a_person_at_the_cli()`, which returns False for
# ANY programmatic caller -- correctly, that is the whole point of CLAUDE.md Hard Rule -1's "you
# may RAISE a halt, you may not LIFT one" -- so `clear()`'s own halt-lifting tail, and
# `_land_clear()` entirely, run only when a person types `python src/escalation.py --clear` by
# hand. No battery row can ever exercise those lines.
#
# THE SMALLEST HONEST VERSION, per the order's own fallback instruction ("if a full detector is
# too large, land the smallest honest version and say what it does not yet cover"):
#
#   * ONE RUNNER -- `verify_math.py`, the one check this project's own house rules let an
#     agent outside the drill's own shift actually run. `drill.py`'s 57 nets are NOT included:
#     running them is restricted to the agent that owns the drill, and this must not become a
#     second, informal way to invoke it. A line reached only through drill.py will show here as
#     unreached even though the battery AS A WHOLE does reach it -- a real gap in THIS PASS, not
#     a claim that the line is actually dead, and `main()`'s report names the gap every time.
#   * ONE MODULE FAMILY TO START -- `GATE_MODULES` below, seeded with the module the order was
#     demonstrated on. Widening it to the rest of the safety-critical tree is exactly the kind
#     of extension this detector is built to take without a rewrite; it is not done here because
#     doing it without measuring each result first would be inventing findings, not reporting
#     them.
#
# REPORTED AS A ROSTER, NEVER A PERCENTAGE (Hard Rule 0). A coverage number is exactly the shape
# of a truncation -- "94% reached" silently discards the 6%, the same way `roster(limit=N)`
# discarded everything past the cutoff. The finding is the LIST of unreached line numbers, in
# full, every time.
#
# A LEGITIMATE RESIDUE IS EXPECTED, AND MUST BE DECLARED, NOT SILENCED. `escalation.clear()`'s
# CLI-only tail is correctly unreachable by any automated check; a detector that reported it as a
# fresh finding every run would train whoever reads this to stop reading it, which is its own
# route back to "a check nobody watches fail". So the precedent `state/MUTANTS_SURVIVED.jsonl`
# already sets for a ruled-equivalent mutant is followed here: `DECLARED_UNREACHABLE` names the
# specific functions ruled unreachable and WHY, and the report separates "declared" from
# "undeclared" -- undeclared is the only list that should ever surprise a reader.
#
# DECLARED BY FUNCTION NAME, NOT BY LINE NUMBER -- this project's own recurring lesson (orders
# 5ed00985ce04, ed58a1a87da0, and `summary()`'s own docstring above: "a citation with a short
# shelf life"). A line-number entry here would rot the moment somebody edited an earlier function
# in the same file; a name is resolved fresh, by AST, every time this runs.
GATE_MODULES = ("escalation.py",)

DECLARED_UNREACHABLE = {
    "escalation.py": {
        "_land_clear": "called only from clear()'s tail, itself gated on "
                        "_by_a_person_at_the_cli() returning True -- reachable solely by a "
                        "person typing `python src/escalation.py --clear`, by design "
                        "(CLAUDE.md Hard Rule -1, 'you may RAISE a halt, you may not LIFT one')",
    },
}


def _function_line_ranges(path):
    """Every `def` in `path`, module-level or method. -> {name: (first_line, last_line)}.

    Separate bookkeeping from `_defs` above on purpose: that pass answers "who calls this",
    this answers "which lines belong to this", and `end_lineno` (stdlib `ast`, present since the
    3.8 floor this project already assumes) gives the span directly with nothing re-derived from
    a sibling's start line.
    """
    tree, _reason = _parse(path)
    if tree is None:
        return {}
    out = {}
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            out[node.name] = (node.lineno, getattr(node, "end_lineno", None) or node.lineno)
    return out


def reachability(modules=GATE_MODULES, runner="verify_math.py", timeout_s=1800):
    """Which executable lines of `modules` no check in `runner` ever ran. -> a report dict.

    -> {"measured_against": runner,
        "modules": {mod: {"executable_lines": int, "unreached": [line, ...],
                           "unreached_undeclared": [line, ...],
                           "declared_unreachable_functions": [name, ...]}
                     or {"error": str}}}
       or {"error": str} if nothing could be measured at all.

    RUNS `runner` FOR REAL, UNDER COVERAGE, AS A SUBPROCESS -- this does not statically guess
    reachability the way `scan()`'s DEAD pass does (a name never appearing anywhere is a good
    proxy for "no caller"; a name appearing in a check that itself never reaches the branch in
    question is not, and only actually running the check answers that). A subprocess, not an
    EVERY STEP RUNS AS A SUBPROCESS, INCLUDING THE ANALYSIS -- not just the measurement. The
    obvious design imports the `coverage` package in-process (`import coverage;
    coverage.Coverage(data_file=...).analysis2(path)`) and that was the first version of this
    function; it failed with `AttributeError: module 'coverage' has no attribute 'Coverage'`
    the first time it was actually run, because THIS PROJECT ALREADY HAS ITS OWN
    `src/coverage.py`. `liveness.py` runs as `python src/liveness.py`, which puts `src/` at the
    front of `sys.path`, so `import coverage` silently resolves to the wrong module -- not an
    ImportError, a WRONG ANSWER, which is worse: the very `try/except ImportError` meant to fail
    this closed if the real package were missing would not even have caught it, since the import
    would have "succeeded" against the shadow. Two more subprocesses -- `coverage --version` to
    prove the REAL package answers before trusting anything, and `coverage json` to do the
    analysis -- avoid the collision entirely, because a subprocess launched with the repo ROOT
    as its cwd (which has no `coverage.py` of its own; only `src/` does) resolves `import
    coverage` correctly. Also sidesteps the second reason importing `runner` in-process would be
    wrong: it is a top-level script that calls `sys.exit()` on completion (see its own tail),
    which would exit THIS process too.

    FAILS CLOSED, NEVER SILENTLY INTO A CLEAN-LOOKING RESULT (the standing lesson this whole
    detector exists to serve, turned on itself). If the real `coverage` package cannot be
    reached, the runner is missing, a subprocess times out, or the run exits without ever
    writing a data file, this returns `{"error": ...}` -- never an empty `unreached` list, which
    would read as "everything is reached" when the true answer is "nothing was measured". A
    `runner` exit code that is merely nonzero is NOT treated as a measurement failure:
    `verify_math.py` exits nonzero on a FAILED check, which is a finding about the library, not
    about whether coverage collection worked, and the data file existing is the actual signal
    that it ran to completion.
    """
    import json as _json
    import shutil
    import subprocess
    import sys as _sys
    import tempfile

    # EVERY CHILD SPAWNED HERE IS WINDOWLESS. `verify_math`'s "every subprocess spawn in src/
    # suppresses its console window" row is absolute, and it caught all three of these the day
    # they were written (2026-09-08): a missed kwarg is a black console window flashing on the
    # owner's desktop, and this detector may run under a scheduled pass with nobody at the
    # machine. Same spelling as `secondopinion._NO_WIN`, and `getattr` because the flag exists
    # only on Windows.
    _NO_WIN = getattr(subprocess, "CREATE_NO_WINDOW", 0)

    # PROVE THE REAL PACKAGE ANSWERS BEFORE TRUSTING ANYTHING FROM IT (see the shadowing note
    # above). Run with cwd=HERE (the repo ROOT, which has no coverage.py of its own) rather than
    # SRC, so this subprocess's `import coverage` cannot hit the same shadow the in-process
    # version did.
    try:
        probe = subprocess.run([_sys.executable, "-m", "coverage", "--version"],
                               cwd=HERE, capture_output=True, text=True, timeout=30,
                               creationflags=_NO_WIN)
    except Exception as e:
        probe = None
        probe_error = "%s: %s" % (type(e).__name__, e)
    if probe is None or probe.returncode != 0:
        detail = probe_error if probe is None else (probe.stderr or probe.stdout or "").strip()
        return {"error": "the `coverage` package could not be reached as `python -m coverage` "
                          "-- gate reachability was NOT measured. A missing instrument, not a "
                          "clean result: this must not be read as \"nothing unreached\". (%s)"
                          % detail[:200]}

    target = os.path.join(SRC, runner)
    if not os.path.exists(target):
        return {"error": "runner %r not found under src/ -- nothing was measured" % runner}
    include = ",".join(os.path.join(SRC, m) for m in modules)
    tmpdir = tempfile.mkdtemp(prefix="liveness_reachability_")
    datafile = os.path.join(tmpdir, "gate.coverage")
    jsonfile = os.path.join(tmpdir, "gate.json")
    try:
        cmd = [_sys.executable, "-m", "coverage", "run", "--data-file", datafile,
               "--include", include, target]
        try:
            proc = subprocess.run(cmd, cwd=HERE, capture_output=True, text=True,
                                  timeout=timeout_s, creationflags=_NO_WIN)
        except subprocess.TimeoutExpired:
            return {"error": "coverage run of %s did not finish inside %ds -- gate "
                              "reachability NOT measured this pass" % (runner, timeout_s)}
        except Exception as e:
            return {"error": "could not run %s under coverage: %s: %s"
                              % (runner, type(e).__name__, e)}
        if not os.path.exists(datafile):
            return {"error": "coverage produced no data file -- %s did not run to completion "
                              "(exit %r, stderr tail: %r); gate reachability NOT measured this "
                              "pass" % (runner, proc.returncode, (proc.stderr or "")[-300:])}
        jcmd = [_sys.executable, "-m", "coverage", "json", "--data-file", datafile,
               "--include", include, "-o", jsonfile, "-q"]
        jproc = subprocess.run(jcmd, cwd=HERE, capture_output=True, text=True, timeout=120,
                               creationflags=_NO_WIN)
        if not os.path.exists(jsonfile):
            return {"error": "coverage could not produce a JSON report (exit %r): %s"
                              % (jproc.returncode, (jproc.stderr or "")[-300:])}
        with open(jsonfile, encoding="utf-8") as f:
            report = _json.load(f)
        files = report.get("files") or {}
        # MATCHED BY ABSOLUTE PATH, NOT BY THE RAW KEY STRING -- `coverage json`'s file keys are
        # relative to the cwd it was RUN with (here, HERE), and this function's own callers may
        # reasonably pass a differently-cased or differently-rooted path. Resolving both sides to
        # an absolute, case-normalised path is the same discipline `_in_src` in local_agent.py
        # uses for the identical reason: ask where the file IS, not what it is called.
        by_abspath = {os.path.normcase(os.path.abspath(os.path.join(HERE, k))): v
                     for k, v in files.items()}
        out = {"measured_against": runner, "modules": {}}
        for m in modules:
            path = os.path.join(SRC, m)
            info = by_abspath.get(os.path.normcase(os.path.abspath(path)))
            if info is None:
                out["modules"][m] = {"error": "not present in the coverage report -- the "
                                               "runner may never have imported this module at "
                                               "all this pass"}
                continue
            missing_sorted = sorted(info.get("missing_lines") or [])
            executed = info.get("executed_lines") or []
            ranges = _function_line_ranges(path)
            declared_fns = DECLARED_UNREACHABLE.get(m, {})
            declared_lines = set()
            for fn_name in declared_fns:
                span = ranges.get(fn_name)
                if span:
                    declared_lines.update(range(span[0], span[1] + 1))
            undeclared = [ln for ln in missing_sorted if ln not in declared_lines]
            out["modules"][m] = {
                "executable_lines": len(executed) + len(missing_sorted),
                "unreached": missing_sorted,
                "unreached_undeclared": undeclared,
                "declared_unreachable_functions": sorted(declared_fns),
            }
        return out
    finally:
        shutil.rmtree(tmpdir, ignore_errors=True)


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--quiet", action="store_true", help="counts only")
    ap.add_argument("--reachability", action="store_true",
                     help="measure which lines of GATE_MODULES no check in verify_math.py ever "
                          "reaches (order 8950aa8d3f62). SLOW -- runs verify_math.py under "
                          "coverage as a subprocess. Opt-in and separate from the scan above: "
                          "that pass is static and fast, this one actually executes the battery "
                          "and its report says by name what it does not yet cover (drill.py's "
                          "nets, and any module not yet in GATE_MODULES).")
    a = ap.parse_args()
    if a.reachability:
        print("gate reachability  (order 8950aa8d3f62 -- measured against verify_math.py only; "
              "drill.py's nets are NOT included here, see reachability()'s docstring)")
        print("-" * 78)
        rep = reachability()
        if "error" in rep:
            print("   NOT MEASURED: %s" % rep["error"])
        else:
            for m, info in rep["modules"].items():
                if "error" in info:
                    print("   %s: NOT MEASURED (%s)" % (m, info["error"]))
                    continue
                print("   %s -- %d executable line(s), %d unreached, %d of those UNDECLARED"
                      % (m, info["executable_lines"], len(info["unreached"]),
                         len(info["unreached_undeclared"])))
                if info["declared_unreachable_functions"]:
                    print("      declared unreachable (ruled, not a gap): %s"
                          % ", ".join(info["declared_unreachable_functions"]))
                if info["unreached_undeclared"]:
                    print("      UNDECLARED -- no check reaches these lines and nobody has "
                          "ruled on why (the roster, in full, never a count alone):")
                    for ln in info["unreached_undeclared"]:
                        print("        line %d" % ln)
                else:
                    print("      no undeclared residue")
        return 0
    r = scan()
    total = sum(len(v) for v in r.values())
    # THE ITEMISATION IS DERIVED FROM THIS TUPLE, and the summary below is derived from the
    # same tuple, so a limb added to scan() can no longer be reported as an unexplained gap in
    # an arithmetic that does not add up. `dead_module` was exactly that (order dded1fc0e664):
    # the limb landed, `total` counted its ten rows, and neither the print loop nor the summary
    # named it, so `47 finding(s) — 0 + 0 + 36 + 1 + 0` was the only thing a reader ever saw.
    KINDS = (("tautology", "CANNOT FAIL — both sides of the comparison are equal", "tautology"),
             ("phantom", "GUARDS AN UNDEFINED NAME — raises only on the branch "
                         "nobody takes", "phantom"),
             ("dead", "NEVER RUNS — no caller anywhere in src/", "dead"),
             ("dead_class", "NEVER INSTANTIATED — the class name appears nowhere "
                            "in src/", "dead class"),
             ("dead_module", "NEVER REACHED — nothing in src/ imports or names this module, so "
                             "every function in it is kept alive only by its siblings",
              "dead module"),
             ("unparsed", "WILL NOT PARSE — excluded from every check above", "unparsed"))
    if not a.quiet:
        for kind, label, _short in KINDS:
            rows = r[kind]
            print("\n%s  (%d)" % (label, len(rows)))
            print("-" * 78)
            for x in rows:
                print("   " + x)
    print("\nliveness: %d finding(s) — %s"
          % (total, ", ".join("%d %s" % (len(r[k]), short) for k, _l, short in KINDS)))
    # THE DECOMPOSITION IS ASSERTED, NOT ASSUMED. A printed bucket rather than a raised
    # AssertionError: the next limb must be visible to the reader on the day it lands, not on
    # the day someone runs this under -O or reads the traceback. Anything scan() returns that
    # KINDS does not name is counted and named here, so it cannot vanish the way dead_module
    # did.
    missing = [k for k in r if k not in {kind for kind, _l, _s in KINDS}]
    if missing:
        n = sum(len(r[k]) for k in missing)
        print("liveness: %d further finding(s) in kinds this report does not itemise (%s) — "
              "add them to KINDS in main()" % (n, ", ".join(sorted(missing))))
        if not a.quiet:
            for k in sorted(missing):
                for x in r[k]:
                    print("   [%s] %s" % (k, x))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
