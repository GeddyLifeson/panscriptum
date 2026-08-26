# SWEEP 34 — BATCH 03

Modules: `src/codewatch.py`, `src/feats_index.py`, `src/autostart.py`, `src/cachekey.py`,
`src/compress_store.py`, `src/drill.py`. All six read end to end.

Every finding below was verified against the source (and, where it is a claim about the corpus,
against disk) before it was filed. Anything I could not prove is a QUESTION at the end of its
section, not a finding.

**A note on `drill.py` line numbers.** I was told to audit it last because another agent was
editing it. It moved twice while I worked: 22:55:32 (2,774 lines) -> 23:07:11 (2,979 lines) ->
23:17:21 (+800 bytes, +10 lines). I read the whole file at the 23:07 state and then re-verified
every anchor at the 23:17 state — all nine findings are still present and unchanged in substance.
But the work orders were filed with the 23:07 line numbers, and everything below line ~1570 has
since shifted **+10**. Each order quotes its anchor text verbatim; trust the quote, not the
number.

---

## src/codewatch.py

### Findings

**C1 — `twins()`'s `exclude_pid` replaces self-exclusion instead of adding to it, and is dead.**
`f883d9bb534e` (MINOR / OWNER)

```
def twins(module, exclude_pid=None):
    me = os.getpid() if exclude_pid is None else exclude_pid
```

A caller passing `exclude_pid` would have its own pid stop being excluded, so the calling process
would count as its own twin and `claim_singleton` would stand a daemon down for itself. No caller
anywhere in `src/` passes it — `codewatch.py:193` calls `twins(module or who)` and
`drill.py:1999/2004/2094` call `CW.twins(needle)` / `CW.twins("anchors")` /
`CW.twins("verify_math")`. Dead API carrying a trap.

**C2 — `_record_restart()` is an unserialised read-modify-write of a shared ledger.**
`d99b11ec050e` (MINOR / RUN)

```
def _record_restart(who):
    try:
        with open(LEDGER, encoding="utf-8") as f:
            doc = json.load(f)
    except Exception:
        doc = {}
    ...
    doc[who].append(time.time())
    silence.write_json(LEDGER, doc, indent=2)
```

`foreman`, `overwatch` and `publish` all call `exit_if_stale()` and all write `state/CODEWATCH.json`
under their own key. One `src/` edit goes stale for all three at once — the normal case — and the
loser's write erases the winner's whole history. `silence.write_json` makes the *write* atomic; it
does not make read-then-write atomic, and there is no lock helper in `silence.py` (grep for
`flock` / `msvcrt` / `LOCK` finds none). So `BUDGET_PER_HOUR` undercounts exactly during the
multi-daemon restart storm it exists to catch.

### Attacking today's `twins()` fix (as instructed)

The fix itself holds up on the three things I could test:

* **It does not leak the sandbox.** `os.path.samefile(resolved, os.path.join(SRC, needle))` compares
  against *the importing module's* `SRC`, so a sandboxed `codewatch` compares against the sandbox
  and the live one against the live tree. The 22:38 false halt is genuinely closed.
* **`claim_singleton` still does the right thing.** It passes `module or who` — `"foreman"`,
  `"overwatch"`, `"publish"` — and those resolve to real absolute paths under `SRC`. The
  `STANDING` set launches every daemon with `os.path.join(SRC, ...)`, so `os.path.isabs` is true
  and the `proc.cwd()` branch is never reached for the daemons it actually guards.
* **The `OSError` fail-open is correct here.** A vanished sandbox makes `samefile` raise, and the
  right answer for a process whose file no longer exists is "not a twin".

The one thing I could not settle is a question, below.

### Questions

* **Is the `proc.cwd()` fail-open reachable in anger?** I measured the live table: 16 python
  processes, **0** `cwd()` failures, but **5** running with a *relative* script path — so the
  branch is live and exercised, it just never failed today. On Windows `psutil` can raise
  `AccessDenied` for another user's or an elevated process, and `proc.cwd()` reports the process's
  *current* directory, not its directory at launch. Either would silently drop a real twin. I have
  no evidence it happens on this machine, so I am not filing it. Worth a decision: is a missed
  twin acceptable in exchange for the false halt this fixed?
* `twins()` never matches `python -m <module>` — the argv scan breaks on the first non-flag,
  non-`.py` argument. Nothing in `src/` launches a daemon that way today. Deliberate?
* `stamp(who="?")` never uses `who`.

---

## src/autostart.py

(The `_twin_watchdog` fail-open-on-exception and runs-once-before-the-loop issues are already
filed as `8c354f6c9780` / `b0dc9acd2f79` and are **not** re-filed here.)

### Findings

**A1 — `supervisor_alive()` converts any exception into "dead", and `watch()` then spawns without a
budget.** `da8939f1ebc2` (MAJOR / RUN)

```
def supervisor_alive():
    try:
        import overnight as ON
        return ON.running("overnight.py")
    except Exception:
        silence.note("autostart.py:alive")
        return False
```

`watch()` calls this in `while True:` and calls `start_supervisor()` whenever it is false, every
`CHECK_SECONDS = 180`, for ever, with no budget and no backoff. The probe underneath is
`overnight._proc_lines()` — a PowerShell/CIM spawn with its own swallow-and-continue handler that
leaves `_PROCS["out"]` at its initial `""` (`overnight.py:96`), and `running()` opens with
`out = _proc_lines(); if not out: return False`. A PowerShell that is unavailable, throttled or
timing out therefore reads as "the supervisor is dead" — and each freshly spawned supervisor
guards itself with the *same* failing probe at `overnight.py:640`, so it does not stand down
either. N supervisors, N keeper threads re-asserting `STANDING`, N foremen shooting each other's
children: verbatim the respawn loop `watch()`'s own docstring says this module exists to prevent.
"Cannot tell" must not be spelled "dead".

**A2 — `_twin_watchdog()` matches a raw substring, which is the defect `codewatch.twins()` was
repaired for today.** `e079026adb9a` (MAJOR / RUN)

```
        if "autostart.py" in cmd and "--watch" in cmd:
            return True
```

No path resolution, no check of which checkout. A `--watch` started from `mutate.py`'s sandbox
copy of `src/`, from `panscriptum-export`, or from any second checkout makes the **live** watchdog
log "another watchdog is already running" and exit — after which nothing restarts the supervisor
and nothing says so. This is the sibling I was asked to look for. Also, the docstring claims "any
interpreter" while the CIM filter is exactly `Name='python.exe' or Name='pythonw.exe'`.

**A3 — `main()`'s status roster is a hand-kept subset, and it is already stale.**
`43d5bcfcdd19` (MINOR / LOCAL)

```
        for job in ("dashboard.py", "publish.py", "foreman.py", "overwatch.py",
                    "feats.py", "read.py"):
```

`overnight.ALL_JOBS` exists for this, and its own comment says *"Anything asking 'what should be up
right now?' reads THIS, not a hand-kept subset of it."* `STANDING` has since gained a `pipeline`
entry, so `autostart --status` can report every job green while `pipeline.py` is down; and it says
`feats.py` where `ALL_JOBS` says `feats.py --roll`.

**A4 — three stale `silence.note()` line tags.** `cb9cc3267474` (MINOR / LOCAL)

```
135        except Exception:
136            silence.note("autostart.py:131")     # 131 is a line inside the PowerShell string
144            except ValueError:
145                silence.note("autostart.py:139")  # 139 is the `for ln in out.splitlines()` line
180                except Exception:
181                    silence.note("autostart.py:174")
```

`health.py` aggregates these as `silent:<site>` keys, so each one sends the next diagnostician to
the wrong line. This file already uses the named form elsewhere (`:alive`, `:watch`, `:status`).

**A5 — `start_supervisor()` leaks two file handles per call, inside an infinite loop.**
`a79600702b85` (MINOR / LOCAL)

`out` and `err` are opened at `autostart.py:115-116`, handed to `Popen`, and never closed. The child
inherits its own duplicates, so the parent's copies serve no purpose after `Popen` returns — but
`watch()` calls this once per supervisor restart in a process designed to live from login to
shutdown.

### Questions

* `install()` writes the Startup `.vbs` with a plain `open(VBS, "w")`. Not JSON, not obviously a
  concurrently-read file — deliberate?
* `_twin_watchdog` re-imports `subprocess` inside its own body although the module already imports
  it at line 30. Harmless; leftover?

---

## src/cachekey.py

This is the cleanest module in the batch. The docstring's own measurements (5 colliding slots,
10 entities, 59 at the 80-char cap) are historical and dated, and the read-verify / write-
disambiguate design does what it says. One finding.

### Findings

**K1 — the host-directory formula is still hand-spelled in two places, contrary to this module's
own "ONE HELPER, NOT FOUR SPELLINGS" rule.** `5159320dd758` (MINOR / RUN)

```
cachekey.py:56-58  def host_dir(host): return _SANITISE.sub("_", host or "")[:HOST_CAP]
hostcheck.py:711   d = os.path.join(HERE, "data", base, re.sub(r"[^A-Za-z0-9]+", "_", mined)[:40])
allsweep.py:242    live = {_re.sub(r"[^A-Za-z0-9]+", "_", h)[:40] for h in hosts.values() if h}
```

Both are against the same `data/<base>/<hostdir>` layout `cachekey` computes, and neither goes
through `host_dir()`. `drill.py`'s helper-adoption net maps `"hostcheck.py": "cachekey"` — an
*import* test, not a *use* test — so it passes over both. If `HOST_CAP` or the sanitiser ever
moves, `hostcheck`'s purge silently deletes nothing and `allsweep` reports every live cache
directory as orphaned.

### Questions

* `text_digest()` re-imports `hashlib` locally although the module imports it at line 42.
* `provenance_ok()` reports `ok=True` when `text_map` carries a page the record never recorded —
  only recorded pages are compared. in-toto would call a new material a change. Deliberate?
* `write_path()` is a check-then-write on a path another writer could take in between. Given
  `load()` verifies ownership on read, is the race considered harmless?

---

## src/compress_store.py

### Findings

**S1 — the write verdict is thrown away, so a blob that never landed is reported as stored.**
`b635a4818c81` (MAJOR / LOCAL)

```
    tmp = "%s.%d.%d.tmp" % (path, os.getpid(), threading.get_ident())
    with open(tmp, "wb") as f:
        f.write(blob)
    silence.replace_retry(tmp, path)
    return {"hash": h, "path": path, "codec": codec, ...}
```

`silence.replace_retry` (silence.py:319-336) **returns False** on persistent denial — it notes
`replace-denied:<file>` and returns rather than raising, by explicit design. `store()` ignores that
and unconditionally returns a dict naming `path`, `codec` and `compressed_bytes`.
`generate.py:468-476` writes that straight into the catalogue as `compressed_path`, and
`catalog.py:97` opens exactly that path when the raw copy is gone. The `.tmp` is left behind too.

The comment block directly above the call is three paragraphs on why the landing must be atomic —
so the module understands the hazard and then discards the answer.

### Questions

* `silence.note("compress_store.py:14")` at line 16 tags line 14, which is `_HAVE_ZSTD = True`
  inside the `try`. Meant to point at the `import zstandard` on line 13, or is it stale? Too small
  to file on its own; worth folding into any pass over note tags.

---

## src/feats_index.py

### Findings

**F1 — the host is derived by an inversion that cannot invert, stranding 14 records / 222 feats
whose hosts ARE bound.** `4b41c1a30e26` (MAJOR / RUN)

```
        host = host_dir.replace("_", ".").lower()
        ...
            rec.setdefault("host", host)
```

The directory name was written by `cachekey.host_dir()`, which maps *every run of
non-alphanumerics* to `_`. Replacing `_` with `.` cannot undo that, so every hyphenated host comes
back wrong and its index key is unjoinable. Measured today:

```
audit()["stranded_hosts"]: date.a.live.fandom.com 4, sakamoto.days.fandom.com 2,
                           the.amazing.digital.circus.fandom.com 6, uncle.grandpa.fandom.com 2
data/WIKI_HOSTS.json:      'Date A Live' -> 'date-a-live.fandom.com'
                           'Sakamoto Days' -> 'sakamoto-days.fandom.com'
                           'The Amazing Digital Circus' -> 'the-amazing-digital-circus.fandom.com'
                           'Uncle Grandpa' -> 'uncle-grandpa.fandom.com'
```

14 records, 222 feats. All four hosts are bound. And the record already carries its own correct
host — every one of the 50 files I sampled has a `host` key, which is why line 165's
`rec.setdefault("host", host)` is a no-op on them. The fix is to key on `rec["host"]` and keep the
derived name only as a fallback. (`host_dir`'s 40-char cap is a second, latent, un-invertible
fold; no host is over 40 characters today.)

**F2 — the docstring and `main()`'s label both assert a diagnosis the data contradicts.**
`710c5b619291` (MINOR / LOCAL)

Docstring lines 36-38: *"**14 records / 222 feats** are hosts with no `WIKI_HOSTS` entry at all (the
amazing digital circus, date a live, sakamoto days, uncle grandpa) — sources whose host was never
recorded. A gap in that file rather than in this join, and binding those four hosts fixes them."*

All four **are** in `WIKI_HOSTS`. Binding will not fix them. The gap is in this join. `main()` then
prints `NOT IN WIKI_HOSTS` beside each, because line 262 tests the same mis-derived host — so the
report confidently sends the reader to the wrong file. (One host genuinely is missing:
`disney.fandom.com`, whose directory holds no records.)

The headline counts are also stale against disk. The module says 39,862 feats / 1,241 records /
1,166 entities; `load_index()` today returns **1,412 records and 47,017 feats**, and `audit()`
returns `{'records': 1412, 'joined': 1396, 'stranded': 16, 'feats_joined': 46646,
'feats_stranded': 371}`.

### Questions

* `load_index()` keys on `(host, _norm(entity))`, and `_norm` strips *all* non-alphanumerics — so
  `Magic 8 Ball` and `Magic 8-Ball` collide and the second file read silently overwrites the first
  in the index, invisible to `audit()`, which counts `len(idx)`. This is exactly the collision
  `cachekey`'s `__<sha>` suffix creates two files for. It is **latent today**: 1,412 files ->
  1,412 keys, and `data/readfeats` holds 0 suffixed files (`data/feats` holds 12). It becomes live
  the first time a colliding pair is mined into `readfeats`. Worth pre-empting, or leave it?

---

## Cross-module (a sibling of today's `codewatch` fix)

**X1 — `overnight.running()` still matches a raw substring against the whole command line.**
`844f39e73d12` (MAJOR / RUN)

```
overnight.py:179  if fragment in cmd.replace("\\", "/").split("/")[-1] or fragment in cmd:
                      return True
```

That second disjunct is the defect `codewatch.twins()` carries a twelve-line comment about having
fixed. And it is reachable on a schedule:

```
allsweep.py:383   subprocess.run([sys.executable, "-m", "pyflakes"] +
                                 [os.path.join(SRC, m + ".py") for m in mods], ... timeout=120)
local_agent.py:446 subprocess.run([PY, "-m", "pyflakes", full], ... timeout=120)
```

`allsweep` puts *every* module path on one command line for up to 120 seconds. During that window
`running("overnight.py")`, `running("publish.py")` and the rest are all TRUE. Consequences, all
live:

* `overnight.main():640` refuses to start a legitimate supervisor because someone is linting it.
* `overnight.run()` refuses to start a stage for the same reason.
* Worst: `autostart.supervisor_alive()` reports the supervisor **UP** while it is merely being
  *mentioned* by a linter, so the watchdog will not restart a genuinely dead supervisor for the
  length of the lint.

Neither is there any check of which checkout the path belongs to.

---

## src/drill.py

`drill.py` is the net collection, so a net that cannot fail here is a safety that has never refused
anything. Six of the nine findings are that shape. The `[:40]` and bare-`except` in
`_policy_corpus_clean` are already assigned to another agent and are **not** re-filed; the fixed
version now reads the whole corpus and fails on an unreadable record, which I verified.

### Findings

**D1 — `_step4_needs_its_plan()` renames the live owner document out of the tree on every run.**
`825429f941ba` (MAJOR / LOCAL) — anchor `os.rename(plan, tmp)`

```
    plan = os.path.join(HERE, "STEP4_PLAN.md")
    ...
    tmp = plan + ".drill-moved"
    os.rename(plan, tmp)
    try:
        return PG.step4_gate_open({"step4_enabled": True})[0] is False
    finally:
        os.rename(tmp, plan)
```

`STEP4_PLAN.md` exists (15,371 bytes), so this path is taken every run. This is the exact hazard
`_gates_agree`'s docstring twenty lines below documents as the reason the `config.yaml` write was
removed: *"`finally` does not run when the process is killed — and the foreman SIGTERMs stalled
jobs as a matter of routine."* The supervisor runs this drill every cycle. A kill in the window
loses the owner's plan and leaves `STEP4_PLAN.md.drill-moved`; on Windows every later run's
`os.rename(plan, tmp)` then raises `FileExistsError`, which `net()` scores as a BREACH and which
raises a real `DRILL_BREACH` halt. Point the gate at a scratch path, the way `_halt_fails_closed`
does with `ESC.HALT_FILE`.

**D2 — `drill_snapshot()` leaves a real snapshot behind on every run; they are now 100% of the undo
store.** `928eefc4bc96` (MAJOR / LOCAL) — anchor `sid = SNAP.before("drill", ["config.yaml"], ...)`

Both sibling nets `rmtree` their snapshot in a `finally` and say so in their docstrings ("the drill
leaves nothing behind"); this one never does. Measured: `state/snapshots` holds **149 directories,
1.4 MB, and every single one is named `drill-*`**. A person looking for the snapshot taken before
a real withdrawal has 149 self-test copies of `config.yaml` to sort through, and the directory
grows once per supervisor cycle for ever.

**D3 — "the withdrawal script takes one before moving anything" passes on a comment.**
`9dcb32e18f33` (MAJOR / LOCAL) — anchor `"snapshot" in open(... "withdraw_chapters.py")`

```
    net(a, "the withdrawal script takes one before moving anything",
        lambda: "snapshot" in open(
            os.path.join(os.path.dirname(os.path.abspath(__file__)), "withdraw_chapters.py"),
            encoding="utf-8").read(),
        "145 chapters were withdrawn with nothing but an instinct behind them")
```

The bare word appears at `withdraw_chapters.py:50` **in a comment sitting directly above the code
it claims to check** — the import, the `SNAP.before`, the verify and the refusal are lines 52-60.
Delete all of that, leave the comment, and the net stays green. `drill.py` documents this failure
twice in its own prose (`_no_programmatic_clear`: *"a literal cannot tell code from prose about
code: it fails on an honest description and it passes on a comment"*; `drill_two_writer`: *"standing
lesson 26"*).

**D4 — `guards_are_wired_where_claimed()` is satisfied by prose in at least three of its six
files.** `bcac9abeb28b` (MAJOR / RUN) — anchor `def guards_are_wired_where_claimed`

```
        want = {"generate.py": "assert_gate_open", "overnight.py": "_prose_enabled()",
                "coverage.py": "cachekey", "feats.py": "cachekey",
                "pipeline.py": "cachekey", "hostcheck.py": "cachekey"}
```

`coverage.py:53` mentions `cachekey` in a **docstring**; `pipeline.py:822` in a **comment**;
`feats.py:918-923` in a comment block. Remove the import and every call from those files and this
net — named *"every guard is present in the file that claims it"*, expectation *"the last incident
was a guard DELETED, not a guard that failed"* — stays green on the explanation of the guard that
is gone. Ask the AST, the way `_no_programmatic_clear` already does after this exact bug burned it
today.

**D5 — three nets assert a constant or a name and never drive a call.** `74e7cd4007a0`
(MAJOR / LOCAL) — anchors `1.0 < F.BACKOFF_MAX <= 128.0`, `hasattr(CB, "pool_exhausted")`,
`isinstance(CW.BUDGET_PER_HOUR, int)`

| net | assertion | what could be deleted with it still green |
|---|---|---|
| "the backoff has a ceiling" | `1.0 < F.BACKOFF_MAX <= 128.0` | `feats.py:148`'s `min(BACKOFF_MAX, ...)` — its sibling `_backoff_adapts` checks growth and recovery, never the ceiling |
| "an exhausted pool is a NAMED condition" | `hasattr(CB,"pool_exhausted") and callable(...)` | the body of `cascade_bridge.pool_exhausted:424` |
| "restarts are budgeted per job per hour" | `isinstance(CW.BUDGET_PER_HOUR,int) and 0 < ... <= 12` | `exit_if_stale`'s whole budget branch, `_budget_left`, `_record_restart` |

This is verbatim the shape `_throttle_hands_off`'s own docstring condemns — *"THE OLD NET ASSERTED
A CONSTANT AND A NAME ... Neither half ever drives a call"* — and which run #33 removed twice from
this same file.

**D6 — `main()` writes `state/drill_last.json` non-atomically and swallows the outcome.**
`950c61c886da` (MAJOR / LOCAL) — anchor `out = os.path.join(HERE, "state", "drill_last.json")`

```
    try:
        os.makedirs(os.path.dirname(out), exist_ok=True)
        ...
        with open(out, "w", encoding="utf-8") as f:
            json.dump({...}, f, indent=1, ensure_ascii=False)
    except Exception:
        pass
```

A truncate-then-fill, not a write, on a file with two live readers (`dashboard.py:529`, and
`workorders.py:564`, which grades the battery from it). A reader arriving in the gap sees an empty
verdict; a failed write leaves the *previous* run's result standing as current with nothing
recording that this run's verdict never landed. `silence.write_json`'s docstring counts twelve
sites already fixed for exactly this. The drill is a thirteenth.

**D7 — "COVERAGE.json unreadable is a refusal, not a pass" cannot fail on its named subject.**
`cb5f547ea13d` (MINOR / LOCAL)

```
121    net(a, "an unmeasured source is refused",
122        lambda: not PG.evidence_ok("no such source", 0.35, [])[0], ...)
...
133    net(a, "COVERAGE.json unreadable is a refusal, not a pass",
134        lambda: PG.cited_fraction("anything", None) is None
135        or PG.evidence_ok("nope", 0.35, [])[0] is False,
136        "unknown must mean stop")
```

The second arm is the assertion the first net of the same area already makes. So the whole
expression holds whatever `cited_fraction` does with an unreadable `COVERAGE.json` — it could start
returning `0.0`, "unknown" silently becoming "zero cited", which is precisely what this net exists
to forbid, and it would stay green. Assert the two properties separately.

**D8 — the two litter-cleanups swallow their reason.** `84fb573fe31f` (MINOR / LOCAL)

`drill.py:577-578` and `747-748` both close a real work order under a bare `except Exception: pass`.
If `WO.resolve_code` fails, a `DRILL_AREA` or `LOCAL_AGENT_BLAST_CAP` order stays in the live
queue, one per supervisor cycle, and nothing records why — the exact outcome the comment above each
one says the cleanup exists to prevent.

**D9 — two inspector docstrings promise more than the code checks.** `be1b02a4ffb6` (MINOR / LOCAL)

* `catalog_matches_disk`: *"Every chapter the catalog claims must exist on disk, **and vice
  versa**"* — the loop only walks catalog -> disk. A chapter on disk the catalog has lost is never
  noticed.
* `coverage_totals_are_recomputable`: *"the per-source arithmetic must **add up to** its own entry
  count"* — the code only refuses `parts > entries`, so a source whose states sum *below* its entry
  count (entries in no state at all) passes.

In both, the net's printed *name* is accurate and only the docstring overstates — which is the
shape that makes the next reader believe a property is covered when it is not.

### Questions

* `main()` truncates the breach summary to `breached[:5]` in both the escalation message and the
  mutation-run print. The full list rides in `evidence`, and `mutate.py` gates on the exit code
  rather than the names, so I read this as a report summary rather than a Hard Rule 0 truncation.
  Confirm?
* `main()`'s `_busy` check fails open to "not busy" if `import mutate` raises, i.e. toward
  halting. That is the safe direction for a breach — deliberate?
* `net()` does `held = bool(attack())`, so any truthy non-boolean counts as HELD. Every net I read
  returns a boolean expression, so nothing exploits it today. Worth tightening to `is True`?
* `publish_asks_before_pushing()`, `mutation_never_touches_the_live_tree()`,
  `daemons_actually_check_their_own_source()` and `singleton_guard_is_wired_into_the_daemons()` are
  all source-literal nets like D3/D4, but they search multi-token, code-shaped strings
  (`"def sandbox("`, `"REFUSING TO PUSH"`, `"codewatch.exit_if_stale"`) rather than a bare word,
  and `publish_asks_before_pushing`'s docstring explicitly argues that a net which actually pushed
  would be worse than the bug. I read those as a defensible pattern and did not file them. Is the
  line between them and D3/D4 the right one?
* `_twins_ignores_a_foreign_tree()` mutates the module global `CW.SRC` for up to 20 seconds and
  restores it in a `finally`. In-process only, single-threaded drill, so nothing on disk is at
  risk — but it is the same "restore in a finally" pattern D1 is filed against. Acceptable because
  a kill loses nothing?
