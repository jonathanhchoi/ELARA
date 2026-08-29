---
stage_id: "17-skeleton-draft"
title: "Create and approve the article skeleton"
paper_steps: ["6"]
core: false
interaction_profile: "plan_then_execute"
long_running: false
goal_condition: null
prerequisites: ["16-replication-package"]
required_inputs: ["project/PROJECT_STATE.md", "project/artifacts/preemption_review_vNNN.pdf (or the explicit researcher-selected alternative)", "project/artifacts/methods_plan_vNNN.md", "project/artifacts/hypotheses_vNNN.md", "project/artifacts/estimands_vNNN.csv", "project/artifacts/preregistration_vNNN.md", "project/artifacts/preregistration_record_vNNN.md", "project/artifacts/human_validation_report_vNNN.md", "project/artifacts/analysis_results_vNNN/", "project/artifacts/analysis_report_vNNN.md", "project/artifacts/robustness_results_vNNN/", "project/artifacts/robustness_report_vNNN.md", "project/artifacts/replication_package_vNNN/", "project/artifacts/replication_rebuild_report_vNNN.md", "project/DEVIATIONS.md"]
declared_outputs: ["project/artifacts/skeleton_draft_vNNN.pdf", "project/artifacts/skeleton_draft_vNNN.tex", "project/artifacts/skeleton_draft_vNNN.docx (only when explicitly requested)", "project/artifacts/skeleton_draft_vNNN.md (only when explicitly requested)", "project/runs/<run_id>/skeleton_draft_source.md", "project/runs/<run_id>/rendered_skeleton_draft/", "project/runs/<run_id>/run_manifest.json", "project/PROJECT_STATE.md", "project/DECISIONS.md", "project/RUN_LEDGER.md", "project/DEVIATIONS.md"]
human_gate: "skeleton-draft-approval"
next_stage: "18-integrate-manuscript"
failure_routes: ["02-preemption-review", "04-methods-design", "09-freeze-and-preregister", "13-human-validation", "14-analysis-and-correction", "15-robustness", "16-replication-package", "17-skeleton-draft"]
---

# Stage 17 — Create and approve the article skeleton

## Objective

Give the researcher an organizationally complete draft after the results and replication package are settled. It should show how the full article fits together and present the complete results primarily through verified tables, figures, and equations. Captions and notes should make those displays intelligible. The methods and results prose should be bare-bones, and the remaining article prose belongs to the researcher. The default is to create the skeleton. The researcher may instead skip this stage, but the skip must be recorded.

## Prerequisite checks

1. Read AGENTS.md, PROJECT_STATE.md, workflow/shared/guardrails.md, workflow/shared/artifact-contract.md, and workflow/shared/execution-control.md completely. Enter the native read-only Plan Mode for the Stage 17 decision interview below. This stage is bounded, so do not create a goal.
2. Confirm that Stage 16 completed and that the current replication package passed its clean rebuild and fresh-agent checks. Resolve every input from the exact versions recorded in state, not from a latest-file guess.
3. Load the accepted contribution and literature position, approved hypotheses and estimands, preregistration and record, validation report, analysis report and machine-readable results, robustness report and results, deviations, and replication manifest. Confirm that their artifact references and file hashes reconcile.
4. If an input is missing, inconsistent, or no longer supported, make no skeleton. Route to the stage that owns the problem and preserve the completed replication package.
5. Confirm that `scripts/build_skeleton_draft.py` and `workflow/templates/skeleton_draft_template.md` are present. For venue-aware Word output, also verify `workflow/templates/word/profiles.json`, the selected binary template, and its recorded SHA-256. Confirm that the local environment can compile LaTeX and render PDF pages. If the researcher expressly selected Word or Markdown, confirm that format's renderer or validator instead.

## Researcher decisions

Use the Plan-Mode interview below to elicit whether to create or skip the
skeleton and, if creating it, the output format, target venue, sections and
ordering, display strategy, organizational preferences,
counterarguments and limitations to foreground, and anything the researcher
wants emphasized. For Word, ask whether the submission is for a student-edited
law review, the Journal of Legal Analysis (JLA), or another outlet. Recommend
`law_review_v1` for a law-review submission and
`journal_of_legal_analysis_v1` only for JLA. For another peer-reviewed outlet,
retrieve and check that outlet's current official instructions; use a supplied
outlet template or obtain the researcher's express approval of a named fallback.
Never silently apply the JLA template to another outlet. Offer **create the skeleton draft** as the recommendation and
**skip** as the explicit alternative. State that the recommended output is a
LaTeX-generated PDF unless the verified environment or researcher preference
supports Word, Markdown, or another format. A response such as "go with your
recommendations" may accept the stated recommendations, but silence may not.

If the researcher skips, leave Plan Mode first, then append the decision with
gate ID `skeleton-draft-approval`, record `skipped` and the researcher's actual
words, set `current_stage` to `18-integrate-manuscript`, and set `status` to
`ready`. Do not create a run or skeleton file. Otherwise record the accepted
format and organizational instructions before opening a run.

## Mode handoff

Follow `workflow/shared/execution-control.md` and always begin Stage 17 in the
host's native read-only Plan Mode. Inspect the verified replication package,
publication profile, result and robustness inventories, available tables,
figures and equations, deviations, and any researcher drafting notes before
asking. Use Codex `request_user_input` or Claude Code `AskUserQuestion` for one
to three adaptive rounds covering the create-or-skip choice and, when creating,
format, venue, Word template and current official requirements where applicable,
sections and order, displays, emphases,
counterarguments, and limitations. For each consequential choice, show the
controlling evidence, put a reasoned recommendation first, offer realistic
alternatives and consequences, and allow free-form answers, "go with your
recommendations," and "I don't know."

Synthesize the answers into a reviewable, evidence-linked skeleton plan that
names the proposed organization, output format, display placements, emphases,
and author-reserved prose. Do not write any project file or create a run while
the interview remains in Plan Mode. After the researcher accepts the plan,
leave Plan Mode and continue into execution in the same session by creating a
run ID under the versioning rules in
`workflow/shared/artifact-contract.md`. Plan acceptance authorizes drafting the
described skeleton only; it does not approve the completed skeleton, begin
Stage 18, or turn later revision instructions into approval to advance.

## Work

1. Copy `workflow/templates/skeleton_draft_template.md` to the immutable run-scoped `skeleton_draft_source.md`. Replace every placeholder from the verified active artifacts and the researcher's organizational instructions. The source is the canonical representation for all output formats. For venue-aware Word output, set `word_template` to `law_review_v1` or `journal_of_legal_analysis_v1`; add `authors`, `running_title`, and `corresponding_author` when known. Missing author-owned facts remain explicit bracketed manuscript placeholders. Sources without `word_template` deliberately retain the legacy ELARA report design.
2. Propose descriptive sections and subsections in reading order. Make the structure complete enough to show the whole article, including the introduction, background or literature where appropriate, data and methods, results, robustness or validation where appropriate, limitations, discussion where appropriate, and conclusion.
3. For every section and subsection, state its role, bare-bones content, source support, displays, work left for the author, and open questions. Cite supporting material as `project/path#artifact-id`. Use `none` only when the field truly has no item. Reserve open questions for what the researcher must decide or notice.
4. Present every result from the active analysis and robustness inventories, including null and fragile findings. Use the verified tables and figures whenever available and include the estimating or identifying equations needed to understand the methods. Follow every equation immediately with text that defines each variable and term appearing in it. Supply concise captions and notes that define variables, samples, uncertainty, scales, panels, and specifications well enough to understand each display without additional prose.
5. Include every hypothesis, estimand, validation result, and preregistration deviation in the relevant section or flag it for the researcher's attention in that section's open questions. Do not omit a statistically inconvenient result or move it into a generic limitations note.
6. Write only enough methods and results text to orient the reader to the design, estimands, full findings, and supporting displays. Keep it factual and compact. Use only verified project artifacts and do not invent an explanation, authority, table, figure, equation, limitation, or contribution.
7. Outside methods, results, validation, and robustness, use `Author to write.` whenever possible. Do not compose an abstract, introduction, literature review, discussion, or conclusion. Researcher-approved thesis or contribution language may be reproduced exactly when useful and cited to its source.
8. Encode each display as `kind|project/path#artifact-id|caption`, using `table`, `figure`, or `equation` as the kind and ` || ` between displays. A figure may add a fourth field: `figure|project/path#artifact-id|caption|alt text`. Alt text is mandatory for JLA, is embedded accessibly in every venue-aware Word figure, and appears under the JLA figure legend as `Alt text:`. Tables must be verified CSV or TSV files, figures must be verified PNG or JPEG files, and equations must be verified TeX or text files. The builder places the actual display and its caption in each output format, and it renders an equation's caption as the text directly below the equation, so write that caption to define every variable and term.
9. Run the deterministic builder from the repository root, selecting the next unused artifact versions and matching the selected extension:

   ```text
   python scripts/build_skeleton_draft.py project/runs/<run_id>/skeleton_draft_source.md project/artifacts/skeleton_draft_vNNN.<docx|tex|md> --manifest project/runs/<run_id>/run_manifest.json --project-root .
   ```

10. By default, compile the generated LaTeX source with the available toolchain, save the PDF and logs under the run directory, render the complete PDF, and inspect every page at 100 percent zoom. For expressly requested venue-aware Word output, the builder loads the approved binary template, fills its title matter, uses the venue's heading and caption system, and records every planning field and display reference in the run manifest rather than the visible manuscript. Word comments are reserved for what needs the researcher's attention or action: a section with open questions receives one comment, anchored to its heading, containing only those questions. The visible file contains article headings, empirical text, displays, and concise bracketed author placeholders; it contains no ELARA branding, structure table, source bullets, or project paths. Update Word fields, including the law-review contents page, render the complete DOCX, and inspect every page at 100 percent zoom. For expressly requested Markdown, validate structure and links and inspect the whole file as text.
11. Give the researcher the versioned skeleton and keep Stage 17 active. Each requested change receives a new run-scoped source, output version, render directory, and run manifest. Never overwrite an earlier iteration.

## Artifacts

The Markdown source is preserved unchanged after the run and contains the canonical article structure, minimal methods and results content, display specifications, captions, and references to the source of each item. The default researcher-facing rendering is `skeleton_draft_vNNN.pdf`, compiled from `skeleton_draft_vNNN.tex`. DOCX, Markdown, or another supported format is used only when the researcher expressly selects it. The render directory contains page images, compiled PDFs where applicable, and inspection evidence. The record of a venue-aware Word run also states the template ID, repository path, SHA-256, requirements authority and check date, comments-to-sections mapping, every planning field, and figure alt text, in addition to the source and output values, exact format, verified source versions, display references, commands, tool versions, and review disposition.

Only the selected researcher-facing format is produced for a run. A later format change is a new version from a new source preserved unchanged, not an in-place conversion.

## Verification

- Run the builder's structure, required-role, field, provenance, placeholder, format, prose-limit, and overwrite checks.
- Confirm that headings are descriptive, ordered, and properly nested. Confirm that the structure includes the introduction, methods, results, limitations, and conclusion.
- Confirm every `project/path#artifact-id` reference resolves to an active or expressly retained project artifact and that every number or result label comes from that artifact.
- Check the complete inventories of hypotheses, estimands, findings, validation, robustness, and deviations. Confirm that every result is presented, including null and fragile findings, and that every other material item is included in the relevant section or expressly flagged for the researcher.
- Confirm that each result and robustness section includes at least one verified table, figure, or equation. Check that the actual displays render and that every caption and note is sufficient to interpret its variables, sample, uncertainty, scale, panels, and specifications. Confirm that the text immediately below each equation defines every variable and term in it.
- Search the source and output for unresolved placeholders. Confirm that methods and results contain only the factual minimum needed to orient the reader and that the remaining substantive prose is assigned to the author.
- For Word and LaTeX, compile or render successfully, inspect every page at 100 percent zoom, and correct clipping, blank pages, broken tables, bad hierarchy, orphan headings, unreadable text, and footer or numbering defects in a new version. For venue-aware Word, refresh and verify the real contents field where applicable; structurally verify true footnotes, heading and caption numbering, repeated table headers and fixed widths, accessible figure descriptions, and every comment anchor; confirm that comments appear only for sections with open questions and that the visible file has no ELARA branding or project path. For Markdown, inspect every section and structural link.
- Reopen the output mechanically. Confirm that its hash matches the run manifest and that no prior artifact changed.
- Confirm the native Plan-Mode interview preceded the skip record or every Stage 17 project write and captured the researcher's create-or-skip, format, organization, display, and emphasis preferences.
- Confirm accepting the skeleton plan was not recorded as approval of the separate `skeleton-draft-approval` gate.

## State transition

Do not alter state or write a skip record while in Plan Mode. After leaving Plan
Mode, a recorded skip follows the Researcher decisions transition above. While
building or revising, keep `current_stage` at `17-skeleton-draft` and use
`running` only for an open run. After verification, pin the new skeleton, set
`status` to `awaiting_approval`, identify its exact paths and hashes, ask for
approval or another iteration, and close the run. Revision instructions reopen
Stage 17 with new versions.

Only the researcher's explicit approval satisfies `skeleton-draft-approval`. Append the decision and pin it to the approved skeleton source, output, and hashes. Then set `current_stage` to `18-integrate-manuscript` and `status` to `ready`. A recorded skip makes the same transition without a skeleton artifact. An unsupported result or source routes to its owning earlier stage and invalidates dependent skeleton approval.

## Next-stage handoff

Tell the researcher which skeleton version and format were approved and which questions remain open. Explain that Stage 18 will use the approved skeleton only as planning context. It will not treat the skeleton as researcher-written manuscript prose. If no substantive researcher-written draft exists, Stage 18 must set `waiting_for_user` and ask for one. If a supplied draft departs from the skeleton, the draft and the researcher's explicit instructions control.
