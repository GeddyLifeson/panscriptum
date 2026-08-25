"""ENTITY MATCH — near-miss name resolution that cannot merge two continuities.

WHAT THIS IS FOR. `feats_index._norm` folds a name to its alphanumeric core and compares for
EQUALITY. That is exact, fast, correct, and it accounts for 98.6% of the join -- but a name
that differs by one character, a stray article, or a reordered surname simply does not join,
and the mined evidence attached to it is never printed by any volume. This module is the
second pass: for names that found no exact fold, it RANKS plausible catalogue entries and says
why, so a human or a later automated pass can act on a list instead of on silence.

IT PROPOSES. IT DOES NOT MERGE. Every function here returns candidates with scores and a
reason; nothing in this file mutates the catalogue or the join. That is deliberate -- see the
next section for what happens when this kind of code is allowed to decide.

THE TRAP THIS MODULE IS BUILT AROUND, and it is the whole design constraint
----------------------------------------------------------------------------
Three DC records strand on hosts that ARE bound: `Wally West (New Earth)`, `Wally West (Prime
Earth)`, and the catalogue's own `Wally West (Earth-16)`. They carry 240 mined deeds between
them -- the majority of all stranded evidence -- and the obvious repair is to strip the
parenthetical so they fold together. That repair is WRONG. They are three separate continuities
and folding them attaches 177 deeds to the wrong one. `verify_math` §19o exists to fail if
anyone loosens `_norm` to do it, and this module must not become a way around that check.

So the rule here is absolute and is enforced by `qualifier_compatible()`:

    A parenthetical qualifier must match, or be absent from BOTH names. "Match" means
    identical after `feats_index._norm` -- case, spacing and punctuation are folded, so
    "(Earth-2)" and "(Earth 2)" ARE the same continuity, while "(New Earth)" and
    "(Prime Earth)" are not. This paragraph said "EXACTLY" until 2026-08-24 and the code
    never did that: it has always compared normalised forms, exactly as verify_math §19r
    describes it ("identical qualifiers DO match, modulo case and spacing"). The gate is
    absolute in the sense that matters -- a qualifier conflict is never overruled by a
    similarity score -- but it is not literal string equality.
    A name with a qualifier never matches a name with a different one.
    A name with a qualifier never matches a bare name.

Fuzzy scoring is applied ONLY to the base name, and only after that gate passes. This means
`Wally West (New Earth)` vs `Wally West (Prime Earth)` scores nothing at all, no matter how
similar the strings are -- which is the correct answer and the reason a pure string-similarity
or pure embedding approach is unsafe for this corpus. An embedding would rate those two nearly
identical, which is exactly backwards.

WHY NO EMBEDDINGS BY DEFAULT
----------------------------
An embedding backend is supported (see `embed_available`) and is OFF unless a model is
installed and it is asked for. Two measured reasons, 2026-08-24. First, this machine has
exactly ONE Ollama model installed and no embedding model at all, so the feature would be a
promise the machine cannot keep. Second, and more important: embedding 85,968 catalogue names
is thousands of calls against the single GPU that is already this project's bottleneck -- the
same card whose contention `gpu_lane` was just written to arbitrate. Spending it to improve a
join that is already at 98.6% is the wrong trade until the exact pass is exhausted. The
fallback shape is borrowed from `aisling_companion/embeddings.py`, which degrades to plain
matching when its model is missing rather than failing.

REASON CODES, NOT SILENT NULLS
------------------------------
Borrowed from `SAM/betting_suite/fetch.py` and `rent_engine/core/property_key.py`, both of
which learned the same lesson this project keeps relearning: a function that returns `[]` for
"failed" and `[]` for "genuinely nothing" has destroyed the distinction its caller needs. Every
unresolved name here comes back with a `MatchReason` naming WHY, so "what did not join and what
kind of problem is it" stays a queryable list rather than an absence.
"""
import difflib
import os
import re
import sys
from collections import Counter

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import feats_index  # noqa: E402


# --------------------------------------------------------------------------- reason codes

class MatchReason:
    """Why a name did not resolve. Never a bare None -- see the module header."""

    EXACT = "exact"                       # folded identically; no fuzzy pass needed
    STRONG = "strong"                     # base names very close, qualifiers compatible
    WEAK = "weak"                         # plausible, below the accept bar; for human eyes
    QUALIFIER_CONFLICT = "qualifier-conflict"   # same base, DIFFERENT continuity/disambiguator
    QUALIFIER_MISSING = "qualifier-missing"     # one side disambiguated, the other bare
    NO_CANDIDATE = "no-candidate"         # nothing in the pool is close on the base name
    EMPTY_NAME = "empty-name"             # the record carries no usable name at all
    NO_POOL = "no-pool"                   # the source has no catalogue entries to match against


# A qualifier is the parenthetical the wikis use to separate continuities, versions and
# homonyms: "(New Earth)", "(Earth-16)", "(Zanpakutou spirit)", "(2003 series)".
_QUAL = re.compile(r"\(([^()]*)\)\s*$")


def split_qualifier(name):
    """-> (base, qualifier or None). Only a TRAILING parenthetical counts as a qualifier.

    Mid-name parentheses are part of the name as written ("Nick Fury (LMD) Prime" is not a
    thing anyone catalogues, but "Agent (Ret.) Coulson" style constructions do occur), and
    treating them as disambiguators would start folding names that are genuinely distinct.
    """
    s = (name or "").strip()
    m = _QUAL.search(s)
    if not m:
        return s, None
    return s[:m.start()].strip(), m.group(1).strip()


def qualifier_compatible(a, b):
    """THE GATE. Two names may only be compared if their qualifiers agree.

    Agreement is equality of `feats_index._norm(qualifier)`, NOT literal string equality:
    "(Earth-2)" and "(Earth 2)" agree; "(New Earth)" and "(Prime Earth)" do not. See the
    module header -- the word "exactly" used to appear here and described behaviour this
    function has never had.

    Returns (ok, reason). See the module header for why this is absolute rather than scored:
    the three Wally West continuities are why §19o exists, and a similarity score cannot be
    allowed to overrule a continuity marker no matter how high it is.
    """
    _, qa = split_qualifier(a)
    _, qb = split_qualifier(b)
    if qa is None and qb is None:
        return True, None
    if qa is not None and qb is not None:
        if feats_index._norm(qa) == feats_index._norm(qb):
            return True, None
        return False, MatchReason.QUALIFIER_CONFLICT
    return False, MatchReason.QUALIFIER_MISSING


# --------------------------------------------------------------------------- similarity

def _bigrams(s):
    return Counter(s[i:i + 2] for i in range(len(s) - 1)) if len(s) > 1 else Counter([s])


def _dice(a, b):
    """Sorensen-Dice over character bigrams. Stdlib, deterministic, no dependency.

    Chosen over a plain edit ratio because it is robust to word order -- "Kratos of Sparta"
    against "Sparta's Kratos" scores well, while an edit distance punishes the transposition
    as heavily as a misspelling.
    """
    if not a or not b:
        return 0.0
    ca, cb = _bigrams(a), _bigrams(b)
    overlap = sum((ca & cb).values())
    total = sum(ca.values()) + sum(cb.values())
    return (2.0 * overlap / total) if total else 0.0


def similarity(a, b):
    """Base-name similarity in [0,1]. Qualifiers are NOT considered -- the gate handles those.

    The two measures disagree in useful ways (Dice is order-tolerant, SequenceMatcher is
    contiguity-sensitive), so the score is the higher of the two: a name should not be punished
    for the weakness of whichever single measure suits it least.

    DO NOT SWAP `difflib` FOR `rapidfuzz` HERE. It looks like an obvious free win -- rapidfuzz
    is installed, it is a compiled library, and it was measured at **6.3x faster** on 6,000 real
    name pairs from CHARACTER_SWEEP. It is not a drop-in, and the measurement is the reason:

        pairs compared            6,000
        disagreements > 1e-9      1,618   (27% of all pairs)
        worst delta               0.345

    `rapidfuzz.distance.Indel.normalized_similarity` computes an OPTIMAL alignment.
    `difflib.SequenceMatcher.ratio` does not -- it is a greedy longest-matching-block recursion,
    which is a genuinely different (and weaker) measure, not an approximation of the same one.
    Substituting it would silently re-tune STRONG (0.90) and WEAK (0.72) against a metric they
    were never calibrated on, and it would do so on more than a quarter of all comparisons,
    without a single test going red. Measured and rejected 2026-08-25.

    If the speed is ever actually needed, the honest route is to adopt the new metric openly,
    re-derive both thresholds against it, and diff every affected match before and after.
    """
    na, nb = feats_index._norm(a), feats_index._norm(b)
    if not na or not nb:
        return 0.0
    if na == nb:
        return 1.0
    return max(_dice(na, nb), difflib.SequenceMatcher(None, na, nb).ratio())


# Above this, the base names are close enough that a human would call it the same name.
STRONG = 0.90
# Below this, it is noise. Between the two is a reviewable middle.
WEAK = 0.72


# --------------------------------------------------------------------------- the match

def candidates(name, pool, limit=None):
    """Rank every compatible catalogue entry for `name`.

    `pool` is an iterable of catalogue entry dicts (or plain name strings). Returns a list of
    {name, score, reason} sorted best-first, plus the reason the BEST one is what it is.

    NO CAP BY DEFAULT (Hard Rule 0). `limit` exists for an interactive caller that genuinely
    wants the head of the list on screen; every programmatic consumer must leave it None, and
    a truncated result is flagged so it can never be mistaken for the whole set.
    """
    names = []
    for e in (pool or []):
        n = e if isinstance(e, str) else (e or {}).get("name")
        if n:
            names.append(n)

    # ONE RETURN SHAPE, ALWAYS. These two early exits omitted `blocked_by_qualifier` while the
    # normal path below always carries it, so a caller reading that key unconditionally would
    # KeyError on an empty name or an empty pool -- the two inputs most likely to arrive from
    # real data. Latent today only because nothing calls this module yet (see the header), and
    # the cheapest possible moment to fix a contract is before it has callers.
    if not (name or "").strip():
        return {"query": name, "reason": MatchReason.EMPTY_NAME, "matches": [],
                "truncated": False, "considered": len(names), "blocked_by_qualifier": []}
    if not names:
        return {"query": name, "reason": MatchReason.NO_POOL, "matches": [],
                "truncated": False, "considered": 0, "blocked_by_qualifier": []}

    rejected = Counter()
    scored = []
    for cand in names:
        ok, why = qualifier_compatible(name, cand)
        if not ok:
            # Only count a rejection when the BASE names are actually close; otherwise every
            # unrelated entry in the source inflates the qualifier-conflict tally and the
            # diagnostic stops meaning anything.
            base_a, _ = split_qualifier(name)
            base_b, _ = split_qualifier(cand)
            if similarity(base_a, base_b) >= WEAK:
                rejected[why] += 1
            continue
        s = similarity(split_qualifier(name)[0], split_qualifier(cand)[0])
        if s >= WEAK:
            scored.append({"name": cand, "score": round(s, 4),
                           "reason": (MatchReason.EXACT if s >= 1.0 else
                                      MatchReason.STRONG if s >= STRONG else
                                      MatchReason.WEAK)})

    # Deterministic: score descending, then name ascending. Never hash order -- a listing the
    # reader or a later pass navigates by must not move between runs (the §19n lesson).
    scored.sort(key=lambda r: (-r["score"], r["name"]))

    truncated = False
    if limit is not None and len(scored) > limit:
        scored, truncated = scored[:limit], True

    if scored:
        reason = scored[0]["reason"]
    elif rejected:
        reason = rejected.most_common(1)[0][0]
    else:
        reason = MatchReason.NO_CANDIDATE

    return {"query": name, "reason": reason, "matches": scored,
            "truncated": truncated, "considered": len(names),
            "blocked_by_qualifier": dict(rejected)}


def best(name, pool):
    """The single best STRONG-or-better match, or None with a reason.

    Returns (match_or_None, reason). A WEAK hit deliberately returns None: this module's job is
    to stop silence, not to start guessing, and a weak match applied automatically is how a
    deed gets attached to the wrong entity.
    """
    r = candidates(name, pool)
    top = r["matches"][0] if r["matches"] else None
    if top and top["score"] >= STRONG:
        return top, top["reason"]
    return None, r["reason"]


# --------------------------------------------------------------------------- optional backend

def embed_available(host=None):
    """Is a local embedding model installed? Absent by default on this machine.

    Reported rather than assumed: `aisling_companion/embeddings.py`'s pattern, where a missing
    model degrades to plain matching instead of raising. Nothing in this module calls it yet --
    it is the seam for an embedding pass, and it stays shut until an embedding model exists AND
    the exact join has been exhausted. See the module header for why that order matters.
    """
    import json
    import urllib.request
    host = host or os.environ.get("OLLAMA_HOST", "http://localhost:11434")
    try:
        with urllib.request.urlopen(host.rstrip("/") + "/api/tags", timeout=10) as r:
            tags = json.loads(r.read().decode("utf-8", "replace"))
    except Exception:
        return {"available": False, "reason": "ollama unreachable", "models": []}
    names = [m.get("name") or "" for m in tags.get("models", [])]
    embed = [n for n in names if "embed" in n.lower() or "bge" in n.lower()]
    return {"available": bool(embed), "models": embed,
            "reason": None if embed else "no embedding model installed "
                                         "(`ollama pull nomic-embed-text` would provide one)"}
