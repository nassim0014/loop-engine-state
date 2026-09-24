# Job: maintenance (daily)

Loop name: `cloud-maintenance`. Read `prompts/_common.md` first; everything there applies.

**Goal:** every repo ends the run with nothing mergeable left waiting, and no red CI that a
small fix could turn green. This job replaces the old review loop.

## Which repos

Every repo in `registry.json` except `loop-engine-state` and archived repos. That includes
repos that are out of the improvement rotation: dependency updates and broken CI still matter
there.

## For each repo

1. List its open PRs with their head branch, author, draft flag and merge state.
2. **Dependency PRs** (author `dependabot[bot]`), oldest first:
   - Merge rules pass: squash-merge. Merging one often puts the next into conflict.
     Dependabot rebases on its own, so move on rather than fighting it.
   - Conflicted: comment `@dependabot rebase`, unless one was posted in the last 48 hours.
     If it has been asked twice already and is still conflicted, close it with a one-line
     comment. Dependabot reopens it if the update is still needed.
   - CI failing: read the failing job's log. If the fix is small and clear, create a
     `claude/loop-maintenance-…` branch from the Dependabot branch, add the fix, and open a PR.
     Merge it when green, then close the Dependabot PR with a link to yours. If the fix is not
     small, leave the PR open and list it in your report.
3. **Agent PRs.** These are head branches starting `claude/loop-`, `claude/auto-improve-`,
   `loop/claude/` or `exp/`:
   - Merge rules pass: mark it ready if it's a draft, then squash-merge.
   - Conflicted: merge the base branch into it, resolve, push, and let CI run again.
   - CI red: find the cause, fix it on the same branch, and push. After two failed fix
     attempts, if the PR is older than 7 days, close it with a comment saying why. Its
     improvement-list item stays open because the tick-off was part of the same PR.
4. **Unmerged work without a PR.** In `kinz-accounting-analysis-*`, the old Kinz routine
   pushed `claude/auto-improve-<date>` branches without always opening PRs. For such branches
   from the last 14 days that have no PR and are ahead of the default branch, open a PR, then
   treat it as an agent PR. Ignore older ones.
5. **Kinz accounting figures wait for Nassim.** In `kinz-accounting-analysis-*`, never merge a
   PR that changes how a reported figure is derived (margins, totals, TVA, anything that ends
   up in the reports), even when CI is green and it has no `hold` label. Add the `hold` label
   and list it in your report. Test-only and doc-only PRs there are fine to merge.
6. **Default branch red.** If the latest CI run on the default branch failed and the cause is
   clear, open a fix PR and merge it when green. Otherwise report it.
7. **No CI on pull requests.** If no workflow in the repo runs on `pull_request`, nothing
   there can ever be merged. Open one PR that adds a new workflow file running the repo's
   existing tests and lint on pull requests. Don't edit the existing workflows. This is the
   one case where adding a workflow is allowed. Merge it when its own checks pass, and name
   it in your report so Nassim knows a new check exists.
8. Leave alone: PRs by humans, `loop/zai/` PRs, and anything labelled `hold` or `do-not-merge`.

Work across repos in parallel where you can. Push fixes everywhere first, then come back to
merge once CI has finished, rather than waiting on each PR in turn. If time runs short, merge
what is ready, stop cleanly, and list what's left. Tomorrow's run continues from there.
Start each run with a different repo so the same ones don't always get cut.

## Report

In the run record, `prs_merged` counts everything you merged, Dependabot included. The
summary names what is still stuck and why. In the final message, use `NEEDS YOU` only for
something an agent cannot fix, such as a secret that has to be set or a paid service that
is down.
