"""Prepend run #36's entry to HANDOFF.md and install NEXT_STEPS.md. Append-only for the log.

HANDOFF.md is a JOURNAL: newest on top, never overwritten. `ledger_guard` treats it as
APPEND_ONLY and checks containment, so this inserts the new entry after the file's header block
and leaves every existing byte in place -- a prepend that rewrote the header would read as a
truncation to the guard, correctly.

NEXT_STEPS.md is the opposite by design: overwritten every run, because it is the reading of the
queue rather than a record of it.
"""
import os
import shutil
import sys

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(HERE, "src"))
import silence  # noqa: E402

HANDOFF = os.path.join(HERE, "HANDOFF.md")
NEXT = os.path.join(HERE, "NEXT_STEPS.md")
ENTRY = os.path.join(HERE, "handoff", "run36", "HANDOFF_ENTRY.md")
NEXT_SRC = os.path.join(HERE, "handoff", "run36", "NEXT_STEPS_DRAFT.md")

MARKER = "---\n"          # the header block ends at the first horizontal rule


def main():
    with open(ENTRY, encoding="utf-8") as fh:
        entry = fh.read().rstrip() + "\n"
    with open(HANDOFF, encoding="utf-8") as fh:
        old = fh.read()

    i = old.find("\n" + MARKER)
    if i < 0:
        raise SystemExit("HANDOFF.md: could not find the header rule; refusing to guess")
    cut = i + 1 + len(MARKER)
    head, rest = old[:cut], old[cut:]

    new = head + "\n" + entry + "\n" + rest.lstrip("\n")

    # CONTAINMENT, checked here rather than trusted: every byte of the old body must still be
    # present, or this is a truncation wearing a prepend's clothes.
    if rest.strip() not in new:
        raise SystemExit("refusing to write: the existing HANDOFF.md body would not survive")
    if len(new) <= len(old):
        raise SystemExit("refusing to write: the file did not grow")

    shutil.copy2(HANDOFF, os.path.join(HERE, "state", "backups", "HANDOFF.md.pre-run36"))
    tmp = HANDOFF + ".run36.%d.tmp" % os.getpid()
    with open(tmp, "w", encoding="utf-8") as fh:
        fh.write(new)
    if silence.replace_retry(tmp, HANDOFF) is False:
        raise SystemExit("HANDOFF.md could not be replaced -- nothing written")
    print("HANDOFF.md: %d -> %d bytes (+%d)" % (len(old), len(new), len(new) - len(old)))

    with open(NEXT_SRC, encoding="utf-8") as fh:
        nxt = fh.read()
    tmp2 = NEXT + ".run36.%d.tmp" % os.getpid()
    with open(tmp2, "w", encoding="utf-8") as fh:
        fh.write(nxt)
    if silence.replace_retry(tmp2, NEXT) is False:
        raise SystemExit("NEXT_STEPS.md could not be replaced")
    print("NEXT_STEPS.md: %d bytes" % len(nxt))
    return 0


if __name__ == "__main__":
    sys.exit(main())
