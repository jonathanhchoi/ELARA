---
stage_id: "04-methods-design"
title: "Design the methods"
paper_steps: ["2"]
core: true
interaction_profile: "plan_then_execute"
long_running: false
goal_condition: null
prerequisites: ["03-feasibility-audit"]
required_inputs: ["project/PROJECT_STATE.md", "project/artifacts/preemption_review_vNNN.docx", "project/artifacts/feasibility_audit_vNNN.md", "approved feasibility decision"]
declared_outputs: ["project/artifacts/methods_plan_vNNN.md", "project/artifacts/hypotheses_vNNN.md", "project/artifacts/estimands_vNNN.csv", "project/artifacts/sampling_validation_plan_vNNN.md", "project/runs/<run_id>/run_manifest.json", "project/PROJECT_STATE.md", "project/DECISIONS.md", "project/RUN_LEDGER.md", "project/DEVIATIONS.md"]
human_gate: "methods-plan-approval"
next_stage: "05-codebook-and-schema"
failure_routes: ["02-preemption-review", "03-feasibility-audit", "04-methods-design"]
---

## Objective

Turn the accepted project into a decision-complete empirical design without outsourcing the researcher's substantive judgments. Define the target population, sampling and coding units, constructs, estimands, hypotheses, comparisons, validation design, error correction, deterministic analysis, and stopping rules before building the codebook or inspecting study outcomes.

## Prerequisite checks

1. Read AGENTS.md and PROJECT_STATE.md, then confirm that the preemption and feasibility gates are approved and load their exact active versions and conditions.
2. Verify that the proposed research question, contribution, corpus, and resource envelope still match those reviews. Flag any material change for an upstream rerun. Compare the current date to the recommended novelty recheck date recorded with the preemption disposition; if it has passed and the review flagged medium-or-high scoop risk, run a versioned targeted refresh of the Stage 02 saturation and closest-author queries before designing methods against a stale verdict.
3. Identify all researcher-owned choices that remain open. Do not hide them in technical defaults. Power and significance defaults, precision targets, and multiplicity procedures are researcher decisions to approve explicitly, not silent settings.
4. Confirm that no study outcome has been computed or inspected beyond the exposure recorded in the Stage 03 probe-exposure manifest. Feasibility probes legitimately produce outcome information; load the manifest, record its extent, and design the confirmatory/exploratory distinction around it. If other outcome information is already known, record that fact as well.
5. Read the actual metadata structure or representative authorized files before proposing fields or code. Do not assume the data shape.

## Researcher decisions

The researcher must decide or approve:

- the substantive theory and honest contribution;
- descriptive, associational, or causal claim boundaries and any identification assumptions;
- target population, sampling frame, inclusion and exclusion rules, temporal and jurisdictional scope;
- constructs, operationalizations, primary and secondary outcomes, comparisons, estimands, and hypotheses;
- treatment of opinions, parties' assertions, dissents, duplicate documents, missingness, and ambiguous cases;
- error tolerances, validation targets, multiplicity policy, and confirmatory versus exploratory analyses; and
- resource, privacy, model, and stopping constraints.

Present meaningful alternatives and consequences. Never make the choice merely because one option is easier to code.

## Mode handoff

Follow `workflow/shared/execution-control.md` and create the native stage plan
before work. Plan first, read-only. Inspect inputs, weigh architecture and
alternatives, settle the design choices (recommend one option with evidence and
record it as a provisional `assistant-default` where the researcher has not
decided), and produce a decision-complete proposed design in chat; do not write
any project file, allocate a run, update state, or append ledgers until the plan
is complete. Then continue into execution in the same session, without waiting,
unless a stop condition in `workflow/shared/guardrails.md` §11 holds; only then
enter Plan Mode, stop, and give the exact execution handoff. Execute Stage 04,
verify the four declared design artifacts, and stop at `methods-plan-approval`,
presenting the provisional choices for the researcher to keep or change. This
stage is bounded: maintain the native plan but do not start a goal.

## Work

1. Allocate a unique run ID only after execution begins. Capture all active input versions, hashes, accepted feasibility conditions, and researcher decisions.
2. State the research question, theory, intended contribution, scope of inference, and what each plausible result would mean. Separate normative motivation from empirically testable claims.
3. Define the target population, sampling frame, document unit, coding unit, unit of analysis, clustering level, and denominator for every reported quantity. Explain how multiple documents, opinions, passages, or observations within a matter relate.
4. Specify inclusion, exclusion, deduplication, time, jurisdiction, language, version, and missing-document rules. Make the unit space enumerable before coding.
5. Define each construct independently of a model. Prefer document-observable, quote-backed components over holistic ratings. Map constructs to planned variables but reserve full edge-case rules for Stage 05.
6. Create hypotheses_vNNN.md with stable IDs, theory, variables, population, comparison, direction or explicitly nondirectional test, and decision rule. Label primary, secondary, falsification, and exploratory questions. Do not retrofit hypotheses to pilot or study outcomes.
7. Create estimands_vNNN.csv with stable IDs and columns for population, unit, outcome or measure, exposure or comparison, contrast, aggregation, denominator, clustering, missing-data treatment, error-correction requirement, linked hypothesis, inference procedure (standard-error estimator, clustering level, small-sample correction, confidence level, and sidedness consistent with the hypotheses file), multiplicity family and correction method, minimum detectable effect or target precision, assumed power and significance level, and effective sample size under the central funnel scenario.
8. Design sampling and power or precision analysis using the feasibility funnel, base rates, and the archived Stage 03 minimum-detectable-effect calculations. State which units are feasibility-probe units (from the Stage 03 probe-exposure manifest), prompt-development examples, pilot units, human-validation units, and study units; prevent overlap where independence is required, and exclude probe-exposed and pilot units from the held-out validation frame. Size the validation sample from the approved precision targets on per-class error rates, and include an independently double-coded reliability subsample (ordinarily ten to twenty percent) unless the researcher records a justification for a single-coder design. Fix the held-out validation sampling rule and seed now, preferring a non-gameable derivation — for example, the SHA-256 of the Stage 09 frozen-artifact manifest — so that no one selects a seed after outcomes exist.
9. Specify the LLM's bounded role: one supplied document or unit per call by default, codebook and schema as authority, quotation plus justification before label, uncertain escape, typed unusable rows, no outcome prediction, and no parametric-memory facts.
10. Specify deterministic mechanical checks: schema validation, exact or documented normalized quote matching, identifier and enum checks, coverage reconciliation, duplicate detection, retry limits, refusal tracking, and raw-output preservation.
11. Specify the human validation and blind adjudication design, performance metrics by class and subgroup, acceptance thresholds chosen before results, and the measurement-error correction or sensitivity analyses that use those estimates. Follow the protocol in workflow/shared/measurement-error-correction-guide.md when matching the correction to the estimand and validation design: its requirements are durable, but its named estimators are dated leads, so verify candidates against current literature retrieved during this project and present the tradeoffs; the choice remains the researcher's and must be feasible under the planned sample.
12. Specify deterministic analysis: transformations, models or descriptive summaries, clustering, weighting, missingness, robustness, table and figure generation, and the distinction between preregistered and exploratory outputs. Define the multiplicity policy concretely: enumerate the family of confirmatory tests by hypothesis ID; name the exact adjustment procedure — for example, a familywise correction for the confirmatory core and a false-discovery-rate procedure for secondary families — or record the researcher's written justification for none; and enumerate planned heterogeneity and subgroup analyses, labeling each confirmatory or exploratory. Prespecify the attrition treatment: a corpus gap-rate threshold and the planned response when it is exceeded, such as bounds or documented reweighting. Do not invent causal identification for a descriptive question.
13. Document data authorization dependencies, model and prompt logging, cost controls, progress ledgers, failure and stopping rules, scope-lock behavior, and amendment triggers.
14. Self-critique the design against selection, leakage, construct validity, dependence, subgroup error, outcome peeking, and researcher degrees of freedom. Present unresolved choices rather than silently resolving them.

## Artifacts

methods_plan_vNNN.md is the integrated design and must link stable hypothesis and estimand IDs. hypotheses_vNNN.md and estimands_vNNN.csv are machine-comparable specifications, not prose duplicates. sampling_validation_plan_vNNN.md must identify sample partitions (including the feasibility-probe exclusions), the exact held-out selection seed or derivation rule, target precision with the power and minimum-detectable-effect assumptions and formulas archived from Stage 03, the double-coded reliability subsample, adjudication, thresholds, and correction inputs. The run manifest records exact source versions and decisions.

## Verification

- Trace every hypothesis to one or more estimands and every estimand to observable variables, a denominator, and an analysis.
- Confirm that population, frame, document unit, coding unit, and analysis unit are distinct where necessary and never used interchangeably.
- Confirm that feasibility-probe, prompt-development, pilot, held-out validation, and study sets cannot leak into one another contrary to the plan, and that the held-out seed or derivation rule is fixed.
- Confirm that validation thresholds, precision targets, minimum detectable effects, multiplicity procedures, per-estimand inference procedures, and correction methods are prespecified and feasible under the Stage 03 budget.
- Confirm that every unresolved substantive choice is visible and no study outcome informed the design without disclosure.
- Compare the artifacts with accepted preemption and feasibility conditions and route any material divergence upstream.

## State transition

Do not alter state during Plan Mode. At execution start, set current_stage to 04-methods-design and status to running, append the run, and preserve all prior versions. After verification, activate the new design artifacts, set status to awaiting_approval, mark methods-plan-approval pending, and enumerate unresolved decisions.

Only explicit approval advances the workflow. Append the approval and exact artifact versions to DECISIONS.md, mark the gate approved, and set current_stage to 05-codebook-and-schema and status to ready. A rejected design remains here for a versioned revision. A changed contribution or infeasible resource demand routes to Stage 02 or 03.

## Next-stage handoff

After approval, list the active methods, hypothesis, estimand, and sampling-plan versions. Provide the exact next task: enter Plan Mode for 05-codebook-and-schema, translate only the approved constructs into RA-usable definitions and a closed schema and unit space, and stop for codebook-schema approval.
