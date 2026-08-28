"""File the two defects batch 2 found OUTSIDE its own orders and correctly did not touch.

An agent that notices something beyond its assignment and neither fixes it nor files it has
found nothing -- the observation dies with its summary. Both of these were verified by the agent
against source and both are the same family of defect this project keeps paying for.
"""
import os
import sys

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(HERE, "src"))
import workorders  # noqa: E402

FINDINGS = [
    dict(
        code="WITHDRAW_CHAPTERS_MOVES_BEFORE_IT_COMMITS",
        where="src/withdraw_chapters.py stray-file sweep",
        severity="MAJOR",
        what=("withdraw_chapters' stray-file sweep calls shutil.move UNGUARDED, so a failure "
              "part-way through aborts main() AFTER files have already moved and BEFORE the "
              "catalog is written. That is the worst possible ordering: the filesystem has been "
              "changed and the record of the change has not, so the catalog and the tree "
              "disagree and nothing on disk says which is right. Either move every file only "
              "after the catalog write is committed, or wrap the sweep so a partial move is "
              "rolled back or at minimum recorded. Found by the run36 batch-2 agent while "
              "working cda7b9e2b4e1; outside its orders, so correctly not touched."),
        evidence={"call": "shutil.move, unguarded",
                  "ordering": "move happens before the catalog write",
                  "consequence": "abort leaves tree and catalog disagreeing",
                  "found_while": "working order cda7b9e2b4e1"},
    ),
    dict(
        code="BINDING_QUARANTINE_LOST_UPDATE",
        where="src/binding_health.py quarantine() / release()",
        severity="MAJOR",
        what=("binding_health.quarantine() and release() are read-modify-writes on "
              "data/HOST_QUARANTINE.json with NO compare-and-swap, so two writers lose one "
              "another's update. This is DISTINCT from the fixed-temp-name collision that order "
              "98831f6e6f6d named and that _land now routes around -- fixing the temp name does "
              "nothing about a lost update, and the two look similar enough that the first fix "
              "reads as covering both. run()'s merge got a CAS this shift (23d84e6f8e81); these "
              "two paths did not. Found by the run36 batch-2 agent, outside its orders."),
        evidence={"file": "data/HOST_QUARANTINE.json",
                  "paths": ["quarantine()", "release()"],
                  "hazard": "lost update, not a temp-name collision",
                  "distinct_from": "98371f6e6f6d / 98831f6e6f6d temp-name fix",
                  "already_fixed_elsewhere": "run()'s merge via _land_cas (23d84e6f8e81)"},
    ),
]


def main():
    for f in FINDINGS:
        o = workorders.file_order(handler="RUN",
                                  found_by="run36 batch-2 agent, observed outside its orders",
                                  **f)
        print("filed:", o["id"], o["code"])
    return 0


if __name__ == "__main__":
    sys.exit(main())
