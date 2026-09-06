---
name: "elr"
description: "Start a new project, adopt an existing one, show the menu of tools, resume, report status, or explain the empirical legal research pipeline. Use when the researcher says start, adopt, menu, tools, resume, continue, next, status, help, or tour, asks what ELARA can do, or asks which workflow stage to run."
---

# Route the empirical legal research workflow

Before any new stage or tool starts (including automatic transitions and recovery
runs), follow `workflow/shared/kit-updates.md` and run `scripts/check_update.py`.
Require `ready: true` before execution; use the update contract's limited
read-only planning exception when applicable; apply verified compatible updates automatically and use
freshly verified installed bytes if GitHub is unavailable. Investigate conflicts;
a declined specific change remains binding. Preserve an already-started run's
software. Help, tour, menu-only, and status need no check.

1. Read `AGENTS.md`, `PIPELINE.md`, `workflow/shared/execution-control.md`, and
   `project/PROJECT_STATE.md` completely (its `usage` key
   records the usage mode: `pipeline`, or `tools` for specific tools; absent means `pipeline`;
   its `checkpoints` key records how often the researcher wants extra pauses; absent means
   `none`; its `failure_handling` key records how individual failures in the Stage 11 coding
   run are decided; absent means `autonomous`), and `project/BOOTSTRAP.md` if it exists. Speak in plain language to a legal
   scholar who may never have used a terminal, run every command yourself, and be low-touch:
   `workflow/shared/guardrails.md` section 11 lists the only reasons to stop and ask.
2. `help` or `tour`: without touching any file, give the orientation in
   `workflow/stages/00-initialize.md` (what ELARA does and does not do, the six steps, gates,
   the commands, the menu, the publication profile), say where this project stands, and stop.
   `status`: without touching any file, report the current stage and status, the usage mode,
   approvals and their basis (verified or researcher-asserted), active artifact versions, the
   last run, and outstanding researcher inputs, then stop.
3. `start` on an uninitialized template: read and follow `workflow/stages/00-initialize.md`,
   fresh path, beginning with its orientation and the usage-mode question (whole pipeline or
   specific tools). `adopt`, or an uninitialized template with existing materials (under
   `project/inputs/existing/`, listed in `project/BOOTSTRAP.md`, or described by the
   researcher): follow the same file's adoption path.
4. `menu` or `tools`, or a named stage or utility: present the menu in `PIPELINE.md` in plain
   language and run what the researcher picks. On an uninitialized template, Stage 00 runs
   first, from its orientation, with the tool as the aim (its two-question specific-tools
   setup). If the tool's prerequisites are not recorded, first satisfy them through Stage 00's
   adoption path (import what exists, record researcher-asserted approvals, note
   limitations), then run it; a utility never changes `current_stage`; an earlier stage runs
   as a versioned recovery route.
5. Reconcile `awaiting_approval` or `waiting_for_user` with current user instructions
   and applicable decisions before repeating a request. Preserve state history, clear
   only resolved inputs, and validate the corrected state. For operational recovery,
   call `scripts/recovery_decision.py` with hash-bound authority and evidence; route
   `repair` to autonomous verification, `wait_external` to a preserved checkpoint,
   and only `request_user` to a concrete missing decision. Assistant-written state
   cannot create restrictions. Never infer approval from silence or another decision.
6. Otherwise (`resume`, `continue`, `next`): in `specific tools` mode (`usage: tools`), reopen
   the menu and offer to continue `current_stage` as one of the choices; in `pipeline` mode
   read the canonical file named by `current_stage`, verify its prerequisites (imported
   artifacts and researcher-asserted approvals recorded at adoption satisfy them), and follow
   it. Create or reconcile the native stage plan before work.
   For interrupted Stage 11 work, read `workflow/shared/operational-recovery.md`,
   verify `run_checkpoint` when present, and reconcile current disk evidence.
   Never equate a live verifier with active coding or repeat an unchanged failure.
   On Claude Code use `TaskCreate`, `TaskUpdate`, and `TaskList`; on resume reconcile the task list from disk.
   For `long_running: true`, resume an equivalent goal covering the authorized work.
   Otherwise give `/goal <goal_condition>` when activation is available; use the
   foreground fallback when unavailable. Never replace an unrelated active goal.
7. When a stage ends with no gate or input pending, reconcile the native plan, summarize
   plainly what was produced and
   what comes next, then in `pipeline` mode continue into the next stage in this session
   unless a stop condition in `workflow/shared/guardrails.md` section 11 holds for it (it
   needs something only the researcher can supply, it would spend beyond the recorded
   budget, it acts outside the folder, or `checkpoints` asks for a pause); in `specific
   tools` mode offer the menu. Agreement to continue is not gate approval. Run only one
   bounded stage at a time; never one goal for the whole pipeline.
