# Handoff Log — the maintenance-pass run journal

*One dated entry per maintenance run, newest on top. This is the RUN LOG only; the project's
deep engineering history, doctrine, and architecture live in `handoff/HANDOFF.md` (decision
recorded run #1: two files, two jobs — a run journal and a reference book do not share a
writer). Bug ledger: `BUGS.md`. Priority queue for the next run: `NEXT_STEPS.md`. The working
tree is not itself a git repo — commits happen through `src/publish.py --push` into the export
repo (`PANSCRIPTUM_EXPORT`), so "commit hash" below means an export-repo hash.*

---

## 2026-08-23 — Run #1, triggered by commit b16f631

**Flagged for human review:** dandwiki HTML-reader decision (BUGS M1); disk at ~5 GB free
(BUGS M2); permanently hostless roll entries; `identity.adjudicate` deletion proposed for
next run (NEXT_STEPS 6); `assay.assay()` gained an OPTIONAL `weights=` kwarg (additive,
default None, no caller broken — noting per the signature guardrail).

**Resolved this run:** the full round-1 + round-2 audit findings — see BUGS.md's paper-trail
section for root causes and commits. Headlines: the two-writer contract got its second,
direction-aware writer after `write_record` silently discarded the doc-ingest's first finds;
`silence.replace_retry` now guards every reader-raced state file; evidence caches self-heal;
custodes' shared-WEIGHTS mutation localized; the terminal's invisible `--dim` labels fixed;
`config.yaml` writes atomic; endpoint cache writes locked.

**New machinery this run:** the maintenance framework itself (`MAINTENANCE.md`, this journal,
`BUGS.md`, `NEXT_STEPS.md`, hourly scheduled task `panscriptum-maintenance`); the supervisor
keeper thread; `write_record_catalogue`; verify_math §18c (merge directions) → 272 checks;
`module_index.py` + `handoff/MODULE_INDEX.md`; `handoff/PHASE_CONTRACTS.md`; descriptive
export commit messages; `ingest_doc.py` (owner-supplied books → corpus, `doc:` host sentinel).

**Optimizations (measured):** standards.check ~146 PowerShell spawns → one 3s-TTL
enumeration, 2.3s/call; chain.harvest 900MB re-parse → incremental index, 3.1s warm;
coverage.measure full-corpus deserialize → mtime cache, 15.6s→6.9s warm; completeness
~1,300 fandom calls per foreman round → 12h disk cache; publish sync ~2GB/day of
unconditional copies → mtime short-circuit; dashboard library/watch on a 5s poll → 30s TTL;
by_axis 3× regex redundancy hoisted; chain per-sentence 54KB DESIGNATORS reload → loaded
once; zstd 19→10.

**Repo health:** verify_math 272/272 · 88/88 modules compile+import · pyflakes clean ·
allsweep 0 bad subsystems · standards ~24-25/37 met (reds: evening pool tide, deliberately
unsatisfiable floors, and items in BUGS.md) · open bugs: 2 major (both human-gated),
2 minor, 3 watching.

**Notes:** the scheduler floors recurring tasks at hourly — that IS "as often as possible"
here; the overlap guard plus the repo's continuous machinery covers the gaps. The evening
free-tier pool is the throughput ceiling tonight; the midnight window reset feeds the
deferred backlog, the charter regression, and the Dragonlords miner without supervision.
