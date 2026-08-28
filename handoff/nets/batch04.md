# run #36, batch 4 — proposed drill nets

`src/drill.py` and `src/verify_math.py` are owned by other agents this shift, so these are staged
here for the run to merge serially. Each net names the guard it watches and the attack that would
defeat that guard. Every one was smoke-tested in this checkout against the modules as they now
stand (the probe scripts ran in a sandbox; no live ledger, no live SCOPE.json, no daemon touched).

Four nets, in the order I would paste them. Local names suffixed `_b4` where a collision looked
possible.

---

## NET 1 — the append-only rule must be IN EFFECT, not merely declared (order `db2728e0f4bb`)

**Guard:** `ledger_guard.check_since_snapshot()`, called from `assert_intact()` for every name in
`APPEND_ONLY`, and therefore from `publish.py:622` before every push.

**Why it needs a net rather than a review.** Measured on 2026-08-27 against the live 473,848-byte
`HANDOFF.md`: a copy truncated to its header and regrown LONGER than it began (476,271 bytes)
passed `check_all()` (the 20,000-byte floor), passed `verify_chain()` (nothing SHRANK — it grew),
and passed `assert_intact()`. Both surviving checks are size tests, and size is exactly what a
truncate-then-append preserves. `check_append_only`, the one check that could have seen it, had no
production caller anywhere in `src/`.

**The attack that would defeat the guard:** someone removes the `for name in APPEND_ONLY:` loop
from `assert_intact()` as redundant with `verify_chain()`'s SHRANK test — the two look alike and
only one of them can see a file that grew. Or the snapshot write is dropped from `seal()`, in
which case `check_since_snapshot()` returns `True, "no sealed snapshot yet"` for ever and reads,
from the outside, exactly like a check that passes.

```python
def drill_ledger_append_only_in_effect():
    """A ledger that was truncated and regrown must not reach the public repo.

    The byte floor and the chain's SHRANK test both measure SIZE, and a run that wipes the
    history and writes a long new entry produces a BIGGER file. Attacked here at the level that
    matters: assert_intact(), which is what publish.py actually calls.
    """
    a = "LEDGER GUARD — history is not a size"

    def a_truncate_then_append_is_refused_before_the_push():
        import os
        import shutil
        import tempfile
        import ledger_guard as LG
        sand = tempfile.mkdtemp(prefix="drill_lg_")
        here, chain, snap = LG.HERE, LG.CHAIN, LG.SNAPSHOT_DIR
        try:
            for n in ("HANDOFF.md", "BUGS.md", "NEXT_STEPS.md", "MAINTENANCE.md"):
                shutil.copyfile(os.path.join(LG.HERE, n), os.path.join(sand, n))
            LG.HERE = sand
            LG.CHAIN = os.path.join(sand, "chain.jsonl")
            LG.SNAPSHOT_DIR = os.path.join(sand, "snap")
            LG.assert_intact()                      # seals the good state
            old = open(os.path.join(sand, "HANDOFF.md"), encoding="utf-8").read()
            cut = old.index(chr(10) + "---" + chr(10))
            open(os.path.join(sand, "HANDOFF.md"), "w", encoding="utf-8").write(
                old[:cut] + ("x" * (len(old) + 5000)))     # LONGER, and the history is gone
            try:
                LG.assert_intact()
                return False                        # published a wiped relay: BREACHED
            except LG.LedgerViolation:
                return True
        finally:
            LG.HERE, LG.CHAIN, LG.SNAPSHOT_DIR = here, chain, snap
            shutil.rmtree(sand, ignore_errors=True)

    net(a, "a truncated-then-regrown HANDOFF.md cannot be published",
        a_truncate_then_append_is_refused_before_the_push, "")
```

---

## NET 2 — and it must not refuse the way the file is actually written (same order)

**Guard:** `ledger_guard._one_insertion()`, the second arm of `check_append_only`.

**Why.** `HANDOFF.md` is newest-on-top by its own header and by `MAINTENANCE.md:143`. A legitimate
run writes `header + new entry + everything that was under the header before`, which loses nothing
and which the old `old in new` containment REJECTED, because the old text stops being contiguous
the moment an entry is spliced in behind the header. A guard that refuses the only writing pattern
its file uses is a guard that gets deleted the first week it is wired up — and Hard Rule -1 already
records this project losing a gate exactly that way.

**The attack:** someone simplifies `check_append_only` back to the one-line containment test,
which looks tidier and passes every net that only tests refusals. This net tests the ACCEPT side,
which is the side that decides whether a safety survives contact with the operator.

```python
def drill_ledger_accepts_its_own_convention():
    """The guard must accept a newest-on-top append and still refuse a middle deletion."""
    a = "LEDGER GUARD — history is not a size"

    def the_documented_append_pattern_is_accepted():
        import ledger_guard as LG
        old = LG._read("HANDOFF.md") or ""
        cut = old.index(chr(10) + "---" + chr(10)) + 5
        prepended = old[:cut] + chr(10) + "## a new dated entry" + chr(10) + old[cut:]
        gutted = old[:cut] + old[cut + 400:]          # 400 bytes removed from the middle
        return (LG.check_append_only("HANDOFF.md", prepended)[0]
                and LG.check_append_only("HANDOFF.md", old + chr(10) + "tail")[0]
                and not LG.check_append_only("HANDOFF.md", gutted)[0])

    net(a, "newest-on-top and bottom-append both keep history; a middle deletion does not",
        the_documented_append_pattern_is_accepted, "")
```

---

## NET 3 — one of each, under concurrency (order `596551e4e37c`)

**Guard:** `overnight._guarded_popen()` and the `_SPAWN_LOCK` it holds across the
`running()`-then-`Popen` pair.

**Why.** The keeper thread (every 300s) and the top of each cycle both do check-then-spawn for the
same STANDING names. `_PROCS_LOCK` guards the process-table CACHE, not the decision. Reproduced in
this checkout with two threads and a stubbed slow `running()`: **2 processes spawned without the
lock, 1 with it.** The keeper's own comment claims "start() keeps the singleton guard, so the
keeper can never double anything" — true of one thread, and this file has had two since the keeper
was written.

**The attack:** someone moves the `running()` check back out of the lock ("it is already checked
above"), or removes `_guarded_popen` as an indirection and inlines `subprocess.Popen`. Both leave
every single-threaded test passing.

```python
def drill_overnight_no_double_spawn():
    """Two threads, one job name, one process. The keeper and the cycle both do this."""
    a = "OVERNIGHT — one of each"

    def concurrent_starts_spawn_once():
        import os
        import tempfile
        import threading
        import time
        import overnight as ON
        table, spawns = [], []
        keep = (ON.running, ON.subprocess.Popen, ON.STATE, ON.log)

        def slow_running(fragment, include_self=False):
            time.sleep(0.05)                       # the enumeration is what opens the window
            return any(fragment in s for s in list(table))

        def fake_popen(argv, **kw):
            time.sleep(0.02)
            spawns.append(argv)
            table.append(os.path.basename(argv[2]))
            return type("P", (), {"args": argv})()

        try:
            ON.running, ON.subprocess.Popen = slow_running, fake_popen
            ON.STATE, ON.log = tempfile.mkdtemp(prefix="drill_on_"), (lambda *x, **k: None)
            args = [os.path.join(ON.SRC, "pipeline.py")]
            ts = [threading.Thread(target=ON.start, args=("pipeline", args, "t.log"))
                  for _ in range(2)]
            for t in ts:
                t.start()
            for t in ts:
                t.join()
            return len(spawns) == 1
        finally:
            ON.running, ON.subprocess.Popen, ON.STATE, ON.log = keep

    net(a, "two concurrent start() calls for one job spawn one process",
        concurrent_starts_spawn_once, "")
```

---

## NET 4 — a scope may never be scored below its own evidence floor (order `09d47bc950d9`)

**Guard:** `scope.scope_for()` returning `None` when no tier reaches `MIN_MENTIONS`, instead of
falling back to the commonest tier.

**Why.** The module header exists to refuse frequency-based scoping, and the fallback applied
frequency at exactly the moment the evidence was thinnest. Measured over the 155 hosts in
`data/SCOPE.json`: 28 (18%) carry a ceiling that branch invented, including `root.fandom.com` and
`rosariovampire.fandom.com` at **M7 — universe scale — on two mentions of the word.**

**The attack:** someone restores an `argmax` fallback because a null scope "loses data", or lowers
`MIN_MENTIONS` toward 1, which reaches the same place by a different road. The net asserts the
INVARIANT (the winning tier cleared the floor) rather than the absence of a particular line, so
both routes trip it.

```python
def drill_scope_never_below_floor():
    """No scope may be returned whose own winning tier did not clear MIN_MENTIONS."""
    a = "SCOPE — the highest attested tier, never the commonest"

    def sparse_evidence_yields_no_ceiling():
        import scope
        import feats as F
        keep = (F.api, F.fetch, F.strip_wikitext)
        sparse = "The hero saved the universe. Another universe. A planet appeared."
        try:
            F.api = lambda h, p: {"query": {"search": [{"title": "T", "size": 5000}]}}
            F.fetch = lambda h, t: {"T": sparse}
            F.strip_wikitext = lambda v: v
            got = scope.scope_for("sparse.example")
            if got is not None and got["counts"][got["scope"]] < scope.MIN_MENTIONS:
                return False                       # a ceiling invented below the floor
            return got is None
        finally:
            F.api, F.fetch, F.strip_wikitext = keep

    def the_recorded_file_holds_no_sub_floor_ceiling():
        import json
        import os
        import scope
        if not os.path.exists(scope.OUT):
            return True
        d = json.load(open(scope.OUT, encoding="utf-8"))
        return not [h for h, v in d.items()
                    if v and (v.get("counts") or {}).get(v.get("scope"), 0) < scope.MIN_MENTIONS]

    net(a, "sparse evidence scores no ceiling at all", sparse_evidence_yields_no_ceiling, "")
    # NOTE FOR WHOEVER MERGES THIS: the second net will FAIL until SCOPE.json is rebuilt --
    # 28 of its 155 rows were written by the old fallback and are still on disk. Merge it
    # AFTER a `python src/scope.py --build` against a cleared file, or as a WATCHING item.
    # It is the one that keeps the fix, because the fix only changes what is written NEXT.
    net(a, "no recorded scope rests on evidence below the floor",
        the_recorded_file_holds_no_sub_floor_ceiling, "")
```
