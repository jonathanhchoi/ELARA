---
name: "elr-17-skeleton-draft"
description: "Run ELR stage 17-skeleton-draft: Create and approve the article skeleton. Use when this is the current stage in project/PROJECT_STATE.md or when the researcher explicitly requests this recovery stage."
---

# Run elr-17-skeleton-draft

Before a new run, follow `workflow/shared/kit-updates.md` and run `scripts/check_update.py`.
Require `ready: true` before execution; use its read-only planning exception when applicable.
Automatically install verified compatible updates when writes are authorized; unavailable GitHub uses freshly verified installed bytes.
Investigate conflicts; a declined specific change remains binding. Preserve existing run software and scientific bindings.

1. Read `AGENTS.md`, `project/PROJECT_STATE.md`, and the guardrails, artifact-contract, and
   execution-control files under `workflow/shared/` completely.
2. Read `workflow/stages/17-skeleton-draft.md` completely as the single source of substantive instructions for this stage.
3. Confirm the stage is current and its prerequisites and approvals are satisfied
   (imported artifacts and researcher-asserted approvals count). If `project_slug` is null,
   run Stage 00 from its orientation with this stage as the aim. If a noncurrent stage was
   explicitly chosen (this skill, the menu, or by name), satisfy its prerequisites through
   Stage 00's adoption path, then run it; otherwise stop.
4. Create or reconcile the host-native stage plan before work and update it at every phase
   boundary as required; On Codex use `update_plan` and keep exactly one item `in_progress`.
5. Honor the mode handoff. For `long_running: true`, resume a goal covering the same
   authorized work, even if worded differently; otherwise give `/goal <goal_condition>`
   when goal activation is available. Use the documented foreground fallback if it is
   unavailable; never replace an unrelated active goal.
   Otherwise work low-touch under `workflow/shared/guardrails.md` section 11.
6. Do not cross the stage's human gate; update state and append the run ledger only as the canonical stage directs.
   Summarize plainly and follow the usage mode (`usage` in `project/PROJECT_STATE.md`): continue into
   the next stage in `pipeline` mode unless a stop condition holds, or offer the menu in `specific tools` mode.
