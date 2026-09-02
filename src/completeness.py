#!/usr/bin/env python3
"""COMPLETENESS — how much of each source's cast the library actually holds.

WHY THIS EXISTS
---------------
`catalogue_web.py` carried `MAX_PER_SOURCE = 320`, a per-source ceiling that trimmed each
source's cast proportionally across its categories. The proportional trim is what made it
invisible: it kept a plausible spread of Persons and Places and Things, so the result had the
same SHAPE as a complete catalogue and nothing downstream could tell the difference.

The measured damage, from the wikis' own `categoryinfo`:

    marvel.fandom.com   Category:Characters   103,554 pages    catalogued 1,051    1.0%
    dc.fandom.com       Category:Characters    33,615 pages    catalogued   377    1.1%

Molecule Man, Mister Mxyzptlk and the Black Winter were all outside those windows. Every one of
them reads, from inside the library, as "not in that fiction" rather than "past the cutoff" --
which is Hard Rule 0's whole thesis, demonstrated three times in one afternoon by an owner
asking after four characters.

WHAT THIS DOES
--------------
Asks each source's wiki how many pages its categories ACTUALLY hold, using `prop=categoryinfo`
-- one cheap call per category, no enumeration required -- and prints that against what the
library catalogued. It answers a question the library could not previously ask about itself:
not "did the catalogue run", but "did it get everything, and if not, how much is missing".

It never truncates anything, and it writes no catalogue. It is a measurement.
"""
import argparse
import json
import os
import threading
import time
import sys
import collections
import urllib.parse
from concurrent.futures import ThreadPoolExecutor

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import wiki_source as ws                                                # noqa: E402
import silence                                                          # noqa: E402

_BAD_CHARS = (chr(8), chr(11), chr(12), chr(7))
if any(c in open(os.path.abspath(__file__), encoding="utf-8").read() for c in _BAD_CHARS):
    raise SystemExit(__file__ + ": a regex escape was eaten in transit.")

OUT = os.path.join(HERE, "data", "COMPLETENESS.json")

# A landing run must carry at least this fraction of the rows already on disk. 0.5 is deliberately
# generous: it exists to catch a broken run (transport collapse, a truncated hosts file, an audit
# that measured almost nothing), not to freeze the roll. `[]` is the degenerate case of it.
SHRINK_FLOOR = 0.5
HOSTS = os.path.join(HERE, "data", "WIKI_HOSTS.json")
RECORDS = os.path.join(HERE, "data", "records")

PERSONS = "Persons (named individual characters, real or fictional)"


def subdomain(host):
    """'dc.fandom.com' -> 'dc'. Non-fandom hosts have no category API we can use this way."""
    if not isinstance(host, str) or not host.endswith(".fandom.com"):
        return None
    return host[: -len(".fandom.com")]


# `pages:<source>` and `doc:<slug>` are PROVENANCE SENTINELS, not hosts: an owner-supplied
# document or a hand-registered page list, recorded in the same column because that column is
# "where this source's material comes from". The project's own idiom for telling them apart is
# `str(h).startswith(("pages:", "doc:"))` -- binding_health.py:1018 and health.py:486-488 both
# do exactly this, and health.py's comment says why: probing one as a host is meaningless.
SENTINELS = ("pages:", "doc:")


def wiki_host(host):
    """Is this a hostname that can be ASKED something? -> bool.

    Added with the 196-source admission below. The audit now sees values that were previously
    filtered out one line earlier, and two of them must never reach the network: a sentinel
    (`pages:all Creeper World`) and a missing host (None). Resolving either through
    `endpoint.detect` would spend a DNS lookup on a phrase and then cache a DEAD verdict for a
    host that does not exist, which is a fabricated fact about a source that never had a wiki.
    """
    if not isinstance(host, str):
        return False
    h = host.strip()
    if not h or h.startswith(SENTINELS):
        return False
    return "." in h and ":" not in h and "/" not in h and not any(c.isspace() for c in h)


_CS_CACHE_P = os.path.join(HERE, "state", "category_sizes.json")
_CS_CACHE = {"loaded": False, "d": {}}
_CS_TTL = 12 * 3600


_CS_LOCK = threading.Lock()


def _cs_load():
    with _CS_LOCK:
        if not _CS_CACHE["loaded"]:
            try:
                with open(_CS_CACHE_P, encoding="utf-8") as f:
                    _CS_CACHE["d"] = json.load(f)
            except Exception:
                _ = "silence-exempt: no cache yet is the normal first state"
            _CS_CACHE["loaded"] = True
        return _CS_CACHE["d"]


def _cs_put(k, n):
    """Record one probe result in the 12h category-size cache, from any of the audit's threads.

    TWO WRITERS, ONE SCRATCH FILE (order 771fc3b0f517, run #36). Both probe functions below wrote
    this through a fixed `_CS_CACHE_P + '.tmp'`, from up to six `ThreadPoolExecutor` workers at
    once: every one of them opened the SAME temp file for writing, so the second truncated the
    first and whichever renamed second could land a half-written cache over the target. That is
    the two-writers-one-temp-filename shape that has cost this project real data twice.
    `silence.write_json` carries pid and thread in the temp name, which makes it unavailable to
    get wrong, and it is what the rest of the tree already uses.

    AND THE DICT WAS BEING SERIALISED WHILE THE OTHER WORKERS INSERTED INTO IT. `_CS_CACHE['d']`
    is one dict shared by every worker; `json.dump` iterates it, and an insertion during that
    iteration raises `RuntimeError: dictionary changed size during iteration` straight into the
    blanket `except` below -- the probe result silently uncached, the wiki asked again next round.
    Same shape as `health.flush()` (order f46fbdf61e31) and the same remedy: mutate and SNAPSHOT
    under a lock, then serialise the snapshot, which nothing else can touch.

    Still MINOR, and the reason stands: a lost or torn cache re-reads as empty and costs one live
    category call to re-earn. That is why this is a temp-name fix and not a compare-and-swap --
    across processes the loser's entries are simply re-probed, and a retry loop here would pace
    against the domain that has IP-banned this machine once already for no data that is at risk.

    `indent=None` keeps the file compact: this holds one row per (host, category) pair across the
    whole roll, and it is a cache nobody reads by eye.
    """
    cache = _cs_load()
    with _CS_LOCK:
        cache[k] = {"at": time.time(), "n": n}
        snap = dict(cache)
    try:
        # THE VERDICT IS DELIBERATELY NOT GATED HERE, and this comment is the repair rather than
        # a check (run #37's discarded-write-verdict pass; the same pass gated address_space,
        # allsweep, cleanup, corpus_db, feats and generate, and stopped here).
        #
        # `write_json` returns False rather than raising when the atomic replace is denied, so
        # the `except` below covers the SERIALISATION only -- reading it as "the write outcome is
        # handled" would be the mistake. The outcome is genuinely ignorable: this file is a 12h
        # scratch cache of category sizes and NOTHING reads it but `_cs_load` in this module. A
        # denial costs one repeated `category_size` call and cannot make any answer wrong -- a
        # miss re-probes, and the probe is the authority in either case. The reason not to make
        # noise is in the docstring above: the retry pressure would land on a domain that has
        # IP-banned this machine once already, for data that is not at risk.
        #
        # A PERSISTENT DENIAL IS STILL VISIBLE where it belongs: `silence.replace_retry` records
        # `replace-denied:<file>` in the health ledger on its own, so a lock that never clears
        # shows up without this caller inventing a second channel for it.
        silence.write_json(_CS_CACHE_P, snap, indent=None)
    except Exception:
        silence.note("completeness.py:cs-cache")


def category_size_probe(sub, category):
    """`category_size` with its failure visible: returns `(n, error)`.

    Added 2026-08-23 (BUGS m3). `category_size` answers `None` for two opposite situations --
    "this wiki has no such category" and "this wiki did not answer" -- and the audit below,
    which only ever saw the `None`, dropped an all-errors source out of COMPLETENESS.json
    entirely. A missing row reads as a source with nothing to catalogue, which is the exact
    inversion of what a transport failure means. 313 URLErrors were recorded at this site as of
    run #2, all of them silently deciding a row did not exist.

    `category_size` stays as it was -- but for NO caller, which is the part this sentence used
    to get wrong. It read "for every caller that only wants the number", true when this function
    was split out of it in the m3 fix and a comment about an empty set ever since: grepping
    `category_size` (excluding this name) finds only its own `def` and docstring mentions. A
    stale claim of callers is load-bearing here, because the next reader takes it as evidence
    that something depends on the None-means-two-things behaviour and leaves it alone.
    (order 551256c7dc68)"""
    d = _cs_load()
    k = sub + "|" + category
    hit = d.get(k)
    if hit and time.time() - hit.get("at", 0) < _CS_TTL:
        return hit.get("n"), None
    try:
        d = ws._api(sub, {"action": "query", "titles": "Category:" + category,
                          "prop": "categoryinfo"})
    except Exception as e:
        silence.note("completeness.py:category_size")
        return None, type(e).__name__
    got = None
    for p in (d.get("query", {}).get("pages", {}) or {}).values():
        ci = p.get("categoryinfo")
        if ci:
            got = ci.get("pages", 0)
            break
    _cs_put(k, got)
    return got, None


def category_size(sub, category):
    """How many pages a category holds, per the wiki itself. One call, no enumeration --
    and CACHED 12h to disk: the always-remedy runs this audit every foreman round, and
    uncached that was ~1,300 live calls per half hour to the domain that has IP-banned this
    machine once already (round-2 optimization audit, finding 3). Category counts move on a
    days clock; the standard's job is to keep the shortfall visible, not to re-ask fandom
    the same question 48 times a day.

    NO CALLER TODAY; KEPT AS THE PLAIN-NUMBER FORM (order 551256c7dc68). Every call site moved
    to `category_size_probe` when the m3 fix split the error out, and `liveness.py` reports this
    function as dead. It is not deleted: the house rule is that a public function is not removed
    by a maintenance pass, and this is the one-line form a hand-run query wants. Said in the
    present tense so the next sweep re-finds the fact rather than the function. If you are
    adding a caller, use `category_size_probe` -- `None` here means BOTH "no such category" and
    "the wiki did not answer", and that ambiguity is what dropped an all-errors source out of
    COMPLETENESS.json entirely."""
    return category_size_probe(sub, category)[0]


def api_base(host):
    """The MediaWiki API base for a non-fandom host, or None. -> str|None.

    Through `endpoint.api_url`, never hardcoded, for the reason `host_reachable` states below:
    `/api.php` is a Fandom assumption and Wikipedia serves `/w/api.php`. A host whose mode is
    RAW or DEAD has no API and answers None here -- which is a different fact from "the probe
    failed", and the caller reports it as a different fact.
    """
    try:
        import endpoint as EP
        return EP.api_url(host)
    except Exception:
        silence.note("completeness.py:api-base")
        return None


def category_size_probe_host(host, category):
    """`category_size_probe` for a wiki that is not on fandom. -> (n, error).

    `wiki_source._api` hardcodes `https://{subdomain}.fandom.com/api.php` -- correctly, it is
    the fandom transport -- so it cannot ask en.wikipedia.org or rimworldwiki.com the same
    question. This asks it over `endpoint`, which already resolves each host's own API path and
    carries the project's User-Agent (a bare urllib request is answered 403 by both Wikipedia
    and Fandom, which would report every host on earth as unmeasurable).

    Cached in the SAME 12h file as the fandom probe, keyed by full host rather than subdomain --
    which matters more here than there: 22 sources share en.wikipedia.org, so a per-source cache
    would ask Wikipedia the identical eight questions 22 times per audit, and this audit runs
    every foreman round.
    """
    d = _cs_load()
    k = host + "|" + category
    hit = d.get(k)
    if hit and time.time() - hit.get("at", 0) < _CS_TTL:
        return hit.get("n"), None
    base = api_base(host)
    if not base:
        return None, "NoAPI"
    try:
        import endpoint as EP
        q = urllib.parse.urlencode({"action": "query", "format": "json",
                                    "prop": "categoryinfo",
                                    "titles": "Category:" + category})
        j = json.loads(EP._get(base + "?" + q))
    except Exception as e:
        silence.note("completeness.py:category_size_host")
        return None, type(e).__name__
    got = None
    for p in ((j.get("query", {}) or {}).get("pages", {}) or {}).values():
        ci = p.get("categoryinfo") if isinstance(p, dict) else None
        if ci:
            got = ci.get("pages", 0)
            break
    _cs_put(k, got)
    return got, None


def catalogued_counts():
    """{source slug: {category-ish: n}} from what is on disk."""
    out = {}
    for fn in os.listdir(RECORDS):
        if not fn.endswith(".json"):
            continue
        try:
            with open(os.path.join(RECORDS, fn), encoding="utf-8") as f:
                j = json.load(f)
        except Exception:
            silence.note("completeness.py:record")
            continue
        c = collections.Counter()
        for e in (j.get("entries") or []):
            c[str(e.get("category") or "?")[:40]] += 1
        out[j.get("source") or fn[:-5]] = {"total": sum(c.values()), "by_category": dict(c),
                                           "file": fn}
    return out


_REACH = {}


def host_reachable(host, timeout=8):
    """Is `host` answering its API right now? One short probe, cached per host per process.

    Asked ONCE per host with a short timeout, instead of 8 category probes each discovering the
    same outage the slow way. Under the 2026-08-24 block a category probe took ~42s to fail, so
    a blocked source cost ~5.6 minutes of guaranteed failure; this replaces that with one 8s
    question whose answer is the same.

    This exists so the audit can be RUN during a block rather than deferred. Deferring the whole
    audit was the previous answer and it had a worse failure mode than the one it fixed: the
    foreman gated the entire pass on fandom being up, so while fandom was down COMPLETENESS.json
    -- already emptied to `[]` by the bug run #5 fixed -- could never be rewritten by anything,
    and the HIGH `every source is fully catalogued` standard read UNMEASURED indefinitely. A
    measurement that cannot be retaken is not deferred, it is abandoned.

    IT IS AN HTTP PROBE, NOT A SOCKET PROBE, and that distinction is the whole point. Measured
    2026-08-24 during the live block: `socket.create_connection(("community.fandom.com", 443))`
    succeeded INSTANTLY while `GET marvel.fandom.com/api.php` returned nothing after 21.3
    seconds. The edge accepts the TCP handshake and then drops the request, so a socket probe
    reports a blocked domain as healthy -- which is exactly what `foreman._fandom_reachable`
    was doing, meaning the gate built to defer this audit had been answering "reachable"
    throughout the outage it existed to detect. Ask the API the question the caller actually
    cares about.

    The API PATH is resolved through `endpoint.api_url`, never hardcoded: this project already
    learned that `/api.php` is a Fandom assumption and that plenty of wikis (Wikipedia among
    them) serve `/w/api.php` instead -- see endpoint.py's own header. Hardcoding `/api.php` here
    reported en.wikipedia.org as unreachable while curl fetched it in 0.16s, which would have
    marked all 21 Wikipedia-hosted sources unreliable for no reason."""
    if not host:
        return False
    if host in _REACH:
        return _REACH[host]
    # PER HOST, NOT PER DOMAIN. Measured 2026-08-24: community.fandom.com answered in 0.2s
    # while marvel / dc / onepiece.fandom.com each failed after 42s, in the same second, from
    # this machine. The block is per-tenant, so asking the farm is worse than asking nothing --
    # it would pronounce all 164 fandom sources healthy and then walk each one into eight
    # 42-second failures. The farm being up says nothing about the tenant.
    try:
        import endpoint as EP
        # A RAW-MODE WIKI IS NOT AN UNREACHABLE WIKI. Fixed run #28.
        #
        # This asked `api_url(host)` and treated None as "unreachable". But `api_url` returns
        # None for MODE_RAW exactly as it does for MODE_DEAD -- `endpoint.py:275-278` -- and
        # MODE_RAW means the opposite of dead: the wiki closed its API and serves
        # `index.php?action=raw` instead, which `endpoint` knows how to read and which the rest
        # of this project reads from happily. So every RAW host on the corpus has been scored
        # unreachable since this function was written, permanently and by construction.
        #
        # This is the standing `health --preflight` failure, and it has been on the page for
        # many runs as `feats/www_dandwiki_com: all 200 sampled entries empty`: dandwiki is
        # MODE_RAW (verified live this run -- `{'mode': 'raw', 'path': '/w/index.php'}`), so the
        # completeness audit concluded the host was down and stopped believing its own caches.
        # The wiki was up the entire time.
        #
        # THE THREE MODES NOW GET THREE ANSWERS, not two. DEAD is still unreachable, and that
        # is the only mode that should be.
        mode = (EP.detect(host) or {}).get("mode")
        if mode == EP.MODE_DEAD:
            _REACH[host] = False
            return False
        # Through endpoint._get, which carries the project's User-Agent. A bare
        # urllib.urlopen sends Python's default UA and BOTH Wikipedia and Fandom answer it
        # 403 -- so a hand-rolled probe reports every host on earth unreachable and marks the
        # whole corpus unreliable. Use the transport the rest of the module already uses.
        if mode == EP.MODE_RAW:
            # The same probe `detect()` itself uses to certify a RAW host, so a host that
            # detection just accepted cannot immediately read as unreachable here.
            probe = EP.raw_url(host, "Main Page")
            _REACH[host] = bool(probe and EP._get(probe, timeout=timeout))
        else:
            base = EP.api_url(host)
            if not base:
                _REACH[host] = False
                return False
            _REACH[host] = bool(EP._get(base + "?action=query&meta=siteinfo&format=json",
                                        timeout=timeout))
    except Exception:
        silence.note("completeness.py:host-unreachable")
        _REACH[host] = False
    return _REACH[host]


def audit(only=None, workers=6):
    with open(HOSTS, encoding="utf-8") as f:
        hosts = json.load(f)
    have = catalogued_counts()
    # index catalogued counts by a loose key so 'Marvel' matches 'marvel.json'
    byslug = {}
    for src, v in have.items():
        byslug[str(src).lower()] = v
        byslug[v["file"][:-5].replace("-", " ")] = v

    # EVERY SOURCE THE LIBRARY KNOWS OF, not every source that happens to be on fandom.
    #
    # This line read `if subdomain(h)`, which admitted only `*.fandom.com`. 164 of the 203
    # sources on WIKI_HOSTS.json are fandom, so THIRTY-TWO hosted sources -- 22 on
    # en.wikipedia.org, 4 on www.dandwiki.com, rimworldwiki.com, and 5 `pages:`/`doc:`
    # sentinels -- got no row of any kind, plus 7 with no host recorded and 13 sources that
    # have records but no WIKI_HOSTS entry at all. A source absent from COMPLETENESS.json is
    # indistinguishable from a source with nothing missing, which is the exact danger `work()`
    # names below for an unreachable host; the filter was doing it to a fifth of the roll and
    # doing it permanently rather than during an outage.
    #
    # It also made two branches of `host_reachable` dead code in production. Its MODE_RAW branch
    # was written for www.dandwiki.com and its `api_url` resolution for "all 21 Wikipedia-hosted
    # sources", and `work()` is the only production caller -- so neither host was ever passed to
    # the code repairing their treatment.
    #
    # The union with the records is deliberate: a source can have a catalogue on disk and no
    # entry in WIKI_HOSTS (13 do today), and that combination is exactly the one where "no row"
    # would read as "nothing catalogued and nothing to catalogue".
    todo = sorted(set(hosts) | set(have))
    todo = [(src, hosts.get(src)) for src in todo]
    if only:
        todo = [t for t in todo if only.lower() in t[0].lower()]

    # A host serving more than one source cannot supply a denominator for either of them.
    # 'major fantasy pantheons' maps to marvel.fandom.com and legitimately so -- its provenance
    # says it draws "the deity/pantheon categories of multiple franchise wikis" -- but its
    # target is Marvel's GODS, not Marvel's 103,554 characters. Reporting 0.3% coverage there
    # would be an accusation against a source that did its job.
    shared = collections.Counter(h for _, h in todo if wiki_host(h))

    # Sharing a host does not disqualify BOTH sources -- it disqualifies the borrower. When two
    # sources point at marvel.fandom.com, one of them is Marvel and the other is drawing a
    # subset of it, and Marvel's denominator is perfectly good. The primary source for a host is
    # the one whose name survives inside the subdomain ('Marvel' -> 'marvel'); where no name
    # matches, no source claims it and all of them are marked.
    primary = {}
    for src, h in todo:
        sub = subdomain(h) or ""
        key = "".join(ch for ch in str(src).lower() if ch.isalnum())
        # Longest match wins, so 'Marvel' beats a hypothetical 'Mar'.
        if (key and key in sub.replace("-", "")
                and (h not in primary or len(key) > len(primary[h][1]))):
            primary[h] = (src, key)

    rows = []

    def _rec(src):
        return byslug.get(str(src).lower()) or byslug.get(str(src).lower().replace("-", " "))

    def _unmeasured(src, host, why, probe_failures=0, probes_run=0):
        """The row shape for a source no denominator could be obtained for. -> dict.

        Every field a measured row carries, so a reader never has to branch on which kind of
        row it is holding, and `unreliable` says which question went unanswered. What is on
        disk IS reported: the numerator is known even when the denominator is not.
        """
        rec0 = _rec(src)
        return {"source": src, "host": host, "wiki_persons": None,
                "wiki_categories": {}, "catalogued_total": (rec0 or {}).get("total"),
                "catalogued_persons": (sum(v for k, v in rec0["by_category"].items()
                                           if k.startswith("Persons")) if rec0 else None),
                "coverage": 0.0, "probe_failures": probe_failures, "probes_run": probes_run,
                "unreliable": why}

    def work(item):
        src, host = item
        sub = subdomain(host)
        probes = ws.CATEGORY_PROBES[PERSONS]

        # NOT A HOST AT ALL, and that is a fact about the source rather than a failure. `pages:`
        # and `doc:` are provenance sentinels (an owner-supplied book, a hand-registered page
        # list) and None is a source with no provenance recorded. None of the three can be
        # asked for a category count, so none of them gets a coverage number -- but all of them
        # get a ROW, because the alternative is what this filter did for a fifth of the roll:
        # leave them out and let their absence read as "complete".
        if not wiki_host(host):
            if host:
                return _unmeasured(src, host, (
                    "no denominator possible: %r is a provenance sentinel, not a wiki host -- "
                    "this source's material is an owner-supplied document or a registered page "
                    "list, so there is no category API to ask how large its cast is" % host))
            return _unmeasured(src, host, (
                "no denominator possible: no host is recorded for this source in "
                "WIKI_HOSTS.json, so there is nothing to ask. Its catalogued counts are "
                "reported here; whether it should have a host is `hostcheck`'s question"))

        # A HOST THAT IS DOWN STILL GETS A ROW. Asking the domain once and emitting an honest
        # `unreliable` row costs one socket call; probing it 8 times per source costs ~17 minutes
        # per source under a block and produces the identical conclusion. The row matters: a
        # source missing from COMPLETENESS.json reads downstream as "nothing on the wiki", which
        # is the opposite of "we could not ask", and a file that loses every fandom source during
        # an outage is the empty-file catastrophe of 2026-08-24 wearing a smaller hat.
        if not host_reachable(host):
            return _unmeasured(src, host,
                               ("host unreachable: %s did not answer its API at audit time, "
                                "so no denominator could be requested. Not probed further, "
                                "deliberately -- see completeness.host_reachable. No category "
                                "probe was attempted, so there are no probe failures to "
                                "report: %d probe(s) were DECLINED, not run and lost."
                                % (host, len(probes))))
    # `probe_failures` IS NOT PASSED HERE, AND THAT IS THE FIX (order 1065e3eb7cd3). It used to
    # be `probe_failures=len(probes)` against the default `probes_run=0`, so every row on this
    # branch recorded eight failures that never occurred -- measured on data/COMPLETENESS.json,
    # 196 of 216 rows carrying `probe_failures: 8, probes_run: 0`, i.e. 1,568 phantom transport
    # failures in the one file whose stated job is telling a real measurement from an unmeasured
    # one. The whole argument of this branch, in the comment above and asserted by verify_math
    # ("its probes_run is honestly zero"), is that a blocked host is deliberately NOT probed. A
    # probe that was never attempted cannot have failed. The count of declined probes is not
    # lost: `unreliable` now says it in words, which is where the reason for every other
    # unmeasured row already lives, and it keeps the unmeasured row the same SHAPE as a measured
    # one rather than growing a field only half the rows carry.

        sizes = {}
        failed = 0
        # THE TRANSPORT FOLLOWS THE HOST. `wiki_source._api` builds
        # `https://{sub}.fandom.com/api.php` and is the right answer for the 164 fandom sources;
        # the other 27 hosted ones are real MediaWikis on their own domains and are asked the
        # identical `prop=categoryinfo` question through `endpoint`, which resolves each host's
        # own API path. A RAW-mode wiki (www.dandwiki.com serves `index.php?action=raw` and no
        # API at all) can be READ but cannot be COUNTED, and that is stated rather than scored.
        no_denominator = None
        if sub:
            for cand in probes:
                n, err = category_size_probe(sub, cand)
                if err:
                    failed += 1
                if n:
                    sizes[cand] = n
        elif api_base(host):
            for cand in probes:
                n, err = category_size_probe_host(host, cand)
                if err:
                    failed += 1
                if n:
                    sizes[cand] = n
        else:
            no_denominator = ("no denominator possible: %s answers no MediaWiki API (it serves "
                              "raw wikitext, which this project reads happily but cannot ask "
                              "for a category size), so the size of its cast is unknown rather "
                              "than zero" % host)
        # A ROW THAT COULD NOT BE MEASURED IS NOT A ROW WITH NOTHING IN IT. Returning None here
        # for an all-errors source deleted it from COMPLETENESS.json, and an absent row is read
        # downstream as "this source has no wiki presence" -- the opposite of "the wiki did not
        # answer". Genuine absence (every probe answered, none of the categories exist) still
        # returns None as before; only the no-answer case is promoted into `unreliable`, which
        # is the bucket this module's own docstring built for exactly this.
        #
        # 2026-08-24: the m3 fix demanded UNANIMITY (`failed < len(probes)`) and that was one
        # notch too narrow. Seven transport failures plus a single clean "no such category"
        # answer scored failed=7, which is < 8, so the row was deleted anyway -- and under the
        # fandom socket-drop this module's own transport documents (wiki_source.py, MIN_GAP
        # note), mostly-failed-with-one-clean-miss IS the normal shape. It emptied
        # COMPLETENESS.json outright: 164 sources probed, 0 rows written, and the `every source
        # is fully catalogued` standard then reported a fabricated `0.0% (0 of 0)` off the empty
        # file for two hours. ANY transport failure means the denominator was not established,
        # so the row is unreliable, not absent. Genuine absence is now the one case it always
        # was in plain English: every probe answered, and none of the categories exist.
        #
        # `no_denominator` is a THIRD answer beside those two: the question could not be put at
        # all. It is not genuine absence (nobody answered "no such category") and not a
        # transport failure (nothing was attempted), so it returns its own row rather than
        # borrowing either story -- and it returns before the coverage arithmetic, because
        # `persons / None` has no meaning to compute.
        if no_denominator:
            return _unmeasured(src, host, no_denominator)
        if not sizes and failed == 0:
            return None
        best = max(sizes.values()) if sizes else None
        rec = byslug.get(str(src).lower()) or byslug.get(str(src).lower().replace("-", " "))
        got = (rec or {}).get("total")
        persons = None
        if rec:
            persons = sum(v for k, v in rec["by_category"].items() if k.startswith("Persons"))
        cov = (persons / best) if (persons and best) else 0.0
        # Two ways this row's denominator is not trustworthy, and both are stated rather than
        # smoothed over. A coverage above 100% is arithmetically impossible and therefore proof
        # that CATEGORY_PROBES missed the category this wiki actually uses -- The Division
        # catalogued 448 people against a probed "People" category holding 314.
        why = None
        # UNCATALOGUED IS NOT THE SAME FINDING AS ZERO. `rec is None` means this source has no
        # catalogue record on disk at all -- `have`/`byslug` never saw it -- so `persons` stayed
        # None and `cov` fell to the `else 0.0` above for lack of a numerator, not because
        # anything was measured and found empty. Left unstated, that reads exactly like a
        # source that WAS catalogued and genuinely has no Persons, which is the same "row that
        # looks reliable but answers nothing" failure `_unmeasured` exists to name elsewhere in
        # this function.
        if rec is None:
            why = ("no catalogue record on disk for this source -- coverage is unmeasured, not "
                   "measured-and-zero, until it is catalogued")
        elif not sizes:
            why = ("no category probe returned a size and %d/%d failed at the transport -- no "
                   "denominator was obtained, so this row carries no coverage judgment either "
                   "way" % (failed, len(probes)))
        # A row that DID obtain a denominator while some probes failed is still reported as
        # measurable, because `best` is a real category count that a real wiki really returned.
        # But the failure count rides along on the row rather than being discarded: if the
        # category that failed was the big one, `best` is an undercount and coverage reads
        # flatteringly high. Whether that should disqualify the row is a judgment about what the
        # `every source is fully catalogued` standard MEASURES, so it is a question in
        # NEXT_STEPS, not a silent change of the aggregate here.
        elif shared[host] > 1 and (primary.get(host) or (None, None))[0] != src:
            why = ("shares " + host + " with " + str(shared[host] - 1) + " other source(s) and "
                   "is not the primary; denominator belongs to "
                   + str((primary.get(host) or ("nobody",))[0]))
        elif cov > 1.0:
            why = ("catalogued exceeds the probed category, so the probe list missed this "
                   "wiki's real category name")
        return {"source": src, "host": host, "wiki_persons": best,
                "wiki_categories": sizes, "catalogued_total": got,
                "catalogued_persons": persons, "probe_failures": failed,
                "probes_run": len(probes),
                "coverage": cov, "unreliable": why}

    with ThreadPoolExecutor(max_workers=workers) as ex:
        for r in ex.map(work, todo):
            if r:
                rows.append(r)

    rows.sort(key=lambda r: -(r["wiki_persons"] or 0))
    return rows


SKIPPED_ONLY = "skipped-only"   # truthy, but `is not True` -- see land()'s three outcomes below


def land(rows, only=None):
    """Write COMPLETENESS.json atomically, and REFUSE to replace a real measurement with an
    empty one. Returns one of THREE outcomes, not two, and they are not interchangeable:

      * `True`  -- the file now holds `rows`.
      * `False` -- it does not: the write was refused (shrink floor, denied rename) or the
        content was empty against a real prior file. The measurement did not land.
      * `SKIPPED_ONLY` -- nothing was attempted, ON PURPOSE, because `--only` makes `rows` a
        slice rather than a whole-corpus answer. This is neither of the above: the file was
        left exactly as it was, deliberately, and that is success -- but it is a DIFFERENT
        success than "I wrote your rows", which is why it is not spelled `True`. It is still
        truthy (`if land(...):` reads correctly either way) so callers that only care whether
        the run may proceed do not need to change; a caller that needs to tell "wrote" from
        "declined on purpose" can check `is True` / `is SKIPPED_ONLY` (order e7614eb0d821 --
        before this, both cases returned `True` and were indistinguishable from each other,
        which is the same discarded-verdict shape the write-denial fix below closes).

    Two faults in one line, both of them this project's oldest species. The old write was
    `open(OUT, "w")` + `json.dump` -- the m6 pattern, which truncates the target BEFORE
    serialising, so an unencodable value leaves the real file unparseable, and which races the
    readers (`standards.check`, `catalogue_web --shortfall`) that hold it open on their own
    clocks. And it wrote unconditionally: on 2026-08-24 an audit that measured nothing wrote
    `[]` over 164 good rows, after which the HIGH `every source is fully catalogued` standard
    reported `0.0% (0 of 0)` -- a fabricated catastrophe, sourced from an empty file, ranked
    above every real fault in the queue for two hours.

    An empty result is not a measurement that every source has nothing. It is the absence of a
    measurement, and the previous measurement is better evidence than it. A run that genuinely
    has nothing to say leaves the last real answer standing and says so on stderr, loudly enough
    that the operator sees it and the exit code is non-zero.

    `--only` is exempted from the emptiness guard in one direction only: a filtered run is
    ALREADY not a whole-corpus answer, so it must never land over the full file at all."""
    if only:
        sys.stderr.write("completeness: --only is a spot check; COMPLETENESS.json not written "
                         "(it would replace the whole-corpus measurement with a slice)\n")
        return SKIPPED_ONLY
    prior = []
    try:
        with open(OUT, encoding="utf-8") as f:
            prior = json.load(f)
    except Exception:
        _ = "silence-exempt: no prior file is a legitimate first state"

    # EMPTY IS NOT THE ONLY WAY TO LOSE THE MEASUREMENT, and guarding only against it left the
    # door open next to the one that was locked. `[]` was refused while 164 rows -> 3 rows was
    # written without comment -- a 98% loss, silently, and the standard downstream would have
    # read a confident coverage figure off the three survivors. The audit runs from the foreman
    # EVERY round (`always`-marked), so whatever shape of bad run is possible will happen
    # repeatedly and unattended; that cadence is exactly why this file kept ending up wrong.
    #
    # A real corpus does not lose half its sources between two rounds. Sources do leave the roll,
    # so this is a floor and not an equality, and it is loud rather than silent when it trips.
    if prior and len(rows) < len(prior) * SHRINK_FLOOR:
        sys.stderr.write("completeness: measured %d row(s) against %d already on disk (below the "
                         "%.0f%% floor); REFUSING to overwrite. A run that lost most of the "
                         "corpus is a broken run, not a smaller corpus -- check transport in "
                         "`health.py --failures`, then re-run.\n"
                         % (len(rows), len(prior), 100 * SHRINK_FLOOR))
        return False
    # THE THIRD WAY TO LOSE THE MEASUREMENT, and the one the two guards above do not cover.
    # Both of them protect the CONTENT; neither checks that the content reached the disk.
    # `replace_retry` returns False -- it does not raise -- when the rename is denied for all
    # its attempts, and this file's denial is not hypothetical: the docstring above names the
    # readers (`standards.check`, `catalogue_web --shortfall`) that hold it open on their own
    # clocks, and on Windows a held handle IS a denied rename. Discarding that boolean and
    # returning True made this function's own contract line -- "Returns True if the file now
    # holds `rows`" -- false in exactly the case the caller most needs to hear about: the run
    # measured correctly, reported success, exited 0, and left the stale file in place.
    #
    # THE FOURTH WAY WAS THE SCRATCH FILE'S OWN NAME. This was a hand-rolled `OUT + '.tmp'`, the
    # same fixed name order 771fc3b0f517 retired from the category cache above, on a file the
    # foreman writes EVERY round: two audits overlapping by a second both open
    # `COMPLETENESS.json.tmp`, the second truncates the first, and the loser's rename lands a
    # half-written measurement over a whole one -- past all three guards, because every one of
    # them inspects `rows` and none of them inspects the file. `silence.write_json` puts pid and
    # thread in the temp name and returns the same `replace_retry` verdict this already gates on.
    # (found and fixed run36 beside its filed sibling, not itself a filed order)
    if not silence.write_json(OUT, rows, indent=1, ensure_ascii=False):
        sys.stderr.write("completeness: measured %d row(s) but the write to COMPLETENESS.json "
                         "was DENIED (a reader is holding it). The file still holds the "
                         "PREVIOUS measurement -- this run's numbers are not on disk. Re-run "
                         "when the readers are quiet.\n" % (len(rows),))
        return False
    return True


def main():
    ap = argparse.ArgumentParser(description="measure catalogue completeness per source")
    ap.add_argument("--only", help="restrict to sources containing this string")
    ap.add_argument("--workers", type=int, default=6)
    ap.add_argument("--top", type=int, default=40, help="how many rows to PRINT (the file "
                                                        "always holds every row)")
    a = ap.parse_args()

    rows = audit(only=a.only, workers=a.workers)
    if not land(rows, only=a.only):
        return 1

    good = [r for r in rows if not r["unreliable"]]
    bad = [r for r in rows if r["unreliable"]]

    print("%-34s %10s %10s %8s" % ("SOURCE", "ON WIKI", "CATALOGUED", "COVERAGE"))
    print("-" * 66)
    for r in good[:a.top]:
        print("%-34s %10s %10s %7.1f%%"
              % (str(r["source"])[:33], "{:,}".format(r["wiki_persons"]),
                 "{:,}".format(r["catalogued_persons"] or 0), 100 * r["coverage"]))

    total_wiki = sum(r["wiki_persons"] or 0 for r in good)
    total_have = sum(r["catalogued_persons"] or 0 for r in good)
    print("-" * 66)
    print("%-34s %10s %10s %7.1f%%"
          % (str(len(good)) + " MEASURABLE SOURCES", "{:,}".format(total_wiki),
             "{:,}".format(total_have),
             100 * total_have / total_wiki if total_wiki else 0))
    print("")
    print("rows printed: %d of %d measurable (the file holds every row)"
          % (min(a.top, len(good)), len(good)))
    print("")
    print("NOT MEASURED -- %d sources whose denominator this tool cannot stand behind:" % len(bad))
    for r in bad:
        print("   %-34s %s" % (str(r["source"])[:33], r["unreliable"]))
    print("")
    print("Those are excluded from the total rather than folded into it. A completeness figure "
          "that quietly")
    print("includes rows it cannot compute is the same species of error it was written to find.")
    print("-> " + OUT)
    return 0


if __name__ == "__main__":
    sys.exit(main())
