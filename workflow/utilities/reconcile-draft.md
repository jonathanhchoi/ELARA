---
utility_id: "reconcile-draft"
title: "Reconcile the researcher's current_draft.docx with the project's records"
skill: "elr-reconcile-draft"
interaction_profile: "normal"
requires: ["project/PROJECT_STATE.md", "current_draft.docx in the project home (the folder the researcher opens)"]
declared_outputs: ["project/inputs/current_draft_vNNN.docx", "project/artifacts/current_draft_text_vNNN.md", "project/artifacts/draft_reconciliation_vNNN.csv", "project/runs/<run_id>/ (the snapshot and check output)", "project/PROJECT_STATE.md", "project/DECISIONS.md", "project/RUN_LEDGER.md", "project/DEVIATIONS.md"]
human_gate: null
---

## Objective

A researcher may keep a Word file named `current_draft.docx` in the project home, the folder they open. It is their current statement of the methods they intend, and ELARA treats it as a source of truth for methods alongside `DECISIONS.md` and the approved files. This utility brings the draft and the records into agreement whenever the draft changes, so that neither silently overrides the other. It runs automatically before the next stage or tool when `scripts/storage.py status` reports `current_draft.changed: true`, and the researcher can also run it from the menu.

This is not a pipeline stage. Do not change `current_stage`. The draft is the researcher's file: ELARA reads it under `workflow/shared/manuscript-editing-contract.md` and never edits, moves, or renames it, so this utility needs no `manuscript-edit-permission`.

## What the draft governs

- **Scope.** The research question, hypotheses, estimands, data and sources, sampling and exclusions, measurement and coding rules, validation, analysis, and robustness. The thesis, framing, and voice are read by `elr-draft-article` and Stages 18 to 20, not reconciled here.
- **Precedence.** The guardrails, the gates, and frozen or preregistered instruments come first. The record of what was actually done describes completed work. Within those limits the draft governs: a choice the records leave open follows the draft at once, and a draft change to a recorded choice that is not yet frozen takes effect when the researcher confirms it.
- **Tracked changes and comments.** The text is read as if every tracked change were accepted. A statement that rests on a change not yet accepted in Word is confirmed with the researcher before it is followed. Comments are notes, never instructions.
- **Gates.** A draft never approves a gate. Each gate still needs the researcher's explicit decision on exact versions.
- **Results seen.** A change to the analysis in the draft made after study outcomes were examined (Stage 14 has started, or results were otherwise seen) can add only an exploratory analysis, never a confirmatory one.

## Prerequisite checks

1. Read `AGENTS.md`, `project/PROJECT_STATE.md`, `workflow/shared/guardrails.md`, `workflow/shared/artifact-contract.md`, and `workflow/shared/manuscript-editing-contract.md`.
2. Read the `current_draft` block of `python scripts/storage.py status --root <project home>`. If it reports an `error` (two files with that name, or a file that is open or still syncing), tell the researcher plainly, carry on with the requested work using the last reconciled copy, and try again at the next stage start.
3. If it reports `removed: true`, append a record to `DECISIONS.md` that the researcher removed the draft, set `active_artifacts.current_draft` to `null`, and stop consulting it. Decisions that cited earlier versions stand.

## Work

1. Allocate a run ID and append a ledger start. Run `python scripts/current_draft.py snapshot --root <project home>` and save its output as `project/runs/<run_id>/snapshot.json`. It copies the draft to `project/inputs/current_draft_vNNN.docx`, writes its text with paragraph and footnote IDs to `project/artifacts/current_draft_text_vNNN.md`, and lists what changed since the last reconciled copy. `unchanged` means there is nothing to do: close the run.
2. Read the first reconciled copy in full; afterwards read the changed, added, and removed passages the snapshot lists, with enough context to understand them, and the unresolved tracked changes and comments listed at the end of the text.
3. Compare each methods statement with the active records: `DECISIONS.md` and the active charter, methods plan, hypotheses, estimands, sampling plan, codebook, schema, settings files, and preregistration; for completed work, the run ledger and reports. Write `project/artifacts/draft_reconciliation_vNNN.csv` with the columns `row_id,paragraph,quote,topic,category,record,disposition,decision_id`, one row per statement, quoting the draft word for word. With an earlier copy, every changed or added paragraph and footnote needs a row; use `not_methods` for one that states no method.

   | Category | Meaning | What ELARA does |
   |---|---|---|
   | `matches` | agrees with the records | nothing |
   | `settles_open` | decides something the records leave open | appends a `selected` record to `DECISIONS.md` (researcher label from the charter; the text begins "From current_draft.docx vNNN, P0012:" and quotes the passage; the snapshot path and hash pinned), follows it, and lists it at the next gate |
   | `conflicts_unfrozen` | conflicts with a recorded or approved choice that is not frozen | asks the researcher (below); on confirmation, supersedes the old record and invalidates dependent approvals under `artifact-contract.md` section 7 |
   | `conflicts_frozen` | conflicts with frozen or preregistered methods | never applied; asks whether it is a proposed amendment (Stage 09, with a `DEVIATIONS.md` entry if work already departed) or a passage to fix in the draft |
   | `misdescribes_done` | describes completed work differently from the record | the record stands; the passage is listed for the researcher to fix in the draft (Stage 18 or 20 picks it up) |
   | `exploratory_after_results` | changes the analysis after results were seen | records it as an exploratory analysis for Stage 14 or 15, never as confirmatory |
   | `not_methods` | a changed passage that states no method | nothing |

4. Put every `conflicts_unfrozen` and `conflicts_frozen` row, every statement that rests on an unaccepted tracked change, and every removed passage that stated a recorded choice to the researcher in one message. For each, quote the draft and the record, say what work would be redone, and recommend an answer: usually the draft for an unfrozen choice, since it is the researcher's later statement, and an amendment only when the change is worth reopening frozen work. Record each answer as a researcher decision and put its ID in the row. Until they answer, mark the row `pending`, keep working on whatever it does not affect, and list it in `outstanding_user_inputs` only when the next step depends on it.
5. Run `python scripts/current_draft.py check project/artifacts/draft_reconciliation_vNNN.csv --text project/artifacts/current_draft_text_vNNN.md --previous <the last reconciled text, when there is one> --project-root .` until it passes.
6. Record the new copy in `active_artifacts` as `current_draft` (its path and SHA-256), `current_draft_text`, and `draft_reconciliation`, and append the ledger close with the counts by category and any pending rows. Tell the researcher in a few plain lines what changed in the draft, what ELARA will now follow, and what needs their answer. Then continue with the stage or tool that was about to start.

## How other stages use the draft

- Stages 04 and 05 start their recommendations from the reconciled draft and cite its passages.
- Stage 09 compares the preregistration with the reconciled draft and lists every difference.
- Stage 14 treats a draft change made after outcomes were examined as exploratory.
- Stage 18 may use the reconciled copy as the researcher's substantive draft, editing only a versioned copy; `elr-draft-article` reads it for the thesis, framing, and voice.

## Verification

- `scripts/current_draft.py check` passes: every quote appears word for word, every record and decision exists, and every changed passage has a row.
- Every `settles_open` row cites a decision that pins the snapshot; every conflict has the researcher's decision or is reported as pending; nothing frozen or preregistered changed.
- The file in the project home is unchanged, its hash matches the snapshot, and `current_stage` is unchanged.

## State transition

Do not change `current_stage`. Append the run to `RUN_LEDGER.md` and the decisions to `DECISIONS.md`. Record the reconciled copy, its text, and the reconciliation table in `active_artifacts`, which is what makes `storage.py status` report the draft as unchanged until the researcher edits it again.
