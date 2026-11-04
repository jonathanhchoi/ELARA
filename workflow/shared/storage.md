# Local work and cloud exports

Google Drive, OneDrive, Dropbox, iCloud, and similar folders are supported
project homes. The researcher keeps opening that folder; ELARA works in a
persistent local copy and copies results back. Explain this briefly as how the
kit works, not a setup decision; honor an explicit different preference and
data-use limits. Routine setup and copying need no separate approval.

## Resolve before reading state

Before any stage, utility, resume, status, or update, run the read-only
`python scripts/storage.py status --root <folder the researcher opened>`. For a
managed project, use its `working_root` for state, commands, the interpreter,
and workers, then reread the active kit's instructions; also read the home's
`BOOTSTRAP.md`, original instructions, and input locations. Status, help, and
Plan Mode never create a workspace, copy files, or change state. A missing or
mismatched workspace is a recovery problem: never fall back to the cloud copy's
old template or ask the researcher to move the project. A synced record is not a
lock between computers, and a copied folder is not permission for a second writer.

## Setup and existing projects

The installer configures new cloud projects. Otherwise run `python
<clean-kit>/scripts/storage.py setup --root <project-home> --kit <clean-kit>`
from a verified clean kit, never a mixed installed project; re-run an
interrupted setup once, then follow "When something breaks" in
`operational-recovery.md`. For existing history setup returns
`needs_transition`: carry state, ledgers, approved files, and dependencies
forward at a verified stopping point, keep prepared runs at their sealed paths,
and record it with `python scripts/storage.py bind --root <project-home>
--working-root <verified-local-project>`. Record the arrangement (home, local
root, results destination, contents, retention) in the charter's Storage
section and later changes in `DECISIONS.md`.

## Work locally, export at the end of each stage

All processing, worker returns, environments, and caches stay at the local
root; originals stay where the researcher placed them. Stage authorized inputs
with `python scripts/storage.py stage --root <home> --source <file> --into
project/inputs/<name>_v001.<ext>`, which verifies and hashes the copy; a changed
original becomes a new import. At the end of each stage, and at an orderly
handoff, run:

```text
python scripts/storage.py export --root <home> --label <stage-id>
```

It copies the deliverables as files (state, the append-only logs, kit issue
reports, every active output; a large output folder becomes one zip) and each
run not yet exported as one zip into `ELARA_Results/<export-id>/`, with a
manifest and `COMPLETE.json` written last. Originals and their input copies are
not sent back, a run in progress waits for its end, and batch checkpoints are
not exported. A project with no cloud home needs none (`not_needed`).

Copy failures never delay research. At stage boundaries and writable resumes,
run `python scripts/storage.py retry --root <home-or-local-root>` once for
pending exports; a remaining problem follows "When something breaks". Retry the
copy, never the model work. If the destination holds different bytes, keep them
and publish under a new name (`storage.py publish --snapshot <id> --name
<new-name>`). `copied_to_sync_folder` confirms bytes in the synced folder, not
a cloud upload. On another computer, restore a missing workspace from a
verified checkpoint; never choose between copies by timestamp.
