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
- During a research run, modify only the current stage's declared outputs under
  `project/`. The kit infrastructure is read-only unless the researcher
  explicitly asks to develop the pipeline itself.
- Make targeted changes. Preserve unrelated files, uncommitted work, manual
  annotations, and artifacts outside the declared scope. Files that were in
  the folder before ELARA was installed (`project/BOOTSTRAP.md` lists them)
  are the researcher's own: import hashed copies; never move, rename, edit, or
  delete the originals.
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
- Record every unusable or excluded unit as an audit row with a typed reason.
  Never silently drop a document because OCR, parsing, retrieval, or coding
  failed.
- For long work, checkpoint exact state and counts after recoverable units so a
  fresh session can resume without chat history or duplication.

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
multiplicity procedure, which robustness design, which tool — check whether
current practice has superseded it: reason from the estimand and design first,
then verify against literature actually retrieved during this project, not
kit memory or model memory. Present the options with evidence and record the
researcher's decision and the sources consulted. Do the same for numeric
defaults, which are conventions to approve, not settings to inherit silently.

Currency checking belongs to design stages only. Once a design is frozen, a
newer method, model, or tool is not a reason to change it mid-run; route the
idea through the revision queue and amendment process like any other change.
