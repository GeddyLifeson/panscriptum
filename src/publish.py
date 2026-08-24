#!/usr/bin/env python3
"""
PUBLISH — the project and its instrument panel, on GitHub, without opening this machine to anyone.

THE PROBLEM WITH THE LOCAL DASHBOARD
------------------------------------
`dashboard.py` serves on 127.0.0.1 and reads the project's files directly, which is exactly right
for a machine you are sitting at and useless from anywhere else. The obvious fixes are all bad:
port-forwarding exposes a machine, a tunnel hands a third party a URL pointing inside this house,
and neither is worth it to look at a progress bar.

WHAT THIS DOES INSTEAD
----------------------
Pushes a SNAPSHOT. The page becomes static and lives on GitHub Pages; the numbers become a small
JSON file it fetches from beside itself; and this script writes that file and commits it on a
timer. Nothing listens, nothing is exposed, and it works on a phone.

WHY IT PUBLISHES FROM A COPY
----------------------------
Two reasons, and neither is tidiness.

Norton locks newly-written objects under the project directory, so `git add` there fails
intermittently with `Permission denied` on `.git/objects`. Fighting an antivirus for the right to
commit is not a good use of an afternoon.

More importantly, a publish that COPIES A NAMED SUBSET into a clean directory cannot accidentally
include something. A `.gitignore` in the live tree is one edit away from publishing 489MB of
third-party wiki text, and the internet indexes fast and forgets slowly. Here the default is
exclusion: a file travels because it is named, not because nobody remembered to exclude it.

The snapshot is scrubbed as well. It carries bucket names, quota counts, progress numbers and
finding summaries; it carries no keys, and `_scrub` refuses anything credential-shaped even if a
future edit puts one in the state dict by accident.
"""
import argparse
import json
import os
import re
import shutil
import subprocess
# Windows: a child process spawned from a windowless (pythonw) parent ALLOCATES ITS OWN
# CONSOLE unless told not to. Under the old console launcher every subprocess inherited a
# hidden console and nobody noticed; under pythonw each powershell/wmic/python child
# flashed a black window -- dozens per cycle across the stack. Passed on every spawn.
_NO_WIN = getattr(subprocess, "CREATE_NO_WINDOW", 0)

import sys
import time

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(HERE, "src")
sys.path.insert(0, SRC)
import silence                                                          # noqa: E402

_BAD_CHARS = (chr(8), chr(11), chr(12), chr(7))
if any(c in open(os.path.abspath(__file__), encoding="utf-8").read() for c in _BAD_CHARS):
    raise SystemExit(__file__ + ": a regex escape was eaten in transit.")

SITE = os.environ.get("PANSCRIPTUM_EXPORT") or os.path.join(
    os.environ.get("TEMP") or os.path.expanduser("~"), "panscriptum-export")
DOCS = os.path.join(SITE, "docs")
STATE_JSON = os.path.join(DOCS, "state.json")
PAGE = os.path.join(DOCS, "index.html")

# What travels. Everything else -- the mined corpus, the run state, the logs -- is derived from
# these and stays home.
COPY_DIRS = ("src", "prompts", "reference", "registry_terminal", "handoff")
COPY_FILES = ("CLAUDE.md", "README.md", "config.yaml", "requirements.txt",
              "WATCH.md", "STATUS.md",
              # the maintenance-pass ledgers: run journal, bug paper-trail, priority
              # queue, and the framework the scheduled super-supervisor reads first
              "HANDOFF.md", "BUGS.md", "NEXT_STEPS.md", "MAINTENANCE.md")
# Backups and scratch copies never travel. The .pre* family is session backups of live modules
# -- seven of them were sitting in src/ and being published to the PUBLIC repo because this
# tuple only knew about two suffixes.
SKIP_SUFFIX = (".pyc", ".presilence", ".prebandfix", ".precapfix", ".prefix", ".prepool",
               ".preprobe", ".prewiden", ".prewindow", ".bak", ".tmp", ".orig")

_SECRET = re.compile(
    r"(sk-[A-Za-z0-9_\-]{16,}|gsk_[A-Za-z0-9]{20,}|AIza[A-Za-z0-9_\-]{20,}|"
    r"github_pat_[A-Za-z0-9_]{20,}|ghp_[A-Za-z0-9]{20,}|hf_[A-Za-z0-9]{20,}|"
    r"xai-[A-Za-z0-9]{20,}|csk-[A-Za-z0-9]{20,})")


def _scrub(obj):
    """Walk the snapshot and redact anything credential-shaped.

    Not a substitute for building the snapshot out of named fields -- it is the second lock, for
    the day somebody adds a field carrying a provider error message with a key in it, which is
    exactly how keys get published.
    """
    if isinstance(obj, dict):
        return {k: _scrub(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_scrub(v) for v in obj]
    if isinstance(obj, str):
        return _SECRET.sub("[redacted]", obj)
    return obj


def snapshot():
    import dashboard as D
    s = D.state()
    try:
        import standards as ST
        s["standards"] = ST.check(s)
    except Exception:
        silence.note("publish.py:standards")
    s["generated"] = time.strftime("%Y-%m-%dT%H:%M:%S")
    return _scrub(s)


def git(*args, check=True):
    # Two credential failures live in the environment, not the repo, and both are shed here.
    #
    # 1. GITHUB_TOKEN: assistant/CI sessions export a fine-grained PAT that gh prefers over the
    #    user's own keyring login -- and that PAT has no write access to this repo, so every
    #    push under it is a 403 reading "Permission to ... denied to GeddyLifeson", which looks
    #    like an account problem and is actually an environment variable. The keyring account
    #    (gho_ token) pushes fine. Remove the override and gh falls back to the login that works.
    # 2. PATH: the supervisor's children inherit a logon PATH that does not always carry the
    #    gh-cli directory, and git's credential call then fails with "gh.exe: No such file or
    #    directory" from sh. The publish loop logged that every ten minutes -- the remote fell
    #    122 commits behind while "synced N files" kept printing above it.
    env = {k: v for k, v in os.environ.items() if k not in ("GITHUB_TOKEN", "GH_TOKEN")}
    gh_dir = os.path.join(os.environ.get("LOCALAPPDATA", ""), "gh-cli", "bin")
    if os.path.isdir(gh_dir) and gh_dir not in env.get("PATH", ""):
        env["PATH"] = env.get("PATH", "") + os.pathsep + gh_dir
    r = subprocess.run(["git"] + list(args), cwd=SITE, capture_output=True,
                       text=True, encoding="utf-8", errors="replace", env=env, creationflags=_NO_WIN)
    if check and r.returncode != 0:
        raise RuntimeError("git " + " ".join(args) + ": "
                           + (r.stderr or r.stdout).strip()[:220])
    return (r.stdout or "").strip()


def sync_tree():
    """Refresh the export copy from the live project. Named files only, never a whole-tree copy."""
    os.makedirs(DOCS, exist_ok=True)
    n = 0
    for d in COPY_DIRS:
        root = os.path.join(HERE, d)
        if not os.path.isdir(root):
            continue
        for base, dirs, files in os.walk(root):
            dirs[:] = [x for x in dirs if x != "__pycache__"]
            for f in files:
                if f.endswith(SKIP_SUFFIX):
                    continue
                srcp = os.path.join(base, f)
                dstp = os.path.join(SITE, os.path.relpath(srcp, HERE))
                os.makedirs(os.path.dirname(dstp), exist_ok=True)
                # rsync-style short-circuit: this loop was copying 139 files / 14.5MB every
                # ten minutes unconditionally (~2GB/day of writes for Norton to re-scan) when
                # a normal sync changes a handful. copy2 preserves mtime, so equal
                # mtime+size means the destination already IS this file.
                try:
                    st_s, st_d = os.stat(srcp), os.stat(dstp)
                    if st_s.st_mtime == st_d.st_mtime and st_s.st_size == st_d.st_size:
                        continue
                except OSError:
                    pass
                shutil.copy2(srcp, dstp)
                n += 1
    for f in COPY_FILES:
        srcp = os.path.join(HERE, f)
        if os.path.exists(srcp):
            shutil.copy2(srcp, os.path.join(SITE, f))
            n += 1
    # Mark the copy AS a copy. Every module imports silence, which refuses to run from a tree
    # carrying this marker -- so a command aimed at the wrong directory fails loudly instead of
    # succeeding into nothing.
    with open(os.path.join(SITE, ".is-export-copy"), "w", encoding="utf-8") as f:
        f.write("Published copy of the Panscriptum. The project lives elsewhere." + chr(10))
    return n


def render_page():
    """The published page IS the local page, with its data source swapped.

    `dashboard.PAGE` stays the single source of truth for the interface. A second copy would
    drift, and the drift would be invisible until somebody noticed the phone showing a panel the
    laptop did not have. So this generates: same markup, `./state.json` instead of the live
    endpoint, a slower refresh, and a line saying the numbers are a snapshot -- which a static
    page owes its reader and a live one does not.
    """
    import dashboard as D
    html = D.PAGE.replace("'/api/state'", "'./state.json'")
    html = html.replace("setInterval(tick,5000)", "setInterval(tick,30000)")
    html = html.replace(
        "Refreshes every 5 seconds.",
        "This is a published SNAPSHOT: the machine pushes it on a timer, so the timestamp above "
        "is when the numbers were true, not now. The live panel is "
        "<code>python src/dashboard.py</code> on the machine itself.")
    os.makedirs(DOCS, exist_ok=True)
    with open(PAGE, "w", encoding="utf-8") as f:
        f.write(html)
    return PAGE


def ensure_site(remote=None):
    os.makedirs(DOCS, exist_ok=True)
    if not os.path.isdir(os.path.join(SITE, ".git")):
        git("init", "-q")
        git("checkout", "-q", "-B", "main")
    with open(os.path.join(SITE, ".gitignore"), "w", encoding="utf-8") as f:
        f.write("__pycache__/" + chr(10) + "*.pyc" + chr(10) + "*.presilence" + chr(10))
    # Pages serves from /docs on the default branch; .nojekyll stops Jekyll hiding anything.
    with open(os.path.join(DOCS, ".nojekyll"), "w", encoding="utf-8") as f:
        f.write("")
    if remote:
        git("remote", "remove", "origin", check=False)
        git("remote", "add", "origin", remote)
    return SITE


def write(state=None):
    os.makedirs(DOCS, exist_ok=True)
    data = state if state is not None else snapshot()
    tmp = STATE_JSON + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=1)
    os.replace(tmp, STATE_JSON)
    return STATE_JSON


def push(message=None):
    """Commit and push, quietly doing nothing when nothing changed.

    FETCH-REBASE FIRST. Two writers publish into this tree (the standing loop and whatever
    session is working), and a bare push from the second one fails `! [rejected] main -> main
    (fetch first)` -- run #5 counted five such silent-ish failures in one morning. Rebasing our
    commit onto whatever landed keeps both writers' work; a rebase that conflicts is aborted
    and reported, never forced -- the next loop retries on a fresh read of the tree."""
    if not os.path.isdir(os.path.join(SITE, ".git")):
        raise RuntimeError("export is not a repo yet -- run --init --remote first")
    git("add", "-A")
    porcelain = git("status", "--porcelain")
    if not porcelain:
        return False
    # A history of identical "instruments <time>" messages answers no question anybody brings
    # to a history. The message now names what actually moved: which code files, how much of
    # everything else -- derived from the same status the commit is about to record.
    if message:
        stamp = message
    else:
        code, other = [], 0
        for ln in porcelain.splitlines():
            p = ln[3:].strip().strip('"')
            if p.startswith("src/") and p.endswith(".py"):
                code.append(os.path.basename(p)[:-3])
            else:
                other += 1
        parts = []
        if code:
            head = ", ".join(sorted(code)[:6])
            more = f" +{len(code) - 6}" if len(code) > 6 else ""
            parts.append(f"code: {head}{more}")
        if other:
            parts.append(f"{other} data/site file(s)")
        stamp = ("sync " + time.strftime("%Y-%m-%d %H:%M") + " — "
                 + ("; ".join(parts) or "no-op"))
    git("-c", "user.name=panscriptum", "-c", "user.email=noreply@users.noreply.github.com",
        "commit", "-q", "-m", stamp)
    try:
        git("fetch", "-q", "origin")
        git("rebase", "-q", "origin/main")
    except RuntimeError as e:
        try:
            git("rebase", "--abort", check=False)
        except Exception:
            silence.note("publish.py:rebase-abort")
        print("push held: rebase onto origin/main failed (" + str(e)[:120]
              + "); retrying next loop on a fresh tree", file=sys.stderr)
        return False
    git("push", "-q", "-u", "origin", "main")
    return True


def main():
    ap = argparse.ArgumentParser(description="publish the project and its instruments")
    ap.add_argument("--init", action="store_true", help="create the export repo")
    ap.add_argument("--remote", help="git remote URL")
    ap.add_argument("--push", action="store_true", help="commit and push")
    ap.add_argument("--loop", type=float, default=0, help="keep publishing, minutes apart")
    a = ap.parse_args()

    if a.init or a.remote:
        ensure_site(remote=a.remote)
        print("export repo at " + SITE + (("  -> " + a.remote) if a.remote else ""))

    while True:
        try:
            n = sync_tree()
            render_page()
            write()
            print(f"synced {n} files, wrote docs/state.json")
            if a.push:
                print("pushed" if push() else "no change to push")
        except Exception as e:
            silence.note("publish.py:main")
            print(f"publish failed: {type(e).__name__}: {str(e)[:180]}")
        if not a.loop:
            return 0
        time.sleep(a.loop * 60)


if __name__ == "__main__":
    sys.exit(main())
