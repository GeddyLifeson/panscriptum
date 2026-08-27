# run35, wave 2, batch M2 -- proposed verify_math/drill checks for the orders worked this batch.
# Runnable Python. Each block is commented with the order id and its target file. These are
# PROPOSALS for verify_math.py / drill.py to adopt -- this agent does not own those files and
# did not add them there.

import inspect
import os
import sys

HERE = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
SRC = os.path.join(HERE, "src")
sys.path.insert(0, SRC)


# order d49cda5cc058 -- src/sweep.py, sweep() -- THE headline fix this batch.
# A corrupt evidence cache must land a distinct health-ledger record, never the silent
# (None, None) that also means "nothing was ever mined here".
def check_sweep_passes_on_corrupt_to_cachekey_load():
    import sweep as SW
    src = inspect.getsource(SW.sweep)
    assert "on_corrupt=" in src, \
        "sweep.sweep() calls cachekey.load without on_corrupt -- a corrupt evidence cache is " \
        "silently indistinguishable from an entity nothing was ever mined for"
    # Exercise the real path: a genuinely corrupt (truncated) cache file must be reported.
    import tempfile
    tmpd = tempfile.mkdtemp()
    host_dir = os.path.join(tmpd, "examplehost_com")
    os.makedirs(host_dir, exist_ok=True)
    import cachekey
    bad_path = cachekey.natural_path(tmpd, "examplehost.com", "Some Entity")
    with open(bad_path, "w", encoding="utf-8") as f:
        f.write("{not valid json")
    seen = []
    doc, fp = cachekey.load(tmpd, "examplehost.com", "Some Entity",
                            on_corrupt=lambda p: seen.append(p))
    assert doc is None and fp is None, "a corrupt file must still read as a miss"
    assert seen, "on_corrupt must fire for a truncated/unparseable cache file"
    import shutil
    shutil.rmtree(tmpd, ignore_errors=True)


# order 29fdcb11b3cd -- src/coverage.py, _so_save()
# dirty must only clear when replace_retry actually landed the file.
def check_coverage_so_save_gates_dirty_on_landed_write():
    import coverage as CV
    src = inspect.getsource(CV._so_save)
    assert 'if _sil.replace_retry(tmp, _SO_CACHE_P):' in src, \
        "coverage._so_save() must only clear dirty inside the replace_retry() truth branch"
    # dirty=0 must not appear unconditionally right after the write.
    lines = [ln.strip() for ln in src.splitlines()]
    idx = next(i for i, ln in enumerate(lines) if "replace_retry(tmp, _SO_CACHE_P)" in ln)
    assert '_SO["dirty"] = 0' in lines[idx + 1], \
        "the dirty-clear must be the line immediately gated by the replace_retry check"


# order 2b10b8d71c45 -- src/ingest_doc.py, main()
# write_record's landed verdict must be checked, not discarded, when stamping provenance.
def check_ingest_doc_checks_write_record_verdict():
    text = open(os.path.join(SRC, "ingest_doc.py"), encoding="utf-8").read()
    assert "if not P.write_record(rp, rec):" in text, \
        "ingest_doc.py main() must gate on write_record's return value, not discard it"


# order 09405680f175 -- src/backfill.py, main() --audit
# The ranked/truncated audit table must announce its remainder, matching catalog.py's pattern.
def check_backfill_audit_announces_remainder():
    text = open(os.path.join(SRC, "backfill.py"), encoding="utf-8").read()
    assert "for x in rows[:26]:" in text, "backfill.py --audit slice changed shape unexpectedly"
    assert "len(rows) - 26" in text, \
        "backfill.py --audit must print how many rows were not shown, like catalog.py:66-67"


# orders 00d8436bb86d, 322cc5ab6f31, eb626e4d9dde -- stale silence.note LINE-NUMBER tags
# No silence.note call anywhere in this batch's owned files should carry a bare numeric tag
# of the form "<file>.py:<digits>" -- every one must be a stable content label.
def check_no_stale_numeric_silence_tags_in_batch_m2_files():
    import re
    numeric_tag = re.compile(r'silence\.note\("([a-zA-Z_]+\.py):(\d+)"\)')
    offenders = []
    for fn in ("wiki_source.py", "overwatch.py", "catalogue_web.py"):
        text = open(os.path.join(SRC, fn), encoding="utf-8").read()
        for m in numeric_tag.finditer(text):
            offenders.append("%s:%s" % (fn, m.group(0)))
    assert not offenders, "stale numeric silence.note tags remain: %r" % offenders


# order b41b17c1b12b -- src/catalogue_web.py, catalogue()
# The fetch-loop progress heartbeat must rebind _short per unit, not read discovery's leftover.
def check_catalogue_web_fetch_loop_rebinds_short():
    import catalogue_web as CWEB
    src = inspect.getsource(CWEB.catalogue)
    fetch_start = src.index('for canon, cats, titles in planned:')
    fetch_body_head = src[fetch_start:fetch_start + 700]
    assert '_short = canon.split(' in fetch_body_head, \
        "catalogue()'s fetch loop must rebind _short at its own top, not inherit discovery's"


# order 3784508bc4da -- src/catalogue_web.py, CATEGORY_SCAN_DEPTH
# Dead constant must stay (not auto-deletable) but its comment must not describe a mechanism
# that no longer exists, and MAX_PER_SOURCE must be untouched (still None, Hard Rule 0).
def check_catalogue_web_category_scan_depth_comment_is_honest():
    import catalogue_web as CWEB
    assert CWEB.CATEGORY_SCAN_DEPTH is None
    assert CWEB.MAX_PER_SOURCE is None, "MAX_PER_SOURCE must stay None -- Hard Rule 0"
    text = open(os.path.join(SRC, "catalogue_web.py"), encoding="utf-8").read()
    assert "Must be well above MAX_PER_CATEGORY or ranking" not in text, \
        "CATEGORY_SCAN_DEPTH's comment still describes the retired scan-then-rank relationship"
    assert "DEAD:" in text.split("CATEGORY_SCAN_DEPTH = None")[0].splitlines()[-4], \
        "CATEGORY_SCAN_DEPTH's comment should say plainly that it is dead"


# order 7c13fa26cf6d -- src/hostcheck.py, --purge help text
# The CLI help must not promise a host-rejection safeguard purge() never implements.
def check_hostcheck_purge_help_matches_docstring():
    text = open(os.path.join(SRC, "hostcheck.py"), encoding="utf-8").read()
    assert "AND whose host was independently rejected" not in text, \
        "hostcheck.py --purge help still advertises the phantom safeguard"


# order a8c3f7ee6965 -- src/feats.py, api()
# note_ok(host) must run only after a successful JSON parse, never before it.
def check_feats_api_notes_ok_only_after_parse():
    import feats as F
    src = inspect.getsource(F.api)
    idx_parse = src.index("json.loads(_body)")
    idx_note = src.index("note_ok(host)")
    assert idx_note > idx_parse, \
        "feats.api() must call note_ok(host) after json.loads succeeds, not before it"


# order f7577dc52f5c -- src/feats.py, strip_wikitext()
# Unquoted/capitalised table attributes and inline || cell separators must not survive.
def check_feats_strip_wikitext_cleans_table_cells():
    import feats as F
    t1 = ('{| class="wikitable"\n|-\n! colspan=2 | Power Levels\n|-\n| Goku || 9,000\n|}')
    out1 = F.strip_wikitext(t1)
    assert "colspan" not in out1 and "||" not in out1, \
        "strip_wikitext left an unquoted table attribute or a raw || separator: %r" % out1
    assert "Power Levels" in out1 and "Goku" in out1 and "9,000" in out1
    t2 = ('{| class="wikitable"\n|-\n! Style="color:red" | Header\n|-\n'
         '| align=center | 42\n|}')
    out2 = F.strip_wikitext(t2)
    assert "Style=" not in out2 and "align=center" not in out2, \
        "strip_wikitext left a capitalised or unquoted attribute: %r" % out2
    assert "Header" in out2 and "42" in out2
    # the already-working lowercase+quoted case must still work
    t3 = '{| class="wikitable"\n|-\n| style="width:10em" | Kaioken\n|}'
    assert F.strip_wikitext(t3).strip() == "Kaioken"


# order 7dd11bb4dae8 -- src/scout.py, _land()
# _land must go through silence.write_json (pid+thread temp name), not a fixed path+".tmp".
# (Checked as an actual assignment statement, not a substring -- the fix's own docstring
# quotes the retired `path + ".tmp"` code by name as explanation, so a bare substring test
# would fail against the very comment documenting the fix.)
def check_scout_land_uses_write_json():
    import re
    import scout as SC
    src = inspect.getsource(SC._land)
    assert not re.search(r'^\s*tmp = path \+ "\.tmp"', src, re.M), \
        "scout._land() still builds a fixed shared temp name"
    assert "silence.write_json(" in src, "scout._land() must delegate to silence.write_json"


# orders b9769e6a9ef6, ba9f7292b400, cf719be96588, 93e99cd8bd7e, 6d6c02c903b0 -- src/read.py
def check_read_run_prints_skipped_counter():
    import read as R
    src = inspect.getsource(R.run)
    assert 'done["skipped"]' in src.split("def work(r):")[1].split("with ThreadPoolExecutor")[1], \
        "read.run()'s closing/print section must surface done['skipped'], not just accumulate it"


def check_read_gate_is_lock_guarded():
    import read as R
    assert isinstance(R._GATE_LOCK, type(R._TRANSPORT_LOCK)), \
        "read.py must define a lock for _gate()'s check-and-set, matching _TRANSPORT_LOCK's shape"
    src = inspect.getsource(R._gate)
    assert "_GATE_LOCK" in src, "_gate() must acquire _GATE_LOCK around its recheck-and-write"


def check_read_entity_cache_write_uses_write_json_and_checks_verdict():
    import re
    import read as R
    src = inspect.getsource(R.read_entity)
    assert not re.search(r'^\s*tmp = path \+ "\.tmp"', src, re.M), \
        "read_entity()'s cache write still builds a fixed shared temp name"
    assert "silence.write_json(path, out" in src, \
        "read_entity() must land its cache file through silence.write_json"
    assert "if not silence.write_json(path, out" in src, \
        "read_entity() must check write_json's landed verdict, not discard it"


def check_read_save_qcache_uses_write_json():
    import re
    import read as R
    src = inspect.getsource(R._save_qcache)
    assert not re.search(r'^\s*tmp = QCACHE \+ "\.tmp"', src, re.M), \
        "_save_qcache() still builds a fixed shared temp name"
    assert "silence.write_json(QCACHE" in src


def check_read_no_stale_ask_tag_and_no_stale_cap_comment():
    text = open(os.path.join(SRC, "read.py"), encoding="utf-8").read()
    assert 'silence.note("read.py:188")' not in text, \
        "read.py still has the merged read.py:188 tag on two distinct _ask() handlers"
    assert "read.py:ask-quick-pool" in text and "read.py:ask-backoff-ladder" in text
    assert "twelve covers the whole of most subjects" not in text, \
        "read_entity()'s stale RANKED-AND-CAPPED comment (describing a retired default cap) " \
        "is still present"


if __name__ == "__main__":
    fails = []
    mod = sys.modules[__name__]
    checks = [(n, f) for n, f in sorted(inspect.getmembers(mod, inspect.isfunction))
             if n.startswith("check_")]
    for name, fn in checks:
        try:
            fn()
            print("  OK  ", name)
        except Exception as e:
            fails.append((name, e))
            print("  FAIL", name, "--", e)
    print("\n%d checks, %d failed" % (len(checks), len(fails)))
