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
  in the same session when no stop condition applies. Stage 04 is the deliberate
  exception to the usual low-touch rule: it always uses Plan Mode for the
  interactive methods interview described below. For other stages, enter Plan
  Mode and pause only when `workflow/shared/guardrails.md` section 11 requires a
  researcher handoff; Stages 18 and 20 always do because their plan is the
  manuscript-edit gate.

This distinction preserves low-touch work between gates. The native tracker is
used throughout; read-only Plan Mode is used where its approval boundary is
actually required. A permission-mode change never grants a workflow approval.

### Stage 04 interactive methods interview

Stage 04 always enters the host's read-only Plan Mode before asking the
researcher to settle methods or hypotheses. Inspect the active preemption and
feasibility files, recorded conditions and decisions, probe-exposure record,
and actual metadata or authorized samples first. Separate what those materials
already fix from the material choices that remain open. Do not ask the
researcher to repeat an answer already in the record.

Use the host's structured user-question control in short, coherent rounds:
Codex uses `request_user_input`, and Claude Code uses `AskUserQuestion`. Ask one
to three questions per round so later questions can respond to earlier answers.
Each question addresses one decision in plain language, leads with a
recommended option grounded in the inspected evidence, offers two or three
realistic alternatives with their consequences, and permits a free-form answer.
The researcher may say "go with the recommendations" or "don't know." Do not
convert silence or "don't know" into an `assistant-default`. If an unknown
choice must be resolved before the design can be coherent, explain why and ask
whether to use the recommendation or pause; if it can be deferred, name the
later boundary and preserve it as unresolved.

Cover only material open choices, including the claim boundary and meaning of
plausible results; population, frame, scope, units, inclusions, and exclusions;
constructs, outcomes, comparisons, estimands, and hypotheses; confirmatory and
exploratory status; clustering, missingness, power or precision, significance,
and multiple testing; validation, adjudication, and error correction; and
resource, privacy, model, and stopping constraints. Adapt the later rounds to
the researcher's earlier preferences instead of reading a fixed questionnaire.

Still in Plan Mode, synthesize the answers into a decision-complete proposed
design that maps each hypothesis to its estimand, data, validation, and analysis
and lists every explicit deferral. Ask the researcher to review or revise that
plan. Plan acceptance authorizes ELARA to leave Plan Mode and draft the
versioned Stage 04 files in the same session; it is not the final
`methods-plan-approval`, which remains a separate gate after the files are
verified. If the host cannot enter Plan Mode or expose its question control,
make no project write and give the exact mode-switch or resume handoff.

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
  described above, and always for the Stage 04 interactive methods interview.
  In that interview, use `request_user_input` as specified above. The plan
  tracker by itself does not make a session read-only.
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
  profiles and approval boundaries described above, including every Stage 04
  methods interview. Use `AskUserQuestion` for the Stage 04 rounds. Leaving
  Plan Mode is not a research approval, and accepting the Stage 04 plan is not
  the later methods gate.
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
