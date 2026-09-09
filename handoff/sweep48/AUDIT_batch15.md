# Sweep #48 — batch 15

Modules (read in full, no sampling):

| module | lines read |
|---|---|
| src/hostcheck.py | 1636 / 1636 |
| src/escalation.py | 1432 / 1432 |
| src/chain.py | 909 / 909 |
| src/ingest_doc.py | 612 / 612 |
| src/worldseed.py | 531 / 531 |
| src/snapshot.py | 376 / 376 |
| src/wh40k.py | 350 / 350 |
| src/audit.py | 271 / 271 |

---

## FINDING 1 — MAJOR — escalation.py:878-910, escalation.py:980, health.py:97

**What is wrong.** `resume_subsystem_verdict()` (the only sanctioned way to lift a rung-4 MANAGER
stop) skips its person-at-the-CLI check whenever `_a_probe_release(name)` returns `True`:

```
escalation.py:980   if not _a_probe_release(name) and not _by_a_person_at_the_cli():
                         raise PermissionError(...)
```

`_a_probe_release` (escalation.py:878-910) has two escape hatches. The first
(`STOPPED != _REAL_STOPPED`) is safe — it only fires when `drill._esc_sandbox` has redirected the
whole ledger to a scratch directory. The second fires against the **real, live** `STOPPED.json`
and is a bare pattern match on the caller-supplied `name` string:

```
escalation.py:906-907   import health as _H
                         return bool(_H.is_selftest(str(name)))
```

`health.is_selftest` (health.py:100-103) tests `name` against `SELFTEST_SUBJECT`
(health.py:97): `re.compile(r"__drill[A-Za-z0-9_]*__")`, using `.search()` — an unanchored
**substring** match, not an equality test against the three literal drill markers the docstring
names (`__drill_rung4__`, `__drill_rung4b__`, `__drill_litter_probe__`).

**How I verified it.** Read `_a_probe_release`, `resume_subsystem_verdict` and
`health.is_selftest`/`SELFTEST_SUBJECT` in full (line numbers above, confirmed with `grep -n`).
Independently re-ran the regex in isolation (no escalation/health code executed) against sample
names:

```
payments__drill_x__            -> True
nightly-publish__drilled__     -> True
catalogue_web                  -> False
```

So any subsystem `name` that merely **contains** a substring shaped like `__drill<word>__`
anywhere in it satisfies the exemption, exactly like the three real drill markers.

**Why it matters.** `stop_subsystem`/`resume_subsystem` take an arbitrary caller-supplied `name`
string — nothing anywhere restricts subsystem names to a fixed enum, and `name` is not the
identity of the *caller*, it is a label the caller *chooses*. The whole point of this exemption's
sibling check, `_by_a_person_at_the_cli()`, is that it is deliberately hard to fake — it inspects
the call stack (`sys._getframe`) rather than trusting a value the caller supplies. This second
escape hatch does the opposite: it trusts a value the caller fully controls. Any automated caller
that names (or has ever named) a subsystem to match that pattern — by accident, by copying the
convention out of this very file's own comments, or deliberately — can call
`resume_subsystem_verdict(name, ruling, by="anything")` and lift a real MANAGER-rung stop with no
person and no CLI, which is precisely the asymmetry ("An autonomous run may STOP a subsystem;
only a person may resume one") owner ruling `ddb5eadd8934` (2026-09-08) was written to guarantee.

I could not find any current production caller of `stop_subsystem`/`resume_subsystem*` outside
`drill.py`'s own self-tests (`grep -rl "stop_subsystem(" src/*.py` -> only `drill.py`,
`escalation.py`, `health.py`), so this is not firing today — but the gate itself, not just its
callers, is the safety, and it is exploitable by construction the moment any real caller adopts
this API with a name it does not fully control (or simply reuses the documented marker).

**Proposed remedy.** Drop the name-substring branch from the *live-ledger* path entirely, or at
minimum require it to be an exact match against a short, explicit tuple of drill subject
constants (as `health.SELFTEST_SUBJECT` already enumerates them in prose) rather than a
`.search()`. The safe branch (`STOPPED != _REAL_STOPPED`) already covers every legitimate drill
call; the marker-matching branch exists only to protect probes that, for some undocumented
reason, run against the real ledger, and it should not be reachable by a name a non-drill caller
picked.

---

## FINDING 2 — MAJOR — src/ingest_doc.py (whole module)

**What is wrong.** `ingest_doc.py` writes unconditionally, with no halt check anywhere in the
module, to both of the files this project's own doctrine names as "not reconstructible from
anything else on disk":

* `register()` (ingest_doc.py:128-151) writes `data/WIKI_HOSTS.json` directly at
  ingest_doc.py:148 (`silence.write_json(HOSTS, hosts, ...)`).
* `mine()` (ingest_doc.py:260-524) merges new catalogued entities into
  `data/records/<slug>.json` — the corpus itself — at ingest_doc.py:452
  (`P.write_record_catalogue(rp, rec)`).

`grep -n "assert_clear\|import escalation" src/ingest_doc.py` returns **nothing**. The module
never imports `escalation`, never calls `assert_clear`, and is not one of the 16 modules in
`src/` that do (`allsweep.py, dashboard.py, drill.py, escalation.py, feats.py, foreman.py,
hostcheck.py, local_agent.py, overnight.py, overwatch.py, pipeline.py, publish.py, read.py,
threads.py, verify_math.py, withdraw_chapters.py`).

**How I verified it.** Read the whole module. Confirmed both write call sites and their targets.
Confirmed the "two files not reconstructible" framing against `hostcheck.py`'s own docstring
(`_assert_not_halted`, hostcheck.py:76-112) and `drill.py:9464`
(`"WIKI_HOSTS.json, which hostcheck.py itself calls one of the two files not reconstructible
from anything else on disk"`) and `canon_backup.py:1-16` (`data/records/*.json` — "217 sources...
derived from nothing" — and `data/WIKI_HOSTS.json` are the two files that module exists to
back up, as opposed to everything else in `data/` which is rebuildable). Confirmed
`pipeline.write_record_catalogue` (pipeline.py:805+) itself performs no halt check — the gate is
expected to live at the caller's entry point, which is the pattern `hostcheck.py` follows
explicitly for the identical two files. Confirmed no drill.py coverage at all:
`grep -c "ingest_doc" src/drill.py` -> `0`.

**Why it matters.** This is the exact shape `hostcheck.py`'s own docstring (hostcheck.py:76-105)
describes as the *original documented incident* about itself, before it was fixed: "This module
had ZERO references to `escalation` and was on no roster, while `--purge --go` empties `entries`
in every matching `data/records/*.json`... `--repair` and `--adopt --go` rewrite
`WIKI_HOSTS.json`, which this same file calls one of the two files confirmed not reconstructible
from anything else on disk." `ingest_doc.py` performs the same two categories of write
(repointing `WIKI_HOSTS.json`, appending to the corpus) and has never been given the equivalent
gate. If a library-wide halt is raised for exactly the reason Hard Rule -1 names as OWNER-worthy
("evidence being attributed to the wrong entity corpus-wide") — which is squarely what `mine()`
does, merging LLM-extracted entities into the corpus — `python src/ingest_doc.py --pdf ... --mine`
run by an owner or a scheduled job would proceed regardless and keep merging.

**Proposed remedy.** Add the same guard `hostcheck.py` uses, at the top of `main()` (or
individually before `register()`'s and `mine()`'s writes): `import escalation as _ESC;
_ESC.assert_clear("ingest_doc.py %s" % what)`, following the fail-closed-on-ImportError pattern
hostcheck.py:106-112 uses (not a bare `except ImportError: pass`). Add a drill.py net asserting it,
matching the two existing nets for hostcheck's `--purge --go` / `--repair` / `--adopt --go`.

---

## FINDING 3 — MINOR (stale citation) — src/worldseed.py:284, src/worldseed.py:309

Both lines cite `(the feats.py:1023 idiom)` for the "REPORTED DEAD, NOT DELETED" doctrine. The
text that idiom refers to (`# REPORTED DEAD, NOT DELETED, per house doctrine that dead code is
not automatically deletable`) is the only occurrence of that phrase in `feats.py`
(`grep -n "REPORTED DEAD" src/feats.py` -> one hit) and it now sits at **feats.py:1918**, not
1023 — an 895-line drift. `feats.py:1023` today is inside an unrelated helper
(`_SLUG_FIXES`/slug-derivation code, nothing to do with dead-code retention).

**Remedy:** update both worldseed.py citations to `feats.py:1918`.

---

## FINDING 4 — MINOR (stale citation, about my module) — overwatch.py:815, overwatch.py:1011

Not in my assigned module list, but both cite my module: `"the house exemption for console
renderers (ingest_doc.py:363)"` / `"(house exemption, ingest_doc.py:363)"`. The text establishing
that exemption — `# store them whole; the console renderers truncate at their own call sites.` —
is at **ingest_doc.py:416** today (inside the `# NO [:2000] (order baf4a18d1f1a...)` comment block
spanning ingest_doc.py:408-417), not line 363. Line 363 in the current file falls inside an
unrelated comment about the `landed_found`/`state["found"]` counters. Drift of ~53 lines.
Flagged here because the citation is about the module I was asked to verify; the fix belongs in
overwatch.py, outside this batch.

---

## FINDING 5 — QUESTION — escalation.py:409 mutation "KILLED" claim (order 58a00e909217)

Confirmed by direct inspection: line 409 of `escalation.py` —

```
409:     UNLOCKED, exactly as it did before this function existed, and the failure is noted.
```

— sits inside the multi-line docstring of `_halt_lock()` (docstring spans escalation.py:390-414),
i.e. it is prose describing the deliberate fail-open design, not executable code. A mutation
scored "KILLED" at this line cannot be evidence about the fail-open logic itself; the order's own
framing (a confirmed false kill) matches what I see. Beyond re-confirming the order: this is a
symptom of the mutation harness attributing kills by raw line number in a file whose docstrings
are hundreds of lines long and get edited/expanded often (the `_halt_lock` docstring alone runs
25 lines, and several other functions in this file carry 40-80 line docstrings). Any edit that
shifts line counts anywhere above a real mutation site will silently remap which line "owns" that
site's verdict in later runs. I'd treat any single-line mutation-report citation into
`escalation.py` as needing a source-line spot-check before acting on it, not just this one.

## FINDING 6 — QUESTION — hostcheck.py's persisted `"examples"` field vs Hard Rule 0

`probe()` (hostcheck.py:326-366) returns both `"examples": found[:5]` (hostcheck.py:363, also
:343) and an uncapped `"titles"` list. `score()` uses `"titles"` internally for the aboutness
check and then does `r.pop("titles", None)` (hostcheck.py:817) before the row is stored in
`results` and eventually written whole to `data/HOST_FITNESS.json` — so the *persisted* artifact
only ever carries a 5-title sample of which pages a host answered for, permanently. Given how
aggressively this same file documents fixing unmarked truncations elsewhere (over a dozen
"UNCUT (Hard Rule 0, ...)" comments), I can't tell whether this was considered and accepted
(it's a diagnostic sample field, not a claimed roster, and the file's real "roster" — the
catalogued entity list — is untouched by it) or simply not yet looked at. Flagging as a question
rather than a finding.

---

## What I read and found nothing wrong in

* `hostcheck.py`'s `_assert_not_halted`, `_land`, `_land_hosts` (compare-and-swap + halt-recheck
  beside the write), `score()`/`null_rate()`'s None-vs-zero handling, `purge()`'s human-only gate,
  and every write path's denied-replace reporting — all fail closed and consistently re-verified
  against their own historical incidents; I found no gap in the reasoning as written.
* `escalation.py`'s level-name/level-number coercion in `escalate()` (string, out-of-range int,
  non-integral float, NaN, inf all correctly fall to MANAGER rather than OPERATOR or OWNER);
  `_raise_halt`/`_land_halt`/`_halt_file_records` compare-and-swap and read-back-to-verify logic;
  `clear()`'s ordering of ruling-check before person-check before signature-check (each
  independently required so drill's negative probes exercise the right refusal); `_read_halt_raw`
  and `_read_stopped`'s fail-closed handling of `null`/wrong-shape/unparseable files;
  `_halt_lock`'s deliberate, well-documented fail-open (this is the one place in the module that
  intentionally does not fail closed, and the reasoning for why is sound and explicit). No
  `except: pass` or `except ImportError: pass` shapes anywhere in the module.
* `chain.py`'s harvest/index incrementality, the mutual-pair epoch adjudication in
  `adjudicate_mutuals` (unprobed vs undated vs self-split are kept genuinely distinct), and
  `write_result`/`landed()`'s denied-replace reporting. `chain.py` performs no halt check at all,
  but it writes only to `data/CHAIN.json` (a reconstructible phase artifact, rebuildable by
  re-running harvest+extract+fit) and `state/chain_harvest_idx.json` (explicitly documented as
  safe to delete and rebuild whole) — neither is one of the two non-reconstructible files, so the
  absence of a gate here is consistent with the project's own established distinction
  (`hostcheck.py`'s "measurement vs irreversible write" reasoning), unlike Finding 2.
* `ingest_doc.py`'s atomic-write discipline (`silence.write_json` throughout,
  `write_record_catalogue`'s landed-verdict handling, the resumable cursor logic, the Hard-Rule-0
  documented exemption at ingest_doc.py:408-417 itself), `record_path`'s ambiguous-match refusal,
  and `_ask`'s pool/local fallback shape-checking — all sound. The one gap is Finding 2 above.
* `worldseed.py`'s seeded-fallback provenance tagging (`_first`), band parsing/clamping with
  provenance (`unassayed`/`unparsed`/`out_of_range`/`ok`), the `limit is not None` fix, and the
  `WORLDSEEDS.json` collision reporting — all sound, aside from the stale citation in Finding 3.
* `snapshot.py`'s containment checks (`_rel`, `_safe_join`), unique-id generation, partial-capture
  refusal, and directory-aware `verify()` — all sound; this module has no non-reconstructible
  writes of its own (it only ever copies files aside) so a halt gate would not apply to it.
* `wh40k.py`'s per-axis provenance derivation and gated, atomic `WH40K_ASSAYS.json` write — sound;
  a purely derived/rebuildable artifact, consistent with no halt gate.
* `audit.py` is read-only end to end (no writes of any kind) — confirmed by inspection; no halt
  gate applies.
