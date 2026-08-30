"""SECOND OPINION — the same three questions, asked again by code this project did not write.

WHY THIS EXISTS AT ALL. The owner's standing requirement is that no two safety layers may share
a failure mode. Every detector in `src/` was written by the same author, in the same week, from
the same understanding of what a defect looks like — so `liveness.py`, `silence.py` and
`publish.scan_for_secrets` are three layers with ONE blind spot between them. If the author's
model of "swallowed exception" is wrong, all three are wrong together and all three report green
together. That is not defence in depth; it is one opinion, stated three times.

The cheapest way to buy genuine independence is not to write a fourth detector. It is to run
somebody else's, built from a different theory, maintained by people who have never seen this
codebase, and to treat DISAGREEMENT as the finding.

WHAT WAS ADOPTED, AND WHAT IT REPLACED — WHICH IS NOTHING. Three tools, chosen after actually
running them against `src/` on 2026-08-25 rather than from their README claims:

    ruff             hundreds of blind-except sites plus a smaller pile of try/except/pass and
                     try/except/continue (run `ruff check --statistics` for today's exact count),
                     plus the bug classes no detector here has: B023 loop-variable capture in a
                     closure, B008 call-in-default-argument, B904 raise-without-from. It is a
                     compiled Rust binary and it RUNS on this machine, which DuckDB does not.
    vulture          dead code by a different method — it counts unused VARIABLES and ATTRIBUTES,
                     which `liveness.py` does not look at at all (it stops at module-level defs).
                     ITS ONE SCORED WIN, AND IT IS SPENT: vulture flagged the `from_m` parameter
                     of `descending_ladder.shrink_report` as accepted-and-never-read, and that
                     was true and is now REPAIRED — the report echoes `from_m`, `to_m` and
                     `is_descent` back to its caller, and that function's own docstring records
                     the repair. Cited here by SYMBOL rather than by line, because the line moved
                     twice while the sentence claiming it did not: this entry used to read
                     `descending_ladder.py:129 from_m`, and 129 is now a different function
                     entirely. A line number in prose is a citation with a decay rate.
                     What it reports on this tree today is a handful of unused variables at 100%
                     — `socktype` in `verify_math._StubNet.getaddrinfo`, `tmp_`/`dst_` in the
                     `drill.py` net that stubs `silence.replace_retry` — and every one of them is
                     a parameter that exists to MATCH A SIGNATURE the stub is standing in for, so
                     every one is a false positive. Stated rather than quietly dropped, because
                     an advertisement for a detector that only ever lists its hits is the same
                     overstatement this module was written to catch in the house detectors. Its
                     value is the CLASS it can see at all, not a running score.
                     NO COUNT IS PINNED IN THIS PARAGRAPH, on purpose. It was four when this was
                     written and three an hour later, because another shift agent touched
                     `drill.py`; the two line numbers moved in the same hour. Run
                     `python src/secondopinion.py` for today's, which is the only way to know it.
    detect-secrets   Yelp's scanner, with a baseline file that is the same idea as
                     `suppressions.py` arrived at independently. It found ZERO in `src/` and
                     `prompts/`, which is the most useful thing it could have said: it AGREES
                     with the hand-written scrubber, from a completely different rule set.

None of the three replaces anything. `liveness.py` finds dead code vulture cannot (it reasons
across the whole package, vulture does not), `silence.py` measures a narrower and more specific
defect than ruff's blanket BLE001, and `publish.scan_for_secrets` is what actually gates the
push. These run BESIDE them. The output that matters is where the two answers differ.

HOW A DISAGREEMENT IS READ, because it cuts both ways and only one direction is obvious:

    THEIRS, NOT MINE   the outside tool sees something my detector is blind to. File it.
    MINE, NOT THEIRS   my detector sees something a mature, widely-used tool does not. That is
                       either a genuinely sharper check or a false positive, and both are worth
                       knowing. Filed at INFO, addressed to RUN, never auto-suppressed.

AND THE FAILURE MODE THIS MODULE MUST NOT HAVE. An optional tool that is not installed produces
no findings, and no findings looks exactly like a clean bill of health — the standing lesson of
this project wearing a new hat. So `run()` NEVER returns an empty finding list for an absent
tool. It returns the status `NOT INSTALLED`, and `report()` prints it as loudly as a failure.
Absence is a third answer here, distinct from clean.

It is deliberately FAIL-OPEN rather than fail-closed, and that is the one place this module
departs from house doctrine, for a stated reason: a linter missing from a fresh checkout is not
evidence that the library is unsafe, and halting the park because an optional second opinion is
unavailable would make a safety indistinguishable from a fault — which is the exact confusion
that caused this project's longest outage. It escalates to JANITOR (record it), not to OWNER.
"""
import argparse
import json
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, SRC)
import silence  # noqa: E402

# Where pip put the console scripts on this machine. Looked up rather than assumed: the
# miniconda Scripts directory is NOT on PATH here, so a bare `ruff` resolves to nothing and the
# whole module would report NOT INSTALLED for three tools that are sitting on disk.
_SCRIPTS = os.path.join(os.path.dirname(sys.executable), "Scripts")

# Every child spawned here runs windowless. This module ran four subprocesses without it
# and `verify_math` failed the run within the minute: on Windows a bare `subprocess.run`
# flashes a console window, and a maintenance pass that pops four black boxes onto the
# owner's desktop is a maintenance pass they will turn off. Held as a module constant so
# a new spawn cannot quietly omit it.
_NO_WIN = getattr(subprocess, "CREATE_NO_WINDOW", 0)


def _exe(name):
    """-> a runnable path for a console script, or None. Checks the interpreter's own Scripts
    directory before PATH, because on this machine that directory is not on PATH."""
    for cand in (os.path.join(_SCRIPTS, name + ".exe"),
                 os.path.join(_SCRIPTS, name),
                 name):
        try:
            r = subprocess.run([cand, "--version"], capture_output=True, creationflags=_NO_WIN, timeout=30)
            if r.returncode == 0:
                return cand
        except Exception:
            silence.note("secondopinion.py:_exe")
    return None


# The rules worth running, and what each one is a second opinion ABOUT. A tool with no stated
# counterpart is a tool nobody can judge the output of, so every entry names one.
RUFF_RULES = "E,F,B,BLE,S110,S112,PLE,PLW,RUF,SIM"
RUFF_IGNORE = "E501,RUF001,RUF002,RUF003"          # line length and the charter's real typography

COUNTERPART = {
    "BLE001": "silence.py", "S110": "silence.py", "S112": "silence.py",
    "F811": "liveness.py", "F841": "liveness.py", "F821": "liveness.py",
    "vulture": "liveness.py", "detect-secrets": "publish.scan_for_secrets",
}

# HOUSE STYLE THIS CODEBASE DELIBERATELY DIVERGES ON, each with the reason written down.
#
# These are still COUNTED and still PRINTED -- they are simply not filed as work orders. The
# distinction matters: a rule dropped from the report is a rule nobody can re-argue, whereas a
# rule that appears in the count with a stated reason stays answerable. This is `suppressions.py`
# doctrine applied to somebody else's detector: an exemption with no reason attached is how a
# real finding gets waved through the second time.
#
# The test for belonging here is "would fixing every instance make this codebase WORSE or merely
# different". Anything where the answer is "better" does not belong here, however many sites it
# has -- BLE001 alone runs into the hundreds (see `ruff check --statistics` for today's count)
# and it is still a real finding, which is why it is NOT in this list.
#
# Kept to rules RUFF_RULES actually selects. UP031, ISC004, C408 and DTZ005 (pyupgrade,
# implicit-str-concat, comprehensions, flake8-datetimez) named as waivers here previously, but
# RUFF_RULES selects only E,F,B,BLE,S110,S112,PLE,PLW,RUF,SIM -- none of those four categories --
# so those entries could never match a finding. A waiver nothing can ever trigger is not a
# recorded divergence, it is a false reading of how many rules this codebase argues with.
NOT_FILED = {
    "E402": "src/ modules do sys.path.insert before importing siblings; the import cannot precede it",
    "RUF100": "noqa comments kept where a rule was once enabled; harmless and self-documenting",
    "PLW1510": "subprocess return codes are checked explicitly by the caller, not by check=True, "
               "because a non-zero exit is often the expected answer here",
    "B007": "unused loop variables are frequently the readable name for a discarded half of a pair",
    "RUF059": "the same shape as B007 one level up: `a, b = f()` keeps a readable name for the "
              "half of a tuple-return a caller does not need (verified across corpus_db.py, "
              "pipeline.py, tiers.py, sevenfold.py, feats.py, hostcheck.py, pick_model.py -- "
              "every sampled site was a discarded return-value member, not a forgotten one)",
    "PLW0603": "the lazy-singleton module cache (`global _X; if _X is None: _X = ...`) appears "
               "independently in address.py, cascade_bridge.py, endpoint.py, read.py, silence.py, "
               "weave_index.py and others -- a deliberate, thread-guarded pattern for a "
               "build-once module resource, not drift toward global mutable state",
    "PLW2901": "every site sampled (backfill.py, cascade_bridge.py, catalogue_codex.py, feats.py, "
               "ledger_guard.py, manifest_builder.py, rosetta.py, scout.py) reassigns the loop "
               "variable to its own normalized or copied form (`block = block.strip()`, "
               "`r = dict(r)`) and only the normalized form is read afterward in that same "
               "iteration -- the safe, common idiom this rule also flags, not the closure-capture "
               "bug B023 exists to catch (checked separately, and fixed where found)",
    "B008": "both current sites are benign: pipeline.py's `_n=len(batch)` default deliberately "
            "freezes the loop-current value at function-definition time so a deferred callback "
            "cannot see `batch` drift in a later iteration -- removing it would REINTRODUCE the "
            "exact B023 closure bug this codebase has already been bitten by once; sevenfold.py's "
            "`depth=len(TIERS)` reads a fixed module-level tuple literal evaluated once at import, "
            "never mutated, so there is no call-time staleness for B008 to protect against",
}

# BLE001, S110 AND S112 WERE WAIVED HERE ON 2026-08-27 AND THE WAIVERS WERE REVERTED THE SAME
# DAY. They are recorded rather than deleted, because the way they were wrong is the thing worth
# keeping.
#
# Both rested on the same premise: that `silence.audit()` already treats its SILENT handlers as
# "an accepted category rather than a queue of individual fixes". It does not. Run it: it prints
# `each of these can turn a failure into a plausible negative result`, lists all 152 by file and
# line, and EXITS 1. The house detector does not accept them; it complains about them. A waiver
# whose stated reason is that another tool has already blessed these sites is void when that tool
# has done the opposite.
#
# The BLE001 entry went further and cited this module's own docstring as authority for waiving
# it. The docstring says the reverse, twenty-odd lines above the map: "BLE001 alone runs into the
# hundreds ... and it is still a real finding, which is why it is NOT in this list." It was the
# named example of what must NOT be waived, and it was waived by citing the sentence that names
# it.
#
# The cost was measurable: 531 BLE001 + 63 S110/S112 sites is 594 sites, and 594 of the 1,002
# live findings that shift is about 59%, not the 96% this paragraph used to claim here -- an
# arithmetic error in the very sentence defending the policy against arithmetic like this. Still
# damning at the correct number: the outside opinion would have gone on reporting while a bit
# under three in five of what it selects never reached the queue. That is precisely the failure
# this whole module exists to prevent -- an independent checker that has been quietly talked out
# of its independence -- and it is a worse one than any of the individual findings, because the
# report would have kept looking healthy.
#
# Re-measured live, this shift, after the revert: 402 of 1,021 ruff findings are waived under
# NOT_FILED (about 39%), and BLE001/S110/S112 are not among the waived codes -- they are filed
# as findings, exactly as this policy requires. The policy is behaving correctly; only the
# sentence above documenting the near-miss had its own arithmetic wrong.
#
# The test at the top of NOT_FILED stands and is the only test: would fixing every instance make
# this codebase WORSE or merely DIFFERENT? "There are a lot of them" is not that test, and
# neither is "another detector also sees them".

# SIM115 WAS REMOVED FROM NOT_FILED HERE, for the same reason the BLE001/S110/S112 waivers above
# were reverted: its written reason did not describe its own sites. The reason on record was "a
# handle outlives one block", but a sample of the 185 sites (sample of 20, seeded, plus every
# `_BAD_CHARS` self-check site, which alone accounts for dozens) is overwhelmingly the single-
# expression idiom `open(path, encoding=...).read()` / `json.load(open(path, ...))` --  the
# handle is created, consumed and dropped inside one expression, so it does not outlive one
# block, it does not outlive one STATEMENT. Wrapping that in `with open(...) as f:` costs one
# extra line and changes nothing about behaviour, so this fails the test above on its own terms:
# fixing every instance would be merely DIFFERENT at worst and arguably BETTER (not dependent on
# CPython's refcounting to close the handle promptly), never WORSE. A waiver that cannot pass its
# own module's test is not a waiver, so SIM115 now files like any other real finding.


# RETURNCODE, NOT JUST STDOUT. `ran_clean()` treats status == "RAN" and an empty finding list as
# "this tool looked and saw nothing" -- the exact clean bill of health `run()`'s own docstring
# says an absent tool must never produce. But ruff exits 2 (a bad --select selector, a path that
# does not exist) and detect-secrets exits 2 (a bad flag, a bad subcommand) writing NOTHING to
# stdout and the reason to stderr instead -- verified by running both here on 2026-08-27.
# `json.loads(r.stdout or "[]")` then parses the placeholder, not the tool's answer, and the
# three runners below returned "RAN", [] for a tool that never actually ran. None of them read
# `r.returncode` at all. Each now does, and treats anything outside the codes that mean "the tool
# ran and told me its verdict" as a failure to report, not a clean pass. Order 12694407d245.
def _ruff(paths):
    exe = _exe("ruff")
    if not exe:
        return "NOT INSTALLED", []
    r = subprocess.run([exe, "check", "--output-format", "json",
                        "--select", RUFF_RULES, "--ignore", RUFF_IGNORE, *list(paths)],
                       capture_output=True, creationflags=_NO_WIN, text=True, timeout=300)
    # ruff's own contract: 0 = no violations, 1 = violations found (real answer, keep going).
    # Anything else is ruff refusing to run at all -- the CLI itself was misused -- and its
    # explanation went to stderr while stdout stayed empty.
    if r.returncode not in (0, 1):
        return ("TOOL ERROR (ruff rc=%d): %s"
                % (r.returncode, (r.stderr or r.stdout or "?").strip()[:200])), []
    try:
        rows = json.loads(r.stdout or "[]")
    except Exception:
        silence.note("secondopinion.py:_ruff")
        return "UNPARSEABLE OUTPUT", []
    out = []
    for x in rows:
        loc = x.get("location") or {}
        out.append({"tool": "ruff", "code": x.get("code") or "?",
                    "file": os.path.basename(x.get("filename") or ""),
                    "line": loc.get("row") or 0,
                    "message": (x.get("message") or "")[:160]})
    return "RAN", out


def _vulture(paths, min_confidence=90):
    """Confidence 90, not 60. At 60 vulture reports every uncalled public function in a library
    of entry points and dispatch tables -- 86 of them here, almost all legitimate -- and a
    detector whose output is mostly noise gets ignored, which is the same as not having it.
    At 90 it reports only what it is sure of, which is the part `liveness.py` cannot see anyway.
    """
    exe = _exe("vulture")
    if not exe:
        return "NOT INSTALLED", []
    r = subprocess.run([exe, *list(paths), "--min-confidence", str(min_confidence)],
                       capture_output=True, creationflags=_NO_WIN, text=True, timeout=300)
    out = []
    for line in (r.stdout or "").splitlines():
        parts = line.split(":", 2)
        if len(parts) != 3:
            continue
        try:
            lineno = int(parts[1])
        except ValueError:
            continue
        out.append({"tool": "vulture", "code": "vulture",
                    "file": os.path.basename(parts[0]),
                    "line": lineno, "message": parts[2].strip()[:160]})
    # VULTURE'S CONTRACT, MEASURED ON THIS MACHINE 2026-08-27 RATHER THAN ASSUMED:
    #   rc=0  it looked and found nothing
    #   rc=3  it looked and FOUND DEAD CODE -- the normal, useful outcome
    #   rc=1  a bad PATH: an "Error: ... could not be found" line that LOOKS like
    #         `path:line:message`, fails `int(parts[1])` above, and is silently dropped
    #   rc=2  argparse rejected a flag
    #
    # An earlier version of this guard admitted only 0 and 1, so every run in which vulture
    # actually did its job came back as `TOOL ERROR (vulture rc=3)` and the report ended
    # `ABSENT: vulture -- install before treating this page as a second opinion`, about a tool
    # that was installed, had run, and had just printed three findings. That is the failure this
    # module was written to prevent, committed by the fix for it: the returncode check was added
    # so a tool that never ran could not read as clean, and it turned a tool that ran and found
    # something into a tool reported as missing. A guard on an exit code has to know what the
    # exit codes MEAN, and the only way to know is to run the thing.
    #
    # The nonzero-but-nothing-parsed case is kept, because it is the real one: a nonzero exit
    # that produced zero USABLE lines is every line failing to parse, not a clean run.
    if r.returncode not in (0, 1, 3) or (r.returncode in (1, 3) and not out):
        return ("TOOL ERROR (vulture rc=%d): %s"
                % (r.returncode, (r.stderr or r.stdout or "?").strip()[:200])), []
    return "RAN", out


def _detect_secrets(paths):
    exe = _exe("detect-secrets")
    if not exe:
        return "NOT INSTALLED", []
    r = subprocess.run([exe, "scan", *list(paths)],
                       capture_output=True, creationflags=_NO_WIN, text=True, timeout=600)
    # `scan` prints its JSON report on success and nothing at all on a CLI-usage error (a bad
    # flag, a bad subcommand), with the reason on stderr and rc=2 -- the same shape ruff's own
    # error path has, and `json.loads(r.stdout or "{}")` would parse the placeholder as "zero
    # results" instead of reporting that the scan never happened.
    if r.returncode != 0:
        return ("TOOL ERROR (detect-secrets rc=%d): %s"
                % (r.returncode, (r.stderr or r.stdout or "?").strip()[:200])), []
    try:
        doc = json.loads(r.stdout or "{}")
    except Exception:
        silence.note("secondopinion.py:_detect_secrets")
        return "UNPARSEABLE OUTPUT", []
    out = []
    for path, hits in (doc.get("results") or {}).items():
        for h in hits:
            out.append({"tool": "detect-secrets", "code": "detect-secrets",
                        "file": os.path.basename(path), "line": h.get("line_number") or 0,
                        "message": h.get("type") or "secret"})
    return "RAN", out


def run(paths=None):
    """Ask all three. -> {tool: {'status': str, 'findings': [...]}}.

    THE STATUS IS NOT DECORATION. A tool that did not run has status 'NOT INSTALLED' and an
    empty finding list, and those two facts must always be read together. Any caller that looks
    only at `findings` will read an absent tool as a clean one -- which is this project's
    single most repeated bug, and the reason the status is a required field rather than a note.
    """
    paths = paths or [SRC]
    got = {}
    for name, fn in (("ruff", _ruff), ("vulture", _vulture),
                     ("detect-secrets", _detect_secrets)):
        try:
            status, findings = fn(paths)
        except Exception as e:
            status, findings = "ERRORED: %s" % type(e).__name__, []
        got[name] = {"status": status, "findings": findings}
    return got


def ran_clean(got):
    """-> True only if every tool RAN and found nothing. Absent is not clean."""
    return all(v["status"] == "RAN" and not v["findings"] for v in got.values())


def missing(got):
    """-> the tools that could not answer. Reported, never silently skipped."""
    return sorted(k for k, v in got.items() if v["status"] != "RAN")


def mine_says(paths=None):
    """The house detectors' verdict on the same three questions, for comparison. -> dict."""
    import liveness
    out = {}
    try:
        lv = liveness.scan()
        out["liveness"] = sum(len(v) for v in lv.values())
    except Exception:
        silence.note("secondopinion.py:mine-liveness")
        out["liveness"] = None
    try:
        out["silence"] = len(silence.audit() or [])
    except Exception:
        silence.note("secondopinion.py:mine-silence")
        out["silence"] = None
    try:
        import publish
        # THE SAME GROUND, or the comparison is worthless. This read `scan_for_secrets(HERE)`
        # -- the whole repository -- while detect-secrets was pointed at `src/` alone, so the
        # two numbers printed side by side under the word "vs" were measuring different things,
        # and the house scanner's 9 against the outsider's 0 looked like a disagreement when it
        # was an artefact of scope. Comparing unlike measurements is this project's most
        # expensive recurring reporting bug.
        root = (paths or [SRC])[0]
        out["secrets"] = len(publish.scan_for_secrets(root) or [])
    except Exception:
        silence.note("secondopinion.py:mine-secrets")
        out["secrets"] = None
    return out


def file_orders(got, found_by="secondopinion"):
    """File what the outside tools saw, grouped by rule so the queue stays readable. -> ids.

    ONE ORDER PER RULE, not per finding. Hundreds of separate blind-except orders would bury
    every other order in the queue, and a queue nobody can read is a queue nobody works -- the drill probes
    already taught this project that lesson once. The order names the rule, the count, and the
    first few sites; the full list is a `ruff check` away and the order says so.
    """
    import workorders
    ids = []
    by_code = {}
    for v in got.values():
        for f in v["findings"]:
            by_code.setdefault(f["code"], []).append(f)

    for code, hits in sorted(by_code.items()):
        if code in NOT_FILED:
            continue          # counted and printed, not queued. See NOT_FILED for the reason.
        sites = ", ".join("%s:%d" % (h["file"], h["line"]) for h in hits[:4])
        if len(hits) > 4:
            sites += " (+%d more)" % (len(hits) - 4)
        counterpart = COUNTERPART.get(code)
        what = ("%s: %d site(s) — %s. %s"
                % (code, len(hits), hits[0]["message"],
                   ("second opinion on %s" % counterpart) if counterpart
                   else "no house detector covers this shape"))
        sev = "MINOR" if counterpart else "MAJOR"
        oid = workorders.file_order(
            code="SECONDOPINION_" + code, what=what, handler="LOCAL",
            severity=sev, where=sites, found_by=found_by,
            evidence={"tool": hits[0]["tool"], "count": len(hits),
                      "counterpart": counterpart})
        if oid:
            ids.append(oid)

    for name in missing(got):
        oid = workorders.file_order(
            code="SECONDOPINION_ABSENT_" + name.replace("-", "_").upper(),
            what=("the independent %s check could not run (%s) — its silence is NOT a pass"
                  % (name, got[name]["status"])),
            handler="RUN", severity="MINOR", where="src/secondopinion.py",
            found_by=found_by,
            evidence={"remedy": "python -m pip install " + name})
        if oid:
            ids.append(oid)
    return ids


def report(paths=None):
    got = run(paths)
    mine = mine_says(paths)
    print("SECOND OPINION — the same questions, asked by code this project did not write")
    print("=" * 78)
    for name, v in got.items():
        cp = {"ruff": "silence.py / liveness.py", "vulture": "liveness.py",
              "detect-secrets": "publish.scan_for_secrets"}[name]
        if v["status"] != "RAN":
            print("  %-15s %-12s  <-- NOT AN ALL-CLEAR. Nothing checked %s from outside."
                  % (name, v["status"], cp))
            continue
        codes = {}
        for f in v["findings"]:
            codes[f["code"]] = codes.get(f["code"], 0) + 1
        ranked = sorted(codes.items(), key=lambda kv: -kv[1])
        top = ", ".join("%s x%d" % (k, n) for k, n in ranked[:6])
        if len(ranked) > 6:
            top += " (+%d more code(s))" % (len(ranked) - 6)
        waived = sum(n for k, n in codes.items() if k in NOT_FILED)
        print("  %-15s RAN   %4d finding(s)   vs %s" % (name, len(v["findings"]), cp))
        if top:
            print("  %-15s       %s" % ("", top))
        if waived:
            print("  %-15s       of which %d are house-style divergences with a written reason "
                  "(NOT_FILED) — counted, not queued" % ("", waived))
    print("-" * 78)
    print("  house detectors: liveness=%s  silence=%s  secrets=%s"
          % (mine["liveness"], mine["silence"], mine["secrets"]))
    ds = got["detect-secrets"]
    if ds["status"] == "RAN" and not ds["findings"] and mine["secrets"] == 0:
        print("  AGREEMENT: two independently-written scanners both find no secret. That is"
              " worth more than either of them saying it alone.")
    if ran_clean(got):
        print("  ALL THREE RAN AND ALL THREE FOUND NOTHING. This is the only sentence on this"
              " page that is an all-clear, and it requires every tool to have actually run.")
    absent = missing(got)
    if absent:
        print("  ABSENT: %s — install before treating this page as a second opinion."
              % ", ".join(absent))
    return got


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--file-orders", action="store_true",
                    help="file what the outside tools found as work orders")
    a = ap.parse_args()
    got = report()
    if a.file_orders:
        ids = file_orders(got)
        print("\nfiled %d work order(s)" % len(ids))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
