# sweep42 batch 5 audit

Modules: src/cascade_bridge.py, src/ledger_guard.py, src/thread_integrity.py,
src/address_space.py, src/pick_model.py, src/hosts.py, src/tells.py, src/ledger.py,
src/lognames.py. All nine read in full.

Special focus per assignment: `cascade_bridge.ask()` returning `None` on ~half of live calls
with no diagnostic reaching the caller, and `selftest()` printing only `"live call -> FAILED"`.

---

## CONFIRMED DEFECTS

### 1. `cascade_bridge.py:1709-1726` — a successful cloud reply that fails JSON extraction is
reported to `served` as `"answered"`, then the function returns `None` anyway, with the raw
reply text discarded and nothing in `served` saying extraction failed. **This is almost
certainly the direct cause of the "ask() returns None on ~half of live calls with no
diagnostic" symptom.**

```python
if pinned:
    _clear(pinned.bucket)
answered = box["answered"]
if served is not None:
    served["outcome"] = "answered"          # <-- 1713, set BEFORE parsing is attempted
    served["label"] = box["answered"]
    served["model_id"] = box["answered_id"]
    served["bucket"] = _bucket_of(box["answered_id"] or box["answered"])
    served["failovers"] = list(box["failovers"])
finally:
    if pinned:
        _ROUTER.release(pinned)
got = _extract_json("".join(out))            # <-- 1721
if got is None:
    return None                              # <-- 1723: served["outcome"] is STILL "answered"
if isinstance(got, dict):
    got["_via"] = answered or "cascade"
return got
```

Why it's a defect: the module's own docstring (lines 17-30) says outright that cloud models
routinely "return perfectly well-formed JSON of entirely the wrong shape" — and more commonly,
wrap it in prose, omit the fence, or answer conversationally instead of with JSON at all
(`_extract_json`'s own docstring: "returns None and is treated as a failed call"). That is a
completely ordinary, expected outcome on this transport, not a rare edge case — exactly the
kind of failure that would show up on "roughly half of live calls." When it happens:

  * `served["outcome"]` says `"answered"` — actively wrong, since the call is being treated
    as a failure (the function returns `None`).
  * No `served["error"]` is ever set for this path.
  * The raw text the provider actually sent (`out`, accumulated in `pump()`) is discarded
    completely — never logged, never truncated-and-kept, never reaches `_metric()` (whose
    `out_chars` is computed as `0` when `got is None`, per `ask()`'s own row).

So any caller that inspects `served` to explain a `None` (the mechanism `prove()` and
`try_disabled()` already rely on) is told the call succeeded when it did not, and there is
categorically no way — not in `served`, not in the metrics ledger — to learn afterward what the
model actually replied with. This is a genuine "swallowed exception"-shaped bug: not a crash,
but a real failure silently laundered into a misleading success flag plus a bare `None`.

Confidence: high. The code is unambiguous and the mechanism matches the reported symptom
precisely.

### 2. `cascade_bridge.py:1750-1758` — `selftest()` never asks for the diagnostic it needs.

```python
got = ask("You extract feats. Copy sentences verbatim.",
          "ENTITY: Test\n\nHe lifted the boulder over his head and hurled it across the "
          "valley. He liked tea.\n\nReturn feats.", schema)
...
print(f"\nlive call -> {'OK via ' + str(_via) if got else 'FAILED'}")
```

`ask()`/`_ask_call()` accept a `served=` dict specifically so a caller can learn *why* a call
failed — outcome, error text, failovers, dispatched bucket (this is the exact mechanism
`prove()` and `try_disabled()` use to produce a reasoned verdict per bucket). `selftest()`,
this module's own health-check entry point, calls `ask()` without passing `served=`. Every
`served[...]=` write inside `_ask_call` is gated on `if served is not None`, so none of them
run, and `selftest()` has structurally no way to distinguish "no engine", "no bucket free",
"deadline", "auth failure", "transient throttle", "unrecognised provider error", or (per
finding 1) "answered but couldn't parse" — it can only ever print `FAILED`. This is exactly the
reported behaviour ("selftest() prints only 'live call -> FAILED' with no reason") and the fix
is available in the same file; it's simply not being used at the one call site that most needs
it.

Confidence: high.

### 3. `cascade_bridge.py:1310-1313` vs `1334-1336` — an unknown `pin` id returns without
updating `served`.

```python
if served is not None:
    served.clear()
    served.update({"asked": pin, "outcome": "not started", ...})   # 1312-1313
...
if pin:
    pinned = next((m for m in _ROUTER.models if m.id == pin), None)   # 1334
    if pinned is None:
        return None                                                    # 1336: outcome left "not started"
```

If a caller pins a model id that doesn't exist in `_ROUTER.models` (config drift, a typo, a
model removed from config since the id was captured), the function returns `None` but
`served["outcome"]` is left at the placeholder `"not started"` rather than something like "pin
not found in router config." A caller reading `served` for an explanation is told nothing
happened, which is misleading in the same direction as finding 1, just for a rarer trigger.
Both `prove()` and `try_disabled()` construct `pin` from `m.id` drawn from `_ROUTER.models`
itself so they can't hit this in practice, but it's a real gap in the diagnostic contract this
module is trying to provide, and a future caller (or a race with a live config reload) could hit
it.

Confidence: medium — real gap, low probability of triggering under current callers.

### 4. `ledger_guard.py:274-279` — `seal()`'s outer write fails silently, no `silence.note`.

```python
try:
    os.makedirs(os.path.dirname(CHAIN), exist_ok=True)
    if not silence.append_line(CHAIN, json.dumps(rec, ensure_ascii=False)):
        return None
except Exception:
    return None
```

Every other failure path in this same function (and this same file) calls `silence.note(...)`
before returning/continuing on a caught exception — e.g. the per-ledger snapshot loop a few
lines below this (`except Exception: silence.note("ledger_guard.py:snapshot")`), and the whole
module's stated philosophy is that a swallow must be countable (`silence.py` exists "so
swallows are countable"). This one bare `except Exception: return None` records nothing: if
`os.makedirs` or `json.dumps(rec)` raises (not just `append_line` returning falsy), the caller
(`assert_intact()`) does still surface a `LedgerViolation` because it checks `seal() is None`,
so the failure isn't fully hidden — but *why* the seal failed (permissions? disk full? a
non-serialisable value smuggled into `rec`?) is lost with no trace in `state/failures.json`,
unlike every comparable failure elsewhere in this file.

Confidence: medium — the caller does fail loudly, but the diagnostic is dropped, which is
exactly the "silence must be countable" property the rest of the file goes out of its way to
uphold.

### 5. `cascade_bridge.py:1760` — `[:400]` truncation of a printed string in `selftest()`.

```python
print(json.dumps({k: v for k, v in got.items() if k != '_via'}, indent=1)[:400])
```

A literal `[:N]` slice on a string about to be printed, with no "...and N more characters"
notice. Per house Hard Rule 0 this is called out by name as the forbidden shape
("`[:N]` on a printed/written string ... is a FINDING"). This module's own comment eleven
lines above (1737-1743) fixed exactly this pattern for `ready[:12]` a few lines earlier in the
same function, with an explicit citation of Hard Rule 0 — this second occurrence, one path
further down in the same function, was not caught by that same pass.

Confidence: medium — real, letter-of-the-rule violation, but low real-world stakes: it only
clips the debug preview of `selftest()`'s own dummy test payload (a self-test schema about a
boulder-throwing entity named "Test"), not any catalogue content, and the underlying `got`
value returned from the call is not itself truncated anywhere.

### 6. `address_space.py:452-453` — truncated preview list and truncated name in `main()`.

```python
for d, a in list(addrs.items())[:6]:
    print(f"     {d[:44]:<46}{shelfmark(a)}")
```

`[:6]` caps the printed "CATALOGUED WORLDS, ADDRESSED" preview to six rows with no "and N more"
note, and `d[:44]` truncates each designation string. The underlying data is not lost — the full
`addrs` dict is written uncapped to `data/SHELFMARKS.json` immediately after — so this is
console-preview-only, but it is a literal `[:N]` on a printed string with no count disclosed,
the exact shape Hard Rule 0 names.

Confidence: medium — same category as finding 5: real per the letter of the rule, low stakes
because the actual generated data (SHELFMARKS.json) is complete.

### 7. `hosts.py:310` — truncated source name in `--discover` report.

```python
print("  %-40s + %s" % (str(src)[:39], ", ".join(hs)))
```

`[:39]` truncates the printed source name for column alignment; the host list itself (`hs`) is
joined in full, uncapped. This file is otherwise unusually careful about exactly this failure
mode — its own `work()` function has an extended comment (lines 161-164) explicitly removing a
`[:40]` cap on a roster because "this roster is the evidence a candidate host is SCORED
against... the CLAUDE.md canonical violation" — so it's notable that a sibling `[:39]` survives
in the same file's own report printer. Two sources sharing a 39-character prefix would print
identically in this one report line (their full names are still recoverable via `--show`).

Confidence: low-medium — cosmetic column formatting, not a data-dropping cap; flagged mainly
because this exact file has already treated the identical pattern as a defect once.

---

## QUESTIONS (may be deliberate design — not proposed as fixes)

### Q1. `cascade_bridge.py` — truncation of provider error text to 200/300 chars throughout
(`record_unrecognised`'s `text[:300]`, `provider_error()`'s `[:300]`, `served["error"]`'s
`[:300]`, `_r = ...[:200]` on failover reasons, `reason[:300]` in `prove()`). These are `[:N]`
slices on strings that get printed/written, which is the literal shape Hard Rule 0 names. I am
NOT filing these as findings because, unlike findings 5-7 above, the file gives extensive,
specific reasoning for these exact cuts (e.g. the `record_unrecognised` docstring: "ENOUGH TEXT
TO CLASSIFY IT" — 300 chars of a provider's error sentence is ample to classify a throttle vs.
an auth failure vs. a billing complaint, unlike a roster/character-list truncation, which drops
irrecoverable content). Whether 300/200 is the right ceiling for a provider error message is a
judgment call the codebase has clearly already made deliberately, not an oversight — but it's
worth the owner's eyes given how central these ledgers are to diagnosing exactly the "ask()
returns None" problem this batch was asked to focus on.

### Q2. `cascade_bridge.py:1349-1358` (widen path) and `_alive()`/`dead_forever()` — the whole
provider-classification apparatus (`permanent_refusal`, `named_transient`, `client_rejection`,
etc.) is a long, hand-maintained vocabulary of substrings and regexes matched against free-text
provider error bodies. This is not a defect I can point at a line for, but it is structurally
the kind of "check that can silently stop matching" the module's own comments repeatedly warn
about (e.g. the extensive history of `_DEAD_WORDS` growing after each newly-discovered escape).
Given the reported symptom (calls silently failing at scale), it's worth the owner confirming
whether the *current* live error text landscape (as of 2026-09-02) has drifted past this
vocabulary again, the way it's demonstrably done at least four times before per the file's own
comments. Not filing as a defect since the pattern (grow the vocabulary as new escapes are
found) is the file's explicit, working methodology, not a bug.

### Q3. `ledger.py` and `lognames.py` — no defects found. Both are small, self-contained
(currency-conversion arithmetic and a filename registry respectively) and I found nothing to
question either.

---

## Coverage record

Recorded via `sweep_plan.record('run42', [...9 files...], batch=5)` — see command below, run
after this file was written.
