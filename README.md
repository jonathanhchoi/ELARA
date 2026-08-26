# ELARA: Empirical Legal Analysis with Research Agents

ELARA is the companion package for *ELARA: A Framework for Empirical Legal
Research with AI Agents* by Jonathan H. Choi. It turns Claude Code or Codex into
a research assistant for empirical legal work. The assistant can help you move
from a research question to a verified replication package. Optional tools can
also integrate results into a draft, check citations, and assist with revisions.

If you use ELARA in your research, **please cite the companion paper**:
Jonathan H. Choi, *ELARA: A Framework for Empirical Legal Research with AI
Agents* (2026), https://ssrn.com/abstract=7349078. A copyable reference is in
[How should I cite ELARA?](#how-should-i-cite-elara) below.

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

### Two warnings

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

## How should I cite ELARA?

If ELARA contributed to your research, please cite the companion paper, which
introduces the framework and reports its validation study:

> Jonathan H. Choi, *ELARA: A Framework for Empirical Legal Research with AI
> Agents* (2026), available at SSRN: https://ssrn.com/abstract=7349078.

In BibTeX:

```bibtex
@misc{choi2026elara,
  author       = {Choi, Jonathan H.},
  title        = {{ELARA}: A Framework for Empirical Legal Research with {AI} Agents},
  year         = {2026},
  howpublished = {Working paper},
  url          = {https://ssrn.com/abstract=7349078}
}
```

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

See [PIPELINE.md](PIPELINE.md) for the stage-by-stage map.

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

## License

MIT. See [LICENSE](LICENSE) (installed as `LICENSE.ELARA` in a project folder).
