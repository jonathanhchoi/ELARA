# Agent-managed storage

Google Drive, OneDrive, Dropbox, iCloud, and similar folders are supported
project homes. The researcher keeps opening that folder. ELARA automatically
maintains a persistent local working folder and copies verified results back.
Explain this briefly as configured behavior, not a storage advisory or another
setup decision. Honor an explicit different preference and existing data-use
limits. Routine setup and copying within this project's scope need no separate
approval; ask only for a genuine unresolved researcher choice.

The coding agent chooses inputs, batch sizes, checkpoint contents, timing, and
recovery from the actual project and tools. `scripts/storage.py` supplies file
operations, not a research policy engine or background scheduler. Use these
primitives or equivalent verified operations when the environment requires it,
retaining the same evidence and invariants.

## Resolve before reading state

Before any stage, utility, resume, status, or update, run the read-only
`python scripts/storage.py status --root <folder opened by the researcher>`.
For a managed project, use its `working_root` for state, commands, the local
interpreter, and workers. Resolve storage before the kit-update check, then
reread the active kit's instructions. Status/help/Plan Mode never create a
workspace, import files, retry exports, or change state. A missing or mismatched
workspace is a recovery problem; never fall back to the cloud's old template.

`project/ELARA_STORAGE.json` in both locations records one project identity and
one active working root. Keep the original folder as the user's entry point;
use the host's supported working-directory and file-access controls for the
local folder. Verify the parent and restricted workers can use it before a run.
Do not weaken worker restrictions or ask the researcher to manually relocate
the project. If host permission is required, request only the concrete access
needed through the host. A copied folder is not permission for a second writer;
a synced record is not a distributed lock between computers.

Read the project home's BOOTSTRAP report, original instructions, and input
locations as well as the active local records. Preserve the researcher's
instructions there; do not lose them when using the clean local kit.
Show result links in the project home once copied; report the local path when
a result is still awaiting export.

## Setup and existing projects

The installer configures new cloud projects automatically from its clean kit
source. The working folder defaults to the platform's local application
data/state directory, not a disposable cache. `ELARA_WORKSPACE_HOME` can select
another base; the agent may choose it when capacity or local settings require.
Path detection is a hint, not proof that synchronization is present or absent.
Check the actual location, links, available space, and access. User-reported
cloud use also triggers setup; do not change account-wide sync settings.

For an unconfigured fresh project the assistant runs:

```text
python <clean-kit>/scripts/storage.py setup --root <project-home> --kit <clean-kit>
```

Use a verified clean kit download or clone, never a mixed installed project as
the source. Reuse its exact installed commit under `kit-updates.md`. An interrupted
setup preserves its local files; inspect and finish that installation before
binding it. Do not delete or replace an unrecognized local folder.

For existing history, setup returns `needs_transition`. The agent inspects it,
preserves a checkpoint, and carries forward state, ledgers, approved files,
and dependencies at a verified stopping point. Do not replace history with blank
templates or asserted approvals. Prepared runs keep their fixed paths, seals,
software, and raw records until a verified operational transition is possible
under `operational-recovery.md`; never rewrite sealed paths merely to make a
copy run. Once the agent has verified the local project, record the transition:

```text
python scripts/storage.py bind --root <project-home> --working-root <verified-local-project>
```

Record the arrangement in the charter's Storage section and subsequent changes
in DECISIONS.md: project home, active local root, results destination, permitted
contents, copying schedule, and retention/access limits. The normal default is
verified batch checkpoints, stage completion, and orderly handoff. Present the
arrangement with the existing charter discussion, not as a prerequisite asking
whether to set up local processing. Compatible kit updates must refresh both
the active kit and the home's entry instructions through the protected installer;
never use one copy's update evidence for the other.

## Work and checkpoint locally

Keep one active state and all intensive processing, live databases, worker
returns, environments, caches, builds, and new Git metadata at the local root.
Original materials remain where the researcher placed them. Stage only the
authorized inputs needed, with sizes and SHA-256 hashes; reuse verified copies.
For example, `storage.py stage --root <home> --source <file> --into
project/inputs/source_v001.txt` verifies a copy and records provenance.
Existing adoption paths under `project/artifacts/imported_vNNN/` remain valid
with equivalent copy verification. Changed originals become new imports, never
automatic replacements of frozen inputs. Handle large collections in bounded
portions. The assistant downloads readable bytes as needed and diagnoses missing
placeholders or space; it handles routine copying itself.

At a useful checkpoint, the parent reconciles results and selects a consistent
set of closed files: deliverables, state, ledgers, prompts, raw returns, and
other records needed to audit or recover that checkpoint. Include the exact kit
identity and needed dependency paths. Use an immutable checkpoint or stop the
selected files' writers first. Never recursively copy a live worker directory
or live SQLite database and call it a checkpoint. The agent decides how to
obtain a consistent snapshot and records omissions with reasons.

Save a selection JSON with `files` (relative file paths) and `omissions` (if any)
under `project/storage/`, then run:

```text
python scripts/storage.py snapshot --root <home> --selection <selection.json> --label <run-or-checkpoint>
python scripts/storage.py publish --root <home> --snapshot <returned-snapshot-id>
```

Snapshots and attempt receipts live under `project/storage/`, outside sealed
run directories. Exports appear under `ELARA_Results/<snapshot-id>/` in the
project home, with a file manifest, original working root, and `files/` holding
the selected paths. Publish verifies destination bytes and writes COMPLETE.json
last. A missing marker or mismatched manifest/files means an incomplete or
damaged export. Exclude previous exports, staging records, live Git metadata,
and disposable environments from subsequent snapshots. Never overwrite source
materials, earlier exports, or the only verified local copy.

## Retry and resume

At checkpoints and writable resumes, the parent automatically runs
`python scripts/storage.py retry --root <home-or-local-root>` to attempt pending
exports once, then diagnoses remaining problems. A failed export preserves
local successes; retry the copy, not model assignments. Continue authorized local
work when capacity and the copying/retention policy allow it. If destination
bytes conflict, preserve them and use `publish --name <new-folder-name>` after
review. Report pending results at completion or handoff. No per-unit upload wait
or fixed retry loop is required.

`copied_to_sync_folder` confirms verified filesystem bytes, not cloud upload.
Only report upload or recipient access as confirmed with service evidence.
On another computer, a missing workspace requires reconciliation and restoration
from a verified checkpoint under the existing recovery contract. Never choose
between copies by timestamps, merge append-only logs, or silently start another
active state. Retain necessary local inputs and audit records until the agent
has verified that recovery and retention requirements are met.
