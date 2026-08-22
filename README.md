# Panscriptum — Library of Babel Book-Generation Kit

**Give this whole folder to a local Claude Code session running on your machine.** Its own
`CLAUDE.md` is written as the briefing document — Claude Code will pick it up automatically.
Read `CLAUDE.md` before running anything; there's more already built (a full charter, four
finished keystone volumes, a working registry-terminal viewer app) than a first glance at
`src/` and `data/` would suggest.

## Why this exists

The cloud session that built this kit can't reach your local Ollama install, so the actual
prose-generation step has to run where Ollama does — on your machine, via Claude Code.

## What's in here

- `reference/keystone_volumes/` — the master charter (shelving system, Magnitude scale, Entry
  and Volume templates, and the real spine-code index for most sources) plus four already-
  written keystone volumes and the card-catalog source files.
- `reference/pipeline_tooling/` — the cloud-side cataloguing scripts, for context on how
  `data/` was produced.
- `registry_terminal/` — an existing, working HTML card-catalog viewer app.
- `data/` — a snapshot of everything catalogued so far: 215 sources, structured facts (named
  people, factions, places, items, events, media, powers), plus the parsed real spine-code
  lookup (`CHARTER_SPINE_CODES.json`).
- `src/` — the pipeline: spine-code-aware addressing, manifest builder, local-model
  auto-selection, the Ollama runner, compression, catalog query tool.
- `prompts/` — the Entry Template / Volume Template prompts and the house-style guide, pulled
  directly from the master charter's own format (Parts Six and Seven).
- `config.yaml` — Ollama connection, chunking size. Model is picked automatically (see below),
  not hand-set.
- `output/` — where generated books land (empty until you run something).

## Quick start

```
cd panscriptum-library-kit
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

ollama serve                             # if not already running
python3 src/pick_model.py --write        # picks the best model you actually have installed
python3 src/manifest_builder.py --pilot 3
python3 src/generate.py --manifest output/index/manifest.pilot.json
python3 src/catalog.py stats
```

Then read `CLAUDE.md` for the full picture: the real addressing system, what's already built,
known gaps (about half the roll has no official shelf code yet — see
`output/index/unassigned_sources.md` after your first manifest build), and what to do once the
pilot looks good.

## A note on the data snapshot

`data/` is current as of when this kit was built. About 100 of the 215 sources still show
`entry_count: 0` in `data/SWEEP_ROLL.json` — mid-re-sweep on the cloud side after a session-
limit hiccup zeroed out a batch of them. `manifest_builder.py` skips anything with zero
entries automatically. Ask the owner for a refreshed `data/` folder periodically, or re-point
`config.yaml`'s data paths at the live `panscriptum/sweep/` directory if you ever have access
to both environments at once.
