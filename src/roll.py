"""ROLL — the Acquisitions Roll, and the one place that answers "is this source in scope".

WHY THIS EXISTS. `SWEEP_ROLL.json` has carried a `status: "out-of-scope"` value since
2026-08-20, set on four sources by an owner decision. **Nothing in `src/` read it.** Not the
generator, not the cataloguer, not the pipeline. A source could be marked excluded and every
stage would go on working it exactly as before.

That is this project's signature failure in a new costume: a decision recorded somewhere nobody
reads is a decision that looks taken and is not. It is worse than the untaken version, because
the record makes everyone stop asking. `withdraw_chapters.py`'s header states the doctrine this
should have followed -- **MOVES, DOES NOT UNLINK** -- and the roll had the moving part without
the unlinking part.

So exclusion now has exactly one implementation, here, and the consumers ask it rather than each
deciding for themselves what a status string means.

WHAT EXCLUSION IS AND IS NOT. An out-of-scope source is **not deleted**. Its records stay on
disk, its evidence stays cached, its entries stay in the corpus index. It is removed from WORK:
nothing crawls it, nothing generates from it, nothing counts it as a coverage shortfall, and
nothing files work orders about how badly cited it is. Reversing it is editing one field.

AND THE TRAP THAT NEARLY ATE IT. `resync_roll.py` rebuilds `status` from the record files on
disk, and its rule is `"catalogued" if n else keep` -- so an out-of-scope source that still has
records (and all four of the 2026-08-25 exclusions have 933 entries between them) would be
silently promoted back to `catalogued` on the next resync. An exclusion that a routine
maintenance script can revert without anyone noticing is not an exclusion. `resync_roll` now
asks this module first, and a drill net attacks the path.
"""
import json
import os
import sys

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import silence  # noqa: E402

ROLL = os.path.join(HERE, "data", "SWEEP_ROLL.json")

# The status that means "a person decided this does not belong in the library". Only a person
# sets it; `resync_roll` and every other automated writer must preserve it, never assign it.
OUT_OF_SCOPE = "out-of-scope"


def load():
    """-> the roll as a list, or [] if unreadable."""
    try:
        with open(ROLL, encoding="utf-8") as f:
            d = json.load(f)
        return d if isinstance(d, list) else []
    except Exception:
        silence.note("roll.py:load")
        return []


def out_of_scope(rows=None):
    """-> {name: note} for every source a person has excluded.

    RETURNS THE REASON, NOT JUST THE NAME. An exclusion with no reason attached is how a real
    source gets quietly dropped and nobody can reconstruct why -- the same argument
    `suppressions.py` makes about detectors. Every caller that skips a source can therefore say
    what it is skipping and on whose authority.
    """
    out = {}
    for r in (rows if rows is not None else load()):
        if isinstance(r, dict) and r.get("status") == OUT_OF_SCOPE:
            out[r.get("name")] = r.get("note") or "excluded; no reason recorded"
    return out


def in_scope(name, rows=None):
    """-> True unless a person has excluded this source.

    FAILS OPEN, deliberately and against house habit. If the roll is unreadable this returns
    True and the source is worked. The alternative -- an unreadable roll silently excluding the
    ENTIRE library -- would be a fault that looks exactly like a completed run, which is the
    worse of the two failures by a wide margin. The roll being unreadable is itself detected
    and escalated elsewhere; it must not also become a mass deletion.
    """
    return name not in out_of_scope(rows)


def exclude(name, note, rows=None):
    """Mark a source out of scope, or correct the note on one already excluded. -> True if the
    roll was written.

    Takes a REQUIRED note. There is no way to call this without recording why. Raises if no row
    matches `name` -- a typo or a renamed source must not come back as the same silent False a
    no-op reason-correction used to return, because the one field this module exists to protect
    cannot be discarded without anyone noticing.

    SUPPLYING `rows` MEANS "WORK ON MY COPY", AND NOW MEANS IT ON THE WRITE TOO. It used to
    mean it only on the READ: the caller's rows were edited in memory and then landed on the
    module-level `ROLL` path regardless, so passing test data in order to AVOID touching the
    real roll was precisely the way to overwrite it. On 2026-08-26 a maintenance agent doing
    exactly that destroyed the live 216-source roll twice while verifying a fix to this
    function, and no backup of that file existed anywhere. It was rebuilt from
    `data/records/*.json` and two dated owner rulings; a backup now sits in `state/backups/`.

    A parameter whose obvious reading is the opposite of its behaviour is not a sharp edge, it
    is a trap, and this one was baited with the word every caller reaches for when being
    careful. `exclude()` has no callers anywhere in `src/` -- it is a hand-run curatorial tool
    -- so nothing depended on the old behaviour. With `rows` supplied the change is made in
    memory and the caller persists it; without it, the roll is loaded and landed exactly as
    before.
    """
    if not (note or "").strip():
        raise ValueError("an exclusion without a recorded reason is not an exclusion")
    caller_supplied = rows is not None
    rows = rows if caller_supplied else load()
    row = next((r for r in rows if isinstance(r, dict) and r.get("name") == name), None)
    if row is None:
        raise ValueError(f"no source named {name!r} on the roll -- exclude() cannot silently "
                          f"no-op on a typo or a renamed source")
    changed = row.get("status") != OUT_OF_SCOPE or row.get("note") != note
    row["status"] = OUT_OF_SCOPE
    row["note"] = note
    if not changed:
        return False
    if caller_supplied:
        # The caller's copy now holds the change; persisting it is the caller's job (see
        # SUPPLYING `rows` above), so True here means "your copy changed", not "it landed".
        return True
    # write_json's verdict was discarded here and `changed` returned regardless (order
    # 26be3dba65cf) -- a DENIED write reported a successful exclusion while the source stayed
    # in scope on disk, exactly the trap this module's own header exists to close. Return what
    # actually happened.
    return silence.write_json(ROLL, rows, indent=2, ensure_ascii=False)


def main():
    excluded = out_of_scope()
    rows = load()
    print("ACQUISITIONS ROLL — %d source(s), %d excluded" % (len(rows), len(excluded)))
    print("=" * 78)
    for name, why in sorted(excluded.items()):
        n = next((r.get("entry_count") or 0 for r in rows if r.get("name") == name), 0)
        print("  %-46s %6d entries" % ((name or "?")[:45], n))
        print("      %s" % why[:150])
    print("\nExcluded sources keep their records. They are removed from WORK, not from disk.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
