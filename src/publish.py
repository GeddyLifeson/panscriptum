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
# WHAT IN THE EXPORT ROOT IS THE EXPORT'S OWN, and therefore never mirrored from the live
# project. `prune_export` uses this to tell a directory it must leave alone from a COPY_DIRS root
# that has been WITHDRAWN from the tuple. `docs/` is generated by `render_page`/`write`; anything
# whose name begins with a dot is repo or forge machinery (`.git`, and the `.github/workflows`
# the export carries) and no COPY_DIRS root has ever begun with one — so the dot rule is a SHAPE,
# not an enumeration, and a new dot-directory GitHub invents next year is safe the first time.
EXPORT_OWN_DIRS = ("docs",)
# Backups and scratch copies never travel. The .pre* family is session backups of live modules
# -- seven of them were sitting in src/ and being published to the PUBLIC repo because this
# tuple only knew about two suffixes. The fix at the time was to enumerate the seven names, which
# repeats the same mistake with a longer list: `.preNNN` is one FAMILY, not nine unrelated
# strings, and the ninth name anyone writes still walks straight past a tuple of the first eight.
# `local_agent.py`'s own header names this failure shape -- "a DENYLIST fails OPEN -- anything
# nobody thought of is permitted" -- so the family is now matched by its SHAPE (`_is_skipped`
# below), and SKIP_SUFFIX goes back to holding only the suffixes that are not part of that family.
SKIP_SUFFIX = (".pyc", ".bak", ".tmp", ".orig")
_PRE_BACKUP = re.compile(r"\.pre[a-z0-9]*$", re.I)


def _is_skipped(name):
    """True for a file `sync_tree` must never publish: a scratch suffix in `SKIP_SUFFIX`, or
    anything in the `.pre*` session-backup family, matched by shape rather than by name so a
    suffix nobody has written yet is still caught the first time."""
    return name.endswith(SKIP_SUFFIX) or _PRE_BACKUP.search(name) is not None


def gitignore_lines():
    """The export repo's `.gitignore`, DERIVED FROM `_is_skipped` rather than restated beside it.

    `ensure_site` used to write a hand-typed `*.presilence` while `_is_skipped` matched the whole
    `.pre*` family by shape, so a hand-placed `.preNNN` in the export tree was skipped by the
    copier and NOT ignored by git -- committed to the PUBLIC repo by `git add -A`. That is the
    family-vs-enumeration mistake `SKIP_SUFFIX` itself was already repaired for, one file over:
    one side of the pair described a pattern, the other listed instances, and a pair like that
    drifts until both come from the same definition. Now they do. (order e14c1f1c494e)

    THE GLOB IS DELIBERATELY WIDER THAN THE REGEX. `.gitignore` has no way to say "at the end of
    the name", so `*.pre*` also catches names the regex would not. Wider is the correct direction
    for the half of the pair that guards a PUBLIC repo, and it costs nothing in precision where
    it matters: `_is_skipped` remains the exact authority on what `sync_tree` copies.
    """
    return ["__pycache__/"] + ["*" + s for s in SKIP_SUFFIX] + ["*.pre*"]

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

    KEYS AS WELL AS VALUES. This was `{k: _scrub(v) for k, v in obj.items()}`, which walks values
    only, so a credential sitting in a dictionary KEY -- a per-token bucket, a provider error
    dict keyed by the string that failed -- passed through verbatim while the value beside it was
    redacted, and the module docstring's promise that `_scrub` "refuses anything credential-shaped
    even if a future edit puts one in the state dict by accident" was false as written. Never a
    leak, because LOCK THREE reads the rendered `docs/state.json` and refuses the push on it --
    but that turns a redaction into a hard publish stoppage somebody then has to diagnose, which
    is the expensive way to learn about a one-line omission. (order b1147f53971e)
    """
    if isinstance(obj, dict):
        out = {}
        for k, v in obj.items():
            sk = scrub_text(k) if isinstance(k, str) else k
            if sk in out:
                # Two distinct keys can redact to the same string, and so can a redaction landing
                # on a key that was already there literally. Keeping one silently would DROP a row
                # from the snapshot; the suffix keeps both and makes the collision visible.
                sk = "%s#%d" % (sk, len(out))
            out[sk] = _scrub(v)
        return out
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
    """Both locks, applied to one string. Named and public so the DRILL can attack it.

    PER LINE, not the whole string at once. FIXTURE_MARKER's own comment above promises the
    marker "must be on the same line, so it cannot silence a region" -- true of `scan_for_secrets`
    (which checks per line) but was false here: checking `FIXTURE_MARKER in s` against a whole
    multi-line value let one marker anywhere blank the scrub for every line that value carried,
    including a line with a live credential and no marker of its own. A multi-line snapshot
    value survives `json.dump` as ONE escaped line in docs/state.json, so LOCK THREE's own
    per-line marker check would then also wave the same secret through.
    """
    return "\n".join(_scrub_line(line) for line in s.split("\n"))


def _scrub_line(s):
    """`scrub_text`'s per-line body. Not named `scrub_text` itself so the drill keeps attacking
    the public per-string entry point rather than a helper nothing else calls."""
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


# How much of one file is held in memory at a time while scanning, and how much of the previous
# segment is carried into the next one. The overlap only has to be longer than the longest
# pattern `_SECRET` can match (a PEM header plus a key line, comfortably under 4 KB) so that a
# credential lying across a segment boundary is still seen whole by the regex.
_SCAN_OVERLAP = 4_096
_SCAN_BLOCK = 262_144


def _scan_units(path, line_cap):
    """Yield (line number, text) for every scannable piece of a file, at any size.

    STREAMS. Nothing here reads a whole file, so SIZE IS NEVER A REASON TO SKIP -- which is the
    entire point of this helper. `scan_for_secrets` used to `continue` past any staged file over
    two megabytes, with no count and no note, and four published files were over it: a 3.36 MB
    register, a 2.97 MB citations file, a 2.68 MB terminal page and a 2.47 MB data script. That
    is 11.5 MB reaching the PUBLIC repo examined by nothing, reported as clean. (Audited and
    hand-scanned 2026-08-25 -- clean, this time.)

    Line numbering and the per-line `FIXTURE_MARKER` rule are preserved exactly for any file with
    ordinary lines. A single logical line longer than `line_cap` -- a minified script, a
    one-line JSON register -- is emitted as OVERLAPPING SEGMENTS under its own line number.
    Splitting can only ever ADD findings: a fixture marker in one segment no longer silences the
    rest of a multi-megabyte line, and an extra false positive is a refusal, which is the safe
    direction for the last gate before a public push.
    """
    with open(path, encoding="utf-8", errors="replace") as fh:
        lineno = 1
        buf = ""            # the current logical line, so far
        carry = ""          # tail of the last segment emitted for THIS line
        while True:
            block = fh.read(_SCAN_BLOCK)
            if not block:
                break
            parts = block.split("\n")
            buf += parts[0]
            if len(parts) == 1:
                # No line break in this block: the line is longer than a block. Emit it in
                # bounded, overlapping segments rather than growing a string without limit.
                while len(buf) > line_cap:
                    seg = carry + buf[:line_cap]
                    yield lineno, seg
                    carry = seg[-_SCAN_OVERLAP:]
                    buf = buf[line_cap:]
                continue
            yield lineno, carry + buf
            carry = ""
            lineno += 1
            for mid in parts[1:-1]:
                yield lineno, mid
                lineno += 1
            buf = parts[-1]
        if buf:
            yield lineno, carry + buf


# COMPILED BYTECODE IS NOT PUBLISHED, AND MUST NOT BE SCANNED. `sync_tree` prunes `__pycache__`
# from its walk, `_is_skipped` refuses `.pyc`, and `ensure_site` writes both into `.gitignore` --
# so no bytecode has ever reached the public repo. But `scan_for_secrets` walks the FILESYSTEM
# rather than the index, and read a stale cache directory anyway: `src/__pycache__/
# drill.cpython-313.pyc` was reported as a high-entropy `api_key` on every single run. It is the
# DRILL'S OWN credential fixture, frozen into bytecode -- where the same-line `SECRET-FIXTURE`
# marker that clears the source cannot survive the compile, so the marker rule can never reach it.
# `detect-secrets`, pointed at the same tree, reports zero because it does not read `.pyc`; this
# was the only disagreement between the two scanners and the outsider is right. A gate that cries
# wolf on every run is a gate somebody switches off, and then it is not there for the real one.
def _is_compiled(path):
    """True for compiled bytecode: any `__pycache__` path component, or a `.pyc`/`.pyo` file."""
    parts = [p for p in path.replace("/", os.sep).split(os.sep) if p]
    if not parts:
        return False
    return "__pycache__" in parts or parts[-1].endswith((".pyc", ".pyo"))


def scan_for_secrets(root, max_bytes=2_000_000, only=None):
    """LOCK THREE — read what is about to be PUBLISHED, not what we meant to publish.

    The two locks above run on the snapshot dict. This one walks the files actually staged in
    the export copy, which is the only thing that is true about what reaches the public repo: a
    file copied wholesale (`COPY_FILES`, `COPY_DIRS`) never passes through `_scrub` at all, so
    the first two locks have nothing to say about it. A log excerpt pasted into HANDOFF.md, a
    provider error quoted in BUGS.md, a config committed by hand -- all arrive this way.

    SIZE IS NOT A REASON TO SKIP, AND UNREADABLE IS NOT CLEAN. Both used to be a bare
    `continue`: a file over `max_bytes` was passed over silently, and so was any file that
    raised on open. "Too big to check" reported as clean is the exact failure shape this project
    is built against, and this is the one gate where "we caught it next run" is not a recovery,
    because the bytes are already public. Every file is now STREAMED (`_scan_units`), and a file
    that genuinely cannot be read is REFUSED BY NAME as an `UNSCANNABLE` finding rather than
    skipped -- a hit, so the caller blocks the push and a person looks at it.

    `max_bytes` is kept (callers pass it) but no longer decides what gets scanned. It is now the
    most of one file held in memory at a time: the segment size for a single very long line.

    COMPILED BYTECODE IS EXCLUDED (`_is_compiled`), and it is the one exclusion here: nothing
    under `__pycache__` and no `.pyc`/`.pyo` is ever copied into the export or committed, so
    reading it could only ever produce a finding about a file that is not published. It did,
    forever, on the drill's own fixture. Source files are not excluded on any ground.

    `only` NARROWS THE WALK TO NAMED TOP-LEVEL ENTRIES, and it must never be passed on the push
    path. The whole point of this lock is that it reads everything staged, so an argument that
    can make it read less is a loaded gun: `write()`/`push()` call it with `only=None` and the
    drill's `_secret_scan_reads_every_staged_file` fixture proves the unnarrowed walk still sees
    an oversized file. It exists for a caller that must scan against REPO-RELATIVE paths -- the
    suppression table is keyed that way, so `root` has to stay the repo root and cannot simply
    be pointed at a subdirectory -- while paying for the export set rather than for a 4.3 GB
    tree of mined corpus. Order 01a479a891a5: one drill net was walking 277,221 files to check
    that a suppressed finding is still reported by 552 of them.

    Returns a list of (relative path, line number, what matched). Empty is the good state.
    """
    hits = []
    seen = set()
    allowed = set(only) if only is not None else None
    root_key = os.path.abspath(root)
    for base, dirs, files in os.walk(root):
        # Bytecode caches are pruned from the WALK, not just filtered per file, so the scanner
        # never pays to descend into them. See `_is_compiled` above for why they are excluded.
        dirs[:] = [x for x in dirs if x != "__pycache__"]
        if allowed is not None and os.path.abspath(base) == root_key:
            # Pruned at the ROOT LEVEL only, so `only` names the same top-level entries the
            # export copies and everything beneath one of them is still scanned in full.
            dirs[:] = [x for x in dirs if x in allowed]
            files = [x for x in files if x in allowed]
        if ".git" in base.replace("/", os.sep).split(os.sep):
            continue
        for f in sorted(files):
            if _is_compiled(f):
                continue          # a stray `.pyc` sitting outside a `__pycache__` directory
            p = os.path.join(base, f)
            # ONE SPELLING OF THE PATH, forward slashes, for every finding this returns.
            # Suppressed findings were reported under the forward-slash spelling the suppression
            # lookup needs and real findings under the os.sep one, so a single refusal message --
            # and a single escalation's evidence list -- could carry both spellings of the same
            # tree. Cosmetic, except that this message is what a person reads at the moment a
            # publish is refused for a credential, which is the worst moment to be working out
            # whether two paths are the same path. (order df572f47255f)
            rel = os.path.relpath(p, root).replace(os.sep, "/")
            supp = None
            try:
                import suppressions as _SUP
                supp = _SUP.suppressed("secret_scan", rel)
            except Exception:
                supp = None

            def _add(key, hit):
                # A long line is scanned in overlapping segments, so the same value can be seen
                # twice. Report it once; a duplicate refusal reads as two leaks.
                if key not in seen:
                    seen.add(key)
                    hits.append(hit)

            try:
                for i, line in _scan_units(p, max(1, int(max_bytes))):
                    if FIXTURE_MARKER in line:
                        continue
                    if supp:
                        # SUPPRESSED, NOT DROPPED. Trivy's `--show-suppressed` discipline: a
                        # finding that is being waived still appears, tagged with the reason it
                        # was waived, so the waiver can be audited. A suppression that hides a
                        # finding entirely is indistinguishable from a detector that stopped
                        # working.
                        if _SECRET.search(line) or _SECRET_ASSIGN.search(line):
                            _add((rel, i, "supp"),
                                 (rel, i,
                                  "SUPPRESSED (%s)" % supp.get("reason", "")[:60]))
                        continue
                    # EVERY vendor match on the line, not just the first. `search` stopped at
                    # match one, so a real key sitting behind a slug that `_is_real_secret`
                    # cleared was never looked at -- survivable on a 90-character source line,
                    # not on a one-line 3 MB register where the whole file is one "line".
                    vendor = False
                    for mv in _SECRET.finditer(line):
                        if _is_real_secret(mv.group(0)):
                            _add((rel, i, "vendor"), (rel, i, "vendor pattern"))
                            vendor = True
                            break
                    if vendor:
                        continue
                    for m in _SECRET_ASSIGN.finditer(line):
                        if _entropy(m.group(2)) >= SECRET_ENTROPY_BITS:
                            _add((rel, i, "assign", m.group(1)),
                                 (rel, i, "high-entropy value in '%s'" % m.group(1)))
                            break
            except Exception as e:
                # NAMED AND REFUSED, NEVER SKIPPED. Line 0 marks a whole-file finding.
                _add((rel, 0, "unscannable"),
                     (rel, 0, "UNSCANNABLE — could not be read for scanning (%s: %s); "
                              "refusing rather than passing it unexamined"
                              % (type(e).__name__, str(e)[:80])))
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
    r = subprocess.run(["git", *list(args)], cwd=SITE, capture_output=True,
                       text=True, encoding="utf-8", errors="replace", env=env, creationflags=_NO_WIN)
    if check and r.returncode != 0:
        raise RuntimeError("git " + " ".join(args) + ": "
                           + (r.stderr or r.stdout).strip()[:220])
    return (r.stdout or "").strip()


def _unpushed():
    """How many local commits are NOT on origin/main. -> (count, detail).

    `count` is None only when the question genuinely cannot be answered.

    THE QUESTION `push()` NEVER ASKED. Its no-op test was `git status --porcelain` alone -- a
    clean WORKTREE -- and a clean worktree says nothing about whether the last cycle's commit
    ever reached the remote. So a `git push` that failed (the 403 from a wrong credential that
    `git()`'s own comment documents, a network failure, a remote rejection) left the commit
    sitting on the local export branch, and the NEXT run found nothing to add, printed "no
    change to push" and exited 0. That is the same defect `PushHeld` was created for standing on
    the sibling branch, and this module's own SITE comment records what it costs: "the remote
    fell 122 commits behind while synced N files kept printing above it."

    LOCAL ONLY -- this reads the remote-TRACKING ref, so it opens no socket and cannot be made
    to lie by a network that is down. A missing `origin/main` is not an error either: it means
    nothing from this repo has ever landed, so every commit here is unpushed, which is exactly
    what the caller needs to hear before it says "nothing to send". An unborn branch (a
    freshly-`--init`ed export with no commit yet) is a true zero and must not read as held.
    """
    try:
        n = git("rev-list", "--count", "origin/main..HEAD")
    except RuntimeError as e:
        detail = "no origin/main to compare against (%s)" % str(e)[:80]
    else:
        try:
            return int(n.strip()), "origin/main..HEAD"
        except ValueError:
            return None, "git rev-list answered %r, which is not a count" % n[:40]
    # No remote-tracking ref. Count what is here instead: on a repo that has never pushed, that
    # IS the unpushed set. A repo with no commits at all answers zero, not unknown.
    try:
        local = git("rev-list", "--count", "HEAD")
    except RuntimeError:
        return 0, "no commits on this branch yet"
    try:
        c = int(local.strip())
    except ValueError:
        return None, "git rev-list answered %r, which is not a count" % local[:40]
    return c, (detail + "; %d local commit(s) have therefore never landed" % c) if c else \
        (detail + "; the branch has no commits, so nothing is held")


def _same_dir(a, b):
    """Are these two paths the SAME directory on disk? Used to refuse a delete path.

    `os.path.abspath` is not an answer to that question. It normalises TEXT and stops: it does
    not resolve a symlink, a Windows junction or a case variant, so a `SITE` that reaches the
    live project by any of those routes reads as a different directory and walks straight
    through the guard written to refuse exactly that. This machine junctions directories
    deliberately -- `mutate.py` builds its sandbox out of junctions into the live tree -- so the
    naive comparison is not a theoretical hole here.

    `realpath` resolves the link; the casefold compares the way this filesystem actually
    compares. Casefolding is the safe direction if it is ever wrong: two genuinely distinct
    case-sensitive directories would compare EQUAL, and equal means the delete path declines.
    """
    return os.path.realpath(a).casefold() == os.path.realpath(b).casefold()


def _live_root_state(d):
    """Classify a `COPY_DIRS` root in the LIVE project: 'live', 'gone' or 'unavailable'.

    The distinction the prune turns on, and it did not exist before. `sync_tree` asked
    `os.path.isdir` and treated the single answer False as "this directory is not in the project
    any more" -- but `isdir` also answers False for a directory that is merely UNREADABLE right
    now, and it swallows the error that would have said which. Absence of evidence was being
    read as evidence of deletion, on the strength of one failed syscall, for a subtree of a
    PUBLIC repo.

    So this asks twice. A root that lists is 'live'. A root that does not list AND whose name is
    ABSENT from a successfully enumerated parent is 'gone' -- positive evidence of removal, not a
    failed read, because the parent answered. Anything else -- the parent unreadable, or the name
    still sitting there while the directory itself will not open (a junction whose target is
    offline, a locked mount, a permissions blip) -- is 'unavailable', and the caller holds the
    prune for that subtree.
    """
    root = os.path.join(HERE, d)
    try:
        if os.path.isdir(root):
            os.listdir(root)              # present is not the same as readable
            return "live"
    except OSError:
        return "unavailable"
    try:
        present = d in os.listdir(HERE)
    except OSError:
        # We could not even read the live project's own root. Nothing may be withdrawn on that.
        return "unavailable"
    return "unavailable" if present else "gone"


def _may_delete_in_export():
    """May anything be DELETED under `SITE` at all? -> bool.

    ONE SPELLING OF THE ANSWER, because there are two delete paths in this module and only one
    of them used to ask both halves of the question. `prune_export` refused unless the
    destination is a different directory from the live project AND carries the `.is-export-copy`
    marker; `sync_tree`'s COPY_FILES withdrawal checked only the first, so a `SITE` that
    misresolved onto some other directory carrying the same file names could be deleted out of.
    Deletion has no undo, and a misresolved SITE has happened here -- see `export_root`.
    """
    if _same_dir(SITE, HERE):
        return False
    # `os.path.exists` is the right call for a MARKER, unlike for a live file: it answers False
    # for absent and for unreadable alike, and both of those mean "not proven to be the export
    # copy", which is a refusal to delete. The failure direction is the safe one.
    return os.path.exists(os.path.join(SITE, ".is-export-copy"))


def _live_file_state(f):
    """Classify a `COPY_FILES` name in the LIVE project: 'live', 'gone' or 'unavailable'.

    `_live_root_state`'s question, asked about a FILE, because the withdrawal two lines below
    the one that got the classification had none of it: it turned on a single `os.path.exists`,
    and `genericpath.exists` catches `(OSError, ValueError)` and answers False -- so a permission
    denial, a lock, an over-long path or a name the filesystem will not parse is spelled exactly
    like "this file has been deleted from the project". Measured: `os.path.exists` returns False
    with no exception for both an over-long path and a path with an illegal character.
    This module's own docstring says Norton locks newly-written objects here, and the files this
    loop carries are the ledgers that get written every cycle -- HANDOFF.md, STATUS.md, BUGS.md.
    One lock, and the ledger is withdrawn from the PUBLIC repo and re-added by the next cycle's
    commit, so the history reads as though somebody meant it. (order d2edc81326da)

    So it asks twice, exactly as `_live_root_state` does. A file that stats is 'live'. A file
    that does not stat AND whose name is ABSENT from a successfully enumerated project root is
    'gone' -- positive evidence of removal, because the directory answered. Anything else is
    'unavailable', and the caller withdraws nothing on it.
    """
    p = os.path.join(HERE, f)
    try:
        os.stat(p)
        return "live"
    except FileNotFoundError:
        pass
    except (OSError, ValueError):
        # The two families `os.path.exists` swallows: a denial or a lock (OSError) and a name
        # the platform will not accept at all (ValueError). Neither is evidence of deletion.
        return "unavailable"
    try:
        present = f in os.listdir(HERE)
    except OSError:
        return "unavailable"
    return "unavailable" if present else "gone"


def prune_export(wanted, held=()):
    """Delete from the export copy everything `sync_tree` did not just put there. -> count.

    A COPY IS NOT A REFRESH. This loop copies forward and never looked back, so a file deleted
    from the live project stayed in the export copy forever: `git add -A` re-staged it every
    cycle and it kept being published to the PUBLIC repo. That is worst exactly when it matters
    most -- a file deleted BECAUSE of what it contained goes on being served after the deletion
    that was supposed to withdraw it. The same hole covers a file that becomes unpublishable
    without being deleted (renamed to `.pre*`, moved under `__pycache__`): `_is_skipped` stops
    the next copy, it does nothing about the copy already sitting there.

    `wanted` is the exact set of relative paths (forward slashes) the sync just wrote or
    verified. Anything else under a `COPY_DIRS` subtree of the export copy is gone. Scope is
    deliberately narrow: `docs/` is generated by `render_page`/`write`, `.git` is the repo
    itself, and the root marker files are ours -- none of them are mirrored from anything, so
    none of them are this function's business.

    REFUSES TO RUN ANYWHERE BUT THE EXPORT COPY. Deletion has no undo, so this walks away
    unless the destination is a different directory from the live project AND carries the
    `.is-export-copy` marker. A misresolved `SITE` (it has happened -- see `export_root`) must
    read as nothing to do, never as permission to delete a live tree. The "different directory"
    test goes through `_same_dir`, not `abspath`, because junctions are in use on this machine.

    AND IT REFUSES A SUBTREE IT WAS NOT ABLE TO READ. `held` is the set of `COPY_DIRS` roots
    `sync_tree` could not enumerate in the live project this cycle. Nothing under those roots is
    touched. A root that is genuinely gone is NOT in `held` and still prunes in full -- that is
    the point of the prune and it is preserved; the change is only that "I could not read it"
    stops being spelled the same way as "it is not there".

    AND IT REACHES A ROOT THAT WAS REMOVED FROM `COPY_DIRS` ALTOGETHER. The loop below walks the
    tuple, so the one subtree it could never see was the one whose root had been DELETED from it:
    the list of things to prune WAS the list of things to copy. Withdrawing a directory from
    publication -- usually the deliberate act of deciding it must stop being served -- therefore
    left its whole export copy standing in the PUBLIC repo for ever, re-staged by `git add -A`
    every cycle. This is the mirror of the over-prune `_live_root_state` was written for, and the
    more dangerous of the two directions: an over-prune loses a copy the next cycle puts back, an
    under-prune goes on serving something somebody decided must stop being served. Found live --
    `state/` (five run-state files, including a scratch SQLite database) had been sitting in the
    public repo since 2026-08-23, left behind by a COPY_DIRS that used to name it.
    (order f2271d9ee843)
    """
    if not _may_delete_in_export():
        return 0
    held = set(held or ())
    removed = 0
    for d in COPY_DIRS:
        if d in held:
            continue
        droot = os.path.join(SITE, d)
        if not os.path.isdir(droot):
            continue
        for base, dirs, files in os.walk(droot, topdown=False):
            if ".git" in base.replace("/", os.sep).split(os.sep):
                continue
            for f in files:
                p = os.path.join(base, f)
                rel = os.path.relpath(p, SITE).replace(os.sep, "/")
                if rel in wanted:
                    continue
                try:
                    os.remove(p)
                    removed += 1
                except OSError:
                    # Locked or already gone. Not fatal -- the next cycle sees it again -- but
                    # a stale public file surviving a prune is exactly the thing this function
                    # exists to notice, so it goes on the record instead of vanishing.
                    silence.note("publish.py:prune-remove")
            for sub in dirs:
                # `topdown=False`, so a directory is visited after its contents: an empty one
                # here is one this prune just emptied, or one the live project no longer has.
                try:
                    os.rmdir(os.path.join(base, sub))
                except OSError:
                    pass

    # THE ROOTS NOBODY COPIES ANY MORE. Everything above is reachable only from `COPY_DIRS`; this
    # is the half that reaches what has LEFT it. Nothing but this module writes a directory into
    # the export root, so a top-level directory that is neither a current `COPY_DIRS` root nor
    # one of the export's own (`EXPORT_OWN_DIRS`, plus the dot-directories that are repo and
    # forge machinery) can only be a root that used to be copied here and is not any more.
    #
    # Held roots are never seen here: being held means still being IN `COPY_DIRS`, so the first
    # branch of the loop above already skipped them and this one skips them again by name. Root
    # FILES are left alone deliberately -- `sync_tree`'s `COPY_FILES` withdrawal owns those, and
    # the marker files are ours.
    try:
        entries = sorted(os.listdir(SITE))
    except OSError:
        # Could not read the export root. Nothing may be withdrawn on the word of a failed read
        # -- the same rule `_live_root_state` enforces on the live side, and the same reason.
        silence.note("publish.py:export-root-unreadable")
        entries = []
    for name in entries:
        if name.startswith(".") or name in COPY_DIRS or name in EXPORT_OWN_DIRS:
            continue
        stale = os.path.join(SITE, name)
        if not os.path.isdir(stale):
            continue
        gone = 0
        for base, _dirs, files in os.walk(stale):
            gone += len(files)
        try:
            shutil.rmtree(stale)
        except OSError:
            # Locked, or partly removed. Recorded rather than swallowed: a withdrawn root
            # surviving the prune is precisely what this block exists to notice.
            silence.note("publish.py:prune-remove")
            continue
        removed += gone
        # SAID OUT LOUD, and named, because a whole subtree leaving the PUBLIC repo is the
        # largest single thing this loop can do and it must never happen quietly.
        print("withdrew the export copy of '%s/' -- %d file(s): it is no longer a COPY_DIRS "
              "root, so it is no longer published." % (name, gone))
    return removed


def sync_tree():
    """Refresh the export copy from the live project. Named files only, never a whole-tree copy.

    Copies forward, then PRUNES (`prune_export`): a refresh that only ever adds is half a
    refresh, and the missing half is the half that withdraws a file. -> files copied.

    A ROOT IT COULD NOT READ IS HELD, NOT WITHDRAWN. `wanted` is built by walking the live
    project, and `prune_export` deletes whatever is not in it -- so a `COPY_DIRS` root that
    failed to enumerate contributed NOTHING to `wanted` and the prune then deleted that entire
    subtree from the public copy. One failed syscall, and `src/` leaves the internet. The root
    classification (`_live_root_state`) and the mid-walk error collector below separate "not
    there any more", which still prunes, from "could not be read this cycle", which holds the
    subtree and says so. Holding costs a stale file for one cycle; the other way costs a
    withdrawal nobody asked for, in public, and the next cycle puts it back with a second commit
    that makes the history read as though somebody meant it.
    """
    os.makedirs(DOCS, exist_ok=True)
    n = 0
    wanted = set()
    held = set()

    def _hold(d, why):
        held.add(d)
        silence.note("publish.py:root-unreadable")
        print("publish: HOLDING the prune of '%s/' -- %s. The published copy keeps what it "
              "already has for that subtree; nothing is withdrawn on the word of a failed read."
              % (d, why), file=sys.stderr)

    for d in COPY_DIRS:
        root = os.path.join(HERE, d)
        state = _live_root_state(d)
        if state == "unavailable":
            _hold(d, "it is named in COPY_DIRS but could not be read as a live directory")
            continue
        if state == "gone":
            continue          # genuinely absent from the live project -- the prune withdraws it
        # A root can enumerate and a directory INSIDE it still fail. `os.walk` swallows that by
        # default and simply yields nothing for the branch, which lands in the same hole one
        # level down, so the errors are collected and the whole root is held if any arrive.
        walk_errors = []
        for base, dirs, files in os.walk(root, onerror=walk_errors.append):
            dirs[:] = [x for x in dirs if x != "__pycache__"]
            for f in files:
                if _is_skipped(f):
                    continue
                srcp = os.path.join(base, f)
                dstp = os.path.join(SITE, os.path.relpath(srcp, HERE))
                wanted.add(os.path.relpath(srcp, HERE).replace(os.sep, "/"))
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
        if walk_errors:
            _hold(d, "%d director(ies) under it could not be listed (%s)"
                     % (len(walk_errors), str(walk_errors[0])[:80]))
    withdrawn = []
    for f in COPY_FILES:
        srcp = os.path.join(HERE, f)
        dstp = os.path.join(SITE, f)
        state = _live_file_state(f)
        if state == "unavailable":
            # HELD, exactly as a COPY_DIRS root is. The published copy keeps the version it
            # already has for one more cycle; nothing is withdrawn on the word of a failed read.
            silence.note("publish.py:file-unreadable")
            print("publish: HOLDING the withdrawal of '%s' -- it is named in COPY_FILES but "
                  "could not be read as a live file. The published copy keeps the version it "
                  "already has; nothing is withdrawn on a failed read." % f, file=sys.stderr)
            continue
        if state == "live":
            # The same rsync-style short-circuit the COPY_DIRS loop above was given, for the
            # same reason. Without it these ~12 root files were re-copied unconditionally every
            # cycle, so the "synced N files" total could never be read as "what actually
            # changed" -- it reported a floor of 12 on a run that changed nothing.
            try:
                st_s, st_d = os.stat(srcp), os.stat(dstp)
                if st_s.st_mtime == st_d.st_mtime and st_s.st_size == st_d.st_size:
                    continue
            except OSError:
                pass
            shutil.copy2(srcp, dstp)
            n += 1
        elif state == "gone" and _may_delete_in_export() and os.path.exists(dstp):
            # PROVEN GONE from the live project -- the project root enumerated and this name was
            # not in it -- so withdraw it rather than leave the last copy standing in public for
            # ever. Guarded exactly as `prune_export` is, and it was not: through `_same_dir`
            # rather than `abspath` because junctions are in use on this machine, AND behind the
            # `.is-export-copy` marker, so a misresolved SITE reads as nothing to do instead of
            # as permission to delete out of a live tree.
            try:
                os.remove(dstp)
                withdrawn.append(f)
            except OSError:
                silence.note("publish.py:prune-remove")
    if withdrawn:
        # SAY IT, for the same reason `prune_export`'s count is said: a file leaving the PUBLIC
        # repo is a bigger event than a file entering it, and this withdrawal was silent.
        print("withdrew %d file(s) no longer in the live project: %s"
              % (len(withdrawn), ", ".join(sorted(withdrawn))))
    pruned = prune_export(wanted, held=held)
    if pruned:
        # SAY IT. A file leaving the public repo is a bigger event than a file entering it,
        # and the cycle line only ever reported arrivals.
        print("pruned %d file(s) no longer in the live project" % pruned)
    # Mark the copy AS a copy. Every module imports silence, which refuses to run from a tree
    # carrying this marker -- so a command aimed at the wrong directory fails loudly instead of
    # succeeding into nothing.
    with open(os.path.join(SITE, ".is-export-copy"), "w", encoding="utf-8") as f:
        f.write("Published copy of the Panscriptum. The project lives elsewhere." + chr(10))
    return n


def _swap(html, old, new, what):
    """One exact-literal rewrite of `dashboard.PAGE`, PROVEN to have fired. -> the new html.

    `render_page` made three bare `.replace()` calls and checked none of them. All three literals
    are present today, so it works -- and it is a string-presence transform standing in for a
    behaviour, which is the shape that fails silently. Re-quote or reformat one line of
    dashboard.py and the published page goes on fetching `'/api/state'`, now from the GitHub
    Pages origin, where nothing answers: a permanently dead panel on the phone, no error
    anywhere, and nothing to tell it from a slow network.

    So a swap that does not change the string REFUSES rather than passing the page through. The
    caller writes no file; `main()` prints the failure and exits non-zero. A stale published page
    is recoverable, a silently broken one is not noticed. (order 3d1efe60b4cf)
    """
    out = html.replace(old, new)
    if out == html:
        raise RuntimeError(
            "REFUSING TO RENDER THE PUBLISHED PAGE: the swap for %s found no %r in "
            "dashboard.PAGE, so the static page would keep the LIVE page's behaviour and fetch "
            "an endpoint that does not exist on GitHub Pages. dashboard.py has been re-quoted or "
            "reformatted; update the literal here to match it." % (what, old))
    return out


def render_page():
    """The published page IS the local page, with its data source swapped.

    `dashboard.PAGE` stays the single source of truth for the interface. A second copy would
    drift, and the drift would be invisible until somebody noticed the phone showing a panel the
    laptop did not have. So this generates: same markup, `./state.json` instead of the live
    endpoint, a slower refresh, and a line saying the numbers are a snapshot -- which a static
    page owes its reader and a live one does not.
    """
    import dashboard as D
    html = _swap(D.PAGE, "'/api/state'", "'./state.json'", "the data source")
    html = _swap(html, "setInterval(tick,5000)", "setInterval(tick,30000)",
                 "the refresh interval")
    html = _swap(
        html, "Refreshes every 5 seconds.",
        "This is a published SNAPSHOT: the machine pushes it on a timer, so the timestamp above "
        "is when the numbers were true, not now. The live panel is "
        "<code>python src/dashboard.py</code> on the machine itself.",
        "the snapshot caveat")
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
        f.write("".join(ln + chr(10) for ln in gitignore_lines()))
    # Pages serves from /docs on the default branch; .nojekyll stops Jekyll hiding anything.
    with open(os.path.join(DOCS, ".nojekyll"), "w", encoding="utf-8") as f:
        f.write("")
    if remote:
        git("remote", "remove", "origin", check=False)
        git("remote", "add", "origin", remote)
    return SITE


def write(state=None):
    """Land the page's data file. -> its path.

    THROUGH THE RETRY, LIKE EVERY OTHER SHARED FILE HERE. The rename was a bare `os.replace`,
    and on Windows that is DENIED outright while any reader holds the target open -- Norton
    scanning the just-copied export tree is the documented one on this machine (see the module
    docstring), and a person with `docs/state.json` open does it too. `silence.replace_retry`
    exists for exactly this and every sibling ledger writer uses it (`overwatch.save`,
    `overwatch.write_report`, `foreman`'s FOR_OWNER). Without it a transient lock raised
    `PermissionError` out of here into `main()`'s catch-all, which abandoned the WHOLE cycle --
    sync, render, write and push -- and returned rc=1 from a one-shot run for a lock that
    outwaits itself in under a second. Run33 order d875404d0bda.

    A DENIAL THAT SURVIVES THE RETRY IS STILL REPORTED. `replace_retry` answers False rather
    than raising, and swallowing that answer here would let the cycle print "wrote
    docs/state.json" over a file that did not move -- a published page frozen at yesterday's
    numbers while the log says it was written, which is the shape of the temp-tree publish this
    file's own SITE comment was written about.

    AND THROUGH `silence.write_json`, WHICH NAMES THE TEMP FILE AFTER THE WRITER. The scratch
    file was `docs/state.json.tmp` -- one fixed name, for a file this module itself permits two
    processes to write at once: the `--push --loop` daemon on its timer, and a person running a
    one-shot `--push` beside it (see `main()`, which deliberately exempts the one-shot from the
    singleton claim). Two writers then share the scratch file, the second truncates the first
    mid-`json.dump`, and whichever renames second can land a PARTIAL `state.json` on the public
    page -- the exact race `runguard._land`, `binding_health._land`, `suppressions._land`,
    `health.py` and `read.py:_chunk_put` were each repaired for. `write_json`'s temp name carries
    pid and thread, so the two writers cannot collide on it, and it lands through the same
    `replace_retry` this docstring is otherwise about.
    """
    os.makedirs(DOCS, exist_ok=True)
    data = state if state is not None else snapshot()
    if not silence.write_json(STATE_JSON, data, indent=1):
        silence.note("publish.py:state-json-denied")
        raise RuntimeError(
            "docs/state.json could not be replaced after five attempts -- a reader is holding "
            "it open. Nothing was written; the page keeps the numbers it already had.")
    return STATE_JSON


def _mutation_unsafe(busy, rec):
    """Does this `mutate.active()` reading mean files under src/ may be deliberately corrupt?

    FAILS CLOSED on anything it does not recognise. A lock with no `sandboxed` key -- an older
    run, or some future in-place mode -- still counts as unsafe, because "I cannot tell whether
    the tree is corrupt" has never been permission to publish it.
    """
    return bool(busy) and not (isinstance(rec, dict) and rec.get("sandboxed") is True)


def _mutation_observation():
    """Take a `mutate.active()` reading for a caller that needs one BEFORE the tree is copied.

    -> the `(busy, record)` pair, or None if the interlock could not be asked at all.

    None is NOT "clear". `push()` refuses outright on an unimportable `mutate`, so a reading that
    could not be taken here meets the same refusal one step later instead of being waved through;
    this only declines to duplicate that refusal in a run that is not pushing anything anywhere.
    Separate from `push()` precisely so it can be taken at the moment the BYTES are taken.
    """
    try:
        import mutate as _MUT
        return _MUT.active()
    except Exception:
        silence.note("publish.py:mutation-observation")
        return None


class PushHeld(RuntimeError):
    """A commit was made and did NOT reach the public repo.

    Its own type because `push()` used to answer this with a bare `False` -- the SAME answer it
    gives for "nothing had changed and nothing needed to go" -- and `main()` printed "no change
    to push" for both, with rc=0. So a one-shot `--push` by a person could commit work, fail to
    land it, tell them on stdout that there had been nothing to send, and exit 0; only a line on
    stderr disagreed, and stderr is what a wrapper throws away. That is the defect `main()`'s own
    "A REFUSED PUBLISH MUST NOT REPORT SUCCESS" comment was written about, still standing in the
    same function.

    RAISED, NOT RETURNED, deliberately: a return value can be read as success by any caller that
    does not know to look for a third state, and the whole fault here was a caller not knowing.
    An exception cannot be mistaken for the quiet no-op by anybody. `main()`'s existing handler
    prints it and sets rc=1; the loop still retries next cycle, which is the documented and
    correct behaviour for a held push.
    """


def push(message=None, before=None):
    """Commit and push. -> True if it landed, False if there was nothing to send.

    `before` is an earlier `mutate.active()` reading (`_mutation_observation()`), taken by the
    caller BEFORE it copied src/ into the export. Optional and defaulting to None so every
    existing caller keeps working; supplied, it closes the window described below.

    THREE OUTCOMES, NOT TWO. `True` means the commit reached origin/main. `False` means the tree
    was clean and no commit was made -- a genuine no-op, and the only state that may read as
    "nothing to push". A commit that was made but could not be landed raises `PushHeld`: see
    that class for why it is not a third return value.

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
    # FAIL CLOSED, exactly as `main()` does for `escalation.py` below. This read
    # `except ImportError: pass`, which meant a deleted, renamed or unparseable
    # `ledger_guard.py` switched the last ledger-integrity check off silently -- no print, no
    # `silence.note`, no escalation -- while the comment above went on promising that a
    # truncated HANDOFF could not be published. That is Hard Rule -1's own incident wearing
    # different clothes for the second time in one file: the run #31 fix was applied to the
    # halt import twenty lines down and not to this one. A push that cannot ask whether the
    # ledgers are intact has no business pushing, and the ledgers travel to the PUBLIC repo.
    # Run33 order 6c1bb80ecc57.
    try:
        import ledger_guard as _LG
    except ImportError as _lg_gone:
        raise RuntimeError(
            "REFUSING TO PUSH: the ledger guard (src/ledger_guard.py) could not be imported "
            "(%s), so the ledgers cannot be checked before they are published. Restore the "
            "module, or push by hand once a person has read the ledgers." % _lg_gone) from _lg_gone
    _LG.assert_intact()

    # NEVER PUBLISH DELIBERATELY BROKEN CODE. `mutate.py` corrupts real source files on disk --
    # that is its entire method -- and on 2026-08-25 a push landed in the middle of a mutation
    # run and shipped a `prose_gate.py` whose `cited_fraction()` matched every source EXCEPT the
    # one it was asked about. To GitHub. The gate protecting the library, published inverted.
    #
    # Nothing caught it: the secret scan does not read logic, `ledger_guard` checks the ledgers,
    # and the drill was itself confused by the same corruption. The only thing that can know is
    # the process doing the corrupting, so it now says so in a lock file and this refuses.
    #
    # FAIL CLOSED, like the two arms above it. This was the third `except ImportError: pass`
    # in this file, and the last one left: a deleted, renamed or unparseable `mutate.py`
    # silently switched off the guard that exists BECAUSE a push once shipped a deliberately
    # corrupted `prose_gate.py` to GitHub. The swallow made the interlock's own absence the
    # condition under which it stops working, which is the one condition it has to survive.
    # (run #33, order 92893f250570.)
    try:
        import mutate as _MUT
    except ImportError as _mut_gone:
        raise RuntimeError(
            "REFUSING TO PUSH: the mutation interlock (src/mutate.py) could not be imported "
            "(%s), so nothing can say whether files in src/ are deliberately corrupt right "
            "now. Restore the module, or push by hand once a person has read src/." % _mut_gone) from _mut_gone
    # ONLY WHEN THE LIVE TREE IS ACTUALLY AT RISK. `mutate.py` was rewritten to work in a
    # sandbox and never opens a file under `src/` for writing, so a mutation run is no longer a
    # reason to hold a push -- and treating it as one blocked a legitimate publish for the
    # several HOURS a full run takes. A safety that stops correct work every night is a safety
    # somebody deletes, and then it is not there for the case it was written for.
    # `_mutation_unsafe` is where the fail-closed rule for an unrecognised lock now lives.
    #
    # ASKED ON BOTH SIDES OF THE COPY. The reading below is taken at PUSH time -- several seconds
    # and one whole tree copy after `sync_tree` read src/ -- so the window it covers is not the
    # window the bytes were captured in. A mutation run that began after `sync_tree` started and
    # ended before this line would leave deliberately-corrupt bytes staged with the interlock
    # seeing nothing at all. Low likelihood while `mutate.py` stays sandboxed, but the interlock's
    # stated premise is the day it does not, and a guard whose window misses the event is a guard
    # that reports clear. So the caller's earlier reading is checked too, and EITHER observation
    # saying a non-sandboxed run was live refuses the push. (order d56228616f9c)
    readings = [("at push time", _MUT.active())]
    if before is not None:
        readings.append(("before the tree was copied into the export", before))
    for _when, (_busy, _rec) in readings:
        if _mutation_unsafe(_busy, _rec):
            raise RuntimeError(
                "REFUSING TO PUSH: a mutation run was active %s and had NOT declared itself "
                "sandboxed, so files in src/ may be deliberately corrupt right now (%s)."
                % (_when, json.dumps(_rec, default=str)[:200]))

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
    held_what = "the commit was made on the local export branch"
    if not porcelain:
        # A CLEAN WORKTREE IS NOT AN EMPTY OUTBOX. `git status --porcelain` answers "is there
        # anything new to COMMIT"; the question this branch is about is "is there anything to
        # SEND", and the two part company the moment a previous cycle committed and could not
        # push. Asked BEFORE the no-op return, so a commit stranded on the local branch can
        # never again be reported as "nothing to push" with rc=0. (order 3778bc42499f)
        ahead, why = _unpushed()
        if not ahead:
            if ahead is None:
                # Not proven held, and not proven landed either. Said out loud rather than
                # folded into the no-op, because "I could not tell" reported as "nothing to
                # send" is the whole shape of this fault.
                silence.note("publish.py:push-ahead-unknown")
                print("publish: could not tell whether the local export branch is ahead of "
                      "origin/main (%s); reporting no change to push on the worktree alone."
                      % why, file=sys.stderr)
            return False        # NOTHING TO SEND. The only outcome that may read as a no-op.
        # STRANDED, NOT IDLE -- and the remedy is to SEND IT, not merely to complain about it.
        # There is no new commit to make, so the commit step is skipped and everything below it
        # runs exactly as it would have on the cycle that failed. If it fails again the reader
        # is told so as a `PushHeld` with rc=1, which is the outcome this order exists about;
        # if it succeeds, a backlog that used to sit there for ever clears itself.
        print("publish: the export worktree is clean, but %d commit(s) never reached "
              "origin/main (%s) -- retrying the push rather than reporting no change."
              % (ahead, why))
        held_what = ("%d commit(s) from an earlier cycle are still on the local export branch"
                     % ahead)
    else:
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
        silence.note("publish.py:push-held")
        raise PushHeld(
            "PUSH HELD -- " + held_what + " and NOTHING reached "
            "the public repo: the rebase onto origin/main failed (" + str(e)[:120]
            + "). The export is now ahead of origin; the next cycle retries on a fresh tree. "
              "This is not 'no change to push'.") from e
    # THE PUSH ITSELF IS HELD, NOT RAISED GENERICALLY. This was a bare `git(...)`, so a refused
    # push (403 on a wrong credential, a rejected update, a dead network) left the commit on the
    # local branch and came out as a plain `RuntimeError` -- clipped to 180 characters by
    # `main()`'s generic handler, never saying that a commit had been made and had not landed,
    # and leaving the next cycle to find a clean worktree and print "no change to push".
    try:
        git("push", "-q", "-u", "origin", "main")
    except RuntimeError as e:
        silence.note("publish.py:push-held")
        raise PushHeld(
            "PUSH HELD -- " + held_what + " and the push to "
            "origin/main was REFUSED (" + str(e)[:160] + "). Nothing reached the public repo; "
            "the export is now ahead of origin. The next cycle retries. This is not 'no change "
            "to push'.") from e
    # AND THE PUSH IS CONFIRMED, not assumed from rc=0. `git push` is the one step here whose
    # success this module cannot otherwise observe, and the whole family of faults this function
    # documents is a publish that reported success while the public repo stood still.
    ahead, why = _unpushed()
    if ahead:
        silence.note("publish.py:push-held")
        raise PushHeld(
            "PUSH HELD -- `git push` reported success, but %d commit(s) are STILL not on "
            "origin/main (%s). The commit has not reached the public repo." % (ahead, why))
    if ahead is None:
        silence.note("publish.py:push-held")
        raise PushHeld(
            "PUSH HELD -- `git push` reported success, but whether the commit actually reached "
            "origin/main could not be confirmed (%s). Unconfirmed is not landed; check the "
            "export repo by hand." % why)
    return True


MAINTENANCE_GUARD = os.path.join(HERE, "state", "MAINTENANCE_RUN.json")
MAINTENANCE_HEARTBEAT_SECONDS = 15 * 60


def maintenance_shift_live(path=None, now=None):
    """Is a maintenance run part-way through editing this tree? -> (bool, why).

    THE FOURTH INTERLOCK, AND THE ONE NOBODY HAD ASKED FOR (order bb4fa3f3c9f1). `push()` is
    well defended, but each existing lock answers a DIFFERENT question: the credential scanner
    asks "is a secret staged", `mutate.active()` asks "is mutate.py deliberately corrupting
    source right now", `claim_singleton` asks "is there a second publisher", and `assert_clear`
    asks "is the library halted" -- and that last one is read once in `main()` at startup, so a
    loop that has been up for hours is not re-asking it. Not one of them asks whether somebody
    is in the middle of CHANGING this tree.

    Measured on 2026-08-29, from the export repo's own commit log, while it was happening. The
    four cycles before the maintenance shift began moved no source at all: 21:35, 21:45, 21:55
    and 22:06 are each "N data/site file(s)". The shift then started sixteen agents editing
    disjoint sets of modules at 22:14. At 22:16:29, two minutes later, commit 5f0d5e1 pushed
    five source files -- compress_store, coverage, escalation, retry_synthesis, tuning -- to a
    PUBLIC repository. Those five belonged to three different agents, none of which had
    finished, verified or self-checked its work. At 22:26:58 commit 8123ef3 pushed forty-one
    more. A public repository received, twice in eleven minutes, an arbitrary instant of a
    sixteen-way concurrent edit.

    `mutate.py`'s interlock is the exact precedent and this is built to match it: after the
    2026-08-25 incident the conclusion drawn was "only the process doing the corrupting can
    know, so it says so in a lock file and publish refuses". A maintenance shift is the same
    shape of writer and already keeps the same kind of lock file -- `state/MAINTENANCE_RUN.json`
    carries `done:false` and a heartbeat refreshed every two minutes for precisely this reason.
    Nothing read it except the next maintenance run.

    FAILS OPEN, deliberately, and this is the opposite of `subsystem_stopped`'s rule. An
    unreadable or missing guard file means PUBLISH. Not being able to look is not a reason to
    stop publishing, and the cost of the two mistakes is asymmetric: failing closed here would
    let one malformed JSON file wedge the publisher silently and indefinitely, which is a worse
    outcome than one cycle of half-finished source in a repo the next cycle overwrites. A
    heartbeat older than MAINTENANCE_HEARTBEAT_SECONDS is treated as a crashed run, not a live
    one, for the same reason -- a shift that died holding the guard must not stop publishing
    forever.
    """
    now = time.time() if now is None else now
    try:
        with open(path or MAINTENANCE_GUARD, encoding="utf-8") as f:
            rec = json.load(f)
        if not isinstance(rec, dict):
            return False, "guard file is not an object; failing open"
    except FileNotFoundError:
        return False, "no maintenance guard on disk"
    except Exception as e:
        silence.note("publish.py:maintenance-guard")
        return False, "maintenance guard unreadable (%s); failing open" % type(e).__name__
    if rec.get("done"):
        return False, "the last maintenance run finished"
    beat = rec.get("heartbeat")
    if not isinstance(beat, (int, float)):
        return False, "guard carries no usable heartbeat; failing open"
    age = now - float(beat)
    if age > MAINTENANCE_HEARTBEAT_SECONDS:
        return False, ("guard held by %r but its heartbeat is %.0f minutes old (limit %d), so "
                       "the run is treated as crashed, not live"
                       % (rec.get("agent", "?"), age / 60.0, MAINTENANCE_HEARTBEAT_SECONDS // 60))
    return True, ("a maintenance run (%r) holds the guard and its heartbeat is %.0fs old, so "
                  "src/ is being edited right now" % (rec.get("agent", "?"), age))


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
            "imported (%s), so the halt cannot be read. Hard Rule -1." % _esc_gone) from _esc_gone
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
    import codewatch
    # ONE OF ME. Two `publish.py` daemons were observed running seventeen seconds
    # apart on 2026-08-25 after a restart race, and two writers into one export repo
    # is the failure `push()` documents at length. Fails open: if the process table
    # cannot be read this starts anyway, because not being able to look is not a
    # reason to take the job down.
    # ONLY IN LOOP MODE, and this needed correcting within the minute: the guard was
    # unconditional at first and immediately refused a hand-run one-shot `--push`
    # because the standing daemon was up. A one-shot is not a second daemon; it is a
    # person doing one thing deliberately, and a safety that blocks the operator
    # from acting is a safety that will be removed.
    if a.loop:
        codewatch.claim_singleton("publish")
        codewatch.stamp("publish")
    while True:
        try:
            # THE HALT IS RE-ASKED EVERY CYCLE (order 5905045ff433). `main()` asserts it once at
            # startup, above, and this loop used to run for hours without asking again -- so an
            # OWNER halt raised by ANY other job while the daemon was up did not stop it, and it
            # went on committing and pushing the whole tree to the PUBLIC repo on its timer until
            # somebody killed the process by hand.
            #
            # `codewatch.exit_if_stale` below does NOT cover this. It fingerprints `src/` and
            # fires when CODE changes; a halt is data in a state file. So this is exactly Hard
            # Rule -1's own 2026-08-25 incident in the dimension the codewatch fix did not close:
            # that one was "the daemon has stale CODE", and this is "the daemon has stale STATE"
            # -- a halt raised at 19:00 stays unread by the 14:28 daemon for ever, because src/
            # never changed. publish.py was the ONE standing daemon in the tree not doing this,
            # and the only one whose action is irreversible and outward-facing.
            #
            # THE HOUSE PATTERN, COPIED DELIBERATELY from overnight.py's cycle loop, including
            # the re-import: a deleted or unparseable escalation.py must be a SystemExit here
            # rather than something the `except Exception` below swallows into "rc=1, loop
            # again". `assert_clear` re-reads the halt file on every call, so this costs one file
            # read per cycle.
            #
            # AND IT BREAKS, IT DOES NOT RETRY. Letting SystemHalted fall into the generic
            # handler would set rc=1 and loop again ten minutes later, for ever: a halted library
            # must STOP the publisher, not make it knock repeatedly.
            try:
                import escalation as _ESC_CYCLE
            except ImportError as _esc_gone_cycle:
                raise SystemExit(
                    "STOPPING: the escalation chain (src/escalation.py) could not be imported "
                    "mid-loop (%s), so the halt can no longer be read. Hard Rule -1."
                    % _esc_gone_cycle) from _esc_gone_cycle
            try:
                _ESC_CYCLE.assert_clear("publish.py cycle")
            except _ESC_CYCLE.SystemHalted as _halted:
                print(str(_halted).splitlines()[0])
                print("STOPPING THE PUBLISHER: a halt is standing, so this daemon takes no more "
                      "bytes and pushes nothing further. Only a person may lift it.")
                rc = 1
                break
            # A MAINTENANCE SHIFT IS EDITING THIS TREE -- TAKE NO BYTES THIS CYCLE (order
            # bb4fa3f3c9f1). Read BEFORE `sync_tree`, because the fault is the copy, not the
            # push: once half-finished source is in the export, the commit is only the last
            # step. See `maintenance_shift_live` for the measurement that produced this.
            #
            # LOOP MODE ONLY, exactly as `claim_singleton` above is loop-mode only, and for the
            # same reason in the same words: a one-shot is not a daemon, it is a person -- or a
            # maintenance run's own final step -- doing one thing deliberately. The shift that
            # sets this guard must still be able to publish its own results at the end of the
            # shift, and a guard that blocked its holder would be a guard nobody could ship with.
            if a.loop:
                _busy, _why = maintenance_shift_live()
                if _busy:
                    print("skipping this cycle: " + _why)
                    codewatch.exit_if_stale("publish")
                    time.sleep(a.loop * 60)
                    continue
            # THE INTERLOCK IS READ BEFORE THE BYTES ARE TAKEN, not only at push time. `push()`
            # asks `mutate.active()` after `sync_tree` has already copied src/ into the export,
            # so a mutation run entirely inside that gap is invisible to it. Read here as well
            # and handed down; `push()` refuses if EITHER reading saw a non-sandboxed run.
            # Only on a pushing cycle -- a render-only run puts nothing in front of anybody.
            before_mutation = _mutation_observation() if a.push else None
            n = sync_tree()
            render_page()
            write()
            # Name the destination every cycle. The loop reported "synced 14 files, wrote
            # docs/state.json" four times an hour for an unknown number of days while writing
            # into a temp-directory clone nobody knew existed (see SITE above). A line that
            # says what it did and not WHERE it did it cannot expose that class of fault.
            print(f"synced {n} files, wrote docs/state.json  ->  {SITE}")
            if a.push:
                # `push()` now has only two RETURN values, and both are honest ones: it landed,
                # or there was nothing to land. The third outcome -- committed but held -- comes
                # out as `PushHeld` and is caught below, where it prints and sets rc=1, because
                # a held push reported as "no change to push" with rc=0 is this comment block's
                # own rule broken one line further down the function.
                print("pushed" if push(before=before_mutation) else "no change to push")
        except PushHeld as held:
            # Printed WHOLE, not clipped to 180 characters like a generic failure, and on
            # stdout: the previous version of this state said its only true word on stderr.
            silence.note("publish.py:main-push-held")
            print(str(held))
            rc = 1
        except Exception as e:
            silence.note("publish.py:main")
            print(f"publish failed: {type(e).__name__}: {str(e)[:180]}")
            rc = 1
        if not a.loop:
            return rc
        # PICK UP CODE CHANGES. A running process is a photograph of the source as it was
        # when it started, and on 2026-08-25 a `publish.py --loop` daemon from 14:28 pushed
        # deliberately-corrupted files to a public repo because the guard written to stop it
        # at 19:00 was never in its memory. Exits with rc=17 on purpose; the keeper's STANDING
        # set restarts it within five minutes running the current code. Budgeted and settled,
        # so an edit storm cannot turn this into a respawn loop -- see codewatch.py.
        codewatch.exit_if_stale("publish")
        time.sleep(a.loop * 60)


if __name__ == "__main__":
    sys.exit(main())
