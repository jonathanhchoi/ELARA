---
name: "elr"
description: "Start a new project, adopt an existing one, show the menu of tools, resume, report status, or explain the empirical legal research pipeline. Use when the researcher says start, adopt, menu, tools, resume, continue, next, status, help, or tour, asks what ELARA can do, or asks which workflow stage to run."
---

# Route the empirical legal research workflow

1. Read `AGENTS.md`, `PIPELINE.md`, and `project/PROJECT_STATE.md` completely (its `usage` key
   records the usage mode: `pipeline`, or `tools` for specific tools; absent means `pipeline`),
   and `project/BOOTSTRAP.md` if it exists. Speak in plain language to a legal scholar who may
   never have used a terminal, and run every command yourself.
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
5. If state is `awaiting_approval` or `waiting_for_user`, report the exact gate or input and
   stop. Never infer approval from silence or from an earlier, different decision.
6. Otherwise (`resume`, `continue`, `next`): in `specific tools` mode (`usage: tools`), reopen
   the menu and offer to continue `current_stage` as one of the choices; in `pipeline` mode
   read the canonical file named by `current_stage`, verify its prerequisites (imported
   artifacts and researcher-asserted approvals recorded at adoption satisfy them), and follow
   it. If the required Plan or Goal mode is not active, give the researcher the exact mode
   command and stage invocation instead of imitating it.
7. When a stage ends with no gate or input pending, summarize plainly what was produced and
   what comes next, then offer it: the next stage in `pipeline` mode (run it on the
   researcher's agreement, in this session), the menu in `specific tools` mode. Agreement to
   continue is not gate approval. Run only one bounded stage at a time; never one Goal for
   the whole pipeline.
