# run35, wave 2, batch M4 — audit notes

**008b8cbb45e3** — Investigated, no in-repo or on-machine caller found. Grepped all of `src/*.py`
for a subprocess spawn of `genre.py` by literal `"py"`/`"python"` (none exist; `autostart.py` and
every Startup-folder launcher — `Panscriptum.vbs`, `CooldownGuard.vbs`, `SemSearch.vbs` — hardcode
`C:\Users\imarl\miniconda3\pythonw.exe` by full path). Checked Windows Scheduled Tasks: the only
`.py`-executing task on this machine is `RentEngineWeekly`, unrelated, also correctly pinned to
miniconda's `python.exe`. Checked `HKCU`/`HKLM` `...\Run` autostart keys: no Python entries at all.
No `.bat`/`.vbs`/`.vscode` task file anywhere under this repo references `genre.py`. The invocation
was very likely a one-off manual command typed into a shell that had not activated the right
environment, or an external orchestration process outside this checked-out tree — neither
reproducible nor fixable from `src/`. LEFT OPEN, reported.

**02277646a783** — Confirmed against source (line numbers had drifted: the checks now sit at
assay.py:524 and 529, constants at 416/419, not the order's 488/493/414/417, but the shape is
identical). Both flagged branches in `_check_constants` are indeed currently unreachable given
today's correct definitions of `SIGMA_MAX`/`SIGMA_UNKNOWN`. But `_check_constants` is one of the
explicitly protected functions this shift (assay.py's 63-check hardening battery calls it by
name), and these two branches are the guard against exactly the threat model that battery exists
for: a future single-token mutation of the `SIGMA_MAX = SIGMA_BY_ATTESTATION["Disputed"]` or
`SIGMA_UNKNOWN = SIGMA_MAX` lines, independent of the monotonicity check three lines above. Removing
"dead" code here would remove defense-in-depth against corruption of the very constants that make
it dead. Judgment call about deliberate design — LEFT OPEN, not touched.

**3a4e66ed5efb** — DISPROVED as a current defect / already fixed. Read `assay.py:605-629`
(`_rho_doc`) in full: the docstring already contains the exact correction the order asks for —
"The docstring here used to justify that by saying `_check_constants` ... IT DOES NOT AND NEVER
DID" — crediting the real protection to `_rho_doc`'s own stderr announcement plus
`RHO_FALLBACK_REASON`/`correlation_source`, and citing the fixing order `c00cab9d0412` by name. An
earlier agent this shift already closed this. Resolved with no further code change.

**4be547515bd9** — Real fix lies in `src/local_agent.py`, which is on this batch's MUST-NOT-EDIT
list. Confirmed the finding is accurate (the blast-cap escalation catch at the cited site has no
`silence.note`, unlike the sibling revert-escalate site at `local_agent.py:665`), but left open and
unresolved since it is out of scope for this agent.

**54cd47a337dc** — FIXED. `pipeline._pool_answering` (pipeline.py:265) used to re-open
`data/POOL_PROOF.json` and count `verdict == "answers"` itself, with no notion of the file's age,
while `tuning._answering_buckets` (tuning.py:138) did the identical count but correctly compared
the file's mtime against `PROOF_STALE_SECONDS`. Now `_pool_answering` delegates to
`tuning._answering_buckets()` directly, so there is one implementation of "how many buckets answer"
and it is staleness-aware everywhere it is asked. `pyflakes` clean, bare import clean.

**5925b90cb6d0** — Real fix lies in `src/cosmography.py`, not on this batch's owned-file list.
Confirmed the finding (`DEFAULT_SIZE_CLASS`, `KARDASHEV_TYPE_I`, `EARTH_POWER_2020` all lack any
reader in `src/`) but left open, out of scope.

**596493b0b139** — Re-verified: `address_space.citation_card` and `seed_from_card` (lines 210 and
240) still have zero callers anywhere in `src/*.py`. Per this shift's standing instruction (already
reviewed once and deliberately left) and the general no-auto-delete-dead-code rule, left as-is and
reported again rather than removed.

**5faa6da447e1** — FIXED. `cleanup.py`'s eaten-escape guard (lines 85-97) carried
`("_SETTING_META", None)`, which the `if _p is not None` test always skipped — `_SETTING_META`
isn't a name in `cleanup.py` at all, it's `pipeline.py:1204`'s `\b`-fenced regex, reachable through
the module's existing `import pipeline as PL`. Swapped the placeholder for `PL._SETTING_META`, and
added every pattern in `_MARKUP` (lines 62-73, whose first entry opens with the identical `\bWP\b`
escape the guard exists to catch) to the same check. `pyflakes` clean, bare import clean.

**87a01fd3b978** — Real fix lies in `src/withdraw_chapters.py`, not on this batch's owned-file
list. Confirmed the finding (the hand-rolled `CATALOG + ".tmp"` write drops `silence.replace_retry`'s
boolean return) but left open, out of scope.

**8fb51fc68004** — FIXED. `rigor.measure_bit_value(band, module=None)` never referenced `module`
in its body, and no caller (`anchors.py:208`, `verify_math.py:403/663/3525/3531`) ever passed it.
Dropped the parameter; `verify_math.py:407`'s own assertion only checks that `"axis"` is absent
from `co_varnames`, so removing `module` doesn't touch a protected check. `pyflakes` clean, bare
import clean.

**96ebf36510b8** — Real fix lies in `src/context_budget.py`, not on this batch's owned-file list.
Confirmed the four silent `except Exception:` handlers and the file's total absence of a `silence`
import, but left open, out of scope.

**9736a5a73b02** — Owner-ruling territory per this batch's explicit instruction; not changed.
Re-measured live against the current `data/SHARED_STAGE_GRAPH.json` with `propagation.py`'s own
`load_graph()`/`shortest()`: the graph has grown since the order was filed (197 shelves, 3,753
edges, vs. the order's 172/1,087), and today's numbers differ in specifics but confirm the same
shape of problem — `shortest(g, "Left 4 Dead", "Dragon Ball Z")` is 1.126 (matches the order's
1.1258), while the true measured diameter is now 4.99 (`DMs Guild: Heroes of Hell` ↔ `Xanathar's
Guide to Everything`), not the 1.0 the `YEARS_PER_UNIT_DISTANCE` anchor comment claims is "the far
end of the measured range." Reported, not changed — this is a published-constant call for the
owner.

**a5018a0c8ee2** — Real fix lies in `src/verify_math.py` (the shared section-tag numbering), not on
this batch's owned-file list. Confirmed `§20e`/`§20f` are each used twice there (verified via grep)
but left open, out of scope.

**ad730acf0b18** — FIXED (docstring only; dead branch left in place). Confirmed live:
`propagation.ascension_years(1) == 0.0`, so once `observed_mark`'s `lag < 0` guard passes, the
loop's very first iteration (`rung == LADDER_HEIGHT` down to 1) always satisfies `lag >=
ascension_years(rung)` at the latest by rung 1, and the trailing `return 0` after the loop is
unreachable. Per the no-auto-delete-dead-code rule this line was not removed; instead the
docstring was corrected to say plainly that the honest `[^0]` comes solely from the `lag < 0`
guard, and the unreachable line is now commented as such so the next reader doesn't mistake it for
a second `[^0]` path. `pyflakes` clean, bare import clean.

**b635a4818c81** — Real fix lies in `src/compress_store.py`, not on this batch's owned-file list.
Confirmed `store()` discards `silence.replace_retry`'s boolean return and reports success
unconditionally, but left open, out of scope.

**cbb921d34442** — FIXED. `rigor.py`'s `measure_bit_value` docstring cited `verify_math.py:382-384`
as what pinned the 2026-08-25 code correction; that range is the unrelated Jensen-gap check. The
real pin (`measure_bit_value` vs. `band_resolution`) lives in section §20f, which the same
docstring already separately credited for the *worked-example* half of the fact. Reworded so both
halves are credited to the one stable section tag instead of the wrong line number, matching the
"cite by tag, not by line" pattern this shift already used elsewhere. `pyflakes` clean, bare import
clean.

**d5ab260d8f71** — Real fix lies in `src/verify_math.py` (the citation itself), referencing
`src/publish.py` (also not owned). Confirmed `verify_math.py:3322`'s comment points at the
credential-scanner regex instead of the actual standards computation at `publish.py:330-331`, but
left open, out of scope.

**dc14fdc767ce** — Real fix lies in `src/verify_math.py` (a third duplicated `§19s` tag), not on
this batch's owned-file list. Confirmed both blocks (metrics-ledger-timestamp and
prose-interlocks) still carry `Section 19s`, but left open, out of scope.

**e3a52d3f20b5** — FIXED. `tempus.apparent_lag_years` returned `{lag_years, note}` on the no-path
branch and `{distance, lag_years, path, note}` on success — a caller reading `r["path"]` or
`r["distance"]` unconditionally would `KeyError` on exactly the branch most likely from real data.
Now both branches always carry all four keys (`distance`/`path` are `None`/`[]` when there is no
path), matching the "ONE RETURN SHAPE, ALWAYS" fix already applied to `entity_match.candidates`.
`verify_math.py:245-246`'s docstring-substring check on `"arrival_years"` is unaffected. `pyflakes`
clean, bare import clean.

**e3a69ceb5857** — Real fix lies in `src/derivation.py:333` and `src/profile.py:20`, both on this
batch's MUST-NOT-EDIT list. Confirmed via grep both still say "74 bits"/"74-bit" against the real
89-bit, 8-field address; `address_space.py`'s own header (line 31) already carries the corrected
figure and a note that it must not go stale again. Left open, out of scope.

**f842daaba5c5** — Real fix lies in `src/feats.py`'s `_QUANTITY` regex (line 750), not on this
batch's owned-file list, even though the downstream consumer (`magnitude.py:233` →
`assay.axis_score`) is owned. Confirmed live: the pattern `x\s*10\^?(\d+)\s*` requires the `^`
(when present) to sit directly against `10` with no space, so `"3 x 10 ^ 9 megatons"` fails the
exponent group entirely and `_QUANTITY.search` instead matches starting at the bare `"9"`,
recording `value: "9"` — nine orders of magnitude short, exactly as reported, and it reaches
`magnitude.quantity_scores` → `assay.axis_score` unflagged. Left open, out of scope.
