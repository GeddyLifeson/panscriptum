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


def mutate(apply, attempts=8, path=None):
    """Land a change to the roll through a COMPARE-AND-SWAP. -> (landed, why).

    ATOMIC WAS NOT ENOUGH, AND SWEEP_ROLL.json WAS THE LAST SHARED FILE STILL RELYING ON IT
    (order f818a77293fc). Every writer of this file landed it with `silence.write_json`, which
    closes the TORN-FILE hazard and has nothing to say about STALENESS. The cataloguers read the
    whole roll at startup, spend a run parsing folders or fetching wikis while mutating
    `entry_count`/`status` on their own rows in memory, and then land the ENTIRE document. Any
    row another process wrote inside that window is overwritten by this process's older copy of
    it. Nothing fails, nothing tears, the file is always complete and consistent -- it is simply
    one or more rows behind. That is the m42 lost update this project has already closed for
    ENDPOINTS.json (endpoint._save), SOURCE_PAGES.json (endpoint.register), scout._mutate,
    workorders._mutate and runguard._land_claim, and endpoint.py's own docstring names the fault
    in capitals: ATOMIC WAS NOT ENOUGH.

    The cost here is specific: the default work selection everywhere in this pipeline is
    `entry_count == 0`, so a lost row means a source is either silently re-catalogued from
    scratch or silently never picked up again.

    `apply(rows) -> rows` is called on a FRESHLY READ copy on every attempt, and on a refusal the
    file is re-read and the mutation RE-APPLIED rather than the same bytes retried. That is
    exactly right for this file because the roll merge is key-wise by source name: re-applying
    to the winner's copy leaves the other writer's rows standing and puts ours beside them.
    `apply` may mutate in place and return None.

    AN UNREADABLE OR ABSENT ROLL IS NOT WRITTEN OVER. `data/SWEEP_ROLL.json` is one of
    canon_backup's four non-derivable canonical files and was destroyed TWICE on 2026-08-26;
    "we could not read it" is not evidence of what it should contain, and a mutation applied to
    a `[]` we invented would publish that invention as canon. Same distinction endpoint.register
    draws: absent and unreadable are different facts, and neither licenses a write here.

    `path` DEFAULTS TO THIS MODULE'S ROLL AND EVERY CALLER PASSES ITS OWN. Each writer module
    carries its own `ROLL` constant, and the test harnesses repoint THAT constant to a temp file
    in order to avoid touching the live roll -- so a helper that silently wrote to `roll.ROLL`
    instead would turn "sandbox this test" into "overwrite data/SWEEP_ROLL.json", which is
    precisely how the live 216-source roll was destroyed twice on 2026-08-26 (see `exclude`'s
    docstring). The parameter exists so the caller's own constant is always the file written.
    """
    import threading
    import time
    path = ROLL if path is None else path
    last_why = "not attempted"
    for attempt in range(attempts):
        # The digest is taken BEFORE the read, so anything that lands between the two makes the
        # swap fail closed rather than pass on a copy that is already behind.
        digest = silence.digest_of(path)
        try:
            with open(path, encoding="utf-8") as f:
                rows = json.load(f)
        except Exception:
            silence.note("roll.py:mutate-unreadable")
            return False, ("%s could not be read, so nothing was written to it -- the roll is "
                           "canonical and not derivable from a failed read"
                           % os.path.basename(path))
        if not isinstance(rows, list):
            silence.note("roll.py:mutate-nonlist")
            return False, "SWEEP_ROLL.json is not a list; refusing to overwrite it"
        out = apply(rows)
        if out is None:
            out = rows
        # pid + thread + attempt in the temp name, for the reason silence.write_json carries
        # them: a fixed `.tmp` suffix is a second collision between the very writers this
        # function exists to keep from overwriting each other.
        tmp = "%s.%d.%d.%d.tmp" % (path, os.getpid(), threading.get_ident(), attempt)
        try:
            with open(tmp, "w", encoding="utf-8") as f:
                json.dump(out, f, indent=2, ensure_ascii=False)
        except Exception:
            silence.note("roll.py:mutate-tmp")
            return False, "could not stage the new roll next to %s" % os.path.basename(path)
        landed, why = silence.replace_if_unchanged(tmp, path, digest)
        if landed:
            return True, ""
        last_why = why
        try:
            os.remove(tmp)
        except OSError:
            silence.note("roll.py:mutate-tmp-cleanup")
        time.sleep(0.05 * (attempt + 1))
    silence.note("roll.py:mutate-contended")
    return False, last_why


def update_rows(changes, attempts=8, path=None):
    """Apply `{source_name: {field: value, ...}}` to the roll, key-wise. -> (landed, why).

    The shape every cataloguer needs: it knows which SOURCES it changed and what it changed
    about them, and nothing about the rest of the file. Passing the fields rather than the whole
    document is what makes the re-apply in `mutate` correct -- a row this writer never touched is
    never carried backwards by it.

    A name with no row in the freshly-read roll is NOT invented. The roll's rows are created by a
    person adding a source, never by a cataloguer, so an unmatched name means the row was renamed
    or removed under this run, and the honest response is to name it rather than to resurrect a
    row from a stale copy. It is reported in `why` and the rest of the changes still land.

    `path` is passed straight to `mutate` -- see there for why every caller supplies its own.
    """
    missed = []

    def _apply(rows):
        seen = set()
        for row in rows:
            ch = changes.get(row.get("name"))
            if ch:
                row.update(ch)
                seen.add(row.get("name"))
        missed[:] = sorted(n for n in changes if n not in seen)
        return rows

    landed, why = mutate(_apply, attempts=attempts, path=path)
    if landed and missed:
        silence.note("roll.py:update-rows-unmatched")
        return True, ("no roll row is named %s any more, so %d change(s) had nowhere to land"
                      % (", ".join(repr(n) for n in missed), len(missed)))
    return landed, why


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
    #
    # DELIBERATELY NOT ON `mutate()` ABOVE, and this is the one roll writer that is not (order
    # f818a77293fc). The lost update `mutate` closes is a LONG window -- a cataloguer reads the
    # roll, works for minutes, lands a stale whole document. This function loads and lands in
    # the same breath and has no callers anywhere in src/: it is a hand-run curatorial act by
    # one person. Moving it is still the right end state, but the live battery pins this exact
    # call as a source string (handoff/run35/checks_L4.py, order b3da16ddfe64) and rewriting a
    # check to fit a refactor is a shift-level decision, not a maintenance one.
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
