# Job: daily commit (every morning, 06:45)

Loop name: `cloud-daily-commit`. Read `prompts/_common.md` first; everything there applies.

**Goal:** Nassim's GitHub contribution graph has something every day, and each thing is a
real improvement, not filler. It runs at 06:45, after the night's jobs, so on most days
something has already landed and there is nothing to do.

## Steps

1. Today means today's date in Africa/Tunis.
2. **Did anything land today?** For each registry repo except `loop-engine-state`, list the
   default branch's commits since today 00:00 Tunis time (23:00 UTC the day before). If any
   commit's author login is `nassim0014`, stop. Record `status: skipped` with the commit you
   found, and finish.
3. **Otherwise make one small, real fix.** Take the rotation repo (`worked_by` `claude`) whose
   default branch was updated longest ago. Prefer the smallest open item in its
   `docs/IMPROVEMENTS.md`. If none is small, fix one real small thing you find: a wrong
   statement in the docs, a missing docstring on a public function, or a missing test for an
   untested branch. No whitespace churn, no renames for their own sake.
4. Do it on a `claude/loop-daily-…` branch, open the PR, and merge it when CI passes and the
   merge rules hold. If CI is still running after 20 minutes, leave it for maintenance and say
   so.
