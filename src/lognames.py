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

# WHAT EACH MANAGED JOB PRODUCES -- the second witness for "every running job is advancing"
# (order d9328fe1ee38, decided under the owner's 2026-09-28 "fix everything" instruction: remedy
# (a) with (b) for anything undeclared, and the declaration lives here beside the log, as the order
# asked). The stall standard used to watch the LOG alone, and on 2026-09-08 it called
# `feats.py --roll` stalled after 82 minutes of quiet log while the crawl had written a catalogue
# entry one minute earlier -- in front of a remedy licensed to kill it. A throttled crawl logs
# almost nothing between entries; its product is files.
#
# Paths are relative to the kit root. A FILE is witnessed by its own mtime; a DIRECTORY by its own
# mtime and each immediate child's (a new or replaced file bumps its directory's mtime, so the
# ~143 host directories under data/feats witness ~277k files without walking them). A job is
# stalled only when its log AND every declared output have held past MAX_JOB_SILENCE_MIN. A job
# missing from this table cannot be called stalled on its log alone: it reads UNMEASURABLE.
PRODUCT = {
    READ:        ("data/readfeats",),
    ROLL:        ("data/feats",),
    PIPELINE:    ("state/PIPELINE_STATE.json", "data/records"),
    RECATALOGUE: ("data/records",),
    SWEEP:       ("data/CHARACTER_SWEEP.json",),
    CALIBRATE:   ("data/CHARTER_REGRESSION.json",),
}
