# Cross-module needs — LOCAL batch 5

## 918da0e4b88b (tiers.py:248) — stale line-number tag in `silence.note()`, module not owned

Order text (from `handoff/sweep33/AUDIT_batch09.md`, finding 2) named five stale
line-number-style `silence.note()` tags across `magnitude.py`, `tiers.py`, `scout.py` (x1) and
`profile.py` (x2). Re-verified against the current source (not the order's stale line numbers)
before touching anything, since none of these four files are in my owned set
(`corpus_db.py`, `onomast.py`, `resonance.py`, `style_audit.py`):

```
grep -n 'silence.note("magnitude.py:151")' src/magnitude.py   -> no match, already descriptive
grep -n 'silence.note("scout.py:241")'      src/scout.py       -> no match, already descriptive
grep -n 'silence.note("profile.py:131")'    src/profile.py     -> no match, already descriptive
grep -n 'silence.note("profile.py:135")'    src/profile.py     -> no match, already descriptive
grep -n 'silence.note("tiers.py:245")'      src/tiers.py       -> src/tiers.py:248
```

**Four of the five are already fixed** — `magnitude.py`, `scout.py` and both `profile.py` sites
now carry descriptive tags (`magnitude.py:pool_ready`, `magnitude.py:_ask-cascade`,
`scout.py:verify-http`, `profile.py:genres-unreadable`, `profile.py:tiers-unreadable`, etc.),
presumably closed by whichever agent owns those modules. **One remains**:

`src/tiers.py:248` — `silence.note("tiers.py:245")`, currently 3 lines below the number it
names (was 2 lines off at sweep33 time; it has drifted further since). Whoever owns `tiers.py`
should replace it with a descriptive tag in the project's own convention, e.g.
`"tiers.py:<what-the-guard-is>"`, matching the fix already applied to its four siblings.

I do not own `tiers.py` and did not edit it. Leaving order `918da0e4b88b` OPEN rather than
closing it — 4/5 sites are resolved but the fifth is not, and the fix belongs to `tiers.py`'s
owner.
