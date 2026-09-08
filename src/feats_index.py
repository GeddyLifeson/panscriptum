#!/usr/bin/env python3
"""
FEATS_INDEX — the join that makes 47,017 mined feats reachable as a chapter.

WHAT WAS MISSING
----------------
`feats.py` mines attested deeds out of wiki prose and lands them under `data/readfeats/<host>/
<Entity>.json`: each feat a QUOTED sentence, tagged with one of the eleven Assay axes and
carrying the page it came from. That is the Charter's Part Three worksheet material, already
gathered -- 47,017 of them across 1,412 records, averaging 33 per entity (re-measured
2026-08-25; the store grows, so treat every count in this note as a reading, not a constant).

And nothing could reach it. `assay.py` and `magnitude.py` consume feats per-entity when scoring,
but the generation path had no idea the store existed: `manifest_builder` groups a source's
CATALOGUE entries by category and emits chapter jobs, and feats are not catalogue entries. So
the best-evidenced material in the library was structurally unable to become prose.

WHY THE OBVIOUS JOIN DOES NOT WORK
----------------------------------
The tempting key is the entry's own `wiki_page` URL: parse out host and title, look up
`readfeats/<host>/<title>.json`. Measured, that reaches **849 of 1,412** records. The reason it
fails is instructive and is the sort of thing this project keeps paying for: **a catalogue entry
does not necessarily have a URL.** All 341 `all Bloons TD` entries carry `wiki_page: None`, so
its feats -- Geraldo, Gravelord Lych, Magus Perfectus, all present in the catalogue BY NAME and
all mined successfully -- could never be matched by a URL join. A key that is absent on a whole
source is not a weak key, it is no key.

THE JOIN THAT WORKS
-------------------
`data/WIKI_HOSTS.json` is the authoritative source -> host binding (202 sources). Invert it,
then match the feats record's `entity` against the source's entry NAMES, normalised. Measured
over the whole store: **1,410 of 1,412 records and 46,868 of 47,017 feats -- 99.9%**.

WHERE THE HOST COMES FROM, AND THE FOURTEEN RECORDS THAT PROVES
---------------------------------------------------------------
A record's directory name is `cachekey.host_dir(host)` -- the shared sanitiser, which folds every
run of non-alphanumerics to a single `_`. `load_index` used to recover the host by substituting
`"_"` -> `"."` back, and that is not an inverse: it cannot know which underscores were dots and
which were hyphens. Every hyphenated host therefore produced a host string that exists nowhere,
and its records could match no source. Measured 2026-08-25, before the fix: **14 records / 222
feats** across `date-a-live`, `sakamoto-days`, `the-amazing-digital-circus` and `uncle-grandpa`
(all four `*.fandom.com`).

An earlier version of this note read that as a gap in `WIKI_HOSTS` -- four sources "whose host was
never recorded" -- and `main()` agreed with it, printing NOT IN WIKI_HOSTS beside each. Both were
looking at the same invented string. **All four hosts are bound in `WIKI_HOSTS` and always were**;
the join was asking for a host nobody had ever written down. The record itself stores the exact
host it was mined from, one field away from where the derivation was happening, so `load_index`
now asks the record. Binding hosts would have fixed nothing.

What remains stranded after that is a different problem, and a real one:

  * **2 records / 149 feats are on hosts that ARE bound** (`dc.fandom.com` -> DC,
    `marvel.fandom.com` -> Marvel): `Wally West (Prime Earth)` and `Brood`. The host is known;
    the catalogue simply holds no entry under a matching name. Neither will loosening `_norm`
    recover them (see its docstring, which measures why). They are catalogue gaps, and the only
    ones left.

They are REPORTED rather than dropped quietly, because an unjoined feats record is a mined deed
that no volume will ever print.

ON SHARED HOSTS, DELIBERATELY
-----------------------------
Some hosts serve several sources: `forgottenrealms.fandom.com` backs thirty D&D books,
`en.wikipedia.org` backs twenty-two, `godofwar.fandom.com` backs both `God of War` and
`major fantasy pantheons`. An entity catalogued in two of them attaches to BOTH, and that is
correct rather than a duplication bug: each volume covers its own cast, and Kratos genuinely
appears in both casts. Measured, this affects 35 records and 531 feats -- small, and the
alternative (picking one source by some tie-break) would silently rob the other volume of
evidence it is entitled to.

NO CAPS. `feats_for_source` returns every feat of every matching entity. Callers that paginate
must page through all of it, exactly as `manifest_builder` already does for large chapters.
"""
import collections
import json
import os
import sys

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import cachekey  # noqa: E402
import silence  # noqa: E402

_BAD_CHARS = (chr(8), chr(11), chr(12), chr(7))
if any(c in open(os.path.abspath(__file__), encoding="utf-8").read() for c in _BAD_CHARS):
    raise SystemExit(__file__ + ": a regex escape was eaten in transit.")

READFEATS = os.path.join(HERE, "data", "readfeats")
WIKI_HOSTS = os.path.join(HERE, "data", "WIKI_HOSTS.json")

# `WIKI_HOSTS` records owner-supplied books as `pages:<title>` rather than a hostname. Those are
# not wiki hosts and must not be inverted into the host map, or every one of them would collide
# on a single pseudo-host.
_PAGES_SENTINEL = "pages:"

# KEYED BY THE PATH THAT WAS ASKED FOR, not by the function that was called. Both readers below
# take a path override and used to cache under one global slot each, so a second call with a
# different path silently returned the FIRST path's answer -- a join quietly computed against a
# store nobody asked for. No caller passes a non-default argument today; the signature invites
# exactly that, and a cache that ignores its own key is a wrong answer waiting for a caller.
_CACHE = {"hosts": {}, "index": {}, "index_faults": {}}

# source name -> ["<source> | kept <a>, dropped <b>", ...]. Filled by `feats_for_source` when two
# entries of ONE source fold to the same `_norm` key; see the comment there. Accumulated across
# calls rather than reset, so a caller that walks the roll ends holding the whole picture, and
# `audit()` reports the corpus-wide figure independently by rewalking the records. (order
# 04a3f79b7f55)
_ENTRY_COLLISIONS = {}


def _norm(s):
    """Fold a name to its comparable core.

    Case and punctuation differ freely between a wiki page title and the catalogue's entry name,
    and both are written by different passes. Alphanumerics only.

    THIS DOES NOT STRIP A PARENTHETICAL, and an earlier version of this docstring claimed it did
    -- it offered "Zangetsu (Zanpakutou spirit)" vs "Zangetsu" as a case this folds together.
    It does not: alphanumeric-only folding gives `zangetsuzanpakutouspirit` against `zangetsu`.
    Corrected 2026-08-24 after measuring, because a comment that promises a capability the code
    lacks is how the next reader mis-diagnoses a stranded record.

    The STRICT form is nonetheless the right one, and that part of the original claim held up.
    174 of 1,412 feats records carry a parenthetical and 173 of them join anyway, because the
    catalogue overwhelmingly records the SAME disambiguated form. Loosening it would recover
    the one that misses (`Wally West (Prime Earth)` would fold onto the catalogue's `Wally West
    (Earth-16)`, silently merging two DC continuities) while risking exactly that class of
    conflation across the whole store. It is a catalogue gap, not a folding failure --
    see `audit()`, which reports a known host separately from an unrecorded one.
    """
    return "".join(c for c in (s or "").lower() if c.isalnum())


def host_to_sources(path=WIKI_HOSTS):
    """{host: [source, ...]} inverted from WIKI_HOSTS.json, minus the `pages:` sentinels.

    RAISES rather than returning an empty map when the host file cannot be read, and does NOT
    cache that emptiness (order e16a93099bbe). The old handler swallowed the failure, set
    `wh = {}` and then cached the empty result for the life of the process with no retry -- so
    an unreadable or missing WIKI_HOSTS.json made `feats_for_source` return [] for EVERY source,
    for ever. That defeated the guard one level up: `manifest_builder` wraps its
    `feats_for_source` call in `except Exception` specifically so a bug here "says so, OUT LOUD"
    (manifest_builder.py:342-358), and its own comment says a swallowed failure here "produce[s]
    the identical observable result to this source genuinely has no attested feats" -- but no
    exception ever escaped this module, so that WARNING could never print and the volume was
    built with no Feats chapter and nothing distinguishing it from a source with none. Reproduced
    before the fix: host_to_sources('<WIKI_HOSTS>.does-not-exist') returned {} with no exception
    and cached it. The note is kept for the ledger; the raise is what reaches the operator.
    """
    if path in _CACHE["hosts"]:
        return _CACHE["hosts"][path]
    out = collections.defaultdict(list)
    try:
        with open(path, encoding="utf-8") as f:
            wh = json.load(f)
    except Exception as e:
        silence.note("feats_index.host_to_sources")
        # UNCUT (order 70f5e5150f8b). A hard [:110] slice on the underlying exception text is
        # Hard Rule 0's exact shape on a stored/reported diagnostic -- the same one already
        # repaired at standards.py:174-181 and catalogue_models.py's provider_pool_denominator
        # [:40] cut (order 6d354a508b96). Whitespace is collapsed instead of sliced, so a long
        # or multi-line OS/JSON error still prints as one row without losing its tail.
        raise RuntimeError(
            "feats_index.host_to_sources(): %s could not be read (%s: %s) -- the source->host "
            "binding is the whole join, so every feats lookup would silently return nothing. "
            "This is NOT the same finding as a source with no attested feats."
            % (path, type(e).__name__, " ".join(str(e).split()))) from e
    for src, host in (wh or {}).items():
        if isinstance(host, str) and host and not host.startswith(_PAGES_SENTINEL):
            out[host.lower()].append(src)
    _CACHE["hosts"][path] = dict(out)
    return _CACHE["hosts"][path]


def load_index(root=READFEATS):
    """Every feats record on disk, as {(host, normalised entity): record}.

    Read once and cached: the store is ~1,240 small files and the manifest builder would
    otherwise re-walk it per source.

    WHAT IT COULD NOT INDEX IS COUNTED, not merely skipped (order e16a93099bbe). A record that
    will not parse was dropped with a `silence.note` and a `continue`, and a second record
    normalising onto an existing (host, entity) key overwrote the first without a word -- while
    `audit()` reported `records = len(idx)`, so every such loss was subtracted from the
    DENOMINATOR and the printed join rate went UP. That is the exact shape the module's own
    docstring promises against: a stranded record is "counted and named rather than left to be
    inferred from a smaller total". The tallies live in `_CACHE["index_faults"][root]` and are
    read back through `index_faults()`.
    """
    if root in _CACHE["index"]:
        return _CACHE["index"][root]
    # NO CAPS on either list: these name the files a person has to go and look at, and a
    # truncated list of them is a smaller universe wearing the same shape (Hard Rule 0).
    faults = {"unreadable": 0, "collided": 0, "unreadable_files": [], "collided_keys": []}
    idx = {}
    if not os.path.isdir(root):
        _CACHE["index"][root] = idx
        _CACHE["index_faults"][root] = faults
        return idx
    # A directory name is `cachekey.host_dir(host)`, and that is NOT invertible by spelling:
    # it folds every run of punctuation to `_`, so `date-a-live.fandom.com` and a hypothetical
    # `date.a.live.fandom.com` land in the same directory. The record itself stores the exact
    # host it was mined from, so ASK IT. The map below is only for a record that somehow lacks
    # one: it re-derives each KNOWN host's directory through the one helper (never re-spelling
    # the sanitiser here) and looks the directory up, which is the only sound direction.
    by_dir = {}
    for known in host_to_sources():
        by_dir.setdefault(cachekey.host_dir(known), known)
    for hdir in sorted(os.listdir(root)):
        p = os.path.join(root, hdir)
        if not os.path.isdir(p):
            continue
        fallback = (by_dir.get(hdir) or hdir.replace("_", ".")).lower()
        for fn in sorted(os.listdir(p)):
            if not fn.endswith(".json"):
                continue
            try:
                with open(os.path.join(p, fn), encoding="utf-8") as f:
                    rec = json.load(f)
            except Exception:
                silence.note("feats_index.load_index")
                faults["unreadable"] += 1
                faults["unreadable_files"].append(hdir + "/" + fn)
                continue
            entity = rec.get("entity") or fn[:-5]
            host = (rec.get("host") or fallback).lower()
            rec.setdefault("entity", entity)
            rec["host"] = host
            key = (host, _norm(entity))
            if key in idx:
                # LAST WRITER STILL WINS -- the resolution is not being changed here, only made
                # visible. Two records folding onto one key is a real condition (a re-mine under
                # a differently-punctuated title), and picking a different survivor is a
                # curatorial call, not a bug fix. What was wrong was that the loser vanished
                # from the total as though it had never been mined.
                faults["collided"] += 1
                faults["collided_keys"].append("%s | %s" % (host, entity))
            idx[key] = rec
    _CACHE["index"][root] = idx
    _CACHE["index_faults"][root] = faults
    return idx


def index_faults(root=READFEATS):
    """What `load_index` could not put in the index, for this root.

    -> {"unreadable": n, "collided": n, "unreadable_files": [...], "collided_keys": [...]}.
    Builds the index if it has not been built, so the answer is never a stale zero.
    """
    load_index(root)
    return dict(_CACHE["index_faults"].get(root)
                or {"unreadable": 0, "collided": 0, "unreadable_files": [],
                    "collided_keys": []})


# HOW OFTEN THE UNBOUND CASE HAS BEEN ANSWERED WITH AN EMPTY LIST, per source, and what kind of
# source it was (order c8dc624e4e02; owner ruling 2026-09-08, "Filters that quietly remove
# entities from the roll" -- *the missing counters land in feats_index/manifest_builder and
# recover_folder_records*). A count nobody prints is not a count, so `binding_report()` below is
# what a caller prints; the counter is what makes it possible to print at all.
_UNBOUND_ASKED = {}


def source_binding(source_name, hosts=None):
    """Why does this source have no host? -> "bound" | "pages" | "doc" | "unbound".

    THE ANSWER `feats_for_source` COULD NOT GIVE. It returned a bare `[]` for a source with no
    host binding, which is the exact conflation the surrounding code was written to forbid:
    `host_to_sources` was deliberately taught to RAISE rather than return {} so that an
    unreadable WIKI_HOSTS.json "could not produce the identical observable result to *this source
    genuinely has no attested feats*" -- and `if not hosts: return []` produced that identical
    observable result for a source that is simply not IN WIKI_HOSTS.json. The guard one level up
    in `manifest_builder` only prints its WARNING on an EXCEPTION, so nothing distinguished the
    two cases at the one call site that matters: the volume was built with no Feats chapter and
    the build report read like a clean run.

    MEASURED 2026-08-30: 216 record files on disk, 198 sources bound to a host, 18 UNBOUND -- of
    which five are legitimate `pages:` sentinels (owner-supplied books that correctly have no
    wiki: A Plethora of Paladins; Guildmasters' Guide to Ravnica; KibblesTasty; all Creeper
    World; the Sex Worker background) and THIRTEEN are simply not recorded. The two answers must
    not sound alike: "not a wiki source" is correct by design and should raise no alarm, while
    "not recorded" is a data gap somebody has to close.
    """
    hosts = hosts if hosts is not None else host_to_sources()
    for h, srcs in (hosts or {}).items():
        if source_name in srcs:
            if str(h).startswith("pages:"):
                return "pages"
            if str(h).startswith("doc:"):
                return "doc"
            return "bound"
    # `host_to_sources` strips the `pages:` sentinels, so a source bound to one is not in the map
    # at all and would otherwise read as unrecorded. Asked of the raw file, which is the only
    # place that distinction survives.
    try:
        with open(WIKI_HOSTS, encoding="utf-8") as f:
            raw = json.load(f)
    except Exception:
        # UNREADABLE IS NOT UNBOUND. `host_to_sources` above already raises on this file, so
        # reaching here means it read once and will not read again -- a fault about the FILE,
        # never a verdict about the source.
        silence.note("feats_index.py:source-binding-hosts")
        return "unknown"
    h = (raw or {}).get(source_name)
    if not h:
        return "unbound"
    return "pages" if str(h).startswith("pages:") else (
        "doc" if str(h).startswith("doc:") else "bound")


def unbound_asked():
    """-> {source: kind} for every source `feats_for_source` answered [] for want of a host.

    Printed by whoever built the manifest. Nothing is inferred from an empty dict: a caller that
    never asked and a run where every source was bound produce the same empty map, which is why
    the report line belongs beside the build's own totals rather than here.
    """
    return dict(_UNBOUND_ASKED)


def feats_for_source(source_name, record, binding=None):
    """Every mined feat belonging to this source's cast, entity by entity.

    `binding` IS AN OUT-CHANNEL FOR *WHY* THE LIST IS EMPTY (order c8dc624e4e02; owner ruling
    2026-09-08). Pass a dict and it is stamped with `{"kind": ...}` from `source_binding` -- see
    that function for the whole argument. The return value is unchanged so no caller breaks, and
    a caller that does not pass one is counted in `unbound_asked()` regardless, so the condition
    cannot go unrecorded merely because nobody was listening.

    `record` is the source's catalogue record (the thing `pipeline.records()` yields), because
    the match is against its ENTRY NAMES -- that is what makes the join survive a source whose
    entries carry no URL.

    Returns a list of dicts, one per entity that has feats, each carrying the catalogue entry it
    matched so the prose has the entry's own description and magnitude to hand:

        {"entity", "host", "pages", "feats": [{"feat", "axis", "page"}, ...],
         "axis_counts": {axis: n}, "entry": <the catalogue entry>, "feat_count": n}

    Ordered by feat count, richest first, then by name for stability. RANKED, NEVER TRUNCATED --
    if a generation run is interrupted the best-evidenced entities have already been written.
    """
    idx = load_index()
    host_map = host_to_sources()
    hosts = [h for h, srcs in host_map.items() if source_name in srcs]
    if not hosts:
        kind = source_binding(source_name, host_map)
        if binding is not None:
            binding.clear()
            binding.update({"kind": kind, "hosts": []})
        _UNBOUND_ASKED[source_name] = kind
        return []
    if binding is not None:
        binding.clear()
        binding.update({"kind": "bound", "hosts": sorted(hosts)})
    # THE LOSER OF A WITHIN-SOURCE NAME COLLISION IS RECORDED (order 04a3f79b7f55). This was a
    # bare `entries_by_norm.setdefault(...)`: two entries of ONE source whose names fold to the
    # same `_norm` key resolved to whichever was listed first in `record['entries']`, and the
    # second simply vanished, with no count, no note and no mention in `audit()`'s report.
    #
    # That is the identical class of problem `load_index` above tracks explicitly, incrementing
    # `faults['collided']` and appending to `faults['collided_keys']`, under a comment that gives
    # the reason: "two records folding onto one key is a real condition ... What was wrong was
    # that the loser vanished from the total as though it had never been mined."
    #
    # WHAT HAPPENS HERE IS NARROWER THAN THE load_index CASE, and saying so is part of the
    # finding: no mined FEAT becomes unreachable, because the entity's feats still attach to
    # whichever catalogue entry won. What can go wrong is that the ENTRY metadata -- the
    # description and magnitude used downstream when the feats prose is generated -- is taken
    # from the wrong one of two same-named catalogue entries.
    #
    # MEASURED over all 282,822 catalogued entries in data/records (whole corpus, no sampling):
    # 992 within-source collisions. Most are exact repeats of one name, where the two entries say
    # the same thing and the choice does not matter; some are not -- Acquisitions Incorporated
    # carries 'New Hampshire Darkmagics' and 'Newhamp Shire (Darkmagics)', which fold together
    # and are different rows. Last-writer-wins is NOT changed here: which of two same-named
    # entries should survive is a curatorial call. What changes is that it is no longer invisible.
    entries_by_norm = {}
    collisions = []
    for e in (record.get("entries") or []):
        k = _norm(e.get("name"))
        if k in entries_by_norm:
            collisions.append("%s | kept %r, dropped %r"
                              % (source_name, entries_by_norm[k].get("name"), e.get("name")))
            continue
        entries_by_norm[k] = e
    if collisions:
        _ENTRY_COLLISIONS[source_name] = collisions

    out = []
    for host in hosts:
        for (h, ent_norm), rec in idx.items():
            if h != host or ent_norm not in entries_by_norm:
                continue
            feats = rec.get("feats") or []
            if not feats:
                continue
            axes = collections.Counter(f.get("axis") for f in feats if f.get("axis"))
            out.append({
                "entity": rec.get("entity"),
                "host": host,
                "pages": rec.get("pages") or [],
                "feats": feats,
                "axis_counts": dict(axes),
                "feat_count": len(feats),
                "entry": entries_by_norm[ent_norm],
            })
    out.sort(key=lambda r: (-r["feat_count"], r["entity"]))
    return out


def binding_report(records_dir=None):
    """Every catalogued source classified by WHY it has (or has not) a wiki host.

    -> {"bound": [...], "pages": [...], "doc": [...], "unbound": [...], "unknown": [...]}

    THE COUNTER THAT WAS MISSING (order c8dc624e4e02; owner ruling 2026-09-08). `audit()` finds
    the condition from the other end -- a feats record on an unbound host lands in
    `stranded_hosts` and prints NOT IN WIKI_HOSTS -- but that only sees hosts we have already
    MINED. A source that was never mined because it was never bound leaves no feats record at
    all, so it appears in no report anywhere, and the volume is built with no Feats chapter over
    a clean-looking run. This asks the question from the catalogue's side, where the absence is.

    UNCAPPED AND NAMED. Every source is listed, because "13 unrecorded" tells a curator nothing
    about which thirteen, and binding them is a data question somebody has to actually do.
    """
    import glob
    root = records_dir or os.path.join(HERE, "data", "records")
    hosts = host_to_sources()
    out = {"bound": [], "pages": [], "doc": [], "unbound": [], "unknown": []}
    for q in sorted(glob.glob(os.path.join(root, "*.json"))):
        try:
            with open(q, encoding="utf-8") as f:
                src = json.load(f).get("source")
        except Exception:
            silence.note("feats_index.py:binding-report-record")
            continue
        if src:
            out.setdefault(source_binding(src, hosts), []).append(src)
    return {k: sorted(set(v)) for k, v in out.items()}


def audit():
    """Which feats records reach a source, and which are stranded.

    A stranded record is a mined deed no volume will ever print, so it is counted and named
    rather than left to be inferred from a smaller total.

    AND SO IS A RECORD THAT NEVER REACHED THE INDEX. `records` is `len(idx)`, which cannot see a
    file that would not parse or a record overwritten by a name collision -- both were dropped
    inside `load_index`, so each loss SHRANK the denominator and pushed the printed join rate up.
    `unreadable` and `collided` now ride beside `records`, and `files_seen` is the honest total
    the join rate should be read against. (order e16a93099bbe)
    """
    sys.path.insert(0, os.path.join(HERE, "src"))
    import pipeline as PL

    idx = load_index()
    h2s = host_to_sources()
    by_src = {}
    for _, rec in PL.records():
        by_src[rec["source"]] = {_norm(e.get("name")) for e in (rec.get("entries") or [])}

    # WITHIN-SOURCE CATALOGUE-ENTRY COLLISIONS, measured over the whole corpus rather than over
    # whatever `feats_for_source` happens to have been called with (order 04a3f79b7f55). See the
    # comment in `feats_for_source`: this is the same fold, computed here so `audit()` can report
    # it without depending on call order. Named uncapped, like `collided_keys` beside it -- a
    # count alone is not something a curator can act on.
    entry_collisions = []
    for _, rec in PL.records():
        seen_names = {}
        for e in (rec.get("entries") or []):
            k = _norm(e.get("name"))
            if k in seen_names:
                entry_collisions.append("%s | kept %r, dropped %r"
                                        % (rec["source"], seen_names[k], e.get("name")))
            else:
                seen_names[k] = e.get("name")

    joined, stranded = [], []
    for (host, ent_norm), rec in idx.items():
        srcs = [s for s in h2s.get(host, []) if ent_norm in by_src.get(s, set())]
        (joined if srcs else stranded).append((host, rec, srcs))
    faults = index_faults()
    return {
        "records": len(idx),
        "unreadable": faults["unreadable"],
        "unreadable_files": faults["unreadable_files"],
        "collided": faults["collided"],
        "collided_keys": faults["collided_keys"],
        # The SECOND collision class, the one that had no reporting at all (order 04a3f79b7f55).
        # Kept distinct from `collided` above: that one is two feats RECORDS folding onto one
        # index key, this one is two CATALOGUE ENTRIES of one source folding onto one name key.
        # Different losses, different remedies, so one number would serve neither.
        "entry_collisions": len(entry_collisions),
        "entry_collision_pairs": entry_collisions,
        "files_seen": len(idx) + faults["unreadable"] + faults["collided"],
        "joined": len(joined),
        "stranded": len(stranded),
        "feats_joined": sum(len(r.get("feats") or []) for _, r, _ in joined),
        "feats_stranded": sum(len(r.get("feats") or []) for _, r, _ in stranded),
        "stranded_hosts": collections.Counter(h for h, _, _ in stranded),
        "shared": sum(1 for _, _, s in joined if len(s) > 1),
    }


def main():
    a = audit()
    print("=" * 96)
    print("FEATS INDEX — can the mined deeds reach a volume?")
    print("=" * 96)
    print(f"\nfeats files on disk   : {a['files_seen']:,}")
    print(f"  in the index        : {a['records']:,}")
    print(f"  joined to a source  : {a['joined']:,}  ({a['feats_joined']:,} feats)")
    print(f"  STRANDED            : {a['stranded']:,}  ({a['feats_stranded']:,} feats)")
    # AGAINST THE FILES, NOT AGAINST THE SURVIVORS. Dividing by `records` let every unreadable
    # or collided file raise the rate by leaving the denominator, which is the reporting fault
    # order e16a93099bbe named. Both are printed whether or not they are zero, so a reader can
    # tell "none today" from "not measured".
    rate = 100.0 * a["joined"] / max(1, a["files_seen"])
    print(f"  join rate           : {rate:.1f}% of files on disk")
    print(f"  UNREADABLE records  : {a['unreadable']:,}  (skipped by load_index, not in the "
          f"index and not in the join rate above)")
    for f in a["unreadable_files"]:
        print(f"      {f}")
    print(f"  NAME COLLISIONS     : {a['collided']:,}  (two records folding onto one "
          f"(host, name) key; the later one wins)")
    for k in a["collided_keys"]:
        print(f"      {k}")
    # THE SECOND COLLISION CLASS, reported the way the first already was (order 04a3f79b7f55).
    # Uncapped and named, because a count of 992 tells a curator nothing about which pair to go
    # and look at. Distinguished in words from the row above it: no feat is lost here, the
    # dropped entry's own description and magnitude are.
    print(f"  ENTRY-NAME COLLISIONS: {a['entry_collisions']:,}  (two CATALOGUE ENTRIES of one "
          f"source folding onto one name key; the first one wins, and the second's description "
          f"and magnitude are what the feats prose will not see. No mined feat is lost.)")
    for k in a["entry_collision_pairs"]:
        print(f"      {k}")
    print(f"  entities catalogued in more than one source on the same host: {a['shared']:,}")
    # THE SOURCES THAT CANNOT REACH A FEATS CHAPTER AT ALL, asked from the catalogue's side.
    # See `binding_report`. `pages:`/`doc:` sources are correct by design and are named as such
    # rather than counted as a fault; the unrecorded ones are the worklist.
    b = binding_report()
    print("\nBINDING — can a source reach a wiki at all?")
    print(f"  bound to a wiki host : {len(b['bound']):,}")
    print(f"  owner-supplied pages : {len(b['pages']):,}  (correct by design -- no wiki exists)")
    print(f"  ingested documents   : {len(b['doc']):,}  (correct by design -- no wiki exists)")
    print(f"  NOT RECORDED         : {len(b['unbound']):,}  (feats_for_source answers [] for "
          f"these, which is indistinguishable downstream from 'this source has no attested "
          f"feats'. Binding them is a data question, not a code one.)")
    for src in b["unbound"]:
        print(f"      {src}")
    if b["unknown"]:
        print(f"  COULD NOT TELL       : {len(b['unknown']):,}  (WIKI_HOSTS.json would not read "
              f"on the second ask -- a fault about the FILE, never a verdict about the source)")
        for src in b["unknown"]:
            print(f"      {src}")
    if a["stranded_hosts"]:
        print("\nSTRANDED BY HOST — a mined deed no volume will print. The host below is the one")
        print("the RECORD states, not one derived from its directory name, so `NOT IN WIKI_HOSTS`")
        print("here really is an unbound host; `known host` is a catalogue with no matching entry:")
        for h, n in a["stranded_hosts"].most_common():
            known = "known host" if h in host_to_sources() else "NOT IN WIKI_HOSTS"
            print(f"   {h:<42}{n:>4} record(s)   {known}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
