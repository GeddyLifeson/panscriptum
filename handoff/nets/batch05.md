# Proposed drill nets — RUN batch 5 (run #36)

Staged, not applied: `src/drill.py` is owned by another agent this shift. Each net names the
guard it protects and the attack that would defeat it.

---

## NET 1 — `NOT_FILED` may not swallow the categories the module names as unwaivable

**Guard:** `secondopinion.NOT_FILED` (src/secondopinion.py:138-168).

**Why it needs a net.** Order `a32028fe76b7` was filed against a real event: on 2026-08-27
`BLE001`, `S110` and `S112` were added to `NOT_FILED` and reverted the same day. While they were
in, 594 of 1,002 live ruff findings never reached `file_orders()` — and the report kept printing
a healthy-looking page, because waived findings are still counted in the summary line. The
BLE001 waiver cited this module's own docstring as its authority, and the docstring says the
exact opposite twenty lines above the map. Nothing mechanical stopped it, and nothing would stop
it being re-added tomorrow. The module's whole purpose is to be an INDEPENDENT opinion; a filter
that can be widened until it swallows the majority of that opinion is the failure it exists to
prevent, and it is worse than any single finding because the page still reads green.

**The net.** Pure, no subprocess, no network:

```python
def _second_opinion_keeps_its_teeth():
    import secondopinion as SO
    banned = {"BLE001", "S110", "S112"}
    return not (banned & set(SO.NOT_FILED))
```

Register with a reason naming the sentence in the docstring that these three are the named
example of what must NOT be waived.

**The attack that defeats it.** A future waiver of a DIFFERENT large category — `F841`, or a new
ruff rule — is not on the banned list and passes. The banned set is a denylist, and a denylist
only defends the three names somebody already argued about. A stronger form, worth considering
as NET 1b, asserts a SHARE rather than names: run `_ruff` and fail if waived findings exceed,
say, half of all selected findings. That version cannot be walked around by picking a new rule
code, but it costs a ruff subprocess in the drill and its threshold is a fresh parameter, which
this codebase is rightly suspicious of. Recommend NET 1 now, and raise 1b as an owner question.

---

## NET 2 — `discover()` follows continuation and does not stop at the first page

**Guard:** `feats._api_list_all` + its two call sites in `feats.discover` (Hard Rule 0).

**Why it needs a net.** Fixed this shift under order `dc27521160c1`. `discover()` refused a
caller's `extra=` truncation loudly and then truncated anyway one level down: `aplimit=500` and
`srlimit=50` are per-request maxima, and the old code read the `continue` object ONLY to
increment `_CAP_BOUND` before iterating the first page it already had. An entity with 900
evidence subpages mined as one with 500 and looked complete. A measurement of a truncation is
not the absence of one, and the counter made it look handled.

**The net.** Drive `discover()` itself, with `feats.api` and `endpoint.detect` monkeypatched to
a synthetic paginated wiki (restore both in a `finally`):

```python
def _discovery_follows_continuation():
    import feats as F, endpoint as EP
    real_api, real_detect = F.api, EP.detect
    try:
        EP.detect = lambda h: {"mode": "api"}
        def fake(host, params, retries=2):
            if params.get("list") == "allpages":
                off = int(params.get("apcontinue", 0))
                rows = [{"title": "E/Powers %d" % i}
                        for i in range(off, min(off + 500, 1200))]
                d = {"query": {"allpages": rows}}
                if off + 500 < 1200:
                    d["continue"] = {"apcontinue": str(off + 500), "continue": "-||"}
                return d
            return {"query": {"search": []}}
        F.api = fake
        return len(F.discover("x.example", "E")) == 1201     # 1200 subpages + own title
    finally:
        F.api, EP.detect = real_api, real_detect
```

**The attack that defeats it.** Stubbing `_api_list_all` instead of `api` would pass even if
`discover` stopped calling the helper — the net must drive `discover()`, which is why it does.
It is still defeated by a change that adds a THIRD discovery route (backlinks, categorymembers)
that truncates: the net only proves the two routes it exercises. Anyone adding a route must add
an arm here, and that expectation belongs in the net's docstring.

---

## NET 3 — a corrected gate may not stay invisible behind the cache

**Guard:** `feats.mined_under_superseded_gate` + `feats.reads_as_wiki`, consulted by
`evidence_for` before it trusts a `cachekey.load` hit.

**Why it needs a net.** Order `77d88ce737bc`. `page_looks_real` gained `wiki=False` because its
markup layer was refusing the two corpora that are not wikis (443 pages in, 3 through the old
gate, 404 through the corrected one) — and the numbers did not move, because `cachekey.load`
kept returning records mined under the old gate. Measured this shift: 96 cached entities holding
1,399 wrongly-refused pages and ZERO feats between them. **A fix whose effect is cached away is
not in effect** — the fourth property from Hard Rule -1, in the data layer rather than in a
running process. This is the shape the project keeps re-learning and it currently has no net.

**The net.** Pure, over the two predicates — no disk, no network:

```python
def _superseded_gate_hit_is_a_miss():
    import feats as F
    stale = {"pages_refused": {"P": "no wiki markup found at all -- not an article page"}}
    return (F.mined_under_superseded_gate(stale, "doc:a-book")          # non-wiki: invalidate
            and not F.mined_under_superseded_gate(stale, "dc.fandom.com")   # wiki: correct
            and not F.mined_under_superseded_gate({}, "doc:a-book")
            and F.reads_as_wiki("dc.fandom.com")
            and not F.reads_as_wiki("doc:a-book"))
```

The second clause is the load-bearing one: on a genuine wiki that refusal is CORRECT, and
invalidating it would re-mine the same pages to the same refusal on every pass, for ever.

**The attack that defeats it.** The predicate matches the literal substring `no wiki markup`.
A future edit that rewords `page_looks_real`'s third-layer refusal leaves records mined under
the old gate unmatched, and the net still passes because it builds its fixture from the same
literal. The durable form asserts the two agree — call `page_looks_real(prose, wiki=True)` and
require `_SUPERSEDED_GATE_MARK` to appear in the reason it returns, so a reworded refusal breaks
the net instead of silently escaping it. Recommend adding that as a fourth clause:

```python
    and F._SUPERSEDED_GATE_MARK in F.page_looks_real("x" * 5000, wiki=True)[1]
```
