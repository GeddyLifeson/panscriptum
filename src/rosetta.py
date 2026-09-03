#!/usr/bin/env python3
"""
ROSETTA — each fiction's own power scale, mined and used as ground truth.

Charter Part Three, on the Rosetta Tables (Vol. X.4): they "run the conversion the other way,
mapping each universe's native scale (scouter power-levels, psyker grades, Stand statistics,
Devil Fruit awakening stages...) onto the Assay, per U-code."

This matters far more for ACCURACY than for flavour. Every other check on the Assay is either
mechanical (does the citation exist, does the arithmetic hold) or tiny (six published values).
A franchise's own scale is large-N ground truth that nobody here authored: One Piece publishes
186 bounties, Dragon Ball publishes 114 power levels, and those orderings are canon. If our
Assay ranks two One Piece characters in the order their bounties forbid, that is a defect we can
detect without asking anyone's opinion.

THE ONE DOCTRINE THAT MAKES THIS WORK
-------------------------------------
We do NOT convert native scales into joules, and any attempt to would be false precision. A
power level is not an energy and a bounty is a bureaucratic threat assessment, not a physical
quantity — Buggy's bounty is famously inflated by association rather than by power, which is
exactly the kind of noise a conversion would launder into a number.

What a native scale gives is an ORDER, and order is all the test needs. The check is monotone
agreement: Spearman rank correlation between the native ordering and ours, per franchise. That
also matches how every other weight in this library is set — fitted from data, never decreed.

Two families of scale, two parsers:

  NUMERIC   power levels, bounties, chakra reserves. Values are magnitudes; rank them directly.
  ORDINAL   One-Punch Man's Wolf/Tiger/Demon/Dragon/God, curse grades, psyker ratings, hero
            classes. There is no number, only a published order, which is still a total order
            and still testable. `Disaster Level` yields zero numeric pairs and is not therefore
            useless — it is the second kind.
"""
import argparse
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import feats as F                                                       # noqa: E402
import pipeline as P                                                    # noqa: E402
import silence

# A regex escape arriving as a literal control character matches nothing and fails SILENTLY.
# A word-boundary escape written through a shell heredoc has arrived here as a 0x08 backspace
# five separate times in this project. Each time it read as a tuning problem -- a gate that
# passed nothing, a parser that found zero rows -- rather than as corruption, which is what
# makes it expensive. The check is built from chr() codes because the first version was
# written with escapes and they were eaten too, so it flagged its own source and refused.
_BAD_CHARS = (chr(8), chr(11), chr(12), chr(7))
if any(c in open(os.path.abspath(__file__), encoding='utf-8').read() for c in _BAD_CHARS):
    raise SystemExit(__file__ + ': a regex escape was eaten in transit - a literal control '
                     'character is present in the source. Repair before running.')


OUT = os.path.join(HERE, "data", "ROSETTA.json")

# How much of the standing mine a fresh `--mine` must reproduce before it may replace it.
# A pass that comes back with three quarters of what is already on disk is a pass that lost a
# quarter of the library's only large-N external ground truth to a throttle, and `scales_for`
# reports a throttled wiki as an empty one -- so the row count is the only signal there is.
# Not a cap on anything: nothing is dropped, the whole mine is either written or refused with
# its reason and re-run. `--force` is the deliberate override. (order 6447bcc2f18c)
MINE_FLOOR = 0.75

# What a native scale is called, across fictions. Searched per wiki; a hit only counts if the
# page then parses into enough rows to be a scale rather than an essay about one.
SCALE_QUERIES = [
    "list of power levels", "power level", "battle power",
    "bounty list", "list of bounties",
    "disaster level", "threat level", "danger level", "hazard level",
    "curse grade", "grade sorcerer", "cursed energy",
    "hero class", "hero ranking",
    "esper level", "level 5",
    "psyker rating", "psychic rating",
    "ninja rank", "shinobi rank",
    "stand stats", "stand parameters",
    "hunter rank", "nen", "haki",
    "devil rank", "quirk ranking", "rank system", "classification system",
]
# Stems, with NO trailing word boundary. The first version wrote `\bbount\b`, which cannot match
# inside "Bounty" — the `y` is a word character, so there is no boundary there. One Piece's
# `Bounty/List`, 195,557 characters and 186 canonical figures, was silently discarded by that
# single `\b`, and the whole wiki came back with one unrelated page.
_SCALE_TITLE = re.compile(
    r"(power level|battle power|bount|disaster level|threat level|danger level|"
    r"hazard level|grade|class|rank|rating|level|tier|stat|parameter|scale)", re.I)

# Ordinal ladders that fictions publish as words. Low index = weak. Written out because these
# are declared orders in the source, not something to infer: One-Punch Man's Wolf-through-God is
# stated on the page, and guessing it from prose would invent a fact the fiction already fixed.
#
# Every tier string must be a distinctive phrase. An early version included Stand statistics as
# ["e","d","c","b","a"] and the single letters matched somewhere on every page of every wiki, so
# the parser graded all 49 entities on an unrelated One-Punch Man page at the top of the ladder.
# A ladder whose rungs are single characters cannot be found by matching; Stand stats are read
# from their parameter block instead (see _STAND).
ORDINAL_LADDERS = {
    "disaster": ["wolf level", "tiger level", "demon level", "dragon level", "god level"],
    "hero_class": ["c-class", "b-class", "a-class", "s-class"],
    "curse_grade": ["grade 4", "grade 3", "grade 2", "grade 1",
                    "semi-first grade", "special grade"],
    "ninja_rank": ["academy student", "genin", "chunin", "jonin", "kage"],
    "esper_level": ["level 0", "level 1", "level 2", "level 3", "level 4", "level 5"],
}

# Stand statistics only ever appear inside a labelled parameter block, which is what makes them
# findable at all: "Power: A", "Speed: B". The label is the context the bare letter lacks.
_STAND = re.compile(
    r"\b(power|speed|range|durability|precision|potential)\s*[:=|]\s*([A-E])\b", re.I)

# Section headings and link targets that are not characters. Without this the DBZ table yields
# "Frieza Saga -> 2000" and the One Piece table yields "Straw Hat Pirates#Bounties -> 903".
_NOT_A_NAME = re.compile(
    r"^(list|saga|arc|chapter|episode|volume|movie|film|game|manga|anime|the [a-z]|"
    r"[a-z ]*(?:pirates|crew|powers|bounties|characters|references|contents))\b|#|/", re.I)

_PAIR = re.compile(r"\[\[([^\]|#]{2,40})(?:\|[^\]]*)?\]\][^\n]{0,120}?([0-9][0-9,\.]{2,})")


def numeric_rows(wikitext):
    """(name, value) pairs read ROW BY ROW from a wikitable.

    The first version searched a 120-character window after each link for a number, which reads
    straight across row boundaries in a dense table. On One Piece it paired Gecko Moria with
    2,247,600,000 -- Blackbeard's bounty, one row down -- and gave Monkey D. Garp a figure he has
    never had. Both are the same bug: proximity in the source text is not membership in a row.

    A wikitable row starts at `|-` and its cells are `|` or `!` delimited. Taking the link and
    the number from within ONE row makes the pairing structural rather than a guess about
    distance. Prose lists still fall back to the window, since they have no rows to respect.
    """
    out = {}

    def offer(name, raw):
        name = name.strip()
        if _NOT_A_NAME.search(name) or len(name) < 3:
            return
        try:
            v = float(raw.replace(",", "").rstrip("."))
        except ValueError:
            silence.note("rosetta.py:offer-bad-number")
            return
        if v <= 0:
            return
        # A character's highest published figure is their scale position; lower earlier readings
        # are epochs of the same being, and the Ascension Curve holds those.
        out[name] = max(out.get(name, 0.0), v)

    rows = re.split(r"^\s*\|-.*$", wikitext, flags=re.M)
    tabular = len(rows) > 4
    for row in rows:
        if tabular and len(row) > 600:
            continue                        # not a row; a run of prose between tables
        links = re.findall(r"\[\[([^\]|#]{2,40})(?:\|[^\]]*)?\]\]", row)
        nums = re.findall(r"\b([0-9][0-9,]{2,})(?![0-9,]*\s*(?:px|em|%))", row)
        # The FIRST number after the name, never the largest. A bounty table carries current
        # bounty, previous bounties and a first-appearance chapter in one row, and taking the max
        # gave Roronoa Zoro 1,563,924,260,242,206,720 — several columns read as one figure.
        # Column order puts the current value first, which is the one the scale means.
        if len(links) == 1 and nums:
            offer(links[0], nums[0])
        elif links and nums and len(links) == len(nums):
            for n, v in zip(links, nums, strict=True):    # one-to-one row, safe to zip
                offer(n, v)

    if not out and not tabular:              # prose list: fall back to proximity
        for name, raw in _PAIR.findall(wikitext):
            offer(name, raw)

    # A published scale spans orders of magnitude but not twelve of them. Anything a thousand
    # times the median is a parse artefact rather than a very strong character, and leaving it in
    # would dominate a rank correlation single-handedly.
    if len(out) >= 8:
        med = sorted(out.values())[len(out) // 2]
        out = {k: v for k, v in out.items() if v <= med * 1000}
    return out


def ordinal_rows(wikitext, ladder):
    """(name, rank-index) pairs for a published word-ladder.

    MATCHED CASE-INSENSITIVELY ON THE ORIGINAL, NEVER ON A LOWERCASED COPY (order f045ffe20c52).
    This searched `wikitext.lower()` and then sliced the ORIGINAL with the offsets it found, and
    `str.lower()` is not length-preserving in Unicode: 'İ'.lower() is two code points, so one
    such character anywhere earlier in a page shifts every subsequent offset by one, and by more
    with each additional one. The 160-character context window then drifts off the tier it is
    supposed to sit beside and the [[names]] harvested get graded onto the wrong rung -- silently,
    at low frequency, in the only parser the library has for fictions that publish no numbers.
    `re.I` on the source text gives the same matches with offsets that are the real ones.
    """
    out = {}
    for i, tier in enumerate(ladder):
        for m in re.finditer(r"\b" + re.escape(tier), wikitext, re.I):
            seg = wikitext[max(0, m.start() - 160):m.start()]
            for name in re.findall(r"\[\[([^\]|#]{3,40})(?:\|[^\]]*)?\]\]", seg):
                name = name.strip()
                if _NOT_A_NAME.search(name):
                    continue
                out[name] = max(out.get(name, -1), i)
    return out


def scales_for(host, verbose=False, errors=None):
    """Every native scale this wiki publishes, as {scale_name: {entity: value}}.

    `errors`, if a list is passed, receives one string per search that did not come back --
    a throttle, a 429, a block, an exception out of `F.api`. It exists because this function
    CANNOT otherwise distinguish "this wiki publishes no scale" from "we were not allowed to
    look": both end at `if not seen: return {}` and both read, to the caller, as an empty wiki
    (order 6447bcc2f18c). The return value is unchanged, so every existing caller is unaffected.
    """
    seen, found = set(), {}
    for q in SCALE_QUERIES:
        # srlimit=50, matching feats.py's discover() -- audited (m82) not to truncate. 5 was
        # below the API's OWN default of 10, and this call is the acquisition step for the
        # library's only large-N external ground truth (see the One Piece Bounty/List loss noted
        # above): a relevance-ranked page beyond the cutoff is a page this pass never sees.
        try:
            d = F.api(host, {"action": "query", "list": "search",
                             "srlimit": "50", "srsearch": q})
        except Exception as e:
            # PER QUERY, like binding_health.run and chain.harvest guard per item: one search
            # raising must not cost this wiki its other thirty.
            silence.note("rosetta.py:scales_for-api")
            if errors is not None:
                errors.append("%s: %s (%s)" % (q, type(e).__name__, str(e)[:60]))
            continue
        if d is None and errors is not None:
            errors.append("%s: no response" % q)
        for row in (d or {}).get("query", {}).get("search", []):
            t = row["title"]
            if t in seen or not _SCALE_TITLE.search(t) or row.get("size", 0) < 1500:
                continue
            seen.add(t)

    if not seen:
        return {}
    try:
        pages = F.fetch(host, sorted(seen))
    except Exception as e:
        silence.note("rosetta.py:scales_for-fetch")
        if errors is not None:
            errors.append("fetch of %d page(s): %s (%s)"
                          % (len(seen), type(e).__name__, str(e)[:60]))
        return {}
    for title, wt in pages.items():
        rows = numeric_rows(wt)
        kind = "numeric"
        if len(rows) < 8:
            best, blab = {}, None
            for lab, ladder in ORDINAL_LADDERS.items():
                r = ordinal_rows(wt, ladder)
                if len(r) > len(best):
                    best, blab = r, lab
            if len(best) >= 8:
                rows, kind = best, f"ordinal:{blab}"
            else:
                continue
        found[title] = {"kind": kind, "n": len(rows), "values": rows}
        if verbose:
            print(f"      {kind:<18}{len(rows):>4} rows   {title}")
    return found


# --------------------------------------------------------------------------- validation

def spearman(pairs):
    """Rank correlation. Written out rather than imported: scipy is not a dependency here and
    this is twelve lines."""
    if len(pairs) < 4:
        return None
    xs = [p[0] for p in pairs]
    ys = [p[1] for p in pairs]

    def rank(v):
        order = sorted(range(len(v)), key=lambda i: v[i])
        r = [0.0] * len(v)
        i = 0
        while i < len(order):                       # average ties, or ordinal ladders skew
            j = i
            while j + 1 < len(order) and v[order[j + 1]] == v[order[i]]:
                j += 1
            avg = (i + j) / 2.0 + 1
            for k in range(i, j + 1):
                r[order[k]] = avg
            i = j + 1
        return r

    rx, ry = rank(xs), rank(ys)
    n = len(rx)
    mx, my = sum(rx) / n, sum(ry) / n
    num = sum((a - mx) * (b - my) for a, b in zip(rx, ry, strict=True))
    dx = sum((a - mx) ** 2 for a in rx) ** 0.5
    dy = sum((b - my) ** 2 for b in ry) ** 0.5
    return round(num / (dx * dy), 3) if dx and dy else None


def _norm(s):
    return re.sub(r"[^a-z0-9]+", " ", s.lower()).strip()


def assays_by_host(assays):
    """{host: {normalised name: decimal}} from ASSAYS.json's own `host|Name` keys.

    THE KEY ALREADY CARRIES THE WIKI, which is what makes the host scoping below exact rather
    than inferred: an assay records which host its entity was read from, so nothing has to be
    matched up out of the corpus to know it. A key with no `|` is filed under the empty host,
    where it can only match a scale from a wiki of that name -- i.e. nothing -- rather than
    being quietly promoted into whichever franchise asked first.

    Returns (by_host, collisions), where `collisions` names every "host|name" that two assay
    keys normalised onto -- the last one read wins for those, and that is not something to
    discover later from a rho that looks odd.
    """
    out, collisions = {}, []
    for k, v in assays.items():
        h, sep, n = k.partition("|")
        # str.partition puts the WHOLE string in the head when the separator is absent, so a
        # bare key "Goku" once became host="Goku", name="" -- the opposite of the docstring's
        # promise that a bare key files under the empty host with its name intact. Split only
        # when "|" is actually present (order 52a73082c56b).
        h, n = (h, n) if sep else ("", h)
        n = _norm(n)
        if n in out.setdefault(h, {}):
            collisions.append("%s|%s" % (h, n))
        out[h][n] = v
    return out, sorted(collisions)


def check(rosetta, assays, by_host=None):
    """Monotone agreement between each native scale and our Assay, per franchise.

    A low correlation is a finding about the Assay, not about the fiction. It says our ordering
    contradicts an ordering the source publishes.

    SCOPED PER WIKI WHEN THE CALLER CAN SUPPLY THE SCOPING (order 0bba50a6d76b). `a_by` was ONE
    GLOBAL map from normalised name to assay decimal and every scale row was looked up in it
    regardless of which wiki the row came from -- `host` was never used in the lookup. That is
    the construction `refine()`'s docstring calls "how a filter becomes a rubber stamp" and
    deliberately avoids: against an unrefined ROSETTA.json a Star Trek row can be vouched for by
    a One Piece assay of the same normalised name. Pass `by_host` (from `assays_by_host`) and a
    row is only ever matched against an assay recorded on its own wiki. `by_host=None` keeps the
    old global behaviour, because `verify_math` drives this function directly with a synthetic
    scale and bare names.

    AND THE GLOBAL PATH WAS NOT EVEN MATCHING. Measured on the live files while fixing the
    above: ASSAYS.json is keyed `host|Name` ("dragonball.fandom.com|Goku"), so `_norm(key)` gave
    "dragonball fandom com goku" and NOTHING matched a scale row's bare name -- all 8 standing
    scales scored 0 overlap, every rho came back None, and rho=None rows were dropped from the
    report entirely. So this check, an allsweep VERIFIER and the module's whole stated purpose,
    printed an empty list and exited 0 while measuring nothing at all. `assays_by_host` splits
    the key the way it is actually written; the Dragon Ball power-level scale scores n=4,
    rho=0.6 with it, and did not exist in the report before.

    A SCALE THAT CANNOT BE SCORED NOW GETS A ROW. `spearman` returns None below four overlapping
    names and the scale simply vanished, so "we disagree with nothing here" and "we could not
    test this at all" produced the same empty space -- which is exactly how the total failure
    above stayed invisible. Those rows come back with `rho: None` and sort last; the caller
    prints them as unscored and does not count them as disagreements.
    """
    a_by, collided = {}, set()
    for k, v in assays.items():
        n = _norm(k)
        # _norm COLLISIONS ARE COUNTED, NOT SWALLOWED. This was a dict comprehension, so two
        # assays normalising to the same key silently kept the last one and nothing said which
        # decimal was being used for the name. (The scoped path reports its own collisions from
        # `assays_by_host`, where they are per wiki and therefore the ones that can bite.)
        if n in a_by:
            collided.add(n)
        a_by[n] = v
    report = []
    for host, scales in rosetta.items():
        known = a_by if by_host is None else by_host.get(host, {})
        for title, sc in scales.items():
            pairs, unmatched = [], 0
            for name, val in sc["values"].items():
                got = known.get(_norm(name))
                if got is None:
                    # Named on this wiki's published scale and carrying no assay from this same
                    # wiki. It may well be assayed elsewhere under the same name; that is
                    # precisely the vouching the scoping refuses.
                    unmatched += 1
                    continue
                pairs.append((val, got))
            report.append({"host": host, "scale": title, "kind": sc["kind"],
                           "overlap": len(pairs), "rho": spearman(pairs),
                           "unmatched": unmatched,
                           "ambiguous_assay_names": len(collided)})
    # rho None (unscorable) sorts last rather than crashing the comparison, and the scorable
    # rows keep their worst-first ordering.
    return sorted(report, key=lambda r: (r["rho"] is None, r["rho"] if r["rho"] is not None else 0))


def refine(rosetta, records, hosts):
    """Keep only rows that name an entity this library actually catalogues, on that same wiki.

    The raw mine grades 2,000 distinct names and only 154 of them are characters. The rest are
    dates lifted from a Star Trek timeline ("2239", "23rd century"), a Magic designer's byline,
    and common nouns that happened to sit beside a number ("academia", "acorn", "admiral").
    Precision, not the join, was the problem, and the honest filter is the corpus itself: a
    published scale position for something we do not catalogue cannot calibrate anything.

    Matching is scoped PER HOST rather than globally, so a name on the Star Trek wiki can only
    match a Star Trek entity. Matching globally would let any 16,000 catalogued names vouch for
    any row, which is how a filter becomes a rubber stamp.
    """
    by_host = {}
    for _, r in records:
        h = hosts.get(r["source"])
        if not h:
            continue
        by_host.setdefault(h, set()).update(
            _norm(e["name"]) for e in r["entries"]
            # Persons only. Filtering on every catalogued entry let "Sabaody Archipelago" and
            # "Cross Guild" through as graded characters, because a bounty table names places
            # and crews too and the library does catalogue those -- as Places and Factions.
            if (e.get("category") or "").startswith("Persons"))

    out, kept, dropped = {}, 0, 0
    for host, scales in rosetta.items():
        known = by_host.get(host, set())
        keep_scales = {}
        for title, sc in scales.items():
            vals = {n: v for n, v in sc["values"].items() if _norm(n) in known}
            dropped += len(sc["values"]) - len(vals)
            kept += len(vals)
            if len(vals) < 4:                  # below four rows a scale cannot rank anything
                continue
            # A POWER scale spans orders of magnitude; a PROGRESSION ladder counts 1 to 100.
            # Fortnite's "Final Level", Call of Duty's multiplayer ranks and a Terminator RPG's
            # NPC stat blocks all parse cleanly and all measure how long someone has played,
            # which would enter a rank correlation as pure noise wearing the right shape.
            # One Piece's bounties span six orders; Dragon Ball's scouter figures span two.
            if sc["kind"] == "numeric":
                lo, hi = min(vals.values()), max(vals.values())
                if lo <= 0 or hi / lo < 100:
                    continue
            keep_scales[title] = {"kind": sc["kind"], "n": len(vals), "values": vals}
        if keep_scales:
            out[host] = keep_scales
    return out, kept, dropped


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--mine", action="store_true", help="mine native scales from every wiki")
    ap.add_argument("--probe", metavar="HOST")
    ap.add_argument("--check", action="store_true", help="score our Assay against the scales")
    ap.add_argument("--refine", action="store_true",
                    help="drop scale rows that name nothing this library catalogues")
    ap.add_argument("--force", action="store_true",
                    help="let --mine overwrite a standing mine it cannot show is no smaller "
                         "(use when a parser fix legitimately shrinks the row count)")
    a = ap.parse_args()

    if a.probe:
        for t, sc in scales_for(a.probe, verbose=True).items():
            top = sorted(sc["values"].items(), key=lambda kv: -kv[1])[:6]
            for n, v in top:
                print(f"          {n[:34]:<36}{v:,.0f}")
        return 0

    if a.mine:
        hosts = json.load(open(F.HOSTS, encoding="utf-8"))
        uniq = sorted({h for h in hosts.values() if h and "wikipedia" not in h})
        out, empty, failed = {}, [], {}
        for i, h in enumerate(uniq, 1):
            # PER HOST, so one wiki raising cannot cost the pass every wiki mined before it.
            # `scales_for` did not catch `F.api` raising and neither did this loop, so a single
            # 429 that came back as an exception aborted the whole run BEFORE either write and
            # lost the lot. `binding_health.run` and `chain.harvest` both guard per item for
            # exactly this reason. (order 6447bcc2f18c)
            errs = []
            try:
                sc = scales_for(h, errors=errs)
            except Exception as e:
                silence.note("rosetta.py:mine-host")
                failed[h] = "%s: %s" % (type(e).__name__, str(e)[:70])
                print(f"  {i:>3}/{len(uniq)}  {h:<38}FAILED -- {failed[h]}", flush=True)
                continue
            if errs:
                failed[h] = "%d of %d searches did not come back" % (len(errs), len(SCALE_QUERIES))
            if sc:
                out[h] = sc
                tot = sum(v["n"] for v in sc.values())
                print(f"  {i:>3}/{len(uniq)}  {h:<38}{len(sc)} scale(s), {tot:,} rows"
                      + (f"   [{failed[h]}]" if h in failed else ""),
                      flush=True)
            else:
                # COUNTED, not passed over in silence. A host that yields nothing is the unit
                # this pass degrades in, and nothing was tallying them.
                empty.append(h)
                if h in failed:
                    print(f"  {i:>3}/{len(uniq)}  {h:<38}nothing -- {failed[h]}", flush=True)
                elif i % 25 == 0:
                    print(f"  {i:>3}/{len(uniq)}  ...", flush=True)

        rows = sum(v["n"] for s in out.values() for v in s.values())
        print(f"\n{len(uniq)} wiki(s) asked: {len(out)} published a scale, {len(empty)} yielded "
              f"nothing, {len(failed)} had at least one search fail.")
        if failed:
            # Named in full: which wikis were not actually measured is the whole question when
            # the numbers below look thin (Hard Rule 0).
            print("  searches that did not come back, by wiki: "
                  + "; ".join(f"{h} ({why})" for h, why in sorted(failed.items())))

        # DO NOT OVERWRITE A BIGGER MINE WITH A SMALLER ONE WITHOUT SAYING SO (order
        # 6447bcc2f18c). Both files were written from the same `out` with nothing compared
        # against the standing file first, so a throttled or blocked pass -- which `scales_for`
        # reports as an empty wiki, not as an error -- replaced a good mine with a degraded one
        # AND replaced the raw copy that was the only thing resembling a backup. The comment on
        # those very lines records that a stale copy already cost "a good 3,514-row mine" once.
        # An unreadable standing file refuses too: not being able to compare is not evidence
        # that the new mine is at least as good.
        prior_rows, prior_why = 0, ""
        try:
            with open(OUT, encoding="utf-8") as f:
                prior = json.load(f)
            prior_rows = sum(v["n"] for s in prior.values() for v in s.values())
        except FileNotFoundError:
            prior_why = ""                     # genuinely the first mine; nothing to protect
        except Exception as e:
            silence.note("rosetta.py:mine-prior-unreadable")
            prior_why = ("the standing %s could not be read (%s), so this mine cannot be "
                         "compared against it" % (os.path.basename(OUT), type(e).__name__))
        if not prior_why and prior_rows and rows < prior_rows * MINE_FLOOR:
            prior_why = ("this mine holds %s rows against the standing file's %s (%.0f%%, floor "
                         "%.0f%%)" % (f"{rows:,}", f"{prior_rows:,}",
                                      100.0 * rows / prior_rows, 100.0 * MINE_FLOOR))
        if prior_why and not a.force:
            print("\nREFUSING TO WRITE: %s. Nothing on disk was touched -- the standing mine and "
                  "its raw copy still stand. Re-run when the hosts above are reachable, or pass "
                  "--force if this smaller mine is the intended one (a parser that stopped "
                  "accepting junk legitimately shrinks the count)." % prior_why, file=sys.stderr)
            return 1
        if prior_why:
            print("\n--force: overwriting anyway. %s" % prior_why)
        # The raw mine is written alongside the working file. `--refine` is destructive and was
        # run against a stale raw copy once, which silently discarded a good 3,514-row mine and
        # replaced it with the output of the parser that had already been fixed.
        # Landed, not truncated-then-filled. The 2026-08-25 whole-tree sweep fixed this exact
        # pattern in scout.py, grounding.py and coverage.py -- all three carry a comment naming
        # that date -- and missed rosetta.py, which already imported `silence` without using it.
        for path in (OUT, OUT.replace(".json", ".raw.json")):
            if not silence.write_json(path, out, indent=1, ensure_ascii=False):
                print("rosetta: %s could not be replaced; the mine above is NOT on disk."
                      % os.path.basename(path), file=sys.stderr)
                return 1
        print(f"\n{len(out)} wikis publish a native scale; {rows:,} graded entities "
              f"(standing file held {prior_rows:,})  -> {OUT}")
        return 0

    if a.refine:
        rosetta = json.load(open(OUT, encoding="utf-8"))
        hosts = json.load(open(F.HOSTS, encoding="utf-8"))
        recs = P.records()
        before = sum(v["n"] for sc in rosetta.values() for v in sc.values())
        out, kept, dropped = refine(rosetta, recs, hosts)
        # `--refine` is the destructive mode: a torn write here loses the mine AND the refinement.
        if not silence.write_json(OUT, out, indent=1, ensure_ascii=False):
            print("rosetta: %s could not be replaced; it still holds the PRE-refine rows."
                  % os.path.basename(OUT), file=sys.stderr)
            return 1
        print(f"rows before refine : {before:,}")
        print(f"rows kept          : {kept:,}   dropped: {dropped:,}")
        print(f"scales surviving   : {sum(len(v) for v in out.values())} "
              f"across {len(out)} wikis")
        # UNCUT, BOTH CUTS (Hard Rule 0, sweep42-batch09). The host list was ranked by row count
        # and then truncated to twelve with no "and N more", and the per-host scale names were
        # cut at 44 characters on top of that -- so a wiki outside the window contributed
        # nothing visible, and one inside it reported an unknowable fraction of its scales.
        # Ranking stays; the truncation goes.
        for host, scales in sorted(out.items(),
                                   key=lambda kv: -sum(v["n"] for v in kv[1].values())):
            tot = sum(v["n"] for v in scales.values())
            print(f"   {tot:>5}  {host:<34}{', '.join(sorted(scales))}")
        return 0

    if a.check:
        rosetta = json.load(open(OUT, encoding="utf-8"))
        path = os.path.join(HERE, "data", "ASSAYS.json")
        if not os.path.exists(path):
            print("no ASSAYS.json yet — mine the scales first, assay second, check third")
            return 0
        # The decimal is taken AS FILED. This read used to be
        # `v["result"]["decimal"] + P.__dict__.get("_x", 0)`, an undocumented offset pulled off
        # the `pipeline` module by name at runtime. `pipeline` defines no `_x` anywhere, so the
        # term was always 0 and the line was inert -- but it was inert by accident, not by
        # design: a `pipeline._x = 0.3` set from a debugging shell, or a future module-level
        # name collision, would have shifted EVERY assay decimal feeding the correlation check
        # by that amount with no error, no log line and nothing in the printed rho report to
        # say the numbers had moved. A calibration check that can be silently detuned by an
        # attribute nobody declared is not a check. Removed; the arithmetic is unchanged. (run33)
        assays = {k: v["result"]["decimal"]
                  for k, v in json.load(open(path, encoding="utf-8")).items()
                  if v.get("result") and v["result"].get("decimal") is not None}
        # HOST-SCOPED, off ASSAYS.json's own `host|Name` keys (order 0bba50a6d76b): a scale row
        # can only be vouched for by an assay recorded on that same wiki. This is also what
        # makes the check match anything at all -- see check()'s docstring on the bare-name
        # lookup that scored 0 overlap on all eight standing scales.
        by_host, collisions = assays_by_host(assays)
        print(f"  (matching scoped per wiki: {len(by_host)} host(s) hold an assayed decimal)")
        if collisions:
            print(f"  ({len(collisions)} assay name(s) collide after normalising, last read "
                  f"wins for each: {', '.join(collisions)})")
        rows = check(rosetta, assays, by_host=by_host)
        bad, unscored = [], []
        for r in rows:
            if r["rho"] is None:
                # SAID OUT LOUD RATHER THAN OMITTED. Fewer than four overlapping names means the
                # scale could not be ranked at all, which is a different thing from agreeing.
                unscored.append(r)
                print(f"  rho     --  n={r['overlap']:>4}  {r['scale'][:38]:<40}"
                      f"{r['kind']}  UNSCORED (needs 4 overlapping names)"
                      f"{'  [%d row(s) carry no assay from this wiki]' % r['unmatched'] if r['unmatched'] else ''}")
                continue
            disagrees = r["rho"] < 0.3
            if disagrees:
                bad.append(r)
            print(f"  rho {r['rho']:>6}  n={r['overlap']:>4}  {r['scale'][:38]:<40}"
                  f"{r['kind']}{'  DISAGREES' if disagrees else ''}")
        if unscored:
            print(f"\n{len(unscored)} of {len(rows)} scale(s) could NOT be scored (fewer than "
                  f"four names overlap the Assay). That is not agreement; it is no measurement.")
        # THE EXIT CODE HAS TO CARRY THE VERDICT, not just the printout. This used to
        # `return 0` unconditionally, so nothing that gates on rc (a shell, allsweep's
        # VERIFIERS, a scheduler) could ever learn a franchise's own published ordering
        # disagreed with our Assay -- the one check this module exists for. Same contract
        # `silence.py` and `audit.py` already use: 0 clean, 1 findings, so a caller can gate on
        # it. 2026-08-26, batch 3.
        if bad:
            print(f"\n{len(bad)} of {len(rows)} scale(s) DISAGREE (rho < 0.3) -- our Assay "
                  f"orders these characters against what the fiction itself publishes.")
            return 1
        return 0

    ap.print_help()
    return 0


if __name__ == "__main__":
    sys.exit(main())
