#!/usr/bin/env python3
"""
SCOPE — the largest arena a fiction's conflicts are decided in, which is what bounds the Anchor.

Part Three fixes the integer Magnitude from the best-attested HEGEMONIC feat: what scale of
conflict an entity can DECIDE, not what it can break. Every automated attempt at that has
under-anchored, and the reason is structural rather than a tuning fault:

  * feat sentences never state hegemony. A wiki says what someone destroyed, never what their
    victory settled, so no amount of mining surfaces it.
  * the per-source ceilings cannot supply it either -- 203 of 211 sources carry
    `provisional_magnitude: unassayed`, because the evidence gate demoted them and was right to.
  * Rosetta covers roughly a hundred characters, all in two franchises.

So the anchor had no input from anywhere, and the model fell back on reading the biggest
destruction feat and anchoring there -- which is exactly what Part Three forbids, and why
Kenshiro anchors M3 without cracking continents.

What CAN be established is the scale the fiction itself operates at. A being cannot decide a
conflict larger than the one its story contains: whatever Luffy does, One Piece is a story about
one planet, and whatever Kenshiro does, Fist of the North Star is a story about a ruined Earth.
That gives the anchor a CEILING drawn from the work rather than from the entity, and the entity
is then placed at or below it.

READING THE SIGNAL
------------------
Not by frequency. Every fiction says "planet" constantly, so counting words puts Marvel -- a
multiverse with a published map of numbered realities -- at planet scale on 112 mentions against
61 for universe. The signal is the HIGHEST tier that appears with real usage, not the commonest,
because a story that discusses universes at all is a story where universes are in play.
"""
import argparse
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import feats as F                                                       # noqa: E402
import silence

_BAD_CHARS = (chr(8), chr(11), chr(12), chr(7))
if any(c in open(os.path.abspath(__file__), encoding="utf-8").read() for c in _BAD_CHARS):
    raise SystemExit(__file__ + ": a regex escape was eaten in transit.")

OUT = os.path.join(HERE, "data", "SCOPE.json")

# Ordered low to high. The band is the CEILING a fiction of this scope can support, taken from
# Part Three's own table of what each rung can threaten.
TIERS = [
    ("nation", r"\bnations?\b|\bkingdoms?\b|\bempires?\b|\bcit(?:y|ies)\b", "M1"),
    ("continent", r"\bcontinents?\b", "M2"),
    ("planet", r"\bplanets?\b|\bworlds?\b", "M3"),
    ("star system", r"star systems?|solar systems?|interstellar", "M4"),
    ("galaxy", r"\bgalax(?:y|ies)\b|galactic", "M6"),
    ("universe", r"\buniverses?\b|universal", "M7"),
    ("multiverse", r"\bmultiverses?\b|multiversal|parallel universes|"
                   r"alternate realit(?:y|ies)", "M8"),
]
_RE = [(lab, re.compile(pat, re.I), band) for lab, pat, band in TIERS]

# Below this a mention is incidental -- one stray line about "another universe" does not make a
# fiction universal. Above it the concept is load-bearing in the setting.
MIN_MENTIONS = 10

QUERIES = ["cosmology universe world setting", "multiverse", "universe", "world"]

# THE CONTRACT A STORED RECORD WAS BUILT UNDER, stamped into the record itself.
#
# `build()` skips any host already keyed in SCOPE.json, which is right for a cache and wrong for
# a cache whose PRODUCER has been repaired. The srlimit=3 + `titles[:8]` truncation fix landed
# after data/SCOPE.json was written (file dated 2026-08-21 15:50), and membership-by-key meant no
# run could ever reach those records again: 80 of the 146 scored hosts sat exactly ON the removed
# eight-page cap, which is that cap's fingerprint, and `magnitude.host_ceiling` was still clamping
# every anchor against them. A cap that survives its own repair by hiding in the memoisation is
# the same fault one layer out.
#
# BUMP THIS whenever anything that changes what a probe SEES changes: `srlimit`, the `size` filter
# in `scope_for`, `QUERIES`, `TIERS`, or `MIN_MENTIONS`. `build()` then re-probes every record
# stamped older, so the next truncation fix heals itself instead of needing another audit to
# notice. Version 1 was the pre-repair contract (srlimit=3, first 8 titles only); records written
# before stamping existed carry no stamp at all and read as 0, so they are all re-probed once.
PROBE_VERSION = 2


def scope_for(host, verbose=False):
    titles, seen = [], set()
    for q in QUERIES:
        # HARD RULE 0. This asked for the top 3 hits of each of four fixed queries and then,
        # below, kept only the first 8 titles that survived -- two stacked truncations feeding
        # the term-frequency count that `ceiling_for()` turns into the Magnitude ceiling for
        # every entity in the source. `srlimit` is raised to the API's own per-call maximum for
        # an ordinary (non-bot) key, same fix `feats.discover()` applied to this identical
        # `list=search` action; a `continue` key in the response means MediaWiki still withheld
        # results beyond that, which is worth knowing rather than pretending away, so it goes
        # into the ledger instead of the API's default of 10. Previously reported at
        # handoff/sweep24/AUDIT_batch06.md:320 and left unfixed since.
        d = F.api(host, {"action": "query", "list": "search", "srlimit": "500", "srsearch": q})
        if (d or {}).get("continue"):
            silence.note("scope.py:srlimit-bound")
        for row in (d or {}).get("query", {}).get("search", []):
            if row["title"] not in seen and row.get("size", 0) > 1200:
                seen.add(row["title"])
                titles.append(row["title"])
    if not titles:
        return None
    # No truncation here either -- `F.fetch` is written to take "up to any number of titles,
    # batched where batching is possible" (feats.py's own docstring); the `[:8]` this used to
    # pass it dropped everything past the eighth relevance-ranked title before a single mention
    # was counted.
    pages = F.fetch(host, titles)
    text = " ".join(F.strip_wikitext(v) for v in pages.values())
    counts = {lab: len(rx.findall(text)) for lab, rx, _ in _RE}

    # Highest tier clearing the floor, never the most frequent one.
    best = None
    for lab, _, band in _RE:
        if counts[lab] >= MIN_MENTIONS:
            best = (lab, band)
    # NOTHING CLEARS THE FLOOR MEANS NOTHING WAS ESTABLISHED, and that is a real answer.
    #
    # This branch used to fall back to `max(counts, key=counts.get)` -- the COMMONEST tier -- which
    # is the one method the module header exists to refuse ("Not by frequency ... never the most
    # frequent one"), applied at exactly the moment the evidence is too thin to support any method
    # at all. It was not a harmless default. Measured over the 155 hosts in data/SCOPE.json on
    # 2026-08-27: 28 of them (18%) hold a ceiling this branch invented, and among them
    # `root.fandom.com` and `rosariovampire.fandom.com` carry M7 -- UNIVERSE scale, the ceiling
    # that bounds nothing -- on TWO mentions of the word, and `cosmoteer` and `ghosts` carry a hard
    # M3 planet ceiling on two. MIN_MENTIONS is the whole statement that a stray line about
    # another universe does not make a fiction universal; taking the argmax below the floor
    # rewrites that stray line as the verdict, and does it silently.
    #
    # A source with no scope keeps `ceiling_for() -> None`, which is what the rest of Part Three
    # already handles for the 203-of-211 sources that are honestly unassayed. An unearned ceiling
    # is not a conservative choice: it is a number describing a fiction no source ever recorded,
    # which is the same fabrication the module was written to stop.
    if best is None:
        if verbose:
            print(f"   {host:<32}{counts}  -- nothing reaches {MIN_MENTIONS}: "
                  f"no scope established")
        return None
    if verbose:
        print(f"   {host:<32}{counts}")
    return {"scope": best[0], "ceiling": best[1], "counts": counts,
            "pages": sorted(pages), "probe_version": PROBE_VERSION}


def _stamp(rec):
    """The PROBE_VERSION a stored record was built under. 0 for anything unstamped.

    A record may legitimately be `None` on disk -- that is the cached "read, nothing cleared
    MIN_MENTIONS" answer the comment in `build()` argues for keeping. Those carry no stamp
    either, so they read as 0 and are re-probed on the next contract change like everything else.
    """
    return (rec or {}).get("probe_version", 0) if isinstance(rec, dict) else 0


def build(hosts, force=False):
    out = {}
    if os.path.exists(OUT):
        out = json.load(open(OUT, encoding="utf-8"))
    # SELECTION IS BY CONTRACT, NOT BY MEMBERSHIP. This was `h not in out`, so a host was skipped
    # for ever once it had a key, whatever produced that key -- and `main()` offered no --rebuild,
    # --force or --host to get past it. See PROBE_VERSION above for what that cost. `force`
    # ignores the stamp entirely, for the case where the operator knows the wikis themselves have
    # moved rather than the code.
    todo = sorted({h for s, h in hosts.items()
                   if h and not F.is_wikipedia(h)
                   and (force or _stamp(out.get(h)) < PROBE_VERSION)})
    for i, h in enumerate(todo, 1):
        try:
            sc = scope_for(h)
        except Exception:
            # A FAILURE IS NOT A VERDICT, AND IT MUST NOT BE CACHED AS ONE. `out[h] = None` used
            # to be written here as well, and `todo` above excludes every host that is already a
            # KEY in `out` regardless of its value -- so one network blip, one 500 from a wiki,
            # one unparseable response permanently retired that host from scoping. It would never
            # be probed again by any future run, and the file would report it as "attempted,
            # nothing to score", which is the one thing that had NOT happened. Left out of `out`
            # entirely, it simply reappears in the next build's `todo`.
            #
            # The genuine empty answer below (`sc is None` from a host that WAS read and had no
            # titles, or nothing clearing MIN_MENTIONS) is still cached, and should be: that is a
            # real result and re-probing it every build would cost four API calls a host to learn
            # the same thing.
            silence.note("scope.py:build-probe-failed")
            print(f"  {i:>3}/{len(todo)}  {h:<34}probe FAILED -- left unscored, "
                  f"the next build retries it", flush=True)
            continue
        # STAMPED EVEN WHEN THE ANSWER IS EMPTY. `sc is None` is the genuine "read, and nothing
        # cleared MIN_MENTIONS" verdict the comment above keeps on purpose -- but a bare `None`
        # has nowhere to carry PROBE_VERSION, so it would be re-probed on EVERY build instead of
        # only when the contract moves, at four API calls a host. Stored as a record whose
        # `ceiling` is None, which is what `ceiling_for()` and `magnitude.host_ceiling` already
        # read as "no ceiling here".
        out[h] = sc or {"scope": None, "ceiling": None, "probe_version": PROBE_VERSION}
        if sc:
            print(f"  {i:>3}/{len(todo)}  {h:<34}{sc['scope']:<12}ceiling {sc['ceiling']}",
                  flush=True)
    # ATOMIC: SCOPE.json is read by magnitude.py and pipeline.py. 2026-08-25.
    # GATED, alongside `out`: `write_json` returns whether the rename LANDED and this dropped
    # the verdict, so a denied replace still let `main()` print "N/M wikis scoped -> SCOPE.json"
    # -- the honest report of a file that, this round, did not change at all. `build()` returns
    # the verdict now so its one caller can tell the difference.
    ok = silence.write_json(OUT, out, indent=1, ensure_ascii=False)
    return out, ok


def ceiling_for(source, hosts=None, cache=None):
    """The Magnitude ceiling a source's own scope supports, or None."""
    if cache is None:
        cache = json.load(open(OUT, encoding="utf-8")) if os.path.exists(OUT) else {}
    if hosts is None:
        hosts = json.load(open(F.HOSTS, encoding="utf-8"))
    sc = cache.get(hosts.get(source) or "")
    return sc["ceiling"] if sc else None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--build", action="store_true")
    ap.add_argument("--rebuild", action="store_true",
                    help="re-probe every non-Wikipedia host, ignoring the stored PROBE_VERSION")
    ap.add_argument("--probe", metavar="HOST",
                    help="print one host's scope answer without writing it")
    ap.add_argument("--host", metavar="HOST",
                    help="re-probe ONE host and write the result into SCOPE.json")
    a = ap.parse_args()
    if a.probe:
        # NOT `[:900]`. This cut the JSON at 900 characters with no ellipsis and no count -- the
        # answer simply stopped, mid-string if the cut landed inside a page title. It did not
        # bite while every stored record was built under the removed `titles[:8]` cap (the
        # largest was 608 chars); post-repair a probe is four searches at srlimit=500 keeping
        # every hit over 1200 bytes, so `pages` -- the provenance of the whole verdict -- runs to
        # hundreds of titles. `--probe` exists to let someone inspect a scope answer before
        # trusting it, so it is the one surface that must never abbreviate one.
        print(json.dumps(scope_for(a.probe, verbose=True), indent=1))
        return 0
    if a.host:
        # ONE WIKI, BY HAND. `build()` skips whatever the stamp says is current, so re-probing a
        # single host after a wiki itself has changed had no route at all before this.
        cache = json.load(open(OUT, encoding="utf-8")) if os.path.exists(OUT) else {}
        sc = scope_for(a.host, verbose=True)
        cache[a.host] = sc or {"scope": None, "ceiling": None,
                               "probe_version": PROBE_VERSION}
        if not silence.write_json(OUT, cache, indent=1, ensure_ascii=False):
            print(f"WRITE DENIED: {a.host} was probed but did not land in {OUT}; rerun to retry")
            return 1
        print(f"{a.host}: {(sc or {}).get('ceiling') or 'no scope established'}  ->  {OUT}")
        return 0
    if a.build or a.rebuild:
        hosts = json.load(open(F.HOSTS, encoding="utf-8"))
        out, ok = build(hosts, force=a.rebuild)
        # A STAMPED EMPTY RECORD IS NOT A SCOPED WIKI. `if v` used to be the whole test, which
        # was right while an empty answer was stored as `None`; it now stores a record carrying
        # only the stamp, so the count asks for the ceiling itself.
        got = sum(1 for v in out.values() if v and v.get("ceiling"))
        if ok:
            print(f"\n{got}/{len(out)} wikis scoped  ->  {OUT}")
            return 0
        print(f"\nWRITE DENIED: {got}/{len(out)} wikis scoped this round did not land in "
              f"{OUT}; rerun to retry")
        # THE VERDICT REACHES THE EXIT CODE. `build()` was changed to return `(out, ok)` so its
        # one caller could tell the difference, `main()` told it in prose, and then returned 0 on
        # both branches -- so a denied write read as a clean run to anything checking rc, while
        # `magnitude.host_ceiling` went on clamping every anchor against the previous round's
        # ceilings. Same doctrine as catalogue_codex.py:315-331.
        return 1
    ap.print_help()
    return 0


if __name__ == "__main__":
    sys.exit(main())
