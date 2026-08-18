---
stage_id: "07-adversarial-review"
title: "Adversarially review and freeze the design"
paper_steps: ["2"]
core: true
interaction_profile: "plan_then_execute"
long_running: true
prerequisites: ["06-data-authorization"]
required_inputs: ["project/PROJECT_STATE.md", "project/artifacts/methods_plan_vNNN.md", "project/artifacts/hypotheses_vNNN.md", "project/artifacts/estimands_vNNN.csv", "project/artifacts/sampling_validation_plan_vNNN.md", "project/artifacts/codebook_vNNN.md", "project/artifacts/coding_schema_vNNN.json", "project/artifacts/unit_space_vNNN.csv", "project/artifacts/coding_prompt_vNNN.md", "project/artifacts/data_authorization_record_vNNN.md"]
declared_outputs: ["project/runs/<run_id>/critiques/", "project/artifacts/adversarial_review_synthesis_vNNN.md", "project/artifacts/adversarial_change_matrix_vNNN.csv", "project/artifacts/methods_plan_vNNN.md", "project/artifacts/hypotheses_vNNN.md", "project/artifacts/estimands_vNNN.csv", "project/artifacts/sampling_validation_plan_vNNN.md", "project/artifacts/codebook_vNNN.md", "project/artifacts/coding_schema_vNNN.json", "project/artifacts/unit_space_vNNN.csv", "project/artifacts/coding_prompt_vNNN.md", "project/artifacts/schema_examples_vNNN.jsonl", "project/artifacts/design_freeze_vNNN.md", "project/runs/<run_id>/schema_validation_report.json", "project/runs/<run_id>/run_manifest.json", "project/PROJECT_STATE.md", "project/DECISIONS.md", "project/RUN_LEDGER.md", "project/DEVIATIONS.md"]
human_gate: "design-freeze"
next_stage: "08-pilot"
failure_routes: ["02-preemption-review", "03-feasibility-audit", "04-methods-design", "05-codebook-and-schema", "06-data-authorization", "07-adversarial-review"]
---

## Objective

Attack every important assumption and artifact with independent reviewers, respond transparently to the critiques, produce a clean internally consistent revision, and obtain the researcher's final design-and-codebook freeze for the pilot. Critics report; they do not silently repair shared files.

## Prerequisite checks

1. Read AGENTS.md and PROJECT_STATE.md, then confirm active approvals for methods, codebook-schema, and the exact data route. Load artifact versions and hashes rather than whichever filenames appear newest.
2. Confirm that all reviewers can be given the necessary artifacts without violating data authorization. This review should ordinarily use design materials and public or synthetic examples, not corpus text.
3. Identify all prior critique, unresolved issue, feasibility condition, authorization constraint, and preemption condition. A reviewer must be able to trace each one.
4. Confirm that no pilot or study-scale coding has begun. If it has, record the deviation and ask the researcher whether this review is retrospective.
5. Check that sub-agents or fresh independent sessions are available. Independent critics run as a research fan-out under `workflow/shared/observation-fanout.md` — one critic per brief, each a fresh `elr-research-worker` / `elr_research_worker` launched by the host's orchestrator (Claude Code: the saved `elr-research-fanout` workflow; Codex: the kit's sub-agents), each receiving the design and codebook and none receiving another critic's findings. If no orchestrator is available, use serial fresh-context reviews and preserve their separation.

## Researcher decisions

The researcher must decide:

- which critiques reveal substantive rather than merely stylistic problems;
- how to resolve contested constructs, legal classifications, scope, identification, and tradeoffs;
- whether to accept, reject with reasons, defer, or test each recommendation in the pilot;
- whether a change is material enough to rerun preemption, feasibility, authorization, or codebook design; and
- when the revised package is strong enough to freeze for the pilot.

No critic, synthesizer, or majority vote substitutes for this judgment.

## Mode handoff

Plan first, read-only. Design independent review assignments, attack surfaces, evidence requirements, non-overlapping file ownership, synthesis rules, and upstream invalidation tests; do not write any project file, create critiques, update artifacts, spawn editing work, allocate a run, or touch state until the plan is complete. Then continue into execution in the same session, without waiting, unless a stop condition in `workflow/shared/guardrails.md` §11 holds (a researcher-owned choice with no reasonable provisional default, a spend beyond the recorded budget, or a `checkpoints` preference of `plans` or `all`); only then enter Plan Mode, stop, and give the exact execution handoff. Because the review and revision cycle may be long-running, Codex and current Claude Code may use /goal when available, with normal researcher-approved execution as the fallback. The objective is: Execute Stage 07 with independent audit-only critics, produce a transparent response matrix and clean versioned artifact package, verify it, and stop at design-freeze.

## Work

1. Allocate a run ID and snapshot every active input version and hash. Create separate reviewer work areas under critiques/; only the synthesizing instance may write shared revised artifacts.
2. Commission independent critiques that receive the frozen inputs but not one another's reports or the synthesis. At minimum cover:
   - research importance, theory, either-way payoff, contribution, and preemption conditions;
   - target population, sampling, selection, denominators, missingness, dependence, and inference;
   - construct validity, legal and doctrinal boundaries, codebook clarity, attribution, edge cases, and uncertainty;
   - schema, identifiers, unit-space closure, quote verification, failure rows, and coverage reconciliation;
   - human validation, subgroup error, measurement-error correction, leakage, prompt sensitivity, and stopping thresholds;
   - data authorization, minimization, provider drift, security, reproducibility, cost, and operational failure;
   - methods currency: whether any named method, statistic, correction, tool, or numeric default the design adopted from the kit's dated defaults has since been superseded, argued from literature retrieved during this project rather than kit or model memory (guardrails section 10).
3. Tell each critic to be adversarial, cite exact artifact locations and evidence, distinguish fatal, major, and minor issues, propose tests or alternatives, and report rather than edit. Preserve each report unchanged.
4. Have at least one fresh critic attempt to falsify the design end to end: construct a plausible data-generating or operational scenario in which every mechanical check passes but the paper's conclusion is still wrong.
5. Build adversarial_change_matrix_vNNN.csv with issue ID, critic, severity, affected artifact and locator, claim, evidence, proposed resolution, disposition, researcher's decision if required, implementation version, verification, and upstream route.
6. Draft the synthesis without smoothing disagreement. Group duplicate issues, identify conflicts among critics, state the strongest version of each material objection, and recommend accept, reject with reason, defer to pilot, or upstream redesign.
7. Pause for researcher decisions on every substantive item. If the question, contribution, corpus, data route, construct, unit, or core estimand changes materially, do not patch through it here; set the corresponding upstream route and invalidate affected approvals.
8. For approved in-scope resolutions, create clean new versions of the complete methods and codebook package. Present the design afresh without recounting the dialectic in those clean files. Preserve the dialectic in critiques, synthesis, and change matrix.
9. Keep stable IDs when meanings do not change; create new IDs or an explicit mapping when they do. Synchronize cross-references, schema version constants, examples, unit-space hashes, prompt versions, validation partitions, hypotheses, estimands, and authorization constraints.
10. Rerun schema fixtures, traceability checks, unit-space reconciliation, authorization comparison, and a new-RA reading. A reviewer who proposed the edit must not be the sole verifier.
11. Draft design_freeze_vNNN.md listing exact proposed active versions and hashes, resolved and deferred issues, pilot tests for deferred risks, remaining limitations, invalidated prior approvals if any, and the statement the researcher is being asked to approve.

## Artifacts

Critique reports are immutable audit records. The synthesis and change matrix explain every disposition. Even if a component's substance remains unchanged, create a clean review-stage version or record an identical hash and explicit carry-forward in the freeze record so the package is closed and unambiguous. The design freeze names one mutually consistent version of every required component.

## Verification

- Confirm reviewer independence from prompts, timestamps, and file boundaries and confirm critics did not edit shared artifacts.
- Trace every fatal and major critique to a disposition, researcher decision where needed, implementation, and independent verification.
- Diff every clean artifact against its predecessor and disclose all substantive and mechanical changes.
- Revalidate schema examples and unit-space counts and trace hypothesis to estimand to codebook to schema to analysis.
- Compare the revised package to the authorization scope. Any corpus, provider, purpose, exposed field, or handling change returns to Stage 06.
- Confirm the clean artifacts contain no unmarked reviewer debate and the audit artifacts contain no hidden resolution.

## State transition

Do not alter state during Plan Mode. At execution start, set current_stage to 07-adversarial-review and status to running and append the run. An upstream-invalidating issue sets status to waiting_for_user and identifies the required route; do not activate a partially inconsistent package.

After all in-scope verification passes, activate the proposed clean versions, set status to awaiting_approval, mark design-freeze pending, and list deferred pilot tests. On explicit researcher approval, append the exact versions and hashes to DECISIONS.md, mark the gate approved, and set current_stage to 08-pilot and status to ready. Rejection produces a versioned review cycle or an upstream route. Design freeze is for the pilot; it does not authorize mid-pilot reinterpretation.

## Next-stage handoff

After approval, report the frozen-for-pilot versions, hashes, deferred tests, and authorization constraints. Provide the exact next task: enter Plan Mode for 08-pilot, agree on architecture and a five-to-ten-unit diagnostic sample, then execute the pilot without changing the frozen package during the run.
