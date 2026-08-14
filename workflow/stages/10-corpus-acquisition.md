---
stage_id: "10-corpus-acquisition"
title: "Acquire and audit the frozen corpus"
paper_steps: ["3"]
core: true
interaction_profile: "execute"
long_running: true
prerequisites: ["09-freeze-and-preregister"]
required_inputs: ["project/PROJECT_STATE.md", "project/artifacts/frozen_artifact_manifest_vNNN.csv", "project/artifacts/preregistration_record_vNNN.md", "project/artifacts/amendment_policy_vNNN.md", "project/artifacts/data_authorization_record_vNNN.md", "project/artifacts/methods_plan_vNNN.md", "project/artifacts/hypotheses_vNNN.md", "project/artifacts/estimands_vNNN.csv", "project/artifacts/sampling_validation_plan_vNNN.md", "project/artifacts/codebook_vNNN.md", "project/artifacts/coding_schema_vNNN.json", "project/artifacts/unit_space_vNNN.csv", "project/artifacts/coding_prompt_vNNN.md", "project/artifacts/pilot_acceptance_vNNN.md"]
declared_outputs: ["project/corpus/corpus_vNNN/", "project/artifacts/corpus_manifest_vNNN.csv", "project/artifacts/provenance_manifest_vNNN.csv", "project/artifacts/corpus_gap_register_vNNN.csv", "project/artifacts/corpus_acquisition_report_vNNN.md", "project/runs/<run_id>/search_log.jsonl", "project/runs/<run_id>/fetch_log.jsonl", "project/runs/<run_id>/integrity_checks.json", "project/runs/<run_id>/run_manifest.json", "project/PROJECT_STATE.md", "project/DECISIONS.md", "project/RUN_LEDGER.md", "project/DEVIATIONS.md"]
human_gate: "material-corpus-deviation"
next_stage: "11-scale-up"
failure_routes: ["05-codebook-and-schema", "06-data-authorization", "08-pilot", "09-freeze-and-preregister", "10-corpus-acquisition"]
---

## Objective

Acquire the full frozen unit space through authorized routes and produce an immutable, source-level corpus with complete provenance, integrity checks, explicit denominators, and typed gaps. Do not silently change the population, source hierarchy, period, exclusions, or evidence policy to make acquisition easier.

## Prerequisite checks

Read `AGENTS.md` and route this stage from `project/PROJECT_STATE.md` before doing any work; the standing rules and exact active versions control every check below.

1. Read state and resolve every `vNNN` placeholder to the exact active version recorded there. Confirm that Stage 09 is approved and that every file and hash in the frozen-artifact manifest still matches. Never select an input merely because it is the newest file.
2. Confirm that the data-authorization record covers every proposed source, access route, storage location, retrieval method, OCR service, and model or tool that may receive text. A license, confidentiality, privilege, sealed-record, personal-data, IRB, ethics, or terms-of-service uncertainty stops work.
3. Validate that the frozen unit-space manifest has stable unique unit IDs, a closed denominator, and the metadata needed to locate each unit. Confirm that the methods and codebook state the governing source-priority, conflict, duplicate, version, exclusion, and gap rules.
4. Confirm that the pilot acceptance applies to the active methods, codebook, schema, prompt, unit space, and acquisition route. A changed dependency invalidates the acceptance.
5. Inspect storage capacity, required credentials, robots or rate constraints, and expected costs without exposing credentials in any artifact. If any prerequisite is missing, make no writes and leave project state unchanged.

## Researcher decisions

The researcher alone decides whether to change the unit space, accept a substitute source, alter an inclusion rule, tolerate a material OCR or coverage limitation, incur nontrivial cost, or amend the preregistration. The agent may apply frozen rules and report options; it may not redefine the corpus, infer a missing value, bypass access controls, or deem a deviation immaterial when the approved documents do not already answer that question.

## Mode handoff

This is a long-running execution stage. In Codex or current Claude Code, `/goal` may be used with this objective: **Acquire every authorized unit in the frozen Stage 09 unit space, preserve immutable sources and complete provenance, verify corpus integrity and coverage, and stop at any authorization issue or material-corpus-deviation gate.** If Goal mode is unavailable, use the tool's normal approved execution mode with frequent state and ledger checkpoints. Do not execute acquisition in Plan Mode.

## Work

1. After all checks pass, allocate a unique timestamped run ID and the next corpus and artifact versions. Record exact input paths and hashes in the run manifest, set the stage to running, and append a ledger start. Never alter `project/inputs/` or a prior corpus version.
2. Copy or fetch one frozen unit at a time into `corpus_vNNN`. For a web-assembled corpus, use one unit per research assignment and follow the frozen source hierarchy and evidence policy. Never code from search snippets or model memory.
3. For every retrieval attempt, append a fetch-log row containing unit ID, source ID and type, URL or stable locator, access time in UTC, request result, content type, bytes, local path, checksum, license or redistribution restriction, and superseded source if any. Preserve failed attempts as well as successes.
4. Preserve the retrieved bytes before OCR, normalization, or extraction. Store derived text beside, not over, the source and record the transformation tool, version, settings, input hash, and output hash. Do not outsource restricted text to an unapproved service.
5. Apply the frozen duplicate and version rules. Record duplicate clusters and the deterministic retained-unit decision; never delete a rostered unit. Confirm that each fetched document is the intended authority, date, jurisdiction, and version rather than a syllabus, summary, docket page, or unrelated file.
6. Run file-open, encoding, extraction, OCR, length, language, truncation, and corruption checks appropriate to the approved methods. Keep the check results at unit level. Do not invent a quality threshold; use the approved one or request a researcher decision.
7. Give every rostered unit exactly one terminal acquisition status, including acquired, not found after documented search, inaccessible, unauthorized, unusable, duplicate under the frozen rule, not applicable, or unresolved conflict. For every non-acquired status, state what was attempted, what was found, and why it failed.
8. Build the corpus manifest and provenance manifest deterministically from the unit roster and logs. Counts must reconcile to the frozen denominator. Identify coverage by every preregistered subgroup and distinguish “searched and found nothing” from “not searched.”
9. If a source conflict cannot be resolved by the frozen rule, or acquisition would materially change scope, coverage, measurement, authorization, or the preregistered analysis, append a deviation proposal without changing the corpus definition and stop at the gate. Route authorization changes to Stage 06, design or unit-space changes through Stage 05 and the dependent approval stages, and preregistration amendments to Stage 09.
10. Have a fresh reviewer sample source identities, checksums, transformations, duplicate decisions, gap records, and manifest-to-disk links. Preserve the review result and correct only by appending a superseding record or creating a new artifact version.

## Artifacts

`corpus_vNNN/` contains immutable retrieved sources and separately identified derived text. `corpus_manifest_vNNN.csv` accounts for every frozen unit and its terminal status. `provenance_manifest_vNNN.csv` traces each usable file from source through transformations and hashes. `corpus_gap_register_vNNN.csv` records typed gaps, searches, conflicts, and proposed resolutions. `corpus_acquisition_report_vNNN.md` states the denominator, acquisition funnel, coverage by approved subgroups, integrity incidents, restrictions, costs, and all deviations. The run logs and manifest preserve each attempt and the exact frozen inputs.

## Verification

- Confirm every frozen unit ID appears exactly once in the corpus manifest and that terminal-status counts sum to the frozen denominator. Where Python is available, run scripts/validate_run.py and archive its machine-readable output in the run directory; otherwise perform and archive the equivalent manual reconciliation.
- Recompute file checksums, verify every manifest path exists, and confirm derived files link to immutable source hashes and recorded tools. Verify the frozen-manifest hashes with scripts/verify_freeze.py where Python is available.
- Sample source identity against authoritative metadata; inspect OCR and corruption checks; and confirm duplicate, version, exclusion, and conflict decisions follow the frozen rules.
- Confirm every acquired item has provenance and every missing or unusable item has a typed gap with documented attempts. Search logs must support any “not found” claim.
- Confirm the active authorization covers the actual routes used and that redistribution restrictions are recorded for the replication package.
- Confirm no material deviation was implemented without an approved amendment and no prior input, source, artifact, or ledger row was overwritten.

## State transition

Set `current_stage` to `10-corpus-acquisition` and `status` to `running` only after prerequisite checks pass and execution starts. On an authorization problem or material deviation, preserve completed work, append the issue to the ledgers, set `status` to `awaiting_approval` or `waiting_for_user`, and record the exact failure route; do not activate the proposed corpus.

After all verification passes, activate the exact corpus, manifest, provenance, gap-register, and report versions; append final attempted, acquired, gap, duplicate, and unusable counts; set `current_stage` to `11-scale-up`; and set `status` to `ready`. Approval of a deviation does not erase it: append the decision, create superseding versions, and rerun every invalidated approval stage.

## Next-stage handoff

Tell the researcher the frozen denominator, acquired and non-acquired counts, coverage by approved subgroups, authorization restrictions, active versions, and any residual limitations. If no gate remains, provide the exact next task: run `11-scale-up` with the active frozen prompt, codebook, schema, unit space, and corpus; use one unit per model context; archive every raw response; and stop on any frozen-rule change.
