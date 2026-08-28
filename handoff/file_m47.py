"""File M47 as a work order. Run #35 raised it as a design question and it lived only in
NEXT_STEPS.md, which is overwritten every run -- so an unfiled question is a question that
disappears on schedule.

The interaction: `codewatch.stale()` requires the `src/` fingerprint to hold still for 180
seconds before a standing daemon exits rc=17 to pick up changed source. A maintenance shift
rewrites `src/` more or less continuously for hours, so the fingerprint never settles and NO
DAEMON BOUNCES FOR THE ENTIRE SHIFT. Re-measured 2026-08-27, after a shift in which roughly
forty source files changed: `codewatch.py` reports foreman 0 restarts in the last hour,
overwatch 0, publish 0.

Both halves of this are working as designed, which is exactly why it needs a person:

  * The settle rule is RIGHT. A digest taken mid-write is a digest of garbage, and bouncing
    daemons on every keystroke is worse than lag.
  * But it means every long-lived job spends a maintenance run executing the code as it stood
    when the run began -- including `publish.py --push --loop`, which on 2026-08-25 pushed
    deliberately-corrupted source to a public repo twice, hours after the guard against exactly
    that was written, because a Python process does not re-read its own source.

Nothing broke this time. The question is whether a maintenance run should quiesce the publisher
for its duration, or whether daemons should bounce on a settle window measured differently --
and that is a judgment about how much lag is acceptable against how much staleness, which is
the owner's to make.
"""
import os
import sys

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(HERE, "src"))
import workorders  # noqa: E402

WHAT = (
    "M47 -- NO DAEMON PICKS UP NEW CODE FOR THE WHOLE OF A MAINTENANCE SHIFT, AND BOTH HALVES "
    "OF THAT ARE WORKING AS DESIGNED. codewatch.stale() needs the src/ fingerprint to hold "
    "still for 180s before a standing daemon exits rc=17 and the keeper restarts it on current "
    "code. A maintenance run rewrites src/ for hours, so the fingerprint never settles. "
    "Measured 2026-08-27 after a shift that changed roughly forty modules: codewatch reports "
    "foreman 0 restarts in the last hour, overwatch 0, publish 0 -- every one of them still "
    "executing the code as it stood when the shift began. The settle rule is correct (a digest "
    "taken mid-write is a digest of garbage, and bouncing on every edit is worse than lag), and "
    "the consequence is also real: this is precisely the shape that let a publish.py --push "
    "--loop daemon ship deliberately-corrupted source to a public repo twice on 2026-08-25, "
    "hours after the guard against it was written. Nothing broke this shift. THE DECISION IS "
    "THE OWNER'S: should a maintenance run quiesce the publisher for its duration, should the "
    "settle window be measured differently (e.g. per-file rather than whole-tree, so an "
    "untouched daemon's dependencies settling is enough), or is hours of staleness during a "
    "supervised shift simply acceptable? Raised by run #35 as a question and left only in "
    "NEXT_STEPS.md, which is overwritten every run -- filed here so it stops disappearing."
)

EVIDENCE = {
    "settle_window_seconds": 180,
    "measured": "2026-08-27, after ~40 modules changed in one shift",
    "restarts_last_hour": {"foreman": 0, "overwatch": 0, "publish": 0},
    "precedent": ("publish.py --push --loop, started 14:28 on 2026-08-25, pushed mutated "
                  "prose_gate.py and escalation.py to a public repo twice with the pre-guard "
                  "code loaded in memory"),
    "both_halves_correct": ("a digest taken mid-write is garbage, so the settle rule is right; "
                            "the staleness it causes is also real"),
    "raised_by": "run #35, as a design question in NEXT_STEPS.md only",
    "owner_options": ["quiesce the publisher for the duration of a maintenance run",
                      "measure the settle window per-file rather than whole-tree",
                      "accept shift-long staleness as the cost of a correct settle rule"],
}


def main():
    o = workorders.file_order(
        code="M47_NO_DAEMON_BOUNCES_DURING_A_MAINTENANCE_SHIFT",
        what=WHAT, handler="OWNER", severity="MAJOR",
        where="src/codewatch.py stale() settle window vs standing daemons",
        evidence=EVIDENCE,
        found_by="maintenance-2026-08-27 (re-measured; raised by run #35)")
    print("filed:", o["id"], o["code"])
    return 0


if __name__ == "__main__":
    sys.exit(main())
