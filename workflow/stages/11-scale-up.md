---
stage_id: "11-scale-up"
title: "Run resumable, verified full-corpus coding"
paper_steps: ["3"]
core: true
interaction_profile: "execute"
long_running: true
goal_condition: "Run Stage 11 exactly as specified until every unit in the active corpus has one terminal reconciled disposition under the frozen instrument, every attempt and raw output is preserved, schema and evidence checks pass, no material queue item is unresolved, and PROJECT_STATE.md is ready for Stage 12, or until an ELARA section 11 stop condition or recorded failure route is surfaced; never change the frozen rules or code units in the parent context."
prerequisites: ["10-corpus-acquisition"]
required_inputs: ["project/PROJECT_STATE.md", "project/artifacts/frozen_artifact_manifest_vNNN.csv", "project/artifacts/methods_plan_vNNN.md", "project/artifacts/codebook_vNNN.md", "project/artifacts/coding_schema_vNNN.json", "project/artifacts/coding_prompt_vNNN.md", "project/artifacts/pilot_acceptance_vNNN.md", "project/corpus/corpus_vNNN/", "project/artifacts/corpus_manifest_vNNN.csv", "project/artifacts/provenance_manifest_vNNN.csv", "project/artifacts/corpus_gap_register_vNNN.csv"]
declared_outputs: ["project/artifacts/coding_dataset_vNNN.jsonl", "project/artifacts/coding_ledger_vNNN.csv", "project/artifacts/schema_validation_vNNN.csv", "project/artifacts/quote_verification_vNNN.csv", "project/artifacts/coding_revision_queue_vNNN.csv", "project/artifacts/scale_up_report_vNNN.md", "project/runs/<run_id>/prompts/", "project/runs/<run_id>/raw_model_outputs/", "project/runs/<run_id>/unit_attempts.jsonl", "project/runs/<run_id>/failure_decisions.jsonl", "project/runs/<run_id>/batch_checks/", "project/runs/<run_id>/run_manifest.json", "project/PROJECT_STATE.md", "project/DECISIONS.md", "project/RUN_LEDGER.md", "project/DEVIATIONS.md"]
human_gate: null
next_stage: "12-interpretive-verification"
failure_routes: ["05-codebook-and-schema", "06-data-authorization", "08-pilot", "09-freeze-and-preregister", "10-corpus-acquisition", "11-scale-up"]
---

## Objective

Apply the exact frozen coding instructions to the authorized corpus in resumable, auditable batches. Produce one independently generated raw result per listed coding unit, check it against the required output format and quoted source text, preserve every failed attempt, and make the final ledger add up to the acquisition count. A coding unit may contain one document or several related documents, as fixed by the approved codebook and the complete list of units eligible for coding.

## Prerequisite checks

Read `AGENTS.md` and route this stage from `project/PROJECT_STATE.md` before doing any work; the standing rules and exact active versions control every check below.

1. Resolve all inputs to the exact active versions and verify them against the Stage 09 hashes. Confirm that the Stage 10 corpus manifests and files pass their recorded integrity checks and that no material acquisition deviation remains open.
2. Confirm that pilot acceptance covers the active model or agent route, model identifier, prompt, codebook, schema, sampling settings, context strategy, retry policy, quote-matching rule, and failure statuses. Do not silently substitute a newer model or provider default.
3. Reconfirm authorization for the actual model endpoint, subagent environment, logging, and storage path. Restricted text may not cross an unapproved boundary.
4. Dry-run the frozen orchestration, parser, schema validator, quote verifier, and checkpoint logic on the accepted pilot fixtures. Inspect their outputs. If a prerequisite fails, make no writes and leave state unchanged.

## Researcher decisions

The researcher decides any change to the instrument, model route, exclusion rule, retry ceiling, quote rule, or resource budget, and whether a systematic failure requires revision and repiloting. During a run, edge cases go to the revision queue. The agent must not reinterpret the codebook, hand-repair JSON, change a label to pass validation, omit a hard unit, or treat a failed request as a negative observation. The researcher also chooses — at Stage 00, confirmable at the Stage 08 interview, and changeable later as a recorded decision — whether individual unit failures during this run are decided by the assistant under the frozen rules and reported in one complete list at the end (`failure_handling`: `autonomous`, the default) or presented for the researcher's decision at the checkpoint where they are found (`interactive`). Neither choice changes the spending limit, the authorization rules, the frozen instrument, or the stop for widespread failure.

## Mode handoff

Follow `workflow/shared/execution-control.md` and create the native stage plan
before work. This is a long-running execution stage: the `goal_condition`
recorded in the settings at the top of this file must be the active goal before
execution begins. If it is not
active, provide `/goal <goal_condition>` and stop. Do not run the scale-up in
Plan Mode. The parent keeps the goal and plan current while the host orchestrator
runs coding waves under `workflow/shared/observation-fanout.md`: Codex spawns the
kit's `elr_worker` sub-agents in bounded waves; Claude Code launches the saved
`elr-observation-fanout` workflow until nothing is pending. If the orchestrator
is unavailable, launch the same restricted worker type one assignment per call
and record the fallback; never code units serially in the parent's context.

## Work

1. Allocate a unique run ID and output versions, record exact input hashes and every model and sampling setting including provider defaults, and append a ledger start. Resume only from the durable unit ledger, never from recollection or a progress estimate.
2. Create one self-contained assignment per coding unit under `workflow/shared/observation-fanout.md` (`python scripts/unit_fanout.py prepare`), then run the fan-out through the host's orchestrator as that contract directs — in Claude Code the saved `elr-observation-fanout` workflow, launched by the assistant; in Codex the kit's `elr_worker` sub-agents in bounded waves (`$elr-code-observations` and `/elr-code-observations` name this same route). Give each request a fresh model context containing only the frozen system instructions, codebook, prompt, schema, that unit's metadata, and that unit's source text or approved excerpt. Never pack multiple coding units into one prompt; a coding unit may contain several related documents only where the approved codebook and unit-space manifest define it that way. Require every worker to pass its return envelope on standard input to `python scripts/unit_fanout.py submit`; workers do not write canonical return paths directly.
3. Parallelize only assignments that write separate prompt, response, and attempt files. Merge results, update shared ledgers, and modify shared scripts serially. Do not claim that work continues after the executing process has stopped.
4. Before parsing, archive the exact rendered prompt or prompt hash, raw provider response, request and response identifiers, model identifier, route, timestamp, parameters, token and cost fields when available, finish status, and error. A retry is a new linked attempt; it never overwrites the failed one. If the provider-reported model version changes mid-run, stop at the next checkpoint with status waiting_for_user and record a deviation: validation metrics estimated at Stage 13 transport to coded units only within one model version, so coding under a changed version requires a researcher decision.
5. Validate every response against the frozen JSON schema. On failure, apply only the accepted retry policy and preserve all attempts. Never repair a substantive value by hand. If the retry policy is exhausted, emit the approved typed failure row. Disposition each failed, invalid, or exhausted unit per the recorded `failure_handling` preference (`workflow/shared/guardrails.md` §11): when it is absent or `autonomous`, decide under these frozen rules, append one judgment row to the run's `failure_decisions.jsonl` — unit and attempt, what happened, the disposition, who decided, a one-line rationale, timestamp — and continue the run; when it is `interactive`, stop at the batch or validation checkpoint that detects the failures, present every pending failure in one message with a recommended disposition and operational content only, and record each answer in the same log before continuing. Only the parent appends the log, serially. In either mode the complete failure digest — every unit-level failure and its recorded judgment — is presented at the end of the run and again at the next gate; an autonomous run also appends one `assistant-default` decision linking to the log.
6. Mechanically match every required supporting quotation to the authorized source using the frozen normalization rule. A real quotation must also be associated with the correct unit. For an approved no-quote or multiple-passage record, mechanically validate the source identifiers and locators, then leave the substantive support question for Stage 12. Evidence failures return for a new coding attempt under the accepted policy, not manual replacement.
7. Enforce evidence-first field order, enumerated values, exact unit IDs, and the codebook's `uncertain` and edge-case rules. Unreadable, wrong-document, refused, not-found, unauthorized, and otherwise unusable units receive explicit audit rows rather than disappearing from the denominator.
8. Work in the accepted batch size. After each batch, write unit attempts, build schema and evidence check records, append exact ledger counts, inspect sampled source-to-output links, and checkpoint the run manifest. Accumulate token and cost totals per batch — when provider cost fields are unobservable, fall back to token counts times the price sheet archived at Stage 03 — and compare cumulative spend, plus a linear per-unit projection to completion, against the approved budget ceiling at every checkpoint; stop with status waiting_for_user when the projection exceeds the ceiling or costs are unobservable for a material fraction of requests. Checkpoint and interim reports expose operational metrics only — coverage, failure types, retries, cost, and schema and evidence pass rates — never outcome distributions or label frequencies of substantive variables, so that no stop, extend, or repair decision can respond to favorable or unfavorable results mid-run. Stop on a systematic or cascading failure in either failure-handling mode: the run-level stopping rule fixed with the accepted pilot configuration is met (by default, failures or invalid returns exceeding the accepted tolerance within a batch or cumulatively, the same typed failure status recurring across consecutive units, or repeated infrastructure failure of a wave), or the failures share one cause that puts many units at risk; set `waiting_for_user` and preserve the run.
9. Append unanticipated situations to `coding_revision_queue_vNNN.csv` with the unit, passage, attempted rule application, and why the frozen codebook was insufficient. Do not resolve the issue inside the active run. A material instrument change routes through Stage 05, Stage 08, and Stage 09 and creates a new run version.
10. Build `coding_dataset_vNNN.jsonl` deterministically from passing terminal attempts plus explicit audit rows. Preserve supersession links; never erase an earlier code or attempt.
11. At completion, run a fresh reconciliation and incident review. Verify all counts from files, not worker summaries, and report exactly what is complete, failed, unresolved, and not running.

## Artifacts

`coding_dataset_vNNN.jsonl` is the machine-readable result, preserved unchanged, with one accounting record per listed unit and evidence-backed observations. `coding_ledger_vNNN.csv` links units to every attempt and final status. The output-format and evidence files record mechanical checks at the observation level. The revision queue records problems with the frozen rules without resolving them. `scale_up_report_vNNN.md` reports expected counts at each processing step, model and settings, dates, cumulative cost against the approved budget ceiling, runtime, batch incidents, retries, failure statuses, coverage, and open queue items, and presents the complete failure digest: every unit-level failure with its recorded decision, who made it, and why, drawn from `failure_decisions.jsonl` in the run directory (the judgment log the parent appends during the run; a clean run reports zero failure decisions). Run directories contain the exact prompts, raw responses, checks, and record needed to audit or resume the run.

## Verification

- Confirm each acquired or otherwise rostered unit has exactly one active terminal status and that all terminal counts reconcile to the Stage 10 denominator. Where Python is available, run scripts/validate_run.py and archive its output; otherwise perform and archive the equivalent manual reconciliation.
- Confirm cumulative spend stayed within the approved ceiling or a recorded researcher decision authorized the overage, and that no checkpoint or interim report exposed substantive outcome distributions mid-run.
- Confirm the provider-reported model version was constant across the run, or every version change stopped the run for a recorded researcher decision.
- Confirm each successful active response passes the exact schema; each quotation required by the codebook matches the correct immutable source; every approved no-quote or multiple-passage record has valid source locators; and every check row links to a preserved raw attempt.
- Confirm prompts, codebook, schema, model identifier, route, and settings match the frozen manifest for every request. Explain any provider field that could not be observed.
- Confirm retries are linked and additive, audit rows are not treated as negative codes, duplicate active observations are absent, and superseded results remain preserved.
- Confirm every unit-level failure, invalid return, and exhausted retry has exactly one judgment row in the run's `failure_decisions.jsonl`, the report's failure digest matches that log exactly, and the recorded `failure_handling` preference was followed: an autonomous run has its one linking `assistant-default` decision, an interactive run records the researcher's answer on each row, and any mid-run instruction outside the frozen rules was routed as a change or deviation rather than applied.
- Sample the complete chain from unit roster to source to prompt to raw response to parsed record to check result. Confirm no parallel worker edited a shared artifact.
- Confirm revision-queue issues and cascade incidents are disclosed and no prior input, run, response, correction, or ledger entry was overwritten.

## State transition

Set `current_stage` to `11-scale-up` and `status` to `running` only after checks pass. An interruption with valid checkpoints keeps this stage current and records exact completed and outstanding units for resumption. An authorization problem sets `waiting_for_user` and routes to Stage 06. A systematic data problem routes to Stage 10; an instrument problem routes through Stage 05, Stage 08, and Stage 09. Preserve the failed run.

After all verification passes and no material queue item remains unresolved, activate the coding dataset, ledger, check files, queue, report, and run manifest; set `current_stage` to `12-interpretive-verification`; and set `status` to `ready`. Mechanical evidence compliance alone is not permission to report substantive results.

## Next-stage handoff

Tell the researcher the exact denominator and terminal counts, observation count, schema and evidence pass counts, retries, unresolved items, active dataset and run versions, model settings, and whether anything is still running, and present the complete failure digest — every document or unit that failed during the run, the decision recorded for it, who made that decision, and why — so nothing is discovered later by surprise. Then provide the exact next task: run `12-interpretive-verification` as an independent audit of whether each evidence record supports its code; do not correct findings inside the audit.
