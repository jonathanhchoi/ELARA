---
stage_id: "11-scale-up"
title: "Run resumable, verified full-corpus coding"
paper_steps: ["3"]
core: true
interaction_profile: "execute"
long_running: true
prerequisites: ["10-corpus-acquisition"]
required_inputs: ["project/PROJECT_STATE.md", "project/artifacts/frozen_artifact_manifest_vNNN.csv", "project/artifacts/methods_plan_vNNN.md", "project/artifacts/codebook_vNNN.md", "project/artifacts/coding_schema_vNNN.json", "project/artifacts/coding_prompt_vNNN.md", "project/artifacts/pilot_acceptance_vNNN.md", "project/corpus/corpus_vNNN/", "project/artifacts/corpus_manifest_vNNN.csv", "project/artifacts/provenance_manifest_vNNN.csv", "project/artifacts/corpus_gap_register_vNNN.csv"]
declared_outputs: ["project/artifacts/coding_dataset_vNNN.jsonl", "project/artifacts/coding_ledger_vNNN.csv", "project/artifacts/schema_validation_vNNN.csv", "project/artifacts/quote_verification_vNNN.csv", "project/artifacts/coding_revision_queue_vNNN.csv", "project/artifacts/scale_up_report_vNNN.md", "project/runs/<run_id>/prompts/", "project/runs/<run_id>/raw_model_outputs/", "project/runs/<run_id>/unit_attempts.jsonl", "project/runs/<run_id>/batch_checks/", "project/runs/<run_id>/run_manifest.json", "project/PROJECT_STATE.md", "project/DECISIONS.md", "project/RUN_LEDGER.md", "project/DEVIATIONS.md"]
human_gate: null
next_stage: "12-interpretive-verification"
failure_routes: ["05-codebook-and-schema", "06-data-authorization", "08-pilot", "09-freeze-and-preregister", "10-corpus-acquisition", "11-scale-up"]
---

## Objective

Apply the exact frozen coding instrument to the authorized corpus in resumable, auditable batches. Produce one independently generated, raw, schema-checked, quote-checked result per rostered coding unit, preserve every failed attempt, and reconcile the final ledger to the acquisition denominator. A coding unit may contain one document or several related documents, as fixed by the approved codebook and unit-space manifest.

## Prerequisite checks

Read `AGENTS.md` and route this stage from `project/PROJECT_STATE.md` before doing any work; the standing rules and exact active versions control every check below.

1. Resolve all inputs to the exact active versions and verify them against the Stage 09 hashes. Confirm that the Stage 10 corpus manifests and files pass their recorded integrity checks and that no material acquisition deviation remains open.
2. Confirm that pilot acceptance covers the active model or agent route, model identifier, prompt, codebook, schema, sampling settings, context strategy, retry policy, quote-matching rule, and failure statuses. Do not silently substitute a newer model or provider default.
3. Reconfirm authorization for the actual model endpoint, subagent environment, logging, and storage path. Restricted text may not cross an unapproved boundary.
4. Dry-run the frozen orchestration, parser, schema validator, quote verifier, and checkpoint logic on the accepted pilot fixtures. Inspect their outputs. If a prerequisite fails, make no writes and leave state unchanged.

## Researcher decisions

The researcher decides any change to the instrument, model route, exclusion rule, retry ceiling, quote rule, or resource budget, and whether a systematic failure requires revision and repiloting. During a run, edge cases go to the revision queue. The agent must not reinterpret the codebook, hand-repair JSON, change a label to pass validation, omit a hard unit, or treat a failed request as a negative observation.

## Mode handoff

This is a long-running execution stage. In Codex, use `/goal` with this objective: **Code the complete active corpus under the frozen Stage 09 instrument, one unit per fresh model context, checkpoint every attempt, preserve raw outputs, enforce schema and evidence checks, and finish only when the exact ledger reconciles.** In Claude Code, invoke `/elr-code-observations` and the saved dynamic workflow on the frozen manifest. If the adapter is unavailable, use normal approved execution with frequent durable checkpoints. Do not run the scale-up in Plan Mode.

## Work

1. Allocate a unique run ID and output versions, record exact input hashes and every model and sampling setting including provider defaults, and append a ledger start. Resume only from the durable unit ledger, never from recollection or a progress estimate.
2. Create one self-contained assignment per coding unit under `workflow/shared/observation-fanout.md`. Invoke `$elr-code-observations` in Codex or `/elr-code-observations` and its saved workflow in Claude Code. Give each request a fresh model context containing only the frozen system instructions, codebook, prompt, schema, that unit's metadata, and that unit's source text or approved excerpt. Never pack multiple coding units into one prompt; a coding unit may contain several related documents only where the approved codebook and unit-space manifest define it that way. Require every worker to pass its return envelope on standard input to `python scripts/unit_fanout.py submit`; workers do not write canonical return paths directly.
3. Parallelize only assignments that write separate prompt, response, and attempt files. Merge results, update shared ledgers, and modify shared scripts serially. Do not claim that work continues after the executing process has stopped.
4. Before parsing, archive the exact rendered prompt or prompt hash, raw provider response, request and response identifiers, model identifier, route, timestamp, parameters, token and cost fields when available, finish status, and error. A retry is a new linked attempt; it never overwrites the failed one. If the provider-reported model version changes mid-run, stop at the next checkpoint with status waiting_for_user and record a deviation: validation metrics estimated at Stage 13 transport to coded units only within one model version, so coding under a changed version requires a researcher decision.
5. Validate every response against the frozen JSON schema. On failure, apply only the accepted retry policy and preserve all attempts. Never repair a substantive value by hand. If the retry policy is exhausted, emit the approved typed failure row.
6. Mechanically match every required supporting quotation to the authorized source using the frozen normalization rule. A real quotation must also be associated with the correct unit. For an approved no-quote or multiple-passage record, mechanically validate the source identifiers and locators, then leave the substantive support question for Stage 12. Evidence failures return for a new coding attempt under the accepted policy, not manual replacement.
7. Enforce evidence-first field order, enumerated values, exact unit IDs, and the codebook's `uncertain` and edge-case rules. Unreadable, wrong-document, refused, not-found, unauthorized, and otherwise unusable units receive explicit audit rows rather than disappearing from the denominator.
8. Work in the accepted batch size. After each batch, write unit attempts, build schema and evidence check records, append exact ledger counts, inspect sampled source-to-output links, and checkpoint the run manifest. Accumulate token and cost totals per batch — when provider cost fields are unobservable, fall back to token counts times the price sheet archived at Stage 03 — and compare cumulative spend, plus a linear per-unit projection to completion, against the approved budget ceiling at every checkpoint; stop with status waiting_for_user when the projection exceeds the ceiling or costs are unobservable for a material fraction of requests. Checkpoint and interim reports expose operational metrics only — coverage, failure types, retries, cost, and schema and evidence pass rates — never outcome distributions or label frequencies of substantive variables, so that no stop, extend, or repair decision can respond to favorable or unfavorable results mid-run. Stop on a systematic or cascading failure.
9. Append unanticipated situations to `coding_revision_queue_vNNN.csv` with the unit, passage, attempted rule application, and why the frozen codebook was insufficient. Do not resolve the issue inside the active run. A material instrument change routes through Stage 05, Stage 08, and Stage 09 and creates a new run version.
10. Build `coding_dataset_vNNN.jsonl` deterministically from passing terminal attempts plus explicit audit rows. Preserve supersession links; never erase an earlier code or attempt.
11. At completion, run a fresh reconciliation and incident review. Verify all counts from files, not worker summaries, and report exactly what is complete, failed, unresolved, and not running.

## Artifacts

`coding_dataset_vNNN.jsonl` is the immutable machine-readable result with one roster-accounting record per unit and evidence-backed observations. `coding_ledger_vNNN.csv` links units to every attempt and terminal status. The schema and evidence files record mechanical checks at observation level. The revision queue records frozen-rule problems without resolving them. `scale_up_report_vNNN.md` reports the funnel, model and settings, dates, cumulative cost against the approved budget ceiling, runtime, batch incidents, retries, failure statuses, coverage, and open queue items. Run directories contain the exact prompts, raw responses, checks, and manifest needed to audit or resume the run.

## Verification

- Confirm each acquired or otherwise rostered unit has exactly one active terminal status and that all terminal counts reconcile to the Stage 10 denominator. Where Python is available, run scripts/validate_run.py and archive its output; otherwise perform and archive the equivalent manual reconciliation.
- Confirm cumulative spend stayed within the approved ceiling or a recorded researcher decision authorized the overage, and that no checkpoint or interim report exposed substantive outcome distributions mid-run.
- Confirm the provider-reported model version was constant across the run, or every version change stopped the run for a recorded researcher decision.
- Confirm each successful active response passes the exact schema; each quotation required by the codebook matches the correct immutable source; every approved no-quote or multiple-passage record has valid source locators; and every check row links to a preserved raw attempt.
- Confirm prompts, codebook, schema, model identifier, route, and settings match the frozen manifest for every request. Explain any provider field that could not be observed.
- Confirm retries are linked and additive, audit rows are not treated as negative codes, duplicate active observations are absent, and superseded results remain preserved.
- Sample the complete chain from unit roster to source to prompt to raw response to parsed record to check result. Confirm no parallel worker edited a shared artifact.
- Confirm revision-queue issues and cascade incidents are disclosed and no prior input, run, response, correction, or ledger entry was overwritten.

## State transition

Set `current_stage` to `11-scale-up` and `status` to `running` only after checks pass. An interruption with valid checkpoints keeps this stage current and records exact completed and outstanding units for resumption. An authorization problem sets `waiting_for_user` and routes to Stage 06. A systematic data problem routes to Stage 10; an instrument problem routes through Stage 05, Stage 08, and Stage 09. Preserve the failed run.

After all verification passes and no material queue item remains unresolved, activate the coding dataset, ledger, check files, queue, report, and run manifest; set `current_stage` to `12-interpretive-verification`; and set `status` to `ready`. Mechanical evidence compliance alone is not permission to report substantive results.

## Next-stage handoff

Tell the researcher the exact denominator and terminal counts, observation count, schema and evidence pass counts, retries, unresolved items, active dataset and run versions, model settings, and whether anything is still running. Then provide the exact next task: run `12-interpretive-verification` as an independent audit of whether each evidence record supports its code; do not correct findings inside the audit.
