# ELARA pipeline map

This is the human-readable map for ELARA (Empirical Legal Analysis with Research
Agents), the companion package for *ELARA: A Framework for Empirical Legal
Research with AI Agents*. The canonical instructions are the numbered files in
`workflow/stages/`; their YAML front matter is the machine-readable source for
prerequisites, inputs, outputs, gates, next-stage routing, and failure routes.

The repository holds one active project. The mandatory core ends when Stage 16
rebuilds a verified replication package. Optional Stages 17–19 implement the
paper's publication step for a substantive manuscript first drafted by the
researcher. ELARA does not draft the first manuscript.

## Six-step crosswalk

| Paper step | ELARA stages | Purpose |
|---|---|---|
| Setup | `00-initialize` | Establish the workspace, project charter, access, inputs, and persistent state. |
| 1. Project viability | `01`–`03` | Select a project, review preemption, and audit feasibility. |
| 2. Methods | `04`–`09` | Design methods, define the coding unit and instrument, authorize data use, adversarially review, pilot, freeze, and preregister. |
| 3. Data acquisition | `10`–`11` | Assemble the corpus and generate structured data. |
| 4. Validation | `12`–`13` | Audit interpretive support and validate against blinded human coding. |
| 5. Analysis, robustness, and replication | `14`–`16` | Analyze, correct measurement error, test robustness, and verify the replication package. |
| 6. Publication (optional) | `17`–`19` | Integrate results into the researcher's first draft, audit citations, and revise with approval. |

The operational stage numbers are intentionally more granular than the six paper
steps. A stage's `paper_steps` field records the crosswalk above.

## How routing works

1. `$elr` in Codex or `/elr` in Claude reads `project/PROJECT_STATE.md`.
2. It reads the current canonical stage and the shared workflow contracts.
3. It checks prerequisites, exact active artifact versions, approvals,
   outstanding researcher inputs, and the authorized data route.
4. It explains the stage's mode handoff; metadata cannot change an application's
   mode automatically.
5. Execution receives a unique run ID, writes only declared versioned paths under
   `project/`, appends to the ledgers, and verifies every declared result.
6. A human gate sets `status: awaiting_approval`; silence is not approval. A
   failed verification follows a declared failure route rather than advancing.

`01-conceive` is optional. A researcher who arrives with a sufficiently specific
approved project charter may record a decision to skip it and route from Stage
00 to Stage 02.

## Interaction profiles

| Profile | Handoff |
|---|---|
| `normal` | Stay interactive and gather a researcher decision. |
| `plan` | Inspect in Plan Mode and make no file changes. |
| `execute` | Run a bounded approved task; use the platform's durable long-running mode for one-unit fan-out where declared. |
| `plan_then_execute` | Finish a decision-complete read-only plan, stop for approval, then execute only the approved scope. |

Plan phases do not alter state, ledgers, or artifacts. A mode or permission
setting never waives a human gate, data restriction, or artifact-version rule.

## Canonical stages

| Stage | Paper step | Core | Profile | Primary result | Researcher gate or stop |
|---|---:|:---:|---|---|---|
| `00-initialize` | setup | yes | `normal` | State, charter, access/model snapshot, and input inventory | `project-charter-approval` |
| `01-conceive` | 1 (optional) | yes | `plan_then_execute` | Researcher profile and ranked, source-checked shortlist | `project-selection` |
| `02-preemption-review` | 1 | yes | `execute` | Retrieved literature, search log, source manifest, and novelty assessment | `preemption-disposition` |
| `03-feasibility-audit` | 1 | yes | `execute` | Live probes, acquisition funnel, current cost/time/risk model, and verdict | `feasibility-go-no-go` |
| `04-methods-design` | 2 | yes | `plan_then_execute` | Hypotheses, estimands, sampling, measurement, validation, and analysis plan | `methods-plan-approval` |
| `05-codebook-and-schema` | 2 | yes | `plan_then_execute` | Codebook, schema, edge cases, `uncertain` route, and closed unit space | `codebook-schema-approval` |
| `06-data-authorization` | 2 | yes | `normal` | Confirmed legal, ethical, confidentiality, and model-processing route | `data-authorization` |
| `07-adversarial-review` | 2 | yes | `plan_then_execute` | Independent critiques, issue disposition, and revised frozen design | `design-freeze` |
| `08-pilot` | 2 | yes | `plan_then_execute` | Pilot outputs, disagreement review, checks, and revision queue | `pilot-acceptance` |
| `09-freeze-and-preregister` | 2 | yes | `plan_then_execute` | Hash-pinned freeze, preregistration, and external record | `preregistration-confirmation` |
| `10-corpus-acquisition` | 3 | yes | `execute` | Corpus/provenance manifests, integrity checks, and typed gaps | Stop for a material corpus deviation |
| `11-scale-up` | 3 | yes | `execute` | Resumable one-coding-unit runs, raw outputs, validated ledger, and merged data | Stop on unresolved failures or frozen-rule violations |
| `12-interpretive-verification` | 4 | yes | `execute` | Independent evidence-support audit and recoding queue | Researcher disposition of unsupported or ambiguous coding |
| `13-human-validation` | 4 | yes | `plan_then_execute` | Held-out sample, blinded coder materials, adjudication, and error metrics | `validation-disposition` |
| `14-analysis-and-correction` | 5 | yes | `plan_then_execute` | Deterministic analysis, diagnostics, and measurement-error correction | Stop if verified inputs do not support the analysis |
| `15-robustness` | 5 | yes | `execute` | Prompt and model comparisons, stability results, and deviations | Researcher disposition of material instability |
| `16-replication-package` | 5 | yes | `execute` | Environment lock, archive, one rebuild command, and fresh-agent report | Core completes only after a clean rebuild |
| `17-integrate-manuscript` | 6 | no | `plan_then_execute` | Approved integration into the researcher's substantive first draft | `manuscript-edit-permission` |
| `18-cite-check` | 6 | no | `execute` | Audit-only citation/source-support report | Findings are reported, never silently repaired |
| `19-revise-and-respond` | 6 | no | `plan_then_execute` | Versioned revisions, response matrix, and change disclosure | `manuscript-edit-permission` |

A coding unit may contain one document or several related documents, as fixed by
the codebook and unit-space manifest. Stage 11 assigns one such unit—not
necessarily one document—to each fresh worker context.

## Hard-gate protocol

At a gate, the stage must:

1. verify and version all gate inputs;
2. set state to `awaiting_approval` and record the exact question;
3. identify the artifact versions and hashes the decision would approve;
4. stop without beginning the next stage;
5. append the researcher's actual decision to `project/DECISIONS.md`; and
6. pin approval to those versions in state before resuming.

Conditional approval records its conditions. Changing methods, hypotheses,
codebook, schema, unit space, data route, or frozen corpus invalidates dependent
approvals and is never a clerical correction.

## Failure loops

| Failure or material change | Route back before continuing |
|---|---|
| Candidate is preempted, unimportant, or not selected | `01-conceive`, or end the project |
| Project is infeasible, unaffordable, or inaccessible | `01-conceive` or `04-methods-design`, then repeat feasibility |
| Methods or estimand changes | `04-methods-design`, then dependent approvals |
| Codebook, schema, edge case, or unit-space changes | `05-codebook-and-schema`, then authorization, review, and pilot as applicable |
| Data permission is absent or the processing route changes | `06-data-authorization`; redesign upstream if authorization is denied |
| Adversarial review finds a material defect | `04-methods-design` or `05-codebook-and-schema`, then `07-adversarial-review` |
| Pilot fails accuracy, evidence, schema, or code review | Relevant design stage or `08-pilot`, followed by a new pilot version |
| Frozen artifact changes after preregistration | Owning design stage, then `09-freeze-and-preregister` with an amendment record |
| Corpus has material gaps, scope changes, or unapproved text | `06-data-authorization`, `09-freeze-and-preregister`, or `10-corpus-acquisition` |
| Scale-up has unresolved failures or rule drift | `10-corpus-acquisition`, `11-scale-up`, or the owning frozen-design stage |
| Interpretive verification finds unsupported codes | `05-codebook-and-schema`, `08-pilot`, `11-scale-up`, or targeted rerun through Stage 12 |
| Human validation or blind adjudication fails | `05-codebook-and-schema` or `08-pilot`, followed by new scale-up and validation versions |
| Analysis fails or robustness is materially unstable | Relevant method, validation, analysis, or robustness stage |
| Replication package does not rebuild | Originating Stage 10–15; never patch a final number by hand |
| Citation audit reports unsupported prose | `17-integrate-manuscript` or `19-revise-and-respond`; Stage 18 remains audit-only |

Every return creates new run and artifact versions. It does not erase the failed
run, original decision, deviation, or prior approval. A necessary departure from
the preregistration follows the recorded amendment/deviation process and carries
through every dependent artifact.

## Persistent state

`project/PROJECT_STATE.md` is the mutable router. Valid statuses are:

| Status | Meaning |
|---|---|
| `ready` | Prerequisites are satisfied and the current stage may begin. |
| `running` | A unique execution run is open. |
| `awaiting_approval` | A named human gate blocks advancement. |
| `waiting_for_user` | Specific information or an external action is required. |
| `failed` | Verification failed; use a declared failure route. |
| `complete` | The selected workflow endpoint has been verified. |
| `superseded` | This state snapshot or project copy is no longer active. |

`project/DECISIONS.md`, `project/RUN_LEDGER.md`, and
`project/DEVIATIONS.md` are append-only. State may point to newer versions, but
history is never rewritten. See `workflow/shared/artifact-contract.md` for exact
naming and invalidation rules.
