#!/usr/bin/env python3
"""
Resolves a roll source to a real wiki and pulls genuine entity data from it.

This is the piece that gives the local model something true to work from. Ollama has no
network access and never will -- it is an inference server, not a browser. So the retrieval
lives here, in the harness: this module fetches real names and real article text over the
MediaWiki API, and the model's job downgrades from "remember a franchise" to "structure text
someone else wrote". That is the difference between Attestation *Reconstructed* (guessed) and
*Transcribed* (the chain delivered it).

Two things learned the hard way, both encoded below:

1. HTTPS from Python works fine on this machine, including through Norton's TLS interception
   (the chain shows "Norton Web/Mail Shield Root" and Python trusts it). What fails is the
   DEFAULT USER-AGENT: Fandom answers urllib's stock UA with 403. Sending a real UA fixes it.
   Nothing about Norton needs disabling.

2. Guessing a Fandom subdomain from the source name is right about 85% of the time and
   catastrophically wrong the rest. "Curse of Strahd" resolves to `curse.fandom.com`, which is
   the *Roblox CURSE Wiki* -- a live, populated wiki about something else entirely. Resolution
   is therefore never trusted on a 200 response alone; the wiki must also prove it contains
   the source (see verify_wiki_matches).
"""
import json
import re
import time
import urllib.error
import urllib.parse
import urllib.request

UA = {"User-Agent": "Panscriptum-Cataloguer/1.0 (local library research tool)"}

# Sources whose wiki cannot be guessed from the name. Extend freely -- an explicit mapping is
# always preferable to a lucky guess.
WIKI_OVERRIDES = {
    "Dragon Ball Z": "dragonball",
    "The Amazing Digital Circus": "the-amazing-digital-circus",
    "Curse of Strahd": "forgottenrealms",
    "Descent into Avernus": "forgottenrealms",
    "Ghosts of Saltmarsh": "forgottenrealms",
    "Hoard of the Dragon Queen": "forgottenrealms",
    "Fist of the North Star": "hokuto",
    "JoJo's Bizarre Adventure": "jojo",
    "Kinnikuman": "kinnikuman",
    "Getter Robo": "getterrobo",
    # Added after a resolution sweep left these unresolved: the subdomain simply is not
    # derivable from the roll's name for them.
    "The Amazing World of Gumball": "theamazingworldofgumball",
    "Heaven's Lost Property": "sorakake",
    "HAWX": "tomclancy",
    "all the Fate series": "typemoon",
    "the FFXIV / Eorzea conversion": "finalfantasy",
    "Twilight Imperium": "twilight-imperium",
    "the Lovecraftian mythos": "lovecraft",
    "major live-action Disney films": "disney",
    "Who Framed Roger Rabbit (incl. all content from its associated crossover-toon IPs)":
        "disney",
    "the Root Companions": "root-boardgame",
}

# Some roll sources are not a single work with a single wiki -- they are cross-media
# categories. Cataloguing them from one wiki is simply wrong: "major fantasy pantheons"
# pointed at forgottenrealms would return Forgotten Realms deities and call it the field.
#
# For these, name the wikis and the deity/pantheon categories explicitly and merge. Note the
# roll ALREADY carries thirteen "Pantheon: <culture>" sources covering real-world mythology
# (Greek 606 entries, Hindu 757, Egyptian 641, Norse 394, Roman 476, ...), so this source is
# specifically the INVENTED pantheons of fiction, not the historical ones.
COMPOSITE_SOURCES = {
    "major fantasy pantheons": [
        ("marvel", ["Gods", "Asgardians", "Olympians"]),
        ("godofwar", ["Gods", "Greek Gods", "Norse Gods"]),
        ("elderscrolls", ["Deities", "Aedra", "Daedra", "Divines"]),
        ("finalfantasy", ["Deities", "Gods"]),
        ("zelda", ["Deities", "Goddesses"]),
        ("riordan", ["Gods", "Greek Gods", "Egyptian Gods", "Norse Gods"]),
        ("genshin-impact", ["Archons", "Gods"]),
        ("smite", ["Gods"]),
        ("warhammerfantasy", ["Gods", "Deities"]),
        ("hades", ["Olympians", "Gods"]),
        # "Characters" was tried here too and dropped: on this wiki it returns the human
        # combatants alongside the gods, and this source is the pantheons specifically.
        ("shuumatsunovalkyrie", ["Gods"]),
        ("saintseiya", ["Gods", "Deities"]),
        ("witcher", ["Deities", "Gods"]),
        # dragonage and darksiders were tried and have no matching deity category; darksiders
        # is its own roll source in any case.
    ],
}

# Maps our seven canonical categories to the keywords that identify a matching wiki category.
# Wiki category naming is wildly inconsistent, so we match loosely and let the model make the
# final call per entity.
CATEGORY_KEYWORDS = {
    # The first seven words here are what a comics wiki calls its cast. The rest are what
    # everybody else calls theirs, and without them a whole source can come back empty or, worse,
    # come back with the wrong thing: the wrestling wiki has no category matching any of
    # "character/people/person/protagonist/antagonist/villain/hero" that holds wrestlers, so its
    # roster resolved to 158 COUNTRIES. Its actual cast is under "Male wrestlers" (13,314) and
    # "Female wrestlers" (4,194). A role noun IS a person noun on most wikis, and the ones below
    # are drawn from the categories real wikis on the roll actually use.
    "Persons (named individual characters, real or fictional)":
        ["character", "people", "person", "protagonist", "antagonist", "villain", "hero",
         "wrestler", "fighter", "warrior", "soldier", "pilot", "knight", "mage", "wizard",
         "ninja", "shinobi", "pirate", "saiyan", "deity", "deities", "god", "goddess",
         "demon", "angel", "vampire", "mutant", "alien", "monster", "creature", "npc",
         "cast", "roster", "individual", "inhabitant", "resident", "citizen", "member",
         "survivor", "champion", "wrestlers", "humans", "males", "females"],
    "Places & Locations (worlds, regions, cities, planes, ships-as-places)":
        ["location", "place", "city", "cities", "region", "world", "planet", "realm", "area"],
    "Vessels & Things (items, vehicles, weapons, artifacts, notable objects)":
        ["item", "weapon", "artifact", "object", "equipment", "vehicle", "ship", "tool"],
    "Factions & Organizations (groups, nations, guilds, companies, orders)":
        ["organization", "organisation", "faction", "group", "clan", "guild", "nation",
         "military", "team"],
    "Powers, Abilities & Systems (magic systems, power systems, tech systems, disciplines)":
        ["abilit", "power", "technique", "magic", "spell", "skill", "jutsu", "quirk"],
    "Events (major storyline events, wars, historical turning points within the fiction)":
        ["event", "war", "battle", "arc", "conflict", "incident"],
    "Media (in-fiction media: books, songs, broadcasts, works that exist within the story itself)":
        ["in-universe media", "fictional book", "in-universe book", "song", "broadcast"],
}

import threading  # noqa: E402
from concurrent.futures import ThreadPoolExecutor  # noqa: E402
import silence

_last_call = [0.0]
_rate_lock = threading.Lock()

# Seconds between request starts, enforced globally across threads. With WORKERS in flight
# this is a throughput floor, not a per-thread stall: at 0.08s the pool sustains ~12 req/s,
# which is polite for Fandom and roughly 4x the old serial 0.35s gap.
#
# Measured on Bleach, 40 pages, identical success rate (37/40) at every setting -- so the
# higher concurrency is costing nothing in reliability:
#     serial (old, 0.35s gap)  0.450 s/page
#     8 workers  @ 0.08s       0.159 s/page
#     16 workers @ 0.04s       0.081 s/page
# and again on Naruto, 60 pages, 60/60 retrieved at every level (no rate-limit damage):
#     16 workers @ 0.04s       0.065 s/page
#     32 workers @ 0.02s       0.044 s/page
#     48 workers @ 0.01s       0.033 s/page   <- 13.6x faster than serial
# Gains are clearly flattening past 32; raise further only with evidence. 429s from Fandom
# would surface as retries in _get and as a falling success ratio here.
MIN_GAP = 0.01
WORKERS = 48


def _get(url, timeout=25, retries=2):
    """GET with a real user-agent and global rate limiting (courtesy to Fandom).

    The gap is held under a lock so concurrent workers cannot bunch their requests; each
    thread waits its turn to *start*, then overlaps its network wait with everyone else's.
    That overlap is the entire speedup -- these calls are latency-bound, not CPU-bound.
    """
    for attempt in range(retries + 1):
        with _rate_lock:
            gap = time.time() - _last_call[0]
            if gap < MIN_GAP:
                time.sleep(MIN_GAP - gap)
            _last_call[0] = time.time()
        try:
            req = urllib.request.Request(url, headers=UA)
            with urllib.request.urlopen(req, timeout=timeout) as r:
                return r.read().decode("utf-8", "replace")
        except urllib.error.HTTPError as e:
            silence.note("wiki_source.py:155")
            if e.code in (429, 503) and attempt < retries:
                time.sleep(2 + attempt * 3)
                continue
            raise
        except Exception:
            silence.note("wiki_source.py:160")
            if attempt < retries:
                time.sleep(1.5)
                continue
            raise


def _api(subdomain, params, timeout=25):
    params = dict(params, format="json")
    url = f"https://{subdomain}.fandom.com/api.php?" + urllib.parse.urlencode(params)
    return json.loads(_get(url, timeout=timeout))


def subdomain_candidates(source_name):
    n = re.sub(r"\(.*?\)", " ", source_name.lower())
    n = re.sub(r"\bincl\..*$", "", n)
    n = re.sub(r"^(all|the)\s+", "", n.strip())
    n = re.sub(r"\s+(games?|series|franchise|films?|movies?)\b", " ", n)
    words = re.findall(r"[a-z0-9]+", n)
    if not words:
        return []
    out = ["".join(words), "-".join(words)]
    if len(words) > 1:
        out.append("".join(words[:2]))
    out.append(words[0])
    return list(dict.fromkeys(out))


def verify_wiki_matches(subdomain, source_name):
    """Does this wiki actually contain the source? Guards against confident wrong resolution.

    The motivating case: `curse.fandom.com` returns HTTP 200 and a healthy sitename for the
    query "Curse of Strahd", but it is the Roblox CURSE Wiki. A 200 proves a wiki exists, not
    that it is the right one. Searching it for the source's own distinctive words does prove
    that -- a Ravenloft wiki knows "Strahd"; a Roblox wiki does not.
    """
    stop = {"all", "the", "of", "and", "a", "incl", "its", "associated"}
    words = [w for w in re.findall(r"[A-Za-z0-9']+", source_name) if w.lower() not in stop]
    if not words:
        return False, 0
    query = " ".join(words[:4])
    try:
        d = _api(subdomain, {"action": "query", "list": "search", "srsearch": query,
                             "srlimit": 8})
    except Exception:
        silence.note("wiki_source.py:204")
        return False, 0
    hits = d.get("query", {}).get("search", [])
    if not hits:
        return False, 0
    # Require a distinctive word from the source to appear in a result title or snippet.
    distinctive = [w.lower() for w in words if len(w) > 3]
    if not distinctive:
        distinctive = [w.lower() for w in words]
    blob = " ".join((h.get("title", "") + " " + re.sub(r"<[^>]+>", "", h.get("snippet", "")))
                    for h in hits).lower()
    matched = sum(1 for w in distinctive if w in blob)
    return matched >= max(1, len(distinctive) // 2), len(hits)


def resolve_wiki(source_name):
    """Return (subdomain, sitename) for a verified wiki, or (None, None).

    THE LIBRARY'S OWN HOST MAP IS CONSULTED FIRST. This function guessed subdomains and
    verified each guess over the network -- while data/WIKI_HOSTS.json, sitting on the same
    disk, has known for days that DC is dc.fandom.com and Marvel is marvel.fandom.com. The
    guess-list happened not to contain 'dc' (too short for the slug generator), the verifier
    got nothing to verify, and the re-catalogue SKIPPED the two largest sources on the roll
    with 'no wiki resolved' -- a resolver failing to resolve a host the library had already
    resolved, recorded, and mined 380 feat files from.
    """
    cands = []
    try:
        with open(os.path.join(HERE, "data", "WIKI_HOSTS.json"), encoding="utf-8") as f:
            known = json.load(f).get(source_name)
        if isinstance(known, str) and known.endswith(".fandom.com"):
            cands.append(known[: -len(".fandom.com")])
    except Exception:
        silence.note("wiki_source.py:resolve-known")
    if source_name in WIKI_OVERRIDES:
        cands.append(WIKI_OVERRIDES[source_name])
    cands += [c for c in subdomain_candidates(source_name) if c not in cands]

    for c in cands:
        try:
            d = _api(c, {"action": "query", "meta": "siteinfo"}, timeout=20)
        except Exception:
            silence.note("wiki_source.py:229")
            continue
        sitename = d.get("query", {}).get("general", {}).get("sitename")
        if not sitename:
            continue
        ok, _ = verify_wiki_matches(c, source_name)
        if ok:
            return c, sitename
    return None, None


# Category titles to probe directly, per canonical bucket. Probing beats searching: a
# namespace-14 search for "character" matches page CONTENT and comes back with 'Help',
# 'Music' and 'Families', while asking a wiki straight out whether it has a category called
# "Characters" is exact and costs one call. Wikis that use none of these names simply yield
# nothing for that bucket, which is the honest result.
CATEGORY_PROBES = {
    "Persons (named individual characters, real or fictional)":
        ["Characters", "People", "Protagonists", "Antagonists", "Villains", "Heroes",
         "Major Characters", "Playable characters"],
    "Places & Locations (worlds, regions, cities, planes, ships-as-places)":
        ["Locations", "Places", "Cities", "Regions", "Worlds", "Planets", "Realms",
         "Countries", "Settlements"],
    "Vessels & Things (items, vehicles, weapons, artifacts, notable objects)":
        ["Items", "Weapons", "Artifacts", "Equipment", "Vehicles", "Ships", "Objects",
         "Armor", "Technology"],
    "Factions & Organizations (groups, nations, guilds, companies, orders)":
        ["Organizations", "Organisations", "Factions", "Groups", "Clans", "Guilds",
         "Nations", "Teams", "Militaries"],
    "Powers, Abilities & Systems (magic systems, power systems, tech systems, disciplines)":
        ["Techniques", "Abilities", "Powers", "Magic", "Spells", "Skills", "Combat",
         "Power Systems"],
    "Events (major storyline events, wars, historical turning points within the fiction)":
        ["Events", "Battles", "Wars", "Arcs", "Story Arcs", "Conflicts"],
    "Media (in-fiction media: books, songs, broadcasts, works that exist within the story itself)":
        ["In-universe media", "Books", "Songs", "Publications", "Documents"],
}


# Meta-categories that group OTHER categories rather than holding subjects. Walking one of
# these catalogues the grouping instead of the group, and the result looks like a real roster.
#
# This is not hypothetical. 'Professional Wrestling: WWE/WCW/AAA/NXT/ECW/TNA/AEW' was catalogued
# with 158 entries and every one of them is a COUNTRY -- Afghanistan, Albania, Argentina,
# Armenia, Australia -- because a nationality grouping was walked and its country articles were
# taken as the cast. That wiki's actual wrestlers live in 'Male wrestlers' (13,314) and 'Female
# wrestlers' (4,194), neither of which any probe in CATEGORY_PROBES would ever have guessed.
_META_CATEGORY = re.compile(
    r"\bby (nationality|country|year|decade|type|company|promotion|brand)\b|"
    r"^(lists?|index|indices|stubs?|templates?|images?|galleries|files)\b|"
    r"\b(stubs?|templates?|images?|disambiguation)\b", re.I)


_ALLCATS = {}
_ALLCATS_LOCK = threading.Lock()


def all_categories(subdomain, min_pages=40, hard_stop=6000):
    """[(size, name)] for every category on a wiki holding at least `min_pages` pages.

    CACHED PER (SUBDOMAIN, MIN_PAGES), and it has to be. `find_categories` calls this once for
    each of the seven canonical classes, so an uncached version walks a wiki's entire category
    listing seven times per source -- on Marvel that is seven full traversals before a single
    entity is fetched, and the catalogue run appears to hang. The listing does not change
    between those seven calls.

    `hard_stop` bounds the API walk, not the answer: it exists so a wiki with a hundred thousand
    year-buckets cannot spin here forever.
    """
    key = (subdomain, min_pages)
    with _ALLCATS_LOCK:
        if key in _ALLCATS:
            return _ALLCATS[key]

    out, cont = [], None
    while len(out) < hard_stop:
        p = {"action": "query", "list": "allcategories", "aclimit": 500,
             "acmin": min_pages, "acprop": "size"}
        if cont:
            p["accontinue"] = cont
        try:
            d = _api(subdomain, p)
        except Exception:
            silence.note("wiki_source.py:all_categories")
            break
        for c in d.get("query", {}).get("allcategories", []):
            name = c.get("*") or ""
            if name and not _META_CATEGORY.search(name):
                out.append((c.get("pages", 0), name))
        cont = d.get("continue", {}).get("accontinue")
        if not cont:
            break
    with _ALLCATS_LOCK:
        _ALLCATS[key] = out
    return out


def discover_categories(subdomain, canonical_category, min_pages=40):
    """Categories this wiki ACTUALLY has that match the canonical category's keywords.

    The fixed probe list assumes every wiki names things the way Marvel's does. Most do not, and
    when the guess misses, the source gets no category at all for that whole class -- or worse,
    falls through to something adjacent and wrong.
    """
    keys = [k.lower() for k in CATEGORY_KEYWORDS[canonical_category]]
    hits = []
    for size, name in all_categories(subdomain, min_pages=min_pages):
        low = name.lower()
        if any(k in low for k in keys):
            hits.append((size, name))
    hits.sort(reverse=True)
    return hits


def find_categories(subdomain, canonical_category, limit=None, discover=True, min_pages=40):
    """Every category on this wiki that holds subjects of the given canonical class.

    `limit` defaults to None. It was 6, which quietly discarded whatever a wiki held past its
    sixth matching category -- and since the probe list is ordered by guesswork rather than by
    size, the six kept were not the six largest. Hard Rule 0: rank, never truncate.
    """
    found = []
    for cand in CATEGORY_PROBES[canonical_category]:
        try:
            d = _api(subdomain, {"action": "query", "list": "categorymembers",
                                 "cmtitle": f"Category:{cand}", "cmlimit": 3,
                                 "cmnamespace": 0})
        except Exception:
            silence.note("wiki_source.py:278")
            continue
        if d.get("query", {}).get("categorymembers"):
            found.append(cand)

    if discover:
        have = {f.lower() for f in found}
        for _size, name in discover_categories(subdomain, canonical_category,
                                               min_pages=min_pages):
            if name.lower() not in have:
                found.append(name)
                have.add(name.lower())

    return found[:limit] if limit else found


def page_text(subdomain, title, max_chars=900):
    """Lead-section prose for one page, via action=parse.

    Fandom does not install the TextExtracts extension, so prop=extracts returns nothing and
    the /api/v1/Articles/Details abstract endpoint answers 403. Parsing section 0 to HTML and
    stripping tags is the route that actually works. Infobox and quote-box text comes along
    with it; that is acceptable, since the model reads this as evidence rather than copying it.
    """
    # Sections are tried in order because section 0 is frequently just a pull-quote on these
    # wikis -- "Renji Abarai" and "Asauchi" have nothing else in it. Section 1 (Appearance /
    # Overview / History) carries the actual description. Fetching the whole page instead would
    # work but costs ~420KB per article, which over tens of thousands of pages is absurd.
    for section in (0, 1, 2):
        try:
            d = _api(subdomain, {"action": "parse", "page": title, "prop": "text",
                                 "section": section, "redirects": 1}, timeout=40)
        except Exception:
            silence.note("wiki_source.py:301")
            return ""
        text = _paragraphs(d.get("parse", {}).get("text", {}).get("*", ""), max_chars)
        if text:
            return text
    return ""


def page_texts(subdomain, titles, max_chars=900, workers=None):
    """Fetch lead prose for many pages concurrently. Returns {title: text}.

    Page fetching dominates runtime and is pure network wait, so running it in a pool is the
    single biggest speedup available -- serially at one request per 0.35s a 300-entity source
    spent minutes doing nothing but waiting.
    """
    out = {}
    if not titles:
        return out
    with ThreadPoolExecutor(max_workers=workers or WORKERS) as pool:
        for title, text in zip(titles, pool.map(
                lambda t: page_text(subdomain, t, max_chars), titles)):
            if text:
                out[title] = text
    return out


def _paragraphs(html, max_chars):
    # Drop the furniture before flattening: infoboxes are <table>/<aside>, quote boxes and
    # navboxes are <div>s with tell-tale classes. Without this the "description" comes back as
    # "Sousuke Aizen Muken Post-Defection Race Soul Birthday May 29 Gender Male Height 186 cm",
    # which is infobox fields concatenated, not prose.
    # Pull <p> elements BEFORE removing anything. Two earlier attempts failed here and both
    # failures looked like "the page has no text":
    #   - stripping <div> by class: nested divs make a non-greedy match close at the wrong tag
    #   - stripping <table>: these wikis wrap the WHOLE article in <center><table>, so removing
    #     tables removed the article
    # Infobox fields and captions are not inside <p>, so paragraph extraction already excludes
    # them without deleting anything.
    paras = re.findall(r"<p\b[^>]*>(.*?)</p>", html, flags=re.S | re.I)

    out = []
    for c in paras:
        t = re.sub(r"<[^>]+>", " ", c)
        t = re.sub(r"&#?\w+;", " ", t)
        t = re.sub(r"\[\d+\]", " ", t)
        t = re.sub(r"\s+", " ", t).strip()
        if len(t) < 45 or "." not in t:
            continue
        # Character pages routinely open with a pull-quote rather than a definition. A quote is
        # not a description, so skip anything that is mostly quoted speech.
        if t.lstrip().startswith(('"', "“", "'")) or t.count('"') + t.count("“") >= 2:
            continue
        out.append(t)
        if sum(len(x) for x in out) >= max_chars:
            break
    return " ".join(out)[:max_chars]


def category_members(subdomain, category, limit=None):
    """Every page in a category. `limit=None` means every page, which is the intended use.

    Hard Rule 0: a cap on a category listing is a truncation, not a sample, because MediaWiki
    returns categories ALPHABETICALLY. A limit of 200 on DC's 33,614-member character category
    returns Abin Sur through Adolf Hitler and reports it as the roster.
    """
    out, cont = [], None
    while limit is None or len(out) < limit:
        p = {"action": "query", "list": "categorymembers",
             "cmtitle": f"Category:{category}",
             "cmlimit": 500 if limit is None else min(500, limit - len(out)),
             "cmnamespace": 0}
        if cont:
            p["cmcontinue"] = cont
        try:
            d = _api(subdomain, p)
        except Exception:
            silence.note("wiki_source.py:376")
            break
        out += [m["title"] for m in d.get("query", {}).get("categorymembers", [])]
        cont = d.get("continue", {}).get("cmcontinue")
        if not cont:
            break
    return out


def extracts(subdomain, titles, chars=700):
    """Intro text for up to 20 pages per call -- the real article prose."""
    out = {}
    for i in range(0, len(titles), 20):
        batch = titles[i:i + 20]
        try:
            d = _api(subdomain, {"action": "query", "prop": "extracts", "exintro": 1,
                                 "explaintext": 1, "exchars": chars,
                                 "titles": "|".join(batch), "redirects": 1}, timeout=40)
        except Exception:
            silence.note("wiki_source.py:394")
            continue
        for page in d.get("query", {}).get("pages", {}).values():
            if "extract" in page and page.get("title"):
                txt = re.sub(r"\s+", " ", page["extract"]).strip()
                if txt:
                    out[page["title"]] = txt
    return out


def rank_by_size(subdomain, titles, top=None):
    """Order titles by article byte-length, longest first.

    Category listings come back ALPHABETICALLY. Taking the first N off a big category is
    therefore not a sample, it is the letter A -- capping Bleach's 1,000+ characters at 90
    produced a catalogue that stopped at surnames beginning "C" and omitted Ichigo Kurosaki,
    the protagonist. Article length is a blunt but reliable proxy for significance: main
    characters have long pages, walk-ons have stubs. One `prop=info` call covers 50 titles, so
    ranking a whole category costs a handful of requests.
    """
    batches = [titles[i:i + 50] for i in range(0, len(titles), 50)]

    def fetch(batch):
        try:
            return _api(subdomain, {"action": "query", "prop": "info",
                                    "titles": "|".join(batch), "redirects": 1}, timeout=40)
        except Exception:
            silence.note("wiki_source.py:420")
            return {}

    sizes = {}
    # Ranking a 1,200-title category is 24 batches; running them in the pool turns 24 serial
    # round trips into roughly one.
    with ThreadPoolExecutor(max_workers=min(WORKERS, max(1, len(batches)))) as pool:
        for d in pool.map(fetch, batches):
            for page in d.get("query", {}).get("pages", {}).values():
                t = page.get("title")
                if t and "length" in page:
                    sizes[t] = page["length"]
    ranked = sorted(titles, key=lambda t: -sizes.get(t, 0))
    return ranked[:top] if top else ranked


def clean_titles(titles):
    """Drop subpages and disambiguation cruft that carry no entity of their own.

    Wiki category listings are full of entries like "Renji Abarai/Anime Continuity" -- a
    subpage of a character already listed. Keeping them produces duplicate entries under
    slightly different names, which is exactly the near-duplicate problem the cataloguer is
    trying to avoid.
    """
    out = []
    for t in titles:
        if "/" in t:
            continue
        if re.search(r"\((disambiguation|list)\)", t, re.I):
            continue
        if t not in out:
            out.append(t)
    return out
