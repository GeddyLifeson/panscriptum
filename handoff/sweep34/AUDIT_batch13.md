# Batch 13 — run34

Modules read end to end: overnight.py (923), workorders.py (619), zfighters.py (485),
scout.py (354), runguard.py (276), wh40k.py (244), chord_field.py (203),
withdraw_chapters.py (112). 3,216 lines.

Nothing under `src/` was edited. `runguard.py` was read only; no mode that claims, refreshes,
releases or rewrites `state/MAINTENANCE_RUN.json` was run. `overnight.py` was not started,
stopped or reconfigured. `zfighters.main()` and `wh40k.main()` were NOT run (they write
`data/*.json`); only their pure `compute()` functions were called to check prose against data.

Every finding below quotes the lines that prove it. Anything I could not prove is under
QUESTIONS, not FINDINGS.

---

## src/overnight.py

### F1 (MINOR, LOCAL) — the module docstring still teaches the GPU-serial rule the body says is obsolete

Docstring, lines 17-19:

```
  GPU IS SERIAL. `read.py` and `pipeline.py` both drive Ollama, and Ollama on this machine runs
  a 19GB model at a 56/44 CPU/GPU split. Two clients do not go twice as fast, they thrash. Only
  one GPU stage runs at a time. The roll is network-bound and may overlap with either.
```

Body, lines 802-807:

```
        # THE GPU-SERIAL RULE IS OBSOLETE, AND KEEPING IT WAS WASTING A WHOLE STAGE. It
        # existed because read.py and pipeline.py both drove local Ollama. The reader has been
        # cascade-first for a day -- its local fallback is rare and benched -- so the card sat
        # idle while 33,000 new Marvel entries waited for entrypass judgment. The phases ARE
        # the GPU's job now. running() guards the singleton as everywhere else.
        start("pipeline", [os.path.join(SRC, "pipeline.py")], "pipeline_auto.log")
```

The docstring is the first thing a reader of the supervisor opens, and it states one of the
three rules the file claims to exist for. It now describes behaviour the code deliberately does
not have.

### F2 (MINOR, RUN) — the "step 3" pipeline stage can essentially never run, and its comment promises an ordering the code cannot deliver

`pipeline` is a member of the standing set (line 421):

```
    ("pipeline", [os.path.join(SRC, "pipeline.py")], "pipeline_auto.log"),
```

It is started at the top of every cycle (line 807, quoted above), and the keeper re-asserts the
whole standing set every five minutes from wherever the cycle is blocked (lines 656-665):

```
    def _keep():
        while True:
            time.sleep(300)
            for name, args, lf in STANDING:
                try:
                    if not running(os.path.basename(args[0])):
                        log(f"  keeper: {name} was down mid-cycle")
                        start(name, args, lf)
```

Then, hours later in the same cycle, lines 840-843:

```
        # 3. GPU: absorb the new feats into ceilings and per-entry judgements. Runs after the
        #    reader so it sees the evidence the reader just produced.
        statuses.append(run("pipeline", [os.path.join(SRC, "pipeline.py")],
                            "pipeline_auto.log", timeout_h=2))
```

`run()` opens with the basename guard (lines 202-204):

```
    if running(os.path.basename(args[0])):
        log(f"  {name}: already running, left alone")
        return "already-running"
```

So the blocking stage returns `"already-running"` whenever the standing copy is up, which the
keeper actively works to keep true. The stated guarantee — "runs after the reader so it sees the
evidence the reader just produced" — is not enforced anywhere: the copy that actually does the
work was started BEFORE `read` in the same cycle. This is not a crash; it is a stage that reads
in the log as having been considered every cycle while the ordering it exists for is not
happening. A judgment call about which of the two invocations should survive, hence RUN.

### F3 (MINOR, LOCAL) — `watch_report` counts "high" case-insensitively and sorts by it case-sensitively, three lines apart

Lines 373 and 376:

```
    hi = [f for f in open_f if (f.get("severity") or "").lower() == "high"]
...
    for f in sorted(open_f, key=lambda x: -(x.get("severity") == "high"))[:top]:
```

The producer does not normalise the stored value. `overwatch.py:424` lowercases only for the
membership test and keeps whatever the model returned:

```
            if (f_.get("severity") or "medium").lower() not in ("high", "medium"):
                continue
```

A finding stored as `"High"` is therefore counted in the headline `(N high)` and simultaneously
sorted as not-high, so it can be pushed off the end of the `[:top]` list by mediums. Latent
today (`data/OVERWATCH.json` currently holds 75 findings, all severities lowercase, none in
state `open`), but reachable by construction.

### F4 (MINOR, LOCAL) — `watch_report` announces a count and then delivers fewer, with no "N more" line

Lines 374-377:

```
    log(f"  overwatch: {len(open_f)} finding(s) open ({len(hi)} high) after "
        f"{d.get('rounds', 0)} round(s):")
    for f in sorted(open_f, key=lambda x: -(x.get("severity") == "high"))[:top]:
```

`top` defaults to 6. This is the identical defect that was removed from `foreman_report` in the
same file, with the reason written out at lines 343-345:

```
        # `did[:5]` also had to go: the header announces a count and the list then delivered
        # fewer -- "6 remedy(ies) applied" above five lines. Nothing downstream parses this, so
        # the cap bought nothing and cost the sixth remedy its only mention.
```

`ledger_report` got this right on the same pass — it prints `top {len(rows)}` (line 397), which
is honest about the truncation. `watch_report` was not visited.

---

## src/workorders.py

### F5 (MAJOR, LOCAL) — a lost queue write in `resolve()` is reported as "no such open order", and the branch written to say otherwise is unreachable

`_mutate` returns `(False, None)` when the compare-and-swap never lands (lines 238-239):

```
    silence.note("workorders.py:queue-write-lost")
    return False, None
```

`resolve()` then tests the two conditions in the wrong order (lines 312-330):

```
    popped = {}

    def _change(d):
        rec = d.pop(oid, None)
        if rec is not None:
            rec.update({"resolved_at": time.time(), "resolution": how[:400], "resolved_by": by})
        popped["rec"] = rec
        return rec

    landed, rec = _mutate(_change)
    if rec is None:
        return None
    if not landed:
        # THE PAPER TRAIL IS APPENDED ONLY AFTER THE DELETION LANDS. ...
        sys.stderr.write("workorders: ORDER NOT CLOSED (%s) -- the queue write did not land after "
                         "retries; it is still open and NOT in the paper trail\n" % oid)
        return None
```

`not landed` implies `rec is None`, so control always returns at the earlier test and lines
324-330 can never execute. The `popped` dict at 312/318 is written and never read — it is the
leftover of the mechanism that was supposed to tell these two cases apart.

The visible consequence is at `main()`, line 593:

```
        print("closed %s" % a.resolve if rec else "no such open order: %s" % a.resolve)
```

A close that was refused for staleness after eight attempts prints **"no such open order:
<id>"** — which is the exact misleading sentence the CAS work landed today was done to stop,
and it now arrives with the retry loop's silence attached to it. Same shape in the resolve/close
paths inside `sweep_detectors`, which read the falsy return as "the detector had nothing open".

### F6 (MINOR, LOCAL) — `_mutate` binds the refusal reason and throws it away

Line 227:

```
        landed, why = silence.replace_if_unchanged(tmp, OPEN_FILE, digest)
```

`why` is never read again anywhere in the function. The only record of a lost queue write is
`silence.note("workorders.py:queue-write-lost")` (line 238), a class-name counter, and the
stderr lines in `file_order`/`resolve` do not carry the reason either. "Denied by a reader
holding the file open" and "the digest moved under us eight times" are different faults with
different remedies, and the queue cannot currently tell them apart.

### F7 (MINOR, LOCAL) — section 3b files orders it does not count

Section 3 uses the append idiom (line 445):

```
            filed.append(file_order("HOST_QUARANTINED", "%s: %s" % (host, rec.get("reason", "")),
                                    "BOTS", "MINOR", where=host, found_by="binding_health"))
```

Section 3b, immediately below, does not (line 481):

```
            file_order("BINDING_SUSPECT",
                       "%s answers its API but none of its catalogued titles resolve -- the "
...
                       "BOTS", "MINOR", where=host, evidence=h.get("reason"),
                       found_by="binding_health.canary")
```

So `--sweep`'s "swept: %d filed/refreshed" (line 598) under-reports by the number of
BINDING_SUSPECT orders. It also discards the `None` return that line 573's comment says must not
be counted as filed — here it cannot be counted at all, in either direction.

---

## src/zfighters.py

### F8 (MAJOR, LOCAL) — `--full` raises `KeyError: 'provenance'` on the carried-in Son Goku sheet, and the atomic write never happens

The Goku record is loaded from a different producer (lines 434-440):

```
    try:
        p = os.path.join(HERE, "data", "REFERENCE_ASSAYS_PRESENCE.json")
        with open(p, encoding="utf-8") as f:
            out["Son Goku"] = json.load(f)["Son Goku"]
```

`main()` already knows that record has a different shape at the top level (lines 454-456):

```
        # Goku's sheet is carried in from the presence rebuild and does not repeat the anchor
        # and epoch at the top level -- both are inside the assay result there.
        anchor = rec.get("anchor") or rec["assay"].get("magnitude", "?")
```

but the `--full` worksheet loop indexes a key Goku's axes do not carry (lines 471-474):

```
        for ax in A.WEIGHTS:
                d = rec["axes"][ax]
                print("   %-15s%5.1f  [%s] %s"
                      % (ax, d["score"], d["provenance"], d["cited"][:60]))
```

Verified against the file on disk: every one of Goku's eleven axes in
`data/REFERENCE_ASSAYS_PRESENCE.json` has exactly `['cited', 'score']` — no `provenance`.
The local roster's axes get theirs synthesised at line 417
(`{"score": v[0], "cited": v[1], "provenance": v[2]}`); the carried-in one does not.

Second-order cost: the crash lands before line 478,

```
    silence.write_json(OUT, out, indent=1, ensure_ascii=False)
```

so `python src/zfighters.py --full` never refreshes `data/Z_FIGHTERS.json` — the file
`pantheon.py` reads. A person asking for the full worksheets gets a traceback and a silently
un-updated artifact.

---

## src/scout.py

### F9 (MAJOR, LOCAL) — `_land` writes through a fixed `path + ".tmp"`, colliding by name with `hostcheck._land` on the very file both docstrings say is shared

`scout.py:59-69`:

```
def _land(path, obj, sort_keys=True):
    """Write a shared artifact whole or not at all -- tmp + `silence.replace_retry`.

    WIKI_HOSTS.json in particular is written from here AND from two call sites in
    `hostcheck.py`, and read by several long-running jobs. ...
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(obj, f, indent=1, sort_keys=sort_keys)
    silence.replace_retry(tmp, path)
```

`hostcheck.py:67-79` is the same construction with the same temp name:

```
def _land(path, obj, sort_keys=True, ensure_ascii=True):
    """Write a shared artifact whole or not at all.
...
    tmp = path + ".tmp"
```

`silence.write_json`'s own docstring names this exactly:

```
    THE TMP NAME CARRIES PID AND THREAD, which the older hand-rolled `path + ".tmp"` sites did
    not. Two writers of the same path otherwise collide on the temp file itself, and the loser
    can replace the winner's target with a partial file
```

This is the same defect run #33 fixed in `runguard._land`, whose docstring (`runguard.py:75-83`)
records `runguard._land:PermissionError` firing 99 times in production as evidence that the
contention is real rather than theoretical. `scout._land` is the surviving instance, on
`WIKI_HOSTS.json`, `SCOUT_ATTEMPTS.json`, `SCOUT_BLOCKED.json` and `SCOUT.json`.

### F10 (MINOR, RUN) — three read-modify-writes on shared artifacts with no compare-and-swap

`SCOUT_ATTEMPTS.json`, read at 284 and written at 307 with the whole map:

```
        seen = json.load(open(ATTEMPTS, encoding="utf-8")) if os.path.exists(ATTEMPTS) else {}
...
    for src in order:
        seen[src] = now
    _land(ATTEMPTS, seen)
```

`WIKI_HOSTS.json`, lines 226-229:

```
            hosts = json.load(open(F.HOSTS, encoding="utf-8"))
            hosts[source] = "pages:" + source
            _land(F.HOSTS, hosts)
```

`SCOUT_BLOCKED.json`, lines 236-241:

```
            prev = {}
            if os.path.exists(BLOCKED):
                with open(BLOCKED, encoding="utf-8") as f:
                    prev = json.load(f)
            prev[source] = sorted({c["url"] for c in blocked} | set(prev.get(source) or []))
            _land(BLOCKED, prev)
```

Each is a whole-file snapshot taken, mutated, and landed unconditionally — the shape
`workorders._mutate` and `runguard._land_claim` were both given CAS for today. The
`WIKI_HOSTS.json` one is the sharpest: `hostcheck.adopt()` writes the same map from another
process, and a lost update there un-adopts a host silently. The `SCOUT_ATTEMPTS.json` one
matters because losing a stamp puts a source back at the front of the rotation, which is the
failure the sweep fix was landed to end.

### F11 (MINOR, LOCAL) — stale line-number tag

Line 324:

```
    except Exception:
        silence.note("scout.py:241")
        prev = []
```

The handler is at line 324, not 241, and line 241 is `_land(BLOCKED, prev)` — a different
swallow entirely. Every other handler in this file uses a content label
(`scout.py:_ask`, `scout.py:verify`, `scout.py:blocked`, `scout.py:register-host`,
`scout.py:attempts-unreadable`). The tag is the key `state/failures.json` aggregates on and the
one `overnight.ledger_report` prints, so a reader chasing this class is sent to the wrong line —
the exact drift `overnight.py:318-324` documents having fixed in five of its own tags.

### AUDIT OF TODAY'S `sweep()` FIX — it holds

I attacked the fix rather than accepting it. It is correct:

- ordering is `sorted(todo, key=lambda s: (float(seen.get(s) or 0.0), -len(todo[s])))` (290) —
  never-attempted sorts to 0.0 and therefore first; entry count is demoted to a tie-break;
- the stamp is written BEFORE the work (301-307), so a source that crashes the scout still
  counts as attempted and cannot re-pin the window — the comment says this and the code does it;
- `deferred` is computed and PRINTED by name (291-300), so the far side of the window is visible;
- `foreman.scout_hostless()` still calls `SC.sweep(limit=4)` (`foreman.py:192`), which is now a
  rate rather than a membership decision, exactly as the docstring claims.

The one hole in it is F10: the rotation is only as good as the `SCOUT_ATTEMPTS.json` write, and
that write has no CAS.

---

## src/runguard.py

### F12 (MINOR, RUN) — `beat()` and `release()` protect their invariant with a check-then-write, and the docstring's reason for skipping CAS describes a different race

`_land_claim`'s docstring, lines 106-108:

```
    `beat()` and `release()` do not need this. Their protection is the ownership check -- they
    refuse outright to touch a record carrying another agent's name -- and a heartbeat that
    loses a CAS race with itself has nothing useful to do about it.
```

But the ownership check is a read (189/215) and the write (205/229) is unconditional:

```
    rec = read(path)
...
    owner = rec.get("agent")
    if owner != agent:
        print("runguard: REFUSING to refresh a heartbeat for %r ...
        return False
...
    rec["heartbeat"] = time.time()
    return _land(rec, path)
```

The race is not a heartbeat against itself. It is a heartbeat against a CLAIMANT. If a
successor's `claim()` lands between our `read()` and our `_land()`, `_land` writes back the
record we read — our agent name, `done: False`, a fresh heartbeat — and the successor's claim is
erased with no trace anywhere. That is m27 exactly: a live run's guard handed to, or taken from,
the wrong owner by a write that succeeded and wrote the wrong thing.

The window is narrow (a successor can only claim once our heartbeat is `STALE_AFTER_S` old, so
this needs a long block followed by a beat), which is why I am filing this MINOR and not MAJOR.
But it is narrow in the same way `claim()`'s window was narrow before run #33's CAS was added,
and this module's whole thesis is that the guard's invariants are held by code rather than by
how unlikely the interleaving is. `release()` has the identical shape and its own docstring
(211-213) states the invariant as absolute.

The rest of the module audits clean. In particular `claim()`'s digest ordering is genuinely
digest-then-read as its comment claims (160-161):

```
    expected = silence.digest_of(path)
    prior = read(path)
```

---

## src/wh40k.py

### F13 (MINOR, OWNER) — every axis is stamped `[wiki]` including the ones with no quoted material

`compute()`, line 197:

```
        sheet = {ax: "[wiki] " + v[1] for ax, v in rec["axes"].items()}
```

The roster's evidence strings are a mixture. Some are verbatim quotations; many are editorial
judgment with nothing quoted at all, e.g.

```
   celerity=(2.0, "The slowest thing in the setting, deliberately. He does not need to arrive"),
...
   volition=(9.5, "Absolute and unsplittable. He wants ONE thing and has never wanted anything
                  else"),
...
   discernment=(4.0, "Sees violence and nothing else. Blind to everything Tzeentch trades in"),
```

Its twin does this correctly. `zfighters.py` carries provenance per axis and says why
(lines 14-16):

```
So each sheet below fixes an epoch, and cites the record at that epoch. Provenance is marked
per axis: [wiki] where the sentence is in the mined cache verbatim, [canon] where the event is
on-panel at the locus given and the miner did not surface it.
```

and its `compute()` reads the marker off the tuple rather than assuming it
(`zfighters.py:412`: `sheet = {ax: "[" + v[2] + "] " + v[1] ...}`).

`wh40k.py:230-236` already records that this file is `zfighters.py`'s twin and that a ruling
applied to one was not applied to the other. This is a second instance of that. Marking an
unquoted editorial judgment `[wiki]` overstates the provenance of the evidence in a file whose
entire output is a worksheet of citations, so the call on how to re-mark them is curatorial —
OWNER.

Everything the docstring asserts about the data checks out against `compute()`:
Tzeentch M7.86, Slaanesh M7.85, Nurgle M7.80, Khorne M7.76, the Emperor M6.76; Tzeentch has
the highest transgression (9.9) and the lowest volition (6.0) of the four, which is what
"the deepest transgression and the worst discipline" claims.

---

## src/chord_field.py

### F14 (MINOR, OWNER) — the module is never imported and none of its six public functions has a caller

A repo-wide search for `chord_field`, `total_beta`, `landauer_floor`, `recoil_momentum`,
`recoil_velocity`, `critical_power_self_focus` and `ADJUDICATIONS` finds, outside this file and
the handoff archive, exactly one hit: the bare STRING `"chord_field"` inside a list of module
names at `derivation.py:477`,

```
SCAN_MODULES = ["assay", "feats", "cosmography", "propagation", "descending_ladder",
                "scale_theories", "chord_field", "resonance", ...]
```

which `scan_constants(mod)` uses to read the file's module-level UPPERCASE assignments off disk
by `ast.parse` — it never imports the module and never touches a function. So
`ADJUDICATIONS`, `total_beta()`, `per_system_beta_without_unification()`, `landauer_floor()`,
`recoil_momentum()`, `recoil_velocity()` and `critical_power_self_focus()` are unreachable from
anything that runs.

Already recorded once, as INFO, by run #33 batch 03 (finding 8), which also noted that sweep31
batch15 and sweep32 batch10 both read the file and called it clean without flagging it. Filing
it as an order rather than leaving it in a fourth audit file is the point of the owner's ruling
about where findings go. The module's arithmetic is correct where I could check it —
`recoil_momentum` is E/c, and the docstring's own worked example (1e20 J giving ~3e11 kg*m/s)
matches 1e20 / 2.998e8 = 3.34e11.

Note the constants ARE reachable, by `derivation.scan_constants`, so `G_NEWTON` and `HBAR`
being unused inside this file is not by itself dead code — that is why this finding is about the
functions and the module import, not about the constants.

---

## src/withdraw_chapters.py

### F15 (MINOR, LOCAL) — hand-rolled fixed temp plus a discarded write verdict where `silence.write_json` belongs

Lines 92-98:

```
    if a.go:
        # The withdrawn catalog is the record of WHAT was withdrawn; keep it beside the files.
        shutil.copy(CATALOG, os.path.join(arch, "catalog.withdrawn.json"))
        tmp = CATALOG + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump({}, f, indent=2)
        silence.replace_retry(tmp, CATALOG)
```

Same `path + ".tmp"` collision hazard as F9, on `output/index/catalog.json` — a file
`generate.py` and `publish.py` both read — and the boolean `replace_retry` returns is dropped on
the floor. This is the one write in the script that runs AFTER all the chapter files have
already been moved, so a denied replace leaves a catalog full of paths whose files are gone. The
line the module already imports `silence` for is `silence.write_json(CATALOG, {}, indent=2)`.

The subsequent print does re-read the file (104-105), so the failure is not fully silent — but
nothing acts on it and nothing raises.

### F16 (MINOR, RUN) — a re-run overwrites the archive it exists to preserve, because the label default is a hardcoded date

Line 39:

```
    ap.add_argument("--label", default="2026-08-25")
```

Line 42: `arch = os.path.join(HERE, "output", "withdrawn_" + a.label)`.

State on disk right now: `output/index/catalog.json` holds **0 entries** and
`output/withdrawn_2026-08-25/raw` holds **148 files** — the withdrawal has already been carried
out, and because the module MOVES rather than copies (docstring, lines 8-11) that archive is the
only copy of those chapters. A second `--go` with no `--label` writes into that same directory.
The stray-sweep at 88-90 is not guarded:

```
            if a.go:
                shutil.move(src, os.path.join(arch, "raw", f))
```

`shutil.move` onto an existing non-directory destination falls back to `copy_function` +
`unlink` when `os.rename` raises, i.e. it overwrites. So a newly generated chapter in
`output/raw` that shares a filename with a withdrawn one replaces the withdrawn one
irrecoverably. Note the contrast with the catalog path immediately above, which takes and
VERIFIES a snapshot before proceeding (lines 47-60) — the protection was thought about for the
catalog and not for the archive.

The unguarded `shutil.move` at line 89 is also the only move in the file with no `try/except`;
the catalog-driven one at 73-77 has one.

---

# QUESTIONS

1. **zfighters.py — "these fifteen".** The docstring's opening sentence is "The mined evidence
   for these fifteen is epoch-skewed to the point of uselessness", and `ROSTER` holds fourteen.
   `main()` carries Son Goku in from `REFERENCE_ASSAYS_PRESENCE.json` (434-440) to make the
   printed ranking fifteen. If "these fifteen" means the printed table, the prose is right and
   only "each sheet below" (line 14) is loose, since Goku's sheet is not below. If it means the
   hand-built sheets, the number is off by one. A curatorial call, not a defect I can prove.

2. **zfighters.py — "above Vegeta and every Earth-raised fighter except Goku".** Computed, this
   is true of Vegeta (17 at M7.60 vs M7.53) but Vegito scores M7.63, above 17. Whether a Potara
   fusion of Goku and Vegeta counts as "an Earth-raised fighter" for the purposes of that
   sentence is the owner's call, and the sentence may be about the anchor rather than the
   decimal. Not filed.

3. **scout.py — `verify()` with an empty name list.** `needed = max(1, min(MIN_NAME_HITS,
   probeable))` (193) floors at 1 even when `probeable` is 0, and `hits` over an empty name list
   is always 0, so `ok` is unconditionally False. Unreachable from `sweep()` (which only reaches
   `verify` through `scout()`'s `sample`), but `main()`'s `--source` path can hand `scout()` a
   record whose entries all have names of three characters or fewer (345-346), producing exactly
   that state. This is the mirror of the "check that cannot pass" the function's own docstring
   (155-171) says was fixed. Whether the residual edge is worth a distinct verdict
   ("nothing probeable") rather than an ordinary failure is a design call.

4. **overnight.py — is `_gl.status()["slots"]` meant to be a hard key?** Line 709 indexes
   `"slots"` rather than `.get`, inside the keep-warm loop's broad `except Exception:` (726). If
   `gpu_lane.status()` ever stopped returning that key, keep-warm would note-and-skip every
   120 s for the process lifetime and look identical to a card that is permanently busy. I could
   not establish that `gpu_lane.status()` can omit it, so this is a question, not a finding.

5. **withdraw_chapters.py — `missing` conflates two states.** Lines 66-70 increment `missing`
   both when a record has no `raw_path`/`compressed_path` key at all and when the key exists but
   the file is gone, and the label printed at line 102 is "paths already gone". I could not
   prove the first case occurs: the live catalog is empty, so there is nothing to sample. If
   every catalog record always carries both keys, the counter is honest and this is nothing.

6. **withdraw_chapters.py — should a spent one-off still be in `src/`?** The ruling it
   implements was carried out (empty catalog, populated archive). Keeping it is defensible as
   the record of how the withdrawal was done; so is retiring it. An owner question either way,
   and F16 is the reason it matters rather than being purely cosmetic.

7. **overnight.py — `snap["cycle_seconds"]` on a failed snapshot.** Line 849 sets
   `cycle_seconds` on whatever `coverage_snapshot()` returned, including the `{"error": ...}`
   dict, so the idle accounting at 874-880 still works on a crashed snapshot. That reads as
   deliberate and correct to me; noting it only so the next reader does not re-derive it.
