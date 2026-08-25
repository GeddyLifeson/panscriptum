# AUDIT — Batch 09, run32

Modules read in full (every line):

| file | lines |
|---|---|
| src/feats.py | 1015 |
| src/handbuilt.py | 487 |
| src/endpoint.py | 394 |
| src/context_budget.py | 278 |
| src/wh40k.py | 244 |
| src/retry_synthesis.py | 182 |
| src/scale_theories.py | 148 |

Also read for context (not part of this batch, not separately audited): `src/silence.py`
(`write_json`/`replace_retry` contract), `src/pipeline.py:synthesis_blocks/synthesis_prompt`
(to settle the retry_synthesis.py lead).

---

## KNOWN OPEN LEADS — verdicts

### Lead 1: `endpoint.py` `fetch_html()` swallows every exception — CONFIRMED

`fetch_raw()` (endpoint.py:190-233) was rewritten to distinguish three cases inside its
`one(t)` worker:
- `urllib.error.HTTPError` with code in `(404, 410)` → tagged `fetch_raw-absent` (a genuine miss)
- any other `HTTPError` code (403/429/500/etc.) → tagged `fetch_raw-refused-<code>` (a refusal,
  counted separately so a block doesn't masquerade as an absence)
- any other `Exception` → tagged `fetch_raw` (generic)

`fetch_html()` (endpoint.py:318-340), defined ~85 lines below and modeled on the same
`ThreadPoolExecutor`/`one(u)` shape, has one `except Exception:` (line 330) that funnels
*everything* — including an `HTTPError` carrying a 403/429/500 — into the single tag
`endpoint.py:fetch_html`. There is no HTTPError branch at all. A rate-limited or blocked
one-author homebrew site (kthomebrew.com, GM Binder pages — exactly the sources this mode
exists for) reads identically to a page that is genuinely 404, and both read as "this source
has no material here." This is precisely the bug class `fetch_raw` was rewritten to fix, left
unfixed one function down. **Severity: MAJOR.**

### Lead 2: `endpoint.py` raw mode does not follow redirects — CONFIRMED

`grep -n redirect src/endpoint.py` returns nothing — the string `redirect` does not appear
anywhere in the file. `raw_url()` (endpoint.py:182-187) builds its query as
```python
q = urllib.parse.urlencode({"title": title.replace(" ", "_"), "action": "raw"})
```
with no `redirect=yes`/`redirect=no` parameter. MediaWiki's `action=raw` does not follow
redirects by default; it returns the literal wikitext of the redirect stub (`#REDIRECT
[[SRD:Barbarian]]`), which is exactly the `redirect SRD:<title>` text the lead describes
showing up in 805 cached dandwiki entries. The same missing parameter is present in the
raw-mode *detection* probe too (`detect()`, line 157: `?title=Main_Page&action=raw`), though
that probe is lower-risk since Main_Page is rarely itself a redirect. `fetch_raw()`'s own
"is this an error page" check (line 160, `<!doctype`/`<html>` prefix test) does not catch a
redirect stub either — a redirect stub is short plain wikitext, so it passes straight through
and gets cached as if it were the article. **Fix location: `raw_url()`, endpoint.py:186** (add
`redirect=yes` to the `urlencode` dict). Not applied, per instructions. **Severity: MAJOR**
(counts as a standing `health --preflight` failure on the whole dandwiki raw-mode source, per
the lead).

### Lead 3: `feats.py` caps that decide a score — CONFIRMED (two separate defects found)

**3a. `discover()` — un-continued API pagination caps still bind.** `discover()`
(feats.py:312-369) queries `list=allpages` with `aplimit=500` (line 350) and `list=search`
with `srlimit=50` (line 360) and never follows the `continue` token MediaWiki returns when a
response was truncated. The file's own header comment (feats.py:76-86) documents this
candidly and instruments it (`_CAP_BOUND`, incremented at lines 352 and 362, reported in
`roll()`'s summary at 919-924) — but instrumenting a cap is not removing it. Any entity with
more than 500 evidence subpages or more than 50 matching search hits has its *evidence
gathering* truncated by the API's own default page size, silently (well, counted, but not
fixed) losing pages that would otherwise feed `mine()` and ultimately the Magnitude ceiling.
This is a live Hard Rule 0 violation on the evidence side of the scoring pipeline, distinct
from (and less visible than) the `extra=[:N]` cap that line 316-328's docstring says was
already removed. **Severity: BLOCKING.**

**3b. `resolve_title()` / `_page_exists()` are dead code — the 17,148-entry fix was never wired in.**
`resolve_title()` (feats.py:385-425) has an extensive docstring describing a real, measured
defect: "17,148 entries mined to nothing because the entity's catalogue name is not the wiki's
page title." It implements a careful ranked-candidate resolver (exact normalized match, then
name-plus-disambiguator, tie-broken by article size) specifically to fix that. **Neither this
function nor its helper `_page_exists()` (feats.py:377-382) is called anywhere in the
codebase** (`grep -rn "resolve_title\|_page_exists" --include=*.py src/` finds only the two
`def` sites). `evidence_for()` → `discover()` (feats.py:733-791, 336) uses the raw catalogue
`name` as the entity's page title directly (`add(name)` at line 336) and never calls
`resolve_title` to correct it. The fix exists in source, reads as applied, and is completely
disconnected from the pipeline that would need it — so the 17,148-entry defect the docstring
describes is still live in production despite looking solved. This is the report's clearest
instance of "a refusal recorded as an absence": the code that would prevent the absence exists
and does nothing. **Severity: BLOCKING.**

### Lead 4: two-writer contract (`silence.replace_retry`/`write_json` vs. hand-rolled tmp+replace)

**`endpoint.py:83-94` `_save()` — CONFIRMED, the clean instance of the reported bug.**
```python
tmp = CACHE + ".tmp"
with open(tmp, "w", encoding="utf-8") as f:
    json.dump(_MEM, f, indent=1, sort_keys=True)
os.replace(tmp, CACHE)
```
wrapped in a bare `except Exception: silence.note("endpoint.py:save")`. Compare
`silence.write_json` (src/silence.py:290-321), which (a) names the tmp file with PID+thread
so two concurrent writers of `ENDPOINTS.json` cannot collide on the tmp file itself, and (b)
replaces via `replace_retry`, which retries a Windows `PermissionError` (a reader holding the
target open) up to 5 times with backoff before giving up — silence.py's own docstring cites a
worker going down on exactly this Windows lock (2026-08-23, WinError 5). `_save()` has neither
protection: a fixed shared tmp name, and a single unretried `os.replace` whose
`PermissionError` is swallowed by the outer `except Exception` and the write is simply lost
(not retried next round, unlike every writer that goes through `replace_retry`). `detect()`
calls `_save()` from inside the lock on every single successful or dead-verdict probe
(endpoint.py:172), so this runs constantly and is the highest-traffic writer in the whole
module. **Severity: BLOCKING** (matches the reported instance exactly).

**Two further partial instances found in-batch (same shape, lower traffic):**
- `feats.py:296-299` (`resolve_hosts()`, writes `WIKI_HOSTS.json`) and `feats.py:810-814`
  (`evidence_for()`, writes the per-entity feats cache) both use `silence.replace_retry` for
  the *replace* step (so they get the Windows-lock retry) but still hand-roll the tmp file as
  a fixed `path + ".tmp"` rather than going through `silence.write_json`'s PID+thread-tagged
  name — so two processes writing the same path at once can still collide on the shared tmp
  file itself, the exact hazard `write_json`'s docstring names. **Severity: MINOR** (partial
  fix, real but lower-probability window; `evidence_for()`'s targets are per-entity so a
  collision needs the *same* entity mined twice concurrently).
- `handbuilt.py:453-459` (`main()`, writes `HANDBUILT_ASSAYS.json`) same fixed-tmp-name
  pattern, but this file has exactly one writer (a manually-run CLI), so the two-writer
  collision risk is theoretical. **Severity: NOTE.**

`wh40k.py:237` and `retry_synthesis.py:48` (`save_side`) both already go through
`silence.write_json` correctly and are clean on this axis — `retry_synthesis.py`'s own
docstring at lines 45-48 explicitly documents having been fixed at run #31.

### Lead: `retry_synthesis.py` Hard Rule 0 cap — REFUTED (already fixed)

The file's own docstring at `synthesise()` (lines 57-72) describes the exact bug the task
description points at — a `sorted(entries, by description length)[:14]` block that never
consulted a mined feat — and states it was rewritten at run #31 to delegate to
`pipeline.synthesis_blocks(rec)` (called at feats.py-adjacent `retry_synthesis.py:74`), which
is now the single shared implementation used by both the main synthesis phase and this retry
path. Read `pipeline.synthesis_blocks` (src/pipeline.py:713-739, outside this batch, read for
context only): every feat-bearing entry is chunked into *all* of its 14-per-call blocks via
`range(0, len(with_feats), 14)` — no truncation of the feat-bearing list. Only the
description-only fallback (`rest[:14]`, used solely when a source has zero feat-bearing
entries at all) stays a single block, and pipeline.py's own comment documents that as a
deliberate decision (a description is biography, not a deed — sampling more of it buys
nothing), not an oversight. **As currently written, `retry_synthesis.py` does not reproduce
the reported cap.** (Note: `pipeline.py` is not in this batch and was not separately audited;
this verdict is scoped to the file the lead named.)

---

## OTHER FINDINGS (this batch's own reading, not from the lead list)

### `feats.py:592-614` `mine()` — rejection ledger silently drops most of what it claims to keep. MAJOR

The module docstring (feats.py:25-29) states the whole point of this module is that it "keeps
everything it gathers, including what the gate turned down, because the previous pass
discarded its rejections and left the rejection rate unauditable." The actual code:
```python
if P.valid_scale_note(s):
    kept.append({"feat": s, "page": page})
elif _QUANTITY.search(s) or re.search(r"\b(destroy|obliterat|shatter|surviv)", s, re.I):
    rejected.append({"text": s, "page": page})
```
A sentence that fails `valid_scale_note` (the gate) is only recorded into `rejected` if it
*additionally* matches a physical-quantity pattern or one of four ruin-adjacent verbs. Every
other gate-failing sentence — which, given the gate's own documented 99.7% rejection rate from
`_act_upon_object` on non-ruin material (feats.py:620-632), is most of them — is dropped by
neither branch and simply vanishes. The rejection rate this function exists to make auditable
is therefore itself under-counted, in the same shape as the defect the docstring says it was
built to fix. This does not affect `kept`/scoring directly, but it means `gate_rejected` in
the on-disk evidence file (feats.py:809) undercounts, so anyone using it to audit the gate's
strictness (which is exactly what the surrounding comments at 620-638 describe doing) is
working from a partial ledger without any signal that it's partial.

### `context_budget.py:243-271` — four silent `except Exception` blocks, no `silence` import at all. MAJOR

`feats_block_budget()` (lines 242-253) and `report()` (lines 262-271) each wrap their
`open(...prompts/system_style.txt...)` / `open(...prompts/feats_prompt.txt...)` reads in
`except Exception: system_text = ""` / `ftpl = ""`, with **no** `silence.note` call — the file
does not `import silence` at all, the only one of this batch's seven files (besides
`scale_theories.py`, which does no file I/O) not to. This is notable specifically because this
module's entire purpose is preventing silent truncation of model prompts (see its own header,
lines 1-58: "the loss must not be filed as a result"). If either prompt file is briefly
unreadable (a Norton object-lock, a concurrent writer, a bad path), `feats_block_budget()`
silently treats the system scaffolding as zero characters, which computes an *inflated*
content budget — the opposite of the pessimism the module's own comments insist on
(`CHARS_PER_TOKEN`/`PROSE_CHARS_PER_TOKEN` are explicitly kept "below their measured values...
so the refusal keeps its safety direction," lines 55-58). Practical impact is capped by a
downstream backstop: `generate.py:132-133` calls `context_budget.assert_fits(cfg,
system_prompt, user_prompt, ...)` with the *actual already-loaded* system prompt text (not
re-read from disk), so the real gate at generation time still sees genuine text and will still
raise `ContextOverflow` loudly if a block is oversized. But `manifest_builder.py:331` calls
`_CBUD.feats_block_budget(cfg)` with no text arguments — hitting the silent fallback directly —
to decide how large a feats block to *pack in the first place*, and `health.py`'s
`check_context_budget()` (health.py:168) surfaces `report()`'s numbers for preflight; both
would silently report a wrong (larger) budget on a transient read failure with no record
anywhere that it happened. Fix would be either to `import silence` and call `silence.note` in
these four except blocks, or better, to let the read failure raise rather than substitute an
empty string.

### `feats.py:693-702` `axis_evidence()` — dead code duplicated (not called) by `by_axis()`. MINOR

`axis_evidence(sentence, axis)` implements "does this sentence evidence this axis" as a
single-sentence predicate. `grep -rn "axis_evidence\b" --include=*.py src/` finds only its own
`def` — it is never called. `by_axis()` (feats.py:705-728), the function that actually builds
the per-axis candidate lists used downstream, reimplements the identical three-gate logic
inline (statblock/patient gate, then object/magnitude/comparative gate, then per-axis
vocabulary) rather than calling `axis_evidence()`, with a comment (717-720) explaining the
inlining was done for performance (hoisting the axis-independent regexes out of an
eleven-times-per-sentence loop). That's a reasonable optimization, but it leaves
`axis_evidence()` as a live landmine: it looks like the current logic and is not, so a future
fix applied to one and not the other silently diverges the two — the exact "ruling applied
where someone was already looking, not next door" failure shape this codebase's own comments
call out repeatedly elsewhere (e.g. wh40k.py:230-236, endpoint.py:361-370). No live impact
today since nothing calls it, but it should be deleted or the duplication resolved.

### `feats.py:453-459`, `handbuilt.py:464-465` — deliberate no-op excepts. Reviewed, no defect.

Both are explicitly commented `"silence-exempt: ..."` no-ops for a genuinely uninformative
failure (removing an already-gone temp file; a console that can't reconfigure encoding but
still prints). Consistent with the project's stated convention. NOTE only, listed so the reader
knows these bare excepts were checked and are not instances of the headline defect.

### `wh40k.py` — clean. NOTE.

Full read, 244 lines. Uses `silence.write_json` correctly (line 237, with an explicit comment
citing the m100/run#27 fix applied to its sibling `zfighters.py`). No caps, no swallowed
exceptions, no dead code found.

### `scale_theories.py` — clean. NOTE.

Full read, 148 lines. Pure-function physics module (no file I/O, no network, no shared state).
`bulk_export_beta`/`growth_strike`/`penetration_pressure` all guard their divisions
(`max(x, epsilon)`), `surviving_theory()`'s `startswith("Nothing attested")` filter is a
by-design single-match check, not a tautology. Confirmed live (imported by `src/derivation.py`),
not dead code.

---

## Summary table

| file:line | severity | defect |
|---|---|---|
| endpoint.py:83-94 | BLOCKING | `_save()` hand-rolled tmp+`os.replace`, no retry, no `write_json`/`replace_retry` — the reported two-writer defect, confirmed |
| endpoint.py:186 | BLOCKING | `raw_url()` omits `redirect=yes`; dandwiki (and any raw-mode host) serves redirect stub text as if it were the article — confirmed |
| feats.py:349-362 | BLOCKING | `discover()`'s `aplimit=500`/`srlimit=50` are never continued past MediaWiki's `continue` token — a live Hard Rule 0 cap on evidence gathering, only instrumented not fixed |
| feats.py:377-425 | BLOCKING | `resolve_title()`/`_page_exists()` — the documented fix for 17,148 wrongly-titled entities — are never called from `discover()`/`evidence_for()`; dead code, defect still live |
| endpoint.py:318-340 vs 190-233 | MAJOR | `fetch_html()` swallows every exception under one tag; `fetch_raw()` (rewritten ~40 lines above) distinguishes absence/refusal/generic — confirmed |
| feats.py:592-614 | MAJOR | `mine()` only records a gate-rejected sentence into `gate_rejected` if it also matches a narrow quantity/ruin-verb pattern; contradicts its own docstring's "keeps everything it gathers" claim |
| context_budget.py:243-271 | MAJOR | four silent `except Exception` (no `silence` import, no `.note` calls) in the one module whose whole job is preventing silent truncation; backstopped at generation time but not at pack-time (`manifest_builder.py:331`) or preflight (`health.check_context_budget`) |
| feats.py:296-299, 810-814 | MINOR | partial two-writer fix: `replace_retry` used but tmp file name is a fixed `path+".tmp"`, not PID/thread-tagged — collision window remains |
| feats.py:693-728 | MINOR | `axis_evidence()` dead, logic duplicated inline in `by_axis()`; drift risk |
| handbuilt.py:453-459 | NOTE | same fixed-tmp-name pattern, single-writer file, low risk |
| retry_synthesis.py cap lead | NOTE | REFUTED — already fixed at run #31, now delegates to `pipeline.synthesis_blocks` |
| wh40k.py | NOTE | clean, full read |
| scale_theories.py | NOTE | clean, full read |

4 BLOCKING, 3 MAJOR, 2 MINOR, 5 NOTE.
