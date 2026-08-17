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

Stage metadata cannot change Claude Code's permission mode automatically. Map
the canonical `interaction_profile` as follows:

- `normal`: remain in Claude's normal approved/default mode and conduct the
  researcher interaction. Do not create a long-running autonomous task.
- `plan`: use `/plan` where available, inspect read-only context, and make no file
  changes. Return the completed plan and the exact command needed for the next
  handoff.
- `execute`: use Claude's approved/default execution mode for a bounded stage.
  When a long-running stage fans out one-unit judgments, use
  `/elr-code-observations`, then `/elr-observation-fanout` from
  `.claude/workflows/elr-observation-fanout.js`, under
  `workflow/shared/observation-fanout.md`. For other long work, use `/goal
  <verifiable completion condition>` where supported; otherwise checkpoint
  through `project/PROJECT_STATE.md` and `project/RUN_LEDGER.md`.
- `plan_then_execute`: complete the Plan Mode phase without writes, stop, and ask
  the researcher to approve the plan and switch to an execution-capable mode,
  using `/goal` for a long-running phase where available. Resume only after that
  explicit handoff.

Claude permission modes control tool access; they never waive a workflow gate or
data-authorization requirement.

Dynamic workflows require Claude Code v2.1.154 or later. The workflow script coordinates only:
agents read and write files. Every worker receives one immutable assignment and one unique output
path; only the parent validates, merges, and edits shared ledgers.
