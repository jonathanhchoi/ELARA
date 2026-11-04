# When ELARA's machinery fails

Use this page when a kit command, saved workflow, worker launch, controller
refusal, storage copy, update, or setup check stops work. A failed coding unit
is not this: it follows the frozen retry rules and the `failure_handling`
preference. Nor is a scientific change: changes to instructions, source
representation, model, route, worker isolation, accepted results, retry rules,
or exclusions follow their amendment gates, whatever they are called.

## Research sessions run ELARA; they never change it

A research session runs the kit's commands, saved workflows, and worker
definitions as documented. It never edits, patches, copies and modifies, wraps,
or replaces a kit file (`AGENTS.md`, `CLAUDE.md`, `PIPELINE.md`, `workflow/`,
`scripts/`, `.claude/`, `.codex/`, `.agents/`, `tests/`), and writes no project
code that stands in for a kit controller, workflow, or worker hand-in: no
replacement submit, reconciliation, or recovery scripts, no hand-edited launch
records, no alternative transports, no experiments on platform limits, and no
reviews of such work. Project code a stage declares (corpus parsing, analysis)
calls the kit's controllers; coding runs need none (`scripts/coding_run.py`).
ELARA is fixed only in its own repository and arrives by update; if the
researcher asks for a fix during a project, say so and continue whatever does
not depend on the failed part.

## When something breaks

Take these steps, in order, and nothing more:

1. **Keep the evidence:** the exact command, its full output, and the time.
2. **Run it again once, unchanged,** when the kit documents it as safe to
   repeat (read-only commands always are). An identical failure ends this step.
3. **Take one documented smaller route:** a smaller batch, a `limit`, one
   worker at a time, or the alternative the relevant contract names (on Claude
   Code, launching the restricted worker type directly).
4. **Report it and set the affected part aside.** Write
   `project/kit_issues/kit_issue_<UTC timestamp>.md` with what was being done,
   the exact command and output, the ELARA version and installed commit, the
   host and version, the operating system, and the steps tried. Continue work
   that does not depend on the failed part, with that part `paused`, and tell
   the researcher in two or three plain sentences what is paused, what still
   works, and that the report is ready to send to
   <https://github.com/jonathanhchoi/ELARA/issues> if they choose. Use
   `waiting_for_user` only when nothing else can proceed.

A problem on the researcher's computer (missing Python or package, a host that
must restart in the project folder) gets the same steps, with step 3 being the
fix `scripts/doctor.py` names; if that fails, tell the researcher the one thing
to do. A website, package repository, or model provider that is down is an
external wait: record it, lower worker concurrency once if a provider is
refusing work, and continue other work.

These steps take minutes; there is no engineering time to track. A restart is
ready when the failed command gets past the point where it failed; build no
separate proof, harness, or review. The steps never waive a check, gate, audit,
frozen instrument, or worker restriction, never change retry eligibility, and
never stop or relaunch a worker that is still running.

## Resuming

Reconstruct progress from the run's files, never chat history: state, run
manifest, ledgers, returns, and a recorded `run_checkpoint` (verify its SHA-256
first). A live process is not coding progress; report verified counts, launched
workers, and the stop reason separately. A worker that stopped without a return
leaves its assignment pending: run the launcher again, since the first valid
return wins. A run continues under the ELARA version recorded when it began.
Authority to complete a task includes these steps; ask only for a concrete
decision of the researcher's (missing or revoked authority, a scientific change,
unresolved retry eligibility), once. Before rewriting state, keep the outgoing
bytes and clear only resolved inputs. After a requested pause, do not resume an
earlier goal once the task has changed.
