# Next Steps — priority queue for the next maintenance run

*Overwritten each run; history lives in HANDOFF.md. Run #2 wrote this on 2026-08-23 ~23:00.*

## 1. Carried over / verify-next-run

1. **`health.py --preflight` "entries stranded in closed batches: 5"** — new this run, not
   investigated (pipeline.py was live and being edited concurrently with this run; chasing a
   moving live-process count mid-edit risked a false read). Re-check first thing next run —
   if the count is stable or growing, it's a real bug; if it cleared on its own as the pipeline
   cycled, note that and drop it.
2. **Verify BUGS m3–m17 land as real fixes, not just findings** — run #2 verified each against
   source (ran the code, not just read it) but only FIXED the six root causes in the Resolved
   section; the rest are documented-not-fixed by design (medium surgery, HUMAN CALL needed, or
   genuinely lower priority). Work top-to-bottom by severity next run, per the framework's own
   ladder — these are largely small/targeted (m3, m4, m5, m8, m9, m11, m17) and a good first
   pass for a quiet window.
3. **Charter regression**: `data/CHARTER_REGRESSION.json` still doesn't exist on disk as of
   this run (checked directly) — confirm the foreman dispatches it and the `automation
   reproduces the charter` standard gets a real reading.
4. **Marvel completeness row**: re-check whether it's still ~0.4% stale, or whether m3's fix
   (once applied) changes what the row reports for Marvel specifically.
5. **`publish.py --push` hit a rejected-push `RuntimeError` 3x (21:51/22:01/22:11) and had
   self-resolved by 22:05 per the export git log** (0/0 diff vs origin/main when checked this
   run) — no action needed, but if it recurs, check for a second writer pushing to the same
   branch (this project or the export copy) rather than assuming it's transient again.

## 2. New findings this run (verified, documented, not yet fixed — see BUGS.md for detail)

Small/targeted (good first pass):
6. **[m3] `completeness.py category_size()`**: all-probes-failed should land in `unreliable`,
   not vanish as `None`.
7. **[m4] `wiki_source.page_text()`**: `continue` not `return ""` on a section-0 exception.
8. **[m5] duplicate silence label `wiki_source.py:278`**: split into two content labels.
9. **[m8] `build_terminal.py` 8-source cap** on the "Shelved here" note — add "+N more".
10. **[m9] `build_terminal.py` "contains" row**: sum branch-children + shelved sources, not `||`.
11. **[m11] `navtree.py sources_under()`**: add the missing `.`-boundary check to the
    `key.startswith(path)` arm.
12. **[m17] `weave_index.py designations()`**: give it the same signature-cache pattern as its
    sibling `load_records()`.

Medium surgery (do in a quiet window, own pass):
13. **[m6] `pipeline.py`'s 9 remaining raw JSON writes** (cosmology/history/shelve/weave/write
    phases) — route through `pipeline._landed`, and fix `phase_history`'s `TIERS.json` read
    handler so a corrupt file isn't misdiagnosed as "phase 5 hasn't run".
14. **[m10] `build_terminal.py` HTML/JS escaping** — `html.escape()` every interpolated
    catalogue string (pattern already correct in `render.py`'s `containment_svg()`), and guard
    the `<script>` splice against a literal `</script>` in `NAVTREE.json`.
15. **[m7] `handbuilt.py`'s artifact write**: route through `silence.replace_retry`.

## 3. Human decisions needed (owner)

16. **[m12] `thread_integrity.py`'s asymmetric/dangling-thread detection is structurally
    unreachable** — `implied_threads()` builds its pair map symmetrically, so `classify()` can
    never report ASYMMETRIC-LAWFUL/-SUSPECT or DANGLING no matter what the corpus actually
    looks like. Is this module meant to compare the weave's implied threads against a
    separately-recorded DIRECTED thread graph it currently isn't given? If so that graph needs
    building; if the module's premise has changed, it may need a rewrite or retirement. Not a
    one-line fix either way.
17. **[m13] `pipeline.py phase_synthesis`'s 14-entity ceiling sample can silently clamp an
    entire source to a lesser band** if the true strongest entity isn't among the 14 sampled
    (by feat-count then description length). Raise the sample, change the ranking, or accept
    as a known tradeoff of a bounded-context model call — owner's call on which.
18. **[m16] `weave.py`'s per-pair `shared_sample` field is capped (8, sliced to 6)** — it's
    diagnostic evidence for a weave decision, not reader-facing catalogue content, but Hard
    Rule 0's text doesn't explicitly carve out diagnostics. Rule on whether it's in scope.
19. **dandwiki.com (BUGS M1)**: unchanged from run #1 — browser-UA HTML reader vs.
    owner-supplied, still a politeness/ToS call.
20. **Permanently hostless roll entries** (Clockwork Angels, Twilight Imperium, HAWX, …):
    unchanged from run #1 — stay as owner-supplied-text candidates or come off the roll?
21. **Paid burst lane**: 500-call cap stands, counter in `state/PAID_BURST.json`. Raise, keep,
    or retire?
