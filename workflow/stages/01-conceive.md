---
stage_id: "01-conceive"
title: "Conceive and select a project"
paper_steps: ["1"]
core: true
interaction_profile: "plan_then_execute"
long_running: true
prerequisites: ["00-initialize"]
required_inputs: ["project/PROJECT_STATE.md", "project/PROJECT_CHARTER_vNNN.md", "project/INPUT_INVENTORY_vNNN.csv", "project/inputs/"]
declared_outputs: ["project/artifacts/researcher_profile_vNNN.md", "project/artifacts/landmark_survey_vNNN.md", "project/artifacts/conception_report_vNNN.md", "project/sources/conception/<run_id>/source_manifest.csv", "project/sources/conception/<run_id>/search_log.csv", "project/sources/conception/<run_id>/retrieved/", "project/runs/<run_id>/run_manifest.json", "project/PROJECT_STATE.md", "project/DECISIONS.md", "project/RUN_LEDGER.md", "project/DEVIATIONS.md"]
human_gate: "project-selection"
next_stage: "02-preemption-review"
failure_routes: ["00-initialize", "01-conceive"]
---

## Objective

Infer and confirm the researcher's interests and reusable methods, survey landmark empirical work, generate genuinely new LLM-enabled project ideas, conduct a proportionate live novelty screen for every surviving idea, and return a ranked shortlist. The agent generates and stress-tests candidates; the researcher selects the project.

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

Plan first, read-only. Read the active inputs, identify missing information, outline the profiling, landmark, brainstorming, screening, and verification passes, and make the plan decision-complete; do not write any project file, create a run, update state, or browse-download files until the plan is complete. Then continue into execution in the same session, without waiting, unless a stop condition in `workflow/shared/guardrails.md` §11 holds (a researcher-owned choice with no reasonable provisional default, a spend beyond the recorded budget, or a `checkpoints` preference of `plans` or `all`); only then enter Plan Mode, stop, and give the exact execution handoff. Because this stage is long-running, Codex and current Claude Code may use /goal when available, with normal researcher-approved execution as the fallback. The Goal objective is: Execute Stage 01 exactly as specified, produce the declared versioned artifacts, and stop at the project-selection gate. Neither the plan nor a mode change is approval of the final project; the researcher decides at project-selection.

## Work

1. Allocate a unique run ID and archive the exact inputs and active artifact hashes in the run manifest.
2. Read every supplied prior paper in full. Draft a concise profile covering recurring substantive themes, actual methodological signature, familiar corpora, theoretical commitments, and reusable pipeline architecture. Separately list every future-research passage, limitation, footnote, or announced project as a claimed-agenda exclusion. Cite the input file and page or section for every inference.
3. Present the profile for correction. Record the researcher's response in DECISIONS.md. If material corrections arrive, version the profile before continuing.
4. Using live web research, identify the important and widely cited empirical works in the confirmed fields. Ground canonical status in retrieved evidence such as reviews, handbooks, syllabi, or citation data. For each landmark, state its question, importance, binding data limitation, and the extension or adjacent test made newly feasible by LLM-scale text measurement.
5. Brainstorm broadly from the confirmed profile and landmark limitations, not by executing the researcher's prior-paper to-do list. Generate at least ten distinct candidates before filtering. Exclude near-duplicates of prior work and claimed-agenda items unless the researcher expressly reopens them.
6. Apply all selection tests to each candidate: the question is important and intelligible in one sentence; either plausible result is interesting; LLM-scale measurement makes the project newly feasible; the task is estimation from researcher-supplied text rather than outcome prediction; variables are auditable and preferably quote-anchored; the corpus has a plausible lawful route; and execution is feasible in weeks rather than years. Decompose holistic judgments into observable components. Reject candidates that fail and preserve the reason in the report.
7. For each surviving candidate, run a proportionate, live novelty screen rather than the exhaustive Stage 02 review. Search multiple phrasings across at least three relevant routes, inspect the most similar results, search the nearest author's related work, and check that the proposed corpus appears to exist. Log queries verbatim. Retrieve and archive the closest openly downloadable sources; list inaccessible sources and exact manual database searches. Label sources read in full as verified and snippets or second-hand mentions as unverified.
8. Give each survivor a provisional screen of open, crowded-but-distinguishable, or apparently already done. This is triage, not a final preemption verdict. Kill or reshape apparently completed ideas; do not inflate novelty to preserve a favorite.
9. Rank approximately five candidates. For each, report the one-sentence question, landmark lineage and lifted limitation, either-way payoff, fit with the profile, closest literature and provisional novelty screen, unit of observation, variables, quote-anchoring prospects, corpus and access route, permission risks, pilot-killing risks, and decisions reserved for the researcher.
10. Before delivery, have a fresh reviewer (per `workflow/shared/fresh-review.md`) check a sample from every candidate's screen by reopening sources and comparing the report's claims. Correct unsupported factual statements or mark them unverified; never invent a citation.

## Artifacts

The active outputs are researcher_profile_vNNN.md, landmark_survey_vNNN.md, and conception_report_vNNN.md. Preserve the complete search log, source manifest, lawfully retrieved copies, and run manifest under the run ID. The source manifest must include citation, URL, access date, retrieval status, local path, hash, full-text-read status, and candidate IDs. Do not overwrite an earlier shortlist when rerunning with a new lens.

## Verification

- Confirm that every profile claim points to an input location and that claimed-agenda items are excluded or expressly reopened.
- Confirm that every surviving candidate passes all selection tests and receives its own live novelty screen; do not reuse one generic search across ideas.
- Confirm that every cited work is in the manifest, verified and unverified labels are honest, and every reported URL was opened during the run.
- Confirm that the shortlist includes result-direction payoffs, an obtainable candidate corpus, observable variables, and explicit researcher-only decisions.
- Confirm that the report calls its novelty findings provisional and reserves the exhaustive selected-project review for Stage 02.
- Reconcile report counts with the source and search logs and disclose all files changed.

## State transition

At execution start, set current_stage to 01-conceive and status to running; append the run start. If required prior work or retrieval access is missing, append an exact waiting row, set status to waiting_for_user, and preserve the prior active versions.

After verified artifacts exist, make them active, set status to awaiting_approval, mark project-selection pending, and identify the selection or requested redirection in outstanding_user_inputs. Do not advance on a rank alone. When the researcher explicitly selects a candidate, append the candidate ID, exact question, intended corpus, claimed contribution, and any conditions to DECISIONS.md; mark the gate approved and set current_stage to 02-preemption-review and status to ready. If the shortlist is rejected, version the next run and remain at this stage.

## Next-stage handoff

After selection, state that the idea has only a proportionate novelty screen. Provide the exact next task: run 02-preemption-review on the selected question, using the selected candidate entry and its source manifest as seeds; Stage 02 begins with a bounded smoke screen of corpus access before any exhaustive searching, then stops for the researcher's preemption disposition.
