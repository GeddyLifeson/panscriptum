# The Panscriptum — a Library of Babel that catalogues fiction itself

An autonomous pipeline that reads the wikis of ~210 fictional universes, catalogues every named
person, faction, place, thing, event and power in them — **uncapped, by hard rule** — and writes
the library's volumes in the house voice of a fictional custodial order, complete with each
entity's **Custodial Assay**: a measured, cited, interval-carrying power magnitude (`𝔄 M7.44 ±
0.06`) computed against the project's own published charter.

The point is not the prose and not the numbers. The point is the **automation**: the owner's
standing brief is that the person is not the instrument. The system catalogues, mines, assays,
audits, repairs and publishes itself, around the clock, on one Windows machine with a 10GB GPU
and a pool of free-tier cloud models.

## The shape of it

```
wikis (fandom.com, wikipedia, +70 adopted hosts)
   │  catalogue_web.py    every named thing, no caps ever (85,000+ entities, 210 sources)
   │  sweep.py / feats.py the per-entity evidence mine: verbatim sentences, by power axis
   ▼
magnitude.py              the Custodial Assay — anchor band + 11 weighted axes, every citation
   │                      verified VERBATIM against the entity's own pages; oversized evidence
   │                      split per-axis, never truncated; epoch-mandatory sources refuse
   │                      unstamped sheets; a fiction's own scope clamps its inhabitants
   ▼
pipeline.py               phases 1-9: synthesis, entry bands, prose volumes (local Ollama)
   ▼
publish.py                scrubbed export → GitHub, continuously
```

Around that chain, a supervision stack that runs unattended:

- **standards.py** — 36 numeric floors defining what "working" means (calls/hour, coverage vs
  the wikis' own counts, job freshness, *the automation reproduces the charter*…). A miss is a
  work order, not a log line.
- **foreman.py** — reads the work orders and dispatches the repair: restart the reader, rerun
  the catalogue, reprove the pool, run the daily charter regression. Bounded, guarded, and
  forbidden from shooting the supervisor.
- **overnight.py / autostart.py** — supervisor + watchdog, one instance of each job, restarts
  from the Windows Startup folder, no console windows.
- **overwatch.py / allsweep.py** — code-reads-the-code audits: import battery, pyflakes on
  every module, cross-subsystem reconciliation (including "no entry may out-band its own
  source's ceiling"), corrupt-file scan.
- **verify_math.py** — 267 checks proving the assay's arithmetic *and its routing*: the split
  gate, the epoch mandate, the ceiling clamp, all five transport paths under a mocked model.
- **cascade_bridge.py** — the router over ~40 free-tier cloud buckets: proof-ranked, rotating,
  self-benching, with an opt-in capped paid burst lane. Per-call metrics land in
  `state/model_metrics.jsonl` for both the cloud and local lanes.

## The rules that make it honest

1. **NO CAPS. EVER.** A cap on an ordered listing is a truncation, and a truncation silently
   decides everything past the cutoff does not exist. If a wiki lists 40,000 characters, the
   library takes 40,000. Ranking is allowed; ranking-then-truncating is not. Too slow means
   more workers or more time, never a smaller universe.
2. **No worksheet, no number.** An Assay decimal exists only when cited feats survive the
   verbatim gate; otherwise the entity carries a band, or nothing. Deferral is always legal;
   invention never is.
3. **Magnitude is capacity to decide outcomes at scale.** For a person: who would win. For an
   equipable: the delta it grants its possessor. For anything else: its effect within what it
   can interact with. Travel is Vector, never the anchor.
4. **Epochs are inputs.** Goku is a different subject at different points in his own story —
   and for sources where history splits power classes (the Mending in MTG, the Sundering in
   the Realms), an unstamped sheet is refused outright.
5. **The instrument is tested against its own charter.** The six assays the charter publishes
   re-run end-to-end through the live automation daily; drift is a red standard with a
   dispatched remedy, not a discovery someone makes later.

## Running it

On the owner's machine the stack self-starts; nothing below is needed day-to-day.

```
python src/overnight.py            # supervisor: starts/watches every job
python src/magnitude.py --calibrate   # the charter regression, on demand
python src/magnitude.py --one <host> "<entity>"
python src/allsweep.py             # the full audit battery
python src/verify_math.py          # 267 checks, no network needed
python src/dashboard.py            # the instrument panel (localhost)
```

`config.yaml` holds the Ollama connection; `pick_model.py --write` selects the best installed
local model. Cloud transport needs a Cascade install with its own key file — absent that,
everything falls back to the local model and the pipeline still runs, slower.

## Where things live

- `reference/keystone_volumes/` — the master charter (the shelving system, the Ladder of
  Being, the Assay method) and four finished keystone volumes. The project's constitution.
- `data/` — the catalogue: per-source records, the character sweep, mined evidence,
  `ASSAYS.json` (multi-epoch accessions keyed `host|name@epoch`), scope ceilings,
  completeness audits.
- `handoff/HANDOFF.md` — the living engineering history, updated daily; the audits beside it
  are line-by-line code reviews of the whole tree.
- `FOR_OWNER.md` — regenerated each round: what the automation wants a human to rule on.
- `src/` — 86 modules, every one importable, linted on every sweep.

The prose volumes land in `output/`; the registry-terminal viewer in `registry_terminal/`
renders the card catalogue.
