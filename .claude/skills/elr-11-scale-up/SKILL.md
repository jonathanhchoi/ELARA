---
name: "elr-11-scale-up"
description: "Run ELR stage 11-scale-up: Run resumable, verified full-corpus coding. Use when this is the current stage in project/PROJECT_STATE.md or when the researcher explicitly requests this recovery stage."
disable-model-invocation: true
---

# Run elr-11-scale-up

First resolve the active root using read-only `scripts/storage.py status` under `workflow/shared/storage.md`, before state or updates.
Before a new run, follow `workflow/shared/kit-updates.md` and run `scripts/check_update.py`; require `ready: true` before execution.
A conflict-free update installs automatically when writes are authorized; otherwise the stage runs on the installed version and the researcher hears the notice once. A declined update stays declined.
Only an update interrupted part-way waits, under "When something breaks" in `workflow/shared/operational-recovery.md`. Preserve existing run software and scientific bindings. Never change ELARA's own files in a project.

1. Read `AGENTS.md`, `project/PROJECT_STATE.md`, and the guardrails, artifact-contract, and
   execution-control files under `workflow/shared/` completely.
2. Read `workflow/stages/11-scale-up.md` completely as the single source of substantive instructions for this stage.
3. Confirm the stage is current and its prerequisites and approvals are satisfied
   (imported artifacts and researcher-asserted approvals count). If `project_slug` is null,
   run Stage 00 from its orientation with this stage as the aim. If a noncurrent stage was
   explicitly chosen (this skill, the menu, or by name), satisfy its prerequisites through
   Stage 00's adoption path, then run it; otherwise stop.
4. Create or reconcile the host-native stage plan before work and update it at every phase
   boundary as required; On Claude Code use `TaskCreate`, `TaskUpdate`, and `TaskList`.
5. Honor the read-only planning and approval boundaries, using the shared conversational
   fallback if native planning or question controls are unavailable. For `long_running: true`,
   reuse a covering authorized goal when present; otherwise continue foreground execution
   with the same completion contract and durable checkpoints. The stage ends when
   `python scripts/stage_check.py --stage <stage-id>` reports `done: true`; end with its output.
   Never require goal activation or replace an unrelated active goal. Work low-touch under
   `workflow/shared/guardrails.md` section 11.
6. Do not cross the stage's human gate; update state and append the run ledger only as the canonical stage directs.
   Summarize plainly and follow the usage mode (`usage` in `project/PROJECT_STATE.md`): continue into
   the next stage in `pipeline` mode unless a stop condition holds, or offer the menu in `specific tools` mode.
