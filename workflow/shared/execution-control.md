# Native plans and goals

How ELARA uses the host's planning, question, and goal features in every stage,
utility, router, and wrapper. The research record on disk is authoritative; a
host plan or goal is a control surface, never evidence that work occurred.

## One stage, one native plan

Before a new stage or utility, including its read-only plan, follow
`kit-updates.md` and resolve storage under `storage.md`. Except for one-step
`help`, `menu`, or status replies, begin with a short plan in the host's native
tracker (or the conversation), derived from the canonical file: prerequisite and
authorization checks; the read-only plan phase; the bounded execution or
fan-out; verification; and state, ledger, gate, and handoff. Keep one item in
progress, mark an item complete only after its evidence exists and has been
inspected, and update the plan at each phase boundary, after an interruption,
and before the final report; a pending gate or failed check stays pending. For
work likely to take more than about two minutes, pair plan creation and each
plan checkpoint with the progress report `guardrails.md` §6 requires.

Plans are session control, never copied into `project/` and never a substitute
for hashes, counts, approvals, or ledger entries. On resume, reconstruct truth
from state, the run manifest, ledgers, and returns, then rebuild the tracker.

## Plan profiles and Plan Mode

Plan Mode means a read-only planning and decision phase: the host's Plan Mode
and question controls when available, otherwise the same interview in the
conversation with no project writes. The researcher's approval, not an interface
transition or permission mode, authorizes execution. `interaction_profile`:
`normal` tracks the interaction and gate with no Plan Mode or goal; `plan` stays
read-only and returns a decision-complete plan; `execute` plans, then executes;
`plan_then_execute` finishes the read-only phase before any project write, then
continues in the same session, entering Plan Mode at the interview boundaries
below or when `guardrails.md` §11 requires a handoff, and always for Stages 18
and 20, whose plan is the manuscript-edit gate.

### Interactive Plan-Mode decision interviews

Stages 01, 04, 05, 07, 08, 09, and 17 interview the researcher at boundaries
their stage files describe, with `request_user_input` on Codex and
`AskUserQuestion` on Claude Code; only the parent asks. First inspect the
evidence, earlier decisions, actual files, and the charter's support section
(`researcher-support.md`), say what they settle, and ask only about material
open choices: rounds of one to three plain-language questions, each with the
recommendation first, two or three realistic alternatives and their
consequences, and room for a free-form answer. Accept "go with the
recommendations" and "don't know"; neither becomes an `assistant-default`. Then
propose a decision-complete plan listing every deferral and ask for review.
Acceptance authorizes only what is named below, never a separate gate, an
external submission, or a change to a frozen design.

#### Stage 01

Use Plan Mode twice: the interest profile before any write (acceptance
authorizes the profile and the novelty work), then the verified shortlist, where
only an express choice against the exact report is `project-selection`.

#### Stage 04

Before settling methods or hypotheses; acceptance authorizes drafting, not
`methods-plan-approval`.

#### Stage 05

Before any codebook, schema, prompt, or unit list; acceptance authorizes drafting
and testing, not `codebook-schema-approval`.

#### Stage 07

Run the independent critiques first; acceptance authorizes the approved
revisions, not `design-freeze`.

#### Stage 08

Before a run, files, or model calls, confirming `failure_handling`; acceptance
authorizes the fixed pilot, not `pilot-acceptance`.

#### Stage 09

Audit the approved design rather than reopening it; acceptance authorizes
drafting the package, not the preregistration or an external submission.

#### Stage 17

Before a skip or skeleton; acceptance authorizes the skeleton, not
`skeleton-draft-approval`. An express skip is the gate decision.

## Long-running stages keep a completion contract

Every stage with `long_running: true` has a `goal_condition`: the stage ends
when `python scripts/stage_check.py --stage <stage-id>` reports `done: true`,
and the condition names what the assistant must not decide on the way. The
check reads only project files and is done when state moved past the stage with
every required output active and the gate approved, when the stage awaits its
gate with every required output active, on a recorded failure route, or when
stopped for a researcher decision; otherwise it lists what is missing, inactive,
or inconsistent.

End every long stage's final turn with the check's output. When a host goal
evaluator disagrees, run the check again and fix only what it lists, never with
more evidence-gathering, another review, or a restated report; if the check is
done and the evaluator still disagrees, say so once in plain language and stop.

Host goals are optional: reuse an authorized goal covering the work, create one
only at the researcher's request, and never replace an unrelated goal. Without
one, use the foreground fallback: continue with the same plan, condition, and
durable checkpoints, never stopping to request a goal or promising work after
the session ends. The parent stays responsible through validation and
reconciliation and reports verified counts, remaining work, elapsed time, a
revised ETA range, and blockers at checkpoints. Workers never create goals or
plans.

## Codex adapter

`update_plan` keeps the plan (one item `in_progress`). Plan Mode serves the
`plan` profile, §11 handoffs, Stages 18 and 20, and the interviews, with
`request_user_input`. Inspect a researcher-requested goal with `get_goal` and
use `update_goal` only when the host's rule is met. During a fan-out the parent
keeps both while `elr_worker` or `elr_research_worker` sub-agents run.

## Claude Code adapter

`TaskCreate`, `TaskUpdate`, and `TaskList` (on resume and at checkpoints) are the
tracker. Plan Mode (`EnterPlanMode`/`ExitPlanMode`) serves the profiles and
interviews, with `AskUserQuestion`; leaving it is not a research approval. A
`/goal` evaluator sees only the conversation, so checkpoints state exact counts
and the final turn shows the `stage_check.py` output.

## Completion report

Before returning control, reconcile the plan against disk and report the item
completed or blocked, the files or commands that prove it, exact counts, any
goal's outcome, the state transition, and the next gate or task. For paused
Stage 11 work, verify a recorded `run_checkpoint` before launching workers.
