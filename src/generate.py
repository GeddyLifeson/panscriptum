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

import requests
import yaml
from tqdm import tqdm

sys.path.insert(0, os.path.dirname(__file__))
from address import recipe_hash, babel_coordinate  # noqa: E402
import compress_store  # noqa: E402
import silence

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# VOLUME DEPTH (owner ruling 2026-08-23): every volume is a full-length book, and a local
# model asked for thirty complete Entry Template entries in one response writes eight of them
# properly and waves at the rest -- output attention thins exactly the way read.py measured
# input attention thinning past 30k characters. So a chapter is WRITTEN IN BLOCKS of a few
# entries per model call and stitched, with every entry's presence verified in the text it
# came back in. A missing entry retries once; still missing fails the whole job LOUDLY so the
# next run redoes it, because a book quietly missing its own entries is the prose version of
# the catalogue cap: a smaller universe wearing the shape of the real one.
WRITE_CHUNK = 8


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
    # ATOMIC: catalog.json and failures.json are rewritten repeatedly across an hours-long
    # generation run while estate.py and catalog.py read them; a truncate-then-fill here hands
    # those readers an empty or half-written file. 2026-08-25.
    full = os.path.join(HERE, path)
    silence.write_json(full, obj, indent=2)


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


_FEATS_TPL = [None]


def feats_template():
    """The Feats chapter template, loaded once, on demand.

    Deliberately NOT added to `load_prompt_templates()`'s return tuple: that tuple is unpacked
    at four call sites and threaded through `generate_job`, so widening it would be a signature
    change across the module for a template only one branch ever uses.
    """
    if _FEATS_TPL[0] is None:
        with open(os.path.join(HERE, "prompts", "feats_prompt.txt"), encoding="utf-8") as f:
            _FEATS_TPL[0] = f.read()
    return _FEATS_TPL[0]


def build_prompt(job, chapter_tpl, front_tpl):
    if job["type"] == "feats":
        # A feats chapter carries `entities`, not `entries`, and its own contract: the deeds are
        # quoted evidence and must not be scored, ranked or embellished. See feats_prompt.txt.
        return feats_template().format(
            source_name=job["source_name"],
            spine_code=job["spine_code"],
            chapter_label=job["chapter_label"],
            address=job["address"],
            source_context=json.dumps(job.get("source_context", {}), indent=2,
                                      ensure_ascii=False),
            entities_json=json.dumps(job["entities"], indent=2, ensure_ascii=False),
        )
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


def call_ollama(cfg, system_prompt, user_prompt, job_type="chapter"):
    # THE INPUT SIDE OF THE SAME WINDOW (m46/m52). `num_predict: -1` below removes the OUTPUT
    # ceiling and its comment correctly names silent truncation as what Hard Rule 0 forbids --
    # but `num_ctx` is shared between prompt and answer, and nothing checked the prompt against
    # it. Measured 2026-08-24: a feats prompt came to 41,469 characters against a 6,144-token
    # window, ~1.9x over. Ollama truncates an over-long prompt and answers anyway, and the
    # coverage check below cannot see a shortened deed list -- so the chapter would be filed as
    # complete. Refusing here turns an invisible loss into a recorded failure.
    import context_budget as _CBUD
    _CBUD.assert_fits(cfg, system_prompt, user_prompt, job_type, label=job_type)
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
            # No output ceiling. Ollama's default num_predict caps the response, and a capped
            # response ends a chapter mid-entry without error -- the silent-truncation failure
            # Hard Rule 0 exists to forbid, wearing a generation flag.
            "num_predict": -1,
        },
    }
    # PROSE IS THE FOREGROUND. This is the library's actual product; the corpus read, the roll,
    # the phases and the model lane are all in service of it, so they yield here rather than
    # the other way round. Measured 2026-08-24: a call that caught a free slot returned in
    # 0.057s and the same call queued behind the standing jobs took 28-35s. gpu_lane fails
    # open -- if arbitration breaks, the call still goes.
    import gpu_lane
    with gpu_lane.lane("generate", priority=True):
        resp = requests.post(url, json=payload, timeout=cfg.get("request_timeout", 600))
    resp.raise_for_status()
    data = resp.json()
    return data.get("response", "")


def _covered(name, text):
    """Is this entry actually present in the block the model returned?

    Loose on purpose: the template renders names with markers and occasional reformatting, so
    an exact-substring miss on a real entry would retry work that was done. First and last
    words of the name both appearing is the floor for 'this entry exists in the text'."""
    t = text.lower()
    n = (name or "").lower().strip()
    if not n:
        return True
    if n in t:
        return True
    words = [w for w in re.split(r"[^a-z0-9]+", n) if w]
    return bool(words) and words[0] in t and words[-1] in t


def _deed_traced(deed, text):
    """Is there evidence THIS deed reached the prose, not merely its entity's name?

    A rare-word probe rather than a substring match: the chapter reports an attested sentence
    in the Custodes' voice, so the sentence itself is reworded, but a distinctive proper noun or
    long term inside it survives. The longest alphabetic token of six characters or more is that
    probe. Short and common words are useless here -- "the" proves nothing.
    """
    words = [w for w in re.split(r"[^A-Za-z]+", str(deed or "")) if len(w) >= 6]
    if not words:
        return True                       # nothing distinctive to look for; do not penalise it
    probe = max(words, key=len)
    return probe.lower() in text.lower()


# A feats block whose traceable deeds fall under this fraction was probably cut, not summarised.
# BACKSTOP ONLY. The real defence against a truncated prompt is `context_budget.assert_fits`,
# which refuses to send one; this catches a shortfall that arrives some other way. The floor is
# deliberately lenient because the probe is a proxy and a false failure would discard good work
# -- it is set to catch a block that lost most of its evidence, not one that paraphrased well.
DEED_TRACE_FLOOR = 0.34


def _deed_shortfall(ents, text):
    """-> (traced, total, fraction) across every deed in the block. Never a sample."""
    traced = total = 0
    for e in ents:
        for f in (e.get("feats") or []):
            total += 1
            if _deed_traced(f.get("feat") if isinstance(f, dict) else f, text):
                traced += 1
    return traced, total, (traced / total if total else 1.0)


def generate_job(cfg, system_prompt, job, chapter_tpl, front_tpl):
    """One manifest job -> the full text, written in verified blocks.

    Frontmatter is one call. A chapter is written WRITE_CHUNK entries at a time; each block's
    entries are verified present and a lacking block is retried once; an entry still missing
    after the retry raises, which files the job as a failure and leaves it pending for the
    next run -- never a book quietly missing its own entries."""
    if job["type"] == "frontmatter":
        text = call_ollama(cfg, system_prompt, build_prompt(job, chapter_tpl, front_tpl))
        if not text.strip():
            raise RuntimeError("empty response from Ollama")
        return text

    if job["type"] == "feats":
        # A feats block is ALREADY sized by `manifest_builder.pack_feats` against a character
        # budget, so it is one call -- re-chunking here by entity count would undo the packing
        # that exists precisely because feats are dense. The coverage check is kept: every
        # entity in the block must appear, and a block that omits one is retried once and then
        # filed as a failure rather than written short.
        ents = job["entities"]
        up = build_prompt(job, chapter_tpl, front_tpl)
        # A FEATS CHAPTER DOES NOT USE THE ENTRY TEMPLATE, so it does not carry it (m46).
        # `system_style.txt` is two documents: ground rules and voice, then THE ENTRY TEMPLATE
        # with its Four Hands marginalia and The Instrument. A feats chapter writes none of
        # that, and `feats_prompt.txt` explicitly forbids the scoring The Instrument sets out.
        # Sending 11,149 characters of instruction that the user prompt then countermands was
        # not merely wasteful, it was contradictory -- and it was most of the overflow.
        import context_budget as _CBUD
        sysp = _CBUD.system_for("feats", system_prompt)
        text = call_ollama(cfg, sysp, up, "feats")
        lacking = [e for e in ents if not _covered(e.get("entity", ""), text)]
        if lacking or not text.strip():
            retry = call_ollama(cfg, sysp, up + (
                "\n\nYour previous attempt omitted these entities entirely; every listed "
                "entity must appear with its deeds: "
                + ", ".join(e.get("entity", "?") for e in lacking)), "feats")
            if retry.strip() and len(
                    [e for e in ents if not _covered(e.get("entity", ""), retry)]) < len(lacking):
                text = retry
                lacking = [e for e in ents if not _covered(e.get("entity", ""), text)]
        if not text.strip():
            raise RuntimeError("empty response on feats block")
        if lacking:
            raise RuntimeError("feats block omitted: "
                               + ", ".join(e.get("entity", "?") for e in lacking))
        # EVERY ENTITY APPEARING IS NOT EVERY DEED APPEARING. The name check above is what a
        # truncated block would still pass: the entities are listed early in the prompt and
        # their headings survive, while the tail of the deed list does not. Measured shortfall
        # is reported in the failure so the next reader gets the number, not a suspicion.
        traced, total, frac = _deed_shortfall(ents, text)
        if total and frac < DEED_TRACE_FLOOR:
            raise RuntimeError(
                f"feats block kept every entity heading but only {traced}/{total} deeds "
                f"({frac:.0%}) are traceable in the prose — below the {DEED_TRACE_FLOOR:.0%} "
                f"floor. A block that names its entities and drops their evidence is exactly "
                f"what a truncated prompt produces; check num_ctx against context_budget.")
        return text

    entries = job["entries"]
    groups = [entries[i:i + WRITE_CHUNK] for i in range(0, len(entries), WRITE_CHUNK)]
    parts, missing = [], []
    for gi, g in enumerate(groups):
        sub = dict(job, entries=g)
        if len(groups) > 1:
            sub["chapter_label"] = (f"{job['chapter_label']} — writing block {gi + 1} of "
                                    f"{len(groups)}")
        up = build_prompt(sub, chapter_tpl, front_tpl)
        if gi:
            up += ("\n\nThis is a CONTINUATION block of the same chapter: do not write "
                   "another framing paragraph, continue directly with the next ◈ entry.")
        text = call_ollama(cfg, system_prompt, up)
        lacking = [e for e in g if not _covered(e.get("name", ""), text)]
        if lacking or not text.strip():
            retry = call_ollama(cfg, system_prompt, up + (
                "\n\nYour previous attempt omitted these entries entirely; every listed entry "
                "must appear in full: " + ", ".join(e.get("name", "?") for e in lacking)))
            if retry.strip() and len([e for e in g if not _covered(e.get("name", ""), retry)]) \
                    < len(lacking):
                text = retry
                lacking = [e for e in g if not _covered(e.get("name", ""), text)]
        if not text.strip():
            raise RuntimeError(f"empty response on block {gi + 1}/{len(groups)}")

        # ======================= LAYER 4 — THE TRAIN'S OWN RESTRAINT CHECK ====================
        # `_covered()` above asked only whether each entity's NAME appears, which is exactly what
        # survives a generation that writes the first entries in full and then degrades into a
        # list. 902 of 1,268 entries in the withdrawn batch passed that check having silently
        # lost their Threads section. This inspects the prose the model actually returned against
        # the template it was asked for, and refuses a half-written block rather than shelving
        # it. A refusal is recoverable; a chapter filed as complete is not.
        import prose_gate as _PG
        _PG.assert_block_complete(text, len(g), f"block {gi + 1}/{len(groups)}")

        # LAYER 4b — an assay nobody earned. Hard Rule 3: band-only Magnitude, because the
        # decimals require a real worksheet against cited feats. An entity with no cited feat
        # that comes back carrying numeric axis scores has been given a number with nothing
        # under it, printed in the same shape as one that was earned.
        _cited = {e.get("name") for e in g if (e.get("feats") or e.get("cited"))}
        _unearned = _PG.unearned_instrument(text, _cited)
        if _unearned:
            raise RuntimeError(
                "block %d/%d printed Instrument axis scores for %d entit%s with no cited feat: "
                "%s. Hard Rule 3 forbids a fabricated assay, and a precise number is the most "
                "convincing thing a model can invent."
                % (gi + 1, len(groups), len(_unearned),
                   "y" if len(_unearned) == 1 else "ies", "; ".join(_unearned[:5])))

        parts.append(text.strip())
        missing.extend(e.get("name", "?") for e in lacking)
    if missing:
        raise RuntimeError(f"entries not written after retry: {', '.join(missing[:8])}"
                           + (f" (+{len(missing) - 8} more)" if len(missing) > 8 else ""))
    return "\n\n".join(parts)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--manifest", required=True)
    ap.add_argument("--limit", type=int, default=None, help="only run the first N pending jobs")
    ap.add_argument("--dry-run", action="store_true", help="build prompts but don't call Ollama")
    args = ap.parse_args()

    cfg = load_config()

    # ============================ LAYER 2 — THE MACHINE'S OWN INTERLOCK ========================
    # `overnight.py` also checks the gate. That is the control room, and it is not enough: it
    # governs only the supervisor's own launch. A hand-run, a keeper restart, a stale supervisor
    # still executing pre-gate code, or any future caller walks straight past it. This refusal
    # lives at the machine. It runs BEFORE the manifest is even loaded, so there is no path
    # through this program that reaches a model call without passing it.
    import prose_gate as PG
    try:
        why = PG.assert_gate_open(cfg)
    except PG.ProseRefused as e:
        print(str(e))
        print("nothing was generated. Open the gate in config.yaml if that is what you intend.")
        return 0
    print("prose gate: OPEN (%s)" % why)

    manifest = load_json(args.manifest, {"jobs": []})
    # Both manifest shapes are in the wild: manifest_builder writes {"jobs": [...]} and at
    # least one phase-8 path wrote a bare list -- the mismatch crash-looped the supervisor's
    # prose job on every keeper restart (2026-08-24, found via the published page's job
    # panel). Accept both, loudly note which arrived.
    if isinstance(manifest, list):
        print("note: manifest is a bare list (phase-8 writer); wrapping as jobs")
        jobs = manifest
    else:
        jobs = manifest.get("jobs") or []

    catalog = load_json(cfg["paths"]["catalog"], {})
    failures = load_json(cfg["paths"]["failures"], {})

    system_prompt, chapter_tpl, front_tpl = load_prompt_templates()
    prompt_version = cfg.get("prompt_version", "v1")
    model = cfg["model"]
    seed = cfg.get("seed", 47)

    # ============================ LAYER 3 — THE QUEUE LINE ====================================
    # A job that should never be written must not reach the platform at all. This is measured
    # ONCE per source and cached, then applied to every job of that source. It fails closed on an
    # unmeasured source, because "not in COVERAGE.json" is indistinguishable from "nothing has
    # ever been read here", and that is exactly the state the withdrawn batch was written from.
    floor = float(cfg.get("prose_min_cited_fraction", 0.35) or 0.0)
    try:
        cov_rows = PG._coverage_rows()
    except Exception as e:
        print("REFUSING EVERYTHING: data/COVERAGE.json unreadable (%s). The evidence floor "
              "cannot be applied, so no source can be shown to be worth writing."
              % type(e).__name__)
        return 0
    _ev_cache, refused_src = {}, {}

    pending = []
    stale_count = 0
    for job in jobs:
        src = job.get("source_name")
        if src not in _ev_cache:
            _ev_cache[src] = PG.evidence_ok(src, floor, cov_rows)
        ok_src, why_src = _ev_cache[src]
        if not ok_src:
            refused_src[src] = why_src
            continue
        rh = recipe_hash(job["address"], model, seed, prompt_version, job.get("content_hash", ""))
        cached = catalog.get(job["address"], {})
        if cached.get("recipe_hash") == rh:
            continue  # already generated from this exact source data, model, seed, and prompt
        if cached and cached.get("recipe_hash") != rh:
            stale_count += 1  # was generated before, but data/model/prompt changed since
        pending.append((job, rh))

    if refused_src:
        print("\nEVIDENCE FLOOR — %d source(s) held back at %.0f%% cited:"
              % (len(refused_src), 100 * floor))
        for s, w in sorted(refused_src.items(), key=lambda kv: str(kv[0]))[:20]:
            print("   %s" % w)
        if len(refused_src) > 20:
            print("   ... and %d more" % (len(refused_src) - 20))
        print("   These are NOT failures. They are sources the reader has not finished.\n")

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
        try:
            text = generate_job(cfg, system_prompt, job, chapter_tpl, front_tpl)
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
