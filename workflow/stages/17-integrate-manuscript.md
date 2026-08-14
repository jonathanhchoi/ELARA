---
stage_id: "17-integrate-manuscript"
title: "Integrate validated results into the researcher's manuscript"
paper_steps: ["6"]
core: false
interaction_profile: "plan_then_execute"
long_running: false
prerequisites: ["16-replication-package"]
required_inputs: ["project/PROJECT_STATE.md", "project/artifacts/replication_package_vNNN/", "project/artifacts/replication_rebuild_report_vNNN.md", "project/artifacts/analysis_results_vNNN/", "project/artifacts/analysis_report_vNNN.md", "project/artifacts/robustness_results_vNNN/", "project/artifacts/robustness_report_vNNN.md", "project/artifacts/human_validation_report_vNNN.md", "researcher-supplied substantive manuscript under project/inputs/manuscript/"]
declared_outputs: ["project/artifacts/manuscript_edit_plan_vNNN.md", "project/artifacts/manuscript_vNNN/", "project/artifacts/manuscript_change_log_vNNN.md", "project/artifacts/manuscript_consistency_report_vNNN.md", "project/runs/<run_id>/build_and_render_logs/", "project/runs/<run_id>/run_manifest.json", "project/PROJECT_STATE.md", "project/DECISIONS.md", "project/RUN_LEDGER.md", "project/DEVIATIONS.md"]
human_gate: "manuscript-edit-permission"
next_stage: "18-cite-check"
failure_routes: ["14-analysis-and-correction", "15-robustness", "16-replication-package", "17-integrate-manuscript"]
---

## Objective

Optionally integrate validated results into a substantive first draft supplied by the researcher while preserving the researcher's thesis, framing, organization, voice, and existing prose. ELARA does not draft the first manuscript, create a paper from an outline, or supply an original argument. Every empirical claim must trace to the active replication package, and no manuscript file may be edited until the researcher approves a concrete edit plan and grants manuscript-edit permission.

## Prerequisite checks

Read `AGENTS.md` and route this stage from `project/PROJECT_STATE.md` before doing any work; the standing rules and exact active versions control every check below.

1. Confirm the Stage 16 core is complete and resolve the exact active package, validation, analysis, and robustness versions. The clean replication rebuild must cover every result proposed for integration.
2. Inspect the actual researcher-supplied manuscript, bibliography, figures, build system, and local instructions read-only. Identify its thesis, organization, voice, audience, entry file, generated components, unresolved notes, existing results discussion, and working-tree or checkpoint constraints.
3. Confirm that the supplied manuscript is a substantive first draft rather than an outline, notes, or a request to generate the paper. If no substantive draft exists, stop and ask the researcher to write and supply it; do not create prose or a plan artifact.
4. Restate the exact integration or revision scope. Confirm that inputs under `project/inputs/` will remain immutable and that a versioned working copy can be built under declared outputs. If the source or scope is ambiguous, stop for clarification. If a relevant result is not validated and reproduced, route upstream before planning prose.

## Researcher decisions

The researcher controls the thesis, framing, normative claims, audience, venue, organization, voice, disclosure language, exact scope of permitted edits, and which validated findings deserve emphasis. The researcher must approve the edit plan and explicitly grant manuscript-edit permission. The agent may propose narrow integrations, consistency repairs, and source-traceable language within that scope. It may not create the first draft, broaden the article, manufacture a contribution, hide null or fragile results, alter substantive commitments, or treat permission to inspect as permission to edit.

## Mode handoff

Begin in Plan Mode. Do not write any project file during Plan Mode. Present a section-by-section integration plan that identifies each proposed change, its exact result source, figures or tables, validation and robustness caveats, disclosure needs, files to copy, dependent passages, and build checks. State expressly that no new thesis, section architecture, or analysis discussion outside the supplied draft and approved scope will be created. Stop for explicit researcher approval at `manuscript-edit-permission`. After the researcher approves the plan and exits Plan Mode, use normal approved execution with this objective: **Create a versioned copy of the researcher-supplied manuscript and make only the approved, source-traceable integrations, preserve the researcher's voice, compile or render it, perform two review passes, and disclose every change.**

## Work

1. After explicit permission, allocate a unique run ID and output versions, persist the approved plan, record exact input hashes, copy the supplied manuscript and required build files into `manuscript_vNNN/`, set the stage running, and append a ledger start. Never edit the file under `project/inputs/` or an earlier manuscript version.
2. Find the least disruptive existing location for each approved result. Modify only the authorized discussion and its necessary abstract, introduction, conclusion, table, figure, disclosure, or cross-reference consequences. Do not invent a new outline, thesis, literature discussion, or normative argument.
3. Pull every number, sample count, estimate, interval, table, and figure from the active machine-readable results and script-output manifest. Use generated tables and figures where possible. Never retype from memory, reverse-engineer a value from a plot, or substitute a preliminary result.
4. Describe human validation, interpretive verification, measurement-error correction, prompt and second-model robustness, coverage, deviations, and remaining limitations accurately. Do not call a provisional, unvalidated, fragile, or restricted result final, representative, or causal unless the approved design supports that characterization.
5. Match the existing sentence structure, vocabulary, formality, citation practices, and rhetorical style. Preserve existing language wherever it already makes the point; change only what is necessary for the approved task. Keep main findings accessible to legal readers and technical implementation details where the manuscript already places them.
6. Keep the abstract, introduction, methods, results, limitations, conclusion, appendices, tables, and figures mutually consistent. Update dependent numbers and descriptions together. Do not change legal terminology, quotations, canonical language, defined labels, or hypotheses merely for stylistic variation.
7. Reuse only citations already supported by retrieved sources. Mark a needed but unverified authority as an explicit citation-needed finding for Stage 18; never fabricate a case, article, quotation, pinpoint, or bibliography entry.
8. Add only the approved LLM-use, data-access, preregistration, validation, and replication disclosures, including restrictions and archive access instructions. Do not claim public availability before the researcher has actually published an archive.
9. Compile or render the manuscript using its real build system. Inspect logs and the rendered artifact for broken references, missing figures, overflow, encoding, bibliography, table, and pagination problems. Fix only issues within approved scope.
10. Build a preregistration concordance inside the consistency report: a machine-checkable crosswalk from every preregistered hypothesis and estimand ID to the table, figure, or section that reports it, or a stated omission reason approved by the researcher.
11. Conduct two separate self-reviews: first trace claims and numbers to artifacts; then compare the versioned manuscript against the immutable source and approved plan. Create a complete change log naming every altered file and substantive edit, including any requested change not made and why.

## Artifacts

The edit plan fixes authorized scope before prose changes. `manuscript_vNNN/` contains the versioned editable manuscript and necessary build inputs in their original format. The change log accounts for every addition, deletion, move, generated-result update, disclosure, and untouched request. The consistency report maps empirical claims and displayed results to active artifacts, contains the preregistration concordance, and records the two review passes, build or render result, unresolved citation needs, and upstream blockers. Run logs preserve the exact build commands and diagnostics.

## Verification

- Diff the versioned manuscript against the immutable source and confirm every change is within the approved plan and appears in the change log.
- Trace every empirical number, table, figure, validation statement, and robustness statement to an exact active package file and confirm no preliminary or superseded result remains.
- Check consistency across abstract, introduction, body, conclusion, appendices, captions, and disclosures, including denominator and uncertainty language.
- Confirm every preregistered hypothesis and estimand appears in the concordance as reported or expressly omitted with a researcher-approved reason.
- Confirm the existing thesis, organization, voice, and legal terminology are preserved, no first-draft prose or unsupported substantive claim was introduced, and requested minimal-change constraints were followed.
- Compile or render from the versioned directory, inspect the output, and confirm references, citations, figures, tables, and build dependencies resolve as documented.
- Confirm no citation was invented, all unresolved authorities are flagged for Stage 18, the source manuscript remains unchanged, and no prior artifact was overwritten.

## State transition

Plan Mode leaves the completed core and all files unchanged. Without a substantive researcher-supplied draft and explicit permission, do not enter this stage or create a plan artifact. After permission and execution start, set `current_stage` to `17-integrate-manuscript` and `status` to `running`. An unsupported result routes to Stage 14 or Stage 15; a package mismatch routes to Stage 16. Preserve the source and any failed version.

After all approved edits and verification pass, activate the manuscript, plan, change log, consistency report, and run; append the permission and scope decision; set `current_stage` to `18-cite-check`; and set `status` to `ready`. Manuscript integration is not citation validation.

## Next-stage handoff

Tell the researcher the exact source and output versions, every section and file changed, results and disclosures integrated, build outcome, unresolved upstream issues, and citation needs. Confirm that ELARA worked from the researcher's substantive draft and did not create the first draft. Then provide the exact next task: run audit-only `18-cite-check` against the versioned manuscript, retrieve the actual source behind every claim-citation pair, and report errors without editing the draft.
