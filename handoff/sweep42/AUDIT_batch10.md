# sweep42 batch 10 audit

Modules read in full: `src/publish.py` (1604 lines), `src/health.py` (954), `src/build_terminal.py`
(654), `src/ingest_doc.py` (542), `src/canon_backup.py` (418), `src/sweep.py` (346), `src/wh40k.py`
(302), `src/suppressions.py` (242).

General note: all eight modules carry an unusually high density of prior self-audit ("order
<hash>") comments and are already hardened against most of the classic failure shapes this
project has catalogued (swallowed exceptions, discarded write verdicts, silent caps). The findings
below are what remains after that baseline.

---

## CONFIRMED DEFECTS

### 1. `src/suppressions.py:69-77` — `_load()` treats a wrong-shaped JSON file as an honest empty list, not a corruption

```python
def _load():
    try:
        with open(FILE, encoding="utf-8") as f:
            d = json.load(f)
        return (d if isinstance(d, list) else []), True
    except FileNotFoundError:
        return [], True
    except Exception:
        silence.note("suppressions.py:load")
        return [], False
```

If `SUPPRESSIONS.json` parses as valid JSON but is not a list (e.g. someone hand-edits it into a
`{...}` object, or a future writer bug lands a dict), `json.load` raises nothing, `isinstance(d,
list)` is `False`, and this returns `([], True)` — `ok=True`. That is indistinguishable from a
file that has never been created.

The module's own header and the `_load` docstring exist specifically to prevent this shape:
"UNREADABLE MUST NOT LOOK LIKE EMPTY (order 9a18068421c3)... A corrupt `SUPPRESSIONS.json`
therefore reported ZERO suppression problems, the exact opposite of an expired-or-dangling
suppression, which this module's whole job is to surface as a fault." That fix only covers the
`JSONDecodeError` / unreadable-file case (the `except Exception` branch). A file that parses fine
but has the wrong top-level type sails straight past it: `problems()` (which drives `--check`)
will print "0 suppression problem(s)" and exit 0 for a corrupted suppressions file, which is
exactly the "check that cannot fail" shape the audit brief calls out and the one this module's own
docstring says it fixed.

**Confidence: high.** The code path is unambiguous; the only question is whether this shape of
corruption has ever actually occurred (probably not yet, since the only writer is `_land()`, which
always writes a list) — but the module treats "wrong type" and "genuinely absent" identically
despite explicitly rejecting that equivalence for the unreadable case one branch up.

---

### 2. `src/canon_backup.py:362-378` — `restore()` can leave a misleading 0-byte file on a bad `rel`

```python
def restore(rel, path=None, dest=None):
    path = path or newest()
    if not path:
        raise RuntimeError("no snapshot to restore from")
    dest = dest or os.path.join(ROOT, "restored", os.path.basename(rel))
    os.makedirs(os.path.dirname(dest), exist_ok=True)
    with zipfile.ZipFile(path) as z, open(dest, "wb") as out:
        with z.open(rel) as fh:
            for block in iter(lambda: fh.read(1 << 20), b""):
                out.write(block)
    return dest
```

`open(dest, "wb")` is entered (creating/truncating `dest`) as part of the same `with` statement
that then calls `z.open(rel)`. If `rel` is not a member of the archive — an operator typo in
`--restore REL`, or a canonical path that existed in an older snapshot but not the one being read
— `z.open(rel)` raises `KeyError` *after* `dest` has already been created as an empty file. The
`with` blocks unwind, `dest` is left on disk at 0 bytes, and the caller sees a raw `KeyError`
traceback rather than a clean message.

This is the exact class of hazard the rest of this module is written to prevent (`snapshot()`'s
temp-then-verify-then-rename pattern, `prune()`'s "a pair half-removed counts as NOT removed").
`restore()` is the one writer in the file that does not go through a temp name + atomic rename, so
a failed restore doesn't fail cleanly — it leaves a plausible-looking but empty artifact at the
destination path, which a caller checking only for the file's existence would misread as a
successful restore of an empty file.

**Confidence: high.** Straightforward to reproduce: `canon_backup.py --restore data/typo.json`
against any real snapshot leaves a 0-byte `state/backups/canon/restored/typo.json` before raising.

---

### 3. `src/health.py:928-930` — `main()`'s `--reopen` path discards `reopen_stranded()`'s failure signal and always returns 0

```python
if a.reopen:
    reopen_stranded(dry=not a.go)
    return 0
```

`reopen_stranded()` prints a distinct message and returns `[]` for at least three different
outcomes: (a) `PIPELINE_STATE.json` is unreadable, (b) there is genuinely nothing to reopen, and
(c) (with `--go`) the write of the repaired state was denied. Cases (a) and (c) are real failures
— exactly the "PIPELINE_STATE.json unreadable" and "write DENIED; nothing re-opened" branches the
function itself prints to stderr — but `main()` never looks at the return value, so `health.py
--reopen --go` exits 0 in every one of these cases. Any scheduler or wrapper script that keys off
the exit code (rather than scraping stdout/stderr) cannot tell "nothing was stranded" from "the
repair failed to read or write its own state file." This is the same "a check that cannot fail
looks like a check that passed" shape the module's own docstring opens with, applied to its own
CLI's exit code.

**Confidence: high.**

---

## FINDINGS WORTH FLAGGING BUT LOWER-CONFIDENCE / PARTIALLY MITIGATED

### 4. `src/publish.py:1266-1281` — the leaked-secret evidence list is capped at 20 (escalation) / 10 (printed refusal), unranked

```python
leaks = [h for h in scan_for_secrets(SITE) if not str(h[2]).startswith('SUPPRESSED')]
if leaks:
    import escalation as _ESC
    _ESC.escalate(_ESC.OWNER, "SECRET_IN_EXPORT",
                  "publish refused: %d credential-shaped value(s) staged for the PUBLIC "
                  "repo. First: %s:%s (%s)"
                  % (len(leaks), leaks[0][0], leaks[0][1], leaks[0][2]),
                  evidence=[{"file": f, "line": n, "why": w} for f, n, w in leaks[:20]],
                  who="publish.py")
    raise RuntimeError(
        "PUBLISH REFUSED — %d credential-shaped value(s) are staged for the public repo:\n"
        % len(leaks)
        + "\n".join("    %s:%s  %s" % (f, n, w) for f, n, w in leaks[:10])
        + "\nNothing was pushed, and the library has been halted. Remove the value, then "
          "clear the halt with a ruling. If it is a false positive, say so in the ruling.")
```

`leaks` comes from `scan_for_secrets`, which walks files via `sorted(files)` within each directory
— i.e. this is an unranked, alphabetical-by-path prefix, not "worst/most-recent first." If more
than 10 (resp. 20) credential-shaped values are staged at once, the escalation evidence and the
raised exception both silently show only an arbitrary alphabetical head, with no "+N more" in the
list itself — the total count (`%d`) is stated in the header, so the omission is at least
*visible* (a reader who does the arithmetic knows something was left off), which is why this is a
partially-mitigated case rather than the classic Hard-Rule-0 shape ("roster(limit=600) returned
Dragon Ball A-through-G... Superman fell outside the window" with nothing to say so). But this is
exactly the guard whose job is remediation evidence for a public-repo secret leak: an owner working
off the printed message (10 of N) or even the escalation record (20 of N) could fix every leak they
were shown and reasonably believe the incident is closed while additional credential-shaped values
remain staged.

**Confidence: medium.** The mechanism is real and the cap is unranked; whether it rises to a
must-fix depends on whether >20 simultaneous leaks is considered plausible in this project (a
single credentials file or `.env` accidentally staged could easily produce more than 20 line hits
by itself).

### 5. `src/health.py` / `src/ingest_doc.py` — the context-budget preflight does not cover `ingest_doc.py`'s own chunking

`health.check_context_budget()` (health.py:451-471) imports `read as R` and checks
`R.SYSTEM`/`R.CHUNK` against `num_ctx`. `ingest_doc.py` runs its own, separately-maintained
pipeline against the same local model (`_ask()` → `pipeline.ask`, ingest_doc.py:221-238) with its
own `CHUNK = 9000` and its own `SYSTEM` prompt (ingest_doc.py:39, 50-58), and the module's own
comment claims parity — "`CHUNK = 9000  # characters per extraction call — the same altitude
read.py mines at`" — but nothing in `health.py`'s preflight battery actually checks
`ingest_doc.py`'s arithmetic. If `read.py`'s `CHUNK`/`SYSTEM` ever change independently (the stated
purpose of `check_context_budget` existing at all — "Ollama does not refuse an overlong prompt, it
truncates silently"), the preflight stays green while `ingest_doc.py`'s separate context budget is
never re-verified, and the parity claim in its own comment becomes unverified rather than
guaranteed.

**Confidence: medium.** Not a live failure today (rough arithmetic: ~2432 body tokens + ~175
system tokens + 700 reply ≈ 3300, comfortably under the 6144 default `num_ctx`), but it is a real
gap in what the preflight actually exercises versus what the codebase asserts it protects against.

---

## QUESTIONS (possibly deliberate design — not proposed as fixes)

* **`src/publish.py:1389-1449` (`maintenance_shift_live`)** is explicitly documented as **failing
  open**: "FAILS OPEN, deliberately, and this is the opposite of `subsystem_stopped`'s rule. An
  unreadable or missing guard file means PUBLISH." This is a carefully reasoned, asymmetric-cost
  argument, but it sits in visible tension with Hard Rule -1's stated non-negotiable property that
  "every layer answers 'I don't know' with STOP" / "FAIL CLOSED... Silence must never authorise
  anything." Worth confirming with the owner that this specific, named exception to the universal
  fail-closed doctrine is still endorsed, since it is the one interlock in `push()`'s chain built
  the opposite way from its three siblings (secret scan, `ledger_guard`, `mutate` interlock — all
  fail closed on import/read failure).

* **`src/canon_backup.py:230-284` (`prune`)** — `for f in snaps[:-keep] if keep > 0 else []:` means
  `--keep 0` (or a negative value) removes *nothing*, i.e. behaves like "keep everything" rather
  than the arguably more intuitive "keep zero snapshots." Likely a deliberate conservative
  guard against a nonsensical `--keep` value rather than a bug, but the CLI help text doesn't say
  so and a `--keep 0` invocation intending "prune all but the one just taken" would silently no-op.

* **`src/suppressions.py:186-200` (`problems()`)** re-globs the entire project tree
  (`glob.glob(os.path.join(HERE, "**", "*"), recursive=True)`) once per wildcard-pattern
  suppression row to check for dangling patterns. Not a correctness issue, but on a corpus this
  size (`data/records/` alone ~206 MB across hundreds of files, plus `data/feats/`) this could be
  materially slow if the suppression list ever grows past a handful of glob-based rows, since the
  full recursive walk repeats per row rather than being computed once.

* **`src/wh40k.py:246-248` (`main()`)** — `A.LADDER.index(kv[1]["assay"]["magnitude"])` will raise
  `ValueError` uncaught if `assay()` (in `src/assay.py`, not part of this batch) ever returns a
  magnitude string not present in `A.LADDER`. Not verified against `assay.py`'s actual guarantees
  since that module is outside this batch's scope; flagged only as a coupling point worth checking
  if `assay.py` is ever audited.

---

## Coverage recorded

```
cd C:\Users\imarl\panscriptum-library-kit && PYTHONIOENCODING=utf-8 C:/Users/imarl/miniconda3/python.exe -c "import sys; sys.path.insert(0,'src'); import sweep_plan; sweep_plan.record('run42', ['publish.py','health.py','build_terminal.py','ingest_doc.py','canon_backup.py','sweep.py','wh40k.py','suppressions.py'], batch=10)"
```
