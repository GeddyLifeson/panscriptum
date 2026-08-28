#!/usr/bin/env python3
"""
HEALTH — make failures loud, because every bug in this project has been a quiet one.

THE PATTERN
-----------
Eleven separate defects were found in one day. Listed as a list they look like bad luck. Lined
up by SHAPE they are one defect:

    Wikipedia served 404              ->  looked like "these entities have no page"
    chunks overflowed num_ctx         ->  looked like "the model fabricates 51% of the time"
    a word-boundary escape became 0x08 ->  looked like "the gate is too strict"
    a batch closed on write not result ->  looked like "judged"
    failed synthesis wrote an empty block -> looked like "no ceiling exists here"
    the gate could only see Ruin       ->  looked like "no evidence on ten axes"

Every layer converts a failure into a plausible NEGATIVE RESULT. Nothing raises, nothing counts,
and so every one of them costs a full investigation to tell "broken" apart from "genuinely
empty". There are 45 bare `except Exception` handlers in this tree, and that number is the real
bug; the eleven were its output.

WHAT THIS DOES
--------------
Two things, neither of which requires rewriting those 45 handlers:

  A LEDGER. The transport layer records why a call failed instead of only that it did. A run
  that 404s 5,590 times now says so at the end rather than reporting 5,590 honest absences.

  A PREFLIGHT. Cheap assertions, run BEFORE a job commits hours, aimed at the exact classes of
  fault already seen: does the context arithmetic hold, does each host family answer on the API
  path we use for it, is any module carrying a control character where an escape should be, is
  a cache systematically empty in a way that means broken rather than absent.

The preflight would have caught the Wikipedia path, the chunk overflow and every escape
corruption before they cost a day each.
"""
import argparse
import collections
import glob
import json
import os
import sys
import threading
import time

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Imported AFTER the path insert, and safe despite the apparent cycle: silence.py imports health
# only lazily, inside note() and its instrumenter, never at module scope.
import silence                                                          # noqa: E402

_BAD_CHARS = (chr(8), chr(11), chr(12), chr(7))
if any(c in open(os.path.abspath(__file__), encoding="utf-8").read() for c in _BAD_CHARS):
    raise SystemExit(__file__ + ": a regex escape was eaten in transit.")

# A feats record with no pages serialises to roughly 200 bytes; one with a single
# page runs to kilobytes. Anything under this threshold held nothing.
EMPTY_BYTES = 400

# Where the preflight leaves its verdict for `workorders.sweep_detectors` to read. See
# `preflight()` for why a check that only prints is a check the queue cannot act on.
PREFLIGHT_STAMP = os.path.join(HERE, "state", "preflight_last.json")

LEDGER = collections.Counter()
_LOCK = threading.Lock()
LEDGER_PATH = os.path.join(HERE, "state", "failures.json")


SAMPLES_PATH = os.path.join(HERE, "state", "failure_samples.json")
_SAMPLES = {}
SAMPLES_KEEP = 3


def record(kind, detail="", sample=None):
    """Note a failure by CLASS. The class is what makes a pattern visible; the instance does
    not -- but a class with NO instance on file costs a grep and a reproduction every time it
    is diagnosed, so the last few concrete examples ride along in a small ring beside the
    counts. Counts are the ledger; samples are the evidence bag."""
    with _LOCK:
        key = f"{kind}:{detail}" if detail else kind
        LEDGER[key] += 1
        if sample:
            ring = _SAMPLES.setdefault(key, [])
            ring.append({"at": time.strftime("%Y-%m-%d %H:%M:%S"), "sample": str(sample)[:240]})
            del ring[:-SAMPLES_KEEP]


def flush():
    if not LEDGER:
        return
    os.makedirs(os.path.dirname(LEDGER_PATH), exist_ok=True)
    prev = {}
    if os.path.exists(LEDGER_PATH):
        try:
            with open(LEDGER_PATH, encoding="utf-8") as f:
                prev = json.load(f)
        except Exception as e:
            # An unreadable ledger must not be quietly replaced by an empty one -- that would
            # make the failure-recorder itself the sixteenth instance of the defect it exists
            # to expose. Keep the corrupt file and say so.
            #
            # THE PRESERVATION WAS A BARE `os.replace` WITH NOTHING AROUND IT. On Windows the
            # rename is DENIED while any reader holds failures.json open -- the WinError 5 class
            # `silence.replace_retry` exists for, and this is the highest-traffic shared file in
            # the project, polled by the dashboard and read by standards. `flush()` is armed via
            # `atexit` by `silence.note`, so a PermissionError here escapes an atexit handler:
            # the recorder's own self-heal becomes the crash. Same treatment the samples ledger
            # beside it already has.
            #
            # PRESERVATION IS THE PRECONDITION, NOT A COURTESY. If the wreck cannot be set
            # aside, this flush writes NOTHING: overwriting an unreadable ledger we could not
            # first preserve would destroy the only copy of whatever tore it. LEDGER is left
            # intact so the counts are still in memory for the next flush attempt.
            if not silence.replace_retry(LEDGER_PATH, LEDGER_PATH + ".corrupt"):
                print(f"health: ledger unreadable ({type(e).__name__}) AND could not be set "
                      f"aside as failures.json.corrupt (rename refused) -- refusing to write "
                      f"over it; counts kept in memory for the next flush", file=sys.stderr)
                return
            prev = {"ledger:unreadable": 1}
            print(f"health: ledger unreadable ({type(e).__name__}); "
                  f"kept as failures.json.corrupt", file=sys.stderr)
    for k, v in LEDGER.items():
        prev[k] = prev.get(k, 0) + v
    # ATOMIC, and this is the write that most needed to be. foreman.py:237 already says it:
    # "state/failures.json is the highest-traffic shared file in the project -- the dashboard
    # polls it, standards reads it, and EVERY process read-modify-writes it through
    # health.flush()." m18 (2026-08-24) then hardened foreman's OWN three writes and left the
    # writer that sentence names untouched -- the canonical one, called every 25 records and
    # again at exit, from every one-shot subprocess in the kit.
    #
    # A bare open("w") truncates BEFORE serialising, so an interrupted flush leaves 0 bytes.
    # The corrupt-read branch above then does exactly what it promises: preserves the wreck as
    # .corrupt and starts a fresh ledger -- discarding the entire accumulated failure history
    # the file exists to hold. The recorder must not become the sixteenth instance of the
    # defect it exists to expose, and that principle has to cover the WRITE as well as the read.
    #
    # LEDGER is cleared only if the write LANDED. A denied replace (Windows, reader holding
    # the file) otherwise silently discarded the counts it failed to persist.
    #
    # THE FIXED `.tmp` NAME WAS ITSELF A HAZARD, on the single highest-traffic shared file in
    # the project (foreman.py:237 above). Two writers flushing at the same moment -- a targeted
    # investigation racing the scheduled cycle, which is the normal case here, not an exotic one
    # -- both open `failures.json.tmp` for writing; the second truncates the first, and
    # whichever renames second lands a half-written file over the target. That is the exact
    # interleaved-writer shape found this run: `failures.json.corrupt` held a valid 102-byte
    # document followed by 38 bytes of a longer, older one -- two writers, not one truncated
    # write. `silence.write_json` puts pid and thread in the temp name so two writers cannot
    # meet there, and returns the same landed/not-landed verdict this already gated on. (found
    # and fixed run36, not itself a filed order -- see handoff/run36/crossmodule_local06.md)
    if silence.write_json(LEDGER_PATH, prev, indent=1, sort_keys=True):
        LEDGER.clear()
    if _SAMPLES:
        try:
            old = {}
            if os.path.exists(SAMPLES_PATH):
                try:
                    with open(SAMPLES_PATH, encoding="utf-8") as f:
                        old = json.load(f)
                except Exception as e:
                    # THE SELF-HEALING PATH THE COMMENT BELOW HAS BEEN ASKING FOR SINCE IT WAS
                    # WRITTEN. It described this exact hole -- a torn SAMPLES_PATH sends every
                    # future flush into the blanket `except` at THIS read, so the evidence bag
                    # goes quietly empty and stays that way for ever, with nothing recorded
                    # anywhere -- and then did not close it. A described, never-implemented fix
                    # is indistinguishable at runtime from no fix at all, and this is the
                    # recorder: it is the one component whose silent failure hides every other
                    # component's failure. So the ledger's own treatment, applied here: keep the
                    # wreck as SAMPLES.json.corrupt, say so on stderr, and carry on with a fresh
                    # bag rather than reading a corpse on every flush from now on.
                    #
                    # PRESERVATION IS THE PRECONDITION, NOT A COURTESY. If the rename does not
                    # land -- Windows, a reader holding the file, the WinError 5 class
                    # `replace_retry` exists for -- the original exception is re-raised into the
                    # blanket `except` below and this flush drops its samples exactly as it did
                    # before. That is the old behaviour and it is the safe one: overwriting an
                    # unreadable evidence file we could not first set aside would destroy the
                    # only copy of whatever tore it. (run33)
                    if not silence.replace_retry(SAMPLES_PATH, SAMPLES_PATH + ".corrupt"):
                        raise
                    old = {}
                    print(f"health: failure samples unreadable ({type(e).__name__}); "
                          f"kept as {os.path.basename(SAMPLES_PATH)}.corrupt, starting fresh",
                          file=sys.stderr)
            for k, ring in _SAMPLES.items():
                merged = (old.get(k) or []) + ring
                old[k] = merged[-SAMPLES_KEEP:]
            # Same treatment, and this file needs it MORE than the ledger does, not less: it
            # has no .corrupt self-healing path. Once torn, every future flush hits the blanket
            # `except` below at the read step and drops its samples silently and permanently --
            # the evidence bag going quietly empty and staying that way, with nothing recorded
            # anywhere, because the recorder cannot safely record against itself.
            #
            # SAME FIXED-`.tmp`-NAME HAZARD AS THE LEDGER WRITE ABOVE, same fix: `write_json`'s
            # pid+thread temp name is unavailable for two concurrent flushes to collide on, where
            # a shared `path + ".tmp"` was not. (found and fixed run36)
            if silence.write_json(SAMPLES_PATH, old, indent=1, sort_keys=True, ensure_ascii=False):
                _SAMPLES.clear()
        except Exception:
            pass          # the evidence bag must never break the ledger write


def summary():
    """The failure ledger as it stands. -> {class: count}.

    THE ONE READER OF failures.json IN THIS FILE THAT COULD NOT SURVIVE READING IT. `flush()`
    twenty lines up treats a torn ledger as a preserve-and-report case, and both external readers
    (dashboard.py:331-339, standards.py:797-800) wrap the read; this one had nothing around it,
    so a `--failures` run against the exact fault the file exists to record -- an interrupted
    write leaving 0 bytes -- died with a JSONDecodeError instead of reporting anything.
    Deliberately NOT returning `{}`: main() prints "no failures recorded" for an empty summary,
    and answering "could not read the ledger" with "there are no failures" is the reporting
    failure this module was written to expose. The unreadable state is itself a recorded class,
    spelled the same way `flush()` spells it, so it shows up in the count table as a row.
    """
    if os.path.exists(LEDGER_PATH):
        try:
            with open(LEDGER_PATH, encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            silence.note("health.py:summary")
            print(f"health: failure ledger unreadable ({type(e).__name__}) -- "
                  f"the counts below are not the ledger", file=sys.stderr)
            return {"ledger:unreadable": 1}
    return {}


# --------------------------------------------------------------------------- preflight

def check_control_chars():
    """A regex escape eaten in transit. Six occurrences so far, every one silent."""
    bad = []
    for p in sorted(glob.glob(os.path.join(HERE, "src", "*.py"))):
        with open(p, encoding="utf-8") as f:
            src = f.read()
        hits = sum(src.count(c) for c in _BAD_CHARS)
        if hits:
            bad.append((os.path.basename(p), hits))
    return bad


def check_context_budget():
    """Does the chunk actually fit the window it is sent to?

    Ollama does not refuse an overlong prompt, it truncates silently -- so this is arithmetic
    nobody is told they got wrong. English wiki prose runs ~3.7 characters per token.
    """
    try:
        import read as R
        cfg = R.config()
    except Exception as e:
        return [("read.py config unreadable", str(e)[:60])]
    ctx = cfg.get("num_ctx", 6144)
    sys_toks = len(R.SYSTEM) / 4
    body_toks = R.CHUNK / 3.7
    reply = 700
    total = sys_toks + body_toks + reply
    if total > ctx:
        return [("chunk overflows context",
                 f"{int(total)} tokens needed vs num_ctx {ctx} "
                 f"(CHUNK={R.CHUNK} chars) - the tail is silently truncated")]
    return []


def check_api_paths():
    """One live call per host FAMILY, on the path that family is actually served from.

    Fandom answers at /api.php and Wikipedia at /w/api.php. Using one for the other returns 404,
    which the transport swallows into None, which reads as 'no page'. That cost 5,590 entries
    across nineteen sources and looked exactly like an honest absence.
    """
    out = []
    try:
        import feats as F
        hosts = json.load(open(F.HOSTS, encoding="utf-8"))
    except Exception as e:
        return [("host map unreadable", str(e)[:60])]
    fams = {}
    for h in hosts.values():
        if not h:
            continue
        # `pages:` and `doc:` are sentinels, not hosts -- probing them as a "fandom family
        # member" produced a false API-unreachable alarm on every preflight (found 2026-08-23).
        if h.startswith("pages:") or h.startswith("doc:"):
            continue
        fams.setdefault("wikipedia" if "wikipedia" in h else "fandom", h)
    for fam, host in fams.items():
        d = F.api(host, {"action": "query", "meta": "siteinfo"}, retries=0)
        if not d or "query" not in d:
            out.append((f"{fam} API unreachable", host))
    return out


def check_caches():
    """A cache that is systematically empty means broken, not absent.

    An empty entry is normal. An entire host directory of empty entries is the 404 signature.

    A QUARANTINED HOST IS NOT REPORTED AGAIN HERE. `binding_health` already holds the fault, with
    the canary detail that diagnosed it, and `workorders` files one HOST_QUARANTINED order per
    host from that record -- so a host like www.dandwiki.com, whose API answers 403 to everyone
    who is not logged in, would otherwise sit red in this preflight for ever with no action that
    could ever clear it. A permanent red is not extra safety; it is how a preflight stops being
    read. The host is still PRINTED below, so it cannot vanish silently -- what changes is that
    it no longer counts as a fresh problem the preflight is asking somebody to fix. (run #33)
    """
    out = []
    try:
        import binding_health as _BH
        import cachekey as _CK
        # THE CACHE DIRECTORY IS NOT THE HOST NAME. `cachekey.host_dir()` is the ONE formula
        # that actually builds a host's directory under data/feats -- `_SANITISE.sub("_", host)
        # [:HOST_CAP]`, folding every RUN of punctuation to a single underscore and capping at
        # 40 chars. A hand-spelled `.replace(".","_").replace("-","_")` here diverges from that
        # for punctuation outside ./- and for hosts over 40 chars, which would have made this
        # whole exemption a no-op that still LOOKS implemented -- the failure mode this project
        # calls a check that cannot fail. Same fix as hostcheck.py's purge path (order
        # 5159320dd758): call the shared helper instead of re-spelling it a third way.
        # (order d7a7bbb70bf1)
        quarantined = {_CK.host_dir(h) for h in _BH.quarantined()}
    except Exception:
        # FAIL LOUD, NOT QUIET. If the quarantine record cannot be read we do not know that a
        # host is excused, so nothing is excused and every empty cache reports as before.
        quarantined = set()
    excused = []
    for base in ("feats", "readfeats"):
        root = os.path.join(HERE, "data", base)
        if not os.path.isdir(root):
            continue
        for host in sorted(os.listdir(root)):
            files = glob.glob(os.path.join(root, host, "*.json"))
            if len(files) < 25:
                continue
            # SIZE, NOT PARSE. Preflight runs at the head of every supervisor cycle, and
            # parsing 200 records for each of 147 hosts meant reading gigabytes of page text to
            # answer a question about emptiness. It pushed a cycle past five minutes before any
            # work began. An entry with no pages is a few hundred bytes; one with pages is
            # kilobytes at least. The file size answers this exactly, and instantly.
            empty = 0
            unreadable = 0
            for fp in files[:200]:
                try:
                    if os.path.getsize(fp) < EMPTY_BYTES:
                        empty += 1
                except OSError:
                    unreadable += 1
            if unreadable:
                out.append((f"{base}/{host} cache unreadable",
                            f"{unreadable} files cannot be stat'd"))
            n = min(len(files), 200)
            if empty == n:
                if host in quarantined:
                    excused.append(f"{base}/{host} ({n})")
                else:
                    out.append((f"{base}/{host}", f"all {n} sampled entries empty"))
    if excused:
        # PRINTED, NOT RETURNED -- the same discipline as the re-judgement queue below: visible
        # every run, but not counted as a problem the preflight is asking anyone to act on.
        print("  info  empty caches on QUARANTINED hosts (fault held by binding_health, "
              "not re-reported here): " + ", ".join(sorted(excused)))
    return out


def check_state():
    """Batches recorded complete that are not, and failures recorded that are not."""
    out = []
    try:
        import pipeline as P
        st = json.load(open(os.path.join(HERE, "state", "PIPELINE_STATE.json"),
                            encoding="utf-8"))
    except Exception as e:
        return [("state unreadable", str(e)[:60])]
    # NAME THE SOURCES, NOT JUST THE COUNT. A bare `227` says a number is wrong and nothing
    # about where to look, so the next run re-derives the breakdown by hand before it can even
    # start diagnosing -- run #27 did exactly that, and the answer took one query: all 227 sat
    # in ONE source. A count that is spread over forty sources and a count that is one source
    # growing are different faults with different remedies, and this line could not tell them
    # apart.
    #
    # WHY ENTRIES STRAND, since the breakdown makes it visible: the done-marker is
    # `source#startIndex` -- a POSITIONAL key over a list that the cast-growing side mutates.
    # Close `Gundam#0` over entries 0-19, let a cataloguer insert or re-sort entries, and that
    # same key now claims a different twenty. The entries that slid into a closed range are
    # never entrypassed again, because nothing re-opens a batch. Appending alone is harmless
    # (new entries land in new, unclosed ranges); insertion and re-ordering are not.
    #
    # Deliberately still just a REPORT. Re-keying the marker by content would invalidate every
    # done-marker on disk and re-run entrypass across the corpus -- real model spend on a pool
    # that is currently the binding constraint -- so it is an owner ruling, in NEXT_STEPS.
    # (run #27)
    # "STRANDED" WAS THE OLD BUG'S NAME, AND IT OUTLIVED THE BUG (measured 2026-08-25).
    #
    # This counted entries lacking `catalogued` inside a span whose key is in `done_keys`, and
    # called them stranded -- a word that means PERMANENTLY LOST, and did mean that once: a batch
    # closed on WRITE rather than on RESULT and 378 entries never came back. `reopen_stranded()`
    # below exists to repair that era.
    #
    # `batch_settled()` fixed it. It re-derives the span from the LIVE entry list and requires
    # every entry in it to be settled, so a batch that acquires an unjudged entry after closing
    # fails the gate and is reprocessed. Verified against the live corpus: of the 874 entries this
    # check was reporting, **874 reopen and 0 are unreachable.**
    #
    # So the number is a BACKLOG -- work queued behind entrypass's throughput -- and reporting it
    # as loss sent four consecutive runs chasing data that was never lost, and put it in the
    # owner's ruling queue as "ACCELERATING". It is accelerating because the catalogue is growing
    # faster than the judge can keep up, which is a throughput finding (M19/M35), not a defect.
    #
    # THERE IS NO SEPARATE REACHABILITY QUESTION LEFT TO ASK HERE (found run35, batch 6). An
    # earlier version of this function believed there was one: for a key already in `done`, it
    # called `P.batch_settled(key, done, batch)` a second time to ask whether the resume gate
    # would (wrongly) skip the batch and strand its unsettled entries forever. But by the time
    # this loop reaches that call it already knows `key in done` (the `continue` two lines above
    # requires it) AND that the batch is NOT fully settled (the `continue` right above requires
    # `n >= 1`) -- and `batch_settled` is exactly `key in done and all(entry_settled(e) for e in
    # batch)`. Both of its inputs are therefore already pinned to the one combination where it
    # answers False, so the "unreachable" branch could never fire: `lost` stayed 0 and
    # `lost_where` stayed empty on every run, which happens to be the true answer (874 reopen, 0
    # ever unreachable) but was never actually being tested for. The real reachability guarantee
    # lives one level up, in `phase_entrypass`'s own resume gate sharing this identical
    # predicate: a batch that acquires an unjudged entry after closing fails that gate too and
    # gets reprocessed, so nothing entrypass marks `done` can go permanently unjudged under the
    # current design. What is left to report here is only ever the backlog.
    done = set(st.get("done", {}).get("entrypass", []))
    B = P.ENTRY_BATCH
    queued = 0
    per_source = {}
    for _, r in P.records():
        E = r["entries"]
        for start in range(0, len(E), B):
            key = f"{r['source']}#{start}"
            if key not in done:
                continue
            batch = E[start:start + B]
            # THROUGH THE SHARED PREDICATE, never re-spelled. This used to read
            # `not e.get("catalogued") and not e.get("excluded")` -- correct, and correct by
            # coincidence: it was a second hand-written copy of the rule that
            # `pipeline.entry_settled` exists to be the only copy of. Run #20's ruling on the
            # struck-entry incident was explicit that the repair "was not the missing clause,
            # it was collapsing the rule into ONE predicate ... so they cannot drift again",
            # and a copy that happens to agree today is exactly what drift looks like the day
            # before it stops agreeing. (run33)
            n = sum(1 for e in batch if not P.entry_settled(e))
            if not n:
                continue
            queued += n
            per_source[r["source"]] = per_source.get(r["source"], 0) + n
    if queued:
        # EVERY source, worst first -- not a sample. The whole point is to see the shape.
        # Reported, but NOT as a problem: this is the judge's queue depth, and it is the honest
        # measure of how far entrypass is behind the catalogue.
        where = ", ".join("%s %d" % (s, n) for s, n in
                          sorted(per_source.items(), key=lambda kv: -kv[1]))
        # PRINTED, NOT RETURNED. Everything in `out` is rendered as a FAIL by the preflight, and
        # a queue depth is not a fault -- reporting it as one is what put this in the owner's
        # ruling queue. It still has to be VISIBLE, though: an unreported backlog is how a judge
        # falling permanently behind would look exactly like a judge keeping up.
        print("  info  entries awaiting re-judgement (queued, NOT lost): %d (%s)"
              % (queued, where))
    stale = 0
    for src in st.get("failed", {}).get("synthesis", {}):
        rec = next((r for _, r in P.records() if r["source"] == src), None)
        if rec and (rec.get("synthesis") or {}).get("ceiling_entity"):
            stale += 1
    if stale:
        out.append(("failures recorded that already succeeded", str(stale)))
    return out


def reopen_stranded(dry=True):
    """Re-open entry batches marked done that still contain uncatalogued entries.

    A batch once closed on WRITE rather than on RESULT, which stranded 378 entries permanently:
    the key said done, the entries said uncatalogued, and nothing in the pipeline ever looked at
    both. The write bug is fixed; this clears what it left behind, and stays because the same
    shape can recur any time a stage is interrupted between its work and its bookkeeping.

    Removing a key only causes rework. Nothing is deleted and nothing is fabricated -- the batch
    simply becomes eligible again.
    """
    import pipeline as P
    path = os.path.join(HERE, "state", "PIPELINE_STATE.json")
    try:
        with open(path, encoding="utf-8") as f:
            st = json.load(f)
    except Exception as e:
        # Say which of the two it is. This tool's whole job is repairing PIPELINE_STATE.json, so
        # "cannot read it" is the one message it must never deliver as a bare traceback -- and an
        # absent file and a torn one call for opposite responses (run it later vs. restore it).
        print(f"health: PIPELINE_STATE.json unreadable ({type(e).__name__}: {e}); "
              f"nothing re-opened", file=sys.stderr)
        return []
    done = st.get("done", {}).get("entrypass", [])
    doneset = set(done)
    B = P.ENTRY_BATCH
    reopen, entries = [], 0
    for _, r in P.records():
        E = r["entries"]
        for start in range(0, len(E), B):
            key = f"{r['source']}#{start}"
            if key not in doneset:
                continue
            # A STRUCK ENTRY IS NOT STRANDED WORK, AND THIS COUNT USED TO SAY IT WAS. The test
            # here was `not e.get("catalogued")`, which is the pre-2026-08-24 gate verbatim --
            # the one whose removal `pipeline.batch_settled` documents at length. `cleanup.py`
            # strikes wiki-navigation cruft and description-less rules constructs by setting
            # `catalogued = False` and writing an `excluded` reason, so a struck entry NEVER
            # becomes catalogued no matter how often its batch is reprocessed. Under the old
            # test every batch holding one was permanently "stranded": `--reopen --go` would
            # reopen it, `phase_entrypass` would set `catalogued = True` unconditionally, and
            # the exclusion would be reverted. That is not a hypothetical -- measured
            # 2026-08-24, 149 entries carried `excluded` and all 149 had already been flipped
            # back, which is cleanup's entire effect on the corpus undone. This repair tool was
            # still holding the loop open by itself while `check_state()` twenty lines above
            # correctly called the same batches settled. Both now ask `pipeline.entry_settled`,
            # which is the single copy of the rule and the reason the two cannot disagree
            # again. (run33)
            missing = sum(1 for e in E[start:start + B] if not P.entry_settled(e))
            if missing:
                reopen.append(key)
                entries += missing
    if not reopen:
        print("no stranded batches")
        return []
    verb = "would re-open" if dry else "re-opened"
    print(f"{verb} {len(reopen)} batch(es) holding {entries} uncatalogued entries")
    for k in reopen[:20]:
        print("   " + k)
    if not dry:
        st["done"]["entrypass"] = [k for k in done if k not in set(reopen)]
        # PIPELINE_STATE.json is the file pipeline.py owns and writes ONLY through
        # silence.replace_retry ("atomic writes; safe to kill the process"). This repair tool
        # was the one writer breaking that contract, with a truncating write, on the single most
        # important state file in the kit -- and it is invoked precisely when a pipeline may be
        # live, since that is when batches strand. Landing it the same way pipeline does.
        #
        # `pipeline.py`'s OWN write to this file was itself hardened (order e080a5f83b3c) from a
        # fixed `path + ".tmp"` to a pid+thread-carrying temp name, because two writers of the
        # same target collide on a SHARED temp name, not just on the target -- the loser's
        # rename can land its own half-written copy over the winner's finished one. This repair
        # tool was left on the old, fixed-name formula, which is the one convention pipeline.py
        # itself no longer uses. `silence.write_json` is that same pid+thread formula, so the two
        # writers of PIPELINE_STATE.json agree again. (found and fixed run36)
        if silence.write_json(path, st, indent=1):
            print("-> PIPELINE_STATE.json")
        else:
            # Do not report a repair that did not land. Returning the list unchanged would read
            # to the caller as "these were re-opened".
            print("health: PIPELINE_STATE.json write DENIED; nothing re-opened", file=sys.stderr)
            return []
    return reopen


CHECKS = [
    ("control characters in source", check_control_chars),
    ("context budget", check_context_budget),
    ("API paths per host family", check_api_paths),
    ("caches empty in a way that means broken", check_caches),
    ("state consistency", check_state),
]


def preflight(verbose=True, stamp=True):
    """Run every preflight check. -> the number of problems found.

    THE STAMP IS WHY THIS RUN'S FAULTS REACHED THE QUEUE AT ALL. Until run #33 the preflight
    reported only to a terminal: `allsweep` grades a verifier bad if it CRASHED or TIMED OUT,
    and this one does neither -- it exits 1 to say "I have findings", which is its contract and
    is deliberately not graded as a crash. So a red preflight left no machine-readable trace
    anywhere, `workorders --sweep` printed "nothing outstanding", and a genuinely failing check
    (every one of 805 dandwiki entries empty) sat unreported through four consecutive runs
    because the only thing that ever knew was a console nobody was reading.

    Writing the result where `workorders.sweep_detectors` can find it costs one small file and
    turns this from a check into a DETECTOR -- something that files. `drill.py` has written
    `drill_last.json` for exactly this reason since run #29; this is that pattern, applied to
    the member of the battery that most needed it.
    """
    problems = 0
    rows = []
    for label, fn in CHECKS:
        try:
            found = fn()
        except Exception as e:
            found = [("check itself failed", f"{type(e).__name__} {str(e)[:60]}")]
        if found:
            problems += len(found)
            rows.extend({"check": label, "what": str(a)[:200], "detail": str(b)[:300]}
                        for a, b in found)
            if verbose:
                print(f"  FAIL  {label}")
                for a, b in found:
                    print(f"          {a}: {b}")
        elif verbose:
            print(f"  ok    {label}")
    if stamp:
        # NEVER FATAL. A preflight that dies because it could not write its own report is worse
        # than one that cannot report: this runs at the head of every supervisor cycle.
        try:
            silence.write_json(PREFLIGHT_STAMP,
                               {"at": time.time(), "problems": problems,
                                "checks": [c[0] for c in CHECKS], "rows": rows}, indent=1)
        except Exception:
            silence.note("health.py:preflight-stamp")
    return problems


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--reopen", action="store_true",
                    help="re-open entry batches marked done that hold uncatalogued entries")
    ap.add_argument("--go", action="store_true", help="with --reopen, actually write")
    ap.add_argument("--preflight", action="store_true")
    ap.add_argument("--failures", action="store_true")
    a = ap.parse_args()
    if a.reopen:
        reopen_stranded(dry=not a.go)
        return 0
    if a.failures:
        s = summary()
        if not s:
            print("no failures recorded")
            return 0
        print(f"{'count':>8}  class")
        for k, v in sorted(s.items(), key=lambda kv: -kv[1]):
            print(f"{v:>8}  {k}")
        return 0
    print("PREFLIGHT")
    n = preflight()
    print(f"\n{n} problem(s)" if n else "\nall checks pass")
    return 1 if n else 0


if __name__ == "__main__":
    sys.exit(main())
