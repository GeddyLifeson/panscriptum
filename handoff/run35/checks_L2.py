# run35, LOCAL batch L2 -- proposed verify_math/drill checks for the orders worked this batch.
# Runnable Python. Each block is commented with the order id and its target file. These are
# PROPOSALS for verify_math.py / drill.py to adopt -- this agent does not own those files and
# did not add them there.

import os
import re

HERE = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
SRC = os.path.join(HERE, "src")


# order 23a7efaeebe0 -- src/retry_synthesis.py
# Assert the merge summary line names both skip reasons distinctly (never a single blended
# "skipped" figure that could hide write-denials inside a benign-looking count).
def check_retry_synthesis_two_counters():
    text = open(os.path.join(SRC, "retry_synthesis.py"), encoding="utf-8").read()
    assert "denied = 0" in text.replace(" ", "") or "denied=0" in text.replace(" ", ""), \
        "retry_synthesis.do_merge lost its separate 'denied' counter"
    assert "denied (write refused" in text, \
        "retry_synthesis.do_merge summary no longer names write-denials distinctly from " \
        "already-had-synthesis skips"


# order 4012ceb89eb4 -- src/build_terminal.py
# The dead 'rim' ternary must not come back; the shell-2 label text element should carry no
# letter-spacing attribute at all (it was always 0 in practice).
def check_build_terminal_no_dead_rim():
    text = open(os.path.join(SRC, "build_terminal.py"), encoding="utf-8").read()
    assert "rim=false" not in text.replace(" ", ""), \
        "build_terminal.py: dead 'rim' flag reintroduced"
    assert "rim?4:0" not in text, \
        "build_terminal.py: unreachable letter-spacing ternary reintroduced"


# order 480757b8acb5 -- src/manifest_builder.py
# The Feats job's content_hash must include its source_context, same as the chapter job does,
# so a corrected ceiling_entity/provisional_magnitude regenerates the Feats chapter too.
def check_manifest_builder_feats_hash_includes_context():
    text = open(os.path.join(SRC, "manifest_builder.py"), encoding="utf-8").read()
    assert 'content_hash({"entities": slim, "context": ctx})' in text, \
        "manifest_builder.py: Feats job content_hash no longer folds in source_context (ctx)"


# order 54950602a322 -- src/manifest_builder.py
# The manifest writer must use the atomic silence.write_json, not a bare truncating open+dump,
# since generate.py reads this exact file on every run.
def check_manifest_builder_atomic_write():
    text = open(os.path.join(SRC, "manifest_builder.py"), encoding="utf-8").read()
    assert 'silence.write_json(out_path, {"jobs": all_jobs}' in text, \
        "manifest_builder.py: manifest.json write is no longer routed through silence.write_json"
    assert 'with open(out_path, "w"' not in text, \
        "manifest_builder.py: a bare truncating open(out_path, 'w') reappeared for manifest.json"


# order 55be447a356e -- src/foreman.py
# clear_learned_caps must not report the same sentence for "nothing to clear" and "could not
# read the database". Runnable smoke test: point it at an unreadable/corrupt db path and check
# the returned message differs from the healthy zero-clear sentence, and that no connection is
# left open (best-effort: sqlite3 has no public open-handle count, so this checks the code
# shape -- the finally/close pattern -- rather than a live handle count).
def check_foreman_clear_learned_caps_distinguishes_failure():
    src = open(os.path.join(SRC, "foreman.py"), encoding="utf-8").read()
    assert "unreadable = []" in src, \
        "foreman.clear_learned_caps: lost its separate 'unreadable dbs' tracking list"
    assert "unknown whether they still hold stale caps" in src, \
        "foreman.clear_learned_caps: failure-path message no longer distinct from the healthy one"
    assert "c.close()" in src.split("def clear_learned_caps")[1].split("def ")[0], \
        "foreman.clear_learned_caps: sqlite connection is no longer explicitly closed"


# order 584fcdd7dfe5 -- src/foreman.py
# Every silence.note("foreman.py:...") tag should be a durable name (function or
# function-suffix), never a bare line number, because line numbers rot on the next edit.
def check_foreman_no_numeric_silence_tags():
    text = open(os.path.join(SRC, "foreman.py"), encoding="utf-8").read()
    bad = re.findall(r'silence\.note\("foreman\.py:(\d+)"\)', text)
    assert not bad, f"foreman.py: stale numeric silence.note tag(s) reappeared: {bad}"


# order eeafcd2aa091 -- src/foreman.py
# recatalogue_models must not report "provider lists refreshed" (or any success text) on a
# nonzero exit from catalogue_models.py.
def check_foreman_recatalogue_models_fails_on_nonzero_exit():
    text = open(os.path.join(SRC, "foreman.py"), encoding="utf-8").read()
    fn = text.split("def recatalogue_models")[1].split("\ndef ")[0]
    assert "r.returncode != 0" in fn, \
        "foreman.recatalogue_models: lost its explicit nonzero-exit branch"
    assert "return False, f\"catalogue_models.py exited" in fn, \
        "foreman.recatalogue_models: no longer reports failure distinctly on nonzero exit"


# order a79600702b85 -- src/autostart.py
# start_supervisor must close its own stdout/stderr log handles after Popen returns.
def check_autostart_start_supervisor_closes_handles():
    text = open(os.path.join(SRC, "autostart.py"), encoding="utf-8").read()
    fn = text.split("def start_supervisor")[1].split("\ndef ")[0]
    assert "finally:" in fn and "out.close()" in fn and "err.close()" in fn, \
        "autostart.start_supervisor no longer closes its stdout/stderr log handles"


# order d04fb20949b1 -- src/generate.py (THE SIGNATURE FAILURE SHAPE)
# A missing/mistyped --manifest must refuse loudly and the process must exit nonzero -- not
# read as an empty work-list and exit 0. This is runnable end-to-end via subprocess, but the
# prose gate (config.yaml prose_enabled) must be OPEN for the manifest check to be reached, so
# this check inspects source shape rather than driving the live pipeline from a checks file.
def check_generate_missing_manifest_refuses():
    text = open(os.path.join(SRC, "generate.py"), encoding="utf-8").read()
    assert "if not os.path.exists(manifest_full):" in text, \
        "generate.py: lost the explicit --manifest existence check"
    assert "REFUSING: --manifest" in text, \
        "generate.py: lost the loud refusal message for a missing --manifest"
    assert "sys.exit(main())" in text, \
        "generate.py: __main__ no longer routes main()'s return value into the process exit " \
        "code -- a refusal that returns 1 would once again be invisible to the scheduler"


if __name__ == "__main__":
    fns = [v for k, v in sorted(globals().items()) if k.startswith("check_")]
    for fn in fns:
        fn()
        print("OK", fn.__name__)
    print(f"{len(fns)} checks passed")
