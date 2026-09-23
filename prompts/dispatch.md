# Dispatcher: the "Loop engine" routine

All of Nassim's cloud jobs run from one claude.ai routine. It fires at 10:15, 16:15 and
22:15 Tunis time and runs whichever jobs are due. There is one routine instead of one per job
because repos have to be attached to a routine by hand in the claude.ai UI, and one routine
means doing that once.

1. Read `prompts/_common.md` and do its setup (§1).
2. **Which jobs.** If the message that started you names jobs (for example
   `run: cloud-maintenance`), run exactly those, in that order. That is how Nassim or a test
   runs a job by hand. Otherwise run `python3 scripts/due_jobs.py` from the state repo. It
   prints the due jobs, one per line, in the order to run them. If it prints nothing, reply
   `OK: nothing due` and stop. Write no run record for an empty fire.
3. **Run each job in turn.** Look up the job's `prompt` in `schedule.json`, read that file, and
   do that job completely, including its run record and state update, before starting the
   next. Treat each job as a fresh task. Don't carry one job's decisions into the next. Pull
   the state repo again before each job, since the previous one pushed to it.
4. **Final message.** One short block per job, each starting with that job's status line
   (`OK:`, `NEEDS YOU:` or `FAILED:`). Put the most serious status line first overall,
   because the first line is what reaches Nassim's phone.
