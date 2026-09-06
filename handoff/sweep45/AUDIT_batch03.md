# sweep45 — batch 03 audit

`src/pipeline.py` · `src/catalogue_web.py` · `src/handbuilt.py` · `src/pick_model.py` ·
`src/coverage.py` · `src/roll.py` · `src/ledger.py` — 5,408 lines.

**Read in full, every line of all seven files.** No sampling, no skimming, no partial read.
Line counts confirmed against the files: pipeline 3,072 · catalogue_web 640 · handbuilt 516 ·
pick_model 403 · coverage 330 · roll 275 · ledger 172.

Read-and-report only. **No source file was edited.** The `DRILL_BREACH` halt was left standing
and no battery tool (`drill.py`, `verify_math.py`, `allsweep.py`, `publish.py`, `mutate.py`)
was run.

---

## The theme of this batch

The coordinator's brief said the defect fixed in `write_record` tonight — a name-keyed fold
that silently collapsed duplicate-named entries and returned `True` — was worth looking for
elsewhere, because 1,840 entries across 65 records carry a duplicated name.

It is elsewhere. **Three separate live sites in this batch treat a `name` as a per-entry
identity**, and one of them is the other half of the two-writer contract the fixed function
belongs to. Measured over `data/records/*.json` this sweep:

| | |
|---|---|
| total entries | 282,822 |
| entries carrying a name duplicated inside their own record | 1,840 |
| records affected | 65 |
| **rows a name-keyed dict collapses** (extras beyond the first of their name) | **935** |

Worst records: `dr-firestorm-s-engineering-corps.json` 125 of 425 · `all-black-ops.json` 75 of
1,470 · `adventurers-league.json` 75 of 477 · `acquisitions-incorporated.json` 60 of 356 ·
`dungeon-of-the-mad-mage.json` 47 of 388.

---

## Filed this sweep — worst first

### `b418b8b3be54` MAJOR · LOCAL · `pipeline.py:751` (`write_record_catalogue`)

**The name-keyed fold fixed in `write_record` tonight is still standing, unchanged, in its
twin.** `by = {e.get("name"): e for e in rec.get("entries") or []}` is the exact expression
order `b67dc1990af6` removed one function over, where the comment at `:1043-1052` now records
the measurement (125 of 125 residual rows duplicated-name, 0 unique). The remedy landed in one
writer and never reached the other — this tree's recorded failure shape, in the words of
`synthesis_blocks`' own docstring.

Two losses, both silent, both ending in `return _landed(tmp, path)` → `True`:

1. **A reverted judgment.** When the fresh cast holds *k* > 1 entries called N, the
   comprehension keeps the last; every disk entry called N folds its `MERGED_ENTRY_FIELDS`
   judgments onto that one survivor, and the other *k*−1 emerge carrying no pipeline judgment
   at all — including `excluded`, which is the reverted-exclusion cycle `MERGED_ENTRY_FIELDS`'
   own comment at `:596-605` says was closed after the 149-entry incident.
2. **A shrunk cast.** Only the `if se is None:` arm appends a disk row. A disk row whose name
   *is* in `by` is folded and never appended, so *m* disk entries called N become *k*. The
   docstring at `:718-720` promises the opposite in as many words — *"disk-only entries are
   kept — a merge never shrinks a cast."* That sentence is now false for every duplicated name.

The twin's remedy does **not** transfer: `write_record` could pair by order within the name
group because `phase_entrypass` never reorders. A wiki re-fetch does. The order states the
honest LOCAL minimum (never drop a disk row; count and log every ambiguous group, as
`unpaired_disk`/`unpaired_mem` at `:1104` already does; leave the fold off ambiguous groups
rather than guessing) and leaves the stored-identity question where `:1061-1063` already
leaves it — with the owner.

### `8bd76479c64e` MAJOR · LOCAL · `catalogue_web.py:423` and `:230`

**The fetch de-duplication key deletes the part of a wiki title that exists to say two pages
are different things, and the drop is counted nowhere.**
`re.sub(r"[^a-z0-9]", "", re.sub(r"\([^)]*\)", "", title.lower()))` strips the *disambiguator*
— the one field whose entire job is to distinguish two distinct entities sharing a base name —
then skips any title whose key is already in `seen`.

Measured over the 272,004 `mode="web"` entries: 56,509 carry a parenthetical, and **430 pairs
on disk carry *different* disambiguators and produce identical keys**. Live examples:
`Narrator (Battlefield 1)` / `Narrator (Battlefield V)`; `Allies (World War I)` /
`Allies (World War II)`; `Coral Sea (Battlefield 1942)` / `Coral Sea (Battlefield 1943)`;
`Susan Strong (Kara)` / `Susan Strong (character)`. They coexist on disk only because they were
catalogued in separate passes and `write_record_catalogue` re-appended the disk-only side —
inside any single `catalogue()` call, `seen` is one set for the whole source and one of each
pair is dropped, never fetched, never counted.

What makes this Hard Rule 0 rather than tuning: the module counts and **declares** its other
loss. `no_text` is tallied at `:436` and named in the record's own provenance at `:478-484`,
with an explicit statement that it is an upper bound. The dedup drop gets none of that — the
record still says "Transcribed from &lt;wiki&gt; via the MediaWiki API" with no qualifier. The
dedup is often *right* (`The Lich (character)` / `The Lich` really is one entity), which is
exactly why the silence is the defect and not the collapsing: nobody can separate the correct
merges from the 430 wrong ones without the drop list.

### `d17a7463a5fd` MAJOR · LOCAL · `pipeline.py:2609-2613` (`phase_shelve`), reported at `:2623`

`shelved[f"{src}::{name}"] = {...}` while walking every entry of every record. The second and
later entries of a name overwrite the first, so only the last gets a spine code, a tier, a rank
and a shelfmark in `data/SHELVES.json` — **935 measured rows have no shelf entry at all**, with
no key and no marker.

And the report cannot show it: `:2623` logs `%d entries placed` from `len(shelved)` — the
post-collapse figure, arithmetically consistent with itself. `gate_done` then closes phase 7 on
a land verdict that is `True`, because nothing failed. The artifact is derived and re-derivable,
so no repair pass is needed — only a writer that stops discarding, and a log line that reports
entries *walked* alongside rows *written*.

### `4c53346eb9ba` INFO · LOCAL · `coverage.py:224-235` (`measure`)

`state_of(host, e["name"])` resolves through a per-`(host, name)` cache path, so two entries in
one record sharing a name read the **same** evidence file and `feats += nf` adds it twice. The
per-source `feats` figure in `COVERAGE.json` and the "total feats on record" headline are
therefore sums over catalogue rows, not over distinct mined evidence. Bounded by 935 entries
(0.33% of the corpus) — hence INFO. It is also arguably *correct*, which is the point: the two
readings are indistinguishable in the number as printed, and one of them should be declared.

---

## Corroborated, not refiled

Verified against source this sweep and still standing:

| order | site | note |
|---|---|---|
| `19c507a16430` | `pipeline.py` stored cuts | Confirmed at current lines `:1494` evidence[:600], `:1495` rationale[:900], `:1921` scale_note[:500], `:1923` scale_note_rejected[:500], `:1970` topic_rejected[:120]. **New site to add:** `:1981` `subroom_rejected = sub[:120]` — `subroom` was added 2026-09-01, after that order was filed, and inherited the same unmarked cut. |
| `7716ac4884cc` | stale `file:line` cross-refs in `pipeline.py` | Confirmed, and **the site list is short by five.** Each checked against the current file: `:604` cites `:1552` for where `phase_entrypass` writes `topic_rejected` (actually `:1970`; `:1552` is prompt prose). `:618` cites `:1532` and `:1573` for the two pops (actually `:1925` and `:1966`). `:628-630` cites `:1718`, `:1707` and `:554` (actually `:1977`, `:1966`, `:606`). `:2339` cites `:1948` and `:2054` for the absent-vs-corrupt ruling in phases 6 and 7 (actually `~:2433` and `~:2537`). Worth widening that order rather than opening a second one. |
| `fe99e57e1993` | Hard Rule 0 omnibus | Already names `catalogue_web.py:557,344`. Both confirmed live. |
| `109b2def0beb` | `coverage.py` console cuts | Confirmed at current lines `:270` `source[:58]`, `:282` and `:297` `source[:44]`. |
| `732f68f640cf` | `coverage --show-best` asymmetry | Partly addressed by order `89fc2eaf23f1` (0 now means all, and the cut is announced). The default-10-vs-unlimited asymmetry itself still stands. |
| `60cb4e0e3595` | `roll.update_rows` `if ch:` | Confirmed at `:186`. |
| `2f38b3e5258d`, `e038ec1759a9`, `ae7b56cd43d0`, `85a6b7b9e2c8` | `pick_model` VRAM/MoE cluster | All four confirmed. On `85a6b7b9e2c8` specifically: `MOE_MARKERS` is read only by `is_moe()`, which is read only by `fit_note()` to pick the word "MoE" in a warning string. The disqualification is `resident()`, which is purely size-based. The comment at `:82-83` claiming MoE is "STILL DISQUALIFYING" describes a gate that does not exist. |
| `4ed4041c3b78` | falsy-zero guards | `catalogue_web.py:545` (`if args.limit:`) confirmed. |
| `1b6a752786b9`, `1e45fae97848`, `26b0e8cb30a1`, `9e300162f4df`, `47067a8f0ad5`, `b248f8f706d3`, `f3d1f95b682b` | `catalogue_web` cluster | All confirmed live. |
| `1a9c237dda4d`, `3fb9fc6b9999` | `ledger.py` unwired | Confirmed, and **there is now a third dead symbol**: `currency_status()` (`:87-103`) has **zero** callers anywhere — not `src/`, not `verify_math.py`, not `derivation.py`. It was added by order `e9167885aef6` specifically so a caller could distinguish an unlisted currency from a deliberately non-convertible one, and no such caller was ever written. Covered by `3fb9fc6b9999` (the whole module is unwired), so not refiled. |
| `9f9f19d77791` | `handbuilt.py:166-168` "four times wider" | **Appears fixed in the tree.** The docstring now reads "±0.19 … a ratio of ~1.27, not 4" and names the measurement. Closable on inspection. |

---

## Checked and clean — reported because absence of a finding is a finding

* **No non-atomic write to shared state anywhere in this batch.** Every writer was traced:
  `pipeline.save_state`, `write_record`, `write_record_catalogue`, `land_json`,
  `update_handoff` (all pid+thread temp → `silence.replace_retry`); `_metric` via
  `silence.append_line`; `catalogue_web.save_roll` → `roll.update_rows` → `roll.mutate`
  (compare-and-swap on `replace_if_unchanged`); `handbuilt`, `coverage._so_save`,
  `coverage.main` and `roll.exclude` via `silence.write_json`; `pick_model.save_config`
  (pid+thread temp → `replace_retry`). **No bare `open(path, "w") + json.dump` to a shared
  file survives in these seven modules.**
* **No un-noted bare `except Exception:`.** Every swallow either calls `silence.note`, calls
  `log` (which prints *and* lands in `state/pipeline.log`), or carries an explicit
  `"silence-exempt: …"` marker with a stated reason. The one handler that reports through `log`
  alone rather than `silence.note` is `update_handoff`'s outer catch at `pipeline.py:2176`, and
  it prints a real traceback — recorded, so not filed.
* **Every landing verdict in this batch is gated.** `_landed`, `gate_done`, `_chain_landed`,
  `save_roll`'s call site, `save_config`'s call site, `coverage.main`'s exit code and
  `handbuilt.main`'s exit code all consume the boolean rather than discarding it.

## Judged deliberate design, and deliberately not filed

* `pipeline.py:1698-1705` — `_SCALE_PATTERNS` / `_SCALE_EVIDENCE` are dead by design. The
  comment says so explicitly and explains that they are kept as the *shape of the rejected
  approach*, not as an alternative someone could wire back in. A liveness scan will flag them;
  it should be suppressed rather than obeyed.
* `pipeline.py:2735-2755` — phase 8's missing third arm. The run40 order `97d5b256fbdc` reading
  is correct as far as it goes, the `elif names:` arm was added and reverted the same shift
  because `drill._write_phase_stays_open_when_everything_refuses` requires the vacuous case to
  close. Already reopened as an owner question (`c391a1f77e42`). Left alone.
* `roll.in_scope` failing **open** on an unreadable roll, against house habit. The docstring
  argues it correctly: an unreadable roll silently excluding the entire library would be a fault
  that looks exactly like a completed run, which is the worse of the two failures.
* `roll.load()` returning `[]` for both an empty roll and an unreadable one. It does call
  `silence.note`, and the one caller that could act on the difference (`exclude`) *raises*
  rather than writing. The misdiagnosis is cosmetic — `main()` would print "0 source(s)" — and
  the write is refused either way. Noted, not filed.
* `catalogue_web`'s decision to keep going after a failed sub-category in `catalogue_composite`
  while the single-wiki path lets the exception propagate. The asymmetry is deliberate, argued
  at `:256-264`, and the failures are named in the provenance.
* `handbuilt.py` — read in full and clean. No silent drop, no unmarked cut (the citation view
  wraps rather than truncating, per order `9c6a23625865`), the artifact lands before anything
  is printed so a console encoding cannot cost the file, and `main()` returns a real exit code.
