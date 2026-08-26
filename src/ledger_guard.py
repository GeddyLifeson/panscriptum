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

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

APPEND_ONLY = ("HANDOFF.md",)
# Floors, set well below the current sizes so ordinary editing never trips them. They exist to
# catch a TRUNCATION -- a file that lost its history -- not to police how much a run writes.
MIN_BYTES = {"HANDOFF.md": 20000, "BUGS.md": 8000, "NEXT_STEPS.md": 3000,
             "MAINTENANCE.md": 5000}
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


def check_append_only(name, new_text):
    """-> (ok, reason). Would this write LOSE history?

    Containment, not length. A run that truncated the file and then appended a long entry
    produces a LONGER file, so a size comparison would wave it through -- and that is precisely
    the shape a botched overwrite takes.
    """
    if name not in APPEND_ONLY:
        return True, "%s is not append-only" % name
    old = _read(name)
    if old is None:
        return True, "%s does not exist yet" % name
    if old.strip() and old not in (new_text or ""):
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


def _digest(text):
    import hashlib
    return hashlib.sha256((text or "").encode("utf-8")).hexdigest()[:32]


def seal():
    """Append a hash-chained record of the ledgers' current state. -> the new link.

    THE THIRD MECHANISM, and it answers what the other two cannot.

    `check_append_only` proves a PROPOSED write keeps history -- but only if it is called, and
    only by a writer that chose to call it. `check_structure` proves the file parses. Neither
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
    rec = {"at": time.time(), "prev": prev,
           "ledgers": {n: {"digest": _digest(_read(n) or ""), "bytes": len((_read(n) or ""))}
                       for n in sorted(MIN_BYTES)}}
    rec["self"] = _digest(json.dumps({k: rec[k] for k in ("at", "prev", "ledgers")},
                                     sort_keys=True))
    try:
        os.makedirs(os.path.dirname(CHAIN), exist_ok=True)
        with open(CHAIN, "a", encoding="utf-8") as f:
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")
    except Exception:
        return None
    return rec


def read_chain():
    out = []
    try:
        with open(CHAIN, encoding="utf-8") as f:
            for ln in f:
                ln = ln.strip()
                if ln:
                    try:
                        out.append(json.loads(ln))
                    except Exception:
                        continue
    except FileNotFoundError:
        return []
    except Exception:
        return []
    return out


def verify_chain():
    """-> (ok, [problems]). Recompute every link and report the first that does not verify.

    Two distinct faults are reported separately, because they mean different things:
      BROKEN LINK   the chain itself was edited -- someone rewrote history
      SHRANK        a ledger got SMALLER between two links. Not proof of wrongdoing (a file can
                    legitimately be rewritten) but it is exactly the shape of a truncation, and
                    it is invisible to every other check once the write has happened.
    """
    links = read_chain()
    problems = []
    prev = None
    for i, rec in enumerate(links):
        body = {k: rec.get(k) for k in ("at", "prev", "ledgers")}
        if rec.get("self") != _digest(json.dumps(body, sort_keys=True)):
            problems.append("link %d does not verify -- the chain has been edited" % i)
        if rec.get("prev") != prev:
            problems.append("link %d does not follow link %d" % (i, i - 1))
        if i:
            for name, cur in (rec.get("ledgers") or {}).items():
                was = ((links[i - 1].get("ledgers") or {}).get(name) or {}).get("bytes")
                now = (cur or {}).get("bytes")
                # `is not None`, not truthiness: a ledger wiped to a genuinely EMPTY file records
                # `now == 0`, which is falsy, and the old `was and now and ...` short-circuited
                # to False on exactly the total truncation this check exists to catch. That it
                # never bit is owed to `assert_intact()` running `check_all()`'s byte floor
                # first -- redundancy in the caller, not a property of this function, and any
                # standalone caller (a drill, a health check) got a clean pass on a wiped ledger.
                if was is not None and now is not None and name in APPEND_ONLY and now < was:
                    problems.append("%s SHRANK between link %d and %d (%d -> %d bytes)"
                                    % (name, i - 1, i, was, now))
        prev = rec.get("self")
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
    ok, problems = verify_chain()
    if not ok:
        raise LedgerViolation(
            "the ledger hash chain does not verify:\n  " + "\n  ".join(problems[:6]))
    seal()
    return True


def main():
    import argparse
    ap = argparse.ArgumentParser(description="check the relay's ledgers")
    ap.parse_args()
    bad = check_all()
    if not bad:
        print("ledgers: all intact")
        return 0
    for name, problems in sorted(bad.items()):
        print("%s:" % name)
        for p in problems:
            print("   " + p)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
