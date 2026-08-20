# Native plans and goals

This contract controls how ELARA uses the host's planning and persistence
features. It applies to every canonical stage, utility, router, and generated
wrapper. The research record on disk remains authoritative; a host plan or goal
is a control surface, not evidence that research work occurred.

## One stage, one native plan

Except for a one-step `help`, `menu`, or status response, begin every stage or
utility by creating a short plan in the host's native tracker. Derive it from
the canonical file rather than inventing a second workflow. Use four to seven
verifiable items covering, as applicable:

1. prerequisite and authorization checks;
2. the read-only design or plan phase;
3. the bounded execution or fan-out;
4. mechanical and substantive verification;
5. state, ledger, gate, and next-stage handoff.

Keep exactly one item in progress. Mark an item complete only after the
canonical evidence exists and has been inspected. Update the plan at every
phase boundary, after a recoverable interruption, when a failure route changes
the work, and before the final report. A stage gate, missing researcher input,
or failed check stays pending and is described accurately; it is never marked
complete to tidy the display.

When work is likely to take more than about two minutes, pair plan creation and
each plan checkpoint with the progress and time-remaining report required by
`workflow/shared/guardrails.md` section 6. A tracker update by itself is not a
researcher-facing progress report, and a progress message does not change a
plan item's status.

Plans are session control, not project artifacts. Do not copy a host plan into
`project/`, `DECISIONS.md`, or `RUN_LEDGER.md` unless the canonical stage itself
declares a plan artifact. Conversely, a completed native plan never substitutes
for hashes, exact counts, validation reports, approvals, or ledger entries.

On resume, first reconstruct truth from `PROJECT_STATE.md`, the active run
manifest, ledgers, and immutable returns. Then inspect the host plan or task
list, discard stale items, and rebuild or update it to match the files. Never
infer completion from a tracker left by an earlier session.

## Plan profiles and Plan Mode

`interaction_profile` determines how the native plan is used:

- `normal`: track the short interaction and gate. Do not enter Plan Mode or
  start a goal.
- `plan`: use the host's read-only Plan Mode, maintain the native plan, make no
  project writes, and return the decision-complete plan and exact execution
  handoff.
- `execute`: create the native plan, then execute. Do not enter Plan Mode merely
  because the work has several steps.
- `plan_then_execute`: create the full native plan with the read-only plan phase
  first. Complete that phase before any project write. Continue into execution
  in the same session when no stop condition applies. Enter Plan Mode and pause
  only when `workflow/shared/guardrails.md` section 11 requires a researcher
  handoff; Stages 18 and 20 always do because their plan is the manuscript-edit
  gate.

This distinction preserves low-touch work between gates. The native tracker is
used throughout; read-only Plan Mode is used where its approval boundary is
actually required. A permission-mode change never grants a workflow approval.

## Long-running stages use one goal

Every canonical stage with `long_running: true` has a nonempty
`goal_condition` in front matter. That condition is the exact, testable contract
for one stage. It states the work, the evidence that proves success, the scope
that must not change, and the gate or failure condition that ends the run.

Before the first execution write or external call in a long-running stage:

1. Inspect goal status. If the same stage goal is active, resume it from disk.
   If a different unfinished goal is active, do not replace, clear, or combine
   it; report the conflict and wait for the researcher.
2. If no goal is active, provide exactly
   `/goal <goal_condition>` and stop so the researcher can activate the host's
   durable loop. A stage or skill invocation is not itself permission to create
   a goal. Do not imitate Goal mode with repeated ordinary turns.
3. Under the active goal, keep the native stage plan current and surface compact
   checkpoint reports: current item, verified evidence, exact remaining count,
   elapsed time, a revised ETA range with its basis, and any blocker. Persist
   the corresponding run checkpoint before reporting it.
4. A goal is complete only when its stated evidence has been surfaced and the
   canonical state transition or section 11 stop has been recorded. Do not mark
   it complete because a turn, wave, or command ended.

Use one goal per stage, never one goal for the whole pipeline and never one goal
per worker. The host's workflow or sub-agent orchestrator owns fan-out; the
stage goal keeps the parent working through plan items, waves, serial
validation, and final reconciliation. A bounded stage (`long_running: false`)
uses the native plan but does not start a goal.

If the host does not expose goals, goals are disabled by policy, or the feature
fails, record that fact in the run manifest and use normal approved execution
with the same native plan and durable on-disk checkpoints. Unavailability is a
fallback, not a reason to weaken the completion condition.

## Codex adapter

- Use `update_plan` to create and maintain the stage plan. Keep at most one
  `in_progress` item and update it at the checkpoints above.
- Use Codex Plan Mode for the `plan` profile and for the section 11 handoffs
  described above. The plan tracker by itself does not make a session
  read-only.
- For a researcher-activated goal, inspect it with `get_goal`; create it with
  the exact front-matter condition only when the researcher explicitly invokes
  `/goal`; and use `update_goal` only when the canonical completion or blocked
  rule is actually satisfied. Never replace another active goal.
- During a Codex fan-out, the active stage goal remains with the parent while
  the named `elr_worker` or `elr_research_worker` sub-agents handle individual
  assignments in bounded waves under `workflow/shared/observation-fanout.md`.

## Claude Code adapter

- Use `TaskCreate` to create the stage items, `TaskUpdate` for status and
  dependencies, and `TaskList` on resume and at checkpoints. Claude Code's task
  list, not a prose checklist hidden in chat, is the native plan tracker.
- Use Plan Mode (`EnterPlanMode`/`ExitPlanMode`, or `/plan`) only for the
  profiles and approval boundaries described above. Leaving Plan Mode is not a
  research approval.
- A researcher activates the exact front-matter condition with `/goal`. Check it
  with `/goal`, never replace an unrelated active goal, and remember that its
  evaluator can see only evidence surfaced in the conversation. Therefore every
  checkpoint and final turn states the verification result and exact counts,
  not merely "done."
- During a Claude fan-out, the active stage goal remains with the parent while
  the saved `elr-observation-fanout` or `elr-research-fanout` workflow runs the
  restricted workers under `workflow/shared/observation-fanout.md`.

## Completion report

Before returning control, reconcile the native plan against disk and report:
the completed or blocked plan item; files or commands that prove it; exact
counts where applicable; the active goal's outcome for a long stage; the state
transition; and the next gate or task. This report helps the host goal evaluator
without becoming a substitute for the durable record.
