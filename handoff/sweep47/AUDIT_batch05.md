# SWEEP 47 -- BATCH 05 AUDIT

Repo: `C:\Users\imarl\panscriptum-library-kit`. Audit only -- no source files edited.

## Coverage

All 9 assigned modules read in full, every line, no sampling:

| module | lines | coverage |
|---|---|---|
| src/standards.py | 2247 | full |
| src/generate.py | 834 | full |
| src/estate.py | 692 | full |
| src/address_space.py | 525 | full |
| src/feats_index.py | 437 | full |
| src/style_audit.py | 338 | full |
| src/runguard.py | 303 | full |
| src/scale_theories.py | 174 | full |
| src/repass_bands.py | 156 | full |

Total: 5,706 lines, matching the brief exactly.

## Already-open work orders: verified, none stale

Every work order the brief listed as already open was checked directly against the current
source. All still describe the code as it stands today; none is fixed. Two are worth noting
because reading the code confirms them precisely:

- **address_space.py: `8fb33a0204c4` / `be9e9f089d62`** (shelfmark omits star) -- confirmed by
  direct inspection: `shelfmark()`'s format string prints hyperverse, xenoverse, metaverse,
  multiverse, universe, galaxy, planet -- seven of the eight `FIELDS` -- with no `star` field
  anywhere in the returned string.
- **feats_index.py: `c8dc624e4e02`** (unbound host reads as no-feats) -- confirmed: `if not
  hosts: return []` at `feats_for_source` produces the identical observable result as "this
  source genuinely has no attested feats," the exact conflation `host_to_sources()` two
  functions above was rewritten to refuse.

One item is **already fixed** and should not be re-worked:

- **generate.py: `4ed4041c3b78`** (limit-zero read as no-limit) lists `src/generate.py:589` as
  one of three surviving sites. Current code at that location (`if args.limit is not None:
  pending = pending[: args.limit]`, line 603) already uses the correct guard, and the comment
  directly above it cites this very order number as the fix. The other two sites named in the
  order (`catalogue_web.py:545`, `feats.py:1622`) are outside this batch and were not
  re-verified here.

## New findings filed (3)

1. **`92fdcb9a8310` STANDARDS_MAIN_JSON_ORDERS_PATHS_ALWAYS_EXIT_0** (LOCAL, MINOR) -- Category
   7 (exit code that always says OK). `standards.py:main()`'s default path correctly computes
   `return 1 if work_orders(state) else 0`, but the `--json` and `--orders` branches both
   hard-code `return 0` regardless of what they just printed -- including `--orders`, the flag
   literally named for "only the breaches." A caller scripting against either flag's exit code
   would never see a breach reported, even though the file itself already knows the correct
   rule two lines below. No current subprocess caller of either flag was found in `src/`, so
   nothing is silently swallowed today, but the inconsistency is internal and mechanical to fix.

2. **`0b6fadca6d7d` STD_TOKEN_FLOW_CHECK_COST_NOT_IN_CONTRACT_AND_TIMEOUT_READS_AS_WEDGED**
   (OWNER, INFO -- a question, per the brief's specific instruction to audit this exact pair of
   functions). `ollama_token_flow()`'s and `check()`'s top-line docstrings do not disclose that
   a call can fire a real GPU generation with up to a 300s timeout, spawn a `tasklist`
   subprocess, and open a live socket to Cloudflare -- `check()`'s stated contract is "measure
   ... against the dashboard's own numbers," which reads as a pure computation over a passed-in
   dict. Separately, `_flow_failure()` reports every plain `TimeoutError` with the fixed,
   confident diagnosis "queue is wedged," but `ollama_token_flow()` takes no lock against
   concurrent callers -- nothing stops two processes (e.g. overlapping mutation-sandbox
   batteries) from both finding the metrics ledger silent and firing simultaneous probes against
   the same single-slot GPU runner, which would time out from ordinary self-contention and be
   reported with the same "wedged" wording as a genuine daemon fault. This is exactly the shape
   of the incident named in this batch's brief. Framed as a question because the file's own
   extensive prose commentary may already be considered the documentation, and "wedged" may be
   intentionally loose language -- but the two already-open orders on this file
   (`74f1bc47da2a`, `728d9e99e9ec`) are scoped to verify_math's specific call sites, not to the
   general contract question of what `check()` promises every caller.

3. **`b11f5e878a6f` ESTATE_EXTERNAL_MODEL_CHECK_MISSING_LATEST_TAG_FOLD** (LOCAL, MINOR).
   `estate.external()` checks `want not in names` (config's model id against `/api/tags`
   names) with a bare membership test, while `standards.py`'s `model_matches()` solves the
   identical problem with an explicit `:latest` fold, after being measured wrong in production.
   `estate.py` never received that fix. Does not misfire today because `config.yaml`'s live
   `model` value (`qwen3:8b`) is already fully qualified, but the check would produce a false
   "MODEL OLLAMA DOES NOT HAVE" `bad=True` fault the moment the config ever names an unqualified
   tag.

## Notes on things considered and NOT filed

- **standards.py's `ollama_token_flow` timeout writing into `state/failures.json`.** This is
  the mechanism behind the brief's cited incident, but the two already-open orders
  `74f1bc47da2a` (VERIFY_MATH_ROWS_RIDE_LIVE_STANDARDS_CHECK) and `728d9e99e9ec`
  (VM_LIVE_STATE_CALLS_LEAK_INTO_THE_FAILURE_LEDGER) already cover the leak into the ledger and
  the battery rows riding a live `check()` call. Not re-filed. What is new above (finding 2) is
  narrower: the contract-disclosure gap and the timeout-vs-contention ambiguity in the function
  itself, independent of verify_math's usage.
- **The Windows `O_APPEND` torn-write race on the shared failure ledger** (two writers, no
  compare-and-swap) is real and was the exact shape hunted for under category 6, but it has
  already been found and fixed elsewhere in the tree: `drill.py`'s
  `a_shared_ledger_keeps_every_row_under_concurrency()` documents the incident (704 of 3,200
  rows destroyed under concurrent writers) and the fix (`silence.append_line` now takes an
  OS-level lock and opens with `O_BINARY`). `drill.py` is outside this batch; not re-verified in
  full, but the fix is visible from its own docstring.
- **style_audit.py's `main()` always returning 0 in normal (non-`--self-test`) mode**, even when
  the printed report flags entries "OVERUSED"/"OVER (target...)". Considered under category 7,
  but not filed: this file is explicitly documented as a manual report tool ("Run it on the
  pilot before scaling. Run it again after every few hundred chapters"), no caller was found
  that reads its exit code, and unlike `standards.py` it never establishes a "nonzero on
  findings" convention anywhere in the file for the always-0 path to contradict. Low confidence
  this is a defect rather than the intended shape of a lint-style report; left as an observation
  rather than a filed order.
- **`scale_theories.py`'s five unused physics constants** and the **duplicate-constants**
  question are already fully covered by open orders `01695fe3ef26` and `a78d5cd748b2`, verified
  against source (all five constants declared once, at their own definition, and read nowhere).
- **`address_space.py`**, **`feats_index.py`**, and **`runguard.py`** were read in full and every
  substantive issue found matches an already-open order exactly (verified by comparing the
  order's own `what` text against the current code at the cited lines). No gaps found between
  what the orders describe and what the code currently does.

## Categories from the hunt list: what turned up

- **(1) could-not-measure as confident value**: none new; `standards.py`'s many `_dropped`/
  `UNMEASURED` mechanisms already handle this correctly and are extensively self-documented as
  having been fixed after being found broken.
- **(2) silent truncation**: none new; every `[:N]` site found in this batch's files either
  carries an explicit marker/count (compliant) or is already named in an open order
  (`fe99e57e1993`, `3dd5b6caef38`/`189532cbf41a`).
- **(3) check that cannot fail**: none new found beyond what's open.
- **(4) guard that fails open**: `runguard.py`'s deliberate fail-open on a corrupt guard is
  already filed as a question (`70f66fbd98aa`).
- **(5) drifted comment/citation**: none new found; this file family is unusually diligent about
  correcting its own stale comments in place, with dated commit history left in the comments
  themselves.
- **(6) two writers, no CAS**: the one instance found (`state/failures.json`'s ledger) is already
  fixed via `silence.append_line`'s lock, per `drill.py`.
- **(7) exit code always OK**: **finding 1** above (`standards.py --json`/`--orders`).
- **(8) shared mutable resource untouched in contract**: **finding 2** above (`ollama_token_flow`
  / `check()`), filed as a question per the brief's instruction.
