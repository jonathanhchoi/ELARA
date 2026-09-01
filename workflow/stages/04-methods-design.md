---
stage_id: "04-methods-design"
title: "Design the methods"
paper_steps: ["2"]
core: true
interaction_profile: "plan_then_execute"
long_running: false
goal_condition: null
prerequisites: ["03-feasibility-audit"]
required_inputs: ["project/PROJECT_STATE.md", "project/artifacts/preemption_review_vNNN.pdf (or the explicit researcher-selected alternative)", "project/artifacts/feasibility_audit_vNNN.pdf (or the explicit researcher-selected alternative)", "approved feasibility decision"]
declared_outputs: ["project/artifacts/methods_plan_vNNN.md", "project/artifacts/hypotheses_vNNN.md", "project/artifacts/estimands_vNNN.csv", "project/artifacts/sampling_validation_plan_vNNN.md", "project/runs/<run_id>/run_manifest.json", "project/PROJECT_STATE.md", "project/DECISIONS.md", "project/RUN_LEDGER.md", "project/DEVIATIONS.md"]
human_gate: "methods-plan-approval"
next_stage: "05-codebook-and-schema"
failure_routes: ["02-preemption-review", "03-feasibility-audit", "04-methods-design"]
---

## Objective

Turn the accepted project into a decision-complete empirical design without outsourcing the researcher's substantive judgments. Define the target population; sampling and coding units; constructs; estimands (the quantities the analysis seeks to estimate); hypotheses; comparisons; validation design; error correction; analysis that produces the same results from the same inputs and rules; and stopping rules before building the codebook or inspecting study outcomes.

## Prerequisite checks

1. Read AGENTS.md and PROJECT_STATE.md, then confirm that the preemption and feasibility gates are approved and load their exact active versions and conditions.
2. Verify that the proposed research question, contribution, collection, and resource limits still match those reviews. Flag any material change for an earlier-stage rerun. Compare the current date to the recommended novelty recheck date recorded with the preemption disposition; if it has passed and the review flagged medium-or-high scoop risk, rerun the Stage 02 searches that test whether further searching still finds relevant work and the closest-author searches before designing methods against an outdated verdict.
3. Identify all researcher-owned choices that remain open. Do not hide them in technical defaults. Power and significance defaults, precision targets, and corrections for multiple comparisons are researcher decisions to approve explicitly, not silent settings.
4. Confirm that no study outcome has been computed or inspected beyond the exposure recorded in the Stage 03 probe-exposure manifest. Feasibility probes legitimately produce outcome information; load the manifest, record its extent, and account for it when deciding which hypotheses and analyses must be fully specified and preregistered before outcomes are examined and which analyses will be exploratory. If other outcome information is already known, record that fact as well.
5. Read the actual metadata structure or representative authorized files before proposing fields or code. Do not assume the data shape.

## Researcher decisions

The researcher must decide or approve:

- the substantive theory and honest contribution;
- whether the study supports descriptive, associational, or causal conclusions and, for a causal study, the identification strategy and assumptions;
- target population, sampling frame, inclusion and exclusion rules, temporal and jurisdictional scope;
- constructs, operationalizations, primary and secondary outcomes, comparisons, estimands, and hypotheses;
- treatment of opinions, parties' assertions, dissents, duplicate documents, missingness, and ambiguous cases;
- error tolerances, validation targets, correction for multiple comparisons, and which hypotheses and analyses must be fully specified and preregistered before outcomes are examined rather than treated as exploratory; and
- resource, privacy, model, and stopping constraints.

Present meaningful alternatives and consequences. Never make the choice merely because one option is easier to code.

Use standard methods terms consistently in questions and design files. Say
`unit of analysis`; `hypothesis`; `outcome` or `dependent variable` for a
measured response; and `quantity to estimate (estimand)` for the target
quantity. Do not add labels that blur these distinct concepts. Say `correction
for multiple comparisons`, and describe the intended conclusions and any
causal identification strategy in a sentence rather than naming an abstract
boundary.

Elicit these choices through the interactive Plan-Mode interview below. Do not
create an `assistant-default` for a material open Stage 04 choice before asking
the researcher. An express answer to use the recommendation is a researcher
decision; silence is not.

## Mode handoff

Follow `workflow/shared/execution-control.md` and create the native stage plan
before work. Always enter the host's read-only Plan Mode for this stage before
asking methods questions or writing a project file. Inspect the active
preemption and feasibility evidence, prior decisions and conditions, the
probe-exposure record, and the actual metadata or authorized representative
files. Tell the researcher what is already fixed and what remains open.

Use the native Plan-Mode question control: `request_user_input` on Codex and
`AskUserQuestion` on Claude Code. Ask one to three plain-language questions per
round, grouped coherently so that later rounds adapt to earlier answers. For
each question, state the controlling evidence, recommend one option, and give
two or three realistic alternatives and their consequences. Permit a free-form
answer and accept "go with the recommendations" or "don't know." Do not ask
what the existing record already answers. Do not silently fill an unanswered
researcher-owned choice. If "don't know" affects the architecture, explain the
tradeoff and ask whether to use the recommendation or pause; otherwise identify
the exact later boundary at which the choice must be resolved.

At minimum, cover every material open choice about:

1. the theory, honest contribution, whether the study supports descriptive,
   associational, or causal conclusions, the identification strategy and
   assumptions for any causal conclusion, and what plausible results would mean;
2. the target population, sampling frame, scope, units, inclusions, exclusions,
   duplicates, missing documents, and ambiguous cases;
3. constructs, operationalizations, outcomes or dependent variables,
   comparisons, quantities to estimate (estimands), hypotheses, and which
   hypotheses and analyses must be fully specified and preregistered before
   outcomes are examined rather than treated as exploratory;
4. clustering, missingness, power or precision, significance, effect-size
   benchmarks, correction for multiple comparisons, and subgroup analyses;
5. validation precision, double coding, adjudication, error tolerances, and
   measurement-error correction; and
6. resource, privacy, model, and stopping constraints.

Still in Plan Mode, synthesize the answers into a decision-complete proposed
design that links each hypothesis to its estimand, evidence, validation, and
analysis and lists every explicit deferral. Ask the researcher to review or
revise the plan. Do not write any project file, allocate a run, update state, or
append a ledger while in Plan Mode. If the host cannot enter Plan Mode or expose
its question control, make no project write and give the exact mode-switch or
resume handoff.

After the researcher accepts the plan and leaves Plan Mode, continue into execution in the same session.
Plan acceptance authorizes drafting the four
versioned design files; it does not approve the final `methods-plan-approval`
gate. Execute Stage 04, verify those files, and stop at that gate with the
researcher's choices, explicit deferrals, and any nonmaterial provisional
defaults visible for review. This stage is bounded: maintain the native plan
but do not start a goal.

## Work

1. Allocate a unique run ID only after execution begins. Capture all active input versions, hashes, accepted feasibility conditions, and each Plan-Mode question, recommendation, alternative, and researcher answer or explicit deferral. Record the decisions faithfully in the run manifest and append-only decision log; do not recast a preference as an assistant choice.
2. State the research question, theory, intended contribution, scope of inference, and what each plausible result would mean. Separate normative motivation from empirically testable claims.
3. Define the target population, sampling frame, document unit, coding unit, unit of analysis, clustering level, and denominator for every reported quantity. Explain how multiple documents, opinions, passages, or observations within a matter relate.
4. Specify inclusion, exclusion, deduplication, time, jurisdiction, language, version, and missing-document rules. Make the unit space enumerable before coding.
5. Define each construct independently of a model. Prefer document-observable, quote-backed components over holistic ratings. Map constructs to planned variables but reserve full edge-case rules for Stage 05.
6. Create hypotheses_vNNN.md with stable IDs, theory, variables, population, comparison, direction or explicitly nondirectional test, and decision rule. Label primary, secondary, falsification, and exploratory questions. Do not retrofit hypotheses to pilot or study outcomes.
7. Create `estimands_vNNN.csv` with stable IDs and columns for population, unit, outcome or measure, exposure or comparison, contrast, aggregation, denominator, clustering, missing-data treatment, error-correction requirement, linked hypothesis, inference procedure (how standard errors are calculated, clustering level, small-sample correction, confidence level, and whether the test is one- or two-sided, consistent with the hypotheses file), family of related hypotheses for correction of multiple comparisons, correction method, minimum detectable effect or target precision, assumed power and significance level, and effective sample size under the central projection of how many records remain after screening and coding.
8. Design sampling and power or precision analysis using the Stage 03 projections of how many records remain after each screening step, base rates, and preserved minimum-detectable-effect calculations. State which units were inspected during feasibility checks (from `probe_exposure_manifest.csv`), used for prompt development, used for the pilot, reserved for human validation, and used in the study; prevent overlap where independence is required, and exclude check-exposed and pilot units from the validation sample kept separate from development. Size the validation sample from the approved precision targets on per-class error rates, and include an independently double-coded reliability subsample (ordinarily ten to twenty percent) unless the researcher records a justification for a single-coder design. Fix the held-out validation sampling rule and random seed (the starting value used to reproduce sample selection) now, using a rule that could not be chosen after outcomes exist — for example, applying SHA-256 to the Stage 09 recorded list of frozen files.
9. Specify the LLM's bounded role: one supplied document or unit per call by default, codebook and schema as authority, quotation plus justification before label, uncertain escape, typed unusable rows, no outcome prediction, and no parametric-memory facts.
10. Specify deterministic mechanical checks: schema validation, exact or documented normalized quote matching, identifier and enum checks, coverage reconciliation, duplicate detection, retry limits, refusal tracking, and raw-output preservation.
11. Specify the human validation and blind adjudication design, performance metrics by class and subgroup, acceptance thresholds chosen before results, and the measurement-error correction or sensitivity analyses that use those estimates. Follow the protocol in workflow/shared/measurement-error-correction-guide.md when matching the correction to the estimand and validation design: its requirements are durable, but its named estimators are dated leads, so verify candidates against current literature retrieved during this project and present the tradeoffs; the choice remains the researcher's and must be feasible under the planned sample.
12. Specify analysis that produces the same results from the same inputs and rules: transformations, models or descriptive summaries, clustering, weighting, missingness, robustness, table and figure generation, and the distinction between preregistered and exploratory outputs. Define the correction for multiple comparisons concretely: group the hypothesis IDs that will be tested together into families; name the exact adjustment procedure — for example, a familywise-error-rate correction for the family of preregistered primary tests and a false-discovery-rate procedure for secondary families — or record the researcher's written justification for none; and enumerate planned heterogeneity and subgroup analyses, identifying which are preregistered and which are exploratory. Prespecify the treatment of records lost before analysis: a corpus gap-rate threshold and the planned response when it is exceeded, such as bounds or documented reweighting. Do not invent causal identification for a descriptive question.
13. Document data authorization dependencies, model and prompt logging, cost controls, progress ledgers, failure and stopping rules, scope-lock behavior, and amendment triggers.
14. Self-critique the design against selection, leakage, construct validity, dependence, subgroup error, outcome peeking, and researcher degrees of freedom. Present unresolved choices rather than silently resolving them.

## Artifacts

methods_plan_vNNN.md is the integrated design and must link stable hypothesis and estimand IDs. hypotheses_vNNN.md and estimands_vNNN.csv are machine-comparable specifications, not prose duplicates. sampling_validation_plan_vNNN.md must identify sample partitions (including the units inspected during feasibility), the exact held-out selection seed or derivation rule, target precision with the power and minimum-detectable-effect assumptions and formulas archived from Stage 03, the double-coded reliability subsample, adjudication, thresholds, and correction inputs. The record for the run identifies the exact source versions and decisions.

## Verification

- Trace every hypothesis to one or more estimands and every estimand to observable variables, a denominator, and an analysis.
- Confirm that population, frame, document unit, coding unit, and analysis unit are distinct where necessary and never used interchangeably.
- Confirm that feasibility-probe, prompt-development, pilot, held-out validation, and study sets cannot leak into one another contrary to the plan, and that the held-out seed or derivation rule is fixed.
- Confirm that validation thresholds, precision targets, minimum detectable effects, corrections for multiple comparisons, per-estimand inference procedures, and other correction methods are prespecified and feasible under the Stage 03 budget.
- Confirm that every unresolved substantive choice is visible and no study outcome informed the design without disclosure.
- Confirm that every material open methods choice was put to the researcher in Plan Mode, every answer or explicit deferral is traceable to the resulting files, and accepting the host plan was not recorded as approval of the final methods gate.
- Compare the artifacts with accepted preemption and feasibility conditions and route any material divergence upstream.

## State transition

Do not alter state during Plan Mode. At execution start, set current_stage to 04-methods-design and status to running, append the run, and preserve all prior versions. After verification, activate the new design artifacts, set status to awaiting_approval, mark methods-plan-approval pending, and enumerate unresolved decisions.

Only explicit approval advances the workflow. Append the approval and exact artifact versions to DECISIONS.md, mark the gate approved, and set current_stage to 05-codebook-and-schema and status to ready. A rejected design remains here for a versioned revision. A changed contribution or infeasible resource demand routes to Stage 02 or 03.

## Next-stage handoff

After approval, list the active methods, hypothesis, estimand, and sampling-plan versions. Provide the exact next task: enter Plan Mode for 05-codebook-and-schema, translate only the approved constructs into RA-usable definitions and a closed schema and unit space, and stop for codebook-schema approval.
