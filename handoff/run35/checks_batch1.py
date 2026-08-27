"""
Proposed checks for run35 batch 1 (agent working assay.py / custodes.py / rigor.py).

These are NOT run standalone. They assume the surrounding verify_math.py namespace: `os`,
`ast`, `check(label, got, want, note=...)`, and the four scan variables/functions named below
already exist by the time this block executes (i.e. this is meant to be spliced in AFTER the
sections it references, sections 19ab / 20p / 20t / 20j-20k). The coordinator merges this in
and re-runs the battery; nothing here was executed against the live verify_math.py by the
agent that wrote it, per this run's rule that verify_math.py/drill.py are not safe to run
concurrently (order c349a51ee2c5). The AST/regex logic below WAS exercised standalone (against
synthetic snippets, and once against the real standards.py/dashboard.py for the d9b895708c45
check) to confirm it behaves as claimed.

Local names are suffixed to avoid colliding with verify_math.py's own `_NN<letters>` locals.
"""

import ast as _ast_b1
import re as _re_b1


# ==================================================================================================
# order 873330d2e98d -- belongs in verify_math.py.
#
# Four negative scans (`_ctx_literals` §19ab, `_failopen20p` §20p, `_writes_the_config20p` §20p,
# `_callers20t` §20t) are each asserted == [] with a parse-coverage net beside them (defends
# against a broken FILE) but no net proving the MATCHER itself can still find a real violation
# (defends against a broken PATTERN -- a typo'd attribute name, string constant or AST node type
# that would leave the scan silently matching nothing, forever, on every future file). The
# house pattern for that already exists three times in this file (the "is actually finding
# X, not silently matching nothing" checks) -- these are the same idea applied to the four
# gaps named in the order.
#
# Where the real matcher is already a standalone function (`_writes_the_config20p`), the canary
# below calls THAT function directly -- a true positive control. Where the real matcher is an
# inline loop with no reusable entry point (`_ctx_literals`, `_failopen20p`, `_callers20t`), the
# canary reimplements the identical predicate/regex here, faithfully, as the closest available
# substitute; ideally the coordinator factors each inline scan into a function the same way
# `_writes_the_config20p` already is, and then rebinds
# these canaries to call the real function instead of a parallel copy.
# ==================================================================================================

print()
print("[batch1] order 873330d2e98d -- positive controls for the four unguarded negative scans")

# ---- canary for _ctx_literals (section 19ab: Ollama request body hardcodes num_ctx) -----------
def _num_ctx_literals_b1_873(tree):
    out = []
    for n in _ast_b1.walk(tree):
        if not isinstance(n, _ast_b1.Dict):
            continue
        for k, v in zip(n.keys, n.values):
            if not (isinstance(k, _ast_b1.Constant) and k.value == "options"):
                continue
            if not isinstance(v, _ast_b1.Dict):
                continue
            for ok, ov in zip(v.keys, v.values):
                if (isinstance(ok, _ast_b1.Constant) and ok.value == "num_ctx"
                        and isinstance(ov, _ast_b1.Constant) and isinstance(ov.value, int)):
                    out.append(ov.value)
    return out


_canary_src_ctx_b1 = "body = {'model': 'x', 'options': {'num_ctx': 512}}\n"
check("[canary 873330d2e98d] the num_ctx-literal predicate still catches a hardcoded window",
      _num_ctx_literals_b1_873(_ast_b1.parse(_canary_src_ctx_b1)), [512],
      note="if this goes red, the shape `_ctx_literals` (S19ab) looks for may have stopped "
           "being matchable and `_ctx_literals == []` above could be silently vacuous")

# ---- canary for _failopen20p (section 20p: escalation import wrapped in except ImportError: pass)
_canary_failopen_b1 = (
    "try:\n"
    "    import escalation as _ESC\n"
    "    _ESC.assert_clear()\n"
    "except ImportError:\n"
    "    pass\n"
)
check("[canary 873330d2e98d] the escalation fail-open regex still catches its own attack shape",
      bool(list(_re_b1.finditer(
          r"import escalation as _ESC\s*\n\s*_ESC\.assert_clear[^\n]*\n\s*except ImportError:"
          r"\s*\n\s*pass", _canary_failopen_b1))), True,
      note="if this goes red, `_failopen20p`'s regex may no longer match the bug it was written "
           "to catch, and `_failopen20p == []` above could be silently vacuous")

# ---- canary for _writes_the_config20p (section 20p: a function that names config.yaml AND opens
# ---- something for writing) -- this one calls the REAL function, since it already is one.
_canary_writes_cfg_src_b1 = (
    "def _bad():\n"
    "    x = 'config.yaml'\n"
    "    open(x, 'w').write('nope')\n"
)
check("[canary 873330d2e98d] _writes_the_config20p still catches a function that both names "
      "and writes config.yaml",
      _writes_the_config20p(_ast_b1.parse(_canary_writes_cfg_src_b1)), ["_bad"],
      note="genuine positive control (calls the real function, not a copy); if this goes red, "
           "`_writes_the_config20p(...) == []` above could be silently vacuous")

# ---- canary for _callers20t (section 20t: any spelling of a call to escalation.clear()) -------
def _escalation_clear_callers_b1_873(tree):
    out = []
    mods, direct = set(), set()
    for n in _ast_b1.walk(tree):
        if isinstance(n, _ast_b1.Import):
            for a in n.names:
                if a.name == "escalation":
                    mods.add(a.asname or "escalation")
        elif isinstance(n, _ast_b1.ImportFrom) and n.module == "escalation":
            for a in n.names:
                if a.name == "clear":
                    direct.add(a.asname or "clear")
    for n in _ast_b1.walk(tree):
        if not isinstance(n, _ast_b1.Call):
            continue
        fn = n.func
        if (isinstance(fn, _ast_b1.Attribute) and fn.attr == "clear"
                and isinstance(fn.value, _ast_b1.Name) and fn.value.id in mods):
            out.append("attr")
        elif isinstance(fn, _ast_b1.Name) and fn.id in direct:
            out.append("direct")
        elif (isinstance(fn, _ast_b1.Call) and isinstance(fn.func, _ast_b1.Name)
                and fn.func.id == "getattr" and len(fn.args) >= 2
                and isinstance(fn.args[0], _ast_b1.Name) and fn.args[0].id in mods
                and isinstance(fn.args[1], _ast_b1.Constant) and fn.args[1].value == "clear"):
            out.append("getattr")
    return out


_canary_esc_attr_b1 = "import escalation as _ESC\n_ESC.clear()\n"
_canary_esc_direct_b1 = "from escalation import clear\nclear()\n"
_canary_esc_getattr_b1 = "import escalation as _ESC\ngetattr(_ESC, 'clear')()\n"
check("[canary 873330d2e98d] the escalation.clear() scan still catches the aliased-attribute "
      "call shape",
      _escalation_clear_callers_b1_873(_ast_b1.parse(_canary_esc_attr_b1)), ["attr"])
check("[canary 873330d2e98d] ...the from-import call shape",
      _escalation_clear_callers_b1_873(_ast_b1.parse(_canary_esc_direct_b1)), ["direct"])
check("[canary 873330d2e98d] ...the dynamic getattr-dispatch shape",
      _escalation_clear_callers_b1_873(_ast_b1.parse(_canary_esc_getattr_b1)), ["getattr"],
      note="if any of these three goes red, `_callers20t == []` above could be silently "
           "vacuous for that call shape -- CLAUDE.md Hard Rule -1 names this exact assertion")


# ==================================================================================================
# order d9b895708c45 -- belongs in verify_math.py, replacing/supplementing the check at
# "every standard the checker declares actually emits a row".
#
# The existing check asserts `len(emitted) >= 40`. Measured against this checkout: standards.py
# statically declares 44 distinct standard names (one `_s(` call site's literal name, "calls
# that succeed", is reused across two mutually-exclusive branches, which is not a bug) and the
# live `standards.check(dashboard.state())` on this machine actually emits 43 of them -- still
# comfortably >= 40, so the existing check is green with FOUR standards' worth of headroom in
# which one can vanish and nothing red will show it, and even a genuine drop below 40 would
# only report a COUNT, never which standard went missing. The file's own comment 25 lines below
# the check (the "fabrication guard" section) already says the fix is to compare emitted against
# declared -- this does that.
#
# ONE declared name is legitimately silent on a fresh checkout: "promotions have their spine
# codes amended" is wrapped in `try: ... except FileNotFoundError:` in standards.py because it
# reads data/SHELF_RANKS.json, written by a phase 7 that has not run here -- the source's own
# comment marks it `"silence-exempt: phase 7 has not run yet"`. That is the one standard allowed
# to be declared-but-silent; anything else missing is the run #25 shape (a standard that stopped
# firing) and should fail loud, by name, not by a falling count nobody reconciles.
# ==================================================================================================

print()
print("[batch1] order d9b895708c45 -- declared-vs-emitted reconciliation for standards.check()")

_KNOWN_CONDITIONAL_STANDARDS_B1 = {
    "promotions have their spine codes amended",  # SHELF_RANKS.json: phase 7 has not run yet
}

_standards_path_b1 = os.path.join(os.path.dirname(os.path.abspath(__file__)), "standards.py")
with open(_standards_path_b1, encoding="utf-8") as _f_b1_std:
    _standards_src_b1 = _f_b1_std.read()

_declared_b1, _unliteral_b1 = set(), []
for _n_b1 in _ast_b1.walk(_ast_b1.parse(_standards_src_b1)):
    if (isinstance(_n_b1, _ast_b1.Call) and isinstance(_n_b1.func, _ast_b1.Name)
            and _n_b1.func.id == "_s"):
        if (_n_b1.args and isinstance(_n_b1.args[0], _ast_b1.Constant)
                and isinstance(_n_b1.args[0].value, str)):
            _declared_b1.add(_n_b1.args[0].value)
        else:
            _unliteral_b1.append(getattr(_n_b1, "lineno", "?"))

check("[d9b895708c45] every _s() call site names its standard with a literal string, so a "
      "static declared-vs-emitted scan can see it",
      _unliteral_b1, [],
      note="a computed or f-string name would hide from the scan below entirely; line(s): "
           + ", ".join(str(x) for x in _unliteral_b1))

_emitted_b1 = {r["standard"] for r in
               __import__("standards").check(__import__("dashboard").state())}
_missing_b1 = sorted(_declared_b1 - _emitted_b1 - _KNOWN_CONDITIONAL_STANDARDS_B1)
check("[d9b895708c45] every standard standards.py declares actually emits a row (declared vs "
      "emitted, not a hardcoded floor)",
      _missing_b1, [],
      note="declared=%d emitted=%d exempt=%d; missing and UNEXEMPTED: %s"
           % (len(_declared_b1), len(_emitted_b1), len(_KNOWN_CONDITIONAL_STANDARDS_B1),
              ", ".join(_missing_b1) or "none"))
check("[d9b895708c45] the conditional-standard exemption list has no stale entries",
      sorted(_KNOWN_CONDITIONAL_STANDARDS_B1 - _declared_b1), [],
      note="a name here that standards.py no longer declares is a stale exemption guarding "
           "against nothing")
