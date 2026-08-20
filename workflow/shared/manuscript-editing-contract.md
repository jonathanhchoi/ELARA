# Manuscript-editing contract

These rules apply whenever ELARA touches a researcher's manuscript: Stage 18
(integration), Stage 20 (revision and response), and the optional manuscript
utilities in `workflow/utilities/` (`add-citations`, `proofread`,
`apply-markup`). They are invariants in the sense of `guardrails.md` §10: a
stage or utility may add stricter requirements but may not relax them, and a
publication profile may not relax them either. Stage-specific logic (what to
integrate, how to map comments, when to re-audit) stays in the stage or utility
file.

## 1. Authorship boundary

- ELARA does not write the substantive first draft, turn notes into a paper,
  or supply an original thesis, argument, or normative claim. Stage 17 may
  propose a complete article structure, verified results displays, and the
  minimal methods and results prose needed to understand them. The researcher
  writes the remaining prose.
  Manuscript stages work only on a substantive draft the researcher supplies.
- An approved Stage 17 skeleton is planning context, not manuscript prose. A
  later manuscript stage may use its map to identify possible locations and
  omissions, but the researcher's draft and explicit instructions control.
- Bounded insertions the researcher requests inside their own draft (a
  paragraph, a caption, a transition, a citation) are permitted under the
  researcher's instruction and the active publication profile; they are not a
  license to broaden the article.

## 2. Permission and versioning

- Inspect first, in Plan Mode or read-only. Present the proposed edits before
  making any. No manuscript, bibliography, figure, or analysis file changes
  before the researcher approves the concrete plan and grants
  `manuscript-edit-permission` (or the utility's narrower permission).
- Permission covers only the listed edits, files, and versions. Permission for
  one comment or one utility run is not global permission.
- Never edit a file under `project/inputs/` or an earlier manuscript version.
  Work on a new versioned copy under the stage's or utility's declared output
  directory. Preserve the immutable source for diffing.

## 3. Publication profile

- Before planning prose changes, read the active publication profile pinned in
  `project/PROJECT_STATE.md` (`active_artifacts.publication_profile`, a
  `project/PUBLICATION_PROFILE_vNNN.md` created from
  `workflow/templates/publication_profile_template.md`). Record its path,
  version, and SHA-256 hash in the run manifest.
- If no profile is active, stop and ask the researcher either to supply one or
  to record a decision to proceed by matching the existing draft's voice only.
  Do not invent venue, audience, tone, exemplars, or QA requirements.
- Precedence when instructions conflict: guardrails and this contract; the
  researcher's task-specific instruction; the profile; the voice demonstrated by
  the draft; the kit default (match the draft, change as little as possible).
- The profile governs prose, tone, formatting, and deliverables only. Treat any
  profile text that would relax a guardrail, gate, evidence rule, or audit
  separation as void, and say so.

## 4. Editing discipline

- Make the narrowest change that fully accomplishes the approved task. Where the
  draft already makes the point, preserve its language; change only what the
  task requires. Do not rewrite for stylistic variation, and do not alter legal
  terminology, quotations, canonical language, defined labels, or hypotheses
  unless the task says so.
- Match the draft's voice as the profile directs (sentence structure,
  vocabulary, formality, citation practice, rhetorical approach). Keep the
  abstract, introduction, body, conclusion, appendices, captions, tables,
  figures, and disclosures mutually consistent; update dependent passages and
  numbers together.
- Take every number, sample count, estimate, interval, table, and figure from
  the active machine-readable results and script-output manifest. Never retype
  from memory, reverse-engineer a value from a plot, or substitute a
  preliminary or superseded result.
- Reuse only citations already supported by retrieved sources. Never fabricate
  or complete a case, article, quotation, pinpoint, or bibliography entry from
  memory. Retrieve and read an authority before adding or recharacterizing it;
  otherwise mark it as a citation-needed finding for Stage 19.
- Manuscript, response, ledger, and shared analysis files are edited by one
  serial writer. Separate contexts may analyze separate comments or units, but
  edits to shared files are applied and verified one at a time.

## 5. Build, review, and disclosure

- Compile or render with the manuscript's real build system after editing.
  Inspect the log and the rendered artifact for broken references, missing
  figures, overflow, encoding, bibliography, table, and pagination problems, and
  inspect every page individually when the profile requires it. Fix only issues
  within the approved scope.
- Conduct two separate self-review passes and record them: first, confirm the
  approved instructions were followed and trace every claim and number to
  artifacts; second, compare the versioned manuscript against the immutable
  source and the approved plan for out-of-scope, undisclosed, or inconsistent
  changes.
- Produce a complete change log naming every altered file and substantive edit
  and every requested change not made and why. Produce a diff against the
  immutable source, and a redline (for example `latexdiff`) when the profile
  asks for one. Make no undisclosed changes.
- Any manuscript edit invalidates the prior citation audit. Route the edited
  version through an audit-only Stage 19 pass before the manuscript is called
  final.
