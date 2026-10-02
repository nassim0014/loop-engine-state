---
description: Work one item off the improvement backlog, end to end, as a PR.
---

Run one improvement cycle on this repository. **One item, one PR, then stop.**

## 0. Throttle

```bash
gh pr list --state open --json number,title
```

If **3 or more** PRs are already open, stop. Post nothing, change nothing. Report:
"N PRs open, skipping this cycle" and list them.

The bottleneck here is review, not authorship. A backlog of unreviewed PRs is
worse than no PRs — it guarantees merge conflicts and means nothing is actually
getting looked at.

## 1. Sync and orient

```bash
git checkout main && git pull
./venv/bin/pytest -q && ./venv/bin/ruff check .
```

If `main` is already failing, that *is* this cycle's item. Fix it and skip to
step 3.

Read `docs/IMPROVEMENTS.md` and `CLAUDE.md`.

## 2. Pick

Take the **top unblocked item under "Now"**. Don't shop around for an easier one.

If it's larger than a single reviewable PR, split it in the backlog file first,
take the first piece, and leave the rest ranked.

If while working you notice something unrelated, **add it to the backlog rather
than fixing it**. Scope creep is what makes a PR unreviewable.

## 3. Work it

Branch: `<type>/<short-slug>` — `fix/`, `perf/`, `test/`, `refactor/`, `docs/`.

Follow the rules in `CLAUDE.md`. In particular:

- Tests before behaviour changes on any database write path.
- **Prove the test would have caught the bug.** Reintroduce the old behaviour,
  watch it fail, restore. A test that only ever passed proves nothing.
- Measure before claiming a speedup, and quote the number. If you can't measure
  it, say that explicitly in the PR rather than implying a result.

## 4. Verify

```bash
./venv/bin/pytest -q && ./venv/bin/ruff check .
```

Both must pass locally before pushing. If they don't, fix or abandon — do not
open a PR hoping CI disagrees.

## 5. Ship

Commit, push, open a PR. The body states: what was wrong, what changed, how it
was verified, and **what was not covered**. Write for someone who wasn't there.

Wait for CI. If green and the change is contained, merge it and delete the
branch. Leave it open and say why if any of these hold:

- It changes a database write path in a way tests don't fully pin down.
- It touches scraper behaviour (can't be verified without a live run).
- It needs a decision that is the owner's, not yours — anything about what data
  is retained, published, or deleted.
- CI is red for a reason you don't understand.

## 6. Close the loop

Move the item to *Done* in `docs/IMPROVEMENTS.md` with its PR number. Add
anything new you noticed. Commit that on the same branch as the work.

Then **stop.** One item per cycle. The point is a steady rate the owner can
actually review, not maximum throughput.

## Report back

Four lines, no preamble:

- Item worked, and the PR link
- Merged / left open, and why
- Test and lint result
- What's now at the top of the backlog
