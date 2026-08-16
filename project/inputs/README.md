# Project inputs

Place source materials for this one project in this directory before stage 00
inventories them. Examples include prior papers, a project memo, seed citations,
data dictionaries, pre-existing code, and corpus files you are authorized to
process.

If you are bringing an existing project into ELARA (`$elr adopt` / `/elr adopt`),
put the work already done in `existing/`: the question memo, literature review,
codebook or prompt, coded data, analysis code and results, replication package,
draft, and referee letters. Stage 00 inventories and hashes them here, then copies
the usable ones unchanged into `project/artifacts/imported_vNNN/` and pins them as
the artifacts later stages use. Anything too large to copy can be named by path in
the interview and is inventoried by path and hash. Manuscript drafts for Stage 17
or the manuscript utilities go in `manuscript/`; a marked-up PDF for
`elr-apply-markup` goes in `manuscript/markup/`.

## Before adding a file

- Use a stable, descriptive filename. Avoid names that differ only by letter
  case, generic names such as `final.pdf`, and paths that contain credentials or
  personal identifiers.
- Make sure cloud-backed files are fully downloaded rather than placeholders and
  that archives can be opened.
- Retain the original format. Do not OCR, normalize, or convert a file in place;
  those transformations become versioned derivatives later.
- Record provenance: who supplied it, where it came from, relevant URL or stable
  identifier, acquisition date, and whether it is complete.
- Record the proposed authorization basis and processing route. Possession does
  not necessarily authorize transmission to a hosted model.

Do not add licensed, confidential, sealed, privileged, export-controlled, or
personally identifying material until you have assessed the applicable license,
consent, confidentiality, security, and IRB or ethics obligations. When in doubt,
leave the material outside the repository and describe it to stage 00; stage 06
will require an explicit researcher authorization before processing.

## After stage 00 inventory

Inputs are immutable once inventoried and hashed:

- do not edit, overwrite, rename, move, or delete them;
- add a correction or replacement under a new filename;
- record which prior input it supersedes; and
- store OCR, redaction, extraction, and normalization results outside `inputs/`
  as declared `_vNNN` artifacts linked to the original hash.

This `README.md` is a kit instruction and is not a research input. All other
files placed here should appear in the input inventory or be reported as an
explicit exception.

## Git and privacy warning

The repository's `.gitignore` excludes new files under `project/inputs/` by
default, but `.gitignore` is not a security control and does not remove files
already committed. If this copy is a Git repository, check `git status` and its
history before relying on local storage for restricted data; if it is a plain
ZIP copy, those Git checks do not apply. Either way, check sync settings, file
permissions, and backups — cloud-synced folders (Google Drive, OneDrive,
Dropbox) can retain and propagate restricted text on their own.
