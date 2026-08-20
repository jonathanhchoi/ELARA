@AGENTS.md

# Claude Code adapter

Use `/elr` to start, adopt, show the menu of tools, resume, or report status.
Use `/elr-<stage-slug>` or `/elr-<utility>` when the router or researcher names
a particular stage or tool. The command is a thin wrapper: always follow the
canonical `workflow/stages/NN-*.md` or `workflow/utilities/*.md` file and
current project state rather than treating wrapper text as a second workflow
definition. If this file did not exist when the session started (the kit was
just installed by `scripts/bootstrap.py`), `project/BOOTSTRAP.md` says what to
do now.

For every nontrivial stage or utility, follow
`workflow/shared/execution-control.md`: use `TaskCreate` for a four-to-seven-item
native stage plan, `TaskUpdate` at every phase or fan-out checkpoint, and
`TaskList` on resume and before the final report. Keep exactly one task in
progress and reconcile the task list from project state and ledgers, never the
other way around.

Stage metadata cannot change Claude Code's permission mode automatically. Map
the canonical `interaction_profile` as follows:

- `normal`: remain in Claude's normal approved/default mode, track the short
  interaction in the task list, and conduct the researcher gate. Do not start a
  goal.
- `plan`: enter Plan Mode, inspect read-only context, update the task list, and
  make no file changes. Return the decision-complete plan and exact execution
  handoff.
- `execute`: use Claude's approved/default execution mode for a bounded stage.
  Every fan-out inside it — coding or audit units in Stages 08, 11, 12, and 15;
  research units such as Stage 02 searches and retrieval, Stage 07 critics,
  Stage 19 claim-citation pairs, and fresh reviews — runs as one of the kit's
  saved dynamic workflows, which you launch yourself as part of the stage:
  `elr-observation-fanout` (`{ "run_dir": ... }`) for coding and audit units,
  `elr-research-fanout` (`{ "fanout_dir": ... }`) for research units, both under
  `workflow/shared/observation-fanout.md`. Do not launch workers one at a time
  with the Agent tool while workflows are available, and do not process the
  units serially in your own context.
- `plan_then_execute`: put the read-only plan phase first in the task list. Plan
  in normal mode without writing any project file, then continue into execution
  in the same session. Enter Plan Mode and stop only when a stop condition in
  `workflow/shared/guardrails.md` §11 holds, and always for Stages 18 and 20,
  whose plan is the manuscript-edit gate.

For every stage marked `long_running: true`, inspect `/goal` status before its
first execution write. Resume only if the exact front-matter `goal_condition`
is active. If none is active, print the complete `/goal <goal_condition>` command
and stop; if another goal is active, do not replace or clear it. The parent
keeps that one stage goal and the task list current while saved workflows run
fan-outs. Surface verification results and exact counts in checkpoint and final
turns because Claude's goal evaluator sees the conversation, not project files.
If goals are unavailable or disabled, record the fallback and use the same task
plan and durable disk checkpoints. Never use one goal for the whole pipeline or
one goal per worker.

Claude permission modes control tool access; they never waive a workflow gate or
data-authorization requirement. Nor do they add stops: outside the gates and
the §11 stop conditions, keep working and record provisional defaults instead
of asking.

Dynamic workflows require Claude Code v2.1.154 or later. The kit's saved workflows live in
`.claude/workflows/` (`elr-observation-fanout.js`, `elr-research-fanout.js`) and are launched with
the Workflow tool by `name` and structured `args` (or as `/elr-observation-fanout` and
`/elr-research-fanout`); the researcher's choice of ELARA's pipeline or of a stage is the opt-in to
run them, so launch them without asking. The workflow script coordinates only: agents read and
write files. Every worker receives one immutable assignment and one unique output path; only the
parent validates, merges, and edits shared ledgers. Workflow agents run with the researcher's tool
allowlist: the first `python scripts/unit_fanout.py …` / `research_fanout.py …` command and the
first web fetch may prompt once, and the first launch of each saved workflow asks whether to allow
it — tell the researcher once, in plain language, that approving "don't ask again for this
workflow in this project" lets a run of many waves proceed without further prompts. If workflows
are disabled or the host is older than 2.1.154, launch workers directly with the Agent tool, one
assignment per call, with the restricted `subagent_type` below, and record that route.

Workers of any kind run as the kit's restricted subagent types, never as `general-purpose`:
`elr-worker` (`.claude/agents/elr-worker.md`; coding and audit units and the workflows' controller
`status` steps, no web) and `elr-research-worker` (`.claude/agents/elr-research-worker.md`;
searches, retrieval, citation chains, critiques, cite-checks, fresh reviews — web fetch and search,
nothing interactive). The workflow scripts set those `agentType`s; direct Agent-tool launches set
the matching `subagent_type`. Claude Code loads a project's first `.claude/agents/` directory only
at session start, so after installing or updating the kit into a folder that had none, restart
once before fanning out. The desktop app's in-app Browser, computer use, Chrome, and other MCP
tools are interactive surfaces for the researcher's own session; a worker must never reach them
(one that did, on a bot-challenge page, crashed the desktop app twice on 2026-08-17). Fan-out
manifests, briefs, and worker returns live under the run directory, never in the session
scratchpad; see `workflow/shared/observation-fanout.md`, "The host orchestrates; the kit
validates" and "Worker tool surface, time boxes, and crash-resume".
