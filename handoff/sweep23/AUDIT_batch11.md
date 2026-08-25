# AUDIT batch11 — sweep23

Files: `src/dashboard.py`, `src/zfighters.py`, `src/publish.py`, `src/cosmography.py`,
`src/wh40k.py`, `src/descending_ladder.py`, `src/catalog.py`

Every line of every file was read in full (dashboard.py 732 lines, zfighters.py 485,
publish.py 380, cosmography.py 283, wh40k.py 239, descending_ladder.py 187, catalog.py 128).

---

## SECURITY-ADJACENT FINDING (publish.py) — read this first

**No actual secret was found sitting in any synced path right now.** I grepped `src/`,
`prompts/`, `reference/`, `registry_terminal/`, `handoff/`, and `config.yaml` for every pattern
in `publish.py`'s own `_SECRET` regex plus broader `api_key=`/`password=`/`secret=`-shaped
strings, and for GitHub-token prefixes inside `HANDOFF.md`/`BUGS.md`/`NEXT_STEPS.md`/
`MAINTENANCE.md`/`WATCH.md`/`STATUS.md`. Nothing matched. So there is nothing to redact today.

**But the architectural gap the task description described is real and precisely as stated.**
`publish.py:151-164`'s `_scrub()` walks and redacts only the object passed to it, and the only
caller is `snapshot()` (`publish.py:167-176`), which builds the small `state.json` dict from
`dashboard.state()` + `standards.check()`. That is the ONLY thing `_scrub` ever touches.

`sync_tree()` (`publish.py:203-241`) is a completely separate code path. It walks
`COPY_DIRS = ("src", "prompts", "reference", "registry_terminal", "handoff")` (line 133) and
copies every file with `shutil.copy2(srcp, dstp)` (line 229) verbatim, byte for byte, plus
`COPY_FILES = ("CLAUDE.md", "README.md", "config.yaml", "requirements.txt", "WATCH.md",
"STATUS.md", "HANDOFF.md", "BUGS.md", "NEXT_STEPS.md", "MAINTENANCE.md")` (lines 134-138),
also via `shutil.copy2` with **zero content inspection**. The only filtering at all is
`SKIP_SUFFIX` (line 142-143: `.pyc/.presilence/.prebandfix/.precapfix/.prefix/.prepool/
.preprobe/.prewiden/.prewindow/.bak/.tmp/.orig`) — a suffix denylist for backup-file
extensions, not a content or secret scan, and no `.env`/`.key`/`.pem`/`.credentials` exclusion
of any kind. `main()` then runs `git("add", "-A")` (line 303) over this exact tree and, with
`--push`, pushes it to the configured public remote.

So: if any file under `src/`, `prompts/`, `reference/`, `registry_terminal/`, `handoff/`, or
`config.yaml` ever contains a literal credential — a pasted API key while debugging, a stray
`.env`, a hardcoded test token in a `.py` file, a credential pasted into `BUGS.md`/`HANDOFF.md`
while troubleshooting an auth failure (`publish.py`'s own `git()` docstring at lines 179-190
describes exactly this kind of troubleshooting happening around `GITHUB_TOKEN`/`GH_TOKEN`) — it
ships to the public repo with no technical safeguard at all, relying entirely on human
discipline. Confirmed concretely: `handoff/` (this very audit tree, `handoff/sweep22/` and
`handoff/sweep23/AUDIT_batch*.md`, `HANDOFF.md`, `BUGS.md`, etc.) is inside `COPY_DIRS` and
travels unscrubbed on every publish cycle.

The docstring at lines 31-33 — "The snapshot is scrubbed as well. It carries bucket names,
quota counts, progress numbers and finding summaries; it carries no keys, and `_scrub` refuses
anything credential-shaped even if a future edit puts one in the state dict by accident." — is
literally true (it says "the snapshot", i.e. state.json) but is easy to misread as a blanket
claim about everything `publish.py` ships, when `sync_tree()`'s much larger payload sits
entirely outside that guarantee. **Recommend**: either run `_scrub`-style regex scanning over
every file `sync_tree()` copies before `git add -A`, or add an explicit doc note at the top of
`sync_tree()` clarifying that only `state.json` is content-scrubbed and the rest is a named-file
allowlist relying on the source tree itself never carrying a credential.

`publish.py:262 — VERIFIED` — non-atomic shared-file write, confirmed: `render_page()` writes
`docs/index.html` with a bare `open(PAGE, "w") ... f.write(html)` (lines 262-263), no tmp+
`os.replace`. Contrast with `write()` just below it (lines 283-290) which writes `state.json`
correctly via `tmp = STATE_JSON + ".tmp"` + `os.replace(tmp, STATE_JSON)`. A GitHub Pages
client (or the git working tree itself, mid `git add`) can observe a partially-written
`index.html`; a crash mid-write leaves it truncated. Minor additional note: the tmp name here
(`STATE_JSON + ".tmp"`, fixed, no PID/thread) doesn't follow `silence.write_json`'s newer
PID+thread-qualified tmp-name convention, so two concurrent `publish.py` invocations against the
same export tree could collide on the temp file — lower risk since the standard workflow runs
one `--loop` instance, but worth using `silence.write_json`/`replace_retry` here for consistency
with the rest of the codebase's now-established pattern (see `silence.py:250-284`'s docstring on
the 2026-08-25 sweep that fixed twelve other such sites).

Everything else in `publish.py` is sound: `export_root()`'s throwaway-directory refusal
(lines 74-123) is careful and well-reasoned; `git()`'s env stripping of `GITHUB_TOKEN`/`GH_TOKEN`
(lines 179-196) is correct; `push()`'s fetch-rebase-before-push (lines 293-343) fails loudly to
stderr rather than swallowing, and aborts a failed rebase rather than forcing.

---

## dashboard.py

**SPECIAL FOCUS confirmed: `dashboard.py:362` is the correct line for the "stalled" flag.**
```python
361:        out.append({"metric": k, "now": v, "delta": delta,
362:                    "minutes": round(span), "stalled": delta == 0 and span >= 10})
```
This is inside `movement()` (lines 314-363). Traced the logic end to end:
- `row` is the current reading; `hist` is loaded from `state/dashboard_history.json`, the new
  `row` appended, then trimmed to the last 24h / 2000 entries and written back atomically
  (`silence.replace_retry`, line 346) — correct.
- `window = now - 30*60`; `older = [h for h in hist if h["at"] <= window]`;
  `base = older[-1] if older else (hist[0] if hist else {})`.
- On the very first-ever reading, `hist == [row]`, `older == []`, so `base = hist[0] == row`,
  giving `delta == 0` for every metric but `span == 0` (`< 10`), so `stalled` is correctly
  `False` — no false "stalled" alarm on startup.
- Before 30 minutes of history exist, `base` falls back to the oldest surviving sample
  (`hist[0]`), so `span` grows toward the true elapsed time since start; once `span >= 10` a
  genuine `delta == 0` correctly reads as stalled.
- Once 30+ minutes of history exist, `base` becomes the most recent sample older than the
  30-minute window, so the delta is measured against a ~30-minute-old baseline as the docstring
  (lines 314-324) describes.
No bug found here — the flag tests exactly what its comment claims (unchanged value AND enough
elapsed time in the comparison window to trust that "unchanged" means "actually stalled," not
"not enough history yet").

I also note lines 386-391 (inside `metrics()`, an unrelated bad-JSON-line handler) contain a
comment reminiscing about a *different*, already-fixed labelling bug ("The old label said
`dashboard.py:336` while sitting at 362 -- m81's drift"). This is likely why an earlier queue
conflated the two and cited :338 — that comment is about `metrics-badline` note-tag history, not
about the `stalled` flag itself. Distinct code, worth not re-conflating again.

**New finding — `dashboard.py:122-126` — MEDIUM — VERIFIED — per-bucket quota failure is
silently dropped from the page with no visible error, unlike every sibling failure path.**
```python
121:        for bucket, m in sorted(seen.items()):
122:            try:
123:                st = router.model_status(m)
124:            except Exception:
125:                silence.note("dashboard.py:model_status")
126:                continue
```
If `router.model_status(m)` raises for one bucket, that bucket is simply omitted from `out` —
no `{"bucket": ..., "windows": [], "worst": 0.0}` placeholder like the outer handler
(`quotas()`'s own `except Exception as e` at lines 143-146) produces for a total failure. The
operator dashboard panel (`panelQuota` in the embedded JS) will just show one fewer row, which
reads as "that provider currently has no listed bucket" rather than "that provider's status
check is broken" — the opposite of the "fail loud, not silent" doctrine the rest of the file
follows (see the `jobs()` docstring at lines 171-193 explicitly calling out fault isolation "so a
single unexpected value... would raise all the way out... and be caught only at the HTTP layer").
Recommend appending an explicit error-state row for that bucket instead of `continue`.

**`dashboard.py:301 — LOW — UNVERIFIED severity, but flagged per Hard Rule 0 instructions —
diagnostic display cap, not a data-loss truncation.**
```python
300:        f = json.load(open(os.path.join(STATE, "failures.json"), encoding="utf-8"))
301:        out["swallowed"] = sorted(f.items(), key=lambda kv: -kv[1])[:6]
302:        out["swallowed_total"] = sum(f.values())
```
Top-6 of the swallowed-failure-type counts for the "Overwatch" panel. This is a ranked
truncation of an ordered listing, which the letter of Hard Rule 0 flags — but `swallowed_total`
preserves the true sum alongside it, and this is a small live UI panel (5s poll, 30s TTL) meant
to surface the biggest offenders, not an entity/page/chunk/source roster being permanently
decided. I read `watch()` (lines 280-305) in full; the finding count itself (`openf`,
lines 290-296) is explicitly uncapped per the file's own 2026-08-24 comment ("ALL open findings
-- a monitoring cap ruled a truncation"). I flag `:301` for completeness per instructions but
assess it as a bounded diagnostic preview, not a rule violation in the load-bearing sense.

**`dashboard.py:64-67`, `RE_ROLL` regex and `catalog.py`/dashboard `_num()` — CLEAN.** No caps,
no truncation of entity/source listings elsewhere in the file. `_library()` (lines 239-277),
`_watch()`, `metrics()` (lines 366-413) all iterate their full input with no `[:N]` on real
data other than the two items above. `metrics()`'s tail-read (`tail_bytes=250_000`, docstring
lines 366-371) is explicitly scoped as "recent past, not an archaeology dig" for an
append-forever ledger — not a roster/entity truncation, matches the project's own stated
distinction between diagnostic tail-reads and entity-listing caps.

Overall: **dashboard.py is otherwise clean.** No two-writer-contract violations (its one shared
write, `movement()`'s history file, correctly uses `silence.replace_retry`); no other swallowed
failures that hide state from the operator; HTML/JS half is inert display code, verified against
the state shape the Python half actually produces (spot-checked `panelMovement`, `panelQuota`,
`panelWatch`, `panelStandards` against their respective builder functions — field names match).

---

## zfighters.py

**`zfighters.py:476-477 — LOW/MEDIUM — VERIFIED — non-atomic write to a data file with a known
external reader.**
```python
476:    with open(OUT, "w", encoding="utf-8") as f:
477:        json.dump(out, f, indent=1, ensure_ascii=False)
```
`OUT = data/Z_FIGHTERS.json`. Bare `open(path, "w")` + `json.dump`, not `silence.write_json`/
`replace_retry` — the exact "truncate-then-fill" pattern `silence.write_json`'s own docstring
(`silence.py:250-265`) describes as the class of bug fixed elsewhere in the 2026-08-25 sweep.
Confirmed via grep that `src/pantheon.py` reads `Z_FIGHTERS.json` (only other reference in the
codebase). This is a manually-invoked, single-writer, infrequent script rather than a
ThreadPoolExecutor worker, so the live race window is small — but a crash or Ctrl-C mid-`dump`
leaves the file empty/truncated, and `pantheon.py` would then read a corrupt or empty result
with no indication anything went wrong (unless it wraps the `json.load` itself, which is
outside this batch). Recommend switching to `silence.write_json(OUT, out)`.

The rest of the file — the fifteen hand-scored Z Fighter assay sheets, `compute()`, `main()`'s
ranking/printing — is straightforward data with cited provenance tags (`[wiki]`/`[canon]`) per
axis; no logic bugs found, no other caps (the roster and per-fighter axis dict are fixed, small,
by-hand data, not a truncated slice of a larger set).

---

## wh40k.py

**`wh40k.py:230-231 — LOW — VERIFIED, same class as zfighters.py:476.**
```python
230:    with open(OUT, "w", encoding="utf-8") as f:
231:        json.dump(out, f, indent=1, ensure_ascii=False)
```
`OUT = data/WH40K_ASSAYS.json`, same bare-write pattern. Unlike `Z_FIGHTERS.json`, grep found
**no other module reading `WH40K_ASSAYS.json`** — it appears to be write-only / consumed only
by a human running `--full`, or not yet wired to a reader. Lower risk than the zfighters.py
instance since there's no confirmed second consumer today, but the same fix (`silence.write_json`)
would bring it in line with the rest of the codebase's now-standard pattern.

Rest of the file (four Chaos Gods + the Emperor, hand-scored under the presence thesis) is
clean: no caps, no swallowed exceptions (the file has none at all — appropriate, since it's a
deterministic, no-I/O-except-the-one-write computation).

---

## cosmography.py — CLEAN

Pure math/derivation module, zero file I/O, zero exception handling needed or present. Read in
full (283 lines). Traced `census()` → `validate()` end to end: every multiplication is visible,
`validate()` correctly refuses a physically-impossible census (Type III count > galaxy count,
Type II > star count, Type I > habitable-world count, extant civs > life-bearing worlds,
`KARDASHEV_MIX` not summing to 1.0) and raises rather than silently clamping or returning a
degraded result — this is exactly the "fail loud" pattern the rest of the codebase aspires to.
No caps on any roster (there is no roster here — it's a numeric derivation). No shared-file
writes. Nothing to report.

---

## descending_ladder.py — CLEAN, one minor unguarded edge case

Pure physics module (187 lines), zero file I/O. `rung_for_length()` (lines 85-95) was traced
carefully:
```python
85: def rung_for_length(metres):
89:    if metres < PLANCK_LENGTH:
90:        return FOLD_RUNG, "Below the Fold"
91:    best = DESCENDING[0]
92:    for r in DESCENDING:
93:        if metres <= r[3]:
94:            best = r
95:    return best[0], best[2]
```
`DESCENDING`'s length column (`r[3]`) is strictly decreasing across the list (1e6 down to
Planck length), so the loop correctly finds the smallest-length rung still `>= metres` —
i.e. "round up to the nearest characteristic scale that contains you." Verified against several
manual traces; behaves as intended.

**UNVERIFIED / minor — no domain guard for `metres > 1e6`.** If called with a size above the
Continental rung's edge (e.g. planetary or larger, which is genuinely out of this module's
stated domain — "the rungs below Planet"), the loop never updates `best` past its initial value
of `DESCENDING[0]` (Continental), so the function silently returns "Continental" for anything
from continent-scale up to arbitrarily large, rather than raising or returning a sentinel
indicating "out of range, use the ascending Ladder instead." Not traced to an actual call site
misusing it in this batch (no caller of `descending_ladder` module is in this batch), so I can't
confirm it's actually exercised out-of-domain anywhere — flagging as a latent footgun rather
than a live bug.

`transgression_bits()` and `shrink_report()` were both traced against their own "CORRECTED
2026-08-20" comments (lines 163-172) explaining a prior bug (pricing against the wrong physical
law) and the fix (density/Schwarzschild-based pricing) — the current code matches the comment's
description of the fix. No discrepancy found.

---

## catalog.py

**`catalog.py:64-67 — LOW — VERIFIED, but a declared/self-reporting display cap, not a data-loss
truncation.**
```python
61:    missing = [r["name"] for r in populated if r["name"] not in sources_with_books]
62:    if missing:
63:        print(f"\nPopulated sources with NO books yet ({len(missing)}):")
64:        for n in missing[:30]:
65:            print(f"  - {n}")
66:        if len(missing) > 30:
67:            print(f"  ... and {len(missing) - 30} more")
```
`missing` itself (line 61) is computed in full over every source, no cap. Only the console
`print` loop is capped at 30, and the header on line 63 already prints the true total
`len(missing)`, with an explicit "...and N more" if truncated. This is a CLI display
convenience over a full, correctly-computed list — it does not hide or discard any data, and
the true count is stated twice. Flagging per instructions since it matches the letter of
`[:30]` truncating an ordered roster-of-sources listing, but assessed as compliant with the
Rule's actual intent (nothing is silently decided not to exist).

`cmd_search` (lines 70-76) is uncapped — returns and prints every match. `cmd_address`/
`cmd_read` (lines 79-98) look up a single address, no truncation applies. No shared-file writes
in this module at all (it's read-only against `catalog.json`/`config.yaml`/`data_roll`) — no
two-writer-contract concern. No swallowed exceptions — the file has no try/except; a bad
`config.yaml` or missing `catalog.json` key raises normally, which is correct for a CLI tool.

Overall: **catalog.py is clean** apart from the declared, self-reporting CLI display cap above.

---

## Coverage recorded

`sweep_plan.record('run23', [...])` was run for all seven files per instructions (see command
output in the session; not duplicated here).
