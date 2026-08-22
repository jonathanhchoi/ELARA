---
stage_id: "14-analysis-and-correction"
title: "Run the approved analysis and correct for coding errors"
paper_steps: ["5"]
core: true
interaction_profile: "plan_then_execute"
long_running: true
goal_condition: "Run Stage 14 exactly as specified until every approved hypothesis module and the clean complete build reproduce from archived inputs, confirmatory outputs are hash-pinned before exploration, correction uncertainty is propagated, every declared artifact passes verification, and PROJECT_STATE.md is ready for Stage 15, or until an unresolved preregistration choice, recorded failure route, or other ELARA section 11 stop condition is surfaced; do not choose a result-affecting open method after seeing results."
prerequisites: ["13-human-validation"]
required_inputs: ["project/PROJECT_STATE.md", "project/artifacts/frozen_artifact_manifest_vNNN.csv", "project/artifacts/methods_plan_vNNN.md", "project/artifacts/hypotheses_vNNN.md", "project/artifacts/estimands_vNNN.csv", "project/artifacts/sampling_validation_plan_vNNN.md", "project/artifacts/preregistration_vNNN.md", "project/artifacts/preregistration_record_vNNN.md", "project/code/frozen_analysis_vNNN/", "project/artifacts/coding_dataset_vNNN.jsonl", "project/artifacts/interpretive_audit_vNNN.jsonl", "project/artifacts/adjudicated_validation_data_vNNN.csv", "project/artifacts/validation_metrics_vNNN.json", "project/artifacts/human_validation_report_vNNN.md", "project/artifacts/human_validation_disposition_vNNN.md", "project/DEVIATIONS.md"]
declared_outputs: ["project/artifacts/analysis_execution_plan_vNNN.md", "project/code/analysis_vNNN/", "project/artifacts/analysis_dataset_vNNN.csv", "project/artifacts/analysis_results_vNNN/", "project/artifacts/measurement_error_correction_vNNN.json", "project/artifacts/script_output_manifest_vNNN.csv", "project/artifacts/analysis_report_vNNN.md", "project/runs/<run_id>/commands.log", "project/runs/<run_id>/test_results/", "project/runs/<run_id>/run_manifest.json", "project/PROJECT_STATE.md", "project/DECISIONS.md", "project/RUN_LEDGER.md", "project/DEVIATIONS.md"]
human_gate: null
next_stage: "15-robustness"
failure_routes: ["04-methods-design", "09-freeze-and-preregister", "11-scale-up", "12-interpretive-verification", "13-human-validation", "14-analysis-and-correction"]
---

## Objective

Create and execute separately runnable analysis code that produces the same results from the same inputs and rules for every approved hypothesis and estimand (the quantity the analysis seeks to estimate), using the actual validated data structure. Produce uncorrected results and the prespecified results corrected for coding errors, with appropriate uncertainty, generated tables and figures, and a complete list linking each script to its outputs. Do not edit a manuscript or choose analyses after seeing which result is attractive.

## Prerequisite checks

Read `AGENTS.md` and route this stage from `project/PROJECT_STATE.md` before doing any work; the standing rules and exact active versions control every check below.

1. Resolve exact active inputs and confirm the `validation-disposition` gate passed for those versions. Recompute the active dataset and validation counts and confirm no unresolved interpretive or adjudication queue remains.
2. Compare methods, hypotheses, preregistration, amendment record, and deviations. Enumerate confirmatory analyses, approved robustness analyses reserved for Stage 15, exploratory analyses, estimands, covariates, exclusions, weights, uncertainty method, the multiplicity policy and its family definitions, the clustering or dependence level declared per estimand, the attrition threshold and treatment, and measurement-error correction. Load the frozen Stage 09 analysis code by manifest hash; the confirmatory build runs those scripts, any edit is a logged deviation, and a material edit routes through the amendment policy.
3. Inspect the actual coding and validation files—their fields, types, missingness, identifiers, nesting, label values, and sampling-probability columns—before proposing code. Do not design against a remembered or hypothetical schema.
4. Confirm that the plan supplies every choice that could materially affect a result. If not, the plan must surface the choice and stop for the researcher (a stop condition under `workflow/shared/guardrails.md` §11, because such a choice must be fixed before any result is seen); execution may not invent a correction method, model specification, transformation, threshold, or missing-data rule.

## Researcher decisions

The researcher decides the quantities to estimate, model specifications, how hypotheses map to variables, any departure from the preregistration, the valid correction for coding errors, treatment of ambiguous or rare classes, and what exploratory work to authorize. The agent may identify incompatibilities and implement approved mathematics. It may not add controls, outcomes, subgroups, exclusions, or transformations because they improve significance, nor may it reclassify an unregistered analysis as confirmatory.

## Mode handoff

Follow `workflow/shared/execution-control.md` and create the native stage plan
before work. Plan first, read-only. Do not write any project file until the plan
is complete. Present a decision-complete, hypothesis-by-hypothesis execution
plan grounded in the inspected files and preregistered analysis, including exact
inputs, transformations, estimands, correction and uncertainty procedure,
command interface, tests, and expected outputs. A result-affecting analysis
choice left open by the preregistration is a stop condition: surface it and stop
before executing, because it must be fixed before any result is seen; only
operational choices take a provisional `assistant-default`. Then continue into execution in the same session, without waiting,
unless a stop condition in `workflow/shared/guardrails.md` §11 holds;
only then enter Plan Mode, stop, and give the exact execution handoff. Because
the execution is long-running, the `goal_condition` recorded in the settings at
the top of this file must be the
active goal before the first execution write. If it is not active, provide
`/goal <goal_condition>` and stop. Keep each hypothesis separately runnable and
the native plan current through the clean rebuild.

## Work

1. After plan approval, allocate a unique run ID and output versions, persist the approved execution plan, record input hashes, set the stage running, and append a ledger start.
2. Build the analysis dataset by deterministic code from the active coding data, audit statuses, adjudicated validation data, and approved external covariates. Preserve stable IDs and explicit denominators; never hand-edit a derived row.
3. Structure `analysis_vNNN/` so each hypothesis or estimand has a stable identifier and can run alone through `--analyses <id>` as well as in the full build. Centralize shared transformations and prevent one module from silently changing another's sample.
4. Encode the preregistered inclusion, exclusion, aggregation, weighting, model, missing-data, multiplicity-adjustment, and per-estimand clustering rules literally. Report unadjusted and family-adjusted inference side by side for every confirmatory estimate, per the preregistered policy. Label authorized post-registration work as exploratory in code, filenames, tables, and the report. Append any material departure before running affected results.
5. Implement tests for schema and type assumptions, unique keys, merge cardinality, denominators, missing values, weights, expected coefficient direction on synthetic fixtures, and deterministic output naming. Run tests on fixtures and a small real-data slice and inspect outputs before the full run.
6. Produce the naive result and the approved validation-based correction from the same explicit estimand. Use the adjudicated confusion structure, inclusion probabilities, and subgroup information exactly as the approved method requires. Propagate first-stage or measurement-model uncertainty rather than treating estimated error rates as known.
7. If the approved correction is unsupported by the observed validation design, sparse cells, or data shape, stop and report the incompatibility. Do not silently replace it with Aigner rescaling, regression calibration, a two-regression adjustment, design-based supervised learning, prediction-powered inference, or another method merely because code is available; workflow/shared/measurement-error-correction-guide.md informs the researcher's decision and never authorizes a substitution.
8. Produce, by script, a table showing how many records are lost at each step from the fixed starting count through the analyzable observations, keyed to the Stage 10 and Stage 11 reasons for missing or unusable records; compare analyzed and non-analyzed listed units using the descriptive fields in the eligible-unit list; and execute the prespecified sensitivity treatment whenever the plan's gap-rate threshold is exceeded, reporting its results alongside the confirmatory estimates.
9. Pin random seeds, sort orders, locale and time behavior, dependency versions, and numerical settings that affect results. Record every command and environment fact needed to reproduce the run. Nondeterministic procedures must use the approved reproducibility protocol.
10. Write machine-readable estimates and generated tables and figures directly from code. Never retype a number or manually redraw a result. The script-output manifest maps every hypothesis, command, input, sample count, estimate, table, and figure.
11. Run the confirmatory modules first and hash their machine-readable outputs into the run manifest before any exploratory module executes; a later change to shared transformation or confirmatory code invalidates that checkpoint and forces a confirmatory rerun. Then run each hypothesis alone and the complete build in a clean output directory. Compare shared results and hashes or approved numerical tolerances. Have a fresh reviewer (per `workflow/shared/fresh-review.md`) inspect code against the actual files and approved plan, rerun the build, and challenge confirmatory/exploratory labeling.

## Artifacts

The execution plan contains the approved analysis instructions. `analysis_vNNN/` contains tested, versioned code and its software requirements. `analysis_dataset_vNNN.csv` is produced entirely by code, not edited by hand. `analysis_results_vNNN/` contains estimates in structured data files plus generated tables and figures. `measurement_error_correction_vNNN.json` records the validation inputs, method, assumptions, uncorrected and corrected estimates, uncertainty, and checks on the method. `script_output_manifest_vNNN.csv` links commands to every result. The report states samples, deviations, failures, confirmatory and exploratory results, and what remains provisional.

## Verification

- Rebuild the analysis dataset from active inputs and confirm IDs, merge cardinalities, exclusions, denominators, weights, and missingness match the approved plan.
- Run all tests; execute every `--analyses <id>` target separately and together; and confirm shared estimates agree within the predeclared numerical tolerance.
- Recompute a sample of statistics independently and trace every reported number, table, and figure to a command and machine-readable result.
- Confirm measurement-error inputs come from the exact approved validation version, sampling design is honored, and uncertainty includes the approved first-stage component.
- Confirm the confirmatory build ran the frozen Stage 09 analysis code by hash, every departure from it is a logged deviation, and every enumerated open parameter was set by its outcome-blind rule.
- Confirm every confirmatory estimate's standard errors implement the estimand's declared clustering level and the family-adjusted inference was computed from the preregistered family definition.
- Confirm from the values recorded to verify that files have not changed, along with timestamps, that no exploratory output predates the frozen confirmatory outputs, and that the table showing records lost at each step, covariate comparison, and any triggered sensitivity treatment are reported.
- Confirm no specification was chosen or relabeled after inspecting results, and all departures and exploratory analyses are explicit.
- Confirm a clean rerun succeeds, no manuscript was edited, and no prior code, result, validation input, or ledger row was overwritten.

## State transition

The plan phase leaves files and state unchanged. After the plan (and any approval a stop condition required) and execution start, set `current_stage` to `14-analysis-and-correction` and `status` to `running`. A data or audit defect routes to Stages 11–13. An unregistered methods change routes to Stage 04 and, where required, Stage 09. A correction incompatibility routes to Stage 13 or awaits an explicit methods decision; preserve the failed run and exact diagnostics.

After every approved analysis and clean rebuild passes verification, activate the execution plan, code, dataset, results, correction, manifest, report, and run; set `current_stage` to `15-robustness`; and set `status` to `ready`. Results remain subject to Stage 15 robustness and must not yet be described as final validated findings.

## Next-stage handoff

Tell the researcher the exact samples, confirmatory and exploratory analyses, naive and corrected estimates, uncertainty method, deviations, failed or sparse specifications, rebuild command, active versions, and output map. Then provide the exact next task: run `15-robustness` on the protected validation sample using the approved prompt paraphrases and second model, and compare downstream results under the same analysis and correction code.
