---
name: "elr-17-integrate-manuscript"
description: "Run ELR stage 17-integrate-manuscript: Integrate validated results into the researcher's manuscript. Use when this is the current stage in project/PROJECT_STATE.md or when the researcher explicitly requests this recovery stage."
disable-model-invocation: true
---

# Run elr-17-integrate-manuscript

1. Read `AGENTS.md`, `project/PROJECT_STATE.md`, and the guardrails, artifact-contract, and
   execution-control files under `workflow/shared/` completely.
   Then read `workflow/shared/manuscript-editing-contract.md` and the active publication profile pinned in
   `project/PROJECT_STATE.md` (`project/PUBLICATION_PROFILE_vNNN.md`), if any.
2. Read `workflow/stages/17-integrate-manuscript.md` completely and follow it as the single source of substantive
   instructions for this stage.
3. Confirm that the stage is current and its prerequisites and approvals are satisfied
   (imported artifacts and researcher-asserted approvals count). If the project is
   uninitialized (`project_slug` is null), run Stage 00 first, from its orientation, with this
   stage as the aim. If it is not current and the researcher chose it explicitly (this skill,
   the menu, or by name), first satisfy its prerequisites through Stage 00's adoption path,
   then run it; otherwise stop.
4. Create or reconcile the host-native stage plan before work and update it at every phase
   boundary as required; On Claude Code use `TaskCreate`, `TaskUpdate`, and `TaskList`.
5. Honor the mode handoff. For `long_running: true`, resume the matching active goal or give
   the exact `/goal <goal_condition>` handoff and stop; never replace another active goal.
   Otherwise work low-touch under `workflow/shared/guardrails.md` section 11.
6. Do not cross the stage's human gate. Update state and append the run ledger only as the
   canonical stage directs. At the end, summarize plainly and, per the usage mode (`usage` in
   `project/PROJECT_STATE.md`), continue into the next stage in `pipeline` mode unless a stop
   condition holds, or offer the menu in `specific tools` mode.
