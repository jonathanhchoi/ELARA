---
stage_id: "03-feasibility-audit"
title: "Audit feasibility"
paper_steps: ["1"]
core: true
interaction_profile: "execute"
long_running: true
prerequisites: ["02-preemption-review"]
required_inputs: ["project/PROJECT_STATE.md", "project/artifacts/preemption_review_vNNN.md", "accepted project and preemption disposition", "candidate corpus locations"]
declared_outputs: ["project/artifacts/feasibility_audit_vNNN.md", "project/runs/<run_id>/probe_log.csv", "project/runs/<run_id>/probe_exposure_manifest.csv", "project/runs/<run_id>/funnel_model.csv", "project/runs/<run_id>/cost_model.csv", "project/runs/<run_id>/variable_verifiability.csv", "project/runs/<run_id>/probes/", "project/runs/<run_id>/run_manifest.json", "project/PROJECT_STATE.md", "project/DECISIONS.md", "project/RUN_LEDGER.md", "project/DEVIATIONS.md"]
human_gate: "feasibility-go-no-go"
next_stage: "04-methods-design"
failure_routes: ["01-conceive", "02-preemption-review", "03-feasibility-audit"]
---

## Objective

Try to kill the accepted project cheaply before resources are committed. Establish each feasibility fact with a current live probe, identify the single binding constraint, quantify the data funnel, validation burden, cost, and time, and return a go, go-with-modifications, or no-go recommendation for the researcher.

## Prerequisite checks

1. Read AGENTS.md and PROJECT_STATE.md, validate the approved preemption disposition, and load the exact selected question, claimed contribution, corpus, variables, method, and conditions from active artifacts and DECISIONS.md.
2. Confirm that the question has not materially shifted since Stage 02. A new question, population, corpus, or contribution must be rechecked for preemption.
3. Confirm live access to the proposed data source, current provider documentation and prices, and any APIs or repositories required for probes. Do not fill a failed probe from memory.
4. This is not data authorization. Inspect only public samples or metadata whose use is clearly permitted for this audit. Do not send licensed, confidential, restricted, or human-subjects text to any hosted model before Stage 06 approval.
5. Define in advance the cheapest probe likely to reveal a fatal flaw. Record planned limits so the audit does not become an unapproved corpus run.

## Researcher decisions

The researcher alone decides:

- whether both plausible result directions are sufficiently important;
- what target population and comparison the paper should speak to;
- whether a judgment-heavy construct should be decomposed, replaced, or abandoned;
- acceptable coverage gaps, selection risks, spending, time, and manual validation burden;
- whether a licensed, restricted, confidential, or human-subjects route is worth pursuing; and
- whether to accept go-with-modifications, return upstream, or stop.

Anything implicating terms, institutional rules, nontrivial spending, or risk is flagged, not resolved by the agent.

## Mode handoff

This is a long-running execution stage. Codex and current Claude Code may use /goal when available, with normal researcher-approved execution as the fallback. Use the objective: Execute Stage 03 adversarially, run and archive only authorized live probes, produce the declared feasibility artifacts, and stop at the feasibility-go-no-go gate. Do not proceed on a paper plan or perform this work in Plan Mode.

## Work

1. Allocate a run ID, register the active inputs and probe budget, and append a start row. Treat a well-evidenced no-go as a successful audit. Order the gates by expected cost-to-kill: the free analytic gates first, then the precommitted cheapest killing probe, then the spending gates.
2. Apply the task-type gate to every proposed LLM use. Classify it as estimation from supplied text or prediction. A prediction task fails absent a defensible target population, sampling procedure, and training-corpus leakage analysis; instructions to ignore learned knowledge are not a leakage control.
3. Apply the verifiability gate variable by variable. Ask whether a careful RA can determine the value from one supplied document, where possible by an exact quotation. State verification method and likely coder disagreements. Red-flag holistic evaluations, expert taxonomies, novel constructs defined by model output, and cross-document inference. Propose observable components, but reserve construct choices for the researcher.
4. Apply the either-way gate. Write the most defensible headline under each result direction and identify who would care. Flag an expected or null direction that cannot support a contribution.
5. Run the precommitted cheapest killing probe from prerequisite check 5. If it fails, do not keep spending merely to rescue the idea: skip the remaining probe-bearing gates, write the gate table, and recommend no-go. If it passes, test the next likely binding constraint within the approved probe budget.
6. Apply the data gate with live probes. Verify that the corpus exists, its authoritative source and access route, dates and jurisdictions covered, document formats, metadata fields, selection layers, known gaps, deduplication identifiers, OCR quality, API behavior, rate limits, and current terms or license status. Pull a small, authorized sample and confirm it contains the information proposed for coding. Preserve raw probe responses and typed failures. Reuse the Stage 02 smoke-screen probes rather than repeating them. Record every unit whose content is inspected or coded during any probe in probe_exposure_manifest.csv — unit or document identifier, hash where available, variables inspected or coded, and probe ID — so Stage 04 partitions and the Stage 13 held-out validation frame can quarantine those units.
7. Apply the base-rate and power gate. Estimate incidence from authorized marker counts or a transparently coded mini-sample, never intuition, and add every mini-sample unit to the probe-exposure manifest. Project the funnel from the raw universe through availability, eligibility, readability, coding success, and analysis inclusion. Give low, central, and high scenarios and identify assumptions. Then compute the minimum detectable effect for each planned primary comparison at a researcher-approved power and significance level — present 0.80 and 0.05 as defaults for explicit approval — under each funnel scenario, inflated for the anticipated misclassification error from the inference gate and for clustering or design effects. Archive the formula or script and its assumptions so Stage 04 and the preregistration can quote them. If the minimum detectable effect exceeds every effect size plausible against the closest literature, this gate fails: the design cannot answer its question, and the verdict should say so in plain language rather than deferring the discovery to analysis.
8. Budget human validation before scale-up. Specify a held-out design and size it from precision targets rather than a heuristic: for each key class, state the maximum acceptable confidence-interval half-width for the error rates the planned correction requires (present a default for researcher approval), derive the sample size from the base-rate scenarios, and treat a few hundred units as a floor, not a target. Budget independent double coding for a prespecified share of the sample — ordinarily ten to twenty percent — so human-to-human reliability can be measured at Stage 13. Carry the derived human-coding hours into the cost gate. Keep prompt-tuning examples separate from the held-out set.
9. Apply the cost and time gate from current evidence. Calculate documents times tokens times current prices at each funnel stage, including retries, orchestration, storage, human coding at the validation size derived above, and robustness. Compare plausible model tiers and a high-recall cheap-screen then precise-model design. Save formulas and price-sheet URLs with access dates; do not recall prices. When any candidate data route is licensed, restricted, confidential, or human-subjects, also estimate the authorization lead time — license negotiation, data-use agreements, IRB or ethics review — from current published evidence, include low, central, and high lead-time scenarios in the schedule range, and treat a lead time incompatible with the researcher's stated timeline as a binding constraint.
10. Apply the inference gate. For each important variable and estimand, explain how false positives, false negatives, subgroup error, missing documents, and selective refusals could bias the estimate. Name a planned measurement-error correction or sensitivity analysis and the validation quantities it requires, following the protocol in workflow/shared/measurement-error-correction-guide.md: reason from the estimand and validation design, then verify candidate methods against current literature retrieved live — the guide's named estimators are dated leads, not a closed menu. The choice remains the researcher's. Accuracy alone is not a pass.
11. Write a gate-by-gate table using pass, pass with conditions, or fail, with evidence IDs. Name one binding constraint, the probe result, the funnel, the minimum detectable effects, cost and schedule ranges, risks, unverified assumptions, and a verdict of go, go with modifications, or no-go. State exactly what evidence would change the verdict and report no confidence score.

## Artifacts

feasibility_audit_vNNN.md is the decision document. probe_log.csv must record probe ID, hypothesis, method, URL or local source, access time, authorization basis, exact result, raw artifact path, and interpretation. probe_exposure_manifest.csv lists every unit whose content was inspected or coded during the audit, so later stages can quarantine those units from held-out validation. funnel_model.csv and cost_model.csv must expose assumptions and formulas — including the minimum-detectable-effect and validation-precision calculations — rather than only totals. variable_verifiability.csv must cover every proposed variable. Preserve raw requests, responses, samples, screenshots where necessary, and typed gap records under probes/.

## Verification

- Reperform or independently inspect every fact that controls a gate; confirm each points to a dated live probe.
- Reconcile funnel denominators from raw universe through analyzable observations and ensure failures remain explicit rows.
- Recalculate cost scenarios from recorded current prices, token assumptions, retries, and human effort.
- Confirm no restricted text was exposed before authorization and that all terms, license, confidentiality, and human-subjects issues remain flagged for Stage 06.
- Confirm validation is held out, sized from the stated precision targets, and budgeted (including the double-coded reliability subsample) and that proposed error correction matches the anticipated error.
- Recompute the minimum-detectable-effect calculations from the archived formula and confirm the verdict reflects them.
- Confirm every unit inspected or coded during a probe appears in the probe-exposure manifest.
- Confirm the verdict follows the gate results, identifies the binding constraint, and contains every unverified assumption.

## State transition

At execution start, set current_stage to 03-feasibility-audit and status to running and append the run. If a live fact cannot be checked, set status to waiting_for_user, list the exact probe or access needed, and do not substitute an assumption.

After verification, activate the audit, set status to awaiting_approval, mark feasibility-go-no-go pending, and request an explicit go, go-with-modifications, no-go, or upstream-revision decision. On go, append accepted conditions to DECISIONS.md, mark approval, and set current_stage to 04-methods-design and status to ready. On modifications that change novelty, return to Stage 02; on a new idea, return to Stage 01. On no-go, record the stopping decision and leave the workflow waiting_for_user or superseded as directed; do not advance.

## Next-stage handoff

After an explicit go, name the active audit version, binding constraint, accepted conditions, and fixed resource limits. Provide the exact next task: enter Plan Mode for 04-methods-design, resolve the researcher-owned design choices, and do not write methods artifacts until the plan is approved for execution.
