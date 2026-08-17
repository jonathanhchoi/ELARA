# The tool menu: whole pipeline or specific tools

Read this file when Stage 00 asks how the researcher wants to use ELARA, when
the researcher says `tools` or `menu`, when a stage or utility is invoked out
of sequence, and at the end of any tool run in a project whose `usage` is
`tools`. Present the choice and the menu in plain language, grouped as below,
with the invocation for the active host (`/elr-...` in Claude Code, `$elr-...`
in Codex). Never paste the whole file at the researcher: name the groups, offer
to expand one, and ask for one choice at a time. A researcher may pick several
tools and run them in any order.

## The two ways to use ELARA

- **Whole pipeline (`usage: pipeline`).** ELARA walks one project through every
  stage from question to verified replication package, with the optional
  publication stages, one bounded stage at a time, stopping at each gate for the
  researcher's decision. Choose this for a new empirical project (fresh path) or
  to bring an existing project under ELARA's verification from some point on
  (adoption path). It is the default when the researcher is unsure.
- **Specific tools (`usage: tools`).** The researcher picks stages or utilities
  from the menu and ELARA runs only those, on the researcher's own materials,
  recording what it verified and what it took on the researcher's word. Choose
  this to cite-check or proofread a draft, apply hand markup, add citations,
  check a project idea for preemption, get an adversarial review of a design,
  pilot a coding instrument, validate coded data against human coders, and so
  on. The researcher can switch to the whole pipeline at any time; the switch is
  a recorded decision.

Say plainly what the choice does not change: every gate still belongs to the
researcher; nothing is sent to a hosted model before the researcher authorizes
it; audit tools report and never silently repair.

## Menu

Descriptions are for the researcher; the canonical instructions are the files
named in the last column, which the tool wrapper reads in full.

### Manuscript tools — work on any draft; no earlier stage is needed

| Tool | What it does | You supply | Canonical file |
|---|---|---|---|
| `elr-proofread` | Reads the draft as a careful proofreader: typos, grammar, clarity, tone, style tells, internal consistency, venue format. Reports; fixes only clear errors, and only if you say so. | the draft (`project/inputs/manuscript/`), optionally a publication profile | `workflow/utilities/proofread.md` |
| `elr-add-citations` | Finds, retrieves, reads, and adds only the citations you marked as needed, in your citation style; changes nothing else; then re-audits. | the draft with marked passages, the citation style or a profile | `workflow/utilities/add-citations.md` |
| `elr-apply-markup` | Transcribes your hand markup on a PDF into a list of proposed edits, stops for your corrections, then applies exactly the approved edits to a new version. | the draft and the marked-up PDF (`project/inputs/manuscript/markup/`) | `workflow/utilities/apply-markup.md` |
| `elr-18-cite-check` | Audits every citation against the retrieved source: does the source exist, say that, and support the proposition? Reports dispositions; repairs nothing. | the draft, your bibliography or source files, database access if any | `workflow/stages/18-cite-check.md` |
| `elr-19-revise-and-respond` | Revises the manuscript in response to reviewer or editor comments or your own notes, with a response matrix and a full change disclosure, after you approve the plan. | the draft and the letters or notes | `workflow/stages/19-revise-and-respond.md` |
| `elr-17-integrate-manuscript` | Integrates verified results (numbers, tables, figures) into a manuscript you drafted; never writes the first draft. | your draft and the results (analysis outputs, ideally an ELARA replication package) | `workflow/stages/17-integrate-manuscript.md` |

### Getting a project off the ground

| Tool | What it does | You supply | Canonical file |
|---|---|---|---|
| `elr-01-conceive` | Builds a researcher profile and a ranked, source-checked shortlist of candidate projects; you select. | prior papers, a CV, research notes (optional) | `workflow/stages/01-conceive.md` |
| `elr-02-preemption-review` | Searches and reads the literature to say whether the project is preempted and where the contribution lies. | the question and claimed contribution | `workflow/stages/02-preemption-review.md` |
| `elr-03-feasibility-audit` | Live probes of data access, cost, time, and risk before you commit. | the question and candidate corpus locations | `workflow/stages/03-feasibility-audit.md` |

### Designing the study

| Tool | What it does | You supply | Canonical file |
|---|---|---|---|
| `elr-04-methods-design` | Hypotheses, estimands, sampling, measurement, validation, and analysis plan, for your approval. | the question, a preemption review or your memo | `workflow/stages/04-methods-design.md` |
| `elr-05-codebook-and-schema` | A frozen codebook with edge cases and an `uncertain` route, a machine-readable schema, and a closed unit space. | the methods plan or a description of what is to be coded | `workflow/stages/05-codebook-and-schema.md` |
| `elr-06-data-authorization` | Walks through license, terms, confidentiality, IRB or ethics, and the hosted-model route, and records your authorization. | the corpus source and its governing terms | `workflow/stages/06-data-authorization.md` |
| `elr-07-adversarial-review` | Independent critiques of the design, an issue disposition, and a frozen revised design. | the design documents (methods, codebook, schema, prompt) | `workflow/stages/07-adversarial-review.md` |
| `elr-08-pilot` | Pilots the whole coding pipeline on a small authorized sample and reviews disagreements. | the frozen design and an authorized sample | `workflow/stages/08-pilot.md` |
| `elr-09-freeze-and-preregister` | Hash-pins the design and prepares the preregistration and external record. | the frozen design and pilot acceptance | `workflow/stages/09-freeze-and-preregister.md` |

### Building the data

| Tool | What it does | You supply | Canonical file |
|---|---|---|---|
| `elr-10-corpus-acquisition` | Assembles the corpus with provenance and integrity checks and typed gaps. | the authorized source and scope | `workflow/stages/10-corpus-acquisition.md` |
| `elr-11-scale-up` | Codes the full corpus, one unit per fresh context, resumable and verified. | the corpus and the frozen codebook, schema, and prompt | `workflow/stages/11-scale-up.md` |

### Checking the data

| Tool | What it does | You supply | Canonical file |
|---|---|---|---|
| `elr-12-interpretive-verification` | Independent audit that each code is supported by the evidence it cites; a recoding queue for the rest. | coded data, the corpus, the codebook | `workflow/stages/12-interpretive-verification.md` |
| `elr-13-human-validation` | Held-out sample, blinded coder materials, adjudication, and error metrics against human coding. | coded data and the codebook (and your coders) | `workflow/stages/13-human-validation.md` |

### Analysis and replication

| Tool | What it does | You supply | Canonical file |
|---|---|---|---|
| `elr-14-analysis-and-correction` | Deterministic analysis with diagnostics and measurement-error correction from the validation results. | coded data, validation results, the analysis plan | `workflow/stages/14-analysis-and-correction.md` |
| `elr-15-robustness` | Prompt-paraphrase and second-model stability checks; reports instability rather than hiding it. | coded data and the codebook and prompt | `workflow/stages/15-robustness.md` |
| `elr-16-replication-package` | Builds a package that rebuilds every number with one command and verifies it in a fresh context. | analysis code, data, and results | `workflow/stages/16-replication-package.md` |

`elr-00-initialize` is the setup stage itself and `elr-code-observations` is the
per-unit fan-out helper that Stages 08, 11, 12, and 15 use; neither is a menu
choice.

## Running a tool on its own

A stage run out of sequence still follows its canonical file; what changes is
how its prerequisites are met. Stage 00's **tools path** does the setup:

1. **Quick setup, once per workspace** (two questions: a short project name and
   one sentence on what the researcher wants done): state, ledgers, access
   snapshot, input inventory, run manifest, and a workspace charter that records
   the purpose and the tools chosen. `usage` becomes `tools`. The researcher's
   yes to the two-line summary is the charter approval, recorded verbatim.
2. **A manuscript utility** then runs directly from its canonical file; it asks
   for the draft and, if none is pinned, the publication profile.
3. **A stage** first gets what it needs: the agent names the stage's required
   inputs in plain language, the researcher supplies files (copied, never moved,
   into `project/inputs/existing/`) or says which do not exist, and the agent
   imports and pins them, records the earlier gates the researcher asserts
   (basis `researcher-asserted`, quoting the researcher, with a one-sentence
   explanation that ELARA takes the work behind those gates on the researcher's
   word and will say so in its reports), writes or extends the adoption map
   (`partial`, `not run by ELARA`, or `not applicable` for the rest), appends
   the standing deviation, sets `current_stage` to the chosen stage, and runs it
   exactly as the router would.
4. **Afterwards** the stage records its normal transition, but the handoff
   returns to this menu instead of starting the next stage. In a later session,
   `resume`, `tools`, or `menu` reopen the menu; naming a tool runs it.
5. **Switching to the whole pipeline** is a recorded decision: `usage` becomes
   `pipeline` and the router continues from `current_stage`, running the
   adoption path first if more needs importing.

Nothing about the tools path relaxes a rule: gates are still recorded, audit
stages still only report, hosted-model processing still waits for
authorization, and the replication package still says which checks ELARA
performed and which rest on the researcher's word.
