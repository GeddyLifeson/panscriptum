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
