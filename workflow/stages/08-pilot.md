---
stage_id: "08-pilot"
title: "Pilot the complete coding pipeline"
paper_steps: ["2"]
core: true
interaction_profile: "plan_then_execute"
long_running: true
prerequisites: ["07-adversarial-review"]
required_inputs: ["project/PROJECT_STATE.md", "project/artifacts/design_freeze_vNNN.md", "project/artifacts/methods_plan_vNNN.md", "project/artifacts/codebook_vNNN.md", "project/artifacts/coding_schema_vNNN.json", "project/artifacts/unit_space_vNNN.csv", "project/artifacts/coding_prompt_vNNN.md", "project/artifacts/data_authorization_record_vNNN.md"]
declared_outputs: ["project/artifacts/pilot_plan_vNNN.md", "project/artifacts/pilot_sample_vNNN.csv", "project/artifacts/pilot_report_vNNN.md", "project/artifacts/pilot_researcher_review_vNNN.csv", "project/artifacts/pilot_disagreements_vNNN.csv", "project/artifacts/pilot_revision_queue_vNNN.csv", "project/artifacts/pilot_acceptance_vNNN.md", "project/runs/<run_id>/code/", "project/runs/<run_id>/raw_model_outputs/", "project/runs/<run_id>/normalized_outputs/", "project/runs/<run_id>/pilot_ledger.csv", "project/runs/<run_id>/schema_quote_compliance.csv", "project/runs/<run_id>/code_review.md", "project/runs/<run_id>/run_manifest.json", "project/PROJECT_STATE.md", "project/DECISIONS.md", "project/RUN_LEDGER.md", "project/DEVIATIONS.md"]
human_gate: "pilot-acceptance"
next_stage: "09-freeze-and-preregister"
failure_routes: ["04-methods-design", "05-codebook-and-schema", "06-data-authorization", "07-adversarial-review", "08-pilot"]
---

## Objective

Build and run the smallest complete version of the authorized pipeline on a deliberately informative sample, inspect every observation, test mechanical compliance and software, expose codebook ambiguity and operational failures, and obtain explicit researcher acceptance before freezing and preregistering.

## Prerequisite checks

1. Read AGENTS.md and PROJECT_STATE.md, validate the Stage 07 design freeze and data authorization, and load only the exact named versions and hashes.
2. Confirm the proposed pilot units are authorized, readable, present in the closed unit space or explicitly marked as pilot-only, and not part of the held-out human-validation sample.
3. Confirm that pilot outcomes have not already been used to tune the active package. If they have, document the contamination and choose fresh units.
4. Confirm current model route, provider settings, and data-handling controls still match authorization. Provider or account drift returns to Stage 06.
5. Agree on pilot success thresholds before running: schema and evidence compliance, coverage accounting, refusal and failure tolerances, researcher-review requirements, and any task-specific minimum performance.

## Researcher decisions

The researcher must:

- approve five to ten familiar, diverse pilot units spanning eras, formats, easy and hard cases, likely positive and negative classes, and known edge cases;
- decide whether to code the units independently before seeing model outputs, which is preferred where feasible;
- read every coded observation and every unusable or uncertain row;
- adjudicate disagreements and decide whether they reveal coder error, codebook ambiguity, construct disagreement, or source failure;
- approve any upstream revisions and the rerun scope; and
- accept or reject the pilot against the predeclared criteria.

The agent may diagnose and propose; it cannot self-certify accuracy or waive failed thresholds.

## Mode handoff

Begin in Plan Mode. Talk through architecture before code: inputs, one-unit execution, prompt assembly, raw-output capture, validation, quote matching, retries, ledgering, human review, code review, and stopping rules. Finalize the sample and thresholds. Plan Mode is read-only: do not write any project file, allocate a run, build code, call a coding model, update state, or append ledgers.

Stop after the decision-complete plan. For execution, Codex may use `/goal`; Claude Code should use `/elr-code-observations` and the saved dynamic workflow after the pilot assignments are fixed. Normal researcher-approved execution with durable checkpoints is the fallback. Use the objective: Save and execute the approved Stage 08 pilot plan on the fixed sample, archive all raw outputs, verify every unit, prepare researcher review, and stop at pilot-acceptance. Switching modes does not accept the pilot.

## Work

1. Allocate a run ID after execution begins. Save pilot_plan_vNNN.md with exact frozen artifact hashes, authorized model route, sample, success criteria, architecture, commands, retry limits, and stop conditions.
2. Create pilot_sample_vNNN.csv with unit IDs, selection reason, source hashes, expected component, authorization status, independent-human-code status, and explicit exclusion from later held-out validation. Preserve selection before outputs.
3. If the researcher will pre-code, provide a codebook-based template and keep their codes hidden from the model and pipeline author until raw model outputs are frozen. Never fabricate human labels or silently treat the researcher's later review as independent pre-coding.
4. Build the minimum deterministic driver under the run's code directory. Follow `workflow/shared/observation-fanout.md` for the one-unit subagent route and use the same assignment envelope and validators intended for Stage 11. The driver must assemble the exact frozen prompt, codebook, schema, and one source unit per request; record platform and model identifiers, parameters, timestamps, attempt numbers, input and prompt hashes, token or usage data when available, and errors; save each raw response immediately; and never put credentials in files.
5. Freeze the code used for the run, execute one unit per call, and maintain pilot_ledger.csv with exact pending, running, succeeded, schema-failed, quote-failed, refused, unreadable, wrong-document, exhausted-retry, and awaiting-review counts. Never drop or replace a difficult unit.
6. Validate each output mechanically before aggregation. Parse against the exact schema; enforce IDs, enums, conditional fields, and duplicates; verify quotations verbatim against source text or the documented normalization rule; validate source locations for approved no-quote and multiple-passage records; reconcile zero-observation and failure rows; and preserve invalid raw output. Retries use the fixed approved repair rule, not a reinterpreted codebook.
7. Produce normalized outputs only from validated raw outputs. Every correction, if permitted, is a new superseding row with provenance; never edit the raw response.
8. Have the researcher review every observation in context and every uncertain, edge-case, and failure row. Populate pilot_researcher_review_vNNN.csv with blinded human code where available, later validity decision, reason, and adjudicator. Do not pressure the researcher to agree with the model.
9. Populate pilot_disagreements_vNNN.csv with human-model mismatches and distinguish label disagreement, missed observation, unsupported quote, attribution error, unit error, ambiguity, and unusable source. Ask the model for a codebook-grounded justification only after the independent judgment is preserved.
10. Run compliance checks over all units: schema, approved evidence path, allowed labels, required fields, unit coverage, duplicate observations, retry and refusal rules, version hashes, raw-output completeness, and no silent gaps. Reconcile every count to the fixed sample.
11. Give the code, frozen artifacts, logs, and outputs to a fresh second model instance for audit (per `workflow/shared/fresh-review.md`). It reports bugs, nondeterminism, leakage, fragile assumptions, security issues, and missing tests in code_review.md; it does not silently fix code or recode observations.
12. Create pilot_revision_queue_vNNN.csv for every codebook ambiguity, schema defect, prompt problem, source issue, operational failure, and deferred adversarial test. Include severity, evidence, proposed upstream stage, and disposition. The active package remains frozen throughout this run.
13. Write pilot_report_vNNN.md with exact sample and completion counts, compliance results, disagreement patterns, diagnostic metrics with small-sample caveats, costs and timing, code-review findings, threshold results, and recommended accept, revise-and-rerun, or stop disposition. The pilot reports measurement quality only: schema and evidence compliance, coverage, disagreements, and diagnostics. Do not compute or report the substantive estimand, an outcome distribution over the pilot sample, or any outcome-exposure association before the Stage 09 freeze; log any accidental computation as a deviation and disclose it in the preregistration.
14. If a substantive revision is needed, do not change the package here. Route to Stage 04 or 05, recheck authorization in Stage 06 and design freeze in Stage 07, then run a fresh pilot with a new run ID. Acceptance requires a clean run under one fixed package.

## Artifacts

All code and run-level data are immutable under the unique run directory. Raw model outputs are irreplaceable and must be saved before parsing. The researcher review, disagreement table, and revision queue are versioned diagnostic artifacts; pilot units and tuned examples are permanently excluded from held-out validation. Create pilot_acceptance_vNNN.md only after the researcher acts on the gate; it records the accepted run, frozen versions and hashes, thresholds, known limitations, and deferred nonblocking items.

## Verification

- Reconcile every sample unit across sample, run ledger, raw output or typed failure, normalized output where valid, compliance table, and researcher review.
- Require all accepted substantive observations to pass schema and quotation checks; report exact numerator and denominator for every compliance measure.
- Confirm raw files are unchanged, normalized rows preserve provenance, retries use fixed rules, and no definition changed during the run.
- Confirm every observation and failure received researcher review and every disagreement has a disposition or remains explicitly unresolved.
- Confirm the independent code audit ran and all fatal or major issues are fixed through a new run or block acceptance.
- Compare results with the predeclared thresholds without moving the thresholds after seeing performance.
- Confirm the pilot report contains no substantive estimand, outcome distribution, or outcome-exposure association computed on pilot data.

## State transition

Do not alter state in Plan Mode. At execution start, set current_stage to 08-pilot and status to running and append the run. Missing human review sets waiting_for_user; software or compliance failure sets failed; a revision requirement records the upstream failure route. Do not activate revised codebook artifacts from this stage.

After the report verifies, activate the pilot artifacts except the acceptance memo, set status to awaiting_approval, mark pilot-acceptance pending, and list every unresolved disagreement and threshold failure. On explicit acceptance, create pilot_acceptance_vNNN.md, append the decision and exact run and artifact hashes, mark the gate approved, activate the memo, and set current_stage to 09-freeze-and-preregister and status to ready. Rejection returns through the named upstream stages and requires a new pilot.

## Next-stage handoff

After acceptance, report exact completion and compliance counts, active pilot and frozen-package versions, and deferred limitations. Provide the exact next task: enter Plan Mode for 09-freeze-and-preregister, prepare a result-free preregistration and hash manifest, and stop before any external registration until the researcher approves it.
