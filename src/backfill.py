#!/usr/bin/env python3
"""
BACKFILL — recover the main casts the original cataloguing crawl missed.

The character sweep found that some sources have no protagonists at all. Dragon Ball Z holds 300
entries and 50 Persons, and among them Goku, Vegeta, Frieza, Gohan, Piccolo, Cell and Trunks are
all absent, while Goku Black, Turles, Towa, Mira, Demigra, Fu and Chronoa are present -- the
Xenoverse and Fusions roster. God of War has three Persons in 220 entries and Kratos is not one
of them. World of Warcraft, Fate and Fire Emblem have zero occurrences of Arthas, Gilgamesh or
Byleth anywhere in the source.

It is not universal, which is the useful part: Marvel (401 Persons), Star Wars (226), One Piece
(297) and Naruto (187) all carry their casts properly. So this is per-source crawl failure and
the repair is per-source, not a re-do of the corpus.

Every wiki publishes the roster the crawl should have walked, as `Category:Characters`. Some
nest it a level down -- God of War's top category holds a single page and the rest sit in
subcategories -- so one level of subcategory is walked too.

WHAT THIS WILL AND WILL NOT WRITE
---------------------------------
An added entry carries a name and the opening sentences of the wiki's own article, and nothing
else. No band, no scale note, no assay, no invented facts: Hard Rule 1 says every generated
entry is prose dressing on top of a record, so a record fabricated here would poison everything
downstream of it. `catalogued` is left False so phase 2 judges these the same way it judged the
rest, and provenance is stamped so a backfilled entry is never mistaken for one the research
pass produced.
"""
import argparse
import json
import os
import re
import sys
import time

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import pipeline as P                                                    # noqa: E402
import feats as F                                                       # noqa: E402

_BAD_CHARS = (chr(8), chr(11), chr(12), chr(7))
if any(c in open(os.path.abspath(__file__), encoding="utf-8").read() for c in _BAD_CHARS):
    raise SystemExit(__file__ + ": a regex escape was eaten in transit.")

PERSON_CATEGORY = "Persons (named individual characters, real or fictional)"


class RosterIncomplete(RuntimeError):
    """A category walk stopped on a transport failure instead of on the end of the listing.

    Named, and raised rather than returned, because the two outcomes are indistinguishable in
    the data: `F.api()` answers `None` both for "this page does not exist" and for a timeout
    (open bug M16), and `members()` used to `return rows` on either -- handing back a roster that
    stops at whatever page the network died on, with no mark on it. `backfill_source` then wrote
    that partial cast as the source's complete cast, which is the exact defect THIS FILE EXISTS
    TO REPAIR, performed by the repair. The caller at the bottom of this module already catches
    per source and prints the exception's class name, so raising costs one source's pass and
    prints why; returning silently costs the source's missing characters, permanently.
    """

# Pages that sit in a character category without being a character.
_NOT_A_CHARACTER = re.compile(
    r"^(list of|index|category:|template:|file:|gallery|glossary|timeline|"
    r"unnamed|minor |.*\(disambiguation\)|.*/(gallery|quotes|relationships|abilities|"
    r"power and abilities|history|synopsis))", re.I)


def roster(host, limit=None):
    """Every character page on a wiki, from Category:Characters and one level of subcategory.

    The limit is deliberately far above any real roster. Category listings come back in
    alphabetical order, so a low cap truncates the alphabet rather than sampling it: at 600,
    Dragon Ball returned A through G and Goku fell outside the window, which reproduced the exact
    defect this file repairs. Enumerate everything, then rank.
    """
    seen, out = set(), []

    def members(cat, kind="page"):
        rows, cont = [], None
        while True:
            q = {"action": "query", "list": "categorymembers", "cmtitle": cat,
                 "cmlimit": "500", "cmtype": kind}
            if cont:
                q["cmcontinue"] = cont
            d = F.api(host, q)
            if not d:
                raise RosterIncomplete(
                    "%s: category walk for %r stopped after %d title(s) -- the API returned "
                    "nothing, which is the same answer it gives for a timeout as for an absent "
                    "page, so this roster cannot be called complete" % (host, cat, len(rows)))
            rows += [x["title"] for x in d.get("query", {}).get("categorymembers", [])]
            cont = (d.get("continue") or {}).get("cmcontinue")
            if not cont or (limit and len(rows) >= limit):
                return rows

    for t in members("Category:Characters"):
        if t not in seen and not _NOT_A_CHARACTER.match(t):
            seen.add(t)
            out.append(t)
    # One level down, for wikis that keep the roster in subcategories rather than the top.
    #
    # ALWAYS, NOT ONLY WHEN THE TOP LEVEL LOOKED THIN. Until run #26 this walk was gated on
    # `if len(out) < 40`, which is a Hard Rule 0 cap wearing a threshold's clothing: a wiki with
    # 40 characters filed at the top and 6,000 filed under "Villains", "Heroes", "Kryptonians"
    # returned the 40 and reported a complete roster. Nothing failed, and the shortfall looked
    # exactly like a small wiki. That is the same defect the `< 12` subcategory cap had -- fixed
    # once at the inner loop and left standing one line up, at the decision to loop at all.
    #
    # `seen` already de-duplicates, so walking the subcategories of a wiki that also lists its
    # cast at the top costs API calls and changes no result. Per Hard Rule 0 the answer to slow
    # is more time, never a smaller universe.
    for sub in members("Category:Characters", "subcat"):
        for t in members(sub):
            if t not in seen and not _NOT_A_CHARACTER.match(t):
                seen.add(t)
                out.append(t)
        if limit and len(out) >= limit:
            break
    # NO CAP. DC's Category:Characters runs past 6,000 and a cap took an alphabetical sliver --
    # Abin Sur, Ace, Adolf Hitler -- while Superman, Wally West and Wonder Woman sat outside the
    # window entirely. A cap on an alphabetically-ordered listing is not a sample, it is a
    # truncation, and it silently decides that everything after the letter B does not exist.
    return out[:limit] if limit else out


def lead(wikitext, chars=420):
    """The article's opening PROSE, which is the only description this file will write.

    Taking the first 420 characters of the stripped page is not the same as taking its lead. A
    large wiki opens an article with infobox and navigation templates, and those strip to
    whitespace and punctuation -- DC's Barry Allen page is 95,881 characters and yielded 72,
    so 494 of 500 queued characters were silently dropped as "stubs" while their articles ran to
    six figures.

    So: walk forward to the first block that actually reads like prose -- a real sentence, with
    a verb's worth of length behind it -- and take the lead from there.
    """
    t = F.strip_wikitext(wikitext)
    for block in re.split(r"\n{2,}", t):
        block = re.sub(r"\s+", " ", block).strip()
        # A lead sentence has length and terminal punctuation. Template residue has neither.
        if len(block) < 80 or "." not in block:
            continue
        if not re.search(r"[a-z]{3}\s+[a-z]{3}", block):   # needs actual words, not a title row
            continue
        cut = block[:chars]
        dot = cut.rfind(". ")
        return (cut[:dot + 1] if dot > 120 else cut).strip()
    # Fall back to the old behaviour rather than returning nothing.
    t = re.sub(r"\s+", " ", t).strip()
    cut = t[:chars]
    dot = cut.rfind(". ")
    return (cut[:dot + 1] if dot > 120 else cut).strip()


def audit(records, hosts):
    """Sources whose catalogued cast looks too thin for the wiki behind them."""
    rows = []
    for _, r in records:
        host = hosts.get(r["source"])
        if not host or F.is_wikipedia(host):
            continue
        ps = [e for e in r["entries"] if (e.get("category") or "").startswith("Persons")]
        rows.append({"source": r["source"], "host": host,
                     "persons": len(ps), "entries": len(r["entries"]),
                     "share": len(ps) / max(len(r["entries"]), 1)})
    return sorted(rows, key=lambda x: x["share"])


def backfill_source(source, records, hosts, cap=None, dry=False):
    rec = next((p, r) for p, r in records if r["source"] == source)
    path, r = rec
    host = hosts.get(source)
    if not host:
        return {"source": source, "error": "no wiki host"}
    have = {re.sub(r"[^a-z0-9]+", "", e["name"].lower()) for e in r["entries"]}
    names = roster(host)
    missing = [t for t in names if re.sub(r"[^a-z0-9]+", "", t.lower()) not in have]
    # Ranked by article size, never alphabetically. A category listing comes back A-first, so a # cap applied to it takes Abo, Abura and Ackman and leaves Goku out — which is precisely the # failure this file exists to repair. Article length is the wiki's own vote on who matters: # Goku's page runs six figures, Agarizame's runs three.
    sizes = {}
    for i in range(0, len(missing), 50):
        d = F.api(host, {"action": "query", "prop": "info", "titles": "|".join(missing[i:i + 50])})
        for pg in (d or {}).get("query", {}).get("pages", []):
            sizes[pg.get("title")] = pg.get("length", 0)
    # Reported BEFORE the cap. Computing it after made "already held" the complement of the cap # rather than of the match, and printed 1,459 held for a source that holds 300 entries total.
    absent = len(missing)
    # Ranked by article size so the deepest arrive first if this is ever interrupted, but NOT # truncated: every character the wiki lists is a character the library should hold.
    missing = sorted(missing, key=lambda t: -sizes.get(t, 0))
    if cap:
        missing = missing[:cap]
    if dry or not missing:
        return {"source": source, "host": host, "roster": len(names), "already_held": len(names) - absent, "absent": absent, "queued": len(missing), "sample": missing[:12], "added": 0}
    added = 0
    for i in range(0, len(missing), 40):
        pages = F.fetch(host, missing[i:i + 40])
        for title, wt in pages.items():
            desc = lead(wt)
            if len(desc) < 40:
                continue # a stub is not a record
            r["entries"].append({
                "name": title,
                "type": "Character",
                "description": desc,
                "category": PERSON_CATEGORY,
                "attestation": "Transcribed",
                "scale_note": "",
                "magnitude": "unassayed",
                "wiki_page": f"https://{host}/wiki/" + title.replace(" ", "_"),
                # Stamped, so a backfilled record is never mistaken for one the research pass # produced. The provenance travels with the entry into every later phase.
                "provenance": f"backfill:{host}",
                "catalogued": False,
                })
            added += 1
            time.sleep(0.2)
    # THE CAST-GROWING SIDE OF THE TWO-WRITER CONTRACT, not the pipeline side. This called
    # `write_record`, which is documented to keep the DISK entry list on drift because the
    # pipeline's in-memory copy is the stale one. Backfill is the opposite case and always has
    # been: it has just APPENDED the missing characters to `r["entries"]`, so its copy is the
    # fresh authority and the append itself guarantees a differing entry count -- i.e. drift is
    # detected on every run that actually did something, the merge takes disk as the base, and
    # every character just backfilled is dropped. The module's whole purpose was defeated on
    # exactly the runs where it had work to do; a run that found nothing missing wrote
    # correctly, so it never looked broken. Found and reproduced by the run #25 sweep.
    #
    # Gated, like every other caller: `write_record_catalogue` returns whether the rename
    # LANDED, and reporting "added N" for a write that never reached disk is the same lie in a
    # smaller font.
    if not P.write_record_catalogue(path, r):
        return {"source": source, "host": host, "roster": len(names),
                "already_held": len(names) - absent, "absent": absent,
                "queued": len(missing), "missing": len(missing),
                "added": 0, "write_denied": True,
                "entries_now": len(r["entries"]) - added}
    # `absent` is the PRE-cap truth and the dry path has always returned it; the real path
    # returned only a post-cap `missing`, so main()'s `res.get("absent", 0)` found no key and
    # printed **absent 0 for every source on every non-dry run** -- a completeness report that
    # read "nothing was missing" precisely when characters were being added to fix what was.
    # Both numbers are now reported, named for what they are, on both paths. 2026-08-24.
    return {"source": source, "host": host, "roster": len(names),
            "already_held": len(names) - absent, "absent": absent,
            "queued": len(missing), "missing": len(missing),
            "added": added, "entries_now": len(r["entries"])}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--audit", action="store_true")
    ap.add_argument("--source", action="append", help="repeatable")
    ap.add_argument("--dry", action="store_true")
    ap.add_argument("--cap", type=int, default=None,
                    help="omit for everything, which is the intended use")
    ap.add_argument("--all", action="store_true",
                    help="repair every source whose catalogued cast is too thin")
    ap.add_argument("--threshold", type=float, default=0.10,
                    help="Persons share below which a source counts as missing its cast")
    a = ap.parse_args()

    recs = P.records()
    hosts = json.load(open(F.HOSTS, encoding="utf-8"))

    if a.audit:
        rows = audit(recs, hosts)
        print(f"{'share':>7}{'persons':>9}{'entries':>9}   source")
        for x in rows[:26]:
            print(f"{x['share']:>7.1%}{x['persons']:>9,}{x['entries']:>9,}   {x['source'][:52]}")
        return 0

    if a.all:
        # No editorial list of "character-driven" sources. The wiki decides: a source whose wiki
        # publishes no Category:Characters gets nothing added, which is the correct answer for a
        # board game or a rules supplement and needs no judgement from here.
        thin = [x for x in audit(recs, hosts) if x["share"] < a.threshold]
        print(str(len(thin)) + " sources below a "
              + format(a.threshold, ".0%") + " Persons share", flush=True)
        tot = 0
        for i, x in enumerate(thin, 1):
            try:
                res = backfill_source(x["source"], recs, hosts, cap=a.cap, dry=a.dry)
            except Exception as e:
                print("  %3d/%d  %-46sERROR %s" % (i, len(thin), x["source"][:44],
                                                   type(e).__name__), flush=True)
                continue
            tot += res.get("added", 0)
            print("  %3d/%d  %-46sroster %5d  absent %5d  added %4d"
                  % (i, len(thin), x["source"][:44], res.get("roster", 0),
                     res.get("absent", 0), res.get("added", 0)), flush=True)
        print("total characters added: %d" % tot)
        return 0

    if not a.source:
        ap.print_help()
        return 0
    for s in a.source:
        print(json.dumps(backfill_source(s, recs, hosts, cap=a.cap, dry=a.dry),
                         ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
