# AUDIT — sweep run55, batch 09

Modules read in full, every line: `foreman.py` (1,992), `overwatch.py` (1,101), `completeness.py`
(866), `custodes.py` (698), `worldseed.py` (532), `runguard.py` (382), `descending_ladder.py`
(357), `tells.py` (296). 6,224 lines.

Method: each file read top to bottom through the Read tool (no sampling, no grep-only passes).
Claims that cite another module were checked against that module's source and are marked as
cross-batch where they are. Nothing under `src/`, `data/`, `state/` was written. Two modules were
driven to confirm a reading — `tells.py` was imported and `scan`/`prompt_in_sync` run (it writes
nothing; it only reads its own source and `prompts/system_style.txt`), and a standalone
ten-element arithmetic model of the Custodes tilt table was run in a scratch process. `custodes.convene`
was NOT run: it reaches `silence.note` through `_abstained`, which writes the health ledger under
`state/`, and the brief forbids a nominally read-only audit writing into the thing it measures.
`completeness.audit`, `foreman.round_once` and `overwatch.round_once` were likewise not executed.

---

## THE TWO LIVE ORDERS

### Order `f5b8e4afb558` — `subdomain()` returns None for every non-fandom host

**The reading in the order is correct on the mechanism.** `subdomain()` (completeness.py:61-65)
returns `None` unless the host ends `.fandom.com`. The `primary` table is built at :442-449 as

    sub = subdomain(h) or ""
    key = "".join(ch for ch in str(src).lower() if ch.isalnum())
    if (key and key in sub.replace("-", "") and ...):
        primary[h] = (src, key)

so for a non-fandom host `sub` is `""`, `key in ""` is False for every non-empty key, and
`primary[h]` is never assigned. The test at :664,
`(primary.get(host) or (None, None))[0] != src`, is therefore True for every source on a shared
non-fandom host: the contest the message describes is never held.

**The message already states it, and the remedy changes no aggregate.** Remedy (a) is present in
the source as it stands (:664-671): when `subdomain(host) is None` the row's `unreliable` reads
"... no primary can be identified for a non-fandom host at all -- the only discriminator this
module implements is a source name matching the wiki's SUBDOMAIN, and this host has none. Not
'this source lost'; 'the question was never asked'." Nothing numeric moves across that branch,
and this can be shown rather than asserted: both arms assign a non-empty `why`, so `unreliable`
is truthy either way; the `good`/`bad` split at :807-808 is computed from truthiness alone, the
`total_wiki` / `total_have` sums at :834-835 run over `good` only, and every downstream consumer
skips on truthiness (`foreman._catalogue_batch`, foreman.py:881, `if c.get("unreliable"):
continue`). Only the sentence changes. So the answer to the question put is: **yes, and it is
already done; keeping it costs no aggregate.**

**Two corrections to the order's premise**, both filed below as findings: the four
`www.dandwiki.com` sources can never reach that branch at all (they return five branches earlier),
and reaching it at all requires a catalogue record on disk plus at least one non-zero probe size.
On the landed `data/COMPLETENESS.json` today all 32 of the wikipedia/dandwiki rows carry the
`host unreachable` sentence, not this one — they are permanently unreliable, as the order says,
but by a different branch than the one the order names.

### Order `5bb12b398783` — `prior_share = 1.0` when `total_var` is zero

custodes.py:508-509:

    prior_share = (prior_var / total_var) if total_var > 0 else 1.0
    prior_share = max(0.0, min(1.0, prior_share))

**What the default does to a published interval: nothing to its WIDTH, and everything to its
meaning.** `total_var == 0` means the ten readings are identical, so `total_sd` is 0 and
`half = max(1.96 * 0, *(abs(v - consensus) for v in vals))` is 0.0 (:513); `half += stale` (:517)
adds 0.0 in production, because no caller supplies `distance`/`years_since` (the module's own
docstring, :437-440). The published `interval` is therefore `0.00` whatever `prior_share` is.
What the default decides is the **decomposition**: `prior_divergence_share: 1.0` and
`attestation_floor_share: 0.0` (:539-540), published beside the fixed `interpretation` string "a
high prior share means further fieldwork will NOT narrow this; the disagreement is between
standpoints, not about facts" (:552). That is the module's strongest claim — the Goku half of the
charter's Goku/Kenshiro contrast — asserted off an undefined 0/0, at the one input where there is
no disagreement to decompose. `0.0` would be an equally arbitrary assertion in the other
direction. The honest third value is "unmeasured", and this module already has that shape
everywhere else: `staleness_measured: False` plus a named `currency_source`,
`comparability_measured: False` plus a named reason, `attestation_recognised: False` plus the
substituted quality. `prior_share` is the one published field with no such flag.

**It is not reachable with the table as it stands**, which is the other half of the answer.
`reading = idx + decimal_i + tilt_i * (1 + sens_i * (1 - q))`, and the ten tilts are ten distinct
values (+0.09 … -0.05); identity across all ten would require the per-Custos `decimal`s to cancel
the tilt spread exactly. `_custos_reading` returns None only when `A.assay(...)["decimal"]` is
None, which is a property of the inputs and not of the Custos, so `readings` is either 0 or 10 and
the `len(readings) < 2` band-only return (:496) covers the 0 case. So today this is a branch that
cannot fire, guarding a field it would state falsely if it did.

**The clamp on the next line is the same shape and is worth naming with it.** `max(0.0, min(1.0,
...))` silently converts any `prior_var > total_var` into a flat 1.0 / 0.0 split. Modelling the
tilt table alone across the charter's five grades gives raw shares 0.379 (q=0) → 0.465 → 0.583 →
0.751 → 1.000 (q=1), and `ATTESTATION_QUALITY` never reaches 1.0 (best grade is
`1 - 0.08/0.55 ≈ 0.855`), so prior_sd < total_sd strictly and the clamp is not firing today
either. Both are published-field guards that currently cannot fail.

---

## completeness.py

Read line by line. Checked: the two probe paths against their transports, the cache's lock/snapshot
discipline, every arm of `work()` against the row shape `_unmeasured` promises, `land()`'s three
outcomes against `main()`'s use of them, and the `primary`/`shared` construction against the live
`data/WIKI_HOSTS.json`.

### MINOR — the order-f5b8e4afb558 comment's own claim about dandwiki is false
**Where:** src/completeness.py:656-659, against :546, :553-557 and :583-584.
**What:** the comment states "Every one of the 28 sources sharing `en.wikipedia.org` and the 4
sharing `www.dandwiki.com` takes this branch permanently."
**Why it is wrong:** the four dandwiki sources never reach it. `www.dandwiki.com` is MODE_RAW
(`endpoint.api_url` returns a URL only for MODE_API — endpoint.py:275-278, cross-batch citation,
verified), so `api_base(host)` is None, `work()` falls to the `else` at :553, sets
`no_denominator`, and returns `_unmeasured` at :584 — five branches before the `elif shared[host]
> 1` chain at :664. Their `unreliable` sentence is the raw-wikitext one, not the shared-host one.
The wikipedia half is right about the mechanism but also conditional: :664 is only reached when
`rec is not None` (:637 wins first) and at least one probe returned a non-zero size (:640 wins
next). This matters because the sentence is the evidence a reader uses to decide what the
shared-host ruling has to cover.
**Confidence:** read the branch order in `work()`, confirmed `api_url`'s MODE_API-only return in
endpoint.py, and confirmed against the landed file that all 32 rows currently carry the
`host unreachable` text instead.

### MINOR — "none of the categories exists" also fires for categories that exist and are empty
**Where:** src/completeness.py:611-617, against :544 and :551.
**What:** `sizes[cand] = n` is guarded by `if n:`, so a probe that answers with a real
`categoryinfo` block holding `pages: 0` is not recorded. With every probe answering that way,
`sizes` is empty and `failed` is 0, and the row is returned saying "every category probe was
answered and none of the %d CATEGORY_PROBES categories exists on %s".
**Why it is wrong:** `got = ci.get("pages", 0)` is only assigned when `ci` is truthy, i.e. when the
category **does** exist. A wiki whose probed categories exist but are empty is reported as a wiki
that has no such categories. Both end in an `unreliable` row so no aggregate moves, but the row's
sentence — which is the whole product of that branch — states the wrong fact about the wiki, and
it is the sentence a curator would act on when deciding whether `CATEGORY_PROBES` needs a new
name for that host.
**Confidence:** read `category_size_probe` (:194-200) and `category_size_probe_host` (:270-276);
the `if ci:` / `if n:` asymmetry is visible in both.

### INFO — three different counts of the same quantity inside one file, all stale
**Where:** src/completeness.py:248 ("22 sources share en.wikipedia.org"), :410 ("22 on
en.wikipedia.org … and 5 `pages:`/`doc:` sentinels … plus 7 with no host", "164 of the 203
sources"), :657 ("the 28 sources sharing `en.wikipedia.org`").
**What:** the file gives 22 in two places and 28 in a third for the same set.
**Why it is wrong:** measured against `data/WIKI_HOSTS.json` this run: 208 sources, 164 fandom, 28
`en.wikipedia.org`, 4 `www.dandwiki.com`, 1 `rimworldwiki.com`, 7 sentinels, 4 with no host. So
:657 is right and :248/:410 are stale, and the "THIRTY-TWO hosted sources" arithmetic at :410
(22+4+1+5) no longer adds up on either reading. This is the "all 57 nets" hazard CLAUDE.md records
under order `864a626a258e` — a figure in prose that a later reader reasons from.
**Confidence:** counted the live hosts file directly.

### INFO — `_rec()` exists for this and `work()` re-derives it inline
**Where:** src/completeness.py:453-454 (`_rec`) against :619.
**What:** `_rec(src)` is defined as the loose-key record lookup; `work()` writes the identical two
`byslug.get(...)` expressions out longhand at :619 instead of calling it.
**Why it matters:** identical today, so nothing is wrong now; it is the two-spellings-of-one-fact
shape this file refuses elsewhere (`_cs_put`'s "one constant, named once"), and the two lookups
would have to be edited together.
**Confidence:** compared the two expressions character by character.

### INFO — one `byslug` key is not lower-cased while every lookup is
**Where:** src/completeness.py:404 (`byslug[v["file"][:-5].replace("-", " ")] = v`) against :454
and :619, which both look up `str(src).lower()`.
**Why it is latent, not live:** every filename under `data/records/` is lower-case today (checked:
0 of them contain an upper-case character), so the key can never miss. A hand-added record with a
capital in its filename would not resolve.
**Confidence:** listed `data/records/` and grepped for upper-case.

---

## custodes.py

Read line by line. Checked: the ten degrees of freedom against the ten table entries, every
`tilt`/`evidence_sensitivity` pair against `table_faults`' own rule, the abstention plumbing
against what `convene` publishes on both return paths, and the interval arithmetic against the
coverage claim it publishes.

### MINOR — `prior_share = 1.0` states the maximal irreducibility claim on an undefined 0/0
Full treatment above under order `5bb12b398783`. **Where:** src/custodes.py:508-509. Reported as a
QUESTION for the coordinator rather than a fix: the value is unreachable with today's table, and
choosing `0.0` instead would be arbitrary in the other direction — what the field is missing is
the `*_measured: False` + named-reason shape this module already uses three times over.

### INFO — the guarantee at :551 is marked as unable to fail, and the marking is correct
**Where:** src/custodes.py:542-551. `covers_every_reading` re-tests a property `half` is defined
to have. The comment says so in those words ("this is a GUARANTEE being published, not a check
being run … it cannot fail") and routes the genuinely informative version (did the 1.96·sd band
alone cover?) to NEXT_STEPS. Saw the marking; moved on.

### INFO — `_transit_widening`'s third state is unreachable and says so
**Where:** src/custodes.py:411-417. The "no Custos is dispersive in dof=currency" sentence cannot
be produced while Lumen carries the flag, and the comment states that it exists so that removing
the flag reads as a change in the college rather than as a measurement. Saw the marking.

---

## foreman.py

Read line by line. Checked: every remedy's `(did, what)` contract against `round_once`'s
break/`always` logic, both `wmic`-driven killers against their `lognames.OWNER` fragments, the
patch gate chain (`lines_changed`, `regex_touched`, `_checks_pass`, `_contracts_pass`) against
what the module docstring sells it as, and `_catalogue_batch`'s rotation against Hard Rule 0.
`allsweep.VERIFIERS` was checked for the `item[0], item[1]` unpacking at :1442 — it is a
`Verifier(label, argv, rc_meaning)` namedtuple (allsweep.py:216-241, cross-batch), so the
unpacking holds.

### MINOR — a denied restart-stamp write leaves the ollama rate limit off, and the remedy still reports success
**Where:** src/foreman.py:1195-1206.
**What:** `st = {"count": …+1, "last": time.time()}` is written through `silence.write_json`; a
denied replace is answered with `silence.note("foreman.py:ollama-stamp-denied")` and execution
falls straight through to `return True, "ollama restarted (automated restart #%d)"`.
**Why it is wrong:** the stamp **is** the 30-minute rate limit (:1176). If it never lands and the
file does not exist, the next round's read raises `FileNotFoundError`, takes the benign
`st = {"count": 0, "last": 0}` branch (:1168-1169), computes `time.time() - 0 >= 1800`, and kills
`ollama` and `llama-server` again — every round, with only a janitor-level note, while the
docstring's promise ("rate-limited: at most one automated restart per 30 minutes, so a deeper
fault escalates to the owner instead of being restart-looped into invisibility") no longer holds
and the operational log reports each kill as a successful remedy. The comment at :1196-1201 names
this hazard exactly ("the guard failing open, silently") and the code closes only half of it: it
notices, it does not refuse and it does not tell the caller. Filed MINOR rather than MAJOR because
nothing else in `src/` reads `state/OLLAMA_RESTARTS.json` (grepped: `RESTART_STAMP` is the only
mention in the tree), so a denied replace on it is unlikely — but the failure direction is the
destructive one, which is why the sibling READ path at :1170-1175 was hardened to refuse.
**Confidence:** traced the read branch, the write branch and the return value; grepped for other
readers of the stamp.

### MINOR — `NEVER_DEDUPED` is DENYLIST plus one name, not two
**Where:** src/foreman.py:129-140 against :126-127.
**What:** the comment says `NEVER_DEDUPED` "currently starts as DENYLIST plus two names" and names
"overnight" and "autostart".
**Why it is wrong:** order `881ff7f49438` put `overnight` into `DENYLIST` itself (:127), so
`DENYLIST | {"overnight", "autostart"}` adds exactly one member — 13, not 12+2. The comment's
argument (the two questions are separate policies and must not silently couple) survives intact;
only its arithmetic about the present state is wrong, and that arithmetic is the evidence a reader
uses to judge whether the two sets have already drifted together.
**Confidence:** read both literals.

### INFO — a source that becomes temporarily unnameable loses its dispatch stamp
**Where:** src/foreman.py:911-919 and :939.
**What:** `unnameable` sources are popped out of `gap` (:918-919), and the attempt ledger is then
pruned with `seen = {k: v for k, v in seen.items() if k in gap}` (:939).
**Why it matters:** nameability is not a property of the source, it is a property of the current
short-source set — `f` must match exactly one member of `gap` (:914) — so a source can leave and
re-enter `unnameable` as other sources are catalogued. Each time it leaves, its dispatch timestamp
has already been dropped, so it returns to the queue with `float(seen.get(s) or 0.0) == 0.0` and
sorts to the very front, ahead of sources that genuinely waited longer. Nothing is lost and the
window still turns; the ordering the docstring promises ("LAST-DISPATCHED FIRST") is not exactly
what is computed. Raised as a QUESTION — pruning the ledger to `gap` is clearly deliberate ("forget
sources no longer short"), and whether unnameable counts as "no longer short" is a judgment.
**Confidence:** read the pop, the prune and the sort key together.

---

## overwatch.py

Read line by line. Checked: the damaged-ledger path against `save`'s `_UNPRESERVED` refusal, the
merge rules against `_progress`/`_finished_at`, the cloud-budget yield against both places that
consume `complete`/`None`, and the report writer against every key `structure()` can produce. The
live ledger was read (not written) to measure the finding below.

### MAJOR — a fingerprint that has reached ANY terminal state permanently blocks re-detection
**Where:** src/overwatch.py:996-1002, against the never-delete rule stated at :235-236 and the
retire loop at :948-954.
**What:** when the model reports a finding, `round_once` does

    fid = _fingerprint(m, f)
    if fid in led["findings"]:
        continue

with no reference to that finding's `state`. Nothing in the module ever removes a key (`save`'s
own docstring: "NOTHING in this module ever deletes a finding or a `seen` entry — retirement is a
state change, not a removal").
**Why it is wrong:** the retire loop sets `state = "retired"` for every open finding on a module
whose file digest changed — i.e. on **any** edit to that file, for any reason, related or not.
The fingerprint stays. So a real defect that was filed, then retired because someone edited an
unrelated function in the same module, can never be re-filed by any future round: `WATCH.md`
lists only `state == "open"` (:782) and `foreman.round_once`'s MODEL lane reads only
`state == "open"` (foreman.py:1874). The same is true of a finding `verify_open` closed on a
mistaken `refuted` verdict (:743-747) — one wrong auto-triage call immunises that defect forever.
Measured on the live `data/OVERWATCH.json` this run: 1,904 findings, of which 949 retired, 944
closed, 5 refuted, 1 stale and **5 open** — 1,899 fingerprints, 99.7% of the ledger, are terminal
and therefore permanently unreportable. The watcher's detection surface shrinks monotonically and
nothing measures the shrinkage.
**Reported as a QUESTION as well as a finding,** per the brief: the docstring's NOVEL filter says
"findings are fingerprinted and remembered. The same one is reported ONCE, and stays open until
the code it points at changes" (:47-48), which is compatible with the observed behaviour on a
generous reading. What the docstring does **not** say, and what the code does, is that a
recurrence after the change is also suppressed. The sharp edge is the retire-on-any-edit rule:
retirement is triggered by the file moving, not by the defect being fixed, so a surviving defect
is silently converted into one the watcher can never mention again. The cheap version of a fix
(allow re-open when a fingerprint's prior state is `retired`, keep the suppression for `closed`)
is a behaviour change and is not proposed here.
**Confidence:** read the dedupe, the retire loop and the never-delete rule; confirmed both
consumers filter on `state == "open"`; counted the states in the live ledger.

### INFO — two sites index `f["module"]` where the rest of the module uses `.get`
**Where:** src/overwatch.py:951 (`_digest(os.path.join(SRC, f["module"] + ".py"))`) and :1060
(`key=lambda x: x["module"]`).
**Why it is latent:** every one of the 1,904 rows on disk carries the key (checked: 0 missing), and
this module always writes it. A row merged in from an older spelling without it would raise
KeyError out of the standing `--loop` job at the top of the round, before any save. Named because
the same function's neighbours (:1678 in foreman, :868 here) all use `.get`.
**Confidence:** read both sites; counted the ledger.

### INFO — the ledger's two-writer and preservation paths read correctly
Checked end to end and found nothing: `load()` distinguishes absent / unparseable / wrong-shape and
routes the last two through the same preserve-then-refuse road; `save()` refuses while
`_UNPRESERVED` is on, reconciles against the digest it stamped, and gates on `write_json`'s
verdict; `_merge_ledgers` is monotone per key and ties to disk with a strict `>`; `_finished_at`
now normalises both vocabularies to epoch seconds so the `retired`-beats-`closed` string bug
(order `72e33d06d4eb`) is genuinely closed. `_LOCAL_BUSY` is reset per round, so the
watcher-stops-watching failure is closed too.

---

## worldseed.py

Read line by line. Checked: every feature table key against its consumer table
(`TEMPLATE`/`CLIMATE_BAND` cover every `LANDFORM`/`CLIMATE` name), the band parser against all four
provenance arms, the `limit is not None` guard against its own stated off-by-one history, and the
collision report against what `--write` actually stores.

### MINOR — a line citation in a repair comment points 40 lines off
**Where:** src/worldseed.py:368 against :355.
**What:** the comment explaining order `0bbf8ff1e3aa` says "What this handler actually leaves
behind is `reg_by_group`, already initialised at line 315 outside the try".
**Why it is wrong:** `reg_by_group, bad_rows = {}, 0` is at line 355. 315 is inside the
`to_options` return dict. The argument is sound and the code is right; the citation is not, and
this file's own doctrine (descending_ladder.py:47, "a comment asserting a completed action that
never happened is worse than no comment") is about exactly this.
**Confidence:** read both lines.

### INFO — the six-callers claim at :325-333 is still exactly right
`WS.build_all` is called from `burgs.py:302`, `navtree.py:49`, `profile.py:204`, `render.py:309`,
`sevenfold.py:292` and `verify_math.py:10850-10854`. Six, and `address_space.py` still does not
import worldseed — which is what order `bf22c557852e` corrected. Verified rather than assumed
because the count is load-bearing for the "widening the signature would break every one" argument.

### INFO — the `"primitive"` and `URL_SETTABLE` / `unreachable_by_url` retentions are marked
**Where:** src/worldseed.py:218-246, :283-292, :308-319. All three carry explicit owner rulings
(`40e98eed6870`, `e68664e621bf`, `c0384991bfc5`) of the 2026-09-08 "mark and keep, delete nothing"
kind. Saw the markings; nothing re-filed.

---

## runguard.py

Read line by line and found nothing. Checked specifically: that `claim()`, `beat()` and `release()`
all take the digest **before** the read (:215, :280, :316) so a competitor landing in the gap makes
our write lose rather than theirs; that `beat` and `release` both refuse on a record whose `agent`
is not ours and that `beat` additionally refuses a closed record (:291-295), which is the m27
invariant stated in the module docstring, enforced in both places it can be violated; that
`_land_claim` stages through a pid+thread temp name and removes it on a refused swap; that
`read_verdict`'s three faults (unparseable, wrong-shape, unfinished-with-no-numeric-heartbeat) each
produce the answer its docstring says, and that the fail-open on a corrupt guard is now announced
at SAFETY through `escalation.escalate` with `claim_allowed: True` in the evidence (:234-247) —
i.e. the departure from Hard Rule -1 leaves a record, which is what the 2026-09-08 ruling asked
for. `holder_is_live` answers False for a missing or non-numeric heartbeat, which is the arm that
ruling deliberately kept open. The only cosmetic point is that `main()` prints "nan min ago" for a
record with no numeric heartbeat (:368-371); it is a console line beside an explicit `verdict`
row, so it misleads nobody.

## tells.py

Read line by line and found nothing wrong. Checked by running the module (it writes nothing):
`LEXICAL` 60 entries, all distinct; `LEXICAL_FICTION` 32, all distinct; no overlap between the two,
so `_LEX` holds 92 patterns and the printed total is honest. `STRUCTURAL` 31 and `DISCOURSE` 15
share no key, so `ALL_PATTERNS` is 46 and the `{**a, **b}` merge loses nothing. `_anchor` strips
exactly the four characters of `r"^\s*"` and only from patterns that start with it. The control-
character guard at :173-175 covers both compiled sets. The self-check passage fires 8 tells,
including both halves of the `it's not X, it's Y` and `not merely X but Y` entries the comments
defend. `prompt_in_sync()` returns `(True, "system_style.txt carries the generated block verbatim
(2683 chars)")`, so the safety order `a08557925d87` added is in effect and the instruction and the
checker have not drifted.

### INFO — the docstring calls `LEXICAL` "single words"; a dozen entries are phrases
**Where:** src/tells.py:16-17 against :46-57.
**What:** "LEXICAL single words that machine prose reaches for far past their natural rate:
delve, tapestry, myriad, meticulous, seamless, vibrant, testament, realm, boasts."
**Why it is a (small) defect of fact:** the list holds `"realm of"`, `"landscape of"`,
`"journey of"`, `"navigate the"`, `"steeped in"`, `"myriad of"` and `"treasure trove"`, and it does
**not** hold the bare `"realm"` the sentence names as an example. Worth a line only because
`prompt_section()` hands these entries to the model verbatim, and the difference between banning
"realm" and banning "realm of" is a real difference in the instruction.
**Confidence:** read both, and confirmed `"realm"` is absent from the list by exact membership.

## descending_ladder.py

Read line by line. Checked: the length column for strict monotonicity, `rung_for_length`'s guards
at both ends, `PLANCK_ENERGY` against `m_P c²` (1.9561e9 J, matching the table's own `-14 Pk
1.956e9`), and both refusal guards in `shrink_report`/`transgression_bits` against the orders that
added them. The held-and-unwired claim is still true: nothing in `src/` imports the module and none
of its seven public functions is called anywhere.

### MINOR — the docstring's "returns three lines" measurement is stale, and one of the three citations is gone
**Where:** src/descending_ladder.py:50-55.
**What:** the docstring states that a grep for the module's own names "returns three lines:
`derivation.py`'s `SCAN_MODULES` list, `anchors.py:43` … and a historical note in
`secondopinion.py`."
**Why it is wrong:** the same grep run this sweep returns ten lines across eight files —
`anchors.py:43`, `assay.py:249` (a **second** "Use `transgression_bits()`" pointer, not mentioned),
`drill.py:248`, `liveness.py:359`, `onomast.py:453`, `scale_theories.py:48` and `:52`,
`secondopinion.py:25` and `:30`, `tempus.py:46`. And `derivation.py` no longer names the module at
all: `SCAN_MODULES` is built from `os.listdir(HERE)` at derivation.py:596, so the citation points
at a list that is now computed. The load-bearing half of the paragraph — no import, no call —
**is** still true and I verified it; it is the enumeration a reader would use to check the claim
that has decayed, in a docstring whose own next paragraph argues that a comment asserting
something that is not so is worse than no comment.
**Confidence:** ran the module's own grep, excluding the file itself; opened derivation.py:596.

### INFO — a decade of length (1e6–1e7 m) has no rung on either ladder
**Where:** src/descending_ladder.py:186-214 against the module docstring at :14-16.
**What:** `rung_for_length` returns `(None, None)` above `DESCENDING[0][3]` = 1e6 m, and the
docstring says that range is "the ASCENDING Ladder's territory, whose first rung is Planet at ~1e7
m."
**Why it is worth a line:** between 1e6 and 1e7 m neither ladder has a rung, so the gap the module
was written to close ("there are no rung-characteristic lengths below 1e7 m, so every
sub-planetary Reach is scored against a floor that does not exist") is closed down to 1e6 m and
not up to where the ascending ladder starts. Raised as a QUESTION, not a fix — the boundary is
named deliberately, the module is held and unwired, and adding a rung there would move published
Reach scores, which the docstring says is a re-derivation with a before/after table rather than a
maintenance edit.
**Confidence:** read the guard and the table's first row.

### INFO — `is_descent` reports False where the two-state distinction elsewhere in the function is None
**Where:** src/descending_ladder.py:304 against :281.
**What:** on the normal path `is_descent` is `bool(from_m is not None and to_m < from_m)`, so a
call that supplies no `from_m` publishes `is_descent: False`; the input-error path at :281 uses
`None` for the same field to mean "not assessed".
**Why it is worth a line:** "no origin was given" and "the trajectory goes the other way" are
different facts and share an answer, which is the distinction this module's own sibling guards
(`mass_conserved_is_lawful: None`, ":281-288 … lawfulness was never assessed, not assessed and
failed") are built on. Nothing calls the function, so nothing is wrong today.
**Confidence:** read both returns.

---

## Cross-batch citations I could not close from inside this batch

* `endpoint.api_url` / `endpoint.MODE_RAW` (endpoint.py:275-278, 60-62) — read directly to settle
  the dandwiki finding; reported as a cross-batch read rather than assumed.
* `allsweep.VERIFIERS`' row shape (allsweep.py:216-241) — read directly to settle
  `_contracts_pass`'s `item[0], item[1]`.
* `silence.write_json` / `replace_retry` / `replace_if_unchanged` / `digest_of` — every module in
  this batch gates on their return values and I read those gates, but the functions themselves are
  another batch's to audit. Every claim above about a denied replace assumes only the documented
  contract (returns False, never raises).
* `verify_math.py` §19d is cited by completeness.py:605-610 as pinning the OLD "genuine absence →
  row dropped" behaviour against a ruling that changed it. That file is outside this batch and is
  explicitly not edited from here; flagged for the coordinator, as the comment itself asks.
