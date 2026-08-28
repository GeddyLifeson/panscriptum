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
import time
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
# The hosts THIS process has probed since its last landed save. The save merges only these into
# whatever is on disk, never the whole of `_MEM` -- see `_save()`.
_DIRTY = set()
# Serialises this process's own savers so two threads do not spend their attempts losing to each
# other. Always taken BEFORE `_LOCK`, never the other way round.
_SAVE_LOCK = threading.Lock()
SAVE_ATTEMPTS = 8


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
    """Land the probe cache through a COMPARE-AND-SWAP. -> True if this process's probes landed.

    This used to be a hand-rolled `open(CACHE + ".tmp")` + bare `os.replace()`. Both halves of
    that were the shapes `silence.write_json` exists to make unavailable. `ENDPOINTS.json` is
    written by every process that probes a host -- `detect()` is reached from `feats.py`,
    `hostcheck.py` and `completeness.py`, several of them threaded -- so the fixed `.tmp`
    suffix let two writers collide on the temp file itself and let the loser replace the
    winner's cache with a partial one; and the bare `os.replace` raises `PermissionError` on
    Windows for as long as any reader holds the target open, which is the collision that took
    an assay worker down mid-batch on 2026-08-23 (WinError 5) and is exactly why
    `silence.replace_retry` was written. Here the denial was swallowed by the `except` below
    and merely noted, so a freshly-earned MODE_API/MODE_RAW/MODE_DEAD verdict was dropped and
    the host re-probed next run -- wasted network against a pipeline that paces itself per
    host on purpose. `write_json` carries pid and thread in the temp name and retries the
    rename, so the write lands instead of vanishing. (run33)

    ATOMIC WAS NOT ENOUGH, AND THIS MODULE-LEVEL CACHE IS THE SAME LOST UPDATE THROUGH A SECOND
    DOOR (order 232b4f3ffc79, run #36). `register()` below was given a compare-and-swap earlier
    this shift for exactly this shape; `_MEM` was not, and `_MEM` is worse, because it is a
    read-ONCE cache. A long-running miner loads `ENDPOINTS.json` at its first `detect()` and then
    writes that whole snapshot back after every probe, for hours. Two such processes -- the
    scheduled pass and a targeted `--force` probe, which is the normal situation here -- each land
    a complete, consistent, atomic file that predates every host the OTHER one probed. Nothing
    fails and nothing is torn; verdicts simply disappear, and a disappeared verdict costs a live
    re-probe against hosts this project has already been IP-banned by once.

    So the write is a merge, not an overwrite: re-read the file, overlay ONLY the hosts this
    process actually probed (`_DIRTY`), and swap only if the file still holds what was read. That
    is the pure key-wise union `register()` performs, and re-applying it to the winner's copy is
    exactly right -- the other writer's hosts survive and ours are added beside them.

    A refusal is NOT raised. `detect()` has a verdict to return and its caller has network work to
    do; the hosts stay in `_DIRTY` and the next probe's save carries them, which is this project's
    established "the caller's write lands next round".
    """
    with _SAVE_LOCK:
        with _LOCK:
            if _MEM is None or not _DIRTY:
                return True
            mine = {h: _MEM[h] for h in _DIRTY if h in _MEM}
        if not mine:
            return True
        last_why = "not attempted"
        for attempt in range(SAVE_ATTEMPTS):
            # The digest is taken BEFORE the read, so anything that lands between the two makes
            # the swap fail closed rather than pass on a copy that is already behind.
            digest = silence.digest_of(CACHE)
            disk = {}
            if os.path.exists(CACHE):
                try:
                    with open(CACHE, encoding="utf-8") as f:
                        disk = json.load(f)
                except Exception:
                    # A probe cache is REGENERABLE -- every entry can be re-earned by asking the
                    # host again -- so an unreadable one is healed rather than preserved, which
                    # is what `_load()` above already does with the same file. This is the one
                    # place that reasoning applies; it would be wrong for WIKI_HOSTS.json.
                    silence.note("endpoint.py:save-reread")
                    disk = {}
            if not isinstance(disk, dict):
                silence.note("endpoint.py:save-nondict")
                disk = {}
            disk.update(mine)
            tmp = "%s.%d.%d.tmp" % (CACHE, os.getpid(), attempt)
            try:
                os.makedirs(os.path.dirname(CACHE), exist_ok=True)
                with open(tmp, "w", encoding="utf-8") as f:
                    json.dump(disk, f, indent=1, sort_keys=True)
            except Exception:
                silence.note("endpoint.py:save")
                return False
            landed, why = silence.replace_if_unchanged(tmp, CACHE, digest)
            if landed:
                with _LOCK:
                    _DIRTY.difference_update(mine)
                    # The merged file is now the truth, and it holds the OTHER writers' hosts
                    # too. Folding it back into `_MEM` is what stops this cache being a
                    # read-once snapshot that grows staler for the life of the process --
                    # except for hosts probed while this save was in flight, which are still
                    # dirty and whose in-memory verdict is the fresher one.
                    for h, v in disk.items():
                        if h not in _DIRTY:
                            _MEM[h] = v
                return True
            last_why = why
            try:
                os.remove(tmp)
            except OSError:
                silence.note("endpoint.py:save-tmp-cleanup")
            time.sleep(0.05 * (attempt + 1))
        silence.note("endpoint.py:save-contended")
        print("endpoint: ENDPOINTS.json changed under this writer on all %d attempts; %d probe "
              "verdict(s) kept in memory for the next save: %s"
              % (SAVE_ATTEMPTS, len(mine), last_why), file=sys.stderr)
        return False


# Hosts whose edge refuses every non-browser client outright (dandwiki: HTTP 403 to any
# API path and any bot UA, while a browser UA reads the same HTML fine). Owner ruling
# 2026-08-24 ("FIX IT ALL", after the politeness question sat flagged since run #1): read
# them as a browser would -- same pages, same rate a patient human produces. The throttle
# below already paces per-host; dandwiki gets an extra-slow gap in feats.HOST_PAUSE.
UA_OVERRIDES = {
    "www.dandwiki.com": ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                         "(KHTML, like Gecko) Chrome/126.0 Safari/537.36"),
}


def _get(url, timeout=25):
    import feats as F
    host = urllib.parse.urlparse(url).netloc
    F._throttle(host)
    req = urllib.request.Request(url, headers={"User-Agent": UA_OVERRIDES.get(host, F.UA)})
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
    # Under the cache's own lock: the write was accidentally-safe GIL behaviour, not design.
    # `_DIRTY` is what makes `_save()` a merge rather than an overwrite -- it is the record of
    # what THIS process actually earned, as opposed to what it happened to read at startup.
    with _LOCK:
        mem[host] = found
        _DIRTY.add(host)
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
        except urllib.error.HTTPError as e:
            # A REFUSAL IS NOT AN ABSENCE. This returned None for every HTTP status, so a 403,
            # a 429 or a 500 reached the caller as the exact same answer a genuine 404 gives --
            # "this page does not exist" -- and a rate-limit during a raw pass was therefore
            # filed as permanent absence. Same failure family as wiki_source.page_text()'s
            # abandon-on-first-error: a transient wearing the face of settled fact.
            #
            # The signature is unchanged (callers in feats.py and hostcheck.py read only
            # presence), so the fix is to make the two cases legible in the ledger, where the
            # counts are what tell a real block apart from a wiki that simply lacks the page.
            # 404/410 are the only statuses that actually mean "not here". (BUGS m15.)
            if getattr(e, "code", None) in (404, 410):
                silence.note("endpoint.py:fetch_raw-absent")
            else:
                silence.note("endpoint.py:fetch_raw-refused-%s" % getattr(e, "code", "?"))
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
    """The URLs registered for a source that has no wiki. [] when it has none."""
    try:
        with open(PAGES_FILE, encoding="utf-8") as f:
            return (json.load(f) or {}).get(source) or []
    except Exception:
        silence.note("endpoint.py:source_pages")
        return []


def register(source, urls):
    """Record where a source's material actually lives.

    A REGISTRY WE COULD NOT READ IS NEVER REPLACED BY ONE WE INVENTED.

    Until run #26 this did `except Exception: d = {}` and then wrote `d` back over the whole
    file, so ANY failure to read -- a torn file from a concurrent writer, a Norton object-lock,
    a truncated tail -- silently republished the registry containing ONE source and erased every
    other source's registered pages. Nothing restored them; `source_pages()` would simply answer
    "none" ever after, and a source with no wiki and no registered pages is uncitable.

    That is the project's own lesson 10 -- "a guard can fail by doing the thing it prevents" --
    reached in a second file: run #24 found `write_record` overwriting the disk copy it could not
    read, and this is the same sentence in a different module. The two cases are distinguished
    now, because they are genuinely different facts:
      - the file is ABSENT       -> `{}` is the truth, and writing it is correct;
      - the file is UNREADABLE   -> we know nothing, and the only safe act is to not write.
    Raising rather than returning quietly is deliberate: the caller asked to record something,
    and reporting success while dropping it is how a registry rots without anyone noticing.

    The write itself goes through a COMPARE-AND-SWAP, not a bare atomic write: this file is
    written from every process that probes an endpoint, and a shared `PAGES_FILE + ".tmp"` is
    the collision m100 retired repo-wide.

    ATOMIC WAS NOT ENOUGH, AND THAT IS THE HALF THIS FUNCTION WAS STILL MISSING (order
    6dc3b3682fc8, run #36). `silence.write_json` closed the TORN-FILE hazard -- nobody ever sees
    a half-written registry. It has nothing to say about STALENESS, which is a different fault
    with the same victim: two processes registering pages for two DIFFERENT sources both read
    the file, both mutate their own key in their own in-memory copy, and both land the WHOLE
    dict. The second writer's copy predates the first writer's key, so it lands complete,
    consistent, atomic, and one source short. Nothing failed. That is the m42 lost-update shape
    `silence.replace_if_unchanged` exists for and that `scout._mutate`, `workorders._mutate` and
    `runguard._land_claim` were all moved onto the same day; this call site was simply missed.

    ON A REFUSAL WE RE-READ AND RE-MERGE RATHER THAN GIVING UP, because the merge is a pure
    union and re-applying it to the winner's copy is exactly right -- the other writer's key
    survives and ours is added beside it. Only a run of consecutive refusals raises, and raising
    is deliberate for the same reason the unreadable branch above raises: the caller asked to
    record something, and reporting success while dropping it is how a registry rots without
    anyone noticing.
    """
    os.makedirs(os.path.dirname(PAGES_FILE), exist_ok=True)
    last_why = "not attempted"
    for attempt in range(8):
        # The digest is taken BEFORE the read, so anything that lands between the two makes the
        # swap fail closed rather than pass on a copy that is already behind.
        digest = silence.digest_of(PAGES_FILE)
        d = {}
        if os.path.exists(PAGES_FILE):
            try:
                with open(PAGES_FILE, encoding="utf-8") as f:
                    d = json.load(f)
            except Exception:
                silence.note("endpoint.py:register-unreadable")
                raise
            if not isinstance(d, dict):
                silence.note("endpoint.py:register-nondict")
                raise ValueError("SOURCE_PAGES.json is not an object; refusing to overwrite it")
        d[source] = sorted(set((d.get(source) or []) + list(urls)))
        tmp = "%s.%d.%d.tmp" % (PAGES_FILE, os.getpid(), attempt)
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(d, f, indent=1, sort_keys=True, ensure_ascii=False)
        landed, why = silence.replace_if_unchanged(tmp, PAGES_FILE, digest)
        if landed:
            return
        last_why = why
        try:
            os.remove(tmp)
        except OSError:
            silence.note("endpoint.py:register-tmp-cleanup")
        time.sleep(0.05 * (attempt + 1))
    silence.note("endpoint.py:register-contended")
    # No `return d[source]` below this: it was unreachable behind an unconditional raise (order
    # 300c8d62a250), and a dead line that LOOKS like a success path is how a reader concludes
    # this function returns the registered pages. It returns None on success, and raises here.
    raise RuntimeError("SOURCE_PAGES.json changed under this writer on every one of 8 attempts, "
                       "so %r's pages were NOT recorded: %s" % (source, last_why))
