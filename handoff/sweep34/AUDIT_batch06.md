# SWEEP 34 — BATCH 06

Modules read end to end: `src/cascade_bridge.py` (1270), `src/generate.py` (503),
`src/endpoint.py` (406), `src/pantheon.py` (308), `src/policy.py` (261),
`src/profile.py` (215), `src/halo.py` (178). 3,141 lines.

Auditor only. **Nothing under `src/` was edited.** Every finding below was re-read in the
source and, where it could be, proven by running it. Anything that could not be proven, or
that might be deliberate design, is a QUESTION and was NOT filed.

Ten findings filed. Two dead functions confirmed but deliberately NOT filed (the house
detector already reports them — see the note at the end). One cross-module finding in
`drill.py` is recorded here for routing, not filed, because `drill.py` is not this batch.

---

## `src/cascade_bridge.py`

### F1 — MAJOR — the module docstring promises schema VALIDATION the module does not do
`cascade_bridge.py:17-20`, the file's own headline contract:

```
STRUCTURED OUTPUT. The local path uses Ollama's `format` parameter, which constrains generation
to a JSON schema. Cloud endpoints do not all offer that, so the schema is carried in the prompt
and the reply is parsed and VALIDATED here. A reply that does not validate is a failure, not a
result -- which is the rule this project keeps having to relearn.
```

`schema` appears exactly five times in the file. Every one is either the parameter itself or
its insertion into the system message:

```
805:def ask(system, prompt, schema=None, pool="coding", ...):
810:    got = _ask_call(system, prompt, schema=schema, ...)
840:def _ask_call(system, prompt, schema=None, ...):
965:    if schema:
966:        sys_msg = (system + "\n\nReply with JSON ONLY, no prose and no code fence, "
967:                   "matching this schema exactly:\n" + json.dumps(schema))
```

There is no validation step anywhere. The reply path is:

```
1147:    got = _extract_json("".join(out))
1148:    if got is None:
1149:        return None
1150:    if isinstance(got, dict):
1151:        got["_via"] = answered or "cascade"
1152:    return got
```

`_extract_json` returns whatever parses. `{}` parses. `{"result": 3}` parses. Both come back
as a successful answer, and `ask()` then records `"ok": got is not None` in the metrics.

This is not theoretical, and the tree already knows it. `pipeline.py:259-291`
(`_pool_answer_usable`) exists solely to compensate, and cites this very file while doing so:

```
    THE GAP THIS CLOSES. Ollama constrains generation to the JSON schema; the cloud path cannot
    -- cascade_bridge.py:18 says so in as many words: "Cloud endpoints do not all offer that, so
    the schema is carried in the prompt." It is a REQUEST there, not a constraint. So a cloud
    model can return perfectly valid JSON of entirely the wrong shape, `_extract_json` parses it
    happily, and `ask_pool_first` used to return it on the sole test `got is not None`.
```

Only the phase call sites route through `ask_pool_first`. Every other caller of `CB.ask`
(`read.py:383`, `read.py:400`, `magnitude.py:142`, `magnitude.py:625`, `chain.py:272`,
`ingest_doc.py:133`, `estate.py:329`, `foreman.py:143`) accepts the answer on `is not None`.
`read.py` then does exactly what the docstring says must never happen:

```
730:                _chunk_put(host, ch, name, (got or {}).get("feats", []))
735:        for f in (got or {}).get("feats", []):
```

and the `got is None` branch two lines above it is the one labelled "NOBODY ANSWERED. Not
'this passage holds no feats'". A `{}` reply misses that branch, is filed as a read with no
feats, and is **cached**.

Handler RUN, not LOCAL: whether the fix is to validate in the bridge or to correct the
docstring and push the check to every caller is a transport-wide judgment, and the same
decision governs `pipeline._pool_answer_usable`'s future.

### F2 — MINOR — three stale numeric `silence.note` tags
`silence.instrument()` writes the tag as `basename:<lineno of the except handler>`
(`silence.py:493` and `:500`). Checked by AST across all seven modules; three are wrong here:

| call | tag | handler actually at |
|------|-----|---------------------|
| 137 | `cascade_bridge.py:100` | 136 |
| 151 | `cascade_bridge.py:113` | 150 |
| 987 | `cascade_bridge.py:151` | 986 |

The third is the worst of them: `cascade_bridge.py:151` points at a line that is itself another
`silence.note` call, so a maintainer tracing a swallowed exception in the stream pump lands on
the JSON brace-matcher. Everything else in the file already uses the durable symbolic form
(`cascade_bridge.py:deadline`, `:widen-proof`, `:provider-error`), and `generate.py:447-452`
argues in prose for exactly that migration.

---

## `src/generate.py`

### F3 — MAJOR — a missing or mistyped `--manifest` reports a clean, successful run
`--manifest` is `required=True` (334), but the loader treats a nonexistent path as an empty
document:

```
45:def load_json(path, default):
46:    full = os.path.join(HERE, path)
47:    if not os.path.exists(full):
48:        return default
...
356:    manifest = load_json(args.manifest, {"jobs": []})
365:        jobs = manifest.get("jobs") or []
```

Proven by running it:

```
missing manifest -> {'jobs': []}
jobs from it -> []
```

With the prose gate open, a typo in the path prints `0 total jobs, 0 pending`, then
`Done. 0 generated this run, 0 failed`, and exits 0. There is no other path in `main()` that
produces a nonzero exit, so a supervisor or keeper reading the return code sees success.
Nothing distinguishes "this manifest was fully generated already" from "this file does not
exist" — the exact substitution `silence.py`'s own preamble is written about.

`catalog` and `failures` at 367-368 use the same helper correctly: absent really does mean
empty for those two. Only the manifest is a required input.

---

## `src/endpoint.py`

### F4 — MINOR — `source_pages` docstring states a return type the function does not return
```
358:def source_pages(source):
359:    """The URLs registered for a source that has no wiki. {} when it has none."""
360:    try:
361:        with open(PAGES_FILE, encoding="utf-8") as f:
362:            return (json.load(f) or {}).get(source) or []
363:    except Exception:
364:        silence.note("endpoint.py:source_pages")
365:        return []
```
Both returns are lists. The sole caller reads it as a list
(`feats.py:975: urls = EP.source_pages(host[6:]) ...`), so the code is right and the sentence is
wrong. Cheap to fix and worth fixing: a caller who believed the docstring would write
`if pages == {}` and get a branch that never fires.

### F5 — MINOR — `MODE_HTML` is a verdict no resolver can ever return
```
301:MODE_HTML = "html"
```
Referenced nowhere — not in `endpoint.py`, not anywhere else in the tree (grepped `MODE_HTML`
across all `*.py`: one hit, the definition). `detect()` can only ever return `MODE_API`,
`MODE_RAW` or `MODE_DEAD`; it never inspects a source-pages registration at all. So
`detect(h)["mode"] == MODE_HTML` is a comparison that cannot succeed, sitting one import away
from any caller who reads the 15-line comment above it announcing "So a third mode".

The HTML capability itself is real and reachable — `feats.py:975-978` reads a `pages:` host
prefix through `source_pages` + `fetch_html`, bypassing `detect()` entirely. The constant is
the part that is fiction. OWNER rather than LOCAL because deleting a module-level public name
is a curatorial call, and the alternative (teaching `detect()` to return it) is a design change.

---

## `src/pantheon.py`

No findings. Verified rather than assumed:

* `A.WEIGHTS` holds 11 axes (8 charter physical + 3 faculty; `assay.py:112-143`) and every
  one of the six rosters here scores all 11, so the `for ax in A.WEIGHTS: rec["axes"][ax]`
  loop at 298-299 cannot `KeyError`.
* `data/Z_FIGHTERS.json` exists, so the merge at 265-271 is not quietly swallowing a missing
  file and printing the gods alone under a banner that says "AND THE WHOLE LADDER WITH IT".
* The write at 261 goes through `silence.write_json`. Correct.

---

## `src/policy.py`

### F6 — MAJOR — `--limit` defaults to 40 and truncates two ordered work-lists
```
202:    ap.add_argument("--limit", type=int, default=40)
...
217:    for p in sorted(glob.glob(os.path.join(HERE, "data", "records", "*.json")))[:a.limit]:
...
228:            for row in json.load(f)[:a.limit]:
```

Measured on disk: `data/records/*.json` = **216** files, `data/COVERAGE.json` = **210** rows.
A default `python src/policy.py --run` therefore evaluates 40 of 216 records (18.5%) and 40 of
210 coverage rows (19%), sorted alphabetically, and prints `N document(s) evaluated` and
`0 rule failure(s)` — a clean structural pass over the alphabetical head of the corpus, wearing
the shape of a pass over the corpus.

This is the `cap=250 took the alphabetical head of every missing-cast repair` shape from Hard
Rule 0, in the module whose own docstring is about rules that "degrade to a no-op without
anyone noticing". The flag is not the problem; the non-None default is. `--limit` defaulting
to `None` with the slice applied only when set would keep the human escape hatch and remove
the silent truncation.

Note the irony recorded at 209-215: run #33 fixed the `except Exception: continue` in this same
loop because "a check that was never attempted looks exactly like one that passed too" — and
the cap immediately above it means 176 records are never attempted at all, without even an
`UNREAD` line.

### F7 — MINOR — `report()` writes through a fixed `.tmp` name
```
148:        os.makedirs(os.path.dirname(REPORT), exist_ok=True)
149:        tmp = REPORT + ".tmp"
150:        with open(tmp, "w", encoding="utf-8") as f:
151:            json.dump({"at": time.time(), "evaluations": evaluations}, f, indent=1,
152:                      ensure_ascii=False)
153:        silence.replace_retry(tmp, REPORT)
```
`silence.write_json` (`silence.py:346-372`) is the one correct writer and builds
`"%s.%d.%d.tmp" % (path, os.getpid(), _th.get_ident())` precisely so two writers cannot collide
on the temp file itself. This is the m100 shape the tree retired everywhere else, and it is
named as such in two of my own batch's neighbours (`endpoint.py:83-98`,
`cascade_bridge.py:548-555`). `state/policy_report.json` is written by `main()` and read by
`drill.py`, so the collision is narrow today — but the point of `write_json` is that it makes
the collision unavailable rather than merely unlikely.

### F8 — MINOR — `coverage.cited_le_entries` asserts something its id does not
```
190:    {"id": "coverage.cited_le_entries", "path": "cited", "op": "gte", "arg": 0,
191:     "severity": "MAJOR", "why": "cited cannot be negative"},
```
The id promises `cited <= entries`. The rule checks `cited >= 0`. The `why` is honest about
what it does, which makes the id the only wrong part — but the id is what appears in the report
output (`print("  FAIL  %-26s %-28s ...", subj, r["id"], ...)`, 253), so a reader of a green
policy run comes away believing an invariant that is asserted nowhere. `OPS` (42-57) has no
operator that can compare two fields of the same document, so this rule could never have done
what its name says; expressing it would mean the stateful Python the docstring at 20-24
deliberately keeps out of the table. Renaming the rule is the honest repair.

---

## `src/profile.py`

### F9 — MAJOR — half the round-trip check cannot fail, and the other fields are never checked
```
194:    print("ROUND TRIP — the string must reconstruct the world exactly")
...
197:    for r in rows:
198:        d = decode(r["profile"])
199:        if d["address"] != r["address"] or d["profile"] != r["profile"]:
200:            bad += 1
201:    print(f"   {len(rows)-bad:,} of {len(rows):,} round-trip exactly   failures: {bad}")
```

`decode()` echoes its own argument back:

```
108:def decode(profile):
...
125:        "profile": profile,
```

So `d["profile"]` is not a reconstruction — it is the same object. Proven:

```
profile string: PS-3nqk8n-hfl-0000-42
d[profile] is the input string: True True
```

The second half of the disjunction is a comparison of an object with itself and can never
contribute a failure. What remains is a check on `address` alone. `decode()` also returns
`genre`, `register`, `features`, `band` and `attested_axes` — the five fields that carry
everything `encode()` was given besides the address — and not one of them is compared against
what went in, while the banner above claims the string "must reconstruct the world exactly".

The consequence is concrete: `encode` maps an unknown genre to `"un"` (`102: GENRE_CODE.get(genre, "un")`)
and `decode` maps an unknown two-letter code back to `"unclassified"` (`120`). A genre that
silently folded to `unclassified` on the way out and back would round-trip "exactly" under this
check, and the attestation digit — the field the module docstring at 34-39 says is "the field a
compression scheme would drop first" and that must never be dropped — is likewise unverified.

`liveness.py` reports 0 tautologies tree-wide and does not see this one, because the two sides
are textually different expressions.

### F10 — MINOR — the docstring still advertises the 74-bit address
```
20:    address   the 74-bit shelfmark in base32: where the world IS
```
`address_space.TOTAL_BITS` is **89** (verified at runtime: fields
hyperverse 3, xenoverse 3, metaverse 3, multiverse 8, universe 6, galaxy 38, star 27, planet 1).
74 is the superseded five-field width, and `address_space.py:31-36` names that exact number as
the drift it already had to correct once:

```
THIS TABLE WENT STALE ONCE AND MUST NOT AGAIN. It described the five-field, 74-bit/10-byte
address for three passes after `tiers.py` charted xenoverse, metaverse and multiverse and FIELDS
grew to eight, so the module's own advertised justification named a design the module no longer
had.
```

The same sentence went stale in this module and was not caught, because `profile.py` never
prints its own bit width and so has nothing that could drift visibly.

### F11 — MINOR — two stale numeric `silence.note` tags
| call | tag | handler actually at |
|------|-----|---------------------|
| 146 | `profile.py:131` | 145 |
| 151 | `profile.py:135` | 150 |

Same class as F2. Filed separately because it is a different file and a different fix.

---

## `src/halo.py`

No findings. `A.WEIGHTS`' 11 axes are all present on all three roster entries, so the `--full`
loop at 167-169 cannot `KeyError`; the write at 171 is `silence.write_json`; there are no
numeric `silence.note` tags; no caps on anything but console column widths; and the anchors in
the roster (`M6`, `M6`, `M4`) agree with the docstring's argument that Halo tops out at M6.

---

## QUESTIONS — not filed, because they may be deliberate

1. **`cascade_bridge.py:1163` — `for lab in ready[:12]:`** in `selftest()`. The full count is
   printed immediately above (`provider-ready: {len(ready)}`), so nothing is hidden, and this
   is a console listing rather than a work-list. Deliberate?
2. **Does the bridge distinguish "no model reachable" from "the model said nothing"?**
   Partly, and the part it gets right is the part the caller uses. `_ask_call` returns `None`
   for both, but `ask`'s metric row separates them: a call that never claimed a bucket carries
   `"tried": []` and `"model": ""`, while a claimed-and-failed call carries
   `"model": "tried:<buckets>"` (818-836). Callers only need "did the cloud answer", and they
   fall back to the GPU either way. The genuinely dangerous conflation is not this one — it is
   F1, where a provider that answers with the wrong shape is not a failure at all.
3. **`endpoint.py:346` — `return u, (text if len(text) > 400 else None)`** in `fetch_html`.
   A page whose extracted text is 400 characters or fewer is dropped with no note and no
   counter, and reaches the caller identically to a page that could not be fetched. On a
   homebrew site — the exact material this mode was written for — a short but real page is a
   plausible thing to exist. Is 400 a measured floor or a guess?
4. **`endpoint.py:401` — `silence.note("endpoint.py:register-nondict")` outside any handler.**
   There is no live exception at that point, so `sys.exc_info()` yields `None` and the ledger
   row records the exception class as the string `"None"`. The row still lands and the
   `raise` on the next line is correct; it is only the recorded class that is empty.
   `generate.py:447-452` argues that `silence.note` "cannot serve here" in exactly this
   situation. Intentional, or a leftover?
5. **`pantheon.py:301` / `halo.py:169` — `d["cited"][:58]` / `[:54]` under `--full`.** The
   cited evidence is truncated mid-sentence in the mode named "full". The complete text does
   land unabridged in `data/PANTHEON.json` and `data/HALO_ASSAYS.json`, so nothing is lost —
   this is a column width, not a cap. Flagging it only because `--full` is a promise.
6. **`generate.py:172` — `_covered` returns `True` for an empty name.** An entry with no name
   is deemed present without anything being checked. Currently unreachable: 0 of 198,705
   entries across all 216 record files lack a name. Worth a guard, or correctly left alone?
7. **`generate.py:465` — `open(raw_path, "w")` for `output/raw/*.md`.** Non-atomic, but the
   path is per-address and its existence is only advertised to readers once `catalog.json`
   lands (through `silence.write_json`) after the write completes. Probably fine; noting it
   because the sibling write two lines up was fixed for this on 2026-08-25.
8. **`generate.py:83-85`** — `feats_template`'s docstring says the templates tuple "is unpacked
   at four call sites". It is unpacked once (370); `chapter_tpl`/`front_tpl` are *passed* at
   four `build_prompt` sites (221, 233, 279, 431). The sentence is true under the second
   reading, so this is wording rather than drift.
9. **`policy.py:123` — `ok = False`** immediately before a `return` that does not read `ok`.
   A dead assignment; harmless, and possibly left as documentation of the branch's verdict.
10. **`profile.py:109`** — the `decode` regex admits `[0-9a-z]+` for the address group, which
    includes the four letters Crockford Base32 excludes (`i`, `l`, `o`, `u`). Such a string
    reaches `_unb32` and raises `ValueError` from `B32.index(ch)` rather than the module's own
    `not a world profile` message. It refuses, which is the important half; only the error is
    less legible than intended.

---

## NOT FILED — already reported by the house detector

`python src/liveness.py` (run this session: 38 findings, 0 tautology, 0 phantom, 38 dead)
already lists both dead functions in this batch, so filing them again would only duplicate a
line the page already carries:

* `cascade_bridge.py:1230 try_disabled()` — no caller anywhere in the live tree (the only other
  hit in the repo is a copy under `state/foreman_backups/`).
* `endpoint.py:248 exists_raw()` — no caller anywhere.

Both are public names, so removal is an OWNER call in any case, and it is already visible where
an owner would look.

## NOT FILED — outside this batch, recorded for routing

`drill.py:1443-1454`, `_policy_corpus_clean`, the net behind
`"the live corpus passes its structural rules"`:

```
    for p in sorted(glob.glob(os.path.join(HERE, "data", "records", "*.json")))[:40]:
        try:
            with open(p, encoding="utf-8") as f:
                ev = POL.evaluate(json.load(f), POL.RECORD_RULES, os.path.basename(p))
        except Exception:
            continue
        bad += len([r for r in ev["failed"] if r.get("severity") != "INFO"])
    return bad == 0
```

Two problems in six lines, and they compound: the same `[:40]` cap as F6 (40 of 216 records,
alphabetical), and a bare `except Exception: continue` that scores an unreadable record as
clean. The net asserts a property of "the live corpus" while examining the alphabetical first
fifth of it and treating anything it cannot parse as a pass. `drill.py` belongs to another
batch of this sweep, so it is not filed here — but it is the same defect as F6 wearing a
drill net, and whoever holds `drill.py` should get it.
