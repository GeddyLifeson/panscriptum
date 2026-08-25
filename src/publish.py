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

# NEVER fall back to TEMP. This default used to read `os.environ.get("TEMP") or
# expanduser("~")`, and the standing publish loop inherits its environment from whatever
# started the supervisor -- which, on this machine, was a Claude Code session whose TEMP
# points at a per-session scratchpad. So `--loop 10` git-init'd a SECOND export repo inside
# a dead session's temp directory, pointed it at the same remote, and published into it four
# times an hour: run #17 found it **160 commits ahead and 63 behind origin/main**, with a
# state.json 40 minutes fresher than the live page's. Every cycle printed "synced 14 files,
# wrote docs/state.json" and then "push held: rebase onto origin/main failed", which is
# honest about the push and silent about the far worse fact that it was the WRONG TREE --
# the rebase could never succeed, because those 160 commits are a parallel history. The
# public page only ever moved because maintenance runs publish separately with
# PANSCRIPTUM_EXPORT set. A temp directory is never the right home for a repo that has a
# remote and is expected to persist; the home directory is, and is where the real export
# lives. USERPROFILE first because a bash-launched child can carry a HOME that expanduser
# would prefer.
def _is_throwaway(path):
    """True for a path under a temp or per-session scratch directory.

    Deliberately structural, not a match against one machine's paths: any segment named
    temp/tmp, or a `scratchpad` segment, is somewhere a cleaner may reap. A repo that has a
    remote and is expected to accumulate history must never live in one.
    """
    segs = [s.lower() for s in os.path.normpath(path).split(os.sep) if s]
    return any(s in ("temp", "tmp", "scratchpad") for s in segs)


def home_export():
    return os.path.join(os.environ.get("USERPROFILE") or os.path.expanduser("~"),
                        "panscriptum-export")


def export_root(env=None, warn=True):
    """Resolve where the export repo lives, refusing any throwaway directory.

    A function, not an inline expression, so the fallback chain can be tested against a
    synthetic environment instead of only against whatever this process happens to have
    inherited -- which is precisely the thing that hid the fault for as long as it hid.

    The guard is on the RESOLVED path, not on one variable, because run #17 found the fault
    twice in one hour wearing two different faces. First the fallback: `TEMP or expanduser`
    put the export in a dead Claude session's scratchpad. That was corrected -- and the very
    next publish cycle, now printing its destination, went to the SAME scratchpad anyway,
    because `PANSCRIPTUM_EXPORT` is *itself* set to that path in the long-lived supervisor's
    inherited environment (nothing in src/ sets it; the process tree has carried it since
    2026-08-23). Fixing the fallback alone would have been a fix that changed nothing while
    reading as a repair.

    So the explicit variable is honoured, as it must be -- but not into a directory the
    system may delete. Measured when found: 160 commits ahead of origin/main, 63 behind, a
    parallel history whose rebase could never land, publishing four times an hour into a
    place nobody would look.
    """
    e = os.environ if env is None else env
    named = e.get("PANSCRIPTUM_EXPORT")
    if named and not _is_throwaway(named):
        return named
    fallback = os.path.join(e.get("USERPROFILE") or os.path.expanduser("~"),
                            "panscriptum-export")
    if named and warn:
        # Loud, every cycle, and never silent: this is the exact class of default whose
        # firing must be reported rather than absorbed.
        print("publish: REFUSING PANSCRIPTUM_EXPORT=" + named
              + " -- it is under a temp/scratchpad directory; publishing to " + fallback,
              file=sys.stderr)
    return fallback


SITE = export_root()
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
              "HANDOFF.md", "BUGS.md", "NEXT_STEPS.md", "MAINTENANCE.md",
              # The Step 4 entanglement plan. Published because it is the document the owner
              # rules on and the next run plans from, and a plan that lives only on one machine
              # is a plan the relay cannot carry.
              "STEP4_PLAN.md")
# Backups and scratch copies never travel. The .pre* family is session backups of live modules
# -- seven of them were sitting in src/ and being published to the PUBLIC repo because this
# tuple only knew about two suffixes.
SKIP_SUFFIX = (".pyc", ".presilence", ".prebandfix", ".precapfix", ".prefix", ".prepool",
               ".preprobe", ".prewiden", ".prewindow", ".bak", ".tmp", ".orig")

# THE VENDOR LIST — first of three independent locks. Widened 2026-08-25 after an audit
# enumerated what walked past the original eight prefixes into the PUBLIC repo unredacted: AWS
# access and secret keys, Slack tokens, generic Bearer tokens, PEM private-key blocks, JWTs,
# Stripe live and test keys, database URLs with inline credentials, and Discord/npm/Twilio/
# SendGrid tokens. The docstring already promised to refuse "anything credential-shaped", which
# is the dangerous half: a claim that reads as a guarantee while covering eight vendors.
_SECRET = re.compile(
    r"(sk-[A-Za-z0-9_\-]{16,}|gsk_[A-Za-z0-9]{20,}|AIza[A-Za-z0-9_\-]{20,}|"
    r"github_pat_[A-Za-z0-9_]{20,}|ghp_[A-Za-z0-9]{20,}|gho_[A-Za-z0-9]{20,}|"
    r"ghs_[A-Za-z0-9]{20,}|hf_[A-Za-z0-9]{20,}|"
    r"xai-[A-Za-z0-9]{20,}|csk-[A-Za-z0-9]{20,}|"
    # AWS: AKIA/ASIA access-key ids, and secret keys named in an assignment
    r"A(?:KIA|SIA)[0-9A-Z]{16}|"
    r"(?i:aws_secret_access_key)[\"' :=]+[A-Za-z0-9/+=]{40}|"
    # Slack, Stripe, Discord, npm, Twilio, SendGrid
    r"xox[abposr]-[A-Za-z0-9\-]{10,}|"
    r"sk_(?:live|test)_[A-Za-z0-9]{16,}|rk_(?:live|test)_[A-Za-z0-9]{16,}|"
    r"dop_v1_[A-Za-z0-9]{32,}|npm_[A-Za-z0-9]{32,}|"
    r"SG\.[A-Za-z0-9_\-]{16,}\.[A-Za-z0-9_\-]{16,}|"
    r"SK[0-9a-fA-F]{32}|"
    # PEM private key blocks, JWTs, and Bearer tokens
    r"-----BEGIN [A-Z ]*PRIVATE KEY-----|"
    r"eyJ[A-Za-z0-9_\-]{10,}\.eyJ[A-Za-z0-9_\-]{10,}\.[A-Za-z0-9_\-]{10,}|"
    r"(?i:bearer)\s+[A-Za-z0-9_\-\.=]{24,}|"
    # a connection string carrying inline credentials
    r"(?i:postgres|postgresql|mysql|mongodb(?:\+srv)?|redis|amqp)://[^\s:@/]+:[^\s:@/]+@)")

# LOCK TWO — SHAPE-BLIND. Every pattern above shares one weakness: it only knows the secrets
# somebody thought of, and the audit's whole finding was a list that had not kept up. This
# catches a long, high-entropy token by its STATISTICS instead of its prefix, so a vendor nobody
# has heard of is still caught the first time. Deliberately conservative -- the corpus is full of
# legitimate long strings (hashes, addresses, base64 page text), so this only fires on a value
# sitting in an assignment next to a credential-ish NAME, which is where a real key leaks from.
_SECRET_ASSIGN = re.compile(
    r"(?i)\b([a-z0-9_\-]*(?:secret|passwd|password|token|api[_\-]?key|access[_\-]?key|"
    r"private[_\-]?key|credential|auth)[a-z0-9_\-]*)\s*[:=]\s*[\"']?([^\s\"',}]{16,})")


def _entropy(s):
    """Shannon entropy per character. A real key is near-random; a sentence is not."""
    if not s:
        return 0.0
    import math as _m
    n = float(len(s))
    counts = {}
    for ch in s:
        counts[ch] = counts.get(ch, 0) + 1
    return -sum((c / n) * _m.log((c / n), 2) for c in counts.values())


# Above this, a 16+ character value in a credential-named field is treated as a live secret.
# English prose runs ~3.5-4.0 bits/char; base64 and hex keys run 4.5-6.0.
SECRET_ENTROPY_BITS = 4.0


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
        return scrub_text(obj)
    return obj


# A line carrying this marker is a DELIBERATE example -- a drill fixture, an audit report
# quoting a pattern, documentation of what a leak looks like. Without it the scanner blocks
# every publish on its own test data, which is the fastest way to get a security check disabled
# by the people it protects. The marker must be on the same line, so it cannot silence a region.
FIXTURE_MARKER = "SECRET-FIXTURE"


# PATTERNS THAT ARE AMBIGUOUS BY SHAPE, and must therefore also look random. Only two, and both
# earned their place by producing a false positive on the real corpus the first time the scanner
# ran: mined He-Man wiki text contains `sk-age-of-apocalypse` (a slug), and an audit report
# contains `postgres://user:pass@` (documentation of what a leak looks like). Everything else in
# `_SECRET` is unambiguous by STRUCTURE -- an AWS key id, a PEM header, a JWT, a Slack token --
# and must never be entropy-gated, because a structural match is already proof.
#
# Getting this wrong in the other direction is worse and I did it first: gating every pattern on
# entropy cleared an AWS access-key id, a PEM private-key header and a live database
# URL, because none of them are random-looking. The drill caught all three immediately.
_AMBIGUOUS = re.compile(r"^(sk-|[a-z+]+://)")
# Credential pairs that are obviously placeholders in documentation.
_PLACEHOLDER_CREDS = re.compile(
    r"(?i)://(user|username|admin|root|me|you|someone|example|test|foo)"
    r":(pass|passwd|password|secret|hunter2|changeme|example|test|bar)@")   # SECRET-FIXTURE


def _is_real_secret(text):
    """Does this matched value look like a KEY rather than like prose or documentation?"""
    if not _AMBIGUOUS.match(text):
        return True                       # structural match -- shape alone is proof
    if _PLACEHOLDER_CREDS.search(text):
        return False                      # `postgres://user:pass@` is documentation
    core = re.sub(r"^(sk-)", "", text)
    core = re.sub(r"^[a-z+]+://", "", core)
    return _entropy(core) >= SECRET_ENTROPY_BITS


def scrub_text(s):
    """Both locks, applied to one string. Named and public so the DRILL can attack it."""
    if FIXTURE_MARKER in s:
        return s

    def _vendor(m):
        return "[redacted]" if _is_real_secret(m.group(0)) else m.group(0)
    out = _SECRET.sub(_vendor, s)

    def _maybe(m):
        name, val = m.group(1), m.group(2)
        if _entropy(val) >= SECRET_ENTROPY_BITS:
            return "%s=[redacted]" % name
        return m.group(0)
    return _SECRET_ASSIGN.sub(_maybe, out)


def scan_for_secrets(root, max_bytes=2_000_000):
    """LOCK THREE — read what is about to be PUBLISHED, not what we meant to publish.

    The two locks above run on the snapshot dict. This one walks the files actually staged in
    the export copy, which is the only thing that is true about what reaches the public repo: a
    file copied wholesale (`COPY_FILES`, `COPY_DIRS`) never passes through `_scrub` at all, so
    the first two locks have nothing to say about it. A log excerpt pasted into HANDOFF.md, a
    provider error quoted in BUGS.md, a config committed by hand -- all arrive this way.

    Returns a list of (relative path, line number, what matched). Empty is the good state.
    """
    hits = []
    for base, _dirs, files in os.walk(root):
        if ".git" in base.replace("/", os.sep).split(os.sep):
            continue
        for f in sorted(files):
            p = os.path.join(base, f)
            try:
                if os.path.getsize(p) > max_bytes:
                    continue
                with open(p, encoding="utf-8", errors="replace") as fh:
                    text = fh.read()
            except OSError:
                continue
            rel_for_supp = os.path.relpath(p, root).replace(os.sep, "/")
            supp = None
            try:
                import suppressions as _SUP
                supp = _SUP.suppressed("secret_scan", rel_for_supp)
            except Exception:
                supp = None
            for i, line in enumerate(text.splitlines(), 1):
                if FIXTURE_MARKER in line:
                    continue
                if supp:
                    # SUPPRESSED, NOT DROPPED. Trivy's `--show-suppressed` discipline: a finding
                    # that is being waived still appears, tagged with the reason it was waived,
                    # so the waiver can be audited. A suppression that hides a finding entirely
                    # is indistinguishable from a detector that stopped working.
                    if _SECRET.search(line) or _SECRET_ASSIGN.search(line):
                        hits.append((rel_for_supp, i,
                                     "SUPPRESSED (%s)" % supp.get("reason", "")[:60]))
                    continue
                mv = _SECRET.search(line)
                if mv and _is_real_secret(mv.group(0)):
                    hits.append((os.path.relpath(p, root), i, "vendor pattern"))
                    continue
                m = _SECRET_ASSIGN.search(line)
                if m and _entropy(m.group(2)) >= SECRET_ENTROPY_BITS:
                    hits.append((os.path.relpath(p, root), i,
                                 "high-entropy value in '%s'" % m.group(1)))
    return hits


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

    # LOCK THREE, AT THE LAST POSSIBLE MOMENT. This is the only step in the whole project whose
    # failure is IRREVERSIBLE and OUTWARD-FACING: a key pushed to a public repo is public even
    # if the next commit removes it. So the staged tree is read as it actually stands, after
    # every copy and every snapshot write, and a hit REFUSES THE PUSH rather than redacting --
    # a secret in a source file is not something to quietly rewrite behind the author's back.
    # The ledgers travel with everything else, so a truncated HANDOFF is not merely a lost relay
    # -- it is a published one. Checked here, at the same last moment as the secret scan.
    try:
        import ledger_guard as _LG
        _LG.assert_intact()
    except ImportError:
        pass

    leaks = [h for h in scan_for_secrets(SITE) if not str(h[2]).startswith('SUPPRESSED')]
    # Suppressed findings are REPORTED by the scanner and excluded from the refusal --
    # visible in the audit trail, not a reason to block a push.
    if leaks:
        import escalation as _ESC
        _ESC.escalate(_ESC.OWNER, "SECRET_IN_EXPORT",
                      "publish refused: %d credential-shaped value(s) staged for the PUBLIC "
                      "repo. First: %s:%s (%s)"
                      % (len(leaks), leaks[0][0], leaks[0][1], leaks[0][2]),
                      evidence=[{"file": f, "line": n, "why": w} for f, n, w in leaks[:20]],
                      who="publish.py")
        raise RuntimeError(
            "PUBLISH REFUSED — %d credential-shaped value(s) are staged for the public repo:\n"
            % len(leaks)
            + "\n".join("    %s:%s  %s" % (f, n, w) for f, n, w in leaks[:10])
            + "\nNothing was pushed, and the library has been halted. Remove the value, then "
              "clear the halt with a ruling. If it is a false positive, say so in the ruling.")

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
    # PLANT-WIDE INTERLOCK. The top rung of the escalation chain (escalation.py). If a
    # library-wide invariant has been violated, nothing starts until a person rules on it.
    # Placed first in main() so there is no path into this job that skips it.
    try:
        import escalation as _ESC
    except ImportError as _esc_gone:
        # FAIL CLOSED. This used to be `except ImportError: pass`, which meant a deleted or
        # unparseable `escalation.py` silently switched the plant-wide halt off in every job
        # at once -- nine sites, all of them quiet about it. That is Hard Rule -1's own
        # incident wearing different clothes: the last one began with an autonomous run
        # removing a safety it had concluded was unnecessary, and nothing downstream could
        # tell. A job that cannot ask whether the library is halted has no business
        # starting. Pinned by verify_math so the swallow cannot come back. (run #31)
        raise SystemExit(
            "REFUSING TO START: the escalation chain (src/escalation.py) could not be "
            "imported (%s), so the halt cannot be read. Hard Rule -1." % _esc_gone)
    _ESC.assert_clear(os.path.basename(__file__))
    ap = argparse.ArgumentParser(description="publish the project and its instruments")
    ap.add_argument("--init", action="store_true", help="create the export repo")
    ap.add_argument("--remote", help="git remote URL")
    ap.add_argument("--push", action="store_true", help="commit and push")
    ap.add_argument("--loop", type=float, default=0, help="keep publishing, minutes apart")
    a = ap.parse_args()

    if a.init or a.remote:
        ensure_site(remote=a.remote)
        print("export repo at " + SITE + (("  -> " + a.remote) if a.remote else ""))

    # A REFUSED PUBLISH MUST NOT REPORT SUCCESS. The `except Exception` below catches every
    # failure this loop can have -- including `push()`'s own `RuntimeError("PUBLISH REFUSED")`
    # when the credential scanner finds a live secret staged for the PUBLIC repo -- and the
    # one-shot path then `return 0`'d regardless. So the scanner could do exactly its job, be
    # heard by nobody, and hand its caller a success code: the same shape as the nine halt
    # interlocks fixed alongside this (run #31), and the one that mattered most, because the
    # caller here is every maintenance run's final step. The loop keeps looping on purpose --
    # a daemon publisher should retry -- but it remembers, and the exit code tells the truth.
    rc = 0
    while True:
        try:
            n = sync_tree()
            render_page()
            write()
            # Name the destination every cycle. The loop reported "synced 14 files, wrote
            # docs/state.json" four times an hour for an unknown number of days while writing
            # into a temp-directory clone nobody knew existed (see SITE above). A line that
            # says what it did and not WHERE it did it cannot expose that class of fault.
            print(f"synced {n} files, wrote docs/state.json  ->  {SITE}")
            if a.push:
                print("pushed" if push() else "no change to push")
        except Exception as e:
            silence.note("publish.py:main")
            print(f"publish failed: {type(e).__name__}: {str(e)[:180]}")
            rc = 1
        if not a.loop:
            return rc
        time.sleep(a.loop * 60)


if __name__ == "__main__":
    sys.exit(main())
