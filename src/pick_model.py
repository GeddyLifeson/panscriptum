#!/usr/bin/env python3
"""
Picks the best available local Ollama model for long-form, fact-grounded encyclopedia prose --
rather than just trusting whatever's hardcoded in config.yaml. Run this before your first real
generation pass (and again any time you pull new models).

What "best" means here: instruct/chat-tuned (not a bare base model, not an embedding model),
strong at following a fairly detailed style contract and staying grounded in supplied facts
without wandering off, and large enough to hold a chapter's worth of entries in context without
losing the thread. Bigger isn't automatically better if it's so slow the run never finishes --
this ranks by a quality tier first, size second, and tells you the tradeoff rather than hiding
it.

Usage:
    python3 src/pick_model.py                 # show the ranked report, don't touch config.yaml
    python3 src/pick_model.py --write          # also update config.yaml's `model:` to the winner
    python3 src/pick_model.py --min-quality 3  # require at least tier 3 (see TIERS below); if
                                                # nothing installed clears the bar, print `ollama
                                                # pull` commands for good options instead of
                                                # silently settling for a worse model
"""
import argparse
_NO_WIN = getattr(__import__("subprocess"), "CREATE_NO_WINDOW", 0)

import os
import re
import sys

import requests
import yaml
import silence

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Family quality tiers for long-form, instruction-following, fact-grounded writing.
# Higher tier = generally better at this specific job, based on public benchmarks/consensus as
# of this kit's creation -- NOT a universal ranking, and it goes stale. Update this list if the
# owner has opinions or newer models exist by the time this actually runs.
#
# UPDATED 2026-08-19 (local session). The original table predated the Qwen3 / Gemma 3 /
# Mistral-Small-3 / gpt-oss generation and mis-ranked all of them badly. Worse, it did so
# *silently*: matching is a plain substring test in list order, so "qwen" in the old tier-1
# legacy bucket caught every `qwen3*` tag and scored it 1 instead of 5. Measured effect on
# this machine's installed models --
#
#     qwen2.5:14b                   tier 5, score 55.0   <- what it picked
#     gemma3:12b                    tier 3, score 34.7
#     qwen3:30b-a3b-instruct-2507   tier 1, score 16.0
#     gpt-oss:20b                   tier 0, score  5.5
#
# qwen2.5:14b was then benchmarked at 4.7 tok/s on a real chapter job (28% of its layers
# offloaded to CPU), i.e. the picker was confidently selecting the slowest available option.
# Ordering matters here: longer, more specific family strings MUST come before their own
# prefixes, which is why "qwen3" sits above the bare "qwen" catch-all.
FAMILY_TIERS = [
    (5, ["qwen3", "qwen2.5-coder", "qwen2.5", "llama3.3", "llama3.1", "gemma3",
         "mistral-small3", "mistral-large", "command-r-plus", "gpt-oss", "deepseek-v3"]),
    (4, ["qwen2", "mixtral", "command-r", "gemma2", "mistral-nemo", "deepseek-v2", "deepseek-r1"]),
    (3, ["llama3", "mistral", "gemma", "phi3.5"]),
    (2, ["phi3", "phi", "llama2", "vicuna", "zephyr"]),
    (1, ["tinyllama", "qwen", "stablelm"]),
]

# Rough on-disk weight size in GB for tags this script knows about, used for the VRAM-fit
# warning below. Anything not listed here falls back to estimating from parameter count.
KNOWN_WEIGHT_GB = {
    "qwen3:14b": 9.3,
    "qwen3:30b-a3b-instruct-2507-q4_K_M": 18.6,
    "qwen3:32b": 20.2,
    "gemma3:12b": 8.1,
    "gemma3:27b": 17.4,
    "mistral-small3.2:24b": 15.2,
    "gpt-oss:20b": 13.8,
    "qwen2.5:14b": 9.0,
    "qwen2.5:32b": 19.9,
}

# Families that are mixture-of-experts: only a small fraction of parameters is active per
# token, so spilling layers to system RAM costs far less than it does for a dense model of the
# same file size. Relevant on a 10GB card, where nothing good fits entirely in VRAM.
MOE_MARKERS = ["a3b", "a22b", "gpt-oss", "mixtral"]

EXCLUDE_PATTERNS = ["embed", "embedding", "bge-", "nomic-embed", "clip", "llava", "moondream",
                     "minilm"]  # vision/embedding models -- wrong tool for prose generation


def load_config():
    with open(os.path.join(HERE, "config.yaml"), encoding="utf-8") as f:
        return yaml.safe_load(f)


def save_config(cfg):
    with open(os.path.join(HERE, "config.yaml"), encoding="utf-8") as f:
        raw = f.read()
    # targeted replace of the model: line so we don't clobber comments/formatting elsewhere
    new_raw = re.sub(r'^model:\s*.*$', f'model: "{cfg["model"]}"', raw, count=1, flags=re.M)
    with open(os.path.join(HERE, "config.yaml"), "w", encoding="utf-8") as f:
        f.write(new_raw)


def list_installed_models(ollama_host):
    resp = requests.get(ollama_host.rstrip("/") + "/api/tags", timeout=15)
    resp.raise_for_status()
    return resp.json().get("models", [])


def family_tier(model_name):
    name = model_name.lower()
    for tier, families in FAMILY_TIERS:
        for fam in families:
            if fam in name:
                return tier
    return 0  # unknown family -- still usable, ranked last among non-excluded models


def parse_param_size(model_entry):
    """Pull a rough parameter count (in billions) out of Ollama's model details, if present."""
    details = model_entry.get("details", {}) or {}
    ps = details.get("parameter_size", "")  # e.g. "8B", "14B", "70.6B"
    m = re.match(r"([\d.]+)\s*B", ps, re.I)
    if m:
        return float(m.group(1))
    # fall back to parsing the tag itself, e.g. "llama3.1:8b-instruct"
    m = re.search(r"(\d+(?:\.\d+)?)\s*b\b", model_entry.get("name", "").lower())
    return float(m.group(1)) if m else 0.0


def is_instruct_tuned(model_entry):
    name = model_entry.get("name", "").lower()
    # most Ollama chat models are instruct-tuned by default even without the word in the tag,
    # but explicit instruct/chat tags and a non-"base"/"text" tag are good positive signals
    if any(bad in name for bad in ["-base", "-text", "-pt"]):
        return False
    return True


def free_vram_gb():
    """Free VRAM in GB via nvidia-smi, or None if it isn't available.

    Deliberately reads *free* rather than total: on this machine the Windows desktop
    (Wallpaper Engine, browsers, Discord, Steam, ...) was holding 2.3GB of a 10GB card, so
    total capacity is a misleading number to size a model against.
    """
    import subprocess
    try:
        out = subprocess.run(
            ["nvidia-smi", "--query-gpu=memory.free", "--format=csv,noheader,nounits"],
            capture_output=True, text=True, timeout=15, creationflags=_NO_WIN)
        if out.returncode != 0:
            return None
        return int(out.stdout.strip().splitlines()[0]) / 1024.0
    except Exception:
        silence.note("pick_model.py:150")
        return None


def print_pull_suggestions():
    """Recommendations sized for a 10GB card, best first. Kept in one place so the no-models
    path and the below-quality-bar path can't drift apart."""
    print("  ollama pull qwen3:30b-a3b-instruct-2507-q4_K_M")
    print("      18.6GB. Mixture-of-experts, only ~3B params active per token, so the layers")
    print("      that don't fit in VRAM cost far less than they would for a dense model this")
    print("      size. The -instruct-2507 variant is non-thinking, which matters: generate.py")
    print("      writes data['response'] straight to disk and has no <think>-tag stripping,")
    print("      so a reasoning variant would embed its scratchpad in the finished volumes.")
    print("  ollama pull gemma3:12b")
    print("      8.1GB. Fits entirely in 10GB once the desktop isn't holding ~2.3GB of it.")
    print("      Faster, strong prose voice, somewhat weaker at holding a rigid repeated")
    print("      template across ten entries in one call.")
    print("  ollama pull llama3.1:8b")
    print("      4.9GB. Comfortable fallback; measured at 20.2 tok/s here, fully GPU-resident.")


def is_moe(name):
    return any(marker in name.lower() for marker in MOE_MARKERS)


def weight_gb(model_entry):
    name = model_entry.get("name", "")
    if name in KNOWN_WEIGHT_GB:
        return KNOWN_WEIGHT_GB[name]
    size = model_entry.get("size")
    if size:
        return size / 1e9
    return parse_param_size(model_entry) * 0.6  # ~Q4 bytes per param


def fit_note(model_entry, vram_gb, num_ctx_gb=1.2):
    """Plain-language warning about whether this model will actually stay on the GPU.

    The whole point: a dense model that spills is catastrophically slow (measured 4.7 tok/s
    for a 28%-offloaded 14B on this box), while an MoE that spills is merely slower.
    """
    need = weight_gb(model_entry) + num_ctx_gb
    if need <= vram_gb:
        return "fits in VRAM"
    if is_moe(model_entry.get("name", "")):
        return (f"needs ~{need:.1f}GB vs {vram_gb:.1f}GB free -- will offload, but it's MoE "
                f"so the cost is modest")
    return (f"WILL OFFLOAD: needs ~{need:.1f}GB vs {vram_gb:.1f}GB free, and it's dense -- "
            f"expect a large speed penalty")


def score_model(model_entry):
    name = model_entry.get("name", "")
    if any(pat in name.lower() for pat in EXCLUDE_PATTERNS):
        return None  # not a text-generation model, skip entirely
    tier = family_tier(name)
    params = parse_param_size(model_entry)
    instruct_bonus = 1 if is_instruct_tuned(model_entry) else 0
    # size sweet spot: quality keeps climbing up to ~30B for this use case, then the speed cost
    # usually isn't worth it for hundreds of chapter generations -- rank size logarithmically
    # and cap its influence so a 70B model doesn't automatically beat a better-tier 14B one
    import math
    size_score = math.log2(max(params, 1) + 1)
    return (tier * 10) + instruct_bonus + min(size_score, 6)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--write", action="store_true", help="update config.yaml with the winner")
    ap.add_argument("--min-quality", type=int, default=0,
                     help="require at least this family tier (1-5); if nothing installed "
                          "qualifies, print `ollama pull` suggestions instead of picking a "
                          "worse model")
    args = ap.parse_args()

    cfg = load_config()
    try:
        models = list_installed_models(cfg["ollama_host"])
    except Exception as e:
        print(f"Couldn't reach Ollama at {cfg['ollama_host']} ({e}). Is it running? "
              f"(`ollama serve`)")
        sys.exit(1)

    if not models:
        print("No models installed. Recommended pulls for this job, best first:")
        print_pull_suggestions()
        sys.exit(1)

    scored = []
    for m in models:
        s = score_model(m)
        if s is not None:
            scored.append((s, m))
    scored.sort(key=lambda x: -x[0])

    vram_gb = free_vram_gb()
    print(f"{len(models)} models installed, {len(scored)} usable for text generation.")
    if vram_gb:
        print(f"~{vram_gb:.1f}GB VRAM currently free (close browsers/wallpaper apps to raise "
              f"this):\n")
    else:
        print("(couldn't read free VRAM -- nvidia-smi not available)\n")
    for s, m in scored:
        tier = family_tier(m["name"])
        params = parse_param_size(m)
        note = f"  [{fit_note(m, vram_gb)}]" if vram_gb else ""
        print(f"  [{s:5.1f}] {m['name']:35s} tier={tier} ~{params:.0f}B params{note}")

    if not scored:
        print("\nNothing usable installed (only embedding/vision models found?). Pull a text "
              "model -- see the no-models message above for suggestions.")
        sys.exit(1)

    best_score, best = scored[0]
    best_tier = family_tier(best["name"])

    if best_tier < args.min_quality:
        print(f"\nBest installed model ({best['name']}) is tier {best_tier}, below your "
              f"--min-quality {args.min_quality}. Consider pulling something better:")
        print_pull_suggestions()
        print(f"\n(Not auto-selecting a model below your quality bar. Re-run without "
              f"--min-quality to accept {best['name']} anyway, or pull a better one first.)")
        sys.exit(1)

    print(f"\nBest available: {best['name']}")
    if args.write:
        cfg["model"] = best["name"]
        save_config(cfg)
        print(f"config.yaml updated: model: \"{best['name']}\"")
    else:
        print("(dry run -- re-run with --write to update config.yaml)")


if __name__ == "__main__":
    main()
