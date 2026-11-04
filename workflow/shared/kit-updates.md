# Check ELARA before starting new work

Before each new stage or optional tool (including Stage 00, automatic
transitions, and new recovery runs), the parent checks the installed kit against
`jonathanhchoi/ELARA` on GitHub, branch `main`, after resolving storage under
`storage.md`. Never use the research project's own Git remote. Existing runs
resume under their recorded software with no check per batch or retry. Routing,
status, help, and menu requests stay read-only. Only the parent checks; workers
never contact GitHub, and no research material is sent.

Updates never hold up research:

1. Run `python scripts/check_update.py --stage <stage-id> --json`. `ready: true`
   means the stage may start.
2. On `update_available`, when writes are authorized, explain the change in a
   line and run the same command with `--auto-update`. It installs that exact
   commit only when the installer's preview shows no conflicts, verifies it,
   and returns `updated`; then reread `AGENTS.md`, this file, and the stage.
   During Plan Mode, plan on the installed instructions and install on leaving
   Plan Mode. Honor any explicit researcher limit on updating; a declined
   update stays declined.
3. When an update would conflict (`update_deferred`), GitHub cannot be reached
   (`verified_installed`, or `unverified` without a recorded identity), or
   ELARA's own files here differ from their installed record
   (`installed_modified`), the result is still `ready: true`: run the stage on
   the installed version, pass its `notice` to the researcher once in plain
   words, and do not repeat it at later stages unless it changes. Never edit
   kit files, adopt changed bytes as a clean baseline, or remove protection to
   force an update.
4. The one case that waits is `unfinished_update`: an installation stopped
   part-way and left `project/ELARA_UPDATE_PENDING.json`. Run `--auto-update`
   once (it resumes the recorded commit); if it still does not finish, follow
   "When something breaks" in `operational-recovery.md`. Never clear the
   marker by hand. (`storage_unresolved` is a workspace to recover under
   `storage.md` first.)

Once writes are authorized, archive the check output as `kit_update_check.json`
in the new run directory and reference it in the run manifest; it records the
ELARA commit the run used. Do not allocate a run merely to record a Plan Mode
check. Before an update while a run is still open, record the kit
files that run depends on in `project/ELARA_PROTECTED_PATHS.json`
(`schema_version: "1.0"`, `bindings` mapping paths to approved SHA-256 hashes);
the installer then defers the update instead of replacing them. A successful
installation never changes a frozen research file or approval.
