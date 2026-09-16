# sweep60 batch03 audit

Modules read in full, uncapped: `src/pipeline.py` (3656 lines), `src/weave_index.py` (730),
`src/feats_index.py` (628), `src/reference.py` (497), `src/recover_folder_records.py` (380),
`src/navtree.py` (335), `src/propagation.py` (254), `src/catalog.py` (167). Total 6,647 lines,
all read top to bottom, no sampling.

Overall impression: this batch is unusually heavily self-audited already. Nearly every
function of any complexity carries an inline history of a bug found and fixed, with the
reasoning and measured evidence attached. I could not find a new instance of Priority 1
("a check that cannot fail") or Priority 2 (fail-open guard) that wasn't already caught and
fixed by the codebase's own prior sweeps, with one partial exception noted below (Finding 3,
reported as unsure). What I did find are two verified Priority 3/4-class issues, both narrow.

---

## Finding 1 — stale line-number citation, `src/weave_index.py:225-228` (VERIFIED)

```python
225	    NO BYPASS PARAMETER (order dae0f99306db). This read `def _records_sig(fresh=False)` and
226	    this line promised `fresh=True` as an escape hatch from the memo, and NOTHING ever passed
227	    it -- the only two call sites in the tree, :111 and :288, are both bare. A documented
```

The comment claims `_records_sig()` has exactly two call sites in this file, at lines 111 and
288. I verified this by locating every call to `_records_sig()` in the file as it stands now:

- line 123: `sig = _records_sig()[1] if cacheable else None` (inside `designations()`)
- line 330: `files, sig = _records_sig()` (inside `load_records()`)
- line 462: `files, sig = _records_sig()` (inside `staleness()`)

That is three call sites, not two, and neither cited line number (111, 288) lands on an actual
call site — line 111 falls inside `designations()`'s own docstring prose, not code. `staleness()`
(which contains the third call site) is dated later in its own commentary (orders `d1709d8e757d`
and `9e884802918e`, discussed as 2026-09-09 work), so it looks like this citation was written
before `staleness()` existed and was never revisited when a third call site was added — exactly
the kind of drift this codebase's own convention (cite by symbol/order, not by line, "because a
line number here has already gone stale twice") exists to prevent, and this comment did not
follow that convention for itself.

Impact: documentation-only. The function takes no parameters today, so "both bare" is still
trivially true of all three call sites; the substantive claim being wrong (2 vs. 3) doesn't
change any behavior. Worth a fix only because a future reader trying to verify "nothing calls
this with `fresh=`" by checking two cited spots would silently miss the third.

## Finding 2 — dead branch in `source_binding()`, `src/feats_index.py:306-308` (VERIFIED, within this file's call sites)

```python
304	    hosts = hosts if hosts is not None else host_to_sources()
305	    for h, srcs in (hosts or {}).items():
306	        if source_name in srcs:
307	            if str(h).startswith("pages:"):
308	                return "pages"
309	            if str(h).startswith("doc:"):
310	                return "doc"
311	            return "bound"
```

`host_to_sources()` (lines 188-190) filters out every `pages:`-sentinel host before returning:

```python
188	    for src, host in (wh or {}).items():
189	        if isinstance(host, str) and host and not host.startswith(_PAGES_SENTINEL):
190	            out[host.lower()].append(src)
```

Both call sites of `source_binding()` in this file pass `hosts = host_to_sources()` (or its
direct result) as the `hosts` argument — `feats_for_source()` at line ~367 passes `host_map`
(itself `host_to_sources()`'s return), and `binding_report()` at line ~467 passes
`host_to_sources()` directly. Since `out` (and therefore every `hosts` dict reaching
`source_binding()` from within this file) can never contain a key starting with `"pages:"`, the
`if str(h).startswith("pages:"): return "pages"` line inside the loop is unreachable from either
call site in this module.

This is not a correctness bug: `source_binding()` still answers "pages" correctly for a
`pages:`-sentinel source, because when the loop above finds no match at all (which is guaranteed
for a pages-sentinel source, since it was filtered out of `hosts`), the function falls through to
re-reading the raw `WIKI_HOSTS.json` file directly (lines ~315-328) and classifies the source
from the unfiltered value there, which does correctly detect the `pages:` prefix. So the final
answer is right; the in-loop check is simply dead weight that could mislead a future reader into
thinking the loop path handles the pages case. (The parallel `doc:` check at 309-310 is *not*
dead — `host_to_sources()` does not filter `doc:` hosts, only `pages:` ones — so only the pages
branch inside the loop is unreachable, not the whole conditional.)

I did not check whether some caller *outside* this file's batch passes `source_binding()` a raw,
unfiltered hosts dict (that would make the branch reachable); within this batch's scope, it is
dead in both call sites.

## Finding 3 — "fail-closed" characterization worth a second look, `src/weave_index.py:129-145` (UNSURE)

```python
127	    try:
128	        recs = records if records is not None else load_records()
129	    except Exception:
130	        silence.note("weave_index-designations-load")
131	        # THE FAILURE IS NOT CACHED (order 75307186e12a). ...
...
143	        # Leaving `_DESIGNATIONS` untouched means the next call retries. The empty set is still
144	        # returned to THIS caller, which is the fail-closed answer for one call (an unknown
145	        # designation set splits nothing and merges nothing new); what it must not become is the
146	        # corpus's standing answer.
147	        return set()
```

The comment calls returning an empty designation set "the fail-closed answer." But by this same
module's own stated risk asymmetry (its file header: "Merging two entities INVENTS a composite
being that never existed... Splitting one entity in two only leaves two thinner records... When
uncertain, split" — merging is the expensive/dangerous direction), an empty `known` set actually
pushes in the opposite direction from safe: `continuity_of()` (line ~161-174) can never match
anything against an empty set, so `norm()` (line ~177-196) never appends a `"@continuity"` suffix
and just strips every parenthetical outright — which is precisely the behavior that folds
`"Thor (Earth-616)"` and `"Thor (Earth-1610)"` onto the same normalised key, i.e. it produces
*more* cross-continuity collisions, not fewer.

I think the comment's own final clause is doing the real work and is defensible on a narrower
reading: this module only ever produces *candidates* for a later, model-driven adjudication step
("What this produces is CANDIDATES, not rulings" — the file's own header) and the raw name
(parenthetical intact) is preserved in each stored attestation, so a downstream reviewer can still
see and correctly reject a spurious cross-continuity match. So "merges nothing new" is arguably
true in the sense that this module itself never merges anything, only proposes candidates — but
calling the result "fail-closed" is still an odd label for a fallback that measurably increases
the false-candidate rate in the direction the module's own header prices as expensive. I'm not
fully confident this rises to a real defect (the failure is explicitly not cached, so it is
transient and self-correcting, and the actual fusion risk is deferred to a later gate this module
doesn't own) — flagging as worth a second opinion rather than a confirmed bug.

---

## What I checked closely and found clean

- `pipeline.py`'s two-writer contract (`write_record` / `write_record_catalogue`, the
  `_merge_top_keys` / per-entry-fold machinery, `_entry_pair_key`'s provable non-shrinking
  surplus-carry math, `save_state`'s three-way CAS merge, `gate_done`/`land_json`/`_landed`
  verdict plumbing across all eight phases) — extensively self-documented with measured
  incident histories, and I re-derived the load-bearing claims (e.g. the "surplus is provably
  <= len(unpaired)" argument in `write_record_catalogue`) by hand rather than trusting the
  comment; they check out.
- `pipeline.py`'s band-gate regexes (`clean_band` vs. deliberately-laxer `ceiling_band`),
  `valid_scale_note`'s four-gate feat filter, and the `phase_entrypass` topic/subroom
  sentinel-vs-absent handling (`unclassified`/`none`) — internally consistent, no contradiction
  found between the docstrings and the code.
- `navtree.py`'s `audit()` self-consistency check (children's `n` should sum to parent's `n`) is
  a genuine, non-tautological check — `n` (a counter) and `k` (a child-key set) are built by two
  independently-updated data paths inside `build()`'s per-world loop, so a real future edit to
  one without the other would be caught; it isn't a case of the same computation feeding both
  sides of an assertion.
- `propagation.py`'s Dijkstra (`shortest`), the `observed_mark` two-clock design (vertical
  ascension vs. lateral arrival), and its documented-dead trailing `return 0` — the docstring's
  own claim that the loop always returns before falling through checks out arithmetically
  (`ascension_years(1) == 0.0`, and `lag >= 0` is guaranteed by the earlier guard), so that dead
  line is already correctly diagnosed as unreachable by the code's own comment; not a new
  finding.
- `reference.py`'s calibration gate in `main()` (`calibrated = not outside`, folded into the
  return code) is the fixed version of a historical "check that couldn't fail" the file's own
  comment describes (dropped exit code that used to make a drifted benchmark exit 0); the current
  code does carry the verdict out through `rc`, verified by re-reading the whole flow.
- `recover_folder_records.py`'s shortfall/collision counters, the `already`-populated write
  guard (fails closed toward "leave it alone" on an unreadable file), and the final
  `1 if denied else 0` exit code — consistent, no gaps found.
- `catalog.py` — small and clean; the `load_catalog`/`cmd_address`/`cmd_read` "absent vs. empty"
  and rc-on-miss fixes are consistent throughout `main()`'s dispatch.

No caps, silent truncations, or `[:N]`-style slicing on stored/reported data were found in this
batch beyond ones already flagged and fixed by the codebase's own prior orders (e.g. the
`[:400]` description cap and `_STOPNAMES`/short-key rules in `weave_index.py`, both already
moved out of the stored index and into match-time filtering, correctly, per their own comments).
