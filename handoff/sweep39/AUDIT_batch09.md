# run39 — comprehensive source audit, BATCH 09

Modules owned by this batch (taken programmatically from `sweep_plan.batches(16)[8]`), all read
in full, no sampling:

| module | lines |
|---|---|
| `src/foreman.py` | 1715 |
| `src/corpus_db.py` | 767 |
| `src/gpu_lane.py` | 620 |
| `src/ledger_guard.py` | 509 |
| `src/catalogue_codex.py` | 392 |
| `src/hosts.py` | 315 |
| `src/scope.py` | 275 |
| `src/cosmology_graph.py` | 244 |

Every finding below was verified against the current source before it was written down. Two were
verified by *running* the code (§1, §2). Items I could read two ways are filed at the bottom as
QUESTIONS, not findings.

---


> **Severity note.** This audit assessed §1 and §2 as CRITICAL. `workorders.SEVERITY` (`src/workorders.py:89`) offers only `INFO / MINOR / MAJOR / BLOCKING`, and `BLOCKING` is reserved in this tree for publish-halting conditions (`ledger_guard` violations at `workorders.py:864`, `publish.scan_for_secrets` at `:1038`). Both were therefore filed as **MAJOR** with the assessment recorded in the order text, rather than halting the library on an auditor's judgement. Treat them as the head of the MAJOR queue.

---

## 1. MAJOR (assessed CRITICAL) — `gpu_lane._take_slot`: a corrupt slot file is never reclaimed, and every model call in nine standing jobs then pays 900 s

`src/gpu_lane.py:386-394`

```python
rec = _read(path)
if rec is not None and _expired(rec, SLOT_LEASE_SECONDS):
    _remove_retry(path)
try:
    fd = os.open(path, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
except FileExistsError:
    continue
```

`_expired` (`gpu_lane.py:223-229`) opens with the contract this guard defeats:

```python
if not isinstance(rec, dict):
    return True                      # unreadable/corrupt: reclaim rather than strand
```

`_read` (`gpu_lane.py:215-220`) returns `None` for a zero-byte or unparseable slot file. The
`rec is not None` guard therefore excludes precisely the case `_expired` was written to handle,
`os.open(O_EXCL)` raises `FileExistsError`, and the file is skipped forever. Nothing else in the
tree removes it: `_remove_retry` is only ever called from a reclaim path this branch cannot reach.

The state is reachable. `_take_slot` creates the file with `os.open` and only then writes it
(`gpu_lane.py:392-399`); a kill, a crash or a Norton denial between those two statements leaves a
zero-byte `slot.N.json`. The one recovery path — `_expired` — is switched off for it.

**The asymmetry proves it is an oversight, not a design choice.** `foreground_active`
(`gpu_lane.py:259-262`) calls `_expired(rec, ...)` with no `rec is not None` guard, so a corrupt
*foreground claim* IS swept. Only the slots have the guard.

Verified by execution against a scratch LANE directory:

```
before: ['slot.0.json' (zero bytes), 'slot.1.json' (expired, dead pid, well-formed)]
_take_slot -> ...\slot.1.json          # the well-formed expired one WAS reclaimed
after : ['slot.0.json', 'slot.1.json'] # the zero-byte one was left untouched
_read(slot.0)          -> None
_expired(None, lease)  -> True         # the reclaim logic agrees it should go
MAX_SLOTS = 3
_take_slot with every slot zero-byte -> False
```

The last line is the cost. `False` means BUSY, and `lane()` answers BUSY by polling
(`gpu_lane.py:552-566`):

```python
deadline = _now() + SLOT_LEASE_SECONDS      # 900 s
while _now() < deadline:
    slot = _take_slot(label)
    if slot: break
    if slot is None: break                  # unarbitrable -> go now
    time.sleep(_POLL)
```

So `MAX_SLOTS` corrupt files turn every model call in every one of the nine standing jobs into a
fifteen-minute stall, permanently, with nothing on disk expiring and nothing in the ledger. That
is verbatim the outcome order `d316c46b67bd` was filed about and that `_take_slot`'s own docstring
records fixing — "it went on calling this every `_POLL` until `deadline = now +
SLOT_LEASE_SECONDS`, i.e. 900 seconds" — reached through a second door the fix did not close. It
also contradicts the module header's capitalised mandate ("FAIL OPEN, ALWAYS ... a slot that
cannot be created ... all of them end in go ahead anyway").

**Remedy.** Drop the `rec is not None` guard so the corrupt case reaches `_expired`, which already
answers correctly:

```python
if os.path.exists(path) and _expired(_read(path), SLOT_LEASE_SECONDS):
    _remove_retry(path)
```

`_expired(None, lease)` already returns `True`, so no change to `_expired` is needed. Guard on
`os.path.exists` rather than on `rec`, so an absent slot is still not "reclaimed". Add a
`silence.note("gpu_lane.py:corrupt-slot-reclaimed")` on that branch, because a slot file that will
not parse is a fact somebody should be able to see afterwards.

---

## 2. MAJOR (assessed CRITICAL) — the "one physical fact" the GPU slot count was unified into is still restated twice, and the two copies disagree; `read.py` raises at import on `OLLAMA_NUM_PARALLEL=auto`

`src/gpu_lane.py:61-66` and `src/read.py:282-290`

`gpu_lane.py:61-65` states the repair as done:

> ONE PHYSICAL FACT, READ RATHER THAN RESTATED: how many requests the card serves at once is
> `OLLAMA_NUM_PARALLEL`, the daemon's own setting. This was a bare "2" default, and `read.py`
> spelled the same number out a third time as GATE_LOCAL_N -- three constants for one fact with
> no link between them, so raising the daemon's parallelism silently left both gates on the old
> number.

`gpu_lane._slot_count()` (`gpu_lane.py:69-111`) is the hardened parser, and its docstring names the
two defects it removes (order `b54fbcf84962`): a bare `int()` that raises at import on a
non-integer, and `max(1, 0)` silently reading Ollama's own "let the server decide" `0` as ONE slot.

`read.py:289-290` is still the old expression, unchanged:

```python
GATE_LOCAL_N = max(1, int(os.environ.get("PANSCRIPTUM_GPU_SLOTS")
                          or os.environ.get("OLLAMA_NUM_PARALLEL") or "2"))
```

It carries both defects, at module scope, in the corpus reader. Nothing links the two: `read.py`
does not import `gpu_lane.MAX_SLOTS`, and `gpu_lane` does not import `read`. Each restates the
fact the other says has stopped being restated.

Verified by execution:

```
OLLAMA_NUM_PARALLEL=auto   gpu_lane MAX_SLOTS = 2
OLLAMA_NUM_PARALLEL=auto   import read -> ValueError: invalid literal for int() with base 10: 'auto'
OLLAMA_NUM_PARALLEL=0      gpu_lane 2   read 1
```

Row 2 is an ImportError in `read.py` — the module the library's whole throughput runs through — on
a setting the daemon accepts. Row 3 is the "quieter half" `_slot_count`'s docstring describes
("silently serialising the whole library behind a single call, the exact outcome the comment above
says two slots exist to avoid"), live, while the lane in front of it admits two.

**Remedy.** Delete the expression at `read.py:289-290` and take the number from the module that
already parses it safely:

```python
import gpu_lane as _GL
GATE_LOCAL_N = _GL.MAX_SLOTS
```

`gpu_lane` imports only `contextlib/json/os/threading/time` plus `silence`, so this adds no cycle.
If `read.py` must not depend on `gpu_lane`, then move `_slot_count()` into `silence` (or a small
shared module) and have both call it — but two independent parsers of one env var is the state
`gpu_lane.py:61-65` already declares unacceptable.

---

## 3. MAJOR — `corpus_db.age_seconds`'s docstring exists to stop a sixth audit re-deriving it, and five of the six line references it gives are wrong

`src/corpus_db.py:344-351`

```
Say that first because five separate sweep audits have now re-derived it from scratch
(sweep33 batch17, sweep34 batch04, sweep36 batch09, sweep37 batch09, sweep38 batch10 ->
order a25e919309cb). `grep -rn 'age_seconds()'` over the repo finds this def, two prose
mentions in comments at :96 and :722, and nothing else; every real reader takes the value
off `freshness()`'s dict instead -- `_freshness_banner()` at :478 and :491, `main()` at :728
and :733, and drill.py.
```

Checked against the current file:

| cited | what is actually there | where the claim is true |
|---|---|---|
| `:96` | `` `corpus_db.DB` ... left `query`, `age_seconds` and `freshness` all `` | **correct** |
| `:722` | blank line between `return 0` and `if a.serve:` | `:742` |
| `:478` | blank line inside `_freshness_banner`'s docstring | `:498` (`if f["age_seconds"] is None:`) |
| `:491` | `# it is a different kind of wrong from being behind...` | `:511` (`mins = f["age_seconds"] / 60`) |
| `:728` | `# Refusing the serve command outright, rather than...` | `:748` |
| `:733` | `% os.path.join(HERE, "state", "datasette.json"))` | `:753` |

Every wrong one is off by exactly +20, so twenty lines were inserted above `:478` after the
docstring was written and the references were never re-derived. `:96` is before the insertion
point, which is why it survived.

This matters more than an ordinary stale comment because of what the docstring is *for*: it is a
map handed to the next auditor so they do not spend the pass re-deriving that `age_seconds` has no
callers. A map whose coordinates are wrong sends them to `_freshness_banner`'s docstring and
`datasette_metadata`'s denial branch, where there is no `age_seconds` to see, and the seventh audit
re-derives it anyway.

**Remedy.** Re-point to `:742`, `:498`, `:511`, `:748`, `:753`. Better: drop the line numbers and
name the call sites (`_freshness_banner`'s `age_seconds is None` branch and its `mins =` line;
`main`'s no-SQL branch), which cannot go stale.

---

## 4. MAJOR — five stale cross-references in `foreman.py`, two of them load-bearing for a safety argument

All verified against the current files.

**(a) `foreman.py:107-108`** — the DENYLIST argument:

> `--quick` runs only the IMPORT and LINT tiers (allsweep.py:479, :498)

`allsweep.py:479` is `import weave_index as WI`; `:498` is inside a comment about over-banded
entries. The `--quick` gates are at **`allsweep.py:676`** (`if not a.quick:` — VERIFY tier) and
**`allsweep.py:701`** (`if not a.quick:` — ESTATE tier). The *claim* is sound — I confirmed LINT
runs unconditionally before `:676` and only VERIFY and ESTATE are skipped — but the citation
offered as its proof points at unrelated code, and this paragraph is the justification for adding
five modules to the model-patch DENYLIST.

**(b) `foreman.py:113-114`** — the reason `drill` is deliberately NOT added to `_checks_pass`:

> verify_math.py:5504 records a standing rule that verify_math and drill "are not safe to run"
> from an agent context

`verify_math.py:5504` is `for _n20q in _ast20q.walk(_pipe20q):`, part of an AST scan for discarded
`land_json` verdicts. The phrase "not safe to run" occurs at **`verify_math.py:6031`** ("per this
run's rule that verify_math.py/drill.py are not safe to run") and **`:6263`** ("are not safe to run
concurrently -- order c349a51ee2c5"). Off by ~527 lines. This citation is the entire basis for
leaving a known gap in the model lane's checks open, described in the file as "an owner ruling", so
a reader who follows it finds nothing and cannot tell whether the ruling exists.

**(c) `foreman.py:475`** — the kill-target fragment:

> The fragment is "read.py --run", which is how overnight.py:619 actually launches it.

`overnight.py:619` is `return {"name": name, "proc": p, "fh": fh, "t0": time.time()}` inside the
generic launcher. The actual launch is **`overnight.py:1409`**:
`statuses.append(run("read", [os.path.join(SRC, "read.py"), "--run", ...`.

**(d) and (e) `foreman.py:193` and `foreman.py:1506`** — both cite `silence.py:408` for
`write_json`'s pid/thread-qualified temp name. `silence.py:408` is inside `replace_retry`'s
`except OSError` handler. The temp name is built at **`silence.py:511`**, inside `write_json`
(which starts at `:471`):
`tmp = "%s.%d.%d.tmp" % (path, os.getpid(), _th.get_ident())`.

Two references in the same file to the same wrong line, and `foreman.py:1506` uses it as the
template for its own inline temp name — so a reader checking that the shapes match is sent to a
sleep-and-retry loop instead.

*Correct in `foreman.py`, checked and left alone:* `health.py:198-210` (`foreman.py:302`) really
does record the interleaved-writer corruption of `state/failures.json`; `silence.py:_discard_tmp`
(`foreman.py:1514`) exists at `silence.py:534`; `verify_math` §19h (`foreman.py:1463`) exists at
`verify_math.py:1796` and does assert `foreman.py` cannot name the paid counter. All 20 `REMEDIES`
keys were checked against `standards.py` and every one is a real declared standard name — no orphan
remedies.

---

## 5. MAJOR — four stale cross-references in `cosmology_graph.py`, all four in the paragraphs justifying that a cap was removed

`src/cosmology_graph.py:64-66, 116-119`. Verified by `grep -rn "shared_sample" src/`:

| cited | actual | drift |
|---|---|---|
| `resonance.py:157` reads SHARED_STAGE_GRAPH.json | `resonance.py:290` (`path = graph_path or ...SHARED_STAGE_GRAPH.json`) | +133 |
| `resonance.py:146` reads `shared_sample` back | `resonance.py:295` (`"shared": p.get("shared_sample", [])`) | +149 |
| `weave.py:478` writes `shared_sample` | `weave.py:519` | +41 |
| `pipeline.py:1795` writes `shared_sample` | `pipeline.py:2375` | +580 |

`resonance.py:157` is `_isolated = [n for n in nodes if not nbrs[n]]`; `:146` is
`nbrs[b].append((a, -f))`; `weave.py:478` is `resolved, homonyms = resolve(index, groups)`;
`pipeline.py:1795` is `def _chain_landed(CH, out):`.

These four citations are the evidence for the two most consequential statements in the file — that
an undeclared `if w >= 1.0` dropped 71% of pairs while the consumer read them as absent (order
`9861c18b8485`), and that an `< 8` cap on `shared_sample` meant "a ninth shared entity simply did
not exist to anything downstream". Both claims are true; every pointer to the code that proves them
is wrong. **Remedy:** re-point to `resonance.py:290`, `resonance.py:295`, `weave.py:519`,
`pipeline.py:2375`, or name the functions instead of the lines.

---

## 6. MINOR — `foreman.kill_stalled_job` reports "no job is stalled now" when the standard it needs was not measured at all

`src/foreman.py:515-517`

```python
row = next((r for r in rows if r["standard"] == "every running job is advancing"), None)
if not row or row.get("holds"):
    return True, "no job is stalled now"
```

`row is None` means `standards.check(dashboard.state())` produced no row for that standard —
renamed, removed, or its own evaluation skipped — and `row.get("holds")` means it was measured and
passed. Two conditions, one sentence, and the sentence asserts the *measured* one. This function's
neighbours are careful about exactly this distinction — `run_catalogue_gap` (`:862-874`) separates
"the audit is EMPTY" from "no source is short" for the same reason, and `clear_learned_caps`
(`:165-170`) refuses to let an unreadable database read as a healthy zero.

It also returns `did=True`, so `round_once`'s `if did and not getattr(fn, "always", False): break`
(`foreman.py:1584-1597`) stops the remedy list on an answer nobody computed.

The standard name does currently exist in `standards.py:936`+ (checked: all 20 `REMEDIES` keys
resolve), so this is latent rather than live — but it is latent in the shape that is only ever
found after it fires.

**Remedy.** Split the branches:

```python
if row is None:
    return False, ("the standard 'every running job is advancing' was not measured this round, "
                   "so whether a job is stalled is UNKNOWN -- nothing killed")
if row.get("holds"):
    return True, "no job is stalled now"
```

---

## 7. MINOR — `foreman.attempt_patch` reports "GPU busy and no spare pool capacity" for a case where the pool had room and answered nothing

`src/foreman.py:1323-1340`

```python
got = None
try:
    got = R._local(R.config(), PATCH_SYSTEM, prompt, PATCH_SCHEMA)
except Exception:
    silence.note("foreman.py:attempt_patch-local")
if got is None and _pool_has_room():
    try:
        ...
        got = R._ask(R.config(), PATCH_SYSTEM, prompt, PATCH_SCHEMA)
    except Exception as e:
        return {"ok": False, "why": f"model unreachable: {type(e).__name__}"}
if got is None:
    return {"ok": False, "why": "GPU busy and no spare pool capacity; will retry"}
```

If `_pool_has_room()` is True and `R._ask` *returns* `None` without raising, control falls to the
last branch and the round logs "GPU busy and no spare pool capacity" — false on both counts. The
round's operational log is the surface a person reads to find out why the model lane never lands a
patch, and this sentence sends them to look at the pool's headroom, which is fine.

**Remedy.** Record whether the cloud attempt was made:

```python
tried_cloud = False
if got is None and _pool_has_room():
    tried_cloud = True
    ...
if got is None:
    return {"ok": False, "why": ("the local model and the pool both returned nothing"
                                 if tried_cloud else
                                 "GPU busy and no spare pool capacity; will retry")}
```

---

## 8. MINOR — `gpu_lane.status()` promises "every holder, never a sample" and returns a silent partial list

`src/gpu_lane.py:599-620`

```python
def status():
    """What is holding the card right now -- every holder, never a sample."""
    out = {"slots": [], "foreground": [], "max_slots": MAX_SLOTS}
    try:
        ...
        for name in sorted(os.listdir(LANE)):
            ...
    except Exception:
        pass
    return out
```

An exception raised part-way through the loop (a lease file removed by a competitor between
`listdir` and `_read`, a permissions denial on one entry) returns `out` holding whatever was
collected before the raise, indistinguishable from a complete answer. The docstring's promise is
exactly the one that is broken, and the `pass` is the only bare swallow in the module that does not
carry a `silence.note` or a documented fail-open reason — the module's other swallows (`_read`,
`_ensure_dir`, `_alive`, `_remove_retry`) each have one.

**Remedy.** Note the failure and mark the answer:

```python
except Exception:
    silence.note("gpu_lane.py:status-partial")
    out["partial"] = True
```

so a caller can tell "the card is idle" from "I could not finish looking".

---

## 9. MINOR — `ledger_guard.assert_intact` truncates the fault list to six with no marker, in the message that blocks a push

`src/ledger_guard.py:420-423`

```python
ok, problems = verify_chain()
if not ok:
    raise LedgerViolation(
        "the ledger hash chain does not verify:\n  " + "\n  ".join(problems[:6]))
```

`main()` at `:488-490` shows the file already knows this is a cap and defends the split:

> Uncapped. `assert_intact()` prints the first six into an exception message, which is a
> different job; this is the surface somebody reads to go and repair the chain, and a truncated
> fault list is how a second break gets missed behind the first.

The split of responsibilities is defensible; the *silence* of the cut is not. `verify_chain`
appends up to three problems per link (`:387`, `:389`, `:401`), so a chain with three bad links
already overflows six, and the exception text — the only thing a blocked `publish.push()` shows —
stops mid-list saying nothing. Hard Rule 0 accepts a display cut only when something says the cut
happened; `corpus_db._cell` (`corpus_db.py:519-541`, order `6160ef68b229`) is this project's own
ruling on that exact point.

**Remedy** (keep the cap, add the marker):

```python
head = problems[:6]
more = ("\n  ... and %d further problem(s); run `python src/ledger_guard.py` for the full list"
        % (len(problems) - 6)) if len(problems) > 6 else ""
raise LedgerViolation("the ledger hash chain does not verify:\n  " + "\n  ".join(head) + more)
```

---

## 10. MINOR — `ledger_guard.read_chain` silently drops any chain line that will not parse, in the function whose docstring argues against exactly that

`src/ledger_guard.py:358-366`

```python
try:
    with open(CHAIN, encoding="utf-8") as f:
        for ln in f:
            ln = ln.strip()
            if ln:
                try:
                    out.append(json.loads(ln))
                except Exception:
                    continue
except FileNotFoundError:
    return []
```

The docstring (`:342-355`) makes the case at length that "cannot tell" must never be collapsed into
"no chain", and that the blanket `except Exception: return []` was removed for it — and then the
per-*line* handler does the same thing one level down, with no `silence.note` and nothing in the
returned value to say a link was dropped. A half-written last link (the chain is appended to with a
non-atomic `open(CHAIN, "a")` at `:221-222`, so a crash mid-append produces one) vanishes, and
`verify_chain` reports the shorter chain as intact.

A dropped *interior* line is caught, because the following link's `prev` then fails to match
(`:388`). A dropped *final* line is not caught by anything.

**Remedy.** `silence.note("ledger_guard.py:chain-line-unparseable")` on the `continue`, and have
`verify_chain` report the count as a problem: an unreadable link is a hole in a tamper-evidence
mechanism, which is the one thing this file exists to notice.

---

## 11. MINOR — `ledger_guard`'s chain records a CHARACTER count under the key `bytes`, and `verify_chain` prints it as bytes

`src/ledger_guard.py:215` and `:401-402`

```python
"ledgers": {n: {"digest": _digest(_read(n) or ""), "bytes": len((_read(n) or ""))}
```
```python
problems.append("%s SHRANK between link %d and %d (%d -> %d bytes)" % (name, i - 1, i, was, now))
```

`len(str)` on text read with `encoding="utf-8"` is characters. `check_structure` (`:128-130`) uses
the real thing — `len(text.encode("utf-8"))` — against `MIN_BYTES`. The SHRANK test is internally
consistent (chars against chars), so it still detects shrinkage; the defect is that the number
published in the chain and printed to an operator is not the unit it is labelled with, and is not
comparable to the `MIN_BYTES` figure printed beside it by the same CLI run.

Same call also reads each ledger from disk **twice** (`_digest(_read(n))` and `len(_read(n))`), so
a file edited between the two reads gets a digest and a size describing different states.

**Remedy.** Read once, measure in bytes:

```python
"ledgers": {}
for n in sorted(MIN_BYTES):
    _t = _read(n) or ""
    rec["ledgers"][n] = {"digest": _digest(_t), "bytes": len(_t.encode("utf-8"))}
```

Note this changes recorded values, so old links keep the old unit — the SHRANK comparison at the
boundary link will be chars-vs-bytes once. Either accept the one-link discontinuity or add a
`"unit"` key and compare only within a unit.

---

## 12. MINOR — `corpus_db.drift()` calls itself "the exact entry-count gap" and silently undercounts when a record will not parse

`src/corpus_db.py:451-473`

```python
real = 0
for p in glob.glob(...):
    try:
        real += len(json.load(f).get("entries") or [])
    except Exception:
        silence.note("corpus_db.py:drift-record")
gap = None if indexed is None else real - indexed
```

`rebuild()` was fixed for precisely this (`corpus_db.py:116-122`): "This used to be `except
Exception: continue` -- the record was dropped in silence and `n_src`/`n_entry` were then reported
as the corpus TOTALS." `drift()` has the note but not the accounting: nothing counts or names the
skipped files, and `main --drift` prints

```python
print("  indexed %s | records %s | gap %s" % (indexed, real, gap))
```

with no caveat, while `main --rebuild` names every unreadable file in full at `:696-704`. The
docstring's contrast ("an approximation of how wrong the index is would just be a second thing to
be wrong about") is the argument against the state the code is in.

**Remedy.** Collect the names as `rebuild` does, return them as a fourth element, and have
`--drift` print the same FLOOR warning `--rebuild` prints.

---

## 13. MINOR — unmarked display truncations in `cosmology_graph.main()` and `hosts.main()`

Both cut values on the console with nothing saying a cut happened, against this project's own
ruling on that (order `6160ef68b229`, recorded in `corpus_db._cell`'s docstring at
`corpus_db.py:532-536`: house doctrine accepts display truncation *because it is reversible* and
"refuses it when nothing says the cut happened").

`src/cosmology_graph.py:562-564`:

```python
shared = ", ".join(names[:4])
more = f" (+{len(names) - 4:,} more shared)" if len(names) > 4 else ""
print(f"  {w:6.1f}  {a[:24]:26s} <-> {b[:24]:26s}  {shared[:52]}{more}")
```

`names[:4]` is correctly marked by `more`. `a[:24]`, `b[:24]` and `shared[:52]` are not — and the
source names are the whole content of the line. `'Who Framed Roger Rabbit (incl. all content...'`
is the example `corpus_db._cell`'s docstring measured this against. `:574` has the same shape:
`", ".join(s[:20] for s in c[:6])`, where `c[:6]` IS marked by `tail` and `s[:20]` is not.

`src/hosts.py:292`:

```python
print("  %-40s + %s" % (str(src)[:39], ", ".join(hs)))
```

**Remedy.** Reuse the marker `corpus_db._cell` already settled on:
`s if len(s) <= w else s[:w-1] + chr(8230)`. It costs one character of width and makes the cut
visible.

---

## 14. MINOR — `hosts.discover()` silently excludes sources with a roster under four names, in the module that argues an unstated bound is indistinguishable from no bound

`src/hosts.py:165-167`

```python
names = list(by.get(source) or [])
if len(names) < 4:
    return None
```

`work()` returning `None` is dropped by `if not res: continue` at `:229-230`, so the source is
never probed, never counted, and never named. Meanwhile the same function reports its *other*
bound in full (`:255-261`): "an unstated bound is indistinguishable from no bound at all", and
`:223-225` records that "615 speculative probes were withheld across the roll on the day this was
measured and nothing anywhere said so".

The threshold is sound — four names is too thin to score a host against — but `todo` counts these
sources and the summary (`hosts added: N`, `sources with more than one host: X -> Y`) does not
distinguish "probed, nothing held" from "never probed". A source with a three-name roster reads as
a source with no alternative hosts.

**Remedy.** Return a distinguishable sentinel (e.g. `(source, None, 0)`), tally them, and print
`"(N source(s) not probed: fewer than 4 roster names to score a host against: <names>)"` beside the
withheld-guesses line that already exists.

---

## 15. MINOR — `foreman.kill_duplicate_jobs` uses the model-patch DENYLIST as a process-kill exclusion

`src/foreman.py:641`

```python
if p == os.getpid() or job in DENYLIST:
    continue
```

`DENYLIST` is declared at `:97-118` as "Files a model may never edit. Each is either the thing that
would have to be working to detect a bad patch, or the thing doing the patching." Nothing in that
declaration, and nothing in `kill_duplicate_jobs`'s own comment (`:632-640`, which covers only
`overnight` and `autostart`), says it also decides which duplicate *processes* survive.

The effect is real: duplicate `health.py`, `standards.py`, `verify_math.py`, `liveness.py`,
`codewatch.py`, `estate.py` and `drill.py` processes are never de-duplicated, and the coupling runs
the wrong way — the 2026-08-25 addition of five modules to the DENYLIST for *patch-safety* reasons
silently granted those five duplicate-process immunity, with no line anywhere recording that as a
decision. The next module added for patch safety will inherit it too.

Both readings are arguable in isolation (checkers are cheap to run twice, so skipping them may be
harmless), but the coupling being **silent and undeclared** is not arguable: this is one list doing
two unrelated jobs.

**Remedy.** Declare a second constant with its own reason, e.g.
`NEVER_DEDUPED = DENYLIST | {"overnight", "autostart"}` with a comment saying why a checker's
duplicate is tolerable, and use it at `:639-641` so the two memberships can diverge on purpose
rather than by inheritance.

---

## 16. MINOR — `catalogue_codex.slug()` has no caller

`src/catalogue_codex.py:94-97`

```python
def slug(s):
    """The record's identity, derived from the source name. UNCAPPED -- see above."""
    from catalogue_aurora import slug as _slug
    return _slug(s)
```

`grep -rn "slug" src/catalogue_codex.py` finds the def, three comment mentions (`:84`, `:90`,
`:326`), and nothing that calls it. `catalogue_aurora.py:36` imports only `TYPE_CATEGORY, THINGS`
from this module. `main()` uses `record_path()` (`:329`), and `:326` says so explicitly:
"`record_path`, not a raw join on slug()".

Not harmful, but it reads as live machinery: it carries a docstring asserting a Hard Rule 0
property, sits directly under a long comment about the cap it removes, and a reader keeping the
codex and aurora paths in step would reasonably think there are two entry points.

**Remedy.** Either delete it, or do what `corpus_db.age_seconds` (`corpus_db.py:344`) does and open
the docstring with the fact — "NOTHING IN THIS TREE CALLS THIS; `record_path()` is the entry
point" — so the next sweep does not re-derive it. (`corpus_db.age_seconds`'s note that vulture at
min_confidence 90 will not flag an uncalled module-level def applies identically here.)

---

## 17. INFO — `catalogue_codex.main()` writes two roll fields nothing reads

`src/catalogue_codex.py:336-339`

```python
r["entry_count"] = len(rec["entries"])
r["status"] = "catalogued"
roll_changes[r["name"]] = {"entry_count": len(rec["entries"]), "status": "catalogued"}
```

`r` is a row of the `roll` list loaded at `:172-173`. Since the compare-and-swap migration (order
`f818a77293fc`), persistence goes exclusively through `roll.update_rows(roll_changes, path=ROLL)`
at `:361` against a freshly-read roll; the in-memory `roll` is never written and never re-read
after this loop. The two mutations are leftovers of the whole-document land the comment at
`:355-359` describes replacing.

Harmless, but they make the in-memory document look like it is still the thing being persisted,
which is the misreading order `f818a77293fc` was filed to end. **Remedy:** delete the two lines,
keep `roll_changes`.

---

## 18. INFO — `gpu_lane.lane()` has a no-op `except Exception: raise`

`src/gpu_lane.py:579-582`

```python
        yield
    except Exception:
        raise
    finally:
```

The clause catches and immediately re-raises, which is what would happen without it. `try/finally`
alone is equivalent. Not a defect, but in a module this heavily annotated an empty handler reads as
a deliberate interception a reader will spend time looking for. **Remedy:** delete the two lines.

---

## 19. INFO — stale cross-references pointing INTO this batch from modules owned elsewhere

Verified while checking this batch's own citations; the fixes belong in the citing files.

* **`drill.py:7239`** cites `corpus_db.py:488-539` for `datasette_metadata`'s denied-write case.
  `datasette_metadata` is at `corpus_db.py:594-646`; lines 488-539 hold `_freshness_banner`'s
  comment and `_cell`. The net doing the citing is
  `datasette_config_is_generated_not_copied` at `drill.py:7228-7267`.
* **`catalogue_web.py:160`** cites `catalogue_codex.py:260` as a site that "lands through
  write_json, whose temp name carries pid and thread". `catalogue_codex.py:260` is
  `"type": etype,` inside an entry dict. The write sites are `:329`
  (`_P.write_record_catalogue`) and `:361` (`_roll.update_rows`).

*Checked and correct, left alone:* `ledger_guard.py:69` -> `MAINTENANCE.md:143` ("dated run
journal, newest on top") — exact; `ledger_guard.py:300` -> `pipeline.py:36` ("handoff/HANDOFF.md
hand-written ... NEVER written here") — exact; `scope.py:413` ->
`handoff/sweep24/AUDIT_batch06.md:320` — exact, the passage on `srlimit=3`/`titles[:8]`;
`foreman.py:302` -> `health.py:198-210` — exact; `corpus_db.py:130` -> `module_index.py:88-90` —
the pid/thread rule is stated at `module_index.py:94-96`, two lines past the cited range, close
enough not to mislead.

---

## QUESTIONS — two defensible readings, filed as questions rather than findings

**Q1. `scope.ceiling_for` will raise on a list-valued host, which `hosts.py` says can occur.**
`scope.py:531` does `cache.get(hosts.get(source) or "")` on the raw `WIKI_HOSTS.json` mapping.
`hosts.primary_host` (`hosts.py:53-57`) explicitly handles `isinstance(h, list)`, so at least one
module in the tree believes that shape is reachable — but `hosts.py`'s own header says the file is
"194 sources, 194 strings, zero lists", and a list key would raise `TypeError: unhashable type`
rather than answer wrongly. Loud rather than silent, so possibly fine as-is. Is the list shape a
real possibility, or vestigial in `hosts.py`?

**Q2. `_catalogue_batch`'s `--only` uniqueness test is scoped to short sources, not to the roll.**
`foreman.py:796` requires a fragment to identify exactly one source *in `gap`*. `catalogue_web
--only` is a substring match over the whole roll, so a fragment unique among short sources could
still match a non-short source. `foreman.py:892-895` argues `--shortfall 1` closes this ("a fragment
that somehow matched a source with no gap still cannot be dispatched"), and that is probably right —
but `gap` is computed here from `COMPLETENESS.json` minus `unreliable` and minus off-roll sources,
which need not be the same set `catalogue_web` computes for `--shortfall 1`. Whether the two
shortfall computations agree is a question for whoever owns `catalogue_web.py`. Also note the
uniqueness test at `:796` is evaluated *before* the unnameable entries are removed from `gap` at
`:800-801`, so a fragment can be judged ambiguous against a source that is itself about to be
dropped — conservative (over-refusal), not a loss, and each refusal is printed by name at
`:888-890`.

---

## 20. MAJOR — batch membership is not stable across a run, and it changed underneath this audit

`src/sweep_plan.py:batches()`

At the start of this batch, `sweep_plan.batches(16)[8]['modules']` returned:

```
foreman.py corpus_db.py gpu_lane.py ledger_guard.py
catalogue_codex.py hosts.py scope.py cosmology_graph.py
```

At the end of the same session, the identical call returned:

```
catalogue_codex.py chord_field.py corpus_db.py entity_match.py
foreman.py gpu_lane.py ledger_guard.py thread_integrity.py
```

`hosts.py`, `scope.py` and `cosmology_graph.py` had moved to batches 7, 7 and 8; `chord_field.py`,
`entity_match.py` and `thread_integrity.py` had moved in. No file was created or deleted — the
plan holds 115 modules either way.

The cause is that `batches()` is a greedy longest-first bin-pack over the **current line counts**
of every module in `src/`:

```python
for m in modules():
    b = min(bins, key=lambda b: b["lines"])
    b["modules"].append(m["module"])
    b["lines"] += m["lines"]
```

A line-count change to *any one* of the 115 modules re-packs *every* bin. The maintenance shift
is editing `src/` right now — `hosts.py` (22:38 today), `scope.py` (23:27), `thread_integrity.py`
(23:24) and `chord_field.py` (22:52) were all written during this run — so the partition moved
while sixteen agents were reading against it.

**Why this is a coverage defect and not a curiosity.** The sixteen batches are a *partition*: the
sweep's completeness argument is that every module is in exactly one batch, so if all sixteen
report, everything was read. That argument only holds if all sixteen resolve the same partition.
They do not. An agent that calls `batches(16)[i]` at 22:00 and one that calls it at 23:40 are
working from different partitions, and the union of sixteen different partitions is neither a
cover nor disjoint: some modules are read twice and **some are read by nobody**, while every
batch reports a clean pass. That is Hard Rule 0's shape applied to the audit process itself — a
sweep that returns a smaller universe wearing the shape of a complete one.

It is only survivable today because `sweep_plan.record()` takes an explicit module list and
`missing()` unions the shards, so an uncovered module is still *nameable* after the fact. Nothing
prevents the gap; something merely reports it afterwards, if anyone runs `--missing`.

**This audit's own resolution.** I read the eight modules the plan named when the run started and
recorded exactly those eight. I did not read `chord_field.py`, `entity_match.py` or
`thread_integrity.py`, and did not record them. Whoever coordinates run39 should check
`sweep_plan.missing('run39')` before calling the sweep complete — on the partition as it now
stands, those three are batch 9's and are **unread by me**.

**Remedy.** Freeze the partition per run rather than recomputing it per call: have `batches()`
take a run id, compute the pack once, and persist it (`state/SWEEP_PLAN.<run>.json`) so every
agent in the fan-out resolves the same assignment for the life of the run. A later call for the
same run reads the frozen file; a call for a new run repacks. That also makes the plan auditable
after the fact, which it currently is not — there is no record of what batch 9 *was* when batch 9
ran.

---

## Coverage

Eight modules read in full, uncapped, and recorded via
`sweep_plan.record('run39', [...], batch=9)`:
`foreman.py`, `corpus_db.py`, `gpu_lane.py`, `ledger_guard.py`, `catalogue_codex.py`,
`hosts.py`, `scope.py`, `cosmology_graph.py`.

**NOT read, and NOT recorded:** `chord_field.py`, `entity_match.py`, `thread_integrity.py`.
These were not in batch 9 when this run began; they moved into it mid-session — see §20. They
need an owner.
