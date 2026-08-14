# Project workspace

This directory contains one empirical legal research project. Repository
instructions and canonical prompts live outside `project/`; research stages may
read those files but write only their declared outputs here.

## Start

1. Read `inputs/README.md` and place the materials you want inventoried in
   `inputs/`.
2. From the repository root, run `$elr start` in Codex or `/elr start` in Claude.
3. Review the stage 00 project charter and input inventory. The pipeline will not
   proceed until you approve the charter.

Do not populate `PROJECT_STATE.md` by hand to skip initialization. The router
uses its front matter to resume safely in a fresh session.

## What lives here

| Path | Purpose | Mutation rule |
|---|---|---|
| `PROJECT_STATE.md` | Current stage, status, active versions, approvals, and next user inputs | Mutable router; update only through verified transitions |
| `DECISIONS.md` | Researcher choices and version-pinned gate dispositions | Append only |
| `RUN_LEDGER.md` | Started, checkpoint, completed, failed, and interrupted run events with exact counts | Append only |
| `DEVIATIONS.md` | Departures, amendments, and their dispositions | Append only |
| `inputs/` | User-supplied source material | Immutable after stage 00 inventory |
| `runs/<run_id>/` | Prompts, raw responses, parsed responses, logs, and run-local evidence | Unique and immutable after close |
| stage-declared paths | Versioned plans, manifests, data, analyses, audits, and packages | New `_vNNN` version for every rerun or correction |

Directories not present in the clean kit are created only when a stage declares
and needs them. Do not treat an empty or absent output directory as evidence that
a stage ran.

## Immutability and resume

- Never overwrite an inventoried input, approved artifact, raw response, human
  code, adjudication, or prior correction.
- Add replacements under new names. Reruns receive unique run IDs and artifacts
  receive the next `_vNNN` suffix.
- Downstream stages use the exact paths pinned in `active_artifacts`; “newest file
  in a folder” is not a valid dependency rule.
- To resume, open the same repository copy and run `$elr resume` or `/elr resume`.
  An interrupted run is inspected and continued or formally superseded; it is
  not silently restarted.

## Sensitive and large material

The root `.gitignore` excludes ordinary contents of `inputs/` and `runs/`, but
ignore rules are not access control, encryption, deletion, or proof of
authorization. Check cloud synchronization, backups, model routing, and
institutional policy before adding sensitive material — and if this copy is a
Git repository, also check `git status` and its history; if it is a plain ZIP
copy, those Git checks do not apply, but sync services and backups can still
retain data. Do not place credentials or secrets anywhere in this directory.

Before transmitting any non-public text to a hosted model, complete the stage 06
authorization gate. If a replication package cannot redistribute a source, give
it a truthful access procedure or synthetic test fixture rather than including
restricted text or pretending the package is complete.

The detailed contract is in `workflow/shared/artifact-contract.md`.
