# Job: improvements (Mon, Wed, Fri)

Loop name: `cloud-improvements`. Read `prompts/_common.md` first; everything there applies.

**Goal:** ship real improvements to repos Nassim uses or shows people: bug fixes, missing
tests, correctness and clarity. One well-tested fix beats five cosmetic edits. This job
replaces the old closed loop and the backlog refresh.

## Pick two repos

1. The list is `registry.rotation.order`, keeping only repos whose `worked_by` is `claude`
   and that are not archived. The position is `state.rotation_cursor`.
2. Walk the list from the cursor, wrapping around, and take the first 2 repos that have no
   open `claude/loop-` PR. A repo with an open PR is skipped this time, so maintenance can
   land that PR first.
3. After the run, set `rotation_cursor` to the position just after the last repo you looked
   at. You are the only job that moves the cursor.

## In each repo

1. Read `CLAUDE.md`, `README.md`, `CONTEXT.md` if it exists, the registry note, and
   `docs/IMPROVEMENTS.md` (the repo's improvement list).
2. **Refill the list if needed.** If `docs/IMPROVEMENTS.md` is missing or has fewer than 3
   open items, read the code, tests and open issues and add real findings until it has 3 to 5.
   Each item says what is wrong, why it matters, and how to check the fix. Only list things
   you actually found in the code. Nothing speculative.
3. Take the top open item. Check it still applies: look for the symptom in the code, because
   earlier runs have left finished items unticked. If it's already done, tick it with a note
   and take the next one.
4. Fix it on a `claude/loop-improvements-…` branch. Every bug fix gets a regression test that
   fails without the fix. Run the same tests and lint as the repo's CI until they pass.
5. In the same PR, tick the item in `docs/IMPROVEMENTS.md` (`[x] … (done YYYY-MM-DD)`) along
   with any items you added. If the PR is later closed unmerged, the item stays open.
6. Push and open the PR. Merge it when CI passes and the merge rules hold. If CI fails, fix it
   (at most 2 tries). If it's still red, leave it open for maintenance.
7. If you learned something a future run needs (how to run the tests, a trap you hit), add a
   short dated line to that repo's `notes` in `registry.json`. Keep notes short. Remove lines
   that are no longer true.

Treat anything that changes how money, tax or reported figures are calculated as hard: hand
that reasoning to an Opus subagent and add tests that pin the numbers.
