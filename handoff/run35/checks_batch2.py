"""
Proposed checks for run35 batch 2 (agent working silence.py / codewatch.py / catalogue_aurora.py /
sevenfold.py / scope.py / weave.py / reference.py).

Same convention as checks_batch1.py: NOT run standalone. Assumes verify_math.py's own namespace
(`os`, `ast`, `check(label, got, want, note=...)`) is already in scope by the time this block
executes, and HERE/SRC-style path constants matching this project's convention. Everything below
WAS exercised standalone by this agent (against scratch copies / synthetic snippets / direct
function calls, not via verify_math.py or drill.py, per this run's rule that those two scripts
are not safe to run concurrently -- order c349a51ee2c5). The coordinator splices this in and
re-runs the battery.

Local names are suffixed _b2 to avoid colliding with verify_math.py's own `_NN<letters>` locals.
"""

import ast as _ast_b2
import re as _re_b2


# ==================================================================================================
# order 1018d49b186e -- catalogue_aurora.py, scope.py, sevenfold.py.
#
# The bug was a discarded `silence.write_json(...)` return value followed by an unconditional
# success print. A regression here is silent by nature (the print still runs; only a denied
# write on someone's machine would ever surface it), so the check reads structure, not behaviour:
# for each fixed file, confirm every `silence.write_json(...)` call site is the right-hand side
# of an assignment (or a `return`), never a bare expression statement whose result is thrown away.
# ==================================================================================================

def _writejson_calls_discarded_b2(path):
    """-> list of line numbers where `silence.write_json(...)` is called and its result unused."""
    with open(path, encoding="utf-8") as f:
        tree = _ast_b2.parse(f.read())
    bad = []
    for node in _ast_b2.walk(tree):
        if not isinstance(node, _ast_b2.Expr):
            continue
        call = node.value
        if (isinstance(call, _ast_b2.Call)
                and isinstance(call.func, _ast_b2.Attribute)
                and call.func.attr == "write_json"):
            bad.append(node.lineno)
    return bad

for _p_b2 in ("catalogue_aurora.py", "scope.py", "sevenfold.py"):
    _full_b2 = os.path.join(os.path.dirname(os.path.abspath(__file__)), _p_b2)
    check(f"1018d49b186e: {_p_b2} write_json verdict is captured, not discarded",
          _writejson_calls_discarded_b2(_full_b2), [],
          note="a write_json(...) call as a bare statement means its landed/denied verdict "
               "is being thrown away again")

# Positive control: confirm the detector itself actually catches a discarded call, so a typo'd
# attribute name or node type doesn't leave it silently matching nothing forever.
_synthetic_b2 = "import silence\nsilence.write_json(PATH, obj)\n"
_synthetic_tree_b2 = _ast_b2.parse(_synthetic_b2)
_synthetic_bad_b2 = [n.lineno for n in _ast_b2.walk(_synthetic_tree_b2)
                     if isinstance(n, _ast_b2.Expr) and isinstance(n.value, _ast_b2.Call)
                     and isinstance(n.value.func, _ast_b2.Attribute)
                     and n.value.func.attr == "write_json"]
check("1018d49b186e: discard-detector finds a real discarded write_json (positive control)",
      _synthetic_bad_b2, [2])


# ==================================================================================================
# order 4ec15db6540b -- weave.py, reference.py.
#
# The specific fault was a `silence.note("file.py:<N>")` label whose N pointed at the wrong line.
# A general "is N still correct" check would have to re-derive the right line every time this
# file is edited, which is exactly the maintenance burden content labels exist to avoid. So this
# checks the narrower, durable claim instead: the two sites this order named now carry the
# converted content labels, and the specific stale strings from before the fix are gone.
# ==================================================================================================

def _has_note_b2(path, label):
    with open(path, encoding="utf-8") as f:
        src = f.read()
    return f'silence.note("{label}")' in src

_HERE_B2 = os.path.dirname(os.path.abspath(__file__))
check("4ec15db6540b: weave.py carries the converted content label",
      _has_note_b2(os.path.join(_HERE_B2, "weave.py"), "weave.py:statblock-import"), True)
check("4ec15db6540b: weave.py's stale numeric label is gone",
      _has_note_b2(os.path.join(_HERE_B2, "weave.py"), "weave.py:187"), False)
check("4ec15db6540b: reference.py carries the converted content label",
      _has_note_b2(os.path.join(_HERE_B2, "reference.py"), "reference.py:shelfmark-navtree"),
      True)
check("4ec15db6540b: reference.py's stale numeric label is gone",
      _has_note_b2(os.path.join(_HERE_B2, "reference.py"), "reference.py:232"), False)


# ==================================================================================================
# order af1d0b1524e6 -- silence.py, instrument()'s classification rule.
#
# The fault was invisible to any check that merely re-derives the SAME buggy predicate and asks
# whether it agrees with itself. This instead runs the real `silence.instrument(dry=True)` against
# a scratch file holding one documented-exempt handler and one genuinely silent one, and asserts
# it finds exactly the genuinely silent one -- a true positive AND a true negative in one pass,
# against the production function, not a reimplementation of it.
# ==================================================================================================

def _instrument_classification_b2(tmp_dir):
    import shutil
    scratch = os.path.join(tmp_dir, "_canary_instrument.py")
    with open(scratch, "w", encoding="utf-8") as f:
        f.write(
            "def exempt_case():\n"
            "    try:\n"
            "        pass\n"
            "    except Exception:\n"
            '        _ = "silence-exempt: already gone IS released -- documented safe"\n'
            "\n"
            "def silent_case():\n"
            "    try:\n"
            "        pass\n"
            "    except Exception:\n"
            "        return None\n"
        )
    try:
        import silence as _silence_b2
        changed = _silence_b2.instrument(root=tmp_dir, dry=True)
    finally:
        with __import__("contextlib").suppress(OSError):
            os.remove(scratch)
    # `changed` is [(basename, n_sites)]; the exempt handler must NOT be counted, the silent one
    # must be the only site found.
    for _base, _n in changed:
        if _base == "_canary_instrument.py":
            return _n
    return 0

import tempfile as _tempfile_b2
with _tempfile_b2.TemporaryDirectory() as _tmp_b2:
    check("af1d0b1524e6: instrument() finds only the genuinely silent handler, not the "
          "silence-exempt one",
          _instrument_classification_b2(_tmp_b2), 1,
          note="if this is 0 the detector regressed to missing real sites; if it is 2 the "
               "silence-exempt marker is being rewritten again")


# ==================================================================================================
# order d99b11ec050e -- codewatch.py, _record_restart()'s shared-ledger race.
#
# A real concurrency regression test: hammer `_record_restart` from several threads against a
# scratch ledger (never the real state/CODEWATCH.json) and confirm every call's entry survives.
# Before the fix this reliably lost entries (verified by the agent, unlocked, on this machine);
# after the fix, N threads x M calls each must land N*M total entries with none of the per-key
# counts short.
# ==================================================================================================

def _codewatch_concurrency_b2():
    import importlib
    import threading
    import codewatch as _cw_b2
    importlib.reload(_cw_b2)
    scratch_dir = _tempfile_b2.mkdtemp()
    _cw_b2.LEDGER = os.path.join(scratch_dir, "_CANARY_CODEWATCH.json")
    _cw_b2.LEDGER_LOCK = _cw_b2.LEDGER + ".lock"
    names = ("foreman", "overwatch", "publish")
    calls_each = 20

    def worker(who):
        for _ in range(calls_each):
            _cw_b2._record_restart(who)

    threads = [threading.Thread(target=worker, args=(n,)) for n in names]
    [t.start() for t in threads]
    [t.join() for t in threads]
    import json as _json_b2
    with open(_cw_b2.LEDGER, encoding="utf-8") as f:
        doc = _json_b2.load(f)
    import shutil as _shutil_b2
    _shutil_b2.rmtree(scratch_dir, ignore_errors=True)
    return {n: len(doc.get(n, [])) for n in names}

check("d99b11ec050e: concurrent _record_restart calls lose no entries",
      _codewatch_concurrency_b2(), {"foreman": 20, "overwatch": 20, "publish": 20},
      note="a short count under any key means the read-modify-write race reappeared")


# ==================================================================================================
# order 44ca86b7a565 -- sevenfold.py, shelve()/seams() collapsing on tied weights.
#
# Calls the real `sevenfold.shelve` (not a reimplementation) with empty weights -- the exact
# call shape `build()` always uses for worlds -- and asserts the resulting top-level split is
# actually balanced: no child may hold more than roughly `ceil(N/span)` members. Before the fix
# this produced six 1-member children and one 94-member child for a 100-member block.
# ==================================================================================================

def _shelve_balance_b2():
    import sevenfold as _sf_b2
    members = [f"m{i}" for i in range(100)]
    coords = _sf_b2.shelve(members, {}, depth=1)
    from collections import Counter
    sizes = Counter(coords[m][_sf_b2.TIERS[0]] for m in members)
    return max(sizes.values())

import math as _math_b2
check("44ca86b7a565: shelve() with tied/empty weights balances children",
      _shelve_balance_b2() <= _math_b2.ceil(100 / 7) + 1, True,
      note="a lopsided split (one child holding most of the block) means seams() regressed to "
           "cutting the first k-1 positions instead of dividing evenly when nothing "
           "distinguishes the seams")


# ==================================================================================================
# order b68ca666da79 -- scope.py, Hard Rule 0 (srlimit + titles[:8] truncation).
#
# Static source check, matching this file's own house style for Hard Rule 0 audits: confirm the
# specific fixed-cap literals named in the original finding are gone, and the fallback-continue
# instrumentation the fix added is present. Not a live network check -- scope_for() makes real
# wiki API calls, which does not belong in a fast, offline verification battery.
# ==================================================================================================

def _scope_source_b2():
    with open(os.path.join(_HERE_B2, "scope.py"), encoding="utf-8") as f:
        return f.read()

_scope_src_b2 = _scope_source_b2()
check("b68ca666da79: scope.py no longer hard-caps srlimit at 3",
      '"srlimit": "3"' in _scope_src_b2, False)
check("b68ca666da79: scope.py no longer truncates fetched titles to 8",
      bool(_re_b2.search(r"titles\[:8\]", _scope_src_b2)), False)
check("b68ca666da79: scope.py fetches the FULL titles list",
      bool(_re_b2.search(r"F\.fetch\(host,\s*titles\)", _scope_src_b2)), True)
check("b68ca666da79: scope.py records when the wiki still withheld results past the raised cap",
      "scope.py:srlimit-bound" in _scope_src_b2, True)
