"""CITECHECK — the cheap half of "does this `file.py:NNN` citation still point where it says".

WHY THIS EXISTS. Three consecutive comprehensive sweeps (44, 48's `89503c58409f` with 60 sites,
and 54's `386c0d66e31e`) filed the same class: line citations in `src/` comments that have rotted,
because every edit above a cited line moves it and NOTHING ANYWHERE CHECKS. The class was being
re-harvested by each sweep rather than repaired, which is the expensive way to learn the same
fact three times. `dc9ffadae765` records that the work queue's own stored text carries 2,898 such
citations and no detector had ever looked at one of them.

WHAT THIS CAN AND CANNOT DO, stated plainly because the difference is the whole design. A full
"does line N still say what the citing comment implies" check is NOT mechanisable — it requires
reading both ends and understanding the claim, which is what a sweep batch does and what costs a
sweep. The CHEAP half is mechanisable and it is what this module does: a citation is flagged when
its target is *structurally impossible*, i.e. when

    PAST_EOF       the cited line number is past the end of that file
    BLANK_LINE     the cited line exists but is empty or whitespace only
    BARE_BRACKET   the cited line is nothing but a closing bracket, with or without a comma

Those three cannot be a correct citation under any reading, BECAUSE THE FILE WAS OPENED AND THE
LINE WAS READ. Everything else this module calls CLEAN, and CLEAN HERE MEANS "not provably
broken", never "verified". That distinction is load bearing: a run that reads a green citecheck
as "the citations are good" has learned the opposite of what was measured. `stale_citations()`
returns only what it can prove.

A CITED MODULE THAT IS NOT IN `src/` IS NOT A FINDING, and getting this wrong is how a detector
becomes furniture. The first version of this module reported ten of them and every single one was
correct as written: `cascade_bridge.py` cites `engine.py` in the *cascade* tree, `gpu_lane.py` and
`overnight.py` cite `motoko/discord_bot.py` on this same machine, `workorders.py` cites
`deprecated/catalogue_local.py`, and `liveness.py`, `secondopinion.py` and `drill.py` cite
`foo.py`/`x.py` as ILLUSTRATIVE PLACEHOLDERS inside their own docstrings and test fixtures. None
of those can be resolved from here, so they are reported separately as UNRESOLVED -- counted,
visible, and deliberately NOT filed as work, because "I could not find this file" is a fact about
this checker's reach and not about the citation.

WHY A FLOOR IS WORTH HAVING ANYWAY. Of the sites sweep 54 filed by hand, standards.py line 604
(a blank line) and address_space.py line 381 (a bare bracket) would both have been caught by this
alone, at no cost, the moment they rotted rather than at the next sweep. Under a floor like this
the class stops GROWING between sweeps, which is the part that was making it permanent.

CITED BY SYMBOL, NOT BY LINE, on purpose. This module's own docstrings name `stale_citations`,
`_classify` and `CITATION` rather than line numbers -- the project rule the order itself points
at (`0c7592915a48`) -- because a citation checker whose own citations rot would be the joke that
writes itself.
"""

import argparse
import os
import re
import sys

_BAD_CHARS = (chr(8), chr(11), chr(12), chr(7))
if any(c in open(os.path.abspath(__file__), encoding="utf-8").read() for c in _BAD_CHARS):
    raise SystemExit(__file__ + ": a regex escape was eaten in transit.")

SRC = os.path.dirname(os.path.abspath(__file__))
HERE = os.path.dirname(SRC)

sys.path.insert(0, SRC)

# A citation is a python module name, a colon, and a line number -- optionally a range or a
# second line (`feats.py:1741,1744`, `standards.py:1584-86`). Only the FIRST number is checked
# against the file; a range whose start is sound and whose end is past EOF is a rarer and much
# weaker signal than a start that is impossible, and this module deliberately reports only what
# it can prove. The module name is restricted to identifier characters so a windows path, a URL
# with a port, or a timestamp cannot match.
CITATION = re.compile(r"\b([A-Za-z_][A-Za-z0-9_]*\.py):(\d{1,6})\b")

# A line that is nothing but a closing bracket, optionally followed by a comma or a colon. These
# are never a meaningful citation target: nobody cites the punctuation that ends a call.
_BARE_BRACKET = re.compile(r"^[)\]}]+[,:]?$")

# A citation carrying a DIRECTORY is about another tree by construction -- `motoko/discord_bot.py`,
# `cascade/engine.py`, `deprecated/catalogue_local.py` -- so it is not resolvable here and not
# this checker's business. Detected by looking at the character before the match rather than by
# widening `CITATION`, so the pattern stays the thing the order describes.
_PATH_LEAD = ("/", "\\")

# Names used as STAND-INS in docstrings and test fixtures, never as real citations. `liveness.py`
# explains its answerability rule with `foo.py:12`, `secondopinion.py` shows a Windows drive
# letter defeating a naive split with `C:\...\foo.py:123`, and `drill.py` feeds `src/x.py:1` to a
# lint-parsing net as data. Flagging those would be reading the example as the thing.
_PLACEHOLDERS = frozenset(("foo.py", "bar.py", "baz.py", "qux.py", "x.py", "y.py", "z.py",
                           "example.py", "module.py", "mymodule.py", "somefile.py"))

# USE vs MENTION (order d7efd67caa6f). A citation is a POINTER: "go read this line". The two
# shapes below are not pointers at all -- they are the token being QUOTED, as a name or as a
# corpse -- and flagging them reads the mention as the use. This detector filed the same two
# sites fifteen times before the distinction was drawn, which is the churn order e114b2d0fe48
# describes: a detector that refiles what cannot be fixed teaches its queue to be ignored.
#
# MEASURED BEFORE IT WAS WRITTEN, over all 190 citation tokens in src/: 21 are quoted-exactly,
# and every one is a mention -- `silence.note` TAGS (present or historical), or synthetic
# fixture rows drill feeds its own nets (`{"id": "B", "where": "x.py:419"}`). Not one is a
# comment sending a reader to a line. The quoted form is how this codebase spells a note tag,
# and the m81 pass that renamed the bare-number tags (`"feats.py:139"` -> `"feats.py:api-http-
# error"`) left exactly these quoted survivors behind AS THE RECORD OF THE RENAME. So a probe
# asserting `"feats.py:139"` is ABSENT from feats.py was being reported as a stale citation TO
# feats.py line 139 -- the detector reading a proof-of-removal as the thing removed.
#
# AND THIS COMMENT IS WRITTEN AROUND ITS OWN RULE, which is worth saying rather than hiding. The
# first draft of this block spelled those examples as bare `name.py:NNN` tokens in running prose
# and CITECHECK IMMEDIATELY FLAGGED ITS OWN DOCUMENTATION -- three findings, all of them here.
# That is the same use/mention fault one paragraph up, committed by the paragraph describing it.
# The repair was NOT to quote them into the exemption this file now grants (leaning on your own
# excuse is how an exemption becomes a hiding place) but to stop writing pointer-shaped tokens
# for things that are not pointers: prose says "feats.py line 139", and the colon form is left
# to mean what it says.
#
# NARROW ON PURPOSE, both of them. The quote must be immediately either side of the whole token,
# so an unquoted token after some quoted words nearby is still checked; and the disclaimer must carry this
# project's own ruling phrase from order a09a0e003c31, not a loose "the old". A citation that is
# genuinely rotted cannot hide behind either without being deliberately dressed as a mention --
# and `drill.py` carries that attack (see `_reasons_for` around the mention nets).
_QUOTES = "\"'"
MENTION_QUOTED_TAG = "QUOTED_TAG"
MENTION_SYMBOL_DISCLAIMER = "SYMBOL_DISCLAIMER"
# The pre-existing skip, which had no name until there was a second kind to tell it from. A
# `skipped` row now always carries `why`, so the report can say WHICH claim was made rather
# than folding three different claims into one number and one sentence about trees.
OTHER_TREE = "OTHER_TREE"

# The ruling phrase itself, order a09a0e003c31 ("CITED BY SYMBOL, NOT BY LINE"). A comment
# carrying it is DECLARING that the number beside it is the superseded form, kept so the next
# reader can see what moved -- `withdraw_chapters.py` records publish.py lines 1385-1398
# drifting onto `_swap()` in exactly this way. Flagging that is flagging the repair.
_SYMBOL_NOT_LINE = re.compile(r"cited\s+by\s+symbol,\s*not\s+(?:by\s+)?line", re.I)


def _mention_kind(line, start, end):
    """-> why this `file.py:NNN` is a MENTION rather than a citation, or None if it is a use.

    `start`/`end` bound the matched token inside `line`. Returning None means "check it", which
    is the default for everything this does not positively recognise -- an unrecognised shape
    must fall through to being CHECKED, never to being excused.
    """
    if start > 0 and end < len(line) and line[start - 1] in _QUOTES and line[end] == line[start - 1]:
        return MENTION_QUOTED_TAG
    # THE DISCLAIMER EXEMPTS WHAT FOLLOWS IT, NOT THE WHOLE LINE. A line-wide test would let a
    # genuinely rotted citation ride along beside a declared-superseded one -- write the phrase
    # anywhere on the line and every citation on it stops being checked, which is an exemption
    # that has become a hiding place. The phrase introduces the dead number, so only tokens
    # AFTER it are covered; anything in front of it is an ordinary citation and is checked.
    d = _SYMBOL_NOT_LINE.search(line)
    if d is not None and start >= d.start():
        return MENTION_SYMBOL_DISCLAIMER
    return None


UNRESOLVED = "UNRESOLVED"
PAST_EOF = "PAST_EOF"
BLANK_LINE = "BLANK_LINE"
BARE_BRACKET = "BARE_BRACKET"


def _lines(path, _cache={}):
    """-> the file's lines, read once per process. Returns None when the file is unreadable.

    UNREADABLE IS NOT MISSING and the two must not collapse into one verdict. A file this
    process cannot decode is a fault about the reader, not about the citation, and reporting it
    as UNRESOLVED would send someone to repair a citation that is perfectly correct.

    BUT IT IS NOT SILENT EITHER, and this module is not allowed to be the next entry in the
    class `3fc19ad4d1c6` files -- "a failure becomes a plausible result". The `None` returned
    here flows into `_classify`, which returns `None`, which `stale_citations` reads as "not
    provably broken": so a `src/` this process cannot read produces a CLEAN report, which is the
    exact shape of the fault this detector exists to end. The note makes the difference between
    "nothing is broken" and "nothing could be checked" reach `state/failures.json`, where the
    handler ladder can see it, rather than living only in a return value nobody inspects.
    """
    if path in _cache:
        return _cache[path]
    try:
        with open(path, "r", encoding="utf-8") as fh:
            _cache[path] = fh.read().splitlines()
    except (OSError, UnicodeDecodeError):
        try:
            import silence
            silence.note("citecheck.py:unreadable-source")
        except Exception:
            pass
        _cache[path] = None
    return _cache[path]


def _classify(target_name, lineno, src_dir=None):
    """-> a reason constant, or None when the citation is not provably broken.

    `lineno` is 1-based, as a citation is. A citation to line 0 is impossible by construction --
    `CITATION` can match "\\.py:0" -- so it is reported as PAST_EOF rather than silently indexing
    from the end of the file the way a bare `lines[lineno - 1]` would.

    `src_dir` DEFAULTS TO THE LIVE `src/` AND EXISTS SO THE DRILL CAN DRIVE THIS OVER A SCRATCH
    TREE. A detector whose only exercise is the directory it is protecting is a detector nobody
    can watch refuse, which is this project's standing objection to an unwatched guard -- and
    planting a deliberately-rotten citation inside live `src/` to prove the net works is exactly
    the kind of probe that has halted this library before.
    """
    target = os.path.join(src_dir or SRC, target_name)
    if not os.path.isfile(target):
        return UNRESOLVED
    lines = _lines(target)
    if lines is None:
        return None
    if lineno < 1 or lineno > len(lines):
        return PAST_EOF
    text = lines[lineno - 1].strip()
    if not text:
        return BLANK_LINE
    if _BARE_BRACKET.match(text):
        return BARE_BRACKET
    return None


def _self_citation_ok(citing_file, target_name, lineno):
    """-> True when a citation inside a file may point at itself at that line.

    A module citing its OWN line numbers is the commonest rot in this library, because an edit
    anywhere above the comment moves both the comment and its target. It is checked exactly like
    any other citation; this hook exists only to keep that decision in one named place rather
    than buried in a condition, and it currently grants no exemption at all.
    """
    return False


def _in_tree_lead(line, start):
    """Is the directory in front of this citation THIS tree's `src/`? -> bool.

    THE BLIND SPOT THIS CLOSES (order 9daa719e4819). Any citation preceded by a slash was
    treated as pointing into another tree and skipped, uncounted -- and this codebase writes
    its own citations both as `foo.py:NNN` and as `src/foo.py:NNN`, so the detector silently
    ignored one of the two spellings its own tree uses. Live-verified by sweep56-batch16:
    `secondopinion.py` cited `src/liveness.py:197` while `def scan()` sat at 348, and nothing
    reported it. Sweep56 then found roughly sixty stale citations by hand that this was not
    seeing.

    A bare `src/` lead -- at the start of the line, or after a space, quote or backtick -- is
    this tree. A lead with anything path-like in front of it (`motoko/src/`,
    `C:\\...\\src\\`) is still treated as elsewhere, so the other-tree net keeps holding.

    MODULE LEVEL, NOT NESTED (order dc9ffadae765). This used to live only inside
    `stale_citations`, so `citations_in_text` -- which scans a work order's own text rather
    than a `src/` file -- would have had to copy it or skip the other-tree check entirely.
    Neither `where` it lived in changed the fact this reads only its two arguments; hoisting it
    costs nothing and is what lets both callers share one resolver.
    """
    lead = line[:start]
    for spelling in ("src/", "src\\"):
        if lead.endswith(spelling):
            before = lead[:-len(spelling)]
            return not before or not (before[-1].isalnum() or before[-1] in "_-./\\")
    return False


def citations_in_text(text, src_dir=None, include_unresolved=False, skipped=None):
    """-> findings for every provably broken `file.py:NNN` citation inside an arbitrary string.

    THE SAME RESOLVER AS `stale_citations`, NOT A SECOND COPY OF ITS RULES (order dc9ffadae765).
    `stale_citations` is bound to reading `src/` files off disk; this is the part of it that
    does not need a file at all -- `CITATION`, `_classify`, `_PLACEHOLDERS` and `_in_tree_lead`,
    applied to whatever text a caller hands it -- so a caller with text that never lived in a
    `src/` file (a work order's own `what`/`where`/`evidence`) can still be checked against
    exactly the PAST_EOF / BLANK_LINE / BARE_BRACKET resolver `_classify` already is.

    Each finding carries `line` (1-based, within `text`), `cites`, `cited_line`, `reason` and
    `text` (the matching line, stripped) -- the same shape `stale_citations` returns, minus
    `citing`, which means nothing for a string that is not a file; the caller attaches whatever
    identifies its own text (an order id, a field name).

    UNCAPPED, per Hard Rule 0: every finding in `text` is returned.
    """
    root = src_dir or SRC
    found = []
    for i, raw in enumerate(str(text or "").splitlines()):
        for m in CITATION.finditer(raw):
            target_name, num = m.group(1), int(m.group(2))
            if target_name in _PLACEHOLDERS:
                continue
            if (m.start() > 0 and raw[m.start() - 1] in _PATH_LEAD
                    and not _in_tree_lead(raw, m.start())):
                if skipped is not None:
                    skipped.append({"line": i + 1, "cites": target_name, "cited_line": num,
                                    "text": raw.strip(), "why": OTHER_TREE})
                continue
            mention = _mention_kind(raw, m.start(), m.end())
            if mention is not None:
                # COUNTED, NOT DROPPED -- the same doctrine as the other-tree skip below it.
                if skipped is not None:
                    skipped.append({"line": i + 1, "cites": target_name, "cited_line": num,
                                    "text": raw.strip(), "why": mention})
                continue
            reason = _classify(target_name, num, src_dir=root)
            if reason is None:
                continue
            if reason == UNRESOLVED and not include_unresolved:
                continue
            found.append({"line": i + 1, "cites": target_name, "cited_line": num,
                          "reason": reason, "text": raw.strip()})
    return found


def stale_citations(paths=None, include_unresolved=False, src_dir=None, skipped=None):
    """-> a list of findings, each a dict, for every provably broken `file.py:NNN` under src/.

    Each finding carries `citing` (the file the citation was written in), `line` (where in that
    file), `cites` (the target file), `cited_line`, `reason` (PAST_EOF, BLANK_LINE or
    BARE_BRACKET) and `text` (the citing line, stripped) so a reader can act without opening
    anything.

    UNRESOLVED IS NOT RETURNED BY DEFAULT and that is the point of the flag. A citation naming a
    module that is not in `src/` is usually a correct reference into another tree on this machine;
    mixing those into the same list as a citation that lands on a blank line would put ten sites
    nobody should touch in front of the reader of every one that matters. `--unresolved` shows
    them for a person who wants to audit the reach of this checker rather than the citations.

    UNCAPPED, per Hard Rule 0. The caller gets every finding; ranking is the caller's business
    and truncating is nobody's.
    """
    root = src_dir or SRC
    if paths is None:
        # THE WHOLE TREE, NOT ITS TOP LEVEL (order 9daa719e4819, sweep57-batch08). `os.listdir`
        # never descended, so `src/deprecated/` was invisible as a citing file -- the fourth
        # occurrence of a shape already repaired in `liveness.py`, `sweep_plan.py` and `drill.py`.
        paths = sorted(os.path.join(dirpath, f)
                       for dirpath, _dirs, files in os.walk(root)
                       if "__pycache__" not in dirpath
                       for f in files if f.endswith(".py"))
    found = []
    for path in paths:
        lines = _lines(path)
        if lines is None:
            continue
        base = os.path.basename(path)
        for i, raw in enumerate(lines):
            for m in CITATION.finditer(raw):
                target_name, num = m.group(1), int(m.group(2))
                if target_name in _PLACEHOLDERS:
                    continue
                if (m.start() > 0 and raw[m.start() - 1] in _PATH_LEAD
                        and not _in_tree_lead(raw, m.start())):
                    # COUNTED, NOT DROPPED. A skip is a claim that the citation is somebody
                    # else's to keep, and a claim nobody can see is a claim nobody can check;
                    # `skipped` lets the caller report how many were set aside, and which.
                    if skipped is not None:
                        skipped.append({"citing": base, "line": i + 1, "cites": target_name,
                                        "cited_line": num, "text": raw.strip(),
                                        "why": OTHER_TREE})
                    continue
                mention = _mention_kind(raw, m.start(), m.end())
                if mention is not None:
                    # THE TOKEN IS BEING NAMED, NOT FOLLOWED (order d7efd67caa6f). Same
                    # "counted, not dropped" rule as the skip above: a mention is still a claim
                    # this checker is making, and it is reported by kind in `main()`.
                    if skipped is not None:
                        skipped.append({"citing": base, "line": i + 1, "cites": target_name,
                                        "cited_line": num, "text": raw.strip(),
                                        "why": mention})
                    continue
                if target_name == base and _self_citation_ok(base, target_name, num):
                    continue
                reason = _classify(target_name, num, src_dir=root)
                if reason is None:
                    continue
                if reason == UNRESOLVED and not include_unresolved:
                    continue
                found.append({
                    "citing": base,
                    "line": i + 1,
                    "cites": target_name,
                    "cited_line": num,
                    "reason": reason,
                    "text": raw.strip(),
                })
    return found


def summary(found):
    """-> {reason: count} plus a 'total', for a detector that wants one number."""
    out = {}
    for f in found:
        out[f["reason"]] = out.get(f["reason"], 0) + 1
    out["total"] = len(found)
    return out


def report(found):
    """-> the findings as printable lines, grouped by citing file, uncapped."""
    out = []
    by_file = {}
    for f in found:
        by_file.setdefault(f["citing"], []).append(f)
    for name in sorted(by_file):
        out.append("%s" % name)
        for f in sorted(by_file[name], key=lambda x: x["line"]):
            out.append("  :%-5d  %-12s -> %s:%d" % (f["line"], f["reason"], f["cites"],
                                                    f["cited_line"]))
            out.append("           %s" % f["text"][:160])
    return out


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--json", action="store_true", help="emit the findings as JSON")
    ap.add_argument("--unresolved", action="store_true",
                    help="also list citations naming a module that is not in src/ -- usually a "
                         "correct reference into another tree, never filed as work")
    a = ap.parse_args()
    skipped = []
    found = stale_citations(include_unresolved=a.unresolved, skipped=skipped)
    if a.json:
        import json
        print(json.dumps(found, indent=1))
        return 0
    s = summary(found)
    print("CITECHECK — provably broken `file.py:NNN` citations under src/")
    print("=" * 78)
    for line in report(found):
        print(line)
    print("-" * 78)
    print("  %d finding(s): %s" % (
        s["total"],
        ", ".join("%s=%d" % (k, v) for k, v in sorted(s.items()) if k != "total") or "none"))
    # AND WHAT WAS SET ASIDE, BY KIND (orders 9daa719e4819 and d7efd67caa6f). A citation this
    # module declines to check is a CLAIM -- that it belongs to another tree, or that it is a
    # mention rather than a pointer -- and a claim nobody can see is one nobody can check.
    #
    # BY KIND, because there are now three of them. This printed one number under one sentence
    # about other trees, which since `_mention_kind` would state two of the three WRONGLY: the
    # exact failure the skip list exists against, committed by the line reporting it. `--json`
    # still emits findings only, so no consumer's input changes shape.
    by_why = {}
    for row in skipped:
        by_why.setdefault(row.get("why") or OTHER_TREE, []).append(row)
    _WHY_SAYS = {
        OTHER_TREE: "pointing into another tree (a path-like lead other than this tree's own "
                    "src/)",
        MENTION_QUOTED_TAG: "a quoted MENTION, not a citation -- a silence.note tag or a "
                            "fixture row, where the token is the name being discussed rather "
                            "than a line to go read",
        MENTION_SYMBOL_DISCLAIMER: "a line declaring 'cited by symbol, not line' -- the number "
                                   "beside it is the superseded form, kept as the record of "
                                   "the repair",
    }
    for why in sorted(by_why):
        print("  %d citation(s) set aside as %s" % (len(by_why[why]),
                                                    _WHY_SAYS.get(why, why)))
    if not skipped:
        print("  0 citation(s) set aside")
    print("  CLEAN HERE MEANS 'not provably broken', NOT 'verified' — this checks whether a "
          "cited line\n  CAN be the one meant, never whether it IS. See the module docstring.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
