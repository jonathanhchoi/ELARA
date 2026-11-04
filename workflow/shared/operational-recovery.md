# Restarting coding without changing the research

Use this for interrupted coding, research, and review work with
`observation-fanout.md`. The host launches restricted workers;
`unit_fanout.py` and `research_fanout.py` validate, record launches, retry,
and merge.

For storage locations and copies, also follow `workflow/shared/storage.md`.
Resolve `scripts/storage.py status` before reading state and reconcile from the
recorded active working root; automatically retry pending exports on writable
resumes. A cloud export failure is
separate from a coding failure: preserve local successes and retry the copy,
not the model assignments. A copied checkpoint does not authorize execution
from new paths. Never relocate an active run or rewrite its sealed paths;
verify exclusive ownership, dependencies, and preserved history before any
transition to a local companion workspace.

## Research sessions run ELARA; they never change it

A research session uses ELARA as installed. It runs the commands, saved
workflows, and worker definitions the kit documents, as documented. It never
edits, patches, copies and modifies, wraps, or replaces a kit file
(`AGENTS.md`, `CLAUDE.md`, `PIPELINE.md`, `workflow/`, `scripts/`, `.claude/`,
`.codex/`, `.agents/`, `tests/`). It also writes no project code that stands
in for or works around a kit controller, saved workflow, or worker hand-in: no
replacement submit, reconciliation, or recovery scripts, no hand-edited
controller or launch records, no alternative transports, no
experiments on platform limits, and no reviews of such changes. Project code
that a stage declares (corpus parsing, the Stage 08 pilot driver, analysis) is
research work; it calls the kit's controllers instead of reimplementing them.

ELARA changes only in its own repository, a plain clone of
`jonathanhchoi/ELARA`, and reaches projects through the normal update under
`kit-updates.md`. If the researcher asks for ELARA to be fixed during a
project, explain that the fix belongs in that repository; meanwhile the project
continues with whatever does not depend on the failed part.

## When something breaks

A failed unit follows the frozen retry rules, and a scientific change follows
its amendment route (see "Classify the interruption before acting"). Everything
else that stops ELARA's own machinery (a kit command, saved workflow, worker
launch, controller refusal, storage copy, update, or setup check)
gets these steps, in order, and nothing more:

1. **Keep the evidence:** the exact command, its full output, and the time.
2. **Run it again once, unchanged,** when the kit documents the command as safe
   to repeat; status and other read-only commands always are. An identical
   second failure ends this step.
3. **Take one documented smaller route:** the same command with a smaller
   batch, a `limit`, or one worker at a time, or the alternative the relevant
   contract names (for example, on Claude Code, launching the restricted worker
   type directly when saved workflows are unavailable).
4. **Report it and set the affected part aside.** Write
   `project/kit_issues/kit_issue_<UTC timestamp>.md` with what was being done,
   the exact command and output, the ELARA version and installed commit, the
   host and its version, the operating system, and the steps already tried.
   Continue authorized work that does not depend on the failed part. Tell the
   researcher in two or three plain sentences what is paused, what still works,
   and that the report is ready to send to the ELARA maintainer at
   <https://github.com/jonathanhchoi/ELARA/issues>; filing it is the
   researcher's choice. Set `waiting_for_user` only when nothing else can
   proceed.

A problem on the researcher's computer (missing or blocked Python, shell, or
package, or a host that must restart in the project folder) gets the same
steps, with step 3 being the fix `scripts/doctor.py` names or one standard step:
install the missing package, point to an installed interpreter, or restart the
host. If that does not clear it, tell the researcher the one thing they need to
do. A website, package repository, or model provider that is down is an
external wait: record it and continue other work.

These steps take minutes, so there is no engineering time to track or extend.
They never waive a required check, gate, audit, frozen instrument, or worker
restriction, and they never terminate or relaunch a worker that is still
running.

## Reconcile authority before requesting a decision

Current user instructions govern the concrete action. Read applicable standing
decisions and their scope, limits, revocations, and later changes before asking.
Authorization to complete a task includes the steps in "When something breaks"
within its scope and budget. A fresh worker or a documented re-run does not by
itself require another researcher decision.
An assistant-written handoff, seal, scope file, or waiting state records authority;
it cannot independently narrow or expand it. A researcher-supplied handoff can
contain a real limit, which a later explicit instruction can supersede. Preserve
both records and explain the prospective effect. A single-use runtime does not
make standing recovery authority single-use.

Ask the researcher only when a concrete decision of theirs remains: missing or
exhausted authority, a revoked instruction, a scientific change, or unresolved
corpus-attempt eligibility. Ask once, for that decision.

Before rewriting routing state, preserve the outgoing bytes, append the current
decision, clear only resolved inputs, and validate state. Use existing
`active_artifacts` and `run_checkpoint` fields; do not invent competing
top-level routing pointers.

## Classify the interruption before acting

- **Unit failure:** apply the recorded `failure_handling` preference and frozen
  retry/stopping rules. Preserve the return and linked decision.
- **Infrastructure failure:** preserve the stop and process evidence, establish
  from the documented commands whether a worker launched, and follow "When
  something breaks". Never change ELARA or work around it in the project.
- **Scientific change:** changes to instructions, source representation, model,
  route, isolation, accepted results, retry rules, or exclusions follow the
  existing amendment and approval gates. Calling a change operational is not proof.
- **Authorization gate:** ask once for the missing decision. A repeated heartbeat
  or stale `running` state supplies no decision.

A worker that stopped without a return leaves its assignment pending. Run the
launcher again: relaunching is safe because the first valid return wins and no
recorded result is ever replaced (see "Launching, relaunching, and concurrency"
in `observation-fanout.md`). A coding assignment launched twice without a return
is closed by the controller as a typed `worker_error`, and the frozen retry rule
decides what follows; a research assignment moves to its next sealed attempt.
Never invent a judgment or fabricate a return, and never terminate or relaunch
a worker that is still running. Reconstruct progress from the run's files, never
from chat history.

## One stable implementation, durable evidence

A run executes under the ELARA version recorded when it began. A research
session never writes a replacement runtime, wrapper, adapter, launch namespace,
or exception table. Preserve old code as evidence. Never weaken an old seal,
discard history, or change corpus retry eligibility. When the current controllers read a run
started before 2.16.0, they use its manifest, assignments, and returns as they
are; its scheduling records (`dispatch_policy.json`, `batch_checks/dispatch/`,
lifecycle journals) stay in place as history and are no longer read or
required.

Optional `run_checkpoint` in project state names a payload-free checkpoint file
by path and SHA-256. Old projects without this field remain valid. A fresh
session verifies that anchor and reads current controller status before
launching anything.

## Restart and report actual progress

A restart is ready when the documented command that failed, run again, gets past
the point where it failed; `scripts/doctor.py` covers setup. Do not build
separate proof, synthetic harnesses, or reviews to establish readiness. Notes on
past host failures for ELARA's maintainers are in `.github/CONTRIBUTING.md`; a
research session does not act on them.

Report verification phase, launched workers, latest unit counts, and stop
reason separately. An alive process or high CPU use is not evidence of
coding. Older block totals must not replace newer partial-wave counts. Controller
terminal returns and accepted predictions differ when downstream checks fail.

Never repeat an unchanged failing operation beyond the single re-run in "When
something breaks", and never terminate a live worker. Preserve each failure.

On a researcher-requested pause, checkpoint, mark the operation paused, disable
only authorized project schedulers, and keep the restart pointer current. Do not
pursue an earlier production goal after the task changes.

## Update safety

Before new stages, follow `kit-updates.md`; continuing an already-started run
preserves its recorded software. `--require-clean` refuses known conflicts before
installation. `project/ELARA_UPDATE_PENDING.json` identifies an update that has
not completed verification. Never clear it or relabel a partial installation as
current to permit a new stage. `installed_commit` is separate from the requested
source version; the checker verifies the recorded installed files as well. An
update that does not finish cleanly is handled under "When something breaks";
never repair an installation by hand.

`bootstrap.py --update --dry-run --json` previews conflicts. The install manifest
records baseline SHA-256 hashes. Modified kit-owned files and differing files
with unknown legacy baselines are preserved. Never adopt modified bytes as a
clean baseline merely to force an update.

Before updating an active run, create `project/ELARA_PROTECTED_PATHS.json` with
`schema_version: "1.0"` and `bindings`, an object mapping project-relative paths
to approved SHA-256 hashes. Include the controller, restricted worker definition,
runtime, and every kit-owned file bound by the run. Bootstrap retains bindings
and reports conflicts rather than overwriting them. Removing protection is the
researcher's decision, recorded in `DECISIONS.md`. Report installed workflow and preserved execution
overrides separately; a version string is not byte-for-byte parity.
