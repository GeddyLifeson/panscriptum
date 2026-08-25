#!/usr/bin/env python3
"""
FEATS — the evidence base for the Custodial Assay, mined from source text.

Charter Part Three requires every Assay decimal to trace back to "a feat somebody witnessed, an
instrument somebody read, or a defeat somebody suffered." Phase 2 tried to get those out of the
catalogue's own entry descriptions and could not: the median description is 170 characters of
biography, so 99.6% of judged entries came back `unassayed` and only 553 kept a scale_note. That
is the gate working correctly on material that does not contain what the gate is looking for.

The material exists elsewhere. Three findings from probing it:

  1. The `wiki_page` stored on 13,857 entries points at the BIOGRAPHY. Goku's biography is
     production history — five sections on Toriyama's influences — and yields zero feats.
     `Goku/Power and Abilities` is 114,748 characters and yields eleven, two of them measured
     quantities. The feats were always one page sideways from where we were looking.
  2. Host coverage is patchy: 71 of 211 sources have a derivable wiki host and 140 have none,
     including One Piece, Naruto and JoJo. Fandom slugs resolve by guess for most of those
     (`onepiece`, `naruto`, `jojo`, `adventuretime` all answer; `magicthegathering` does not,
     it is `mtg`), so guesses are VERIFIED against the API and cached, never assumed.
  3. Tables carry the numeric scale data. A first strip deleted `{|...|}` wholesale and took
     `List of Power Levels` from 19,110 characters to 1,317, throwing away the numbers, which
     are the most citable evidence on the wiki. Table CELLS are kept now; only the markup goes.

What comes out is a per-entity evidence file: gate-passing feat sentences and extracted physical
quantities, each carrying the page it came from, so the worksheet line can cite it. Nothing here
scores anything — scoring is `magnitude.py` against `assay.py`. This only gathers, and it keeps
everything it gathers, including what the gate turned down, because the previous pass discarded
its rejections and left the rejection rate unauditable.
"""
import argparse
import collections
import json
import os
import re
import sys
import time
import threading
import urllib.error
import urllib.parse
import urllib.request

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import cachekey                                                         # noqa: E402
import pipeline as P                                                    # noqa: E402
import silence

CACHE = os.path.join(HERE, "data", "feats")
HOSTS = os.path.join(HERE, "data", "WIKI_HOSTS.json")
# Wikimedia's user-agent policy asks for a contact, and honouring it is the difference between
# being rate-limited and being blocked outright.
UA = ("PanscriptumResearchBot/1.0 (personal research archive; "
      "contact imarlonlee@gmail.com) python-urllib")

# Fandom asks for restraint rather than a published number. One request at a time with a pause
# is well inside anything reasonable, and the whole roll is only a few thousand requests.
PAUSE = 0.34
# Wikimedia is far stricter than Fandom and says so in its policy. One global pause with eight
# workers on nineteen Wikipedia-routed sources earned a flat 429 across the whole host, which
# then read as "the API is unreachable" -- another failure wearing the costume of an absence.
# Per-family limits, with Wikipedia deliberately slow.
HOST_PAUSE = {"wikipedia.org": 1.5, "dandwiki.com": 2.0}
TIMEOUT = 45
BATCH = 40                      # MediaWiki accepts 50 titles per query; 40 leaves headroom


# The roll runs many workers at once, and a global pause would let eight of them hit ONE wiki
# twenty-three times a second. The limit that matters is per host: workers on different sources
# are on different wikis and do not queue behind each other, while two workers on the same wiki
# take turns.
_HOST_LOCKS = collections.defaultdict(threading.Lock)
_HOST_LAST = {}
_RATE_LIMITED = {}

# HOW OFTEN THE DISCOVERY CAPS ACTUALLY BIND (m82, measured from run #19 onward).
#
# `discover()` asks for aplimit=500 subpages and srlimit=50 search hits and handles no
# continuation token, so an entity with more than that is read in part. Nothing measured how
# often that happens, which made it impossible to rank against Hard Rule 0 -- the rule forbids
# caps, but the remedy (a continuation loop, more requests against every wiki) is only worth
# its cost if the cap ever binds. MediaWiki says so itself: a response carrying a top-level
# `continue` key means it withheld results. Counting that is free and settles the question with
# a number instead of an argument. Reported in roll()'s summary alongside _RATE_LIMITED, which
# had been incremented since the file was written and never once read.
_CAP_BOUND = {}


def _pause_for(host):
    for frag, val in HOST_PAUSE.items():
        if frag in host:
            return val
    return PAUSE


def _throttle(host):
    with _HOST_LOCKS[host]:
        last = _HOST_LAST.get(host, 0.0)
        wait = _pause_for(host) - (time.time() - last)
        if wait > 0:
            time.sleep(wait)
        _HOST_LAST[host] = time.time()



# A regex escape arriving as a literal control character matches nothing and fails SILENTLY.
# A word-boundary escape written through a shell heredoc has arrived here as a 0x08 backspace
# three separate times in this project, most recently in the axis gates below, where all
# eleven returned False and read as a tuning problem rather than as corruption. The check
# itself is built from chr() codes, because the first version was written with escapes and
# they were eaten too -- it flagged its own source and refused to load.
_BAD = (chr(8), chr(11), chr(12), chr(7))
_SRC = open(os.path.abspath(__file__), encoding='utf-8').read()
if any(c in _SRC for c in _BAD):
    raise SystemExit(__file__ + ': a regex escape was eaten in transit - a literal control '
                     'character is present in the source. Repair before running.')


# --------------------------------------------------------------------------- transport

def api(host, params, retries=2):
    """One MediaWiki API call. Returns parsed JSON, or None."""
    q = dict(params)
    q.update({"format": "json", "formatversion": "2"})
    # Wikipedia serves its API from /w/api.php; Fandom serves it from /api.php. Getting this
    # wrong fails as a 404 inside the retry loop, which api() swallows and returns None for --
    # indistinguishable from "this entity has no page". Every Wikipedia source therefore mined
    # to exactly zero and looked like an honest absence: the twelve Pantheons, the astrologies,
    # the Solomonic tradition. Those hold the ontological claimants, which is the material Part
    # Three's Omega Band exists to assay.
    # The path is PROBED, not assumed. Two hardcoded cases covered Fandom and Wikipedia and
    # nothing else, so a self-hosted MediaWiki (rimworldwiki.com serves /api.php but is not
    # Fandom) and an API-closed wiki (dandwiki.com answers every API call with 403) both mined
    # to exactly zero and read as honest absence. See endpoint.py.
    import endpoint as EP
    base = EP.api_url(host)
    if not base:
        return None                       # no usable API here; fetch() takes the raw path
    url = base + "?" + urllib.parse.urlencode(q)
    for attempt in range(retries + 1):
        try:
            _throttle(host)
            req = urllib.request.Request(url, headers={"User-Agent": UA})
            with urllib.request.urlopen(req, timeout=TIMEOUT) as r:
                return json.loads(r.read().decode("utf-8", "replace"))
        except urllib.error.HTTPError as e:
            # 429 is a request to slow down, not a failure to retry at the same speed. Backing
            # off exponentially and honouring Retry-After is the difference between recovering
            # and being banned. A 404 is a real miss and retrying it only wastes the budget.
            #
            # The note is taken AFTER the status code is known (run #19). It used to fire first,
            # so an expected 404 — which the branch below calls "a real miss", i.e. the wiki
            # answering correctly that a page is absent — landed in the same swallowed-error
            # bucket as a genuine 500. That made the ledger's count for this site unreadable:
            # it mixed "the network is failing" with "the page does not exist". The 404 arm
            # returns exactly what it returned before; only which counter it lands in changed.
            if e.code == 404:
                silence.note("feats.py:api-404")
                return None
            silence.note("feats.py:125")
            if e.code == 429:
                wait = int(e.headers.get("Retry-After") or 0) or (5 * (attempt + 1) ** 2)
                _RATE_LIMITED[host] = _RATE_LIMITED.get(host, 0) + 1
                if attempt == retries:
                    return None
                time.sleep(min(wait, 120))
                continue
            if attempt == retries:          # 404 already returned above
                return None
            time.sleep(2 + attempt * 4)
        except Exception:
            silence.note("feats.py:139")
            if attempt == retries:
                return None
            time.sleep(2 + attempt * 4)


def alive(host):
    return bool(api(host, {"action": "query", "meta": "siteinfo"}, retries=0))


# --------------------------------------------------------------------------- host resolution

_SLUG_FIXES = {
    "magicthegathering": "mtg",
    "thelordoftherings": "lotr",
    "dungeonsdragons": "forgottenrealms",
}

# Sources whose host cannot be guessed from their name, resolved by hand. Three families:
# published D&D books and adventures, which live on the Forgotten Realms wiki rather than one of
# their own; shooter sub-series, which share their franchise's wiki; and real-world material --
# the pantheons, the astrologies, the magical traditions -- which is not fandom material at all
# and belongs on Wikipedia. That last family is the consequential one: the pantheons hold the
# ontological claimants, which are the entries Part Three's Omega Band is FOR.
_HOST_OVERRIDES = [
    (r"^DMs Guild:|^Hoard of the Dragon|^Mordenkainen|^Xanathar|^Tomb of Annihilation|"
     r"^Dungeon of the Mad Mage|^Curse of Strahd|^Descent into Avernus|^Ghosts of Saltmarsh|"
     r"^Storm King|^Princes of the Apocalypse|^Out of the Abyss|^Rime of the|^Waterdeep|"
     r"^Sword Coast|^Dungeon Master's Guide|^Player's Handbook|^Monster Manual|"
     r"^Tales from the Yawning Portal|^Adventurers League|^Acquisitions Inc",
     "forgottenrealms.fandom.com"),
    (r"^all Black Ops|^all Modern Warfare|^Call of Duty", "callofduty.fandom.com"),
    (r"^The Division", "thedivision.fandom.com"),
    (r"^Magic: The Gathering", "mtg.fandom.com"),
    (r"^Vampire: The Masquerade", "whitewolf.fandom.com"),
    (r"^Warhammer 40", "warhammer40k.fandom.com"),
    (r"^Team Fortress", "teamfortress.fandom.com"),
    (r"^War Thunder", "warthunder.fandom.com"),
    (r"^Explorer's Guide to Wildemount|^Rise of Tiamat|^Lost Mines|^Curse of the Crimson|"
     r"^Icewind Dale|^Baldur's Gate", "forgottenrealms.fandom.com"),
    # real-world material -> Wikipedia, same API, different conventions
    (r"^Pantheon:|astrology|witchcraft|Solomonic|Native Combat Traditions|"
     r"^Eastern astrology|^Western astrology|^2112 \(Rush\)|mythology", "en.wikipedia.org"),
]


def _override(source):
    for pat, host in _HOST_OVERRIDES:
        if re.search(pat, source, re.I):
            return host
    return None


def is_wikipedia(host):
    return host.endswith("wikipedia.org")


def _slugs(source):
    """Candidate fandom subdomains for a source name, best guess first."""
    s = source.lower()
    s = re.sub(r"\(.*?\)", " ", s)
    s = re.sub(r"^(all|the)\s+", "", s)
    s = re.split(r"\s+[-–—]\s+|:|,", s)[0]
    bare = re.sub(r"[^a-z0-9]", "", s)
    nothe = re.sub(r"[^a-z0-9]", "", re.sub(r"\bthe\b", "", s))
    out = []
    for c in (_SLUG_FIXES.get(bare), bare, nothe, re.sub(r"[^a-z0-9]", "", s.split()[0]) if s.split() else ""):
        if c and len(c) > 2 and c not in out:
            out.append(c)
    return out


def resolve_hosts(records, verify=True):
    """{source: host}. Derived from stored pages where possible, guessed and VERIFIED otherwise."""
    known = {}
    if os.path.exists(HOSTS):
        with open(HOSTS, encoding="utf-8") as f:
            known = json.load(f)

    for _, r in records:
        src = r["source"]
        # An OVERRIDE outranks a cached guess, always. The overrides were written after the first
        # host resolution had already run and cached its guesses, and this loop skipped anything
        # already present -- so the wrong guesses were frozen in permanently.
        #
        # They were wrong in the most expensive way available: plausibly. "Descent into Avernus"
        # guessed descent.fandom.com, which is the BOARD GAME Descent and answers happily;
        # "Rime of the Frostmaiden" guessed rime.fandom.com, the video game RiME. Verifying that
        # a host responds is not verifying it is the right fiction, and thirteen wikis' worth of
        # entities were mined against unrelated source material before anything noticed.
        ov = _override(src)
        if ov and known.get(src) != ov:
            known[src] = ov
            continue
        if src in known:
            continue
        # Preferred: the corpus already told us, on the entries that carry a page.
        seen = collections.Counter(
            urllib.parse.urlparse(e["wiki_page"]).netloc
            for e in r["entries"] if e.get("wiki_page"))
        if seen:
            known[src] = seen.most_common(1)[0][0]
            continue
        ov = _override(src)
        if ov:
            known[src] = ov
            continue
        if not verify:
            continue
        # Otherwise guess the slug and CHECK it. An unverified guess would silently mine the
        # wrong fiction's wiki, which is worse than mining nothing.
        for slug in _slugs(src):
            h = f"{slug}.fandom.com"
            if alive(h):
                known[src] = h
                break
        else:
            known[src] = None

    # tmp + replace_retry, not a bare open("w"). This file is read by `read.py:queue()` with an
    # unguarded json.load and by completeness, ingest_doc and wiki_source besides; a truncating
    # write racing `read.py --run` could take down a multi-hour pass with a JSONDecodeError, and
    # a half-written host map reads as "no source has a wiki" to everything downstream.
    os.makedirs(os.path.dirname(HOSTS), exist_ok=True)
    tmp = HOSTS + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(known, f, indent=1, ensure_ascii=False, sort_keys=True)
    silence.replace_retry(tmp, HOSTS)
    return known


# --------------------------------------------------------------------------- page discovery

# Where a fandom wiki actually files combat evidence. The subpage convention is the strongest
# signal (`Goku/Power and Abilities`); the rest catch wikis that use their own arrangement.
_EVIDENCE_TITLE = re.compile(
    r"(power|abilit|technique|statistic|arsenal|equipment|weapon|form|transformation|"
    r"skill|feat|strength|combat)", re.I)


def discover(host, name, extra=None):
    """Titles worth reading for one entity: its own page, its evidence subpages, and any page
    whose title names both the entity and an evidence word.

    HARD RULE 0. `extra` was 25, applied as `sorted(hits, reverse=True)[:extra]` -- ranking by
    article size and then TRUNCATING, which the rule names outright ("Ranking is still allowed
    and is encouraged ... Ranking then truncating is not"). The pages it dropped were the tail
    of the evidence list for exactly the entities that have the most written about them, which
    is to say the ones the read prioritises. Nothing logged the drop, so an entity with 40
    qualifying evidence pages was read as an entity with 25 and looked complete. Ranking is
    kept -- richest first still means an interrupted run got the best material -- and the
    truncation is gone. The parameter survives so no caller breaks, but a numeric value is now
    refused loudly rather than honoured silently."""
    if extra is not None:
        raise SystemExit("feats.discover: `extra` was a cap on a ranked page list and is "
                         "refused under Hard Rule 0. Pass None (the default); the list is "
                         "ranked richest-first and returned whole.")
    titles, seen = [], set()

    def add(t):
        if t and t not in seen:
            seen.add(t)
            titles.append(t)

    add(name)
    # A RAW-ONLY HOST HAS NO SEARCH, AND THAT IS A LIMIT, NOT A FAILURE.
    #
    # Every discovery route below goes through the API -- allpages by prefix, search, backlinks.
    # A wiki that closed its API offers none of them, so discovery there is the entity's own
    # title and nothing else. That is genuinely thinner coverage and it is worth having: an
    # entity's own page is where nearly all of its feats are anyway, and the alternative on
    # these hosts is no page at all. Saying which case we are in beats silently returning one
    # title and letting the caller assume the wiki was searched.
    import endpoint as EP
    if EP.detect(host)["mode"] == EP.MODE_RAW:
        return titles
    # The subpage convention, asked for directly — cheaper and more precise than searching.
    ap = api(host, {"action": "query", "list": "allpages",
                    "apprefix": f"{name}/", "aplimit": "500"})
    if (ap or {}).get("continue"):
        _CAP_BOUND["aplimit"] = _CAP_BOUND.get("aplimit", 0) + 1
    for row in (ap or {}).get("query", {}).get("allpages", []):
        if _EVIDENCE_TITLE.search(row["title"]):
            add(row["title"])

    # Then search, keeping only hits that name the entity — otherwise a search for a common
    # name drags in every unrelated power page on the wiki.
    sr = api(host, {"action": "query", "list": "search", "srlimit": "50",
                    "srsearch": f"{name} power abilities strength feats"})
    if (sr or {}).get("continue"):
        _CAP_BOUND["srlimit"] = _CAP_BOUND.get("srlimit", 0) + 1
    key = name.lower().split()[0] if name.split() else name.lower()
    hits = [(row.get("size", 0), row["title"])
            for row in (sr or {}).get("query", {}).get("search", [])
            if key in row["title"].lower() and _EVIDENCE_TITLE.search(row["title"])]
    for _, t in sorted(hits, reverse=True):
        add(t)
    return titles



def _tnorm(t):
    return re.sub(r"[^a-z0-9]+", "", (t or "").lower())


def _page_exists(host, title):
    d = api(host, {"action": "query", "titles": title, "prop": "info", "redirects": "1"})
    for pg in (d or {}).get("query", {}).get("pages", []):
        if not pg.get("missing"):
            return True
    return False


def resolve_title(host, name):
    """The wiki's actual title for this entity, or None.

    17,148 entries mined to nothing because the entity's catalogue name is not the wiki's page
    title -- "Hulk (Bruce Banner)" where the wiki says "Hulk", "Thor Odinson" where it files
    under an Earth designation. A plain search is not safe enough to fix that: searching for
    "Little Horn" returns "Little Steve", and attributing one entity's feats to another is worse
    than an honest blank.

    So candidates are RANKED rather than taken in order, and the ranking is what makes it safe:

      exact normalised match          "Jotaro Kujo" -> Jotaro Kujo
      the name plus a disambiguator   "Jupiter (god)", "Thor (Earth-616)"
      nothing else

    A title that merely CONTAINS the name loses -- that is what turned "Quetzalcoatl" into
    "Order of Quetzalcoatl" -- and a title the name does not open is refused outright.
    """
    n = _tnorm(name)
    bare = _tnorm(re.sub(r"\s*\([^)]*\)", "", name))
    if not n:
        return None
    d = api(host, {"action": "query", "list": "search", "srlimit": "8", "srsearch": name})
    best, best_score = None, (-1, -1)
    for row in (d or {}).get("query", {}).get("search", []):
        t = row["title"]
        tn = _tnorm(t)
        if tn == n or (bare and tn == bare):
            return t                                  # exact: nothing beats it
        # the entity name must OPEN the title; the remainder is a disambiguator
        for cand in (n, bare):
            if cand and tn.startswith(cand) and len(cand) >= len(tn) * 0.55:
                # Tie-broken by ARTICLE SIZE. Marvel files a character once per continuity, and
                # "Thor Odinson (Earth-8096)" scores identically to "Thor Odinson (Earth-616)"
                # on name overlap while being a cartoon adaptation with a stub page. The main
                # continuity's article is the long one, which is the same signal that surfaced
                # Kratos and Zeus when the backfill needed to rank a roster.
                score = (len(cand) / len(tn), row.get("size", 0))
                if score > best_score:
                    best, best_score = t, score
    return best


def fetch(host, titles):
    """{title: wikitext} for up to any number of titles, batched where batching is possible.

    A wiki that closed its API is not a wiki that cannot be read. D&D Wiki -- which holds the
    homebrew shelf this library has the most sources for -- returns 403 on every `api.php`
    action and serves `index.php?action=raw` to anyone. One title per request instead of fifty
    is slower; it is not nothing, and the difference is several thousand entries.
    """
    import endpoint as EP
    if EP.detect(host)["mode"] == EP.MODE_RAW:
        return EP.fetch_raw(host, titles)
    out = {}
    for i in range(0, len(titles), BATCH):
        chunk = titles[i:i + BATCH]
        # redirects=1 matters more than it looks: `Kenshiro` on the Hokuto wiki is a redirect,
        # and without this the miner read 22 characters and reported the entity had no feats.
        d = api(host, {"action": "query", "prop": "revisions", "rvprop": "content",
                       "rvslots": "main", "redirects": "1", "titles": "|".join(chunk)})
        for p in (d or {}).get("query", {}).get("pages", []):
            if p.get("missing") or "revisions" not in p:
                continue
            try:
                out[p["title"]] = p["revisions"][0]["slots"]["main"]["content"]
            except (KeyError, IndexError):
                silence.note("feats.py:374")
                continue
    return out


# --------------------------------------------------------------------------- text


def _unwrap_templates(c, depth=0):
    """Strip template SCAFFOLDING while keeping the prose inside it.

    Deleting `{{...}}` outright is right for an infobox and catastrophic for a Database wiki. DC
    and Marvel wrap the ENTIRE article in one call:

        {{DC Database:Character Template
         | RealName = Bruce Wayne
         | History  = <the whole biography>
         | Powers   = <every power, in prose>
        }}

    Bruce Wayne's page is 190,687 characters inside 760 brace pairs. Repeated `{{[^{}]*}}`
    removal ate the outer call and left THIRTY CHARACTERS -- a stray interwiki link. Every DC and
    Marvel entity was being read as an empty page, and recorded as an honest absence, which is
    this project's signature failure wearing yet another costume. Marvel's 233 "read but silent"
    entries are almost certainly this.

    So: walk the braces, drop the template NAME and the parameter NAMES, and keep the VALUES,
    recursively. A genuine infobox contributes short values that the sentence filter discards
    downstream; an article template contributes its article.
    """
    if depth > 6 or "{{" not in c:
        return c
    out, i, n = [], 0, len(c)
    while i < n:
        if c.startswith("{{{", i):
            # A TEMPLATE PARAMETER, NOT A TEMPLATE CALL. `{{{name|default}}}` is wikitext's
            # parameter syntax and it is three braces, not two. The `{{` branch below matched it
            # anyway, consumed two of the three, scanned to the first `}}` and left the THIRD
            # closing brace behind as literal text: `{{{1|just a param}}}` rendered as
            # `" just a param }"` and `prose {{{2}}} more` as `"prose   } more"`. Measured
            # 2026-08-24 -- filed by the run #5 audit as "miscounts brace nesting on {{{" and
            # open ever since.
            #
            # The stray brace is not cosmetic. This text is what the reader hands the model AND
            # what the VERBATIM check compares its answers against, so a `}` injected into a
            # sentence makes a genuine quotation fail `_norm_q(s) not in _norm_q(ch)` and be
            # counted as a FABRICATION -- the one thing this pipeline is most careful about.
            #
            # A parameter renders as its default: the text after the first pipe, or nothing.
            j, level = i + 3, 1
            while j < n and level:
                if c.startswith("{{{", j):
                    level += 1
                    j += 3
                elif c.startswith("}}}", j):
                    level -= 1
                    j += 3
                else:
                    j += 1
            _, _, dflt = c[i + 3:j - 3].partition("|")
            out.append(" " + _unwrap_templates(dflt, depth + 1) + " ")
            i = j
        elif c.startswith("{{", i):
            j, level = i + 2, 1
            while j < n and level:
                if c.startswith("{{", j):
                    level += 1
                    j += 2
                elif c.startswith("}}", j):
                    level -= 1
                    j += 2
                else:
                    j += 1
            inner = c[i + 2:j - 2]
            # Split on TOP-LEVEL pipes only, so a nested template's own pipes stay with it.
            parts, buf, lvl = [], [], 0
            for ch_i, ch in enumerate(inner):
                if inner.startswith("{{", ch_i) or inner.startswith("[[", ch_i):
                    lvl += 1
                elif inner.startswith("}}", ch_i) or inner.startswith("]]", ch_i):
                    lvl = max(0, lvl - 1)
                if ch == "|" and lvl == 0:
                    parts.append("".join(buf))
                    buf = []
                else:
                    buf.append(ch)
            parts.append("".join(buf))
            vals = []
            for part in parts[1:]:                 # parts[0] is the template name
                eq = part.find("=")
                vals.append(part[eq + 1:] if 0 <= eq < 40 else part)
            out.append(" " + _unwrap_templates(" ".join(vals), depth + 1) + " ")
            i = j
        else:
            out.append(c[i])
            i += 1
    return "".join(out)


def strip_wikitext(c):
    """Wikitext to prose, KEEPING table cell text.

    Deleting tables wholesale cost `List of Power Levels` 93% of its content — and a power-level
    table is the single most citable thing on a fandom wiki, being an actual instrument reading
    rather than a narrator's adjective. Only the pipe-and-brace scaffolding is removed.
    """
    c = re.sub(r"<ref[^>]*>.*?</ref>|<ref[^>]*/>", " ", c, flags=re.S)
    c = re.sub(r"<!--.*?-->", " ", c, flags=re.S)
    c = _unwrap_templates(c)
    c = re.sub(r"\[\[(?:File|Image|Category):[^\]]*\]\]", " ", c)
    c = re.sub(r"\[\[[^\]|]*\|([^\]]*)\]\]", r"\1", c)
    c = re.sub(r"\[\[([^\]]*)\]\]", r"\1", c)
    c = re.sub(r"\[https?://\S+\s+([^\]]*)\]", r"\1", c)
    # table scaffolding only: the {| |} fences, the |- row breaks, and any style attributes
    # ahead of a cell's `|`. The cell text itself survives.
    c = re.sub(r"^\s*\{\|.*$|^\s*\|\}\s*$|^\s*\|-.*$", " ", c, flags=re.M)
    c = re.sub(r"^\s*[!|]\s*(?:[a-z\-]+=\"[^\"]*\"\s*)*\|?", " ", c, flags=re.M)
    c = re.sub(r"'''?|<[^>]+>", "", c)
    c = re.sub(r"^\s*[=*#:;]+\s*", " ", c, flags=re.M)
    return re.sub(r"[ \t]+", " ", c).strip()


# Jace Beleren's page is 142,492 characters and mined to ZERO feats, with zero held back either
# — the tell that nothing was being split at all. Sentence punctuation alone was the cause: a
# wiki page is half list items and table cells, which carry no terminal full stop, so the whole
# page arrived as one 142k-character "sentence" and the length filter dropped it. A newline ends
# a unit of wiki prose as surely as a full stop does.
_SENT = re.compile(r"(?<=[.!?])\s+(?=[A-Z\"“])|\n+")

# Physical quantities that mean the same thing in every fiction, which is why they are worth
# extracting separately: assay.band_for_quantity() can place them on the ladder without anyone's
# opinion in the loop.
_QUANTITY = re.compile(
    r"\b(\d[\d,\.]*)\s*(?:x\s*10\^?(\d+)\s*)?"
    r"(tons?|tonnes?|kilotons?|megatons?|gigatons?|joules?|watts?|newtons?|"
    r"kilomet(?:er|re)s?|met(?:er|re)s?|miles?|light[- ]?years?|parsecs?|"
    r"kili|power\s*level|degrees?|kelvin|celsius|mach|times\s+the\s+speed\s+of\s+light)\b",
    re.I)


def mine(text, page):
    """Sentences that clear the evidence gate, plus any physical quantities, each tagged with
    the page it came from. Rejections are kept — see the module docstring."""
    kept, rejected, quants = [], [], []
    for s in _SENT.split(text):
        s = s.strip()
        if not (20 < len(s) < 400):
            continue
        if P.valid_scale_note(s):
            kept.append({"feat": s, "page": page})
        elif _QUANTITY.search(s) or re.search(r"\b(destroy|obliterat|shatter|surviv)", s, re.I):
            rejected.append({"text": s, "page": page})
        for m in _QUANTITY.finditer(s):
            # The FULL sentence is stored, not a 220-char prefix (run #19). This field is not a
            # display string: `magnitude.py` copies it verbatim into the permanent instrument-tier
            # citation (`out[axis]["feat"]`), and `chain.py` uses it as a provenance dedup KEY —
            # where a shared 220-char prefix would collide two different sentences into one.
            # `s` is already bounded above by the 20 < len(s) < 400 gate, so this stores at most
            # 400 characters. Callers that need a short form truncate at the point of display,
            # which `_show` already does.
            quants.append({"value": m.group(1), "unit": m.group(3), "sentence": s,
                           "page": page})
    return kept, rejected, quants



# --------------------------------------------------------------------------- the axis gates
#
# `pipeline.valid_scale_note` passes 0.28% of wiki sentences, and 99.7% of its refusals come from
# one function: `_act_upon_object`. Reading its vocabulary explains the whole calibration failure.
# `_ACT` holds only catastrophic verbs (destroy, annihilate, shatter, raze, vaporise) and
# `_OBJECT` only cosmic nouns (planets, galaxies, armies, empires), so the gate is structurally a
# RUIN DETECTOR. It cannot see the other ten axes at all:
#
#     "reacted before the bullet arrived"     no ACT verb            refused
#     "survived a point-blank blast"          `survived` not in ACT  refused
#     "convinced the army to stand down"      `convinced` not in ACT refused
#     "teleported across the galaxy"          `teleported` not in ACT refused
#
# So when the model cited an earthquake for Celerity, it was not misreading the evidence. It was
# allocating the only evidence it had ever been shown across eleven axes.
#
# The original gate is not wrong; it is right for the job it was written for. A SOURCE CEILING
# anchors every entry beneath it, so a false positive there tilts a whole shelf and refusing is
# nearly free. One axis of one entity's worksheet carries a different asymmetry: a false positive
# moves a decimal inside an already-anchored band, and the interval already carries the doubt.
# Different cost, different gate. `valid_scale_note` keeps the ceiling job untouched.
AXIS_ACT = {
    "ruin": r"destroy|annihilat|obliterat|shatter|erase|unmake|unmade|raze|level(?:l?ed|s)|"
            r"vapori[sz]|incinerat|disintegrat|sunder|cleave|blow[ns]? (?:up|apart)|"
            r"wipe[ds]? out|kill|slew|slay|slaughter|demolish|wreck",
    "continuity": r"surviv|withstood|withstand|endur|tank(?:ed)?|shrug(?:ged)? off|regenerat|"
                  r"heal(?:ed|s)?|recover|resurrect|reviv|unharmed|no[- ]sold|came back|"
                  r"refus(?:ed)? to (?:die|fall)|immortal",
    "celerity": r"react(?:ed|s)?|dodg|evad|outrun|outpac|blitz|intercept|"
                r"clos(?:ed)? the distance|mov(?:ed|es)? (?:faster|before)|faster than|"
                r"kept pace|struck first|in an instant",
    "reach": r"reach(?:ed|es)?|extend|spann|stretch|cover(?:ed|s)?|from orbit|across the|"
             r"at a range of|hurl|threw|launch",
    "transgression": r"erase|rewr(?:ote|ite)|negat|nullif|bypass|ignor(?:ed|es)?|seal(?:ed|s)?|"
                     r"curs|stop(?:ped)? time|reverse|undo|undid|resurrect|banish|unmade|"
                     r"phas(?:ed)? through|immune",
    "sustain": r"maintain|sustain|held|kept up|for (?:hours|days|weeks|years)|"
               r"without (?:rest|tiring|food|sleep)|continuous|indefinit|never stopped|fought on",
    # `planeswalk` added after the automation assayed the most famous planeswalker in fiction
    # and marked his VECTOR unestimable -- every sentence describing the ability was invisible
    # to the candidate gate because the franchise's own verb for it was not in the vocabulary.
    # The neighbours are the same class of miss: `shunpo`/`flash step` (Bleach), `apparat`
    # (Harry Potter), `blink`, `portal`, `rift`, `dimension(-hop)`.
    "vector": r"teleport|travel(?:l?ed)?|fl(?:y|ew|ies)|cross(?:ed|es)?|traverse|warp|phas(?:ed)?|"
              r"step(?:ped)? (?:through|between)|arriv|appear(?:ed)? (?:at|in)|"
              r"planeswalk|plane ?shift|apparat|shunpo|flash ?step|blink(?:ed|s)?|"
              r"portal(?:ed|s)?|rift|dimension(?:al)? (?:travel|hop|door)",
    "volition": r"master|train|learn|adapt|counter(?:ed)?|outfought|outmatch|defeat|best(?:ed)?|"
                r"overpower|wield|perfect(?:ed)?|develop(?:ed)? (?:a|the|his|her)",
    "acumen": r"predict|calculat|deduc|plan(?:ned)?|analy[sz]|solv|forese|anticipat|devis|"
              r"engineer|invent|outwit|outsmart|realis|realiz",
    "discernment": r"sens(?:ed|es)?|detect|perceiv|notic|observ|read (?:the|his|her|their)|"
                   r"saw through|recogni[sz]|identif|track(?:ed)?|felt",
    "suasion": r"convinc|persuad|inspir|rall(?:y|ied)|command(?:ed)?|negotiat|"
               r"talk(?:ed)? (?:down|out)|sway|won over|united|recruit",
}
_AXIS_ACT_RE = {k: re.compile(v, re.I) for k, v in AXIS_ACT.items()}

# Something of consequence for the act to land on. Widened past the cosmic-only list, because a
# worksheet needs opponents, techniques and crowds as well as planets — Celerity evidence is
# almost never about a galaxy.
_OBJ = re.compile(
    r"\b(?:planets?|worlds?|continents?|galax(?:y|ies)|universes?|multiverses?|dimensions?|"
    r"realit(?:y|ies)|stars?|suns?|moons?|solar systems?|timelines?|civili[sz]ations?|"
    r"cities|city|nations?|countries|country|fleets?|armies|army|islands?|mountains?|"
    r"oceans?|realms?|kingdoms?|empires?|"
    r"opponents?|enem(?:y|ies)|foes?|attacks?|blows?|strikes?|blasts?|techniques?|"
    r"warriors?|soldiers?|fighters?|gods?|deit(?:y|ies)|beasts?|monsters?|dragons?|"
    r"buildings?|fortress(?:es)?|ships?|towers?|walls?|crowds?|villages?|towns?)\b", re.I)

# A comparative is evidence too: "faster than light" fixes a bound without naming an object.
_CMP = re.compile(r"\b(faster|stronger|greater|more powerful|beyond|surpass|exceed|outclass)\b",
                  re.I)


def axis_evidence(sentence, axis):
    """Does this sentence evidence THIS axis, with the subject as the doer?"""
    if P._STATBLOCK.search(sentence):
        return False
    if not _AXIS_ACT_RE[axis].search(sentence):
        return False
    if P._PATIENT.search(sentence):
        return False
    return bool(_OBJ.search(sentence) or P._MAGNITUDE.search(sentence)
                or _CMP.search(sentence))


def by_axis(text, page):
    """{axis: [sentences]} — the worksheet's per-axis candidate lists.

    Handing the model one flat pile and asking it to allocate across eleven axes is what let an
    earthquake be cited for Celerity. Choosing only among an axis's own candidates makes that
    particular error structurally impossible rather than caught afterwards.
    """
    out = {ax: [] for ax in AXIS_ACT}
    for s in _SENT.split(text):
        s = s.strip()
        if not (20 < len(s) < 400):
            continue
        # The statblock, patient and evidence-object gates do not depend on the axis, yet the
        # per-axis loop was re-running all three eleven times per sentence -- a 3x regex
        # redundancy over an 874MB corpus (round-2 optimization audit, finding 1). Hoisted:
        # each runs once per sentence, and only the axis vocabulary check stays inside.
        if P._STATBLOCK.search(s) or P._PATIENT.search(s):
            continue
        if not (_OBJ.search(s) or P._MAGNITUDE.search(s) or _CMP.search(s)):
            continue
        for ax in AXIS_ACT:
            if _AXIS_ACT_RE[ax].search(s):
                out[ax].append({"feat": s, "page": page})
    return out


# --------------------------------------------------------------------------- per-entity

def evidence_for(host, name, cache=True):
    """Everything mined for one entity. Cached on disk: a re-run costs no requests."""
    # M23: the path is built by `cachekey`, and a HIT MUST PROVE IT IS THIS ENTITY'S. The four
    # sites that used to sanitise the name inline all folded `Magic 8 Ball` and `Magic 8-Ball`
    # onto one file, so a reader could be handed a neighbour's mined feats and count them as its
    # own. `cachekey.load` compares the stored `entity` and treats a mismatch as a MISS, which
    # re-mines this one entity instead of inheriting the wrong evidence.
    path = cachekey.write_path(CACHE, host, name)

    def _corrupt(fp):
        # Self-healing, same as read.py's cache: a truncated file (kill mid-write) must be
        # re-earned, never allowed to permanently masquerade as the entity's evidence.
        silence.note("feats.py:corrupt-cache")
        try:
            os.remove(fp)
        except OSError:
            _ = "silence-exempt: removing an already-gone corrupt cache needs no record"
            pass

    if cache:
        doc, _fp = cachekey.load(CACHE, host, name, on_corrupt=_corrupt)
        if doc is not None:
            return doc

    # A SOURCE WITH NO WIKI IS READ FROM ITS OWN PAGES.
    #
    # Homebrew is scattered: kthomebrew.com, GM Binder, a publisher's own site. There is no title
    # lookup on any of them, so discovery cannot ask "give me the page for this entity" -- the
    # registered URLs ARE the corpus, and the reader's name-matching does the attribution, the
    # same way it already does for a shared wiki index page.
    # `pages:<source>` is a host that is not a host: a source whose material lives on ordinary
    # web pages rather than any wiki. The sentinel keeps one host map for everything, so every
    # stage that asks "does this source have somewhere to read from" gets a yes.
    # `doc:<slug>` is the `pages:` sentinel's sibling: an OWNER-SUPPLIED document ingested by
    # ingest_doc.py. The book's own pages are the corpus; name-matching does the attribution,
    # the same way it does for a shared wiki index page. The text is already plain -- running
    # the wikitext stripper over real prose eats legitimate brackets.
    plain = bool(host) and host.startswith("doc:")
    if plain:
        dp = os.path.join(HERE, "data", "docs", host[4:], "pages.json")
        with open(dp, encoding="utf-8") as f:
            all_pages = json.load(f)
        low = (name or "").lower()
        words = [w for w in re.split(r"[^a-z0-9]+", low) if w]

        def _mentions(t):
            tl = t.lower()
            return low in tl or (bool(words) and words[0] in tl and words[-1] in tl)

        pages = {t: txt for t, txt in all_pages.items() if _mentions(txt)}
        titles = sorted(pages)
    else:
        import endpoint as EP
        urls = EP.source_pages(host[6:]) if host and host.startswith("pages:") else []
        if urls:
            pages = EP.fetch_html(urls)
            titles = sorted(pages)
        else:
            titles = discover(host, name)
            pages = fetch(host, titles)
    feats, rej, quants, text = [], [], [], {}
    for t, wt in pages.items():
        clean = wt if plain else strip_wikitext(wt)
        text[t] = clean
        k, r, q = mine(clean, t)
        feats += k
        rej += r
        quants += q

    # The cleaned page text is kept, not only what the gate let through. The gate was tuned for
    # 240-character catalogue blurbs and is visibly too strict on long-form wiki prose — Luffy's
    # 97,519 characters yielded a single feat. Keeping the text makes every later tuning pass a
    # local re-mine over cached files instead of another 48,866 fetches, which is the difference
    # between iterating on the gate in seconds and iterating on it in days.
    out = {"entity": name, "host": host, "pages_read": sorted(pages),
           "chars_read": sum(len(v) for v in pages.values()),
           "feats": feats, "quantities": quants, "gate_rejected": rej, "text": text}
    os.makedirs(os.path.dirname(path), exist_ok=True)
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(out, f, indent=1, ensure_ascii=False)
    silence.replace_retry(tmp, path)
    return out


def remine(path):
    """Re-run the gate over one cached evidence file. No network."""
    with open(path, encoding="utf-8") as f:
        ev = json.load(f)
    if not ev.get("text"):
        return None
    feats, rej, quants = [], [], []
    for t, clean in ev["text"].items():
        k, r, q = mine(clean, t)
        feats += k
        rej += r
        quants += q
    ev["feats"], ev["gate_rejected"], ev["quantities"] = feats, rej, quants
    # ATOMIC: the per-entity evidence cache has live readers (the roll, the assay). This
    # function currently has no callers, which is exactly when a truncation race is easiest
    # to leave in place and hardest to notice later. 2026-08-25.
    silence.write_json(path, ev, indent=1, ensure_ascii=False)
    return ev


# --------------------------------------------------------------------------- the roll

def roll(records, hosts, workers=8, limit=None, only=None):
    """Mine every entity of every resolved source, in parallel.

    Parallelism is per ENTITY but politeness is per HOST (see _throttle), so eight workers spread
    across eight wikis run at full speed while eight workers on one wiki queue behind each other.
    Everything is cached to disk on write, so a killed run resumes for free.
    """
    jobs = []
    for _, r in records:
        h = hosts.get(r["source"])
        if not h or (only and only not in r["source"]):
            continue
        for e in r["entries"]:
            jobs.append((h, r["source"], e["name"]))
    # Jobs built source-by-source put all eight workers on the SAME wiki at once, where the
    # per-host throttle serialises them and the roll runs at one entity a second regardless of
    # worker count. Interleaving by host means the workers are on eight different wikis at any
    # moment, which is what the throttle was designed to allow.
    by_host = collections.defaultdict(list)
    for j in jobs:
        by_host[j[0]].append(j)
    queues, jobs = list(by_host.values()), []
    while any(queues):
        for q in queues:
            if q:
                jobs.append(q.pop())
    if limit:
        jobs = jobs[:limit]

    # `errored` is counted separately from `empty` (run #19). Before it existed, an entity whose
    # evidence_for() raised incremented `n` and NOTHING else: not `empty`, not any other counter.
    # A systemic fault — a bug in evidence_for, a host refusing every request — would therefore
    # depress the roll's feats-per-entity rate with no visible signal anywhere in the summary,
    # and read as "these entities simply had nothing". "Nothing found" and "we never got to look"
    # are different facts and now have different counters.
    done = {"n": 0, "feats": 0, "quant": 0, "pages": 0, "chars": 0, "empty": 0, "errored": 0}
    lock = threading.Lock()
    t0 = time.time()

    def work(job):
        h, src, name = job
        errored = False
        try:
            ev = evidence_for(h, name)
        except Exception:
            silence.note("feats.py:695")
            ev = None
            errored = True
        with lock:
            done["n"] += 1
            if errored:
                done["errored"] += 1
            if ev:
                done["feats"] += len(ev["feats"])
                done["quant"] += len(ev["quantities"])
                done["pages"] += len(ev["pages_read"])
                done["chars"] += ev["chars_read"]
                if not ev["pages_read"]:
                    done["empty"] += 1
            n = done["n"]
            if n % 200 == 0 or n == len(jobs):
                el = time.time() - t0
                rate = n / max(el, 1e-9)
                print(f"  {n:>6,}/{len(jobs):,}  {rate:>5.1f}/s  "
                      f"feats {done['feats']:,}  quantities {done['quant']:,}  "
                      f"pages {done['pages']:,}  {done['chars']/1e6:.0f}M chars  "
                      f"eta {(len(jobs)-n)/max(rate,1e-9)/3600:.1f}h", flush=True)

    from concurrent.futures import ThreadPoolExecutor
    print(f"roll: {len(jobs):,} entities across "
          f"{len({j[0] for j in jobs})} wikis, {workers} workers", flush=True)
    with ThreadPoolExecutor(max_workers=workers) as ex:
        list(ex.map(work, jobs))
    print(f"\ndone in {(time.time()-t0)/3600:.2f}h  "
          f"{done['feats']:,} feats, {done['quant']:,} quantities, "
          f"{done['empty']:,} entities with no page, "
          f"{done['errored']:,} entities that raised")
    # Both of these were being counted and thrown away -- _RATE_LIMITED since the file was
    # written, _CAP_BOUND as of run #19. A measurement nobody prints is not a measurement.
    if _CAP_BOUND:
        print("  discovery caps BOUND: "
              + ", ".join(f"{k} x{v:,}" for k, v in sorted(_CAP_BOUND.items()))
              + "  (m82: these entities were discovered in PART -- no continuation is handled)")
    else:
        print("  discovery caps bound: never (m82: aplimit=500 / srlimit=50 did not truncate)")
    if _RATE_LIMITED:
        tot = sum(_RATE_LIMITED.values())
        ranked = sorted(_RATE_LIMITED.items(), key=lambda kv: -kv[1])   # ranked, never truncated
        print(f"  429s absorbed: {tot:,} across {len(_RATE_LIMITED)} host(s), busiest first: "
              + ", ".join(f"{h} x{n:,}" for h, n in ranked))
    return done


# --------------------------------------------------------------------------- cli

def _show(ev):
    print(f"  {ev['entity']}  @ {ev['host']}")
    print(f"    pages   : {len(ev['pages_read'])}  ({ev['chars_read']:,} chars)")
    for t in ev["pages_read"]:
        print(f"              {t}")
    print(f"    feats   : {len(ev['feats'])}   quantities: {len(ev['quantities'])}"
          f"   held-back: {len(ev['gate_rejected'])}")
    for f in ev["feats"][:6]:
        print(f"       * {f['feat'][:120]}")
    for q in ev["quantities"][:4]:
        print(f"       # {q['value']} {q['unit']}  <- {q['sentence'][:80]}")


def main():
    # PLANT-WIDE INTERLOCK. The top rung of the escalation chain (escalation.py). If a
    # library-wide invariant has been violated, nothing starts until a person rules on it.
    # Placed first in main() so there is no path into this job that skips it.
    try:
        import escalation as _ESC
        _ESC.assert_clear(os.path.basename(__file__))
    except ImportError:
        pass
    ap = argparse.ArgumentParser()
    ap.add_argument("--probe", nargs=2, metavar=("HOST", "ENTITY"),
                    help="mine one entity from one wiki host")
    ap.add_argument("--hosts", action="store_true", help="resolve and cache wiki hosts")
    ap.add_argument("--self-test", action="store_true")
    ap.add_argument("--no-cache", action="store_true")
    ap.add_argument("--roll", action="store_true", help="mine the whole corpus")
    ap.add_argument("--workers", type=int, default=8)
    ap.add_argument("--limit", type=int)
    ap.add_argument("--only", help="restrict the roll to sources containing this string")
    a = ap.parse_args()

    if a.hosts:
        h = resolve_hosts(P.records())
        got = sum(1 for v in h.values() if v)
        print(f"{got}/{len(h)} sources resolved to a wiki host  ->  {HOSTS}")
        for s, v in sorted(h.items()):
            if not v:
                print(f"   unresolved: {s}")
        return 0

    if a.roll:
        recs = P.records()
        hosts = resolve_hosts(recs, verify=False)
        roll(recs, hosts, workers=a.workers, limit=a.limit, only=a.only)
        return 0

    if a.probe:
        _show(evidence_for(a.probe[0], a.probe[1], cache=not a.no_cache))
        return 0

    if a.self_test:
        # The miner has to beat what the catalogue blurb gave us, or it is not worth running.
        # Goku's own biography page yields zero feats; the claim being tested is that pointing
        # at the right page changes that.
        ev = evidence_for("dragonball.fandom.com", "Goku", cache=not a.no_cache)
        _show(ev)
        ok = (len(ev["feats"]) >= 5 and len(ev["quantities"]) >= 1
              and any("Power" in t for t in ev["pages_read"]))
        print(f"\nself-test {'PASSED' if ok else 'FAILED'} — "
              f"{len(ev['feats'])} feats, {len(ev['quantities'])} quantities from "
              f"{len(ev['pages_read'])} pages")
        return 0 if ok else 1

    ap.print_help()
    return 0


if __name__ == "__main__":
    sys.exit(main())
