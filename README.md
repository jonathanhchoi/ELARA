# ELARA: Empirical Legal Analysis with Research Agents

ELARA is the ready-to-use companion package for *ELARA: A Framework for
Empirical Legal Research with AI Agents* by Jonathan H. Choi. It gives Codex and
Claude Code a shared, stateful workflow for conducting a new empirical legal
research project from project selection through a verified replication package,
with optional tools for integrating results into a researcher-written manuscript,
checking citations, and revising in response to feedback.

This repository contains only reusable materials for a new project: canonical
workflow instructions, platform adapters, blank project templates, validators,
and public-domain test fixtures. It intentionally excludes the paper's validation
study data, prompts, model calls, code, run records, and results. Those materials
are not required to use ELARA.

Canonical stages live in `workflow/stages/`. `$elr` in Codex and `/elr` in
Claude Code route to the same files using `project/PROJECT_STATE.md`. Stages
that require independent model judgments also provide
`$elr-code-observations` and `/elr-code-observations`, which implement the same
one-unit assignment and serial-validation contract.

## Five-minute start

### 1. Get a clean copy

Download the repository ZIP from
[`jonathanhchoi/ELARA`](https://github.com/jonathanhchoi/ELARA), or clone it:

```text
git clone https://github.com/jonathanhchoi/ELARA.git
```

On Windows, if you download a ZIP, right-click it and choose **Extract All** so
the hidden `.claude` and `.agents` folders and the rest of the directory
structure are preserved.

Keep the working copy in a **local, non-synced folder**. Cloud-synced locations
such as Google Drive, OneDrive, and Dropbox can interfere with append-only logs,
resurrect superseded files, and copy restricted source material into cloud
storage. Stage 00 can initialize local Git change tracking; skip that step inside
a cloud-synced folder.

Use one clean copy for one research project. Start another project from another
clean copy.

### 2. Open the repository root

Choose either platform.

**Codex**

1. Install or open a supported Codex surface using the
   [official Codex documentation](https://developers.openai.com/codex/).
2. Open the folder containing `AGENTS.md` as the workspace.
3. Ask: `List the repository-local skills and confirm that $elr is available.`
4. Run `$elr start`.

**Claude Code**

Install Claude Code using its
[official setup guide](https://code.claude.com/docs/en/installation), then open
a terminal in the repository root and run:

```text
claude
```

Type `/skills` and confirm that `/elr` is present, then run `/elr start`.
Claude Code v2.1.154 or later is required for the saved Stage 11 dynamic
workflow.

If a skill does not appear, confirm that the folder you opened directly contains
both `AGENTS.md` and the hidden platform folder. A double-nested ZIP extraction
is the most common cause. Accept the workspace trust prompt, update older
installations, and use the platform's diagnostic command if needed.

### 3. Add your materials

Read `project/inputs/README.md`, then place papers, research notes, seed
citations, data dictionaries, and authorized source files in `project/inputs/`.
Stage 00 inventories and hashes those inputs. After inventory, add corrections
or replacements under new names instead of overwriting files.

Before starting, be ready to state:

- the working project name and intended contribution;
- whether you want the optional conception stage or already have a question;
- the people, institutions, jurisdictions, periods, and source types in scope;
- known license, confidentiality, terms-of-service, IRB, or ethics restrictions;
- the databases, APIs, models, subscriptions, and budget available; and
- anything that must never be sent to a hosted model.

Unanswered items become recorded open questions, not silent defaults. Do not
place licensed, confidential, sealed, privileged, or personal data in the
workspace—or send it to a hosted model—until the applicable authorization is
confirmed. ELARA has a hard data-authorization gate before corpus processing.

### 4. Resume at any time

Open the same repository root and use:

```text
$elr resume       # Codex
/elr resume       # Claude Code
```

`$elr status` and `/elr status` report the current stage, approvals, active
artifact versions, last-run counts, and outstanding researcher inputs. The
router reads `project/PROJECT_STATE.md` rather than relying on chat history.

## Try a ten-minute demo first (optional)

Use a **scratch copy of ELARA**, never the copy for a real project.

1. **Interactive demo (uses model tokens).** Move the files from
   `tests/fixtures/minimal_public_domain/inputs/` and its
   `project_question.md` into `project/inputs/`, run `$elr start` or
   `/elr start`, and answer the Stage 00 interview with the fixture's project
   question.
2. **Deterministic demo (free; requires Python).** Run
   `python tests/fixtures/public_domain_e2e/rebuild.py --output build`. It
   produces a miniature deterministic pass over Stages 08–16 without model or
   network calls.

Delete the scratch copy afterward. Demo outputs do not belong in a real project.

## The six paper steps

ELARA's nineteen operational stages implement the six-step framework in the
paper:

| Paper step | ELARA stages | Purpose |
|---|---|---|
| Setup | `00-initialize` | Establish the project workspace, inputs, access, and state. |
| 1. Project viability | `01`–`03` | Select a question, review preemption, and audit feasibility. |
| 2. Methods | `04`–`09` | Design methods, freeze the coding instrument, authorize data use, adversarially review, pilot, and preregister. |
| 3. Data acquisition | `10`–`11` | Acquire the corpus and generate structured data. |
| 4. Validation | `12`–`13` | Verify interpretive support and benchmark against blinded human coding. |
| 5. Analysis, robustness, and replication | `14`–`16` | Analyze, correct for measurement error, test robustness, and build a verified replication package. |
| 6. Publication (optional) | `17`–`19` | Integrate results into the researcher's first draft, audit citations, and revise with permission. |

Stage 17 is integration-only. ELARA will not draft the first manuscript or turn
an outline into a paper; the researcher supplies a substantive draft and retains
control over the thesis, framing, organization, and voice.

See `PIPELINE.md` for the stage-by-stage map and failure routes.

## Coding units and parallel work

ELARA assigns one observation or coding unit to each fresh worker context. A
coding unit may contain one document or several related documents, as defined by
the approved codebook and unit-space manifest. Document boundaries do not
silently determine the observation unit. Workers write to unique paths; a serial
controller validates and merges their returns.

## Modes and approvals

Each stage declares an `interaction_profile`:

- `normal`: gather an interactive researcher decision;
- `plan`: inspect and plan without file changes;
- `execute`: perform a bounded approved task, using a durable long-running mode
  for stages marked `long_running: true`; and
- `plan_then_execute`: complete a read-only plan, stop for approval, and execute
  only after an explicit handoff.

ELARA never silently crosses project selection, feasibility, data authorization,
methods or codebook approval, pilot acceptance, preregistration, blind
adjudication, or manuscript-edit permission. Silence is not approval.

## Ground rules

- Analyze supplied or actually retrieved text; never invent cases, citations,
  quotations, doctrine, data, or design decisions from memory.
- Use fixed schemas, quote anchors where feasible, explicit evidence paths for
  relational or synthesized labels, and an `uncertain` escape valve.
- Preserve inputs, raw prompts, raw outputs, approvals, and audit history.
  Reruns create new timestamped and `_vNNN` artifacts.
- Reconcile exact attempted, succeeded, failed, unusable, and outstanding counts.
  Missing or unusable units become typed gap rows, not silent exclusions.
- Retrieve and read sources before relying on them. Record provenance and
  supporting evidence; report unavailable sources as unavailable.
- Keep audit stages separate from correction stages.
- Reserve questions, framing, design, gates, adjudication, amendments, and
  publication decisions for the researcher.
- Treat named techniques and numeric defaults as dated choices to recheck at
  design time; treat authorization, gates, blinding, quarantine, preregistration,
  and audit separation as invariants.

The complete shared constitution is in `AGENTS.md`; artifact and audit rules are
in `workflow/shared/`.

## Repository map

```text
AGENTS.md                       Shared constitution and state router
CLAUDE.md                       Claude-specific adapter
PIPELINE.md                     Human-readable workflow map
workflow/stages/NN-*.md         Canonical sequential stage prompts
workflow/shared/                Guardrails and artifact/fan-out contracts
workflow/templates/             Preregistration skeleton
.agents/skills/                 Codex wrappers ($elr-...)
.claude/skills/                 Claude wrappers (/elr-...)
.claude/workflows/              Claude one-unit fan-out workflow
project/                        Blank state, input, log, and output structure
scripts/                        Standalone validators and fan-out controller
tests/                          Package-maintenance tests and public fixtures
```

There is deliberately no `benchmarks/` directory and no validation-study archive
in this repository.

## Verify your download

With Python 3.10 or newer:

```text
python scripts/doctor.py
```

(`py scripts/doctor.py` on Windows if needed.) The command verifies the stage
inventory, generated skill wrappers, and state template and prints PASS or FAIL.
Python is required for the deterministic fan-out controller and optional
validators, not for the earliest interactive design stages.

## Cost and requirements

Stage 00 records a spending limit and Stage 03 obtains current prices and builds
project-specific cost and time estimates before expensive work begins. Nothing
beyond conception and feasibility proceeds until the researcher approves the
feasibility decision.

ELARA requires macOS, Windows, or Linux; Codex or Claude Code with
repository-local skill support; internet access for installation and retrieval;
adequate local storage; and lawful and ethical authorization for the selected
data and model route. A stage checks any additional tool it needs before relying
on it.

## License

MIT. See [LICENSE](LICENSE).
