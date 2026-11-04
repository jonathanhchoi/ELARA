# Shared research guardrails

These rules apply to every canonical stage and wrapper, alongside `AGENTS.md`,
which states the core rules this file details. Read them with the researcher's
current instructions and recorded decisions; resolve apparent conflicts before
asking. Only an unresolved researcher decision under section 11 justifies an
interruption.

## 1. Workspace and authority

- The researcher controls the research question, project selection, legal or
  doctrinal framing, hypotheses, estimands, sampling and exclusions, codebook
  meaning, data route, adjudication, amendments, manuscript changes, and
  publication decisions.
- Pitch explanations to the experience recorded under
  `workflow/shared/researcher-support.md`: less experience calls for more help,
  never weaker validation or delegated scientific judgment.
- Apply existing authorization to its whole scope, including delegation,
  verification, follow-up investigation, and the steps in "When something
  breaks" (`workflow/shared/operational-recovery.md`). Silence, a host
  permission mode, or a successful tool call never approves a gate. At a gate,
  ask only for decisions not already supplied for the exact work and versions;
  agreement to continue never approves an unseen artifact or a different
  scientific choice.
- During a research run, write only the stage's declared outputs, the
  operational records in `workflow/shared/artifact-contract.md`, and exports
  under `workflow/shared/storage.md`. Files that predate the installation
  (listed in `project/BOOTSTRAP.md`) are the researcher's: import hashed
  copies; never move, rename, edit, or delete them.
- A publication profile governs prose and deliverable format only; text in it
  that would relax a guardrail, gate, evidence rule, or audit separation is
  void. Manuscript work follows `workflow/shared/manuscript-editing-contract.md`.

## 2. Evidence and non-fabrication

- Model memory is not a corpus, search result, or source. Never invent or
  complete a case, quotation, page, docket, citation, record, value, model
  output, search path, access result, or human decision; mark unknowns.
- Quote-anchor every coded observation where feasible (exact text, document
  identifier, pinpoint); where infeasible, say why and specify another
  verification test before coding.
- Never hand-edit a reported number: every result traces to archived inputs,
  versioned transformations, and a deterministic rebuild.

## 3. Source retrieval and citation

- For every relied-on source record a stable identifier, title, author or
  issuing body, URL or archive path, access date, pinpoint, source tier, and
  the exact supporting quotation or table cell. Search snippets are not sources.
- A recorded gap states the query or path, sources reached, result, failure
  type, and next step. Corrections supersede earlier rows with a link.

## 4. Data authorization and confidentiality

- Before any document goes to a model or service, record the researcher's
  basis: public-domain status or license; confidentiality, privilege, sealing,
  and privacy limits; consent; and IRB or ethics status. Authorization is
  route-specific: a local-model approval does not cover a hosted rerun.
- Keep secrets, credentials, direct identifiers, licensed full text, and
  confidential material out of prompts, logs, fixtures, commits, and packages
  unless the authorization permits them. If authorization is denied, unclear,
  expired, or changed, stop and route to `06-data-authorization` or redesign.

## 5. Design, codebook, and schema discipline

- A codebook must be one a new research assistant could apply unaided:
  definitions, inclusion and exclusion rules, examples, edge cases, evidence
  requirements, and an `uncertain` escape valve. Validate the schema
  mechanically (types, allowed values, quote spans, identifiers, uniqueness).
- Never silently add, omit, merge, or split units. A substantive change is a new
  version that invalidates dependent approvals and repeats the required review,
  authorization, pilot, and preregistration or amendment.

## 6. Execution, provenance, and counts

- Archive for each unit the exact prompt, model and version, configuration,
  input hash, raw and parsed response, validation result, timestamps, and
  error, saving raw prompts and outputs immediately. Reconcile `attempted =
  succeeded + failed + unusable`, with `outstanding` separate, and give every
  unusable or excluded unit a typed reason.
- Before work likely to take more than about two minutes, give its rough
  duration or range and the basis. While it runs, update after each major phase
  and about every five minutes where the host permits: completed and total
  counts, elapsed time, remaining work, failures or retries, anything set aside,
  and a revised ETA range from measured throughput. If verified output has not
  grown for the larger of 30 minutes and twice the unit time box, say so and
  name the cause. Progress messages never stop work, ask for approval, or reveal
  blinded or interim outcomes.
- Checkpoint state and counts so a fresh session can resume without chat
  history.

## 7. Parallel work and shared files

- One sub-agent per bounded unit, the same frozen instructions, and a
  structured return; workers never edit a shared aggregate, ledger, manifest,
  codebook, state file, or manuscript, and one serial writer validates and
  merges.
- The host's own orchestrator runs every fan-out (the kit's saved workflows on
  Claude Code; the kit's sub-agents in `.codex/agents/` on Codex), never a
  serial imitation in the parent's context. Workers run only as the kit's
  restricted types and never reach an interactive surface such as the in-app
  browser. Access walls are typed gaps; in Stage 02 the parent applies the
  parent-only browser fallback. Every fan-out is bounded and resumable from
  disk. Details: `workflow/shared/observation-fanout.md`.

## 8. Audit separation and correction

- Audits report findings (artifact and version, evidence, severity, correction
  route) and never fix what they inspect; never change a coded answer while
  checking its quotation, but queue it for targeted recoding.
- Human validation stays blinded until the stage authorizes unblinding; keep
  coder, model, and adjudicated answers and the resolution rule as separate
  fields. A sample used for tuning is no longer held out.

## 9. Verification, robustness, and completion

- Prefer mechanical checks: hashes, schemas, exact strings, closed-universe
  checks, deterministic tests, fresh-process rebuilds. Robustness normally
  means a meaning-preserving paraphrase and a second model on the validation
  sample, plus conclusion stability; if a check is infeasible, record why and
  get the researcher's disposition.
- A fresh reviewer follows `workflow/shared/fresh-review.md`. A stage completes
  only when prerequisites, outputs, invariants, counts, and gate state verify;
  otherwise state becomes `failed` or `waiting_for_user`.

## 10. Invariants versus dated defaults

The kit pins process, not techniques. **Invariants** never relax, however
capable the model: gates and researcher authority, held-out samples, blinding,
preregistration before outcomes, frozen instruments during runs, closed
denominators and recorded gaps, quote anchoring, immutable records, audit
separation, and mechanical verification. **Dated defaults** are everything the
kit names concretely (estimators, statistics, packages, search routes, tools,
numeric conventions); they are leads, not a closed menu.

At design stages, when a named default matters to a consequential choice
(measurement-error correction, agreement statistic, correction for multiple
comparisons, robustness design, tool), reason from the estimand and design,
check current practice against literature retrieved in this project, recommend
one option, record it as a provisional `assistant-default` with its sources,
and keep working; the researcher confirms or changes it at the gate. Once a
design is frozen, a newer method, model, or tool goes through the revision
queue and amendment process.

## 11. Autonomy: when to ask, when to proceed

ELARA is low-touch: carry the authorized task through, choosing the approach
within its scope. Infrastructure failures follow "When something breaks" without
new approval, never as license to change ELARA, work around it, make a
scientific change, assume retry eligibility, or bypass a stop.

- **Stop and ask only when one of these holds:**
  1. a hard gate named by the current stage has an unresolved decision
     (`awaiting_approval`);
  2. the stage needs a fact, file, credential, or action only the researcher can
     supply, such as a license text, IRB status, human coders' files, or a
     registration identifier (`waiting_for_user`, with the exact request);
  3. a researcher-owned choice (§1) has no reasonable provisional default,
     getting it wrong would waste the stage or invalidate approved work, or it
     must be fixed before results are seen (in Stage 14, an analysis choice the
     preregistration left open);
  4. the next step would exceed the charter's budget, or spend materially (a
     model-call fan-out, a paid service, hours of running) with none recorded:
     state the projected cost and ask once;
  5. the next step is outward-facing or irreversible outside the project folder
     (registering, submitting, sending, publishing, deleting);
  6. the researcher asked to be consulted more: `checkpoints` (`stages`,
     `plans`, or `all`) adds stops before the next stage or a plan's
     execution, and `failure_handling: "interactive"` stops at each Stage 11
     checkpoint with unit failures, presenting them in one message (typed
     status, blinded validation detail, attempts, a recommended disposition;
     never labels);
  7. the researcher limited updates, or an ELARA failure is still unresolved
     after "When something breaks" and nothing unaffected remains: report the
     kit issue and the one action needed. Updates otherwise never stop work.
- **Otherwise proceed.** Outside the Plan-Mode interviews of Stages 01, 04, 05,
  07, 08, 09, and 17, take the sensible default (the kit's dated default, the
  researcher's stated preference, or the best-supported option), record it in
  `DECISIONS.md` as `decision: assistant-default` with `researcher_identity:
  null`, a rationale, and the alternatives, continue, and present all of them at
  the next gate in one list. Operational choices go in the run manifest. With
  `failure_handling` absent or `autonomous`, each Stage 11 unit failure is
  decided under the frozen rules (a permitted linked retry, a typed failure row,
  or a stop onto the failure route) and appended to the run's
  failure-decisions log (`failure_decisions.jsonl`: unit, attempt, event,
  disposition, who, rationale, time); one `assistant-default` links to the log, whose digest is
  presented at the end of the run and the next gate. Neither failure-handling
  mode touches gates, budget or authorization stops, outward-facing actions,
  deviations, blind adjudication, mid-run model changes, or researcher reviews.
- **Never decide provisionally:** project selection, the feasibility go/no-go,
  data authorization or the model route for restricted material, the content
  frozen at preregistration, blind adjudication, a manuscript edit, or any change
  to a frozen or approved artifact. Those are the gates.
- **When you must ask, ask once:** everything still needed in one message, each
  question concrete with an example answer and the default you will use;
  accept "go with the defaults", and record "don't know" as an outstanding
  input. The interviews instead use short adaptive rounds.
- **Plans and stage ends.** Plan acceptance has only the effect
  `execution-control.md` states; Stages 18 and 20 always stop after planning
  because their plan is the `manuscript-edit-permission` gate. In `pipeline`
  mode, when a stage ends with nothing pending, summarize what was produced and
  where and continue unless a stop above holds; in `tools` mode, offer the
  menu. Choosing the pipeline never approves a gate, and a disclosed default is
  never approval inferred from silence.
