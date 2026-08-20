---
stage_id: "17-skeleton-draft"
title: "Create and approve the article skeleton"
paper_steps: ["6"]
core: false
interaction_profile: "normal"
long_running: false
goal_condition: null
prerequisites: ["16-replication-package"]
required_inputs: ["project/PROJECT_STATE.md", "project/artifacts/preemption_review_vNNN.docx", "project/artifacts/methods_plan_vNNN.md", "project/artifacts/hypotheses_vNNN.md", "project/artifacts/estimands_vNNN.csv", "project/artifacts/preregistration_vNNN.md", "project/artifacts/preregistration_record_vNNN.md", "project/artifacts/human_validation_report_vNNN.md", "project/artifacts/analysis_results_vNNN/", "project/artifacts/analysis_report_vNNN.md", "project/artifacts/robustness_results_vNNN/", "project/artifacts/robustness_report_vNNN.md", "project/artifacts/replication_package_vNNN/", "project/artifacts/replication_rebuild_report_vNNN.md", "project/DEVIATIONS.md"]
declared_outputs: ["project/artifacts/skeleton_draft_vNNN.docx", "project/artifacts/skeleton_draft_vNNN.tex", "project/artifacts/skeleton_draft_vNNN.md", "project/runs/<run_id>/skeleton_draft_source.md", "project/runs/<run_id>/rendered_skeleton_draft/", "project/runs/<run_id>/run_manifest.json", "project/PROJECT_STATE.md", "project/DECISIONS.md", "project/RUN_LEDGER.md", "project/DEVIATIONS.md"]
human_gate: "skeleton-draft-approval"
next_stage: "18-integrate-manuscript"
failure_routes: ["02-preemption-review", "04-methods-design", "09-freeze-and-preregister", "13-human-validation", "14-analysis-and-correction", "15-robustness", "16-replication-package", "17-skeleton-draft"]
---

# Stage 17 — Create and approve the article skeleton

## Objective

Give the researcher an organizationally complete draft after the results and replication package are settled. It should show how the full article fits together and present the complete results primarily through verified tables, figures, and equations. Captions and notes should make those displays intelligible. The methods and results prose should be bare-bones, and the remaining article prose belongs to the researcher. The default is to create the skeleton. The researcher may instead skip this stage, but the skip must be recorded.

## Prerequisite checks

1. Read AGENTS.md, PROJECT_STATE.md, workflow/shared/guardrails.md, workflow/shared/artifact-contract.md, and workflow/shared/execution-control.md completely. Create or reconcile the native Stage 17 plan. This is a bounded `normal` stage, so do not enter Plan Mode or create a goal.
2. Confirm that Stage 16 completed and that the active replication package passed its clean rebuild and fresh-agent checks. Resolve every input from the exact versions pinned in state, not from a latest-file guess.
3. Load the accepted contribution and literature position, approved hypotheses and estimands, preregistration and record, validation report, analysis report and machine-readable results, robustness report and results, deviations, and replication manifest. Confirm that their artifact references and file hashes reconcile.
4. If an input is missing, inconsistent, or no longer supported, make no skeleton. Route to the stage that owns the problem and preserve the completed replication package.
5. Confirm that `scripts/build_skeleton_draft.py` and `workflow/templates/skeleton_draft_template.md` are present. Confirm that the local environment can render Word when Word is selected or compile LaTeX when LaTeX is selected.

## Researcher decisions

Ask one consolidated question. Offer **create the skeleton draft** as the default and **skip** as the explicit alternative. If creating it, ask for the output format, with Word as the default and LaTeX or Markdown as alternatives, together with the target venue or approximate article length if known, any fixed sections or organizational preferences, and anything the researcher wants emphasized. One answer such as “go with the defaults” is enough to select Word with no added constraints.

If the researcher skips, append the decision with gate ID `skeleton-draft-approval`, record `skipped` and the researcher's actual words, set `current_stage` to `18-integrate-manuscript`, and set `status` to `ready`. Do not create a run or skeleton artifact. Otherwise record the format and organizational instructions before opening a run.

## Mode handoff

Remain in the ordinary execution session. Create a run ID under the artifact contract only after the researcher chooses to create the skeleton. Do not begin Stage 18 and do not treat a request to iterate on the skeleton as approval to advance.

## Work

1. Copy `workflow/templates/skeleton_draft_template.md` to the immutable run-scoped `skeleton_draft_source.md`. Replace every placeholder from the verified active artifacts and the researcher's organizational instructions. The source is the canonical representation for all output formats.
2. Propose descriptive sections and subsections in reading order. Make the structure complete enough to show the whole article, including the introduction, background or literature where appropriate, data and methods, results, robustness or validation where appropriate, limitations, discussion where appropriate, and conclusion.
3. For every section and subsection, state its role, bare-bones content, source support, results presented, displays, work left for the author, open questions, and approximate length. Cite supporting material as `project/path#artifact-id`. Use `none` only when the field truly has no item.
4. Present every result from the active analysis and robustness inventories, including null and fragile findings. Use the verified tables and figures whenever available and include the estimating or identifying equations needed to understand the methods. Supply concise captions and notes that define variables, samples, uncertainty, scales, panels, and specifications well enough to understand each display without additional prose.
5. Include every hypothesis, estimand, validation result, and preregistration deviation in the relevant section or flag it for the researcher's attention. Do not omit a statistically inconvenient result or move it into a generic limitations note.
6. Write only enough methods and results text to orient the reader to the design, estimands, full findings, and supporting displays. Keep it factual and compact. Use only verified project artifacts and do not invent an explanation, authority, table, figure, equation, limitation, or contribution.
7. Outside methods, results, validation, and robustness, use `Author to write.` whenever possible. Do not compose an abstract, introduction, literature review, discussion, or conclusion. Researcher-approved thesis or contribution language may be reproduced exactly when useful and cited to its source.
8. Encode each display as `kind|project/path#artifact-id|caption`, using `table`, `figure`, or `equation` as the kind and ` || ` between displays. Tables must be verified CSV or TSV files, figures must be verified PNG or JPEG files, and equations must be verified TeX or text files. The builder places the actual display and its caption in each output format.
9. Run the deterministic builder from the repository root, selecting the next unused artifact versions and matching the selected extension:

   ```text
   python scripts/build_skeleton_draft.py project/runs/<run_id>/skeleton_draft_source.md project/artifacts/skeleton_draft_vNNN.<docx|tex|md> --manifest project/runs/<run_id>/run_manifest.json --project-root .
   ```

10. For Word, use the builder's real headings, fixed-width table geometry, header, and page number. Render the complete DOCX under `rendered_skeleton_draft/` and inspect every page at 100 percent zoom. For LaTeX, compile the generated source with the repository's available LaTeX toolchain, save the PDF and logs under the run directory, render the complete PDF, and inspect every page. For Markdown, validate structure and links and inspect the whole file as text.
11. Give the researcher the versioned skeleton and keep Stage 17 active. Each requested change receives a new run-scoped source, output version, render directory, and run manifest. Never overwrite an earlier iteration.

## Artifacts

The immutable Markdown source contains the canonical article structure, minimal methods and results content, complete result references, display specifications, captions, and provenance references. `skeleton_draft_vNNN.docx`, `.tex`, or `.md` is the researcher-facing rendering selected for that iteration. The render directory contains page images, compiled PDFs where applicable, and inspection evidence. The run manifest records source and output hashes, exact format, verified source versions, display references, commands, tool versions, and review disposition.

Only the selected researcher-facing format is produced for a run. A later format change is a new version from a new immutable source, not an in-place conversion.

## Verification

- Run the builder's structure, required-role, field, provenance, placeholder, format, prose-limit, and overwrite checks.
- Confirm that headings are descriptive, ordered, and properly nested. Confirm that the structure includes the introduction, methods, results, limitations, and conclusion.
- Confirm every `project/path#artifact-id` reference resolves to an active or expressly retained project artifact and that every number or result label comes from that artifact.
- Check the complete inventories of hypotheses, estimands, findings, validation, robustness, and deviations. Confirm that every result is presented, including null and fragile findings, and that every other material item is included in the relevant section or expressly flagged for the researcher.
- Confirm that each result and robustness section includes at least one verified table, figure, or equation. Check that the actual displays render and that every caption and note is sufficient to interpret its variables, sample, uncertainty, scale, panels, and specifications.
- Search the source and output for unresolved placeholders. Confirm that methods and results contain only the factual minimum needed to orient the reader and that the remaining substantive prose is assigned to the author.
- For Word and LaTeX, compile or render successfully, inspect every page at 100 percent zoom, and correct clipping, blank pages, broken tables, bad hierarchy, orphan headings, unreadable text, and footer or numbering defects in a new version. For Markdown, inspect every section and structural link.
- Reopen the output mechanically. Confirm that its hash matches the run manifest and that no prior artifact changed.

## State transition

While building or revising, keep `current_stage` at `17-skeleton-draft` and use `running` only for an open run. After verification, pin the new skeleton, set `status` to `awaiting_approval`, identify its exact paths and hashes, ask for approval or another iteration, and close the run. Revision instructions reopen Stage 17 with new versions.

Only the researcher's explicit approval satisfies `skeleton-draft-approval`. Append the decision and pin it to the approved skeleton source, output, and hashes. Then set `current_stage` to `18-integrate-manuscript` and `status` to `ready`. A recorded skip makes the same transition without a skeleton artifact. An unsupported result or source routes to its owning earlier stage and invalidates dependent skeleton approval.

## Next-stage handoff

Tell the researcher which skeleton version and format were approved and which questions remain open. Explain that Stage 18 will use the approved skeleton only as planning context. It will not treat the skeleton as researcher-written manuscript prose. If no substantive researcher-written draft exists, Stage 18 must set `waiting_for_user` and ask for one. If a supplied draft departs from the skeleton, the draft and the researcher's explicit instructions control.
