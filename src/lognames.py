"""LOGNAMES — the one place a job's log file is named.

The dashboard's Jobs panel, the `corpus read is progressing` standard, the stall detector and
the foreman's restart remedy are all keyed on these filenames. They used to be string literals
repeated in overnight.py and dashboard.py independently — one rename in one place and the whole
observability chain went quietly blind: panel empty, standard vacuously green, remedy never
firing. A constant shared by writer and reader cannot drift.
"""

READ = "read_auto.log"          # the corpus reader (read.py --run), started by the supervisor
ROLL = "roll_auto.log"          # the page roll (feats.py --roll)
PIPELINE = "pipeline_auto.log"  # the phase runner, when the supervisor drives it
RECATALOGUE = "recatalogue.log"  # catalogue_web --recatalogue, foreman-dispatched
SWEEP = "sweep.log"             # the character sweep rebuild (sweep.py)
CALIBRATE = "calibrate.log"     # the daily charter regression (magnitude.py --calibrate)

# WHICH PROCESS WRITES WHICH LOG. The stall detector has to ask "is the writer of this log
# still up?", and it used to answer by assuming the log's own filename was the script name --
# `read_auto.log` -> is `read_auto.py` running? Nothing by that name has ever run, so the
# corpus reader, the page roll and the phase pipeline were all permanently invisible to the one
# standard built to catch a job that is up and producing nothing. Meanwhile stale legacy logs
# whose stems DO collide with a live script (`read.log`, 52 bytes, last written two days ago,
# while `read.py` runs) were matched as live and would have been reported stalled forever once
# the timer was fixed -- a false alarm and a blind spot from the same wrong assumption.
#
# The fragment is matched against the live command line by `overnight.running()`, so it must be
# specific enough to distinguish two invocations of the same script: `feats.py --roll` is the
# page roll, a bare `feats.py` is something else.
#
# PIPELINE CARRIES `--run` BECAUSE pipeline.py HAS INVOCATIONS THAT ARE NOT THIS JOB (order
# 08c1fd3932a4). It was a bare `pipeline.py`, which is the rule above being broken by the table
# the rule is written over: `pipeline.py --status` prints the handoff and exits, and a hand-run
# `pipeline.py --phase 6` is one stage, yet either one answered "the phase runner is up" to
# `overnight.running()` -- and through it to the stall detector, the dashboard's Jobs panel and
# the foreman's restart remedy. The supervisor's own two invocations now pass `--run`
# (overnight.py STANDING and the serial lap call), so the fragment names the writer of
# pipeline_auto.log and nothing else. `--run` is optional in pipeline.py, so a bare invocation
# still runs the phases; it is a label on the daemon, not a new mode.
#
# SWEEP IS DELIBERATELY BARE, and that is not the same fault. Every invocation of sweep.py runs
# the rebuild and writes CHARACTER_SWEEP.json -- `--top` only changes how many rows the report
# prints -- so there is no second invocation to be confused with, and a hand-run sweep.py
# answering "the sweep is running" is a true answer. The rule asks for enough specificity to
# distinguish two invocations; where a script has one, its name is that.
OWNER = {
    READ:        "read.py --run",
    ROLL:        "feats.py --roll",
    PIPELINE:    "pipeline.py --run",
    RECATALOGUE: "catalogue_web.py --recatalogue",
    SWEEP:       "sweep.py",
    CALIBRATE:   "magnitude.py --calibrate",
}
