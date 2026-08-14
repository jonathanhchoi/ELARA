---
name: "elr-code-observations"
description: "Fan out frozen empirical legal research coding or audit work with exactly one observation or unit per isolated subagent. Use during Stages 08, 11, 12, or 15 after the unit manifest, prompt, schema, retry rule, and output paths are fixed."
---

# Code observations with isolated subagents

1. Read `AGENTS.md`, `project/PROJECT_STATE.md`, and
   `workflow/shared/observation-fanout.md` completely.
2. Read the active canonical file under `workflow/stages/`; this skill implements its
   per-unit execution contract and never changes stage gates or frozen instruments.
3. Validate the immutable assignment manifest and its canonical visible-prompt and response-schema
   hashes before spawning anything. Give each fresh worker exactly one assignment and one unique
   return path; workers never edit shared files.
4. Require workers to send their return envelope through `python scripts/unit_fanout.py submit`;
   they do not write the worker-return path directly or expose substantive labels in receipts.
5. Use the Codex Goal adapter specified by the shared contract. If its required mode is not
   active, issue the exact handoff for `$elr-code-observations` instead of imitating that mode.
6. Validate returns and update ledgers serially after each bounded wave. Resume from files,
   preserve every attempt, expose only operational progress, and reconcile before merging.
