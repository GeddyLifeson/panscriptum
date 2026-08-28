# run #36 — batch 06 cross-module requests

Batch 06 owns `catalogue_web.py`, `dashboard.py`, `drill.py`, `publish.py`, `render.py`,
`resync_roll.py`. The changes below are needed in modules this batch does not own and were NOT
made here.

## 1. `wiki_source.py` — `page_text()` collapses failure and emptiness into the same `""`

**Owner of `wiki_source.py`, please read.** Order `ea2f5e924fb2` (catalogue_web drops entries
whose page text failed to fetch) was fixed inside `catalogue_web.py` as far as it can be: both
`catalogue()` and `catalogue_composite()` now COUNT every title that came back without text and
name the count in the record's `provenance` and in the returned note, instead of dropping the
title in silence.

That is the honest limit of what the cataloguer can say, because the module it asks cannot tell
it any more than that:

* `wiki_source.page_text()` (`src/wiki_source.py`, the `for section in (0, 1, 2)` loop) returns
  `""` when all three section fetches raised — timeout, 429, anything — and returns the same
  `""` when the page genuinely has no prose. The `silence.note("wiki_source-page_text-section")`
  in the except records that something failed, but the RETURN VALUE carries none of it.
* `wiki_source.page_texts()` then drops every falsy result from the dict it hands back, so the
  caller cannot even count how many titles it asked about and did not get.

So `catalogue_web`'s new count is an upper bound on both quantities at once, and the provenance
sentence says so in as many words. It cannot become a real "N pages were LOST to the network"
figure until `wiki_source` distinguishes the two.

**Requested change (additive, no public-signature break):** have `page_text()` report whether it
exhausted all three sections on transport errors rather than on empty parses — e.g. an optional
out-parameter, a module-level counter, or a second function `page_texts_with_failures()` that
returns `(texts, failed_titles)`. Then `catalogue_web` can split its one number into "no prose"
and "never read", and the second one can be made retryable.

Nothing in `catalogue_web.py` needs to change first; the counting is already in place and will
simply become more precise.

## 2. Nothing else

No other batch-06 fix required a module outside the batch. In particular the sixteen drill nets
converted from whole-file substring search to AST checks only READ the modules they assert
about (`overnight.py`, `local_agent.py`, `binding_health.py`, `workorders.py`, `feats.py`,
`generate.py`, `publish.py`, `foreman.py`, `overwatch.py`, `mutate.py`, `manifest_builder.py`,
`cascade_bridge.py`, `resync_roll.py`, `drill.py`); none of them were edited.
