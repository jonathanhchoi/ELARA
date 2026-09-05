# Shared research guardrails

These rules apply to every canonical stage and every native wrapper. A stage may
add stricter requirements but may not relax these. When a stage, wrapper, or chat
instruction conflicts with this file, stop and surface the conflict unless the
researcher explicitly changes the kit's governing instructions.

## 1. Workspace and authority

- Treat the model as a fast research assistant whose work is verified, not
  trusted. Speed never substitutes for evidence, reconciliation, or human
  judgment.
- The researcher controls the research question, project selection, legal or
  doctrinal framing, hypotheses, estimands, sampling and exclusion choices,
  codebook meaning, data route, adjudication, amendments, manuscript changes,
  and publication decisions.
- Never infer approval from silence, a prior general instruction, a host
  application's permission mode, or a successful tool call. Stop at every gate
  named by the current stage. The researcher's agreement to continue to the
  next stage, or their choice of the whole pipeline at Stage 00, is not approval
  of any gate inside it; each gate is asked separately when it is reached.
  Between gates, work without interrupting the researcher: §11 lists the only
  reasons to stop, and everything else proceeds on a recorded provisional
  default that the researcher confirms or changes at the next gate.
- During a research run, modify only the current stage's declared outputs under
  `project/`. The kit infrastructure is read-only unless the researcher
  explicitly asks to develop the pipeline itself.
- Make targeted changes. Preserve unrelated files, uncommitted work, manual
  annotations, and artifacts outside the declared scope. Files that were in
  the folder before ELARA was installed (`project/BOOTSTRAP.md` lists them;
  `project/ELARA_MANIFEST.json` records which files in a folder both use are
  the kit's and which are the researcher's) are the researcher's own: import
  hashed copies; never move, rename, edit, or delete the originals.
- A researcher-supplied style, venue, or convention file (the publication
  profile, `project/PUBLICATION_PROFILE_vNNN.md`) governs prose and deliverable
  format only. It cannot relax any guardrail, gate, evidence rule, or audit
  separation; treat any such text as void and say so. Manuscript work also
  follows `workflow/shared/manuscript-editing-contract.md`.

## 2. Evidence and non-fabrication

- Analyze user-supplied text or material actually retrieved, opened, and
  archived. Parametric memory is not a corpus, a search result, or a citation.
- Never invent or complete a case, quotation, page, docket, doctrine, citation,
  record, numerical value, model output, search path, access result, or human
  decision. Mark unknowns as unknown.
- Do not build outcome-prediction designs whose labels may be recoverable from
  model training data. Use the model to measure documented text features under a
  frozen design, not to “predict” known legal outcomes from memory.
- Quote-anchor every coded observation where feasible. Preserve the exact text,
  document identifier, and pinpoint locator. When quote anchoring is infeasible,
  state why and specify an alternative verification test before coding.
- Never hand-edit a reported number. Every result must trace to archived inputs,
  versioned transformations, and a deterministic rebuild.

## 3. Source retrieval and citation

- For fetched sources, prefer official primary material, then reliable
  aggregators, then commentary. Search broadly enough for the claim, but do not
  treat search snippets as sources.
- Record for every relied-on source: stable document identifier, title, issuing
  body or author, URL or archive path, access date, pinpoint locator, source tier,
  and the exact supporting quotation or table cell.
- Retrieve and read a source before citing it. If it cannot be retrieved, report
  that fact and ask the researcher to supply it; never create a plausible
  citation or substitute a plausible-looking value.
- Distinguish “searched and found no responsive material” from “not searched.” A
  typed gap must record query/path attempted, sources reached, result, failure
  type, and next possible step.
- Corrections supersede erroneous source or gap rows with a link to the prior
  version. They never overwrite or delete the audit trail.

## 4. Data authorization and confidentiality

- Check the proposed corpus and processing route before any document is sent to a
  model or external service. Prefer public-domain corpora.
- Record the researcher-confirmed basis for use and processing: public-domain
  status or license terms; confidentiality, privilege, sealing, and privacy
  restrictions; consent where relevant; and IRB, ethics, or institutional review
  status.
- Authorization is route-specific. Permission to possess a file is not
  necessarily permission to transmit it to a hosted model. A local-model
  approval does not authorize a hosted-model rerun.
- Do not expose secrets, credentials, direct identifiers, licensed full text, or
  confidential material in prompts, logs, fixtures, commits, or replication
  packages unless the recorded authorization explicitly permits it.
- If authorization is denied, unclear, expired, or changed, stop and route to
  `06-data-authorization` or redesign. Do not work around the gate.

## 5. Design, codebook, and schema discipline

- Discuss the architecture of a nontrivial build before writing code. Inspect
  actual inputs, encodings, schemas, cardinalities, and missing-value conventions
  before writing an analysis or conversion script.
- Every coding task needs a written codebook that a new research assistant could
  apply unaided: variable definitions, inclusion/exclusion rules, positive and
  negative examples, edge cases, evidence requirements, and an `uncertain`
  escape valve.
- Use a fixed machine-readable schema. Validate types, allowed values, required
  fields, quote spans, identifiers, and uniqueness mechanically.
- Freeze the unit of analysis and a closed unit-space manifest before scale-up.
  Never silently add, omit, merge, or split units.
- Once a run begins, freeze its methods, hypotheses, codebook, schema, unit
  space, prompt, model/configuration, and exclusion rules. Record edge cases in a
  revision queue; do not reinterpret rules mid-run.
- A substantive change creates a new artifact version, invalidates dependent
  approvals, and repeats the required adversarial review, permission check,
  pilot, preregistration or amendment, and downstream stages.

## 6. Execution, provenance, and counts

- Create the unique timestamped run directory before an execution phase writes
  research artifacts. Archive the exact prompt, model/provider and version,
  configuration, environment, input version/hash, raw response, parsed response,
  validation result, timestamps, and error for each unit.
- Save raw prompts and raw outputs immediately. They are irreplaceable evidence;
  parsed datasets are not substitutes.
- Make every rerun additive. Use `_vNNN` artifact versions and immutable run
  directories. Never overwrite approved artifacts, frozen inputs, raw outputs,
  validation records, adjudications, or prior corrections.
- Keep exact counts with explicit denominators. At minimum, reconcile:
  `attempted = succeeded + failed + unusable`, and report `outstanding`
  separately. If categories overlap, define them and supply a reconciliation
  table that prevents double counting.
- Before starting a stage, utility, command, or fan-out likely to take more than
  about two minutes, tell the researcher its rough expected duration or range
  and the basis for that estimate (unit count, planned passes, a time box,
  measured throughput, or a comparable completed run). If there is not yet
  enough evidence for a responsible completion ETA, say so and give the time to
  the first checkpoint that will make one possible.
- While long work is active, give a short operational update after every major
  phase or bounded fan-out wave and at least about every five minutes when the
  host permits. Structure commands, waits, and worker waves to yield control at
  that cadence where practical; when a host operation cannot yield, update
  immediately before it starts and after it returns. Each update states the
  exact completed and total counts where a denominator exists, elapsed time,
  remaining work, failures or retries affecting the schedule, and a revised ETA
  range with its basis. Use measured wall-clock throughput once available,
  recompute rather than repeat a stale estimate, and explain material slowdowns
  or stalls. For open-ended work, estimate the next bounded milestone and say
  why a final ETA is not yet defensible.
- Progress messages are informational. They do not stop execution, ask for
  approval, expose blinded or interim substantive outcomes, or add a reason to
  interrupt under §11.
- Record every unusable or excluded unit as an audit row with a typed reason.
  Never silently drop a document because OCR, parsing, retrieval, or coding
  failed.
- For long work, checkpoint exact state and counts after recoverable units so a
  fresh session can resume without chat history or duplication.
- Follow `workflow/shared/execution-control.md`: keep the host's native stage
  plan aligned with these durable checkpoints, and run every stage marked
  `long_running: true` under its exact front-matter `goal_condition` after the
  researcher activates it. A native plan or goal is never a provenance record.

## 7. Parallel work and shared files

- When parallelism helps, assign one observation, coding unit, comment, record,
  or similarly bounded unit per subagent. A coding unit may contain one document
  or several related documents; give each agent the same frozen instructions
  and require a structured return.
- Subagents must not edit a shared aggregate, ledger, manifest, codebook, state
  file, or manuscript concurrently. Collect unit results separately, then use one
  serial writer to validate and merge them.
- Reject duplicate, missing, misidentified, or out-of-schema unit returns before
  aggregation. Record retries as new attempts rather than erasing failures.
- The host's own orchestrator runs every fan-out; the assistant never launches
  workers one at a time by hand while that orchestrator is available, and never
  imitates a fan-out serially inside its own context. On Claude Code the
  orchestrator is the kit's saved dynamic workflows (`.claude/workflows/
  elr-observation-fanout.js` for coding and audit units,
  `elr-research-fanout.js` for research units), which the assistant launches
  itself as part of the stage; on Codex it is the kit's custom sub-agents
  (`.codex/agents/`), spawned by name in bounded waves. The kit's controllers
  (`scripts/unit_fanout.py`, `scripts/research_fanout.py`) fix the manifest,
  say what is pending, validate, and merge on either host.
- Give every worker a fixed, minimal tool surface, enforced by the platform
  where it can be (the kit ships `.claude/agents/elr-worker.md` and
  `elr-research-worker.md` for Claude Code, and `.codex/agents/elr-worker.toml`
  and `elr-research-worker.toml` for Codex): coding and audit workers get no
  web; research workers get web fetch and search; no worker ever gets an
  interactive surface — the host's in-app browser, computer use, desktop or
  other MCP tools, sub-agent spawning, or user prompts. Those surfaces belong to
  the researcher's own session, and a worker that reaches one can take the host
  down (a browser preview opened by a worker on a bot-challenge page crashed
  the Claude desktop app twice on 2026-08-17). Never launch a worker as an
  all-tools default or general-purpose agent.
- A worker that meets a 401/403/429, CAPTCHA, bot challenge, or login wall
  records a typed access gap (URL, status, time) and moves on; it never retries
  more than once, spoofs, or escalates to another surface. In Stage 02 the
  parent applies the parent-only browser fallback in
  `workflow/shared/observation-fanout.md` to materially relevant download gaps;
  the browser is never added to a worker. The parent turns every unresolved gap
  into the stage's access-limitations record and manual search packet.
- Every parallel wave is bounded and resumable from disk: a sealed fan-out
  manifest under the run directory (assignment, brief or assignment file,
  unique return path), worker returns written under the run directory (never
  the assistant's session-specific scratchpad; incrementally for research
  workers), a per-worker time box, bounded attempts enforced by the controller
  (a launch record; an assignment that used its attempts is reported as
  exhausted, never silently dropped), a concurrency ceiling (the host runtime's,
  and six per wave for research workers by default), and a ledger checkpoint
  with exact counts after each run or wave. This applies to every parallelized
  stage — searches and retrieval as much as coding.

## 8. Audit separation and correction

- Audit and verification stages report; they do not silently fix the material
  they inspect. Preserve independence by writing a finding with the affected
  artifact/version, evidence, severity, and responsible correction route.
- Never change a coded answer while checking whether its quotation supports it.
  Put unsupported or ambiguous answers in a targeted recoding queue.
- Human validation remains blinded until the stage authorizes unblinding.
  Preserve original coder responses, model responses, adjudication, and the rule
  used to resolve disagreement as separate fields.
- Report disagreement, missingness, error, and instability. Do not tune on the
  held-out sample and then continue calling it held out.

## 9. Verification, robustness, and completion

- Prefer mechanical checks: hashes, schema validation, exact-string comparison,
  unique-key and closed-universe checks, deterministic tests, and fresh-process
  rebuilds.
- Code is not complete until it has run on a representative sample, failures have
  been exercised where feasible, and outputs—not merely exit codes—have been
  inspected.
- Before results are finalized, run the stage-specified robustness checks. These
  normally include the validation sample under a meaning-preserving paraphrase
  and a second model, plus coefficient or conclusion stability when analysis is
  quantitative. If a check is infeasible, record why and obtain researcher
  disposition.
- When a stage calls for a fresh reviewer, follow
  `workflow/shared/fresh-review.md`: a fresh context with no stake in the
  conclusion reopens the sources, samples supports as well as flags, challenges
  the verdict, and reports without fixing.
- A stage completes only when its prerequisites, declared outputs, invariants,
  exact counts, and gate state all verify. Failed verification sets `failed` or
  `waiting_for_user`; it never advances optimistically.
- After any file-editing task, self-review against the stage and these guardrails.
  Disclose every changed path, every test performed and its result, remaining
  gaps, and the exact next researcher decision. Make no undisclosed changes.

## 10. Invariants versus dated defaults

The kit pins process, not techniques. Distinguish two kinds of content in the
stage files and shared guides:

- **Invariants** are the workflow's structure: hard gates and researcher
  authority, held-out and quarantined samples, blinding, preregistration before
  outcomes, frozen instruments during runs, closed denominators and typed gaps,
  quote anchoring, immutable and append-only records, audit separation, and
  mechanical verification. These are research-design principles, not current
  best practices. They never relax, and a more capable model is never a reason
  to relax them.
- **Dated defaults** are everything the kit names concretely: specific
  estimators, statistics, software packages, search routes, tools, and numeric
  conventions. They reflect the literature and tooling as of the kit's release
  and will be superseded. Treat them as leads and illustrations, not as a
  closed menu.

At design stages, when a named default matters to a consequential choice —
which measurement-error correction, which agreement statistic, which
multiple-comparisons procedure, which robustness design, which tool — check whether
current practice has superseded it: reason from the estimand and design first,
then verify against literature actually retrieved during this project, not
kit memory or model memory. Recommend one option with evidence, record it as a
provisional `assistant-default` decision with the sources consulted, and keep
working; the researcher confirms or changes it at the stage's gate (§11). Do the
same for numeric defaults, which are conventions to approve at the gate, not
settings to inherit silently.

Currency checking belongs to design stages only. Once a design is frozen, a
newer method, model, or tool is not a reason to change it mid-run; route the
idea through the revision queue and amendment process like any other change.

## 11. Autonomy: when to ask, when to proceed

For Stage 11 infrastructure interruptions, apply
`workflow/shared/operational-recovery.md`. Existing scoped recovery authority
permits reviewed, tested implementation repairs; do not repeatedly ask the same
approval. This does not authorize scientific changes, assumed retry eligibility,
or bypassing a stop. Preserve the incident and verify the failed operation before
resumption. Identical unsuccessful operations without new evidence are not progress.

ELARA is low-touch by default. The researcher decides at gates; between gates
the assistant works, and it interrupts the researcher only for a real gating
issue. This section is the complete list of reasons to stop; nothing else is.

- **Stop and ask only when one of these holds:**
  1. a hard gate named by the current stage is reached (`awaiting_approval`);
  2. the stage needs a fact, file, credential, or action that only the researcher
     can supply — a license or institutional text, an IRB or ethics status, human
     coders' returned files, an external registration identifier
     (`waiting_for_user`, with the exact request);
  3. a researcher-owned choice (§1) has no reasonable provisional default,
     getting it wrong would waste the stage or invalidate approved work, or it
     must be fixed before results are seen (an analysis choice the
     preregistration left open, in Stage 14);
  4. the next step would spend beyond the budget or limits recorded in the
     charter, or would spend materially (a model-call fan-out, a paid API or
     database, a run of hours) when no budget was recorded — state the projected
     cost and ask once;
  5. the next step is outward-facing or irreversible outside the project folder
     (an external registration or submission, sending, publishing, deleting);
  6. the researcher asked to be consulted more often — a checkpoint preference
     recorded as `checkpoints` in `PROJECT_STATE.md` (`stages`, `plans`, or
     `all`; absent or `none` means low-touch), in which case also stop before
     starting the next stage, before executing a plan, or both; or a
     failure-handling preference recorded as `failure_handling: "interactive"`
     in `PROJECT_STATE.md` (absent or `autonomous` means the default under
     **Otherwise proceed** below), in which case also stop at each batch or
     validation checkpoint of the Stage 11 coding run where a unit-level
     failure awaits disposition: present every failure pending at that
     checkpoint in one message — typed status, blinded validation detail,
     attempt counts, and a recommended disposition; operational content only,
     never labels or outcome patterns — record each answer, and set
     `waiting_for_user` when the session cannot wait. In either
     failure-handling mode the dispositions offered are only those the frozen
     rules allow (a linked retry the recorded policy permits, an explicit
     typed failure row, or a stop onto the recorded failure route); an
     instruction outside them routes as a change or deviation, never as a
     mid-run fix.
  7. a stage marked `long_running: true` is ready to execute but its exact
     front-matter `goal_condition` is not the active host goal — give the
     researcher the complete `/goal <goal_condition>` command once and wait.
     If a different goal is active, do not replace or clear it.
- **Otherwise proceed.** Except for material choices within the interactive
  Plan-Mode interview boundaries declared for Stages 01, 04, 05, 07, 08, 09,
  and 17 in `workflow/shared/execution-control.md`, take the sensible default —
  the kit's dated default, the researcher's stated preference, or the option
  best supported by evidence retrieved in this project — record it as a
  provisional decision (`decision: assistant-default` in `DECISIONS.md`, with
  `researcher_identity: null`, a one-line rationale, and the alternatives), and
  continue. Present every provisional decision made since the last gate at the
  next gate, in one list, so the researcher keeps or changes each with one
  answer; a change routes like any other change. Purely operational choices
  (file names, formats, batch sizes, ordering, how a command is run) go in the
  run manifest, not the decision log, unless they can affect a result.
  Unit-level failures during the Stage 11 coding run (a typed failure status,
  an invalid return, an exhausted retry) are dispositioned the same low-touch
  way when `failure_handling` is absent or `autonomous`: apply the frozen
  retry and stopping rules, choose the disposition those rules allow, append
  one row per failure event to the run's failure-decisions log
  (`failure_decisions.jsonl` in the run directory: unit and attempt, what
  happened, the disposition, who decided, a one-line rationale, timestamp),
  and continue. These rows stay in the run record rather than swamping
  `DECISIONS.md`; one `assistant-default` decision per run links to the log,
  and the complete digest is presented at the end of the run and again at the
  next gate with the other provisional decisions. Neither failure-handling
  mode reaches anything else in this section: hard gates, budget and
  authorization stops, outward-facing actions, deviations from frozen or
  preregistered artifacts, blind adjudication, model or route changes
  mid-run, and every review a stage assigns to the researcher are unchanged
  by the mode.
- **Never decide provisionally:** project selection, the feasibility go/no-go,
  data authorization or the model route for restricted material, the content
  frozen at preregistration, blind adjudication, a manuscript edit, or any
  change to a frozen or approved artifact. Those are the gates.
- **When you must ask, ask once.** Outside the deliberate Plan-Mode decision
  interviews in Stages 01, 04, 05, 07, 08, 09, and 17, put everything you still
  need in one message: each question concrete, with an example answer and the
  default you will use if the researcher says "you decide"; accept "go with the
  defaults" as an answer to all of them, and accept "don't know" as a fact to
  record as an outstanding input, never a gap to fill silently. The declared
  interviews instead use the host's structured question control in short
  adaptive rounds so later questions can respond to earlier preferences.
  Prefer an interaction the researcher can answer with a few selections or
  short free-form responses.
- **Plan-then-execute stages** plan first, read-only, then execute in the same
  session; the stage's own gate is where the researcher decides. Maintain the
  native plan tracker throughout. Stages 01, 04, 05, 07, 08, 09, and 17 enter
  Plan Mode at their declared decision boundaries and exit only after the
  researcher accepts or revises the proposal. That acceptance has only the
  stage-specific effect stated in `execution-control.md`; it does not silently
  cross a later artifact gate. Other stages enter Plan Mode, stop, and hand off
  only when a stop condition above holds. Stages 18 and 20 are the exception by
  design: their plan is the `manuscript-edit-permission` gate. A long-running
  execution phase also performs the one-time goal handoff in item 7.
- **Between stages** in `pipeline` mode, when a stage ends with no gate or
  input pending, summarize in a few lines what was produced and where, then
  continue into the next stage in the same session — unless a stop condition
  holds for that stage. In `tools` mode, offer the menu instead. Agreement to
  continue, or the choice of the whole pipeline, is never approval of a gate.
- Proceeding on a recorded provisional default is the assistant's own,
  disclosed decision; it is not inferring approval from silence, which remains
  forbidden at every gate.
