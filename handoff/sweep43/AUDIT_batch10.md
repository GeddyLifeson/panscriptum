# Sweep43 batch10 audit

Files read in full: src/publish.py, src/rigor.py, src/build_terminal.py, src/ingest_doc.py,
src/canon_backup.py, src/feats_index.py, src/entity_match.py, src/halo.py.

No credential was found committed anywhere in this batch's files. All apparent "secret-shaped"
text in publish.py is detector regex source, not a leaked value.

Overall: this batch's files -- especially publish.py and canon_backup.py, the two named as
highest-stakes in the brief -- are extremely heavily hardened already. Nearly every line carries
a comment citing a specific prior incident/order that produced it. Most obvious failure shapes
(caps, discarded write verdicts, swallowed exceptions on the halt/mutation/ledger imports,
non-atomic writes) have already been repaired and are annotated as such. This audit therefore
reports a small number of genuinely new, verified findings rather than padding the list with
re-discoveries of what the file's own comments already document as fixed.

## src/publish.py

### MINOR -- `_AMBIGUOUS` is case-sensitive; the vendor patterns it gates are not
`src/publish.py:293`
```
_AMBIGUOUS = re.compile(r"^(sk-|[a-z+]+://)")
```
`_is_real_secret()` uses this regex to decide whether a `_SECRET` match needs the
placeholder/entropy check at all: "if not `_AMBIGUOUS.match(text)`: return True # structural
match -- shape alone is proof". But `_SECRET`'s own connection-string alternative is explicitly
case-insensitive (`(?i:postgres|postgresql|mysql|mongodb(?:\+srv)?|redis|amqp)://...`), while
`_AMBIGUOUS`'s scheme group `[a-z+]+://` has no `re.I` and only matches an all-lowercase scheme.

Verified directly:
```
>>> P._SECRET.search("Postgres://user:pass@host/db").group(0)
'Postgres://user:pass@'
>>> P._AMBIGUOUS.match("Postgres://user:pass@host/db")
None
>>> P._is_real_secret("Postgres://user:pass@host/db")
True
```
So a documentation placeholder such as `Postgres://user:pass@host/db` -- structurally identical
to the exact case (`postgres://user:pass@`) the module's own header names as the motivating
false-positive that `_PLACEHOLDER_CREDS`/entropy gating exists to clear -- is instead treated as
"shape alone is proof" and always redacted/flagged, skipping the placeholder check entirely,
purely because of capitalisation.

What actually happens: this fails toward over-blocking, never toward a leak (a real secret with
a capitalised scheme is still caught, more aggressively even). So it is not a hole in the guard
publish.py exists to provide. But `push()` treats any non-suppressed hit as `SECRET_IN_EXPORT`
and both raises `PUBLISH REFUSED` and calls `escalation.escalate(OWNER, ...)` -- and per this
project's own CLAUDE.md, an OWNER halt may only be lifted by a written ruling, never cleared on
"it seems fine now". A capitalised documentation example of a placeholder credential landing
anywhere in the exported tree (a HANDOFF.md example, a BUGS.md quote, a book's own in-fiction
"insert your Mongo connection string here" passage) would trigger a real OWNER-level halt for
nothing.

Remedy: compile `_AMBIGUOUS` with `re.I`, matching `_SECRET`'s own case-insensitivity for the
schemes it shares.

## src/canon_backup.py

### MINOR -- `restore()`'s final rename does not use the project's own Windows-lock-safe replace
`src/canon_backup.py:392`
```
os.replace(tmp, dest)
```
Every other writer in this module (`snapshot()`'s zip via `silence.replace_retry`, the manifest
via `silence.write_json`) is deliberately routed through `silence`'s retrying replace, because
this project has repeatedly documented (in this very module's own header, and throughout
publish.py) that Norton locks newly-written files on this machine and a bare rename can be
transiently `PermissionError`-denied. `restore()` -- the one function in this module that is the
actual disaster-recovery path -- stages its extraction correctly (opens the zip member before
truncating `dest`, per the fix two comments above this line) but lands it with a plain
`os.replace`, which raises rather than retrying on exactly the class of transient denial this
project's own `silence.replace_retry` docstring says "one such collision took an assay worker
down mid-batch."

What actually happens: a `--restore` invoked during a real recovery, at the moment Norton (or
any other reader) is scanning the file it was just written to, or holding the destination open,
raises an unhandled `PermissionError` out of `main()` instead of retrying for the ~1.5s that
would normally clear it. No corruption results (the write is staged to a `.part` file first and
`os.replace` either lands cleanly or raises before touching `dest`), so this fails safe rather
than silently -- but it is an inconsistency in a module whose whole subject, per its own header,
is "not trusting a write it has not confirmed," and it degrades reliability at the one moment
(an actual emergency restore) where a spurious failure is most costly to a person's confidence
in the tool.

Remedy: route the final `os.replace(tmp, dest)` through `silence.replace_retry(tmp, dest)` and
raise/report on `False`, matching every other write in this file.

## src/rigor.py

### MINOR / INFO -- `bradley_terry()`'s "unbounded MLE" refusal branch is dead code
`src/rigor.py:478` (`elif undefeated or winless:`)

```python
if not identified:
    ...
elif undefeated or winless:
    out["strengths"] = None
    out["refusal"] = (f"unbounded MLE: undefeated={undefeated} winless={winless}. ...")
```

`identified` is `len(comps) == 1 and len(comps[0]) == n`, i.e. the "beat" graph (edge a->b iff
`wins[(a,b)] > 0`) is a single strongly-connected component. For any node count n > 1, Ford's
condition (which this function itself invokes, correctly, in its docstring) means: a node with
zero losses (`observed[:, i].sum() == 0`, this function's own definition of `undefeated`) has
in-degree 0 and therefore cannot be reached from any other node, and a node with zero wins
(`winless`) has out-degree 0 and therefore cannot reach any other node -- either one makes the
graph NOT strongly connected. So `identified == True` mathematically implies
`undefeated == [] and winless == []` whenever n > 1 (and both lists are vacuously empty when
n <= 1 too, since no pair exists to record a win/loss against). I verified this is not merely a
proof but the actual runtime behaviour: 20,000 randomised tournament graphs (2-5 entrants, random
edges) produced zero cases where `identified` was True and `undefeated`/`winless` were non-empty
(see fixture used for this audit; reproducible via `rigor.bradley_terry`).

What actually happens: control can never reach the `elif` body. This does not create a gap in
the actual protection the function's docstring is proud of ("Both now REFUSE rather than
report") -- the `if not identified:` branch above it already refuses in every case that would
otherwise reach the unbounded-MLE branch, because non-strong-connectivity is a strictly weaker
(easier-to-trigger) condition than "has an undefeated/winless member." So the safety property
holds; the code just contains an unreachable branch presented as a second, independent check
when it is not one. This is exactly the "a check that cannot fail looks exactly like a check
that passed" shape this project explicitly watches for (CLAUDE.md, drill.py/liveness.py), so it
is worth recording even though the real invariant is not at risk.

Remedy: either collapse the two branches (the `elif` body is unreachable and can be removed, or
folded into a single combined message), or -- if the intent was for this to be an INDEPENDENT
second check rather than a logical corollary of the first -- restructure so it is actually
evaluated independently of `identified` (e.g. check `undefeated or winless` unconditionally,
before or regardless of the connectivity check). Owner/RUN judgment on which is intended;
functionally harmless either way today.

## src/feats_index.py

### MINOR -- a within-source catalogue-entry name collision is silently resolved, unlike the identical class of collision `load_index()` tracks
`src/feats_index.py:268`
```python
entries_by_norm.setdefault(_norm(e.get("name")), e)
```
in `feats_for_source()`. If a single source's catalogue carries two entries whose names fold to
the same `_norm()` key (the exact scenario `load_index()` a few dozen lines above tracks
explicitly as `faults["collided"]`, with a printed `collided_keys` list, precisely because "two
records folding onto one key is a real condition... What was wrong was that the loser vanished
from the total as though it had never been mined"), `setdefault` silently keeps whichever entry
was listed FIRST in `record["entries"]` and the second is dropped from `entries_by_norm` with no
count, no note, and no mention in `audit()`'s report.

What actually happens: this does not lose any FEATS (the entity's mined feats still attach, just
to whichever of the two catalogue entries "won" the collision), so it is narrower than the
`load_index` case it structurally mirrors -- no deed becomes unreachable. But the catalogue
`"entry"` metadata attached to a feats block (used downstream for the entity's own description
and magnitude) can be silently attributed to the wrong one of two same-named catalogue entries,
and unlike its sibling collision in `load_index()`, nothing here reports that it happened.

Remedy: track and surface entries-by-norm collisions the same way `load_index()` already does
for record collisions (a count and a named list, exposed through `audit()`), or confirm via
sampling that same-source name collisions do not currently occur in the corpus and leave this as
a documented non-issue if so.

## src/build_terminal.py, src/ingest_doc.py, src/halo.py, src/entity_match.py

No findings survived verification in these four files. Each was read in full.

- `build_terminal.py`: the HTML/JS templating is carefully disciplined about escaping
  catalogue-derived strings before they reach `innerHTML` (three prior fixes are cited inline --
  `shelfmark()`, `selectWorld()`'s `cat`, and the `f.*` rows -- and I checked every remaining
  `innerHTML=` sink against `esc()` and found none unescaped). The world "seed" (`w.s`) is spliced
  unescaped into a constructed URL's `href` attribute, but it is a deterministic numeric value
  produced by `navtree.py`'s `address_space.map_seed()`, not wiki/catalogue free text, so this is
  not the same class of hole as the ones already fixed; noting it here only so a future reader who
  widens what `s` can hold rechecks it. The `--help`-must-not-rebuild fix, the `<` neutralisation
  before splicing JSON into an inline `<script>`, and the atomic write with a checked verdict are
  all present and correct.
- `ingest_doc.py`: the resumable chunking, the two-writer-safe cursor/record writes, the
  ambiguous-record-match refusal, and the ISO-Rule-0-compliant uncapped description storage are
  all present and internally consistent with what their own comments claim.
- `halo.py`: a small, fixed, hand-authored roster (3 entities) with per-axis provenance tags and
  a checked atomic write. No cap or truncation applies to anything ordered/enumerated here.
- `entity_match.py`: proposes candidates only, never merges; the qualifier gate is absolute and
  correctly implemented (verified by re-reading `qualifier_compatible`/`split_qualifier` against
  the Wally-West continuity example the module's own header uses to justify the gate). No caps
  applied by default; `limit` is opt-in and marks `truncated` when used.

## Questions for the owner

None of the findings above required a curatorial judgment call rather than a fix -- all four are
either a one-line correction (case-insensitive regex, use the retrying replace) or a
"remove dead code vs. make it live" choice the owner/RUN handler should make (`rigor.py`
finding). No QUESTION-only items are being raised from this batch.
