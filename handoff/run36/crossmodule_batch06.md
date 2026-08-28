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

## 2. OWNER QUESTION — order `026a498d47d2`, `render.py` has no callers

Left OPEN on purpose. The finding is TRUE as stated: nothing in `src/` imports `render` or calls
`render.view` / `containment_svg` / `children_of`, and the single grep hit in `build_terminal.py`
is a comment. But "no callers" is not by itself a defect here, and the repair is a product
decision this batch is not entitled to take.

Measured rather than assumed, run #36: `python src/render.py` runs clean and answers for all
nine tiers against a real coordinate --

    hyperverse svg 7 children 3,939 bytes | xenoverse svg 7 children | metaverse svg 7 children
    multiverse svg 1 child | universe svg 0 children | galaxy/system/planet/burg url

-- and `--write` lands the five drawn tiers into `output/views/`. So this is a working
operator-facing CLI with a documented `--write` mode, not dead code: the module reads as
something meant to be RUN, and it does run.

**The question for the owner:** should the cosmology views be WIRED IN -- published by
`publish.py` and linked from the registry terminal so the top five tiers are viewable from the
site -- or is `render.py` deliberately a hand-run tool? Wiring it in means choosing what gets
published, where the SVGs live in the export copy, and what links to them; none of that is
recoverable from the source, and guessing it would put nine new files into a PUBLIC repo on a
maintenance agent's judgement. `publish.py` is in this batch and could carry the change in one
edit the moment the answer is yes.

## 3. Nothing else

One thing to be aware of rather than to act on: the drill breach this batch found and fixed was
in ITS OWN fixture, not in another module. `policy.py` gained a deliberate `absent`-operator
exemption from the vacuous-pass report this run (its comment cites order `9ef866225683`), and
the drill net "a pass over a MISSING field is flagged vacuous" happened to drive `op: "absent"`
-- the one operator that is now exempt. The exemption is right; the fixture moved to
`not_matches` (which `policy.py` names as the case that must STAY reported) and the exemption
itself got a net of its own. `policy.py` was not edited.

No other batch-06 fix required a module outside the batch. In particular the sixteen drill nets
converted from whole-file substring search to AST checks only READ the modules they assert
about (`overnight.py`, `local_agent.py`, `binding_health.py`, `workorders.py`, `feats.py`,
`generate.py`, `publish.py`, `foreman.py`, `overwatch.py`, `mutate.py`, `manifest_builder.py`,
`cascade_bridge.py`, `resync_roll.py`, `drill.py`); none of them were edited.
