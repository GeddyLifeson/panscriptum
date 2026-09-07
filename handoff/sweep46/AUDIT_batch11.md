# run46 batch 11 -- AUDIT

Modules read end to end, every line: `src/overnight.py` (1784), `src/silence.py` (1043),
`src/identity.py` (727), `src/endpoint.py` (577), `src/tiers.py` (492), `src/sweep.py`
(365), `src/catalogue_aurora.py` (324), `src/audit.py` (271). 5,583 lines, all read directly
by this session (no sub-agents).

`silence.py` is the atomic-write layer the whole project routes shared-state writes
through. Its three claimed changes were verified against the live code: `write_json` now
does `flush()` + `os.fsync(f.fileno())` inside the same `try/except` that already discarded
the temp and re-raised on a failed dump, so a failed fsync is handled identically to a
failed `json.dump` (no new behaviour for callers); `_close_quietly`'s `except OSError` now
calls `note("silence.py:fd-not-closed")` instead of a bare `pass`; and
`replace_if_unchanged`'s two refusal branches file under distinct names
(`cas-target-unreadable` vs `cas-target-changed`), matching `replace_retry`'s existing
`replace-denied` / `replace-failed` split. All three hold on the executable line.

No committed secret or credential was found in any of the eight modules.

## FILED

### STALE_CITATION_OVERNIGHT -- MINOR -- LOCAL -- order `5ed00985ce04`

`overnight.py` carries several line-number citations into other modules, written in prose
that reads as a current fact (unlike this file's many *other* citations, which are
explicitly marked "was", "used to say", or otherwise flagged as historical). Verified
against the live tree 2026-09-07, all four have drifted:

- `running()`'s docstring (~line 201) cites `publish.py:168-172` for "`publish.py` computes
  the published page in its own process" -- that content is now `publish.py`'s
  `render_page()`, at ~line 1229. Lines 168-172 are `EXPORT_OWN_DIRS`, unrelated.
- `identity_refresh_cycle()`'s docstring (~line 459) cites `allsweep.py:170` as "the only
  automated caller" of `identity.py --refresh`. The only `identity.py` reference left in
  `allsweep.py` is now at line 248 (`Verifier("continuity inventory", ["identity.py"], ...)`);
  line 170 is unrelated verifier-tail-truncation prose.
- `main()`'s comment (~line 1315) cites `autostart.py:389-420` for "`autostart.py --watch`,
  which polls `supervisor_alive()` and calls `start_supervisor()`". Those two calls are
  actually at `autostart.py:435` and `:463` -- outside the cited range, which is mid-docstring
  prose about the `stale()` vs `exit_if_stale()` choice.
- The same comment block (~line 1327) cites `autostart.py:402-407` as carrying "the same
  shape" (bind `codewatch = None` on an import failure). That pattern is actually at
  `autostart.py:424-428`; 402-407 is plain prose with no code in it.

No behavioural effect -- these are comments -- but a reader chasing any of the four numbers
lands on unrelated code, which is precisely the failure this project's own
"cite by symbol, not by line number" lesson (invoked repeatedly elsewhere in this same file)
exists to prevent.

### STALE_CITATION_TIERS -- MINOR -- LOCAL -- order `e866d1520c16`

`tiers.py`'s `deliberate_joins()` docstring cites `weave.py:519`, `pipeline.py:2401` and
`cosmology_graph.py:209` as the sites of the sibling "WHOLE list -- Hard Rule 0" markers on
the same shared-evidence key, and states these were re-checked against the live files on
2026-09-01 (replacing three *earlier*, also-stale citations of :478, :1795 and :86). Verified
against the live tree 2026-09-07: all three have drifted again -- the marker is now at
`weave.py:306` (not 519), `pipeline.py:2905` (not 2401), and `cosmology_graph.py:131` (not
209). Notably, `cosmology_graph.py:131` itself repeats the stale `weave.py:519` citation
inline, so the drift has propagated into a second file's comments.

This is exactly the rot this file's own docstring names as the reason other citations in
this project were converted from line numbers to symbol-based tags; this one site was
refreshed by hand once (2026-09-01) rather than converted, and had already gone stale again
within a week. No behavioural effect -- prose only.

## QUESTIONS (not filed -- genuinely ambiguous, both readings offered)

**`silence.py`'s own silent-handler count includes two of its own unmarked, reasoned
exemptions.** `_unlock()`'s `except Exception: pass` and `_digest_or_unreadable()`'s
`except FileNotFoundError: return None` both fail `_handler_is_observed()` (no
health/log/note/re-raise/bound-name-use in the body), so `python src/silence.py`'s own
count classifies them as "silent". Both are in fact deliberate and reasoned in nearby prose
(`_unlock`: "the OS drops it at close anyway... not worth a ledger entry"; explicitly
contrasted by `_close_quietly`'s docstring one function below it. `_digest_or_unreadable`:
`FileNotFoundError` is the documented "absent" case, distinct from the `UNREADABLE`
sentinel the same function returns for a real read failure two lines later). Neither carries
the `_ = "silence-exempt: ..."` marker idiom used for equivalent reasoned exemptions
elsewhere in this tree (e.g. `identity.staleness()`'s `OSError` branch). `instrument()`
correctly never rewrites these (`SKIP_FILES = {"silence.py", "health.py"}`), but `audit()`/
`main()`'s COUNT has no such skip, so silence.py's own report is quietly polluted by two
handlers that are silent by design rather than by omission.
Reading A: working as intended -- the count is an honest literal count of handlers that
don't call a recorder, and a reader is expected to recognise `file=silence.py` rows as
self-referential noise (the module is explicitly excluded from `--instrument` for the same
reason, and adding a self-referential `silence-exempt` marker to the tool that defines that
idiom is arguably circular).
Reading B: a gap -- `_handlers`/`audit()` should apply the same `SKIP_FILES` exclusion
`instrument()` already does, or these two handlers should carry the `silence-exempt` marker
like their siblings elsewhere in the tree, so `python src/silence.py`'s printed count is not
quietly off by its own module's unmarked exemptions.
No work order filed -- this is about the audit tool's self-report, not about data loss or a
wrong verdict reaching any caller.

**`write_json`'s new `os.fsync()` call can turn a filesystem that doesn't support fsync
(some network/virtual mounts) into a hard write failure where before it silently skipped
durability.** The change is caught by the same `except Exception: _discard_tmp(tmp); raise`
that already wrapped `json.dump`, so behaviour for callers is exactly as documented ("only a
DENIED REPLACE is guaranteed silent" -- a raise on the write side was already the contract).
Reading A: correct and deliberate -- durability against a crash between rename and flush is
worth a hard failure on a filesystem that cannot provide it, and every writer in this project
already tolerates `write_json` raising. Reading B: a latent fragility if `data/`/`state/` is
ever moved onto a mount where `fsync` is unsupported or slow, since every JSON write in the
project now depends on it succeeding. Not filed -- no evidence either way about this
machine's actual mounts, and the module's own docstring already argues for the change with a
measured before/after (5,590/104,810 corrupted-row counts on this exact function's other
hazards).

## COVERAGE

`identity.py`, `tiers.py`, `sweep.py`, `catalogue_aurora.py`, `audit.py`, `endpoint.py` and
`silence.py` are all extensively self-documented with their own prior-fault histories (each
carries dozens of "this used to X, now Y, because Z (order ...)" comments); this pass found
no new instance of blind-probe-as-negative-answer, silent data loss, or an unmarked cap/
truncation in any of the eight modules beyond the two stale-citation findings above. Every
`[:N]` slice, `[:top]`/`most_common(N)` cut, and truncated print in all eight files was
checked against Hard Rule 0 and found either uncapped-with-a-disclosed-"+N more"-marker
(display only, underlying data whole) or a deliberately named, load-bearing display width
(e.g. `tiers.py`'s `_cut()` on the "deliberate joins" table's source-name columns, next to a
column that is explicitly documented as printed WHOLE).

`overnight.py`'s process-liveness sensing (`_proc_lines`/`running`/`_cmd_is_running`/
`_in_this_tree`) was read closely against priority 1 (blind probe as negative answer) given
it is the exact shape this project has been bitten by before: it already returns a
three-state answer (`True`/`False`/`None`-for-blind) at every layer, and every spawn site in
this file (`_guarded_popen`, `run()`, `start()`, the keeper thread, the twin-supervisor
check in `main()`) tests `is None` before truthiness and refuses to start on a blind probe.
No gap found.
