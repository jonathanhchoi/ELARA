---
name: "elr"
description: "Start, resume, or report status for the empirical legal research pipeline. Use when the researcher says start, resume, continue, next, status, or asks which workflow stage to run."
---

# Route the empirical legal research workflow

1. Read `AGENTS.md`, `PIPELINE.md`, and `project/PROJECT_STATE.md` completely.
2. If no initialized state exists, read and follow `workflow/stages/00-initialize.md`.
3. If state is `awaiting_approval` or `waiting_for_user`, report the exact gate or input and
   stop. Never infer approval from silence or from an earlier, different decision.
4. Otherwise read the canonical file named by `current_stage`, verify its prerequisites,
   and follow it. If the required Plan or Goal mode is not active, give the researcher the
   exact mode command and stage invocation instead of imitating that mode.
5. Run only one bounded stage at a time. Do not use one Goal for the whole pipeline.
