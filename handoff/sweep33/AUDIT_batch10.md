# Batch 10 — run33
Modules read: dashboard.py (986 lines), allsweep.py (495 lines), catalogue_web.py (403 lines),
backfill.py (300 lines), hosts.py (253 lines), style_audit.py (211 lines), scope.py (152 lines),
withdraw_chapters.py (112 lines). All eight read in full.

## FINDINGS

### 1. withdraw_chapters.py:66-98 — the withdrawal has no selection logic; it processes the
entire catalog, not the ruled-on subset  [severity: BLOCKING]
The module's own docstring states a scoped action: "the 145 chapters written while the prose
gate was inverted are withdrawn." The code implements no such scoping anywhere. `main()` loads
the whole catalog and iterates every entry unconditionally:

```python
with open(CATALOG, encoding="utf-8") as f:
    cat = json.load(f)
...
for _addr, rec in cat.items():
    for key, sub in (("raw_path", "raw"), ("compressed_path", "compressed")):
        ...
        shutil.move(src, os.path.join(arch, sub, os.path.basename(src)))
```

and then, if `--go`, truncates the live catalog to nothing at all:

```python
tmp = CATALOG + ".tmp"
with open(tmp, "w", encoding="utf-8") as f:
    json.dump({}, f, indent=2)
```

There is no filter by citation percentage, by Threads-section presence, by date, by source, or
by any other criterion the docstring describes as the reason for withdrawal — the criteria named
in the docstring exist only as prose, not as a predicate anywhere in the code. `--label` only
names the archive directory; it selects nothing.

I confirmed this against the actual run already on disk: `output/index/catalog.json` currently
holds 0 entries, `output/withdrawn_2026-08-25/catalog.withdrawn.json` holds exactly 145, and
`output/raw` / `output/compressed` are both empty. The counts line up with the docstring's "145"
only because, at the moment this script last ran, the entire live catalog happened to consist of
those 145 chapters and nothing else (this was evidently an early/pilot-scale run, before other
sources had been generated). That is a coincidence of timing, not a safety property of the code.
The very next time this script is needed — a future ruling that withdraws a different, smaller
set of chapters while the rest of a now-larger catalog is healthy — `--go` will move every
healthy chapter's raw and compressed files into the archive and reset the entire live catalog to
`{}`, deleting the library's record of everything it has generated, not just the flagged set.
Nothing in the script would warn the operator this was about to happen; the only signal offered
is `print("catalog entries: %d" % len(cat))`, printed with no comparison against an expected
count and no gate on `--go` proceeding regardless of what that number is.

The move-not-unlink design (explicitly called out in the module's own docstring as the safety
property) protects against permanent data loss, but does not protect against the wrong 20,000
chapters being pulled out of the live library and the catalog that indexes them being wiped, on
a script whose whole job is described as narrowly scoped and is not.

### 2. withdraw_chapters.py:80-90 — the "unclaimed strays" sweep has no way to tell a stray from
work in flight  [severity: MAJOR]
```python
# Anything left in output/raw that the catalog never claimed -- the pilot's strays.
extra = 0
rawdir = os.path.join(HERE, "output", "raw")
if os.path.isdir(rawdir):
    for f in sorted(os.listdir(rawdir)):
        src = os.path.join(rawdir, f)
        if not os.path.isfile(src):
            continue
        if a.go:
            shutil.move(src, os.path.join(arch, "raw", f))
        extra += 1
```
This treats "not yet present as a key in catalog.json" as proof a file is an orphaned pilot
artifact. `generate.py` writes the raw `.md` file to disk first and only afterward records the
job in its in-memory `catalog` dict (`generate.py:458-468`), which per CLAUDE.md is saved to
disk periodically rather than after every single job ("generate.py's progress bar and periodic
catalog saves"). That means there is a real, ordinary window in which a freshly-generated,
perfectly legitimate chapter sits in `output/raw/` with no corresponding catalog entry yet. If
`withdraw_chapters.py --go` runs during that window — generate.py mid-run, or recently
interrupted before its next catalog save — this loop sweeps that legitimate file into the
withdrawal archive next to the actually-bad chapters, with no distinguishing mark and no
timestamp or "generate.py is not running" check. This is exactly the live archive evidence found
for finding 1: `output/withdrawn_2026-08-25/raw` holds 148 files against 145 catalog entries and
145 compressed files — 3 files were swept up by this exact "unclaimed" path, unverified against
anything.

### 3. allsweep.py:400-491 — the grading can report "0 subsystem(s) in a bad state" while a
graded verifier has genuinely failed  [severity: BLOCKING]
`bad` — the number that gates `main()`'s printed verdict and its exit code — only counts a
verifier as bad if it crashed or timed out:
```python
bad = (len(broken)
       + sum(1 for r in verifiers if r["crashed"] or r.get("timeout"))
       + len(lint_bad)
       + len((est.get("artifacts") or {}).get("bad", [])))
```
A verifier that exits nonzero WITHOUT crashing is printed as `findings` (line ~411) and is never
added to `bad`. The comment justifying this is scoped narrowly and correctly to two of the nine
verifiers: "`silence` and `audit` exit 1 when they HAVE findings -- that is their contract." But
`VERIFIERS` applies the identical treatment to all nine, including `verify_math.py` and
`anchors.py`, whose nonzero exit is not a "here are some findings to browse" contract — it is
their designed way of reporting a genuine, already-detected correctness failure:
- `verify_math.py:4497` — `if FAIL: ... sys.exit(1)` after printing `f"RESULT: {len(PASS)}
  passed, {len(FAIL)} FAILED"`. A FAILED check here means a checked invariant about the
  project's numbers is actually broken.
- `anchors.py:277`, with its own comment explaining exactly this: `sys.exit(0 if _ok else 1)`
  after "INVARIANT VIOLATED. The anchors do not ascend from floor to ceiling... It exits 1
  TODAY: measured run #26, `A Sword` (0.10) sits below `The Skate Guy` (0.22)."

So if either of these genuinely fails on a given sweep, allsweep prints it as `findings` (the
same word used for silence.py/audit.py's harmless reporting contract), does not add it to `bad`,
and the closing lines — `f"{bad} subsystem(s) in a bad state"` and the process's own exit code
(`return 1 if bad else 0`) — can both read clean while the numbers or the instrument are
verifiably broken. The final summary line only calls out `reconcile` as "ungraded" (line 490);
it says nothing about the fact that six of the nine VERIFY-tier checks can fail for a real reason
and vanish from the grade with no acknowledgment at all, unlike reconcile's honestly-labeled gap.

(By contrast: I checked whether RECONCILE's own "ungraded" label, which the task asked me to
verify, is a genuine judgment call rather than a fault quietly downgraded — it is. The comment at
lines 473-480 explains specifically why (`note()` carries no severity and the row list
deliberately mixes real disagreements with plain healthy facts, e.g. "phases implemented 8"), and
documents that summing it was tried and reverted in run #26. That part of the grading design is
sound and explicitly reasoned about. The VERIFY-tier gap above is not similarly labeled anywhere.)

### 4. style_audit.py:38-39 — `TURN_ENDING`'s `re.M` flag makes `$` match end-of-line, not
end-of-record, so the "ends on a turn" density metric overcounts  [severity: MAJOR]
```python
TURN_ENDING = re.compile(
    r"(?:\.|\?)\s+(?:And|But|Yet|Still|Which|That)\b[^.]{0,80}\.\s*$", re.M)
```
`re.M` makes `$` match immediately before ANY `\n` in the record, not only at the true end of the
record's text. A Record can and does span multiple paragraphs (`record_of()` captures with
`re.S`, i.e. across newlines, up to the next section marker). I reproduced this directly:
```
rec = 'Alpha is a city of the northern reach. It endures. And so it remains standing.\n'
      'More facts follow here about Alpha that are entirely mundane and add nothing dramatic at all.'
TURN_ENDING.search(rec) -> a match, even though rec plainly does NOT end on a turn
```
Any Record containing a turn-shaped sentence ("...And so it remains.") anywhere before an
internal paragraph break gets counted as an entry that "ends on a turn," inflating `turn_rate`
and potentially tripping the `> 0.25` "OVER" flag the report prints, for entries that in fact
close on ordinary prose. The check exists specifically to enforce Ground Rule 6 ("Do not end an
entry on a turn"); as written it is measuring something else (does a turn-sentence appear
anywhere except in the final paragraph's last line) and will misreport corpus health to anyone
relying on this audit before scaling a run.

### 5. catalogue_web.py:199-244 — `_short` is a stale closure variable during the fetch loop, so
every "fetching" progress line prints the wrong category  [severity: MINOR]
```python
for canon in ws.CATEGORY_KEYWORDS:
    ...
    _short = canon.split(" (")[0][:16]        # (only assignment site in the function)
    ...
for canon, cats, titles in planned:
    ...
    texts = ws.page_texts(sub, wanted,
                          progress=lambda d, t: _beat(_short + " fetching", d, t))
```
`_short` is assigned only inside the first loop (category discovery) and is never reassigned in
the second loop (page fetching), even though the second loop iterates over a different `canon`
each time. Every "fetching" heartbeat line printed during the second loop therefore carries the
short name of whichever category happened to be the LAST one with non-empty `cats` in the first
loop — not the category actually being fetched. The module's own long comment (lines 162-181)
explains that these heartbeat lines exist specifically so a human (or the foreman's stall
detector) can tell what a long-running catalogue pass is doing; the labels are wrong for the
entire fetch phase on any source with more than one planned category. The heartbeat still fires
on schedule (so the stall-killer isn't fooled), but the diagnostic text is misleading for exactly
the large, slow sources (DC, Marvel) the comment says this exists to help debug.

### 6. dashboard.py:329-384 — concurrent `/api/state` requests can race on
`state/dashboard_history.json` and silently drop a movement sample  [severity: MINOR]
`Server` is a `socketserver.ThreadingTCPServer` with `daemon_threads = True`, so simultaneous
`GET /api/state` requests are served on different threads, each independently calling `state()`
-> `movement()`. `movement()` does an unsynchronized read-modify-write of the shared file:
```python
hist = []
if os.path.exists(HISTORY):
    ... hist = json.load(f) ...
...
hist.append(row)
...
with open(tmp, "w", encoding="utf-8") as f:
    json.dump(hist, f)
silence.replace_retry(tmp, HISTORY)
```
`silence.replace_retry` makes the individual *write* atomic, but does nothing about two threads
each having read the same pre-append `hist`, each appending their own `row`, and the second
`replace_retry` clobbering the first thread's write — the first thread's sample is lost with no
error and no `silence.note()`. Given the page auto-refreshes every 5 seconds per client, this
mainly matters when more than one browser/consumer polls `/api/state` at once, or when a request
overlaps its own next poll under load; the practical damage is a missing point in the last-30-
minutes movement window, and the file structure self-heals on the next successful write, so this
is low-impact — but it is exactly the read-modify-write-on-shared-state pattern the brief asks
to be checked for, on the one file this ThreadingTCPServer handler writes on every request.

## QUESTIONS

- **withdraw_chapters.py:74** — `shutil.move(src, os.path.join(arch, sub, os.path.basename(src)))`
  moves by basename alone. If two different catalog addresses ever produced the same
  `safe_filename(job["address"], "md")` (a collision inside `generate.py`, not read in this
  batch), the second move would silently overwrite the first archived file. I could not confirm
  or rule this out without reading `generate.py`'s `safe_filename`; worth a look given finding 1
  and 2 already show this script's safety margin is thinner than its docstring implies.
- **scope.py:102-120** — `build()` accumulates results for every host in `todo` in memory and
  calls `silence.write_json(OUT, out, ...)` exactly once, after the whole loop finishes, unlike
  every other long-running fetch job in this codebase (catalogue_web.py, backfill.py) which
  write per-item specifically so an interrupted run doesn't lose completed work. Is this
  deliberate because a scope build is expected to be short (bounded host count, few queries per
  host), or is it a gap that should get the same per-item persistence treatment?
- **style_audit.py:44** — `re.split(r"^[◈◈]\s*", text, flags=re.M)`: the character class
  contains the same codepoint (U+25C8) twice, which is functionally identical to a single `◈`
  and has no effect on behavior. Harmless as it stands, but it reads like the trace of an edit
  that meant to also match a second marker and didn't. Worth a glance in case a second entry-
  opening convention was meant to be recognized and silently isn't.
- **dashboard.py:234-247** — `_TTL_MEMO` is a plain module-level dict read and written from
  multiple `ThreadingTCPServer` worker threads with no lock (`_ttl()`). Under CPython's GIL the
  individual dict get/set are atomic, so this shouldn't corrupt, but two overlapping requests
  inside the same TTL window can both miss the cache and both run the underlying `fn()` (e.g.
  `_library()`, `_watch()`) redundantly. Given the TTL exists specifically to avoid recomputing
  expensive sums on every 5-second poll, is the occasional double-computation acceptable, or
  should this get the same lock the roll/record writes elsewhere in the tree already use?

## CLEAN
- **hosts.py** — read in full. The multi-host registry's write path (`add()`), the specialist-
  vs-substantial secondary-host admission logic, and the `discover()` thread pool were checked
  for the race the module's own comments describe having fixed (`silence.write_json` replacing a
  shared temp-file pattern); the current code matches what the comments claim, and `add()` calls
  are confirmed to happen serially in the main thread even though scoring runs in a worker pool,
  so there is no read-modify-write race left on `SOURCE_HOSTS.json`. Nothing else found.
- **backfill.py** — read in full, including the two-writer contract fix, the `absent`-computed-
  before-cap fix, and the `RosterIncomplete` distinction between "no page" and "timeout" — all
  checked against the code and all consistent with what their comments claim was fixed. No
  remaining defect found.
- **scope.py** — read in full. The "highest tier clearing the floor, never the most frequent
  one" claim was checked directly against the loop that builds `best` (low-to-high iteration,
  unconditional overwrite means the last, i.e. highest, tier that clears `MIN_MENTIONS` wins) —
  correct as implemented. See the one open question above about write timing, which is not a
  correctness defect in what's written, only in when.

