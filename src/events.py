"""EVENTS — the Chronica Annex's event spine, parsed into stable codes. Phase 4.3's first artifact.

WHAT THIS IS FOR. STEP4_PLAN.md §4 gives Phase 4.3 as "T3, the Chronicle join: parse the event
spine into `data/EVENTS.json` with stable codes, join to entries", and §3 says T3 "is the first
class that crosses verses, and it crosses them *through the charter's own history* rather than by
resemblance". This module does the parse. The join is `threads.py`'s, and it may only join on what
this module records.

THE CONSTRAINT THIS MODULE EXISTS TO MAKE KEEPABLE, from §6, named there as the failure that would
do real damage: **T3 MUST JOIN ON EVENT PARTICIPATION, NEVER ON NAME SIMILARITY.** "If a thread's
only evidence is that two names resemble each other, it is not a thread." Joining "Wally West (New
Earth)" to "Wally West (Prime Earth)" is a *continuity* claim, and the ledger already shows 240
mined deeds stranded on exactly that question. So this module records, for every participant, the
EXACT string the Chronicle used and the event it used it in -- and nothing else. There is no
fuzzy matcher here, no stemmer, no edit distance, and there must never be one: a caller that wants
to know whether an entity took part in an event asks for an exact name, or gets nothing.

THE CODES ARE THE CHRONICLE'S OWN, NOT MINTED HERE. The spine already carries them --
`E-0000-SUND`, `E-0212-CROSS`, `E-0388-PORT`, `E-0902-VEILS`, `E-1112-BRACKET`, `E-CONV`,
`E-THEO`, `E-1204-DELIVERY`. "Stable" in §4's phrase means exactly that: this module reads codes
that already exist in an authored volume rather than inventing an identifier scheme that would
drift the first time the Chronicle was revised. A code appearing in the text but NOT owning a
heading is still a real event (`E-THEO` and `E-1204-DELIVERY` are both) and is recorded with
`heading: null` rather than dropped -- dropping it would be a cap, and a cap on an ordered listing
is the truncation Hard Rule 0 forbids.

WHY BOLD IS NOT TAKEN AS "PARTICIPANT", measured before deciding: the Chronicle carries 33 bolded
spans and they are not one kind of thing. Some are participants (`Seriah of Vel`, `Azor`,
`Tamiyo of the Eternities`); some are whole sentences used for emphasis (`And the Ladder slammed
its doors.`, `The Silence came through the description.`); some are treaties, panics and concepts
(`Pale Accords`, `Long Embargo`, `Energon Panic`, `Compact of Mirrors`). Emitting a thread for a
sentence would be absurd, and emitting one for a concept would be a category error. So a bolded
span is only ever a CANDIDATE here: this module records it, says which event it sits in, and
applies the shape rules below. Whether a candidate is a real entity is decided by the join, by
EXACT match against the catalogue -- never here, and never by resemblance.

WHAT THIS MODULE DELIBERATELY DOES NOT DO. It does not decide participation, it does not touch
`data/THREADS.json`, and it emits no threads. It reads one authored volume and writes one derived
file. `threads.py` owns the join and `thread_integrity.py` owns the verdict, exactly as they do
for T1 and T2.
"""
import argparse
import os
import re
import sys

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# A regex escape eaten in transit is this project's oldest bug; every module carries the guard.
_BAD_CHARS = (chr(8), chr(11), chr(12), chr(7))
if any(c in open(os.path.abspath(__file__), encoding="utf-8").read() for c in _BAD_CHARS):
    raise SystemExit(__file__ + ": a regex escape was eaten in transit.")

import silence  # noqa: E402

CHRONICLE = os.path.join(HERE, "reference", "keystone_volumes", "VIII_MASTER_CHRONICLE.md")
OUT = os.path.join(HERE, "data", "EVENTS.json")

# The Chronicle's own code shape: E- then upper-case letters, digits and hyphens.
CODE = re.compile(r"\bE-[A-Z0-9]+(?:-[A-Z0-9]+)*\b")
BOLD = re.compile(r"\*\*([^*]{2,80})\*\*")

# CANDIDATE SHAPE RULES, and every one of them is a REFUSAL rather than a repair. A span that
# fails any of these is recorded as a candidate that was NOT taken, with the rule that stopped it,
# because a filter that silently drops rows is how a roster quietly becomes a smaller universe.
MAX_WORDS = 8          # a participant is a name, not a clause
SENTENCE_END = (".", "!", "?", ":")


def _looks_like_a_sentence(s):
    """Is this bolded span prose rather than a name? -> (bool, reason or None).

    Deliberately conservative and deliberately explicit: each rule names itself in the record, so
    a later reader can see WHY a span was not offered to the join rather than finding it absent.
    """
    t = s.strip()
    if not t:
        return True, "empty"
    if t.endswith(SENTENCE_END):
        return True, "ends with sentence punctuation"
    if len(t.split()) > MAX_WORDS:
        return True, "longer than %d words" % MAX_WORDS
    # THERE IS NO THIRD RULE, AND THE COMMENT THAT CLAIMED ONE IS GONE (sweep of run #46).
    # This spot carried three sentences describing a rule about "a leading article plus a
    # verb-ish tail" and asserting that "only the plainest signal is used -- a lower-case first
    # letter after an article". No such test was ever written here; the function has always
    # returned False at this point. A reader auditing whether emphasis spans get through would
    # have read that paragraph, believed a filter was standing, and moved on -- which is this
    # project's oldest finding wearing prose instead of code: a check that cannot fail looks
    # exactly like a check that passed, and a check that does not exist looks like both.
    #
    # The absent rule is also the RIGHT thing to be absent. Deciding "The Silence came through
    # the description" is a sentence by inspecting its article and inferring a verb is grammar
    # guessing, and this module refuses that class of reasoning everywhere else on purpose. The
    # two rules above are mechanical -- terminal punctuation, word count -- and a span that slips
    # past both is not smuggled anywhere: it becomes a CANDIDATE, and a candidate still has to
    # equal a catalogued name exactly at the join. The cost of a false candidate is a row that
    # resolves to nobody. The cost of a grammar heuristic is a thread built on resemblance.
    return False, None


# The joiners the Chronicle uses inside one bold span to name two participants at once. Kept to a
# named, short list rather than a general splitter: a comma inside a title ("Solomon, called the
# Binding King") is ONE name, and a general split would manufacture "called the Binding King" as a
# participant. Each fragment must still match the catalogue exactly to survive the join, so a
# wrong split costs nothing but a candidate that resolves to nobody.
_SPAN_JOINERS = (", wearing ", " wearing ", " and ", " & ")


def _fragments(span):
    """The separately-named participants inside one bold span, if it names more than one. -> [str].

    Returns [] for the ordinary case of a span that names one thing. Only splits on the explicit
    joiners above, and only when BOTH sides survive the same shape rules the whole span faced --
    so a split can never smuggle in a clause the unsplit span would have been refused for.
    """
    for j in _SPAN_JOINERS:
        if j in span:
            parts = [p.strip(" ,;") for p in span.split(j)]
            out = []
            for p in parts:
                if not p or p == span.strip():
                    continue
                bad, _why = _looks_like_a_sentence(p)
                if not bad:
                    out.append(p)
            if len(out) >= 2:
                return out
    return []


def shelf_positions(text):
    """The Concordance table: where each shelf stands at the Delivery. -> [{shelf, stands_at}].

    THIS IS PARTICIPATION, NOT RESEMBLANCE, and it is the richest such surface the Chronicle has.
    "THE CONCORDANCE NOW — CANON POSITIONS BY SHELF" states, for each major shelf, where its local
    canon stands at Delivery (1,204 AS, `E-1204-DELIVERY`). A shelf's presence in that table is
    the charter's own history placing it in a dated event -- exactly what §3 means by crossing
    verses "through the charter's own history rather than by resemblance".

    Parsed but NOT joined here. Whether a shelf name corresponds to a source on the Acquisitions
    Roll is `threads.py`'s question, answered by the address resolver, never by this module.
    """
    rows, in_table = [], False
    for ln in text.splitlines():
        s = ln.strip()
        # `"stands at"` IS TESTED AGAINST THE LINE ITSELF. This read
        # `"stands at" in s.replace("Now ", "")`, which looked like it was normalising the header
        # so the test could match -- and was doing nothing at all, because the header reads
        # `| Shelf | Now stands at |` and "Now stands at" already CONTAINS "stands at". The
        # replace could be deleted with no change in behaviour on any input, so it was not a
        # normalisation step, it was a decoy: a future reader would have preserved it while
        # editing the real condition, or trusted that some header variant depended on it. Removed
        # rather than kept, on the same grounds this file refuses a grammar heuristic -- the
        # dangerous line is not the one that is wrong, it is the one that cannot be wrong.
        if s.startswith("|") and "Shelf" in s and "stands at" in s:
            in_table = True
            continue
        if in_table:
            if not s.startswith("|"):
                if rows:
                    break
                continue
            cells = [c.strip() for c in s.strip("|").split("|")]
            if len(cells) < 2 or set(cells[0]) <= set("-: "):
                continue
            rows.append({"shelf": cells[0], "stands_at": cells[1]})
    return rows


def parse(text=None):
    """Read the spine. -> {"events": [...], "ages": [...], "candidates_refused": [...]}.

    Every event the Chronicle names gets a row, whether or not it owns a heading. The body of a
    heading-owning event is the text from its heading to the next heading of the same or higher
    level; an event named only in passing carries `heading: null` and no body, and says so.
    """
    if text is None:
        with open(CHRONICLE, encoding="utf-8") as f:
            text = f.read()
    lines = text.splitlines()

    # Headings, with their level, so a body can end at the next same-or-higher heading.
    heads = []
    for i, ln in enumerate(lines):
        m = re.match(r"^(#{1,6})\s+(.*)$", ln)
        if m:
            heads.append((i, len(m.group(1)), m.group(2).strip()))

    ages = [h[2] for h in heads if h[1] == 2]

    events, seen = [], {}
    for idx, (i, lvl, title) in enumerate(heads):
        codes = CODE.findall(title)
        if not codes:
            continue
        end = len(lines)
        for j, lvl2, _t2 in heads[idx + 1:]:
            if lvl2 <= lvl:
                end = j
                break
        body = "\n".join(lines[i + 1:end]).strip()
        # The age this event sits under: the nearest preceding level-2 heading.
        age = None
        for j, lvl2, t2 in reversed(heads[:idx + 1]):
            if lvl2 == 2:
                age = t2
                break
        for code in codes:
            if code in seen:
                continue
            seen[code] = True
            events.append({"code": code, "heading": title, "age": age,
                           "body_chars": len(body), "body": body})

    # Codes the Chronicle uses without giving them a heading of their own. They are real events --
    # E-THEO (the Theomachies) and E-1204-DELIVERY (the Delivery) both are -- and dropping them
    # because they are cited rather than titled would be a cap on the roster.
    for code in CODE.findall(text):
        if code in seen:
            continue
        seen[code] = True
        events.append({"code": code, "heading": None, "age": None,
                       "body_chars": 0, "body": ""})

    refused, splits = [], []
    for ev in events:
        named, seen_here = [], set()
        for span in BOLD.findall(ev["body"]):
            s = span.strip()
            bad, why = _looks_like_a_sentence(s)
            if bad:
                refused.append({"event": ev["code"], "span": s, "rule": why})
                continue
            if s in seen_here:
                continue
            seen_here.add(s)
            # THE EXACT STRING, UNTOUCHED. No casefolding, no stripping of honorifics, no
            # normalisation of any kind is applied here. The join matches on this verbatim, and
            # anything this module smoothed away would be a resemblance the join could not see it
            # was making.
            named.append(s)
            # ONE SPAN CAN CARRY TWO PARTICIPANTS, and dropping the second is a cap.
            # `**Soul Edge, wearing Siegfried**` is one bold span naming two entities, and BOTH
            # are catalogued (Soul Calibur) -- measured. Taking the span whole matched neither,
            # so the Chronicle's own statement that they took part in E-1112-BRACKET was lost to
            # punctuation. The fragments are offered SEPARATELY, each recorded with the span it
            # came from so the evidence stays auditable.
            #
            # THIS IS NOT RESEMBLANCE MATCHING, and the distinction is the one §6 turns on: the
            # fragment is still required to equal a catalogued name EXACTLY at the join. Splitting
            # a string is tokenisation; deciding two different strings mean the same entity is
            # what this pass may never do.
            for frag in _fragments(s):
                if frag in seen_here:
                    continue
                seen_here.add(frag)
                named.append(frag)
                splits.append({"event": ev["code"], "span": s, "fragment": frag})
        ev["named"] = named
        ev.pop("body")          # the body is the source, not the artifact; codes and names are
    return {"events": events, "ages": ages, "candidates_refused": refused,
            "spans_split": splits, "shelf_positions": shelf_positions(text)}


def build(write=False):
    """Parse and optionally land `data/EVENTS.json`. -> the document."""
    doc = parse()
    doc["source"] = os.path.relpath(CHRONICLE, HERE).replace("\\", "/")
    doc["counts"] = {
        "events": len(doc["events"]),
        "events_with_a_heading": sum(1 for e in doc["events"] if e["heading"]),
        "named_participants": sum(len(e["named"]) for e in doc["events"]),
        "distinct_named": len({n for e in doc["events"] for n in e["named"]}),
        "candidates_refused": len(doc["candidates_refused"]),
        "spans_split": len(doc["spans_split"]),
        "shelf_positions": len(doc["shelf_positions"]),
    }
    if write:
        landed = silence.write_json(OUT, doc, indent=1)
        if not landed:
            # A denied write is reported, never swallowed: the caller decides, and a half-landed
            # spine is worse than none.
            raise RuntimeError("EVENTS.json could not be landed (atomic replace denied); "
                               "nothing downstream may read this run's parse")
    return doc


def main():
    # THIS CLI COULD NOT PRINT ITS OWN CONTENT (2026-09-09 sweep, batch 04). `E-CONV`'s heading
    # carries a Unicode minus sign, so `print` raised UnicodeEncodeError on a bare Windows
    # console -- the module crashed on the very spine it exists to read, and only the
    # PYTHONIOENCODING=utf-8 the maintenance instructions happen to mandate was hiding it.
    # Reproduced both ways before this was added. Same fix, same shape, as `threads.py` and
    # `handbuilt.py` already carry, and for the same reason: a CLI that dies on its own data is
    # a gate nobody can run.
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass        # an older stdout without reconfigure is not a reason to refuse to run
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--write", action="store_true", help="land data/EVENTS.json")
    ap.add_argument("--refused", action="store_true",
                    help="print every bolded span NOT offered to the join, with the rule")
    a = ap.parse_args()
    doc = build(write=a.write)
    c = doc["counts"]
    print("THE EVENT SPINE — %s" % doc["source"])
    print("=" * 78)
    print("  events                 %4d  (%d own a heading, %d are cited without one)"
          % (c["events"], c["events_with_a_heading"], c["events"] - c["events_with_a_heading"]))
    print("  named participants     %4d  (%d distinct)"
          % (c["named_participants"], c["distinct_named"]))
    print("  bolded spans refused   %4d  (emphasis and concepts, not names)"
          % c["candidates_refused"])
    print()
    for e in doc["events"]:
        print("  %-16s %s" % (e["code"], (e["heading"] or "(cited without a heading)")[:58]))
        if e["named"]:
            print("        names: %s" % ", ".join(e["named"]))
    if a.refused:
        print()
        print("  REFUSED CANDIDATES — recorded, not dropped:")
        for r in doc["candidates_refused"]:
            print("    %-16s %-46s (%s)" % (r["event"], r["span"][:46], r["rule"]))
    print()
    print("  A name here is a CANDIDATE. Whether it is a real entity is decided by the join, by")
    print("  EXACT match against the catalogue -- never by resemblance (STEP4_PLAN.md §6).")
    if a.write:
        print("  -> %s" % OUT)
    return 0


if __name__ == "__main__":
    sys.exit(main())
