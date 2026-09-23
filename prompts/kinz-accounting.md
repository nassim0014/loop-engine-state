# Job: Kinz accounting improvement (Sun, Tue, Thu)

Loop name: `cloud-kinz-improvement`. Read `prompts/_common.md` first; everything there applies.

This is the old "Kinz repo — improvement pass" routine (`trig_01FTYzTF5d7GsEuQZ3sxuebP`, deleted
2026-09-23), brought into the loop engine. The repo is
`nassim0014/kinz-accounting-analysis-20260623-102129`, at
`/home/user/kinz-accounting-analysis-20260623-102129`. It is a private repo of Odoo-derived
financial reporting for a Tunisian cosmetics business.

Start by reading `CLAUDE.md` at the repo root. It documents the read-only guarantee, the
pipeline order, which paths are generated, and the code conventions. Follow it.

## Model budget

Escalate to an Opus subagent when the work involves:
- reasoning about financial or tax correctness (TVA, margins, reconciliation, accrual
  treatment), where a wrong answer would look plausible,
- a bug whose cause you cannot pin down after a focused attempt, or one spanning several files,
- a change to how a reported figure is derived, or any change touching the read-only guarantee.

Do not escalate for reading the repo, running tests, doc updates, lint fixes, adding a test for
a bug already understood, or deciding there is nothing to do. Note in your report which model
did what.

## This run

1. Read the repo and run the checks:
   `pip install -r requirements-dev.txt`, then
   `pytest && ruff check . && python3 scripts/verify_readonly.py`.
   Steps 2 and 3 of the pipeline (`scripts/process_data.py`, `scripts/generate_reports.py`)
   run offline against the committed extract, so use them to verify changes. Step 1 needs
   `ODOO_API_KEY` and network access. Do not run it.
2. Find what would genuinely improve the repo: real bugs (wrong maths, silently dead code
   paths, joins that produce blank columns), generated output that contradicts the data behind
   it, documentation that no longer matches the code, missing tests on logic that matters, and
   CI gaps.
3. Pick the 1 to 3 highest-value items. Depth over breadth: one well-tested correctness fix
   beats five cosmetic edits.
4. Implement them, escalating as above. Add a regression test for every bug fixed. Re-run
   pytest, ruff and the read-only verifier until all pass.
5. Commit to a `claude/loop-kinz-<YYYYMMDD>-<slug>` branch, push, open the PR, and merge it when
   CI passes and the merge rules in `_common.md` hold. A change to how a reported figure is
   derived is the exception: leave that PR open and say `NEEDS YOU` with one line on what
   changes in the numbers.

## Hard boundaries

- Odoo access is READ-ONLY. Never add or run anything that writes, creates, unlinks, posts,
  confirms or cancels in Odoo. Never weaken or bypass `assert_read_only`, and never remove
  entries from `FORBIDDEN_METHODS`.
- You may change: `scripts/`, `automation/`, `tests/`, `CLAUDE.md`, `README.md` (outside the
  METRICS markers), `requirements*.txt`, `pyproject.toml`. Workflows follow the merge rules.
- Do NOT hand-edit generated content: `data/`, `analysis/`, `compliance/`, `recommendations/`,
  `visualizations/`, `audit/`, `EXECUTIVE_SUMMARY.md`, or the README block between the METRICS
  markers. These belong to the monthly pipeline. If their content is wrong, fix the generator
  that produces them, and do not commit regenerated data or report files, because that would
  churn the monthly diff. Run `git checkout --` on any generated file your verification run
  modified before committing.
- Never modify or disable the monthly analysis workflow's schedule.
- Do not invent financial figures, compliance claims or Tunisian tax rules. Anything in
  generated reports must be derived from `data/processed/financial_metrics.json`.

## If there is nothing worth changing

Say so and push nothing. An empty run is a correct outcome. This job exists to improve the
repo, not to produce a change every two days. Don't make busywork, cosmetic refactors or
speculative abstractions to justify a run.
