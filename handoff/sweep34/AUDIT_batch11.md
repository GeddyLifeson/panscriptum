# SWEEP 34 — BATCH 11 AUDIT

Modules read end to end: `dashboard.py` (986), `build_terminal.py` (579), `rosetta.py` (425),
`tiers.py` (360), `context_budget.py` (288), `hosts.py` (253), `retry_synthesis.py` (208),
`roll.py` (116). 3,215 lines.

Every finding below was checked against the source and, where the claim is about data or
runtime behaviour, against the files on disk or a live run. Anything I could not prove is in the
QUESTIONS section of its module and was NOT filed as an order.

No file under `src/` was modified.

---

## dashboard.py

### FINDING D1 (MAJOR, OWNER) — the instrument that displays the halt refuses to start while a halt stands

`main()` calls the plant-wide interlock before it does anything:

    968:    _ESC.assert_clear(os.path.basename(__file__))

and `escalation.assert_clear` raises `SystemHalted` whenever a halt is recorded. But the whole
top half of this file exists to make a standing halt visible:

    784:  // THE HALT IS THE HEADLINE. If the library has stopped itself, nothing else on this page
    785:  // matters until a person rules on it, so it is rendered first, loud, and with the reason --
    786:  // a halt whose cause you have to go and find is a halt that stays up longer than it should.

Proven live, with the current `DRILL_BREACH` halt standing:

    $ python src/dashboard.py --once
    escalation.SystemHalted: THE LIBRARY IS HALTED and dashboard.py may not proceed.

So the panel is only ever visible while there is nothing for it to report. The daemon on 8777
right now survives only because it was started before the halt; the moment it is restarted, the
halt becomes invisible in the one place designed to shout about it. This is a judgment call
(exempt the read-only instrument, or accept that the halt is read from `escalation.py --status`
instead) — hence OWNER, not a repair.

### FINDING D2 (MAJOR, LOCAL) — a fixed `.tmp` name and a read-modify-write, inside a threaded server

`movement()` writes the shared history file by hand:

    377:        hist = [h for h in hist if h.get("at", 0) > cutoff][-2000:]
    378:        tmp = HISTORY + ".tmp"
    379:        with open(tmp, "w", encoding="utf-8") as f:
    380:            json.dump(hist, f)
    381:        silence.replace_retry(tmp, HISTORY)

The server is threaded, one thread per request, and every `/api/state` poll runs `movement()`:

    946: class Server(socketserver.ThreadingTCPServer):
    947:     allow_reuse_address = True
    948:     daemon_threads = True

Two browser tabs (or any second client) therefore have two threads reading `hist`, appending
their own row, and writing the SAME temp path. `silence.write_json` exists for exactly this and
says so:

    358:    THE TMP NAME CARRIES PID AND THREAD, which the older hand-rolled `path + ".tmp"` sites did
    359:    not. Two writers of the same path otherwise collide on the temp file itself, and the loser
    360:    can replace the winner's target with a partial file

`dashboard.py` imports `silence` (line 47) and already uses `silence.replace_retry` on the very
next line — it simply never adopted the writer. The lost-update half (both threads read, both
append, last one wins) is separate from the tmp collision and is not fixed by the writer alone.

### FINDING D3 (MINOR, LOCAL) — `RE_READ` scrapes `read.py`'s console progress line

The `RE_ROLL` joint is already filed. `RE_READ` is the same defect at a different line, and it
is stricter — nine named groups that must appear contiguously in one line:

    58: RE_READ = re.compile(
    59:     r"(?P<done>[\d,]+)/(?P<total>[\d,]+)\s+(?P<rate>[\d.]+)\s+chunks/s\s+"
    60:     r"feats\s+(?P<feats>[\d,]+)\s+dropped\s+(?P<dropped>[\d,]+)\s+"
    61:     r"chunks\s+(?P<chunks>[\d,]+)/(?P<budget>[\d,]+).*?"
    62:     r"(?P<gpu>\d+)\s+to\s+GPU,\s+(?P<unans>\d+)\s+UNANSWERED.*?eta\s+(?P<eta>[\d.]+)h")

The comment above it claims the failure mode is safe —

    56: # The reader's progress line. Built from the same format string read.py prints, so if that line
    57: # changes this stops matching rather than silently reporting stale numbers.

— but `_tail_match` returns `None` on no match and `_read_row` then appends nothing, so the
corpus-read row simply vanishes from the panel and from `movement()`'s `chunks` metric. A metric
that disappears is not distinguishable on the page from a job that is not running: `panelJobs`
renders "No job is writing a progress line right now." That is the same class as the RE_ROLL
finding and `read.py`'s author has no way to see the coupling.

### FINDING D4 (MINOR, LOCAL) — a rank-then-truncate on the swallowed-failure table, five lines after the identical cap was ruled a truncation

    308:            out["findings"] = [{"module": f.get("module"), "symbol": f.get("symbol"),
    ...
    311:                           for f in openf]     # ALL open findings -- a monitoring cap ruled a truncation, 2026-08-24
    ...
    316:        out["swallowed"] = sorted(f.items(), key=lambda kv: -kv[1])[:6]
    317:        out["swallowed_total"] = sum(f.values())

`state/failures.json` currently holds 25 distinct tags; the panel can show six. The total is
published so the magnitude is not hidden, which is why this is MINOR rather than MAJOR — but the
ruling recorded on line 311 was about this same panel, and this line was not brought in line.

### QUESTIONS — dashboard.py

- `panelSafety` truncates two safety lists client-side: `br.slice(0,6)` (line 844, breached
  drill nets) and `Object.keys(qn).slice(0,4)` (line 865, quarantined hosts). Both print the
  count alongside, so the magnitude survives; only the identities are cut. Deliberate?
- `throughput()` opens a sqlite connection per poll (line 157) and never closes it explicitly.
  Refcounting closes it at function exit in CPython, so this is style, not a leak. Leaving it.
- `silence.note("dashboard.py:73")` at line 74 is a numeric line tag in a file that argues
  numeric tags always rot (lines 436-440). It currently points at the `except` it annotates, so
  it is not stale today. Convention drift, not a defect.

---

## build_terminal.py

### FINDING B1 (MINOR, LOCAL) — a dead constant makes one attribute unreachable

    291:      const rim=false, nm=(p.node.name||k).slice(0,22);
    ...
    298:       + `letter-spacing="${rim?4:0}">${esc(nm)}</text>`;

`rim` is assigned `false` on the line it is declared and never reassigned, so the `4` branch
cannot execute and the attribute is always `letter-spacing="0"`. A leftover from an earlier
rim-label layout.

### QUESTIONS — build_terminal.py

- `main()` writes `output/registry_terminal.html` with a plain `open(..., "w")` (line 572), i.e.
  truncate-then-fill on a file a browser may be holding. It is a build artifact with one writer
  and it is not JSON, so `silence.write_json` does not apply. Worth an atomic HTML lander, or is
  a torn build artifact acceptable here?
- Display-name truncations at lines 241 (`.slice(0,24)`), 291 and 348/353 (`.slice(0,22)`), 323
  (18 chars + ellipsis). These cut a rendered LABEL, not a list — the full name is in the
  `<title>` tooltip and the side panel in each case. Reading these as out of Hard Rule 0's scope;
  flagging in case the owner reads them differently.
- The module has no `escalation.assert_clear`. I checked: only the eleven job entry points carry
  it (`allsweep`, `dashboard`, `escalation`, `feats`, `foreman`, `overnight`, `overwatch`,
  `pipeline`, `publish`, `read`, `verify_math`), so this looks like the intended boundary rather
  than an omission.

---

## rosetta.py

### FINDING R1 (MAJOR, LOCAL) — `srlimit: "5"` truncates a ranked page search, with no way for a person to widen it

    193:    for q in SCALE_QUERIES:
    194:        d = F.api(host, {"action": "query", "list": "search", "srlimit": "5", "srsearch": q})

A MediaWiki `list=search` result is ranked by relevance; `srlimit=5` is an internal caller
passing a fixed N — there is no CLI flag and no argument that reaches it. This is the acquisition
step for the library's only large-N external ground truth, and the module's own header records
what a silent miss here costs:

    76: # Stems, with NO trailing word boundary. The first version wrote `\bbount\b`, which cannot match
    77: # inside "Bounty" -- the `y` is a word character, so there is no boundary there. One Piece's
    78: # `Bounty/List`, 195,557 characters and 186 canonical figures, was silently discarded by that
    79: # single `\b`, and the whole wiki came back with one unrelated page.

The same outcome is reachable today by relevance rank rather than by regex. Note the default
`srlimit` is 10, so this is a deliberate tightening below the API's own default.

### FINDING R2 (MAJOR, RUN) — the Spearman agreement check, the module's stated purpose, has no automated caller

The header states the value proposition:

    12: 186 bounties, Dragon Ball publishes 114 power levels, and those orderings are canon. If our
    13: Assay ranks two One Piece characters in the order their bounties forbid, that is a defect we can
    14: detect without asking anyone's opinion.

`check()` is called from exactly one place, `main()` under `--check` (line 414), and its verdict
is printed and dropped — `main()` returns 0 whatever the correlations say. Nothing schedules it:

- `allsweep.py:74-81` lists `"rosetta"` in `NEVER_RUN`;
- `allsweep.py:83-93` `VERIFIERS` does not include `rosetta.py --check`;
- grep over `src/` finds only `sweep.py:101` reading `data/ROSETTA.json`, and that reads the
  MINED values for its own index — never the correlation.

So the mine is consumed and the accuracy test it exists to enable is not. This is `roll.py`'s own
thesis, in a different file: a check nobody runs is a check that looks taken and is not. RUN
because the fix is a decision about where it belongs (`VERIFIERS`, `standards.py`, or a
work-order emitter) plus a second file.

### QUESTIONS — rosetta.py

- `main()` prints ranked leaderboards under `--probe` (`[:6]`, line 343) and `--refine` (`[:12]`,
  line 391). Both are human-invoked summaries whose authoritative output is the full JSON on
  disk. Reading these as out of scope; confirm.
- `numeric_rows` line 169-171 drops any value more than 1,000x the median once there are 8+ rows.
  That is a documented outlier filter, not a cap, and it discards data. Deliberate — noting it so
  the next sweep does not re-file it.
- `import silence` at line 45 lacks the `# noqa: E402` its two neighbours carry. Cosmetic.

---

## tiers.py

### FINDING T1 (MAJOR, OWNER) — the module prints "hyperverse: DECLINED for all 209 shelves" in the same run that writes four distinct hyperverse values

This is my answer to the open question attached to the `address_space.py` order: **the claim is
wrong, not the cut.** The hyperverse was re-implemented and the top docstring was never updated.

The header still says the tier is declined:

    38: and NO cut for the hyperverse, for reasons set out below -- that tier is declined rather than
    39: charted, and declining it is itself the result.
    44:     168 multiverses  ->  8 metaverses  ->  6 xenoverses  ->  H declined
    87: So H stays '?', and the question mark now means something sharper than it did.

But 130 lines further down the SAME file says the opposite, in capitals:

    137: # The hyperverse therefore comes from grounding.py and from nowhere else.
    151:     """THE HYPERVERSE. A grounding is answered per XENOVERSE, not per shelf.

and `chart()` assigns it per source:

    265:            out[s]["hyperverse"] = xg[xi]["index"]
    266:            out[s]["hyperverse_type"] = xg[xi]["grounding"]

`main()` then prints the declination and writes the assignments eleven lines apart:

    309:    print(f"\nhyperverse: DECLINED for all {len(srcs)} shelves — uncharted by cause, not omission")
    ...
    348:            print(f"   {s[:26]:<28}H{c['hyperverse']} › X{c['xenoverse']} › "
    ...
    354:    silence.write_json(out, charted, indent=2, ensure_ascii=False)

Line 348 prints a hyperverse NUMBER for each sample stack in the same output that line 309 says
there is none. Measured against `data/TIERS.json` as it stands (209 sources):

    hyperverse index : {None: 53, 4: 146, 5: 6, 2: 2, 3: 2}
    hyperverse_type  : {None: 53, 'immanent': 146, 'ungrounded': 6,
                        'eternal_cycle': 2, 'demiurgic': 2}

Four distinct non-null values. The dendrogram cut is fine — there deliberately is no hyperverse
cut in `CUTS` (lines 112-118) and there is not meant to be one. What is stale is the top
docstring and the line 309 print, both of which describe the pantheon-era design that the
grounding pass replaced. OWNER because it is a curatorial call about what the tier now means in
print, not a mechanical repair.

### FINDING T2 (MINOR, LOCAL) — the residue list is truncated to six

    310:    print(f"unaddressed (share no entity with anything at all): {len(unaddressed)}")
    311:    for s in unaddressed[:6]:
    312:        print(f"   {s}")

The docstring calls these out by name as the finding's honest remainder —

    92: The 13 unaddressed shelves are the honest residue: they share nothing with anything, which is what
    93: a fragment of another hyperverse would look like from here

— and the only place they are ever enumerated shows six of them. This is a source list, i.e. a
roster.

### FINDING T3 (MINOR, LOCAL) — `import silence` runs before the `sys.path` repair that is supposed to enable it

     96: import collections
     97: import json
     98: import os
     99: import sys
    100: import silence
    101:
    102: HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    103: sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

The insert on line 103 is dead for the import on line 100. Proven — loading the file with `src`
absent from `sys.path` fails:

    FAILED: ModuleNotFoundError No module named 'silence'

It works today only because `python src/tiers.py` puts `src` on the path implicitly and every
in-tree importer inserts it first. `rosetta.py` (insert 42, imports 43+) and `hosts.py` (insert
33, import 34) both have the order right.

### QUESTIONS — tiers.py

- `main()` line 328: `peers = [t for t in srcs if charted[t][lo] == c[lo] and c[lo] is not None]`
  — the second clause does not depend on `t` and is loop-invariant. I traced it and it is
  correct (it makes `peers` empty when `c[lo]` is None, which is the intent), but it reads like
  the guard was meant to be on `charted[t][lo]`. Confirm the intent before anyone "tidies" it.
- Lines 119-120 use bare `assert` for the cut-ordering invariants, which `python -O` strips.
  Cheap to convert to a raise; leaving the call to the owner since nothing here runs under `-O`.
- `chart()`'s docstring says "Returns per-source dicts" but it returns `(out, tiers, multi)`.

---

## context_budget.py

### FINDING C1 (MINOR, LOCAL) — four bare handlers default the budget in the truncating direction, silently

    247:    if system_text is None:
    248:        try:
    249:            with open(os.path.join(PROMPTS, "system_style.txt"), encoding="utf-8") as f:
    250:                system_text = f.read()
    251:        except Exception:
    252:            system_text = ""

and the same shape at 253-258 (`feats_prompt.txt`), 272-276 and 277-281 (both files again, in
`report()`). This module never imports `silence`, so none of the four records anything.

An unreadable prompt file makes `scaffold_chars` zero, which makes `content_budget_chars` LARGER,
which widens the feats block — the exact direction the header forbids:

    41: characters and deliberately PESSIMISTIC: being wrong in that direction costs smaller blocks and
    42: more calls, and being wrong in the other costs silently truncated evidence, which is the thing
    43: the whole project exists to refuse.

`report()` is worse in kind than in effect: it publishes `system_full_chars: 0` and
`chapter_scaffold_chars: 0` as ordinary readings, and `report()` is what health/preflight and the
ledgers display. MINOR rather than MAJOR because `generate.py:133` calls `assert_fits` on the
real strings at send time, so an over-wide block still refuses loudly downstream — the loss here
is the instrument, not the evidence.

### QUESTIONS — context_budget.py

- `verify_math` §19 pins `system_for()` against a synthetic fixture
  (`"voice\nTHE ENTRY TEMPLATE\nbody"`, lines 2237-2242) but nothing checks that the REAL
  `prompts/system_style.txt` still contains the `THE ENTRY TEMPLATE` heading. If it were renamed,
  `split_system_prompt` degrades to a no-op (line 135) and feats jobs quietly get the whole 18k
  document back. I traced the consequence and it fails LOUD — `assert_fits` would then refuse —
  so I am not filing it. A `template_only_chars > 0` assertion in `verify_math` would close it.
- `content_budget_chars` line 169 builds `"x" * int(scaffold_chars)` — a 20,000-character
  throwaway string — only to take its length inside `estimate_prose_tokens`. Correct, wasteful,
  and it hides that the function wants a COUNT not a text. Style.

---

## hosts.py

### FINDING H1 (MAJOR, LOCAL) — `discover()` silently disables one of `candidates()`'s three generators

    157:        try:
    158:            cands = HC.candidates(source, cur, by=by)

`hostcheck.candidates` gates its NEIGHBOURS generator on BOTH arguments:

    335:    if by and hosts:
    336:        mine = set(by.get(source) or ())

With `hosts` defaulting to `None`, the whole block is skipped. `hostcheck.py`'s own two call
sites pass it — `hostcheck.py:536` and `hostcheck.py:878` both read
`candidates(src, ..., by=by, hosts=hosts)`. `src/hosts.py:158` is the only caller in the tree
that omits it.

The generator this silences is the one the docstring singles out as unreachable by any other
means:

    285:    NEIGHBOURS. Any source whose catalogued roster substantially overlaps this one's is about the
    286:    same world, so its host is a candidate. This is what found
    287:    `Explorer's Guide to Wildemount -> criticalrole.fandom.com` at 90%: Wildemount IS Critical
    288:    Role's setting, and no string manipulation on the title would ever have reached it.

Measured over all 203 sources on the roll, diffing `candidates(..., hosts=prim)` against
`candidates(...)`:

    sources losing neighbour candidates when hosts= is omitted: 5   total hosts lost: 5
      Alien                                  -> ['predator.fandom.com']
      Explorer's Guide to Wildemount         -> ['criticalrole.fandom.com']
      Player's Handbook                      -> ['criticalrole.fandom.com']
      Predator                               -> ['alien.fandom.com']
      Who Framed Roger Rabbit (...)          -> ['kingdomhearts.fandom.com']

Including the docstring's own worked example, and including the Alien/Predator pair that
`tiers.py:51` names as the strongest deliberate join in the entire corpus (6489). Those two are
each other's best secondary host and `--discover` cannot see it.

### QUESTIONS — hosts.py

- `discover(per_source=24)` slices the candidate list at line 166-167 with a comment asserting
  "the bound sits AFTER the evidence, never through it". The code does not enforce that — it is a
  blind positional slice on `grounded + spec`. I measured it: 80 of 203 sources produce more than
  24 candidates, but `en.wikipedia.org` (the LAST grounded entry appended) never falls at index
  >= 24 on today's roll, so the cut currently lands entirely in the speculative tail. **Not
  filed** — the comment happens to be true today. It is one long source name away from being the
  `grounded[:1] + spec[:14]` bug that `hostcheck.py:296-304` documents. `per_source` also has no
  CLI flag, so nobody can widen it without editing the file.
- `_load()` records one tag, `"hosts.py:load"`, for two different files and every possible
  reason (line 49). A missing `SOURCE_HOSTS.json` (normal on a fresh tree) and a corrupt
  `WIKI_HOSTS.json` (a real fault) are indistinguishable in `failures.json`.
- `add()` re-reads and rewrites the entire `SOURCE_HOSTS.json` per host adopted. Called from the
  main thread only (`discover` collects results through `ex.map` and calls `add` outside the
  pool), so there is no race — but it is O(n^2) file I/O over a run.

---

## retry_synthesis.py

### FINDING S1 (MINOR, LOCAL) — a denied merge is tallied as "already had synthesis"

    162:        if not PL.write_record(path, rec):
    163:            print("  MERGE DENIED  %s -- record left as it was on disk; rerun the merge"
    164:                  % src, flush=True)
    165:            skipped += 1
    166:            continue
    167:        merged += 1
    168:    print(f"merged {merged}, skipped {skipped} (already had synthesis)")

`skipped` is incremented both at line 145 (the record genuinely already had a synthesis) and at
line 165 (the write was REFUSED), and the closing line labels the whole count with only the
benign reason. The per-source DENIED line does print, so nothing is lost to a reader watching the
run — but the summary a person copies into a handoff says every skip was benign. Two counters.

### QUESTIONS — retry_synthesis.py

- `load_side()` (line 37-41) has no handler: a corrupt `SYNTHESIS_RETRY.json` raises out of
  `save_side()` mid-run. That is fail-loud and arguably correct for a file this script owns —
  but `save_side` is called after every rescued source, so the corruption would abort the run
  with the earlier rescues already landed. Deliberate?
- The `save_side` re-read-and-merge landed today closes the content race down to the window
  between the read and the replace, and the docstring is honest that a lock was declined. Read
  it, agree with it, nothing to file.

---

## roll.py

Read with extra care — run #33 never opened this file.

### FINDING L1 (MAJOR, LOCAL) — the write verdict is discarded, so a denied exclusion reports success

     97:    if changed:
     98:        silence.write_json(ROLL, rows, indent=2)
     99:    return changed

`silence.write_json` returns False on a denied replace and never raises — that is its documented
contract:

    363:    Returns True if the file landed. Never raises on a denied replace: `replace_retry` records
    364:    it and the caller's write lands next round, which is the established behaviour here.

`exclude()` throws that away and returns `changed`, i.e. True, meaning a Windows lock on
`SWEEP_ROLL.json` produces "the source was excluded" while the source is still in scope on disk.
`SWEEP_ROLL.json` has five writers (`catalogue_web`, `catalogue_aurora`, `catalogue_codex`,
`resync_roll`, `recover_folder_records`) and is the file `silence.py:353` names as the
four-writer hazard, so a denial here is not hypothetical. Two siblings already handle it
correctly:

    recover_folder_records.py:188:  if not silence.write_json(ROLL, roll, indent=2, ensure_ascii=False):
    recover_folder_records.py:189:      print("  ROLL WRITE DENIED; the records landed but SWEEP_ROLL.json still reads "

and `hosts.py:92-96` fixed this exact shape with a comment naming the consequence: "both used to
be `False`, which is how a lost host looks like a known one." Here it is worse — both are True.

The stakes are set by the module's own header: this is the one implementation of an owner's
exclusion decision, and `resync_roll` will promote an out-of-scope source back to `catalogued` on
its next run if the status never landed.

### FINDING L2 (MINOR, LOCAL) — a corrected reason is applied in memory and never written; an unknown source name is indistinguishable from a no-op

     91:    for r in rows:
     92:        if isinstance(r, dict) and r.get("name") == name:
     93:            if r.get("status") != OUT_OF_SCOPE:
     94:                r["status"] = OUT_OF_SCOPE
     95:                changed = True
     96:            r["note"] = note
     97:    if changed:
     98:        silence.write_json(ROLL, rows, indent=2)
     99:    return changed

Two paths return False without writing:

1. The source is ALREADY out of scope and the caller supplies a corrected or expanded reason.
   `r["note"] = note` runs on line 96, `changed` stays False, the file is not written, the
   reason update is discarded. The module exists to protect exactly this field —
   "an exclusion with no reason attached is how a real source gets quietly dropped and nobody can
   reconstruct why" (lines 58-61) — and it cannot be corrected through its own writer.
2. `name` matches no row at all (a typo, a renamed source). The loop body never runs, False is
   returned, and the caller cannot tell "already excluded" from "that source does not exist and
   nothing happened."

### FINDING L3 (MINOR, LOCAL) — the only roll writer that does not pass `ensure_ascii=False`

     98:        silence.write_json(ROLL, rows, indent=2)

Every other writer of this file passes it:

    resync_roll.py:85              silence.write_json(ROLL, roll, indent=2, ensure_ascii=False)
    recover_folder_records.py:188  ... indent=2, ensure_ascii=False)
    catalogue_aurora.py:172        ... indent=2, ensure_ascii=False)
    catalogue_codex.py:223         ... indent=2, ensure_ascii=False)

`data/SWEEP_ROLL.json` currently holds 50 literal non-ASCII characters (en and em dashes) and
zero `\u` escapes. One call to `exclude()` rewrites all 50 as escapes, producing a whole-file
diff that has nothing to do with the exclusion, which the next writer then reverts.

### QUESTIONS — roll.py

- `exclude()` has no caller anywhere in `src/` and no CLI flag — `main()` only lists existing
  exclusions. The only way to invoke the sanctioned writer is
  `python -c "import roll; roll.exclude(...)"`, which means the four exclusions on the roll today
  were almost certainly made by hand-editing the JSON, bypassing the required-note guard on line
  87-88 entirely. Is a `--exclude NAME --note "..."` flag wanted, or is `exclude()` meant to be
  removed in favour of hand-editing plus `resync_roll`'s preservation rule?
- `main()` line 110 prints `why[:150]`. The reason is the thing `out_of_scope()`'s docstring says
  must travel with the exclusion; the one display that shows it truncates it. Line 109 also cuts
  the source name to 45 characters. Display-only, but this is the only human view of the field.
- `in_scope()` fails OPEN on an unreadable roll (lines 70-79) and argues the case well. Agreed,
  noting it so it is not re-filed.
- `load()` records `"roll.py:load"` for every failure including a legitimately absent file.

---

## COVERAGE

All eight modules read end to end and recorded via `sweep_plan.record('run34', [...], batch=11)`.
