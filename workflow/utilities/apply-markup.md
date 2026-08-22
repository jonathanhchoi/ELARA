---
utility_id: "apply-markup"
title: "Transcribe hand markup on a PDF into an edit list, then apply the approved edits"
skill: "elr-apply-markup"
interaction_profile: "plan_then_execute"
requires: ["project/PROJECT_STATE.md", "an active manuscript version under project/artifacts/ or a researcher-supplied draft under project/inputs/manuscript/", "a researcher-supplied marked-up PDF under project/inputs/manuscript/markup/", "project/PUBLICATION_PROFILE_vNNN.md (optional; the active publication profile, including the proofreaders' marks legend)"]
declared_outputs: ["project/artifacts/markup_transcription_vNNN.md", "project/artifacts/markup_transcription_vNNN.csv", "project/artifacts/manuscript_vNNN/", "project/artifacts/manuscript_change_log_vNNN.md", "project/runs/<run_id>/page_images/", "project/runs/<run_id>/build_and_render_logs/", "project/runs/<run_id>/run_manifest.json", "project/PROJECT_STATE.md", "project/DECISIONS.md", "project/RUN_LEDGER.md", "project/DEVIATIONS.md"]
human_gate: "manuscript-edit-permission"
---

## Objective

Turn a researcher's hand-marked PDF into an explicit, reviewable list of proposed edits, stop for the researcher's corrections and approval, and then apply exactly the approved edits to a versioned copy of the manuscript. Transcription and application are separate phases with a hard stop between them. This is not a pipeline stage and does not change `current_stage`; where a revision is under way, Stage 20 consumes the approved transcription as researcher notes.

## Prerequisite checks

Read `AGENTS.md`, `project/PROJECT_STATE.md`, `workflow/shared/guardrails.md`, `workflow/shared/artifact-contract.md`, and `workflow/shared/manuscript-editing-contract.md` before doing any work.

1. Resolve the manuscript version the markup was made on and record its path and a hash (a value used to verify that its contents have not changed). If the markup was made on a redline or an older version, say so and map page numbers accordingly.
2. Resolve the marked-up PDF under `project/inputs/manuscript/markup/` and record the same kind of verification value for it. Never modify it.
3. Resolve the proofreaders' marks legend from the active publication profile or from the researcher's instruction for this run. If no legend exists, ask; do not guess what a symbol means. Record the legend used in the transcription.
4. Confirm the tools needed to split the PDF into page images and to read them are available; record their versions in the record of the run.

## Researcher decisions

The researcher decides what each mark means where the legend is silent or the mark is ambiguous, corrects the transcription, approves the edit list, and grants manuscript-edit permission for the application phase. The agent may transcribe, propose, and flag; it may not apply an edit that was not approved, resolve an ambiguity by choosing the more convenient reading, or make changes beyond the approved list.

## Mode handoff

Follow `workflow/shared/execution-control.md` and create the native utility plan
before work, with separate transcription, mapping review, approval, application,
and verification items. Phase 1 (transcription) needs no edit permission but
must not touch the manuscript. Phase 2 (application) begins only after the
researcher has reviewed the transcription and granted
`manuscript-edit-permission` for the approved items. Between the phases, update
the native plan, stop, and hand the transcription to the researcher. This is
bounded work; do not start a goal.

## Work

Phase 1, transcription:

1. Allocate a unique run ID and output versions, record the values used to verify the manuscript and PDF and the exact publication-profile version, and append a ledger start.
2. Split the PDF into one image per page under `project/runs/<run_id>/page_images/`. Read every page. Transcribe every mark into `markup_transcription_vNNN.csv` and a readable `markup_transcription_vNNN.md`: page, anchor text in the manuscript, mark type under the legend, the exact proposed edit (deletion, insertion, replacement, move, or comment), and a flag when the reading is uncertain. Do not interpret arrows or symbols the legend does not define; flag them.
3. For marks that are comments or instructions rather than literal edits, propose the edit that would carry them out under the active publication profile, and label it as proposed prose rather than a literal transcription.
4. Conduct two review passes over the transcription against the page images: first for completeness (every mark captured), second for correctness (each edit matches its mark). Present the transcription and every flagged item to the researcher and stop.

Phase 2, application (after approval):

5. Copy the manuscript into a new `manuscript_vNNN/`. Apply exactly the approved edits, in manuscript order, under the manuscript-editing contract and the publication profile. Where an approved edit is proposed prose, write it in the draft's voice and change nothing beyond what the mark requires.
6. Compile or render, inspect every affected page (every page when the profile requires it), and produce the change log, a diff, and a redline when the profile asks. Cross-check the change log against the approved transcription: every approved item applied or listed as not applied with a reason; nothing applied that was not approved.
7. If any approved edit added, removed, or recharacterized a citation, route the new version through an audit-only Stage 19 pass before it is treated as the active manuscript.

## Verification

- Every mark on every page appears once in the transcription with a legend-defined type or an explicit ambiguity flag; the two transcription review passes are recorded.
- The diff against the source contains only approved edits; every approved edit is applied or expressly declined with a reason.
- No number, quotation, canonical language, defined label, or citation changed except as an approved edit directs.
- The record of the run states the legend used, the tool versions, and the exact publication-profile version.
- `current_stage` is unchanged; the run and the permission are recorded in the ledgers.

## State transition

Do not change `current_stage`. Append the run to `RUN_LEDGER.md` and the transcription approval and permission to `DECISIONS.md`. Record the new manuscript version as the version currently in use only after the researcher accepts the applied result and any required Stage 19 audit is clean or expressly accepted.
