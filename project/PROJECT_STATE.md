---
schema_version: "1.2"
workflow_version: "2.0.2"
project_slug: null
usage: "pipeline"
checkpoints: "none"
current_stage: "00-initialize"
status: "ready"
active_artifacts: {}
approvals: {}
outstanding_user_inputs: []
last_run_id: null
updated_at: null
---

# Project state

This file records where one research project stands and what the software should
do next. The settings at the top of the file—not chat history—control resume
behavior. Stage 00 replaces the initial
`null` values with the approved project identity and timestamp and records the
first exact versions of the project files then in use. `usage` records the usage mode the researcher
chose at Stage 00: `pipeline` (the whole workflow, stage by stage; the router
continues into the next stage when one ends unless a stop condition holds) or
`tools` (specific tools from the menu in
`PIPELINE.md`, run on request; the router offers the menu instead). It is
optional in state files written under the older format labeled `schema 1.0` and
defaults to `pipeline`.
`checkpoints` records how often the researcher wants to be consulted beyond
the gates: `none` (the default: the assistant continues between stages and
executes its plans without waiting), `stages`, `plans`, or `all`. It is
optional and defaults to `none`; see `workflow/shared/guardrails.md` section 11.

Do not hand-edit state merely to bypass a prerequisite or gate. State changes
must correspond to a verified stage transition, append-only run entry, and, when
applicable, a researcher decision recorded with the exact file version it
approved.

Valid statuses are `ready`, `running`, `awaiting_approval`, `waiting_for_user`,
`failed`, `complete`, and `superseded`; treat any other value as malformed
state. See `PIPELINE.md` and the machine-interface rules in
`workflow/shared/artifact-contract.md` for their
meanings and transition rules. Save this file as UTF-8 without a byte-order
mark; a BOM breaks the state parser.
