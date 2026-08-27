#!/usr/bin/env python3
"""
ESTATE — everything this project owns that is not code, checked.

WHY SEPARATELY FROM THE CODE
----------------------------
The code is the smallest part of the Panscriptum. The tree holds about 45,000 files and 44,926
of them are in `data/` — mined pages, catalogue records, indices, ledgers — and until this file
existed, not one of them had ever been opened to see whether it would parse.

That matters more here than in most projects, because of how every stage reads them: open,
`json.load`, `except: continue`. A record that will not load is skipped in silence by every
consumer, so a corrupt cache is indistinguishable from a cache that is genuinely empty — and
"genuinely empty" is a legitimate finding in this library, which is exactly what makes the
confusion so expensive. It is the project's signature defect, at rest, across its largest
surface.

So: every file, opened. No sampling. On this machine that is about a minute across fourteen
workers, which is a cheap price for the difference between "44,926 records" and "44,926 records,
of which some number are unreadable and nobody knows which".

WHAT ELSE IS AUDITED HERE
-------------------------
    CHARTER    the specification is prose and nothing enforces it. Three of its claims are
               checkable against the code directly, and all three have been wrong before.
    WRITTEN    what prose actually exists, against how much was supposed to.
    TERMINAL   the reference viewer's data files load and are not husks.
    EXTERNAL   Ollama, Cascade, and the disk — the dependencies that live outside the tree and
               can fail without anything in it changing.
"""
import ast
import collections
import glob
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import silence                                                          # noqa: E402

_BAD_CHARS = (chr(8), chr(11), chr(12), chr(7))
if any(c in open(os.path.abspath(__file__), encoding="utf-8").read() for c in _BAD_CHARS):
    raise SystemExit(__file__ + ": a regex escape was eaten in transit.")

SKIP_DIRS = {"__pycache__", ".git", ".venv", "node_modules"}
TEXT_EXT = (".py", ".md", ".txt", ".yaml", ".yml", ".js", ".html", ".css")


# --------------------------------------------------------------------------- every file

def _walk(root):
    for base, dirs, files in os.walk(root):
        dirs[:] = [d for d in dirs if d not in SKIP_DIRS]
        for f in files:
            yield os.path.join(base, f)


def inspect(path):
    """One file, opened and actually read. Size is a hint; parsing is the answer."""
    rec = {"path": os.path.relpath(path, HERE), "bytes": 0}
    try:
        rec["bytes"] = os.path.getsize(path)
    except OSError:
        silence.note("estate.py:stat-failed")
        rec["error"] = "cannot stat"
        return rec
    if rec["bytes"] == 0:
        # A LOG IS ALLOWED TO BE EMPTY. `state/overnight_stderr.log` at zero bytes means the
        # supervisor wrote nothing to stderr, which is the best possible news, and reporting it
        # as corruption teaches the reader to skim past the corruption list. An auditor that
        # cries wolf is worse than no auditor: it produces exactly the "one known failure we
        # ignore" habit that let four broken modules sit unnoticed.
        if os.path.splitext(path)[1].lower() in (".log", ".tmp", ".out", ".err"):
            return rec
        rec["error"] = "zero bytes"
        return rec
    ext = os.path.splitext(path)[1].lower()
    if ext == ".json":
        try:
            with open(path, encoding="utf-8") as f:
                json.load(f)
        except UnicodeDecodeError as e:
            silence.note("estate.py:json-not-utf8")
            rec["error"] = "not utf-8: " + str(e)[:60]
        except json.JSONDecodeError as e:
            silence.note("estate.py:json-malformed")
            rec["error"] = "malformed JSON: " + str(e)[:60]
        except Exception as e:
            silence.note("estate.py:json-unreadable")
            rec["error"] = type(e).__name__ + ": " + str(e)[:60]
    elif ext in TEXT_EXT:
        try:
            with open(path, encoding="utf-8") as f:
                text = f.read()
        except UnicodeDecodeError as e:
            silence.note("estate.py:text-not-utf8")
            rec["error"] = "not utf-8: " + str(e)[:60]
            return rec
        except Exception as e:
            silence.note("estate.py:text-unreadable")
            rec["error"] = type(e).__name__ + ": " + str(e)[:60]
            return rec
        hits = sum(text.count(c) for c in _BAD_CHARS)
        if hits:
            # The escape-eaten-in-transit fault: six occurrences so far, silent every time.
            # Checked across EVERY text file here, not only the regex-bearing modules.
            rec["error"] = str(hits) + " control character(s) where an escape should be"
        elif ext == ".py":
            try:
                ast.parse(text)
            except SyntaxError as e:
                silence.note("estate.py:py-will-not-parse")
                rec["error"] = "will not parse: line " + str(e.lineno)
    return rec


def artifacts(workers=8, roots=None):
    """Every file in the project, opened and checked. No sampling anywhere."""
    from concurrent.futures import ThreadPoolExecutor
    roots = roots or ["data", "src", "state", "output", "prompts", "reference",
                      "registry_terminal", "handoff"]
    paths = []
    for d in roots:
        p = os.path.join(HERE, d)
        if os.path.isdir(p):
            paths += list(_walk(p))
    for f in ("CLAUDE.md", "README.md", "STATUS.md", "config.yaml", "requirements.txt"):
        p = os.path.join(HERE, f)
        if os.path.exists(p):
            paths.append(p)

    with ThreadPoolExecutor(max_workers=workers) as ex:
        recs = list(ex.map(inspect, paths))

    by_dir = collections.defaultdict(lambda: {"files": 0, "bytes": 0, "bad": 0})
    bad = []
    for r in recs:
        top = r["path"].replace(chr(92), "/").split("/")[0]
        d = by_dir[top]
        d["files"] += 1
        d["bytes"] += r["bytes"]
        if r.get("error"):
            d["bad"] += 1
            bad.append(r)
    return {"total": len(recs), "by_dir": dict(by_dir), "bad": bad}


# --------------------------------------------------------------------------- the charter

def charter():
    """Does the code agree with the document it claims to implement?

    The charter is the specification and it is prose, so nothing enforces it. Several of its
    claims are checkable against the code directly, and several have already been wrong.

    Known errata, raised and unresolved: rungs 10 (Supercluster), 11 (Filament/Void) and 16
    (Hyperverse) carry NO Magnitude band, and M0-M2 sit below rung 1. Those are faults in the
    document rather than the code, and they are reported here so they stay visible instead of
    living in a conversation.
    """
    out = []

    def note(finding, detail=""):
        out.append({"finding": finding, "detail": str(detail)})

    path = os.path.join(HERE, "reference", "keystone_volumes", "00_MASTER_CHARTER.md")
    if not os.path.exists(path):
        note("MASTER CHARTER MISSING", path)
        return out
    with open(path, encoding="utf-8") as f:
        text = f.read()
    note("charter", f"{len(text):,} characters")

    named = sorted({int(m) for m in re.findall(r"\bM(10|[0-9])\b", text)})
    note("Magnitude bands named in the charter", ", ".join("M" + str(b) for b in named))
    try:
        import assay as A
        gap = [b for b in A.LADDER if int(b[1:]) not in named]
        if gap:
            note("bands the code uses that the charter never names", ", ".join(gap))
    except Exception as e:
        note("could not compare bands", type(e).__name__)

    spine = os.path.join(HERE, "data", "CHARTER_SPINE_CODES.json")
    if os.path.exists(spine):
        codes = None
        try:
            with open(spine, encoding="utf-8") as f:
                codes = json.load(f)
            note("spine codes parsed from the Acquisitions Index", f"{len(codes)} sources")
        except Exception as e:
            note("spine codes unreadable", str(e)[:80])
        # A SECOND HANDLER, because these are two subsystems. Reading the records is
        # `weave_index`'s work, not the spine file's, and one handler over both reported a
        # malformed record or a bug in `weave_index` as "spine codes unreadable" -- which sends
        # whoever reads the estate report to open the wrong file.
        if codes is not None:
            try:
                import weave_index as WI
                recs = {r["source"] for r in WI.load_records()}
                un = sorted(recs - set(codes))
                if un:
                    note("catalogued sources with NO charter spine code",
                         f"{len(un)} — e.g. " + ", ".join(un[:4]))
            except Exception as e:
                note("records unreadable — could not compare them against the spine codes",
                     str(e)[:80])
    else:
        note("CHARTER_SPINE_CODES.json MISSING", spine)

    for name in ("0-1_CUSTODIANS_VADE_MECUM.md", "X2_MENSURA_FUNDAMENTA.md",
                 "I9_THE_CONCORDANCE.md", "VIII_MASTER_CHRONICLE.md"):
        if not os.path.exists(os.path.join(HERE, "reference", "keystone_volumes", name)):
            note("KEYSTONE VOLUME MISSING", name)

    # The errata, restated every run so they cannot quietly become accepted.
    for rung in ("Supercluster", "Filament", "Hyperverse"):
        if rung.lower() in text.lower():
            note("charter erratum (open)", rung + " is a rung with no Magnitude band")
    return out


# --------------------------------------------------------------------------- what is written

def written():
    """What prose actually exists, against how much was supposed to.

    Phases 5 through 8 are unbuilt, so this is expected to be nearly empty. Saying so with a
    number is the point: `output/` holding 41 files reads very differently once you know the
    roll is 212 sources.
    """
    out = []

    def note(finding, detail=""):
        out.append({"finding": finding, "detail": str(detail)})

    root = os.path.join(HERE, "output")
    if not os.path.isdir(root):
        note("no output directory", "nothing has been written")
        return out
    raw = [p for p in glob.glob(os.path.join(root, "raw", "**", "*"), recursive=True)
           if os.path.isfile(p)]
    note("chapters written", f"{len(raw)} files under output/raw")
    try:
        import weave_index as WI
        note("sources on the roll", f"{len({r['source'] for r in WI.load_records()})}")
    except Exception:
        silence.note("estate.py:written-sources")
    for fn, label in (("catalog.json", "generation catalog"),
                      ("failures.json", "generation failures on record"),
                      ("unassigned_sources.md", "sources with no spine code")):
        p = os.path.join(root, "index", fn)
        if not os.path.exists(p):
            continue
        if fn.endswith(".json"):
            try:
                with open(p, encoding="utf-8") as f:
                    d = json.load(f)
                if d:
                    note(label, f"{len(d)} records")
            except Exception as e:
                note(label + " UNREADABLE", str(e)[:70])
        else:
            note(label, f"{os.path.getsize(p):,} bytes")
    return out


# --------------------------------------------------------------------------- the terminal

def terminal():
    """The Registry Terminal: does its data load, and is any of it a husk?"""
    out = []

    def note(finding, detail=""):
        out.append({"finding": finding, "detail": str(detail)})

    root = os.path.join(HERE, "registry_terminal")
    if not os.path.isdir(root):
        note("no registry_terminal", "the reference viewer is absent")
        return out
    files = sorted(os.listdir(root))
    js = [f for f in files if f.endswith(".js")]
    html = [f for f in files if f.endswith(".html")]
    note("terminal", f"{len(html)} page(s), {len(js)} data file(s)")
    if not html:
        note("TERMINAL HAS NO HTML ENTRY POINT", "")
    for f in js:
        p = os.path.join(root, f)
        try:
            with open(p, encoding="utf-8") as fh:
                body = fh.read()
        except Exception as e:
            note(f + " UNREADABLE", str(e)[:70])
            continue
        if len(body) < 64:
            note(f + " is effectively empty", f"{len(body)} bytes")
    return out


# --------------------------------------------------------------------------- outside the tree

def external():
    """The dependencies that live outside this project and can fail without it changing."""
    out = []

    def note(finding, detail=""):
        out.append({"finding": finding, "detail": str(detail)})

    try:
        import urllib.request
        with urllib.request.urlopen("http://localhost:11434/api/tags", timeout=15) as r:
            tags = json.loads(r.read().decode("utf-8", "replace"))
        names = [m.get("name") for m in tags.get("models", [])]
        note("Ollama", f"up, {len(names)} model(s) installed")
        try:
            import yaml
            cfg = yaml.safe_load(open(os.path.join(HERE, "config.yaml"), encoding="utf-8"))
            want = cfg.get("model")
            if want and want not in names:
                note("config.yaml NAMES A MODEL OLLAMA DOES NOT HAVE", want)
        except Exception as e:
            note("config.yaml unreadable", str(e)[:70])
    except Exception as e:
        note("OLLAMA UNREACHABLE", type(e).__name__)

    try:
        import cascade_bridge as CB
        if CB.available():
            note("Cascade", f"{len(CB.cloud_buckets())} usable remote bucket(s)")
            dead = CB.dead_buckets()
            if dead:
                note("buckets currently benched", ", ".join(sorted(dead)))
        else:
            note("CASCADE NOT AVAILABLE", "every model call would fall to the local GPU")
    except Exception as e:
        note("Cascade check failed", type(e).__name__)

    try:
        import shutil
        free = shutil.disk_usage(HERE).free / 1e9
        note("disk free", f"{free:.0f} GB")
        if free < 10:
            note("DISK NEARLY FULL", "the roll writes hundreds of MB an hour")
    except Exception as e:
        note("disk check failed", str(e)[:60])
    return out
