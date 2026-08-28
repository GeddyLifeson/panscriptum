# Net staged by run #36 — M46: a reap must never delete a LIVE run's sandbox

## What was actually wrong, after three wrong diagnoses

`mutate.py --target all` had been dying about four minutes in with a bare `FileNotFoundError`
on `<sandbox>/src/assay.py`, *after* its own baseline gates had passed in that same sandbox. It
blocked the entire §3b mutation mandate for three consecutive runs. It was blamed on:

1. **concurrent edits during the copy** (run #34) — ruled out: it reproduced on a stable tree;
2. **the `drill` gate** (run #35) — ruled out below;
3. **`drill.py` generally** (run #36's first two probes) — also wrong.

What settled it was the control nobody had run: build **two** sandboxes, run `drill.py` in only
**one**, and watch both. **Both died together, six seconds in.** A bare sandbox with nothing
whatsoever running against it died as well, while decoy directories under other prefixes
survived the same window untouched. So the reaper matched `SANDBOX_PREFIX` and nothing else.

The reason it had stayed invisible for three runs is that **reaping was the one destructive
operation here that reported nothing**: `removed` was returned to callers that discarded it, and
the only `note()` covered the *failure* case — so an incomplete reap was recorded and a
successful one was not. A reap ledger (`state/reap_ledger.jsonl`, added this shift) named the
call site on the first attempt: `drill.py → M.reap_orphans()`.

## The defect, stated plainly

`reap_orphans` deleted by **prefix and age only**. It had no notion of ownership, so it deleted
sandboxes belonging to **other live processes**. The age gate was the only thing standing
between a reap and somebody else's in-flight run — and an age gate is exactly what a caller
lowers when it wants to watch reaping actually happen. So `abandoned_sandboxes_are_reaped`, *in
the act of being made able to go red*, destroyed every concurrent sandbox on the machine.

That is the sharpest form of this project's standing lesson: the net that could not fail was
harmless, and **fixing it so it could fail is what made it dangerous.**

## The fix

A sandbox records its owner pid (`_owner.json`, written *before* any module is copied, since the
copy is the fragile window). `reap_orphans` skips any sandbox whose owner is still alive, **at
any age**. The age gate becomes what it should always have been: a fallback for sandboxes whose
owner died without cleaning up. Unknown/unreadable owner falls back to age-only, so no directory
becomes permanently undeletable — that would recreate the 154 MB leak this reaper exists for.

## The net, and the attack that defeats it

```python
    def _a_reap_never_takes_a_live_runs_sandbox():
        """M46. Reaping matched a prefix and an age, so it deleted other runs' live sandboxes.

        Attacked from the direction that actually happened: a sandbox owned by a DIFFERENT live
        process, against the most aggressive reap there is (`older_than=0`). Both other
        directions are pinned too, because a guard that simply never deletes anything would pass
        the first arm and reintroduce the disk leak the reaper was written for.
        """
        import json as _json
        import subprocess as _sp
        import mutate as M

        def _mk(tag, pid, age=0.0):
            d = tempfile.mkdtemp(prefix=M.SANDBOX_PREFIX + tag + "_")
            os.makedirs(os.path.join(d, "src"), exist_ok=True)
            if pid is not None:
                with open(os.path.join(d, M.OWNER_FILE), "w", encoding="utf-8") as fh:
                    _json.dump({"pid": pid, "started": time.time()}, fh)
            if age:
                os.utime(d, (time.time() - age, time.time() - age))
            return d

        made = []
        child = _sp.Popen([sys.executable, "-c", "import time; time.sleep(60)"],
                          creationflags=getattr(_sp, "CREATE_NO_WINDOW", 0))
        try:
            live = _mk("netlive", child.pid)
            dead = _mk("netdead", 999999999, age=10 * 3600)
            none_ = _mk("netnone", None, age=10 * 3600)
            made = [live, dead, none_]
            M.reap_orphans(older_than=0)
            survives_live = os.path.isdir(live)     # the M46 failure
            reaps_dead = not os.path.isdir(dead)    # no new disk leak
            reaps_unowned = not os.path.isdir(none_)
            return survives_live and reaps_dead and reaps_unowned
        finally:
            child.kill()
            child.wait(timeout=10)
            for d in made:
                shutil.rmtree(d, ignore_errors=True)

    net(a, "a reap never deletes a sandbox whose owner is still running",
        _a_reap_never_takes_a_live_runs_sandbox,
        "M46: reaping matched only a prefix and an age, so a drill net lowering the age to "
        "prove reaping works deleted a live mutation run's sandbox and blocked the whole "
        "mutation mandate for three runs")
```

**What defeats this net:** a future reap path that does not consult `_owner_pid` — a second
cleanup routine elsewhere, or a caller that removes the tree itself rather than going through
`reap_orphans`. The net proves the function, not the policy, so any new deleter of
`panscriptum_mutate_*` directories has to be brought under the same rule deliberately.

## Proven before staging

`handoff/run36/m46_fix_redcheck.txt` — five arms, run against the patched module:

```
arm 1  live-owned sandbox survives older_than=0 -> PASS
arm 1b another live process's sandbox survives -> PASS
arm 2  dead-owner sandbox is still reaped     -> PASS
arm 3  unowned old sandbox is still reaped    -> PASS
arm 4  CONTROL: without the check it dies     -> RED as required
```

Arm 1 **failed on the first attempt** and that is worth keeping: the first cut exempted only
*other* processes, so a sandbox owned by the reaping process itself was still deleted at
`older_than=0` — one `reap_orphans()` call inside a live run away from being M46 again with a
shorter stack. The rule is now "any live owner, including self".

## Note for whoever merges this

`abandoned_sandboxes_are_reaped` must be re-read against the new semantics. Reaping a directory
to demonstrate the net now requires that directory to have a **dead or absent** owner — which is
both easy to arrange and much closer to what the net claims to be testing.
