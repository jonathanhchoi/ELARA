# ELARA pipeline map

This is the human-readable map for ELARA (Empirical Legal Analysis with Research
Agents), the companion package for *ELARA: A Framework for Empirical Legal
Research with AI Agents*. The authoritative instructions are the numbered files in
`workflow/stages/`; the settings at the top of each file are the
machine-readable source for prerequisites, inputs, outputs, interaction mode,
long-running completion condition, gates, next-stage routing, and failure
routes.

The repository holds one active project. The mandatory core ends when Stage 16
rebuilds a verified replication package. Optional Stage 17 maps the article
from verified project files without writing article prose. Stages 18–20 support
a substantive manuscript first drafted by the researcher. ELARA does not draft
the first manuscript.

## Six-step crosswalk

| Paper step | ELARA stages | Purpose |
|---|---|---|
| Setup | `00-initialize` | Establish the workspace, project charter, access, inputs, and persistent state. |
| 1. Project viability | `01`–`03` | Select a project, review preemption, and audit feasibility. |
| 2. Methods | `04`–`09` | Design methods, define the coding unit and instrument, authorize data use, adversarially review, pilot, freeze, and preregister. |
| 3. Data acquisition | `10`–`11` | Assemble the corpus and generate structured data. |
| 4. Validation | `12`–`13` | Audit interpretive support and validate against blinded human coding. |
| 5. Analysis, robustness, and replication | `14`–`16` | Analyze, correct measurement error, test robustness, and verify the replication package. |
| 6. Publication (optional) | `17`–`20` | Organize the article, integrate results into the researcher's first draft, audit citations, and revise with approval. |

The operational stage numbers are intentionally more granular than the six paper
steps. A stage's `paper_steps` field records the crosswalk above.

## How routing works

1. `$elr` in Codex or `/elr` in Claude reads `project/PROJECT_STATE.md`.
2. It reads the current authoritative stage instructions and the shared workflow contracts.
3. It checks prerequisites, the exact file versions currently in use, approvals,
   outstanding researcher inputs, and the authorized data route.
4. It creates or updates the host's stage plan so that the plan agrees with the
   project files, then follows the mode handoff; metadata cannot change an
   application's mode automatically.
5. A long stage resumes its matching goal or gives the researcher the exact
   `/goal` command. Execution then receives a unique run ID, writes only
   declared versioned paths under `project/`, appends to the ledgers, and
   verifies every declared result.
6. A human gate sets `status: awaiting_approval`; silence is not approval. A
   failed verification follows a declared failure route rather than advancing.

`01-conceive` is optional. A researcher who arrives with a sufficiently specific
approved project charter may record a decision to skip it and route from Stage
00 to Stage 02.

## Router commands

| Command | What happens |
|---|---|
| `start` | Stage 00, fresh path: orientation, environment check, the usage-mode question (whole pipeline or specific tools, with the menu below), a short interview asked in one message (with a suggested default for each question), the charter, and the first gate. |
| `adopt` | Stage 00, adoption path: inventory existing materials wherever they are (under `project/inputs/existing/`, elsewhere in the folder, or at a named path), choose a preset or a specific tool, import unchanged versioned copies, record researcher-asserted approvals, write the adoption map, and land at the first stage that still needs to run. |
| `menu`, `tools` | Show the menu below in plain language and run what the researcher picks, importing and asserting whatever that tool needs first (on a fresh template, Stage 00's two-question specific-tools setup runs first). |
| `resume`, `continue`, `next` | In pipeline mode, read `PROJECT_STATE.md`, verify the current stage's prerequisites, run it, and at its end summarize what happened and continue into the next stage in the same session unless a stop condition in `workflow/shared/guardrails.md` §11 holds. In specific-tools mode, reopen the menu with "continue the current stage" as one of the choices. |
| `status` | Report stage, status, usage mode, approvals and their basis, active versions, and outstanding inputs. |
| `help`, `tour` | Orientation and current position; no file changes. |

Every command is available as `$elr <command>` in Codex and `/elr <command>` in
Claude Code, and the router also understands the same words in an ordinary
sentence ("let's continue", "show me the menu", "where are we?").

## Two ways to use ELARA: the whole pipeline or specific tools

Right after the orientation, Stage 00 asks one question: does the researcher
want to follow the **whole pipeline** — every stage in order, from question to
verified replication package, with the optional publication stages at the end —
or use **specific tools** now? The answer is the project's *usage mode*. Stage
00 records it in the `usage` setting at the top of
`project/PROJECT_STATE.md` (`pipeline` or `tools`; a state file without the key
means `pipeline`), in the charter, and as a decision. The researcher can change
it at any time by saying so; the router records the change the same way. Usage
mode decides only what is offered next; it never alters a prerequisite, gate,
or approval.

- **Pipeline mode.** The assistant walks the researcher through each stage. When
  a stage finishes and no gate or input is pending, it summarizes in a few
  plain-language lines what was produced and where it is, and continues into
  the next stage in the same session — still one bounded stage at a time, never
  one long-running mode for the whole pipeline — unless a stop condition in
  `workflow/shared/guardrails.md` §11 holds for that stage (it needs something
  only the researcher can supply, it would spend beyond the recorded budget, it
  acts outside the project folder, or the researcher recorded a `checkpoints`
  preference). Continuing is not approval of any gate: every gate is still put
  to the researcher separately, and silence never advances anything.
- **Low-touch by default.** Between gates the assistant does not interrupt the
  researcher: `workflow/shared/guardrails.md` §11 lists the only reasons to
  stop, and every other choice takes a sensible default, is recorded as a
  provisional `assistant-default` decision, and is presented at the next gate
  for the researcher to keep or change. A researcher who prefers to be
  consulted more often says so once; Stage 00 records it as `checkpoints` in
  `project/PROJECT_STATE.md` (`stages`, `plans`, or `all`), and the router then
  pauses before each stage, before executing each plan, or both. Likewise for
  failures during the full coding run: by default the assistant decides each
  failed document or unit under the approved rules, records the decision, and
  presents the complete list at the end of the run and at the next gate; a
  researcher who would rather decide each failure says so once and Stage 00
  records `failure_handling: "interactive"`, which pauses at the checkpoint
  where failures are found. Neither setting relaxes a gate, a spending limit,
  or a required review.
- **Specific-tools mode.** The researcher picks from the menu below. Stage 00
  runs its adoption path aimed at that tool, with the interview cut to two
  questions (a name for the project and what the researcher wants done): it asks
  only for the materials the tool needs, imports them, records
  researcher-asserted approvals for the gates before it, writes a short
  workspace charter, and lands there. When the tool finishes, the router offers
  the menu again rather than the next stage, and `resume` reopens the menu.
  `current_stage` records where the pipeline would continue if the researcher
  ever switches to pipeline mode (a project that only ever uses the manuscript
  utilities stays at `00-initialize`, status `ready`).

In either mode, a stage or utility the researcher names explicitly — from the
menu, in a sentence, or by its own skill — is authorized to run even if it is
not the current stage: the router first satisfies its prerequisites through
Stage 00's adoption path (importing what exists, recording researcher-asserted
approvals, noting what could not be verified) and then runs it. An earlier stage
run again is a recovery route and creates new versions under the dependency
rules in `workflow/shared/artifact-contract.md`.

## What ELARA can do: the menu

The router presents this list in plain language when asked for the `menu`, when
the researcher chooses specific tools at Stage 00, and whenever it is unclear
what to run next. In chat, the menu reads best grouped into a few plain-language
clusters (finding and checking a question; designing and testing the coding
instrument; getting and coding the data; analysis, robustness, and packaging;
manuscript help) rather than as one long list; the table below remains the
complete reference. Each tool is a numbered stage or utility; the last column is
what the researcher needs to bring (or point to) so that the tool can start.

| If you want to… | Tool | Bring |
|---|---|---|
| Find and choose a research question | Stage 01, `elr-01-conceive` | prior papers, a CV, or notes (optional) |
| Find out whether your idea has already been done | Stage 02, `elr-02-preemption-review` | your question and claimed contribution |
| Find out whether it is feasible, make the key choices with the evidence in hand, and receive the full analysis as a PDF | Stage 03, `elr-03-feasibility-audit` | your question, intended data, and method |
| Design the methods (hypotheses, sample, measurement, analysis plan) | Stage 04, `elr-04-methods-design` | your question |
| Write the codebook, the required coding-output format (the coding schema), and the coding prompt | Stage 05, `elr-05-codebook-and-schema` | the methods plan, or a description of what should be coded |
| Check whether you may use the data (license, terms, IRB or ethics) | Stage 06, `elr-06-data-authorization` | your sources |
| Get an adversarial review of the design before freezing it | Stage 07, `elr-07-adversarial-review` | the design and codebook |
| Pilot the coding on a sample | Stage 08, `elr-08-pilot` | the codebook and sample documents |
| Freeze the design and preregister | Stage 09, `elr-09-freeze-and-preregister` | the approved design |
| Assemble the corpus | Stage 10, `elr-10-corpus-acquisition` | authorized sources |
| Code the full corpus | Stage 11, `elr-11-scale-up` | the frozen codebook and the corpus |
| Check the coding against the underlying text | Stage 12, `elr-12-interpretive-verification` | coded data with evidence quotes |
| Run a blinded human validation study | Stage 13, `elr-13-human-validation` | coded data (and human coders) |
| Analyze, correcting for measurement error | Stage 14, `elr-14-analysis-and-correction` | coded data (and validation results) |
| Test robustness to prompts and models | Stage 15, `elr-15-robustness` | the analysis |
| Build a replication package | Stage 16, `elr-16-replication-package` | code, data, and results |
| Build a complete article skeleton with minimal methods and results prose | Stage 17, `elr-17-skeleton-draft` | the verified replication package and any organization preferences |
| Put results into your draft | Stage 18, `elr-18-integrate-manuscript` | your draft and the results |
| Cite-check a draft | Stage 19, `elr-19-cite-check` | your draft |
| Revise in response to referee or editor comments | Stage 20, `elr-20-revise-and-respond` | your draft and the comments |
| Add citations you marked as needed | `elr-add-citations` | your draft with the passages marked |
| Proofread | `elr-proofread` | your draft |
| Apply your hand-marked edits from a PDF | `elr-apply-markup` | the marked-up PDF |

Materials may stay wherever they are: in `project/inputs/`, elsewhere in this
folder (bootstrap lists what it found in `project/BOOTSTRAP.md`), or at a path
the researcher names. Stage 00 records their paths and enough information to
detect later changes, then copies the usable ones, unchanged, into
`project/artifacts/imported_vNNN/`; nobody has to
move or rename a file. Tools that presuppose earlier stages record what they
could not verify (for example, that a codebook was not piloted under ELARA) as
limitations rather than refusing to run.

## Adopting an existing project

Stage 00's adoption path lets a researcher bring in work already done, wherever
it sits (in `project/inputs/existing/`, elsewhere in the folder ELARA was
installed into, or at a named path). Imported files are copied unchanged into
`project/artifacts/imported_vNNN/`, checked for later changes, and recorded in
the `active_artifacts` state field under the names later stages use.
Any gate may be recorded as approved with basis `researcher-asserted`; the
adoption map (`project/artifacts/adoption_map_vNNN.md`) records, for every
stage, whether it has, partially has, lacks, or was not run by ELARA, and one
standing `DEVIATIONS.md` entry says where ELARA's own verification begins.
Later stages treat these recorded imports and asserted approvals as satisfying
their prerequisites, verify what they can, build missing derivative files as
new versions, and record the rest as limitations.

| Preset | Landing stage |
|---|---|
| Question only | `02-preemption-review` |
| Design in hand | `06-data-authorization` (or `07`/`08` if authorization and review are asserted) |
| Data in hand | `12-interpretive-verification` (or `13`/`14` if verification and validation are asserted) |
| Results in hand | `16-replication-package` (or `17-skeleton-draft` if a verified package is asserted) |
| Publication only | `18-integrate-manuscript` or `19-cite-check`; Stages 01–17 recorded as not run or, for the skeleton, skipped; manuscript utilities available at once |

Facts adoption cannot supply are recorded rather than assumed: preregistration
timing (analyses that predate any preregistration are labeled not preregistered
unless a dated record is imported), held-out purity (an unlisted tuning set
makes the Stage 13 sample "not held out"), audit separation (prior audits are
recorded as prior audits; Stages 12 and 19 re-audit), and an unknown coder model
version.

## Interaction modes

| Profile | Handoff |
|---|---|
| `normal` | Track the short stage in the native plan and gather a researcher decision; no Plan Mode or goal. |
| `plan` | Track the work, inspect in Plan Mode, make no file changes, and return the exact execution handoff. |
| `execute` | Track and run approved execution. If `long_running: true`, use the stage's exact completion condition as the durable goal. The host coordinates any parallel sub-agents under `workflow/shared/observation-fanout.md`. |
| `plan_then_execute` | Put the decision-complete read-only plan first in the native tracker, then continue into execution in the same session. Stages 01, 04, 05, 07, 08, 09, and 17 use Plan Mode and the host's question interface at their declared decision boundaries; the Stage 01 and 09 interviews are partial, and the Stage 07 interview follows the independent critiques. Other stages enter Plan Mode and stop only when a `workflow/shared/guardrails.md` §11 condition holds (Stages 18 and 20 always stop because their plan is the manuscript-edit gate). A long execution phase uses the exact stage goal. |

Plan phases do not alter state, ledgers, or research files. A mode or permission
setting never waives a human gate, data restriction, or version rule.

Every substantive stage and utility uses the host's native tracker: Codex uses
`update_plan`; Claude Code uses `TaskCreate`, `TaskUpdate`, and `TaskList`. The
tracker is rebuilt from the files on resume and is not part of the research
record. Every stage marked `long_running: true` has a completion condition that
the validator checks. If the matching goal is not active, the assistant gives
the exact `/goal ...` command and stops for the one-time activation. It never
replaces another active goal. One goal covers one stage, not the full pipeline
or an individual worker. Stages 01–03, 07–08, 10–12, 14–16, and 19 are
long-running. See `workflow/shared/execution-control.md`.

## Numbered stages

| Stage | Paper step | Core | Profile | Primary result | Researcher gate or stop |
|---|---:|:---:|---|---|---|
| `00-initialize` | setup | yes | `normal` | State, charter, access/model snapshot, and input inventory | `project-charter-approval` |
| `01-conceive` | 1 (optional) | yes | `plan_then_execute` | Plan-Mode profile confirmation, ranked source-checked shortlist, and Plan-Mode candidate comparison | `project-selection` |
| `02-preemption-review` | 1 | yes | `execute` | LaTeX-generated PDF literature review with a closest-match preemption summary, search log, source list, and novelty assessment | `preemption-disposition` |
| `03-feasibility-audit` | 1 | yes | `execute` | Live feasibility audit, one consolidated chat consultation on material researcher choices, and a question-led full-analysis PDF containing the evidence, calculations, alternatives, expected observation counts, sub-agent timing, optional API cost comparison, risks, decisions, and verdict | `feasibility-go-no-go` |
| `04-methods-design` | 2 | yes | `plan_then_execute` | Interactive Plan-Mode methods interview, then hypotheses, quantities to estimate, sampling, measurement, validation, and analysis plan | `methods-plan-approval` |
| `05-codebook-and-schema` | 2 | yes | `plan_then_execute` | Interactive Plan-Mode coding decisions, then codebook, required output format, edge cases, `uncertain` route, and complete list of units eligible for coding | `codebook-schema-approval` |
| `06-data-authorization` | 2 | yes | `normal` | Confirmed legal, ethical, confidentiality, and model-processing route | `data-authorization` |
| `07-adversarial-review` | 2 | yes | `plan_then_execute` | Independent critiques, Plan-Mode issue disposition, and revised frozen design | `design-freeze` |
| `08-pilot` | 2 | yes | `plan_then_execute` | Plan-Mode pilot configuration, then pilot outputs, disagreement review, checks, and revision queue | `pilot-acceptance` |
| `09-freeze-and-preregister` | 2 | yes | `plan_then_execute` | Plan-Mode registry and disclosure setup, exact recorded versions, preregistration, and external record | `preregistration-confirmation` |
| `10-corpus-acquisition` | 3 | yes | `execute` | Corpus and source-history lists, integrity checks, and a reason recorded for every missing item | Stop for a material corpus deviation |
| `11-scale-up` | 3 | yes | `execute` | Resumable one-coding-unit runs, raw outputs, validated ledger, and merged data | Stop on unresolved failures or frozen-rule violations |
| `12-interpretive-verification` | 4 | yes | `execute` | Independent evidence-support audit and recoding queue | Researcher disposition of unsupported or ambiguous coding |
| `13-human-validation` | 4 | yes | `plan_then_execute` | Held-out sample, blinded coder materials, adjudication, and error metrics | `validation-disposition` |
| `14-analysis-and-correction` | 5 | yes | `plan_then_execute` | Analysis that returns the same results from the same inputs and rules, diagnostics, and measurement-error correction | Stop if verified inputs do not support the analysis |
| `15-robustness` | 5 | yes | `execute` | Prompt and model comparisons, stability results, and deviations | Researcher disposition of material instability |
| `16-replication-package` | 5 | yes | `execute` | Exact software versions, included files, one rebuild command, and fresh-agent report | Core completes only after a clean rebuild |
| `17-skeleton-draft` | 6 | no | `plan_then_execute` | Plan-Mode organization and venue choices, then an organizationally complete draft with full results in displays and minimal prose; venue-aware Word uses an approved template, with comments only for open questions | `skeleton-draft-approval`, with a recorded skip available |
| `18-integrate-manuscript` | 6 | no | `plan_then_execute` | Approved integration into the researcher's substantive first draft | `manuscript-edit-permission` |
| `19-cite-check` | 6 | no | `execute` | Audit-only citation/source-support report | Findings are reported, never silently repaired |
| `20-revise-and-respond` | 6 | no | `plan_then_execute` | Versioned revisions, response matrix, and change disclosure | `manuscript-edit-permission` |

A coding unit may contain one document or several related documents, as fixed by
the codebook and the complete list of units eligible for coding. Stage 11
assigns one such unit—not necessarily one document—to each fresh sub-agent.

## How parallel work runs

Whenever a stage needs many independent judgments or retrievals — coding units
in Stages 08, 11, 12, and 15; searches, author and citation chains, and
retrieval in Stage 02; independent critics in Stage 07; claim-citation pairs in
Stage 19; fresh reviews — the work runs in parallel, with one bounded assignment
per isolated sub-agent under `workflow/shared/observation-fanout.md`. The host
coordinates the sub-agents rather than the assistant launching them by hand:

| Host | How parallel work is coordinated | Worker definitions |
|---|---|---|
| Claude Code | The kit's saved dynamic workflows, `elr-observation-fanout` (coding and audit units) and `elr-research-fanout` (research units), which the assistant launches as part of the stage; the researcher can watch them in `/workflows` | `.claude/agents/elr-worker.md`, `.claude/agents/elr-research-worker.md` |
| Codex | The kit's custom sub-agents, spawned by name in bounded waves; the parent retains the stage plan and goal | `.codex/agents/elr-worker.toml` (`elr_worker`), `.codex/agents/elr-research-worker.toml` (`elr_research_worker`) |

On either host the kit's controllers (`scripts/unit_fanout.py`,
`scripts/research_fanout.py`) fix the assignment list on disk, say what is still
pending, validate returns, bound attempts, and merge — so interrupted parallel
work resumes in a later session from the files, and no unit is silently dropped.
In the Stage 11 full coding run, each failed or unusable unit also gets a
recorded judgment — made by the assistant under the frozen rules and reported
in one complete list at the end (the default), or put to the researcher at the
checkpoint where it is found if they chose `failure_handling: "interactive"`
at setup.
Workers have a fixed, limited set of tools (coding workers no web; research
workers web search and fetch; none an interactive surface), a time box, and one
unique return path each; shared ledgers are edited serially by the parent.
During Stage 02 only, the parent session follows a separate browser-control
fallback for materially relevant papers that a worker could not download: it
tries open routes first, makes one ordinary browser attempt in the researcher's
authorized session, archives and hashes a successful download, and records any
remaining restriction. The browser is never given to a worker.

## Article planning, manuscript utilities, and the publication profile

Stage 17 produces an organizationally complete skeleton from verified project
files. It presents the full results through verified tables, figures, and
equations with sufficient captions and notes, and the text below each equation
defines every variable in it. It uses only the prose needed to
orient the reader and leaves the article's substantive writing to the researcher.
When Word is selected, the researcher may choose the bundled law-review or JLA
template. The visible manuscript follows that venue's title, heading, caption,
table, figure, equation, and page conventions; the planning fields and display
provenance are recorded in the run manifest, and a Word comment marks only a
section with open questions for the researcher.
JLA figures require alt text under the legend, and all venue-aware Word figures
embed that text accessibly. A different peer-reviewed outlet requires a current
official-requirements check and a supplied template or an expressly approved
fallback; JLA is never the silent default.
Stages 18–20 and three optional utilities work on the
researcher's manuscript under `workflow/shared/manuscript-editing-contract.md` (fixed invariants: no
first-draft authorship, permission before edits, versioned copies, numbers only
from results, no citations from memory, build and two review passes, complete
change disclosure, post-edit citation audit) and the researcher's **publication
profile** (`project/PUBLICATION_PROFILE_vNNN.md`, created from
`workflow/templates/publication_profile_template.md`, recorded in state as the
active `publication_profile`, with its exact version recorded for each
manuscript run). The profile owns
venue, audience, tone, exemplars, voice matching, prohibited constructions,
punctuation, citation style, and QA and deliverable requirements; it governs
prose only and cannot relax any guardrail or gate. It is read on demand by these
stages and utilities, never imported into `AGENTS.md` or `CLAUDE.md`.

| Utility | Authoritative file | What it does | Then |
|---|---|---|---|
| `elr-add-citations` | `workflow/utilities/add-citations.md` | Retrieves, reads, and adds only the citations the researcher marked, in the profile's citation style | audit-only Stage 19 |
| `elr-proofread` | `workflow/utilities/proofread.md` | Reports typos, grammar, clarity, tone, style tells, internal consistency, and venue compliance; fixes only clear errors when permitted | accepted items to Stage 20 |
| `elr-apply-markup` | `workflow/utilities/apply-markup.md` | Transcribes a hand-marked PDF into a reviewable edit list, stops, then applies exactly the approved edits | Stage 19 if citations changed |

Utilities never change `current_stage`; they append the run ledger and decisions
and produce versioned outputs like any stage.

## Hard-gate protocol

At a gate, the stage must:

1. verify and version all gate inputs;
2. set state to `awaiting_approval` and record the exact question;
3. identify the exact file versions the decision would approve;
4. stop without beginning the next stage;
5. append the researcher's actual decision to `project/DECISIONS.md`; and
6. attach the approval to those versions in state before resuming.

Conditional approval records its conditions. Changing methods, hypotheses,
codebook, required coding-output format, eligible-unit list, data route, or frozen corpus invalidates dependent
approvals and is never a clerical correction.

## Failure loops

| Failure or material change | Route back before continuing |
|---|---|
| Candidate is preempted, unimportant, or not selected | `01-conceive`, or end the project |
| Project is infeasible, unaffordable, or inaccessible | `01-conceive` or `04-methods-design`, then repeat feasibility |
| Methods or changes to a quantity the analysis will estimate | `04-methods-design`, then dependent approvals |
| Codebook, required output format, edge case, or eligible-unit-list changes | `05-codebook-and-schema`, then authorization, review, and pilot as applicable |
| Data permission is absent or the processing route changes | `06-data-authorization`; redesign upstream if authorization is denied |
| Adversarial review finds a material defect | `04-methods-design` or `05-codebook-and-schema`, then `07-adversarial-review` |
| Pilot fails accuracy, evidence, schema, or code review | Relevant design stage or `08-pilot`, followed by a new pilot version |
| A frozen file changes after preregistration | Owning design stage, then `09-freeze-and-preregister` with an amendment record |
| Corpus has material gaps, scope changes, or unapproved text | `06-data-authorization`, `09-freeze-and-preregister`, or `10-corpus-acquisition` |
| Scale-up has unresolved failures or rule drift | `10-corpus-acquisition`, `11-scale-up`, or the owning frozen-design stage |
| Interpretive verification finds unsupported codes | `05-codebook-and-schema`, `08-pilot`, `11-scale-up`, or targeted rerun through Stage 12 |
| Human validation or blind adjudication fails | `05-codebook-and-schema` or `08-pilot`, followed by new scale-up and validation versions |
| Analysis fails or robustness is materially unstable | Relevant method, validation, analysis, or robustness stage |
| Replication package does not rebuild | Originating Stage 10–15; never patch a final number by hand |
| Citation audit reports unsupported prose | `18-integrate-manuscript` or `20-revise-and-respond`; Stage 19 remains audit-only |

Every return creates new run and file versions. It does not erase the failed
run, original decision, deviation, or prior approval. A necessary departure from
the preregistration follows the recorded amendment/deviation process and carries
through every dependent output.

## Workflow 2.0 state compatibility

Version 2.0.0 inserts `17-skeleton-draft` and renumbers the former publication
Stages 17–19 as 18–20. ELARA does not automatically migrate a project whose
state points to one of the former Stage 17–19 IDs. Repair that state against the
append-only ledgers and exact active file versions, or rerun Stage 00's adoption path
to record the proper 2.0 landing. Do not change `current_stage` by number alone.

Version 2.0.1 refines the Stage 17 output. A project with an earlier Stage 17
output should create a new Stage 17 version or record a skip before Stage 18.

Version 2.0.2 makes researcher-facing language more concrete. It changes no
state field, stage order, approval gate, file format, or research safeguard, so
existing 2.0 projects need no migration.

Version 2.1.0 adds a required Stage 03 consultation after the evidence audit and
before the full feasibility-analysis report. Completed feasibility approvals
remain valid. An unfinished Stage 03 run completes the consultation and creates
a new report version under the updated contract.

Version 2.2.0 makes the Stage 04 read-only design phase an interactive Plan-Mode
methods interview. Existing approved methods remain valid. An unfinished Stage
04 run repeats the interview against the active evidence before writing a new
design version; accepting the host plan is not the final methods approval.

Version 2.3.0 extends evidence-first Plan-Mode decision interviews to the
declared boundaries in Stages 01, 05, 07, 08, 09, and 17. Stage 01 is limited
to its profile and shortlist decisions, Stage 07 interviews after preserving
independent critiques, and Stage 09 is limited to registry and disclosure
choices. Existing completed approvals remain valid. An unfinished affected
stage runs the interview at its next declared boundary before making the
affected write.

Version 2.3.1 removes article-level and section-level length guidance from
Stage 17 skeletons while retaining the target venue. Existing approved outputs
remain valid. Earlier skeleton source files continue to build, but their legacy
length fields are ignored and do not appear in newly rendered outputs.

Version 2.3.2 fixes the installation check inside Codex Desktop on Windows: a
running Codex session now satisfies the doctor's Codex requirement even when
the `codex` command cannot be started or found, with the skipped command check
recorded as a nonblocking note, and the installer's console report renders
correctly in every Windows console. It changes no state field, stage order,
approval gate, file format, or research safeguard, so existing projects need
no migration.

Version 2.3.3 aligns state validation with Stage 00's declared lifecycle. A
project may retain a null slug while Stage 00 is running, waiting for input, or
waiting for charter approval; the slug is assigned only after approval.
Bootstrap now checks the complete blank-state signature before treating a kit
copy as an installation source, so it still rejects in-progress projects.
Existing projects and approvals need no migration; a project stopped by the
earlier false validation error can resume Stage 00 with its records intact.

Version 2.3.4 makes research-worker retries auditable. Each sealed attempt has
its own return path and attempt number; a parent can record a failed or
stage-schema-unusable attempt without changing its raw file, and the controller
then offers the next distinct path. Exhausted paths are never reopened. Existing
completed waves remain valid. If an unfinished wave prepared under an older
version needs a retry, start a new versioned wave rather than overwrite its sole
return file.

Version 2.3.5 extends the 2.3.2 installation-check fix to Claude Code Desktop:
a running Claude Code session verifies itself when the `claude` command is not
on PATH, by probing the executable the session exports for its children or
reading the version stamped into the session environment, so the 2.1.154
dynamic-workflow minimum is still enforced. A live session with no version
evidence at all passes with a nonblocking note instead of failing, and the
installer selects the active host for its setup check. It changes no state
field, stage order, approval gate, file format, or research safeguard, so
existing projects need no migration.

Version 2.3.6 hardens two verifications after a field test's adversarial
review caught defects both had allowed through. Stage 05's unit-space step now
requires closure against the source, not only internal reconciliation: no two
rows may be the same underlying unit (duplicates, superseded versions, or
separately indexed components), classification fields must come from the
source's authoritative registry rather than identifier patterns, and the
enumerated counts must reconcile against the source's own reported totals
across every alternate identifier the source assigns to the same anchor. The
workflow validator now also checks that every always-firing researcher gate
passed before the current stage keeps its entry in the state approvals object,
with an error that says how to reconstruct a missing entry from DECISIONS.md
instead of re-running the stage. A previously valid state missing such an
entry fails validation after updating; the fix is the reconstruction the
error describes, and no stage, gate, file format, or research safeguard
changes otherwise.

Version 2.4.0 quiets the Stage 17 skeleton and makes its equations
self-explanatory. Venue-aware Word output now creates a comment only where the
researcher must notice or decide something: a section whose open questions are
not `none` gets one comment, anchored to its heading, containing only those
questions. The per-heading planning summaries and per-display provenance
comments are gone; the run manifest still records every planning field and
display reference. The per-section "Results presented" listing is retired from
the template, the stage, the builder, and every output format, and a source
that still contains the field builds without rendering it, like the retired
length fields. Every equation is now followed by its caption in all output
formats, and that caption must define each variable and term in the equation;
venue-aware Word previously omitted equation captions. The python-docx minimum
rises to 1.2 because the Word comment interface requires it. No state field,
stage order, approval gate, or research safeguard changes, so existing projects
need no migration; the next Stage 17 run simply produces the quieter form.

Version 2.4.1 adds a nonblocking model-readiness check to installation and
first-run setup. The installing agent retrieves current official model guidance
and inspects the active host and account; a deterministic offline helper
(`scripts/model_readiness.py`) validates dated, secret-free evidence and
distinguishes unavailable access, unverified access, and an available model
that is not selected; setup recommends the strongest applicable configuration
and surfaces capacity warnings. Model identifiers and rankings are not
hard-coded. No state field, stage order, approval gate, file format, or
research safeguard changes, so existing projects need no migration.

Version 2.4.2 hardens the Stage 02 parent-only browser fallback after a third
field crash (2026-08-30): a Cloudflare-style challenge page rendered in the
desktop app's in-app browser pane killed the app's GPU process about one second
after loading — faster than any agent reaction — so the former
navigate-away-immediately rule could never execute in time. The protocol now
classifies hosts before any browser use: a host that bot-walled automated
fetching in the same project, or a known challenge-fronted host, is never
opened in the in-app pane; such sources go to the researcher's own
separate-process browser session or the manual search packet, and remaining
in-pane attempts run as one batched sequence so no unknown page rests in the
pane between tool calls. No state field, stage order, approval gate, file
format, or research safeguard changes, so existing projects need no migration.

Version 2.5.0 lets the researcher choose how individual document or unit
failures during the Stage 11 full coding run are handled. A new optional
`failure_handling` key in `project/PROJECT_STATE.md` (state schema 1.3) records
the choice: `autonomous` — the default — has the assistant decide each failure
under the frozen rules, record every judgment in the run's
`failure_decisions.jsonl`, keep the run going, and present the complete digest
at the end of the run and at the next gate; `interactive` pauses at the batch
or validation checkpoint where failures are detected and puts each one to the
researcher, with operational content only. Stage 00 asks for the preference,
the Stage 08 interview confirms or changes it before the full run, and either
value can be changed later as a recorded decision. The mode governs only the
disposition of individual failed units in Stage 11: gates, budget and
authorization stops, the systematic-failure stop, deviation handling, the
pilot's row-by-row review, and every other stage's behavior are unchanged. The
new state key is optional and validated; a state file without it behaves as
`autonomous`, and files written under earlier schemas remain valid, so
existing projects need no migration.

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
history is never rewritten. The optional `usage` key of `PROJECT_STATE.md`
(`pipeline` or `tools`) is the usage mode that Stage 00 writes and the router
reads; it is validated, and absent means `pipeline`. The optional `checkpoints`
key (`none`, `stages`, `plans`, or `all`) is the researcher's preference for
extra pauses; it is validated, and absent means `none`. The optional
`failure_handling` key (`autonomous` or `interactive`) is the researcher's
preference for how individual failures during the Stage 11 full coding run are
decided; it is validated, and absent means `autonomous`. `project/BOOTSTRAP.md`, when present, is
the installer's report: how the kit was installed, what the folder already held,
which Python to use, and the doctor's result. `project/ELARA_MANIFEST.json`,
rewritten on every installer run, records which files in the folder are the
kit's, which are shared, and which were the researcher's before the kit arrived.
See `workflow/shared/artifact-contract.md` for exact naming and invalidation
rules.
