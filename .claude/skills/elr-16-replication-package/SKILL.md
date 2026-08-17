---
name: "elr-16-replication-package"
description: "Run ELR stage 16-replication-package: Build and verify the replication package. Use when this is the current stage in project/PROJECT_STATE.md or when the researcher explicitly requests this recovery stage."
disable-model-invocation: true
---

# Run elr-16-replication-package

1. Read `AGENTS.md`, `project/PROJECT_STATE.md`, `workflow/shared/guardrails.md`, and
   `workflow/shared/artifact-contract.md` completely.
2. Read `workflow/stages/16-replication-package.md` completely and follow it as the single source of substantive
   instructions for this stage.
3. Confirm that the stage is current and its prerequisites and approvals are satisfied.
   If the project is uninitialized or `usage` in state is `tools`, an out-of-sequence
   request is expected: follow the tools path in `workflow/stages/00-initialize.md` (see
   `workflow/shared/tool-menu.md`) to import what this stage needs and record the gates the
   researcher asserts, then continue. Otherwise, if it is not current, stop unless the
   researcher explicitly authorized a recovery route.
4. Honor the stage's mode handoff. A skill cannot switch Plan or Goal mode by itself.
5. Do not cross the stage's human gate. Update state and append the run ledger only as the
   canonical stage directs.
