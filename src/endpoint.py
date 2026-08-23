#!/usr/bin/env python3
"""
ENDPOINT — how to read a wiki that is not Fandom, and not Wikipedia, and not cooperative.

THE ASSUMPTION THAT WAS BAKED IN
--------------------------------
Every request in this project went to `https://{host}/api.php`, with one special case bolted on
for Wikipedia's `/w/api.php`. That assumption is wrong in three separate ways, and each one
looked like an absence rather than a failure:

    a self-hosted MediaWiki serves /api.php but is not Fandom   rimworldwiki.com
    a wiki serves its API at /w/api.php and is not Wikipedia     many independent wikis
    a wiki CLOSES its API to anonymous users entirely            dandwiki.com

That last one is the interesting case and it is the one the owner asked about. D&D Wiki holds
the homebrew — KibblesTasty, Mage Hand Press, Yorviing's, the whole third-party shelf — which is
most of the sources this library has no host for. Its `api.php` answers every request with
HTTP 403: *"To reduce server load, we had to restrict this action to logged in users only."*

Read as a 403 that is a closed door. It is not:

    https://www.dandwiki.com/w/index.php?title=Barbarian&action=raw   ->  {{dab|term1=Barbarian}}

`action=raw` is a plain index.php view, not an API action, and it is open. It returns exactly
what `prop=revisions` would have returned — the wikitext — one title per request instead of
fifty. That is slower and it is not nothing, which is the whole difference.

WHAT THIS MODULE IS
-------------------
A resolver that answers, per host and once, HOW to read it:

    MODE_API   batched MediaWiki API at some path. Fifty titles a request.
    MODE_RAW   index.php?action=raw, one title a request, no API at all.
    MODE_DEAD  neither works.

Detection is by probe, not by a list of hostnames, because a list is a thing somebody has to
maintain and this project has been bitten by every list it ever wrote. The answer is cached to
`data/ENDPOINTS.json` so the probe cost is paid once per host per project, not per request.
"""
import argparse
import json
import os
import re
import sys
import threading
import urllib.error
import urllib.parse
import urllib.request

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import silence                                                          # noqa: E402

_BAD_CHARS = (chr(8), chr(11), chr(12), chr(7))
if any(c in open(os.path.abspath(__file__), encoding="utf-8").read() for c in _BAD_CHARS):
    raise SystemExit(__file__ + ": a regex escape was eaten in transit.")

CACHE = os.path.join(HERE, "data", "ENDPOINTS.json")
MODE_API = "api"
MODE_RAW = "raw"
MODE_DEAD = "dead"

API_PATHS = ("/api.php", "/w/api.php", "/wiki/api.php")
RAW_PATHS = ("/w/index.php", "/index.php", "/wiki/index.php")

_LOCK = threading.Lock()
_MEM = None


def _load():
    global _MEM
    with _LOCK:
        if _MEM is None:
            try:
                with open(CACHE, encoding="utf-8") as f:
                    _MEM = json.load(f)
            except Exception:
                silence.note("endpoint.py:load")
                _MEM = {}
        return _MEM


def _save():
    with _LOCK:
        if _MEM is None:
            return
        try:
            os.makedirs(os.path.dirname(CACHE), exist_ok=True)
            tmp = CACHE + ".tmp"
            with open(tmp, "w", encoding="utf-8") as f:
                json.dump(_MEM, f, indent=1, sort_keys=True)
            os.replace(tmp, CACHE)
        except Exception:
            silence.note("endpoint.py:save")


def _get(url, timeout=25):
    import feats as F
    F._throttle(urllib.parse.urlparse(url).netloc)
    req = urllib.request.Request(url, headers={"User-Agent": F.UA})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read().decode("utf-8", "replace")


# A DEAD verdict expires; a live one is forever. The asymmetry is the point: a host that once
# answered its API keeps answering it (MediaWiki paths do not move), but "dead" is a claim about
# one afternoon's network. Today the entire fandom.com domain dropped this machine's connections
# at the socket for a while -- any host probed during such a window would have been branded
# MODE_DEAD in a cache with no expiry, permanently unreadable for the price of one bad hour.
# 2,958 dead entries are on file; none of the real assigned hosts is among them, by luck of the
# cache's mtime alone.
DEAD_TTL = 24 * 3600

def detect(host, force=False):
    """How to read this host. Probed once; a DEAD verdict is re-probed after DEAD_TTL.

    Order matters: the API is tried first because one request answers for fifty titles, and raw
    is the fallback because one request answers for one. A host that can do both should do the
    cheap thing.
    """
    mem = _load()
    if not force and host in mem:
        got = mem[host]
        if got.get("mode") != MODE_DEAD:
            return got
        import time as _t
        if _t.time() - (got.get("at") or 0) < DEAD_TTL:
            return got
        # dead verdict has aged out -- fall through and probe again

    found = {"mode": MODE_DEAD, "path": None}
    for path in API_PATHS:
        try:
            body = _get(f"https://{host}{path}?action=query&format=json&meta=siteinfo")
            d = json.loads(body)
            if isinstance(d, dict) and ("query" in d or "batchcomplete" in d):
                found = {"mode": MODE_API, "path": path}
                break
        except Exception:
            silence.note("endpoint.py:detect-api")

    if found["mode"] == MODE_DEAD:
        for path in RAW_PATHS:
            try:
                body = _get(f"https://{host}{path}?title=Main_Page&action=raw")
                # A raw view returns wikitext. An error page returns HTML, and the difference
                # is unmistakable at the first character.
                if body and not body.lstrip().lower().startswith(("<!doctype", "<html")):
                    found = {"mode": MODE_RAW, "path": path}
                    break
            except Exception:
                silence.note("endpoint.py:detect-raw")

    if found["mode"] == MODE_DEAD:
        import time as _t
        found["at"] = _t.time()
    mem[host] = found
    _save()
    return found


def api_url(host):
    """The API base for this host, or None when it has no usable API."""
    d = detect(host)
    return f"https://{host}{d['path']}" if d["mode"] == MODE_API else None


def raw_url(host, title):
    d = detect(host)
    if d["mode"] != MODE_RAW:
        return None
    q = urllib.parse.urlencode({"title": title.replace(" ", "_"), "action": "raw"})
    return f"https://{host}{d['path']}?{q}"


def fetch_raw(host, titles, workers=2):
    """{title: wikitext} for a raw-only host, one request per title.

    Deliberately few workers. A wiki that closed its API did so to reduce load, and answering
    that by opening eight connections would be both rude and a fast route to being blocked
    outright — which would turn a slow source into a dead one.
    """
    from concurrent.futures import ThreadPoolExecutor
    out = {}

    def one(t):
        url = raw_url(host, t)
        if not url:
            return t, None
        try:
            body = _get(url, timeout=40)
        except urllib.error.HTTPError:
            silence.note("endpoint.py:fetch_raw-http")
            return t, None
        except Exception:
            silence.note("endpoint.py:fetch_raw")
            return t, None
        if not body or body.lstrip().lower().startswith(("<!doctype", "<html")):
            return t, None
        return t, body

    with ThreadPoolExecutor(max_workers=workers) as ex:
        for t, body in ex.map(one, titles):
            if body:
                out[t] = body
    return out


def exists_raw(host, titles, workers=2):
    """Which of these titles the host actually serves. The raw-mode answer to a titles probe."""
    return sorted(fetch_raw(host, titles, workers=workers))


def main():
    ap = argparse.ArgumentParser(description="how to read a wiki that is not Fandom")
    ap.add_argument("hosts", nargs="*", help="hosts to probe")
    ap.add_argument("--force", action="store_true", help="re-probe even if cached")
    ap.add_argument("--list", action="store_true", help="show everything already known")
    a = ap.parse_args()

    if a.list or not a.hosts:
        mem = _load()
        if not mem:
            print("nothing probed yet")
            return 0
        by = {}
        for h, d in sorted(mem.items()):
            by.setdefault(d["mode"], []).append((h, d["path"]))
        for mode in (MODE_API, MODE_RAW, MODE_DEAD):
            rows = by.get(mode) or []
            print(f"\n{mode.upper()}  ({len(rows)})")
            for h, path in rows:
                print(f"   {h:<40}{path or ''}")
        return 0

    for h in a.hosts:
        d = detect(h, force=a.force)
        print(f"   {h:<40}{d['mode']:<6}{d['path'] or ''}")
    return 0


if __name__ == "__main__":
    sys.exit(main())


# ============================================================================ mode: html
#
# HOMEBREW DOES NOT LIVE ON WIKIS.
#
# The owner: "for a lot of the homebrew stuff you might have to do a little bit of internet
# scouring for more information since homebrew can be inconsistent with where stuff is kept."
# Exactly right, and it is the reason 6,110 catalogued entries are uncitable. KibblesTasty --
# 1,335 of them -- lives at kthomebrew.com and on GM Binder. Neither is MediaWiki, so both modes
# above return `dead` and the miner has nowhere to read.
#
# So a third mode: fetch the page and take the text out of the HTML. It is cruder than an API and
# it is what the material actually is. One important consequence: there is no title lookup, so a
# source in HTML mode is read from a LIST OF PAGES rather than by asking for an entity by name --
# see data/SOURCE_PAGES.json. The reader's own name-matching then does the attribution, which is
# what it already does for shared wiki pages.

MODE_HTML = "html"

_TAG = re.compile(r"<[^>]+>")
_SCRIPT = re.compile(r"(?is)<(script|style|nav|footer|header|noscript)[^>]*>.*?</\1>")
_WS = re.compile(r"[ \t\r\f\v]+")
_BLANK = re.compile(r"\n{3,}")


def html_text(body):
    """Readable text out of an HTML page.

    Deliberately not a parser. A homebrew page is prose in divs, and everything a parser would
    buy -- structure, attributes, the DOM -- is irrelevant to a reader that wants sentences. What
    matters is removing the things that produce FALSE sentences: script bodies, stylesheets, and
    navigation, all of which read as text once the tags are stripped and none of which any entity
    ever did.
    """
    body = _SCRIPT.sub(" ", body or "")
    body = re.sub(r"(?i)<br\s*/?>", chr(10), body)
    body = re.sub(r"(?i)</(p|div|li|h[1-6]|tr)>", chr(10), body)
    body = _TAG.sub(" ", body)
    for a, b in (("&nbsp;", " "), ("&amp;", "&"), ("&lt;", "<"), ("&gt;", ">"),
                 ("&quot;", '"'), ("&#39;", "'"), ("&mdash;", "--"), ("&ndash;", "-")):
        body = body.replace(a, b)
    body = _WS.sub(" ", body)
    body = chr(10).join(ln.strip() for ln in body.splitlines())
    return _BLANK.sub(chr(10) + chr(10), body).strip()


def fetch_html(urls, workers=2):
    """{url: text} for a list of ordinary web pages.

    Two workers, and politely. These are one-author sites on shared hosting, not Fandom's CDN,
    and the entire point of reading them is that the author put the material there to be read.
    """
    from concurrent.futures import ThreadPoolExecutor
    out = {}

    def one(u):
        try:
            body = _get(u, timeout=45)
        except Exception:
            silence.note("endpoint.py:fetch_html")
            return u, None
        text = html_text(body)
        return u, (text if len(text) > 400 else None)

    with ThreadPoolExecutor(max_workers=workers) as ex:
        for u, t in ex.map(one, list(urls)):
            if t:
                out[u] = t
    return out


PAGES_FILE = os.path.join(HERE, "data", "SOURCE_PAGES.json")


def source_pages(source):
    """The URLs registered for a source that has no wiki. {} when it has none."""
    try:
        with open(PAGES_FILE, encoding="utf-8") as f:
            return (json.load(f) or {}).get(source) or []
    except Exception:
        silence.note("endpoint.py:source_pages")
        return []


def register(source, urls):
    """Record where a source's material actually lives."""
    try:
        with open(PAGES_FILE, encoding="utf-8") as f:
            d = json.load(f)
    except Exception:
        d = {}
    d[source] = sorted(set((d.get(source) or []) + list(urls)))
    os.makedirs(os.path.dirname(PAGES_FILE), exist_ok=True)
    tmp = PAGES_FILE + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(d, f, indent=1, sort_keys=True)
    os.replace(tmp, PAGES_FILE)
    return d[source]
