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
import pipeline as P                                                    # noqa: E402
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


def scope_for(host, verbose=False):
    titles, seen = [], set()
    for q in QUERIES:
        d = F.api(host, {"action": "query", "list": "search", "srlimit": "3", "srsearch": q})
        for row in (d or {}).get("query", {}).get("search", []):
            if row["title"] not in seen and row.get("size", 0) > 1200:
                seen.add(row["title"])
                titles.append(row["title"])
    if not titles:
        return None
    pages = F.fetch(host, titles[:8])
    text = " ".join(F.strip_wikitext(v) for v in pages.values())
    counts = {lab: len(rx.findall(text)) for lab, rx, _ in _RE}

    # Highest tier clearing the floor, never the most frequent one.
    best = None
    for lab, _, band in _RE:
        if counts[lab] >= MIN_MENTIONS:
            best = (lab, band)
    if best is None:                       # nothing clears it: fall back to the commonest tier
        lab = max(counts, key=counts.get)
        band = dict((l, b) for l, _, b in _RE)[lab]
        best = (lab, band) if counts[lab] else None
    if verbose:
        print(f"   {host:<32}{counts}")
    if not best:
        return None
    return {"scope": best[0], "ceiling": best[1], "counts": counts,
            "pages": sorted(pages)}


def build(records, hosts):
    out = {}
    if os.path.exists(OUT):
        out = json.load(open(OUT, encoding="utf-8"))
    todo = sorted({h for s, h in hosts.items() if h and h not in out
                   and not F.is_wikipedia(h)})
    for i, h in enumerate(todo, 1):
        try:
            sc = scope_for(h)
        except Exception:
            silence.note("scope.py:110")
            sc = None
        out[h] = sc
        if sc:
            print(f"  {i:>3}/{len(todo)}  {h:<34}{sc['scope']:<12}ceiling {sc['ceiling']}",
                  flush=True)
    with open(OUT, "w", encoding="utf-8") as f:
        json.dump(out, f, indent=1, ensure_ascii=False)
    return out


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
    ap.add_argument("--probe", metavar="HOST")
    a = ap.parse_args()
    if a.probe:
        print(json.dumps(scope_for(a.probe, verbose=True), indent=1)[:900])
        return 0
    if a.build:
        hosts = json.load(open(F.HOSTS, encoding="utf-8"))
        out = build(P.records(), hosts)
        got = sum(1 for v in out.values() if v)
        print(f"\n{got}/{len(out)} wikis scoped  ->  {OUT}")
        return 0
    ap.print_help()
    return 0


if __name__ == "__main__":
    sys.exit(main())
