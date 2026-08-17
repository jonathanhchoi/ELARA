---
schema_version: "1.1"
workflow_version: "1.0.0"
project_slug: null
usage: "pipeline"
current_stage: "00-initialize"
status: "ready"
active_artifacts: {}
approvals: {}
outstanding_user_inputs: []
last_run_id: null
updated_at: null
---

# Project state

This file is the persistent router for one research project. The YAML front
matter—not chat history—controls resume behavior. Stage 00 replaces the initial
`null` values with the approved project identity and timestamp and records the
first active artifact versions. `usage` records the usage mode the researcher
chose at Stage 00: `pipeline` (the whole workflow, stage by stage; the router
offers the next stage when one ends) or `tools` (specific tools from the menu in
`PIPELINE.md`, run on request; the router offers the menu instead). It is
optional in state files written under schema 1.0 and defaults to `pipeline`.

Do not hand-edit state merely to bypass a prerequisite or gate. State changes
must correspond to a verified stage transition, append-only run entry, and, when
applicable, a version-pinned researcher decision.

Valid statuses are `ready`, `running`, `awaiting_approval`, `waiting_for_user`,
`failed`, `complete`, and `superseded`; treat any other value as malformed
state. See `PIPELINE.md` and `workflow/shared/artifact-contract.md` for their
meanings and transition rules. Save this file as UTF-8 without a byte-order
mark; a BOM breaks the state parser.
