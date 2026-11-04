# Restarting coding without changing the research

Use this for interrupted coding, research, and review work with
`observation-fanout.md`. The host still launches
restricted workers; `unit_fanout.py` still validates, retries, and merges.
`scripts/fanout_lifecycle.py` is a provider-neutral journal, not a launcher,
scientific validator, source of retry permission, or replacement model route.

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
in for or works around a kit controller, dispatch helper, saved workflow, or
worker hand-in: no replacement submit, reconciliation, or recovery scripts, no
hand-edited controller or dispatch records, no alternative transports, no
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
launch, controller or dispatch refusal, storage copy, update, or setup check)
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
restriction. They never terminate a live worker or relaunch a worker whose
outcome is unknown; a run whose outcomes the documented commands cannot settle
goes to step 4.

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

`scripts/recovery_decision.py` is needed only where a documented command takes
its request file: the paused-run migration and resume commands below. Its
`decide(root, request)` API and `--root ... --request ...` CLI are read-only.
Requests identify the action, run, scientific binding hash, all applicable
researcher instructions (source path, SHA-256, exact quote, scope), current
restrictions, and evidence references. The parent must accurately
interpret those instructions and include every applicable limit; hashing a quote
cannot establish its meaning or create consent. Do not supply a permission
boolean or treat a helper's result as independent research authorization.

- `proceed`: the action is covered and its required operational evidence exists.
- `repair`: required operational evidence is missing; dispatch remains stopped.
  Follow "When something breaks"; do not build the missing evidence with new
  code or reviews.
- `wait_external`: record a verified external capability problem and preserve
  the checkpoint. Do not relaunch unchanged work or recreate monitoring unless
  requested. A timeout while a handle remains live is still a live operation.
- `request_user`: a concrete researcher decision remains, such as missing or
  exhausted authority, a revoked instruction, scientific change, or unresolved
  corpus-attempt eligibility. Ask once for that decision and its actual source.

Required evidence is separate for offline boundary tests, live capability,
independent review, activation review, unchanged scientific bindings, preserved
history, exclusive ownership, and reconciled attempts. The helper verifies
hash-bound summary receipts; their producers must derive each finding from the
actual operation and preserve underlying evidence. It does not validate research
results or allocate retries. An adapter must enforce the decision before its
own dispatch checks, not merely display it in a report.

Before rewriting routing state, preserve the outgoing bytes, append the current
decision, clear only resolved inputs, and validate state. Optional
`recovery_decision` binds request/result references so the validator can reproduce
the decision and reject stale routing. Use existing `active_artifacts` and
`run_checkpoint` fields; do not invent competing top-level routing pointers.

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

No return means unknown finality unless affirmative evidence proves otherwise.
An unacknowledged launch intent may have reached the host. Never silently
relaunch that attempt, invent a no-judgment finding, fabricate a return, or
allocate a retry from absence alone. Explicit exceptions remain scoped to the
units and attempts the researcher approved.

Distinguish host acceptance of a launch from execution of the research assignment.
Prevent duplicate execution; do not impose a lifetime limit on worker launches.
Correct an invocation when affirmative evidence shows it never ran. If the worker
has terminated before admission and before reading scientific inputs, preserve
the native failure evidence and replace it under the existing task authority.
An accepted launch remains in history. Once scientific execution has begun,
the frozen controller's retry and stopping rules govern any further attempt.

For ticketed runs, the parent records verified failure before admission as
`startup_failed` through `fanout_dispatch.py reconcile --host-evidence`.
The evidence must establish native termination without successful admission
or scientific-input access; missing files alone cannot establish this.
The helper also requires no start marker or return. Reconcile and close the
session, then obtain a new ticket for the still-pending assignment and attempt.
The old ticket stays closed, and the original launch and failure are preserved.
`never_started` remains reserved for a launch the host did not accept.
Do not restart a live worker or one whose execution status is unresolved.
Investigate that uncertainty using authorized operational evidence, continue
independent work where permitted, and ask only if a researcher decision remains.

## Opt-in migration to continuous scheduling

An installed update never converts an existing parallel run implicitly. A run
without a scheduling policy keeps its original scheduler, including its wave
barriers. To adopt continuous scheduling, the researcher must explicitly choose
migration for the named paused run. Migration itself does not authorize workers
or resume a researcher-requested stop.

First run `python scripts/fanout_dispatch.py migrate --run-dir <run-dir>
--kind coding|research --owner <native-session-id> --host codex|claude
--capacity <available-worker-slots> --dry-run`. Inspect the exact source seals,
frozen scientific and operational bindings, accepted batch size, concurrency and
budget restrictions, all accepted or unknown native launches, returns, retries,
and checkpoint lineage. Obtain independent review of the migration evidence.
Require quiescence and resolved finality; a missing return is not proof no worker
started. Preserve all old sealed bytes and raw records, and add operational
migration evidence instead of rewriting a seal or old assignment.

The activation command supplies `--request <migration-request-json>
--request-root <project-root>` using the existing `recovery_decision.py` request
contract. It requires action `operational_migration` and the exact `run_id`,
`binding_sha256`, and `candidate_sha256` from the dry-run plan; inspect and approve
those concrete bytes, not an unconstrained future change. The migrated run stays
paused. A separate `resume_dispatch` request for the same candidate is required
on `open-session --request <resume-request-json> --request-root <project-root>`;
migration approval alone never starts a worker. If the frozen instrument or
preregistration fixes scheduling, concurrency, scientific worker instructions, or another
changed scientific binding, route through its amendment and reapproval process.
Do not reclassify that change as infrastructure repair. An operational start guard
must leave the scientific assignment and its visible coding prompt unchanged.
Record original and new implementation hashes and the compatible dispatch policy,
then test interruption, duplicate admission, and unknown-native-outcome behavior
with synthetic assignments before any authorized real-data resume.

For a continuous run interrupted under an old native-session owner, first preserve
and reconcile the exact old tickets and native evidence. Preview ownership recovery
with `python scripts/fanout_dispatch.py recover-session --run-dir <run-dir>
--expected-owner <old-owner> --owner <new-owner> --dry-run`. Its candidate binds the
old session, both owners, scientific bindings, adapter, policy, and current event
head. Activation uses `--request <reviewed-resume-request> --request-root <project-root>`
with action `resume_dispatch` for that exact candidate. It requires every prior
attempt's finality to be resolved; time elapsed, an absent process, or an empty return
path cannot satisfy that condition. Recovery closes the old operational session;
it does not launch or reassign work. Open a new session only under the recorded
resume authority and current controller eligibility.

Dispatch checkpoints and closed-session segments preserve the operational record
without rewriting scientific source seals. Keep their hashes and lineage with the
run's recovery evidence. The helper's average registered workers and attempt-rate
metrics measure recorded start-to-return intervals; they do not establish active
model inference, token throughput, or direct native-worker liveness.

Provider backoff is a separate admission constraint. Preserve an observed Retry-After
as `reconcile --throttled --retry-after-seconds <observed-seconds>`; without a known
delay, `--throttled` keeps admission blocked until new provider-availability evidence
is supplied to `resolve-backoff --evidence-sha256 <hash>`. Use the existing run and
owner in both commands. Neither elapsed guesswork, a website's HTTP 429, a null
workflow result, nor a raw exception string establishes model-provider availability.
Resolving backoff never waives an outstanding attempt, ownership, or researcher stop.

## One stable implementation, durable evidence

A run executes under the ELARA version recorded when it began, or under a
documented migration the researcher chose. A research session never writes a
replacement runtime, wrapper, adapter, launch namespace, or exception table.
Preserve old code as evidence. Never weaken an old seal, discard history, or
change corpus retry eligibility.

The kit's host adapters (kit code, not project code) use `Journal` for a new or
explicitly migrated run as follows:

1. Initialize a bounded-segment journal with scientific and operational binding hashes,
   concurrency, and attempt limits. Record the exact adapter version separately.
2. Hold `ownership()` around dispatch. It persists PID plus creation identity
   and refuses another owner. Recover an abandoned owner only after independent
   process-tree/lock checks and recorded review; ambiguous identity fails closed.
   Journal ownership is not a substitute for host-tree checks.
3. Record `intent` before each host spawn and `acknowledged` after the host
   acknowledges it. Neither proves a judgment. Record `returned`, `validated`,
   and `reconciled` separately, each linked to its authoritative receipt hash.
   Only the frozen controller/validator determines these facts.
4. Record a linked retry only after the controller allocated it under frozen
   policy. The journal prevents duplicate unit-attempt dispatch within that segment, but a supplied
   receipt hash is a reference, not independently verified scientific evidence.
5. On interruption, reconcile existing returns before consulting controller
   pending assignments. Never reconstruct research progress from chat history.

Journal replay is deliberately complete before each mutation. Keep each journal
bounded to a small dispatch segment, not the full corpus: replay cost grows with
its history. The host adapter must maintain an authenticated segment index and
checkpoint lineage and prove every prior segment attempt terminal before opening
the next segment. Keep linked retries in their original segment until reconciled;
never move an unknown-finality or retryable attempt into a fresh journal. The
controller's pending list alone cannot detect an unreturned prior launch. Global
uniqueness and exactly-once dispatch across segments remain adapter obligations.
These segment boundaries limit bookkeeping work, not total units, tokens, time,
or the researcher's approved concurrency.

Store closed operational identifiers and categories only, never prompts, labels,
result bodies, exception strings, or model output. Existing raw material stays
in its authorized location. Existing controller formats remain unchanged.

Read-only commands:

```
python scripts/fanout_lifecycle.py inspect --directory <run>/batch_checks/lifecycle/<segment>
python scripts/fanout_lifecycle.py resume-plan --directory <run>/batch_checks/lifecycle/<segment>
```

After quiescence, use `checkpoint --directory <run>/batch_checks/lifecycle/<segment> --output
<run>/batch_checks/checkpoints/checkpoint_vNNN.json`. Record the snapshot path and SHA-256 as
`run_checkpoint` in project state. Old projects without this field remain valid.
A fresh session verifies that anchor, reconstructs current controller facts, and
resolves discrepancies before dispatch.

## Restart and report actual progress

A restart is ready when the documented command that failed, run again, gets past
the point where it failed; `scripts/doctor.py` covers setup. Do not build
separate proof, synthetic harnesses, or reviews to establish readiness. Notes on
past host failures for ELARA's maintainers are in `.github/CONTRIBUTING.md`; a
research session does not act on them.

Report verification phase, acknowledged launches, latest reconciled unit counts,
and stop reason separately. An alive process or high CPU use is not evidence of
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
and reports conflicts rather than overwriting them. Removing protection requires
separate reviewed migration. Report installed workflow and preserved execution
overrides separately; a version string is not byte-for-byte parity.
