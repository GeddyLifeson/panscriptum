#!/usr/bin/env python3
"""
Autonomous pipeline runner for the Panscriptum.

Runs the project's phases in order, unattended and resumably, driving the local Ollama model
for every step that needs judgment or composition. Designed to survive being left overnight:
each unit of work is checkpointed the moment it completes, so a crash, a reboot, or a Ctrl-C
costs at most one unit.

PHASES
  1  synthesis   per-source: nominate the power ceiling entity and a band-only magnitude,
                 grounded in quoted evidence from the source's own entry text
  2  entrypass   per-entry: correct the category, assign a Magnitude band, assign the
                 encyclopedia topic, and extract scale_note ONLY where the text states a
                 demonstrated feat
  3  weave       cross-source ENTITY RESOLUTION -- "Zeus" becomes one canonical entity with
                 four attestations, not four entries (the charter's Step 4 entanglement)
  4  chain       THE CHAIN OF DEFEATS (Charter S129, X.2 S5) -- extract attested contests,
                 fit Bradley-Terry per connected component, and derive a band for entities
                 that have no feat of their own but are placed by comparison
  5  cosmology   derive universe -> multiverse -> metaverse -> xenoverse -> hyperverse from
                 the resolved entities, bottom-up from evidence
  6  history     write THE HISTORY OF THE OMNIVERSE from the weave + cosmology
  7  shelve      assemble THE ENCYCLOPEDIA OF THE OMNIVERSE: topical A-Z volumes, with
                 Persons of Importance shelved by Magnitude band then A-Z
  8  write       volume prose

All eight phases are implemented (the IMPLEMENTED dict at the bottom is derived from PHASES,
so writing `phase_<name>` IS registering it). The orchestrator still stops cleanly at any gap,
should one ever reopen.

STATE
  state/PIPELINE_STATE.json   phase progress + per-unit completion, the resume point
  state/pipeline.log          append-only run log
  handoff/RUN_STATUS.md       machine-written run status, rewritten after every unit
  handoff/HANDOFF.md          hand-written; the defects and the reasoning. NEVER written here.

Usage:
    python3 src/pipeline.py --status
    python3 src/pipeline.py --phase 1
    python3 src/pipeline.py            # run from the resume pointer to phase 8, then stop

THE RUNNER DOES NOT GO "FOREVER", and this line used to say it did. One pass runs
`state["phase"]` through the last phase and exits; the loop that makes it continuous is
`overnight.py`, which starts this process again every cycle. The distinction is not pedantry --
believing the runner looped is exactly what made a pointer parked past the last phase look like
a long-running job rather than a process exiting 0 having done nothing. It ran that way twice a
cycle for five passes. A pass that finds nothing to run now says which kind of nothing it found
(see `main`). (m37, 2026-08-25.)
"""
import argparse
import datetime
import glob
import collections
import json
import os
import re
import subprocess
import sys
import threading
import time
import traceback
import urllib.request
import cachekey
import silence

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RECORDS = os.path.join(HERE, "data/records")
STATE_DIR = os.path.join(HERE, "state")
STATE = os.path.join(STATE_DIR, "PIPELINE_STATE.json")
LOG = os.path.join(STATE_DIR, "pipeline.log")
# THE RUNNER GETS ITS OWN FILE.
#
# This pointed at handoff/HANDOFF.md, which is also the hand-written document that carries every
# defect this project has found and the reasoning that keeps each one from recurring. The runner
# rewrote it after every completed unit, so running the phases destroyed 629 lines of it and
# replaced them with a status table. Nothing failed, nothing warned, and the loss was only
# visible because a later edit could not find its own anchor.
#
# Two authors writing one file, one of them silently clobbering the other, is this project's
# defect in its most literal form. The status is machine-written and belongs in a machine-written
# file; the handoff is written by whoever last understood something and belongs in theirs.
HANDOFF = os.path.join(HERE, "handoff/RUN_STATUS.md")

sys.path.insert(0, os.path.dirname(__file__))
import yaml  # noqa: E402

# A regex escape arriving as a literal control character matches nothing and fails SILENTLY.
# A word-boundary escape written through a shell heredoc has arrived here as a 0x08 backspace
# five separate times in this project. Each time it read as a tuning problem -- a gate that
# passed nothing, a parser that found zero rows -- rather than as corruption, which is what
# makes it expensive. The check is built from chr() codes because the first version was
# written with escapes and they were eaten too, so it flagged its own source and refused.
_BAD_CHARS = (chr(8), chr(11), chr(12), chr(7))
if any(c in open(os.path.abspath(__file__), encoding='utf-8').read() for c in _BAD_CHARS):
    raise SystemExit(__file__ + ': a regex escape was eaten in transit - a literal control '
                     'character is present in the source. Repair before running.')


# Phase ladder, revised 2026-08-20 on the owner's architectural correction.
#
# Volumes are organised BY TOPIC ACROSS THE WHOLE OMNIVERSE, never by source IP. "Zeus" is one
# entry in Persons A-Z carrying four attestations (Marvel, God of War, Riordan, Smite), not
# four separate entries in four franchise volumes. Two collections, in dependency order:
#
#   The History of the Omniverse  -- narrative volumes built FROM the weave, whose job is to
#                                    construct the hyper/xeno/meta/multiverse structure by
#                                    connecting the sources to each other
#   The Encyclopedia of the Omniverse -- topical A-Z series drawing on that history:
#                                    Wars A-Z, Persons of Importance A-Z, Relics A-Z,
#                                    Powers A-Z, Weapons A-Z, Media A-Z, Events A-Z
#
# This makes `weave` load-bearing for everything downstream: without cross-source entity
# resolution, a topical volume is just a concatenation of per-IP lists with duplicate subjects.
PHASES = ["synthesis", "entrypass", "weave", "chain", "cosmology", "history", "shelve", "write"]

# Encyclopedia series. Volumes are built from these, across the whole omniverse -- never per
# source IP. Order matters only for reporting.
#
# Weapons vs Relics (owner ruling, 2026-08-20): a relic weapon is still a WEAPON. If its
# attested use is combat it files under Weapons regardless of how sacred or historically
# significant it is, so that a holy sword sits beside ordinary blades rather than being
# separated from them. Relics is therefore the NON-weapon significant-object series.
TOPICS = ["Persons", "Places", "Factions", "Weapons", "Relics",
          "Powers", "Events", "Wars", "Media"]

# SUBROOMS -- the finer room INSIDE a catalogue `category`. A THIRD AXIS, added 2026-09-01 by
# owner ruling, and it is worth being exact about why it is not either of the other two.
#
#   `category`  WHICH ROOM this entry sits in, in its source's catalogue. On 100% of entries.
#               Drives `threads.category_path` and the shelfmark chapter slugs.
#   `topic`     WHICH ENCYCLOPEDIA SERIES this entity publishes into, across the whole
#               omniverse -- Persons of Importance A-Z, Weapons A-Z, Wars A-Z. A publication
#               axis, deliberately independent of which work the entry came from.
#   `subroom`   WHICH SHELF WITHIN THE ROOM. A vehicle and a sword are both `Vessels & Things`
#               and they are not the same kind of thing; nothing could say so until now.
#
# THE THREE WERE CONFLATED AND IT COST A DAY. `topic` and `category` share six vocabulary words
# (Persons, Places, Factions, Powers, Events, Media), which reads as redundancy and is not: they
# answer different questions and are allowed to differ. A run acting on that misreading rewrote
# 7,909 topics to match their categories -- moving 1,459 entities out of Powers A-Z into Media
# A-Z, among others -- and it was reverted. Do not re-derive this: they are three axes.
#
# WHY `Vessels & Things` NEEDED THIS MOST. It holds 42,485 entries, half of them typed literally
# `Item`, and its only finer labels came from `topic`'s Weapons/Relics -- which are SERIES, not
# shelves. Measured: of 14,984 entries whose topic said `Weapons`, only 1,191 had a `type` of
# Weapon, and 966 vehicles were filed inside it.
#
# `Wars` sits under Events as both a series and a shelf; that is not a conflict, it is one word
# doing honest work on two axes.
SUBROOMS = {
    "Vessels & Things": ("Weapons", "Vehicles", "Armour", "Relics", "Consumables",
                         "Materials", "Accessories", "Documents", "Technology"),
    "Events": ("Wars",),
}
# Every legal value, and the two sentinels. A SENTINEL CAN BE COUNTED; AN ABSENT KEY CANNOT
# (BUGS m14, which cost `worldseed` and `weave` a silent permanent exclusion when `topic` went
# missing). The two are deliberately different facts:
#   "none"          this category has no finer shelves, or none applies. A CORRECT answer, and
#                   the right one for every Person, Place, Faction, Power and Media entry.
#   "unclassified"  the classifier offered something outside the vocabulary. A FAULT, and the
#                   offered value is kept in `subroom_rejected` so it is fixable rather than
#                   merely survived.
SUBROOM_VALUES = tuple(sorted({v for vs in SUBROOMS.values() for v in vs}))
SUBROOM_NONE = "none"
SUBROOM_UNCLASSIFIED = "unclassified"


def subroom_ok(category, subroom):
    """Is this subroom legal for this category? -> bool.

    Legality is per-ROOM, not global: `Wars` is a shelf in Events and nowhere else, and
    `Vehicles` is a shelf in Vessels & Things and nowhere else. A subroom that is merely in the
    vocabulary is not thereby correct for the room it was written into -- that is the same
    mistake `threads.FINER` avoids by checking each finer value against its declared parent.
    """
    if subroom in (SUBROOM_NONE, SUBROOM_UNCLASSIFIED):
        return True
    coarse = (category or "").split("(")[0].strip()
    return subroom in SUBROOMS.get(coarse, ())

# Magnitude bands, strongest first. Persons of Importance is shelved BY BAND THEN A-Z
# (owner ruling, 2026-08-20): "Persons of Importance: M7 A-Z", "... M6 A-Z", and so on, with
# unassayed entities in their own trailing series. This is why phase 2 assigns a band to every
# entry and not just to each source's ceiling.
BANDS = ["M10", "M9", "M8", "M7", "M6", "M5", "M4", "M3", "M2", "M1", "M0", "unassayed"]

# A CLEAN BAND IS THE WHOLE STRING, NOT ITS PREFIX.
#
# Both band gates used to read `re.match(r"^(M(?:10|[0-9]))\b", value)`. `re.match` anchors only
# the START, and `\b` is satisfied by any non-word character -- including a decimal point. So
# "M4.31 +/- 0.30" matched, `group(1)` returned "M4", and a fabricated Assay decimal was
# LAUNDERED into a clean published band, which is precisely what the phase-2 comment below says
# must be refused ("treat anything else -- prose, A DECIMAL, an empty string -- as unassayed")
# and what the system prompt calls a fabrication. Charter Part Three's "no worksheet, no number"
# rule forbids a decimal that no worksheet produced; accepting its integer part invents a
# provenance for it. Full-match, so a band is a band or it is nothing.
_CLEAN_BAND = re.compile(r"M(?:10|[0-9])")


def clean_band(value):
    """The band a value actually is, or "unassayed". Never a prefix of one."""
    text = str(value or "").strip()
    return text if _CLEAN_BAND.fullmatch(text) else "unassayed"


def ceiling_band(value):
    """A source's ceiling read for CLAMPING only, where a legacy dirty value is still usable.

    Deliberately laxer than `clean_band`: the clamp can only ever LOWER an entry's band, never
    raise one, so reading a pre-gate record whose `provisional_magnitude` still carries a
    decimal is safe -- while refusing to read it would silently drop the ceiling clamp for
    exactly the oldest records. Acceptance is strict, clamping is forgiving; the asymmetry is
    the point. Returns None when there is no band to clamp against.
    """
    m = re.match(r"^(M(?:10|[0-9]))\b", str(value or "").strip())
    return m.group(1) if m else None

CATEGORIES = [
    "Persons (named individual characters, real or fictional)",
    "Places & Locations (worlds, regions, cities, planes, ships-as-places)",
    "Vessels & Things (items, vehicles, weapons, artifacts, notable objects)",
    "Factions & Organizations (groups, nations, guilds, companies, orders)",
    "Powers, Abilities & Systems (magic systems, power systems, tech systems, disciplines)",
    "Events (major storyline events, wars, historical turning points within the fiction)",
    "Media (in-fiction media: books, songs, broadcasts, works that exist within the story itself)",
]


# --------------------------------------------------------------------------- infrastructure

def log(msg):
    os.makedirs(STATE_DIR, exist_ok=True)
    stamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    line = f"[{stamp}] {msg}"
    print(line, flush=True)
    with open(LOG, "a", encoding="utf-8") as f:
        f.write(line + "\n")


def _tmp_for(path):
    """The scratch name to write before renaming onto `path`. CARRIES PID AND THREAD.

    Four writers here used a fixed `path + ".tmp"`, which is not a private scratch file: two
    writers of the same target collide ON THE TEMP ITSELF, and the loser can rename its own
    half-written copy over the winner's finished one. `silence.write_json` was built on
    2026-08-25 to make that unavailable at twelve sites across the project and its docstring
    says why; these four -- `save_state`, `land_json` and both record writers, i.e. every shared
    file this module owns -- were still doing it by hand. Same formula, so the two agree.
    (order e080a5f83b3c.)
    """
    return "%s.%d.%d.tmp" % (path, os.getpid(), threading.get_ident())


def load_state():
    if os.path.exists(STATE):
        with open(STATE, encoding="utf-8") as f:
            return json.load(f)
    return {"phase": 1, "done": {}, "failed": {}, "started": None, "units_done": 0}


def save_state(st):
    """Land the resume point. -> True if it actually landed.

    GATED. The one-line comment below already said "readers poll this file" and the code then
    threw away the answer to whether they would see anything new. PIPELINE_STATE.json is not a
    convenience here: it is the resume point (`load_state` rebuilds `done`/`failed` from it),
    `health.py` reads it to report phase progress and `health.reopen_stranded` READ-MODIFY-WRITES
    it. A denied rename -- the ordinary Windows case, any of those readers holding it open --
    left the previous state on disk while this process carried on as though the unit were
    recorded. Two wrong answers follow, not one slow one: a restart re-runs work already done
    and re-writes its records, and a repair tool reading the stale copy calls settled batches
    stranded. Reported through `log`, which is this module's own way of making a fault visible
    (it prints AND lands in state/pipeline.log, so the trace survives the process).
    """
    os.makedirs(STATE_DIR, exist_ok=True)
    tmp = _tmp_for(STATE)
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(st, f, indent=2, ensure_ascii=False)
    if not silence.replace_retry(tmp, STATE):  # atomic; retried, readers poll this file
        silence.note("pipeline.py:save_state-denied")
        log("STATE WRITE DENIED -- PIPELINE_STATE.json still holds the PREVIOUS resume point "
            "(a reader is holding it open). Progress since the last successful save is not "
            "recorded; a restart will redo it.")
        return False
    return True


def cfg():
    with open(os.path.join(HERE, "config.yaml"), encoding="utf-8") as f:
        return yaml.safe_load(f)


METRICS = os.path.join(STATE_DIR, "model_metrics.jsonl")


_VRAM = {"at": 0.0, "mb": None}


def _vram_mb():
    """Card memory in use, sampled at most every 30s. When tok/s craters, this column says
    whether the model was fully resident or spilling to CPU -- gemma3:12b at 7.3 tok/s on a
    3080 (2026-08-23) was that question with no answer on file."""
    now = time.time()
    if now - _VRAM["at"] < 30:
        return _VRAM["mb"]
    _VRAM["at"] = now
    try:
        r = subprocess.run(["nvidia-smi", "--query-gpu=memory.used",
                            "--format=csv,noheader,nounits"],
                           capture_output=True, text=True, timeout=8,
                           creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
        _VRAM["mb"] = int(r.stdout.strip().splitlines()[0])
    except Exception:
        silence.note("pipeline.py:vram")
        _VRAM["mb"] = None
    return _VRAM["mb"]


def _metric(row):
    """One line per model call: tokens, latency, phase. The file the blame lives in.

    When something is slow, this is which stage and which call shape to blame -- Ollama
    already returns eval counts and durations on every response; they were being read and
    thrown away."""
    try:
        v = _vram_mb()
        if v is not None:
            row = dict(row, vram_mb=v)
        # ONE SYSCALL, NOT A BUFFERED WRITE (m62). See silence.append_line.
        #
        # VERDICT DELIBERATELY UNUSED, and this is the one write in this module where that is
        # right. Two reasons, both checked rather than assumed. (1) It is not silent: on failure
        # `append_line` calls `silence.note("silence.py:append_line")` itself, so the loss is
        # already in state/failures.json and visible to `health.py --failures` -- the verdict
        # would add a second report of a fault that is on file. (2) A lost row cannot produce a
        # wrong answer downstream. `standards.ollama_token_flow` treats a metrics row inside the
        # last 15 minutes as free proof of token flow and falls through to a LIVE generate probe
        # when the ledger is silent, so a dropped row costs a probe, never a false green; and
        # `standards`' ledger reader already `continue`s past rows it cannot use. The failure
        # direction is toward more checking, not less. Do not "fix" this by gating it: a
        # metrics failure must never cost a model call, which is what the docstring promises.
        silence.append_line(METRICS, json.dumps(row))
    except Exception:
        silence.note("pipeline.py:metric")


_PHASE_POOL = {"at": 0.0, "n": 0}


def _pool_answering(ttl=120):
    """How many cloud buckets actually answer, from the proof -- never from headroom.

    DELEGATED to `tuning._answering_buckets`, not reimplemented (order 54cd47a337dc). This used
    to re-open POOL_PROOF.json and count `verdict == "answers"` on its own, with no notion of
    the proof's age -- so an arbitrarily old proof was trusted as current, while tuning's copy of
    the identical count already compared the file's mtime against `PROOF_STALE_SECONDS`. Two
    spellings of one fact is exactly the shape `ask_pool_first` was already fixed for on the
    THRESHOLD thirty lines below; this closes it for the COUNT too. Falls back to 0 if tuning
    cannot be imported, same failure mode as before.
    """
    now = time.time()
    if now - _PHASE_POOL["at"] > ttl:
        try:
            import tuning as _T
            _PHASE_POOL["n"], _ = _T._answering_buckets()
        except Exception:
            silence.note("pipeline.py:pool-proof")
            _PHASE_POOL["n"] = 0
        _PHASE_POOL["at"] = now
    return _PHASE_POOL["n"]


def _pool_answer_usable(got, schema, accept):
    """Is a CLOUD answer actually usable, or merely non-None?

    THE GAP THIS CLOSES. Ollama constrains generation to the JSON schema; the cloud path cannot
    -- cascade_bridge.py:18 says so in as many words: "Cloud endpoints do not all offer that, so
    the schema is carried in the prompt." It is a REQUEST there, not a constraint. So a cloud
    model can return perfectly valid JSON of entirely the wrong shape, `_extract_json` parses it
    happily, and `ask_pool_first` used to return it on the sole test `got is not None`.

    Downstream that is indistinguishable from the model judging every entry and finding nothing.
    On 2026-08-24 four consecutive Marvel entrypass batches logged `returned 0/20 - left open
    for retry` while the pool proof reported >= 3 answering -- and the SAME batch, put to the
    local model directly, returned 20 valid results in 54s. The batch was not hard. The cloud
    answer was unusable and the local arm, which works, was never reached, because a
    cloud-first/local-second helper that accepts any non-None answer has no second.

    Two checks, cheapest first:
      * SHAPE -- every key the schema marks `required` must be present. Free, and generic.
      * ACCEPT -- an optional caller predicate, because "usable" is caller knowledge. A call
        that asked for judgments on 20 named entries and got zero back has not been answered;
        a call that legitimately may return an empty list has. Only the caller knows which.
    """
    if not isinstance(got, dict):
        return False
    for k in (schema or {}).get("required", []):
        if k not in got:
            return False
    if accept is not None:
        try:
            return bool(accept(got))
        except Exception:
            silence.note("pipeline.py:pool-accept")
            return False
    return True


def ask_pool_first(c, system, prompt, schema, timeout=None, num_ctx=None, tag="", accept=None):
    """Cloud pool first, local second -- for the PHASES' own judgment calls.

    OWNER QUESTION 2026-08-24: "why do we keep using ollama when there are free cloud ais?"
    Answer: every reading stage already is pool-first; the phases were local-only from the era
    when the GPU sat idle and the pool was the reader's. That era ended -- eight buckets were
    measured answering while entrypass queued behind one 8B model. Phase judgment calls are
    small structured JSON, exactly what the free lanes are best at. Gated on the PROOF (>=3
    answering), not on reported quota: headroom is not evidence -- 25 of 36 buckets once
    reported healthy quota while answering nothing. Prose stays local by charter design; its
    book-length outputs would drain a free tier in minutes.

    Every other caller of ask() (magnitude, ingest_doc, overwatch, read's fallback) manages
    its own pool order and uses ask() as the deliberately-LOCAL arm; only the phase call
    sites route through here, so nothing double-claims a bucket it already tried."""
    # THE THRESHOLD IS TUNING'S, NOT A SECOND COPY OF IT. This read `>= 3` as a bare literal
    # while `tuning.CLOUD_MIN_BUCKETS` held the same 3 and carried the argument for changing it
    # ("Two is not enough..."). Two spellings of one policy: raise it there and this call site
    # silently keeps the old bar. Falls back to 3 if tuning cannot be imported, so the routing
    # decision never depends on the import succeeding.
    try:
        import tuning as _T
        _min_buckets = int(_T.CLOUD_MIN_BUCKETS)
    except Exception:
        silence.note("pipeline.py:min-buckets")
        _min_buckets = 3
    if _pool_answering() >= _min_buckets:
        try:
            import cascade_bridge as CB
            got = CB.ask(system, prompt, schema)
            if _pool_answer_usable(got, schema, accept):
                return got
            if got is not None:
                # Not a transport failure -- a bucket answered, with something this call cannot
                # use. Say so, because it is invisible otherwise: the batch just scores zero and
                # the log blames the model. Then fall through to the local arm, which is the
                # entire point of a cloud-FIRST helper.
                log(f"    pool answered {tag or 'call'} with an unusable shape; "
                    f"falling back to local")
        except Exception:
            silence.note("pipeline.py:phase-pool")
    return ask(c, system, prompt, schema, timeout=timeout, num_ctx=num_ctx, tag=tag)


def ask(c, system, prompt, schema, retries=2, timeout=None, num_ctx=None, tag=""):
    """One structured Ollama call. Returns parsed dict, or None on repeated failure.

    `timeout` deliberately does NOT default to config's request_timeout (1800s). That value is
    sized for volume prose, where a single chapter legitimately runs several minutes. The
    judgment calls here emit a few hundred tokens and should never take minutes -- so a call
    that does is hung, and waiting half an hour to find out would burn a whole unattended
    night on one stuck request. Fail fast, log it, move to the next unit.
    """
    body = json.dumps({
        "model": c["model"], "system": system, "prompt": prompt, "stream": False,
        "format": schema,
        # keep_alive is sent explicitly on EVERY request rather than relying on
        # OLLAMA_KEEP_ALIVE being inherited by whichever process happened to start the
        # server. Getting this wrong is expensive out of all proportion: an unloaded MoE
        # costs ~170s to bring back (measured), against ~12s for the call itself. Belt and
        # braces is correct here.
        "keep_alive": -1,
        # num_ctx SIZED TO THE CALL, not a generous default. The KV cache scales with the
        # window: a 2,400-token entrypass batch inside a 6,144 window pays 2.5x the VRAM it
        # needs, which is exactly the headroom the 10GB card keeps running out of.
        "options": {"seed": c.get("seed", 47), "temperature": 0.1,
                    "num_ctx": num_ctx or c.get("num_ctx", 6144)},
    }).encode()
    import gpu_lane
    for attempt in range(retries + 1):
        try:
            req = urllib.request.Request(c["ollama_host"].rstrip("/") + "/api/generate",
                                         data=body,
                                         headers={"Content-Type": "application/json"})
            t0 = time.time()
            # THE LANE. Every phase call is background work: it yields to prose generation and
            # to an owner's interactive run, then queues for one of the card's slots. Nine
            # standing jobs used to arrive here at once and the card served none of them well.
            # gpu_lane fails open, so a fault in it costs nothing but the arbitration.
            with (gpu_lane.lane(f"pipeline:{tag or 'ask'}"),
                  urllib.request.urlopen(req, timeout=timeout or 420) as r):
                raw = json.loads(r.read().decode())
            # "at" IS NOT OPTIONAL: it is what makes a row findable in time.
            #
            # This row carried no timestamp for the whole life of the ledger while
            # cascade_bridge._metric's row always did. Both write the same file, so every
            # time-windowed query over it -- including the "is the cloud still storming"
            # one-liner each maintenance run is handed -- filtered on `at` and silently
            # returned CLOUD-ONLY results. 913 local rows across 7 tags were invisible, and
            # the local lane's call volume had never once been measurable. The count looked
            # like a complete answer because the rows it dropped did not exist to it.
            _metric({"at": round(t0, 1), "tag": tag or "ask", "s": round(time.time() - t0, 2),
                     "in_tok": raw.get("prompt_eval_count"), "out_tok": raw.get("eval_count"),
                     "tps": (round(raw["eval_count"] / (raw["eval_duration"] / 1e9), 1)
                             if raw.get("eval_duration") and raw.get("eval_count") else None),
                     "model": c.get("model")})
            return json.loads(raw.get("response", "{}"))
        except Exception as e:
            if attempt == retries:
                # UNCUT (Hard Rule 0, sweep42-batch03). This line is the ONLY record that a
                # local call failed after exhausting its retries, and the exception text was cut
                # at 80 characters -- shorter than most Ollama error bodies, which put the
                # actionable part (a 503 queue refusal, a model name, a context overflow) after
                # the first clause. A diagnostic too short to diagnose.
                log(f"    ollama failed after {retries + 1} tries: {type(e).__name__} {e}")
                return None
            time.sleep(5 + attempt * 10)


def records():
    out = []
    for p in sorted(glob.glob(os.path.join(RECORDS, "*.json"))):
        try:
            with open(p, encoding="utf-8") as f:
                r = json.load(f)
        except Exception:
            silence.note("pipeline.py:records-unreadable")
            continue
        if r.get("entries"):
            out.append((p, r))
    return out


# THE PER-ENTRY MERGE ALLOWLIST, WRITTEN ONCE FOR BOTH WRITERS.
#
# Both sides of the two-writer contract fold per-entry fields across the merge, in opposite
# directions (see each writer's docstring), and both used to spell the list out separately as
# ('category', 'scale_note', 'scale_note_rejected', 'magnitude', 'topic', 'catalogued'). Two
# spellings of one policy is how they came to disagree with the rest of the pipeline: `excluded`,
# `topic_rejected`, `thin_description` and `description` are all written per-entry by sanctioned
# callers and NONE of them was on the list, so every one of those edits was computed, reported,
# and then dropped by the writer.
#
# `excluded` is the one that did damage rather than merely losing information. `cleanup.py`
# strikes an entry by setting `catalogued = False` AND `excluded = <reason>`; the fold carried the
# False and dropped the reason, and `entry_settled` is `catalogued or excluded` -- so the entry
# came out NEITHER catalogued NOR excluded, i.e. unsettled, and `phase_entrypass` duly re-judged
# it and set `catalogued = True`. The strike reverted itself, on the next pass, every time. That
# is the reverted-exclusion cycle `batch_settled`'s docstring says was closed after the 149-entry
# incident, surviving in the writer. Measured across data/records/ before this fix: 111 entries
# carry `excluded` and 111 of those also carry `catalogued: True`, and `topic_rejected` -- which
# `phase_entrypass` writes at pipeline.py:1552 -- appears 0 times in 282,822 entries.
# (order 4866dfb2d9fc)
MERGED_ENTRY_FIELDS = ("category", "scale_note", "scale_note_rejected", "subroom",
                       "subroom_rejected",
                       "magnitude", "topic", "catalogued",
                       # added by order 4866dfb2d9fc: the settlement pair must move together,
                       # and cleanup.py's own two marks must survive the writer that carries them
                       "excluded", "topic_rejected", "thin_description", "description")

# A CLEAR IS AN EDIT TOO, FOR THE TWO FIELDS THAT ENCODE ONE. `write_record`'s fold is
# PRESENCE-gated (`if fld in se`), so it can SET a field and can never CLEAR one -- and that is
# the right default, because `_merge_top_keys` rules that a key the caller did not write means
# unauthored, not deleted. But `phase_entrypass` clears exactly two keys DELIBERATELY: it pops
# `scale_note_rejected` when the note validates (:1532) and `topic_rejected` when the topic is in
# TOPICS (:1573), and both pops mean "the earlier rejection no longer stands". Neither could
# reach the disk copy, so an entry carried a record that its topic was REJECTED sitting beside
# the corrected topic that supersedes it -- two contradictory claims about one judgment, and the
# blast radius grows with every reopened batch. So these two travel as COMPANIONS of the field
# they qualify: when the qualified field is present in the caller's entry and the rejection is
# not, the rejection is absent ON PURPOSE and goes. Nothing else is cleared by absence.
# (order 2f248e854b58)
#
# AND `subroom`, WHICH WAS THE ONE FIELD ADDED AFTER THIS MECHANISM WAS WRITTEN
# (sweep43-batch03). The judging loop treats it identically to `topic` -- `:1718` pops
# `subroom_rejected` the moment a subroom passes `subroom_ok`, exactly as `:1707` pops
# `topic_rejected` -- and `subroom_rejected` is already declared in `MERGED_ENTRY_FIELDS` at
# :554. It was simply never added here, so the pop stayed in memory and could not reach disk:
# the per-entry fold can SET a field and never CLEAR one on absence, which is the whole reason
# this map exists. The result is the precise fault the comment above describes, on the newest of
# the three fields -- a corrected subroom sitting on disk beside a `subroom_rejected` note
# asserting the opposite, with no way for any later run to retract it.
ENTRY_REJECTION_COMPANIONS = {"scale_note": "scale_note_rejected",
                              "topic": "topic_rejected",
                              "subroom": "subroom_rejected"}


def write_record_catalogue(path, rec):
    """The CATALOGUE's side of the two-writer contract; write_record below is the pipeline's.

    Direction matters, and one merge cannot serve both writers: write_record keeps the DISK
    entry list because the pipeline's in-memory copy is the stale side. The catalogue is the
    opposite case -- its fresh cast IS the authority -- and routing it through write_record
    would have discarded a 30,207-entry re-catalogue in favour of the 1,051 stale entries on
    disk (caught during the 2026-08-23 audit before any catalogue ever did it; they were
    writing raw, non-atomically, which was its own hazard). Here rec's entry LIST wins, the
    disk copy's per-entry judgments (bands, scale notes, topics) are preserved onto matching
    names, and disk-only entries are kept -- a merge never shrinks a cast.

    AND THE KEYS THAT ARE NOT `entries`, which this merge did not look at ONCE. It reconciled
    the cast and then wrote `rec` WHOLE, so every top-level key the caller did not author was
    destroyed by the write that followed the merge. `catalogue_web.catalogue()` and
    `catalogue_composite()` both return `"synthesis": None` -- correctly, because a wiki lead
    paragraph is not an Assay and they say so in their own provenance -- and that None landed on
    top of the pipeline's `ceiling_entity` and `provisional_magnitude` and erased them. It was
    running: 31 of 216 records carry a null synthesis, all of them mode=web, 26 nulled in the
    last 24 hours, the most recent at 22:47 today, and the casualties include DC (44,958
    entries), Legend of Zelda, Dragon Ball Z and Transformers. It does not self-heal, because
    `phase_synthesis` skips any source already in its done-keys -- the block stays null forever.
    Two records' `purged_roster` went the same way, by simple absence.

    So a key the caller did not author no longer overwrites one the disk holds:

      * absent from `rec`           -> the disk value is carried over
      * present as `None` in `rec`  -> the disk value is kept

    "Did not compute this field" and "means to clear this field" are genuinely different acts
    and this cannot read minds, so it takes the recoverable side of the ambiguity: `None` means
    unauthored. A caller that really does mean to CLEAR a key still can, by writing an explicit
    empty value (`{}`, `[]`, `""`) -- which is a deliberate statement rather than the default
    shape of a dict that was never filled in. The entry-list direction above is UNCHANGED: the
    fresh cast still wins, because that asymmetry is the whole reason this writer exists.
    (Order 7292a1c3d84b / 3c7c8a6e9102, 2026-08-25. The 26 damaged records are NOT repaired
    here -- re-deriving a ceiling is the owner's call, and it is filed as one.)
    """
    try:
        with open(path, encoding="utf-8") as f:
            disk = json.load(f)
        by = {e.get("name"): e for e in rec.get("entries") or [] if isinstance(e, dict)}
        for de in disk.get("entries") or []:
            if not isinstance(de, dict):
                continue
            se = by.get(de.get("name"))
            if se is None:
                rec.setdefault("entries", []).append(de)
                continue
            for fld in MERGED_ENTRY_FIELDS:
                dv, sv = de.get(fld), se.get(fld)
                if dv and (not sv or sv == "unassayed"):
                    se[fld] = dv
        # THE NON-ENTRIES KEYS. See the docstring: absent or None from the caller is not an
        # instruction to erase what is on disk.
        kept = []
        for k, dv in (disk.items() if isinstance(disk, dict) else ()):
            if k == "entries" or dv is None:
                continue
            if k not in rec or rec[k] is None:
                rec[k] = dv
                kept.append(k)
        if kept:
            log(f"    write_record_catalogue: {os.path.basename(path)} keeping "
                f"{len(kept)} disk-authored key(s) the caller did not write: "
                f"{', '.join(sorted(kept))}")
    except FileNotFoundError:
        _ = "silence-exempt: no disk copy yet means nothing to merge; first write"
        pass
    except Exception:
        # THE SAME FALL-THROUGH AS write_record, WITH THE LOSS POINTING THE OTHER WAY.
        #
        # Found run #24 alongside its twin. Here `rec` is the authority for the entry LIST, so
        # a swallowed read does not revert the cast -- it does something quieter and just as
        # permanent. The merge is what carries the disk copy's per-entry judgments (bands,
        # scale notes, topics) forward onto matching names, and what re-appends the entries
        # only disk has. Skip it and this write DROPS every disk-only entry and blanks every
        # judgment the pipeline had already made, while the docstring one screen up promises
        # "a merge never shrinks a cast".
        #
        # Same trigger as the twin: the read fails most readily when the other writer is
        # mid-write. Same remedy, and it is this module's own idiom -- return False, the caller
        # leaves its unit open, the next run redoes it against a readable file.
        silence.note("pipeline.py:write_record_catalogue")
        log(f"    write_record_catalogue: {os.path.basename(path)} could not be read for "
            f"merge; REFUSING to write an unmerged cast over it -- this unit stays open")
        return False
    stamp_record(rec, "pipeline.write_record_catalogue")
    tmp = _tmp_for(path)
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(rec, f, indent=2, ensure_ascii=False)
    return _landed(tmp, path)


def _landed(tmp, path):
    """Rename `tmp` over `path`, and SAY whether it actually happened.

    `silence.replace_retry` records persistent denial and returns False rather than raising, on
    the reasoning that "the caller's write lands next round". That is only true if the caller
    comes back -- and both record writers are called by phases that then mark their unit DONE,
    which means there is no next round. A denied rename plus a recorded done-key is the exact
    silent permanent loss the phase-2 comment at the `done_keys` gate says was already paid for
    once. So the writers now return the verdict and the callers gate their done-keys on it.
    """
    if silence.replace_retry(tmp, path):
        return True
    silence.note("pipeline.py:write-did-not-land")
    log(f"    WRITE DID NOT LAND: {os.path.basename(path)} is still the pre-write copy; "
        f"this unit stays open so the next run redoes it")
    return False


def mark_done(st, phase, unit="all"):
    """Record a completion marker for `phase` WITHOUT letting it accumulate duplicates.

    THE DONE-LIST IS A SET WEARING A LIST'S CLOTHES. Every phase-level marker in this file is
    the literal string "all" -- "this phase, whole, is finished" -- and both `gate_done` and the
    three phases that mark themselves done directly appended it unguarded on every run. So the
    live state grew `weave: ["all", "all", "all", "all"]` and `write: ["all"] * 5`: a count of
    how many times the phase was re-run, recorded in the field that answers whether it is done.
    Nothing reads the length, so nothing objected -- but it made the state unreadable as
    evidence, which is how the runner's own no-op stayed invisible for five passes (m37).

    Idempotent by construction: appending "all" twice cannot mean more than appending it once.
    The per-unit phases (1 and 2) keep their own done-key lists, which are genuinely
    accumulative and unique per unit, so they go on appending directly.

    Returns True if this call is what closed the phase, False if it was already closed. The
    return is information, not a gate -- either way the phase is done when this returns.
    """
    keys = st.setdefault("done", {}).setdefault(phase, [])
    if unit in keys:
        return False
    keys.append(unit)
    return True


def phases_never_closed(st):
    """The phases carrying NO completion marker at all. The runner's honesty check.

    A phase pointer past the end of PHASES means one of two things, and they are opposites: the
    run finished, or the pointer walked past work that never completed. `done` is what tells
    them apart, so it is read here rather than assumed. (m37.)
    """
    d = st.get("done") or {}
    return [n for n in PHASES if not d.get(n)]


def gate_done(st, phase, landed):
    """Mark a phase done ONLY if every artifact it wrote actually landed.

    `_landed` returns its verdict precisely so callers can gate their done-keys on it, and says
    so in its own docstring -- "the writers now return the verdict and the callers gate their
    done-keys on it". They did not. All TWELVE `land_json` call sites discarded the verdict and
    appended the done-key unconditionally, so a denied rename left the phase marked complete
    sitting over a pre-write artifact, and because the done-key was already written no later run
    ever redid it. That is exactly the silent permanent loss `_landed` was added to close,
    reintroduced at every single call site -- the fix landed in the writer and never reached the
    callers the docstring described.

    Note the asymmetry that makes this worth gating rather than merely logging: a phase artifact
    is read by a LATER PHASE IN THE SAME RUN (phase 6 reads phase 5's TIERS.json), so a stale
    artifact is not one lost cycle, it is a wrong input that the next phase reports as its own
    empty result. (m36, 2026-08-25.)
    """
    if all(landed):
        mark_done(st, phase)
        return True
    log(f"    phase {phase} NOT marked done: {landed.count(False)} of {len(landed)} artifact(s) "
        f"did not land; leaving the unit open so the next run redoes it")
    silence.note("pipeline.py:phase-not-marked-done")
    return False


def land_json(path, obj, indent=1, default=None):
    """Write a phase artifact atomically. Returns whether it landed.

    The later phases wrote their artifacts as `json.dump(obj, open(path, "w"), ...)`: not
    atomic, and the handle never explicitly closed either, so a reader could see a
    half-serialised file and CPython's refcount close was the only thing flushing it. Several of
    these are read by a LATER PHASE IN THE SAME RUN -- phase 6 reads phase 5's TIERS.json -- so
    a crash or a slow reader mid-write does not just cost a cycle, it feeds the next phase a
    truncated file. `phase_history`'s own TIERS.json handler then reports that corruption as
    "phase 5 has not run" and marks itself done with an empty result.

    Same discipline as the record writers; `_landed` already explains why the verdict is
    returned rather than swallowed. (BUGS m6, 2026-08-24.)"""
    tmp = _tmp_for(path)
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(obj, f, indent=indent, ensure_ascii=False, default=default)
    return _landed(tmp, path)


def _merge_top_keys(disk, rec, label):
    """Fold `rec`'s non-`entries` top-level keys onto `disk`. -> [keys kept from disk].

    THE SAME RULING AS `write_record_catalogue`, APPLIED TO THE OTHER WRITER, which never got it.
    On 2026-08-25 the catalogue side was found writing `rec` whole after its merge, so every
    top-level key the caller had not authored was destroyed: `catalogue_web` returns
    `"synthesis": None` -- correctly, since a wiki lead paragraph is not an Assay -- and that
    `None` landed on the pipeline's `ceiling_entity` and `provisional_magnitude` and erased them.
    31 of 216 records still carry a null synthesis from it, and it does not self-heal because
    `phase_synthesis` skips any source already in its done-keys. That is order 3c7c8a6e9102, and
    it is still open at OWNER because re-deriving a ceiling is a curatorial act.

    `write_record` was left with the unguarded version of the identical shape -- found by the
    run #36 whole-tree sweep, batch 3 -- in BOTH of its paths:

      * the drift branch did `disk[key] = val` for every non-`entries` key, unconditionally, so
        a `None` in the pipeline's hours-old in-memory copy overwrote a live disk value;
      * the no-drift fast path never merged at all: `merged = rec` wrote the stale in-memory
        copy WHOLE, which silently drops any top-level key another writer added since the
        pipeline loaded its records. Equal entry lists do not mean equal records.

    So the ambiguity is resolved here exactly as it was resolved there, and deliberately in the
    same words: "did not compute this field" and "means to clear this field" are different acts,
    this cannot read minds, and it takes the recoverable side -- `None` means unauthored. A
    caller that really does mean to clear a key still can, with an explicit empty value (`{}`,
    `[]`, `""`), which is a statement rather than the default shape of a dict never filled in.

    The entry-list asymmetry is UNTOUCHED: `write_record` still keeps the DISK cast, because the
    pipeline's copy is the stale side, and that asymmetry is the whole reason it exists.
    """
    kept = []
    for key, val in rec.items():
        if key == "entries":
            continue
        if val is None and disk.get(key) is not None:
            kept.append(key)          # unauthored by this caller; the disk value stands
            continue
        disk[key] = val
    if kept:
        log(f"    write_record: {label} keeping {len(kept)} disk-authored key(s) the caller "
            f"left unauthored: {', '.join(sorted(kept))}")
    return kept


def write_record(path, rec):
    """Write a record back WITHOUT clobbering a concurrent writer's work.

    The catalogue and the pipeline both write these files, and they write them WHOLE. The
    pipeline loads its records at phase start and holds them for hours; the re-catalogue
    rewrites the same file in the meantime -- marvel.json went from 1,051 entries to 30,207 in
    one such pass. Writing the pipeline's stale in-memory copy over that would silently revert
    twenty-nine thousand entries, and the loss would read as "the re-catalogue never ran".

    So: if the file on disk has drifted, this MERGES instead of overwriting. The pipeline only
    ever changes per-entry judgment fields and the source-level synthesis block, so those move
    onto the disk copy by entry name; every entry the disk version has that this in-memory copy
    lacks is kept. The fast path -- no drift -- writes directly, which is the common case.

    DRIFT IS A DIGEST OF THE ENTRY NAMES, NOT A COUNT OF THEM (order 1c2ea97cdc36, run #36).
    The sole drift test used to be `len(disk["entries"]) != len(rec["entries"])`, which is blind
    to every same-size edit: a rename, a dedup-then-add, any cast correction that swaps one entry
    for another. `write_record_catalogue`, `ingest_doc` and `catalogue_web` all write these files
    and all can produce that shape. Seeing no drift, this function took the fast path and wrote
    the pipeline's hours-old in-memory copy WHOLE over the disk file -- the same silent revert
    the paragraph above says it exists to stop, just at a granularity the count could not see.
    `_entry_digest` was already in this module (it is what `stamp_record` records and
    `verify_record_provenance` checks) and was simply not consulted here; it is now. The count
    test is KEPT rather than replaced -- it is cheap, it names the common case in the log line,
    and two independent drift signals cannot share a hash collision.
    """
    merged = rec
    try:
        with open(path, encoding="utf-8") as f:
            disk = json.load(f)
        n_disk, n_mem = len(disk.get("entries") or []), len(rec.get("entries") or [])
        drift = ("count" if n_disk != n_mem else
                 "content" if _entry_digest(disk) != _entry_digest(rec) else None)
        # THE PER-ENTRY FOLD RUNS ON BOTH PATHS, and it did not.
        #
        # This copy carries the caller's fresh per-entry JUDGMENTS -- category, scale_note,
        # scale_note_rejected, magnitude, topic, catalogued -- onto the disk cast that is about
        # to be written. It used to live inside `if drift:` only, while the `else` branch set
        # `merged = disk` after folding the TOP-LEVEL keys and nothing else. So on the no-drift
        # path every judgment the caller had just computed was silently dropped and the function
        # still returned True.
        #
        # That is not a corner, it is phase 2's ORDINARY path: `drift` is decided by
        # `_entry_digest`, which digests entry NAMES, and `phase_entrypass` never changes a
        # name -- it fills in bands and notes on a cast whose names it leaves exactly as it
        # found them. So entrypass took the `else` branch essentially every time.
        #
        # Measured by the run-37 sweep on a copy of a real record: 20 entries judged in memory,
        # `write_record` returned True, 0 of 20 settled on disk. Corroborated live: 1,496 of the
        # 4,559 recorded `done.entrypass` keys name spans that are unsettled on disk (677
        # Marvel, 195 DC, 151 Final Fantasy). Every phase-2 model call spent while this stood
        # bought a write that did not land, and RUN_STATUS.md reported the progress anyway.
        #
        # Introduced by the run-36 top-key repair, whose own red-check uses entries carrying no
        # judgment fields -- so the check could not see the fields it was dropping. Hoisted here
        # rather than duplicated into the `else`, so the two paths cannot drift apart again.
        by_name = {e.get("name"): e for e in rec.get("entries") or []}
        # ORDER b67dc1990af6: `by_name` is keyed on `name`, and `name` is demonstrably not a
        # per-entry identity -- duplicate names are ordinary here ('2112 (Rush)' carries two
        # entries called 'The Guitar'). Every disk entry sharing a duplicated name folds from
        # whichever in-memory entry the dict comprehension above happened to keep last, so the
        # OTHER duplicates' judgments are silently discarded even though this function still
        # returns True. Giving every entry a stable identity that survives the merge is a data
        # model decision for the owner (index? content hash? (name, type, description) triple?)
        # and is not made here. What IS done, per the order's own "cheaper interim": count the
        # collapses and say so, so a caller -- or a human reading the log -- can tell a write
        # was partial instead of finding out by diffing the file.
        name_counts = collections.Counter(
            e.get("name") for e in rec.get("entries") or [] if isinstance(e, dict))
        dup_names = {n for n, c in name_counts.items() if n and c > 1}
        collapsed = 0
        for de in disk.get("entries") or []:
            se = by_name.get(de.get("name"))
            if not se:
                continue
            if de.get("name") in dup_names:
                collapsed += 1
            for fld in MERGED_ENTRY_FIELDS:
                if fld in se:
                    de[fld] = se[fld]
            # The two companion clears; see ENTRY_REJECTION_COMPANIONS for why these and only
            # these. Guarded on the qualified field being present so a caller that never
            # touched `topic` at all cannot delete a rejection it knows nothing about.
            for fld, rej in ENTRY_REJECTION_COMPANIONS.items():
                if fld in se and rej not in se:
                    de.pop(rej, None)
        if collapsed:
            log(f"    write_record: {os.path.basename(path)} {collapsed} disk entr"
                f"{'y shares' if collapsed == 1 else 'ies share'} a duplicated name with "
                f"{len(dup_names)} distinct name(s) in the in-memory cast -- only the LAST "
                f"in-memory entry per name survived the merge, so the others' judgments were "
                f"not written even though this call returns True. See order b67dc1990af6.")
            silence.note("pipeline.py:write_record-duplicate-name-collapse")
        # NO DRIFT IS NOT NO CHANGE. Folding onto `disk` keeps every disk-authored top-level key
        # -- a `synthesis`, `purged_roster` or `ceiling_entity` another writer refreshed since
        # this record was loaded -- instead of writing the pipeline's hours-old copy whole.
        _merge_top_keys(disk, rec, os.path.basename(path))
        merged = disk
        if drift:
            log(f"    write_record: {os.path.basename(path)} drifted on disk by {drift} "
                f"({n_mem} -> {n_disk} entries); merged")
    except FileNotFoundError:
        silence.note("pipeline.py:write_record-notfound")
        pass
    except Exception:
        # A FAILED MERGE MUST NOT FALL THROUGH INTO THE OVERWRITE IT EXISTS TO PREVENT.
        #
        # Found run #24. `merged` is initialised to `rec` -- the STALE in-memory copy -- and
        # only becomes the disk-merged version if the read above succeeds. So when this handler
        # fired, the function swallowed the error and then wrote the pipeline's hours-old copy
        # over the disk file WHOLE: exactly the 30,207-entries-to-1,051 revert the docstring
        # says this function was written to stop, performed by the guard itself.
        #
        # And the trigger is not exotic. The read most likely fails precisely WHEN the other
        # writer is mid-write -- a torn or momentarily-empty file is a JSONDecodeError -- which
        # is the one moment the merge matters. The rarer the condition, the more total the loss.
        #
        # Refusing is the safe direction and it is already this module's idiom: `_landed`
        # returns False so the caller leaves its unit open and the next run redoes it. Losing
        # one update is recoverable; overwriting a fresh re-catalogue is not.
        silence.note("pipeline.py:write_record-merge")
        log(f"    write_record: {os.path.basename(path)} could not be read for merge; "
            f"REFUSING to write the in-memory copy over it -- this unit stays open")
        return False
    stamp_record(merged, "pipeline.write_record")
    tmp = _tmp_for(path)
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(merged, f, indent=2, ensure_ascii=False)
    return _landed(tmp, path)


# ------------------------------------------------- the two-writer contract, made checkable
#
# The contract is old and sound: records are written by `write_record` (pipeline side) or
# `write_record_catalogue` (cast-growing side), and by nothing else. What it never had was a way
# to NOTICE a violation. Eight-plus modules touch `data/records`, and a third writer leaves no
# trace at all -- the file simply differs from what the sanctioned writers would have produced,
# which is indistinguishable from ordinary progress.
#
# M24 made that concrete: `local_agent.propose_patch` could edit a record directly, and every
# gate it passed (parse, lint, import, verify_math) was green, because those gates check that a
# patch is well-formed rather than that it came through the right door.
#
# So each sanctioned write now leaves a stamp naming its writer and a digest of the entry names
# it wrote. A later reader can ask whether the file still matches its own stamp. This is a
# DETECTOR, deliberately, not a lock -- a lock on a JSON file on the owner's own disk would be
# theatre, and the failure worth catching is the silent one, not the determined one.
def _entry_digest(rec):
    import hashlib
    names = [str((e or {}).get("name", "")) for e in (rec.get("entries") or [])
             if isinstance(e, dict)]
    h = hashlib.sha1()
    h.update(("\n".join(names)).encode("utf-8"))
    return h.hexdigest()[:16]


def stamp_record(rec, writer):
    """Record who wrote this and what it contained. Called by the sanctioned writers only."""
    if not isinstance(rec, dict):
        return rec
    rec["_writer"] = {"by": writer, "entries": len(rec.get("entries") or []),
                      "digest": _entry_digest(rec)}
    return rec


def verify_record_provenance(rec):
    """-> (state, detail). Does this record still match the stamp its writer left?

    Three outcomes, and the middle one matters most:
      OK        stamped, and the stamp still describes the file
      UNSTAMPED written before stamping existed, or by something that does not stamp. NOT an
                accusation -- most of the corpus predates this -- but it is not evidence of
                good provenance either, and it must never be reported as OK.
      DRIFTED   stamped, and the content no longer matches. Something wrote this file that was
                not the writer that stamped it.
    """
    if not isinstance(rec, dict):
        return "UNSTAMPED", "not a record"
    st = rec.get("_writer")
    if not isinstance(st, dict):
        return "UNSTAMPED", "no writer stamp"
    n = len(rec.get("entries") or [])
    if st.get("entries") != n:
        return "DRIFTED", ("stamp says %s entries, file has %d" % (st.get("entries"), n))
    if st.get("digest") != _entry_digest(rec):
        return "DRIFTED", "entry names changed since the stamp was written"
    return "OK", "written by %s" % st.get("by")


# ------------------------------------------------------------------------------- phase 1

SYNTH_SYSTEM = """You assess fictional sources for an encyclopedia's power-scale index.

You are given a sample of catalogued entries from ONE source. Identify which entity is the
source's power ceiling -- the single most powerful being or force present -- and assign a
MAGNITUDE BAND.

HARD RULES:
1. Ground every claim in the supplied text. Quote the phrase that justifies your choice in
   `evidence` -- at most 20 words, the quoted fragment only. If the text does not demonstrate
   power, say so and use "unassayed".
0. BE TERSE. `rationale` is ONE short sentence, never a paragraph. Long rationales cost
   generation time and add nothing a reader of `evidence` does not already have.
2. BAND ONLY. Output M0-M10, never a decimal. Decimal Assay scores require a nine-measure
   worksheet against cited feats and are a separate process. Emitting "M4.31" is a fabrication.
3. If no entry shows a demonstrated feat, set ceiling_entity to "" and magnitude "unassayed".
   That is a correct, expected answer for many sources.

MAGNITUDE BANDS -- capacity to DECIDE OUTCOMES at scale (owner ruling 2026-08-23, restating
Part Three's "what scale of conflict it can decide, not merely what it can break"). For a
person: who would they beat. For an equipable thing: how much stronger it makes its possessor.
For anything else: how much effect it has within the scope of what it can interact with. The
band names are the charter's own and the scale terms are exact: a planetary system is not a
planet, multiversal is not metaversal.
  M0 Mundane - a village
  M1 Heroic - a city or nation
  M2 Paragon - a continent
  M3 Worldshaker - A PLANET
  M4 Planetary Sovereign - A PLANETARY OR STELLAR SYSTEM
  M5 Stellar - star clusters, associations, nebulae
  M6 Galactic - a galaxy, group or cluster
  M7 Universal - a universe and its fundamental laws
  M8 Multiversal - whole multiverses
  M9 Metaversal - metaverses and xenoverses
  M10 Omniversal - everything
"""

SYNTH_SCHEMA = {
    "type": "object",
    "properties": {
        "ceiling_entity": {"type": "string"},
        "magnitude": {"type": "string"},
        "evidence": {"type": "string"},
        "rationale": {"type": "string"},
    },
    "required": ["ceiling_entity", "magnitude", "evidence", "rationale"],
}



def _mined_feats(rec):
    """{entity name: [feat sentences]} from whatever the miners have collected for this source.

    Reads the model-read cache first and falls back to the regex-mined one, so this improves on
    its own as `read.py` works through the roll.
    """
    import feats as _F
    out = {}
    try:
        hosts = json.load(open(_F.HOSTS, encoding="utf-8"))
    except Exception:
        silence.note("pipeline.py:mined_feats-hosts")
        return out
    host = hosts.get(rec["source"])
    if not host:
        return out
    # M23: was `re.sub(...)[:80] + ".json"` inline, one of four independent spellings of a lossy
    # key. `Magic 8 Ball` and `Magic 8-Ball` resolved to one file, so THIS loop would attach one
    # entity's mined feats to the other's name and hand them to the chapter that cites them.
    # `cachekey.load` proves the file's `entity` matches before the feats are believed.
    for e in rec["entries"]:
        for base in (os.path.join(HERE, "data", "readfeats"),
                     os.path.join(HERE, "data", "feats")):
            d, _fp = cachekey.load(base, host, e["name"],
                                   on_corrupt=lambda _p: silence.note("pipeline.py:mined_feats-corrupt"))
            if d is None:
                continue
            fl = [x.get("feat") for x in (d.get("feats") or []) if x.get("feat")]
            if fl:
                out[e["name"]] = fl
                break
    return out


def synthesis_blocks(rec):
    """The nomination blocks for one source, and the mined feat text behind them.

    ONE SPELLING OF THE BLOCK RULE, BECAUSE THERE WERE TWO AND THEY DISAGREED. Extracted
    2026-08-25 (run #31). `phase_synthesis` was rewritten under the owner's `FIX IT ALL`
    ruling of 2026-08-24 so that EVERY feat-bearing entry is nominated, fourteen per call,
    best band across blocks winning -- the m13 fix. `retry_synthesis.synthesise()` kept its
    own copy, `sorted(entries, by description length)[:14]`: a single ranked-then-truncated
    block, no feats consulted at all, under a docstring claiming the construction was
    "byte-identical to phase_synthesis". It was not, and a source that failed the main phase
    for an infrastructure reason was then re-scored by a WEAKER method than its neighbours --
    which is the one thing that docstring promised would not happen.

    This is the project's recorded failure shape (BUGS m138/m139, run #26's whole theme): a
    ruling gets applied to the file in front of the person applying it, and the identical
    construction one module over is never visited. The cure is not to copy the fix across; it
    is to leave only one place where the rule is written down. Both callers now read it here.
    """
    feats_for = _mined_feats(rec)
    with_feats = [e for e in rec["entries"] if feats_for.get(e["name"])]
    with_feats.sort(key=lambda e: -len(feats_for[e["name"]]))
    rest = sorted((e for e in rec["entries"] if not feats_for.get(e["name"])),
                  key=lambda e: -len(e.get("description", "")))
    # IT WAS A CAP. OWNER RULING 2026-08-25, and the old comment above this line is REWRITTEN
    # rather than merely deleted, because the way it was wrong is the instructive part.
    #
    # THE ORIGINAL JUSTIFICATION, VERBATIM: *"The description-only fallback stays a single ranked
    # block DELIBERATELY... a description is a wiki lead paragraph -- biography, not a deed --
    # and the evidence gate is looking for an act upon an object. Sampling more lead paragraphs
    # buys nothing."*
    #
    # WHY IT CANNOT STAND, and two independent readers flagged it before the owner did: the
    # argument refutes its own conclusion. If a lead paragraph genuinely cannot carry a ceiling
    # feat, then **the number kept is irrelevant** -- fourteen is as useless as four hundred, and
    # the honest form is to nominate none at all and record the source as unassayable. If a lead
    # paragraph CAN carry one, then keeping the top fourteen by description LENGTH is a ranked
    # truncation, and Hard Rule 0's own words apply exactly: *ranking then truncating is not
    # sampling, it is deciding on the entity's behalf that everything past the cutoff does not
    # exist.* There is no third reading in which fourteen is the right number.
    #
    # The owner ruled the second way: lead paragraphs CAN carry a ceiling feat. So the cap goes.
    # `rest` is already sorted longest-first, which is the ranking Hard Rule 0 explicitly still
    # permits and encourages -- the richest material lands in the first block, so an interrupted
    # run has read the best of it. What changes is that the tail is now REACHED rather than
    # discarded, in blocks of the same fourteen the feat-bearing path already uses.
    #
    # THE COST, stated because the ruling was asked for on exactly this basis: a feat-less source
    # with 900 entries becomes 65 nomination calls instead of 1. That is real spend on a
    # constrained pool, and it is the correct spend -- the alternative is a ceiling chosen from
    # the first fourteen paragraphs and published as though the whole source had been read.
    blocks = ([with_feats[i:i + 14] for i in range(0, len(with_feats), 14)]
              or [rest[i:i + 14] for i in range(0, len(rest), 14)])
    return (blocks, feats_for)


def synthesis_prompt(src, sample, feats_for, ci, nchunks, total):
    """The prompt for one nomination block. Same spelling for the main phase and the retry."""
    lines = []
    for e in sample:
        fl = feats_for.get(e["name"]) or []
        if fl:
            d = " | ".join(re.sub(r"\s+", " ", x)[:150] for x in fl[:3])[:420]
        else:
            d = re.sub(r"\s+", " ", e.get("description", ""))[:300]
        lines.append(f"- {e['name']} [{e.get('type','')}]: {d}")
    return (f"SOURCE: {src}\n\nCATALOGUED ENTRIES (nomination block {ci + 1} of "
            f"{nchunks}, {len(sample)} of {total} entries):\n"
            + "\n".join(lines) +
            "\n\nIdentify the power ceiling and magnitude band for this source.")


def phase_synthesis(c, st):
    """Per-source ceiling + band. ~186 units, roughly 45s each."""
    # A source that FAILED still had a synthesis block written, with empty fields. Filtering on
    # the block's mere presence therefore made failure permanent: the source could never appear
    # in `todo` again, no matter how many times phase 1 was re-run. Sixty-nine sources sat with
    # `ceiling_entity: ""` and no way back.
    #
    # It also mattered more than a retry usually does. Those sixty-nine include SpongeBob, Mario,
    # Overwatch, Yakuza, Fire Emblem and Gundam -- sources whose ceilings came back empty because
    # phase 1 examined them BEFORE their casts existed, and honestly found no entity to nominate
    # among places and items. They have casts now, so the nomination is worth making again.
    todo = [(p, r) for p, r in records()
            if not (r.get("synthesis") or {}).get("ceiling_entity")]
    log(f"phase 1 synthesis: {len(todo)} sources need a ceiling")
    done_keys = st["done"].setdefault("synthesis", [])

    for path, rec in todo:
        src = rec["source"]
        if src in done_keys:
            continue
        # Feed the entries most likely to carry a feat: longest descriptions first.
        #
        # Sized deliberately. Was 22 entries x 420 chars = ~2,300 input tokens; the ceiling
        # entity is essentially always in the top handful of longest descriptions, so the tail
        # was paying prompt-eval cost for nothing. 14 x 300 is ~1,100 tokens -- less than half
        # -- with no observed change in which entity gets nominated.
        # FEATS FIRST, descriptions only as a fallback.
        #
        # This sampled the longest DESCRIPTIONS, and a description is a wiki lead paragraph --
        # biography, not a deed. It is the identical failure that made entrypass return 99.6%
        # `unassayed`: the evidence gate is looking for an act upon an object and a lead
        # paragraph does not contain one. Overwatch was sampled with twelve of its fourteen
        # slots filled by real characters (Reaper, Soldier: 76, Junker Queen) and still nominated
        # nobody, because what it was shown about them was where they were born.
        #
        # The library now holds mined feats for these same entities. An entity with a feat on
        # record is exactly what a ceiling nomination wants to see, so those go first and carry
        # their feat text with them.
        # EVERY feat-bearing entry is nominated, fourteen per call, best band across chunks
        # wins. The fixed sample-of-14 could silently clamp a whole source to a lesser
        # ceiling whenever the true strongest entity ranked fifteenth by feat-count -- and
        # the clamp then cut that entity's own later evidence down to the wrong band (BUGS
        # m13, Hard-Rule-0-shaped, ruled by the owner 2026-08-24: FIX IT ALL). Ranking is
        # kept -- richest evidence leads, so an interrupted pass still saw the likeliest
        # ceiling first -- but no feat-bearing entry is ever excluded from nomination.
        # The rule itself now lives in `synthesis_blocks`, which the retry path reads too.
        chunks, feats_for = synthesis_blocks(rec)
        best = None
        for ci, sample in enumerate(chunks):
            prompt = synthesis_prompt(src, sample, feats_for, ci, len(chunks),
                                      len(rec["entries"]))
            # ONE RUNNER, ONE CONTEXT. See `ask()` -- this asked for 4096 while config declares
            # 12288, and Ollama holds a model at ONE size, so the difference bought a REBUILD
            # rather than a smaller window. Order 706215aabc5f.
            g = ask_pool_first(c, SYNTH_SYSTEM, prompt, SYNTH_SCHEMA, timeout=420,
                               tag="synthesis")
            if g is None:
                continue
            b = clean_band(g.get("magnitude"))
            # NO FEAT, NO BAND -- at phase 1 as well as phase 2. 70 of 211 sources once
            # carried a ceiling whose evidence field was the EMPTY STRING; an unevidenced
            # source ceiling does not misplace one entity, it tilts a whole shelf.
            _ev = (g.get("evidence") or "").strip()
            if b != "unassayed" and not valid_scale_note(_ev):
                b = "unassayed"
            r_ = int(b[1:]) if b != "unassayed" else -1
            if best is None or r_ > best[0]:
                best = (r_, g, b)
        if best is None:
            st["failed"].setdefault("synthesis", {})[src] = "ollama failure"
            save_state(st)
            continue
        got, band = best[1], best[2]

        rec["synthesis"] = {
            "ceiling_entity": (got.get("ceiling_entity") or "").strip(),
            "provisional_magnitude": band,
            "evidence": (got.get("evidence") or "").strip()[:600],
            "rationale": (got.get("rationale") or "").strip()[:900],
            "method": ("Band-only nomination by local model over the source's own catalogued "
                       "text. NOT a Custodial Assay: no nine-measure worksheet, no decimal, "
                       "no confidence interval. Treat as a provisional shelving hint that a "
                       "real Assay pass must confirm."),
            "assessed_at": datetime.datetime.now().isoformat(timespec="seconds"),
        }
        if not write_record(path, rec):
            # The synthesis exists only in memory; recording it done would lose it silently.
            st["failed"].setdefault("synthesis", {})[src] = "write denied"
            save_state(st)
            continue
        done_keys.append(src)
        # A later attempt succeeded, so the earlier failure is no longer true. Without this the
        # failed-set becomes a permanent record of every transient ollama hiccup, and a run that
        # fully recovered still reports twelve casualties -- which is how a healthy pipeline gets
        # mistaken for a damaged one.
        st.get("failed", {}).get("synthesis", {}).pop(src, None)
        st["units_done"] += 1
        save_state(st)
        log(f"  {src[:44]:46s} {band:10s} {rec['synthesis']['ceiling_entity'][:34]}")
        update_handoff(st)

    return True


# ------------------------------------------------------------------------------- phase 2

ENTRY_SYSTEM = """You are correcting catalogue metadata for an encyclopedia. You are given
entries with a name, a type, and a description transcribed from a reference source.

For each entry return:
  * `category` - the correct bucket, as a NUMBER 1-7:
      1 Persons  2 Places  3 Vessels & Things  4 Factions  5 Powers  6 Events  7 Media The commonest
    error to fix is an ability filed as an object: a named technique, transformation, release
    state or process is a POWER, never a Vessel. Vessels & Things means physical objects.
  * `scale_note` - a demonstrated feat of power or scale, ONLY if the supplied description
    actually states one (destruction caused, distance crossed, beings overcome). Quote or
    closely paraphrase the description. If the description shows no feat, return "".
    Do NOT estimate, infer, or import knowledge you have about this entity from elsewhere.
  * `magnitude` - the power band THIS entity's own supplied text demonstrates. Band only.
    Return "unassayed" unless the description states an actual feat. This is the single
    easiest field to get wrong: a description that calls someone "a powerful warrior" or "a
    legendary king" demonstrates NOTHING and is "unassayed". A description that says they
    destroyed a city is M3. Rank the feat, never the reputation.

      M0 a village         M1 a city or nation  M2 a continent
      M3 A PLANET          M4 A STELLAR SYSTEM  M5 star clusters
      M6 a galaxy          M7 a universe        M8 multiverses
      M9 metaverses        M10 everything

    Most entries are "unassayed" and that is the correct, expected answer. Do not reach for a
    band to avoid saying so -- these bands order the entire encyclopedia, and an inflated one
    files an ordinary soldier next to a god.

  * `topic` - which encyclopedia series this entity belongs to. The volumes are organised by
    TOPIC ACROSS THE WHOLE OMNIVERSE, not by which work it came from.

      Persons  a named individual
      Places   a world, region, city, plane, realm
      Factions a group, nation, order, organisation, or a people/race
      Weapons  an object whose attested use is combat -- INCLUDING relic and sacred weapons.
               A holy sword is a Weapon, not a Relic. If it is wielded to fight, it is here.
      Relics   a NON-weapon object of historical, sacred or reality-affecting significance
      Powers   a magic/tech system, technique, discipline or ability
      Events   a discrete happening within the fiction
      Wars     a sustained armed conflict specifically (a subset of Events, filed separately)
      Media    a work existing INSIDE the fiction (in-universe book, song, broadcast)

  * `subroom` - which SHELF inside the entry's category. This is NOT the same question as
    `topic`: `topic` says which encyclopedia volume the entity publishes into across the whole
    omniverse, `subroom` says where it sits on the shelf in this source's own catalogue.

    Answer "none" unless the category is one of the two that has shelves. "none" is the
    correct, expected answer for most entries -- every Person, Place, Faction, Power and Media
    entry is "none".

      Vessels & Things:
        Weapons      an object whose attested use is combat, including sacred and relic weapons
        Vehicles     a thing that carries or conveys -- ship, craft, tank, mount, mecha
        Armour       worn protection: armour, shields, helms
        Relics       a NON-weapon object of historical, sacred or reality-affecting significance
        Consumables  used up in the using: potions, food, ammunition-as-supply
        Materials    raw stuff and components, not yet a finished object
        Accessories  worn or carried minor items: rings, amulets, charms, trinkets
        Documents    written or recorded things: scrolls, tomes, maps, keys-as-tokens
        Technology   devices, machines, engines and systems that are objects rather than powers
      Events:
        Wars         a sustained armed conflict specifically

    If the entry is a vessel or thing and none of those shelves fits, answer "none" rather than
    forcing it. A wrong shelf is worse than an unshelved object.

BE TERSE. `scale_note` is at most 15 words when present, and "" otherwise -- and "" is the
right answer for most entries. Output length is the dominant cost of this pass: every wasted
word is multiplied by 52,000 entries.

Return one object per input entry, in the same order, keyed by the entry's index.
"""

ENTRY_SCHEMA = {
    "type": "object",
    "properties": {
        "results": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "index": {"type": "integer"},
                    "category": {"type": "integer"},
                    "scale_note": {"type": "string"},
                    "magnitude": {"type": "string"},
                    "topic": {"type": "string", "enum": [
                        "Persons", "Places", "Factions", "Weapons", "Relics",
                        "Powers", "Events", "Wars", "Media"]},
                    # REQUIRED, with an explicit "none" rather than optional. An absent key is
                    # the one shape that cannot be counted (BUGS m14); "none" is a real answer
                    # and the correct one for most entries.
                    "subroom": {"type": "string", "enum": list(SUBROOM_VALUES) + ["none"]},
                },
                "required": ["index", "category", "scale_note", "magnitude", "topic",
                             "subroom"],
            },
        }
    },
    "required": ["results"],
}

ENTRY_BATCH = 20

# A scale_note must record a DEMONSTRATED feat, not a vivid sentence. The model reliably
# ignores this instruction and echoes a fragment of the description instead -- observed:
# "witnesses a past age of flourishing creativity" (a vision, no feat) and "You manifest a
# circular amphitheater with a 50 foot radius" (a utility spell). So the instruction is
# backed by a deterministic filter: a feat names a quantity, a scale, or an act of
# destruction/creation at scale. Anything else is discarded.
# CORRECTED 2026-08-20 after a backscan of 10,574 catalogued entries found that ~90% of assigned
# bands rested on no evidence at all.
#
# The three patterns below were previously OR-ed together, so ANY ONE of them satisfied "no feat,
# no band". The middle one is a list of bare scale nouns, which meant that the phrase
# "resource-rich jungle planet" -- a description of a setting, containing no act by anybody --
# licensed a Magnitude. Measured on the corpus:
#
#     225 banded entries
#       7.1%  carried a number with a unit (and most of those were DATES)
#      38.2%  named a destructive act but no object or quantity
#      54.2%  contained neither an act nor a quantity of any kind
#
# Entries carrying a band on that basis included "one of the cities dedicated to the preservation
# of humanity" at M2, and "primordial cosmic being once called the 'Breaker of Worlds'" at M5 --
# a TITLE, at a band that means the gravitational binding energy of a star.
#
# The gate was testing for scale VOCABULARY. A feat is an ACT UPON AN OBJECT, or a measured
# quantity, and nothing else qualifies. Hence conjunction rather than disjunction.
#
# Real physical units only. "years" is deliberately absent: a date is not a magnitude, and it was
# letting "colonized in 2186" read as quantified evidence. Durations belong to Sustain and are
# scored there from their own worksheet.
_MAGNITUDE = re.compile(
    r"\d[\d,.]*\s*(?:km|kilometers?|kilometres?|miles?|meters?|metres?|light[- ]?years?|"
    r"astronomical units?|au|parsecs?|tons?|tonnes?|kilotons?|megatons?|gigatons?|"
    r"joules?|watts?|newtons?|kelvin|solar masses?|earth masses?|g(?:'s)? of (?:force|accel)"
    r")\b", re.I)

# An act, and a thing of consequence for it to be performed upon.
_ACT = re.compile(
    r"\b(?:destroy|annihilat|obliterat|shatter|erase|unmake|unmade|raze|razed|level(?:l?ed|s)?|"
    r"vapori[sz]|incinerat|disintegrat|sunder|split|cleave|collapse|wipe[ds]? out|"
    r"blow[ns]? (?:up|apart)|conquer|subjugat|reshap|rewr(?:ote|ite|iting)|"
    r"drain|consum|devour)\w*", re.I)
_OBJECT = re.compile(
    r"\b(?:planets?|worlds?|continents?|galax(?:y|ies)|universes?|multiverses?|"
    r"dimensions?|realit(?:y|ies)|stars?|suns?|moons?|solar systems?|timelines?|"
    r"civili[sz]ations?|cities|city|nations?|countries|country|fleets?|armies|army|"
    r"islands?|mountains?|oceans?|realms?|kingdoms?|empires?)\b", re.I)

# The entity must be the AGENT. "must be located, activated, and destroyed to save a planet"
# describes something done TO the subject and was licensing an M3.
_PAST_ACT = (r"destroyed|razed|shattered|obliterated|erased|vapori[sz]ed|annihilated|"
             r"levelled|leveled|consumed|devoured|drained|split|sundered|conquered")
_PATIENT = re.compile(
    # "must be located, activated, and destroyed" -- the intervening words carry commas, which an
    # earlier \w+ run could not cross, so this leaked an M3 for a thing that gets destroyed.
    r"\b(?:must be|to be|can be|was|were|is|are|been|being)\s+(?:[\w,]+\s+){0,5}"
    r"(?:" + _PAST_ACT + r")\b"
    # "stars consumed by Sanguilius" -- a past participle followed by an agent. The subject is
    # what was acted upon; the feat belongs to whoever is named after "by".
    r"|\b(?:" + _PAST_ACT + r")\s+by\b", re.I)

# A reputation is not a deed. "once called the Breaker of Worlds" reports what people say.
_REPUTATION = re.compile(
    r"\b(?:known as|called|titled|named|nicknamed|referred to as|epithet|moniker|"
    r"reputed|rumou?red|said to be|believed to|considered|regarded as|legend(?:s|ary)?"
    r"|myth(?:s|ical)?|prophec"
    # ADDED after the re-pass: the surviving SOURCE ceilings were almost all of the form
    # "GOLB is described as a dimension-spanning entity". A description of a description is not a
    # deed, and these are the most expensive bands in the library -- a source ceiling anchors every
    # entry beneath it, so an unearned one tilts a whole shelf rather than one entry.
    r"|described as|depicted as|portrayed as|presented as|characteri[sz]ed as"
    r"|stated to be|claimed to|purported|allegedly|apparently|seemingly"
    r")\w*", re.I)

# UNUSED. Nothing in src/ reads either name below -- grep confirms only their own definitions.
# valid_scale_note() below does NOT use this OR-of-three-patterns gate; it requires an act UPON
# an object (see _act_upon_object), which is exactly the conjunction the comment above this block
# explains replaced a disjunction like this one. Left here as the shape of the REJECTED approach,
# not as an alternative implementation someone could wire back in -- doing so would reopen the
# defect that comment describes.
_SCALE_PATTERNS = [_MAGNITUDE.pattern, _ACT.pattern, _OBJECT.pattern]
_SCALE_EVIDENCE = re.compile("|".join(_SCALE_PATTERNS), re.I)

# How close an act must sit to its object to count as acting upon it.
_PROXIMITY = 70


def _act_upon_object(text):
    """An act performed on something of consequence, close enough together to be one claim."""
    for m in _ACT.finditer(text):
        lo = max(0, m.start() - _PROXIMITY)
        window = text[lo:m.end() + _PROXIMITY]
        if _OBJECT.search(window):
            return True
    return False


# Stat-block mechanics. These are RESOLUTION PROCEDURE, not demonstrated acts, and the difference
# is the whole point of the invariant: "each creature within 5 feet must succeed on a Dexterity
# saving throw" describes how an outcome would be adjudicated at a table, and contains no evidence
# whatsoever about what the entity did to a world. A distance in feet inside such a clause is a
# rules radius, not a reach.
#
# Found by audit: 112 scale_notes (2.6%) carried meta-language, and the stat-block ones were
# supplying "scale" made entirely of saving throws and hit points.
_STATBLOCK = re.compile(
    r"\b(saving throws?|hit points?|temporary hit points?|armou?r class|challenge rating|CR \d+"
    r"|proficiency bonus|initiative|stat block|d20|advantage on the roll|spell slots?"
    r"|damage dice|\d+d\d+)\b", re.I)

# Setting words. These contaminate the PHRASING of an otherwise real feat -- "overthrew the Titans
# roughly 500 years before the campaign's start" is a genuine deed wearing one wrong word. The feat
# survives; the wording is flagged so the write phase rephrases rather than the evidence being
# thrown away.
_SETTING_META = re.compile(r"\b(campaign|adventure path|session|the table|module|sourcebook"
                           r"|players?|DMs?|game master)\b", re.I)


def valid_scale_note(text):
    """Keep a scale_note only if it actually evidences scale. Returns '' otherwise.

    Three gates, in order of severity:
      1. too short to say anything
      2. STAT-BLOCK mechanics -- rejected outright; a saving throw is not a feat
      3. no scale evidence at all
    """
    t = (text or "").strip()
    if len(t) < 8:
        return ""
    if _STATBLOCK.search(t):
        return ""

    # A measured quantity stands on its own -- that is what measurement means.
    if _MAGNITUDE.search(t):
        return t

    # Otherwise: an act, upon an object, performed BY the subject, and reported as done rather
    # than as said. All four conditions, because dropping any one of them is what produced a
    # library in which a city's dedication to preserving humanity was worth an M2.
    if not _act_upon_object(t):
        return ""
    if _PATIENT.search(t):
        # The subject is the target, not the doer. An earlier version allowed an escape hatch for
        # notes that ALSO contained an active verb, and it promptly matched "destroyed to save a
        # planet" and let the M3 through. The asymmetry decides it: a false negative costs an
        # honest `unassayed`, a false positive mints a Magnitude nobody earned. Refuse.
        return ""
    if _REPUTATION.search(t) and not _MAGNITUDE.search(t):
        return ""                       # a title or a rumour, not a deed
    return t


def scale_note_needs_rephrase(text):
    """True when a VALID feat is described in contaminated words. Not a rejection -- a flag."""
    return bool(text) and bool(_SETTING_META.search(text))


def entry_settled(e):
    """One entry is finished with: judged, or deliberately struck.

    ONE PREDICATE, TWO GATES (run #20). This existed twice, inline, and the two copies
    disagreed — which cost 66 batches an unbounded retry loop. The resume gate below said
    `catalogued or excluded`; the write-completion gate in `phase_entrypass` said `catalogued`
    alone. Since a struck entry is skipped by both loops that could ever set `catalogued`
    (the prompt build and the result walk), its `catalogued` key is never written, so any batch
    holding one could never satisfy the second gate — `done_keys.append(key)` never ran, the
    resume gate then always failed on membership, and the batch went back to the model on EVERY
    pass, for ever. Measured before the fix: 66 of 4,416 batches, one model call each, per pass,
    against a pool answering roughly a third of its calls.

    The fix is not the missing clause — it is that there is now only one place to put it. Both
    gates call this.
    """
    return bool(e.get("catalogued") or e.get("excluded"))


def batch_settled(key, done_keys, batch):
    """True when an entrypass batch may be skipped on resume.

    Pulled out of `phase_entrypass` so the rule can be tested without an Ollama call -- see
    verify_math section 18d. The rule is deliberately NOT "the key is recorded": a record's
    entry list grows after entrypass runs (doc ingest appends through write_record_catalogue),
    which widens the tail batch under a key already in `done_keys`. Membership plus a fully
    judged span is the honest gate; membership alone strands every later-appended entry.

    AN EXCLUDED ENTRY COUNTS AS SETTLED. `cleanup.py` strikes wiki-navigation cruft and
    description-less rules constructs by setting `catalogued = False` and writing an `excluded`
    reason. Under the old gate that unsettled the whole batch, which reopened it, which sent it
    back through `phase_entrypass` -- where `catalogued = True` is set unconditionally. So every
    exclusion was reverted by the next pass, and the marker recording WHY was read by nothing.
    Measured 2026-08-24: 149 entries carried `excluded`, and all 149 had already been flipped
    back to catalogued. Cleanup's entire effect on the corpus had been undone.

    A struck entry is a decision, not unfinished work."""
    return key in done_keys and all(entry_settled(e) for e in batch)


def phase_entrypass(c, st):
    """Per-entry category correction + grounded scale_note. Multi-day; fully resumable."""
    done_keys = st["done"].setdefault("entrypass", [])
    allrecs = records()
    log(f"phase 2 entrypass: {len(allrecs)} records, {sum(len(r['entries']) for _, r in allrecs):,} entries")


    for path, rec in allrecs:
        src = rec["source"]
        entries = rec["entries"]
        for start in range(0, len(entries), ENTRY_BATCH):
            key = f"{src}#{start}"
            batch = entries[start:start + ENTRY_BATCH]
            # A CLOSED BATCH IS NOT A CLOSED SPAN. The resume key is `source#start`, but the
            # span it names is `entries[start:start+B]` -- and a record's entry list GROWS after
            # entrypass has run over it (`ingest_doc.py` appends doc-derived entries through
            # write_record_catalogue). So the tail batch silently widens under a key that is
            # already in done_keys, and every entry appended past the old end is skipped
            # forever: never categorised, never given a scale_note, never banded.
            #
            # Found 2026-08-23 by health.py --preflight ("entries stranded in closed batches:
            # 5") -- Arcanum Worlds (Odyssey of the Dragonlords) grew from 292 to 297 entries
            # after batch #280 closed, and the 5 doc-ingested entries carried no `catalogued`
            # flag and no `topic`. This is the SAME failure mode the write-gate comment below
            # was written to kill; that fix stopped batches closing over unjudged entries, but
            # nothing reopened a batch that acquired unjudged entries afterwards.
            #
            # The gate is therefore the work, not the bookkeeping: skip only when the span as it
            # stands right now is fully judged. Re-doing a grown batch costs one call, which is
            # what the write-gate comment below already priced and accepted.
            if batch_settled(key, done_keys, batch):
                continue
            lines = []
            for i, e in enumerate(batch):
                # Struck entries are not sent to the model. They are not entities, so there is
                # nothing to categorise, and asking would spend a call to re-manufacture the
                # `catalogued` flag that cleanup deliberately cleared. The label keeps the TRUE
                # batch index so the result indices below stay aligned with `batch`.
                if e.get("excluded"):
                    continue
                # 380 -> 240 chars. Classification needs the opening clause ("X is a city in
                # ...", "a technique used by ..."), not the whole lead paragraph. Feats, when
                # present, are almost always stated early too.
                d = re.sub(r"\s+", " ", e.get("description", ""))[:240]
                lines.append(f"[{i}] {e['name']} (type: {e.get('type','')}): {d}")
            if not lines:
                # Every entry in this span was struck. Record the key so the span is not
                # rewalked forever, and spend no call on a batch with nothing to judge.
                if key not in done_keys:
                    done_keys.append(key)
                    save_state(st)
                continue
            # The category list lives in the system prompt only. It used to be repeated here
            # as well, paying ~200 input tokens per call across ~2,600 calls for a list the
            # model already had.
            # len(lines), NOT len(batch): struck entries are skipped above, so a span of 20
            # holding 3 excluded ones shows the model 17. Asking for "all 20" invited it to
            # invent verdicts for entries it was never shown -- harmless, because the index
            # guards below discard them, but it spent tokens and muddied the instruction.
            prompt = (f"SOURCE: {src}\n\nENTRIES:\n" + "\n".join(lines) +
                      f"\n\nReturn results for all {len(lines)} entries.")

            # This call names N entries by index and asks for a judgment on each. An answer
            # carrying no result whose index is one of the ones we ASKED about has judged
            # nothing, however well-formed it looks -- so it is a pool miss, not an empty
            # verdict, and the local arm gets its turn. See _pool_answer_usable.
            def _judged_something(g, _n=len(batch)):
                return any(isinstance(r.get("index"), int) and 0 <= r["index"] < _n
                           for r in (g.get("results") or []))

            # ONE RUNNER, ONE CONTEXT -- order 706215aabc5f, same as synthesis above.
            got = ask_pool_first(c, ENTRY_SYSTEM, prompt, ENTRY_SCHEMA, timeout=600,
                                 tag="entrypass", accept=_judged_something)
            if got is None:
                st["failed"].setdefault("entrypass", {})[key] = "ollama failure"
                save_state(st)
                continue

            for res in got.get("results", []):
                i = res.get("index")
                if not isinstance(i, int) or not (0 <= i < len(batch)):
                    continue
                # A struck entry was never in the prompt, so any result claiming to be one is
                # the model addressing an index it was not given. Honouring it would set
                # `catalogued = True` and undo the exclusion by the back door -- which is how
                # all 149 of them came back the first time.
                if batch[i].get("excluded"):
                    continue
                ci = res.get("category")
                if isinstance(ci, int) and 1 <= ci <= len(CATEGORIES):
                    batch[i]["category"] = CATEGORIES[ci - 1]
                # NEVER DISCARD WHAT THE GATE REJECTED. The first version assigned the gated
                # result straight over the field, so a rejected note left no trace: 51,611
                # entries ended up holding an empty string and ~46,000 candidate feats were
                # destroyed. The cost is not only the feats. It is that the rejection rate
                # became unauditable -- with the raw text gone there is no way to tell a gate
                # that is correctly refusing biography from one that is too tight, which is
                # exactly the question that matters before a Magnitude pass.
                raw = (res.get("scale_note") or "").strip()
                sn = valid_scale_note(raw)
                batch[i]["scale_note"] = sn[:500]
                if raw and not sn:
                    batch[i]["scale_note_rejected"] = raw[:500]
                else:
                    batch[i].pop("scale_note_rejected", None)

                # Band-clamp exactly as phase 1 does: accept only a clean M0-M10, and treat
                # anything else -- prose, a decimal, an empty string -- as unassayed. These
                # bands order the whole Persons series (Mx A-Z), so a malformed value would
                # silently misfile an entity rather than fail loudly.
                band = clean_band(res.get("magnitude"))

                # NO FEAT, NO BAND. A Magnitude with no surviving scale_note behind it is a
                # number with no evidence -- exactly what Charter Part Three's "no worksheet,
                # no number" rule (theorem H5, Vol. X.6) forbids. This caught a utility spell
                # that creates a wooden amphitheater being filed at M2 because the model
                # ranked the building's 50-foot radius as a power feat.
                #
                # These bands shelve the entire Persons series (Mx A-Z), so an unevidenced
                # band does real damage: it files an ordinary character beside a god.
                if not sn:
                    band = "unassayed"
                # A FICTION CANNOT BE OUT-SCALED BY ITS OWN INHABITANT -- the same clamp the
                # assay applies from SCOPE.json, here against this record's own synthesis
                # band. Without it the two passes could disagree forever: allsweep's band
                # reconcile found Starkiller Base at M5 inside an M4 source the night this
                # was added (2026-08-23).
                syn = ceiling_band((rec.get("synthesis") or {}).get("provisional_magnitude"))
                if band != "unassayed" and syn:
                    order = ["M%d" % n for n in range(11)]
                    if order.index(band) > order.index(syn):
                        band = syn
                batch[i]["magnitude"] = band

                # AN UNREADABLE TOPIC IS RECORDED, NOT DROPPED. `magnitude` has an explicit
                # "unassayed" for exactly this and `scale_note` keeps its rejected raw text --
                # `topic` alone failed its enum check by leaving no key at all, while
                # `catalogued = True` was still set below, so the resume gate never revisited
                # it. A missing topic is not inert: `worldseed` selects on `topic == "Places"`
                # and `weave` builds its per-shelf topic set from truthy values only, so the
                # entry was silently excluded from both, permanently, with nothing anywhere
                # saying so. A sentinel can be counted; an absent key cannot. (BUGS m14.)
                topic = (res.get("topic") or "").strip()
                if topic in TOPICS:
                    batch[i]["topic"] = topic
                    batch[i].pop("topic_rejected", None)
                else:
                    batch[i]["topic"] = "unclassified"
                    if topic:
                        batch[i]["topic_rejected"] = topic[:120]
                # The same shape for `subroom`, and CHECKED AGAINST THE ROOM rather than only
                # against the vocabulary: `Wars` is a shelf in Events and nowhere else, so a
                # `Wars` written under Vessels & Things is a rejection, not an acceptance.
                sub = (res.get("subroom") or "").strip()
                if sub and subroom_ok(batch[i].get("category"), sub):
                    batch[i]["subroom"] = sub
                    batch[i].pop("subroom_rejected", None)
                else:
                    batch[i]["subroom"] = SUBROOM_UNCLASSIFIED if sub else SUBROOM_NONE
                    if sub:
                        batch[i]["subroom_rejected"] = sub[:120]
                batch[i]["catalogued"] = True

            landed = write_record(path, rec)
            # A batch is done only when every entry in it carries a result AND the write that
            # carries those results actually reached the disk -- see `_landed`. The model is asked
            # for N and sometimes returns fewer, or returns an out-of-range index that the loop
            # above discards -- and marking the batch done on the WRITE rather than on the
            # RESULT stranded those entries permanently. 95 batches were sitting complete with
            # 378 entries inside them that had never been judged and never would be.
            #
            # An unfinished batch is simply not recorded, so the next run picks it up again. The
            # cost of re-doing a mostly-complete batch is one call; the cost of the old behaviour
            # was silent, permanent data loss.
            if landed and all(entry_settled(e) for e in batch):   # same predicate as the
                if key not in done_keys:      # a reopened grown batch is already recorded --
                    done_keys.append(key)     # re-appending would grow the resume list forever
                st.get("failed", {}).get("entrypass", {}).pop(key, None)   # see phase 1: a
                # later success retires the earlier failure, so the failed-set stays a list of
                # things actually still broken rather than a scar log.
                #
                # ONLY ON THIS BRANCH, since the run #33 sweep. The pop used to sit outside the
                # if/elif/else and fired on all three paths -- including "the write was denied"
                # and "judged 6 of 20" -- so any non-None answer from the model retired a
                # recorded failure whether or not anything landed. Its correctly-gated twin in
                # `phase_synthesis` about four hundred lines above only reaches its pop after
                # `if not write_record(...): ...; continue`. The damage is to the health signal
                # rather than to the corpus, and that is worse than it sounds: a batch under
                # sustained write contention could sit at ZERO entries in `st["failed"]`, which
                # is precisely the number `update_handoff` publishes to the owner as "Failures
                # logged" in `handoff/RUN_STATUS.md`. This library runs unattended for days on
                # that one line. It went quiet exactly when it should have been loudest.
            elif not landed:
                log(f"    batch {key} judged in full but its write was denied - left open")
                # RECORDED, NOT ONLY LOGGED, for the same reason and in the same words as
                # `phase_synthesis`: a denied write is the failure most likely to repeat (the
                # Windows lock this project hits routinely), and a failure whose only trace is
                # a line in `state/pipeline.log` is not one the handoff can count.
                st["failed"].setdefault("entrypass", {})[key] = "write denied"
            else:
                log(f"    batch {key} returned {sum(1 for e in batch if entry_settled(e))}"
                    f"/{len(batch)} - left open for retry")
                # NOT recorded as a failure. A short answer is ordinary model behaviour and the
                # batch is simply left open for the next run to redo; filing it would fill the
                # failed-set with routine retries, which is the same way an alarm that always
                # sounds becomes furniture.
            st["units_done"] += 1
            save_state(st)
        log(f"  {src[:50]:52s} done")
        update_handoff(st)

    return True


# ------------------------------------------------------------------------------- handoff

_HANDOFF_CACHE = {"at": 0.0, "counts": None}
HANDOFF_RECOUNT_S = 120


def update_handoff(st):
    try:
        # Re-parsing every record after EVERY unit was fine at 254 entries a source and is not
        # fine now that marvel.json alone holds 30,207 -- the status file becomes the heaviest
        # thing in the phase. The counts change slowly; the file only has to be roughly live.
        import time as _t
        if _HANDOFF_CACHE["counts"] and _t.time() - _HANDOFF_CACHE["at"] < HANDOFF_RECOUNT_S:
            total, with_syn, catted, n_recs = _HANDOFF_CACHE["counts"]
        else:
            recs = records()
            total = sum(len(r["entries"]) for _, r in recs)
            with_syn = sum(1 for _, r in recs if r.get("synthesis"))
            catted = sum(1 for _, r in recs for e in r["entries"] if e.get("catalogued"))
            n_recs = len(recs)
            _HANDOFF_CACHE.update(at=_t.time(), counts=(total, with_syn, catted, n_recs))
        with open(os.path.join(HERE, "data/SWEEP_ROLL.json"), encoding="utf-8") as f:
            roll = json.load(f)
        have = sum(1 for r in roll if r.get("entry_count", 0) > 0)

        # The table is DERIVED from IMPLEMENTED, never hand-maintained. The hand-written
        # version listed phases 4-8 as "to build" long after all eight existed, and this file
        # is rewritten after every unit -- a stale table here is published continuously.
        phase_rows = chr(10).join(
            "| %d | `%s` | %s |" % (i, name,
                                    "**built**" if i in IMPLEMENTED else "to build")
            for i, name in enumerate(PHASES, 1))
        phase = st.get("phase", 1)
        name = PHASES[phase - 1] if 1 <= phase <= len(PHASES) else "?"
        fails = sum(len(v) for v in st.get("failed", {}).values())

        # AND THE SAME ARGUMENT APPLIES TO THE TABLE UNDERNEATH THE LADDER, which is still
        # hand-written (order 4c4c8c24e34c). Its verify_math row published "237 independent
        # checks across 17 sections" while the battery had grown to 35 numbered sections and
        # ~967 `check(` sites -- an understatement of more than half the sections, republished
        # after every unit into the file the owner reads to judge an unattended run. The counts
        # are simply GONE rather than re-transcribed: nothing downstream reads them, and a
        # description that carries no number cannot go stale. Deriving them would mean running
        # verify_math from here, which is unsafe concurrently with the pipeline (order
        # c349a51ee2c5). The other transcribed figures in that table were re-checked the same
        # day and hold: tells 60+31+15+32 = 138, and `custodes.CUSTODES` is ten.
        md = f"""# PANSCRIPTUM — AUTONOMOUS RUN STATUS

*Rewritten automatically by `src/pipeline.py` after every completed unit.*
*Last update: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}*

## Where the run is

| | |
|---|---|
| Current phase | **{phase} — {name}** |
| Units completed this run | {st.get('units_done', 0):,} |
| Failures logged | {fails} |

## Corpus

| | |
|---|---|
| Sources catalogued | **{have}/{len(roll)}** |
| Records with entries | {n_recs} |
| Total entries | **{total:,}** |
| Sources with a ceiling nominated (phase 1) | {with_syn}/{n_recs} |
| Entries through the judgment pass (phase 2) | {catted:,}/{total:,} |

## Phase ladder

| # | phase | state |
|---|---|---|
{phase_rows}

Volumes are organised by **topic across the omniverse**, never by source IP.

The runner stops cleanly at the first unimplemented phase rather than faking it.

## Built alongside the pipeline

These run standalone and do not block the sweep.

| module | what it is |
|---|---|
| `verify_math.py` | the battery: independent checks that recompute, never re-call |
| `derivation.py` | the ledger: every quantity names its parents, or the graph fails |
| `assay.py` `rigor.py` `custodes.py` | the Assay, commensuration, and the ten-Custos college |
| `tiers.py` `sevenfold.py` `grounding.py` | the cosmological tiers and the declared 1–7 shelving |
| `address_space.py` `profile.py` | the shelfmark, and the whole world in one 30-char string |
| `worldseed.py` `burgs.py` | map parameters and settlements by the rank-size rule |
| `navtree.py` `build_terminal.py` | the Registry Terminal (`output/registry_terminal.html`) |
| `audit.py` `cleanup.py` | the backscan and its repairs |
| `tells.py` `style_audit.py` | 138 machine-writing tells; Rule 7 is generated from the list |

## Files

- `state/PIPELINE_STATE.json` — resume point (atomic writes; safe to kill the process)
- `state/pipeline.log` — append-only run log
- `handoff/AUTONOMOUS_PLAN.md` — the full plan for every phase

## Restarting

```
python3 src/pipeline.py            # resumes exactly where it stopped
python3 src/pipeline.py --status   # no work, just report
```

**Run one instance only.** Two concurrent runners both write `PIPELINE_STATE.json` and the same
record files; that happened on 2026-08-21 and the records survived by luck. Check before starting:

```
powershell -Command "Get-CimInstance Win32_Process -Filter \"Name='python.exe' or Name='pythonw.exe'\" | Select CommandLine"
```
"""
        os.makedirs(os.path.dirname(HANDOFF), exist_ok=True)
        # THE LAST UNRETRIED WRITE IN THIS FILE. Every other artifact here -- `save_state`,
        # `write_record`, `write_record_catalogue`, `land_json` -- lands through
        # `silence.replace_retry`, which outwaits the Windows reader-holds-the-target denial
        # this project hits routinely; this one called `os.replace` directly and simply lost
        # the round to the `except` below. And the temp NAME carried neither pid nor thread, so
        # two writers of this file collide on the temp itself and the loser can rename its own
        # half-written copy over the winner's -- the collision `silence.write_json` was built
        # to make unavailable at twelve sites on 2026-08-25, still open at this one. Both halves
        # matter here specifically because `RUN_STATUS.md` is the file the owner reads to decide
        # whether an unattended multi-day run is healthy. (run #33)
        #
        # GATED (run #38). The paragraph above names the stake and the call then discarded the
        # answer. `replace_retry` does not raise on a denial -- that is its contract -- so the
        # `except` below could never see one, and a refused rename left the PREVIOUS run's
        # RUN_STATUS.md in place with its earlier counts and phase ladder. The owner reads that
        # file to decide whether an unattended multi-day run is healthy; a stale copy under a
        # silent success is the wrong answer, not a missing one. Reported through `log`, which
        # both prints and lands in state/pipeline.log where an unattended run's trace lives.
        tmp = "%s.%d.%d.tmp" % (HANDOFF, os.getpid(), threading.get_ident())
        with open(tmp, "w", encoding="utf-8") as f:
            f.write(md)
        if not silence.replace_retry(tmp, HANDOFF):
            silence.note("pipeline.py:handoff-denied")
            log("  (handoff NOT updated: replace refused -- %s still shows the PREVIOUS run's "
                "figures. Do not read it as current.)" % os.path.basename(HANDOFF))
    except Exception:
        log("  (handoff update failed: " + traceback.format_exc(limit=1).strip() + ")")


def _chain_landed(CH, out):
    """Did phase 4's artifact actually reach the disk? -> True/False.

    THE ONE PHASE THAT COULD NOT USE `gate_done`, and therefore the one that reintroduced the
    bug `gate_done` exists to close. Every other phase in this file writes through `land_json`,
    which returns a landed/not-landed verdict; phase 4 writes through `chain.write_result`,
    which is the right thing to do (one schema, one writer, see that function's own docstring)
    but which returns the DATA it tried to write, unconditionally, whatever the disk said. A
    denied rename there is only ever printed to stderr. So the call site had no verdict to gate
    on and appended its done-key regardless -- and because the done-key is permanent, no later
    run would ever redo it. `CHAIN.json` would keep the PREVIOUS cycle's fit forever while
    `PIPELINE_STATE.json` recorded phase 4 as complete: the exact silent, permanent loss m36
    closed at the twelve `land_json` sites, surviving at the thirteenth. Found by the run #33
    sweep.

    ASKED OF THE DISK, NOT OF THE WRITER, because the writer is not the one that can be wrong
    here -- the rename is. `write_result` hands back the document it built, so reading the file
    and comparing it to that document answers the only question that matters: is what is on
    disk this cycle's fit or last cycle's? Compared through a json round-trip because the
    document holds tuples (`unmatched` comes from `Counter.most_common`) that come back from
    the file as lists, and a tuple/list mismatch would report a landed write as denied. The
    file is a few kilobytes; this costs nothing once per run.
    """
    try:
        with open(CH.OUT, encoding="utf-8") as f:
            on_disk = json.load(f)
    except Exception:
        silence.note("pipeline.py:chain-artifact-unreadable")
        return False
    return on_disk == json.loads(json.dumps(out))


def phase_chain(c, st):
    """Phase 4 -- the Chain of Defeats. See chain.py for the reasoning.

    This existed as a standalone module and NOT as a phase, so the runner reached phase 4, found
    no `phase_chain`, and stopped cleanly every single time -- reporting "not implemented yet"
    about a module that was finished and working. Phase 4 only ever ran when somebody invoked it
    by hand, and phases 5 through 8 were never even attempted, because the runner never got past
    the gap. A finished stage that nothing dispatches to is indistinguishable from a stage that
    was never written, which is this project's defect wearing yet another hat.

    Charter Part Three names three kinds of evidence: a witnessed feat, an instrument reading,
    and a suffered defeat. The first two are what phases 1-2 collect. This is the third, and it
    is the only one that CHECKS the others -- if the Assay puts A above B while the source
    records B beating A, that is a defect visible without anyone's opinion.
    """
    import chain as CH
    rows = CH.harvest()
    log(f"phase 4 chain: {len(rows):,} sentences read like a contest outcome")
    if len(rows) < 10:
        log("  too few contests on record to fit anything; leaving the graph empty")
        mark_done(st, "chain")
        st["units_done"] += 1
        save_state(st)
        return True     # an empty graph IS this phase's finished result, not an unfinished one

    edges, unmatched, prov = CH.extract(rows, workers=c.get("workers", 8))
    edges = CH.adjudicate_mutuals(edges, prov)
    log(f"  {len(edges):,} distinct edges, {sum(edges.values()):,} recorded wins")

    res = CH.fit(edges, prior=0.5)
    if res.get("error"):
        # Ford (1957): the Bradley-Terry MLE exists and is unique only on a strongly connected
        # graph. Refusing is the correct answer, and it is a RESULT -- the edges are kept and the
        # graph is the finding.
        log(f"  no fit: {res['error']} -- the edges stand as the result")
    else:
        log(f"  identified: {res.get('identified')}  components: {len(res.get('components', []))}"
            f"  deviance/df: {res.get('deviance_per_df')}")

    out = CH.write_result(edges, res, unmatched)   # one schema, one writer -- see write_result
    ok = gate_done(st, "chain", [_chain_landed(CH, out)])   # ... and the thirteenth landing gated
    st["units_done"] += 1
    save_state(st)
    return ok


def phase_cosmology(c, st):
    """Phase 5 -- chart the tiers, and answer the First Argument per cosmos.

    Every piece of this existed and nothing dispatched to it. `tiers.chart` places each source in
    a multiverse, metaverse, xenoverse and hyperverse from the resonance graph phase 3 built;
    `grounding` answers what each cosmos says about its own origin; `cosmography.census` gives the
    population arithmetic; `address_space` turns a tier stack into a real address, `TOTAL_BITS` wide -- no
    number transcribed here, because the upper-tier widths are read out of TIERS.json at import
    and a re-charting moves them without touching this file (address_space.py says so at length,
    having gone stale twice; profile.py:20 was carrying a third stale copy, 89 against a live 88,
    when this was written). Four
    finished modules and no phase, so none of it ever ran inside the pipeline.

    What comes out is the shelving skeleton: which universe a thing is in, as a number the Ladder
    can read, instead of the charter's honest-but-empty `omega > ? > ?` placeholder.
    """
    import tiers as T
    import grounding as G
    import cosmography as CG
    import address_space as AS

    # ORDER 525dd7bbffed: GROUNDINGS.json now lands BEFORE TIERS.json, not after. `T.chart()`
    # derives the hyperverse/own_grounding columns from data/GROUNDINGS.json AS IT STANDS ON
    # DISK (`_load_groundings`), so charting before this run's groundings were written meant
    # TIERS.json always reflected the PREVIOUS run's groundings -- and on a fresh tree, where
    # GROUNDINGS.json does not exist yet when chart() first reads it, every row came out
    # hyperverse 5 / hyperverse_type 'ungrounded' / own_grounding 'ungrounded'. `address_space`
    # reads TIERS.json AT IMPORT and a re-charting moves the upper-tier widths (its own header
    # says so), so a bootstrap run silently re-charted the top of the Ladder of Being. This is
    # remedy (a) from the order: compute and land GROUNDINGS.json first, THEN chart and land
    # TIERS.json, so the two agree within a single run. `classify_source` does not depend on
    # anything `chart()` produces, so nothing else here has to change.
    #
    # `srcs, w, shared` are fetched via `tiers._graph()` -- the exact call `chart()` makes
    # internally when given none -- so grounds are computed over the SAME source domain
    # `charted` used to be built from, and handed to `chart()` below so it does not redo the
    # graph build a second time.
    srcs, w, shared = T._graph()

    # classify_source takes the RECORD, not the source name -- it reads the catalogue's ORIGIN
    # entries to see what a cosmos says about its own beginning. Passing the name gave 209
    # AttributeErrors and 209 sources reported "ungrounded", which is a real category in the
    # charter and was therefore completely invisible as a bug. The failure ledger caught it:
    # 419 identical silent:phase_cosmology-ground entries, which is not what a real finding
    # looks like.
    import weave_index as WI
    records = {r["source"]: r for r in WI.load_records()}
    grounds = {}
    for src in srcs:
        rec = records.get(src)
        if not rec:
            grounds[src] = {"type": G.UNGROUNDED, "why": "no catalogue record"}
            continue
        try:
            grounds[src] = G.classify_source(rec)
        except Exception:
            silence.note("pipeline.py:phase_cosmology-ground")
            grounds[src] = {"type": G.UNGROUNDED}
    def _kind(v):
        if isinstance(v, dict):
            return v.get("type") or v.get("grounding") or "ungrounded"
        return str(v)
    kinds = collections.Counter(_kind(v) for v in grounds.values())
    log("  grounding: " + ", ".join("%s %d" % (k, n) for k, n in kinds.most_common(6)))
    landed = [land_json(os.path.join(HERE, "data/GROUNDINGS.json"), grounds)]

    # chart() returns a tuple; the first element is the per-source tier stack. Unpacking by
    # position rather than assuming a dict, because assuming cost a TypeError on the first run.
    # `srcs, w, shared` passed through so this reuses the graph built above instead of
    # recomputing it, and so `chart()` reads the GROUNDINGS.json this same call just landed.
    charted = T.chart(srcs, w, shared)
    if isinstance(charted, tuple):
        charted = charted[0]
    log("phase 5 cosmology: %d sources charted across the tiers" % len(charted))
    landed.append(land_json(os.path.join(HERE, "data/TIERS.json"), charted))

    cen = CG.census("STANDARD")
    log("  census: %.3g worlds, %.3g in a habitable zone, %.3g civilisations extant"
        % (cen["exoplanets"], cen["habitable_zone_rocky"], cen["civilizations_extant"]))
    landed.append(land_json(os.path.join(HERE, "data/CENSUS.json"), cen))

    # ABSENT AND CORRUPT ARE DIFFERENT ANSWERS -- the ruling phases 6 and 7 carry (:1948 and
    # :2054) and phase 5 never got. One `except Exception` made an unparseable WORLDSEEDS.json
    # read as an empty seed set, and the SHELFMARKS.json write below is UNCONDITIONAL: `{}` went
    # over a file holding 1,016 world shelfmarks, `land_json` returned True, and `gate_done` saw
    # all-True and closed phase 5 permanently. Phase 7's `_phase_input` does not catch the
    # aftermath either, because `{}` PARSES -- so the emptied map shelves the whole library with
    # `shelfmark: None` and closes phase 7 too. Two phases shut over a file nothing ever read.
    _ws = os.path.join(HERE, "data/WORLDSEEDS.json")
    try:
        seeds = json.load(open(_ws, encoding="utf-8"))
    except FileNotFoundError:
        # A first run legitimately has no seeds; worldseed.py has not encoded any yet.
        silence.note("pipeline.py:phase_cosmology-seeds-absent")
        seeds = {}
    except Exception as e:
        silence.note("pipeline.py:phase_cosmology-seeds-corrupt")
        log("phase 5 cosmology: WORLDSEEDS.json EXISTS BUT WILL NOT PARSE (%s) -- refusing to "
            "re-address the library from an empty seed set (that would read as a mass "
            "un-addressing). Leaving phase 5 open; the next run retries once it is rewritten."
            % type(e).__name__)
        return False
    marks = {}
    for desig in seeds:
        src = desig.split("::")[0]
        addr = AS.assign(desig, charted.get(src) or {})
        marks[desig] = {"address": addr, "shelfmark": AS.shelfmark(addr),
                        "map_seed": AS.map_seed(addr)}
    dupes = len(marks) - len({v["address"] for v in marks.values()})
    log("  addressed %d worlds, %d collision(s)" % (len(marks), dupes))
    # AND THE SECOND HALF OF THE SAME GUARD, which the absent path needs too. Zero marks written
    # over a standing map is not a re-address, it is a deletion wearing the shape of one -- and
    # nothing downstream can tell the difference, because every shelfmark in SHELVES.json comes
    # from this file. Same asymmetry `write_record` applies to a cast: a merge never shrinks one.
    # A SHELFMARKS.json that is present but unreadable counts as something to lose, because
    # "I don't know what is in it" is exactly the answer Hard Rule -1 says must STOP.
    _sm = os.path.join(HERE, "data/SHELFMARKS.json")
    if not marks:
        try:
            with open(_sm, encoding="utf-8") as f:
                standing = len(json.load(f))
        except FileNotFoundError:
            standing = 0        # nothing on the shelf yet, so an empty map loses nothing
        except Exception:
            standing = None
        if standing is None or standing > 0:
            silence.note("pipeline.py:phase_cosmology-would-empty-shelfmarks")
            log("phase 5 cosmology: 0 worlds addressed, but SHELFMARKS.json already holds %s -- "
                "refusing to write an empty map over a standing one. Leaving phase 5 open; fix "
                "the seed set (or say so deliberately) rather than letting this land."
                % ("an unreadable map" if standing is None else "%d shelfmark(s)" % standing))
            return False
    landed.append(land_json(_sm, marks))

    ok = gate_done(st, "cosmology", landed)
    st["units_done"] += 1
    save_state(st)
    return ok


def phase_history(c, st):
    """Phase 6 -- the Chain of Record: how far each shelf lags the registry, and what is
    therefore contemporary with what.

    `tempus` settles a question the Chronicle had been quietly assuming an answer to.
    Simultaneity between universes has no physical referent -- there is no shared frame, so "at
    the same time" means nothing between them. The library's `now` is INSTITUTIONAL: two events
    are contemporary iff they were accessioned together.

    So this computes the accessioning, not a date. Each source's apparent lag from the registry
    comes from X.7's propagation metric over its charted tier stack -- a shelf nested deeper is
    further from the Communion and its news arrives later. Shelves whose lag agrees to within the
    tolerance are contemporary, and that grouping is the only claim about omniversal time the
    charter can actually support.

    Written against tempus's REAL surface. A first draft called `TP.mark()`, which does not
    exist, and reported "0 shelves given an ascension mark" -- a phase that ran, returned an
    empty result, and looked like a finding rather than a wrong call. That is this project's
    signature defect, committed inside a phase written to close it, which is worth leaving in the
    record.
    """
    import tempus as TP
    # ABSENT AND CORRUPT ARE DIFFERENT ANSWERS. One `except Exception` gave both the same
    # message ("phase 5 has not run") and, worse, the same consequence: phase 6 then marked
    # itself DONE with an empty result, so an unreadable TIERS.json was never looked at again.
    # A missing file genuinely means phase 5 has not run and there is nothing to do; a file that
    # exists but will not parse means phase 5's write was damaged, and the honest response is to
    # leave phase 6 OPEN so the next run retries once phase 5 has rewritten it. (BUGS m6.)
    _tp = os.path.join(HERE, "data/TIERS.json")
    try:
        tiersd = json.load(open(_tp, encoding="utf-8"))
    except FileNotFoundError:
        silence.note("pipeline.py:phase_history-tiers-absent")
        log("phase 6 history: no charted tiers on disk -- phase 5 has not run")
        tiersd = {}
    except Exception as e:
        silence.note("pipeline.py:phase_history-tiers-corrupt")
        log("phase 6 history: TIERS.json EXISTS BUT WILL NOT PARSE (%s) -- phase 5's write was "
            "damaged. Leaving phase 6 open rather than recording an empty result; the next run "
            "retries after phase 5 rewrites it." % type(e).__name__)
        return False
    if not tiersd:
        mark_done(st, "history")
        st["units_done"] += 1
        save_state(st)
        return True     # nothing charted to write a chronicle from; a correct empty result

    # The registry sits at the apex. A shelf's distance from it is how deep its tier stack goes
    # before a tier is unknown -- an unnested shelf is close to the Communion, a shelf inside a
    # xenoverse inside a hyperverse is far.
    TIER_ORDER = ("hyperverse", "xenoverse", "metaverse", "multiverse")
    # The shelf everything is measured from. The Concordance is a lightcone with an origin, and
    # this is it: the shelf the Communion keeps its register on.
    # CONVENTION, and a soft one: the registry shelf is the alphabetically first charted
    # source, which today is "2112 (Rush)". Nothing in the charter designates a registry shelf
    # yet, and every lag below is RELATIVE to this origin -- consistent within a run, arbitrary
    # across the doctrine. When the owner designates one, pin it here and every lag re-derives.
    REGISTRY_SHELF = sorted(tiersd)[0]

    def depth(stack):
        d = 0
        for t in TIER_ORDER:
            if (stack or {}).get(t) is not None:
                d += 1
        return d

    lags, marks = {}, {}
    for src, stack in sorted(tiersd.items()):
        d = depth(stack)
        # apparent_lag_years takes two SHELVES and walks X.7's propagation graph between them --
        # it is not a function of depth. The registry is the reference shelf, so every source is
        # measured against it, and a source with no shared furniture returns a null lag, which is
        # a real answer meaning "the relation is mediated or absent".
        try:
            got = TP.apparent_lag_years(REGISTRY_SHELF, src)
            lag = (got or {}).get("lag_years") if isinstance(got, dict) else got
        except Exception:
            silence.note("pipeline.py:phase_history-lag")
            lag = None
        lags[src] = lag
        marks[src] = {"tier_depth": d, "apparent_lag_years": lag,
                      "grounding": (stack or {}).get("own_grounding")}
    log("phase 6 history: %d shelves placed against the Chain of Record" % len(marks))

    groups = collections.defaultdict(list)
    for src, m in marks.items():
        groups[m["tier_depth"]].append(src)
    biggest = max((len(v) for v in groups.values()), default=0)
    log("  %d contemporaneity classes by ratification depth, largest holds %d shelves"
        % (len(groups), biggest))
    for d in sorted(groups):
        known = [lags[x] for x in groups[d] if isinstance(lags.get(x), (int, float))]
        log("    depth %d: %4d shelves, %d with a measurable lag%s"
            % (d, len(groups[d]), len(known),
               (", median %.0f yr" % sorted(known)[len(known) // 2]) if known else ""))

    # A closed timelike shelf spends no reference time and can therefore never accession. That is
    # a real category in the charter, not an error, and it belongs in the record.
    try:
        loops = TP.loop_report(1000)
    except Exception:
        silence.note("pipeline.py:phase_history-loops")
        loops = None

    landed = [land_json(os.path.join(HERE, "data/CHRONICLE.json"),
                        {"marks": marks, "loops": loops,
                         "contemporary": {str(k): v for k, v in sorted(groups.items())}},
                        default=str)]
    ok = gate_done(st, "history", landed)
    st["units_done"] += 1
    save_state(st)
    return ok


def phase_shelve(c, st):
    """Phase 7 -- put every entry on a shelf, with a real address and a real spine code.

    This is where the library stops being a database. Each entry takes the charter's
    Collection/Set/Series/Volume spine code and a Ladder-of-Being shelfmark from the address
    space. Everything it needs was built in phases 3 to 6; nothing until now put them together.

    Hard Rule 2 is enforced rather than worked around: about half the roll is not in the charter's
    Acquisitions Index, and inventing a spine code for those is exactly what that rule forbids.
    They are RECORDED as unspined, which is a finding the owner can act on, not a gap.
    """
    import address as AD
    import weave_index as WI

    # Absent is tolerable, corrupt is not -- same distinction as phase 6, and for the same
    # reason. Every entry below takes its `tier` from tiersd and its `shelfmark` from marks, so
    # reading an unparseable file as `{}` shelves the WHOLE library tierless and shelfmarkless
    # and then marks phase 7 done, permanently. If phases 5/6 simply have not run yet the files
    # are missing, and placing entries by spine code alone is the intended partial result.
    def _phase_input(name):
        try:
            return json.load(open(os.path.join(HERE, "data", name), encoding="utf-8")), None
        except FileNotFoundError:
            silence.note("pipeline.py:phase_shelve-%s-absent" % name)
            return {}, None
        except Exception as e:
            silence.note("pipeline.py:phase_shelve-%s-corrupt" % name)
            return None, type(e).__name__

    marks, m_bad = _phase_input("SHELFMARKS.json")
    tiersd, t_bad = _phase_input("TIERS.json")
    if m_bad or t_bad:
        log("phase 7 shelve: a phase input EXISTS BUT WILL NOT PARSE (%s) -- refusing to shelve "
            "the library with empty tiers/shelfmarks and mark itself done. Leaving phase 7 open."
            % (m_bad or t_bad))
        return False

    def spine_of(src):
        try:
            return AD.spine_code_for(src)
        except Exception:
            silence.note("pipeline.py:phase_shelve-spine")
            return None

    # THE PROMOTION LADDER (owner amendment 2026-08-24). A source's shelf RANK follows the size
    # of its cast: >=400 a Series, >=900 a Grand Series, >=3000 a Set. Applied automatically, by
    # the owner's ruling -- and one-way, by `address.promote`, because demoting on a bad read
    # would rewrite an address downward and break every cross-reference aimed at it.
    #
    # NOTE the field is `rank`, not `tier`: `tier` in this record already means the COSMOLOGY
    # tier (hyperverse/xenoverse/...) read from TIERS.json a few lines above. Two different
    # hierarchies, and collapsing them into one name would have made both unreadable.
    ranks_p = os.path.join(HERE, "data", "SHELF_RANKS.json")
    try:
        with open(ranks_p, encoding="utf-8") as f:
            ranks = json.load(f)
    except FileNotFoundError:
        # Deliberately silent, and now marked as such (run #20). This is the only bare handler
        # in the file that called neither `silence.note` nor `log` nor carried the exemption
        # string — three lines above, `_phase_input` notes the identical absent-file case, so
        # the inconsistency read as an oversight rather than a decision. It IS a decision: on a
        # first run nothing has been ranked yet, every source starts unranked, and `AD.promote`
        # builds the ranking from scratch. An empty prior here is the correct starting state,
        # unlike a CORRUPT one — which the handler below refuses, because re-ranking from an
        # empty prior would read as a mass demotion.
        _ = "silence-exempt: no ranking yet is the correct first-run state, not a failure"
        ranks = {}
    except Exception:
        silence.note("pipeline.py:phase_shelve-ranks-corrupt")
        log("phase 7 shelve: SHELF_RANKS.json will not parse -- leaving phase open rather than "
            "re-ranking the library from an empty prior (that would read as a mass demotion)")
        return False

    promoted = []
    shelved, unspined = {}, set()
    for r in WI.load_records():
        src = r["source"]
        spine = spine_of(src)
        if not spine:
            unspined.add(src)
        n = len(r.get("entries", []))
        prior = ranks.get(src) or {}
        was = prior.get("rank")
        now = AD.promote(was, n)
        # A PROMOTION IS NOT A RE-SHELVING. The rank is measured; the ADDRESS is curatorial, and
        # Hard Rule 2 forbids this code inventing one. A source that outgrows Volume into Series
        # needs its spine code deepened in the charter's Acquisitions Index by the owner -- so
        # the promotion is recorded together with the rank the current code was written for, and
        # the gap between them is surfaced as a standing work order rather than acted on.
        # `rank_at_code` only ever moves when a human amends the charter.
        at_code = prior.get("rank_at_code") or (was or now)
        if now != was:
            promoted.append("%s %s->%s (%d entries)" % (src, was or "-", now, n))
        ranks[src] = {"rank": now, "entries": n, "rank_at_code": at_code,
                      "code_amendment_pending": AD.tier_rank(now) > AD.tier_rank(at_code),
                      "spine": spine}
        for e in r.get("entries", []):
            key = "%s::%s" % (src, e.get("name"))
            shelved[key] = {"source": src, "name": e.get("name"),
                            "category": e.get("category"), "spine": spine,
                            "tier": tiersd.get(src), "rank": now,
                            "shelfmark": (marks.get(key) or {}).get("shelfmark")}

    landed = [land_json(ranks_p, ranks)]
    if promoted:
        log("phase 7 shelve: %d source(s) promoted -- %s"
            % (len(promoted), "; ".join(promoted)))
    pending = [s for s, v in ranks.items() if v.get("code_amendment_pending")]
    if pending:
        log("phase 7 shelve: %d source(s) have OUTGROWN THEIR SPINE CODE and need the charter's "
            "Acquisitions Index amended by hand -- %s" % (len(pending), ", ".join(sorted(pending))))
    log("phase 7 shelve: %d entries placed, %d source(s) with no charter spine code"
        % (len(shelved), len(unspined)))
    landed.append(land_json(os.path.join(HERE, "data/SHELVES.json"),
                            {"entries": shelved, "unspined": sorted(unspined)}))
    ok = gate_done(st, "shelve", landed)
    st["units_done"] += 1
    save_state(st)
    return ok


# A source is written when this fraction of its entries is SETTLED -- cited, or read with nothing
# found, which is a real finding rather than a gap. Below it the volume would be mostly silence
# wearing the shape of scholarship.
WRITE_SETTLED_MIN = 0.60


def phase_write(c, st):
    """Phase 8 -- the volumes themselves, and the one thing this library must never do.

    Delegates to `manifest_builder`, which knows which jobs exist, and `generate.py`, which knows
    how to turn a manifest into prose against the house style. This phase's own job is the guard
    rail: it REFUSES to write about a source whose entries have not been read.

    Prose about an entity with no evidence is the single output that would undo everything above
    it. It would be indistinguishable from the cited kind -- same voice, same shelfmark, same
    confident interval -- and the entire apparatus of verbatim checks, host fitness tests and
    honest absences exists to keep that distinction real. A library that writes about what it has
    not read is just a generator with a card catalogue.
    """
    import manifest_builder as MB

    # ABSENT AND CORRUPT ARE DIFFERENT ANSWERS -- the third phase in this file to need the
    # ruling and the last to get it (order 3aaeb798551e). One `except Exception` gave a missing
    # COVERAGE.json and a torn one the identical `rows = []`, and with no rows the `if not ready`
    # branch below publishes a POSITIVE VERDICT ABOUT THE CORPUS ("nothing is ready, and that is
    # a correct outcome") and calls `mark_done`, permanently, on the strength of a file it could
    # not read. Hard Rule -1 names this exact file: "a missing COVERAGE.json ... all refuse."
    _cov = os.path.join(HERE, "data/COVERAGE.json")
    try:
        rows = json.load(open(_cov, encoding="utf-8"))
    except FileNotFoundError:
        # Coverage has genuinely not been computed yet, and refusing to write about unread
        # sources is then the correct FINISHED answer rather than a failure -- as below.
        silence.note("pipeline.py:phase_write-coverage-absent")
        rows = []
    except Exception as e:
        silence.note("pipeline.py:phase_write-coverage-corrupt")
        log("phase 8 write: COVERAGE.json EXISTS BUT WILL NOT PARSE (%s) -- refusing to record "
            "\"nothing is ready\" from a file that was not read. Leaving phase 8 open; the next "
            "run retries once coverage is rewritten." % type(e).__name__)
        return False
    ready, thin = [], []
    for r in rows:
        n = max(r.get("entries", 0), 1)
        settled = (r.get("cited", 0) + r.get("read", 0)) / n
        (ready if settled >= WRITE_SETTLED_MIN else thin).append((settled, r.get("source")))
    log("phase 8 write: %d of %d sources are settled enough to write (>= %d%% read or cited)"
        % (len(ready), len(rows), int(WRITE_SETTLED_MIN * 100)))
    if not ready:
        log("  nothing is ready, and that is a correct outcome rather than a failure:")
        log("  the library does not write about entities nobody has read.")
        mark_done(st, "write")
        st["units_done"] += 1
        save_state(st)
        return True     # refusing to write unread sources is this phase's finished answer

    names = sorted({s for _, s in ready if s})
    # The real signature is build_jobs_for_source(cfg, roll_entry, record, spine) -- four
    # arguments, in that order. Calling it with two produced "117 sources would not build",
    # which reads as a property of the sources and was a property of the call.
    cfg = MB.load_config()
    roll = {r.get("source") or r.get("name"): r for r in (MB.load_roll(cfg) or [])}
    jobs, refused = [], []
    for src in names:
        try:
            rec = MB.load_record(cfg, src)
            spine = MB.spine_code_for(src) or MB.provisional_spine(src)
            jobs += MB.build_jobs_for_source(cfg, roll.get(src) or {"source": src},
                                             rec, spine) or []
        except Exception as e:
            silence.note("pipeline.py:phase_write-jobs")
            refused.append("%s (%s)" % (src, type(e).__name__))
    log("  manifest: %d job(s) across %d source(s), %d source(s) would not build"
        % (len(jobs), len(names), len(refused)))
    # UNCAPPED, per Hard Rule 0. This read `refused[:5]`, and a refusal roster is a roster: the
    # five that print are the alphabetical head of the list, and every source past the cutoff
    # is decided, on its own behalf, not to have happened. The count above stayed right the
    # whole time, which is what made it comfortable -- "117 sources would not build" with five
    # names under it looks like a summary rather than a truncation. The list is bounded by the
    # roll, it only prints when something is already wrong, and the whole point of the line is
    # to name which sources. (run #33)
    for r in refused:
        log("    refused: %s" % r)
    landed = []
    if jobs:
        out = os.path.join(HERE, "output", "index", "manifest.json")
        os.makedirs(os.path.dirname(out), exist_ok=True)
        landed.append(land_json(out, jobs))
        log("  -> output/index/manifest.json   (run generate.py against it)")
    elif refused:
        # VACUOUS TRUTH, AND THE TWO HISTORIES IT CONFLATES. `gate_done` marks the phase done on
        # `all(landed)`, and `all([])` is True -- deliberately, because a phase that correctly
        # wrote nothing must not be held open forever (there is a drill net on exactly that).
        # But `landed` is also empty when EVERY ready source raised inside
        # `build_jobs_for_source` and landed in `refused` instead, and those two states are not
        # the same state: one is "nothing needed building", the other is "everything refused to
        # build". Marked done, the second is permanent -- no later run redoes phase 8, no
        # manifest exists, and nothing anywhere records that a total build failure happened.
        # A single False is enough to keep the unit open for the next run. (run #33)
        log("  every ready source refused to build; phase 8 stays open rather than "
            "recording an empty manifest as a finished one")
        landed.append(False)
    # A THIRD ARM WAS ADDED HERE ON 2026-09-01 AND REVERTED THE SAME SHIFT. Recorded so the
    # next reader does not re-derive it a third time.
    #
    # The run40 sweep filed order 97d5b256fbdc: `build_jobs_for_source` returns an EMPTY LIST,
    # with no exception, for a record whose `entries` list is empty -- so if every ready source
    # is like that, `jobs` and `refused` are both empty, neither arm above runs, and `gate_done`
    # marks phase 8 done on `all([]) == True` having built nothing. That reading is CORRECT as
    # far as it goes, and an `elif names:` arm was added to hold the phase open for it.
    #
    # IT CONTRADICTED A DELIBERATE DECISION THAT ALREADY HAS A NET ON IT.
    # `drill._write_phase_stays_open_when_everything_refuses` drives exactly this fixture --
    # `load_record` returning `{"entries": []}` and `build_jobs_for_source` returning `[]` -- and
    # its second half REQUIRES the phase to close: "the vacuous case is still allowed to close,
    # or the phase never finishes." The drill went red, and a breached net is an OWNER halt.
    #
    # So the question is settled the other way, on purpose: a source with no entries is not a
    # failure to build, it is nothing to build, and holding phase 8 open for it would hold it
    # open for ever on a library that has simply catalogued a source it has not read yet. The
    # order was reopened as a QUESTION for the owner rather than re-fixed -- if the silent close
    # IS wrong, the net is what has to change first, and that is a curatorial call about what
    # phase 8 means, not a maintenance one.
    ok = gate_done(st, "write", landed)
    st["units_done"] += 1
    save_state(st)
    return ok


def phase_weave(c, st):
    """Phase 3 -- cross-source entity resolution. See weave.py for the reasoning.

    Runs whole-corpus rather than per-source, because identity is a property of the WHOLE
    catalogue: whether Alien's Ripley and Predator's Ripley are one person cannot be decided by
    looking at either shelf alone. It is therefore safe to run before phase 2 finishes -- it reads
    entity NAMES, which entrypass never changes (it only adds bands and topics).

    Two graphs come out, and conflating them was the first draft's error:
      IDENTITY   strict complete-linkage continuities. Mostly singletons: each universe keeps its
                 own Earth, and Earth resolves to ~30 distinct entities rather than one.
      RESONANCE  permissive. Drives X.7 propagation. Diameter 5, mean path 2.04 hops.
    """
    import weave as W
    raw = W.load_index()
    index, dropped = W.filtered_index(raw)
    log(f"phase 3 weave: {len(raw):,} keys, {dropped:,} mechanics dropped")

    occ, idf, sources, N = W.idf_table(index)
    sur, names = W.name_surprisal(index)
    w, shared = W.surprisal_pair_weights(occ, sur)
    thr = W.null_threshold_surprisal(occ, sur, sources, trials=12)
    log(f"  permutation threshold {thr:.1f} over {len(w):,} shelf-pairs")

    groups = W.components(sources, w, thr)
    resolved, homonyms = W.resolve(index, groups)
    res = W.resonance_graph(w, sources)
    log(f"  {len(groups)} continuities | {homonyms:,} homonyms kept apart | "
        f"{sum(1 for v in resolved.values() if v['n_attestations'] > 1):,} fused")
    log(f"  resonance diameter {res['diameter']} hops, six degrees: {res['six_degrees_holds']}")

    landed = [land_json(os.path.join(HERE, "data/CONTINUITY_GROUPS.json"),
                        {"threshold": thr, "groups": groups}, indent=2)]
    landed.append(land_json(os.path.join(HERE, "data/RESOLVED_ENTITIES.json"), resolved, indent=2))
    landed.append(land_json(os.path.join(HERE, "data/RESONANCE_GRAPH.json"),
              {"threshold": thr, "metric": "name-surprisal (bits)", "topology": res,
               "pairs": [{"a": a, "b": b, "weight": round(v, 2),
                          "shared_sample": shared[(a, b)]}   # WHOLE list -- Hard Rule 0, ruled 2026-08-24
                         for (a, b), v in sorted(w.items(), key=lambda kv: -kv[1])
                         if v >= thr]}, indent=2))

    # The onomasticon belongs to this phase, not a later one: resolution is what reveals that
    # thirty distinct worlds are all called Earth, and a catalogue that knows this and still files
    # them under one name is worse off than before resolution ran.
    import onomast as O
    # UNREADABLE PRIOR -> NO WRITE, and the phase stays open so the next run redoes it.
    # `name_worlds` used to be handed `{}` for a corrupt ONOMASTICON.json and this line wrote
    # that back, destroying every designation the file held in one cycle (order 549069e9c298).
    # The loader now refuses instead, and the refusal is turned into a False in `landed` --
    # `gate_done` below already leaves the unit open on a False, which is exactly the right
    # outcome: nothing here can repair the file, and the phase must not be marked complete
    # sitting over an onomasticon nobody could read.
    try:
        named = O.name_worlds(resolved)
    except O.OnomasticonUnreadable as e:
        log("  onomasticon: REFUSED — %s" % e)
        silence.note("pipeline.py:phase_weave-onomasticon-unreadable")
        named = None
        landed.append(False)
    if named is not None:
        landed.append(land_json(os.path.join(HERE, "data/ONOMASTICON.json"), named, indent=2))
    # `named` is the WHOLE onomasticon, retired records included -- that is what makes the file
    # append-only, and it is the point of order 9309a040f208. Counting it whole reports withdrawn
    # designations as worlds this phase has just named, and inflates the carried-name figure with
    # endonyms only retired records still hold. `onomast.main()` already splits the two and says
    # why ("a count that quietly included withdrawn designations would be the same class of
    # untruth as the one this fixes"); this is that arithmetic, in the phase's log line. No
    # difference today because nothing is retired yet -- which is precisely why the overstatement
    # would have arrived unannounced. (order 65e5735ba6dd)
    if named is not None:
        live = {cid: v for cid, v in named.items() if not O.is_retired(v)}
        endos = len({v["endonym"] for v in live.values()})
        log(f"  onomasticon: {len(live):,} worlds given designations across {endos} carried names"
            + (f"; {len(named) - len(live):,} retired designation(s) carried forward, never"
               f" reissued" if len(named) != len(live) else ""))

    ok = gate_done(st, "weave", landed)
    st["units_done"] += 1
    save_state(st)
    update_handoff(st)
    return ok


# BUILT FROM PHASES, NOT HAND-MAINTAINED.
#
# This was a literal dict of three entries, and it went stale the moment a phase was written
# without somebody remembering to add it here. `chain` was finished, working, and reported by the
# runner as "not implemented yet" for exactly that reason -- so phase 4 only ever ran by hand and
# phases 5 through 8 were never attempted, because the runner stopped at the gap.
#
# Deriving it from PHASES means writing `phase_<name>` IS registering it, and the two can never
# disagree again.
IMPLEMENTED = {i: globals()["phase_" + name]
               for i, name in enumerate(PHASES, 1)
               if "phase_" + name in globals()}


def main():
    # PLANT-WIDE INTERLOCK. The top rung of the escalation chain (escalation.py). If a
    # library-wide invariant has been violated, nothing starts until a person rules on it.
    # Placed first in main() so there is no path into this job that skips it.
    try:
        import escalation as _ESC
    except ImportError as _esc_gone:
        # FAIL CLOSED. This used to be `except ImportError: pass`, which meant a deleted or
        # unparseable `escalation.py` silently switched the plant-wide halt off in every job
        # at once -- nine sites, all of them quiet about it. That is Hard Rule -1's own
        # incident wearing different clothes: the last one began with an autonomous run
        # removing a safety it had concluded was unnecessary, and nothing downstream could
        # tell. A job that cannot ask whether the library is halted has no business
        # starting. Pinned by verify_math so the swallow cannot come back. (run #31)
        raise SystemExit(
            "REFUSING TO START: the escalation chain (src/escalation.py) could not be "
            "imported (%s), so the halt cannot be read. Hard Rule -1." % _esc_gone) from _esc_gone
    _ESC.assert_clear(os.path.basename(__file__))
    # THE FINGERPRINT OF src/ AS THIS PROCESS FOUND IT. Taken here, before any phase runs, so
    # `exit_if_stale` in the phase loop below has something to compare against. See codewatch.py.
    import codewatch
    codewatch.stamp("pipeline")
    ap = argparse.ArgumentParser()
    ap.add_argument("--phase", type=int, default=None)
    ap.add_argument("--status", action="store_true")
    # AN IDENTIFIABLE INVOCATION, the same reason `read.py --run` carries one (order
    # 08c1fd3932a4). `lognames.OWNER` names the process that writes each managed log by a
    # command-line fragment, and the fragment must be specific enough to tell two invocations
    # of one script apart -- but the supervisor started this runner with a BARE `pipeline.py`,
    # so `pipeline.py --status` (which prints the handoff and exits) and a hand-run
    # `pipeline.py --phase 6` both answered for the daemon in `overnight.running()`, the stall
    # detector, the dashboard's Jobs panel and the foreman's restart remedy. Selecting the
    # default behaviour explicitly is what makes the daemon's command line say which job it is.
    # Optional on purpose: a bare `pipeline.py` still runs the phases, so nothing that already
    # invokes it that way breaks.
    ap.add_argument("--run", action="store_true",
                    help="run the phases (the default); names the supervisor's invocation so "
                         "lognames.OWNER can tell it from --status and --phase")
    args = ap.parse_args()

    # --phase IS AN INDEX INTO PHASES, AND EVERY OUT-OF-RANGE VALUE USED TO FAIL DIFFERENTLY.
    # `--phase 9` reached `IMPLEMENTED.get(9) -> None` and the "not implemented yet -- stopping
    # cleanly" line then evaluated `PHASES[8]` and raised an uncaught IndexError: a traceback
    # instead of the clean stop the message promises. `--phase 0` was swallowed by the truthiness
    # test below (`[args.phase] if args.phase`) and the runner silently did a full resume run
    # instead of the one phase asked for. `--phase -1` logged "phase -1 (shelve) is not
    # implemented yet", naming the wrong phase from a negative index. This matters more than an
    # operator typo usually would: `--phase N` is the documented recovery action the
    # pointer-past-end-with-open-phases branch below tells a person to take. Validated once,
    # here, where the value arrives. (order 4a79b0e8a375)
    if args.phase is not None and not 1 <= args.phase <= len(PHASES):
        raise SystemExit(
            "--phase %s is out of range: the ladder has %d phases, numbered 1..%d (%s)."
            % (args.phase, len(PHASES), len(PHASES),
               ", ".join("%d %s" % (i, n) for i, n in enumerate(PHASES, 1))))

    st = load_state()
    if args.status:
        update_handoff(st)
        print(open(HANDOFF, encoding="utf-8").read())
        return

    if st.get("started") is None:
        st["started"] = datetime.datetime.now().isoformat(timespec="seconds")
    c = cfg()
    log(f"pipeline start | model={c['model']} | "
        f"phase={args.phase if args.phase is not None else st['phase']}")

    # `is not None`, not truthiness -- see the validation above. 0 is now refused outright, but
    # the flag's presence and its value are different questions and this is the spelling that
    # says so.
    phases = ([args.phase] if args.phase is not None
              else list(range(st.get("phase", 1), len(PHASES) + 1)))

    # A RUNNER WITH AN EMPTY WORK LIST MUST SAY WHICH KIND OF EMPTY IT IS.
    #
    # `range(9, 9)` is empty, the loop below never turned over, and the old code fell straight
    # through to "runner exiting" and exit 0. Every cycle, twice a cycle (overnight.py starts it
    # backgrounded and again in-line), for as long as the pointer sat past the end -- a clean
    # exit code from a process that did nothing at all, which is indistinguishable from a
    # process that did everything. That is the whole defect: not that the runner stopped, but
    # that stopping and finishing produced the same signal. (m37.)
    if not phases:
        never = phases_never_closed(st)
        if never:
            log("RUNNER HAS NOTHING TO RUN, AND THAT IS A FAULT, NOT A FINISH.")
            log(f"  the phase pointer is {st.get('phase')}, past the last phase ({len(PHASES)}),"
                f" but {len(never)} phase(s) carry NO completion marker: {', '.join(never)}")
            log("  the pointer was advanced past work that never completed. NOT repaired here:")
            log("  rewinding it by hand is what hid this for five passes. A person decides"
                " which phase to resume from, then runs with --phase.")
            silence.note("pipeline.py:pointer-past-end-with-open-phases")
            update_handoff(st)
            raise SystemExit(3)
        log(f"nothing to do: the pointer is past phase {len(PHASES)} and every phase carries a "
            f"completion marker. The run is FINISHED, not stalled.")
        log("  to run the ladder again over newly catalogued sources, reset the pointer"
            " deliberately (--phase N) rather than leaving this to look like work.")
        update_handoff(st)
        return

    # THE POINTER FOLLOWS THE WORK, NOT THE LOOP COUNTER. `st["phase"] = ph + 1` used to run
    # unconditionally at the bottom of this loop, including for the phases that deliberately
    # return early to stay open (6 and 7 on a corrupt input) and for every gate_done that
    # refused to mark its phase done -- phase 4 has refused four cycles running and the pointer
    # sailed past it every time. `st["done"]` was never consulted for phases 3-8, so nothing
    # anywhere noticed. Now a phase reports its own completion and the pointer stops at the
    # first phase that did not report one; later phases still get their turn (they may be able
    # to make progress from the artifacts already on disk), but the RESUME POINT stays behind
    # the open work, which is the only thing the pointer was ever for.
    stalled = None
    for ph in phases:
        # PICK UP CODE CHANGES, AT A PHASE BOUNDARY. A running process is a photograph of the
        # source as it was when it started: on 2026-08-25 a `publish.py --loop` daemon from
        # 14:28 pushed deliberately-corrupted files to a public repo because the guard written
        # at 19:00 to stop it was never in its memory. This runner is in `overnight.STANDING`,
        # so the keeper re-asserts it within five minutes running the current code, and the
        # state is saved and the pointer is advanced per phase -- a phase boundary is therefore
        # the one place an exit costs nothing but the phase about to start. Exits rc=17 on
        # purpose; budgeted and settled, so an edit storm cannot make this a respawn loop.
        # (order 1f172f5acc6f: this daemon had no codewatch call site at all.)
        codewatch.exit_if_stale("pipeline")
        # NAMED BEFORE IT IS DISPATCHED, and named safely. `PHASES[ph-1]` was evaluated inside
        # the not-implemented message, where an out-of-range `ph` turns a clean stop into an
        # IndexError and a negative one silently names the phase at the other end of the list.
        # --phase is validated above; the resume range is derived from `st["phase"]`, which comes
        # off disk and is not, so the guard stays here too. (order 4a79b0e8a375)
        name = PHASES[ph - 1] if 1 <= ph <= len(PHASES) else "no such phase"
        fn = IMPLEMENTED.get(ph)
        if fn is None:
            log(f"phase {ph} ({name}) is not implemented yet -- stopping cleanly.")
            log("Build it, then re-run; state is preserved.")
            break
        if stalled is None:
            st["phase"] = ph
            save_state(st)
        log(f"=== PHASE {ph}: {name} ===")
        try:
            ok = fn(c, st)
        except KeyboardInterrupt:
            log("interrupted -- state saved, safe to resume")
            save_state(st)
            return
        except Exception:
            log("PHASE CRASHED:\n" + traceback.format_exc())
            save_state(st)
            return
        # FAIL CLOSED ON THE VERDICT. Anything that is not an explicit True counts as "did not
        # finish": a phase that forgets to report leaves the pointer where it is and gets redone,
        # which costs a cycle. The other direction cost eight phases' worth of silent no-ops.
        if ok is True:
            log(f"=== PHASE {ph} COMPLETE ===")
            st.get("failed", {}).get("runner", {}).pop(name, None)
            if stalled is None:
                st["phase"] = ph + 1
        else:
            log(f"=== PHASE {ph} ({name}) LEFT OPEN -- it did not report completion "
                f"(returned {ok!r}); the resume pointer stays at "
                f"{stalled if stalled is not None else ph} ===")
            silence.note("pipeline.py:phase-left-open")
            st.setdefault("failed", {}).setdefault("runner", {})[name] = (
                "left open at %s -- did not report completion"
                % datetime.datetime.now().isoformat(timespec="seconds"))
            if stalled is None:
                stalled = ph
                st["phase"] = ph
        save_state(st)
        update_handoff(st)

    if stalled is not None:
        open_now = sorted(st.get("failed", {}).get("runner", {}))
        log(f"runner exiting with phase {stalled} ({PHASES[stalled-1]}) STILL OPEN "
            f"-- the pointer stays at {st.get('phase')} so the next run redoes it "
            f"(open: {', '.join(open_now)})")
        return
    log("runner exiting")


if __name__ == "__main__":
    main()


# ------------------------------------------------------------------ P8: the meta-language ban
#
# "these books should read like in-universe books only, nothing meta about the game they are
# designed for" -- owner, on file. Ground Rule 4 says it, the model ignores it, so it is
# enforced in code like scale_note and the Marginalia cap before it.
#
# This scans GENERATED PROSE ONLY. It must never be run against entries[].description, which is
# transcribed evidence: 7.4% of that text (3,870 entries, concentrated in the D&D homebrew)
# legitimately contains "saving throw" and "hit points" because that is what the source says.
# Evidence is allowed to be meta. The library's own voice is not.
_META_TERMS = re.compile(
    r"\b(?:DMs?|dungeon master|game master|GMs?|player characters?|players?|PCs?|NPCs?"
    r"|tier of play|at your table|the table|adventuring party|session|campaign"
    r"|d20|saving throws?|hit points?|armou?r class|proficiency bonus|initiative"
    r"|challenge rating|CR \d+|stat block|5e|fifth edition|homebrew|sourcebook"
    r"|roll(?:s|ed)? (?:a )?d\d+|advantage on the roll)\b", re.I)


def meta_violations(prose):
    """Return the distinct meta terms found in generated prose. Empty list = clean."""
    return sorted({m.group(0).lower() for m in _META_TERMS.finditer(prose or "")})


def assert_in_universe(prose, where=""):
    """Raise on meta leakage. Callers in the write phase should reject and regenerate rather
    than publish -- a single 'as a DM you might' in a finished volume breaks the frame for
    every entry around it."""
    bad = meta_violations(prose)
    if bad:
        raise ValueError(f"meta-language in generated prose{' at ' + where if where else ''}: "
                         f"{bad}")
    return True
