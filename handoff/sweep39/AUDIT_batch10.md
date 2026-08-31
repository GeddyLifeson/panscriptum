# run39 — comprehensive source audit, BATCH 10

Modules owned by this batch (taken from `sweep_plan.batches(16)[9]['modules']`, not from any
hand-typed list), all read IN FULL:

| module | lines |
|---|---|
| `src/publish.py` | 1534 |
| `src/escalation.py` | 820 |
| `src/scout.py` | 666 |
| `src/zfighters.py` | 536 |
| `src/withdraw_chapters.py` | 422 |
| `src/catalogue_aurora.py` | 324 |
| `src/wh40k.py` | 301 |
| `src/chord_field.py` | 210 |
| **total** | **4813** |

Read-only audit. No source file was edited.

---

## 0. The two modules the maintenance shift changed today

Both were re-read against the current file before anything else, as instructed.

**`publish.py` `--loop` halt re-assertion — COMPLETE, not half-finished.** `main()` asserts the
halt once at startup (`publish.py:1398`), and the loop body now re-imports `escalation` per cycle
(`publish.py:1458-1464`, `SystemExit` on `ImportError`, so the generic `except Exception` cannot
swallow it) and calls `_ESC_CYCLE.assert_clear("publish.py cycle")` at `publish.py:1466`, catching
`SystemHalted` and **breaking** the loop with `rc = 1` (`publish.py:1467-1472`). The break — rather
than a retry — is the correct half and it is present. `drill.py:2818-2837` already has an AST net
requiring a reachable `escalation.assert_clear` inside the `while` body, and it resolves against
the loop-local alias.

**`escalation.HALT_REFUSAL` — COMPLETE and wired end to end.** Declared once at
`escalation.py:64`; `assert_clear` builds its message from it at `escalation.py:650`;
`allsweep.py:93` does `_HALT_REFUSAL = _esc.HALT_REFUSAL` (no second literal) and consumes it at
`allsweep.py:264` and `:318`; `verify_math.py:5447` pins `_alls20p._HALT_REFUSAL is
_esc20p.HALT_REFUSAL` by IDENTITY, and `verify_math.py:5457-5469` drives `assert_clear` against a
scratch halt file so the row cannot collapse to a literal-vs-literal comparison on a healthy
library. That was the stated defect and it is closed. The only remaining copy of the sentence is
`dashboard.py:867`, where it is a display label in the page's JavaScript, not a comparison — no
drift hazard.

Neither is reported below as incomplete.

---

## 1. Findings (each verified against the current source)

### F1 — MAJOR — the withdrawal archive's own manifest is overwritten with no guard
`src/withdraw_chapters.py:316` `record_path = os.path.join(arch, "catalog.withdrawn.json")`
`src/withdraw_chapters.py:331` `record_landed = silence.write_json(record_path, withdrawn, indent=2)`

Order `8d14f0adda1b` (WITHDRAW_ARCHIVE_COLLISION_OVERWRITES, closed) established that two
withdrawals sharing one `--label` archive silently destroy each other's files, and was closed by
adding `_archive_name_free` in front of **both** `shutil.move` sites (`:242-250` for catalogued
chapters, `:299-302` for strays). The manifest write did not get the same guard. `arch` is
`output/withdrawn_<label>`, `record_path` is one fixed name inside it, and `silence.write_json`
replaces unconditionally.

So: two `--go` runs on the same day (the default `--label` is today's date), or any two runs with
the same explicit `--label`, put both sets of chapter files in one archive — the file collision
guard lets them coexist because the names differ — and the second run's manifest **replaces** the
first's. The archive then holds chapters from two withdrawals under a manifest that lists only
one. This is precisely the outcome the module names at `:328-330`: "a heap of files with no
manifest", and it is the harm order `5d2d456145d0` only half-addressed (that order made the
verdict non-silent; it did not stop the overwrite).

Remedy: refuse an occupied `record_path` the way `_archive_name_free` refuses an occupied chapter
name, and either merge into the existing manifest or refuse the run and tell the operator to pick
a different `--label`. Merging is preferable — the archive really does hold both sets.

### F2 — MAJOR — the most destructive tool in the batch never asks whether the library is halted
`src/withdraw_chapters.py:131` (`def main()`), which reaches `shutil.move` at `:252` and `:304`
and rewrites `output/index/catalog.json` at `:346`.

`escalation.assert_clear`'s own docstring (`escalation.py:641`) opens "EVERY entry point calls
this before doing anything. The plant-wide interlock." Fourteen modules in `src/` call it;
`withdraw_chapters` is not one of them (verified by grep over `src/`). It moves chapter files out
of the library and rewrites the catalog those files are indexed by, and it does so under a
standing OWNER halt without ever reading `state/HALT.json`.

This is filed narrowly for this module rather than as the general gap, because this is the one in
this batch whose action changes the filesystem irreversibly. (The general gap — 83 of 97 `src/`
modules with a `__main__` do not call `assert_clear` — is a QUESTION, see §2.)

Remedy: `import escalation as _ESC` / `_ESC.assert_clear(os.path.basename(__file__))` as the first
statement of `main()`, fail-closed on `ImportError` exactly as `publish.py:1385-1398` does.

### F3 — MINOR — `publish.home_export()` is dead, and its body is duplicated inline beside it
`src/publish.py:85-87`

```
def home_export():
    return os.path.join(os.environ.get("USERPROFILE") or os.path.expanduser("~"),
                        "panscriptum-export")
```

Zero callers anywhere in `src/` or `handoff/` (verified by grep). `liveness.scan()` reports it in
its `dead` set as `publish.py:85 home_export()`. `export_root()` at `publish.py:115-116` builds
the identical path with the identical expression inline instead of calling it:

```
    fallback = os.path.join(e.get("USERPROFILE") or os.path.expanduser("~"),
                            "panscriptum-export")
```

Two spellings of one fact, one of them unreachable — the family-vs-enumeration shape this module
repairs elsewhere (`SKIP_SUFFIX`/`gitignore_lines`, `publish.py:158-184`), on the constant that
decides where a repo with a public remote lives. There is no open or closed work order naming
`home_export`.

Remedy: either delete `home_export`, or have `export_root`'s fallback call it so the two cannot
drift. The second is preferable — `export_root(env=...)` is written to be testable against a
synthetic environment, and `home_export` reads `os.environ` directly, so wiring them needs the
`env` parameter carried through.

### F4 — MINOR — `prune_export`'s refusal is silent and indistinguishable from "nothing to prune"
`src/publish.py:757-758`

```
    if not _may_delete_in_export():
        return 0
```

`sync_tree` receives that 0 at `publish.py:939` and `if pruned:` at `:940` prints nothing. So a
`SITE` that has lost (or never gained) its `.is-export-copy` marker — or one whose marker merely
cannot be read, since `_may_delete_in_export` uses `os.path.exists`, which answers False for
unreadable as well as absent (`publish.py:674-677` says so itself) — turns the whole prune off
**permanently and silently**, and every file withdrawn from the live project goes on being
re-staged by `git add -A` and published. That is the exact condition `prune_export` was written
for (order `f2271d9ee843`: `state/` sat in the public repo for two days).

The module already holds the opposite rule twelve lines up, at `publish.py:117-122`, about the
export-root refusal: "Loud, every cycle, and never silent: this is the exact class of default
whose firing must be reported rather than absorbed." And the return value collapses two worlds
into one number, which is the shape `PushHeld` (`publish.py:1085-1101`) and `clear()`
(`escalation.py:790-798`) were both rewritten for.

Also worth noting in the same remedy: the marker is written at the END of `sync_tree`
(`publish.py:947`), AFTER `prune_export` is called at `:939`, so the first cycle into a fresh
export directory is always a silent no-op prune. That one self-corrects; the misresolved-SITE case
does not.

Remedy: `silence.note` plus a stderr line naming which half of `_may_delete_in_export` refused,
and either a distinct return value or a raise so the caller cannot read it as "nothing to do".

### F5 — MINOR — a suppression's reason is cut to 60 characters, unmarked, in the line written to audit it
`src/publish.py:504-506`

```
                            _add((rel, i, "supp"),
                                 (rel, i,
                                  "SUPPRESSED (%s)" % supp.get("reason", "")[:60]))
```

The comment immediately above (`publish.py:498-502`) states the whole purpose of the line:
"Trivy's `--show-suppressed` discipline: a finding that is being waived still appears, tagged with
the reason it was waived, **so the waiver can be audited**." A reason cut mid-sentence with no
ellipsis and no "+N" is a waiver that cannot be audited from the line that exists to make it
auditable — and a reader cannot tell a cut reason from a short one.

This is the same `[:60]` construction that `scout.py:559-568` removed with the note "The `[:60]`
shape is the one standards.py's unrecognised-pool block already removed with the note 'fix a
shape, then grep the tree for it'; this is that grep." That grep did not reach here.

Remedy: print the whole reason, or wrap it, as `zfighters.py:511` and `wh40k.py:272` now do with
`textwrap.wrap`.

### F6 — MINOR — the credential refusal truncates its own evidence list with no marker
`src/publish.py:1205` `evidence=[{"file": f, "line": n, "why": w} for f, n, w in leaks[:20]]`
`src/publish.py:1210` `+ "\n".join("    %s:%s  %s" % (f, n, w) for f, n, w in leaks[:10])`

Both are silent `[:N]` slices on the list a person reads at the moment a publish is refused for a
credential. The `[:20]` one is the more serious of the two: it is the `evidence` array persisted
into `state/HALT.json` by `_raise_halt`, so the halt record a person opens carries twenty entries
and no statement anywhere in the array that there were more.

Mitigating, and stated honestly: the total **is** present in the same record — `"%d
credential-shaped value(s) staged"` at `publish.py:1202` and `"PUBLISH REFUSED — %d ..."` at
`:1208` — so a careful reader can subtract. That is the count, not a marker on the list, and the
project's own rule (`scout.py:509-518`, `withdraw_chapters.py:355-358`, "UNCAPPED. This is the
list a person reads to go and look at the files") is that the list itself carries the marker.

Remedy: append an explicit `{"and_more": len(leaks) - 20}` element / a `"... and %d more"` line, or
carry all of them — a secret scan's hit list is bounded by the number of real hits, and every one
of them is a file somebody has to open.

### F7 — MINOR — a stop that could not be recorded leaves a work order nothing can ever close
`src/escalation.py:413-415`, `:460-466`, `:592-593`, `:631-634`

`stop_subsystem` escalates at MANAGER **first** (`:413`), and `escalate` files a work order for
every escalation (`:243-251`), so a `SUBSYSTEM_STOPPED` order keyed `(code, where=name)` exists
before the write to `state/STOPPED.json` is attempted. If the compare-and-swap loop never lands
(`:428-459`), `stop_subsystem` escalates to OWNER at `:464` — correctly — but the
`SUBSYSTEM_STOPPED` order stands while `STOPPED.json` does **not** hold the name.

`resume_subsystem` is the only sanctioned way to close that order (`:631-634`,
`WO.resolve_code("SUBSYSTEM_STOPPED", ..., where=str(name))`), and it returns early at `:592-593`:

```
        if str(name) not in doc:
            return False
```

— before the `resolve_code` call. So for a stop that was escalated but never recorded, the queue
carries an open MAJOR order claiming a subsystem is stopped, addressed to RUN, that the API
provides no path to close. This is the same leak the module documents and repaired at `:613-626`
("the queue went on saying a subsystem was stopped after it had been resumed"), entered through
the failed-write door instead of the resume door.

Remedy: resolve the order in the not-landed arm of `stop_subsystem` (the stop did not take, so the
order is false), or have `resume_subsystem` resolve the code even when the name is absent from
`doc`, saying so.

### F8 — MINOR — `scout --dry` counts unregistered sources as found and says they now have somewhere to read from
`src/scout.py:392`, `:543-547`, `:572`, `:661`

`main()` passes `register=not a.dry` (`:661`) → `sweep(register=False)` → `scout(..., register=False)`.
In `scout`, `registered, reg_note = True, ""` at `:392` and the registration block at `:393-435` is
skipped entirely, so the result carries `"registered": True` having registered nothing. `sweep`
then tests `if r["kept"] and r.get("registered", True):` at `:543`, prints `FOUND`, increments
`found`, and finishes at `:572` with:

```
    print(f"\n{found} of {len(order)} sources now have somewhere to read from")
```

which is false in `--dry`: nothing was written to `SOURCE_PAGES.json` or `WIKI_HOSTS.json`, so the
sources are still hostless and the next `hostless()` returns them again. `sweep`'s own comment at
`:549-557` is explicit that `found` "is the count of sources that now have somewhere to read from",
and the `UNSAVED` branch exists precisely so a verified-but-unregistered source is not counted —
`--dry` walks past that distinction with `registered=True`.

Remedy: make `registered` reflect what happened — `registered = bool(kept) and register` or an
explicit third value `"registered": None` for "not attempted" — and have `sweep` print a
`--dry`-aware summary line ("would give N of M somewhere to read from").

### F9 — MINOR — `hostless()` reads WIKI_HOSTS.json with none of the care `_mutate` argues for on the same file
`src/scout.py:466` `hosts = json.load(open(F.HOSTS, encoding="utf-8"))`

No `try`, no shape check, and the handle is never closed. `_mutate` — the WRITE side of this same
file — spends `scout.py:119-135` arguing the opposite case at length, and enforces it at
`:148-159`: unreadable refuses with a note, and wrong-shape refuses with a note because
"wrong-shape is the same fact as unparseable". The read side has neither. A `WIKI_HOSTS.json`
that parses as a list gives `AttributeError: 'list' object has no attribute 'get'` at `:470`; one
that does not parse gives a `JSONDecodeError` out of `sweep()` and out of `main()`.

`foreman.scout_hostless` (`foreman.py:234-241`) wraps the call in `except Exception` and turns it
into a `silence.note` plus `False`, so on the standing path the failure is muffled rather than
loud — an unreadable host map reads as "the scout found nothing this cycle", which is the exact
conflation `_ask`'s `reached` flag was added to end (order `7f2cbf26a60e`, `scout.py:220-238`).

Remedy: read it through the same discipline `_mutate` uses — refuse and say which of the two
conditions it is, rather than raising an untyped exception into a caller that swallows it.

### F10 — MINOR — `foreman.scout_hostless` disagrees with `scout.sweep` about what "found" means
`src/foreman.py:236-238`

```
        res = SC.sweep(limit=4)
        found = sum(1 for r in res if r.get("kept"))
        return bool(found), f"{found} of {len(res)} sources given somewhere to read from"
```

`r["kept"]` is truthy for a source whose URLs passed verification and whose **registration
failed** — the `UNSAVED` case `scout.sweep` deliberately excludes from its own `found`
(`scout.py:548-558`, order `d57377577891`: "Not counted in `found`, because `found` is the count
of sources that now have somewhere to read from and this one does not"). So the same cycle can
print scout's honest `0 of 4 sources now have somewhere to read from` and foreman's `4 of 4
sources given somewhere to read from`, and foreman's is the line the supervisor's report carries.

Filed from this batch because it is scout's contract being read wrongly by its only standing
caller; the edit lands in `foreman.py`.

Remedy: `sum(1 for r in res if r.get("kept") and r.get("registered", True))`, matching
`scout.py:543`.

### F11 — MINOR — stale cross-reference in `zfighters.py`
`src/zfighters.py:477` — "Same ruling as `pantheon.py:294-297`, order 9d24c8a5febf, on the
identical last-column cut in this table's sibling."

Verified against the current `pantheon.py`. Lines 294-297 hold the *magnitude-band table* comment
("Charter Part Two's magnitude table ... M2-M4 and M7 are the bands Z_FIGHTERS.json actually
populates today"). The ruling actually cited — the removal of `epoch[:40]` from the ranked
table's last column — is at `pantheon.py:313-315`:

```
313        # `epoch[:40]` cut the last column of the ranked table for no gain: it is the LAST
314        # column, so nothing after it needs aligning and a long epoch costs only line length.
315        # Order 9d24c8a5febf, same rule as the citation cap below.
```

Remedy: `pantheon.py:313-315`. (Or drop the line number and cite the order id alone, which cannot
drift — the failure mode this whole class has.)

### F12 — MINOR — stale cross-reference in `wh40k.py`
`src/wh40k.py:276` — "ATOMIC, for the same reason and by the same hand as `zfighters.py:478`."

Verified against the current `zfighters.py`. Line 478 is `# order 9d24c8a5febf, on the identical
last-column cut in this table's sibling.` — a comment about epoch truncation in the ranked table,
not about the atomic write. The atomic/gated `silence.write_json` this sentence means is
`zfighters.py:516-529`, and the `write_json` call itself is at `zfighters.py:524`.

The citation was accurate when written and was invalidated by the `textwrap` repair that grew the
`--full` block above it — which is the mechanism `catalogue_aurora.py:151-156` names in this same
batch ("a line number is a fact about a file that edits invalidate silently").

Remedy: `zfighters.py:516-529`, or cite the order id alone.

### F13 — INFO — `verify()` reports an unsatisfiable check as an ordinary negative
`src/scout.py:324-328`

```
    probeable = sum(1 for n in names if (n or "").strip() and len((n or "").strip()) > 3)
    needed = max(1, min(MIN_NAME_HITS, probeable))
    return {"url": url, "ok": hits >= needed, "hits": hits, "needed": needed, ...
            "why": f"{hits} catalogued name(s) present, {needed} needed"}
```

When `probeable == 0` the `max(1, ...)` floor makes `needed = 1` while `hits` is structurally 0 —
`_names_in` (`:253-269`) skips every name shorter than 4 characters, so a source with no probeable
name can never score. Every URL then fails with `0 catalogued name(s) present, 1 needed`, which
reads as "the model guessed wrong" for a check that could not be satisfied before it was called.

That is the mirror-image of the fault this function's own docstring says it repaired
(`scout.py:287-303`: "This is the mirror of a net that cannot fail -- a check that cannot pass").
The `max(1, ...)` floor closed the one-name case and left the zero-name case open.

**Not live today**: measured against the current roll, all 8 hostless sources have at least one
probeable name (smallest: `aurora_mods (Way of the Inkmaster)`, 1 name, `needed=1`). `hostless()`
admits any source with a non-empty `entries` list, so an entry whose only names are blank or ≤3
characters reaches it. Latent, cheap to close.

Remedy: when `probeable == 0`, return `ok=False` with `why="unverifiable: this source has no
catalogued name long enough to probe with"` — a different finding with a different owner, exactly
as `verify()`'s docstring argues for the 404/403/200 distinction.

### F14 — INFO — `wh40k --full` drops the provenance mark its own `compute()` derives
`src/wh40k.py:272-275` prints `ax`, `score` and the wrapped citation and nothing else, while
`compute()` computes `_provenance(v)` for every axis (`:220`, `:225`) and its twin
`zfighters.py:512` prints the mark inline: `print("   %-15s%5.1f  [%s] %s" % (ax, d["score"],
prov, body[0]))`.

`compute()`'s docstring (`wh40k.py:195-215`) says the whole point of the `unattributed` default is
that it "leaves the gap VISIBLE for the curatorial pass, instead of hiding it behind a tag that
reads as if the work had been done". `--full` is the view a curator would use, and it is the one
view that does not show the gap. Every one of the 55 axis entries in this roster is a 2-tuple
(verified), so all 55 are `unattributed` today and `--full` shows none of that.

Adjacent to open order `82fc93f056d4` (WH40K_AXIS_PROVENANCE_NEEDS_A_CURATORIAL_PASS) but
distinct: that order is about doing the curatorial work, this is about the view not showing what
is already known.

Remedy: print `[%s]` as `zfighters.py:512` does.

---

## 2. Questions — two defensible readings, filed as questions rather than findings

**Q1 — `push()` treats "I could not tell whether commits are held" as a clean no-op.**
`publish.py:1223-1233`. `_unpushed()` answers `(None, why)` when the question genuinely cannot be
answered. On the clean-worktree path, `if not ahead:` catches both 0 and None; the None case gets
a `silence.note` and a stderr line, and then `return False` — which `main():1510` prints as `"no
change to push"` with `rc = 0`. Thirty lines down, at `:1306-1311`, the SAME uncertainty after a
push raises `PushHeld` with the sentence "Unconfirmed is not landed."
*Reading A*: it is a defect — `PushHeld`'s own class docstring (`:1085-1101`) exists because "a
return value can be read as success by any caller that does not know to look for a third state",
and stderr "is what a wrapper throws away" is that docstring's own words about this very module.
*Reading B*: no commit was made **this** cycle, so there is genuinely nothing new to send; the
comment at `:1226-1228` shows the author considered it and chose to say it on stderr rather than
fail a cycle on an unanswerable question.
Needs a ruling on whether stderr is a sufficient channel here given this file's own finding that
it is not.

**Q2 — `_FIELDS` gives `who` to OPERATOR and MANAGER but not to SUPERVISOR or SAFETY.**
`escalation.py:97-104`. `brief(rec, level)` is a deliberate whitelist, and the per-source log
written at `:172-173` uses the escalating rung's own field set — so a SUPERVISOR escalation ("this
source's area of the park closes") lands in that source's log without recording who closed it,
while an OPERATOR escalation one rung lower does record it.
*Reading A*: an oversight — `who` is a decision field at every rung that can stop work, and the
asymmetry has no stated reason.
*Reading B*: deliberate — the doctrine at `:88-91` is that "a safety net carries only what its
handler must act on", and a supervisor acting on a closed source arguably acts on the source, not
on the reporter; the janitor's log keeps `who` in full regardless.

**Q3 — "EVERY entry point calls this before doing anything" is true of 14 of 97.**
`escalation.py:641`. Measured: 97 modules under `src/` have an `if __name__ == "__main__"` block;
14 call `assert_clear` (`allsweep`, `dashboard`, `deprecated/catalogue_local`, `drill`,
`escalation`, `feats`, `foreman`, `local_agent`, `overnight`, `overwatch`, `pipeline`, `publish`,
`read`, `verify_math`).
*Reading A*: the docstring states an invariant that does not hold, which is the "a check that
cannot fail looks exactly like a check that passed" shape applied to prose — and the batch's own
`withdraw_chapters` (F2) shows the cost.
*Reading B*: "entry point" plausibly means a JOB entry point — the daemons, the pipeline, the
battery — and not every one-shot analysis or report tool; a halt that stops `zfighters.py` from
printing a table buys nothing, and open order `aad11acb1183` records the opposite harm (the
dashboard, the one instrument built to DISPLAY a halt, refuses to start under one).
A ruling that names the criterion would settle F2 and the eighty-odd other cases at once.

---

## 3. Checked and found clean (recorded so it is not re-measured)

* **Tautologies, always-true disjuncts, guards on undefined names**: `liveness.scan()` reports
  `tautology: 0` and `phantom: 0` across the whole tree, and I found none by eye in this batch.
  Every guard checked resolves against a symbol that exists: `codewatch.claim_singleton`/`stamp`/
  `exit_if_stale`, `mutate.active`, `ledger_guard.assert_intact`, `dashboard.state`/`PAGE`,
  `suppressions.suppressed`, `roll.update_rows`, `snapshot.before`/`verify`/`SnapshotFailed`,
  `pipeline.write_record_catalogue`, `endpoint.register`/`html_text`, `workorders.resolve_code`,
  `silence.write_json`/`append_line`/`replace_if_unchanged`/`digest_of`/`replace_retry` — all
  present, all with the signatures the call sites use.
* **`publish._swap`'s three literals are all present in `dashboard.PAGE` today** (verified by
  importing `dashboard` and testing each): `'/api/state'`, `setInterval(tick,5000)`,
  `Refreshes every 5 seconds.` The refuse-on-no-op guard at `publish.py:966-973` is live and
  correct.
* **`publish.maintenance_shift_live`'s guard target exists and its shape matches.**
  `state/MAINTENANCE_RUN.json` is written by `runguard.py:174` with exactly the `done`,
  `heartbeat` and `agent` keys `publish.py:1367-1378` reads. Not a guard on a file nothing writes.
* **`publish._unpushed`'s ordering is correct**: `if ahead:` before `if ahead is None:` at
  `:1301`/`:1306`, so None cannot fall through the truthiness test unnoticed.
* **`escalation._by_a_person_at_the_cli`'s frame depth is right**: `sys._getframe(2)` with
  0 = itself, 1 = `clear()`, 2 = `clear()`'s caller; `main()` in this file satisfies both
  conditions and no other caller can.
* **`escalation.escalate`'s unrecognised-level handling lands at MANAGER, not OWNER** (`:206-223`),
  as its comment claims, and the bad value travels in the evidence.
* **`zfighters.py:492` `rec["axes"][ax]` cannot KeyError today**: `assay.WEIGHTS` holds exactly the
  11 axes (8 physical + 3 faculty) that every ROSTER sheet carries, and the carried-in Son Goku
  sheet in `data/REFERENCE_ASSAYS_PRESENCE.json` has all 11 (verified). `zfighters.py:471-472`'s
  `rec.get("anchor") or rec["assay"].get("magnitude")` fallback is needed and works — Goku's sheet
  has no top-level `anchor`/`epoch`, and `assay.epoch` is populated (`'Mastered Ultra Instinct,
  Tournament of Power'`).
* **`zfighters`'s `_incomplete` marker really is skipped downstream**, as `zfighters.py:453-455`
  claims: `pantheon.py:278-279` does `if k.startswith("_")` and handles `_incomplete` explicitly.
* **`withdraw_chapters.py:403`'s cross-reference to `address_space.py:467-480` is ACCURATE** — the
  denied-`write_json` → `return 1` ruling occupies exactly those lines.
* **`textwrap.wrap` replaced the `[:56]`/`[:60]` citation cuts** in both `wh40k.py:272` and
  `zfighters.py:511`, with continuation lines, so `--full` shows whole citations.
* **`catalogue_aurora`'s dedup key carries the description** (`:165`), so the 442-element silent
  collapse is closed, and the collapse count is printed (`:224`). Its roll write goes through
  `roll.update_rows` CAS (`:296`) and its record write is gated (`:261`); `refused` reaches the
  exit code (`:315-320`).
* **`chord_field.py` has no caps, no guards and no error paths** — it is a pure constants-and-
  formulas module. Its only issue (nothing imports it, no function has a caller) is already filed
  as open order `7e360eaec3a6`; NOT re-filed here.
* **`escalation.Refused` is declared with no raiser** — already filed as open order `da15f582b2ea`;
  NOT re-filed.
* **`escalation.resume_subsystem` returning False for two worlds** — already filed as open order
  `7209d442c73e`; NOT re-filed. (F7 above is a different, adjacent hole: the order left OPEN by a
  stop that never landed.)
* **`publish.snapshot`'s swallowed `standards` block** (`6e92acd502fa`), **`git()`'s 220-character
  stderr clip** (`f5fdaab825a6`), **`render_page`'s truncate-then-fill** (`7d2d5f2d0d57`),
  **`scan_for_secrets`'s docstring naming a drill net that does not exist** (`f4ed53f4691b`), and
  **`sync_tree`'s unreachable COPY_FILES withdrawal** (`3d2d9b87cc10`) are all already on the
  queue. Re-verified as still standing; NOT re-filed.

---

## 4. A coverage stamp this batch got wrong, and corrected

Recorded here because it happened during this audit and because the ledger was edited by hand to
repair it.

`sweep_plan.batches(16)[9]['modules']` was called at dispatch and returned the eight modules
listed at the top of this file (4,813 lines), all of which were read in full. About forty minutes
later, following the protocol's own instruction to record coverage, **the same call returned a
different eight**: `publish.py, escalation.py, custodes.py, ingest_doc.py, burgs.py, genre.py,
resonance.py, halo.py`. Two in common, six different. `SP.record('run39', <that list>, batch=10)`
was called with it, so `state/sweep_shards/run39.10.45176.json` and the aggregate
`state/SWEEP_COVERAGE.json` briefly asserted that batch 10 had read six modules it never opened
and did **not** assert the eight it had.

Cause: `batches()` (`sweep_plan.py:102-115`) greedy-packs by LIVE line count, so any edit anywhere
in `src/` reshuffles every bin — and a sweep runs precisely while the maintenance shift is editing
`src/`. This is already filed twice, by other batches, as `44c420f80448`
(SWEEP_BATCHES_UNSTABLE_UNDER_LIVE_EDITS, seen twice) and `4d44a6363245`
(SWEEP_PLAN_BATCHES_RESHUFFLE_MID_SWEEP). No third independent order was filed; a corroboration
order `0c1670811107` records this sighting, because it is the first one where the predicted harm
actually landed in the ledger rather than being caught before the write.

**Repair performed:** the shard was rewritten in place to the eight modules actually read (with a
`corrected` key on the record explaining why), `SP.record` was re-run to rebuild the aggregate from
shards, and the result was verified module by module — the eight true modules now stamp `run39`,
`custodes.py` correctly falls back to `run38` (nobody has read it this run), and the other five
keep the stamps written by the batches that really did read them (12, 15, 16). `missing('run39')`
reports 19. No source file was touched.

---

*Audit written by run39 batch 10. Read-only; no source file was modified. The only file written
outside `handoff/` was the correction to this batch's own coverage shard, described in section 4.*
