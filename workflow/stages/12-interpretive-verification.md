---
stage_id: "12-interpretive-verification"
title: "Independently verify interpretive support"
paper_steps: ["4"]
core: true
interaction_profile: "execute"
long_running: true
prerequisites: ["11-scale-up"]
required_inputs: ["project/PROJECT_STATE.md", "project/artifacts/codebook_vNNN.md", "project/artifacts/coding_schema_vNNN.json", "project/corpus/corpus_vNNN/", "project/artifacts/corpus_manifest_vNNN.csv", "project/artifacts/coding_dataset_vNNN.jsonl", "project/artifacts/coding_ledger_vNNN.csv", "project/artifacts/schema_validation_vNNN.csv", "project/artifacts/quote_verification_vNNN.csv", "project/runs/<run_id>/raw_model_outputs/"]
declared_outputs: ["project/artifacts/interpretive_audit_vNNN.jsonl", "project/artifacts/interpretive_audit_coverage_vNNN.csv", "project/artifacts/interpretive_recoding_queue_vNNN.csv", "project/artifacts/interpretive_verification_report_vNNN.md", "project/runs/<run_id>/prompts/", "project/runs/<run_id>/raw_model_outputs/", "project/runs/<run_id>/unit_attempts.jsonl", "project/runs/<run_id>/run_manifest.json", "project/PROJECT_STATE.md", "project/DECISIONS.md", "project/RUN_LEDGER.md", "project/DEVIATIONS.md"]
human_gate: null
next_stage: "13-human-validation"
failure_routes: ["05-codebook-and-schema", "08-pilot", "11-scale-up", "12-interpretive-verification"]
---

## Objective

Independently audit every coded observation to determine whether its evidence record, checked against the original source, supports the assigned label under the frozen codebook. Mechanical evidence checks establish that quotations or locators exist; this stage tests what the source supports. It reports findings and creates a targeted recoding queue but does not silently repair codes.

## Prerequisite checks

Read `AGENTS.md` and route this stage from `project/PROJECT_STATE.md` before doing any work; the standing rules and exact active versions control every check below.

1. Resolve the exact active corpus, codebook, schema, coding dataset, mechanical check files, and Stage 11 run. Confirm that their paths, hashes, counts, and supersession relationships reconcile.
2. Confirm that every observation to be audited has a stable observation ID, unit ID, label, justification, retrievable source, and exactly one evidence path allowed by the codebook. The path may be a verbatim quotation, multiple identified passages, or an approved no-quote record for an absence, relation, or synthesis. Mechanical failures must return to Stage 11 before interpretive review.
3. Confirm that the verifier is independent of the original coding context: use a fresh context and do not supply the original coder's hidden reasoning, confidence, or a prior verifier's conclusion. Confirm the verifier model, route, and settings were fixed in the approved methods plan or by a recorded researcher decision before this run began; do not choose the verifier after seeing coding results. Where authorization and cost permit, prefer a model family different from the Stage 11 coder, because a verifier sharing the coder's model family shares its systematic misreadings; when they do share a family, disclose that correlated-error limitation in the report and describe Stage 13 human validation as the only independent accuracy check.
4. Dry-run the audit parser and coverage builder on accepted examples and inspect output. If any prerequisite fails, make no writes and leave state unchanged.

## Researcher decisions

The researcher decides whether a recurring unsupported or ambiguous pattern reveals a codebook defect, whether any disputed interpretation needs expert review, and whether revisions require repiloting and a new frozen run. The verifier may apply the existing definition and explain its finding; it may not broaden the definition, relabel the observation, or choose a convenient interpretation to preserve the result.

## Mode handoff

This is a long-running audit stage. In Codex, `/goal` may be used with this objective: **Independently audit the interpretive support for every active coded observation, one audit unit per fresh context, preserve raw findings, create a complete targeted recoding queue, and make no coding corrections.** In Claude Code, invoke `/elr-code-observations` and the saved dynamic workflow on the frozen audit manifest. If the adapter is unavailable, use normal approved execution with durable checkpoints. Do not run this audit in Plan Mode.

## Work

1. Allocate a unique audit run ID and output versions, record exact input hashes and verifier settings, set the stage running, and append a ledger start.
2. Construct one audit assignment per active coded observation under `workflow/shared/observation-fanout.md`; this stage's assignment kind is `audit_observation`, not a document-level coding unit. Supply the frozen codebook definition, label, evidence record, one-sentence justification, and a deterministic route to inspect every cited location and the full immutable source. Use a fresh model context for each audit unit.
3. Ask only whether the documented evidence supports the label under the supplied definition. For a quotation, read the passage in context. For an approved no-quote or multiple-passage record, inspect the named sources and locations and decide whether the evidence search supports the claimed absence, relation, or synthesis. Require exactly one disposition—`supported`, `unsupported`, or `ambiguous`—plus concise reasoning and every source location inspected. The verifier audits; it does not generate a preferred replacement label.
4. Archive every exact prompt, raw response, model identifier, settings, timestamp, parse result, and retry as immutable run material. Parallel assignments may write separate files; shared ledgers and aggregates are updated serially.
5. Validate the audit response structure and its observation and source identifiers. A failed audit remains an explicit failed attempt and is retried only under the recorded policy; it is never assumed supported.
6. Build `interpretive_recoding_queue_vNNN.csv` from every unsupported, ambiguous, or failed audit, retaining the original unit and observation IDs, finding, reasoning, source locator, and required route. Do not modify `coding_dataset_vNNN.jsonl`.
7. Review patterns by variable, label, source type, period, batch, and coding attempt. A concentrated failure may indicate a cascade or instrument defect. Report the pattern and route it rather than changing the audit standard after seeing results.
8. Send queued observations to Stage 11 for fresh recoding under the same frozen instrument. If the instrument itself must change, route through Stage 05, Stage 08, and Stage 09. New codes receive new IDs and supersession links, after which this entire stage must audit the active set again.
9. Have a fresh reviewer (per `workflow/shared/fresh-review.md`) sample supported as well as flagged findings against full source context and confirm coverage construction. Preserve disagreements in the report.

## Artifacts

`interpretive_audit_vNNN.jsonl` contains one immutable finding per active observation and links it to the exact source, codebook, dataset, and raw audit attempt. `interpretive_audit_coverage_vNNN.csv` reconciles every active observation to a terminal audit status. `interpretive_recoding_queue_vNNN.csv` lists all findings requiring correction or expert disposition without changing the coding dataset. `interpretive_verification_report_vNNN.md` reports coverage, dispositions, patterns, fresh-review results, and routing decisions. The run directory preserves the exact prompts and raw verifier outputs.

## Verification

- Confirm every active coded observation appears exactly once in the coverage file and that status counts equal the active observation count.
- Confirm each finding used the correct immutable source context and active codebook definition and links to a preserved raw verifier attempt.
- Confirm the verifier was independent, one audit unit occupied each fresh context, and shared artifacts were edited serially.
- Confirm every unsupported, ambiguous, failed, or missing finding appears in the recoding queue and no audited label or source record was altered.
- Reopen a sample from each disposition and variable, including apparent supports, and compare every evidence path with the full original source.
- Confirm no prior artifact, raw output, audit result, correction, or ledger row was overwritten.

## State transition

Set `current_stage` to `12-interpretive-verification` and `status` to `running` only after checks pass. If the recoding queue is nonempty, activate the audit artifacts, record exact counts, set `status` to `failed`, and route targeted items to Stage 11 or instrument defects through Stage 05, Stage 08, and Stage 09. Preserve this audit version as evidence; never mark flagged observations verified by fiat.

Only after a rerun accounts for every active observation and the recoding queue is empty may the stage activate the clean audit version, set `current_stage` to `13-human-validation`, and set `status` to `ready`. Interpretive verification is not human validation and cannot satisfy the Stage 13 gate.

## Next-stage handoff

Tell the researcher the audited observation count, supported, unsupported, ambiguous, failed, and recoded counts; recurring patterns; active audit and dataset versions; and any routes taken. When the active audit has complete coverage and an empty queue, provide the exact next task: plan `13-human-validation` from the approved validation design, protect the held-out sample, and stop for blind human adjudication and the `validation-disposition` gate.
