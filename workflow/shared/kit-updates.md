# Check ELARA before starting new work

Before each new stage or optional tool begins, the parent checks the installed
ELARA against `jonathanhchoi/ELARA` on GitHub, branch `main`. This is an
operational prerequisite, separate from the stage's research approvals.
"Latest" means the exact commit on that branch at the successful check, not
the largest release number. Never use a project's own Git remote as upstream.

## When to check

- Check before Stage 00, every automatic next-stage transition, a selected
  stage or tool, and every new recovery run of a previously completed stage.
  Run the check before substantive work, including a stage's read-only plan
  or interview. Reading routing instructions and installation evidence is allowed.
- Check again when execution follows an approved plan or a long pause before
  any run has begun. A prior session's check is not permission for a new run.
- An existing run resumes with its recorded software and frozen files. Do not
  update it mid-run or before each batch, retry, or coding assignment. Follow
  `operational-recovery.md` for an explicitly reviewed migration.
- `help`, `tour`, `menu`, and `status` remain available without a check or any
  file changes. Once the researcher picks work from the menu, check it.
- Only the parent checks and asks for updates. Restricted workers never
  contact GitHub, update the kit, or ask the researcher for update permission.
  Maintaining ELARA itself is not a research-stage invocation.

## Check, ask, update, verify

1. Run this read-only command with the canonical stage or utility identifier:

   ```text
   python scripts/check_update.py --stage 03-feasibility-audit --json
   ```

   Only `ready: true` / exit 0 permits starting the stage, subject to its other
   prerequisites. The helper verifies the installation's recorded file hashes
   as well as its commit. For a ZIP or older installation without an exact
   identity, it compares local files with an archive of the checked commit.
   It writes nothing to the project and sends no research material to GitHub.

2. If current, continue without asking. If an update is available, preview the
   exact proposed commit using `python scripts/bootstrap.py --update --ref
   <full-commit> --dry-run --json`. Explain the installed and available versions
   (or commit identifiers when a version is unknown), summarize the changes
   from the actual GitHub comparison and preview, and disclose conflicts.
   Ask the researcher to agree to that update before starting the new stage.
   Approval to start research, acceptance of a plan, and approval of an earlier
   update are not approval of this update. Silence is never approval.

3. A declined update leaves the new stage paused. An unavailable GitHub check
   also leaves it paused until verification succeeds, including on a timeout
   or rate limit. Do not use an old result, an offline exception, or an
   `assistant-default` to proceed. Invalid identity, modified files, protected
   files, or an unfinished update require inspection and resolution first.
   Explain the actual issue; do not repeatedly ask an unchanged question.

4. After explicit agreement, run `python scripts/bootstrap.py --update --ref
   <approved-full-commit> --require-clean --json`. This is narrow permission to
   update kit-owned files and managed ELARA blocks. Preserve the researcher's
   files, project state, ledgers, models, prompts, codebooks, schemas, and frozen
   run bindings. Update permission does not authorize a scientific amendment
   or removal of a protection. Never substitute `git pull` in a research folder.
   Resolve conflicts through the protected-update/migration process; never
   replace an unknown baseline with local bytes merely to make an update pass.
   A legacy ZIP can need a verified historical source to establish its baseline;
   never guess its original revision. Files removed upstream are retained and
   reported for review, not silently deleted or treated as current.

5. Require a successful bootstrap report, a completed installation, and no
   outstanding conflicts or `project/ELARA_UPDATE_PENDING.json`. Run the doctor,
   workflow validator, and wrapper check. Complete the existing model-readiness
   advisory without changing the approved research model. Reread `AGENTS.md`,
   this contract, and the current canonical stage from disk. If the host still
   holds an old skill or worker definition, use its supported reload/restart
   before new work; do not proceed under instructions held over from before
   the update. Preserve the pending stage and approvals across that restart.

6. Re-run the live check before starting. If GitHub has moved since the
   approved commit, show the additional changes and obtain agreement to the
   newer update. Do not silently expand consent to a different commit. Each
   new stage gets its own check; there is no session-wide or daily bypass.

## Records and interrupted installations

The installer records source identity separately from `installed_commit` and
`installation_complete` in `project/ELARA_MANIFEST.json`. The project's
`workflow_version` is historical research state, not installation evidence.
A partial update never claims to be current. An update writes
`project/ELARA_UPDATE_PENDING.json` before changing kit files and removes it
only after installation and setup verification succeed. An interruption leaves
that marker in place. Inspect the retained baseline and actual bytes, then
complete the approved update; do not clear the marker just to advance.

Keep check output in the conversation during read-only planning. Once the
stage is authorized to write, archive the successful JSON as
`kit_update_check.json` in its new run directory and reference it in the run
manifest. It records the stage, check time, exact installed/upstream commit,
and result. Record an update decision with its exact target commit and the
researcher's actual answer in `DECISIONS.md` when writes are allowed; the
bootstrap report preserves installation results. Do not allocate a run, edit
project state, or append a ledger merely to record a check during Plan Mode.
If no run has begun, an update remains a separate maintenance action after the
researcher agrees and the host permits writes. On resume, recover decisions
from those records and the conversation; never manufacture consent.

Existing installations need one update to acquire this contract and checker.
After that, all stage entry routes require it. This is an executable check
called by the agent's routing instructions, not an operating-system lock on
arbitrary commands run outside ELARA.
