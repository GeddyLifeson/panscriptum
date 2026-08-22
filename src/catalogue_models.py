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


def ask_provider(name, prov, timeout=30):
    """What this provider says it serves today."""
    base = _base_of(prov)
    key = _key_of(prov)
    if not base:
        return {"provider": name, "error": "no base url in config"}
    if not key and not prov.get("local"):
        return {"provider": name, "error": "no key"}

    # A base of ".../v1" already carries the version; appending "/v1/models" would ask for
    # /v1/v1/models, which 404s and reads as a dead provider. Try the shorter form first.
    tries = []
    for path in LIST_PATHS:
        if base.endswith("/v1") and path.startswith("/v1"):
            continue
        tries.append(base + path)
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
                return {"provider": name, "url": url, "models": sorted(ids)}
        except Exception as e:
            silence.note("catalogue_models.py:ask_provider")
            last = f"{type(e).__name__}: {str(e)[:70]}"
    return {"provider": name, "error": locals().get("last", "no model list endpoint")}


def wanted(cfg):
    """{provider: [model ids the config asks for]}"""
    out = {}
    for m in cfg.get("models") or []:
        p = m.get("provider")
        if p:
            out.setdefault(p, []).append(m.get("model") or m.get("id"))
    return out


def sweep(config_path=None, workers=6):
    from concurrent.futures import ThreadPoolExecutor
    config_path = config_path or os.path.join(os.path.expanduser("~"), "cascade", "config.json")
    with open(config_path, encoding="utf-8") as f:
        cfg = json.load(f)
    provs = cfg.get("providers") or {}
    want = wanted(cfg)

    with ThreadPoolExecutor(max_workers=workers) as ex:
        rows = list(ex.map(lambda kv: ask_provider(kv[0], kv[1]), sorted(provs.items())))

    live = {r["provider"]: r for r in rows if r.get("models")}
    print(f"{len(live)} of {len(rows)} providers answered with a model list\n")
    stale = []
    for name in sorted(provs):
        r = live.get(name)
        asks = [a for a in (want.get(name) or []) if a]
        if not r:
            why = next((x.get("error") for x in rows if x["provider"] == name), "?")
            print(f"  {name:<16}-- {why}")
            continue
        have = set(r["models"])
        missing = [a for a in asks if a not in have]
        print(f"  {name:<16}{len(have):>4} model(s) available"
              + (f"   CONFIG ASKS FOR {len(missing)} THAT NO LONGER EXIST" if missing else ""))
        for a in missing:
            print(f"      stale: {a}")
            stale.append({"provider": name, "wants": a, "available_sample": r["models"][:8]})
    if stale:
        print(f"\n{len(stale)} stale model reference(s). The keys work; the names do not.")
        print("Current alternatives, per provider:")
        for name in sorted({s["provider"] for s in stale}):
            r = live.get(name)
            if r:
                print(f"  {name}: " + ", ".join(r["models"][:10]))

    payload = {"at": time.strftime("%Y-%m-%d %H:%M"), "providers": rows, "stale": stale}
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=1, sort_keys=True)
    print(f"\n-> {OUT}")
    return payload


def main():
    ap = argparse.ArgumentParser(description="ask each provider what it actually serves")
    ap.add_argument("--config", help="path to cascade config.json")
    a = ap.parse_args()
    sweep(config_path=a.config)
    return 0


if __name__ == "__main__":
    sys.exit(main())
