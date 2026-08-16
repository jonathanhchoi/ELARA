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

## Two ways in

- **New project:** follow the five-minute start below and run `$elr start`
  (Codex) or `/elr start` (Claude Code).
- **Existing project** — you already have a question, a literature review, a
  codebook, coded data, results, a draft, or a referee letter: follow steps 1–3
  below, put your existing materials in `project/inputs/existing/`, and run
  `$elr adopt` / `/elr adopt`. Stage 00 inventories what you have, asks which
  decisions you vouch for, imports your files as versioned artifacts, and lands
  the pipeline at the first stage that still needs to run — or, if all you have
  is a draft, hands you straight to the cite-check and manuscript utilities. See
  "Adopting an existing project" below.
- **Lost at any point:** `$elr help` / `/elr help` explains what ELARA is, where
  this project stands, and what to type next.

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

### 2. Install the validator and run the preflight

With Python 3.10 or newer, run from the repository root:

```text
python -m pip install -r requirements.txt
python scripts/doctor.py
```

(`py` may replace `python` on Windows.) The doctor detects installed agent
hosts, checks their versions, validates the kit and its dependency, and runs a
temporary one-unit `prepare`/`submit`/`status`/`merge` exercise. The exercise
uses no model and no network. Resolve every reported failure before continuing.

### 3. Open the repository root

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

### 4. Add your materials

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

### What to expect in your first session

Stage 00 opens with a short orientation, checks the environment, and interviews
you one question at a time (project name and contribution; whether to brainstorm
a question or bring your own; scope; restrictions; databases, models, and budget;
anything that must stay off hosted models; optionally the venue you are writing
for). "Don't know" is a valid answer and is recorded as an open question. It then
drafts a project charter and stops: approving the charter is the first gate.
Every later stage ends the same way, at a decision that is yours, and nothing
advances on silence. `$elr status` / `/elr status` says where you are;
`$elr resume` / `/elr resume` picks up wherever you left off, in a new session,
because the state lives in `project/PROJECT_STATE.md`, not in the chat. Stages
02, 03, and 11 run long; start them and walk away.

### 5. Resume at any time

Open the same repository root and use:

```text
$elr resume       # Codex
/elr resume       # Claude Code
```

`$elr status` and `/elr status` report the current stage, approvals, active
artifact versions, last-run counts, and outstanding researcher inputs. The
router reads `project/PROJECT_STATE.md` rather than relying on chat history.

## Adopting an existing project

You do not have to start from a blank question. Put whatever exists under
`project/inputs/existing/` (a memo, a literature review, a codebook or prompt,
coded data, analysis code and results, a draft, referee letters — anything too
large to copy can be named by path) and run `$elr adopt` / `/elr adopt`. Stage
00 walks a checklist of what you have, proposes a preset, imports your files
unchanged into `project/artifacts/imported_v001/`, pins them as the artifacts
later stages will use, records the gates you vouch for as approvals with basis
`researcher-asserted` (any gate can be asserted — the point is to make your
existing judgment usable, not to re-litigate it), writes an adoption map saying
what each stage has, and lands the pipeline at the first stage that still needs
to run. Keep your original project folder as it is; the ELARA copy is the
auditable workspace and reads from the imported copies.

| Preset | You have | ELARA lands at |
|---|---|---|
| Question only | a chosen question and contribution | `02-preemption-review` (Stage 01 skipped) |
| Design in hand | methods, a codebook, schema, or prompt | `06-data-authorization`, or `07`/`08` if you assert authorization (and adversarial review) |
| Data in hand | coded data, with or without a codebook | `12-interpretive-verification`, or `13`/`14` if you assert a verification (and human validation) |
| Results in hand | analysis code and results | `16-replication-package`, or `17-integrate-manuscript` if you assert a package |
| Publication only | a draft, perhaps a referee letter | `17-integrate-manuscript` if results are to be integrated, else `18-cite-check`; the utilities work at once |

Adoption cannot supply a few facts after the fact, and the adoption map says so
where they apply: if analyses ran before any preregistration (or none exists),
they are labeled not preregistered unless you import a dated record; if you
cannot list which units were used to tune the prompt or codebook, Stage 13
reports its sample as not held out; work you already audited is re-audited when
Stages 12 or 18 run. None of this blocks the pipeline; it changes what the
reports say ELARA verified.

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

## Manuscript work: the publication profile and utilities

Voice, venue, and formatting are the researcher's. Before Stage 17, copy
`workflow/templates/publication_profile_template.md` to
`project/PUBLICATION_PROFILE_v001.md`, fill in the venue and audience, tone and
exemplars, whether to match your existing voice, prohibited constructions and
punctuation preferences, citation style, and the QA and deliverables you want
(compile and inspect every page, change log, redline, number of review passes),
and pin it in `project/PROJECT_STATE.md` as `publication_profile`. To change it,
save a new version and repin. Stages 17 and 19 and the utilities below read the
active profile on demand and record its version and hash; it governs prose only
and cannot relax a guardrail or gate. If no profile exists, those stages ask
before writing prose.

Three optional utilities cover manuscript tasks that are not pipeline stages
(`$elr-...` in Codex, `/elr-...` in Claude Code): `elr-add-citations` retrieves
and adds only the citations you marked, in the profile's citation style, then
routes the new version through the audit-only Stage 18; `elr-proofread` reports
typos, grammar, clarity, tone, style tells, internal consistency, and venue
compliance and fixes only clear errors when you permit it; `elr-apply-markup`
transcribes a hand-marked PDF into an edit list, stops for your review, then
applies exactly the approved edits. Their canonical instructions are in
`workflow/utilities/`; the shared invariants for any manuscript edit are in
`workflow/shared/manuscript-editing-contract.md`.

## Coding units and parallel work

ELARA assigns one observation or coding unit to each fresh worker context. A
coding unit may contain one document or several related documents, as defined by
the approved codebook and unit-space manifest. Document boundaries do not
silently determine the observation unit. Each worker sends its return envelope
through the deterministic controller's `submit` command; the controller validates
the sealed assignment, schema, IDs, and unique path before creating the return,
refuses overwrites, and later merges returns serially.

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
requirements.txt                Bounded Python runtime dependency
workflow/stages/NN-*.md         Canonical sequential stage prompts
workflow/utilities/             Optional manuscript utilities (add citations, proofread, apply markup)
workflow/shared/                Guardrails, artifact/fan-out/manuscript contracts, fresh-review protocol
workflow/templates/             Preregistration skeleton and publication profile template
.agents/skills/                 Codex wrappers ($elr-...)
.claude/skills/                 Claude wrappers (/elr-...)
.claude/workflows/              Claude one-unit fan-out workflow
project/                        Blank state, input, log, and output structure
scripts/                        Standalone validators and fan-out controller
tests/                          Package-maintenance tests and public fixtures
```

There is deliberately no `benchmarks/` directory and no validation-study archive
in this repository.

## Preflight options

Require a particular host, both hosts, or perform package maintenance without a
host check:

```text
python scripts/doctor.py --platform codex
python scripts/doctor.py --platform claude
python scripts/doctor.py --platform all
python scripts/doctor.py --platform none
```

`--platform none` is for maintainers and does not establish that an agent host is
ready. Stage 00 can capture a machine-readable, secret-free capability record:

```text
python scripts/doctor.py --json
```

Python and `jsonschema` are required for the deterministic fan-out controller
and validators, not for the earliest interactive design discussion.

## Plugins, MCP servers, and hooks

ELARA deliberately installs no third-party plugin, MCP server, credential, or
repository hook. Research databases, storage systems, browsers, reference
managers, and provider APIs differ by project and may expose licensed or
restricted material. Add an integration only after Stage 06 authorizes the exact
source, action, account, model route, and data exposure; record its name, version,
permissions, and limitations in the active access snapshot and run manifest.

For large observation runs, use host permission rules or explicitly trusted
deterministic hooks, where supported, to deny web, unrelated MCP tools, sibling
return reads, and writes outside the assigned path. ELARA's strict `submit`
command validates and creates canonical returns but is not itself a host sandbox.
An optional plugin may distribute future ELARA updates, but one clean repository
copy remains the authoritative, stateful workspace for one project.

## Cost and requirements

Stage 00 records a spending limit and Stage 03 obtains current prices and builds
project-specific cost and time estimates before expensive work begins. Nothing
beyond conception and feasibility proceeds until the researcher approves the
feasibility decision.

ELARA requires macOS, Windows, or Linux; Python 3.10 or newer with the packages
in `requirements.txt`; Codex or Claude Code with repository-local skill support;
internet access for installation and retrieval; adequate local storage; and
lawful and ethical authorization for the selected data and model route. A stage
checks any additional tool it needs before relying on it.

## License

MIT. See [LICENSE](LICENSE).
