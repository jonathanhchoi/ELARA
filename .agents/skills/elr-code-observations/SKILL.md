---
name: "elr-code-observations"
description: "Run empirical legal research coding or audit assignments in parallel, with exactly one observation or unit per isolated sub-agent. Use during Stages 08, 11, 12, or 15 after the complete assignment list, prompt, required output format, retry rule, and output paths are fixed."
---

# Code observations with isolated subagents

First resolve the active root using read-only `scripts/storage.py status` under `workflow/shared/storage.md`, before state or updates.
The parent must satisfy `workflow/shared/kit-updates.md` with `scripts/check_update.py` and `ready: true` before a new stage run begins.
Use compatible automatic updates and verified installed fallback; a declined
specific change remains binding. Within an existing run, preserve the
recorded software; do not repeat update checks per worker, batch, or retry.

1. Read `AGENTS.md`, `project/PROJECT_STATE.md`,
   `workflow/shared/execution-control.md`, and
   `workflow/shared/observation-fanout.md` completely.
2. Read the active canonical file under `workflow/stages/`; this skill implements its
   per-unit execution contract and never changes stage gates or frozen instruments.
3. Prepare, check, and close the run with `python scripts/coding_run.py` and the stage's settings
   (`workflow/templates/coding_run_settings.md`), never a driver: launch the block its `next` step
   names, then `check --apply`. One assignment and return path per worker; no shared edits.
4. Each worker writes its return envelope to the draft path it is given and submits it with
   `python scripts/unit_fanout.py submit --input <draft-path>`; workers do not write the
   worker-return path directly or expose substantive labels in receipts. One failed worker never
   stops the others; run the launcher again for whatever is still pending.
5. Run the fan-out through the host's orchestrator as the shared contract directs — never one
   hand-launched worker at a time and never an all-tools agent. On this host that means
   the kit's `elr_worker` custom sub-agents (`.codex/agents/`), spawned by name in non-forked contexts, one per
   assignment listed by the `discover` command that `python scripts/coding_run.py check` prints,
   in a bounded rolling pool under the stage completion contract. Close terminal handles when
   supported and refill each freed slot. Never reuse a terminal worker context.
   Use foreground execution without a covering authorized goal; never code units in your own context.
6. The parent keeps the completion contract and plan; workers never create either. Validate
   returns and update the plan and ledgers serially at checkpoints. Resume from files, preserve
   every attempt, expose only operational progress, and reconcile before merging.
