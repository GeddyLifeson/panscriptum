# run39 — BATCH 05 AUDIT

Modules owned (from `sweep_plan.batches(16)[4]`, taken programmatically, not transcribed):

    cascade_bridge.py   1933 lines
    completeness.py      737
    sweep_plan.py        576
    worldseed.py         466
    pantheon.py          365
    runguard.py          303
    roll.py              270
    compress_store.py    149
                        ----
                        4799 lines, all read in full, no sampling.

Every finding below was verified against the current source before it was written down —
line numbers re-read, cited files opened, "dead" claims grepped, and the one behavioural
finding (F1) reproduced offline. Where two readings are defensible the item is filed as a
QUESTION at the end rather than as a finding. Nothing in `src/` was edited.

Three claims I set out to file and then **withdrew** after checking them, recorded here so the
next sweep does not re-spend the time:

* `worldseed.py:287-291` says `build_all` has SIX callers and names them. Verified exactly:
  `burgs.py:285`, `navtree.py:49`, `profile.py:155`, `render.py:248`, `sevenfold.py:289`,
  `verify_math.py:960`. The comment is accurate.
* `cascade_bridge.py:25-26` cites `pipeline._pool_answer_usable` and `ask_pool_first` as where a
  parsed-but-unusable cloud answer is rejected. Both exist and are live: `pipeline.py:319` and
  `pipeline.py:355`. Accurate.
* `completeness.category_size`'s docstring claims it has NO caller. Verified: grepping
  `category_size` excluding `category_size_probe` finds only its own `def` and prose. Accurate,
  and deliberately kept.

Two faults I found are **already filed and are not re-filed**: `worldseed.to_options`'s
unreachable `"primitive"` size tier (OWNER, `src/worldseed.py:184`) and
`sweep_plan.coverage_map()` having no callers (OWNER, queue line 604). Both still stand as
described; only their line numbers have drifted (`unreachable_by_url` is now at
`worldseed.py:278`, not the `:236` the order records).

---

## F1 — `dead_forever()`'s memo overrides `PROOF_TTL`, so an exclusion never expires  (MAJOR, RUN)

`src/cascade_bridge.py:415-449`

The comment at `:401-414` describes the bug it is fixing precisely: a process-lifetime memo
"quietly overrode [PROOF_TTL] with 'forever'", so a bucket excluded at 09:00 kept being excluded
"until the process restarts", and a rotated key "stays excluded until restart, so the fix does
not take". The repair keys the memo on the proof file's **mtime**:

    stamp = os.path.getmtime(PROOF)
    if _PROVEN[0] is not None and _PROVEN[0][0] == stamp:
        return _PROVEN[0][1]

`PROOF_TTL` is then applied only on the *recompute* path (`:423`). So as long as
`POOL_PROOF.json` is not rewritten, the mtime never changes, the memo never invalidates, and the
cached exclusion set outlives the TTL by exactly as long as the process runs. The TTL is still
overridden with "forever" — it just now takes a stalled `prove()` rather than a stalled
`dead_forever()` to get there.

Reproduced offline (scratch file, `PROOF_TTL` shrunk to 1.0s so the test takes a second; the
real file was not touched):

    t=0   (fresh, inside TTL)      -> ['acme:free']
    t=1.6 (cached, outside TTL)    -> ['acme:free']
    t=1.6 (recomputed, no memo)    -> []

The third line is what any process starting one second later computes from the identical file.
Two workers therefore disagree about which buckets are in the pool, which is the "two views of
the same pool disagreeing" defect this module's own widen-path comment (`:1331`) calls the one
the project keeps meeting. The direction of the error is pool-narrowing, on the resource this
file repeatedly names the binding constraint, and the readers are exactly the long-lived
sixteen-worker processes the memo comment was written about.

**Remedy:** make the cache key carry both the mtime *and* the freshness verdict — e.g. store
`(stamp, computed_at, out)` and recompute when `time.time() - stamp > PROOF_TTL` regardless of
whether `stamp` changed, or simply expire the memo entry after `PROOF_TTL` seconds. A one-stat
recompute is what the comment already budgets for.

---

## F2 — eight `if pinned:` guards that cannot be false  (INFO, RUN)

`src/cascade_bridge.py:1517, 1586, 1597, 1599, 1607, 1637, 1657, 1667`

`_ask_call` returns at `:1389-1400` when `pinned is None`. From `:1401` to the end of the
function `pinned` is therefore guaranteed non-`None`, and it is a router `Model`, so its
truthiness is not in question either. Every `if pinned` / `pinned and` below that point is
always-true. `:1637` is the clearest: it sits inside `elif pinned:` at `:1607` and re-tests the
same name.

Nothing is wrong today. It is filed because this project's stated concern is that "a check that
cannot fail looks exactly like a check that passed", `liveness.py` hunts this exact mechanical
shape, and a reader of a 300-line branch reasonably takes eight guards as evidence that the
branch can be reached with `pinned` unset — which it cannot. **Remedy:** either drop the
redundant conjuncts, or leave one comment at `:1401` stating the invariant so the guards read as
deliberate belt-and-braces rather than as live conditions.

---

## F3 — `selftest()` cuts its own answer at 400 characters, unmarked  (MINOR, LOCAL)

`src/cascade_bridge.py:1708`

    print(json.dumps({k: v for k, v in got.items() if k != '_via'}, indent=1)[:400])

No ellipsis, no "and N more", no count. Twenty-three lines above it, `:1685-1693` records order
`c48c3de407d8` removing `ready[:12]` from this same function on Hard Rule 0 grounds, with the
argument "printing the lot costs a couple of dozen lines at this scale, which is cheaper than a
truncated answer to the one question the command exists to answer". The identical cut survived
one screen further down, on the payload that IS the live call's result. **Remedy:** print it
whole, or print a marked tail count.

---

## F4 — two stale line citations in `completeness.py`'s sentinel comment  (MINOR, LOCAL)

`src/completeness.py:71-72`

    # `str(h).startswith(("pages:", "doc:"))` -- binding_health.py:406 and health.py:255-257 both
    # do exactly this, and health.py's comment says why

Verified against the current files:

* `binding_health.py:406` is inside an `except Exception: silence.note("binding_health.py:escalate")`
  handler. The idiom actually lives at **`binding_health.py:1018`** — a drift of 612 lines.
* `health.py:255-257` is inside the ledger-flush `_cas_land` block. The idiom, with the comment
  the sentence promises, lives at **`health.py:486-488`** — a drift of 231 lines.

The claimed content does exist; only the addresses are wrong, which is the worst version of this
because the comment reads as verified precedent. **Remedy:** cite by name
(`binding_health.hosts_map filter`, `health`'s fandom-family probe) rather than by number, which
is the fix `compress_store.py:63-66` already applied to two of its own citations.

---

## F5 — `_unmeasured`'s `probe_failures` / `probes_run` parameters have no caller  (MINOR, LOCAL)

`src/completeness.py:445` (signature), call sites `:473`, `:477`, `:489`, `:560`

Order `1065e3eb7cd3` removed `probe_failures=len(probes)` from the unreachable-host branch and
moved the count into the `unreliable` prose (the comment recording it is at `:496-506`). After
that change **no call site passes either parameter** — all four callers rely on the `0` defaults.
Verified by reading every call to `_unmeasured` in the module; there are exactly four.

They are not harmful: the fields are still emitted, honestly, as zeros. But they are now
parameters that only ever take their default, i.e. a knob nothing turns, in a function whose
docstring explains the row shape field by field. **Remedy:** drop the two parameters and set the
fields to `0` in the body, or keep them and note in the docstring that no caller supplies them
and why (the `category_size` docstring in this same file is the house pattern for that).

---

## F6 — `land(only=...)` returns `True` for a file it deliberately did not write  (MINOR, RUN)

`src/completeness.py:638-641`

The docstring's contract line is `"Returns True if the file now holds `rows`"`. With `--only` the
function writes nothing at all and returns `True`.

This is the same discarded-verdict shape the function's own comment at `:665-682` was written to
close, quoted verbatim there: *"Discarding that boolean and returning True made this function's
own contract line ... false in exactly the case the caller most needs to hear about."* The
`--only` exemption is correct policy — a slice must never land over the whole-corpus file — but
the return value now says two different things ("it landed" and "nothing was attempted") through
one channel, and `main():701` turns both into exit 0.

Low blast radius, verified: `foreman.run_completeness_audit` shells this module without `--only`,
so the conflation is confined to hand-run spot checks. **Remedy:** return a third value (or
`(ok, why)`) so "not written on purpose" is distinguishable from "written", and keep `main()`
exiting 0 for the deliberate case.

---

## F7 — `main()` cuts source names to 33 characters, unmarked; fires on 21 of 216 live rows  (MINOR, LOCAL)

`src/completeness.py:711` and `:727` — `str(r["source"])[:33]`

Measured against the live files: 21 of the 216 rows in `data/COMPLETENESS.json` (and 21 of the
215 sources on `data/SWEEP_ROLL.json`) carry names longer than 33 characters, so the cut fires on
every ordinary run. `:727` is the NOT-MEASURED list, which is the part of the output a person
reads in order to go and fix a source — a name cut mid-word there is a name they have to guess
at. There is no marker of any kind.

Note the module gets this right one line down: `:722` prints "rows printed: %d of %d measurable
(the file holds every row)", which is exactly the honest form. **Remedy:** widen the column or
mark the cut; the row count precedent at `:722` is the pattern.

---

## F8 — category keys truncated to 40 characters in `catalogued_counts`  (INFO, LOCAL)

`src/completeness.py:293` — `c[str(e.get("category") or "?")[:40]] += 1`

Two different categories sharing a 40-character prefix would silently fold into one count. I
checked the live vocabulary: `wiki_source.CATEGORY_PROBES` holds seven canonical categories and
their 40-character prefixes are all distinct, so **nothing collides today** and the downstream
`k.startswith("Persons")` test is unaffected. Filed as latent, not live: `data/records/*.json` is
written by a separate cloud session and `category` is not constrained to those seven values, so
the guarantee is a property of today's data rather than of the code.

---

## F9 — stale citation of `silence.py` in a load-bearing comment  (MINOR, RUN)

`src/sweep_plan.py:272-276`

    # `silence.write_json` re-raises a failed dump
    # (silence.py:409-415, `except Exception: _discard_tmp(tmp); raise`)

Verified: `silence.write_json` is defined at **`silence.py:471`**, and the
`except Exception: _discard_tmp(tmp); raise` shape is at **`silence.py:512-517`**. Lines 409-415
are inside `replace_if_unchanged`, an unrelated function, and contain no such code.

This matters more than an ordinary drift because the citation is the entire justification for the
change it documents (order `6794cb447987`, moving the `open`/`json.dump` inside the try): the
argument is "the condition that sends control into this fallback is usually the same condition
that breaks it two lines later", and the evidence for it is a line range that no longer holds the
code. The claim is still TRUE — I checked the current `write_json` — only the address is wrong.
**Remedy:** cite `silence.write_json`'s dump handler by name.

---

## F10 — `latest_run()` has no caller; the check it was written for reimplemented it inline  (MINOR, RUN)

`src/sweep_plan.py:392-434`

`grep -rn "latest_run(" src/*.py` returns the `def` and two `verify_math` **comment** lines. There
is no call anywhere.

Its docstring presents it as the live fix for a named defect: *"THE COMPLETENESS CHECK MUST NOT
NAME A RUN IN A LITERAL ... Returns None rather than a guess when there is no evidence, so the
caller can FAIL CLOSED instead of proving the completeness of a sweep that never happened."* That
caller is gone. Order `b18acbb35760` replaced it — `verify_math.py:5007-5028` now globs
`_SP20n.SHARDS` itself, builds `_at20n`/`_batches20n`, and derives `_run20n` from a
finished-run rule (`latest_run` has no notion of a run being over, which is exactly why it was
dropped).

So `sweep_plan` now carries two dead readers of the shard directory (`latest_run`, and
`coverage_map` which is already filed) while the one live consumer duplicates the shard scan.
This is a declared safety nothing calls, in the module whose job is proving a sweep was complete.
**Remedy:** either delete `latest_run` and say so, or — better, and this is the substance — move
`verify_math`'s finished-run selection INTO `sweep_plan` as `latest_finished_run(planned)` and
have the check call it, so the shard-reading rule has one implementation the way `runguard` gives
the guard protocol one.

---

## F11 — `modules()`'s `unreadable` marker reaches nothing  (MINOR, RUN)

`src/sweep_plan.py:85-97`

The comment states the intent plainly: *"Recorded, and marked so the plan itself carries the
fault."* The record half is real (`silence.note`, and `{"module":…, "lines":0, "unreadable":
True}`). The **marked-in-the-plan half is not**: `batches()` at `:113` keeps only `m["module"]`,
so the flag is dropped before the plan is built; `--batches` prints the batches, not `modules()`;
and the `else` branch of `main()` prints only counts. `grep -rn '"unreadable"' src/*.py` finds no
reader of this key anywhere.

The consequence is the one the comment was written to prevent: an unreadable module still sorts
last at `lines: 0`, still packs into a bin as free weight, and still reads in the emitted plan
exactly like an empty stub. **Remedy:** carry the flag through `batches()` (e.g. an `unreadable`
list per bin, or a `# N module(s) UNREADABLE` line on the `--batches` footer at `:527-529`), so
the plan a coordinator dispatches actually says which files could not be sized.

---

## F12 — `URL_SETTABLE` is read by nothing, and has diverged from what is emitted  (MINOR, OWNER)

`src/worldseed.py:262`

    URL_SETTABLE = ("seed", "template", "width", "height")

`grep -rn "URL_SETTABLE" src/` matches only this line (plus a stale `.pyc`). Nothing reads it —
`to_fmg_query` at `:273-274` builds its own dict literal. The two have already drifted: the
function additionally emits `"options": "default"`, which `URL_SETTABLE` does not list.

The constant sits directly under a 17-line empirically-measured comment block (the Azgaar
v1.146.0 test table) whose whole point is that "emitting a parameter that is silently discarded
is worse than omitting it" — so a reader takes `URL_SETTABLE` as the authoritative list, and it
is neither authoritative (nothing enforces it) nor complete. This is the same keep-or-delete
judgment already sitting in the OWNER queue for `unreachable_by_url` in this module, which is why
it goes to the same handler rather than being tidied away by a maintenance pass. **Remedy:**
either have `to_fmg_query` build its query FROM `URL_SETTABLE` (which makes the constant
load-bearing and the drift impossible), or delete it and let the comment block carry the finding
as prose.

---

## F13 — dead assignment in `build_all`'s onomasticon handler  (INFO, LOCAL)

`src/worldseed.py:324-325`

    except Exception:
        silence.note("worldseed.py:onomasticon-load")
        ono = {}

`ono` is never read after this point — the only consumer is the `for v in (ono or {}).values()`
loop *inside* the `try`, which the exception has already left. `reg_by_group` is what the rest of
the function reads, and it is correctly initialised at `:315`. Harmless; noted because it reads
as a fallback that does something and does not. **Remedy:** delete the assignment.

---

## F14 — `pantheon --full` silently prints 6 of 21 entries  (MINOR, RUN)

`src/pantheon.py:318-320`

    if a.full:
        for n, rec in rank:
            if n not in out:
                continue

`out` is `compute(GODS)` — the six hand-built gods. `rank` is `combined`, which merges
`data/Z_FIGHTERS.json`. So the ranked table above (`:292-316`) prints all 21 entries and the
detail view prints six, with no note, no count, and nothing telling the reader that fifteen
entries were skipped.

I checked whether the skip is structurally necessary. It is not: all 15 Z_FIGHTERS entries carry
the identical shape the detail loop reads — `anchor`, `assay`, `axes`, `epoch`, `presence` — and
every one of them has all eleven `assay.WEIGHTS` axes present with `score`/`cited`/`provenance`.
The detail block would render them unchanged.

This is the shape the same function was already repaired for twice: `:328-343` records order
`9d24c8a5febf` removing `d["cited"][:58]` on the grounds that *"a cap on the evidence for a claim
is not a display convenience"*, in "the view whose flag is literally named --full". A view named
`--full` that drops 71% of its rows is the same argument one level up. **Remedy:** print the
merged entries too (they need no new code), or, if the intent really is "only the hand-built
tier gets a worksheet", say so in a line that names how many were omitted and why.

---

## F15 — `roll --list` cuts the exclusion reason to 150 characters; live, it drops 74% of it  (MINOR, LOCAL)

`src/roll.py:263-264`

    print("  %-46s %6d entries" % ((name or "?")[:45], n))
    print("      %s" % why[:150])

Measured against the live `data/SWEEP_ROLL.json`: 8 sources are `out-of-scope`, and **four of them
carry 587-character notes**, so `[:150]` silently discards 437 characters — 74% — of the recorded
reason, mid-sentence, with no ellipsis. (The `[:45]` on the name does not fire today; the longest
excluded name is 33. Latent.)

This is the module that exists to make exclusion legible. `out_of_scope`'s own docstring is
emphatic about it: *"RETURNS THE REASON, NOT JUST THE NAME. An exclusion with no reason attached
is how a real source gets quietly dropped and nobody can reconstruct why."* The one CLI a person
runs to read those reasons cuts three quarters of them off. Structurally identical to
`pantheon.py`'s `d["cited"][:58]` (order `9d24c8a5febf`), which was filed and fixed on exactly
this reasoning. **Remedy:** wrap the note instead of cutting it — `textwrap.wrap` with a hanging
indent, which is precisely what `pantheon.py:344-348` now does for its citations.

---

## F16 — the one remaining line-numbered citation in `compress_store.py` has drifted  (MINOR, LOCAL)

`src/compress_store.py:124`

    ...and it finds it at the moment the damage matters -- when catalog.py:97 serves the chapter
    to a reader.

Verified: `catalog.py:97` is a **blank line**. `cmd_read` begins at `catalog.py:98` and the
actual `compress_store.load(...)` call is at `catalog.py:108`.

The joke this file already told on itself applies again. `:63-66` records order `bf22c557852e`
de-numbering `generate.py:554` because it "had drifted onto generate.py's own comment about not
putting line numbers in strings, the joke writing itself", and `:81-82` de-numbers
`generate.py:468` for the same reason. `catalog.py:97` is the third citation in the same file,
was left numbered, and has drifted. **Remedy:** name it — "`catalog.cmd_read` serves the chapter
to a reader" — matching what the other two were changed to.

---

## QUESTIONS — defensible either way, filed as questions, not as findings

**Q1. `completeness.primary` can never be assigned for a non-fandom host.**
`:434` computes `sub = subdomain(h) or ""`, and `subdomain()` returns `None` for anything not
ending in `.fandom.com`. So the "longest name match wins" rule at `:436-438` is structurally
unreachable off Fandom, and every one of the 22 sources sharing `en.wikipedia.org` gets
`unreliable = "...is not the primary; denominator belongs to nobody"`. For Wikipedia that outcome
is arguably CORRECT — no single source owns it, and the comment at `:429-430` explicitly says
"where no name matches, no source claims it and all of them are marked". But the rule is not
being *applied and failing*, it is being *skipped*, and a future shared non-Fandom host whose name
does match (a hypothetical `rimworldwiki.com` shared by two sources) could never claim primacy.
Is the Fandom-only restriction intended, or is it an artefact of reusing `subdomain()` where a
host-substring test was meant?

**Q2. `completeness.work` treats a 0-page category as an absent one.**
`:522` and `:529` guard with `if n:`, so `categoryinfo.pages == 0` — a category that exists and is
empty, which is a real measurement — is dropped from `sizes` exactly like "no such category".
Today the downstream outcome is identical (both routes lead to the same row-absent or
`why="no category probe returned a size"` treatment), so nothing is currently wrong. But
`category_size_probe` was split out of `category_size` specifically to stop this module conflating
two conditions under one `None`, and the caller re-conflates a third. Worth a ruling on whether
`0` should enter `sizes`.

**Q3. `runguard.holder_is_live` fails OPEN on an unreadable heartbeat.**
`:148-151`: a record with an agent and `done: False` but a non-numeric `heartbeat` returns
`False`, i.e. "a run may proceed". `read()`'s docstring argues the fail-open case well for an
unreadable FILE ("refusing to run on a corrupt guard would wedge the pass permanently"), but this
is a different case — the file parsed, a run is on record as started, and only its clock is
unreadable. Against Hard Rule -1's FAIL CLOSED this is the one place in the module that answers
"I don't know" with GO. It may still be the right call for the same wedging reason; it is not
argued anywhere, which is why it is a question. Note also that `rec.get("done")` is a truthiness
test, so a hand-edited `"done": "false"` reads as done — the same `bool()`-instead-of-strict shape
CLAUDE.md records `overnight.py` being caught on with `prose_enabled: "false"`.

**Q4. `cascade_bridge.try_disabled` records no `reason`.**
`:1880-1883` downgrades `ANSWERS` to `no answer` when the served bucket does not match, but unlike
`prove()` (`:1804-1812`, which writes a `reason` explaining which of the two mismatch cases fired)
it writes no reason field at all, and `try_disabled` rows have no `reason` key at any exit. Since
this is "the tool a person reaches for precisely when they distrust the pool" (its own words at
`:1874`), a bare `no answer` where `prove` would have said "the call was served by X" loses the
distinction between a real refusal and a routing surprise. Deliberate asymmetry, or the half of
order `77d59411ca75` that did not carry over?
