"""CACHE KEY — one entity, one file, and a read that proves it before believing it.

THE BUG THIS EXISTS FOR (M23, owner-ruled "it must be done" 2026-08-25). Four modules built the
per-entity cache path independently, all the same way:

    re.sub(r"[^A-Za-z0-9]+", "_", name)[:80] + ".json"

Two collision sources ride in that one line. The sanitiser maps every run of punctuation to a
single underscore, so `Magic 8 Ball` and `Magic 8-Ball` become the same file; and the 80-char cap
folds any two names that agree on their first 80 characters. Verified live before the fix:
`data/feats/pixar_fandom_com/Magic_8_Ball.json` holds `entity: "Magic 8-Ball"`, so a reader
asking for `Magic 8 Ball` was handed the OTHER entity's mined feats and counted them as its own.
`coverage.measure()` then reported that borrowed evidence as CITED for both.

WHAT THE MEASUREMENT CHANGED ABOUT THE FIX. The ledger's framing was that re-keying "invalidates
every cache on disk and re-mines the corpus", which is why it sat open as a spend decision. It
does not. Measured across all 96,666 entities: **5 colliding key slots, 10 entities, 0.01% of
the corpus**, plus 59 entities sitting at the 80-char cap. And measured across all 86,288 cache
files on disk: **every one carries an `entity` key, and every one re-derives to its own
filename** -- so nothing is MIS-FILED. The corruption exists only at READ time, when a reader
asks for a name that sanitises onto a neighbour's file.

So the fix is not a re-key at all, and costs no re-mine:

  1. READS VERIFY. `load()` opens the file and compares the stored `entity` against the name that
     was asked for. A mismatch is a MISS, not a hit -- the caller re-mines that one entity. This
     is correct for collisions nobody has enumerated yet, including any future 80-char fold,
     which is why it is preferred over patching the five known pairs.
  2. WRITES DISAMBIGUATE. If an entity's natural path is already held by a DIFFERENT entity, the
     write goes to a suffixed sibling instead. Without this a colliding pair would overwrite each
     other forever, each re-mining on every pass -- correct, but perpetually expensive.
  3. ONE HELPER, NOT FOUR SPELLINGS. The path was built in `pipeline.py`, `coverage.py`,
     `feats.py` and `hostcheck.py`. The ledger named two of them. A rule applied at some of its
     sites is not applied (standing lesson 14), and four independent copies of one convention is
     four chances for the next edit to drift.

ON NOT CHANGING THE KEY ITSELF. The natural path is deliberately left byte-identical to what the
four sites already produced, so all 86,288 existing files stay live and no rename runs underneath
`read.py`, which writes into these directories continuously. The disambiguating suffix appears
only where a genuine collision is observed.
"""
import hashlib
import json
import os
import re

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# The sanitiser, kept EXACTLY as the four call sites spelled it. Changing it would rename every
# file on disk, which is the expensive migration this fix exists to avoid.
_SANITISE = re.compile(r"[^A-Za-z0-9]+")
HOST_CAP = 40
NAME_CAP = 80


def host_dir(host):
    """The per-host directory component."""
    return _SANITISE.sub("_", host or "")[:HOST_CAP]


def name_stem(name):
    """The per-entity filename stem, before `.json`. Lossy on purpose -- see `load()`."""
    return _SANITISE.sub("_", name or "")[:NAME_CAP]


def _suffix(name):
    """A short, stable digest of the EXACT name -- what the stem threw away."""
    return hashlib.sha1((name or "").encode("utf-8")).hexdigest()[:10]


def natural_path(base, host, name):
    """The path the four original call sites would have built. Unchanged, by design."""
    return os.path.join(base, host_dir(host), name_stem(name) + ".json")


def disambiguated_path(base, host, name):
    """Where an entity goes when its natural path belongs to a different entity."""
    return os.path.join(base, host_dir(host), name_stem(name) + "__" + _suffix(name) + ".json")


def candidate_paths(base, host, name):
    """Every path this entity's evidence could legitimately live at, natural first."""
    return [natural_path(base, host, name), disambiguated_path(base, host, name)]


def owns(doc, name):
    """Is this parsed cache document actually THIS entity's?

    The stored `entity` is the exact, unsanitised name, so it is the only field that can tell
    `Magic 8 Ball` from `Magic 8-Ball` once the filename has folded them together. Measured at
    fix time: all 86,288 files on disk carry it, so a missing key means a file this scheme did
    not write, and is not trusted.
    """
    return isinstance(doc, dict) and doc.get("entity") == name


def load(base, host, name, on_corrupt=None):
    """-> (doc, path) for this entity, or (None, None).

    A file that parses but belongs to another entity is a MISS, not a hit. That is the whole
    fix: the caller re-mines one entity instead of silently inheriting a neighbour's evidence.
    """
    for fp in candidate_paths(base, host, name):
        if not os.path.exists(fp):
            continue
        try:
            with open(fp, encoding="utf-8") as f:
                doc = json.load(f)
        except Exception:
            # A truncated file must be re-earned, never allowed to masquerade as evidence.
            if on_corrupt:
                on_corrupt(fp)
            continue
        if owns(doc, name):
            return doc, fp
    return None, None


def text_digest(text_map):
    """A digest over the page text an evidence record was mined FROM.

    THE in-toto IDEA, WITHOUT THE ECOSYSTEM. in-toto's link metadata records the MATERIALS a step
    read and the PRODUCTS it wrote, each by digest, so a later reader can prove an output came
    from the inputs it claims. That property is worth having; the tooling is not -- in-toto needs
    its own library and a key-management story, and sigstore needs a network call to a
    transparency-log service. Neither earns a dependency to answer "did this evidence come from
    that page".

    Applied where this project actually HAS inputs: not files on disk, but the fetched page text
    an entity's feats were extracted from. It composes with the writer stamps already on records
    -- the stamp says WHO wrote a file, this says WHAT it was written FROM.

    (A file-path variant was written first and deleted the same hour: it had no caller, and this
    project's own liveness ratchet flagged it within minutes. Forward-looking API is dead code
    wearing a plan.)
    """
    import hashlib
    per = {}
    for title, body in (text_map or {}).items():
        per[str(title)] = hashlib.sha1((body or "").encode("utf-8")).hexdigest()[:16]
    roll = hashlib.sha1(
        "\n".join("%s=%s" % (k, v) for k, v in sorted(per.items())).encode("utf-8")
    ).hexdigest()[:16]
    return {"pages": per, "roll": roll, "n": len(per)}


def provenance_ok(recorded, text_map):
    """-> (ok, changed). Does this evidence still match the text it was mined from?

    THREE OUTCOMES, and the middle one is the reason this exists:
        True   the pages still hash to what was recorded -- the evidence is PROVEN
        False  the source text changed since mining -- the citation is not wrong retroactively,
               but it is no longer proven, and those are different states
        None   nothing was recorded -- UNVERIFIABLE, which must never be reported as verified

    That third case is the whole discipline. `coverage` learned the same lesson today: "nobody
    asked" and "asked and found nothing" were one number for months.
    """
    if not isinstance(recorded, dict) or not recorded.get("pages"):
        return None, []
    now = text_digest(text_map)
    changed = [k for k, v in (recorded.get("pages") or {}).items()
               if now["pages"].get(k) != v]
    return (not changed), changed


def write_path(base, host, name):
    """Where this entity's evidence should be written.

    The natural path unless a DIFFERENT entity already holds it, in which case the suffixed
    sibling. Without this branch a colliding pair overwrites each other on every pass.
    """
    nat = natural_path(base, host, name)
    if not os.path.exists(nat):
        return nat
    try:
        with open(nat, encoding="utf-8") as f:
            doc = json.load(f)
    except Exception:
        return nat            # unreadable: this entity may as well re-earn the slot
    if owns(doc, name):
        return nat
    return disambiguated_path(base, host, name)
