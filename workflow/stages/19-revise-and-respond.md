---
stage_id: "19-revise-and-respond"
title: "Revise the manuscript and prepare the response"
paper_steps: ["6"]
core: false
interaction_profile: "plan_then_execute"
long_running: false
prerequisites: ["18-cite-check"]
required_inputs: ["project/PROJECT_STATE.md", "project/artifacts/manuscript_vNNN/", "project/artifacts/manuscript_change_log_vNNN.md", "project/artifacts/citation_audit_vNNN.jsonl", "project/artifacts/citation_audit_report_vNNN.md", "project/artifacts/replication_package_vNNN/", "project/artifacts/analysis_results_vNNN/", "researcher-supplied reviewer letter, editor letter, or revision notes under project/inputs/peer_review/", "project/PUBLICATION_PROFILE_vNNN.md (optional; the active publication profile)"]
declared_outputs: ["project/artifacts/revision_plan_vNNN.md", "project/artifacts/revised_manuscript_vNNN/", "project/code/revision_analysis_vNNN/", "project/artifacts/revision_analysis_results_vNNN/", "project/artifacts/citation_finding_disposition_vNNN.csv", "project/artifacts/peer_review_response_vNNN.md", "project/artifacts/revision_internal_report_vNNN.md", "project/runs/<run_id>/build_test_and_render_logs/", "project/runs/<run_id>/run_manifest.json", "project/PROJECT_STATE.md", "project/DECISIONS.md", "project/RUN_LEDGER.md", "project/DEVIATIONS.md"]
human_gate: "manuscript-edit-permission"
next_stage: null
failure_routes: ["09-freeze-and-preregister", "13-human-validation", "14-analysis-and-correction", "15-robustness", "16-replication-package", "17-integrate-manuscript", "18-cite-check", "19-revise-and-respond"]
---

## Objective

Turn citation-audit findings, an editor or referee letter, and researcher notes into a researcher-approved revision plan; execute approved changes serially on versioned copies; rerun affected analysis through the validated pipeline; and produce both a cooperative response letter and a candid internal accounting. No manuscript or code edit may occur before explicit permission, and no reviewer request may silently reopen the empirical design.

## Prerequisite checks

Read `AGENTS.md` and route this stage from `project/PROJECT_STATE.md` before doing any work; the standing rules and exact active versions control every check below. Read and follow `workflow/shared/manuscript-editing-contract.md` throughout this stage, and resolve the active publication profile (`active_artifacts.publication_profile`, a `project/PUBLICATION_PROFILE_vNNN.md`); if none is active, ask the researcher to supply one from `workflow/templates/publication_profile_template.md` or to record a decision to proceed by matching the existing draft's voice only.

1. Resolve the exact active manuscript, citation audit, replication package, results, and reviewer materials. Hash researcher-supplied letters and notes and preserve them under `project/inputs/` unchanged.
2. Parse each discrete reviewer, editor, researcher, and citation-audit issue into a stable comment ID. Researcher notes may arrive as a letter, a comments file, margin instructions written into the draft in `[[double square brackets]]`, or a marked-up PDF (transcribe it with `elr-apply-markup` first); use the conventions named in the publication profile. Keep compound comments together only when they require one inseparable decision.
3. Inspect the actual manuscript and relevant analysis code read-only. For each comment, determine whether it calls for explanation, prose, citation, rerunning an existing registered command, a new exploratory analysis, a measurement or data change, or no change.
4. Identify comments that would change hypotheses, methods, codebook, schema, unit space, data authorization, validation, correction, or robustness. Those require the appropriate upstream stage and, where material, a preregistration amendment and new replication package; Stage 19 cannot waive the loop.
5. Confirm the active citation audit applies to the manuscript that will be the base revision. If not, rerun Stage 18 before planning. If prerequisites fail, make no writes and leave state unchanged.

## Researcher decisions

The researcher decides whether each suggestion has merit; whether to accept, partially accept, or respectfully decline it; what new analysis or authority to pursue; whether a change is confirmatory, exploratory, or an amendment; the response strategy; and the exact files and scope the agent may edit. The researcher must approve the comment-by-comment plan and explicitly grant manuscript-edit permission. The agent may recommend dispositions and execute approved work. It may not concede a point for convenience, reject a suggestion to protect a result, change methods without routing, or treat permission for one comment as global permission.

## Mode handoff

Begin in Plan Mode. Do not write any project file during Plan Mode. Present a table with one row per comment or audit finding: exact request, evidence, merit assessment, recommended accept, partial, or decline disposition, upstream route if any, proposed code and manuscript edits, dependent sections and outputs, verification, and draft response. Stop at `manuscript-edit-permission`. After the researcher approves the dispositions and exits Plan Mode, use normal approved execution with this objective: **Execute only the approved comment-level revisions serially on versioned copies, rerun and validate any authorized analysis, update every dependent statement, and produce a complete response letter and internal change report.**

## Work

1. After explicit permission, allocate a unique run ID and output versions, persist the approved plan, record input hashes and approved comment scope — including the active publication profile's path, version, and SHA-256 hash, or the recorded decision to proceed without one — copy the active manuscript into `revised_manuscript_vNNN/`, set the stage running, and append a ledger start. Copy code into `revision_analysis_vNNN/` only for comments authorized to change or rerun it. Never edit prior artifacts or researcher inputs.
2. Process one comment in one focused context. Separate contexts may analyze different comments, but because manuscript, response, ledgers, and analysis files are shared, apply and verify edits serially. Record the start, files touched, tests, disposition, and completion of each comment before the next begins.
3. For an accepted prose or citation issue, make the narrowest change that fully responds. Write under the active publication profile (venue, audience, tone, exemplars, voice-matching choice, prohibited constructions and punctuation, citation style) with the contract's precedence rule; where it is silent, preserve the researcher's voice and unchanged text. Retrieve and read the actual authority before adding or replacing a citation; never fabricate a source, quotation, pinpoint, or characterization.
4. For an existing approved analysis, inspect the actual data and invoke or minimally extend a separately runnable command. Test it, archive machine-readable output, and update every dependent number, table, figure, abstract, introduction, body discussion, conclusion, appendix, and response-letter statement.
5. A request that changes the empirical design, instrument, data route, held-out validation, correction, or robustness exits this stage and routes upstream. Preserve the revision plan and comment ID, complete the invalidated stages with new versions, rebuild Stage 16, and only then resume the corresponding manuscript edit. Do not bury the change in “additional analysis.”
6. Label post-registration analysis honestly and append every deviation or amendment. Report null, contradictory, or fragile results as fully as favorable ones. Do not choose a specification to satisfy a reviewer without the same validation and robustness obligations.
7. Address citation-audit findings one by one in `citation_finding_disposition_vNNN.csv`: corrected with source, proposition narrowed, citation removed, researcher-supplied source pending, or expressly retained with reason. Unsupported and unverified citations cannot be marked resolved without actual evidence.
8. After each approved comment, run relevant code tests and manuscript builds and inspect the changed passage and dependent outputs. A failed analysis or build blocks that comment; do not move on with inconsistent prose.
9. Compile or render the complete manuscript and inspect it visually and structurally, page by page when the profile requires it. Conduct a full consistency pass across claims, numbers, citations, tables, figures, cross-references, disclosures, and appendices, followed by a diff review for out-of-scope edits and a redline (for example `latexdiff`) when the profile asks for one.
10. Draft a respectful, cooperative response letter organized by comment ID that quotes or fairly paraphrases each request, states the disposition, describes the precise change and location, reports new results accurately, and explains any principled decline without defensiveness. Winning the reviewers' approval is a legitimate aim for the letter's tone; it is not a test of whether a comment has merit or of which specification to run.
11. Create a separate candid internal report listing every file and line or section changed, analysis command run, result added or changed, issue declined, upstream reroute, unresolved risk, citation disposition, and difference between the response letter's diplomacy and the complete project record.
12. Because manuscript edits invalidate the prior citation audit, route the revised manuscript through a new audit-only Stage 18 version. If that audit finds a required repair, return with a new approved edit scope. Finalize Stage 19 only after the active revised manuscript has a clean or expressly accepted citation audit and no later manuscript edit has invalidated it.

## Artifacts

The revision plan preserves the researcher-approved disposition and route for every comment and citation finding. `revised_manuscript_vNNN/` is a versioned copy, never the researcher input or prior manuscript. Revision code and results contain only authorized reruns or extensions and retain their tests and command provenance. The citation-disposition table links each audit finding to actual evidence and action. `peer_review_response_vNNN.md` is the journal-facing cooperative response; `revision_internal_report_vNNN.md` is the complete, frank project record. Run logs preserve comment order, builds, tests, renders, and upstream handoffs.

## Verification

- Confirm every reviewer comment, editor request, researcher note, and citation finding has one approved disposition, a corresponding action or reason, and a response-letter entry.
- Diff the revised manuscript and code against their immutable bases; confirm every changed file and substantive edit falls within permission and appears in the internal report.
- Re-run tests and each changed analysis alone and in the full build; trace every revised number, table, and figure to machine-readable output and the active replicated data.
- Confirm design-changing requests followed the correct upstream approval, validation, robustness, preregistration, and replication routes before manuscript integration.
- Retrieve and reopen every authority added or materially recharacterized; confirm citation findings are not marked resolved by unsupported prose edits.
- Compile or render and inspect the complete manuscript, verify the response letter against actual changes, and confirm a post-edit Stage 18 audit covers the exact final manuscript version.
- Confirm parallel work never edited shared artifacts, no unrelated change occurred, and no input, prior manuscript, code version, result, or ledger row was overwritten.
- Confirm the run manifest records the publication profile version and hash (or the recorded decision to proceed without one), and that the profile's prohibited constructions, punctuation preferences, QA steps, and deliverables were honored.

## State transition

Plan Mode leaves all files and state unchanged. Without explicit permission, keep the prior stage active and do not create outputs. After permission and execution start, set `current_stage` to `19-revise-and-respond` and `status` to `running`. An upstream design or data change records the comment ID and routes to the owning stage with this revision pending. A missing source sets `waiting_for_user`. Preserve every partial version and never call it final.

After manuscript edits, set `current_stage` to `18-cite-check` and `status` to `ready` for the required audit. When a later Stage 18 audit covers the exact revised version and no further manuscript edit is required, resume Stage 19, activate the final manuscript, analysis, citation disposition, response letter, internal report, and run; append all approvals; keep `current_stage` at `19-revise-and-respond`; and set `status` to `complete`.

## Next-stage handoff

Tell the researcher every comment and audit disposition, upstream stage rerun, file changed, analysis command and result, citation resolution, declined suggestion, build and test result, post-edit audit version, unresolved risk, and exact final artifact versions. State whether the optional publication workflow is complete. If any manuscript edit occurs later, explain that Stage 18 must audit that new version before another Stage 19 completion.
