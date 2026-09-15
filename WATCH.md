# OVERWATCH

round 531  ·  last run 2026-09-14 22:10

## Structure

- modules that will not import: **0**
- files that will not parse: **0** of 304,847 inspected (deep scan as of round 529)
- catalogued sources with no host: **7** Curious DM Investigations (the Sharkin), Genuine Fantasy Press (Forgotten Secrets), JMBrew, Kobold Press (Midgard Heroes Handbook, Midgard Worldbook), Super Energy Apocalypse 1 & 2, aurora_mods (Way of the Inkmaster), and 1 more
- on the roll but never catalogued: **6** HAWX, Heaven's Lost Property, Lost Mines of Phandelver, Twilight Imperium, major live-action Disney films, the Witch Tradition

## What the model found in the code

**13 open** (3 high). Newest first.

- **assay.py** `assay` — [HIGH] Computes a Moth Number but does not include the M_a term
  - says: Compute a Moth Number: 𝔄 = M_a + (sum w_i * s_i) / 10
- **address.py** `slugify` — [HIGH] Truncates to 60 characters
  - says: Mint a slug from a label. NOT TRUNCATED -- see below.
- **coverage.py** `measure` — [HIGH] measure() raises SystemExit on failure, which is not the same as measuring
  - says: measure() is a function that measures something
- **audit.py** `audit_invariants` — [MEDIUM] audit the invariants but with a critical off-by-one error in the calculation of the rate for synthesis-level failures
  - says: audit the invariants
- **assay.py** `floor` — [MEDIUM] the attestation floor if recognised, otherwise 0.30
  - says: the attestation floor
- **assay.py** `_interval` — [MEDIUM] The docstring mentions two components contributing to variance, but the code may not correctly implement the variance propagation as described.
  - says: Half-width of the honest error bar, in BAND units, by variance propagation.
- **assay.py** `_attestation_sigma` — [MEDIUM] Returns a value that is clamped to SIGMA_MAX, but the function's name and docstring suggest it should return the dispersion and recognition status based on the attestation.
  - says: -> (the dispersion this call will use, whether the GRADE was recognised).
- **assay.py** `_rho` — [MEDIUM] Delegates to `axis_correlation.rho`, which may not be the same as the measured correlation between two Measures as described in the docstring.
  - says: Measured correlation between two Measures. -> float in [-1, 1].
- **assay.py** `_rho_source` — [MEDIUM] Returns a string that includes the 'degraded' status and the reason for degradation, but the function's name and docstring suggest it should provide a provenance stamp for the correlations, not the degradation status.
  - says: -> a one-line provenance stamp for the correlations behind an interval.
- **custodes.py** `main` — [MEDIUM] returns 1 if _faults else 0
  - says: A TABLE FAULT IS A NON-ZERO EXIT, NOT ONLY A PRINTED LINE
- **feats.py** `main` — [MEDIUM] returns 1 if the roll failed, otherwise 0
  - says: the sibling branches in this same file already do it: `--hosts` twenty lines up returns `1 if _HOSTS_DENIED else 0`, and `resolve_hosts`'s own docstring promises "main() exits nonzero on it". `--roll` was the one place the pattern was never applied, even though `roll()` has always returned exactly the counters needed.
- **feats.py** `wiki_source` — [MEDIUM] ReNone of the findings are valid. The code correctly computes `wiki_source` using `reads_as_wiki` as described. There are no defects of fact in this slice. The repeated entries in the findings list were due to a formatting error in the response. The correct answer is an empty list. The code does not have any issues where it does something other than what it claims. The `wiki_source` variable is properly computed using the `reads_as_wiki` function, and there are no other defects of fact in the provided code slice. The repeated findings were a result of an error in generating the response, not actual issues in the code. The code is sound and does not contain any defects of fact as per the given criteria. The findings list should be empty. The code correctly implements the intended functionality without any discrepancies between the code and its claims. The response should be {
  - says: Answered by `reads_as_wiki` rather than recomputed here, so the cache-staleness check above and this mining path can never disagree about what kind of corpus a host is.
- **health.py** `return 1 if reopen_stranded(dry=not a.go) is None else 0` — [MEDIUM] return 1 if the result of reopen_stranded is None else 0
  - says: return 1 if the result of reopen_stranded is None else 0

---

Written by `src/overwatch.py`. Structure is checked every round; the model reads modules that changed first, then whichever has gone longest unread. A finding stays open until the file it points at changes.
