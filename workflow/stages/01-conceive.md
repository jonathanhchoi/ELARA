---
stage_id: "01-conceive"
title: "Conceive and select a project"
paper_steps: ["1"]
core: true
interaction_profile: "plan_then_execute"
long_running: true
goal_condition: "Run Stage 01 exactly as specified until every declared conception artifact and its sources have passed the stage verification and PROJECT_STATE.md records the project-selection gate, or until an ELARA section 11 stop condition is recorded and surfaced; do not select a project or cross the gate for the researcher."
prerequisites: ["00-initialize"]
required_inputs: ["project/PROJECT_STATE.md", "project/PROJECT_CHARTER_vNNN.md", "project/INPUT_INVENTORY_vNNN.csv", "project/inputs/"]
declared_outputs: ["project/artifacts/researcher_profile_vNNN.md", "project/artifacts/landmark_survey_vNNN.md", "project/artifacts/conception_report_vNNN.md", "project/sources/conception/<run_id>/source_manifest.csv", "project/sources/conception/<run_id>/search_log.csv", "project/sources/conception/<run_id>/retrieved/", "project/runs/<run_id>/run_manifest.json", "project/PROJECT_STATE.md", "project/DECISIONS.md", "project/RUN_LEDGER.md", "project/DEVIATIONS.md"]
human_gate: "project-selection"
next_stage: "02-preemption-review"
failure_routes: ["00-initialize", "01-conceive"]
---

## Objective

Infer and confirm the researcher's interests and reusable methods, survey important empirical work, generate genuinely new LLM-enabled project ideas, conduct a proportionate live review of whether every surviving idea appears new, and return a ranked shortlist. The agent generates and stress-tests candidates; the researcher selects the project.

## Prerequisite checks

1. Read AGENTS.md, validate that Stage 00 is approved, and load the exact active charter, inventory, and restrictions from PROJECT_STATE.md.
2. Confirm that the supplied prior work is sufficient to infer an agenda. Prefer two or three papers read in full, supplemented by a CV or notes. If there is too little evidence, request more and leave state unchanged. If the researcher confirms that no substantial prior work exists, run a structured interest interview instead — fields, courses taught or taken, doctrinal areas, methods comfort, corpora of interest, normative commitments — and record the confirmed answers in researcher_profile_vNNN.md labeled as researcher-supplied rather than inferred; the claimed-agenda exclusion list then defaults to empty.
3. Confirm that web retrieval is available for the landmark survey and novelty screens. If it is not, do not substitute memory; identify the searches the researcher must run or arrange a later retrieved-source run.
4. Check that no input has changed by comparing hashes to the active inventory. A changed input is a new immutable input version, not a replacement.

## Researcher decisions

The researcher alone:

- corrects or approves the inferred interest profile;
- decides whether a claimed future-work item may nevertheless be reconsidered;
- supplies field, jurisdiction, corpus, resource, or normative constraints not apparent from prior work;
- chooses, redirects, combines, or rejects shortlist candidates; and
- decides what contribution is worth pursuing.

Pause after presenting the profile if any material inference is disputed. At the end, do not choose the winner or begin methods design.

## Mode handoff

Follow `workflow/shared/execution-control.md` and create the native stage plan
before work. Use the two targeted Plan-Mode interviews in
`workflow/shared/execution-control.md`, not one continuous planning session.
First enter the host's read-only Plan Mode, inspect the supplied work, infer the
interest profile with exact source locations, and use `request_user_input` on
Codex or `AskUserQuestion` on Claude Code in rounds of one to three questions
to resolve disputed or unsupported inferences, substantive constraints, and
claimed future-work items. Synthesize the confirmed profile and the research
plan for review. Do not write any project file, create a run, update state, or
browse-download files while this interview is active.

After the researcher accepts that proposal, leave Plan Mode and continue into
execution in the same session. The
`goal_condition` recorded in the settings at the top of this file must be the
active goal before execution begins. If it is not active, provide
`/goal <goal_condition>` and stop. Run the landmark, brainstorming, screening,
and verification work under that goal. After the verified shortlist exists,
re-enter Plan Mode and use the same question control to compare, redirect, or
combine candidates. An express selection tied to the exact report is the
`project-selection` decision; accepting a generic host plan, the goal, or a mode
change is not. If a redirection needs new research, leave Plan Mode, create and
verify a new report version under the same goal, and return to the shortlist
interview.

## Work

1. After the first Plan-Mode proposal is accepted and the exact goal is active, allocate a unique run ID and archive the exact inputs and active artifact hashes in the run manifest.
2. Write the confirmed profile from the Plan-Mode synthesis, covering recurring substantive themes, actual methodological approach, familiar collections of documents or data, theoretical commitments, reusable sequences of research steps, and every future-research passage, limitation, footnote, or announced project that ELARA should not duplicate. Cite the input file and page or section for every inference and record the researcher's corrections or express adoption of the recommendation in DECISIONS.md.
3. Using live web research, identify the important and widely cited empirical works in the confirmed fields. Support their recognized importance with retrieved evidence such as reviews, handbooks, syllabi, or citation data. For each landmark, state its question, importance, principal data limitation, and the extension or adjacent test made newly feasible by LLM-scale text measurement.
4. Brainstorm broadly from the confirmed profile and landmark limitations, not by executing the researcher's prior-paper to-do list. Generate at least ten distinct candidates before filtering. Exclude near-duplicates of prior work and claimed-agenda items unless the researcher expressly reopens them.
5. Apply all selection tests to each candidate: the question is important and intelligible in one sentence; either plausible result is interesting; LLM-scale measurement makes the project newly feasible; the task determines values from researcher-supplied text rather than predicting an outcome beyond that text; variables can be checked and preferably supported by exact quotations; the collection of documents or data has a plausible lawful route; and execution is feasible in weeks rather than years. Break overall judgments into observable components. Reject candidates that fail and preserve the reason in the report.
6. For each surviving candidate, run a proportionate live review of whether it appears new, rather than the exhaustive Stage 02 review. Search multiple phrasings across at least three relevant routes, inspect the most similar results, search the nearest author's related work, and check that the proposed collection appears to exist. Log queries verbatim. Retrieve and preserve the closest openly downloadable sources; list inaccessible sources and exact database searches requiring researcher access. Label sources read in full as verified and snippets or second-hand mentions as unverified.
7. Give each survivor a provisional assessment of open, crowded but distinguishable, or apparently already done. This is a preliminary review, not a final preemption verdict. Reject or reshape apparently completed ideas; do not inflate novelty to preserve a favorite.
8. Rank approximately five candidates. For each, report the one-sentence question, the important prior work and limitation it overcomes, why either result direction would matter, fit with the profile, closest literature and provisional review of novelty, unit of observation, variables, ability to support coding with exact quotations, collection and access route, permission risks, pilot results that would show the project cannot work, and decisions reserved for the researcher.
9. Before delivery, have a fresh reviewer (per `workflow/shared/fresh-review.md`) check a sample from every candidate's screen by reopening sources and comparing the report's claims. Correct unsupported factual statements or mark them unverified; never invent a citation.
10. After the report and source records verify, enter the second Plan-Mode interview. Present the evidence-supported recommendation first, realistic alternatives and combinations with their consequences, and a free-form route. Write nothing while the interview is active. If the researcher redirects or combines candidates, complete the necessary new research and verification before asking for selection against a new report version.

## Artifacts

The active outputs are researcher_profile_vNNN.md, landmark_survey_vNNN.md, and conception_report_vNNN.md. Preserve the complete search log, source list, lawfully retrieved copies, and record of the run under the run ID. The source list must include citation, URL, access date, retrieval status, local path, the value used to verify that the file has not changed, full-text-read status, and candidate IDs. Do not overwrite an earlier shortlist when rerunning with a new lens.

## Verification

- Confirm that every profile claim points to an input location and that claimed-agenda items are excluded or expressly reopened.
- Confirm that every surviving candidate passes all selection tests and receives its own live novelty screen; do not reuse one generic search across ideas.
- Confirm that every cited work is in the manifest, verified and unverified labels are honest, and every reported URL was opened during the run.
- Confirm that the shortlist includes result-direction payoffs, an obtainable candidate corpus, observable variables, and explicit researcher-only decisions.
- Confirm that the report calls its novelty findings provisional and reserves the exhaustive selected-project review for Stage 02.
- Confirm that both targeted Plan-Mode interviews used the host's structured question control, wrote nothing while active, and preserved every answer, recommendation, redirection, and explicit deferral in the resulting record.
- Reconcile report counts with the source and search logs and disclose all files changed.

## State transition

At execution start, set current_stage to 01-conceive and status to running; append the run start. If required prior work or retrieval access is missing, append an exact waiting row, set status to waiting_for_user, and preserve the prior active versions.

After verified artifacts exist, make them active, set status to awaiting_approval, mark project-selection pending, and identify the selection or requested redirection in outstanding_user_inputs before entering the second Plan-Mode interview. Do not advance on a rank or on acceptance of a generic host plan. When the researcher explicitly selects a candidate against the exact report, leave Plan Mode, append the candidate ID, exact question, intended corpus, claimed contribution, and any conditions to DECISIONS.md; mark the gate approved and set current_stage to 02-preemption-review and status to ready. If the shortlist is rejected or redirected, version the next run and remain at this stage.

## Next-stage handoff

After selection, state that the idea has received only a proportionate preliminary novelty review. Provide the exact next task: run 02-preemption-review on the selected question, using the selected candidate entry and its source list as starting points; Stage 02 begins with a short preliminary check of corpus access before any exhaustive searching, then stops for the researcher's preemption decision.
