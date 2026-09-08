# OWNER DECISION DIGEST — BATCH 09

Verified against the live tree 2026-09-07. Every claim below was re-measured or re-read from the
current executable line; no order was judged on its own filed text. Nothing was edited.

**16 live, 4 dead. 2 reroute to RUN/LOCAL.**
Dead and off the desk: `b1f561587b19`, `7ebac78494e8`, `33000660ddac`, `732f68f640cf`.

---

### 572918512dbc  [SESSION] [MAJOR]  — Refusal-marker layer refuses real articles on the API transport
STILL LIVE: yes — `feats.py:249-252` is unchanged (`for m in _REFUSAL_MARKERS: if m in low: return False`),
there is no `parsed=` kwarg, and only `wiki=False` drops a layer (the third, not this one). Re-counted
the whole of `data/feats` today: 276,218 files, **exactly 119** refusal-marker records, same tally as
filed (rate limit 101, temporarily unavailable 13, access denied 3, captcha 2) on the same eight hosts.
`data/ENDPOINTS.json` still reads api 321 / dead 2,991 / raw 1.
QUESTION:   Should the marker layer be gated on the transport, so it stops running on the one path where a block page cannot arrive?
OPTIONS:    (a) gate on transport (`parsed=True` skips markers; `binding_health.py:494,661` keep the default) and re-mine the 119 (b) leave as is (c) gate on transport but do not re-mine
RECOMMEND:  (a) — **reroute to RUN/LOCAL, no ruling needed.** This is not a judgment call: the remedy is fully specified, it strengthens no guard and weakens none (the length floor and wiki-markup layer stay, and the ambiguous markers keep working on `fetch_raw`/`fetch_html`), and the 119 records are false refusals of 41KB articles. Feats totals will rise; that is the defect leaving.
COST IF WRONG: Nothing breaks either way — but leaving it means 119 real articles stay on disk permanently recorded as "we were blocked", which is the project's signature failure inverted.
UNBLOCKS:   none
THEME:      stale cached data

---

### a3d518d078c3  [SESSION] [MAJOR]  — Forty-four sources stranded by a done-keys gate the todo filter fixed
STILL LIVE: yes — `pipeline.py:1541` still reads `if src in done_keys: continue`, `:1613` still
`done_keys.append(src)`, no `unassayable` field is written anywhere, and `retry_synthesis.stranded_sources()`
still selects on `if rec.get("synthesis"): continue`. Re-measured today: done.synthesis 186 keys,
**49 records with no ceiling_entity, 44 of them already in done_keys, 0 reachable by the rescue tool** —
identical to the filed figures. Largest stranded: Ghost Recon 808 entries, FFXIV/Eorzea 685, Splinter Cell 468, Overwatch 259.
QUESTION:   Should those 44 sources be re-nominated, and on what condition should phase 1 ever re-admit a source it has already answered?
OPTIONS:    (a) record the negative verdict explicitly (`unassayable` + the cast digest it was reached against) and re-admit when the cast has GROWN — phase 2's `batch_settled` rule, applied to phase 1 (b) widen `stranded_sources()` to select on `ceiling_entity` instead of the block's presence (c) both (d) leave; accept the 44 as permanently answered
RECOMMEND:  (c) — (a) is the durable fix and matches the ruling this same file already made at `pipeline.py:1906-1924`; (b) is one line and rescues the existing 44 without waiting for (a). Do NOT simply drop the done_keys test: that re-nominates every genuinely feat-less source on every pass, and the pool is at 199,938/200,000 tokens right now.
COST IF WRONG: Picking (d) leaves Overwatch and 43 others shelved on a verdict reached before their casts existed. Picking a naive drop-the-gate burns the whole daily quota re-asking questions already honestly answered.
UNBLOCKS:   none
THEME:      stale cached data

---

### b1f561587b19  [OWNER] [MAJOR]  — Extra-entry penalty in the prose gate: fixed, verified twice
STILL LIVE: **NO** — fixed 2026-08-28. `prose_gate.py:289` now reads
`required += extra * (len(REQUIRED_PER_ENTRY) + 1)`, directly beneath the comment recording that
appending to `missing` alone was never a price. `SECTION_LOSS_FLOOR = 0.0`, so `assert_block_complete`
raises on any `frac < 1.0`.
**I re-ran the order's own repro against the live module.** Filed result: `present 15 required 15
frac 1.0`, no refusal. Today: `present 15 required 20 frac 0.7500` → **`ProseRefused` raised**:
"the block kept 15 of 20 required entry sections (75%)". The gate is strictly stronger than when
the order was written. The instrument gap is closed too: alongside the message-only net at
`drill.py:1373-1376`, a behaviour net was added under order 212e3096edfc — the comment at
`drill.py:1377` names the exact defeat ("THE BEHAVIOUR, NOT THE MESSAGE") — and
`_the_shortfall_counts_agree_with_their_nouns` at `drill.py:1442` now checks the quantities.
QUESTION:   None remaining. Close it.
OPTIONS:    (a) close as fixed, citing `prose_gate.py:289` and the live repro above
RECOMMEND:  (a) — this is the order two agents split on; the disagreement is settled by execution, not by reading. Padding is no longer free. **Change nothing here.** The prose gate is the safety whose removal cost 145 unauthorised chapters; the only correct action on this order is to close it and leave line 289 alone.
COST IF WRONG: None. Closing costs nothing. Re-opening it to "fix" a gate that already refuses would be the review cycle that weakens it.
UNBLOCKS:   none
THEME:      guard vacuity

---

### 642a95fe9f3c  [OWNER] [MAJOR]  — A missing tier is published as charted tier zero
STILL LIVE: yes, and the code says so itself. `address_space.py` `fit()` ends
`return 0 if v is None else int(v)`, under a comment that reads "THE `None` -> 0 ARM IS DELIBERATELY
UNCHANGED … has its own open order (642a95fe9f3c)". The compensating note at `:482` is still
`if not tiers:` — whole-file only. Callers `pipeline.py:2469` and `profile.py:186` still pass through.
`UNADDRESSED = None` at `:141` is still referenced by nothing.
**The blast radius shrank.** Re-measured: TIERS.json now holds 208 rows, **65** carry at least one
None (was 109 of 209), and only **16 of 1,016** worldseed designations are affected (was reported as
8 of 30 sources). Demonstrated live: `A Plethora of Paladins` → `Ω › H0 › X0 › Mt.0 › Mv.34 …`,
indistinguishable from a charted zero. Note `Magic: The Gathering` has `metaverse: None` and prints
`Mt.0` while being genuinely charted everywhere else.
QUESTION:   Should an uncharted tier print as a marked blank rather than as zero?
OPTIONS:    (a) print a marker (`?` or `—`) for a None tier and keep 0 for a charted zero (b) leave; accept 16 shelfmarks reading as surveys they are not (c) refuse to address a source with any None tier at all
RECOMMEND:  (a) — the vocabulary already exists unused (`UNADDRESSED` at `:141`, and TIERS rows now carry a `hyperverse_type` field), and 16 rows is a small, safe change. (c) is too strong: it would pull those 16 worlds off the shelf entirely.
COST IF WRONG: Choosing (b) leaves the module doing the one thing its own charter forbids — "the Custodes considered guessing a form of lying" — on 16 published shelfmarks.
UNBLOCKS:   60dc7c624c06 (same TIERS.json ruling; answer them in one sitting)
THEME:      address honesty

---

### 95f817b752ac  [OWNER] [INFO]  — Fabrication standard reports red when its reader is merely down
STILL LIVE: yes — `standards.py:1146-1158` still emits `fab is not None and fab <= MAX_FABRICATION`
with "UNMEASURED -- the reader has logged no progress line yet", while the sibling at `:874-879`
still routes the same absent job to `_dropped.append("corpus-read-standards")`. Confirmed the
decisive factor: `"sentences that survive the verbatim check"` is **not** in `foreman.REMEDIES`
(`foreman.py:1137-1172`), so `foreman.py:1631-1633` falls through to `log["owner"].append(...)`
every round.
QUESTION:   Is a HIGH row in the owner's file every round the right price for never again letting this standard read green by absence?
OPTIONS:    (a) keep red-when-unmeasured; close with a note that it is intentional (b) route only the `not read` case to `_dropped` and keep red for the three genuine instrument faults (no `dropped` key, kept+dropped==0, unparseable line)
RECOMMEND:  (b) — the tipping factor is that the sibling block's own stated reason applies *more* here, not less: this standard has no remedy at all, so its red row cannot even dispatch a cure, it can only occupy the owner's page. Reading (a)'s real fear — silence reading as health — is fully answered by (b), because the three instrument-fault cases still go red and `_dropped` is itself reported by the aggregate standard.
COST IF WRONG: Picking (b) wrongly means a genuinely dead reader shows as "dropped" rather than red for one supervisor lap. Picking (a) means a recurring HIGH row for a normal state — the alarm-that-always-sounds this project calls furniture, and the exact complaint `standards.py:1830` already makes about `include_self`.
UNBLOCKS:   none
THEME:      alarm routing

---

### d411f780d347  [OWNER] [MINOR]  — coverage_map() has no callers and the CLI bypasses it
STILL LIVE: yes — `sweep_plan.py:606` `def coverage_map()`, with exactly one other hit tree-wide
(`:633`, a docstring mention that explicitly says something else is "Deliberately NOT derived from
`coverage_map()`"). `main()` at `:986-988` still opens `COVERAGE` directly.
QUESTION:   Should `--coverage` report from the authoritative shards-first view, or should the unused function go?
OPTIONS:    (a) point `main()`'s `--coverage` branch at `coverage_map()` (b) delete `coverage_map()` and let `--coverage` keep reading the aggregate file (c) leave both
RECOMMEND:  (a) — `--coverage` is documented at `:20` as "what the last sweep actually covered", and it currently answers from the file `record()`'s own docstring at `:139` says "nothing draws a conclusion from". One call site changes; the function was written for exactly this question.
COST IF WRONG: (b) discards a correct implementation and leaves `--coverage` permanently answering from the convenience view. (c) keeps a named authoritative view that nothing consults.
UNBLOCKS:   4e92365b54f6, 707fefc17465, c72431056a14 — see the standing-policy note at the foot of this file
THEME:      dead code

---

### 7ebac78494e8  [OWNER] [MAJOR]  — Four cloud buckets: the DNS diagnosis is disproven
STILL LIVE: **NO, as filed.** The order's whole finding is "a resolver fault on THIS MACHINE".
I resolved all four hosts just now: `api.deepinfra.com` → 38.101.151.30, `router.huggingface.co` →
13.249.141.67, `api.cerebras.ai` → 104.18.10.146, `llm.chutes.ai` → 34.111.142.178. DNS works.
The stored errors have also changed under the order: `state/cascade_scratch.db` `bucket_state` now
holds **`curl: (7) Failed to connect … after 7-120ms`**, not the filed `curl: (6) Could not resolve
host`. All four last spoke at 1787757900 = **2026-08-26, 12.4 days ago**, and have not been probed
since. `nvidia:free` and `mistral:free` carry the same curl (7), so it is six buckets, not four.
QUESTION:   The resolver is fine — so should those six buckets be re-probed, and is a sub-120ms connect refusal a local block rather than a provider fault?
OPTIONS:    (a) re-probe the six; if they answer, the outage is over and the pool gains six buckets (b) re-probe, and if they still fail at connect, file a fresh order against the local firewall/TLS layer (this machine's known Norton constraint), not against the providers (c) leave them dark
RECOMMEND:  (b) — a connect that fails in 7ms is a local refusal, not a network timeout, which fits this machine's documented TLS/firewall interception. Either way `cascade_bridge.py:543-549`'s protection must stand: a fault on this machine still must never cost a bench.
COST IF WRONG: Leaving them dark keeps six buckets absent from the binding constraint while the rest of the pool sits at 199,938/200,000. Benching them would convert a local fault into six permanently disabled providers and hide the cause.
UNBLOCKS:   partially 88982cef258d (six recovered buckets change the quota picture)
THEME:      cloud pool

---

### 4e92365b54f6  [OWNER] [MINOR]  — build_address() is dead and returns the colliding pre-volume form
STILL LIVE: yes — `address.py:363` `def build_address(...)` still ends
`addr = f"{spine}/{volume}"` from a bare `spine_code_for`, and the only other occurrence tree-wide
is its own `__main__` demo at `:477`. `manifest_builder.py:506-512` still builds `volume_code`
first and `:532` still uses it, which is the repair that removed "303 duplicate addresses across
916 of 3,502 jobs".
QUESTION:   Retire the module's named address builder, or route it through the volume map?
OPTIONS:    (a) retire it (and its `__main__` demo) (b) route it through `volume_code` so the public name is correct (c) leave
RECOMMEND:  (a) — nothing calls it, and the honest address needs a per-Series volume map that `address.py` does not hold; (b) would either duplicate `manifest_builder`'s map or take a new argument, which is a new function, not a repair. (c) leaves a trap: the module's obvious entry point hands out the exact collision the manifest path was fixed to avoid.
COST IF WRONG: (a) wrongly means re-writing eight lines if a caller ever appears. (c) means the next person reaching for `address.build_address` reintroduces 303 duplicate addresses.
UNBLOCKS:   settled together with d411f780d347, 707fefc17465, c72431056a14
THEME:      dead code

---

### 707fefc17465  [OWNER] [MAJOR]  — render.py, all nine cosmology view tiers, reachable only by hand
STILL LIVE: yes — the only mention of `render` outside the module is still a **comment** at
`build_terminal.py:87`. No entry in `lognames.OWNER`, no job in `overnight.py`. `drill.py:81-83`
independently confirms it: render is one of ten modules "imported and named by nothing else in the
tree", and names this order by id. `render.py:363` states in its own words that "nothing in `src/`
or `registry_terminal/` currently reads `output/views/*.svg`" — I checked `registry_terminal/`, and
that is true. `output/views/` holds 5 SVGs from a past manual run.
QUESTION:   Wire the cosmology views into a cycle, or retire the module and write the decision down?
OPTIONS:    (a) wire it: add a `render.py` step to `publish.py`'s cycle or the registry terminal so the top five tiers can actually be looked at (b) retire the module deliberately, with the decision recorded (c) leave it reachable by hand only
RECOMMEND:  (a) — the module's stated purpose is real and unmet: five cosmology tiers "had addresses and no way to look at them", and 60dc7c624c06 below is a question about exactly those tiers that a picture would help answer. Retiring it discards working code that closes a gap nothing else closes.
COST IF WRONG: (a) costs one cycle step and a few SVG writes per run. (c) is the status quo — a documented gap that reads as closed and is not.
UNBLOCKS:   settled together with d411f780d347, 4e92365b54f6, c72431056a14
THEME:      dead code

---

### a34f10a87483  [OWNER] [INFO]  — A drill net that halts the library over the wording of a comment
STILL LIVE: yes — `drill.py:6858` still ends `return not named and "THERE IS NO PAID LANE" in text`,
and the sentence it requires is a single comment at `cascade_bridge.py:232`. The structural half is
sound and does the real work. A breached net escalates to OWNER and halts the library.
QUESTION:   Should the library be able to stop itself because someone reflowed a comment?
OPTIONS:    (a) keep both halves; close with a note that `cascade_bridge.py:232` is not to be edited (b) keep the structural half as the net; move the sentence requirement to `policy.py`'s rule table or a `verify_math` section, where a miss costs a work order instead of the park
RECOMMEND:  (b) — this weakens nothing. The owner's no-paid-lane ruling stays pinned in code and stays checked; only the *penalty* for a wording change moves from "halt the library" to "file a finding". What tips it is this file's own standing line at `drill.py:598-599`: "A net that goes red when a guard is improved teaches people to stop improving guards" — and orders 7cc460706efe and 8ee268ce32cc are two prior cases where a text-pinned net did exactly that.
COST IF WRONG: (b) wrongly means the ruling sentence could be deleted and the library keeps running until the next `verify_math` pass names it. (a) means a paragraph reflow in `cascade_bridge.py` parks the library until a person rules on it.
UNBLOCKS:   none
THEME:      alarm routing

---

### 98f18453deaf  [OWNER] [INFO]  — Synthesis blob bypasses the origin-entry filter in grounding
STILL LIVE: yes as a question, with **zero live impact**. `grounding.py` still appends
`syn.rationale + syn.evidence` outside the `_ORIGIN` loop, and the docstring five lines above still
says a source with no origin-bearing entry "comes back UNGROUNDED by the honest route". I ran the
classifier over all 216 records today: **0 sources have `origin_entries == 0` and a grounding**
(was 0 of 210 when filed). 187 records now carry a non-empty synthesis rationale, so the exposure
is growing, not shrinking.
QUESTION:   Does a synthesis rationale count as an attested cosmogony?
OPTIONS:    (a) yes — add a clause to the docstring saying the synthesis block is exempt from `_ORIGIN` and why (b) no — put an `_ORIGIN.search` on the synthesis blob too
RECOMMEND:  (a) — a synthesis rationale is the most considered origin account in a record, and the `_ORIGIN` filter exists to stop *incidental entry* vocabulary outvoting the creation account ("recurring character" nearly made eternal recurrence the commonest cosmology), a risk a deliberate synthesis rationale does not carry. What tips it: the filter's stated purpose does not apply to this field, so exempting it is faithful to the method, and the honest repair is to say so where the method is stated.
COST IF WRONG: Either way the change is one line and nothing on disk moves today. Choosing (a) wrongly means a source with no origin entries could one day be classified from a synthesis blob alone — visible in the record, because `origin_entries: 0` sits right beside the verdict.
UNBLOCKS:   none
THEME:      doc/code drift

---

### 2239a87c57f5  [OWNER] [MAJOR]  — Router discards the provider's own retry-after and redispatches
STILL LIVE: yes — `cascade_bridge.py:1669-1676` still reads
`elif pinned and (exhausted or named_transient(err)): … pass`, under "Named here, deliberately not
benched". There is **no `retry_after` parsing anywhere in the file** (grepped). The provider is
still handing us the number: `bucket_state` right now carries "Please try again in 15m8.496s",
"5m44.736s", "37m17.328s" against groq, updated 11 minutes ago.
QUESTION:   Should a parsed retry-after become a bench duration, and is a per-DAY quota exhaustion the same thing as a per-minute throttle?
OPTIONS:    (a) leave as is; the cost is one wasted call per rotation (b) honour the parsed retry-after as a bench duration WITHOUT writing to the unrecognised-failure ledger (c) treat a stated per-DAY exhaustion as permanent-for-the-day, distinct from a per-minute throttle
RECOMMEND:  (b) — it keeps the order's stated rationale fully intact (a throttle is not a mystery and still must not reach the unrecognised ledger) while fixing the different question, which is routing. What tips it is the measurement: 3 of 6 probes dispatched into a bucket that had just said "retry in 499s", so the pool reported ~50% success while other buckets were answering. (c) is the stronger form of the same idea and can follow later; (b) subsumes it, because a TPD retry-after is already tens of minutes.
COST IF WRONG: (b) wrongly means a bucket sits idle for a stated cooldown that the provider would have lifted early. (a) means every rotation burns a call on a bucket that already told us not to call. Note: `drill.py`'s net "a provider on cooldown is kept, not axed" pins the CURRENT behaviour — moving it must be deliberate, not incidental.
UNBLOCKS:   informs 88982cef258d
THEME:      cloud pool

---

### 33000660ddac  [SESSION] [MAJOR]  — feats --roll exit code: fixed, counters now reach rc
STILL LIVE: **NO** — fixed under order f4f4b9d5f935 (run40 sweep). `feats.py:1900` now binds the
result (`done = roll(...)`) and `:1921-1934` carry three named failing conditions to `return 1`:
the `WIKI_HOSTS.json` write denied (`_HOSTS_DENIED`), `n == 0`, and `errored >= n`. Each prints
"ROLL FAILED, exiting nonzero so the supervisor can see it: …", so the rc and the console agree.
The order's core claim — "returns 0 unconditionally, the return value is not even bound" — is
false against the current line.
QUESTION:   Nothing required. One residual worth a line, not a ruling: `_UNCACHED`, `_CAP_BOUND` and `_STALE_GATE` are still printed but still do not reach the rc, which is the one clause of the filed remedy the fixer did not take.
OPTIONS:    (a) close as fixed (b) close as fixed and file a MINOR follow-up for `sum(_UNCACHED.values()) > 0 → rc 1`
RECOMMEND:  (b) — the fault is dead and the order should come off the desk; the `_UNCACHED` clause is a separate, smaller question ("a roll that mined everything and cached nothing is a failed run") and deserves its own order rather than keeping a MAJOR open.
COST IF WRONG: None. `overnight.py:1624` already gets a truthful rc for the three conditions that matter most.
UNBLOCKS:   none
THEME:      exit codes

---

### 481ef92af785  [OWNER] [MAJOR]  — Invented scope ceilings still clamping every published Magnitude
STILL LIVE: yes — **but the blocker has changed, and only the owner's half is left.** The
"can NEVER be re-probed" mechanism is **fixed**: `scope.py` `build()` no longer skips on `h not in
out`; it now selects `if force or _stamp(out.get(h)) < PROBE_VERSION`, with an explicit comment
naming the old skip as the fault. So the rows are reachable now.
The data is untouched. Measured on disk today: `data/SCOPE.json` holds 155 rows, `PROBE_VERSION = 2`,
and **146 rows carry a ceiling with no `probe_version` stamp at all** — i.e. the entire pre-fix file
is re-probe-eligible and **zero rows have ever been re-probed**. The named worst cases are intact:
`root.fandom.com` M7 on 2 universe mentions and `rosariovampire.fandom.com` M7 on 2, against
`MIN_MENTIONS = 10`. `magnitude.host_ceiling()` (`magnitude.py:1721`) still reads them straight off
disk as authoritative clamps.
QUESTION:   Run the re-probe, accepting that published Magnitudes will move?
OPTIONS:    (a) run `scope.build()` and let all 146 pre-v2 rows re-derive (b) re-probe only the rows whose ceiling was invented below the mention floor (c) leave; keep today's published numbers stable
RECOMMEND:  (a) — the code fix already decided the method; what is left is only consent to the numbers moving, and they should move: a source clamped at M7 on two mentions is constraining every entity under it on evidence the current parser would refuse outright. (b) is not meaningfully safer, because the pre-v2 rows carry no mention counts to filter on.
COST IF WRONG: (a) changes published Magnitudes across up to 146 hosts in one pass — irreversible without a snapshot, so take one first. (c) leaves invented ceilings permanently authoritative over the library's headline numbers.
UNBLOCKS:   none
THEME:      stale cached data

---

### 1e83e387cfc1  [SESSION] [MINOR]  — Spawn-site anti-vacuity floor has 14 of headroom
STILL LIVE: yes — `verify_math.py:5003-5005` still reads
`check("the guard is actually finding the spawn sites …", _guarded20e >= 20, True)`. I replicated
the scan today: **34 guarded, 0 unguarded, 0 os.system/os.popen/os.startfile, 0 unparsed**, across
13 modules that import subprocess. Headroom is 14 — fourteen spawn sites could stop being recognised
without the row moving, and a genuine drop would report a count, never a name. A partial hardening
did land beside it (`:5006`, "every module was readable by the console-window scan"), and its own
note concedes "The >=20 floor does not cover this".
QUESTION:   Should the anti-vacuity row reconcile against the declared set instead of a hardcoded floor?
OPTIONS:    (a) reconcile: every module in `src/` that imports subprocess must contribute at least one recognised spawn, and the check names any module that imports subprocess and yields none (b) leave the floor
RECOMMEND:  (a) — **reroute to RUN/LOCAL, no ruling needed.** This is the identical instrument `verify_math.py:4828-4839` already retired for the standards roster under order ba7b55d6465f, for the identical reason; the argument transfers unchanged and the pattern already exists in this file at SECTION 20q. Nothing is weakened: the floor is replaced by a strictly stronger reconciliation.
COST IF WRONG: Nothing breaks. Leaving it means the no-console-window guarantee — a hard machine-wide rule here — rests on a check with 14 of slack that would never name the file that went blind.
UNBLOCKS:   none
THEME:      guard vacuity

---

### c72431056a14  [SESSION] [INFO]  — Mutation token env var documents a safety nothing implements
STILL LIVE: yes — exactly three occurrences tree-wide: `mutate.py:131` (defined), `:349` (written),
`:358` (popped). No reader anywhere in `src/` or `handoff/`.
**One fact that settles the choice, and was not in the order:** the distinction the comment at
`:346-348` describes *is* implemented — through the lock file, not the env var. `mutate.active()`
(`mutate.py:197`) reads `state/MUTATION_ACTIVE.json`, and it is consulted widely: `publish.py:1339,
1349, 1388, 1624, 1791` and pinned by drill nets at `drill.py:3848, 12222-12301`. The lock record
even carries `"sandboxed": True` (`mutate.py:261`). So the env var is a redundant second channel
that no one has ever read, not a missing safety.
QUESTION:   Delete the three lines, or wire a reader?
OPTIONS:    (a) delete `_TOKEN_ENV`, the two `os.environ` lines and the paragraph describing them (b) wire a reader (c) leave
RECOMMEND:  (a) — the mechanism is already served by `mutate.active()`, so wiring a reader would duplicate a working interlock, and a constant documenting a safety nothing implements is precisely the shape this module exists to find. This is a one-word answer, not an investigation. Removing it removes no guard: `mutate.active()` is untouched.
COST IF WRONG: None operationally. If a future sandboxed gate ever needs the token *without* filesystem access to the lock, it would be re-added — eight lines.
UNBLOCKS:   settled together with d411f780d347, 4e92365b54f6, 707fefc17465
THEME:      dead code

---

### 88982cef258d  [OWNER] [MINOR]  — Free cloud tiers are spent; recorded so nobody re-diagnoses it
STILL LIVE: yes, and worse than filed — measured 11 minutes ago in `state/cascade_scratch.db`.
`groq:qwen/qwen3.6-27b` 198,192/200,000 TPD; `groq:openai/gpt-oss-120b` 199,938/200,000;
`groq:openai/gpt-oss-20b` 198,540/200,000; `openrouter:free` daily free-models limit exceeded;
three Gemini buckets over quota; `zai:free` "Insufficient balance"; `cohere:free` trial 1,000
calls/month reached; `sambanova:free` high demand; `ollama:qwen3:8b` HTTP 503 max pending requests.
QUESTION:   Nothing about money — but two buckets are failing on **credentials, not quota**, and that is free to fix: `cloudflare:free` HTTP 401 "Authentication error" and `hyperbolic:free` HTTP 401 "Could not validate credentials", both dark since 2026-08-25.
OPTIONS:    (a) close as recorded; the remedy is money or waiting and the standing answer to money is no (b) close as recorded, but re-issue the two free API keys behind the 401s
RECOMMEND:  (b) — (a) is right about the quota half and needs no further thought. The 401s are a different fault hiding inside a quota order: two buckets are absent from the binding constraint for want of a key, which costs nothing. Worth ten minutes of the owner's time given the pool is the constraint.
COST IF WRONG: None. Re-keying two free tiers cannot make the pool worse; leaving them means two permanently dark buckets misfiled as "spent".
UNBLOCKS:   none
THEME:      cloud pool

---

### aad11acb1183  [OWNER] [MAJOR]  — The dashboard refuses to start while a halt stands
STILL LIVE: yes structurally, not firing today. `dashboard.py:1160` still calls
`_ESC.assert_clear(os.path.basename(__file__))` in `main()`, before `argparse` — so `--once` cannot
even parse. No read-only exemption exists in `escalation.assert_clear`. `dashboard.py:784-786`
still declares "THE HALT IS THE HEADLINE … rendered first, loud, and with the reason".
No halt stands right now (`state/HALT.json` code DRILL_BREACH, `cleared: true`, raised 2026-09-05
and lifted the same shift), so the fault is latent — it bites only in the one circumstance the
instrument exists for. I confirmed the drill net at `drill.py:3847-3849` that pins
`escalation.assert_clear` to `main()` is scoped to **publish.py**, not dashboard, so a change here
moves no net.
QUESTION:   Should the read-only instrument be exempt from the plant-wide interlock?
OPTIONS:    (a) exempt the dashboard: render the halt as the headline instead of refusing to start (b) exempt only `--once` (the JSON read path), keep the refusal for the served daemon (c) accept that a standing halt is readable only via `escalation.py --status`
RECOMMEND:  (a) — the interlock exists so a job cannot do WORK while the library is halted; the dashboard does no work, it only reports, and reporting the halt is the whole point. The honest form is to call `escalation.status()` and render, not `assert_clear()` and die. This removes no guard: every job that acts still calls `assert_clear`, and the dashboard would be *more* informative under a halt, not less.
COST IF WRONG: (a) wrongly means one read-only page runs during a halt. (c) means the next standing halt is invisible in the place designed to shout about it the moment anything restarts the daemon on 8777.
UNBLOCKS:   none
THEME:      alarm routing

---

### 60dc7c624c06  [OWNER] [MAJOR]  — TIERS.json contradicts the address prose on all four tier counts
STILL LIVE: yes, and it has widened. The prose still appears three times
(`address_space.py:124, 158-159, 222`): "168 multiverses -> 8 metaverses -> 6 xenoverses ->
1 hyperverse, strictly nested, zero containment violations".
Measured against `data/TIERS.json` today (208 rows): hyperverse distinct **{0, 3, 5}** → derived
population **6**; xenoverse {0,1,2} → 3; metaverse {0..5} → 6; multiverse 0..142 → **143**.
`_tier_counts()` returns `{hyperverse: 6, xenoverse: 3, metaverse: 6, multiverse: 143}` — **all
four claimed numbers are now wrong**, not just the hyperverse. Demonstrated live: `Magic: The
Gathering — all planes` prints `Ω › H5 › X1 › …`, a hyperverse index the prose says cannot exist.
QUESTION:   Is the dendrogram cut wrong, or is the prose describing a chart that has since been re-cut?
OPTIONS:    (a) the data is authoritative: rewrite the three prose sites to state the measured counts, and have them read from `_tier_counts()` rather than be hardcoded (b) the prose is the charter: re-cut the dendrogram to produce one hyperverse and re-derive every shelfmark (c) leave the contradiction standing
RECOMMEND:  (a) — the prose was written against a chart that no longer exists (the filed measurement was "4 distinct values 2-5"; it is now {0,3,5}), so it is a stale caption, not a charter. Critically, (a) changes **no published address**: `assign()` reads TIERS.json, not the prose. (b) moves address arithmetic under every shelfmark already published and should not be taken to fix a sentence.
COST IF WRONG: (a) wrongly means the omniverse is described as having six hyperverses when the intended cosmology has one — a documentation error, correctable. (b) invalidates every shelfmark in `data/SHELFMARKS.json`. (c) leaves the module's own prose contradicting its own output.
UNBLOCKS:   642a95fe9f3c (same TIERS.json sitting; the `_tier_counts()` read is the same edit)
THEME:      address honesty

---

### 732f68f640cf  [OWNER] [MINOR]  — coverage --show-best cap: disclosed and ruled on in code
STILL LIVE: **NO.** The complaint was that the cap is "silent" and "undisclosed", so "the two halves
of one report answer different questions". Both halves are answered at `coverage.py:295-300`, which
now prints either "BEST COVERED (showing 10 of N; N-10 more not shown, --show-best to raise)" or
"BEST COVERED (N, all shown)" — the cap announces itself every run. `--show-best 0` now means all
of them (order 89fc2eaf23f1), so the uncapped request the CLI could not previously make now exists.
The remaining asymmetry is no longer undisclosed but *ruled on in writing*, at `coverage.py:314-316`:
"The default stays 10 because this list is the good news and the WORST COVERED list above it is
where the work is; the difference is that asking for everything is now possible and says so."
QUESTION:   None. The recorded ruling can be overturned in one line if the owner disagrees with it, but nothing is hidden and nothing is unstated.
OPTIONS:    (a) close as resolved (b) change the default to None for symmetry
RECOMMEND:  (a) — a disclosed default with a written rationale is not a defect, and the smallest item on this desk should leave it. If the owner wants symmetry anyway it is a one-word answer and a one-token edit.
COST IF WRONG: None either way; it is a display default on a report both halves of which now state their own truncation.
UNBLOCKS:   none
THEME:      report symmetry

---

## Standing policy that would close four of these at once

`d411f780d347`, `4e92365b54f6`, `707fefc17465` and `c72431056a14` are one question wearing four
hats: **what happens to a module or function in `src/` that nothing calls?** Each is individually
small; together they are a policy. `drill.py:81-83` records that ten modules in `src/` are imported
and named by nothing else in the tree (chord_field, descending_ladder, halo, handbuilt,
module_index, pantheon, render, scale_theories, wh40k, zfighters), so answering the policy once
would also settle six orders not in this batch.

Suggested policy, offered for a yes/no rather than a discussion: *an uncalled public function is
retired unless a named consumer is wired in the same shift; an uncalled whole module is wired into
a cycle or retired, and the decision is written down.* Under it: d411f780d347 → wire,
707fefc17465 → wire, 4e92365b54f6 → retire, c72431056a14 → retire.

## Nothing in this batch asks for a safety to be weakened

The three orders that touch guards all move in the same direction — `b1f561587b19` is closed
because the prose gate got *stronger*; `1e83e387cfc1` replaces a slack floor with a reconciliation;
`a34f10a87483` keeps the paid-lane check and only moves the penalty for a comment edit off "halt the
library". `prose_enabled` and `step4_enabled` are not touched by any order here and were not read,
tested, or reasoned about as candidates for change.
