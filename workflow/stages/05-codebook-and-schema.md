---
stage_id: "05-codebook-and-schema"
title: "Build the codebook, schema, and unit space"
paper_steps: ["2"]
core: true
interaction_profile: "plan_then_execute"
long_running: false
goal_condition: null
prerequisites: ["04-methods-design"]
required_inputs: ["project/PROJECT_STATE.md", "project/artifacts/methods_plan_vNNN.md", "project/artifacts/hypotheses_vNNN.md", "project/artifacts/estimands_vNNN.csv", "project/artifacts/sampling_validation_plan_vNNN.md", "authorized metadata or public corpus index"]
declared_outputs: ["project/artifacts/codebook_vNNN.md", "project/artifacts/coding_schema_vNNN.json", "project/artifacts/unit_space_vNNN.csv", "project/artifacts/coding_prompt_vNNN.md", "project/artifacts/schema_examples_vNNN.jsonl", "project/runs/<run_id>/schema_validation_report.json", "project/runs/<run_id>/run_manifest.json", "project/PROJECT_STATE.md", "project/DECISIONS.md", "project/RUN_LEDGER.md", "project/DEVIATIONS.md"]
human_gate: "codebook-schema-approval"
next_stage: "06-data-authorization"
failure_routes: ["03-feasibility-audit", "04-methods-design", "05-codebook-and-schema"]
---

## Objective

Translate the approved design into an unambiguous codebook a new research assistant could apply unaided, strict machine-readable rules for the output, a complete list and fixed count of units eligible for coding, and the exact coding prompt. Preserve uncertainty, source and processing history, evidence support, a reason for every missing or unusable item, and audit rows by construction.

## Prerequisite checks

1. Read AGENTS.md and PROJECT_STATE.md, confirm methods-plan approval, and load the exact active methods, hypothesis, estimand, and sampling-plan versions.
2. Inspect real authorized metadata or a public corpus index before defining identifiers and fields. Do not process restricted text before Stage 06. Worked examples and smell-test materials may expose text to a model only from three pre-gate sources: (a) researcher-supplied files inventoried at Stage 00 whose recorded authorization status permits model processing, (b) documents the researcher expressly confirms as public domain for this purpose in a logged decision, or (c) synthetic text. Enumerate in the run manifest every document whose text was exposed to a model during this stage; Stage 06 audits that enumeration rather than memory.
3. Confirm that every proposed variable traces to an approved construct and estimand. New substantive variables require a methods revision.
4. Confirm that the target universe can be enumerated without silent selection. If it cannot, stop with the exact missing index, metadata, or researcher rule.
5. Identify variables that cannot be supported from one supplied document or cannot be checked by a human; route them to methods design rather than disguising them as labels.

## Researcher decisions

The researcher must approve:

- the meaning and boundaries of every substantive variable and category;
- the coding unit and rules for multiple observations in one document;
- positive and negative clarifications, edge cases, examples, and uncertain or not-applicable treatment;
- whose statements count as the document's own and how majorities, concurrences, dissents, parties, quotations, and incorporated material are treated;
- inclusion, exclusion, deduplication, gap, conflict, and supersession rules;
- the complete list and fixed count of units eligible for coding and the stable ID logic; and
- the exact information exposed to a hosted model.

The agent may expose ambiguity and propose alternatives, but must not settle doctrinal or theoretical boundaries on the researcher's behalf.

## Mode handoff

Follow `workflow/shared/execution-control.md` and create the native stage plan
before work. Plan first, read-only. Inspect the active design and metadata,
enumerate every definition and schema decision, identify unresolved edge cases
(record a provisional `assistant-default` for each one that has a reasonable
resolution), and describe the validation fixtures and unit-space construction;
do not write any project output, state file, example record, ledger, or run directory
until the plan is complete. Then continue into execution in the same session,
without waiting, unless a stop condition in `workflow/shared/guardrails.md` §11
holds; only then enter Plan Mode, stop, and give the exact execution handoff.
Write and validate the declared output files and stop at
`codebook-schema-approval`, presenting the provisional choices there. This stage
is bounded: maintain the native plan but do not start a goal. The resulting
version may be revised after the pilot, but each pilot run must use one frozen
version.

## Work

1. Allocate a run ID only in execution and record all active input versions and researcher decisions.
2. Define the coding unit first. Explain when a document yields zero, one, or multiple observations; how overlapping passages, repeated statements, quoted authorities, separate opinions, and duplicate documents are handled; and which identifier links an observation to its source and unit-space row.
3. For every variable, provide a stable ID, type, allowed values, one-sentence definition, operational rule, positive clarifications, negative clarifications, boundary cases, worked positive and negative examples with provenance, and the evidence required. Tell coders to apply the written definition rather than background knowledge.
4. Include explicit uncertain, not_applicable, and unusable-document paths where appropriate. Keep substantive uncertainty distinct from missing data, unreadable text, wrong document, refusal, schema failure, and access failure. Never force a guess or return nothing.
5. Require each substantive observation, wherever feasible, to carry an exact verbatim quotation, source location, and one-sentence justification before the label. If documented normalization is needed for OCR or line breaks, preserve the original quote and normalization rule. For an absence, relation, or synthesis that no single passage can establish, require an explicit no-quote or multiple-passage evidence record instead. That record must identify every source and location reviewed, explain why no single quotation suffices, and state how the evidence supports the label. A citation or memory-based paraphrase cannot substitute for inspecting the original source.
6. Specify scope and attribution rules: distinguish a document's own position from a party, quoted source, dissent, concurrence, or background account. Define conflict resolution between sources and require unresolved conflicts to remain explicit.
7. Build coding_schema_vNNN.json using a declared JSON Schema draft. Require stage and schema version, run and document IDs, unit ID, status, provenance, observations, evidence records, justifications, labels, uncertainty, edge-case flag, and error details as appropriate. Use strict types and enums, required fields, conditional requirements by status, and additionalProperties false unless an approved reason is documented. Each successful observation must take exactly one approved evidence path: a verbatim quotation, multiple identified passages, or a no-quote record allowed by the codebook.
8. Build schema_examples_vNNN.jsonl with valid examples spanning zero observations, multiple observations, uncertain, not applicable, unusable, refusal, and edge case, plus intentionally invalid fixtures maintained in the validation report. Examples illustrate rules; they do not change them.
9. Build coding_prompt_vNNN.md. It must state the coder's bounded role and task (extracting evidence-backed observations from one supplied unit, not judging whether the source is correct or well reasoned, plus any researcher-approved perspective), and instruct the coder to read the codebook and schema, analyze only the supplied source material, apply definitions as written, record evidence before the label, use only enumerated values, prefer fewer supported observations, mark uncertainty, return an audit row for failure, log unanticipated cases without reinterpreting the frozen rules, and, before returning, review its own output against the codebook, schema, and these instructions and correct any failure to follow them. It must require an exact quotation where feasible and use the approved multiple-passage or no-quote path only for absence, relational, or synthesized labels that cannot rest on one passage. It must also carry the worker-isolation instructions from `workflow/shared/observation-fanout.md`: no memory or web, no sibling files, and only an operational receipt returned to the orchestrator.
10. Enumerate unit_space_vNNN.csv from the approved frame. Give each row a stable unit ID and record source identifier, expected document or component, inclusion status and rule, partition eligibility, source location, metadata provenance, and typed availability status. Include excluded and missing candidates where needed to reconcile the frame. Record the construction query, snapshot date, row count, and SHA-256 hash.
11. Mechanically validate the schema and all positive and negative fixtures. Test enum violations, absent required fields, extra fields, malformed quotations, conflicting statuses, duplicate observation IDs, and unknown unit IDs. Save commands, results, counts, and tool versions.
12. Conduct the new-RA smell test with a fresh reviewer (per `workflow/shared/fresh-review.md`): give only the codebook, prompt, schema, and a small authorized example set. The reviewer identifies ambiguity and inconsistent artifacts but does not silently edit them. Resolve changes through a new version and disclose them.

## Artifacts

The codebook, machine-readable output rules, complete list of coding units, prompt, and examples form one version-linked package and must name one another's exact versions and the values used to verify that the files have not changed. The validation report records the validator and output-format versions, commands, example counts, expected and actual outcomes, and unresolved failures. The record for the run shows which inputs and transformations produced each output. Never overwrite an approved package or revise definitions midway through a run.

## Verification

- Trace every codebook variable through schema fields to an approved estimand; confirm no orphan or newly invented variable.
- Parse the JSON Schema and require every valid fixture to pass and every intentionally invalid fixture to fail for the expected reason.
- Reconcile unit-space counts by inclusion, exclusion, missing status, and planned partition; confirm stable IDs are unique and the file hash is recorded.
- Confirm that substantive observations cannot validate without one approved evidence path, justification, label, provenance, and status fields.
- Confirm uncertainty and each failure type are distinguishable and no pathway silently drops a unit.
- Confirm the fresh-review ambiguities are resolved in a new version or listed as outstanding researcher inputs.

## State transition

Do not alter state in Plan Mode. At execution start, set current_stage to 05-codebook-and-schema and status to running and append the run. On a schema, unit-space, or smell-test failure, set status to failed or waiting_for_user as appropriate, preserve the last active package, and route to this stage or methods design.

After verification, activate the linked artifact versions, set status to awaiting_approval, mark codebook-schema-approval pending, and list every unresolved definition or denominator choice. On explicit approval, append the package versions and hashes to DECISIONS.md, mark the gate approved, and set current_stage to 06-data-authorization and status to ready. Approval is not authorization to send data and does not freeze the package against pilot revisions.

## Next-stage handoff

After approval, report the active package versions, the number of coding units, the value used to verify that the list has not changed, the example-validation results, and any restrictions. Provide the exact next task: run 06-data-authorization in normal interactive mode, verify and record the lawful and institutional route for the exact corpus-model use, and do not expose corpus text until that hard gate is approved.
