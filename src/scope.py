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


class ProbeUnread(Exception):
    """The host was NOT read. Distinct from "read it, and nothing cleared MIN_MENTIONS".

    `F.api` does not raise. It returns None for a throttle, for any HTTP status, for a non-JSON
    200 (a WAF or a login wall), for a network fault and for "no usable API here" -- the same
    None that a genuine empty search returns. `scope_for` used to read all of those as
    `titles == []` and return None, and `build()` then STAMPED that None at PROBE_VERSION, which
    retires the host from every future build until somebody bumps the constant. The exception
    handler in `build()` already says what must happen instead -- "A FAILURE IS NOT A VERDICT,
    AND IT MUST NOT BE CACHED AS ONE" -- and it only ever saw exceptions, so the swallowed
    failures walked straight past it. Raising is how they reach it.

    The ONE clean negative `api()` documents is http-404: the wiki answered, and there is no
    such page. Everything else means the probe did not happen.
    """


# The one `why` from `feats.api`'s outcome channel that is a real answer rather than a failure
# to get one. See ProbeUnread.
_CLEAN_NEGATIVE = ("http-404",)


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
        oc = {}
        d = F.api(host, {"action": "query", "list": "search", "srlimit": "500", "srsearch": q},
                  outcome=oc)
        # THE HOST WAS NOT READ, SO THERE IS NO VERDICT TO CACHE. Without this, a throttled,
        # unreachable or challenge-serving host produced an empty `titles` that is spelled
        # exactly like the honest "nothing cleared MIN_MENTIONS", and `build()` stamped it
        # permanently. See ProbeUnread.
        if not oc.get("ok") and oc.get("why") not in _CLEAN_NEGATIVE:
            raise ProbeUnread("%s: query %r not answered (%s)" % (host, q, oc.get("why")))
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
    # F.fetch HAS THE SAME PROPERTY ONE LAYER DOWN: it returns {} rather than raising when its
    # own api() calls fail, so a search that succeeded followed by a fetch that did not lands as
    # another honest-looking empty. It has no `outcome` channel to consult (feats.py is not this
    # module's to change), so the one thing that CAN be said from here is said: the titles came
    # out of a search this host just answered, so fetching every one of them and getting nothing
    # back is a transport failure, not a corpus fact. A PARTIALLY failed fetch -- some batches
    # answered, some not -- is still invisible from here and remains an open gap; it degrades a
    # measurement rather than inventing one, and it is bounded by the same retry the next build
    # gives an unstamped host.
    if titles and not pages:
        raise ProbeUnread("%s: %d titles searched, none fetched" % (host, len(titles)))
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
    """Probe every host whose stored record is older than the contract, and land the result.

    THE 28 INVENTED CEILINGS WERE WITHDRAWN ON 2026-09-08, WITHOUT A SINGLE REQUEST
    (order 481ef92af785, owner ruling 10: "re-derive all of it, with a snapshot and a
    before/after table").

    The repaired `scope_for()` answers None when no tier reaches MIN_MENTIONS, and the counts
    every stored row holds are already on disk -- so for a row whose counts do not clear the
    floor, the value the fixed writer WOULD compute is knowable offline, exactly. It is None.
    Twenty-eight rows held a ceiling the removed argmax-below-the-floor branch invented, worst
    of them `tales.fandom.com` at M7 on ONE mention; every one of them was clamping published
    Magnitudes through `magnitude.host_ceiling`. They now read `ceiling: None` and carry a
    `rederived` sentence saying so.

    THEY WERE NOT STAMPED, deliberately. No probe happened, so writing `probe_version` would
    retire them from this function's `todo` and make a paper correction look like a measurement.
    They are still first in line for the next real build.

    THE RE-PROBE IS STILL OWED and is a live crawl on the Fandom edge -- 155 hosts, four
    searches each at srlimit=500, then a fetch over every returned title -- which is why it was
    not started by the run that did the withdrawal. Snapshot, before/after table and the cost
    are in `handoff/REDERIVE_20260908_scope_wh40k.md`.
    """
    out = {}
    if os.path.exists(OUT):
        out = json.load(open(OUT, encoding="utf-8"))
    # WHAT THIS RUN PROBED, kept apart from the merged view. `out` is read to decide the work and
    # returned for the caller's count; `probed` is the only thing written, which is what makes the
    # compare-and-swap at the bottom key-wise rather than a whole-document overwrite.
    probed = {}
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
        except ProbeUnread as e:
            # THE SWALLOWED FAILURES NOW ARRIVE HERE TOO, which is the whole point of the class:
            # this branch and its comment below were written for exactly this condition and only
            # ever saw the small minority of it that happened to raise.
            silence.note("scope.py:build-probe-unread")
            print(f"  {i:>3}/{len(todo)}  {h:<34}NOT READ -- {e}; left unscored, "
                  f"the next build retries it", flush=True)
            continue
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
        out[h] = probed[h] = sc or {"scope": None, "ceiling": None,
                                    "probe_version": PROBE_VERSION}
        if sc:
            print(f"  {i:>3}/{len(todo)}  {h:<34}{sc['scope']:<12}ceiling {sc['ceiling']}",
                  flush=True)
    # ATOMIC: SCOPE.json is read by magnitude.py and pipeline.py. 2026-08-25.
    # GATED, alongside `out`: `write_json` returns whether the rename LANDED and this dropped
    # the verdict, so a denied replace still let `main()` print "N/M wikis scoped -> SCOPE.json"
    # -- the honest report of a file that, this round, did not change at all. `build()` returns
    # the verdict now so its one caller can tell the difference.
    #
    # AND NOW COMPARE-AND-SWAP RATHER THAN A WHOLE-DOCUMENT LAND (order 3610ec65ebd3). Atomic
    # closed the torn-file half and had nothing to say about STALENESS: this function reads the
    # cache, then crawls up to 155 wikis, then landed its own copy of the whole table -- so a
    # `--host` re-probe or a second invocation that landed inside that window was silently
    # discarded. `probed` carries ONLY the hosts this run actually probed, so the re-apply is
    # key-wise and nobody else's row is carried backwards by us. `out` still holds the merged
    # view for the caller's count, which is what it always held.
    landed, why = mutate(lambda cache: cache.update(probed))
    if not landed and why:
        print("SCOPE.json was NOT updated: %s" % why)
    return out, landed


def mutate(apply, attempts=8, path=None):
    """Land a change to SCOPE.json through a COMPARE-AND-SWAP. -> (landed, why).

    ATOMIC WAS ALREADY DONE HERE, AND THAT IS WHAT MADE THE REST EASY TO MISS (order 3610ec65ebd3).
    The comment at this file's write site is entirely about atomicity: that SCOPE.json is read by
    `magnitude` and `pipeline`, that the rename must not tear, and that `write_json`'s
    landed/denied verdict was being dropped so `main()` printed success over a write that never
    happened. Both were fixed. So a reader arriving there met careful, recent, correct reasoning
    about concurrent access and had no reason to suspect the OTHER concurrency fault was still
    open -- three paths loading the whole document, mutating it, and landing it whole with no
    comparison against what was on disk in between.

    THE WINDOW IS LONG HERE EVEN THOUGH THE FILE IS SMALL. `build()` reads the cache, then probes
    up to 155 wikis with four searches each at srlimit=500 and a fetch over every returned title,
    and lands its copy at the end. Anything another invocation wrote during that crawl -- a
    `--host` re-probe by hand, a foreman remedy, a second agent -- is overwritten by this run's
    older copy of it. Nothing fails and nothing tears; the file is simply rows behind, and the
    rows it is behind by cost a live crawl on an edge that has IP-banned this machine once.

    THE PATTERN IS `roll.mutate`'s, DELIBERATELY, and the reason it transfers is that SCOPE.json is
    KEYED BY HOST: re-applying our probed hosts to the winner's freshly-read copy leaves their
    hosts standing and puts ours beside them. `apply(cache) -> cache` is therefore called on a
    fresh read on EVERY attempt, and a refusal re-reads and re-applies rather than retrying the
    same bytes. `apply` may mutate in place and return None.

    AN UNREADABLE SCOPE.json IS NOT WRITTEN OVER. Absent is normal -- the first build has no cache
    -- but unreadable is a different fact, and it is not evidence of what the file should contain.
    Overwriting it on a failed read would discard 155 hosts' probe results and quietly re-open the
    crawl that produced them. Same distinction `roll.mutate` and `endpoint.register` draw.

    `path` defaults to this module's OUT and the tests repoint that constant, for the reason
    `roll.mutate` spells out at length: a helper that wrote to its own module global instead of
    the caller's would turn "sandbox this test" into "overwrite the live file".
    """
    import threading
    import time
    path = OUT if path is None else path
    last_why = "not attempted"
    for attempt in range(attempts):
        # The digest is taken BEFORE the read, so anything landing between the two fails the swap
        # closed rather than passing on a copy that is already behind.
        digest = silence.digest_of(path)
        cache = {}
        if os.path.exists(path):
            try:
                with open(path, encoding="utf-8") as f:
                    cache = json.load(f)
            except Exception:
                silence.note("scope.py:mutate-unreadable")
                return False, ("%s exists and could not be read, so nothing was written to it -- "
                               "a failed read is not evidence of what the file should hold, and "
                               "these rows cost a live crawl" % os.path.basename(path))
            if not isinstance(cache, dict):
                silence.note("scope.py:mutate-nondict")
                return False, ("%s is not an object; refusing to overwrite it"
                               % os.path.basename(path))
        out = apply(cache)
        if out is None:
            out = cache
        # pid + thread + attempt in the temp name, for the reason silence.write_json carries them:
        # a fixed `.tmp` is a second collision between the very writers this function separates.
        tmp = "%s.%d.%d.%d.tmp" % (path, os.getpid(), threading.get_ident(), attempt)
        try:
            with open(tmp, "w", encoding="utf-8") as f:
                json.dump(out, f, indent=1, ensure_ascii=False)
        except Exception:
            silence.note("scope.py:mutate-tmp")
            return False, "could not stage the new scope table next to %s" % os.path.basename(path)
        landed, why = silence.replace_if_unchanged(tmp, path, digest)
        if landed:
            return True, ""
        last_why = why
        try:
            os.remove(tmp)
        except OSError:
            silence.note("scope.py:mutate-tmp-cleanup")
        time.sleep(0.05 * (attempt + 1))
    silence.note("scope.py:mutate-contended")
    return False, last_why


# REPORTED DEAD, NOT DELETED, per house doctrine that dead code is not automatically deletable
# (order de43fe54feb7, owner ruling 1 of 2026-09-08: mark and keep, one line each, delete
# nothing). `ceiling_for` has ZERO callers repo-wide -- `grep -rn ceiling_for src/ docs/ *.md`
# returns only this def line and prior audit reports, and it has been reported so in sweeps 23,
# 26, 30, 32 and 34. The LIVE path to the same data is `magnitude.host_ceiling`
# (magnitude.py:942), which reads SCOPE.json directly and reimplements the live-probe fallback.
# Kept because this is the spelling that reads the file through its owning module rather than
# reaching across into it, and because deleting a public function is a curatorial act.
def ceiling_for(source, hosts=None, cache=None):
    """The Magnitude ceiling a source's own scope supports, or None. NO CALLERS -- see above."""
    if cache is None:
        cache = json.load(open(OUT, encoding="utf-8")) if os.path.exists(OUT) else {}
    if hosts is None:
        hosts = json.load(open(F.HOSTS, encoding="utf-8"))
    sc = cache.get(hosts.get(source) or "")
    return sc["ceiling"] if sc else None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--build", action="store_true")
    ap. add_argument("--rebuild", action="store_true",
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
        try:
            print(json.dumps(scope_for(a.probe, verbose=True), indent=1))
        except ProbeUnread as e:
            # NOT `null`. --probe printing `null` for an unread host is the same conflation this
            # module's build path was just repaired for, on the surface a person uses to decide
            # whether to trust a scope answer.
            print(f"NOT READ: {e}")
            return 1
        return 0
    if a.host:
        # ONE WIKI, BY HAND. `build()` skips whatever the stamp says is current, so re-probing a
        # single host after a wiki itself has changed had no route at all before this.
        #
        # THE PRE-READ IS GONE, and its removal is the fix rather than a tidy-up. It loaded the
        # whole table HERE, before a live wiki probe that takes as long as it takes, and the
        # write below then landed that snapshot -- so this path's own copy of the table was
        # always the stalest thing in the process. `mutate` re-reads at the moment of writing.
        try:
            sc = scope_for(a.host, verbose=True)
        except ProbeUnread as e:
            # NOTHING IS WRITTEN. Stamping an unread host here retires it from `build()` exactly
            # as the cached-failure path did.
            print(f"NOT READ: {e}; {OUT} is unchanged and the next build retries this host")
            return 1
        rec = sc or {"scope": None, "ceiling": None, "probe_version": PROBE_VERSION}
        # ONE HOST, LANDED KEY-WISE (order 3610ec65ebd3). This read the whole table at the top of
        # the branch, probed a live wiki, and then landed its own copy of the whole thing -- so a
        # `--build` crawl running beside it lost every row it had finished in the meantime. Now
        # only this host's row is applied, to a freshly-read copy, under a compare-and-swap.
        landed, why = mutate(lambda c: c.__setitem__(a.host, rec))
        if not landed:
            print(f"WRITE DENIED: {a.host} was probed but did not land in {OUT} ({why}); "
                  f"rerun to retry")
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
