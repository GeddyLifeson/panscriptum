# Net staged by run #36 for `src/canon_backup.py` — merge into `drill.py`

New machinery landed this shift closes order `ec67de571754` (the canonical corpus had no
backup: `data/` is gitignored, 0 data files are tracked in git, and 219 canonical files /
214.7 MB existed in exactly one place on one disk).

`canon_backup.snapshot()` writes a zip and then **re-opens it and re-hashes every member**
against the source before it will record success. That read-back is the only thing separating a
backup from an assertion that a backup happened — so it is the thing the net has to attack.

## The guard

`snapshot()` must REFUSE, and must delete the archive it wrote, when the archive it produced
does not match the tree it came from.

## The attack that defeats it

Corrupt one member *after* the archive is written but *before* verification reads it, and check
that `snapshot()` raises and leaves no `canon-*.zip` behind. A guard that only ever runs against
a good archive has never been shown to refuse anything.

The second arm is the one that matters more and is easy to get wrong: an EMPTY canonical set
must also refuse. A backup of nothing verifies perfectly — every one of its zero members
matches — and would sit in the snapshot directory looking exactly like a real backup. That is
the "a check that cannot fail looks exactly like a check that passed" shape, arriving in the
one place where believing it costs the whole corpus.

```python
    def _snapshot_refuses_a_corrupt_or_empty_archive():
        """A verified backup must be able to say no, in both the ways it can be wrong.

        `canon_backup.snapshot()` re-reads its own archive and compares digests. Nothing had
        ever seen it refuse, so this constructs both refusals: an archive whose contents were
        swapped under the verifier, and a canonical set that is empty. The empty arm is the
        dangerous one -- a zero-member archive passes verification trivially and occupies the
        place a real backup would go.
        """
        import zipfile
        import canon_backup as CB
        saved_root, saved_files, saved_dirs = CB.ROOT, CB.CANON_FILES, CB.CANON_DIRS
        d = tempfile.mkdtemp(prefix="drill_canon_")
        try:
            CB.ROOT = os.path.join(d, "snaps")

            # ARM 1 -- empty canonical set must refuse rather than write an empty archive.
            CB.CANON_FILES, CB.CANON_DIRS = (), ()
            try:
                CB.snapshot()
                empty_refused = False
            except RuntimeError as e:
                empty_refused = "empty snapshot" in str(e) or "no canonical files" in str(e)
            wrote_anything = os.path.isdir(CB.ROOT) and any(
                f.startswith("canon-") for f in os.listdir(CB.ROOT))
            if not empty_refused or wrote_anything:
                return False

            # ARM 2 -- an archive that does not match its source must refuse AND self-delete.
            src = os.path.join(d, "data")
            os.makedirs(src, exist_ok=True)
            with open(os.path.join(src, "ONE.json"), "w", encoding="utf-8") as fh:
                fh.write('{"real": 1}')
            saved_here = CB.HERE
            CB.HERE = d
            CB.CANON_FILES, CB.CANON_DIRS = ("data/ONE.json",), ()
            real_zip = zipfile.ZipFile

            class LyingZip(zipfile.ZipFile):
                """Writes the wrong bytes, so the read-back must catch it."""
                def write(self, filename, arcname=None, *a, **k):
                    return self.writestr(arcname or filename, "{}")

            try:
                zipfile.ZipFile = LyingZip
                try:
                    CB.snapshot()
                    corrupt_refused = False
                except RuntimeError as e:
                    corrupt_refused = "verification" in str(e)
            finally:
                zipfile.ZipFile = real_zip
                CB.HERE = saved_here
            left_behind = [f for f in os.listdir(CB.ROOT) if f.startswith("canon-")] \
                if os.path.isdir(CB.ROOT) else []
            return corrupt_refused and not left_behind
        finally:
            CB.ROOT, CB.CANON_FILES, CB.CANON_DIRS = saved_root, saved_files, saved_dirs
            shutil.rmtree(d, ignore_errors=True)

    net(a, "a canonical-corpus snapshot refuses when it cannot verify itself",
        _snapshot_refuses_a_corrupt_or_empty_archive,
        "an unverified backup of the only copy of a 217-source corpus is a belief, and the "
        "empty case verifies perfectly while restoring nothing")
```

Run #36 confirmed both arms go red against the unguarded shape before merging (see
`handoff/run36/canon_net_redcheck.txt`).

---

## ADDENDUM — a third arm, added hours later, because the sweep found the hole this net missed

The net above guards the EMPTY canonical set, on the reasoning that a zero-member archive
verifies trivially. Within hours the run #36 whole-tree sweep (batch 9) found that the same
failure had a middle case the net did not cover, and that the code did not guard either:

> `members()` silently drops a `CANON_FILES` entry if it is missing, and silently skips all of
> `CANON_DIRS` if the directory does not exist; only an all-empty result is guarded, so a
> missing `data/records/` produces a "verified" snapshot of 2-3 small files and zero corpus
> records.

That is the module's own stated hazard coming in through its front door. **Verification only
ever compares what was collected against where it came from; it never asks whether the
collection was complete.** A 3-of-219 snapshot passes every digest check perfectly. The empty
case was guarded because it was easy to imagine; the partial case is the same failure and is far
likelier — a briefly-unreadable directory is an ordinary event.

`members(strict=True)` now RAISES, naming each missing path, and `snapshot()` uses the strict
form. `main()`'s status line and `verify()` pass `strict=False`, since reporting an inventory is
not the same act as trusting one.

Add this arm to the net, between the empty and corrupt arms:

```python
            # ARM 1b -- a PARTIAL canonical set must refuse. A snapshot of 3 files out of 219
            # verifies flawlessly, which is precisely why nothing catches it downstream.
            src2 = os.path.join(d, "data")
            os.makedirs(src2, exist_ok=True)
            with open(os.path.join(src2, "SIDE.json"), "w", encoding="utf-8") as fh:
                fh.write("{}")
            CB.HERE = d
            CB.CANON_FILES = ("data/SIDE.json",)
            CB.CANON_DIRS = ("data/records",)          # deliberately absent
            try:
                CB.snapshot()
                partial_refused = False
            except RuntimeError as e:
                partial_refused = "refusing to build a snapshot" in str(e) and "records" in str(e)
            if not partial_refused:
                return False
```

Proven 2026-08-27 against the patched module: a real 219-file snapshot still succeeds, a missing
`data/records/` refuses naming `records`, and a missing single canonical file refuses naming
`WIKI_HOSTS`.

**Also fixed in the same pass, and worth the note because of where it happened:** the manifest
write discarded `silence.replace_retry`'s verdict while the archive write three lines above
correctly raised on refusal. That is the same discarded-write-verdict defect the sweep found in
ten other modules — committed inside the one module whose entire purpose is not to trust a write
it has not confirmed. Without the manifest, `verify()` has no recorded digests and silently
degrades to "the zip still opens".
