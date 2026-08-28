# run #36, batch 1 — proposed drill nets (staged, NOT merged)

Batch 1 owns `assay.py`, `catalogue_aurora.py`, `codewatch.py`, `generate.py`, `sevenfold.py`.
`src/drill.py` and `src/verify_math.py` belong to other agents this shift, so the four nets below
are written out exactly as they should be pasted rather than edited in. Each one was RUN in this
session against the fixed code (held) and against the pre-fix behaviour (breached) before being
written down — the check line under each says which.

---

## 1. `drill.py` → inside `drill_no_caps()` — the Aurora dedup key drops distinct content

**Guards:** order `6816c9ad12f6`. `catalogue_aurora.parse_folder` used the key
`(type, normalised name)`, so the 2nd..Nth element sharing a (type, name) pair was dropped
unseen — 442 elements across the ten folders, 293 of them with DIFFERENT rules text
(e.g. four different subclasses' "Bonus Proficiencies" in `unearthed-arcana`). The key now
carries the description, and `parse_folder(folder, dropped)` fills `dropped` so the collapse is
counted.

**The attack that defeats it:** anyone shortening the key back to name-and-type "because the
same feature is obviously the same feature". Also catches dropping the `dropped` out-parameter,
which is what makes the collapse visible.

**Cost:** milliseconds. Writes two tiny XML files into a temp dir and removes them; it never
reads the owner's real `custom/` tree.

Paste at the end of `drill_no_caps()` (it uses `os`, `shutil`, `tempfile`, already imported at
the top of `drill.py`):

```python
    def aurora_keeps_same_named_distinct_elements():
        """Two subclasses' 'Bonus Proficiencies' are two elements, not one.

        Measured before the fix: 442 elements dropped across the ten catalogued folders, 293
        of them carrying rules text different from the one kept. A cap that leaves no count
        behind is exactly Hard Rule 0's prohibition wearing a dedup key.
        """
        import catalogue_aurora as CA
        real = CA.CUSTOM
        d = os.path.join(tempfile.gettempdir(), "drill_aurora_dedup")
        try:
            shutil.rmtree(d, ignore_errors=True)
            os.makedirs(os.path.join(d, "f"), exist_ok=True)
            CA.CUSTOM = d

            def xml(path, body):
                with open(os.path.join(d, "f", path), "w", encoding="utf-8") as fh:
                    fh.write("<elements>" + body + "</elements>")

            el = ('<element type="Archetype Feature" name="Bonus Proficiencies">'
                  '<description>%s</description></element>')
            xml("a.xml", el % "sidearms, from the 2015 document")
            xml("b.xml", el % "thieves tools, College of Satire")   # SAME name+type, other text
            xml("c.xml", el % "sidearms, from the 2015 document")   # a genuine verbatim restate
            dropped = []
            got = CA.parse_folder("f", dropped)
            descs = sorted(e["description"] for e in got)
            return (len(got) == 2
                    and descs == ["sidearms, from the 2015 document",
                                  "thieves tools, College of Satire"]
                    and len(dropped) == 1)          # the verbatim one collapsed, and was COUNTED
        finally:
            CA.CUSTOM = real
            shutil.rmtree(d, ignore_errors=True)
    net(a, "same-named Aurora elements with different rules text are both kept",
        aurora_keeps_same_named_distinct_elements,
        "a (type, name) dedup key dropped 293 distinct homebrew features and printed no count")
```

**Checked:** holds against the fixed `parse_folder`; breaches against the old key (the old code
returns 1 entry and has no `dropped` parameter at all).

---

## 2. `drill.py` → inside `drill_codewatch()` — the restart budget is claimed, not read-then-taken

**Guards:** order `c81c6ea16d10`. `exit_if_stale` read `_budget_left(who)` UNLOCKED and only then
called the locked `_record_restart(who)`, so two twins sharing a job key could both see the last
free slot and both spend it. Replaced by `_claim_restart_slot(who)`, one check-and-take under one
`_ledger_lock`.

**The attack that defeats it:** re-splitting the decision — any future edit that puts a
`_budget_left` read back in front of an unconditional write. The behavioural half alone cannot
see that (a sequential caller caps correctly either way), so the net also reads the function.

**Cost:** milliseconds, against a scratch ledger in a temp dir; it never touches
`state/CODEWATCH.json`. Note it sets `CW.LEDGER_LOCK` as well as `CW.LEDGER` — the existing
`restarts_are_budgeted` net swaps only the ledger, which leaves the lock file in the real
`state/` directory.

Paste after the existing `restarts_are_budgeted` net in `drill_codewatch()`:

```python
    def the_budget_is_claimed_not_read_then_taken():
        """Check and take must be ONE operation under ONE lock.

        `twins()` in this same file records the real incident: two `publish.py` processes
        seventeen seconds apart. Two processes on one job key each reading `left = 1` before
        either writes is how BUDGET_PER_HOUR = 4 becomes 5, in precisely the restart storm the
        budget exists to cap — and the ledger afterwards shows only that it happened.
        """
        import codewatch as CW
        import shutil
        real, real_lock = CW.LEDGER, CW.LEDGER_LOCK
        d = os.path.join(tempfile.gettempdir(), "drill_codewatch_claim")
        who = "__drill_claim__"
        try:
            shutil.rmtree(d, ignore_errors=True)
            os.makedirs(d, exist_ok=True)
            CW.LEDGER = os.path.join(d, "CODEWATCH.json")
            CW.LEDGER_LOCK = os.path.join(d, "CODEWATCH.lock")

            # a) exactly BUDGET_PER_HOUR claims are granted, and the ledger holds no more
            grants = [CW._claim_restart_slot(who)
                      for _ in range(CW.BUDGET_PER_HOUR + 3)]
            if [g for g, _ in grants] != [True] * CW.BUDGET_PER_HOUR + [False] * 3:
                return False
            with open(CW.LEDGER, encoding="utf-8") as fh:
                if len(json.load(fh)[who]) != CW.BUDGET_PER_HOUR:
                    return False
            # b) a refused claim writes NOTHING -- a refusal that still records is a leak
            before = os.path.getsize(CW.LEDGER)
            if CW._claim_restart_slot(who)[0] or os.path.getsize(CW.LEDGER) != before:
                return False
            # c) an hour on, the rolling window refills
            with open(CW.LEDGER, "w", encoding="utf-8") as fh:
                json.dump({who: [time.time() - 3601] * CW.BUDGET_PER_HOUR}, fh)
            if CW._claim_restart_slot(who) != (True, 0):
                return False
            # d) AND THE DECISION IS NOT SPLIT AGAIN. Read the function: a `_budget_left` read
            # in front of the write is the exact shape that raced, and it passes (a)-(c).
            src = os.path.join(os.path.dirname(os.path.abspath(__file__)), "codewatch.py")
            with open(src, encoding="utf-8") as fh:
                text = fh.read()
            body = text.split("def exit_if_stale(")[1].split("\ndef ")[0]
            return "_claim_restart_slot(" in body and "_budget_left(" not in body
        finally:
            CW.LEDGER, CW.LEDGER_LOCK = real, real_lock
            shutil.rmtree(d, ignore_errors=True)
    net(a, "the restart budget is claimed under one lock, not read then taken",
        the_budget_is_claimed_not_read_then_taken,
        "two twins each reading the last free slot is how a capped budget is exceeded")
```

**Checked:** (a)-(c) run green here against the fixed module (8 racing real processes given one
free slot produced exactly one grant and a ledger of exactly BUDGET_PER_HOUR); (d) is false
against the pre-fix `exit_if_stale`, whose body contained `_budget_left(who)`.

---

## 3. `drill.py` → inside `drill_codewatch()` or wherever exit codes are drilled — a refused
generate run must not exit 0

**Guards:** order `134188eb2296`. `generate.main()` printed "REFUSING EVERYTHING" when
`data/COVERAGE.json` was unreadable and then `return 0`, so `sys.exit(main())` reported SUCCESS
on a run that generated nothing because its safety data was broken — the same failure shape as
the missing-manifest bug fixed beside it, which returns 1.

**Why it is read and not run:** driving `main()` requires the prose gate to be open, and
`prose_enabled` is owner-held. A net must not stand that gate up, even in-process. So the net
parses the file and asserts the refusal branch's return value, which is the whole content of the
fix. `ast`, not a substring, so reformatting the message does not breach it.

**The attack that defeats it:** anyone "tidying" the refusal back to `return 0` on the grounds
that refusing correctly is not a failure.

**Cost:** one parse of `generate.py`, milliseconds. Needs `import ast` locally.

```python
    def a_refused_generate_run_exits_nonzero():
        """Refusing every job because the evidence data is broken is not a successful run.

        The exit code is the only thing the keeper reads. Zero here means a corrupt
        COVERAGE.json can hold prose generation at a standstill for ever without one failing
        exit code — a job that did nothing reporting exactly like a job that did everything.
        """
        import ast
        src = os.path.join(os.path.dirname(os.path.abspath(__file__)), "generate.py")
        with open(src, encoding="utf-8") as fh:
            tree = ast.parse(fh.read())
        found = []
        for node in ast.walk(tree):
            if not isinstance(node, ast.ExceptHandler):
                continue
            text = ast.dump(node)
            if "REFUSING EVERYTHING" not in text:
                continue
            rets = [n for n in ast.walk(node) if isinstance(n, ast.Return)]
            found.append(bool(rets) and all(isinstance(r.value, ast.Constant)
                                            and r.value.value not in (0, None)
                                            for r in rets))
        return len(found) == 1 and found[0]
    net(a, "generate.py exits nonzero when the evidence floor cannot be applied",
        a_refused_generate_run_exits_nonzero,
        "exit 0 on a run that generated nothing is a job reporting success for doing none of it")
```

**Checked:** returns True against the fixed file, False when the branch is `return 0`. The live
path itself was exercised separately this shift by patching `prose_gate._coverage_rows` to raise
inside a throwaway process: it printed the refusal and `main()` returned 1.

---

## 4. `drill.py` → a `drill_sevenfold` net — an unshelved source must be counted

**Guards:** order `8e79104f3112`. `sevenfold.build()` dropped an entire source's worlds with
`if base is None: continue` — no count, no note. `coords` covers only sources that survive
weave's resonance graph (209 today) while `by_source` comes from `worldseed` over every record
in `pipeline.records()` (210). It drops nothing today, which is exactly why it needs a net.

**The attack that defeats it:** removing `UNSHELVED` again, or the more likely one — a future
edit to `weave.filtered_index` that starts filtering a rules-heavy source out of the graph. With
this net the world count moves and something says so; without it the worlds simply are not there.

**COST WARNING, decide before merging:** `sevenfold.build()` measured **4.9 s** here, and this
net calls it twice (~10 s). If that is too expensive for the battery, the honest cheaper option
is the source-read half only (assert `UNSHELVED[src] = len(ws)` sits on the `base is None`
branch) — but the behavioural version below is the one that actually proves the count is right.

```python
def drill_sevenfold():
    """A world that is filed nowhere must at least be COUNTED somewhere."""
    a = "THE SEVENFOLD ORDER — is anything shelved nowhere and reported as nothing?"

    def an_unshelved_source_is_counted():
        import sevenfold as SF
        import tiers as TI
        _s0, _c0, _w0, worlds0 = SF.build()
        if SF.UNSHELVED != {}:
            return False                      # today every world-bearing source is in the graph
        victim = sorted({d.split("::")[0] for d in worlds0})[0]
        real = TI._graph

        def maimed():
            s, w, shared = real()
            return [x for x in s if x != victim], w, shared

        TI._graph = maimed
        try:
            _s, _c, _w, worlds = SF.build()
        finally:
            TI._graph = real
        lost = len(worlds0) - len(worlds)
        return lost > 0 and SF.UNSHELVED.get(victim) == lost
    net(a, "worlds whose source is absent from the resonance graph are counted, not vanished",
        an_unshelved_source_is_counted,
        "an entire source's worlds disappearing from every tier count with no line printed")
```

**Checked:** run here against the fixed module — dropping `2112 (Rush)` from the graph lost 5
worlds and `UNSHELVED` reported exactly `{'2112 (Rush)': 5}`, with the stderr note printed. Before
the fix `SF.UNSHELVED` does not exist, so the net breaches on `AttributeError`.
