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
import time
import sys
import collections
from concurrent.futures import ThreadPoolExecutor

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import wiki_source as ws                                                # noqa: E402
import silence                                                          # noqa: E402

_BAD_CHARS = (chr(8), chr(11), chr(12), chr(7))
if any(c in open(os.path.abspath(__file__), encoding="utf-8").read() for c in _BAD_CHARS):
    raise SystemExit(__file__ + ": a regex escape was eaten in transit.")

OUT = os.path.join(HERE, "data", "COMPLETENESS.json")
HOSTS = os.path.join(HERE, "data", "WIKI_HOSTS.json")
RECORDS = os.path.join(HERE, "data", "records")

PERSONS = "Persons (named individual characters, real or fictional)"


def subdomain(host):
    """'dc.fandom.com' -> 'dc'. Non-fandom hosts have no category API we can use this way."""
    if not isinstance(host, str) or not host.endswith(".fandom.com"):
        return None
    return host[: -len(".fandom.com")]


_CS_CACHE_P = os.path.join(HERE, "state", "category_sizes.json")
_CS_CACHE = {"loaded": False, "d": {}}
_CS_TTL = 12 * 3600


def _cs_load():
    if not _CS_CACHE["loaded"]:
        try:
            with open(_CS_CACHE_P, encoding="utf-8") as f:
                _CS_CACHE["d"] = json.load(f)
        except Exception:
            _ = "silence-exempt: no cache yet is the normal first state"
        _CS_CACHE["loaded"] = True
    return _CS_CACHE["d"]


def category_size_probe(sub, category):
    """`category_size` with its failure visible: returns `(n, error)`.

    Added 2026-08-23 (BUGS m3). `category_size` answers `None` for two opposite situations --
    "this wiki has no such category" and "this wiki did not answer" -- and the audit below,
    which only ever saw the `None`, dropped an all-errors source out of COMPLETENESS.json
    entirely. A missing row reads as a source with nothing to catalogue, which is the exact
    inversion of what a transport failure means. 313 URLErrors were recorded at this site as of
    run #2, all of them silently deciding a row did not exist.

    `category_size` stays as it was for every caller that only wants the number."""
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
    cache = _cs_load()
    cache[k] = {"at": time.time(), "n": got}
    try:
        tmp = _CS_CACHE_P + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(cache, f)
        silence.replace_retry(tmp, _CS_CACHE_P)
    except Exception:
        silence.note("completeness.py:cs-cache")
    return got, None


def category_size(sub, category):
    """How many pages a category holds, per the wiki itself. One call, no enumeration --
    and CACHED 12h to disk: the always-remedy runs this audit every foreman round, and
    uncached that was ~1,300 live calls per half hour to the domain that has IP-banned this
    machine once already (round-2 optimization audit, finding 3). Category counts move on a
    days clock; the standard's job is to keep the shortfall visible, not to re-ask fandom
    the same question 48 times a day."""
    return category_size_probe(sub, category)[0]


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


def audit(only=None, workers=6):
    with open(HOSTS, encoding="utf-8") as f:
        hosts = json.load(f)
    have = catalogued_counts()
    # index catalogued counts by a loose key so 'Marvel' matches 'marvel.json'
    byslug = {}
    for src, v in have.items():
        byslug[str(src).lower()] = v
        byslug[v["file"][:-5].replace("-", " ")] = v

    todo = [(src, h) for src, h in hosts.items() if subdomain(h)]
    if only:
        todo = [t for t in todo if only.lower() in t[0].lower()]

    # A host serving more than one source cannot supply a denominator for either of them.
    # 'major fantasy pantheons' maps to marvel.fandom.com and legitimately so -- its provenance
    # says it draws "the deity/pantheon categories of multiple franchise wikis" -- but its
    # target is Marvel's GODS, not Marvel's 103,554 characters. Reporting 0.3% coverage there
    # would be an accusation against a source that did its job.
    shared = collections.Counter(h for _, h in todo)

    # Sharing a host does not disqualify BOTH sources -- it disqualifies the borrower. When two
    # sources point at marvel.fandom.com, one of them is Marvel and the other is drawing a
    # subset of it, and Marvel's denominator is perfectly good. The primary source for a host is
    # the one whose name survives inside the subdomain ('Marvel' -> 'marvel'); where no name
    # matches, no source claims it and all of them are marked.
    primary = {}
    for src, h in todo:
        sub = subdomain(h) or ""
        key = "".join(ch for ch in str(src).lower() if ch.isalnum())
        if key and key in sub.replace("-", ""):
            # Longest match wins, so 'Marvel' beats a hypothetical 'Mar'.
            if h not in primary or len(key) > len(primary[h][1]):
                primary[h] = (src, key)

    rows = []

    def work(item):
        src, host = item
        sub = subdomain(host)
        sizes = {}
        probes = ws.CATEGORY_PROBES[PERSONS]
        failed = 0
        for cand in probes:
            n, err = category_size_probe(sub, cand)
            if err:
                failed += 1
            if n:
                sizes[cand] = n
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
        if not sizes:
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


def land(rows, only=None):
    """Write COMPLETENESS.json atomically, and REFUSE to replace a real measurement with an
    empty one. Returns True if the file now holds `rows`.

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
        return True
    if not rows:
        prior = []
        try:
            with open(OUT, encoding="utf-8") as f:
                prior = json.load(f)
        except Exception:
            _ = "silence-exempt: no prior file is a legitimate first state"
        if prior:
            sys.stderr.write("completeness: measured 0 rows; REFUSING to overwrite %d existing "
                             "rows. An unmeasurable run is not a measurement of nothing -- see "
                             "the transport failures in `health.py --failures`.\n" % len(prior))
            return False
    tmp = OUT + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(rows, f, indent=1, ensure_ascii=False)
    silence.replace_retry(tmp, OUT)
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
