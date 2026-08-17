# ELARA: Empirical Legal Analysis with Research Agents

This repository is a one-project workspace for the workflow in *ELARA: A
Framework for Empirical Legal Research with AI Agents*. Treat the model as a
very fast research assistant whose work is verified, never trusted.

## Route every request from project state

1. Read `project/PROJECT_STATE.md` before doing research work.
2. Read `workflow/shared/guardrails.md` and
   `workflow/shared/artifact-contract.md`.
3. Read the canonical file in `workflow/stages/` named by `current_stage`.
   Canonical stage files control prerequisites, inputs, outputs, gates, failure
   routes, and the next stage; native skills are only wrappers.
4. Route the clean initial template to `00-initialize`, which opens with an
   orientation and asks whether the researcher wants the whole pipeline or
   specific tools (`workflow/shared/tool-menu.md`), then takes its fresh path
   (new project), its adoption path (`adopt`, or existing work brought in), or
   its tools path (`tools`). If state is missing or malformed but project
   history exists, stop and report a state-recovery issue; never erase history
   by reinitializing. If state says `awaiting_approval` or `waiting_for_user`,
   request the recorded input and do not advance. If it says `failed`, use the
   current stage's `failure_routes`.
5. In an adopted project, artifacts imported at Stage 00 and pinned in
   `active_artifacts` satisfy a stage's required inputs, and approvals recorded
   with basis `researcher-asserted` satisfy its gate prerequisites. Verify what
   can be verified (hashes, counts, formats), build any missing derivative as a
   versioned artifact, and record what cannot be verified as a limitation; do not
   refuse to run because an earlier stage was not run by ELARA.
6. `usage` in state records the researcher's choice: `pipeline` (default) or
   `tools`. In a `tools` project, stages and utilities run on request and out
   of sequence: Stage 00's tools path imports what a requested stage needs and
   records the gates the researcher asserts; a completed stage still records
   its normal transition, but its handoff and `resume` return to the menu
   rather than starting the next stage. In a `pipeline` project an
   out-of-sequence request stops with an explanation and the offer to switch;
   the switch either way is a recorded decision. Neither usage relaxes a gate,
   an authorization requirement, or audit separation.
7. Treat `interaction_profile` as a handoff, not an automatic mode switch:
   `normal` is interactive; `plan` produces no file changes; `execute` uses a
   bounded task unless `long_running: true`; `plan_then_execute` stops after a
   decision-complete plan and waits for an explicit execution handoff. For
   long-running execution, use Codex Goal mode or the saved Claude dynamic
   workflow for one-unit fan-out where the installed platform supports it.

During a research run, edit only paths under `project/` that the current stage
declares. Do not modify `AGENTS.md`, `CLAUDE.md`, `README.md`, `START_HERE.md`,
`PIPELINE.md`, `workflow/`, `.agents/`, `.claude/`, `scripts/`, or `tests/`
unless the researcher explicitly asks to develop the kit itself. Files the
researcher already had in this folder before the kit was installed beside them
are theirs: never edit, move, or delete them; copy them into `project/inputs/`
only when the researcher agrees.

## Gates and researcher authority

- Never auto-cross project selection, the feasibility go/no-go decision, data
  authorization, final methods/codebook/design approval, pilot acceptance,
  preregistration, blind adjudication, or approval to edit a manuscript.
- Research questions, doctrinal framing, hypotheses, design choices, exclusions,
  amendments, adjudication, and publication decisions belong to the researcher.
  Surface them with evidence; do not silently decide them.
- A gate approval is valid only for the exact artifact versions recorded in
  state. A changed approved artifact invalidates its dependent approvals.

## Evidence, data, and citations

- Analyze text the user supplies or material actually retrieved and archived.
  Never invent cases, quotations, doctrine, records, citations, values, or
  search results from model memory. Never design outcome prediction that invites
  training-data leakage.
- Check authorization before any corpus processing. Prefer public-domain data.
  Do not send licensed, confidential, sealed, privileged, personal, or otherwise
  restricted material to a hosted model until the researcher confirms the
  governing license, consent, confidentiality, and IRB or ethics route.
- For fetched material, prefer official primary sources, then reliable
  aggregators, then commentary. Record URL or stable identifier, access date,
  pinpoint locator, and the supporting quotation for every cited proposition.
  If a source cannot be obtained, say so; never substitute a plausible value.
- Distinguish “searched and found nothing” from “not searched.” Record every
  unusable document and missing value as a typed gap with what was attempted,
  what was found, and why it failed. Corrections supersede prior rows; they do
  not erase them.

## Design and coding discipline

- Discuss the architecture of a nontrivial build before writing code. Inspect
  actual input files and schemas before writing analysis code against them.
- Every coding task requires a frozen, written codebook with definitions, edge
  cases, and an `uncertain` escape valve, plus a fixed machine-readable schema
  and a closed unit-space manifest where applicable.
- Once a run begins, do not reinterpret its codebook, schema, unit space, or
  exclusion rules. Put edge cases in a revision queue. A revision starts a new
  version and triggers the required pilot, authorization, or preregistration
  route.
- Prefer mechanically verifiable outputs: exact-quote anchors, fixed schemas,
  deterministic transformations, checksums, and explicit denominators.
- The kit pins process, not techniques. Named methods, estimators, statistics,
  tools, and numeric defaults in the kit are dated defaults: at design stages,
  verify them against currently retrieved literature and surface alternatives
  for the researcher's decision. Gates, blinding, quarantine, preregistration,
  and audit rules are invariants and never relax, however capable the model.
- Keep inputs immutable. Give every run a unique timestamped run directory and
  every rerun a new `_vNNN` artifact. Never overwrite an approved artifact, raw
  prompt, raw model response, validation record, or prior correction.

## Execution and audit discipline

- Keep an exact run ledger: attempted, succeeded, failed, unusable, and
  outstanding counts must reconcile. Archive prompts and raw outputs as soon as
  they are produced; never report progress with vague estimates.
- When parallelizing, assign one observation, coding unit, comment, or other
  bounded unit per subagent. A coding unit may contain one document or several
  related documents; do not assume that document boundaries define units.
  Follow `workflow/shared/observation-fanout.md`: workers get fresh contexts and
  unique return paths, while shared ledgers and aggregates are edited serially.
- Make only requested, stage-declared changes. Preserve unrelated and uncommitted
  work.
- Audit stages report findings; they do not silently repair the work audited.
  Save a detailed finding and route it to the responsible correction stage.
- Before reporting results, run the prescribed validation and robustness checks,
  including prompt-paraphrase and second-model checks when required or feasible,
  and report disagreement rather than concealing it.
- Code is not done until it runs on a sample and its output is inspected. A stage
  is not done until every declared artifact and invariant is verified. Finish any
  file-editing task with a self-review and a complete, accurate list of changes.
- Manuscript work (Stages 17–19 and the optional utilities in
  `workflow/utilities/`) follows `workflow/shared/manuscript-editing-contract.md`
  and the researcher's publication profile (`project/PUBLICATION_PROFILE_vNNN.md`),
  which those stages read on demand. The profile governs prose and deliverable
  format only; it cannot relax any rule here or in `workflow/shared/`.

The complete operational rules live in `workflow/shared/`; `PIPELINE.md` is the
human-readable map of stages, modes, gates, and failure loops.
