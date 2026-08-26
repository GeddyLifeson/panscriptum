"""SUPPRESSIONS — the exceptions a detector is allowed, each with a reason and an expiry.

WHY THIS REPLACES INLINE MARKERS. The secret scanner needed exceptions within minutes of being
written: its own drill fixtures and the documentation describing them look exactly like leaks,
because a scanner cannot tell a fixture from a credential and should not try. The first answer
was an inline `# SECRET-FIXTURE` comment, and that answer has three faults that only show up
later:

  * it is INVISIBLE. A suppressed finding vanishes from the report entirely, so nobody can audit
    what is being waved through, or notice that the list has quietly grown.
  * it never EXPIRES. A marker added for a fixture that was deleted six months ago still silences
    that line, and nothing ever revisits it.
  * it carries no REASON that a reviewer can weigh. "SECRET-FIXTURE" asserts a conclusion; it
    does not give the evidence for it.

The tools that live with this at scale all landed on the same shape. Trivy's `.trivyignore.yaml`
requires an id, a path, a `statement` and an `expired_at`, and `--show-suppressed` still LISTS
suppressed findings rather than dropping them. Prowler's mutelist keeps muted findings in the
output marked `MUTED`, and its docs say plainly that muting "does not resolve the underlying
issue". Falco lets a rule declare structured `exceptions:` on named fields instead of loosening
the rule's condition for everyone.

So: suppressions are DATA, they carry a reason and an expiry, an expired or dangling one is a
FAULT rather than a silent pass, and a suppressed finding is still reported -- just marked.

THE RULE THAT MATTERS MOST: a suppression narrows a detector for a NAMED case. It never turns a
detector off. If an exception is broad enough to hide a class of real findings, the detector is
wrong and should be fixed instead.
"""
import json
import os
import sys
import time

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import silence  # noqa: E402

FILE = os.path.join(HERE, "data", "SUPPRESSIONS.json")
# A suppression may not outlive review. Long enough to be practical, short enough that the list
# is re-read a few times a year rather than never.
DEFAULT_TTL_DAYS = 180


def _load():
    try:
        with open(FILE, encoding="utf-8") as f:
            d = json.load(f)
        return d if isinstance(d, list) else []
    except FileNotFoundError:
        return []
    except Exception:
        silence.note("suppressions.py:load")
        return []


def _land(rows):
    """Write the list. -> True if it LANDED on disk, False if the rename was refused.

    GATE ON THE WRITE. `silence.replace_retry` returns whether the rename succeeded and, by its
    own docstring, deliberately never raises on persistent denial ("the caller's write lands next
    round") -- which is right for a metrics file and wrong for this one. This function discarded
    that verdict, so under the WinError 5 collision that helper exists for (a reader holding the
    target open; taken an assay worker down once already, 2026-08-23) `add()` returned a row that
    looked committed while `SUPPRESSIONS.json` was untouched. `active()` re-reads from disk every
    call and has no cache, so the very next read would not see it -- and in this module that
    failure mode points the wrong way twice: the operator believes an exemption is recorded and
    reviewable when nothing is, and the reason they wrote is lost with it. `repass_bands.py`
    gates on the identical verdict for the identical reason (run #25).
    """
    os.makedirs(os.path.dirname(FILE), exist_ok=True)
    tmp = FILE + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(rows, f, indent=1, ensure_ascii=False)
    return silence.replace_retry(tmp, FILE)


def add(detector, path_glob, reason, added_by="owner", ttl_days=DEFAULT_TTL_DAYS):
    """Record one narrow exception. A reason is REQUIRED and is not decoration."""
    if not reason or len(str(reason).strip()) < 12:
        raise ValueError("a suppression needs a reason in words -- what is this, and why is it "
                         "not what the detector thinks it is?")
    rows = [r for r in _load()
            if not (r.get("detector") == detector and r.get("path") == path_glob)]
    rows.append({"detector": str(detector), "path": str(path_glob),
                 "reason": str(reason).strip()[:300], "added_by": str(added_by),
                 "added_at": time.time(),
                 "expires_at": time.time() + float(ttl_days) * 86400})
    if not _land(rows):
        # REFUSED IS NOT ADDED. Returning the row here would tell the caller a detector has been
        # narrowed when it has not been -- the one lie this module must never tell, since the
        # next scan will report the finding the operator believes they waived.
        raise IOError("SUPPRESSIONS.json could not be written (rename refused); the suppression "
                      "for %s on %s was NOT recorded -- try again" % (detector, path_glob))
    return rows[-1]


def active(detector=None):
    """-> [suppressions] that have not expired."""
    now = time.time()
    rows = [r for r in _load() if (r.get("expires_at") or 0) > now]
    if detector:
        rows = [r for r in rows if r.get("detector") == detector]
    return rows


def suppressed(detector, path):
    """-> the suppression covering this finding, or None. Fnmatch on the repo-relative path.

    CASE-SENSITIVE ON PURPOSE (`fnmatchcase`, never `fnmatch`). `fnmatch.fnmatch` runs both
    operands through `os.path.normcase` first, which on Windows -- the platform this ships on --
    lowercases them, so `data/fixtures/*` would also swallow findings under `DATA/Fixtures/`.
    That is the silent widening this module's header forbids in capitals: a suppression narrows a
    detector for a NAMED case, and a case nobody wrote down is not a named case. The stricter
    match can only ever fail SHUT -- a pattern whose casing does not match the tree stops
    matching and the finding is reported, which is the direction an exemption should fail in.
    `problems()` uses `fnmatchcase` for the same reason, so a mis-cased pattern surfaces there as
    DANGLING rather than quietly covering files it was never reviewed against.
    """
    import fnmatch
    rel = str(path).replace(os.sep, "/")
    for r in active(detector):
        if fnmatch.fnmatchcase(rel, r.get("path", "")):
            return r
    return None


def problems():
    """-> [problems]. An expired or dangling suppression is a FAULT, not a silent pass.

    Dangling matters as much as expired: a suppression whose path no longer exists is a rule
    narrowed for a case that is gone, and the next file to land on that path inherits a hole
    nobody chose. Trivy and Prowler both validate this in CI for the same reason.
    """
    import fnmatch
    import glob
    now = time.time()
    out = []
    for r in _load():
        if (r.get("expires_at") or 0) <= now:
            out.append("EXPIRED: %s on %s (%s) -- re-justify it or delete it"
                       % (r.get("detector"), r.get("path"), r.get("reason", "")[:60]))
            continue
        pat = r.get("path", "")
        if any(ch in pat for ch in "*?["):
            hits = [p for p in glob.glob(os.path.join(HERE, "**", "*"), recursive=True)
                    if fnmatch.fnmatchcase(os.path.relpath(p, HERE).replace(os.sep, "/"), pat)]
            if not hits:
                out.append("DANGLING: %s on %s matches nothing on disk"
                           % (r.get("detector"), pat))
        elif not os.path.exists(os.path.join(HERE, pat.replace("/", os.sep))):
            out.append("DANGLING: %s on %s does not exist" % (r.get("detector"), pat))
    return out


def main():
    import argparse
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--list", action="store_true",
                    help="the active suppressions (the default when no flag is given)")
    ap.add_argument("--check", action="store_true", help="expired or dangling entries")
    a = ap.parse_args()
    # `--list` used to be parsed and never read, so `--check --list` silently answered only the
    # first question and dropped the second. Refuse the pair rather than pick one: "what is
    # waived" and "what is rotten" are different questions, and an operator who asked both and
    # got one answer has no way to tell which.
    if a.check and a.list:
        ap.error("--check and --list are separate questions; ask one at a time")
    if a.check:
        probs = problems()
        for p in probs:
            print("  " + p)
        print("\n%d suppression problem(s)" % len(probs))
        return 1 if probs else 0
    rows = active()
    if not rows:
        print("no active suppressions")
        return 0
    for r in rows:
        days = (r.get("expires_at", 0) - time.time()) / 86400.0
        print("  %-22s %-34s expires in %4.0fd  %s"
              % (r.get("detector"), r.get("path")[:34], days, r.get("reason", "")[:44]))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
