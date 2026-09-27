### Resolved by run #65 (2026-09-26 daily maintenance, evening; sweep65)

*Found by the run itself and by sweep65 (16 batches, all 119 modules, `sweep_plan.missing('run65')
== []`), fixed in the same shift, so none of these sat in `## Open`. Each was re-read against
source before it was fixed, and each change that a net can hold got an attack that was watched
going red. Export commit: the run #65 push (see HANDOFF.md's run #65 entry).*

- **[M126 — RESOLVED 2026-09-26, run #65] THE 09-26 MUTATION PASS HAD verify_math AND drill OFF
  AS GATES FOR TWO OF ITS THREE TARGETS, AND ITS LOG COULD NOT SAY WHY.** Part way through the
  assay section both gates drifted red on clean code. verify_math's red row named the leak:
  `silent:tuning.py:ollama_up`. `standards.check()` asks `tuning.regime()`, which asks Ollama
  `/api/tags` with a 6s timeout whenever the cloud pool is not answering well enough. Under the
  GPU load from prose and the pipeline that call sometimes times out, and the class was not in
  `_THIRD_PARTY_CLASSES_VM`. The drifted red baseline was then carried into prose_gate and
  escalation (the baseline dict is shared across targets and refreshed in place), so both ran
  about 14 hours with only the import gate killing. The log printed "WAS RED AT THE BASELINE"
  beside a launch signature reading 0 FAILED / 0 BREACHED, and the drill's breach rows carried
  only net names.
  - **REPRODUCED:** verify_math with Ollama unreachable AND `_answering_buckets` forced to 0 gives
    exactly `FAILED a third-party abstention only ever covers the classes it was granted for:
    got ['live machine and network state -> silent:tuning.py:ollama_up']`. Ollama down alone is
    green, because regime() answers "cloud" first. The drill half did NOT reproduce under either
    condition, so its class is still unknown.
  - **FIX:** `silent:tuning.py:ollama_up` is granted under `_LIVE_STATE_VM` (only that class;
    `tuning.py:ollama-host` reads config.yaml and still reddens), and the grant ratchet now reads
    note sites from tuning.py as well. `mutate._row_ids` appends the drill's indented reason line
    to each BREACHED row, so the next drift names its probe and class. The per-target "red at
    baseline" line now says when the red was carried in from an earlier target's drift.
  - **PROVEN:** the forced repro is green after the grant. New net "a drill breach recorded by a
    mutation pass carries the reason, not only the net's name": HELD on the fix, RED with the
    reason capture disabled (`drill.py --prove drill_mutation ... --revert`).
- **[M127 — DIAGNOSED 2026-09-26, run #65; the fix is the owner's, order `573ab7b04b6f`] THE
  PUBLISH DAEMON CANNOT SEE gh.exe BECAUSE IT LIVES IN THE CLAUDE APP'S VIRTUALISED AppData.**
  Every daemon push since 2026-09-14 ended PUSH HELD with gh.exe "No such file or directory"
  while every session pushed. Cause: Claude Desktop is MSIX-packaged, and its child processes'
  AppData writes land in `AppData\Local\Packages\Claude_pzs8sxrjxfjjc\LocalCache\...`. gh.exe and
  gh's `hosts.yml` were installed from a session, so they exist only there. The keeper starts
  from the Startup folder, outside the app, and sees neither. A probe launched through WMI
  (outside the app) reported isfile=False for both ordinary paths and True for the package-store
  copy; the same probe from a session reported True. Run #61's AppContainer lead is ruled out
  (every PUSH HELD reads appcontainer=False restricted=False).
  - **CHANGED:** `publish._credential_probe` now adds a `package store:` line
    (`_package_store_facts`) naming this case. Display only; it gates nothing. Tested from inside
    and outside the app. sweep65 batch10 found it misreported a Roaming path with LOCALAPPDATA
    unset; fixed the same shift.
  - **OPEN, OWNER:** install gh from an ordinary terminal (`winget install GitHub.cli`,
    `gh auth login`, `gh auth setup-git`), or drop the gh helper line from `~/.gitconfig` so Git
    Credential Manager takes over. Until then the daily run's push is the only one that lands.
- **[M128 — RESOLVED 2026-09-26, run #65] THE CATALOGUE MERGE COULD DROP A UNIQUE ENTITY TO KEEP
  A DUPLICATE.** In `write_record_catalogue`, disk rows of a duplicated name that could not pair
  one to one went into one `unpaired` list, and `unpaired[:max(m-k, 0)]` kept whichever came
  first in dict order. So a disk row whose (name, type, description) the fresh cast does not carry
  at all could be dropped while a second copy of a row the fresh cast already holds was carried.
  (sweep65 batch03, reproduced in a scratch copy.)
  - **FIX:** rows with no fresh counterpart go to the front of the carry list. The COUNT is
    unchanged. The auditor's proposed fix (carry every such row unconditionally) was not taken:
    a wiki that rewords a duplicated name's descriptions would grow the record by the whole group
    on every re-catalogue. The remaining trade-off is OWNER question 1 of order `beb7db270826`.
  - **PROVEN:** two new cases in "the catalogue merge does not key entries on name alone": (5) the
    unique row survives, and survives a re-merge, at the same count; (6) rewording both rows of a
    duplicated name keeps the cast at two. RED with the old order restored, RED with the naive
    carry-everything fix, HELD after.
- **[m — RESOLVED 2026-09-26, run #65] three small ones from sweep65:** verify_math's only bare
  `assert` (`_b5_wiki_source_nonfandom_shortcircuit`, stripped under `-O`) is an explicit raise
  (batch02); a present-tense comment in `wh40k.main()` said all 55 axes are 'unattributed' when
  order `82fc93f056d4` has tagged every one (batch03); `_package_store_facts`'s Roaming edge
  (batch10, above).

