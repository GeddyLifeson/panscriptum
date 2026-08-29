#!/usr/bin/env python3
"""INGEST_DOC — an owner-supplied text becomes library corpus.

THE STOREFRONT LOOP, CLOSED. FOR_OWNER.md has carried the same line for days: material that
exists and declines automated readers "can only be read if you supply the text." This module
is what happens when the owner supplies it. A PDF goes in; out come (1) the full cleaned text
as a page-keyed corpus under `data/docs/<slug>/`, (2) a `doc:<slug>` host registration so the
evidence pipeline reads it exactly the way it reads a wiki (the `pages:` sentinel's sibling —
a host that is not a host), and (3) an uncapped entity-extraction pass that merges every named
person, faction, place, thing, event, media item and power into the source's existing record.

HARD RULE 0 APPLIES. The whole document is extracted, the whole corpus is chunked, every chunk
is mined. The pass is resumable (per-chunk cursor in `ingest_state.json`, each chunk's finds
merged the moment they exist) because a 482-page book against an evening pool is hours of
calls — interruption must cost nothing, and a partial run must never look complete.

    python src/ingest_doc.py --pdf <path> --source "<record name>"          extract + register
    python src/ingest_doc.py --source "<record name>" --mine               entity pass (resumable)
"""
import argparse
import json
import os
import re
import sys
import time

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import silence                                                          # noqa: E402

_BAD_CHARS = (chr(8), chr(11), chr(12), chr(7))
if any(c in open(os.path.abspath(__file__), encoding="utf-8").read() for c in _BAD_CHARS):
    raise SystemExit(__file__ + ": a regex escape was eaten in transit.")

DOCS = os.path.join(HERE, "data", "docs")
HOSTS = os.path.join(HERE, "data", "WIKI_HOSTS.json")
RECORDS = os.path.join(HERE, "data", "records")

CHUNK = 9000            # characters per extraction call — the same altitude read.py mines at
CATEGORIES = [
    "Persons (named individual characters, real or fictional)",
    "Factions & Organizations (groups, nations, guilds, companies, orders)",
    "Places & Locations (worlds, regions, cities, planes, ships-as-places)",
    "Vessels & Things (items, vehicles, weapons, artifacts, notable objects)",
    "Events (major storyline events, wars, historical turning points within the fiction)",
    "Media (in-fiction media: books, songs, broadcasts, works that exist within the story itself)",
    "Powers, Abilities & Systems (magic systems, power systems, tech systems, disciplines)",
]

SYSTEM = (
    "You are cataloguing a fictional setting from the verbatim text of its own sourcebook. "
    "Extract EVERY named thing in the passage: persons, factions, places, items, events, "
    "in-fiction media, and powers/systems. Rules: (1) the description must be grounded ONLY "
    "in this passage — no outside knowledge, no invention; (2) skip real-world game mechanics "
    "(dice, saving throws, stat-block jargon, page references) and real people (authors, "
    "artists); (3) a name mentioned without any describable substance is still returned, with "
    "the little the passage gives; (4) skip nothing that is named. Return JSON only."
)

SCHEMA = {
    "type": "object",
    "properties": {"entries": {"type": "array", "items": {
        "type": "object",
        "properties": {
            "name": {"type": "string"},
            "type": {"type": "string"},
            "description": {"type": "string"},
            "scale_note": {"type": "string"},
            "category": {"type": "string", "enum": CATEGORIES},
        },
        "required": ["name", "type", "description", "category"]}}},
    "required": ["entries"],
}


def slug(source):
    return re.sub(r"[^a-z0-9]+", "-", source.lower()).strip("-")


def _clean(t):
    t = t.replace(chr(173), "")                       # soft hyphens litter print PDFs
    t = re.sub(r"(\w)-\n(\w)", r"\1\2", t)            # re-join hyphenated line breaks
    t = re.sub(r"[ \t]+", " ", t)
    return re.sub(r"\n{3,}", "\n\n", t).strip()


def extract(pdf_path, source):
    """PDF -> data/docs/<slug>/pages.json, page-keyed. The WHOLE document, every page.

    RAISES IF THE CORPUS DID NOT LAND (order e7b6dcc8d630). Everything else in this module
    reports a denied write and continues, because everything else has a next round; this one
    does not have the same shape. `main()` calls this, then `register()`, and registering
    points `WIKI_HOSTS` at `doc:<slug>` -- a host whose corpus is either absent or is the
    PREVIOUS extraction of a different book. Returning `out` on a denied replace also made the
    "extracted N pages" line true of memory and false of disk, and `mine()` reads the disk.
    The one exception to the module's own report-and-continue house style is deliberate: there
    is no useful "continue" from here, only a register-and-mine sequence built on a corpus that
    is not there. `main()` catches it and reports it as a refusal rather than a traceback.
    """
    import fitz
    doc = fitz.open(pdf_path)
    out = {}
    for i in range(len(doc)):
        t = _clean(doc[i].get_text())
        if t:
            out["p. %04d" % (i + 1)] = t
    d = os.path.join(DOCS, slug(source))
    os.makedirs(d, exist_ok=True)
    # ATOMIC: pages.json is the only machine copy of a book the library cannot re-fetch, read
    # by mine() and by the evidence pipeline through the doc: host. A bare open()+json.dump here
    # was a truncate-then-fill; a re-extract that died mid-dump would have destroyed the corpus
    # it was re-extracting, with nothing left to recover from.
    #
    # GATED: the sentence above is about a crash; a DENIED replace is the quiet version of the
    # same loss, and `write_json` reports it by returning False instead of raising.
    # The call is written out inline rather than through a `pages_p` local because
    # `handoff/run35/checks_L6.py::check_ingest_doc_extract_writes_pages_atomically` asserts on
    # this exact source text; hoisting the path broke a check whose intent this change keeps.
    if not silence.write_json(os.path.join(d, "pages.json"), out, indent=0, ensure_ascii=False):
        silence.note("ingest_doc.py:pages-write-denied")
        raise OSError("pages.json for %s could not be replaced (denied, most likely a reader "
                      "holding %s open) -- the extracted corpus did NOT land, so nothing may "
                      "be registered or mined against it."
                      % (source, os.path.join(d, "pages.json")))
    return out


def register(source):
    """Point the source at its document corpus — but never over a real wiki.

    -> the host string now recorded on disk, or None if the binding could not be written.
    The None is the point (order e7b6dcc8d630): this used to return `hosts[source]` -- the
    value it had just put in a local dict -- whether or not that dict ever reached the file,
    so `main()` printed `host=doc:<slug>` for a binding that existed only in this process. A
    host binding nothing else can see is the same as no binding at all.
    """
    with open(HOSTS, encoding="utf-8") as f:
        hosts = json.load(f)
    cur = hosts.get(source)
    if cur and not cur.startswith("doc:"):
        return cur                       # a live wiki outranks a static text; keep it
    hosts[source] = "doc:" + slug(source)
    # ATOMIC: feats.resolve_hosts and standards both read WIKI_HOSTS on their own clocks.
    # And BECAUSE they do, the replace can be denied at any moment -- which is exactly why the
    # verdict is returned rather than dropped. WIKI_HOSTS has lost a write silently once
    # already (silence.replace_if_unchanged's docstring, m42); the corpus is useless to the
    # evidence pipeline until this file names it.
    if not silence.write_json(HOSTS, hosts, indent=1, ensure_ascii=False, sort_keys=True):
        silence.note("ingest_doc.py:hosts-write-denied")
        return None
    return hosts[source]


def record_path(source):
    p = os.path.join(RECORDS, slug(source) + ".json")
    if os.path.exists(p):
        return p
    # The roll names sources long-form; records are slugged. Find by containment.
    want = slug(source)
    for fn in os.listdir(RECORDS):
        base = fn[:-5]
        if want in base or base in want:
            return os.path.join(RECORDS, fn)
    return p


def _ask(system, prompt, schema):
    """Pool first, local second — the house transport order."""
    try:
        import cascade_bridge as CB
        got = CB.ask(system, prompt, schema)
        if got is not None:
            return got
    except Exception:
        silence.note("ingest_doc.py:ask-cascade")
    try:
        import pipeline as P
        c = P.cfg()
        return P.ask({"model": c["model"], "ollama_host": c["ollama_host"], "seed": 47,
                      "num_ctx": c.get("num_ctx", 6144)}, system, prompt, schema,
                     timeout=420, tag="ingest")
    except Exception:
        silence.note("ingest_doc.py:ask-local")
        return None


def mine(source):
    """The uncapped entity pass, chunk by chunk, merged as it goes."""
    import pipeline as P
    d = os.path.join(DOCS, slug(source))
    with open(os.path.join(d, "pages.json"), encoding="utf-8") as f:
        pages = json.load(f)
    state_p = os.path.join(d, "ingest_state.json")
    try:
        with open(state_p, encoding="utf-8") as f:
            state = json.load(f)
    except Exception:
        silence.note("ingest_doc.py:ingest-state")
        state = {"next": 0, "found": 0}

    # Chunk on page boundaries so a citation's page label survives.
    #
    # A SINGLE PAGE LARGER THAN `CHUNK` IS RE-SPLIT, NOT EMITTED WHOLE (run #36). The
    # accumulator only ever flushed BEFORE appending, so a page bigger than CHUNK met an empty
    # `cur`, went in entire, and left as one oversize chunk -- 12,608 characters against a 9,000
    # budget in the one document ingested so far, and print sourcebooks are full of full-bleed
    # text pages. The transport does not refuse an overlong prompt; it silently reads the head
    # of it against a fixed num_ctx, so the tail of that page is catalogued as containing no
    # named things. `read.py:_local_carded` already faced exactly this and answers it exactly
    # this way -- `for i in range(0, len(body), CHUNK)` over the oversized body -- so this
    # mirrors it rather than inventing a second rule.
    #
    # SPLITTING ONLY ADDS BOUNDARIES, so chunk `k` under this scheme begins at or before where
    # chunk `k` began under the old one, and a resume cursor written by an earlier run can only
    # RE-read text, never skip past it -- checked against the one live corpus rather than
    # asserted: 252 chunks became 262, no chunk's start moved forward, and the Arcanum Worlds
    # ingest's cursor of 81 lands on the identical document offset (the first oversize page in
    # that book is p. 0471, well past it).
    chunks, cur, cur_pages = [], "", []
    for label in sorted(pages):
        body = pages[label]
        if len(body) > CHUNK:
            if cur:
                chunks.append((cur, list(cur_pages)))
                cur, cur_pages = "", []
            for i in range(0, len(body), CHUNK):
                chunks.append(("[" + label + "]\n" + body[i:i + CHUNK] + "\n\n", [label]))
            continue
        if cur and len(cur) + len(body) > CHUNK:
            chunks.append((cur, list(cur_pages)))
            cur, cur_pages = "", []
        cur += "[" + label + "]\n" + body + "\n\n"
        cur_pages.append(label)
    if cur:
        chunks.append((cur, cur_pages))

    rp = record_path(source)
    with open(rp, encoding="utf-8") as f:
        rec = json.load(f)

    def _key(n):
        return re.sub(r"[^a-z0-9]", "", (n or "").lower())

    known = {_key(e.get("name")) for e in rec.get("entries", [])}
    print("%s: %d chunks, resuming at %d, %d entries already known"
          % (source, len(chunks), state["next"], len(known)))

    misses = 0
    ci = state["next"]
    while ci < len(chunks):
        text, chunk_pages = chunks[ci]
        got = _ask(SYSTEM, "PASSAGE (%s):\n\n%s" % (", ".join(chunk_pages), text), SCHEMA)
        if got is None:
            # PATIENCE, NOT ABANDONMENT. Against an evening pool the first launch of this
            # died on chunk 1 of 252 -- an honest stop, but a 5-minute nap and another try is
            # what the free-tier tide actually calls for; the midnight window reset feeds it.
            # Sixty consecutive misses (~5 hours) outlasts any daily-window drought;
            # only something structural survives that long, and THEN it stops.
            misses += 1
            if misses >= 60:
                print("  chunk %d/%d: 60 consecutive misses (~5h); stopping (resumable)"
                      % (ci + 1, len(chunks)))
                break
            print("  chunk %d/%d: no transport; napping 300s (miss %d/60)"
                  % (ci + 1, len(chunks), misses))
            time.sleep(300)
            continue
        misses = 0
        fresh = []
        for e in (got.get("entries") or []):
            if not isinstance(e, dict) or not (e.get("name") or "").strip():
                continue
            k = _key(e["name"])
            if k in known:
                continue
            known.add(k)
            fresh.append({
                "name": e["name"].strip(), "type": (e.get("type") or "").strip(),
                "description": (e.get("description") or "").strip()[:2000],
                "scale_note": (e.get("scale_note") or "").strip(),
                "category": e.get("category") if e.get("category") in CATEGORIES
                else CATEGORIES[0],
                "wiki_page": "", "attestation": "Transcribed", "magnitude": "unassayed",
                "doc_pages": chunk_pages,
                "origin_work": source,
            })
        if fresh:
            with open(rp, encoding="utf-8") as f:
                rec = json.load(f)
            rec.setdefault("entries", []).extend(fresh)
            # write_record_CATALOGUE, not write_record: this is a cast-growing writer, and
            # write_record's disk-wins merge DISCARDED the first 14 entities this module ever
            # found (2026-08-23, caught within minutes because found-count and record-count
            # disagreed). Each side of the two-writer contract has its own writer; this is
            # the catalogue side.
            # ADVANCE ON THE WRITE, NOT ON THE INTENT. `write_record_catalogue` returns whether
            # the rename actually landed (`pipeline._landed`) precisely because on Windows it
            # can be denied while a reader holds the file, and it never raises -- so discarding
            # the result advanced the resume cursor past entities that were never saved. The
            # cursor is the only record of what has been done, so that loss is permanent and
            # silent: this is the same shape as the 378 stranded entries phase 2 already paid
            # for, and the same shape as the 5 doc-ingested entries this module stranded in
            # Arcanum Worlds. It compounds inside one run too -- `known` had already absorbed
            # the names, so a later chunk mentioning the same entity would skip it as
            # "already known" when nothing had ever been written.
            #
            # A denied write therefore rewinds `known` and stops the run WITHOUT moving the
            # cursor. Nothing is lost; the next run resumes on this chunk. (2026-08-23.)
            if not P.write_record_catalogue(rp, rec):
                for e in fresh:
                    known.discard(_key(e["name"]))
                print("  chunk %d/%d: record write denied; stopping without advancing "
                      "(resumable)" % (ci + 1, len(chunks)))
                break
            state["found"] += len(fresh)
        state["next"] = ci + 1
        # Atomic, like every other resume cursor in this project: a crash between `open` and
        # `json.dump` left a zero-byte state file, which `mine()` reads as "start from chunk 0".
        tmp_state = state_p + ".tmp"
        with open(tmp_state, "w", encoding="utf-8") as f:
            json.dump(state, f)
        # THE CURSOR MAY LAG; IT MAY NEVER LEAD. That asymmetry is why this denial is reported
        # rather than acted on (order e7b6dcc8d630). A denied cursor write leaves `state[next]`
        # on disk BEHIND the work already merged into the record -- the safe direction, and the
        # same direction the `write_record_catalogue` gate twenty lines up is protecting: next
        # run rebuilds `known` from the record itself and skips every entity already there, so
        # nothing is lost and nothing is duplicated. Stopping here would abandon chunks that
        # are landing correctly, so the loop continues.
        #
        # What is NOT free is the silence. This module naps 300s per miss and runs for hours
        # against a free-tier tide; a persistently denied cursor means the whole run's progress
        # is unrecorded and the next run re-asks the model for every chunk of it. That is a
        # bill the operator should see arriving, not discover.
        if not silence.replace_retry(tmp_state, state_p):
            silence.note("ingest_doc.py:cursor-write-denied")
            print("  chunk %d/%d: resume cursor NOT advanced on disk (write denied); the "
                  "entries above are saved, but a rerun will re-ask every chunk since the "
                  "last cursor that landed" % (ci + 1, len(chunks)))
        if (ci + 1) % 10 == 0 or fresh:
            print("  chunk %d/%d  +%d new  (%d total this ingest)"
                  % (ci + 1, len(chunks), len(fresh), state["found"]))
        ci += 1
    if ci >= len(chunks):
        print("ingest complete: %d new entries merged" % state["found"])
        return True
    return False


def main():
    ap = argparse.ArgumentParser(description="owner-supplied text -> library corpus")
    ap.add_argument("--pdf", help="path to the supplied PDF")
    ap.add_argument("--source", required=True, help="the source's roll/record name")
    ap.add_argument("--mine", action="store_true", help="run the entity pass (resumable)")
    a = ap.parse_args()

    if a.pdf:
        try:
            pages = extract(a.pdf, a.source)
        except OSError as e:
            # The one refusal in this module, and it stops the sequence rather than reporting
            # and carrying on: registering a host or mining entities against a corpus that did
            # not land would build on a book that is not there. Reported as a message and a
            # non-zero exit, not a traceback. (order e7b6dcc8d630)
            print("EXTRACT FAILED: %s" % e)
            return 1
        host = register(a.source)
        if host is None:
            # The corpus landed; the pointer to it did not. Said plainly, because the corpus is
            # invisible to `feats.resolve_hosts` until WIKI_HOSTS names it, and re-running with
            # the same --pdf is the whole repair.
            print("extracted %d pages (%d chars) -> data/docs/%s/  but the WIKI_HOSTS write "
                  "was DENIED: the source is NOT yet bound to doc:%s and nothing will read the "
                  "corpus until it is. Rerun to retry."
                  % (len(pages), sum(len(v) for v in pages.values()), slug(a.source),
                     slug(a.source)))
            return 1
        print("extracted %d pages (%d chars) -> data/docs/%s/  host=%s"
              % (len(pages), sum(len(v) for v in pages.values()), slug(a.source), host))
        # Provenance is part of the record the moment the corpus exists.
        rp = record_path(a.source)
        try:
            with open(rp, encoding="utf-8") as f:
                rec = json.load(f)
            note = (" Full text of the print sourcebook supplied by the owner on "
                    + time.strftime("%Y-%m-%d") + " and ingested by src/ingest_doc.py; the "
                    "doc:%s corpus is the book itself, page-keyed." % slug(a.source))
            if "ingest_doc" not in (rec.get("provenance") or ""):
                rec["provenance"] = (rec.get("provenance") or "") + note
                import pipeline as P
                # ADVANCE ON THE WRITE, NOT ON THE INTENT (same discipline this file argues for
                # at 233-245 re: write_record_catalogue): write_record returns whether the
                # rename actually landed and never raises, so a denied write must not be read as
                # a success. The "ingest_doc" guard above makes a re-run retry this note anyway,
                # but the operator should see the denial rather than a false "extracted" line.
                if not P.write_record(rp, rec):
                    print("  provenance note not landed (write denied; will retry next run)")
        except Exception:
            silence.note("ingest_doc.py:provenance")
    if a.mine:
        mine(a.source)
    return 0


if __name__ == "__main__":
    sys.exit(main())
