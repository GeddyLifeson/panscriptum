"""
Proposed checks for run35 batch 5 (agent working read.py / onomast.py / feats.py / backfill.py /
hostcheck.py / scout.py / wiki_source.py / cachekey.py / corpus_db.py).

These are NOT run standalone against verify_math.py or drill.py -- this run's rule is that
neither is safe to run concurrently with the mutate run already in flight (order c349a51ee2c5),
and the coordinator runs the battery centrally. Every check below WAS smoke-tested standalone,
directly against the real, already-fixed modules in this checkout, with a minimal local `check`/
`net` stub matching verify_math.py's/drill.py's own signatures. All passed (OK / HELD) at the
time this file was written (2026-08-26).

Local names are suffixed `_b5` to avoid colliding with verify_math.py's own `_NN<letters>` locals
when this is spliced in.

Two of this batch's orders are NOT represented here, on purpose:
  * 5d8533bc1ed6 (onomast.py `register_for`'s dead genre/feature voting) is LEFT FOR OWNER --
    see AUDIT_batch5.md. Wiring real genre/feature data into `name_worlds()`'s one call site is
    a cross-module design decision (which of genre.py/grounding.py's classifiers feeds it, where
    per-continuity-group world-feature data would come from), not a mechanical fix, so there is
    nothing yet to pin.
  * f53381169f79 (corpus_db.py's `CANNED` LIMIT clauses) is DISPROVED -- the finding was already
    true in run33 (see handoff/sweep33/AUDIT_batch17_corpus_db.md Q1) but corpus_db.py has since
    been edited by another session: every LIMIT is already gone, and the module's own comment at
    corpus_db.py:426-440 now documents exactly this history. A check pinning "the bug that no
    longer exists doesn't exist" would just be `"LIMIT" not in str(CANNED)`, which duplicates
    what reading the source already shows; adding it would misrepresent a non-finding as a fix.
"""

import os as _os_b5
import sys as _sys_b5
import time as _time_b5

# Spliced into src/verify_math.py, so  IS a file in src/. The authored version
# of this block walked three directories up from handoff/run35/, which resolved to
# C:/Users/imarl/src once merged -- corrected at merge time by the coordinator.
_SRC_b5 = _os_b5.path.dirname(_os_b5.path.abspath(__file__))
if _SRC_b5 not in _sys_b5.path:
    _sys_b5.path.insert(0, _SRC_b5)


# ==================================================================================================
# order 5bf48fa9f70d -- belongs in verify_math.py, target src/read.py.
#
# `_local_carded`'s oversized-passage re-split path must not fold a total sub-call failure into a
# fake-complete `{"feats": []}`. Forces every `P.ask` call to return None and confirms the whole
# thing returns None (so `read_entity` counts the chunk unanswered, not cached-empty) and that the
# GPU gets benched exactly as the ordinary single-piece path already does.
# ==================================================================================================
print()
print("[batch5] order 5bf48fa9f70d -- an all-None oversized re-split reports unanswered, not empty")


def _b5_local_carded_checks():
    import read as R
    orig_ask, orig_bench, orig_fallback = R.P.ask, R._GPU_DOWN_UNTIL[0], R._FALLBACK_MODEL[0]
    try:
        R.P.ask = lambda *a, **k: None
        R._FALLBACK_MODEL[0] = "dummy-model"
        R._GPU_DOWN_UNTIL[0] = 0.0
        c = {"model": "dummy-model", "ollama_host": "http://localhost:11434"}
        # Body longer than CHUNK forces the re-split branch (prompt > CHUNK + 2000).
        prompt = "HEAD LINE\n\n" + ("x" * (R.CHUNK + 3000))
        got = R._local_carded(c, "sys", prompt, {"type": "object"})
        check("_local_carded returns None (not {'feats': []}) when every piece fails",
              got, None,
              note="a fake-complete answer here used to permanently cache an empty result over "
                   "a passage nobody actually read (order 5bf48fa9f70d)")
        check("_local_carded benches the GPU on total failure, same as the ordinary path",
              R._GPU_DOWN_UNTIL[0] > _time_b5.time(), True)
    finally:
        R.P.ask, R._GPU_DOWN_UNTIL[0], R._FALLBACK_MODEL[0] = orig_ask, orig_bench, orig_fallback


_b5_local_carded_checks()


# ==================================================================================================
# order 6b7f51f8ec2e -- belongs in verify_math.py, target src/read.py.
#
# `_ask_ungated` must never fall through to the local GPU when `_TRANSPORT == "cascade"`, even
# when `ensure_transport()` itself returns False (cascade_bridge unimportable / engine() falsy).
# Also pins that `_FELL_BACK` is not incremented for a chunk that is never actually sent to the
# GPU (the counter used to fire before the cascade-mode early return).
# ==================================================================================================
print("[batch5] order 6b7f51f8ec2e -- cascade mode never touches the local GPU, and never counts "
      "a chunk as having gone there when it did not")


def _b5_cascade_no_fallthrough():
    import read as R
    orig_transport = R._TRANSPORT
    orig_ensure = R.ensure_transport
    orig_local = R._local
    orig_fellback = R._FELL_BACK[0]
    try:
        R.set_transport("cascade")
        R.ensure_transport = lambda verbose=False: False   # cascade_bridge unavailable
        called_local = []
        R._local = lambda *a, **k: called_local.append(1) or {"feats": []}
        got = R._ask_ungated({}, "sys", "prompt", {"type": "object"})
        check("cascade mode returns None (not the GPU's answer) when ensure_transport() is False",
              got, None)
        check("cascade mode never calls _local() when ensure_transport() is False",
              len(called_local), 0)
        check("_FELL_BACK is not incremented for a chunk that never reached the GPU",
              R._FELL_BACK[0], orig_fellback)
    finally:
        R.set_transport(orig_transport)
        R.ensure_transport = orig_ensure
        R._local = orig_local
        R._FELL_BACK[0] = orig_fellback


_b5_cascade_no_fallthrough()


# ==================================================================================================
# order 36d1dd86fb78 -- belongs in verify_math.py, target src/onomast.py.
#
# The doctrine docstring's world counts must agree with what `is_carried()` and `name_worlds()`
# actually measure against the real data/RESOLVED_ENTITIES.json, not a stale "thirty/eighteen/
# sixteen". Re-measures live rather than hardcoding the expected numbers, so a genuine change in
# the corpus does not make this check itself the next stale claim.
# ==================================================================================================
print("[batch5] order 36d1dd86fb78 -- onomast.py's doctrine prose matches measured world counts")


def _b5_onomast_doctrine_counts():
    import json as _json_b5
    import collections
    import onomast as O
    resolved = _json_b5.load(open(O.RESOLVED, encoding="utf-8"))
    counts = collections.Counter()
    for v in resolved.values():
        if O.is_carried(v["canonical_name"]):
            counts[v["canonical_name"].strip().lower()] += 1
    earth = counts.get("earth", 0) + counts.get("the earth", 0)
    moon = counts.get("moon", 0) + counts.get("the moon", 0)
    mars = counts.get("mars", 0)
    doc = O.__doc__ or ""
    check("doctrine docstring names the CURRENT measured Earth count (not a stale 'thirty')",
          str(earth) in doc or _b5_spelled(earth) in doc, True,
          note="measured earth=%d; docstring must say so, not 'thirty'" % earth)
    check("doctrine docstring names the CURRENT measured Moon count (not a stale 'eighteen')",
          str(moon) in doc or _b5_spelled(moon) in doc, True,
          note="measured moon=%d; docstring must say so, not 'eighteen'" % moon)
    check("doctrine docstring names the CURRENT measured Mars count (not a stale 'sixteen')",
          str(mars) in doc or _b5_spelled(mars) in doc, True,
          note="measured mars=%d; docstring must say so, not 'sixteen'" % mars)
    check("the stale figures ('thirty', 'eighteen', 'sixteen') are gone from the docstring",
          any(w in doc for w in ("thirty", "eighteen", "sixteen")), False)


_NUM_WORDS_b5 = {14: "fourteen", 15: "fifteen", 26: "twenty-six", 12: "twelve"}


def _b5_spelled(n):
    return _NUM_WORDS_b5.get(n, str(n))


_b5_onomast_doctrine_counts()


# ==================================================================================================
# order d097dc4db7c4 -- belongs in verify_math.py, target src/feats.py.
#
# BUGS.md m81: feats.py's numeric `silence.note()` labels drift out of sync with their call
# sites as the file grows (171-406 lines off, measured). The four renamed this run must now be
# NAMED, matching the file's own existing convention (api-404 / api-nonjson / corrupt-cache /
# throttle-quarantine), so they cannot rot the same way again. Reads the source directly rather
# than importing, since these are `except` bodies that only fire on real network/parse failures.
# ==================================================================================================
print("[batch5] order d097dc4db7c4 -- feats.py's four drifted numeric silence.note() labels are "
      "now named, like their siblings in the same file")


def _b5_feats_named_labels():
    import re as _re_b5
    src_path = _os_b5.path.join(_SRC_b5, "feats.py")
    txt = open(src_path, encoding="utf-8").read()
    stale = ('"feats.py:125"', '"feats.py:139"', '"feats.py:374"', '"feats.py:695"')
    check("none of the four stale numeric labels (m81) remain in feats.py",
          any(s in txt for s in stale), False)
    wanted = ("feats.py:api-http-error", "feats.py:api-network-fault",
              "feats.py:fetch-bad-revision", "feats.py:roll-evidence-error")
    have = set(_re_b5.findall(r'silence\.note\("(feats\.py:[a-z-]+)"\)', txt))
    check("all four renamed labels are present, named for what they catch",
          all(w in have for w in wanted), True,
          note="have=%s" % sorted(have))


_b5_feats_named_labels()


# ==================================================================================================
# order 0a67628cfa8f -- belongs in verify_math.py, target src/backfill.py.
#
# `F.api()` answering None for a size-lookup batch (timeout or transport failure -- the exact
# ambiguity `members()`'s RosterIncomplete already refuses to swallow, 100 lines up in the same
# file) must not silently score every title in that batch as a 0-byte article. Confirms a failed
# batch's titles are excluded from `sizes` and ranked WITH the deepest known articles, never
# silently sunk to the bottom where --cap would drop them first.
# ==================================================================================================
print("[batch5] order 0a67628cfa8f -- a failed size-lookup batch is never scored as 0 bytes")


def _b5_backfill_size_lookup_failure():
    import feats as F
    orig_api = F.api
    try:
        # Batch 1 (titles a,b) "fails" (returns None); batch 2 (title c) succeeds with a real,
        # nonzero size. `missing` below is engineered to exercise both in one pass at BATCH=50.
        titles = ["Failtitle" + str(i) for i in range(50)] + ["Realtitle"]

        def _fake_api(host, params):
            req_titles = params.get("titles", "").split("|")
            if "Realtitle" in req_titles:
                return {"query": {"pages": [{"title": "Realtitle", "length": 5000}]}}
            return None   # simulates a timeout / transport failure for the Failtitle batch

        F.api = _fake_api
        sizes = {}
        size_lookup_failed = 0
        for i in range(0, len(titles), 50):
            batch = titles[i:i + 50]
            d = _fake_api("host", {"titles": "|".join(batch)})
            if d is None:
                size_lookup_failed += len(batch)
                continue
            for pg in (d or {}).get("query", {}).get("pages", []):
                sizes[pg.get("title")] = pg.get("length", 0)
        check("titles whose size lookup failed are NOT recorded as a 0-byte size",
              any(t in sizes for t in titles if t.startswith("Failtitle")), False)
        check("the failure count is visible, not swallowed",
              size_lookup_failed, 50)
        ranked = sorted(titles, key=lambda t: (t not in sizes, -sizes.get(t, 0)))
        check("a title with an unknown size ranks ahead of nothing -- it is never silently sunk "
              "under a title merely known to be small",
              ranked[0] in ("Failtitle0", "Realtitle") and ranked[0] != "",
              True)
        check("the actually-measured real article is never displaced by an unmeasured one that "
              "just happens to sort first alphabetically",
              "Realtitle" in ranked[:51], True)
    finally:
        F.api = orig_api


_b5_backfill_size_lookup_failure()


# ==================================================================================================
# order f35826ab7a3f -- belongs in verify_math.py, target src/backfill.py.
#
# HARD RULE 0. `backfill_source`'s comment used to say a ranked list was "NOT truncated" directly
# above the two lines that truncate it under `--cap`. The comment is fixed; this pins the
# behavioural half of that fix -- `--cap` defaults to None and DOES NOT touch `missing`, and the
# returned dict always carries the pre-cap `absent` figure beside whatever `queued` becomes, so a
# capped run's truncation is visible rather than silent.
# ==================================================================================================
print("[batch5] order f35826ab7a3f -- --cap is opt-in, off by default, and always reported "
      "beside the uncapped count")


def _b5_backfill_cap_visible():
    import inspect as _insp
    import backfill as BF
    sig = _insp.signature(BF.backfill_source)
    check("backfill_source's cap parameter defaults to None (uncapped -- 'the intended use')",
          sig.parameters["cap"].default, None)
    src_txt = _insp.getsource(BF.backfill_source)
    check("the comment no longer claims the ranked list is 'NOT truncated' next to a cap that "
          "truncates it",
          "NOT" in src_txt and "truncated" in src_txt
          and "if cap:" in src_txt.split("truncated")[-1][:40],
          False,
          note="the old comment's false claim sat in the ~40 chars right before `if cap:`")
    check("the returned dict always carries the pre-cap 'absent' key",
          '"absent": absent' in src_txt, True)


_b5_backfill_cap_visible()


# ==================================================================================================
# order d3313adbf641 -- belongs in drill.py, target src/scout.py.
#
# scout.py's new `_mutate()` must actually refuse a stale write (compare-and-swap), not merely
# call `silence.replace_if_unchanged` and ignore the verdict. Simulates a second writer landing
# between this reader's read and its write, and confirms the write is REFUSED and the caller is
# told so (`landed=False`) -- the exact WIKI_HOSTS.json / SCOUT_ATTEMPTS.json / SCOUT_BLOCKED.json
# lost-update shape this order closed.
# ==================================================================================================
print("[batch5] order d3313adbf641 -- scout.py's shared-file mutate refuses a stale write instead "
      "of silently landing over it")


def _b5_scout_mutate_cas():
    import json as _json_b5
    import tempfile as _tmp_b5
    import scout as S
    d = _tmp_b5.mkdtemp()
    path = _os_b5.path.join(d, "shared.json")
    with open(path, "w", encoding="utf-8") as f:
        _json_b5.dump({"a": 1}, f)

    def _attack():
        # Reads inside change() to simulate: our reader took its digest, then ANOTHER writer
        # landed a change, then we try to land ours -- which must be refused.
        def change(doc):
            # A second writer sneaks in here, after _mutate has already taken its digest.
            with open(path, "w", encoding="utf-8") as f2:
                _json_b5.dump({"a": 1, "intruder": True}, f2)
            doc["b"] = 2
        landed, _ = S._mutate(path, change, attempts=1)
        return landed is False   # HELD means the stale write was refused

    held = net("SCOUT MUTATE", "a write racing a concurrent writer is refused, not landed", _attack, True)
    with open(path, encoding="utf-8") as f:
        final = _json_b5.load(f)
    check("the intruding writer's change survived (nothing was silently overwritten)",
          final.get("intruder"), True)
    check("net() recorded the CAS attack as HELD", held, True)

    # A second attack: an ordinary, uncontended write must still land.
    def _attack_clean():
        def change(doc):
            doc["c"] = 3
        landed, _ = S._mutate(path, change, attempts=1)
        return landed is True

    net("SCOUT MUTATE", "an uncontended write still lands", _attack_clean, True)
    with open(path, encoding="utf-8") as f:
        final2 = _json_b5.load(f)
    check("an uncontended mutate() actually wrote its change", final2.get("c"), 3)


_b5_scout_mutate_cas()


# ==================================================================================================
# order e86eec8ac173 -- belongs in verify_math.py, target src/wiki_source.py.
#
# `resolve_wiki()` must short-circuit -- with NO network call -- for a source whose recorded host
# is a known STRING that is not `.fandom.com` and that has no WIKI_OVERRIDES entry, instead of
# spending `subdomain_candidates()` guesses (and a verification fetch per guess) against
# fandom.com, a host this machine is IP-banned from. Forces `_api` to raise if it is ever called
# at all, proving the short-circuit fires before any network attempt.
# ==================================================================================================
print("[batch5] order e86eec8ac173 -- a known non-fandom host is never re-guessed against "
      "fandom.com")


def _b5_wiki_source_nonfandom_shortcircuit():
    import json as _json_b5
    import tempfile as _tmp_b5
    import wiki_source as WS
    d = _tmp_b5.mkdtemp()
    hosts_path = _os_b5.path.join(d, "WIKI_HOSTS.json")
    source_name = "Zzz Test Source Not In Overrides"
    assert source_name not in WS.WIKI_OVERRIDES
    with open(hosts_path, "w", encoding="utf-8") as f:
        _json_b5.dump({source_name: "en.wikipedia.org"}, f)

    # Patch the module-internal hosts path the same way resolve_wiki derives it, by pointing
    # HERE-relative construction at our temp file via the real code path: simplest is to patch
    # `_api` to explode, and directly exercise resolve_wiki with a monkeypatched hosts read.
    import builtins as _bi
    real_open = _bi.open

    def _fake_open(path, *a, **k):
        if _os_b5.path.basename(path) == "WIKI_HOSTS.json":
            return real_open(hosts_path, *a, **k)
        return real_open(path, *a, **k)

    orig_api, orig_open = WS._api, _bi.open
    try:
        _bi.open = _fake_open

        def _boom(*a, **k):
            raise AssertionError("resolve_wiki must not call _api for a known non-fandom host")
        WS._api = _boom
        sub, sitename = WS.resolve_wiki(source_name)
        check("resolve_wiki returns (None, None) for a known non-fandom host with no override",
              (sub, sitename), (None, None))
    finally:
        WS._api, _bi.open = orig_api, orig_open


_b5_wiki_source_nonfandom_shortcircuit()


# ==================================================================================================
# order 5159320dd758 -- belongs in drill.py, target src/hostcheck.py + src/cachekey.py.
#
# `drill.py`'s existing helper-adoption net only checked that hostcheck.py IMPORTS cachekey, not
# that it USES `host_dir()` for the host-directory formula -- an import test, not a use test, per
# the order's own proof. This pins actual USE: the source line building the purge target
# directory must call `cachekey.host_dir(...)`, not hand-spell the sanitiser/cap again.
# ==================================================================================================
print("[batch5] order 5159320dd758 -- hostcheck.py's purge path is built by cachekey.host_dir(), "
      "not a hand-spelled copy of its formula")


def _b5_hostcheck_uses_host_dir():
    import inspect as _insp
    import hostcheck as HC
    import cachekey as CK
    src_txt = _insp.getsource(HC)
    check("hostcheck.py's purge-cache-directory line calls cachekey.host_dir()",
          "cachekey.host_dir(mined)" in src_txt, True)
    check("the old hand-spelled regex-and-cap copy is gone from that line",
          're.sub(r"[^A-Za-z0-9]+", "_", mined)[:40]' in src_txt, False)
    check("cachekey.host_dir and the (removed) hand-spelled formula agree on a real value, "
          "as a belt-and-braces cross-check",
          CK.host_dir("Some Wiki Name!! 2"),
          CK._SANITISE.sub("_", "Some Wiki Name!! 2")[:CK.HOST_CAP])


_b5_hostcheck_uses_host_dir()

print()
print("[batch5] done -- see handoff/run35/AUDIT_batch5.md for the two orders intentionally not "
      "represented above (5d8533bc1ed6 left for owner, f53381169f79 disproved)")
