# AUDIT batch 15 — sweep36

Modules: local_agent.py, overwatch.py, silence.py, custodes.py, grounding.py, cosmography.py,
descending_ladder.py, scale_theories.py, repass_bands.py

All nine read in full (not skimmed from docstrings). Findings below; several sections are
"read, nothing found" and that is a real result.

---

## overwatch.py — MAJOR

**`_ask()` requests a context window that is neither config's nor stable, contradicting the
"one runner, one context" doctrine the rest of the tree enforces — and the structural check
meant to catch this (verify_math S19ab) cannot see it.**

Anchor: `overwatch.py:357-359`

```python
nc = 4096 if len(prompt) + len(system) < 11000 else 8192
got = P.ask(R.config(), system, prompt, schema, timeout=300, num_ctx=nc, tag="overwatch")
```

`config.yaml:82` sets `num_ctx: 12288`. `gpu_lane.py`'s own header table, measured 2026-08-24,
names **overwatch** explicitly as one of nine standing jobs sharing the one Ollama daemon on
the one card, and lists the cost of a context mismatch as "asking for a num_ctx not resident:
240 s+, never completed" — because "Ollama serves a resident model at ONE context size. A call
asking for a different `num_ctx` needs the runner torn down and rebuilt." `local_agent.py`
(this same batch) was fixed today for exactly this shape — it used to hardcode 8192 against
config's 12288, and the fix comment says explicitly: "every local-agent task named a window the
daemon did not have resident and paid for a runner teardown+rebuild." `standards.py`'s probe had
the identical bug (asked for 512) and is cited as the reason `verify_math` section 19ab now
exists: "no Ollama request body hardcodes a context window," pinned so "a THIRD site cannot
appear quietly."

`overwatch._ask` is that third site, still open. It never reads `config.yaml`'s `num_ctx` at
all — it derives 4096 or 8192 from the combined character length of the prompt and system text,
per SLICE (7000 chars), so within one `review()` pass across several slices of one module the
requested window can itself change slice-to-slice, in addition to differing from whatever the
daemon has resident for the standing prose jobs it is documented to share the card with.

**Why S19ab misses it.** The check (`verify_math.py:2737-2770`) walks every module's AST for the
literal shape `{"options": {"num_ctx": <int literal>}}` and only flags a bare `ast.Constant`
int. `overwatch.py` never builds that dict itself — it passes `num_ctx=nc` as a keyword argument
into `pipeline.ask()`, which builds the request body internally as `"num_ctx": num_ctx or
c.get("num_ctx", 6144)` (`pipeline.py:390`), a `BoolOp`, not a `Constant`. So the exact
"structural, so a third site cannot appear quietly" promise the check's own comment makes
(`verify_math.py:2725`) does not hold for this idiom — any caller of `pipeline.ask()` (or
`P.ask`) that names an explicit `num_ctx` differing from config's is invisible to S19ab. This
should be reported as a QUESTION as well as a finding: `pipeline.ask()`'s own docstring says
`num_ctx` is deliberately "SIZED TO THE CALL, not a generous default" for VRAM reasons, and
`pipeline.py:981`/`pipeline.py:1372` (its own synthesis/entrypass calls) and `magnitude.py:903`
do the identical thing — so "derive num_ctx from config, always" and "size num_ctx to the call"
are two live, contradictory doctrines in this codebase, and S19ab enforces only the first
against only one AST shape. Whether `overwatch.py` specifically should be moved onto config's
window, or whether the whole per-call-sizing idiom needs an S19ab-visible allowlist, is a
judgment call above this audit's pay grade — but the check's claimed universality is not true
today, and `overwatch.py` is live, undetected evidence of that gap.

---

## local_agent.py — MINOR (x2)

Heavily hardened module (five previously-fixed gate bypasses documented in its own comments,
audit trail for both accepted and refused patches, blast-radius cap, halt-check on entry). Two
residual issues found on a close read:

**1. The blast-radius budget is charged before the outcome is known, contradicting its own
comment.** Anchor: `local_agent.py:650-664`.

```python
# The cap is charged AFTER the allow/deny checks and BEFORE anything is read or written, so
# a refused path costs no budget and an accepted one cannot exceed it.
_ok, _why = _blast_ok(full)
...
original = open(full, encoding="utf-8").read()
if original.count(find) != 1:
    return _settle({"applied": False, "error": ...})       # refused, but ALREADY charged
if not apply:
    return _settle({"applied": False, "staged": True, ...})  # staged, ALSO already charged
```

`_blast_ok` runs before the find-string uniqueness check and before the `--no-apply` staged
path, both of which can refuse/no-op *after* the charge. The comment claims "a refused path
costs no budget" — true only for the denylist/allowlist/protected-region refusals that precede
the charge; a model that repeatedly proposes a patch whose `find` string doesn't match
verbatim (a plausible, even expected, failure mode for a small local model per
`_achievement`'s own docstring) burns real blast-radius budget on every miss, and a
`--no-apply` survey run burns the same budget for patches that never touch disk at all. Neither
is what the comment describes. Low severity — the cap is generous (`MAX_FILES_PER_RUN=8`,
`MAX_PATCHES_PER_RUN=24`) and erring toward tripping the cap early is the safe direction, but
the comment and the code disagree about which outcomes are free.

**2. A failed-revert ALARM is dropped when the turn budget runs out.** Anchor: `local_agent.py:830`
(the `unreverted` list) vs `local_agent.py:896-899` (the turn-budget-exhausted exit).

The "no tool calls" exit path (`local_agent.py:857-861`) correctly surfaces `unreverted` into
`out["ALARM"]` and `out["error"]`, with an extensive comment explaining why this matters ("Every
alarm in the world is worth less than the one number the scheduler actually looks at"). The
turn-budget-exhausted path a few lines later does not:

```python
out = {"ok": False, "error": "turn budget (%d) exhausted" % MAX_TURNS,
       "patches": patches, "tool_calls": tool_calls_seen}
out.update(_achievement(patches, apply))
return out
```

No reference to `unreverted` here. `out["ok"]` is already `False` so the exit code (`main()`:
`0 if out.get("ok") else 1`) is still correct — this is not a silent-success bug — but if a
revert failure happens on a late turn and the model keeps calling tools until `MAX_TURNS` is
hit, the printed JSON and the returned dict lose the specific "module X may be half-written on
disk, restore by hand" detail that `t_propose_patch` already computed. The independent
`escalation.SAFETY` call inside `t_propose_patch` (`local_agent.py:718-721`) still fires
regardless of this gap, so the plant-wide halt chain is not compromised — only this function's
own reporting is incomplete on this one exit path.

---

## silence.py — MINOR, and the flagged fix verified good

Read hardest, per the brief. The two handlers called out as edited today —
`_handlers`'s parse-failure except (`silence.py:124-134`) and `instrument`'s parse-failure
except (`silence.py:486-498`) — both now correctly call `note()` **and** print to stderr naming
the file (`os.path.basename(path)` / `base`), and both are counted in the audit's own totals via
the returned/skipped-module bookkeeping rather than silently returning `[]`/continuing with no
trace. This matches the file's own stated discipline ("a file this audit cannot read is not a
file with no handlers") and I could not find a way in which either handler still swallows the
failure class silently. Confirmed fixed, not a residual defect.

One small, genuinely minor observation while reading the rest of the file:

**`replace_retry` only retries/records `PermissionError`; any other `OSError` from
`os.replace` (e.g. `EXDEV` on a cross-device rename) propagates uncaught.** Anchor:
`silence.py:339-348`. This is not a silence violation — an uncaught exception is loud, not
quiet, which is this module's whole preference — but it means `write_json`'s promise ("Never
raises on a denied replace") is narrower than it reads: it only covers the specific denial mode
this project has actually hit (a Windows reader holding the target open). Worth a `note()` +
generic `except OSError` if a non-Windows deployment or a network-mounted `state/` directory is
ever in scope; not urgent today since every caller in this tree runs on the one Windows machine
the whole file's comments are keyed to.

Everything else in `silence.py` — `swallow`, `digest_of`/`_digest_or_unreadable`'s
None-vs-UNREADABLE split, `replace_if_unchanged`'s compare-and-swap, `write_json`'s per-PID/TID
tmp name, `note()`'s atexit/flush-cadence bookkeeping, the rewriter's `_ensure_import` anchor —
read clean against their own docstrings' claims. No further findings.

---

## custodes.py — read, nothing found (one already-self-flagged non-issue)

`convene()`'s `"covers_every_reading"` field (`custodes.py:340-349`) is a guarantee that is true
by construction (`half` is defined as `max(1.96*sd, max|v-consensus|)`, so it can never read
`False`) — but the code's own comment already says exactly this ("this is a GUARANTEE being
published, not a check being run... it is true by construction... and cannot fail... must not
be mistaken for verification"), names the fix that would make it a real check (report whether
the *1.96·sd band alone* covered every reading, before the explicit widening), and defers it
to `NEXT_STEPS` on purpose. Not reporting this as a fresh finding since the module already found
and disclosed it; flagging only so the coverage record shows it was seen and re-checked, not
missed.

`dof_coverage()`'s one-to-one claim (10 degrees of freedom, 10 Custodes) verified true by direct
count against `DEGREES_OF_FREEDOM` and `CUSTODES`. `_merge`-adjacent arithmetic (`prior_share`,
`_ATT_BASE`/`ATTESTATION_QUALITY` derived from `assay.ATTESTATION_FLOOR` rather than
hand-copied) reads correctly against its own docstring's claims. No defects found.

---

## grounding.py — read, nothing found; the flagged truncated-denominator defect is FIXED

Checked directly per the batch guidance ("verify whether it is still there"). It is not.
`classify_text(text, top=None)` (`grounding.py:125-174`) defaults to the whole field —
`scores.most_common(top)` with `top=None` returns every grounding, not a truncated head.
`classify_source` (`grounding.py:177-253`) calls it with no `top` override, computes
`total = sum(s for _, s in ranked)` over that full, untruncated list, and sets
`runners_up = ranked[1:]` (whole field minus the winner) plus a `groundings_scored` count so a
reader can see the denominator was the whole field. The `cap` parameter (origin-entry
truncation) now raises `SystemExit` on any non-`None` value rather than silently truncating.
`main()`'s "contested cosmogonies" diagnostic list (`grounding.py:295-308`) is explicitly
uncapped with a comment citing the exact prior mistake (`low[:5]`) this batch was told to watch
for. This matches `genre.classify_text`'s sibling fix and the extensive changelog docstring
checks out against the code as written. No residual truncation found anywhere in this module.

---

## cosmography.py — read, nothing found

`validate()`'s physical-impossibility guards (Type III ≤ galaxies, Type II ≤ stars, Type I ≤
habitable worlds, extant civilizations ≤ life-bearing worlds, `KARDASHEV_MIX` sums to 1.0) are
reachable, not tautological — computed by hand against the current constants (`STANDARD` size
class, `GALAXIES_DEFAULT`): Type III occupancy comes out ≈6% of galaxies, comfortably under the
ceiling, so the guard is currently slack but not dead — it is linear-scaling-invariant across
`SIZE_CLASSES` (every stage of `census()` is a straight multiplication, so the occupancy ratios
`validate()` checks do not change with `size_class` or a caller-supplied `galaxies` override;
they only move if `KARDASHEV_MIX` or the `F_*` constants themselves change), which is a property
of the model, not a bug — a future edit to those constants is exactly the case this guard exists
to catch, and it can fail. `KARDASHEV_MIX` verified to sum to exactly `1.0` as declared.
`kardashev_to_magnitude`'s "round down to the highest band whose Ruin edge is met" loop reads
correctly against `assay.BAND_EDGES`/`LADDER`'s expected ascending order. No findings.

---

## descending_ladder.py — read; one QUESTION (orphaned module), no code defect

Edited today per the batch brief. The two fixes visible in the file's own comments — the
top-of-range mislabelling in `rung_for_length` (previously fell through to "Continental" for
anything above 1e6 m instead of refusing) and the `NUCLEAR_DENSITY` duplicate-constant merge
between `shrink_report` and `transgression_bits` — both check out against the current code:
`rung_for_length` (`descending_ladder.py:97-122`) now returns `(None, None)` above the top
edge, and both functions read the single module-level `NUCLEAR_DENSITY`, no stray `1e17`
literal remains. Re-derived `transgression_bits`' worked example by hand (70 kg compressed to
1e-10 m: density ≈1.67e31 kg/m³, β ≈ 46.4 bits, nonzero) — matches the docstring's claim that
this used to wrongly return 0.

I considered and rejected, on a second pass, a suspected direction bug in `rung_for_length`'s
interior binning (it resolves a length to the *smallest* rung threshold still ≥ the value,
which looked at first like "rounds up" rather than "rounds down" to the nearest tier). On
reflection this is the physically correct convention for a *containment* ladder — a structure
is classified by the smallest binding scale that can still hold something of its size, not the
nearest order of magnitude — so I am not reporting it; flagging the reasoning here in case a
future reader wants to check it against the charter text this module is proposing to extend.

**QUESTION, not a defect:** this module has **zero callers anywhere in `src/`.**
`grep -rn "import descending_ladder"` across the whole repo matches only
`handoff/run35/checks_M3.py`, a *proposed, unadopted* verify_math check (its own header says
"these are PROPOSALS... this agent does not own those files and did not add them there") — not
a production call site. The module has no `if __name__ == "__main__":` block either, so it
cannot even be run standalone for a report. `liveness.py`'s own dead-code scan (run live,
2026-08-27) independently confirms this: `shrink_report()`, `transgression_bits()`, and
`rung_table()` are all reported `dead — NEVER RUNS — no caller anywhere in src/`. All the
physics — the Fold, the descending rungs, the Schwarzschild/degeneracy transgression pricing —
is real, cited, and internally consistent, but none of it currently reaches any Assay, any
generated volume, or any other module's output. This may be entirely deliberate (a charter
extension proposal awaiting adoption, per its own docstring's framing — "Proposed extension to
Vol. I.3"), but as written today it is inert.

---

## scale_theories.py — confirmed dead, per the batch brief

Batch brief: "believed imported by nothing — verify before reporting." Verified: `grep -rln
"import scale_theories\|from scale_theories"` across the whole repository returns **zero**
matches, in `src/` or anywhere else. No `if __name__ == "__main__":` block. `liveness.py`'s live
scan confirms all four public functions (`bulk_export_beta`, `growth_strike`,
`penetration_pressure`, `surviving_theory`) as `dead — NEVER RUNS`. `THEORIES`, the dict holding
the four candidate shrink-physics theories and their `falsified_by` verdicts, is read only by
`surviving_theory()` — itself uncalled — so it never reaches anything either.

Only two cross-references exist in the whole tree, both comments, not code:
`descending_ladder.py:49` ("scale_theories.py names the same value as G_NEWTON") and
`tempus.py:46`. Confirmed as fully orphaned, matching `descending_ladder.py`'s status above —
same finding, same likely explanation (an unadopted charter-extension proposal), reported
separately per the brief's specific instruction to verify this one.

---

## repass_bands.py — read; one MINOR (diagnostic sample vs. Hard Rule 0), and one confirmed fix

**Confirmed fix**, per the proposed check in `handoff/run35/checks_F1.py`
(`check_repass_bands_denominator_is_dynamic`): no hardcoded `"211"` denominator remains;
`main()`'s summary line (`repass_bands.py:98`) reads `f"{len(demoted_sources):,} of
{len(recs):,}"`, deriving the total from the live record count, not a stale literal.

**MINOR — the console preview of what a `--apply` run would demote is capped.** Anchor:
`repass_bands.py:102,108`:

```python
for s, n, b, sn in kept_entries[:14]:
for s, n, b, sn in demoted_entries[:8]:
```

Both are explicitly labelled samples ("SURVIVORS", "a sample of what was carrying a
Magnitude") and the true totals are printed in full just above (`len(kept_entries)`,
`len(demoted_entries)`, plus a full `Counter` breakdown by band at line 106-107), so this is not
the disguised-truncation shape Hard Rule 0 is mainly aimed at — nothing is reported as complete
when it isn't. It is flagged anyway because this project has twice already (`grounding.py`'s
`low[:5]`, and `feats._show`, both cited in `grounding.py`'s own comments) walked back an
identical "it's just a diagnostic sample" cap on the grounds that a dry-run preview is exactly
the artifact a person reads before deciding whether to run `--apply` against the whole corpus,
and a truncated preview under-informs that decision. `repass_bands.py` writes no full
accounting to disk in either mode — the only place to see which entries would be (or were)
demoted is this capped console output. Worth the same treatment `grounding.py` got (uncap the
sample, or write the full list to `handoff/`) if this script is still in active use for its
stated purpose; flagged as a question of consistency with established project precedent rather
than a confirmed defect, since a console preview is a different kind of artifact than
`grounding.py`'s persisted contested-cosmogony list.

---

## Modules I could NOT read and why

None. All nine modules in this batch were read in full.
