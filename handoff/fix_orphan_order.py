"""Correct and sharpen order e26cb69d77fb, and file the second, different fault beside it.

The sweep reported one orphan record (bone-jeff-smith, 86 entries) with no roll row. Measured
directly, there are TWO records with no matching roll row -- 390 catalogued entries between them
-- and they are NOT the same fault, which is the part worth getting right before anyone acts:

  * `who-framed-roger-rabbit-incl-all-content-from-its-associated` (304 entries) DOES have a
    roll row. The row is "Who Framed Roger Rabbit (incl. all content from its associated
    crossover-toon IPs)", whose full slug is 79 characters -- and the record on disk is named
    with that slug TRUNCATED TO EXACTLY 60. Nothing is missing from the roll; the record's
    IDENTITY was cut in half by a cap, so every lookup that slugs the roll name and expects a
    file finds nothing. That is `catalogue_aurora.slug()`'s 60-character truncation, which the
    same sweep independently flagged as inconsistent with `ingest_doc.slug()` (uncapped) -- and
    it is a Hard Rule 0 violation of the purest kind: a cap that does not fail, and quietly
    produces a smaller universe by making a 304-entry source unfindable.
  * `bone-jeff-smith` (86 entries) has no roll row under any spelling -- searching the roll for
    "bone" returns nothing at all. That one really is an orphan, and it is a different question
    (was it ever rolled, or was its row lost when SWEEP_ROLL.json was destroyed twice on
    2026-08-26?).

Filing them apart because one is a code defect with a mechanical fix and the other is a
curatorial question about what belongs on the roll, and merging them would get one of the two
answered wrongly.
"""
import os
import sys

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(HERE, "src"))
import workorders  # noqa: E402


def main():
    a = workorders.file_order(
        code="SLUG_CAP_MADE_A_304_ENTRY_SOURCE_UNFINDABLE",
        what=(
            "A 60-CHARACTER SLUG CAP HAS DETACHED A 304-ENTRY SOURCE FROM ITS OWN ROLL ROW, and "
            "this is Hard Rule 0 arriving through the identity of a file rather than through the "
            "length of a list. The roll row 'Who Framed Roger Rabbit (incl. all content from its "
            "associated crossover-toon IPs)' slugs to 79 characters: "
            "'who-framed-roger-rabbit-incl-all-content-from-its-associated-crossover-toon-ips'. "
            "The record on disk is 'who-framed-roger-rabbit-incl-all-content-from-its-associated' "
            "-- exactly 60 characters, the cap. So the roll row is NOT missing and the record is "
            "NOT orphaned in the sense first reported: the two simply cannot find each other, and "
            "any resync, gating or generation step that slugs the roll name to locate a record "
            "concludes the source has none. 304 catalogued entries are invisible that way. The "
            "same sweep independently found that catalogue_aurora.slug() truncates at 60 while "
            "ingest_doc.slug() does not truncate at all, so two slug functions in one tree "
            "disagree about identity -- which is how cache keys and record names collide or "
            "diverge. FIXING THE CAP DOES NOT FIX THIS FILE: the record already on disk keeps its "
            "truncated name, so a rename (or an alias) is needed as well, and renaming a "
            "canonical record is a data change that wants a decision rather than a script. Note "
            "the record IS covered by canon_backup as of this shift, so the rename is now "
            "reversible."),
        handler="RUN", severity="MAJOR",
        where="src/catalogue_aurora.py slug() + data/records/who-framed-roger-rabbit-*.json",
        evidence={
            "roll_row": "Who Framed Roger Rabbit (incl. all content from its associated "
                        "crossover-toon IPs)",
            "full_slug_length": 79,
            "record_filename_length": 60,
            "entries_made_invisible": 304,
            "cap_location": "catalogue_aurora.slug()",
            "inconsistent_sibling": "ingest_doc.slug() is uncapped",
            "roll_row_missing": False,
            "backed_up_now": "yes, canon_backup covers data/records/*.json as of 2026-08-27"},
        found_by="maintenance-2026-08-27 direct measurement (sharpens sweep36-batch06)")
    print("filed:", a["id"], a["code"])

    b = workorders.file_order(
        code="BONE_JEFF_SMITH_HAS_NO_ROLL_ROW_AT_ALL",
        what=(
            "data/records/bone-jeff-smith.json holds 86 catalogued entries and there is NO roll "
            "row for it under any spelling -- searching all 215 rows of SWEEP_ROLL.json for "
            "'bone' returns nothing. Unlike the Roger Rabbit case filed beside this one, this is "
            "not a slug mismatch: the row is genuinely absent. Two possibilities and they need "
            "different answers. Either the source was catalogued without ever being added to the "
            "Acquisitions Roll -- in which case whether it belongs there is a curatorial "
            "decision, per Hard Rule 2 -- or its row was lost when SWEEP_ROLL.json was destroyed "
            "TWICE on 2026-08-26 and reconstructed from the records plus two dated owner rulings, "
            "in which case restoring it is repair rather than judgement. The reconstruction is at "
            "state/backups/SWEEP_ROLL.json.reconstructed-20260826 and should settle which. Filed "
            "at OWNER because adding a source to the roll is not a maintenance run's call, and "
            "because 86 entries are meanwhile invisible to downstream gating."),
        handler="OWNER", severity="MAJOR",
        where="data/records/bone-jeff-smith.json vs data/SWEEP_ROLL.json",
        evidence={"entries_at_risk": 86,
                  "roll_rows_searched": 215,
                  "matches_for_bone": 0,
                  "not_a_slug_mismatch": True,
                  "check_against": "state/backups/SWEEP_ROLL.json.reconstructed-20260826",
                  "related_incident": "SWEEP_ROLL.json destroyed twice, 2026-08-26"},
        found_by="maintenance-2026-08-27 direct measurement (sharpens sweep36-batch06)")
    print("filed:", b["id"], b["code"])

    workorders.resolve(
        "e26cb69d77fb",
        how=("Superseded by two sharper orders after direct measurement, because the original "
             "diagnosis was right about the symptom and wrong about the cause for the larger "
             "half. Measured: TWO records have no matching roll row, 390 entries between them, "
             "and they are different faults. (1) who-framed-roger-rabbit... (304 entries) DOES "
             "have a roll row -- its full slug is 79 chars and the record filename is that slug "
             "cut to exactly 60, the catalogue_aurora.slug() cap, so the row and the record "
             "cannot find each other; filed as a Hard Rule 0 code defect. (2) bone-jeff-smith "
             "(86 entries) genuinely has no row under any spelling; filed at OWNER as a "
             "curatorial question, with the 2026-08-26 roll reconstruction named as the way to "
             "tell 'never rolled' from 'row lost in the incident'. The underlying observation "
             "that resync_roll iterates the roll and therefore cannot see a record absent from "
             "it remains true and is carried in both successors."))
    print("closed e26cb69d77fb (superseded)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
