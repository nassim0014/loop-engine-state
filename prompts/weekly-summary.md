# Job: weekly summary (Monday morning)

Loop name: `cloud-weekly-summary`. Read `prompts/_common.md` first; everything there applies.

**Goal:** a short, honest weekly report that Nassim reads on his phone. It tells him what
shipped, what broke, and whether every job actually ran. This job changes nothing in the
work repos. It only writes the report to the state repo.

## Collect (window: the last 7 days)

1. **Run records.** Read `runs/*.json` in the window, grouped by loop.
2. **Did every job run?** For each enabled loop in `schedule.json`, work out how many times its
   cron (Africa/Tunis time) should have fired in the window, and compare that with its run
   records. Each expected run is one of: ran (success or partial), skipped on purpose, failed,
   or **missing** (no record at all). Missing is the important one, because it means the job
   never fired or died before writing anything. For `repo-genesis-loop`, a skipped run on a
   non-acting day is correct. Skip `cloud-dispatch` itself: it only starts the other jobs and
   writes no record of its own.
3. **Per repo** (all registry repos except `loop-engine-state`, read only):
   PRs merged in the window, open PRs by kind (Dependabot, agent, human), and whether the
   latest CI run on the default branch is green.
4. **Creative judge.** Read `experiments/*.md` for this week's verdict. Also count how many
   `VERIFIED` verdicts in a row there have been. A long unbroken streak is suspicious,
   because it suggests the judge is too easy.
5. **Next week.** The next two rotation repos, from `state.rotation_cursor`.
6. **Repos not attached.** Compare the registry with the folders in `/home/user`. Any registry
   repo that is missing, such as a new repo from genesis, is invisible to every job until
   Nassim attaches it to the Loop engine routine. If one is missing, say so with `NEEDS YOU`.

## Write

1. `reports/weekly-<ISO-year>-W<week>.md`, at most 60 lines, with these sections: Shipped (merged PRs by
   repo, one line each, with links), Broken or stuck, Jobs that did not run, Creative verdict,
   Next week. Plain words.
2. Your run record and state, as in the shared rules. `status` is `success` even if the week
   went badly, because the report is the success.

## Final message

This is the weekly summary Nassim receives. Start with `OK: weekly summary W<nn>`, or
`NEEDS YOU:` if something needs him. Then at most 6 bullets: merged count, the most
important thing shipped, what's broken, any job that didn't run, the creative verdict, and a
link to the report file on GitHub.
