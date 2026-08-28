# run #36, batch 2 — proposed drill nets

`src/drill.py` and `src/verify_math.py` are owned by other agents this shift, so these are staged
here for the run to merge serially. Every net below was smoke-tested standalone in this checkout
against the real, already-fixed modules, with a local `net`/`_refuses` stub matching `drill.py`'s
own signature (`net(area, name, attack, expectation)`, `attack()` returns True when the net HELD).
Local names are suffixed `_b2` where a collision looked possible.

Three nets, in the order I would paste them.

---

## NET 1 — `silence` must not swallow its own subject (order `6c1fc8ac52f8`)

**Guard:** `silence._handlers()` and `silence.instrument()` no longer treat an unreadable or
unparseable module as a module with nothing in it. Both now `note()` and say so out loud.

**The attack that would defeat it:** somebody restores the bare `except Exception: return []` /
`except Exception: continue` — or keeps the handler but drops the `note()`, so the failure is
printed to a stream nobody keeps and never reaches the ledger. This net checks the LEDGER, not
the print, because the print is the part that gets redirected away.

New function; goes in `drill.py` beside the other `silence` nets. Registration lines included.

```python
def drill_silence_self_report():
    """The audit for silent failures, audited for silent failures.

    `_handlers` and `instrument` both faced a file they could not read by returning nothing at
    all -- zero handler rows, no entry in `changed` -- which downstream is indistinguishable from
    a module that is simply clean. That is this module's own subject, committed by this module,
    and it is invisible to any check that only counts what the audit DID find.
    """
    a = "SILENCE — the recorder must not be the thing that goes quiet"

    def an_unparseable_module_is_recorded_not_skipped():
        """Point the audit at a file that will not parse. The row count is legitimately zero;
        what must NOT be zero is the ledger."""
        import os
        import tempfile
        import health
        import silence
        before = sum(v for k, v in health.LEDGER.items() if "silence.py:_handlers" in k)
        with tempfile.TemporaryDirectory() as d:
            with open(os.path.join(d, "zz_broken.py"), "w", encoding="utf-8") as f:
                f.write("def f(:\n    not python\n")
            rows = silence.audit(root=d)
        after = sum(v for k, v in health.LEDGER.items() if "silence.py:_handlers" in k)
        return rows == [] and after > before
    net(a, "a module the audit cannot parse is RECORDED, not counted as clean",
        an_unparseable_module_is_recorded_not_skipped,
        "zero handler rows and zero ledger entries is exactly the shape that filed 233 truncated "
        "Marvel pages as correct silence")

    def instrument_says_which_files_it_could_not_reach():
        """--instrument skipping a file is correct; skipping it silently is the fault. The
        skipped file must reach the ledger, and the file that CAN be instrumented must still be
        found in the same pass -- a net that only proves the failure path would pass just as well
        against an instrument() that had stopped working entirely."""
        import os
        import tempfile
        import health
        import silence
        before = sum(v for k, v in health.LEDGER.items()
                     if "silence.py:instrument-unparseable" in k)
        with tempfile.TemporaryDirectory() as d:
            with open(os.path.join(d, "aa_good.py"), "w", encoding="utf-8") as f:
                f.write("def f():\n    try:\n        pass\n"
                        "    except Exception:\n        return None\n")
            with open(os.path.join(d, "zz_broken.py"), "w", encoding="utf-8") as f:
                f.write("def f(:\n    not python\n")
            changed = silence.instrument(root=d, dry=True)
        after = sum(v for k, v in health.LEDGER.items()
                    if "silence.py:instrument-unparseable" in k)
        return changed == [("aa_good.py", 1)] and after > before
    net(a, "--instrument records the modules it could not reach", 
        instrument_says_which_files_it_could_not_reach,
        "a file absent from `changed` reads identically to a file with nothing to instrument")
```

Registration in whatever runs the areas (same shape as its neighbours):

```python
    drill_silence_self_report()
```

---

## NET 2 — a partial `binding_health` pass cannot land over a newer report (order `23d84e6f8e81`)

**Guard:** `run()`'s merge now takes `silence.digest_of(OUT)` BEFORE reading the report and lands
through `_land_cas` / `silence.replace_if_unchanged`.

**The attack that would defeat it:** a future edit drops the digest, moves the `digest_of` call
to AFTER the read (which produces a digest matching disk while the merged content is already
stale — a compare-and-swap that certifies the loss), or routes the merge back through the blind
`_land`. All three restore the exact partial-over-complete clobber the merge was written to stop,
and all three still pass any check that only looks at host counts on a quiet machine.

```python
def drill_binding_health_merge():
    """The merge that stops a partial run shrinking the estate, attacked as a race.

    A five-host `--host` pass reads BINDING_HEALTH.json, folds its results in, and writes the
    result back. Between the read and the write, a whole-estate `--run` can finish. Without a
    compare-and-swap the partial pass wins and ~200 fresh verdicts are replaced by a snapshot
    taken before they existed -- the write SUCCEEDS, which is why nothing would ever report it.
    """
    a = "BINDING HEALTH — the partial-pass merge, raced"

    def a_partial_pass_refuses_to_land_over_a_newer_report():
        import json
        import os
        import shutil
        import tempfile
        import binding_health as B
        import silence
        real_out, real_digest = B.OUT, silence.digest_of
        d = tempfile.mkdtemp()
        try:
            B.OUT = os.path.join(d, "BINDING_HEALTH.json")
            shutil.copy(real_out, B.OUT)

            fired = []

            def racing_digest(path):
                dg = real_digest(path)
                if not fired:                    # land a whole-estate report in the window
                    fired.append(True)
                    B._land(B.OUT, {"at": 0, "checked": 999, "failed": 0,
                                    "hosts": [{"host": "whole.estate", "healthy": True}]})
                return dg

            silence.digest_of = racing_digest
            try:
                B.run(only=["nosuch.invalid"])   # probes nothing: no network, no API budget
            finally:
                silence.digest_of = real_digest
            with open(B.OUT, encoding="utf-8") as f:
                doc = json.load(f)
            litter = [x for x in os.listdir(d) if x.endswith(".tmp")]
            return doc.get("checked") == 999 and not litter
        finally:
            B.OUT, silence.digest_of = real_out, real_digest
            shutil.rmtree(d, ignore_errors=True)
    net(a, "a partial pass refuses to land over a report written under it",
        a_partial_pass_refuses_to_land_over_a_newer_report,
        "the merge is a read-modify-write; without compare-and-swap it reintroduces the "
        "partial-over-complete loss it was written to prevent")

    def an_uncontested_partial_pass_still_lands():
        """The other direction, and the reason this net is two attacks. A CAS that refuses
        everything would pass the check above and quietly stop `--host` working at all."""
        import json
        import os
        import shutil
        import tempfile
        import binding_health as B
        real_out = B.OUT
        d = tempfile.mkdtemp()
        try:
            B.OUT = os.path.join(d, "BINDING_HEALTH.json")
            shutil.copy(real_out, B.OUT)
            with open(B.OUT, encoding="utf-8") as f:
                before = len(json.load(f).get("hosts") or [])
            B.run(only=["nosuch.invalid"])
            with open(B.OUT, encoding="utf-8") as f:
                doc = json.load(f)
            return len(doc.get("hosts") or []) == before and "partial_pass" in doc
        finally:
            B.OUT = real_out
            shutil.rmtree(d, ignore_errors=True)
    net(a, "an uncontested partial pass still merges and lands",
        an_uncontested_partial_pass_still_lands,
        "a compare-and-swap that refuses everything looks identical to one that works")
```

Registration:

```python
    drill_binding_health_merge()
```

**What the simulation does and does not model.** The racing writer is fired from inside
`digest_of`, i.e. between the digest and the read, because that is the only clean hook in the
function under test. The real race is slightly later — digest, read, *then* the other writer
lands — but both are caught by the same property (the digest was taken before the read, so it no
longer matches at write time), and pinning the hook where it is keeps the net free of any
patching of the merge itself. **Negative control run 2026-08-27:** substituting a blind
`_land_cas = lambda p, o, d: (_land(p, o), "blind")` makes the first attack BREACH, so the net is
load-bearing rather than passing on ambient behaviour.

---

## NET 3 — pin the `binding_verdict` calibration (order `30854f11f322`, LEFT OPEN)

**Why this net and not a fix:** the order asks for the `token_set_ratio` subset behaviour to be
treated as a bug. Measured against the live report, **all three** calibrated CONFIRMED hosts are
subset matches with low token_sort_ratio — `eberron` ⊂ `eberron rising from last war` (token_sort_ratio 40.0),
`war thunder` ⊂ `war thunder world tanks warplanes warships space refit` (sort 33.8), `aneurism` ⊂
`aneurism iv` (sort 84.2) — all three CONFIRMED at 100 on token_set_ratio alone. Any fix that penalises the subset relationship flips all three to
UNCLASSIFIED or MISBOUND and re-files the permanently-unfixable orders the discriminator exists
to stop. See my summary: that is an owner question, not a repair. What CAN be done today is
nail the five calibrated cases down so nobody "fixes" them by accident.

**The attack that would defeat it:** somebody swaps the metric (`token_sort_ratio`, `WRatio`,
`partial_ratio`), moves `BINDING_CONFIRMED_AT` / `BINDING_MISBOUND_BELOW`, or adds a
subset penalty — each of which silently re-classifies live hosts, and none of which fails
anything that exists today.

```python
def drill_binding_verdict_calibration():
    """The five hosts `binding_verdict` was calibrated against, pinned by name.

    PURE and network-free by construction (that is why `binding_verdict` was split out of the
    probe). The three CONFIRMED cases are all SUBSET matches -- the wiki names itself after part
    of the source, or the source name carries a subtitle the wiki does not -- so any change that
    stops rewarding a subset relationship re-opens the three unfixable work orders this
    discriminator was built to close, and any change that rewards it harder starts confirming
    misbindings. Both directions are named here.
    """
    a = "BINDING VERDICT — the 2026-08-26 calibration, held from both sides"

    # Copied verbatim from data/BINDING_HEALTH.json as it stood 2026-08-27 -- these are the
    # sitenames the hosts actually served and the source names actually bound to them, not
    # tidied-up versions of either.
    CALIBRATION_B2 = (
        ("Eberron Wiki", ["Eberron: Rising from the Last War"], "CONFIRMED"),
        ("War Thunder Wiki",
         ["War Thunder + World of Tanks/Warplanes/Warships (space-refit)"], "CONFIRMED"),
        ("ANEURISM Wiki", ["ANEURISM IV"], "CONFIRMED"),
        ("Prime Hydration Wiki", ["Prime World Equipment"], "MISBOUND"),
        ("The Brain World Wikia", ["Star Realms"], "MISBOUND"),
    )

    def the_calibrated_five_still_classify_as_measured():
        import binding_health as B
        for sitename, sources, want in CALIBRATION_B2:
            if B.binding_verdict(sitename, sources)["verdict"] != want:
                return False
        return True
    net(a, "the five calibrated bindings still classify as they were measured",
        the_calibrated_five_still_classify_as_measured,
        "these five ARE the calibration; a metric or threshold change that moves any of them is "
        "a re-classification of the live estate, not a refactor")

    def an_empty_side_is_UNKNOWN_not_a_verdict():
        import binding_health as B
        return (B.binding_verdict("", ["Anything"])["verdict"] == "UNKNOWN"
                and B.binding_verdict("Anything Wiki", [])["verdict"] == "UNKNOWN"
                and B.binding_verdict("Anything Wiki", ["Anything"])["score"] is not None)
    net(a, "no sitename and no source are UNKNOWN, never CONFIRMED",
        an_empty_side_is_UNKNOWN_not_a_verdict,
        "a host with no siteinfo scoring 100 against nothing would confirm every dead binding")
```

Registration:

```python
    drill_binding_verdict_calibration()
```

**Note for whoever merges this:** net 3 pins CURRENT behaviour including the false-CONFIRMED
exposure the order describes. If the owner later rules that a short generic sitename must not
CONFIRM, `CALIBRATION_B2` is the table to extend (add
`("Prime Wiki", ["Prime World: Equipment"], "UNCLASSIFIED")` — today that case returns CONFIRMED
at score 100, which is the order's whole point).
