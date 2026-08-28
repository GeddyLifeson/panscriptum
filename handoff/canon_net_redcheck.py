"""Watch the staged canon_backup net go RED, then green. A net nobody has seen refuse is not
evidence of anything -- CLAUDE.md's rule, applied to the net this run is asking to merge.

Three runs of the same predicate:
  1. against the real `canon_backup` -- must be GREEN (the guard is in effect);
  2. against a build whose verification step is removed -- must be RED;
  3. against a build whose empty-set refusal is removed -- must be RED.

If arm 2 or 3 comes out green, the net is furniture and must not be merged.
"""
import os
import shutil
import sys
import tempfile
import zipfile

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(HERE, "src"))
import canon_backup as CB  # noqa: E402


def predicate():
    """The staged net's body, verbatim in behaviour. -> True when the guard holds."""
    saved_root, saved_files, saved_dirs = CB.ROOT, CB.CANON_FILES, CB.CANON_DIRS
    saved_here = CB.HERE
    d = tempfile.mkdtemp(prefix="drill_canon_")
    try:
        CB.ROOT = os.path.join(d, "snaps")

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

        src = os.path.join(d, "data")
        os.makedirs(src, exist_ok=True)
        with open(os.path.join(src, "ONE.json"), "w", encoding="utf-8") as fh:
            fh.write('{"real": 1}')
        CB.HERE = d
        CB.CANON_FILES, CB.CANON_DIRS = ("data/ONE.json",), ()
        real_zip = zipfile.ZipFile

        class LyingZip(zipfile.ZipFile):
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
        left = [f for f in os.listdir(CB.ROOT) if f.startswith("canon-")] \
            if os.path.isdir(CB.ROOT) else []
        return corrupt_refused and not left
    finally:
        CB.ROOT, CB.CANON_FILES, CB.CANON_DIRS = saved_root, saved_files, saved_dirs
        CB.HERE = saved_here
        shutil.rmtree(d, ignore_errors=True)


def main():
    print("arm 1  real code                 ->", "GREEN" if predicate() else "RED")

    real_snapshot = CB.snapshot

    def no_verification(stamp=None):
        """The guard removed: write the archive, never read it back."""
        os.makedirs(CB.ROOT, exist_ok=True)
        items = CB.members()
        if not items:
            raise RuntimeError("no canonical files found -- refusing to write an empty snapshot")
        final = os.path.join(CB.ROOT, "canon-unverified.zip")
        with zipfile.ZipFile(final, "w") as z:
            for rel, p in items:
                z.write(p, arcname=rel)
        return final, {"files": len(items), "bytes": 0}

    CB.snapshot = no_verification
    print("arm 2  verification removed      ->", "GREEN" if predicate() else "RED")

    def no_empty_check(stamp=None):
        """The other guard removed: an empty canonical set writes a snapshot happily."""
        os.makedirs(CB.ROOT, exist_ok=True)
        final = os.path.join(CB.ROOT, "canon-empty.zip")
        with zipfile.ZipFile(final, "w") as z:
            for rel, p in CB.members():
                z.write(p, arcname=rel)
        return final, {"files": 0, "bytes": 0}

    CB.snapshot = no_empty_check
    print("arm 3  empty-set refusal removed ->", "GREEN" if predicate() else "RED")

    CB.snapshot = real_snapshot
    print("arm 4  restored real code        ->", "GREEN" if predicate() else "RED")
    print("\nA merge is justified only if this reads GREEN, RED, RED, GREEN.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
