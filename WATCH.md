# OVERWATCH

round 71  ·  last run 2026-08-24 17:00

## Structure

- modules that will not import: **0**
- files that will not parse: **0** of 64,919 inspected
- catalogued sources with no host: **20** Clockwork Angels (Rush), Curious DM Investigations (the Sharkin), Dr. Firestorm'
- on the roll but never catalogued: **6** HAWX, Heaven's Lost Property, Lost Mines of Phandelver, Twilight Imperium, major

## What the model found in the code

**10 open** (1 high). Newest first.

- **build_terminal.py** `view.w` — [HIGH] The view width is set to the maximum of the SVG's width and height scaled by the aspect ratio, but the code uses `view.w = Math.max(b.width, b.height * ar) * 1.07;` which incorrect
  - says: The view width is adjusted based on the SVG's actual bounding box dimensions after drawing.
- **endpoint.py** `source_pages` — [MEDIUM] endpoint.py:334
  - says: endpoint.py:source_pages
- **dashboard.py** `metrics` — [MEDIUM] Returns a list of metrics per tag, aggregating data from the model_metrics.jsonl file, but the code does not actually process the data as described in the docstring. The docstring 
  - says: Per-tag latency and outcome from state/model_metrics.jsonl -- the observability baseline. Local rows (pipeline.ask) carry token counts and tps from Ollama's own
- **catalogue_web.py** `write_record_catalogue` — [MEDIUM] returns whether the rename was successful
  - says: returns whether the rename LANDED
- **catalogue_web.py** `ws.rank_by_size` — [MEDIUM] truncates at top=None
  - says: rank, never truncate
- **hostcheck.py** `add` — [MEDIUM] Adds a host to the grounded list if speculative is False, but the function is called with speculative=True for some cases, which is not handled correctly
  - says: Adds a host to either the speculative or grounded list
- **feats.py** `roll` — [MEDIUM] restrict the roll to sources containing this string
  - says: mine the whole corpus
- **rigor.py** `p_point` — [MEDIUM] p_point is computed as 1.0 - math.exp(-(10.0 ** log10_median)), which is P evaluated at the mean of lambda, but the comment claims this is the 'point-estimate column' and warns it 
  - says: the point-estimate column is the one to distrust; it is P evaluated at the mean, not the mean of P
- **build_terminal.py** `bindStage` — [MEDIUM] The `pointermove` handler uses `stage.getBoundingClientRect()` to compute scale, but if the stage is not yet rendered or has collapsed dimensions (e.g., width/height < 2), it retur
  - says: The stage event listeners for wheel and pointermove are bound to enable zoom and pan, with proper handling of pointer events.
- **build_terminal.py** `srFit` — [MEDIUM] The variable srFit is computed using fitIn with the maximum length of the source names, the radius sr, and a font size of 46, but this value is never used. Instead, the code uses s
  - says: The variable srFit is computed using fitIn with the maximum length of the source names, the radius sr, and a font size of 46, to determine how much text fits in

---

Written by `src/overwatch.py`. Structure is checked every round; the model reads modules that changed first, then whichever has gone longest unread. A finding stays open until the file it points at changes.
