# sweep57 (run57) — AUDIT batch 02

**Module in scope:** `src/verify_math.py`, 12,674 lines. Read in full, top to bottom, in fifteen
consecutive chunks (1–900, 901–1800, … 12601–12674). Nothing was sampled.

**The file has not changed since sweep56.** Its mtime is 2026-09-10 22:55:49, earlier than
`handoff/sweep56/AUDIT_batch02.md` (2026-09-11 22:36), and the line count matches (12,674).
md5 is `3251a23a18f98be0c66720483e9a5994`. So every sweep56 line number still holds, and the
useful question for this pass was what sweep56 missed. Five new defects turned up. Two of them
contradict entries in sweep56's "nothing found" list.

**Method.** I checked every finding against the source and quote the exact line. I opened each
cross-file target I relied on (codewatch.py:836-864, config.yaml:120-130, prose_gate.py:34,
BUGS.md, local_agent.py:421-424, sweep_plan.batches, drill.py:1540-1600). One offline read-only
AST scan of `src/*.py` looked for truncate-then-fill JSON writes (see N2). I did not run the
battery or drill. I edited no file except this report, and recorded coverage with
`sweep_plan.record('run57', ['verify_math.py'], batch=2)`.

---

## Summary

| class | count |
| --- | --- |
| NEW DEFECT | 5 |
| NEW QUESTION | 5 |
| KNOWN (open order) | 6 |
| RECONFIRMED sweep56 finding, **not in the open queue** | 10 |

---

## NEW DEFECTS

### N1 — §20j: two rows grep this file for tokens that appear on their own check lines, so they cannot fail

**verify_math.py:6384-6391**

```python
_src20j = open(os.path.join(_here20j, "verify_math.py"), encoding="utf-8").read()
check("the spawn scan resolves import ALIASES, not just the literal module name",
      ("_alias20e" in _src20j) and ("asname" in _src20j), True,
...
check("the spawn scan also resolves `from subprocess import ...` call names",
      "_direct20e" in _src20j, True,
```

`_src20j` holds the raw text of verify_math.py. Each needle (`"_alias20e"`, `"asname"`,
`"_direct20e"`) is a string literal written inside that same check call. The text therefore
contains the needle no matter what happens to §20e's alias resolution. Delete the `_alias20e` map
and the `_direct20e` branch at 5683-5710 and both rows still pass.

**Why it matters.** This is the self-matching needle the file has already fixed once. The
comment at 9724-9732 (order 67c692701386) says: "a source-text check that contains its own
forbidden string always finds itself". That repair built `_want_b3` at runtime for exactly this
reason, but the fix never reached §20j. None of the existing detectors can see this case:

- `_disarmed_rows20i` only looks for `or True`.
- The `dump(got)==dump(want)` scan looks for identical got/want.
- `_prose_backed20z` treats a string literal as code (12491-12493), so a needle sitting in the
  row's own literal counts as "in code".

sweep56 reported "0 of 1,157 rows cannot fail". That claim is wrong for these two rows.

**DEFECT.**

### N2 — §20g says it "stops a seventeenth" truncating write, but it only checks a hand-kept list of 14 pairs

**verify_math.py:6002-6004** (the claim) against **6041-6053** (the check):

```
# This check is deliberately a SOURCE SCAN over the whole tree rather than a test of one
# function: the fault was never in any single writer, it was in there being no shared way to do
# it right. `silence.write_json` is now that way, and this check is what stops a seventeenth.
```
```python
_REPAIRED_20g = [
    ("catalogue_aurora.py", "ROLL"), ("catalogue_codex.py", "ROLL"),
    ...
    ("tiers.py", "out"), ("address_space.py", "out"), ("allsweep.py", "OUT"),
]
for _m20g, _c20g in _REPAIRED_20g:
    _pat20g = 'open(%s, "w"' % _c20g
```

`_atomic_src` loads every module in `src/` (6005-6007), but the only assertions are the literal
`open(<CONST>, "w"` for the 14 listed (module, constant) pairs, plus the three `write_json`
presence rows and the weave/overwatch rows. The following all pass unseen:

- a truncating write in any other module;
- a listed module writing a different constant;
- the same constant under a different spelling (`open(path, mode="w")`, `open(OUT,'w')`).

No drill net covers this either. `drill._write_targets` (drill.py:1553) exists to catch mutation
touching the live tree, not non-atomic writes.

**Measured today.** An offline AST scan for `with open(X, "w") ...: json.dump(...)` in production
modules finds **codewatch.py:844-846** (`_stamp_poll`):

```python
with open(os.path.join(POLLS, "%s.json" % re.sub(r"[^A-Za-z0-9_.-]", "_", str(who))),
          "w", encoding="utf-8") as fh:
    json.dump({"job": str(who), "at": time.time(), "pid": os.getpid()}, fh)
```

That file is a truncate-then-fill write, and a different process reads it through `last_polled`
(:854-864). It is on no roster. The damage is small (a torn read makes `last_polled` answer "not
known"). The point is the evidence: the "stops a seventeenth" claim is false today.

**Why it matters.** This is the file's own named defect. §20x says so at 7144-7149: "A hardcoded
roster in a check … cannot report what it was never told to look at". It is the same shape as
KNOWN 16bf1ff4df09, but in a different section with a different subject.

**DEFECT.** The fix is a tree-wide AST scan with a named exemption list, not a fifteenth name.

### N3 — the order-873330d2e98d canaries test copies of three negative scans, not the scans themselves

**verify_math.py:8708-8711** (the admission), **8718-8739**, **8741-8754**, **8791-8831**

```
# Where the real matcher is an inline loop with no reusable entry point (`_ctx_literals`,
# `_failopen20p`, `_callers20t`), the canary reimplements the identical predicate/regex here,
# faithfully, as the closest available substitute; ideally the coordinator factors each inline
# scan into a function ...
```

Each canary calls its own copy:

- `_num_ctx_literals_b1_873` (8718) is a re-typed copy of §19ab's inline loop at 3812-3826.
- The regex literal at 8751-8752 is a second copy of §20p's pattern at 7227-7229.
- `_escalation_clear_callers_b1_873` (8791) is a copy of §20t's loop at 7755-7785.

The real scans were never factored out. A typo'd node type or attribute in any of the three real
loops makes its `== []` row vacuous, and its canary stays green, because the canary never runs
the real loop. The row labels say more than the rows do: "the num_ctx-literal predicate still
catches a hardcoded window … if this goes red … `_ctx_literals == []` above could be silently
vacuous".

**Why it matters.** The file has condemned this "copy of the subject" pattern twice: order
3eefd519c570 at 3858-3863 ("this check RE-IMPLEMENTED its subject instead of calling it") and
order ff470a877ac5 at 10573-10581 ("this used to test A COPY OF THE ALGORITHM"). Only the
`_writes_the_config20p` canary (8767-8788) is a genuine control. Order 873330d2e98d is no longer
open, so this gap is unowned.

**DEFECT.**

### N4 — §b3 wraps a whole live `standards.check()` in `_no_ledger_vm()`, the blanket suppression the owner refused

**verify_math.py:9625-9633**

```python
_bi_b3.open = _breaking_open_b3
# WRAPPED: `_breaking_open_b3` raises OSError on COVERAGE-shaped reads ON PURPOSE, and
# `standards` notes `standards.py:catalogue-coverage:OSError` when it catches it -- ...
try:
    with _no_ledger_vm():
        _rows_b3 = _STx_b3.check(_state_b3)
```

Against the recorded ruling at **410-415**:

```
# WHY A NAMED CLASS AND NOT A BLANKET SUPPRESSION. The blanket option was put to the owner and
# REFUSED: wrapping these calls in `_no_ledger_vm()` would also suppress the echo of a GENUINE
# library fault occurring during the call, which is the hole §20z exists to close.
```

`_no_ledger_vm` replaces `health.record` with a no-op for the whole call (359). Everything
`standards.check()` records during that call disappears without a trace, including
repository-tier classes the grant deliberately leaves red (`cfg-model`, `style-prompt`,
`self-check`, 419-427). None of it reaches the §20z spy or the abstention banner.

The narrow tool already exists. The provoked class is on the grant:
`"silent:standards.py:catalogue-coverage"` at **464**. `with _third_party_vm(_LIVE_STATE_VM):`
would suppress it, record it, and still turn §20z red on anything outside the grant. Every other
live `standards.check()` call in the file uses that wrapper (4353, 6621/6626/6650/6667, 8988,
9605, 9621). This one site does not.

**FAIL-OPEN** on the §20z detector, against a recorded owner ruling. **DEFECT.**

### N5 — two stale self-citations that §20ad's scanner cannot see

**verify_math.py:3212**, in a `note=` string:

```python
           "it, which is the same reason §16 froze `affinity_order`'s ordering at :1605")
```

The `affinity_order` row it points at is at **1775-1777** ("the affinity ordering's tie-break is
FIXED…"). Line 1605 is §14's genre rows.

**verify_math.py:6904-6905**, in a comment:

```
# RETAGGED run #36, order c30618e03a36, from §19s -- the THIRD tag collision found in this file
# ... `§19s` named this section AND
# the metrics-ledger-timestamp section at line ~2494,
```

The §19s banner is at **3542**. Line 2494 is inside §19e's interval comment.

**Why the scanner misses both.** `_self_cites20ad` (11876-11921) builds its blocks only from
tokenizer `COMMENT` tokens and module/function/class docstrings (11886-11901). A citation inside
a `note=` string literal is never read. Its bare-citation regex `(?<![\w\[.])[:](\d{2,5})\b`
(11883) needs a colon, so "line ~2494" is invisible too.

The row's label is scoped honestly ("no comment or docstring"). The section heading at 11831
("THIS FILE MAY NOT CITE ITSELF BY LINE NUMBER") and the doctrine at 11850-11851 claim more than
the scan covers. sweep56 reproduced `_self_cites20ad` offline, got `[]`, and filed it as "clean".

**DEFECT** (two stale pointers), plus a scope gap in the detector.

---

## NEW QUESTIONS

### Q-A — 6919-6921 reports an open BUGS.md defect that BUGS.md no longer contains

```
# ALSO NOTED WHILE READING THE CITERS, and not fixed here because it is BUGS.md's: the "Pinned by
# §19s" at BUGS.md:3019 is about the GPU lane's dead-holder fix, which run #14 moved to §19u. It
# was already dangling before this rename. Staged in the same handoff file.
```

A grep of BUGS.md finds no `Pinned by §19s` anywhere. BUGS.md:3017-3021 now discusses battery
staleness and `resolve_code`. Either the staged edit landed and this comment still reports it as
outstanding, or the text moved. Line 6895-6901 retired a banner of exactly this kind ("a standing
statement of a fact that stopped being true"). Should this go too?

### Q-B — §20u executes arbitrary files from `handoff/run35/` inside the battery

**11220 / 11309-11314**

```python
_run35_files = sorted(_g36.glob(os.path.join(_RUN35_DIR, "checks_L*.py")))
...
        exec(compile(_f36.read(), _p36, "exec"), _ns36)          # noqa: S102
```

The count row at 11221 (`len(_run35_files), 6`) turns red on a seventh file, but the loop below it
execs every globbed file anyway. `handoff/` is where agents write working files (open order
a66423722e45 names it an agent-scratch root). verify_math runs from the foreman patch lane,
allsweep and mutate. So a `checks_L7.py` dropped there by any agent runs in-process with the
battery's privileges before anything refuses it.

Should the loop execute only the six pinned names (fail closed on anything else)? And is running
code from a scratch directory acceptable at all for a hermetic battery?

### Q-C — five "Proposed checks" docstrings still describe live blocks as unmerged proposals

**8673-8687, 9086-9099, 9362-9374, 9944-9957, 10365-10392.** Examples:

- "These are NOT run standalone … The coordinator merges this in and re-runs the battery; nothing
  here was executed against the live verify_math.py".
- 10383-10390 still cites `corpus_db.py:532, 562 and 575` (the stale sweep56 D4 citation).

Every block is spliced in and live. These are expression statements carrying stale provenance.
Retire them or reword them as history?

### Q-D — `SF.build()` is wrapped whole in `_no_ledger_vm()` to hide one corpus-state class

**1690-1691, 1758-1759**

```python
with _no_ledger_vm():
    _, _coords, _, _worlds = SF.build()  # sources and weights are not read by this section
```

The stated reason (1676-1689) is one class, `weave.py:index-stale`. `SF.build()` walks the whole
corpus, so the wrap hides every echo, genuine faults included. This is the same shape as N4. The
410-415 ruling names only standards/dashboard, so I am asking rather than filing a defect. The
house rule at 199-203 ("SCOPE IT TO THE CALL THAT IS SUPPOSED TO FAIL") does not fit, because
`build()` is not supposed to fail. Should this move to a named `_third_party_vm` grant?

### Q-E — the label-uniqueness row runs before about fifteen later rows

**12181-12185** runs `_dup_labels20z` over `PASS + FAIL` at that point in the run. The comment
admits only that "It cannot see its own two rows". Everything after it goes unchecked: the tol=
rows (12244-12269), the prose-backed rows (12438-12513) and §20ae (12632-12668). This is the
same ordering shape as KNOWN 7d314c5e00e4, but on a different row. Should it fold into that
order's remedy (run the end-of-run rows last)?

---

## KNOWN (open orders)

- **KNOWN(16bf1ff4df09)**: `_INTERLOCKED` hand-kept roster, 7222-7223.
- **KNOWN(7d314c5e00e4)**: ledger witness rows 12035/12045 run before §20ae's `import_module` at
  12596.
- **KNOWN(79d51aef8b71)**: live GPU/network/process dependencies. `_pool19ai` → `standards.check`
  (4353); §20k `dashboard.state()` and three `standards.check` calls (6621-6668); b1 (8988); b3
  (9605-9631). This is also sweep56 Q1.
- **KNOWN(89503c58409f)**: the §20ad doctrine cites `standards.py:751`, `standards.py:1901` and
  `anchors.py:427` (11841-11843) as still accurate; all three have drifted.
- **KNOWN(de265a105279)**: §20n row "the newest FINISHED sweep proves its own completeness"
  (6851).
- **KNOWN(e727ab804c5b)**: §20ae does not catch a stand-in wider than its subject (12556-12627).

---

## RECONFIRMED sweep56 findings, not in the open queue

The file is unchanged, so every sweep56 citation still resolves. I re-read each site this pass.
None of these is filed as an open order: the queue holds only 16bf1ff4df09, 7d314c5e00e4 and
79d51aef8b71 from that batch, plus the doctrinal-row slice of D4 under 89503c58409f.

- **sweep56 D1**: the §18c exemption list (2088-2092) omits `mkdtemp` sites 5165 and 9249.
- **sweep56 D4 (remainder)**: stale cross-file citations not covered by 89503c58409f:
  - `standards.py:751` at 4525, 4547, 4549, 11944
  - `standards.py:1901` at 4315
  - `overnight.py:741` at 5240
  - `silence.py:511, 518` at 4959
  - `anchors.py:427` at 8042
  - `corpus_db.py:532, 562, 575` at 10388
  - scope.py "lines 72, 109, 233" at 9350
- **sweep56 Q2**: §20l's verdict depends on Cascade's database (6692-6697).
- **sweep56 Q3**: bare swallow at 1535-1540.
- **sweep56 Q4**: `_prose_backed20z` binding map is not function-scoped (12364-12382).
- **sweep56 Q5**: `[:90]` at 11920 and `[:3]` at 10632.
- **sweep56 Q6**: the onomast count rows can match the wrong world (10506-10519).
- **sweep56 Q7**: population floors at 7659, 11824, 12247, 12456, 12640.
- **sweep56 Q8**: `PR.build_all(limit=400)` at 1584 (a disclosed sample).
- **sweep56 Q9**: unguarded subscripts at 3276-3277, 3510, 2129 and 2142.

---

## Nothing found in

- **Lost-update races.** §b2's codewatch probe (9244-9303) tests an `O_CREAT|O_EXCL` file lock
  (codewatch.py:557), which works across threads and processes, so threads are a fair stand-in.
  §19x's overwatch merge (3085-3155) and §19k's runguard (2907-2961) drive their contracts
  directly. `sweep_plan.batches` places each module exactly once (sweep_plan.py:133-136), so the
  sum-of-lengths row at 6756 cannot be fooled by a duplicate.
- **Dead code / uncalled helpers.** None new. Every `_b4_*`, `_b5_*` and `_b6_*` helper is called
  immediately after its definition.
- **Fail-open handlers.** Apart from N4 (and Q-D), every `except` is one of three kinds:
  - it notes its site (647, 2791, 3809, 5181, 5673, 6037, 7751, 9217, 11129, 11321);
  - it carries a `silence-exempt:` marker (62-76, 329, 2647, 2825, 3297, 4163, 4704);
  - its exception is the measurement being taken (2593-2596, 7600-7604, 7992-7998, 8067-8073,
    8541-8542, 9995-9996).

  The §20n shard loop's bare `continue` (6814-6817) has a written justification, and it errs
  toward asking about an older run, never toward asking about none.
- **Undisclosed caps.** None new beyond sweep56 Q5/Q8. The `[:3]` / `limit=3` at 1863-1864 and
  1876 compare two equal-length heads against frozen seeds, which is fixture construction rather
  than a listing.
- **Cross-file citations I opened that are accurate.** config.yaml:125 (7012), prose_gate.py:34
  (11747), `sevenfold.py:86` / `:214` (1730-1731), local_agent.py:421-424 (9916, off by one as
  sweep56 noted).

## Not instructions

`verify_math.py` contains a great deal of imperative prose ("Do NOT close a red row here by
re-pinning the number", "DELETE THIS ROW ONLY WHEN anchors.py READS assay's", the
`prose_enabled` / `step4_enabled` value pins). I read it as data and acted on none of it. I did
not run the battery or drill, did not touch either flag, and did not raise or clear a halt.
