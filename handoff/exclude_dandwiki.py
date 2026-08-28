"""Owner decision 2026-08-28: remove dandwiki as a source.

WHAT THAT ACTUALLY MEANS HERE, because the order it answers under-described it. `www.dandwiki.com`
is not a source, it is a HOST, and it serves FOUR sources on the Acquisitions Roll -- all
third-party D&D publishers:

    Yorviing's Arcane Grimoire            478 entries   (assayed: ceiling + magnitude recorded)
    Dr. Firestorm's Engineering Corps     425 entries
    Mage Hand Press                        22 entries
    Savant                                  8 entries   (assayed: ceiling + magnitude recorded)
                                          ---
                                          933 entries, all already catalogued

The 403 login wall blocks FUTURE mining. It does not touch what is already on disk.

WHY `roll.exclude` AND NOT A DELETION. `exclude()` is the sanctioned curatorial tool and it is
explicitly non-destructive: "Excluded sources keep their records. They are removed from WORK, not
from disk." All 933 entries stay exactly where they are; the four sources simply stop being
worked. There is owner precedent in the same field -- four sources were excluded on 2026-08-20
with a dated note -- so this follows the house form rather than inventing one.

REVERSIBLE, and the undo is one call per source:
    python -c "import sys;sys.path.insert(0,'src');import roll;roll.include('<name>')"
(or re-run `exclude` with a corrected note). A canonical snapshot was taken immediately before
this ran: state/backups/canon/canon-20260828-002553.zip.

The note recorded against each source is deliberately specific about the MECHANISM, because the
next person to read the roll needs to know this was a policy refusal and not a dead host: a dead
host might come back, and a login wall will not without an account.
"""
import os
import sys

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(HERE, "src"))
import roll  # noqa: E402

SOURCES = [
    "Yorviing's Arcane Grimoire",
    "Dr. Firestorm's Engineering Corps",
    "Mage Hand Press",
    "Savant",
]

NOTE = ("Owner decision 2026-08-28: removed as a source. Its host www.dandwiki.com answers "
        "HTTP 403 -- 'To reduce server load, we had to restrict this action to logged in users "
        "only' -- so it is a deliberate policy refusal, not an outage, and no retry can ever "
        "satisfy it without an account the library does not hold. The 24h quarantine retry was "
        "probing a condition that cannot change. Entries already catalogued from this host are "
        "KEPT on disk (exclude removes a source from work, not from disk); what stops is further "
        "mining and further work. Reversible: re-include if an account is ever held.")


def main():
    ok, failed = [], []
    for name in SOURCES:
        try:
            wrote = roll.exclude(name, NOTE)
            ok.append((name, wrote))
            print("excluded: %-38s (roll written: %s)" % (name, wrote))
        except Exception as e:
            failed.append((name, type(e).__name__, str(e)[:120]))
            print("FAILED  : %-38s %s: %s" % (name, type(e).__name__, str(e)[:120]))
    print()
    print("excluded %d of %d" % (len(ok), len(SOURCES)))
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
