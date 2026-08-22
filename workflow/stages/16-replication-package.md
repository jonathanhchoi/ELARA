---
stage_id: "16-replication-package"
title: "Build and verify the replication package"
paper_steps: ["5"]
core: true
interaction_profile: "execute"
long_running: true
goal_condition: "Run Stage 16 exactly as specified until the lawful versioned replication package, manifest, and checksums pass, one clean downstream command rebuilds every reported number, a fresh agent verifies the rebuild, restrictions and non-rerunnable steps are disclosed, and PROJECT_STATE.md records the core pipeline complete, or until a redistribution question, rebuild discrepancy, recorded failure route, or other ELARA section 11 stop condition is surfaced."
prerequisites: ["15-robustness"]
required_inputs: ["project/PROJECT_STATE.md", "project/artifacts/frozen_artifact_manifest_vNNN.csv", "project/artifacts/preregistration_vNNN.md", "project/artifacts/preregistration_record_vNNN.md", "project/artifacts/data_authorization_record_vNNN.md", "project/artifacts/corpus_manifest_vNNN.csv", "project/artifacts/provenance_manifest_vNNN.csv", "project/artifacts/corpus_gap_register_vNNN.csv", "project/artifacts/coding_dataset_vNNN.jsonl", "project/artifacts/coding_ledger_vNNN.csv", "project/artifacts/schema_validation_vNNN.csv", "project/artifacts/quote_verification_vNNN.csv", "project/artifacts/interpretive_audit_vNNN.jsonl", "project/artifacts/adjudicated_validation_data_vNNN.csv", "project/artifacts/validation_metrics_vNNN.json", "project/code/analysis_vNNN/", "project/artifacts/analysis_results_vNNN/", "project/artifacts/measurement_error_correction_vNNN.json", "project/artifacts/robustness_results_vNNN/", "project/artifacts/robustness_report_vNNN.md", "project/runs/", "project/DEVIATIONS.md"]
declared_outputs: ["project/artifacts/replication_package_vNNN/", "project/artifacts/replication_manifest_vNNN.json", "project/artifacts/replication_checksums_vNNN.txt", "project/artifacts/replication_rebuild_report_vNNN.md", "project/artifacts/fresh_agent_rerun_report_vNNN.md", "project/runs/<run_id>/rebuild_logs/", "project/runs/<run_id>/run_manifest.json", "project/PROJECT_STATE.md", "project/DECISIONS.md", "project/RUN_LEDGER.md", "project/DEVIATIONS.md"]
human_gate: null
next_stage: "17-skeleton-draft"
failure_routes: ["10-corpus-acquisition", "11-scale-up", "12-interpretive-verification", "13-human-validation", "14-analysis-and-correction", "15-robustness", "16-replication-package"]
---

## Objective

Assemble a replication package, preserved unchanged once complete, containing the prompts, source and processing history, raw model outputs, validation evidence, code that applies the same mechanical rules each time, environment, and final data required to rebuild every reported result. Prove the package in a clean location with a fresh agent and no model-vendor call. The mandatory core ends only when that rebuild succeeds or every irreproducible item is expressly identified as a blocking failure.

## Prerequisite checks

Read `AGENTS.md` and route this stage from `project/PROJECT_STATE.md` before doing any work; the standing rules and exact active versions control every check below.

1. Resolve every exact project-file version and run currently recorded in state. Confirm Stages 10–15 are complete for those versions and no open acquisition, coding, interpretive, validation, analysis, or robustness queue remains.
2. Inventory every number, table, figure, dataset, prompt, model condition, raw response, validation input, amendment, and deviation that the project treats as current. Confirm a script and command using the same mechanical rules each time produce each analytical output from preserved inputs.
3. Re-read the data-authorization and redistribution terms. Identify files that may be archived publicly, shared only under controlled access, or not redistributed. The package must never copy restricted, confidential, privileged, sealed, personal, or licensed text beyond the approved route.
4. Confirm secrets, credentials, tokens, local usernames, temporary paths, and unnecessary personal identifiers can be excluded without breaking the rebuild. If required material is missing or unlawful to package, do not claim a complete package.

## Researcher decisions

The researcher decides the public, controlled-access, and nonshareable components; the archive destination and license; any permitted redaction; and whether a disclosed inability to redistribute source text is acceptable for release. The agent may assemble and test the package. It may not weaken restrictions, publish a package, omit an unfavorable output, or describe a failed rebuild as successful.

## Mode handoff

Follow `workflow/shared/execution-control.md` and create the native stage plan
before work. This is a long-running execution stage: the `goal_condition`
recorded in the settings at the top of this file must be the active goal before
execution begins. If it is not
active, provide `/goal <goal_condition>` and stop. Do not perform packaging in
Plan Mode. Keep the native plan and durable run checkpoints aligned through the
clean rebuild and fresh-agent verification. If goals are unavailable, record
the fallback and use normal approved execution with the same completion
condition.

## Work

1. Allocate a unique run ID and package version, record every active input path and hash, set the stage running, and append a ledger start. Build in a new directory; never reorganize, overwrite, or delete the working project to make the package tidy.
2. Copy the full frozen instruction set: standing instructions, methods, hypotheses, codebook, required coding-output format, complete list of units eligible for coding, coding prompt, worked examples, preregistration and amendments, and every robustness paraphrase. Record exact model identifiers, access routes, run dates, all sampling and model settings including defaults, and provider fields that were unavailable.
3. Include records of acquisition, sources, and processing: the corpus and source lists, search and download logs, transformation and OCR records, values used to verify that files have not changed, the evidence policy, every missing or unusable item and its reason, duplicate decisions, the authorization statement, and exact access instructions for material that cannot be included. Do not include restricted files merely to make the package self-contained.
4. Include records of how parallel agents ran and how their work was checked: pipeline code, exact prompts or values used to verify the prompts, every raw model output and failed attempt, coding and status ledgers, required-output and quotation checks, independent coding reviews, human coder instructions and permitted data, sampling probabilities, blind adjudication data, performance measures, and robustness conditions.
5. Include the final analysis dataset, versioned analysis code, machine-readable estimates, generated tables and figures, measurement-error inputs and outputs, script-output manifest, tests, and all deviations. Every reported result must be generated, not manually transcribed.
6. Create a package README following the Social Science Data Editors template: scope, directory map, data restrictions, prerequisites, exact command order, a single downstream rebuild command, expected outputs, approximate runtime and cost, script-to-table and figure mapping, steps that may produce different results when repeated with the same inputs, and which original model calls cannot be reproduced, with preserved raw outputs identified as the record of those calls. Include one data-availability statement per source — access class, expected persistence or DOI, access procedure, and time and cost to obtain — plus a rights statement certifying legitimate access and permission to use and redistribute each source, formal dataset citations, IRB or ethics approval identifiers where applicable, and a computational-requirements section stating machine specification and per-script runtime.
7. Record the exact software environment with the ecosystem's lock or requirements files, interpreter and system-tool versions, locale, hardware notes, and random seeds (the starting values used to reproduce random procedures). Add small lawful example files for integrity tests where restricted source data cannot be distributed.
8. Create `replication_manifest_vNNN.json` with every packaged or intentionally omitted item, role, exact source-file version, relative path, checksum (a value used to verify that a file has not changed), size, license or access class, and rebuild dependency. Create the checksum file from package contents after assembly.
9. Copy the package to a new clean test location outside the working project. Give a fresh agent only the package README and files. It must install or verify the exact recorded software environment, run tests, execute the documented rebuild from preserved raw outputs, and map every generated number, table, and figure back to the list of package files. It must not call a model provider or rely on undeclared workspace files.
10. Compare rebuilt machine-readable outputs and reported numbers to active Stage 14 and Stage 15 artifacts using exact equality or the prespecified numerical tolerance. Record commands, environment, runtime, warnings, hashes, discrepancies, missing dependencies, and every manual step in both rebuild reports.
11. Scan the final package for secrets, absolute local paths, unauthorized source text, omitted active results, broken relative links, unhashed files, stale versions, and undocumented network dependencies. Recompute checksums after any correction and rerun the clean test.

## Artifacts

`replication_package_vNNN/` is the self-contained lawful set of files and includes its README, exact software versions, rebuild command, tests, prompts, raw outputs, validation data, code, and permitted results. `replication_manifest_vNNN.json` maps the exact project files currently in use to package paths or documented omissions and access instructions. The checksum file records values used to verify the package's contents. The rebuild report records the clean mechanical test; the fresh-agent report independently states what reproduced, what did not, and why. The record of the run and its logs preserve how the package was built and tested.

## Verification

- Confirm every project file currently in use and every reported number, table, and figure appears in `replication_manifest_vNNN.json` as included or expressly omitted for a documented authorization reason.
- Verify checksums, relative paths, environment locks, tests, command order, and script-output mappings from inside a clean copy with no access to the working repository. Where Python is available, run scripts/verify_freeze.py and scripts/validate_run.py and archive their outputs.
- Confirm the README carries a data-availability and rights statement for every source, formal dataset citations, ethics identifiers where applicable, and computational requirements, and that the fresh agent checked they are truthful.
- Confirm the one-command downstream rebuild uses archived raw model outputs and reproduces every reported number within the approved tolerance without a model-vendor call.
- Confirm the fresh agent used only declared package files and recorded all discrepancies and manual steps; independently reopen a sample of its output mappings.
- Scan for secrets, personal or restricted data, absolute workstation paths, fake URLs, stale artifacts, and unauthorized redistribution. Confirm controlled-access instructions are sufficient without exposing credentials.
- Confirm the package and prior project files remain unchanged, the final checksum covers the delivered version, and no failed or unfavorable result was omitted.

## State transition

Set `current_stage` to `16-replication-package` and `status` to `running` only after checks pass. A missing or inconsistent upstream artifact routes to the stage that owns it. A redistribution question sets `waiting_for_user`; a rebuild discrepancy sets `failed` at this stage until corrected and retested. Preserve each failed package and report as a versioned audit trail.

After the lawful package passes every verification, activate the package, manifest, checksums, and reports; append the final rebuild command and outcome; keep `current_stage` at `16-replication-package`; and set `status` to `complete`. This completes the mandatory core. Do not begin manuscript work merely because `next_stage` names an optional module.

## Next-stage handoff

Tell the researcher the package version and checksum, archive contents and restrictions, exact rebuild command, clean-environment result, fresh-agent result, runtime, any non-rerunnable model step, and any controlled-access requirement. State that the core pipeline is complete. Offer optional `17-skeleton-draft` as the default next step, with a recorded skip as the alternative. Explain that it organizes the full article and presents the complete results through verified displays with sufficient captions and notes. The researcher writes the remaining prose.
