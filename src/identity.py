#!/usr/bin/env python3
"""
IDENTITY — who a record is about, when an entity is more than one entity.

THE OWNER'S RULING
------------------
    "each continuity in marvel and dc should be their own, not resolved into one,
     it's timelines not retcons"
    "the same should be for DragonBall and any other thing that has multiple timelines"

This is a claim about the world, and it decides how the library must be built. A retcon says
the earlier account was WRONG and the later one replaces it; there is one entity and one true
history, and the archive's job is to keep the current version. A timeline says both accounts
happened, in different branches; there are TWO entities and two histories, and the archive's job
is to keep both and never merge them.

The Panscriptum takes the second reading, which means Kal-El (New Earth) and Kal-El (Prime
Earth) are two accessions, assayed separately, shelved separately, and never averaged. An
average across continuities is not a summary of anything -- it is a number describing a being
that no source ever recorded.

WHY THIS ALSO FIXES THE CHAIN
-----------------------------
Phase 4 builds a comparison graph from recorded defeats and fits Bradley-Terry to it. It found
two MUTUAL pairs -- A beats B and B beats A -- and a mutual pair is either a genuine split
decision or a category error. Both of ours were category errors of exactly this kind:

    Goku loses to Mercenary Tao.
    Goku beats Mercenary Tao "after training with Korin".

Those are not one entity with an inconsistent record. They are two states of one entity across
its own history, and collapsing them manufactures a contradiction the sources never contained.
Continuity is the coarse case of this problem; EPOCH is the fine case, and both are the same
error: an identity that omits a coordinate the evidence depends on.

HOW A CONTINUITY IS RECOGNISED, WITHOUT A HARDCODED LIST
--------------------------------------------------------
Fandom titles carry a parenthetical: `Anthony Stark (Earth-616)`, `Wally West (New Earth)`,
`Goku (Xenoverse 2)` -- but also `Ki (ability)`, `Kaio-ken (Tom Keenlyside)`. A list of known
continuity names would need maintaining per franchise forever and would silently miss every
source added after it was written, which is this project's signature failure.

Three structural tests do it instead, and none of them names a franchise.

    ORTHOGRAPHY   a continuity is a proper name -- a work, a world, a broadcast line -- and
                  Fandom writes its own metadata lowercase. `(Filmation)` against `(character)`,
                  `(Lostbelt)` against `(operator)`. One test, every wiki, no maintenance.

    POPULATION    a designator worn by several distinct base names is a place characters live
                  in. `G1` carries 48 bearers; `Tom Keenlyside` carries one, because it is a
                  voice actor's credit.

    BRANCHING     a designator most of whose bearers ALSO appear under another designator is
                  describing a branch, since that is what a branch is: the same names occurring
                  twice. This catches a young continuity with only two characters written up.

Population is sufficient but not necessary and branching is sufficient but not necessary --
`(Revelation)` shares no bearers yet and is obviously a continuity, while `(Fates)` has one
bearer and is obviously a continuity because that bearer exists in three other branches. Either
alone admits it. Add a franchise tomorrow and its continuities are recognised the same day,
because the evidence for what they are is in the titles themselves.

A short NEVER list handles what survives all three: capitalised words that are still the wiki
describing its own furniture (`Skill`, `Multiplayer`, `Codex Entry`). Every entry there was
observed as a false positive first, which is the only warrant it accepts.

WHAT THIS DELIBERATELY DOES NOT DO
----------------------------------
It does not guess an epoch for every entity. Epoch resolution costs a model call per sentence and
almost every sentence needs none: an entity whose record contains no contradiction gains nothing
from being split in time. So epoch is resolved WHERE THE CONTRADICTION IS -- `adjudicate()` takes
the mutual pairs the chain actually found and asks only about those. Two model calls, not eleven
thousand.
"""
import argparse
import collections
import glob
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import silence                                                          # noqa: E402

_BAD_CHARS = (chr(8), chr(11), chr(12), chr(7))
if any(c in open(os.path.abspath(__file__), encoding="utf-8").read() for c in _BAD_CHARS):
    raise SystemExit(__file__ + ": a regex escape was eaten in transit.")

CACHE = os.path.join(HERE, "data", "DESIGNATORS.json")

# A designator worn by at least this many DISTINCT base names is a continuity rather than a
# disambiguation of one particular thing. Three is deliberately low: a small wiki's alternate
# timeline may only have a handful of characters written up, and excluding it would silently
# merge it into the main line -- the exact error this module exists to prevent. The cost of the
# opposite mistake is only that two records stay separate that could have been one, which is
# recoverable; a wrong merge is not.
MIN_BEARERS = 3

# Parentheticals that are never a continuity however many bearers they have. These are the
# wiki's own metadata vocabulary, not places in the omniverse. Kept short on purpose -- the
# bearer-count rule does nearly all the work, and every entry here is a hardcoded list of the
# kind this module argues against, so each one has to earn itself.
NEVER = {
    "disambiguation", "character", "ability", "object", "location", "episode", "film", "movie",
    "novel", "comics", "video game", "game", "song", "album", "term", "concept", "species",
    "race", "item", "weapon", "technique", "move", "attack", "organization", "organisation",
    "event", "manga", "anime", "series", "position", "title", "rank", "good", "evil",
    # Capitalised on the wiki but still the wiki describing its own furniture rather than a
    # branch of the world. Every entry here was observed as a false positive in the inventory,
    # which is the only warrant this list accepts.
    "skill", "mission", "multiplayer", "singleplayer", "codex entry", "co-op level", "level",
    "map", "achievement", "trophy", "quest", "class", "stat", "perk", "faction", "unit",
}

_PAREN = re.compile(r"^(.*?)\s*\(([^()]+)\)$")


def split(title):
    """`Anthony Stark (Earth-616)` -> `('Anthony Stark', 'Earth-616')`."""
    m = _PAREN.match((title or "").strip())
    if not m:
        return (title or "").strip(), None
    return m.group(1).strip(), m.group(2).strip()


# --------------------------------------------------------------------------- the inventory

def _titles(host_dir):
    """Every resolved wiki title in one host's feats cache."""
    out = []
    for fp in glob.glob(os.path.join(host_dir, "*.json")):
        try:
            with open(fp, encoding="utf-8") as f:
                d = json.load(f)
        except Exception:
            silence.note("identity.py:_titles")
            continue
        for pg in (d.get("pages_read") or d.get("pages") or []):
            t = pg.get("title") if isinstance(pg, dict) else pg
            if t:
                out.append(str(t))
    return out


def mine(root=None):
    """Build the designator inventory from the cache.

    Returns `{host: {designator: {"bearers": n, "shared": n}}}`, where SHARED counts the bearers
    that also appear under some other designator or bare. Shared is the branch signature: the
    reason `Kal-El` reads as a continuity split and `Kaio-ken (Tom Keenlyside)` does not is that
    Kal-El exists in more than one branch and the voice actor's credit exists in exactly one.

    Uses every title present -- no sampling. A designator that only appears in the tail of a
    host's cache is exactly the alternate timeline most at risk of being merged away.
    """
    root = root or os.path.join(HERE, "data", "feats")
    inv = {}
    for host in sorted(os.listdir(root)) if os.path.isdir(root) else []:
        hd = os.path.join(root, host)
        if not os.path.isdir(hd):
            continue
        bearers = collections.defaultdict(set)
        seen = collections.defaultdict(set)
        for t in _titles(hd):
            base, desig = split(t)
            if not base:
                continue
            seen[base].add(desig)          # None means the bare title was also mined
            if desig:
                bearers[desig].add(base)
        if bearers:
            inv[host] = {d: {"bearers": len(b),
                             "shared": sum(1 for x in b if len(seen[x]) > 1)}
                         for d, b in bearers.items()}
    return inv


def _is_continuity(desig, stat):
    """Is this parenthetical a branch of the world, or the wiki talking about itself?

    Three tests, none of them a franchise list:

    ORTHOGRAPHY. A continuity is a proper name -- a work, a world, a broadcast line. Fandom's
    own metadata vocabulary is lowercase by convention: `(ability)`, `(location)`, `(operator)`,
    `(character)`. The initial capital separates `(Filmation)` from `(character)` on every wiki
    at once, for free, forever.

    BRANCHING. A designator most of whose bearers ALSO exist under another designator is
    describing a branch, because that is what a branch is: the same names occurring twice.

    POPULATION. A designator worn by several distinct names is a place many characters live in,
    even when the cache has not yet mined their counterparts elsewhere. `(Revelation)` shares no
    bearers yet and is still plainly a continuity, so branching cannot be required -- only
    sufficient.

    BRANCHING AT n == 1. `(Fates)` has one bearer and is obviously a continuity because that
    bearer exists in three other branches -- population alone would never admit it, so a bare
    `n >= 2` guard here would make branching require what population is supposed to cover for
    it. A single shared bearer is `shared >= 1` at n == 1, and is handled as its own case rather
    than folded into the general majority test below, whose `n >= 2` shape does not extend to
    n == 1 without dividing by a majority of one.
    """
    d = (desig or "").strip()
    if not d or d.lower() in NEVER:
        return False
    if d[0].islower():
        return False
    n = stat["bearers"] if isinstance(stat, dict) else stat
    shared = stat.get("shared", 0) if isinstance(stat, dict) else 0
    if n >= MIN_BEARERS:
        return True
    if n == 1:
        return shared >= 1
    return n >= 2 and shared >= max(2, 0.5 * n)


def load(refresh=False):
    if not refresh and os.path.exists(CACHE):
        try:
            with open(CACHE, encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            silence.note("identity.py:load")
    inv = mine()
    # silence.write_json, not a hand-rolled tmp + json.dump + replace_retry (order 92a07b4ba203):
    # the old tmp name carried no pid/thread, so two concurrent --refresh runs shared one temp
    # path, and the write's verdict was discarded -- `load()` returned the fresh inventory
    # whether or not it actually reached disk. write_json fixes both.
    silence.write_json(CACHE, inv, indent=1, sort_keys=True)
    return inv


def continuities(host, inv=None):
    """The designators on this host that behave like continuities."""
    inv = inv if inv is not None else load()
    key = host.replace(".", "_").replace("-", "_")
    counts = inv.get(key) or inv.get(host) or {}
    return {d: (v["bearers"] if isinstance(v, dict) else v)
            for d, v in counts.items() if _is_continuity(d, v)}


# --------------------------------------------------------------------------- the identity

def identify(title, host, inv=None):
    """Return `(base, continuity)` for a resolved wiki title.

    `continuity` is None when the title carries no continuity marker, which is the ordinary case
    for a single-timeline source. None is a real answer here and means "this source records one
    history", not "we failed to find one" -- the distinction the rest of this project keeps
    losing.
    """
    base, desig = split(title)
    if not desig:
        return base, None
    return (base, desig) if desig in continuities(host, inv) else (base, None)


def node(base, continuity=None, epoch=None):
    """The canonical comparison-graph node.

    Every coordinate the evidence depends on goes in the key, and nothing else does. Two records
    share a node only when they are about the same being in the same branch at the same point in
    its own history.
    """
    out = base
    if continuity:
        out += f" @{continuity}"
    if epoch:
        out += f" #{epoch}"
    return out


# --------------------------------------------------------------------------- epoch, on demand

EPOCH_SYSTEM = """You read one sentence from a fiction wiki and report WHEN it happened in the
subject's own history.

Return JSON only:
  {"epoch": "<short phrase>", "explicit": true|false}

RULES
- "epoch" names the point in the subject's own timeline the sentence places the event: a story
  arc, a saga, a training period, a transformation state, an age. Six words at most.
- "explicit" is true only if the SENTENCE ITSELF carries the marker ("after training with
  Korin", "during the Cell Games", "as a child"). If you are inferring from background
  knowledge, "explicit" is false.
- If the sentence carries no marker at all, return {"epoch": "", "explicit": false}. An absent
  marker is a real answer. Do not guess one."""


EPOCH_SCHEMA = {
    "type": "object",
    "properties": {"epoch": {"type": "string"}, "explicit": {"type": "boolean"}},
    "required": ["epoch", "explicit"],
}


def _ask(prompt, system=EPOCH_SYSTEM):
    try:
        import read as R
        R.ensure_transport(verbose=False)
        return R._ask(R.config(), system, prompt, EPOCH_SCHEMA)
    except Exception:
        silence.note("identity.py:_ask")
        return None


def _json(raw):
    """The transport already returns a parsed object when the schema holds; tolerate a string."""
    if isinstance(raw, dict):
        return raw
    m = re.search("[{].*[}]", raw or "", re.S)
    if not m:
        return {}
    try:
        return json.loads(m.group(0))
    except Exception:
        silence.note("identity.py:_json")
        return {}


class ProbeUnavailable(RuntimeError):
    """The epoch probe never ran. This is not the same claim as "the sentence names no epoch"."""


def epoch_of(sentence, strict=False):
    """The epoch a single sentence places itself in, or "" when it names none.

    TWO DIFFERENT ANSWERS USED TO ARRIVE AS THE SAME EMPTY STRING, and the system prompt above
    is emphatic about which one it means: "If the sentence carries no marker at all, return
    {"epoch": "", "explicit": false}. An absent marker is a real answer. Do not guess one."
    `chain.adjudicate_mutuals()` reads it the same way and prints "neither sentence dates itself"
    on the strength of it -- then records the pair as a genuine disagreement in the record and
    hands it to Bradley-Terry.

    But `_ask()` swallows every exception and returns None -- the transport down,
    `read.ensure_transport` failing, a response that will not parse -- and `_json(None)` is `{}`,
    whose `explicit` is falsy, which is the same `""`. So "the model read this sentence and found
    no epoch marker in it" and "nothing ever asked" were indistinguishable to every caller, and
    the second one was being reported as the first. A run with no transport at all would report
    every mutual pair as a settled genuine disagreement, unanimously, and look like a clean run.

    `strict=True` refuses to answer instead of guessing, per the fail-closed rule: a layer that
    does not know must not authorise. It is an ADDITIVE keyword with the old behaviour as the
    default so no existing caller changes; `chain.py:422` is the caller that should pass it, and
    that is filed as a cross-module change in handoff/run36/crossmodule_batch04.md rather than
    edited here, because chain.py belongs to another agent this shift.
    """
    raw = _ask(sentence.strip()[:1200])
    d = _json(raw) if raw is not None else None
    if not d:
        # UNPROBED, not unmarked. Both arms land here: no transport (raw is None) and a reply
        # that would not parse (`_json` -> {}). Neither is evidence about the sentence.
        silence.note("identity.py:epoch-unprobed")
        if strict:
            raise ProbeUnavailable(
                "the epoch probe did not run for this sentence, so its epoch is UNKNOWN rather "
                "than absent; treating it as absent would date a record from a failed call")
        return ""
    if not d.get("explicit"):
        return ""
    return str(d.get("epoch") or "").strip()[:60]


# `adjudicate(edges)` (mutual-pair time-splitting over `winner`/`loser` edges) lived here and
# was deleted 2026-08-23 maintenance run #2, one cycle after being flagged dead in run #1's
# audit: superseded by `chain.adjudicate_mutuals()`, nothing called it, and nothing anywhere in
# src/ ever read the `winner_epoch` field it wrote (both re-verified by grep immediately before
# deletion). `epoch_of()` above it is still live -- `chain.py:381` calls it directly -- so it
# stays.


# ---------------------------------------------------------------- epoch-mandatory sources
#
# OWNER RULING, 2026-08-23: "mtg and dnd need epoch markings like come on." Correct, and for a
# reason the fictions themselves state: these franchises draw their POWER BOUNDARIES in time
# rather than in branches. Marvel splits into Earths; Magic splits at the MENDING -- an
# oldwalker (Urza, pre-Mending) and a neowalker (Jace) are different power classes wearing one
# card type, and a sheet that does not say which it measured is a measurement of an unspecified
# subject. The Forgotten Realms redraw everyone's capabilities at each era boundary: the Time
# of Troubles, the Spellplague, the Second Sundering.
#
# For these hosts an assay WITHOUT an epoch is refused, not published unstamped. The eras below
# are the recognised coarse markers; a finer state ("Living Guildpact of Ravnica", "compleated
# by Phyrexia") is better still and always accepted.
#
# MOVED ABOVE `if __name__ == "__main__"` (order 3c86a8d541b2): this block used to sit after
# that guard, so `EPOCH_REQUIRED`, `epoch_directive()` and `epoch_acceptable()` did not exist
# yet in a process that runs this module directly (`python src/identity.py`) -- only in one
# that imports it. Latent because `main()` never calls them and every real caller imports the
# module, but the owner-ruled epoch mandate should not depend on how the module was invoked.
EPOCH_REQUIRED = {
    "mtg.fandom.com": {
        "eras": ["pre-Mending", "post-Mending"],
        "note": ("Magic's power history splits at THE MENDING. Say which side this state is "
                 "on, and name the storyline state when the page centres one -- 'Living "
                 "Guildpact of Ravnica', 'Gatewatch era', 'compleated by Phyrexia'."),
    },
    "forgottenrealms.fandom.com": {
        "eras": ["pre-Time of Troubles", "post-Time of Troubles", "Spellplague era",
                 "post-Second Sundering"],
        "note": ("The Realms redraw capability at era boundaries. Fix the era the cited feats "
                 "belong to; an edition marker (1e-5e) also serves."),
    },
}


def epoch_directive(host):
    """The prompt block that makes an epoch mandatory for this host, or None."""
    spec = EPOCH_REQUIRED.get(host)
    if not spec:
        return None
    return ("EPOCH IS MANDATORY FOR THIS SOURCE. " + spec["note"]
            + " Recognised coarse eras: " + ", ".join(spec["eras"])
            + ". Score ONLY feats belonging to the one epoch you name; an answer with no "
              "epoch, or 'unstamped', is refused.")


def epoch_acceptable(host, epoch):
    """Is this epoch tag good enough to publish for this host?"""
    if host not in EPOCH_REQUIRED:
        return True
    e = (epoch or "").strip().lower()
    return bool(e) and e not in ("unstamped", "unknown", "n/a", "none", "current", "modern")


# --------------------------------------------------------------------------- CLI

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--refresh", action="store_true", help="re-mine the designator inventory")
    ap.add_argument("--host", help="report one host in detail")
    a = ap.parse_args()

    inv = load(refresh=a.refresh)
    if a.host:
        key = a.host.replace(".", "_").replace("-", "_")
        counts = inv.get(key, {})
        cont = continuities(a.host, inv)
        print(f"{a.host}: {len(counts)} distinct parentheticals, "
              f"{len(cont)} behave like continuities\n")
        rows = sorted(counts.items(),
                      key=lambda kv: -(kv[1]["bearers"] if isinstance(kv[1], dict) else kv[1]))
        for d, v in rows:
            n = v["bearers"] if isinstance(v, dict) else v
            sh = v.get("shared", 0) if isinstance(v, dict) else 0
            mark = "CONTINUITY" if d in cont else "disambiguator"
            print(f"   {n:>6} bearers  {sh:>5} shared  {mark:<14}{d}")
        return 0

    print("=" * 78)
    print("CONTINUITY INVENTORY — mined from resolved titles, no hardcoded franchise list")
    print("=" * 78)
    rows = []
    for host in sorted(inv):
        cont = continuities(host, inv)
        if cont:
            rows.append((host, cont))
    for host, cont in sorted(rows, key=lambda kv: -len(kv[1])):
        top = sorted(cont.items(), key=lambda kv: -kv[1])
        names = ", ".join(f"{d} ({n})" for d, n in top[:6])
        more = f" +{len(top) - 6} more" if len(top) > 6 else ""
        print(f"\n  {host}  — {len(cont)} continuities")
        print(f"     {names}{more}")
    if not rows:
        print("\n  no continuity designators found yet — the feats cache is still filling.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
