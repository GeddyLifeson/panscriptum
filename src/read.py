#!/usr/bin/env python3
"""
READ — the model reads the source pages; regex only decides what to skip.

The division of labour here was backwards for most of this project's life. Regex was being asked
"is this sentence a feat?", which is reading comprehension, and it failed at it in every way the
record shows: a gate that passed 0.28% of sentences and turned out to be structurally a RUIN
detector, blind to the other ten axes; a scale parser that took five separate fixes and still
emitted Fortnite progression levels as a power scale; a word-boundary escape that silently became
a 0x08 backspace five separate times.

Measured on Goku's three pages, same text, same axes:

    eleven regex axis gates      13 feats
    the model reading the pages  95 feats, 10/11 axes, 81 of them verbatim-verified

The model also found what no pattern was going to -- "capable of instantly learning techniques
performed by other fighters after seeing them once" is a Volition feat with no destructive verb
and no object of consequence in it anywhere.

So regex keeps exactly one job, the one it is good at: throwing away text that cannot contain a
feat, cheaply, with no judgement involved. On Goku, three of eleven chunks were production
history and plot summary and returned nothing; skipping those costs one regex and saves a
minute of GPU each.

WHAT DOES NOT CHANGE
--------------------
Every guard stays, because the same test showed 14 of 95 returned sentences were NOT on the page
-- paraphrased or invented, a 15% fabrication rate. The verbatim check caught all of them
mechanically. Guards verify the model's output and are indifferent to how that output was
produced, so a better reader does not make them less necessary; it makes them the only thing
standing between a fluent paraphrase and a printed measurement.
"""
import argparse
import hashlib
import json
import os
import re
import sys
import threading
import time

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import pipeline as P                                                    # noqa: E402
import feats as F                                                       # noqa: E402
import assay as A                                                       # noqa: E402
import silence

_BAD_CHARS = (chr(8), chr(11), chr(12), chr(7))
if any(c in open(os.path.abspath(__file__), encoding="utf-8").read() for c in _BAD_CHARS):
    raise SystemExit(__file__ + ": a regex escape was eaten in transit.")

CACHE = os.path.join(HERE, "data", "readfeats")
AXES = list(A.WEIGHTS)
# SIZED AGAINST THE CONTEXT, not guessed. num_ctx is 6144 tokens. The system prompt is ~400 and
# the reply needs ~600, leaving ~5,100 for the passage. English wiki prose runs about 3.7
# characters per token, so ~18,000 characters is the theoretical ceiling and 20,000 was OVER it.
#
# Ollama does not refuse an overlong prompt, it silently truncates -- so the tail of every chunk
# was never read, feats living there were invisible, and any sentence the model half-recalled
# from the cut portion failed the verbatim check and was counted a fabrication. The measured
# 51% "fabrication" rate and the 600-second timeouts were both this.
#
# 10,000 leaves real headroom. It doubles the number of calls and each one is faster and
# correct, which is the trade worth making.
# THE GPU-SAFE UNIT. Ollama runs at num_ctx 6144, and English wiki prose is about 3.7
# characters per token, so 10,000 characters is roughly 2,700 tokens of passage plus the system
# prompt -- comfortably inside the window. Sending more does not error: Ollama truncates in
# silence, which is what produced the "51% fabrication rate" that was really a cut-off passage.
CHUNK = 10000

# THE CLOUD UNIT — MEASURED, AND THE MEASUREMENT SAID NO.
#
# The reasoning was sound: pool models carry contexts an order of magnitude larger than the local
# one, free tiers meter REQUESTS rather than tokens, and reading a page in four big pieces instead
# of fourteen small ones is the same text for a quarter of the calls. 47,757 chunks across the
# corpus would have become 13,265.
#
# Then it was measured on one entity, both ways:
#
#     10,000 characters   5 chunks  ->  41 feats
#     36,000 characters   2 chunks  ->  19 feats
#
# Fifty-four percent of the evidence, gone, for a 2.5x saving in calls. The model is asked to
# find EVERY feat in what it is shown, and attention over a long passage thins; a feat that is
# never returned is indistinguishable from a feat that was never there, which is this project's
# defect arriving by a new road. Recall is the entire reason the model reads instead of the regex.
#
# So the cloud unit is the local unit. Throughput comes from more providers and more workers,
# never from showing the model more text per call. Revisit only with a fresh measurement.
CLOUD_CHUNK = CHUNK

# Filled in by run() once the queue and the transport are both known.
CHUNK_BUDGET = 1

# The ONLY regex judgement left, and it is a rejection rather than a selection: a block of text
# with no action verb in it at all cannot contain a feat. Deliberately generous -- it is cheaper
# to send a doubtful chunk to the model than to silently drop a real feat, which is the mistake
# the old gate made ten thousand times.
_HAS_ACTION = re.compile(
    r"\b(destroy|shatter|obliterat|erase|kill|slew|slay|defeat|beat|overpower|surviv|withstood|"
    r"withstand|endur|regenerat|heal|dodg|evad|react|outrun|blitz|intercept|block|parr|"
    r"lift|carr|hurl|threw|throw|launch|punch|strike|struck|cut|slice|pierc|crush|"
    r"teleport|fly|flew|travel|cross|traverse|master|train|learn|adapt|counter|"
    r"predict|calculat|deduc|outwit|sens|detect|perceiv|notic|convinc|persuad|inspir|"
    r"command|led|rall|seal|negat|nullif|bypass|absorb|summon|transform|power|strength|"
    r"speed|durab|abilit)", re.I)

SYSTEM = """You are reading one page of a fiction wiki to collect POWER FEATS for an entity.

A feat is something the entity DID, on the page, to something of consequence. It is not a
reputation, not an intention, not a plan, and not something done TO them by someone else.

For each feat, copy the sentence VERBATIM from the page and name the ONE axis it evidences:

  ruin           destructive or effective output
  continuity     what it takes to remove them - durability, regeneration, resurrection
  celerity       speed, reaction, combat tempo
  reach          spatial extent of effect
  transgression  violating a law of the setting - time, soul, fate, causality, toon-force
  sustain        how long peak output holds; resource dependence
  vector         getting to a target - mobility, travel, teleportation
  volition       skill, mastery, battle intelligence
  acumen         prediction, planning, deduction
  discernment    perception and insight
  suasion        moving other agents by voice and standing alone (never by force or compulsion)

Copy sentences EXACTLY as written. A paraphrase is discarded by the checker and the feat is lost.

Return ONLY the feats actually present in the text in front of you. There is no target number.
Most passages hold none at all, and a page of biography or production history holds none no
matter how long it is - an empty list is the correct and expected answer there. Never extend a
list to make it look complete: a sentence you compose rather than copy is discarded anyway, so
padding costs you the real feats' credibility and gains nothing."""

SCHEMA = {
    "type": "object",
    "properties": {"feats": {"type": "array", "items": {
        "type": "object",
        "properties": {"sentence": {"type": "string"},
                       "axis": {"type": "string", "enum": AXES}},
        "required": ["sentence", "axis"]}}},
    "required": ["feats"],
}



_QMAP = {0x2018: 39, 0x2019: 39, 0x201c: 34, 0x201d: 34, 0x2013: 45, 0x2014: 45,
         0x2026: 46, 0xa0: 32}


def _norm_q(t):
    """Fold the punctuation a wiki and a model disagree about, then collapse whitespace."""
    return ' '.join(t.translate(_QMAP).split())


def _names(sentence, entity):
    """Is the entity actually the subject of this sentence?

    Accepts the entity's name, any distinctive word of it (surnames and given names are used
    interchangeably across a wiki), or a personal pronoun. Rejects the generic subjects a
    techniques index uses -- "the user", "the wielder", "this technique".
    """
    low = sentence.lower()
    parts = [w for w in re.split(r'[^A-Za-z]+', entity) if len(w) > 3]
    if any(w.lower() in low for w in parts):
        return True
    # Tokenised rather than pattern-matched. A word-boundary escape has been eaten in
    # transit six times in this project, and here the failure would have been
    # invisible-but-total: with no boundaries, 'he' matches inside 'the' and every
    # sentence ever written passes the check.
    words = set(re.split(r'[^a-z]+', low))
    return bool(words & {'he', 'she', 'they', 'his', 'her', 'their', 'him',
                         'himself', 'herself', 'themselves'})



# ------------------------------------------------------------------ transport
#
# Reading is the long pole and it was pinned to one GPU. `ollama ps` explains why: a 19GB MoE on
# a 10GB card runs 56/44 CPU/GPU, which is about ten minutes an entity and a month for the roll.
#
# Cascade is the owner's own quota-aware router over 27 providers and 24 separately-metered
# buckets, and this work is exactly the shape it suits -- stateless, embarrassingly parallel, and
# happy to be served by whichever model is free. Local Ollama is IN that pool as an unlimited
# bucket, so when cloud quota runs dry the router falls back to the local model on its own rather
# than stalling. That is the whole thesis, applied to a batch job instead of a chat window.
#
# Direct Ollama remains as a last resort for when Cascade is unreachable, because a transport
# that fails should degrade rather than stop.
_TRANSPORT = "auto"
_CASCADE_OK = None
_TRANSPORT_LOCK = threading.Lock()
_FELL_BACK = [0]
# Attempts through the pool before a chunk is handed to the local GPU. Each attempt claims a
# different bucket, so three is three providers, not one provider three times.
CASCADE_TRIES = 5
# Seconds to wait between pool attempts. A free tier's window is measured in seconds, not
# minutes, so a short ladder recovers most declines without a worker sitting idle for long.
BACKOFF = (2, 5, 12, 30)
# How long the local GPU sits out after failing to answer. Long enough that a saturated card
# stops costing three-minute waits, short enough that it returns within one reading pass.
GPU_BENCH = 900
_GPU_DOWN_UNTIL = [0.0]
# Seconds of history the progress line averages its rate over.
RATE_WINDOW = 300
_rate_log = []


def set_transport(mode):
    global _TRANSPORT
    _TRANSPORT = mode


def ensure_transport(verbose=True):
    """Decide the transport ONCE, before any worker starts, and say which one won.

    This was a lazy `if _CASCADE_OK is None` inside the hot path, and with ten workers all ten
    hit it simultaneously on the first chunk. The probe is not thread-safe; under that race it
    could resolve False, and False is permanent -- so every call for the rest of the run went to
    local Ollama, which serialises on a 10GB card. The run did not fail. It got four times
    slower and said nothing, which is this project's signature defect wearing a different hat.

    Resolving before the pool starts removes the race. Announcing the result removes the silence.
    """
    global _CASCADE_OK
    with _TRANSPORT_LOCK:
        if _CASCADE_OK is not None:
            return _CASCADE_OK
        if _TRANSPORT == "ollama":
            _CASCADE_OK = False
        else:
            try:
                import cascade_bridge as CB
                _CASCADE_OK = bool(CB.engine())
            except Exception as e:
                silence.note("read.py:ensure_transport")
                if verbose:
                    print(f"transport: Cascade unavailable ({type(e).__name__}); "
                          f"falling back to local Ollama", flush=True)
                _CASCADE_OK = False
    if verbose:
        print("transport: " + ("Cascade (cloud buckets, local Ollama as the last bucket)"
                               if _CASCADE_OK else "local Ollama only"), flush=True)
    return _CASCADE_OK


# ------------------------------------------------------------------ the adaptive gate (M11)
#
# A ThreadPoolExecutor is sized once, at construction, from whatever the regime was at launch --
# and the regime CHANGES underneath a long run. Last night a batch started on cloud settings
# with twelve workers, four buckets shed to HTTP 402 mid-flight, and twelve threads went on
# queueing against one local model, timing each other out for the rest of the run. The pool
# cannot shrink; this gate can. Every model call passes through it, and when the regime reads
# local/starved only GATE_LOCAL_N calls are in flight at once -- the surplus workers WAIT at the
# gate instead of stacking onto the card. On cloud the wide gate never binds. The regime is
# re-read lazily on a timer, so a mid-run recovery re-opens the gate without a restart.
GATE_CLOUD_N = 16
GATE_LOCAL_N = 2
GATE_RECHECK_S = 120
_GATE_CLOUD = threading.BoundedSemaphore(GATE_CLOUD_N)
_GATE_LOCAL = threading.BoundedSemaphore(GATE_LOCAL_N)
_GATE_STATE = {"at": 0.0, "regime": "cloud"}


def _gate():
    now = time.time()
    if now - _GATE_STATE["at"] > GATE_RECHECK_S:
        try:
            import tuning as T
            _GATE_STATE["regime"] = T.regime()
        except Exception:
            silence.note("read.py:gate-regime")
        _GATE_STATE["at"] = now
    return _GATE_CLOUD if _GATE_STATE["regime"] == "cloud" else _GATE_LOCAL


def _ask(c, system, prompt, schema):
    """One structured call, by whichever transport is available -- through the adaptive gate."""
    with _gate():
        return _ask_ungated(c, system, prompt, schema)


def _ask_ungated(c, system, prompt, schema):
    """The transport ladder itself. Call _ask, not this, unless you are the gate."""
    if _TRANSPORT in ("auto", "cascade"):
        if ensure_transport(verbose=False):
            # RETRY ACROSS BUCKETS BEFORE SURRENDERING THE CHUNK TO THE GPU.
            #
            # One free-tier provider erroring is ordinary -- a rate window closes, a model goes
            # dark, an account hits zero. What is not ordinary is what it cost: a single error
            # sent that chunk to local Ollama on a 600-second timeout, so a two-second failure
            # bought a two-minute detour. The pool exists precisely so that one provider's bad
            # minute is somebody else's ordinary one, and the router claims a DIFFERENT bucket
            # each time, so a second attempt is a genuinely different provider.
            # WAIT, DO NOT DROP.
            #
            # The pool's sustained capacity is what the free tiers allow -- measured around
            # 3,400 calls an hour -- and fourteen workers ask for several times that. The excess
            # has to go somewhere, and the two honest options are "wait" and "use the GPU". The
            # third option, which is what the code did, is to give up on the passage: 5,090 of
            # 7,083 chunks in one pass were declined by every transport and skipped.
            #
            # So the retries back off instead of failing fast. A chunk that waits ninety seconds
            # for a bucket to free up is a chunk that gets read; the alternative costs the
            # entity's evidence and there is no later pass that knows to look again.
            # THE GPU IS CAPACITY, NOT A LAST RESORT.
            #
            # This tried the pool up to six times with a backoff ladder before ever touching the
            # card, on the theory that the cloud is fast and the GPU is slow. That is true per
            # call and false in aggregate: the free pool's sustained rate is a few hundred calls
            # an hour once the big daily allowances are spent, and the GPU adds four hundred more
            # for nothing. Waiting ninety seconds for a bucket while an idle card sits there is
            # not conservation, it is throughput thrown away.
            #
            # So: two quick attempts at the pool, then the GPU, and only if BOTH decline does the
            # backoff ladder start. The long waits are for when there is genuinely nowhere to go.
            for quick in range(2):
                try:
                    import cascade_bridge as CB
                    got = CB.ask(system, prompt, schema)
                    if got is not None:
                        return got
                except Exception:
                    silence.note("read.py:188")
            if _TRANSPORT != "cascade" and _GPU_DOWN_UNTIL[0] <= time.time():
                got = _local(c, system, prompt, schema)
                if got is not None:
                    _FELL_BACK[0] += 1
                    return got
            delay = 0.0
            for attempt in range(CASCADE_TRIES):
                if delay:
                    time.sleep(delay)
                try:
                    import cascade_bridge as CB
                    got = CB.ask(system, prompt, schema)
                    if got is not None:
                        return got
                except Exception:
                    silence.note("read.py:188")
                delay = BACKOFF[min(attempt, len(BACKOFF) - 1)]
            # Every bucket tried and none answered. Falling through to the GPU is right, but the
            # count has to be visible: a run quietly serving every call from the slow path looks
            # identical to a run that is merely slow.
            _FELL_BACK[0] += 1
            if _TRANSPORT == "cascade":
                return None
    # THE GPU GETS THE SAME TEXT, IN PIECES IT CAN HOLD.
    #
    # Chunks are built at cloud size, and Ollama does not refuse an overlong prompt -- it
    # truncates it silently, which is the exact fault that once looked like a 51% fabrication
    # rate. So an oversized passage is re-split here and the results merged. The reader still
    # sees every character; only the seams move.
    #
    # The local timeout is deliberately not generous. A piece the GPU cannot finish in three
    # minutes is better retried through the pool next pass than sat on for ten.
    # THE GPU GETS BENCHED TOO.
    #
    # The roll and the reader both run against one 10GB card, so the local fallback spends most
    # of a long run saturated -- and a saturated Ollama does not refuse, it holds the connection
    # until the timeout. Thirty-nine fallbacks at 180 seconds is two hours of worker time bought
    # for nothing, while thirteen cloud buckets sat available. If it has failed recently, skip it
    # and let the chunk be retried through the pool on the next pass.
    return _local(c, system, prompt, schema)


_FALLBACK_MODEL = [None]
# The card is 10GB. A model needs room for weights AND context, so the budget is deliberately
# under that -- a model that "fits" at 9.9GB does not fit once a 2,700-token prompt arrives.
# 8.5GB on a 10GB card. Nine leaves barely a gigabyte for the context window, and a
# model that fits its weights but not its prompt spills to CPU anyway -- which is the
# whole failure being fixed here.
VRAM_BUDGET_BYTES = 8.5e9


def fallback_model(c):
    """The largest installed local model that fits the card WHOLE.

    config.yaml names a 30B MoE at 18.6GB. On a 10GB 3080 that runs at a 56/44 CPU/GPU split,
    which is fine for a batch job nobody is waiting on and useless as a fallback: every request
    blew the 180-second timeout, 18 in fifteen minutes, and the reader kept paying for them.
    The card sat at 22% utilisation and 9,711MB of 10,240 -- not busy, thrashing.

    A 12B that fits entirely in VRAM answers in seconds. It is a weaker model and it will
    fabricate more, but the verbatim check already discards fabrication, so the cost is a few
    wasted calls rather than bad data -- and the alternative is a fallback that never answers.

    The phase work keeps config.yaml's model: synthesis and entrypass are batch jobs where the
    bigger model's quality is worth the wait, which is exactly what a fallback is not.
    """
    if _FALLBACK_MODEL[0] is not None:
        return _FALLBACK_MODEL[0]
    try:
        import urllib.request
        host = c.get("ollama_host", "http://localhost:11434")
        with urllib.request.urlopen(host + "/api/tags", timeout=20) as r:
            tags = json.loads(r.read().decode("utf-8", "replace"))
        fits = []
        for m in tags.get("models", []):
            name, size = m.get("name") or "", m.get("size") or 0
            if not name or not (0 < size <= VRAM_BUDGET_BYTES):
                continue
            # Not every small model can do this job: an embedding model has no chat head and a
            # 1B vision model cannot hold a schema. Excluded by name because Ollama's tag list
            # does not say what a model is for.
            if any(k in name.lower() for k in ("embed", "moondream", "vision", "clip")):
                continue
            fits.append((size, name))
        _FALLBACK_MODEL[0] = max(fits)[1] if fits else c.get("model")
    except Exception:
        silence.note("read.py:fallback_model")
        _FALLBACK_MODEL[0] = c.get("model")
    return _FALLBACK_MODEL[0]


def _local(c, system, prompt, schema):
    """The GPU, re-splitting anything too long for its window, benched when it stops answering."""
    if _GPU_DOWN_UNTIL[0] > time.time():
        return None
    c = dict(c, model=fallback_model(c))
    if len(prompt) <= CHUNK + 2000:
        got = P.ask(c, system, prompt, schema, timeout=180)
        if got is None:
            _GPU_DOWN_UNTIL[0] = time.time() + GPU_BENCH
        return got
    head, _, body = prompt.partition(chr(10) + chr(10))
    merged = {"feats": []}
    for i in range(0, len(body), CHUNK):
        got = P.ask(c, system, head + chr(10) + chr(10) + body[i:i + CHUNK],
                    schema, timeout=180)
        merged["feats"].extend((got or {}).get("feats", []))
    return merged


def config():
    import yaml
    cfg = yaml.safe_load(open(os.path.join(HERE, "config.yaml"), encoding="utf-8"))
    return {"model": cfg.get("model"),
            "ollama_host": cfg.get("ollama_host", "http://localhost:11434"),
            "seed": 47, "num_ctx": cfg.get("num_ctx", 6144)}


def cache_path(host, name):
    return os.path.join(CACHE, re.sub(r"[^A-Za-z0-9]+", "_", host)[:40],
                        re.sub(r"[^A-Za-z0-9]+", "_", name)[:80] + ".json")


CHUNK_CACHE = os.path.join(HERE, "data", "chunkfeats")


def _chunk_key(host, ch):
    """A chunk's identity: its exact text. Independent of which entity asked for it.

    Two entities attached to the same shared index page read the same passage, and there is no
    reason to pay for it twice -- so the key is the passage, not the pair.
    """
    h = hashlib.sha256((host + chr(31) + ch).encode("utf-8")).hexdigest()
    return h[:2], h[2:18]


def _chunk_get(host, ch):
    d, name = _chunk_key(host, ch)
    p = os.path.join(CHUNK_CACHE, d, name + ".json")
    if not os.path.exists(p):
        return None
    try:
        with open(p, encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        silence.note("read.py:chunk_get")
        return None


def _chunk_put(host, ch, feats):
    d, name = _chunk_key(host, ch)
    folder = os.path.join(CHUNK_CACHE, d)
    try:
        os.makedirs(folder, exist_ok=True)
        p = os.path.join(folder, name + ".json")
        tmp = p + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump({"feats": feats}, f, ensure_ascii=False)
        os.replace(tmp, p)
    except Exception:
        silence.note("read.py:chunk_put")


def read_entity(c, host, name, cap_chunks=None):
    """Read one entity's cached pages with the model. Returns verified feats by axis."""
    path = cache_path(host, name)
    if os.path.exists(path):
        with open(path, encoding="utf-8") as f:
            return json.load(f)

    ev = F.evidence_for(host, name)
    text = ev.get("text") or {}
    # A chunk must MENTION the entity, not merely belong to a page discovery attached to it.
    #
    # Discovery matches a page when the entity's first word appears in its title, so
    # "Metal Gear Solid V: The Phantom Pain/Weapons and Equipment" -- 430,000 characters, 44
    # chunks -- was attached to every Metal Gear entity and read END TO END for each one. Three
    # of the first four entities spent about half an hour of GPU apiece on it and returned zero
    # feats, because the page barely names them.
    #
    # Filtering by mention costs one string search and turns 44 chunks into the two or three
    # that concern this entity. The entity's own page always passes, since its title is its name.
    keys = [w.lower() for w in re.split(r"[^A-Za-z0-9]+", name) if len(w) > 3] or [name.lower()]
    # Sized for whichever transport will actually carry it. The GPU fallback re-splits an
    # oversized passage rather than truncating it (see _ask), so a cloud-sized chunk is safe
    # even on the rare call that ends up local.
    size = CLOUD_CHUNK if _CASCADE_OK else CHUNK
    chunks = []
    for title, body in text.items():
        own = _norm_q(title).lower() == _norm_q(name).lower()
        for i in range(0, len(body), size):
            ch = body[i:i + size]
            if not _HAS_ACTION.search(ch):
                continue
            if own or any(k in ch.lower() for k in keys):
                density = sum(ch.lower().count(k) for k in keys)
                chunks.append((0 if own else 1, -density, title, ch))

    # RANKED AND CAPPED. Filtering by mention took a shared franchise page from 44 chunks to 24,
    # which is better and still ruinous: a 430,000-character page names "Metal Gear" on nearly
    # every chunk, so a mention test barely narrows it. What actually separates signal from bulk
    # is DENSITY -- how often this entity is named in this passage -- and the entity's own page,
    # which is about it by definition.
    #
    # The cap is depth, not a compromise on it: an entity's own pages run three to twenty chunks
    # at 10,000 characters, so twelve covers the whole of most subjects and the densest part of
    # every shared page. Uncapped, one entity could eat an hour of GPU on a page that names it
    # twice, and at 35,000 entities that is the difference between a night and a year.
    chunks.sort()
    # Ranked by how densely the entity is named, so the richest passages are read first if this
    # is interrupted. Not truncated: a cap here decides on the entity's behalf that the rest of
    # its own pages do not count.
    chunks = [(t, c) for _, _, t, c in chunks]
    if cap_chunks:
        chunks = chunks[:cap_chunks]
    skipped = sum(len(b) for b in text.values()) // size - len(chunks)

    # ANSWERS ARE CACHED PER CHUNK, NOT PER ENTITY.
    #
    # An entity is written only when every one of its chunks was answered -- correct, because a
    # partial record is cached forever and reads as an entity with fewer feats. But with a thin
    # pool almost every entity had at least one unanswered chunk, so almost nothing was ever
    # written, and each pass re-read from scratch the same passages it had already paid for.
    # Work happened; nothing accumulated. Forty-five entities in an hour, 168 chunks abandoned,
    # and an estimate of 582 hours that really meant never.
    #
    # Caching the ANSWER TO A PASSAGE fixes it without weakening the guard: a retry re-asks only
    # what is still missing, so every call ever made counts for something. The key is the
    # passage text, so two entities sharing a wiki index page pay for it once between them.
    kept, fabricated, generic = [], 0, 0
    unanswered = 0
    reused = 0
    for title, ch in chunks:
        # _ask, NOT P.ask. This one line is why every transport fix above did nothing.
        #
        # `_ask` is the router: Cascade first, across a dozen separately-metered providers,
        # with the local GPU only when all of them decline. `P.ask` is the local GPU,
        # unconditionally. The hot loop called the second, so the reader spent the morning
        # serialising on one 10GB card while thirteen cloud buckets sat idle -- and every
        # diagnostic pointed at Cascade, because Cascade was never being asked.
        cached = _chunk_get(host, ch)
        if cached is not None:
            got = cached
            reused += 1
        else:
            got = _ask(c, SYSTEM, "ENTITY: " + name + "\nPAGE: " + title + "\n\n" + ch,
                       SCHEMA)
            if got is not None:
                _chunk_put(host, ch, (got or {}).get("feats", []))
        if got is None:
            # NOBODY ANSWERED. Not "this passage holds no feats" -- nobody read it. Every
            # transport declined: the pool was exhausted or erroring and the GPU was benched.
            unanswered += 1
            continue
        for f in (got or {}).get("feats", []):
            s = (f.get("sentence") or "").strip()
            ax = f.get("axis")
            if ax not in AXES or len(s) < 25:
                continue
            # Verbatim or it does not exist. Roughly half of what the model returns on a sparse
            # chunk is padding -- it is told it may return twelve, and a chunk holding two will
            # get twelve anyway. The check is the whole sentence, not its opening: a paraphrase
            # that begins with a real fragment and then wanders would pass a prefix test, and 3%
            # of an earlier batch did exactly that.
            #
            # Quotes and dashes are normalised on both sides first. Wiki text carries curly
            # apostrophes and the model returns straight ones, so "Hera's" failed against
            # "Hera's" and a real sentence was thrown away as a fabrication.
            if _norm_q(s) not in _norm_q(ch):
                fabricated += 1
                continue
            # The entity has to be IN it. A techniques index describes moves generically -- "The
            # user in an upside-down position strikes the opponent away" is a rulebook entry, not
            # a feat anybody performed, and it passes a verbatim check because it is genuinely
            # printed on the page. Requiring the name or a pronoun is what separates a record of
            # an act from a definition of a capability.
            if not _names(s, name):
                generic += 1
                continue
            kept.append({"feat": s, "axis": ax, "page": title})

    out = {"entity": name, "host": host, "pages": sorted(text),
           "chunks_read": len(chunks) - unanswered, "chunks_unanswered": unanswered,
           "chunks_reused": reused,
           "chunks_skipped": max(0, skipped),
           "feats": kept, "fabricated_dropped": fabricated,
           "generic_dropped": generic,
           "axes": sorted({f["axis"] for f in kept})}

    # AN ENTITY IS CACHED ONLY WHEN IT WAS ACTUALLY READ, ALL OF IT.
    #
    # Writing the record marks this entity done forever -- read_entity returns the cache on every
    # later call and queue() never revisits it. So a record written after some chunks went
    # unanswered is not an incomplete record, it is a PERMANENTLY incomplete one, and it is
    # indistinguishable from an entity that genuinely had fewer feats.
    #
    # This was live: 4,755 of 6,706 chunks in a single pass hit a benched GPU after the pool
    # declined, returned None, and were counted as read. Seventy-one percent of the passages in
    # that pass were never seen by any model and their entities were filed as finished. Nothing
    # raised, nothing logged, and the progress line said 9.8 chunks a second.
    if unanswered:
        return out
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(out, f, indent=1, ensure_ascii=False)
    return out


# An own page this size is a deep subject: tens of model calls, and worth them.
DEEP_CHARS = 50_000
# Short subjects admitted alongside each deep one. Four keeps the pool mixed without starving
# the deep end -- at ten workers there is always one long read running and nine short ones.
WEAVE = 4


def priority(rows):
    """Depth first, because depth is what the model is actually better at.

    This was ordered by depth, then flipped to coverage, then measured -- and the measurement
    settled it. Of 43 entities where the regex miner had found nothing, the model also found
    nothing in 41. A 5% conversion. They agree on the negatives, because most entries genuinely
    have no feats: an item, a location, a Pokemon trainer. The library recording that WITH THE
    PAGES READ is the correct answer and not a gap.

    Where the model is transformative is the opposite case. Goku had 13 feats from the regex
    gates and 241 from being read. That is what makes an eleven-axis worksheet possible, and no
    amount of breadth substitutes for it.

    So: entities that already show evidence, deepest first. Coverage of the remaining 17,148
    entries with no page at all is a DISCOVERY problem -- network, cheap, parallel -- and putting
    a GPU on it was spending the expensive resource on the cheap constraint.
    """
    def yield_per_chunk(r):
        """Evidence already visible, divided by what it will cost to read.

        Ordering by raw size put the worst possible entities first. `Metal Gear Sahelanthropus`
        carries 783,000 characters -- seventy-eight model calls -- almost all of it a shared
        weapons index that names it twice, and ten workers each took one of those and produced
        nothing for the first quarter hour of every run. Its regex axes were high for the same
        reason its cost was: the giant attached page.

        Cost is the divisor, so a dense own-page entity outranks a thin entity bolted to an
        encyclopedia. Nothing is dropped -- Sahelanthropus is still read, just after the
        hundreds of subjects whose evidence arrives in three calls instead of seventy-eight.
        """
        chunks = max(1, r.get("chars", 0) // CLOUD_CHUNK)
        return (r.get("axes", 0) + 0.5 * r.get("quantities", 0)) / chunks

    # The regex miner's axis count turned out to carry no signal here -- every entity in the
    # queue shows either one axis or none, because that gate was built for Ruin and 240-character
    # blurbs. Ranking on it sorted 27,754 entries into two heaps and then ordered them by
    # accident, which is how "Stars" and "LSAT" ended up above Goku.
    #
    # What does carry signal is the OWN PAGE: the article whose title is the entity's name. A
    # large own page means the wiki treats this as a subject in its own right, and that is
    # exactly the case where reading transforms the record -- Goku went from 13 regex feats to
    # 241 read ones off a 97,000-character own page. A large TOTAL with a small own page means
    # the opposite: a name that appeared in somebody else's index.
    have_page = [r for r in rows if r.get("own", 0) > 0]
    no_page = [r for r in rows if not r.get("own", 0) and r.get("chars", 0) >= 2000]
    have_page.sort(key=lambda r: (-r.get("own", 0), -yield_per_chunk(r)))
    # Then the names that only ever appeared inside other articles, densest mention first. These
    # are still read -- nothing here is dropped -- they are simply the thinner half of the work.
    no_page.sort(key=lambda r: (-yield_per_chunk(r), r.get("chars", 0)))

    # DEPTH AND BREADTH, not depth then breadth. Sorted purely by own-page size the queue opens
    # with Dark Angels, Space Wolves, Ultramarines and Blood Angels -- four Warhammer chapters at
    # sixty-odd model calls apiece. Ten workers would spend the first hours of every run inside
    # one franchise while 27,000 subjects with three-call pages waited behind them.
    #
    # Interleaving fixes the ORDER without touching the CONTENT: one deep subject enters the
    # pool alongside four short ones, so a run stopped at any moment has both the richest
    # material available and a wide spread of settled questions. Nothing is dropped, nothing is
    # sampled, and the full list is still the full list.
    deep = [r for r in have_page if r.get("own", 0) >= DEEP_CHARS]
    light = [r for r in have_page if r.get("own", 0) < DEEP_CHARS]
    woven, di, li = [], 0, 0
    while di < len(deep) or li < len(light):
        if di < len(deep):
            woven.append(deep[di]); di += 1
        for _ in range(WEAVE):
            if li < len(light):
                woven.append(light[li]); li += 1
    return woven + no_page


QCACHE = os.path.join(HERE, "state", "read_queue_index.json")


def _load_qcache():
    try:
        with open(QCACHE, encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        silence.note("read.py:qcache-load")
        return {}


def _save_qcache(d):
    try:
        os.makedirs(os.path.dirname(QCACHE), exist_ok=True)
        tmp = QCACHE + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(d, f)
        os.replace(tmp, QCACHE)
    except Exception:
        silence.note("read.py:qcache-save")


def queue(all_entries=True):
    """Everything with cached source pages, ordered by how much evidence it already shows.

    Breadth is every ENTRY, not every character. Places, Vessels, Powers, Factions and Events
    carry pages too, and Part Three assays "person, beast, god, relic, polity, or power system"
    -- a relic with a Ruin feat is as assayable as a swordsman, and the sweep's Persons-only view
    was a convenience of that report rather than a limit of the instrument.

    Order is still by evidence depth, so a run stopped at any point has read the richest material
    available for that spend rather than an alphabetical slice.
    """
    import feats as FF
    recs = P.records()
    hosts = json.load(open(FF.HOSTS, encoding="utf-8"))
    qcache = _load_qcache()
    rows = []
    for _, r in recs:
        h = hosts.get(r["source"])
        if not h:
            continue
        for e in r["entries"]:
            if not all_entries and not (e.get("category") or "").startswith("Persons"):
                continue
            path = os.path.join(FF.CACHE, re.sub(r"[^A-Za-z0-9]+", "_", h)[:40],
                                re.sub(r"[^A-Za-z0-9]+", "_", e["name"])[:80] + ".json")
            if not os.path.exists(path):
                continue
            # THE CACHE FILE IS OPENED ONCE PER LIFETIME, NOT ONCE PER RUN.
            #
            # These records carry the full cleaned page text -- 497 million characters across
            # the tree -- and the queue only needs four numbers out of each. Parsing all of it
            # at the head of every run took longer than the run's first hour of useful work, and
            # from outside it looked exactly like a reader that had started and gone quiet.
            # Keyed on mtime, so a record the roll has just rewritten is re-read and every other
            # one is not.
            try:
                st = os.stat(path)
            except OSError:
                silence.note("read.py:queue-stat")
                continue
            key = path
            memo = qcache.get(key)
            if memo and memo.get("mtime") == st.st_mtime and memo.get("size") == st.st_size:
                if memo.get("skip"):
                    continue
                rows.append(dict(memo["row"], name=e["name"], host=h, source=r["source"],
                                 category=(e.get("category") or "?")[:20]))
                continue
            try:
                with open(path, encoding="utf-8") as fh:
                    ev = json.load(fh)
            except Exception:
                silence.note("read.py:354")
                continue
            if not ev.get("text"):
                qcache[key] = {"mtime": st.st_mtime, "size": st.st_size, "skip": True}
                continue
            # An entity's OWN page is the part of its evidence that is actually about it. The
            # rest is whatever shared index its name appeared in, and that is where the cost
            # hides.
            own = 0
            for t, body in (ev.get("text") or {}).items():
                if t.strip().lower() == e["name"].strip().lower():
                    own = len(body)
                    break
            row = {"chars": ev.get("chars_read", 0), "own": own,
                   "axes": len({f.get("axis") for f in ev.get("feats", [])}),
                   "quantities": len(ev.get("quantities") or [])}
            qcache[key] = {"mtime": st.st_mtime, "size": st.st_size, "row": row}
            rows.append(dict(row, name=e["name"], host=h, source=r["source"],
                             category=(e.get("category") or "?")[:20]))
    _save_qcache(qcache)
    return priority(rows)


def run(limit=None, workers=2, cap_chunks=None, all_entries=True):
    c = config()
    todo = queue(all_entries=all_entries)
    if limit:
        todo = todo[:limit]

    done = {"n": 0, "feats": 0, "fab": 0, "chunks": 0, "skipped": 0, "unanswered": 0}
    lock = threading.Lock()
    t0 = time.time()

    def work(r):
        try:
            out = read_entity(c, r["host"], r["name"], cap_chunks=cap_chunks)
        except Exception:
            silence.note("read.py:379")
            out = None
        with lock:
            done["n"] += 1
            if out:
                done["unanswered"] += out.get("chunks_unanswered", 0)
                done["feats"] += len(out["feats"])
                done["fab"] += out["fabricated_dropped"]
                done["chunks"] += out["chunks_read"]
                done["skipped"] += out["chunks_skipped"]
            n = done["n"]
            if n % 5 == 0 or n == len(todo):
                el = time.time() - t0
                dead = ""
                try:
                    import cascade_bridge as CB
                    d = CB.dead_buckets()
                    if d:
                        dead = "  benched: " + ", ".join(sorted(d))
                except Exception:
                    silence.note("read.py:dead-buckets")
                # THE ESTIMATE IS IN CHUNKS, NOT ENTITIES.
                #
                # Entities are wildly uneven -- a Warhammer chapter is sixty model calls and a
                # side character is two -- and the queue is deliberately front-loaded with the
                # deepest subjects. An entities-per-second rate measured over that head projected
                # 121 hours for work whose real bound was fifteen. A chunk is the unit that
                # actually costs something, so it is the unit the estimate is built from.
                # A ROLLING RATE, because the queue opens with whatever is already cached and
                # those entities complete in microseconds. Averaged from t0 they reported 1,595
                # chunks per second and an ETA of 0.0 hours for eight hours of work -- a number
                # that is not merely wrong but reassuring, which is worse.
                _rate_log.append((time.time(), done["chunks"]))
                while len(_rate_log) > 2 and time.time() - _rate_log[0][0] > RATE_WINDOW:
                    _rate_log.pop(0)
                if len(_rate_log) > 1:
                    dt = _rate_log[-1][0] - _rate_log[0][0]
                    dc = _rate_log[-1][1] - _rate_log[0][1]
                    crate = dc / dt if dt > 1 else 0.0
                else:
                    crate = 0.0
                if crate <= 0:
                    crate = done["chunks"] / max(el, 1e-9)
                left = max(0, CHUNK_BUDGET - done["chunks"])
                print("  %6d/%d  %5.2f chunks/s  feats %7d  dropped %5d  chunks %7d/%d "
                      "(%d to GPU, %d UNANSWERED, not cached)  eta %.1fh%s"
                      % (n, len(todo), crate, done["feats"], done["fab"], done["chunks"],
                         CHUNK_BUDGET, _FELL_BACK[0], done["unanswered"],
                         left / max(crate, 1e-9) / 3600, dead), flush=True)

    from concurrent.futures import ThreadPoolExecutor
    # cap_chunks is None by default and must stay printable as such. Hard Rule 0 made the
    # uncapped path the normal one, and this format string still assumed a number -- so the
    # reader died on its own status line for ten supervisor cycles while the log recorded
    # "finished". A crash on the banner is the cheapest possible version of this project's
    # signature bug, and it still cost an hour.
    ensure_transport()
    # The honest denominator: every chunk the queue can produce at the size this run will use.
    # An upper bound -- the mention and action filters remove some -- so the estimate is
    # pessimistic rather than flattering, which is the right direction for a number anyone is
    # going to plan a night around.
    global CHUNK_BUDGET
    size = CLOUD_CHUNK if _CASCADE_OK else CHUNK
    CHUNK_BUDGET = max(1, sum(r.get("chars", 0) for r in todo) // size)
    # WORKERS TRACK THE WIDTH OF THE POOL, not the width of the machine.
    #
    # Sixteen workers were measurably slower than eight, because the pool has about a dozen
    # usable remote buckets and the rest of the sixteen queued on providers already busy or on
    # the single local GPU. Concurrency here is bounded by how many separately-metered places
    # there are to send a request, and that number is knowable rather than guessable.
    # And the regime caps whatever that reasoning produces. The bucket-count logic below is
    # correct WHEN THERE ARE BUCKETS; when the pool has shed to nothing and the local GPU is
    # carrying the run, one-worker-per-bucket resolves to a number that describes a pool that
    # no longer exists. The cap is applied after, not instead: on cloud it never binds.
    if workers in (None, 0, "auto"):
        try:
            import cascade_bridge as CB
            # ONE PER BUCKET. Two was tried and it is worse, not twice as good.
            #
            # The claim hands each worker a DIFFERENT bucket, so one worker per bucket is exactly
            # the concurrency the pool can absorb without two workers stacking on one meter. Past
            # that, the extra workers are declined, and a declined call now BACKS OFF instead of
            # dropping the passage -- so every worker ends up asleep. Twenty workers ran at 0.33
            # chunks a second; fourteen ran at ten. The decline storm costs more than the
            # parallelism buys.
            # ANSWERING lanes, not TAGGED ones. cloud_buckets() counts the router's pool
            # tags (~5); the widened fallback reaches every funded bucket, and the proof
            # says how many actually answer right now (14 this evening). Auto ran the reader
            # at a third of the pool's real width for a day.
            try:
                import json as _j, os as _o
                _pp = _o.path.join(HERE, "data", "POOL_PROOF.json")
                _n = sum(1 for x in _j.load(open(_pp, encoding="utf-8"))
                         if isinstance(x, dict) and x.get("verdict") == "answers")
            except Exception:
                silence.note("read.py:auto-proof")
                _n = len(CB.cloud_buckets())
            workers = max(2, min(16, _n + 2)) if _CASCADE_OK else 2
        except Exception:
            silence.note("read.py:auto-workers")
            workers = 8
    try:
        import tuning as T
        prof = T.profile(force=True)
        capped = T.workers(int(workers))
        if capped != int(workers):
            print("read: regime %s (%s) caps workers %s -> %d"
                  % (prof["regime"], prof["why"], workers, capped), flush=True)
        workers = capped
    except Exception:
        silence.note("read.py:tuning")
    print("read: %d entries with pages, %d workers, chunks %s"
          % (len(todo), workers, cap_chunks if cap_chunks else "uncapped"), flush=True)
    with ThreadPoolExecutor(max_workers=workers) as ex:
        list(ex.map(work, todo))
    print("done in %.2fh  %d feats kept, %d fabrications dropped"
          % ((time.time() - t0) / 3600, done["feats"], done["fab"]))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--run", action="store_true")
    ap.add_argument("--limit", type=int)
    ap.add_argument("--workers", default="auto",
                    help="number, or 'auto' to match the count of usable remote buckets")
    ap.add_argument("--chunks", type=int, default=None,
                    help="omit to read every chunk of every page")
    ap.add_argument("--persons-only", action="store_true")
    ap.add_argument("--transport", choices=("auto", "cascade", "ollama"), default="auto")
    ap.add_argument("--one", nargs=2, metavar=("HOST", "ENTITY"))
    a = ap.parse_args()

    set_transport(a.transport)
    if a.one:
        out = read_entity(config(), a.one[0], a.one[1], cap_chunks=a.chunks)
        print("%s: %d feats across %s (%d chunks read, %d skipped, %d dropped)"
              % (out["entity"], len(out["feats"]), ",".join(out["axes"]),
                 out["chunks_read"], out["chunks_skipped"], out["fabricated_dropped"]))
        for f in out["feats"][:12]:
            print("   %-14s %s" % (f["axis"], f["feat"][:104]))
        return 0
    if a.run:
        w = a.workers
        if isinstance(w, str) and w.strip().isdigit():
            w = int(w)
        run(limit=a.limit, workers=w, cap_chunks=a.chunks,
            all_entries=not a.persons_only)
        return 0
    ap.print_help()
    return 0


if __name__ == "__main__":
    sys.exit(main())
