#!/usr/bin/env python3
"""
Runs the generation manifest against a local Ollama model, compresses the output, and
maintains a resumable catalog + failure log.

Usage:
    python3 src/generate.py --manifest output/index/manifest.pilot.json
    python3 src/generate.py --manifest output/index/manifest.json --limit 20
    python3 src/generate.py --manifest output/index/manifest.json --dry-run
"""
import argparse
import datetime
import json
import os
import re
import sys
import time

import requests
import yaml
from tqdm import tqdm

sys.path.insert(0, os.path.dirname(__file__))
from address import recipe_hash, babel_coordinate  # noqa: E402
import compress_store  # noqa: E402
import silence

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def load_config():
    with open(os.path.join(HERE, "config.yaml"), encoding="utf-8") as f:
        return yaml.safe_load(f)


def load_json(path, default):
    full = os.path.join(HERE, path)
    if not os.path.exists(full):
        return default
    with open(full, encoding="utf-8") as f:
        return json.load(f)


def save_json(path, obj):
    full = os.path.join(HERE, path)
    os.makedirs(os.path.dirname(full), exist_ok=True)
    with open(full, "w", encoding="utf-8") as f:
        json.dump(obj, f, indent=2)


def safe_filename(address, ext):
    s = re.sub(r"[^A-Za-z0-9]+", "_", address).strip("_")
    return f"{s}.{ext}"


def load_prompt_templates():
    p = os.path.join(HERE, "prompts")
    with open(os.path.join(p, "system_style.txt"), encoding="utf-8") as f:
        system = f.read()
    with open(os.path.join(p, "chapter_prompt.txt"), encoding="utf-8") as f:
        chapter_tpl = f.read()
    with open(os.path.join(p, "frontmatter_prompt.txt"), encoding="utf-8") as f:
        front_tpl = f.read()
    return system, chapter_tpl, front_tpl


def build_prompt(job, chapter_tpl, front_tpl):
    if job["type"] == "frontmatter":
        return front_tpl.format(
            source_name=job["source_name"],
            spine_code=job["spine_code"],
            address=job["address"],
            volume_facts_json=json.dumps(job["volume_facts"], indent=2, ensure_ascii=False),
        )
    else:
        return chapter_tpl.format(
            source_name=job["source_name"],
            spine_code=job["spine_code"],
            chapter_label=job["chapter_label"],
            address=job["address"],
            source_context=json.dumps(job.get("source_context", {}), indent=2, ensure_ascii=False),
            entries_json=json.dumps(job["entries"], indent=2, ensure_ascii=False),
        )


def call_ollama(cfg, system_prompt, user_prompt):
    url = cfg["ollama_host"].rstrip("/") + "/api/generate"
    payload = {
        "model": cfg["model"],
        "system": system_prompt,
        "prompt": user_prompt,
        "stream": False,
        "options": {
            "seed": cfg.get("seed", 47),
            "temperature": cfg.get("temperature", 0.2),
            "num_ctx": cfg.get("num_ctx", 8192),
        },
    }
    resp = requests.post(url, json=payload, timeout=cfg.get("request_timeout", 600))
    resp.raise_for_status()
    data = resp.json()
    return data.get("response", "")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--manifest", required=True)
    ap.add_argument("--limit", type=int, default=None, help="only run the first N pending jobs")
    ap.add_argument("--dry-run", action="store_true", help="build prompts but don't call Ollama")
    args = ap.parse_args()

    cfg = load_config()
    manifest = load_json(args.manifest, {"jobs": []})
    jobs = manifest["jobs"]

    catalog = load_json(cfg["paths"]["catalog"], {})
    failures = load_json(cfg["paths"]["failures"], {})

    system_prompt, chapter_tpl, front_tpl = load_prompt_templates()
    prompt_version = cfg.get("prompt_version", "v1")
    model = cfg["model"]
    seed = cfg.get("seed", 47)

    pending = []
    stale_count = 0
    for job in jobs:
        rh = recipe_hash(job["address"], model, seed, prompt_version, job.get("content_hash", ""))
        cached = catalog.get(job["address"], {})
        if cached.get("recipe_hash") == rh:
            continue  # already generated from this exact source data, model, seed, and prompt
        if cached and cached.get("recipe_hash") != rh:
            stale_count += 1  # was generated before, but data/model/prompt changed since
        pending.append((job, rh))

    if stale_count:
        print(f"({stale_count} of those are stale -- previously generated, but the source data, "
              f"model, or prompt version has changed since, so they'll be regenerated)")

    if args.limit:
        pending = pending[: args.limit]

    print(f"{len(jobs)} total jobs, {len(pending)} pending (not yet cached under current "
          f"model={model} seed={seed} prompt_version={prompt_version})")

    if args.dry_run:
        for job, rh in pending[:3]:
            print("=" * 80)
            print(job["address"])
            print(build_prompt(job, chapter_tpl, front_tpl)[:1500])
        print(f"\n(dry run: showed {min(3, len(pending))} of {len(pending)} pending prompts, "
              f"nothing was sent to Ollama)")
        return

    raw_dir = os.path.join(HERE, cfg["paths"]["raw_dir"])
    compressed_dir = os.path.join(HERE, cfg["paths"]["compressed_dir"])
    os.makedirs(raw_dir, exist_ok=True)

    done_count = 0
    fail_count = 0

    for job, rh in tqdm(pending, desc="generating"):
        user_prompt = build_prompt(job, chapter_tpl, front_tpl)
        try:
            text = call_ollama(cfg, system_prompt, user_prompt)
            if not text.strip():
                raise RuntimeError("empty response from Ollama")
        except Exception as e:
            silence.note("generate.py:166")
            fail_count += 1
            failures[job["address"]] = {
                "error": str(e),
                "job_type": job["type"],
                "source_name": job["source_name"],
                "timestamp": datetime.datetime.utcnow().isoformat() + "Z",
            }
            save_json(cfg["paths"]["failures"], failures)
            continue

        raw_path = os.path.join(raw_dir, safe_filename(job["address"], "md"))
        with open(raw_path, "w", encoding="utf-8") as f:
            f.write(f"<!-- {job['address']} -->\n\n{text}")

        store_info = compress_store.store(text, compressed_dir)
        babel_coord = babel_coordinate({"address": job["address"], "hash": store_info["hash"]})

        catalog[job["address"]] = {
            "recipe_hash": rh,
            "content_hash": store_info["hash"],
            "raw_path": os.path.relpath(raw_path, HERE),
            "compressed_path": os.path.relpath(store_info["path"], HERE),
            "codec": store_info["codec"],
            "raw_bytes": store_info["raw_bytes"],
            "compressed_bytes": store_info["compressed_bytes"],
            "model": model,
            "seed": seed,
            "prompt_version": prompt_version,
            "job_type": job["type"],
            "source_name": job["source_name"],
            "chapter_label": job.get("chapter_label"),
            "babel_coordinate": babel_coord,
            "generated_at": datetime.datetime.utcnow().isoformat() + "Z",
        }
        done_count += 1

        # save incrementally so Ctrl-C doesn't lose progress
        if done_count % 5 == 0:
            save_json(cfg["paths"]["catalog"], catalog)

    save_json(cfg["paths"]["catalog"], catalog)
    if failures:
        save_json(cfg["paths"]["failures"], failures)

    print(f"\nDone. {done_count} generated this run, {fail_count} failed "
          f"(see {cfg['paths']['failures']}).")


if __name__ == "__main__":
    main()
