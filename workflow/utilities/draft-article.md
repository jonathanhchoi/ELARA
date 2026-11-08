---
utility_id: "draft-article"
title: "Write an illustrative law review article draft for the researcher to rewrite"
skill: "elr-draft-article"
interaction_profile: "plan_then_execute"
requires: ["project/PROJECT_STATE.md", "a research question and claimed contribution recorded in the project (charter, conception report, selected-project decision, preemption review, or a researcher memo under project/inputs/manuscript/)", "project/PUBLICATION_PROFILE_vNNN.md (optional; the active publication profile)"]
declared_outputs: ["project/artifacts/article_draft_vNNN.docx (or .md when the researcher asks for Markdown)", "project/artifacts/article_draft_memo_vNNN.md", "project/runs/<run_id>/article_draft_source.md", "project/runs/<run_id>/article_sources.csv", "project/runs/<run_id>/article_values.csv", "project/runs/<run_id>/review/ (review copy, its manifest, the reviewed source, and the fresh reader's report)", "project/runs/<run_id>/rendered_article_draft/", "project/runs/<run_id>/run_manifest.json", "project/sources/article_draft/<run_id>/ (only when new sources are retrieved)", "project/PROJECT_STATE.md", "project/DECISIONS.md", "project/RUN_LEDGER.md", "project/DEVIATIONS.md"]
human_gate: "manuscript-edit-permission"
---

## Objective

Write a complete, readable draft of a law review article from the project's own records, so the researcher can see what a good version of the article might look like and iterate on it. The draft has an abstract, an introduction, numbered Parts, a conclusion, Bluebook-style footnotes, and an appendix with the technical details. It frames the known results in the way most interesting to law review editors and holds clearly marked placeholders for evidence still to come. It is an **illustrative draft**: the author footnote says so, it is never the manuscript in use, and the researcher rewrites it before anyone else sees it. The utility can run at any point once the project has a question and a claimed contribution, before results exist or after.

This is not a pipeline stage. Do not change `current_stage`. Follow `workflow/shared/manuscript-editing-contract.md` (section 1 permits this draft and nothing broader), `workflow/guides/law-review-article-style.md` for voice, structure, footnotes, and framing, and the active publication profile, which overrides the guide where it speaks.

## Prerequisite checks

Read `AGENTS.md`, `project/PROJECT_STATE.md`, `workflow/shared/guardrails.md`, `workflow/shared/artifact-contract.md`, `workflow/shared/manuscript-editing-contract.md`, and `workflow/guides/law-review-article-style.md` before doing any work.

1. Resolve, from the exact versions recorded in state, whatever of the following exists: the charter and conception report or selected-project decision (question, contribution, thesis); the preemption review and its archived sources (`project/sources/preemption/<run_id>/`); the feasibility audit; methods plan, hypotheses, estimands, codebook, and preregistration; validation, analysis, and robustness reports and machine-readable results; the replication package; an approved skeleton; earlier illustrative drafts and their memos; and the researcher's notes, outline, partial draft, and exemplars under `project/inputs/manuscript/`. Record each path and a hash (a value that shows whether a file has changed).
2. Confirm the project records a research question and a claimed contribution. If it does not, the Plan-Mode interview below asks for them; never supply a thesis the researcher has not accepted.
3. List every hypothesis and estimand and whether its result exists, is provisional, or is still to come. Results that are not yet validated and reproduced are described as provisional or held as placeholders.
4. Resolve the active publication profile, or record that the guide's defaults apply.
5. Confirm that `scripts/build_article_draft.py`, `workflow/templates/article_draft_template.md`, and the `law_review_v1` entry in `workflow/templates/word/profiles.json` are present, and that the environment can render a Word document to PDF for page inspection (Word or LibreOffice). If it cannot, say so and inspect the document structurally instead.

## Researcher decisions

The researcher decides the thesis and contribution, the headline framing, which results to put first, the target length, whether new sources may be retrieved, and the output format. The assistant may recommend a framing, write the prose, choose the organization within the accepted plan, and mark questions for the researcher. It may not invent a source, quotation, holding, number, or result; describe a pending result as known; leave out a null or fragile result; claim more than the design supports; or present the draft as the researcher's own work.

## Mode handoff

Follow `workflow/shared/execution-control.md` and create the native utility plan before work. Begin in Plan Mode with the drafting plan as the only item in progress and write no project file. Inspect the records above, then hold one or two short rounds of questions (Claude Code `AskUserQuestion`, Codex `request_user_input`), each with the evidence, a recommendation first, and realistic alternatives:

- the thesis and contribution as recorded, to confirm or revise;
- the headline framing: the recommended lead for law review editors and one or two alternatives, with what each puts first (guide section 4);
- which results to foreground, and in what order;
- the target length (recommend a full article of roughly 15,000 to 25,000 words including footnotes unless the profile or venue says otherwise);
- sources: cite only sources already archived in the project, marking every other needed authority `[[citation needed: ...]]` (the default), or also retrieve up to an agreed number of new authorities for the most important claims;
- the output: Word on the bundled law-review template (the default) or Markdown, and the author names and author note for the title page.

Accept "go with your recommendations" and "I don't know." Then present a short drafting plan: working title, a three-sentence pitch, the outline of Parts with their main claims, the displays, the expected placeholders, the sources, and a rough duration. Acceptance of this plan is the `manuscript-edit-permission` decision for writing this one draft version; record it with the researcher's words. Leave Plan Mode and continue in normal bounded execution in the same session. Do not start a goal.

## Work

1. Allocate a run ID and the next unused output versions, append a ledger start, and copy `workflow/templates/article_draft_template.md` to `project/runs/<run_id>/article_draft_source.md`. For a revision, copy the previous run's source, source register, and values table instead (see "Revisions and updates").
2. Build the source register `article_sources.csv` (columns `source_id,citation,url,access_date,local_path,sha256,origin`): one row per source the draft cites, each one actually retrieved and read, with its archived copy and the project record it came from in `origin`. Use the Stage 02 source records and any other archived project sources. If the researcher allowed new retrieval, research the agreed claims as one assignment each through the research workers under `workflow/shared/observation-fanout.md` (on Claude Code the saved `elr-research-fanout` workflow, with briefs under `project/runs/<run_id>/fanout/`), following the retrieval rules in `workflow/utilities/add-citations.md`, and archive what they find under `project/sources/article_draft/<run_id>/`. Anything not found stays `[[citation needed: ...]]`.
3. Build the values table `article_values.csv` (columns `key,value,status,source,description`): one `verified` row per number the draft uses, copied from the active machine-readable results with its `project/path#id`, and one `pending` row, with a description, for each result still to come.
4. Write the draft yourself, as one writer, so the voice and argument stay consistent; parallel workers never write prose. Work in this order: the pitch, the outline with heading anchors, the Parts, the appendix, then the introduction, the abstract, and the conclusion. Follow the guide and the profile. Take the thesis and contribution from the accepted plan and the records; footnote every assertion with `{{src:ID}}` or `[[citation needed: ...]]`; write every number as `{{value:key}}` and every cross-reference as a token; present every hypothesis and estimand as a result or a placeholder; keep technical detail in the appendix; and use `[[note: ...]]` only for what the researcher must decide.
5. Run `python scripts/build_article_draft.py project/runs/<run_id>/article_draft_source.md --check --project-root .` until it passes. Resolve each style warning or keep it deliberately; the warnings never block.
6. Make the consistency and transitions pass in guide section 6, reading the whole draft from start to finish.
7. Build a Markdown review copy into `project/runs/<run_id>/review/` with its own manifest, keep a copy of the reviewed source there, and give the copy to one fresh reader under `workflow/shared/fresh-review.md`, as a single research-worker assignment. The reader receives only the review copy, the guide, and the profile, reads as a law review student editor would, and reports jargon, unclear passages, overstatement, weak transitions, inconsistencies among the abstract, introduction, body, conclusion, and appendix, and footnotes whose form or support looks wrong. Fix what should be fixed in the source, confirm with `--check`, and keep the report and every disagreement with it in the review directory. A revision run gets a fresh reader only when the researcher asks.
8. Build the draft: `python scripts/build_article_draft.py project/runs/<run_id>/article_draft_source.md project/artifacts/article_draft_vNNN.docx --manifest project/runs/<run_id>/run_manifest.json --project-root .` Render it to PDF under `project/runs/<run_id>/rendered_article_draft/`, updating the contents field, and inspect every page for broken footnotes, tables, figures, headings, and the contents page. A defect found after the build is fixed in a new version; never overwrite.
9. Write `project/artifacts/article_draft_memo_vNNN.md` for the researcher, in plain language: the pitch; where the thesis, contribution, and each Part's main claims came from; the framing choices made and the alternatives; how the framing would change under each plausible outcome of each pending result; every placeholder and citation needed, by location, from the run manifest; the glossary of defined terms; the fresh reader's main findings and what was done about each; open questions; and, for a revision, what changed and why.

### Revisions and updates

New results, new sources, or the researcher's comments start a new run that copies the previous source, register, and values table into the new run directory and produces the next version; earlier versions are never edited. Update the values table from the newly active results, replace the placeholders the new evidence fills, reread the whole draft, repair every transition next to a change, and update the abstract, introduction, roadmap, and conclusion whenever a finding or the organization changed. The memo's "what changed" section lists every substantive change.

## Verification

- The builder passes, and the run manifest records the source, register, values table, output, and their hashes.
- Every cited source has an archived copy that was read and a row whose `origin` names the project record; no citation came from memory.
- Every number in the draft comes from a `verified` values row naming its result file, and every hypothesis and estimand appears as a result or a placeholder, including null and fragile results.
- The abstract, introduction, body, conclusion, and appendix agree; the roadmap matches the Parts; the claims match the design.
- The author footnote marks the draft as illustrative.
- Every rendered page was inspected, or the reason it could not be is recorded.
- The fresh reader's report and its disposition are kept with the run, and the memo is complete.
- `current_stage` is unchanged, and the permission is recorded in `DECISIONS.md`.

## State transition

Do not change `current_stage`. Append the run to `RUN_LEDGER.md` and the plan acceptance (`manuscript-edit-permission`, with the researcher's words) to `DECISIONS.md`. Record the draft, its memo, and its source in `active_artifacts` under `illustrative_article_draft`, never as the manuscript in use. Stages 18 to 20 treat it as planning context, like an approved skeleton, until the researcher rewrites it and supplies the rewrite as their own draft; any citations in that rewrite go through Stage 19 before the manuscript is called final. In `specific tools` mode offer the menu afterwards.
