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

    lift >= GOOD_LIFT   the host holds the fiction
    lift <= LIFT_MIN    the host answers to the name and holds something else
    in between          a partial match, usually a wiki that covers part of a franchise

LIFT, NOT THE RAW RATE, and this paragraph used to say otherwise. The verdicts in `score()` have
been lift-based for some time; the SELECTION in `sweep(--repair)` was still comparing raw rates
until order e2f0b13c766f, and this text was the reading that made that look correct. The two
rate constants survive: `DEAD` separates "WRONG FICTION" from "NAMES ONLY" inside `score`, and
`GOOD` is now only the figure quoted in prose here. An absolute hit rate is not comparable
between hosts, which is the argument `score()`'s own docstring makes at length.

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
import itertools
import json
import os
import re
import sys
import threading
import time
import urllib.parse
import urllib.request

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import cachekey                                                         # noqa: E402
import silence                                                          # noqa: E402

_BAD_CHARS = (chr(8), chr(11), chr(12), chr(7))
if any(c in open(os.path.abspath(__file__), encoding="utf-8").read() for c in _BAD_CHARS):
    raise SystemExit(__file__ + ": a regex escape was eaten in transit.")

OUT = os.path.join(HERE, "data", "HOST_FITNESS.json")
UNFIT = os.path.join(HERE, "data", "HOST_UNFIT.json")


def _land(path, obj, sort_keys=True, ensure_ascii=True):
    """Write a shared artifact whole or not at all. -> True if it LANDED, False if refused.

    Every write in this module was a bare `open(path, "w")` + `json.dump`, which truncates the
    target BEFORE serialising and takes no account of the readers holding it open on their own
    clocks. WIKI_HOSTS.json is the one that matters most -- written from here, from `adopt()`,
    and from `scout.py`, and read by feats, read, completeness, ingest_doc and wiki_source --
    but the same reasoning covers the fitness, unfit, purge and roster artifacts.
    `silence.replace_retry` carries the Windows backoff: os.replace is DENIED while any reader
    holds the destination open, and a brief retry outwaits an honest reader.

    THE TEMP NAME MUST NOT BE SHARED (order 1f79b49a4df7, run #36). The hand-rolled
    `path + ".tmp"` is what `silence.write_json` exists to make unavailable to get wrong, and it
    is the shape `binding_health._land` and `suppressions._land` were both moved off earlier
    today. Two writers of the same target -- a targeted `--only` investigation racing the
    scheduled sweep, or `--adopt` racing `--repair`, which is the normal situation here and not
    an exotic one -- collide on the SCRATCH FILE ITSELF: both open `WIKI_HOSTS.json.tmp` for
    writing, the second truncates the first, and whichever renames second can land a half-written
    file over the target. `write_json` carries pid and thread in the temp name, so two writers
    cannot meet there.

    AND WIKI_HOSTS.json IS ONE OF THE TWO FILES CONFIRMED NOT RECONSTRUCTIBLE from anything else
    on disk, which is why this write and not another one was the filed order.

    THE VERDICT IS NOW RETURNED, because it was being discarded. `replace_retry` deliberately
    never raises on persistent denial ("the caller's write lands next round"), so a refused
    rename left `sweep(--repair)` and `adopt()` printing "WIKI_HOSTS.json updated" over a file
    that had not changed. `binding_health._land` and `suppressions._land` gate on this identical
    verdict for the identical reason."""
    return silence.write_json(path, obj, indent=1, sort_keys=sort_keys,
                              ensure_ascii=ensure_ascii)


HOST_MERGE_ATTEMPTS = 8


def _land_hosts(merge, label):
    """Fold `merge` into WIKI_HOSTS.json under a COMPARE-AND-SWAP. -> (landed, reason).

    `_land` above closes the TORN-FILE and shared-scratch-file hazards. It has nothing to say
    about STALENESS, which is a different fault with the same victim and the one that actually
    threatens this file. Both writers here are read-modify-writes across a long window: `adopt()`
    reads the whole host map, then probes every hostless source over eight threads -- minutes,
    often much longer -- and only then writes the map back. `scout.py` and `sweep(--repair)`
    write the same file on their own clocks. The loser lands a complete, consistent, atomic host
    map that predates every host the winner adopted, and nothing anywhere reports it. That is
    the m42 lost-update shape `silence.replace_if_unchanged` was written for, and on the one file
    this project cannot rebuild it is unrecoverable rather than merely expensive.

    `merge` is applied key-wise to a FRESH read on every attempt, so a refusal costs a re-read
    and not the pass's work: the other writer's hosts survive and ours are set beside them. A
    value of None means "remove this source's host", which is how `sweep(--repair)` records a
    host it has judged unfit.

    -> (False, why) after HOST_MERGE_ATTEMPTS refusals. The caller must report that; this is the
    file where a write that quietly did not happen is the whole hazard.
    """
    import feats as F
    if not merge:
        # A NO-OP MERGE MUST NOT WRITE. Re-landing an unchanged map is not free on this file: it
        # invalidates every other writer's in-flight digest, so a pass that earned real hosts is
        # made to retry against a write that changed nothing -- and on the one file this project
        # cannot rebuild, a write with no content behind it is pure exposure. Both callers guard
        # this already; the guard belongs here, where it cannot be forgotten by the third one.
        return True, "nothing to merge"
    last_why = "not attempted"
    for attempt in range(HOST_MERGE_ATTEMPTS):
        # Digest BEFORE the read: anything landing between the two then fails the swap rather
        # than passing on a copy that is already behind.
        digest = silence.digest_of(F.HOSTS)
        hosts = {}
        if os.path.exists(F.HOSTS):
            try:
                with open(F.HOSTS, encoding="utf-8") as f:
                    hosts = json.load(f)
            except Exception:
                # NEVER heal this one by starting empty. An empty host map reads downstream as
                # "no source has a wiki", which is how COMPLETENESS.json came to hold zero rows
                # on 2026-08-24, and the file cannot be rebuilt from anything else on disk.
                silence.note("hostcheck.py:hosts-unreadable")
                return False, ("WIKI_HOSTS.json could not be read, so it cannot be merged into "
                               "-- refusing to write. It is not reconstructible; fix the file.")
        if not isinstance(hosts, dict):
            silence.note("hostcheck.py:hosts-nondict")
            return False, "WIKI_HOSTS.json is not an object; refusing to overwrite it"
        for k, v in merge.items():
            if v is None:
                hosts.pop(k, None)
            else:
                hosts[k] = v
        tmp = "%s.%d.%d.tmp" % (F.HOSTS, os.getpid(), threading.get_ident())
        try:
            with open(tmp, "w", encoding="utf-8") as f:
                json.dump(hosts, f, indent=1, sort_keys=True)
        except Exception:
            _unlink(tmp)
            raise
        landed, why = silence.replace_if_unchanged(tmp, F.HOSTS, digest)
        if landed:
            return True, "landed"
        last_why = why
        # `replace_if_unchanged` leaves the temp file where it is on a refusal, and litter beside
        # a shared state file is its own small fault.
        _unlink(tmp)
        time.sleep(0.05 * (attempt + 1))
    silence.note("hostcheck.py:hosts-contended")
    print("hostcheck: WIKI_HOSTS.json changed under %s on all %d attempts; %d change(s) were NOT "
          "recorded: %s" % (label, HOST_MERGE_ATTEMPTS, len(merge), last_why), file=sys.stderr)
    return False, last_why


def _unlink(path):
    try:
        os.remove(path)
    except FileNotFoundError:
        pass
    except Exception:
        silence.note("hostcheck.py:tmp-cleanup")


GOOD = 0.35        # at or above: the host holds the fiction
DEAD = 0.05        # at or below: the host is about something else entirely
PROBE = 40         # names per host. One API call takes 50; forty leaves room for redirects.
ABOUT = 0.40       # of the articles that exist, this fraction must actually be about the source
MIN_PROBE = 5      # under five names, a hit rate is noise -- 1/2 reads as 50% and means nothing
# THE SAME ARGUMENT, APPLIED TO THE OTHER HALF OF THE JUDGEMENT (order 44ae72489678). `ABOUT` is
# a rate over the article bodies that came back readable, and until now nothing put a floor under
# that denominator -- so the reasoning one line up, which the roster rate has enforced since it
# was written, was never applied to the rate that VETOES. `_bodies`' own docstring records what
# that costs: "Twelve titles came back with a single extract, so aboutness was computed over one
# article and reported as a rate. Polynesian myth scored 98% held and 0% about that way." The
# prop=revisions fix removed that particular CAUSE; it did not stop a generous host returning two
# readable bodies and a two-article rate deciding NAMES ONLY, which in the repair pass repoints
# or unassigns a wiki.
#
# THREE, NOT MIN_PROBE'S FIVE, and the difference is deliberate. A floor is an opinion, and this
# is the smallest one that covers exactly the shape argued above -- n of 1 (the recorded defect)
# and n of 2 (the thinnest case still reachable, since `hits >= 2` is tested first). Five would
# be the stronger reading and would also bite the RAW path hard, which samples at most eight
# bodies. Raising it is one constant and the owner's call.
ABOUT_MIN = 3      # article bodies. Under this, an aboutness rate is not a measurement
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
    """Of the articles that DO exist here, how many are about this fiction? -> (rate, n).

    THE DENOMINATOR TRAVELS WITH THE RATE, and it did not before (order 44ae72489678). This
    returned a bare rounded rate, `score` stored it as `r["about"]` and then dropped the titles,
    so `data/HOST_FITNESS.json` published an aboutness rate with NO sample size -- and the two
    paths into `_bodies` do not even use the same one: the API path samples up to twelve titles
    (`sample=12`, below) and the RAW path up to eight (`EP.fetch_raw(host, list(titles)[:8])`).
    Two rows could carry `about: 0.5` off different n with nothing on file saying which was one
    of two and which was six of twelve. `n` is None only for the domain-named short-circuit
    below, where the evidence is the host's own name and no sample was taken at all.

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
        return None, 0

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
        # n is None, not 0: no sample was taken, and 0 would read as an empty one.
        return 1.0, None
    # The longest words are the distinctive ones. "war" and "world" appear everywhere;
    # "warships" and "phandelver" appear where the fiction does.
    toks = sorted(rest, key=len, reverse=True)[:3]
    bodies = _bodies(host, titles)
    if not bodies:
        return None, 0
    about = sum(1 for b in bodies if any(t in b for t in toks))
    return round(about / len(bodies), 3), len(bodies)


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

def candidates_split(source, current, by=None, hosts=None):
    """-> (grounded, speculative). The two halves apart, for a caller that must bound one.

    `candidates()` below is the ordinary entry point and returns `grounded + spec`; this exists
    because a caller taking `cands[:n]` off that concatenation has NO WAY TO KNOW WHERE THE
    BOUNDARY IS, so its bound can silently eat evidence the moment the grounded prefix grows
    past n. `hosts.discover` was doing exactly that with n=24, and the comment above its slice
    asserted an invariant nothing enforced. Returning the boundary makes the guarantee the
    caller's to keep rather than the caller's to assume. (order 0b43bb663c36)

    Everything below documents how the two lists are built.

    Other hosts worth probing for this source, best first.

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
    for a, b in itertools.pairwise(clean):
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
    return grounded, spec


def candidates(source, current, by=None, hosts=None):
    """Other hosts worth probing for this source, best first: grounded, then speculation.

    Unchanged for every caller: the same flat `grounded + spec` list it has always returned.
    A CALLER THAT MEANS TO BOUND THE TAIL MUST USE `candidates_split` INSTEAD -- see its
    docstring -- because a slice taken off this concatenation cannot tell where the evidence
    ends and the guessing begins, and that is how `en.wikipedia.org` was lost at position
    nineteen of a list cut at eighteen. (order 0b43bb663c36)
    """
    grounded, spec = candidates_split(source, current, by=by, hosts=hosts)
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

    RETURNS None WHEN THE CONTROL COULD NOT BE MEASURED -- a failed or throttled probe, a host
    with no usable endpoint, or no foreign names to draw a sample from. None is not zero, and
    callers must not default it to zero; see the comment at the bottom of this function.

    A hit rate means nothing without one. `Song of Syx` -- a colony sim -- scored 8% on D&D Wiki
    and was adopted, because eight percent looked like thin coverage. It is not coverage at all:
    its roster contains words like `Druidic` and `Scavenger`, and a D&D wiki has articles for
    those whatever fiction is asking.

    So the same host is asked about FOREIGN names, drawn from other sources' rosters, and that
    is the floor a real answer has to clear. It is the same idea as the permutation threshold
    `weave.py` already uses for entity resolution: measure what chance alone produces, then
    require the observed value to beat it.
    """
    # KEYED BY THE WHOLE QUESTION, NOT JUST THE HOST (order 6657938d1890). `exclude` decides
    # which rosters the foreign sample is drawn FROM and `sample` decides how many names it
    # holds, so two callers asking about the same host with different arguments are asking
    # different questions -- and a host-only key answered the second one with the first one's
    # number. The control is the whole point of this function: a baseline measured against the
    # wrong foreign set is worse than no baseline, because it still looks like one.
    #
    # AND `by` IS THE SAME KIND OF PARAMETER, AND WAS STILL OUTSIDE THE KEY (order 4ff1db780b99).
    # `exclude` decides which roster is left OUT of the control sample; `by` decides which
    # rosters EXIST to draw it from, and the entire foreign sample is built from it. The two
    # callers genuinely disagree about it: `sweep()` passes `entities_by_source()`, read from
    # data/CHARACTER_SWEEP.json, while `adopt()` builds `{s: [e["name"] for e in
    # recs[s]["entries"]]}` from `weave_index.load_records()`. Those are different universes, so
    # the same host with the same `exclude` and `sample` has two different correct baselines.
    # It was contained only because main() dispatches exactly one of --adopt / --repair /
    # --rosters per process, which is a property of today's CLI and not of this module:
    # `_NULL_CACHE` is module-level and `score(host, names, source, by=...)` is public.
    #
    # `by` is an unhashable dict, which is presumably why it was left out. Rather than digest the
    # dict, THE SAMPLE ITSELF IS THE KEY -- it is what the question actually asks, so the key is
    # exact rather than approximate: any difference in `by` that reaches the control changes it,
    # and two different `by` maps that produce the same control sample are the same question and
    # may honestly share an answer. Building the sample is dict work over at most three names per
    # source; the cost this cache exists to avoid is the network probe below. `exclude` and
    # `sample` stay in the key although the sample now subsumes them, because they are what the
    # earlier order pinned and a key that names the question in the caller's own terms is easier
    # to read than one that names only its result.
    foreign = []
    for src, names in (by or {}).items():
        if src == exclude:
            continue
        foreign.extend(names[:3])
    # Deterministic, not random: the control must be reproducible, or two runs disagree about
    # the same host for reasons nobody can inspect.
    #
    # DEDUPE FIRST, THEN STRIDE (order cb8bc5afa58f). This was one expression --
    # `sorted(set(foreign))[::max(1, len(foreign) // sample)][:sample]` -- and the right-hand
    # side is evaluated before the assignment, so `len(foreign)` counted the list WITH
    # duplicates while the stride was applied to the deduplicated one. Whenever rosters share
    # names the stride came out too coarse and the control ended up SMALLER than `sample`,
    # silently. Measured on the live corpus: 561 raw foreign names, 538 distinct, stride
    # 561//40 = 14, giving 39 control names where the deduplicated stride 538//40 = 13 gives 40.
    # One name today, which is why this was filed INFO -- but the gap scales with name reuse
    # (150 raw / 63 distinct yields 21 names instead of 40), and this function's own comment
    # argues that "a baseline measured against the wrong foreign set is worse than no baseline,
    # because it still looks like one". The cache key below carries `tuple(foreign)`, so it
    # stays exact and no previously cached baseline is silently reinterpreted under the new
    # sample -- a changed control is a changed key.
    uniq = sorted(set(foreign))
    foreign = uniq[::max(1, len(uniq) // sample)][:sample]
    key = (host, exclude, sample, tuple(foreign))
    with _NULL_LOCK:
        if key in _NULL_CACHE:
            return _NULL_CACHE[key]
    r = probe(host, foreign) or {}
    rate = r.get("rate")
    # A CONTROL THAT DID NOT MEASURE IS `None`, NOT ZERO -- and this line is why the order that
    # fixed `probe()` was only half a fix. `probe()` deliberately returns rate=None with an
    # error field when the request throws or the host has no usable endpoint, with a comment
    # saying a failed request is not a wiki that holds nothing. This function then wrote
    # `rate = 0.0 if rate is None else rate` and committed the identical conflation one call
    # deeper: a throttled or network-failed probe of the FOREIGN control sample became "this
    # host answers 0% of names it has no reason to hold", the most generous baseline available,
    # which flatters every lift computed against it. Seventy-four throttled probes reading as 0%
    # is what unassigned warhammer40k.fandom.com from Warhammer 40,000; the same failure on the
    # control side would silently ADOPT hosts instead, which is the worse direction.
    #
    # `probe()` also returns None outright for an empty name list, so a host with no foreign
    # sample to draw on (every other source excluded, or an empty corpus) lands here too. That
    # is equally an unmeasured control and is answered the same way.
    if rate is None:
        # NOT CACHED. A failure is a fact about this moment, not about this host, and caching it
        # would make one throttled probe stand as the host's baseline for the rest of the run.
        return None
    with _NULL_LOCK:
        _NULL_CACHE[key] = rate
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

    # `null_rate` now answers an UNMEASURED control with None rather than with the flattering
    # 0.0 it used to. There is no lift without a baseline, so None propagates all the way to the
    # verdict instead of being defaulted here -- defaulting it is the whole defect.
    base = null_rate(host, by=by, exclude=source) if by else 0.0
    r["baseline"] = None if base is None else round(base, 3)
    rate = r.get("rate")
    r["lift"] = None if (rate is None or base is None) else round(rate - base, 3)

    # The aboutness veto only applies to GENEROUS hosts, and generosity is what the baseline
    # measures. With no baseline there is no such thing as "generous enough to need a veto",
    # and `base >= ABOUT_VETO_ABOVE` on None raises TypeError besides.
    # `about_n` IS PART OF THE ANSWER, NOT A DIAGNOSTIC. It rides into HOST_FITNESS.json with the
    # rate so a reader can tell six-of-twelve from one-of-two, and the verdict below reads it.
    r["about"], r["about_n"] = (
        relevance(host, r.get("titles") or [], source)
        if r["hits"] and base is not None and base >= ABOUT_VETO_ABOVE else (None, None))
    r.pop("titles", None)

    if rate is None:
        r["verdict"] = "UNREACHABLE — no judgement"
        r["rate"] = 0.0
    elif base is None:
        # THE ROSTER PROBE ANSWERED AND THE CONTROL DID NOT. Every verdict below this line is a
        # statement about LIFT, and lift is undefined here. Judging on the raw rate instead is
        # the reading that adopted a homebrew shelf onto Wikipedia and rejected one from the
        # wiki that hosts it. Bucketed as UNREACHABLE so `sweep()` retries it another day rather
        # than sending it for repair on a measurement that was never made.
        r["verdict"] = "UNREACHABLE — the control probe failed, so this host has no baseline"
    elif r["probed"] < MIN_PROBE:
        r["verdict"] = "too few names to judge"
    elif r["hits"] < 2 or r["lift"] <= LIFT_MIN:
        # Indistinguishable from what this host gives anybody who asks.
        r["verdict"] = "WRONG FICTION" if rate <= DEAD else "NAMES ONLY"
    elif (r["about"] is not None and r["about"] < ABOUT
          and r["about_n"] is not None and r["about_n"] < ABOUT_MIN):
        # THE VETO IS DUE AND ITS INPUT IS TOO THIN TO CARRY IT (order 44ae72489678). This host
        # is generous enough that only the pages can separate coverage from coincidence, and
        # fewer than ABOUT_MIN of them came back readable -- so the aboutness figure here is the
        # 1/2-reads-as-50% case MIN_PROBE already refuses one measurement over.
        #
        # UNREACHABLE RATHER THAN A SILENT ABSTENTION, and that is the whole point. Letting the
        # veto simply not fire hands the verdict to lift alone, which lands on `holds` or on
        # `partial` -- and `partial` is inside JUDGED, so an unmeasured host would still have
        # gone to the repair pass. This bucket is the one `score` already uses two branches up
        # for exactly this class of fact ("the control probe failed, so this host has no
        # baseline"): the probe answered, a control the verdict depends on did not, so nothing
        # is decided. `sweep` leaves these hosts exactly as they are and retries another day,
        # `adopt`/`recover` will not promote one, and no correct wiki is unassigned on two
        # articles. An unmeasurable condition does not come back as a measured zero.
        r["verdict"] = ("UNREACHABLE — only %d article body(ies) could be read, too few to judge "
                        "aboutness" % r["about_n"])
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
            #
            # RANKED BY LIFT, NOT BY RAW HIT RATE (order e2f0b13c766f). This loop read
            # `best = (0.0, None)`, `p["rate"] > best[0]`, `best[0] >= GOOD`, `best[0] > DEAD` --
            # every comparison in raw-rate units, in the pass that decides where a source's
            # evidence will be mined from. `score()`'s own docstring is a sustained argument that
            # the raw rate must not decide: "33% on D&D Wiki is thirty-three points of signal and
            # 33% on Wikipedia is worse than chance. Both readings were made in this project and
            # both were wrong." `adopt()` -- the sibling pass doing this same job for hostless
            # sources -- already selects by lift, and carries its own note about an earlier
            # version whose units changed between iterations.
            #
            # IT WAS BOUNDED, NOT FATAL, and the bound is worth writing down: a candidate must
            # first pass `verdict in ("holds", "partial")`, which is itself lift-based (see
            # `score`), so the raw-rate comparison could only ever REORDER hosts that had already
            # cleared the lift bar -- it could not adopt one that failed it. What it did do is
            # systematically prefer the GENEROUS survivors, en.wikipedia.org at 45% held over a
            # specific wiki at 40% held whose lift is far larger, which is precisely the
            # preference lift was introduced to remove. The `>= GOOD` early exit made that worse:
            # the loop stopped at the first candidate to reach 0.35 RATE, so a better host later
            # in the ranking was never probed at all.
            #
            # (lift, rate, host), shaped like `adopt()`'s tuple: the first slot is LIFT and only
            # lift, so no iteration can compare one unit against another. The rate rides along
            # only so the operator's line still shows the figure they are used to reading.
            best = (0.0, 0.0, None)
            judged_any = False
            for h in candidates(src, r["host"], by=by, hosts=hosts):
                p = score(h, by[src], src, by=by)
                ok = p["verdict"] in ("holds", "partial")
                judged_any = judged_any or not p["verdict"].startswith("UNREACHABLE")
                if ok and p["lift"] is not None and p["lift"] > best[0]:
                    best = (p["lift"], p["rate"] or 0.0, h)
                ab = "   -" if p.get("about") is None else f"{p['about']:>4.0%}"
                lf = "    -" if p.get("lift") is None else f"{p['lift']:>+5.0%}"
                print(f"    {p['rate']:>5.0%} held {lf} lift  {ab} about  {h:<34}"
                      f"{p['verdict'] if not ok else ''}", flush=True)
                if best[0] >= GOOD_LIFT:
                    break
            # `> LIFT_MIN` is the lift-unit translation of the `> DEAD` this replaces: DEAD is
            # "the host is about something else entirely" in rate, LIFT_MIN is "the result is
            # what the host gives anyone" in lift. Nothing that passed `ok` can fail it -- the
            # verdict already required it -- and it is kept for the same reason `adopt()` keeps
            # its floor: the gate should state the bar even when the bar is already met.
            if best[2] and best[2] != r["host"] and best[0] > LIFT_MIN:
                fixed[src] = best[2]
                print(f"  -> {src}: {r['host']} => {best[2]} "
                      f"({best[0]:+.0%} lift, {best[1]:.0%} held)")
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
            for k, v in fixed.items():
                if v is None:
                    unfit[k] = {"rejected": hosts.get(k),
                                "verdict": results[k]["verdict"],
                                "held": results[k]["rate"],
                                # WITH ITS DENOMINATOR. A rejection filed as `about: 0.0` and
                                # nothing else cannot be re-read later for how much was actually
                                # looked at, which is the first thing anyone reviewing an
                                # unassignment wants to know.
                                "about": results[k].get("about"),
                                "about_n": results[k].get("about_n")}
            hosts.update({k: v for k, v in fixed.items() if v})
            for k, v in fixed.items():
                if v is None:
                    hosts.pop(k, None)
            # WIKI_HOSTS.json is written from THREE call sites in two modules (this function,
            # `adopt()` below, and `scout.py`'s host registration) and read by feats, read,
            # completeness, ingest_doc and wiki_source, several of them long-running. A bare
            # open("w") truncates before json.dump starts, so a losing writer or a mid-dump
            # failure leaves every one of those readers looking at an unparseable or empty host
            # map -- and an empty host map reads downstream as "no source has a wiki", which is
            # how COMPLETENESS.json came to hold zero rows on 2026-08-24. tmp + replace_retry,
            # the pattern the rest of the tree already uses. 2026-08-24.
            #
            # THROUGH THE MERGE, NOT THE WHOLE MAP (order 1f79b49a4df7, run #36). `hosts` was read
            # at the top of this function and this pass then probed every failing source over
            # eight threads, so writing it back whole reverts anything `adopt()` or `scout.py`
            # landed in between. `fixed` is exactly the set of changes this pass earned -- a host
            # for a repointed source, None for one judged unfit -- and that is what gets applied,
            # to a fresh read, under a compare-and-swap. The local `hosts` above stays updated
            # only so the report below and any later reader in this call see the same picture.
            landed, why = _land_hosts(fixed, "the host-fitness repair pass")
            # THE REJECTIONS FILE HAS A VERDICT TOO, AND IT WAS BEING THROWN AWAY (order
            # 1b15acd3f7b2). `_land_hosts` on the line above has ALREADY dropped every unfit
            # source from WIKI_HOSTS.json by the time this runs, and `_land` ->
            # `silence.write_json` returns False and NEVER RAISES on a denied replace -- the
            # ordinary case here, a reader holding the file open. So a refused UNFIT write left
            # the source gone from the host map with no finding written down anywhere, which is
            # precisely the "gap indistinguishable from a source nobody has got to yet" the
            # comment eight lines above says this whole file exists to end, and the line below
            # announced the rejections file as written.
            unfit_landed = _land(UNFIT, unfit)
            if landed:
                print(f"\nWIKI_HOSTS.json updated: {sum(1 for v in fixed.values() if v)} "
                      f"repointed, {sum(1 for v in fixed.values() if not v)} recorded unfit")
            else:
                # A repair that did not land must not be reported as one. This is the file the
                # rest of the pipeline reads to know where anything lives.
                print("\nWIKI_HOSTS.json NOT updated: " + why, file=sys.stderr)
            if unfit_landed:
                print(f"-> {UNFIT}   (every rejection kept, so a gap reads as a gap)")
            else:
                print(f"{UNFIT} NOT updated (denied replace): {sum(1 for v in fixed.values() if not v)} "
                      f"rejection(s) from this pass are not on file, so the sources they dropped "
                      f"from the host map now read as sources nobody has got to yet",
                      file=sys.stderr)

    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    # Gated for the same reason (order 1b15acd3f7b2): the verdict was discarded and "-> path"
    # printed either way, so a denied replace reported this pass's fitness report over the
    # previous one. Nothing is lost -- the pass can be re-run -- but an operator acting on a
    # stale report they believe is today's is the expensive half of that.
    if _land(OUT, results):
        print(f"-> {OUT}")
    else:
        print(f"{OUT} NOT updated (denied replace); the fitness report on disk is the previous "
              f"pass's, not this one's", file=sys.stderr)
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

    The safety here is the HUMAN, not a second automated condition. An earlier docstring
    claimed the code also required the host to have been independently rejected; it never did
    (the check was loaded and unused), and pretending a safeguard exists is worse than naming
    the real one: nothing is purged except sources a person explicitly listed with --source,
    after reading the roster. Every purge is written to ROSTER_PURGES.json with what was removed, so
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
    if not only:
        print("  --source is required: the audit shortlists, a person decides.")
        print("  Pass --source NAME (repeatable) to purge exactly those.")
        print("")
        # THE SHORTLIST IS SPLIT BY `judgeable`, AND UNTIL NOW IT WAS NOT (order 601435e86a76).
        # `roster_audit` computes `judgeable` for every row -- False when the title names a
        # PRODUCT rather than a world (a homebrew class page has no reason to say "Unearthed
        # Arcana") or when its only token is too common to carry information ("Extra Life"
        # reduces to "life"). `standards.py` already filters on it, with the comment "a standard
        # that counts findings nobody can act on is a standard nobody reads". This shortlist did
        # not, and it is the more dangerous of the two places to omit it: it is what a person
        # reads immediately before running the irreversible `--purge --go`.
        #
        # MEASURED ON THE LIVE AUDIT, 2026-09-01: 43 rows, 3 below the rate bar, and ALL THREE
        # of them not judgeable -- Explorer's Guide to Wildemount, Extra Life, Player's Handbook.
        # So every entry on the shortlist was a source the audit itself says it cannot speak to,
        # presented under a heading asserting the host was wrong.
        #
        # SPLIT, NOT FILTERED (Hard Rule 0). Dropping the unjudgeable rows would be a truncation
        # of the same listing by another name -- a person who has seen this shortlist should not
        # have to wonder what was left out of it. They are printed under their own heading that
        # says what their low rate does and does not mean.
        low = sorted((kv for kv in audit.items() if kv[1]["rate"] < 0.10),
                     key=lambda kv: kv[1]["rate"])
        actionable = [kv for kv in low if kv[1].get("judgeable", True)]
        unjudgeable = [kv for kv in low if not kv[1].get("judgeable", True)]
        print("  shortlist -- the pages mined for these sources never name them, which means")
        print("  the HOST was wrong. Read each roster before concluding the ENTRIES are:")
        if not actionable:
            print("     (none)")
        for src, r in actionable:
            print(f"     {r['rate']:>4.0%}  {src}  <- {r['host']}")
        if unjudgeable:
            print("")
            print("  BELOW THE BAR BUT NOT JUDGEABLE BY THIS TEST -- these are NOT evidence of a")
            print("  wrong host. The title names a product rather than a world, or its only")
            print("  token is too common to carry information, so a low rate here means the")
            print("  test could not speak, not that the roster is foreign:")
            for src, r in unjudgeable:
                print(f"     {r['rate']:>4.0%}  {src}  <- {r['host']}  "
                      f"(looked for {', '.join(r['tokens'])})")
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
        n_entries = n_files = n_removed = 0
        # THE RECORD WRITE'S VERDICT NOW DECIDES WHETHER THE CACHE MAY BE DELETED (order
        # 1b15acd3f7b2), and this is the one discarded verdict in this module that was
        # DESTRUCTIVE. `_land` -> `silence.write_json` returns False and NEVER RAISES on a denied
        # replace, and a denied replace is the ordinary case on this machine -- a reader holding
        # the target open. With the verdict thrown away the sequence was: leave the wrong-fiction
        # entries and the purged_roster note UNWRITTEN, then unconditionally os.remove() every
        # cached page under data/feats/<host>/ and data/readfeats/<host>/, then print that the
        # purge succeeded. The entries stayed, their only supporting evidence was gone
        # irreversibly, and nothing on disk said so. This function's own docstring says the point
        # is that "the gap it leaves is a recorded finding rather than a silence"; on a denied
        # write it was a silence.
        landed = True
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
                # Deliberately a direct write and NOT pipeline.write_record_catalogue: that
                # writer merges and never shrinks an entry list, which is exactly right for a
                # cast-growing pass and exactly wrong for a purge whose whole purpose is to
                # empty one. It is made atomic here so a kill mid-dump cannot leave a record
                # file unparseable, which would lose the entries AND the purge note together.
                if not _land(fp, r, sort_keys=False, ensure_ascii=False):
                    landed = False
                    silence.note("hostcheck.py:purge-record-denied")
        # the caches those entries wrote
        # Order 5159320dd758: this hand-spelled cachekey.host_dir()'s own formula instead of
        # calling it -- the exact "four independent copies of one convention" cachekey.py's own
        # docstring says drift, in a module that already imports cachekey for `load()` above. If
        # HOST_CAP or the sanitiser regex ever moves, a hand-spelled copy here keeps the OLD
        # answer and this purge silently deletes nothing from the actual cache directories.
        for base in ("feats", "readfeats"):
            d = os.path.join(HERE, "data", base, cachekey.host_dir(mined))
            if not os.path.isdir(d):
                continue
            for fp in glob.glob(os.path.join(d, "*.json")):
                n_files += 1
                if dry or not landed:
                    continue
                try:
                    os.remove(fp)
                except OSError:
                    # Counted as NOT removed rather than assumed gone. A cache file that will
                    # not delete is a page still on disk supporting entries that are not, and
                    # the operator has to be able to see the difference; the bare `os.remove`
                    # this replaces would also have aborted the whole purge on one locked file.
                    silence.note("hostcheck.py:purge-cache-remove")
                    continue
                n_removed += 1
        # `landed` is None in a dry run because nothing was written, and a caller must be able
        # to tell "not attempted" from "attempted and refused" -- the distinction this order was
        # filed about. `removed` is what actually left the disk; `files` is what was found.
        log[src] = {"mined_from": mined, "now": now, "entries": n_entries, "files": n_files,
                    "removed": n_removed, "landed": None if dry else landed}
        if dry:
            print(f"  would remove: {src}  <- {mined}   {n_entries} entries, "
                  f"{n_files} cache files")
        elif landed:
            print(f"  removed: {src}  <- {mined}   {n_entries} entries, "
                  f"{n_removed}/{n_files} cache files")
        else:
            print(f"  NOT PURGED: {src}  <- {mined}   the record write was denied, so its "
                  f"{n_entries} entries STAY and its {n_files} cache files were left in place "
                  f"rather than deleted out from under them", file=sys.stderr)

    if not dry and log:
        prev = {}
        if os.path.exists(PURGED):
            try:
                with open(PURGED, encoding="utf-8") as f:
                    prev = json.load(f)
            except Exception:
                silence.note("hostcheck.py:purge-log")
        prev.update(log)
        # Gated (order 1b15acd3f7b2). This is the file that explains what became of the purged
        # entries; announcing it as written when the replace was denied leaves the purge with no
        # record of itself anywhere, which is the same silence the per-record write above was
        # gated to prevent.
        if _land(PURGED, prev):
            print(f"-> {PURGED}")
        else:
            print(f"{PURGED} NOT updated (denied replace): this pass's purges are not on file",
                  file=sys.stderr)
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
        if not by.get(src):
            # An empty roster has already been purged. It cannot fail a test about its
            # contents, and leaving the old verdict on file keeps a solved problem permanently
            # red. (This sat AFTER the seen<MIN_PROBE return for a while -- unreachable, since
            # an empty roster always trips that first.)
            return None
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
            # M23: the roster audit judges whether a host's pages actually name the source's
            # entities. Reading a colliding neighbour's cached text here would credit THIS
            # entity with a page that never mentioned it, so ownership is proved first.
            d, fp = cachekey.load(
                os.path.join(HERE, "data", "feats"), host, name,
                on_corrupt=lambda _p: silence.note("hostcheck.py:roster_audit"))
            if d is None:
                continue
            body = " ".join((d.get("text") or {}).values()).lower()
            if not body:
                continue
            seen += 1
            if any(t in body for t in toks):
                hit += 1
        if seen < MIN_PROBE:
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
            # THE MARKER READS `judgeable` NOW (order 601435e86a76). It asserted "ROSTER FROM
            # ANOTHER FICTION" purely on the rate, on rows this same function has just decided
            # the test cannot speak to -- so a Player's Handbook, which no spell page has any
            # reason to name, was flagged as evidence of a wrong host.
            if r.get("judgeable", True):
                mark = "" if r["rate"] >= 0.10 else "   <-- ROSTER FROM ANOTHER FICTION"
            else:
                mark = "   <-- not judgeable: the test cannot speak to this title"
            # HARD RULE 0: the source name is printed WHOLE. This was `r['source'][:44]` inside
            # a `:<46` field -- a silent mid-name cut on the one column a person uses to tell two
            # sources apart, and the roll's longest names are exactly the publisher-plus-title
            # forms that share prefixes. The column still pads; it no longer truncates.
            print(f"  {r['rate']:>5.0%}  {r['naming_source']:>4}/{r['pages']:<5} "
                  f"{r['source']:<46}{mark}", flush=True)
    low = [r for r in out if r["rate"] < 0.10]
    bad = [r for r in low if r.get("judgeable", True)]
    unjudgeable = [r for r in low if not r.get("judgeable", True)]
    print(f"\n{len(out)} sources with enough mined text to judge; "
          f"{len(bad)} carry a roster that never names their own fiction")
    for r in sorted(bad, key=lambda x: x["rate"]):
        print(f"   {r['source']}  ({r['host']}, looked for {', '.join(r['tokens'])})")
    if unjudgeable:
        # Counted and named separately rather than folded into `bad` or dropped: the first
        # overstates the finding, the second hides rows a person has a right to see.
        print(f"{len(unjudgeable)} more sit below the bar but are NOT judgeable by this test "
              f"-- a low rate here means the test could not speak, not that the host is wrong")
        for r in sorted(unjudgeable, key=lambda x: x["rate"]):
            print(f"   {r['source']}  ({r['host']}, looked for {', '.join(r['tokens'])})")
    # Gated (order 1b15acd3f7b2). `purge()` reads this file to decide what to purge, so a denied
    # replace reported as a success hands the next purge the PREVIOUS audit's verdicts -- and
    # those name sources whose rosters it will empty and whose caches it will delete.
    if _land(ROSTERS, {r["source"]: r for r in out}):
        print(f"-> {ROSTERS}")
    else:
        print(f"{ROSTERS} NOT updated (denied replace); the roster audit on disk is the previous "
              f"pass's, and purge() reads it", file=sys.stderr)
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
        # (lift, rate, host, verdict). The first slot is LIFT and only lift -- an earlier
        # version stored the RATE there and then compared other candidates' lift against it,
        # so the units changed between iterations and a worse-lift host could win.
        best = (0.0, 0.0, None, "")
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
                best = (r["lift"], r["rate"] or 0.0, h, r["verdict"])
            if best[0] >= GOOD_LIFT:
                break
        return src, best

    found = {}
    with ThreadPoolExecutor(max_workers=workers) as ex:
        for src, (lift, rate, host, verdict) in ex.map(one, hostless):
            if host:
                found[src] = host
                print("   {:>+5.0%} lift  {:<9}{:<34}{}".format(lift, verdict, host, src[:40]),
                      flush=True)
            else:
                print("      -   none      {:<34}{}".format("", src[:40]), flush=True)

    print("")
    print("{} adopted, {} genuinely without a wiki".format(
        len(found), len(hostless) - len(found)))
    if found and not dry:
        # THE MERGE, NOT THE MAP. `hosts` was read before the threaded probe above, which runs for
        # as long as the hostless list takes -- the widest read-to-write window in this module.
        # Writing that snapshot back whole reverts every host `sweep(--repair)` or `scout.py`
        # registered while this pass was probing, on the one file this project cannot rebuild.
        # (order 1f79b49a4df7, run #36)
        hosts.update(found)
        landed, why = _land_hosts(found, "the adopt pass")
        if landed:
            print("-> " + F.HOSTS)
        else:
            # `found` is returned either way -- the caller asked what this pass adopted and that
            # is a true answer -- but it must not read as "and it is on disk".
            print("adopt: " + str(len(found)) + " adopted host(s) were NOT written: " + why,
                  file=sys.stderr)
    return found


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--only", help="restrict to sources whose name contains this")
    ap.add_argument("--repair", action="store_true",
                    help="search for a better host for every failing source and rewrite the map")
    ap.add_argument("--purge", action="store_true",
                    help="remove the roster for each source named with --source, after a human "
                         "has read the audit shortlist; no automated host check gates this")
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
