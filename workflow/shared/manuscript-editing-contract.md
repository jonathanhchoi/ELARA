# Manuscript-editing contract

These rules apply whenever ELARA touches a researcher's manuscript: Stage 18
(integration), Stage 20 (revision and response), and the manuscript utilities in
`workflow/utilities/` (`add-citations`, `proofread`, `apply-markup`). They are
invariants under `guardrails.md` §10: a stage, utility, or publication profile
may add requirements but never relax them. What to integrate, how to map
comments, and when to re-audit stay in the stage or utility file.

## 1. Authorship boundary

- ELARA does not write the substantive first draft, turn notes into a paper, or
  supply an original thesis, argument, or normative claim. Stage 17 may propose
  an article structure, verified results displays, and the minimal methods and
  results prose needed to read them; the researcher writes the rest. Manuscript
  stages work only on a substantive draft the researcher supplies.
- An approved Stage 17 skeleton is planning context, not prose. Bounded
  insertions the researcher requests in their own draft (a paragraph, caption,
  transition, citation) are permitted but never license broadening the article.

## 2. Permission and versioning

- Inspect first, read-only, and present the proposed edits. No manuscript,
  bibliography, figure, or analysis file changes before the researcher approves
  the concrete plan and grants `manuscript-edit-permission` (or the utility's
  narrower permission), which covers only the listed edits, files, and versions.
- Never edit a file under `project/inputs/` or an earlier manuscript version.
  Work on a new versioned copy in the declared output directory and keep the
  source for diffing.

## 3. Publication profile

- Before planning prose changes, read the active profile
  (`active_artifacts.publication_profile`, a `project/PUBLICATION_PROFILE_vNNN.md`
  from `workflow/templates/publication_profile_template.md`) and record its path,
  version, and SHA-256 in the run manifest. With no active profile, ask the
  researcher to supply one or to record a decision to match the draft's voice;
  never invent venue, audience, tone, exemplars, or QA requirements.
- Precedence: guardrails and this contract; the researcher's task instruction;
  the profile; the draft's voice; the kit default (match the draft, change as
  little as possible). Profile text that would relax a guardrail, gate,
  evidence rule, or audit separation is void; say so.

## 4. Editing discipline

- Make the narrowest change that accomplishes the approved task. Keep the
  draft's language where it already makes the point; do not alter legal terms,
  quotations, defined labels, or hypotheses unless the task says so. Match the
  draft's voice and keep abstract, body, conclusion, appendices, captions,
  tables, figures, and disclosures consistent, updating dependent passages and
  numbers together.
- Take every number, count, estimate, interval, table, and figure from the
  active machine-readable results; never retype from memory, read a value off a
  plot, or use a superseded result.
- Reuse only citations supported by retrieved sources. Retrieve and read an
  authority before adding or recharacterizing it; otherwise record a
  citation-needed finding for Stage 19. Never complete a citation from memory.
- One serial writer edits the manuscript, response, ledger, and shared files.

## 5. Build, review, and disclosure

- Build with the manuscript's real build system and inspect the log and the
  rendered output (references, figures, overflow, bibliography, pagination;
  every page when the profile requires it), fixing only in-scope issues.
- Record two self-review passes: the approved instructions were followed and
  every claim and number traces to artifacts; then a comparison against the
  source and plan for out-of-scope, undisclosed, or inconsistent changes.
- Produce a change log naming every altered file and substantive edit and every
  requested change not made and why, a diff against the source, and a redline
  (for example `latexdiff`) when the profile asks. Make no undisclosed changes.
- Any manuscript edit invalidates the prior citation audit: route the edited
  version through an audit-only Stage 19 pass before calling it final.
