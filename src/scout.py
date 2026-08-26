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
# WHEN EACH SOURCE WAS LAST ATTEMPTED, which is what makes `sweep`'s window a ROTATION rather
# than a cap. Kept beside the other scout artifacts, and absent-means-never-attempted, so a
# source added tomorrow sorts to the front on its own without anything having to seed it.
ATTEMPTS = os.path.join(HERE, "data", "SCOUT_ATTEMPTS.json")


def _land(path, obj, sort_keys=True):
    """Write a shared artifact whole or not at all -- tmp + `silence.replace_retry`.

    WIKI_HOSTS.json in particular is written from here AND from two call sites in
    `hostcheck.py`, and read by several long-running jobs. A bare `open(path, "w")` truncates
    before json.dump starts, so a losing writer leaves the host map empty or unparseable for
    every reader -- and an empty host map reads downstream as "no source has a wiki". 2026-08-24."""
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(obj, f, indent=1, sort_keys=sort_keys)
    silence.replace_retry(tmp, path)

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

    THE BAR CANNOT BE HIGHER THAN THE EVIDENCE AVAILABLE. `MIN_NAME_HITS` is 2, and `scout()`
    probes only names longer than three characters, so a source catalogued with a single usable
    name hands this function a one-name list -- and no page in existence, including the right one,
    can score two hits against a list of one. Those sources failed on every run for ever while
    reporting the ordinary "0 catalogued name(s) present", which reads as "the model guessed
    wrong" rather than "this check was unsatisfiable before it was called". Measured when this was
    fixed: 2 of the 15 hostless sources were in that state ('aurora_mods (Way of the Inkmaster)'
    and 'the Sex Worker background', one name each). This is the mirror of a net that cannot fail
    -- a check that cannot pass -- and it is the same class of fault run #27 fixed in
    magnitude.py.

    So the requirement is `min(MIN_NAME_HITS, len(usable names))`, never below one. This does not
    lower the bar for a normal source: with two or more probeable names the threshold is still 2.
    It lowers it only where 2 was unreachable, and the intent stated at MIN_NAME_HITS survives
    intact there -- the floor that matters is "more than a page about something else", and a page
    about something else still scores zero. `needed` is returned alongside `hits` so a reader of
    the result can see which bar was applied rather than having to infer it.
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
    probeable = sum(1 for n in names if (n or "").strip() and len((n or "").strip()) > 3)
    needed = max(1, min(MIN_NAME_HITS, probeable))
    return {"url": url, "ok": hits >= needed, "hits": hits, "needed": needed,
            "chars": len(text),
            "why": f"{hits} catalogued name(s) present, {needed} needed"}


def scout(source, names, register=True):
    """Ask where the material lives, then prove each answer before believing it."""
    sample = [n for n in names if n and len(n) > 3][:PROBE_NAMES]
    prompt = (f"SOURCE: {source}\n"
              f"CATALOGUED UNDER IT: {', '.join(sample[:18])}\n\n"
              f"Where is this material readable online?")
    got = _ask(prompt)
    # Every URL the model proposes gets PROVEN, not the first eight of them. The prompt above
    # explicitly invites a spread across seven or more platforms (own site, GM Binder,
    # Homebrewery, D&D Wiki, DMs Guild, itch.io, subreddit wiki, GitHub) for one creator, so a
    # well-documented author is precisely the case where a ninth URL exists -- and the cap sat
    # BEFORE verification, so the dropped candidates were never even tested. Verification is one
    # cheap fetch each. Uncapped 2026-08-24 (Hard Rule 0).
    urls = [u for u in ((got or {}).get("urls") or []) if str(u).startswith("http")]
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
            _land(F.HOSTS, hosts)
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
            _land(BLOCKED, prev)
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
    """Scout the hostless sources, oldest attempt first. -> [result].

    HARD RULE 0, AND THE SHAPE THAT LOOKED LIKE COMPLIANCE. This ordered its work-list by entry
    count and then took `order[:limit]`, with `foreman.scout_hostless()` calling it as
    `sweep(limit=4)` on a 30-second loop. Ranking is allowed and truncating is not, and the
    reason is visible here rather than theoretical: a source LEAVES `hostless()` only when a
    scout SUCCEEDS. A source that keeps failing therefore stays hostless, stays among the four
    largest, and is re-scouted every thirty seconds for ever -- while everything ranked fifth
    and below is never attempted once. The window could not rotate, because the only thing that
    moved a source out of it was the very success that was not happening. Measured at the time
    this was fixed: 15 hostless sources, of which 4 could ever be reached.

    So the ordering is now LAST-ATTEMPTED FIRST, entry count only breaking ties among equally
    stale sources. `limit` survives and still means "how much work this cycle" -- it is a rate,
    which is a cost decision the caller is entitled to make -- but it no longer decides which
    sources exist. Every source reaches the front of the queue by waiting, so the universe is
    whole and merely spread over cycles. What is deferred is PRINTED, because a window nobody
    can see the far side of reads exactly like a complete list.
    """
    todo = hostless()
    try:
        seen = json.load(open(ATTEMPTS, encoding="utf-8")) if os.path.exists(ATTEMPTS) else {}
    except Exception:
        silence.note("scout.py:attempts-unreadable")
        seen = {}                     # unreadable ledger -> everything reads as never attempted
    # Never-attempted sorts first (0.0), then longest-waiting, then largest -- the old
    # preference, kept as the TIE-BREAK it should always have been.
    order = sorted(todo, key=lambda s: (float(seen.get(s) or 0.0), -len(todo[s])))
    deferred = []
    if limit:
        deferred = order[limit:]
        order = order[:limit]
    print(f"{len(todo)} source(s) have nowhere to read from; scouting {len(order)}")
    if deferred:
        # NOT a truncation of the universe: these are ahead of nobody and behind everybody,
        # and each moves to the front by waiting. Named so the deferral is legible.
        print(f"   {len(deferred)} waiting for a later cycle (longest-waiting first): "
              + ", ".join(s[:30] for s in deferred))
    # STAMPED BEFORE THE WORK, NOT AFTER. A source that crashes the scout must still count as
    # attempted, or it sorts to the front again next cycle and pins the window exactly the way
    # the entry-count ordering did -- the same bug wearing the fix's clothes.
    now = time.time()
    for src in order:
        seen[src] = now
    _land(ATTEMPTS, seen)
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
        silence.note("scout.py:241")
        prev = []
    prev.append({"at": time.strftime("%Y-%m-%d %H:%M"), "results": results})
    _land(LOG, prev[-40:], sort_keys=False)
    return results


def main():
    ap = argparse.ArgumentParser(description="find where a source's material lives")
    ap.add_argument("--limit", type=int, default=None,
                    help="how many to scout this cycle, longest-waiting first; the rest are "
                         "named and reached on a later cycle, never dropped")
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
