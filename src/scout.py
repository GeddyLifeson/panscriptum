#!/usr/bin/env python3
"""
SCOUT — find where a source's material lives, without a person doing the searching.

THE LAST MANUAL STEP
--------------------
`hostcheck --adopt` finds a WIKI for a source. `endpoint` can read an ordinary web page once
somebody registers its URL. Between those two sat the one step nothing could do: knowing that
KibblesTasty's material is at `kthomebrew.com` and on GM Binder in the first place. I found that
by searching the web myself, which makes the pipeline dependent on me being awake.

Homebrew is the hard case precisely because it is inconsistent -- a publisher site, a GM Binder
share link, a Homebrewery brew, a subreddit wiki, an itch.io page, sometimes all four for one
author. There is no registry to consult.

WHAT REPLACES THE SEARCH
------------------------
The model already knows. It has read the same internet, and asking it "where does this material
live" is a question it can answer far better than any URL pattern I could write. What it cannot
be trusted with is the ANSWER -- a model asked for a URL will produce a plausible one whether or
not it exists, which is the same failure mode as a model asked for a feat.

So the design is exactly the one that already works for feats: **the model proposes, the fetch
disposes.** Every candidate URL is fetched, and kept only if the page

    exists and returns real text, and
    CONTAINS THIS SOURCE'S OWN CATALOGUED ENTITY NAMES

That second test is the whole safety property. A hallucinated URL 404s. A real URL about the
wrong thing contains none of the names. Only a page that is actually about this material passes,
and the check costs one fetch.

Nothing is registered on the model's say-so. That is the difference between a scout and a rumour.
"""
import argparse
import json
import os
import re
import sys
import time

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(HERE, "src")
sys.path.insert(0, SRC)
import silence                                                          # noqa: E402

_BAD_CHARS = (chr(8), chr(11), chr(12), chr(7))
if any(c in open(os.path.abspath(__file__), encoding="utf-8").read() for c in _BAD_CHARS):
    raise SystemExit(__file__ + ": a regex escape was eaten in transit.")

LOG = os.path.join(HERE, "data", "SCOUT.json")
BLOCKED = os.path.join(HERE, "data", "SCOUT_BLOCKED.json")

# The project's honest crawler identity. A site that declines THIS is declining consent, and the
# correct response is to record that and stop asking -- not to put on a browser costume. The
# material behind a storefront is purchased content and belongs to whoever bought it.
_UA = ("PanscriptumResearchBot/1.0 (personal research archive; "
       "contact imarlonlee@gmail.com) python-urllib")

# A page must contain at least this fraction of the names probed against it. Low on purpose: an
# index page carries many names and a single class page carries one, and both are worth reading.
# The floor that matters is not "most names" but "more than a page about something else", and a
# page about something else scores zero.
MIN_NAME_HITS = 2
PROBE_NAMES = 25

SYSTEM = """You are asked where a body of tabletop-RPG or fiction material is published online.

Given a source name and a sample of the things catalogued under it, list the URLs where that
material is actually readable. Homebrew commonly lives on:
  a creator's own site, GM Binder (gmbinder.com/share/...), The Homebrewery
  (homebrewery.naturalcrit.com/share/...), D&D Wiki, DMs Guild, itch.io, a subreddit wiki,
  or a GitHub repository.

RULES
- Only URLs you actually believe exist. A plausible-looking guess is worse than nothing, because
  it costs a fetch and teaches nobody anything.
- Prefer pages that CONTAIN the material over pages that describe or sell it.
- Prefer an index or compendium page that holds many entries over one page per entry.
- If you do not know where this material lives, return an empty list. That is the correct answer
  far more often than a guess, and it is never wrong to give.

Return JSON only:
{"urls": ["https://...", ...], "note": "<one short line on what these are>"}"""

SCHEMA = {
    "type": "object",
    "properties": {"urls": {"type": "array", "items": {"type": "string"}},
                   "note": {"type": "string"}},
    "required": ["urls"],
}


def _ask(prompt):
    try:
        import read as R
        R.ensure_transport(verbose=False)
        return R._ask(R.config(), SYSTEM, prompt, SCHEMA)
    except Exception:
        silence.note("scout.py:_ask")
        return None


def _names_in(text, names):
    """How many of these catalogued names appear in the page.

    Case-insensitive and whole-name: a homebrew class called `Warden` should not match the word
    "warden" inside a sentence about prison guards, so the check requires the name with a
    boundary either side. Short names are skipped entirely -- a two-letter name matches
    everything and proves nothing.
    """
    low = text.lower()
    hits = 0
    for n in names:
        n = (n or "").strip().lower()
        if len(n) < 4:
            continue
        if re.search(r"(?<![a-z0-9])" + re.escape(n) + r"(?![a-z0-9])", low):
            hits += 1
    return hits


def verify(url, names):
    """Fetch a proposed URL and decide whether it is about this material.

    The failure REASON is recorded, not just the failure, because three very different things
    look identical as "no readable text" and only one of them is the model's fault:

        404 / no such host   the URL was invented. Nothing to do; do not try it again.
        403                  the page exists and declines automated readers. That is a real
                             finding -- the material is there and consent was withheld -- and it
                             belongs in front of the owner rather than in a retry loop.
        200 but no names     a real page about something else.

    Distinguishing them is what turns "the scout found nothing" into "these four are paid
    products behind a storefront and these three do not exist".
    """
    import urllib.error
    import urllib.request
    import endpoint as EP
    try:
        req = urllib.request.Request(url, headers={"User-Agent": _UA})
        with urllib.request.urlopen(req, timeout=40) as r:
            body = r.read().decode("utf-8", "replace")
    except urllib.error.HTTPError as e:
        silence.note("scout.py:verify-http")
        kind = "exists but declines readers" if e.code in (401, 403, 429) else f"HTTP {e.code}"
        return {"url": url, "ok": False, "why": kind, "code": e.code}
    except Exception as e:
        silence.note("scout.py:verify")
        return {"url": url, "ok": False, "why": "no such host or no route",
                "code": type(e).__name__}
    text = EP.html_text(body)
    if len(text) < 400:
        return {"url": url, "ok": False, "why": "page has almost no text (script-rendered?)"}
    hits = _names_in(text, names)
    return {"url": url, "ok": hits >= MIN_NAME_HITS, "hits": hits, "chars": len(text),
            "why": f"{hits} catalogued name(s) present"}


def scout(source, names, register=True):
    """Ask where the material lives, then prove each answer before believing it."""
    sample = [n for n in names if n and len(n) > 3][:PROBE_NAMES]
    prompt = (f"SOURCE: {source}\n"
              f"CATALOGUED UNDER IT: {', '.join(sample[:18])}\n\n"
              f"Where is this material readable online?")
    got = _ask(prompt)
    urls = [u for u in ((got or {}).get("urls") or []) if str(u).startswith("http")][:8]
    if not urls:
        return {"source": source, "proposed": 0, "kept": [], "note": "model proposed nothing"}

    kept, checked = [], []
    for u in urls:
        r = verify(u, sample)
        checked.append(r)
        if r["ok"]:
            kept.append(u)
    if kept and register:
        import endpoint as EP
        EP.register(source, kept)
        try:
            import feats as F
            hosts = json.load(open(F.HOSTS, encoding="utf-8"))
            hosts[source] = "pages:" + source
            with open(F.HOSTS, "w", encoding="utf-8") as f:
                json.dump(hosts, f, indent=1, sort_keys=True)
        except Exception:
            silence.note("scout.py:register-host")
    # Pages that exist and decline us are a finding for the owner, not a retry target.
    blocked = [c for c in checked if c.get("code") in (401, 403, 429)]
    if blocked:
        try:
            prev = {}
            if os.path.exists(BLOCKED):
                with open(BLOCKED, encoding="utf-8") as f:
                    prev = json.load(f)
            prev[source] = sorted({c["url"] for c in blocked} | set(prev.get(source) or []))
            with open(BLOCKED, "w", encoding="utf-8") as f:
                json.dump(prev, f, indent=1, sort_keys=True)
        except Exception:
            silence.note("scout.py:blocked")
    return {"source": source, "proposed": len(urls), "kept": kept, "checked": checked,
            "blocked": [c["url"] for c in blocked],
            "note": (got or {}).get("note", "")}


def hostless():
    """Sources with nowhere to read from — the only ones worth scouting."""
    import weave_index as WI
    import feats as F
    hosts = json.load(open(F.HOSTS, encoding="utf-8"))
    out = {}
    for r in WI.load_records():
        s = r["source"]
        if not hosts.get(s) and r.get("entries"):
            out[s] = [e.get("name") for e in r["entries"]]
    return out


def sweep(limit=None, register=True):
    todo = hostless()
    order = sorted(todo, key=lambda s: -len(todo[s]))
    if limit:
        order = order[:limit]
    print(f"{len(todo)} source(s) have nowhere to read from; scouting {len(order)}")
    results, found = [], 0
    for src in order:
        r = scout(src, todo[src], register=register)
        results.append(r)
        if r["kept"]:
            found += 1
            print(f"   FOUND  {src[:38]:<40}{len(r['kept'])} page(s)")
            for u in r["kept"]:
                print(f"            {u}")
        else:
            reasons = ", ".join(sorted({c.get("why", "?") for c in (r.get("checked") or [])}))
            print(f"   none   {src[:38]:<40}{reasons[:60]}")
    print(f"\n{found} of {len(order)} sources now have somewhere to read from")
    try:
        prev = json.load(open(LOG, encoding="utf-8")) if os.path.exists(LOG) else []
    except Exception:
        prev = []
    prev.append({"at": time.strftime("%Y-%m-%d %H:%M"), "results": results})
    with open(LOG, "w", encoding="utf-8") as f:
        json.dump(prev[-40:], f, indent=1)
    return results


def main():
    ap = argparse.ArgumentParser(description="find where a source's material lives")
    ap.add_argument("--limit", type=int, default=None, help="scout only the N largest")
    ap.add_argument("--dry", action="store_true", help="verify but do not register")
    ap.add_argument("--source", help="one source by exact name")
    a = ap.parse_args()
    if a.source:
        todo = hostless()
        names = todo.get(a.source)
        if names is None:
            import weave_index as WI
            rec = next((r for r in WI.load_records() if r["source"] == a.source), None)
            names = [e.get("name") for e in (rec or {}).get("entries", [])]
        r = scout(a.source, names or [], register=not a.dry)
        print(json.dumps(r, indent=1)[:2000])
        return 0
    sweep(limit=a.limit, register=not a.dry)
    return 0


if __name__ == "__main__":
    sys.exit(main())
