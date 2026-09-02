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
import contextlib
import hashlib
import json
import os
import re
import sys
import threading
import time
import unicodedata

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import pipeline as P                                                    # noqa: E402
import feats as F                                                       # noqa: E402
import assay as A                                                       # noqa: E402
import cachekey
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


def _fold_diacritics(s):
    """Strip combining marks after NFKD decomposition: 'Zanpakutō' -> 'Zanpakuto'.

    Added alongside the Unicode-aware split below (order e61e1c8e9ac4). Splitting on `\\w`
    instead of `[^A-Za-z]+` keeps an accented word whole rather than shattering it, but a
    whole-name comparison then needs the ACCENT itself to be optional, because the wiki prose
    and the catalogue disagree about carrying it -- "Zanpakuto" (2 unaccented instances measured
    live) against the catalogue's "Zanpakutō". The old ASCII-only split passed this one case
    by accident, by treating the macron as a separator and truncating both sides down to a
    common stem; folding is the same outcome on purpose, without shattering names that need
    their non-Latin letters kept together (Morgaen, and CJK/Cyrillic names with nothing to
    fold at all -- NFKD leaves those untouched).
    """
    return ''.join(c for c in unicodedata.normalize('NFKD', s) if not unicodedata.combining(c))


def _names(sentence, entity):
    """Is the entity actually the subject of this sentence?

    Accepts the entity's name, any distinctive word of it (surnames and given names are used
    interchangeably across a wiki), or a personal pronoun. Rejects the generic subjects a
    techniques index uses -- "the user", "the wielder", "this technique".
    """
    low = _fold_diacritics(sentence).lower()
    entity_f = _fold_diacritics(entity)
    # UNICODE-AWARE SPLIT (order e61e1c8e9ac4, 2026-09-01). This was `[^A-Za-z]+`, which treats
    # every accented or non-Latin letter as a separator: "Morgaen" split into "Mo"/"rgae"/"n",
    # none of which clears the length-4 floor below, so 391 catalogued names with a non-ASCII
    # letter (Morgaen, Quang Tri, Aule, Koenig, 'El Nino', ...) had NO usable word here at all.
    # `\w` is Unicode-aware for str patterns by default, matching feats_index._norm's own
    # `c.isalnum()` folding rather than hand-spelling a fifth, ASCII-only convention. Both sides
    # are folded through `_fold_diacritics` first (see above) so a name kept whole here can
    # still match prose that dropped its accent -- measured live on the full corpus diff, one
    # regression (Zanpakutō/Zanpakuto) surfaced without the fold and is why it is here.
    parts = [w for w in re.split(r'\W+', entity_f) if len(w) > 3]
    # A NAME WORD MUST START A WORD OF THE SENTENCE. This was raw substring containment
    # (`w.lower() in low`), directly under a comment explaining why the pronoun test below was
    # tokenised -- the boundary discipline was applied to the second check and not the first.
    # Substring matching attributed 'MetalGarurumon then defeats Azulongmon' to GARURUMON (a
    # different catalogue entity, whose magnitude the borrowed feat then inflates) and put every
    # sentence mentioning the Daily 'Planet' onto LOIS LANE, via 'lane'.
    #
    # Full-corpus diff before shipping, per the run-#3 lesson that a matching change is not
    # verified until the cases nobody reported are checked -- 39,198 sentences across all 1,219
    # readfeats files. Plain word-boundary tokenisation was measured FIRST and rejected: it
    # dropped 265 real matches, because wiki prose inflects ('Xenomorphs', 'glaives',
    # 'Geraldos') and a name word is a stem far more often than it is a whole token. Matching at
    # the START of a token keeps every one of those 265 and removes 37 sentences, every one of
    # them a suffix collision of the MetalGarurumon/Planet kind. 0 real matches lost.
    if any(t.startswith(w.lower()) for t in re.split(r'\W+', low) if t for w in parts):
        return True
    # NO WORD ABOVE THE FLOOR (order e61e1c8e9ac4). 4,939 catalogued entities -- Ash, Vi, Ike,
    # Uub, 'The Six', 'Mr. Fox' -- have no single word longer than three letters, so `parts` is
    # empty and every sentence naming them outright, with no pronoun, fell through to `False`
    # and was counted as `generic_dropped` -- the OPPOSITE of what that counter documents.
    # read_entity's chunk-selection filter (read.py:731) already falls back to the whole name
    # for exactly this case; this is the same fallback, but phrase-bound rather than a raw
    # substring test, because a raw substring here would let a short word like "The" (half of
    # 'The Six') match on its own -- the exact generic-word risk the length floor exists to
    # stop. Instead the entity's own words are required TOGETHER, in order, with the same
    # token-start rule as above applied to the whole phrase.
    if not parts:
        whole = [w for w in re.split(r'\W+', entity_f) if w]
        if whole:
            pattern = r'\b' + r'\s+'.join(re.escape(w) for w in whole)
            if re.search(pattern, low, re.IGNORECASE):
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
# `+= 1` on a shared slot is a read-modify-write, not an atomic step, and both increments below
# run inside `_ask_ungated` under the whole worker pool. Lost updates understate the "N to GPU"
# figure -- and that figure is the only thing that distinguishes a run quietly served entirely
# from the slow path from a run that is merely slow, which is the reason the counter exists.
_FELL_BACK_LOCK = threading.Lock()
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

# ONE PHYSICAL FACT, READ RATHER THAN RESTATED. How many requests the card serves at once is
# decided by the daemon's `OLLAMA_NUM_PARALLEL`, and it was previously spelled out a second time
# here as a bare `2` and a third time as `gpu_lane.MAX_SLOTS`. Three constants for one fact, with
# nothing linking them: change the daemon's setting and this gate keeps admitting the old number,
# silently over- or under-subscribing the card. `PANSCRIPTUM_GPU_SLOTS` still wins if set, so the
# lane and this gate can be pinned together for an experiment. The 2 at the end is the last
# resort, not the source of truth.
GATE_LOCAL_N = max(1, int(os.environ.get("PANSCRIPTUM_GPU_SLOTS")
                          or os.environ.get("OLLAMA_NUM_PARALLEL") or "2"))
GATE_RECHECK_S = 120
_GATE_CLOUD = threading.BoundedSemaphore(GATE_CLOUD_N)
_GATE_LOCAL = threading.BoundedSemaphore(GATE_LOCAL_N)
_GATE_STATE = {"at": 0.0, "regime": "cloud"}
# Guards the check-and-set below, same shape as `_TRANSPORT_LOCK` above and for the identical
# reason `ensure_transport`'s docstring names: the test and the write are not atomic together,
# so every in-flight worker (up to GATE_CLOUD_N=16) can pass a stale "it's been over 120s" test
# at once and all call `tuning.regime()` -- reading data/POOL_PROOF.json and querying
# state/cascade_scratch.db -- simultaneously, on every recheck, for the life of a long run.
_GATE_LOCK = threading.Lock()


def _gate():
    now = time.time()
    if now - _GATE_STATE["at"] > GATE_RECHECK_S:
        with _GATE_LOCK:
            if now - _GATE_STATE["at"] > GATE_RECHECK_S:   # re-check: someone may have won already
                try:
                    import tuning as T
                    _GATE_STATE["regime"] = T.regime()
                except Exception:
                    silence.note("read.py:gate-regime")
                _GATE_STATE["at"] = now
    return _GATE_CLOUD if _GATE_STATE["regime"] == "cloud" else _GATE_LOCAL


_CARD_HELD = threading.local()


@contextlib.contextmanager
def _card_gate():
    """Hold one of the card's GATE_LOCAL_N permits -- unless this thread already holds one.

    RE-ENTRANCY HERE IS A DEADLOCK, NOT A NUISANCE. _gate() hands out _GATE_LOCAL itself when
    the regime reads local/starved, and _ask holds it for the whole ladder. A second, nested
    acquire of that same BoundedSemaphore from the same thread cannot be satisfied once
    GATE_LOCAL_N threads are inside the ladder: each holds the only permits there are and each
    blocks forever waiting for another. So the permit is tracked PER THREAD, and a thread that
    is already inside the card's gate passes straight through instead of acquiring twice.
    """
    if getattr(_CARD_HELD, "on", False):
        yield
        return
    with _GATE_LOCAL:
        _CARD_HELD.on = True
        try:
            yield
        finally:
            _CARD_HELD.on = False


def _ask(c, system, prompt, schema):
    """One structured call, by whichever transport is available -- through the adaptive gate."""
    gate = _gate()
    if gate is _GATE_LOCAL:
        # The regime already chose the narrow gate; take it through _card_gate so the nested
        # acquire in _local() sees that this thread is holding it and does not deadlock.
        with _card_gate():
            return _ask_ungated(c, system, prompt, schema)
    with gate:
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
                    silence.note("read.py:ask-quick-pool")
            if _TRANSPORT != "cascade" and _GPU_DOWN_UNTIL[0] <= time.time():
                got = _local(c, system, prompt, schema)
                if got is not None:
                    with _FELL_BACK_LOCK:
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
                    silence.note("read.py:ask-backoff-ladder")
                delay = BACKOFF[min(attempt, len(BACKOFF) - 1)]
            # Every bucket tried and none answered. Falling through to the GPU is right for
            # auto -- but cascade mode is a promise never to touch the GPU (the check just
            # below), and the counter has to agree with what actually happened: a chunk that is
            # NOT going to the GPU must not be counted as having gone there. Order 6b7f51f8ec2e:
            # this increment used to fire before that check, so the progress line's "(%d to
            # GPU)" included chunks the GPU never received.
            #
            # AND THE INCREMENT ITSELF HAS NOW MOVED (order 6f95694b8143). It stood here, past
            # the cascade guard but still well above the `return _local(...)` that ends this
            # function -- so it went on counting chunks the card never received, by a different
            # route: `_local` returns None immediately when `_GPU_DOWN_UNTIL` is in the future
            # (the card is benched), and nothing between here and there re-tested that. One
            # counter with two meanings at its two sites, and the sibling increment on the quick
            # pool above already had the right one. It now lives beside the call it describes.
            if _TRANSPORT == "cascade":
                return None
        elif _TRANSPORT == "cascade":
            # ensure_transport() came back False -- cascade_bridge would not import, or
            # CB.engine() was falsy. Order 6b7f51f8ec2e: this branch used to be absent, so
            # control fell out of the whole `if _TRANSPORT in ("auto", "cascade")` block
            # to the unconditional `return _local(...)` at the end of this function -- sending
            # a cascade-only call to the local GPU, exactly what the "if _TRANSPORT == 'cascade'"
            # checks above exist to forbid. auto still falls through on purpose; only cascade
            # is a hard no.
            return None
    # THE GPU GETS THE SAME TEXT, IN PIECES IT CAN HOLD.
    #
    # CLOUD_CHUNK == CHUNK now (:94-96) -- there is no longer a cloud/local size difference for
    # this to compensate for. What is left is header overhead: read_entity's prompt is
    # "ENTITY: <name>\nPAGE: <title>\n\n" plus a full-size chunk, so a prompt can run a little
    # over CHUNK before it ever reaches here. Ollama does not refuse an overlong prompt -- it
    # truncates it silently, which is the exact fault that once looked like a 51% fabrication
    # rate. So an oversized passage is re-split in _local_carded and the results merged. The
    # reader still sees every character; only the seams move.
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
    #
    # COUNTED HERE, AND ONLY ON AN ANSWER (order 6f95694b8143). Every route that reaches this
    # line hands the chunk to the card: the backoff ladder giving up in auto mode, an
    # `ensure_transport()` that came back False in auto mode, and an explicit `--transport
    # ollama`. A benched or failing card returns None and that chunk went nowhere, so the "(%d
    # to GPU)" figure counts what the GPU actually received -- which is the whole reason
    # read.py:213-215 says the counter exists.
    got = _local(c, system, prompt, schema)
    if got is not None:
        with _FELL_BACK_LOCK:
            _FELL_BACK[0] += 1
    return got


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
    """The GPU, bounded to the card's real slot count, benched when it stops answering.

    THE GATE HAS TO BIND ON WHERE THE CALL LANDS, NOT ON WHAT THE REGIME IS CALLED.

    _gate() picks its width from tuning.regime(), and regime() answers "cloud" whenever enough
    buckets ANSWER A PROOF CALL. Reachability is not capacity. Measured 2026-08-24: regime read
    "cloud", so every worker passed the wide GATE_CLOUD_N=16 gate -- while the live cloud success
    rate was 4.1% over the previous hour, so nearly every chunk fell straight through the ladder
    onto the card. Nine requests were in flight against OLLAMA_NUM_PARALLEL=2. Seven of them sat
    in the daemon's queue, and a trivial 7-token call measured 113s and 178s of pure queue wait
    against 0.58s unloaded -- past the 180s timeout below, which benches the GPU for GPU_BENCH
    and DISCARDS the chunk. Result over 7.5 hours: 1,235 chunks handed to the GPU, 1,168 of them
    UNANSWERED and not cached -- 94.6% of the work thrown away by a job that looked healthy.

    That is precisely the pile-up GATE_LOCAL_N exists to prevent ("the surplus workers WAIT at
    the gate instead of stacking onto the card"), and it did not bind because the regime label
    disagreed with where the traffic actually went. So the local leg now takes the local gate
    unconditionally: whatever the regime is called, only GATE_LOCAL_N calls touch the card at
    once. Waiting for a permit costs a worker seconds; timing out costs the chunk entirely.

    The bench check is deliberately BEFORE the gate -- a benched card should not consume a
    permit just to return None.
    """
    if _GPU_DOWN_UNTIL[0] > time.time():
        return None
    with _card_gate():
        return _local_carded(c, system, prompt, schema)


def _local_carded(c, system, prompt, schema):
    """The local call itself. Call _local, not this: this one does not hold the card's gate."""
    c = dict(c, model=fallback_model(c))
    if len(prompt) <= CHUNK + 2000:
        # 360s, not 180: sized for the 8B's real service time on a full chunk (prefill on a
        # 10k-token prompt plus a structured reply), WITH the gate bounding concurrency to the
        # card's slots so queue wait stays near zero. At 180s the card burned at 98% while 94%
        # of handed chunks died at the deadline AFTER their compute was spent -- the thrash of
        # 2026-08-24: paying for work and discarding it. A completed slow call beats a fast
        # discard every time; chunks that still miss are deferred, never lost.
        got = P.ask(c, system, prompt, schema, timeout=360)
        if got is None:
            _GPU_DOWN_UNTIL[0] = time.time() + GPU_BENCH
        return got
    # Order 5bf48fa9f70d: a None from any piece used to be swallowed by `(got or {})`, so a
    # total transport failure on every piece came back as {"feats": []} -- ANSWERED, not
    # unanswered, permanently caching an empty result over a passage nobody actually read. The
    # ordinary chunk path -- the `len(prompt) <= CHUNK + 2000` branch at the top of THIS function
    # (:554-564) -- treats a None as unanswered and benches the GPU; this path has to make the
    # same promise, not a weaker one just because it is rarer.
    # (Order ce9735ec93ba: that citation read ":521-524", which is `def _local` and the opening
    # of its docstring -- a different function, saying nothing about a None or about benching.
    # The branch is named as well as numbered now, so the proof survives the next line shift.)
    head, _, body = prompt.partition(chr(10) + chr(10))
    merged = {"feats": []}
    for i in range(0, len(body), CHUNK):
        got = P.ask(c, system, head + chr(10) + chr(10) + body[i:i + CHUNK],
                    schema, timeout=180)
        if got is None:
            _GPU_DOWN_UNTIL[0] = time.time() + GPU_BENCH
            return None
        merged["feats"].extend(got.get("feats", []))
    return merged


def config():
    import yaml
    cfg = yaml.safe_load(open(os.path.join(HERE, "config.yaml"), encoding="utf-8"))
    return {"model": cfg.get("model"),
            "ollama_host": cfg.get("ollama_host", "http://localhost:11434"),
            "seed": 47, "num_ctx": cfg.get("num_ctx", 6144)}


def cache_path(host, name):
    """The entity's NATURAL cache path. Delegates -- there is one spelling of this key.

    M23: this used to build the path inline, which made it a fifth independent copy of a lossy
    formula. It has no callers left (`read_entity` goes through `cachekey` so the read is
    verified), and it is kept rather than deleted because deleting a public helper is a
    signature change. Delegating is the safer half of that trade: anything that finds it later
    gets the same answer as everything else, and it cannot drift.
    NOTE it returns the natural path only. If you are READING, use `cachekey.load`, which proves
    the file belongs to the entity you asked for.
    """
    return cachekey.natural_path(CACHE, host, name)


CHUNK_CACHE = os.path.join(HERE, "data", "chunkfeats")


def _chunk_key(host, ch, entity):
    """A chunk's identity: its exact text AND the entity it was read FOR.

    THE ENTITY BELONGS IN THE KEY, AND LEAVING IT OUT LOST REAL FEATS SILENTLY (2026-08-24).

    The original premise was "two entities attached to the same shared index page read the same
    passage, and there is no reason to pay for it twice -- so the key is the passage, not the
    pair." That is true of the PASSAGE and false of the ANSWER. The model is not summarising the
    passage: `SYSTEM` opens "You are reading one page of a fiction wiki to collect POWER FEATS
    for an entity", the prompt carries `ENTITY: <name>`, and what comes back is the feats OF
    THAT ENTITY.

    So on a shared franchise index -- exactly the case the old docstring cited as the win -- the
    first entity to arrive cached ITS feats under a key naming no entity, and every later entity
    hitting that passage was served the first one's answer. Downstream, `_names(s, name)`
    correctly rejects sentences that do not name the later entity, so they were counted as
    `generic_dropped`, the chunk was recorded as ANSWERED, and `read_entity` wrote the record as
    complete. This is the one path in this file that loses work PERMANENTLY: the "deferred, not
    lost" guarantee (`if unanswered: return out`) never fires, because nothing went unanswered.
    The entity is filed as having no feats in a passage that describes its feats -- this
    project's signature failure, once more in a new costume.

    Keying on the entity too costs a sharing that was never legitimate. Entries written under
    the old key simply stop being found; they are LEFT IN PLACE, not deleted, and those passages
    are re-asked per entity as the reader reaches them.
    """
    h = hashlib.sha256(
        (host + chr(31) + (entity or "") + chr(31) + ch).encode("utf-8")).hexdigest()
    return h[:2], h[2:18]


def _chunk_get(host, ch, entity):
    d, name = _chunk_key(host, ch, entity)
    p = os.path.join(CHUNK_CACHE, d, name + ".json")
    if not os.path.exists(p):
        return None
    try:
        with open(p, encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        silence.note("read.py:chunk_get")
        return None


def _chunk_put(host, ch, entity, feats):
    d, name = _chunk_key(host, ch, entity)
    folder = os.path.join(CHUNK_CACHE, d)
    try:
        os.makedirs(folder, exist_ok=True)
        p = os.path.join(folder, name + ".json")
        # A PER-WRITER TEMP NAME. This was `p + ".tmp"`, derived only from the cache key, so two
        # workers answering the same passage at once opened and truncated ONE file -- each
        # writing over the other mid-dump, then both renaming it. `replace_retry` makes the
        # rename safe; nothing made the WRITE safe. The pid and thread id make the staging file
        # private, so the only shared operation left is the atomic rename.
        tmp = "%s.%d.%d.tmp" % (p, os.getpid(), threading.get_ident())
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump({"feats": feats}, f, ensure_ascii=False)
        # VERDICT DELIBERATELY UNUSED, and checked rather than assumed. This is a pure memo of
        # one model answer, and a miss is a re-ask, not a wrong answer: `_chunk_get` returns
        # None for "not cached", `read_entity` distinguishes that from an empty `feats` list
        # (see its `got is None` branch, which counts `unanswered` rather than recording an
        # honest absence), and the key already carries host+entity+chunk text, so a chunk that
        # fails to land can only ever be re-mined -- never mis-read as a silent no-feat result.
        # `replace_retry` records the denial itself, so the loss is already on file. The cost of
        # a failure is one model call next run; gating it would abort a read for that.
        silence.replace_retry(tmp, p)
    except Exception:
        silence.note("read.py:chunk_put")


def read_entity(c, host, name, cap_chunks=None):
    """Read one entity's cached pages with the model. Returns verified feats by axis."""
    # M23, SECOND PASS. This module was MISSED by the first fix, which migrated four call sites
    # and reasoned about this one in its own comments without touching it -- the exact shape of
    # standing lesson 14 (a ruling is not applied until every file of that shape is visited).
    # An adversarial audit found it live: `Tag Der Toten` (all Black Ops) and `Tag der Toten`
    # (Call of Duty Zombies) are two distinct catalogued entities on one host, and NTFS folds
    # their sanitised filenames together, so this function returned one's mined feats as the
    # other's and returned BEFORE mining, permanently starving the real entity.
    # Case matters here in a way the first measurement missed: comparing sanitised keys
    # case-SENSITIVELY found 5 colliding slots; comparing them the way the filesystem actually
    # behaves finds 12, of which 7 are case-only.
    #
    # THE WRITE PATH IS DERIVED AT WRITE TIME, NOT HERE (run #36). It used to be computed on
    # this line and used unconditionally at the bottom of the function, minutes of mining later,
    # under a ThreadPoolExecutor -- so for the whole of that window the answer to "does a
    # DIFFERENT entity already hold my natural path" was a stale one. Two pool workers holding
    # `Tag Der Toten` and `Tag der Toten` both saw the slot free, both mined, and both wrote the
    # natural path: the loser's evidence replaced the winner's, and `cachekey.load` then read
    # the survivor as a MISS for the other entity forever -- correct, but re-mined every pass.
    # See the derivation immediately above the write below.

    def _corrupt(fp):
        # SELF-HEALING: a kill mid-write once left truncated JSON here, and the raise was
        # swallowed upstream -- the entity silently vanished from every future pass while the
        # cache said it existed. A cache that will not parse is deleted and re-earned.
        silence.note("read.py:corrupt-cache")
        try:
            os.remove(fp)
        except OSError:
            _ = "silence-exempt: removing an already-gone corrupt cache needs no record"
            pass

    _doc, _fp = cachekey.load(CACHE, host, name, on_corrupt=_corrupt)
    if _doc is not None:
        return _doc

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
    # Counted where the chunks are actually made, not reconstructed afterwards from a character
    # total. Order 7265801f9528: `skipped` used to be
    # `sum(len(b) for b in text.values()) // size - len(chunks)`, which floor-divides the WHOLE
    # corpus once while the loop below splits each PAGE separately -- so the true chunk count is
    # sum(ceil(len(body)/size)) per page and the formula undercounted by one per page whose
    # length is not an exact multiple of `size` (i.e. essentially every page). Four 500-char
    # pages, every chunk filtered out, reported 0 skipped instead of 4. The error was always in
    # the flattering direction, and this is the number an operator reads to judge whether the
    # _HAS_ACTION / mention filters are too aggressive.
    generated = 0
    for title, body in text.items():
        own = _norm_q(title).lower() == _norm_q(name).lower()
        for i in range(0, len(body), size):
            generated += 1
            ch = body[i:i + size]
            if not _HAS_ACTION.search(ch):
                continue
            if own or any(k in ch.lower() for k in keys):
                density = sum(ch.lower().count(k) for k in keys)
                chunks.append((0 if own else 1, -density, title, ch))

    # RANKED, NOT CAPPED. Filtering by mention took a shared franchise page from 44 chunks to 24,
    # which is better and still ruinous: a 430,000-character page names "Metal Gear" on nearly
    # every chunk, so a mention test barely narrows it. What actually separates signal from bulk
    # is DENSITY -- how often this entity is named in this passage -- and the entity's own page,
    # which is about it by definition. Sorting by that puts the richest passages first so an
    # interrupted run has already read the part of the page that mattered most; see the comment
    # below for why nothing here truncates the tail (Hard Rule 0).
    chunks.sort()
    # Ranked by how densely the entity is named, so the richest passages are read first if this
    # is interrupted. Not truncated: a cap here decides on the entity's behalf that the rest of
    # its own pages do not count.
    chunks = [(t, c) for _, _, t, c in chunks]
    if cap_chunks:
        # `cap_chunks` NO LONGER TRUNCATES (order 4f02ea2d7ecd). It used to slice the
        # density-ranked list right here, and the partial read that produced was then written to
        # the entity's PERMANENT cache as a finished record. The "deferred, not lost" guard
        # below is `if unanswered: return out`, and a chunk removed by the cap never enters
        # `chunks` at all, so it can never be counted unanswered -- `unanswered == 0`, the
        # record lands, `read_entity` returns that cache on every later call, and `queue()`
        # never revisits the entity. The entity is filed as finished on a fraction of its own
        # pages, permanently. CLAUDE.md's Hard Rule 0 names this exact parameter in its own list
        # of the four caps the rule was written about.
        #
        # Kept rather than deleted, because the parameter is public and `--chunks` is a
        # documented flag; made inert on the shape order 97b39265457f gave
        # `corpus_db.rebuild`'s `evidence_limit`. A caller that still passes one gets the full
        # read and a note, never a silently smaller universe written down as complete.
        silence.note("read.py:cap-chunks-ignored")
    # `generated` is the exact number of chunks the loop above cut, so this subtraction is now
    # the exact number the filters threw away -- it can no longer go negative.
    skipped = generated - len(chunks)

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
        cached = _chunk_get(host, ch, name)
        if cached is not None:
            got = cached
            reused += 1
        else:
            got = _ask(c, SYSTEM, "ENTITY: " + name + "\nPAGE: " + title + "\n\n" + ch,
                       SCHEMA)
            if got is not None:
                _chunk_put(host, ch, name, (got or {}).get("feats", []))
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
           # max(0, ...) is provably unnecessary now that `skipped` counts real chunks rather
           # than a floor-divided character total; kept as a belt so a future miscount surfaces
           # as a zero rather than as a nonsensical negative in a persisted record.
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
    # THROUGH `silence.write_json`, not a hand-rolled `path + ".tmp"`: the fixed name is the
    # exact race `_chunk_put` above was fixed for individually (a pid+thread temp name), left
    # unfixed here in the migration -- two pool workers landing the same entity's evidence at
    # once could have the loser's partial file replace the winner's target. The landed verdict
    # is also no longer discarded: a denied write must not make this cache look complete when
    # it is not, so a later pass can tell the entity still needs re-caching.
    #
    # DERIVED HERE, not on entry: `write_path` asks the filesystem whether the natural slot is
    # already held by a different entity, and that answer is only usable for as long as it takes
    # to act on it. Asked on entry it was minutes stale by the time it was used (see the note at
    # the top of this function); asked here the gap is the length of one `write_json`.
    path = cachekey.write_path(CACHE, host, name)
    if not silence.write_json(path, out, indent=1, ensure_ascii=False):
        silence.note("read.py:read-entity-write-denied")
    return out


# An own page this size is a deep subject: tens of model calls, and worth them.
DEEP_CHARS = 50_000

# Below this much evidence a hostless entity is RANKED LAST -- never excluded. It was previously
# an unnamed literal `2000` that decided membership of the queue rather than position in it.
THIN_CHARS = 2_000
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
    no_page = [r for r in rows if not r.get("own", 0) and r.get("chars", 0) >= THIN_CHARS]
    # THE THIRD BUCKET, WHICH USED TO BE NO BUCKET AT ALL (Hard Rule 0, found 2026-08-24).
    #
    # This function built exactly two lists -- own-page rows, and hostless rows with at least
    # THIN_CHARS of evidence -- and returned `woven + no_page`. An entity with no own page AND
    # under THIN_CHARS of mentions therefore appeared in NEITHER list and was silently absent
    # from the queue this function's own comment calls "the full list". Measured against the
    # live queue index: 40,884 rows, of which **668 were dropped**, every one of them holding
    # real evidence text. Nothing raised, nothing logged, and the reader reported completing a
    # corpus it had never been handed.
    #
    # That is precisely the shape CLAUDE.md's Hard Rule 0 forbids: not a sample, a TRUNCATION,
    # "a smaller universe wearing the same shape as the real one". Ranking is still allowed and
    # is still what happens -- thin rows sort last, so an interrupted run has lost nothing that
    # a richer row would have given it. They are simply no longer discarded for being thin.
    thin = [r for r in rows if not r.get("own", 0) and r.get("chars", 0) < THIN_CHARS]
    have_page.sort(key=lambda r: (-r.get("own", 0), -yield_per_chunk(r)))
    # Then the names that only ever appeared inside other articles, densest mention first. These
    # are still read -- nothing here is dropped -- they are simply the thinner half of the work.
    no_page.sort(key=lambda r: (-yield_per_chunk(r), r.get("chars", 0)))
    thin.sort(key=lambda r: (-yield_per_chunk(r), r.get("chars", 0)))

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
            woven.append(deep[di])
            di += 1
        for _ in range(WEAVE):
            if li < len(light):
                woven.append(light[li])
                li += 1
    return woven + no_page + thin


QCACHE = os.path.join(HERE, "state", "read_queue_index.json")


def _load_qcache():
    try:
        with open(QCACHE, encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        silence.note("read.py:qcache-load")
        return {}


def _save_qcache(d):
    # THROUGH `silence.write_json`: the fixed `QCACHE + ".tmp"` this used to build is the same
    # single-shared-name hazard `_chunk_put` and `read_entity`'s cache write were fixed for --
    # a second writer of this file collides on the temp file itself, not just the target.
    #
    # VERDICT DELIBERATELY UNUSED. Every entry here is keyed on the evidence file's `mtime` AND
    # `size` and `queue()` re-parses the file whenever either differs, so this cache cannot go
    # stale in the read-as-fresh sense -- it can only be MISSING, and a miss costs one re-parse.
    # A failed save therefore returns the run to the behaviour it had before this memo existed:
    # slower, never wrong. `write_json` -> `replace_retry` records a denial on its own, so the
    # loss is on file in state/failures.json without a second report from here.
    try:
        silence.write_json(QCACHE, d)
    except Exception:
        silence.note("read.py:qcache-save")


# The unit separator, between an evidence path and the entity the memo below is ABOUT. Chosen
# for the same reason `_chunk_key` uses it: it cannot occur in a Windows path or in an entity
# name, so the key cannot be ambiguous about where one half ends.
_QK = chr(31)


def _queue_row(qcache, base, host, name):
    """The four ranking numbers from THIS entity's own cached evidence, or None.

    ONE HELPER, NOT FOUR SPELLINGS (`cachekey.py`'s docstring, section 3). `queue()` built the
    path inline here -- `os.path.join(base, re.sub(...)[:40], re.sub(...)[:80] + ".json")`, the
    last entity-naming copy left in src/ -- and then `os.path.exists`-tested it and read whatever
    document was there. The string it produced was byte-identical to `cachekey.natural_path`, so
    this was never a WRONG path; it was a MISSING OWNERSHIP PROOF, which is the half of M23 that
    matters at READ time.

    WHAT THAT COST, MEASURED (orders c812e8db852f, 8c3d5e9aac87). Over all 282,059 catalogued
    entity/host rows, 29 natural paths on disk are shared by two distinct catalogued names each
    -- `Magic 8 Ball`/`Magic 8-Ball`, `Ten Towns`/`Ten-Towns`, `NEMESIS`/`Nemesis`, and
    `Tag Der Toten`/`Tag der Toten`, which NTFS folds into one file. In every one of the 29 the
    document belongs to exactly one of the pair, so the other entity was admitted to the read
    queue and RANKED on its neighbour's chars/own/axes/quantities; 8 of them inherited the
    neighbour's `skip: True` memo and were dropped from the queue altogether on an empty file
    that was not theirs. `cachekey.owns` decides that by the stored `entity`, which is the only
    field that survives the sanitiser.

    AND IT NEVER LOOKED AT THE DISAMBIGUATED SIBLING, which is where `feats.evidence_for` writes
    (via `cachekey.write_path`) for every one of those 58 entities. There are no such files today
    -- so nothing is lost yet, and the first one that lands would be an entity WITH cached source
    pages that a queue whose contract is "everything with cached source pages" could not see.
    `candidate_paths` walks both spellings, natural first.

    THE MEMO KEY CARRIES THE ENTITY, for the reason `_chunk_key` above gives at length: the
    answer is about the PAIR, not about the file, and a path-only key is exactly what let one
    entity's verdict stand in for its neighbour's. `skip` is now the REASON rather than a bare
    True, because the two reasons differ in what to do next -- a document belonging to somebody
    else means try the sibling, an empty one means this entity has nothing to rank.
    """
    for path in cachekey.candidate_paths(base, host, name):
        if not os.path.exists(path):
            continue
        # THE CACHE FILE IS OPENED ONCE PER LIFETIME, NOT ONCE PER RUN.
        #
        # These records carry the full cleaned page text -- 497 million characters across the
        # tree -- and the queue only needs four numbers out of each. Parsing all of it at the
        # head of every run took longer than the run's first hour of useful work, and from
        # outside it looked exactly like a reader that had started and gone quiet. Keyed on
        # mtime, so a record the roll has just rewritten is re-read and every other one is not.
        try:
            st = os.stat(path)
        except OSError:
            silence.note("read.py:queue-stat")
            continue
        key = path + _QK + name
        memo = qcache.get(key)
        if memo and memo.get("mtime") == st.st_mtime and memo.get("size") == st.st_size:
            if memo.get("skip") == "notmine":
                continue                     # the sibling may still hold this entity's evidence
            if memo.get("skip"):
                return None
            return memo["row"]
        try:
            with open(path, encoding="utf-8") as fh:
                ev = json.load(fh)
        except Exception:
            silence.note("read.py:queue-evidence-read")
            continue
        if not cachekey.owns(ev, name):
            qcache[key] = {"mtime": st.st_mtime, "size": st.st_size, "skip": "notmine"}
            continue
        if not ev.get("text"):
            qcache[key] = {"mtime": st.st_mtime, "size": st.st_size, "skip": "empty"}
            return None
        # An entity's OWN page is the part of its evidence that is actually about it. The rest
        # is whatever shared index its name appeared in, and that is where the cost hides.
        own = 0
        for t, body in (ev.get("text") or {}).items():
            if t.strip().lower() == name.strip().lower():
                own = len(body)
                break
        row = {"chars": ev.get("chars_read", 0), "own": own,
               "axes": len({f.get("axis") for f in ev.get("feats", [])}),
               "quantities": len(ev.get("quantities") or [])}
        qcache[key] = {"mtime": st.st_mtime, "size": st.st_size, "row": row}
        return row
    return None


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
    # Self-healing, like every other cache read in this file. This is a multi-hour pass and the
    # host map has three writers; an unguarded load meant a single racing write could end the
    # whole run with a JSONDecodeError and no note. An unreadable host map is a real fault, so
    # it is recorded rather than shrugged off -- but it must not be able to discard the pass.
    #
    # FAIL CLOSED, AND LOUD (run #36). `except: hosts = {}` did the exact thing the sentence
    # above forbids. With an empty map every record fails the `if not h` below, the queue comes
    # back EMPTY, and `run()` prints "0 entries with pages", finishes in a second and exits 0 --
    # a total loss of the library's main throughput wearing the face of "there was nothing left
    # to read". The retry is what the original guard was actually reaching for: all three
    # writers of this file land it through `silence.replace_retry`, so a racing write is
    # unreadable for milliseconds, not seconds. Anything that outlasts four attempts is a real
    # fault, and a reader that cannot tell which entities have hosts has no business reporting a
    # completed pass over none of them.
    hosts = None
    for _attempt in range(4):
        try:
            with open(FF.HOSTS, encoding="utf-8") as _hf:
                hosts = json.load(_hf)
            break
        except Exception:
            silence.note("read.py:hosts-unreadable")
            hosts = None
            if _attempt < 3:
                time.sleep(0.3 * (_attempt + 1))
    if not isinstance(hosts, dict) or not hosts:
        # An EMPTY map is refused for the same reason an unreadable one is: it produces an empty
        # queue, and an empty queue is reported as a finished pass. If this is a fresh tree, the
        # remedy is `python src/feats.py --hosts` (resolve_hosts), not a run over nothing.
        raise SystemExit(
            "REFUSING TO READ: the host map (%s) did not load as a non-empty object after 4 "
            "attempts. Every record's host is looked up in it, so an empty map empties the "
            "whole read queue and this pass would report itself finished having read nothing. "
            "Restore or rebuild the file (src/feats.py --hosts) and re-run." % FF.HOSTS)
    qcache = _load_qcache()
    # THE MEMO KEY GAINED THE ENTITY (orders c812e8db852f / 8c3d5e9aac87), so every entry written
    # under the old path-only key is unreachable. They are DROPPED rather than left in place --
    # `_chunk_key`'s migration could leave its stale entries alone because each is its own small
    # file, whereas this cache is one 61 MB object rewritten whole on every pass, and keeping
    # keys nothing can ever hit again would double it forever. Nothing is lost: every entry here
    # is a memo of four numbers that are still on disk. The cost is one slow pass that re-reads
    # each evidence file once, which is what this memo cost to build in the first place.
    qcache = {k: v for k, v in qcache.items() if _QK in k}
    rows = []
    for _, r in recs:
        h = hosts.get(r["source"])
        if not h:
            continue
        for e in r["entries"]:
            if not all_entries and not (e.get("category") or "").startswith("Persons"):
                continue
            row = _queue_row(qcache, FF.CACHE, h, e["name"])
            if row is None:
                continue
            rows.append(dict(row, name=e["name"], host=h, source=r["source"],
                             category=(e.get("category") or "?")[:20]))
    _save_qcache(qcache)
    return priority(rows)


def run(limit=None, workers=2, cap_chunks=None, all_entries=True):
    c = config()
    todo = queue(all_entries=all_entries)
    if limit:
        todo = todo[:limit]

    done = {"n": 0, "feats": 0, "fab": 0, "chunks": 0, "skipped": 0, "unanswered": 0,
             "errored": 0, "last_error": None}
    lock = threading.Lock()
    t0 = time.time()

    def work(r):
        try:
            out = read_entity(c, r["host"], r["name"], cap_chunks=cap_chunks)
        except Exception:
            silence.note("read.py:work-read-entity")
            out = None
        with lock:
            done["n"] += 1
            # A CRASHED ENTITY IS NOT A "NOTHING TO REPORT" ENTITY (order 337233a185f2).
            # `out is None` on this path means read_entity RAISED -- distinct from every other
            # `out` falsy case (there is none; read_entity always returns a dict) -- and until
            # now nothing here told the difference between "raised" and "read cleanly". The
            # silence ledger records the CLASS; this records the COUNT and an instance to
            # reproduce from, on the same progress line and closing line as every other outcome.
            if out is None:
                done["errored"] += 1
                done["last_error"] = "%s / %s" % (r.get("host"), r.get("name"))
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
                      "(%d to GPU, %d UNANSWERED, not cached, %d skipped, %d ERRORED)  "
                      "eta %.1fh%s"
                      % (n, len(todo), crate, done["feats"], done["fab"], done["chunks"],
                         CHUNK_BUDGET, _FELL_BACK[0], done["unanswered"], done["skipped"],
                         done["errored"], left / max(crate, 1e-9) / 3600, dead), flush=True)

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
                import json as _j
                import os as _o
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
    # SAYS SO WHEN A CAP WAS ASKED FOR AND REFUSED (order 4f02ea2d7ecd). Printing the requested
    # number alone would tell the operator the run is capped when `read_entity` now ignores it,
    # and a banner that disagrees with the run is this project's oldest failure shape.
    chunks_note = ("uncapped (--chunks %s ignored, Hard Rule 0)" % cap_chunks
                   if cap_chunks else "uncapped")
    print("read: %d entries with pages, %d workers, chunks %s"
          % (len(todo), workers, chunks_note), flush=True)
    with ThreadPoolExecutor(max_workers=workers) as ex:
        list(ex.map(work, todo))
    err_note = ("  0 entities errored" if not done["errored"] else
                "  %d entities ERRORED (last: %s -- see silence ledger read.py:work-read-entity)"
                % (done["errored"], done["last_error"]))
    print("done in %.2fh  %d feats kept, %d fabrications dropped, %d chunks skipped%s"
          % ((time.time() - t0) / 3600, done["feats"], done["fab"], done["skipped"], err_note))


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
    ap = argparse.ArgumentParser()
    ap.add_argument("--run", action="store_true")
    ap.add_argument("--limit", type=int)
    ap.add_argument("--workers", default="auto",
                    help="number, or 'auto' to match the count of usable remote buckets")
    ap.add_argument("--chunks", type=int, default=None,
                    help="INERT (order 4f02ea2d7ecd): every chunk of every page is read whatever "
                         "you pass. A capped read used to be written to the entity's permanent "
                         "cache as a finished record. Accepted so existing command lines still "
                         "run; a value logs read.py:cap-chunks-ignored")
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
        # NOT SLICED (order a84c002fb0e3, Hard Rule 0). This used to print `out["feats"][:12]`
        # with no marker, so Goku's 241 feats came back as twelve rows and nothing on the page
        # said the other 229 were rows you could have seen. `--one` is the interactive
        # inspection path -- it exists precisely so a person can look at everything that was
        # mined for one entity -- and the volume is bounded by the single entity, so there is
        # nothing here worth capping and nothing to reverse a cap with.
        for f in out["feats"]:
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
