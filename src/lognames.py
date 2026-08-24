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
OWNER = {
    READ:        "read.py --run",
    ROLL:        "feats.py --roll",
    PIPELINE:    "pipeline.py",
    RECATALOGUE: "catalogue_web.py --recatalogue",
    SWEEP:       "sweep.py",
    CALIBRATE:   "magnitude.py --calibrate",
}
