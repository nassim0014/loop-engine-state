# Job: creative idea (Saturday)

Loop name: `cloud-creative`. Read `prompts/_common.md` first; everything there applies.

**Goal:** once a week, add one new, useful idea to one repo. The work is judged by a separate,
stronger agent against a goal you write before you start, because an agent that grades its own
work passes every time. This job replaces the old open loop.

## Steps

1. **Pick a repo.** Choose at random from the rotation repos whose `worked_by` is `claude`.
   Avoid last week's pick, which you can find in the latest `runs/*-cloud-creative.json`.
2. **Pick an idea.** Read the repo properly. Think of 3 ideas that would make it clearly more
   useful or more impressive to someone looking at it: a feature, a command-line tool, a chart
   or report, a link to one of Nassim's other repos, a benchmark, a runnable demo. Choose one
   that fits in a single PR, can be tested, and needs no new secrets or paid services.
3. **Write the goal first.** Before any code, create
   `experiments/<YYYY-MM-DD>-<repo>-<slug>.md` in the state repo. It holds the idea in two
   sentences, and 3 to 6 **success checks**. Each check is something a stranger can confirm
   by running a command or reading a file, for example "`python -m x --demo` prints a table
   with 3 rows" or "`pytest tests/test_x.py` passes". Commit and push it now. The commit
   time proves the goal was set before the work.
4. **Build it** on a `claude/loop-creative-…` branch, with tests. Open the PR and link the
   experiment file in the body.
5. **Have it judged.** Start a fresh subagent with the Agent tool and `model: "opus"`. Give it
   only the repo path, the branch name, and the experiment file's text. Tell it to check each
   success check by actually running it, and to reply with PASS or FAIL per check with
   evidence, then an overall `VERIFIED` or `NOT VERIFIED`. Don't give it your own opinion of
   the work.
6. **Record the verdict.** Append the judge's verdict and evidence to the experiment file,
   then commit and push.
   - `VERIFIED`, CI green and merge rules pass: merge.
   - `NOT VERIFIED`: make one fix attempt, then ask a *new* fresh judge. If that is still not
     verified, close the PR with the verdict as a comment and keep the branch.
