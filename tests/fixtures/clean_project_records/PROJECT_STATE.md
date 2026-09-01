---
schema_version: "1.3"
workflow_version: "2.5.1"
project_slug: null
usage: "pipeline"
checkpoints: "none"
failure_handling: "autonomous"
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
behavior. Stage 00 leaves `project_slug` as `null` while it runs, waits for
needed input, and presents the charter for approval. Charter approval assigns
the stable project identity. Stage 00 also records the first exact versions of
the project files then in use. `usage` records the usage mode the researcher
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
`failure_handling` records what the assistant does when an individual document
or unit fails during the full coding run (Stage 11): `autonomous` (the default:
it decides each case under the approved rules, records every decision in that
run's failure-decisions log, keeps the run going, and presents the complete
list at the end of the run and at the next gate) or `interactive` (it pauses at
the checkpoint where failures are found and asks the researcher to decide
each). It is optional and defaults to `autonomous`; it never relaxes a gate, a
spending limit, or a required review. See `workflow/shared/guardrails.md`
section 11.

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
