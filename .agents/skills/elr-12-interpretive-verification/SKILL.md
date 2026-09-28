---
name: "elr-12-interpretive-verification"
description: "Run ELR stage 12-interpretive-verification: Independently verify interpretive support. Use when this is the current stage in project/PROJECT_STATE.md or when the researcher explicitly requests this recovery stage."
---

# Run elr-12-interpretive-verification

First resolve the active root using read-only `scripts/storage.py status` under `workflow/shared/storage.md`, before state or updates.
Before a new run, follow `workflow/shared/kit-updates.md` and run `scripts/check_update.py`; require `ready: true` before execution, respecting its read-only planning exception.
Automatically install verified compatible updates when writes are authorized; unavailable GitHub uses freshly verified installed bytes.
Investigate conflicts; a declined specific change remains binding. Preserve existing run software and scientific bindings.

1. Read `AGENTS.md`, `project/PROJECT_STATE.md`, and the guardrails, artifact-contract, and
   execution-control files under `workflow/shared/` completely.
2. Read `workflow/stages/12-interpretive-verification.md` completely as the single source of substantive instructions for this stage.
3. Confirm the stage is current and its prerequisites and approvals are satisfied
   (imported artifacts and researcher-asserted approvals count). If `project_slug` is null,
   run Stage 00 from its orientation with this stage as the aim. If a noncurrent stage was
   explicitly chosen (this skill, the menu, or by name), satisfy its prerequisites through
   Stage 00's adoption path, then run it; otherwise stop.
4. Create or reconcile the host-native stage plan before work and update it at every phase
   boundary as required; On Codex use `update_plan` and keep exactly one item `in_progress`.
5. Honor the read-only planning and approval boundaries, using the shared conversational
   fallback if native planning or question controls are unavailable. For `long_running: true`,
   reuse a covering authorized goal when present; otherwise continue foreground execution
   with the same completion contract and durable checkpoints. Never require goal activation
   or replace an unrelated active goal. Work low-touch under `workflow/shared/guardrails.md` section 11.
6. Do not cross the stage's human gate; update state and append the run ledger only as the canonical stage directs.
   Summarize plainly and follow the usage mode (`usage` in `project/PROJECT_STATE.md`): continue into
   the next stage in `pipeline` mode unless a stop condition holds, or offer the menu in `specific tools` mode.
