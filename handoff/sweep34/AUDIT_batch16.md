# SWEEP 34 — BATCH 16

Modules read end to end: `overwatch.py` (762), `mutate.py` (715), `handbuilt.py` (487),
`secondopinion.py` (361), `backfill.py` (300), `sweep.py` (258), `style_audit.py` (211),
`catalog.py` (127). 3,221 lines.

Nothing under `src/` was edited. `mutate.py` was read only; it was not run and
`state/MUTATION_ACTIVE.json` was not touched (it was read, and is discussed below).

Every finding below was verified against the source before it was written down. Where a claim
needed a fact off disk (does the tool exist, does this format raise, does that call site exist)
the check that produced it is named.

---

## mutate.py

### FINDINGS

**M1 — MAJOR — the mutation lock is never acquired. `publish.py`'s refusal cannot fire.**

`_lock_acquire` and `_lock_release` are defined and are called from nowhere in this module:

```
186	def _lock_acquire(targets, token):
200	def _lock_release():
```

`grep -n "_lock_acquire\|_lock_release" src/mutate.py` returns only those two definition lines.
`main()` (616-711) builds the sandbox, takes the baseline, runs the targets and removes the
sandbox; it never takes the lock. The only callers in the tree are drill nets:

```
src/drill.py:2184	M._lock_acquire(["a.py"], "t1")
src/drill.py:2186	M._lock_acquire(["b.py"], "t2")
src/drill.py:2191	M._lock_release()
```

which exercise the function directly against a temp `M.LOCK`, and `publish.py:519-526`, which
reads `_MUT.active()` and refuses to push while it is held. So the interlock is proven at both
ends and disconnected in the middle: no run of the current code ever writes the file that
`publish.py` looks for. Four green nets (`lock_is_exclusive`,
`unreadable_lock_counts_as_HELD`, `dead_holder_does_not_block_forever`,
`publish_asks_before_pushing`) sit on top of it, and none of them asserts that a real run
acquires it.

The lock section's own prose (110-129) is written in the present tense — "This lock is how they
know, and `publish.py` refuses to push while it is held" — which is behaviour the module no
longer has. The same is true of `_lock_acquire`'s exclusivity refusal ("a mutation run is
already active ... refusing to start a second"): two `mutate.py --target all` runs can start
side by side today.

Corroboration from disk: the file present right now was written at 19:49, before the 20:56 run,
and records `"targets": ["escalation.py"]` and a dead pid — i.e. it is an orphan left by the
older in-place version. The run in flight wrote no lock.

`_TOKEN_ENV = "PANSCRIPTUM_MUTATION_TOKEN"` (line 130) is referenced nowhere in the tree.

**M2 — MINOR — nothing ever removes a stale lock, and without psutil that is a permanent
publish outage.**

`active()` marks a dead holder's record `stale` and returns `False` (180-182) but leaves the
file in place, and the only remover, `_lock_release()`, is on the path that is never called
(M1). The fallback in `_pid_alive` is:

```
155	            if os.name == "nt":
156	                return True
```

so on a machine without `psutil` every lock on Windows reads as alive forever. Verified here:
`psutil` is installed and `mutate.active()` returns
`(False, {... 'stale': True})`, so the orphan is currently harmless — on a fresh checkout it
would refuse every push permanently.

**M3 — MINOR — `reap_orphans` reports sandboxes as removed without knowing that they were,
and its handler is unreachable.**

```
408	        try:
409	            shutil.rmtree(p, ignore_errors=True)
410	            removed.append(p)
411	        except Exception:
412	            silence.note("mutate.py:reap")
```

`ignore_errors=True` means `rmtree` cannot raise, so `removed.append(p)` runs unconditionally
and the `except` is dead. A sandbox that could not be deleted — the junction case the comment
immediately above spends six lines on — is reported as reaped, and the 154 MB leak this
function exists to stop would be reported as cleaned up.

**M4 — MAJOR — `--check-flaky --no-confirm` always refuses to run.**

```
656	        gates = FAST_GATES
657	        confirm = () if a.no_confirm else CONFIRM_GATES
658	        base = baseline(root, gates=gates + confirm)
...
664	        flaky = flaky_gates(root, base) if a.check_flaky else []
```

`flaky_gates(root, base)` takes its default `gates=GATES`, which is `FAST_GATES +
CONFIRM_GATES`. Under `--no-confirm` the baseline has no `drill` key, so
`sig != base.get("drill")` compares a signature against `None`, is always true, and
`main()` prints "FLAKY GATES — REFUSING TO MUTATE" and returns 3 — after paying the five
minutes to run `drill` that `--no-confirm` was asked for in order to skip.

**M5 — MINOR — `verify_restore`'s docstring describes a job it no longer does, and the check
cannot fail for any reason the code can produce.**

```
329	def verify_restore(path):
330	    """Prove the save/restore cycle is byte-exact BEFORE mutating anything. -> bool.
331	
332	    A restore that does not restore turns a diagnostic into a corruption, on the three files
333	    this project can least afford to corrupt.
```

Since the sandbox rewrite the only caller is `run()` at line 530, and `path` there is
`os.path.join(root, "src", target)` — the throwaway copy. The three live files are never
written at all, so this no longer protects them; `live_file_untouched` does, separately.

On the second question: it can return `False`, but only if a filesystem hands back different
bytes than were just written to the same path through the same two four-line helpers. Every
failure this project actually sees — permissions, a locked file, a full disk — raises out of
`_write`/`_read` and propagates rather than returning `False`. `run()`'s `restored_exactly`
(line 589) has the same shape: it digests what `_write(path, original)` put there one line
earlier, using the same functions.

**M6 — MINOR — "the live tree is never opened for writing at any point" is true of the copied
halves only.**

```
442	    opened for writing at any point.
```

`sandbox()` copies `src/` (447-449) and `state/` (462-468) and junctions the rest:

```
450	    for shared in ("data", "prompts", "reference"):
...	        _junction(os.path.join(root, shared), src_dir)
482	        _junction(os.path.join(root, "output", "index"), idx)
```

A junction is a portal, not a copy: any write by a sandboxed gate to `data/`, `prompts/`,
`reference/` or `output/index` lands in the live tree. I read the three gate commands' write
paths (`import assay, prose_gate, escalation`; `verify_math.py`; `drill.py`) and found none
reachable today — drill's writes go to `tempfile.TemporaryDirectory()` or to `state/`, and its
`data/` uses at 408-409, 1447, 1821, 2350, 2487 are reads. So the guarantee holds in practice
by the gates' good behaviour, not by construction, and `live_file_untouched` would not notice
if it stopped holding: it digests `src/<target>` and nothing else.

### QUESTIONS

- `run()` returns `"capped": bool(limit) and len(muts) == limit` (587). A target with exactly
  `--limit` mutants and nothing dropped reports `capped: True`. Over-reporting in the safe
  direction — deliberate?
- `--limit` truncates `muts` (540-543) with the comment that Hard Rule 0 requires it to say so,
  and it does say so. `_mutations` returns in `ast.walk` order rather than ranked, so nothing is
  ranked-then-truncated. Reading this as compliant; flagging it only so the next sweep does not
  re-litigate it.
- `_mutations` takes `node.lineno` and edits that one line, so an operator that sits on a
  continuation line produces no mutant, and the dedup key `(lineno, description)` (281) drops the
  second of two identical ops on one line. Both silently shrink the mutant set with no count of
  what was skipped. Deliberate simplification, or worth reporting a skip count?
- `main()`'s two `shutil.rmtree(root, ignore_errors=True)` calls (592, 711) do not unlink the
  junctions first, which `reap_orphans` (397-406) documents as the one place in the project where
  getting it wrong deletes `data/`. Windows `rmtree` does not traverse a junction, so this is
  probably only a leaked directory rather than a data loss — but the asymmetry with
  `reap_orphans` is unexplained.

---

## secondopinion.py

### FINDINGS

**S1 — MAJOR — an installed tool that FAILS is reported as `RAN` with a clean result.**

None of the three runners looks at the return code.

```
134	    r = subprocess.run([exe, "check", "--output-format", "json", ...])
137	    try:
138	        rows = json.loads(r.stdout or "[]")
```

`ruff` exits 2 on a bad selector or an unreadable path and writes the reason to *stderr*, so
`r.stdout` is empty, `json.loads("[]")` succeeds, and the function returns `"RAN", []`.
`_detect_secrets` is the same shape (`json.loads(r.stdout or "{}")`, 185) and `_vulture` the
same (an empty stdout yields no parsed lines, 164-175). Downstream, `ran_clean` (220) requires
`status == "RAN" and not findings`, which is exactly what a crashed tool produces, and
`report()` prints "ALL THREE RAN AND ALL THREE FOUND NOTHING. This is the only sentence on this
page that is an all-clear."

The module's own docstring names this failure and guards only the neighbouring case: absence is
a third answer, but *failure* is not — it is folded back into clean. `NOT INSTALLED` itself is
reachable and loud (`_exe` returns None on a missing binary; `report()` prints "<-- NOT AN
ALL-CLEAR. Nothing checked ... from outside."), and `file_orders` queues an
`SECONDOPINION_ABSENT_*` order for it (294-303). That half works.

**S2 — MINOR — four of the nine `NOT_FILED` waivers name rules the scan never selects.**

```
94	RUFF_RULES = "E,F,B,BLE,S110,S112,PLE,PLW,RUF,SIM"
```

`UP031`, `ISC004`, `C408` and `DTZ005` (119, 120, 121, 126) are pyupgrade, implicit-str-concat,
comprehensions and datetimez — none of those prefixes is selected, so those four entries can
never match a finding. Confirmed by running ruff with the module's own selectors: the 30 codes
reported do not include any of the four. The waiver list reads as covering nine divergences and
covers five.

**S3 — MINOR — three different stale numbers for one measurement, in one file.**

```
17	    ruff             449 blind-except + 19 try/except/pass + 12 try/except/continue
113	# has -- 456 blind-excepts is a big number and it is still a real finding
265	    ONE ORDER PER RULE, not per finding. 449 separate blind-except orders would bury
```

Measured today with `RUFF_RULES`/`RUFF_IGNORE` as written in this file: BLE001 492, S110 20,
S112 11, 974 findings total. None of the three prose numbers matches, and 449 and 456
contradict each other.

**S4 — MINOR — the per-code summary is a ranked truncation with no disclosure.**

```
322	        top = ", ".join("%s x%d" % (k, n) for k, n in
323	                        sorted(codes.items(), key=lambda kv: -kv[1])[:6])
```

30 distinct codes were reported today; six are printed and nothing says the other 24 exist.
`file_orders` handles the same shape correctly one screen up — `sites` appends
`" (+%d more)"` (278-279).

### QUESTIONS

- `ran_clean` is not dead: it is called at 338 and by `drill.py:2585`. If it was filed as dead
  earlier in the shift, that order can be closed.
- `_exe` probes with `--version` and swallows every exception per candidate
  (`silence.note("secondopinion.py:_exe")`, 87-88). A tool present but broken enough to fail
  `--version` reports NOT INSTALLED rather than ERRORED. Correct answer, or worth distinguishing?

---

## overwatch.py

### FINDINGS

**O1 — MAJOR — a review that never happened is recorded as a review that found nothing.**

When the GPU is busy and the cloud budget is spent, `_ask` returns `None`:

```
370	        if _LOCAL_BUSY[0] > CLOUD_BUDGET:
...
378	            return None
```

`review()` cannot tell that from a sound slice:

```
423	        for f_ in (got or {}).get("findings", []):
```

and `round_once` stamps the module as read regardless of whether any slice was answered:

```
664	            d = _digest(os.path.join(SRC, m + ".py"))
665	            led["seen"][m] = {"digest": d, "at": time.time()}
```

`rotation()` (511-521) then treats that module as unchanged-and-recently-seen and sorts it to
the back of the stale queue, so an unreviewed module is demoted exactly as if it had been read
clean. The printed line carries a "(GPU busy; ... budget spent)" note, but the ledger — the
thing the next round reads — does not. This is the module's own thesis ("a watcher that stops
watching is the thing this file exists to prevent") landing one layer down.

**O2 — MINOR — two stale `silence.note` line tags.**

```
331	        silence.note("overwatch.py:193")
341	        silence.note("overwatch.py:202")
```

Line 193 is inside `save()`; line 202 is `silence.replace_retry(tmp, LEDGER)`. Neither tag
points at its own site.

**O3 — MINOR — `review()`'s docstring claims a filter it does not apply, and carries a dead
parameter.**

```
412	def review(module, local=True, ledger=None):
413	    """Read one module and return the findings that survive all three filters."""
```

The body applies SEVERE (424) and ANCHORED (426). NOVEL is applied by the caller, at 669
(`if fid in led["findings"]: continue`). `ledger` is never read in the body although 659 passes
it, and `_anchored(module, finding, src)` never reads its `module` parameter either (405-409).

### QUESTIONS

- `write_report` prints `sorted(open_f, ...)[:40]` (572-573). The true open count is printed on
  the line above, so the truncation is disclosed — but there is no "+N more" and this is the
  human-facing work list. Intentional ten-second-read discipline?
- `save()` swallows every failure into `silence.note("overwatch.py:save")` (204-205) and returns
  nothing, so `round_once` continues and reports the round as complete over a ledger that was
  never written. Elsewhere in the tree a denied write is reported as a verdict (see
  `sweep.main`). Deliberate difference?

---

## sweep.py

### FINDINGS

**W1 — MINOR — `load()` has no caller in this module, and its docstring is built entirely on a
call site that no longer exists.**

```
68	def load(path):
71	    THE ABSENT FILE IS THE NORMAL PATH, NOT A FAILURE. The only call site (`:129`) asks for the
72	    evidence of every Person-category entry in the library and does no existence check first
```

`sweep()` reads evidence through `cachekey.load` at line 160, not through this function, and
line 129 is blank. `grep` finds no other caller in `src/` except `verify_math.py:3360-3370`,
which imports `sweep` to test `load` against a nonexistent path — and `verify_math.py:3358`
repeats the false claim in its own comment. Contrast `cache_path` directly above (59-65), which
is explicitly documented as callerless and kept on purpose; `load` is not.

**W2 — MINOR — `report()` divides by an unguarded `n`.**

```
195	        bar = "#" * int(38 * f[k] / max(n, 1))
196	        print(f"  {k:<12}{f[k]:>9,}{f[k]/n:>8.1%}  {bar}"
```

Same line: the bar guards with `max(n, 1)` and the percentage does not. Lines 199 and 201
(`f['ranked']/n`, `f['banded']/n`) are unguarded too. An empty rows list raises
ZeroDivisionError in the reporter rather than printing a funnel of zeros.

### QUESTIONS

- The module docstring opens "The corpus holds 17,444 entries classed Persons" while `load`'s
  docstring says the same population is "~45,000 entries". One of the two is stale; I did not run
  the sweep to find out which, because it reads the whole corpus and the library is halted.
- `report` truncates several ranked lists for display — `[:top]` (215), `most_common(10)` (224),
  `most_common(8)` (231). All are reports rather than work lists and the section headers say so;
  not filed.

---

## handbuilt.py

### FINDINGS

**H1 — MINOR — `--full` raises TypeError on the one sheet the module documents as its most
instructive.**

```
478	            for ax in A.WEIGHTS:
479	                d = rec["axes"][ax]
480	                print("   %-15s%5.1f  [%s] %s"
481	                      % (ax, d["score"], d["provenance"], d["cited"][:58]))
```

Zalama's `ruin`, `continuity`, `celerity`, `vector`, `volition` and `discernment` are the string
`"unestimable"` (182-201), and `A.WEIGHTS` contains all eleven axis names (verified). `"%5.1f" %
"unestimable"` raises `TypeError: must be real number, not str` (verified). The JSON artifact
lands before the print loop by design (444-459), so the file is safe — but `--full` cannot
render the sheet whose whole point is that six axes decline to score.

**H2 — MINOR — a stale count in prose.**

```
280	  why_missed="NOTHING missed it -- catalogued, mined, 94,809 chars, 10 clean feats. The only
281	             "one of these four the machine could have assayed on its own
```

`ROSTER` holds nine sheets: The Undertaker, The Internal Revenue Service, Zalama, Molecule Man,
Rune King Thor, The Sentry, The Black Winter, Getter Emperor, Mister Mxyzptlk.

### QUESTIONS

- The module docstring (9-41) documents two entities; seven more were added since. Not a defect —
  but the header now reads as the file's contents and is not.

---

## backfill.py

### FINDINGS

**B1 — MINOR — a comment says "NOT truncated" immediately above the truncation.**

```
187	    # Ranked by article size so the deepest arrive first if this is ever interrupted, but NOT # truncated: every character the wiki lists is a character the library should hold.
188	    missing = sorted(missing, key=lambda t: -sizes.get(t, 0))
189	    if cap:
190	        missing = missing[:cap]
```

`--cap` defaults to `None` and its help says "omit for everything, which is the intended use",
and the result dict reports pre-cap `absent` beside post-cap `queued`, so the truncation is at
least visible. The comment still directly contradicts the two lines under it, and this is the
exact rank-then-truncate shape Hard Rule 0 names.

**B2 — MINOR — the article-size query treats an API failure as "no sizes", silently.**

```
182	        d = F.api(host, {"action": "query", "prop": "info", "titles": ...})
183	        for pg in (d or {}).get("query", {}).get("pages", []):
```

`F.api` answering `None` is exactly what `members()` raises `RosterIncomplete` over, on the
stated grounds that `None` means timeout as often as absence (48-59, 85-90). Here the same
`None` yields `sizes` without those titles, they rank at 0, and under `--cap` they are the ones
dropped. (The `pages`-as-list read is correct: `feats.api` forces `formatversion: 2`.)

**B3 — MINOR — `--audit` prints a ranked slice with no total.**

```
264	        for x in rows[:26]:
```

`audit()` returns every non-Wikipedia source sorted ascending by Persons share; 26 are printed
and nothing says how many were not. `--all` uses the full list, so this is the human-facing view
of the same work list, truncated with no count.

### QUESTIONS

- Several comments in this file have been collapsed onto single very long lines with embedded
  `#` marks (179, 185, 187, 209, 199). Harmless to the parser; it looks like newlines were eaten
  in transit, which is the same class of damage the `_BAD_CHARS` guard at the top exists for.
  Worth a pass, or leave it?
- `backfill_source` opens with `next((p, r) for p, r in records if r["source"] == source)`
  (171). On the `--source` path a name that is not on the roll raises `StopIteration` rather
  than the "no wiki host" style refusal one line below. Deliberate fail-fast?

---

## style_audit.py

### FINDINGS

**Y1 — MINOR — `BANNED` is dead.**

```
34	BANNED = TELLS.ALL_PATTERNS
```

Nothing in this module reads it — `audit()` calls `TELLS.scan(r)` (119) — and `grep -rn BANNED
src/*.py` finds no other reader in the tree.

### QUESTIONS

- `re.split(r"^[◈◈]\s*", text, flags=re.M)` (44) holds the same character twice: both members
  are U+25C8 (verified by codepoint). Harmless as written, and `prompts/system_style.txt:105`
  confirms U+25C8 is the marker the generator is told to emit — so this is redundancy rather
  than a broken match. Was a second glyph intended?
- `--self-test` (183-193) is capable of failing: `ok` requires a non-empty `banned` counter and a
  repeated opening shape, and I traced the fixture to `"NAME is a city"` twice plus at least two
  live tells, so it passes on content rather than by construction.
- `_WATCHED` (35-36) is accurate: `tells.ALL_PATTERNS` is `{**STRUCTURAL, **DISCOURSE}` and
  `tells.scan` additionally walks `LEXICAL + LEXICAL_FICTION`, so the printed count matches what
  is scanned. Checked because the shape invites double-counting; it does not.

---

## catalog.py

No findings. The one truncation in the file discloses itself:

```
64	        for n in missing[:30]:
66	        if len(missing) > 30:
67	            print(f"  ... and {len(missing) - 30} more")
```

and the docstring's stale `PANSCRIPTUM://` example was already removed with a note saying why
(11-15).

### QUESTIONS

- `load_catalog` returns `{}` for an absent catalog (36-37), so `stats` prints
  "Sources with at least one generated chapter: 0" for a catalog that was never written and for
  one that failed to land. Every other reader in this file fails closed on a missing file
  (`load_config`, `load_roll` raise). Deliberate, since zero is the honest answer on a fresh
  tree?
- `main()` is invoked bare at 127 rather than through `sys.exit(main())`, so the process always
  exits 0 — including when `cmd_read` printed "No entry for address". Every other module in this
  batch propagates a return code.

---

## Observed in passing — not this batch's module

At 22:54:50 `src/workorders.py` was unimportable:

```
File "src/workorders.py", line 241
    sys.stderr.write("workorders: queue write lost after %d attempt(s); last refusal was: %s
                     ^
SyntaxError: unterminated string literal
```

A literal newline stood where an escaped one belonged, which is the same transit-corruption class
the `_BAD_CHARS` guards at the top of four modules in this batch exist for. `ls` put the file's
mtime three seconds earlier, and the next attempt imported cleanly, so this was a concurrent
agent's edit caught mid-write rather than a landed defect — but for those seconds every
work-order filing in the tree would have failed, and `file_order` is not something callers
generally expect to raise ImportError. Flagged for whoever owns that edit; not filed as an order,
since it is somebody's in-flight work.
