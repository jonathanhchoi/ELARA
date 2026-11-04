---
stage_id: "08-pilot"
title: "Pilot the complete coding pipeline"
paper_steps: ["2"]
core: true
interaction_profile: "plan_then_execute"
long_running: true
goal_condition: "Run Stage 08 exactly as specified until the fixed pilot sample has terminal reconciled returns, every raw output and attempt is preserved, schema, quote, settings-review, and researcher-review artifacts pass validation, and PROJECT_STATE.md records the pilot-acceptance gate, or until an ELARA section 11 stop condition is recorded and surfaced; do not accept the pilot for the researcher."
prerequisites: ["07-adversarial-review"]
required_inputs: ["project/PROJECT_STATE.md", "project/artifacts/design_freeze_vNNN.md", "project/artifacts/methods_plan_vNNN.md", "project/artifacts/codebook_vNNN.md", "project/artifacts/coding_schema_vNNN.json", "project/artifacts/unit_space_vNNN.csv", "project/artifacts/coding_prompt_vNNN.md", "project/artifacts/data_authorization_record_vNNN.md"]
declared_outputs: ["project/artifacts/pilot_plan_vNNN.md", "project/artifacts/pilot_sample_vNNN.csv", "project/artifacts/pilot_report_vNNN.md", "project/artifacts/pilot_researcher_review_vNNN.csv", "project/artifacts/pilot_disagreements_vNNN.csv", "project/artifacts/pilot_revision_queue_vNNN.csv", "project/artifacts/pilot_acceptance_vNNN.md", "project/artifacts/coding_run_settings_vNNN.json", "project/runs/<run_id>/run_settings.json", "project/runs/<run_id>/assignments/", "project/runs/<run_id>/worker_returns/", "project/runs/<run_id>/normalized_outputs.jsonl", "project/runs/<run_id>/pilot_ledger.csv", "project/runs/<run_id>/schema_quote_compliance.csv", "project/runs/<run_id>/code_review.md", "project/runs/<run_id>/run_manifest.json", "project/PROJECT_STATE.md", "project/DECISIONS.md", "project/RUN_LEDGER.md", "project/DEVIATIONS.md"]
human_gate: "pilot-acceptance"
next_stage: "09-freeze-and-preregister"
failure_routes: ["04-methods-design", "05-codebook-and-schema", "06-data-authorization", "07-adversarial-review", "08-pilot"]
---

## Objective

Run the smallest complete version of the authorized pipeline, through the kit's runner, on a deliberately informative sample, inspect every observation, test mechanical compliance and software, expose codebook ambiguity and operational failures, and obtain explicit researcher acceptance before freezing and preregistering.

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

Every material pilot-configuration choice must be elicited through the
Plan-Mode interview below before execution. The agent may diagnose and
recommend; it cannot treat silence as agreement, self-certify accuracy, waive
failed thresholds, or accept the pilot.

## Mode handoff

Follow `workflow/shared/execution-control.md` and always enter the host's native
read-only Plan Mode before any Stage 08 project write, run allocation, code
build, coding-model call, state update, or ledger append. First inspect the
exact frozen design, codebook, schema, prompt, unit space, authorization record,
adversarial conditions, and recorded budget. Then use Codex
`request_user_input` or Claude Code `AskUserQuestion` for one to three adaptive
rounds that elicit the researcher's preferences about the pilot sample,
independent pre-coding, one-unit execution architecture, validation and
quotation checks, retries and stopping rules — including confirming or changing
the `failure_handling` preference recorded at Stage 00, which governs how the
Stage 11 full run handles individual unit failures, and the run-level stopping
rule Stage 11 will apply to widespread failure — success thresholds, researcher
review and disagreement handling, model route, and time and cost limits. For
each consequential choice, show the controlling evidence, put a reasoned
recommendation first, offer realistic alternatives and consequences, and
allow free-form answers, "go with your recommendations," and "I don't know."

Synthesize the answers into a reviewable pilot plan that fixes the sample,
thresholds, commands, validation checks, review workflow, retry and stopping
rules, and projected cost. Do not use a material provisional
`assistant-default` in place of asking, and do not write or execute while the
interview remains in Plan Mode. After the researcher accepts the plan, leave
Plan Mode and continue into execution in the same session unless a stop
condition in `workflow/shared/guardrails.md` §11 holds. Plan acceptance
authorizes only the described pilot execution; it does not accept the pilot or
waive any later gate. Stop if projected model-call cost exceeds the recorded
budget. Because this stage is long-running, the `goal_condition` recorded in
the settings at the top of this file is the completion contract. Use a covering authorized goal when present;
otherwise continue foreground execution with durable checkpoints.
Once assignments are fixed, the host coordinates the parallel sub-agent assignments under
`workflow/shared/observation-fanout.md`: Claude Code launches the saved
`elr-observation-fanout` workflow and Codex spawns the kit's `elr_worker`
sub-agents in a bounded rolling pool. The completion contract stays with the parent through serial
validation and reconciliation. Neither the plan, goal, nor mode switch accepts
the pilot.

## Work

1. Allocate a run ID after execution begins. Save pilot_plan_vNNN.md with exact frozen artifact hashes, authorized model route, sample, success criteria, architecture, commands, retry limits, and stop conditions.
2. Create pilot_sample_vNNN.csv with unit IDs, selection reason, source hashes, expected component, authorization status, independent-human-code status, and explicit exclusion from later held-out validation. When the researcher wants a reproducible draw rather than hand-picked units, `python scripts/coding_run.py sample` draws one from the settings' `sample` rule (strata, exclusions such as earlier pilots, and filters); record why any drawn unit is replaced. Preserve selection before outputs.
3. If the researcher will pre-code, provide a codebook-based template and keep their codes hidden from the model and pipeline author until raw model outputs are frozen. Never fabricate human labels or silently treat the researcher's later review as independent pre-coding.
4. Write the run settings, `coding_run_settings_vNNN.json`, under `workflow/templates/coding_run_settings.md`: the frozen prompt, codebook, and schema as inputs; the unit-list columns and what workers see of each source; the quotation rule; the retry rule; the run-level stopping rule; and the review and comparison fields. Do not write a driver, wrapper, launch script, or validator: `scripts/coding_run.py` draws reproducible samples, builds each worker's view of its source, prepares and seals the run, checks every return, and writes the ledgers, review sheet, and disagreement tables, with the same assignment format and checks Stage 11 uses. Code is needed only for a step the runner does not cover, such as parsing the corpus into one text file per document; keep it in `project/code/`, name that folder as `project_code`, and let each run record its commit. Run `prepare --dry-run`, then inspect a few assignments and source views, before preparing.
5. Prepare the run with `python scripts/coding_run.py prepare --settings <settings> --units <pilot sample> --run-dir project/runs/<run_id>`. Then repeat what its `next` step names until it says `close`: launch the block it shows under `workflow/shared/observation-fanout.md`, then `check --apply`. One unit is one worker; never drop or replace a difficult unit. Credentials never go in any file.
6. `submit` validates each return against the exact schema, identifiers, and enumerations; `check` verifies every quotation under the frozen rule (verbatim or the recorded normalization, the cited lines or offsets, and the right source) and lists what the retry rule allows. Retries use the fixed rule, never a reinterpreted codebook, and every attempt and invalid raw return is preserved. Express conditional requirements, such as a quotation required for a positive code, in the frozen schema so they are checked mechanically.
7. Run `close` to build `normalized_outputs.jsonl`, `pilot_ledger.csv`, `schema_quote_compliance.csv`, and the quotation results from validated returns only, with a receipt that reconciles every count to the fixed sample. Nothing in a raw return is edited; an unreadable unit stays in the counts with its reason.
8. Run `review` to produce pilot_researcher_review_vNNN.csv (with `--human-codes` when the researcher pre-coded, and `--blind` when the conditions should not be identifiable), and have the researcher review every observation in context and every uncertain, edge-case, and failure row. The sheet carries the blinded human code where available, the researcher's validity decision, the reason, and the adjudicator. Do not pressure the researcher to agree with the model.
9. Run `compare` to produce pilot_disagreements_vNNN.csv with every human-model and model-model mismatch and agreement statistics, and have the researcher classify each one as label disagreement, missed observation, unsupported quote, attribution error, unit error, ambiguity, or unusable source. Ask the model for a codebook-grounded justification only after the independent judgment is preserved.
10. Confirm from the close receipt and check files that schema, approved evidence path, allowed labels, required fields, unit coverage, duplicate observations, retry and refusal rules, version hashes, and raw-output completeness all reconcile to the fixed sample, with no silent gaps.
11. Give the settings file, any project code the run used, the frozen artifacts, and a sample of assignments and outputs to a fresh second model instance (per `workflow/shared/fresh-review.md`). It reports in code_review.md whether the settings implement the approved pilot plan (sources and views, quotation and retry rules, conditions, stopping rule) and any bugs, leakage, or fragile assumptions in the project code; it does not silently fix anything or recode observations. The kit's runner is tested in ELARA and is not reviewed per project.
12. Create pilot_revision_queue_vNNN.csv for every codebook ambiguity, schema defect, prompt problem, source issue, operational failure, and deferred adversarial test. Include severity, evidence, proposed upstream stage, and disposition. The active package remains frozen throughout this run.
13. Write pilot_report_vNNN.md with exact sample and completion counts, compliance results, disagreement patterns, diagnostic metrics with small-sample caveats, costs and timing, code-review findings, threshold results, and recommended accept, revise-and-rerun, or stop disposition. The pilot reports measurement quality only: schema and evidence compliance, coverage, disagreements, and diagnostics. Do not compute or report the substantive estimand, an outcome distribution over the pilot sample, or any outcome-exposure association before the Stage 09 freeze; log any accidental computation as a deviation and disclose it in the preregistration.
14. If a substantive revision is needed, do not change the package here. Route to Stage 04 or 05, recheck authorization in Stage 06 and design freeze in Stage 07, then run a fresh pilot with a new run ID. Acceptance requires a clean run under one fixed package.

## Artifacts

All run-level data are preserved unchanged under the unique run directory, and the run records the settings hash and the project code's commit. Raw model outputs are irreplaceable and must be saved before parsing. The researcher review, disagreement table, and revision queue are versioned diagnostic records; pilot units and tuning examples are permanently kept out of held-out validation. Create pilot_acceptance_vNNN.md only after the researcher acts on the gate; it records the accepted run, exact frozen versions including the run settings Stage 11 will reuse, the values used to verify that they have not changed, thresholds, known limitations, and deferred nonblocking items.

## Verification

- Reconcile every sample unit across sample, run ledger, raw output or typed failure, normalized output where valid, compliance table, and researcher review.
- Require all accepted substantive observations to pass schema and quotation checks; report exact numerator and denominator for every compliance measure.
- Confirm raw files are unchanged, normalized rows preserve provenance, retries use fixed rules, and no definition changed during the run.
- Confirm every observation and failure received researcher review and every disagreement has a disposition or remains explicitly unresolved.
- Confirm the fresh settings and project-code review ran and all fatal or major issues are fixed through a new run or block acceptance.
- Compare results with the predeclared thresholds without moving the thresholds after seeing performance.
- Confirm the pilot report contains no substantive estimand, outcome distribution, or outcome-exposure association computed on pilot data.
- Confirm the native Plan-Mode interview preceded every Stage 08 project write or model call, captured the researcher's material configuration choices, and fixed the sample and thresholds before any pilot outcome was observed.
- Confirm accepting the execution plan was not recorded as approval of the separate `pilot-acceptance` gate.

## State transition

Do not alter state in Plan Mode. At execution start, set current_stage to 08-pilot and status to running and append the run. Missing human review sets waiting_for_user; software or compliance failure sets failed; a revision requirement records the upstream failure route. Do not activate revised codebook artifacts from this stage.

After the report verifies, activate the pilot artifacts except the acceptance memo, set status to awaiting_approval, mark pilot-acceptance pending, and list every unresolved disagreement and threshold failure. On explicit acceptance, create pilot_acceptance_vNNN.md, append the decision and exact run and artifact hashes, mark the gate approved, activate the memo, and set current_stage to 09-freeze-and-preregister and status to ready. Rejection returns through the named upstream stages and requires a new pilot.

## Next-stage handoff

After acceptance, report exact completion and compliance counts, active pilot and frozen-package versions, and deferred limitations. Provide the exact next task: enter Plan Mode for 09-freeze-and-preregister, prepare a result-free preregistration and a list of the frozen files with the values used to verify that they have not changed, and stop before any external registration until the researcher approves it.
