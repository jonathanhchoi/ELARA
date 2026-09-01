# ELARA: Empirical Legal Analysis with Research Agents

This repository is a one-project workspace for the workflow in *ELARA: A
Framework for Empirical Legal Research with AI Agents*. Treat the model as a
very fast research assistant whose work is verified, never trusted.

## Route every request from project state

1. Read `project/PROJECT_STATE.md` before doing research work.
2. Read `workflow/shared/guardrails.md` and
   `workflow/shared/artifact-contract.md`, then
   `workflow/shared/execution-control.md`.
3. Read the canonical file in `workflow/stages/` named by `current_stage`.
   Canonical stage files control prerequisites, inputs, outputs, gates, failure
   routes, and the next stage; native skills are only wrappers.
4. Route the clean initial template to `00-initialize` (its fresh path for a new
   project, its adoption path when the researcher says `adopt`, brings existing
   work, or picks a specific tool from the menu in `PIPELINE.md`). Stage 00
   begins with an orientation and asks whether the researcher wants the whole
   pipeline or specific tools; that answer is the project's usage mode, recorded
   as `usage` (`pipeline` or `tools`) in the state front matter. If state
   is missing or malformed but project history exists, stop and report a
   state-recovery issue; never erase history by reinitializing. If state says
   `awaiting_approval` or `waiting_for_user`, request the recorded input and do
   not advance. If it says `failed`, use the current stage's `failure_routes`.
5. In an adopted project, artifacts imported at Stage 00 and pinned in
   `active_artifacts` satisfy a stage's required inputs, and approvals recorded
   with basis `researcher-asserted` satisfy its gate prerequisites. Verify what
   can be verified (hashes, counts, formats), build any missing derivative as a
   versioned artifact, and record what cannot be verified as a limitation; do not
   refuse to run because an earlier stage was not run by ELARA. A stage or
   utility the researcher names explicitly — from the menu, in a sentence, or by
   its own skill — is authorized even when it is not current: satisfy its
   prerequisites through Stage 00's adoption path first (import what exists,
   record researcher-asserted approvals, note the limitations), then run it.
6. Give every nontrivial stage or utility one native host plan derived from its
   canonical file, keep exactly one item in progress, and update it only when
   the declared evidence exists. Treat `interaction_profile` as a handoff, not
   an automatic permission switch: `normal` is interactive; `plan` produces no
   file changes; `execute` runs the tracked execution; `plan_then_execute`
   completes its tracked read-only plan phase before any write and continues in
   the same session unless a §11 stop applies. At the boundaries declared in
   `workflow/shared/execution-control.md`, Stages 01, 04, 05, 07, 08, 09, and
   17 enter Plan Mode and use the host's native structured-question control for
   researcher decisions. Stages 18 and 20 always enter Plan Mode because their
   plan is the manuscript-edit gate. Each interview has a separately stated
   execution effect; accepting a host plan never silently approves a later
   research gate or external action.
   A stage marked
   `long_running: true` executes only under its exact front-matter
   `goal_condition`: inspect the current goal, resume it if it matches, or give
   the complete `/goal <goal_condition>` handoff and stop; never replace a
   different active goal and never use one goal for the whole pipeline. Claude
   Code tracks work with its Task tools and Codex with `update_plan`; both hosts
   use `/goal` for the durable stage loop. See
   `workflow/shared/execution-control.md`.
7. Every fan-out on either host runs through the host's own orchestrator:
   Claude Code runs the kit's saved dynamic workflows in `.claude/workflows/`,
   which the assistant launches itself; Codex spawns the kit's custom
   sub-agents in `.codex/agents/` in bounded waves. The stage goal stays with
   the parent through wave validation and reconciliation. See
   `workflow/shared/observation-fanout.md`.
8. When a stage finishes and no gate or input is pending, do not stop silently
   and do not wait: summarize in a few plain-language lines what was produced
   and where it is, then in `pipeline` mode continue into the next stage in the
   same session, one bounded stage at a time, unless a §11 stop condition holds
   for that stage (it needs something only the researcher can supply, it would
   spend beyond the recorded budget, it acts outside the folder, or a
   `checkpoints` preference asks for a pause); in `specific tools` mode
   (`usage: tools`) offer the menu, which `resume` also reopens. Agreement to
   continue is never approval of a gate; every gate is put to the researcher
   separately. Neither usage mode relaxes a gate, an authorization requirement,
   or audit separation.
9. Be low-touch. Interrupt the researcher only for a real gating issue: the
   stop conditions in `workflow/shared/guardrails.md` §11 are the complete list.
   Every other choice takes the sensible default, is recorded as a provisional
   `assistant-default` decision, and is presented at the next gate for the
   researcher to keep or change. During the Stage 11 coding run, individual
   unit failures follow the recorded `failure_handling` preference (§11):
   absent or `autonomous`, decide each under the frozen rules, log the
   judgment in the run's failure-decisions file, and present the complete
   digest at the end of the run; `interactive` adds a pause at the checkpoint
   where failures are detected.
10. At installation/first use, after a kit update, or when the host/account/model
    route changes, follow `workflow/shared/model-readiness.md`. Verify the
    current strongest applicable model and actual access from live evidence,
    prominently communicate unknown/unavailable access and capacity advice,
    and record the versioned setup snapshot. This is advisory, not a new gate;
    never silently change models, reasoning settings, subscriptions, or a
    frozen research instrument. Read-only requests remain read-only.

During a research run, edit only paths under `project/` that the current stage
declares (plus the repository-local Git change-tracking the researcher
approved at Stage 00, which lives in `.git/`). Do not modify the kit's own files — `AGENTS.md`, `CLAUDE.md`,
`PIPELINE.md`, the kit README (`ELARA_README.md` in a project folder;
`README.md` in a plain clone of the kit), `workflow/`, `.agents/`, `.claude/`,
`.codex/`, `scripts/`, and `tests/` — unless the researcher explicitly asks to
develop the kit itself. Files that were in this folder before ELARA was
installed are the researcher's: never move, rename, edit, or delete them;
import copies. `project/BOOTSTRAP.md` lists them, and
`project/ELARA_MANIFEST.json` records which files are the kit's, which are
shared, and which are the researcher's, so a folder both use (for example
`scripts/`) is never a guess.

## Working with the researcher

- Assume a well-informed empirical legal researcher who may never have used a
  terminal and is not expected to know ELARA's internal vocabulary. This rule
  governs orientations, menus, questions, approval requests, progress and
  completion reports, decision documents, report prose, and handoffs.
- Unnecessary, invented, or purely internal jargon is prohibited. Use concrete
  language. Do not expose invented, ELARA-specific, or avoidable
  shorthand such as "fan-out," "typed gap," "unit-space manifest," "pinned,"
  "front matter," "quarantine," or "confirmatory core." Say what the thing is
  or what will happen:
  "parallel sub-agents," "a missing item with the reason it is missing," "the
  complete list of documents or other units eligible for coding," "recorded as
  the active version,"
  "the settings at the top of the file," or "kept out of the validation sample."
- Use a genuine term from statistics, computer science, AI-agent engineering,
  law, or another established literature only when it adds useful precision or
  avoids cumbersome repetition. If a well-informed empirical legal researcher
  may not know it, define it in ordinary language at its first use in each
  standalone context. If "agent harness" is useful, introduce it as "the
  software infrastructure surrounding an LLM that enables it to operate as an
  agent (the agent harness)." A term is not justified merely because it can be
  defined.
- When discussing methods, use standard terms without inventing compound
  labels. Say `unit of analysis`; `hypothesis`; `outcome` or `dependent
  variable` for a measured response; `quantity to estimate (estimand)` for the
  target quantity; and `correction for multiple comparisons`. Describe whether
  conclusions are descriptive, associational, or causal in a sentence and, for
  causal conclusions, state the identification strategy and assumptions. Use
  `confirmatory` only for the conventional distinction between analyses fully
  specified before outcomes are examined and exploratory analyses.
- Treat "artifact" as a context-dependent term, not a preferred word. Use it
  only when its established broad meaning is useful and define it if needed;
  otherwise say "file," "report," "dataset," "record," or "output." Preserve
  literal filenames, commands, state fields, and code values, but show them only
  when the researcher needs to locate or use them, in code formatting, and do
  not turn them into prose vocabulary.
- Say what will happen before it happens. Ask as little as possible: infer what
  the folder and the record already answer. Outside the deliberate Plan-Mode
  decision interviews in Stages 01, 04, 05, 07, 08, 09, and 17, when you must
  ask, put everything you still need in one message. In those interviews, use
  short, coherent rounds so later questions can respond to earlier answers.
  Make each question concrete, state the evidence and recommended answer, and
  explain the realistic alternatives and consequences. Accept "go with the
  recommendations", and accept "don't know" as an answer to record, not a gap
  to fill silently.
- The assistant runs the commands (`scripts/doctor.py`, validators, and the
  software that manages parallel sub-agents). Never ask the researcher to edit
  state, YAML, or a ledger by hand, and never make them retype an instruction the
  kit already contains.
- Speak in terms of the researcher's project ("your codebook", "the 400 opinions
  you sent"), not the kit's internals, and translate stage numbers into what
  they do. Name the exact file when they want to look at something.
- Before work likely to take more than about two minutes, give a rough duration
  or range and say what it is based on. While it runs, send brief progress and
  revised time-remaining updates after each major phase or group of parallel
  sub-agent assignments and at
  least about every five minutes when the host permits. Include exact completed
  and total counts where a denominator exists, elapsed time, retries or delays,
  and an ETA range based on observed throughput. If there is not yet enough
  evidence for a responsible completion ETA, say that and estimate the next
  checkpoint instead. These are informational updates, not gates or requests to
  stop; follow `workflow/shared/guardrails.md` §6.

## Gates and researcher authority

- Never auto-cross project selection, the feasibility go/no-go decision, data
  authorization, final methods/codebook/design approval, pilot acceptance,
  preregistration, blind adjudication, or approval to edit a manuscript.
- Research questions, doctrinal framing, hypotheses, design choices, exclusions,
  amendments, adjudication, and publication decisions belong to the researcher.
  Do not decide them silently: recommend one option with evidence, record the
  recommendation as a provisional `assistant-default` when the stage would
  otherwise stall, keep working, and put it to the researcher at the next gate.
  Project selection, data authorization, preregistration content, adjudication,
  manuscript edits, and changes to frozen artifacts are never provisional.
- At each declared Plan-Mode interview boundary, put every in-scope material
  open choice to the researcher before creating an `assistant-default`. The
  researcher's express choice to use a recommendation is a decision; silence is
  not. Do not expand a partial interview beyond its declared scope: Stage 01
  covers the profile and shortlist, Stage 09 covers registration and disclosure
  rather than reopening the frozen methods, and Stage 07 begins only after the
  independent critiques are preserved.
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
  they are produced; report progress and remaining time under
  `workflow/shared/guardrails.md` §6, never with vague or stale estimates.
- Keep the host-native plan synchronized with the run: update it at phase and
  wave checkpoints and before the completion report. For a long stage, report
  the exact verification evidence and counts in the conversation so the goal
  evaluator can judge the front-matter condition. Neither surface replaces the
  ledger or state.
- When parallelizing, assign one observation, coding unit, search, retrieval,
  comment, or other bounded unit per subagent. A coding unit may contain one
  document or several related documents; do not assume that document boundaries
  define units. Follow `workflow/shared/observation-fanout.md`: the host's
  orchestrator runs the wave (Claude Code: the kit's saved workflows; Codex: the
  kit's custom sub-agents `elr_worker` and `elr_research_worker`) — never
  hand-launched workers one at a time, never an all-tools agent, never a serial
  imitation in the parent's context — while workers get fresh contexts and
  unique return paths and shared ledgers and aggregates are edited serially.
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
- Manuscript work (Stages 18–20 and the optional utilities in
  `workflow/utilities/`) follows `workflow/shared/manuscript-editing-contract.md`
  and the researcher's publication profile (`project/PUBLICATION_PROFILE_vNNN.md`),
  which those stages read on demand. The profile governs prose and deliverable
  format only; it cannot relax any rule here or in `workflow/shared/`.

The complete operational rules live in `workflow/shared/`; in particular,
`execution-control.md` governs native plans and goals and
`observation-fanout.md` governs orchestrated workers. `PIPELINE.md` is the
human-readable map of stages, modes, gates, and failure loops.
