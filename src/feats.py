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
what the gate turned down when the rejection is itself interesting — carries a quantity, or a
ruin verb — because the previous pass discarded its rejections and left the rejection rate
unauditable. Everything else the gate turns down is COUNTED, not kept, in `_UNIT_DROPS["mine"]
["gate_failed_unrecorded"]` (order fa86e8b92150) — the rejection rate this promises is auditable
is a rate over that full denominator, not just the interesting subset.
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
#
# AND "PER HOST" WAS THE WRONG UNIT, MEASURED (order 959b98f38a63, owner ruling 2026-09-08,
# "Traffic on the Fandom edge"). These dicts were keyed on the NETLOC, so marvel.fandom.com,
# naruto.fandom.com, onepiece.fandom.com and nine more each believed it was the only caller and
# each paced itself at one request per 0.34s -- while all twelve of them resolve to ONE Fandom
# edge, which was therefore taking roughly 35 requests a second from a crawl that thought it was
# asking for 2.9. The hosts were not banning us; we were out-requesting them, and every one of
# the six standing HOST_QUARANTINED orders (marvel, naruto, onepiece, dragonball, mtg, dandwiki)
# was a symptom of this one setting. The key is now the REGISTRABLE DOMAIN, so every subdomain
# of one edge shares one pacer and the aggregate rate is the rate the pacer says it is.
#
# `_BACKOFF` and `_STRIKE` below are deliberately NOT re-keyed. A 429 is evidence about the edge,
# but a QUARANTINE is a verdict about a HOST -- binding_health quarantines, escalates and
# releases per host, and folding the strike counter onto the domain would hand off all twelve
# Fandom wikis the first time one of them was busy. So the strike ledger stays per host and
# `_throttle` reads the SLOWEST multiplier on the domain, which is the conservative direction:
# the shared edge is paced at the rate its unhappiest subdomain is asking for.
_HOST_LOCKS = collections.defaultdict(threading.Lock)
_HOST_LAST = {}
_RATE_LIMITED = {}
# GUARDS THE READ-MODIFY-WRITE ON `_RATE_LIMITED` AND `_CAP_BOUND` BELOW, NOT PACING.
#
# `_HOST_LOCKS[registrable_domain(host)]` is taken and released inside
# `_throttle`/`note_throttled` for spacing requests to one EDGE; it was never held around
# the `dict[key] = dict.get(key, 0) + 1` updates
# to these two dicts, and `roll()` runs 8 workers by default (`overnight.py` launches it with
# `--workers 12`), so concurrent increments lost updates the same way an unlocked counter always
# does. `_CAP_BOUND` in particular is keyed by "aplimit"/"srlimit", not by host, so a per-host
# lock could never have serialised it even if it had been used here. Both dicts are printed as
# measurements in roll()'s own summary, under this file's rule that a measurement nobody prints
# is not a measurement -- an uncounted count is worse than an absent one because it looks real.
_COUNTS_LOCK = threading.Lock()

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


# Two-label public suffixes this roll's hosts can plausibly sit under. Deliberately a SHORT,
# NAMED list rather than a vendored public-suffix database: the list below is what the
# Acquisitions Roll actually meets, and the failure mode of an unknown one is stated below and
# is the safe direction.
_TWO_LABEL_SUFFIXES = frozenset((
    "co.uk", "org.uk", "ac.uk", "me.uk", "com.au", "net.au", "org.au", "co.nz", "co.za",
    "co.jp", "or.jp", "ne.jp", "co.kr", "com.br", "com.cn", "com.mx", "com.tr", "com.ar",
))


def registrable_domain(host):
    """The domain a remote EDGE belongs to -- the unit a rate limit is actually enforced on.

    `marvel.fandom.com`, `naruto.fandom.com` and `dc.fandom.com` are three names for one server
    estate and one throttle. `en.wikipedia.org` and `commons.wikimedia.org` are two estates.
    Pacing on the netloc treats the first case as three independent budgets, which is the
    measured cause of the six standing host quarantines (see `_HOST_LOCKS` above).

    ERRS TOWARD SHARING, NEVER TOWARD SPLITTING. An unrecognised multi-label public suffix --
    say a wiki at `example.co.jp` were the suffix missing from `_TWO_LABEL_SUFFIXES` -- collapses
    to `co.jp`, so unrelated hosts would share one pacer and the crawl would run SLOWER than it
    needs to. The opposite error, splitting one edge into many pacers, is the one that gets this
    machine IP-banned, and it is the one this function is written to make impossible.

    The `pages:` and `doc:` sentinels are not hosts at all and are returned unchanged: nothing
    reaches the network for them, and giving them a made-up domain would silently queue five
    unrelated homebrew sources behind one pacer.
    """
    h = (host or "").strip().lower()
    if not h or h.startswith(("pages:", "doc:")):
        return h
    h = h.split("/")[0].split(":")[0].rstrip(".")
    labels = [p for p in h.split(".") if p]
    if len(labels) <= 2:
        return ".".join(labels)
    if ".".join(labels[-2:]) in _TWO_LABEL_SUFFIXES:
        return ".".join(labels[-3:])
    return ".".join(labels[-2:])


# ADAPTIVE BACKOFF STATE, per host. A fixed pause is a guess about a remote server's mood; this
# is a measurement of it. `_BACKOFF[host]` multiplies the base pause and is raised on every 429
# or 503 and decayed on every clean response, so a host that starts throttling us slows us down
# within one request instead of after a run's worth of them.
_BACKOFF = {}
BACKOFF_MAX = 32.0          # a 0.34s base becomes ~11s at the ceiling -- slow, never stopped
BACKOFF_GROWTH = 2.0
BACKOFF_DECAY = 0.8         # gentler than the growth: earn speed back slowly, lose it fast
# Consecutive throttles after which the host is handed to `binding_health` for quarantine rather
# than hammered further. Three is the point at which "busy right now" stops being the likelier
# reading than "we are being blocked".
THROTTLE_STRIKES = 3
_STRIKE = {}


def _throttle(host):
    """Pace one request to `host`. Adaptive, per host, and enforced IN CODE.

    WHY THIS IS WRITTEN RATHER THAN BORROWED. Four tools that face this at far greater scale were
    studied for a pattern to copy and none of them has one worth copying:

        sherlock  -- an acknowledged UNSOLVED problem (issue #816); rate-limited sites are
                     misreported as false positives project-wide
        maigret   -- exposes only `--timeout`, `--retries`, `-n` concurrency knobs
        shannon   -- asks the AGENT, in English, to "throttle to under 5 requests per second and
                     back off 60s on any 429". A prompt is not a rate limiter. This is the one
                     pattern the study flagged as an ANTI-pattern rather than a gap.
        strix     -- single-target; the question does not arise

    So this is the contribution, not the borrowing. It matters here specifically because this
    project has already been throttled into believing sources were EMPTY: 1,364 swallowed
    HTTPErrors in one adoption pass, after which every pantheon and astrology source read as
    "no wiki holds this fiction" when the truth was "we were being throttled". A 429 that reads
    as an absence is the project's signature failure arriving over the network.

    THE LOCK IS TAKEN ON THE REGISTRABLE DOMAIN, NOT THE NETLOC (owner ruling 2026-09-08,
    "Traffic on the Fandom edge"; orders 959b98f38a63, 5be28f56946c). See `_HOST_LOCKS` for the
    measurement. The pause is the SLOWEST any subdomain of this edge is currently asking for,
    because a shared edge that has told one of its wikis to slow down has told the crawl.
    """
    dom = registrable_domain(host)
    with _HOST_LOCKS[dom]:
        base = _pause_for(dom)
        # The strike ledger is per host (see `_HOST_LOCKS`); the pace is per edge. `_BACKOFF`
        # only ever gains a key from `note_throttled`, so this scan is over the hosts that have
        # actually been throttled -- a handful, not the roll.
        mult = _BACKOFF.get(host, 1.0)
        for h, m in _BACKOFF.items():
            if m > mult and registrable_domain(h) == dom:
                mult = m
        last = _HOST_LAST.get(dom, 0.0)
        wait = (base * mult) - (time.time() - last)
        if wait > 0:
            time.sleep(wait)
        _HOST_LAST[dom] = time.time()


def note_throttled(host):
    """Call on a 429/503. Widens this host's pause immediately, and quarantines a persistent one.

    RAISED ON THE FIRST SIGN, not after a threshold: the cost of slowing down one host slightly
    too early is nothing, and the cost of finding out too late is a source that reads as empty.

    THE LOCK IS THE EDGE'S, THE LEDGER IS THE HOST'S. `_HOST_LOCKS` is keyed on the registrable
    domain since the 2026-09-08 ruling, so this takes the same lock `_throttle` takes for the
    same edge -- which is what it always meant to do, and is now true across subdomains as well
    as within one. What is COUNTED here stays per host: see `_HOST_LOCKS` for why a strike
    ledger must not be folded onto the domain.
    """
    with _HOST_LOCKS[registrable_domain(host)]:
        _BACKOFF[host] = min(BACKOFF_MAX, _BACKOFF.get(host, 1.0) * BACKOFF_GROWTH)
        _STRIKE[host] = _STRIKE.get(host, 0) + 1
        strikes, mult = _STRIKE[host], _BACKOFF[host]
    if strikes >= THROTTLE_STRIKES:
        # HAND OFF RATHER THAN HAMMER. Past this point "busy" is a less likely reading than
        # "blocked", and continuing to spend requests on it costs the whole pool's politeness
        # budget. binding_health records the reason and retries on a slow cadence.
        #
        # AND THE HAND-OFF IS NOW A BRAKE, WHICH THIS COMMENT USED TO CLAIM WITHOUT IT BEING
        # TRUE (order 5be28f56946c; owner ruling 2026-09-08). Nothing on the fetch path asked
        # `is_quarantined` -- the only call in this file was the double-quarantine guard three
        # lines below -- so a host crossed three strikes, was "handed off", and the same twelve
        # workers went on queueing on it at the 32x ceiling for the rest of the run. That is how
        # marvel.fandom.com reached SEVENTY-FIVE consecutive throttles: if the hand-off braked
        # anything, the counter could not pass three by more than one worker's in-flight
        # requests. `roll()` now consults `quarantine_view()` before it spends a request on a
        # host and DEFERS that host's entities to the end of the roll. Deferred, never dropped:
        # dropping them would be a smaller universe in the same shape Hard Rule 0 forbids.
        try:
            import binding_health as BH
            if not BH.is_quarantined(host):
                BH.quarantine(host, "throttled %d times consecutively; backoff at %.0fx"
                              % (strikes, mult))
        except Exception:
            silence.note("feats.py:throttle-quarantine")
    return mult


def note_ok(host):
    """Call on a clean response. Decays the backoff and clears the strike run.

    Same lock as `_throttle` and `note_throttled` -- the edge's -- and the same per-host ledger.
    """
    with _HOST_LOCKS[registrable_domain(host)]:
        cur = _BACKOFF.get(host, 1.0)
        if cur > 1.0:
            _BACKOFF[host] = max(1.0, cur * BACKOFF_DECAY)
        _STRIKE[host] = 0


def backoff_state():
    """-> {host: multiplier} for hosts currently slowed. Reported, never silent."""
    return {h: round(m, 2) for h, m in _BACKOFF.items() if m > 1.0}


# THE QUARANTINE, READ ONCE A MINUTE INSTEAD OF ONCE AN ENTITY (order 5be28f56946c).
#
# `binding_health.is_quarantined` opens and parses HOST_QUARANTINE.json on every call, and the
# roll asks the question once per entity across a corpus of 276,218 of them. A cached view is
# what makes consulting it affordable at all; the TTL is what stops a quarantine raised mid-roll
# taking until the next run to bite.
_QVIEW = {"at": 0.0, "held": frozenset(), "unreadable": False, "reads": 0}
_QVIEW_LOCK = threading.Lock()
QUARANTINE_TTL_S = 60.0


def quarantine_view(now=None):
    """-> (held hosts, could_not_read). The quarantine as the fetch path should see it.

    THE UNREADABLE CASE IS REPORTED, NOT GUESSED (owner ruling 2026-09-08, "Answering unknown
    with a plausible value"). `binding_health.quarantined(strict=True)` raises when the file
    exists and will not parse, and this does NOT round that to "nothing is held" and move on
    silently: the flag rides out with the answer, `roll()` prints it in the summary, and the
    reader is told how many entities were fetched without the question having been answerable.

    It does not DEFER on an unreadable file, and that is the argued half. Deferring is not a
    drop, so deferring everything would be safe for the universe -- but it would move the whole
    roll to its slow tail pass on a single unparseable file, which is an outage rather than a
    brake. The honest reading is that we do not know a host is held, so we proceed and say so.
    """
    now = time.time() if now is None else now
    with _QVIEW_LOCK:
        if now - _QVIEW["at"] < QUARANTINE_TTL_S:
            return _QVIEW["held"], _QVIEW["unreadable"]
        held, bad = frozenset(), False
        try:
            import binding_health as BH
            held = frozenset(BH.quarantined(strict=True))
        except Exception:
            # Includes `QuarantineUnreadable`. Named as unknown rather than as an empty hold.
            silence.note("feats.py:quarantine-view")
            held, bad = frozenset(), True
        _QVIEW.update({"at": now, "held": held, "unreadable": bad,
                       "reads": _QVIEW["reads"] + 1})
        return held, bad


# Text that a real wiki article carries and a block page does not. Deliberately weak signals
# individually -- the point is that a page must clear SEVERAL, the way maigret's `checkType`
# layers status, presence strings and absence strings rather than trusting one.
_WIKI_MARKERS = ("[[", "{{", "==", "categor", "reflist", "infobox", "cite ", "'''")
# Phrases that mean "you are being refused", whatever HTTP status accompanies them. A WAF often
# answers 200 with an interstitial, which is the case a status check cannot see.
#
# SPLIT INTO TWO TIERS (order 572918512dbc). These four cannot be a real article's own words in
# ordinary use -- a page is never itself the Cloudflare or DDoS-Guard chrome around it -- so a
# hit is sufficient alone, unchanged from before.
_REFUSAL_MARKERS_SUFFICIENT = ("cloudflare", "ddos-guard", "request blocked", "are you a robot")
# These are AMBIGUOUS: a real article can legitimately contain them (the Doom UAC announcer's
# canonical line IS "Access denied"; an article about CAPTCHAs or rate limiting says those
# words). Measured whole-corpus, every one of 119 refusals on this tier sat on a MODE_API host
# where the marker layer has zero true-positive capability to begin with (see `parsed=True`
# below) -- but even off that transport an ambiguous hit alone is not proof, so it now requires
# the ABSENCE of positive wiki-markup evidence to count: a body that clears the third layer too
# is an article about the phrase, not the phrase.
_REFUSAL_MARKERS_AMBIGUOUS = ("enable javascript", "checking your browser", "access denied",
                              "captcha", "rate limit", "too many requests",
                              "temporarily unavailable")
MIN_REAL_PAGE_CHARS = 200
# `mined_under.marker_layer` stamp -- bump this when the marker layer's judgement changes shape,
# so `mined_under_old_marker_layer` can tell a record mined under an earlier rule from one mined
# under this one. See that function.
_MARKER_LAYER_VERSION = 2


def page_looks_real(text, *, wiki=True, parsed=False):
    """-> (ok, why). Is this the article, or something wearing its URL?

    NO `title` PARAMETER, AND DELIBERATELY NOT. This took `title=""` between `text` and `wiki`
    for as long as it has existed and never read it once -- both callers passed one, so both
    were entitled to believe the gate checked that the document it was handed is the document
    that was asked for, and it never did (order 9beb0391c8ab). The parameter is gone rather than
    wired up, because the check a caller would infer from it CANNOT be written here safely: the
    obvious form is "the title must appear in the page", and `binding_health` probes with
    catalogue entry names carrying the cataloguer's disambiguators -- `Scout (Jeremy Willis)`,
    `Cetana (the Synthetic Queen)` -- which no article contains verbatim. That test would refuse
    real pages and quarantine live hosts, which is the exact false-quarantine failure run #33
    paid for across twenty hosts. `wiki` is keyword-only so an old positional `(text, title)`
    call raises instead of quietly binding the title to `wiki` and loosening the gate.

    THE GAP THIS CLOSES. Every extracted sentence is already verified VERBATIM against the page
    it came from, and that check is sound -- it cannot be fooled by a paraphrase. What it cannot
    do is notice that the PAGE is wrong: a Cloudflare interstitial, a login wall, a soft-404 or a
    rate-limit notice is a real document, and a model quoting it quotes it accurately. Verbatim
    provenance against the wrong source is still wrong, and it looks exactly like success.

    Layered on purpose (maigret/sherlock's `checkType` + `presenseStrs`/`absenceStrs` pattern):
    length, then an explicit refusal phrase, then positive evidence that this is wiki markup at
    all. One signal cannot separate "empty article" from "we were blocked", and this project has
    already paid for that confusion -- 1,364 throttled fetches were filed as honest absences.

    CHEAP BY CONSTRUCTION: string tests over bytes already in memory, no extra request, so it can
    sit in front of the expensive model call without costing anything (nuclei's fingerprint-gate
    idea -- a cheap check gates an expensive one).

    `parsed=True` SKIPS THE MARKER LAYER ENTIRELY (order 572918512dbc). Set it only when `text`
    was extracted from a response that already parsed as JSON -- `api()`'s MediaWiki
    prop=revisions content is the one caller with this shape. A WAF interstitial, a login wall
    or a rate-limit page fails `json.loads` and is caught separately, inside `api()`, as
    'nonjson' -- it cannot arrive here at all on that transport. So on a parsed-JSON body every
    marker hit is necessarily a false positive matching the ARTICLE's own words, not a block
    page: measured whole-corpus, 119 records refused this way, every one on a MODE_API host,
    several of them 20,000+ characters of real wikitext (doom/UAC_announcer's canonical line IS
    "Access denied"). The length floor and the wiki-markup layer still apply -- only the marker
    layer is skipped, and only for callers holding text that could not physically be a block
    page. MODE_RAW and the HTML/`pages:` corpora return an UNPARSED body and keep the default.

    `wiki=False` DROPS THE THIRD LAYER ONLY, and it exists because the third layer turned this
    guard against the two corpora that are not wikis. Measured on the one owner-ingested book on
    disk (`data/docs/arcanum-worlds-odyssey-of-the-dragonlords`): 443 pages in, 3 through the
    gate, 401 refused for "no wiki markup found at all". Real prose has no `[[`, no `{{` and no
    `==` in it, so a positive test for wiki markup is a positive test for BEING A WIKI, which
    `doc:` and `pages:` sources never are. The failure it produced is the same one this function
    was written to end, moved down a floor: a book that was read fine mines to zero feats and
    reads afterwards as an entity with no evidence. Length and the refusal markers still apply --
    those two catch a block page whatever it is dressed as -- and callers holding actual wikitext
    keep the default, so nothing that was gated before is ungated now.
    """
    t = (text or "")
    if len(t.strip()) < MIN_REAL_PAGE_CHARS:
        return False, ("only %d chars -- too thin to be an article, and an empty fetch must not "
                       "read as an empty subject" % len(t.strip()))
    low = t.lower()
    if not parsed:
        for m in _REFUSAL_MARKERS_SUFFICIENT:
            if m in low:
                return False, ("carries a refusal marker (%r) -- this is a block page, not the "
                               "article, whatever status it arrived with" % m)
        markup_present = wiki and any(m in low for m in _WIKI_MARKERS)
        for m in _REFUSAL_MARKERS_AMBIGUOUS:
            if m in low and not markup_present:
                return False, ("carries a refusal marker (%r) with no corroborating wiki markup "
                               "-- this is a block page, not the article, whatever status it "
                               "arrived with" % m)
    if wiki and not any(m in low for m in _WIKI_MARKERS):
        return False, ("no wiki markup found at all -- not an article page")
    return True, "%d chars, %s" % (len(t.strip()),
                                   "wiki markup present" if wiki
                                   else "prose corpus, wiki markup not required")


# The exact wording `page_looks_real`'s third layer refuses with. Matched as a substring rather
# than reconstructed, so the two cannot drift apart silently.
_SUPERSEDED_GATE_MARK = "no wiki markup"

# How many cache entries were dropped for having been mined under the superseded gate. Counted
# and PRINTED, like _CAP_BOUND and the refusal tally beside it: a re-mine nobody can see is
# indistinguishable from a cache that was always right.
_STALE_GATE = {}

# How many entities were mined and then FAILED TO CACHE -- the atomic replace of the per-entity
# evidence file denied. Counted per host and printed in roll()'s summary for the same reason as
# every counter above it: the feats are in the totals either way, so without this an entity
# whose evidence never reached disk is indistinguishable from one whose did, and the only sign
# is the same entity being fetched again on the next roll. Against a host that has IP-banned
# this machine once, "fetched again" is not free. (run #37 sweep.)
_UNCACHED = {}

# WHAT THE LENGTH FILTER TOOK, per gate, so its rate is auditable (order eacc5444288c).
#
# `mine()` and `by_axis()` both open with `if not (20 < len(s) < 400): continue`, and until now
# that drop reached NOTHING: not `feats`, not `gate_rejected`, not `quantities`, not roll()'s
# summary -- the one place every other kind of loss is printed. This module's own docstring
# promises the opposite ("it keeps everything it gathers, including what the gate turned down,
# because the previous pass discarded its rejections and left the rejection rate unauditable"),
# and an unrecorded cap on an evidence list is Hard Rule 0's exact shape. Measured by the audit
# that filed the order: 0.20% of units are 400 characters or longer, extrapolating to ~62,700
# dropped units across the cache, of which ~575 would have passed the evidence gate and ~128
# carry a physical quantity.
#
# COUNTED PER GATE, not once, and the distinction is not pedantry: `evidence_for` runs the same
# page through BOTH functions, so one shared tally would double every unit and report a rate for
# a denominator that does not exist. The floor and the ceiling are counted apart because they
# are different claims -- 20 characters is noise control, 400 is an upper bound on evidence, and
# only the second is a truncation of the corpus.
#
# The numbers are only counted here. What to DO about the ceiling is the order's open question
# and the owner's; this makes the answer measurable instead of invisible.
_UNIT_DROPS = {"mine": {"seen": 0, "short": 0, "long": 0, "gate_failed_unrecorded": 0},
               "by_axis": {"seen": 0, "short": 0, "long": 0}}

# The longest unit dropped by the ceiling, per gate, so the reader can see whether the material
# being lost is a runaway table row or a genuine paragraph of prose.
_UNIT_LONGEST = {"mine": 0, "by_axis": 0}


def _units(text, where):
    """Yield the text units of `text` that clear the length gate, TALLYING what it drops.

    The gate itself is unchanged -- `20 < len(s) < 400`, the same bound both call sites carried
    inline. What is new is that the drop is recorded. See `_UNIT_DROPS`.
    """
    tally = _UNIT_DROPS[where]
    for s in _SENT.split(text):
        s = s.strip()
        n = len(s)
        with _COUNTS_LOCK:
            tally["seen"] += 1
            if n <= 20:
                tally["short"] += 1
            elif n >= 400:
                tally["long"] += 1
                if n > _UNIT_LONGEST[where]:
                    _UNIT_LONGEST[where] = n
        if 20 < n < 400:
            yield s


def unit_drops():
    """A copy of the length-filter tallies, for anything that wants to report them."""
    return {k: dict(v) for k, v in _UNIT_DROPS.items()}


def reads_as_wiki(host):
    """-> is this host's material wikitext? THE ONE PLACE that question is answered.

    `page_looks_real`'s third layer is a positive test for wiki markup, so it may only be asked
    of a wiki. This predicate decides that, and both the mining path and the cache-staleness
    check below read it, because the same question answered in two places is the drift this
    codebase keeps paying for.

    `doc:` is an owner-ingested book -- never a wiki. `pages:` is a source whose material lives
    on ordinary web pages, but ONLY when URLs are actually registered for it: a `pages:` host
    with an empty registry falls through to wiki discovery and genuinely does hold wikitext.
    """
    if host and host.startswith("doc:"):
        return False
    if host and host.startswith("pages:"):
        import endpoint as EP
        return not EP.source_pages(host[6:])
    return True


def mined_under_superseded_gate(doc, host):
    """-> was this cached record produced by the wiki-markup gate that no longer applies here?

    A FIX WHOSE EFFECT IS CACHED AWAY IS NOT IN EFFECT. `page_looks_real` gained `wiki=False`
    because its markup layer was refusing the two corpora that are not wikis: measured on the one
    ingested book on disk, 443 pages in, 3 through the old gate, 401 refused for "no wiki markup",
    against 404 through the corrected one. The code was right the same hour it was written -- and
    the numbers did not move, because `cachekey.load` kept handing back records mined under the
    old gate, each holding a pile of wrongly-refused pages and near-zero feats. Measured across
    `data/feats/` for `doc:`/`pages:` hosts: 2,898 cached entities, 96 of them carrying that
    refusal, all 96 with ZERO feats, covering 1,399 individually refused pages.

    Those 96 are not merely stale, they are WRONG IN A DIRECTION THAT LOOKS LIKE AN ANSWER: an
    entity with no evidence and a recorded reason reads downstream as honestly empty. So a hit
    of this shape is treated as a MISS and the entity is re-mined -- which for a `doc:` host
    costs no network at all, because that corpus is `data/docs/<slug>/pages.json` on disk.

    Scoped by `reads_as_wiki` on purpose. On a genuine wiki "no wiki markup" is a CORRECT
    refusal, and invalidating those would re-mine the same pages to the same refusal on every
    single pass, for ever.
    """
    if reads_as_wiki(host):
        return False
    refused = (doc or {}).get("pages_refused") or {}
    return any(_SUPERSEDED_GATE_MARK in str(v) for v in refused.values())


def mined_without_name_matching(doc, host):
    """-> was this cached `pages:` record produced before the arm name-matched? (127ec13af78a)

    THE SIBLING `mined_under_superseded_gate` COULD NOT BE EXTENDED TO COVER THIS, and the reason
    is the whole argument for the `mined_under` stamp. That predicate recognises a damaged record
    by the WORDING OF A REFUSAL it happens to carry, which works only because the gate it is
    about leaves one. The two faults this one is about leave no mark at all: a page put through
    `strip_wikitext` when it should not have been (order abe49b3ba7b3) looks like any other page,
    and a page attributed to an entity it never mentions (order 127ec13af78a) looks like
    evidence. `A FIX WHOSE EFFECT IS CACHED AWAY IS NOT IN EFFECT` -- so the question is asked
    structurally instead: a record mined under the corrected arm SAYS SO, and one that does not
    say so predates it.

    SCOPED TO `pages:` HOSTS WITH REGISTERED URLS, which is exactly the set both fixes changed
    (`reads_as_wiki` is False for those and for `doc:`; `doc:` was already name-matched and was
    already never stripped, so invalidating it would buy nothing). Five sources are in scope
    today: A Plethora of Paladins, Guildmasters' Guide to Ravnica, KibblesTasty, all Creeper
    World, the Sex Worker background.

    IT FIRES ONCE PER ENTITY, NOT EVERY PASS. The re-mine writes the stamp, so the same record
    is not stale again -- which is what the order asked for, because unlike a `doc:` re-mine this
    one goes over the network. `_source_pages_text` makes that cost one fetch per URL per
    process rather than one per entity.
    """
    if not (host and host.startswith("pages:")) or reads_as_wiki(host):
        return False
    return ((doc or {}).get("mined_under") or {}).get("attribution") != "name-match"


def mined_under_old_marker_layer(doc, host):
    """-> was this cached record refused by the pre-transport-gating marker layer? (572918512dbc)

    THE THIRD SIBLING, same shape as the two above: `page_looks_real`'s refusal-marker layer used
    to run unconditionally, including on `title-lookup` pages pulled out of `api()`'s
    already-parsed JSON -- a transport a block page cannot physically reach, because it fails
    `json.loads` and is caught separately as 'nonjson'. Every marker hit recorded there was
    therefore a false positive: measured whole-corpus, 119 article-sized real pages filed as
    refusals, all on MODE_API Fandom hosts. `page_looks_real` now takes `parsed=True` on that
    transport and skips the marker layer entirely -- but the 119 records are already on disk with
    zero feats and a refusal that reads as an honest diagnosis, and `A FIX WHOSE EFFECT IS CACHED
    AWAY IS NOT IN EFFECT` (see `mined_under_superseded_gate`, this file's own precedent for that
    exact sentence).

    STRUCTURAL, not string-matched on its own: a record's `mined_under.marker_layer` says which
    version of the marker layer produced it, the same way `stripper`/`attribution` say which
    version of the other two arms did. Anything below `_MARKER_LAYER_VERSION` predates this fix.
    Scoped to `title-lookup` records that actually carry a marker refusal on a host whose CURRENT
    transport is `MODE_API` -- a record with no such refusal, or one on `MODE_RAW`/a non-wiki
    corpus, was never touched by the bug and re-mining it would buy nothing.
    """
    mu = (doc or {}).get("mined_under") or {}
    if mu.get("attribution") != "title-lookup" or mu.get("marker_layer", 1) >= _MARKER_LAYER_VERSION:
        return False
    import endpoint as EP
    if EP.detect(host)["mode"] != EP.MODE_API:
        return False
    refused = (doc or {}).get("pages_refused") or {}
    return any("carries a refusal marker" in str(v) for v in refused.values())


# HOSTS WHOSE EMPTY-RATE IS ANOMALOUS AGAINST THE dc.fandom.com CONTROL (order ef4ca9edd61f;
# owner ruling 2026-09-08, "Traffic on the Fandom edge": *only* hosts whose empty-rate is
# anomalous against dc's 8.6% control are re-mined).
#
# 34,676 records already on disk carry `pages_read=[]` with `pages_refused={}` and NO transport
# stamp, because the stamp did not exist when they were written. They cannot be classified after
# the fact -- that inability IS the finding -- so clearing them means re-mining them, which is
# network spend against hosts that are already throttling us. The ruling draws the line at the
# control: dc.fandom.com sits at 8.6% empty over 55,565 files on the same wiki farm as
# marvel.fandom.com at 25.6%, so a host near the control is showing the corpus's ordinary rate
# of genuinely page-less entities and re-mining it would buy nothing at real cost.
#
# THE LIST IS MEASURED, NEVER GUESSED, AND ITS ABSENCE IS A REFUSAL RATHER THAN AN EMPTY SET
# DRESSED AS A MEASUREMENT. `feats.py --empty-rates` walks the whole cache off local disk (no
# network) and writes the file; until it has been run, `anomalous_empty_hosts()` reports that
# nothing has been measured and NO legacy record is re-mined. Failing toward not re-mining is
# the conservative direction here: the cost of waiting is that some records stay unclassified,
# and the cost of guessing is a corpus-wide re-crawl of a wiki farm that has IP-banned this
# machine once.
EMPTY_RATE_CONTROL = 0.086            # dc.fandom.com, 4,802 empty of 55,565 files
EMPTY_RATE_ANOMALY = 2.0              # x the control before a host counts as anomalous
EMPTY_RATES = os.path.join(HERE, "data", "FEATS_EMPTY_RATES.json")


def anomalous_empty_hosts(path=None):
    """-> (set of hosts, measured?). The hosts the ruling admits for a legacy re-mine.

    The second element is the honest half: `(set(), False)` means NOBODY HAS MEASURED, which is
    a different fact from "no host is anomalous" and must not be rounded to it. Callers act only
    on `(hosts, True)`.
    """
    try:
        with open(path or EMPTY_RATES, encoding="utf-8") as f:
            doc = json.load(f)
    except FileNotFoundError:
        return set(), False
    except Exception:
        # Unreadable is not empty -- the same rule `binding_health.quarantined` keeps.
        silence.note("feats.py:empty-rates-unreadable")
        return set(), False
    rows = (doc or {}).get("hosts") or {}
    if not isinstance(rows, dict) or not rows:
        return set(), False
    out = set()
    for h, r in rows.items():
        try:
            rate = float((r or {}).get("empty_rate"))
        except (TypeError, ValueError):
            continue
        if rate >= EMPTY_RATE_CONTROL * EMPTY_RATE_ANOMALY:
            out.add(h)
    return out, True


# THE REASONS THAT ARE NOT A TRANSPORT FAILURE, named once instead of twice (order 71a9b380cb03).
# `fetch()` counts them and `mined_under_failed_transport` forgives them, and those two lists
# drifting apart is precisely how the forgiveness below became unreachable.
#   "ok"            every batch answered.
#   "http-404"      the host answered that there is nothing there. This file's one clean
#                   negative, and the whole reason this tuple exists.
#   "raw-transport" the raw transport has no per-request channel, so this is an honest UNKNOWN
#                   rather than a clean bill -- kept here because re-mining every raw-transport
#                   record for ever is not what the arm below was written to do either.
CLEAN_NEGATIVES = ("ok", "http-404", "raw-transport")


def mined_under_failed_transport(doc, host):
    """-> did this record's fetch FAIL, leaving an absence that is not evidence of absence?

    THE FOURTH SIBLING, and the one the module's own docstring has been describing all along:
    "1,364 swallowed HTTPErrors ... after which every pantheon and astrology source read as no
    wiki holds this fiction", reproduced one layer down, at rest, in the cache. `evidence_for`
    writes its record unconditionally, and when `api()` converted a 429-that-exhausted-retries,
    a non-JSON 200 from a WAF or a network fault into a bare `None`, `fetch()` returned `{}` and
    the record was written with everything empty -- byte-identical to the record a genuinely
    page-less entity produces, because `pages_refused` only ever holds pages that ARRIVED.
    `cachekey.load` then served that for ever: the three predicates above cannot reject it
    (`mined_under_superseded_gate` returns False for any `reads_as_wiki` host and
    `mined_without_name_matching` is scoped to `pages:`), so a throttled fetch became a permanent
    honest absence.

    TWO ARMS, AND THE SECOND IS THE ONE THE OWNER RULED ON.

    (a) STAMPED records. `fetch()` now carries `api()`'s outcome out and `evidence_for` stores it
        in `mined_under.transport`. A stamped record whose transport was not ok and which
        obtained nothing is a MISS and is re-asked. This costs nothing today and cannot loop: a
        re-mine that succeeds stamps "ok"; one that fails again re-stamps the failure, which is
        the correct behaviour for a host that is still refusing us, and the roll's own deferral
        keeps that from being a hammer. "http-404" is NOT a failure here -- it is this file's one
        clean negative, the host answering that there is nothing there.

    (b) LEGACY records, written before the stamp existed. These are re-mined ONLY on a host the
        measurement says is anomalous against the dc control -- see `anomalous_empty_hosts`. With
        no measurement on disk, none of them is re-mined and nothing pretends otherwise.
    """
    d = doc or {}
    if d.get("pages_read") or d.get("pages_fetched") or (d.get("pages_refused") or {}):
        # Something arrived. This is not the empty-with-no-reason shape.
        return False
    tr = ((d.get("mined_under") or {}).get("transport")) or None
    if tr:
        why = str(tr.get("why") or "unknown")
        # THE 404 EXEMPTION USED TO BE UNREACHABLE, AND THE DOCSTRING ABOVE PROMISED IT
        # (order 71a9b380cb03). The line was:
        #
        #     return bool(tr.get("failed")) or why not in ("ok", "http-404", "raw-transport")
        #
        # A 404 calls `_stamp(False, "http-404")`, which sets ok=False, which makes `fetch()`
        # increment `failed` -- so for any real 404 the LEFT operand is True, `or`
        # short-circuits, and the tuple naming "http-404" is never evaluated. Every genuinely
        # absent entity was therefore re-mined on every load, for ever, and the cost landed on
        # the hosts already in deep throttle backoff, which is where the requests are dearest.
        #
        # `failed` cannot answer this on its own because it counts EVERY non-ok batch. `why` is
        # only the FIRST non-ok reason, so a batch that 404s and then throttles reports
        # why="http-404" while a throttled page hides inside it -- forgiving on `why` alone
        # would turn that page into a permanent false absence, which is the exact harm this
        # function exists to prevent. So `fetch()` now counts the failures that are NOT clean
        # negatives separately, and that is the number this asks.
        #
        # MONOTONE ON WHAT IS ALREADY ON DISK. A record stamped before `failed_dirty` existed
        # has no such key, and for those the ORIGINAL expression stands unchanged -- so no
        # record already written starts being trusted today on evidence it never carried. New
        # stamps get the distinction; old ones keep the conservative re-mine.
        if "failed_dirty" in tr:
            return bool(tr.get("failed_dirty")) or why not in CLEAN_NEGATIVES
        return bool(tr.get("failed")) or why not in CLEAN_NEGATIVES
    hosts, measured = anomalous_empty_hosts()
    return bool(measured and host in hosts)


def empty_rates(cache=None):
    """Walk the whole feats cache off LOCAL DISK and report each host's unexplainable-empty rate.

    No network, nothing sampled, no cap: every file under `data/feats/` is opened. This is the
    measurement the owner's ruling rests on -- "only hosts whose empty-rate is anomalous against
    dc's 8.6% control are re-mined" -- and it is deliberately a separate, explicit pass rather
    than something a roll does on the way past, because its output authorises network spend.

    An "unexplainable empty" is a record that obtained NO page and recorded NO refusal and
    carries NO transport stamp: the exact shape that cannot say whether it was blocked or
    genuinely blank. Records written since the stamp landed are counted separately, because they
    CAN say, and folding them in would make the rate drift as the cache turns over.
    """
    root = cache or CACHE
    rows = {}
    # THE ROW IS KEYED ON THE HOST THE RECORD ITSELF STATES, NOT ON THE DIRECTORY NAME.
    # `cachekey` sanitises a host into a path segment -- `marvel.fandom.com` becomes
    # `marvel_fandom_com` -- and `mined_under_failed_transport` is handed the REAL host string by
    # `evidence_for`. Keying this on the directory would produce a file whose every key missed,
    # so the anomaly list would silently match nothing and read as "no host is anomalous". That
    # is the shape this whole order is about: a smaller answer wearing the right shape.
    for seg in sorted(os.listdir(root)) if os.path.isdir(root) else []:
        hdir = os.path.join(root, seg)
        if not os.path.isdir(hdir):
            continue
        n = empty = stamped = unreadable = 0
        host = None
        for fn in os.listdir(hdir):
            if not fn.endswith(".json"):
                continue
            n += 1
            try:
                with open(os.path.join(hdir, fn), encoding="utf-8") as f:
                    d = json.load(f)
            except Exception:
                unreadable += 1
                continue
            if host is None and d.get("host"):
                host = d["host"]
            if ((d.get("mined_under") or {}).get("transport")):
                stamped += 1
                continue
            if not (d.get("pages_read") or d.get("pages_fetched")
                    or (d.get("pages_refused") or {})):
                empty += 1
        if n:
            row = {"files": n, "unexplainable_empty": empty,
                   "empty_rate": round(empty / float(n), 4),
                   "carries_transport_stamp": stamped, "unreadable": unreadable,
                   "directory": seg}
            if host is None:
                # Every record in this directory was unreadable, so the host it belongs to is
                # not known from here. Recorded under the directory name WITH the ambiguity
                # marked, rather than guessed by un-sanitising the segment -- that mapping is
                # lossy in both directions.
                row["host_from_directory_name_only"] = True
                host = seg
            rows[host] = row
    return {"at": time.time(), "control": EMPTY_RATE_CONTROL,
            "anomaly_multiple": EMPTY_RATE_ANOMALY,
            "note": "empty_rate counts records with no page, no refusal and no transport stamp. "
                    "A host at or above control x anomaly_multiple is admitted for re-mining "
                    "under the owner ruling of 2026-09-08; every other host is left alone.",
            "hosts": rows}



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

def api(host, params, retries=2, outcome=None):
    """One MediaWiki API call. Returns parsed JSON, or None.

    `outcome` IS AN OPTIONAL CHANNEL FOR *WHY* NONE CAME BACK (order 64e4db060ad6). This
    function already separates the failure classes for the silence ledger -- 404, HTTP error,
    non-JSON 200, network fault -- and then throws that distinction away at the return, so every
    caller sees one undifferentiated `None`. That is tolerable for a page fetch, where a miss is
    a miss, and it is NOT tolerable for a liveness probe: `alive()` turned a swallowed timeout
    into "this source has no wiki", and `resolve_hosts` cached that judgement permanently.

    Pass a dict and this call stamps it with {"ok": bool, "why": str}. `why` is one of
    "ok", "no-api", "http-404", "throttled", "http-<code>", "nonjson", "network", or "unknown"
    -- the last being the pre-stamped default, so a path that somehow returns without stamping
    reads as *undetermined* rather than as a clean negative. Additive keyword with the old
    behaviour as the default: every existing caller is unchanged and ignores it.
    """
    def _stamp(ok, why):
        if outcome is not None:
            outcome["ok"], outcome["why"] = ok, why

    if outcome is not None:
        outcome.clear()
        _stamp(False, "unknown")
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
        # NOT a clean negative: `endpoint.detect()` probes to decide this, so "no usable API"
        # can itself be the answer of a failed probe. Reported as undetermined.
        _stamp(False, "no-api")
        return None                       # no usable API here; fetch() takes the raw path
    url = base + "?" + urllib.parse.urlencode(q)
    for attempt in range(retries + 1):
        try:
            _throttle(host)
            req = urllib.request.Request(url, headers={"User-Agent": UA})
            with urllib.request.urlopen(req, timeout=TIMEOUT) as r:
                _body = r.read().decode("utf-8", "replace")
                parsed = json.loads(_body)
                # A CLEAN RESPONSE EARNS SPEED BACK. Without this the backoff only ever
                # grows, so one bad minute would slow a host for the rest of the run. Taken
                # only AFTER the parse succeeds (run35 batch7): a 200 carrying a WAF/login-wall
                # HTML challenge -- the case `except json.JSONDecodeError` below exists for --
                # used to decay backoff and zero the strike counter before the parse ever ran,
                # so a host refusing every call with an interstitial could never accumulate
                # enough strikes to reach THROTTLE_STRIKES and be handed to binding_health's
                # quarantine.
                note_ok(host)
                _stamp(True, "ok")
                return parsed
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
                # THE ONE CLEAN NEGATIVE. The host answered and said there is nothing here.
                _stamp(False, "http-404")
                return None
            silence.note("feats.py:api-http-error")
            if e.code in (429, 503):
                wait = int(e.headers.get("Retry-After") or 0) or (5 * (attempt + 1) ** 2)
                with _COUNTS_LOCK:
                    _RATE_LIMITED[host] = _RATE_LIMITED.get(host, 0) + 1
                # WIDEN THE PACE, not just this one sleep. The retry below waits and then
                # carries on at the SAME rate, which is what let a throttling host be hit
                # at full speed for a whole run. 503 is folded in with 429 deliberately:
                # both mean "not now", and a wiki under load returns either.
                note_throttled(host)
                if attempt == retries:
                    _stamp(False, "throttled")
                    return None
                time.sleep(min(wait, 120))
                continue
            if attempt == retries:          # 404 already returned above
                _stamp(False, "http-%d" % e.code)
                return None
            time.sleep(2 + attempt * 4)
        except json.JSONDecodeError:
            # A NON-JSON 200 IS NOT A NETWORK FAULT, and it used to be filed as one. The body
            # arrived, the status said success, and `json.loads` choked -- which is what happens
            # when a WAF or a login wall answers an `/api.php` call with an HTML challenge page.
            # That landed on "feats.py:api-network-fault", the same ledger key as a plain
            # connection timeout, so a host that was quietly refusing every API call all run
            # read afterwards as a host with a flaky network. This is the identical separation
            # the 404 arm above was given in run #19, for the identical reason: the ledger's
            # count for a site is only readable if "the network is failing", "the page does
            # not exist" and "we are being refused" land in different buckets. It is also the
            # transport-layer twin of what
            # `page_looks_real` catches at the content layer, and the two should be legible as
            # the same story when a host is read afterwards.
            #
            # RETRY BEHAVIOUR IS UNCHANGED: same sleep, same give-up on the last attempt. Only
            # which counter it lands in changed.
            silence.note("feats.py:api-nonjson")
            if attempt == retries:
                _stamp(False, "nonjson")
                return None
            time.sleep(2 + attempt * 4)
        except Exception:
            silence.note("feats.py:api-network-fault")
            if attempt == retries:
                _stamp(False, "network")
                return None
            time.sleep(2 + attempt * 4)


def alive_verdict(host):
    """Is there a wiki at this host? -> (verdict, why). THREE answers, not two.

    True   the API answered siteinfo: there is a wiki here.
    False  a CLEAN negative -- the host answered 404, which is a wiki saying there is nothing
           at this address. This is the only shape that may be cached as "no wiki".
    None   the probe FAILED and we learned nothing: a timeout, a throttle, a 5xx, a WAF page,
           this machine's ephemeral-port exhaustion, or an endpoint detection that could not
           complete. NOT evidence of absence.

    WHY THE THIRD ANSWER EXISTS (order 64e4db060ad6). `alive()` was `bool(api(host, ...,
    retries=0))` -- ONE attempt, and `api()` swallows every exception into the ledger and
    returns None -- so any transport hiccup answered "no wiki", `resolve_hosts` wrote that
    judgement into data/WIKI_HOSTS.json as a null, and `roll()` then dropped every entity of
    that source from the universe (`h = hosts.get(src); if not h: continue`). A cached failure
    is indistinguishable from a genuine absence to every later reader, and to the code.
    """
    out = {}
    parsed = api(host, {"action": "query", "meta": "siteinfo"}, retries=0, outcome=out)
    # TEST `out['ok']`, NOT THE PARSED BODY'S TRUTHINESS (order 8350f7a183d1). `api()` stamps
    # {"ok": True, "why": "ok"} on ANY successful 200-and-parsed response, including one whose
    # body is `{}`, `[]` or `null` -- which is falsy, so `if api(...)` used to fall through to
    # the failure branch below with `why` still "ok", and the caller-facing verdict came out as
    # (None, "ok") -- "undetermined, because everything was fine". The behaviour was safe (an
    # undetermined verdict re-probes rather than caching a negative), but the REASON STRING was
    # not actionable and not true, and it is what `resolve_hosts` prints for an operator to act
    # on. An empty-but-successfully-parsed body now gets its own explicit reason instead.
    if out.get("ok"):
        if parsed:
            return True, "siteinfo answered"
        return None, "empty-body"
    why = out.get("why") or "unknown"
    # Only an explicit 404 is treated as settled. Everything else -- including "no-api", which
    # `endpoint.detect()` reaches by probing and can therefore reach by failing -- leaves the
    # question open, which costs one re-probe next run and is the cheaper error by far.
    return (False if why == "http-404" else None), why


# RETAINED, NOT DELETED: `alive` -- uncalled repo-wide, kept under the owner ruling of
# 2026-09-08 ("Correct code that no caller ever reaches", orders 665e3609bc82, f27d210d4fea:
# mark and keep, one line each, delete nothing). The order proposed deleting it as a trap
# standing open -- a wrapper whose only function is to be the wrong thing to call -- and the
# ruling declines deletion; the trap is defused by saying so here and in the docstring instead.
def alive(host):
    """Unchanged contract: True only when the wiki answered. See `alive_verdict` for the third
    answer, which every caller that CACHES a negative must ask for instead of this.

    THERE ARE NO CALLERS, AND YOU PROBABLY WANT `alive_verdict`. `resolve_hosts` calls that one
    directly (this file's own live path), because collapsing three answers to two is how a
    swallowed timeout became "this source has no wiki" and was cached permanently -- order
    64e4db060ad6, the incident this wrapper is the surviving shape of.
    """
    return alive_verdict(host)[0] is True


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


# Did the last `resolve_hosts` land WIKI_HOSTS.json? A module-level fact reported by `main()`,
# the same shape as `_CAP_BOUND`/`_RATE_LIMITED`/`_STALE_GATE` above, and for the same reason:
# the function's return value is the map and cannot also be the verdict without changing an
# arity that every caller and half the handoff notes name. (run #37 sweep.)
_HOSTS_DENIED = False


def resolve_hosts(records, verify=True):
    """{source: host}. Derived from stored pages where possible, guessed and VERIFIED otherwise.

    The returned map is the in-memory one and is correct whether or not the cache write landed;
    `_HOSTS_DENIED` says which, and `main()` exits nonzero on it. See the write at the foot of
    this function."""
    known = {}
    if os.path.exists(HOSTS):
        with open(HOSTS, encoding="utf-8") as f:
            known = json.load(f)

    # {source: [candidate (why), ...]} for sources whose probes could not be completed this run.
    # Reported below, UNCAPPED: this is the list a person acts on, and the whole finding is that
    # a failed probe used to leave no trace at all.
    unprobed = {}

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
        # A NULL IS A CACHED FAILURE, NOT AN ANSWER (order 64e4db060ad6). This tested
        # `src in known`, and a key whose value is None is still `in` the dict -- so the first
        # time a probe failed for a source, the None it wrote was never re-asked by any later
        # run, and `roll()` dropped every entity of that source from the universe for ever
        # (`h = hosts.get(src); if not h: continue`). Testing the VALUE re-probes a null; the
        # loop below now writes one only on a clean negative, so the two together mean a
        # transport failure costs one re-probe next run instead of a permanent deletion.
        if known.get(src):
            continue
        # Preferred: the corpus already told us, on the entries that carry a page.
        seen = collections.Counter(
            urllib.parse.urlparse(e["wiki_page"]).netloc
            for e in r["entries"] if e.get("wiki_page"))
        if seen:
            known[src] = seen.most_common(1)[0][0]
            continue
        # A SECOND `ov = _override(src)` USED TO SIT HERE, as a fallback below the corpus
        # evidence -- the original design, from before the override was promoted to the top of
        # this loop to unfreeze the wrong cached guesses described above. It could not run.
        # `_override` is a pure function of `src` (a regex walk over the module-level
        # `_HOST_OVERRIDES`), so the only way to arrive here is for the call at the top of the
        # loop to have returned falsy, and a deterministic function asked the same question
        # twice answers it the same way. Removed rather than left standing, because an
        # unreachable safety reads as a safety, and this file's whole subject is the difference
        # between a check that passes and a check that never ran.
        if not verify:
            continue
        # Otherwise guess the slug and CHECK it. An unverified guess would silently mine the
        # wrong fiction's wiki, which is worse than mining nothing.
        #
        # AND ONLY A CLEAN NEGATIVE MAY BE CACHED (order 64e4db060ad6). The for/else wrote
        # `known[src] = None` whenever no candidate answered TRUE, which folded "every candidate
        # answered 404" together with "the network refused us four times" -- and the null it
        # wrote was permanent. Now a candidate whose probe could not complete is collected in
        # `undetermined`, and a source with any such candidate is left OUT of the map entirely
        # rather than recorded as absent: absence and a missing key read identically to every
        # consumer (`hosts.get(src)`), so nothing downstream changes, but the next run asks
        # again instead of inheriting a verdict nobody ever reached.
        undetermined = []
        # AND NO CANDIDATE AT ALL IS NOT A NEGATIVE EITHER (order d1113e987407). `_slugs` drops
        # every candidate of two characters or fewer, so a source whose cleaned name is that
        # short produces NO slug -- and the for/else below then ran its else clause with
        # `undetermined` still empty, because the loop body had executed zero times, and cached
        # `known[src] = None`: a settled "this source has no wiki" reached without one probe
        # being attempted. Same fault as the paragraph above, arriving through an empty candidate
        # list instead of a failed probe, and strictly worse -- a probed-and-failed source is
        # re-asked next run, while this one returns [] on every run and can never self-correct.
        # Measured over data/SWEEP_ROLL.json (215 sources) exactly one name does it, `DC`, and
        # it is dormant only because WIKI_HOSTS.json already carries dc.fandom.com from before
        # this filter existed, which the `known.get(src)` guard skips. An UNASKABLE source is
        # unmeasured, not absent: it goes in `unprobed`, is printed by name, and is left out of
        # the map, so a rebuild of WIKI_HOSTS.json cannot silently invent the verdict.
        cands = _slugs(src)
        if not cands:
            unprobed[src] = ["(no candidate slug -- the cleaned name is too short to guess a "
                             "host from; needs a _HOST_OVERRIDES or _SLUG_FIXES entry)"]
            known.pop(src, None)
            continue
        for slug in cands:
            h = f"{slug}.fandom.com"
            verdict, why = alive_verdict(h)
            if verdict is True:
                known[src] = h
                break
            if verdict is None:
                undetermined.append("%s (%s)" % (h, why))
        else:
            if undetermined:
                unprobed[src] = undetermined
                known.pop(src, None)
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
    # GATED. `replace_retry` answers False rather than raising when the rename is denied, and
    # this dropped that answer -- so `--hosts` printed "N/M sources resolved to a wiki host ->
    # data/WIKI_HOSTS.json" and exited 0 over a file that had not changed. The paragraph above
    # already names the readers (`read.py:queue()`, completeness, ingest_doc, wiki_source), and
    # a denial is the ordinary Windows case precisely because they hold it open.
    #
    # WHAT GOES WRONG IS NOT "the map is missing", IT IS "the map is the old one". The override
    # loop at the top of this function exists to unfreeze cached guesses that were wrong in the
    # most expensive way available -- descent.fandom.com for Descent into Avernus, the board
    # game -- and a silently denied write leaves exactly those wrong guesses in place while the
    # console reports the correction. The next roll then mines thirteen wikis' worth of the
    # wrong fiction, which is the failure this file's own comment was written about.
    #
    # Recorded rather than raised: the map returned here is correct in memory, so `--roll` may
    # go on using it for this run, and `main()` turns the flag into a nonzero exit.
    global _HOSTS_DENIED
    _HOSTS_DENIED = not silence.replace_retry(tmp, HOSTS)
    if _HOSTS_DENIED:
        silence.note("feats.py:hosts-write-denied")
        print("WRITE DENIED -> %s: the replace was refused (most likely a reader holding it "
              "open). The map below is this run's, in memory; the file every other stage reads "
              "still holds the PREVIOUS map, overrides and all. Re-run `--hosts`." % HOSTS,
              flush=True)
    # EVERY SOURCE WHOSE PROBE COULD NOT BE COMPLETED, BY NAME. Uncapped: this is the list the
    # operator acts on, and until now a failed probe left no trace anywhere -- it was written
    # into the map as a null and read afterwards as a settled absence. These sources are absent
    # from the map, so this run treats them exactly as it treats a hostless source, and the next
    # `--hosts` asks again.
    if unprobed:
        silence.note("feats.py:host-probe-undetermined")
        print("PROBE UNDETERMINED for %d source(s) -- NOT recorded as 'no wiki', and re-asked "
              "next run:" % len(unprobed), flush=True)
        # THE NAME IS PADDED, NEVER CUT. This printed `_src[:44]`, three lines under a comment
        # promising the list is uncapped -- and a truncated NAME is worse than a truncated list,
        # because it still looks like an entry the operator can act on. Measured against the live
        # data/SWEEP_ROLL.json (215 sources), 11 names exceed 44 characters and were cut
        # mid-word: `Kobold Press (Midgard Heroes Handbook, Midga`, `DMs Guild: Xanathar's Lost
        # Notes to Everythi`. No two roll sources collide on their first 44 characters TODAY, and
        # the two `DMs Guild: ...` families are the shape that collides first as the roll grows,
        # at which point two different sources would print as one line. `%-44s` still pads the
        # short names, so the column survives for as long as it is honest. (order b0e69b869473)
        for _src in sorted(unprobed):
            print("   %-44s %s" % (_src, ", ".join(unprobed[_src])), flush=True)
    return known


# --------------------------------------------------------------------------- page discovery

# Where a fandom wiki actually files combat evidence. The subpage convention is the strongest
# signal (`Goku/Power and Abilities`); the rest catch wikis that use their own arrangement.
_EVIDENCE_TITLE = re.compile(
    r"(power|abilit|technique|statistic|arsenal|equipment|weapon|form|transformation|"
    r"skill|feat|strength|combat)", re.I)


def _api_list_all(host, params, cap_key, extract):
    """Every page of a MediaWiki list query, not just the first. -> list of rows.

    HARD RULE 0, AT THE PLACE IT WAS ACTUALLY BEING BROKEN. `discover()` refused a caller's
    `extra` truncation loudly and then truncated anyway, one level down: `aplimit=500` and
    `srlimit=50` are the API's own per-request maxima, and a query with more results than that
    answers with a top-level `continue` object meaning "ask again from here". The old code read
    that object only to INCREMENT A COUNTER and then iterated the first page it already had. So
    an entity with 900 evidence subpages was mined as an entity with 500 and looked complete --
    the same shape as `roster(limit=600)` losing Goku, with the cutoff moved into the transport.
    The tally is not the fix; measuring a truncation is not the same as not truncating.

    `continue` is merged into the next request verbatim (formatversion=2 returns exactly the
    parameters to resend: `apcontinue`, `sroffset`, and the `continue` sentinel itself), so this
    follows whatever continuation the wiki uses without knowing which list it is reading.

    THE ONE STOP CONDITION IS NOT A CAP. A wiki that returns the SAME continuation token twice
    is not offering more results, it is looping, and following it forever would hang the run
    rather than enlarge the universe. That case -- and a mid-continuation API failure, where
    `api()` returns None with results still outstanding -- increments `_CAP_BOUND[cap_key]`,
    because a partial list that nothing recorded is exactly the silent smaller universe the rule
    exists to prevent. A complete walk increments nothing.
    """
    q = dict(params)
    rows, seen_tokens = [], set()
    while True:
        d = api(host, q)
        if not d:
            # Ran out of answer with more to come: partial, and it must not read as complete.
            #
            # COUNTED EVEN WHEN `rows` IS EMPTY (order 051244c2628f). The guard here used to be
            # `if rows:`, so a walk whose VERY FIRST request failed counted nothing and returned
            # [] -- which is byte-for-byte what a genuine "this entity has no pages" looks like,
            # while the caller's "discovery lists: complete" banner still printed. That is the
            # same smaller-universe Hard Rule 0 forbids, arriving through the error path instead
            # of through a cap, and it is the worse case rather than the lesser one: a partial
            # walk at least returns what it read, while this one returns nothing and says so in
            # the same words a real zero uses. A failed read and an empty result are not the
            # same answer and must never be recorded as one.
            with _COUNTS_LOCK:
                _CAP_BOUND[cap_key] = _CAP_BOUND.get(cap_key, 0) + 1
            return rows
        rows.extend(extract(d))
        cont = d.get("continue")
        if not cont:
            return rows                    # the wiki says that is all of them
        token = tuple(sorted((k, str(v)) for k, v in cont.items()))
        if token in seen_tokens:
            with _COUNTS_LOCK:
                _CAP_BOUND[cap_key] = _CAP_BOUND.get(cap_key, 0) + 1
            return rows
        seen_tokens.add(token)
        q = dict(params)
        q.update({k: str(v) for k, v in cont.items()})


def discover(host, name, extra=None, resolved=None):
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
    refused loudly rather than honoured silently.

    THE RANKED RESOLVED TITLE IS ASKED FOR AND ADDED BESIDE THE RAW NAME (orders 4f308dbd9d2c,
    14a73de63099, f27d210d4fea; owner ruling 2026-09-08, "Wrong wikis, wrong titles, unmined
    entities"). `resolve_title` was written against a measured defect -- its own docstring:
    17,148 entries mined to nothing because the catalogue name is not the wiki's page title,
    "Hulk (Bruce Banner)" where the wiki says "Hulk" -- and until this ruling it had ZERO callers
    anywhere in the tree, so the loss it describes was, per the call graph, entirely unmitigated.

    BESIDE, NEVER INSTEAD. That is the whole shape of the ruling and it is what makes wiring a
    ranked guess safe: the raw catalogue name is still asked for first, so a resolution that is
    WRONG costs one extra page in a batched fetch, while a resolution that is RIGHT recovers an
    entity that mined to nothing. Replacing the raw name would have made a bad resolution a
    misattribution instead -- attributing one entity's feats to another, which `resolve_title`'s
    own docstring calls worse than an honest blank.

    `resolved` is an optional out-channel in the same idiom as `api()`'s `outcome`: pass a dict
    and it is stamped with the title that was resolved (or None) and whether it differed from the
    raw name. `evidence_for` stamps that into the record's `mined_under`, because a re-mine after
    this change that leaves no mark on the record is a fix that gets cached away and is never in
    effect -- exactly what `mined_under_superseded_gate`'s docstring describes."""
    if extra is not None:
        raise SystemExit("feats.discover: `extra` was a cap on a ranked page list and is "
                         "refused under Hard Rule 0. Pass None (the default); the list is "
                         "ranked richest-first and returned whole.")
    titles, seen = [], set()

    def add(t):
        if t and t not in seen:
            seen.add(t)
            titles.append(t)

    if resolved is not None:
        resolved.clear()
        resolved.update({"title": None, "differs": False, "asked": False})

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
        # A raw-only host has no search, so there is nothing for `resolve_title` to rank over.
        # Said out loud in the out-channel rather than left reading as "resolved to nothing".
        if resolved is not None:
            resolved["why"] = "no API on this host: nothing to rank a title over"
        return titles
    # THE RANKED RESOLVED TITLE, BESIDE THE RAW NAME. One extra search per entity, which is the
    # cost the ruling named and accepted. `resolve_title` returns None rather than a weak guess:
    # a title that merely CONTAINS the name loses, and a title the name does not open is refused
    # outright, which is what stops "Little Horn" being mined as "Little Steve".
    rtitle = None
    try:
        rtitle = resolve_title(host, name)
    except Exception:
        silence.note("feats.py:discover-resolve-title")
    if resolved is not None:
        resolved.update({"title": rtitle, "asked": True,
                         "differs": bool(rtitle) and _tnorm(rtitle) != _tnorm(name)})
    if rtitle:
        add(rtitle)
    # The subpage convention, asked for directly — cheaper and more precise than searching.
    # 500 and 50 below are the API's per-REQUEST maxima, not a cap on the answer: `_api_list_all`
    # follows `continue` until the wiki says there is no more, so asking for the largest legal
    # page merely means fewer round trips for the same complete list.
    #
    # WALKED UNDER BOTH SPELLINGS WHEN THEY DIFFER. The subpage convention hangs the evidence
    # pages off the ARTICLE's title -- "Hulk/Powers", not "Hulk (Bruce Banner)/Powers" -- so a
    # prefix walk under the catalogue name alone finds nothing for precisely the entities
    # `resolve_title` exists to rescue. Both prefixes are asked for rather than the resolved one
    # substituted, for the same reason the title is added beside rather than instead: some wikis
    # really do file the disambiguated form, and dropping that walk would trade one blind spot
    # for another.
    prefixes = [name] + ([rtitle] if rtitle and _tnorm(rtitle) != _tnorm(name) else [])
    for pref in prefixes:
        ap_rows = _api_list_all(
            host, {"action": "query", "list": "allpages",
                   "apprefix": f"{pref}/", "aplimit": "500"},
            "aplimit",
            lambda d: d.get("query", {}).get("allpages", []) or [])
        for row in ap_rows:
            if _EVIDENCE_TITLE.search(row["title"]):
                add(row["title"])

    # Then search, keeping only hits that name the entity — otherwise a search for a common
    # name drags in every unrelated power page on the wiki.
    sr_rows = _api_list_all(
        host, {"action": "query", "list": "search", "srlimit": "50",
               "srsearch": f"{name} power abilities strength feats"},
        "srlimit",
        lambda d: d.get("query", {}).get("search", []) or [])
    # THE FILTER KEY ACCEPTS EITHER SPELLING. It was the first word of the catalogue name alone,
    # so an entity whose article is filed under a different leading word ("Hulk" for "Bruce
    # Banner") had every one of its evidence hits filtered out even after the resolution
    # succeeded. Both keys are tried; nothing is loosened beyond that.
    keys = {name.lower().split()[0] if name.split() else name.lower()}
    if rtitle and rtitle.split():
        keys.add(rtitle.lower().split()[0])
    hits = [(row.get("size", 0), row["title"])
            for row in sr_rows
            if any(k in row["title"].lower() for k in keys)
            and _EVIDENCE_TITLE.search(row["title"])]
    for _, t in sorted(hits, reverse=True):
        add(t)
    return titles



def _tnorm(t):
    return re.sub(r"[^a-z0-9]+", "", (t or "").lower())


# `resolve_title` IS NOW WIRED IN. The paragraph that stood here reported both of these as dead
# and left the choice to whoever owned the title-lookup path. The owner ruled on 2026-09-08
# ("Wrong wikis, wrong titles, unmined entities", orders 4f308dbd9d2c, f27d210d4fea, 14a73de63099):
# `discover()` adds the ranked resolved title BESIDE the raw name with a `mined_under` stamp, so a
# wrong resolution costs one extra fetch rather than a misattribution. See `discover`'s docstring
# for the shape and the argument.
#
# RETAINED, NOT DELETED: `_page_exists` -- uncalled, kept under the owner ruling of 2026-09-08
# ("Correct code that no caller ever reaches", order 665e3609bc82: mark and keep, one line each,
# delete nothing). It is the natural companion to `resolve_title` and was not wired with it for a
# measured reason: `discover` adds the resolved title BESIDE the raw name, so a title that does
# not exist costs one absent page inside an already-batched `fetch` -- while a `_page_exists`
# probe would cost one EXTRA request per entity across the whole 276,218-entity roll to learn the
# same thing. It stays because the confirm-before-add design is the right one the moment a caller
# wants a resolution used INSTEAD of a name rather than beside it.
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
    # THE CANDIDATE LIST IS RANKED, NOT CUT (order 09a410dc7457). This asked for `srlimit=8` in
    # ONE request and followed no continuation, so the list this function ranks over was
    # truncated by us at eight and a correct title ranked ninth by the wiki's relevance was
    # invisible -- with no signal of any kind, since the function simply returns None or a
    # weaker candidate. `discover()` in this same file was corrected for exactly this
    # ("measuring a truncation is not the same as not truncating") and this call was not
    # visited. 50 is the API's per-REQUEST maximum, not an answer: `_api_list_all` follows
    # `continue` until the wiki says there is no more, and records a walk it could not finish in
    # `_CAP_BOUND` so a partial list cannot read as a complete one. The ranking below is
    # unchanged -- it is what makes this safe, and it was never the problem.
    rows = _api_list_all(
        host, {"action": "query", "list": "search", "srlimit": "50", "srsearch": name},
        "srlimit",
        lambda d: d.get("query", {}).get("search", []) or [])
    best, best_score = None, (-1, -1)
    for row in rows:
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


def fetch(host, titles, outcome=None):
    """{title: wikitext} for up to any number of titles, batched where batching is possible.

    A wiki that closed its API is not a wiki that cannot be read. D&D Wiki -- which holds the
    homebrew shelf this library has the most sources for -- returns 403 on every `api.php`
    action and serves `index.php?action=raw` to anyone. One title per request instead of fifty
    is slower; it is not nothing, and the difference is several thousand entries.

    `outcome` CARRIES *WHY* NOTHING CAME BACK, in the same idiom as `api()`'s own channel
    (orders ef4ca9edd61f, 64e4db060ad6; owner ruling 2026-09-08). MEASURED OVER THE WHOLE CACHE,
    all 275,029 files and nothing sampled: 34,676 records (12.6%) carry `pages_read=[]` with
    `pages_refused={}` -- nothing arrived at all and no reason is recorded anywhere on the
    record. They concentrate on exactly the host that was being throttled seventy-five times
    consecutively (marvel.fandom.com, 25.6% of its files, against dc.fandom.com's 8.6% on the
    same wiki farm), which is consistent with throttling being written to disk as absence and
    cannot be made into proof BECAUSE THE RECORD DOES NOT SAY. `api()` computes exactly this
    distinction and threw it away at the return; this threads it out.

    Pass a dict and it is stamped with `{"batches", "failed", "why"}` -- `why` being the FIRST
    non-ok reason any batch reported, from `api()`'s own vocabulary ("throttled", "http-404",
    "nonjson", "network", "no-api", "http-<code>"). A run where every batch answered stamps
    `why: "ok"`. The RAW transport has no such channel to offer and says so rather than
    inventing one: it reports "raw-transport", which is an honest *unknown*, not a clean bill.
    """
    import endpoint as EP
    if outcome is not None:
        outcome.clear()
        # `failed_dirty` counts the failures that are NOT clean negatives -- see
        # CLEAN_NEGATIVES and `mined_under_failed_transport`. Its PRESENCE is what
        # tells a reader this record was stamped by a writer that knew the
        # difference, so it is always initialised, never conditionally added.
        outcome.update({"batches": 0, "failed": 0, "failed_dirty": 0,
                        "why": "unknown"})
    if EP.detect(host)["mode"] == EP.MODE_RAW:
        got = EP.fetch_raw(host, titles)
        if outcome is not None:
            # NOT "ok". `endpoint.fetch_raw` reports no per-request outcome, so the honest
            # answer here is that this transport does not say -- which is a different fact from
            # every page having arrived, and rounding it to "ok" would put a clean stamp on the
            # one path that cannot support one.
            outcome.update({"batches": 1, "failed": 0, "failed_dirty": 0,
                            "why": "raw-transport"})
        return got
    out = {}
    for i in range(0, len(titles), BATCH):
        chunk = titles[i:i + BATCH]
        # redirects=1 matters more than it looks: `Kenshiro` on the Hokuto wiki is a redirect,
        # and without this the miner read 22 characters and reported the entity had no feats.
        _oc = {}
        d = api(host, {"action": "query", "prop": "revisions", "rvprop": "content",
                       "rvslots": "main", "redirects": "1", "titles": "|".join(chunk)},
                outcome=_oc)
        if outcome is not None:
            outcome["batches"] += 1
            if not _oc.get("ok"):
                outcome["failed"] += 1
                _w = _oc.get("why") or "unknown"
                # COUNTED PER BATCH, not derived from `why` at the end. `why` keeps only the
                # FIRST non-ok reason, so a pass that 404s and then throttles would look wholly
                # clean to anyone reading `why` alone. This counter is what lets
                # `mined_under_failed_transport` forgive a real 404 without also forgiving the
                # throttled page sitting beside it in the same batch. (order 71a9b380cb03)
                if _w not in CLEAN_NEGATIVES:
                    outcome["failed_dirty"] = outcome.get("failed_dirty", 0) + 1
                if outcome["why"] in ("unknown", "ok"):
                    outcome["why"] = _w
            elif outcome["why"] == "unknown":
                outcome["why"] = "ok"
        for p in (d or {}).get("query", {}).get("pages", []):
            if p.get("missing") or "revisions" not in p:
                continue
            try:
                out[p["title"]] = p["revisions"][0]["slots"]["main"]["content"]
            except (KeyError, IndexError):
                silence.note("feats.py:fetch-bad-revision")
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
    # ATTRIBUTE VALUES ARE NOT ALWAYS QUOTED AND NAMES ARE NOT ALWAYS LOWERCASE. This used to
    # require both (`[a-z\-]+="..."`), so `colspan=2 |` and `Style="color:red" |` both survived
    # into the mined prose intact -- measured on a real power-level table. Any attribute name
    # (any case) now pairs with either a quoted value or a bare unquoted token.
    c = re.sub(r'^\s*[!|]\s*(?:[A-Za-z\-]+=(?:"[^"]*"|\'[^\']*\'|[^\s|]+)\s*)*\|?',
              " ", c, flags=re.M)
    # INLINE "||" / "!!" ARE THE SAME CELL BOUNDARY AS A LEADING "|" OR "!", just repeated
    # mid-line for wikitext's one-line-per-row style: "| Goku || 9,000" left the "||" between
    # cells untouched, so "9,000" arrived glued to "Goku" by two raw pipe characters. Given the
    # same attribute treatment as the row-start marker above and turned into a line break, so
    # each cell becomes its own unit exactly as a cell already on its own physical line does.
    c = re.sub(r'\s*(?:\|\||!!)\s*(?:[A-Za-z\-]+=(?:"[^"]*"|\'[^\']*\'|[^\s|]+)\s*)*\|?',
              "\n", c)
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
#
# THE CARET DOES NOT HAVE TO TOUCH THE 10. `10\^?(\d+)` required the exponent digits to sit
# directly against an (optional) caret with no whitespace anywhere in between, so "3 x 10 ^ 9
# megatons" -- an entirely ordinary way to write that -- failed the exponent clause outright
# and the regex backtracked onto matching "9 megatons" alone, recording value "9": nine orders
# of magnitude short, silently, because `magnitude.py` floats `q["value"]` straight into
# `assay.axis_score` with no parse-failure signal anywhere in between. `\s*` now sits on both
# sides of the caret. Negative exponents ("10^-9") and the real multiplication sign ("×", not
# just the letter x) are both accepted, and a bare superscript exponent with no caret at all
# ("10⁹", "10⁻⁹") is matched by the second alternative, since `\d` does not match the
# superscript-digit Unicode category.
_SUPERSCRIPT_EXP = str.maketrans("⁰¹²³⁴⁵⁶⁷⁸⁹⁻", "0123456789-")
_QUANTITY = re.compile(
    r"\b(\d[\d,\.]*)\s*"
    r"(?:[x×]\s*10\s*(?:\^?\s*(-?\d+)|([⁰¹²³⁴⁵⁶⁷⁸⁹⁻]+))\s*)?"
    r"(tons?|tonnes?|kilotons?|megatons?|gigatons?|joules?|watts?|newtons?|"
    r"kilomet(?:er|re)s?|met(?:er|re)s?|miles?|light[- ]?years?|parsecs?|"
    # `kili` IS A WHOLE WORD, NOT AN EATEN ESCAPE. It reads like the truncated-fragment
    # corruption this project calls its oldest bug -- a bare four letters among otherwise
    # complete unit words -- and a sweep has flagged it as exactly that, correctly, as a
    # QUESTION. The answer, so that it lives beside the code instead of in a handoff nobody
    # greps: `kili` and `power level` are the Dragon Ball scouter's own units, which is why they
    # are adjacent here. magnitude.py:417 names both in terms as "franchise-internal scales with
    # no conversion", deliberately absent from `_TO_JOULES` and belonging to the Rosetta Tables
    # (Vol. X.4) rather than a joules column; "3,000 kili" is the worked example at
    # magnitude.py:45 and :640 and the cited Reach evidence at reference.py:95, and
    # src/zfighters.py is the module whose evidence is written in these units. Mining them is
    # the point: a quantity that cannot be converted is still a quantity the assay must SEE
    # before it decides it has no arithmetic for it. (order 26599d13c6a9)
    #
    # AND A MEASUREMENT THAT CAME OUT OF ANSWERING THAT QUESTION, LEFT HERE AS A QUESTION OF ITS
    # OWN RATHER THAN CHANGED. This pattern is anchored on a LEADING figure, so `power level`
    # can only ever match the form "<N> power level" -- and that is not how the corpus writes
    # it. Counted over the whole feats cache, every one of the 275,010 files and nothing
    # sampled: `power level` appears 11,622 times and the minable "<N> power level" form 16
    # times, so this alternative reaches about 0.1% of its own subject. `kili` is the opposite
    # and earns its place -- 565 mentions, 247 of them minable, because the wikis really do
    # write "3,000 kili". The corpus form for the other one is "a power level of 5,000" (see
    # this module's own docstring at line 7, and zfighters.py:302, :328, :365), which is
    # UNIT-then-number and cannot be reached without a second alternative. Whether to add one
    # is a judgment for whoever owns the assay and NOT a maintenance fix: "a power level of
    # 5,000" attributed to the wrong subject is worse evidence than no quantity at all, and
    # this pattern has no subject-resolution to lean on. Nothing is changed here on that basis.
    #
    # AND `mach` HAS THE IDENTICAL PROBLEM, which this paragraph used to be silent about (order
    # 3b9812ae8ab7). English writes the Mach number UNIT FIRST -- "Mach 5", not "5 mach" -- and
    # measured over the same whole cache the unit-first form occurs 210 times against 33 minable
    # here, 86% unreachable. It is the same defect at a hundredth of the volume, so the reader of
    # this paragraph is no longer told the problem is confined to one alternative. Unlike `power
    # level` it HAS been acted on: see `_QUANTITY_UNIT_FIRST` below the pattern, added under the
    # owner ruling of 2026-09-08 as a bounded test, with the argument for why the deferral above
    # is weakest for this one alternative and strongest for `power level`.
    r"kili|power\s*level|degrees?|kelvin|celsius|mach|times\s+the\s+speed\s+of\s+light)\b",
    re.I)

# THE UNIT-FIRST ALTERNATIVE, BOUNDED TO MACH (order 3b9812ae8ab7; owner ruling 2026-09-08,
# "Which measurement passes get commissioned now": *add the unit-first Mach alternative as a
# bounded test at 210 unminable against 33 minable, before anyone touches power level's 11,622
# mentions*).
#
# `_QUANTITY` above is anchored on a LEADING figure, so every alternative in its unit list can
# only ever match "<number> <unit>". English writes the Mach number the other way round -- "Mach
# 5", not "5 mach". MEASURED ACROSS THE WHOLE FEATS CACHE, all 275,029 files, nothing sampled:
# the unit-first form occurs 210 times and the minable number-first form 33, so 86% of the Mach
# evidence in the corpus was unreachable, for the identical structural reason as `power level`.
#
# WHY THIS ONE AND NOT `power level`. The existing note inside `_QUANTITY` defers the general
# question with a real argument: a quantity attributed to the wrong subject is worse evidence
# than no quantity at all, and this pattern has no subject-resolution to lean on. That argument
# is at its WEAKEST here and at its strongest for power level. "Mach 5" is a single unambiguous
# token: the unit name and the figure are adjacent, in that order, with nothing between them for
# a wrong subject to hide in. "a power level of 5,000" is a prepositional phrase whose subject is
# wherever the sentence put it, and it carries 11,622 mentions rather than 210 -- so the bounded
# test is deliberately the small, safe one, and the big one stays deferred exactly as the note
# says. If the 210 turn out to attribute badly, the blast radius is 210 quantities.
#
# SEPARATE PATTERN RATHER THAN A SECOND ALTERNATIVE INSIDE `_QUANTITY`. `mine()` reads groups 1
# to 4 of that regex by number -- mantissa, decimal exponent, superscript exponent, unit -- and
# splicing a differently-shaped alternative into it would renumber them, which is how an
# exponent gets silently dropped and an axis moves by orders of magnitude (see the group-2
# comment in `mine`). This keeps one shape per pattern.
_QUANTITY_UNIT_FIRST = re.compile(r"\b(mach)\s*(\d[\d,\.]*)\b", re.I)


def mine(text, page):
    """Sentences that clear the evidence gate, plus any physical quantities, each tagged with
    the page it came from. INTERESTING rejections are kept — see the module docstring; every
    other rejection is counted, not kept, in `_UNIT_DROPS["mine"]["gate_failed_unrecorded"]`
    (order fa86e8b92150) — see that counter's comment."""
    kept, rejected, quants = [], [], []
    # `_units` applies the identical `20 < len(s) < 400` gate this loop carried inline, and
    # COUNTS what it drops -- see `_UNIT_DROPS`. (order eacc5444288c)
    for s in _units(text, "mine"):
        if P.valid_scale_note(s):
            kept.append({"feat": s, "page": page})
        elif _QUANTITY.search(s) or re.search(r"\b(destroy|obliterat|shatter|surviv)", s, re.I):
            rejected.append({"text": s, "page": page})
        else:
            # THE DROP THAT USED TO REACH NOTHING (order fa86e8b92150). Not `feats`, not
            # `gate_rejected`, not `quantities`, and not roll()'s summary -- a unit that fails
            # `valid_scale_note` and carries neither a quantity nor one of the four ruin verbs
            # above vanished with no trace anywhere, contradicting this module's own docstring
            # promise to keep the rejection rate auditable. Counted here, the same shape as the
            # length filter's own `_UNIT_DROPS` tally one function up (order eacc5444288c), and
            # printed in roll()'s summary beside it. NOT added to `rejected` itself: that would
            # multiply per-entity file size for no evidentiary gain the docstring asks for --
            # the count is what answers the auditability question.
            with _COUNTS_LOCK:
                _UNIT_DROPS["mine"]["gate_failed_unrecorded"] += 1
        for m in _QUANTITY.finditer(s):
            # The FULL sentence is stored, not a 220-char prefix (run #19). This field is not a
            # display string: `magnitude.py` copies it verbatim into the permanent instrument-tier
            # citation (`out[axis]["feat"]`), and `chain.py` uses it as a provenance dedup KEY —
            # where a shared 220-char prefix would collide two different sentences into one.
            # `s` is already bounded above by the 20 < len(s) < 400 gate, so this stores at most
            # 400 characters. Callers that need a short form truncate at the point of display,
            # which `_show` already does.
            # THE EXPONENT WAS CAPTURED AND THROWN AWAY. `_QUANTITY`'s second group holds the
            # N of an `x 10^N`, and for as long as it existed only groups 1 and 3 were read --
            # so "5 x 10^44 joules", an entirely ordinary way to write a large energy in this
            # material, was recorded as `value: "5"`. That is not a display defect: it is read
            # back by `magnitude.quantity_scores`, which does `float(str(q["value"]).replace
            # (",", ""))` and hands the result to `assay.axis_score` as an instrument-tier
            # reading. A citation could therefore move an axis by forty-four orders of magnitude
            # in the wrong direction while every other check -- verbatim provenance, the page
            # gate, the unit table -- reported success, because all of them were looking at a
            # sentence that really did say what it said.
            #
            # The mantissa's own commas are stripped only when an exponent is folded in, because
            # `"1,200e9"` does not survive `float()` and `"1,200"` alone still does via that
            # consumer's own `.replace(",", "")`. `exponent` is kept alongside so the reading
            # stays auditable against the sentence it came from.
            #
            # THREE EXPONENT SHAPES, ONE FIELD. Group 2 is a signed decimal exponent ("^9",
            # "^-9", or bare "9" with no caret at all); group 3 is a run of superscript
            # characters ("⁹", "⁻⁹") that `\d` cannot see, translated back to plain digits here
            # so both shapes land in the same `exponent` string.
            val, exp = m.group(1), m.group(2) or (m.group(3) or "").translate(_SUPERSCRIPT_EXP)
            if exp:
                val = "%se%s" % (val.replace(",", ""), exp)
            quants.append({"value": val, "unit": m.group(4), "exponent": exp, "sentence": s,
                           "page": page})
        # THE UNIT-FIRST FORM, same record shape so nothing downstream has to know which pattern
        # found it. `unit_first` is stamped so the 210 this recovers stay separable from the 33
        # the leading-figure pattern already reached -- the ruling commissioned this as a BOUNDED
        # TEST, and a test whose results cannot be told apart from the control is not one.
        for m in _QUANTITY_UNIT_FIRST.finditer(s):
            quants.append({"value": m.group(2), "unit": m.group(1).lower(), "exponent": "",
                           "sentence": s, "page": page, "unit_first": True})
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


def _axis_independent_gates(sentence):
    """The three gates that do not depend on which axis is being evidenced. ONE definition.

    These were spelled out TWICE -- once inline in `by_axis` and once in `axis_evidence` -- and
    that is the whole of order 73aacce08418. `by_axis` is the live one (magnitude.py:867);
    `axis_evidence` has no callers anywhere in the tree. So the axis gate had two definitions and
    only one of them ran: anyone tuning `axis_evidence`, the one with the explanatory name and
    the docstring, would have changed nothing at all, and anyone tuning `by_axis` would have left
    the named function silently disagreeing with the live one. Neither would have been told.

    Pulled out rather than deleted, because the drift is the hazard and the duplication is the
    drift. THE HOIST IS PRESERVED EXACTLY, which the order is explicit about: this runs ONCE per
    sentence in `by_axis` and the per-axis loop still runs only the axis vocabulary check, so the
    3x regex cost over an 874MB corpus that the hoist was measured to remove does not come back.
    """
    if P._STATBLOCK.search(sentence) or P._PATIENT.search(sentence):
        return False
    return bool(_OBJ.search(sentence) or P._MAGNITUDE.search(sentence)
                or _CMP.search(sentence))


# REPORTED DEAD, NOT DELETED, per house doctrine that dead code is not automatically deletable
# (order 25ec11447b4c) -- the same marker `weave.pair_weights` carries. `axis_evidence` has ZERO
# callers repo-wide; `by_axis` below is the live spelling of this gate and is what
# magnitude.py:867 calls. It is kept as a WRAPPER over the shared predicate rather than as a
# second copy of it, so that a future tuning of the gate cannot leave the two disagreeing in
# silence: there is now one definition of the axis-independent part and one of the axis part,
# and this function is composed of both. (order 73aacce08418)
#
# RETAINED, NOT DELETED, under the owner ruling of 2026-09-08 ("Correct code that no caller ever
# reaches", order 665e3609bc82: mark and keep, one line each, delete nothing).
def axis_evidence(sentence, axis):
    """Does this sentence evidence THIS axis, with the subject as the doer?"""
    return _axis_independent_gates(sentence) and bool(_AXIS_ACT_RE[axis].search(sentence))


def by_axis(text, page):
    """{axis: [sentences]} — the worksheet's per-axis candidate lists.

    Handing the model one flat pile and asking it to allocate across eleven axes is what let an
    earthquake be cited for Celerity. Choosing only among an axis's own candidates makes that
    particular error structurally impossible rather than caught afterwards.
    """
    out = {ax: [] for ax in AXIS_ACT}
    # Same length gate as before, now tallied -- see `_UNIT_DROPS`. (order eacc5444288c)
    for s in _units(text, "by_axis"):
        # The statblock, patient and evidence-object gates do not depend on the axis, yet the
        # per-axis loop was re-running all three eleven times per sentence -- a 3x regex
        # redundancy over an 874MB corpus (round-2 optimization audit, finding 1). Hoisted:
        # each runs once per sentence, and only the axis vocabulary check stays inside. The
        # hoist is unchanged; the three gates simply live in `_axis_independent_gates` now, so
        # that `axis_evidence` cannot drift away from this one. (order 73aacce08418)
        if not _axis_independent_gates(s):
            continue
        for ax in AXIS_ACT:
            if _AXIS_ACT_RE[ax].search(s):
                out[ax].append({"feat": s, "page": page})
    return out


# --------------------------------------------------------------------------- per-entity

# ONE FETCH PER REGISTERED URL PER PROCESS, not one per entity. `endpoint.fetch_html` has no
# cache of its own, and a `pages:` host's corpus is THE SAME handful of URLs for every entity
# bound to it -- so a cold roll over `pages_KibblesTasty_techno_psionic_line_` alone would ask
# that one author's site for its seven pages 1,290 times, 9,744 requests across the five `pages:`
# sources. These are one-author sites on shared hosting, which is the reason `fetch_html` already
# limits itself to two workers, and this project has been IP-banned once already. The memo is
# process-local and never persisted: it exists so a run that must re-mine (see
# `mined_without_name_matching`) costs twelve fetches rather than ten thousand.
#
# Per-key locks rather than one global one: two entities of the SAME host should wait for one
# fetch, two entities of DIFFERENT hosts should not wait for each other.
_PAGES_TEXT = {}
_PAGES_TEXT_LOCKS = {}
_PAGES_TEXT_GUARD = threading.Lock()


def _source_pages_text(urls):
    """{url: text} for a `pages:` source's registered URLs, fetched once per process."""
    key = tuple(urls)
    with _PAGES_TEXT_GUARD:
        lock = _PAGES_TEXT_LOCKS.setdefault(key, threading.Lock())
    with lock:
        if key not in _PAGES_TEXT:
            import endpoint as EP
            _PAGES_TEXT[key] = EP.fetch_html(urls)
    # A COPY, so a caller cannot edit the memo out from under the next entity.
    return dict(_PAGES_TEXT[key])


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
        if doc is not None and (mined_under_superseded_gate(doc, host)
                                or mined_without_name_matching(doc, host)
                                or mined_under_old_marker_layer(doc, host)
                                or mined_under_failed_transport(doc, host)):
            # Mined by a gate or an arm that has since been corrected for this corpus, or --
            # `mined_under_failed_transport` -- not mined at all, because the fetch was refused
            # and the record could not say so. Returning either would make the correction
            # invisible: see `mined_under_superseded_gate`, `mined_without_name_matching`,
            # `mined_under_old_marker_layer` and `mined_under_failed_transport`. Fall through and
            # re-mine; for a `doc:` host that reads the book off disk and costs no request, and
            # for a `pages:` host it costs one fetch per registered URL per process, not one per
            # entity (`_source_pages_text`).
            with _COUNTS_LOCK:
                _STALE_GATE[host] = _STALE_GATE.get(host, 0) + 1
            doc = None
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
    # WHICH CORPUS THIS ACTUALLY IS -- a `pages:` host with no registered URLs falls through to
    # wiki discovery below, and would then be holding wikitext after all. `page_looks_real`'s
    # markup layer is a positive test for being a wiki, so it must only be asked of one.
    # Answered by `reads_as_wiki` rather than recomputed here, so the cache-staleness check above
    # and this mining path can never disagree about what kind of corpus a host is.
    wiki_source = reads_as_wiki(host)

    # THE NAME-MATCH IS HOISTED OUT OF THE `doc:` BRANCH, because BOTH corpora that have no title
    # lookup depend on it and only one of them was doing it (order 127ec13af78a). It is a pure
    # function of the entity name and a page's text, so there was never a reason for it to live
    # inside one arm. `attribution` below records which way this record got its pages.
    low = (name or "").lower()
    words = [w for w in re.split(r"[^a-z0-9]+", low) if w]

    def _mentions(t):
        """Is this page about THIS entity? The whole name, or its first AND last token.

        Deliberately NOT "any token matches": the established form in this file is the whole
        lowercased name, or first-and-last, and loosening it would re-attribute half the corpus
        on a shared surname. Deliberately not tightened either -- these pages are prose, and a
        subclass named in a heading is named in the page.
        """
        tl = t.lower()
        return low in tl or (bool(words) and words[0] in tl and words[-1] in tl)

    # WHETHER `pages` HOLDS ALREADY-PARSED-JSON CONTENT (order 572918512dbc), so the marker
    # layer in `page_looks_real` can be told a block page could not physically have arrived.
    # Only the `title-lookup` arm below can set this True, and only when this host's CURRENT
    # transport is `MODE_API` -- `fetch()` re-derives the same mode internally, so the two can
    # never disagree about which arm a given `titles` batch actually went down.
    api_parsed = False
    # THE TWO CHANNELS THE RECORD USED TO BE UNABLE TO CARRY (orders ef4ca9edd61f, 4f308dbd9d2c).
    # `transport` is why the fetch answered as it did; `resolved` is the ranked title the pages
    # were also asked for under. Both are stamped into `mined_under` below. Only the wiki arm
    # fills them -- the two name-matched corpora reach no transport and resolve no title -- and
    # their default shape says so rather than reading as a clean fetch that resolved nothing.
    transport, resolved = {}, {}
    if plain:
        dp = os.path.join(HERE, "data", "docs", host[4:], "pages.json")
        with open(dp, encoding="utf-8") as f:
            all_pages = json.load(f)
        pages = {t: txt for t, txt in all_pages.items() if _mentions(txt)}
        titles = sorted(pages)
        attribution = "name-match"
    else:
        import endpoint as EP
        urls = EP.source_pages(host[6:]) if host and host.startswith("pages:") else []
        if urls:
            # `wiki_source` is already False here -- `reads_as_wiki` asked this same registry.
            #
            # AND THE PAGES ARE NAME-MATCHED, WHICH THIS ARM DID NOT DO AT ALL (order
            # 127ec13af78a). The comment four paragraphs above makes the same promise for both
            # non-wiki arms -- "the registered URLs ARE the corpus, and the reader's name-matching
            # does the attribution" -- and only the `doc:` arm honoured it. Without it a `pages:`
            # source's ENTIRE corpus was attributed to EVERY ONE of its entities: measured
            # 2026-08-29 against data/feats, all 1,290 KibblesTasty entities, all 364 Creeper
            # World entities and all 116 Plethora-of-Paladins entities held a BYTE-IDENTICAL
            # evidence document, provenance digest included. Nothing downstream re-filters it --
            # `magnitude.assay_entity` feeds these candidates to the model as this entity's own
            # evidence, under a no-evidence string that says "this entity's own source pages" --
            # so one homebrew subclass's feat was offered to 1,289 others as citable evidence
            # with a digest attesting it. That is `page_looks_real`'s own "verbatim provenance
            # against the wrong source" with the wrong source being another entity's page, which
            # no gate in this file can see.
            #
            # EXPECT THE TOTALS TO FALL. Most of those entities drop to zero pages and zero
            # feats, and that is the CORRECT answer: a homebrew subclass named on none of the
            # registered pages has no evidence. The drop is the defect leaving, not arriving.
            pages = {t: txt for t, txt in _source_pages_text(urls).items() if _mentions(txt)}
            titles = sorted(pages)
            attribution = "name-match"
        else:
            titles = discover(host, name, resolved=resolved)
            pages = fetch(host, titles, outcome=transport)
            attribution = "title-lookup"
            # MODE_RAW returns the body UNPARSED (`index.php?action=raw`), exactly like the
            # HTML/`pages:` corpora above -- a block page can arrive down that transport and
            # the marker layer must keep checking it. Only MODE_API pages come out of `api()`'s
            # already-parsed JSON, where a block page fails `json.loads` and never reaches here.
            api_parsed = EP.detect(host)["mode"] == EP.MODE_API
    feats, rej, quants, text = [], [], [], {}
    unreal = {}
    for t, wt in pages.items():
        # GATED ON `wiki_source`, NOT ON `plain` (order abe49b3ba7b3). The two are not the same
        # question and the difference was live for the five sources bound `pages:` in
        # WIKI_HOSTS.json: `plain` is true only for `doc:`, so a `pages:` host with registered
        # URLs -- whose text arrives as prose already extracted from HTML by `endpoint.fetch_html`
        # -- was still put through the wikitext stripper. That stripper eats legitimate prose:
        # its `<[^>]+>` arm removes anything in angle brackets, so "Roll 1d20 <plus> your
        # proficiency" loses the middle word, and its `^\s*[=*#:;]+` arm strips a leading '!',
        # '=', ';' or ':' from a prose line as table or heading scaffolding. The comment three
        # paragraphs above already gave the reason not to run it ("The text is already plain --
        # running the wikitext stripper over real prose eats legitimate brackets") and then wired
        # that reasoning to `doc:` alone. `reads_as_wiki` is the one place the question "what
        # kind of corpus is this host?" is answered, and it is the answer used by the
        # cache-staleness check and by `page_looks_real` on the very next line -- asking it here
        # too is what stops those three drifting apart again.
        clean = strip_wikitext(wt) if wiki_source else wt
        # THE CHEAP GATE IN FRONT OF THE EXPENSIVE ONE. A block page, a soft-404 or a rate-limit
        # interstitial is a real document that mines to zero feats, and "zero feats" is
        # indistinguishable from an honest absence once it is written to the cache. Recorded
        # rather than dropped: the whole point is that the reason is visible afterwards.
        ok, why = page_looks_real(wt, wiki=wiki_source, parsed=api_parsed)
        if not ok:
            unreal[t] = why
            continue
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
    # `pages_read` HOLDS ONLY THE PAGES THAT PASSED THE GATE (order 6d594a775899; owner ruling
    # 2026-09-08). It was `sorted(pages)` -- every title that ARRIVED, refusals included -- so an
    # entity every one of whose pages was a Cloudflare interstitial or a soft-404 was recorded
    # with a non-empty `pages_read` and a large `chars_read`. Inside this file that was handled
    # (`roll()` counts `refused` separately); one layer up it was not, and `coverage.py`'s
    # three-way status read a wholly-blocked entity as READ with zero feats -- read-and-silent,
    # which is exactly "a failure wearing the costume of an absence" restored at the consumer.
    #
    # `pages_fetched` AND `chars_fetched` PRESERVE THE OLD NUMBERS, so nothing is lost and a
    # reader who wants the fetch log still has it. The two questions are now separable on the
    # record: what arrived, and what was the article. `text` was always gate-passing-only, so
    # `pages_read` and `chars_read` are now the fields that agree with it.
    # `chars_read` STAYS IN THE SAME UNITS IT WAS ALWAYS IN -- the SOURCE characters of the pages
    # that passed, not the stripped ones. `text` holds `strip_wikitext`ed prose on a wiki, so
    # summing that would have moved this number for every record on disk rather than only for the
    # refused ones, which is not what the order was about and would have made the before/after
    # unreadable.
    out = {"entity": name, "host": host, "pages_read": sorted(text),
           "chars_read": sum(len(pages[t]) for t in text),
           "pages_fetched": sorted(pages),
           "chars_fetched": sum(len(v) for v in pages.values()),
           "feats": feats, "quantities": quants, "gate_rejected": rej, "text": text,
           # Pages that arrived but were NOT the article. Kept on the record so a later reader
           # can tell "this entity has no evidence" from "we were served a block page" -- the
           # distinction the whole project keeps losing.
           "pages_refused": unreal,
           # WHAT THIS RECORD WAS MINED UNDER, so staleness can be asked STRUCTURALLY rather
           # than inferred from the shape of a refusal string (order fe2db0dc0f44).
           # `mined_under_superseded_gate` can only recognise a record by the wording of a
           # refusal it happens to carry, which is why the `strip_wikitext` gating fix
           # (abe49b3ba7b3) and the `pages:` name-match fix (127ec13af78a) were both invisible
           # to it: neither leaves a mark on the record it damaged. These two booleans are that
           # mark. `stripper` says the wikitext stripper ran over this page text;
           # `attribution` says how the pages were decided to be this entity's -- "name-match"
           # for the two corpora with no title lookup, "title-lookup" for a wiki.
           # `transport` and `resolved_title` ARE THE TWO FACTS THE RECORD COULD NOT STATE.
           # `transport` is `fetch()`'s outcome channel -- "ok", "throttled", "http-404",
           # "nonjson", "network", "no-api", "raw-transport" -- so an entity whose fetch was
           # REFUSED is no longer byte-identical to one that genuinely has no pages, and
           # `mined_under_failed_transport` below can re-ask it instead of the cache serving a
           # throttled miss as an honest absence for ever. `resolved_title` says which name the
           # pages were also asked for under, so the re-mine that this ruling causes is VISIBLE
           # on the record rather than cached away invisibly.
           # `pages_read_gated` marks the schema change above, so a reader can tell a record
           # whose `pages_read` excludes refusals from one written before the ruling. It is NOT
           # a marker-layer bump: bumping that would re-mine all 275,029 files against hosts
           # that are already throttling us, and the ruling limits re-mining to anomalous hosts.
           "mined_under": {"stripper": bool(wiki_source), "attribution": attribution,
                          "marker_layer": _MARKER_LAYER_VERSION,
                          "pages_read_gated": True,
                          "transport": dict(transport) or None,
                          "resolved_title": (resolved or {}).get("title")},
           # PROVENANCE: a digest of the exact page text these feats were mined from. Lets a
           # later pass ask whether a citation is still PROVEN, or merely was once -- a source
           # page can be edited or deleted after mining, and the evidence file would otherwise
           # go on asserting it for ever. (in-toto's materials idea, stdlib-sized.)
           "provenance": cachekey.text_digest(text)}
    os.makedirs(os.path.dirname(path), exist_ok=True)
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(out, f, indent=1, ensure_ascii=False)
    # GATED INTO A COUNTER, not into a refusal. `replace_retry` answers False on a denied
    # rename and this dropped it, which is survivable in one specific way and misleading in
    # another. Survivable: `out` is returned from memory, so this call's answer is right, and a
    # cache that did not land re-earns itself as an ordinary miss on the next roll. Misleading:
    # the roll counts this entity's feats, chars and pages into its summary regardless, so a
    # host that denies every write produces a run that reports a full mining pass and leaves
    # nothing behind -- "nothing found" and "found and lost it" telling the same story again,
    # which is the confusion `errored`, `empty` and `refused` were each added to end.
    # A denial ALSO leaves any older evidence file for this entity standing, and that copy is
    # what every later reader sees; the superseded-gate check on load re-mines it, so the stale
    # copy cannot become permanent, but it is served until then.
    if not silence.replace_retry(tmp, path):
        with _COUNTS_LOCK:
            _UNCACHED[host] = _UNCACHED.get(host, 0) + 1
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
    #
    # AND IT RAISES RATHER THAN RETURNING A RE-MINE THAT DID NOT LAND (run #37 sweep).
    # `write_json` answers False on a denied replace instead of raising, so dropping the verdict
    # here returned the freshly re-mined `ev` while the file on disk still held the OLD feats --
    # a success value pointing at a write that never happened, which is the same shape
    # `compress_store.store()` was changed away from (see `generate.py`'s handler for it). It is
    # the wrong direction for this function in particular: unlike `evidence_for` above, there is
    # nothing to re-earn later. A re-mine is the whole product, its caller has no way to notice
    # the file is unchanged, and the point of re-mining is that the gate has been corrected --
    # a correction that silently does not land makes the old gate's verdict permanent.
    # It has no callers yet, so nothing today has a handler to break; a future one is told.
    #
    # RETAINED, NOT DELETED, under the owner ruling of 2026-09-08 ("Correct code that no caller
    # ever reaches", order 665e3609bc82: mark and keep, one line each, delete nothing).
    if not silence.write_json(path, ev, indent=1, ensure_ascii=False):
        silence.note("feats.py:remine-write-denied")
        raise OSError("re-mined evidence could not be landed over %s (replace denied after "
                      "five attempts -- a reader is holding it). The file still holds the "
                      "PREVIOUS mining; nothing was written." % path)
    return ev


# --------------------------------------------------------------------------- the roll

def roll(records, hosts, workers=8, limit=None, only=None):
    """Mine every entity of every resolved source, in parallel.

    Parallelism is per ENTITY but politeness is per HOST (see _throttle), so eight workers spread
    across eight wikis run at full speed while eight workers on one wiki queue behind each other.
    Everything is cached to disk on write, so a killed run resumes for free.
    """
    jobs = []
    # HOSTLESS SOURCES, COUNTED (order b9584c782d95). Every OTHER way an entity fails to be mined
    # in this file is measured and printed in the summary below -- _RATE_LIMITED, _CAP_BOUND,
    # _STALE_GATE, _UNCACHED, the length-filter drops, the refused-page tally -- and a source with
    # no resolved host was the one exclusion this accounting never named. `resolve_hosts(recs,
    # verify=False)` (what --roll calls) leaves a source out of its returned map entirely when it
    # has no cached host, override, or corpus-derived guess, so `hosts.get(...)` answers None and
    # this loop used to just `continue` -- dropping every entity of that source from the universe
    # with nothing anywhere to show it happened. Kept SEPARATE from the `only` filter just below:
    # that is an operator-requested narrowing, not a silent exclusion, and folding the two into
    # one count would hide the involuntary one behind the deliberate one.
    hostless_sources, hostless_entities = set(), 0
    for _, r in records:
        h = hosts.get(r["source"])
        if not h:
            hostless_sources.add(r["source"])
            hostless_entities += len(r["entries"])
            continue
        if only and only not in r["source"]:
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
    # `is not None`, not truthiness (order 4ed4041c3b78): `--limit 0` is a value the operator
    # gave, and `if limit:` read it as "no limit given" -- the same falsy-zero slip fixed in
    # binding_health.py (orders cd7492eec3bc, f1901d2178ba) and burgs.py. An empty `jobs` list
    # here is safe: the loop below, the progress print and the summary counters all handle
    # zero jobs correctly (`ex.map` over an empty iterable does nothing; every rate/eta
    # computation already guards its denominator).
    if limit is not None:
        jobs = jobs[:limit]

    # `errored` is counted separately from `empty` (run #19). Before it existed, an entity whose
    # evidence_for() raised incremented `n` and NOTHING else: not `empty`, not any other counter.
    # A systemic fault — a bug in evidence_for, a host refusing every request — would therefore
    # depress the roll's feats-per-entity rate with no visible signal anywhere in the summary,
    # and read as "these entities simply had nothing". "Nothing found" and "we never got to look"
    # are different facts and now have different counters.
    # `refused` is the third fact in the same family. `empty` says we found no page and
    # `errored` says we never got to look; neither can say WE WERE SERVED A BLOCK PAGE, which is
    # the exact distinction `page_looks_real` was added to draw and which then went no further
    # than each entity's own cache file. A run spent on WAF interstitials totalled identically to
    # a run that honestly found nothing -- the confusion that filed 1,364 throttled fetches as
    # absences, restored one layer up. Counted here and printed below, on the file's own rule
    # that a measurement nobody prints is not a measurement.
    done = {"n": 0, "feats": 0, "quant": 0, "pages": 0, "chars": 0, "empty": 0, "errored": 0,
            "refused": 0, "refused_entities": 0,
            # DEFERRED, NOT DROPPED (order 5be28f56946c; owner ruling 2026-09-08). Counted so
            # the deferral can never be the silent exclusion it exists to replace.
            "deferred": 0, "deferred_hosts": 0, "quarantine_unreadable": 0}
    lock = threading.Lock()
    t0 = time.time()
    deferred = []
    total = len(jobs)

    def work(job, honour_quarantine=True):
        h, src, name = job
        if honour_quarantine:
            # THE BRAKE THE HAND-OFF ALWAYS CLAIMED TO BE. `note_throttled` quarantines a host
            # after THROTTLE_STRIKES consecutive 429s and its comment says the crawl stops
            # spending requests on it; until the 2026-09-08 ruling nothing on the fetch path
            # asked, so twelve workers went on queueing at the 32x ceiling. Asked here, once per
            # entity, off a view refreshed at most once a minute.
            held, unreadable = quarantine_view()
            if unreadable:
                with lock:
                    done["quarantine_unreadable"] += 1
            elif h in held:
                with lock:
                    deferred.append(job)
                    done["deferred"] += 1
                return
        errored = False
        try:
            ev = evidence_for(h, name)
        except Exception:
            silence.note("feats.py:roll-evidence-error")
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
                # `.get`, not `[]`: cache files written before `pages_refused` existed are still
                # on disk and are legitimate hits, so a missing key here means "not recorded",
                # never an error.
                nref = len(ev.get("pages_refused") or {})
                if nref:
                    done["refused"] += nref
                    done["refused_entities"] += 1
                # `pages_fetched` IS THE QUESTION HERE, NOT `pages_read` (order 6d594a775899).
                # `pages_read` now holds only the pages that PASSED the gate, so an entity every
                # one of whose pages was a block page would have been counted `empty` -- "we
                # found no page" -- when the truth is that pages arrived and were refused, which
                # `refused` already says. `empty` keeps its own meaning: nothing arrived at all.
                # `.get` with a fallback so records predating the split still answer.
                arrived = ev.get("pages_fetched")
                if arrived is None:
                    arrived = ev["pages_read"] or list((ev.get("pages_refused") or {}))
                if not arrived:
                    done["empty"] += 1
            n = done["n"]
            if n % 200 == 0 or n == total:
                el = time.time() - t0
                rate = n / max(el, 1e-9)
                print(f"  {n:>6,}/{total:,}  {rate:>5.1f}/s  "
                      f"feats {done['feats']:,}  quantities {done['quant']:,}  "
                      f"pages {done['pages']:,}  {done['chars']/1e6:.0f}M chars  "
                      f"eta {(total-n)/max(rate,1e-9)/3600:.1f}h", flush=True)

    from concurrent.futures import ThreadPoolExecutor
    print(f"roll: {len(jobs):,} entities across "
          f"{len({j[0] for j in jobs})} wikis, {workers} workers", flush=True)
    with ThreadPoolExecutor(max_workers=workers) as ex:
        list(ex.map(work, jobs))
    # THE DEFERRED TAIL. A quarantined host's entities are mined at the END of the roll and on ONE
    # worker, which is the "slow cadence" `note_throttled`'s hand-off comment promises: the
    # per-domain pacer plus the host's own backoff multiplier still apply, so this tail runs at
    # whatever rate the edge has been asking for. They are mined REGARDLESS of whether the host is
    # still held, because the alternative is dropping them, and a dropped roster is a smaller
    # universe in the same shape Hard Rule 0 forbids -- the quarantine's job is to move the
    # traffic off the hot path, not to decide that an entity does not exist.
    if deferred:
        done["deferred_hosts"] = len({j[0] for j in deferred})
        print(f"\n  DEFERRED TAIL: {len(deferred):,} entities across "
              f"{done['deferred_hosts']} quarantined host(s), mined now on ONE worker at the "
              f"pace their edge is asking for. Deferred, never dropped.", flush=True)
        total = done["n"] + len(deferred)
        for job in deferred:
            work(job, honour_quarantine=False)
    print(f"\ndone in {(time.time()-t0)/3600:.2f}h  "
          f"{done['feats']:,} feats, {done['quant']:,} quantities, "
          f"{done['empty']:,} entities with no page, "
          f"{done['errored']:,} entities that raised")
    # All three of these were being counted and thrown away -- _RATE_LIMITED since the file was
    # written, _CAP_BOUND as of run #19, the refusal tally since `page_looks_real` was added.
    # A measurement nobody prints is not a measurement.
    if done["refused"]:
        print(f"  pages REFUSED (block page, soft-404, interstitial): {done['refused']:,} "
              f"across {done['refused_entities']:,} entit"
              f"{'y' if done['refused_entities'] == 1 else 'ies'} "
              f"-- these arrived and were NOT the article; they are not evidence of absence")
    else:
        print("  pages refused: none (every page that arrived looked like the article)")
    if done["deferred"]:
        print(f"  entities DEFERRED to the tail for a quarantined host: {done['deferred']:,} "
              f"across {done['deferred_hosts']} host(s) -- they were mined last and slowly, not "
              f"skipped; their feats ARE in the totals above")
    else:
        print("  entities deferred for a quarantined host: none")
    if done["quarantine_unreadable"]:
        print(f"  QUARANTINE NOT CONSULTABLE for {done['quarantine_unreadable']:,} of the "
              f"entities walked: data/HOST_QUARANTINE.json exists and would not parse, so those "
              f"fetches went out without the hand-off being able to brake them. This is NOT "
              f"'no host was quarantined' -- it is 'we could not tell', and it is printed rather "
              f"than rounded to the friendlier of the two answers.")
    if _UNCACHED:
        tot = sum(_UNCACHED.values())
        print(f"  evidence that did NOT reach disk: {tot:,} entit"
              f"{'y' if tot == 1 else 'ies'} across {len(_UNCACHED)} host(s) -- "
              + ", ".join(f"{k} x{v:,}" for k, v in sorted(_UNCACHED.items(),
                                                           key=lambda kv: -kv[1]))
              + ". Their feats ARE in the totals above and their cache files are NOT written, "
                "so the next roll re-fetches them. A denied replace means a reader is holding "
                "the file; if this number is large the roll bought nothing.")
    if _STALE_GATE:
        print("  cache entries RE-MINED for having been gated by the superseded wiki-markup "
              "check: "
              + ", ".join(f"{k} x{v:,}" for k, v in sorted(_STALE_GATE.items()))
              + "  (their recorded refusals were an artefact of the old gate, not evidence of"
                " absence)")
    if _CAP_BOUND:
        print("  discovery lists INCOMPLETE: "
              + ", ".join(f"{k} x{v:,}" for k, v in sorted(_CAP_BOUND.items()))
              + "  (the continuation walk could not finish -- the wiki repeated a continuation"
                " token, or the API stopped answering mid-walk. These entities were discovered"
                " in PART and must not read as fully discovered)")
    else:
        print("  discovery lists: complete (every allpages/search walk followed `continue` to"
              " the end; aplimit=500 / srlimit=50 are per-request maxima, not caps)")
    # THE LENGTH FILTER'S OWN RATE. Every other loss in this roll is printed above; this one
    # reached nothing at all until order eacc5444288c. Printed even when it is zero, because
    # "no unit was dropped for length" and "nobody counted" are the two readings this whole
    # block exists to keep apart.
    _drops = unit_drops()
    for _gate in ("mine", "by_axis"):
        _t = _drops[_gate]
        if not _t["seen"]:
            print("  length filter (%s): no text unit reached it this roll" % _gate)
            continue
        print(f"  length filter ({_gate}): {_t['seen']:,} unit(s) seen, "
              f"{_t['short']:,} dropped under 20 chars "
              f"({100.0 * _t['short'] / _t['seen']:.2f}%), "
              f"{_t['long']:,} dropped at 400+ chars "
              f"({100.0 * _t['long'] / _t['seen']:.2f}%, "
              f"longest {_UNIT_LONGEST[_gate]:,} chars)")
        if "gate_failed_unrecorded" in _t:
            # The rejection this module's own docstring promises is auditable -- units that
            # cleared the length filter but neither passed the evidence gate nor carried an
            # interesting rejection (a quantity or a ruin verb). Order fa86e8b92150: until now
            # this drop reached no counter at all. Printed even at zero for the same reason the
            # length filter above is.
            print(f"    gate-failed and UNRECORDED (no quantity, no ruin verb): "
                  f"{_t['gate_failed_unrecorded']:,}")
    if _UNIT_DROPS["mine"]["long"] or _UNIT_DROPS["by_axis"]["long"]:
        print("    (the 400-char ceiling is an upper bound on EVIDENCE, not noise control like "
              "the 20-char floor -- an over-long unit is discarded before the evidence gate "
              "sees it, so it reaches neither feats nor gate_rejected nor quantities. The rate "
              "above is the whole of what is known about what it took.)")
    if _RATE_LIMITED:
        tot = sum(_RATE_LIMITED.values())
        ranked = sorted(_RATE_LIMITED.items(), key=lambda kv: -kv[1])   # ranked, never truncated
        print(f"  429s absorbed: {tot:,} across {len(_RATE_LIMITED)} host(s), busiest first: "
              + ", ".join(f"{h} x{n:,}" for h, n in ranked))
    if hostless_sources:
        print(f"  sources with NO RESOLVED HOST: {len(hostless_sources):,} source(s), "
              f"{hostless_entities:,} entities excluded from this roll entirely -- "
              + ", ".join(sorted(hostless_sources))
              + "  (resolve_hosts had no cached host, override, or corpus-derived guess for "
                "these; not mined, not counted anywhere above, and not evidence of absence)")
    else:
        print("  sources with no resolved host: none (every source in this roll had one)")
    return done


# --------------------------------------------------------------------------- cli

def _show(ev):
    print(f"  {ev['entity']}  @ {ev['host']}")
    # BOTH NUMBERS, because they are now different questions (order 6d594a775899): `pages_read`
    # is what passed the gate and `pages_fetched` is what arrived. A display showing only the
    # first would say "0 pages" for an entity served nothing but block pages, which is the exact
    # reading `pages_refused` exists to prevent.
    _fetched = ev.get("pages_fetched")
    print(f"    pages   : {len(ev['pages_read'])} read  ({ev['chars_read']:,} chars)"
          + (f", {len(_fetched)} fetched ({ev.get('chars_fetched', 0):,} chars)"
             if _fetched is not None else
             "   [this record predates the read/fetched split; its pages_read may include "
             "refusals]"))
    for t in ev["pages_read"]:
        print(f"              {t}")
    # THE TRANSPORT, WHEN THE RECORD CAN SAY. An entity with nothing at all is the shape this
    # whole channel was added for, and the one moment a person is looking at `--probe` output is
    # the moment they need to know whether the fetch was refused or the wiki was simply empty.
    _tr = (ev.get("mined_under") or {}).get("transport")
    if _tr:
        print(f"    fetch   : {_tr.get('why')}  "
              f"({_tr.get('failed', 0)} of {_tr.get('batches', 0)} batch(es) failed)")
    elif not ev["pages_read"] and not (ev.get("pages_refused") or {}):
        print("    fetch   : NOT RECORDED -- this record predates the transport stamp, so it "
              "cannot say whether the fetch was refused or the entity has no pages")
    print(f"    feats   : {len(ev['feats'])}   quantities: {len(ev['quantities'])}"
          f"   held-back: {len(ev['gate_rejected'])}"
          f"   refused: {len(ev.get('pages_refused') or {})}")
    # The reason each refusal carries is the whole value of recording it: "no page" and "a block
    # page" are the two readings this display exists to keep apart. Listed in full and not
    # truncated like the feats and quantities above it -- a cap on a diagnostic hides exactly
    # the tail you opened it to read.
    # AND THE ROWS ARE NOT CUT EITHER. The list was uncapped and every row was truncated --
    # `t[:60]` and `why[:80]` -- so the comment above was true of the list and false of its
    # contents. Measured by calling `page_looks_real` directly, its three refusal reasons are 95,
    # 97 and 124 characters and all three were cut mid-sentence at 80: "only 0 chars -- too thin
    # to be an article, and an empty fetch must not read as a", "carries a refusal marker (...)
    # -- this is a block page, not ". The half that was cut is the half that explains WHY the
    # distinction matters, which is the sentence this display exists to show. (order b0e69b869473)
    for t, why in sorted((ev.get("pages_refused") or {}).items()):
        print(f"       ! {t} -- {why}")
    # THE PREVIEWS SAY THEY ARE PREVIEWS. These are genuine previews and defensible as such --
    # the true counts print two lines above -- but an unmarked `[:6]` is indistinguishable from
    # "this entity has six feats", which is the reading the comment above spends its length
    # refusing. Marked the way `chain.main()` marks its own: the count, and where the rest is.
    #
    # AND NOW THE ROWS THEMSELVES ARE WHOLE (orders 85678936df55, 86b9f6b2f32d). The paragraph
    # above -- "AND THE ROWS ARE NOT CUT EITHER" -- was written about the refusal rows and was
    # TRUE of them and false of these two, which still carried `f['feat'][:120]` and
    # `q['sentence'][:80]`: one sentence in one comment, true of the block above it and false of
    # the block below it, which is the worst arrangement of the two. The cut is not marked here,
    # it is GONE, because nothing forced it. Both values come out of `_units`, whose 400-char
    # ceiling is printed by the length-filter report above, so a row is bounded at roughly three
    # console lines and the whole value fits. That matters for exactly the reason the preview
    # exists: this is the view a person opens to judge whether a feat is real evidence, and a
    # feat's qualifying clause -- the "in the anime only", the "according to a databook" -- is
    # written at the END of the sentence, which is the half both cuts removed.
    _nf, _nq = len(ev["feats"]), len(ev["quantities"])
    if _nf:
        print(f"       feats, first {min(6, _nf)} of {_nf} (all of them are in the record):")
    for f in ev["feats"][:6]:
        print(f"       * {f['feat']}")
    if _nq:
        print(f"       quantities, first {min(4, _nq)} of {_nq} "
              f"(all of them are in the record):")
    for q in ev["quantities"][:4]:
        print(f"       # {q['value']} {q['unit']}  <- {q['sentence']}")


def main():
    # PLANT-WIDE INTERLOCK. The top rung of the escalation chain (escalation.py). If a
    # library-wide invariant has been violated, nothing starts until a person rules on it.
    # Placed first in main() so there is no path into this job that skips it.
    try:
        import escalation as _ESC
    except ImportError as _esc_gone:
        # FAIL CLOSED. This used to be `except ImportError: pass`, which meant a deleted or
        # unparseable `escalation.py` silently switched the plant-wide halt off in every job
        # at once -- nine sites, all of them quiet about it. That is Hard Rule -1's own
        # incident wearing different clothes: the last one began with an autonomous run
        # removing a safety it had concluded was unnecessary, and nothing downstream could
        # tell. A job that cannot ask whether the library is halted has no business
        # starting. Pinned by verify_math so the swallow cannot come back. (run #31)
        # `from _esc_gone` keeps the ORIGINAL ImportError attached as the cause. Without it the
        # traceback reads "During handling of the above exception, another exception occurred",
        # which invites whoever reads it to suspect this handler rather than the missing module
        # -- and the message already interpolates the error, so the two would disagree about
        # which failure is the real one. (B904, filed against eleven sites; this is feats.py's.)
        raise SystemExit(
            "REFUSING TO START: the escalation chain (src/escalation.py) could not be "
            "imported (%s), so the halt cannot be read. Hard Rule -1." % _esc_gone
        ) from _esc_gone
    _ESC.assert_clear(os.path.basename(__file__))
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
    ap.add_argument("--empty-rates", action="store_true",
                    help="measure each host's unexplainable-empty rate over the whole local "
                         "cache (no network) and write data/FEATS_EMPTY_RATES.json -- the "
                         "measurement the 2026-09-08 ruling's re-mine list is taken from")
    a = ap.parse_args()

    if a.empty_rates:
        doc = empty_rates()
        rows = doc["hosts"]
        floor = EMPTY_RATE_CONTROL * EMPTY_RATE_ANOMALY
        # RANKED, NEVER TRUNCATED -- every host prints, worst rate first (Hard Rule 0).
        for h, r in sorted(rows.items(), key=lambda kv: -kv[1]["empty_rate"]):
            print(f"  {'ANOMALOUS' if r['empty_rate'] >= floor else '   ok    '}  "
                  f"{r['empty_rate']:>7.2%}  {r['unexplainable_empty']:>7,} of {r['files']:>7,}"
                  f"  stamped {r['carries_transport_stamp']:>7,}"
                  f"  unreadable {r['unreadable']:>5,}  {h}")
        n_anom = sum(1 for r in rows.values() if r["empty_rate"] >= floor)
        print(f"\n{len(rows)} host(s) measured, {n_anom} anomalous against the "
              f"{EMPTY_RATE_CONTROL:.1%} dc.fandom.com control at x{EMPTY_RATE_ANOMALY:g}. "
              f"Only those are admitted for a legacy re-mine.")
        if not silence.write_json(EMPTY_RATES, doc, indent=1, ensure_ascii=False):
            # The measurement is the product. A run that measured and could not land it has not
            # authorised anything, and must not exit as though it had.
            print("\nMEASUREMENT NOT WRITTEN: %s could not be replaced, so nothing on disk "
                  "authorises a re-mine and `anomalous_empty_hosts()` still reports UNMEASURED."
                  % EMPTY_RATES)
            return 1
        print("wrote %s" % EMPTY_RATES)
        return 0

    if a.hosts:
        h = resolve_hosts(P.records())
        got = sum(1 for v in h.values() if v)
        where = "NOT SAVED (write denied)" if _HOSTS_DENIED else HOSTS
        print(f"{got}/{len(h)} sources resolved to a wiki host  ->  {where}")
        for s, v in sorted(h.items()):
            if not v:
                print(f"   unresolved: {s}")
        # The whole point of `--hosts` is the file; resolving the map and failing to save it is
        # a failed run, not a successful one with a note attached.
        return 1 if _HOSTS_DENIED else 0

    if a.roll:
        recs = P.records()
        hosts = resolve_hosts(recs, verify=False)
        done = roll(recs, hosts, workers=a.workers, limit=a.limit, only=a.only)
        # THE COUNTERS REACH THE EXIT CODE (order f4f4b9d5f935, run40 sweep). This threw
        # `roll()`'s return away and returned 0 unconditionally, so a roll with NO jobs at all --
        # an empty or unresolved host map -- and a roll in which every entity's `evidence_for()`
        # raised both exited 0.
        #
        # That is not a cosmetic loss. `overnight.py` launches this exact invocation as a
        # supervised background job and its `join()` only tails the log and reports anything
        # other than "ok" when rc != 0, so to the ONE automated consumer of this exit code a roll
        # that mined nothing was indistinguishable from a roll that mined everything. The crawl
        # can then be dead for hours with the supervisor reporting it fine, which is this
        # project's signature failure -- a fault that presents as nothing at all.
        #
        # The sibling branches in this same file already do it: `--hosts` twenty lines up returns
        # `1 if _HOSTS_DENIED else 0`, and `resolve_hosts`'s own docstring promises "main() exits
        # nonzero on it". `--roll` was the one place the pattern was never applied, even though
        # `roll()` has always returned exactly the counters needed.
        #
        # THREE FAILING CONDITIONS, each named on stdout so the rc is never the only evidence.
        # A denied WIKI_HOSTS.json write counts too, for the same reason `--hosts` counts it.
        _n = int((done or {}).get("n") or 0)
        _err = int((done or {}).get("errored") or 0)
        _bad = []
        if _HOSTS_DENIED:
            _bad.append("the WIKI_HOSTS.json write was denied")
        if not _n:
            _bad.append("the roll had NOTHING to do -- 0 entities were walked, which usually "
                        "means an empty or unresolved host map rather than a finished crawl")
        elif _err >= _n:
            _bad.append("every one of the %d entities walked raised in evidence_for(), so "
                        "nothing was mined" % _n)
        if _bad:
            print("\nROLL FAILED, exiting nonzero so the supervisor can see it: "
                  + "; ".join(_bad))
            return 1
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
