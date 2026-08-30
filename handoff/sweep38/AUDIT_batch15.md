# SWEEP 38 — AUDIT, batch 15

Agent: `sweep38-batch15`. Eight modules, 4,469 lines, all read in full.
Read-only pass: nothing under `src/` was edited.

Modules: `binding_health.py`, `overwatch.py`, `escalation.py`, `ingest_doc.py`,
`canon_backup.py`, `navtree.py`, `tempus.py`, `resync_roll.py`.

Verification scripts live in
`…/scratchpad/sweep38/batch15/` (`probe.py`, `repro.py`, `ow.py`); every measured
number below came from running them against the live tree on 2026-08-29.

---

## binding_health.py (1,146 lines) — 4 findings

Read in full. The module is in good shape: the CAS on both state files, the three-valued
`verdict()`, the fail-closed `QuarantineUnreadable`, the whole-estate/partial-merge guards and
the `_report_not_released` capture are all present and coherent today. Four faults survive.

**1. The canary's failure reason is truncated twice on its way to disk.** `_probe_present`
builds its detail naming only `tried[:4]` of up to `PRESENT_CANDIDATES` (8) titles
(`binding_health.py:562-563`), with no "and N more"; `quarantine()` then stores
`str(reason)[:300]` (`:355`, `:364`). Reproduced offline against the live records for
`fireemblem.fandom.com`: the reason a 429 would produce is 330 characters and is stored cut
mid-title —

```
STORED (300 chars): host unreachable: HTTPError: HTTP Error 429: Too Many Requests (present
probe: 8 known-present title(s) all returned nothing or too little to be a page (tried:
'Characters', 'List of characters in Fire Emblem Awakening', 'List of characters in Fire
Emblem Echoes: Shadows of Valentia', 'List of chara
```

Eight candidates were attempted, four are named, and the fourth is then cut in half. The live
`HOST_QUARANTINE.json` holds one host (`www.dandwiki.com`, reason 229 chars), so nothing is cut
*today* — this is the cheap moment. Filed.

**2. `_probe_absent` applies a weaker gate than `_probe_present`.** `_fetch_chars` runs every
fetched body through `feats.page_looks_real` (length → refusal markers → wiki markup) precisely
because "a Cloudflare interstitial, a login wall, a JS challenge or a rate-limit notice is a real
document". `_probe_absent` (`:566-596`) does none of that: any truthy return from
`feats.fetch(host, [ABSENT_PROBE])` is read as "resolved a title that cannot exist", which is the
one branch of `verdict()` that quarantines a host *whatever its reachability*. Filed.

**3. `n >= 200` at `:545` contradicts the docstring directly above it.** `_fetch_chars`'s
docstring states "THE PAGE IS JUDGED BY `feats.page_looks_real`, NOT BY ITS LENGTH. This counted
characters and the caller compared them against a hardcoded 200" — and the caller still does.
Harmless today (`feats.MIN_REAL_PAGE_CHARS` is also 200, confirmed at runtime) and a silent
divergence the moment that constant moves. Filed.

**4.** Not filed, recorded here: `main()` truncates the console table (`host[:34]`,
`reason[:60]`, `--quarantined`'s `reason[:60]`). `ingest_doc.py:348` states the house ruling that
"the console renderers truncate at their own call sites", so this is rendering, not a cap on
stored or acted-on data. Left alone.

## overwatch.py (946 lines) — 2 findings

Read in full. The ledger lifecycle (`load`/`_merge_ledgers`/`_reconcile_with_disk`, the
`_UNPRESERVED` refusal, the `complete`/yielded discipline in `review` and `verify_open`, the
per-round `_LOCAL_BUSY` reset) is sound.

**5. `save()` writes through a shared temp name.** `tmp = LEDGER + ".tmp"` (`:249`) — in the one
module whose own `save()` docstring says "two processes hold this ledger routinely: the standing
`--loop` job, plus any ad-hoc `verify_open` call a maintenance run leaves behind", and which
built `_merge_ledgers` for exactly that. The merge protects the *content*; nothing protects the
*scratch file*. `write_report` twelve lines further down already does the right thing
(`"%s.%d.tmp" % (REPORT, os.getpid())`), so the file disagrees with itself. Filed.

**6. WATCH.md truncates each finding's text.** The `[:40]` cap on the finding *list* was removed
under order e8e095597f74 with a long note about Hard Rule 0; the per-finding
`actual[:180]` / `claim[:160]` (`:721-722`), the reconcile line's `detail[:80]` (`:699`) and
`--show`'s `actual[:150]` (`:911`) were left. Measured against the live ledger: 435 findings, 71
of them (16%) carry an `actual` longer than 180 characters, longest 966; 27 carry a `claim` over
160. WATCH.md is a file, not a console, and is described in this module as the only thing a
person reads to learn what the sweep found. Filed.

## escalation.py (658 lines) — 2 findings

Read in full. `_read_halt_raw`'s shape check, `_read_stopped`'s wrong-shape fail-closed arm,
`_safe_name`'s injective truncation, the `BY_NAME`/MANAGER fallback for a bad rung, and
`clear()`'s runtime person-check are all correct as written.

**7. `main()`'s `--raise-halt` throws away `halt_landed`.** `escalate()` was rewritten (run #34)
to put the landing verdict *on the returned record* specifically so a caller could see it, and
this caller — the CLI a person uses to halt the library by hand — does
`escalate(OWNER, …)` / `print("halted.")` / `return 0` (`:610-614`). On the ordinary Windows
reader-holds-target case the halt file never appears, every other process's `assert_clear()`
finds no halt and carries on, and the operator was told "halted." with rc 0. This is the same
discarded-verdict defect the file fixes at four other sites, left standing at its own front door.
Filed.

**8. `_write_stopped` is the one write in this module that does not retry.** `:444-449` is
`os.replace(tmp, STOPPED)` with a pid-only (not thread-unique) temp name, where `_raise_halt` and
`clear` both go through `silence.write_json`/`replace_retry`. `subsystem_stopped()` is polled by
the keeper, so the destination is routinely open for reading — the exact denial the rest of the
project retries around. Two consequences: `stop_subsystem` catches the PermissionError and
escalates `SUBSYSTEM_STOP_UNRECORDABLE` at **OWNER**, so a transient rename denial halts the whole
library; and `resume_subsystem` does not catch it at all, so a resume exits by traceback. The
read-modify-write over `STOPPED.json` also has no compare-and-swap, so two concurrent stops lose
one. Filed.

## ingest_doc.py (517 lines) — 2 findings

Read in full. The write-verdict discipline is thorough here (extract raises, register returns
None, `write_record_catalogue` rewinds `known`, the cursor-lag asymmetry is argued and the
`landed_found` divergence is printed). `record_path`'s ambiguity refusal and the oversize-page
re-split are both correct.

**9. `mine()` opens the corpus with no guard.** `open(os.path.join(d, "pages.json"))` at `:245`,
and `main()` catches only `ValueError` around `mine()` (`:498-503`). `--mine --source X` for a
source that was never `--pdf`'d exits by FileNotFoundError traceback, in a module that otherwise
turns every refusal into a printed sentence and rc 1. Filed.

**10. The resume cursor uses a shared temp name.** `tmp_state = state_p + ".tmp"` (`:390`). This
matters more here than it looks: the module naps 300 s per transport miss for up to five hours,
so "it looks hung, I'll start another one" is its normal failure mode, and two miners on the same
source then share one scratch file for the only record of what has been done. Filed.

## canon_backup.py (398 lines) — 2 findings

Read in full. `members(strict=True)`'s refusal, the read-back verification, the age-based orphan
reap, the half-removed-pair rule in `prune`, and `verify`'s no-manifest fail-closed arm are all
correct.

**11. Three `[:5]` caps on lists a person reads to act.** `snapshot()`'s "N canonical file(s)
could not be read: …" (`:146`), its verification failure list (`:175`), and `verify()`'s
"canonical files present in the snapshot are GONE from the live tree" (`:338`). None says "and N
more", and `members()`'s own refusal eight lines up deliberately names every absent path. Filed.

**12. `_write_manifest` uses a fixed temp name.** `tmp = dst + ".writing"` (`:198`), eight lines
after `snapshot()`'s own comment reading "PID AND THREAD IN THE TEMP NAME, the convention
`silence.write_json` set after two writers sharing one fixed temp filename cost this project real
data." Filed.

## navtree.py (318 lines) — 1 finding

Read in full. The three named bugs the file exists to prevent are all genuinely prevented; the
m41 hash-order tie-breaks, `sources_under`'s boundary fix and the gated `NAVTREE.json` write are
all in place.

**13. `main()` returns 0 when its audit record did not land.** `audit_landed` is False, the
console says "AUDIT RECORD NOT WRITTEN … whatever is in that file is an older run's", and with
`--write` absent the function falls through to `return 0`. The same shape (`problems` found on a
read-only run also exits 0) — this is the defect `resync_roll.py` was corrected for under order
8605c2ed6061, with that module's own note that "THE EXIT CODE IS THE NUMBER THE SCHEDULER ACTUALLY
LOOKS AT". Nothing in `src/` currently shells out to `navtree.py`, so this is latent. Filed at
INFO.

## tempus.py (274 lines) — read in full, nothing found

Checked `is_present_at` against `concordance_now`'s definition (an event ratified to rung n is
present to every registry at or below n → `event_mark >= observer_rung`: correct);
`rung_description_length`'s floor (`BAND_EDGES["M0"]["ruin"] = 1e2`, no division by zero);
`band_resolution`'s M10 arm (inherits the M9→M10 width as documented) and its separation from
the cumulative figure, which `verify_math` pins at four places including
`measure_bit_value("M5") == band_resolution("M5")/10`; `apparent_lag_years`'s single return
shape; and `prescience_horizon_bits`'s non-positive-lead refusal. The `/10 per decimal point` in
`band_resolution`'s summary line reads slightly loose against a function that returns the whole
band's width, but the docstring body states the formula correctly and `rigor.measure_bit_value`
does the division — not a defect.

## resync_roll.py (212 lines) — 1 finding

Read in full. The duplicate-source flagging, the unreadable/unmatched counting, the caveat that
travels with the closing figure, the status rule's OUT_OF_SCOPE exemption and the gated write
with its non-zero exit are all correct. Verified against the live tree: 0 record files fail to
parse and 0 lack a declared `source`, so neither of those arms is currently firing.

**14. `--dry-run` is detected by scanning `sys.argv`.** `dry = "--dry-run" in sys.argv` (`:31`),
with no argparse anywhere in the module. Any near miss — `--dryrun`, `--dry`, `-n` — is silently
ignored and the script performs a real write to `data/SWEEP_ROLL.json`, the file this module's own
docstring opens by describing being clobbered. Filed.

**15.** Not filed, recorded here as a question of house style: the `changed` and `relabelled`
tables print `name[:44]` in a fixed-width column while the module's own comment declares its two
other lists "UNCAPPED, both of them, per Hard Rule 0". 11 of the 215 roll names exceed 44
characters (longest 82, *Who Framed Roger Rabbit (incl. all content from its associated
crossover-toon IPs)*), and no two names share a 44-character prefix today, so nothing is currently
ambiguous. By the `ingest_doc.py:348` ruling — console renderers truncate at their own call sites
— this is rendering, not a cap. Left alone.

---

## Summary

| module | lines | verdict |
|---|---|---|
| binding_health.py | 1,146 | 3 filed (1 with reproduction) |
| overwatch.py | 946 | 2 filed (1 with measurement) |
| escalation.py | 658 | 2 filed |
| ingest_doc.py | 517 | 2 filed |
| canon_backup.py | 398 | 2 filed |
| navtree.py | 318 | 1 filed (INFO) |
| tempus.py | 274 | read in full, nothing found |
| resync_roll.py | 212 | 1 filed |
