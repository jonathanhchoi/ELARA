# Cloud materials and local processing

Google Drive, OneDrive, Dropbox, iCloud, and similar services are supported
locations for source materials and shared results. Pair them with a persistent
local working folder outside synchronization for active processing. The parent
agent manages this arrangement with the existing installer, imports, versioned
outputs, and file tools. This is a workflow instruction, not a background sync
service or a new research gate.

## Choose and record the locations

At Stage 00, or before a later stage if storage has changed, read the active
charter, DECISIONS.md, and any BOOTSTRAP.md report. Reuse the researcher's choices.
The installer's path detection is a hint: it neither proves synchronization nor
proves its absence. Inspect the actual location and available sync settings;
user-reported cloud use also triggers this guidance. Do not change account-wide
sync settings. Offline or mirrored files can avoid downloads but remain synced.

Recommend the local companion in the existing setup discussion. Record a
`Storage` section in the versioned charter, with subsequent changes in
DECISIONS.md, identifying:

- the absolute local working root, its authoritative `project/PROJECT_STATE.md`,
  and the cloud source locations whose originals must stay unchanged;
- a dedicated cloud export folder, the files or data classes allowed there,
  and whether it is shared with other people;
- the copying schedule (default: verified batch or stage checkpoints), local
  capacity, and any retention or access limits.

Resolve the roots, including links or junctions. Keep the cloud export folder
outside the local working root and use a dedicated destination that will not
overwrite source files. Never infer that a folder is private from its name.

Bundle any unresolved choice with the existing setup or charter discussion.
Once the arrangement and data route are authorized, routine copies within that
scope need no repeated approval. Selecting cloud storage does not authorize
sharing restricted data. A declined local setup is a recorded limitation, not
permission to silently relocate files or add a blanket cloud-storage ban.
In that case, keep the recorded active root and explain the expected I/O
limitation; use separately authorized local staging where possible. The local
arrangement below applies once adopted, never retroactively to a prepared run.

For a new workspace, the assistant runs
`python scripts/bootstrap.py --into <local folder> --source <verified clean kit>`.
Use a clean kit folder or ZIP, never the installed folder containing researcher
materials as the installation source: bootstrap could copy unrelated files or
merged instructions along with the kit. Reuse the verified clean download if
available, or obtain a clean upstream copy under `kit-updates.md`. Check that
the destination is writable, has enough space, and is outside known sync roots.
A folder directly under the home directory is a candidate, not a
guarantee. Work from the local root and use its interpreter and host definitions;
reopen the host there when required. Keep source paths available for Stage 00's
inventory and adoption imports. Bootstrap installs kit templates; it does not
migrate an existing research project or its approvals.

## Work locally

Keep one active project state. Its normal `project/` structure, run directories,
logs, frozen assignments, and output paths are rooted in the local workspace.
Keep live `.git` metadata, environments, caches, tests, extraction, repeated
searches, coding, validation, and document builds outside synchronization. Store
research intermediates and raw returns in the stage-declared local run paths,
never in a disposable session scratchpad. Preserve every required audit record.

Copy only the authorized inputs needed for the task, using the existing import
or acquisition paths. Verify source and destination SHA-256 values and sizes,
record their mapping in the input inventory or run manifest, and reuse the
verified local copy on repeated reads. Changed originals become new imported
versions, never automatic replacements. Check capacity before copying; stage
large collections in bounded portions and freeze each portion's local paths
before preparing its assignments. Do not evict inputs referenced by an open run
or promise that a cloud-only placeholder can be read offline. A missing download
or insufficient space is a concrete limitation to resolve, not a reason to
silently change the sample. Avoid repeated full-cloud-tree scans.

## Copy at verified checkpoints

At the recorded batch or stage boundary, the parent performs these steps serially:

1. Reconcile outputs and counts locally. Select verified, closed files and a
   consistent snapshot of state, ledgers, and required run records. Use an
   existing immutable checkpoint where available; otherwise ensure all writers
   to the selected files have stopped before copying them. Do not take a live
   recursive copy of a directory whose workers are still writing.
2. Assemble the snapshot under `project/runs/<run_id>/storage/` before
   the run closes. Record a manifest of relative paths, sizes, SHA-256 values,
   run/checkpoint identity, original working root, and omissions with reasons.
   Include a short README identifying it as an archival copy and naming the
   local root to resume. Copy only authorized data; omit disposable caches and
   environments. Keep live Git metadata local; a closed Git backup archive may
   be included only if requested and permitted.
3. Copy to a new versioned subfolder of the recorded cloud export folder. Never
   overwrite source materials or an earlier snapshot. Exclude the local staging
   folder itself and prior export snapshots from recursive collection. Verify
   destination bytes against the manifest and write a completion receipt last.
   An incomplete destination without that receipt is not a usable checkpoint.
4. Record the export location, verified hashes, time, and disposition in a
   versioned receipt under that run's `storage/` and reference it from the run
   manifest. Distinguish `copied to sync folder`, `upload confirmed` (only with
   service evidence), and `pending` or `failed`. File
   existence in a synced folder alone cannot prove remote availability. At a
   handoff to another computer or person, verify upload and destination access
   or explicitly report that the handoff is pending.

Do not wait for cloud uploads between individual assignments. If an export
fails, preserve the verified local snapshot and the partial destination, record
what remains, and continue authorized local work when the copying or retention
policy allows it. Retry at the next checkpoint under the same scope, verifying
already-copied bytes and using a new destination if any content conflicts.
Never delete the only verified copy, and report outstanding exports at stage
completion. A later retry records its receipt in the current open run; do not
append to a closed run directory. Keep the snapshot as it was at its stated
checkpoint rather than rewriting it to include its own later export receipt.
No unrequested background scheduler is needed.

## Resume and existing projects

Read the recorded storage locations before every stage and recovery. A cloud
snapshot is not a second active project. Do not choose between local and cloud
state using modification times, merge append-only logs automatically, or run
two writers from different copies. If the local workspace is unavailable,
reconcile the recorded checkpoint and paths before restoring or continuing.

Existing runs retain their fixed paths, seals, approvals, and raw records.
Installing this guidance does not relocate them. At a verified stopping point,
confirm that no worker or parent writer remains active or has an unknown
outcome; preserve the original state and records, verify copied bytes, and check
every dependency needed to resume. Do not rewrite sealed absolute paths to make
a copied run appear portable. If those bindings cannot be honored, resume the
run at its original root or follow `operational-recovery.md` for a separately
verified, authorized transition. New runs can use the local root once the
existing project state and dependencies have been carried forward and validated;
never replace that history with fresh templates or researcher-asserted approvals.

Google documents streamed files, locally mirrored files, and the performance
benefit of mirroring for extensive writes in
[Drive for desktop help](https://support.google.com/drive/answer/13401938?hl=en)
(accessed 2026-09-24). A separate unsynced working folder additionally keeps
ELARA's intermediate writes out of the synchronization workload; actual speed
depends on the files, cache, network, and device.
