---
utility_id: "proofread"
title: "Proofread the manuscript against the publication profile without rewriting it"
skill: "elr-proofread"
interaction_profile: "plan_then_execute"
requires: ["project/PROJECT_STATE.md", "an active manuscript version under project/artifacts/ or a researcher-supplied draft under project/inputs/manuscript/", "project/PUBLICATION_PROFILE_vNNN.md (optional; the active publication profile)"]
declared_outputs: ["project/artifacts/proofreading_report_vNNN.md", "project/artifacts/proofreading_findings_vNNN.csv", "project/artifacts/manuscript_vNNN/", "project/artifacts/manuscript_change_log_vNNN.md", "project/runs/<run_id>/build_and_render_logs/", "project/runs/<run_id>/run_manifest.json", "project/PROJECT_STATE.md", "project/DECISIONS.md", "project/RUN_LEDGER.md", "project/DEVIATIONS.md"]
human_gate: "manuscript-edit-permission"
---

## Objective

Read the manuscript as a careful proofreader and report what should change, without rewriting it. Fix only clear typographical and grammatical errors, and only when the researcher has permitted uncontroversial fixes; flag everything else for the researcher's decision. This is an audit in the sense of `guardrails.md` §8: it reports; the researcher decides; substantive changes go to Stage 19. It is not a pipeline stage and does not change `current_stage`.

## Prerequisite checks

Read `AGENTS.md`, `project/PROJECT_STATE.md`, `workflow/shared/guardrails.md`, `workflow/shared/artifact-contract.md`, and `workflow/shared/manuscript-editing-contract.md` before doing any work.

1. Resolve the manuscript to proofread (active version, or the researcher-supplied draft before Stage 17) and record its path and hash.
2. Resolve the active publication profile: venue and audience, prohibited constructions and punctuation preferences, word and grammar preferences, author-reference conventions, structure rules, venue format and length constraints, and whether uncontroversial fixes may be applied. If no profile is active, ask the researcher for the checks to apply and whether any fix may be made; do not assume.
3. Confirm the manuscript builds, so page-level review is possible.

## Researcher decisions

The researcher decides which categories are in scope, whether the agent may apply uncontroversial fixes at all, and what to do about every flagged item. The agent may identify, explain, and propose exact replacement text. It may not rewrite for style, resolve a reasoning or clarity problem by changing the argument, alter numbers, quotations, canonical language, or citations, or make any change the researcher has not permitted.

## Mode handoff

Begin in Plan Mode. Do not write any project file. Confirm the categories to check and whether uncontroversial fixes are permitted; state the exact definition of "uncontroversial" that will be used (a clear typographical or grammatical error with one obvious correction). Stop at `manuscript-edit-permission` if any fix will be applied; a report-only run needs no edit permission. After the researcher decides and exits Plan Mode, use normal approved execution.

## Work

1. Allocate a unique run ID and output versions, record the manuscript hash and the publication profile version and hash, and append a ledger start.
2. Read the entire manuscript, including footnotes, captions, tables, and appendices, page by page in the rendered output when the profile requires it. Record findings in `proofreading_findings_vNNN.csv` with location, category, the passage, the problem, a proposed fix, severity, and whether it was fixed. Categories, as the profile and researcher define them:
   - typos and clear grammatical errors, including tense consistency when the same kind of thing (prior literature, the article's own analysis) is described;
   - reasoning and clarity: awkward or unclear passages, identified but not fixed;
   - reader-friendliness: concepts the target audience would not know, unexplained at first use;
   - tone: overstatement, exaggeration, or claims stronger than the results support;
   - style tells: the profile's prohibited constructions and punctuation, word, and name conventions;
   - internal consistency: findings, numbers, and characterizations that disagree between the abstract, introduction, body, tables, and appendices; and
   - venue compliance: format and length requirements the profile names, checked against the venue's current published instructions retrieved during this run.
3. Apply a fix only if the researcher permitted uncontroversial fixes and the finding meets the stated definition; work on a new `manuscript_vNNN/` copy, never on the source. Everything else stays flagged.
4. Compile or render if anything was changed, inspect the affected pages, and produce the change log, a diff, and a redline when the profile asks.
5. Write `proofreading_report_vNNN.md`: counts by category, every finding in manuscript order with its proposed fix, the fixes applied, and the items that need a researcher decision. Then conduct two validation passes over the report against the manuscript: first that the list is complete for the categories in scope, second that every applied fix is correct and within the permitted definition. Record both passes.
6. Route flagged items the researcher accepts to Stage 19 as researcher notes; route any citation problem to Stage 18.

## Verification

- Every finding names a location, category, and proposed fix; every applied fix is a clear typographical or grammatical error with one obvious correction and appears in the change log.
- The diff against the source contains nothing beyond the permitted fixes.
- No number, quotation, canonical language, defined label, or citation was changed.
- The report records the two validation passes and the publication profile version and hash.
- `current_stage` is unchanged; the run and any permission are recorded in the ledgers.

## State transition

Do not change `current_stage`. Append the run to `RUN_LEDGER.md` and any permission decision to `DECISIONS.md`. If fixes were applied, pin the new manuscript version only after the researcher accepts the report; a manuscript with changed text also needs a fresh Stage 18 audit before it is called final.
