---
name: "elr"
description: "Start a new project, adopt an existing one, resume, report status, or explain the empirical legal research pipeline. Use when the researcher says start, adopt, resume, continue, next, status, help, or tour, or asks which workflow stage to run."
---

# Route the empirical legal research workflow

1. Read `AGENTS.md`, `PIPELINE.md`, and `project/PROJECT_STATE.md` completely.
2. `help` or `tour`: without touching any file, give the orientation in
   `workflow/stages/00-initialize.md` (what ELARA does and does not do, the six steps, gates,
   the commands, the publication profile), say where this project stands, and stop.
   `status`: without touching any file, report the current stage and status, approvals and
   their basis (verified or researcher-asserted), active artifact versions, the last run, and
   outstanding researcher inputs, then stop.
3. `start` on an uninitialized template: read and follow `workflow/stages/00-initialize.md`,
   fresh path, beginning with its orientation. `adopt`, or an uninitialized template with
   materials under `project/inputs/existing/`: follow the same file's adoption path.
4. If state is `awaiting_approval` or `waiting_for_user`, report the exact gate or input and
   stop. Never infer approval from silence or from an earlier, different decision.
5. Otherwise (`resume`, `continue`, `next`) read the canonical file named by `current_stage`,
   verify its prerequisites (imported artifacts and researcher-asserted approvals recorded
   at adoption satisfy them), and follow it. If the required Plan or Goal mode is not active,
   give the researcher the exact mode command and stage invocation instead of imitating it.
6. Run only one bounded stage at a time. Do not use one Goal for the whole pipeline.
