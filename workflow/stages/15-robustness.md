---
stage_id: "15-robustness"
title: "Test prompt and model robustness"
paper_steps: ["5"]
core: true
interaction_profile: "execute"
long_running: true
prerequisites: ["14-analysis-and-correction"]
required_inputs: ["project/PROJECT_STATE.md", "project/artifacts/methods_plan_vNNN.md", "project/artifacts/preregistration_record_vNNN.md", "project/artifacts/codebook_vNNN.md", "project/artifacts/coding_schema_vNNN.json", "project/artifacts/coding_prompt_vNNN.md", "project/artifacts/data_authorization_record_vNNN.md", "project/artifacts/held_out_sample_vNNN.csv", "project/artifacts/adjudicated_validation_data_vNNN.csv", "project/artifacts/validation_metrics_vNNN.json", "project/code/analysis_vNNN/", "project/artifacts/analysis_dataset_vNNN.csv", "project/artifacts/analysis_results_vNNN/", "project/artifacts/measurement_error_correction_vNNN.json"]
declared_outputs: ["project/artifacts/robustness_specification_vNNN.md", "project/artifacts/prompt_paraphrases_vNNN.md", "project/artifacts/robustness_dataset_vNNN.jsonl", "project/artifacts/robustness_metrics_vNNN.json", "project/artifacts/robustness_results_vNNN/", "project/artifacts/robustness_report_vNNN.md", "project/runs/<run_id>/prompts/", "project/runs/<run_id>/raw_model_outputs/", "project/runs/<run_id>/unit_attempts.jsonl", "project/runs/<run_id>/schema_and_quote_checks/", "project/runs/<run_id>/run_manifest.json", "project/PROJECT_STATE.md", "project/DECISIONS.md", "project/RUN_LEDGER.md", "project/DEVIATIONS.md"]
human_gate: null
next_stage: "16-replication-package"
failure_routes: ["05-codebook-and-schema", "06-data-authorization", "08-pilot", "13-human-validation", "14-analysis-and-correction", "15-robustness"]
---

## Objective

Test whether validation performance and downstream conclusions are fragile to reasonable paraphrases of the frozen coding prompt or to an independently identified second model. Preserve the human benchmark as ground truth, apply the same schema, checks, analysis, and correction to every variant, and report the full spread rather than choosing a preferred specification after seeing results.

## Prerequisite checks

Read `AGENTS.md` and route this stage from `project/PROJECT_STATE.md` before doing any work; the standing rules and exact active versions control every check below.

1. Resolve exact active validation and analysis versions. Confirm that the validation sample, human labels, base prompt, model settings, analysis commands, correction, comparison metrics, and any robustness acceptance rules are fixed in the approved methods or preregistration.
2. Confirm the planned paraphrase count and construction rule and the second model or model-selection rule. If those choices are absent and could be results-responsive, obtain and record a researcher decision before execution; do not invent thresholds or shop among variants.
3. Confirm Stage 06 authorization covers the second provider or self-hosted route and the protected sample. Keep adjudicated gold labels hidden from every coding request until all variant predictions are frozen.
4. Verify model availability, exact identifiers, context capacity, structured-output support, settings, expected cost, and a common unit-level input representation. If a provider cannot implement the frozen task comparably, report that limitation rather than disguising a different task as robustness.
5. Dry-run the variant runner, schema validator, quote verifier, and analysis interface on fixtures without exposing gold labels. If a prerequisite fails, make no writes and leave state unchanged.

## Researcher decisions

The researcher approves the paraphrase rule, second-model choice, comparison metrics, any materiality criterion, and the scientific disposition of instability. The agent may create semantically faithful variants under that rule and compute comparisons. It may not alter the construct, examples, schema, evidence requirement, sample, or settings to favor agreement; select only the best-performing paraphrase; or treat cross-model agreement as a substitute for human validation.

## Mode handoff

This is a long-running execution stage. In Codex, `/goal` may be used with this objective: **Run every approved prompt-paraphrase and second-model robustness condition on the protected validation sample, one unit per fresh context, preserve raw outputs, apply identical checks and downstream analysis, and report the complete stability spread.** In Claude Code, invoke `/elr-code-observations` and the saved dynamic workflow on the frozen condition manifest. If the adapter is unavailable, use normal approved execution with durable checkpoints. Do not execute a robustness search in Plan Mode.

## Work

1. Allocate a unique run ID and output versions, persist the exact robustness specification, record input hashes and all condition settings, set the stage running, and append a ledger start.
2. Generate only the approved number of prompt paraphrases before running any of them. Preserve the task, codebook definitions, evidence-first order, examples, schema, uncertain option, and approved evidence paths; vary wording or organization only as the approved rule permits. Hash and freeze every prompt.
3. Define the base-model, paraphrase, and second-model conditions in advance. Use the same validation units, source representation, metadata, retry policy, and provider settings to the extent technically possible. Record every unavoidable difference.
4. Submit one validation unit per fresh model context under `workflow/shared/observation-fanout.md`, with the robustness condition included in the immutable assignment identity. Do not provide human labels, adjudication outcomes, earlier model answers, or condition-level performance. Archive each exact prompt, raw response, model identifier, settings, timestamp, and attempt before parsing.
5. Apply the frozen schema and evidence checks to every condition. Preserve failures and retries as typed attempts. Do not hand-repair output or relax a check for one model.
6. After all predictions are immutable, join them to the adjudicated human data and calculate the same approved validation metrics, weights, and uncertainty for each condition. Cross-model agreement is a fragility diagnostic, not accuracy evidence.
7. Feed each condition through the identical Stage 14 transformation, hypothesis modules, and approved measurement-error correction. Do not alter covariates, samples, correction, or table definitions by condition.
8. Compare the prespecified downstream quantities: estimates, intervals, sign, magnitude, classification error, and other estimand-appropriate measures named in the robustness specification. Because every condition codes the identical units, build unit-level condition-by-condition disagreement matrices and estimate paired differences with uncertainty for the validation metrics and downstream quantities — paired comparisons are far more powerful than comparing marginal intervals. Include a minimum-detectable-difference statement in the report given the validation-sample size. Report every condition and the complete spread; never rank and retain only the favorable one.
9. Diagnose instability by variable, label, document characteristics, and failure type. Prompt sensitivity may reveal an underspecified codebook; model sensitivity may reveal a brittle operationalization. Route revisions through Stage 05, Stage 08, and a new validation cycle rather than editing this run.
10. Have a fresh reviewer verify that paraphrases are semantically faithful, the gold labels remained sealed during prediction, settings and samples are comparable, raw attempts exist, and all conditions flow through identical analysis code.

## Artifacts

The robustness specification fixes conditions and comparisons before results. The paraphrase file contains full frozen prompts and hashes. `robustness_dataset_vNNN.jsonl` links every unit-condition prediction to its raw attempt and human benchmark only after unsealing. The metrics file contains condition-level validation and comparison statistics. `robustness_results_vNNN/` contains machine-readable downstream estimates and generated comparisons. The report describes model and prompt differences, failures, validation and coefficient spread, instability patterns, limitations, and any routed revision. Run files preserve exact prompts, responses, checks, and settings.

## Verification

- Confirm all robustness conditions were fixed before any condition result was inspected and every planned condition and validation unit has a terminal status.
- Confirm one unit occupied each fresh context, gold labels remained unavailable during prediction, and every output links to an archived prompt and raw response.
- Confirm schema, evidence, retry, sampling, validation, analysis, and correction rules were identical across conditions except for documented unavoidable model differences.
- Recompute condition metrics and downstream estimates; confirm every condition appears in the report and no unfavorable variant was dropped.
- Confirm paraphrases preserve the same construct and second-model comparisons are described as robustness, not independent validation.
- Confirm stability is claimed only where the paired comparison could detect the prespecified materiality threshold; otherwise the report must disclose that the check was underpowered to detect the stated difference, not read absence of evidence as evidence of absence.
- Confirm no prior prompt, raw response, human label, result, or ledger row was overwritten and every authorization or feasibility limitation is explicit.

## State transition

Set `current_stage` to `15-robustness` and `status` to `running` only after checks pass. An authorization problem routes to Stage 06. A semantically noncomparable model or unavailable required condition sets `waiting_for_user` for a recorded researcher decision or amendment. A codebook or pilot defect routes to Stages 05 and 08; a validation or analysis defect routes to Stages 13 or 14. Preserve every attempted condition.

After all approved conditions and comparisons pass verification, activate the specification, prompts, dataset, metrics, results, report, and run; append any fragility finding without suppressing it; set `current_stage` to `16-replication-package`; and set `status` to `ready`. A robustness failure is a substantive finding, not permission to choose a different prompt after the fact.

## Next-stage handoff

Tell the researcher every condition run, model and settings, validation and downstream spread, materiality comparison if one was prespecified, instability patterns, missing conditions, routed revisions, and exact active versions. Then provide the exact next task: build `16-replication-package`, including every prompt variant and raw output, and prove in a clean environment that archived artifacts rebuild every reported number without calling a model vendor.
