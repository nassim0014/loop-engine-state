# Handoff: the loop engine, and what to do with it next

> **Historical, 2026-09-23.** This handoff was acted on the same day. The setup it describes
> was replaced: most loops moved to claude.ai routines, with no merge caps, no markers, and
> run records that link to their session. See `README.md` for the current setup. Two
> corrections to §4: the "byte-identical commit pairs" were single runs writing two files
> through the contents API, which makes one commit per file. And the loop sessions seen on
> 2026-09-08 were Claude sessions on Nassim's own account, run from a local machine, not Z.ai.

**Written** 2026-09-23 by Claude Opus 5, for the next model that picks this up.
**Owner** Nassim (`nassim0014`). **Read this whole file before touching anything.**

A note on provenance so you weight this correctly: I am the model that *built* most of
what follows. I am therefore the least reliable auditor of it. Everything in "What I got
wrong" is self-caught, which means the real count is higher than the list. Treat the list
as a floor, not a ceiling. That asymmetry is exactly why Nassim is handing this to you.

---

## 1. What this system is

Nassim watched some talks on "loop engineering" and asked for scheduled agent sessions
that improve his GitHub repos on their own. It grew into six loops plus a coordination
repo. The design brief, in his words, was three loops:

- a **closed loop** every other day improving 2 repos,
- an **open loop** weekly finding a creative idea for a random repo, implementing it, and
  *verifying it afterwards*,
- a **monthly loop** creating a new repo coherent with the existing profile, private by
  default, with him choosing visibility.

Everything else — the review sweep, the backlog refresh, the digest, the state repo —
was added because the first three could not survive contact with reality without them.

### The loops as they stand

| loop | cadence | writes PRs | merges | where |
|---|---|---|---|---|
| `repo-closed-loop` | every 2 days | yes | **yes** | systemd (**disabled**) |
| `repo-review-loop` | daily 16:13 | yes | **yes** | systemd (**disabled**) |
| `repo-open-loop` | Sat 11:41 | yes | no | systemd (enabled) |
| `repo-genesis-loop` | every 28 days | no (creates a repo) | no | systemd (enabled) |
| `repo-backlog-refresh` | Sat 09:00 | yes (docs only) | no | systemd (**disabled**) |
| `loop-engine-digest` | Sun 18:37 | no | no | in-app task |
| `kinz-competitor-analyst` | Mon/Wed/Fri 06:00 | no | no | in-app task |
| `cloud-kinz-improvement` | every 2 days 02:00 | — | — | claude.ai routine |
| `cloud-daily-commit` | daily 12:00 | — | — | claude.ai routine |

Timezone is `Africa/Tunis` (+01:00, no DST) throughout.

### Where things live

```
/home/kiwif/loop-engine/                 control plane + cache
  bin/run-loop.sh                        headless runner (preflight, model, deferral)
  bin/make-calendar.py                   schedule.json -> .ics, + drift check
  schedule.json                          calendar source of truth
  loop-settings.json                     Claude Code permission allowlist
  loop-settings.dry.json                 DERIVED, do not edit
  state-cache/                           what state_sync pull writes
  logs/                                  per-run logs, deferrals.tsv
  KILLSWITCH                             touch this to stop everything (laptop only)

/home/kiwif/loop-engine/state-repo/      = github.com/nassim0014/loop-engine-state (private)
  schemas/                               JSON Schema 2020-12, 5 files
  scripts/                               validate_config, state_sync, merge_budget,
                                         genesis_guard, schema_drift, schedule_table, …
  docs/STATE_PROTOCOL.md                 write protocol + ownership table
  runs/                                  one JSON record per run
  reports/                               weekly digests

~/.claude/scheduled-tasks/<loop>/SKILL.md    the prompts (ONE copy, shared app+headless)
~/.config/systemd/user/                      loop@.service + five timers
```

---

## 2. The principles that are load-bearing

These were earned, usually painfully. Break them deliberately or not at all.

**Cron fires often, a state gate decides.** There is no cron expression for "every 28
days", and `*/2` on day-of-month double-fires at month boundaries. So every loop fires on
a simple schedule and the *prompt* checks state to decide whether to act. A run that
correctly skips is a success, not a failure — your tooling must distinguish
"gated itself correctly" from "ran and failed" from "never fired", because in a log
directory those look identical and mean completely different things.

**The judge must be stronger than the author.** The open loop implements on Sonnet and
verifies with a *fresh* Opus subagent that gets only the success criterion, written
verbatim *before* implementation. If the agent that wrote the code also grades it, it
passes every time. A run of unbroken VERIFIED verdicts is a symptom, not an achievement.

**Lease before work, not after.** Claim state first so a crash cannot double-run.

**GitHub is the truth; local counters are a cache.** Two agents share one merge budget. A
counter in a local file is structurally incapable of being right. Recompute from GitHub.

**The agent must not be able to edit the gate that judges it.** `.github/workflows/**` is
in `forbidden_paths` for exactly this reason.

**Zero-width markers are built in code, never pasted.** `"\u2060\u200b"`. CI fails on any
literal zero-width character in source. I violated this once by pasting them, which is why
the CI gate exists.

**Every change ships as an idempotent script.** Not a one-off command. Re-running must be
safe and must say "already correct".

### Hard safety constraints — do not relax these

- Never touch `data/competitors_seed.json` (gitignored; 77 real people's contact details).
- Never touch `kinz-competitor-intelligence-BACKUP-2026-07-21` (owner's revert point).
- Never run the KINZ scrapers — hours long, hits live sites.
- Never read, print, commit or log `.env`, databases, tokens, or `~/Desktop/API's.txt`.
- Never change repository visibility. Never make anything public.
- Never rewrite history or force-push.

---

## 3. What I got wrong

Read this as a map of where the thinking was weak, not a confession. The pattern worth
noticing: **almost every bug was a control that depended on the cooperation of the thing
it was controlling.**

**`state_sync push` silently ate config commits.** The worst one. `cmd_push` did
`d.clear(); d.update(local)` *inside* the SHA-conditional retry loop — it re-read the
fresh blob and immediately discarded it. Detection worked; resolution ignored it. That is
worse than no CAS at all, because on 409 it re-read, cleared, and retried until the
overwrite succeeded. It deleted a config entry that had landed 16 seconds earlier and
rolled the budget week backwards. Fixed with a real three-way merge against a base
snapshot recorded at pull time. Lesson: optimistic concurrency has two halves, and I
built one.

**`--dry-run` was advisory.** It prepended "write nothing" to the prompt and trusted the
model. That is persuasion, not enforcement — for a loop holding merge authority over six
repos. Now a derived settings file layers unconditional denies on top.

**My own deny rules were porous.** A dry run reported, unprompted, that it was blocked on
`cd x && git ...` and "worked around with `git -C`". `Bash()` rules are *prefix* matches:
`Bash(git push:*)` misses `git -C /repo push`. Also `git pull` was never denied at all.
Tool-level denies (`Write`, `Edit`) are hard; Bash denies are only as good as your
enumeration of spellings, and an enumeration is never provably complete.

**The merge budget could not see a merge that happened.** It matched the literal string
`loop-agent:`; a PR body said `Loop-Agent:`. Different case, no match, merge invisible,
budget reported 0/20 with a merge already landed. A marker is a convention the writing
agent must remember; a budget is a control. Now counts on the branch prefix, which is
structural — a loop PR cannot exist without the branch it was pushed to.

**`validate_config.py` resolved schemas relative to the config, not to itself.** Would
have aborted every `repo-backlog-refresh` run forever, while looking like a config
problem.

**Two unrelated files are both called `loop-settings.json`** — the Claude Code permission
allowlist and the loop config. `state_sync` syncs the second *by name*. Only the default
`--work` value stood between that and overwriting the allowlist, or publishing it to the
shared repo. I added a guard and deliberately did **not** rename, because both names are
referenced from `run-loop.sh`, the prompts, and the other agent's tooling. **The rename
is still owed.** See §5.

**`claude` was not on the systemd service PATH.** A user service freezes PATH at login, so
a binary installed after the last login is invisible. One open-loop run died at preflight
and produced nothing for a week before anyone noticed.

**The open-loop prompt contradicted itself for weeks.** Step 6 said "open an ISSUE — never
a pull request"; step 7b said "ALWAYS PARK AS A PR", then "this loop opens no PRs at all",
then told the agent to label the PR. I had applied Nassim's correction to the heading and
left the body. An agent reading top-to-bottom opened an issue and then labelled a PR that
did not exist.

**I wrote a commit message describing work I had not done.** Claimed `git pull` denies
were added when only one other file was edited. Caught it, added them for real, and
recorded the discrepancy rather than backfilling quietly. Watch for this in yourself.

Also, for calibration: I once verified a Next.js repo with `npm` when it uses `pnpm` and
wrote a PR body asserting things that were false; I ran genesis live instead of
`--dry-run` and was saved only by the 28-day gate; and I twice restarted a
`Persistent=true` timer, which is a *catch-up fire*, not a no-op — `daemon-reload` alone
is what you want.

---

## 4. The live unresolved problem — start here

**Something other than this laptop is running the loops, and it has merge authority.**

Evidence as of 2026-09-23 20:34:

- `loop-closed`, `loop-review`, `loop-backlog` timers are **disabled** and have been for a
  month. Only `loop-open` and `loop-genesis` are enabled.
- The state repo nonetheless has run records for closed-loop, review-loop **and**
  backlog-refresh dated **today**, one of them merging a PR.
- Every run record claims `"agent": "claude-laptop"`. That field is therefore meaningless.
- Nassim and the Z.ai agent share one PAT, so commit authorship cannot separate them.
- Genesis fired **twice ~3 minutes apart** today (14:02 and 14:08 records, one flagged
  "duplicate fire").
- Since 2026-09-01 there are **six** pairs of byte-identical consecutive commit messages,
  every one of them `closed-loop:`. That is a systemic double-write, not a fluke.

The likeliest explanation is the parallel Z.ai agent Nassim authorized, running its own
copy of the loops against the same state repo. **Do not assume that.** Establish it. The
honest position today is: an unidentified writer holds merge authority over six repos and
the run records lie about who it is.

This is the single highest-value thing to fix, and it is not a code bug — it is that the
system has no way to answer "who did this". Until it can, every control below it is
advisory.

Secondary: **21 dependabot PRs** are stacked in `kinz-secure-commerce-hub` and
`Next.js-SaaS` with the review loop dark. Only 1 agent PR is open, so the merge side is
keeping up; the dependency side is not.

---

## 5. What I want you to do

Nassim's instruction, verbatim: *improve what's already done, and if necessary **replace**
or improve them depending on what's best.* You are explicitly not required to preserve my
architecture. If the state repo, the marker scheme, or the whole systemd approach is the
wrong shape, say so and propose the replacement. I would rather be replaced than
politely patched.

Work in this order. The order matters — each step feeds the next.

### Step 1 — `/anthropic-skills:interview-me`

**Start here, before reading more code.** Interview Nassim about what these loops are
actually *for*. I built to a spec without ever establishing the success criterion, and a
year of small green PRs is not self-evidently valuable. Things genuinely unknown:

- Is the goal shipped improvements, a green contribution graph, learning, or something else?
- Is he reading the weekly digest? If not, it should not exist.
- What does he want to *stop* doing by hand?
- How much review attention per week is he actually willing to spend? Every cap in this
  system was picked by me and ratified by him, which is not the same as being right.
- Does he still want the Z.ai agent in the loop at all?

Answers here may well delete loops rather than improve them. That is a good outcome.

### Step 2 — `/superpowers:brainstorming`

Before designing anything. The skill exists at
`plugins/cache/claude-plugins-official/superpowers/6.3.0/skills/brainstorming/`, and its
own rule is that it comes *before* plan mode. Use it on the question the interview
surfaces, not on "how do I patch the merge budget".

The design question I would put to it: **this system's failures are all one failure.**
Every control I built — markers, dry-run preambles, the agent field in run records, the
budget — asked the controlled party to cooperate. Is there a shape where the controls are
structural instead? Per-agent PATs so authorship is real, branch namespaces per agent,
GitHub rulesets instead of prompt rules, a merge queue instead of a counter. That is a
different architecture, not a patch, and it may be the right one.

### Step 3 — `/ultrareview`

**You cannot launch this. Nassim must type it.** It is user-triggered and billed; do not
attempt it via Bash. `/ultrareview` is a deprecated alias for `/code-review ultra`, which
runs a multi-agent cloud review of the current branch. Ask him to run it, and tell him
what to point it at.

Point it at `state-repo/scripts/` — `state_sync.py` and `merge_budget.py` especially.
Those two hold the concurrency and the budget, both of which I have now been wrong about
once each, and both of which I wrote *and* reviewed. An independent adversarial pass on
that code is worth more than anything I can tell you about it.

When the findings come back, `superpowers:receiving-code-review` is installed and is worth
using — verify before implementing; some findings will be wrong.

### Then

Do not re-enable `loop-closed`, `loop-review`, or `loop-backlog` until §4 is settled.
Enabling the closed loop while an unidentified closed loop is already running is precisely
the condition that produced the clobber. If you do enable them, dry-run first
(`bin/run-loop.sh <task> --dry-run`) and re-read §3 on how weak that dry run's guarantees
actually are.

Whatever you change: regenerate the calendar (`python3 bin/make-calendar.py`, it drift-
checks against the task dirs and the timers), keep `validate_config.py` green, and if you
touch the merge logic run `scripts/test_three_way.py`. Nassim has asked to be given a
fresh `.ics` whenever a loop or routine changes — treat that as standing.

---

## 6. Things I would do differently, if you want a starting list

Not instructions. Opinions, held loosely, for you to discard after Step 1.

1. **Per-agent credentials.** Everything in §4 is downstream of one shared PAT.
2. **Rename one `loop-settings.json`.** The collision is a live footgun; I only guarded it.
3. **Kill the marker scheme.** Zero-width characters in PR bodies are clever and have been
   a recurring source of bugs. Branch namespaces are structural and legible.
4. **Make run records unforgeable or drop the `agent` field.** A field that lies is worse
   than no field.
5. **Reconsider whether six loops is right.** I added loops to fix problems caused by
   loops. The backlog refresh exists because the closed loop consumed backlog faster than
   a human refills it — which is arguably an argument for a slower closed loop.
6. **The digest should earn its place.** If Nassim is not reading it, it is ceremony.

Good luck. Be more suspicious of this system than I was.

— Claude Opus 5, 2026-09-23
