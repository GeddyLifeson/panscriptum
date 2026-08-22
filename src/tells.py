#!/usr/bin/env python3
"""
TELLS — the phrasings that mark text as machine-written, in one place.

WHY ONE FILE
------------
This list has to govern two things at once: the instruction given to the model that writes the
entries, and the audit that checks what it wrote. Kept in two places they drift, and a phrase
banned in the prompt but absent from the checker goes unnoticed for fifty thousand entries. So the
list lives here, the prompt section is GENERATED from it, and the audit imports it.

WHAT COUNTS AS A TELL
---------------------
Three kinds, and they fail differently.

  LEXICAL     single words that machine prose reaches for far past their natural rate: delve,
              tapestry, myriad, meticulous, seamless, vibrant, testament, realm, boasts.
  STRUCTURAL  sentence shapes used as a reveal: "not merely X but Y", "It's not that X, it's Y",
              rule-of-three lists, "not only ... but also".
  DISCOURSE   connective furniture that announces the machine: "That said", "It is worth noting",
              "In conclusion", "Ultimately", "Moreover" as a paragraph opener.

A word on the lexical set: none of these words is bad. Delve is a fine English word. The problem
is frequency — machine prose uses them at many times the rate a human writer would, so their
presence in quantity is the signature. The audit therefore reports RATES, not mere presence, and
a single "vibrant" in fifty thousand entries is not a defect.
"""
import re
import os

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


# ------------------------------------------------------------------ lexical
LEXICAL = [
    "delve", "delving", "tapestry", "myriad", "plethora", "meticulous", "meticulously",
    "seamless", "seamlessly", "vibrant", "bustling", "nestled", "boasts", "boasting",
    "testament", "realm of", "landscape of", "journey of", "unlock", "unleash",
    "leverage", "robust", "holistic", "multifaceted", "nuanced", "profound",
    "resonate", "resonates", "captivating", "compelling", "intricate", "enigmatic",
    "formidable", "renowned", "iconic", "pivotal", "cornerstone", "hallmark",
    "epitome", "quintessential", "indelible", "unwavering", "steeped in",
    "underscore", "underscores", "showcase", "showcases", "elevate", "elevates",
    "navigate the", "embark", "foster", "cultivate", "harness", "myriad of",
    "treasure trove", "beacon", "crucible", "watershed", "paradigm",
]

# Fiction and encyclopedia furniture: the fantasy-flavoured equivalents.
LEXICAL_FICTION = [
    "shrouded in mystery", "shrouded in", "whispered in hushed", "hushed tones",
    "time immemorial", "since time began", "echoes of", "whispers of",
    "the very fabric", "torn asunder", "ancient and terrible", "long forgotten",
    "lost to history", "veil of", "tapestry of", "annals of", "eons past",
    "primordial darkness", "unspeakable", "eldritch horror", "dark and terrible",
    "looms over", "looms large", "walls thick with", "iron hand", "iron grip",
    "scarred by", "haunted by", "born of", "forged in", "baptised in", "baptized in",
]

# ------------------------------------------------------------------ structural
STRUCTURAL = {
    "not merely X but Y": r"\bnot merely\b|\bnot simply\b|\bnot just\b.{0,40}\bbut\b",
    "it's not X, it's Y": r"\b(?:is|was|are|were)n['’]?t (?:a |an |the )?\w+[,;] (?:it|they|which) (?:is|was|are|were)\b",
    "X is not Y; it is Z": r"\bis not (?:a |an |the )?\w+[;,] (?:it|which) is\b",
    "not only ... but also": r"\bnot only\b.{0,60}\bbut also\b",
    "more than just": r"\bmore than (?:just|merely|simply)\b",
    "stands as a testament": r"stands? as a (?:testament|monument|reminder)",
    "serves as a": r"\bserves? as a\b",
    "plays a X role": r"\bplays? a (?:crucial|vital|pivotal|key|significant|central) role\b",
    "at its core / heart": r"\bat (?:its|the) (?:core|heart)\b",
    "rule of three": r"\b\w+, \w+,? and \w+ (?:alike|all|together)\b",
    "whether you're": r"\bwhether (?:you|one)['’]?(?:re| are)\b",
    "from X to Y": r"\bfrom \w+ to \w+, \b",
    "little is known save": r"little is known (?:of|about) .{0,40}(?:save|except|beyond)\b",
    "what survives": r"\bwhat (?:survives|remains) of\b",
    "whatever else may be said": r"whatever else (?:may|might) be said\b",
    "here then is": r"\bhere,? then,? (?:is|lies)\b",
    "remains to this day": r"remains?,? to this day\b",
    "the record notes": r"the record (?:notes|shows|tells)\b",
    "one thing is certain": r"one thing (?:is|remains) certain\b",
    "no small feat": r"\bno small (?:feat|matter|thing)\b",
    "speaks volumes": r"\bspeaks volumes\b",
    "sheds light": r"\bshed(?:s|ding)? light on\b",
    "paints a picture": r"\bpaints? a .{0,12}picture\b",
    "weaves together": r"\bweav(?:es|ing) together\b",
    "stands the test of time": r"stands? the test of time\b",
    "against the backdrop": r"against the backdrop\b",
    "in stark contrast": r"in stark contrast\b",
    "a far cry from": r"\ba far cry from\b",
    "double-edged sword": r"double[- ]edged sword\b",
    "interplay between": r"\binterplay between\b",
    "which is the point": r"which is (?:the|precisely the|exactly the) point\b",
}

# ------------------------------------------------------------------ discourse
DISCOURSE = {
    "that said": r"^\s*That (?:said|being said)\b",
    "it is worth noting": r"\bit is worth (?:noting|saying|remarking|mentioning)\b",
    "worth flagging": r"\bworth (?:flagging|highlighting|underlining)\b",
    "importantly": r"^\s*(?:More |Most )?[Ii]mportantly,",
    "in conclusion": r"^\s*(?:In conclusion|In summary|To summarise|To summarize|Overall|Ultimately)\b",
    "moreover / furthermore": r"^\s*(?:Moreover|Furthermore|Additionally|In addition),",
    "firstly / secondly": r"^\s*(?:Firstly|Secondly|Thirdly|Lastly),",
    "here's the thing": r"\bhere['’]?s the thing\b",
    "the truth is": r"^\s*The truth is\b",
    "make no mistake": r"\bmake no mistake\b",
    "at the end of the day": r"at the end of the day\b",
    "needless to say": r"\bneedless to say\b",
    "to be clear": r"^\s*To be clear\b",
    "in essence": r"^\s*In essence\b",
    "simply put": r"^\s*Simply put\b",
}

ALL_PATTERNS = {**STRUCTURAL, **DISCOURSE}

# Discourse markers were anchored to ^ and so were invisible mid-paragraph: in
# "...only whispers. That said, the record notes..." the tell went undetected, which is exactly
# where it actually occurs. The anchor is now a sentence boundary OR a line start.
_SENTENCE_START = r"(?:^|(?<=[.!?])\s+)"


def _anchor(pat):
    return _SENTENCE_START + pat[4:] if pat.startswith(r"^\s*") else pat


_COMPILED = {k: re.compile(_anchor(v), re.I | re.M) for k, v in ALL_PATTERNS.items()}
_LEX = {w: re.compile(r"\b" + re.escape(w) + r"\b", re.I) for w in LEXICAL + LEXICAL_FICTION}

# The escape-mangling guard: a pattern that arrives with a control character matches nothing and
# reports clean, which is the worst failure a checker can have.
for _n, _p in list(_COMPILED.items()) + list(_LEX.items()):
    if any(ord(c) < 32 and c not in "\n\t" for c in _p.pattern):
        raise SystemExit(f"tells.py: pattern {_n!r} contains a control character")


def scan(text):
    """Every tell in one passage, with counts."""
    hits = {}
    for name, pat in _COMPILED.items():
        c = len(pat.findall(text))
        if c:
            hits[name] = c
    for word, pat in _LEX.items():
        c = len(pat.findall(text))
        if c:
            hits[f"word: {word}"] = c
    return hits


def prompt_section(width=96):
    """The banned-phrase block for the style prompt, GENERATED from this list.

    Generated rather than transcribed so the instruction and the audit cannot disagree. Editing
    the lists above changes both at once.
    """
    lines = [
        "7. NO MACHINE TELLS. The phrasings below mark text as machine-written. Do not use them,",
        "   and do not use close variants of them. This is not a style preference; a corpus of",
        "   fifty thousand entries built on these reads as one voice with a small vocabulary.",
        "",
        "   Never these words and phrases:",
    ]

    def wrap(items, indent="     "):
        out, cur = [], indent
        for it in items:
            add = it + ", "
            if len(cur) + len(add) > width:
                out.append(cur.rstrip())
                cur = indent
            cur += add
        if cur.strip():
            out.append(cur.rstrip().rstrip(","))
        return out

    lines += wrap(sorted(LEXICAL))
    lines += ["", "   Never this fantasy-encyclopedia furniture:"]
    lines += wrap(sorted(LEXICAL_FICTION))
    lines += ["", "   Never these sentence shapes:"]
    lines += wrap(sorted(STRUCTURAL))
    lines += ["", "   Never these discourse markers, and never open a paragraph with one:"]
    lines += wrap(sorted(DISCOURSE))
    lines += [
        "",
        "   Two further rules that matter more than the lists:",
        "   - Do not build a sentence as a reveal. State the thing.",
        "   - Do not end an entry on a turn. Most entries should stop when the facts stop.",
    ]
    return "\n".join(lines)


if __name__ == "__main__":
    import sys
    if "--prompt" in sys.argv:
        print(prompt_section())
    else:
        print(f"lexical tells          : {len(LEXICAL)}")
        print(f"fiction furniture      : {len(LEXICAL_FICTION)}")
        print(f"structural shapes      : {len(STRUCTURAL)}")
        print(f"discourse markers      : {len(DISCOURSE)}")
        print(f"total patterns         : {len(LEXICAL)+len(LEXICAL_FICTION)+len(ALL_PATTERNS)}")
        demo = ("It's not merely a fortress, it is a testament to the meticulous craft of a "
                "bygone age. That said, little is known of its builders save whispers. "
                "Ultimately, the record notes that it endures.")
        print("\nself-check on a deliberately bad passage:")
        for k, v in sorted(scan(demo).items()):
            print(f"   {v}  {k}")
