# SWEEP 34 — BATCH 12 AUDIT

Modules read end to end (3,216 lines total):

    src/hostcheck.py (953)   src/health.py (592)   src/completeness.py (482)
    src/escalation.py (356)  src/navtree.py (275)  src/catalogue_codex.py (229)
    src/snapshot.py (210)    src/repass_bands.py (119)

Auditor only. Nothing under `src/` was edited. `escalation.clear()` and `escalate()` were NOT
called; the standing halt was not touched, read only through the source.

11 findings filed, 10 questions. Two findings already on the queue before this batch started
(`CODEX_WEAPON_PROPERTY_UNMAPPED`, `state/failures.json.corrupt` never triaged) are confirmed
below but not re-filed.

---

## health.py

### FINDING H-1 (MAJOR) — `check_state()`'s "UNREACHABLE" verdict cannot fire. health.py:396-409

The check that separates permanent loss from queue backlog is tautologically false in the
`lost` direction. It is the newest code in the file (comment dated 2026-08-25) and its own
comment claims the distinction is now measured.

```
396                n = sum(1 for e in batch if not P.entry_settled(e))
397                if not n:
398                    continue
399                if P.batch_settled(key, done, batch):
400                    # The gate would SKIP this span: these entries are genuinely unreachable.
401                    lost += n
...
403                else:
404                    queued += n
```

and, `pipeline.py:1174`:

```
1174    return key in done_keys and all(entry_settled(e) for e in batch)
```

Line 397 guarantees at least one `e` in `batch` for which `entry_settled(e)` is False.
`all(entry_settled(e) for e in batch)` is therefore False for every batch that reaches line
399, so `batch_settled()` is False every time it is asked here. (`key in done_keys` is also
already guaranteed — line 385, `if key not in done: continue`.) Consequences:

* `lost` is permanently 0 and `lost_where` permanently empty;
* the row `("entries UNREACHABLE in closed batches", ...)` can never be appended to `out`,
  so it can never reach the preflight stamp, `workorders.sweep_detectors`, or a person;
* the file's own claim, at line 375, "A count and a REACHABILITY test are different questions;
  this now asks both and says which" — is enforced by a comparison that has one answer.

This is the flagship shape: a check that cannot fail looks exactly like a check that passed.
Note the concept, not only the code, is now unreachable: under the current `batch_settled`, a
span the gate would skip is by definition a span with every entry settled, which line 397 has
already `continue`d past. Whatever "unreachable" is supposed to mean after the 2026-08-24 gate
fix, this expression is not it — which is why the handler is RUN and not LOCAL.

### FINDING H-2 (MINOR) — a third spelling of the cache-directory key. health.py:288

```
288        quarantined = {h.replace(".", "_").replace("-", "_") for h in _BH.quarantined()}
```

The comment directly above it (283-287) is explicit that getting this spelling wrong "would have
made this whole exemption a no-op that still LOOKED implemented — the failure mode this project
calls a check that cannot fail." The repair hand-spelled the key a third time instead of calling
the module that exists to be the only copy of it:

```
cachekey.py:56    def host_dir(host):
cachekey.py:58        return _SANITISE.sub("_", host or "")[:HOST_CAP]      # HOST_CAP = 40
```

The two spellings diverge for any host carrying punctuation outside `.`/`-`, and for any host
longer than 40 characters. Measured against the live map: 5 of 196 hosts differ, and one of them
already has a directory on disk in the cachekey spelling —
`data/feats/doc_arcanum_worlds_odyssey_of_the_dragon` (exactly 40 chars) for host
`doc:arcanum-worlds-odyssey-of-the-dragonlords`, which health would spell
`doc:arcanum_worlds_odyssey_of_the_dragonlords`. Latent today (the only quarantined host is
`www.dandwiki.com`, which both spellings render `www_dandwiki_com`) — it becomes a silent no-op
the day one of those five is quarantined.

### CONFIRMED, ALREADY FILED — `failures.json.corrupt` is written and never triaged (115-122).

---

## completeness.py

### FINDING C-1 (MAJOR) — `host_reachable`'s RAW/Wikipedia handling cannot run; 32 sources get no row at all. completeness.py:248 vs 155-235

`audit()` admits only Fandom hosts:

```
248        todo = [(src, h) for src, h in hosts.items() if subdomain(h)]
```

```
59     def subdomain(host):
61         if not isinstance(host, str) or not host.endswith(".fandom.com"):
62             return None
```

`work()` is mapped over `todo` only, and `work()` is the sole production caller of
`host_reachable` (verified: the other three matches in `src/` are a comment in `foreman.py` and
`verify_math`'s monkeypatch). So every branch in `host_reachable` that exists for non-Fandom
hosts is unreachable in production, including the two the docstring is mostly about:

```
220            if mode == EP.MODE_RAW:
...
181     The API PATH is resolved through `endpoint.api_url`, never hardcoded ... Hardcoding
183     `/api.php` here reported en.wikipedia.org as unreachable ... which would have marked
183     all 21 Wikipedia-hosted sources unreliable for no reason.
```

Wikipedia-hosted sources are never passed to this function. Neither is `www.dandwiki.com`, the
named subject of the run #28 MODE_RAW repair at lines 195-211 ("every RAW host on the corpus has
been scored unreachable since this function was written"). Measured on the live map: of 196
hosted sources, 32 are not `*.fandom.com` — 22 `en.wikipedia.org`, 4 `www.dandwiki.com`,
`rimworldwiki.com`, and 5 `pages:`/`doc:` sentinels.

The second half is the more serious half. Those 32 sources get **no COMPLETENESS.json row of any
kind**, which is precisely the condition `work()` warns about twelve lines further down:

```
282        # A HOST THAT IS DOWN STILL GETS A ROW. ... The row matters: a
284        # source missing from COMPLETENESS.json reads downstream as "nothing on the wiki", which
285        # is the opposite of "we could not ask" ...
```

`subdomain()`'s own docstring ("Non-fandom hosts have no category API we can use this way") makes
the exclusion defensible as a measurement decision, but it is not carried through: there is no
`unreliable` row saying so, and the module's stated invariant that a source never goes missing is
violated for 16% of the roll. Handler RUN: either emit an unmeasurable row for the 32, or strike
the unreachable branches and the paragraphs justifying them.

### FINDING C-2 (MINOR) — `category_size()` is dead, and its docstring claims callers it does not have. completeness.py:122-129

```
122     def category_size(sub, category):
128         the same question 48 times a day."""
129         return category_size_probe(sub, category)[0]
```

```
92          `category_size` stays as it was for every caller that only wants the number."""
```

There is no such caller. `grep -rn "category_size\b" src/*.py` excluding `category_size_probe`
returns only this definition and four mentions inside `category_size_probe`'s own docstring and
its `silence.note("completeness.py:category_size")` tag. The only importer of `completeness` in
`src/` is `verify_math.py`, which patches `HOSTS`, `RECORDS`, `host_reachable` and
`category_size_probe` — never this. Filed to OWNER because deleting a public function is a
curatorial call.

### PRE-EMPTIVELY NOT FILED — the SHRINK_FLOOR path (409-415) is the deliberate guard, and the
"measured 0 rows" line is `verify_math`'s self-test of it, not a live fault. Confirmed, not a
finding. Existing order 662b9fc2d7e2 already covers the no-record-on-disk row at 325-358.

---

## escalation.py

READ ONLY. `clear()` was not called, `escalate()` was not called, the standing halt
(state/HALT.json, DRILL_BREACH) was not read for the purpose of lifting anything.

### FINDING E-1 (MAJOR) — a halt that fails to land is reported as raised. escalation.py:197-207

```
197        try:
199            tmp = HALT_FILE + ".tmp"
200            with open(tmp, "w", encoding="utf-8") as f:
201                json.dump(payload, f, indent=1, ensure_ascii=False)
202            silence.replace_retry(tmp, HALT_FILE)
203        except Exception:
206            silence.note("escalation.py:halt-write")
207            sys.stderr.write("CANNOT WRITE HALT FILE — %s: %s\n" % ...)
```

`silence.replace_retry` does not raise on failure — it returns False:

```
silence.py:331            except PermissionError:
silence.py:332                if a == attempts - 1:
silence.py:333                    note("replace-denied:" + os.path.basename(dst))
silence.py:336        return False
```

So the one failure mode this file's own comments treat as routine everywhere else (Windows
denies the rename while a reader holds the destination — and every `assert_clear()` caller in
the kit reads HALT.json) produces: no halt file, no stderr, no exception, and `escalate()`
returning the record to a caller that has every reason to believe the library is now stopped.
The `except` arm cannot cover it, because nothing was raised. This is the same defect class the
sibling modules were hardened against today (`completeness.land` at 428-433 spells out the
correct handling: "Both of them protect the CONTENT; neither checks that the content reached the
disk"), on the single most important write in the kit.

### FINDING E-2 (MAJOR) — a denied clear reports success. escalation.py:310-316

```
310        tmp = HALT_FILE + ".tmp"
311        with open(tmp, "w", encoding="utf-8") as f:
312            json.dump(rec, f, indent=1, ensure_ascii=False)
313        silence.replace_retry(tmp, HALT_FILE)
...
316        return True
```

and the caller:

```
336            did = clear(a.ruling, by="owner-cli")
340        print("halt cleared." if did else "nothing was halted.")
```

Same discarded verdict, opposite direction: a denied rename leaves HALT.json holding
`"cleared": false` while the person at the CLI is told "halt cleared." and the process exits 0.
The library then keeps refusing while its operator believes it has been released — and the
written ruling, which is the entire reason `clear()` demands words, is not on disk either. Note
the runtime caller-guard added today (`_by_a_person_at_the_cli`, 252-281) is sound on its own
terms and is NOT the subject of this finding; both conditions (`__main__.__file__` is this file,
frame 2 is this file's `main`) are correct, and `clear()`'s deliberate refusal ordering matches
what `drill.py` probes.

---

## hostcheck.py

### FINDING X-1 (MINOR) — the `--purge` help text is the claim the code says it never had. hostcheck.py:916-917

```
916        ap.add_argument("--purge", action="store_true",
917                        help="remove rosters the audit rejected AND whose host was independently rejected")
```

against `purge()`'s own docstring:

```
644        The safety here is the HUMAN, not a second automated condition. An earlier docstring
645        claimed the code also required the host to have been independently rejected; it never did
646        (the check was loaded and unused), and pretending a safeguard exists is worse than naming
647        the real one: nothing is purged except sources a person explicitly listed with --source
```

The docstring was corrected; the argparse help — the string an operator actually reads at the
terminal before running a destructive command — still advertises the phantom second safeguard.
Verified against the body: `targets` (670-676) is built purely from `only` and the audit rows,
and `hosts.get(src)` is recorded as `now` for the log, never used as a gate.

### FINDING X-2 (MINOR) — `purge()` re-spells the cache-directory key. hostcheck.py:711

```
711                d = os.path.join(HERE, "data", base, re.sub(r"[^A-Za-z0-9]+", "_", mined)[:40])
```

This is `cachekey.host_dir` copied by hand — the fifth copy of a convention whose module header
says "ONE HELPER, NOT FOUR SPELLINGS ... four independent copies of one convention is four
chances for the next edit to drift", and which names `hostcheck.py` as one of the four sites it
was consolidating. Byte-identical output today, so the damage is latent; the reason to report it
is that it is invisible to the net that is supposed to catch it — `verify_math`'s "%s reads
entity caches through cachekey" check is satisfied by `roster_audit`'s legitimate
`cachekey.load()` call at 799-801, so the module passes while a second site still hand-rolls the
path. A rule applied at some of its sites is the project's own standing lesson 14.

---

## navtree.py

### FINDING N-1 (MINOR) — `import silence` runs before the path insert. navtree.py:26-35

```
26     import argparse
30     import silence
32     HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
33     sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
```

Every other module in this batch inserts first and imports siblings after, and the tree states
this as its convention where it exempts E402 wholesale:

```
secondopinion.py:116    "E402": "src/ modules do sys.path.insert before importing siblings; the
                         import cannot precede it",
```

Here it does precede it. It survives today only because `src/` happens to be on `sys.path`
already (script invocation, or an importer that inserted it first — `allsweep` and `sweep.py`
both reach navtree). It is a mechanical single-line fix and it removes an exception to a rule the
tree claims is universal.

### FINDING N-2 (MINOR) — the audit's problem list is truncated to six with no other record. navtree.py:257-270

```
257        problems = audit(data)
258        print(f"\nAUDIT: {len(problems)} problems")
259        for p in problems[:6]:
260            print("   " + p)
262        if args.write and not problems:
```

`audit()`'s findings are never written anywhere — the file is written only when the list is
empty (262), and nothing else calls `audit()`. So problems 7..N of a broken tree exist for the
length of one function call and are then unrecoverable without editing the source. The count is
honest, which is what makes it the bad case the module's own header names: "The count in the
panel was right and the bubbles were a subset, which is the worst combination: it looks complete
and is not." Ranking is fine; truncating a findings list with no full copy anywhere is Hard Rule
0 applied to the diagnostics.

---

## repass_bands.py

### FINDING R-1 (MINOR) — a hardcoded corpus size in the printed report. repass_bands.py:98

```
98        print(f"  demoted to unassayed: {len(demoted_sources):,} of 211")
```

The denominator is a literal. `demoted_sources` is accumulated over `PL.records()`, which is
every `data/records/*.json` holding entries. Measured on disk: **216 record files, 216 distinct
sources**. The printed fraction has understated its denominator by five since the roll last grew
and will drift further with every source added.

---

## catalogue_codex.py

No new findings. The already-filed `weapon property` gap is confirmed by measurement: parsing
the codex's Part Two manifests yields exactly one element type absent from `TYPE_CATEGORY`,
`weapon property`, at **35 occurrences**, all of them defaulting to THINGS via
`TYPE_CATEGORY.get(etype.lower(), THINGS)` (line 173). No second unmapped type exists.

## snapshot.py

No findings. Two things that look like defects and are not, checked and cleared:

* `before()` skipping a path that does not exist (63-64) is correct — a destructive step cannot
  destroy what is not there, and the all-missing case does raise (82-85).
* `before()` is not dead: `withdraw_chapters.py:53` calls it for real, `drill.py` for the nets.

---

# QUESTIONS

**Q1 (snapshot.py:124-155).** `verify()` restores the snapshot into a temp dir and compares the
result against *the same snapshot*, using copies made by `shutil` moments earlier in the same
process. It can fail on a manifest that will not parse, on a file the snapshot no longer holds,
and on a copy error — but it cannot fail because the snapshot does not match what was originally
taken. Given the module's premise ("An untested backup is a belief"), is proving copyability the
intended contract, or should `before()` record per-file digests of the SOURCE so `verify` has
something independent to compare against?

**Q2 (health.py:190-191).** `except Exception: pass` on the samples write, with the reason
discarded entirely and not even a `silence.note`. The comment ("the evidence bag must never break
the ledger write") justifies not raising, but not the silence. Is the omission deliberate because
`silence.note` re-enters `health` and arms `flush()` via `atexit`?

**Q3 (escalation.py:304-313).** If HALT.json is unreadable, `status()` hands back the synthetic
`HALT_FILE_UNREADABLE` record and `clear()` then writes a fresh, parseable file over the corrupt
one — the original bytes are gone. `health.flush()` treats preservation as the precondition for
exactly this case ("overwriting an unreadable ledger we could not first preserve would destroy
the only copy of whatever tore it"). Should the halt file get the same `.corrupt` treatment, or
is a person at the CLI ruling on it enough?

**Q4 (escalation.py:77-84).** `OWNER` is the only rung whose `_FIELDS` tuple omits `level_name`,
so the per-source line `_append_log` writes for a halt (127-128) carries no level at all, while
every other rung's does. Deliberate distillation, or an omission?

**Q5 (repass_bands.py:59).** `if not e.get("catalogued"): continue` is the pre-2026-08-24 gate
spelling that `pipeline.entry_settled` was created to be the only copy of. A struck entry
(`catalogued=False` + `excluded`) is therefore never re-passed and keeps both its unearned
magnitude and a `scale_note` that fails the corrected gate. Harmless because the entry is
excluded, or should the demotion cover struck entries too?

**Q6 (whole batch).** None of these eight modules calls `escalation.assert_clear()`.
`verify_math`'s `_INTERLOCKED` set is exactly eight standing jobs (dashboard, feats, foreman,
overnight, overwatch, pipeline, publish, read). But `hostcheck --repair` / `--purge --go`,
`health --reopen --go`, `catalogue_codex`, `repass_bands --apply` and `navtree --write` all write
shared state, and a hand-run invocation of any of them proceeds during a standing halt. Is the
interlock deliberately scoped to standing jobs, on the theory that the orchestrator refuses
first?

**Q7 (catalogue_codex.py:100).** The manifest's declared per-type count is captured — `\((\d+)\)`
— and discarded; nothing checks the parsed names against it. Checked before reporting: today
**4,489 declared and 4,489 parsed, zero mismatched lines**, so there is no live fault. Worth an
assertion anyway, given a lost `;` split would read as a smaller manifest?

**Q8 (hostcheck.py:294-304 vs 369).** "TWO LISTS, BECAUSE ONLY ONE OF THEM MAY BE TRUNCATED ...
capping them is right" — but `candidates()` now returns `grounded + spec` uncapped, and the cap
lives in the caller instead (`hosts.py:166`). The comment is normative rather than descriptive,
so this is a question rather than a doc-drift finding: is the paragraph still the intent?

**Q9 (completeness.py:71-79).** `_cs_load()` swallows every read error under "no cache yet is the
normal first state", so a torn `state/category_sizes.json` is indistinguishable from a first run
and is then overwritten wholesale on the next probe. Acceptable for a pure cache?

**Q10 (hostcheck.py:698).** `n_entries = len(r.get("entries") or [])` is assigned, not
accumulated, inside the loop over record files, so a source spread across two record files would
log only the last file's count. Benign today — measured: 216 record files, 216 distinct sources,
none appearing twice.
