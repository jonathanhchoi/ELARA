# Start here

ELARA is installed in this folder. From now on the assistant walks you through
everything: it explains what ELARA does, asks how you want to use it (the whole
pipeline, or specific tools from a menu), and then takes one step at a time,
asking one question at a time and stopping wherever a decision is yours. You do
not need to read the rest of this repository first.

- **Coming back later:** open this folder in Claude Code or Codex and type
  `/elr` (Claude Code) or `$elr` (Codex). `help` explains, `status` says where
  you are, `tools` shows the menu, `resume` picks up where you left off.
- **Manual setup, options, and the full reference:** `README.md`.
- **Nothing here is sent anywhere by itself.** ELARA runs where you opened it;
  it asks before it processes your material with a hosted model.

## For the assistant (Claude Code or Codex) reading this after installation

Follow these steps in this session; do not wait for a restart.

1. Read `AGENTS.md`, `PIPELINE.md`, and `project/PROJECT_STATE.md` completely.
   `AGENTS.md` is this repository's standing instruction file; the same rules
   apply now, even though your session started before it existed. If
   `scripts/install.py` reported a `CONFLICT`, `PIP`, or `DOCTOR` problem,
   resolve it with the researcher first (rerun `python scripts/doctor.py` to
   confirm) — do not proceed on a broken environment.
2. If `project/PROJECT_STATE.md` shows an initialized project (`project_slug`
   is not `null`), this is a reinstall or upgrade: report where the project
   stands as `status` would, then continue as `resume` would.
3. Otherwise read `workflow/stages/00-initialize.md` completely and follow it
   from its **Orientation** section: give the short orientation, ask whether the
   researcher wants to follow the whole pipeline or use specific tools
   (present `workflow/shared/tool-menu.md`), and then take the fresh path,
   the adoption path, or the tools path as that stage directs. If
   `scripts/install.py` listed files that were already in this folder, offer to
   copy — never move — the relevant ones into `project/inputs/`
   (`project/inputs/existing/` for work already done).
4. The `/elr` and `$elr` commands become available the next time the host
   starts in this folder; nothing you do now depends on them, because the
   canonical files under `workflow/` are the instructions. Tell the researcher
   how to come back (the bullet above) when this session's step ends.
