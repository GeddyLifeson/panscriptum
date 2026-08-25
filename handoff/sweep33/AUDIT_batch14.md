# Batch 14 — run33
Modules read: rigor.py (865 lines), build_terminal.py (579 lines), rosetta.py (416 lines), ingest_doc.py (302 lines), binding_health.py (256 lines), cleanup.py (215 lines), audit.py (177 lines)

## FINDINGS

### 1. binding_health.py:117-133 — `_probe_present` validates a wiki response with a bare length check, not the wiki-markup/refusal check this project already built for exactly this  [severity: MAJOR]
`_probe_present` decides a host is answering for real like this:

```python
if len(text.strip()) < 200:
    return False, "known-present title returned %d chars -- too thin to be the page" % len(text)
return True, "%d chars" % len(text)
```

`feats.py` already has `page_looks_real(text, title)` (feats.py:192-221), built specifically to close
this gap — its own docstring: *"a Cloudflare interstitial, a login wall, a soft-404 or a rate-limit
notice is a real document... Verbatim provenance against the wrong source is still wrong, and it
looks exactly like success."* It layers three checks: length (`MIN_REAL_PAGE_CHARS = 200`, the same
200 `binding_health.py` hardcodes), an explicit refusal-phrase check (`_REFUSAL_MARKERS` — "enable
javascript", "checking your browser", "cloudflare", etc.), and a positive check that the text
actually contains wiki markup (`_WIKI_MARKERS` — `[[`, `{{`, `==`, "infobox", ...).

`_probe_present` reimplements only the first, weakest layer and drops the other two. For a
RAW-mode host (`feats.fetch` → `endpoint.fetch_raw`, used by every API-closed wiki such as D&D
Wiki), the only other filter in the chain is `endpoint.fetch_raw`'s
`body.lstrip().lower().startswith(("<!doctype", "<html"))` check (endpoint.py:225) — which misses
any block/interstitial page that is not literally prefixed with one of those two exact tokens (a
BOM-prefixed page, a plaintext rate-limit message, a JS-challenge fragment that opens with
`<script>` or a comment). Any such page over 200 characters — which most real interstitials are —
passes `_probe_present` as `healthy=True`, exactly the failure class `page_looks_real` exists to
catch and that this project has already paid for once ("1,364 throttled fetches were filed as
honest absences," feats.py:204). For API-mode hosts this specific scenario is accidentally caught
because `json.loads` on HTML raises and `api()` returns `None` — but that is incidental, not
something `_probe_present` verifies.

### 2. binding_health.py:136-151 — `_probe_absent` treats an exception as a successful "correctly absent" verdict, letting `release()` fire on a probe that never actually completed  [severity: MAJOR]
```python
def _probe_absent(host, timeout=25):
    try:
        import feats as F
        got = F.fetch(host, [ABSENT_PROBE])
    except Exception:
        return True, "no answer, which is the correct answer"
```
An exception here (timeout, TLS failure, a raw-mode URL-encoding quirk on the deliberately-ugly
`ABSENT_PROBE` title) tells you nothing about whether the host correctly rejected the nonsense
title — it just means the request never completed. That is treated as `ok=True` anyway. Compare
`_probe_present`, four lines above it, which treats the identical situation as `False` (failure).
The two probes are inconsistent with each other, and `_probe_absent`'s branch is also inconsistent
with the project's own stated invariant in CLAUDE.md: *"FAIL CLOSED — every layer answers 'I don't
know' with STOP... Silence must never authorise anything."* Here an unrelated network exception
during the absent probe silently authorises `healthy = ok_p and ok_a` to be `True` (if the present
probe happens to succeed), and `run()`'s only gate on `release()` is `rec.get("healthy") is True` —
so a quarantined host can be released from an absent probe that never actually ran to completion,
let alone verified the host says no to a page it shouldn't hold.

### 3. cleanup.py:41-48 — `_NAV`'s word-boundary anchors don't require the match to end the name, so `--apply` would exclude real catalogued entities whose names merely start with a nav-like word  [severity: MAJOR]
```python
_NAV = re.compile(
    r"^(?:season\s+\d+\b|category:|list of |index of |gallery$|navigation$|main page$|"
    r"contents?$|glossary$|episodes?$|seasons?$|appearances?$|references?$|trivia$|"
    r"see also$|external links$|sitemap$|all pages$|recent changes$"
    r"|characters?\b|gameplay\b|mechanics\b|controls\b|achievements?\b|trophies\b"
    r"|downloadable content\b|patch notes?\b|version history\b|soundtrack\b)", re.I)
```
The comment directly above this block claims: *"'Character' matched and 'Character condition' did
not, because the anchor demanded the word end the name."* That is false for the second half of the
alternation (`characters?\b`, `gameplay\b`, `mechanics\b`, `controls\b`, `achievements?\b`,
`trophies\b`, the DLC/patch-notes/version-history/soundtrack terms) — those use `\b`, which is a
word-boundary, not `$` (end of string), unlike the first half of the pattern which correctly uses
`$`. Verified directly:
```
'Character condition'      -> MATCHES ('Character')
'Characters of the Realm'  -> MATCHES ('Characters')
'Character Alignment'      -> MATCHES ('Character')
```
Under `--apply` (cleanup.py:152-158), any catalogued entity whose name happens to open with one of
these words followed by more text — a plausible real name like "Trophies of the Fallen King," a
faction called "Controls Division," anything titled "Achievements of House X" — is set
`catalogued=False` with `excluded: "wiki navigation, not an entity of any fiction"`. That is a
real, silent removal from the catalogue for entities the pattern was never meant to catch, and the
dry-run preview only prints the first 5 examples (`nav[:5]`, line 193), so the full blast radius of
a given `--apply` run would not be visible before it writes.

### 4. audit.py:30-32 — `_JUNK` has the identical word-boundary bug as cleanup.py's `_NAV`, so the BACKSCAN invariant "wiki navigation artefact" count is unreliable  [severity: MAJOR]
```python
_JUNK = re.compile(r"^(characters?|category:|list of |index of |gallery|navigation|"
                   r"main page|contents?|glossary|timeline|episodes?|seasons?|"
                   r"appearances?|references?|trivia|see also|external links)\b", re.I)
```
Every alternative here shares one trailing `\b`, so `.match()` succeeds whenever the name simply
*opens* with one of these words followed by a word boundary — not when the whole name IS one of
these words. Verified directly against `_JUNK.match()`:
```
'Timeline of the Fallen Empire' -> MATCHES ('Timeline')
'Seasons of War'                -> MATCHES ('Seasons')
'Gallery of Rogues'             -> MATCHES ('Gallery')
'References Codex'              -> MATCHES ('References')
'Navigation Beacon'             -> MATCHES ('Navigation')
```
audit.py is read-only (it only builds a printed report, per its own docstring: *"checked from
outside rather than trusting the code that enforces them... the only way to catch a rule that
quietly stopped applying"*), so this doesn't delete data — but it does mean the "entry: wiki
navigation artefact, not an entity" bucket in the BACKSCAN report is itself unreliable, over-firing
on any real entity whose name happens to start with one of these words. That both undermines trust
in a check whose entire purpose is to be trustworthy-from-outside, and could bury genuine
navigation-scaffolding hits in a flood of false positives from unrelated entities.

### 5. rosetta.py:402 — an unexplained addition of a nonexistent module attribute into every Assay decimal used for the Rosetta correlation check  [severity: MINOR]
```python
assays = {k: v["result"]["decimal"] + P.__dict__.get("_x", 0)
          for k, v in json.load(open(path, encoding="utf-8")).items()
          if v.get("result") and v["result"].get("decimal") is not None}
```
`pipeline.py` never defines a module-level `_x` anywhere (confirmed by grep across `src/pipeline.py`),
so `P.__dict__.get("_x", 0)` is currently always `0` — a no-op. This codebase otherwise documents
every non-obvious line at length (see every other file in this batch); this line has no comment and
no evident purpose, and reads like debug residue (e.g. someone poking a scratch value onto the
`pipeline` module from a REPL) that was left in committed code. As written it is inert, but it is
also a silent corruption path with zero warning: if anything anywhere in the process ever does
`pipeline._x = <something>` (a debugging session, a future module, an interactive shell sharing the
same process), every Assay decimal used by `rosetta.check()` — the correlation test that validates
the Assay against each franchise's own published power scale — would be silently shifted by that
amount, with no error, no log line, and no indication in the printed `rho` report that anything
had changed.

## QUESTIONS

1. **binding_health.py:79-87, 221-222** — `is_quarantined(host)` is defined via `quarantined()`,
   which filters `HOST_QUARANTINE.json` down to entries whose `retry_after` has not yet passed. If a
   host's retry period elapses naturally and it is then found healthy, `is_quarantined(h)` is
   already `False` by the time `run()` checks it, so `release(h)` — gated on
   `rec.get("healthy") is True and is_quarantined(h)` — never fires, and the stale record (with a
   `retry_after` in the past) is never actually popped from the JSON file. Every real consumer
   (`feats.py`, `dashboard.py`, `health.py`, `workorders.py`) reads through the same filtered
   `quarantined()` view, so this looks functionally inert — but the file itself accumulates
   permanently-stale entries, and if the same host later fails again, `quarantine()`'s `times`
   counter continues from the old stale entry rather than starting fresh. Is the JSON file meant to
   be pruned of naturally-expired-and-now-healthy entries, or is "grows forever, filtered at read
   time" the intended shape?

2. **audit.py:166-172** — the "BANDED SAMPLE" section reuses the same `random.Random(args.seed)`
   instance after it has already been advanced by the "RANDOM SAMPLE" draw a few lines above, rather
   than seeding a second, independent `Random(args.seed)`. Re-running the identical command
   reproduces both sections identically (the stated goal — "the same sample can be re-read after a
   fix" — holds for that case), but the BANDED SAMPLE's actual draw is entangled with `--sample`'s
   value and with `len(pool)` in a way its own seed name doesn't suggest. Is that entanglement
   intentional, or should BANDED SAMPLE get its own `Random(args.seed)` for a sample that is
   reproducible independent of `--sample`?

3. **cleanup.py / audit.py — scope note, not a finding.** The task brief for this batch said
   "cleanup.py deletes things: audit every deletion path for what happens when its target is
   unexpectedly large or unexpectedly missing." I read the whole file and found no filesystem
   deletion anywhere in it (no `os.remove`, `shutil.rmtree`, `unlink`, `rmdir`) — it only mutates
   in-memory catalogue records (`catalogued = False`, an `excluded` reason) and rewrites the JSON
   record file via `pipeline.write_record`. There is no oversized/missing-target deletion path in
   this file as written, so I audited what it does instead (see Finding 3) rather than a deletion
   path that doesn't exist. Flagging this in case the brief's description was meant for a different
   file, or in case there is a deletion path elsewhere in the pipeline this module's output feeds
   into that I should have looked at instead.

## CLEAN

- **rigor.py** — read in full. This is the commensuration/math module (AHP/Perron eigenvector,
  HodgeRank log-least-squares, Bradley-Terry MM with Ford's-condition connectivity refusal, MDL
  beta-floor accounting, log-normal uncertainty propagation, extreme-value ceiling correction). I
  extracted `_strongly_connected` (its iterative Tarjan SCC implementation, used to enforce Ford's
  condition before Bradley-Terry will report a strength) and ran it against `networkx`'s
  `strongly_connected_components` over 200 random directed graphs plus several hand-picked cases
  (a 3-cycle, a disconnected pair, a chain, two components joined by a one-way edge) — all matched.
  The rest of the file is heavily narrated with dated, specific historical-bug commentary (several
  run-numbered fixes) that reads as evidence of real prior scrutiny, not as cover. Found nothing
  live.
- **build_terminal.py** — read in full, including the embedded JS (radial-layout SVG renderer for
  the Registry Terminal). The Python half (read NAVTREE.json, neutralise `<` before splicing into
  an inline `<script>` block, write the HTML) is correct and the `<` -> `<` escaping is safe
  inside JSON strings by construction. I traced the JS layout/sizing math (`discR`, `fitIn`,
  `ringFits`, `dotR`'s min-gap sizing, `layout()`'s wedge-weighting, `descend()`'s operator
  precedence, `clampView`) and found no logic bug, though this is presentational/geometric code I
  could not execute in a live browser to confirm the visual result — noted rather than certified.
- **ingest_doc.py** — read in full (PDF extraction, chunking on page boundaries, the resumable
  entity-mining loop with its `ingest_state.json` cursor). The resume/cursor-advance logic is
  explicitly and correctly hardened against the exact failure this project has been bitten by twice
  before (advancing the cursor past entities that were never actually written) — the code now
  rewinds `known` and stops without advancing `state["next"]` when `write_record_catalogue` reports
  the write was denied. Found nothing live.
