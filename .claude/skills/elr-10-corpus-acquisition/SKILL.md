---
name: "elr-10-corpus-acquisition"
description: "Run ELR stage 10-corpus-acquisition: Acquire and audit the frozen corpus. Use when this is the current stage in project/PROJECT_STATE.md or when the researcher explicitly requests this recovery stage."
disable-model-invocation: true
---

# Run elr-10-corpus-acquisition

1. Read `AGENTS.md`, `project/PROJECT_STATE.md`, `workflow/shared/guardrails.md`, and
   `workflow/shared/artifact-contract.md` completely.
2. Read `workflow/stages/10-corpus-acquisition.md` completely and follow it as the single source of substantive
   instructions for this stage.
3. Confirm that the stage is current and its prerequisites and approvals are satisfied
   (imported artifacts and researcher-asserted approvals count). If the project is
   uninitialized (`project_slug` is null), run Stage 00 first, from its orientation, with this
   stage as the aim. If it is not current and the researcher chose it explicitly (this skill,
   the menu, or by name), first satisfy its prerequisites through Stage 00's adoption path,
   then run it; otherwise stop.
4. Honor the stage's mode handoff. A skill cannot switch Plan or Goal mode by itself.
5. Do not cross the stage's human gate. Update state and append the run ledger only as the
   canonical stage directs. At the end, summarize plainly and offer the next step per the
   usage mode (`usage` in `project/PROJECT_STATE.md`): the next stage in `pipeline` mode,
   the menu in `specific tools` mode.
