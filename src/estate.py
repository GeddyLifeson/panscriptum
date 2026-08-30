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

So: every file, and every one whose type can be PARSED is opened and parsed. No sampling. On
this machine that is about a minute across fourteen workers, which is a cheap price for the
difference between "44,926 records" and "44,926 records, of which some number are unreadable
and nobody knows which".

THAT SENTENCE USED TO READ "every file, opened", AND THE CODE DID NOT DO IT (order 19fc2fdda102).
`inspect()` opened `.json` and `TEXT_EXT` and sized everything else, so five `.jsonl` ledgers and
the whole hand-made backup family (`.presilence` x16, `.precatfix`, `.postsweep`, `.prewiden`,
`.prev`, `.new` and nine more spellings) were never read at all. The `.jsonl` files were the
consequential ones: `state/model_metrics.jsonl` is appended by five processes and its only
failure mode is a torn line, which is neither zero bytes nor a checked extension -- and the
first pass after this was fixed found exactly that, on line 1831. Binaries and free-form logs
are still only sized, deliberately; `inspect()`'s docstring now lists which is which, so the
promise and the pass say the same thing.

WHAT ELSE IS AUDITED HERE
-------------------------
    CHARTER    the specification is prose and nothing enforces it. Three of its claims are
               checkable against the code directly, and all three have been wrong before.
    WRITTEN    what prose actually exists, against how much was supposed to.
    TERMINAL   the reference viewer's data files load and are not husks.
    EXTERNAL   Ollama, Cascade, and the disk — the dependencies that live outside the tree and
               can fail without anything in it changing.

EVERY ROW CARRIES ITS OWN SEVERITY, AND THAT IS NEW (run #36, batch 08)
----------------------------------------------------------------------
Until now every row here was an undifferentiated `{finding, detail}` pair, which meant the four
tiers below could be READ but could not be GRADED: `allsweep.main()` summed only
`artifacts["bad"]`, so `MASTER CHARTER MISSING`, `OLLAMA UNREACHABLE` and
`TERMINAL HAS NO HTML ENTRY POINT` could all stand at once and the sweep still exited 0. Proven
by execution before it was changed: charter() driven against an empty tree returned
`MASTER CHARTER MISSING` and allsweep's own formula still graded `bad = 0`.

That is the project's signature defect wearing an auditor's uniform — a check that cannot fail
looks exactly like a check that passed. `allsweep.py`'s own comment names the same gap for the
RECONCILE tier and says the fix is "giving note() a severity so this tier CAN gate". This is
that, for ESTATE: `note(..., bad=True)` marks a row as a FAULT and `allsweep.estate_faults()`
counts exactly those.

`bad=False` is not a synonym for "unimportant". Three kinds of row are deliberately NOT faults:
a plain measurement (`chapters written`, `disk free`), a KNOWN AND ACCEPTED standing condition
(`catalogued sources with NO charter spine code` — Hard Rule 2 makes extending the Acquisitions
Index owner work, and 33 sources sit outside it today by decision, not by breakage), and an
erratum already recorded as open against the document (`charter erratum (open)`). Grading those
red would turn the battery into an alarm that always sounds, which this file's own `inspect()`
docstring says is worse than no auditor at all.
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
# Everything `inspect()` actually OPENS. `.jsonl` is parsed a line at a time rather than whole,
# so it is listed here beside `.json` rather than folded into it.
CHECKED_EXT = (".json", ".jsonl") + TEXT_EXT
# A `.corrupt` copy is the tree's own name for "this is the damaged one, kept as evidence"
# (`state/failures.json.corrupt`, `state/failure_samples.json.corrupt`). Reporting it as damaged
# would be a permanently red row that no repair can ever clear, which is precisely the auditor
# that cries wolf `inspect()`'s docstring refuses to become. Sized, never opened.
KEPT_DAMAGED_EXT = (".corrupt",)


# --------------------------------------------------------------------------- every file

def _walk(root):
    for base, dirs, files in os.walk(root):
        dirs[:] = [d for d in dirs if d not in SKIP_DIRS]
        for f in files:
            yield os.path.join(base, f)


def _effective_ext(path):
    """The extension whose content rules apply here -- a backup marker peeled off first.

    THE HAND-MADE BACKUP FAMILY WAS ONLY EVER SIZED (order 19fc2fdda102). This tree keeps
    copies named `<original>.<marker>`: `.presilence` (16 of them), `.precatfix`, `.postsweep`,
    `.prewiden`, `.precapfix`, `.prepool`, `.prewindow`, `.prebandfix`, `.preprobe`, `.prefix`,
    `.pre-run36`, `.reconstructed-20260826`, `.new`, `.prev`. None of those is a checked
    extension, so every one of them got `getsize` and nothing else -- while the file underneath
    the marker is ordinary Python or JSON.

    Peeling the marker and re-deriving the extension is deliberately preferred to listing the
    markers: the list above was already fourteen spellings long on the day this was written and
    a fifteenth is one `cp` away, so an enumerated list would go stale silently, which is the
    shape this module exists to catch rather than commit. A marker whose inner extension is not
    one we check (`read_auto.log.prev`) falls back to the marker itself and is still only sized,
    exactly as it is today.
    """
    ext = os.path.splitext(path)[1].lower()
    if ext in CHECKED_EXT or ext in KEPT_DAMAGED_EXT:
        return ext
    inner = os.path.splitext(os.path.splitext(path)[0])[1].lower()
    return inner if inner in CHECKED_EXT else ext


def inspect(path):
    """One file, opened and actually read where its type can be parsed. Size is a hint.

    WHAT IS OPENED, exactly, because the header used to promise more than this performed:
    `.json` (loaded whole), `.jsonl` (every non-empty line loaded on its own), and `TEXT_EXT`
    -- with `.py` additionally handed to `ast.parse`. A hand-made backup is judged by the
    extension UNDER its marker; see `_effective_ext`.

    WHAT IS ONLY SIZED, and why that is right: binaries (`.db`, `.db-wal`, `.zip`), logs
    (`.log`, `.out`, `.err` -- free-form and not necessarily UTF-8; `state/runner.out` is
    cp1252 today), and the `.corrupt` copies this tree keeps on purpose. Saying so here rather
    than leaving the module header's "every file, opened" to stand is the point: a stale
    comment in this codebase actively misleads, and a promise the code does not keep is the
    same defect as a check that cannot fail.
    """
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
    ext = _effective_ext(path)
    if ext == ".jsonl":
        # A TORN LINE IS NEITHER ZERO BYTES NOR A CHECKED EXTENSION, so until now this battery
        # could not see the one corruption mode these files actually have.
        # `state/model_metrics.jsonl` is the live cloud-lane ledger appended by five processes,
        # and `cascade_bridge._metric`'s own comment explains it uses a single unbuffered
        # syscall precisely because "a buffered append can be split mid-line, producing rows
        # that parse as neither writer's". Found on the first pass after adding this: line 1831
        # of that file is exactly such a row. Reported the same shape as the `.py` branch below
        # -- the FIRST bad line number, because that is what a person needs to go and look at.
        try:
            with open(path, encoding="utf-8") as f:
                for lineno, line in enumerate(f, 1):
                    if not line.strip():
                        continue
                    try:
                        json.loads(line)
                    except json.JSONDecodeError as e:
                        silence.note("estate.py:jsonl-malformed")
                        rec["error"] = ("malformed JSON on line %d: %s"
                                        % (lineno, str(e)[:50]))
                        break
        except UnicodeDecodeError as e:
            silence.note("estate.py:jsonl-not-utf8")
            rec["error"] = "not utf-8: " + str(e)[:60]
        except Exception as e:
            silence.note("estate.py:jsonl-unreadable")
            rec["error"] = type(e).__name__ + ": " + str(e)[:60]
    elif ext == ".json":
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
    living in a conversation. Each of the four is TESTED against the charter's own two tables
    rather than asserted, so amending the document is what clears the row -- see the block at
    the foot of this function.
    """
    out = []

    def note(finding, detail="", bad=False):
        out.append({"finding": finding, "detail": str(detail), "bad": bool(bad)})

    path = os.path.join(HERE, "reference", "keystone_volumes", "00_MASTER_CHARTER.md")
    if not os.path.exists(path):
        note("MASTER CHARTER MISSING", path, bad=True)
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
            # A band the code SCORES WITH that the specification never names is the code and the
            # charter disagreeing about the instrument. That is a fault, not an observation.
            note("bands the code uses that the charter never names", ", ".join(gap), bad=True)
    except Exception as e:
        # A comparison that could not be made is not a comparison that passed.
        note("could not compare bands", type(e).__name__, bad=True)

    spine = os.path.join(HERE, "data", "CHARTER_SPINE_CODES.json")
    if os.path.exists(spine):
        codes = None
        try:
            with open(spine, encoding="utf-8") as f:
                codes = json.load(f)
            note("spine codes parsed from the Acquisitions Index", f"{len(codes)} sources")
        except Exception as e:
            note("spine codes unreadable", str(e)[:80], bad=True)
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
                    # NOT GRADED A FAULT, deliberately. Hard Rule 2 makes extending the
                    # Acquisitions Index owner work, and the sources outside it are outside it
                    # by that decision. Reported every run so the number stays visible; red
                    # would make the battery sound an alarm at a condition nobody may clear
                    # without the owner.
                    note("catalogued sources with NO charter spine code",
                         f"{len(un)} — e.g. " + ", ".join(un[:4]))
            except Exception as e:
                note("records unreadable — could not compare them against the spine codes",
                     str(e)[:80], bad=True)
    else:
        note("CHARTER_SPINE_CODES.json MISSING", spine, bad=True)

    for name in ("0-1_CUSTODIANS_VADE_MECUM.md", "X2_MENSURA_FUNDAMENTA.md",
                 "I9_THE_CONCORDANCE.md", "VIII_MASTER_CHRONICLE.md"):
        if not os.path.exists(os.path.join(HERE, "reference", "keystone_volumes", name)):
            note("KEYSTONE VOLUME MISSING", name, bad=True)

    # The errata, restated every run so they cannot quietly become accepted. NOT graded faults:
    # they are defects in the DOCUMENT, already raised and recorded as open, and a standing
    # erratum that reddens every battery is how a real red gets scrolled past.
    #
    # EACH ROW IS NOW THE TEST ITS OWN TEXT DESCRIBES (order 7c9d763fa17c). This was
    # `for rung in (...): if rung.lower() in text.lower()`, i.e. the finding claimed the rung has
    # no Magnitude band while the only thing evaluated was whether the WORD occurs anywhere in
    # the charter. Amending Part Three to give Supercluster a band would not have silenced the
    # row -- the only way to clear it was to delete the rung's name from the document, which is
    # the opposite of fixing it. A string-presence test standing in for behaviour, in the one
    # function whose docstring says the charter's claims are "checkable against the code
    # directly". The band check twelve lines above (A.LADDER against the bands the document
    # actually names) was already a real test; this is now the same kind.
    #
    # The question a Magnitude band answers is Part Three's own: "what rung of reality this thing
    # can meaningfully threaten". So the test reads the "Can threaten..." column of the Magnitude
    # table and asks whether any band reaches the rung. Nothing in it is fuzzy: the three rung
    # names are distinctive tokens ("supercluster" is not matched by M6's "cluster", which is why
    # the patterns are anchored on word boundaries and allow only a plural).
    ladder_txt = text.split("THE LADDER OF BEING", 1)[-1].split("### The Shelfmark", 1)[0]
    band_rows = dict(re.findall(r"^\|\s*\*\*(M\d+)\*\*\s*\|[^|]*\|([^|]*)\|", text, re.M))
    rung_rows = re.findall(r"^\|\s*(\d{1,2})\s*\|\s*([^|]+?)\s*\|", ladder_txt, re.M)
    if set(band_rows) != {"M%d" % i for i in range(11)} or len(rung_rows) != 17:
        # A comparison that could not be made is not a comparison that passed -- the same ruling
        # as "could not compare bands" above. If the charter's tables are reshaped, these four
        # errata stop being checked, and that must say so rather than read as four rows cleared.
        note("could not read the charter's own tables, so the errata below were NOT checked",
             f"{len(band_rows)} Magnitude bands and {len(rung_rows)} ladder rungs parsed",
             bad=True)
        return out
    threatens = " ".join(band_rows.values()).lower()
    for num, rung, pat in ((10, "Supercluster", r"\bsuperclusters?\b"),
                           (11, "Cosmic Filament / Void", r"\bfilaments?\b|\bvoids?\b"),
                           (16, "Hyperverse", r"\bhyperverses?\b")):
        if not re.search(pat, threatens):
            note("charter erratum (open)",
                 f"rung {num} ({rung}) has no Magnitude band: no band's 'Can threaten...' "
                 f"column in Part Three reaches it")
    # THE FOURTH ERRATUM, which the docstring named and nothing checked. M0-M2 threaten a
    # village, a city or nation, and a continent -- none of which is a rung of the Ladder, whose
    # rung 1 is already a whole Planet. So the three lowest bands describe scales the shelfmark
    # has no address for. Checked by asking whether the bottom three bands name ANY rung: a
    # single significant word from any of the seventeen rung names, plural allowed, clears it.
    low = "; ".join((band_rows[b] or "").strip() for b in ("M0", "M1", "M2")).lower()
    rung_words = {w.lower() for _, r in rung_rows for w in re.findall(r"[A-Za-z]{4,}", r)}
    if not any(re.search(r"\b" + w + r"s?\b", low) for w in sorted(rung_words)):
        note("charter erratum (open)",
             f"M0-M2 ({low}) name no rung of the Ladder at all, so the three lowest bands sit "
             f"below rung 1 ({rung_rows[0][1]}) and the shelfmark has no address for what they "
             f"threaten")
    return out


# --------------------------------------------------------------------------- what is written

def written():
    """What prose actually exists, against how much was supposed to.

    Phases 5 through 8 are unbuilt, so this is expected to be nearly empty. Saying so with a
    number is the point: `output/` holding 41 files reads very differently once you know the
    roll is 212 sources.
    """
    out = []

    def note(finding, detail="", bad=False):
        out.append({"finding": finding, "detail": str(detail), "bad": bool(bad)})

    root = os.path.join(HERE, "output")
    if not os.path.isdir(root):
        # Not a fault: Phases 5-8 are unbuilt and the prose gate is shut, so an absent
        # `output/` is the same news as `chapters written 0`, which is also not red.
        note("no output directory", "nothing has been written")
        return out
    raw = [p for p in glob.glob(os.path.join(root, "raw", "**", "*"), recursive=True)
           if os.path.isfile(p)]
    note("chapters written", f"{len(raw)} files under output/raw")
    try:
        import weave_index as WI
        note("sources on the roll", f"{len({r['source'] for r in WI.load_records()})}")
    except Exception as e:
        # THE LINE USED TO VANISH HERE. This handler filed the exception in `silence` and
        # appended NOTHING to the report, so a `weave_index` that would not load took the whole
        # "sources on the roll" row off the page -- and a missing row reads exactly like a row
        # that was never supposed to be there. Every sibling handler in this file (charter()'s
        # "spine codes unreadable", terminal()'s "X UNREADABLE", the catalog.json handler ten
        # lines below) leaves a visible line; this one did not. The denominator disappearing is
        # the worse half: `chapters written 0` next to nothing at all is unreadable, and the
        # docstring above says the number is the entire point of the tier. Run #36, batch 08.
        silence.note("estate.py:written-sources")
        note("SOURCES ON THE ROLL UNREADABLE — the denominator is missing from this report",
             type(e).__name__ + ": " + str(e)[:70], bad=True)
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
                # THE ROW IS ALWAYS EMITTED (order f856ff7445b0). This was gated on `if d:`, so
                # an index file that exists and parses but is EMPTY produced no row at all --
                # indistinguishable, on the page, from the `continue` twelve lines up for a file
                # that is not there. `output/index/catalog.json` holds exactly `{}` today, so
                # the report showed no 'generation catalog' row whatever, which is the same
                # vanishing-row fault the `sources on the roll` handler above was repaired for
                # in this very function: "a missing row reads exactly like a row that was never
                # supposed to be there", and the missing denominator is the worse half, since
                # `chapters written 0` with nothing beside it is unreadable. Zero is a
                # legitimate and expected finding here -- Phases 5-8 are unbuilt -- so it stays
                # `bad=False`, exactly like `chapters written 0`. What must not happen is the
                # row disappearing.
                note(label, f"{len(d)} records")
            except Exception as e:
                note(label + " UNREADABLE", str(e)[:70], bad=True)
        else:
            note(label, f"{os.path.getsize(p):,} bytes")
    return out


# --------------------------------------------------------------------------- the terminal

def terminal():
    """The Registry Terminal: does its data load, and is any of it a husk?"""
    out = []

    def note(finding, detail="", bad=False):
        out.append({"finding": finding, "detail": str(detail), "bad": bool(bad)})

    root = os.path.join(HERE, "registry_terminal")
    if not os.path.isdir(root):
        # The charter's Part Nine calls this the reference implementation and it is tracked in
        # the tree. Its absence is a lost asset, not a phase that has not started yet.
        note("no registry_terminal", "the reference viewer is absent", bad=True)
        return out
    files = sorted(os.listdir(root))
    js = [f for f in files if f.endswith(".js")]
    html = [f for f in files if f.endswith(".html")]
    note("terminal", f"{len(html)} page(s), {len(js)} data file(s)")
    if not html:
        note("TERMINAL HAS NO HTML ENTRY POINT", "", bad=True)
    for f in js:
        p = os.path.join(root, f)
        try:
            with open(p, encoding="utf-8") as fh:
                body = fh.read()
        except Exception as e:
            note(f + " UNREADABLE", str(e)[:70], bad=True)
            continue
        if len(body) < 64:
            # A husk is the exact fault this tier was written to find: a data file that loads
            # and says nothing, which every consumer reads as "no data" rather than "no file".
            note(f + " is effectively empty", f"{len(body)} bytes", bad=True)
    return out


# --------------------------------------------------------------------------- outside the tree

def external():
    """The dependencies that live outside this project and can fail without it changing."""
    out = []

    def note(finding, detail="", bad=False):
        out.append({"finding": finding, "detail": str(detail), "bad": bool(bad)})

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
                note("config.yaml NAMES A MODEL OLLAMA DOES NOT HAVE", want, bad=True)
        except Exception as e:
            note("config.yaml unreadable", str(e)[:70], bad=True)
    except Exception as e:
        # GRADED RED, and it will redden the sweep whenever the daemon is down. That is the
        # intended reading: this project's model calls all land here, and an unreachable Ollama
        # is a subsystem in a bad state, which is the exact sentence the sweep prints.
        note("OLLAMA UNREACHABLE", type(e).__name__, bad=True)

    try:
        import cascade_bridge as CB
        if CB.available():
            note("Cascade", f"{len(CB.cloud_buckets())} usable remote bucket(s)")
            dead = CB.dead_buckets()
            if dead:
                # Benching is the router WORKING -- a bucket over its quota is meant to be
                # benched -- so this is reported, not graded.
                note("buckets currently benched", ", ".join(sorted(dead)))
        else:
            note("CASCADE NOT AVAILABLE", "every model call would fall to the local GPU",
                 bad=True)
    except Exception as e:
        note("Cascade check failed", type(e).__name__, bad=True)

    try:
        import shutil
        free = shutil.disk_usage(HERE).free / 1e9
        note("disk free", f"{free:.0f} GB")
        if free < 10:
            note("DISK NEARLY FULL", "the roll writes hundreds of MB an hour", bad=True)
    except Exception as e:
        note("disk check failed", str(e)[:60], bad=True)
    return out
