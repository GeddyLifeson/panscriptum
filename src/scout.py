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
# WHERE THE ROLLED-OFF CYCLES GO INSTEAD OF NOWHERE (order e8cd908ce5e4). `sweep()` writes
# `LOG` as `prev[-LOG_CYCLES:]`, so every cycle past the window used to be DELETED from disk
# with nothing said anywhere -- a cap on a persisted history, which is the one place a cap does
# not even leave a person the option of re-running to see the rest. `foreman.py`'s failures
# ledger already has the house answer to this ("ARCHIVE AFTER READING, because the ledger never
# forgets" / "ARCHIVE FIRST, AND ONLY CLEAR IF THE ARCHIVE LANDED"), and this is that answer
# applied here: the recent window stays a readable JSON array, and nothing is ever dropped.
# Append-only JSONL, one cycle per line, via `silence.append_line`'s single O_APPEND syscall so
# two sweeps cannot interleave mid-record.
#
# DERIVED FROM `LOG`, NOT DECLARED BESIDE IT, and that is deliberate. `drill.py`'s two scout
# nets redirect `SC.LOG` into a temp directory precisely so a drill cannot touch the real
# ledger; a second module constant would sit there un-redirected and start writing the overflow
# into the live `data/` directory the first time a fixture ran past `LOG_CYCLES` cycles. One
# knob, one place the pair of them lands.
def _archive_for(log_path):
    """-> the append-only overflow file that belongs to this log."""
    return os.path.splitext(log_path)[0] + "_ARCHIVE.jsonl"


# The window `LOG` keeps in readable form. A number, not a magic literal buried in a slice, so
# that changing it is a decision rather than an edit -- and it is only a WINDOW now, not a
# horizon, because the archive holds everything that falls out of it.
LOG_CYCLES = 40
BLOCKED = os.path.join(HERE, "data", "SCOUT_BLOCKED.json")
# WHEN EACH SOURCE WAS LAST ATTEMPTED, which is what makes `sweep`'s window a ROTATION rather
# than a cap. Kept beside the other scout artifacts, and absent-means-never-attempted, so a
# source added tomorrow sorts to the front on its own without anything having to seed it.
ATTEMPTS = os.path.join(HERE, "data", "SCOUT_ATTEMPTS.json")


def _land(path, obj, sort_keys=True):
    """Write a shared artifact whole or not at all -- through `silence.write_json`.

    Order d3313adbf641 (see `_mutate`'s docstring below) moved this module's WIKI_HOSTS.json,
    SCOUT_ATTEMPTS.json and SCOUT_BLOCKED.json writes off `_land` and onto `_mutate`'s
    read-modify-write CAS; `_land`'s sole remaining caller is `sweep`'s own SCOUT.json log,
    which nothing but this process appends to. It went through `silence.write_json` anyway
    (run #33's fix to the identical `runguard._land`) rather than the hand-rolled fixed
    `path + ".tmp"` this used to build: that name is shared by every process that ever lands
    through a bare `_land`-shaped writer, and `hostcheck.py`'s own `_land` still builds the
    same fixed name for the files it writes -- there is no reason for this one to keep the
    hazard `silence.write_json` exists to end just because nothing currently collides with it.

    This is the WHOLE-FILE half of a write -- atomic against a torn read, but blind to another
    writer's read-modify-write racing this one. Use `_mutate` below for anything that reads a
    shared file, changes a piece of it, and writes it back."""
    return silence.write_json(path, obj, indent=1, sort_keys=sort_keys)


def _mutate(path, change, attempts=8):
    """Read-modify-write a shared JSON object under compare-and-swap. -> (landed, value).

    Order d3313adbf641: SCOUT_ATTEMPTS.json, WIKI_HOSTS.json and SCOUT_BLOCKED.json were each
    read, mutated and written back here with no lock and no staleness check -- three whole-file
    read-modify-writes on artifacts at least one OTHER process also writes. `hostcheck.adopt()`
    writes WIKI_HOSTS.json from a separate process; a lost update there silently un-adopts a
    host. A lost update to SCOUT_ATTEMPTS.json puts a source back at the front of `sweep`'s
    rotation, which is the exact failure `sweep`'s own docstring measured and fixed for the
    ranking side of this same file. `workorders._mutate` and `runguard._land_claim` were both
    given this same treatment the same day, over the same primitive: a digest taken at read
    time, and a write that lands only if the file still holds what was read.

    `change(d)` must be a pure function of the dict it is handed and return whatever the caller
    wants back (or None) -- on a refused write this re-reads the fresh copy and calls `change`
    again, so a side effect inside `change` would run twice.

    FAILS CLOSED ON A DAMAGED FILE, which it did not used to. The digest is taken BEFORE the
    read, so a file that is unparseable or the wrong shape became `d = {}`, `change` added its
    one key, and `replace_if_unchanged` compared the digest of a file nothing had modified --
    it matched, and an almost-empty dict landed over the whole artifact with `landed=True`
    returned to a caller who now believes its record was appended to something. The non-dict
    branch did not even leave a `silence.note` behind. `silence.replace_if_unchanged` cannot
    catch this: it refuses only when the TARGET is unreadable AS BYTES at write time, and a
    corrupt-but-readable file digests perfectly well.

    The live targets make the cost concrete. `hostcheck.adopt()` writes WIKI_HOSTS.json from a
    SEPARATE process, so one torn read here un-adopted every host in the library at once --
    `scout.hostless()`, `feats_index.host_to_sources`, `hostcheck` and the MIN_HOST_COVERAGE=1.0
    standard all read that file. `escalation._read_stopped` was given this identical treatment
    for the identical shape in run #36, and its note is the whole argument: "Wrong-shape is not
    better evidence than unparseable. It is the same fact." An unreadable or wrong-shape file is
    NOT an empty one. Refuse the write and say why; a caller told "not landed" retries or
    escalates, where a caller told "landed" over a wreck loses the file silently.
    """
    import time as _t
    os.makedirs(os.path.dirname(path), exist_ok=True)
    last_why = "not attempted"
    for a in range(attempts):
        digest = silence.digest_of(path)
        try:
            with open(path, encoding="utf-8") as f:
                d = json.load(f)
        except FileNotFoundError:
            # The ordinary first write. Absent is not damaged.
            d = {}
        except Exception as e:
            silence.note("scout.py:mutate-unreadable")
            return False, ("%s is unreadable (%s) -- refusing to write over it, because an "
                           "unreadable shared artifact is not an empty one"
                           % (os.path.basename(path), type(e).__name__))
        if not isinstance(d, dict):
            # Previously the completely silent path: valid JSON of the wrong shape became {}
            # with no note at all, so the loss left no trace anywhere to find it by.
            silence.note("scout.py:mutate-wrong-shape")
            return False, ("%s holds %s, not an object -- refusing to write over it, because "
                           "wrong-shape is the same fact as unparseable"
                           % (os.path.basename(path), type(d).__name__))
        value = change(d)
        tmp = "%s.%d.%d.tmp" % (path, os.getpid(), a)
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(d, f, indent=1, sort_keys=True)
        landed, why = silence.replace_if_unchanged(tmp, path, digest)
        if landed:
            return True, value
        last_why = why
        try:
            os.remove(tmp)
        except OSError:
            pass
        _t.sleep(0.05 * (a + 1))
    # Never raises, matching every other shared write in this file: a caller that cannot land
    # gets told so and decides what "attempted but not recorded" means for it, rather than
    # believing a mutation happened that did not.
    silence.note("scout.py:mutate-failed")
    return False, last_why

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
    """-> (answer, why_not). `why_not` is None ONLY when a model actually answered.

    ONE STRING FOR FOUR DIFFERENT EVENTS, until order 7f2cbf26a60e. This swallowed every
    exception into a bare `return None`, and `scout()` then reported "model proposed nothing"
    -- so a dead transport, a failed `read.ensure_transport`, a closed pool and a model honestly
    answering "I do not know" were the same line in SCOUT.json. The last of those is an answer
    the SYSTEM prompt explicitly invites ("If you do not know where this material lives, return
    an empty list. That is the correct answer far more often than a guess"), and it is the one
    reading that must not be confused with the other three: `sweep()` stamps the source as
    attempted before the work, so a transport outage burned every hostless source's rotation
    slot and wrote a clean negative result for each, and the next reader saw a completed sweep
    that found nothing rather than a sweep that never asked. Same class as manifest_builder's
    fix for feats_index -- "a failed lookup SAYS SO, OUT LOUD ... NOT the same finding as a
    source with no attested feats".

    A `None` FROM `read._ask` IS ALSO NOT AN ANSWER, and that is the half an exception handler
    could never have caught: `_ask_ungated` returns None without raising when cascade mode has
    no transport, when every bucket declines and the card is benched, or when the local call
    times out. Nobody was asked in any of those either.
    """
    try:
        import read as R
        R.ensure_transport(verbose=False)
        got = R._ask(R.config(), SYSTEM, prompt, SCHEMA)
    except Exception as e:
        silence.note("scout.py:_ask")
        return None, type(e).__name__
    if got is None:
        silence.note("scout.py:_ask-no-transport")
        return None, "no transport answered"
    return got, None


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
    if probeable == 0:
        # THE MIRROR CASE `MIN_NAME_HITS` DID NOT CLOSE. `max(1, ...)` below stops the bar
        # from being unreachable when there is ONE usable name, but when there are ZERO the
        # floor still sets `needed = 1` against a `hits` that is structurally 0 forever --
        # `_names_in` skips every name under four characters, so nothing can ever be counted.
        # That reported as the ordinary "0 catalogued name(s) present, 1 needed", which reads
        # as a wrong guess rather than a check that was unsatisfiable before it ran. Say so.
        return {"url": url, "ok": False, "unverifiable": True, "hits": 0, "needed": 1,
                "chars": len(text),
                "why": "unverifiable: this source has no catalogued name longer than three "
                       "characters to probe a page with"}
    needed = max(1, min(MIN_NAME_HITS, probeable))
    return {"url": url, "ok": hits >= needed, "hits": hits, "needed": needed,
            "chars": len(text),
            "why": f"{hits} catalogued name(s) present, {needed} needed"}


def scout(source, names, register=True):
    """Ask where the material lives, then prove each answer before believing it.

    THE PROMPT IS SAMPLED; THE VERIFICATION IS NOT. Order e8cd908ce5e4 -- and this was the
    load-bearing half of that order, not a cosmetic one. Both the prompt and `verify()` used to
    be handed the SAME list, `[n for n in names if n and len(n) > 3][:PROBE_NAMES]`: the first
    25 usable names IN RECORD ORDER, with no ranking anywhere. `verify()` accepts a page only
    when at least `needed` of the names it was given appear on it, so a genuine page for a
    source whose catalogued names all sit past index 25 scored zero hits and was REJECTED. That
    is truncation without ranking on the input to a pass/fail decision -- the shape Hard Rule 0
    separates from ranking-then-taking-work-in-order -- and it was silently deciding that the
    26th name onward did not exist. Measured on the current roll: `The Elements Beyond` is
    hostless with 681 catalogued names, of which 25 were ever probed.
    The URL list beside it was uncapped on 2026-08-24 for the same reason; the name list it is
    verified AGAINST was left behind.

    So `verify()` now gets every probeable name. It costs nothing: `_names_in` is a regex pass
    over page text already in memory, 681 of them on the worst source on the roll.

    The PROMPT still takes a sample, and that one is a real cost (tokens), so it is RANKED
    first -- longest name first, ties broken alphabetically for determinism. Length is the
    available proxy for distinctiveness here: `Way of the Inkmaster` identifies a page and
    `Warden` identifies nothing. And it says how many it is showing out of how many exist, so
    the model is not handed a smaller universe wearing the shape of the whole one.
    """
    probeable = [n for n in names if n and len(n) > 3]
    shown = sorted(probeable, key=lambda n: (-len(n), n))[:PROBE_NAMES]
    _more = len(probeable) - len(shown)
    prompt = (f"SOURCE: {source}\n"
              f"CATALOGUED UNDER IT ({len(probeable)} name(s) in all"
              + (f"; the {len(shown)} most distinctive are listed" if _more else "")
              + f"): {', '.join(shown)}\n\n"
              f"Where is this material readable online?")
    got, why_not = _ask(prompt)
    if why_not:
        # NOT "proposed nothing" (order 7f2cbf26a60e). Nobody was asked, so this source has no
        # result -- negative or otherwise -- and `reached` is what `sweep()` reads to give it its
        # rotation slot back.
        return {"source": source, "proposed": 0, "kept": [], "checked": [], "reached": False,
                "note": "the model was never reached (%s)" % why_not}
    # Every URL the model proposes gets PROVEN, not the first eight of them. The prompt above
    # explicitly invites a spread across seven or more platforms (own site, GM Binder,
    # Homebrewery, D&D Wiki, DMs Guild, itch.io, subreddit wiki, GitHub) for one creator, so a
    # well-documented author is precisely the case where a ninth URL exists -- and the cap sat
    # BEFORE verification, so the dropped candidates were never even tested. Verification is one
    # cheap fetch each. Uncapped 2026-08-24 (Hard Rule 0).
    urls = [u for u in ((got or {}).get("urls") or []) if str(u).startswith("http")]
    if not urls:
        # A REAL negative: the model answered and named nowhere. `reached` says so, so this is
        # not confused with the branch above.
        return {"source": source, "proposed": 0, "kept": [], "checked": [], "reached": True,
                "note": "model proposed nothing"}

    kept, checked = [], []
    for u in urls:
        # `probeable`, not the prompt's sample: see this function's docstring. A page is judged
        # against every name catalogued under the source, never against the first 25 of them.
        r = verify(u, probeable)
        checked.append(r)
        if r["ok"]:
            kept.append(u)
    # THREE STATES, LIKE `reached` (order 7f2cbf26a60e; order a17efd461050 for this field).
    # `True` everywhere else in this module means "the registry took them" -- using it as the
    # INITIAL value made "nobody tried" indistinguishable from "it worked", which is exactly
    # how `--dry` (register=False) ended up reporting sources as FOUND having registered
    # nothing: `sweep()` read the untouched default straight through. `None` means nobody
    # attempted registration (register=False, or nothing was kept to register); `True` means
    # both the page registration and the host adoption landed; `False` means one of them was
    # attempted and failed.
    registered, reg_note = None, ""
    if kept and register:
        import endpoint as EP
        # THE PAGE REGISTRATION IS GUARDED, LIKE THE HOST REGISTRATION TEN LINES BELOW ALWAYS
        # WAS (order d57377577891). `endpoint.register` raises DELIBERATELY -- an unreadable or
        # wrong-shaped SOURCE_PAGES.json is re-raised immediately, and eight consecutive
        # compare-and-swap refusals under contention end in RuntimeError -- and it returns None
        # on success, so the raise is its only signal. This call had no handler, and neither
        # does `sweep()`'s loop, so one raise took down the WHOLE CYCLE rather than one source:
        # `results` was discarded, so the SCOUT.json write and the ARCHIVE append never ran and
        # nothing anywhere recorded that the cycle happened; the `never_asked` unstamp never
        # ran; and the attempt stamps written BEFORE the work still stood, so every source in
        # the batch -- including the ones already scouted successfully, whose kept URLs are in
        # SOURCE_PAGES.json but in no log -- had spent its rotation slot for nothing. On
        # foreman's 30-second scout_hostless loop that is a repeating burn.
        #
        # NOT reported as a success: the URLs passed verification and the registry does not
        # have them, so the source stays hostless and will be re-scouted, which is the correct
        # self-healing outcome as long as the log says why.
        try:
            EP.register(source, kept)
            registered = True
        except Exception as e:
            silence.note("scout.py:register-pages")
            registered = False
            reg_note = ("%d page(s) verified but NOT registered (%s: %s)"
                        % (len(kept), type(e).__name__, str(e)[:120]))
        # AND THE HOST ADOPTION IS GATED ON THE PAGE REGISTRATION HAVING WORKED. The mapping
        # written below is literally `hosts[source] = "pages:" + source` -- it tells `feats` to
        # read this source's pages OUT OF SOURCE_PAGES.json. Adopting it while the pages are not
        # in that file points the reader at nothing and, worse, takes the source off
        # `hostless()`, so the self-healing re-scout this branch is counting on would never
        # happen. The two registrations are one fact and must land or fail together -- so a
        # failed adoption takes `registered` back to False even though the page registration
        # itself succeeded; `True` is reserved for both landing.
        if registered:
            try:
                import feats as F

                def _adopt(hosts):
                    hosts[source] = "pages:" + source

                landed, _ = _mutate(F.HOSTS, _adopt)
                if not landed:
                    silence.note("scout.py:register-host")
                    registered = False
                    reg_note = ("%d page(s) registered but the host map could not be updated"
                                % len(kept))
            except Exception as e:
                silence.note("scout.py:register-host")
                registered = False
                reg_note = ("%d page(s) registered but host adoption failed (%s: %s)"
                            % (len(kept), type(e).__name__, str(e)[:120]))
    elif kept:
        # register=False (--dry): pages were verified but nobody was ever asked to save them.
        # `registered` stays None -- nobody tried, which is neither a success nor a failure --
        # and the note says so, so `sweep()`'s FOUND/UNSAVED print reads correctly under --dry
        # instead of defaulting to "registered".
        reg_note = "%d page(s) verified (--dry: not registered)" % len(kept)
    # Pages that exist and decline us are a finding for the owner, not a retry target.
    blocked = [c for c in checked if c.get("code") in (401, 403, 429)]
    if blocked:
        try:
            urls_blocked = {c["url"] for c in blocked}

            def _add_blocked(prev):
                prev[source] = sorted(urls_blocked | set(prev.get(source) or []))

            landed, _ = _mutate(BLOCKED, _add_blocked)
            if not landed:
                silence.note("scout.py:blocked")
        except Exception:
            silence.note("scout.py:blocked")
    # `registered` rides in the result so `sweep()` can log the source as scouted-but-
    # unregistered and move on. The model's own note is kept: the registration failure is
    # PREPENDED rather than substituted, because both are findings and the second one does not
    # stop being true because the first happened.
    _note = (got or {}).get("note", "")
    if reg_note:
        _note = reg_note + ("; " + _note if _note else "")
    return {"source": source, "proposed": len(urls), "kept": kept, "checked": checked,
            "blocked": [c["url"] for c in blocked], "reached": True,
            "registered": registered, "note": _note}


class HostsUnreadable(RuntimeError):
    """WIKI_HOSTS.json could not be read as the shared host map it is."""


def hostless():
    """Sources with nowhere to read from — the only ones worth scouting.

    THE READ SIDE NOW HAS THE DISCIPLINE `_mutate` HAS ALWAYS ARGUED FOR ON THE WRITE SIDE
    (order a0dddab8a9bc). `hostcheck.adopt()` writes WIKI_HOSTS.json from a SEPARATE process --
    the exact hazard `_mutate`'s docstring is about -- so a torn read or a wrong-shape file
    here is not hypothetical. Raises rather than falling back to `{}`: an empty host map would
    make EVERY source look hostless and put the whole roll into the scout rotation.
    `foreman.scout_hostless` already wraps `SC.sweep()` in a broad `except Exception`, so this
    still surfaces as a reported failure on the standing path -- now a distinguishing one.
    """
    import weave_index as WI
    import feats as F
    try:
        with open(F.HOSTS, encoding="utf-8") as f:
            hosts = json.load(f)
    except Exception as e:
        silence.note("scout.py:hosts-unreadable")
        raise HostsUnreadable(
            "%s is unreadable (%s) -- refusing to read it as an empty host map, because an "
            "unreadable shared artifact is not an empty one"
            % (os.path.basename(F.HOSTS), type(e).__name__)) from e
    if not isinstance(hosts, dict):
        silence.note("scout.py:hosts-wrong-shape")
        raise HostsUnreadable(
            "%s holds %s, not an object -- refusing to read it as an empty host map, because "
            "wrong-shape is the same fact as unparseable"
            % (os.path.basename(F.HOSTS), type(hosts).__name__))
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
        # WHOLE NAMES. This was `", ".join(s[:30] for s in deferred)`, which cut source names
        # mid-name -- the identical shape standards.py's shelf-ranks block already removed with
        # the note "ALL OF THEM, not [:120] characters -- that cut the joined name list
        # mid-name". A deferral list exists so a person can see the far side of the window, and
        # half a source name is not a source anyone can look up. Order e8cd908ce5e4.
        print(f"   {len(deferred)} waiting for a later cycle (longest-waiting first): "
              + ", ".join(deferred))
    # STAMPED BEFORE THE WORK, NOT AFTER. A source that crashes the scout must still count as
    # attempted, or it sorts to the front again next cycle and pins the window exactly the way
    # the entry-count ordering did -- the same bug wearing the fix's clothes.
    #
    # Order d3313adbf641: this used to mutate the `seen` snapshot read above (for RANKING) and
    # write that same copy back -- a plain read-modify-write with no staleness check, over a
    # file nothing stops a second `sweep()` from touching at the same moment. A lost stamp here
    # puts a source back at the front of the rotation, which is the exact failure this
    # function's own docstring measured and fixed on the ranking side. `_mutate` re-reads the
    # CURRENT file at write time, so a concurrent stamp from another process is merged rather
    # than overwritten.
    now = time.time()

    def _stamp(seen_now):
        for src in order:
            seen_now[src] = now

    landed, _ = _mutate(ATTEMPTS, _stamp)
    if not landed:
        silence.note("scout.py:attempts-unwritable")
    results, found = [], 0
    for src in order:
        r = scout(src, todo[src], register=register)
        results.append(r)
        # `is True`, not truthy/default-True (order a17efd461050): `registered` is now a
        # three-state field (None = nobody tried, True = landed, False = tried and failed), so
        # only an actual landing counts as FOUND. Under --dry every result's `registered` is
        # None, so `found` stays honestly 0 rather than the field's old default standing in for
        # a registration that never happened.
        if r["kept"] and r.get("registered") is True:
            found += 1
            print(f"   FOUND  {src:<38}  {len(r['kept'])} page(s)")
            for u in r["kept"]:
                print(f"            {u}")
        elif r["kept"]:
            # PAGES VERIFIED, REGISTRY DID NOT TAKE THEM (order d57377577891). Not counted in
            # `found`, because `found` is the count of sources that now have somewhere to read
            # from and this one does not. Deliberately NOT unstamped either: the source did have
            # its turn -- a model call was spent on it -- and a registry that is persistently
            # unwritable would otherwise unstamp the same sources every cycle and pin the
            # rotation window, which is the exact failure the stamp-before-the-work rule above
            # exists to prevent. It stays hostless, so `hostless()` returns it again and the
            # ordinary rotation re-scouts it; this line is what makes that legible rather than
            # mysterious.
            print(f"   UNSAVED {src:<37}  {r.get('note') or 'registration failed'}")
        else:
            # NEITHER COLUMN IS CUT ANY MORE (order e8cd908ce5e4). `src[:38]` truncated the
            # source NAME and `reasons[:60]` cut the per-source failure reason mid-sentence --
            # and the reason is the whole product of this line: "exists but declines readers"
            # and "no such host or no route" are different findings with different owners, and
            # a run of them concatenated hits 60 characters immediately. The [:60] shape is the
            # one standards.py's unrecognised-pool block already removed with the note "fix a
            # shape, then grep the tree for it"; this is that grep. `:<40` is kept as a PAD,
            # which lengthens a short name and leaves a long one whole -- alignment is a
            # courtesy and it does not get to overrule what the line says.
            reasons = ", ".join(sorted({c.get("why", "?") for c in (r.get("checked") or [])})
                                ) or r.get("note", "?")
            print(f"   none   {src:<38}  {reasons}")
    if register:
        print(f"\n{found} of {len(order)} sources now have somewhere to read from")
    else:
        # --dry NEVER registers, so `found` (which now requires `registered is True`) is
        # always 0 here -- that is correct, not a regression, but printing it bare would still
        # read as "found nothing" rather than "found nothing to register on purpose". Report
        # what --dry actually measured: sources whose pages verified and WOULD have been kept.
        verified = sum(1 for r in results if r["kept"])
        print(f"\n{verified} of {len(order)} sources would give somewhere to read from "
              "(--dry: nothing registered)")
    # A SOURCE THAT WAS NEVER ASKED HAS NOT HAD ITS TURN (order 7f2cbf26a60e). The stamp above
    # goes on before the work on purpose -- a source that CRASHES the scout must still count as
    # attempted, or it pins the window -- but a transport outage is not that: it burns every
    # source's rotation slot at once and writes a clean negative result for each, so the roll
    # comes back a cycle later looking scouted and empty. Only a stamp this pass itself just
    # wrote is reverted, and only to the value it had before, so a concurrent sweep that stamped
    # the same source for its own real attempt is left alone.
    #
    # `is False`, not falsy: a result dict without the key at all (an older log entry, a drill
    # stub) means "this predates the distinction", and guessing on its behalf would put the
    # rotation back where this order found it.
    never_asked = [r["source"] for r in results if r.get("reached") is False]
    if never_asked:
        def _unstamp(seen_now):
            for src in never_asked:
                if seen_now.get(src) != now:
                    continue          # somebody else stamped it since; not ours to take back
                if seen.get(src) is None:
                    seen_now.pop(src, None)
                else:
                    seen_now[src] = seen[src]

        if not _mutate(ATTEMPTS, _unstamp)[0]:
            silence.note("scout.py:attempts-unwritable")
        print(f"   {len(never_asked)} source(s) were NEVER ASKED (the model could not be "
              f"reached) and keep their place in the rotation")
    try:
        prev = json.load(open(LOG, encoding="utf-8")) if os.path.exists(LOG) else []
    except Exception:
        silence.note("scout.py:log-unreadable")
        prev = []
    prev.append({"at": time.strftime("%Y-%m-%d %H:%M"), "results": results})
    # GATED, exactly as the `_mutate` call twenty lines above already is. `_land` returns
    # `silence.write_json`'s verdict -- whether the rename LANDED -- and this discarded it, so a
    # denied replace dropped this cycle's scouting record with nothing said anywhere. Milder than
    # the sibling defects in this sweep because nothing here prints a false success and the log
    # is advisory rather than load-bearing; recorded all the same, because "the log has no entry
    # for that cycle" and "that cycle never ran" are the two readings this note tells apart.
    # Run #36 discarded-verdict sweep.
    #
    # AND THE ROLL-OFF IS AN ARCHIVE, NOT A DELETION (order e8cd908ce5e4). This wrote
    # `prev[-40:]`, so on every cycle past the fortieth the oldest scouting record was dropped
    # from disk with nothing said. Now the cycles falling out of the window are appended to
    # `ARCHIVE` FIRST, and the window is only trimmed if every one of them landed -- the move
    # ordering `foreman.py` already uses for its failures ledger. If an append fails, this cycle
    # keeps the whole list in `LOG` rather than trimming: a duplicated cycle in an append-only
    # archive is a far smaller fault than a deleted one, and the note says which happened.
    window, roll = prev[-LOG_CYCLES:], prev[:-LOG_CYCLES]
    if roll:
        _arch = _archive_for(LOG)
        _lost = [c for c in roll
                 if not silence.append_line(_arch, json.dumps(c, ensure_ascii=False))]
        if _lost:
            silence.note("scout.py:archive-unwritable")
            sys.stderr.write("scout: %d cycle(s) could not be archived to %s; keeping all %d "
                             "in the log rather than dropping them.\n"
                             % (len(_lost), os.path.basename(_arch), len(prev)))
            window = prev
    if not _land(LOG, window, sort_keys=False):
        silence.note("scout.py:log-unwritable")
        sys.stderr.write("scout: SCOUT.json write denied -- this cycle's %d results are not in "
                         "the log; the run itself was fine.\n" % len(results))
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
        # WHOLE. This was `[:2000]`, which silently cut the single-source result a person had
        # explicitly asked for by name -- and the part that gets cut is `checked`, the per-URL
        # verdicts, which is the only reason to run `--source` rather than read the log. A
        # truncated JSON document does not even parse, so the cut did not merely shorten the
        # answer, it destroyed it as data. Order e8cd908ce5e4.
        print(json.dumps(r, indent=1))
        return 0
    sweep(limit=a.limit, register=not a.dry)
    return 0


if __name__ == "__main__":
    sys.exit(main())
