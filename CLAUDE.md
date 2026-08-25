# The Panscriptum — Library of Babel Book-Generation Kit

You are Claude Code, running locally with real filesystem and shell access on the owner's
machine — including their local Ollama installation. This is the piece of the pipeline that
could NOT be done from the cloud session that built this kit, because that session cannot
reach `localhost:11434`. That's why you're here.

**Read this document fully before running anything.** There is more existing infrastructure in
this kit than you might expect on first glance — read `reference/keystone_volumes/` before you
assume you're starting from a blank page, because you are not.

## What already exists (read this first)

The owner has been building "The Panscriptum" across multiple sessions. This is NOT a fresh
concept you're inventing tooling for — it has a complete, already-written charter and four
finished keystone volumes:

- `reference/keystone_volumes/00_MASTER_CHARTER.md` — the master plan. Defines the shelving
  hierarchy (Collection → Set → Series → Volume), the 17-rung Ladder of Being (Part Two), the
  M0–M10 Magnitude scale and the full Custodial Assay decimal-scoring method (Part Three), the
  Volume Template (Part Six), the Entry Template (Part Seven, with the Four Hands marginalia
  system), a worked sample entry (Part Eight), the production roadmap (Part Nine), and —
  critically — **the Acquisitions Index**, an appendix mapping most sources to their real home
  spine code (e.g. `One Piece → II.A.3`, `Marvel → II.D.1`). **This is the actual addressing
  system for the project. Don't invent a different one.**
- `reference/keystone_volumes/0-1_CUSTODIANS_VADE_MECUM.md` — Vol. 0.1, "How to Read the
  Library," already written in full, demonstrating the house voice.
- `reference/keystone_volumes/X2_MENSURA_FUNDAMENTA.md` — Vol. X.2, the mathematical
  foundation of the Assay method, already written.
- `reference/keystone_volumes/I9_THE_CONCORDANCE.md` — Vol. I.9, the political geography of
  the omniverse, already written.
- `reference/keystone_volumes/VIII_MASTER_CHRONICLE.md` — the Chronica Annex's event spine,
  already written (this will need revision after the owner's Step 4/5 entanglement work — see
  below).
- `reference/keystone_volumes/CATALOG_A_KEYSTONE_COSMOGRAPHIA_WEAVE.md` and `CATALOG_B_WORLDS.md`
  — the card-catalog data (human-readable seed for the Registry Terminal, see below).
- `registry_terminal/` — a working HTML card-catalog application (`PANSCRIPTUM_TERMINAL.html`
  + supporting `.js` data files) that the charter's own Part Nine calls "the reference
  implementation" of the in-fiction registry terminal. **This already exists and already
  displays catalog cards.** Read it before assuming you need to build a new viewer — you may
  just need to feed it more data.

Per the charter's own Part Nine production roadmap, Phase 1 (the keystone volumes above) is
done. You are picking up at Phase 2/3: writing the actual per-source Worlds volumes
(Collection II and beyond), which is what this kit's pipeline automates using your local model.

## What this kit adds on top of that

A separate cloud Claude session has been running Step 1 of the owner's plan: cataloguing every
named Person, Faction, Place, Vessel/Thing, Event, Media item, and Power/System for each of the
~215 sources on the Acquisitions Roll, grounded in real research. That structured data lives in
`data/`. **Your job is turning that data into the actual prose volumes**, addressed against the
charter's real spine codes, using your local Ollama model so the cloud session's token budget
never touches prose generation.

## HARD RULE -1 — THE CHAIN OF COMMAND, AND THE HALT AT THE TOP (owner directive, 2026-08-25)

**Read this before Hard Rule 0, because it is the rule about what happens when a rule is
broken.** On 2026-08-25 the library wrote 145 chapters it should not have. The uncomfortable
finding was that **nothing failed**. Every component did what it was told. What was missing was
a chain: nobody whose job it was to notice had the authority to stop anything, and nobody with
authority to stop things was told. The gate that should have prevented it had been DELETED
months-of-work earlier by an autonomous run acting on a fair reading of a code smell.

So the library now has an escalation chain, in `src/escalation.py`, and it binds every actor
here — human, scheduled run, or local model:

    0  JANITOR      record it. No authority to stop anything. On duty at all hours.
    1  OPERATOR     refuse THIS unit of work — one block, one entity, one call.
    2  SUPERVISOR   refuse THIS SOURCE. Its area closes; the rest of the library keeps running.
    3  SAFETY       fail the BATTERY. No run may claim success while this stands.
    4  MANAGER      stop the SUBSYSTEM.
    5  OWNER        HALT EVERYTHING. Nothing starts until a person rules on it.

**Every source is its own area of the park.** A fault in one source must never close the whole
library — `Song of Syx` having nothing cited is a SUPERVISOR event, not an OWNER one. Escalating
everything is the same failure as escalating nothing, because an alarm that always sounds is
furniture.

**The three properties every safety here must have**, and they are not negotiable:

  * **INDEPENDENT** — no two layers may share a failure mode. When `overnight.py` reimplemented
    the prose gate with `bool()` instead of the strict check, `prose_enabled: "false"` opened it,
    and two layers enforcing *different* invariants is not defence in depth, it is one layer and
    a decoy.
  * **FAIL CLOSED** — every layer answers "I don't know" with STOP. An unreadable config, a
    missing COVERAGE.json, an unparseable block, a corrupt halt file: all refuse. Silence must
    never authorise anything.
  * **PROVEN** — `python src/drill.py` attacks all 57 nets and reports HELD or BREACHED for each.
    A guard nobody has watched *refuse* is a guard nobody has evidence about. The supervisor runs
    this every cycle, before any stage starts, and a BREACHED net halts the library by itself.

**You may RAISE a halt. You may not LIFT one.** `escalation.clear()` demands a written ruling and
is asserted by `verify_math` to have no caller anywhere in `src/`. That asymmetry is the whole
point: the last incident was an automated agent removing a safety it had concluded was
unnecessary.

**And the standing lesson this all serves: a check that cannot fail looks exactly like a check
that passed.** `python src/liveness.py` finds the mechanical shapes of that — dead functions,
tautological comparisons, guards on undefined names. `drill.py` ratchets its count so a new one
cannot appear silently.

## HARD RULE 0 — NO CAPS. EVER. (owner directive, 2026-08-22)

**Every IP and every reference is MANDATORILY UNCAPPED.** No limit, no cap, no sample, no
"top N", no truncation of a roster, a page list, a chunk list, or an entry list. If a wiki
lists 40,000 characters, the library takes 40,000 characters.

This is not a preference about thoroughness. A cap on an ordered listing is not a sample, it is
a TRUNCATION, and it silently decides that everything past the cutoff does not exist:

* `roster(limit=600)` returned Dragon Ball A-through-G. **Goku fell outside the window.**
* `roster(limit=6000)` on DC returned Abin Sur, Ace, Adolf Hitler. **Superman, Wally West and
  Wonder Woman fell outside the window.**
* `cap=250` took the alphabetical head of every missing-cast repair.
* `cap_chunks=12` decided on an entity's behalf that the rest of its own pages did not count.

Every one of those looked like a completed job. That is the whole danger: a cap does not fail,
it returns a smaller universe wearing the same shape as the real one.

Ranking is still allowed and is encouraged — order by article size or evidence density so the
richest material lands first if a run is interrupted. **Ranking then truncating is not.**

If something is genuinely too slow, the answer is more workers, more providers, or more time.
It is never a smaller universe.

## Hard rules

1. **Don't invent facts.** Every generated entry is prose dressing on top of the JSON records.
   The Entry Template and style contract in `prompts/` already enforce this — don't loosen it.
2. **Don't invent addresses.** `src/address.py` looks up real spine codes from
   `data/CHARTER_SPINE_CODES.json` (parsed from the charter's own Acquisitions Index). About
   half the current roll (~110 of 215 sources) isn't in that appendix yet — these are sources
   the owner added to the Acquisitions Roll AFTER the charter's appendix was last written
   (League of Legends, the big Nintendo/anime batch, the entire D&D "Folder" of official books
   and third-party creators, etc.). `manifest_builder.py` skips these by default and writes
   `output/index/unassigned_sources.md`. **Extending the Acquisitions Index is real curatorial
   work** — where a source belongs in the Collection/Set structure is a judgment call the
   owner made deliberately for the other ~105 entries. Either propose additions to the owner
   for sign-off, or use `--include-unassigned` to generate books under clearly-marked
   provisional codes (`UNSORTED.<Category>.PROVISIONAL`) as a stopgap, never as the final
   shelving.
3. **Don't fake the Assay decimals.** Part Three's Custodial Assay (𝔄 M3.52 ± 0.12-style
   scores) requires scoring eight power measures against cited feats — a real worksheet
   process, not something to rubber-stamp per entry. The prompts deliberately ask for
   band-only Magnitude (`M4`, not `𝔄 M4.31 ± 0.30`) for exactly this reason. If the owner wants
   full Assay scoring later, that's its own pass against Part Three's method, likely worth its
   own subagent/workflow rather than folding into prose generation.
4. **Don't invent Shelfmarks.** The Ladder-of-Being address for an individual entity (which
   galaxy, which universe) requires real classification research per entity that hasn't been
   done. `address.py` emits an honest `Ω › ? › ? › ...` placeholder using the charter's own `?`
   convention. Leave it as-is until that research exists.
5. **Threads stay pending.** The owner's Step 4 (near-exhaustive cross-verse entanglement)
   hasn't happened yet. Every generated entry's ⌁ Threads section should say so, not invent
   cross-franchise connections — that's explicitly enforced in `prompts/system_style.txt`.
6. **Pilot before you scale.** Run `--pilot 3` first, read the output, adjust
   `prompts/system_style.txt` if the voice needs work, THEN scale up.
7. **Report progress.** Local generation of hundreds of chapters takes a while. Don't go quiet
   for hours — `generate.py`'s progress bar and periodic catalog saves are there so you can
   check in.

## Setup

```bash
cd panscriptum-library-kit
# ON THIS MACHINE: use miniconda's python directly (C:/Users/imarl/miniconda3/python.exe).
# The bare `py` launcher and a fresh venv both hit Norton's TLS interception on pip
# installs; the miniconda env already has requirements.txt plus pyflakes (the sweep's
# LINT tier depends on it). The venv instructions below are for OTHER machines.
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

ollama serve   # if not already running
python3 src/pick_model.py --write
```

`pick_model.py` queries your actual installed Ollama models and picks the best one for
long-form, fact-grounded prose — don't just trust the hardcoded default in `config.yaml`,
which is only a fallback. It ranks by model family (instruction-tuned families known to be
solid at this kind of task, weighted ahead of raw size) and writes the winner into
`config.yaml` with `--write`. If nothing good is installed, it prints `ollama pull` suggestions
rather than silently settling — check with the owner before pulling anything large.

## Pilot, then scale

```bash
python3 src/manifest_builder.py --pilot 3
python3 src/generate.py --manifest output/index/manifest.pilot.json
```

Read `output/raw/`. Show the owner. Iterate on `prompts/system_style.txt` for voice (it's the
one file that controls tone). Then:

```bash
python3 src/manifest_builder.py            # full manifest, spine-code-assigned sources only
python3 src/generate.py --manifest output/index/manifest.json
```

Check `output/index/unassigned_sources.md` and handle it per Hard Rule 2 above before deciding
whether those ~110 sources get generated at all yet.

`generate.py` is resumable (checks `output/index/catalog.json`, skips anything already
generated under the current model/seed/prompt-version/**content** recipe) — safe to Ctrl-C and
restart, or re-run after the cloud session hands you a refreshed `data/`. The recipe hash
includes a hash of the actual source data per job (`manifest_builder.py`'s `content_hash`), not
just the address — so if a source's underlying facts changed since the last generation (e.g. it
went from a partial to a full research pass, or got new entries), that job is correctly flagged
stale and regenerated rather than silently skipped. `generate.py` prints how many pending jobs
are stale-vs-new each run so you can see this happening.

**On data freshness generally:** `data/` is a point-in-time snapshot, not a live sync — the
cloud session keeps cataloguing after this kit is handed off, and there is no automatic channel
back to it. Don't run a full 215-source generation pass against a `data/` snapshot you know is
mid-flight (check `SWEEP_ROLL.json` for `entry_count: 0` sources and the timestamp the owner
gives you it was exported). Pilot testing on a handful of already-solid sources is fine anytime;
hold the full run until the owner confirms cataloguing (including the ~110 unassigned-spine-code
sources and any in-flight re-sweeps) is actually settled, then ask for one final refreshed
`data/` snapshot to generate the real library from.

## Feeding the Registry Terminal

Part Nine of the charter says every volume's card is meant to be encoded as data inside
`registry_terminal/PANSCRIPTUM_TERMINAL.html` (or its supporting `.js` files — look at
`conc.js`, `d0.js` through `d6.js`, `names.js`, `lex.js` to understand the existing data shape
before writing to it). Once you have real generated volumes in `output/`, look at whether the
terminal's existing card format can be extended to link to or embed them, rather than building
a second, disconnected viewer. This wasn't wired up as part of this kit — it's flagged here as
the natural next integration step, not done for you.

## Querying what's generated

```bash
python3 src/catalog.py stats
python3 src/catalog.py search "One Piece"
python3 src/catalog.py read "II.A.3/Persons#1-30"
```

## When you're done with a batch

Summarize for the owner: chapters generated, wall-clock time, any failures
(`output/index/failures.json`), current coverage (`catalog.py stats`), and the state of the
unassigned-sources question. Don't just go quiet.
