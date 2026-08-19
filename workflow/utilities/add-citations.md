---
utility_id: "add-citations"
title: "Research and add only the requested citations"
skill: "elr-add-citations"
interaction_profile: "plan_then_execute"
requires: ["project/PROJECT_STATE.md", "an active manuscript version under project/artifacts/ or a researcher-supplied draft under project/inputs/manuscript/", "project/PUBLICATION_PROFILE_vNNN.md (optional; the active publication profile)", "researcher marks identifying the passages that need citations"]
declared_outputs: ["project/artifacts/manuscript_vNNN/", "project/artifacts/citation_additions_vNNN.csv", "project/artifacts/manuscript_change_log_vNNN.md", "project/sources/cite_check/<run_id>/", "project/runs/<run_id>/run_manifest.json", "project/PROJECT_STATE.md", "project/DECISIONS.md", "project/RUN_LEDGER.md", "project/DEVIATIONS.md"]
human_gate: "manuscript-edit-permission"
---

## Objective

Find, retrieve, read, and add the citations the researcher has asked for in marked passages of the manuscript, in the citation style named by the publication profile, and change nothing else. This is the narrow "add citations" entry point that Stage 18 (audit-only) and Stage 19 (comment-driven revision) do not provide. It is not a pipeline stage: it does not change `current_stage`, and its output must be re-audited by Stage 18.

## Prerequisite checks

Read `AGENTS.md`, `project/PROJECT_STATE.md`, `workflow/shared/guardrails.md`, `workflow/shared/artifact-contract.md`, and `workflow/shared/manuscript-editing-contract.md` before doing any work.

1. Resolve the manuscript to work on: the active `manuscript_vNNN/` or `revised_manuscript_vNNN/`, or, before Stage 17, the researcher-supplied draft under `project/inputs/manuscript/`. Record its path and hash. Never edit an input or an earlier version.
2. Resolve the active publication profile and its citation style, or the researcher's explicit citation-style instruction for this run. If neither exists, stop and ask; do not guess Bluebook or any other style.
3. Locate every passage the researcher marked as needing a citation (highlighted text, `[[citation needed: ...]]` notes, or a supplied list). Restate the claim each citation must support. If a mark is ambiguous, ask.
4. Confirm lawful access routes for the sources likely to be needed. If a source requires researcher access, prepare an exact retrieval request rather than substituting memory.

## Researcher decisions

The researcher decides which claims need citations, the citation style, and which of the proposed sources to use. The agent may search, retrieve, read, verify, and propose. It may not invent or complete a citation, treat a search snippet or another author's footnote as a source, broaden or reword the claim so a source fits, or make any change other than adding the approved citations and the punctuation they require.

## Mode handoff

Follow `workflow/shared/execution-control.md` and create the native utility plan
before work. Begin in Plan Mode with research and proposal as the only
in-progress item. Do not write any project file. For each marked claim, present
the candidate source(s) actually retrieved and read, the supporting quotation
and pinpoint, the proposed citation in the required style, and, where nothing
was found, the searches attempted. Stop for approval at
`manuscript-edit-permission` covering exactly those citations. After the
researcher approves and exits Plan Mode, update the native plan and use normal
bounded execution. Do not start a goal.

## Work

1. After explicit permission, allocate a unique run ID and a new manuscript version, record input hashes and the publication profile version and hash, copy the manuscript into `manuscript_vNNN/`, and append a ledger start.
2. For each approved claim, retrieve the source through an authoritative route (official reporter, court, legislature, agency, publisher, repository, DOI landing page), archive a lawful copy under `project/sources/cite_check/<run_id>/`, and record full citation, stable and landing URLs, access date, local path, checksum, and the exact supporting quotation and pinpoint.
3. Insert only the approved citation at the marked location, in the required style, adjusting nothing but the punctuation the insertion requires. Where a claim could not be supported, insert nothing and leave the mark in place.
4. Record one row per marked claim in `citation_additions_vNNN.csv`: manuscript location, claim, disposition (`added`, `not found`, `researcher-supplied source pending`), source ID, citation string, supporting quotation, pinpoint, and searches attempted when nothing was found.
5. Compile or render, inspect the affected pages, and produce the change log and a diff (and a redline when the profile asks). Confirm by diff that no text other than the approved citations changed.
6. Route the new manuscript version through an audit-only Stage 18 pass (as a researcher-authorized recovery run when Stage 18 is not the current stage) before it is treated as the active manuscript.

## Verification

- Every marked claim has one row in `citation_additions_vNNN.csv`, and every `added` row links to an archived, read source with a supporting quotation.
- The diff against the source version contains only the approved citations and their punctuation.
- No citation was supplied from memory; every `not found` row lists the searches attempted.
- The run manifest records the manuscript source, the publication profile version and hash, and the citation style used.
- `current_stage` is unchanged; the run and permission are recorded in the ledgers.

## State transition

Do not change `current_stage`. Append the run to `RUN_LEDGER.md` and the permission and citation-style decision to `DECISIONS.md`. Pin the new manuscript version in `active_artifacts` only after the Stage 18 audit of that version is clean or expressly accepted; until then leave the prior active version pinned and record the new version as pending audit.
