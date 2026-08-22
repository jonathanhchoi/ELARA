---
stage_id: "06-data-authorization"
title: "Authorize the data route"
paper_steps: ["2"]
core: true
interaction_profile: "normal"
long_running: false
goal_condition: null
prerequisites: ["05-codebook-and-schema"]
required_inputs: ["project/PROJECT_STATE.md", "project/PROJECT_CHARTER_vNNN.md", "project/ACCESS_MODEL_SNAPSHOT_vNNN.md", "project/artifacts/codebook_vNNN.md", "project/artifacts/coding_schema_vNNN.json", "project/artifacts/unit_space_vNNN.csv", "corpus source and governing terms"]
declared_outputs: ["project/artifacts/data_authorization_record_vNNN.md", "project/artifacts/data_handling_plan_vNNN.md", "project/artifacts/authorization_evidence_manifest_vNNN.csv", "project/runs/<run_id>/run_manifest.json", "project/PROJECT_STATE.md", "project/DECISIONS.md", "project/RUN_LEDGER.md", "project/DEVIATIONS.md"]
human_gate: "data-authorization"
next_stage: "07-adversarial-review"
failure_routes: ["03-feasibility-audit", "04-methods-design", "05-codebook-and-schema", "06-data-authorization"]
---

## Objective

Establish and record the exact lawful, contractual, ethical, institutional, and technical basis for every planned data action and model exposure. No corpus text may be sent to a hosted model until the researcher explicitly approves this record for the named data, source, purpose, platform, model route, and safeguards.

## Prerequisite checks

1. Read AGENTS.md and PROJECT_STATE.md, validate the approved codebook-schema package, and load the precise unit space, planned fields, model-visible inputs, outputs, and storage locations.
2. Identify every data class and action: discovery, download, scraping or API access, local storage, transformation, hosted-model upload, sub-agent access, human sharing, publication, and archival.
3. Check DEVIATIONS.md and the run history for any prior data exposure, including the Stage 05 model-exposure enumeration in its run manifest and the Stage 03 probe-exposure manifest. If text was exposed before authorization outside the recorded pre-gate sources, stop, record the event without deleting evidence, and ask the researcher how institutional or legal review should proceed.
4. Retrieve current official terms, license text, repository policies, provider data-use documentation, and institutional records. A feasibility-stage summary or remembered rule is not sufficient.
5. If governing material is behind a login, belongs to the researcher's institution, or requires legal or IRB interpretation, ask the researcher to supply the controlling text or determination. Do not guess.

## Researcher decisions

The researcher, with their institution or counsel where appropriate, must:

- confirm the authority to obtain and use each corpus and any restrictions on automated access;
- determine whether hosted-model processing is permitted by licenses, terms, confidentiality duties, protective orders, consent, data-use agreements, or other obligations;
- supply or confirm any IRB, exempt, not-human-subjects, privacy, security, or institutional determination;
- choose the approved provider, account tier, model, region, retention or training settings, sub-agent route, and local-versus-hosted processing;
- approve minimization, redaction, access control, retention, publication, and destruction rules; and
- accept, modify, or deny the authorization.

The agent assembles evidence and identifies issues; it does not give a binding legal opinion or sign for the researcher.

## Mode handoff

Follow `workflow/shared/execution-control.md`: create the native stage plan and
keep its authority, route, evidence, and gate items current. Run in normal
interactive mode, not Plan or Goal. This stage depends on short, explicit
confirmations and documents that only the researcher may possess. Inspect and
summarize public governing materials, then stop for any missing authority. Never
interpret silence, prior data access, technical capability, or a public-facing
webpage as authorization.

## Work

1. Allocate a run ID and create a matrix of every data source, data class, planned action, recipient or processor, output, and governing instrument.
2. For claimed public-domain or open-data routes, retrieve the authoritative source and exact scope. Distinguish underlying government text from vendor-added headnotes, annotations, metadata, OCR, images, or compilations. Do not assume all state or local government material, court-platform content, or freely downloadable material is public domain.
3. For licensed data, record the license edition and date, account or institutional basis, permitted users and purposes, automation and bulk-download rules, third-party or hosted-model clauses, derivative-output rights, redistribution and replication limits, retention, and termination obligations. If the text is unavailable, mark authorization unresolved.
4. For confidential, privileged, sealed, personally identifiable, human-subjects, or otherwise restricted data, record the controlling agreement or institutional determination, consent and purpose limits, security classification, approved environment, access list, minimization, de-identification, incident response, retention, and publication rules. Do not copy sensitive evidence into an unnecessarily broad artifact; use a secure reference and hash when appropriate.
5. Verify current official provider terms for the exact account and execution route where possible: API versus consumer product, enterprise controls, training use, abuse monitoring, retention, region, file persistence, subprocessors, and deletion. Distinguish public documentation from account-specific promises the researcher reports.
6. Compare the proposed codebook and schema with data minimization. Remove fields only through a versioned Stage 05 revision; do not collect convenient but unnecessary text. Identify any values that require local redaction, local-only computation, a different provider, or aggregation before model exposure.
7. Draft data_handling_plan_vNNN.md with source-to-output data flow, approved environments, least-privilege access, secrets handling, encryption where required, logging without sensitive payloads, raw and derived storage, backup, retention and destruction, sharing, and incident escalation. Never place credentials in an artifact.
8. Build authorization_evidence_manifest_vNNN.csv with evidence ID, source, authority, title, effective date, retrieved URL or secure reference, access date, hash where available, relevant section, short supporting excerpt or paraphrase, verified status, and unresolved question.
9. Draft data_authorization_record_vNNN.md as a bounded permission statement: exact corpus and version, source, authorized acts, project purpose, approved users and tools, provider/model/account route, prohibited acts, required controls, publication and replication limits, expiration or recheck date, evidence IDs, and unresolved risks.
10. Present the record to the researcher. Require an explicit approve, approve with listed conditions, deny, or obtain further review response. Quote the decision in DECISIONS.md; do not manufacture a signature or institutional determination.

## Artifacts

The authorization record is limited to the named corpus, model route, purpose, and project and is saved as a specific version; it does not transfer to another use. The handling plan states how to carry out those limits. The evidence list distinguishes official material the agent verified, material the researcher supplied, and questions of authority that remain unresolved. Sensitive governing records may remain in an approved secure location, identified by a value that verifies the file has not changed, rather than being copied into the repository.

## Verification

- Trace every planned data action and model-visible field to an authorization basis and handling control.
- Reopen every public evidence URL and confirm dates, route, and account distinctions are current; flag recheck dates for changeable terms.
- Confirm that public-domain claims exclude proprietary enhancements and that licensed and confidential routes include hosted-model and replication rights.
- Confirm that the record contains no credentials or unnecessary sensitive text and that the handling plan matches actual available controls.
- Confirm every unresolved authority remains a blocker and no downstream execution occurred.
- Ask the researcher to verify that the record matches their institution, license, and account, and preserve the exact response.

## State transition

At execution start, set current_stage to 06-data-authorization and status to running and append the run. Missing license, institutional, provider, or confidentiality authority changes status to waiting_for_user and lists each required determination; prior approvals remain untouched.

After artifacts verify, set status to awaiting_approval and mark data-authorization pending. Only an explicit approval scoped to the listed versions marks the gate approved and advances current_stage to 07-adversarial-review with status ready. A denial blocks all corpus processing and routes to a lawful redesign in Stage 03, 04, or 05. A conditional approval records each condition as an active constraint. A later change to corpus, source, platform, model route, purpose, or exposed fields invalidates this approval and returns here.

## Next-stage handoff

After approval, report the exact authorized corpus, model route, active evidence and handling versions, conditions, and recheck date. Provide the exact next task: enter Plan Mode for 07-adversarial-review, arrange independent critiques of the approved design and codebook, and do not treat data authorization as approval of the research design.
