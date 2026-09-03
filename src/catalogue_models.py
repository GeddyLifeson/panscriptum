#!/usr/bin/env python3
"""
CATALOGUE MODELS — ask each provider what it actually serves, instead of trusting the config.

THE FINDING THAT PROMPTED IT
---------------------------
    "what about all of the other fucking models, like if its rate limited we should have a
     fail-safe to switch to a different model then"

The failover works: a declined call claims a different bucket, seven times, before anything
falls to the GPU. The pool is small for a different reason, and probing every disabled model
that holds a key found it:

    cerebras    "Model zai-glm-4.7 is archived and unavailable for the organization"
    nvidia      410  "qwen/qwen3-coder-480b-a35b-instruct has reached its end of life"
    sambanova   "The requested model (DeepSeek-V3-0324) is not available"
    github      410  "GitHub Models is temporarily unavailable as part of a retirement brownout"
    groq        404  "The model llama-3.3-70b-versatile does not exist"

**The keys work. The model NAMES are stale.** Providers retire and rename models constantly, and
a config written months ago points at a graveyard -- so capacity that is paid for, authorised and
live reads as a dead provider. Five providers, every one of them reachable, all failing on a
string.

WHAT THIS DOES
--------------
Asks. Almost every one of these is OpenAI-compatible and answers `GET /v1/models` with the list
it will actually serve today. That is the authority; the config is a memory of one.

It writes `data/PROVIDER_MODELS.json` and prints, per provider, what is on offer next to what the
config asks for -- so a stale entry is visible as a stale entry rather than as a provider that
stopped working. It does not rewrite the config: which model to use is a judgement about cost,
context and quality that belongs to whoever owns the account.
"""
import argparse
import json
import os
import sys
import time
import urllib.request

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(HERE, "src")
sys.path.insert(0, SRC)
import silence                                                          # noqa: E402

_BAD_CHARS = (chr(8), chr(11), chr(12), chr(7))
if any(c in open(os.path.abspath(__file__), encoding="utf-8").read() for c in _BAD_CHARS):
    raise SystemExit(__file__ + ": a regex escape was eaten in transit.")

OUT = os.path.join(HERE, "data", "PROVIDER_MODELS.json")

# Where each provider lists what it serves. Every one of these is the provider's own documented
# endpoint; none is guessed.
LIST_PATHS = ("/models", "/v1/models")


def _key_of(prov):
    for k in ("api_key", "key", "token"):
        if prov.get(k):
            return prov[k]
    return None


def _base_of(prov):
    for k in ("base_url", "base", "url", "endpoint"):
        if prov.get(k):
            return str(prov[k]).rstrip("/")
    return None


# The four things a probe can conclude. Every provider gets exactly one, and every one of them
# is reported: "we could not ask" is a finding about the pool, not an absence from it.
LISTED = "listed"              # answered with at least one model id
EMPTY_LIST = "empty_list"      # answered 200 with a WELL-FORMED, EMPTY list -- serves nothing
UNREACHABLE = "unreachable"    # the request itself failed: HTTP error, timeout, bad JSON
UNCONFIGURED = "unconfigured"  # never asked: no base url, or no key


def ask_provider(name, prov, timeout=30):
    """What this provider says it serves today, and -- if it did not say -- why not.

    Always returns an `outcome` from the four above. A caller must not infer freshness from the
    absence of a `stale` entry: `unreachable` and `unconfigured` providers have no verified
    model list at all, and a provider nobody could ask is not a provider with nothing wrong.
    """
    base = _base_of(prov)
    key = _key_of(prov)
    if not base:
        return {"provider": name, "outcome": UNCONFIGURED, "error": "no base url in config"}
    if not key and not prov.get("local"):
        return {"provider": name, "outcome": UNCONFIGURED, "error": "no key"}

    # A base of ".../v1" already carries the version; appending "/v1/models" would ask for
    # /v1/v1/models, which 404s and reads as a dead provider. Try the shorter form first.
    tries = []
    for path in LIST_PATHS:
        if base.endswith("/v1") and path.startswith("/v1"):
            continue
        tries.append(base + path)
    # A 200 CARRYING AN EMPTY LIST IS AN ANSWER, and a different one from a dead endpoint. This
    # loop used `if ids: return ...` with no other branch, so a provider that answered correctly
    # and served nothing fell out of the bottom described as "no model list endpoint" -- i.e. as
    # a provider whose API does not exist, when in fact its API exists and its catalogue is
    # empty. Those two want opposite responses: one is a wrong URL, the other is an account with
    # no entitlements. Recorded distinctly now, and still tried against the remaining paths
    # first, because an empty /models does not mean /v1/models is empty too. Order e307e2c38267.
    empty_at = None
    last = None
    for url in tries:
        try:
            req = urllib.request.Request(url, headers={
                "Authorization": f"Bearer {key}" if key else "",
                "User-Agent": "PanscriptumResearchBot/1.0"})
            with urllib.request.urlopen(req, timeout=timeout) as r:
                d = json.loads(r.read().decode("utf-8", "replace"))
            rows = d.get("data") if isinstance(d, dict) else d
            ids = []
            for m in (rows or []):
                mid = m.get("id") or m.get("name") if isinstance(m, dict) else str(m)
                if mid:
                    ids.append(mid)
            if ids:
                return {"provider": name, "outcome": LISTED, "url": url,
                        "models": sorted(ids)}
            if empty_at is None:
                empty_at = url
        except Exception as e:
            silence.note("catalogue_models.py:ask_provider")
            # NOT CUT. `str(e)[:70]` was a Hard Rule 0 cap on a PERSISTED field: this string
            # becomes `providers[].error` and `unverified[].why` in data/PROVIDER_MODELS.json,
            # which standards.py reads, and it is the one thing that tells a reader whether to
            # add a key, top up an account or fix a URL. These are single-line exception reprs,
            # not documents -- a URL plus a status line already passes 70 characters, so the cut
            # was landing on the reason itself. (order 6d354a508b96)
            # Whitespace is collapsed rather than trimmed: nothing is dropped, and the row stays
            # one console line even if some provider client ever raises a multi-line message.
            last = "%s: %s" % (type(e).__name__, " ".join(str(e).split()))
    if empty_at is not None:
        return {"provider": name, "outcome": EMPTY_LIST, "url": empty_at, "models": [],
                "error": "endpoint answered with an EMPTY model list -- the API is alive and "
                         "serves nothing (not a missing endpoint)"}
    return {"provider": name, "outcome": UNREACHABLE,
            "error": last or "no model list endpoint (no path answered)"}


def wanted(cfg):
    """{provider: [model ids the config asks for]}"""
    out = {}
    for m in cfg.get("models") or []:
        p = m.get("provider")
        if p:
            out.setdefault(p, []).append(m.get("model") or m.get("id"))
    return out


# Whether the last `sweep()` actually LANDED PROVIDER_MODELS.json on disk. Carried out of band
# rather than in `sweep`'s return value because that return value is the payload -- the shape
# `standards.py` reads -- and because a flag inside the payload would read as though it were a
# field of the FILE, which it deliberately is not. One writer, one reader (`main`), one call.
LAST_WRITE_LANDED = True


def sweep(config_path=None, workers=6):
    from concurrent.futures import ThreadPoolExecutor
    global LAST_WRITE_LANDED
    config_path = config_path or os.path.join(os.path.expanduser("~"), "cascade", "config.json")
    with open(config_path, encoding="utf-8") as f:
        cfg = json.load(f)
    provs = cfg.get("providers") or {}
    want = wanted(cfg)

    with ThreadPoolExecutor(max_workers=workers) as ex:
        rows = list(ex.map(lambda kv: ask_provider(kv[0], kv[1]), sorted(provs.items())))

    # ON THE OUTCOME, NOT ON TRUTHINESS (sweep42-batch14).
    #
    # This read `if r.get("models")`, and an empty list is falsy -- so a provider whose outcome
    # is EMPTY_LIST was dropped out of `live` and fell into the `if not r` branch below, where
    # it was printed as unverifiable and its configured model ids were counted as UNVERIFIED.
    #
    # But EMPTY_LIST is the opposite of unverifiable. The constant's own definition two hundred
    # lines up says it: "answered 200 with a WELL-FORMED, EMPTY list -- serves nothing". That is
    # a SUCCESSFUL measurement with a definite result, and the correct reading of it is that
    # every model id the config asks that provider for is STALE -- the provider serves none of
    # them. Recording a completed measurement as a measurement that never happened is the same
    # arithmetic error the long comment below this line was written about, arriving through the
    # one outcome that comment did not anticipate.
    #
    # With the provider in `live`, `have` is the empty set, every ask lands in `missing`, and
    # the rows print and count as stale, which is what they are.
    live = {r["provider"]: r for r in rows
            if r.get("outcome") in (LISTED, EMPTY_LIST)}
    by_name = {r["provider"]: r for r in rows}
    print(f"{len(live)} of {len(rows)} providers answered with a model list\n")
    stale = []
    # A PROVIDER NOBODY COULD ASK IS NOT A PROVIDER WITH NOTHING WRONG. The loop below used to
    # `continue` past every provider that produced no list, so those providers contributed
    # nothing to `stale` and nothing to any count -- they simply were not in the arithmetic.
    # `standards.py`'s `model IDs their providers still serve` standard then reported "0 stale
    # in the cloud pool" over a pool that, in the
    # 2026-08-25 20:21 snapshot, had 14 of its 26 providers never produce a list at all: 10 with
    # no key configured and 4 that failed the request outright. Zero stale out of twelve verified
    # is a fact; zero stale out of twenty-six is what that line was read as.
    #
    # `stale` deliberately does NOT absorb them -- a stale row asserts "the config asks for a
    # model this provider no longer serves", and for an unasked provider that is unknown, not
    # true. They get their own list, `unverified`, carrying the model ids whose status could not
    # be established, so the gap is countable and nameable instead of invisible. Order
    # cd64337d3349.
    unverified = []
    for name in sorted(provs):
        r = live.get(name)
        asks = [a for a in (want.get(name) or []) if a]
        if not r:
            row = by_name.get(name) or {}
            why = row.get("error", "?")
            outcome = row.get("outcome", UNREACHABLE)
            print(f"  {name:<16}-- {outcome.upper()}: {why}")
            unverified.append({"provider": name, "outcome": outcome, "why": why,
                               "config_asks_for": asks, "unchecked": len(asks)})
            continue
        have = set(r["models"])
        missing = [a for a in asks if a not in have]
        print(f"  {name:<16}{len(have):>4} model(s) available"
              + (f"   CONFIG ASKS FOR {len(missing)} THAT NO LONGER EXIST" if missing else ""))
        for a in missing:
            print(f"      stale: {a}")
            # THE WHOLE LIST. `[:8]` here was a Hard Rule 0 cap on the very field a person reads
            # to pick the replacement for a retired model name: if the provider's ninth model was
            # the right substitute, nothing that consumed this record could see it. The key name
            # keeps its `_sample` suffix only because the written record may already be on disk
            # under it; the value is no longer a sample. (run #26)
            stale.append({"provider": name, "wants": a, "available_sample": list(r["models"])})
    if stale:
        print(f"\n{len(stale)} stale model reference(s). The keys work; the names do not.")
        print("Current alternatives, per provider:")
        for name in sorted({s["provider"] for s in stale}):
            r = live.get(name)
            if r:
                # THE WHOLE LIST HERE TOO. `[:10]` was the same Hard Rule 0 cap as the
                # `available_sample` fix in this same `sweep()` (run #26), surviving on the
                # console line rather than in the record -- and this line is the one a person actually reads while
                # choosing the replacement for a retired model name. The persisted copy being
                # complete does not help someone looking at the terminal: an eleventh-ranked
                # model that was the right substitute simply was not there to be picked, and
                # a truncated listing does not announce itself as truncated. (run33)
                print(f"  {name}: " + ", ".join(r["models"]))

    # THE DENOMINATOR, PRINTED. Every unverified provider by name, with the outcome that made it
    # unverifiable and how many configured model ids went unchecked because of it -- so nobody
    # reads "N stale" without also reading how much of the pool that N was measured over.
    # EMPTY_LIST COUNTS AS VERIFIED HERE TOO, for the same reason it now counts as live above
    # (sweep42-batch14): a provider that answered with a well-formed empty list HAS been asked
    # and HAS answered, so it belongs in the denominator this line exists to make honest. Left
    # out of it, the "measured over N providers" figure understated the pool by exactly the
    # providers whose answer was most definite.
    verified = [r for r in rows if r.get("outcome") in (LISTED, EMPTY_LIST)]
    if unverified:
        n_unchecked = sum(u["unchecked"] for u in unverified)
        print(f"\n{len(unverified)} of {len(rows)} provider(s) produced NO model list, so their "
              f"{n_unchecked} configured model id(s) are UNVERIFIED -- neither fresh nor stale, "
              f"unasked. An unreachable provider is not a fresh provider.")
        for u in sorted(unverified, key=lambda u: (u["outcome"], u["provider"])):
            asks = ", ".join(u["config_asks_for"]) or "(config asks for nothing here)"
            # THE REASON IS THE PAYLOAD OF THIS LINE, so it is not cut. `[:52]` was a third cut
            # on the same string (:130 stored it, this clipped the console copy) on the one line
            # whose stated purpose, four lines up, is "Every unverified provider by name, with
            # the outcome that made it unverifiable". Moved onto its own continuation line
            # beside the existing `unchecked:` line so the column stays aligned and the reason
            # gets the full width. (order 6d354a508b96)
            print(f"  {u['outcome'].upper():<13}{u['provider']}")
            print(f"                {' ' * 16}why:       {u['why']}")
            print(f"                {' ' * 16}unchecked: {asks}")
    print(f"\nstale count is measured over {len(verified)} verified provider(s) of {len(rows)}.")

    payload = {
        "at": time.strftime("%Y-%m-%d %H:%M"),
        "providers": rows,
        "stale": stale,
        # Read `stale` next to these or not at all: `stale: []` over 12 of 26 providers is not
        # the same claim as `stale: []` over 26 of 26, and the file used to record only the
        # former while looking like the latter.
        "unverified": unverified,
        "counts": {"providers": len(rows), "verified": len(verified),
                   "unverified": len(unverified),
                   "empty_list": len([r for r in rows if r.get("outcome") == EMPTY_LIST]),
                   "unreachable": len([r for r in rows if r.get("outcome") == UNREACHABLE]),
                   "unconfigured": len([r for r in rows if r.get("outcome") == UNCONFIGURED]),
                   "stale_ids": len(stale),
                   "unchecked_ids": sum(u["unchecked"] for u in unverified)},
    }
    # ATOMIC: standards.py polls PROVIDER_MODELS.json on its own cycle. 2026-08-25.
    #
    # GATED: `write_json` returns whether the rename LANDED and this discarded the verdict, then
    # printed "-> {OUT}" unconditionally -- and `main()` returned 0 on top of that. `foreman.py`
    # runs this module as a subprocess and reads its RETURN CODE (recatalogue_models), so a
    # denied replace reported a successful refresh of the model IDs to the one caller whose whole
    # job is deciding whether the remedy worked, while `standards.py` went on polling the stale
    # snapshot. Run #36 discarded-verdict sweep.
    LAST_WRITE_LANDED = silence.write_json(OUT, payload, indent=1, sort_keys=True)
    if LAST_WRITE_LANDED:
        print(f"\n-> {OUT}")
    else:
        silence.note("catalogue_models.py:sweep-write-denied")
        print(f"\nWRITE DENIED -> {OUT}: replace refused, so this sweep's results did NOT land. "
              f"The snapshot on disk is the PREVIOUS one and standards.py is still reading it. "
              f"Rerun to retry.")
    return payload


def main():
    ap = argparse.ArgumentParser(description="ask each provider what it actually serves")
    ap.add_argument("--config", help="path to cascade config.json")
    a = ap.parse_args()
    sweep(config_path=a.config)
    # A sweep whose snapshot did not reach disk is not a refresh, and `foreman.recatalogue_models`
    # distinguishes the two only by this status.
    return 0 if LAST_WRITE_LANDED else 1


if __name__ == "__main__":
    sys.exit(main())
