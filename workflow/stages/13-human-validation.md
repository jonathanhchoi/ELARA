---
stage_id: "13-human-validation"
title: "Run blind human validation and adjudication"
paper_steps: ["4"]
core: true
interaction_profile: "plan_then_execute"
long_running: false
goal_condition: null
prerequisites: ["12-interpretive-verification"]
required_inputs: ["project/PROJECT_STATE.md", "project/artifacts/methods_plan_vNNN.md", "project/artifacts/hypotheses_vNNN.md", "project/artifacts/estimands_vNNN.csv", "project/artifacts/sampling_validation_plan_vNNN.md", "project/artifacts/preregistration_record_vNNN.md", "project/artifacts/codebook_vNNN.md", "project/artifacts/coding_schema_vNNN.json", "project/artifacts/coding_dataset_vNNN.jsonl", "project/artifacts/interpretive_audit_vNNN.jsonl", "project/artifacts/interpretive_audit_coverage_vNNN.csv", "project/artifacts/interpretive_verification_report_vNNN.md", "researcher-supplied blind human codes under project/inputs/human_validation/ when coding is complete"]
declared_outputs: ["project/artifacts/validation_plan_vNNN.md", "project/artifacts/held_out_sample_vNNN.csv", "project/artifacts/coder_pack_vNNN/", "project/artifacts/blind_review_interface_vNNN/", "project/artifacts/validation_crosswalk_vNNN.csv", "project/artifacts/blind_adjudication_queue_vNNN.csv", "project/artifacts/adjudicated_validation_data_vNNN.csv", "project/artifacts/validation_metrics_vNNN.json", "project/artifacts/human_validation_report_vNNN.md", "project/artifacts/human_validation_disposition_vNNN.md", "project/runs/<run_id>/run_manifest.json", "project/PROJECT_STATE.md", "project/DECISIONS.md", "project/RUN_LEDGER.md", "project/DEVIATIONS.md"]
human_gate: "validation-disposition"
next_stage: "14-analysis-and-correction"
failure_routes: ["05-codebook-and-schema", "08-pilot", "11-scale-up", "12-interpretive-verification", "13-human-validation"]
---

## Objective

Measure the active pipeline against genuinely independent human coding on the approved held-out sample, give the researcher a locally runnable blind adjudication interface, estimate the prespecified error and agreement metrics with the correct sampling design, and stop for the researcher's validation disposition. The agent must never adjudicate its own accuracy.

## Prerequisite checks

Read `AGENTS.md` and route this stage from `project/PROJECT_STATE.md` before doing any work; the standing rules and exact active versions control every check below.

1. Resolve exact active versions and confirm Stage 12 audited every active observation with an empty recoding queue. Verify that the validation design in the methods or preregistration specifies the sampling frame, held-out rule, inclusion probabilities, coder design — including the double-coded reliability subsample or the researcher's recorded justification for a single-coder design — matching unit, metrics, and any acceptance criteria.
2. Confirm that the proposed sample played no role in choosing the model, prompt, codebook, examples, pilot revisions, or production retry rules, and that it excludes every unit in the Stage 03 probe-exposure manifest and every pilot unit. If it did or does not, it is not held out and a new eligible frame is required.
3. Confirm that humans can lawfully view the source material and that their returned files can be stored locally. Do not send confidential human labels, adjudications, or a clean test set to a hosted model unless separately authorized.
4. Inspect actual dataset and human-code formats before planning the crosswalk or interface. If the approved design leaves a choice that could change the validation result or no longer fits the data, obtain a researcher decision before execution; do not invent a sample size, threshold, or metric.

## Researcher decisions

The researcher approves the sample and coder design, selects and instructs the human coders, resolves scope mismatches, personally performs or supervises blind adjudication, decides what counts as ground truth under the approved design, and renders the final pass, revise, or abandon disposition. The agent may randomize, package, match, calculate, and surface disagreements. It may not reveal which source produced a judgment during blind review, infer missing human codes, exclude inconvenient disagreements, move an acceptance threshold, or approve the pipeline.

## Mode handoff

Follow `workflow/shared/execution-control.md` and create the native stage plan
before work. Plan first, read-only. Inspect files and present a decision-complete
architecture covering sampling, blinding, coder packets, returned-file
contract, scope matching, interface behavior, adjudication, metrics,
uncertainty, and failure routes; do not write any project file until the plan is
complete. Then continue into execution in the same session, without waiting,
unless a stop condition in `workflow/shared/guardrails.md` §11 holds; only then
enter Plan Mode, stop, and give the exact execution handoff. Build and run the
approved held-out human-validation workflow, preserve blinding through
adjudication, compute the approved metrics, and stop at
`validation-disposition`. This stage is bounded: maintain the native plan but
do not start a goal.

## Work

1. After plan approval, allocate a unique run ID and output versions, persist the approved validation plan, record all active input hashes, set the stage running, and append a ledger start.
2. Draw the held-out sample deterministically from the approved eligible frame using the approved randomization method and the seed or derivation rule fixed at Stages 04 and 09. Record unit and observation inclusion probabilities, weights, replacement rules, and exclusions. Keep any origin or model-label columns out of coder-facing files.
3. Build a versioned coder pack containing the frozen instructions, codebook, source excerpts or documents, stable blind IDs, response schema, edge-case route, and return-file specification. Include only information the approved design permits; never include the pipeline's codes, confidence, justifications, or correctness claims.
4. Validate the coder pack against the sample and schema, then stop with `waiting_for_user` while the researcher distributes it and places returned files, unchanged, under `project/inputs/human_validation/`. Hash every returned input and preserve coder identities only to the degree the approved ethics and privacy plan permits.
5. On resume, run structural checks for duplicate IDs, impossible labels, missing assignments, coder overlap, and protocol deviations. Do not silently coerce substantive values. Record discrepancies and request corrected or expressly accepted inputs.
6. Construct the validation crosswalk at the unit specified in the plan. If human and pipeline tasks differed in scope, use the researcher-approved eligible target list before comparison. Preserve unmatched candidates from both sides; do not treat an unmatched observation as an error until comparability is established.
7. Build a local blind review interface. Randomize presentation order, display the relevant source context and competing observation without identifying whether it came from the model or a person, require a decision and rationale, support safe resume, and seal the provenance key until all adjudication decisions are final. Test the interface with synthetic fixtures and inspect the saved output.
8. Produce the adjudication queue. Set matched items aside only if the approved design authorizes that assumption. The researcher, not an agent, completes every required blind decision. Stop with `waiting_for_user`; do not unblind partial decisions or provide cues about likely origin.
9. After the researcher confirms adjudication is final, hash and freeze it, unblind deterministically, and build `adjudicated_validation_data_vNNN.csv`. Preserve the raw human and adjudication inputs; corrections append superseding records.
10. Calculate exactly the approved metrics. These must include per-variable chance-corrected human-to-human agreement (Krippendorff's alpha or Cohen's kappa) on the double-coded subsample — or, for an approved single-coder design, carry the recorded justification and a benchmark-noise limitation statement into the report and disposition memo — and may further include per-variable confusion matrices, accuracy, precision, recall or sensitivity and specificity, F1 with its averaging convention, false-positive and false-negative rates, relative discovery and omission errors, and sampling-weighted aggregate rates. Use the recorded inclusion probabilities and report uncertainty. Do not substitute headline accuracy for a prespecified rare-class metric. When the approved design is a comparative disagreement audit, state in the report and disposition memo that it reports which source prevails among disputed labels and does not detect shared errors or estimate absolute accuracy, precision, recall, or false-negative rates.
11. Compare the realized sample against the plan before the gate: per-class adjudicated counts and achieved confidence-interval widths for each prespecified metric versus the sampling plan's precision targets. Flag every class whose estimated error rates cannot support the approved Stage 14 correction, and surface those flags in the report so the researcher can extend the sample now rather than discover the incompatibility after the disposition is recorded.
12. Diagnose error types without changing the labels. Compare results to the prespecified criteria, where they exist, and explain what the validation sample can and cannot establish. Present the complete report and blind-review audit trail to the researcher for disposition.

## Artifacts

The validation plan records the approved design and criteria. The held-out sample preserves blind IDs, sampling probabilities, and source information in a restricted research copy. The coder pack contains only authorized blinded material. The local interface and adjudication queue make every required disagreement reviewable without origin cues. The crosswalk and adjudicated dataset preserve comparability and final ground truth. `validation_metrics_vNNN.json` is machine-readable and `human_validation_report_vNNN.md` reports design, coder protocol, deviations, error profiles, uncertainty, subgroup results, and limitations. The disposition memo records the researcher's explicit decision and the exact file versions it covers.

## Verification

- Confirm the sample was eligible and held out, the selection is reproducible from the recorded seed and frame, the seed matches the value or derivation rule fixed at Stages 04 and 09 (any mismatch is a material deviation), and inclusion probabilities and weights reproduce reported totals.
- Confirm realized per-class counts and interval widths were compared to the plan's precision targets and every shortfall is flagged in the report.
- Confirm coder-facing materials contain no model outputs or origin cues and that the provenance key stayed sealed until required adjudication was complete.
- Confirm every expected human assignment and every required adjudication has a terminal status; no missing or incomparable item was silently counted as agreement or error.
- Recompute crosswalks, confusion matrices, agreement, weighted metrics, and uncertainty from the adjudicated file and compare them to the machine-readable metrics and report.
- Confirm the local interface saves and resumes safely, operates without sending validation content to an unauthorized service, and was tested on fixtures.
- Confirm criteria came from approved artifacts or an explicit preregistered researcher decision, all deviations are disclosed, and no input or prior validation artifact was overwritten.

## State transition

The plan phase leaves all files and state unchanged. After the plan (and any approval a stop condition required) and execution start, set `current_stage` to `13-human-validation` and `status` to `running`. Use `waiting_for_user` while awaiting coder returns or completed blind adjudication, with the exact outstanding action recorded. Once metrics are verified, set `status` to `awaiting_approval` and mark `validation-disposition` pending.

Advance only after the researcher records a pass for the exact validation artifacts. Activate those versions, append the decision, set `current_stage` to `14-analysis-and-correction`, and set `status` to `ready`. A revise disposition preserves all evidence and routes the defect to Stage 05 or Stage 08, with new downstream versions through Stages 09–13. Data or matching defects route to Stages 11–12. An abandon disposition records the reason and sets `status` to `failed`; it is not relabeled as a pass.

## Next-stage handoff

Tell the researcher the held-out design, coder completion, adjudication count, prespecified metrics and uncertainty, subgroup results, leading error modes, criteria comparison, limitations, and exact active versions. After an explicit pass, provide the exact next task: plan `14-analysis-and-correction` against the actual validated data, keep every hypothesis separately runnable, and implement only the approved measurement-error correction.
