# Round-2 agent brief — panscriptum maintenance run #46

Read this fully. It is short because everything in it cost something to learn.

## Where you are

Repo: `C:\Users\imarl\panscriptum-library-kit`. **Always `cd` there first** — the shell resets to
`/c` between calls and `state/workorders.json` then reads as missing.

Python on this machine is `C:/Users/imarl/miniconda3/python.exe`. Not `py`, not `python3` — those
hit Norton's TLS interception. Prefix long runs with `PYTHONIOENCODING=utf-8`.

Read `CLAUDE.md` before you touch anything. Hard Rule -1 (the escalation chain and the four
properties of a safety), Hard Rule 0 (no caps, ever) and Hard Rule 2 (don't invent shelf
addresses) bind you.

## Your orders

You are given order ids. Read each one in full:

```bash
python -c "import json;d=json.load(open('state/workorders.json',encoding='utf-8'));import sys;print(json.dumps(d['ORDER_ID'],indent=1))"
```

The `evidence` field usually contains the measurement that opened the order and often the
proposed remedy. Read it before deciding the order is obvious.

## The standard for a fix here

This codebase's most-repeated finding is: **a check that cannot fail looks exactly like a check
that passed.** Three consequences that are not negotiable:

1. **Never make a red row green by weakening it.** If a check now asserts the wrong thing because
   the code legitimately changed, move the check *with* the change and make it **stricter** — more
   assertions, not fewer — and say in a comment why the old expectation is gone. Deleting a net,
   relaxing an expectation, or widening a tolerance to reach green is the forbidden act.
2. **Write down why.** Every non-trivial change carries a comment naming what was wrong, what was
   measured, and what was rejected. The plausible-wrong-answer belongs in the comment too, because
   somebody will propose it again next quarter. Match the surrounding density — this tree is heavily
   commented on purpose.
3. **Measure before you conclude.** Do not assert a behaviour you have not run. If you cannot
   measure it, say so and leave the order open with what you found.

## Rules that come from this shift's own failures

- **Do NOT run the full battery** (`python src/verify_math.py`). It takes 150s+ and several agents
  last round suspended waiting on it. Run targeted checks: import the module, exercise the function,
  print the result. I run the full battery and the drill at the end, once, on a settled tree.
- **If you change a function's SIGNATURE or its public behaviour, grep the whole tree for every
  caller and every stub — `src/drill.py` keeps pinned stubs of other modules' functions — and fix
  them all in the same edit.** This is precisely what raised a halt earlier today: one agent made
  `--by` mandatory on `escalation.clear()` while six drill nets still called it unsigned, and
  another widened `binding_health.canary` while drill's stub stayed pinned. Neither change was
  wrong. Neither agent looked outward.
- **Never pass prose through a shell.** Backticks in a heredoc get executed. Write resolutions to a
  file with the Write tool and pass `--how-file`, never `--how "..."`.
- **Probe litter.** If your change drives a deliberate failure path, it may write into the live
  `state/failures.json` through `silence.note` → `health.record`. Wrap deliberate failures in
  `drill._deliberately_failing`. Check before and after: if a failure class grew, you littered.
- **Stay inside your assigned modules.** If a correct fix needs a file outside your set, **do not
  make it.** Report the exact change needed and which order it belongs to. Cross-file debts are
  real and are mine to sequence.

## Closing an order

```bash
python src/workorders.py --resolve ORDER_ID --how-file /path/to/resolution.txt
```

The resolution is a written record another person reads months later. Say what was wrong, what you
changed, what you measured, and what you deliberately did not do. A one-line "fixed" is not a
resolution.

**If an order should NOT be executed** — it is blocked on the owner, it rests on a false premise,
or the remedy would be worse than the fault — say so and leave it open with your reasoning in your
report. Refusing with a reason is a valid outcome and is worth more than a bad fix.

## Report back

For each order: **CLOSED** (with a one-line summary of the change), **REFUSED** (with why), or
**INCOMPLETE / NO RESULT** (with what blocked you). Never claim a pass you did not observe. If you
ran out of time on something, say "INCOMPLETE" — an honest gap is cheap and a false green is not.
