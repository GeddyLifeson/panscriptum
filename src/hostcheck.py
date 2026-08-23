#!/usr/bin/env python3
"""
HOSTCHECK — does this wiki hold THIS fiction, or merely answer to the name?

THE FAULT
---------
A source's wiki is guessed from its title: `Descent into Avernus` -> `descent.fandom.com`. The
guess is checked for whether the host EXISTS, and every one of these existed:

    Descent into Avernus      -> descent.fandom.com        the board game Descent
    Odyssey of the Dragonlords-> arcanum.fandom.com        the CRPG Arcanum
    Unearthed Arcana          -> unearthed.fandom.com      an Egyptology wiki
    The Elements Beyond       -> elements.fandom.com       the periodic table
    Clockwork Angels (Rush)   -> clockwork.fandom.com      three pages, none of them Rush
    Guildmasters' Guide       -> guildmasters.fandom.com   one campaign's room list

Each returned HTTP 200, a valid MediaWiki API, and real article titles. Then every entity was
looked up, none was found, and 2,765 pages of the wrong fiction were filed as an honest absence.
Existence was never the question. The question is whether the wiki holds the fiction, and no
part of the pipeline was asking it.

THE TEST
--------
Ask the wiki about the source's OWN CATALOGUED NAMES. A wiki that holds a fiction has articles
for that fiction's characters; a wiki that merely shares a slug has none of them. One batched
`action=query&titles=...` call answers for fifty names at once, which makes this cheap enough to
run over every host on the roll rather than only the suspicious ones.

    hit rate >= GOOD    the host holds the fiction
    hit rate <= DEAD    the host answers to the name and holds something else
    in between          a partial match, usually a wiki that covers part of a franchise

The threshold matters less than the shape of the result. A right host scores 0.6 and up; a wrong
host scores almost exactly zero, because two unrelated fictions share no proper nouns. There is
no ambiguous middle in practice, which is why this test is worth trusting.

WHY NOT JUST FIX THE SIX
------------------------
Because the list of hand-written host overrides is itself the defect: it was written after the
first six wrong hosts were found by hand, and it will be wrong again for the next source added
to the roll. A measurement runs on every host every time and needs nobody to remember anything.
"""
import argparse
import collections
import glob
import json
import os
import re
import sys
import threading
import urllib.parse
import urllib.request

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import silence                                                          # noqa: E402

_BAD_CHARS = (chr(8), chr(11), chr(12), chr(7))
if any(c in open(os.path.abspath(__file__), encoding="utf-8").read() for c in _BAD_CHARS):
    raise SystemExit(__file__ + ": a regex escape was eaten in transit.")

OUT = os.path.join(HERE, "data", "HOST_FITNESS.json")
UNFIT = os.path.join(HERE, "data", "HOST_UNFIT.json")

GOOD = 0.35        # at or above: the host holds the fiction
DEAD = 0.05        # at or below: the host is about something else entirely
PROBE = 40         # names per host. One API call takes 50; forty leaves room for redirects.
ABOUT = 0.40       # of the articles that exist, this fraction must actually be about the source
MIN_PROBE = 5      # under five names, a hit rate is noise -- 1/2 reads as 50% and means nothing
# LIFT thresholds, in points above the host's own baseline for foreign names.
LIFT_MIN = 0.05    # at or below this, the result is what the host gives anyone
GOOD_LIFT = 0.25   # at or above this, the host holds the fiction
# Read the pages only on hosts generous enough that holding names proves nothing.
ABOUT_VETO_ABOVE = 0.25


def _api(host):
    import endpoint as EP
    return EP.api_url(host)


def _get(url, timeout=25, host=None):
    """One API call, PACED PER HOST.

    This function was hammering every wiki as fast as the thread pool allowed, and Wikimedia is
    far stricter than Fandom about it. Six workers times eighteen candidates produced 1,364
    swallowed HTTPErrors in a single adoption pass -- and because an unreachable host reads as a
    host that answered nothing, every pantheon and astrology source came back "no wiki holds
    this fiction" when the truth was "we were being throttled".

    `feats._throttle` already implements exactly the right thing, with Wikipedia paced far slower
    than the rest. Not using it here was the whole bug; the fix is one call.
    """
    import feats as F
    if host is None:
        m = re.match(r"https?://([^/]+)/", url)
        host = m.group(1) if m else ""
    if host:
        F._throttle(host)
    req = urllib.request.Request(url, headers={"User-Agent": F.UA})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read().decode("utf-8", "replace"))


def probe(host, names):
    """Fraction of these names that exist as articles on this host.

    Batched: MediaWiki takes fifty titles per query and answers for all of them, so a host costs
    one round trip rather than fifty. Redirects count as hits -- a redirect means the wiki knows
    the name, which is the thing being tested.
    """
    names = [n for n in names if n and len(n) > 1][:PROBE]
    if not names:
        return None
    # A RAW-ONLY HOST ANSWERS TITLE-BY-TITLE. There is no batched query to ask, so existence is
    # tested by fetching. Slower, and the only way to judge a wiki that closed its API at all.
    import endpoint as EP
    if EP.detect(host)["mode"] == EP.MODE_RAW:
        got = EP.fetch_raw(host, names[:12])
        n = min(len(names), 12)
        return {"host": host, "probed": n, "hits": len(got),
                "rate": round(len(got) / n, 3), "examples": sorted(got)[:5],
                "titles": sorted(got)}
    if not _api(host):
        return {"host": host, "probed": len(names), "hits": 0, "rate": None,
                "error": "no usable endpoint"}
    q = urllib.parse.urlencode({
        "action": "query", "format": "json", "redirects": "1",
        "titles": "|".join(n.replace("|", " ") for n in names)})
    try:
        d = _get(f"{_api(host)}?{q}")
    except Exception as e:
        silence.note("hostcheck.py:probe")
        # NOT a rate of zero. A request that failed is not a wiki that holds nothing, and
        # conflating them is precisely the defect this file exists to catch -- committed here, by
        # the tool built to catch it. Seventy-four throttled probes came back as 0% and the repair
        # pass unassigned `warhammer40k.fandom.com` from Warhammer 40,000.
        return {"host": host, "probed": len(names), "hits": 0, "rate": None,
                "error": f"{type(e).__name__} {str(e)[:60]}"}
    pages = ((d.get("query") or {}).get("pages") or {})
    live = [p for p in pages.values() if "missing" not in p and int(p.get("pageid", 0)) > 0]
    found = [p.get("title") for p in live][:5]
    return {"host": host, "probed": len(names), "hits": len(live),
            "rate": round(len(live) / len(names), 3), "examples": found,
            "titles": [p.get("title") for p in live]}


# Words that name a CATEGORY rather than a fiction. A source called "all Pixar films" is
# identified by "Pixar"; testing articles for "films" asks whether Pixar's wiki discusses
# cinema, which is both true and useless. Every entry here was observed producing a false
# rejection.
_STOP = {"the", "of", "and", "a", "an", "all", "in", "to", "incl", "s", "guide", "from",
         "film", "films", "movie", "movies", "series", "game", "games", "book", "books",
         "novel", "novels", "show", "shows", "edition", "content", "associated", "its",
         "handbook", "manual", "centuries", "century", "world", "worlds", "adventures"}


def _tokens(source):
    """The words in a source name that would identify it inside an article.

    Letters required. `Warhammer 40,000` on `warhammer40k.fandom.com` struck out "warhammer" as
    already-in-the-domain and was left testing articles for the string "000", which appears in
    none of them -- so a wiki holding 95% of its own roster was judged to be about another
    fiction. A bare number identifies nothing.
    """
    raw = re.split(r"[^A-Za-z0-9']+", source)
    return [w.lower() for w in raw
            if len(w) > 2 and any(c.isalpha() for c in w) and w.lower() not in _STOP]


def relevance(host, titles, source, sample=12):
    """Of the articles that DO exist here, how many are about this fiction?

    Existence is not aboutness, and on a general encyclopedia the difference is everything.
    `Rocket League` scored 72% on Wikipedia because its entities are ordinary words that have
    Wikipedia articles -- about ordinary things. Every one of those "hits" was a page on some
    unrelated subject, and taken as a host score it would have pointed the miner at nonsense
    with a number that looked healthy.

    So the hits are opened and read for the source's own distinctive words. A page about Wano
    mentions One Piece; a page about a rocket does not mention Rocket League.
    """
    titles = [t for t in titles if t][:sample]
    toks = _tokens(source)
    if not titles or not toks:
        return None

    # A token already spelled into the host's own domain proves nothing when found in its
    # articles. `lost.fandom.com` scored a perfect 100% aboutness for "Lost Mines of Phandelver"
    # because every article on the television wiki says "Lost", and the entity names it matched
    # were ordinary words. Strip those tokens and judge on what remains.
    dom = host.lower().replace(".", "").replace("-", "")
    rest = [t for t in toks if t not in dom]
    if not rest:
        # Every distinctive word in the source name is in the domain: this wiki is NAMED after
        # the fiction. `metro.fandom.com` for Metro, `bindingofisaac.fandom.com` for The Binding
        # of Isaac. That is stronger evidence than any article body could give, so the aboutness
        # test has nothing left to add.
        return 1.0
    # The longest words are the distinctive ones. "war" and "world" appear everywhere;
    # "warships" and "phandelver" appear where the fiction does.
    toks = sorted(rest, key=len, reverse=True)[:3]
    bodies = _bodies(host, titles)
    if not bodies:
        return None
    about = sum(1 for b in bodies if any(t in b for t in toks))
    return round(about / len(bodies), 3)


def _bodies(host, titles):
    """Lowercased article text for these titles. Raw wikitext, on every wiki, always.

    `prop=extracts` was the obvious choice and it is unusable here for two separate reasons, each
    of which silently returned a wrong answer rather than an error:

      it is the TextExtracts extension, which Wikipedia has and most Fandom wikis do not, so the
      request succeeds and returns nothing -- which read as "no text" and made the aboutness test
      quietly unavailable across the entire Fandom half of the roll;

      and `exlimit` is capped at ONE unless `exintro` is also set. Twelve titles came back with a
      single extract, so aboutness was computed over one article and reported as a rate.
      Polynesian myth scored 98% held and 0% about that way.

    `prop=revisions` needs no extension, has no such limit, and returns the whole article rather
    than its opening line -- which is what the test actually wants, since an article is about its
    subject throughout and not only in its first sentence.
    """
    import endpoint as EP
    if EP.detect(host)["mode"] == EP.MODE_RAW:
        return [b[:8000].lower() for b in EP.fetch_raw(host, list(titles)[:8]).values()]
    joined = "|".join(t.replace("|", " ") for t in titles)
    out = []
    try:
        d = _get(f"{_api(host)}?" + urllib.parse.urlencode({
            "action": "query", "format": "json", "prop": "revisions",
            "rvprop": "content", "rvslots": "main", "titles": joined}))
        for p in ((d.get("query") or {}).get("pages") or {}).values():
            for rev in (p.get("revisions") or []):
                slot = ((rev.get("slots") or {}).get("main") or {})
                body = slot.get("*") or rev.get("*") or ""
                if body:
                    out.append(body[:8000].lower())
    except Exception:
        silence.note("hostcheck.py:relevance-wikitext")
    return out


# --------------------------------------------------------------------------- candidates

def candidates(source, current, by=None, hosts=None):
    """Other hosts worth probing for this source, best first.

    Fandom's CrossWiki search API used to answer this. It returns 404 now, and it had been
    returning 404 on every call -- 124 of them -- while this function swallowed the error and
    fell through to slug guessing, looking for all the world like it was still searching.

    Three generators replace it, all built from evidence already on hand and none of them a
    maintained list:

    TOKENS. Each proper noun in the source name, each adjacent pair, and each with Fandom's own
    disambiguation suffixes. That last part matters more than it sounds: when a name is taken,
    a wiki takes the name plus a category word and the bare name goes to whoever got there
    first. `metro.fandom.com` is the New York City Subway; the game is
    `metrovideogame.fandom.com`. Without the suffixes the search proposes the squatter, measures
    0%, and concludes the fiction has no wiki at all -- which is how 303 Metro entries were
    permanently uncitable.

    NEIGHBOURS. Any source whose catalogued roster substantially overlaps this one's is about the
    same world, so its host is a candidate. This is what found
    `Explorer's Guide to Wildemount -> criticalrole.fandom.com` at 90%: Wildemount IS Critical
    Role's setting, and no string manipulation on the title would ever have reached it.

    WIKIPEDIA, last. It answers for almost anything, which is exactly why it must rank below
    wikis that are about one thing; the aboutness test is what stops it winning on names alone.
    """
    import feats as F
    # TWO LISTS, BECAUSE ONLY ONE OF THEM MAY BE TRUNCATED.
    #
    # The suffix variants are SPECULATIVE -- ten guesses per token, most of which 404 -- and
    # capping them is right. The grounded candidates are not guesses: a neighbour's host is
    # evidence, and Wikipedia is the universal fallback. Mixing them into one list and slicing
    # it put `en.wikipedia.org` at position nineteen of a list cut at eighteen, so every
    # pantheon and astrology source was reported as having no wiki while scoring `holds` on a
    # host that was never probed.
    #
    # That is Hard Rule 0 in miniature: ranking is fine, ranking then TRUNCATING is not, and the
    # truncation does not fail -- it returns a smaller universe wearing the same shape.
    spec, grounded = [], []

    def add(h, speculative=False):
        if not h or h == current:
            return
        if h in spec or h in grounded:
            return
        (spec if speculative else grounded).append(h)

    # D&D Wiki holds the third-party and homebrew shelf, and nothing about the SOURCE NAMES
    # would ever propose it: "Mage Hand Press" yields magehandpress.fandom.com, not dandwiki.
    # It is the one host this project needs that no generator can derive, so it is named -- and
    # a named host that is probed like any other is a very different thing from a hardcoded
    # assignment.
    add("www.dandwiki.com")
    proper = [w for w in re.split(r"[^A-Za-z0-9']+", source)
              if len(w) > 2 and any(ch.isalpha() for ch in w)
              and w.lower() not in _STOP and w[:1].isupper()]
    clean = ["".join(ch for ch in w.lower() if ch.isalnum()) for w in proper]
    for a, b in zip(clean, clean[1:]):
        add(f"{a}{b}.fandom.com")
    for w in clean:
        if len(w) > 3:
            add(f"{w}.fandom.com")
    for w in clean:
        if len(w) > 3:
            for suffix in ("videogame", "game", "games", "series", "franchise", "wiki",
                           "official", "movie", "film", "tv"):
                add(f"{w}{suffix}.fandom.com", speculative=True)

    if by and hosts:
        mine = set(by.get(source) or ())
        if mine:
            near = []
            for other, names in by.items():
                if other == source or not hosts.get(other):
                    continue
                shared = len(mine & set(names))
                if shared >= max(3, 0.25 * len(mine)):
                    near.append((shared, hosts[other]))
            for _, h in sorted(near, reverse=True):
                add(h)

    for sl in F._slugs(source):
        add(sl if "." in sl else f"{sl}.fandom.com")

    # Universal hosts: places that hold SOMETHING about almost every fiction on the roll, and
    # which no amount of slug-guessing will ever produce. They are grounded by definition -- we
    # know they exist and we know they are readable -- so they lead. Whether any of them actually
    # holds THIS source is decided by score(), which measures lift over the host's own baseline
    # and is not fooled by a site that answers every name anybody asks about.
    for u in ("en.wikipedia.org",):
        add(u)

    # EVIDENCE FIRST, SPECULATION AFTER.
    #
    # This read `grounded[:1] + spec[:14] + grounded[1:]`, which put ONE known-real host at the
    # front and buried the rest behind fourteen guesses. Any caller taking a slice of the result
    # -- and callers do -- got one real host and a fistful of invented subdomains. On Bleach the
    # first eight entries were www.dandwiki.com followed by seven wikis that do not exist, while
    # en.wikipedia.org sat at position sixteen.
    #
    # The interleave was itself a repair for this exact bug in a smaller form. The repair was to
    # promote one grounded host. The fix is to promote all of them.
    return grounded + spec


# --------------------------------------------------------------------------- the sweep

def entities_by_source():
    """{source: [catalogued entity names]} — every name, no sampling of the roll itself."""
    path = os.path.join(HERE, "data", "CHARACTER_SWEEP.json")
    by = collections.defaultdict(list)
    try:
        with open(path, encoding="utf-8") as f:
            rows = json.load(f)
    except Exception:
        silence.note("hostcheck.py:entities_by_source")
        return by
    for r in rows:
        s, n = r.get("source"), r.get("name")
        if s and n:
            by[s].append(n)
    return by


_NULL_CACHE = {}
_NULL_LOCK = threading.Lock()


def null_rate(host, by=None, exclude=None, sample=40):
    """How often this host answers for names it has no reason to hold. The control.

    A hit rate means nothing without one. `Song of Syx` -- a colony sim -- scored 8% on D&D Wiki
    and was adopted, because eight percent looked like thin coverage. It is not coverage at all:
    its roster contains words like `Druidic` and `Scavenger`, and a D&D wiki has articles for
    those whatever fiction is asking.

    So the same host is asked about FOREIGN names, drawn from other sources' rosters, and that
    is the floor a real answer has to clear. It is the same idea as the permutation threshold
    `weave.py` already uses for entity resolution: measure what chance alone produces, then
    require the observed value to beat it.
    """
    with _NULL_LOCK:
        if host in _NULL_CACHE:
            return _NULL_CACHE[host]
    foreign = []
    for src, names in (by or {}).items():
        if src == exclude:
            continue
        foreign.extend(names[:3])
    # Deterministic, not random: the control must be reproducible, or two runs disagree about
    # the same host for reasons nobody can inspect.
    foreign = sorted(set(foreign))[::max(1, len(foreign) // sample)][:sample]
    r = probe(host, foreign) or {}
    rate = r.get("rate")
    rate = 0.0 if rate is None else rate
    with _NULL_LOCK:
        _NULL_CACHE[host] = rate
    return rate


def score(host, names, source, by=None):
    """One host, fully judged: how much of this roster it holds, ABOVE ITS OWN BASELINE.

    An absolute hit rate is meaningless on its own, because hosts differ enormously in how
    generous they are with names they have no reason to hold:

        en.wikipedia.org              answers  50% of FOREIGN names
        forgottenrealms.fandom.com    answers   8%
        dc.fandom.com                 answers   5%
        www.dandwiki.com              answers   0%

    Judged absolutely, 33% is a weak result. Against those baselines, 33% on D&D Wiki is
    thirty-three points of signal and 33% on Wikipedia is worse than chance. Both readings were
    made in this project and both were wrong: a homebrew shelf was rejected from the wiki that
    hosts it, and `Rocket League` was nearly adopted onto Wikipedia because its entities are
    ordinary words with ordinary articles.

    LIFT is the measurement -- observed minus baseline. It needs no per-host rule and no special
    case for encyclopedias, because the encyclopedia's generosity is the thing being subtracted.

    ABOUTNESS stays, as a veto, but only on generous hosts. Where a host answers for half of all
    names, holding a roster proves nothing and only reading the pages can separate coverage from
    coincidence. Where a host answers for almost none, the hits are already the evidence -- and
    demanding aboutness there rejects every SOURCEBOOK, whose title names a product rather than
    a world: a homebrew class page has no reason to say "Mage Hand Press". Wrong-fiction ROSTERS
    on specific hosts are caught by `--rosters`, which is the instrument built for them.
    """
    r = probe(host, names) or {"host": host, "probed": 0, "hits": 0, "rate": 0.0, "titles": []}
    r.setdefault("host", host)
    r.setdefault("rate", 0.0)
    r.setdefault("hits", 0)
    r.setdefault("probed", 0)
    r["source"] = source

    base = null_rate(host, by=by, exclude=source) if by else 0.0
    r["baseline"] = round(base, 3)
    rate = r.get("rate")
    r["lift"] = None if rate is None else round(rate - base, 3)

    r["about"] = (relevance(host, r.get("titles") or [], source)
                  if r["hits"] and base >= ABOUT_VETO_ABOVE else None)
    r.pop("titles", None)

    if rate is None:
        r["verdict"] = "UNREACHABLE — no judgement"
        r["rate"] = 0.0
    elif r["probed"] < MIN_PROBE:
        r["verdict"] = "too few names to judge"
    elif r["hits"] < 2 or r["lift"] <= LIFT_MIN:
        # Indistinguishable from what this host gives anybody who asks.
        r["verdict"] = "WRONG FICTION" if rate <= DEAD else "NAMES ONLY"
    elif r["about"] is not None and r["about"] < ABOUT:
        r["verdict"] = "NAMES ONLY"
    elif r["lift"] >= GOOD_LIFT:
        r["verdict"] = "holds"
    else:
        r["verdict"] = "partial"
    return r


def sweep(only=None, repair=False, workers=8):
    from concurrent.futures import ThreadPoolExecutor
    import feats as F
    hosts = json.load(open(F.HOSTS, encoding="utf-8"))
    by = entities_by_source()
    todo = [(s, h) for s, h in sorted(hosts.items())
            if by.get(s) and h and (not only or only.lower() in s.lower())]
    unassigned = sorted(s for s, h in hosts.items()
                        if by.get(s) and not h and (not only or only.lower() in s.lower()))
    if unassigned:
        # A source with no host is not a failure to report as zero -- it is a source nobody has
        # found a wiki for yet, which is a different fact and needs a different remedy.
        print(f"  ({len(unassigned)} sources carry no host at all and are not probed)")

    results = {}

    def one(item):
        src, host = item
        return score(host, by[src], src, by=by)

    with ThreadPoolExecutor(max_workers=workers) as ex:
        for r in ex.map(one, todo):
            results[r["source"]] = r
            flag = "" if r["verdict"] == "holds" else f"   <-- {r['verdict']}"
            lift = "    -" if r.get("lift") is None else f"{r['lift']:>+5.0%}"
            print(f"  {r['rate']:>5.0%} held {lift} lift  {r['hits']:>3}/{r['probed']:<3} "
                  f"{r['host']:<34}{r['source'][:34]}{flag}", flush=True)

    # A host that could not be reached is not a host that failed. Only verdicts reflecting an
    # ANSWER from the wiki are eligible for repair; anything else is retried another day.
    JUDGED = ("WRONG FICTION", "NAMES ONLY", "partial")
    wrong = [r for r in results.values() if r["verdict"] in JUDGED]
    unreachable = [r for r in results.values() if r["verdict"].startswith("UNREACHABLE")]
    if unreachable:
        print("  " + str(len(unreachable))
              + " host(s) did not answer and were left exactly as they are")
    print(f"\n{len(results)} hosts probed, {len(wrong)} do not hold their fiction")

    if repair and wrong:
        print("\nSEARCHING FOR REPLACEMENTS")
        fixed = {}
        for r in sorted(wrong, key=lambda x: x["rate"]):
            src = r["source"]
            # The rejected host is NOT the bar to beat. Seeding `best` with its own hit rate
            # meant a host judged NAMES ONLY at 95% could not be replaced by a host that
            # genuinely holds the fiction at 45%, and the source was unassigned instead --
            # Gundam lost `en.wikipedia.org` at 45% held and 100% about that way.
            best = (0.0, None)
            judged_any = False
            for h in candidates(src, r["host"], by=by, hosts=hosts):
                p = score(h, by[src], src, by=by)
                ok = p["verdict"] in ("holds", "partial")
                judged_any = judged_any or not p["verdict"].startswith("UNREACHABLE")
                if ok and p["rate"] is not None and p["rate"] > best[0]:
                    best = (p["rate"], h)
                ab = "   -" if p.get("about") is None else f"{p['about']:>4.0%}"
                print(f"    {p['rate']:>5.0%} held  {ab} about  {h:<34}"
                      f"{p['verdict'] if not ok else ''}", flush=True)
                if best[0] >= GOOD:
                    break
            if best[1] and best[1] != r["host"] and best[0] > DEAD:
                fixed[src] = best[1]
                print(f"  -> {src}: {r['host']} => {best[1]} ({best[0]:.0%})")
            elif not judged_any:
                # Every alternative was unreachable. That is a fact about the network this
                # afternoon, not about the omniverse, and it must not cost the source its host.
                print(f"  -> {src}: no candidate answered; keeping {r['host']} for now")
            elif r["verdict"] == "partial":
                # A partial host is the best evidence available and stays. Dropping it would
                # trade a thin source for no source, and thin is not the same as wrong -- these
                # are usually catalogues whose entity names are items rather than articles.
                print(f"  -> {src}: nothing better; keeping {r['host']} ({r['rate']:.0%})")
            else:
                # No wiki on Fandom or Wikipedia holds this fiction. That is a real finding and
                # the entry stays unassigned rather than being pointed at something plausible.
                print(f"  -> {src}: no host holds this fiction; left unassigned")
                fixed[src] = None
        if fixed:
            # A rejected host is a FINDING and is written down. Dropping the source from the map
            # and saying nothing would leave a gap indistinguishable from a source nobody has
            # got to yet, which is the confusion this whole file exists to end.
            unfit = {}
            if os.path.exists(UNFIT):
                try:
                    with open(UNFIT, encoding="utf-8") as f:
                        unfit = json.load(f)
                except Exception:
                    silence.note("hostcheck.py:unfit")
            hosts.update({k: v for k, v in fixed.items() if v})
            for k, v in fixed.items():
                if v is None:
                    unfit[k] = {"rejected": hosts.get(k),
                                "verdict": results[k]["verdict"],
                                "held": results[k]["rate"],
                                "about": results[k].get("about")}
                    hosts.pop(k, None)
            with open(F.HOSTS, "w", encoding="utf-8") as f:
                json.dump(hosts, f, indent=1, sort_keys=True)
            with open(UNFIT, "w", encoding="utf-8") as f:
                json.dump(unfit, f, indent=1, sort_keys=True)
            print(f"\nWIKI_HOSTS.json updated: {sum(1 for v in fixed.values() if v)} "
                  f"repointed, {sum(1 for v in fixed.values() if not v)} recorded unfit")
            print(f"-> {UNFIT}   (every rejection kept, so a gap reads as a gap)")

    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=1, sort_keys=True)
    print(f"-> {OUT}")
    return results


# Titles that name a BOOK rather than a world. The roster test asks whether mined pages mention
# the source; for these the answer is always no and means nothing, because the pages are about
# the material and the title is about the product it shipped in.
PRODUCT_WORDS = ("handbook", "guide to", "arcana", "compendium", "manual", "tome of",
                 "primer", "almanac", "sourcebook", "dms guild", "screenplay")

ROSTERS = os.path.join(HERE, "data", "ROSTER_AUDIT.json")
PURGED = os.path.join(HERE, "data", "ROSTER_PURGES.json")


def purge(dry=True, only=None):
    """Remove rosters catalogued from a wiki that has since been judged the wrong fiction.

    WHAT THE AUDIT ACTUALLY MEASURES, AND WHY THAT NEEDS SAYING.
    ------------------------------------------------------------
    `roster_audit` asks whether the PAGES mined for a source name that source. A "no" proves the
    HOST was wrong. It does not prove the ROSTER was, and the difference nearly cost 1,119
    correct entries:

        Lost Mines of Phandelver -> lost.fandom.com       roster IS the cast of the TV series
        Unearthed Arcana -> unearthed.fandom.com          roster IS genuine D&D -- Changeling,
                                                          Shifter, Beasthide Shifter, Eberron
                                                          content. Only the wiki was wrong.

    Both fail the audit identically, because an Egyptology wiki's articles never say "arcana"
    either. And no threshold separates them: a sourcebook's title names a PRODUCT, not a world,
    so "does this page say Unearthed Arcana" is simply the wrong question for it.

    So this no longer acts on the audit alone. It purges the sources it is TOLD to purge, after
    somebody has read the roster and seen another fiction in it -- ten seconds of reading, and
    the only evidence that actually distinguishes the two cases. The audit shortlists; the
    reading decides.
    

    Correcting the host map does not correct what the wrong host already wrote. `Lost Mines of
    Phandelver` still carries 262 entries and they are the cast of the television series Lost;
    every one of them would be assayed, shelfmarked and written into a volume about a D&D
    adventure. Leaving them in would put fabrications in the library under the exact appearance
    of research, which is worse than the gap they would leave.

    The rule is deliberately narrow, because deleting catalogue data on a heuristic is its own
    way to lose a world:

      the roster must never name its own fiction (the audit's finding), AND
      the host that mined it must no longer be this source's host -- either repointed by
      hostcheck or recorded unfit.

    Both together mean an independent measurement already rejected that wiki for this source.
    A roster that merely reads oddly, or one mined from a host still considered correct, is
    reported and kept. Every purge is written to ROSTER_PURGES.json with what was removed, so
    the gap it leaves is a recorded finding rather than a silence.
    """
    import feats as F
    import weave_index as WI
    hosts = json.load(open(F.HOSTS, encoding="utf-8"))
    try:
        with open(ROSTERS, encoding="utf-8") as f:
            audit = json.load(f)
    except Exception:
        print("no roster audit on disk -- run --rosters first")
        return []
    unfit = {}
    if os.path.exists(UNFIT):
        try:
            with open(UNFIT, encoding="utf-8") as f:
                unfit = json.load(f)
        except Exception:
            silence.note("hostcheck.py:purge-unfit")

    if not only:
        print("  --source is required: the audit shortlists, a person decides.")
        print("  Pass --source NAME (repeatable) to purge exactly those.")
        print("")
        print("  shortlist -- the pages mined for these sources never name them, which means")
        print("  the HOST was wrong. Read each roster before concluding the ENTRIES are:")
        for src, r in sorted(audit.items(), key=lambda kv: kv[1]["rate"]):
            if r["rate"] < 0.10:
                print(f"     {r['rate']:>4.0%}  {src}  <- {r['host']}")
        return []

    targets = []
    for src in only:
        r = audit.get(src)
        if not r:
            print(f"  no audit row for {src!r}; run --rosters first")
            continue
        targets.append((src, r["host"], hosts.get(src)))
    if not targets:
        print("nothing to purge")
        return []

    log = {}
    for src, mined, now in targets:
        n_entries = n_files = 0
        # The catalogue records live as files; load_records() hands back their contents without
        # their paths, so the purge reads the directory itself and writes each record back in
        # place. The entries are cleared and the removal is stamped INTO the record, so a later
        # reader finds "262 entries removed, mined from lost.fandom.com" rather than a source
        # that looks like it was never catalogued.
        for fp in sorted(glob.glob(os.path.join(WI.RECORDS, "*.json"))):
            try:
                with open(fp, encoding="utf-8") as f:
                    r = json.load(f)
            except Exception:
                silence.note("hostcheck.py:purge-record")
                continue
            if r.get("source") != src:
                continue
            n_entries = len(r.get("entries") or [])
            if not dry:
                r["entries"] = []
                r["purged_roster"] = {"mined_from": mined, "reason": "wrong fiction",
                                      "removed": n_entries}
                with open(fp, "w", encoding="utf-8") as f:
                    json.dump(r, f, indent=1, ensure_ascii=False)
        # the caches those entries wrote
        for base in ("feats", "readfeats"):
            d = os.path.join(HERE, "data", base, re.sub(r"[^A-Za-z0-9]+", "_", mined)[:40])
            if not os.path.isdir(d):
                continue
            for fp in glob.glob(os.path.join(d, "*.json")):
                n_files += 1
                if not dry:
                    os.remove(fp)
        log[src] = {"mined_from": mined, "now": now, "entries": n_entries, "files": n_files}
        verb = "would remove" if dry else "removed"
        print(f"  {verb}: {src}  <- {mined}   {n_entries} entries, {n_files} cache files")

    if not dry and log:
        prev = {}
        if os.path.exists(PURGED):
            try:
                with open(PURGED, encoding="utf-8") as f:
                    prev = json.load(f)
            except Exception:
                silence.note("hostcheck.py:purge-log")
        prev.update(log)
        with open(PURGED, "w", encoding="utf-8") as f:
            json.dump(prev, f, indent=1, sort_keys=True)
        print(f"-> {PURGED}")
    return log





def roster_audit(workers=8):
    """Is each source's CATALOGUED ROSTER actually from that source's fiction?

    Fixing the host map is not enough, because a wrong host does not only mine the wrong pages
    -- it writes the wrong ENTITIES into the catalogue, and they stay there after the host is
    corrected. `Lost Mines of Phandelver` carries 262 entries, and they are the cast of the
    television series Lost: Sawyer, Hurley, Benjamin Linus, John Locke. Nothing downstream can
    tell, because a roster of 262 plausible character names is exactly what a correct roster
    looks like.

    The test uses evidence already on disk. Take the source's distinctive words and look for
    them anywhere in the pages mined for its own entities. A roster from the right fiction is
    saturated with its own name -- Wano articles say One Piece constantly. A roster from the
    wrong one never says it at all: "phandelver" appears zero times in 106,000 characters about
    a plane crash.
    """
    from concurrent.futures import ThreadPoolExecutor
    import feats as F
    hosts = json.load(open(F.HOSTS, encoding="utf-8"))
    by = entities_by_source()
    # Where the pages actually ARE, which is not always where the map now points: repointing a
    # bad host does not move the cache it already wrote, and the poisoned roster lives with the
    # old one. Reading the sweep's own record of what was mined is the only way to find it.
    mined_host = {}
    try:
        with open(os.path.join(HERE, "data", "CHARACTER_SWEEP.json"), encoding="utf-8") as f:
            for r in json.load(f):
                if r.get("source") and r.get("host") and r.get("pages"):
                    mined_host.setdefault(r["source"], r["host"])
    except Exception:
        silence.note("hostcheck.py:mined_host")

    def one(src):
        # The distinctive words in a source name are its PROPER NOUNS, not its longest words.
        # Ranking by length asked whether Pixar's roster mentions "films" and whether Gundam's
        # mentions "centuries", and flagged both as foreign when they answered no. Capitalisation
        # separates `Pixar`, `Gundam`, `Wildemount` and `Phandelver` from `films`, `centuries`,
        # `handbook` and `guide` at no cost, the same test identity.py uses on continuities.
        host = mined_host.get(src) or hosts.get(src) or ""
        proper = [w for w in re.split(r"[^A-Za-z0-9']+", src)
                  if len(w) > 3 and w[:1].isupper() and w.lower() not in _STOP]
        toks = [w.lower() for w in proper
                if w.lower() not in host.lower().replace(".", "").replace("-", "")]
        toks = sorted(toks, key=len, reverse=True)[:3]
        if not toks or not host:
            # No proper noun survives, or no host: this source cannot be judged this way and is
            # reported as unjudged rather than accused. A sourcebook titled "Player's Handbook"
            # names no fiction of its own, so its roster cannot be checked against its title.
            return None
        seen = hit = 0
        for name in by[src]:
            fp = os.path.join(HERE, "data", "feats",
                              re.sub(r"[^A-Za-z0-9]+", "_", host)[:40],
                              re.sub(r"[^A-Za-z0-9]+", "_", name)[:80] + ".json")
            if not os.path.exists(fp):
                continue
            try:
                with open(fp, encoding="utf-8") as f:
                    d = json.load(f)
            except Exception:
                silence.note("hostcheck.py:roster_audit")
                continue
            body = " ".join((d.get("text") or {}).values()).lower()
            if not body:
                continue
            seen += 1
            if any(t in body for t in toks):
                hit += 1
        if seen < MIN_PROBE:
            return None
        if not by.get(src):
            # An empty roster has already been purged. It cannot fail a test about its contents,
            # and leaving the old verdict on file keeps a solved problem permanently red.
            return None
        return {"source": src, "host": host, "tokens": toks, "pages": seen,
                "naming_source": hit, "rate": round(hit / seen, 3),
                # A source whose title names a PRODUCT rather than a world cannot be judged this
                # way at all: a homebrew class page has no reason to say "Unearthed Arcana", and
                # a Player's Handbook spell does not mention the book it is printed in. Marked
                # so the finding reads as "not judgeable" rather than "foreign".
                # Judgeable needs a title that names a WORLD and a token distinctive enough to
                # find. `Extra Life` reduces to the single word "life" -- present in almost any
                # text and absent from plenty that is about it, so its verdict carries no
                # information either way. One four-letter common word is not evidence.
                "judgeable": (not any(w in src.lower() for w in PRODUCT_WORDS)
                              and (len(toks) > 1 or max((len(t) for t in toks), default=0) >= 6))}

    out = []
    with ThreadPoolExecutor(max_workers=workers) as ex:
        for r in ex.map(one, sorted(by)):
            if not r:
                continue
            out.append(r)
            mark = "" if r["rate"] >= 0.10 else "   <-- ROSTER FROM ANOTHER FICTION"
            print(f"  {r['rate']:>5.0%}  {r['naming_source']:>4}/{r['pages']:<5} "
                  f"{r['source'][:44]:<46}{mark}", flush=True)
    bad = [r for r in out if r["rate"] < 0.10]
    print(f"\n{len(out)} sources with enough mined text to judge; "
          f"{len(bad)} carry a roster that never names their own fiction")
    for r in sorted(bad, key=lambda x: x["rate"]):
        print(f"   {r['source']}  ({r['host']}, looked for {', '.join(r['tokens'])})")
    with open(ROSTERS, "w", encoding="utf-8") as f:
        json.dump({r["source"]: r for r in out}, f, indent=1, sort_keys=True)
    print(f"-> {ROSTERS}")
    return out


def adopt(dry=True, workers=4):
    """Find a host for every catalogued source that has none.

    `sweep()` only probes sources that ALREADY have a host, so a source with none is invisible to
    it -- and forty-six of them were, holding nine thousand entries between them. Every one of
    those entries is uncitable by construction: no host, no pages, no evidence, forever, and
    nothing in the pipeline was ever going to mention it.

    Some are genuinely hostless. One-author homebrew has no wiki and never will, and recording
    that is a real finding rather than a gap. Others lost their host to a throttled probe or an
    over-eager repair and simply need it back. The same three-test verdict decides, so nothing is
    adopted on a name match alone.
    """
    from concurrent.futures import ThreadPoolExecutor
    import feats as F
    import weave_index as WI
    hosts = json.load(open(F.HOSTS, encoding="utf-8"))
    recs = {r["source"]: r for r in WI.load_records()}
    by = {s: [e["name"] for e in recs[s]["entries"]] for s in recs}
    hostless = sorted(s for s in recs if not hosts.get(s))
    print("{} catalogued sources have no host, holding {:,} entries".format(
        len(hostless), sum(len(by[s]) for s in hostless)))
    print("")

    def one(src):
        best = (0.0, None, "")
        # The WHOLE candidate list, not its head. Wikipedia is deliberately ranked last -- it
        # answers for almost anything and must not win on names alone -- so a head-only scan
        # never reached it, and every pantheon and astrology source came back "no wiki" while
        # scoring `holds` on Wikipedia the moment it was actually probed. Ranking decides ORDER;
        # it must not decide membership.
        for h in candidates(src, None, by=by, hosts=hosts):
            r = score(h, by[src], src, by=by)
            # No encyclopedia special-case any more. `score` now measures LIFT above each
            # host's own baseline for foreign names, so Wikipedia's generosity is subtracted
            # rather than compensated for by a rule about its hostname. A hand-written exemption
            # is a list, and every list this project wrote was eventually wrong.
            ok = r["verdict"] in ("holds", "partial")
            if ok and r["lift"] is not None and r["lift"] > best[0]:
                best = (r["rate"], h, r["verdict"])
            if best[0] >= GOOD:
                break
        return src, best

    found = {}
    with ThreadPoolExecutor(max_workers=workers) as ex:
        for src, (rate, host, verdict) in ex.map(one, hostless):
            if host:
                found[src] = host
                print("   {:>+5.0%} lift  {:<9}{:<34}{}".format(rate, verdict, host, src[:40]),
                      flush=True)
            else:
                print("      -   none      {:<34}{}".format("", src[:40]), flush=True)

    print("")
    print("{} adopted, {} genuinely without a wiki".format(
        len(found), len(hostless) - len(found)))
    if found and not dry:
        hosts.update(found)
        with open(F.HOSTS, "w", encoding="utf-8") as f:
            json.dump(hosts, f, indent=1, sort_keys=True)
        print("-> " + F.HOSTS)
    return found


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--only", help="restrict to sources whose name contains this")
    ap.add_argument("--repair", action="store_true",
                    help="search for a better host for every failing source and rewrite the map")
    ap.add_argument("--purge", action="store_true",
                    help="remove rosters the audit rejected AND whose host was independently rejected")
    ap.add_argument("--go", action="store_true", help="with --purge, actually delete")
    ap.add_argument("--source", action="append",
                    help="with --purge: exact source name to purge (repeatable). Required")
    ap.add_argument("--adopt", action="store_true",
                    help="find a host for every catalogued source that has none")
    ap.add_argument("--rosters", action="store_true",
                    help="audit whether each source's catalogued entities are from its fiction")
    ap.add_argument("--workers", type=int, default=8)
    a = ap.parse_args()
    if a.adopt:
        print("=" * 92)
        print("ADOPT — sources with no host at all")
        print("=" * 92)
        adopt(dry=not a.go, workers=a.workers)
        return 0
    if a.purge:
        print("=" * 92)
        print("ROSTER PURGE — entries catalogued from the wrong fiction")
        print("=" * 92)
        purge(dry=not a.go, only=a.source)
        return 0
    if a.rosters:
        print("=" * 92)
        print("ROSTER AUDIT — is each source's catalogued cast actually from that source?")
        print("=" * 92)
        roster_audit(workers=a.workers)
        return 0
    print("=" * 92)
    print("HOST FITNESS — does each wiki hold the fiction it is assigned to?")
    print("=" * 92)
    sweep(only=a.only, repair=a.repair, workers=a.workers)
    return 0


if __name__ == "__main__":
    sys.exit(main())
