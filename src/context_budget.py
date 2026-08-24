"""CONTEXT BUDGET — the cap the code did not choose, and the refusal that replaces it.

THE BUG THIS EXISTS FOR (m46/m52, found 2026-08-24, never fired because generation has not run
at volume). A feats block's prompt was measured at **41,469 characters** -- `entities_json`
20,545 + `prompts/system_style.txt` 18,112 + `prompts/feats_prompt.txt` 2,812 -- and was being
sent into a window of `num_ctx: 6144`. At any plausible tokenizer ratio that is between 1.5x
and 1.9x the window. `generate.py` was careful about the OUTPUT ceiling (`num_predict: -1`,
with a comment about silent truncation being what Hard Rule 0 forbids) and nothing at all
checked the INPUT against the same window, which is shared between the two.

Ollama does not refuse an over-long prompt. It truncates it and answers anyway. And the feats
coverage check (`generate._covered`) verifies only that an entity's NAME appears in the
returned text -- so a block whose deed list was cut in half would still pass, and be written to
`catalog.json` as a finished chapter. That is a Hard Rule 0 truncation arriving from the
runtime instead of from a `[:n]`, which is worse, because there is no slice in the source for a
reader to find.

THREE CHANGES, AND THE ORDER MATTERS

  1. The budget is DERIVED, not declared. `FEATS_BLOCK_CHARS = 20000` was a constant with no
     arithmetic relationship to `num_ctx`; raising the window did not widen it and lowering the
     window did not protect it. `content_budget_chars()` computes what actually fits from the
     window, the measured scaffolding, and an explicit output reserve. Raise `num_ctx` later
     and the blocks widen on their own.

  2. Feats jobs stop carrying the chapter-only half of the system prompt. `system_style.txt` is
     two documents in one file: lines 1-102 are ground rules and voice (6,964 chars, true of
     every job), lines 103-245 are THE ENTRY TEMPLATE (11,147 chars) -- the per-entry shape,
     the Four Hands marginalia, and The Instrument. A feats chapter writes none of those, and
     `prompts/feats_prompt.txt` explicitly FORBIDS the scoring The Instrument describes. Eleven
     thousand characters of instruction telling the model to do something the user prompt then
     forbids is worse than wasted -- it is contradictory. Splitting it returns ~3,700 tokens.

  3. Overflow becomes a LOUD failure. `assert_fits()` raises `ContextOverflow` naming the
     numbers. A job that cannot fit is now a recorded failure that a person can act on, which
     is the whole discipline this project keeps arriving at: the loss must not be filed as a
     result.

ON THE TOKEN ESTIMATE, HONESTLY. There is no tokenizer here -- `ollama` exposes no tokenize
endpoint and installing one is a dependency this kit does not need. So the ratio is measured in
characters and deliberately PESSIMISTIC: 3.0 characters per token, where ordinary English runs
nearer 4 and JSON with heavy punctuation runs nearer 3.2. Being wrong in this direction costs
smaller blocks and more calls. Being wrong in the other direction costs silently truncated
evidence, which is the thing the whole project exists to refuse. An attempt to measure the true
ratio against the live daemon on 2026-08-24 timed out twice under GPU contention; if that
becomes cheap later, `CHARS_PER_TOKEN` is the one number to re-measure.
"""
import os

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PROMPTS = os.path.join(HERE, "prompts")

# Pessimistic on purpose -- see the header. Fewer chars per token => a larger token estimate
# => a smaller content budget => an earlier refusal.
CHARS_PER_TOKEN = 3.0

# Room the model needs to WRITE its answer, inside the same window as the prompt. A feats block
# reports several entities' deeds in prose; a chapter block writes full template entries.
DEFAULT_RESERVE_TOKENS = 1024
CHAPTER_RESERVE_TOKENS = 2048

# The line THE ENTRY TEMPLATE begins on in prompts/system_style.txt (1-indexed). Located by its
# heading rather than hardcoded, so editing the prompt above it cannot silently mis-split.
_TEMPLATE_HEADING = "THE ENTRY TEMPLATE"


class ContextOverflow(RuntimeError):
    """A prompt that does not fit its window. Raised rather than sent and truncated."""


def estimate_tokens(text):
    """Characters -> a deliberately high token estimate."""
    return int(len(text or "") / CHARS_PER_TOKEN + 0.999)


def split_system_prompt(system_text):
    """-> (voice_only, full). The voice half applies to every job; the template half does not.

    Split on the heading, never on a line number: `system_style.txt` is the one file the owner
    is invited to edit freely for tone, and a hardcoded offset would start cutting mid-sentence
    the first time a paragraph was added above it. If the heading is absent the split is a
    no-op and both halves are the whole file -- degrade to today's behaviour rather than guess.
    """
    text = system_text or ""
    lines = text.split("\n")
    for i, line in enumerate(lines):
        if line.strip().startswith(_TEMPLATE_HEADING):
            return "\n".join(lines[:i]).rstrip(), text
    return text, text


def system_for(job_type, system_text):
    """The system prompt this job type actually needs.

    Feats jobs get voice and ground rules only. Everything else gets the whole document.
    """
    voice, full = split_system_prompt(system_text)
    return voice if job_type == "feats" else full


def reserve_for(job_type):
    return DEFAULT_RESERVE_TOKENS if job_type == "feats" else CHAPTER_RESERVE_TOKENS


def window(cfg):
    return int((cfg or {}).get("num_ctx", 8192))


def content_budget_chars(cfg, scaffold_chars, job_type="feats"):
    """How many characters of CONTENT may ride along with this scaffolding.

    Returns a number that can be ZERO OR NEGATIVE, and callers must treat that as "this cannot
    be done at this window" rather than clamping it to something small and carrying on. A
    clamped budget is how a cap gets reintroduced wearing the shape of a safety margin.
    """
    usable = window(cfg) - reserve_for(job_type) - estimate_tokens("x" * int(scaffold_chars))
    return int(usable * CHARS_PER_TOKEN)


def measure(cfg, system_prompt, user_prompt, job_type="feats"):
    """The full arithmetic, as data. Every number the failure message would need."""
    sys_t = estimate_tokens(system_prompt)
    usr_t = estimate_tokens(user_prompt)
    res = reserve_for(job_type)
    win = window(cfg)
    return {"window": win, "system_chars": len(system_prompt or ""),
            "user_chars": len(user_prompt or ""), "system_tokens": sys_t,
            "user_tokens": usr_t, "reserve_tokens": res,
            "needed_tokens": sys_t + usr_t + res,
            "headroom_tokens": win - (sys_t + usr_t + res),
            "chars_per_token": CHARS_PER_TOKEN, "job_type": job_type}


def fits(cfg, system_prompt, user_prompt, job_type="feats"):
    m = measure(cfg, system_prompt, user_prompt, job_type)
    return m["headroom_tokens"] >= 0, m


def assert_fits(cfg, system_prompt, user_prompt, job_type="feats", label=""):
    """Refuse to send a prompt that would be silently truncated.

    The alternative is not "it works anyway" -- it is a chapter that is missing evidence nobody
    can see is missing, filed as complete. A raised error is recoverable; that is not.
    """
    ok, m = fits(cfg, system_prompt, user_prompt, job_type)
    if ok:
        return m
    raise ContextOverflow(
        f"{label or m['job_type']}: prompt needs ~{m['needed_tokens']} tokens "
        f"(system {m['system_tokens']} + user {m['user_tokens']} + reserve "
        f"{m['reserve_tokens']}) but num_ctx is {m['window']} — over by "
        f"{-m['headroom_tokens']} tokens. Ollama would TRUNCATE this prompt and answer "
        f"anyway, and the coverage check cannot see a shortened deed list. Lower the block "
        f"budget, trim the system prompt for this job type, or raise num_ctx.")


def scaffold_chars(system_prompt, template_text):
    """Everything in the prompt that is not the content itself."""
    return len(system_prompt or "") + len(template_text or "")


# TWO MEASURED CORRECTIONS, both found by checking the arithmetic against real rendered jobs
# rather than trusting it (2026-08-24, Warhammer 40,000, 331 blocks).
#
# JOB_OVERHEAD_CHARS: `feats_prompt.txt` is a TEMPLATE, and the rendered prompt carries the
# source name, the chapter label, the page span, the ceiling entity and the rest of the job
# context on top of it. Measured across all 331 blocks: min 314, median 1,193, max 1,536. The
# constant is the max rounded up, because a budget that is right on average is wrong for
# whichever block happens to be largest -- and that block is the one that would truncate.
JOB_OVERHEAD_CHARS = 2000

# METADATA_INFLATION: `pack_feats` measures a block with `cost()`, which weighs ONLY each
# entity's `feats` list. The emitted block also carries entity, shelfmark, magnitude, topic,
# pages, feat_count and axis_counts per entity, none of it counted. Measured earlier the same
# day: blocks packed to a nominal 20,000 emitted a median of 20,464 and a max of 21,993 -- about
# 10%. Budgeted at 20% so a source with many small entities (more metadata per feat, the worst
# case for this ratio) still fits.
METADATA_INFLATION = 1.20


def feats_block_budget(cfg, system_text=None, template_text=None):
    """Characters of feats JSON one call may carry, derived from the live window.

    Reads the prompt files when not given them, so a caller that only has `cfg` still gets the
    real measurement rather than a constant that drifted away from the files years ago.

    The number returned is what `pack_feats`'s `cost()` may report -- NOT the size of the
    emitted block, which is larger by the two corrections above.
    """
    if system_text is None:
        try:
            with open(os.path.join(PROMPTS, "system_style.txt"), encoding="utf-8") as f:
                system_text = f.read()
        except Exception:
            system_text = ""
    if template_text is None:
        try:
            with open(os.path.join(PROMPTS, "feats_prompt.txt"), encoding="utf-8") as f:
                template_text = f.read()
        except Exception:
            template_text = ""
    sys_used = system_for("feats", system_text)
    room = content_budget_chars(
        cfg, scaffold_chars(sys_used, template_text) + JOB_OVERHEAD_CHARS, "feats")
    return int(room / METADATA_INFLATION)


def report(cfg):
    """What fits right now, for a human. Used by health/preflight and by the ledgers."""
    try:
        with open(os.path.join(PROMPTS, "system_style.txt"), encoding="utf-8") as f:
            sysd = f.read()
    except Exception:
        sysd = ""
    try:
        with open(os.path.join(PROMPTS, "feats_prompt.txt"), encoding="utf-8") as f:
            ftpl = f.read()
    except Exception:
        ftpl = ""
    voice, full = split_system_prompt(sysd)
    return {"num_ctx": window(cfg),
            "system_full_chars": len(full), "system_voice_chars": len(voice),
            "template_only_chars": len(full) - len(voice),
            "feats_prompt_chars": len(ftpl),
            "feats_block_budget_chars": feats_block_budget(cfg, sysd, ftpl),
            "chapter_scaffold_chars": len(full)}
