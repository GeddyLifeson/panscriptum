"""LEDGER GUARD — the relay's own integrity, checked rather than trusted.

WHY THE LEDGERS NEEDED NETS AND HAD NONE.

Every maintenance run is a fresh session with no memory of the last one. What survives is four
files -- `HANDOFF.md`, `BUGS.md`, `NEXT_STEPS.md`, `MAINTENANCE.md` -- and they are the ONLY
thing carrying continuity. That makes them the highest-leverage target in the project and, until
2026-08-25, the least defended: `HANDOFF.md` was append-only *by convention*, `NEXT_STEPS.md` is
overwritten wholesale every run, and nothing anywhere parsed `BUGS.md` for structure.

The failure mode is specific and nasty. A run that truncates `HANDOFF.md`, or writes a
`NEXT_STEPS.md` that is empty or garbled, does not crash anything. It poisons **every future
run**, silently, because the next run reads it as fact and has nothing to compare it against.
That is the exact profile the owner's rule selects for: a failure that is silent AND outlives the
run that caused it.

THREE INDEPENDENT SYSTEMS, per the standing doctrine:

  1. APPEND-ONLY, ENFORCED. `HANDOFF.md` is history. New content must CONTAIN the old, verbatim.
     Not "be longer than" -- longer is what a truncation plus a large new entry looks like.
  2. STRUCTURE, PARSED. `BUGS.md` must have its three sections, and no bug id may appear in both
     Open and Resolved. That second check has been run BY HAND at the end of every session in
     this project's history, which is a good sign it should not have been a manual step.
  3. SUBSTANCE, MEASURED. A ledger that exists but says nothing is indistinguishable from a
     healthy one to any check that only asks "does the file parse". Each has a floor.

These are deliberately cheap -- string containment and a section split, no model, no network --
because a guard that costs anything gets skipped on the run that most needed it.
"""
import json
import os
import re
import sys
import threading

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
# This module is imported by `publish.push` -> `assert_intact` from processes whose sys.path may
# not carry src/, so it is put there rather than assumed -- the same two lines every other
# module in this directory opens with. `silence` is needed by seal() below, which used to
# swallow its one failure with a bare `pass` and therefore left no trace in state/failures.json.
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import silence                                                          # noqa: E402

# `handoff/HANDOFF.md` JOINED THIS LIST ON 2026-08-31 (order 42db308cc85d, run40 sweep).
#
# The four root-level ledgers were guarded and this one was not, while the project's own file
# headers describe it as the durable carrier of "the project's deep engineering history,
# doctrine, and architecture" -- the reference book to the root HANDOFF.md's run journal. That
# is a ledger by every definition this module uses, and `pipeline.py`'s own commentary records
# it ALREADY LOSING 629 LINES to exactly the truncation class this file exists to prevent.
# None of the three mechanisms here could see it, and `publish.py` copies the whole `handoff/`
# directory into the public export tree with no integrity check on the way.
#
# The module docstring's claim that four files "are the ONLY thing carrying continuity" was a
# false completeness claim -- the most expensive kind in this project, because it reads as
# coverage. Five now, and the fifth is the one with the history in it.
APPEND_ONLY = ("HANDOFF.md", "handoff/HANDOFF.md")
# Floors, set well below the current sizes so ordinary editing never trips them. They exist to
# catch a TRUNCATION -- a file that lost its history -- not to police how much a run writes.
# handoff/HANDOFF.md is ~58 KB today; 20000 is the same proportional slack the root ledger gets.
MIN_BYTES = {"HANDOFF.md": 20000, "BUGS.md": 8000, "NEXT_STEPS.md": 3000,
             "MAINTENANCE.md": 5000, "handoff/HANDOFF.md": 20000}
REQUIRED_SECTIONS = {"BUGS.md": ("## Open", "## Resolved")}


class LedgerViolation(RuntimeError):
    """A ledger was about to lose something. Raised before the write, never after."""


def _read(name):
    p = os.path.join(HERE, name)
    try:
        with open(p, encoding="utf-8") as f:
            return f.read()
    except FileNotFoundError:
        return None


def _one_insertion(old, new):
    """Is `new` exactly `old` with ONE contiguous block inserted at one point? -> bool.

    NEWEST ON TOP IS THIS FILE'S DOCUMENTED CONVENTION, and the substring test alone could not
    express it. `HANDOFF.md` says so in its own header and `MAINTENANCE.md:143` repeats it:
    "dated run journal, newest on top". A legitimate run therefore writes
    `header + new entry + everything that was under the header before` -- which loses NOTHING,
    and which `old in new` REJECTS, because the old text is no longer contiguous once an entry
    is spliced in behind the header. Measured 2026-08-27 (run #36) against the live 473,848-byte
    file: the real append pattern was rejected, a bottom-append accepted. A guard that refuses
    the only writing pattern its file actually uses cannot be wired to a writer, which is a large
    part of why it never was.

    So: longest common prefix plus longest common suffix must cover the whole of `old`. That is
    precisely "nothing removed, one block inserted at a single point" -- true for a bottom
    append (insert at the end), a top append (insert at the start), and the newest-on-top
    append-after-header this project uses. It is NOT true of a truncation, a reordering, or an
    edit that removes a line from the middle, all of which still fail.
    """
    if new is None or len(new) < len(old):
        return False
    n = len(old)
    p = 0
    while p < n and old[p] == new[p]:
        p += 1
    if p >= n:
        return True
    s = 0
    while s < n - p and old[n - 1 - s] == new[len(new) - 1 - s]:
        s += 1
    return p + s >= n


def check_append_only(name, new_text, old=None):
    """-> (ok, reason). Would this write LOSE history?

    Containment, not length. A run that truncated the file and then appended a long entry
    produces a LONGER file, so a size comparison would wave it through -- and that is precisely
    the shape a botched overwrite takes.

    `old` is an ADDITIVE keyword with the previous behaviour as its default (read the live file):
    `check_since_snapshot()` compares a live ledger against the last SEALED copy of itself rather
    than against itself, and that is the same question asked from the other side of the write.
    """
    if name not in APPEND_ONLY:
        return True, "%s is not append-only" % name
    old = _read(name) if old is None else old
    if old is None:
        return True, "%s does not exist yet" % name
    if old.strip() and not (old in (new_text or "") or _one_insertion(old, new_text)):
        return False, ("%s is append-only and this write does not contain the existing file. "
                       "History is the whole value of a relay ledger; a run that cannot see the "
                       "last run's entry is a run starting from nothing." % name)
    return True, "history preserved"


def check_structure(name, text=None):
    """-> (ok, [problems]). Sections present, floors met, and no bug filed in two places."""
    text = text if text is not None else _read(name)
    problems = []
    if text is None:
        return False, ["%s is missing entirely" % name]
    floor = MIN_BYTES.get(name)
    if floor and len(text.encode("utf-8")) < floor:
        problems.append("%s is %d bytes, below the %d-byte floor — a ledger this short has lost "
                        "something" % (name, len(text.encode("utf-8")), floor))
    for sec in REQUIRED_SECTIONS.get(name, ()):
        if sec not in text:
            problems.append("%s has no '%s' section" % (name, sec))
    if name == "BUGS.md" and "## Open" in text and "## Resolved" in text:
        # SECTIONS BOUNDED BY THE ORDER THEY ARE FOUND IN, not by an assumed Open-then-Resolved
        # layout. The earlier version sliced `text[i:j]` on that assumption; reorder the file --
        # a human edit, a template change -- and `i > j` makes Python answer the slice with `""`,
        # so `op` is empty, the intersection is empty, and the one check that exists to catch a
        # bug filed in two places passes even when every Resolved bug is still sitting in Open.
        # A check that cannot fail reads exactly like a check that passed.
        marks = sorted((text.find(s), s) for s in ("## Open", "## Resolved", "## Watching")
                       if text.find(s) >= 0)
        span = {}
        for n, (at, sec) in enumerate(marks):
            span[sec] = text[at:(marks[n + 1][0] if n + 1 < len(marks) else len(text))]
        op, res = span["## Open"], span["## Resolved"]
        both = sorted(set(re.findall(r"\[([Mm]\d+)\]", op))
                      & set(re.findall(r"\[([Mm]\d+)\]", res)))
        if both:
            problems.append("these bug ids are in BOTH Open and Resolved: %s — a resolved bug "
                            "left in Open is how the Open section rots" % ", ".join(both))
    return (not problems), problems


def check_all():
    """-> {name: [problems]} across every ledger. Empty dict is the good state."""
    out = {}
    for name in list(MIN_BYTES):
        ok, problems = check_structure(name)
        if not ok:
            out[name] = problems
    return out


CHAIN = os.path.join(HERE, "state", "ledger_chain.jsonl")
# The last SEALED copy of every append-only ledger. The chain records digests, and a digest can
# only ever answer "did this change" -- never "did the change keep the history", which is the
# one question `check_append_only` was written to answer and the one thing a hash cannot be
# asked. One file per append-only ledger, overwritten each seal.
SNAPSHOT_DIR = os.path.join(HERE, "state", "ledger_snapshot")

# How much of an append-only ledger may disappear between two seals before it is a TRUNCATION
# rather than an edit. A person fixing a typo in an old entry, or re-wrapping a paragraph,
# removes a handful of lines out of thousands; a run that lost its history removes most of them.
# Set high enough that ordinary hand-editing cannot reach it, because this refuses a PUSH and a
# safety that stops the operator doing ordinary work is a safety that gets deleted.
MAX_LOST_FRACTION = 0.05


def _digest(text):
    import hashlib
    return hashlib.sha256((text or "").encode("utf-8")).hexdigest()[:32]


def seal():
    """Append a hash-chained record of the ledgers' current state. -> the new link.

    THE THIRD MECHANISM, and it answers what the other two cannot.

    `check_append_only` proves a PROPOSED write keeps history -- but only if it is called, and
    only by a writer that chose to call it. (Run #36 gave it the one caller this project can
    actually give it: `check_since_snapshot()` below asks the same question AFTER the write, from
    `assert_intact()`, because nothing in `src/` writes HANDOFF.md and a Python function cannot
    gate a person's editor.) `check_structure` proves the file parses. Neither
    can answer the question a relay actually needs: *did anything change these files between the
    last run and this one, and if so what?* A run that edits HANDOFF.md directly, or a crash
    mid-write, or an edit made by hand between runs, leaves both of them satisfied.

    A hash chain answers it. Each link records the digest of every ledger plus the digest of the
    PREVIOUS link, so the sequence is tamper-evident: change any past link and every link after
    it stops verifying. Borrowed from the audit-trail pattern used for autonomous-agent logs
    (Asqav), minus the signing -- there is one writer here and no adversary to authenticate
    against, so the chain-of-hashes property is the whole value and the PKI would be theatre.

    Deliberately a SEPARATE file rather than hashes embedded in the markdown: the ledgers are
    prose a person reads and an agent appends to, and threading hashes through them would make
    every ordinary edit look like tampering.
    """
    prev = None
    links = read_chain()
    if links:
        prev = links[-1].get("self")
    import time
    # ONE READ PER LEDGER, AND THE UNITS SAY WHAT THEY ARE (order 016fcf397818).
    #
    # This was `{"digest": _digest(_read(n) or ""), "bytes": len((_read(n) or ""))}`, which had
    # two faults in one expression. It read every ledger from DISK TWICE, so a file edited
    # between the two reads got a digest of one state and a size of another -- a link that
    # describes nothing that ever existed. And `len()` on text decoded as UTF-8 counts
    # CHARACTERS, which it then stored under the key `bytes` and `verify_chain()` printed to an
    # operator as bytes, in the same CLI run where `check_structure` measures the real thing
    # (`len(text.encode("utf-8"))`) against MIN_BYTES. Two numbers, two units, one label, not
    # comparable -- and these ledgers carry em dashes and ellipses, so the two genuinely differ.
    #
    # THE NAME WAS RIGHT AND THE MEASUREMENT WAS WRONG, so the measurement changed: `bytes` now
    # means bytes, matching MIN_BYTES and every other size in this file. `chars` rides along
    # because the chain already holds 948 legacy links whose `bytes` is really a character
    # count, and the SHRANK test compares a link against its PREDECESSOR -- without a
    # same-unit number to compare, the one boundary link between the old records and the new
    # would have been structurally unable to fire (UTF-8 bytes >= characters always, so
    # `now < was` cannot hold there), a silent one-link hole in a truncation detector. With
    # `chars` recorded, verify_chain() compares that boundary chars-to-chars and keeps its
    # coverage. Nothing already written is touched: the chain is append-only evidence.
    _texts = {n: (_read(n) or "") for n in sorted(MIN_BYTES)}
    rec = {"at": time.time(), "prev": prev,
           "ledgers": {n: {"digest": _digest(t),
                           "bytes": len(t.encode("utf-8")),
                           "chars": len(t)}
                       for n, t in sorted(_texts.items())}}
    rec["self"] = _digest(json.dumps({k: rec[k] for k in ("at", "prev", "ledgers")},
                                     sort_keys=True))
    # THROUGH `silence.append_line`, NOT A BARE `open(CHAIN, "a")` (order f7b611d107cb,
    # sweep41-batch10). This was the exact pattern measured on 2026-09-01 losing 704 of 3,200
    # rows: `O_APPEND` makes the seek-to-end and the write one operation on POSIX, and the
    # Windows CRT implements it as a seek FOLLOWED BY a write, so two processes seek to the same
    # end offset and the second lands ON the first. `silence.append_line` was written that same
    # day to close it -- an OS-level lock on a sidecar plus `O_BINARY` -- and this call site, in
    # the module whose own commentary quotes that measurement, was still using the old shape.
    #
    # AND THE LOSS MODE HERE IS THE ONE `verify_chain()` CANNOT SEE. A torn line is caught: the
    # read side now reports unparseable lines as problems. But a cleanly LOST WHOLE LINK is not,
    # because the surviving link's `prev` still points at its true predecessor -- the chain
    # simply has one fewer link and hangs together perfectly. That is a checker unable to fail on
    # precisely the failure this file documents, in the ledger that exists to prove the records
    # were not altered.
    #
    # NOT HYPOTHETICAL: `publish.py` deliberately allows two writers at once (the `--push --loop`
    # daemon and a hand-run one-shot, exempted from the singleton claim), and each calls
    # `assert_intact()`, which seals.
    try:
        os.makedirs(os.path.dirname(CHAIN), exist_ok=True)
        if not silence.append_line(CHAIN, json.dumps(rec, ensure_ascii=False)):
            return None
    except Exception:
        return None
    # AND KEEP THE TEXT, not only its digest, for the append-only ones. A stale or missing
    # snapshot makes the next `check_since_snapshot()` compare against an OLDER state, which is
    # strictly a subset of the history the live file should still contain -- so a failure here
    # cannot wave a truncation through, only report one late. That is why it does not fail the
    # seal it rides along with.
    #
    # THAT REASONING IS TRUE OF STALE AND FALSE OF TORN (order be7b01fe1467). The temp file was
    # a FIXED, SHARED name -- `HANDOFF.md.tmp` -- and seal() is reached from `assert_intact()`,
    # which `publish.push()` calls before every push, while this project runs a `publish.py
    # --loop` daemon alongside manual pushes. Two sealers meeting here is an ordinary
    # situation, not a rarity: both open the same temp, the second truncates the first, and the
    # first's `os.replace` lands whatever was in the file at that instant. A torn snapshot is a
    # PREFIX of HANDOFF.md, and `_one_insertion(old=prefix, new=live)` returns True for any live
    # file that still begins with that prefix, because the longest common prefix already covers
    # the whole of `old`. So `check_since_snapshot` would answer "history preserved" for a
    # HANDOFF.md truncated and regrown -- precisely the attack it was added on 2026-08-27 (run
    # #36, order db2728e0f4bb) to catch, and which its own docstring records having passed
    # check_all(), verify_chain() and assert_intact() before it existed. The weakening is
    # proportional to the tear and was completely silent, because `except Exception: pass` did
    # not even reach the ledger.
    #
    # Unique per writer, matching `hostcheck._land_hosts` and `silence.write_json`; noted rather
    # than swallowed; and the temp is unlinked on failure so a shared state directory is not
    # littered with half-written snapshots. NOT failing the seal is still deliberate and
    # unchanged -- only the silence and the shared name are gone.
    for n in APPEND_ONLY:
        text = _read(n)
        if text is None:
            continue
        # FLATTENED, because a guarded name may now contain a path separator. With
        # `handoff/HANDOFF.md` on the list the old spelling built a snapshot path inside a
        # `handoff/` SUBDIRECTORY of SNAPSHOT_DIR that nothing creates, so the write would have
        # raised, been swallowed into `silence.note`, and left the one file this order added
        # unsnapshotted -- a guard that reports itself installed and takes no copy.
        flat = os.path.basename(_snapshot_path(n))
        tmp = os.path.join(SNAPSHOT_DIR,
                           "%s.%d.%d.tmp" % (flat, os.getpid(), threading.get_ident()))
        try:
            os.makedirs(SNAPSHOT_DIR, exist_ok=True)
            with open(tmp, "w", encoding="utf-8") as f:
                f.write(text)
            os.replace(tmp, _snapshot_path(n))
        except Exception:
            silence.note("ledger_guard.py:snapshot")
            try:
                os.unlink(tmp)
            except OSError:
                # Never written, or already renamed away. Nothing to clean and nothing to say.
                pass
    return rec


def _snapshot_path(name):
    """Where the sealed copy of `name` lives. ONE SPELLING, used by the writer and the reader.

    THE TWO HAD DRIFTED, AND THE GATE WENT DARK. `seal()` flattened the separator (the comment
    above it says why: `handoff/HANDOFF.md` would otherwise be written into a `handoff/`
    subdirectory nothing creates) and `_read_snapshot` did not, so it opened
    `state/ledger_snapshot/handoff/HANDOFF.md`, got FileNotFoundError, and returned None --
    which `check_since_snapshot` reads as "no sealed snapshot yet", returns TRUE on, and prints
    as `SINCE LAST SEAL : ok`. The copy was on disk the whole time, correctly written, under
    `handoff__HANDOFF.md`.

    So the append-only enforcement on `handoff/HANDOFF.md` was inert from the day that file
    joined APPEND_ONLY (2026-08-31, order 42db308cc85d) and reported itself passing on every
    run -- a checker that cannot fail, on the ledger whose own commentary records it ALREADY
    LOSING 629 LINES to the truncation class this module exists to catch, and which
    `assert_intact()` is the only gate on before `publish.push()`. Found 2026-09-01 while
    working orders 016fcf397818 / 77b098d099e6; not in any order.

    A shared function rather than the same two `.replace()` calls in two places, per the rule
    this project restates everywhere: two spellings of one fact are two things that can drift.
    """
    return os.path.join(SNAPSHOT_DIR, name.replace("/", "__").replace(os.sep, "__"))


def _read_snapshot(name):
    try:
        with open(_snapshot_path(name), encoding="utf-8") as f:
            return f.read()
    except FileNotFoundError:
        return None


def _lost_fraction(old, new):
    """How much of `old`'s substance is missing from `new`. -> float in [0, 1].

    Lines rather than bytes, and set membership rather than position, so a reordering or a
    reflowed paragraph is not read as a loss. Blank and rule-only lines are dropped because a
    markdown ledger is full of them and they carry no history.
    """
    def body(t):
        return {ln.strip() for ln in (t or "").splitlines()
                if ln.strip() and set(ln.strip()) - set("-=*_# ")}
    was = body(old)
    if not was:
        return 0.0
    return len(was - body(new)) / len(was)


def check_since_snapshot(name):
    """-> (ok, reason). Has this ledger LOST history since it was last sealed?

    THE ONLY PLACE `check_append_only` CAN ACTUALLY STAND IN THIS PROJECT. It was written as a
    PRE-write guard, and it had no production caller for a structural reason rather than an
    oversight: nothing in `src/` writes `HANDOFF.md` at all (`pipeline.py:36` says so outright),
    because the file is written by hand -- by a person, or by an agent's editor -- and a Python
    function cannot gate an editor. Left there, it was a safety in a file rather than a safety in
    effect, which is the exact fourth property Hard Rule -1 was written about.

    Asked from the other side of the write it becomes answerable. `seal()` keeps the last
    published copy; this compares the live file against it and hands the verdict to
    `assert_intact()`, which `publish.push()` already calls before every push. Measured on
    2026-08-27 (run #36): a HANDOFF.md truncated to its header and regrown LONGER than it began
    -- 473,848 -> 476,271 bytes -- passed `check_all()`, passed `verify_chain()` (no SHRANK: it
    grew) and passed `assert_intact()`. The whole relay history would have been published as
    fact. The byte floor and the SHRANK test are both size tests, and size is precisely what a
    truncate-then-append preserves.

    The tolerance is deliberate and it is not a weakening. `check_append_only` alone would refuse
    a person fixing a typo in a two-month-old entry, and that refusal blocks the PUSH -- a
    safety that stops ordinary work gets removed, and this project has already lost one gate
    that way. So an exact append passes outright, and anything else is measured: losing more
    than MAX_LOST_FRACTION of the ledger's lines is a truncation whoever caused it.
    """
    old = _read_snapshot(name)
    if old is None:
        return True, "no sealed snapshot of %s yet -- this run makes the first one" % name
    new = _read(name)
    if new is None:
        return False, ("%s existed at the last seal and is GONE now -- the relay's history was "
                       "deleted, not edited" % name)
    ok, why = check_append_only(name, new, old=old)
    if ok:
        return True, why
    lost = _lost_fraction(old, new)
    if lost <= MAX_LOST_FRACTION:
        return True, ("%s was edited rather than appended to (%.1f%% of its lines are gone, "
                      "under the %.0f%% truncation floor)" % (name, lost * 100,
                                                              MAX_LOST_FRACTION * 100))
    return False, ("%s has LOST %.0f%% of its lines since the last seal -- that is a truncation, "
                   "not an edit. The sealed copy is %s; compare it before writing anything else, "
                   "because the live file is no longer the history."
                   % (name, lost * 100, os.path.join(SNAPSHOT_DIR, name)))


def read_chain():
    """Read the chain, or raise -- "no chain yet" and "could not be read" are not the same claim.

    Only `FileNotFoundError` means "no chain yet": a fresh project, or the first run after this
    file was introduced, where an empty list is simply true. The blanket `except Exception:
    return []` that used to sit beside it collapsed every OTHER failure into that same empty
    list -- permission denied, the file held open by another process, a directory sitting where
    the file should be, an encoding that will not decode. Those are not "no chain"; they are
    "cannot tell", and `verify_chain()` on an empty list reports the chain intact because it
    never got the chance to find otherwise. `assert_intact()` trusts that report before `push()`
    reaches the PUBLIC repo. So this now only swallows the one exception that is genuinely
    silence-shaped, and lets everything else propagate: `verify_chain()` and `assert_intact()`
    make no attempt to catch it either, which means an unreadable chain now STOPS the publish
    (and, in `workorders.py`'s sweep, files a DETECTOR_FAILED order instead of a clean one) —
    fail closed, per the project rule that a layer that does not know must never authorise.
    """
    return _read_chain_lines()[0]


def _read_chain_lines():
    """-> (links, [unparseable line numbers]). The reader `read_chain()` is the front of.

    AND THE SECOND HALF OF THE SAME ARGUMENT, one level down (order 77b098d099e6). The
    docstring above records that the blanket `except Exception: return []` around the whole
    FILE was removed because "cannot tell" must never be collapsed into "no chain yet" -- and
    the per-LINE handler underneath it was doing exactly that, `except Exception: continue`,
    with no `silence.note` and nothing in the returned value to say a link had been dropped.
    A dropped link is indistinguishable from a link that was never written, which is precisely
    what a tamperer and a torn write both produce, inside the one function whose subject is
    telling those apart.

    NOT HYPOTHETICAL ON THIS MACHINE. `seal()` appends with a plain `open(..., "a")` +
    `write()`, and this project measured the Windows behaviour of exactly that pattern on
    2026-09-01: eight concurrent writers against an O_APPEND ledger lost 704 of 3,200 rows and
    tore 3 more, because the append is a seek-then-write rather than an atomic one there. A
    half-written final line is a thing that happens here.

    A dropped INTERIOR line is still caught downstream -- the next link's `prev` stops matching
    -- but a dropped FINAL line is caught by nothing at all, and `verify_chain()` then reports
    the shorter chain as intact. So the line numbers travel out of here and `verify_chain()`
    turns them into problems, which makes `assert_intact()` fail closed on them: a layer that
    does not know must never authorise.
    """
    out = []
    unparseable = []
    try:
        with open(CHAIN, encoding="utf-8") as f:
            for lineno, ln in enumerate(f, 1):
                ln = ln.strip()
                if ln:
                    try:
                        out.append(json.loads(ln))
                    except Exception:
                        silence.note("ledger_guard.py:chain-line-unparseable")
                        unparseable.append(lineno)
    except FileNotFoundError:
        return [], []
    return out, unparseable


# AN ACKNOWLEDGED SHRINK IS STILL REPORTED, EVERY RUN. NEVER HIDDEN. (owner ruling 2026-09-02,
# order be33a61be79f -- option (a) of the three the self-report offered.)
#
# On 2026-09-01 a maintenance probe written to prove the append-only gate can refuse repointed
# only half of this module's globals, sealed a two-hundred-line fixture into the REAL snapshot
# directory and appended fixture links to the REAL chain. No ledger content was lost -- the live
# files were never touched -- but links 948 and 949 now truthfully record the sealed state
# shrinking, and the chain is append-only, so `verify_chain()` reported three SHRANK problems for
# ever and `assert_intact()` blocked every push. The run that caused it refused to rewrite the
# chain and refused to add a quiet override, and left the choice to a person.
#
# The person chose an ACKNOWLEDGEMENT with these properties, each of which is load-bearing:
#   * SPECIFIC. It names a closed link range AND the ledger names it covers. A shrink outside
#     that range, or of a ledger not named, still FAILS -- there is no blanket waiver here.
#   * ATTRIBUTED AND REASONED. It carries the order id, the reason, who ruled and when. An entry
#     missing any of those is refused, i.e. it does not acknowledge anything, which is the
#     fail-closed direction: an unparseable or half-written acknowledgement file changes nothing.
#   * STILL REPORTED. `verify_chain(with_acknowledged=True)` hands the acknowledged problems
#     back beside the live ones, `main()` prints them under their own heading every single run,
#     and `assert_intact()` prints them on every push. The chain's evidence is intact and the
#     reader always sees it; what changed is only that a fault a person has ruled on no longer
#     stops the presses on its own. That is `suppressions.py`'s standing rule -- a suppressed
#     finding is still REPORTED -- applied to the hash chain.
ACKNOWLEDGED = os.path.join(HERE, "state", "ledger_chain_acknowledged.json")
_ACK_REASON_MIN = 40


def _load_acknowledgements():
    """-> [well-formed acknowledgement records]. Malformed entries are dropped AND noted.

    Fails closed in the only direction that is safe: an entry this cannot read acknowledges
    nothing, so the shrink it would have covered still fails. Nothing here can widen a waiver.
    """
    try:
        with open(ACKNOWLEDGED, encoding="utf-8") as f:
            raw = json.load(f)
    except FileNotFoundError:
        return []
    except Exception:
        silence.note("ledger_guard.py:acknowledgements-unreadable")
        return []
    if not isinstance(raw, list):
        silence.note("ledger_guard.py:acknowledgements-shape")
        return []
    out = []
    for rec in raw:
        ok = (isinstance(rec, dict)
              and isinstance(rec.get("links"), list) and len(rec["links"]) == 2
              and all(isinstance(x, int) for x in rec["links"])
              and rec["links"][0] <= rec["links"][1]
              and isinstance(rec.get("ledgers"), list) and rec["ledgers"]
              and all(isinstance(x, str) for x in rec["ledgers"])
              and isinstance(rec.get("reason"), str) and len(rec["reason"].strip()) >= _ACK_REASON_MIN
              and isinstance(rec.get("order"), str) and rec["order"].strip()
              and isinstance(rec.get("by"), str) and rec["by"].strip())
        if ok:
            out.append(rec)
        else:
            silence.note("ledger_guard.py:acknowledgement-refused")
    return out


def _acknowledgement_for(name, i_prev, i, acks):
    """The acknowledgement covering a SHRANK of `name` between links i_prev and i, or None.

    Both link indices must sit inside the closed range, and the ledger must be named. A range
    that covers only one end of the pair covers nothing: the shrink happened BETWEEN the two.
    """
    for rec in acks:
        lo, hi = rec["links"]
        if name in rec["ledgers"] and lo <= i_prev and i <= hi:
            return rec
    return None


def verify_chain(with_acknowledged=False):
    """-> (ok, [problems]), or (ok, [problems], [acknowledged]) when asked.

    An ACKNOWLEDGED problem is one a person has ruled on by name (see `ACKNOWLEDGED` above). It
    is removed from `problems` -- so it does not fail the chain -- and returned separately so it
    is still reported. The two-tuple form is kept for every existing caller.

    Recompute every link and report the first that does not verify.

    Three distinct faults are reported separately, because they mean different things:
      UNPARSEABLE   a line of the chain file will not read as JSON. The link it held is GONE
                    from every check below, and a dropped FINAL link is invisible to all of
                    them -- so it is a fault in its own right, not a line to skip past.
                    (order 77b098d099e6)
      BROKEN LINK   the chain itself was edited -- someone rewrote history
      SHRANK        a ledger got SMALLER between two links. Not proof of wrongdoing (a file can
                    legitimately be rewritten) but it is exactly the shape of a truncation, and
                    it is invisible to every other check once the write has happened.
    """
    links, unparseable = _read_chain_lines()
    problems = []
    acknowledged = []
    acks = _load_acknowledgements()
    for lineno in unparseable:
        problems.append(
            "chain line %d will not parse -- the link it held is missing from every check "
            "below, and a torn or edited FINAL line is invisible to all of them. Inspect "
            "%s at that line; do NOT rebuild the chain, it is the evidence."
            % (lineno, CHAIN))
    prev = None
    for i, rec in enumerate(links):
        body = {k: rec.get(k) for k in ("at", "prev", "ledgers")}
        if rec.get("self") != _digest(json.dumps(body, sort_keys=True)):
            problems.append("link %d does not verify -- the chain has been edited" % i)
        if rec.get("prev") != prev:
            problems.append("link %d does not follow link %d" % (i, i - 1))
        if i:
            for name, cur in (rec.get("ledgers") or {}).items():
                old_l = ((links[i - 1].get("ledgers") or {}).get(name) or {})
                cur_l = cur or {}
                # SAME UNIT ON BOTH SIDES, ALWAYS. Links written before order 016fcf397818
                # store a CHARACTER count under `bytes` and carry no `chars` key; links written
                # after store real bytes plus `chars`. Comparing across that boundary in mixed
                # units would be a comparison that cannot fail (UTF-8 bytes >= characters), so
                # the pair is measured in whichever unit both links actually have.
                if "chars" in old_l or "chars" in cur_l:
                    unit = "bytes" if ("chars" in old_l and "chars" in cur_l) else "characters"
                else:
                    unit = "characters"      # both legacy: `bytes` there means characters
                key = "bytes" if unit == "bytes" else "chars"
                was = old_l.get(key, old_l.get("bytes"))
                now = cur_l.get(key, cur_l.get("bytes"))
                # `is not None`, not truthiness: a ledger wiped to a genuinely EMPTY file records
                # `now == 0`, which is falsy, and the old `was and now and ...` short-circuited
                # to False on exactly the total truncation this check exists to catch. That it
                # never bit is owed to `assert_intact()` running `check_all()`'s byte floor
                # first -- redundancy in the caller, not a property of this function, and any
                # standalone caller (a drill, a health check) got a clean pass on a wiped ledger.
                if was is not None and now is not None and name in APPEND_ONLY and now < was:
                    msg = ("%s SHRANK between link %d and %d (%d -> %d %s)"
                           % (name, i - 1, i, was, now, unit))
                    ack = _acknowledgement_for(name, i - 1, i, acks)
                    if ack is None:
                        problems.append(msg)
                    else:
                        acknowledged.append("%s -- ACKNOWLEDGED by %s (order %s): %s"
                                            % (msg, ack["by"], ack["order"], ack["reason"]))
        prev = rec.get("self")
    if with_acknowledged:
        return (not problems), problems, acknowledged
    return (not problems), problems


def assert_intact():
    """Raise unless every ledger is whole. Called by `publish` before anything is pushed.

    The ledgers travel to the PUBLIC repo with everything else, so a truncated HANDOFF or a
    BUGS.md with a resolved bug still sitting in Open does not just mislead the next run -- it
    is published. This is the enforcing wrapper; `check_all` is the reporting one, and both
    exist because a checker with no caller is a checker that never runs.
    """
    bad = check_all()
    if bad:
        raise LedgerViolation(
            "the relay's ledgers are not intact:\n"
            + "\n".join("  %s: %s" % (n, "; ".join(p)) for n, p in sorted(bad.items())))
    ok, problems, acknowledged = verify_chain(with_acknowledged=True)
    # REPORTED ON EVERY PUSH, before the verdict, whatever the verdict is. An acknowledgement
    # that stopped being printed would be a waiver, and this module does not have those.
    for line in acknowledged:
        print("ledger chain: carried  " + line)
    if not ok:
        # THE CUT IS KEPT AND THE CUT IS DECLARED (order e62a650c6c41). The split with `main()`
        # is deliberate and stays: an exception message is not a repair sheet, and `main()` two
        # functions down prints the list uncapped for the person actually going to fix it. What
        # was wrong is that this stopped at six saying NOTHING -- and `verify_chain` appends up
        # to three problems per link, so three bad links already overflow it. An operator whose
        # push was blocked read six faults and had no way to know there were fifty, which is
        # how a second break hides behind the first. House doctrine (Hard Rule 0, and
        # `corpus_db._cell`'s ruling on it, order 6160ef68b229) allows a display cut precisely
        # because it is reversible, and refuses one that is silent.
        head = problems[:6]
        more = ("\n  ... and %d further problem(s) not shown here; run "
                "`python src/ledger_guard.py` for the full list" % (len(problems) - 6)
                ) if len(problems) > 6 else ""
        raise LedgerViolation(
            "the ledger hash chain does not verify:\n  " + "\n  ".join(head) + more)
    # THE APPEND-ONLY RULE, ENFORCED RATHER THAN DECLARED. Before this, `APPEND_ONLY` was a
    # tuple nothing consulted on any production path: `check_append_only` had no caller outside
    # `drill.py`, and the two checks that DO run here are both size tests that a
    # truncate-then-append passes by growing. Run #36 order db2728e0f4bb.
    for name in APPEND_ONLY:
        ok, why = check_since_snapshot(name)
        if not ok:
            raise LedgerViolation(why)
    # `seal()` returns None on any write failure (disk full, permissions, the state/ directory
    # gone) with no exception raised. A bare call here used to discard that -- `verify_chain`
    # would keep passing on every later run, because the existing links still verify against
    # each other; there would simply be no new one. The mechanism whose whole job is answering
    # "did anything change these files since the last run" would have silently stopped
    # answering, and nothing downstream would know to stop trusting it.
    if seal() is None:
        raise LedgerViolation(
            "the ledger hash chain could not be sealed this run -- the new link was not "
            "written, so a future run cannot tell whether these files changed underneath it")
    return True


def main():
    """The CLI. RUNS ALL THREE MECHANISMS, because it says all three passed.

    ORDER 418e83501f0f. This called `check_all()` and, on an empty result, printed "ledgers: all
    intact" and returned 0 -- having run ONE of the three mechanisms this module's docstring
    enumerates. It never called `verify_chain()` and never called `check_since_snapshot()`, and
    the second of those was added on 2026-08-27 specifically because `check_all()`'s byte floor
    and `verify_chain()`'s SHRANK test are BOTH size tests and a truncate-then-append preserves
    size. So a broken hash chain, or a HANDOFF.md truncated to its header and regrown, printed
    "all intact" and exited 0 out of the module whose entire subject is that failure.
    `assert_intact()` does run all three, but it is reached only from `publish.push()`; the CLI
    is the surface a person uses to ASK, and it was the one answering from the least evidence.

    Deliberately does NOT seal. `assert_intact()` seals because it is the gate on a write that is
    about to happen; a question asked from the command line must not change the state it is
    asking about, or every `--check` would move the baseline the next one compares against.

    Each mechanism reports separately, pass or fail. A single "all intact" line is what let the
    gap hide: three verdicts collapsed into one sentence cannot be audited against the code.
    """
    import argparse
    ap = argparse.ArgumentParser(description="check the relay's ledgers")
    ap.parse_args()
    failures = 0

    bad = check_all()
    if bad:
        failures += 1
        print("STRUCTURE + FLOORS: FAILED")
        for name, problems in sorted(bad.items()):
            print("  %s:" % name)
            for p in problems:
                print("     " + p)
    else:
        print("STRUCTURE + FLOORS: ok (%d ledger(s) parsed, all above their byte floors)"
              % len(MIN_BYTES))

    ok, problems, acknowledged = verify_chain(with_acknowledged=True)
    links = len(read_chain())
    if ok and not acknowledged:
        print("HASH CHAIN       : ok (%d link(s) verify, no append-only ledger shrank)" % links)
    elif ok:
        print("HASH CHAIN       : ok (%d link(s) verify; %d acknowledged shrink(s) carried -- "
              "ruled on by a person, listed below, never hidden)" % (links, len(acknowledged)))
    else:
        failures += 1
        # Uncapped. `assert_intact()` prints the first six into an exception message, which is a
        # different job; this is the surface somebody reads to go and repair the chain, and a
        # truncated fault list is how a second break gets missed behind the first.
        print("HASH CHAIN       : FAILED over %d link(s)" % links)
        for p in problems:
            print("     " + p)
    for line in acknowledged:
        print("     carried: " + line)

    for name in APPEND_ONLY:
        ok, why = check_since_snapshot(name)
        if ok:
            print("SINCE LAST SEAL  : ok  %s -- %s" % (name, why))
        else:
            failures += 1
            print("SINCE LAST SEAL  : FAILED  %s -- %s" % (name, why))

    print("\nledgers: all intact" if not failures
          else "\nledgers: %d of the three mechanisms reported a fault" % failures)
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
