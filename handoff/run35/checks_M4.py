# run35, wave 2, batch M4 -- proposed verify_math/drill checks for the orders worked this batch.
# Runnable Python. Each block is commented with the order id and its target file. These are
# PROPOSALS for verify_math.py / drill.py to adopt -- this agent does not own those files and
# did not add them there.

import os
import sys

HERE = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
SRC = os.path.join(HERE, "src")
sys.path.insert(0, SRC)


# order 54cd47a337dc -- src/pipeline.py, src/tuning.py
# pipeline._pool_answering must not have its own copy of the POOL_PROOF read; it delegates to
# tuning._answering_buckets() now, so the two modules cannot drift on staleness handling again.
def check_pipeline_pool_answering_delegates_to_tuning():
    import inspect
    import pipeline
    src = inspect.getsource(pipeline._pool_answering)
    body = src.split('"""', 2)[-1]  # drop the docstring, which may mention the old filename
    assert "_answering_buckets" in body, \
        "pipeline._pool_answering no longer delegates to tuning._answering_buckets"
    assert "json.load" not in body and "POOL_PROOF.json" not in body, \
        "pipeline._pool_answering re-acquired its own copy of the POOL_PROOF read"


# order 5faa6da447e1 -- src/cleanup.py
# The eaten-escape guard must actually cover _SETTING_META (via pipeline.PL) and every pattern
# in _MARKUP, not skip them as an inert None entry.
def check_cleanup_guard_covers_setting_meta_and_markup():
    import cleanup
    assert cleanup.PL._SETTING_META is not None
    # The guard already ran at import time without raising -- this just confirms the patterns
    # it must have checked are the ones the finding named, so a future edit that removes them
    # from the roster (reverting to the None placeholder) is easy to catch by re-reading the
    # source rather than only trusting import-time silence.
    import inspect
    src = inspect.getsource(cleanup)
    guard_start = src.index("# GUARD.")
    guard_region = src[guard_start:src.index("\n\n\n", guard_start)]
    assert "_SETTING_META" in guard_region and "PL._SETTING_META" in guard_region, \
        "cleanup.py's guard roster dropped the real _SETTING_META pattern"
    assert "_MARKUP" in guard_region, \
        "cleanup.py's guard roster no longer covers _MARKUP's patterns"


# order 8fb51fc68004 -- src/rigor.py
# measure_bit_value must take exactly one parameter now that the dead 'module' was dropped.
def check_rigor_measure_bit_value_has_no_dead_param():
    import rigor
    assert rigor.measure_bit_value.__code__.co_varnames[
        :rigor.measure_bit_value.__code__.co_argcount] == ("band",), \
        "measure_bit_value should take exactly one parameter, 'band'"
    assert "module" not in rigor.measure_bit_value.__code__.co_varnames


# order cbb921d34442 -- src/rigor.py
# The measure_bit_value docstring must not cite the wrong verify_math.py line range for its pin;
# it should cite the stable section tag instead.
def check_rigor_docstring_cites_section_tag_not_stale_line():
    import rigor
    doc = rigor.measure_bit_value.__doc__ or ""
    assert "pinned by `verify_math.py:382-384`" not in doc, \
        "measure_bit_value should no longer assert the wrong (Jensen-gap) range as its pin"
    assert "§20f" in doc or "20f" in doc, \
        "measure_bit_value should cite section 20f as what pins it"


# order ad730acf0b18 -- src/propagation.py
# observed_mark's post-loop 'return 0' is unreachable once lag >= 0 (ascension_years(1) == 0.0),
# and the docstring must say the honest [^0] comes from the lag<0 guard alone, not the loop.
def check_propagation_observed_mark_zero_lag_returns_rung_one():
    import propagation as P
    assert P.ascension_years(1) == 0.0
    # lag == 0 exactly should hit the rung-1 branch inside the loop, not the unreachable trailer.
    assert P.observed_mark(distance=0.0, years_since=0.0) == 1
    doc = (P.observed_mark.__doc__ or "").upper()
    assert "LAG < 0` GUARD" in doc, \
        "observed_mark's docstring should attribute the honest [^0] to the lag<0 guard alone"


# order e3a52d3f20b5 -- src/tempus.py
# apparent_lag_years must return one shape regardless of whether a path was found.
def check_tempus_apparent_lag_years_one_shape():
    import tempus as T
    no_path = T.apparent_lag_years("__no_such_shelf_a__", "__no_such_shelf_b__")
    assert set(no_path.keys()) >= {"distance", "lag_years", "path", "note"}, \
        "apparent_lag_years' no-path branch must carry the same keys as the success branch"
    assert no_path["distance"] is None and no_path["path"] == []


# order 3a4e66ed5efb -- src/assay.py (verification only; already fixed, no code change)
# _rho_doc's docstring must not attribute the missing-matrix guard to _check_constants, which
# never mentions axis_correlation at all.
def check_assay_rho_doc_does_not_misattribute_guard():
    import assay
    doc = assay._rho_doc.__doc__ or ""
    assert "IT DOES NOT AND NEVER DID" in doc, \
        "assay._rho_doc should still carry the correction disowning the _check_constants credit"
    import inspect
    cc_src = inspect.getsource(assay._check_constants)
    assert "axis_correlation" not in cc_src and "AXIS_CORRELATION" not in cc_src, \
        "_check_constants must not actually reason about the correlation matrix"
