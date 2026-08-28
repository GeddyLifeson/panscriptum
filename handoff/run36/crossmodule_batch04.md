# run #36, batch 4 — cross-module change requests

Batch 4 owns `health.py`, `identity.py`, `ledger_guard.py`, `overnight.py`, `scope.py`. The change
below is required to finish an order but lands in a module another agent holds this shift, so it is
written here rather than applied.

---

## `src/chain.py` — `adjudicate_mutuals()` must not read "the probe never ran" as "no epoch"

**Order:** `70563ce550eb` (MAJOR). **Half of it is already done** in `identity.py`; this is the
half that makes it take effect. Until this lands, the defect is still live in production.

**What changed on my side.** `identity.epoch_of()` now separates the two answers it used to
collapse into one empty string:

* the model read the sentence and found no marker → `""`, unchanged, a real answer;
* nothing ever asked — transport down, `read.ensure_transport` failing, a reply that will not
  parse → a `silence.note("identity.py:epoch-unprobed")`, and, with the new **additive**
  `strict=True` keyword, `identity.ProbeUnavailable` instead of a fabricated `""`.

The default is unchanged, so no caller breaks and nothing is forced. But the default is also the
old behaviour, which means `chain.py` is still being told "this sentence dates nothing" every time
the probe fails.

**Why it matters here specifically.** `chain.py:422` dates both sides of every mutual pair and
then, at `chain.py:433`, prints `"neither sentence dates itself"` and counts the pair as a
**genuine disagreement in the record** — which is a substantive claim that goes on to the
Bradley-Terry fit. With no transport at all, every mutual pair would be reported that way,
unanimously, and the run would look clean. That is a check that cannot fail.

**The change**, at `chain.py:422` inside the `for (w, loser) in mutual:` loop:

```python
        try:
            ea, eb = ID.epoch_of(sa, strict=True), ID.epoch_of(sb, strict=True)
        except ID.ProbeUnavailable:
            # UNPROBED IS NOT UNDATED. The pair is left standing either way, but it must not be
            # counted as a genuine disagreement: nothing asked, so nothing was found out.
            unprobed += 1
            silence.note("chain.py:epoch-unprobed")
            print(f"   NOT ADJUDICATED: {w} vs {loser} -- the epoch probe did not run, so this "
                  f"pair is left standing UNJUDGED rather than recorded as a disagreement")
            continue
```

with `unprobed = 0` initialised beside `split = kept = 0`, and the closing line widened so the
count cannot hide inside `kept`:

```python
    print(f"   {split} split by epoch, {kept} recorded as genuine disagreement"
          + (f", {unprobed} NOT ADJUDICATED -- the probe did not run" if unprobed else ""))
```

`chain.py` already imports `silence`; if it does not, drop that one line rather than adding an
import for it.

**Verified on my side** (execution, not reading): with `_ask` stubbed to return `None`,
`epoch_of(s)` still returns `''` and `epoch_of(s, strict=True)` raises `ProbeUnavailable`; with a
stub returning `{"epoch": "", "explicit": false}` — the model genuinely finding no marker —
`strict=True` returns `''` and does **not** raise, which is the distinction the whole order is
about. An unparseable reply raises as well.
