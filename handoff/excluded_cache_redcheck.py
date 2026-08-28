"""Prove the excluded-source cache exemption, in BOTH directions, with a control.

The exemption says: an empty feats cache belonging to a host whose sources have ALL been excluded
from the roll is not a fault. That is the durable fix for the 24-hour flicker -- the quarantine
exemption beside it is TTL-gated, so every time a quarantine lapsed the preflight went red again
on a host nobody was ever going to act on.

Three arms, and the second is the one that stops this being a rubber stamp:

  1. all sources on the host excluded          -> EXCUSED (no fault reported)
  2. one live source still bound to the host   -> STILL A FAULT (the cache is load-bearing)
  3. the roll cannot be read                   -> nothing excused, fault reported as before

Plus the control: with the exemption disabled, arm 1 must report a fault.

Driven against scratch directories throughout. The live data/ tree is never written.
"""
import json
import os
import shutil
import sys
import tempfile

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(HERE, "src"))
import cachekey as CK  # noqa: E402
import health as H  # noqa: E402
import roll as R  # noqa: E402

HOST = "example-excluded.fandom.com"


def build(tmp, rows):
    """A scratch tree with one host directory of 30 empty cache entries."""
    os.makedirs(os.path.join(tmp, "data", "feats", CK.host_dir(HOST)), exist_ok=True)
    d = os.path.join(tmp, "data", "feats", CK.host_dir(HOST))
    for i in range(30):
        with open(os.path.join(d, "e%02d.json" % i), "w", encoding="utf-8") as fh:
            fh.write("{}")                      # under EMPTY_BYTES -> reads as empty
    with open(os.path.join(tmp, "data", "WIKI_HOSTS.json"), "w", encoding="utf-8") as fh:
        json.dump({r["name"]: HOST for r in rows}, fh)
    with open(os.path.join(tmp, "data", "SWEEP_ROLL.json"), "w", encoding="utf-8") as fh:
        json.dump(rows, fh)
    return tmp


def run(rows, break_roll=False):
    """-> (faults, excused_printed). Redirects health and roll at their module roots."""
    tmp = tempfile.mkdtemp(prefix="exccache_")
    saved_h, saved_r = H.HERE, R.ROLL
    try:
        build(tmp, rows)
        H.HERE = tmp
        R.ROLL = os.path.join(tmp, "data", "SWEEP_ROLL.json")
        if break_roll:
            with open(R.ROLL, "w", encoding="utf-8") as fh:
                fh.write("{ not json")
        import io
        import contextlib
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            out = H.check_caches()
        faults = [o for o in out if CK.host_dir(HOST) in o[0]]
        return faults, buf.getvalue()
    finally:
        H.HERE, R.ROLL = saved_h, saved_r
        shutil.rmtree(tmp, ignore_errors=True)


def main():
    all_excluded = [{"name": "Only Source", "status": R.OUT_OF_SCOPE, "note": "n"}]
    mixed = [{"name": "Only Source", "status": R.OUT_OF_SCOPE, "note": "n"},
             {"name": "Live Source", "status": "catalogued"}]

    f1, p1 = run(all_excluded)
    a1 = not f1 and "source excluded from the roll" in p1
    print("arm 1  every source excluded -> excused, not a fault  ->", "PASS" if a1 else "FAIL")

    f2, _ = run(mixed)
    a2 = bool(f2)
    print("arm 2  a live source shares the host -> STILL a fault  ->", "PASS" if a2 else "FAIL")

    f3, _ = run(all_excluded, break_roll=True)
    a3 = bool(f3)
    print("arm 3  unreadable roll -> nothing excused              ->", "PASS" if a3 else "FAIL")

    real = R.OUT_OF_SCOPE
    R.OUT_OF_SCOPE = "__never_matches__"       # the exemption can no longer recognise anything
    f4, _ = run(all_excluded)
    R.OUT_OF_SCOPE = real
    a4 = bool(f4)
    print("arm 4  CONTROL: exemption disabled                     ->",
          "RED as required" if a4 else "STILL GREEN -- the exemption is not load-bearing")

    ok = a1 and a2 and a3 and a4
    print("\nVERDICT:", "the exclusion exemption holds and is load-bearing" if ok
          else "NOT PROVEN -- do not rely on this")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
