# PANSCRIPTUM — AUTONOMOUS RUN STATUS

*Rewritten automatically by `src/pipeline.py` after every completed unit.*
*Last update: 2026-08-22 15:53:24*

## Where the run is

| | |
|---|---|
| Current phase | **7 — shelve** |
| Units completed this run | 3,369 |
| Failures logged | 0 |

## Corpus

| | |
|---|---|
| Sources catalogued | **209/215** |
| Records with entries | 210 |
| Total entries | **56,748** |
| Sources with a ceiling nominated (phase 1) | 210/210 |
| Entries through the judgment pass (phase 2) | 56,564/56,748 |

## Phase ladder

| # | phase | state | what it does |
|---|---|---|---|
| 1 | `synthesis` | **built** | per-source power ceiling + magnitude band |
| 2 | `entrypass` | **built** | per-entry category, band, topic, grounded scale_note |
| 3 | `weave` | **built** | cross-source entity resolution + the onomasticon |
| 4 | `chain` | to build | the Chain of Defeats; Bradley-Terry theta per component |
| 5 | `cosmology` | to build | universe → multiverse → metaverse → xenoverse → hyperverse |
| 6 | `history` | to build | *The History of the Omniverse* |
| 7 | `shelve` | to build | the topical A–Z encyclopedia volumes |
| 8 | `write` | to build | volume prose |

Volumes are organised by **topic across the omniverse**, never by source IP.

The runner stops cleanly at the first unimplemented phase rather than faking it.

## Built alongside the pipeline

These run standalone and do not block the sweep.

| module | what it is |
|---|---|
| `verify_math.py` | 237 independent checks across 17 sections; recomputes, never re-calls |
| `derivation.py` | the ledger: every quantity names its parents, or the graph fails |
| `assay.py` `rigor.py` `custodes.py` | the Assay, commensuration, and the ten-Custos college |
| `tiers.py` `sevenfold.py` `grounding.py` | the cosmological tiers and the declared 1–7 shelving |
| `address_space.py` `profile.py` | the shelfmark, and the whole world in one 30-char string |
| `worldseed.py` `burgs.py` | map parameters and settlements by the rank-size rule |
| `navtree.py` `build_terminal.py` | the Registry Terminal (`output/registry_terminal.html`) |
| `audit.py` `cleanup.py` | the backscan and its repairs |
| `tells.py` `style_audit.py` | 138 machine-writing tells; Rule 7 is generated from the list |

## Files

- `state/PIPELINE_STATE.json` — resume point (atomic writes; safe to kill the process)
- `state/pipeline.log` — append-only run log
- `handoff/AUTONOMOUS_PLAN.md` — the full plan for every phase

## Restarting

```
python3 src/pipeline.py            # resumes exactly where it stopped
python3 src/pipeline.py --status   # no work, just report
```

**Run one instance only.** Two concurrent runners both write `PIPELINE_STATE.json` and the same
record files; that happened on 2026-08-21 and the records survived by luck. Check before starting:

```
powershell -Command "Get-CimInstance Win32_Process -Filter "Name='python.exe'" | Select CommandLine"
```
