# ELARA: Empirical Legal Analysis with Research Agents

ELARA is the companion package for *ELARA: A Framework for Empirical Legal
Research with AI Agents* by Jonathan H. Choi. It turns Claude Code or Codex into
a research assistant for empirical legal work. The assistant can help you move
from a research question to a verified replication package. Optional tools can
also integrate results into a draft, check citations, and assist with revisions.

You remain responsible for the research decisions. ELARA stops for your
approval at each important choice, including the question, design, data use,
codebook, pilot, preregistration, and manuscript edits.

You don't need to know Git, Python, or the command line. The assistant handles
the setup and runs the commands. You answer its questions and make the calls.

## Start here

1. Open Claude Code or Codex in the folder where you want to work. This can be
   an empty folder or one that already contains your draft, data, or notes. A
   folder that OneDrive, Google Drive, or Dropbox does not sync is best (see the
   cautions below); the assistant will offer to move if it detects one.
2. Paste this message and press Enter.

   ```text
   Please set up ELARA (https://github.com/jonathanhchoi/ELARA), a workflow kit
   for empirical legal research, in this folder and walk me through it.

   1. Download
      https://raw.githubusercontent.com/jonathanhchoi/ELARA/main/scripts/bootstrap.py
      into this folder and run it with Python 3 (`python bootstrap.py`; try
      `python3` or `py` if that fails, and if Python 3.10 or newer is missing,
      help me install it first). The script installs ELARA here without
      overwriting my files, checks the setup, and removes itself.
   2. Follow the NEXT STEPS it prints: read `AGENTS.md`, then begin with the
      Orientation in `workflow/stages/00-initialize.md`. Explain things in plain
      language, work out what you can from my files, and ask me only what you
      still need, in one message. Ask whether I want the whole pipeline or
      specific tools, and show me the choices.

   Do not delete or overwrite any of my files.
   ```

3. Approve the commands if the app asks, then answer the questions. Use a
   different folder for each project.

## What happens after setup?

The assistant installs the kit without moving your files. It checks Python and
the one required package, then gives you a short explanation of what ELARA can
and can't do.

Next, it asks whether you want the whole pipeline or a specific tool. The whole
pipeline proceeds in order from project selection through replication, with
optional article-planning and publication steps at the end. The tools menu lets you go directly to
tasks such as a preemption review, feasibility audit, methods design, codebook,
human validation, a skeleton draft, manuscript integration, citation checking, or proofreading.
See [PIPELINE.md](PIPELINE.md) for the complete menu.

ELARA then works out what it can from your files, asks the few things it still
needs in one message (each with a suggested answer, so "go with your
defaults" is a complete reply), and drafts a short project charter. It stops
for your approval before continuing. From then on it is low-touch: at the end
of each step it says what it produced and moves on, and it interrupts you only
for a real decision — the formal gates, a fact only you hold, or a cost beyond
the budget you set. Choices it makes in between are recorded as provisional
and shown to you at the next gate to keep or change. If you would rather be
consulted before each step or before each plan, say so once and it will.
Agreement to continue never substitutes for approval at a formal gate.

If you already have a question, codebook, dataset, analysis, draft, or referee
letter, tell the assistant. It will import copies of that work and begin at the
first step that still needs attention.

### How do I come back later?

Open the same folder and type `/elr resume` in Claude Code or `$elr resume` in
Codex. You can also say `continue`. ELARA keeps its state in the project folder
rather than relying on the chat history.

Use `$elr status` or `/elr status` to see where the project stands. Use
`$elr menu` or `/elr menu` to see the tools, and `$elr help` or `/elr help` for
an explanation of what to do next. If the command is not recognized after
installation, restart the app once in that folder. Repository-local commands
load when the app starts.

### Two cautions before you begin

Keep the project in a local folder if you can. Google Drive, OneDrive, Dropbox,
and similar services can interfere with append-only logs, restore superseded
files, and copy restricted material to cloud storage. On Windows 11, Desktop and
Documents are usually inside OneDrive, so choose a folder directly under your
home folder instead (for example `C:\Users\<you>\elara\<project>`). The
installer warns when it detects a synced location, and the assistant offers to
set up elsewhere before anything is written; your files stay where they are.

Do not place licensed, confidential, sealed, privileged, or personal material
where the assistant can read it until ELARA has completed the data-authorization
step with you. That step addresses licenses, consent, confidentiality, and the
applicable IRB or ethics rules. ELARA will not send restricted material to a
hosted model before the planned route is approved.

## What if I prefer to install it myself?

The guided setup above is the simplest route. The following instructions are
for readers who prefer to install the kit by hand or inspect its components.

This repository contains the reusable parts of ELARA. These include the
workflow instructions, platform adapters, blank project templates, validators,
and public-domain test fixtures. The repository doesn't include the data,
prompts, model calls, code, run records, or results from the paper's validation
study. You don't need those materials to use the kit.

The authoritative instructions live in `workflow/stages/`. The `$elr` command in Codex
and `/elr` in Claude Code route to those same files using
`project/PROJECT_STATE.md`. Stages that need independent model judgments also
provide `$elr-code-observations` and `/elr-code-observations`. Both use the same
procedure of giving one unit to each assignment and validating returned files
one at a time.

### 1. Get a clean copy

Download the repository ZIP from
[`jonathanhchoi/ELARA`](https://github.com/jonathanhchoi/ELARA), or clone it.

```text
git clone https://github.com/jonathanhchoi/ELARA.git
```

On Windows, right-click a downloaded ZIP and choose **Extract All**. This
preserves the hidden `.claude` and `.agents` folders and the rest of the
directory structure.

Keep the working copy in a local, non-synced folder. Stage 00 can initialize
local Git change tracking, but you should skip that option in a cloud-synced
folder. Use one clean copy for each research project.

### 2. Run the preflight

ELARA requires Python 3.10 or newer. From the repository root, run the following
commands.

```text
python -m pip install -r requirements.txt
python scripts/doctor.py
```

On Windows, `py` may replace `python`. The doctor detects installed agent hosts,
checks their versions, validates the kit and its dependencies, and performs a
temporary one-unit `prepare`/`submit`/`status`/`merge` exercise. This exercise
uses no model and no network. Resolve every reported failure before continuing.

You can instead run `python scripts/bootstrap.py`. It installs the dependencies,
uses a `.venv` if the system Python is locked down, runs the doctor, and writes
`project/BOOTSTRAP.md`.

### 3. Open the repository root

For Codex, install or open a supported surface using the
[official documentation](https://developers.openai.com/codex/). Open the folder
that directly contains `AGENTS.md`. Ask the agent to list the repository-local
skills and confirm that `$elr` is available, then run `$elr start`.

For Claude Code, follow the
[official installation guide](https://code.claude.com/docs/en/installation).
Open a terminal in the repository root and run `claude`. Type `/skills` and
confirm that `/elr` appears, then run `/elr start`. Claude Code v2.1.154 or later
is required for the saved dynamic workflows that run ELARA's parallel work
(coding in Stage 11 and its pilots and audits; searches, retrieval, cite-checks,
and reviews elsewhere).

If a skill does not appear, make sure the folder you opened directly contains
both `AGENTS.md` and the hidden folder for your platform. A double-nested ZIP
extraction is a common cause. Accept the workspace trust prompt, update older
installations, and use the platform's diagnostic command if needed.

### 4. Add your materials

Read `project/inputs/README.md`. Then place papers, notes, seed citations, data
dictionaries, and authorized source files in `project/inputs/`. Stage 00 lists
them and records enough information to detect a later change. After that
inventory, add a correction or replacement under a new name instead of
overwriting the earlier file.

Before starting, be ready to describe the following items.

- The working project name and intended contribution
- Whether you have a question or want help developing one
- The people, institutions, jurisdictions, periods, and sources in scope
- Any license, confidentiality, terms-of-service, IRB, or ethics restrictions
- The databases, APIs, models, subscriptions, and budget available
- Anything that must never be sent to a hosted model

`Don't know` is a valid answer. ELARA records it as an open question rather than
filling the gap with a silent default.

### 5. What to expect in your first session

Use `$elr start` in Codex or `/elr start` in Claude Code. The first session
checks the environment and asks whether you want the pipeline or specific tools.
For the pipeline, it infers what it can from your files, asks the rest in one
message, and drafts the project charter. Approving that charter is the first
gate; after it, ELARA works between gates without interrupting you.

For a specific tool, ELARA asks for a project name and the task. It then asks
for the materials and prior decisions that the tool needs. If you run a stage
out of sequence, its reports distinguish decisions you vouch for from work that
ELARA independently verified. The menu returns when the task is done.

Stages 02, 03, and 11 can take a long time. You can start them and return later.
Stage 02 delivers its literature review as a LaTeX-generated PDF by default;
its search log, source list, and table linking claims to evidence remain
separate audit files. Word or another report format is used only when you ask
for it.

## Can I bring an existing project?

Yes. Your memo, literature review, codebook, prompt, coded data, analysis,
draft, or referee letter can remain where it is. Run `$elr adopt` or `/elr
adopt`, or choose a tool from the menu. Large files can remain at a path you
identify rather than being copied into the workspace.

ELARA inventories the existing work and imports unchanged copies into
`project/artifacts/imported_v001/`. It records those copies as the versions that
later stages should use. It can record any gate you explicitly vouch for with
the basis `researcher-asserted`. The resulting adoption map identifies what each
stage has and places the project at the first stage that still needs to run.
Your original files are never moved, renamed, or edited.

| Preset | You have | ELARA begins at |
|---|---|---|
| Question only | A chosen question and contribution | `02-preemption-review` after skipping Stage 01 |
| Design in hand | Methods, a codebook, a required coding-output format (a schema), or a prompt | `06-data-authorization`, or `07`/`08` if you also assert authorization and adversarial review |
| Data in hand | Coded data, with or without a codebook | `12-interpretive-verification`, or `13`/`14` if you also assert verification and human validation |
| Results in hand | Analysis code and results | `16-replication-package`, or `17-skeleton-draft` if you assert a verified package |
| Publication only | A draft and perhaps a referee letter | `18-integrate-manuscript` for results integration, otherwise `19-cite-check`. Stage 17 may be recorded as skipped, and the manuscript utilities are immediately available |

Adoption cannot reconstruct facts that were never recorded. An analysis without
a dated preregistration remains labeled as not preregistered. A human-validation
sample remains labeled as not held out if you cannot identify which units were
used to tune the prompt or codebook. Work you already audited is audited again
when Stages 12 or 19 run. These limitations don't block the pipeline, but they
change what ELARA reports as verified.

## Can I try a short demonstration?

Use a scratch copy of ELARA rather than the copy for a real project.

1. The interactive demonstration uses model tokens. Move the files from
   `tests/fixtures/minimal_public_domain/inputs/` and its `project_question.md`
   into `project/inputs/`. Run `$elr start` or `/elr start`, then use the
   fixture's project question in the interview.
2. The fully scripted demonstration is free and requires Python. The same
   inputs and rules always produce the same outputs. Run
   `python tests/fixtures/public_domain_e2e/rebuild.py --output build`. It makes
   a miniature pass over Stages 08 through 16 without a model or
   network call.

Delete the scratch copy when you are finished. Its outputs do not belong in a
real project.

## How does the kit correspond to the paper?

ELARA's twenty-one operational stages implement the paper's six-step framework.

| Paper step | ELARA stages | Purpose |
|---|---|---|
| Setup | `00-initialize` | Establish the workspace, inputs, access, and project state |
| 1. Project viability | `01` through `03` | Select a question, review preemption, and audit feasibility |
| 2. Methods | `04` through `09` | Design the study, freeze the coding instrument, authorize data use, review the design adversarially, pilot, and preregister |
| 3. Data acquisition | `10` through `11` | Assemble the corpus and generate structured data |
| 4. Validation | `12` through `13` | Verify interpretive support and benchmark against blinded human coding |
| 5. Analysis, robustness, and replication | `14` through `16` | Analyze the data, correct for measurement error, test robustness, and build a verified replication package |
| 6. Publication | `17` through `20` | Map the article without prose, integrate results into the researcher's draft, audit citations, and revise with permission |

Stage 02's formatted PDF literature review begins with a decision-focused
executive summary, normally no more than two or three pages, that compares what
each closest match actually says with the intended contribution and identifies
exactly what it preempts and what remains. The detailed map of the closest work
and the supporting search record follow.

The publication steps are optional. Stage 17 offers a default, skippable article
skeleton after the replication package is verified. It supplies a complete
article structure and presents the full results through verified tables,
figures, and equations with sufficient captions and notes. LaTeX-generated PDF
is the default, with Word and Markdown available on request. For Word, Stage 17
can use the bundled law-review or Journal of Legal Analysis template. The
visible manuscript contains article text, displays, and concise author
placeholders; planning sources and open questions remain in Word comments and
the run manifest. Figures carry accessible descriptions, and JLA descriptions
also appear below the legend. Another peer-reviewed outlet requires a current
check of its official instructions and either its own template or an expressly
approved fallback; the JLA template is never applied silently. Stage 17 leaves the
remaining prose to the author. Stage 18 only integrates results into an
existing substantive draft. ELARA won't write the first draft or turn notes
into a paper. The researcher retains control over the thesis, framing,
organization, and voice.

Workflow version 2.0.0 inserted Stage 17 and renumbered the former publication
Stages 17–19 as 18–20. Existing projects whose state points to one of those old
IDs are not migrated automatically. Repair the state against its ledgers and
the exact active file versions, or use Stage 00's adoption path to record the
correct 2.0 landing.

Workflow version 2.0.1 refines Stage 17 into an organizationally complete draft
that presents the full verified results through displays and leaves the
remaining prose to the researcher. A project with an earlier Stage 17 output
should create a new Stage 17 version or record a skip before entering Stage 18.

Workflow version 2.0.2 makes ELARA's researcher-facing language more concrete.
It does not change project state, stage order, approval gates, file formats, or
research safeguards, and existing 2.0 projects need no migration.

Workflow version 2.1.0 separates the Stage 03 evidence audit from its final
report. After the live checks and preliminary analysis, ELARA puts every
material researcher-owned choice to the researcher in one chat message, records
the answers, and only then produces the full feasibility-analysis PDF. A project
that has already passed the feasibility gate needs no migration. An unfinished
Stage 03 run should complete the consultation and create a new report version.

Workflow version 2.2.0 makes Stage 04 an interactive methods-design interview
in Codex or Claude Code Plan Mode. ELARA inspects the existing evidence first,
asks only the material open choices in short adaptive rounds, and drafts the
versioned design files only after the researcher accepts the proposed plan.
Completed methods approvals remain valid. An unfinished Stage 04 run should
repeat the read-only interview against its current active inputs before writing
a new design version.

Workflow version 2.3.0 extends that evidence-first Plan-Mode interview pattern
to the decision boundaries in Stages 01, 05, 07, 08, 09, and 17. Stage 01 uses
it only for the inferred researcher profile and the verified shortlist; Stage
07 uses it after independent critiques exist; and Stage 09 uses it only for
registry and disclosure choices, without reopening the approved scientific
design. Completed approvals remain valid. An unfinished affected stage should
run the interview at its next declared boundary before making the affected
write.

Workflow version 2.3.1 removes article-level and section-level length guidance
from Stage 17 skeletons while retaining the target venue. Existing approved
outputs remain valid. Earlier skeleton source files continue to build, but
their legacy length fields are ignored and do not appear in newly rendered
outputs.

Workflow version 2.3.2 fixes the installation check inside Codex Desktop on
Windows: a running Codex session now satisfies the doctor's Codex requirement
even when the `codex` command cannot be started or found (the packaged app
forbids other programs from launching it), and the skipped command check is
recorded as a note that does not block research. Outside a running session the
check still fails, now naming the underlying error. The installer's console
report also renders correctly in every Windows console. No stage behavior
changes; existing projects and approvals need no migration.

See [PIPELINE.md](PIPELINE.md) for the stage-by-stage map and failure routes.

## How does ELARA handle manuscript work?

The Stage 17 skeleton is an organizational aid, not a substantive first draft. It stays active
through as many versioned iterations as the researcher wants, then advances only
after explicit approval or a recorded skip. Stage 18 may consult an approved
skeleton, but the researcher's substantive draft and explicit instructions
control.

Voice, venue, and formatting belong to the researcher. Before Stage 18, copy
`workflow/templates/publication_profile_template.md` to
`project/PUBLICATION_PROFILE_v001.md`. Use the profile to record the venue,
audience, tone, relevant examples, citation style, and whether ELARA should
match your existing voice. You can also state constructions or punctuation to
avoid and specify the quality checks and deliverables you want. These may
include compilation, inspection of every page, a change log, a redline, and a
set number of review passes.

Record the profile in `project/PROJECT_STATE.md` as the active
`publication_profile`. Save and record a new active version whenever you change
it. The publication stages record the exact version and verify that it has not
changed. The profile governs prose and deliverables, but it cannot relax an
approval gate or shared guardrail. If no profile exists, ELARA asks for one
before writing prose.

Three optional utilities address manuscript tasks outside the sequential
pipeline. `$elr-add-citations` retrieves and adds only the citations you marked,
then sends the new version through the audit-only Stage 19. `$elr-proofread`
reports issues involving grammar, clarity, tone, style, consistency, and venue
rules. It fixes only clear errors that you permit. `$elr-apply-markup`
transcribes a hand-marked PDF into an edit list, stops for your review, and then
applies only the approved edits. Claude Code uses the same command names with a
leading slash.

The authoritative utility instructions are in `workflow/utilities/`. The shared
rules for manuscript edits are in
`workflow/shared/manuscript-editing-contract.md`.

## How do plans and goals run?

ELARA uses the planning surface in the tool you opened for every substantive
stage. In Codex that is the native plan updated with `update_plan`. In Claude
Code it is the task list maintained with `TaskCreate`, `TaskUpdate`, and
`TaskList`. The plan follows the authoritative stage instructions: prerequisites, any read-only
design phase, execution, verification, and the gate or handoff. ELARA updates it
as each phase actually finishes. The plan display is useful for orientation,
but the project state, the record of each run, the ledger, and the validated
files remain authoritative.

A long-running stage also states exactly what must be true before it is done.
Before execution starts, ELARA checks whether the matching durable goal is
active. If it is not, ELARA gives you one complete `/goal ...` line to paste.
That goal covers one stage, including every group of parallel assignments and
the final check that the records and counts agree. It never covers the whole
pipeline, and workers do not create goals of their own. If goals are not
available in the host, ELARA records the fallback and uses the same plan and
completion condition with durable file checkpoints.

Plan Mode is narrower. ELARA uses it when the result should be a read-only plan
or when your decision is the boundary between planning and writing. Stages 01,
04, 05, 07, 08, 09, and 17 use short, adaptive interviews at their declared
decision boundaries. The assistant first inspects the evidence, recommends an
option, explains realistic alternatives and consequences, and asks for your
preferences through Codex's or Claude Code's question interface. The Stage 01
and 09 interviews are intentionally partial, and the Stage 07 interview begins
only after the independent critiques are preserved. Accepting a proposed plan
permits only the named execution; it does not approve the later artifact gate
or authorize an external submission. Other `plan_then_execute` work completes
the no-write plan item in the native tracker and continues in the same session.
This keeps routine work moving between the research gates you control.

The complete contract is in `workflow/shared/execution-control.md`.

## How does parallel work run?

ELARA gives one observation or coding unit to each fresh sub-agent. The approved
codebook and the complete list of units eligible for coding define a coding
unit, which may contain one document or several related documents. File
boundaries do not silently determine the unit of observation. Searches,
retrieval, cite-checks, critiques, and reviews also run in parallel, with one
bounded assignment per sub-agent.

The tool you are using coordinates this parallel work: in Claude Code the
assistant launches ELARA's saved workflows (`elr-observation-fanout` for
coding, `elr-research-fanout` for research units), which you can watch in
`/workflows`; in Codex it spawns ELARA's custom sub-agents (`elr_worker`,
`elr_research_worker`) in bounded waves. Workers have a fixed, minimal set of
tools — coding workers have no web access, research workers have web search and
fetch, and none can reach a browser, desktop, or external tool or data connection
provided through the Model Context Protocol (MCP) — and each writes one unique
return.

Stage 02 adds a parent-only browser-control fallback without broadening those
worker permissions. After each literature-search wave, the parent session
reviews download gaps for potentially material papers, tries lawful open routes,
and then makes one ordinary browser-control attempt in your authorized session
when a bot restriction still blocks full text. It never bypasses a CAPTCHA,
paywall, login, license, or terms. Successful downloads are checked, archived,
and recorded so a later change can be detected; failed attempts remain listed,
with the reason for each failure, in the list of searches requiring researcher
access.

Each coding worker submits its response through software that applies the same
mechanical rules every time. It checks the fixed assignment, required output
format, identifiers, and unique output path before accepting the return. It
refuses overwrites and merges validated returns one at a time. The research
controller similarly records the fixed assignment list, pending work, and
allowed attempts, so an interrupted run resumes from the files in a later
session.

## What are the interaction modes and approval rules?

Each stage uses one of four interaction modes:

- `normal` tracks and gathers a short interactive researcher decision.
- `plan` uses Plan Mode and returns a plan without changing project files.
- `execute` performs the tracked work. A long-running execution uses the
  stage's exact goal condition.
- `plan_then_execute` completes the read-only plan item first, then continues in
  the same session unless a real approval or other stop condition requires Plan
  Mode and a handoff. Its execution uses a goal when the stage is long-running.

ELARA never silently crosses project selection, feasibility, data
authorization, methods or codebook approval, pilot acceptance, preregistration,
blind adjudication, or permission to edit a manuscript. Silence is not
approval.

## What ground rules does ELARA follow?

- Analyze text you supplied or material that was actually retrieved. Never
  invent cases, citations, quotations, doctrine, data, or design decisions from
  memory.
- Use fixed schemas and quote anchors where feasible. Use explicit evidence
  paths for relational or synthesized labels, and include an `uncertain` escape
  valve.
- Preserve inputs, raw prompts, raw outputs, approvals, and audit history. A
  rerun creates a new timestamped or `_vNNN` output.
- Make the attempted, succeeded, failed, unusable, and outstanding counts add
  up exactly. List every missing or unusable unit and the reason it is missing
  or unusable rather than excluding it silently.
- Retrieve and read a source before relying on it. Record where it came from,
  how it was processed, and the supporting evidence; report an unavailable
  source as unavailable.
- Keep an audit separate from the correction it may prompt.
- Leave research questions, framing, design, gates, adjudication, amendments,
  and publication decisions to the researcher.
- Recheck named techniques and numeric defaults when designing a project. Treat
  authorization, gates, blinding, keeping tuning and pilot material out of the
  validation sample, preregistration, and audit separation as fixed safeguards.

The complete shared rules are in [AGENTS.md](AGENTS.md). File, output, and audit
requirements are in `workflow/shared/`.

## What is in the repository?

```text
AGENTS.md                       Shared rules and state router
CLAUDE.md                       Claude-specific adapter
PIPELINE.md                     Workflow map, router commands, and tools menu
requirements.txt                Bounded Python dependencies
workflow/stages/NN-*.md         Authoritative sequential stage instructions
workflow/utilities/             Optional manuscript utilities
workflow/shared/                Guardrails and contracts for files, parallel work, and manuscripts
workflow/templates/             Report, skeleton-draft, publication-profile, and venue-aware Word templates and registry
scripts/latex_report.py         Render shared formatted-report LaTeX
scripts/build_preemption_review.py  Build the formatted Stage 02 report
scripts/build_feasibility_audit.py   Build the question-led Stage 03 report
scripts/build_skeleton_draft.py Build and validate Stage 17 Word, LaTeX, or Markdown skeletons
.agents/skills/                 Codex wrappers ($elr-...)
.claude/skills/                 Claude wrappers (/elr-...)
.claude/agents/                 Claude restricted worker sub-agents
.claude/workflows/              Claude saved workflows for parallel coding and research
.codex/agents/                  Codex restricted worker sub-agents
project/                        Blank project state, inputs, logs, and outputs
scripts/bootstrap.py            Safe installer and setup check
scripts/                        Validators and the two parallel-work controllers
tests/                          Maintenance tests and public fixtures
```

There is no `benchmarks/` directory or validation-study archive in this
repository.

### What happens when I install into an existing folder?

`scripts/bootstrap.py` copies the kit without overwriting an existing file. It
installs its own README and license as `ELARA_README.md` and `LICENSE.ELARA`,
so `README.md` and `LICENSE` in your folder stay yours, or free for your own
use. It appends missing lines from its own `.gitignore` or `requirements.txt`
in a marked block. It places the ELARA text first in an existing `AGENTS.md` or
`CLAUDE.md`, also in a marked block, and leaves your text after it. Run it with
`--dry-run` to see all of this as a plan before anything is written.

The installer lists what the folder already held in `project/BOOTSTRAP.md`, by
name for any file of yours inside a folder the kit also uses (such as
`scripts/`), and writes `project/ELARA_MANIFEST.json`, which records which files
are the kit's, which are shared, and which were yours. A file of yours that sits
exactly where a kit file would go is left alone, and `--update` never touches
it. Stage 00 uses that list when it offers to import existing work. Run the
installer again with `--update` to refresh ELARA's own files from GitHub. It
does not change project state, ledgers, or your files. The doctor and
validators ignore files that are not part of the kit.

An agent may also run the maintenance test suite from an initialized project.
The tests use `project/ELARA_MANIFEST.json` to build a temporary clean view of
that installed kit and substitute blank fixtures for the four live project
records. They never treat the project's state or append-only ledgers as clean
installation templates. They stop safely rather than guessing if that file is
unavailable or malformed.

## What else can the preflight check?

You can require a particular host, check both hosts, or run package-maintenance
checks without testing a host.

```text
python scripts/doctor.py --platform codex
python scripts/doctor.py --platform claude
python scripts/doctor.py --platform all
python scripts/doctor.py --platform none
```

The `--platform none` option is for maintainers. It doesn't establish that an
agent host is ready. Stage 00 can also save a machine-readable capability record
that contains no secrets.

When the check itself runs inside a live Codex session (Codex Desktop or the
Codex command line), that session counts as proof the Codex host works, even
if the `codex` command cannot be started or found; the skipped command check
becomes a note that does not block research. Claude Code is always verified
through its command, because ELARA's parallel workflows need version 2.1.154
or newer.

```text
python scripts/doctor.py --json
```

Python, `jsonschema`, and `python-docx` are required for the software that
coordinates parallel sub-agents, the validators, optional Word reports, and the
Stage 17 skeleton builder. Formatted reports default to PDF and require a
working LaTeX toolchain. These tools aren't required for the earliest design
discussion.

## What about plugins, MCP servers, and hooks?

ELARA installs no third-party plugin, MCP server, credential, or repository
hook. An MCP server connects an agent to outside tools or data through the Model
Context Protocol; a hook automatically runs a command in response to a specified
event. Projects use different databases, storage systems, browsers, reference
managers, and provider APIs. These tools may also expose licensed or restricted
material.

Add an integration only after Stage 06 authorizes the exact source, action,
account, model route, and data exposure. Record its name, version, permissions,
and limitations in the active access snapshot and the record for that run.

For a large run, ELARA's workers already have a fixed, limited set of tools:
the restricted sub-agent definitions in `.claude/agents/` (Claude Code) and
`.codex/agents/` (Codex) give coding workers no web access, research workers web
search and fetch only, and no worker a browser, desktop, MCP, or user-prompt
tool. Add host permission rules or trusted automated checks where supported
to also prevent sibling-return reads and writes outside the assigned path. The
strict `submit` command validates and creates return files in the required
format, but it is not an operating-system or host-enforced restriction on tool
and file access (a sandbox). An optional plugin may distribute later ELARA updates. A clean
repository copy remains the authoritative workspace for one project.

## What does ELARA cost, and what does it require?

Stage 00 records a spending limit. In Stage 03, ELARA first completes the live
checks and preliminary feasibility analysis. It then consults the researcher in
chat on the material choices the evidence cannot settle, presenting all of the
questions together with recommendations, alternatives, and consequences. The
researcher's answers are recorded before ELARA drafts the report. The resulting
LaTeX-generated PDF is the full analysis, not merely a verdict: it contains the
evidence, calculations, alternatives, tradeoffs, risks, and researcher
decisions, organized around eight plain-language questions with no gate table.
Word or another format is available on request. The analysis treats the
software infrastructure surrounding an LLM that enables it to operate as an
agent (the agent harness) as the default route for later coding and estimates
its completion time under low, central, and high scenarios. It does not invent
a dollar value for subscription-backed sub-agent use. Every audit also gives a
separately labeled estimate of what the same work would cost through the
optional API route, using current provider prices, projected tokens, retries,
model tiers, and available batch discounts. Human validation and other resource
burdens are stated primarily as time or capacity requirements; known fixed
charges are recorded and nontrivial spending is flagged for the researcher.
Nothing beyond conception and feasibility proceeds until the researcher
approves the feasibility decision.

ELARA runs on macOS, Windows, and Linux. It requires Python 3.10 or newer with
the packages in `requirements.txt`, plus Codex or Claude Code with
repository-local skill support. Installation and research retrieval require
internet access. A project also needs adequate local storage and lawful,
ethical authorization for its data and model route. Each stage checks any
additional tool before relying on it.

## License

MIT. See [LICENSE](LICENSE) (installed as `LICENSE.ELARA` in a project folder).
