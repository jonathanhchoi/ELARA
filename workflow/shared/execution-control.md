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
  in the same session when no stop condition applies. At the decision boundaries
  named below, enter Plan Mode and use the host's structured question interface
  before writing or revising the affected files. For other stages, enter Plan
  Mode and pause only when `workflow/shared/guardrails.md` section 11 requires a
  researcher handoff; Stages 18 and 20 always do because their plan is the
  manuscript-edit gate.

This distinction preserves low-touch work between gates. The native tracker is
used throughout; read-only Plan Mode is used where its approval boundary is
actually required. A permission-mode change never grants a workflow approval.

### Interactive Plan-Mode decision interviews

Stages 01, 04, 05, 07, 08, 09, and 17 use Plan Mode at the specific decision
boundaries below. Codex uses `request_user_input`; Claude Code uses
`AskUserQuestion`. The parent conducts the interview. A sub-agent never asks the
researcher to decide and never owns the plan.

Before asking, inspect the active evidence, prior decisions, and actual files.
State what they already settle and ask only about material choices that remain
open. Use short, coherent rounds of one to three plain-language questions so
later questions can respond to earlier answers. Each question addresses one
decision, puts the evidence-supported recommendation first, offers two or three
realistic alternatives with their consequences, and permits a free-form answer.
Accept "go with the recommendations" and "don't know." Do not turn silence or
"don't know" into an `assistant-default`. If an unknown must be resolved now,
explain why and ask whether to use the recommendation or pause; if it can be
deferred, name the later boundary and preserve it as unresolved.

Still in Plan Mode, synthesize the answers into a decision-complete proposal,
list every explicit deferral, and ask the researcher to review or revise it.
Write no project file, state entry, ledger row, run record, code, or revised
research output while the interview is active. Files created before a mid-stage
interview remain unchanged. Plan acceptance authorizes only the execution that
the stage names below. It never by itself approves a separately named artifact
gate, authorizes an external submission, or changes a frozen design. If the host
cannot enter Plan Mode or expose its question control, stop at the interview
boundary without the affected write and give the exact mode-switch or resume
handoff.

#### Stage 01 profile and shortlist interviews

Use Plan Mode twice, without keeping the long research execution in Plan Mode.
First, inspect the researcher's supplied work and infer an interest profile
before any Stage 01 project write. Ask only about disputed or unsupported
inferences, substantive constraints, and whether a claimed future-work item may
be reconsidered. Acceptance authorizes writing the confirmed profile and
running the landmark, brainstorming, and preliminary novelty review; activate
the Stage 01 goal before that execution begins.

After the verified shortlist exists, re-enter Plan Mode to compare the
candidates. Explain each candidate's contribution, either-way payoff, fit,
closest literature, access route, principal risk, and realistic combinations or
redirections. An express answer selecting a candidate against the exact report
is the `project-selection` decision; accepting a generic host plan is not. If a
redirection or combination needs new research, leave Plan Mode, complete and
verify it under the same stage goal, then return with a new report version for
selection.

#### Stage 04 methods-design interview

Enter Plan Mode before settling methods or hypotheses. Inspect the active
preemption and feasibility files, recorded conditions and decisions,
probe-exposure record, and actual metadata or authorized samples first. Cover
only material open choices: whether the study supports descriptive,
associational, or causal conclusions, the identification strategy and
assumptions for any causal conclusion, and the meaning of plausible results;
population, frame, scope, units, inclusions, and exclusions; constructs,
outcomes or dependent variables, comparisons, quantities to estimate
(estimands), and hypotheses; which hypotheses and analyses must be fully
specified and preregistered before outcomes are examined rather than treated as
exploratory; clustering, missingness, power or precision, significance, and
correction for multiple comparisons; validation, adjudication, and error
correction; resource limits and stopping rules, privacy and confidentiality
limits; and exactly which documents, data, prompts, or other information may be
sent to each model or provider.

The proposed plan maps every hypothesis to its estimand, data, validation, and
analysis. Acceptance authorizes drafting the versioned Stage 04 files; it is not
the final `methods-plan-approval` after those files are verified.

#### Stage 05 codebook-and-schema interview

Enter Plan Mode before creating a codebook, schema, prompt, examples, or list of
units eligible for coding. Inspect the approved design, actual metadata, and any
authorized representative documents. Ask about material open boundaries for
variables and categories; the coding unit and multiple observations; attribution
to opinions, parties, quotations, incorporated material, majorities,
concurrences, and dissents; inclusions, exclusions, duplicates, missing and
ambiguous cases, conflicts, and supersession; uncertainty and not-applicable
routes; how units and variables are identified consistently across files and
versions; and exactly which documents, data, prompts, or other information may
be sent to each model or provider.

The proposal maps each construct and hypothesis to definitions, edge cases,
schema fields, evidence requirements, unit counting, and validation fixtures.
Acceptance authorizes drafting and testing the Stage 05 files; it is not the
final `codebook-schema-approval`. Do not create a provisional
`assistant-default` for a material substantive definition before asking.

#### Stage 07 critique-disposition interview

Run the independent critiques first under the active Stage 07 goal. Preserve
their reports, build the issue matrix, and draft evidence-based disposition
recommendations without revising the shared design or codebook. Then enter Plan
Mode. Group duplicate issues but preserve disagreements among critics. For each
material issue, recommend accept, reject with reasons, defer to a named pilot
test, or route upstream, with the consequences and invalidated approvals.

Acceptance authorizes only the approved issue-level revisions after leaving
Plan Mode. It is not the final `design-freeze` approval. An upstream route is
recorded after Plan Mode and completed before any inconsistent package is
activated.

#### Stage 08 pilot interview

Enter Plan Mode before allocating a run, writing pilot code or files, or calling
a model. Inspect the frozen design, codebook, schema, list of eligible units,
authorization, adversarial-review conditions, and recorded budget. Ask about the
five-to-ten-unit diagnostic sample and why it is informative; independent human
pre-coding; architecture and one-unit execution; success thresholds; quote,
schema, retry, and stopping rules — including the `failure_handling` preference
recorded at Stage 00 (confirm or change it; it governs how the Stage 11 run
dispositions individual unit failures) and the run-level stopping rule Stage 11
will apply to widespread failure; human review and disagreement categories;
model route; and spending and time limits.

The proposal fixes the sample, thresholds, commands, checks, review sequence,
and cost ceiling. Acceptance authorizes building and running that fixed pilot
after the exact Stage 08 goal is active; it is not `pilot-acceptance` and cannot
authorize a mid-pilot reinterpretation.

#### Stage 09 preregistration-setup interview

Enter Plan Mode before drafting the frozen manifest, preregistration, executable
analysis package, or amendment policy. Audit the already approved and piloted
design rather than reopening it. Ask only about unresolved registry and release
choices: title and authorship, registry, public or embargoed visibility,
license, sensitive attachments, submission route, and how material amendments
and deviations will be disclosed. If the audit reveals an unresolved scientific
choice or inconsistency, route it to the owning earlier stage instead of asking
the researcher to settle it here.

Acceptance authorizes drafting and verifying the Stage 09 package. It is not
approval of the exact preregistration PDF, acceptance of registry terms, or
authorization to submit or publish anything externally.

#### Stage 17 skeleton interview

Enter Plan Mode before recording a skip or creating a skeleton. Inspect the
verified replication package, active publication profile, available tables,
figures, and equations, and any researcher-supplied draft or organization notes.
Ask whether to create or skip; if creating, ask only the still-open choices about
output format, venue, fixed sections and order, displays,
counterarguments, limitations, and what deserves emphasis. Offer LaTeX source
compiled to PDF as the default and accept "go with the defaults."

Still in Plan Mode, propose the complete evidence-oriented organization while
reserving substantive prose for the researcher. Acceptance authorizes creating
that versioned skeleton. It is not the later `skeleton-draft-approval`. An
express skip answer is the gate decision, but record it only after leaving Plan
Mode.

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
- Use Codex Plan Mode for the `plan` profile, the section 11 handoffs, Stages 18
  and 20, and every Stage 01, 04, 05, 07, 08, 09, and 17 interview boundary
  described above. Use `request_user_input` for those decision interviews. The
  plan tracker by itself does not make a session read-only.
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
  profiles and approval boundaries described above, including every Stage 01,
  04, 05, 07, 08, 09, and 17 interview boundary. Use `AskUserQuestion` for those
  decision rounds. Leaving Plan Mode is not a research approval; plan
  acceptance has only the stage-specific effect stated above.
- A researcher activates the exact front-matter condition with `/goal`. Check it
  with `/goal`, never replace an unrelated active goal, and remember that its
  evaluator can see only evidence surfaced in the conversation. Therefore every
  checkpoint and final turn states the verification result and exact counts,
  not merely "done."
- During a Claude fan-out, the active stage goal remains with the parent while
  the saved `elr-observation-fanout` or `elr-research-fanout` workflow runs the
  restricted workers under `workflow/shared/observation-fanout.md`.

## Completion report

For paused or interrupted Stage 11 work, follow
`workflow/shared/operational-recovery.md`. Verify the recorded `run_checkpoint`
when present, reconcile it against current disk evidence, and replace stale
active pointers before dispatch. Do not report a live verifier as live coding.
An explicitly paused task must not continue an earlier production goal.

Before returning control, reconcile the native plan against disk and report:
the completed or blocked plan item; files or commands that prove it; exact
counts where applicable; the active goal's outcome for a long stage; the state
transition; and the next gate or task. This report helps the host goal evaluator
without becoming a substitute for the durable record.
