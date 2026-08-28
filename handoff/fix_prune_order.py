"""Re-file order 915fa8abf2bd with its text intact.

The first attempt was written through a shell argument containing BACKTICKS, and bash performed
command substitution on them: the word inside the backticks was executed as a command
("wanted: command not found") and replaced with the empty string, so the order landed reading
"so nothing from it enters  -- and prune_export then...".

That is the eaten-escape corruption CLAUDE.md has warned about since the beginning, committed by
the maintenance run that was in the middle of telling its own agents not to do it. Recording it
here rather than quietly repairing it, because the failure is the interesting part: the order
still LOOKED fine in the queue listing, which is exactly how this bug survives.

Filed through a file, with the Write tool, which is the rule.
"""
import os
import sys

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(HERE, "src"))
import workorders  # noqa: E402

WHAT = (
    "publish.sync_tree skips a COPY_DIRS root that is not a live directory "
    "(if not os.path.isdir(root): continue), so nothing from it enters the 'wanted' set -- and "
    "prune_export then walks the EXPORT copy of that same directory and deletes every file in "
    "it. For a directory genuinely removed from the project that is correct, and is the point "
    "of the new prune. For a directory that is momentarily unavailable -- a locked mount, a "
    "rename in flight, a permissions blip, an antivirus quarantine, all of which have happened "
    "on this machine -- it silently withdraws an ENTIRE SUBTREE from a PUBLIC repo. This is the "
    "same 'absent means unauthored, not delete' ambiguity that pipeline.write_record and "
    "write_record_catalogue were both fixed for THIS SHIFT, arriving in the one module whose "
    "writes are irreversible and public. The two existing guards do not cover it: SITE != HERE "
    "and the .is-export-copy marker are both satisfied in exactly this case. SUGGESTED FIX, "
    "matching the ruling already applied twice elsewhere today: prune only within roots that "
    "were actually walked, and treat a MISSING live root as a refusal to prune that subtree "
    "plus a loud note, rather than as permission to empty it. Verified by dry run this shift "
    "that the prune currently wants to delete only 13 files, every one of them a "
    "src/__pycache__ .pyc that should never have been published -- so the feature is working "
    "and this is a latent edge, not a live fault."
)

EVIDENCE = {
    "guards_that_do_not_cover_it": ["SITE != HERE", ".is-export-copy marker present"],
    "anchor": "if not os.path.isdir(root): continue   (sync_tree, COPY_DIRS loop)",
    "dry_run_today": "13 files, all src/__pycache__/*.pyc",
    "same_ruling_applied_twice_this_shift": ["pipeline.write_record",
                                             "pipeline.write_record_catalogue"],
    "COPY_DIRS": "src, prompts, reference, registry_terminal, handoff",
    "note_on_this_order": ("the first filing of this order was corrupted by shell backtick "
                           "substitution and was re-filed through a file"),
}


def main():
    o = workorders.file_order(
        code="PRUNE_EXPORT_TREATS_AN_ABSENT_LIVE_ROOT_AS_DELETE_EVERYTHING",
        what=WHAT, handler="RUN", severity="MAJOR",
        where="src/publish.py prune_export / sync_tree",
        evidence=EVIDENCE,
        found_by="maintenance-2026-08-27 pre-publish audit of the new delete path")
    print("refiled:", o["id"], "seen", o["seen"])
    ok = "enters the 'wanted' set" in o["what"]
    print("text intact:", ok)
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
