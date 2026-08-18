---
stage_id: "09-freeze-and-preregister"
title: "Freeze and preregister the study"
paper_steps: ["2"]
core: true
interaction_profile: "plan_then_execute"
long_running: false
goal_condition: null
prerequisites: ["08-pilot"]
required_inputs: ["project/PROJECT_STATE.md", "project/artifacts/design_freeze_vNNN.md", "project/artifacts/data_authorization_record_vNNN.md", "project/artifacts/pilot_acceptance_vNNN.md", "active methods, hypotheses, estimands, sampling plan, codebook, schema, unit space, and prompt"]
declared_outputs: ["project/artifacts/frozen_artifact_manifest_vNNN.csv", "project/artifacts/preregistration_vNNN.md", "project/artifacts/preregistration_vNNN.pdf", "project/artifacts/preregistration_record_vNNN.md", "project/artifacts/amendment_policy_vNNN.md", "project/code/frozen_analysis_vNNN/", "project/runs/<run_id>/rendered_pages/", "project/runs/<run_id>/run_manifest.json", "project/PROJECT_STATE.md", "project/DECISIONS.md", "project/RUN_LEDGER.md", "project/DEVIATIONS.md"]
human_gate: "preregistration-confirmation"
next_stage: "10-corpus-acquisition"
failure_routes: ["04-methods-design", "05-codebook-and-schema", "06-data-authorization", "07-adversarial-review", "08-pilot", "09-freeze-and-preregister"]
---

## Objective

Freeze the complete result-generating specification by exact version and hash, create a clean result-free preregistration in source and inspected PDF form, obtain the researcher's approval before external action, and record the completed registration before any full-corpus acquisition, coding, or outcome analysis.

## Prerequisite checks

1. Read AGENTS.md and PROJECT_STATE.md, validate explicit design-freeze, data-authorization, and pilot-acceptance approvals, and load the exact active versions named in those records.
2. Confirm that every fatal or major pilot issue is resolved in an accepted clean rerun and every deferred issue is disclosed.
3. Confirm that full-corpus coding and study-outcome analysis have not begun. If outcomes have been inspected, stop and require a transparent exploratory or retrospective-registration decision rather than pretending the design is prospective.
4. Distinguish pilot information legitimately used to refine the instrument from held-out or study outcomes. List all pilot units, observations seen, and design changes.
5. Confirm the researcher-selected registry, required fields, access or embargo choice, and who will perform the external submission. Do not assume authority to post.
6. Confirm the render toolchain for the chosen preregistration route before execution: verify the exact render command (for example, pandoc with a PDF engine) on a one-page fixture. If no toolchain is available, use the documented fallback — submit the verified Markdown source through the registry's web form, archive rendered-page screenshots and extracted text as the visual-QA evidence, and record the SHA-256 of the registered source file in the registration record in place of a PDF hash. For a non-programmer, the fallback is a first-class route, not a failure.

## Researcher decisions

The researcher must approve:

- the final question, theory, hypotheses, estimands, units, codebook, schema, sampling, validation, correction, analysis, and robustness specification;
- the confirmatory and exploratory boundary and disclosure of pilot-informed choices;
- the registry, title, authors, license, public or embargo status, and any sensitive attachments;
- the amendment threshold and how deviations will be reported; and
- the exact preregistration PDF before submission, followed by the external registration record.

External submission, creation of a public record, or acceptance of registry terms is never inferred from a request to draft.

## Mode handoff

Follow `workflow/shared/execution-control.md` and create the native stage plan
before work. Plan first, read-only. Audit the proposed frozen package, crosswalk
the preregistration sections to active artifacts, identify unresolved choices,
choose the PDF and registry workflow, and define amendment rules; do not write
any project file, hash into a manifest, render a PDF, update state, or contact a
registry until the plan is complete. Then continue into execution in the same session, without waiting, unless a stop condition in
`workflow/shared/guardrails.md` §11 holds; only then enter Plan Mode, stop, and
give the exact execution handoff. Create and verify the frozen manifest,
preregistration source and PDF, and amendment policy, then stop at the
preregistration gate before external submission. An unresolved choice in what
is to be frozen is never decided provisionally, and a later explicit instruction
is required for any external submission. This stage is bounded: maintain the
native plan but do not start a goal.

## Work

1. Allocate a run ID only after execution begins and record all approved input versions, hashes, pilot run, model and platform snapshot, and registry plan.
2. Build frozen_artifact_manifest_vNNN.csv with one row per frozen artifact: role, path, version, SHA-256 hash, byte size, creation or approval time, originating run, approval IDs, and downstream use. Include charter scope, preemption and feasibility conditions, methods, hypotheses, estimands, sampling and validation plan, codebook, schema, schema examples, unit space, coding prompt, authorization and handling plan, adversarial freeze, accepted pilot, and required software or prompt components.
3. Verify every hash from disk and every cross-reference. Versioned artifacts remain immutable. PROJECT_STATE.md points downstream stages to this manifest, not to a filename search or latest modification time.
4. Draft preregistration_vNNN.md by instantiating workflow/templates/preregistration_template.md and completing every section: title and authorship placeholders; research question and contribution; theory and hypotheses with stable IDs; target population, frame, units, inclusion and exclusion, and fixed denominator; corpus sources and authorization limits; sampling and partitions, including the held-out validation seed or derivation rule and the probe- and pilot-unit exclusions; power or precision analysis, with the minimum detectable effect or target precision for each primary estimand and the base-rate and funnel assumptions behind them; variables and codebook/schema versions; model and prompt route and reproducibility limits; pilot procedure and everything learned from it; coding, retries, failures, quote and schema checks; held-out human validation, blinding, adjudication, the double-coded reliability subsample, subgroup metrics, and acceptance thresholds; estimands, per-estimand inference procedures, and deterministic analysis, referencing the frozen analysis code by path and hash; measurement-error correction and sensitivity analyses; missingness, the multiplicity policy with its family definitions and exact correction procedures, robustness, stopping rules, and the attrition threshold and treatment; confirmatory versus exploratory boundary; and deviations and amendments.
5. Describe hypotheses honestly without reporting observed study results or presenting pilot-informed expectations as untouched priors. The registration freezes tests and decision rules; it need not assert a favored empirical outcome.
6. Crosswalk every hypothesis and estimand to frozen artifacts and executable analysis requirements. Quote the unit-space row count and hash, planned sample partitions, the held-out validation seed or derivation rule, validation targets, and pilot exclusions exactly.
7. Draft and dry-run executable analysis code for every confirmatory hypothesis and estimand under project/code/frozen_analysis_vNNN/, exercised only against accepted pilot outputs or synthetic fixtures conforming to the frozen schema — no study outcomes exist yet, and none may be created for this test. A parameter that cannot be fixed before data may remain open only if it is enumerated with an outcome-blind rule for setting it; validation quantities estimated at Stage 13, such as the confusion structure and inclusion probabilities, are data inputs rather than open choices. Add each script's path and SHA-256 to the frozen manifest. Prose plans never fully determine code, and every residual choice made after outcomes exist is a forking path; freezing runnable code closes it.
8. Create amendment_policy_vNNN.md. Material changes include the question, contribution, hypotheses, estimands, population, frame, units, inclusion rules, corpus or data route, codebook meaning, schema semantics, sampling, validation threshold, correction, model/prompt strategy, or primary analysis. They require an explained versioned amendment before affected work and rerouting through the relevant stage approvals. Non-substantive implementation fixes are logged with evidence and never used to change results silently.
9. Render preregistration_vNNN.pdf from the source with a reproducible command and embedded metadata where appropriate, or follow the approved no-toolchain fallback from prerequisite check 6. Inspect every rendered page for clipping, missing characters, broken tables, blank pages, unresolved placeholders, bad links, and illegible text. Extract text back from the PDF and compare section presence and key IDs with the source.
10. Present the verified PDF (or fallback package), manifest, disclosed pilot use, registry plan, and any unresolved placeholders to the researcher. Do not submit, upload, publish, accept terms, or create a DOI or timestamp until explicitly authorized.
11. After the researcher approves the exact PDF and completes the registration or separately authorizes an in-scope submission, verify the resulting registry page or receipt. Create preregistration_record_vNNN.md with registry, registration ID or DOI, canonical URL, registered timestamp and timezone, registered file hash, visibility or embargo, submitter, receipt path or hash, and any discrepancy from the approved package. Never invent a completed registration.

## Artifacts

The manifest, source, PDF, amendment policy, frozen analysis code, and completed registration record form the freeze package. rendered_pages/ is visual-QA evidence. Before external registration, the registration record may not exist and the stage remains at its gate. After registration, no frozen artifact is edited; corrections create a new version and, when material, an external amendment linked to the original.

## Verification

- Recompute all manifest hashes and confirm paths, versions, approval IDs, and cross-references resolve to one internally consistent package. Run scripts/verify_freeze.py where Python is available; otherwise perform and archive the manual hash comparison.
- Confirm hypothesis, estimand, variable, schema, and unit IDs match across the preregistration and frozen artifacts and that the unit count, hash, and held-out seed or derivation rule are exact.
- Execute the frozen analysis code end to end against the fixtures and confirm it runs, and confirm every enumerated open parameter carries an outcome-blind rule.
- Search source and extracted PDF text for unresolved placeholders, results language, hidden outcome values, inconsistent versions, and omitted pilot disclosures.
- Inspect every rendered PDF page and confirm the reproducible render command and tool versions are in the run manifest.
- Before transition, verify the registry record live or from an authentic researcher-supplied receipt and match the registered file hash to the approved PDF.
- Confirm no corpus acquisition, scale-up, or outcome analysis occurred between freeze review and registration.

## State transition

Do not alter state during Plan Mode. At execution start, set current_stage to 09-freeze-and-preregister and status to running and append the run. After the source, PDF, manifest, and amendment policy verify, activate them, set status to awaiting_approval, mark preregistration-confirmation pending, and list PDF approval, registry submission, and registration evidence as outstanding inputs.

Only after explicit PDF approval and verified external registration create and activate preregistration_record_vNNN.md, append the decision and identifiers to DECISIONS.md, mark the gate approved, and set current_stage to 10-corpus-acquisition and status to ready. A rejected draft remains here for a new version. A substantive design change routes through Stages 04–08 as applicable and requires a new freeze; a changed data route also returns to Stage 06.

## Next-stage handoff

Report the registration URL or identifier, timestamp, registered PDF hash, frozen manifest version, unit-space count and hash, and amendment rules. Provide the exact next task: execute 10-corpus-acquisition against only the registered unit space and authorized sources, treating any material corpus deviation as an amendment rather than silently changing the denominator.
