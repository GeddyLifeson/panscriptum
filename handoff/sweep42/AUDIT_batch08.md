# sweep42 batch 8 audit

Modules read in full: `src/magnitude.py`, `src/chain.py`, `src/catalogue_web.py`,
`src/handbuilt.py`, `src/backfill.py`, `src/navtree.py`, `src/entity_match.py`, `src/halo.py`.

General note: all eight modules are unusually heavily self-audited already — most carry
paragraph-length comments citing prior "order <hash>" fixes for exactly the classes of defect
this sweep looks for (caps, swallowed exceptions, truncated persisted strings). The findings
below are the residue that survived that process, not first-pass bugs.

---

## CONFIRMED DEFECTS

### 1. `src/catalogue_web.py:579-580` — exception swallowed with no `silence.note` tag

```python
        try:
            record, note = catalogue(name)
        except Exception as e:
            record, note = None, f"error: {type(e).__name__} {str(e)[:60]}"
```

Every other broad `except Exception` in this file (and in all 7 other modules in this batch)
either calls `silence.note("module.py:tag")` or carries an explicit `_ = "silence-exempt: ..."`
marker — `silence.py`'s own `audit()` walks the whole tree looking for exactly this and treats an
untagged handler as "unobserved". This one has neither. Functionally the source is still retried
next run (`entry_count` stays 0), so nothing is lost permanently, but the failure is invisible to
the project's own swallowed-exception inventory, and the error text is separately capped to 60
characters in the same statement (console-only consequence, since `record` is `None` and nothing
downstream persists it).

Confidence: high that this is an inconsistency with the codebase's own enforced convention;
medium on how much it matters in practice (the source is still correctly requeued).

### 2. `src/magnitude.py:1523` — persisted regression row truncates its own diagnostic reason

```python
            row.update({"status": r.get("status") or "NO_SCORE",
                        "reason": (r.get("reason") or "band only")[:120], "consistent": None})
            rows.append(row)
            _land(rows, False)
```

`_land()` writes `rows` straight into `data/CHARTER_REGRESSION.json` (via `silence.write_json`).
This is a written/persisted string sliced to 120 characters with no marker of how much was cut —
the exact shape Hard Rule 0 names ("`[:N]` on a printed/written string ... is a FINDING"). The
same file fixes an analogous cut nine lines below at print time (`order 01df9304f918`, "the
refusal ... was printed cut to 240 characters ... Printed whole") but the persisted `row["reason"]`
above was left capped.

Confidence: high that this is exactly the pattern Hard Rule 0 forbids; the practical stakes are
small since it only fires for a benchmark entity whose `reason` string already tends to be short
("no axis cleared its gate on this entity's own source pages" etc. — see `assay_entity`'s returns).

### 3. `src/magnitude.py:1301` — DEFERRED anchor value truncated before being persisted

```python
        return {"entity": entity, "host": host, "result": None, "status": "DEFERRED",
                "reason": ("the model returned an anchor that is not on the ladder ("
                           + repr(str((got or {}).get("anchor"))[:40]) + "); retried next run"),
```

This dict is `run_batch`'s per-entity result, written whole into `data/ASSAYS.json`. The garbage
anchor string the model returned is cut to 40 characters inside the persisted `reason` field. If a
future model hallucinates a long non-ladder "anchor" (e.g. a rambling sentence instead of "M4"),
the persisted diagnostic loses the tail of it with no indication anything was cut.

Confidence: medium — this is diagnostic text about an anomalous model output rather than a roster
or listing, so it's a smaller instance of the pattern, but it is a written string sliced per Hard
Rule 0's literal wording.

### 4. `src/magnitude.py:722` — citation-rejection reason truncates the citation, and that reason is persisted

```python
    if not _substantial(rn):
        return None, ("citation too short to identify one feat (" + repr(raw[:40])
                      + "); quote the evidence line verbatim")
```

`why_cite` here becomes a `rejects` entry inside `verify()`, and `assay_entity()` returns
`"rejections": rejects` which `run_batch` persists whole into `data/ASSAYS.json`. `_substantial`
rejects a citation for being short on *either* token count or character count — a citation with
few tokens can still exceed 40 characters (one very long non-space run, or several short words
strung together past the 40-char mark), so this can silently drop the informative tail of a
rejected citation from the permanent record. This is the same shape the file's own comments
elsewhere call out and fix (`order a3c5d3bfe312`, `order 29dde10c569c` in `chain.py`) but this
particular site was missed.

Confidence: medium — the input is by construction usually short, so the practical loss is often
nil, but the guard clause (`too short on chars OR too short on tokens`) means it isn't always.

### 5. `src/magnitude.py:1727` — batch-worker exception reason truncated, persisted to ASSAYS.json

```python
        except Exception as e:
            silence.note("magnitude.py:run_batch")
            r = {"entity": n, "host": h, "result": None,
                 "reason": type(e).__name__ + ": " + str(e)[:160]}
```

`r` is stored into `done[h + "|" + n]` and written whole to `data/ASSAYS.json` on every completion.
The exception message is cut to 160 characters in the persisted record with no note of the cut or
the original length. (The exception itself is properly logged via `silence.note`, so this is only
about the persisted text being shortened, not about a swallowed exception.)

Confidence: medium — a longer stack-trace-adjacent message could plausibly matter for diagnosing a
recurring transport failure across the batch; 160 chars usually covers the useful part but not
always.

### 6. `src/backfill.py:230` — `--dry` run exposes only a 12-item sample of the missing roster, with no full list anywhere

```python
    if dry or not missing:
        return {"source": source, "host": host, "roster": len(names),
                "already_held": len(names) - absent, "absent": absent,
                "queued": len(missing), "sample": missing[:12], "added": 0, ...}
```

Unlike the other capped-preview patterns already fixed elsewhere in this same file (e.g. the
`--audit` roster print, corrected under order 03c0fe609e89, prints every row precisely because
"the roll bounds this at ~215 rows... and NAMING which sources are thin is the entire purpose of
the line"), a `--dry` invocation never writes anything to disk (no `write_record_catalogue` call)
and the caller (`main()`, both the `--source` and `--all` paths) never surfaces the full `missing`
list — only `len(missing)` counts and this 12-name `sample`. So for a source that is short by (say)
400 characters, a person running `--dry` to see *which* characters would be added can only ever see
12 of them; the rest exist solely as a count until the run is repeated without `--dry`. This is
narrower than the roster/page-list caps Hard Rule 0's examples name, but it is the same shape: a
ranked list silently cut with no "and N more" and no pointer to where the rest live.

Confidence: medium — this is a diagnostic/preview path rather than a corpus-shaping one, and the
field name `"sample"` at least signals it isn't the whole list, but the full list is genuinely
unavailable through this tool's own dry-run mode.

---

## QUESTIONS (possibly deliberate — not filed as defects)

### Q1. `src/backfill.py:371-378` — per-source exception handler has no `silence.note` tag

```python
            try:
                res = backfill_source(x["source"], recs, hosts, cap=a.cap, dry=a.dry)
            except Exception as e:
                # Contained per source (Hard Rule -1: a source is its own area of the park) --
                # but COUNTED. N sources raising RosterIncomplete used to leave no mark on the
                # closing summary at all.
                errors += 1
                print("  %3d/%d  %-46sERROR %s" % (i, len(thin), x["source"][:44],
                                                   type(e).__name__), flush=True)
                continue
```

Unlike finding #1 above, this one has a substantial in-line justification explicitly invoking
Hard Rule -1's "a fault in one source must never close the whole library" doctrine, and the
failure is visibly counted (`errors`) and printed with the exception's class name, then reported
in the run's closing summary. It just doesn't also call `silence.note`, so it won't show up in
whatever inventory reads those tags. Is the explicit Hard Rule -1 comment + counter meant to be
the accepted substitute for a `silence.note` tag here, or should this call it too for the tooling
to see it?

### Q2. `src/entity_match.py:290` — `embed_available()`'s except has no `silence.note` tag

```python
    try:
        with urllib.request.urlopen(host.rstrip("/") + "/api/tags", timeout=10) as r:
            tags = json.loads(r.read().decode("utf-8", "replace"))
    except Exception:
        return {"available": False, "reason": "ollama unreachable", "models": []}
```

This reads as an ordinary reachability probe (the function's whole job is "is a thing there or
not"), and the returned `reason` already states plainly what happened, so nothing is hidden from
the caller. It just isn't tagged the way this codebase tags every other broad `except`. Worth
asking whether a probe like this is meant to be exempt from the `silence.note` convention, or
whether it should carry one too (this module is also explicitly "nothing calls this module yet",
per its own docstring, so it may simply not have been through the same audit passes as the rest
of the pipeline yet).

### Q3. `src/magnitude.py` `LOCAL_FITS` / `ONE_SHOT_MAX` / `SPLIT_SLICE` constants (20000 / 30000 / 8000 chars)

Not a finding — these are extensively justified with measured numbers in the surrounding
comments (recall-cliff measurements, context-window sizes). Flagged only so it's on record that
they were reviewed and found to be deliberate, evidence-based tuning rather than arbitrary caps.

---

## Modules with no findings beyond the above

`src/chain.py`, `src/handbuilt.py`, `src/navtree.py`, `src/halo.py` were read in full and no new
defects were found in them — each already carries the "Hard Rule 0 / no cap / atomic write /
gated write-verdict" fixes throughout, consistently applied, with no residual truncation of a
persisted or printed roster located during this pass.
