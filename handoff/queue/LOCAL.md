# LOCAL rung -- 52 open orders

## c16499b0a50b  [MAJOR]  SWEEP33_FINDING

- **where**: b08 resonance.py
- **found_by**: sweep33-batch08
- **seen**: 1

resonance.py — the whole module is unimported anywhere in src/, contradicting its own docstring

```
{
  "batch": 8,
  "report": "handoff/sweep33/AUDIT_batch08.md"
}
```

## ae05af0b5492  [MAJOR]  SWEEP34_FINDING

- **where**: src/standards.py:1101-1104
- **found_by**: sweep34-batch04
- **seen**: 1

standards check() writes state/job_progress.json with a FIXED tmp name and DISCARDS the replace_retry verdict. If the replace is denied - and this file is read by every check() run, the modules own stated normal case for replace_retry - the size stamps never persist, prev stays stale, job_stamp() returns held=False every pass, and quiet_min can never reach MAX_JOB_SILENCE_MIN. That is exactly the failure the comment eleven lines above (1072-1079) says was already found and fixed once: "The standard this file own docstring calls the failure this whole library is built to refuse was therefore st

```
{
  "batch": 4,
  "proof": "tmp = JOB_WATCH + \".tmp\"\nwith open(tmp, \"w\", encoding=\"utf-8\") as f:\n    json.dump(cur, f)\nsilence.replace_retry(tmp, JOB_WATCH)"
}
```

## 26c8ed2c095b  [MAJOR]  SWEEP34_FINDING

- **where**: src/publish.py:550,585,653
- **found_by**: sweep34-batch15
- **seen**: 1

publish.push() returns bare False from two unrelated states -- "nothing to commit" (line 550) and "committed but the rebase onto origin/main failed, push HELD" (line 585) -- and main() line 653 prints "no change to push" for both, leaving rc=0. A one-shot --push by a person therefore exits 0 having committed work that never reached the public repo, and stdout says there was nothing to send. Only the stderr line tells the truth. Same shape as the defect main()'s own comment at 638-646 ("A REFUSED PUBLISH MUST NOT REPORT SUCCESS") was written to fix.

```
{
  "batch": 15,
  "proof": "porcelain = git(\"status\",\"--porcelain\")\nif not porcelain:\n    return False        # line 550\n...\nprint(\"push held: rebase onto origin/main failed (\"...); return False   # line 585\n...\nprint(\"pushed\" if push() else \"no change to push\")   # line 653"
}
```

## 6a83762ab9bb  [MAJOR]  SWEEP34_FINDING

- **where**: src/hosts.py:158
- **found_by**: sweep34-batch11
- **seen**: 1

hosts.py:158 calls HC.candidates(source, cur, by=by) and OMITS hosts=, which silently disables one of candidates()'s three generators outright: hostcheck.py:335 gates the NEIGHBOURS block on 'if by and hosts:'. This is the only caller in the tree that omits it - hostcheck.py:536 and :878 both pass 'by=by, hosts=hosts'. MEASURED over all 203 sources: 5 lose their neighbour candidate, including the docstring's own worked example (Wildemount -> criticalrole.fandom.com) and Alien/Predator. Fix: pass hosts=prim, loaded at line 142.

```
{
  "batch": 11,
  "detail": "MEASURED by diffing candidates(s, prim.get(s), by=by, hosts=prim) against candidates(s, prim.get(s), by=by) over all 203 sources in data/WIKI_HOSTS.json: 5 sources lose 5 hosts. Alien -> predator.fandom.com; Explorer's Guide to Wildemount -> criticalrole.fandom.com; Player's Handbook -> criticalrole.fandom.com; Predator -> alien.fandom.com; Who Framed Roger Rabbit -> kingdomhearts.fandom.com.",
  "proof": "hosts.py:142: prim = _load(PRIMARY, {})  ||  hosts.py:157-160: try: / cands = HC.candidates(source, cur, by=by) / except Exception: / silence.note('hosts.py:candidates')  ||  hostcheck.py:335-336: if by and hosts: / mine = set(by.get(source) or ())  ||  hostcheck.py:536: for h in candidates(src, r['host'], by=by, hosts=hosts):  ||  hostcheck.py:878: for h in candidates(src, None, by=by, hosts=hosts):  ||  hostcheck.py:285-288: 'NEIGHBOURS. ... This is what found Explorer's Guide to Wildemount -> criticalrole.fandom.com at 90%: Wildemount IS Critical Role's setting, and no string manipulation on the title would ever have reached it.'"
}
```

## b635a4818c81  [MAJOR]  SWEEP34_FINDING

- **where**: src/compress_store.py:56
- **found_by**: sweep34-batch03
- **seen**: 1

compress_store.py:56 throws away the write verdict. silence.replace_retry() RETURNS False when the rename is denied on every attempt (it notes 'replace-denied:<file>' and returns False rather than raising, by explicit design). store() ignores the return and unconditionally returns {'hash','path','codec','raw_bytes','compressed_bytes'} -- so a blob that never landed is reported as stored. generate.py:468-476 writes that path straight into the catalogue as 'compressed_path' plus compressed_bytes, giving a catalogue entry pointing at a file that does not exist, and catalog.py:97 opens exactly tha

```
{
  "batch": 3,
  "proof": "    tmp = '%s.%d.%d.tmp' % (path, os.getpid(), threading.get_ident())\n    with open(tmp, 'wb') as f:\n        f.write(blob)\n    silence.replace_retry(tmp, path)\n    return {'hash': h, 'path': path, 'codec': codec, ...}\nsilence.py:319-336 replace_retry(...): for a in range(attempts): try os.replace -> return True; except PermissionError ... ; return False\ngenerate.py:468 store_info = compress_store.store(text, compressed_dir); catalog[...]['compressed_path'] = os.path.relpath(store_info['path'], HERE)"
}
```

## 6673ec6bfb0b  [MAJOR]  SWEEP35_FINDING

- **where**: onomast.py:428-429
- **found_by**: sweep35-batch05
- **seen**: 1

onomast.main() discards the verdict of silence.write_json(). Line 428: silence.write_json(OUT, named, indent=2, ensure_ascii=False) -- the boolean return (True=landed, False=denied replace) is never read. Line 429 then unconditionally prints "wrote {OUT}", so a denied replace (a reader holding ONOMASTICON.json open, per silence.replace_retry docstring) is reported to the operator as a successful write. Compare worldseed.py:332-335, which checks the same call (if silence.write_json(...): print(wrote) else: print(WRITE DENIED)) -- onomast.py is the sibling that was missed.

```
{
  "proof": "onomast.py:428: silence.write_json(OUT, named, indent=2, ensure_ascii=False)  /  429: print(f\"\nwrote {OUT}\")"
}
```

## be2b133b6e95  [MAJOR]  SWEEP35_FINDING

- **where**: coverage.py:251-253
- **found_by**: sweep35-batch05
- **seen**: 1

coverage.main() discards the verdict of silence.write_json(). Line 251: silence.write_json(OUT, rows, indent=1, ensure_ascii=False) -- return value never checked. Line 252 unconditionally prints "per-source table -> {OUT}", and main() returns 0 at line 253 regardless. COVERAGE.json is read by the dashboard, standards and the published page per the comment two lines above the call (line 248-250), so a denied replace (a reader mid-poll) is reported as a landed write and the CLI exits success while the file on disk is stale. Same class as onomast.py:428 and the pattern silence.write_json document

```
{
  "proof": "coverage.py:251: silence.write_json(OUT, rows, indent=1, ensure_ascii=False)  /  252: print(f\"\nper-source table -> {OUT}\")  /  253: return 0"
}
```

## 596493b0b139  [MINOR]  SWEEP33_FINDING

- **where**: b05 address_space.py:186, 216
- **found_by**: sweep33-batch05
- **seen**: 1

address_space.py:186, 216 — `citation_card()` and `seed_from_card()` are dead code

```
{
  "batch": 5,
  "report": "handoff/sweep33/AUDIT_batch05.md"
}
```

## 918da0e4b88b  [MINOR]  SWEEP33_FINDING

- **where**: b09 Five `silence.note()` calls carry stale line-number tags ins
- **found_by**: sweep33-batch09
- **seen**: 1

Five `silence.note()` calls carry stale line-number tags instead of the project's own descriptive convention

```
{
  "batch": 9,
  "report": "handoff/sweep33/AUDIT_batch09.md"
}
```

## 671d32878fa6  [MINOR]  LIVENESS_BLIND_TO_UNUSED_VARIABLES

- **where**: descending_ladder.py:129, verify_math.py:2310,2399
- **found_by**: secondopinion: vulture 2.16
- **seen**: 1

vulture at 90%% confidence found 3 unused local variables that liveness.py cannot see at all -- it stops at module-level function definitions and never looks inside them. descending_ladder.py:129 'from_m', verify_math.py:2310 'kw', verify_math.py:2399 'socktype'. Not dead code in the liveness sense; a computed value nobody uses, which in this codebase has twice meant a check that was written and then not wired up.

```
{
  "gap": "liveness inspects module-level defs only, never function bodies",
  "house_detector": "liveness.py",
  "tool": "vulture --min-confidence 90"
}
```

## 7cf0bdf44232  [MINOR]  SECRET_SCANNER_READS_BYTECODE

- **where**: src/publish.py:scan_for_secrets
- **found_by**: secondopinion: disagreement with detect-secrets 1.5.0
- **seen**: 1

publish.scan_for_secrets flags __pycache__/drill.cpython-313.pyc line 1109 as a high-entropy 'api_key'. It is the drill's own assembled credential FIXTURE, frozen into compiled bytecode -- not a real secret, and not a file that is ever published. detect-secrets, scanning the same tree, reports zero because it does not read .pyc. This is the only disagreement between the two scanners and the outsider is right: a gate that reads compiled bytecode will produce this false positive on every run forever, and a push gate that cries wolf is a push gate that gets bypassed. Exclude __pycache__ and *.pyc

```
{
  "detect_secrets": 0,
  "house_scanner": 1,
  "site": "__pycache__/drill.cpython-313.pyc:1109",
  "why_not_real": "drill.py builds the fixture from fragments at runtime by design"
}
```

## e3a69ceb5857  [MINOR]  ADDRESS_BIT_WIDTH_DRIFT

- **where**: src/derivation.py:333, src/profile.py:20
- **found_by**: maintenance-2026-08-25b queue agents
- **seen**: 1

Both still describe the address as 74 bits. It is 89 (8 fields, 12 bytes) -- corrected in address_space.py this shift, where main() now prints TOTAL_BITS instead of a literal so it cannot drift again. These two siblings kept the old number.

## adffa670486c  [MINOR]  PHYSICS_NEGATIVE_MASS_UNCHECKED

- **where**: src/physics.py binding_energy
- **found_by**: maintenance-2026-08-25b queue agents
- **seen**: 1

float(mass_kg) ** 2 squares the sign away, so a negative mass returns a POSITIVE binding energy silently. Same class as the non-positive-radius guard added to sphere_volume and binding_energy this shift, and left outside that order's scope.

## e40b786256e1  [MINOR]  OVERWATCH_DEEP_COUNT_HAS_NO_AGE

- **where**: src/overwatch.py write_report
- **found_by**: maintenance-2026-08-25b queue agents
- **seen**: 1

The carried-forward deep-scan count is printed with no indication of its age. With the poisoning fixed this shift (17b1ddd12fc2) the number is now real, but it can still be several rounds stale and reads as current. An 'as of round N' costs one field in last_deep.

## a9259945a65b  [MINOR]  PICK_MODEL_TWO_CONTEXT_ALLOWANCES

- **where**: src/pick_model.py:190 vs :242
- **found_by**: maintenance-2026-08-25b queue agents
- **seen**: 1

resident() allows KV_GB for context while fit_note() defaults to num_ctx_gb=1.2. Two different context allowances for the same question; they should be one constant.

## dc14fdc767ce  [MINOR]  SWEEP34_FINDING

- **where**: verify_math.py:4222
- **found_by**: sweep34-batch01
- **seen**: 1

verify_math.py has a THIRD duplicated section tag: 'Section 19s' labels both the metrics-ledger-timestamp block at 2295 and the prose-interlocks block at 4222. The file's own audit of this fault at line 3390 names only 20e and 20f as shared tags, so 19s is outside whatever order that sentence refers to. Retag the later block (the tags are cited by BUGS.md and rigor.py, so this is not a print-only change).

```
{
  "batch": 1,
  "proof": "2295: # ---- Section 19s: both writers of the metrics ledger stamp a timestamp\n4222: # ---- Section 19s: THE PROSE INTERLOCKS, AT EVERY LAYER, INCLUDING THE OPERATORS\n3390: # are the stable identifier. (The separate fault that 20e and 20f are each shared by two"
}
```

## 873900f156d1  [MINOR]  SWEEP34_FINDING

- **where**: verify_math.py:3057
- **found_by**: sweep34-batch01
- **seen**: 1

verify_math.py:3057-3059 cites stale foreman.py line numbers: 'restart_reader (foreman.py:315 ...) and kill_stalled_job (foreman.py:385 ...)'. The real definitions are foreman.py:368 and foreman.py:413. foreman.py:315 is docstring prose about refusing a kill; foreman.py:385 is the process-enumeration except handler inside restart_reader. Cite by symbol name, not by line, as this file's own sweep.py:load-unreadable note idiom already recommends.

```
{
  "batch": 1,
  "proof": "verify_math.py:3057-3059 comment cites foreman.py:315 / foreman.py:385\ngrep -n 'def restart_reader|def kill_stalled_job' src/foreman.py -> 368:def restart_reader():  and  413:def kill_stalled_job():"
}
```

## d5ab260d8f71  [MINOR]  SWEEP34_FINDING

- **where**: verify_math.py:3322
- **found_by**: sweep34-batch01
- **seen**: 1

verify_math.py:3322 cites 'public page (computed by publish.py:168-172, in publish.py's process)'. publish.py:166-174 is the credential-scanner regex (dop_v1_, SG., PEM key blocks, JWTs). The standards computation meant is publish.py:330-331 (import standards as ST / s['standards'] = ST.check(s)). Correct or de-line the citation.

```
{
  "batch": 1,
  "proof": "verify_math.py:3322: #   public page   (computed by publish.py:168-172, in publish.py's process)\npublish.py:330-331: import standards as ST / s[\"standards\"] = ST.check(s)\npublish.py:168-172 is inside the SECRET regex (r\"SK[0-9a-fA-F]{32}|\" etc.)"
}
```

## 79a7d0f284a5  [MINOR]  SWEEP34_FINDING

- **where**: src/liveness.py:72-77
- **found_by**: sweep34-batch04
- **seen**: 1

liveness._parse discards the exception reason, so the unparsed row can only ever say "will not parse" and never whether it was a SyntaxError, a control character, or a mid-write truncation - the three causes the comment at lines 86-93 says it exists to catch.

```
{
  "batch": 4,
  "proof": "def _parse(path):\n    try:\n        with open(path, encoding=\"utf-8\") as fh:\n            return ast.parse(fh.read(), filename=path)\n    except Exception:\n        return None"
}
```

## 5925b90cb6d0  [MINOR]  SWEEP34_FINDING

- **where**: src/cosmography.py:133
- **found_by**: sweep34-batch14
- **seen**: 1

cosmography declares constants that nothing reads, in the module whose admissibility rests on reversibility. Its docstring (cosmography.py:18-20) claims 'every convention is a named module-level constant ... Change one, re-run, and every downstream figure moves with it'. DEFAULT_SIZE_CLASS = 'STANDARD' (cosmography.py:133) has no reader anywhere in src/; census() re-types the same string in its own signature at cosmography.py:169, so editing the constant moves nothing. Same shape, milder: KARDASHEV_TYPE_I (line 66) and EARTH_POWER_2020 (line 69) have no reader in src/ while verify_math.py:176-

```
{
  "batch": 14,
  "proof": "cosmography.py:133  DEFAULT_SIZE_CLASS = \"STANDARD\"  (grep -rn over src/: defined once, no other reference) | cosmography.py:169  def census(size_class=\"STANDARD\", galaxies=None, verbose=False): | cosmography.py:18-20  \"REVERSIBLE -- every convention is a named module-level constant with an erratum note. Change one, re-run, and every downstream figure moves with it.\" | cosmography.py:66  KARDASHEV_TYPE_I = 1.0e16  vs verify_math.py:176  check(\"Kardashev K(Type I = 1e16 W) == 1.0\", C.kardashev_K(1e16), 1.0, tol=1e-9) | cosmography.py:69  EARTH_POWER_2020 = 2.0e13  vs verify_math.py:177  C.kardashev_K(2e13)"
}
```

## e45d838478c1  [MINOR]  SWEEP_COVERAGE_VIEW_HOLDS_TEST_DEBRIS

- **where**: state/SWEEP_COVERAGE.json
- **found_by**: sweep34-batch01 + maintenance-2026-08-25b verification
- **seen**: 1

The aggregate coverage view holds 13 rows for modules that do not exist in src/: modA1.py through modF2.py under run TESTRUN_A, and sharedmod.py under run_old. Nothing in src/ writes those names -- grep finds no TESTRUN_A anywhere -- so they are one-off debris left by an interactive test that wrote into the LIVE artifact instead of a temp file, and they will not regenerate. HARMLESS TO THE PROOF, and that was worth checking rather than assuming: missing() answers from covered_by(), which merges the per-batch SHARDS under state/sweep_shards/, not from this aggregate -- the aggregate is explicit

```
{
  "aggregate_role": "convenience view for --coverage only",
  "ghost_rows": 13,
  "proof_path": "missing() -> covered_by() -> state/sweep_shards/*.json",
  "runs": [
    "TESTRUN_A (12)",
    "run_old (1)"
  ]
}
```

## fdf1814552fb  [MINOR]  SWEEP34_FINDING

- **where**: src/corpus_db.py:6
- **found_by**: sweep34-batch04
- **seen**: 1

corpus_db prose numbers disagree with disk, in the present tense, in the module whose header says "anything that disagrees with the records is this file being stale". Line 6: "walks 216 JSON files and 109,295 entries"; line 36: "against a corpus of 109,295 entries"; line 411 --no-evidence help: "skip the 109k evidence files". Measured 2026-08-25: 216 record files (correct), state/corpus.db meta.entries = 197,334, and 144,107 evidence files on disk. The 109,295 figures inside freshness() docstring lines 234-236 are timestamped historical measurements and are fine; these three are not.

```
{
  "batch": 4,
  "proof": "Every question anyone asks about this corpus currently costs a throwaway Python script that walks 216 JSON files and 109,295 entries.  [disk: 197,334 entries, 144,107 evidence files]"
}
```

## 97b39265457f  [MINOR]  SWEEP34_FINDING

- **where**: src/corpus_db.py:87
- **found_by**: sweep34-batch04
- **seen**: 1

corpus_db.rebuild() carries a cap parameter evidence_limit that no caller ever sets and no CLI flag exposes - grep -rn evidence_limit src/ finds only the def and its two use lines. main() calls rebuild(include_evidence=not a.no_evidence). The slice it guards is applied to an UNORDERED concatenation of two globs, so if it were ever set the sample would be arbitrary rather than ranked. Dead parameter plus a latent cap.

```
{
  "batch": 4,
  "proof": "def rebuild(include_evidence=True, evidence_limit=None):  ...  if evidence_limit:\n    files = files[:evidence_limit]"
}
```

## d7a7bbb70bf1  [MINOR]  SWEEP34_FINDING

- **where**: src/health.py:288
- **found_by**: sweep34-batch12
- **seen**: 1

health.py:288 -- the quarantine exemption spells the cache-directory key a third way (`h.replace('.','_').replace('-','_')`) instead of calling cachekey.host_dir (cachekey.py:56-58, `_SANITISE.sub('_', host)[:40]`), in the very comment that warns a wrong spelling makes the exemption a no-op that still looks implemented. The two diverge for punctuation outside ./- and for hosts over 40 chars: measured, 5 of 196 live hosts differ, and `doc:arcanum-worlds-odyssey-of-the-dragonlords` already has a directory on disk in the cachekey spelling (data/feats/doc_arcanum_worlds_odyssey_of_the_dragon, exac

```
{
  "batch": 12,
  "proof": "quarantined = {h.replace('.', '_').replace('-', '_') for h in _BH.quarantined()}  vs cachekey.host_dir: return _SANITISE.sub('_', host or '')[:HOST_CAP]"
}
```

## 1090feb5f6f1  [MINOR]  SWEEP34_FINDING

- **where**: src/recover_folder_records.py:54
- **found_by**: sweep34-batch05
- **seen**: 1

The slug comment names a module that does not exist and the wrong sibling. It says 'Matches ingest.py's slug()' -- there is no src/ingest.py (only src/ingest_doc.py; src/deprecated/ holds only catalogue_local.py). And ingest_doc.slug is not what it matches: ingest_doc's lacks the [:60] truncation this one has. The function it matches character for character is catalogue_web.slug (catalogue_web.py:66-67), which is the right one to name, since that is the writer whose filenames these must land beside.

```
{
  "batch": 5,
  "proof": "recover_folder_records.py:54-59: '# Matches ingest.py's slug(), so recovered files land where the cloud session would have put them.' / def slug(s): s = re.sub(...); return s.strip('-')[:60]   |||   ingest_doc.py:76-77: def slug(source): return re.sub(...).strip('-')  (NO [:60])   |||   catalogue_web.py:66-67: def slug(s): return re.sub(...).strip('-')[:60]   |||   ls src/ingest*.py -> src/ingest_doc.py only"
}
```

## bd33dbbb362a  [MINOR]  SWEEP34_FINDING

- **where**: src/standards.py:812
- **found_by**: sweep34-batch04
- **seen**: 1

Two stale silence.note line tags in standards.py: line 812 emits silence.note("standards.py:370") and line 891 emits silence.note("standards.py:449"). Neither number points at its own call site. Both sit on the failure path of a data-file read (data/ROSTER_PURGES.json and data/CHARTER_REGRESSION.json), so triage reading health.py --failures is sent roughly 440 lines away from the code that failed. Every other note in the file uses a symbolic tag (standards.py:ledger, standards.py:shelfmarks, standards.py:allsweep).

```
{
  "batch": 4,
  "proof": "812:            silence.note(\"standards.py:370\")\n891:            silence.note(\"standards.py:449\")"
}
```

## ca654b1add66  [MINOR]  SWEEP34_FINDING

- **where**: src/standards.py:1553-1554
- **found_by**: sweep34-batch04
- **seen**: 1

standards.main() runs check() TWICE per invocation - once via report() at line 1510 and once via work_orders() at line 1492 - both with state=None, so each builds its own dashboard.state(). The second pass repeats every live probe: a DNS lookup plus TCP connect per address at 8s timeout (fandom_ipv4_reachable, line 1191), a powershell Get-CimInstance at 60s timeout (line 1338), a tasklist spawn, and a full data/readfeats/** walk whenever the 120s _UNANS_CACHE has expired. The two passes are also free to disagree: the printed report can show a standard as met while the exit code is 1 for that s

```
{
  "batch": 4,
  "proof": "print(report())\nreturn 1 if work_orders() else 0"
}
```

## 6cf2a6486075  [MINOR]  SWEEP34_FINDING

- **where**: src/coverage.py:192-208
- **found_by**: sweep34-batch04
- **seen**: 1

coverage.report() divides by an unguarded denominator seven times while measure() guards every one of its own divisions with max(n, 1) (lines 185-186). n = sum(r["entries"] for r in rows) at line 192, then cited/n, read/n, nopage/n, untried/n, nohost/n and (cited+read)/n at lines 202-208. An empty or entry-less rows raises ZeroDivisionError from inside the reporting function, after measure() has already done the full corpus pass.

```
{
  "batch": 4,
  "proof": "n = sum(r[\"entries\"] for r in rows)\n...\nprint(f\"  CITED       {cited:>8,}  {cited/n:>6.1%}   carries a verbatim feat\")\n--- measure(): \"coverage\": c[\"CITED\"] / max(n, 1)"
}
```

## cb07046fd241  [MINOR]  SWEEP34_FINDING

- **where**: src/pick_model.py:251-253
- **found_by**: sweep34-batch04
- **seen**: 1

pick_model.fit_note() still prints the MoE tolerance the owner ruling retired: "needs ~{need}GB vs {vram_gb}GB free -- will offload, but it is MoE so the cost is modest". The constant comment sixty lines above says the opposite -- MOE_MARKERS is "STILL DISQUALIFYING under the residency mandate below -- the tolerance this marker used to buy is what produced 40-minute single calls" (lines 81-83) and "OWNER RULING 2026-08-24: GPU-ONLY, AND STICK TO IT ... MoE spills cheaply was true relative to a dense spill and still catastrophic in absolute terms" (lines 85-88). The branch is reachable: fit_not

```
{
  "batch": 4,
  "proof": "if is_moe(model_entry.get(\"name\", \"\")):\n    return (f\"needs ~{need:.1f}GB vs {vram_gb:.1f}GB free -- will offload, but it is MoE \"\n            f\"so the cost is modest\")"
}
```

## f282ba72f742  [MINOR]  SWEEP34_FINDING

- **where**: src/binding_health.py:220-221
- **found_by**: sweep34-batch15
- **seen**: 1

binding_health._probe_present success detail formats the SAME value twice, so it always reads "candidate N of N tried" and conveys nothing. The docstring claims the bound "is reported in the detail rather than left implicit ... and the reader can see how many were asked"; the reader can only see that the last candidate tried was the last candidate tried. The second operand should be PRESENT_CANDIDATES or the candidate-list length.

```
{
  "batch": 15,
  "proof": "return True, \"%d chars from %r (candidate %d of %d tried)\" % (\n    n, t, len(tried), len(tried))"
}
```

## 0f8be4893543  [MINOR]  SWEEP34_FINDING

- **where**: src/binding_health.py:189,234
- **found_by**: sweep34-batch15
- **seen**: 1

binding_health._probe_present and _probe_absent both declare a timeout=25 parameter that is never used -- neither passes it to feats.fetch or to anything else. A parameter that reads as a control and controls nothing; a caller setting it believes it has bounded the probe.

```
{
  "batch": 15,
  "proof": "def _probe_present(host, title, timeout=25):  ... body calls _fetch_chars(host, t) with no timeout\ndef _probe_absent(host, timeout=25):  ... body calls F.fetch(host, [ABSENT_PROBE]) with no timeout"
}
```

## 9beb0391c8ab  [MINOR]  SWEEP34_FINDING

- **where**: src/feats.py:186
- **found_by**: sweep34-batch07
- **seen**: 1

feats.py:186 page_looks_real(text, title='', wiki=True) never reads `title` anywhere in its body -- the word appears only in the docstring. binding_health.py:183 passes one: `real, why = F.page_looks_real(text, title)`. A caller supplying a title has reason to believe it is used (e.g. to catch a soft-404 that returns a different article) and it is not. Either use it or drop the parameter and fix the caller.

```
{
  "batch": 7,
  "proof": "def page_looks_real(text, title=\"\", wiki=True): -- runtime inspection of the function source shows no use of `title` outside the docstring; binding_health.py:183 = 'real, why = F.page_looks_real(text, title)'"
}
```

## 4be547515bd9  [MINOR]  SWEEP34_FINDING

- **where**: src/local_agent.py:578-584
- **found_by**: sweep34-batch15
- **seen**: 1

local_agent.t_propose_patch swallows the blast-cap escalation with a bare 'except Exception: pass' and no silence.note. The refusal itself still happens, so this is not a gate hole -- but every other escalation site in this file records the swallow (line 665, silence.note('local_agent.py:revert-escalate')), and this one does not, so a broken or missing escalation.py makes the runaway signal vanish with no trace in the failure ledger. The blast cap exists precisely because the enumerated gates will be bypassed a sixth time; its alarm should not be the quiet one.

```
{
  "batch": 15,
  "proof": "_ok, _why = _blast_ok(full)\nif not _ok:\n    try:\n        import escalation as _ESC\n        _ESC.escalate(_ESC.MANAGER, 'LOCAL_AGENT_BLAST_CAP', _why, who='local_agent')\n    except Exception:\n        pass\n    return {'applied': False, 'error': _why}\n-- contrast local_agent.py:663-665 which notes the same class of failure"
}
```

## a75cd9ac1273  [MINOR]  SWEEP34_FINDING

- **where**: src/local_agent.py:761-767
- **found_by**: sweep34-batch15
- **seen**: 1

local_agent.run() dispatches model-controlled **args with no exception handling, so a malformed tool call kills the whole run with a traceback instead of handing the model an error dict. A model emitting {'apply': false} for propose_patch raises TypeError (multiple values for keyword argument 'apply'); one omitting a required 'path' raises TypeError (missing required positional argument). Only _chat is wrapped in a try. Every other bad input in this file is answered with {'error': ...} so the model can correct itself; this one ends the conversation and loses the transcript.

```
{
  "batch": 15,
  "proof": "if fn == 'propose_patch':\n    res = t_propose_patch(apply=apply, log=patches, **args)\nelif fn in impl:\n    res = impl[fn](**args)\nelse:\n    res = {'error': 'no such tool: ' + str(fn)}\n-- args comes straight from the model: args = (c.get('function') or {}).get('arguments')"
}
```

## 8d0ec897cb0b  [MINOR]  SWEEP34_FINDING

- **where**: src/local_agent.py:528-617
- **found_by**: sweep34-batch15
- **seen**: 1

local_agent's patch audit trail records nothing at all about REFUSED writes. The log entry is created and appended at line 617, after six early returns: no-such-file (528), the module/path denylist (554), the writable-surface allowlist (560), the protected-region prefixes (569), the blast cap (584) and the find-count check (588). A model that repeatedly tries to patch foreman.py or data/records/*.json produces an empty 'patches' list. The comment at 607-616 argues that a record of intentions is not an audit trail; the complementary gap is that a record of only the ACCEPTED intentions is not on

```
{
  "batch": 15,
  "proof": "entry = None\nif log is not None:\n    entry = {'path': path, 'why': why[:200], ...}\n    log.append(entry)\n-- appears at line 616-620, below every refusal return: line 554 'is on the denylist', line 560-564 'is outside the writable surface', line 569-574 'is inside the protected region', line 584 blast cap, line 588 'find string occurs %d times'"
}
```

## 687dbda9881d  [MINOR]  SWEEP34_FINDING

- **where**: src/publish.py:288-295
- **found_by**: sweep34-batch15
- **seen**: 1

publish.scan_for_secrets treats a file it cannot open as clean: 'except OSError: continue', with no hit, no count and no silence.note. For the scanner whose whole premise is that it reads what actually reaches the PUBLIC repo, 'could not read' and 'read it and found nothing' must not be the same answer. Same class as the 2MB size skip on the line above.

```
{
  "batch": 15,
  "proof": "try:\n    if os.path.getsize(p) > max_bytes:\n        continue\n    with open(p, encoding='utf-8', errors='replace') as fh:\n        text = fh.read()\nexcept OSError:\n    continue"
}
```

## f80a67b48caf  [MINOR]  SWEEP34_FINDING

- **where**: src/axis_correlation.py:19-28
- **found_by**: sweep34-batch15
- **seen**: 1

axis_correlation's module header prints what reads as an unbroken descending top five, and two ranks are missing from it. Re-derived against the live tree, the true order is 1 reach|ruin 0.8161, 2 continuity|sustain 0.7731, 3 continuity|reach 0.7562, 4 reach|sustain 0.6942, 5 continuity|suasion 0.6887, 6 reach|transgression 0.6679, 7 acumen|discernment 0.6534. The header's fifth line is acumen x discernment r = +0.653 n = 44, followed by an ellipsis that asserts the five above it are the top five. Every quoted VALUE is exact; the ORDER is not, so a reader reconstructing the ranking from the he

```
{
  "batch": 15,
  "proof": "header lists: reach x ruin +0.816 n=44 / continuity x sustain +0.773 n=42 / continuity x reach +0.756 n=44 / reach x sustain +0.694 n=43 / acumen x discernment +0.653 n=44 / ...\nlive measure() ranked by abs(r): 1 reach|ruin 0.8161 n=44, 2 continuity|sustain 0.7731 n=42, 3 continuity|reach 0.7562 n=44, 4 reach|sustain 0.6942 n=43, 5 continuity|suasion 0.6887 n=44, 6 reach|transgression 0.6679 n=45, 7 acumen|discernment 0.6534 n=44"
}
```

## 8f54fab65c69  [MINOR]  SWEEP34_FINDING

- **where**: src/axis_correlation.py:202
- **found_by**: sweep34-batch15
- **seen**: 1

axis_correlation.main() raises TypeError in exactly the state where a reader most needs it to speak: measure() sets mean_r to None when no pair clears MIN_N, and line 202 formats it with %+.4f unconditionally. The two lines below it guard correctly (if doc['mean_r'] and ...), so this is an oversight rather than a decision -- the report crashes instead of saying 'nothing measurable yet'.

```
{
  "batch": 15,
  "proof": "measure() line 128: 'mean_r': round(sum(vals) / len(vals), 4) if vals else None\nmain()  line 202: print('   %d pair(s) measured, mean r = %+.4f' % (doc['measured_pairs'], doc['mean_r']))\nmain()  line 203: if doc['mean_r'] and doc['mean_r'] > 0.1:   <- the correct guard, one line later"
}
```

## fa4e143ebd02  [MINOR]  SWEEP34_FINDING

- **where**: src/axis_correlation.py:76-78
- **found_by**: sweep34-batch15
- **seen**: 1

axis_correlation.observations() skips a missing SOURCES file with a bare 'continue', and neither measure()'s return nor data/AXIS_CORRELATION.json records how many of the seven were actually read. All seven exist today. If one is renamed the matrix silently shrinks -- fewer entities, different correlations, a different mean_r -- and the file on disk looks exactly as authoritative as before. For the covariance term the header calls the thing inside 'every published interval in the library', the provenance of the sample should travel with the number: record the sources read, the sources missing,

```
{
  "batch": 15,
  "proof": "for rel in SOURCES:\n    p = os.path.join(HERE, rel)\n    if not os.path.exists(p):\n        continue\n-- measure() returns {'pairs', 'axes', 'n_entities', 'mean_r', 'measured_pairs'} and write() adds only a 'note'; nothing names the seven SOURCES or which of them were read"
}
```

## 5082a529e937  [MINOR]  SWEEP34_FINDING

- **where**: src/ledger.py:130-134
- **found_by**: sweep34-batch15
- **seen**: 1

ledger.assay_to_standards silently ignores ruin_score at the top band. LADDER[min(i+1, len(LADDER)-1)] clamps to the band itself for M10, so hi == lo, the log range is zero and the interpolation collapses to a point. Reproduced: M10 at ruin 0.0, 5.0 and 10.0 all return standards 4.672897196261646e+90, while M9 spans 4.67e+76 to 4.67e+90 over the same argument. A parameter that moves the answer fourteen orders of magnitude at every other band is inert at one of them, and the returned dict says nothing about it. tempus.band_resolution faces the same 'M10 has no band above it' problem and handles

```
{
  "batch": 15,
  "proof": "i = LADDER.index(magnitude_band)\nlo = BAND_EDGES[magnitude_band]['ruin']\nhi = BAND_EDGES[LADDER[min(i + 1, len(LADDER) - 1)]]['ruin']\njoules = math.exp(math.log(lo) + (ruin_score / 10.0) * (math.log(hi) - math.log(lo)))\n-- reproduced: assay_to_standards('M10', 0.0)['standards'] == assay_to_standards('M10', 5.0)['standards'] == assay_to_standards('M10', 10.0)['standards'] == 4.672897196261646e+90; assay_to_standards('M9', 0.0) 4.67289719626174e+76 vs assay_to_standards('M9', 10.0) 4.672897196261646e+90"
}
```

## e9167885aef6  [MINOR]  SWEEP34_FINDING

- **where**: src/ledger.py:87-98
- **found_by**: sweep34-batch15
- **seen**: 1

ledger.to_standards and ledger.from_standards cannot distinguish an UNLISTED currency from the deliberately non-convertible one. Both return bare None: to_standards(100, 'quatloos') and to_standards(100, 'poneglyph-grade favour') are identical answers, though the second is a considered doctrinal statement ('A market cannot price what one party has criminalised knowing') and the first is a typo. A caller writing an Aperture Doctrine Position Paragraph would print 'not convertible' for a misspelling. The 'unlisted' reason string is built on the same line and thrown away by the [0] subscript. ent

```
{
  "batch": 15,
  "proof": "def to_standards(amount, currency):\n    rate = CURRENCIES.get(currency, (None, 'unlisted'))[0]\n    if rate is None:\n        return None\n-- reproduced: to_standards(100, 'quatloos') -> None; to_standards(100, 'poneglyph-grade favour') -> None"
}
```

## ed7df12bf429  [MINOR]  SWEEP34_FINDING

- **where**: src/style_audit.py:34
- **found_by**: sweep34-batch16
- **seen**: 1

style_audit.BANNED is dead. src/style_audit.py:34 assigns BANNED = TELLS.ALL_PATTERNS and nothing reads it: audit() scans through TELLS.scan(r) at :119, and grep over src/*.py finds no other reader in the tree. The comment above it (:28-30) explains why the banned set is imported rather than restated, which remains true of _WATCHED and of TELLS.scan -- the name itself is left over.

```
{
  "batch": 16,
  "proof": "34 BANNED = TELLS.ALL_PATTERNS -- only other BANNED hit in src/*.py is this line; audit() at 119 calls TELLS.scan(r)"
}
```

## 96ebf36510b8  [MINOR]  SWEEP34_FINDING

- **where**: src/context_budget.py:251
- **found_by**: sweep34-batch11
- **seen**: 1

context_budget.py has FOUR bare 'except Exception:' handlers that discard the reason (251, 257 in feats_block_budget; 275, 280 in report()), and never imports silence, so none of them records anything. An unreadable prompt file sets the text to '', making scaffold_chars zero, making content_budget_chars LARGER - the truncating direction the header says this module exists to refuse. report() then publishes system_full_chars: 0 as an ordinary reading. MINOR only because generate.py:133 assert_fits still refuses loudly at send time, so the loss is the instrument, not the evidence.

```
{
  "batch": 11,
  "proof": "247-252: if system_text is None: / try: / with open(os.path.join(PROMPTS, 'system_style.txt'), encoding='utf-8') as f: / system_text = f.read() / except Exception: / system_text = ''  ||  same shape at 253-258, 272-276, 277-281  ||  line 60 is the only import in the file: 'import os' - silence appears nowhere  ||  header 41-43: 'characters and deliberately PESSIMISTIC: being wrong in that direction costs smaller blocks and more calls, and being wrong in the other costs silently truncated evidence, which is the thing the whole project exists to refuse.'"
}
```

## faee3befb768  [MINOR]  SWEEP34_FINDING

- **where**: src/tells.py:81
- **found_by**: sweep34-batch08
- **seen**: 1

tells.py's STRUCTURAL entry keyed "it's not X, it's Y" (tells.py:81) cannot match the contracted form it is named for, and neither can its neighbour at 82. Measured with tells.scan: "It isn't a fortress, it is a prison." -> hit; "It is not a fortress, it is a prison." -> hit; "It's not a fortress, it's a prison." -> {}; "It's not that it failed, it's that nobody looked." -> {}. Both halves escape: "'s not" is neither "is not" nor "isn't", and the completion side accepts only it is / which is, never it's. The undetected form is the one this module's own docstring names at line 18 as the shape t

```
{
  "batch": 8,
  "proof": "tells.py:18 'It's not that X, it's Y' | 81 pattern requires (?:is|was|are|were)n['\u2019]?t ... (?:it|they|which) (?:is|was|are|were) | 82 requires literal 'is not' + 'it is'/'which is' | measured: scan(\"It's not a fortress, it's a prison.\") == {}"
}
```

## 5a9a75916f94  [MINOR]  SWEEP34_FINDING

- **where**: src/coverage.py:82
- **found_by**: sweep34-batch04
- **seen**: 1

coverage._so_save() writes state/coverage_cache.json through a FIXED tmp name (_SO_CACHE_P + ".tmp"), the hand-rolled shape silence.write_json exists to replace: "THE TMP NAME CARRIES PID AND THREAD, which the older hand-rolled path + .tmp sites did not. Two writers of the same path otherwise collide on the temp file itself, and the loser can replace the winner target with a partial file" (silence.py:358-361). coverage.measure() is reached by the dashboard, standards, allsweep and the publisher. silence is imported at line 37.

```
{
  "batch": 4,
  "proof": "tmp = _SO_CACHE_P + \".tmp\"\nwith open(tmp, \"w\", encoding=\"utf-8\") as f:\n    json.dump(_SO[\"d\"], f)"
}
```

## 7ed8fb99bb4c  [MINOR]  SWEEP34_FINDING

- **where**: src/pick_model.py:126-129
- **found_by**: sweep34-batch04
- **seen**: 1

pick_model.save_config() writes config.yaml through a FIXED temp name (p + ".tmp") -- the hand-rolled shape silence.write_json exists to replace (silence.py:358-361), in a function whose own docstring one line above says "config.yaml is re-read by nine running modules". The replace_retry VERDICT is correctly checked here, so only the temp name is at fault. silence is already imported at module level (line 31), so the local "import silence as _sil" at line 126 is also redundant.

```
{
  "batch": 4,
  "proof": "import silence as _sil\nwith open(p + \".tmp\", \"w\", encoding=\"utf-8\") as f:\n    f.write(new_raw)\nif not _sil.replace_retry(p + \".tmp\", p):"
}
```

## c3b5aba07f4a  [MINOR]  SWEEP34_FINDING

- **where**: src/coverage.py:47-55
- **found_by**: sweep34-batch04
- **seen**: 1

coverage._p() is dead code: defined at coverage.py:47 with a full docstring, zero callers anywhere in src/ (grep -n "_p(" src/coverage.py returns only the def line; the only other mention in the tree is liveness.py:10 citing it AS the example of dead code). Its own docstring says it "used to be the whole answer" and that state_of() now verifies via cachekey.owns() instead -- which lines 105-106 do via cachekey.candidate_paths. It duplicates cachekey.natural_path and is free to drift from it. See the companion order on liveness.py: the dead-code detector cannot see this function.

```
{
  "batch": 4,
  "proof": "def _p(base, host, name):  ...  return cachekey.natural_path(base, host, name)   [docstring: \"This function used to be the whole answer, and it is lossy ... state_of() now verifies via cachekey.owns() before believing a file.\"]"
}
```

## cfb92f76ffb1  [MINOR]  SWEEP34_FINDING

- **where**: src/corpus_db.py:390-393
- **found_by**: sweep34-batch04
- **seen**: 1

corpus_db.datasette_metadata() writes state/datasette.json with a bare open(path,"w") + json.dump - a truncate-then-fill on a file a running Datasette server reads. silence is imported at line 53, silence.write_json is the named remedy (silence.py:346-364), and the same module already uses silence.replace_retry at line 215.

```
{
  "batch": 4,
  "proof": "os.makedirs(os.path.dirname(path), exist_ok=True)\nwith open(path, \"w\", encoding=\"utf-8\") as f:\n    json.dump(doc, f, indent=2)\nreturn path"
}
```

## d7ed21164177  [MINOR]  SWEEP35_FINDING

- **where**: coverage.py:234-237
- **found_by**: sweep35-batch05
- **seen**: 1

coverage.report()'s BEST COVERED section silently caps a ranked list, unlike its own WORST COVERED section eleven lines above it. Lines 217-229 (hostless, worst) explicitly disclose truncation ("showing {limit} of {len(worst)}; N more not shown, --show to raise") and expose --show to lift the cap. Lines 234-237 have no such disclosure: print("BEST COVERED") then for r in sorted(have, key=lambda x: -x[coverage])[:10] -- a bare [:10] with no count header, no "N more not shown", and no CLI flag. A reader who trusts the WORST section pattern has no way to tell BEST COVERED is truncated at all.

```
{
  "proof": "coverage.py:234: print(\"\nBEST COVERED\")  /  235: for r in sorted(have, key=lambda x: -x[\"coverage\"])[:10]:  -- contrast 224-229 which computes limit and prints \"showing N of M; K more not shown, --show to raise\""
}
```

## 91bb70c85e31  [INFO]  CODEWATCH_RESTART

- **where**: publish
- **found_by**: codewatch
- **seen**: 9

publish exited to pick up changed source (src/ changed 412b9ab4691cde90 -> eb7a3d0c2fefaf0c and held for 615s)

```
{
  "job": "publish",
  "restarts_this_hour": 1
}
```

## ee382241ff8c  [INFO]  CODEWATCH_RESTART

- **where**: overwatch
- **found_by**: codewatch
- **seen**: 5

overwatch exited to pick up changed source (src/ changed 412b9ab4691cde90 -> eb7a3d0c2fefaf0c and held for 6664s)

```
{
  "job": "overwatch",
  "restarts_this_hour": 1
}
```

## e45618de083f  [INFO]  CODEWATCH_RESTART

- **where**: foreman
- **found_by**: codewatch
- **seen**: 5

foreman exited to pick up changed source (src/ changed 412b9ab4691cde90 -> eb7a3d0c2fefaf0c and held for 3941s)

```
{
  "job": "foreman",
  "restarts_this_hour": 1
}
```

