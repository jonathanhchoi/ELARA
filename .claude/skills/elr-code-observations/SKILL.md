---
name: "elr-code-observations"
description: "Run empirical legal research coding or audit assignments in parallel, with exactly one observation or unit per isolated sub-agent. Use during Stages 08, 11, 12, or 15 after the complete assignment list, prompt, required output format, retry rule, and output paths are fixed."
---

# Code observations with isolated subagents

The parent must satisfy `workflow/shared/kit-updates.md` with
`scripts/check_update.py` and `ready: true` before a new stage run begins.
Use compatible automatic updates and verified installed fallback; a declined
specific change remains binding. Within an existing run, preserve the
recorded software; do not repeat update checks per worker, batch, or retry.

1. Read `AGENTS.md`, `project/PROJECT_STATE.md`,
   `workflow/shared/execution-control.md`, and
   `workflow/shared/observation-fanout.md` completely.
2. Read the active canonical file under `workflow/stages/`; this skill implements its
   per-unit execution contract and never changes stage gates or frozen instruments.
3. Validate the immutable assignment manifest and its canonical visible-prompt and response-schema
   hashes before spawning anything. Give each fresh worker exactly one assignment and one unique
   return path; workers never edit shared files.
4. For a new or explicitly migrated run, require the assigned dispatch ticket start command before
   any assignment read, and its finish command after submission. Controller-only discovery and
   verification steps do not start scientific assignments. Require workers to send their return
   envelope through `python scripts/unit_fanout.py submit`;
   they do not write the worker-return path directly or expose substantive labels in receipts.
5. Run the fan-out through the host's orchestrator as the shared contract directs — never one
   hand-launched worker at a time and never an all-tools agent. On this host that means
   the saved `elr-observation-fanout` workflow (`.claude/workflows/`), which you launch
   yourself with the Workflow tool (`name` plus `{ "run_dir": ... }`) and relaunch until
   nothing is pending; every agent in it is the restricted `elr-worker` type. If dynamic
   workflows are unavailable, launch `elr-worker` directly, one assignment per call, and
   record that route.
6. The parent keeps the one stage goal and native plan; workers never create either. Validate
   returns and confirm completed slots are released individually; update the plan and ledgers serially at checkpoints. Resume from
   files, preserve every attempt, expose only operational progress, and reconcile before merging.
