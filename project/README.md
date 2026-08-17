# Project workspace

This directory contains one empirical legal research project. Repository
instructions and canonical prompts live outside `project/`; research stages may
read those files but write only their declared outputs here.

## Start

1. Read `inputs/README.md` and place the materials you want inventoried in
   `inputs/`. If you are bringing an existing project (a question, a codebook,
   coded data, results, a draft), you may put those materials in
   `inputs/existing/` — or leave them where they already are in the folder ELARA
   was installed into, or name their path; nothing has to move.
2. From the repository root, run `$elr start` in Codex or `/elr start` in Claude
   for a new project, `$elr adopt` / `/elr adopt` for an existing one, or
   `$elr menu` / `/elr menu` to pick a specific tool. `$elr help` / `/elr help`
   explains the workflow at any time. (If ELARA was installed by the paste-in
   message in the root README, the assistant has already started this for you.)
3. Review the stage 00 project charter and input inventory (and, on the
   adoption path, the adoption map and the approvals you asserted). The
   pipeline will not proceed until you approve the charter.

Do not populate `PROJECT_STATE.md` by hand to skip initialization. The router
uses its front matter to resume safely in a fresh session.

## What lives here

| Path | Purpose | Mutation rule |
|---|---|---|
| `PROJECT_STATE.md` | Current stage, status, active versions, approvals, and next user inputs; its `usage` key records the usage mode (`pipeline` for the whole pipeline, `tools` for specific tools) | Mutable router; update only through verified transitions |
| `BOOTSTRAP.md` | The installer's report: how the kit was installed, what the folder already contained, which Python to use, the doctor's result | Written by `scripts/bootstrap.py`; a new section per run |
| `DECISIONS.md` | Researcher choices and version-pinned gate dispositions | Append only |
| `RUN_LEDGER.md` | Started, checkpoint, completed, failed, and interrupted run events with exact counts | Append only |
| `DEVIATIONS.md` | Departures, amendments, and their dispositions | Append only |
| `inputs/` | User-supplied source material | Immutable after stage 00 inventory |
| `PUBLICATION_PROFILE_vNNN.md` | Your venue, audience, tone, voice, prohibited constructions, citation style, and manuscript QA preferences, from `workflow/templates/publication_profile_template.md`; pinned in state as `publication_profile` and read by Stages 17 and 19 and the manuscript utilities | New `_vNNN` version for every change; governs prose only |
| `artifacts/imported_vNNN/`, `artifacts/adoption_map_vNNN.md` | Adoption path only: unchanged copies of your existing files, pinned as the artifacts later stages use, and the stage-by-stage map of what they satisfy | Immutable once written; new version for a later import |
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
